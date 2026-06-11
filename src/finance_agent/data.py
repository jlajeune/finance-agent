"""Historical market data fetching and caching.

Default source is Yahoo Finance via ``yfinance`` (no API key required). Everything
is cached to ``data/cache`` as parquet so repeated backtests are fast and offline.

Look-ahead safety note
----------------------
We return adjusted **close** prices indexed by date. Strategies must form signals
from data up to and including day *t*, and the backtest engine applies a one-day
execution lag (trade at *t+1*) so that a signal computed on day *t*'s close cannot
be traded at day *t*'s close. See :mod:`finance_agent.backtest`.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable, Sequence

import pandas as pd

CACHE_DIR = Path(os.environ.get("FINANCE_AGENT_CACHE", "data/cache"))


def _cache_path(key: str) -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    safe = key.replace("/", "_").replace(":", "_")
    return CACHE_DIR / f"{safe}.parquet"


def get_prices(
    tickers: Sequence[str],
    start: str = "2005-01-01",
    end: str | None = None,
    field: str = "Close",
    auto_adjust: bool = True,
    use_cache: bool = True,
) -> pd.DataFrame:
    """Return a (dates x tickers) DataFrame of one OHLCV field.

    Parameters
    ----------
    tickers : list of symbols, e.g. ["AAPL", "MSFT", "SPY"].
    start, end : ISO date strings. ``end=None`` means "through today".
    field : one of Open/High/Low/Close/Volume. With ``auto_adjust=True`` the
        Close field is split/dividend adjusted (the right default for backtests).
    use_cache : read/write the parquet cache.
    """
    tickers = sorted(set(tickers))
    end = end or pd.Timestamp.today().strftime("%Y-%m-%d")
    key = f"{field}_{start}_{end}_{auto_adjust}_{'-'.join(tickers)}"
    path = _cache_path(key)

    if use_cache and path.exists():
        return pd.read_parquet(path)

    import yfinance as yf  # imported lazily so the package imports without network

    raw = yf.download(
        tickers=list(tickers),
        start=start,
        end=end,
        auto_adjust=auto_adjust,
        progress=False,
        group_by="column",
    )

    # yfinance returns a column MultiIndex (field, ticker) for multiple symbols and a
    # flat frame for a single symbol. Normalize to (dates x tickers).
    if isinstance(raw.columns, pd.MultiIndex):
        df = raw[field].copy()
    else:
        df = raw[[field]].copy()
        df.columns = tickers

    df = df.sort_index().dropna(how="all")
    if use_cache:
        df.to_parquet(path)
    return df


def get_returns(prices: pd.DataFrame, kind: str = "simple") -> pd.DataFrame:
    """Daily returns from a price panel. ``kind`` is 'simple' or 'log'."""
    if kind == "log":
        import numpy as np

        return np.log(prices / prices.shift(1))
    return prices.pct_change()


# A small, dependency-free default universe so agents can start immediately.
# (A liquid, sector-diverse slice of large-cap US equities + core ETFs.)
DEFAULT_UNIVERSE: list[str] = [
    "AAPL", "MSFT", "AMZN", "GOOGL", "META", "NVDA", "TSLA", "BRK-B", "JPM", "V",
    "JNJ", "WMT", "PG", "MA", "HD", "XOM", "CVX", "KO", "PEP", "ABBV",
    "BAC", "PFE", "AVGO", "COST", "DIS", "CSCO", "MRK", "ORCL", "ACN", "MCD",
    "SPY", "QQQ", "IWM", "TLT", "GLD", "HYG", "XLF", "XLK", "XLE", "XLV",
]

# A liquid, diversified CROSS-ASSET ETF universe for risk-managed portfolio work
# (Pivot B). Spans US/intl equity, the Treasury curve, credit, inflation, gold, and
# broad commodities — distinct return drivers so risk-parity actually diversifies.
# All have history back to ~2007 on yfinance.
CROSS_ASSET_UNIVERSE: list[str] = [
    "SPY",   # US large-cap equity
    "QQQ",   # US growth/tech equity
    "IWM",   # US small-cap equity
    "EFA",   # developed ex-US equity
    "EEM",   # emerging-market equity
    "TLT",   # long Treasuries
    "IEF",   # intermediate Treasuries
    "LQD",   # investment-grade credit
    "HYG",   # high-yield credit
    "TIP",   # inflation-protected Treasuries
    "GLD",   # gold
    "DBC",   # broad commodities
]


def get_fred(series_ids, start: str = "2000-01-01", end: str | None = None,
             use_cache: bool = True) -> pd.DataFrame:
    """Fetch FRED macro series as a (dates x series) DataFrame — FREE, no API key.

    Uses the public ``fredgraph.csv`` endpoint (e.g. DGS3MO 3-month T-bill, DGS10,
    T10Y2Y, VIXCLS, BAMLH0A0HYM2 HY credit spread, UNRATE, CPIAUCSL). This is the
    Tier-5 macro connector from research/pivots.md — the template for adding more data
    sources look-ahead-safely (values are as-released daily series; align + ffill to your
    trading grid, and beware macro release lags for point-in-time use).
    """
    if isinstance(series_ids, str):
        series_ids = [series_ids]
    end = end or pd.Timestamp.today().strftime("%Y-%m-%d")
    out = {}
    for sid in series_ids:
        path = _cache_path(f"fred_{sid}_{start}_{end}")
        if use_cache and path.exists():
            out[sid] = pd.read_parquet(path)[sid]
            continue
        url = (f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}"
               f"&cosd={start}&coed={end}")
        df = pd.read_csv(url)
        # FRED CSVs use the series id (or 'DATE'/'observation_date') as columns; '.' = NA.
        date_col = df.columns[0]
        val_col = df.columns[1]
        s = pd.to_numeric(df[val_col].replace(".", float("nan")), errors="coerce")
        s.index = pd.to_datetime(df[date_col])
        s.name = sid
        s = s.dropna()
        if use_cache:
            s.to_frame().to_parquet(path)
        out[sid] = s
    return pd.DataFrame(out).sort_index()


def load_universe(name_or_list: str | Iterable[str] = "default") -> list[str]:
    """Resolve a universe spec into a concrete ticker list.

    Accepted specs:
      - ``"default"`` -> :data:`DEFAULT_UNIVERSE` (today's survivor large-caps; NOT PIT).
      - ``"cross_asset"`` -> :data:`CROSS_ASSET_UNIVERSE`.
      - ``"sp500_pit@YYYY-MM-DD"`` -> the **point-in-time** S&P 500 membership *as-of* that
        date (look-ahead-safe; includes names later removed). Use this for honest
        cross-sectional factor tests — it removes the universe-selection survivorship bias.
        Backed by :func:`finance_agent.universe.point_in_time_universe`. Note the residual
        price-survivorship caveat documented there (yfinance lacks many delisted names);
        intersect with names that actually have prices/fundamentals at the rebalance.
      - a path to a newline-/comma-delimited file, or an explicit iterable of symbols.
    """
    if isinstance(name_or_list, str):
        if name_or_list == "default":
            return list(DEFAULT_UNIVERSE)
        if name_or_list == "cross_asset":
            return list(CROSS_ASSET_UNIVERSE)
        if name_or_list.startswith("sp500_pit@"):
            from .universe import point_in_time_universe

            asof = name_or_list.split("@", 1)[1].strip()
            return point_in_time_universe(asof)
        p = Path(name_or_list)
        if p.exists():
            text = p.read_text()
            sep = "," if "," in text else None
            return [t.strip() for t in (text.split(sep) if sep else text.split()) if t.strip()]
        raise ValueError(f"Unknown universe spec: {name_or_list!r}")
    return [str(t).strip() for t in name_or_list if str(t).strip()]
