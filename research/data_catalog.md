# Data catalog & moat rubric

Living catalog of data the system can use, with a **moat score** so we invest where edge
actually lives. See `research/pivots.md` for the strategy. Add sources via the
`add-data-source` skill / `data-engineer` agent.

**Moat score (0–5):** `acquire-difficulty × mechanism-strength × our-processing-edge ÷ crowding`,
judged coarsely. High = worth building around; low = commoditized or weak-mechanism.

| Source | Tier | Access | History | Mechanism unlocked | Crowding | Look-ahead/lag caveat | Moat |
|---|---|---|---|---|---|---|---|
| yfinance OHLCV (equities/ETFs) | 0 | free | 1993+ | price/vol factors | very high | adj-close survivorship in universe | 0.5 |
| **CROSS_ASSET_UNIVERSE** (12 ETFs) | 5 | free | 2007+ | cross-asset risk parity / allocation | med | none (liquid ETFs) | 2 (foundation) |
| **FRED macro** (`get_fred`) ✅ built | 5 | free | varies | rates/credit/macro regime, cross-asset carry | med | **release lag** (prints weeks late) — use later availability | 2 |
| Point-in-time fundamentals/constituents | 0 | paid (cheap: Sharadar) | 1998+ | honest value/quality/profitability factors | high | **must be point-in-time** (restatement + filing lag) | 3.5 |
| FINRA short interest | 1 | free | — | crowding/squeeze | med | biweekly, ~settlement lag | 2 |
| Borrow cost/availability | 1 | paid (S3/Markit) | — | short-side feasibility, squeeze | low | as-of dating | 3 |
| **Options surface / dealer positioning** | 2 | paid (ORATS/OptionMetrics) | 2007+ | VRP, skew, gamma/pinning | low–med | surface cleaning; timestamp align | **4** |
| **LLM-on-primary-text** (EDGAR filings/transcripts) | 4 | free text (EDGAR) + LLM | 1994+ | guidance deltas, risk-factor changes, tone | low | **filing-date availability only**; no restated text | **4** |
| Alt-data: cards / foot-traffic / satellite | 3 | paid | varies | revenue nowcasting | low | panel lag + as-of dating | 4 (costly) |
| COT futures positioning | 5 | free (CFTC) | 1986+ | positioning/carry in futures | med | weekly, Tue→Fri release lag | 2 |

## Priorities (where to build the moat)
1. **Point-in-time DB** — not alpha itself, but makes every cross-sectional backtest honest. Do first.
2. **LLM-on-primary-text** — our AI-native edge; novel, low crowding. Build the extraction pipeline.
3. **Options / dealer positioning** — strong mechanisms, real cleaning craft, semi-accessible.
4. **One alt-data vertical** — only after 1–3, with a clear thesis.

✅ = connector exists in `src/finance_agent/data.py`. Everything carries the standard
discipline downstream: novelty + placebo + beat-the-right-baseline with honest standard errors.
