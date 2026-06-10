---
name: run-research-cycle
description: Orchestrate one full strategy-research cycle — diversify, generate hypotheses in parallel, backtest, adversarially vet, and report. Use when the user wants to "run a research cycle", "find new strategies", "generate and test stock strategies", or kick off the finance-agent pipeline. The main thread runs this; it dispatches the role sub-agents.
---

# Run a strategy research cycle

You are the **orchestrator**. You don't generate or judge ideas yourself — you run the
process that keeps the team exploring *novel, diverse* strategies and subjects each to
honest, adversarial validation. Sub-agents do the specialized work; you coordinate,
enforce diversity, and manage the ledger.

## 0. Setup (once)
- Ensure deps: `pip install -r requirements.txt` and `pip install -e .` (so
  `finance_agent` imports). If the environment blocks network/installs, tell the user
  and pause — the cycle needs data access to backtest.
- Pick the cycle number `N` (one more than the max `cycle` in the ledger; 1 if empty).
- Decide cycle size: default **4-6 parallel ideas**. More breadth = better search but
  more cost.

## 1. Novelty synthesis (research → unique untried combinations)
Dispatch **lit-scout**. Its job is not just to find recent research but to **recombine** it
into *genuinely untried* ideas: "given this finding, what could we combine it with — in a
unique way that hasn't been done — that still makes economic sense?" Keep ideation **as open
as possible** (cross-domain pairings welcome) with one hard gate: **not a re-implementation
of a known method**. Each seed must carry a **prior-art label** (`none_found` / `extends: X`
/ `reimplements: X`) from an actual search. Prefer `none_found`/`extends`; treat `reimplements`
seeds as baselines only. Re-coding famous methods (we've rejected Absorption Ratio, Zumbach,
VRP for being known/VIX-redundant) is the failure mode this stage exists to prevent.
Hold the ranked shortlist for assignment.

## 2. Assign diverse lenses
- Run `python -m finance_agent.cli diversity --cycle N` to see crowded vs open families.
- Sample **one distinct taxonomy family per generator** without replacement, biased
  toward open families and lit-scout seeds. Give each generator: its assigned lens, the
  coarse diversity brief, a distinct random seed/variation hint, and cycle N.
- **Diversity vs freedom balance (important):** pass only the *coarse* brief (which
  families are crowded). Do NOT pass the formulas/params of existing strategies — that
  would anchor the generators. Differentiation is enforced at the idea/family level, not
  by prescribing solutions.

## 3. Generate in parallel
Dispatch one **quant-researcher** per assigned lens **in a single message** (parallel
fan-out). Each returns a strategy file + thesis + falsification conditions. Track the
total number of ideas explored — this is `K` for the deflated-Sharpe test.

## 4. Backtest
For each strategy, dispatch a **backtester** with `--n-trials K`. Collect the JSON
reports. (These can run in parallel too.) If a backtester flags a look-ahead leak,
send the strategy back to its quant-researcher to fix before proceeding.

## 5. Adversarial vetting
For each backtested strategy, dispatch a **red-team-quant**. It returns
REJECT / REVISE / PASS with evidence and sharpening notes, and updates the ledger
status. For REVISE verdicts, optionally loop once: hand the notes back to the
quant-researcher, re-backtest, re-vet (cap at one revision loop per cycle to control
cost).

## 6. Report
Dispatch **portfolio-reporter** to synthesize `reports/cycle_N_report.md`: the cycle
map, validated strategies, current picks, what was learned, and seeds for the next
cycle. Surface the report path and TL;DR to the user. **Fallback:** if the reporter
dies mid-run (session limit), the main thread writes the report + records the run itself
from the committed eval JSONs and ledger statuses — never leave the cycle half-closed.

## 7. Capture a durable run artifact (always)
Record the cycle as a traceable, ID'd artifact so results are reviewable in GitHub:
```python
from finance_agent.runlog import record_run
record_run({
    "cycle": N, "universe": "...", "data_span": "...", "cost_bps": 5, "n_trials": K,
    "idea_provenance": "lit-scout web research | internal knowledge",
    "strategies": [{"id": ..., "family": ..., "net_sharpe": ..., "verdict": "PASS|REVISE|REJECT", "reason": ...}],
    "survivors": <int>, "summary": "...", "next_cycle_seeds": [...],
}, artifacts=["reports/cycle_N_report.md", "reports/eval_<id>.json", ...])
```
This creates `runs/run-XXXX-<UTCstamp>/` (manifest + copied artifacts) and appends a row
to `runs/INDEX.md`. The run id is both incrementing and datetime-based. Then **commit and
push** `runs/`, `strategies/`, and `ledger/strategies.jsonl` so the cycle is captured.

## Recoverability (assume any sub-agent or your own session can die mid-run)
Sub-agents and the orchestrator both hit session limits in practice. Never keep cycle
state only in memory or in an agent's pending final message. Instead:
- **Persist + commit after every stage.** After generation, after backtests, after
  vetting, after the report — `git add` the new artifacts and commit (short message). A
  crash then costs at most one stage, and the branch always reflects real progress.
- **Status lives in the ledger**, not your head: each strategy moves
  `proposed → (rejected|validated)` as verdicts land. That row is the source of truth.
- **Resume from disk.** To pick up an interrupted cycle, reconstruct state from committed
  artifacts — no memory required:
  - `python -m finance_agent.cli ledger-list` → which ids exist this cycle and their status.
  - `ls reports/eval_*.json` → which strategies are already backtested.
  - `ls runs/` + `runs/INDEX.md` → whether the run artifact was recorded.
  Then run only the missing stages. The standardized harness is deterministic, so re-running
  a stage reproduces the same numbers.
- **Sub-agents persist as they go** (the quant-researcher writes the file + registers the
  ledger row before writing its summary), so a dead generator still leaves a usable strategy.
- **You (the orchestrator) can do any role's deterministic work yourself** if its agent dies
  — run the eval CLI, write the report, call `record_run` — rather than blocking on a respawn.

## Guardrails
- **No look-ahead, ever** — the engine enforces an execution lag, but reject any
  strategy whose code peeks forward.
- **Novelty over re-implementation** — favor untried combinations; record each idea's
  `prior_art` label, and don't let a re-coded known method pass as a new discovery.
- **Honest accounting** — always carry `n_trials = K` into deflated Sharpe; never reset
  it to 1 to make a result look significant.
- **Diversity check** — if two generators converged on near-identical theses (use
  `cli novelty`), keep only the better and re-task the other into an open family.
- **Not investment advice** — every report carries the disclaimer; you are producing a
  research artifact on a survivorship-biased universe.
- **Pause points** — if the user asked to review between stages (e.g. after generation,
  before backtesting), stop and present rather than barrelling through.

## State & artifacts
- `ledger/strategies.jsonl` — every attempted strategy (the novelty memory across cycles).
- `strategies/<id>.py` — strategy implementations.
- `reports/eval_<id>.json` — per-strategy evaluation.
- `reports/cycle_N_report.md` — the cycle deliverable.
