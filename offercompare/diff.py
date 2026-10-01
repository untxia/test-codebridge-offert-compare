"""Comparaison de deux offres : écarts confirmés, correspondances incertaines, contrôles arithmétiques, effet net.

Règles :
  - un écart est « substantiel » s'il touche le périmètre (ligne ajoutée/supprimée), une quantité, un prix unitaire,
    une date de livraison ou un total affiché ; renommage, ordre des lignes, mise en forme : jamais ;
  - chaque écart porte la référence des DEUX emplacements sources (page, ligne, zone dans le PDF) ;
  - les totaux sont recalculés de façon déterministe ; on signale l'écart avec ce qui est écrit, sans jamais le corriger ;
  - en cas de doute (ligne scindée, renommage vague) on ne conclut pas : on pose la question ;
  - document illisible (pas de couche texte, aucun tableau reconnu, devises différentes) : on refuse de conclure.
"""
from __future__ import annotations

import os
import time
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Optional

from .extract import extract_offer
from .match import MatchResult, match_offers
from .models import BBox, Item, Money, Offer
from .parsing import norm

CENT = Decimal("0.01")
TOL = Decimal("0.01")
TYPE_ORDER = {"unit_price": 0, "quantity": 1, "delivery_date": 2}


def d(x: Optional[Decimal]) -> Optional[str]:
    return None if x is None else str(x.quantize(CENT) if isinstance(x, Decimal) else x)


def _box(b: Optional[BBox]) -> Optional[Dict]:
    return None if b is None else {"page": b.page, "x0": b.x0, "top": b.top, "x1": b.x1, "bottom": b.bottom}


def _amount(it: Item) -> Optional[Decimal]:
    """Montant de ligne tel qu'écrit dans le document ; à défaut qty × prix."""
    if it.line_total is not None:
        return it.line_total
    if it.qty is not None and it.unit_price is not None:
        return (it.qty * it.unit_price).quantize(CENT)
    return None


def _calc(it: Item) -> Optional[Decimal]:
    if it.qty is not None and it.unit_price is not None:
        return (it.qty * it.unit_price).quantize(CENT)
    return _amount(it)


def _qty_txt(it: Item) -> Optional[str]:
    if it.qty is None:
        return None
    q = int(it.qty) if it.qty == it.qty.to_integral() else it.qty
    return f"{q}" + (f" {it.unit}" if it.unit else "")


def _vals(it: Item) -> Dict:
    return {"label": it.label, "qty": _qty_txt(it), "unit_price": d(it.unit_price), "line_total": d(_amount(it)),
            "delivery": it.delivery}


def _src(role: str, offer: Offer, it: Item, field: Optional[str] = None) -> Dict:
    return {"document": role, "file": os.path.basename(offer.file), "page": it.page,
            "row_number": it.printed_no or str(it.index), "label_text": it.label, "bbox": _box(it.bbox),
            "cell": _box(it.cells.get(field)) if field else None, "raw": it.raw.get(field) if field else None}


def _tsrc(role: str, offer: Offer, m: Optional[Money], key: str) -> Optional[Dict]:
    if m is None:
        return None
    return {"document": role, "file": os.path.basename(offer.file), "page": m.bbox.page if m.bbox else None,
            "block": "totals", "field": key, "raw": m.raw, "bbox": _box(m.bbox)}


def _same_delivery(a: Item, b: Item) -> bool:
    if a.delivery is None or b.delivery is None:
        return a.delivery == b.delivery
    if a.delivery_is_date != b.delivery_is_date:
        return False
    return a.delivery == b.delivery if a.delivery_is_date else norm(a.delivery) == norm(b.delivery)


def _field_diffs(o: Item, r: Item) -> List[Dict]:
    out = []
    if o.unit_price != r.unit_price and not (o.unit_price is None and r.unit_price is None):
        out.append({"type": "unit_price", "field": "unit_price", "from": d(o.unit_price), "to": d(r.unit_price)})
    if o.qty != r.qty or (o.unit or "").lower() != (r.unit or "").lower():
        out.append({"type": "quantity", "field": "qty", "from": _qty_txt(o), "to": _qty_txt(r)})
    if not _same_delivery(o, r):
        out.append({"type": "delivery_date", "field": "delivery", "from": o.delivery, "to": r.delivery})
    return out


# --- contrôles arithmétiques --------------------------------------------------------------------------------------
def arithmetic_checks(role: str, offer: Offer) -> List[Dict]:
    out: List[Dict] = []
    for it in offer.items:                           # lignes : qty × prix unitaire vs total de ligne affiché
        if it.qty is not None and it.unit_price is not None and it.line_total is not None:
            calc = (it.qty * it.unit_price).quantize(CENT)
            if abs(calc - it.line_total) > TOL:
                out.append({"document": role, "scope": "line", "code": "line_arithmetic", "stated": d(it.line_total),
                            "recomputed": d(calc), "difference": d(it.line_total - calc),
                            "source": _src(role, offer, it, "line_total")})
    t = offer.totals
    rec_ht = sum((x for x in (_calc(i) for i in offer.items) if x is not None), Decimal("0")).quantize(CENT)
    if t.ht is not None and t.ht.value is not None and offer.items:
        if abs(t.ht.value - rec_ht) > TOL:
            out.append({"document": role, "scope": "total_ht", "code": "total_ht_sum_mismatch", "stated": d(t.ht.value),
                        "recomputed": d(rec_ht), "difference": d(t.ht.value - rec_ht),
                        "source": _tsrc(role, offer, t.ht, "ht")})
    if t.ht is not None and t.vat is not None and t.vat_rate is not None and t.ht.value is not None and t.vat.value is not None:
        calc = (t.ht.value * t.vat_rate).quantize(CENT, rounding=ROUND_HALF_UP)
        if abs(calc - t.vat.value) > TOL:
            out.append({"document": role, "scope": "vat", "code": "vat_mismatch", "stated": d(t.vat.value),
                        "recomputed": d(calc), "difference": d(t.vat.value - calc),
                        "basis": "stated_total_ht", "source": _tsrc(role, offer, t.vat, "vat")})
    if t.ht is not None and t.vat is not None and t.ttc is not None and None not in (t.ht.value, t.vat.value, t.ttc.value):
        calc = t.ht.value + t.vat.value
        if abs(calc - t.ttc.value) > TOL:
            out.append({"document": role, "scope": "total_ttc", "code": "ttc_mismatch", "stated": d(t.ttc.value),
                        "recomputed": d(calc), "difference": d(t.ttc.value - calc),
                        "basis": "stated_total_ht_plus_stated_vat", "source": _tsrc(role, offer, t.ttc, "ttc")})
    return out


def _recomputed_totals(offer: Offer) -> Optional[Dict]:
    if not offer.items:
        return None
    ht = sum((x for x in (_calc(i) for i in offer.items) if x is not None), Decimal("0")).quantize(CENT)
    rate = offer.totals.vat_rate
    out = {"ht": d(ht), "basis": "sum(qty x unit_price)"}
    if rate is not None:
        vat = (ht * rate).quantize(CENT, rounding=ROUND_HALF_UP)
        out.update({"vat": d(vat), "ttc": d(ht + vat), "vat_rate": str(rate)})
    return out


def _doc_summary(role: str, offer: Offer) -> Dict:
    t = offer.totals
    return {"file": os.path.basename(offer.file), "pages": [vars(p) for p in offer.pages], "has_text_layer": offer.has_text_layer,
            "line_items": len(offer.items), "currency": offer.currency, "method": offer.method,
            "stated_totals": {"ht": d(t.ht.value) if t.ht else None, "vat": d(t.vat.value) if t.vat else None,
                              "ttc": d(t.ttc.value) if t.ttc else None, "vat_rate": str(t.vat_rate) if t.vat_rate is not None else None},
            "recomputed_totals": _recomputed_totals(offer), "warnings": offer.warnings, "extract_ms": offer.elapsed_ms}


# --- comparaison --------------------------------------------------------------------------------------------------
def _decline(orig: Offer, rev: Offer, reasons: List[str]) -> Dict:
    return {"decision": "decline", "decision_reasons": reasons,
            "documents": {"original": _doc_summary("original", orig), "revised": _doc_summary("revised", rev)},
            "changes": [], "uncertain": [], "arithmetic": [], "net_effect": None, "non_commercial": None,
            "summary": {"confirmed_changes": 0, "uncertain_items": 0, "arithmetic_discrepancies": 0},
            "warnings": orig.warnings + rev.warnings}


def compare_offers(orig: Offer, rev: Offer, overrides: Optional[Dict] = None) -> Dict:
    t0 = time.perf_counter()
    reasons: List[str] = []
    for role, off in (("original", orig), ("revised", rev)):
        if not off.has_text_layer:
            reasons.append(f"no_text_layer_{role}")
        elif not off.items:
            reasons.append(f"no_line_items_{role}")
    if orig.currency and rev.currency and orig.currency != rev.currency:
        reasons.append("currency_mismatch")
    for role, off in (("original", orig), ("revised", rev)):
        if len(off.currencies_seen) > 1:
            reasons.append(f"multiple_currencies_{role}")
    if reasons:
        return _decline(orig, rev, reasons)

    m: MatchResult = match_offers(orig, rev, overrides)
    O = {i.index: i for i in orig.items}
    R = {i.index: i for i in rev.items}
    changes: List[Dict] = []

    def add(ctype: str, o: Optional[Item], r: Optional[Item], **extra) -> None:
        field = {"unit_price": "unit_price", "quantity": "qty", "delivery_date": "delivery"}.get(ctype)
        ch = {"type": ctype, "orig_index": o.index if o else None, "rev_index": r.index if r else None,
              "original": _vals(o) if o else None, "revised": _vals(r) if r else None,
              "line_total_delta": d((_amount(r) or Decimal(0)) - (_amount(o) or Decimal(0))) if (o and r) else
              d(-(_amount(o) or Decimal(0))) if o else d(_amount(r) or Decimal(0)),
              "sources": {"original": _src("original", orig, o, field) if o else None,
                          "revised": _src("revised", rev, r, field) if r else None}}
        ch.update(extra)
        changes.append(ch)

    for p in m.pairs:
        o, r = O[p.orig], R[p.rev]
        for fd in _field_diffs(o, r):
            add(fd["type"], o, r, field=fd["field"], **{"from": fd["from"], "to": fd["to"]}, basis=p.basis)
    for i in m.removed:
        add("scope_removed", O[i], None)
    for i in m.added:
        add("scope_added", None, R[i])
    changes.sort(key=lambda c: (c["orig_index"] if c["orig_index"] is not None else 10_000 + (c["rev_index"] or 0),
                                TYPE_ORDER.get(c["type"], 9)))

    # totaux affichés : un seul écart « stated_total » (HT, TVA, TTC regroupés)
    to, tr = orig.totals, rev.totals
    fields = {}
    for key, a, b in (("ht", to.ht, tr.ht), ("vat", to.vat, tr.vat), ("ttc", to.ttc, tr.ttc)):
        if a and b and a.value is not None and b.value is not None and a.value != b.value:
            fields[key] = {"from": d(a.value), "to": d(b.value), "delta": d(b.value - a.value)}
    if fields:
        changes.append({"type": "stated_total", "orig_index": None, "rev_index": None, "fields": fields,
                        "sources": {"original": _tsrc("original", orig, to.ht, "ht"), "revised": _tsrc("revised", rev, tr.ht, "ht")}})
    for k, c in enumerate(changes, 1):
        c["id"] = f"C{k}"

    arithmetic = arithmetic_checks("original", orig) + arithmetic_checks("revised", rev)
    for k, a in enumerate(arithmetic, 1):
        a["id"] = f"A{k}"

    uncertain = []
    for g in m.uncertain:
        o_items, r_items = [O[i] for i in g.orig], [R[i] for i in g.rev]
        o_sum = sum((_amount(i) or Decimal(0) for i in o_items), Decimal(0))
        r_sum = sum((_amount(i) or Decimal(0) for i in r_items), Decimal(0))
        entry = {"id": g.id, "kind": g.kind, "reason_code": g.reason_code,
                 "original": [{**_vals(i), "index": i.index, "source": _src("original", orig, i)} for i in o_items],
                 "revised": [{**_vals(i), "index": i.index, "source": _src("revised", rev, i)} for i in r_items],
                 "candidates": [{k: (round(v, 2) if isinstance(v, float) else v) for k, v in c.items()} for c in g.candidates],
                 "amount_at_stake": {"original": d(o_sum), "revised": d(r_sum), "delta": d(r_sum - o_sum)}}
        if g.kind == "one_to_one":   # aperçu : ce qui changerait si c'était la même ligne
            entry["if_same_item"] = [{k: v for k, v in fd.items() if k != "field"} for fd in _field_diffs(o_items[0], r_items[0])]
        uncertain.append(entry)

    # effet net
    rec_o, rec_r = _recomputed_totals(orig), _recomputed_totals(rev)
    net: Dict = {"stated": {}, "recomputed_ht": None}
    for key in ("ht", "vat", "ttc"):
        a, b = getattr(to, key), getattr(tr, key)
        if a and b and a.value is not None and b.value is not None:
            net["stated"][key] = {"original": d(a.value), "revised": d(b.value), "delta": d(b.value - a.value)}
    if rec_o and rec_r:
        net["recomputed_ht"] = {"original": rec_o["ht"], "revised": rec_r["ht"],
                                "delta": d(Decimal(rec_r["ht"]) - Decimal(rec_o["ht"]))}
    net["unattributed_by_uncertain_items"] = d(sum((Decimal(u["amount_at_stake"]["delta"]) for u in uncertain), Decimal(0)))

    pairs_by_o = sorted(m.pairs, key=lambda p: p.orig)
    reordered = [p.rev for p in pairs_by_o] != sorted(p.rev for p in pairs_by_o)
    renamed = [{"orig_index": p.orig, "rev_index": p.rev, "from": O[p.orig].label, "to": R[p.rev].label}
               for p in m.pairs if p.label_changed]

    if uncertain:
        decision = "conclude_partially_and_ask"
    elif not changes and not arithmetic:
        decision = "no_changes"
    else:
        decision = "conclude"
    counts: Dict[str, int] = {}
    for c in changes:
        counts[c["type"]] = counts.get(c["type"], 0) + 1
    return {
        "decision": decision, "decision_reasons": [],
        "documents": {"original": _doc_summary("original", orig), "revised": _doc_summary("revised", rev)},
        "changes": changes, "uncertain": uncertain, "arithmetic": arithmetic, "net_effect": net,
        "non_commercial": {"renamed": renamed, "reordered": reordered, "note": "Non signalés comme écarts commerciaux."},
        "summary": {"confirmed_changes": len(changes), "by_type": counts, "uncertain_items": len(uncertain),
                    "arithmetic_discrepancies": len(arithmetic)},
        "warnings": orig.warnings + rev.warnings,
        "compare_ms": round((time.perf_counter() - t0) * 1000, 1),
    }


def compare_files(original_pdf: str, revised_pdf: str, overrides: Optional[Dict] = None,
                  names: Optional[Dict[str, str]] = None) -> Dict:
    t0 = time.perf_counter()
    names = names or {}
    o = extract_offer(original_pdf, names.get("original"))
    r = extract_offer(revised_pdf, names.get("revised"))
    rep = compare_offers(o, r, overrides)
    rep["total_ms"] = round((time.perf_counter() - t0) * 1000, 1)
    return rep
