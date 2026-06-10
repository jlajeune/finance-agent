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

## PHYSICS branch (Fable, cycle 6) — full source list in commit

### P1 — Zumbach time-reversal-asymmetry vol overlay  · `queued` · OVERALL TOP PICK
- **Domain/technique:** non-equilibrium stat-mech (broken time-reversal symmetry). The
  "Zumbach effect": past *trends* (squared multi-day return sums) predict future vol, but
  past vol does not predict future trends. Forecast σ²(t+1..h) = a·RV₂₂ + b·Z, where
  Z=[Σ K(τ)r(t−τ)]² (squared EMA-trend, half-life ~10–20d); size = min(1, target_vol/σ̂).
- **Edge beyond VIX:** conditions on *signed trend* (time-irreversible), so it forecasts vol
  rises from **low-VIX melt-ups** where a VIX-timer and plain vol-target are blind. A 2-param
  additive upgrade to our *only validated strategy*.
- **Build:** SPY closes (+H/L for Garman–Klass RV baseline); walk-forward fit a,b≥0 (or freeze
  b/a on first half); weekly rebalance + hysteresis. `volatility_timing` / new `time_irreversibility`.
- **Must beat:** the **validated `voltarget_spy` itself** AND a VIX-sized variant, on net Sharpe
  AND maxDD; report whether b's incremental t-stat survives walk-forward.
- **Risk+guard:** trend² overlaps the leverage effect → also fit signed b⁺Z_up+b⁻Z_down and
  require the *symmetric* (b⁺>0) part to add Sharpe over a leverage-effect-only baseline. (NOT
  the shelved Hawkes idea — no point-process/intensity estimation; 2 frozen hyperparameters.)
- **Sources:** Zumbach 2007 (SSRN 1004992); Bouchaud 2022; El Euch-Gatheral-Radoičić-Rosenbaum
  2019 (arXiv 1809.02098); QHawkes microstructure (arXiv 1901.00834). Empirically corroborated, low-moderate crowding.

### P2 — Multifractal-cascade log-vol forecaster (MRW/MSM)  · `queued`
- **Domain/technique:** turbulence/intermittency. Log-vol has log-decaying autocovariance
  C(τ)≈λ²·ln(T/τ) (Bacry–Muzy MRW) → closed-form ~2-param long-memory vol predictor.
- **Edge beyond VIX:** multi-horizon physical-measure vol forecast (1d/1w/1m, same 2 params);
  log-kernel keeps old vol info a 22d RV throws away. Sattarhoff–Lux (IJF 2023): MRW beat 10
  classical models OOS.
- **Build:** SPY (±QQQ/IWM pooling); Garman–Klass RV from O/H/L/C; kriging-style log-covariance
  projection of log-RV; size = target_vol/exp(ω̂); freeze λ²,T pre-2015. `volatility_timing` /
  `multifractal_scaling`.
- **Must beat:** plain-RV vol-target AND EWMA(RiskMetrics) vol-target on net Sharpe AND maxDD,
  plus QLIKE forecast loss vs EWMA (forecast gain must translate to portfolio gain).
- **Risk+guard:** daily-bar gains may be small vs a good EWMA → pre-register "adopt only if
  ΔSharpe≥0.05 and maxDD not worse"; causal RV smoothing only; freeze calibration pre-2015.
- **Sources:** Duchon-Robert-Vargas (Math.Finance 2012, arXiv 0801.4220); Sattarhoff-Lux (IJF 2023);
  Wu-Muzy-Bacry log-S-fBM (arXiv 2201.09516). Empirically supported, low crowding.

### P3 — Kuramoto sector phase-synchronization  · `queued`
- **Domain/technique:** coupled-oscillator synchronization. Extract a *causal* instantaneous
  phase per sector ETF; Kuramoto order parameter R(t)=|mean e^{iφ}| measures phase-locking.
  Rising R = coherent single-mode = fragile.
- **Edge beyond VIX & AR:** *phase* alignment (timing/lead-lag), mathematically distinct from
  amplitude covariance (Absorption Ratio eigenvalues) and average correlation; can build while
  vol/VIX still low.
- **Build:** 9 sector SPDRs; causal windowed Hilbert analytic-signal phase (NEVER full-sample
  FFT — hard look-ahead leak); trade VIX-orthogonalized residual of R. `market_state_structural`/`synchronization`.
- **Must beat:** SPY / 60-40 / VIX-timer on Sharpe AND maxDD; require |corr(R,VIX)|<~0.7 and an
  incremental-info test **before** any backtest Sharpe (AR post-mortem discipline).
- **Risk+guard:** Hilbert edge-effect look-ahead → causal-only + shuffled-time placebo; VIX
  redundancy → mandatory orthogonalization first.
- **Sources:** thinner/partly speculative — Kuramoto critical points (2015); phase-sync crisis
  detection (arXiv 2001.11843); Rosenblum-Kurths method. Single-author 2025 preprint treated as untested.

### P4 — Omori-law aftershock re-entry scheduler  · `queued` · post-crash overlay
- **Domain/technique:** seismology relaxation. After a "main shock," vol relaxes as a power law
  v(t)∝(t+c)^(−p), p≈0.2–0.5 (Omori). Re-lever along the curve to harvest post-crash recovery
  that VIX-timers (slow to re-risk) sit out.
- **Edge beyond VIX:** theory-based *forward decay schedule* for re-entry; VIX overstays elevated
  post-shock (vol risk premium), so an Omori schedule re-risks earlier and faster.
- **Build:** SPY; shock = |ret|>3×trailing-63d σ; fit p,c once pre-2015, freeze; w=min(1,
  target_vol/max(σ_EWMA, v_omori)) so the curve auto-expires. `volatility_timing`/`event_relaxation`.
- **Must beat:** plain vol-target + VIX-timer on net Sharpe AND maxDD; per-episode (2008/11/18/20/22).
- **Risk+guard:** few shocks (~8–12) → one bad re-entry (Sep-2008 false bottom) dominates; cap
  exposure increase at +25%/wk, leave-one-episode-out, must not worsen maxDD in any left-out episode.
  Honest kinship: deterministic-kernel cousin of the shelved Hawkes idea (but 2 frozen params, no filtering).
- **Sources:** Lillo-Mantegna (PRE 2003); Weber-Wang-Vodenska-Havlin-Stanley (PRE 2007). Empirically supported, older.

### P5 — Fluctuation-theorem "market temperature" (gain/loss asymmetry)  · `queued` · speculative
- **Domain/technique:** non-equilibrium thermodynamics. Rolling slope Δβ of ln[P(+Q)/P(−Q)] vs
  return magnitude Q — a robustified asymmetry/skew measure. Claim: Δβ stability precedes crises.
- **Edge beyond VIX:** a skew-like state variable orthogonal to vol level. **Speculative** (one
  2025 preprint, one group).
- **Build:** SPY 50–100d window; signal = z-score of Δβ and its dispersion; de-risk gate atop vol-target.
  New `nonequilibrium_thermo`.
- **Must beat:** vol-target alone on Sharpe AND maxDD, **and** must beat the same pipeline with plain
  rolling skewness (else it's skew rebranded).
- **Risk+guard:** ~50 points to fit a distribution slope → huge sampling error; block-bootstrap Δβ
  for significance before any trading rule.
- **Sources:** Ramezani et al. 2025 (arXiv 2509.23692). Crowding ~0 (because unproven).

**Physics honorable mentions (logged, not this cycle):** entropy production in lead-lag networks
(reduces to shelved transfer-entropy; daily lead-lag mostly dead); Ising susceptibility χ
(coupling-level → same VIX-redundancy that killed AR); visibility-graph roughness (weaker-pedigree
duplicate of P2's slot).

---

## Combined build order (biology + physics)
1. **P1 — Zumbach time-reversal vol overlay** (OVERALL TOP: a 2-param upgrade to our *validated*
   `voltarget_spy`, orthogonal-to-VIX by construction, strongly corroborated, cheap to test).
2. **B1 — foraging diffusion-exponent** (best *new-axis* idea: prices-only path-memory, novel, falsifiable).
3. **P2 — multifractal log-vol forecaster** (second vol-forecast upgrade; adopt only if ΔSharpe≥0.05).
4. **B2 — cross-sectional diversity** (build as B1's complement; orthogonalize-vs-VIX gate first).
5. **P3 — Kuramoto phase-sync** (incremental-info test before backtest, per AR post-mortem).
6. Overlays/insurance only if a primary leaves tail on the table: **P4 — Omori re-entry**, **B4 — avalanche σ**.
7. Speculative / last: **B3 — Lotka-Volterra phase**, **P5 — fluctuation-theorem temperature**.

**Why P1 first:** it modifies the one strategy that has already cleared our bar, so the marginal
test is clean (does the Zumbach term beat plain `voltarget_spy`?), the mechanism is the most clearly
beyond-VIX (signed-trend → vol), and the evidence base is the deepest. **Why B1 second:** highest-value
*genuinely new axis* (path memory), uncorrelated with the vol-forecast cluster, so it diversifies the book.

*Research artifact — not investment advice.*
