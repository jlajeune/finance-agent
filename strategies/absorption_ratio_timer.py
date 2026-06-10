"""Absorption Ratio (RMT/PCA systemic-coupling) fragility timer: long/flat SPY vs cash.

Lens: market_state_structural (+ volatility_timing). Convergent #1 pick of the
cross-domain ideation brief. This is a *rigorous, frozen-parameter, look-ahead-safe*
implementation of a well-specified published technique — not a new idea.

Economic / structural mechanism
-------------------------------
The Absorption Ratio (AR) of Kritzman, Li, Page & Rigobon (2011) measures how much of
the *cross-sectional* variance of asset returns is captured ("absorbed") by a small
number of principal components of the return correlation matrix. When markets are
fragile, capital and risk become tightly coupled: sectors that normally diversify each
other start moving together, so a handful of eigenvectors explain an unusually large
share of variance and AR *rises*. A high, recently-rising AR means the system is
compact and tightly wound — a small shock propagates everywhere with little to absorb
it. A low / falling AR means risk is spread across many independent dimensions and the
system is resilient. Critically, this is a property of the *coupling structure* of the
market (the correlation eigen-spectrum), which is conceptually orthogonal to the level
of trend (momentum), the level of volatility (vol-timing), or the variance-risk premium
(VRP). It is a leading indicator of fragility: tight coupling precedes drawdowns, it
does not merely coincide with realized volatility. We harvest this by de-risking SPY to
cash when fragility spikes and re-risking when the structure relaxes.

Signal construction (FROZEN from the paper — no fitting here)
-------------------------------------------------------------
* Signal universe: the 9 classic sector SPDRs that exist back to 1998 -- XLB, XLE, XLF,
  XLI, XLK, XLP, XLU, XLV, XLY. These are ETFs (no survivorship bias in the covariance
  structure). They are fetched INSIDE generate_weights and cached; only their *signal*
  is used -- the strategy trades SPY only.
* Daily LOG returns.
* Each day t (data <= t only): correlation matrix over a trailing 500-day window;
  eigendecompose with numpy.linalg.eigh; AR = sum(top-k eigenvalues)/sum(all
  eigenvalues), k = ceil(N/5) = 2 for N = 9.
* Standardized AR shift (already a z-score, so NO in-sample scaling is introduced):
      dAR = (mean(AR, last 15d) - mean(AR, last 252d)) / std(AR, last 252d).
* Exposure mapping (frozen, long/flat SPY vs cash):
      dAR > +1.0  -> 0.0  (fragile, tightly coupled -> de-risk to cash)
      dAR < -1.0  -> 1.0  (resilient, diffuse risk -> full SPY)
      otherwise   -> 0.5  (neutral).
  A small no-trade band on the *weight* suppresses micro-rebalances; dAR moves slowly so
  turnover stays low even though we recompute daily.

Look-ahead safeguards (red-team will probe these)
--------------------------------------------------
* The 500-day correlation window and the 15d / 252d AR-history windows all END at day t.
  No negative shifts, no centered windows, no full-sample eigendecomposition, no
  normalization that uses future AR values. The engine adds the 1-day execution lag.
* Sector prices are reindexed onto the strategy's own price index; returns are computed
  *within* the sector panel. Until there is enough clean history (500d window + 252d AR
  history ~= 750 trading days) AR/dAR are NaN and the weight stays in cash (0.0).
* If any sector is missing on day t (early history), that day's AR is NaN -> cash.

Falsification / failure conditions
----------------------------------
This strategy FAILS (adds nothing) unless, net of 5bps costs, it beats ALL of:
  (1) buy-and-hold SPY,
  (2) a VIX-LEVEL timer using the identical exposure mapping driven by a standardized
      VIX z-score (the key guard: dAR must add content BEYOND "VIX is high"), and
  (3) a static 60/40 SPY/TLT book,
on BOTH net Sharpe AND max drawdown -- and dAR must retain residual predictive content
for next-month SPY returns after controlling for VIX (low R^2 of dAR on VIX changes).
If dAR merely proxies the VIX level, the VIX timer matches or beats it and the idea is
redundant.

Data limitations
----------------
Cash leg modeled at 0% (no T-bill yield wired in) -- conservative for de-risked periods.
Sector SPDR adjusted closes via yfinance (cached). No fundamentals/alt-data needed.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from finance_agent.strategy import StrategySpec

# The 9 classic sector SPDRs with history back to 1998 (XLRE/XLC excluded on purpose:
# they were created later and would contaminate the covariance structure / start date).
SECTOR_ETFS = ["XLB", "XLE", "XLF", "XLI", "XLK", "XLP", "XLU", "XLV", "XLY"]

SPEC = StrategySpec(
    id="absorption_ratio_timer",
    thesis=(
        "Absorption Ratio fragility timer (Kritzman, Li, Page & Rigobon 2011): each day, "
        "PCA the trailing-500d correlation matrix of the 9 classic sector SPDRs and take "
        "AR = share of variance absorbed by the top 2 of 9 eigenvalues. A rising, "
        "extreme AR means sectors are tightly coupled -- a fragile, shock-amplifying "
        "regime that precedes drawdowns. Trade a standardized AR shift dAR = (15d mean - "
        "252d mean)/252d std: dAR>+1 -> cash, dAR<-1 -> full SPY, else half. This times "
        "SPY vs cash on cross-sectional COUPLING structure, which is orthogonal to trend, "
        "vol level, and VRP. Frozen params, ETF universe (no survivorship bias), "
        "look-ahead-safe trailing windows; must beat buy-and-hold, a VIX-level timer, and "
        "60/40 on net Sharpe AND drawdown to survive."
    ),
    taxonomy=["market_state_structural", "volatility_timing"],
    feature_families=["price"],
    universe="default",
    params={
        "asset": "SPY",
        "corr_window": 500,
        "k": 2,
        "short_window": 15,
        "long_window": 252,
        "hi_thresh": 1.0,
        "lo_thresh": 1.0,
        "band": 0.10,
    },
    author="quant-researcher",
    references=[
        "Kritzman, Li, Page & Rigobon (2011), Principal Components as a Measure of "
        "Systemic Risk, Journal of Portfolio Management; SSRN 1582687",
    ],
    gross_leverage=None,  # variable net exposure (cash <-> SPY) -- do NOT renormalize
)


def _absorption_ratio_series(
    sector_rets: pd.DataFrame, corr_window: int, k: int
) -> pd.Series:
    """Trailing Absorption Ratio per date, using only past returns at each row.

    AR[t] = sum(top-k eigenvalues) / sum(all eigenvalues) of the correlation matrix of
    sector returns over the window ENDING at t. NaN until a full clean window exists.
    """
    idx = sector_rets.index
    ar = pd.Series(np.nan, index=idx, dtype=float)
    vals = sector_rets.to_numpy()
    n = len(idx)
    for i in range(n):
        if i + 1 < corr_window:
            continue
        win = vals[i + 1 - corr_window : i + 1]  # rows [start, t], inclusive of t
        if not np.isfinite(win).all():
            continue  # any missing sector history on this window -> leave NaN (cash)
        # Correlation matrix; guard against a zero-variance column.
        sd = win.std(axis=0, ddof=1)
        if (sd <= 0).any() or not np.isfinite(sd).all():
            continue
        c = np.corrcoef(win, rowvar=False)
        if not np.isfinite(c).all():
            continue
        # eigh: ascending real eigenvalues of a symmetric matrix.
        eig = np.linalg.eigvalsh(c)
        eig = np.clip(eig, 0.0, None)  # numerical floor; correlation eigenvalues >= 0
        total = eig.sum()
        if total <= 0:
            continue
        ar.iloc[i] = float(eig[-k:].sum() / total)
    return ar


def _standardized_shift(
    ar: pd.Series, short_window: int, long_window: int
) -> pd.Series:
    """dAR = (mean(AR, last short) - mean(AR, last long)) / std(AR, last long).

    All windows END at t (trailing), so no future AR values enter. min_periods is set to
    the full window so dAR is NaN until enough AR history exists -> strategy stays in cash.
    """
    short_mean = ar.rolling(short_window, min_periods=short_window).mean()
    long_mean = ar.rolling(long_window, min_periods=long_window).mean()
    long_std = ar.rolling(long_window, min_periods=long_window).std(ddof=1)
    return (short_mean - long_mean) / long_std.replace(0.0, np.nan)


def _exposure_from_dar(
    dar: pd.Series, hi_thresh: float, lo_thresh: float
) -> pd.Series:
    """Map dAR -> SPY weight: >+hi -> 0.0 (cash), <-lo -> 1.0 (full), else 0.5."""
    w = pd.Series(np.nan, index=dar.index, dtype=float)
    valid = dar.notna()
    w[valid] = 0.5
    w[dar > hi_thresh] = 0.0
    w[dar < -lo_thresh] = 1.0
    return w


def generate_weights(
    prices: pd.DataFrame,
    asset: str = "SPY",
    corr_window: int = 500,
    k: int = 2,
    short_window: int = 15,
    long_window: int = 252,
    hi_thresh: float = 1.0,
    lo_thresh: float = 1.0,
    band: float = 0.10,
) -> pd.DataFrame:
    """Return weights (dates x tickers): a single varying long-or-flat SPY position.

    Sector SPDR prices are fetched internally for the signal; only ``asset`` is traded.
    Only past data is used at each row; the engine adds the 1-day execution lag.
    """
    if asset not in prices.columns:
        raise ValueError(f"asset {asset!r} not in price universe")

    weights = pd.DataFrame(0.0, index=prices.index, columns=prices.columns)

    # --- Fetch the sector signal universe (cached, look-ahead-safe by construction) ---
    from finance_agent.data import get_prices

    start = (prices.index.min() - pd.Timedelta(days=5)).strftime("%Y-%m-%d")
    end = (prices.index.max() + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
    try:
        sector_px = get_prices(SECTOR_ETFS, start=start, end=end)
    except Exception:
        return weights  # no signal data -> stay in cash everywhere (graceful degrade)

    # Reindex sectors onto the STRATEGY's price index; log returns within the panel.
    sector_px = sector_px.reindex(columns=SECTOR_ETFS)
    sector_px = sector_px.reindex(prices.index).ffill(limit=2)
    if sector_px.isna().all().any():
        return weights  # a sector entirely missing -> cannot form AR -> cash
    sector_rets = np.log(sector_px / sector_px.shift(1))

    ar = _absorption_ratio_series(sector_rets, corr_window=corr_window, k=k)
    dar = _standardized_shift(ar, short_window=short_window, long_window=long_window)
    target = _exposure_from_dar(dar, hi_thresh=hi_thresh, lo_thresh=lo_thresh)

    # No-trade band on the WEIGHT: only move when the target shifts by >= band; ffill
    # the held weight between moves. Pre-warmup (NaN dAR) -> 0 (cash).
    held = pd.Series(np.nan, index=prices.index, dtype=float)
    cur = np.nan
    for dt in prices.index:
        t = target.loc[dt]
        if np.isfinite(t) and (np.isnan(cur) or abs(t - cur) >= band):
            cur = float(t)
        if np.isfinite(cur):
            held.loc[dt] = cur

    weights[asset] = held.ffill().fillna(0.0)
    return weights
