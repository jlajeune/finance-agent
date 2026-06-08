"""Performance and risk metrics computed from a daily return series.

All functions take a pandas Series of *periodic* (usually daily) returns and assume
252 trading periods per year unless told otherwise.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

TRADING_DAYS = 252


def annualized_return(returns: pd.Series, periods_per_year: int = TRADING_DAYS) -> float:
    r = returns.dropna()
    if r.empty:
        return float("nan")
    growth = (1 + r).prod()
    years = len(r) / periods_per_year
    if years <= 0 or growth <= 0:
        return float("nan")
    return growth ** (1 / years) - 1


def annualized_vol(returns: pd.Series, periods_per_year: int = TRADING_DAYS) -> float:
    return returns.dropna().std(ddof=1) * np.sqrt(periods_per_year)


def sharpe(returns: pd.Series, rf: float = 0.0, periods_per_year: int = TRADING_DAYS) -> float:
    r = returns.dropna()
    excess = r - rf / periods_per_year
    sd = excess.std(ddof=1)
    if sd == 0 or np.isnan(sd):
        return float("nan")
    return np.sqrt(periods_per_year) * excess.mean() / sd


def sortino(returns: pd.Series, rf: float = 0.0, periods_per_year: int = TRADING_DAYS) -> float:
    r = returns.dropna()
    excess = r - rf / periods_per_year
    downside = excess[excess < 0]
    dd = np.sqrt((downside ** 2).mean()) if len(downside) else np.nan
    if not dd or np.isnan(dd):
        return float("nan")
    return np.sqrt(periods_per_year) * excess.mean() / dd


def max_drawdown(returns: pd.Series) -> float:
    """Most negative peak-to-trough drawdown of the cumulative curve (<= 0)."""
    curve = (1 + returns.dropna()).cumprod()
    if curve.empty:
        return float("nan")
    peak = curve.cummax()
    return float((curve / peak - 1).min())


def calmar(returns: pd.Series, periods_per_year: int = TRADING_DAYS) -> float:
    mdd = max_drawdown(returns)
    if not mdd or np.isnan(mdd):
        return float("nan")
    return annualized_return(returns, periods_per_year) / abs(mdd)


def hit_rate(returns: pd.Series) -> float:
    r = returns.dropna()
    return float((r > 0).mean()) if len(r) else float("nan")


def t_statistic(returns: pd.Series) -> float:
    """t-stat of the mean daily return being non-zero. |t| > ~2 is the usual bar."""
    r = returns.dropna()
    sd = r.std(ddof=1)
    if sd == 0 or np.isnan(sd) or len(r) < 2:
        return float("nan")
    return r.mean() / (sd / np.sqrt(len(r)))


def deflated_sharpe(observed_sharpe: float, n_trials: int, n_obs: int,
                    skew: float = 0.0, kurt: float = 3.0) -> float:
    """Probabilistic Sharpe deflated for multiple testing (Bailey & López de Prado).

    Returns the probability that the *true* Sharpe is > 0 after accounting for the
    fact that ``n_trials`` strategies were tried (selection bias). Values below ~0.95
    mean the result is plausibly a fluke of searching. ``observed_sharpe`` and the
    return are in the same (annualization-agnostic) per-observation convention used
    internally, so pass the *non-annualized* Sharpe here.
    """
    from scipy.stats import norm

    if n_trials < 1 or n_obs < 2:
        return float("nan")
    sr = observed_sharpe  # per-observation (non-annualized) Sharpe
    # Expected maximum of N independent zero-skill Sharpe ESTIMATES, expressed in units
    # of the estimator's standard deviation (a z-score, ~0.85 for N=3). For a single
    # trial there is no selection, so the expected max is 0.
    if n_trials == 1:
        e_max = 0.0
    else:
        e_max = (
            (1 - np.euler_gamma) * norm.ppf(1 - 1.0 / n_trials)
            + np.euler_gamma * norm.ppf(1 - 1.0 / (n_trials * np.e))
        )
    # Convert that z-score into a per-observation Sharpe threshold by multiplying by the
    # std of the Sharpe estimator under the null (~1/sqrt(n-1)). This is the fix for the
    # original scale bug, where e_max (a z-score) was compared directly to a per-obs
    # Sharpe (~0.05), making the test fire false-negative for every daily strategy.
    sr_star = e_max * np.sqrt(1.0 / (n_obs - 1))
    denom = np.sqrt(1 - skew * sr + (kurt - 1) / 4 * sr ** 2)
    if denom == 0 or np.isnan(denom):
        return float("nan")
    z = (sr - sr_star) * np.sqrt(n_obs - 1) / denom
    return float(norm.cdf(z))


def turnover(weights: pd.DataFrame, execution_lag: int = 1) -> pd.Series:
    """Per-period one-way turnover implied by a weight schedule."""
    w = weights.shift(execution_lag).fillna(0.0)
    return (w - w.shift(1).fillna(0.0)).abs().sum(axis=1)


def summary(returns: pd.Series, periods_per_year: int = TRADING_DAYS) -> dict:
    """A compact dict of headline stats for reports and the ledger."""
    return {
        "ann_return": annualized_return(returns, periods_per_year),
        "ann_vol": annualized_vol(returns, periods_per_year),
        "sharpe": sharpe(returns, periods_per_year=periods_per_year),
        "sortino": sortino(returns, periods_per_year=periods_per_year),
        "max_drawdown": max_drawdown(returns),
        "calmar": calmar(returns, periods_per_year),
        "hit_rate": hit_rate(returns),
        "t_stat": t_statistic(returns),
        "n_obs": int(returns.dropna().shape[0]),
    }
