"""Tests for the EDGAR filing-TEXT pipeline (LLM-on-primary-text moat, v1 lexicon proxy).

Two kinds:
  - **Offline / synthetic** (always run): the look-ahead guard
    (:func:`point_in_time_asof_text`), the LM tone counter, and the Item-1A slicer on a
    hand-built fake filing — the pieces that silently break backtests if wrong.
  - **Network smoke** (skipped gracefully if the SEC is unreachable / no cache): a tiny live
    fetch on AAPL confirming filings come back and ``filingDate >= reportDate``.
"""

import pandas as pd
import pytest

from finance_agent import edgar_text as et


# --------------------------------------------------------------------------- #
# Offline: LM tone counting.
# --------------------------------------------------------------------------- #
def test_lm_tone_counts_and_densities():
    text = "The company may suffer a loss and litigation could harm results."
    tone = et.lm_tone(text)
    assert tone["word_count"] > 0
    # 'loss', 'harm' -> negative; 'may', 'could' -> uncertainty; 'litigation' -> litigious.
    assert tone["negative_count"] >= 2
    assert tone["uncertainty_count"] >= 2
    assert tone["litigious_count"] >= 1
    assert 0.0 <= tone["negative_density"] <= 1.0


def test_lm_tone_empty():
    tone = et.lm_tone("")
    assert tone["word_count"] == 0.0
    assert tone["negative_density"] == 0.0


# --------------------------------------------------------------------------- #
# Offline: Item 1A slicing on a synthetic filing.
# --------------------------------------------------------------------------- #
def _fake_10k() -> str:
    risk_body = (
        "Our business faces many risks. Adverse market conditions could harm revenue and "
        "result in significant losses. We may fail to compete and litigation could increase "
        "our liabilities. Economic downturn and volatility may decrease demand. "
    ) * 6  # make it comfortably > 50 words
    return (
        "PART I Item 1. Business. We make widgets. "
        "Item 1A. Risk Factors " + risk_body +
        "Item 1B. Unresolved Staff Comments. None. "
        "Item 2. Properties. We lease offices."
    )


def test_extract_risk_factors_found_and_bounded():
    rf = et.extract_risk_factors(_fake_10k())
    assert rf["found"] is True
    assert rf["word_count"] >= 50
    # The slice must stop before Item 1B (no "Unresolved Staff Comments" leaking in).
    assert "Unresolved Staff Comments" not in rf["risk_text"]
    assert rf["negative_density"] > 0  # 'harm', 'losses', 'fail', 'downturn' present


def test_extract_risk_factors_not_found_returns_flag():
    rf = et.extract_risk_factors("This document has no risk factors section at all.")
    assert rf["found"] is False
    assert rf["word_count"] == 0.0


# --------------------------------------------------------------------------- #
# Offline: the look-ahead guard.
# --------------------------------------------------------------------------- #
def _toy_panel():
    return pd.DataFrame({
        "ticker": ["AAA", "AAA"],
        "accession": ["0001", "0002"],
        "form": ["10-K", "10-K"],
        "filingDate": pd.to_datetime(["2021-02-15", "2022-02-15"]),
        "reportDate": pd.to_datetime(["2020-12-31", "2021-12-31"]),
        "lm_negative_density": [0.02, 0.05],
    })


def test_point_in_time_asof_text_no_lookahead():
    panel = _toy_panel()
    dates = pd.to_datetime(["2021-01-01", "2021-02-15", "2022-02-14", "2022-02-15"])
    pit = et.point_in_time_asof_text(panel, dates, value_col="lm_negative_density")
    s = pit["AAA"]
    # Before the first filing: nothing known -> NaN (never peek).
    assert pd.isna(s.loc["2021-01-01"])
    # On the first filing date: first value available.
    assert s.loc["2021-02-15"] == 0.02
    # Day before the 2022 filing: still the old value (no future leak).
    assert s.loc["2022-02-14"] == 0.02
    # On the 2022 filing date: the newer value.
    assert s.loc["2022-02-15"] == 0.05


def test_point_in_time_asof_text_empty():
    out = et.point_in_time_asof_text(et._empty_panel(), pd.bdate_range("2021", periods=4))
    assert out.empty
    assert len(out.index) == 4


# --------------------------------------------------------------------------- #
# Live smoke — skips gracefully when SEC is unreachable.
# --------------------------------------------------------------------------- #
def test_edgar_text_live_smoke():
    filings = et.get_filings("AAPL", forms=("10-K",))
    if filings.empty:
        pytest.skip("SEC unreachable / no cache — skipping live EDGAR-text smoke test")
    # Point-in-time invariant: a filing is public on/after the period it reports.
    valid = filings.dropna(subset=["reportDate", "filingDate"])
    if not valid.empty:
        assert (valid["filingDate"] >= valid["reportDate"]).all()
    assert {"filingDate", "accession", "doc_url"}.issubset(filings.columns)
