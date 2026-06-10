"""Pivot B — assemble and evaluate risk-managed cross-asset portfolios.

Builds three risk-managed variants on the cross-asset ETF universe and compares them to
60/40 and buy-hold SPY on one common span, saving an equity-curve chart + a stats JSON.

Run: python scripts/build_risk_managed_portfolio.py
"""
from __future__ import annotations

import json
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from finance_agent.data import get_prices, load_universe
from finance_agent import portfolio as pf
from finance_agent.backtest import run_backtest

START = "2007-01-01"
COST_BPS = 5.0


def build():
    px = get_prices(load_universe("cross_asset"), start=START).dropna(how="all")

    rp = pf.risk_parity_weights(px, window=63, rebalance=21)
    rp_vt = pf.vol_target(rp, px, target_vol=0.10, window=63)

    # trend overlay: hold only assets with positive 12-month absolute momentum, then vol-target
    mom = (px / px.shift(252) - 1.0)
    mask = (mom > 0).reindex(px.index).ffill().fillna(False)
    trend_rp = (rp * mask).ffill().fillna(0.0)
    trend_rp_vt = pf.vol_target(trend_rp, px, target_vol=0.10, window=63)

    variants = {
        "Risk parity": rp,
        "RP + vol-target (10%)": rp_vt,
        "Trend-RP + vol-target": trend_rp_vt,
        "60/40 (SPY/TLT)": pf.static_weights(px, {"SPY": 0.6, "TLT": 0.4}),
        "Buy-hold SPY": pf.static_weights(px, {"SPY": 1.0}),
    }
    results, curves = {}, {}
    for name, w in variants.items():
        res = run_backtest(px, w, cost_bps=COST_BPS, gross_leverage=None)
        results[name] = res.stats()
        curves[name] = res.equity_curve
    return px, results, curves


def main():
    px, results, curves = build()
    out = Path("research/charts"); out.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(12, 6.5))
    for name, c in curves.items():
        style = "-" if name in ("Trend-RP + vol-target", "RP + vol-target (10%)") else "--"
        lw = 2.2 if name.startswith(("Trend-RP", "RP + vol")) else 1.3
        ax.plot(c.index, c.values, style, lw=lw, label=name)
    ax.set_yscale("log")
    ax.set_title("Pivot B — risk-managed cross-asset portfolios vs 60/40 & SPY\n"
                 f"(growth of $1, {px.index.min().date()}→{px.index.max().date()}, {COST_BPS:.0f}bps, log scale)")
    ax.set_ylabel("growth of $1 (log)"); ax.grid(alpha=0.3, which="both"); ax.legend(fontsize=9)
    fig.tight_layout(); fig.savefig(out / "portfolio_v1.png", dpi=130)

    table = {name: {k: s[k] for k in ("sharpe", "ann_return", "ann_vol",
                                      "max_drawdown", "calmar", "avg_turnover")}
             for name, s in results.items()}
    (out / "portfolio_v1.json").write_text(json.dumps(
        {"start": START, "cost_bps": COST_BPS, "results": table}, indent=2, default=str))

    print(f"{'portfolio':<26}{'Sharpe':>7}{'annRet':>8}{'annVol':>7}{'maxDD':>7}{'Calmar':>7}{'turn':>7}")
    for name, s in results.items():
        print(f"{name:<26}{s['sharpe']:>7.2f}{s['ann_return']*100:>7.1f}%{s['ann_vol']*100:>6.1f}%"
              f"{s['max_drawdown']*100:>6.0f}%{s['calmar']:>7.2f}{s.get('avg_turnover',0):>7.3f}")
    print(f"\nwrote {out/'portfolio_v1.png'} and {out/'portfolio_v1.json'}")


if __name__ == "__main__":
    main()
