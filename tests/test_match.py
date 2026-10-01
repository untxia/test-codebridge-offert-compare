"""Tests d'appariement : vérité terrain du jeu de test + cas synthétiques (ajout, doublons, décisions utilisateur)."""
import json
import os
import sys
import unittest
from decimal import Decimal as D

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from offercompare.extract import extract_offer  # noqa: E402
from offercompare.match import match_offers  # noqa: E402
from offercompare.models import BBox, Item, Offer, Totals  # noqa: E402

EXP = json.load(open(os.path.join(ROOT, "testset", "expected_differences.json"), encoding="utf-8"))
SC = {s["id"]: s for s in EXP["scenarios"]}
PDF = lambda n: os.path.join(ROOT, "testset", "pdf", n)  # noqa: E731


def mk(rows):
    """rows: [(label, qty, price, delivery)] -> Offer synthétique."""
    items = []
    for i, (label, qty, price, dl) in enumerate(rows, 1):
        items.append(Item(index=i, printed_no=str(i), label=label, qty=D(qty), unit="", unit_price=D(price),
                          line_total=D(qty) * D(price), delivery=dl, delivery_is_date=True, page=1,
                          bbox=BBox(1, 0, 0, 1, 1)))
    return Offer(file="x", pages=[], has_text_layer=True, items=items, totals=Totals(), currency="EUR",
                 currencies_seen={}, method="test")


class TestTruth(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.orig = extract_offer(PDF("offer_original.pdf"))

    def test_s1_normal(self):
        m = match_offers(self.orig, extract_offer(PDF("offer_revised.pdf")))
        want = {(x["original_row"], x["revised_row"]) for x in SC["S1_normal"]["matches"] if x["status"] == "confirmed"}
        self.assertEqual({(p.orig, p.rev) for p in m.pairs}, want)
        self.assertEqual(m.removed, [x["original_row"] for x in SC["S1_normal"]["matches"] if x["status"] == "removed"])
        self.assertEqual((m.added, m.uncertain), ([], []))
        renamed = [p.orig for p in m.pairs if p.label_changed]
        self.assertEqual(renamed, [1])          # seul le portable est renommé

    def test_s2_formatting_only(self):
        m = match_offers(self.orig, extract_offer(PDF("offer_original_reformatted.pdf")))
        self.assertEqual([(p.orig, p.rev) for p in m.pairs], [(i, i) for i in range(1, 9)])
        self.assertFalse(any(p.label_changed for p in m.pairs))
        self.assertEqual((m.removed, m.added, m.uncertain), ([], [], []))

    def test_s3_ambiguous(self):
        sc = SC["S3_ambiguous"]
        m = match_offers(self.orig, extract_offer(PDF("offer_revised_ambiguous.pdf")))
        # incertains : exactement ceux attendus, jamais présentés comme confirmés
        got = sorted((tuple(u.orig), tuple(u.rev)) for u in m.uncertain)
        want = sorted(((x["original_row"],), tuple(x["revised_rows"])) for x in sc["uncertain_matches"])
        self.assertEqual(got, want)
        confirmed = {(p.orig, p.rev) for p in m.pairs}
        for x in sc["matches"]:   # confirmés attendus (le switch renommé est accepté confirmé ou incertain)
            if x["status"] == "confirmed":
                self.assertIn((x["original_row"], x["revised_row"]), confirmed)
        for u in sc["uncertain_matches"]:
            self.assertNotIn(u["original_row"], {p.orig for p in m.pairs})
        self.assertEqual((m.removed, m.added), ([], []))
        self.assertEqual(sc["required_clarifications"], len(m.uncertain))


class TestSynthetic(unittest.TestCase):
    def test_price_and_qty_changes_stay_confirmed(self):
        a = mk([("Switch 24 ports", 2, "320", "2026-11-20"), ("Borne Wi-Fi", 4, "180", "2026-11-20")])
        b = mk([("Switch 24 ports", 3, "400", "2026-12-01"), ("Borne Wi-Fi", 4, "180", "2026-11-20")])
        m = match_offers(a, b)
        self.assertEqual([(p.orig, p.rev) for p in m.pairs], [(1, 1), (2, 2)])

    def test_added_line(self):
        a = mk([("Ecran 27 pouces", 10, "280", "2026-11-16")])
        b = mk([("Ecran 27 pouces", 10, "280", "2026-11-16"), ("Support ecran double", 5, "95", "2026-12-05")])
        m = match_offers(a, b)
        self.assertEqual(([(p.orig, p.rev) for p in m.pairs], m.added, m.removed), ([(1, 1)], [2], []))

    def test_reordering_does_not_matter(self):
        rows = [("Ecran 27 pouces", 10, "280", "2026-11-16"), ("Station accueil USB-C", 10, "135", "2026-11-16"),
                ("Borne Wi-Fi 6", 4, "180", "2026-11-20"), ("Garantie 3 ans", 10, "60", "2026-11-23")]
        m = match_offers(mk(rows), mk(list(reversed(rows))))
        self.assertEqual({(p.orig, p.rev) for p in m.pairs}, {(1, 4), (2, 3), (3, 2), (4, 1)})

    def test_duplicate_labels_are_not_guessed(self):
        """Deux lignes au libellé identique et aux conditions voisines : ne pas inventer un appariement sûr."""
        a = mk([("Licence logiciel", 5, "100", "2026-11-16"), ("Licence logiciel", 5, "100", "2026-11-16")])
        b = mk([("Licence logiciel", 5, "100", "2026-11-16"), ("Licence logiciel", 5, "100", "2026-11-16")])
        m = match_offers(a, b)
        self.assertEqual(len(m.pairs) + sum(len(u.orig) for u in m.uncertain), 2)  # tout est traité, rien de perdu
        self.assertEqual((m.removed, m.added), ([], []))

    def test_user_override_resolves_ambiguity(self):
        orig = extract_offer(PDF("offer_original.pdf"))
        rev = extract_offer(PDF("offer_revised_ambiguous.pdf"))
        m = match_offers(orig, rev, {"pairs": [[4, 5]], "removed": [1], "added": [1, 2]})
        self.assertIn((4, 5), {(p.orig, p.rev) for p in m.pairs})
        self.assertEqual([p.basis for p in m.pairs if (p.orig, p.rev) == (4, 5)], ["user"])
        self.assertEqual((m.uncertain, m.removed, m.added), ([], [1], [1, 2]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
