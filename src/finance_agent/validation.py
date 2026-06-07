"""Robustness checks — the quantitative backbone the red-team relies on.

These functions exist to make it *hard* for an overfit strategy to survive:

* ``split_oos``           - honest in-sample / out-of-sample split.
* ``walk_forward``        - rolling re-evaluation across many windows.
* ``parameter_sensitivity`` - does performance survive perturbing the knobs?
* ``cost_sensitivity``    - does edge survive higher transaction costs?
* ``subsample_stability`` - is the Sharpe stable across disjoint sub-periods?
* ``deflated_sharpe_report`` - is the result plausibly just data-snooping?
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import numpy as np
import pandas as pd

from . import metrics
from .backtest import run_backtest

# A strategy is a callable: prices -> weights. Params are bound by the caller.
WeightFn = Callable[[pd.DataFrame], pd.DataFrame]


@dataclass
class WindowResult:
    label: str
    stats: dict


def _bt_stats(prices: pd.DataFrame, weight_fn: WeightFn, **bt_kwargs) -> dict:
    w = weight_fn(prices)
    return run_backtest(prices, w, **bt_kwargs).stats()


def split_oos(prices: pd.DataFrame, weight_fn: WeightFn, split: str | float = 0.6,
              **bt_kwargs) -> dict:
    """In-sample vs out-of-sample stats. ``split`` is a date string or a fraction.

    Weights are computed on the full history (so rolling features warm up correctly)
    and then the *returns* are partitioned — this avoids a discontinuity at the seam
    while still measuring genuine OOS performance.
    """
    w = weight_fn(prices)
    full = run_backtest(prices, w, **bt_kwargs)
    idx = full.returns.index
    if isinstance(split, float):
        cut = idx[int(len(idx) * split)]
    else:
        cut = pd.Timestamp(split)
    is_r = full.returns[full.returns.index < cut]
    oos_r = full.returns[full.returns.index >= cut]
    return {
        "split_at": str(cut.date()) if hasattr(cut, "date") else str(cut),
        "in_sample": metrics.summary(is_r, full.periods_per_year),
        "out_of_sample": metrics.summary(oos_r, full.periods_per_year),
        "sharpe_decay": (
            metrics.sharpe(is_r) - metrics.sharpe(oos_r)
        ),
    }


def walk_forward(prices: pd.DataFrame, weight_fn: WeightFn, n_windows: int = 5,
                 **bt_kwargs) -> list[WindowResult]:
    """Evaluate the strategy on ``n_windows`` consecutive, equal-length slices."""
    w = weight_fn(prices)
    res = run_backtest(prices, w, **bt_kwargs)
    chunks = np.array_split(res.returns.index, n_windows)
    out = []
    for i, ch in enumerate(chunks):
        seg = res.returns.loc[ch[0]:ch[-1]]
        out.append(WindowResult(
            label=f"window_{i+1} [{ch[0].date()}..{ch[-1].date()}]",
            stats=metrics.summary(seg, res.periods_per_year),
        ))
    return out


def parameter_sensitivity(prices: pd.DataFrame,
                          weight_fn_factory: Callable[..., WeightFn],
                          grid: dict[str, list], metric: str = "sharpe",
                          **bt_kwargs) -> pd.DataFrame:
    """Sweep a 1- or 2-parameter grid and report the chosen metric per cell.

    A robust strategy shows a smooth plateau, not a lone spike. ``weight_fn_factory``
    takes the swept params as kwargs and returns a ``prices -> weights`` callable.
    """
    keys = list(grid)
    rows = []
    if len(keys) == 1:
        (k,) = keys
        for v in grid[k]:
            stats = _bt_stats(prices, weight_fn_factory(**{k: v}), **bt_kwargs)
            rows.append({k: v, metric: stats.get(metric)})
        return pd.DataFrame(rows).set_index(k)
    if len(keys) == 2:
        k1, k2 = keys
        table = pd.DataFrame(index=grid[k1], columns=grid[k2], dtype=float)
        for v1 in grid[k1]:
            for v2 in grid[k2]:
                stats = _bt_stats(prices, weight_fn_factory(**{k1: v1, k2: v2}), **bt_kwargs)
                table.loc[v1, v2] = stats.get(metric)
        table.index.name, table.columns.name = k1, k2
        return table
    raise ValueError("parameter_sensitivity supports 1 or 2 parameters")


def cost_sensitivity(prices: pd.DataFrame, weight_fn: WeightFn,
                     cost_grid_bps=(0, 5, 10, 20, 40), **bt_kwargs) -> pd.DataFrame:
    """Net Sharpe / return as transaction costs rise. Edge should not vanish at 10bps."""
    bt_kwargs.pop("cost_bps", None)
    rows = []
    for c in cost_grid_bps:
        s = _bt_stats(prices, weight_fn, cost_bps=c, **bt_kwargs)
        rows.append({"cost_bps": c, "sharpe": s["sharpe"], "ann_return": s["ann_return"]})
    return pd.DataFrame(rows).set_index("cost_bps")


def subsample_stability(prices: pd.DataFrame, weight_fn: WeightFn, n: int = 4,
                        **bt_kwargs) -> dict:
    """Mean/std of Sharpe across ``n`` disjoint sub-periods. Lower std == more robust."""
    sharpes = [w.stats["sharpe"] for w in walk_forward(prices, weight_fn, n, **bt_kwargs)]
    arr = np.array([s for s in sharpes if not np.isnan(s)])
    return {
        "sub_sharpes": sharpes,
        "mean_sharpe": float(arr.mean()) if arr.size else float("nan"),
        "std_sharpe": float(arr.std(ddof=1)) if arr.size > 1 else float("nan"),
        "fraction_positive": float((arr > 0).mean()) if arr.size else float("nan"),
    }


def deflated_sharpe_report(result_returns: pd.Series, n_trials: int) -> dict:
    """Wrap the deflated-Sharpe calc with the bookkeeping the red-team needs."""
    r = result_returns.dropna()
    if r.empty:
        return {"deflated_sharpe_prob": float("nan")}
    per_obs_sr = r.mean() / r.std(ddof=1) if r.std(ddof=1) else float("nan")
    prob = metrics.deflated_sharpe(
        observed_sharpe=per_obs_sr,
        n_trials=max(1, n_trials),
        n_obs=len(r),
        skew=float(r.skew()),
        kurt=float(r.kurtosis() + 3.0),  # pandas kurtosis is excess; DSR wants raw
    )
    return {
        "per_obs_sharpe": float(per_obs_sr),
        "n_trials": n_trials,
        "n_obs": len(r),
        "deflated_sharpe_prob": prob,
        "passes": bool(prob is not None and not np.isnan(prob) and prob > 0.95),
    }
