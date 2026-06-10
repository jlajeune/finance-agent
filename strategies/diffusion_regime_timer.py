"""Foraging diffusion-exponent regime timer (Levy-vs-Brownian path memory on SPY).

Lens: path_geometry (new axis) + trend_following. Seeded by the cross-domain backlog
entry B1 (movement-ecology Levy-flight foraging hypothesis applied to price paths).

Economic / behavioral mechanism
-------------------------------
Movement ecology distinguishes a *searching* forager (super-diffusive, Levy-like, long
directed runs) from an *area-restricted* forager (sub-diffusive, choppy, mean-reverting).
The same path geometry shows up in price series: the anomalous-diffusion scaling exponent
of cumulative log returns, MSD(tau) ~ tau^(2H) with generalized Hurst exponent H, measures
**path memory**, not amplitude. H>0.5 is persistent/trending ("the market is searching in
one direction"); H<0.5 is anti-persistent/choppy; H~0.5 is a memoryless random walk.

This is an axis that VIX cannot see. VIX is an *amplitude* (volatility-level) measure; it
cannot tell a low-vol grind-higher (trending, H>0.5) from a low-vol whipsaw (choppy,
H<0.5). The economic edge: trend-following / momentum capture works in persistent regimes
and bleeds (whipsaw, transaction-cost drag) in anti-persistent ones. By gating a plain
50/200 trend rule with the *current diffusion regime*, we ride trends only when the path
itself is behaving super-diffusively, and step to cash when the path turns choppy — which
is precisely when a naive trend rule gives back its gains. The persistence of the edge
rests on (1) a behavioral driver: slow information diffusion + herding produce serially
correlated runs, while crowded/uncertain markets produce reversals; and (2) a structural
driver: regimes are sticky, so a memory measure estimated on the trailing window has
forward content over the next month.

Estimator choice (and the look-ahead trap it avoids)
----------------------------------------------------
H is estimated by **DFA (detrended fluctuation analysis)**, NOT rescaled-range (R/S). R/S
is badly biased on short windows; on a 120-day window that bias is a small-sample artifact
that would masquerade as signal (a look-ahead-flavored trap). DFA detrends each box with a
local linear fit and is the standard robust short-window estimator. H is the slope of
log F(n) on log n across box sizes n in {8,16,32,64} (all <= window/2).

Frozen, pre-registered parameters (NOT fit)
-------------------------------------------
* DFA window           = 120 trading days
* DFA box scales       = {8, 16, 32, 64}
* H z-score window     = 252 trading days  (z over the trailing H-history)
* H_z thresholds       = +/- 0.5
* trend filter         = 50d vs 200d simple MA on price
* exposure mapping (long/flat SPY):
    H_z > +0.5  (super-diffusive / trending) -> ride trend: 1.0 if MA50>MA200 else 0.0
    H_z < -0.5  (sub-diffusive / choppy)     -> de-risk: 0.0
    otherwise   (Brownian / neutral)         -> 0.5
* rebalance cadence    = 5d (weekly), no-trade band = 0.1 on the weight (slow signal)

Look-ahead safety
-----------------
DFA at date t uses only the trailing 120 log returns ending at t. The H-history z-score at
t uses only H values up to t. The 50/200 MAs use only past prices. No negative shifts, no
centered windows, no full-sample normalization. The engine adds the 1-day execution lag.
Until ~120+252 days of history exist the signal is NaN -> held in cash (weight 0).

Falsification / failure conditions
----------------------------------
* If net-of-cost Sharpe does NOT beat buy-hold SPY, static 60/40, AND a VIX-level timer on
  Sharpe AND max drawdown, the path-memory axis adds nothing.
* If it does NOT beat a plain 50/200 trend rule (no Hurst gate), the diffusion gate is
  inert and the whole thesis is dead.
* If H_z has no significant coefficient on next-month SPY returns controlling for VIX
  (non-overlapping monthly + Newey-West HAC), it is redundant with vol.
* If results live on a lone (window, threshold) spike rather than a smooth plateau, it is
  fit, not real. If it dies in the post-2010 OOS subsample, it is regime-lucky.

Data limitations
----------------
SPY adjusted closes only (price family). Cash leg modeled at 0% (conservative for the
de-risked periods). gross_leverage=None so the engine does NOT renormalize the variable
SPY/cash exposure.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from finance_agent.strategy import StrategySpec

SPEC = StrategySpec(
    id="diffusion_regime_timer",
    thesis=(
        "Foraging diffusion-exponent regime timer: estimate the generalized Hurst "
        "exponent H of SPY daily log returns on a trailing 120-day window via DFA "
        "(detrended fluctuation analysis, not biased R/S), z-scored over the trailing "
        "252 days. H>0.5 is a super-diffusive 'searching'/trending path; H<0.5 is a "
        "sub-diffusive choppy/mean-reverting path -- a path-memory axis VIX (an amplitude "
        "measure) cannot see. Gate a plain 50/200 trend rule with the regime: when H_z>+0.5 "
        "ride the trend (1.0 if MA50>MA200 else 0.0), when H_z<-0.5 de-risk to cash, else "
        "hold a neutral 0.5. Rides trends only while the path is genuinely persistent and "
        "steps aside in whipsaw regimes where naive trend-following bleeds. Long/flat SPY, "
        "weekly rebalance + no-trade band -> low turnover; all parameters pre-registered."
    ),
    taxonomy=["path_geometry", "trend_following"],
    feature_families=["price"],
    universe="default",
    params={
        "asset": "SPY",
        "dfa_window": 120,
        "z_window": 252,
        "z_hi": 0.5,
        "z_lo": -0.5,
        "ma_fast": 50,
        "ma_slow": 200,
        "w_trend": 1.0,
        "w_neutral": 0.5,
        "w_choppy": 0.0,
        "rebalance": 5,
        "band": 0.1,
    },
    author="quant-researcher",
    references=[
        "Sims et al. (2012), Levy flight and Brownian search patterns, J. Animal Ecology",
        "Mantegna & Stanley, truncated Levy flight (arXiv cond-mat/9705087)",
        "Peng et al. (1994), Detrended Fluctuation Analysis, Phys. Rev. E 49:1685",
        "Hurst trend/mean-reversion in markets (Macrosynergy; arXiv 2205.11122)",
    ],
    gross_leverage=None,  # variable SPY<->cash exposure -- do NOT renormalize
)


def _dfa_hurst(x: np.ndarray, scales: tuple[int, ...]) -> float:
    """Detrended Fluctuation Analysis exponent of a 1-D series ``x``.

    ``x`` is a window of LOG RETURNS. We integrate to the cumulative profile, split it into
    non-overlapping boxes of each scale n, remove a local linear trend per box, take the RMS
    fluctuation F(n), and return the slope of log F(n) vs log n (= the DFA exponent ~ H).

    Causal/self-contained: depends only on the values passed in. NaNs -> NaN.
    """
    x = np.asarray(x, dtype=float)
    if not np.all(np.isfinite(x)):
        return np.nan
    N = x.size
    usable = [n for n in scales if n >= 4 and n <= N // 2]
    if len(usable) < 2:
        return np.nan

    profile = np.cumsum(x - x.mean())  # integrated, mean-removed
    log_n, log_F = [], []
    for n in usable:
        n_boxes = N // n
        if n_boxes < 1:
            continue
        # Detrend each non-overlapping box with a local linear fit; collect squared resids.
        idx = np.arange(n, dtype=float)
        # design matrix for a degree-1 polyfit (shared across boxes)
        A = np.vstack([idx, np.ones(n)]).T
        sq = np.empty(n_boxes)
        for b in range(n_boxes):
            seg = profile[b * n:(b + 1) * n]
            coef, _, _, _ = np.linalg.lstsq(A, seg, rcond=None)
            resid = seg - A @ coef
            sq[b] = np.mean(resid ** 2)
        F = np.sqrt(sq.mean())
        if F > 0 and np.isfinite(F):
            log_n.append(np.log(n))
            log_F.append(np.log(F))
    if len(log_n) < 2:
        return np.nan
    slope = np.polyfit(log_n, log_F, 1)[0]
    return float(slope)


def _rolling_dfa_hurst(log_ret: pd.Series, window: int, scales: tuple[int, ...]) -> pd.Series:
    """Trailing-window DFA Hurst series. Row t uses log returns in (t-window, t]."""
    vals = log_ret.to_numpy()
    out = np.full(vals.size, np.nan)
    for t in range(window, vals.size):
        out[t] = _dfa_hurst(vals[t - window + 1:t + 1], scales)
    return pd.Series(out, index=log_ret.index)


def generate_weights(
    prices: pd.DataFrame,
    asset: str = "SPY",
    dfa_window: int = 120,
    z_window: int = 252,
    z_hi: float = 0.5,
    z_lo: float = -0.5,
    ma_fast: int = 50,
    ma_slow: int = 200,
    w_trend: float = 1.0,
    w_neutral: float = 0.5,
    w_choppy: float = 0.0,
    rebalance: int = 5,
    band: float = 0.1,
    dfa_scales: tuple[int, ...] = (8, 16, 32, 64),
) -> pd.DataFrame:
    """Long/flat SPY weights gated by the trailing DFA diffusion regime.

    Only past data is used at each row; the engine adds the 1-day execution lag.
    """
    if asset not in prices.columns:
        raise ValueError(f"asset {asset!r} not in price universe")

    px = prices[asset].astype(float)
    log_ret = np.log(px / px.shift(1))

    # Trailing DFA Hurst, then a trailing z-score of the H history (both strictly causal).
    H = _rolling_dfa_hurst(log_ret, dfa_window, dfa_scales)
    H_mean = H.rolling(z_window, min_periods=max(60, z_window // 2)).mean()
    H_std = H.rolling(z_window, min_periods=max(60, z_window // 2)).std()
    H_z = (H - H_mean) / H_std.replace(0.0, np.nan)

    # Trend filter on past prices.
    ma_f = px.rolling(ma_fast, min_periods=ma_fast).mean()
    ma_s = px.rolling(ma_slow, min_periods=ma_slow).mean()
    trend_up = ma_f > ma_s

    # Regime -> target exposure mapping (per-row, all from past data).
    target = pd.Series(np.nan, index=prices.index)
    valid = H_z.notna() & ma_s.notna()
    # neutral by default where valid
    target[valid] = w_neutral
    # trending regime
    trend_mask = valid & (H_z > z_hi)
    target[trend_mask] = np.where(trend_up[trend_mask], w_trend, w_choppy)
    # choppy regime
    target[valid & (H_z < z_lo)] = w_choppy

    # Weekly rebalance with a no-trade band -> low turnover; ffill held weight; warmup -> cash.
    weights = pd.DataFrame(0.0, index=prices.index, columns=prices.columns)
    w_asset = pd.Series(index=prices.index, dtype=float)
    cur = np.nan
    for dt in prices.index[::rebalance]:
        t = target.loc[dt]
        if np.isfinite(t) and (np.isnan(cur) or abs(t - cur) >= band):
            cur = float(t)
        if np.isfinite(cur):
            w_asset.loc[dt] = cur

    weights[asset] = w_asset.ffill().fillna(0.0)
    return weights
