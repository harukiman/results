"""
portfolio_aum_manager.py — K429 Daily Reinvest AUM Tracking Manager
=====================================================================
K428 S1 finding: daily compounding @ $10M AUM → +$3.6M / 5y vs static sizing.
This module provides single-source-of-truth AUM state management with:
  - 8% cash buffer maintained at all times
  - PT1 safety valve (7d return > +5% → 50% of gains to cash_buffer)
  - Atomic file writes (write-then-rename) for concurrency safety
  - Per-sleeve position sizing from deployed_capital × sleeve_weight
  - Daily append to cache/portfolio_aum_history.jsonl

Architecture:
  data/portfolio_aum_state.json  — single source of truth
  cache/portfolio_aum_history.jsonl — append-only daily snapshots

Sleeve weights (apply to deployed_capital, not AUM):
  K280:        75%  →  position = deployed_capital × 0.75
  K297_prime:  20%  →  position = deployed_capital × 0.20
  sUSDe:        5%  →  position = deployed_capital × 0.05
  K376:         3%  →  position = deployed_capital × 0.03  (v6.14 candidate)

Note: K376 is experimental (3% within the 100% weight budget, sub-allocated from
deployed_capital). The sum K280+K297_prime+sUSDe = 100%; K376 is a sub-slice of K280.

K339 security rule: REPO_ROOT = Path(__file__).resolve().parent.parent

Usage:
  from portfolio_aum_manager import (
      load_state, compute_position_size, update_aum,
      check_pt1_safety, apply_pt1_withdrawal, get_current_metrics
  )

  # At startup of each sleeve script:
  state = load_state()
  my_target_usdc = compute_position_size("K280")

  # After computing today's PnL:
  update_aum(my_sleeve_pnl_usdc)

  # Primary (K280) checks PT1:
  if check_pt1_safety(rolling_7d_return_pct):
      apply_pt1_withdrawal()

Environment:
  AUM_TRACKING_ENABLED=False  — disable AUM tracking (default: True)
  INITIAL_AUM_USDC=10000000   — override initial AUM (default: $10M)
"""
from __future__ import annotations

import json
import os
import tempfile
import time
from collections import deque
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, Optional

# ── K339 Security: REPO_ROOT from __file__, no /Users/ literals ───────────────
REPO_ROOT = Path(__file__).resolve().parent.parent
DATA      = REPO_ROOT / "data"
CACHE     = REPO_ROOT / "cache"
DATA.mkdir(exist_ok=True)
CACHE.mkdir(exist_ok=True)

AUM_STATE_JSON   = DATA  / "portfolio_aum_state.json"
AUM_HISTORY_JSONL = CACHE / "portfolio_aum_history.jsonl"

# ── JST timezone ───────────────────────────────────────────────────────────────
JST = timezone(timedelta(hours=9))

# ── Configuration ──────────────────────────────────────────────────────────────
AUM_TRACKING_ENABLED = os.environ.get("AUM_TRACKING_ENABLED", "true").lower() != "false"

# Default initial values (overridable via env)
_DEFAULT_AUM   = float(os.environ.get("INITIAL_AUM_USDC",   "10000000"))   # $10M
_CASH_BUFFER_PCT = 0.08   # 8% cash buffer
_DEPLOYED_PCT    = 0.92   # 92% deployed

# PT1 safety valve parameters
PT1_TRIGGER_PCT   = 5.0   # 7d cumulative return > 5% fires PT1
PT1_WITHDRAW_PCT  = 0.50  # 50% of recent gains → cash_buffer

# Default sleeve weights (applied to deployed_capital)
DEFAULT_SLEEVE_WEIGHTS: Dict[str, float] = {
    "K280":       0.75,
    "K297_prime": 0.20,
    "sUSDe":      0.05,
    "K376":       0.03,   # sub-slice of K280 (v6.14 candidate; 3% of deployed)
}


# ─────────────────────────────────────────────────────────────────────────────
# State I/O helpers
# ─────────────────────────────────────────────────────────────────────────────

def _default_state() -> dict:
    """Return the initial default state for a $10M AUM portfolio."""
    now_jst = datetime.now(JST).strftime("%Y-%m-%d %H:%M JST")
    aum     = _DEFAULT_AUM
    cash    = aum * _CASH_BUFFER_PCT
    deploy  = aum * _DEPLOYED_PCT
    return {
        "last_updated_jst":        now_jst,
        "last_updated_utc":        datetime.now(timezone.utc).isoformat(),
        "current_aum_usdc":        aum,
        "cash_buffer_usdc":        cash,
        "deployed_capital_usdc":   deploy,
        "cumulative_pnl_usdc":     0.0,
        "cumulative_pnl_pct":      0.0,
        "max_drawdown_usdc":       0.0,
        "peak_aum_usdc":           aum,
        "pt1_safety_active":       False,
        "pt1_last_triggered_jst":  None,
        "pt1_trigger_count":       0,
        "7d_rolling_return_pct":   0.0,
        "7d_daily_pnl_history":    [],   # list of up to 7 daily fractional returns
        "day_count":               0,
        "sleeve_weights":          DEFAULT_SLEEVE_WEIGHTS,
        "initial_aum_usdc":        aum,
    }


def load_state() -> dict:
    """
    Load portfolio AUM state from data/portfolio_aum_state.json.
    If file does not exist, returns (and saves) the default $10M state.
    """
    if not AUM_STATE_JSON.exists():
        state = _default_state()
        _atomic_save(state)
        return state
    try:
        with open(AUM_STATE_JSON) as f:
            state = json.load(f)
        # Backfill missing keys from default
        default = _default_state()
        for k, v in default.items():
            if k not in state:
                state[k] = v
        return state
    except (json.JSONDecodeError, OSError) as exc:
        print(f"[AUM] WARNING: Failed to load state ({exc}). Using defaults.")
        return _default_state()


def _atomic_save(state: dict) -> None:
    """
    Save state atomically using write-to-temp + rename pattern.
    Prevents partial writes from corrupting the state file.
    """
    try:
        tmp = AUM_STATE_JSON.parent / f".portfolio_aum_state_tmp_{os.getpid()}.json"
        with open(tmp, "w") as f:
            json.dump(state, f, indent=2)
        tmp.rename(AUM_STATE_JSON)
    except OSError as exc:
        print(f"[AUM] ERROR: Failed to save state: {exc}")


def _append_history(state: dict) -> None:
    """Append current state snapshot to cache/portfolio_aum_history.jsonl."""
    record = {
        "ts_jst":              state.get("last_updated_jst"),
        "ts_utc":              state.get("last_updated_utc"),
        "day":                 state.get("day_count", 0),
        "current_aum_usdc":    state.get("current_aum_usdc"),
        "deployed_capital_usdc": state.get("deployed_capital_usdc"),
        "cash_buffer_usdc":    state.get("cash_buffer_usdc"),
        "cumulative_pnl_usdc": state.get("cumulative_pnl_usdc"),
        "cumulative_pnl_pct":  state.get("cumulative_pnl_pct"),
        "7d_rolling_return_pct": state.get("7d_rolling_return_pct"),
        "pt1_safety_active":   state.get("pt1_safety_active"),
        # Sleeve allocations (live $ amounts)
        "sleeve_allocations_usdc": {
            sleeve: round(state["deployed_capital_usdc"] * weight, 2)
            for sleeve, weight in state.get("sleeve_weights", {}).items()
        },
    }
    try:
        with open(AUM_HISTORY_JSONL, "a") as f:
            f.write(json.dumps(record) + "\n")
    except OSError as exc:
        print(f"[AUM] WARNING: Failed to append history: {exc}")


# ─────────────────────────────────────────────────────────────────────────────
# Core API
# ─────────────────────────────────────────────────────────────────────────────

def compute_position_size(sleeve_name: str, state: Optional[dict] = None) -> float:
    """
    Returns the USDC allocation for a given sleeve.

    Position size = deployed_capital_usdc × sleeve_weight

    E.g. at $10M AUM:
      deployed_capital = $10M × 92% = $9.2M
      K280 = $9.2M × 75% = $6.9M

    Args:
        sleeve_name: one of "K280", "K297_prime", "sUSDe", "K376"
        state:       optional pre-loaded state dict (avoids re-reading file)

    Returns:
        USDC amount to allocate to this sleeve, or 0.0 if sleeve not found.
    """
    if not AUM_TRACKING_ENABLED:
        return 0.0
    if state is None:
        state = load_state()
    weight = state.get("sleeve_weights", {}).get(sleeve_name, 0.0)
    return round(state["deployed_capital_usdc"] * weight, 2)


def update_aum(daily_pnl_usdc: float, sleeve_name: Optional[str] = None) -> dict:
    """
    Update portfolio AUM with today's PnL contribution from a sleeve.

    This function:
    1. Increments current_aum_usdc by daily_pnl_usdc
    2. Rebalances cash_buffer (8%) and deployed_capital (92%) proportionally
    3. Updates cumulative PnL, peak AUM, drawdown
    4. Appends to 7d rolling return history
    5. Atomically saves updated state
    6. Appends to history JSONL

    Args:
        daily_pnl_usdc:  today's PnL in USDC (positive = profit, negative = loss)
        sleeve_name:     optional label for logging (e.g. "K280")

    Returns:
        Updated state dict.
    """
    if not AUM_TRACKING_ENABLED:
        return {}

    state = load_state()
    old_aum = state["current_aum_usdc"]

    # ── Update AUM ────────────────────────────────────────────────────────────
    new_aum = old_aum + daily_pnl_usdc
    if new_aum < 0:
        new_aum = 0.0  # floor at 0

    # ── Rebalance: always maintain 8% cash / 92% deployed ────────────────────
    new_cash   = new_aum * _CASH_BUFFER_PCT
    new_deploy = new_aum * _DEPLOYED_PCT

    # ── Update cumulative PnL ─────────────────────────────────────────────────
    initial_aum  = state.get("initial_aum_usdc", old_aum)
    cum_pnl_usdc = new_aum - initial_aum
    cum_pnl_pct  = (cum_pnl_usdc / initial_aum * 100) if initial_aum > 0 else 0.0

    # ── Update peak AUM and drawdown ──────────────────────────────────────────
    peak_aum = state.get("peak_aum_usdc", old_aum)
    if new_aum > peak_aum:
        peak_aum = new_aum
    drawdown_usdc = new_aum - peak_aum  # negative or zero

    # ── 7d rolling return history (fractional daily return) ──────────────────
    daily_return_frac = (daily_pnl_usdc / old_aum) if old_aum > 0 else 0.0
    history_7d = list(state.get("7d_daily_pnl_history", []))
    history_7d.append(daily_return_frac)
    if len(history_7d) > 7:
        history_7d = history_7d[-7:]

    # 7d cumulative return as percentage
    rolling_7d_pct = sum(history_7d) * 100.0

    # ── Timestamps ────────────────────────────────────────────────────────────
    now_jst = datetime.now(JST).strftime("%Y-%m-%d %H:%M JST")
    now_utc = datetime.now(timezone.utc).isoformat()

    # ── Build updated state ───────────────────────────────────────────────────
    state.update({
        "last_updated_jst":       now_jst,
        "last_updated_utc":       now_utc,
        "current_aum_usdc":       round(new_aum, 2),
        "cash_buffer_usdc":       round(new_cash, 2),
        "deployed_capital_usdc":  round(new_deploy, 2),
        "cumulative_pnl_usdc":    round(cum_pnl_usdc, 2),
        "cumulative_pnl_pct":     round(cum_pnl_pct, 6),
        "max_drawdown_usdc":      round(drawdown_usdc, 2),
        "peak_aum_usdc":          round(peak_aum, 2),
        "7d_daily_pnl_history":   history_7d,
        "7d_rolling_return_pct":  round(rolling_7d_pct, 6),
        "day_count":              state.get("day_count", 0) + 1,
    })

    # ── Save state and log ────────────────────────────────────────────────────
    _atomic_save(state)
    _append_history(state)

    sleeve_label = f" [{sleeve_name}]" if sleeve_name else ""
    print(
        f"[AUM]{sleeve_label} Updated: PnL={daily_pnl_usdc:+,.2f} USDC | "
        f"AUM={new_aum:,.0f} | Deploy={new_deploy:,.0f} | "
        f"CumPnL={cum_pnl_pct:+.3f}% | 7d={rolling_7d_pct:+.3f}%"
    )
    return state


def check_pt1_safety(rolling_7d_return_pct: Optional[float] = None) -> bool:
    """
    Check whether PT1 safety valve should fire.

    PT1 trigger: 7d cumulative return > +5%
    "Essentially free" per K428 — given v6.13d 0.03%/day mean, 7d ≈ 0.2%,
    so this fires rarely (~1-2×/year) but provides psychological + tail protection.

    Args:
        rolling_7d_return_pct: override the 7d return from state (for testing).
                                If None, reads from state.

    Returns:
        True if PT1 should fire (caller should call apply_pt1_withdrawal()).
    """
    if not AUM_TRACKING_ENABLED:
        return False

    state = load_state()

    if rolling_7d_return_pct is None:
        rolling_7d_return_pct = state.get("7d_rolling_return_pct", 0.0)

    should_fire = rolling_7d_return_pct > PT1_TRIGGER_PCT

    if should_fire:
        print(
            f"[AUM][PT1] ⚠ Safety valve triggered: 7d return = {rolling_7d_return_pct:.3f}% "
            f"> {PT1_TRIGGER_PCT:.1f}% threshold. Call apply_pt1_withdrawal()."
        )
    return should_fire


def apply_pt1_withdrawal(amount_pct: float = PT1_WITHDRAW_PCT) -> dict:
    """
    Move `amount_pct` of recent gains from deployed_capital to cash_buffer.

    Default: move 50% of 7d gains to cash_buffer.
    This locks in partial profits while keeping 50% compounding.

    When to re-deploy:
      - 7d rolling return goes negative → call reactivate_from_cash()
      - Or user manually adjusts state JSON

    Args:
        amount_pct: fraction of recent gains to move to cash (default: 0.50)

    Returns:
        Updated state dict.
    """
    if not AUM_TRACKING_ENABLED:
        return {}

    state = load_state()
    now_jst = datetime.now(JST).strftime("%Y-%m-%d %H:%M JST")
    now_utc = datetime.now(timezone.utc).isoformat()

    aum        = state["current_aum_usdc"]
    initial    = state.get("initial_aum_usdc", aum)
    total_gain = aum - initial

    if total_gain <= 0:
        print("[AUM][PT1] No gains to protect (total_gain <= 0). Skipping.")
        return state

    # How much to move from deployed to cash
    gain_to_protect = total_gain * amount_pct
    deploy_reduction = gain_to_protect * _DEPLOYED_PCT  # only the deployed portion

    new_deploy = max(0.0, state["deployed_capital_usdc"] - deploy_reduction)
    new_cash   = aum - new_deploy  # cash = everything not deployed

    print(
        f"[AUM][PT1] Withdrawal: moving ${gain_to_protect:,.0f} gains to cash_buffer "
        f"({amount_pct*100:.0f}% of total ${total_gain:,.0f} gain). "
        f"Deploy: ${state['deployed_capital_usdc']:,.0f} → ${new_deploy:,.0f}"
    )

    state.update({
        "last_updated_jst":       now_jst,
        "last_updated_utc":       now_utc,
        "deployed_capital_usdc":  round(new_deploy, 2),
        "cash_buffer_usdc":       round(new_cash, 2),
        "pt1_safety_active":      True,
        "pt1_last_triggered_jst": now_jst,
        "pt1_trigger_count":      state.get("pt1_trigger_count", 0) + 1,
    })

    _atomic_save(state)
    _append_history(state)
    return state


def reactivate_from_cash(target_deploy_pct: float = _DEPLOYED_PCT) -> dict:
    """
    Re-deploy from cash_buffer when 7d return goes negative after PT1.
    Restores the standard 8% cash / 92% deployed split.

    Args:
        target_deploy_pct: fraction of AUM to deploy (default: 92%)

    Returns:
        Updated state dict.
    """
    if not AUM_TRACKING_ENABLED:
        return {}

    state = load_state()
    now_jst = datetime.now(JST).strftime("%Y-%m-%d %H:%M JST")
    now_utc = datetime.now(timezone.utc).isoformat()

    aum        = state["current_aum_usdc"]
    new_deploy = aum * target_deploy_pct
    new_cash   = aum * (1 - target_deploy_pct)

    old_deploy = state["deployed_capital_usdc"]
    print(
        f"[AUM][PT1] Reactivating: deploy ${old_deploy:,.0f} → ${new_deploy:,.0f}. "
        f"PT1 safety released."
    )

    state.update({
        "last_updated_jst":      now_jst,
        "last_updated_utc":      now_utc,
        "deployed_capital_usdc": round(new_deploy, 2),
        "cash_buffer_usdc":      round(new_cash, 2),
        "pt1_safety_active":     False,
    })

    _atomic_save(state)
    _append_history(state)
    return state


def get_current_metrics() -> dict:
    """
    Return a summary of current AUM metrics for dashboard display.

    Returns:
        Dict with:
          current_aum_usdc, deployed_capital_usdc, cash_buffer_usdc,
          cumulative_pnl_usdc, cumulative_pnl_pct,
          7d_rolling_return_pct, pt1_safety_active,
          peak_aum_usdc, max_drawdown_usdc,
          sleeve_allocations_usdc (live $ amounts per sleeve),
          last_updated_jst
    """
    if not AUM_TRACKING_ENABLED:
        return {"aum_tracking_enabled": False}

    state = load_state()
    allocations = {
        sleeve: round(state["deployed_capital_usdc"] * weight, 2)
        for sleeve, weight in state.get("sleeve_weights", {}).items()
    }

    return {
        "aum_tracking_enabled":   True,
        "current_aum_usdc":       state.get("current_aum_usdc"),
        "deployed_capital_usdc":  state.get("deployed_capital_usdc"),
        "cash_buffer_usdc":       state.get("cash_buffer_usdc"),
        "cash_buffer_pct":        round(
            state.get("cash_buffer_usdc", 0) / state.get("current_aum_usdc", 1) * 100, 2
        ),
        "cumulative_pnl_usdc":    state.get("cumulative_pnl_usdc"),
        "cumulative_pnl_pct":     state.get("cumulative_pnl_pct"),
        "7d_rolling_return_pct":  state.get("7d_rolling_return_pct"),
        "pt1_safety_active":      state.get("pt1_safety_active"),
        "pt1_last_triggered_jst": state.get("pt1_last_triggered_jst"),
        "peak_aum_usdc":          state.get("peak_aum_usdc"),
        "max_drawdown_usdc":      state.get("max_drawdown_usdc"),
        "max_drawdown_pct":       round(
            state.get("max_drawdown_usdc", 0) / state.get("peak_aum_usdc", 1) * 100, 4
        ),
        "day_count":              state.get("day_count", 0),
        "sleeve_allocations_usdc": allocations,
        "sleeve_weights":         state.get("sleeve_weights", {}),
        "last_updated_jst":       state.get("last_updated_jst"),
    }


# ─────────────────────────────────────────────────────────────────────────────
# CLI: status display and simulation utilities
# ─────────────────────────────────────────────────────────────────────────────

def _fmt_usd(v: float) -> str:
    if v is None:
        return "—"
    if abs(v) >= 1_000_000:
        return f"${v/1_000_000:+.3f}M"
    if abs(v) >= 1_000:
        return f"${v/1_000:+.2f}K"
    return f"${v:+.2f}"


def print_status() -> None:
    """Pretty-print current AUM status to stdout."""
    m = get_current_metrics()
    if not m.get("aum_tracking_enabled"):
        print("[AUM] Tracking disabled (AUM_TRACKING_ENABLED=False)")
        return

    print("\n" + "=" * 60)
    print("  K429 Portfolio AUM Status")
    print("=" * 60)
    print(f"  Last Updated:      {m['last_updated_jst']}")
    print(f"  Day Count:         {m['day_count']}")
    print(f"  Current AUM:       {_fmt_usd(m['current_aum_usdc'])}")
    print(f"  Deployed Capital:  {_fmt_usd(m['deployed_capital_usdc'])} ({100*_DEPLOYED_PCT:.0f}%)")
    print(f"  Cash Buffer:       {_fmt_usd(m['cash_buffer_usdc'])} ({m['cash_buffer_pct']:.1f}%)")
    print(f"  Cumulative PnL:    {_fmt_usd(m['cumulative_pnl_usdc'])} ({m['cumulative_pnl_pct']:+.3f}%)")
    print(f"  7d Rolling Return: {m['7d_rolling_return_pct']:+.4f}%")
    print(f"  Peak AUM:          {_fmt_usd(m['peak_aum_usdc'])}")
    print(f"  Max Drawdown:      {_fmt_usd(m['max_drawdown_usdc'])} ({m['max_drawdown_pct']:+.4f}%)")
    print(f"  PT1 Safety Active: {m['pt1_safety_active']}")
    if m.get("pt1_last_triggered_jst"):
        print(f"  PT1 Last Trigger:  {m['pt1_last_triggered_jst']}")

    print("\n  Sleeve Allocations (deployed_capital × weight):")
    for sleeve, alloc_usdc in (m.get("sleeve_allocations_usdc") or {}).items():
        w = m.get("sleeve_weights", {}).get(sleeve, 0.0)
        print(f"    {sleeve:<14}  {w*100:5.1f}%  →  {_fmt_usd(alloc_usdc)}")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="K429 Portfolio AUM Manager")
    parser.add_argument("--status",   action="store_true", help="Print current status")
    parser.add_argument("--init",     action="store_true", help="Initialize/reset state to defaults")
    parser.add_argument("--sim-pnl",  type=float,          help="Simulate a PnL update (USDC)")
    parser.add_argument("--check-pt1",action="store_true", help="Check PT1 safety valve")
    parser.add_argument("--pt1-fire", action="store_true", help="Manually fire PT1 withdrawal")
    parser.add_argument("--reactivate",action="store_true",help="Reactivate from cash after PT1")
    args = parser.parse_args()

    if args.init:
        state = _default_state()
        _atomic_save(state)
        print(f"[AUM] State initialized at {AUM_STATE_JSON}")

    if args.sim_pnl is not None:
        update_aum(args.sim_pnl, sleeve_name="SIM")

    if args.check_pt1:
        state = load_state()
        rolling = state.get("7d_rolling_return_pct", 0.0)
        fires   = check_pt1_safety(rolling)
        print(f"[AUM] 7d return: {rolling:.4f}% — PT1 {'FIRES' if fires else 'does not fire'}")

    if args.pt1_fire:
        apply_pt1_withdrawal()

    if args.reactivate:
        reactivate_from_cash()

    print_status()
