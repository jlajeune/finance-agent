# Cycle 5 Report — Absorption Ratio (cross-domain build #1)

**Date:** 2026-06-08 · **Type:** cross-domain implementation + adversarial vetting ·
**Idea source:** `research/cross_domain_ideation.md` (convergent #1 of two parallel
research agents) · **Data:** yfinance, 9 sector SPDRs + SPY/VIX, signal live 2004→2026 ·
**Costs:** 5 bps · **Execution lag:** 1 day

> **Research artifact — not investment advice.**

## The idea (+ prior art)
The **Absorption Ratio** (Kritzman, Li, Page & Rigobon, *JPM* 2011): PCA the trailing
500-day correlation matrix of the 9 classic sector SPDRs; AR = share of variance in the
top-2 of 9 eigenvalues = how tightly *coupled* (fragile) the market is. Roots in
econophysics random-matrix theory (Laloux et al. 1999; Plerou et al. 1999–2002). Trade the
standardized coupling shift dAR = (15d − 252d mean)/252d std: dAR > +1σ → de-risk SPY→cash,
< −1σ → full SPY, else 50%. Frozen parameters (not fit). The premise: coupling rises
*before* crashes while prices still climb — a fragility axis orthogonal to trend/vol/VRP.

## Result: REJECT
**Standardized battery (2004→2026):** net Sharpe **0.41**, max DD **−23.0%**, turnover
0.005, OOS decay −0.32 (OOS > IS), 4/4 subsamples positive. Look-ahead-clean, ETF-only
(no survivorship), genuinely low-turnover.

**Must-beat-VIX comparison — fails:**
| Timer | Sharpe | max DD |
|---|---|---|
| Absorption Ratio | 0.41–0.45 | **−23.0%** |
| VIX-level timer (same mapping) | 0.48–0.58 | −24.5% |
| Buy-and-hold SPY | 0.65 | −55.2% |
| Static 60/40 | 0.83 | −29.9% |

It cuts SPY's −55% crash to −23% (the fragility mechanism is real) but **loses on Sharpe to
all three benchmarks, including a plain VIX timer** — the frozen binary long/flat mapping
gives up too much upside for the tail it saves.

**The decisive adversarial finding (overlapping-returns t-stat inflation).** The builder
claimed dAR carried independent forward-return content (t = +3.77) beyond VIX. That used
**daily observations of 21-day forward returns** — heavily overlapping, serially correlated,
which inflates OLS t-stats (Hansen-Hodrick). Recomputed honestly:
- **Non-overlapping monthly:** dAR → next-month return **t = +0.46** (with VIX, +0.49). Insignificant.
- **Daily overlapping, Newey-West HAC (L=42):** **t = +1.11** (not +3.77). Insignificant.

The "orthogonal alpha beyond VIX" claim does not survive honest standard errors.

**Salvage tests — none clear the bar.** Combining AR with VIX (de-risk if either elevated)
gives Sharpe 0.345 (< VIX-only 0.48); it improves drawdown (−19.5%) but not risk-adjusted
return. A smooth/vol-targeted mapping was not able to beat the VIX timer either.

## What we learned
1. **The adversarial layer worked:** it caught a 3.4× t-stat inflation from overlapping
   returns — the classic predictive-regression trap. Lesson logged.
2. The **fragility/coupling axis is real for drawdown** (−23% vs −55%) but, at the monthly
   horizon, **redundant with VIX** and carries no significant standalone directional alpha.
3. **Infra idea:** add a HAC / non-overlapping predictive-regression helper to `validation.py`
   so future signal-vs-benchmark claims are stress-tested for overlap automatically.
4. The structure axis may still earn its place as a **drawdown-insurance feature inside a
   regime model** (judged on Calmar/Sortino), not as a standalone directional timer — but
   only if it adds beyond VIX, which here it did not.

## Standing recommendation (unchanged)
Nothing validated this cycle. The only validated strategy remains cycle-2's `voltarget_spy`
(~76% SPY / 24% cash). Not investment advice.
