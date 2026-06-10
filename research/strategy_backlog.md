# Cross-Domain Strategy Backlog (ranked idea queue)

A living, ranked queue of cross-domain strategy ideas surfaced by `lit-scout` research,
so we can work down the list over successive cycles. Each entry: domain, technique, the
edge vs vanilla+VIX, an implementation sketch, the benchmark it must beat, top risk+guard,
and status. **Universal bar (from cycle 5):** must beat buy-hold SPY / static 60-40 / a
VIX-level timer on **Sharpe AND drawdown**, on a parameter plateau, look-ahead-safe, with
a deflated-Sharpe penalty and a *beyond-VIX residual* check using honest non-overlapping /
Newey-West standard errors.

Status legend: `queued` · `building` · `validated` · `rejected`

---

## Already resolved (for context)
- Absorption Ratio (RMT/PCA coupling) — **rejected** (cycle 5): cut drawdown but redundant
  with VIX; orthogonal-alpha claim was an overlapping-returns t-stat artifact.
- `voltarget_spy` (volatility_timing) — **validated** (cycle 2): the only standing winner.
- Prior briefs also shelved: LPPL/Sornette, Hawkes, critical-slowing-down, SIR, permutation/
  transfer entropy, TDA, reservoir computing, HMM/jump models, MST/correlation networks.

---

## BIOLOGY / LIFE-SCIENCES branch (Fable, cycle 6) — full source list in commit

### B1 — Foraging diffusion-exponent regime (Lévy vs Brownian)  · `queued` · TOP PICK
- **Domain/technique:** movement ecology's Lévy-flight foraging hypothesis. Estimate the
  anomalous-diffusion scaling exponent α in MSD(τ)∝τ^α (generalized Hurst H=α/2) on SPY
  returns: H>0.5 super-diffusive/trending ("searching"), H≈0.5 Brownian, H<0.5
  sub-diffusive/choppy mean-reverting.
- **Edge beyond VIX:** a *path-memory* axis, not an amplitude axis — distinguishes
  low-vol-trending from low-vol-choppy, which VIX cannot, and is not a coupling/eigenvalue
  measure (so not auto-redundant like the Absorption Ratio).
- **Build:** SPY log returns; trailing 120d DFA (not R/S — bias trap) → H; trailing-252d
  z-score H_z; frozen mapping H_z>+0.5 ride trend (1.0 if 50d>200d else 0), H_z<−0.5
  de-risk (0–0.5), else 0.5; no-trade band; low turnover. New taxonomy `path_geometry`
  (or `market_state_structural`+`trend_following`).
- **Must beat:** SPY / 60-40 / VIX-timer on Sharpe AND drawdown; H_z must keep a
  significant coefficient on next-month returns controlling for VIX (non-overlapping/HAC).
- **Risk+guard:** Hurst noisy on short windows / estimator snoopable → pre-register DFA,
  one window (120d), one threshold (±0.5); plateau heatmap; deflated-Sharpe; require
  post-2010 OOS survival.
- **Sources:** Sims et al. *J. Animal Ecology* 2012; Mantegna & Stanley truncated-Lévy
  (arXiv cond-mat/9705087); Hurst trend/mean-reversion (Macrosynergy; arXiv 2205.11122).

### B2 — Cross-sectional diversity collapse (Shannon/Simpson evenness)  · `queued`
- **Domain/technique:** ecology diversity-stability. Treat the cross-section of sector/stock
  returns as "species"; compute effective diversity D = exp(Shannon) or 1/Σpᵢ² of variance
  shares. Collapsing D = synchronization/"monoculture" = fragility.
- **Edge beyond VIX & AR:** reads the *shape* of the cross-sectional return distribution
  (evenness/kurtosis), documented to be regime-asymmetric and to predict future vol —
  distinct from eigenvalue concentration (AR) and index vol (VIX).
- **Build:** 9 sector SPDRs ±large-caps; trailing 20–60d variance shares → D → trailing
  z-score; falling D → de-risk; no-trade band; ~monthly turnover. `market_state_structural`
  / `cross_sectional_diversity`.
- **Must beat:** SPY / 60-40 / VIX-timer; **and** D_z must predict beyond VIX *and* beyond
  the Absorption Ratio (prove it isn't AR relabeled).
- **Risk+guard:** mechanically correlated with realized vol → orthogonalize D against
  contemporaneous VIX+RV and trade only the residual; reject early if residual is empty.
- **Sources:** diversity-index theory; cross-sectional dispersion→vol (ScienceDirect
  S0927538X19301830; Wiley J.Forecasting 2023; arXiv 1010.4917).
- **Note:** strongest *pairing* with B1 — together span temporal-memory + cross-sectional
  evenness; natural two-feature regime model our vol-target winner is blind to.

### B3 — Predator-prey capital rotation (Lotka-Volterra phase)  · `queued` · speculative
- **Domain/technique:** LV predator-prey. Risk-on aggregate (SPY/QQQ/IWM/HYG) = prey,
  defensive (TLT/GLD) = predator; use the *phase/lead-lag* of relative momentum (NOT a
  fitted LV ODE) — defensive momentum leading equity momentum = early de-risk.
- **Edge beyond VIX:** rotational *phase* of the risk-on/off cycle, orthogonal to vol level
  and absolute trend.
- **Build:** rolling 60–120d relative-strength of risk-on vs TLT/GLD; phase-plane
  (rel-mom, Δrel-mom); de-risk when defensive lead crosses positive; slow/low-turnover.
  `cross_asset` / `population_dynamics`.
- **Must beat:** 60-40, the existing dual-momentum, AND VIX-timer — else it's dual-momentum
  relabeled (already rejected).
- **Risk+guard:** full LV fit over-parameterized → collapse to parameter-free phase
  observable; require it to add beyond plain risk-on/off relative momentum.
- **Sources:** market-as-ecology (arXiv adap-org/9812005; cond-mat/9803367); Haldane & May
  *Nature* 2011.

### B4 — Neuronal-avalanche branching ratio (criticality)  · `queued` · drawdown-insurance
- **Domain/technique:** neuroscience self-organized criticality. Define "avalanches" as runs
  of large-|return| days; estimate the **model-free branching ratio σ** (mean offspring per
  event) + avalanche-size exponent. σ→1⁺ = cascade-prone. Distinct from Hawkes (no MLE).
- **Edge beyond VIX:** cascade *propensity* (clustering geometry), not amplitude.
- **Build:** SPY (+VIX channel); threshold at trailing-year 90th pct; rolling σ; σ near/above
  1 → de-risk; low turnover. `market_state_structural`.
- **Must beat:** VIX-timer + 60-40 on Sharpe and drawdown; judge as Calmar/Sortino insurance.
- **Risk+guard:** few crash avalanches in-sample → small-sample noise; pre-register one-sided
  σ→1 rule, no crash-tuning; must add beyond a same-threshold EWMA-of-squared-returns proxy.
- **Sources:** Beggs & Plenz (Scholarpedia; J.Neurosci 29:15595); avalanche scaling (arXiv 0912.5369).

**Biology shelved:** Boolean gene-regulatory attractors (no finance bridge, arbitrary
discretization); artificial immune / negative-selection (heavy black-box, weak OOS); May
interaction-matrix eigenvalue (≈ Absorption Ratio, already rejected).

---

## PHYSICS branch (Fable, cycle 6) — **PENDING** (agent still running; will append on completion)

---

## Suggested build order
1. **B1 — foraging diffusion-exponent** (TOP: novel, prices-only, orthogonal path-memory axis, falsifiable).
2. **B2 — cross-sectional diversity** (build as B1's complement; orthogonalize-vs-VIX gate first).
3. Physics #1 (TBD) — slot after physics branch lands.
4. B3 / B4 as overlays/insurance only if a primary leaves alpha/tail on the table.

*Research artifact — not investment advice.*
