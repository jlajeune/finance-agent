"""Tests for the SEC EDGAR point-in-time fundamentals connector.

Two kinds of tests:
  - **Offline / synthetic** (always run): verify the look-ahead guard in
    :func:`point_in_time_asof` — the one piece that silently breaks backtests if wrong.
  - **Network smoke** (skipped gracefully if the SEC is unreachable / no requests): a
    tiny live fetch on AAPL confirming the data is shaped right and ``filed >= end``.
"""

import pandas as pd
import pytest

from finance_agent import edgar


# --------------------------------------------------------------------------- #
# Offline look-ahead guard — no network, must always run.
# --------------------------------------------------------------------------- #
def _toy_panel():
    """A two-fact panel: a value filed 2020-05-15 for the Q ending 2020-03-31, then a
    restatement-style newer value filed 2020-11-10 for the Q ending 2020-09-30."""
    return pd.DataFrame(
        {
            "ticker": ["AAA", "AAA"],
            "concept": ["Assets", "Assets"],
            "end": pd.to_datetime(["2020-03-31", "2020-09-30"]),
            "start": pd.to_datetime([pd.NaT, pd.NaT]),
            "val": [100.0, 120.0],
            "filed": pd.to_datetime(["2020-05-15", "2020-11-10"]),
            "fy": [2020, 2020],
            "fp": ["Q1", "Q3"],
            "form": ["10-Q", "10-Q"],
            "frame": [pd.NA, pd.NA],
        }
    )


def test_point_in_time_asof_no_lookahead():
    panel = _toy_panel()
    dates = pd.to_datetime(
        ["2020-01-01", "2020-05-14", "2020-05-15", "2020-09-30", "2020-11-09", "2020-11-10"]
    )
    pit = edgar.point_in_time_asof(panel, dates)
    s = pit[("AAA", "Assets")]

    # Before the first filing: nothing is known -> NaN (never fabricate / peek).
    assert pd.isna(s.loc["2020-01-01"])
    # The day BEFORE the 05-15 filing: still NaN even though the period (Q1) already ended.
    assert pd.isna(s.loc["2020-05-14"])
    # On the filing date: the value becomes available.
    assert s.loc["2020-05-15"] == 100.0
    # 2020-09-30 is the Q3 period END but it was not FILED until 11-10 -> must still be 100.
    assert s.loc["2020-09-30"] == 100.0
    assert s.loc["2020-11-09"] == 100.0
    # On/after the 11-10 filing the newer value appears.
    assert s.loc["2020-11-10"] == 120.0


def test_point_in_time_asof_empty_panel():
    out = edgar.point_in_time_asof(edgar._empty_concept_frame(), pd.bdate_range("2020", periods=5))
    assert out.empty
    assert len(out.index) == 5  # still indexed by the requested grid


# --------------------------------------------------------------------------- #
# Live smoke — skips gracefully if SEC is unreachable.
# --------------------------------------------------------------------------- #
def test_edgar_live_smoke_filed_after_end():
    tickers = edgar.get_company_tickers()
    if tickers.empty:
        pytest.skip("SEC unreachable / no cache — skipping live EDGAR smoke test")

    df = edgar.get_edgar_concept("AAPL", "Assets")
    if df.empty:
        pytest.skip("SEC concept fetch returned empty (offline?) — skipping")

    # Core point-in-time invariant: every value is filed on/after the period it describes.
    assert (df["filed"] >= df["end"]).all()
    # First-reported discipline: one row per period end.
    assert df["end"].is_unique
    assert {"end", "val", "filed"}.issubset(df.columns)
