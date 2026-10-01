"""Extraction déterministe des lignes et des totaux d'un PDF texte (pdfplumber), avec page + zone (bbox)
pour chaque valeur : c'est ce qui permet les références vers l'emplacement source.

Stratégie : 1) tableaux à traits (pdfplumber), 2) à défaut, reconstruction par alignement des mots sous les en-têtes.
Les colonnes sont reconnues par leur en-tête (désignation, qté, prix unitaire, total, livraison...), jamais par position.
Aucune correction silencieuse : on conserve ce qui est écrit ; les incohérences deviennent des avertissements.
"""
from __future__ import annotations

import re
import time
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

import pdfplumber

from .models import BBox, Item, Money, Offer, PageInfo, Totals
from .parsing import (MONEY_TAIL_RE, clean_spaces, detect_currencies, norm, parse_date, parse_money,
                      parse_qty)

CELL_GAP = 8.0   # écart horizontal (pt) au-delà duquel deux mots appartiennent à des cellules différentes

ROLE_LABELS = {"label", "qty", "unit_price", "line_total", "delivery", "printed_no"}


def _role_of(header: str) -> Optional[str]:
    tokens = set(norm(header).split())
    if not tokens:
        return None
    if tokens & {"livraison", "delai", "delivery", "echeance", "ship", "shipping", "shipment", "dispatch", "eta", "delivered"}:
        return "delivery"
    if tokens & {"unitaire", "pu", "unit"} or (tokens & {"prix", "tarif"} and not tokens & {"total", "montant"}):
        return "unit_price"
    if tokens & {"total", "montant", "amount"}:
        return "line_total"
    if tokens & {"qte", "quantite", "qty", "quantity", "nb", "nombre"}:
        return "qty"
    if tokens & {"designation", "description", "article", "libelle", "produit", "item", "prestation", "intitule"}:
        return "label"
    if tokens <= {"n", "no", "num", "pos", "poste", "ligne", "ref", "reference", "#"}:
        return "printed_no"
    return None


def _header_map(cells: List[str]) -> Optional[Dict[int, str]]:
    cmap: Dict[int, str] = {}
    used = set()
    for i, c in enumerate(cells):
        role = _role_of(c)
        if role and role not in used:
            cmap[i] = role
            used.add(role)
    if "label" in used and len(used) >= 3:
        return cmap
    return None


def _bbox(page: int, b) -> Optional[BBox]:
    if b is None:
        return None
    return BBox(page, round(float(b[0]), 2), round(float(b[1]), 2), round(float(b[2]), 2), round(float(b[3]), 2))


def _union(page: int, boxes: List[Optional[BBox]]) -> BBox:
    bs = [b for b in boxes if b]
    return BBox(page, min(b.x0 for b in bs), min(b.top for b in bs), max(b.x1 for b in bs), max(b.bottom for b in bs))


def _extract_items_lines(pdf) -> Tuple[List[Item], set]:
    """Tableaux à traits."""
    items: List[Item] = []
    roles_seen: set = set()
    colmap: Optional[Dict[int, str]] = None
    ncols = 0
    for page in pdf.pages:
        for table in page.find_tables():
            texts = table.extract()
            for row_text, row in zip(texts, table.rows):
                cells = [clean_spaces((c or "").replace("\n", " ")) for c in row_text]
                hm = _header_map(cells)
                if hm:
                    colmap, ncols = hm, len(cells)
                    roles_seen |= set(hm.values())
                    continue
                if not colmap or len(cells) != ncols:
                    continue
                raw = {role: cells[i] for i, role in colmap.items()}
                boxes = {role: _bbox(page.page_number, row.cells[i]) for i, role in colmap.items() if i < len(row.cells)}
                it = _build_item(len(items) + 1, page.page_number, raw, boxes)
                if it:
                    items.append(it)
    return items, roles_seen


def _cells_of(words: List[dict]) -> List[List[dict]]:
    cells, cur = [], [words[0]]
    for w in words[1:]:
        if w["x0"] - cur[-1]["x1"] > CELL_GAP:
            cells.append(cur)
            cur = [w]
        else:
            cur.append(w)
    cells.append(cur)
    return cells


def _ctext(ws: List[dict]) -> str:
    return " ".join(w["text"] for w in ws)


def _cbox(pno: int, ws: List[dict]) -> BBox:
    return BBox(pno, round(min(w["x0"] for w in ws), 2), round(min(w["top"] for w in ws), 2),
                round(max(w["x1"] for w in ws), 2), round(max(w["bottom"] for w in ws), 2))


def _extract_items_words(pdf) -> Tuple[List[Item], set]:
    """Sans traits : en-tête repéré par ses mots-clés, puis chaque cellule est rattachée à l'en-tête le plus proche
    (alignement gauche, droit ou centre). Un libellé sur plusieurs lignes (centré verticalement ou non) est recollé :
    les lignes qui ne contiennent que du libellé sont rattachées à la ligne de données la plus proche."""
    items: List[Item] = []
    roles_seen: set = set()
    headers: Optional[List[Tuple[Optional[str], float, float]]] = None
    for page in pdf.pages:
        pno = page.page_number
        rows: List[dict] = []
        frags: List[dict] = []
        for text, words, spans in _lines(page):
            cells = _cells_of(words)
            hm = _header_map([_ctext(c) for c in cells])
            if hm:
                _flush_rows(items, pno, rows, frags)
                rows, frags = [], []
                headers = [(hm.get(i), min(w["x0"] for w in c), max(w["x1"] for w in c)) for i, c in enumerate(cells)]
                roles_seen |= set(hm.values())
                continue
            if not headers:
                continue
            groups: Dict[str, List[List[dict]]] = {}
            for c in cells:
                x0, x1 = min(w["x0"] for w in c), max(w["x1"] for w in c)
                role = min(headers, key=lambda h: min(abs(x0 - h[1]), abs(x1 - h[2]), abs((x0 + x1) / 2 - (h[1] + h[2]) / 2)))[0]
                if role:
                    groups.setdefault(role, []).append(c)
            if not groups:
                continue
            entry = dict(top=min(w["top"] for w in words), bottom=max(w["bottom"] for w in words),
                         raw={r: " ".join(_ctext(c) for c in cs) for r, cs in groups.items()},
                         boxes={r: _cbox(pno, [w for c in cs for w in c]) for r, cs in groups.items()})
            (frags if set(groups) == {"label"} else rows).append(entry)
        _flush_rows(items, pno, rows, frags)
    return items, roles_seen


def _flush_rows(items: List[Item], pno: int, rows: List[dict], frags: List[dict], reach: float = 12.0) -> None:
    for f in frags:   # rattache chaque fragment de libellé à la ligne de données la plus proche (verticalement)
        near = [r for r in rows if f["bottom"] >= r["top"] - reach and f["top"] <= r["bottom"] + reach]
        if near:
            r = min(near, key=lambda r: abs((r["top"] + r["bottom"]) / 2 - (f["top"] + f["bottom"]) / 2))
            r.setdefault("frags", []).append(f)
    for r in rows:
        parts = list(r.get("frags", []))
        if r["raw"].get("label"):
            parts.append(dict(top=r["boxes"]["label"].top, raw=r["raw"], boxes=r["boxes"]))
        if parts:
            parts.sort(key=lambda p: p["top"])
            r["raw"]["label"] = " ".join(p["raw"]["label"] for p in parts)
            r["boxes"]["label"] = _union(pno, [p["boxes"]["label"] for p in parts])
        it = _build_item(len(items) + 1, pno, r["raw"], r["boxes"])
        if it:
            items.append(it)


def _build_item(index: int, pno: int, raw: Dict[str, str], boxes: Dict[str, Optional[BBox]]) -> Optional[Item]:
    label = raw.get("label", "").strip()
    if not label:
        return None
    nl = norm(label)
    if re.match(r"(sous )?total\b|sub ?total\b|tva\b|vat\b|sales tax\b|grand total|total due|montant (ht|ttc)\b|net a payer", nl):
        return None
    qty, unit = parse_qty(raw.get("qty")) if "qty" in raw else (None, "")
    price = parse_money(raw.get("unit_price")) if "unit_price" in raw else None
    total = parse_money(raw.get("line_total")) if "line_total" in raw else None
    if qty is None and price is None and total is None:
        return None
    dtext = raw.get("delivery", "").strip()
    diso = parse_date(dtext) if dtext else None
    cell_boxes = {k: v for k, v in boxes.items() if v}
    warns: List[str] = []
    if qty is not None and price is not None and total is not None and abs(qty * price - total) > Decimal("0.01"):
        warns.append(f"quantité × prix unitaire ({qty * price}) ≠ total de ligne ({total})")
    return Item(
        index=index, printed_no=raw.get("printed_no") or None, label=label, qty=qty, unit=unit,
        unit_price=price, line_total=total, delivery=(diso or dtext or None), delivery_is_date=diso is not None,
        page=pno, bbox=_union(pno, list(cell_boxes.values())), cells=cell_boxes, raw=raw, warnings=warns)


def _lines(page) -> List[Tuple[str, List[dict], List[Tuple[int, int]]]]:
    """Mots regroupés par ligne visuelle : (texte, mots, spans de caractères par mot)."""
    words = sorted(page.extract_words(x_tolerance=2, y_tolerance=2), key=lambda w: (round(w["top"]), w["x0"]))
    groups: List[List[dict]] = []
    for w in words:
        if groups and abs(w["top"] - groups[-1][0]["top"]) <= 3:
            groups[-1].append(w)
        else:
            groups.append([w])
    out = []
    for g in groups:
        g.sort(key=lambda w: w["x0"])
        text, spans, pos = "", [], 0
        for w in g:
            if text:
                text += " "
                pos += 1
            spans.append((pos, pos + len(w["text"])))
            text += w["text"]
            pos += len(w["text"])
        out.append((text, g, spans))
    return out


def _extract_totals(pdf) -> Totals:
    tot = Totals()
    for page in pdf.pages:
        for text, words, spans in _lines(page):
            n = norm(text)
            n = re.sub(r"\bh t\b", "ht", n)
            n = re.sub(r"\bt t c\b", "ttc", n)
            if re.match(r"(total|montant) (ttc|toutes taxes)|net a payer|total a payer|grand total|total due|amount due|balance due|total (incl|including|with)\b", n):
                key = "ttc"
            elif re.match(r"(sous )?(total|montant) (ht|hors tax)|sub ?total\b|net total|total (excl|excluding|before|ex)\b", n):
                key = "ht"
            elif re.match(r"(tva|vat|taxe|sales tax|tax)\b", n):
                key = "vat"
            else:
                continue
            m = MONEY_TAIL_RE.search(text)
            if not m:
                continue
            val = parse_money(m.group(0))
            if val is None:
                continue
            hit = [w for w, (a, b) in zip(words, spans) if b > m.start()]
            box = BBox(page.page_number, round(min(w["x0"] for w in hit), 2), round(min(w["top"] for w in hit), 2),
                       round(max(w["x1"] for w in hit), 2), round(max(w["bottom"] for w in hit), 2))
            setattr(tot, key, Money(val, clean_spaces(m.group(0)), box))   # la dernière occurrence gagne
            if key == "vat":
                r = re.search(r"(\d+(?:[.,]\d+)?)\s*%", text)
                if r:
                    tot.vat_rate = Decimal(r.group(1).replace(",", ".")) / 100
    return tot



_NUMERIC_DATE = re.compile(r"^(\d{1,2})[-/.](\d{1,2})[-/.](\d{2,4})$")


def _fix_date_convention(offer: Offer, text: str) -> None:
    """Dates numériques : jj/mm ou mm/jj ? Décidé par le document (un champ > 12), sinon par la devise, avec avertissement."""
    raws = [(it, _NUMERIC_DATE.match((it.raw.get("delivery") or "").strip())) for it in offer.items]
    raws = [(it, m) for it, m in raws if m]
    if not raws:
        return
    first_gt12 = any(int(m[1]) > 12 for _, m in raws)
    second_gt12 = any(int(m[2]) > 12 for _, m in raws)
    if first_gt12 and not second_gt12:
        month_first = False
    elif second_gt12 and not first_gt12:
        month_first = True
    else:
        month_first = "USD" in detect_currencies(text) or "$" in text
        if any(int(m[1]) <= 12 and int(m[2]) <= 12 and m[1] != m[2] for _, m in raws):
            offer.warnings.append("Dates numériques ambiguës (jj/mm ou mm/jj) : interprétées en "
                                  + ("mm/jj/aaaa" if month_first else "jj/mm/aaaa") + " d'après la devise du document.")
    if month_first:
        for it, _ in raws:
            iso = parse_date(it.raw["delivery"].strip(), month_first=True)
            if iso:
                it.delivery, it.delivery_is_date = iso, True


def extract_offer(path: str, display_name: Optional[str] = None) -> Offer:
    t0 = time.perf_counter()
    with pdfplumber.open(path) as pdf:
        infos: List[PageInfo] = []
        all_text = []
        for p in pdf.pages:
            words = p.extract_words(x_tolerance=2, y_tolerance=2)
            infos.append(PageInfo(p.page_number, round(float(p.width), 2), round(float(p.height), 2), bool(words), len(p.images)))
            all_text.append(" ".join(w["text"] for w in words))
        has_text = any(i.has_text for i in infos)
        offer = Offer(file=display_name or path, pages=infos, has_text_layer=has_text, items=[], totals=Totals(), currency=None,
                      currencies_seen={}, method="none")
        if not has_text:
            offer.warnings.append("Aucune couche texte : document scanné ou image. Hors périmètre (pas d'OCR).")
        else:
            blanks = [i.number for i in infos if not i.has_text]
            if blanks:
                offer.warnings.append(f"Pages sans texte exploitable : {blanks}.")
            roles: set = set()
            for strat, fn in (("lines", _extract_items_lines), ("words", _extract_items_words)):
                items, roles = fn(pdf)
                if items:
                    offer.items, offer.method = items, f"pdfplumber/{strat}"
                    break
            offer.totals = _extract_totals(pdf)
            _fix_date_convention(offer, " ".join(all_text))
            offer.currencies_seen = detect_currencies(" ".join(all_text))
            if offer.currencies_seen:
                offer.currency = max(offer.currencies_seen, key=offer.currencies_seen.get)
            if len(offer.currencies_seen) > 1:
                offer.warnings.append(f"Plusieurs devises détectées : {offer.currencies_seen}.")
            if not offer.items:
                offer.warnings.append("Aucun tableau de lignes reconnu (en-têtes de colonnes introuvables).")
            else:
                for r in ("qty", "unit_price", "line_total"):
                    if r not in roles:
                        offer.warnings.append(f"Colonne « {r} » non reconnue dans l'en-tête du tableau.")
            if offer.totals.ht is None:
                offer.warnings.append("Total HT introuvable.")
    offer.elapsed_ms = round((time.perf_counter() - t0) * 1000, 1)
    return offer
