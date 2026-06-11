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
| **PIT S&P 500 constituent universe** (`universe.py`) ✅ built | 0 | **free** (no key; GitHub `fja05680/sp500` + Wikipedia fallback) | 1996+ (effective dates) | **removes universe-selection survivorship** — cross-sectional factors run on names actually in the index each date | low (membership) | membership effective-date is PIT; **RESIDUAL price-survivorship**: yfinance lacks ~47% of *exited* names (~73% of full union has prices, ~59% have EDGAR) | **3** |
| Point-in-time fundamentals/constituents (paid superset) | 0 | paid (cheap: Sharadar) | 1998+ | honest value/quality/profitability factors; pre-2009 history + **delisting-complete prices** (fixes the residual gap above) | high | **must be point-in-time** (restatement + filing lag) | 3.5 |
| FINRA short interest | 1 | free | — | crowding/squeeze | med | biweekly, ~settlement lag | 2 |
| Borrow cost/availability | 1 | paid (S3/Markit) | — | short-side feasibility, squeeze | low | as-of dating | 3 |
| **Options surface / dealer positioning** | 2 | paid (ORATS/OptionMetrics) | 2007+ | VRP, skew, gamma/pinning | low–med | surface cleaning; timestamp align | **4** |
| **LLM-on-primary-text** (EDGAR filings/transcripts) | 4 | free text (EDGAR) + LLM | 1994+ | guidance deltas, risk-factor changes, tone | low | **filing-date availability only**; no restated text | **4** |
| Alt-data: cards / foot-traffic / satellite | 3 | paid | varies | revenue nowcasting | low | panel lag + as-of dating | 4 (costly) |
| COT futures positioning | 5 | free (CFTC) | 1986+ | positioning/carry in futures | med | weekly, Tue→Fri release lag | 2 |

## Priorities (where to build the moat)
> **Update (cycle 9):** the EDGAR *data* is point-in-time, but our *ticker list* is today's survivor large-caps — proven to be the binding constraint (the gross-profitability long-only leg's apparent edge was pure survivorship). **Build a point-in-time CONSTITUENT universe** (historical index membership + delistings; free-ish via Wikipedia change logs) BEFORE trusting any cross-sectional fundamental factor.
>
> **Update (Pivot A, phase 3 — built ✅, 2026-06):** the PIT constituent universe is built in `src/finance_agent/universe.py` (membership panel + as-of universe + add/remove event log, 1996→present, 1201 distinct historical tickers, ~24 names churn/yr). The **membership** half of survivorship bias is fixed. **Residual price gap remains:** yfinance covers ~100% of current members but only ~53% of *exited* names (≈73% of the full historical union has prices; ≈59% have EDGAR CIKs). Cross-sectional fundamental factors can now be re-tested honestly **with the price-coverage caveat measured** — a full fix needs delisting-complete prices (CRSP/Sharadar). Consume via `point_in_time_universe(date) ∩ names-with-prices ∩ names-with-EDGAR` at each rebalance, and report how many names you dropped for missing data.

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

## PIT S&P 500 constituent universe — build notes (Pivot A, phase 3, Tier 0)

Code: `src/finance_agent/universe.py` (`get_sp500_changes`, `sp500_membership`,
`point_in_time_universe`, `all_historical_constituents`, `coverage_report`). Wired into
`data.load_universe` via the `"sp500_pit@YYYY-MM-DD"` spec. Tests: `tests/test_universe.py`.

- **Why it's the moat:** EDGAR fundamentals were already PIT by `filed`, but the *ticker list*
  was today's survivors — so every cross-sectional factor was selected on names that survived
  to 2026. This reconstructs **who was actually in the index on each date** (1996→present),
  including delistings/removals, killing the universe-selection survivorship bias.
- **Look-ahead guard:** membership is indexed by the change's **effective date** and forward-
  filled; `point_in_time_universe(asof)` applies only events with `effective_date <= asof`.
  Smoke-verified: Lehman (`LEHMQ`) is in the 2008-06-30 universe, removed 2008-09-17, and
  absent today; Bear Stearns (`BSC`) removed 2008-06-02; Monsanto/Time Warner removed 2018.
- **Source / access:** free, no key. Primary = `fja05680/sp500` GitHub historical-components
  CSV (full as-of member set per change date; we strip the repo's `-YYYYMM` exit suffix and
  normalize `BRK.B`→`BRK-B`) + its `sp500_changes_since_2019.csv` to roll forward. Fallback =
  Wikipedia current table + "Selected changes". Raw downloads cached to `data/cache`; degrades
  to cache then empty when offline. Untrusted web content: only regex-validated date+ticker
  strings are parsed (NaN/empty cells filtered).
- **Smoke result:** event log 2006 rows (1254 adds / 752 removes), 1996-01→2026-06; membership
  panel ~500/date (min 492, median 498, max 506); **1201 distinct historical tickers**; ~24
  names churn/year (≈5%); 699 names exited the index vs 502 current.
- **HONEST LIMITATION — residual price-survivorship (measured, `coverage_report`):**
  membership is PIT, but yfinance lacks many dead tickers. Coverage of the full historical
  union: **~73% have yfinance prices, ~59% have EDGAR CIKs.** Split out: current members
  ~100%/~100%, **exited members only ~53% price / ~30% EDGAR**. Some symbol matches are
  reused tickers (`AL`, `BLL`), so true coverage of the historical *entity* is a touch lower.
  Fully fixing this needs delisting-complete prices (CRSP/Sharadar).

### Factor-sleeve ideas unlocked (handoff → quant-researcher)
- **Re-test gross profitability / earnings-yield on the PIT universe.** At each monthly
  rebalance use `tradable = point_in_time_universe(date) ∩ has-price ∩ has-EDGAR`, rank
  cross-sectionally, dollar-neutral. The honest result is the *change* in the long-leg edge vs
  the old survivor universe — if the cycle-9 gross-profitability edge shrinks/vanishes once
  losers are included, that confirms it was survivorship. Log the count of names dropped for
  missing data each rebalance (it bounds the residual bias).
- **Index-membership event study (mechanism: forced index-fund flows):** the add/remove event
  log enables a clean S&P 500 inclusion/deletion effect study (abnormal return around the
  effective date), and a survivorship *placebo* — re-running any factor on today's-list-only
  vs PIT to quantify how much apparent alpha is pure survivorship.
