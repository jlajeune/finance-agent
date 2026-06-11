---
name: build-risk-managed-portfolio
description: Assemble and evaluate a risk-managed, multi-asset portfolio (Pivot B) — combine validated strategy sleeves + diversified allocation, vol-target it, and benchmark honestly vs 60/40 / risk parity / SPY. Use when the goal is a robust risk/return profile and drawdown control rather than a single alpha signal.
---

# Build a risk-managed portfolio

The project's repeated finding: directional alpha is hard, but **risk control and
diversification reliably reduce drawdown**. This skill turns that into the product.

## Steps
1. **Universe & data.** `load_universe("cross_asset")` (equity/rates/credit/inflation/gold/
   commodities). Add macro context via `finance_agent.data.get_fred` if useful.
2. **Allocation.** Build a diversified base with `portfolio.risk_parity_weights` (equal risk
   contribution) or `inverse_vol_weights`.
3. **De-risk.** Apply `portfolio.vol_target` (the validated overlay) and/or a trend/absolute-
   momentum mask (hold an asset only while its 12-month return > 0) for crisis protection.
4. **Combine sleeves (when available).** Pull `status: validated` strategies from the ledger
   and blend with `portfolio.combine_sleeves(method="equal_risk")` — size by risk so no
   sleeve dominates. The portfolio (a weight schedule) is scored by the standard harness.
5. **Benchmark honestly.** `portfolio.evaluate_portfolio(..., benchmarks={...})` vs **60/40,
   risk parity, buy-hold SPY** on a common span and cost. Report Sharpe AND max drawdown AND
   Calmar AND turnover; show crisis-period (2008/2020/2022) behavior and a cost-sensitivity curve.
6. **Artifacts.** Reuse `scripts/build_risk_managed_portfolio.py` to emit an equity-curve
   chart + JSON under `research/charts/`; write the findings to `research/portfolio_v*.md`.

## Guardrails
- **Don't overfit to beat 60/40.** Its 2007-2026 Sharpe is flattered by an unrepeatable bond
  bull. Prefer regime-robustness; freeze construction choices; don't cherry-pick assets ex-post.
- **Drawdown control is a legitimate deliverable.** "Far smaller drawdowns at lower Sharpe" is
  an honest, sellable outcome — state it plainly rather than torturing the data.
- **Look-ahead-safe & net of costs** throughout. Not investment advice.

## Record a process retrospective
After the work, log how the agents/skills/harness performed (not the result itself) via
`finance_agent.runlog.record_retro(cycle=..., what=..., worked=..., friction=..., suggestion=...)`
→ appends to `research/process_retro.md`. Records for later review; does not auto-apply changes.
