"""IV/RV monthly market timer: variance-risk-premium SPY long/flat switch.

Lens: volatility_timing + statistical_ml. PREDICTION task — predict the SIGN of
next month's SPY total return from the implied/realized volatility term structure,
then trade it as a long-or-cash SPY market timer.

Hypothesis
----------
The **variance risk premium** (VRP = implied variance minus realized variance) is a
priced compensation for bearing volatility risk and forecasts positive future equity
returns. When option-implied vol (VIX) sits *above* recently realized vol, investors are
paying a large premium to hedge volatility — historically that premium is mean-reverting
and is followed by *positive* equity returns as the premium is harvested. Bollerslev,
Tauchen & Zhou (2009) show the VRP predicts the equity premium, with peak predictability
around the quarterly horizon. Implied vol here is **VIX only** (30-day); the 1/3/6-month
structure lives on the realized side, so VRP_h = VIX - RV_h with RV_h the matched
21/63/126-day realized vol from SPY (h in {1m, 3m, 6m}).

Mechanism (why IV > RV predicts positive returns)
-------------------------------------------------
Selling variance (being short vol) earns a premium because variance spikes coincide with
bad states (crashes), so risk-averse investors overpay for protection. A high VRP means
that premium is rich; harvesting it is implicitly a long-equity / short-vol position, and
the unwinding of elevated implied vol tends to accompany rising prices. A high IV term
structure in *calm* realized conditions (large positive VRP) is therefore a buy signal;
a collapsing/inverted VRP (RV catching up to or exceeding IV — a vol shock in progress)
is a flat/cash signal.

Model & small-sample discipline
-------------------------------
Sample is small (~255 monthly obs since 2005, the start of VIX history), so overfitting
is the central enemy.
* **Expanding-window walk-forward logistic regression.** At each month-end t we
  standardize features and fit an L2-penalized logistic regression using ONLY months
  <= t, then predict P(up) for t -> t+1. Refit every month on the growing window.
* **Minimum training window of 60 months** before any live (non-flat) prediction; before
  that the strategy sits in cash.
* **L2 regularization** (ridge penalty) is always on, and the feature count is kept
  small (3 VRPs: VIX minus 1/3/6-month realized vol) to limit degrees of freedom.
* **No full-sample scaling or fitting** anywhere — the StandardScaler mean/std and the
  logistic coefficients at date t are estimated only from data <= t. This is the exact
  thing the red-team checks; see ``scratch/eval_ivrv_forecast.py`` which re-derives the
  OOS metrics independently.
* **Baseline guard:** a dead-simple univariate rule (long when VRP_1m > its expanding
  median) is evaluated alongside, so we can see whether the logistic adds OOS skill or
  merely overfits.

Trading rule
------------
Long-flat SPY. Weight 1.0 in SPY when predicted P(up) >= the expanding-window base rate
(fraction of up months seen so far), else 0 (cash). Monthly rebalance, held through the
month, ffilled. ``gross_leverage = None`` so variable net exposure is preserved.

Success bar
-----------
1. OOS directional accuracy AND AUC must beat the ALWAYS-LONG base rate (the fraction of
   up months — a model that always says "up" gets accuracy == base rate, AUC == 0.5).
2. Net-of-cost Sharpe must beat buy-and-hold SPY (the whole point of timing is risk-
   adjusted improvement, since being in cash sacrifices the equity premium part of the
   time).

Falsification / failure conditions
----------------------------------
* OOS accuracy <= base rate, or OOS AUC <= 0.5  => the VRP carries no usable directional
  information at the monthly horizon in this sample; reject.
* The multi-feature logistic does NOT beat the univariate VRP baseline OOS => the extra
  features only add overfitting noise; prefer the baseline / reject the ML claim.
* Net-of-cost Sharpe does not beat buy-and-hold SPY => timing destroys value (cash drag
  > avoided-drawdown benefit); reject as a tradable timer even if direction has skill.
* Edge present only in one sub-period (e.g. only the 2008-2011 GFC window) and absent
  post-2015 => regime-specific artifact, not a persistent premium.

Data
----
Implied vol: ^VIX only via yfinance, fetched inside ``generate_weights`` (cached). VIX
begins 2005-01, which bounds the usable sample. Realized vol: trailing 21/63/126-day
annualized std of SPY daily returns. All vol series are reindexed to the price grid and
forward-filled, so the value used at date t is known at t (look-ahead-safe). If VIX
cannot be fetched (offline), the strategy degrades to all-cash (zero weights) rather than
fabricating a signal.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from finance_agent.strategy import StrategySpec

SPEC = StrategySpec(
    id="ivrv_monthly_timer",
    thesis=(
        "Predict the sign of next month's SPY return from the variance risk premium "
        "(implied minus realized vol) at 1/3/6-month horizons using an expanding-window "
        "walk-forward L2 logistic regression, then trade long/flat SPY: go long when "
        "predicted P(up) beats the expanding base rate, else hold cash. A large positive "
        "VRP is compensation for bearing volatility risk and historically precedes "
        "positive equity returns (Bollerslev-Tauchen-Zhou 2009). Refit monthly on data "
        "<= t with per-date standardization and a 60-month minimum training window; no "
        "full-sample fitting. A univariate VRP baseline is reported as an overfit guard."
    ),
    taxonomy=["volatility_timing", "statistical_ml"],
    feature_families=["price", "implied_volatility"],
    universe="default",
    params={
        "asset": "SPY",
        "min_train_months": 60,
        "l2": 1.0,
        "rv_windows": (21, 63, 126),
    },
    author="quant-researcher",
    references=[
        "Bollerslev, Tauchen & Zhou (2009), Expected Stock Returns and Variance Risk Premia, RFS",
        "Carr & Wu (2009), Variance Risk Premiums, RFS",
        "Drechsler & Yaron (2011), What's Vol Got to Do with It, RFS",
        "Bekaert & Hoerova (2014), The VIX, the Variance Premium and Stock Market Volatility, JoE",
    ],
    gross_leverage=None,  # variable net exposure (SPY <-> cash) — do NOT renormalize
)

# Feature column order is fixed and shared with the eval script.
# Implied vol is VIX ONLY (per user direction); the 1/3/6-month structure lives on the
# realized-vol side, so VRP_h = VIX - RV_h for h in {1m, 3m, 6m}.
FEATURES = ["VRP_1m", "VRP_3m", "VRP_6m"]


def _month_end_index(idx: pd.DatetimeIndex) -> pd.DatetimeIndex:
    """Last available trading date of each calendar month in ``idx`` (look-ahead-safe)."""
    s = pd.Series(idx, index=idx)
    last = s.groupby([idx.year, idx.month]).max()
    return pd.DatetimeIndex(last.values)


def build_features(prices: pd.DataFrame, asset: str = "SPY",
                   rv_windows=(21, 63, 126)) -> pd.DataFrame:
    """Daily feature panel (VRPs + term-structure slopes). Each row uses only data <= t.

    Returns a DataFrame indexed like ``prices`` with columns ``FEATURES`` (may contain
    leading NaNs before warmup / before VIX6M history begins).
    """
    from finance_agent.data import get_prices

    px = prices[asset].astype(float)
    start = (prices.index.min() - pd.Timedelta(days=400)).strftime("%Y-%m-%d")
    try:
        vix = get_prices(["^VIX"], start=start)
    except Exception:
        return pd.DataFrame(index=prices.index, columns=FEATURES, dtype=float)

    # Reindex VIX onto the price grid and forward-fill: value at t known at t.
    # Implied vol is VIX only; we difference the SAME VIX against realized vol at each
    # horizon to form the variance risk premium per horizon.
    iv = vix["^VIX"].reindex(prices.index).ffill()

    daily = px.pct_change()
    w1, w3, w6 = rv_windows
    rv1 = daily.rolling(w1, min_periods=w1 // 2).std() * np.sqrt(252) * 100.0
    rv3 = daily.rolling(w3, min_periods=w3 // 2).std() * np.sqrt(252) * 100.0
    rv6 = daily.rolling(w6, min_periods=w6 // 2).std() * np.sqrt(252) * 100.0

    feat = pd.DataFrame(index=prices.index)
    feat["VRP_1m"] = iv - rv1
    feat["VRP_3m"] = iv - rv3
    feat["VRP_6m"] = iv - rv6
    return feat[FEATURES]


def _fit_logistic_l2(X: np.ndarray, y: np.ndarray, l2: float,
                     iters: int = 100, tol: float = 1e-8) -> np.ndarray:
    """L2-penalized logistic regression via Newton-IRLS. Intercept is NOT penalized.

    X already includes a leading column of ones. Returns the coefficient vector.
    """
    n, p = X.shape
    beta = np.zeros(p)
    reg = np.full(p, l2)
    reg[0] = 0.0  # do not penalize intercept
    for _ in range(iters):
        eta = X @ beta
        eta = np.clip(eta, -30, 30)
        mu = 1.0 / (1.0 + np.exp(-eta))
        w = np.clip(mu * (1.0 - mu), 1e-6, None)
        grad = X.T @ (mu - y) + reg * beta
        H = (X * w[:, None]).T @ X + np.diag(reg)
        try:
            step = np.linalg.solve(H, grad)
        except np.linalg.LinAlgError:
            step = np.linalg.lstsq(H, grad, rcond=None)[0]
        beta_new = beta - step
        if np.max(np.abs(beta_new - beta)) < tol:
            beta = beta_new
            break
        beta = beta_new
    return beta


def _predict_proba(beta: np.ndarray, x_row: np.ndarray) -> float:
    eta = float(np.clip(x_row @ beta, -30, 30))
    return 1.0 / (1.0 + np.exp(-eta))


def walk_forward_predictions(feat_m: pd.DataFrame, up: pd.Series,
                             min_train_months: int = 60, l2: float = 1.0):
    """Expanding-window walk-forward predictions at each month-end.

    Parameters
    ----------
    feat_m : month-end feature panel (rows = month-end dates, cols = FEATURES).
    up : binary target aligned to ``feat_m`` index — 1 if month t -> t+1 return > 0.
         The LAST month-end has an undefined target (no next month yet) -> NaN.

    Returns a DataFrame indexed by month-end with columns:
      p_full   : logistic P(up) using only data strictly before the prediction date,
      base_rate: expanding fraction of up months observed strictly before,
      p_base   : univariate baseline P(up) proxy (VRP_1m vs its expanding median).

    Look-ahead safety: to predict month t -> t+1 we train on pairs (feat_s, up_s) where
    the *outcome* up_s (covering s -> s+1) is already realized, i.e. s+1 <= t. So the
    training set for the prediction made at month-end t excludes the pair anchored at t.
    """
    idx = feat_m.index
    cols = ["p_full", "base_rate", "p_base", "y"]
    out = pd.DataFrame(index=idx, columns=cols, dtype=float)

    feat_vals = feat_m.values
    y_vals = up.reindex(idx).values  # may have trailing NaN

    for i, dt in enumerate(idx):
        # Predict the outcome anchored at month-end i (i -> i+1). Train only on anchors
        # whose outcome is already known: anchors 0..i-1 with non-NaN y and full features.
        train_mask = np.zeros(i, dtype=bool)
        if i > 0:
            yt = y_vals[:i]
            Xt = feat_vals[:i]
            valid = np.isfinite(yt) & np.all(np.isfinite(Xt), axis=1)
            train_mask = valid
        n_train = int(train_mask.sum()) if i > 0 else 0
        out.loc[dt, "y"] = y_vals[i]

        if i == 0 or n_train < 1:
            continue

        Xtr = feat_vals[:i][train_mask]
        ytr = y_vals[:i][train_mask]
        out.loc[dt, "base_rate"] = float(ytr.mean())

        x_now = feat_vals[i]
        if not np.all(np.isfinite(x_now)):
            continue

        # Univariate baseline: long if current VRP_1m above expanding median of training.
        med = np.median(Xtr[:, 0])
        out.loc[dt, "p_base"] = 1.0 if x_now[0] > med else 0.0

        # Require the minimum training window for the logistic live prediction.
        if n_train < min_train_months:
            continue
        if len(np.unique(ytr)) < 2:
            continue

        # Standardize on TRAINING data only.
        mean = Xtr.mean(axis=0)
        std = Xtr.std(axis=0)
        std[std < 1e-9] = 1.0
        Xtr_s = (Xtr - mean) / std
        x_now_s = (x_now - mean) / std

        Xtr_aug = np.column_stack([np.ones(len(Xtr_s)), Xtr_s])
        x_aug = np.concatenate([[1.0], x_now_s])
        beta = _fit_logistic_l2(Xtr_aug, ytr, l2=l2)
        out.loc[dt, "p_full"] = _predict_proba(beta, x_aug)

    return out


def generate_weights(prices: pd.DataFrame, asset: str = "SPY",
                     min_train_months: int = 60, l2: float = 1.0,
                     rv_windows=(21, 63, 126)) -> pd.DataFrame:
    """Return long/flat SPY weights from the walk-forward VRP timer.

    Only past data is used at each row; the engine adds the 1-day execution lag. The
    decision made at month-end t (using data <= t) is applied to month t+1 and ffilled.
    """
    weights = pd.DataFrame(0.0, index=prices.index, columns=prices.columns)
    if asset not in prices.columns:
        return weights

    feat = build_features(prices, asset=asset, rv_windows=rv_windows)
    if feat.dropna(how="all").empty:
        return weights  # degraded: no IV data -> all cash

    me = _month_end_index(prices.index)
    me = me[me.isin(prices.index)]
    feat_m = feat.reindex(me)

    # Target: sign of asset total return month t -> t+1 (last month has NaN target).
    px_m = prices[asset].reindex(me).astype(float)
    fwd_ret = px_m.shift(-1) / px_m - 1.0
    up = (fwd_ret > 0).astype(float)
    up[fwd_ret.isna()] = np.nan

    preds = walk_forward_predictions(feat_m, up, min_train_months=min_train_months, l2=l2)

    # Decision at month-end t: long if p_full >= expanding base rate, else cash.
    # If no live logistic prediction yet (warmup), stay in cash (0).
    p = preds["p_full"]
    thr = preds["base_rate"]
    long_flag = (p >= thr) & p.notna() & thr.notna()
    w_at_me = long_flag.astype(float)  # 1.0 long, 0.0 cash, indexed by month-end

    # Place the decision on its month-end row, ffill through the next month.
    w_series = pd.Series(np.nan, index=prices.index)
    w_series.loc[w_at_me.index] = w_at_me.values
    w_series = w_series.ffill().fillna(0.0)

    weights[asset] = w_series
    return weights
