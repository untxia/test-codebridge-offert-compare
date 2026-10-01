#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Génère le jeu de test « comparaison d'offres commerciales » (matériel informatique, fictif).

Sorties (dans ce dossier) :
  pdf/offer_original.pdf               offre de départ
  pdf/offer_revised.pdf                révision avec les écarts attendus (S1)
  pdf/offer_original_reformatted.pdf   même contenu que l'original, mise en forme différente (S2)
  pdf/offer_revised_ambiguous.pdf      révision ambiguë : ligne scindée, renommages vagues (S3)
  pdf/offer_revised_scanned.pdf        révision « scannée » sans couche texte : on doit refuser de conclure (S4)
  expected_differences.json            résultats attendus, écrits AVANT tout test de l'application

Les PDF et la vérité terrain sortent du MÊME modèle de données : reproductible, déterministe.
Dépendances : reportlab, pdfplumber (et Pillow, installé avec reportlab).
"""
import io
import json
import os
import random
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

from reportlab import rl_config

rl_config.invariant = 1  # PDF reproductibles (pas de date de création variable)

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas as rl_canvas
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

HERE = os.path.dirname(os.path.abspath(__file__))
PDF_DIR = os.path.join(HERE, "pdf")
D = Decimal
CENT = D("0.01")
VAT_RATE = D("0.20")


# --------------------------------------------------------------------------- données
@dataclass(frozen=True)
class Row:
    key: str       # identifiant interne (vérité terrain uniquement, jamais imprimé dans les PDF)
    label: str
    qty: Decimal
    unit: str      # "" ou "h"
    price: Decimal
    delivery: str  # date ISO ou texte libre

    @property
    def total(self):
        return (self.qty * self.price).quantize(CENT)


def r(key, label, qty, price, delivery, unit=""):
    return Row(key, label, D(qty), unit, D(price), delivery)


D1, D2, D3, RECEPTION = "2026-11-16", "2026-11-20", "2026-11-23", "À réception"

ORIGINAL = [
    r("laptop", "Ordinateur portable 15 pouces Pro", 10, "1150.00", D1),
    r("screen", "Écran 27 pouces QHD", 10, "280.00", D1),
    r("dock", "Station d'accueil USB-C", 10, "135.00", D1),
    r("kbm", "Clavier et souris sans fil", 10, "45.00", D1),
    r("switch", "Switch réseau 24 ports", 2, "320.00", D2),
    r("ap", "Borne Wi-Fi 6", 4, "180.00", D2),
    r("install", "Installation et configuration", 12, "70.00", D3, unit="h"),
    r("warranty", "Garantie 3 ans sur site", 10, "60.00", RECEPTION),
]

# S1 : renommage (laptop), lignes réordonnées, prix (screen), quantité (ap),
#      ligne supprimée (kbm), date (dock) ; total HT affiché volontairement faux.
REVISED = [
    r("screen", "Écran 27 pouces QHD", 10, "295.00", D1),
    r("laptop", "PC portable professionnel 15 pouces", 10, "1150.00", D1),
    r("dock", "Station d'accueil USB-C", 10, "135.00", "2026-11-30"),
    r("ap", "Borne Wi-Fi 6", 6, "180.00", D2),
    r("switch", "Switch réseau 24 ports", 2, "320.00", D2),
    r("install", "Installation et configuration", 12, "70.00", D3, unit="h"),
    r("warranty", "Garantie 3 ans sur site", 10, "60.00", RECEPTION),
]

# S3 : ligne scindée en deux (config différente, prix différent), « Pack accessoires » vague,
#      « Équipement réseau » renommé, et un changement net (ap 4 -> 5).
AMBIGUOUS = [
    r("laptop_a", "PC portable Pro 15 - config standard", 6, "1150.00", D1),
    r("laptop_b", "PC portable Pro 15 - config renforcée 32 Go", 4, "1290.00", D1),
    r("screen", "Écran 27 pouces QHD", 10, "280.00", D1),
    r("dock", "Station d'accueil USB-C", 10, "135.00", D1),
    r("pack", "Pack accessoires bureau", 10, "45.00", D1),
    r("switch", "Équipement réseau 24 ports", 2, "320.00", D2),
    r("ap", "Borne Wi-Fi 6", 5, "180.00", D2),
    r("install", "Installation et configuration", 12, "70.00", D3, unit="h"),
    r("warranty", "Garantie 3 ans sur site", 10, "60.00", RECEPTION),
]


def sum_lines(rows):
    return sum((x.total for x in rows), D("0.00")).quantize(CENT)


def totals_from_ht(ht):
    tva = (ht * VAT_RATE).quantize(CENT, rounding=ROUND_HALF_UP)
    return {"ht": ht.quantize(CENT), "tva": tva, "ttc": (ht + tva).quantize(CENT)}


# --------------------------------------------------------------------------- formats
MONTHS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août",
          "septembre", "octobre", "novembre", "décembre"]


def _num_fr(v, sep):
    s = f"{v.quantize(CENT):,.2f}"
    return s.replace(",", "§").replace(".", ",").replace("§", sep)


def money_a(v):   # 1 150,00 €  (espace insécable, comme dans beaucoup de PDF réels)
    return _num_fr(v, " ") + " €"


def money_b(v):   # EUR 1 150,00 (espace simple, devise en préfixe)
    return "EUR " + _num_fr(v, " ")


def date_a(s):
    if len(s) == 10 and s[4] == "-":
        return f"{s[8:10]}/{s[5:7]}/{s[0:4]}"
    return s


def date_b(s):
    if len(s) == 10 and s[4] == "-":
        return f"{int(s[8:10])} {MONTHS[int(s[5:7]) - 1]} {s[0:4]}"
    return s


STYLE_A = dict(
    name="A", font="Helvetica", bold="Helvetica-Bold", size=9, head_bg=colors.HexColor("#1F3A5F"),
    head_fg=colors.white, zebra=None, money=money_a, date=date_a,
    title="OFFRE COMMERCIALE", title_align=TA_LEFT,
    columns=["N°", "Désignation", "Qté", "Prix unitaire HT", "Total HT", "Livraison"],
    widths=[10, 66, 18, 28, 26, 26],
    totals_labels={"ht": "Total HT", "tva": "TVA 20 %", "ttc": "Total TTC"},
)
STYLE_B = dict(
    name="B", font="Times-Roman", bold="Times-Bold", size=10, head_bg=colors.HexColor("#2E6B4F"),
    head_fg=colors.white, zebra=colors.HexColor("#EEF3EF"), money=money_b, date=date_b,
    title="Offre commerciale", title_align=TA_CENTER,
    columns=["Pos.", "Description", "Quantité", "PU HT", "Montant HT", "Date de livraison"],
    widths=[12, 54, 18, 28, 28, 34],
    totals_labels={"ht": "TOTAL HT", "tva": "TVA 20 %", "ttc": "TOTAL TTC"},
)

SUPPLIER = "Nordika Systèmes SAS"
CLIENT = "Atelier Lumière SARL"
OFFER_REF = "OFF-2026-0412"
CONDITIONS = ("Conditions : paiement à 30 jours fin de mois. Prix en euros (EUR), hors taxes sauf mention "
              "contraire. Offre soumise à la disponibilité du matériel.")
FICTIVE = "Document fictif généré pour un jeu de test. Les sociétés citées n'existent pas."

OFFERS = {
    "original": dict(file="offer_original.pdf", rows=ORIGINAL, break_after=5, style=STYLE_A, version="A", ht=None),
    "revised": dict(file="offer_revised.pdf", rows=REVISED, break_after=4, style=STYLE_B, version="B",
                    ht=sum_lines(REVISED) + D("100.00")),  # total HT faux : +100,00
    "reformatted": dict(file="offer_original_reformatted.pdf", rows=ORIGINAL, break_after=5, style=STYLE_B,
                        version="A", ht=None),
    "ambiguous": dict(file="offer_revised_ambiguous.pdf", rows=AMBIGUOUS, break_after=5, style=STYLE_B,
                      version="B", ht=None),
}


def stated_totals(o):
    return totals_from_ht(o["ht"] if o["ht"] is not None else sum_lines(o["rows"]))


# --------------------------------------------------------------------------- rendu PDF
def _styles(st):
    f, b, s = st["font"], st["bold"], st["size"]
    return dict(
        left=ParagraphStyle("l", fontName=f, fontSize=s, leading=s + 2, alignment=TA_LEFT),
        right=ParagraphStyle("r", fontName=f, fontSize=s, leading=s + 2, alignment=TA_RIGHT),
        hl=ParagraphStyle("hl", fontName=b, fontSize=s - 0.5, leading=s + 1, alignment=TA_LEFT, textColor=st["head_fg"]),
        hr=ParagraphStyle("hr", fontName=b, fontSize=s - 0.5, leading=s + 1, alignment=TA_RIGHT, textColor=st["head_fg"]),
        title=ParagraphStyle("t", fontName=b, fontSize=s + 8, leading=s + 12, alignment=st["title_align"], spaceAfter=6),
        meta=ParagraphStyle("m", fontName=f, fontSize=s, leading=s + 3),
        small=ParagraphStyle("sm", fontName=f, fontSize=s - 1.5, leading=s + 1, textColor=colors.HexColor("#555555")),
        bold_r=ParagraphStyle("br", fontName=b, fontSize=s, leading=s + 2, alignment=TA_RIGHT),
    )


def _items_table(rows, start_no, st, ps):
    data = [[Paragraph(h, ps["hr"] if i in (2, 3, 4) else ps["hl"]) for i, h in enumerate(st["columns"])]]
    for i, row in enumerate(rows, start=start_no):
        qty = f"{int(row.qty)}" + (f" {row.unit}" if row.unit else "")
        data.append([
            Paragraph(str(i), ps["left"]), Paragraph(row.label, ps["left"]), Paragraph(qty, ps["right"]),
            Paragraph(st["money"](row.price), ps["right"]), Paragraph(st["money"](row.total), ps["right"]),
            Paragraph(st["date"](row.delivery), ps["left"]),
        ])
    t = Table(data, colWidths=[w * mm for w in st["widths"]], repeatRows=1)
    cmds = [("BACKGROUND", (0, 0), (-1, 0), st["head_bg"]),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]
    if st.get("grid", True):
        cmds.append(("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#999999")))
    if st["zebra"] is not None:
        for k in range(2, len(data), 2):
            cmds.append(("BACKGROUND", (0, k), (-1, k), st["zebra"]))
    t.setStyle(TableStyle(cmds))
    return t


def build_pdf(path, o):
    st, rows, brk = o["style"], o["rows"], o["break_after"]
    ps = _styles(st)
    tot = stated_totals(o)
    doc = SimpleDocTemplate(path, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=18 * mm,
                            bottomMargin=18 * mm, title=f"Offre {OFFER_REF} v{o['version']}", author="Jeu de test (fictif)")
    story = [Paragraph(st["title"], ps["title"]),
             Paragraph(f"Fournisseur : {SUPPLIER}", ps["meta"]), Paragraph(f"Client : {CLIENT}", ps["meta"]),
             Paragraph(f"Offre n° {OFFER_REF} - Version : {o['version']}", ps["meta"]),
             Paragraph("Devise : EUR", ps["meta"]), Spacer(1, 8 * mm),
             _items_table(rows[:brk], 1, st, ps), PageBreak(),
             Paragraph(f"Offre n° {OFFER_REF} (suite)", ps["meta"]), Spacer(1, 4 * mm),
             _items_table(rows[brk:], brk + 1, st, ps), Spacer(1, 6 * mm)]
    lab = st["totals_labels"]
    tdata = [[Paragraph(lab[k], ps["bold_r"] if k == "ttc" else ps["right"]),
              Paragraph(st["money"](tot[k]), ps["bold_r"] if k == "ttc" else ps["right"])] for k in ("ht", "tva", "ttc")]
    tt = Table(tdata, colWidths=[110 * mm, 64 * mm])
    tcmds = [("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]
    if st.get("grid", True):
        tcmds.append(("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#999999")))
    tt.setStyle(TableStyle(tcmds))
    story += [tt, Spacer(1, 8 * mm), Paragraph(CONDITIONS, ps["meta"]), Spacer(1, 6 * mm), Paragraph(FICTIVE, ps["small"])]
    doc.build(story)


def build_scanned(src_pdf, dst_pdf, seed=7):
    """Rastérise le PDF source en images (légère rotation + bruit) : aucune couche texte."""
    import pdfplumber
    from PIL import Image, ImageFilter

    rnd = random.Random(seed)
    c = rl_canvas.Canvas(dst_pdf, pagesize=A4, invariant=1)
    with pdfplumber.open(src_pdf) as pdf:
        for page in pdf.pages:
            img = page.to_image(resolution=110).original.convert("L")
            img = img.rotate(0.6, expand=True, fillcolor=235, resample=Image.BICUBIC).filter(ImageFilter.GaussianBlur(0.6))
            px = img.load()
            for _ in range(img.width * img.height // 40):
                x, y = rnd.randrange(img.width), rnd.randrange(img.height)
                px[x, y] = max(0, min(255, px[x, y] + rnd.randint(-25, 25)))
            buf = io.BytesIO()
            img.save(buf, "JPEG", quality=70)
            buf.seek(0)
            c.drawImage(ImageReader(buf), 0, 0, width=A4[0], height=A4[1])
            c.showPage()
    c.save()


# --------------------------------------------------------------------------- vérité terrain
def pos(name, key):
    return [x.key for x in OFFERS[name]["rows"]].index(key) + 1


def rowof(name, key):
    return OFFERS[name]["rows"][pos(name, key) - 1]


def rref(name, key):
    o, n, row = OFFERS[name], pos(name, key), rowof(name, key)
    return {"file": "pdf/" + o["file"], "page": 1 if n <= o["break_after"] else 2, "row_number": n, "label_text": row.label}


def tref(name):
    o = OFFERS[name]
    return {"file": "pdf/" + o["file"], "page": 2, "block": "totals", "label_text": o["style"]["totals_labels"]["ht"]}


def vals(row):
    return {"qty": str(int(row.qty)) + (f" {row.unit}" if row.unit else ""), "unit_price": str(row.price),
            "line_total": str(row.total), "delivery": row.delivery}


def doc_truth(name):
    o = OFFERS[name]
    tot, rec = stated_totals(o), totals_from_ht(sum_lines(o["rows"]))
    return {
        "file": "pdf/" + o["file"], "version_label": o["version"], "pages": 2, "line_items": len(o["rows"]),
        "rows": [dict(row_number=i, page=1 if i <= o["break_after"] else 2, key=x.key, label=x.label, **vals(x))
                 for i, x in enumerate(o["rows"], 1)],
        "stated_totals": {k: str(v) for k, v in tot.items()},
        "recomputed_totals_from_lines": {k: str(v) for k, v in rec.items()},
        "arithmetic_consistent": tot["ht"] == rec["ht"],
    }


def change(cid, ctype, key, o_name="original", r_name="revised", **extra):
    c = {"id": cid, "type": ctype, "item_key": key}
    c.update(extra)
    c["sources"] = {"original": rref(o_name, key) if key in [x.key for x in OFFERS[o_name]["rows"]] else None,
                    "revised": rref(r_name, key) if key in [x.key for x in OFFERS[r_name]["rows"]] else None}
    return c


def build_expected():
    o_s, r_s = rowof("original", "screen"), rowof("revised", "screen")
    o_a, r_a = rowof("original", "ap"), rowof("revised", "ap")
    o_k = rowof("original", "kbm")
    o_d, r_d = rowof("original", "dock"), rowof("revised", "dock")
    t_o, t_r = stated_totals(OFFERS["original"]), stated_totals(OFFERS["revised"])
    rec_o, rec_r = sum_lines(ORIGINAL), sum_lines(REVISED)

    s1 = {
        "id": "S1_normal", "purpose": "Cas normal : tous les types d'écarts demandés, plus des changements de mise en forme sans effet.",
        "original": "pdf/offer_original.pdf", "revised": "pdf/offer_revised.pdf", "expected_decision": "conclude",
        "matches": [
            {"original_row": 1, "revised_row": pos("revised", "laptop"), "status": "confirmed",
             "note": "Renommage seul (Ordinateur portable 15 pouces Pro -> PC portable professionnel 15 pouces) : pas un écart commercial."},
            {"original_row": 2, "revised_row": pos("revised", "screen"), "status": "confirmed"},
            {"original_row": 3, "revised_row": pos("revised", "dock"), "status": "confirmed"},
            {"original_row": 4, "revised_row": None, "status": "removed",
             "note": "Clavier et souris sans fil n'existe plus dans la révision."},
            {"original_row": 5, "revised_row": pos("revised", "switch"), "status": "confirmed"},
            {"original_row": 6, "revised_row": pos("revised", "ap"), "status": "confirmed"},
            {"original_row": 7, "revised_row": pos("revised", "install"), "status": "confirmed"},
            {"original_row": 8, "revised_row": pos("revised", "warranty"), "status": "confirmed"},
        ],
        "uncertain_matches": [],
        "substantive_changes": [
            change("S1-C1", "unit_price", "screen", original=vals(o_s), revised=vals(r_s),
                   line_total_delta=str(r_s.total - o_s.total)),
            change("S1-C2", "quantity", "ap", original=vals(o_a), revised=vals(r_a),
                   line_total_delta=str(r_a.total - o_a.total)),
            change("S1-C3", "scope_removed", "kbm", original=vals(o_k), revised=None,
                   line_total_delta=str(-o_k.total)),
            change("S1-C4", "delivery_date", "dock", original=vals(o_d), revised=vals(r_d), line_total_delta="0.00"),
            {"id": "S1-C5", "type": "stated_total", "item_key": None,
             "original": {"total_ht": str(t_o["ht"])}, "revised": {"total_ht": str(t_r["ht"])},
             "stated_total_ht_delta": str(t_r["ht"] - t_o["ht"]),
             "sources": {"original": tref("original"), "revised": tref("revised")}},
        ],
        "arithmetic_discrepancies": [{
            "id": "S1-A1", "document": "revised", "field": "total_ht", "stated": str(t_r["ht"]),
            "recomputed_from_lines": str(rec_r), "difference": str(t_r["ht"] - rec_r),
            "note": "TVA et TTC affichés sont cohérents avec le HT affiché (faux) ; le signaler sans corriger silencieusement.",
            "sources": {"revised": tref("revised")},
        }],
        "net_effect": {"recomputed_ht_original": str(rec_o), "recomputed_ht_revised": str(rec_r),
                       "recomputed_delta": str(rec_r - rec_o), "stated_delta": str(t_r["ht"] - t_o["ht"])},
        "must_not_report_as_commercial_change": [
            "Renommage de la ligne portable", "Réordonnancement des lignes", "Version A -> B",
            "Polices, couleurs, alignement", "Format des montants (1 150,00 € -> EUR 1 150,00)",
            "Format des dates (16/11/2026 -> 16 novembre 2026)", "Libellés d'en-têtes de colonnes et de totaux",
        ],
        "expected_counts": {"confirmed_changes": 5, "arithmetic_discrepancies": 1, "false_changes_allowed": 0},
    }

    s2 = {
        "id": "S2_formatting_only", "purpose": "Même contenu, mise en forme différente : aucun écart substantiel.",
        "original": "pdf/offer_original.pdf", "revised": "pdf/offer_original_reformatted.pdf", "expected_decision": "no_changes",
        "matches": [{"original_row": i, "revised_row": i, "status": "confirmed"} for i in range(1, 9)],
        "uncertain_matches": [], "substantive_changes": [], "arithmetic_discrepancies": [],
        "must_not_report_as_commercial_change": [
            "Polices, couleurs, zébrage", "Format des montants", "Format des dates", "En-têtes de colonnes", "Casse des libellés de totaux"],
        "expected_counts": {"confirmed_changes": 0, "arithmetic_discrepancies": 0, "false_changes_allowed": 0},
    }

    o_l = rowof("original", "laptop")
    s3 = {
        "id": "S3_ambiguous", "purpose": "Ambiguïté : une ligne scindée et un renommage vague. Ne pas conclure sans confirmation.",
        "original": "pdf/offer_original.pdf", "revised": "pdf/offer_revised_ambiguous.pdf",
        "expected_decision": "conclude_partially_and_ask",
        "matches": [
            {"original_row": 2, "revised_row": pos("ambiguous", "screen"), "status": "confirmed"},
            {"original_row": 3, "revised_row": pos("ambiguous", "dock"), "status": "confirmed"},
            {"original_row": 5, "revised_row": pos("ambiguous", "switch"), "status": "confirmed_or_uncertain",
             "note": "Switch réseau 24 ports -> Équipement réseau 24 ports : mêmes quantité, prix et date ; confirmé ou signalé, les deux acceptés."},
            {"original_row": 6, "revised_row": pos("ambiguous", "ap"), "status": "confirmed"},
            {"original_row": 7, "revised_row": pos("ambiguous", "install"), "status": "confirmed"},
            {"original_row": 8, "revised_row": pos("ambiguous", "warranty"), "status": "confirmed"},
        ],
        "uncertain_matches": [
            {"original_row": 1, "revised_rows": [pos("ambiguous", "laptop_a"), pos("ambiguous", "laptop_b")],
             "why": "Une ligne (10 x 1150,00) devient deux lignes (6 x 1150,00 et 4 x 1290,00, config 32 Go) : scission, "
                    "montée en gamme ou nouvelle ligne ? Ne pas affirmer 'prix unitaire passé de 1150 à 1290'.",
             "sources": {"original": rref("original", "laptop"),
                         "revised": [rref("ambiguous", "laptop_a"), rref("ambiguous", "laptop_b")]}},
            {"original_row": 4, "revised_rows": [pos("ambiguous", "pack")],
             "why": "Clavier et souris sans fil (10 x 45,00) vs Pack accessoires bureau (10 x 45,00) : renommage ou remplacement ? "
                    "Ne pas affirmer 'ligne supprimée' ni 'ligne ajoutée'.",
             "sources": {"original": rref("original", "kbm"), "revised": rref("ambiguous", "pack")}},
        ],
        "substantive_changes": [
            change("S3-C1", "quantity", "ap", o_name="original", r_name="ambiguous",
                   original=vals(o_a), revised=vals(rowof("ambiguous", "ap")),
                   line_total_delta=str(rowof("ambiguous", "ap").total - o_a.total)),
            # correction de la clé de réponse (1er jet : omission) : le total HT affiché diffère bel et bien, c'est un fait du
            # document ; seule son ATTRIBUTION aux lignes 1 et 4 reste incertaine.
            {"id": "S3-C2", "type": "stated_total", "item_key": None,
             "original": {"total_ht": str(stated_totals(OFFERS["original"])["ht"])},
             "revised": {"total_ht": str(stated_totals(OFFERS["ambiguous"])["ht"])},
             "stated_total_ht_delta": str(stated_totals(OFFERS["ambiguous"])["ht"] - stated_totals(OFFERS["original"])["ht"]),
             "sources": {"original": tref("original"), "revised": tref("ambiguous")}}],
        "arithmetic_discrepancies": [],
        "required_clarifications": 2,
        "net_effect": {"recomputed_ht_original": str(rec_o), "recomputed_ht_revised": str(sum_lines(AMBIGUOUS)),
                       "note": "Écart global calculable, mais son attribution ligne à ligne reste incertaine pour les lignes 1 et 4."},
        "must_not_report_as_commercial_change": ["Mise en forme", "Version A -> B"],
        "expected_counts": {"confirmed_changes": 2, "arithmetic_discrepancies": 0, "uncertain_items": 2, "false_changes_allowed": 0},
    }

    s4 = {
        "id": "S4_unreadable", "purpose": "Entrée hors périmètre : PDF scanné sans couche texte. Refuser de conclure et le dire.",
        "original": "pdf/offer_original.pdf", "revised": "pdf/offer_revised_scanned.pdf", "expected_decision": "decline",
        "expected_behaviour": ["Détecter l'absence de texte exploitable dans la révision.",
                               "Ne produire aucune liste d'écarts ni aucun chiffre pour ce document.",
                               "Demander un PDF texte (non scanné) ou une saisie de confirmation par l'utilisateur."],
        "matches": [], "uncertain_matches": [], "substantive_changes": [], "arithmetic_discrepancies": [],
        "expected_counts": {"confirmed_changes": 0, "arithmetic_discrepancies": 0, "false_changes_allowed": 0},
        "note": "Contenu source du scan = offer_revised.pdf ; toute valeur chiffrée annoncée serait une hallucination ou un OCR non demandé.",
    }

    return {
        "meta": {
            "title": "Jeu de test - comparaison de deux offres commerciales (matériel informatique)",
            "language": "fr", "currency": "EUR", "vat_rate": "0.20", "fictional": True,
            "supplier": SUPPLIER, "client": CLIENT, "offer_ref": OFFER_REF,
            "generator": "generate_testset.py (reportlab, déterministe)",
            "how_to_score": {
                "missed_change": "Écart attendu (substantive_changes ou arithmetic_discrepancies) non rapporté.",
                "false_change": "Écart rapporté comme confirmé alors qu'il n'est pas dans la vérité terrain "
                                "(inclut toute entrée de must_not_report_as_commercial_change).",
                "source_reference_check": "Pour chaque écart rapporté : page et numéro de ligne exacts dans les DEUX documents "
                                          "(sauf ligne supprimée : un seul côté).",
                "uncertain": "Les éléments de uncertain_matches doivent être séparés des écarts confirmés.",
            },
            "scope_limits": ["2 PDF texte, 3 pages max chacun (ici 2)", "une seule devise", "10 lignes max (ici 8 et 9)",
                             "pas de scanné/manuscrit (sauf S4 : refus attendu)"],
        },
        "documents": {n: doc_truth(n) for n in ("original", "revised", "reformatted", "ambiguous")},
        "scenarios": [s1, s2, s3, s4],
    }


# --------------------------------------------------------------------------- main
def main():
    os.makedirs(PDF_DIR, exist_ok=True)
    for name, o in OFFERS.items():
        build_pdf(os.path.join(PDF_DIR, o["file"]), o)
    build_scanned(os.path.join(PDF_DIR, OFFERS["revised"]["file"]), os.path.join(PDF_DIR, "offer_revised_scanned.pdf"))
    exp = build_expected()
    with open(os.path.join(HERE, "expected_differences.json"), "w", encoding="utf-8") as fh:
        json.dump(exp, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    for name, d in exp["documents"].items():
        print(f"{name:12s} lignes={d['line_items']}  HT affiché={d['stated_totals']['ht']}  "
              f"HT recalculé={d['recomputed_totals_from_lines']['ht']}  cohérent={d['arithmetic_consistent']}")
    print("OK ->", PDF_DIR)


if __name__ == "__main__":
    main()
