# Cycle 9 Report — Gross-profitability equity sleeve (first fundamentals strategy)

**Date:** 2026-06-11 · **Build:** Opus on the new EDGAR point-in-time connector · 5 bps · lag 1 day

> **Research artifact — not investment advice.**

## Executive summary
Phase 2 of the moat program: the first strategy to use **real fundamentals** — gross
profitability (Novy-Marx), built point-in-time-correctly on the EDGAR connector (cycle-8
moat). **Verdict: REJECTED as a sleeve** — the long/short factor is dead and a filing-shuffle
placebo confirms it carries no information *in this universe*. But the **point-in-time
plumbing is verified leak-free**, and the cycle pinpoints the real blocker: our **ticker list
is survivor-biased** (today's large-caps), so fundamental factors can't be tested fairly until
we have a **point-in-time constituent universe**.

## Result (2010+, 5 bps, monthly)
| Sleeve | Ann ret | Sharpe | t-stat | MaxDD | Turnover |
|---|---|---|---|---|---|
| **GP long/short** | **−1.0%** | **−0.12** | −0.52 | −39% | 0.024 |
| GP long-only (top tercile) | 20.9% | 1.12 | 4.95 | −31% | 0.025 |
| Equal-weight universe | 19.9% | 1.18 | 5.62 | −31% | 0.000 |
| Buy-hold SPY | 14.0% | 0.85 | 3.95 | −34% | 0.000 |

- **L/S is flat-to-negative and insignificant.** The **filing-shuffle placebo** (500 seeds,
  break the value→company link) puts the real factor at the **49th percentile** (p=0.51) — it
  is statistically indistinguishable from random. No extractable GP premium here.
- **The long-only leg's strength is survivorship, not the factor** — it loses to equal-weight
  of the same 23 names. You can't lose owning today's hand-picked survivor large-caps.
- **Look-ahead: CLEAN.** As-of equality held (0 mismatches; 2,129 future filings correctly
  excluded); delaying availability +90 days did *not* improve returns (−1.0% → −3.4%). The
  EDGAR connector + `point_in_time_asof` guard are demonstrably leak-free.

## What this cycle is genuinely worth
1. **Validated point-in-time fundamentals plumbing** end-to-end (the moat foundation works).
2. **A template** for honestly stress-testing a fundamentals factor (filing-shuffle placebo +
   as-of look-ahead proof).
3. **A crisp diagnosis of the binding constraint:** the EDGAR *data* is point-in-time, but our
   *universe selection* is not. Survivorship in the ticker list is now the #1 thing to fix —
   not the data.

## Next step (clear now): point-in-time constituent universe
Build/obtain a **historical index-membership list** (e.g. S&P 500 constituents as-of each
date, free-ish from Wikipedia change logs / public datasets) + delisting handling, so
cross-sectional fundamental factors are tested on the names that *actually existed then*,
not today's winners. Then re-test gross profitability (and value/quality) on a wide,
point-in-time universe. Until then, fundamental-factor results are not trustworthy.

## Standing recommendation (unchanged)
`voltarget_spy` remains the only validated strategy; the risk-managed portfolio (Pivot B,
drawdown control) is the current usable product.

### TL;DR
- First fundamentals sleeve (gross profitability, PIT-correct) — **REJECTED**; L/S dead, placebo p=0.51.
- Long-only "strength" is survivorship (loses to equal-weight). Look-ahead verified clean.
- Real blocker identified: need a **point-in-time constituent universe** to test fundamental factors fairly.
