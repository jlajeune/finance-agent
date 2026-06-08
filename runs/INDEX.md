# Research run index

Every row is one research cycle. Click into `runs/<run_id>/` for the manifest,
report, and per-strategy evaluation JSON.

| run_id | cycle | strategies | survived | summary |
|---|---|---|---|---|
| `run-0001-20260607T200935Z` | 1 | 2 | 0 | 2 diverse look-ahead-clean strategies generated in parallel; both REJECTED. Reversal has a real but uneconomic gross edge; low-vol fails due to survivorship-bia |
| `run-0002-20260607T202351Z` | 2 | 1 | 1 | Real web-research cycle. Top lit-scout seed (vol-targeting) implemented and PASSED: same Sharpe as SPY but -14pp drawdown (-24pp and +0.09 Sharpe edge with cris |
| `run-0003-20260608T031721Z` | 3 | 3 | 0 | Cycle 3: 3 diverse candidates (cross_asset / trend_following / seasonality_calendar), all clean & robust but each loses to its own honest passive benchmark -> 0 |
