"""Portfolio construction — the Pivot B harness.

The alpha-hunt found that *risk control*, not directional edge, is what reliably works on
accessible data. So instead of hunting for one magic signal, we COMBINE return streams into
a risk-managed portfolio. Two levels:

1. **Asset allocation** across a cross-asset universe (`inverse_vol_weights`,
   `risk_parity_weights`) — diversify across distinct risk drivers.
2. **Sleeve combination** (`combine_sleeves`) — blend several validated strategies
   ("sleeves"), each a (dates x tickers) weight schedule, by risk so no one sleeve dominates.

Everything is look-ahead-safe: weights at date t use only trailing data, and the existing
`backtest.run_backtest` adds the 1-day execution lag. A portfolio is itself just a weight
schedule, so it is scored by the same standardized harness as any strategy.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import metrics
from .backtest import run_backtest


def _trailing_vol(returns: pd.DataFrame, window: int = 63) -> pd.DataFrame:
    """Annualized trailing vol per asset (causal: uses returns up to and including t)."""
    return returns.rolling(window, min_periods=max(20, window // 2)).std() * np.sqrt(metrics.TRADING_DAYS)


def inverse_vol_weights(prices: pd.DataFrame, window: int = 63, rebalance: int = 21,
                        long_only: bool = True) -> pd.DataFrame:
    """Inverse-volatility ("naive risk parity") weights across the columns of ``prices``.

    Each rebalance, weight_i ∝ 1/vol_i, normalized to sum to 1. Lower-vol assets (bonds)
    get more notional, higher-vol assets (equity) less — a robust, parameter-light
    diversified allocation. Held between monthly rebalances.
    """
    rets = prices.pct_change()
    vol = _trailing_vol(rets, window)
    inv = 1.0 / vol.replace(0.0, np.nan)
    raw = inv.div(inv.sum(axis=1), axis=0)
    weights = pd.DataFrame(index=prices.index, columns=prices.columns, dtype=float)
    for dt in prices.index[::rebalance]:
        row = raw.loc[dt]
        if row.notna().sum() >= 2:
            weights.loc[dt] = row.fillna(0.0).values
    return weights.ffill().fillna(0.0)


def risk_parity_weights(prices: pd.DataFrame, window: int = 63, rebalance: int = 21,
                        iters: int = 50) -> pd.DataFrame:
    """Equal *risk-contribution* weights via a simple iterative solver on the trailing
    covariance. More principled than inverse-vol when assets are correlated (it accounts
    for the covariance, not just the diagonal). Long-only, sums to 1, monthly rebalance.
    """
    rets = prices.pct_change()
    weights = pd.DataFrame(index=prices.index, columns=prices.columns, dtype=float)
    cols = list(prices.columns)
    for dt in prices.index[::rebalance]:
        i = prices.index.get_loc(dt)
        win = rets.iloc[max(0, i - window + 1): i + 1].dropna(axis=1, how="any")
        if win.shape[0] < max(20, window // 2) or win.shape[1] < 2:
            continue
        cov = win.cov().values * metrics.TRADING_DAYS
        w = _solve_risk_parity(cov, iters=iters)
        weights.loc[dt, win.columns] = w
    return weights.ffill().fillna(0.0)


def _solve_risk_parity(cov: np.ndarray, iters: int = 50) -> np.ndarray:
    """Cyclical-coordinate solver for equal risk contribution (long-only, sums to 1)."""
    n = cov.shape[0]
    w = np.ones(n) / n
    for _ in range(iters):
        port_var = float(w @ cov @ w)
        if port_var <= 0:
            break
        mrc = cov @ w                      # marginal risk contribution
        rc = w * mrc                       # risk contribution per asset
        target = port_var / n
        # nudge each weight toward equal risk contribution
        w = w * (target / np.clip(rc, 1e-12, None)) ** 0.5
        w = np.clip(w, 0, None)
        s = w.sum()
        if s <= 0:
            return np.ones(n) / n
        w = w / s
    return w


def vol_target(weights: pd.DataFrame, prices: pd.DataFrame, target_vol: float = 0.10,
               window: int = 63, max_leverage: float = 1.0,
               rebalance: int = 21) -> pd.DataFrame:
    """Scale a weight schedule so the *portfolio's* trailing realized vol targets
    ``target_vol`` (capped at ``max_leverage``). This is the validated `voltarget_spy`
    idea applied at the portfolio level — the de-risking that actually works.
    """
    rets = prices.pct_change()
    held = weights.shift(1).fillna(0.0)
    port_ret = (held * rets).sum(axis=1)
    realized = port_ret.rolling(window, min_periods=max(20, window // 2)).std() * np.sqrt(metrics.TRADING_DAYS)
    scale = (target_vol / realized.replace(0.0, np.nan)).clip(upper=max_leverage)
    scale = scale.reindex(weights.index)
    # only update the scalar on the rebalance grid to keep turnover sane
    grid = pd.Series(np.nan, index=weights.index)
    for dt in weights.index[::rebalance]:
        if np.isfinite(scale.get(dt, np.nan)):
            grid.loc[dt] = scale.loc[dt]
    grid = grid.ffill().fillna(0.0)
    return weights.mul(grid, axis=0)


def combine_sleeves(sleeves: dict[str, pd.DataFrame], prices: pd.DataFrame,
                    method: str = "equal_risk", window: int = 63,
                    rebalance: int = 21) -> pd.DataFrame:
    """Blend several strategy "sleeves" into one portfolio weight schedule.

    Each sleeve is a (dates x tickers) weight DataFrame (a validated strategy). We size the
    sleeves against each other so no one sleeve's risk dominates, then sum their (scaled)
    weights. ``method``:
      - ``"equal_weight"``  : 1/N across sleeves.
      - ``"equal_risk"``    : inverse-vol across sleeves' own backtested return streams.
    The result is itself a weight schedule, scored by the standard harness.
    """
    names = list(sleeves)
    cols = prices.columns
    aligned = {n: sleeves[n].reindex(index=prices.index, columns=cols).fillna(0.0) for n in names}

    # Each sleeve's realized return stream (lagged, like the engine) for risk sizing.
    rets = prices.pct_change()
    sleeve_ret = pd.DataFrame({n: (aligned[n].shift(1).fillna(0.0) * rets).sum(axis=1)
                               for n in names})
    sleeve_vol = sleeve_ret.rolling(window, min_periods=max(20, window // 2)).std() * np.sqrt(metrics.TRADING_DAYS)

    if method == "equal_weight":
        alloc = pd.DataFrame(1.0 / len(names), index=prices.index, columns=names)
    elif method == "equal_risk":
        inv = 1.0 / sleeve_vol.replace(0.0, np.nan)
        alloc = inv.div(inv.sum(axis=1), axis=0)
    else:
        raise ValueError(f"unknown method {method!r}")

    # rebalance the sleeve allocation monthly, hold between
    grid = pd.DataFrame(index=prices.index, columns=names, dtype=float)
    for dt in prices.index[::rebalance]:
        row = alloc.loc[dt]
        if row.notna().all():
            grid.loc[dt] = row.values
    grid = grid.ffill().fillna(1.0 / len(names))

    portfolio = pd.DataFrame(0.0, index=prices.index, columns=cols)
    for n in names:
        portfolio = portfolio.add(aligned[n].mul(grid[n], axis=0), fill_value=0.0)
    return portfolio


def evaluate_portfolio(prices: pd.DataFrame, weights: pd.DataFrame, cost_bps: float = 5.0,
                       benchmarks: dict[str, pd.DataFrame] | None = None) -> dict:
    """Backtest a portfolio weight schedule and (optionally) named benchmark weightings,
    returning comparable headline stats for each. ``benchmarks`` maps name -> weights.
    """
    res = run_backtest(prices, weights, cost_bps=cost_bps, gross_leverage=None)
    out = {"portfolio": res.stats()}
    for name, bw in (benchmarks or {}).items():
        bres = run_backtest(prices, bw.reindex(index=prices.index, columns=prices.columns).fillna(0.0),
                            cost_bps=cost_bps, gross_leverage=None)
        out[name] = bres.stats()
    return out


def static_weights(prices: pd.DataFrame, alloc: dict[str, float]) -> pd.DataFrame:
    """A constant-mix benchmark, e.g. {'SPY': 0.6, 'TLT': 0.4} for 60/40."""
    w = pd.DataFrame(0.0, index=prices.index, columns=prices.columns)
    for tic, a in alloc.items():
        if tic in w.columns:
            w[tic] = a
    return w
