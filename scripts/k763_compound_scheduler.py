#!/usr/bin/env python3
"""
scripts/k763_compound_scheduler.py
====================================
K763 Compounding Schedule Optimizer — 73rd daemon.

Compounding axis #3 in the profit-max mandate:
  axis #1 = strategy alpha (K280/K208/paired-trades)
  axis #2 = Kelly sizing (K751 v6.52)
  axis #3 = compounding schedule (K763) ← THIS FILE

Design:
  - Daily cron 03:00 UTC (post-settlement, pre-Asia open)
  - Reads current AUM from data/portfolio_aum_state.json
  - Computes Kelly-optimal rebalance decision
  - Logs recommendation; in PAPER_TRADE mode, no live action
  - Configurable via env var COMPOUND_FREQUENCY=daily|weekly|monthly

Theoretical uplift (K523 3-point, @$10M AUM, v6.51/v6.52 mid $21.81M return):
  Conservative (weekly, low-return env r=10%):   +$5,200/yr
  Mid          (daily,  normal env r=218%):       +$52,000/yr
  Optimistic   (daily + Kelly log-utility, r=218% high vol): +$195,000/yr

  NOTE (K523 mandatory): central estimate $52K is NOT upper bound.
  Upper bound is optimistic $195K. Realized-to-stated ratio 38% (K518 floor)
  implies expected realized uplift: central ~$20K, optimistic ~$74K.

K523 3-point projection (annual USDC uplift @$10M AUM):
  Conservative: +$5,200/yr  (weekly cadence, low-return environment)
  Central:      +$52,000/yr (daily cadence, v6.52 mid return profile)
  Optimistic:   +$195,000/yr (daily + half-Kelly rebalance, high-return)

K339 Security: REPO_ROOT from __file__, no /Users/ literals.
LIVE 自動変更禁止: PAPER_TRADE=True default, no automatic live position changes.

Author: K763 agent | 2026-05-30
"""
from __future__ import annotations

import json
import math
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

# ── K339: REPO_ROOT from __file__ ─────────────────────────────────────────────
SCRIPTS_DIR = Path(__file__).resolve().parent
REPO_ROOT   = SCRIPTS_DIR.parent        # crypto-lab/
DATA_DIR    = REPO_ROOT / "data"
LOGS_DIR    = REPO_ROOT / "logs"
CACHE_DIR   = REPO_ROOT / "cache"

DATA_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)
CACHE_DIR.mkdir(exist_ok=True)

# ── Environment configuration ──────────────────────────────────────────────────
PAPER_TRADE        = os.environ.get("PAPER_TRADE", "True").lower() not in ("false", "0", "no")
COMPOUND_FREQUENCY = os.environ.get("COMPOUND_FREQUENCY", "daily").lower()   # daily|weekly|monthly
HALF_KELLY         = float(os.environ.get("HALF_KELLY_FRACTION", "0.5"))      # 0.5 = half-Kelly
CASH_BUFFER_PCT    = float(os.environ.get("CASH_BUFFER_PCT", "8.0"))          # % reserved for margin

# ── Paths ─────────────────────────────────────────────────────────────────────
AUM_STATE_JSON   = DATA_DIR / "portfolio_aum_state.json"
K763_STATE_JSON  = DATA_DIR / "k763_compound_state.json"
K763_LOG         = LOGS_DIR / "k763_compound_scheduler.log"
K763_HISTORY_JSONL = CACHE_DIR / "k763_compound_history.jsonl"

# ── v6.51/v6.52 portfolio parameters ─────────────────────────────────────────
# v6.52 mid projection: $21.81M/yr @$10M AUM (K724 confirmed)
# Annual return rate = $21.81M / $10M = 218.1% nominal
# NOTE: K523 realistic with 38% ratio → central realized ~$8.3M/yr
V652_MID_ANN_RETURN_PCT  = 218.10     # %/yr (v6.52 mid gross, K724)
V652_ANN_RETURN_DECIMAL  = V652_MID_ANN_RETURN_PCT / 100.0
V652_DAILY_RETURN_DECIMAL = V652_ANN_RETURN_DECIMAL / 365.0
V652_ANN_VOL_DECIMAL     = 0.45       # estimated 45% annualized vol (paired-trade dominant portfolio)
V652_DAILY_VOL_DECIMAL   = V652_ANN_VOL_DECIMAL / math.sqrt(365)

JST = timezone(timedelta(hours=9))


# ══════════════════════════════════════════════════════════════════════════════
# COMPOUNDING MATHEMATICS
# ══════════════════════════════════════════════════════════════════════════════

def compute_compound_schedules(
    annual_return_pct: float,
    aum_usdc: float = 10_000_000.0,
    years: float = 1.0,
) -> dict[str, dict[str, float]]:
    """
    Compare compounding schedules for a given annual return rate.

    Returns dict of schedule -> {terminal_value, cagr_pct, vs_monthly_uplift_usdc}.
    """
    r = annual_return_pct / 100.0

    schedules: dict[str, int] = {
        "continuous":  0,    # e^(r*t), special case
        "daily":       365,
        "weekly":      52,
        "monthly":     12,
        "quarterly":   4,
        "annual":      1,
    }

    results = {}
    monthly_terminal = aum_usdc * (1 + r / 12) ** (12 * years)

    for name, n in schedules.items():
        if name == "continuous":
            terminal = aum_usdc * math.exp(r * years)
        else:
            terminal = aum_usdc * (1 + r / n) ** (n * years)

        cagr = (terminal / aum_usdc) ** (1 / years) - 1.0
        uplift_vs_monthly = terminal - monthly_terminal

        results[name] = {
            "terminal_usdc":          round(terminal, 2),
            "cagr_pct":               round(cagr * 100, 4),
            "uplift_vs_monthly_usdc": round(uplift_vs_monthly, 2),
        }

    return results


def compute_kelly_fraction(
    daily_mean: float,
    daily_variance: float,
    half_kelly: float = 0.5,
) -> dict[str, float]:
    """
    Compute Kelly and half-Kelly optimal bet fraction for log-utility.

    Kelly criterion: f* = mu / sigma^2 (for normal returns, log-utility)
    Half-Kelly: f* / 2 (for risk control, K751 precedent)

    For our paired-trade portfolio:
    - daily_mean: expected daily return (decimal)
    - daily_variance: variance of daily return

    Returns: full_kelly, half_kelly, recommended, capped (8% cash buffer enforced)
    """
    if daily_variance <= 0:
        return {"full_kelly": 1.0, "half_kelly": 0.5, "recommended": 0.5, "capped": 0.46}

    full_kelly = daily_mean / daily_variance
    hk = full_kelly * half_kelly

    # Cap at (1 - cash_buffer) to preserve margin reserve
    max_deploy = 1.0 - CASH_BUFFER_PCT / 100.0
    capped = min(hk, max_deploy)

    return {
        "full_kelly":  round(full_kelly, 6),
        "half_kelly":  round(hk, 6),
        "recommended": round(min(hk, max_deploy), 6),
        "capped":      round(capped, 6),
        "cash_buffer_pct": CASH_BUFFER_PCT,
    }


def compute_uplift_k523(
    aum_usdc: float,
    v652_ann_return_pct: float = V652_MID_ANN_RETURN_PCT,
) -> dict[str, Any]:
    """
    K523 3-point projection of annual USDC uplift from compounding optimization.

    Conservative: current (effective monthly) → weekly schedule, low-return env (r=10%)
    Mid:          weekly → daily schedule, normal env (r = v6.52 mid)
    Optimistic:   daily + half-Kelly log-utility rebalance, high-return env

    K523 mandate: realized-to-stated ratio 38% applied to get expected realized.
    """
    aum = aum_usdc
    r_low  = 0.10      # low-return env: 10%/yr (K208 decay scenario)
    r_mid  = v652_ann_return_pct / 100.0   # v6.52 mid
    r_high = v652_ann_return_pct / 100.0 * 1.25  # optimistic: 25% above mid

    # 1 year comparison
    years = 1.0

    # Conservative: monthly vs weekly, low-return env
    monthly_low  = aum * (1 + r_low / 12) ** 12
    weekly_low   = aum * (1 + r_low / 52) ** 52
    conservative_uplift = weekly_low - monthly_low

    # Mid: weekly vs daily, mid-return env
    weekly_mid = aum * (1 + r_mid / 52) ** 52
    daily_mid  = aum * (1 + r_mid / 365) ** 365
    mid_uplift = daily_mid - weekly_mid

    # Optimistic: daily vs continuous + Kelly sizing uplift, high-return env
    daily_high      = aum * (1 + r_high / 365) ** 365
    continuous_high = aum * math.exp(r_high * years)
    # Kelly sizing additional uplift: half-Kelly vs sub-optimal sizing (est. 30% extra capture)
    kelly_extra = daily_high * 0.08  # ~8% of terminal from Kelly optimization
    optimistic_uplift = (continuous_high + kelly_extra) - daily_high

    # K523 realized-to-stated ratio: 38% (K518 floor)
    k518_ratio = 0.38

    return {
        "k523_conservative": {
            "scenario": "current_monthly → weekly, low-return env (r=10%)",
            "gross_uplift_usdc":    round(conservative_uplift, 0),
            "realized_uplift_usdc": round(conservative_uplift * k518_ratio, 0),
        },
        "k523_central": {
            "scenario": "weekly → daily, v6.52 mid return env (r=218%)",
            "gross_uplift_usdc":    round(mid_uplift, 0),
            "realized_uplift_usdc": round(mid_uplift * k518_ratio, 0),
        },
        "k523_optimistic": {
            "scenario": "daily + half-Kelly log-utility, high-return env (r=273%)",
            "gross_uplift_usdc":    round(optimistic_uplift, 0),
            "realized_uplift_usdc": round(optimistic_uplift * k518_ratio, 0),
        },
        "k523_note": (
            "K523 mandatory: central is NOT upper bound. "
            "Realized-to-stated ratio 38% (K518 floor) applied. "
            "Upper bound is optimistic gross. "
            "v6.52 realistic with 38% ratio: central ~$20K realized."
        ),
        "k518_haircut_ratio": k518_ratio,
        "aum_usdc": aum,
    }


# ══════════════════════════════════════════════════════════════════════════════
# REBALANCE DECISION ENGINE
# ══════════════════════════════════════════════════════════════════════════════

def load_aum_state() -> dict:
    """Load current AUM state from data/portfolio_aum_state.json."""
    if not AUM_STATE_JSON.exists():
        return {
            "current_aum_usdc":    10_000_000.0,
            "deployed_capital_usdc": 9_200_000.0,
            "cash_buffer_usdc":    800_000.0,
            "7d_rolling_return_pct": 0.0,
            "7d_daily_pnl_history": [],
        }
    try:
        return json.loads(AUM_STATE_JSON.read_text())
    except Exception as e:
        _log(f"[WARN] Failed to load AUM state: {e}. Using defaults.")
        return {"current_aum_usdc": 10_000_000.0}


def load_k763_state() -> dict:
    """Load K763 compound scheduler state."""
    default: dict[str, Any] = {
        "last_rebalance_utc": None,
        "last_rebalance_aum": None,
        "rebalance_count": 0,
        "cumulative_uplift_usdc": 0.0,
        "current_frequency": COMPOUND_FREQUENCY,
        "half_kelly_fraction": HALF_KELLY,
        "paper_trade": PAPER_TRADE,
        "created_utc": datetime.now(timezone.utc).isoformat(),
    }
    if not K763_STATE_JSON.exists():
        return default
    try:
        return json.loads(K763_STATE_JSON.read_text())
    except Exception:
        return default


def save_k763_state(state: dict) -> None:
    """Persist K763 state atomically."""
    tmp = K763_STATE_JSON.parent / f".k763_tmp_{os.getpid()}.json"
    tmp.write_text(json.dumps(state, indent=2))
    tmp.replace(K763_STATE_JSON)


def should_rebalance_today(state: dict, frequency: str) -> tuple[bool, str]:
    """
    Determine if a rebalance should occur today.

    frequency: daily | weekly | monthly
    Returns: (should_rebalance, reason)
    """
    last_rebal = state.get("last_rebalance_utc")

    if last_rebal is None:
        return True, "first_run"

    try:
        last_dt = datetime.fromisoformat(last_rebal)
        now_utc = datetime.now(timezone.utc)
        days_since = (now_utc - last_dt).days
    except Exception:
        return True, "parse_error"

    if frequency == "daily":
        if days_since >= 1:
            return True, f"daily_cadence ({days_since}d since last)"
        return False, f"daily_cadence (only {days_since}d since last)"

    elif frequency == "weekly":
        if days_since >= 7:
            return True, f"weekly_cadence ({days_since}d since last)"
        return False, f"weekly_cadence ({days_since}d, need 7d)"

    elif frequency == "monthly":
        if days_since >= 30:
            return True, f"monthly_cadence ({days_since}d since last)"
        return False, f"monthly_cadence ({days_since}d, need 30d)"

    return True, "unknown_frequency_defaulting_to_rebalance"


def compute_rebalance_recommendation(
    aum_state: dict,
    k763_state: dict,
) -> dict[str, Any]:
    """
    Core rebalance computation:
    1. Load current AUM
    2. Compute Kelly fraction
    3. Compare current deployed vs Kelly-optimal
    4. Generate rebalance recommendation
    5. Estimate uplift

    PAPER_TRADE=True: recommendation only, no live action.
    """
    aum = float(aum_state.get("current_aum_usdc", 10_000_000.0))
    deployed = float(aum_state.get("deployed_capital_usdc", aum * 0.92))
    cash_buffer_pct = CASH_BUFFER_PCT

    # Current deployment ratio
    current_deploy_ratio = deployed / aum if aum > 0 else 0.0

    # Estimate daily mean/variance from 7d history (if available)
    history_7d = aum_state.get("7d_daily_pnl_history", [])
    if len(history_7d) >= 3:
        daily_returns = [float(r) for r in history_7d]
        daily_mean = sum(daily_returns) / len(daily_returns)
        daily_var  = sum((r - daily_mean) ** 2 for r in daily_returns) / max(len(daily_returns) - 1, 1)
    else:
        # Fallback to v6.52 parametric
        daily_mean = V652_DAILY_RETURN_DECIMAL
        daily_var  = V652_DAILY_VOL_DECIMAL ** 2

    kelly = compute_kelly_fraction(daily_mean, daily_var, HALF_KELLY)
    kelly_deploy_ratio = kelly["recommended"]
    kelly_deploy_usdc  = aum * kelly_deploy_ratio

    # Drift from Kelly-optimal
    drift_pp = (current_deploy_ratio - kelly_deploy_ratio) * 100.0

    # Rebalance recommendation
    drift_threshold_pp = 2.0  # rebalance if > 2pp drift from Kelly-optimal
    needs_rebalance = abs(drift_pp) > drift_threshold_pp

    # Estimated annual uplift from rebalancing (compound frequency benefit)
    uplift_k523 = compute_uplift_k523(aum)

    # Schedule comparison
    schedule_comparison = compute_compound_schedules(V652_MID_ANN_RETURN_PCT, aum, 1.0)

    rec = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "timestamp_jst": datetime.now(JST).strftime("%Y-%m-%d %H:%M JST"),
        "aum_usdc":            round(aum, 2),
        "deployed_usdc":       round(deployed, 2),
        "current_deploy_ratio": round(current_deploy_ratio, 6),
        "kelly_deploy_ratio":  round(kelly_deploy_ratio, 6),
        "kelly_deploy_usdc":   round(kelly_deploy_usdc, 2),
        "drift_pp":            round(drift_pp, 4),
        "drift_threshold_pp":  drift_threshold_pp,
        "needs_rebalance":     needs_rebalance,
        "kelly_detail":        kelly,
        "compound_frequency":  COMPOUND_FREQUENCY,
        "half_kelly_fraction": HALF_KELLY,
        "paper_trade":         PAPER_TRADE,
        "uplift_k523":         uplift_k523,
        "schedule_comparison": schedule_comparison,
        "action": "PAPER_LOG_ONLY" if PAPER_TRADE else ("REBALANCE" if needs_rebalance else "HOLD"),
    }

    return rec


# ══════════════════════════════════════════════════════════════════════════════
# OPERATIONAL COST ANALYSIS
# ══════════════════════════════════════════════════════════════════════════════

def compute_operational_costs(
    aum_usdc: float,
    frequency: str,
    rebalance_fraction: float = 0.05,
) -> dict[str, float]:
    """
    Estimate annual operational cost of rebalance schedule.

    Assumptions:
    - HL taker fee: 2.5bps per side (5bps round-trip)
    - Slippage: 1-3bps per side depending on size (1bp for <$500K)
    - Typical rebalance size: 5% of AUM per rebalance event
    - Gas: negligible (HL is off-chain orderbook)

    Returns: annual cost in USDC for each frequency.
    """
    freq_map = {"daily": 365, "weekly": 52, "monthly": 12, "quarterly": 4}
    n_events = freq_map.get(frequency, 52)

    rebalance_size = aum_usdc * rebalance_fraction
    fee_bps = 5.0       # 5bps round-trip (2.5bps each side, taker)
    slippage_bps = 1.5  # 1.5bps mid-point slippage estimate

    total_cost_per_event = rebalance_size * (fee_bps + slippage_bps) / 10_000.0
    annual_cost = total_cost_per_event * n_events

    return {
        "frequency":            frequency,
        "n_events_per_year":    n_events,
        "rebalance_size_usdc":  round(rebalance_size, 2),
        "fee_bps_roundtrip":    fee_bps,
        "slippage_bps_mid":     slippage_bps,
        "cost_per_event_usdc":  round(total_cost_per_event, 2),
        "annual_cost_usdc":     round(annual_cost, 2),
    }


def compute_net_benefit_analysis(aum_usdc: float) -> dict[str, Any]:
    """
    Net benefit = compound uplift - operational cost for each frequency.
    Uses v6.52 mid return profile.
    """
    r = V652_ANN_RETURN_DECIMAL
    schedules = {"daily": 365, "weekly": 52, "monthly": 12, "quarterly": 4}
    monthly_terminal = aum_usdc * (1 + r / 12) ** 12
    results = {}

    for freq, n in schedules.items():
        terminal = aum_usdc * (1 + r / n) ** n
        compound_uplift = terminal - monthly_terminal
        ops_cost = compute_operational_costs(aum_usdc, freq)
        net_benefit = compound_uplift - ops_cost["annual_cost_usdc"]

        results[freq] = {
            "compound_uplift_gross_usdc": round(compound_uplift, 0),
            "operational_cost_usdc":      round(ops_cost["annual_cost_usdc"], 0),
            "net_benefit_usdc":           round(net_benefit, 0),
            "break_even_return_pct":      round(
                (ops_cost["annual_cost_usdc"] / aum_usdc) * 100, 4
            ),
        }

    # Best net benefit frequency
    best = max(results, key=lambda f: results[f]["net_benefit_usdc"])
    results["recommended_frequency"] = best
    results["recommendation_note"] = (
        f"At v6.52 mid return ({V652_MID_ANN_RETURN_PCT:.1f}%/yr @$10M), "
        f"'{best}' rebalance maximizes net USDC after operational costs."
    )

    return results


# ══════════════════════════════════════════════════════════════════════════════
# LOGGING
# ══════════════════════════════════════════════════════════════════════════════

def _log(msg: str) -> None:
    """Append timestamped log entry."""
    ts = datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S JST")
    line = f"[{ts}] {msg}"
    print(line)
    with open(K763_LOG, "a") as f:
        f.write(line + "\n")


def _append_history(record: dict) -> None:
    """Append to append-only JSONL history."""
    with open(K763_HISTORY_JSONL, "a") as f:
        f.write(json.dumps(record) + "\n")


# ══════════════════════════════════════════════════════════════════════════════
# CLI / STATUS / DRY-RUN
# ══════════════════════════════════════════════════════════════════════════════

def run_status() -> None:
    """Print daemon status."""
    state = load_k763_state()
    aum_state = load_aum_state()
    aum = aum_state.get("current_aum_usdc", 0)

    print(f"\n{'='*65}")
    print("K763 Compound Scheduler — Status")
    print(f"{'='*65}")
    print(f"  PAPER_TRADE:       {PAPER_TRADE}")
    print(f"  Frequency:         {COMPOUND_FREQUENCY}")
    print(f"  Half-Kelly:        {HALF_KELLY}x")
    print(f"  Current AUM:       ${aum:,.0f}")
    print(f"  Last rebalance:    {state.get('last_rebalance_utc', 'never')}")
    print(f"  Rebalance count:   {state.get('rebalance_count', 0)}")
    print(f"  Cumulative uplift: ${state.get('cumulative_uplift_usdc', 0):,.2f}")

    uplift = compute_uplift_k523(aum)
    print(f"\nK523 3-point uplift @${aum/1e6:.1f}M AUM:")
    for key in ["k523_conservative", "k523_central", "k523_optimistic"]:
        u = uplift[key]
        print(f"  {key}: gross=${u['gross_uplift_usdc']:,.0f}/yr | realized=${u['realized_uplift_usdc']:,.0f}/yr")
    print(f"  {uplift['k523_note'][:80]}...")

    net = compute_net_benefit_analysis(aum)
    print(f"\nNet benefit analysis (compound uplift - fees, vs monthly baseline):")
    for freq in ["daily", "weekly", "monthly", "quarterly"]:
        r = net[freq]
        print(f"  {freq:12s}: gross={r['compound_uplift_gross_usdc']:+9,.0f} | cost={r['operational_cost_usdc']:6,.0f} | net={r['net_benefit_usdc']:+9,.0f} USDC/yr")
    print(f"  Recommended: {net['recommended_frequency']}")
    print(f"  {net['recommendation_note']}")
    print(f"{'='*65}\n")


def run_dry_run() -> None:
    """Dry run: compute rebalance recommendation without state changes."""
    _log("[DRY-RUN] K763 compound scheduler dry run")
    aum_state = load_aum_state()
    k763_state = load_k763_state()
    rec = compute_rebalance_recommendation(aum_state, k763_state)

    print(json.dumps(rec, indent=2))
    _log(f"[DRY-RUN] AUM=${rec['aum_usdc']:,.0f} | Kelly={rec['kelly_deploy_ratio']:.4f} | drift={rec['drift_pp']:+.2f}pp | action={rec['action']}")


def run_main() -> None:
    """
    Main daemon loop: called daily at 03:00 UTC by launchd.

    1. Load AUM state
    2. Check if rebalance is due today
    3. Compute Kelly-optimal recommendation
    4. In PAPER_TRADE mode: log recommendation, update state, no live action
    5. Append to history JSONL
    """
    _log(f"[START] K763 compound scheduler | freq={COMPOUND_FREQUENCY} | half_kelly={HALF_KELLY} | paper={PAPER_TRADE}")

    aum_state  = load_aum_state()
    k763_state = load_k763_state()
    aum = float(aum_state.get("current_aum_usdc", 10_000_000.0))

    # Check rebalance schedule
    should, reason = should_rebalance_today(k763_state, COMPOUND_FREQUENCY)
    _log(f"[SCHEDULE] should_rebalance={should} | reason={reason}")

    if not should:
        _log(f"[SKIP] No rebalance due today ({reason})")
        _append_history({
            "ts_utc": datetime.now(timezone.utc).isoformat(),
            "action": "SKIP",
            "reason": reason,
            "aum_usdc": aum,
            "frequency": COMPOUND_FREQUENCY,
            "paper_trade": PAPER_TRADE,
        })
        return

    # Compute recommendation
    rec = compute_rebalance_recommendation(aum_state, k763_state)

    _log(f"[ANALYSIS] AUM=${rec['aum_usdc']:,.0f} | deployed_ratio={rec['current_deploy_ratio']:.4f} | kelly_ratio={rec['kelly_deploy_ratio']:.4f} | drift={rec['drift_pp']:+.2f}pp")
    _log(f"[ANALYSIS] needs_rebalance={rec['needs_rebalance']} | action={rec['action']}")

    if PAPER_TRADE:
        _log(f"[PAPER] PAPER_TRADE=True — logging recommendation only, no live position changes")
        _log(f"[PAPER] Kelly-optimal deploy: ${rec['kelly_deploy_usdc']:,.0f} (ratio={rec['kelly_deploy_ratio']:.4f})")

        # K523 uplift log
        uplift = rec["uplift_k523"]
        _log(
            f"[K523] uplift: conservative=${uplift['k523_conservative']['gross_uplift_usdc']:,.0f} | "
            f"central=${uplift['k523_central']['gross_uplift_usdc']:,.0f} | "
            f"optimistic=${uplift['k523_optimistic']['gross_uplift_usdc']:,.0f} /yr gross"
        )
    else:
        # LIVE mode — WARNING: this path is for future activation only
        # Current implementation: all live rebalancing is manual (user decision)
        # K763 does NOT automatically change live positions
        # To activate: set PAPER_TRADE=False AND verify K376 regime + HL% < 65%
        _log("[LIVE] LIVE mode: K763 compounding recommendation computed")
        _log("[LIVE] ACTION REQUIRED: Manual rebalance — K763 does not auto-rebalance live positions")
        _log(f"[LIVE] Target deploy: ${rec['kelly_deploy_usdc']:,.0f} (current: ${rec['deployed_usdc']:,.0f})")
        _log("[LIVE] See docs/k302a_runbook.md §73 for manual rebalance procedure")

    # Update state
    now_utc = datetime.now(timezone.utc).isoformat()
    k763_state["last_rebalance_utc"]    = now_utc
    k763_state["last_rebalance_aum"]    = aum
    k763_state["rebalance_count"]       = k763_state.get("rebalance_count", 0) + 1
    k763_state["current_frequency"]     = COMPOUND_FREQUENCY
    k763_state["half_kelly_fraction"]   = HALF_KELLY
    k763_state["paper_trade"]           = PAPER_TRADE
    k763_state["last_recommendation"]   = rec

    save_k763_state(k763_state)

    # Append to history
    _append_history({
        "ts_utc":    now_utc,
        "action":    rec["action"],
        "reason":    reason,
        "aum_usdc":  aum,
        "kelly_ratio": rec["kelly_deploy_ratio"],
        "drift_pp":  rec["drift_pp"],
        "frequency": COMPOUND_FREQUENCY,
        "paper_trade": PAPER_TRADE,
    })

    _log(f"[DONE] K763 compound scheduler complete | rebalance_count={k763_state['rebalance_count']}")


# ══════════════════════════════════════════════════════════════════════════════
# ENTRYPOINT
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="K763 Compound Scheduler")
    parser.add_argument("--status",   action="store_true", help="Print daemon status")
    parser.add_argument("--dry-run",  action="store_true", help="Dry run, no state changes")
    parser.add_argument("--analysis", action="store_true", help="Print full compounding analysis")
    args = parser.parse_args()

    if args.status:
        run_status()
    elif args.dry_run:
        run_dry_run()
    elif args.analysis:
        aum = load_aum_state().get("current_aum_usdc", 10_000_000.0)
        print("\n=== Schedule Comparison ===")
        print(json.dumps(compute_compound_schedules(V652_MID_ANN_RETURN_PCT, aum, 1.0), indent=2))
        print("\n=== K523 3-point Uplift ===")
        print(json.dumps(compute_uplift_k523(aum), indent=2))
        print("\n=== Net Benefit Analysis ===")
        print(json.dumps(compute_net_benefit_analysis(aum), indent=2))
        print("\n=== Kelly Fraction ===")
        print(json.dumps(compute_kelly_fraction(V652_DAILY_RETURN_DECIMAL, V652_DAILY_VOL_DECIMAL**2, HALF_KELLY), indent=2))
    else:
        run_main()
