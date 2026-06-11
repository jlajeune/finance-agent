# Pivots: from alpha-hunting to a genuinely useful system

**Context (honest framing).** Eight cycles on free daily price data for liquid US names
produced **one** validated strategy — vol-targeting, which is *risk control, not alpha*. That
is the correct, expected result: this is the most picked-over data in finance. The *research
machine* (look-ahead-safe, adversarial, placebo-tested, reproducible) is the valuable asset.
To make it genuinely useful we should change the **inputs** (better data) and/or the **goal**
(risk-managed portfolio; strategy due-diligence) — not the machine. This doc lays out three
pivots and the skill/agent changes each needs.

---

## Pivot A — Data: what else, paid ideas, and where to build a moat

**Principle.** Durable edge comes from one of: (1) **data others don't have / won't clean**,
(2) **processing common data better**, or (3) **a structural/behavioral mechanism** others
can't or won't arb. Free daily OHLCV gives us none of these. Here's the data map, by tier.

### Tier 0 — Fix what's broken (cheap, do FIRST; not alpha, but makes everything trustworthy)
- **Point-in-time, survivorship-free database**: index constituents as they were, delisting
  returns, restated-vs-as-reported fundamentals. Without this, every cross-sectional backtest
  is quietly biased. Sources: **Sharadar/Nasdaq Data Link (SF1, ~$_low/mo)**, CRSP/Compustat
  (institutional/academic), Tiingo/Stooq for cleaner price history. **Highest ROI per dollar.**
- **Corporate actions, borrow/short data** (FINRA short interest is free; borrow *cost/
  availability* is paid: S3 Partners, IHS Markit) — needed for any realistic shorting.

### Tier 1 — Cross-sectional fundamentals (classic factors, real long-run evidence)
- Point-in-time financials + analyst estimates/revisions (**IBES**), earnings surprise.
- Powers value / quality / profitability / investment / revisions factors — these have
  decades of out-of-sample evidence but **require point-in-time data** (Tier 0) to be honest.
- Mostly *cheap-to-moderate*; the edge is crowded but real and diversifying.

### Tier 2 — Options & dealer positioning (STRONG moat candidate)
- Implied-vol surface, skew, term structure, put/call, **dealer gamma/positioning**, 0DTE flow.
  Sources: **ORATS, CBOE DataShop, OptionMetrics/IvyDB** (academic), some free-ish proxies.
- Why it's a moat: messier and less accessible than price; strong mechanisms (variance risk
  premium, skew, gamma-driven pinning/acceleration); genuinely less crowded than price factors;
  there's real *craft* in cleaning the surface and modeling positioning. **The moat is the
  cleaning + positioning models, not the raw feed.**

### Tier 3 — Alternative data (the real moat territory, paid, pick ONE vertical)
- Card/debit **transaction panels** (revenue nowcasting), **web traffic / app downloads**
  (SimilarWeb, Sensor Tower), **satellite** (parking lots, oil tanks, crops), **foot traffic**
  (Placer.ai), **supply-chain graphs** (Bloomberg SPLC), hiring momentum (job postings),
  consumer reviews, patents.
- Real edges exist here, but they're expensive and high-maintenance. **Don't boil the ocean —
  pick one vertical with a clear thesis** (e.g. consumer/retail via card + foot-traffic, or
  energy via satellite) and go deep.

### Tier 4 — LLM-processed primary text (the moat that fits an AI-native team)
- Filings (10-K/Q, 8-K), earnings-call transcripts, regulatory text, news. The moat is **not**
  generic "sentiment" (commoditized) but **specific structured extraction**: guidance changes,
  risk-factor deltas year-over-year, management-tone shifts, supply-chain mentions, litigation.
- This is newly tractable *because* we're AI-native — our comparative advantage. Sources:
  **SEC EDGAR (free)**, transcript vendors (paid), news APIs. The moat is the pipeline + the
  exact signals we extract, validated with the same placebo/honest-SE discipline.

### Tier 5 — Macro / cross-asset (accessible, where risk-managed allocation lives)
- **FRED (free)** macro, futures, FX, credit spreads, commodity term structure, COT positioning
  (free CFTC). Powers cross-asset carry/trend/risk-rotation — the raw material for Pivot B.

### Recommended data-moat priorities (ranked)
1. **Tier 0 point-in-time DB** — cheap, unlocks honest cross-sectional work. Do first.
2. **Tier 4 LLM-on-primary-text** — our structural advantage; novel, not yet commoditized.
3. **Tier 2 options/positioning** — strong mechanisms, real craft, semi-accessible.
4. **One Tier 3 vertical** — only after 1–3 prove the loop, and with a clear thesis.

---

## Pivot B — The risk-managed portfolio (the "safe, smart car")

We keep rediscovering that **risk control works and directional alpha doesn't** (on this data).
So make *that* the product instead of fighting it.

**What it is:** a diversified, cross-asset, risk-targeted portfolio built from liquid ETFs
(equity indices, Treasuries, credit, gold, commodities, int'l) — combining the things that are
robustly real:
- **Vol-targeting** (our validated winner) at the portfolio level.
- **Risk parity / inverse-vol** weighting across assets (cycle-3 red-team even found a plain
  inverse-vol RP basket beat 60/40 — Sharpe ~1.0).
- **Time-series trend / absolute-momentum overlay** for crash de-risking.
- **Diversification across uncorrelated streams** + drawdown-aware sizing.

**What it produces:** not "beat the S&P on return," but **S&P-like-or-better *risk-adjusted*
returns with materially smaller drawdowns** — an all-weather / managed-futures-lite profile.
Honest, defensible, and scalable (liquid, capacity-friendly).

**The reframe:** treat each *surviving* strategy as a **sleeve**; the deliverable is the
**combined portfolio**, allocated by risk — not any single magic signal. The ledger of
validated sleeves becomes the input to a portfolio constructor. We're already ~80% here.

---

## Pivot C — Strategy due-diligence mode (the red-team as a product)

Our red-team is the crown jewel — it correctly killed two famous *published* methods (Absorption
Ratio, Zumbach). Point it at **someone else's** strategy claim (a paper, a vendor, a blog) and
have it honestly try to break it: reproduce, placebo, cost-stress, beyond-benchmark, honest SEs.
This is genuinely valuable as a tool/service and needs almost no new infra — just an entry point
that ingests an external strategy spec.

---

## Adapting the skills & agents to these goals

| New goal | Agent / skill change |
|---|---|
| **Better data** | New **`data-engineer`** agent + grow `data.py` into typed connectors (point-in-time DB, options, EDGAR/LLM-text, FRED). A **`add-data-source`** skill with a look-ahead-safe + caching checklist. A **data catalog** artifact (`research/data_catalog.md`) + a **data-moat rubric** (coverage, cost, mechanism, crowding, our edge). |
| **Use data well** | `lit-scout` gains a **data-scouting** mandate: "which dataset unlocks which mechanism?" `quant-researcher` gets data-aware (declare required dataset + whether it's a moat in `SPEC`). |
| **Risk-managed portfolio** | New **`portfolio-constructor`** agent + harness support for **multi-asset risk-parity / vol-target / sleeve-combination** and a **portfolio backtest** (allocate across validated sleeves, walk-forward). New skill **`build-risk-managed-portfolio`**. Reporter shifts from "did we find alpha" → "portfolio risk/return/drawdown profile vs 60-40 / risk-parity." |
| **Realism** | Backtester/harness upgrades: **point-in-time universe**, **realistic costs** (slippage + market impact + borrow), **capacity analysis**, paper-trading/live-data hook. |
| **Due-diligence mode** | A **`vet-external-strategy`** skill: ingest an external spec → backtester + red-team (placebo/cost/beyond-benchmark) → verdict report. |
| **Orchestration** | `run-research-cycle` gains **modes**: (a) alpha-discovery [current], (b) **portfolio-assembly**, (c) **due-diligence**. The ledger already supports `status: shipped` for sleeves promoted into the portfolio. |

---

## Honest cost / effort & recommended sequence
1. **(Cheap, high-ROI) Pivot B + Tier-0 data + realism upgrades** — turn the existing validated
   pieces into a real risk-managed portfolio with honest costs and a point-in-time universe.
   Mostly *harness + portfolio-constructor* work; no expensive data. This is the fastest path to
   something genuinely useful and demo-able.
2. **(Medium) Pivot C due-diligence mode** — small infra, high standalone value.
3. **(Investment) Data moat: Tier-4 LLM-text, then Tier-2 options** — where new, real,
   less-crowded edges actually live; build behind the same placebo/honest-SE discipline.
4. **(Later, thesis-driven) One Tier-3 alt-data vertical.**

> The machine is good. Point it at less-crowded data and a goal it can actually win
> (risk-managed allocation, honest vetting), and it becomes genuinely useful — not just a demo.

*Research artifact — not investment advice.*
