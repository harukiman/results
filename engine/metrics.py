"""Performance metrics for backtested strategies."""

import numpy as np
import pandas as pd


def compute_metrics(trades: list[dict], equity_curve: pd.Series, benchmark_curve: pd.Series, bars_per_year: int = 35040) -> dict:
    """Compute comprehensive strategy metrics.

    trades: list of {entry_time, exit_time, entry_price, exit_price, side, pnl_pct}
    equity_curve: cumulative equity (starting at 1.0)
    benchmark_curve: buy-and-hold equity (starting at 1.0)
    bars_per_year: 35040 for 15m (24/7 crypto), 105120 for 5m, 8760 for 1h
    """
    if not trades or equity_curve.empty:
        return _empty_metrics()

    total_return = (equity_curve.iloc[-1] / equity_curve.iloc[0] - 1) * 100
    bench_return = (benchmark_curve.iloc[-1] / benchmark_curve.iloc[0] - 1) * 100
    alpha = total_return - bench_return

    # Daily return: normalize by number of days for cross-period comparison
    bars_per_day = bars_per_year / 365.25
    num_days = max(1, len(equity_curve) / bars_per_day)
    return_daily = total_return / num_days

    # Returns
    returns = equity_curve.pct_change().dropna()
    if returns.empty:
        return _empty_metrics()

    ann_factor = np.sqrt(bars_per_year)

    sharpe = (returns.mean() / returns.std() * ann_factor) if returns.std() > 0 else 0
    downside = returns[returns < 0].std()
    sortino = (returns.mean() / downside * ann_factor) if downside > 0 else 0

    # Max drawdown
    cummax = equity_curve.cummax()
    drawdown = (equity_curve - cummax) / cummax
    max_dd = drawdown.min() * 100

    # Trade stats
    pnls = [t["pnl_pct"] for t in trades]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]
    win_rate = len(wins) / len(pnls) * 100 if pnls else 0
    avg_win = np.mean(wins) if wins else 0
    avg_loss = np.mean(losses) if losses else 0
    profit_factor = (sum(wins) / abs(sum(losses))) if losses and sum(losses) != 0 else 99.99
    expectancy = np.mean(pnls) if pnls else 0

    # Calmar ratio
    calmar = (total_return / abs(max_dd)) if max_dd != 0 else 0

    return {
        "total_return_pct": round(total_return, 2),
        "benchmark_return_pct": round(bench_return, 2),
        "alpha_pct": round(alpha, 2),
        "return_daily_pct": round(return_daily, 4),
        "num_days": round(num_days, 1),
        "sharpe_ratio": round(sharpe, 3),
        "sortino_ratio": round(sortino, 3),
        "max_drawdown_pct": round(max_dd, 2),
        "calmar_ratio": round(calmar, 3),
        "total_trades": len(trades),
        "win_rate_pct": round(win_rate, 1),
        "avg_win_pct": round(avg_win, 3),
        "avg_loss_pct": round(avg_loss, 3),
        "profit_factor": round(profit_factor, 2),
        "expectancy_pct": round(expectancy, 3),
    }


def _empty_metrics() -> dict:
    return {
        "total_return_pct": 0, "benchmark_return_pct": 0, "alpha_pct": 0,
        "return_daily_pct": 0, "num_days": 0,
        "sharpe_ratio": 0, "sortino_ratio": 0, "max_drawdown_pct": 0,
        "calmar_ratio": 0, "total_trades": 0, "win_rate_pct": 0,
        "avg_win_pct": 0, "avg_loss_pct": 0, "profit_factor": 0,
        "expectancy_pct": 0,
    }


def grade_strategy(m: dict) -> str:
    """Grade a strategy: A/B/C/D/F."""
    score = 0
    if m["alpha_pct"] > 5: score += 3
    elif m["alpha_pct"] > 0: score += 1
    if m["sharpe_ratio"] > 2: score += 3
    elif m["sharpe_ratio"] > 1: score += 2
    elif m["sharpe_ratio"] > 0.5: score += 1
    if m["max_drawdown_pct"] > -10: score += 2
    elif m["max_drawdown_pct"] > -20: score += 1
    if m["win_rate_pct"] > 55: score += 1
    if m["profit_factor"] > 1.5: score += 2
    elif m["profit_factor"] > 1.0: score += 1

    if score >= 10: return "A"
    if score >= 7: return "B"
    if score >= 4: return "C"
    if score >= 2: return "D"
    return "F"
