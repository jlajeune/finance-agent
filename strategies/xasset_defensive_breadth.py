"""Cross-asset defensive breadth rotation with a timing-luck ensemble guard.

Lens: cross_asset. Seeded by cycle-3 lit-scout web research: Keller & Keuning (2018)
"Breadth Momentum and the Canary Universe: Defensive Asset Allocation (DAA)" (SSRN
3212862), and Hoffstein/Newfound Research on rebalance timing luck / portfolio fragility.

Economic mechanism
------------------
Two well-documented, persistent effects, combined:

1. **Absolute (dual) momentum / trend.** Risk assets earn their premium in trending
   regimes; in sustained downtrends the equity risk premium does not compensate for the
   left-tail. A 13612W average-momentum score (an average of 1/3/6/12-month returns,
   front-weighted) is a robust, low-noise trend estimate (Keller & Keuning). Rotating OUT
   of risk and INTO whichever defensive asset is itself trending (bonds, gold, credit)
   harvests the trend premium while sidestepping crashes. The mechanism is behavioral
   (under-reaction / slow diffusion of macro information) plus a structural flight-to-
   quality bid that makes defensives trend exactly when equities break.

2. **Breadth as an early-warning gate.** Rather than reacting only to the asset you hold,
   DAA reads a small "canary" basket (SPY = broad equity, IWM = small-cap risk appetite,
   HYG = credit risk appetite). When credit and small-caps roll over, broad market stress
   is usually imminent — these are the canaries in the coal mine. The fraction of canaries
   with non-positive momentum sets the cash fraction, so the book de-risks *before* the
   asset it holds confirms a downtrend. This is the source of DAA's crash protection.

The KEY refinement over classic GEM/dual-momentum: the defensive sleeve only buys a
defensive asset if ITS OWN 13612W is positive; otherwise it holds cash. This avoids the
2022 trap where rigid dual-momentum was forced long bonds into a bond bear market.

Timing-luck ensemble guard (the central design choice)
------------------------------------------------------
Monthly-rebalanced tactical strategies suffer enormous *rebalance timing luck*: a
portfolio that reconstitutes on the 1st can post a wildly different path than the
identical rule run on the 15th, purely because of WHEN it looks (Hoffstein/Newfound).
That is path-dependent noise, not edge, and it inflates both backtest Sharpe variance and
realized turnover. We neutralize it by running an ENSEMBLE of identical sub-strategies
that differ only in their month-end phase offset (0, 5, 10, 15 trading days within the
21-day cycle) and averaging their target-weight matrices. The blended book is the average
of four "tranches," so on any given day only ~1/4 of capital can possibly rotate ->
turnover is smoothed by ~4x and no single arbitrary rebalance date dominates the result.
A small no-trade band on the final blended weights further damps churn.

Variable net exposure
----------------------
Net exposure floats in [0, 1]: fully risk-on when breadth is clean, fully defensive (or
cash) when all canaries are bad. We therefore set ``SPEC.gross_leverage = None`` so the
engine does NOT renormalize the book to fully-invested — the cash fraction IS the signal.

Benchmarks & falsification
--------------------------
Judged vs (a) static 60/40 SPY/TLT and (b) buy-and-hold SPY, on BOTH Sharpe AND max
drawdown. The strategy FAILS if:
* It does not cut max drawdown materially vs buy-and-hold SPY — crash protection is its
  whole reason to exist; if it draws down like the index, the breadth gate is useless.
* Its net-of-cost Sharpe does not beat 60/40 — if a static, zero-turnover mix wins, the
  tactical machinery (and its turnover) is not earning its keep.
* The edge collapses when the ensemble is reduced to a single offset (i.e. results are
  pure timing luck), or when the defensive "positive-momentum-only" rule is removed
  (i.e. it was just levered bond beta).
* Turnover/costs erase the risk-adjusted edge.

Data limitations
----------------
Price-only (yfinance adjusted closes, cached). Cash leg modeled at 0% (conservative; a
real T-bill yield in defensive regimes would only help). Only the 7 named ETFs receive
weight; all other default-universe names are held flat at 0. Missing/NaN tickers at a
date are skipped gracefully (dropped from that date's selection).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from finance_agent.strategy import StrategySpec

OFFENSIVE = ["SPY", "QQQ", "IWM", "XLK"]
DEFENSIVE = ["TLT", "GLD", "HYG"]
CANARY = ["SPY", "HYG", "IWM"]

SPEC = StrategySpec(
    id="xasset_defensive_breadth",
    thesis=(
        "Cross-asset defensive asset allocation (DAA): each month score every asset with a "
        "13612W average-momentum (front-weighted 1/3/6/12-month returns). A canary breadth "
        "gate (SPY, HYG, IWM) sets the cash fraction = share of canaries with non-positive "
        "momentum, de-risking before the held asset confirms a downtrend. The risk-on book "
        "holds the top-2 offensive equity ETFs (SPY/QQQ/IWM/XLK); the defensive book holds "
        "the top defensive asset (TLT/GLD/HYG) only if its own momentum is positive, else "
        "cash — avoiding the 2022 forced-long-bonds trap. Net exposure floats in [0,1]. "
        "Crucially, an ensemble across staggered month-end rebalance offsets (0/5/10/15) is "
        "averaged to neutralize rebalance timing luck and smooth turnover by ~4x."
    ),
    taxonomy=["cross_asset"],
    feature_families=["price"],
    universe="default",
    params={
        "lookbacks": (21, 63, 126, 252),
        "weights_13612w": (12.0, 4.0, 2.0, 1.0),
        "rebalance": 21,
        "offsets": (0, 5, 10, 15),
        "n_offensive": 2,
        "n_defensive": 1,
        "band": 0.05,
    },
    author="quant-researcher",
    references=[
        "Keller & Keuning (2018), Breadth Momentum and the Canary Universe: "
        "Defensive Asset Allocation (DAA), SSRN 3212862",
        "Hoffstein / Newfound Research, Rebalance Timing Luck & Portfolio Fragility",
        "Antonacci (2014), Dual Momentum Investing (GEM)",
    ],
    gross_leverage=None,  # variable net exposure (cash<->risk) — do NOT renormalize
)


def _score_13612w(
    prices: pd.DataFrame,
    lookbacks: tuple[int, ...],
    weights_13612w: tuple[float, ...],
) -> pd.DataFrame:
    """13612W average-momentum score per (date, ticker). Uses only trailing prices.

    score = sum_i w_i * (P0 / P_lookback_i - 1), with default
    w = (12, 4, 2, 1) over lookbacks (21, 63, 126, 252) trading days.
    """
    score = pd.DataFrame(0.0, index=prices.index, columns=prices.columns)
    for lb, w in zip(lookbacks, weights_13612w):
        # P0 / P(t-lb) - 1 ; .shift(lb) pulls a STRICTLY PAST price (no look-ahead).
        ret = prices / prices.shift(lb) - 1.0
        score = score.add(w * ret, fill_value=np.nan)
    # Rows without enough history (any lookback NaN) stay NaN -> treated as "no signal".
    return score


def _weights_for_offset(
    prices: pd.DataFrame,
    score: pd.DataFrame,
    rebal_dates: pd.DatetimeIndex,
    n_offensive: int,
    n_defensive: int,
) -> pd.DataFrame:
    """Build a target-weight matrix for ONE rebalance phase, held forward between dates."""
    cols = prices.columns
    w = pd.DataFrame(np.nan, index=prices.index, columns=cols)

    for dt in rebal_dates:
        s = score.loc[dt]
        px = prices.loc[dt]
        row = pd.Series(0.0, index=cols)

        # Available = has a finite score AND a finite price at this date.
        def avail(names: list[str]) -> list[str]:
            return [a for a in names if a in s.index and np.isfinite(s.get(a, np.nan))
                    and a in px.index and np.isfinite(px.get(a, np.nan))]

        canary = avail(CANARY)
        offensive = avail(OFFENSIVE)
        defensive = avail(DEFENSIVE)

        # Need at least one canary to form a breadth read; else stay in cash this date.
        if not canary:
            w.loc[dt] = row
            continue

        n_bad = sum(1 for c in canary if s[c] <= 0)
        cash_fraction = n_bad / len(canary)
        risk_fraction = 1.0 - cash_fraction

        # --- Offensive sleeve: top-N by score, equal weight, scaled by risk_fraction. ---
        if risk_fraction > 0 and offensive:
            top = s[offensive].sort_values(ascending=False).index[:n_offensive]
            top = list(top)
            if top:
                each = risk_fraction / len(top)
                for a in top:
                    row[a] += each

        # --- Defensive sleeve: top-N defensive with POSITIVE score only; scaled by cash. ---
        if cash_fraction > 0 and defensive:
            pos_def = [a for a in defensive if s[a] > 0]
            if pos_def:
                top_d = s[pos_def].sort_values(ascending=False).index[:n_defensive]
                top_d = list(top_d)
                each = cash_fraction / len(top_d)
                for a in top_d:
                    row[a] += each
            # else: no positive defensive -> leave that capital in cash (row stays 0).

        w.loc[dt] = row

    # Hold each monthly decision forward; pre-warmup stays NaN.
    return w.ffill()


def generate_weights(
    prices: pd.DataFrame,
    lookbacks: tuple[int, ...] = (21, 63, 126, 252),
    weights_13612w: tuple[float, ...] = (12.0, 4.0, 2.0, 1.0),
    rebalance: int = 21,
    offsets: tuple[int, ...] = (0, 5, 10, 15),
    n_offensive: int = 2,
    n_defensive: int = 1,
    band: float = 0.05,
) -> pd.DataFrame:
    """Return target weights (dates x tickers) for the defensive-breadth rotation.

    Only past data is used at each rebalance: the 13612W score at date t is formed from
    ``prices.shift(lb)`` (strictly past) and P0 = the date-t close; the engine adds the
    1-day execution lag. Weights are carried forward (ffill) between monthly rebalances.

    The returned book is the AVERAGE of ``len(offsets)`` identical sub-strategies that
    differ only in their month-end phase offset within the ``rebalance``-day cycle — the
    timing-luck guard. A no-trade ``band`` on the blended weights damps residual churn.
    """
    prices = prices.astype(float)
    score = _score_13612w(prices, lookbacks, weights_13612w)

    n = len(prices.index)
    members = []
    for off in offsets:
        # Rebalance dates for this phase: every ``rebalance`` rows starting at ``off``.
        idx_positions = range(off, n, rebalance)
        rebal_dates = prices.index[list(idx_positions)]
        members.append(
            _weights_for_offset(
                prices, score, rebal_dates, n_offensive, n_defensive
            )
        )

    # Ensemble average of the target-weight matrices (NaN before each member warms up).
    blended = sum(m.fillna(0.0) for m in members) / float(len(members))
    blended = blended.fillna(0.0)

    # Zero out anything that isn't one of the 7 named ETFs (defensive against stray cols).
    named = OFFENSIVE + DEFENSIVE
    keep = [c for c in blended.columns if c in named]
    final = pd.DataFrame(0.0, index=prices.index, columns=prices.columns)
    final[keep] = blended[keep]

    # --- No-trade band on the blended book: only commit a new row if it moved enough. ---
    held = None
    out = pd.DataFrame(0.0, index=prices.index, columns=prices.columns)
    for dt in final.index:
        target = final.loc[dt]
        if held is None:
            held = target.copy()
        elif float((target - held).abs().sum()) >= band:
            held = target.copy()
        out.loc[dt] = held
    return out
