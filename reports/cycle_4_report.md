# Cycle 4 Report — Volatility → next-month direction (user-directed)

**Date:** 2026-06-08 · **Type:** focused single-hypothesis investigation (user-directed) ·
**Data:** Yahoo Finance (yfinance), real daily prices · implied vol = **VIX only** ·
realized vol = SPY 21/63/126-day · **Sample:** VIX history from 2005; OOS predictions
2010-04 → 2026-05 (194 months) · **Costs:** 5 bps · **Execution lag:** 1 day

> **Research artifact — not investment advice.**

## The question
Can we predict whether **next month's** S&P 500 (SPY) return will be **positive** using
**implied volatility (VIX)** and **realized volatility** at 1/3/6-month horizons? If so,
trade it as a long/flat SPY timer (long when "up" is predicted, else cash).

## The model (`ivrv_monthly_timer`)
- **Features:** the variance risk premium VRP_h = VIX − realized-vol_h for h ∈ {1m, 3m, 6m}
  (per user direction, implied vol is VIX only; the 1/3/6m structure is on the realized side).
- **Mechanism tested:** the VRP is compensation for bearing volatility risk and is
  documented to predict the *equity premium* (Bollerslev-Tauchen-Zhou 2009) — does that
  translate into monthly *directional* skill?
- **Model:** expanding-window walk-forward L2 logistic regression, refit each month on
  data ≤ t (per-date standardization, 60-month minimum training window, no full-sample
  fitting). A univariate VRP rule is run alongside as an overfit guard.

## Result: NO — fails both success bars
**Forecasting skill (OOS, 194 months, up-rate 0.68):**
| Predictor | Accuracy | AUC |
|---|---|---|
| Full logistic (VRP 1/3/6m) | 0.510 | 0.474 |
| Univariate VRP baseline | 0.515 | 0.520 |
| **Always-long benchmark** | **0.680** | 0.500 |

Both the full model and the baseline are **well below the always-long accuracy (0.68)**,
and AUC ≈ 0.5 (no better than a coin flip). Both pre-2015 and post-2015 sub-periods fail.

**Trading P&L:** net Sharpe **0.41 vs buy-and-hold SPY 0.64**; annual return 3.9% vs
10.9%. In the market only ~53% of months, so it gives up the equity premium for no
directional edge.

## Why it fails (honest read)
- Markets are up ~68% of months, so **"always long" is a very hard benchmark** — you have
  to be genuinely skilled at calling the ~32% of down months, and the VRP isn't.
- The VRP's documented predictability is for the **magnitude of the equity premium at a
  quarterly horizon**, not the **sign at a monthly horizon** — this test exposes that
  mismatch. The signal that worked for sizing exposure (cycle-2's `voltarget_spy`) does
  not work for calling monthly direction.

## What we learned / possible next angles
- Predicting the monthly *sign* is the wrong framing for this signal. More promising:
  predict/scale by **return magnitude or volatility** (sizing, not direction), or test a
  **quarterly** horizon where the VRP's predictability is documented.
- The expanding-window, look-ahead-safe ML scaffold and the new **VIX data integration**
  are reusable for future predictive strategies.

## Standing recommendation (unchanged)
Nothing validated this cycle. The only validated strategy remains cycle-2's
`voltarget_spy` (~76% SPY / 24% cash). Not investment advice.
