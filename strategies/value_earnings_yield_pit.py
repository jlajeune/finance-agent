"""Earnings-yield VALUE long/short on a POINT-IN-TIME S&P 500 universe (survivorship-controlled).

Lens: value. This is the cycle-11 follow-up to cycle 10. Cycle 10 showed gross
profitability was DEAD on the honest point-in-time (PIT) universe: long-only top tercile
Sharpe 0.85 == equal-weight-PIT 0.838 == SPY 0.856, and the L/S spread was flat (~0.01).
The decisive open question: does classic VALUE survive on the same honest PIT universe
where quality did not? This strategy tests the oldest value signal -- the **earnings
yield** (trailing-twelve-month net income / market cap) -- with every input pulled
point-in-time via the EDGAR ``point_in_time_asof`` guard, on the point-in-time S&P 500
membership at each rebalance (losers/delistings back in the sample).

SIGNAL
------
earnings_yield = TTM_NetIncomeLoss(filed <= t) / market_cap_t
  - TTM_NetIncomeLoss: sum of the trailing four DISCRETE fiscal quarters of NetIncomeLoss,
    reconstructed point-in-time. XBRL income-statement flows are reported YTD-CUMULATIVE
    within a fiscal year (Q1=3mo, Q2=6mo YTD, Q3=9mo YTD, FY=12mo), then reset. Naively
    summing the last 4 reported values is WRONG. We reconstruct discrete quarters by
    differencing consecutive cumulative figures within each fiscal year (using the reported
    period start/end to detect length), then sum the most recent four discrete quarters
    available as-of t. Every input obeys filed <= t.
  - market_cap_t = price_t * shares_outstanding_asof(t). Shares come from the EDGAR
    share-count tag, point-in-time (filed <= t): we try dei:EntityCommonStockSharesOutstanding,
    then us-gaap:CommonStockSharesOutstanding, then us-gaap:WeightedAverageNumberOfSharesOutstandingBasic.
  Higher earnings yield = cheaper = LONG.

PRIOR ART / NOVELTY
-------------------
This is explicitly a **re-implementation** of a decades-old factor (earnings yield / E/P,
Basu 1977; the value premium, Fama-French 1992), run as a survivorship-control experiment
on a free PIT universe -- NOT a novelty claim. ``prior_art = "reimplements: earnings-yield
value on PIT universe"``. The only new thing vs the textbook factor is the universe
construction (``novel_combination``: earnings-yield value on a point-in-time S&P 500 universe).

ECONOMIC MECHANISM (the value premium)
--------------------------------------
Cheap stocks (high E/P) earn a premium over expensive ones. Rationalized either as
compensation for distress/risk (Fama-French) or as a behavioral correction of
over-extrapolation: the market over-pays for glamour growth and under-pays for unloved
value, and the gap mean-reverts. Earnings yield is the income-statement analogue of
book-to-market and avoids book-value distortions (buybacks, intangibles) that have
plagued B/M post-2010. The falsifiable question here is narrow: does the premium appear
in the FREE PIT large-cap (S&P 500, XBRL-era) cross-section, or has large-cap value
decayed post-2010 the way quality did in cycle 10?

UNIVERSE
--------
``SPEC.universe = "sp500_pit_union"`` so the standardized harness fetches the WIDE
historical-constituent price panel and runs this through the STANDARD ``evaluate`` battery.
At each monthly rebalance ``t`` the tradable set is:
  point_in_time_universe(t)  [membership effective <= t, look-ahead-safe]
    INTERSECT {names with a price at t}
    INTERSECT {names with PIT TTM earnings filed <= t}
    INTERSECT {names with PIT shares filed <= t}.
Tercile dollar-neutral L/S (long top earnings-yield, short bottom), equal-weight legs,
monthly rebalance, ``gross_leverage = 1.0``.

LOOK-AHEAD SAFETY
-----------------
1. Membership: ``point_in_time_universe(t)`` applies only changes effective <= t.
2. Fundamentals (earnings, shares): ``point_in_time_asof`` returns the latest value with
   SEC ``filed`` <= t; TTM quarters reconstructed only from filed-<=-t observations.
3. Prices supply the date grid / return panel; the engine adds the 1-day execution lag.
No ``.shift(-k)``, no centered windows, no full-sample normalization.

FALSIFICATION / FAILURE CONDITIONS
----------------------------------
* If the long-only top earnings-yield tercile does NOT beat equal-weight of the same
  PIT-tradable set (as GP failed to in cycle 10), large-cap value is weak/decayed post-2010.
* If the L/S spread is flat-to-negative and insignificant (monthly |t| < 2), no value premium
  in this free PIT cross-section.
* Filing-shuffle placebo: if shuffling earnings yield across names (holding turnover fixed)
  does about as well, the factor carries no information beyond churn.

DATA LIMITATIONS (stated honestly)
----------------------------------
* RESIDUAL price-survivorship: membership is PIT, but yfinance lacks many delisted names
  (~53% of exited names priced). Unpriced removed names are dropped; the eval logs avg #
  names dropped/period as a bound. Full fix = CRSP/Sharadar delisting-complete prices.
* XBRL starts ~2009 -> sample begins ~2010; only ~711/1201 historical constituents have a CIK.
* Income-statement YTD-cumulative reporting handled by quarter reconstruction; filers with
  irregular fiscal calendars or missing interim filings degrade to fewer usable quarters
  (a name needs >=4 reconstructable trailing quarters; otherwise it is dropped that period).
* Shares tag varies; we fall back across three tags. US filers only.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from finance_agent.strategy import StrategySpec

SPEC = StrategySpec(
    id="value_earnings_yield_pit",
    thesis=(
        "Point-in-time earnings-yield VALUE (E/P, Basu 1977 / Fama-French value premium): "
        "trailing-twelve-month NetIncomeLoss (filed<=t, reconstructed from the YTD-cumulative "
        "XBRL income statement into four discrete quarters) divided by market cap (price_t x "
        "point-in-time shares outstanding). Higher = cheaper = long. The cycle-11 follow-up to "
        "cycle 10: instead of today's survivors, the cross-section at each monthly rebalance t "
        "is the POINT-IN-TIME S&P 500 membership (point_in_time_universe(t), look-ahead-safe) "
        "intersected with names having a price, PIT TTM earnings, and PIT shares as-of t. Long "
        "the top earnings-yield tercile, short the bottom, dollar-neutral, equal-weight, "
        "gross_leverage=1.0. Decisive test: does long-only beat equal-weight of the PIT-tradable "
        "set (gross profitability did NOT in cycle 10), and is the L/S spread positive and "
        "significant? Tests whether VALUE survives on the honest PIT universe where QUALITY died."
    ),
    taxonomy=["value"],
    feature_families=["price", "fundamentals"],
    universe="sp500_pit_union",
    params={
        "quantile": 0.33,
        "rebalance": 21,
        "filed_lag_days": 0,
        "min_names": 12,
        "min_quarters": 4,
    },
    author="quant-researcher",
    references=[
        "Basu (1977), Investment Performance of Common Stocks in Relation to Their P/E Ratios, JF",
        "Fama & French (1992), The Cross-Section of Expected Stock Returns, JF",
        "fja05680/sp500 -- S&P 500 Historical Components & Changes (free PIT membership)",
    ],
    prior_art="reimplements: earnings-yield value on PIT universe",
    novel_combination="earnings-yield value on point-in-time S&P500 universe",
    gross_leverage=1.0,
)


# --------------------------------------------------------------------------- #
# Trailing-twelve-month NetIncomeLoss, point-in-time, from YTD-cumulative XBRL
# --------------------------------------------------------------------------- #
def ttm_net_income_asof(
    tickers: list[str],
    dates: pd.DatetimeIndex,
    filed_lag_days: int = 0,
    min_quarters: int = 4,
    ni_panel: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Point-in-time TTM net income, (dates x tickers), using ONLY filed<=date data.

    XBRL income flows are YTD-cumulative within a fiscal year (Q1=3mo, Q2=6mo, Q3=9mo,
    FY=12mo), then reset. To get discrete quarters we sort each ticker's NetIncomeLoss
    facts by period ``end`` and, within a fiscal year (identified by the YTD ``start``),
    difference consecutive cumulative values; a fact whose period length is ~one quarter
    (<=100 days) is already discrete. We then build, for each (ticker), a time series of
    discrete-quarter net income indexed by the fact's ``filed`` date (availability), and at
    each trading ``date`` sum the most recent ``min_quarters`` quarters with filed<=date.

    A pre-built ``ni_panel`` (long EDGAR format with start/end/filed/val) may be injected
    (placebo/proof scripts); otherwise it is fetched from EDGAR. Look-ahead safety: every
    discrete quarter is stamped with the ``filed`` date of the cumulative figure it was
    derived from, and we only ever sum quarters filed on/before the trading date.
    """
    from finance_agent.edgar import get_edgar_fundamentals

    if ni_panel is None:
        ni_panel = get_edgar_fundamentals(tickers, ["NetIncomeLoss"])
    if ni_panel is None or ni_panel.empty:
        return pd.DataFrame(index=dates, columns=tickers, dtype=float)

    p = ni_panel.copy()
    p = p[p["concept"] == "NetIncomeLoss"] if "concept" in p.columns else p
    p["filed"] = pd.to_datetime(p["filed"])
    p["end"] = pd.to_datetime(p["end"])
    p["start"] = pd.to_datetime(p["start"])
    if filed_lag_days:
        p["filed"] = p["filed"] + pd.Timedelta(days=filed_lag_days)

    grid = pd.DatetimeIndex(pd.to_datetime(dates)).sort_values().unique()
    out = pd.DataFrame(index=grid, columns=tickers, dtype=float)

    for tk, grp in p.groupby("ticker"):
        if tk not in tickers:
            continue
        # discrete quarters: (period_end, filed, q_val)
        quarters = _reconstruct_discrete_quarters(grp)
        if len(quarters) < min_quarters:
            continue
        qdf = pd.DataFrame(quarters, columns=["end", "filed", "val"]).sort_values(["filed", "end"])
        # For each trading date, sum the most recent `min_quarters` DISTINCT-period quarters
        # whose filed <= date. We resolve by walking filed dates.
        ttm = _ttm_series(qdf, grid, min_quarters)
        out[tk] = ttm.reindex(grid).values

    return out.reindex(index=pd.DatetimeIndex(pd.to_datetime(dates)))


def _reconstruct_discrete_quarters(grp: pd.DataFrame) -> list[tuple]:
    """Turn one ticker's YTD-cumulative NetIncomeLoss facts into discrete quarters.

    Returns a list of (period_end, filed, discrete_quarter_value). Strategy:
    sort by period end; for each fact compute its period length (end-start in days). If
    ~<=100 days it is already a single quarter. If it is a multi-quarter YTD figure, we
    subtract the immediately-preceding YTD figure of the SAME fiscal year (same ``start``)
    to recover the marginal quarter. The discrete quarter inherits the ``filed`` date of the
    cumulative figure it is derived from (availability is when the later filing appeared).
    """
    g = grp.dropna(subset=["end", "filed", "val"]).copy()
    if g.empty:
        return []
    g["len_days"] = (g["end"] - g["start"]).dt.days
    g = g.sort_values("end")

    quarters: list[tuple] = []
    # Group by fiscal-year YTD anchor: facts sharing a `start` are cumulative within a FY.
    for start_val, fy in g.groupby("start"):
        fy = fy.sort_values("end")
        prev_cum = 0.0
        prev_end = None
        for _, r in fy.iterrows():
            length = r["len_days"]
            if pd.isna(length):
                continue
            if length <= 100:
                # already a discrete quarter
                q = float(r["val"])
            else:
                # YTD cumulative: marginal quarter = this YTD - previous YTD in same FY
                q = float(r["val"]) - prev_cum
                prev_cum = float(r["val"])
                prev_end = r["end"]
                quarters.append((r["end"], r["filed"], q))
                continue
            prev_cum = float(r["val"])
            prev_end = r["end"]
            quarters.append((r["end"], r["filed"], q))
    # Deduplicate by period end (keep earliest filed = as-originally-reported), sort by end.
    if not quarters:
        return []
    qdf = (
        pd.DataFrame(quarters, columns=["end", "filed", "val"])
        .sort_values("filed")
        .drop_duplicates("end", keep="first")
        .sort_values("end")
    )
    return list(qdf.itertuples(index=False, name=None))


def _ttm_series(qdf: pd.DataFrame, grid: pd.DatetimeIndex, min_quarters: int) -> pd.Series:
    """TTM (sum of trailing `min_quarters` discrete quarters) as-of each grid date.

    qdf has columns [end, filed, val], sorted by filed. At each filed date we recompute TTM
    as the sum of the `min_quarters` most-recent-by-period-end quarters known so far, then
    forward-fill onto the grid (each trading date carries the latest TTM with filed<=date).
    """
    # Build a step series keyed by filed date: after each filing, recompute TTM from all
    # quarters known up to that filed date.
    qdf = qdf.sort_values("filed")
    known: dict[pd.Timestamp, float] = {}  # period_end -> quarter val (latest known)
    ttm_by_filed: dict[pd.Timestamp, float] = {}
    for _, r in qdf.iterrows():
        known[r["end"]] = r["val"]
        # most recent min_quarters by period end
        ends = sorted(known.keys())
        recent = ends[-min_quarters:]
        if len(recent) >= min_quarters:
            ttm_by_filed[r["filed"]] = float(sum(known[e] for e in recent))
    if not ttm_by_filed:
        return pd.Series(index=grid, dtype=float)
    s = pd.Series(ttm_by_filed).sort_index()
    s = s[~s.index.duplicated(keep="last")]
    aligned = s.reindex(s.index.union(grid)).ffill().reindex(grid)
    return aligned


# --------------------------------------------------------------------------- #
# Point-in-time shares outstanding, with tag fallback
# --------------------------------------------------------------------------- #
def shares_asof(
    tickers: list[str],
    dates: pd.DatetimeIndex,
    filed_lag_days: int = 0,
    panels: dict | None = None,
) -> pd.DataFrame:
    """Point-in-time shares outstanding, (dates x tickers), filed<=date.

    Tries, per name, in preference order: dei:EntityCommonStockSharesOutstanding,
    us-gaap:CommonStockSharesOutstanding, us-gaap:WeightedAverageNumberOfSharesOutstandingBasic.
    First tag with data wins per name. ``panels`` (a dict tag -> long EDGAR frame) may be
    injected to avoid network. Look-ahead safety via point_in_time_asof.
    """
    from finance_agent.edgar import get_edgar_concept, point_in_time_asof, get_company_tickers

    grid = pd.DatetimeIndex(pd.to_datetime(dates)).sort_values().unique()
    out = pd.DataFrame(index=grid, columns=tickers, dtype=float)

    tag_specs = [
        ("dei", "EntityCommonStockSharesOutstanding"),
        ("us-gaap", "CommonStockSharesOutstanding"),
        ("us-gaap", "WeightedAverageNumberOfSharesOutstandingBasic"),
    ]
    cmap = None
    try:
        cmap = get_company_tickers()
    except Exception:
        cmap = None

    for tk in tickers:
        filled = False
        for tax, tag in tag_specs:
            if panels is not None:
                df = panels.get((tk, tax, tag))
            else:
                try:
                    df = get_edgar_concept(tk, tag, taxonomy=tax, unit="shares", tickers_df=cmap)
                except Exception:
                    df = None
            if df is None or len(df) == 0:
                continue
            d = df.copy()
            d["ticker"] = tk
            d["concept"] = "Shares"
            if filed_lag_days:
                d["filed"] = pd.to_datetime(d["filed"]) + pd.Timedelta(days=filed_lag_days)
            wide = point_in_time_asof(d[["ticker", "concept", "end", "filed", "val"]], grid)
            try:
                ser = wide[(tk, "Shares")]
            except KeyError:
                continue
            if ser.notna().any():
                out[tk] = ser.reindex(grid).values
                filled = True
                break
        if not filled:
            continue
    return out.reindex(index=pd.DatetimeIndex(pd.to_datetime(dates)))


# --------------------------------------------------------------------------- #
# Earnings-yield panel
# --------------------------------------------------------------------------- #
def earnings_yield_asof(
    tickers: list[str],
    prices: pd.DataFrame,
    filed_lag_days: int = 0,
    min_quarters: int = 4,
    ttm_ni: pd.DataFrame | None = None,
    shares: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Point-in-time earnings yield (dates x tickers) = TTM_NetIncome / (price * shares).

    All inputs filed<=date. ``ttm_ni`` and ``shares`` panels may be injected (eval/placebo);
    otherwise fetched from EDGAR.
    """
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
    ey = ey.where(mktcap > 0)
    return ey


# --------------------------------------------------------------------------- #
# Point-in-time membership mask (shared with the GP-PIT pattern)
# --------------------------------------------------------------------------- #
def pit_membership_mask(
    dates: pd.DatetimeIndex,
    columns: pd.Index,
    rebal_dates: pd.DatetimeIndex,
    use_cache: bool = True,
) -> pd.DataFrame:
    """Boolean (dates x columns): True iff ticker was an S&P 500 member as-of each date.

    Evaluated only on rebalance dates (weights are ffill'd elsewhere). Uses
    ``point_in_time_universe(t)`` (changes effective <= t only; look-ahead-safe).
    """
    from finance_agent.universe import point_in_time_universe

    mask = pd.DataFrame(False, index=dates, columns=columns)
    colset = set(columns)
    for dt in rebal_dates:
        members = set(point_in_time_universe(dt, use_cache=use_cache)) & colset
        if members:
            mask.loc[dt, list(members)] = True
    return mask


# --------------------------------------------------------------------------- #
# Weights from signal with PIT membership gate + drop logging
# --------------------------------------------------------------------------- #
def weights_from_signal(
    signal: pd.DataFrame,
    membership: pd.DataFrame,
    index: pd.DatetimeIndex,
    columns: pd.Index,
    quantile: float,
    rebalance: int,
    min_names: int,
    drop_log: list | None = None,
) -> pd.DataFrame:
    """Tercile dollar-neutral L/S weights from a (dates x names) earnings-yield signal,
    gated by PIT membership, then ffill'd. Higher signal = long. Optionally logs drops.
    """
    weights = pd.DataFrame(index=index, columns=columns, dtype=float)
    rebal_dates = index[::rebalance]
    for dt in rebal_dates:
        if dt not in signal.index or dt not in membership.index:
            continue
        members = membership.loc[dt]
        member_names = members[members].index
        if len(member_names) == 0:
            continue
        row = signal.loc[dt, member_names].dropna()
        n_members = len(member_names)
        n_usable = len(row)
        if drop_log is not None:
            drop_log.append(
                {"date": dt, "n_members": int(n_members), "n_usable": int(n_usable),
                 "n_dropped": int(n_members - n_usable)}
            )
        if n_usable < min_names:
            continue
        hi = row.quantile(1 - quantile)
        lo = row.quantile(quantile)
        longs = row[row >= hi].index
        shorts = row[row <= lo].index
        if len(longs) == 0 or len(shorts) == 0:
            continue
        w = pd.Series(0.0, index=columns)
        w[longs] = 0.5 / len(longs)
        w[shorts] = -0.5 / len(shorts)
        weights.loc[dt] = w.values
    return weights.ffill().fillna(0.0)


def generate_weights(
    prices: pd.DataFrame,
    quantile: float = 0.33,
    rebalance: int = 21,
    filed_lag_days: int = 0,
    min_names: int = 12,
    min_quarters: int = 4,
    drop_log: list | None = None,
) -> pd.DataFrame:
    """Dollar-neutral earnings-yield value L/S weights (dates x tickers) on a PIT universe.

    Cross-section at each rebalance = point_in_time_universe(t) INTERSECT {priced columns}
    INTERSECT {names with PIT TTM earnings filed<=t} INTERSECT {names with PIT shares
    filed<=t}. Only past data per row; the engine adds the 1-day lag. ``prices`` should be
    the WIDE historical-constituent panel (SPEC.universe="sp500_pit_union"); a narrow panel
    degrades to whatever columns are present.
    """
    names = [t for t in prices.columns if not prices[t].dropna().empty]
    ey = earnings_yield_asof(names, prices[names], filed_lag_days=filed_lag_days,
                             min_quarters=min_quarters)
    rebal_dates = prices.index[::rebalance]
    membership = pit_membership_mask(prices.index, pd.Index(names), rebal_dates)
    priced = prices[names].notna()
    membership = membership & priced.reindex(columns=names).fillna(False)

    weights = weights_from_signal(
        ey.reindex(columns=names), membership.reindex(columns=names),
        prices.index, pd.Index(names), quantile, rebalance, min_names, drop_log=drop_log,
    )
    out = pd.DataFrame(0.0, index=prices.index, columns=prices.columns)
    out[names] = weights[names]
    return out
