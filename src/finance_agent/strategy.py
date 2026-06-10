"""The Strategy contract.

Every generated strategy is a Python module under ``strategies/`` that exposes:

    SPEC : StrategySpec        # metadata for the ledger (thesis, taxonomy, ...)
    def generate_weights(prices: pd.DataFrame, **params) -> pd.DataFrame

``generate_weights`` returns target weights (dates x tickers). It must only use
information available up to and including each row's date; the backtest engine adds
the execution lag. Keeping the surface this small lets sub-agents write strategies
quickly and lets the validator treat every strategy identically.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Callable, Protocol

import pandas as pd

# The factor-family taxonomy is the *coarse* coordinate system used for diversity.
# Generators are told which families are already crowded this cycle — but NOT the
# actual signal formulas — so they differentiate without being anchored.
TAXONOMY = [
    "time_series_momentum",
    "cross_sectional_momentum",
    "short_term_reversal",
    "value",
    "quality",
    "low_volatility",
    "carry",
    "seasonality_calendar",
    "trend_following",
    "cross_asset",
    "volatility_timing",
    "sentiment_altdata",
    "statistical_ml",
    "microstructure",
    "event_driven",
    "market_state_structural",
    "time_irreversibility",
    "path_geometry",
]


@dataclass
class StrategySpec:
    """Metadata describing a strategy. Persisted to the ledger for novelty tracking."""

    id: str                       # short slug, unique, e.g. "xs_mom_12_1"
    thesis: str                   # one-paragraph economic/behavioral rationale
    taxonomy: list[str]           # one or more families from TAXONOMY
    feature_families: list[str]   # coarse inputs used, e.g. ["price", "volume"]
    universe: str = "default"
    params: dict = field(default_factory=dict)
    author: str = "quant-researcher"
    references: list[str] = field(default_factory=list)  # papers/data informing it
    # Novelty bookkeeping — so re-implementations of known methods can't masquerade as new.
    # One of: "none_found" (a genuinely untried combination; say what you searched),
    # "extends: <id/method>" (a novel twist on something we/others have), or
    # "reimplements: <source>" (a known technique we are re-testing — allowed, but labelled).
    prior_art: str = "unknown"
    # The unique, not-previously-tried combination this idea expresses, in one line
    # (e.g. "path-memory regime gate ON the validated vol-target sizing"). Empty = vanilla.
    novel_combination: str = ""
    # Gross exposure each period is normalized to this. Use 1.0 for a fully-invested
    # long/short or long-only book; use None to leave weights untouched (required for
    # market-timing / vol-targeting strategies whose whole point is VARIABLE exposure
    # between cash and the asset).
    gross_leverage: float | None = 1.0

    def to_dict(self) -> dict:
        return asdict(self)


class Strategy(Protocol):
    """Structural type a strategy module satisfies."""

    SPEC: StrategySpec

    def generate_weights(self, prices: pd.DataFrame, **params) -> pd.DataFrame: ...


GenerateWeights = Callable[..., pd.DataFrame]
