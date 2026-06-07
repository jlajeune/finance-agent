---
name: backtest-harness
description: Reference for the finance_agent backtest/validation harness — the standardized yardstick used to score and compare strategies. Use when implementing a strategy, running an evaluation, or interpreting metrics. The harness is the common measuring stick; you are free to build new signal code, scripts, and data integrations around it.
---

# The backtest harness (the shared yardstick)

The Python harness exists so **every** strategy is scored the same auditable way and
results are comparable across a cycle. It is intentionally small and readable. It is a
**yardstick, not a cage**: build whatever new signal code, scripts, or data integrations
you need — just funnel the final strategy through this contract so it can be compared
fairly and checked for look-ahead bias.

## The contract
A strategy is a file under `strategies/` exposing:
- `SPEC: StrategySpec` — metadata (id, thesis, taxonomy, feature_families, params, references).
- `generate_weights(prices, **params) -> DataFrame` — target weights (dates x tickers),
  longs positive, shorts negative, using only data up to each row's date.

The engine (`finance_agent.backtest.run_backtest`) shifts weights by `execution_lag`
(default 1 day) and charges `cost_bps` per unit turnover, so look-ahead and free churn
are structurally prevented.

## Common commands
```bash
# Coarse diversity signal for generators (which families are crowded this cycle)
python -m finance_agent.cli diversity --cycle N

# Duplicate check for a proposed thesis
python -m finance_agent.cli novelty --thesis "..." --taxonomy cross_sectional_momentum

# Full evaluation battery (headline + OOS + subsample + cost + deflated Sharpe + picks)
python -m finance_agent.cli evaluate strategies/<id>.py --n-trials K --out reports/eval_<id>.json

# Register / update a strategy in the novelty ledger
python -m finance_agent.cli ledger-add --id <id> --thesis "..." --taxonomy <fam> --cycle N --status proposed
python -m finance_agent.cli ledger-list
```

## Interpreting metrics (rules of thumb)
- **Net Sharpe** is after costs; always compare to gross to see cost drag.
- **sharpe_decay** (IS minus OOS) large & positive ⇒ overfit.
- **deflated_sharpe_prob** must clear ~0.95 given the TRUE number of variants searched
  (`n_trials`); passing 1 is cheating the test.
- **cost_sensitivity** — edge should survive ~10-20 bps to be plausibly tradeable.
- A Sharpe > 3, near-zero drawdown, or a monotonic equity curve almost always means a
  bug or a leak — treat as suspect, not success.

## Extending the harness (encouraged)
You are NOT limited to prices/volume. To test a new idea you may, for example:
- Add a fetcher to `src/finance_agent/data.py` (or a new module) for FRED macro, EDGAR
  filings, options-implied vol, Google Trends, Wikipedia/GDELT, crypto on-chain, or a
  social API like Twitter/X — cache it under `data/cache` and expose it look-ahead-safe.
- Write throwaway research scripts under `scratch/` for exploration.
- Add new metrics to `metrics.py` or new robustness checks to `validation.py`.
Keep two invariants: (1) signals use only past data; (2) the final strategy still
implements the `generate_weights` contract so the standardized evaluation applies.
List any new data dependency in the strategy's `SPEC.feature_families` and note required
API keys/env vars so others can reproduce it.
