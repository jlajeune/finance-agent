# Cycle 11 Report — Value (earnings yield) on the point-in-time universe

**Date:** 2026-06-15 · **Build:** Opus agent (orchestrator-finished eval) · 2010+ · 5 bps ·
EDGAR point-in-time earnings + shares ∩ point-in-time S&P 500 membership

> **Research artifact — not investment advice.**

## Executive summary
Second fundamental factor on the honest universe (after gross profitability, cycle 10):
**earnings-yield value**, via the new `sp500_pit_union` runner path. The result is the most
nuanced so far — the **signal is genuinely real (passes the placebo decisively), but its
tradable magnitude is sub-threshold.** Reject as a standalone sleeve; keep as a *component*
for a multi-factor composite.

## Result (2010+, 5 bps, monthly)
| Sleeve | Sharpe | Ann ret | monthly t |
|---|---|---|---|
| EY **long/short** | 0.23 | 0.7% | 0.95 |
| EY **long-only** top tercile | 0.83 | 15.2% | 3.73 |
| Equal-weight PIT universe | 0.81 | 13.9% | 3.71 |
| Buy-hold SPY | 0.86 | 14.2% | — |
| EY long-only **minus** equal-weight | 0.34 | +1.3% | **1.45** |

**Placebo (200 filing-shuffle seeds):** real L/S Sharpe **0.23 vs shuffled mean −0.49**;
real factor at the **100th percentile, p = 0.0.** Shuffling the earnings-yield values destroys
the result → **the ranking is signal-specific, not turnover.** (Contrast cycle 10's gross
profitability: placebo p=0.51, pure noise.) **Drop rate: 11.5%** of members/period (vs 40% in
cycle 10 — the wide-universe plumbing + better earnings/share coverage helped).

## Interpretation (honest)
- **The value signal is real here** — it's the first fundamental factor to clear the placebo /
  signal-specificity bar on the survivorship-controlled universe. The earnings-yield ranking
  contains information.
- **But it is not a tradable edge on this sample.** The long-only tilt over equal-weight is
  +1.3%/yr at **t=1.45 (below the t>2 bar)**, the L/S spread is insignificant (t=0.95), and
  long-only (0.83) merely matches equal-weight (0.81) and trails SPY (0.86). This is consistent
  with value's well-documented weak 2010s in large-cap US — and our sample (XBRL-era, ~500
  large-caps, 11.5% dropped) lacks the breadth/power small-caps + a longer history would give.
- **Verdict: REJECT as a standalone sleeve; RETAIN as a composite component.** A weak-but-real,
  signal-specific factor is exactly the kind of thing that earns its place *combined* with
  others (quality, low-vol, momentum) in a multi-factor sleeve — not alone.

## What this cycle is worth
1. **The placebo discipline discriminates** — it killed gross profitability (noise) and *passed*
   value (real-but-weak). It's not just a rejection machine; it tells signal from turnover.
2. **The wide-universe harness path works** — `sp500_pit_union` + chunked `get_prices` ran a
   ~700-name PIT factor through cleanly; drop rate fell to 11.5%.

## Standing recommendation (unchanged)
`voltarget_spy` remains the only validated standalone strategy; the risk-managed portfolio
(drawdown control) is the usable product. Value is logged as a candidate **composite component**.

### TL;DR
- Value (earnings yield) on the honest universe: **real signal (placebo p=0.0) but sub-threshold**
  (long-only-minus-EW t=1.45). Reject standalone; keep as a multi-factor composite component.
- First fundamental factor to pass signal-specificity post-survivorship-control; the placebo
  discriminates (killed GP, passed value).
