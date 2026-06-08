# Cycle 3 — End-of-Cycle Research Memo

**Date:** 2026-06-08  **Cycle:** 3  **Mode:** Full cycle (lit-scout -> 3 quant-researchers -> 3 backtesters -> 3 red-team-quants -> research lead)
**Idea provenance:** Live web research (lit-scout)

---

> ## DISCLAIMER — READ FIRST
> This is an internal **research artifact**, not investment advice and not a recommendation to buy or sell any security. All figures are **model outputs** of historical backtests on a **survivorship- and selection-biased** ETF/equity universe. **Past performance does not predict future results.** Sharpe ratios are net of modeled transaction costs (5 bps default) but ignore taxes, slippage at scale, financing, and regime shifts. "Current picks" and "latest weights" are the mechanical output of a model on the last data bar, not a view. Do not trade on this document.

---

## 1. Executive Summary

Cycle 3 was a full, every-skill exercise. Lit-scout did live web research; three quant-researchers proposed genuinely diverse strategies (one each in **cross-asset allocation**, **trend-following**, and **calendar seasonality**); three backtesters ran them; three red-team-quants adversarially reviewed them.

**All three candidates were REJECTED. Zero survivors.** The ideas were clean (no look-ahead leakage), robust to parameters and costs, and each posted a respectable standalone net Sharpe (0.80–0.86). But every one of them **loses to its own honest passive benchmark** — the binding failure was not data-snooping, it was benchmark underperformance. A defensive cross-asset rotation lost to static 60/40; a cross-asset trend overlay lost to the *same basket with trend removed*; a turn-of-month tilt lost to buy-and-hold SPY in every sub-period.

The cycle's real value came from two places: **(a) the adversarial layer caught and fixed a scale bug in the deflated-Sharpe harness** that had been false-failing every daily strategy, and **(b) the rejections produced concrete, high-conviction leads for cycle 4** — most notably a plain inverse-vol risk-parity ETF basket (Sharpe ~1.02) that fell out of the trend-following autopsy.

**Single most promising strategy this cycle:** none validated. The most promising *lead* is the trend-stripped **inverse-vol risk-parity 6-ETF basket** (net Sharpe ~1.02, maxDD ~-21.3%, turnover ~0.004), which dominated SPY and 60/40 and should be tested as a first-class strategy in cycle 4. The **only standing validated recommendation across all cycles remains cycle-2's `voltarget_spy`.**

---

## 2. Cycle Map

| id | family | thesis (1 line) | net Sharpe | OOS Sharpe | DSR pass? (n=3) | honest benchmark & result | verdict |
|---|---|---|---|---|---|---|---|
| `xasset_defensive_breadth` | cross_asset | 13612W momentum rotation + canary breadth cash gate across offensive/defensive ETF sleeves | **0.83** | 1.05 | PASS (0.993) | static 60/40 SPY/TLT **1.00** (and SPY 0.86) — **loses** | **REVISE → rejected** |
| `tsmom_barbell_etf` | trend_following | barbell (short+long) TSMOM, long-flat, inverse-vol weighted on a 6-ETF basket | **0.80** | 0.68 | PASS (0.991) | same basket, **trend removed**, inverse-vol RP **1.02** — **loses** | **REJECT** |
| `tom_tilt_spy` | seasonality_calendar | small SPY overweight during turn-of-month window, parked defensive the rest | **0.86** | 0.83 | PASS (0.995) | buy-and-hold SPY net 10 bps — **loses in every sub-period** | **REJECT** |

*Headline net Sharpe at 5 bps cost, full sample (n_obs = 4131, ~2005–2025). Source: `reports/eval_<id>.json`, `headline.sharpe`. OOS Sharpe from `oos.out_of_sample.sharpe`, split at 2019-11-06.*

Three different factor families, three different mechanisms, three independent autopsies — **the breadth here is real**, which is the point: the cycle explored widely and rejected honestly.

---

## 3. Per-Strategy Findings

### 3.1 `xasset_defensive_breadth` (cross_asset) — REVISE, recorded rejected

**Thesis & mechanism.** Each month, score every asset with a front-weighted 13612W average-momentum signal. Rotate the risk book into the top-2 offensive equity ETFs (SPY/QQQ/IWM/XLK) and the defensive book into the best *positive-momentum* defensive asset (TLT/GLD/HYG, else cash). A canary breadth gate (SPY/HYG/IWM) sets the cash fraction = share of canaries with non-positive momentum, de-risking before the held asset confirms a downtrend. Ensembled across staggered rebalance offsets to neutralize timing luck.

**Evidence.** Net Sharpe **0.83**, maxDD **-25.4%** (`eval_xasset_defensive_breadth.json` headline). OOS Sharpe **1.05** > IS 0.64 (improves out of sample). Clean leak scan, flat parameter plateau, DSR 0.993 (n=3). Cost-robust down to ~20 bps.

**Why rejected.** It fails its **own** falsification bar — beat static 60/40. 60/40 SPY/TLT posts Sharpe **1.00** (maxDD -27.2%); plain SPY is **0.86**. The strategy cuts drawdown vs SPY but *loses Sharpe to both*. Worse, the defensive machinery barely earns its keep: the canary/breadth gate adds only **~0.01 Sharpe** over a naive always-long-top-2 (0.82), and the "positive-defensive-only" 2022 refinement is cosmetic. The current book is a **100% tech long (QQQ/XLK)** — the model is just riding momentum into concentration.

**Mitigation (genuine).** The 60/40 dominance is largely a **2010–2021 bond-bull artifact**; in the 2008, 2020, and 2022 stress years the strategy *beats* 60/40 on return. So the loss is benchmark-era-specific, not structural.

**Promising fix (red-team tested).** **Vol-target the book to ~10%** annual: Sharpe **0.84** but maxDD improves from **-25% to -17.8%** — now beats 60/40 on drawdown. This is the top cycle-4 revision and re-confirms vol-targeting as the recurring value-add.

**Residual risks / treatment.** Concentration risk (single-sleeve tech long), benchmark-era sensitivity, and the fact that the alpha is mostly passive equity beta. **Recommended treatment: no capital. Carry forward as a vol-targeted REVISE candidate in cycle 4.**

### 3.2 `tsmom_barbell_etf` (trend_following) — REJECT

**Thesis & mechanism.** Per-asset barbell time-series momentum (short ~20d + long ~250–500d trend-slope sign, excluding the spanned medium horizon), EMA-smoothed with hysteresis, mapped long-flat {0,+1}, inverse-vol weighted with gross ≤ 1 on a 6-ETF basket (SPY/QQQ/IWM/TLT/GLD/HYG). Ensembled over lookback pairs and rebalance offsets.

**Evidence.** Net Sharpe **0.80**, maxDD **-24.3%** (`eval_tsmom_barbell_etf.json`). **Lowest turnover of the cycle (0.007)**, cost-robust to 40 bps (Sharpe still 0.73), flat parameter plateau, clean leak scan, DSR 0.991.

**Why rejected — decisively.** The trend timing **strictly destroys value**. The *identical inverse-vol risk-parity basket with trend removed* (always-on) posts Sharpe **1.02**, maxDD **-21.6%** — better Sharpe *and* better drawdown. It also loses to equal-weight daily (0.99), inverse-vol monthly (1.02), and buy-and-hold variants. The crisis-convexity thesis is **falsified**: trend timing detracted in **11 of 17 years**; in 2022 it cost 2.9pp and still lost **-19.6%**. The **~40% HYG inverse-vol weight is dead-weight ballast** — capping per-name exposure to 20% lifts Sharpe to 0.91.

**Serendipitous lead (the real prize).** The trend-stripped **inverse-vol monthly-rebalanced risk-parity 6-ETF basket** = Sharpe **~1.02**, maxDD **-21.3%**, turnover **0.004** — it dominates both SPY and 60/40. **This is a strong, near-shovel-ready cycle-4 candidate.**

**Residual risks / treatment.** None to carry as a trend strategy — the timing layer is value-destroying here. **No capital.** Promote the RP basket as a new strategy.

### 3.3 `tom_tilt_spy` (seasonality_calendar) — REJECT

**Thesis & mechanism.** Hold SPY always, apply a small calendar-locked overweight during the turn-of-month window (last trading day of prior month through TD+3, weighted to days 0/+1), funded by a small underweight parked in a TLT/GLD/HYG inverse-vol blend. Harvest institutional-flow TOM as a mild oscillation, ~2 rebalances/month.

**Evidence.** Net Sharpe **0.86**, maxDD **-31.0%** (`eval_tom_tilt_spy.json`). Looks fine in isolation; DSR 0.995.

**Why rejected.** It **loses to buy-and-hold SPY net of 10 bps in every sub-period** (post-2015 Sharpe 0.79 vs SPY 0.82). Break-even cost is only **~6–7 bps**, against **~100x SPY turnover**. The required **post-2015 persistence test FAILS**: the in/out-window premium is statistically insignificant (post-2015 **+2.6 bps/day, Welch t = 0.48, p ≈ 0.63**), and an amplitude sweep is monotone toward **tilt = 0** (best variant is just hold SPY). The -31% vs -34% drawdown edge is **100% the static defensive parking, not seasonal timing** — a constant (non-seasonal) defensive tilt does *better*. The TOM anomaly has decayed in the ETF era.

**Residual risks / treatment.** None worth carrying. **No capital. Do not revisit TOM as a standalone timing edge.**

---

## 4. Process Win — Harness Bug Caught & Fixed

> **The adversarial layer found a real bug in `metrics.deflated_sharpe`.**

The deflated-Sharpe routine compared a **per-observation** Sharpe (~0.05) against a **z-score** threshold (~0.85). The two are on different scales, so the test **false-failed every daily strategy**, while `n_trials=1` would auto-pass (no selection penalty). The bug meant the gate was effectively decorative.

**Fix:** convert `e_max` to a per-observation threshold via `1/sqrt(n-1)`, and treat `n_trials=1` as "no selection." After the fix, **all three cycle-3 strategies PASS deflated Sharpe (~0.99) at n_trials=3** — confirming that **data-snooping was *not* the reason they failed.** Benchmark underperformance is the binding constraint.

**Meta-lesson from the red-team:** an *honest* `n_trials` should count **all decision points (≥20)**, not 3. At n_trials ≥ 20 the DSR becomes **borderline** for these candidates. Future evals must pass a realistic `n_trials`, or the gate will keep waving through marginal strategies. (See cycle-4 seeds.)

---

## 5. What We Learned

1. **Beating a simple passive benchmark net of cost is the real bar.** Every cycle-3 idea cleared the statistical gates and died on the economic one. Standalone Sharpe is not evidence; **Sharpe vs the right passive comparator** (RP basket, 60/40, buy-and-hold) is.
2. **Trend/calendar timing overlays on already-diversified baskets tend to subtract value.** Both the TSMOM timing layer and the TOM tilt were *negative* alpha relative to leaving the underlying static. Timing must clear a high bar to justify its turnover.
3. **Vol-targeting is the recurring value-add.** It was cycle-2's validated winner (`voltarget_spy`) and is the proposed cycle-4 fix for `xasset`. When a strategy's problem is drawdown, vol-targeting is the first lever to pull.
4. **Concentration creep is a silent failure mode.** The xasset book drifted to 100% tech; HYG dominated the TSMOM basket as dead ballast. Per-name caps materially help.
5. **The statistical gate was lying to us** (Section 4) — and would have done so silently without an adversarial reviewer. Fix shipped.

**Regions of idea space still open:** plain risk-parity / inverse-vol allocation (not yet tested as a first-class strategy), cross-sectional equity factors on a **point-in-time** (de-survivorshipped) universe, and regime-conditioned timing. **Closed for now:** turn-of-month / calendar seasonality as a standalone timing edge; naive cross-asset trend overlays on diversified baskets.

---

## 6. Next Cycle (Cycle 4) — Ranked Seeds

1. **Inverse-vol risk-parity 6-ETF basket as its own strategy** *(highest conviction).* The trend-stripped basket already shows Sharpe ~1.02, maxDD -21.3%, turnover 0.004, dominating SPY and 60/40. Test directly, add per-name caps, stress regimes.
2. **Vol-targeted `xasset_defensive_breadth` (REVISE).** Apply ~10% vol-target + duration sizing; red-team prototype already cut maxDD to -17.8% and beats 60/40 on drawdown. Cheapest path to a first validated cross-asset strategy.
3. **Deconcentrated / regime-gated trend.** If trend is revisited, force per-name caps (≤20%) and gate it on a regime signal so timing only acts when it historically helped — not as an always-on overlay.
4. **Pass an honest `n_trials` (≥20) to every eval.** Count all decision points. Re-run survivors under the realistic selection penalty; expect borderline DSR and budget for it.
5. **Move toward a point-in-time / de-survivorshipped universe.** The recurring caveat across cycles is selection bias. Begin sourcing a point-in-time universe so cross-sectional ideas can be tested honestly.

**Lit-scout follow-ups:** risk-parity construction and vol-targeting refinements; evidence on TSMOM horizon spanning (fast+slow vs medium); decay of calendar anomalies in the ETF era (confirms the TOM rejection).

---

## 7. Standing Recommendation

**No strategy was validated in cycle 3.** The **only validated, standing recommendation across all cycles is cycle-2's `voltarget_spy`** — volatility-targeted SPY exposure (~11% vol target, ~**76% SPY / 24% cash** at the latest bar; net Sharpe 0.86, maxDD -19.9%, source `reports/eval_voltarget_spy.json`). This remains a research artifact, not investment advice (see disclaimer).

---

*Sources: `reports/eval_xasset_defensive_breadth.json`, `reports/eval_tsmom_barbell_etf.json`, `reports/eval_tom_tilt_spy.json`, `reports/eval_voltarget_spy.json`, ledger (`finance_agent.cli ledger-list`), and the three red-team verdict/sharpening notes for cycle 3.*
