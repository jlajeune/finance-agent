# Process retrospective — effectiveness of the agents, skills & harness

A running record of what worked and what caused friction **in the process itself** (the
agent/skill definitions and the harness), separate from strategy P&L (that lives in
`runs/` and the cycle reports). The point is a reviewable trail so we — or a future agent —
can decide which **definition or harness updates** are worth making. **This log records;
it does not auto-apply changes.**

Append an entry per cycle (or per notable event) via `finance_agent.runlog.record_retro(...)`
or by hand, using the template at the bottom. Keep it about *process*, not returns.

Tags: `worked` ✅ · `friction` ⚠️ · `bug` 🐞 · `suggestion` 💡 (unapplied) · `applied` 🔧

---

## Standing process learnings (cross-cycle)

- 🔧 **Honest statistics caught real bugs.** Backtesters flagged the `deflated_sharpe` scale
  bug (cycle 3) and the red-team's HAC/non-overlapping discipline caught inflated t-stats
  (cycles 5, 8). *Keeps paying off — the harness's honesty machinery is the highest-value part.*
- 🔧 **Placebo / signal-specificity test → institutionalized** (cycle 8). A persistence-matched
  random surrogate of equal turnover killed the path-memory overlay; a filing-shuffle placebo
  killed gross profitability (cycle 9). Now standard in `red-team-quant.md`. *Most decisive single check.*
- 🔧 **Recoverability matters — session limits are routine.** The red-team (cycle 8) and
  reporter (cycle 6) died mid-run; agents repeatedly hit limits. Mitigations applied: commit
  after every stage, status-in-ledger, resume-from-disk, orchestrator finishes a dead agent's
  deterministic work (used for cycle 6 report, cycle 10 eval). *Keep persisting early.*
- ✅ **Cross-domain lit-scout convergence is a strong signal.** Two independent searches both
  ranked the Absorption Ratio #1 (cycle 5/6 ideation); worth treating multi-agent convergence
  as a prior. The novelty-first + prior-art-label upgrade reduced "re-implement a paper" churn.
- ✅ **Background bash for heavy deterministic jobs.** Long fetch/compute (wide-universe eval)
  runs better as a backgrounded shell than a sub-agent — no model budget, fully recoverable.
- ⚠️ **Sub-agents can't spawn sub-agents.** Orchestration must stay in the main thread; the
  `run-research-cycle` skill is run by the main thread, not delegated. Known and documented.

## Per-cycle notes (process only)

- **Cycles 5–7 (cross-domain builds):** ✅ agents produced novel, well-sourced ideas;
  ⚠️ several were prior art (Absorption Ratio, Zumbach) → motivated the novelty-first /
  prior-art-label upgrade. 🔧 added.
- **Cycle 8 (first novelty-first build):** 🔧 placebo test institutionalized after it
  exposed a noise edge that beat its pre-registered bar.
- **Cycle 9 (first fundamentals sleeve, EDGAR):** ✅ point-in-time EDGAR plumbing verified
  leak-free; ⚠️ the binding constraint turned out to be the *universe* (survivorship in the
  ticker list), not the data → motivated the phase-3 PIT constituent build.
- **Cycle 10 (gross profitability on PIT universe):** 🐞 **`get_prices` cache-key bug** — the
  cache filename was the literal joined ticker list, which exceeds the 255-char filesystem
  limit for wide universes (700+ names), so the wide universe couldn't fetch/cache at all.
  🔧 **Fixed** (`data._cache_path` now hashes long keys). 💡 *Suggestion for review:* the wide
  fundamental universe stresses several harness assumptions (batched fetch tolerance, EDGAR
  rate-limit time) — worth a dedicated "wide-universe" path + a capacity note in
  `backtest-harness` skill. ✅ EDGAR + PIT-universe connectors composed cleanly via
  `point_in_time_asof` ∩ `point_in_time_universe`.

---

## Template (append per cycle)
```
- **Cycle N (one-line what it was):**
  - ✅ worked: <which agent/skill/harness elements performed well>
  - ⚠️ friction / 🐞 bug: <what was clunky, broke, or wasted effort>
  - 💡 suggestion (unapplied): <concrete agent/skill/harness change to consider>
  - 🔧 applied this cycle: <any process fix actually made>
```
- **Cycle 10 (gross profitability on the point-in-time S&P500 universe (honest re-run of cycle 9)):**
  - ✅ worked: EDGAR PIT + PIT constituent universe composed cleanly (point_in_time_asof ∩ point_in_time_universe) on 710 names and produced a trustworthy, decisive result; background-bash for the heavy ~710-name fetch was fully recoverable after the agent hit a session limit (orchestrator finished it)
  - ⚠️ friction / 🐞 bug: standardized `evaluate`/runner can't score a strategy that builds its OWN wide universe (it only loads SPEC.universe=default 30 names) -> needed a bespoke eval script; ~40% of PIT members dropped/period for missing price/EDGAR data (residual price-survivorship)
  - 💡 suggestion (unapplied): add a first-class wide/PIT-universe path to the runner (e.g. SPEC.universe='sp500_pit' resolved to the union price panel) so such strategies run through the standard battery + deflated-Sharpe; evaluate a paid delisting-complete price source to cut the 40% drop
  - 🔧 applied this cycle: fixed data._cache_path to hash long cache keys (wide universes blew past the 255-char filename limit)
- **Cycle Pivot A / Tier 4 — LLM-on-primary-text v1 (Built EDGAR filing-TEXT pipeline (edgar_text.py): get_filings/get_filing_text/extract_risk_factors/text_signal_panel + point_in_time_asof_text guard + LM lexicon proxy + scaffolded llm_extract hook.):**
  - ✅ worked: Mirroring edgar.py patterns (CIK lookup, User-Agent, cache, graceful degrade, asof guard) made the connector fast to write and consistent. Offline synthetic tests for the look-ahead guard + slicer caught logic early.
  - ⚠️ friction / 🐞 bug: HTML tag-stripping injects stray spaces inside words (MSFT "RIS K FACTORS") and TOC/cross-reference "Item 1A" headings broke naive last-match slicing — needed a longest-valid-slice strategy with xref exclusion and intra-word whitespace tolerance. Section-heading variation is the main fragility.
  - 💡 suggestion (unapplied): A shared html_to_text util + a small fixtures set of real filings (cached) would let the slicer be regression-tested across filers offline. The LLM upgrade (llm_extract) is the next moat step once a key is provisioned.
