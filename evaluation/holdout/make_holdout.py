#!/usr/bin/env python3
"""Jeu de test « hold-out » : écrit APRÈS le développement de l'extracteur, avec un autre fournisseur, des en-têtes
anglais, une autre devise (USD), des montants au format US (1,150.00), un autre ordre de colonnes, avec/sans grille.
Sert à mesurer la généralisation (le moteur n'a pas été réglé dessus)."""
import json, os
from decimal import Decimal as D
from reportlab import rl_config
rl_config.invariant = 1
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = [  # item, qty, unit price, delivery
    ("Rack server 1U Xeon", 4, "2450.00", "2026-12-02"),
    ("NVMe SSD 2TB enterprise", 20, "189.00", "2026-12-02"),
    ("10GbE network card dual port", 8, "145.50", "2026-12-09"),
    ("Rack mounting rail kit", 4, "38.00", "2026-12-09"),
    ("Extended warranty 3 years", 4, "260.00", "2027-01-15"),
    ("On-site installation service", 1, "900.00", "2026-12-16"),
]
REV = [  # reordered, one rename, 1 price, 1 qty, 1 date, 1 removed, 1 added
    ("On-site installation service", 1, "900.00", "2026-12-16"),
    ("1U rack server (Xeon)", 4, "2450.00", "2026-12-02"),
    ("NVMe SSD 2TB enterprise", 24, "189.00", "2026-12-02"),
    ("10GbE network card dual port", 8, "152.00", "2026-12-09"),
    ("Extended warranty 3 years", 4, "260.00", "2027-01-29"),
    ("UPS 3kVA rack battery backup", 2, "640.00", "2026-12-09"),
]
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def usd(v):
    return f"${D(v):,.2f}"


def dt(s, long):
    y, m, d = s.split("-")
    return f"{MONTHS[int(m) - 1]} {int(d)}, {y}" if long else f"{m}/{d}/{y}"


def build(path, rows, version, order, grid, long_dates, title):
    ss = getSampleStyleSheet()
    heads = dict(item="Item", qty="Qty", price="Unit price", total="Line total", date="Ship date")
    data = [[heads[k] for k in order]]
    ht = D("0")
    for i, (lab, q, p, d) in enumerate(rows, 1):
        lt = D(q) * D(p); ht += lt
        cell = dict(item=Paragraph(lab, ss["BodyText"]), qty=str(q), price=usd(p), total=usd(lt), date=dt(d, long_dates))
        data.append([cell[k] for k in order])
    t = Table(data, colWidths=[200 if k == "item" else 70 for k in order])
    cmds = [("FONTSIZE", (0, 0), (-1, -1), 8), ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#444444")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]
    if grid:
        cmds.append(("GRID", (0, 0), (-1, -1), 0.4, colors.grey))
    t.setStyle(TableStyle(cmds))
    vat = (ht * D("0.08")).quantize(D("0.01"))
    tot = Table([["Subtotal", usd(ht)], ["Sales tax (8%)", usd(vat)], ["Total due", usd(ht + vat)]], colWidths=[400, 100])
    tot.setStyle(TableStyle([("ALIGN", (1, 0), (1, -1), "RIGHT"), ("FONTSIZE", (0, 0), (-1, -1), 9)]))
    SimpleDocTemplate(path, pagesize=A4, title=title).build([
        Paragraph(f"Quotation Q-77-{version}", ss["Title"]), Paragraph("Supplier: Brightfield Data Systems Inc. (fictional) - Currency: USD", ss["Normal"]),
        Spacer(1, 12), t, Spacer(1, 12), tot])
    return ht


def main():
    out = {}
    for name, grid, order, long_dates in (("h1", True, ["item", "qty", "price", "total", "date"], False),
                                           ("h2", False, ["item", "date", "qty", "price", "total"], True)):
        build(f"{HERE}/{name}_original.pdf", BASE, "A", order, grid, long_dates, "Quote A")
        build(f"{HERE}/{name}_revised.pdf", REV, "B", order, grid, long_dates, "Quote B")
    out["expected"] = dict(
        changes=[("unit_price", "10GbE network card dual port"), ("quantity", "NVMe SSD 2TB enterprise"),
                 ("delivery_date", "Extended warranty 3 years"), ("scope_removed", "Rack mounting rail kit"),
                 ("scope_added", "UPS 3kVA rack battery backup"), ("stated_total", None)],
        not_changes=["1U rack server (Xeon) rename", "row reorder"])
    json.dump(out, open(f"{HERE}/expected.json", "w"), indent=1)


main()
