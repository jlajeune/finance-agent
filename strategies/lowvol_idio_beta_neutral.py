"""Beta-neutral idiosyncratic-volatility low-vol anomaly.

This is a *low_volatility* strategy that deliberately differs from the textbook
"low-beta" or "inverse-vol" construction. Instead of sorting on *total* realized
volatility (which is dominated by market beta and sector co-movement), we sort on
*idiosyncratic* volatility: the standard deviation of the residual after regressing
each stock's daily returns on a contemporaneous equal-weight market return over a
trailing window. We go LONG the lowest-idio-vol names and SHORT the highest, then
make the book beta-neutral so the bet is purely on idiosyncratic risk, not on a
disguised low-beta tilt.

Economic / behavioral mechanism
-------------------------------
1. Lottery preference (Ang, Hodrick, Xing & Zhang 2006; Bali, Cakici & Whitelaw
   2011). High-idiosyncratic-vol stocks have lottery-like, positively-skewed payoffs.
   Behaviorally-biased investors overpay for that small chance of a large gain,
   pushing such stocks' prices up and their subsequent returns *down*. The mirror
   image: dull, low-idio-vol stocks are under-demanded and earn a premium.
2. Arbitrage asymmetry (Stambaugh, Yu & Yuan 2015). Overpricing is harder to correct
   than underpricing because shorting is costly/constrained, so the overpriced
   high-idio-vol leg stays mispriced longer — the short leg, not the long leg, carries
   much of the anomaly. That makes an explicit short of high-idio-vol stocks the
   right structural expression.
Both forces are distinct from the leverage-constraint story behind plain low-beta,
and distinct from momentum (no return-direction sort) and short-term reversal
(no recent-return sort, monthly cadence, residual-vol not price-level signal).

Construction
------------
- Compute daily log returns; estimate an equal-weight cross-sectional market return
  each day (a cheap, look-ahead-safe market proxy from the universe itself).
- Over a trailing window, regress each stock on the market (beta + intercept) using
  only past data; idio-vol = std of residuals; beta is reused for neutralization.
- Rank cross-sectionally on idio-vol: long bottom quantile, short top quantile.
- Solve simple scalars so the long and short legs are dollar-neutral AND the
  portfolio's net market beta is ~0 (beta-neutral), so we isolate the idio bet.
- Monthly rebalance, weights carried forward between rebalances.

Falsification / failure conditions
----------------------------------
- If, in out-of-sample backtest, the LOW-idio-vol minus HIGH-idio-vol spread has a
  Sharpe indistinguishable from zero (or negative) net of costs, the premium is gone.
- If essentially all of the P&L comes from the long leg with the short leg flat, the
  arbitrage-asymmetry mechanism is wrong for this universe.
- If realized portfolio beta is materially non-zero, the "idio not beta" claim fails
  and results may just be repackaged low-beta.
- If performance vanishes once we control for size/illiquidity (high-idio-vol names
  are often small), the effect is a liquidity artifact, not a behavioral premium.

Data limitations
----------------
Uses only price data (yfinance default universe). The "market" is an equal-weight
proxy built from the traded universe rather than a true cap-weighted index, and there
are no real borrow costs for the short leg — both are acknowledged approximations.
Fundamental controls (size, illiquidity) noted above are not available this round, so
those falsification checks are deferred to later analysis, not enforced in-code.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from finance_agent.strategy import StrategySpec

SPEC = StrategySpec(
    id="lowvol_idio_beta_neutral",
    thesis=(
        "Beta-neutral idiosyncratic-volatility low-vol: each month regress every "
        "stock's daily returns on an equal-weight market proxy over a trailing window, "
        "take the residual (idiosyncratic) volatility, go long the lowest-idio-vol "
        "names and short the highest, then neutralize net market beta. Captures the "
        "lottery-preference / arbitrage-asymmetry anomaly (dull stocks underpriced, "
        "lottery-like high-idio-vol stocks overpriced) rather than a disguised low-beta "
        "tilt; dollar-neutral and beta-neutral, rebalanced monthly."
    ),
    taxonomy=["low_volatility"],
    feature_families=["price"],
    universe="default",
    params={"window": 126, "quantile": 0.30, "rebalance": 21, "min_names": 8},
    author="quant-researcher",
    references=[
        "Ang, Hodrick, Xing & Zhang (2006)",
        "Bali, Cakici & Whitelaw (2011)",
        "Stambaugh, Yu & Yuan (2015)",
    ],
)


def generate_weights(
    prices: pd.DataFrame,
    window: int = 126,
    quantile: float = 0.30,
    rebalance: int = 21,
    min_names: int = 8,
) -> pd.DataFrame:
    """Return dollar-neutral, beta-neutral long-low/short-high idio-vol weights.

    Only past data is used at each row; the engine adds the 1-day execution lag.
    """
    prices = prices.sort_index()
    log_ret = np.log(prices).diff()

    # Equal-weight cross-sectional market proxy, built from the universe itself.
    # At each date this is just the mean of that date's returns -> no look-ahead.
    mkt = log_ret.mean(axis=1)

    weights = pd.DataFrame(index=prices.index, columns=prices.columns, dtype=float)
    rebal_dates = prices.index[::rebalance]

    for dt in rebal_dates:
        i = prices.index.get_loc(dt)
        if i < window:
            continue
        # Trailing window strictly up to and including dt (past data only).
        win = log_ret.iloc[i - window + 1 : i + 1]
        m = mkt.iloc[i - window + 1 : i + 1]

        mc = m - m.mean()
        var_m = float((mc * mc).sum())
        if var_m <= 0:
            continue

        idio = pd.Series(index=prices.columns, dtype=float)
        beta = pd.Series(index=prices.columns, dtype=float)
        for tic in prices.columns:
            y = win[tic]
            if y.notna().sum() < window // 2:
                continue
            yc = y - y.mean()
            # OLS slope on demeaned series; align on common non-NaN dates.
            pair = pd.concat([yc, mc], axis=1).dropna()
            if len(pair) < window // 2:
                continue
            yy = pair.iloc[:, 0].values
            xx = pair.iloc[:, 1].values
            denom = float((xx * xx).sum())
            if denom <= 0:
                continue
            b = float((yy * xx).sum() / denom)
            resid = yy - b * xx
            beta[tic] = b
            idio[tic] = float(np.std(resid))

        idio = idio.dropna()
        if len(idio) < min_names:
            continue

        lo_th = idio.quantile(quantile)
        hi_th = idio.quantile(1 - quantile)
        longs = idio[idio <= lo_th].index
        shorts = idio[idio >= hi_th].index
        if len(longs) == 0 or len(shorts) == 0:
            continue

        # Start dollar-neutral, equal-weight within each leg.
        w = pd.Series(0.0, index=prices.columns)
        w[longs] = 0.5 / len(longs)
        w[shorts] = -0.5 / len(shorts)

        # Beta-neutralize: scale the two legs so net portfolio beta ~ 0 while keeping
        # gross exposure fixed. Let bL, bS be leg betas (dollar-weighted).
        bL = float((w[longs] * beta.reindex(longs)).sum())   # >0 contribution
        bS = float((w[shorts] * beta.reindex(shorts)).sum())  # <0 contribution
        # Solve a*bL + s*bS = 0 with a+|s| gross preserved (a,s>0 scalars on legs).
        if abs(bL) > 1e-12 and abs(bS) > 1e-12:
            # net beta = a*bL + s*bS ; choose a=|bS|, s=|bL| up to sign then renorm.
            a = abs(bS)
            s = abs(bL)
            w[longs] = w[longs] * a
            w[shorts] = w[shorts] * s
            gross = w.abs().sum()
            if gross > 0:
                w = w / gross  # gross-leverage 1; engine may renormalize anyway.

        weights.loc[dt] = w.values

    return weights.ffill().fillna(0.0)
