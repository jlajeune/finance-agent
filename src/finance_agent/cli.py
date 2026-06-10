"""Command-line entry point so agents (and humans) can drive the harness without
writing glue code each time.

Examples
--------
    python -m finance_agent.cli diversity --cycle 1
    python -m finance_agent.cli evaluate strategies/example_xs_momentum.py --n-trials 12
    python -m finance_agent.cli ledger-add --id xs_mom_12_1 --thesis "..." \
        --taxonomy cross_sectional_momentum --features price --cycle 1 --status proposed
    python -m finance_agent.cli ledger-list
"""

from __future__ import annotations

import argparse
import json

from . import ledger
from .runner import evaluate, pretty


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="finance_agent")
    sub = p.add_subparsers(dest="cmd", required=True)

    ev = sub.add_parser("evaluate", help="Run the full evaluation battery on a strategy file")
    ev.add_argument("strategy_path")
    ev.add_argument("--start", default="2010-01-01")
    ev.add_argument("--end", default=None)
    ev.add_argument("--cost-bps", type=float, default=5.0)
    ev.add_argument("--n-trials", type=int, default=1,
                    help="How many variants were searched (for deflated Sharpe)")
    ev.add_argument("--out", default=None, help="Write JSON report to this path")

    dv = sub.add_parser("diversity", help="Print the coarse diversity brief for generators")
    dv.add_argument("--cycle", type=int, default=None)

    add = sub.add_parser("ledger-add", help="Append a strategy record to the ledger")
    add.add_argument("--id", required=True)
    add.add_argument("--thesis", required=True)
    add.add_argument("--taxonomy", nargs="+", required=True)
    add.add_argument("--features", nargs="+", default=["price"])
    add.add_argument("--cycle", type=int, default=None)
    add.add_argument("--status", default="proposed",
                     choices=["proposed", "validated", "rejected", "shipped"])
    add.add_argument("--references", nargs="*", default=[])
    add.add_argument("--prior-art", default="unknown",
                     help="none_found | extends: X | reimplements: X (novelty bookkeeping)")
    add.add_argument("--novel-combination", default="",
                     help="one-line 'what x what' unique combination this idea expresses")

    nc = sub.add_parser("novelty", help="Check a proposed thesis for duplication")
    nc.add_argument("--thesis", required=True)
    nc.add_argument("--taxonomy", nargs="+", required=True)
    nc.add_argument("--cycle", type=int, default=None)

    sub.add_parser("ledger-list", help="Dump the ledger as JSON")

    args = p.parse_args(argv)

    if args.cmd == "evaluate":
        report = evaluate(args.strategy_path, start=args.start, end=args.end,
                          cost_bps=args.cost_bps, n_trials=args.n_trials)
        text = pretty(report)
        if args.out:
            with open(args.out, "w") as f:
                f.write(text)
        print(text)
    elif args.cmd == "diversity":
        print(ledger.diversity_brief(cycle=args.cycle))
    elif args.cmd == "ledger-add":
        ledger.record({
            "id": args.id, "thesis": args.thesis, "taxonomy": args.taxonomy,
            "feature_families": args.features, "cycle": args.cycle,
            "status": args.status, "references": args.references,
            "prior_art": args.prior_art, "novel_combination": args.novel_combination,
        })
        print(f"recorded {args.id}")
    elif args.cmd == "novelty":
        print(json.dumps(ledger.novelty_check(args.thesis, args.taxonomy, cycle=args.cycle), indent=2))
    elif args.cmd == "ledger-list":
        print(json.dumps(ledger.load(), indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
