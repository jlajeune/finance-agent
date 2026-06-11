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
| **SEC EDGAR XBRL fundamentals** (`get_edgar_fundamentals`) ✅ built | 0 | **free** (no key, just User-Agent) | ~2009+ (XBRL era) | honest value/quality/profitability factors from *as-filed* financials | high (raw numbers) / low (PIT-clean panel) | **point-in-time by `filed` date** — value usable only on/after filing (~20-75d lag); first-reported, restatements dropped; US filers only; tag naming varies across filers | 3.5 |
| Point-in-time fundamentals/constituents (paid superset) | 0 | paid (cheap: Sharadar) | 1998+ | honest value/quality/profitability factors; pre-2009 history + delistings | high | **must be point-in-time** (restatement + filing lag) | 3.5 |
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

✅ = connector exists in `src/finance_agent/data.py` (or a submodule). Everything carries the
standard discipline downstream: novelty + placebo + beat-the-right-baseline with honest SEs.

## SEC EDGAR fundamentals — build notes (Pivot A, Tier 0)

Code: `src/finance_agent/edgar.py` (`get_company_tickers`, `get_edgar_concept`,
`get_edgar_fundamentals`, `point_in_time_asof`). Tests: `tests/test_edgar.py`.

- **Why it's the moat foundation:** every SEC XBRL datapoint carries a `filed` date — the day
  it became *public*. We index by `filed` (availability), never period `end`, and keep the
  **first-reported** value per period (drop later restatements). That kills the two biases that
  silently invalidate fundamental backtests: look-ahead and restatement bias. The moat isn't the
  raw (free) feed — it's the **point-in-time-clean panel** + the `point_in_time_asof` guard.
- **Look-ahead guard:** `point_in_time_asof(panel, dates)` returns, per trading date, the latest
  value with `filed <= date` (backward as-of). Smoke-verified: AAPL Assets flips on the
  2018-11-05 filing date (not the period-end) and is NaN before the first filing.
- **Access:** free, no key; descriptive `User-Agent` (env `SEC_USER_AGENT`, sensible default);
  ~0.15s sleep (SEC caps ~10 req/s). Caches raw JSON + parsed parquet to `data/cache`; degrades
  to empty (never fabricated) when offline.
- **Smoke result (AAPL/MSFT/JNJ, Revenues/NetIncomeLoss/Assets):** 617-row panel, filed range
  2009-07 → 2026-05, **0 rows with `filed < end`**, median filing lag 32 days.
- **Honest limitations:** US filers only; XBRL ~2009+ (no older history); quarterly/annual
  cadence. **Concept tags vary across filers/eras** — e.g. revenue is `Revenues` pre-2018 then
  `RevenueFromContractWithCustomerExcludingAssessedTax` (ASC 606). `get_edgar_fundamentals`
  *merges* synonym tags per period (first-filed wins on overlap), which lifted AAPL revenue
  coverage from ~9 to ~73 periods. Still verify per-name coverage before trusting a factor.

### Factor-sleeve ideas unlocked (handoff → quant-researcher / portfolio-constructor)
Both must be built **only** through `point_in_time_asof` (look-ahead-safe) and clear the usual
bar: beat the right baseline (cap-weighted / equal-weight universe, and a plain value/size
control), pass a placebo (shuffle the `filed` dates → edge must vanish), honest SEs, realistic
costs. Cross-sectionally rank within the liquid universe, monthly rebalance, dollar-neutral.

1. **Gross profitability (Novy-Marx 2013):** `(Revenues − CostOfRevenue) / Assets`, all PIT.
   Strong, decades-old mechanism; diversifies classic book/price value. EDGAR gives every input
   as-filed; `GrossProfit` is also directly tagged for many filers (cross-check the two).
2. **Earnings yield / quality:** trailing-4Q `NetIncomeLoss` as-of `filed`, over market cap
   (price × shares, shares from the `dei`/`us-gaap` share-count tag). Tilt by accruals/ROE
   (`NetIncomeLoss / StockholdersEquity`) for a quality overlay. Becomes an equity sleeve in the
   risk-managed portfolio (Pivot B), sized by risk alongside the validated vol-target sleeve.
