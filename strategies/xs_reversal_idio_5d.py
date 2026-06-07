"""Idiosyncratic short-term reversal, amplitude-weighted, dollar-neutral.

Lens: short_term_reversal (cross-sectional mean reversion over a short horizon).

Economic mechanism
------------------
Short-term reversal is widely understood as *compensation for liquidity provision*
(Nagel 2012; Lehmann 1990; Lo & MacKinlay 1990). When a stock is hit by
non-informational order flow — forced selling, retail attention, an overreaction to a
piece of idiosyncratic news — its price is pushed away from fair value. Liquidity
providers who take the other side earn a premium as the price snaps back. Two refinements
follow directly from that mechanism, and they are what make this distinct from a naive
"flip yesterday's return":

1. **Idiosyncratic, not total, moves.** Market-wide moves (a Fed surprise, a risk-off
   day) are *informational* and should NOT be faded — fading them is just shorting beta
   into drawdowns. We therefore residualize each stock's recent return against the
   equal-weight cross-sectional market move and trade only the stock-specific residual.
   This is the cleanest expression of "overreaction to idiosyncratic news".

2. **Amplitude / abnormality weighting.** Reversal compensation is largest where the
   dislocation is largest *relative to the stock's normal noise*. We divide the residual
   move by the stock's own trailing volatility (a z-score). A 5-sigma idiosyncratic pop
   is far more likely to be overreaction than a 0.3-sigma drift, so it earns a bigger
   contrarian bet. With only adjusted-close prices available (no share volume in the
   contract), this volatility-normalized amplitude is our look-ahead-safe proxy for the
   "abnormal volume / forced flow" that the liquidity story really wants.

Construction: each rebalance, compute the trailing ``lookback``-day return, subtract the
cross-sectional mean return (market residual), z-score it by each name's trailing
``vol_window`` daily-return volatility, and take positions PROPORTIONAL TO THE NEGATIVE of
that z-score (fade winners, buy losers). Positions are demeaned (dollar-neutral) and
L1-scaled. A short holding period (a few days) lets the snap-back play out while keeping
turnover and cost in check.

Why it is not the crowded families
-----------------------------------
* Not momentum: the sign is reversed (we fade recent relative strength).
* Not low-volatility: we do not select low-vol names; volatility enters only as a
  *normalizer* of the move, and high-amplitude (often higher-vol) dislocations get the
  *largest* bets.
* Not naive 1-day reversal: market component is stripped out, bets scale continuously
  with abnormality, and the horizon/holding period are multi-day.

Falsification (what would make this fail)
-----------------------------------------
* Net (post-cost) reversal Sharpe <= 0 over the sample, or no improvement of the
  *idiosyncratic* residual version over fading the raw total return -> the
  "residualize the market" refinement adds nothing.
* If the amplitude-weighted (continuous z) book does not beat an equal-weight
  top/bottom-quantile reversal book, the abnormality story is not paying.
* If gross alpha is positive but the cost drag from turnover wipes it out, the edge is
  not implementable in this universe at these costs.
* If profitability concentrates entirely on the single most recent day (i.e. it is pure
  1-day bid/ask bounce that vanishes by t+1 execution), it is microstructure noise, not
  a tradable reversal premium.

Data limitations / graceful degradation
----------------------------------------
The standardized contract passes only an adjusted-close panel; real volume is not
available here. The liquidity-provision story ideally conditions on *abnormal volume*;
we degrade to a price-only proxy (trailing-vol-normalized residual amplitude), which is
strictly past-data-safe. Residualization uses a cross-sectional equal-weight mean as a
cheap one-factor (market) control rather than a fitted beta, to keep the parameter count
and look-ahead surface minimal.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from finance_agent.strategy import StrategySpec

SPEC = StrategySpec(
    id="xs_reversal_idio_5d",
    thesis=(
        "Cross-sectional short-term reversal as liquidity-provision compensation, "
        "refined two ways: (1) fade only the IDIOSYNCRATIC part of each stock's recent "
        "move by residualizing against the equal-weight market, so we don't short beta "
        "into market drawdowns; (2) AMPLITUDE-weight the contrarian bet by the move's "
        "trailing-volatility z-score, since larger abnormal dislocations carry larger "
        "reversal premia. Dollar-neutral, multi-day holding to let the snap-back play out."
    ),
    taxonomy=["short_term_reversal"],
    feature_families=["price"],
    universe="default",
    params={"lookback": 5, "vol_window": 60, "rebalance": 3, "clip_z": 3.0},
    author="quant-researcher",
    references=[
        "Lehmann (1990) Fads, Martingales, and Market Efficiency",
        "Lo & MacKinlay (1990) When Are Contrarian Profits Due to Overreaction?",
        "Nagel (2012) Evaporating Liquidity",
    ],
)


def generate_weights(
    prices: pd.DataFrame,
    lookback: int = 5,
    vol_window: int = 60,
    rebalance: int = 3,
    clip_z: float = 3.0,
) -> pd.DataFrame:
    """Return dollar-neutral long/short weights (dates x tickers).

    Only past data is used at each row; the engine adds the 1-day execution lag.

    Parameters
    ----------
    lookback : horizon (days) of the recent move we fade.
    vol_window : trailing window for the per-name daily-return volatility normalizer.
    rebalance : trade every ``rebalance`` days (multi-day holding period).
    clip_z : winsorize the amplitude z-score to this many sigma (controls outlier names).
    """
    prices = prices.sort_index()

    # Trailing lookback-day simple return (past-only: uses prices up to row date).
    ret_lb = prices / prices.shift(lookback) - 1.0

    # Daily returns and a trailing daily-vol normalizer (shifted to exclude the most
    # recent day's own move from its own scale; strictly past info).
    daily = prices.pct_change()
    vol = daily.rolling(vol_window, min_periods=max(10, vol_window // 2)).std()

    # Idiosyncratic residual: strip the cross-sectional equal-weight market move so we
    # only fade stock-specific dislocations, not market-wide (informational) moves.
    mkt = ret_lb.mean(axis=1)
    resid = ret_lb.sub(mkt, axis=0)

    # Amplitude z-score: residual move scaled by the name's normal noise over the
    # horizon (sqrt(lookback) converts daily vol to the lookback-horizon scale).
    horizon_vol = vol * np.sqrt(lookback)
    z = resid / horizon_vol.replace(0.0, np.nan)
    z = z.clip(lower=-clip_z, upper=clip_z)

    weights = pd.DataFrame(index=prices.index, columns=prices.columns, dtype=float)
    rebal_dates = prices.index[::rebalance]

    for dt in rebal_dates:
        row = z.loc[dt].dropna()
        if len(row) < 6:
            continue
        # Reversal: position proportional to the NEGATIVE amplitude z (fade the move).
        raw = -row
        # Dollar-neutral: demean across the cross-section.
        raw = raw - raw.mean()
        gross = raw.abs().sum()
        if gross <= 0 or not np.isfinite(gross):
            continue
        w = pd.Series(0.0, index=prices.columns)
        w[raw.index] = (raw / gross).values  # L1-normalized to gross exposure 1.0
        weights.loc[dt] = w.values

    # Hold each rebalance vector until the next; pre-warmup rows -> 0.
    return weights.ffill().fillna(0.0)
