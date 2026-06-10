"""Zumbach time-reversal-asymmetry volatility overlay on SPY.

Lens: volatility_timing + time_irreversibility (new). A 2-parameter additive upgrade
to the project's only validated strategy, ``voltarget_spy``.

Economic / statistical mechanism
--------------------------------
Financial volatility is **time-irreversible**: past *trends* (the running directional
push of returns) forecast future volatility, while past volatility carries far less
information about future trends. This broken time-reversal symmetry is the *Zumbach
effect* (Zumbach 2007; formalised as a key feature of rough/quadratic-Hawkes vol models,
El Euch-Gatheral-Radoicic-Rosenbaum 2019; Bouchaud 2022). The intuition: a sustained
directional move (up or down) reflects an *imbalance* that the market subsequently
resolves through elevated activity — so a strong recent trend is a leading indicator of
a vol rise, *over and above* the level of recently-realised variance.

We forecast next-period variance additively:

    sigma2_hat(t) = a * RV22(t) + b * Z(t)

* ``RV22(t)`` — trailing ~22-day Garman-Klass realised variance (uses OHLC, ends at t).
* ``Z(t) = ( sum_tau K(tau) r(t-tau) )^2`` — the SQUARED causal exponentially-weighted
  daily-log-return trend (half-life ``trend_hl`` ~ 15 trading days). This is the
  Zumbach term: a *signed* multi-day trend, squared.

``a, b >= 0`` are fit by **expanding-window walk-forward non-negative least squares** of
realised forward variance on ``[RV22, Z]`` (refit every ``refit_every`` days, after a
``min_train`` warm-up). No full-sample fit; the EMA is strictly causal; every feature
at row t uses data <= t. The engine adds the 1-day execution lag.

Position sizing is identical in spirit to ``voltarget_spy`` — inverse-vol exposure
capped at ``max_leverage``, weekly rebalance, no-trade band — but the vol estimate is the
Zumbach-augmented forecast instead of plain realised vol:

    w_SPY = clip( target_vol / sqrt(sigma2_hat) , 0, max_leverage )

Edge beyond a VIX-timer / plain vol-target
------------------------------------------
Plain vol-targeting and a VIX-level sizer both condition on the *level* of recent/implied
vol. The Zumbach term conditions on the *signed trend*, which is information they do not
use, so it can flag vol rises forming inside calm, low-VIX **melt-ups** (a strong upward
trend that precedes a vol pickup) where level-based sizers are blind.

Falsification / failure conditions
----------------------------------
* If walk-forward NNLS sets ``b`` ~ 0 (the Zumbach term carries no incremental
  information about forward variance), the overlay collapses to ``voltarget_spy``.
* If net-of-cost Sharpe and max drawdown do NOT beat both ``voltarget_spy`` AND a
  VIX-level sizer, the trend augmentation adds nothing tradable.
* **Leverage-effect guard:** if a signed decomposition (b_up*Z_up + b_dn*Z_dn) shows the
  predictive lift comes essentially only from DOWN-trends (b_dn), with b_up ~ 0 / weak
  t-stat, then this is merely the leverage effect, not the symmetric Zumbach effect.
  (Tested in scratch/eval_zumbach.py with Newey-West HAC standard errors, because the
  forward-variance windows overlap and naive t-stats are inflated.)

Data limitations
----------------
SPY OHLC via yfinance (cached) for Garman-Klass RV; close-to-close RV fallback if OHLC
is missing. Cash leg modelled at 0% (conservative). ``gross_leverage = None`` so the
engine does NOT renormalise the variable cash<->SPY exposure.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from finance_agent.strategy import StrategySpec

SPEC = StrategySpec(
    id="zumbach_vol_overlay",
    thesis=(
        "Zumbach time-reversal-asymmetry vol overlay on SPY: forecast next-period "
        "variance as a*RV22 + b*Z, where Z is the SQUARED causal EMA trend of daily log "
        "returns (half-life ~15d) and RV22 is trailing Garman-Klass realised variance. "
        "Volatility is time-irreversible: past signed trends predict future vol beyond "
        "the level of recent realised vol (Zumbach effect). Size SPY inversely to "
        "sqrt(forecast), capped at 1x, weekly rebalance + no-trade band. a,b>=0 fit by "
        "expanding-window walk-forward NNLS (no full-sample fit, causal EMA only). The "
        "signed-trend term conditions on information that plain vol-target and VIX-level "
        "sizers ignore, so it can flag vol rises inside low-VIX melt-ups."
    ),
    taxonomy=["volatility_timing", "time_irreversibility"],
    feature_families=["price"],
    universe="default",
    params={
        "asset": "SPY",
        "rv_window": 22,
        "trend_hl": 15.0,
        "fwd_window": 22,
        "target_vol": 0.11,
        "max_leverage": 1.0,
        "rebalance": 5,
        "band": 0.05,
        "min_train": 756,
        "refit_every": 63,
    },
    author="quant-researcher",
    references=[
        "Zumbach (2007), Time reversal invariance in finance, SSRN 1004992",
        "El Euch, Gatheral, Radoicic & Rosenbaum (2019), The Zumbach effect under "
        "rough Heston, arXiv 1809.02098",
        "Bouchaud (2022), The Zumbach effect and quadratic Hawkes models",
        "Man Group, The Impact of Volatility Targeting (sizing discipline)",
    ],
    gross_leverage=None,  # variable net exposure (cash<->SPY) — do NOT renormalize
)


# ---------------------------------------------------------------------------
# Feature construction (all strictly causal: every value at row t uses data <= t)
# ---------------------------------------------------------------------------

def _garman_klass_rv(
    open_: pd.Series, high: pd.Series, low: pd.Series, close: pd.Series, window: int
) -> pd.Series:
    """Trailing Garman-Klass realised variance (annualized) ending at each row.

    Per-day GK variance estimate:
        0.5*(ln(H/L))^2 - (2 ln2 - 1)*(ln(C/O))^2
    Averaged over a trailing ``window`` and annualized by 252. Uses only past/current
    bars (rolling, right-aligned) so it is look-ahead-safe.
    """
    hl = np.log(high / low)
    co = np.log(close / open_)
    daily_var = 0.5 * hl ** 2 - (2.0 * np.log(2.0) - 1.0) * co ** 2
    daily_var = daily_var.clip(lower=0.0)  # numerical guard
    rv = daily_var.rolling(window, min_periods=max(10, window // 2)).mean() * 252.0
    return rv


def _cc_rv(close: pd.Series, window: int) -> pd.Series:
    """Close-to-close trailing realised variance (annualized) — GK fallback."""
    r = np.log(close / close.shift(1))
    return (r.rolling(window, min_periods=max(10, window // 2)).var()) * 252.0


def _ema_trend(log_ret: pd.Series, halflife: float) -> pd.Series:
    """Causal exponentially-weighted moving average of daily log returns (the trend).

    pandas ewm is causal (uses only past+current observations), so this is
    look-ahead-safe. The Zumbach term Z = trend^2.
    """
    return log_ret.ewm(halflife=halflife, adjust=True, min_periods=5).mean()


def _nnls_2d(X: np.ndarray, y: np.ndarray) -> tuple[float, float]:
    """Non-negative least squares for a 2-column design [RV22, Z] -> (a, b), a,b>=0.

    Closed-form for 2 non-negative coefficients via the KKT cases (no scipy needed):
    try the interior unconstrained solution; if a coefficient is negative, fall back to
    the best single-regressor non-negative fit. Returns (a, b) with both >= 0.
    """
    # Drop rows with any nan/inf
    mask = np.isfinite(X).all(axis=1) & np.isfinite(y)
    X = X[mask]
    y = y[mask]
    if X.shape[0] < 30:
        return 1.0, 0.0  # not enough data -> degrade to plain RV (b=0)

    # Unconstrained OLS
    try:
        beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    except np.linalg.LinAlgError:
        return 1.0, 0.0
    a, b = float(beta[0]), float(beta[1])
    if a >= 0 and b >= 0:
        return a, b

    # KKT boundary cases: project each regressor alone (non-negative), keep best fit.
    best = None
    for j in (0, 1):
        xj = X[:, j]
        denom = float(xj @ xj)
        if denom <= 0:
            continue
        cj = max(0.0, float(xj @ y) / denom)
        resid = y - cj * xj
        sse = float(resid @ resid)
        coef = [0.0, 0.0]
        coef[j] = cj
        if best is None or sse < best[0]:
            best = (sse, coef[0], coef[1])
    if best is None:
        return 1.0, 0.0
    return best[1], best[2]


# ---------------------------------------------------------------------------
# Main contract
# ---------------------------------------------------------------------------

def generate_weights(
    prices: pd.DataFrame,
    asset: str = "SPY",
    rv_window: int = 22,
    trend_hl: float = 15.0,
    fwd_window: int = 22,
    target_vol: float = 0.11,
    max_leverage: float = 1.0,
    rebalance: int = 5,
    band: float = 0.05,
    min_train: int = 756,
    refit_every: int = 63,
) -> pd.DataFrame:
    """Return weights (dates x tickers) with a single varying long position in ``asset``.

    All signals use only data up to and including each row's date; the engine adds the
    1-day execution lag. The forecast coefficients (a, b) are fit by expanding-window
    walk-forward NNLS of realised forward variance on [RV22, Z], so the parameters used
    at date t are estimated only from data available before t.
    """
    if asset not in prices.columns:
        raise ValueError(f"asset {asset!r} not in price universe")

    idx = prices.index

    # --- Fetch OHLC for Garman-Klass RV (cached); fall back to close-to-close. -------
    close = prices[asset].astype(float)
    log_ret = np.log(close / close.shift(1))
    try:
        from finance_agent import data as _data

        start = idx.min().strftime("%Y-%m-%d")
        end = (idx.max() + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
        o = _data.get_prices([asset], start=start, end=end, field="Open")[asset].reindex(idx)
        h = _data.get_prices([asset], start=start, end=end, field="High")[asset].reindex(idx)
        lo = _data.get_prices([asset], start=start, end=end, field="Low")[asset].reindex(idx)
        c = _data.get_prices([asset], start=start, end=end, field="Close")[asset].reindex(idx)
        rv = _garman_klass_rv(o, h, lo, c, rv_window)
        if rv.notna().sum() < 100:  # OHLC came back unusable -> fallback
            rv = _cc_rv(close, rv_window)
    except Exception:
        rv = _cc_rv(close, rv_window)

    # --- Zumbach term: squared causal EMA trend of daily log returns. ----------------
    trend = _ema_trend(log_ret, trend_hl)
    # Express trend on a comparable (annualized-variance) scale: (annualized trend)^2.
    Z = (trend * np.sqrt(252.0)) ** 2

    # --- Forward realised variance TARGET for the walk-forward fit. ------------------
    # Realised variance over the NEXT fwd_window days. This is used ONLY in training
    # rows that are entirely in the past relative to the date whose coefficients we
    # estimate — i.e. the fit at date t uses (feature, target) pairs whose target window
    # has fully closed by t. No future leakage into the live signal.
    fwd_var = (
        log_ret.rolling(fwd_window).var().shift(-fwd_window) * 252.0
    )  # fwd_var.loc[s] = realised var over (s, s+fwd_window]; known only at s+fwd_window

    rv_v = rv.to_numpy(dtype=float)
    z_v = Z.to_numpy(dtype=float)
    fv_v = fwd_var.to_numpy(dtype=float)
    n = len(idx)

    # --- Expanding-window walk-forward NNLS for (a, b). ------------------------------
    a_arr = np.full(n, np.nan)
    b_arr = np.full(n, np.nan)
    cur_a, cur_b = 1.0, 0.0  # default: plain RV until the first fit
    last_fit = -10**9
    for i in range(n):
        # Refit using only pairs whose forward-variance window has fully closed by date
        # i: pair at position k is usable iff k + fwd_window <= i. That guarantees the
        # target fv_v[k] was observable strictly before the live signal at i.
        if i - last_fit >= refit_every and i >= min_train:
            kmax = i - fwd_window  # last training index whose fwd window closed by i
            if kmax >= 60:
                X = np.column_stack([rv_v[:kmax + 1], z_v[:kmax + 1]])
                y = fv_v[:kmax + 1]
                cur_a, cur_b = _nnls_2d(X, y)
                last_fit = i
        a_arr[i] = cur_a
        b_arr[i] = cur_b

    # --- Augmented variance forecast and inverse-vol sizing. -------------------------
    sigma2_hat = a_arr * rv_v + b_arr * z_v
    sigma_hat = np.sqrt(np.clip(sigma2_hat, 1e-8, None))
    sigma_hat = pd.Series(sigma_hat, index=idx)

    target = (target_vol / sigma_hat).clip(lower=0.0, upper=max_leverage)

    # --- Weekly rebalance + no-trade band (turnover discipline, matches incumbent). --
    weights = pd.DataFrame(0.0, index=idx, columns=prices.columns)
    w_asset = pd.Series(index=idx, dtype=float)
    rebal_dates = idx[::rebalance]
    cur = np.nan
    for dt in rebal_dates:
        t = target.loc[dt]
        if np.isfinite(t) and (np.isnan(cur) or abs(t - cur) >= band):
            cur = float(t)
        if np.isfinite(cur):
            w_asset.loc[dt] = cur

    weights[asset] = w_asset.ffill().fillna(0.0)
    return weights
