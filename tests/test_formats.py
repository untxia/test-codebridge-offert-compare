"""Formats d'entrée : les mêmes offres (S0 -> S1) écrites en xlsx/docx/ods/csv/html/md/txt/json, et mélangées avec les PDF,
doivent donner les MÊMES écarts que la paire de PDF, avec une référence de source pour chaque document."""
import io
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from offercompare.diff import compare_files  # noqa: E402
from offercompare.readers import UnsupportedFormat, detect_kind  # noqa: E402

F = lambda n: os.path.join(ROOT, "testset", "formats", n)  # noqa: E731
PDF = lambda n: os.path.join(ROOT, "testset", "pdf", n)  # noqa: E731
EXTS = ["xlsx", "docx", "ods", "csv", "html", "md", "txt", "json"]


def signature(rep):
    """(type, ligne d'origine, ligne révisée) de chaque écart + montants : indépendant du format."""
    out = set()
    for c in rep["changes"]:
        if c["type"] == "stated_total":
            out.add(("stated_total", c["fields"]["ht"]["delta"]))
        else:
            s = c["sources"]
            out.add((c["type"], s["original"]["row_number"] if s["original"] else None,
                     s["revised"]["row_number"] if s["revised"] else None, c["line_total_delta"]))
    return out


class TestFormats(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ref = compare_files(PDF("offer_original.pdf"), PDF("offer_revised.pdf"))

    def test_each_format_matches_pdf_result(self):
        for ext in EXTS:
            with self.subTest(ext=ext):
                rep = compare_files(F(f"original.{ext}"), F(f"revised.{ext}"))
                self.assertEqual(rep["decision"], "conclude")
                self.assertEqual(signature(rep), signature(self.ref))
                self.assertEqual(rep["arithmetic"][0]["difference"], self.ref["arithmetic"][0]["difference"])
                self.assertEqual(rep["documents"]["revised"]["stated_totals"]["ht"], "19060.00")   # jamais corrigé
                for c in rep["changes"]:
                    for side in ("original", "revised"):
                        src = c["sources"][side]
                        if src:
                            self.assertEqual(src["kind"], "txt" if ext == "md" else ext)   # le Markdown est lu comme du texte
                            self.assertIn("style", src)
                            self.assertIsNotNone(src["bbox"])

    def test_mixed_formats(self):
        for a, b in (("original.xlsx", "revised.docx"), ("original.json", PDF("offer_revised.pdf")), ("original.csv", "revised.html")):
            with self.subTest(pair=(a, b)):
                rep = compare_files(F(a) if os.path.sep not in a else a, b if os.path.sep in b else F(b))
                self.assertEqual(signature(rep), signature(self.ref))
        rep = compare_files(PDF("offer_original.pdf"), F("revised.xlsx"))
        self.assertEqual(signature(rep), signature(self.ref))
        pdf_side = next(c for c in rep["changes"] if c["type"] == "unit_price")["sources"]
        self.assertNotIn("style", pdf_side["original"])        # PDF : page + zone
        self.assertEqual(pdf_side["revised"]["bbox"]["ref"], "Offre!A6:F6")   # Excel : référence A1 de la ligne

    def test_xlsx_cell_reference_and_real_dates(self):
        rep = compare_files(F("original.xlsx"), F("revised.xlsx"))
        d = next(c for c in rep["changes"] if c["type"] == "delivery_date")
        self.assertEqual(d["sources"]["revised"]["cell"]["ref"], "Offre!F8")
        self.assertEqual((d["from"], d["to"]), ("2026-11-16", "2026-11-30"))   # dates Excel : jamais ambiguës jj/mm

    def test_preview_returned_for_viewer(self):
        rep = compare_files(F("original.docx"), F("revised.docx"))
        pv = rep["documents"]["original"]["preview"]
        self.assertEqual(pv["kind"], "docx")
        self.assertIn("Écran 27 pouces QHD", [c for row in pv["tables"][0]["rows"] for c in row])
        self.assertIsNone(self.ref["documents"]["original"]["preview"])

    def test_formula_without_cached_value_is_not_guessed(self):
        import openpyxl
        wb = openpyxl.load_workbook(F("original.xlsx"))
        wb["Offre"]["E7"] = "=C7*D7"           # jamais calculé par Excel : pas de valeur enregistrée
        p = os.path.join(ROOT, "tests", "_tmp_formula.xlsx")
        wb.save(p)
        try:
            rep = compare_files(p, F("revised.xlsx"))
        finally:
            os.remove(p)
        self.assertTrue(any("formule" in w for w in rep["documents"]["original"]["warnings"]))

    def test_unsupported_and_unreadable(self):
        self.assertEqual(detect_kind(b"\x89PNG\r\n\x1a\n" + b"0" * 50, "x.png"), "image")
        with self.assertRaises(UnsupportedFormat):
            detect_kind(b"\xd0\xcf\x11\xe0" + b"0" * 50, "x.xls")
        with self.assertRaises(UnsupportedFormat):
            detect_kind(b"PK\x03\x04" + b"junk", "x.zip")

    def test_image_declines(self):
        from PIL import Image
        p = os.path.join(ROOT, "tests", "_tmp.png")
        Image.new("RGB", (80, 40), "white").save(p)
        try:
            rep = compare_files(p, F("revised.csv"))
        finally:
            os.remove(p)
        self.assertEqual(rep["decision"], "decline")
        self.assertIn("no_text_layer_original", rep["decision_reasons"])

    def test_text_without_table_declines(self):
        p = os.path.join(ROOT, "tests", "_tmp.txt")
        with open(p, "w") as fh:
            fh.write("Bonjour, voici notre offre : un prix à discuter.")
        try:
            rep = compare_files(p, F("revised.csv"))
        finally:
            os.remove(p)
        self.assertEqual(rep["decision"], "decline")
        self.assertIn("no_line_items_original", rep["decision_reasons"])


if __name__ == "__main__":
    unittest.main()
