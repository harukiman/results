"""
leverage_manager.py — K430 Leverage Management Module
======================================================
Provides leverage-aware position sizing for all production sleeves.

Design:
  - Reads/writes data/leverage_config.json (single source of truth)
  - Default PAPER_TRADE phase → LEVERAGE=1.0 (additive: no behaviour change at default)
  - Rollout: PAPER_TRADE → LIVE_1.5X → LIVE_3X (user advances manually)
  - Per-exchange caps enforced (HL 3x, Bybit 3x, PAXG 10x, SPX 5x, sUSDe 1x)
  - Circuit breaker integration: check_margin_health() → refuse_trade() if > 80% margin used

K426 finding: 3x leverage → +$2.2M/yr @ $10M AUM
K430 implementation: safe-default PAPER_TRADE=1x, user advances to 1.5x then 3x

Usage:
  from leverage_manager import get_current_leverage, compute_position_size, check_margin_health

K339 Security: REPO_ROOT from __file__, no /Users/ literals.
"""
from __future__ import annotations

import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional

# ── K339: REPO_ROOT from __file__ ─────────────────────────────────────────────
REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR  = REPO_ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)

LEVERAGE_CONFIG_PATH = DATA_DIR / "leverage_config.json"

# ── Rollout phase constants ────────────────────────────────────────────────────
PHASE_PAPER_TRADE = "PAPER_TRADE"
PHASE_LIVE_1_5X   = "LIVE_1.5X"
PHASE_LIVE_3X     = "LIVE_3X"
ROLLOUT_SEQUENCE  = [PHASE_PAPER_TRADE, PHASE_LIVE_1_5X, PHASE_LIVE_3X]
PHASE_LEVERAGE_MAP = {
    PHASE_PAPER_TRADE: 1.0,
    PHASE_LIVE_1_5X:   1.5,
    PHASE_LIVE_3X:     3.0,
}

# ── Exchange-side leverage caps (HL min margin = notional / leverage) ──────────
DEFAULT_EXCHANGE_CAPS: Dict[str, float] = {
    "K280_K208_HL":    3.0,
    "K280_K208_Bybit": 3.0,
    "K280_K208_OKX":   3.0,   # K456: OKX 3rd venue (conservative 3x, OKX supports 100x for BTC)
    "K280_K208_Aevo":  3.0,   # K460: Aevo 4th venue (conservative 3x, Aevo max ~10x, 1h cycle)
    "K280_K208_dYdX":  3.0,   # K460: dYdX v4 5th venue (conservative 3x, Cosmos chain, TODO Cosmos signing)
    "K280_K276b":      3.0,
    "K297_PAXG":       10.0,
    "K297_SPX":        5.0,
    "sUSDe":           1.0,
    "K449_ETH_BTC":   4.0,   # K450: ETH-BTC paired-trade (v6.16 sleeve, HL-only)
    "K476_SOL_BTC":   4.0,   # K478: SOL-BTC paired-trade (v6.21 candidate, HL-only)
    "K484_AVAX_BTC":  4.0,   # K489: AVAX-BTC paired-trade (v6.23 candidate, HL-only, OOS Sh 43.89)
    "K457_basket":    4.0,   # K459: BTC+ETH+SOL multi-asset basket carry (matches K449 4x cap)
}

# ── v6.13d sleeve weights (K348) ──────────────────────────────────────────────
# v6.16 candidate: K280 72% + K297' 20% + sUSDe 5% + K449 3% = 100%
SLEEVE_WEIGHTS: Dict[str, float] = {
    "K280":   0.75,   # K280 main (K198 + K208 + K276b) — v6.13d; v6.16 reduces to 0.72
    "K297":   0.20,   # K302a satellite (PAXG 60% + SPX 40%)
    "sUSDe":  0.05,   # sUSDe OC sleeve
    "K449":   0.03,   # K449 ETH-BTC FR differential paired-trade (K450 scaffold)
    "K457":   0.00,   # K457 BTC+ETH+SOL basket (K459 scaffold, 5% target at v6.20 activation)
    "K476":   0.00,   # K476 SOL-BTC FR differential paired-trade (K478 scaffold, 3% target at v6.21 activation)
    "K484":   0.00,   # K484 AVAX-BTC FR differential paired-trade (K489 scaffold, 3% target at v6.23 activation)
}

# v6.21 candidate weights (proposed in K478 — not yet active)
SLEEVE_WEIGHTS_V621: Dict[str, float] = {
    "K280":  0.69,   # reduced 3pp to fund K476 sleeve
    "K297":  0.20,
    "sUSDe": 0.05,
    "K449":  0.03,   # ETH-BTC delta-neutral, 4x leverage, HL-only (v6.16 activation)
    "K476":  0.03,   # SOL-BTC delta-neutral, 4x leverage, HL-only (v6.21 addition, K478 scaffold)
}

# v6.23 candidate weights (proposed in K489 — not yet active)
# K449 5% + K476 3% + K484 3% = 11% combined paired-trade sleeve, ~$276K/yr @ $10M
SLEEVE_WEIGHTS_V623: Dict[str, float] = {
    "K280":  0.63,   # reduced 6pp vs v6.13d to fund combined paired-trade sleeve
    "K297":  0.20,
    "sUSDe": 0.05,
    "K449":  0.05,   # ETH-BTC delta-neutral, 4x leverage, HL-only (v6.16 base, bumped to 5%)
    "K476":  0.03,   # SOL-BTC delta-neutral, 4x leverage, HL-only (v6.21 addition)
    "K484":  0.03,   # AVAX-BTC delta-neutral, 4x leverage, HL-only (v6.23 addition, K489 scaffold)
    "K457":  0.01,   # BTC+ETH+SOL basket (placeholder, reduced from v6.20 5% pending paper gate)
}

# v6.16 candidate weights (proposed in K450 — not yet active)
SLEEVE_WEIGHTS_V616: Dict[str, float] = {
    "K280":  0.72,   # reduced 3pp to fund K449 sleeve
    "K297":  0.20,
    "sUSDe": 0.05,
    "K449":  0.03,   # ETH-BTC delta-neutral, 4x leverage, HL-only
}


# ─────────────────────────────────────────────────────────────────────────────
# Config I/O
# ─────────────────────────────────────────────────────────────────────────────

def _load_config() -> Dict:
    """Load leverage_config.json; return defaults if missing."""
    if LEVERAGE_CONFIG_PATH.exists():
        try:
            with open(LEVERAGE_CONFIG_PATH) as f:
                return json.load(f)
        except Exception as e:
            print(f"  [leverage_manager] Config load error: {e} — using defaults")
    # Return safe defaults (PAPER_TRADE, 1x)
    return {
        "rollout_phase":    PHASE_PAPER_TRADE,
        "current_leverage": 1.0,
        "target_leverage":  3.0,
        "exchange_caps":    DEFAULT_EXCHANGE_CAPS.copy(),
        "deployment_pct":   0.80,
        "cash_buffer_pct":  0.20,
        "circuit_breaker": {
            "max_margin_pct":     0.80,
            "warning_margin_pct": 0.70,
            "deactivated":        False,
        },
        "rollout_history": [],
    }


def _save_config(cfg: Dict) -> None:
    """Persist leverage config atomically."""
    tmp = LEVERAGE_CONFIG_PATH.with_suffix(".tmp")
    with open(tmp, "w") as f:
        json.dump(cfg, f, indent=2)
    tmp.replace(LEVERAGE_CONFIG_PATH)


# ─────────────────────────────────────────────────────────────────────────────
# Core API
# ─────────────────────────────────────────────────────────────────────────────

def get_current_leverage() -> float:
    """
    Return current operational leverage from config.

    At PAPER_TRADE (default): returns 1.0 — no change to position sizing.
    At LIVE_1.5X: returns 1.5.
    At LIVE_3X: returns 3.0.
    If circuit_breaker.deactivated is True: returns 1.0 regardless (emergency).
    """
    cfg = _load_config()
    # Circuit breaker override: emergency reduce to 1x
    cb = cfg.get("circuit_breaker", {})
    if cb.get("deactivated", False):
        return 1.0
    lev = float(cfg.get("current_leverage", 1.0))
    return max(1.0, lev)


def get_rollout_phase() -> str:
    """Return current rollout phase string."""
    return _load_config().get("rollout_phase", PHASE_PAPER_TRADE)


def compute_position_size(
    sleeve_name: str,
    current_aum: float,
    deployment_pct: Optional[float] = None,
) -> float:
    """
    Compute leveraged notional position size for a sleeve.

    Formula:
        notional = current_aum × deployment_pct × sleeve_weight × leverage

    Args:
        sleeve_name:    One of 'K280', 'K297', 'sUSDe'
        current_aum:    Total portfolio AUM in USD
        deployment_pct: Fraction of AUM deployed (reads from config if None)

    Returns:
        Notional position size in USD.

    Example at 3x (K280, $10M AUM, 80% deployment):
        notional = $10M × 0.80 × 0.75 × 3.0 = $18M

    K448: Apply per-sleeve exchange caps (e.g. sUSDe capped at 1x).
    """
    cfg = _load_config()
    raw_leverage = get_current_leverage()

    # K448/K450: cap leverage by exchange limit per sleeve
    cap_key_map = {
        "K280":   "K280_K208_HL",
        "K297":   "K297_PAXG",
        "sUSDe":  "sUSDe",
        "K449":   "K449_ETH_BTC",   # K450: 4x cap for ETH-BTC paired-trade sleeve
        "K457":   "K457_basket",    # K459: 4x cap for BTC+ETH+SOL basket
        "K476":   "K476_SOL_BTC",   # K478: 4x cap for SOL-BTC paired-trade sleeve
        "K484":   "K484_AVAX_BTC",  # K489: 4x cap for AVAX-BTC paired-trade sleeve
    }
    cap_key = cap_key_map.get(sleeve_name, sleeve_name)
    exchange_caps = cfg.get("exchange_caps", DEFAULT_EXCHANGE_CAPS)
    sleeve_cap = float(exchange_caps.get(cap_key, raw_leverage))
    effective_leverage = min(raw_leverage, sleeve_cap)

    sleeve_weight = SLEEVE_WEIGHTS.get(sleeve_name, 0.0)
    if deployment_pct is None:
        deployment_pct = float(cfg.get("deployment_pct", 0.80))

    return current_aum * deployment_pct * sleeve_weight * effective_leverage


def compute_margin_required(
    sleeve_name: str,
    leverage: Optional[float] = None,
    current_aum: float = 0.0,
    deployment_pct: Optional[float] = None,
) -> float:
    """
    Compute margin required for a sleeve at given leverage.

    HL exchange margin model: margin = notional / exchange_leverage_cap
    (Exchange provides leverage; margin = collateral posted.)

    For sUSDe (spot, no leverage): margin = notional (leverage = 1x always).

    Args:
        sleeve_name:    One of 'K280', 'K297', 'sUSDe'
        leverage:       Operational leverage to use (reads from config if None)
        current_aum:    AUM for absolute margin computation (0 = ratio only)
        deployment_pct: Deployment fraction (reads from config if None)

    Returns:
        Margin required in USD (0.0 if current_aum=0, i.e. fractional mode).
    """
    cfg = _load_config()
    if leverage is None:
        leverage = get_current_leverage()
    if deployment_pct is None:
        deployment_pct = float(cfg.get("deployment_pct", 0.80))

    # Exchange cap lookup (sleeve → exchange cap key)
    cap_key_map = {
        "K280":   "K280_K208_HL",   # use HL cap as conservative reference
        "K297":   "K297_PAXG",      # PAXG dominates margin (60% weight)
        "sUSDe":  "sUSDe",
        "K449":   "K449_ETH_BTC",   # K450: 4x cap ETH-BTC paired-trade
        "K457":   "K457_basket",    # K459: 4x cap BTC+ETH+SOL basket
        "K476":   "K476_SOL_BTC",   # K478: 4x cap SOL-BTC paired-trade
        "K484":   "K484_AVAX_BTC",  # K489: 4x cap AVAX-BTC paired-trade
    }
    cap_key = cap_key_map.get(sleeve_name, sleeve_name)
    exchange_caps = cfg.get("exchange_caps", DEFAULT_EXCHANGE_CAPS)
    exchange_cap  = float(exchange_caps.get(cap_key, 1.0))

    # Cap operational leverage at exchange cap
    eff_leverage = min(leverage, exchange_cap)

    if current_aum <= 0:
        # Return margin fraction of notional (useful for ratio checks)
        return 1.0 / eff_leverage if eff_leverage > 0 else 1.0

    notional = compute_position_size(sleeve_name, current_aum, deployment_pct)
    # At 1x: no exchange leverage benefit → margin = notional
    margin = notional / eff_leverage
    return margin


def check_margin_health(
    current_aum: float,
    deployment_pct: Optional[float] = None,
    verbose: bool = False,
) -> Dict:
    """
    Compute portfolio-wide margin health snapshot.

    Returns:
        {
            "margin_used_pct":       float,   # 0–1 fraction of AUM used as margin
            "cash_buffer_remaining": float,   # USD remaining as cash buffer
            "warning":               bool,    # True if > warning_margin_pct (70%)
            "circuit_breaker_fire":  bool,    # True if > max_margin_pct (80%)
            "sleeves":               dict,    # per-sleeve margin breakdown
            "leverage":              float,
            "phase":                 str,
        }

    Circuit breaker logic:
        margin_used_pct > 80% → fire (emergency reduce to 1x)
        margin_used_pct > 70% → warning (dashboard alert)
    """
    cfg            = _load_config()
    leverage       = get_current_leverage()
    phase          = get_rollout_phase()
    cb             = cfg.get("circuit_breaker", {})
    max_pct        = float(cb.get("max_margin_pct", 0.80))
    warn_pct       = float(cb.get("warning_margin_pct", 0.70))
    if deployment_pct is None:
        deployment_pct = float(cfg.get("deployment_pct", 0.80))

    sleeves_margin: Dict[str, float] = {}
    total_margin   = 0.0

    for sleeve in ["K280", "K297", "sUSDe", "K449", "K457", "K476", "K484"]:
        m = compute_margin_required(sleeve, leverage, current_aum, deployment_pct)
        sleeves_margin[sleeve] = round(m, 2)
        total_margin += m

    margin_used_pct  = total_margin / current_aum if current_aum > 0 else 0.0
    cash_buffer      = current_aum - total_margin

    # In PAPER_TRADE at 1x: margin = notional (no exchange leverage benefit yet).
    # At 1x with 80% deployment, computed margin_used_pct = 80% which is benign.
    # Suppress CB fire/warning in PAPER_TRADE — only meaningful when leverage > 1x.
    _phase = cfg.get("rollout_phase", PHASE_PAPER_TRADE)
    if _phase == PHASE_PAPER_TRADE or leverage <= 1.0:
        cb_fire = False
        warning = False
    else:
        cb_fire = margin_used_pct > max_pct
        warning = margin_used_pct > warn_pct

    if verbose:
        print(f"  [margin_health] phase={phase}, leverage={leverage}x, "
              f"margin_used={margin_used_pct*100:.1f}%, cash_buffer=${cash_buffer:,.0f}")
        for s, m in sleeves_margin.items():
            print(f"    {s}: ${m:,.0f}")
        if cb_fire:
            print("  [margin_health] *** CIRCUIT BREAKER FIRE ***")
        elif warning:
            print("  [margin_health] WARNING: margin usage approaching limit")

    return {
        "margin_used_pct":       round(margin_used_pct, 4),
        "cash_buffer_remaining": round(cash_buffer, 2),
        "total_margin_usd":      round(total_margin, 2),
        "warning":               warning,
        "circuit_breaker_fire":  cb_fire,
        "sleeves":               sleeves_margin,
        "leverage":              leverage,
        "phase":                 phase,
        "aum":                   current_aum,
        "max_margin_pct":        max_pct,
        "warn_margin_pct":       warn_pct,
        "checked_at_utc":        datetime.now(timezone.utc).isoformat(),
    }


def refuse_trade(sleeve_name: str, margin_check: Dict) -> None:
    """
    Log and raise when margin health check blocks a trade.
    Called by production scripts when compute_margin_required > MAX_ALLOWED.
    """
    msg = (
        f"[leverage_manager] TRADE REFUSED — {sleeve_name}: "
        f"margin_used_pct={margin_check.get('margin_used_pct',0)*100:.1f}% "
        f"exceeds max {margin_check.get('max_margin_pct',0.80)*100:.0f}%. "
        f"phase={margin_check.get('phase','?')}, leverage={margin_check.get('leverage',1)}x. "
        f"Emergency: reduce leverage or increase cash buffer."
    )
    print(msg)
    # Write alert to data/leverage_alert.json for dashboard pickup
    alert_path = DATA_DIR / "leverage_alert.json"
    with open(alert_path, "w") as f:
        json.dump({"alert": msg, "ts_utc": datetime.now(timezone.utc).isoformat(),
                   "margin_check": margin_check}, f, indent=2)
    raise RuntimeError(msg)


def apply_rollout_step() -> Dict:
    """
    Advance rollout phase one step: PAPER_TRADE → LIVE_1.5X → LIVE_3X.
    Idempotent at LIVE_3X (already at target).

    Returns updated config dict.
    This is a USER-TRIGGERED action; NOT called automatically.
    """
    cfg   = _load_config()
    phase = cfg.get("rollout_phase", PHASE_PAPER_TRADE)
    idx   = ROLLOUT_SEQUENCE.index(phase) if phase in ROLLOUT_SEQUENCE else 0

    if idx >= len(ROLLOUT_SEQUENCE) - 1:
        print(f"  [leverage_manager] Already at max rollout phase: {phase}")
        return cfg

    next_phase = ROLLOUT_SEQUENCE[idx + 1]
    next_lev   = PHASE_LEVERAGE_MAP[next_phase]

    # Record history entry
    history_entry = {
        "ts_utc":      datetime.now(timezone.utc).isoformat(),
        "from_phase":  phase,
        "to_phase":    next_phase,
        "from_lev":    cfg.get("current_leverage", 1.0),
        "to_lev":      next_lev,
    }
    cfg.setdefault("rollout_history", []).append(history_entry)

    cfg["rollout_phase"]    = next_phase
    cfg["current_leverage"] = next_lev
    _save_config(cfg)

    print(f"  [leverage_manager] Rollout advanced: {phase} → {next_phase} "
          f"(leverage {history_entry['from_lev']}x → {next_lev}x)")
    return cfg


def emergency_reduce_leverage() -> None:
    """
    Emergency leverage reduction: set circuit_breaker.deactivated = True.
    get_current_leverage() returns 1.0 when deactivated=True.
    All scripts automatically use 1x leverage after this call.
    """
    cfg = _load_config()
    cfg.setdefault("circuit_breaker", {})["deactivated"] = True
    cfg["rollout_phase"]    = PHASE_PAPER_TRADE  # record phase regression
    cfg["current_leverage"] = 1.0
    cfg.setdefault("rollout_history", []).append({
        "ts_utc":      datetime.now(timezone.utc).isoformat(),
        "event":       "EMERGENCY_REDUCE",
        "from_phase":  get_rollout_phase(),
        "to_phase":    PHASE_PAPER_TRADE,
        "from_lev":    cfg.get("current_leverage", 1.0),
        "to_lev":      1.0,
    })
    _save_config(cfg)
    print("  [leverage_manager] EMERGENCY LEVERAGE REDUCE: circuit_breaker.deactivated=True, leverage=1x")


def restore_leverage_after_emergency(target_phase: str = PHASE_PAPER_TRADE) -> None:
    """
    Restore leverage after emergency. Sets deactivated=False and resets to target_phase.
    User calls this manually after resolving the margin crisis.
    """
    if target_phase not in ROLLOUT_SEQUENCE:
        raise ValueError(f"Unknown phase: {target_phase}. Must be one of {ROLLOUT_SEQUENCE}")
    cfg = _load_config()
    cfg.setdefault("circuit_breaker", {})["deactivated"] = False
    cfg["rollout_phase"]    = target_phase
    cfg["current_leverage"] = PHASE_LEVERAGE_MAP[target_phase]
    cfg.setdefault("rollout_history", []).append({
        "ts_utc":   datetime.now(timezone.utc).isoformat(),
        "event":    "EMERGENCY_RESTORE",
        "to_phase": target_phase,
        "to_lev":   PHASE_LEVERAGE_MAP[target_phase],
    })
    _save_config(cfg)
    print(f"  [leverage_manager] Leverage restored: phase={target_phase}, "
          f"leverage={PHASE_LEVERAGE_MAP[target_phase]}x, deactivated=False")


# ─────────────────────────────────────────────────────────────────────────────
# CLI (quick sanity check)
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    args = sys.argv[1:]

    if "--advance" in args:
        updated = apply_rollout_step()
        print(f"Phase: {updated['rollout_phase']}, Leverage: {updated['current_leverage']}x")
        sys.exit(0)

    if "--emergency-reduce" in args:
        emergency_reduce_leverage()
        sys.exit(0)

    if "--restore" in args:
        target = args[args.index("--restore") + 1] if len(args) > args.index("--restore") + 1 else PHASE_PAPER_TRADE
        restore_leverage_after_emergency(target)
        sys.exit(0)

    # Default: print current status
    cfg = _load_config()
    lev = get_current_leverage()
    phase = get_rollout_phase()
    print(f"\n=== K430 Leverage Manager Status ===")
    print(f"  Rollout phase:    {phase}")
    print(f"  Current leverage: {lev}x")
    print(f"  Target leverage:  {cfg.get('target_leverage', 3.0)}x")
    print(f"  Circuit breaker:  {'DEACTIVATED (emergency 1x)' if cfg.get('circuit_breaker',{}).get('deactivated') else 'OK'}")
    print(f"  Deployment pct:   {cfg.get('deployment_pct', 0.80)*100:.0f}%")

    # Show position sizes at $10M for reference
    aum = 10_000_000
    print(f"\n  Position sizes @ ${aum/1e6:.0f}M AUM ({lev}x leverage):")
    for sleeve in ["K280", "K297", "sUSDe", "K449", "K457"]:
        notional = compute_position_size(sleeve, aum)
        margin   = compute_margin_required(sleeve, lev, aum)
        print(f"    {sleeve:8s}: notional=${notional:>12,.0f}  margin=${margin:>12,.0f}")

    health = check_margin_health(aum, verbose=True)
    print(f"\n  Margin used: {health['margin_used_pct']*100:.1f}%  "
          f"Cash buffer: ${health['cash_buffer_remaining']:,.0f}")
    print(f"  CB fire: {health['circuit_breaker_fire']}  Warning: {health['warning']}")
