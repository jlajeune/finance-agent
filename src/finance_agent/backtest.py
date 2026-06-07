"""A small, transparent, vectorized backtest engine.

Design goals
------------
* **Look-ahead safe by construction.** Weights are shifted forward by
  ``execution_lag`` (default 1 day): a target weight derived from day *t*'s data is
  applied to day *t+1*'s return. Strategies physically cannot trade on information
  they haven't seen yet.
* **Costs are explicit.** Turnover is charged at ``cost_bps`` basis points per unit
  of one-way notional traded, so a strategy can't win purely by churning.
* **Weights, not orders.** A strategy outputs target portfolio weights per date per
  asset (longs positive, shorts negative). This keeps the contract simple and the
  engine fully vectorized.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from . import metrics


@dataclass
class BacktestResult:
    """Container for a backtest's outputs."""

    returns: pd.Series           # net portfolio returns per period
    gross_returns: pd.Series     # before costs
    weights: pd.DataFrame        # the (lagged) weights actually held
    turnover: pd.Series          # per-period one-way turnover
    cost_bps: float
    periods_per_year: int
    meta: dict = field(default_factory=dict)

    @property
    def equity_curve(self) -> pd.Series:
        return (1 + self.returns.fillna(0)).cumprod()

    def stats(self) -> dict:
        s = metrics.summary(self.returns, self.periods_per_year)
        s["avg_turnover"] = float(self.turnover.mean())
        s["gross_sharpe"] = metrics.sharpe(self.gross_returns, periods_per_year=self.periods_per_year)
        s["cost_drag_ann"] = (
            metrics.annualized_return(self.gross_returns, self.periods_per_year)
            - metrics.annualized_return(self.returns, self.periods_per_year)
        )
        return s


def normalize_weights(weights: pd.DataFrame, gross_leverage: float | None = 1.0) -> pd.DataFrame:
    """Optionally scale each row so total absolute exposure == ``gross_leverage``.

    Pass ``gross_leverage=None`` to leave weights untouched (e.g. for a strategy that
    deliberately runs variable exposure). Rows that are all-zero are left as zero.
    """
    if gross_leverage is None:
        return weights
    gross = weights.abs().sum(axis=1)
    scale = gross.replace(0, np.nan)
    out = weights.div(scale, axis=0).mul(gross_leverage)
    return out.fillna(0.0)


def run_backtest(
    prices: pd.DataFrame,
    weights: pd.DataFrame,
    cost_bps: float = 5.0,
    execution_lag: int = 1,
    periods_per_year: int = metrics.TRADING_DAYS,
    gross_leverage: float | None = 1.0,
    meta: dict | None = None,
) -> BacktestResult:
    """Run a weight-based backtest.

    Parameters
    ----------
    prices : (dates x tickers) adjusted close prices.
    weights : (dates x tickers) target weights, same columns as ``prices``.
    cost_bps : transaction cost per unit one-way turnover, in basis points.
    execution_lag : periods between signal and execution (>=1 prevents look-ahead).
    gross_leverage : if set, each period's weights are scaled to this gross exposure.
    """
    prices = prices.sort_index()
    asset_returns = prices.pct_change()

    # Align weights onto the price grid and apply the execution lag.
    w = weights.reindex(index=asset_returns.index, columns=asset_returns.columns)
    w = normalize_weights(w.fillna(0.0), gross_leverage)
    held = w.shift(execution_lag).fillna(0.0)

    gross = (held * asset_returns).sum(axis=1)
    turn = (held - held.shift(1).fillna(0.0)).abs().sum(axis=1)
    costs = turn * (cost_bps / 1e4)
    net = gross - costs

    return BacktestResult(
        returns=net,
        gross_returns=gross,
        weights=held,
        turnover=turn,
        cost_bps=cost_bps,
        periods_per_year=periods_per_year,
        meta=meta or {},
    )
