"""Tests d'extraction : lecture des PDF du jeu de test comparée à la vérité terrain (expected_differences.json),
tolérance de formats, robustesse sans traits de tableau, détection du scan."""
import json
import os
import sys
import tempfile
import unittest
from decimal import Decimal as D

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "testset"))

from offercompare.extract import extract_offer  # noqa: E402
from offercompare.parsing import parse_date, parse_money, parse_qty  # noqa: E402

TRUTH = json.load(open(os.path.join(ROOT, "testset", "expected_differences.json"), encoding="utf-8"))["documents"]


def check_against_truth(tc, offer, truth):
    tc.assertTrue(offer.has_text_layer)
    tc.assertEqual(len(offer.items), truth["line_items"])
    for it, t in zip(offer.items, truth["rows"]):
        tc.assertEqual(it.label, t["label"])
        tc.assertEqual(it.page, t["page"], t["label"])
        tc.assertEqual(it.printed_no, str(t["row_number"]))
        q = t["qty"].split()
        tc.assertEqual(it.qty, D(q[0]))
        tc.assertEqual(it.unit, q[1] if len(q) > 1 else "")
        tc.assertEqual(it.unit_price, D(t["unit_price"]))
        tc.assertEqual(it.line_total, D(t["line_total"]))
        tc.assertEqual(it.delivery, t["delivery"])
        tc.assertEqual(it.warnings, [])
        tc.assertTrue(it.bbox.x1 > it.bbox.x0 and it.bbox.bottom > it.bbox.top)
        for role in ("label", "qty", "unit_price", "line_total", "delivery"):
            tc.assertIn(role, it.cells)
    for k, attr in (("ht", "ht"), ("tva", "vat"), ("ttc", "ttc")):
        m = getattr(offer.totals, attr)
        tc.assertIsNotNone(m, k)
        tc.assertEqual(m.value, D(truth["stated_totals"][k]))
        tc.assertEqual(m.bbox.page, 2)
    tc.assertEqual(offer.totals.vat_rate, D("0.20"))
    tc.assertEqual(offer.currency, "EUR")


class TestParsing(unittest.TestCase):
    def test_money(self):
        cases = {"1 150,00 €": "1150.00", "1 150,00 €": "1150.00", "EUR 1 150,00": "1150.00",
                 "1,150.00": "1150.00", "1.150,00 €": "1150.00", "€1,150.00": "1150.00", "12,5": "12.5",
                 "1150": "1150", "-45,00": "-45.00", "1,150": "1150", "2 950,00": "2950.00"}
        for s, v in cases.items():
            self.assertEqual(parse_money(s), D(v), s)
        for s in ("", "abc", "À réception", "16/11/2026", None):
            self.assertIsNone(parse_money(s), s)

    def test_dates(self):
        for s in ("16/11/2026", "16 novembre 2026", "16 nov. 2026", "2026-11-16", "16.11.26", "le 16 novembre 2026",
                  "November 16, 2026", "16 November 2026"):
            self.assertEqual(parse_date(s), "2026-11-16", s)
        for s in ("À réception", "sous 15 jours", "31/02/2026", ""):
            self.assertIsNone(parse_date(s), s)

    def test_qty(self):
        self.assertEqual(parse_qty("10"), (D("10"), ""))
        self.assertEqual(parse_qty("12 h"), (D("12"), "h"))
        self.assertEqual(parse_qty("2,5 j"), (D("2.5"), "j"))
        self.assertEqual(parse_qty("x 3"), (D("3"), ""))
        self.assertEqual(parse_qty("abc"), (None, ""))


class TestExtraction(unittest.TestCase):
    def test_all_text_documents_match_truth(self):
        for name, truth in TRUTH.items():
            with self.subTest(doc=name):
                offer = extract_offer(os.path.join(ROOT, "testset", truth["file"]))
                self.assertEqual(offer.method, "pdfplumber/lines")
                check_against_truth(self, offer, truth)

    def test_scanned_has_no_text_layer(self):
        offer = extract_offer(os.path.join(ROOT, "testset", "pdf", "offer_revised_scanned.pdf"))
        self.assertFalse(offer.has_text_layer)
        self.assertEqual(offer.items, [])
        self.assertTrue(any("couche texte" in w for w in offer.warnings))
        self.assertTrue(all(p.n_images >= 1 for p in offer.pages))

    def test_text_fallback_without_table_lines(self):
        """Même contenu, tableau SANS traits : doit passer par la stratégie « text »."""
        import generate_testset as g
        for name in ("original", "revised"):
            with self.subTest(doc=name):
                o = dict(g.OFFERS[name])
                o["style"] = dict(o["style"], grid=False)
                with tempfile.TemporaryDirectory() as td:
                    path = os.path.join(td, "nogrid.pdf")
                    g.build_pdf(path, o)
                    offer = extract_offer(path)
                self.assertEqual(offer.method, "pdfplumber/words")
                check_against_truth(self, offer, TRUTH[name])


if __name__ == "__main__":
    unittest.main(verbosity=2)
