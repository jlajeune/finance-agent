"""Gross-profitability long/short equity sleeve — point-in-time correct (EDGAR).

Lens: quality. This is a deliberate **re-implementation** of a known, decades-old factor
(Novy-Marx 2013, "The Other Side of Value: The Gross Profitability Premium") used as a
risk-managed-portfolio SLEEVE, NOT a novelty claim. The contribution here is mechanical
honesty: every fundamental input is pulled **point-in-time** via the EDGAR connector's
``point_in_time_asof`` guard, so the factor at date t uses only values whose SEC ``filed``
date is <= t — never a period-``end`` date (which would leak ~20-75 days of look-ahead).

Economic mechanism
------------------
Gross profitability, ``GP/Assets = (Revenues - CostOfRevenue) / Assets``, is the cleanest
profitability measure on the income statement: it sits *above* the line where managers
make discretionary, value-destroying choices (SG&A, R&D capitalization, depreciation
policy, financing). Novy-Marx shows it predicts the cross-section of returns about as well
as book-to-market, and is *negatively* correlated with value, so a gross-profitability
tilt diversifies a classic value book. The premium is usually rationalized as (a) a
risk-premium for productive but unglamorous "quality" firms the market under-prices
relative to flashier growth names, and/or (b) slow diffusion of profitability information.
Profitable firms keep earning; the market is slow to fully price persistent gross margin.

Construction
-----------
* Universe: the ~30 single-name large-caps in ``DEFAULT_UNIVERSE`` (ETFs excluded — they
  have no fundamentals).
* Inputs via ``get_edgar_fundamentals(tickers, ["Revenues","CostOfRevenue","Assets"])``,
  which merges synonym XBRL tags (e.g. CostOfGoodsAndServicesSold) per period.
* At each MONTHLY rebalance date, ``point_in_time_asof`` returns the latest value with
  ``filed <= date`` for each (name, concept). Compute GP/Assets. Names with any missing
  PIT input -> dropped (0 weight) at that date.
* Cross-sectional: rank GP/Assets, LONG top tercile, SHORT bottom tercile, dollar-neutral,
  equal-weight within each leg. Monthly rebalance (fundamentals move quarterly -> low
  turnover). ``gross_leverage = 1.0``.

Falsification / failure conditions
----------------------------------
* If the L/S spread is not positive with a defensible t-stat, the premium is absent in
  this short XBRL-era sample / tiny universe.
* **Filing-shuffle placebo:** if shuffling GP values across names (breaking the
  value->name link) does about as well, the "factor" is just rebalancing/turnover, not
  profitability — and we reject it.
* If shifting all ``filed`` dates 90 days later changes results discontinuously, the
  signal was secretly relying on too-fresh data (a look-ahead leak).
* If the long-only top tercile does not beat equal-weight of the same universe and SPY on
  a risk-adjusted basis, the sleeve adds nothing to the risk-managed portfolio.

Data limitations (stated honestly)
----------------------------------
* **Survivorship in the UNIVERSE selection.** The EDGAR *data* is point-in-time, but the
  *ticker list* is today's surviving large-caps. We do not yet have a point-in-time
  constituent list (a future Tier-0 build), so the universe itself is forward-looking.
  This inflates returns and is the single biggest caveat.
* XBRL history begins ~2009, so the usable sample is short -> modest statistical power.
* US filers only; quarterly/annual cadence; concept tags vary across filers (the connector
  merges synonyms but per-name coverage must still be verified — names without data drop).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from finance_agent.strategy import StrategySpec

# The single-name equities in DEFAULT_UNIVERSE (ETFs have no fundamentals -> excluded).
EQUITY_NAMES = [
    "AAPL", "MSFT", "AMZN", "GOOGL", "META", "NVDA", "TSLA", "BRK-B", "JPM", "V",
    "JNJ", "WMT", "PG", "MA", "HD", "XOM", "CVX", "KO", "PEP", "ABBV",
    "BAC", "PFE", "AVGO", "COST", "DIS", "CSCO", "MRK", "ORCL", "ACN", "MCD",
]

SPEC = StrategySpec(
    id="gross_profitability_ls",
    thesis=(
        "Point-in-time gross profitability (Novy-Marx 2013): GP/Assets = "
        "(Revenues - CostOfRevenue) / Assets, every input pulled as-of its SEC filing "
        "date via the EDGAR point_in_time_asof guard (no period-end look-ahead). "
        "Cross-sectionally rank the ~30 single-name large-caps monthly, go long the top "
        "tercile and short the bottom tercile, dollar-neutral and equal-weight, "
        "gross_leverage=1.0. Gross profitability is the cleanest above-the-line quality "
        "measure; profitable firms keep earning and the market is slow to price persistent "
        "gross margin. Used here as an honest equity SLEEVE for the risk-managed portfolio, "
        "not a novelty claim. Quarterly fundamentals -> low turnover."
    ),
    taxonomy=["quality"],
    feature_families=["price", "fundamentals"],
    universe="default",
    params={
        "quantile": 0.33,
        "rebalance": 21,
        "filed_lag_days": 0,
        "min_names": 6,
    },
    author="quant-researcher",
    references=[
        "Novy-Marx (2013), The Other Side of Value: The Gross Profitability Premium, JFE",
    ],
    prior_art="reimplements: Novy-Marx 2013 gross profitability",
    novel_combination=(
        "point-in-time gross-profitability equity sleeve for the risk-managed portfolio"
    ),
    gross_leverage=1.0,
)


def _gp_asof(
    tickers: list[str],
    dates: pd.DatetimeIndex,
    filed_lag_days: int = 0,
    panel: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Point-in-time GP/Assets, (dates x tickers), using ONLY filed<=date data.

    ``filed_lag_days`` optionally shifts every ``filed`` date *later* (more conservative
    availability) — used by the look-ahead proof; 0 in production.

    A pre-built ``panel`` can be injected (placebo / proof scripts); otherwise it is
    fetched from EDGAR. Look-ahead safety lives entirely in ``point_in_time_asof``.
    """
    from finance_agent.edgar import get_edgar_fundamentals, point_in_time_asof

    if panel is None:
        panel = get_edgar_fundamentals(tickers, ["Revenues", "CostOfRevenue", "Assets"])
    if panel is None or panel.empty:
        return pd.DataFrame(index=dates, columns=tickers, dtype=float)

    panel = panel.copy()
    if filed_lag_days:
        panel["filed"] = pd.to_datetime(panel["filed"]) + pd.Timedelta(days=filed_lag_days)

    wide = point_in_time_asof(panel, dates)  # MultiIndex columns (ticker, concept)
    if wide.empty:
        return pd.DataFrame(index=dates, columns=tickers, dtype=float)

    gp = pd.DataFrame(index=dates, columns=tickers, dtype=float)
    for tk in tickers:
        try:
            rev = wide[(tk, "Revenues")]
            cost = wide[(tk, "CostOfRevenue")]
            assets = wide[(tk, "Assets")]
        except KeyError:
            continue
        with np.errstate(divide="ignore", invalid="ignore"):
            val = (rev - cost) / assets
        # Guard against non-positive assets / missing inputs.
        val = val.where(assets > 0)
        gp[tk] = val
    return gp


def _weights_from_signal(
    signal: pd.DataFrame,
    index: pd.DatetimeIndex,
    columns: pd.Index,
    quantile: float,
    rebalance: int,
    min_names: int,
) -> pd.DataFrame:
    """Tercile dollar-neutral L/S weights from a (dates x names) signal, ffill'd."""
    weights = pd.DataFrame(index=index, columns=columns, dtype=float)
    rebal_dates = index[::rebalance]
    for dt in rebal_dates:
        if dt not in signal.index:
            continue
        row = signal.loc[dt].dropna()
        if len(row) < min_names:
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
    min_names: int = 6,
) -> pd.DataFrame:
    """Dollar-neutral gross-profitability L/S weights (dates x tickers).

    Only past data at each row: the GP signal at date t uses only fundamentals with SEC
    ``filed`` <= t (enforced by ``point_in_time_asof``), and prices supply only the date
    grid here. The engine adds the 1-day execution lag. ETFs in ``prices`` get 0 weight.
    """
    names = [t for t in EQUITY_NAMES if t in prices.columns]
    gp = _gp_asof(names, prices.index, filed_lag_days=filed_lag_days)
    weights = _weights_from_signal(
        gp.reindex(columns=names), prices.index, names, quantile, rebalance, min_names
    )
    # Re-expand to the full price column set (ETFs / missing names -> 0).
    out = pd.DataFrame(0.0, index=prices.index, columns=prices.columns)
    out[names] = weights[names]
    return out
