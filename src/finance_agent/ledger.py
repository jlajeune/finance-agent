"""The strategy ledger — the novelty / diversity registry.

Why this exists
---------------
The orchestrator wants parallel researchers to explore *different* ideas without
over-constraining them. The ledger solves this by recording every attempted strategy
and exposing only a **coarse** view of what's been tried:

* the factor-family taxonomy coordinates already occupied this cycle, and
* short theses (so a generator can avoid literal duplicates),

but **not** the signal formulas or parameters of prior winners. Generators are told
"momentum and short-term reversal are crowded — aim elsewhere," which differentiates
them while leaving the actual idea space wide open.

Storage is a simple append-only JSONL file so it is diffable and git-friendly.
"""

from __future__ import annotations

import json
import time
from collections import Counter
from pathlib import Path
from typing import Iterable

LEDGER_PATH = Path("ledger/strategies.jsonl")


def _tokenize(text: str) -> set[str]:
    return {t for t in "".join(c.lower() if c.isalnum() else " " for c in text).split() if len(t) > 2}


def record(entry: dict, path: Path | str = LEDGER_PATH) -> None:
    """Append one strategy record. Expected keys: id, thesis, taxonomy,
    feature_families, plus optional cycle, status, stats, references."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    entry = {"ts": time.time(), **entry}
    with path.open("a") as f:
        f.write(json.dumps(entry) + "\n")


def load(path: Path | str = LEDGER_PATH) -> list[dict]:
    path = Path(path)
    if not path.exists():
        return []
    out = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if line:
            out.append(json.loads(line))
    return out


def occupied_regions(cycle: int | None = None, path: Path | str = LEDGER_PATH) -> dict:
    """Coarse summary handed to generators: how crowded each taxonomy family is.

    If ``cycle`` is given, only that cycle's entries are counted (so each cycle starts
    with a clean diversity budget). Returns family -> count, most-crowded first.
    """
    entries = load(path)
    if cycle is not None:
        entries = [e for e in entries if e.get("cycle") == cycle]
    counts: Counter = Counter()
    for e in entries:
        for fam in e.get("taxonomy", []):
            counts[fam] += 1
    return dict(counts.most_common())


def novelty_check(thesis: str, taxonomy: Iterable[str], cycle: int | None = None,
                  path: Path | str = LEDGER_PATH, jaccard_threshold: float = 0.6) -> dict:
    """Cheap, transparent duplicate detector.

    Flags a proposed idea as a likely duplicate if its thesis has high token-Jaccard
    overlap with an existing thesis that shares a taxonomy family. This is intentionally
    a *soft* signal for the red-team/orchestrator to weigh — not a hard gate — so it
    catches obvious clones without policing genuinely new variations.
    """
    taxonomy = set(taxonomy)
    proposed = _tokenize(thesis)
    entries = load(path)
    if cycle is not None:
        entries = [e for e in entries if e.get("cycle") == cycle]

    best = {"is_duplicate": False, "max_jaccard": 0.0, "closest_id": None}
    for e in entries:
        if not (taxonomy & set(e.get("taxonomy", []))):
            continue
        other = _tokenize(e.get("thesis", ""))
        if not (proposed and other):
            continue
        j = len(proposed & other) / len(proposed | other)
        if j > best["max_jaccard"]:
            best.update(max_jaccard=j, closest_id=e.get("id"))
    best["is_duplicate"] = best["max_jaccard"] >= jaccard_threshold
    return best


def diversity_brief(cycle: int | None = None, path: Path | str = LEDGER_PATH,
                    top_n: int = 4) -> str:
    """A short natural-language nudge for generators. Coarse on purpose."""
    occ = occupied_regions(cycle, path)
    if not occ:
        return ("No strategies recorded yet this cycle — the whole idea space is open. "
                "Pick whichever factor family you find most promising.")
    crowded = list(occ)[:top_n]
    from .strategy import TAXONOMY

    open_families = [f for f in TAXONOMY if f not in occ]
    msg = f"Crowded this cycle (avoid unless you have a genuinely distinct angle): {', '.join(crowded)}. "
    if open_families:
        msg += f"Wide-open families you might explore: {', '.join(open_families[:6])}. "
    msg += "You are NOT told the formulas behind existing strategies — differentiate on idea, not parameters."
    return msg
