"""Glue that loads a strategy module and runs the standard evaluation battery.

Sub-agents should call into this rather than re-implementing backtest plumbing, so
every strategy is judged by an identical, auditable yardstick.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType

import pandas as pd

from . import data, validation
from .backtest import run_backtest


def load_strategy_module(path: str | Path) -> ModuleType:
    """Import a strategy file by path. Must expose SPEC and generate_weights."""
    path = Path(path)
    spec = importlib.util.spec_from_file_location(path.stem, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load strategy at {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    for attr in ("SPEC", "generate_weights"):
        if not hasattr(mod, attr):
            raise AttributeError(f"Strategy {path} is missing required `{attr}`")
    return mod


def evaluate(strategy_path: str | Path, start: str = "2010-01-01",
             end: str | None = None, cost_bps: float = 5.0,
             n_trials: int = 1) -> dict:
    """Fetch data for the strategy's universe and run the full evaluation battery.

    ``n_trials`` should be the number of distinct strategy variants the search
    explored to find this one — it feeds the deflated-Sharpe (data-snooping) test.
    Returns a JSON-serializable dict the reporter and red-team consume.
    """
    mod = load_strategy_module(strategy_path)
    spec = mod.SPEC
    tickers = data.load_universe(getattr(spec, "universe", "default"))
    prices = data.get_prices(tickers, start=start, end=end)

    params = getattr(spec, "params", {}) or {}
    weight_fn = lambda p: mod.generate_weights(p, **params)  # noqa: E731

    # Strategies that vary their net exposure (vol-targeting / market-timing) opt out of
    # per-row gross normalization via SPEC.gross_leverage = None.
    gl = getattr(spec, "gross_leverage", 1.0)

    result = run_backtest(prices, weight_fn(prices), cost_bps=cost_bps, gross_leverage=gl)
    report = {
        "id": spec.id,
        "thesis": spec.thesis,
        "taxonomy": spec.taxonomy,
        "feature_families": spec.feature_families,
        "universe": spec.universe,
        "params": params,
        "gross_leverage": gl,
        "headline": result.stats(),
        "oos": validation.split_oos(prices, weight_fn, cost_bps=cost_bps, gross_leverage=gl),
        "subsample": validation.subsample_stability(prices, weight_fn, cost_bps=cost_bps, gross_leverage=gl),
        "cost_sensitivity": validation.cost_sensitivity(prices, weight_fn, gross_leverage=gl).to_dict(),
        "deflated_sharpe": validation.deflated_sharpe_report(result.returns, n_trials),
        "latest_weights": _latest_nonzero_weights(result.weights),
    }
    return report


def _latest_nonzero_weights(weights: pd.DataFrame, top: int = 20) -> dict:
    if weights.empty:
        return {}
    last = weights.iloc[-1]
    last = last[last.abs() > 1e-9].sort_values(key=abs, ascending=False)
    return {k: round(float(v), 4) for k, v in last.head(top).items()}


def pretty(report: dict) -> str:
    return json.dumps(report, indent=2, default=str)
