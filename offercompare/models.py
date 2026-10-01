"""Modèles de données. Les valeurs lues dans les documents sont conservées telles que lues (Decimal + texte brut)."""
from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Dict, List, Optional


@dataclass
class BBox:
    page: int
    x0: float
    top: float
    x1: float
    bottom: float


@dataclass
class Money:
    value: Optional[Decimal]
    raw: str
    bbox: Optional[BBox] = None


@dataclass
class Item:
    index: int                      # ordre d'apparition dans le document (1-based)
    printed_no: Optional[str]       # numéro imprimé dans le document, s'il existe
    label: str
    qty: Optional[Decimal]
    unit: str
    unit_price: Optional[Decimal]
    line_total: Optional[Decimal]
    delivery: Optional[str]         # date ISO si reconnue, sinon texte tel quel
    delivery_is_date: bool
    page: int
    bbox: BBox                      # ligne entière
    cells: Dict[str, BBox] = field(default_factory=dict)   # rôle -> zone de la cellule
    raw: Dict[str, str] = field(default_factory=dict)      # rôle -> texte brut
    warnings: List[str] = field(default_factory=list)


@dataclass
class Totals:
    ht: Optional[Money] = None
    vat: Optional[Money] = None
    ttc: Optional[Money] = None
    vat_rate: Optional[Decimal] = None


@dataclass
class PageInfo:
    number: int
    width: float
    height: float
    has_text: bool
    n_images: int


@dataclass
class Offer:
    file: str
    pages: List[PageInfo]
    has_text_layer: bool
    items: List[Item]
    totals: Totals
    currency: Optional[str]
    currencies_seen: Dict[str, int]
    method: str
    warnings: List[str] = field(default_factory=list)
    elapsed_ms: float = 0.0


def to_jsonable(o):
    """dataclasses / Decimal -> structures JSON."""
    if dataclasses.is_dataclass(o) and not isinstance(o, type):
        return {f.name: to_jsonable(getattr(o, f.name)) for f in dataclasses.fields(o)}
    if isinstance(o, Decimal):
        return str(o)
    if isinstance(o, dict):
        return {k: to_jsonable(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [to_jsonable(v) for v in o]
    return o
