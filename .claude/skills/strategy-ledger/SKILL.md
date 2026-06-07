---
name: strategy-ledger
description: Reference for the strategy ledger — the novelty/diversity memory that keeps parallel and successive cycles exploring DIFFERENT ideas without over-constraining them. Use when assigning lenses, checking novelty, or recording a strategy's status.
---

# The strategy ledger (novelty memory)

`ledger/strategies.jsonl` is an append-only record of every strategy ever attempted. It
is how the system "remembers" what's been tried so it keeps finding new regions of idea
space instead of rediscovering the same factors.

## The diversity-vs-freedom balance (the whole point)
The ledger deliberately exposes only a **coarse** view to idea generators:
- which **taxonomy families** are crowded this cycle (`occupied_regions` / `diversity_brief`), and
- short theses, for a soft duplicate check (`novelty_check`).

It does **not** hand generators the signal formulas or tuned parameters of prior
strategies. Telling a generator "momentum is crowded, value is open" steers diversity;
showing it "here's exactly how the last 5 momentum strategies were built" would anchor
it and kill originality. Always prefer the coarse nudge.

## Usage
```bash
python -m finance_agent.cli diversity --cycle N      # coarse brief for generators
python -m finance_agent.cli novelty --thesis "..." --taxonomy <fam>   # soft dup check
python -m finance_agent.cli ledger-add --id <id> --thesis "..." --taxonomy <fam> \
    --features price volume --cycle N --status proposed|validated|rejected|shipped
python -m finance_agent.cli ledger-list
```
Programmatic: `finance_agent.ledger.{record, load, occupied_regions, novelty_check, diversity_brief}`.

## Conventions
- Record at **proposed** when a strategy file is written; update to **validated** or
  **rejected** after the red-team verdict. This keeps `occupied_regions` honest.
- `taxonomy` values come from `finance_agent.strategy.TAXONOMY`. If a genuinely new
  idea doesn't fit, add a new family there and use it — the taxonomy is meant to grow.
- One `cycle` integer per cycle so each cycle starts with a fresh diversity budget while
  the full cross-cycle history remains for long-term novelty.
- `novelty_check` is a *soft* signal (token-Jaccard over theses sharing a family), not a
  hard gate — use judgment; a real variation that overlaps wording is still allowed.
