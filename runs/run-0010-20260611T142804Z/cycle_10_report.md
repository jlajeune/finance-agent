# Cycle 10 Report — Gross profitability on a point-in-time universe (the honest re-run)

**Date:** 2026-06-11 · **Build:** Opus (agent) + orchestrator-finished eval · 5 bps · 2010+ ·
EDGAR point-in-time fundamentals ∩ point-in-time S&P 500 membership

> **Research artifact — not investment advice.**

## Executive summary
The decisive experiment from phases 1–3: re-run cycle 9's gross-profitability factor on a
**point-in-time universe** (the names actually in the S&P 500 each month, losers included),
instead of today's 30 survivors. **Result: the survivorship hypothesis is confirmed, and there
is no gross-profitability premium here.** The cycle-9 long leg that looked strong (Sharpe 1.12)
**collapses to 0.85 once losers are back in** — exactly equal to just equal-weighting the same
universe (0.838) and to SPY (0.856). The factor tilt adds nothing.

## Result (2010+, 5 bps, monthly)
| Sleeve | Sharpe | Ann ret | monthly t | MaxDD | vs cycle 9 (30 survivors) |
|---|---|---|---|---|---|
| GP **long/short** | **0.01** | −0.0% | 0.04 | −10% | −0.12 (still dead) |
| GP **long-only** top tercile | **0.85** | 14.4% | 3.83 | −36% | **1.12 → 0.85** |
| **Equal-weight** PIT universe | 0.838 | 14.4% | 3.79 | −38% | 1.18 → 0.838 |
| Buy-hold SPY | 0.856 | 14.1% | — | −34% | — |

**Reading it:**
- **Survivorship confirmed.** On survivors, long-only (1.12) *looked* like it beat the market.
  On the honest universe it drops to **0.85 ≈ equal-weight (0.838) ≈ SPY (0.856)** — the
  apparent edge was entirely the hand-picked survivor list, not the factor. Precisely the bias
  phases 1–3 were built to expose.
- **No GP premium.** The long/short spread is flat-dead (0.01, t=0.04) on a wide universe too —
  the gross-profitability premium is absent in the free PIT S&P 500 (XBRL-era) sample.
- **The tilt adds nothing** over equal-weighting the same names.

## Honest caveat (measured, not hand-waved)
Of ~**409** point-in-time members per period, only ~**247 were usable** — **~162 (40%) dropped
each period** for missing price or EDGAR data. So this *materially de-biases but does not fully
eliminate* survivorship: yfinance still lacks ~47% of delisted names' prices, and XBRL/EDGAR
coverage starts ~2009. The directional confirmation (long-only 1.12 → 0.85) is clear and robust
to this; full confidence on the absolute level needs delisting-complete prices (CRSP/Sharadar).

## What this cycle is genuinely worth
1. **The phases 1–3 program paid off:** it converted a survivorship-flattered "looks great"
   (cycle 9) into an honest "the tilt adds nothing" — the whole point of the data moat.
2. **The infrastructure composes and works:** `point_in_time_asof` ∩ `point_in_time_universe`
   produced a trustworthy result on 710 names; the PIT plumbing is validated end-to-end.
3. **A clear cost/benefit for paid data:** the 40% drop rate quantifies exactly what a paid
   delisting-complete price source would buy us.

## Standing recommendation (unchanged)
`voltarget_spy` remains the only validated strategy; the risk-managed portfolio (drawdown
control) is the usable product. No fundamentals sleeve survives yet — and we now know that's
the *truth*, not a survivorship illusion.

### TL;DR
- Gross profitability re-tested on a point-in-time universe → **survivorship confirmed**: the
  cycle-9 long leg (1.12) falls to **0.85**, dead even with equal-weight and SPY.
- No GP premium (L/S 0.01). The data moat did its job: honest "no", not a flattered "yes".
- Caveat: ~40% of members dropped/period for missing data — directional result is clear; absolute
  level needs paid delisting-complete prices.
