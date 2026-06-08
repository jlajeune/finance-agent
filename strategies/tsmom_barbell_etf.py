"""Barbell cross-asset time-series momentum on a 6-ETF basket (long-flat, risk-parity).

Lens: trend_following (time_series_momentum sub-tilt). Seeded by cycle-3 lit-scout web
research: Moskowitz, Ooi & Pedersen (2012) "Time Series Momentum"; and 2025 work on
trend-premia *horizon redundancy* (arXiv 2510.23150) showing the medium (~6-month / 125d)
trend horizon is largely spanned by the combination of a fast and a slow horizon.

Economic mechanism
------------------
Time-series momentum is a robust, multi-decade, cross-asset premium: an asset that has
been trending up tends to keep trending over the next month. The standard behavioral story
is *under-reaction to information then delayed over-reaction* (Moskowitz-Ooi-Pedersen),
reinforced by structural flows (CTA/risk-parity rebalancing, hedging demand) that diffuse
slowly. The single most reliable empirical fact about trend, however, is that its *Sharpe*
comes from **cross-asset diversification**, not from any one market: a basket spanning
equities (SPY, QQQ, IWM), duration (TLT), gold (GLD) and credit (HYG) lets the independent
trend bets net out idiosyncratic whipsaw and deliver a smoother, crisis-convex payoff.

Why a BARBELL of horizons (and why the medium horizon is EXCLUDED)
-----------------------------------------------------------------
We estimate trend at two deliberately separated horizons — a SHORT (~20d) and a LONG
(~250-500d) trend — and equal-weight them. A short trend captures fast regime turns
(reduces drawdown latency); a long trend captures the durable risk-premium component
(higher hit-rate, lower turnover). The 2025 redundancy result (arXiv 2510.23150) shows the
MEDIUM (~125d) horizon is approximately a linear combination of the fast and slow ones, so
adding it buys almost no incremental diversification while adding turnover and an extra
researcher degree of freedom. We therefore omit it on parsimony grounds — a falsifiable
design choice, not a tuning hack.

Trend estimator
---------------
Per asset and horizon we use the SIGN of a fitted least-squares linear-trend slope on log
price (more stable OOS and lower-turnover than raw past-return sign or a single crossover),
then EMA-smooth the {-1,+1} slope-sign before sizing so the position does not flicker.

Sizing: LONG-FLAT, inverse-vol (risk parity)
-------------------------------------------
The combined smoothed signal is mapped LONG-FLAT per asset: weight in {0, +1} (we do NOT
short — shorting trend in bonds/credit/gold is fragile and costly here). Active longs are
then weighted by INVERSE trailing realized volatility across the basket so no single asset
dominates the book. Net exposure is therefore VARIABLE (sits partly in cash when assets are
trend-flat), so SPEC.gross_leverage = None and gross is capped <= 1 (no true leverage).

Timing-luck guard (REQUIRED)
----------------------------
A single (short, long) lookback pair and a single rebalance day is a coin-flip on
"timing luck". We instead ENSEMBLE over a small grid of (short, long) lookback pairs AND a
set of staggered monthly rebalance offsets, computing target weights for each member and
AVERAGING them. The strategy is only kept if it is robust to the exact lookback/offset —
the ensemble both delivers that robustness and damps turnover (members rebalance on
different days, so the book moves a little every day instead of jumping monthly).

Hysteresis / no-trade band
--------------------------
Each ensemble member uses signal HYSTERESIS: the smoothed slope-sign must cross a small
threshold band (not merely zero) to flip on/off, and per-member weights are only refreshed
on that member's monthly rebalance dates, then held forward — suppressing churn.

Benchmarks & falsification
--------------------------
Judged on Sharpe AND max drawdown vs TWO benchmarks: (1) buy-and-hold SPY, and (2) an
equal-weight / risk-parity buy-and-hold of the SAME 6-ETF basket. Falsified if:
* Net-of-cost Sharpe does NOT beat the 6-ETF buy-and-hold basket (then the trend timing
  adds nothing beyond static diversification — the whole claim);
* Max drawdown is NOT reduced vs both benchmarks (trend's crisis-convexity failed);
* Results hinge on a single (short,long) pair or rebalance offset (no plateau across the
  ensemble grid -> it is timing luck / overfit, not a premium);
* Turnover/costs erase the edge (long-flat + monthly + bands are meant to prevent this);
* Re-adding the excluded ~125d medium horizon materially changes results (would refute the
  redundancy rationale).

Data limitations
----------------
Price-only (adjusted closes via yfinance; the 6 ETFs are in the default universe). Cash leg
modeled at 0% — conservative for the de-risked / trend-flat periods (a real T-bill yield
only helps). Missing/short-history tickers are skipped gracefully (weight 0).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from finance_agent.strategy import StrategySpec

BASKET = ["SPY", "QQQ", "IWM", "TLT", "GLD", "HYG"]

# Timing-luck ensemble grid: (short, long) trend horizons (days). Medium ~125d EXCLUDED.
LOOKBACK_PAIRS = [(15, 250), (20, 350), (25, 500)]
# Staggered monthly rebalance offsets (in trading days within the ~21d cycle).
REBAL_OFFSETS = [0, 7, 14]

SPEC = StrategySpec(
    id="tsmom_barbell_etf",
    thesis=(
        "Barbell cross-asset time-series momentum on a diversified 6-ETF basket (SPY, QQQ, "
        "IWM, TLT, GLD, HYG). Per asset, trend is a BARBELL of a short (~20d) and a long "
        "(~250-500d) fitted linear-trend slope sign — deliberately EXCLUDING the medium "
        "(~125d) horizon, which 2025 research shows is spanned by the fast+slow pair. "
        "Signals are EMA-smoothed with hysteresis and mapped LONG-FLAT ({0,+1}); active "
        "longs are inverse-vol (risk-parity) weighted with gross capped <=1, so net "
        "exposure is variable (cash when trend-flat). A timing-luck guard ensembles over "
        "several lookback pairs and staggered monthly rebalance offsets, averaging weights "
        "for robustness and low turnover. Exploits slow information diffusion / under-"
        "reaction; the Sharpe edge comes from cross-asset trend diversification."
    ),
    taxonomy=["trend_following", "time_series_momentum"],
    feature_families=["price"],
    universe="default",
    params={
        "basket": BASKET,
        "lookback_pairs": LOOKBACK_PAIRS,
        "rebal_offsets": REBAL_OFFSETS,
        "rebalance": 21,
        "ema_span": 10,
        "vol_window": 60,
        "hysteresis": 0.15,
        "gross_cap": 1.0,
    },
    author="quant-researcher",
    references=[
        "Moskowitz, Ooi & Pedersen (2012), Time Series Momentum, JFE",
        "Trend premia horizon redundancy (2025), arXiv:2510.23150",
        "Hurst, Ooi & Pedersen (2017), A Century of Evidence on Trend-Following Investing",
    ],
    gross_leverage=None,  # long-flat => VARIABLE net exposure (cash<->basket); no renorm
)


def _slope_sign(log_px: pd.Series, window: int) -> pd.Series:
    """Sign of the trailing least-squares slope of log price over ``window`` days.

    Uses a closed-form rolling OLS slope (cov(t, y) / var(t)) over a fixed time index
    0..window-1, so it is a pure trailing computation — no look-ahead. Returns {-1,0,+1}.
    """
    n = window
    t = np.arange(n, dtype=float)
    t_mean = t.mean()
    t_dev = t - t_mean
    denom = float((t_dev ** 2).sum())  # constant var(t) * n

    def _fit(y: np.ndarray) -> float:
        if np.isnan(y).any():
            return np.nan
        return float((t_dev * (y - y.mean())).sum() / denom)

    slope = log_px.rolling(n, min_periods=n).apply(_fit, raw=True)
    return np.sign(slope)


def _member_weights(
    prices: pd.DataFrame,
    basket: list[str],
    short_lb: int,
    long_lb: int,
    rebal: int,
    offset: int,
    ema_span: int,
    vol_window: int,
    hysteresis: float,
    gross_cap: float,
) -> pd.DataFrame:
    """Target weights for ONE ensemble member (one lookback pair + one rebalance offset)."""
    idx = prices.index
    cols = prices.columns
    w = pd.DataFrame(0.0, index=idx, columns=cols)

    available = [t for t in basket if t in cols and prices[t].notna().sum() > long_lb + 5]
    if not available:
        return w

    # Per-asset long-flat state (on this member's own grid), then inverse-vol size.
    state = pd.DataFrame(0.0, index=idx, columns=available)
    invvol = pd.DataFrame(np.nan, index=idx, columns=available)

    for t in available:
        px = prices[t].astype(float)
        log_px = np.log(px)

        # Barbell: short + long fitted-slope sign, equal-weight, then EMA-smooth.
        s_short = _slope_sign(log_px, short_lb)
        s_long = _slope_sign(log_px, long_lb)
        combo = 0.5 * (s_short + s_long)  # in [-1, 1]
        smooth = combo.ewm(span=ema_span, min_periods=ema_span).mean()

        # Hysteresis -> long-flat {0,1}: turn ON above +band, OFF below -band, else hold.
        on = pd.Series(0.0, index=idx)
        cur = 0.0
        sm = smooth.to_numpy()
        for i in range(len(idx)):
            v = sm[i]
            if np.isfinite(v):
                if v >= hysteresis:
                    cur = 1.0
                elif v <= -hysteresis:
                    cur = 0.0
            on.iloc[i] = cur
        state[t] = on

        daily = px.pct_change()
        rv = daily.rolling(vol_window, min_periods=max(20, vol_window // 2)).std() * np.sqrt(252)
        invvol[t] = 1.0 / rv.replace(0.0, np.nan)

    # Build risk-parity weights among the ACTIVE longs, gross capped, on rebalance dates.
    rebal_dates = idx[offset::rebal]
    raw = state * invvol  # inverse-vol weight only where state==1
    row_sum = raw.sum(axis=1)
    target = raw.div(row_sum.replace(0.0, np.nan), axis=0).fillna(0.0)
    gross = target.sum(axis=1)
    scale = np.minimum(1.0, gross_cap / gross.replace(0.0, np.nan)).fillna(0.0)
    target = target.mul(scale, axis=0)  # gross <= gross_cap; 0 when nothing is on

    # Refresh only on this member's rebalance dates; hold forward otherwise.
    held = pd.DataFrame(np.nan, index=idx, columns=available)
    for dt in rebal_dates:
        held.loc[dt] = target.loc[dt]
    held = held.ffill().fillna(0.0)

    for t in available:
        w[t] = held[t]
    return w


def generate_weights(
    prices: pd.DataFrame,
    basket: list[str] | None = None,
    lookback_pairs: list | None = None,
    rebal_offsets: list | None = None,
    rebalance: int = 21,
    ema_span: int = 10,
    vol_window: int = 60,
    hysteresis: float = 0.15,
    gross_cap: float = 1.0,
) -> pd.DataFrame:
    """Ensemble-averaged long-flat risk-parity barbell-TSMOM weights (dates x tickers).

    Only trailing data is used at each row; the engine adds the 1-day execution lag.
    The timing-luck guard averages target weights across every (lookback pair, rebalance
    offset) ensemble member, so no single magic lookback or rebalance day drives the book.
    """
    basket = basket if basket is not None else BASKET
    lookback_pairs = lookback_pairs if lookback_pairs is not None else LOOKBACK_PAIRS
    rebal_offsets = rebal_offsets if rebal_offsets is not None else REBAL_OFFSETS

    acc = pd.DataFrame(0.0, index=prices.index, columns=prices.columns)
    n_members = 0
    for (short_lb, long_lb) in lookback_pairs:
        for offset in rebal_offsets:
            acc = acc.add(
                _member_weights(
                    prices, basket, short_lb, long_lb, rebalance, offset,
                    ema_span, vol_window, hysteresis, gross_cap,
                ),
                fill_value=0.0,
            )
            n_members += 1

    if n_members:
        acc = acc / n_members
    return acc
