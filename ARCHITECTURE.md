# finance-agent — how the agents and skills fit together

This system hypothesizes, backtests, and adversarially vets equity trading strategies,
then reports validated stock-pick recommendations. It is built from **sub-agents**
(specialist roles) coordinated by an **orchestration skill**, sitting on top of a small,
transparent Python **harness** (the shared yardstick) and a **ledger** (novelty memory).

The design goal throughout: keep the search **diverse and novel** without **over-
constraining** the ideas. Deterministic Python handles the parts that must be identical
for fair comparison (backtest, validation, metrics); everything else — new signals, new
data sources, new API integrations — is open for the agents to build.

---

## The pieces

### 1. Orchestration skill — `run-research-cycle` (the conductor)
**Yes, this is the overarching skill that pulls everything together.** The main thread
invokes it and plays orchestrator: it sets the cycle number, assigns diverse lenses,
dispatches the sub-agents in the right order (with parallel fan-out where possible),
manages the ledger, enforces guardrails (no look-ahead, honest `n_trials`, dedup), and
respects pause points. It does **not** generate or judge ideas itself — it runs the
process.

```
                         ┌─────────────────────────────────────────┐
                         │   run-research-cycle  (orchestrator)     │
                         │   — the main thread plays this role      │
                         └─────────────────────────────────────────┘
                                          │ dispatches
        ┌──────────────┬──────────────────┼──────────────────┬───────────────┐
        ▼              ▼                   ▼                  ▼               ▼
  ┌───────────┐  ┌───────────┐    ┌───────────────┐   ┌───────────┐  ┌────────────────┐
  │ lit-scout │  │  quant-   │×N  │  backtester   │×N │ red-team- │×N│  portfolio-    │
  │ (seeds)   │  │ researcher│    │ (eval battery)│   │  quant    │  │  reporter      │
  │           │  │ (ideas)   │    │               │   │(adversary)│  │  (cycle memo)  │
  └─────┬─────┘  └─────┬─────┘    └───────┬───────┘   └─────┬─────┘  └────────┬───────┘
        │ seeds        │ writes           │ scores          │ verdict         │ reads all
        ▼              ▼                  ▼                 ▼                 ▼
   recent papers   strategies/<id>.py   reports/eval_*.json  ledger status   reports/cycle_N.md
   & free data         │                     │                  │
        └──────────────┴─────────┬───────────┴──────────────────┘
                                 ▼
                    ┌──────────────────────────────┐
                    │  finance_agent harness +      │  ← shared yardstick + novelty memory
                    │  ledger/strategies.jsonl      │
                    └──────────────────────────────┘
```

### 2. Sub-agents (specialist roles, in `.claude/agents/`)
A new fresh-context agent is dispatched per role; several run in parallel.

| Sub-agent | Role | Key tools | Output |
|---|---|---|---|
| **lit-scout** | Recombine recent research into *untried* ideas (multi-paper fusion, "future work", analogical transfer); prior-art label each | WebSearch, WebFetch | ranked novel seeds + sources + prior-art |
| **quant-researcher** | Implement ONE novel, falsifiable strategy (with `prior_art`/`novel_combination`) | Read/Write/Edit/Bash | `strategies/<id>.py` + thesis + falsification |
| **backtester** | Run the standardized eval battery; report facts, flag leaks | Bash/Read/Write | `reports/eval_<id>.json` + honest summary |
| **red-team-quant** | Break the strategy: look-ahead, overfit, cost, **placebo / signal-specificity**, difference-vs-incumbent significance | Bash/Read/Edit/WebSearch | REJECT / REVISE / PASS + evidence |
| **portfolio-reporter** | Synthesize the cycle into a decision-ready memo + current picks | Read/Write/Bash | `reports/cycle_N_report.md` |
| **data-engineer** | Add & look-ahead-proof new data sources; maintain the data catalog + moat rubric (Pivot A) | Read/Write/Edit/Bash/WebSearch | new connector + catalog entry + sleeve ideas |
| **portfolio-constructor** | Assemble a risk-managed multi-asset portfolio from validated sleeves; benchmark honestly (Pivot B) | Read/Write/Edit/Bash | portfolio + stats vs 60/40/RP/SPY + chart |

Why sub-agents (not one mega-prompt): each gets a clean context and a single mandate,
they can run **in parallel** (true breadth), and the **adversarial separation** is real
— the red-team has no stake in the idea it's attacking.

### 3. Skills (in `.claude/skills/`)
Three *orchestration* skills (the main thread runs one to drive a workflow) + two reference
skills (shared knowledge, loaded on demand):
- **run-research-cycle** — alpha-discovery orchestrator (research → generate → backtest →
  red-team → report), with novelty-first ideation and mid-run recoverability baked in.
- **build-risk-managed-portfolio** — assemble & honestly benchmark a risk-managed portfolio (Pivot B).
- **add-data-source** — add a look-ahead-safe data connector + catalog it with a moat score (Pivot A).
- **backtest-harness** (reference) — the strategy contract, CLI, metrics, how to extend.
- **strategy-ledger** (reference) — the novelty memory + diversity-vs-freedom balance.

### 4. The Python harness (`src/finance_agent/`) — the shared yardstick
Small and readable so agents can audit and extend every line. It is the part that must
stay identical across strategies so results are **comparable**:
- `data.py` — fetch/cache prices (yfinance); default + **cross-asset** universes; free
  **`get_fred`** macro connector; look-ahead-safe API. (`edgar.py` — point-in-time EDGAR
  fundamentals.)
- `strategy.py` — the `StrategySpec` (incl. `gross_leverage`, `prior_art`,
  `novel_combination`) + `generate_weights` contract and the `TAXONOMY`.
- `backtest.py` — vectorized weights→P&L engine; **execution lag** kills look-ahead,
  **turnover costs** kill free churn.
- `metrics.py` — Sharpe/Sortino/drawdown/Calmar/turnover/t-stat/**deflated Sharpe**.
- `validation.py` — OOS split, walk-forward, parameter & cost sensitivity, subsample
  stability, deflated-Sharpe report. Part of the red-team's arsenal.
- `portfolio.py` — risk parity / inverse-vol allocation, portfolio-level vol-targeting,
  **`combine_sleeves`** (blend validated strategies by risk), honest benchmark eval (Pivot B).
- `runlog.py` — record each cycle as a durable `runs/run-XXXX-<UTC>/` artifact + `INDEX.md`.
- `runner.py` / `cli.py` — load a strategy and run the full battery in one command.

### 5. The ledger (`ledger/strategies.jsonl`) — novelty memory
Append-only record of every strategy attempted. It exposes only a **coarse** view to
generators (which factor families are crowded, plus short theses for a soft dup check)
— never the formulas of prior work. That is the mechanism that keeps the search diverse
**without anchoring** new ideas.

---

## How a cycle flows

1. **Seed (optional).** `lit-scout` surfaces fresh, externally-grounded angles from
   recent papers and free datasets.
2. **Diversify.** Orchestrator reads the ledger's coarse "occupied regions" and assigns
   each generator a distinct, mostly-open factor family + a variation seed.
3. **Generate (parallel).** N `quant-researcher`s each produce one novel strategy. They
   are free to build new data fetchers/API integrations and scratch scripts — only two
   rules: past-data-only signals, and conform to `generate_weights` at the end.
4. **Backtest (parallel).** A `backtester` scores each strategy with the SAME battery,
   carrying the true `n_trials` (= ideas explored) into the deflated-Sharpe test.
5. **Adversarial vetting.** A `red-team-quant` tries to break each one (look-ahead,
   overfitting, OOS decay, regime/survivorship bias, cost/capacity) and either rejects
   it, requests a revision, or passes it — and sharpens survivors.
6. **Report.** `portfolio-reporter` writes the cycle memo: the breadth map, validated
   strategies with evidence, current picks, lessons, and seeds for the next cycle.

Across cycles, the ledger grows, so the system keeps pushing into unexplored regions.

---

## Three modes
The same harness + agents support three workflows:
1. **Alpha discovery** (`run-research-cycle`) — the cycle above; find & vet new strategies.
2. **Risk-managed portfolio** (`build-risk-managed-portfolio` + `portfolio-constructor`) —
   combine *validated* strategies ("sleeves", `status: validated` in the ledger) with a
   cross-asset allocation into a drawdown-controlled portfolio, benchmarked honestly vs
   60/40 / risk parity / SPY. The product is risk control, not a single signal.
3. **Data-moat expansion** (`add-data-source` + `data-engineer`) — widen the data layer
   toward less-crowded, higher-mechanism sources (point-in-time fundamentals, LLM-on-text,
   options), each look-ahead-safe and scored in `research/data_catalog.md`.

## Research disciplines that make verdicts trustworthy
- **Novelty-first:** prefer *untried combinations* over re-implementing known methods; every
  idea carries a `prior_art` label (`none_found` / `extends` / `reimplements`).
- **Beat the right baseline:** a strategy must beat its honest benchmark (incumbent / 60-40 /
  a plain VIX timer), not just "go up".
- **Placebo / signal-specificity:** for any "signal gates a base", a persistence-matched
  *random* surrogate of the same turnover must NOT match it — else the edge is the turnover,
  not the signal. (A statistically beyond-VIX signal is not automatically tradable.)
- **Honest statistics:** deflated Sharpe for multiple testing; non-overlapping / Newey-West
  standard errors; test the *difference* vs the incumbent, not the absolute Sharpe.
- **Recoverability:** commit after every stage; status lives in the ledger; resume from disk
  (`ledger-list` / `reports/eval_*.json` / `runs/`); the orchestrator can do any dead agent's
  deterministic work itself.

## What 8 cycles actually showed (honest)
**One** validated strategy (`voltarget_spy`); everything else correctly rejected — several on
the placebo/beyond-baseline bar (Absorption Ratio, Zumbach, the path-memory overlay). The
repeatable edge on accessible data is **risk control / drawdown reduction, not directional
alpha**. `research/progress.md` charts it; `research/pivots.md` lays out where real usefulness
lives (better/rarer data, risk-managed portfolios, strategy due-diligence).

---

## The two design tensions, and how each is resolved

**Novelty vs. over-constraining.** Diversity is steered at the *coarse* taxonomy level
(crowded vs open families) and with per-generator seeds and parallel fan-out — never by
prescribing solutions or leaking prior formulas. Generators keep full creative latitude
inside their lens.

**Reusable determinism vs. open-ended experimentation.** Only the *evaluation* is fixed
(so comparisons are fair and look-ahead is structurally impossible). *Idea generation is
wide open*: agents write new signal code, add data sources (Twitter/X, FRED, EDGAR,
options, Trends, on-chain, …), and prototype freely under `scratch/`. The single bridge
back to rigor is the `generate_weights` contract.

---

## Extending the system
- **New data source / API** → use the `add-data-source` skill / `data-engineer` agent: add a
  fetcher in `data.py` (or a submodule like `edgar.py`) following the `get_fred` template,
  cache under `data/cache`, keep it **point-in-time / look-ahead-safe** (index by availability
  date), document any key/env var, and catalog it with a moat score in `data_catalog.md`.
- **New factor family** → add it to `TAXONOMY` in `strategy.py`; the ledger and diversity
  brief pick it up automatically.
- **New robustness test** → add to `validation.py`; wire into the red-team's checklist.
- **New portfolio construction** → add to `portfolio.py`; combine validated sleeves via
  `combine_sleeves`; benchmark with `evaluate_portfolio`.
- **New role** → add a sub-agent in `.claude/agents/` and a dispatch step in the relevant
  orchestration skill.

---

## Disclaimer
This is a **research artifact**. The default universe (today's large caps) carries
survivorship/selection bias; backtests are not live performance. Nothing here is
investment advice.
