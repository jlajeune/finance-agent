"""Point-in-time S&P 500 CONSTITUENT universe — FREE, look-ahead-safe.

This is **Pivot A, phase 3** from ``research/data_catalog.md`` — the #1 priority flagged
in cycle 9. EDGAR fundamentals are already point-in-time by ``filed`` date, but the
*ticker list* we ran factors on was today's surviving large-caps. That is a forward-looking
universe-selection bias: a name only appears in the test if it survived to today, so any
cross-sectional factor (e.g. the cycle-9 gross-profitability long leg) looks good purely
because losers/delistings were never in the sample. This module fixes the *membership*
half of survivorship bias by reconstructing **who was actually in the index on each date**.

What this gives you
-------------------
- :func:`get_sp500_changes` — a tidy add/remove **event log** (date, ticker, action).
- :func:`sp500_membership` — a (dates x tickers) **boolean** panel: True where a ticker was
  an index member on that date.
- :func:`point_in_time_universe` — the **list of members as-of a date** (the look-ahead
  guard: only changes effective on/before ``asof`` are applied).

LOOK-AHEAD GUARANTEE (read before using)
----------------------------------------
Index membership changes on its **effective date** (the day S&P actually adds/removes the
name, ~1-5 business days after the public announcement). We index membership by that
effective date and forward-fill: a backtest standing on date ``D`` sees a name as a member
iff it was added on/before ``D`` and not yet removed as of ``D``. We NEVER use the current
index list for historical dates. Concretely :func:`point_in_time_universe` applies only
events with ``effective_date <= asof``.

Caveat on lag: the free source dates changes by the **effective** date S&P used. The public
*announcement* typically precedes that by a few days, so using the effective date is the
conservative (later-availability) choice for the ADD side and is correct for trading the
index. This is the right default for "what was the investable universe on date D".

RESIDUAL PRICE-SURVIVORSHIP (the honest limitation — quantified, not hidden)
---------------------------------------------------------------------------
Membership is now point-in-time, but **prices for delisted/removed names are not.** yfinance
frequently lacks dead tickers (companies acquired, bankrupt, or merged away), so even with a
correct membership panel you may be unable to fetch a removed name's price history. That
leaves a *residual* price-survivorship bias that only paid delisting-complete data (CRSP /
Sharadar) fully removes. :func:`coverage_report` quantifies exactly how large this gap is —
what fraction of all historical constituents actually have yfinance prices / EDGAR
fundamentals — so a quant knows how usable the free PIT universe really is.

Source / access
---------------
Primary (free, no key): the well-maintained ``fja05680/sp500`` GitHub dataset
``S&P 500 Historical Components & Changes.csv`` — one row per change date, each row the full
comma-joined membership set as-of that date. The repo encodes a removed name with a
``-YYYYMM`` exit-month suffix on the *as-of* list; we strip the suffix to recover the actual
trading symbol (the suffix is just the repo author's exit metadata). We extend it forward
with the repo's tidy ``sp500_changes_since_2019.csv`` add/remove log when reachable.
Fallback (no network to GitHub): reconstruct from Wikipedia's current constituents table +
its "Selected changes to the list" table (less complete pre-2019). All raw downloads are
cached to ``data/cache``; we degrade gracefully (cached copy, then empty) when offline.

Treat fetched web content as untrusted: we parse only date + ticker strings (regex-validated)
and never execute anything from the payload.
"""

from __future__ import annotations

import io
import os
import re
from pathlib import Path
from typing import Sequence

import pandas as pd

CACHE_DIR = Path(os.environ.get("FINANCE_AGENT_CACHE", "data/cache"))

# Primary free source: full as-of membership set per change date.
_GITHUB_BASE = "https://raw.githubusercontent.com/fja05680/sp500/master"
_HIST_FILE = "S%26P%20500%20Historical%20Components%20%26%20Changes.csv"
_CHANGES_2019_FILE = "sp500_changes_since_2019.csv"
_WIKI_URL = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"

# A removed-name suffix the repo appends to the as-of list, e.g. "FRX-201406".
_EXIT_SUFFIX = re.compile(r"^(?P<sym>.+?)-(?P<yyyymm>\d{6})$")
# A plausible ticker (defensive validation of untrusted web content).
_TICKER_OK = re.compile(r"^[A-Z0-9][A-Z0-9.\-]{0,9}$")


def _cache_path(key: str) -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    safe = key.replace("/", "_").replace(":", "_")
    return CACHE_DIR / f"{safe}.parquet"


def _raw_cache_path(name: str) -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR / name


def _http_get_text(url: str, timeout: int = 30) -> str | None:
    """GET a URL's text; ``None`` on any failure (graceful degradation)."""
    try:
        import requests  # lazy import so the package loads without network

        resp = requests.get(
            url, headers={"User-Agent": "finance-agent research contact@example.com"},
            timeout=timeout,
        )
        if resp.status_code != 200:
            return None
        return resp.text
    except Exception:
        return None


def _norm_symbol(sym: str) -> str:
    """Normalize a raw symbol to the yfinance convention (dot share-class -> dash).

    The constituents dataset uses dots (``BRK.B``, ``BF.B``); yfinance uses dashes
    (``BRK-B``). We normalize to dashes so downstream price joins line up.
    """
    sym = sym.strip().upper()
    return sym.replace(".", "-")


def _parse_member_symbol(token: str) -> str | None:
    """Strip the repo's ``-YYYYMM`` exit-month suffix and validate the symbol.

    ``"FRX-201406"`` -> ``"FRX"``; ``"AAPL"`` -> ``"AAPL"``. Returns ``None`` if the token
    does not look like a ticker (defensive against malformed/untrusted payload rows).
    """
    token = token.strip()
    # Guard against empty / pandas-NaN cells in the add/remove log (one-sided change rows
    # leave the other column blank, which read_csv yields as the literal "nan").
    if not token or token.lower() in {"nan", "na", "none", "null"}:
        return None
    m = _EXIT_SUFFIX.match(token)
    sym = m.group("sym") if m else token
    sym = _norm_symbol(sym)
    if not _TICKER_OK.match(sym):
        return None
    return sym


# --------------------------------------------------------------------------- #
# 1. Raw as-of membership sets (per change date)
# --------------------------------------------------------------------------- #
def _fetch_historical_components(use_cache: bool = True) -> pd.DataFrame:
    """Return a frame ``[date, members(frozenset)]`` of as-of membership per change date.

    Primary GitHub source; falls back to a cached copy, then to Wikipedia reconstruction.
    """
    cache = _raw_cache_path("sp500_historical_components.csv")
    text: str | None = None
    if not (use_cache and cache.exists()):
        text = _http_get_text(f"{_GITHUB_BASE}/{_HIST_FILE}")
        if text is not None:
            try:
                cache.write_text(text)
            except Exception:
                pass
    if text is None and cache.exists():
        text = cache.read_text()

    if text is None:
        return _wikipedia_fallback(use_cache=use_cache)

    df = pd.read_csv(io.StringIO(text))
    if "date" not in df.columns or "tickers" not in df.columns:
        return _wikipedia_fallback(use_cache=use_cache)

    rows = []
    for _, r in df.iterrows():
        d = pd.to_datetime(r["date"], errors="coerce")
        if pd.isna(d):
            continue
        members = {
            s for s in (_parse_member_symbol(t) for t in str(r["tickers"]).split(","))
            if s is not None
        }
        if members:
            rows.append((d.normalize(), frozenset(members)))
    out = pd.DataFrame(rows, columns=["date", "members"]).sort_values("date")
    out = out.drop_duplicates("date", keep="last").reset_index(drop=True)

    # Extend forward with the tidy post-2019 add/remove log when reachable.
    out = _extend_with_changes_log(out, use_cache=use_cache)
    return out


def _extend_with_changes_log(components: pd.DataFrame, use_cache: bool = True) -> pd.DataFrame:
    """Roll the latest as-of set forward using ``sp500_changes_since_2019.csv``.

    The historical-components file stops ~2019; this tidy add/remove log carries membership
    to the present. Each row applies a removal then an addition to the running set, producing
    a fresh as-of snapshot per change date.
    """
    if components.empty:
        return components
    cache = _raw_cache_path("sp500_changes_since_2019.csv")
    text: str | None = None
    if not (use_cache and cache.exists()):
        text = _http_get_text(f"{_GITHUB_BASE}/{_CHANGES_2019_FILE}")
        if text is not None:
            try:
                cache.write_text(text)
            except Exception:
                pass
    if text is None and cache.exists():
        text = cache.read_text()
    if text is None:
        return components

    try:
        log = pd.read_csv(io.StringIO(text))
    except Exception:
        return components
    if not {"date", "add", "remove"}.issubset(log.columns):
        return components

    last_date = components["date"].max()
    running = set(components.iloc[-1]["members"])
    new_rows = []
    for _, r in log.iterrows():
        d = pd.to_datetime(r["date"], errors="coerce")
        if pd.isna(d) or d.normalize() <= last_date:
            continue
        for tok in str(r.get("remove", "")).split(","):
            sym = _parse_member_symbol(tok)
            if sym:
                running.discard(sym)
        for tok in str(r.get("add", "")).split(","):
            sym = _parse_member_symbol(tok)
            if sym:
                running.add(sym)
        new_rows.append((d.normalize(), frozenset(running)))

    if not new_rows:
        return components
    extra = pd.DataFrame(new_rows, columns=["date", "members"])
    out = pd.concat([components, extra], ignore_index=True)
    out = out.drop_duplicates("date", keep="last").sort_values("date").reset_index(drop=True)
    return out


def _wikipedia_fallback(use_cache: bool = True) -> pd.DataFrame:
    """Reconstruct as-of membership from Wikipedia (current table + selected changes).

    Less complete than the GitHub dataset (the changes table only spans recent years), but
    keeps the module usable when GitHub is unreachable. Builds snapshots by walking the
    "Selected changes to the list" table backward from today's constituents.
    """
    text = _http_get_text(_WIKI_URL)
    if text is None:
        return pd.DataFrame(columns=["date", "members"])
    try:
        tables = pd.read_html(io.StringIO(text))
    except Exception:
        return pd.DataFrame(columns=["date", "members"])

    current: set[str] | None = None
    changes: pd.DataFrame | None = None
    for tb in tables:
        cols = {str(c).lower() for c in tb.columns.get_level_values(-1)} if isinstance(
            tb.columns, pd.MultiIndex) else {str(c).lower() for c in tb.columns}
        if current is None and "symbol" in cols:
            sym_col = [c for c in tb.columns if str(c).lower().endswith("symbol")][0]
            current = {
                s for s in (_parse_member_symbol(str(x)) for x in tb[sym_col]) if s
            }
        if changes is None and "added" in cols and "removed" in cols:
            changes = tb

    if not current:
        return pd.DataFrame(columns=["date", "members"])

    today = pd.Timestamp.today().normalize()
    rows = [(today, frozenset(current))]
    if changes is not None:
        flat = changes.copy()
        flat.columns = ["_".join(str(c) for c in tup).lower() if isinstance(tup, tuple)
                        else str(tup).lower() for tup in flat.columns]
        date_c = next((c for c in flat.columns if "date" in c), None)
        add_c = next((c for c in flat.columns if "added" in c and "ticker" in c), None)
        rem_c = next((c for c in flat.columns if "removed" in c and "ticker" in c), None)
        if date_c and add_c and rem_c:
            running = set(current)
            ev = flat[[date_c, add_c, rem_c]].dropna(subset=[date_c])
            ev[date_c] = pd.to_datetime(ev[date_c], errors="coerce")
            ev = ev.dropna(subset=[date_c]).sort_values(date_c, ascending=False)
            for _, r in ev.iterrows():
                add = _parse_member_symbol(str(r[add_c]))
                rem = _parse_member_symbol(str(r[rem_c]))
                # walking backward: undo the change (remove the added, restore the removed)
                if add:
                    running.discard(add)
                if rem:
                    running.add(rem)
                rows.append((pd.to_datetime(r[date_c]).normalize(), frozenset(running)))
    out = pd.DataFrame(rows, columns=["date", "members"]).sort_values("date")
    return out.drop_duplicates("date", keep="last").reset_index(drop=True)


# --------------------------------------------------------------------------- #
# 2. Tidy add/remove EVENT LOG
# --------------------------------------------------------------------------- #
def get_sp500_changes(use_cache: bool = True) -> pd.DataFrame:
    """Return a tidy S&P 500 add/remove **event log** — FREE, look-ahead-safe.

    Returns
    -------
    DataFrame ``[date, ticker, action]`` sorted by date, where ``action`` is ``"add"`` or
    ``"remove"`` and ``date`` is the **effective date** the change took place. Built by
    diffing consecutive as-of membership sets from the free GitHub dataset (a name present
    in snapshot *t* but absent in *t-1* is an ``add`` on date *t*, and vice versa). The very
    first snapshot's members are emitted as ``add`` events on the start date (their true add
    date predates the dataset; treat that start date as a left-censor boundary).

    Look-ahead note: ``date`` is when the membership change is effective, i.e. the first date
    a backtest may act on it. Symbols are normalized to yfinance convention (``BRK-B``).
    """
    key = "sp500_changes_eventlog"
    path = _cache_path(key)
    if use_cache and path.exists():
        return pd.read_parquet(path)

    comp = _fetch_historical_components(use_cache=use_cache)
    if comp.empty:
        empty = pd.DataFrame(columns=["date", "ticker", "action"])
        return empty

    events = []
    prev: frozenset[str] = frozenset()
    for i, row in comp.iterrows():
        cur = row["members"]
        if i == 0:
            for t in sorted(cur):
                events.append((row["date"], t, "add"))
        else:
            for t in sorted(cur - prev):
                events.append((row["date"], t, "add"))
            for t in sorted(prev - cur):
                events.append((row["date"], t, "remove"))
        prev = cur

    out = pd.DataFrame(events, columns=["date", "ticker", "action"])
    out["date"] = pd.to_datetime(out["date"])
    out = out.sort_values(["date", "action", "ticker"]).reset_index(drop=True)
    if use_cache:
        out.to_parquet(path)
    return out


# --------------------------------------------------------------------------- #
# 3. Boolean membership panel on a trading grid
# --------------------------------------------------------------------------- #
def sp500_membership(
    start: str = "2000-01-01",
    end: str | None = None,
    freq: str = "B",
    use_cache: bool = True,
) -> pd.DataFrame:
    """Return a (dates x tickers) BOOLEAN membership panel — True where a member.

    Parameters
    ----------
    start, end : ISO date strings. ``end=None`` => today.
    freq : pandas offset for the grid — ``"B"`` business-day (default) or ``"ME"`` month-end
        (much smaller; the right grid for a monthly-rebalanced cross-sectional factor).

    Construction (look-ahead-safe)
    ------------------------------
    Reconstruct the as-of member set at each change date from the event log, then **forward
    fill** that set onto the trading grid: each grid date carries the membership implied by
    all events with ``effective_date <= date``. No future change ever leaks backward.

    Returns a boolean frame; ``df.sum(axis=1)`` is the index size over time (~500).
    """
    end = end or pd.Timestamp.today().strftime("%Y-%m-%d")
    changes = get_sp500_changes(use_cache=use_cache)
    grid = pd.date_range(start=start, end=end, freq=freq)
    if changes.empty or len(grid) == 0:
        return pd.DataFrame(index=grid)

    # Reconstruct the running member set after each event date.
    changes = changes.sort_values(["date", "action"])  # 'add' < 'remove' alphabetically
    running: set[str] = set()
    snapshots: dict[pd.Timestamp, frozenset[str]] = {}
    for d, grp in changes.groupby("date", sort=True):
        # apply removes first then adds (an add+remove on the same date both take effect)
        for _, r in grp[grp["action"] == "remove"].iterrows():
            running.discard(r["ticker"])
        for _, r in grp[grp["action"] == "add"].iterrows():
            running.add(r["ticker"])
        snapshots[pd.Timestamp(d).normalize()] = frozenset(running)

    snap = pd.Series(snapshots).sort_index()
    all_tickers = sorted({t for s in snap.values for t in s})

    # For each grid date, take the snapshot effective on/before it (backward as-of).
    snap_dates = snap.index
    panel = pd.DataFrame(False, index=grid, columns=all_tickers)
    pos = snap_dates.searchsorted(grid, side="right") - 1  # latest snapshot <= grid date
    for gi, sp_idx in enumerate(pos):
        if sp_idx < 0:
            continue
        members = snap.iloc[sp_idx]
        panel.iloc[gi, [panel.columns.get_loc(t) for t in members]] = True
    panel.index.name = "date"
    return panel


# --------------------------------------------------------------------------- #
# 4. Point-in-time member list as-of a date (THE look-ahead guard)
# --------------------------------------------------------------------------- #
def point_in_time_universe(asof_date, use_cache: bool = True) -> list[str]:
    """Return the list of S&P 500 members **as-of** ``asof_date`` — look-ahead-safe.

    Applies only membership changes with ``effective_date <= asof_date``: a name is in the
    returned list iff it had been added on/before ``asof_date`` and not since removed. This
    is the function a backtest calls at each rebalance to get the *investable* universe on
    that date — never today's survivor list.

    >>> point_in_time_universe("2008-06-30")     # doctest: +SKIP
    ['AAPL', 'ABT', ..., 'LEH', ...]   # includes names later removed (e.g. Lehman)
    """
    asof = pd.Timestamp(asof_date).normalize()
    changes = get_sp500_changes(use_cache=use_cache)
    if changes.empty:
        return []
    eff = changes[changes["date"] <= asof].sort_values(["date", "action"])
    members: set[str] = set()
    for d, grp in eff.groupby("date", sort=True):
        for _, r in grp[grp["action"] == "remove"].iterrows():
            members.discard(r["ticker"])
        for _, r in grp[grp["action"] == "add"].iterrows():
            members.add(r["ticker"])
    return sorted(members)


def all_historical_constituents(use_cache: bool = True) -> list[str]:
    """Union of every ticker that was ever an S&P 500 member in the dataset.

    This is the survivorship-free name set — including delistings/removals — that
    :func:`coverage_report` checks for price/fundamental availability.
    """
    changes = get_sp500_changes(use_cache=use_cache)
    if changes.empty:
        return []
    return sorted(changes["ticker"].unique().tolist())


# --------------------------------------------------------------------------- #
# 5. RESIDUAL price-survivorship — quantify free-data usability
# --------------------------------------------------------------------------- #
def coverage_report(
    tickers: Sequence[str] | None = None,
    price_start: str = "2000-01-01",
    check_edgar: bool = True,
    use_cache: bool = True,
) -> dict:
    """Measure the residual price-survivorship gap of the FREE PIT universe.

    Membership is point-in-time, but yfinance often lacks delisted/removed names. This walks
    the union of historical constituents and reports what fraction have (a) any yfinance
    price history and (b) an EDGAR CIK (proxy for fundamentals availability). The resulting
    coverage % tells a quant how usable the free universe is before paying for CRSP/Sharadar.

    Returns a dict with counts, fractions, and a small sample of missing names. Network is
    used (yfinance per-ticker, EDGAR ticker map); degrades to whatever is reachable.
    """
    if tickers is None:
        tickers = all_historical_constituents(use_cache=use_cache)
    tickers = list(dict.fromkeys(tickers))
    n = len(tickers)
    out: dict = {"n_constituents": n, "tickers": tickers}

    # (a) yfinance price availability
    have_price: list[str] = []
    no_price: list[str] = []
    try:
        import yfinance as yf

        for t in tickers:
            try:
                hist = yf.Ticker(t).history(start=price_start, period="max")
                (have_price if hist is not None and len(hist) > 0 else no_price).append(t)
            except Exception:
                no_price.append(t)
    except Exception:
        out["price_error"] = "yfinance unavailable"
    out["n_with_price"] = len(have_price)
    out["frac_with_price"] = (len(have_price) / n) if n else 0.0
    out["sample_missing_price"] = no_price[:25]

    # (b) EDGAR fundamentals availability (CIK presence is the cheap proxy)
    if check_edgar:
        try:
            from . import edgar

            cmap = edgar.get_company_tickers(use_cache=use_cache)
            known = set(cmap["ticker"]) if not cmap.empty else set()
            # EDGAR uses dots; our tickers use dashes — check both forms.
            def _has_cik(t: str) -> bool:
                return t in known or t.replace("-", ".") in known
            with_edgar = [t for t in tickers if _has_cik(t)]
            out["n_with_edgar"] = len(with_edgar)
            out["frac_with_edgar"] = (len(with_edgar) / n) if n else 0.0
            out["sample_missing_edgar"] = [t for t in tickers if not _has_cik(t)][:25]
        except Exception:
            out["edgar_error"] = "edgar map unavailable"
    return out
