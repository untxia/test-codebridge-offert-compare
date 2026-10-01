"""Lecture tolérante des montants, quantités et dates (formats FR/EN usuels)."""
from __future__ import annotations

import datetime as _dt
import re
import unicodedata
from decimal import Decimal
from typing import Optional, Tuple

_SPACES = "    "

MONTHS = {
    "janvier": 1, "janv": 1, "jan": 1, "january": 1,
    "fevrier": 2, "fev": 2, "feb": 2, "february": 2,
    "mars": 3, "mar": 3, "march": 3,
    "avril": 4, "avr": 4, "apr": 4, "april": 4,
    "mai": 5, "may": 5,
    "juin": 6, "jun": 6, "june": 6,
    "juillet": 7, "juil": 7, "jul": 7, "july": 7,
    "aout": 8, "aug": 8, "august": 8,
    "septembre": 9, "sept": 9, "sep": 9, "september": 9,
    "octobre": 10, "oct": 10, "october": 10,
    "novembre": 11, "nov": 11, "november": 11,
    "decembre": 12, "dec": 12, "december": 12,
}

CURRENCY_RE = re.compile(r"€|\bEUR\b|\bUSD\b|\$|£|\bGBP\b|\bCHF\b", re.I)
CURRENCY_MAP = {"€": "EUR", "eur": "EUR", "usd": "USD", "$": "USD", "£": "GBP", "gbp": "GBP", "chf": "CHF"}


def norm(s: str) -> str:
    """minuscules, sans accents, ponctuation -> espace, espaces réduits."""
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9#]+", " ", s)).strip()


def clean_spaces(s: str) -> str:
    for c in _SPACES:
        s = s.replace(c, " ")
    return re.sub(r"\s+", " ", s).strip()


def detect_currencies(text: str) -> dict:
    out: dict = {}
    for m in CURRENCY_RE.finditer(text or ""):
        cur = CURRENCY_MAP[m.group(0).lower()]
        out[cur] = out.get(cur, 0) + 1
    return out


def parse_money(s: Optional[str]) -> Optional[Decimal]:
    """'1 150,00 €' / 'EUR 1 150,00' / '1,150.00' / '1.150,00' -> Decimal. None si ce n'est pas un montant.
    Un seul séparateur suivi d'exactement 3 chiffres ('1,150') est lu comme séparateur de milliers."""
    if s is None:
        return None
    t = clean_spaces(s)
    t = re.sub(r"(?i)\b(eur|euros?|usd|gbp|chf)\b|[€$£]", "", t).strip()
    if not t:
        return None
    neg = t.startswith(("-", "−")) or (t.startswith("(") and t.endswith(")"))
    t = re.sub(r"[()\-−+]", "", t).strip()
    if not re.fullmatch(r"\d[\d ',.]*", t):
        return None
    t = t.replace("'", "").replace(" ", "")
    lc, ld = t.rfind(","), t.rfind(".")
    dec = None
    if lc >= 0 and ld >= 0:
        dec = "," if lc > ld else "."
    elif lc >= 0 or ld >= 0:
        sep = "," if lc >= 0 else "."
        parts = t.split(sep)
        if len(parts) == 2 and len(parts[1]) != 3:
            dec = sep
    if dec:
        ip, fp = t.rsplit(dec, 1)
        ip = re.sub(r"[.,]", "", ip)
        v = Decimal(f"{ip}.{fp}")
    else:
        v = Decimal(re.sub(r"[.,]", "", t))
    return -v if neg else v


def parse_qty(s: Optional[str]) -> Tuple[Optional[Decimal], str]:
    """'10' -> (10, ''), '12 h' -> (12, 'h'), 'x 2,5 j' -> (2.5, 'j')."""
    if s is None:
        return None, ""
    t = clean_spaces(s)
    m = re.fullmatch(r"(?:[x×]\s*)?(\d+(?:[.,]\d+)?)\s*([^\d\s][^\d]*)?", t, re.I)
    if not m:
        return None, ""
    return Decimal(m.group(1).replace(",", ".")), (m.group(2) or "").strip()


def parse_date(s: Optional[str], month_first: bool = False) -> Optional[str]:
    """Retourne une date ISO (YYYY-MM-DD) ou None."""
    if not s:
        return None
    t = clean_spaces(s)
    t = re.sub(r"(?i)^(le|the|au|on)\s+", "", t).strip()
    y = m_ = d = None
    m = re.fullmatch(r"(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})", t)
    if m:
        y, m_, d = int(m[1]), int(m[2]), int(m[3])
    else:
        m = re.fullmatch(r"(\d{1,2})[-/.](\d{1,2})[-/.](\d{2,4})", t)
        if m:
            a, b = int(m[1]), int(m[2])
            d, m_, y = (b, a, int(m[3])) if month_first else (a, b, int(m[3]))
        else:
            m = re.fullmatch(r"(\d{1,2})(?:er)?\s+([A-Za-zÀ-ÿ]+)\.?,?\s+(\d{2,4})", t)
            if m and norm(m[2]) in MONTHS:
                d, m_, y = int(m[1]), MONTHS[norm(m[2])], int(m[3])
            else:
                m = re.fullmatch(r"([A-Za-zÀ-ÿ]+)\.?\s+(\d{1,2}),?\s+(\d{4})", t)
                if m and norm(m[1]) in MONTHS:
                    m_, d, y = MONTHS[norm(m[1])], int(m[2]), int(m[3])
    if y is None:
        return None
    if y < 100:
        y += 2000
    try:
        return _dt.date(y, m_, d).isoformat()
    except ValueError:
        return None


MONEY_TAIL_RE = re.compile(
    r"(?:(?:€|EUR|USD|\$|£|GBP|CHF)\s*)?-?\d{1,3}(?:[   .,']\d{3})*(?:[.,]\d{1,2})?(?:\s*(?:€|EUR|USD|\$|£|GBP|CHF))?\s*$"
    r"|(?:(?:€|EUR|USD|\$|£|GBP|CHF)\s*)?-?\d+(?:[.,]\d{1,2})?(?:\s*(?:€|EUR|USD|\$|£|GBP|CHF))?\s*$"
)
