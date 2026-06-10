# Cross-Domain Ideation Brief — borrowing techniques from other fields

**Date:** 2026-06-08 · **Method:** two independent `lit-scout` web-research agents run in
parallel over disjoint domain partitions (A = natural/physical sciences; B = math / CS /
engineering / information theory), then synthesized and deduped here.

## The unifying thesis
Everything we've validated or tried so far reads the market's **level or trend** of a
*single* series — price (momentum/trend), index vol (vol-targeting), or the implied–realized
spread (VRP). The cross-domain ideas below instead read the market's **internal structure
and state**: how tightly coupled its parts are, whether it is approaching a regime
transition, how its shocks self-propagate, and how ordered/predictable its dynamics have
become. That is an axis our existing factors are blind to — and it is where crash-timing and
fragility live. **Headline:** both independent searches ranked the **Absorption Ratio**
(correlation-matrix eigenvalue concentration) as the strongest, most-buildable idea.

> **The one discipline that governs all of these:** each must be shown to add predictive
> content *beyond the VIX level*. Otherwise we've just re-derived cycle-2's `voltarget_spy`
> through a fancier lens. Every idea below carries that as its primary falsification guard.

Proposed new taxonomy family: **`market_state_structural`** (correlation/network/entropy
regime detectors), plus a `point_process` tag for the Hawkes idea.

---

## Tier 1 — build first (convergent #1 from BOTH agents)

### Absorption Ratio (RMT / PCA → systemic-coupling fragility)
- **Domain:** random-matrix theory / statistical physics (variance concentration in the
  leading eigenmodes of a coupled system).
- **Technique:** rolling PCA of the cross-sectional return correlation matrix; AR = fraction
  of total variance in the top ~N/5 eigenvectors. High AR ⇒ tightly coupled, *fragile*
  market where a local shock propagates everywhere. Trade the **standardized shift**
  ΔAR = (AR_15d − AR_1yr) / std(AR_1yr) — already a z-score, no in-sample scaling.
- **Edge vs vanilla:** measures cross-sectional *coupling*, orthogonal to trend, index-vol
  level, and VRP. Coupling can rise *while prices still climb and vol is still low* — the
  "calm but fragile" pre-crash state (flagged the tech bubble and 2008 per Kritzman et al.).
- **Build on our data:** sector SPDRs — we have XLF/XLK/XLE/XLV; add XLY, XLP, XLI, XLB,
  XLU, XLRE, XLC (all yfinance). Daily log returns → 500-day correlation window → AR with
  k=ceil(N/5) → ΔAR rule: >+1σ de-risk (SPY→TLT/cash), <−1σ risk-on, else neutral.
  `gross_leverage=None`; low turnover (multi-week signal).
- **Evidence (empirically supported, but replications are in-sample-heavy):** Kritzman, Li,
  Page & Rigobon, "Principal Components as a Measure of Systemic Risk," *JPM* 2011
  (SSRN 1582687); Portfolio Optimizer replication on the exact sector-SPDR universe; a 2020
  arXiv autoencoder-reconstruction-ratio paper builds on it.
- **Risks + guards:** (1) crowded since 2010 → test post-2010 OOS separately. (2) **Must beat
  a plain VIX-level timer AND static 60/40 on net Sharpe AND drawdown**, and ΔAR must retain
  predictive content after regressing out VIX changes. (3) freeze the 4 params to the paper's
  values (500/15/252, ±1σ) — do not fit. (4) ETFs (not single names) avoid survivorship in
  the covariance structure.

---

## Tier 2 — strong, and they compose into an ensemble

### Regime-switching via Statistical Jump Model (state estimation / control)
- **Domain:** hidden Markov / regime-switching, with the 2024 *statistical jump model*
  variant (a clustering objective with a jump penalty) that fixes HMM's flickering.
- **Edge:** regimes are persistent and latent; jointly estimating transitions + current state
  detects turning points earlier and more stably than thresholds on raw vol. Documented to
  cut vol and max drawdown vs HMM and buy-and-hold (US/DE/JP, 1990–2023), net of costs.
- **Build:** 2 states, ≤3 causal features (SPY realized vol, VIX level/change, down-day
  frequency) — and crucially it can **consume the Absorption Ratio and permutation entropy
  below as features**, making this the natural "ensemble" home. Filtered (not smoothed/Viterbi
  — that leaks the future) state → exposure. `gross_leverage=None`.
- **Evidence:** Nystrup et al., "Downside Risk Reduction Using Regime-Switching Signals: A
  Statistical Jump Model Approach," arXiv 2402.05272; MDPI 2020 HMM factor-investing.
- **Guard:** fix #states/features, choose jump penalty by CV-drawdown on an early held-out
  period, deflated-Sharpe penalty for configs tried.

### Critical-slowing-down: rising-variance early-warning (ecology / climate tipping points)
- **Domain:** Scheffer/Dakos/Guttal EWS before regime shifts. **Honest finding (Guttal 2015):**
  before crashes *variance and low-frequency power rise reliably, but lag-1 autocorrelation
  does NOT* — so use variance-slope only, ~3-month lead.
- **Build:** Kendall-τ trend of trailing realized variance over a rolling sub-window; rising
  τ → de-risk. Drop AC1/skew as triggers (keeps it minimal). A *transition* detector,
  complementary to vol-targeting's *level* reaction.
- **Evidence:** Guttal et al., PLOS One 2015; Diks-Hommes-Wang, *Empirical Economics* 2019.
- **Guard:** only ~4–5 true crashes in-sample ⇒ severe small-sample risk; pre-register a
  one-sided rule, no crash-specific tuning, judge as drawdown-insurance, require it to add
  beyond the Absorption Ratio.

---

## Tier 3 — promising as *features/confirmers*, not standalone alpha

- **Hawkes self-exciting jump intensity (seismology / ETAS).** Asymmetric, self-reinforcing
  stress measure ("one big down day breeds more") vs symmetric rolling variance; 3-param
  univariate exponential Hawkes on threshold-defined jumps; extends to cross-asset contagion.
  *Guard:* must beat a same-half-life EWMA of squared returns, else the machinery adds
  nothing. (Aït-Sahalia et al., *JFE* 2015.)
- **Permutation entropy / forbidden patterns (nonlinear dynamics / info theory).** Model-free
  measure of how *ordered/predictable* the return ordering has become; falling entropy ⇒
  herding/structure ⇒ de-risk. Sign is inconsistent across papers → **pre-register the sign**
  and use as a feature inside the jump model, not standalone. (Zanin et al.; 2025 crash-EWS
  evals.)
- **Correlation-network / MST breakdown (network science).** Mean pairwise correlation + MST
  total edge length as a diversification-collapse stress gauge; overlaps the Absorption Ratio.
  Use **rank (Spearman) correlation** (more stable). Build only if AR underperforms.
- **Transfer entropy coupling (information theory).** Directed information flow between
  assets/sectors as a systemic-coupling/lead-lag measure; richer but heavier than AR.

---

## Explicitly shelved
- **Reservoir computing / Echo State Networks** — large hyperparameter search will data-snoop
  ~20y of daily data; only keep if it clearly beats a linear AR(p) benchmark OOS.
- **SIR / epidemic contagion** — collapse to a parameter-free "infected-sector fraction +
  slope" breadth proxy; full network-SIR is over-parameterized with no clean OOS trading
  evidence.
- **LPPL / log-periodic power law (Sornette).** The famous econophysics crash predictor, but
  the critical literature is damning on implementability: non-unique subjective fits, no
  p-value crash criterion, matched only 7/11 crashes in a careful test. Crowded and fragile.
  Not worth a build.

---

## Recommendation
1. **Build the Absorption Ratio first** (Tier 1) — strongest, convergent, prices-only, frozen
   parameters, low turnover — with the **must-beat-VIX** guard front and center.
2. Then build the **Statistical Jump Model regime layer** and let it **ensemble** the
   Absorption Ratio + rising-variance EWS + permutation entropy as features — a genuinely
   novel "market-fragility regime" strategy that no single vanilla factor expresses.
3. Everything carries the same bar used to validate `voltarget_spy`: beat the honest
   benchmark (60/40 / VIX-timer / buy-and-hold) net of cost, on a robust parameter plateau,
   look-ahead-safe, with a deflated-Sharpe penalty for the search.

*Research artifact — not investment advice.*
