"""finance_agent — a small, transparent harness for hypothesizing and validating
equity trading strategies.

The package is deliberately lightweight so that LLM sub-agents can read and modify
every line. Heavy lifting (data, backtest, validation, ledger) lives in focused
modules:

    data        - fetch & cache historical prices (yfinance) with a look-ahead-safe API
    metrics     - performance statistics (Sharpe, Sortino, drawdown, turnover, ...)
    backtest    - vectorized weight -> P&L engine with execution lag and costs
    validation  - robustness checks (OOS split, walk-forward, deflated Sharpe, ...)
    strategy    - the Strategy contract every generated strategy must satisfy
    ledger      - the novelty/diversity registry of attempted strategies
"""

from .backtest import BacktestResult, run_backtest
from .strategy import Strategy, StrategySpec

__all__ = ["BacktestResult", "run_backtest", "Strategy", "StrategySpec"]
__version__ = "0.1.0"
