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


def load_universe(name_or_list: str | Iterable[str] = "default") -> list[str]:
    """Resolve a universe spec into a concrete ticker list.

    Pass ``"default"`` for :data:`DEFAULT_UNIVERSE`, a path to a newline- or
    comma-delimited file, or an explicit iterable of symbols.
    """
    if isinstance(name_or_list, str):
        if name_or_list == "default":
            return list(DEFAULT_UNIVERSE)
        p = Path(name_or_list)
        if p.exists():
            text = p.read_text()
            sep = "," if "," in text else None
            return [t.strip() for t in (text.split(sep) if sep else text.split()) if t.strip()]
        raise ValueError(f"Unknown universe spec: {name_or_list!r}")
    return [str(t).strip() for t in name_or_list if str(t).strip()]
