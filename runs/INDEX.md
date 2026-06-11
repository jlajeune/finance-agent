# Research run index

Every row is one research cycle. Click into `runs/<run_id>/` for the manifest,
report, and per-strategy evaluation JSON.

| run_id | cycle | strategies | survived | summary |
|---|---|---|---|---|
| `run-0001-20260607T200935Z` | 1 | 2 | 0 | 2 diverse look-ahead-clean strategies generated in parallel; both REJECTED. Reversal has a real but uneconomic gross edge; low-vol fails due to survivorship-bia |
| `run-0002-20260607T202351Z` | 2 | 1 | 1 | Real web-research cycle. Top lit-scout seed (vol-targeting) implemented and PASSED: same Sharpe as SPY but -14pp drawdown (-24pp and +0.09 Sharpe edge with cris |
| `run-0003-20260608T031721Z` | 3 | 3 | 0 | Cycle 3: 3 diverse candidates (cross_asset / trend_following / seasonality_calendar), all clean & robust but each loses to its own honest passive benchmark -> 0 |
| `run-0004-20260608T181906Z` | 4 | 1 | 0 | User-directed test: can VIX/realized-vol variance risk premium predict next-month SPY direction? Answer: NO. Robust negative on a 194-month OOS sample (VIX-only |
| `run-0005-20260610T140538Z` | 5 | 1 | 0 | Cross-domain build #1 (Absorption Ratio, RMT). REJECT: cuts drawdown but redundant with VIX; the orthogonal-alpha claim was an overlapping-returns t-stat artifa |
| `run-0006-20260610T212239Z` | 6 | 1 | 0 | Model split: 2 Fable agents produced a ranked 10-idea cross-domain backlog (physics+biology); Opus built+self-vetted the top pick (Zumbach vol overlay). REJECTE |
| `run-0007-20260610T213557Z` | 7 | 1 | 0 | B1 path-memory (DFA-Hurst) timer: rejected as standalone (over-de-risks) but the signal is the FIRST cross-domain input to pass the honest beyond-VIX test (t~2- |
| `run-0008-20260610T222300Z` | 8 | 1 | 0 | First novelty-first build: path-memory H_z tilt x vol-target. Looked like a modest PASS but red-team REJECTED - noise, cost-fragile, and fails a persistence-mat |
| `run-0009-20260611T030143Z` | 9 | 1 | 0 | First fundamentals sleeve (gross profitability, point-in-time on EDGAR): REJECTED - L/S dead, placebo p=0.51, long-only is survivorship. The PIT plumbing is val |
