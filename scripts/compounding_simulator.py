"""
scripts/compounding_simulator.py
==================================
Compounding strategy simulation tool for v6.13d daily PnL.

Simulates 6 compounding policies over 5 years starting from $10M AUM.
Returns scenario JSON for analysis. Standalone analysis tool (no production changes).

Author: K428 agent | 2026-05-25
REPO_ROOT = Path(__file__).resolve().parent.parent  (K339 security rule)
"""

from __future__ import annotations

import json
import math
import numpy as np
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ── Paths (K339 security rule) ────────────────────────────────────────────────
SCRIPTS_DIR = Path(__file__).resolve().parent
LAB_ROOT    = SCRIPTS_DIR.parent        # crypto-lab/
REPO_ROOT   = LAB_ROOT.parent           # K339: parent of crypto-lab

# ── Simulation parameters ─────────────────────────────────────────────────────
INITIAL_AUM_USD   = 10_000_000.0   # $10M starting capital
SIM_YEARS         = 5
SIM_DAYS          = SIM_YEARS * 365
TRADING_DAYS_PER_YEAR = 365

# ── v6.13d parametric model (from K346 backtest) ──────────────────────────────
# ann_ret = 10.009%, ann_vol = 0.3929%, max_dd = 0.0189%, Sharpe = 25.47
# daily_mean = 10.009% / 365 = 0.027422% per day
# daily_std  = 0.3929% / sqrt(365) = 0.02056% per day
V613D_DAILY_MEAN = 0.10009 / 365        # ~0.0002742 (decimal)
V613D_DAILY_STD  = (0.003929 / math.sqrt(365))  # ~0.0002057 (decimal)
V613D_SHARPE     = 25.47
V613D_MAX_DD_PCT = 0.0189 / 100.0       # 0.000189 as fraction (very small — FR carry)

# Cash buffer reserved for margin / emergency (K357)
CASH_BUFFER_RATIO = 0.08   # 8% — see Phase 4 analysis

# ── RNG seed for reproducibility ──────────────────────────────────────────────
SEED = 42


def _load_actual_returns() -> np.ndarray | None:
    """
    Attempt to load actual K280/v6.13d daily returns from wave_k280_curves.json.
    Returns array of daily fractional returns, or None if unavailable.
    """
    curves_path = LAB_ROOT / "wave_k280_curves.json"
    if not curves_path.exists():
        return None
    try:
        d = json.loads(curves_path.read_text())
        k280 = np.array(d.get("K280", []), dtype=float)
        if len(k280) < 50:
            return None
        # k280 is cumulative equity (starts at 1.0), convert to daily returns
        returns = k280[1:] / k280[:-1] - 1.0
        return returns
    except Exception:
        return None


def _load_v613d_composite_returns() -> np.ndarray:
    """
    Build v6.13d composite daily returns from K280 equity curve + parametric sUSDe.
    v6.13d weights: K280=75%, K297'=20%, sUSDe=5%.

    K280 and K297' are highly correlated (K346: rho=0.9593) so we approximate
    K297' as K280 * 0.97 scaled (slightly lower vol, HIP-3 RWA carry).
    sUSDe: deterministic 13% APY = 13/365 bps/day.
    """
    k280_ret = _load_actual_returns()
    k280_path = LAB_ROOT / "wave_k280_curves.json"

    if k280_ret is not None and len(k280_ret) >= 200:
        # Use actual K280 returns as K280 sleeve
        r280 = k280_ret
        # K297' approximation: K280 slightly dampened + small orthogonal noise
        rng = np.random.default_rng(SEED + 1)
        k297p = r280 * 0.97 + rng.normal(0, r280.std() * 0.1, len(r280))
        # sUSDe: deterministic daily yield (13% APY / 365)
        susde_daily = 0.13 / 365
        susde = np.full(len(r280), susde_daily)
        # Composite v6.13d: 75% K280 + 20% K297' + 5% sUSDe
        composite = 0.75 * r280 + 0.20 * k297p + 0.05 * susde
        return composite
    else:
        # Parametric fallback: normal distribution with K346 params
        rng = np.random.default_rng(SEED)
        return rng.normal(V613D_DAILY_MEAN, V613D_DAILY_STD, SIM_DAYS)


def _generate_sim_returns(n_days: int, base_returns: np.ndarray, seed_offset: int = 0) -> np.ndarray:
    """
    Generate n_days of synthetic daily returns using the historical distribution.
    Uses block bootstrap (30-day blocks) to preserve autocorrelation structure.
    """
    if len(base_returns) >= n_days:
        # Sufficient actual data: use as-is (truncate)
        return base_returns[:n_days]

    # Block bootstrap from actual history
    rng = np.random.default_rng(SEED + seed_offset)
    block_size = 30
    history = base_returns.copy()
    n_blocks_needed = math.ceil(n_days / block_size)
    n_blocks_avail = len(history) // block_size

    if n_blocks_avail < 2:
        # Pure parametric fallback
        return rng.normal(V613D_DAILY_MEAN, V613D_DAILY_STD, n_days)

    blocks = [history[i * block_size:(i + 1) * block_size] for i in range(n_blocks_avail)]
    chosen = [blocks[rng.integers(0, len(blocks))] for _ in range(n_blocks_needed)]
    bootstrapped = np.concatenate(chosen)[:n_days]
    return bootstrapped


def compute_metrics(equity: np.ndarray, daily_ret: np.ndarray) -> dict[str, float]:
    """Compute CAGR, MaxDD, Sharpe, Sortino from equity curve and daily returns."""
    terminal = float(equity[-1])
    initial  = float(equity[0])
    years    = len(equity) / 365.0

    cagr = (terminal / initial) ** (1.0 / years) - 1.0

    # Max drawdown (absolute $)
    running_max = np.maximum.accumulate(equity)
    dd_abs = running_max - equity
    max_dd_abs = float(dd_abs.max())
    max_dd_pct = max_dd_abs / initial * 100.0

    # Drawdown days (duration of the deepest drawdown trough)
    peak_idx = int(np.argmax(equity))
    trough_idx = int(peak_idx + np.argmax(dd_abs[peak_idx:]))
    dd_days = int(trough_idx - peak_idx) if trough_idx > peak_idx else 0

    # Sharpe and Sortino (annualised)
    ret_mean = float(np.mean(daily_ret))
    ret_std  = float(np.std(daily_ret, ddof=1)) if len(daily_ret) > 1 else 1e-9
    sharpe   = ret_mean / ret_std * math.sqrt(365) if ret_std > 0 else 0.0

    downside = daily_ret[daily_ret < 0]
    down_std = float(np.std(downside, ddof=1)) if len(downside) > 1 else 1e-9
    sortino  = ret_mean / down_std * math.sqrt(365) if down_std > 0 else 0.0

    return {
        "terminal_usd": round(terminal, 2),
        "cagr_pct":     round(cagr * 100, 4),
        "max_dd_abs_usd": round(max_dd_abs, 2),
        "max_dd_pct":   round(max_dd_pct, 6),
        "dd_days":      dd_days,
        "sharpe":       round(sharpe, 4),
        "sortino":      round(sortino, 4),
    }


# ══════════════════════════════════════════════════════════════════════════════
# COMPOUNDING STRATEGIES
# ══════════════════════════════════════════════════════════════════════════════

def strategy_daily_reinvest_100(daily_ret: np.ndarray, initial: float) -> tuple[np.ndarray, np.ndarray]:
    """
    S1 — Daily reinvest 100%.
    Every day's P&L is fully added to capital. Deployed capital = effective AUM * (1 - cash_buffer).
    """
    aum = initial
    equity = [aum]
    effective_returns = []
    cash_buffer = CASH_BUFFER_RATIO

    for r in daily_ret:
        deployed = aum * (1.0 - cash_buffer)
        pnl = deployed * r
        aum += pnl
        equity.append(aum)
        effective_returns.append(pnl / (equity[-2]))

    return np.array(equity[1:]), np.array(effective_returns)


def strategy_weekly_rebalance(daily_ret: np.ndarray, initial: float,
                               reinvest_frac: float = 1.0) -> tuple[np.ndarray, np.ndarray]:
    """
    S2 — Weekly rebalance (every 7 days).
    Daily P&L accumulates; on Sunday (day % 7 == 0) the full week's gain
    is absorbed into capital. reinvest_frac controls what fraction is reinvested.
    """
    aum = initial
    pending_pnl = 0.0
    equity = [aum]
    effective_returns = []
    cash_buffer = CASH_BUFFER_RATIO

    for day, r in enumerate(daily_ret, start=1):
        deployed = aum * (1.0 - cash_buffer)
        pnl = deployed * r
        pending_pnl += pnl

        if day % 7 == 0:
            # Rebalance: reinvest fraction, leave rest in cash buffer
            aum += pending_pnl * reinvest_frac
            pending_pnl = 0.0

        equity.append(aum + pending_pnl)
        effective_returns.append(pnl / equity[-2])

    return np.array(equity[1:]), np.array(effective_returns)


def strategy_monthly_fixed(daily_ret: np.ndarray, initial: float) -> tuple[np.ndarray, np.ndarray]:
    """
    S3 — Monthly fixed allocation.
    Capital is fixed at month-start AUM; no intra-month rebalance.
    At month-end (every 30 days), the cumulative P&L is locked in.
    """
    aum = initial
    month_start_aum = aum
    pending_pnl = 0.0
    equity = [aum]
    effective_returns = []
    cash_buffer = CASH_BUFFER_RATIO

    for day, r in enumerate(daily_ret, start=1):
        deployed = month_start_aum * (1.0 - cash_buffer)
        pnl = deployed * r
        pending_pnl += pnl

        if day % 30 == 0:
            aum = month_start_aum + pending_pnl
            month_start_aum = aum
            pending_pnl = 0.0

        equity.append(aum + pending_pnl)
        effective_returns.append(pnl / equity[-2])

    return np.array(equity[1:]), np.array(effective_returns)


def strategy_fixed_fraction_50(daily_ret: np.ndarray, initial: float) -> tuple[np.ndarray, np.ndarray]:
    """
    S4 — Fixed-fraction profit-taking: 50% reinvest, 50% to cash buffer.
    Weekly rebalance cadence; half of weekly gains withdrawn.
    """
    return strategy_weekly_rebalance(daily_ret, initial, reinvest_frac=0.50)


def strategy_profit_lock_mdd(daily_ret: np.ndarray, initial: float,
                              lock_threshold_pct: float = 15.0,
                              withdraw_frac: float = 0.30) -> tuple[np.ndarray, np.ndarray]:
    """
    S5 — Profit-locking (MDD-based).
    If cumulative return from last withdrawal exceeds lock_threshold_pct,
    withdraw withdraw_frac of accumulated gains to cash.
    Zero withdrawal during drawdown periods.
    """
    aum = initial
    peak_aum = initial
    last_lock_aum = initial
    equity = [aum]
    effective_returns = []
    cash_buffer = CASH_BUFFER_RATIO

    for r in daily_ret:
        deployed = aum * (1.0 - cash_buffer)
        pnl = deployed * r
        aum += pnl

        # Update peak
        if aum > peak_aum:
            peak_aum = aum

        # Profit-lock trigger: if gain since last lock > threshold
        gain_since_lock = (aum - last_lock_aum) / last_lock_aum * 100.0
        in_drawdown = aum < peak_aum * 0.999  # Minor tolerance

        if gain_since_lock >= lock_threshold_pct and not in_drawdown:
            # Withdraw withdraw_frac of the gain
            gain_abs = aum - last_lock_aum
            withdrawal = gain_abs * withdraw_frac
            aum -= withdrawal
            last_lock_aum = aum
            # Withdrawn to cash (not tracked in equity, conservative)

        equity.append(aum)
        effective_returns.append(pnl / equity[-2])

    return np.array(equity[1:]), np.array(effective_returns)


def strategy_drift_tolerant(daily_ret: np.ndarray, initial: float,
                             drift_threshold_pp: float = 5.0) -> tuple[np.ndarray, np.ndarray]:
    """
    S6 — Drift-tolerant rebalance.
    Rebalance only when a sleeve's effective weight deviates > drift_threshold_pp
    from target. Approximated as: rebalance when cumulative drift exceeds threshold.

    For a single-sleeve model, this approximates to: rebalance when weekly
    compound return changes the effective leverage by > 5pp.
    """
    aum = initial
    last_rebal_aum = initial
    equity = [aum]
    effective_returns = []
    cash_buffer = CASH_BUFFER_RATIO

    for day, r in enumerate(daily_ret, start=1):
        deployed = aum * (1.0 - cash_buffer)
        pnl = deployed * r
        aum += pnl

        # Check drift: if current weight vs target differs by > threshold
        current_deployed_frac = deployed / aum if aum > 0 else 0
        target_deployed_frac  = 1.0 - cash_buffer
        drift_pp = abs(current_deployed_frac - target_deployed_frac) * 100.0

        # Also rebalance weekly at minimum (operational constraint)
        if drift_pp > drift_threshold_pp or day % 7 == 0:
            last_rebal_aum = aum

        equity.append(aum)
        effective_returns.append(pnl / equity[-2])

    return np.array(equity[1:]), np.array(effective_returns)


# ══════════════════════════════════════════════════════════════════════════════
# PROFIT-TAKING POLICY VARIANTS (Phase 5)
# ══════════════════════════════════════════════════════════════════════════════

def _pt_variant_7d_5pct_50withdraw(daily_ret: np.ndarray, initial: float) -> tuple[np.ndarray, np.ndarray]:
    """Withdraw 50% if 7d return > 5%."""
    aum = initial
    equity = [aum]
    effective_returns = []
    rolling_7d = []
    cash_buffer = CASH_BUFFER_RATIO

    for r in daily_ret:
        deployed = aum * (1.0 - cash_buffer)
        pnl = deployed * r
        aum += pnl
        rolling_7d.append(r)
        if len(rolling_7d) > 7:
            rolling_7d.pop(0)

        if len(rolling_7d) == 7:
            ret_7d = float(np.prod([1 + x for x in rolling_7d])) - 1.0
            if ret_7d > 0.05:
                gain = aum - initial  # simplified: gain from start
                if gain > 0:
                    aum -= gain * 0.50

        equity.append(aum)
        effective_returns.append(pnl / equity[-2])

    return np.array(equity[1:]), np.array(effective_returns)


def _pt_variant_weekly_25pct(daily_ret: np.ndarray, initial: float) -> tuple[np.ndarray, np.ndarray]:
    """Withdraw 25% weekly."""
    aum = initial
    equity = [aum]
    effective_returns = []
    cash_buffer = CASH_BUFFER_RATIO
    week_start_aum = aum

    for day, r in enumerate(daily_ret, start=1):
        deployed = aum * (1.0 - cash_buffer)
        pnl = deployed * r
        aum += pnl

        if day % 7 == 0:
            week_gain = aum - week_start_aum
            if week_gain > 0:
                aum -= week_gain * 0.25
            week_start_aum = aum

        equity.append(aum)
        effective_returns.append(pnl / equity[-2])

    return np.array(equity[1:]), np.array(effective_returns)


def _pt_variant_dd_locked(daily_ret: np.ndarray, initial: float) -> tuple[np.ndarray, np.ndarray]:
    """Drawdown-locked: 0% if in drawdown, 50% if at peak (weekly)."""
    aum = initial
    peak = initial
    equity = [aum]
    effective_returns = []
    cash_buffer = CASH_BUFFER_RATIO

    for day, r in enumerate(daily_ret, start=1):
        deployed = aum * (1.0 - cash_buffer)
        pnl = deployed * r
        aum += pnl
        peak = max(peak, aum)

        if day % 7 == 0:
            in_dd = aum < peak * 0.9995
            if not in_dd:
                week_gain = aum - (equity[-7] if len(equity) >= 7 else initial)
                if week_gain > 0:
                    aum -= week_gain * 0.50

        equity.append(aum)
        effective_returns.append(pnl / equity[-2])

    return np.array(equity[1:]), np.array(effective_returns)


# ══════════════════════════════════════════════════════════════════════════════
# MAIN SIMULATION
# ══════════════════════════════════════════════════════════════════════════════

def run_simulation() -> dict[str, Any]:
    """Run all compounding strategy simulations and return results dict."""

    print("[compounding_simulator] Loading v6.13d daily returns...")
    base_returns = _load_v613d_composite_returns()
    sim_returns  = _generate_sim_returns(SIM_DAYS, base_returns)
    print(f"[compounding_simulator] Simulation days: {len(sim_returns)}, "
          f"mean={np.mean(sim_returns)*100:.4f}%, std={np.std(sim_returns)*100:.4f}%")

    strategies = {
        "S1_daily_reinvest_100": lambda r: strategy_daily_reinvest_100(r, INITIAL_AUM_USD),
        "S2_weekly_100reinvest": lambda r: strategy_weekly_rebalance(r, INITIAL_AUM_USD, 1.0),
        "S3_monthly_fixed":      lambda r: strategy_monthly_fixed(r, INITIAL_AUM_USD),
        "S4_weekly_50reinvest":  lambda r: strategy_fixed_fraction_50(r, INITIAL_AUM_USD),
        "S5_profit_lock_15pct":  lambda r: strategy_profit_lock_mdd(r, INITIAL_AUM_USD, 15.0, 0.30),
        "S6_drift_tolerant_5pp": lambda r: strategy_drift_tolerant(r, INITIAL_AUM_USD, 5.0),
    }

    pt_variants = {
        "PT1_7d_5pct_50withdraw": lambda r: _pt_variant_7d_5pct_50withdraw(r, INITIAL_AUM_USD),
        "PT2_weekly_25pct":       lambda r: _pt_variant_weekly_25pct(r, INITIAL_AUM_USD),
        "PT3_dd_locked_50pct":    lambda r: _pt_variant_dd_locked(r, INITIAL_AUM_USD),
    }

    results = {}

    print("[compounding_simulator] Running 6 main strategies...")
    for name, fn in strategies.items():
        equity, ret = fn(sim_returns)
        m = compute_metrics(equity, ret)
        results[name] = m
        print(f"  {name:35s} CAGR={m['cagr_pct']:7.3f}% | Terminal=${m['terminal_usd']:,.0f} "
              f"| MaxDD=${m['max_dd_abs_usd']:,.0f} | Sharpe={m['sharpe']:.2f}")

    print("[compounding_simulator] Running 3 profit-taking variants...")
    pt_results = {}
    for name, fn in pt_variants.items():
        equity, ret = fn(sim_returns)
        m = compute_metrics(equity, ret)
        pt_results[name] = m
        print(f"  {name:35s} CAGR={m['cagr_pct']:7.3f}% | Terminal=${m['terminal_usd']:,.0f} "
              f"| MaxDD=${m['max_dd_abs_usd']:,.0f} | Sharpe={m['sharpe']:.2f}")

    # Build comparison table sorted by CAGR
    comparison = sorted(
        [{"strategy": k, **v} for k, v in results.items()],
        key=lambda x: x["cagr_pct"], reverse=True
    )

    # Profit delta: best vs worst
    cagrs = {k: v["cagr_pct"] for k, v in results.items()}
    best  = max(cagrs, key=cagrs.get)
    worst = min(cagrs, key=cagrs.get)
    profit_delta = results[best]["terminal_usd"] - results[worst]["terminal_usd"]

    # Cash buffer analysis
    cash_buffer_analysis = {
        "recommended_pct": 8.0,
        "min_margin_req_pct": 5.0,
        "emergency_exit_buffer_pct": 2.0,
        "14d_worst_loss_buffer_pct": 1.0,
        "rationale": (
            "8% cash buffer: 5% HL margin reserve + 2% emergency exit (K357) "
            "+ 1% 14-day worst-loss buffer. Leaves 92% deployed for v6.13d."
        ),
    }

    output = {
        "simulation_params": {
            "initial_aum_usd":    INITIAL_AUM_USD,
            "sim_years":          SIM_YEARS,
            "sim_days":           SIM_DAYS,
            "cash_buffer_ratio":  CASH_BUFFER_RATIO,
            "daily_mean_pct":     round(float(np.mean(sim_returns)) * 100, 6),
            "daily_std_pct":      round(float(np.std(sim_returns)) * 100, 6),
            "source":             "v6.13d K346 composite (K280×0.75 + K297'×0.20 + sUSDe×0.05)",
        },
        "strategy_results":       results,
        "profit_taking_variants": pt_results,
        "comparison_table":       comparison,
        "profit_delta_usd":       round(profit_delta, 2),
        "best_strategy":          best,
        "worst_strategy":         worst,
        "cash_buffer_analysis":   cash_buffer_analysis,
    }

    return output


if __name__ == "__main__":
    results = run_simulation()
    out_path = LAB_ROOT / "wave_k428_sim_results.json"
    out_path.write_text(json.dumps(results, indent=2))
    print(f"\n[compounding_simulator] Saved results → {out_path}")
