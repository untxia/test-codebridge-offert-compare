#!/usr/bin/env python3
"""Évaluation de bout en bout : compare la sortie de l'application à la vérité terrain (testset/expected_differences.json).

Mesure : écarts manqués, faux écarts, bon traitement des cas incertains / à refuser, anomalies arithmétiques,
exactitude des références sources (page + ligne + libellé, puis contrôle INDÉPENDANT : le texte situé sous la bbox
renvoyée dans le PDF contient bien la ligne ou le montant cité), temps de traitement.
Usage : python3 evaluation/evaluate.py   (écrit evaluation/results.json et affiche un résumé)
"""
import json, os, re, statistics, sys
import pdfplumber

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from offercompare.diff import compare_files  # noqa: E402

TS = os.path.join(ROOT, "testset")
EXP = json.load(open(os.path.join(TS, "expected_differences.json"), encoding="utf-8"))
REPEATS = 5


def exp_ref(s):
    if not s:
        return None
    return ("totals", s["page"]) if s.get("block") == "totals" else (int(s["row_number"]), s["page"])


def act_ref(s):
    if not s:
        return None
    return ("totals", s["page"]) if s.get("block") == "totals" else (int(s["row_number"]), s["page"])


def bbox_text_ok(pdf_dir, src):
    """Contrôle indépendant : le texte sous la bbox contient le numéro de ligne + début du libellé, ou le montant brut."""
    path = os.path.join(pdf_dir, src["file"])
    b = src["bbox"]
    with pdfplumber.open(path) as pdf:
        page = pdf.pages[src["page"] - 1]
        txt = (page.crop((max(b["x0"] - 1, 0), max(b["top"] - 1, 0), min(b["x1"] + 1, page.width), min(b["bottom"] + 1, page.height))).extract_text() or "")
    txt = txt.replace(" ", " ").replace("\xa0", " ")
    if src.get("block") == "totals":
        digits = re.sub(r"\D", "", src.get("raw") or "")
        return bool(digits) and digits in re.sub(r"\D", "", txt)
    first = (src["label_text"].split() or [""])[0]
    return first.lower() in txt.lower()


def run():
    out, tot = [], dict(expected=0, found=0, missed=0, false=0, refs=0, refs_ok=0, bbox=0, bbox_ok=0)
    for sc in EXP["scenarios"]:
        o, r = os.path.join(TS, sc["original"]), os.path.join(TS, sc["revised"])
        times, rep = [], None
        for _ in range(REPEATS):
            rep = compare_files(o, r)
            times.append(rep["total_ms"])
        exp_set = {(c["type"], exp_ref(c["sources"].get("original")), exp_ref(c["sources"].get("revised"))) for c in sc["substantive_changes"]}
        act_set = {(c["type"], act_ref(c["sources"].get("original")), act_ref(c["sources"].get("revised"))) for c in rep["changes"]}
        missed, false = sorted(map(str, exp_set - act_set)), sorted(map(str, act_set - exp_set))
        # références sources : chaque écart doit citer les DEUX emplacements attendus ; bbox vérifiée dans le PDF
        refs = refs_ok = bb = bb_ok = 0
        for c in rep["changes"]:
            for side, pdf in (("original", o), ("revised", r)):
                s = c["sources"].get(side)
                if s is None:
                    continue
                bb += 1
                bb_ok += bbox_text_ok(os.path.dirname(pdf), {**s, "file": os.path.basename(pdf)})
        for c in sc["substantive_changes"]:
            got = next((a for a in rep["changes"] if a["type"] == c["type"] and act_ref(a["sources"].get("original")) == exp_ref(c["sources"].get("original"))
                        and act_ref(a["sources"].get("revised")) == exp_ref(c["sources"].get("revised"))), None)
            for side in ("original", "revised"):
                if c["sources"].get(side):
                    refs += 1
                    if got and got["sources"].get(side) and (got["sources"][side].get("label_text") or "") .lower() == c["sources"][side]["label_text"].lower():
                        refs_ok += 1
                    elif got and got["sources"].get(side) and c["sources"][side].get("block") == "totals":
                        refs_ok += 1
        exp_unc = sorted((u["original_row"], tuple(u["revised_rows"])) for u in sc["uncertain_matches"] if "original_row" in u) if sc["uncertain_matches"] else []
        act_unc = sorted((tuple(l["index"] for l in g["original"]), tuple(l["index"] for l in g["revised"])) for g in rep["uncertain"])
        exp_unc_n = sc["expected_counts"].get("uncertain_items", 0)
        arith_ok = len(rep["arithmetic"]) == sc["expected_counts"]["arithmetic_discrepancies"]
        if sc["arithmetic_discrepancies"] and rep["arithmetic"]:
            a, e = rep["arithmetic"][0], sc["arithmetic_discrepancies"][0]
            arith_ok = arith_ok and a["stated"] == e["stated"] and a["recomputed"] == e["recomputed_from_lines"]
        row = dict(scenario=sc["id"], expected_decision=sc["expected_decision"], decision=rep["decision"],
                   decision_ok=rep["decision"] == sc["expected_decision"],
                   expected_changes=len(exp_set), found=len(exp_set & act_set), missed=missed, false_changes=false,
                   uncertain_expected=exp_unc_n, uncertain_found=len(rep["uncertain"]), uncertain_ok=len(rep["uncertain"]) == exp_unc_n,
                   arithmetic_ok=arith_ok, source_refs=refs, source_refs_ok=refs_ok, bbox_checked=bb, bbox_text_ok=bb_ok,
                   non_commercial_listed=len(rep.get("non_commercial") or []),
                   ms_median=round(statistics.median(times), 1), ms_max=round(max(times), 1))
        out.append(row)
        tot["expected"] += len(exp_set); tot["found"] += len(exp_set & act_set); tot["missed"] += len(missed); tot["false"] += len(false)
        tot["refs"] += refs; tot["refs_ok"] += refs_ok; tot["bbox"] += bb; tot["bbox_ok"] += bb_ok
    return out, tot


def holdout():
    """Jeu hold-out (écrit après le développement). Attendus : 5 écarts de lignes + total, 0 faux, renommage/réordonnancement non signalés."""
    H = os.path.join(ROOT, "evaluation", "holdout")
    want = {"unit_price": "10GbE network card dual port", "quantity": "NVMe SSD 2TB enterprise", "delivery_date": "Extended warranty 3 years",
            "scope_removed": "Rack mounting rail kit", "scope_added": "UPS 3kVA rack battery backup", "stated_total": None}
    res = []
    for h in ("h1", "h2"):
        rep = compare_files(os.path.join(H, f"{h}_original.pdf"), os.path.join(H, f"{h}_revised.pdf"))
        got = {}
        for c in rep["changes"]:
            side = c["revised"] if c["type"] == "scope_added" else c.get("original")
            got[c["type"]] = (side or {}).get("label") if c["type"] != "stated_total" else None
        missed = sorted(set(want) - set(got)); false = sorted(k for k in got if k not in want or got[k] != want[k])
        res.append(dict(doc=h, decision=rep["decision"], expected=len(want), found=len(want) - len(missed), missed=missed, false_changes=false,
                        uncertain=len(rep["uncertain"]), arithmetic=len(rep["arithmetic"]), ms=rep["total_ms"]))
    return res


if __name__ == "__main__":
    rows, tot = run()
    ho = holdout()
    res = dict(scenarios=rows, totals=tot, holdout=ho, repeats=REPEATS)
    json.dump(res, open(os.path.join(ROOT, "evaluation", "results.json"), "w"), ensure_ascii=False, indent=1)
    for r in rows:
        print(f"{r['scenario']:20s} decision {r['decision']:26s} {'OK' if r['decision_ok'] else 'KO'} | écarts {r['found']}/{r['expected_changes']} manqués={len(r['missed'])} faux={len(r['false_changes'])} "
              f"| incertains {r['uncertain_found']}/{r['uncertain_expected']} | arith {'OK' if r['arithmetic_ok'] else 'KO'} | refs {r['source_refs_ok']}/{r['source_refs']} | bbox {r['bbox_text_ok']}/{r['bbox_checked']} | {r['ms_median']} ms")
        for m in r["missed"]: print("   MANQUÉ", m)
        for m in r["false_changes"]: print("   FAUX  ", m)
    print("TOTAL", tot)
    for h in ho: print("HOLDOUT", h)
    sys.exit(0 if tot["missed"] == 0 and tot["false"] == 0 and all(h["found"] == h["expected"] and not h["false_changes"] and h["decision"] == "conclude" for h in ho) and all(r["decision_ok"] and r["arithmetic_ok"] and r["uncertain_ok"] for r in rows) else 1)
