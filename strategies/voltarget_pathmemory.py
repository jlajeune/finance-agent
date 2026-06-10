"""Path-memory-gated volatility-target overlay (DFA-Hurst regime tilt ON vol-target SPY).

Lens: volatility_timing x path_geometry. This is a deliberate *novel combination* of two
things that have each already cleared a bar in this project:

  (1) the validated incumbent ``voltarget_spy`` — inverse-realized-vol SPY sizing that
      targets a roughly constant ex-ante vol (our only PASS strategy); and
  (2) the validated orthogonal signal from ``diffusion_regime_timer`` — the DFA-Hurst
      path-memory z-score ``H_z`` (DFA window 120, z-window 252). Cycle 7 proved H_z
      predicts next-month SPY returns BEYOND VIX (non-overlap monthly t=2.90, Newey-West
      t=2.01, R^2-on-VIX only 0.10). The standalone H_z timer was rejected ONLY because it
      over-de-risked (binary 0%-equity in choppy regimes), not because the signal is bad.

Economic mechanism
------------------
Vol-targeting exploits volatility *persistence* + the leverage effect: it scales exposure
inversely to recent realized vol, cutting risk into vol spikes before the worst of a
drawdown. But realized vol is an *amplitude* measure — it cannot tell a low-vol grind
higher (persistent / trending) from a low-vol whipsaw (choppy / mean-reverting). The
DFA-Hurst exponent measures *path memory* (MSD(tau) ~ tau^(2H)): H>0.5 persistent, H<0.5
anti-persistent. Choppy / sub-diffusive regimes are exactly where the equity risk premium
and trend capture are weakest and where tail-clustering is worst — yet vol-targeting alone,
seeing only amplitude, may keep full exposure through a low-vol whipsaw. So we keep the
incumbent's vol-target weight as the BASE and apply a GENTLE, bounded, multiplicative tilt
from H_z: persistent regime -> allow full (slightly higher) exposure; choppy regime ->
modestly trim (never to zero, so we keep harvesting the premium the rest of the time). The
binary cash-switch of the standalone timer was its fatal flaw; a smooth tilt is not.

Why a tilt, not a switch (the lesson from B1's rejection)
---------------------------------------------------------
The standalone diffusion timer cut to 0% equity in choppy regimes, throwing away the equity
premium for long stretches and over-fitting the regime boundary. Here ``g(H_z)`` is a
smooth, monotone, BOUNDED function ``g = clip(1 + k*tanh(H_z), g_min, g_max)`` with
``g_min ~ 0.6`` and ``g_max ~ 1.1`` and a small ``k`` — so the worst it ever does is trim
the vol-target weight by ~40%, and the best is a ~10% lean-in. The base mechanism (vol
targeting) always dominates; H_z only nudges it.

Frozen, pre-registered parameters (NOT fit)
-------------------------------------------
Base (reused verbatim from voltarget_spy):
  * vol_window=60, target_vol=0.11, max_leverage=1.0, rebalance=5 (weekly), band=0.05
Path-memory gate (reused from diffusion_regime_timer):
  * dfa_window=120, dfa_scales={8,16,32,64}, z_window=252
Tilt (new, small, frozen):
  * k=0.3, g_min=0.6, g_max=1.1   (g = clip(1 + k*tanh(H_z), g_min, g_max))

Look-ahead safety
-----------------
Both inputs at date t use only trailing data ending at t: realized vol from returns <= t;
DFA-Hurst from the trailing 120 log returns ending at t; H_z from the trailing H-history.
No negative shifts, no centered windows, no full-sample normalization. The engine adds the
1-day execution lag. During warmup (before H_z exists) the gate defaults to g=1 so the
overlay degrades gracefully to the plain incumbent rather than to cash. The final weight is
re-passed through the no-trade band so the tilt does not inflate turnover.

Falsification / failure conditions
----------------------------------
* If net-of-cost Sharpe does NOT beat the incumbent voltarget_spy, the H_z tilt adds nothing
  in practice -> reject (a clean negative; voltarget_spy is hard to beat).
* If max drawdown is WORSE than voltarget_spy, the tilt is mis-signed / counterproductive.
* If the improvement lives on a lone (k, g_min) spike rather than a smooth plateau across
  the small grid, it is fit, not real.
* If it dies in the post-2010 OOS subsample, it is regime-lucky.

Data limitations
----------------
SPY adjusted closes only (price family). Cash leg modeled at 0% (conservative for de-levered
periods). gross_leverage=None so the engine does NOT renormalize the variable SPY/cash book.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from finance_agent.strategy import StrategySpec

SPEC = StrategySpec(
    id="voltarget_pathmemory",
    thesis=(
        "Path-memory-gated vol-target overlay on SPY. BASE weight = the validated "
        "voltarget_spy sizing (inverse trailing-60d realized vol, ~11% target, capped 1x, "
        "weekly rebalance, no-trade band). OVERLAY = a gentle, bounded, monotone "
        "multiplicative tilt g(H_z) = clip(1 + k*tanh(H_z), g_min, g_max) driven by the "
        "DFA-Hurst path-memory z-score H_z (DFA window 120, z-window 252) -- the cycle-7 "
        "signal shown to predict next-month returns BEYOND VIX. Persistent/trending regime "
        "(H_z high) allows full-to-slightly-higher exposure; choppy/mean-reverting regime "
        "(H_z low) trims exposure modestly (never to zero, unlike the rejected binary "
        "timer), because that is where the equity premium is weakest and tail-clustering "
        "worst. Vol amplitude (the base) and path memory (the tilt) are orthogonal axes. "
        "Long/flat SPY, frozen params, look-ahead-safe."
    ),
    taxonomy=["volatility_timing", "path_geometry"],
    feature_families=["price"],
    universe="default",
    params={
        "asset": "SPY",
        # base vol-target (from voltarget_spy)
        "vol_window": 60,
        "target_vol": 0.11,
        "max_leverage": 1.0,
        "rebalance": 5,
        "band": 0.05,
        # path-memory gate (from diffusion_regime_timer)
        "dfa_window": 120,
        "z_window": 252,
        # tilt (new, small, frozen)
        "k": 0.3,
        "g_min": 0.6,
        "g_max": 1.1,
    },
    author="quant-researcher",
    references=[
        "Man Group, The Impact of Volatility Targeting",
        "Research Affiliates, Harnessing Volatility Targeting in Multi-Asset Portfolios",
        "Xu (2024), Improving Volatility-Managed Portfolios in Real Time, SSRN 4778937",
        "Peng et al. (1994), Detrended Fluctuation Analysis, Phys. Rev. E 49:1685",
        "Sims et al. (2012), Levy flight and Brownian search patterns, J. Animal Ecology",
        "Hurst trend/mean-reversion in markets (Macrosynergy; arXiv 2205.11122)",
    ],
    prior_art="extends: voltarget_spy + diffusion H_z signal",
    novel_combination="DFA-Hurst path-memory regime tilt ON vol-target sizing",
    gross_leverage=None,  # variable SPY<->cash exposure -- do NOT renormalize
)


# --- Path-memory estimator (copied verbatim from diffusion_regime_timer for self-containment) ---

def _dfa_hurst(x: np.ndarray, scales: tuple[int, ...]) -> float:
    """Detrended Fluctuation Analysis exponent of a 1-D window of LOG RETURNS.

    Integrate to the cumulative profile, split into non-overlapping boxes of each scale n,
    remove a local linear trend per box, take RMS fluctuation F(n), return slope of
    log F(n) vs log n (= DFA exponent ~ H). Causal / self-contained. NaNs -> NaN.
    """
    x = np.asarray(x, dtype=float)
    if not np.all(np.isfinite(x)):
        return np.nan
    N = x.size
    usable = [n for n in scales if n >= 4 and n <= N // 2]
    if len(usable) < 2:
        return np.nan

    profile = np.cumsum(x - x.mean())
    log_n, log_F = [], []
    for n in usable:
        n_boxes = N // n
        if n_boxes < 1:
            continue
        idx = np.arange(n, dtype=float)
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
    # base vol-target
    vol_window: int = 60,
    target_vol: float = 0.11,
    max_leverage: float = 1.0,
    rebalance: int = 5,
    band: float = 0.05,
    # path-memory gate
    dfa_window: int = 120,
    z_window: int = 252,
    # tilt
    k: float = 0.3,
    g_min: float = 0.6,
    g_max: float = 1.1,
    dfa_scales: tuple[int, ...] = (8, 16, 32, 64),
) -> pd.DataFrame:
    """Vol-target SPY weight tilted by a bounded DFA-Hurst path-memory multiplier.

    Only past data is used at each row; the engine adds the 1-day execution lag.
    """
    if asset not in prices.columns:
        raise ValueError(f"asset {asset!r} not in price universe")

    px = prices[asset].astype(float)
    daily = px.pct_change()
    log_ret = np.log(px / px.shift(1))

    # --- BASE: inverse-vol target exposure, capped (identical to voltarget_spy). ---
    realized = daily.rolling(vol_window, min_periods=max(20, vol_window // 2)).std() * np.sqrt(252)
    w0 = (target_vol / realized.replace(0.0, np.nan)).clip(upper=max_leverage)

    # --- GATE: trailing DFA-Hurst, then a trailing z-score of its own history. ---
    H = _rolling_dfa_hurst(log_ret, dfa_window, dfa_scales)
    H_mean = H.rolling(z_window, min_periods=max(60, z_window // 2)).mean()
    H_std = H.rolling(z_window, min_periods=max(60, z_window // 2)).std()
    H_z = (H - H_mean) / H_std.replace(0.0, np.nan)

    # --- TILT: smooth, monotone, bounded multiplier. Warmup (H_z NaN) -> g=1 (graceful
    #     degradation to the plain incumbent, NOT to cash). ---
    g = (1.0 + k * np.tanh(H_z)).clip(lower=g_min, upper=g_max)
    g = g.where(H_z.notna(), 1.0)

    # Final target = base * tilt, still capped at max_leverage (g_max can push w0 up).
    target = (w0 * g).clip(upper=max_leverage)

    # Weekly rebalance with a no-trade band on the FINAL weight -> low, controlled turnover.
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
