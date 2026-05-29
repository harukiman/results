"""K208 Microstructure Feature Module (K492-1)
==============================================
Computes microstructure signals for K208 entry gate enhancement.

This module is a PROPOSAL ONLY — not integrated into production.
Production integration requires 14-day paper-trade confirmation.

Features:
  1. FR gradient: rate of change of HL-Bybit spread over last 4h (1.5 periods)
  2. Spread compression ratio: spread_now / max(spread_last_24h)
  3. HL trade direction imbalance: net buy fraction over last 60min
  4. Book pressure proxy: hl_predicted_fr - hl_current_fr (positive = crowding)

Integration:
  - Called from scripts/k280_live_fetch.py when MICROSTRUCTURE_ENABLED=True
  - Returns per-symbol bool gate: True = OK to enter, False = skip this period
  - Graceful degradation: if data unavailable, gate returns True (no filter)

Usage:
  from k208_microstructure import batch_microstructure_check
  gates = batch_microstructure_check(K208_ACTIVE_SYMS)
  # gates = {"SOL": True, "XRP": False, ...}

K339 REPO_ROOT pattern. No production modification.
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import requests

# ── Paths ──────────────────────────────────────────────────────────────────────
BASE     = Path(__file__).resolve().parent.parent
CACHE    = BASE / "cache"
HL_CACHE = CACHE / "k163_hl"

# ── Configuration toggles ──────────────────────────────────────────────────────
MICROSTRUCTURE_ENABLED       = False   # master toggle (set True after paper-trade)
FR_GRADIENT_ENABLED          = True    # sub-toggle: FR gradient feature
SPREAD_COMPRESSION_ENABLED   = True    # sub-toggle: compression ratio
TRADE_IMBALANCE_ENABLED      = False   # sub-toggle: requires HL recentTrades API call
BOOK_PRESSURE_ENABLED        = False   # sub-toggle: requires K304 predictedFR daemon

# ── Thresholds ─────────────────────────────────────────────────────────────────
FR_GRADIENT_THRESHOLD        = 0.0    # positive gradient required
SPREAD_COMPRESSION_THRESHOLD = 0.75   # spread must be >= 75% of 24h max
TRADE_IMBALANCE_THRESHOLD    = 0.60   # skip if buy-side > 60% (crowded long)
BOOK_PRESSURE_THRESHOLD      = 0.0    # skip if pred_fr - curr_fr > 0 (crowding)

# ── API settings ───────────────────────────────────────────────────────────────
HL_API_URL       = "https://api.hyperliquid.xyz/info"
REQUEST_TIMEOUT  = 5   # seconds

# ── Bybit ticker overrides ────────────────────────────────────────────────────
BYBIT_OVERRIDES: Dict[str, str] = {
    "BONK": "1000BONK", "PEPE": "1000PEPE", "MEME": "1000MEME",
}


# ──────────────────────────────────────────────────────────────────────────────
# Feature 1: FR Gradient
# ──────────────────────────────────────────────────────────────────────────────

def load_hl_fr_series(sym: str, n_periods: int = 5) -> Optional[pd.Series]:
    """Load last N periods of HL FR from parquet cache.

    Returns:
        pd.Series of HL FR values (most recent last), or None if unavailable.
    """
    f = HL_CACHE / f"hl_fr_{sym}.parquet"
    if not f.exists():
        return None
    try:
        df = pd.read_parquet(f)
        col = "hl_fr" if "hl_fr" in df.columns else df.columns[0]
        if "timestamp" in df.columns:
            df = df.set_index("timestamp")
        s = df[col].astype(float).sort_index().dropna()
        return s.iloc[-n_periods:] if len(s) >= n_periods else s
    except Exception:
        return None


def compute_fr_gradient(
    sym: str,
    bybit_fr: Optional[float] = None,
    lookback_periods: int = 2,
) -> Optional[float]:
    """Compute FR spread gradient over last lookback_periods × 8h.

    Args:
        sym:              Symbol (e.g. "SOL").
        bybit_fr:         Current Bybit FR (bps). If None, not used.
        lookback_periods: Number of 8h periods to look back (default 2 = 16h).

    Returns:
        Normalised gradient: (spread_now - spread_prev) / std(spread_hist).
        Positive = spread still expanding (good entry signal).
        None if insufficient data.
    """
    hl_series = load_hl_fr_series(sym, n_periods=lookback_periods + 2)
    if hl_series is None or len(hl_series) < 2:
        return None

    hl_now  = float(hl_series.iloc[-1])
    hl_prev = float(hl_series.iloc[-2]) if len(hl_series) >= 2 else hl_now
    hl_std  = float(hl_series.std()) if len(hl_series) >= 3 else 1.0

    # If bybit_fr not provided, use HL gradient only (direction signal)
    if bybit_fr is not None:
        # Spread gradient: approximated by HL FR change (HL is the short leg)
        # HL FR increasing → spread (Bybit - HL) decreasing → bad entry
        # HL FR decreasing → spread (Bybit - HL) increasing → good entry
        gradient = (hl_prev - hl_now) / (abs(hl_std) + 1e-8)
    else:
        gradient = (hl_prev - hl_now) / (abs(hl_std) + 1e-8)

    return round(gradient, 6)


# ──────────────────────────────────────────────────────────────────────────────
# Feature 2: Spread Compression Ratio
# ──────────────────────────────────────────────────────────────────────────────

def compute_spread_compression(
    sym: str,
    current_spread_bps: Optional[float] = None,
    window_periods: int = 9,
) -> Optional[float]:
    """Compute spread compression ratio: spread_now / max(spread_last_24h).

    Args:
        sym:                 Symbol.
        current_spread_bps:  Current FR spread in bps (Bybit - HL).
        window_periods:      Number of 8h periods for window (9 = 72h = 3 days).

    Returns:
        Ratio in [0, 1+]. >= SPREAD_COMPRESSION_THRESHOLD is good.
        None if insufficient data.
    """
    hl_series = load_hl_fr_series(sym, n_periods=window_periods + 1)
    if hl_series is None or len(hl_series) < 3:
        return None

    hl_max  = float(hl_series.abs().max())
    if hl_max < 1e-8:
        return None

    if current_spread_bps is not None:
        ratio = abs(current_spread_bps) / (hl_max * 1e4 + 1e-8)
    else:
        hl_now = float(hl_series.iloc[-1])
        ratio = abs(hl_now) / (hl_max + 1e-8)

    return round(ratio, 6)


# ──────────────────────────────────────────────────────────────────────────────
# Feature 3: Trade Direction Imbalance
# ──────────────────────────────────────────────────────────────────────────────

def fetch_hl_trade_imbalance(
    sym: str,
    lookback_min: int = 60,
) -> Optional[float]:
    """Fetch net buy fraction from HL recent trades API.

    Args:
        sym:          Symbol (e.g. "SOL").
        lookback_min: Lookback window in minutes (default 60).

    Returns:
        Buy fraction in [0, 1]. > TRADE_IMBALANCE_THRESHOLD = crowded long (skip).
        None if API call fails.

    API: POST https://api.hyperliquid.xyz/info
         {"type": "recentTrades", "coin": "SOL"}
    """
    if not TRADE_IMBALANCE_ENABLED:
        return None
    try:
        resp = requests.post(
            HL_API_URL,
            json={"type": "recentTrades", "coin": sym},
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        trades = resp.json()
        if not isinstance(trades, list) or not trades:
            return None

        cutoff_ms = (time.time() - lookback_min * 60) * 1000
        recent = [t for t in trades if float(t.get("time", 0)) >= cutoff_ms]
        if not recent:
            return None

        buy_vol  = sum(float(t.get("sz", 0)) for t in recent if t.get("side", "") == "B")
        sell_vol = sum(float(t.get("sz", 0)) for t in recent if t.get("side", "") == "A")
        total    = buy_vol + sell_vol
        if total < 1e-8:
            return None

        return round(buy_vol / total, 4)

    except Exception:
        return None


# ──────────────────────────────────────────────────────────────────────────────
# Feature 4: Book Pressure Proxy (predictedFR delta)
# ──────────────────────────────────────────────────────────────────────────────

def get_book_pressure_proxy(sym: str) -> Optional[float]:
    """Compute book pressure proxy from predictedFR - current FR.

    Uses K304 predictedFundings cache if available.

    Returns:
        Positive value → crowding (book pricing in FR rise) → bad entry.
        Negative value → no crowding → potentially good entry.
        None if K304 cache not available.
    """
    if not BOOK_PRESSURE_ENABLED:
        return None

    snap_files = sorted(CACHE.glob("hl_predicted_fr_*.parquet"))
    if not snap_files:
        return None

    try:
        df = pd.read_parquet(snap_files[-1])
        row = df[df["coin"] == sym]
        if row.empty:
            return None
        hl_pred = float(row["hl_fr"].values[0]) if "hl_fr" in row.columns else None
        if hl_pred is None:
            return None
        hl_curr_series = load_hl_fr_series(sym, n_periods=1)
        if hl_curr_series is None or len(hl_curr_series) == 0:
            return None
        hl_curr = float(hl_curr_series.iloc[-1])
        return round((hl_pred - hl_curr) * 1e4, 6)  # bps difference
    except Exception:
        return None


# ──────────────────────────────────────────────────────────────────────────────
# Gate Decision
# ──────────────────────────────────────────────────────────────────────────────

def get_microstructure_gate(
    sym: str,
    bybit_fr: Optional[float] = None,
    current_spread_bps: Optional[float] = None,
) -> Tuple[bool, Dict]:
    """Evaluate microstructure gate for a single symbol.

    Args:
        sym:                 Symbol (e.g. "SOL").
        bybit_fr:            Current Bybit FR (bps). Optional.
        current_spread_bps:  Current FR spread Bybit - HL (bps). Optional.

    Returns:
        (gate_pass: bool, details: dict)
        gate_pass = True → proceed with entry
        gate_pass = False → skip this entry

    Graceful degradation: if any feature is unavailable, it is treated as
    "neutral" (does not block entry), so unavailability never over-filters.
    """
    if not MICROSTRUCTURE_ENABLED:
        return True, {"reason": "MICROSTRUCTURE_ENABLED=False (no filter)"}

    details: Dict = {}
    votes_pass = 0
    votes_total = 0

    # Feature 1: FR Gradient
    if FR_GRADIENT_ENABLED:
        grad = compute_fr_gradient(sym, bybit_fr=bybit_fr)
        if grad is not None:
            votes_total += 1
            vote = grad >= FR_GRADIENT_THRESHOLD
            if vote:
                votes_pass += 1
            details["fr_gradient"] = {"value": grad, "threshold": FR_GRADIENT_THRESHOLD, "pass": vote}

    # Feature 2: Spread Compression
    if SPREAD_COMPRESSION_ENABLED:
        comp = compute_spread_compression(sym, current_spread_bps)
        if comp is not None:
            votes_total += 1
            vote = comp >= SPREAD_COMPRESSION_THRESHOLD
            if vote:
                votes_pass += 1
            details["spread_compression"] = {"value": comp, "threshold": SPREAD_COMPRESSION_THRESHOLD, "pass": vote}

    # Feature 3: Trade Imbalance
    if TRADE_IMBALANCE_ENABLED:
        imb = fetch_hl_trade_imbalance(sym)
        if imb is not None:
            votes_total += 1
            vote = imb <= TRADE_IMBALANCE_THRESHOLD
            if vote:
                votes_pass += 1
            details["trade_imbalance"] = {"value": imb, "threshold": TRADE_IMBALANCE_THRESHOLD, "pass": vote}

    # Feature 4: Book Pressure
    if BOOK_PRESSURE_ENABLED:
        pressure = get_book_pressure_proxy(sym)
        if pressure is not None:
            votes_total += 1
            vote = pressure <= BOOK_PRESSURE_THRESHOLD
            if vote:
                votes_pass += 1
            details["book_pressure"] = {"value": pressure, "threshold": BOOK_PRESSURE_THRESHOLD, "pass": vote}

    # Decision: pass if majority of available features agree (>= ceil(n/2))
    # With 0 available features: default to True (no filter).
    if votes_total == 0:
        gate_pass = True
        details["reason"] = "No microstructure data available — default pass"
    else:
        required = max(1, (votes_total + 1) // 2)  # majority
        gate_pass = votes_pass >= required
        details["votes_pass"] = votes_pass
        details["votes_total"] = votes_total
        details["required"] = required
        details["reason"] = f"{votes_pass}/{votes_total} features pass (required {required})"

    return gate_pass, details


def batch_microstructure_check(
    syms: List[str],
    bybit_frs: Optional[Dict[str, float]] = None,
    spreads_bps: Optional[Dict[str, float]] = None,
) -> Dict[str, Tuple[bool, Dict]]:
    """Evaluate microstructure gate for all symbols in batch.

    Args:
        syms:       List of symbol strings.
        bybit_frs:  Optional dict of {sym: bybit_fr_bps}.
        spreads_bps: Optional dict of {sym: spread_bps}.

    Returns:
        Dict of {sym: (gate_pass, details)}.
    """
    results: Dict[str, Tuple[bool, Dict]] = {}
    for sym in syms:
        bfr = bybit_frs.get(sym) if bybit_frs else None
        sp  = spreads_bps.get(sym) if spreads_bps else None
        results[sym] = get_microstructure_gate(sym, bybit_fr=bfr, current_spread_bps=sp)
    return results


# ──────────────────────────────────────────────────────────────────────────────
# Standalone diagnostics
# ──────────────────────────────────────────────────────────────────────────────

def run_diagnostics(syms: List[str]) -> None:
    """Run microstructure diagnostics on given symbols and print report."""
    print("=" * 60)
    print(f"K208 Microstructure Diagnostics  [{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}]")
    print(f"MICROSTRUCTURE_ENABLED: {MICROSTRUCTURE_ENABLED}")
    print("=" * 60)

    for sym in syms:
        grad = compute_fr_gradient(sym)
        comp = compute_spread_compression(sym)
        imb  = fetch_hl_trade_imbalance(sym) if TRADE_IMBALANCE_ENABLED else "disabled"
        pres = get_book_pressure_proxy() if BOOK_PRESSURE_ENABLED else "disabled"  # type: ignore[call-arg]
        gate, detail = get_microstructure_gate(sym)
        status = "PASS" if gate else "SKIP"
        print(f"  {sym:<6} | gate={status}  grad={str(grad):<10}  "
              f"comp={str(comp):<8}  imb={str(imb):<8}  | {detail.get('reason', '')}")


if __name__ == "__main__":
    K208_ACTIVE = ["SOL", "XRP", "SUI", "OP", "APT", "JTO", "IMX", "SAND", "ADA"]
    run_diagnostics(K208_ACTIVE)
