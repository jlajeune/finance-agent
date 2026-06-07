"""Volatility-targeted equity-index exposure (vol-scaling overlay on SPY).

Lens: volatility_timing (with an implicit time_series_momentum tilt via the leverage
effect). Seeded by cycle-2 web research (lit-scout): Man Group "The Impact of
Volatility Targeting"; Research Affiliates "Harnessing Volatility Targeting"; Xu (2024)
"Improving Volatility-Managed Portfolios in Real Time" (SSRN 4778937).

Economic mechanism
------------------
Equity volatility is *persistent* (it clusters) and *negatively* correlated with returns
(the leverage effect): high-vol regimes tend to persist and contain the left-tail
crashes. Holding the index but scaling exposure inversely to its own recent realized
volatility — to target a roughly constant ex-ante vol — therefore (1) cuts exposure into
high-vol regimes before much of the drawdown plays out, and (2) leans back in after calm
periods. The documented benefit is concentrated in **tail/drawdown reduction and a higher
Sharpe**, not a higher mean return. The effect is specific to risk assets (equities,
credit), which is exactly what SPY is — that is why this beats applying the same overlay
to bonds/commodities.

Why it fits this project's constraints (cycle-1 lessons)
--------------------------------------------------------
* **Time-series, no cross-section, no short leg** → immune to the survivorship bias that
  sank the cycle-1 low-vol strategy.
* **Low turnover by construction** → the weight only moves when the vol estimate moves;
  we further damp it with a weekly rebalance and a no-trade band, so it survives costs.
* **Price-only** → just SPY adjusted closes from yfinance (already cached).

This is a *market-timing* overlay: exposure varies between 0 and ``max_leverage`` with the
remainder in cash (modeled at 0% — conservative; a real T-bill yield would only help).
It therefore sets ``SPEC.gross_leverage = None`` so the engine does NOT renormalize the
book to fully-invested.

Falsification / failure conditions
----------------------------------
* If net-of-cost Sharpe does NOT beat buy-and-hold SPY (the correct benchmark), the
  overlay adds nothing — vol-targeting's entire claim is risk-adjusted improvement.
* If max drawdown is not reduced vs buy-and-hold, the tail-reduction mechanism failed.
* If the result only holds for one vol window / target (no plateau in the parameter
  sweep), it is fit, not real.
* If turnover/costs erase the Sharpe edge, it is not implementable here.

Data limitations
----------------
Cash leg modeled at 0% (no FRED T-bill yield wired in this cycle) — conservative for the
de-levered periods. SPY history via yfinance; no leverage above ``max_leverage`` is used,
so this is implementable as a plain SPY/cash allocation.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from finance_agent.strategy import StrategySpec

SPEC = StrategySpec(
    id="voltarget_spy",
    thesis=(
        "Volatility-targeted SPY exposure: hold the equity index but scale the weight "
        "inversely to its trailing 60-day realized volatility to target ~11% annual vol, "
        "capped at 1x (SPY-vs-cash, deleveraging into vol spikes). Exploits volatility "
        "persistence + the leverage effect to cut left-tail drawdowns and raise the "
        "Sharpe vs buy-and-hold. Weekly rebalance with a no-trade band keeps turnover and "
        "costs low. Time-series and long-only, so it is immune to the survivorship bias "
        "that sank cross-sectional cycle-1 ideas."
    ),
    taxonomy=["volatility_timing", "time_series_momentum"],
    feature_families=["price"],
    universe="default",
    params={
        "asset": "SPY",
        "vol_window": 60,
        "target_vol": 0.11,
        "max_leverage": 1.0,
        "rebalance": 5,
        "band": 0.05,
    },
    author="quant-researcher",
    references=[
        "Man Group, The Impact of Volatility Targeting",
        "Research Affiliates, Harnessing Volatility Targeting in Multi-Asset Portfolios",
        "Xu (2024), Improving Volatility-Managed Portfolios in Real Time, SSRN 4778937",
        "Moskowitz, Ooi & Pedersen (2012), Time Series Momentum",
    ],
    gross_leverage=None,  # variable net exposure (cash<->SPY) — do NOT renormalize
)


def generate_weights(
    prices: pd.DataFrame,
    asset: str = "SPY",
    vol_window: int = 60,
    target_vol: float = 0.11,
    max_leverage: float = 1.0,
    rebalance: int = 5,
    band: float = 0.05,
) -> pd.DataFrame:
    """Return weights (dates x tickers) with a single varying long position in ``asset``.

    Only past data is used at each row; the engine adds the 1-day execution lag, so the
    vol estimate at date t (known at t's close) is traded at t+1.

    Parameters
    ----------
    vol_window : trailing window (days) for realized-vol estimation.
    target_vol : annualized volatility target.
    max_leverage : cap on the weight (1.0 => long-only SPY/cash, no true leverage).
    rebalance : trade cadence in days (weekly = 5) — damps turnover.
    band : no-trade band; only move the weight if the new target differs by >= this.
    """
    if asset not in prices.columns:
        raise ValueError(f"asset {asset!r} not in price universe")

    px = prices[asset].astype(float)
    daily = px.pct_change()
    realized = daily.rolling(vol_window, min_periods=max(20, vol_window // 2)).std() * np.sqrt(252)

    # Inverse-vol target exposure, capped. (No look-ahead: realized[t] uses returns <= t.)
    target = (target_vol / realized.replace(0.0, np.nan)).clip(upper=max_leverage)

    weights = pd.DataFrame(0.0, index=prices.index, columns=prices.columns)
    w_asset = pd.Series(index=prices.index, dtype=float)

    rebal_dates = prices.index[::rebalance]
    cur = np.nan
    for dt in rebal_dates:
        t = target.loc[dt]
        # Only update the held weight when the target has moved beyond the no-trade band.
        if np.isfinite(t) and (np.isnan(cur) or abs(t - cur) >= band):
            cur = float(t)
        if np.isfinite(cur):
            w_asset.loc[dt] = cur

    # Hold each decision forward until the next rebalance; pre-warmup -> 0 (in cash).
    weights[asset] = w_asset.ffill().fillna(0.0)
    return weights
