"""Example strategy: cross-sectional 12-1 momentum, dollar-neutral long/short.

This is a *reference implementation* showing the contract every generated strategy
must satisfy. It is intentionally a well-known factor so new strategies have a clear,
documented template to differentiate against (the ledger will mark this family as
occupied). Generators should NOT clone it — they should explore other regions.

Economic rationale: stocks that outperformed over the past ~12 months (skipping the
most recent month to avoid short-term reversal) tend to keep outperforming over the
next month — a robust, widely-documented anomaly (Jegadeesh & Titman 1993).
"""

from __future__ import annotations

import pandas as pd

from finance_agent.strategy import StrategySpec

SPEC = StrategySpec(
    id="example_xs_mom_12_1",
    thesis=(
        "Cross-sectional momentum: rank the universe by trailing 12-month return "
        "skipping the most recent month, go long the top tercile and short the bottom "
        "tercile, dollar-neutral, rebalanced monthly. Captures the momentum anomaly "
        "while the 1-month skip sidesteps short-term reversal."
    ),
    taxonomy=["cross_sectional_momentum"],
    feature_families=["price"],
    universe="default",
    params={"lookback": 252, "skip": 21, "quantile": 0.33, "rebalance": 21},
    author="reference",
    references=["Jegadeesh & Titman (1993)"],
)


def generate_weights(prices: pd.DataFrame, lookback: int = 252, skip: int = 21,
                     quantile: float = 0.33, rebalance: int = 21) -> pd.DataFrame:
    """Return dollar-neutral long/short weights (dates x tickers).

    Uses only past prices at each date; the backtest engine adds the execution lag.
    """
    # Trailing return from t-lookback to t-skip (the classic momentum signal window).
    past = prices.shift(skip)
    signal = past / past.shift(lookback - skip) - 1.0

    # Rebalance rows are set explicitly; all other rows stay NaN so we can ffill the
    # *entire* held row (including intended zeros) until the next rebalance.
    weights = pd.DataFrame(index=prices.index, columns=prices.columns, dtype=float)
    rebal_dates = prices.index[::rebalance]
    for dt in rebal_dates:
        row = signal.loc[dt].dropna()
        if len(row) < 6:
            continue
        hi = row.quantile(1 - quantile)
        lo = row.quantile(quantile)
        longs = row[row >= hi].index
        shorts = row[row <= lo].index
        if len(longs) == 0 or len(shorts) == 0:
            continue
        w = pd.Series(0.0, index=prices.columns)
        w[longs] = 0.5 / len(longs)
        w[shorts] = -0.5 / len(shorts)
        weights.loc[dt] = w.values

    # Carry each rebalance's full weight vector forward; pre-warmup rows -> 0.
    return weights.ffill().fillna(0.0)
