# Cycle 1 Research Report

**Date:** 2026-06-07 · **Universe:** 40 large-cap equities + core ETFs (default) ·
**Data:** Yahoo Finance (yfinance), real daily prices 2010-01-04 → 2026-06-05 (4,131 days) ·
**Costs:** 5 bps/turnover · **Execution lag:** 1 day · **n_trials (deflated Sharpe):** 2

> **Research artifact — not investment advice.** The default universe is today's
> large-cap survivors, which embeds material survivorship/selection bias. Backtests are
> not live performance. Past results do not predict the future.

## Executive summary
Two diverse, well-motivated, **look-ahead-clean** strategies were generated in parallel
(one per distinct factor family) and put through the standardized evaluation battery.
**Both were rejected** — neither produced a positive, robust, net-of-cost edge in this
universe. This is a clean negative result and a successful test of the validation
machinery: it did not rubber-stamp plausible-sounding ideas. The most useful output is
*why* each failed, which directly shapes the next cycle.

> Note on provenance: ideas this cycle came from the generators' internal knowledge
> (with real paper citations), **not** live web research — the `lit-scout` agent was not
> run this pass.

## Cycle map
| id | family | net Sharpe | gross Sharpe | OOS Sharpe | deflated-SR pass | avg turnover | verdict |
|---|---|---|---|---|---|---|---|
| `xs_reversal_idio_5d` | short_term_reversal | **-0.35** | +0.22 | -0.48 | ✗ | 0.36 | **REJECT (uneconomic net of cost)** |
| `lowvol_idio_beta_neutral` | low_volatility | **-0.56** | -0.54 | -0.66 | ✗ | 0.009 | **REJECT (no edge in this universe)** |

The two ideas were genuinely distinct (novelty check Jaccard 0.0): a fast, high-turnover
cross-sectional reversal vs. a slow, monthly, beta-neutral idiosyncratic-vol sort. The
diversity mechanism worked.

## Findings per strategy

### 1. `xs_reversal_idio_5d` — idiosyncratic amplitude-weighted reversal
- **The signal is faintly real but uneconomic.** Gross Sharpe is *positive* (+0.22) yet
  net Sharpe is -0.35: a 4.5%/yr cost drag on 0.36 turnover eats the entire edge.
- **Cost sensitivity is decisive:** net Sharpe by cost — 0bps: +0.22, 5bps: -0.35,
  10bps: -0.91, 20bps: -2.01. It only "works" at zero cost. This is exactly the
  strategy's own pre-stated falsification condition #3.
- Out-of-sample Sharpe -0.48 (decay 0.25); subsamples 1/4 positive; max drawdown -49.5%
  on 8% vol is alarmingly large.
- **Verdict: REJECT**, but with a real sharpening path — the gross signal suggests the
  reversal premium exists here; it needs **far lower turnover** (longer holding, trade
  only the largest-amplitude tail, cost-aware/banded rebalancing) to survive costs.

### 2. `lowvol_idio_beta_neutral` — beta-neutral idiosyncratic-vol low-vol
- **No edge even gross** (gross Sharpe -0.54, net -0.56, t-stat -2.28, 0/4 subsamples
  positive). Turnover is tiny (0.009), so this is *not* a cost problem — the signal
  itself points the wrong way in this universe.
- **Root cause = universe/survivorship fit, not a bug.** Among today's mega-cap
  survivors, the highest-idiosyncratic-vol names (NVDA, META, AVGO, TSLA) were the
  biggest *winners* of 2010–2025, so shorting them and longing dull names was a
  structural loser. The low-vol anomaly lives in broad, point-in-time cross-sections
  with small/junk names — which this 40-name survivor universe excludes by construction.
- **Verdict: REJECT for this universe.** The idea is not disproven in general; it was
  given an unfair test. It deserves a re-run on a broad, point-in-time universe before
  any conclusion.

## Current recommendations
**None.** No strategy survived validation, so there are no model-backed picks to publish
this cycle. (Publishing the rejected strategies' latest positions would be misleading.)

## What we learned (feeds cycle 2)
1. **Cost realism is binding.** At 5–10 bps, high-turnover cross-sectional signals on a
   40-name universe struggle. Future generators should design for turnover from the
   start, and the red-team should weight cost sensitivity heavily.
2. **The survivorship-biased universe actively distorts results** — it penalizes the
   low-vol/anti-lottery short leg and flatters momentum-like exposure. This is the single
   biggest threat to validity and should be fixed before trusting any cross-sectional
   anomaly. **Recommended infra change:** add a broader, point-in-time universe option.
3. **Negative results are informative** and were captured in the ledger so cycle 2 won't
   repeat them.

## Proposed seeds for cycle 2
- **Lower-turnover / time-series families** still wide open: `time_series_momentum`,
  `trend_following`, `seasonality_calendar`, `carry`, `cross_asset` (e.g. bond/equity or
  gold/equity risk rotation using TLT/GLD/SPY) — these tolerate costs far better.
- **Re-test low-vol fairly** on a broader, point-in-time universe (infra task first).
- **Dispatch `lit-scout`** next cycle to pull genuinely recent, externally-grounded
  ideas from the web rather than relying on internal knowledge.
- A reversal **revision**: same thesis, re-engineered for ~3–5× lower turnover, to test
  whether the positive gross signal can be made economic.

### TL;DR
- Real data (2010–2026, 40 names), 2 diverse look-ahead-clean strategies, **both rejected**.
- Reversal has a faint *gross* edge destroyed by costs; low-vol fails due to a
  survivorship-biased universe, not a bug.
- Next: fix the universe (point-in-time), favor low-turnover families, and turn on web research.
