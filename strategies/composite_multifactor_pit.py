"""Composite MULTI-FACTOR equity sleeve on a POINT-IN-TIME S&P 500 universe.

Lens: quality + value (multifactor composite). This is the cycle-12 follow-up to the
cycle-11 insight (research/process_retro.md): individually-weak-but-real factors keep
failing the significance bar ALONE. Earnings-yield VALUE (cycle 11) passed the placebo
(signal-specific, p=0.0) yet was sub-threshold (long-only-minus-EW monthly t=1.45). Gross
profitability (cycle 10) was outright DEAD on the honest PIT set. The thesis now: do NOT
keep testing single weak factors -- COMBINE several signal-specific, plausibly-orthogonal
factors into a composite. Diversifying weak orthogonal signals is where accessible-data
alpha most plausibly lives: each factor's idiosyncratic noise partially cancels, so the
composite's information ratio can exceed any single factor's even when no single factor
clears the bar.

THE FOUR FACTORS (each computed point-in-time, cross-sectionally z-scored each monthly
rebalance over the PIT-tradable cross-section; higher z = more attractive = long):
  1. VALUE -- earnings yield = TTM NetIncomeLoss (filed<=t, reconstructed from the
     YTD-cumulative XBRL income statement into four discrete quarters) / market cap
     (price_t * PIT shares outstanding). Higher = cheaper = better. (Reuses the validated
     cycle-11 machinery in value_earnings_yield_pit.)
  2. QUALITY -- return on equity = TTM NetIncomeLoss (filed<=t) / StockholdersEquity
     (PIT, filed<=t). Higher = more profitable = better.
  3. LOW VOLATILITY -- NEGATIVE trailing 126-day realized vol of daily returns (price-only,
     trailing window up to t-1). Lower vol -> higher score (the low-vol anomaly: low-risk
     stocks earn higher risk-adjusted returns than CAPM predicts).
  4. MOMENTUM -- 12-1 price momentum: trailing 252d return skipping the most recent 21d
     (price-only). Higher = stronger trend = better.

COMPOSITE SCORE = equal-weight mean of the AVAILABLE per-name z-scores. Missing factors are
simply averaged over the present ones; a name needs >=2 factors present to be scored. This
degrades gracefully (a name missing fundamentals still gets a price-only composite of
low-vol + momentum). Rank the composite -> tercile dollar-neutral L/S (long top, short
bottom), equal-weight legs, monthly rebalance, gross_leverage=1.0.

WHY z-SCORE NOT RANK
--------------------
z-scoring puts the four heterogeneous factors on a comparable scale before averaging, so the
composite is a true equal-risk blend rather than dominated by whichever factor has the widest
raw dispersion. z is computed per-rebalance over the cross-section present that day (no
full-sample stats -> no look-ahead). Outliers winsorized at +/-3 sd before averaging so a
single blown-up fundamental cannot hijack the composite.

PRIOR ART / NOVELTY
-------------------
Multi-factor compositing is textbook (Fama-French multifactor; Asness/AQR "style premia";
MSCI/Barra composites). ``prior_art = "reimplements: standard multi-factor compositing"``.
The only thing not-previously-tried HERE is the exact combination under our discipline:
value+quality+low-vol+momentum equal-z composite on a FREE point-in-time S&P 500 universe,
vetted with a per-rebalance shuffle placebo and honest non-overlapping monthly SEs, and the
decisive *diversification* test (does the composite beat its best single part?).

ECONOMIC MECHANISM
------------------
Each leg has its own documented premium and, crucially, LOW mutual correlation: value and
momentum are famously negatively correlated (the classic value/momentum diversification of
Asness-Moskowitz-Pedersen 2013); quality (profitability) is near-orthogonal to value
(Novy-Marx 2013, "the other side of value"); low-vol captures the leverage-constrained /
lottery-preference anomaly (Frazzini-Pedersen BAB, Baker-Bradley-Wurgler). Blending premia
whose timing differs raises the ensemble Sharpe even if each component Sharpe is modest --
the core argument for multifactor sleeves. Falsifiable claim: the composite's L/S monthly t
and Sharpe should EXCEED the best single factor's on the SAME PIT universe. If not, there is
no diversification benefit and combining weak factors is not the answer.

UNIVERSE
--------
``SPEC.universe = "sp500_pit_union"`` so the standardized harness fetches the WIDE
historical-constituent price panel and runs this through the STANDARD ``evaluate`` battery.
At each monthly rebalance ``t`` the tradable set is point_in_time_universe(t) [membership
effective <= t, look-ahead-safe] INTERSECT {priced at t} INTERSECT {>=2 factors present}.

LOOK-AHEAD SAFETY
-----------------
1. Membership: ``point_in_time_universe(t)`` applies only changes effective <= t.
2. Fundamentals (earnings, shares, equity): ``point_in_time_asof`` / TTM reconstruction use
   ONLY facts with SEC ``filed`` <= t.
3. Price factors (low-vol, momentum) use trailing windows ending at t (the engine adds the
   1-day execution lag). z-scores use only the cross-section present at t. No ``.shift(-k)``,
   no centered windows, no full-sample normalization.

FALSIFICATION / FAILURE CONDITIONS
----------------------------------
* If the composite L/S Sharpe and monthly t do NOT exceed the BEST single factor's on the
  same PIT universe, there is no diversification benefit -> combining weak factors is not the
  answer (the central thesis is rejected).
* If composite long-only does not beat equal-weight of the same PIT-tradable set, the
  long leg carries no edge over the universe.
* Per-rebalance shuffle placebo: if shuffling the composite score across names (turnover
  fixed) does about as well, the signal is churn, not information.

DATA LIMITATIONS (stated honestly)
----------------------------------
* RESIDUAL price-survivorship: membership is PIT, but yfinance lacks many delisted names; the
  eval logs avg names dropped/period as a bound. Full fix = CRSP/Sharadar.
* XBRL starts ~2009 -> sample begins ~2010; only ~711/1201 historical constituents have a CIK.
  Names lacking fundamentals still receive a price-only composite (low-vol + momentum), so the
  cross-section is not silently restricted to fundamentals-covered names.
* Income statement is YTD-cumulative -> reconstructed into discrete quarters; filers with
  irregular calendars degrade to fewer usable quarters. StockholdersEquity tag has a fallback.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from finance_agent.strategy import StrategySpec

# Reuse the validated cycle-11 PIT machinery (TTM net income, shares, membership mask).
# Load the sibling strategy by file path so this works regardless of whether ``strategies``
# is importable as a package (the standard runner loads strategy files by path, not import).
def _load_value_module():
    import importlib.util
    from pathlib import Path

    sib = Path(__file__).resolve().parent / "value_earnings_yield_pit.py"
    spec = importlib.util.spec_from_file_location("value_earnings_yield_pit_sib", sib)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


_value_mod = _load_value_module()
ttm_net_income_asof = _value_mod.ttm_net_income_asof
shares_asof = _value_mod.shares_asof
pit_membership_mask = _value_mod.pit_membership_mask

SPEC = StrategySpec(
    id="composite_multifactor_pit",
    thesis=(
        "Composite multi-factor equity sleeve on a point-in-time S&P 500 universe. The "
        "cycle-12 follow-up to the cycle-11 finding that individually-weak-but-real factors "
        "(e.g. earnings-yield value: placebo-clean but sub-threshold) keep failing the "
        "significance bar ALONE. Instead of testing one weak factor, blend four signal-specific, "
        "plausibly-orthogonal factors -- VALUE (earnings yield = TTM NetIncomeLoss / market cap), "
        "QUALITY (ROE = TTM NetIncomeLoss / StockholdersEquity), LOW VOL (negative trailing 126d "
        "realized vol), MOMENTUM (12-1 price momentum) -- each computed point-in-time and "
        "cross-sectionally z-scored per monthly rebalance over the PIT-tradable set. Composite = "
        "equal-weight mean of the AVAILABLE z-scores (>=2 required; price-only composite when "
        "fundamentals missing). Rank -> tercile dollar-neutral L/S (long top, short bottom), "
        "equal-weight legs, monthly rebalance, gross_leverage=1.0. Universe at each t = "
        "point_in_time_universe(t) (look-ahead-safe) INTERSECT priced INTERSECT >=2-factor names. "
        "Decisive test: does the composite L/S beat its BEST single factor (diversification "
        "benefit), clearing the bar where singles did not? Value/momentum are negatively "
        "correlated and quality is near-orthogonal to value, so the blend's Sharpe can exceed "
        "any one component's even when each is individually modest."
    ),
    taxonomy=["quality", "value"],
    feature_families=["price", "fundamentals"],
    universe="sp500_pit_union",
    params={
        "quantile": 0.33,
        "rebalance": 21,
        "filed_lag_days": 0,
        "min_names": 12,
        "min_quarters": 4,
        "vol_lookback": 126,
        "mom_lookback": 252,
        "mom_skip": 21,
        "min_factors": 2,
        "winsor": 3.0,
    },
    author="quant-researcher",
    references=[
        "Asness, Moskowitz & Pedersen (2013), Value and Momentum Everywhere, JF",
        "Novy-Marx (2013), The Other Side of Value: The Gross Profitability Premium, JFE",
        "Frazzini & Pedersen (2014), Betting Against Beta, JFE (low-vol/BAB)",
        "Fama & French (1992/2015), multifactor models",
        "fja05680/sp500 -- S&P 500 Historical Components & Changes (free PIT membership)",
    ],
    prior_art="reimplements: standard multi-factor compositing",
    novel_combination=(
        "value+quality+low-vol+momentum equal-z composite on a point-in-time S&P500 universe "
        "under placebo / honest-SE discipline (decisive diversification-vs-parts test)"
    ),
    gross_leverage=1.0,
)


# --------------------------------------------------------------------------- #
# Point-in-time StockholdersEquity panel (for ROE quality factor)
# --------------------------------------------------------------------------- #
def equity_asof(
    tickers: list[str],
    dates: pd.DatetimeIndex,
    filed_lag_days: int = 0,
    panel: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Point-in-time StockholdersEquity, (dates x tickers), using ONLY filed<=date data.

    Uses the EDGAR connector's StockholdersEquity tag (with the connector's built-in
    fallback to the including-noncontrolling-interest variant). A pre-built ``panel`` (long
    EDGAR frame) may be injected (eval/placebo); otherwise fetched. Look-ahead safety lives
    entirely in ``point_in_time_asof``.
    """
    from finance_agent.edgar import get_edgar_fundamentals, point_in_time_asof

    if panel is None:
        panel = get_edgar_fundamentals(tickers, ["StockholdersEquity"])
    if panel is None or panel.empty:
        return pd.DataFrame(index=dates, columns=tickers, dtype=float)

    panel = panel.copy()
    if filed_lag_days:
        panel["filed"] = pd.to_datetime(panel["filed"]) + pd.Timedelta(days=filed_lag_days)

    wide = point_in_time_asof(panel, dates)
    if wide.empty:
        return pd.DataFrame(index=dates, columns=tickers, dtype=float)

    out = pd.DataFrame(index=dates, columns=tickers, dtype=float)
    for tk in tickers:
        try:
            eq = wide[(tk, "StockholdersEquity")]
        except KeyError:
            continue
        out[tk] = eq.where(eq > 0)
    return out


# --------------------------------------------------------------------------- #
# Factor panels (dates x tickers), all look-ahead-safe
# --------------------------------------------------------------------------- #
def value_panel(
    tickers: list[str],
    prices: pd.DataFrame,
    filed_lag_days: int = 0,
    min_quarters: int = 4,
    ttm_ni: pd.DataFrame | None = None,
    shares: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Earnings yield = TTM NetIncomeLoss / (price * PIT shares). Higher = cheaper = better."""
    dates = prices.index
    if ttm_ni is None:
        ttm_ni = ttm_net_income_asof(tickers, dates, filed_lag_days=filed_lag_days,
                                     min_quarters=min_quarters)
    if shares is None:
        shares = shares_asof(tickers, dates, filed_lag_days=filed_lag_days)
    ttm_ni = ttm_ni.reindex(index=dates, columns=tickers)
    shares = shares.reindex(index=dates, columns=tickers)
    px = prices.reindex(columns=tickers)
    with np.errstate(divide="ignore", invalid="ignore"):
        mktcap = px * shares
        ey = ttm_ni / mktcap
    return ey.where(mktcap > 0)


def quality_panel(
    tickers: list[str],
    dates: pd.DatetimeIndex,
    filed_lag_days: int = 0,
    min_quarters: int = 4,
    ttm_ni: pd.DataFrame | None = None,
    equity: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """ROE = TTM NetIncomeLoss / StockholdersEquity (PIT). Higher = more profitable = better."""
    if ttm_ni is None:
        ttm_ni = ttm_net_income_asof(tickers, dates, filed_lag_days=filed_lag_days,
                                     min_quarters=min_quarters)
    if equity is None:
        equity = equity_asof(tickers, dates, filed_lag_days=filed_lag_days)
    ttm_ni = ttm_ni.reindex(index=dates, columns=tickers)
    equity = equity.reindex(index=dates, columns=tickers)
    with np.errstate(divide="ignore", invalid="ignore"):
        roe = ttm_ni / equity
    return roe.where(equity > 0)


def lowvol_panel(prices: pd.DataFrame, vol_lookback: int = 126) -> pd.DataFrame:
    """NEGATIVE trailing realized vol of daily returns. Lower vol -> higher (better) score.

    Trailing window ends at t (returns through t); the engine adds the 1-day execution lag.
    """
    rets = prices.pct_change()
    vol = rets.rolling(vol_lookback, min_periods=max(20, vol_lookback // 2)).std()
    return -vol  # lower vol = higher score


def momentum_panel(prices: pd.DataFrame, mom_lookback: int = 252, mom_skip: int = 21) -> pd.DataFrame:
    """12-1 momentum: trailing return from t-lookback to t-skip. Higher = better."""
    past = prices.shift(mom_skip)
    return past / past.shift(mom_lookback - mom_skip) - 1.0


# --------------------------------------------------------------------------- #
# Cross-sectional z-score (per-date, over present names only -> no look-ahead)
# --------------------------------------------------------------------------- #
def _zscore_row(row: pd.Series, winsor: float) -> pd.Series:
    """z-score a cross-section (one rebalance), winsorized at +/-``winsor`` sd. Robust to
    constant/degenerate rows (returns 0s if std is 0)."""
    r = row.dropna()
    if len(r) < 3:
        return pd.Series(dtype=float)
    mu = r.mean()
    sd = r.std(ddof=0)
    if not np.isfinite(sd) or sd == 0:
        return pd.Series(0.0, index=r.index)
    z = (r - mu) / sd
    return z.clip(-winsor, winsor)


def composite_score_at(
    dt: pd.Timestamp,
    names: pd.Index,
    factor_panels: dict[str, pd.DataFrame],
    winsor: float,
    min_factors: int,
) -> pd.Series:
    """Equal-weight mean of available per-name z-scores at rebalance ``dt``.

    For each factor, z-score its cross-section over ``names`` present at ``dt``, then average
    each name's available z-scores. Names with < ``min_factors`` present are dropped.
    """
    zmat = {}
    for fname, panel in factor_panels.items():
        if dt not in panel.index:
            continue
        z = _zscore_row(panel.loc[dt, names], winsor)
        if len(z):
            zmat[fname] = z
    if not zmat:
        return pd.Series(dtype=float)
    zdf = pd.DataFrame(zmat)  # (names x factors), NaN where factor missing for that name
    n_present = zdf.notna().sum(axis=1)
    composite = zdf.mean(axis=1, skipna=True)  # average over present factors
    composite = composite[n_present >= min_factors]
    return composite.dropna()


# --------------------------------------------------------------------------- #
# Weights from a per-rebalance composite-score function
# --------------------------------------------------------------------------- #
def weights_from_composite(
    factor_panels: dict[str, pd.DataFrame],
    membership: pd.DataFrame,
    index: pd.DatetimeIndex,
    columns: pd.Index,
    quantile: float,
    rebalance: int,
    min_names: int,
    winsor: float,
    min_factors: int,
    drop_log: list | None = None,
) -> pd.DataFrame:
    """Tercile dollar-neutral L/S weights from the composite score, gated by PIT membership."""
    weights = pd.DataFrame(index=index, columns=columns, dtype=float)
    rebal_dates = index[::rebalance]
    for dt in rebal_dates:
        if dt not in membership.index:
            continue
        members = membership.loc[dt]
        member_names = members[members].index
        if len(member_names) == 0:
            continue
        score = composite_score_at(dt, member_names, factor_panels, winsor, min_factors)
        n_members = len(member_names)
        n_usable = len(score)
        if drop_log is not None:
            drop_log.append(
                {"date": dt, "n_members": int(n_members), "n_usable": int(n_usable),
                 "n_dropped": int(n_members - n_usable)}
            )
        if n_usable < min_names:
            continue
        hi = score.quantile(1 - quantile)
        lo = score.quantile(quantile)
        longs = score[score >= hi].index
        shorts = score[score <= lo].index
        if len(longs) == 0 or len(shorts) == 0:
            continue
        w = pd.Series(0.0, index=columns)
        w[longs] = 0.5 / len(longs)
        w[shorts] = -0.5 / len(shorts)
        weights.loc[dt] = w.values
    return weights.ffill().fillna(0.0)


def build_factor_panels(
    names: list[str],
    prices: pd.DataFrame,
    filed_lag_days: int = 0,
    min_quarters: int = 4,
    vol_lookback: int = 126,
    mom_lookback: int = 252,
    mom_skip: int = 21,
    ttm_ni: pd.DataFrame | None = None,
    shares: pd.DataFrame | None = None,
    equity: pd.DataFrame | None = None,
) -> dict[str, pd.DataFrame]:
    """Build the four factor panels (dates x names). Fundamental panels may be injected
    (eval reuses fetched EDGAR data to avoid re-downloading)."""
    if ttm_ni is None:
        ttm_ni = ttm_net_income_asof(names, prices.index, filed_lag_days=filed_lag_days,
                                     min_quarters=min_quarters)
    if shares is None:
        shares = shares_asof(names, prices.index, filed_lag_days=filed_lag_days)
    if equity is None:
        equity = equity_asof(names, prices.index, filed_lag_days=filed_lag_days)
    return {
        "value": value_panel(names, prices[names], filed_lag_days=filed_lag_days,
                             min_quarters=min_quarters, ttm_ni=ttm_ni, shares=shares),
        "quality": quality_panel(names, prices.index, filed_lag_days=filed_lag_days,
                                 min_quarters=min_quarters, ttm_ni=ttm_ni, equity=equity),
        "lowvol": lowvol_panel(prices[names], vol_lookback=vol_lookback),
        "momentum": momentum_panel(prices[names], mom_lookback=mom_lookback, mom_skip=mom_skip),
    }


def generate_weights(
    prices: pd.DataFrame,
    quantile: float = 0.33,
    rebalance: int = 21,
    filed_lag_days: int = 0,
    min_names: int = 12,
    min_quarters: int = 4,
    vol_lookback: int = 126,
    mom_lookback: int = 252,
    mom_skip: int = 21,
    min_factors: int = 2,
    winsor: float = 3.0,
    drop_log: list | None = None,
) -> pd.DataFrame:
    """Dollar-neutral composite multi-factor L/S weights (dates x tickers) on a PIT universe.

    Cross-section at each rebalance = point_in_time_universe(t) INTERSECT {priced columns}
    INTERSECT {names with >= min_factors of (value, quality, low-vol, momentum) present}.
    Only past data per row; the engine adds the 1-day lag. ``prices`` should be the WIDE
    historical-constituent panel (SPEC.universe="sp500_pit_union").
    """
    names = [t for t in prices.columns if not prices[t].dropna().empty]
    panels = build_factor_panels(
        names, prices, filed_lag_days=filed_lag_days, min_quarters=min_quarters,
        vol_lookback=vol_lookback, mom_lookback=mom_lookback, mom_skip=mom_skip,
    )
    rebal_dates = prices.index[::rebalance]
    membership = pit_membership_mask(prices.index, pd.Index(names), rebal_dates)
    priced = prices[names].notna()
    membership = membership & priced.reindex(columns=names).fillna(False)

    panels = {k: v.reindex(columns=names) for k, v in panels.items()}
    weights = weights_from_composite(
        panels, membership.reindex(columns=names), prices.index, pd.Index(names),
        quantile, rebalance, min_names, winsor, min_factors, drop_log=drop_log,
    )
    out = pd.DataFrame(0.0, index=prices.index, columns=prices.columns)
    out[names] = weights[names]
    return out
