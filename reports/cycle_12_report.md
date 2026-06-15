# Cycle 12 Report — Multi-factor composite on the point-in-time universe

**Date:** 2026-06-15 · **Build:** Opus · 2010+ (198 months) · 5 bps · point-in-time EDGAR +
S&P 500 membership · the cycle-11 "combine weak-but-real factors" thesis

> **Research artifact — not investment advice.**

## Executive summary
Cycle 11 showed value is real-but-sub-threshold and suggested **combining** signal-specific
factors. We tested that directly: an equal-z composite of **value + quality + low-vol +
momentum** on the honest universe. **The thesis is rejected — combining made it worse.**
Three of the four legs have no signal on this free large-cap PIT set, so equal-weighting
*dilutes* value rather than diversifying it. This closes out the **free-data equity-factor
avenue**: no tradable cross-sectional edge survives here, individually or combined.

## The decisive test: composite vs its parts
| Book (L/S) | Sharpe | monthly t |
|---|---|---|
| **Composite** | **−0.22** | **−1.00** |
| value | 0.23 | 0.95 |
| quality (ROE) | −0.03 | −0.14 |
| low-vol | −0.40 | −1.74 |
| momentum (12-1) | −0.06 | −0.33 |

Composite beats its best single factor? **No** (−0.22 < value's 0.23, on either Sharpe or |t|).
The diversification thesis fails because only one leg (value) carries signal; the other three
are flat-to-negative on the free PIT large-cap set, so the equal-weight blend drags value down.

**Headline / baselines:** composite long-only tercile Sharpe 0.84 (t=4.05) edges equal-weight-PIT
(0.82) but trails SPY (0.86), and long-only-minus-EW is negative (t=−0.93) — no edge over the
universe even on the long leg. **Placebo p=0.11** (89th pctile of 200 shuffles) — not
signal-specific. **Drop rate 4.2%** (best yet; 678/707 have TTM earnings).

## What this milestone establishes (honest)
Across cycles 9–12, on **free, large-cap, XBRL-era (post-2009) point-in-time data**, the
cross-sectional fundamental/price factors we can build do **not** produce a tradable edge —
gross profitability (dead, placebo-fail), value (real but sub-threshold), and now their
composite (negative). This is consistent with market efficiency on the most-mined data, and
it's now a *trustworthy* conclusion (survivorship-controlled, placebo-tested, honest SEs) —
not a survivorship illusion. The free-data equity-factor program has reached its honest end.

## Where the remaining leverage is
1. **The text moat we built but never tested.** `edgar_text.py` (risk-factor change, tone) is
   genuinely **less-crowded** data — the untested frontier. A text-derived factor is the most
   novel next experiment.
2. **Paid breadth/delisting + small-caps** — factors live in the parts of the market free data
   can't reach (small-caps, complete delisting returns). Quantified cost: the residual gap.
3. **Accept the validated product:** the **risk-managed portfolio** (drawdown control) remains
   the genuinely useful, honest deliverable; equity-factor alpha is not on free data.

## Standing recommendation (unchanged)
`voltarget_spy` is the only validated standalone strategy; the risk-managed portfolio is the
usable product. No equity-factor sleeve survives — and that is now a well-evidenced truth.

### TL;DR
- Multi-factor composite (value+quality+lowvol+momentum) on the honest universe: **rejected** —
  combining made it *worse* (L/S −0.22) because only value carries signal.
- Closes the free-data equity-factor avenue: no tradable cross-sectional edge here, alone or combined.
- Frontier now: the **untested text moat**, paid breadth data, or accept the risk-managed portfolio.
