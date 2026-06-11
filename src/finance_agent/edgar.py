"""SEC EDGAR XBRL fundamentals — FREE, no API key, point-in-time correct.

This is the **Tier-0 moat foundation** from ``research/pivots.md``: a free, public,
*point-in-time* fundamentals source that lets us build honest cross-sectional equity
factors (value / quality / profitability) without the restatement and look-ahead biases
that quietly invalidate naive backtests.

Why EDGAR for point-in-time
---------------------------
The SEC XBRL "companyconcept" API returns, for every reported datapoint, the **``filed``
date** — the date the value first became public in a filing. That timestamp is exactly
what point-in-time correctness requires: a fundamental value is *knowable* only on/after
its ``filed`` date, never on its period-``end`` date (financials are filed weeks-to-months
after the quarter closes). We therefore index facts by ``filed`` (availability), NEVER by
``end`` (period close).

LOOK-AHEAD GUARANTEE (read this before using the data)
------------------------------------------------------
1. Every fact carries ``filed`` (availability date) and ``end`` (period it describes).
2. A backtest standing on trading date ``D`` may only use facts with ``filed <= D``.
   Use :func:`point_in_time_asof` to enforce this — it returns, per asof-date, the latest
   value whose ``filed <= asof``. Do not join on ``end``.
3. We keep the **FIRST** value filed for each (ticker, concept, period) and drop later
   restatements. This is "as-originally-reported": it reflects what an investor actually
   saw at the time, not a number management revised two years later. Honest, not pretty.

Access / etiquette
------------------
- Endpoints (no key, just a descriptive User-Agent the SEC requires):
    company map : https://www.sec.gov/files/company_tickers.json
    concept     : https://data.sec.gov/api/xbrl/companyconcept/CIK{cik:010d}/{tax}/{concept}.json
- Set ``SEC_USER_AGENT`` env var to "Your Name your-email@example.com". A sensible default
  is used otherwise. The SEC rate-limits at ~10 req/s; we sleep a touch between calls.
- Raw JSON and parsed parquet are cached under ``data/cache``; we degrade gracefully
  (return an empty, correctly-typed frame) if the source is unreachable or offline.

Coverage / limits (be honest)
-----------------------------
- **US filers only** (foreign private issuers filing 20-F have spotty XBRL).
- **XBRL history starts ~2009**; pre-2009 fundamentals are not here.
- **Quarterly / annual cadence** (10-Q / 10-K), not intra-quarter.
- **Concept naming is inconsistent across filers**: e.g. revenue appears as
  ``Revenues``, ``RevenueFromContractWithCustomerExcludingAssessedTax``,
  ``SalesRevenueNet``, etc. :func:`get_edgar_fundamentals` accepts a list of fallback
  concept names per logical field; callers should expect gaps and verify coverage.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Iterable, Sequence

import pandas as pd

CACHE_DIR = Path(os.environ.get("FINANCE_AGENT_CACHE", "data/cache"))

# SEC requires a descriptive User-Agent identifying the requester. Never a secret.
DEFAULT_USER_AGENT = "finance-agent research contact@example.com"
_SEC_RATE_LIMIT_SLEEP = 0.15  # seconds between SEC requests (~<10 req/s, polite)

# Common multi-name fallbacks for logical fields whose XBRL tag varies across filers.
# (Order = preference; first tag with data wins per ticker.)
CONCEPT_FALLBACKS: dict[str, list[str]] = {
    "Revenues": [
        "Revenues",
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "RevenueFromContractWithCustomerIncludingAssessedTax",
        "SalesRevenueNet",
    ],
    "GrossProfit": ["GrossProfit"],
    "NetIncomeLoss": ["NetIncomeLoss"],
    "Assets": ["Assets"],
    "StockholdersEquity": [
        "StockholdersEquity",
        "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",
    ],
    "CostOfRevenue": ["CostOfRevenue", "CostOfGoodsAndServicesSold", "CostOfGoodsSold"],
}


def _cache_path(key: str) -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    safe = key.replace("/", "_").replace(":", "_")
    return CACHE_DIR / f"{safe}.parquet"


def _user_agent() -> str:
    return os.environ.get("SEC_USER_AGENT", DEFAULT_USER_AGENT)


def _sec_get_json(url: str) -> dict | None:
    """GET a SEC JSON endpoint with the required User-Agent; ``None`` on any failure.

    Graceful degradation: network errors / non-200 / bad JSON return ``None`` so callers
    can fall back to cache or empty output rather than crash a backtest.
    """
    try:
        import requests  # imported lazily so the package imports without network

        resp = requests.get(url, headers={"User-Agent": _user_agent()}, timeout=30)
        time.sleep(_SEC_RATE_LIMIT_SLEEP)
        if resp.status_code != 200:
            return None
        return resp.json()
    except Exception:
        return None


# --------------------------------------------------------------------------- #
# 1. ticker <-> CIK map
# --------------------------------------------------------------------------- #
def get_company_tickers(use_cache: bool = True) -> pd.DataFrame:
    """Return the SEC ticker<->CIK map as a DataFrame (FREE, no key).

    Columns: ``ticker`` (upper-case), ``cik`` (int), ``title`` (company name). Cached to
    parquet; degrades to the cached copy (or an empty frame) if the SEC is unreachable.

    The CIK is the join key for every other EDGAR endpoint. Note tickers here use a dot
    (e.g. ``BRK.B``); yfinance uses a dash (``BRK-B``) — :func:`_lookup_cik` normalizes.
    """
    path = _cache_path("edgar_company_tickers")
    if use_cache and path.exists():
        return pd.read_parquet(path)

    data = _sec_get_json("https://www.sec.gov/files/company_tickers.json")
    if data is None:
        if path.exists():
            return pd.read_parquet(path)
        return pd.DataFrame(columns=["ticker", "cik", "title"])

    rows = [
        {"ticker": str(v["ticker"]).upper(), "cik": int(v["cik_str"]), "title": v.get("title", "")}
        for v in data.values()
    ]
    df = pd.DataFrame(rows).drop_duplicates("ticker").reset_index(drop=True)
    if use_cache:
        df.to_parquet(path)
    return df


def _normalize_ticker(ticker: str) -> str:
    return ticker.upper().replace("-", ".").strip()


def _lookup_cik(ticker: str, tickers_df: pd.DataFrame | None = None) -> int | None:
    if tickers_df is None:
        tickers_df = get_company_tickers()
    if tickers_df.empty:
        return None
    t = _normalize_ticker(ticker)
    hit = tickers_df[tickers_df["ticker"] == t]
    if hit.empty:  # also try the raw (dash) form just in case
        hit = tickers_df[tickers_df["ticker"] == ticker.upper().strip()]
    if hit.empty:
        return None
    return int(hit.iloc[0]["cik"])


# --------------------------------------------------------------------------- #
# 2. single XBRL concept -> tidy point-in-time frame
# --------------------------------------------------------------------------- #
_CONCEPT_COLUMNS = ["ticker", "concept", "end", "start", "val", "filed", "fy", "fp", "form", "frame"]


def _empty_concept_frame() -> pd.DataFrame:
    df = pd.DataFrame(columns=_CONCEPT_COLUMNS)
    df["end"] = pd.to_datetime(df["end"])
    df["filed"] = pd.to_datetime(df["filed"])
    return df


def get_edgar_concept(
    ticker: str,
    concept: str,
    taxonomy: str = "us-gaap",
    unit: str = "USD",
    tickers_df: pd.DataFrame | None = None,
    use_cache: bool = True,
) -> pd.DataFrame:
    """Fetch ONE XBRL concept for a ticker as a tidy, point-in-time DataFrame.

    Parameters
    ----------
    ticker : e.g. ``"AAPL"``. Resolved to a CIK via :func:`get_company_tickers`.
    concept : XBRL tag, e.g. ``"NetIncomeLoss"``, ``"Revenues"``, ``"Assets"``,
        ``"StockholdersEquity"``, ``"GrossProfit"``.
    taxonomy : ``"us-gaap"`` (default) or ``"dei"``.
    unit : reporting unit, usually ``"USD"`` (use ``"shares"`` for share counts).

    Returns
    -------
    DataFrame with columns ``[ticker, concept, end, start, val, filed, fy, fp, form, frame]``:
      - ``end``   : period end (the period the value describes) — **do not join on this**.
      - ``filed`` : the date the value became public — **the availability date** you join on.
      - ``val``   : the reported number.
      - ``fy``/``fp``/``form`` : fiscal year, fiscal period (FY/Q1..Q4), filing form.

    Point-in-time discipline
    ------------------------
    Within each ``end`` period we keep the **first** ``filed`` value and drop later
    restatements (sorted by ``filed`` ascending, ``drop_duplicates(keep="first")``). This is
    the as-originally-reported number an investor actually saw. Empty frame on failure.
    """
    cik = _lookup_cik(ticker, tickers_df)
    if cik is None:
        return _empty_concept_frame()

    cache_key = f"edgar_concept_{ticker.upper()}_{taxonomy}_{concept}_{unit}"
    path = _cache_path(cache_key)
    if use_cache and path.exists():
        return pd.read_parquet(path)

    url = (
        f"https://data.sec.gov/api/xbrl/companyconcept/"
        f"CIK{cik:010d}/{taxonomy}/{concept}.json"
    )
    data = _sec_get_json(url)
    if data is None:
        # 404 = filer simply doesn't report this tag; cache the empty result so we don't
        # re-hit the SEC for a known-missing concept. (Only cache empties on a real miss,
        # not a transient network error — but we cannot tell them apart from None alone,
        # so we cache to be polite; callers should clear cache to retry.)
        out = _empty_concept_frame()
        if use_cache:
            out.to_parquet(path)
        return out

    facts = data.get("units", {}).get(unit, [])
    if not facts:
        out = _empty_concept_frame()
        if use_cache:
            out.to_parquet(path)
        return out

    df = pd.DataFrame(facts)
    df["ticker"] = ticker.upper()
    df["concept"] = concept
    for col in ("end", "start", "filed", "fy", "fp", "form", "frame", "val"):
        if col not in df.columns:
            df[col] = pd.NA
    df["end"] = pd.to_datetime(df["end"], errors="coerce")
    df["start"] = pd.to_datetime(df["start"], errors="coerce")
    df["filed"] = pd.to_datetime(df["filed"], errors="coerce")
    df["val"] = pd.to_numeric(df["val"], errors="coerce")

    df = df[_CONCEPT_COLUMNS].dropna(subset=["end", "filed", "val"])
    # POINT-IN-TIME: keep the FIRST filed value per period end (as-originally-reported).
    df = df.sort_values("filed").drop_duplicates(subset=["end"], keep="first")
    df = df.sort_values(["end", "filed"]).reset_index(drop=True)

    if use_cache:
        df.to_parquet(path)
    return df


# --------------------------------------------------------------------------- #
# 3. multi-ticker, multi-concept point-in-time panel
# --------------------------------------------------------------------------- #
def get_edgar_fundamentals(
    tickers: Sequence[str],
    concepts: Iterable[str],
    taxonomy: str = "us-gaap",
    unit: str = "USD",
    use_fallbacks: bool = True,
    use_cache: bool = True,
) -> pd.DataFrame:
    """Build a long-format point-in-time fundamentals panel across tickers & concepts.

    Parameters
    ----------
    tickers : list of symbols, e.g. ``["AAPL", "MSFT", "JNJ"]``.
    concepts : logical fields. If a name is a key in :data:`CONCEPT_FALLBACKS` and
        ``use_fallbacks`` is True, **all** candidate XBRL tags are fetched and *merged*
        across the filer's history (handling cross-filer AND cross-era tag inconsistency,
        e.g. revenue tagged ``Revenues`` pre-2018 vs
        ``RevenueFromContractWithCustomerExcludingAssessedTax`` after ASC 606). Where two
        tags both report the same period ``end``, we keep the value with the **earliest
        ``filed``** (first-reported, preserving point-in-time honesty). The output
        ``concept`` column reports the *logical* name so the panel is uniform.

    Returns
    -------
    Long DataFrame ``[ticker, concept, end, start, val, filed, fy, fp, form, frame]``,
    one row per (ticker, concept, period). Index by ``filed`` for any backtest join —
    see :func:`point_in_time_asof`. Empty frame (correct columns) if nothing resolves.

    Note on coverage: merging synonyms (rather than "first tag with any data wins") is what
    gives revenue a full 2009+ history. Naively taking the first non-empty tag silently
    truncates filers that switched tags mid-history, weakening any revenue-based factor.
    """
    tickers_df = get_company_tickers(use_cache=use_cache)
    frames: list[pd.DataFrame] = []

    for ticker in tickers:
        for logical in concepts:
            candidates = (
                CONCEPT_FALLBACKS.get(logical, [logical]) if use_fallbacks else [logical]
            )
            tag_frames = []
            for tag in candidates:
                df = get_edgar_concept(
                    ticker, tag, taxonomy=taxonomy, unit=unit,
                    tickers_df=tickers_df, use_cache=use_cache,
                )
                if not df.empty:
                    tag_frames.append(df)
            if not tag_frames:
                continue
            merged = pd.concat(tag_frames, ignore_index=True)
            merged["concept"] = logical  # report the logical name, not the raw tag
            # POINT-IN-TIME merge across synonym tags: per period end keep the earliest
            # filed value (as-originally-reported), regardless of which tag carried it.
            merged = (
                merged.sort_values("filed")
                .drop_duplicates(subset=["end"], keep="first")
                .reset_index(drop=True)
            )
            frames.append(merged)

    if not frames:
        return _empty_concept_frame()
    panel = pd.concat(frames, ignore_index=True)
    return panel.sort_values(["ticker", "concept", "end", "filed"]).reset_index(drop=True)


# --------------------------------------------------------------------------- #
# 4. THE look-ahead guard: as-of join on the availability (`filed`) date
# --------------------------------------------------------------------------- #
def point_in_time_asof(
    panel: pd.DataFrame,
    dates: Sequence,
    value_col: str = "val",
) -> pd.DataFrame:
    """Point-in-time as-of view: latest value KNOWN (``filed`` <= date) at each date.

    THIS IS THE LOOK-AHEAD GUARD. For every (ticker, concept) and every requested trading
    ``date``, it returns the most recent reported value whose **``filed`` <= date**. A
    backtest standing on ``date`` therefore only ever sees fundamentals that were already
    public — never a number filed in the future, never a later restatement (the panel
    already holds first-reported values from :func:`get_edgar_concept`).

    Parameters
    ----------
    panel : long output of :func:`get_edgar_fundamentals` / :func:`get_edgar_concept`,
        carrying ``ticker``, ``concept``, ``filed``, and ``value_col``.
    dates : the trading grid (anything ``pd.to_datetime`` accepts). Typically your price
        index. The result is forward-filled in availability time, so a value persists at
        each date until a newer filing supersedes it.

    Returns
    -------
    Wide DataFrame indexed by ``date`` with a MultiIndex column ``(ticker, concept)`` of
    the as-of values. NaN where nothing had been filed yet at that date.

    Example
    -------
    >>> panel = get_edgar_fundamentals(["AAPL"], ["NetIncomeLoss"])
    >>> px = get_prices(["AAPL"])              # doctest: +SKIP
    >>> ni = point_in_time_asof(panel, px.index)   # doctest: +SKIP
    >>> # ni["AAPL"]["NetIncomeLoss"].loc[D] is the latest NI filed on/before D
    """
    grid = pd.DatetimeIndex(pd.to_datetime(list(dates))).sort_values().unique()
    grid = pd.DatetimeIndex(grid)
    if panel is None or panel.empty:
        return pd.DataFrame(index=grid)

    out = {}
    p = panel.dropna(subset=["filed"]).copy()
    p["filed"] = pd.to_datetime(p["filed"])
    for (ticker, concept), grp in p.groupby(["ticker", "concept"]):
        # One observation per availability date: if several facts were filed the same day,
        # keep the one for the latest period end (most recent information that day).
        grp = grp.sort_values(["filed", "end"]).drop_duplicates("filed", keep="last")
        s = pd.Series(grp[value_col].values, index=pd.to_datetime(grp["filed"].values))
        s = s[~s.index.duplicated(keep="last")].sort_index()
        # as-of / forward-fill in availability time onto the trading grid: each date gets
        # the latest value with filed <= date (reindex+ffill == backward as-of search).
        aligned = s.reindex(s.index.union(grid)).ffill().reindex(grid)
        out[(ticker, concept)] = aligned

    wide = pd.DataFrame(out)
    wide.index.name = "date"
    if not wide.empty:
        wide.columns = pd.MultiIndex.from_tuples(wide.columns, names=["ticker", "concept"])
    return wide


# Convenience: a small set of fundamentals concepts useful for value/quality factors.
CORE_CONCEPTS: list[str] = [
    "Revenues",
    "GrossProfit",
    "CostOfRevenue",
    "NetIncomeLoss",
    "Assets",
    "StockholdersEquity",
]
