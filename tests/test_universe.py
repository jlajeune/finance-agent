"""Tests for the point-in-time S&P 500 constituent universe.

Two kinds of tests:
  - **Offline / synthetic** (always run): the look-ahead logic that silently breaks backtests
    if wrong — event-log diffing, as-of membership reconstruction, and that
    :func:`point_in_time_universe` never applies a future change.
  - **Network smoke** (skipped gracefully if GitHub/Wikipedia is unreachable): a tiny live
    fetch confirming ~500 members/date, ~1000+ distinct historical tickers, and that a known
    exited name (Lehman) is in the 2008 universe but not today's.
"""

import pandas as pd
import pytest

from finance_agent import universe as u


# --------------------------------------------------------------------------- #
# Offline look-ahead logic — no network, must always run.
# --------------------------------------------------------------------------- #
def _patch_changes(monkeypatch, df):
    """Force get_sp500_changes() to return a fixed event log (no network)."""
    monkeypatch.setattr(u, "get_sp500_changes", lambda use_cache=True: df.copy())


def _toy_changes():
    # AAA added at start; BBB added 2010, removed 2015; CCC added 2015.
    return pd.DataFrame(
        {
            "date": pd.to_datetime(
                ["2005-01-03", "2010-06-01", "2015-03-01", "2015-03-01"]
            ),
            "ticker": ["AAA", "BBB", "BBB", "CCC"],
            "action": ["add", "add", "remove", "add"],
        }
    )


def test_point_in_time_universe_no_lookahead(monkeypatch):
    _patch_changes(monkeypatch, _toy_changes())
    # Before BBB is added: only AAA.
    assert u.point_in_time_universe("2009-12-31") == ["AAA"]
    # After BBB added, before removal: AAA + BBB (CCC not yet in — no future leak).
    assert u.point_in_time_universe("2012-01-01") == ["AAA", "BBB"]
    # On the swap date BBB out, CCC in.
    assert u.point_in_time_universe("2015-03-01") == ["AAA", "CCC"]
    # Exactly on add date BBB is a member (effective <= asof is inclusive).
    assert "BBB" in u.point_in_time_universe("2010-06-01")
    # One day before, it is not.
    assert "BBB" not in u.point_in_time_universe("2010-05-31")


def test_membership_panel_shape_and_values(monkeypatch):
    _patch_changes(monkeypatch, _toy_changes())
    panel = u.sp500_membership("2008-01-01", "2016-12-31", freq="ME")
    assert panel.dtypes.eq(bool).all()
    # AAA is a member throughout.
    assert panel["AAA"].all()
    # BBB true only between its add and remove.
    bbb = panel["BBB"]
    assert not bbb.loc[:"2010-05-31"].any()
    assert bbb.loc["2010-07-01":"2015-02-01"].all()
    assert not bbb.loc["2015-04-01":].any()
    # CCC only after 2015-03.
    assert not panel["CCC"].loc[:"2015-02-01"].any()
    assert panel["CCC"].loc["2015-04-01":].all()


def test_all_historical_includes_exited(monkeypatch):
    _patch_changes(monkeypatch, _toy_changes())
    allc = u.all_historical_constituents()
    assert set(allc) == {"AAA", "BBB", "CCC"}  # BBB present though it later exited


def test_empty_changes_degrades(monkeypatch):
    _patch_changes(monkeypatch, pd.DataFrame(columns=["date", "ticker", "action"]))
    assert u.point_in_time_universe("2020-01-01") == []
    assert u.sp500_membership("2020-01-01", "2020-12-31", freq="ME").empty


def test_parse_member_symbol():
    assert u._parse_member_symbol("FRX-201406") == "FRX"   # strip exit suffix
    assert u._parse_member_symbol("AAPL") == "AAPL"
    assert u._parse_member_symbol("BRK.B") == "BRK-B"       # dot -> dash (yfinance)
    assert u._parse_member_symbol("nan") is None           # guard NaN cells
    assert u._parse_member_symbol("") is None


# --------------------------------------------------------------------------- #
# Network smoke — skipped gracefully if the source is unreachable.
# --------------------------------------------------------------------------- #
def test_live_membership_smoke():
    changes = u.get_sp500_changes()
    if changes.empty:
        pytest.skip("S&P 500 source unreachable (offline) — skipping live smoke")
    panel = u.sp500_membership("2005-01-01", "2024-12-31", freq="ME")
    sizes = panel.sum(axis=1)
    # ~500 members per date.
    assert 480 <= sizes.median() <= 515
    # Lots of churn => 1000+ distinct historical names.
    assert panel.shape[1] >= 1000
    # A famous exit: Lehman (LEHMQ) was in the 2008 index but not today's.
    universe_2008 = set(u.point_in_time_universe("2008-06-30"))
    universe_now = set(u.point_in_time_universe("2026-01-01"))
    assert "LEHMQ" in universe_2008
    assert "LEHMQ" not in universe_now
