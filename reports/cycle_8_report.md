# Cycle 8 Report — voltarget_pathmemory (first novel-combination build)

**Date:** 2026-06-10 · **Build + red-team:** Opus · **Data:** yfinance · 5 bps · lag 1 day

> **Research artifact — not investment advice.**

## Executive summary
First idea through the upgraded **novelty-first** process: a genuinely novel combination —
a gentle, bounded **DFA-Hurst path-memory tilt `g(H_z)` ON the validated vol-target sizing**
(`prior_art: extends`). The build cleared its pre-registered bar (beat the incumbent
`voltarget_spy` on Sharpe AND drawdown), but the **red-team decisively REJECTED it.** The
modest edge is statistical noise, cost-fragile, and — the decisive finding — **not specific
to the Hurst signal**: a persistence-matched random tilt of the same turnover reproduces it.
`voltarget_spy` remains the **only** validated strategy.

## The combination
Base = incumbent inverse-vol SPY sizing. Tilt = `g(H_z) = clip(1 + k·tanh(H_z), 0.6, 1.1)`
where H_z is the cycle-7 DFA-Hurst path-memory z-score. Trim modestly in choppy regimes,
never to cash (fixing B1's over-de-risk). Frozen params, look-ahead-safe, gross_leverage=None.

## Build result (looked like a modest PASS)
Full sample (2005+, 5 bps): overlay Sharpe **0.760** / maxDD **−23.2%** vs incumbent **0.741
/ −26.2%** — beat on both, 9-cell plateau, OOS decay −0.05, deflated-Sharpe (absolute) passed.

## Red-team verdict: REJECT (evidence)
1. **Not Hurst-specific (placebo — decisive).** Swapping H_z for persistence-matched random
   signals (phase-shuffled, AR(1) matched to H_z's 0.89 autocorr), keeping identical g()/band/
   turnover: the real overlay sits at only the ~88–95th percentile of the random-tilt
   distribution (empirical **p ≈ 0.10–0.12**); 5/40 phase-shuffled and 2/40 AR(1) surrogates
   match-or-beat it. The edge is "a slow, bounded, occasionally-de-risking tilt of this
   turnover," not path memory. (White noise *hurts* — so persistence matters, but DFA-Hurst
   specifically does not.)
2. **Sharpe edge is noise.** Daily difference (overlay − incumbent) has a **negative** mean
   (ann. difference-Sharpe **−0.22**) — the overlay earns *less* return (7.80% vs 8.15%); its
   whole Sharpe "advantage" is lower vol. Paired t = −1.02, Newey-West t ≈ −1.1; block-bootstrap
   95% CI for the Sharpe gap ≈ [−0.05, +0.08], P(edge ≤ 0) ≈ 0.30.
3. **Cost-fragile.** Sharpe-edge break-even ≈ **12.5 bps**; at realistic 15–20 bps the overlay
   **loses to its own incumbent** (3.8× turnover is the cause). The drawdown edge (~+3 pp)
   does survive costs — the one durable feature.
4. **Drawdown edge is crisis-driven & redundant.** Concentrated in 2008/2020 vol spikes where
   the base vol-target already acts; 2022 (the slow grind a path-memory tilt should catch) adds
   nothing. Dropping 2020 flips the Sharpe edge negative.
5. **Honest deflated-Sharpe:** the right object is the *difference* Sharpe, which is negative —
   nothing to deflate. The absolute DSR the build reported just reflects that vol-target SPY is
   already ~0.74.
- **Look-ahead: clean** (price-shock test: weights before the shock bit-identical).

## The meta-lesson (and a process upgrade)
H_z **passed** the cycle-7 "beyond-VIX" predictive test (monthly t≈2–2.9) yet **failed** to
yield a tradable edge here. A statistically-orthogonal signal is *not* automatically a tradable
one — the **persistence-matched placebo control** caught what the beyond-VIX regression missed.
We are **downgrading the H_z claim** from "validated tradable signal" to "statistically
beyond-VIX, but not shown to beat a matched-persistence random tilt." **Process change:** the
persistence-matched placebo + difference-series significance test are now standard red-team
checks (added to `.claude/agents/red-team-quant.md`).

## Standing recommendation (unchanged)
`voltarget_spy` (~76% SPY / 24% cash) remains the **only** validated strategy. Not investment
advice; survivorship/selection bias present; backtests are not live performance.

## Next steps
- If salvaging the path-memory tail feature: reframe as a **drawdown overlay** (not a Sharpe
  claim), slash turnover (tilt the target pre-band / monthly), and require it to beat a
  **matched-persistence placebo OOS** — else drop the DFA machinery for a simpler trend/vol
  filter.
- Otherwise continue the backlog (B2 cross-sectional diversity, P2 multifractal log-vol),
  now under the stricter placebo bar.

### TL;DR
- First novel-combination build (path-memory × vol-target) — **REJECTED** by red-team.
- Edge is noise, cost-fragile, and indistinguishable from a random-turnover tilt (placebo p≈0.1).
- New standard bar: beat a matched-persistence placebo. `voltarget_spy` still the only winner.
