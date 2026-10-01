"""Tests de comparaison de bout en bout (PDF -> rapport) contre la vérité terrain écrite avant les tests."""
import json
import os
import sys
import unittest
from decimal import Decimal as D

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from offercompare.diff import compare_files  # noqa: E402

EXP = json.load(open(os.path.join(ROOT, "testset", "expected_differences.json"), encoding="utf-8"))
SC = {s["id"]: s for s in EXP["scenarios"]}
PDF = lambda n: os.path.join(ROOT, "testset", "pdf", n)  # noqa: E731
ORIG = PDF("offer_original.pdf")


def key_of_truth(c):
    if c["type"] == "stated_total":
        return ("stated_total", None, None)
    s = c["sources"]
    return (c["type"], s["original"]["row_number"] if s["original"] else None, s["revised"]["row_number"] if s["revised"] else None)


def key_of_report(c):
    if c["type"] == "stated_total":
        return ("stated_total", None, None)
    s = c["sources"]
    return (c["type"], int(s["original"]["row_number"]) if s["original"] else None,
            int(s["revised"]["row_number"]) if s["revised"] else None)


class TestS1(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rep = compare_files(ORIG, PDF("offer_revised.pdf"))
        cls.sc = SC["S1_normal"]

    def test_decision_and_counts(self):
        self.assertEqual(self.rep["decision"], "conclude")
        self.assertEqual(self.rep["summary"]["confirmed_changes"], self.sc["expected_counts"]["confirmed_changes"])
        self.assertEqual(self.rep["summary"]["arithmetic_discrepancies"], self.sc["expected_counts"]["arithmetic_discrepancies"])
        self.assertEqual(self.rep["uncertain"], [])

    def test_changes_match_truth_with_both_sources(self):
        want = {key_of_truth(c) for c in self.sc["substantive_changes"] if c["type"] != "stated_total"}
        got = {key_of_report(c) for c in self.rep["changes"] if c["type"] != "stated_total"}
        self.assertEqual(got, {(t, o, r) for t, o, r in {(t, o, r) for t, o, r in want}})
        truth_pages = {c["id"]: c for c in self.sc["substantive_changes"]}
        for tc in self.sc["substantive_changes"]:
            if tc["type"] == "stated_total":
                continue
            rc = next(c for c in self.rep["changes"] if key_of_report(c) == key_of_truth(tc))
            for side in ("original", "revised"):
                ts, rs = tc["sources"][side], rc["sources"][side]
                if ts is None:
                    self.assertIsNone(rs)
                    continue
                self.assertEqual((rs["page"], int(rs["row_number"])), (ts["page"], ts["row_number"]), (tc["id"], side))
                self.assertEqual(rs["label_text"], ts["label_text"])
                self.assertIsNotNone(rs["bbox"])
            self.assertEqual(D(rc["line_total_delta"]), D(tc["line_total_delta"]), tc["id"])
            if tc["type"] in ("unit_price", "quantity", "delivery_date"):
                self.assertEqual(rc["original"]["unit_price"], tc["original"]["unit_price"])
                self.assertEqual(rc["revised"]["delivery"], tc["revised"]["delivery"])
                self.assertIsNotNone(rc["sources"]["revised"]["cell"])   # cellule exacte à surligner

    def test_stated_total_and_arithmetic(self):
        st = next(c for c in self.rep["changes"] if c["type"] == "stated_total")
        tc = next(c for c in self.sc["substantive_changes"] if c["type"] == "stated_total")
        self.assertEqual(st["fields"]["ht"]["delta"], tc["stated_total_ht_delta"])
        self.assertEqual(st["sources"]["revised"]["page"], tc["sources"]["revised"]["page"])
        (a,), (ta,) = self.rep["arithmetic"], self.sc["arithmetic_discrepancies"]
        self.assertEqual((a["document"], a["scope"], a["stated"], a["recomputed"], a["difference"]),
                         (ta["document"], "total_ht", ta["stated"], ta["recomputed_from_lines"], ta["difference"]))
        self.assertEqual(a["source"]["page"], ta["sources"]["revised"]["page"])
        # on ne corrige jamais le document : le total affiché reste celui du PDF
        self.assertEqual(self.rep["documents"]["revised"]["stated_totals"]["ht"], "19060.00")
        self.assertEqual(self.rep["documents"]["revised"]["recomputed_totals"]["ht"], "18960.00")

    def test_net_effect_and_non_commercial(self):
        ne, tn = self.rep["net_effect"], self.sc["net_effect"]
        self.assertEqual(ne["recomputed_ht"]["delta"], tn["recomputed_delta"])
        self.assertEqual(ne["stated"]["ht"]["delta"], tn["stated_delta"])
        self.assertEqual(sum(D(c["line_total_delta"]) for c in self.rep["changes"] if c["type"] != "stated_total"), D(tn["recomputed_delta"]))
        nc = self.rep["non_commercial"]
        self.assertEqual([r["orig_index"] for r in nc["renamed"]], [1])
        self.assertTrue(nc["reordered"])
        types = {c["type"] for c in self.rep["changes"]}
        self.assertEqual(types, {"unit_price", "quantity", "scope_removed", "delivery_date", "stated_total"})


class TestOtherScenarios(unittest.TestCase):
    def test_s2_formatting_only_gives_nothing(self):
        rep = compare_files(ORIG, PDF("offer_original_reformatted.pdf"))
        self.assertEqual(rep["decision"], "no_changes")
        self.assertEqual((rep["changes"], rep["arithmetic"], rep["uncertain"]), ([], [], []))
        self.assertFalse(rep["non_commercial"]["reordered"])
        self.assertEqual(rep["non_commercial"]["renamed"], [])

    def test_s3_ambiguous_asks_instead_of_concluding(self):
        sc = SC["S3_ambiguous"]
        rep = compare_files(ORIG, PDF("offer_revised_ambiguous.pdf"))
        self.assertEqual(rep["decision"], "conclude_partially_and_ask")
        self.assertEqual(len(rep["uncertain"]), sc["required_clarifications"])
        self.assertEqual({key_of_report(c) for c in rep["changes"]}, {key_of_truth(c) for c in sc["substantive_changes"]})
        # jamais d'affirmation « prix passé de 1150 à 1290 » ni « ligne supprimée/ajoutée » pour les lignes douteuses
        self.assertFalse([c for c in rep["changes"] if c["type"] in ("scope_removed", "scope_added")])
        self.assertFalse([c for c in rep["changes"] if c["orig_index"] in (1, 4)])
        by_orig = {tuple(u["original"][i]["index"] for i in range(len(u["original"]))): u for u in rep["uncertain"]}
        self.assertEqual(by_orig[(1,)]["amount_at_stake"], {"original": "11500.00", "revised": "12060.00", "delta": "560.00"})
        self.assertEqual(by_orig[(4,)]["if_same_item"], [])    # même prix, quantité, date : simple renommage possible
        self.assertEqual(rep["arithmetic"], [])

    def test_s4_scanned_declines(self):
        rep = compare_files(ORIG, PDF("offer_revised_scanned.pdf"))
        self.assertEqual(rep["decision"], "decline")
        self.assertEqual(rep["decision_reasons"], ["no_text_layer_revised"])
        self.assertEqual((rep["changes"], rep["uncertain"], rep["arithmetic"], rep["net_effect"]), ([], [], [], None))

    def test_user_confirmation_recomputes_report(self):
        rep = compare_files(ORIG, PDF("offer_revised_ambiguous.pdf"), {"pairs": [[4, 5]]})
        self.assertEqual([u["id"] for u in rep["uncertain"]], ["U1"])    # il reste le portable scindé
        self.assertFalse([c for c in rep["changes"] if c["orig_index"] == 4])   # simple renommage : aucun écart

    def test_identical_documents(self):
        rep = compare_files(ORIG, ORIG)
        self.assertEqual((rep["decision"], rep["changes"], rep["arithmetic"]), ("no_changes", [], []))


if __name__ == "__main__":
    unittest.main(verbosity=2)
