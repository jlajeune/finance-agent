"""Data-reliability benchmark — the "agents in biology" lesson applied to our data layer.

Anthropic's *Paving the Way for Agents in Biology* found the agent bottleneck was not
reasoning but **non-deterministic, unauditable data access** (the same query returned
106 / 15 / 5 results). Their fix was a deterministic retrieval layer. Our equivalent
discipline: the data layer must be **boringly reproducible and look-ahead-safe**. These
tests assert exactly that on synthetic data — they always run, no network — so the
point-in-time guard can't silently regress.
"""

from __future__ import annotations

import pandas as pd

from finance_agent.data import _cache_path
from finance_agent.edgar import point_in_time_asof


def _synthetic_panel() -> pd.DataFrame:
    """One ticker/concept (AAPL Revenues), three first-reported facts with known FILED
    dates — the minimal fixture that pins down the as-of / look-ahead behaviour."""
    return pd.DataFrame({
        "ticker": ["AAPL", "AAPL", "AAPL"],
        "concept": ["Revenues", "Revenues", "Revenues"],
        "end": pd.to_datetime(["2020-12-31", "2021-03-31", "2021-06-30"]),
        "filed": pd.to_datetime(["2021-01-28", "2021-04-29", "2021-07-28"]),
        "val": [100.0, 110.0, 120.0],
    })


def test_asof_is_deterministic():
    """Same query -> same answer (the property the biology paper found agents lacked)."""
    panel = _synthetic_panel()
    dates = pd.bdate_range("2020-12-01", "2021-09-01")
    a = point_in_time_asof(panel, dates)
    b = point_in_time_asof(panel, dates)
    pd.testing.assert_frame_equal(a, b)


def test_asof_never_sees_future_filings():
    """The look-ahead guard: at each date only facts with filed <= date are visible."""
    panel = _synthetic_panel()
    dates = pd.to_datetime(["2021-02-01", "2021-04-28", "2021-04-29",
                            "2021-07-27", "2021-07-28"])
    w = point_in_time_asof(panel, dates)[("AAPL", "Revenues")]
    assert w.loc["2021-02-01"] == 100.0    # only the first filing is public
    assert w.loc["2021-04-28"] == 100.0    # DAY BEFORE the 110 filing -> no future peek
    assert w.loc["2021-04-29"] == 110.0    # on the filing date -> updates
    assert w.loc["2021-07-27"] == 110.0    # day before the 120 filing
    assert w.loc["2021-07-28"] == 120.0


def test_asof_nan_before_any_filing():
    """Before the first filing, the value is NaN — never fabricated/back-filled."""
    panel = _synthetic_panel()
    w = point_in_time_asof(panel, pd.to_datetime(["2020-12-15"]))[("AAPL", "Revenues")]
    assert pd.isna(w.iloc[0])


def test_cache_path_is_stable_and_collision_resistant():
    """Cache keys map deterministically to paths; distinct keys -> distinct paths; and
    very long keys (wide universes) stay within the filesystem limit (cycle-10 bug)."""
    k1 = "Close_2010_2026_True_" + "-".join(f"TK{i}" for i in range(800))
    assert _cache_path(k1) == _cache_path(k1)                      # deterministic
    assert _cache_path(k1) != _cache_path(k1 + "X")                # collision-resistant
    assert len(_cache_path(k1).name) <= 255                        # filesystem-safe
