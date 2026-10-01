#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Vérifie le jeu de test de façon indépendante du générateur :
  - lit les PDF avec pdfplumber (comme le ferait l'application) et compare lignes/totaux à la vérité terrain ;
  - recalcule l'arithmétique ligne par ligne ;
  - contrôle que chaque référence source attendue (page + libellé) existe bien dans le PDF ;
  - recalcule les écarts S1/S3 par différence de clés et les compare au fichier d'attendus ;
  - contrôle que le PDF scanné n'a aucune couche texte.
Code de sortie 0 si tout est cohérent.
"""
import json
import os
import re
import sys
from decimal import Decimal

import pdfplumber

HERE = os.path.dirname(os.path.abspath(__file__))
D = Decimal
MONTHS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août",
          "septembre", "octobre", "novembre", "décembre"]
fails = []


def check(cond, msg):
    print(("  ok   " if cond else "  FAIL ") + msg)
    if not cond:
        fails.append(msg)


def money(s):
    s = re.sub(r"[^\d,.\-]", "", s.replace(" ", " ").replace("EUR", "").replace("€", ""))
    return D(s.replace(",", "."))


def date_iso(s):
    s = s.replace(" ", " ").strip()
    m = re.fullmatch(r"(\d{2})/(\d{2})/(\d{4})", s)
    if m:
        return f"{m[3]}-{m[2]}-{m[1]}"
    m = re.fullmatch(r"(\d{1,2}) (\w+) (\d{4})", s)
    if m and m[2] in MONTHS:
        return f"{m[3]}-{MONTHS.index(m[2]) + 1:02d}-{int(m[1]):02d}"
    return s


def parse_pdf(path):
    rows, totals, pages_text = [], {}, []
    with pdfplumber.open(path) as pdf:
        for pno, page in enumerate(pdf.pages, 1):
            pages_text.append(page.extract_text() or "")
            for tb in page.extract_tables():
                for cells in tb:
                    c = [(x or "").replace("\n", " ").strip() for x in cells]
                    if c and c[0].isdigit() and len(c) >= 6:
                        q = re.fullmatch(r"(\d+)(?: (\w+))?", c[2])
                        rows.append(dict(row_number=int(c[0]), page=pno, label=c[1], qty=q[1] + (f" {q[2]}" if q[2] else ""),
                                         unit_price=money(c[3]), line_total=money(c[4]), delivery=date_iso(c[5])))
                    elif c and c[0].upper().startswith(("TOTAL HT", "TVA", "TOTAL TTC")):
                        k = "ht" if "HT" in c[0].upper() else ("tva" if c[0].upper().startswith("TVA") else "ttc")
                        totals[k] = money(c[1])
    return rows, totals, pages_text


def main():
    exp = json.load(open(os.path.join(HERE, "expected_differences.json"), encoding="utf-8"))
    docs = exp["documents"]

    for name, truth in docs.items():
        print(f"[{name}] {truth['file']}")
        rows, totals, texts = parse_pdf(os.path.join(HERE, truth["file"]))
        check(len(texts) == truth["pages"] and len(texts) <= 3, f"{len(texts)} pages (max 3)")
        check(len(rows) == truth["line_items"] <= 10, f"{len(rows)} lignes (max 10)")
        for t in truth["rows"]:
            got = next((x for x in rows if x["row_number"] == t["row_number"]), None)
            ok = (got is not None and got["page"] == t["page"] and got["label"] == t["label"] and got["qty"] == t["qty"]
                  and got["unit_price"] == D(t["unit_price"]) and got["line_total"] == D(t["line_total"])
                  and got["delivery"] == t["delivery"])
            check(ok, f"ligne {t['row_number']} p{t['page']} : {t['label']}")
            if got:
                q = D(got["qty"].split()[0])
                check(q * got["unit_price"] == got["line_total"], f"  arithmétique ligne {t['row_number']} : {q} x {got['unit_price']} = {got['line_total']}")
        for k in ("ht", "tva", "ttc"):
            check(totals.get(k) == D(truth["stated_totals"][k]), f"total {k} affiché = {truth['stated_totals'][k]}")
        rec = sum((x["line_total"] for x in rows), D("0.00"))
        check((rec == totals["ht"]) == truth["arithmetic_consistent"],
              f"cohérence HT : somme des lignes {rec} vs affiché {totals['ht']} (cohérent attendu = {truth['arithmetic_consistent']})")
        check(totals["ht"] * D("0.20") == totals["tva"] and totals["ht"] + totals["tva"] == totals["ttc"],
              "TVA 20 % et TTC cohérents avec le HT affiché")

    print("[scanned] pdf/offer_revised_scanned.pdf")
    with pdfplumber.open(os.path.join(HERE, "pdf/offer_revised_scanned.pdf")) as pdf:
        check(all(not (p.extract_text() or "").strip() for p in pdf.pages), "aucune couche texte")
        check(all(len(p.images) >= 1 for p in pdf.pages), "une image par page")
        check(len(pdf.pages) <= 3, f"{len(pdf.pages)} pages")

    print("[références sources]")
    cache = {}
    def page_text(f, p):
        if f not in cache:
            cache[f] = parse_pdf(os.path.join(HERE, f))[2]
        return cache[f][p - 1].replace(" ", " ")

    def walk(o):
        if isinstance(o, dict):
            if "file" in o and "page" in o and "label_text" in o:
                yield o
            for v in o.values():
                yield from walk(v)
        elif isinstance(o, list):
            for v in o:
                yield from walk(v)

    refs = list(walk(exp["scenarios"]))
    rows_cache = {}
    for ref in refs:
        f = ref["file"]
        if "row_number" in ref:  # ligne d'articles : page + numéro + libellé exacts (libellés longs = retour à la ligne)
            if f not in rows_cache:
                rows_cache[f] = parse_pdf(os.path.join(HERE, f))[0]
            hit = [x for x in rows_cache[f] if x["row_number"] == ref["row_number"] and x["page"] == ref["page"]
                   and x["label"] == ref["label_text"]]
            check(len(hit) == 1, f"ligne {ref['row_number']} p{ref['page']} '{ref['label_text']}' ({os.path.basename(f)})")
        else:
            check(ref["label_text"] in page_text(f, ref["page"]),
                  f"'{ref['label_text']}' trouvé p{ref['page']} de {os.path.basename(f)}")

    print("[écarts recalculés par clés]")
    def keydiff(a, b):
        ra, rb = {x["key"]: x for x in docs[a]["rows"]}, {x["key"]: x for x in docs[b]["rows"]}
        out = set()
        for k in ra:
            if k not in rb:
                out.add(("scope_removed", k))
                continue
            if ra[k]["unit_price"] != rb[k]["unit_price"]:
                out.add(("unit_price", k))
            if ra[k]["qty"] != rb[k]["qty"]:
                out.add(("quantity", k))
            if ra[k]["delivery"] != rb[k]["delivery"]:
                out.add(("delivery_date", k))
        return out

    sc = {s["id"]: s for s in exp["scenarios"]}
    for sid, b in (("S1_normal", "revised"), ("S2_formatting_only", "reformatted")):
        want = {(c["type"], c["item_key"]) for c in sc[sid]["substantive_changes"] if c["item_key"]}
        check(keydiff("original", b) == want, f"{sid} : écarts par ligne = {sorted(want)}")
    s3 = {(c["type"], c["item_key"]) for c in sc["S3_ambiguous"]["substantive_changes"] if c["item_key"]}
    got3 = {x for x in keydiff("original", "ambiguous") if x[1] in ("ap", "screen", "dock", "install", "warranty")}
    check(got3 == s3, f"S3 : seuls changements non ambigus = {sorted(s3)}")
    s1 = sc["S1_normal"]
    check(len(s1["substantive_changes"]) == s1["expected_counts"]["confirmed_changes"], "S1 : nombre d'écarts attendus")
    delta = D(s1["net_effect"]["recomputed_delta"])
    parts = sum(D(c["line_total_delta"]) for c in s1["substantive_changes"] if c["item_key"])
    check(delta == parts, f"S1 : somme des écarts de lignes {parts} = écart recalculé {delta}")

    print()
    print("RÉSULTAT :", "tout est cohérent" if not fails else f"{len(fails)} échec(s)")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
