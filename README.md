# finance-agent

An agentic system that **researches, builds, and adversarially vets** quantitative trading
ideas — and, just as importantly, **honestly rejects** the ones that don't hold up. It now
spans three modes: discovering strategies, assembling risk-managed portfolios, and growing a
data moat.

> **Research artifact, not investment advice.** Backtests on a survivorship-biased universe
> are not live performance. Past results do not predict the future.

## What it does (one paragraph)
Specialist **sub-agents** — `lit-scout` (recombine recent research into *untried* ideas),
`quant-researcher` (implement them), `backtester` (standardized eval), `red-team-quant`
(adversarial vetting, incl. a placebo/signal-specificity test), `portfolio-reporter` (cycle
memo), plus `data-engineer` (new data sources) and `portfolio-constructor` (risk-managed
portfolios) — sit on a small, transparent Python **harness** (the shared yardstick that makes
results comparable and look-ahead structurally impossible) and a **ledger** (novelty memory).
Every cycle is captured as a durable run artifact. Full picture:
**[ARCHITECTURE.md](ARCHITECTURE.md)**.

## Three modes
1. **Alpha discovery** — `run-research-cycle`: research → generate (parallel) → backtest →
   red-team → report. Novelty-first (combine ideas in untried ways, with a prior-art label).
2. **Risk-managed portfolio** — `build-risk-managed-portfolio`: combine validated strategies
   ("sleeves") + a cross-asset allocation into a drawdown-controlled portfolio, benchmarked
   honestly vs 60/40 / risk parity / SPY.
3. **Data-moat expansion** — `add-data-source` / `data-engineer`: add look-ahead-safe data
   (FRED macro, point-in-time EDGAR fundamentals, options, …) and catalog it with a moat score.

## Layout
```
.claude/agents/     7 specialist sub-agents (research, build, vet, report, data, portfolio)
.claude/skills/     run-research-cycle + build-risk-managed-portfolio + add-data-source
                    + reference skills (backtest-harness, strategy-ledger)
src/finance_agent/  harness: data (+FRED/EDGAR connectors), backtest, metrics, validation,
                    portfolio, strategy contract, ledger, runlog, runner, cli
strategies/         strategy modules (example_xs_momentum.py is the reference template)
ledger/             strategies.jsonl — the novelty memory (status + prior_art per idea)
runs/               run-XXXX-<UTC>/ manifests + reports + evals, indexed in runs/INDEX.md
research/           pivots, strategy_backlog, data_catalog, progress + charts, portfolio_v1
scripts/            plot_cycle_trends.py, build_risk_managed_portfolio.py
scratch/            throwaway prototyping space for agents (gitignored)
```

## Quick start
```bash
pip install -r requirements.txt && pip install -e .

# Alpha-discovery cycle (orchestrator skill drives the sub-agents):
#   /run-research-cycle      (or: "run a research cycle")
# Risk-managed portfolio:
python scripts/build_risk_managed_portfolio.py
# Cross-cycle progress chart:
python scripts/plot_cycle_trends.py
# Drive the harness directly:
python -m finance_agent.cli evaluate strategies/example_xs_momentum.py --n-trials 1
```

## Design principles
- **Novelty over re-implementation** — combine ideas in *untried* ways (multi-paper fusion,
  papers' "future work", analogical transfer, crossing with our ledger); every idea carries a
  `prior_art` label so re-coded known methods can't masquerade as new.
- **Open-ended ideas, fixed evaluation** — agents freely write new signals and data
  integrations; only the scoring battery is standardized, via the `generate_weights` contract.
- **Adversarial by construction** — a red-team with no stake hunts look-ahead, overfitting,
  OOS decay, regime/survivorship/cost fragility, and runs a **persistence-matched placebo**
  + difference-vs-incumbent significance test (a beyond-VIX signal isn't automatically tradable).
- **Honest statistics** — deflated Sharpe (multiple-testing), honest standard errors
  (non-overlapping / Newey-West), beat-the-right-benchmark.
- **Recoverable** — commit after every stage; status lives in the ledger; resume from disk.

## What we've actually learned (8 cycles, honest)
- **1 validated strategy** (`voltarget_spy`, vol-targeting); the rest correctly rejected.
- The repeatable edge on accessible data is **risk control / drawdown reduction, not
  directional alpha** — see `research/portfolio_v1.md` (trend-overlay portfolio −11% max
  drawdown vs SPY −55%). Where to go next (better data / portfolio framing): `research/pivots.md`.

## Data
Free **yfinance** (no key) by default, cached to `data/cache`; plus a free **FRED** macro
connector and a point-in-time **EDGAR** fundamentals connector. The data moat plan + a
moat-score rubric live in `research/data_catalog.md`.
