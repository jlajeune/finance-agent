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
| **lit-scout** | Scout recent literature & free datasets to seed novel angles | WebSearch, WebFetch | ranked strategy seeds + sources |
| **quant-researcher** | Generate ONE novel, falsifiable hypothesis and implement it | Read/Write/Edit/Bash | `strategies/<id>.py` + thesis + falsification conditions |
| **backtester** | Run the standardized eval battery; report facts, flag leaks | Bash/Read/Write | `reports/eval_<id>.json` + honest summary |
| **red-team-quant** | Adversarially try to break the strategy, then sharpen survivors | Bash/Read/Edit/WebSearch | REJECT / REVISE / PASS + evidence |
| **portfolio-reporter** | Synthesize the cycle into a decision-ready memo + current picks | Read/Write/Bash | `reports/cycle_N_report.md` |

Why sub-agents (not one mega-prompt): each gets a clean context and a single mandate,
they can run **in parallel** (true breadth), and the **adversarial separation** is real
— the red-team has no stake in the idea it's attacking.

### 3. Reference skills (in `.claude/skills/`)
Loaded on demand by whichever agent needs them — shared knowledge, not roles:
- **backtest-harness** — the strategy contract, CLI commands, how to read metrics, and
  how to *extend* the harness with new data/scripts.
- **strategy-ledger** — how the novelty memory works and how to keep the diversity-vs-
  freedom balance right.

### 4. The Python harness (`src/finance_agent/`) — the shared yardstick
Small and readable so agents can audit and extend every line. It is the part that must
stay identical across strategies so results are **comparable**:
- `data.py` — fetch/cache prices (yfinance default); look-ahead-safe API; default universe.
- `strategy.py` — the `StrategySpec` + `generate_weights` contract and the `TAXONOMY`.
- `backtest.py` — vectorized weights→P&L engine; **execution lag** kills look-ahead,
  **turnover costs** kill free churn.
- `metrics.py` — Sharpe/Sortino/drawdown/Calmar/turnover/t-stat/**deflated Sharpe**.
- `validation.py` — OOS split, walk-forward, parameter & cost sensitivity, subsample
  stability, deflated-Sharpe report. This is the red-team's arsenal.
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
- **New data source / API** → add a fetcher in `data.py` (or a new module), cache under
  `data/cache`, keep it look-ahead-safe, document any API key/env var, and list it in
  the strategy's `SPEC.feature_families`.
- **New factor family** → add it to `TAXONOMY` in `strategy.py`; the ledger and
  diversity brief pick it up automatically.
- **New robustness test** → add to `validation.py`; wire into the red-team's checklist.
- **New role** → add a sub-agent in `.claude/agents/` and a dispatch step in
  `run-research-cycle`.

---

## Disclaimer
This is a **research artifact**. The default universe (today's large caps) carries
survivorship/selection bias; backtests are not live performance. Nothing here is
investment advice.
