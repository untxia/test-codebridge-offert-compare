"""Appariement des lignes entre l'offre originale et la révision.

Principe : tout est déterministe et explicable. Un score (libellé, conditions chiffrées, position) est calculé pour
chaque couple de lignes ; seuls les couples *sans ambiguïté* sont confirmés. Le reste est séparé en :
  - correspondances incertaines (renommage ou remplacement ? ligne scindée ou fusionnée ?) -> à confirmer,
  - lignes supprimées / ajoutées (aucun candidat plausible).
Un renommage, un changement d'ordre ou de mise en forme n'est jamais un écart commercial en soi.

L'utilisateur peut trancher une ambiguïté (overrides) ; la comparaison est alors recalculée.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from difflib import SequenceMatcher
from typing import Dict, List, Optional, Sequence, Tuple

from .models import Item, Offer
from .parsing import norm

# --- seuils (documentés dans le README ; ajustables) -------------------------------------------------------------
LABEL_NEAR_IDENTICAL = 0.90   # libellés quasi identiques : suffisant pour confirmer si le candidat est unique
CONFIRM_SCORE = 0.70          # libellé renommé : exige un score global élevé...
CONFIRM_MIN_LABEL = 0.50      # ...et un minimum de ressemblance de libellé
MARGIN_NEAR_IDENTICAL = 0.20  # avance exigée sur le 2e meilleur candidat (des deux côtés)
MARGIN_RENAMED = 0.25
PLAUSIBLE = 0.35              # en dessous : aucun lien plausible

W_LABEL, W_ATTR, W_POS = 0.55, 0.35, 0.10
STOPWORDS = {"de", "du", "la", "le", "les", "des", "et", "en", "au", "aux", "un", "une", "d", "l", "a", "the", "of", "and"}


# --- similarité -----------------------------------------------------------------------------------------------------
def _tokens(label: str) -> List[str]:
    return [t for t in norm(label).split() if t not in STOPWORDS]


def _tok_eq(a: str, b: str) -> bool:
    if a == b:
        return True
    if min(len(a), len(b)) >= 3 and (a.startswith(b) or b.startswith(a)):
        return True
    return len(a) >= 4 and len(b) >= 4 and SequenceMatcher(None, a, b).ratio() >= 0.84


def label_similarity(a: str, b: str) -> float:
    na, nb = norm(a), norm(b)
    if na == nb:
        return 1.0
    ta, tb = _tokens(a), _tokens(b)
    if not ta or not tb:
        return 0.0
    used, hit = set(), 0
    for x in ta:
        for j, y in enumerate(tb):
            if j not in used and _tok_eq(x, y):
                used.add(j)
                hit += 1
                break
    dice = 2 * hit / (len(ta) + len(tb))
    return round(0.7 * dice + 0.3 * SequenceMatcher(None, na, nb).ratio(), 4)


def _num_sim(a: Optional[Decimal], b: Optional[Decimal], tol: float) -> Optional[float]:
    if a is None or b is None:
        return None
    if a == b:
        return 1.0
    if a == 0 or b == 0:
        return 0.0
    rel = abs(float(a) - float(b)) / max(abs(float(a)), abs(float(b)))
    return 0.5 if rel <= tol else 0.0


def attr_similarity(o: Item, r: Item) -> float:
    parts: List[Tuple[float, float]] = []
    s = _num_sim(o.unit_price, r.unit_price, 0.10)
    if s is not None:
        parts.append((0.4, s))
    s = _num_sim(o.qty, r.qty, 0.0)
    if s is not None:
        parts.append((0.3, s))
    if o.delivery is not None and r.delivery is not None:
        parts.append((0.3, 1.0 if o.delivery == r.delivery else 0.0))
    if not parts:
        return 0.5
    return round(sum(w * s for w, s in parts) / sum(w for w, _ in parts), 4)


def _relpos(i: int, n: int) -> float:
    return 0.0 if n <= 1 else (i - 1) / (n - 1)


@dataclass
class Score:
    orig: int
    rev: int
    label: float
    attr: float
    pos: float
    total: float


def score_pair(o: Item, r: Item, n_o: int, n_r: int) -> Score:
    lab, att = label_similarity(o.label, r.label), attr_similarity(o, r)
    pos = round(1 - abs(_relpos(o.index, n_o) - _relpos(r.index, n_r)), 4)
    return Score(o.index, r.index, lab, att, pos, round(W_LABEL * lab + W_ATTR * att + W_POS * pos, 4))


# --- résultat -------------------------------------------------------------------------------------------------------
@dataclass
class Pair:
    orig: int
    rev: int
    status: str                 # "confirmed"
    basis: str                  # "auto" | "user"
    label_changed: bool
    score: float
    label_score: float
    attr_score: float


@dataclass
class UncertainGroup:
    id: str
    kind: str                   # "one_to_one" | "split_or_merge" | "many_to_many"
    reason_code: str            # rename_or_replacement | split_or_merge | ambiguous_group
    orig: List[int]
    rev: List[int]
    candidates: List[Dict]      # [{orig, rev, score, label_score, attr_score}]


@dataclass
class MatchResult:
    pairs: List[Pair] = field(default_factory=list)
    uncertain: List[UncertainGroup] = field(default_factory=list)
    removed: List[int] = field(default_factory=list)     # lignes de l'original sans équivalent plausible
    added: List[int] = field(default_factory=list)       # lignes de la révision sans équivalent plausible
    scores: List[Score] = field(default_factory=list)


def _confirmable(s: Score, row_others: Sequence[Score], col_others: Sequence[Score]) -> bool:
    r2 = max((x.total for x in row_others), default=0.0)
    c2 = max((x.total for x in col_others), default=0.0)
    gap = s.total - max(r2, c2)
    if s.label >= LABEL_NEAR_IDENTICAL:
        return gap >= MARGIN_NEAR_IDENTICAL
    return s.total >= CONFIRM_SCORE and s.label >= CONFIRM_MIN_LABEL and gap >= MARGIN_RENAMED


def match_offers(orig: Offer, rev: Offer, overrides: Optional[Dict] = None) -> MatchResult:
    """overrides (décisions de l'utilisateur) : {"pairs": [[o, r], ...], "removed": [o, ...], "added": [r, ...]}"""
    overrides = overrides or {}
    O = {i.index: i for i in orig.items}
    R = {i.index: i for i in rev.items}
    res = MatchResult()
    res.scores = [score_pair(o, r, len(O), len(R)) for o in orig.items for r in rev.items]
    S = {(s.orig, s.rev): s for s in res.scores}

    free_o, free_r = set(O), set(R)

    def accept(o: int, r: int, basis: str) -> None:
        s = S[(o, r)]
        res.pairs.append(Pair(o, r, "confirmed", basis, label_similarity(O[o].label, R[r].label) < 1.0, s.total, s.label, s.attr))
        free_o.discard(o)
        free_r.discard(r)

    # 1) décisions explicites de l'utilisateur
    for o, r in overrides.get("pairs", []):
        if o in free_o and r in free_r:
            accept(o, r, "user")
    for o in overrides.get("removed", []):
        if o in free_o:
            free_o.discard(o)
            res.removed.append(o)
    for r in overrides.get("added", []):
        if r in free_r:
            free_r.discard(r)
            res.added.append(r)

    # 2) appariements sans ambiguïté, du meilleur score au moins bon, jusqu'à stabilité
    progress = True
    while progress:
        progress = False
        cands = sorted((S[(o, r)] for o in free_o for r in free_r), key=lambda s: -s.total)
        for s in cands:
            if s.orig not in free_o or s.rev not in free_r:
                continue
            row_others = [S[(s.orig, r)] for r in free_r if r != s.rev]
            col_others = [S[(o, s.rev)] for o in free_o if o != s.orig]
            if _confirmable(s, row_others, col_others):
                accept(s.orig, s.rev, "auto")
                progress = True
                break

    # 3) le reste : composantes connexes de couples plausibles -> incertain ; sinon supprimé / ajouté
    plaus = [(o, r) for o in free_o for r in free_r if S[(o, r)].total >= PLAUSIBLE]
    parent: Dict[Tuple[str, int], Tuple[str, int]] = {}

    def find(x):
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for o, r in plaus:
        parent[find(("o", o))] = find(("r", r))
    comps: Dict[Tuple[str, int], Dict[str, set]] = {}
    for o, r in plaus:
        c = comps.setdefault(find(("o", o)), {"o": set(), "r": set()})
        c["o"].add(o)
        c["r"].add(r)
    in_group_o, in_group_r = set(), set()
    for k, (_, c) in enumerate(sorted(comps.items(), key=lambda kv: min(kv[1]["o"])), 1):
        os_, rs_ = sorted(c["o"]), sorted(c["r"])
        in_group_o |= set(os_)
        in_group_r |= set(rs_)
        if len(os_) == 1 and len(rs_) == 1:
            kind, code = "one_to_one", "rename_or_replacement"
        elif len(os_) == 1 or len(rs_) == 1:
            kind, code = "split_or_merge", "split_or_merge"
        else:
            kind, code = "many_to_many", "ambiguous_group"
        res.uncertain.append(UncertainGroup(
            id=f"U{k}", kind=kind, reason_code=code, orig=os_, rev=rs_,
            candidates=[dict(orig=o, rev=r, score=S[(o, r)].total, label_score=S[(o, r)].label, attr_score=S[(o, r)].attr)
                        for o in os_ for r in rs_ if S[(o, r)].total >= PLAUSIBLE]))
    res.removed += sorted(free_o - in_group_o)
    res.added += sorted(free_r - in_group_r)
    res.removed.sort()
    res.added.sort()
    res.pairs.sort(key=lambda p: p.orig)
    return res
