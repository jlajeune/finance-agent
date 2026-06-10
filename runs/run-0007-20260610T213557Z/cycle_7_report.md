# Cycle 7 Report — Foraging diffusion-exponent (B1) path-memory timer

**Date:** 2026-06-10 · **Build:** Opus · **Data:** yfinance · **Costs:** 5 bps · lag 1 day

> **Research artifact — not investment advice.**

## Executive summary
Built backlog item **B1** — a Lévy/Brownian **path-memory** regime timer: estimate the
generalized Hurst exponent H (via DFA) of SPY returns; H>0.5 = persistent/trending, H<0.5 =
choppy/mean-reverting; gate a 50/200 trend rule by the z-scored regime. **Verdict: REJECT as
a standalone timer — but the signal itself is the most encouraging cross-domain result yet:
it is the FIRST to pass the honest beyond-VIX test.**

## Result
**Must-beat (net, 5 bps, from 2005):**
| strategy | Sharpe | maxDD | turnover |
|---|---|---|---|
| diffusion_regime_timer | 0.57 | **−19.8%** | 0.052 |
| buy-hold SPY | 0.64 | −55.2% | 0 |
| static 60/40 | 0.80 | −29.9% | 0 |
| VIX timer (analogous z-map) | 0.81 | −14.4% | 0.031 |
| plain 50/200 trend (no Hurst gate) | 0.70 | −33.7% | 0.004 |

It **fails Sharpe-and-drawdown vs every baseline** and does not beat the ungated trend rule
on Sharpe — it over-de-risks, trading −19.8% drawdown for too much foregone return.
Standardized battery: Sharpe 0.55, maxDD −19.8%, OOS decay −0.44 (OOS *better* — robust).

**The encouraging part — beyond-VIX, honest standard errors (next-21d SPY return ~ H_z + VIX):**
- Non-overlapping monthly OLS: H_z **t = +2.90** (n=245)
- Overlapping + Newey-West (lag 21): H_z **t = +2.01**
- R²(H_z on VIX level+change) = **0.098**, corr(H_z, VIX) = −0.18

So H_z carries genuine predictive content **independent of VIX** — the exact test that sank
cycle 5's Absorption Ratio (which was VIX-redundant). **Path memory is a real, orthogonal
axis.** Parameter plateau is smooth (window {90,120,150}×threshold {0.4,0.5,0.6}); post-2010
OOS survives and strengthens.

## What we learned
- **First validated orthogonal signal from the cross-domain program.** The problem is
  *monetization*, not information: a binary long/flat map with a 0%-equity choppy state
  throws away too much premium. The right home for H_z is as a **gate/overlay/feature**, not
  a standalone strategy — i.e. pair it with the validated `voltarget_spy`, or with B2
  (cross-sectional diversity), inside a small regime model.
- This is the constructive flip-side of the "beyond-VIX" discipline: it doesn't just kill
  ideas, it certifies when a signal is genuinely new (H_z passed; AR/Zumbach did not).

## Standing recommendation (unchanged)
`voltarget_spy` (~76% SPY / 24% cash) remains the only validated *strategy*. New asset:
the **H_z path-memory signal** is a validated orthogonal *input* for future overlays.

## Next steps
1. **Re-home H_z as an overlay** — e.g. vol-target sizing tilted by regime, or feed H_z +
   diversity (B2) into a 2-feature regime model, judged vs plain `voltarget_spy`.
2. Continue the backlog: **B2 cross-sectional diversity**, **P2 multifractal log-vol**.

### TL;DR
- B1 diffusion-regime timer REJECTED as standalone (Sharpe 0.57, over-de-risks).
- But H_z is the **first cross-domain signal to pass the honest beyond-VIX test** (t≈2–2.9, R²-on-VIX 0.10).
- Re-home it as a gate/overlay; `voltarget_spy` still the only validated strategy.
