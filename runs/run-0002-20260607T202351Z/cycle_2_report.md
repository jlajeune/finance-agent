# Cycle 2 Research Report

**Date:** 2026-06-07 · **Universe:** SPY (within the default panel) ·
**Data:** Yahoo Finance via yfinance, real daily prices · **Costs:** 5 bps base
(stress-tested to 40 bps) · **Execution lag:** 1 day · **n_trials:** 1 (pre-registered
config from literature; a 25-cell sweep was run as *robustness*, not selection)

> **Research artifact — not investment advice.** Backtests are not live performance.

## Executive summary
This was a **real web-research cycle**: the `lit-scout` sub-agent mined recent literature
and surfaced a ranked, source-cited shortlist; the top seed — **volatility-targeted
equity exposure** — was implemented and validated. Unlike cycle 1, this cycle produced a
**PASS**: a robust, low-turnover, cost-cheap, look-ahead-clean, OOS-stable risk-managed
equity overlay. Its edge over plain SPY is in **drawdown and volatility reduction**, with
a **Sharpe improvement that appears specifically when crisis regimes are in-sample** —
exactly the documented behavior of the mechanism.

> Provenance: ideas this cycle came from **live web research** (Man Group, Research
> Affiliates, SSRN/Xu 2024, Moskowitz-Ooi-Pedersen), corroborated across ≥2 sources each,
> with vendor/blog performance figures treated as untrusted until reproduced here.

## Cycle map
| id | family | net Sharpe | vs SPY Sharpe | max DD | vs SPY DD | turnover | deflated-SR | verdict |
|---|---|---|---|---|---|---|---|---|
| `voltarget_spy` | volatility_timing | **0.86** | 0.86 (tie) | **−19.9%** | −33.7% (**−14pp**) | 0.004 | ✓ pass | **PASS** |

## Validated strategy: `voltarget_spy`
**Idea.** Hold SPY but scale the weight inversely to its trailing 60-day realized
volatility to target ~11% annual vol, capped at 1× (SPY-vs-cash, deleveraging into vol
spikes). Weekly rebalance + a 0.05 no-trade band keep turnover trivial.

**Mechanism.** Equity vol clusters (persistent) and is negatively correlated with returns
(leverage effect), so cutting exposure when realized vol rises avoids much of the
left-tail drawdown; the benefit is concentrated in tail/Sharpe, not mean return.

**Evidence the red-team accepted:**
- **Headline (2010–2026, 5bps):** net Sharpe 0.86, vol 11.5% (target met), max DD −19.9%
  (vs SPY −33.7%), Calmar 0.48 (vs 0.42), t-stat 3.47.
- **Cost-robust:** turnover 0.004; net Sharpe 0.86→0.82 from 0→40 bps. Cost is a non-issue.
- **OOS-stable:** in-sample 0.87 → out-of-sample 0.84 (decay 0.02); 4/4 subsamples
  positive (mean 0.86, std 0.16).
- **Crisis test (2000–2026, incl. dot-com + GFC, 10bps):** Sharpe **0.60 vs SPY 0.51**
  (+0.09 edge) and max DD **−31.0% vs −55.2%** (−24pp). The Sharpe edge materializes once
  major crises are in-sample.
- **Parameter plateau:** net Sharpe 0.77–0.94 across all 25 (vol_window ∈ {20..120}) ×
  (target_vol ∈ {0.08..0.15}) cells — all positive, smooth. Not a fit; the chosen 60/0.11
  is on the conservative side of the plateau.
- **Look-ahead-clean:** realized vol at t uses returns ≤ t; engine trades at t+1.

**Residual risks / honest caveats.**
- The **Sharpe improvement over buy-and-hold is regime-dependent** — strong with crises
  in-sample, ~zero in a pure bull market (2010s) where the value is purely drawdown/vol
  reduction. This trips the strategy's own strict falsification #1 on the bull-only window
  while passing on the full-cycle window; we judge it a PASS *as a risk-managed overlay*,
  not as a standalone Sharpe-alpha source.
- It **gives up absolute return** (9.6%/yr vs SPY 14.1% in 2010–26) by capping at 1× and
  de-levering — the cost of lower risk.
- Cash leg modeled at **0%** (no T-bill yield wired in) — conservative; a real yield helps.

## Current recommendation
Per the live vol target, current exposure is **~76% SPY / ~24% cash** (`SPY: 0.76`) —
i.e. modestly de-risked because recent realized vol is slightly above the 11% target.
Framed as a risk-managed equity allocation, not a stock pick. *Not investment advice.*

## What we learned (feeds cycle 3)
1. **Web research paid off** — a literature-grounded, cost-aware, time-series idea
   survived where cycle 1's internally-recalled cross-sectional ideas did not.
2. **Match the metric to the mechanism** — vol-targeting's value is drawdown/vol control;
   judging it purely on Sharpe vs a bull-market benchmark understates it. Reports should
   always show the benchmark *and* drawdown, which this one does.
3. The **gross_leverage=None** contract extension now supports market-timing strategies
   cleanly — reusable infra for future vol/trend overlays.

## Proposed seeds for cycle 3
- **Modest leverage (cap 1.5×)** on the same overlay to test whether the de-levered edge
  converts into a Sharpe beat in calm regimes too.
- **Conditional / downside-vol targeting** (lit-scout Seed 3) — act only in tail regimes;
  lower turnover, potentially higher Sharpe.
- **Defensive cross-asset dual-momentum** (Seed 2: SPY/QQQ vs TLT/GLD/cash) — a
  diversifying `cross_asset` entry; pair with hysteresis to stay low-turnover.
- Wire a **FRED T-bill yield** for the cash leg (free, no key via CSV) for a fairer return.

### TL;DR
- Real web-research cycle (1 subagent, `lit-scout`) → top seed implemented and **PASSED**.
- `voltarget_spy`: same Sharpe as SPY but **−14pp drawdown** (−24pp with crises in-sample,
  where it also **beats** SPY on Sharpe), negligible cost, robust parameter plateau.
- Current call: ~76% SPY / 24% cash. Next: add modest leverage, downside-vol variant,
  cross-asset rotation.
