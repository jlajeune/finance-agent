"""Gross-profitability long/short — on a POINT-IN-TIME S&P 500 universe (survivorship-controlled).

Lens: quality. This is the **honest re-run of cycle 9**. Same factor as
``gross_profitability_ls`` (Novy-Marx 2013, ``GP/Assets = (Revenues - CostOfRevenue) / Assets``,
every input pulled point-in-time via the EDGAR ``point_in_time_asof`` guard), but the *universe*
is no longer today's 30 surviving large-caps. At each rebalance date the cross-section is the
**point-in-time S&P 500 membership** (``point_in_time_universe(t)``) intersected with the names
that actually have a price and a filed fundamental as-of ``t``. This includes names that were
in the index then but later removed/delisted — the very losers (financial-crisis casualties,
acquisitions) whose *absence* from the cycle-9 sample is suspected to have inflated the long
leg. The experiment: does the gross-profitability edge appear, shrink, or stay dead once the
losers are back in?

PRIOR ART / NOVELTY
-------------------
This is explicitly a **re-implementation** of a decades-old factor, run as a survivorship
control experiment — NOT a novelty claim. ``prior_art = "reimplements: Novy-Marx 2013 on a
point-in-time universe"``. The only new thing vs cycle 9 is the universe construction
(``novel_combination``: gross profitability on a point-in-time S&P 500 universe).

Economic mechanism (unchanged from Novy-Marx)
---------------------------------------------
Gross profitability sits above the income-statement line where managers make discretionary,
value-destroying choices. Novy-Marx finds it predicts the cross-section about as well as
book-to-market and diversifies value. The premium is rationalized as a risk premium for
unglamorous "quality" firms the market under-prices, and/or slow diffusion of profitability
information. The falsifiable question here is narrower: was the cycle-9 long-leg strength the
*factor*, or just survivorship in the ticker list?

UNIVERSE (note: strategy builds its own PIT universe internally)
----------------------------------------------------------------
``SPEC.universe = "default"`` for the standardized harness, but this strategy does NOT trade
the default 30 names. At each monthly rebalance ``t`` it forms its tradable set as
``point_in_time_universe(t)`` (look-ahead-safe: only membership changes effective <= t) ∩
{names with a price at t in the supplied ``prices``} ∩ {names with PIT fundamentals filed <= t}.
The eval script (``scratch/eval_gross_profitability_pit.py``) supplies a WIDE price panel
(historical-constituent union) so ``run_backtest`` scores returns on the right names. If only
the narrow default panel is supplied, the strategy degrades to whatever columns are present.

Look-ahead safety
-----------------
1. Membership: ``point_in_time_universe(t)`` applies only changes with effective_date <= t.
2. Fundamentals: ``point_in_time_asof`` returns the latest value with SEC ``filed`` <= t.
3. Prices supply only the date grid / return panel; the engine adds the 1-day execution lag.
No ``.shift(-k)``, no centered windows, no full-sample normalization.

Construction
-----------
Tercile dollar-neutral L/S (long top GP/Assets, short bottom), equal-weight within each leg,
monthly rebalance, ``gross_leverage = 1.0``. Names with any missing PIT input or no PIT
membership at t are dropped (0 weight) that period.

Falsification / failure conditions
----------------------------------
* If, with losers included, the L/S spread is still flat-to-negative and insignificant, the
  GP premium is absent in the free PIT S&P universe (XBRL era).
* If the long-only top tercile no longer beats equal-weight of the *same PIT-tradable set*,
  cycle 9's long-leg "strength" was survivorship — confirmed.
* Filing-shuffle placebo: if shuffling GP across names does about as well, the factor carries
  no information beyond turnover.

Data limitations (stated honestly)
----------------------------------
* RESIDUAL price-survivorship. Membership is now point-in-time, but yfinance lacks ~47% of
  exited names' prices. Some removed names cannot be priced and are dropped, so a residual
  survivorship bias remains; the eval logs the average # names dropped/period as a bound.
  Full fix = paid delisting-complete prices (CRSP / Sharadar).
* XBRL starts ~2009 -> sample begins ~2010; only ~711/1201 historical constituents have a CIK.
* US filers only; concept tags vary (connector merges synonyms).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from finance_agent.strategy import StrategySpec

SPEC = StrategySpec(
    id="gross_profitability_pit",
    thesis=(
        "Point-in-time gross profitability (Novy-Marx 2013): GP/Assets = "
        "(Revenues - CostOfRevenue) / Assets, every input pulled as-of its SEC filing date "
        "via the EDGAR point_in_time_asof guard. The honest re-run of cycle 9: instead of "
        "today's 30 surviving large-caps, the cross-section at each monthly rebalance t is the "
        "POINT-IN-TIME S&P 500 membership (point_in_time_universe(t), look-ahead-safe) "
        "intersected with names having a price and a filed fundamental as-of t. This puts the "
        "later-removed losers (financial-crisis casualties, acquisitions) back in the sample. "
        "Long the top GP/Assets tercile, short the bottom, dollar-neutral, equal-weight, "
        "gross_leverage=1.0. The decisive test: does the long-only tercile now beat equal-weight "
        "of the PIT-tradable set (it did NOT on survivors), and is the L/S spread positive? A "
        "LOWER long-only Sharpe than cycle 9 would confirm survivorship inflated cycle 9."
    ),
    taxonomy=["quality"],
    feature_families=["price", "fundamentals"],
    universe="default",
    params={
        "quantile": 0.33,
        "rebalance": 21,
        "filed_lag_days": 0,
        "min_names": 12,
    },
    author="quant-researcher",
    references=[
        "Novy-Marx (2013), The Other Side of Value: The Gross Profitability Premium, JFE",
        "fja05680/sp500 — S&P 500 Historical Components & Changes (free PIT membership)",
    ],
    prior_art="reimplements: Novy-Marx 2013 on a point-in-time universe",
    novel_combination=(
        "gross profitability on a point-in-time S&P 500 universe (survivorship-controlled)"
    ),
    gross_leverage=1.0,
)


# --------------------------------------------------------------------------- #
# Point-in-time GP/Assets panel
# --------------------------------------------------------------------------- #
def gp_asof(
    tickers: list[str],
    dates: pd.DatetimeIndex,
    filed_lag_days: int = 0,
    panel: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Point-in-time GP/Assets, (dates x tickers), using ONLY filed<=date data.

    ``filed_lag_days`` optionally shifts every ``filed`` date *later* (more conservative
    availability) — used by the look-ahead proof; 0 in production. A pre-built ``panel`` can
    be injected (placebo / proof scripts); otherwise it is fetched from EDGAR. Look-ahead
    safety lives entirely in ``point_in_time_asof``.
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
        val = val.where(assets > 0)
        gp[tk] = val
    return gp


# --------------------------------------------------------------------------- #
# Point-in-time membership mask, (dates x tickers) boolean
# --------------------------------------------------------------------------- #
def pit_membership_mask(
    dates: pd.DatetimeIndex,
    columns: pd.Index,
    rebal_dates: pd.DatetimeIndex,
    use_cache: bool = True,
) -> pd.DataFrame:
    """Boolean (dates x columns): True iff a ticker was an S&P 500 member as-of each date.

    Only evaluated on rebalance dates (the rest is irrelevant — weights are ffill'd). Uses
    ``point_in_time_universe(t)`` which applies only changes effective <= t (look-ahead-safe).
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
# Weights from signal, with PIT membership gate + drop-count logging
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
    """Tercile dollar-neutral L/S weights from a (dates x names) GP signal, gated by PIT
    membership, then ffill'd. Optionally appends per-period drop diagnostics to ``drop_log``.
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
        # Of the PIT members, how many have a usable GP value as-of dt?
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
    drop_log: list | None = None,
) -> pd.DataFrame:
    """Dollar-neutral gross-profitability L/S weights (dates x tickers) on a PIT universe.

    The cross-section at each rebalance = point_in_time_universe(t) ∩ {priced columns} ∩
    {names with PIT fundamentals filed <= t}. Only past data at each row: GP uses fundamentals
    filed <= t; membership uses changes effective <= t. The engine adds the 1-day lag.

    ``prices`` should be the WIDE historical-constituent price panel (supplied by the eval
    script). If only a narrow panel is passed, the strategy degrades to those columns.
    """
    names = [t for t in prices.columns if not prices[t].dropna().empty]
    gp = gp_asof(names, prices.index, filed_lag_days=filed_lag_days)
    rebal_dates = prices.index[::rebalance]
    membership = pit_membership_mask(prices.index, pd.Index(names), rebal_dates)
    # Only consider a name "priced at t" if it has a non-NaN price on/before the rebalance.
    priced = prices[names].notna()
    membership = membership & priced.reindex(columns=names).fillna(False)

    weights = weights_from_signal(
        gp.reindex(columns=names), membership.reindex(columns=names),
        prices.index, pd.Index(names), quantile, rebalance, min_names, drop_log=drop_log,
    )
    out = pd.DataFrame(0.0, index=prices.index, columns=prices.columns)
    out[names] = weights[names]
    return out
