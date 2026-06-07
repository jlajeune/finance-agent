"""Offline sanity tests for the harness — synthetic data only, no network.

These verify the math and the look-ahead guarantee without touching yfinance, so they
are safe to run anytime (including before the full pipeline is exercised).
"""

import numpy as np
import pandas as pd

from finance_agent import metrics
from finance_agent.backtest import run_backtest
from finance_agent import ledger


def _synthetic_prices(n_days=500, n_assets=5, seed=0):
    rng = np.random.default_rng(seed)
    rets = rng.normal(0.0003, 0.01, size=(n_days, n_assets))
    prices = 100 * np.exp(np.cumsum(rets, axis=0))
    idx = pd.bdate_range("2015-01-01", periods=n_days)
    return pd.DataFrame(prices, index=idx, columns=[f"A{i}" for i in range(n_assets)])


def test_metrics_basic():
    r = pd.Series(np.r_[0.01, -0.005, 0.02, 0.0, -0.01])
    assert metrics.sharpe(r) == metrics.sharpe(r)  # not NaN for non-constant series
    assert metrics.max_drawdown(r) <= 0
    assert 0 <= metrics.hit_rate(r) <= 1


def test_execution_lag_blocks_same_bar_trading():
    """The engine's execution lag must prevent trading on the *same bar* a signal is
    observed. We build weights from the same-day return (info available at close t).
    With lag=0 this is a look-ahead cheat and prints a wildly high Sharpe; with the
    default lag=1 the edge disappears. This is the core same-bar guarantee."""
    prices = _synthetic_prices()
    same_bar_ret = prices.pct_change()           # known at close t (uses P[t], P[t-1])
    weights = np.sign(same_bar_ret).fillna(0.0)

    cheat = run_backtest(prices, weights, cost_bps=0, execution_lag=0)
    honest = run_backtest(prices, weights, cost_bps=0, execution_lag=1)

    assert metrics.sharpe(cheat.returns) > 10          # same-bar look-ahead leaks hugely
    assert metrics.sharpe(honest.returns) < 3          # one-day lag removes the edge
    assert honest.returns.notna().sum() > 0


def test_backtest_costs_reduce_returns():
    prices = _synthetic_prices()
    rng = np.random.default_rng(1)
    w = pd.DataFrame(rng.normal(size=prices.shape), index=prices.index, columns=prices.columns)
    free = run_backtest(prices, w, cost_bps=0)
    pricey = run_backtest(prices, w, cost_bps=50)
    assert pricey.returns.sum() < free.returns.sum()


def test_ledger_roundtrip(tmp_path):
    path = tmp_path / "led.jsonl"
    ledger.record({"id": "x1", "thesis": "trend following on bonds", "taxonomy": ["trend_following"],
                   "feature_families": ["price"], "cycle": 1, "status": "proposed"}, path=path)
    assert len(ledger.load(path)) == 1
    occ = ledger.occupied_regions(cycle=1, path=path)
    assert occ.get("trend_following") == 1
    dup = ledger.novelty_check("trend following on bonds", ["trend_following"], cycle=1, path=path)
    assert dup["max_jaccard"] > 0.5
