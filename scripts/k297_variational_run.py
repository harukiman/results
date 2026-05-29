#!/usr/bin/env python3
"""K297' Variational Equivalent Paper-Trade Scaffold — K443 Venue Prep.

Strategy: K297''-Variational  (XAU 50% + XAG 30% + CL 20%, inv-vol weighted)
Exchange: Variational (https://variational.io)  — trading API PENDING Q3-Q4 2026
Mode:     PAPER-TRADE ONLY — no real orders until trading API available

K297' HL equivalent:      PAXG 60% + SPX 40%, 1h/8h funding (K302a satellite)
K297''-Variational equiv: XAU  50% + XAG 30% + CL 20%, 4h funding cycle
New assets vs HL:         XAG (Silver), CL (WTI Crude) — not on HyperLiquid

Architecture:
  Multi-venue K297 sleeve (v6.17 candidate):
    HL K297'       60% of sleeve  (12% of AUM)  → K302a satellite
    Variational K297''  40% of sleeve  (8% of AUM)  → this script (paper-trade)
  Rebalance: monthly (K427 pattern)
  Trigger: HL K297' sleeve exposure > 65% → shift 5pp to Variational

v6.13d overall architecture for reference:
    K280 main sleeve:        75%
    K297' satellite (HL):    20%   → K302a satellite
    sUSDe OC sleeve:          5%
    -----------------------------------
    K297 total (both venues): 20% of AUM now; target 20% split 12%/8% multi-venue
    after Variational API activation

Capacity rationale (K431/K443):
  $25M AUM: HL K297' alone hits capacity (K297 OI impact at HL @ $5M position)
  Variational ($3.85B TVL): K297'' absorbs overflow — unlocks $6-7M/yr @ $50M

SPX-style filter (K297' pattern adaptation):
  Variational has no equity index instruments.
  Proxy: use gold (XAU) FR trend as filter for silver/crude entries.
  XAU_TREND_FILTER: enter XAG/CL only when XAU 3d FR trend > 0 AND XAU FR > threshold.
  Rationale: XAU acts as "risk-on" signal for commodity basket carry.

4h funding cycle:
  Variational settles every 4 hours (vs HL 1h/8h).
  Daily PnL = 6 settlements × (position_value × fr_rate_4h / 365*24/4) - cost

Emergency exit stub (K357 integration pattern):
  close_variational_positions() is scaffolded below.
  When trading API available: fill in REST calls per K380 Bybit pattern.

EMERGENCY flag check:
  If EMERGENCY_EXIT_TRIGGERED.flag exists → exit 0 immediately.
  Log the skip.

BEAR_1 flag check (K386):
  If BEAR_1_FALLBACK_ACTIVE.flag exists:
    XAU/PAXG-linked positions → HOLD (safe-haven, carry may increase during HL stress)
    CL positions → REDUCE 50% (commodity carry less certain in CFTC stress scenario)
    Log the adjustment.

Dashboard: data/k443_variational_dashboard.json
Log:       logs/k443_variational_paper.log
Error:     logs/k443_variational_paper.err

K363 cache: cache/variational_fr_snapshots/ (accumulated by K363 daemon)
  When daemon has accumulated 90d data → enable rolling Sharpe computation.
  Currently: 0-1 snapshots (daemon not loaded by user per K443 task brief).
  Fallback: use K365 baseline snapshot if cache empty.

Security (K339): REPO_ROOT = Path(__file__).resolve().parent.parent (no /Users/ literals)

Usage:
    python3 scripts/k297_variational_run.py
    python3 scripts/k297_variational_run.py --dry-run
    python3 scripts/k297_variational_run.py --date 2026-05-25
    python3 scripts/k297_variational_run.py --status    # dashboard summary only

Activation:
    1. Variational trading API released (Q3-Q4 2026)
    2. Paper-trade for 60 days (K444 gate)
    3. K444 production patch: fill in order submission, live PnL tracking
    See docs/k302a_runbook.md §27 for full activation playbook.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# ── K339 Security: REPO_ROOT from __file__, no /Users/ literals ──────────────
REPO_ROOT  = Path(__file__).resolve().parent.parent
DATA_DIR   = REPO_ROOT / "data"
LOGS_DIR   = REPO_ROOT / "logs"
CACHE_DIR  = REPO_ROOT / "cache" / "variational_fr_snapshots"
SCRIPTS_DIR = REPO_ROOT / "scripts"

DATA_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)

# ── Flag files (priority order, K339/K386) ────────────────────────────────────
EMERGENCY_FLAG = REPO_ROOT / "EMERGENCY_EXIT_TRIGGERED.flag"
BEAR1_FLAG     = REPO_ROOT / "BEAR_1_FALLBACK_ACTIVE.flag"

# ── Dashboard / log paths ─────────────────────────────────────────────────────
DASHBOARD_JSON = DATA_DIR  / "k443_variational_dashboard.json"
VAR_FR_DASH    = DATA_DIR  / "variational_fr_dashboard.json"   # K363 cache
LOG_FILE       = LOGS_DIR  / "k443_variational_paper.log"
ERR_FILE       = LOGS_DIR  / "k443_variational_paper.err"
TRADES_LOG     = DATA_DIR  / "k443_variational_paper_trades.jsonl"

JST = timezone(timedelta(hours=9))

# ── Variational API (public read, K363/K365 confirmed) ───────────────────────
VAR_API_URL  = "https://api.variational.io/metadata/stats"
API_TIMEOUT  = 15   # seconds

# ── Trading API status (K365/K443 tracking) ───────────────────────────────────
# When Variational releases trading API (Q3-Q4 2026 target), set:
#   VARIATIONAL_TRADING_API_AVAILABLE = True
#   Fill in close_variational_positions() and order submission stubs below
VARIATIONAL_TRADING_API_AVAILABLE = False   # K443: NOT YET AVAILABLE

# ── K297'' Strategy Configuration ─────────────────────────────────────────────
# Base weights (before inv-vol adjustment)
BASE_WEIGHTS: Dict[str, float] = {
    "XAU": 0.50,    # Gold (Gold perp, K297 equivalent component)
    "XAG": 0.30,    # Silver (NEW — not on HyperLiquid)
    "CL":  0.20,    # WTI Crude (NEW — not on HyperLiquid)
}

# Inv-vol reweighting: adjust weights by 1/vol(FR), per K297 pattern.
# Min weight floor to prevent extreme concentration.
INV_VOL_MIN_WEIGHT    = 0.10    # 10% floor per asset
INV_VOL_MAX_WEIGHT    = 0.65    # 65% ceiling per asset

# XAU trend filter (SPX-style proxy for commodity basket):
#   Enter XAG and CL only when XAU 3d FR > 0 AND XAU FR > XAU_FR_THRESHOLD
#   Enter XAU always-on (analogous to PAXG always-on in K302a)
XAU_ALWAYS_ON           = True      # analogous to PAXG always-on in K297'
XAU_TREND_FILTER_ENABLE = True      # XAG/CL entry filter (SPX-proxy via XAU)
XAU_FR_THRESHOLD        = 0.0       # XAU FR must be > 0 for XAG/CL entries

# 4h settlement cadence (Variational)
SETTLEMENTS_PER_DAY     = 6         # 24h / 4h = 6 settlements/day

# Cost estimate (paper-trade conservative)
COST_BPS_PER_SIDE       = 7.0       # 7 bps/side (conservative; Variational maker TBD)
COST_BPS_ROUNDTRIP      = 2 * COST_BPS_PER_SIDE   # hold multiple days → amortized

# AUM and sleeve sizing
DEFAULT_AUM_USD         = 10_000_000.0   # $10M reference (overridden by K429 dashboard)
SLEEVE_PCT_OF_AUM       = 0.08           # K297'' = 8% of AUM (40% of 20% K297 sleeve)
SLEEVE_PCT_HL_K297      = 0.12           # HL K297' = 12% of AUM (60% of 20% sleeve)

# ── K365 Baseline (fallback when K363 cache empty) ────────────────────────────
K365_BASELINE: Dict[str, Dict] = {
    "XAUT":   {"fr_ann_pct": -71.1,  "oi_usd": 26_600_000},
    "XAU":    {"fr_ann_pct":  560.0, "oi_usd": 21_900_000},
    "PAXG":   {"fr_ann_pct":  239.8, "oi_usd": 15_000_000},
    "CL":     {"fr_ann_pct": -247.0, "oi_usd":  4_900_000},
    "XAG":    {"fr_ann_pct":    0.0, "oi_usd":  4_100_000},
    "COPPER": {"fr_ann_pct":    0.0, "oi_usd":  1_600_000},
}

# Multi-venue allocator trigger (K443 Phase 5)
HL_SLEEVE_TRIGGER_REBALANCE_PCT = 0.65  # if HL K297' > 65% of sleeve → shift to Variational


# ── Logging helpers ───────────────────────────────────────────────────────────

def _ts() -> str:
    return datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S JST")


def _log(msg: str) -> None:
    line = f"[{_ts()}] {msg}"
    print(line)
    try:
        with open(LOG_FILE, "a") as f:
            f.write(line + "\n")
    except Exception:
        pass


def _err(msg: str) -> None:
    line = f"[{_ts()}] ERROR: {msg}"
    print(line, file=sys.stderr)
    try:
        LOGS_DIR.mkdir(exist_ok=True)
        with open(ERR_FILE, "a") as f:
            f.write(line + "\n")
    except Exception:
        pass


# ── API fetch ─────────────────────────────────────────────────────────────────

def fetch_variational_fr() -> Optional[Dict[str, Dict]]:
    """Fetch current FR data from Variational public API.

    Returns dict: symbol → {fr_ann_pct, oi_usd, mark_price, spread}.
    Falls back to K363 cached dashboard, then K365 baseline.
    """
    # Try K363 cached dashboard first (avoid redundant API call)
    try:
        if VAR_FR_DASH.exists():
            with open(VAR_FR_DASH) as f:
                dash = json.load(f)
            # Check freshness (accept if < 8 hours old)
            updated_ts_ms = dash.get("updated_ts_ms", 0)
            age_h = (datetime.now(timezone.utc).timestamp() * 1000 - updated_ts_ms) / 3_600_000
            if age_h < 8.0:
                result: Dict[str, Dict] = {}
                for inst in dash.get("rwa_instruments", []):
                    sym = inst.get("symbol", "")
                    if sym in BASE_WEIGHTS:
                        result[sym] = {
                            "fr_ann_pct": inst.get("fr_ann_pct"),
                            "oi_usd":     inst.get("oi_usd", 0),
                            "mark_price": inst.get("mark_price"),
                            "spread":     inst.get("spread"),
                            "source":     "k363_cache",
                        }
                if result:
                    _log(f"  [fetch] K363 cache hit (age {age_h:.1f}h): {list(result.keys())}")
                    return result
    except Exception as e:
        _err(f"K363 cache read failed: {e}")

    # Try live API
    try:
        req = urllib.request.Request(
            VAR_API_URL,
            headers={"Accept": "application/json", "User-Agent": "ct-k443-variational/1.0"},
        )
        with urllib.request.urlopen(req, timeout=API_TIMEOUT) as resp:
            raw = json.loads(resp.read())
        instruments = raw if isinstance(raw, list) else raw.get("instruments", [])
        result = {}
        for inst in instruments:
            sym = (inst.get("symbol") or inst.get("coin") or "").upper()
            if sym in BASE_WEIGHTS:
                result[sym] = {
                    "fr_ann_pct": inst.get("fundingRate") or inst.get("fr_ann_pct"),
                    "oi_usd":     float(inst.get("openInterest") or inst.get("oi_usd") or 0),
                    "mark_price": inst.get("markPrice") or inst.get("mark_price"),
                    "spread":     inst.get("spread"),
                    "source":     "live_api",
                }
        if result:
            _log(f"  [fetch] Live API: {list(result.keys())}")
            return result
    except Exception as e:
        _err(f"Live API fetch failed: {e}")

    # Fallback: K365 baseline
    _log("  [fetch] Using K365 baseline (no cache or API)")
    return {
        sym: {
            "fr_ann_pct": K365_BASELINE[sym]["fr_ann_pct"],
            "oi_usd":     K365_BASELINE[sym]["oi_usd"],
            "mark_price": None,
            "spread":     None,
            "source":     "k365_baseline",
        }
        for sym in BASE_WEIGHTS
        if sym in K365_BASELINE
    }


# ── Inv-vol weight computation ────────────────────────────────────────────────

def compute_invvol_weights(
    fr_data: Dict[str, Dict],
) -> Dict[str, float]:
    """Compute inverse-volatility weights per K297 pattern.

    Volatility proxy: |fr_ann_pct|. Higher FR magnitude = higher volatility signal
    for commodity carry = lower weight. Floor/ceiling applied.
    Falls back to BASE_WEIGHTS for assets with null/zero FR.
    """
    vols: Dict[str, float] = {}
    for sym in BASE_WEIGHTS:
        fr = fr_data.get(sym, {}).get("fr_ann_pct")
        if fr is None or fr == 0.0:
            vols[sym] = 1.0   # default volatility = 1 (neutral)
        else:
            vols[sym] = max(abs(fr), 1.0)   # 1.0 floor to avoid division issues

    inv_vols = {sym: 1.0 / vols[sym] for sym in BASE_WEIGHTS}
    total_inv = sum(inv_vols.values())

    if total_inv == 0:
        return {sym: BASE_WEIGHTS[sym] for sym in BASE_WEIGHTS}

    # Blend: 50% base weight + 50% inv-vol weight (per K297 conservative blend)
    raw_weights = {
        sym: 0.5 * BASE_WEIGHTS[sym] + 0.5 * (inv_vols[sym] / total_inv)
        for sym in BASE_WEIGHTS
    }

    # Apply floor / ceiling
    clamped = {sym: max(INV_VOL_MIN_WEIGHT, min(INV_VOL_MAX_WEIGHT, w))
               for sym, w in raw_weights.items()}

    # Renormalize
    total = sum(clamped.values())
    return {sym: round(clamped[sym] / total, 4) for sym in BASE_WEIGHTS}


# ── XAU trend filter (SPX-proxy) ──────────────────────────────────────────────

def xau_trend_filter_passes(fr_data: Dict[str, Dict]) -> bool:
    """Check if XAU FR condition allows XAG/CL entries.

    Simple check: XAU fr_ann_pct > XAU_FR_THRESHOLD (default: > 0).
    When K363 daemon has 90d+ data, upgrade to 3d rolling average.
    """
    if not XAU_TREND_FILTER_ENABLE:
        return True
    xau_fr = fr_data.get("XAU", {}).get("fr_ann_pct")
    if xau_fr is None:
        # null FR = no signal → allow entry (conservative: treat as neutral)
        return True
    return float(xau_fr) > XAU_FR_THRESHOLD


# ── BEAR_1 position adjustment (K386) ─────────────────────────────────────────

def apply_bear1_adjustments(
    weights: Dict[str, float],
    active_signal: Dict[str, bool],
) -> Tuple[Dict[str, float], Dict[str, bool]]:
    """Reduce CL 50%, hold XAU/XAG under BEAR_1 (CFTC enforcement scenario).

    BEAR_1 rationale: in CFTC enforcement vs HyperLiquid scenario,
    gold/silver carry likely stable or increases (safe-haven demand).
    CL (crude oil) carry less predictable → reduce exposure.
    """
    adj_weights = dict(weights)
    adj_signals = dict(active_signal)
    adj_weights["CL"] = adj_weights.get("CL", 0.0) * 0.5   # 50% reduction
    # Renormalize
    total = sum(adj_weights.values())
    if total > 0:
        adj_weights = {sym: round(w / total, 4) for sym, w in adj_weights.items()}
    _log("  [BEAR_1] CL weight halved; XAU/XAG held. Renormalized weights applied.")
    return adj_weights, adj_signals


# ── PnL calculation (paper-trade) ─────────────────────────────────────────────

def compute_daily_pnl(
    fr_data: Dict[str, Dict],
    weights: Dict[str, float],
    active_signal: Dict[str, bool],
    sleeve_usd: float,
) -> Dict:
    """Compute paper-trade PnL for K297'' Variational sleeve.

    Model:
        daily_fr_return[sym] = (fr_ann_pct[sym] / 100.0) / 365.0
        daily_pnl[sym] = sleeve_usd * weight[sym] * signal[sym] * daily_fr_return[sym]
        cost[sym] = sleeve_usd * weight[sym] * signal[sym] * (COST_BPS_ROUNDTRIP / 10000 / 365)
        net_pnl = sum(daily_pnl[sym] - cost[sym])

    Notes:
    - Positive fr_ann_pct = long perp earns from short counterparties.
    - 4h settlement = 6 per day (already in annual rate → divide by 365 for daily).
    - Cost amortized daily (no reentry assumed for carry strategy).
    """
    records: List[Dict] = []
    total_gross_pnl = 0.0
    total_cost = 0.0
    total_net_pnl = 0.0

    for sym, weight in weights.items():
        if not active_signal.get(sym, False):
            records.append({
                "symbol": sym, "weight": weight, "signal": False,
                "fr_ann_pct": None, "gross_pnl": 0.0, "cost": 0.0, "net_pnl": 0.0,
            })
            continue

        fr_ann = fr_data.get(sym, {}).get("fr_ann_pct")
        if fr_ann is None:
            fr_ann = 0.0   # no signal = no carry
        fr_ann = float(fr_ann)

        position_usd     = sleeve_usd * weight
        gross_pnl        = position_usd * (fr_ann / 100.0) / 365.0
        cost_usd         = position_usd * (COST_BPS_ROUNDTRIP / 10_000.0) / 365.0
        net_pnl          = gross_pnl - cost_usd

        total_gross_pnl += gross_pnl
        total_cost      += cost_usd
        total_net_pnl   += net_pnl

        records.append({
            "symbol":      sym,
            "weight":      round(weight, 4),
            "signal":      True,
            "fr_ann_pct":  round(fr_ann, 4),
            "position_usd": round(position_usd, 2),
            "gross_pnl":   round(gross_pnl, 4),
            "cost_usd":    round(cost_usd, 4),
            "net_pnl":     round(net_pnl, 4),
        })

    return {
        "components":       records,
        "gross_pnl_usd":    round(total_gross_pnl, 4),
        "total_cost_usd":   round(total_cost, 4),
        "net_pnl_usd":      round(total_net_pnl, 4),
        "net_pnl_bps":      round(total_net_pnl / sleeve_usd * 10_000, 4) if sleeve_usd > 0 else 0.0,
    }


# ── K357 Emergency Exit Stub (K443 Phase 6) ───────────────────────────────────

def close_variational_positions(dry_run: bool = False) -> Dict:
    """Emergency close all Variational positions.

    SCAFFOLD ONLY — trading API not yet available (Q3-Q4 2026).

    When Variational trading API is released (K444 production patch):
        1. Authenticate with API key (similar to K380 Bybit close-all pattern)
        2. GET /positions → list all open perp positions
        3. For each position: POST /order {side: opposite, size: full, type: market}
        4. Confirm all positions closed (retry up to 3x)
        5. Return {"status": "CLOSED", "closed_positions": [...], "total_pnl": ...}

    Current behaviour (scaffold): log the request, return STUB status.
    """
    _log("  [K357] close_variational_positions() called")
    if not VARIATIONAL_TRADING_API_AVAILABLE:
        _log("  [K357] STUB: Variational trading API not yet available. "
             "Positions are paper-trade only — no real positions to close.")
        return {
            "status":          "STUB_NO_API",
            "api_available":   False,
            "message":         "Trading API pending Q3-Q4 2026 release. No real positions.",
            "timestamp_jst":   _ts(),
        }

    # === TO BE IMPLEMENTED WHEN API AVAILABLE (K444) ===
    # See K380 Bybit close-all pattern in scripts/emergency_hl_exit.py
    # var_api_key = os.environ.get("VARIATIONAL_API_KEY", "")
    # positions_url = "https://api.variational.io/v1/positions"
    # close_url = "https://api.variational.io/v1/order"
    # ...
    _log("  [K357] API available but implementation pending K444 production patch.")
    return {
        "status":          "STUB_PENDING_IMPL",
        "api_available":   True,
        "message":         "Trading API available but close_positions() not yet implemented. Apply K444 patch.",
        "timestamp_jst":   _ts(),
    }


# ── Multi-venue allocator state (K443 Phase 5) ────────────────────────────────

def compute_multivenue_allocation(aum_usd: float) -> Dict:
    """Compute K297 sleeve split between HL and Variational.

    Total K297 sleeve = 20% of AUM (v6.13d K297' target).
    HL K297':         60% of sleeve = 12% of AUM → K302a satellite
    Variational K297'': 40% of sleeve = 8% of AUM → this script

    Rebalance trigger: if HL_SLEEVE_TRIGGER_REBALANCE_PCT exceeded,
    shift additional 5pp to Variational (capacity management per K431).
    """
    total_sleeve = aum_usd * 0.20
    hl_alloc     = total_sleeve * 0.60
    var_alloc    = total_sleeve * 0.40

    return {
        "aum_usd":                 round(aum_usd, 0),
        "k297_sleeve_total_usd":   round(total_sleeve, 0),
        "hl_k297_prime_usd":       round(hl_alloc, 0),
        "variational_k297pp_usd":  round(var_alloc, 0),
        "hl_sleeve_pct":           round(hl_alloc / total_sleeve * 100, 1),
        "var_sleeve_pct":          round(var_alloc / total_sleeve * 100, 1),
        "rebalance_trigger":       f"HL > {HL_SLEEVE_TRIGGER_REBALANCE_PCT*100:.0f}% of sleeve → shift to Variational",
        "rebalance_cadence":       "monthly (K427 pattern)",
        "note":                    "Variational K297'' SCAFFOLD — activate when trading API available",
    }


# ── Load AUM from K429 dashboard ──────────────────────────────────────────────

def load_aum() -> float:
    """Read current AUM from K429 dashboard JSON. Falls back to DEFAULT_AUM_USD."""
    k429_path = DATA_DIR / "k429_aum_dashboard.json"
    try:
        if k429_path.exists():
            with open(k429_path) as f:
                d = json.load(f)
            return float(d.get("current_aum_usd", DEFAULT_AUM_USD))
    except Exception:
        pass
    return DEFAULT_AUM_USD


# ── Write trades log (JSONL) ──────────────────────────────────────────────────

def write_trade_record(record: Dict) -> None:
    try:
        with open(TRADES_LOG, "a") as f:
            f.write(json.dumps(record) + "\n")
    except Exception as e:
        _err(f"Failed to write trades log: {e}")


# ── Dashboard writer ──────────────────────────────────────────────────────────

def write_dashboard(payload: Dict) -> None:
    tmp = DASHBOARD_JSON.with_suffix(".tmp")
    try:
        tmp.write_text(json.dumps(payload, indent=2, default=str))
        tmp.replace(DASHBOARD_JSON)
    except Exception as e:
        _err(f"Dashboard write failed: {e}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main(args: argparse.Namespace) -> int:
    run_date_str = args.date or datetime.now(JST).strftime("%Y-%m-%d")
    _log(f"=== K443 K297'' Variational paper-trade | date={run_date_str} ===")

    # ── Priority 1: EMERGENCY flag ────────────────────────────────────────────
    if EMERGENCY_FLAG.exists():
        _log(f"  EMERGENCY_EXIT_TRIGGERED.flag detected — K443 skip (EMERGENCY mode)")
        write_dashboard({
            "status":          "EMERGENCY_SKIP",
            "date":            run_date_str,
            "updated_at_jst":  _ts(),
            "note":            "K357 emergency exit active. Variational positions are paper-trade only.",
        })
        return 0

    # ── Priority 2: BEAR_1 flag ───────────────────────────────────────────────
    bear1_active = BEAR1_FLAG.exists()
    if bear1_active:
        _log("  BEAR_1_FALLBACK_ACTIVE.flag detected — CL weight halved, XAU/XAG held.")

    # ── Load AUM ──────────────────────────────────────────────────────────────
    aum_usd = load_aum()
    sleeve_usd = aum_usd * SLEEVE_PCT_OF_AUM
    _log(f"  AUM=${aum_usd:,.0f}  K297'' sleeve=${sleeve_usd:,.0f} ({SLEEVE_PCT_OF_AUM*100:.0f}% of AUM)")

    # ── Fetch FR data ─────────────────────────────────────────────────────────
    fr_data = fetch_variational_fr()
    if not fr_data:
        _err("FR data unavailable — aborting run.")
        return 1

    # ── Compute inv-vol weights ───────────────────────────────────────────────
    weights = compute_invvol_weights(fr_data)
    _log(f"  Inv-vol weights: {weights}")

    # ── XAU trend filter (SPX-proxy) ──────────────────────────────────────────
    xau_filter = xau_trend_filter_passes(fr_data)
    active_signal: Dict[str, bool] = {
        "XAU": True if XAU_ALWAYS_ON else xau_filter,
        "XAG": xau_filter,
        "CL":  xau_filter,
    }
    _log(f"  XAU filter pass={xau_filter} | signals: {active_signal}")

    # ── BEAR_1 adjustment ─────────────────────────────────────────────────────
    if bear1_active:
        weights, active_signal = apply_bear1_adjustments(weights, active_signal)

    # ── PnL calculation ───────────────────────────────────────────────────────
    pnl_result = compute_daily_pnl(fr_data, weights, active_signal, sleeve_usd)
    _log(f"  Net PnL: ${pnl_result['net_pnl_usd']:.4f}  ({pnl_result['net_pnl_bps']:.2f} bps)")

    # ── Multi-venue allocation ────────────────────────────────────────────────
    allocation = compute_multivenue_allocation(aum_usd)

    # ── Profit projection (K443 Phase 8) ─────────────────────────────────────
    #   Annualized from today's paper PnL (single-day estimate)
    ann_net_pnl = pnl_result["net_pnl_usd"] * 365.0
    ann_net_pct = (ann_net_pnl / aum_usd * 100) if aum_usd > 0 else 0.0

    # ── Build dashboard payload ───────────────────────────────────────────────
    dashboard = {
        "wave":                    "K443",
        "strategy":                "K297''-Variational (XAU 50% + XAG 30% + CL 20%)",
        "mode":                    "PAPER-TRADE",
        "api_status":              "PENDING" if not VARIATIONAL_TRADING_API_AVAILABLE else "AVAILABLE",
        "trading_api_target":      "Q3-Q4 2026",
        "activation_trigger":      "Variational trading API public release",
        "date":                    run_date_str,
        "updated_at_jst":          _ts(),
        "bear1_active":            bear1_active,
        "emergency_active":        False,
        "aum_usd":                 round(aum_usd, 0),
        "sleeve_usd":              round(sleeve_usd, 0),
        "sleeve_pct_of_aum":       SLEEVE_PCT_OF_AUM,
        "fr_data": {
            sym: {
                "fr_ann_pct": fr_data[sym].get("fr_ann_pct"),
                "oi_usd":     fr_data[sym].get("oi_usd"),
                "source":     fr_data[sym].get("source"),
            }
            for sym in fr_data
        },
        "inv_vol_weights":         weights,
        "active_signals":          active_signal,
        "xau_filter_pass":         xau_filter,
        "pnl_result":              pnl_result,
        "ann_net_pnl_usd":         round(ann_net_pnl, 0),
        "ann_net_pct":             round(ann_net_pct, 4),
        "multivenue_allocation":   allocation,
        "profit_projection": {
            "25M_aum_est_yr_usd":  5_500_000,   # K443 Phase 8: HL+Bybit+Variational
            "50M_aum_est_yr_usd":  6_500_000,   # K443 Phase 8: 3-venue capacity
            "vs_drift_note":       "Variational > Drift: XAG/CL not on Drift, HIP-3 equiv, $3.85B TVL",
            "capacity_note":       "$25M+ AUM requires Variational (K431: HL alone insufficient)",
        },
        "venue_comparison": {
            "HL_K297_prime": {
                "instruments": ["PAXG", "SPX"],
                "settlement":  "1h/8h",
                "sleeve_pct":  SLEEVE_PCT_HL_K297,
            },
            "Variational_K297pp": {
                "instruments": ["XAU", "XAG", "CL"],
                "settlement":  "4h",
                "sleeve_pct":  SLEEVE_PCT_OF_AUM,
                "new_assets":  ["XAG", "CL"],
            },
        },
        "close_stub": {
            "function":   "close_variational_positions()",
            "status":     "SCAFFOLD — trading API required (K444 production patch)",
            "pattern":    "K357/K380 emergency exit pattern",
        },
        "notes": [
            "K443: SCAFFOLD-READY. Paper-trade starts daily cron when plist activated.",
            "Activation: Variational trading API release → K444 paper-trade 60d → production.",
            "Multi-venue rebalance: monthly (K427). Trigger: HL > 65% of K297 sleeve.",
            "K363 daemon: accumulates FR snapshots (load plist to start data collection).",
            "Profit lift: +$1-2M/yr at $25M AUM (Variational K297 capacity unlocked).",
        ],
    }

    if not args.dry_run:
        write_dashboard(dashboard)
        write_trade_record({
            "date": run_date_str,
            "ts_jst": _ts(),
            "net_pnl_usd": pnl_result["net_pnl_usd"],
            "ann_pct": ann_net_pct,
            "weights": weights,
            "signals": active_signal,
            "bear1": bear1_active,
            "api_status": "PENDING",
        })
        _log(f"  Dashboard written: {DASHBOARD_JSON}")
    else:
        _log("  [dry-run] dashboard NOT written")

    # ── Summary ───────────────────────────────────────────────────────────────
    _log(f"  === K443 K297'' Summary ===")
    _log(f"  Mode: PAPER-TRADE (API: {dashboard['api_status']})")
    _log(f"  Sleeve: ${sleeve_usd:,.0f} ({SLEEVE_PCT_OF_AUM*100:.0f}% of ${aum_usd:,.0f} AUM)")
    _log(f"  Today net PnL: ${pnl_result['net_pnl_usd']:.4f} ({pnl_result['net_pnl_bps']:.2f} bps)")
    _log(f"  Ann est:       ${ann_net_pnl:,.0f}/yr  ({ann_net_pct:.4f}% of AUM)")
    _log(f"  Activation:    {dashboard['trading_api_target']} → K444 60d paper-trade → production")
    _log(f"=== K443 done ===")

    return 0


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="K443 K297'' Variational paper-trade scaffold"
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="Compute but do not write dashboard/logs")
    parser.add_argument("--date",
                        help="Override run date (YYYY-MM-DD, default: today JST)")
    parser.add_argument("--status", action="store_true",
                        help="Print current dashboard summary and exit")
    args = parser.parse_args()

    if args.status:
        try:
            with open(DASHBOARD_JSON) as f:
                d = json.load(f)
            print(json.dumps({
                "wave":         d.get("wave"),
                "mode":         d.get("mode"),
                "api_status":   d.get("api_status"),
                "date":         d.get("date"),
                "updated":      d.get("updated_at_jst"),
                "net_pnl_usd":  d.get("pnl_result", {}).get("net_pnl_usd"),
                "ann_est_usd":  d.get("ann_net_pnl_usd"),
            }, indent=2))
        except Exception as e:
            print(f"No dashboard yet: {e}")
        sys.exit(0)

    sys.exit(main(args))
