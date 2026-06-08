"""Turn-of-month (TOM) tilt on SPY — a mild seasonal oscillation, not an in/out switch.

Lens: seasonality_calendar. Seeded by cycle-3 lit-scout web research: McConnell & Xu
(2008/2011, Financial Analysts Journal) document that essentially ALL of the equity
market's positive return historically accrues in the window spanning the last trading
day of a month through the first three trading days of the next month — and that the
effect survives into the ETF era. A 2026 infrequent-rebalancing TOM study reinforces
that the tradable edge is concentrated on the FIRST trading day and that the effect must
be harvested with very few rebalances, because a naive 100/0 in-out version churns to
cash for ~16 days/month and loses to buy-and-hold after costs.

Economic / behavioral mechanism
-------------------------------
The TOM seasonal is an *institutional-flow* anomaly, not a risk premium. Around the
turn of the month a recurring, calendar-locked wall of price-insensitive buying hits
equities: (1) payroll-driven 401(k)/DC retirement contributions and automatic index-fund
purchases settle at month boundaries; (2) pension and mutual funds reinvest coupon/
dividend cash and rebalance to month-end mandates; (3) performance reporting and
window-dressing concentrate demand at the turn. Because the flow is *predictable in
timing but inelastic in price*, it pushes prices up over the turn window and reverses
mildly thereafter. The signal is a pure function of the calendar (known in advance), so
there is no forecasting risk — only the structural question of whether the flow persists.

Why a TILT and not a switch
---------------------------
The honest finding (and the explicit reason this is built as a tilt) is that going
100% SPY in the ~4-day window and 100% cash otherwise underperforms buy-and-hold after
costs: you forfeit ~16 trading days/month of equity risk premium and pay a round-trip
every month. So instead we hold SPY *all the time* and apply a SMALL overweight during
the TOM window funded by a SMALL underweight outside it, parking the underweight in a
defensive blend (TLT/GLD/HYG) rather than cash so we still earn carry. The amplitude is
a single small tunable knob (default 12 pct of book, to be stress-tested at 10-20 bps of
tilt economics later). With only two rebalances per month — the two window edges —
turnover is inherently tiny.

Window FIXED FROM THEORY (no in-sample day fitting)
---------------------------------------------------
The TOM window is set a priori from the literature: the last trading day of month T-1
through trading day +3 of month T (~4 trading days), and within that window the tilt is
weighted toward days 0/+1 (the recent ETF-era evidence concentrates the effect on the
first trading day). These day boundaries are NOT optimized on the sample — that would be
a data-snooping/look-ahead trap. The only quantities estimated from data are the trailing
inverse-vol weights of the defensive parking blend, which use past prices only.

The trading-day calendar is derived FROM THE PRICE INDEX ITSELF (group by year-month;
the window is the last index date of the prior month plus the first few index dates of
the current month). No external/exchange calendar is used, so the window is always
self-consistent with the data the engine sees.

Construction
------------
Fully-invested rotation (gross_leverage = 1.0): the book is always 100% allocated, it
just shifts a small slice between SPY and the defensive blend. We therefore prefer the
defensive-parking version (no cash drag) so the rotation is tested cleanly, and set
SPEC.gross_leverage = 1.0. Inside the TOM window: ~100% SPY. Outside: SPY underweighted
by ``tilt`` (default 0.12), with the freed weight allocated across TLT/GLD/HYG by trailing
inverse volatility (a defensive, low-correlation blend rather than a single bond bet).

Benchmark and falsification
---------------------------
Benchmark = buy-and-hold SPY, judged on Sharpe AND max drawdown at equal-or-lower trading
cost. This strategy FAILS / is falsified if:
* Net-of-cost Sharpe does not beat buy-and-hold SPY (the flow edge is too small to matter
  after the defensive blend's own drag).
* It does NOT hold in BOTH the pre-2010 and post-2010 sub-samples (decay would show up
  post-ETF-saturation) AND in BOTH the pre-2015 and post-2015 sub-samples — required
  robustness; a result living in only one regime is fit, not real.
* The edge requires the amplitude to be large (no monotone, stable behavior as ``tilt``
  is swept 0.05 -> 0.25): a knife-edge amplitude means it is overfit.
* Max drawdown is materially worse than buy-and-hold (the defensive parking is supposed
  to be risk-neutral-to-helpful, not a hidden duration/credit bet that adds tail risk).
* Turnover/costs erase the small edge — with only ~2 rebalances/month this should be
  comfortable, and if it isn't the idea is not implementable here.

Data limitations
----------------
Price-only (yfinance adjusted closes, already cached). The institutional-flow mechanism
is inferred, not measured — we do not have settlement/fund-flow data, so we proxy it
purely with the calendar window. Degrades gracefully: any missing defensive ticker is
dropped and the inverse-vol blend renormalizes over what remains; if NONE of the
defensive tickers are present the off-window weight stays in SPY (so it collapses to
buy-and-hold rather than erroring).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from finance_agent.strategy import StrategySpec

SPEC = StrategySpec(
    id="tom_tilt_spy",
    thesis=(
        "Turn-of-month seasonal tilt on SPY: hold SPY at all times but apply a small "
        "calendar-locked overweight during the turn-of-month window (last trading day "
        "of the prior month through trading day +3, weighted toward days 0/+1), funded "
        "by a small underweight parked in a defensive TLT/GLD/HYG inverse-vol blend the "
        "rest of the month. Harvests the institutional-flow TOM anomaly (payroll/401k "
        "inflows, dividend reinvestment, month-end rebalancing) as a mild oscillation "
        "rather than an in/out switch, so it keeps the equity risk premium and only "
        "rebalances ~twice a month. Window is fixed from theory, not fit; fully-invested "
        "rotation with no cash drag."
    ),
    taxonomy=["seasonality_calendar"],
    feature_families=["price"],
    universe="default",
    params={
        "core": "SPY",
        "defensive": ("TLT", "GLD", "HYG"),
        "pre_days": 1,    # include the last trading day of the prior month (day -1 / TD0)
        "post_days": 3,   # ...through trading day +3 of the current month
        "tilt": 0.12,     # SMALL off-window underweight of SPY (stress-test 0.05->0.25)
        "vol_window": 90,  # trailing window for defensive-blend inverse-vol weights
    },
    author="quant-researcher",
    references=[
        "McConnell & Xu (2008/2011), Equity Returns at the Turn of the Month, "
        "Financial Analysts Journal (ETF-era turn-of-month effect)",
        "2026 infrequent-rebalancing turn-of-month study (TOM harvested with few "
        "rebalances; effect concentrated on the first trading day)",
    ],
    gross_leverage=1.0,  # fully-invested rotation: SPY <-> defensive blend, no cash leg
)


def _tom_mask(index: pd.DatetimeIndex, pre_days: int, post_days: int) -> pd.Series:
    """Boolean per-date: is this date inside the turn-of-month window?

    The window = the last ``pre_days`` trading dates of the prior month + the first
    ``post_days`` trading dates of the current month. The calendar is derived purely
    from the price index (group by year-month, rank within month), so it depends only
    on which dates are present — no external calendar, no future data.
    """
    idx = pd.DatetimeIndex(index)
    ym = idx.to_period("M")
    df = pd.DataFrame({"ym": ym}, index=idx)
    # Trading-day ordinal within each month: 0 = first trading day, ... ; and from the end.
    df["rank_fwd"] = df.groupby("ym").cumcount()                       # 0,1,2,... from start
    grp_size = df.groupby("ym")["ym"].transform("size").to_numpy()
    df["rank_bwd"] = grp_size - 1 - df["rank_fwd"].to_numpy()          # 0 = last trading day

    first_of_month = df["rank_fwd"] < post_days        # first post_days trading days (TD0..)
    last_of_month = df["rank_bwd"] < pre_days           # last pre_days trading days of month
    return (first_of_month | last_of_month).to_numpy()


def generate_weights(
    prices: pd.DataFrame,
    core: str = "SPY",
    defensive=("TLT", "GLD", "HYG"),
    pre_days: int = 1,
    post_days: int = 3,
    tilt: float = 0.12,
    vol_window: int = 90,
) -> pd.DataFrame:
    """Return fully-invested weights (dates x tickers): SPY oscillating with a defensive blend.

    Each row's allocation is a function of (a) the calendar position of the date — known
    in advance — and (b) trailing inverse-vol weights of the defensive blend computed from
    prices up to and including that date. No future data is used; the engine adds the
    1-day execution lag.

    Inside the TOM window: 100% ``core``. Outside: ``(1 - tilt)`` in ``core`` and ``tilt``
    spread across the available ``defensive`` tickers by trailing inverse volatility.
    """
    if core not in prices.columns:
        raise ValueError(f"core asset {core!r} not in price universe")
    tilt = float(np.clip(tilt, 0.0, 1.0))

    weights = pd.DataFrame(0.0, index=prices.index, columns=prices.columns)

    # Defensive tickers actually present in the panel; degrade gracefully if some/all absent.
    def_assets = [t for t in defensive if t in prices.columns]

    in_window = _tom_mask(prices.index, pre_days, post_days)  # length-N boolean array

    # SPY leg: 1.0 inside the window, (1 - tilt) outside it.
    spy_w = np.where(in_window, 1.0, 1.0 - tilt)

    if not def_assets or tilt == 0.0:
        # No place to park (or zero tilt): collapse to buy-and-hold SPY.
        weights[core] = 1.0
        return weights

    # Trailing inverse-vol weights for the defensive blend (past data only).
    def_px = prices[def_assets].astype(float)
    rets = def_px.pct_change()
    vol = rets.rolling(vol_window, min_periods=max(20, vol_window // 3)).std()
    inv = 1.0 / vol.replace(0.0, np.nan)
    blend = inv.div(inv.sum(axis=1), axis=0)  # rows sum to 1 across def_assets
    # Before enough history exists, fall back to equal weight across the defensive blend.
    eq = pd.Series(1.0 / len(def_assets), index=def_assets)
    blend = blend.fillna(eq)

    off_amt = np.where(in_window, 0.0, tilt)  # weight to allocate to defensive blend

    weights[core] = spy_w
    for a in def_assets:
        weights[a] = off_amt * blend[a].to_numpy()

    return weights
