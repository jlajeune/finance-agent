# finance-agent

An agentic system that **hypothesizes, backtests, and adversarially vets equity trading
strategies** — then reports validated stock-pick recommendations. It runs ideas in
parallel, keeps them novel and diverse via a strategy ledger, and pressure-tests each
one with a dedicated adversarial reviewer.

> **Research artifact, not investment advice.** Backtests on a survivorship-biased
> universe are not live performance. Past results do not predict the future.

## How it works (one paragraph)
An orchestration **skill** (`run-research-cycle`) coordinates five specialist
**sub-agents** — `lit-scout` (seed ideas from recent research/free data),
`quant-researcher` (generate & implement novel strategies, in parallel),
`backtester` (standardized evaluation), `red-team-quant` (adversarial vetting), and
`portfolio-reporter` (the end-of-cycle memo). They sit on a small, transparent Python
**harness** (the shared yardstick that makes results comparable and look-ahead
impossible) and a **ledger** that remembers what's been tried so the search keeps
finding new ideas. Full picture: **[ARCHITECTURE.md](ARCHITECTURE.md)**.

## Layout
```
.claude/agents/     5 specialist sub-agents (the roles)
.claude/skills/     run-research-cycle (orchestrator) + harness/ledger references
src/finance_agent/  the Python harness: data, backtest, metrics, validation, ledger, cli
strategies/         strategy modules (example_xs_momentum.py is the reference template)
ledger/             strategies.jsonl — the novelty memory
reports/            per-strategy eval JSON + cycle report markdown
scratch/            free space for agents to prototype data integrations & scripts
```

## Quick start
```bash
pip install -r requirements.txt && pip install -e .

# Kick off a cycle (the orchestrator skill drives the sub-agents):
#   in Claude Code:  /run-research-cycle      (or just ask: "run a research cycle")

# Drive the harness directly:
python -m finance_agent.cli diversity --cycle 1
python -m finance_agent.cli evaluate strategies/example_xs_momentum.py --n-trials 1
```

## Design principles
- **Diverse without over-constraining** — diversity is steered at the coarse factor-
  family level (crowded vs open); generators are never shown prior formulas.
- **Open-ended ideas, fixed evaluation** — agents freely write new signals and wire up
  new data sources/APIs (Twitter/X, FRED, EDGAR, options, Trends, on-chain, …); only the
  scoring battery is standardized, via the `generate_weights` contract.
- **Adversarial by construction** — a red-team with no stake in the idea hunts
  look-ahead bias, overfitting, OOS decay, regime/survivorship bias, and cost fragility.
- **Honest statistics** — deflated Sharpe accounts for how many ideas were searched.

## Data
Defaults to **yfinance** (no API key). Cached to `data/cache`. Swap or extend in
`src/finance_agent/data.py`.
