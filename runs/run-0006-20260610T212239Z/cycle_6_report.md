# Cycle 6 Report — Cross-domain ideation (Fable) + build (Opus)

**Date:** 2026-06-10 · **Model split:** Fable for ideation & conclusions, Opus for build &
adversarial execution · **Data:** Yahoo Finance (yfinance) · **Costs:** 5 bps · lag 1 day

> **Research artifact — not investment advice.**

## Executive summary
This cycle exercised a deliberate **model split**: two **Fable** cross-domain research
agents (physics + biology) produced a ranked, durable idea **backlog**
(`research/strategy_backlog.md`, ~10 sourced ideas), and **Opus** built and self-vetted the
top pick, **P1 — the Zumbach time-reversal volatility overlay**. The build is a clean,
honest **REJECT**: its predictive content is the ordinary leverage effect, not the
time-irreversible "melt-up predicts vol" Zumbach effect, and it fails to beat the incumbent
`voltarget_spy` on drawdown. No new validated strategy; the durable win is the backlog.

## What was produced
- **`research/strategy_backlog.md`** — a ranked queue across physics (Zumbach, multifractal
  log-vol, Kuramoto phase-sync, Omori re-entry, fluctuation-theorem temperature) and biology
  (foraging diffusion-exponent, cross-sectional diversity, Lotka-Volterra rotation, neuronal
  avalanche). Each entry: build sketch, must-beat-VIX bar, risk+guard, sources, status.
- **`strategies/zumbach_vol_overlay.py`** (P1) — built, tested, rejected.

## The build: `zumbach_vol_overlay` — VERDICT: REJECT
**Idea.** 2-parameter upgrade to the validated `voltarget_spy`: forecast variance
`σ²̂ = a·RV22 + b·Z`, where `Z` = squared causal EMA-trend (half-life 15d) — the Zumbach
claim that a sustained *signed trend* forecasts a future vol expansion beyond the level of
recent realized vol. Size SPY by `target_vol/√σ²̂`. NNLS coefficients fit by expanding-window
walk-forward (look-ahead-safe, causal EMA, engine adds the lag).

**Two findings, both failing:**
1. **Does not beat the incumbent (Sharpe AND drawdown).** Net, 5 bps:

   | strategy | Sharpe | maxDD | turnover |
   |---|---|---|---|
   | Zumbach overlay (2008-start) | 0.80 | −23.7% | 0.0100 |
   | `voltarget_spy` (incumbent) | 0.75 | **−21.1%** | **0.0039** |
   | VIX-level sizer | 0.78 | −19.4% | 0.0108 |
   | buy-hold SPY | 0.64 | −51.5% | 0 |

   Zumbach edges Sharpe (+0.06) but **worsens drawdown** and runs 2.6× the turnover →
   fails the "Sharpe *and* drawdown" bar. Standardized battery from 2005 (incl. GFC):
   Sharpe 0.79, maxDD −29.5%, OOS decay −0.15.

2. **It's the leverage effect, not the Zumbach effect.** Signed decomposition
   `σ² = a·RV22 + b_up·Z_up + b_dn·Z_dn` with **Newey-West HAC** standard errors (the
   honest-SE discipline from cycle 5):
   - `b_up` (up-trends): t = **−0.81** (insignificant, wrong sign)
   - `b_dn` (down-trends): t = **+4.60** (strongly significant)

   All predictive content comes from *down*-trends. The symmetric "melt-up predicts vol"
   channel adds **−0.0009 Sharpe** over a down-trend-only baseline. The walk-forward NNLS's
   positive `b_up` was a ≥0-constraint artifact, not a real effect.

## What we learned
- **The ideation engine (Fable) is generating genuinely novel, well-sourced ideas**, and the
  **Opus execution + adversarial layer is honestly killing** the ones that don't beat simple
  baselines. Two cross-domain builds now — **Absorption Ratio** (cycle 5) and **Zumbach**
  (cycle 6) — died specifically on the **"add content beyond VIX / use honest HAC standard
  errors"** discipline. That guard is doing exactly its job: catching ideas whose apparent
  edge is either VIX-redundant or an overlapping-/constrained-estimator artifact.
- **Negative results are cheap and informative here** because every idea is pre-registered
  against the incumbent and a VIX baseline.

## Standing recommendation (unchanged)
Nothing validated this cycle. The only validated strategy remains cycle-2's **`voltarget_spy`**
(~76% SPY / 24% cash). Not investment advice; survivorship/selection bias present; backtests
are not live performance.

## Next steps (work down the backlog)
1. **B1 — foraging diffusion-exponent** (Lévy/Brownian Hurst): best *new-axis* idea
   (price-path memory), prices-only, uncorrelated with the vol-forecast cluster.
2. **P2 — multifractal log-vol forecaster** (adopt only if ΔSharpe ≥ 0.05 vs EWMA vol-target).
3. **B2 — cross-sectional diversity** (orthogonalize-vs-VIX gate before any backtest).

### TL;DR
- Model split worked: Fable ideated a 10-idea cross-domain backlog; Opus built + rejected P1.
- `zumbach_vol_overlay` REJECTED — it's the leverage effect (b_up t=−0.81, b_dn t=+4.60), and
  it worsens drawdown vs the incumbent.
- The backlog is the durable asset (8 ideas still queued); `voltarget_spy` remains the only winner.
