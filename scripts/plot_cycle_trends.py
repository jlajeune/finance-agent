"""Generate a cycle-by-cycle trend chart of key metrics across all strategies.

Honest comparability: every strategy is re-run on ONE common, fully-warmed-up window
(2011-01-01 -> present) at the same cost, so Sharpe/drawdown are directly comparable
across cycles (the per-cycle eval JSONs used different spans). Weights are still built
from 2005 data so long-warmup strategies (DFA, eigen-windows) are live by 2011.

Run: python scripts/plot_cycle_trends.py
"""
from __future__ import annotations

import glob
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from finance_agent import metrics
from finance_agent.data import get_prices, load_universe
from finance_agent.backtest import run_backtest
from finance_agent.runner import load_strategy_module
from finance_agent.ledger import load as load_ledger

COMMON_START = "2011-01-01"   # all strategies are warmed-up & live by here
BUILD_START = "2005-01-01"    # build weights from here for warmup
COST_BPS = 5.0


def latest_status_and_cycle():
    meta = {}
    for e in load_ledger():
        meta[e["id"]] = {"cycle": e.get("cycle"), "status": e.get("status"),
                         "novel": e.get("novel_combination", "")}
    return meta


def strat_metrics(path: str):
    mod = load_strategy_module(path)
    spec = mod.SPEC
    tickers = load_universe(getattr(spec, "universe", "default"))
    prices = get_prices(tickers, start=BUILD_START)
    params = getattr(spec, "params", {}) or {}
    w = mod.generate_weights(prices, **params)
    gl = getattr(spec, "gross_leverage", 1.0)
    res = run_backtest(prices, w, cost_bps=COST_BPS, gross_leverage=gl)
    r = res.returns[res.returns.index >= COMMON_START]
    return spec.id, metrics.sharpe(r), metrics.max_drawdown(r)


def main():
    meta = latest_status_and_cycle()
    rows = []
    for path in sorted(glob.glob("strategies/*.py")):
        if Path(path).stem == "example_xs_momentum":
            continue
        try:
            sid, sh, dd = strat_metrics(path)
        except Exception as exc:  # noqa: BLE001 - one bad strategy shouldn't kill the chart
            print(f"skip {path}: {exc}")
            continue
        m = meta.get(sid, {})
        if m.get("cycle") is None:
            continue
        rows.append({"id": sid, "cycle": m["cycle"], "status": m.get("status", "?"),
                     "sharpe": sh, "maxdd": dd})
    rows.sort(key=lambda x: (x["cycle"], x["id"]))

    # Reference baselines on the SAME common window.
    spy = get_prices(["SPY", "TLT"], start=BUILD_START)
    spy_r = spy["SPY"].pct_change()[lambda s: s.index >= COMMON_START]
    bh_sharpe, bh_dd = metrics.sharpe(spy_r), metrics.max_drawdown(spy_r)
    w6040 = (0.6 * spy["SPY"].pct_change() + 0.4 * spy["TLT"].pct_change())
    w6040 = w6040[w6040.index >= COMMON_START]
    s6040, d6040 = metrics.sharpe(w6040), metrics.max_drawdown(w6040)

    def color(s):
        return {"validated": "#2ca02c", "rejected": "#d62728",
                "shipped": "#1f77b4"}.get(s, "#9467bd")  # purple = proposed/under-review

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 9), sharex=True)
    for r in rows:
        ax1.scatter(r["cycle"], r["sharpe"], c=color(r["status"]), s=90, zorder=3,
                    edgecolors="black", linewidths=0.4)
        ax1.annotate(r["id"], (r["cycle"], r["sharpe"]), fontsize=6.5, rotation=18,
                     xytext=(5, 4), textcoords="offset points")
        ax2.scatter(r["cycle"], r["maxdd"] * 100, c=color(r["status"]), s=90, zorder=3,
                    edgecolors="black", linewidths=0.4)

    ax1.axhline(bh_sharpe, ls="--", c="gray", lw=1, label=f"buy-hold SPY ({bh_sharpe:.2f})")
    ax1.axhline(s6040, ls=":", c="#1f77b4", lw=1.2, label=f"static 60/40 ({s6040:.2f})")
    ax1.set_ylabel("net Sharpe (2011+, 5bps)")
    ax1.set_title("finance-agent — strategies by cycle on a common window\n"
                  "green = validated · red = rejected · purple = under review")
    ax1.grid(alpha=0.3); ax1.legend(fontsize=8, loc="lower left")

    ax2.axhline(bh_dd * 100, ls="--", c="gray", lw=1, label=f"buy-hold SPY ({bh_dd*100:.0f}%)")
    ax2.axhline(d6040 * 100, ls=":", c="#1f77b4", lw=1.2, label=f"static 60/40 ({d6040*100:.0f}%)")
    ax2.set_ylabel("max drawdown (%)"); ax2.set_xlabel("cycle")
    ax2.grid(alpha=0.3); ax2.legend(fontsize=8, loc="lower left")
    ax1.set_xticks(sorted({r["cycle"] for r in rows}))

    plt.tight_layout()
    out = Path("research/charts"); out.mkdir(parents=True, exist_ok=True)
    fig.savefig(out / "cycle_trends.png", dpi=130)
    print(f"wrote {out/'cycle_trends.png'} with {len(rows)} strategies "
          f"(common window {COMMON_START}+, {COST_BPS}bps)")
    # Also dump the underlying numbers for the doc/table.
    (out / "cycle_trends.json").write_text(json.dumps(
        {"common_start": COMMON_START, "cost_bps": COST_BPS,
         "buy_hold_spy": {"sharpe": bh_sharpe, "maxdd": bh_dd},
         "static_6040": {"sharpe": s6040, "maxdd": d6040},
         "strategies": rows}, indent=2))


if __name__ == "__main__":
    main()
