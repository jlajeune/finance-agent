"""Run artifacts — give every research cycle a durable, traceable record in the repo.

Each run gets an ID that is BOTH incrementing and datetime-based, e.g.

    run-0003-20260607T142530Z

so runs sort chronologically, are easy to reference in GitHub, and never collide.
A run directory under ``runs/<run_id>/`` holds the manifest plus copied artifacts
(reports, eval JSONs), and a top-level ``runs/INDEX.md`` table is appended so the
history is reviewable at a glance in a PR.
"""

from __future__ import annotations

import json
import re
import shutil
import time
from pathlib import Path

RUNS_DIR = Path("runs")
INDEX = RUNS_DIR / "INDEX.md"
_RUN_RE = re.compile(r"run-(\d+)-")


def _next_seq() -> int:
    if not RUNS_DIR.exists():
        return 1
    seqs = [int(m.group(1)) for p in RUNS_DIR.iterdir()
            if (m := _RUN_RE.match(p.name))]
    return (max(seqs) + 1) if seqs else 1


def new_run_id(when: float | None = None) -> str:
    """Return a fresh run id: incrementing sequence + UTC timestamp."""
    ts = time.gmtime(when if when is not None else time.time())
    stamp = time.strftime("%Y%m%dT%H%M%SZ", ts)
    return f"run-{_next_seq():04d}-{stamp}"


def record_run(manifest: dict, artifacts: list[str | Path] | None = None,
               run_id: str | None = None) -> Path:
    """Create ``runs/<run_id>/`` with a manifest.json and copied artifacts, and append
    a summary row to ``runs/INDEX.md``. Returns the run directory path.

    ``manifest`` should include at least: cycle, summary, and a ``strategies`` list of
    ``{id, family, net_sharpe, verdict}`` dicts. Anything JSON-serializable is allowed.
    """
    run_id = run_id or new_run_id()
    run_dir = RUNS_DIR / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    manifest = {"run_id": run_id, "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                **manifest}
    copied = []
    for a in artifacts or []:
        a = Path(a)
        if a.exists():
            dest = run_dir / a.name
            shutil.copy2(a, dest)
            copied.append(dest.name)
    manifest["artifacts"] = copied
    (run_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, default=str))

    _append_index(manifest)
    return run_dir


def _append_index(manifest: dict) -> None:
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    if not INDEX.exists():
        INDEX.write_text(
            "# Research run index\n\n"
            "Every row is one research cycle. Click into `runs/<run_id>/` for the manifest,\n"
            "report, and per-strategy evaluation JSON.\n\n"
            "| run_id | cycle | strategies | survived | summary |\n"
            "|---|---|---|---|---|\n"
        )
    strats = manifest.get("strategies", [])
    # Prefer the manifest's explicit survivor count (authoritative). Fall back to counting
    # only verdicts that actually clear the bar — REVISE/REJECT are NOT survivors.
    survived = manifest.get("survivors")
    if survived is None:
        survived = sum(1 for s in strats
                       if str(s.get("verdict", "")).upper().startswith(("PASS", "VALID")))
    summary = str(manifest.get("summary", "")).replace("\n", " ").replace("|", "/")[:160]
    row = f"| `{manifest['run_id']}` | {manifest.get('cycle','')} | {len(strats)} | {survived} | {summary} |\n"
    with INDEX.open("a") as f:
        f.write(row)
