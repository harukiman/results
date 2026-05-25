"""
k287_satellite_run.py — K287d Satellite Daily Paper-Trade Execution
====================================================================
Satellite portfolio: K270 (dYdX FR carry) + K275 (OKX FR carry)
  - K270: dYdX v4, 30 symbols, 14d rolling mean FR, L/S quartile
  - K275: OKX perp,  35 symbols,  7d rolling mean FR, L/S quartile
  - Inv-vol allocator: natural ~35.5% K270 / ~64.5% K275
  - Portfolio weight within K287d: 20% satellite / 80% K280 main

No K280 component here (separate daemon at 09:00 JST via com.cryptolab.k280-live.plist).
Satellite daemon runs at 09:30 JST.

Backtest reference (K287c inv-vol satellite):
  OOS Sharpe: 22.95 | MaxDD: -0.000496 | WF min: 17.01
  K270 weights: ~35.5%  |  K275 weights: ~64.5%

Daily workflow:
  1. Load k270_dydx_daily.parquet  → K270 FR signals → daily PnL
  2. Load okx_fr_daily.parquet     → K275 FR signals → daily PnL
  3. Inv-vol weights (60d window)  → satellite combined PnL
  4. Load K280 main equity from data/k280_live_dashboard.json
  5. Combined K287d = 80% K280 + 20% Satellite
  6. Alerts: satellite DD, component Sh floors, exchange status
  7. Save data/k287_satellite_dashboard.json

Usage:
  python3 scripts/k287_satellite_run.py
  python3 scripts/k287_satellite_run.py --date 2026-05-25
"""
from __future__ import annotations

import argparse
import json
import math
import time
import warnings
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

# ── Paths ──────────────────────────────────────────────────────────────────────
BASE       = Path("/Users/nekonaomichi/crypto-lab")
CACHE      = BASE / "cache"
DATA       = BASE / "data"
DATA.mkdir(exist_ok=True)

DASHBOARD_JSON = DATA / "k287_satellite_dashboard.json"
TRADES_LOG     = DATA / "k287_satellite_paper_trades.jsonl"

K280_DASHBOARD = DATA / "k280_live_dashboard.json"

# ── Universes (from K270/K275 specs) ──────────────────────────────────────────
K270_SYMBOLS = [
    "AAVE", "ADA",  "APT",  "ARB",  "ATOM",
    "AVAX", "AXS",  "BLUR", "BONK", "CRV",
    "DOGE", "DOT",  "ENA",  "INJ",  "JUP",
    "LDO",  "NEAR", "OP",   "PEPE", "PYTH",
    "SEI",  "SOL",  "SUI",  "TAO",  "TIA",
    "UNI",  "WIF",  "WLD",  "XRP",  "BNB",
]

K275_SYMBOLS = [
    "DOGE", "AVAX", "LINK", "ARB",  "NEAR", "DOT",  "ATOM",
    "BNB",  "LTC",  "UNI",  "AAVE", "INJ",  "TIA",  "SEI",
    "STRK", "WLD",  "ENA",  "BLUR", "BONK", "PEPE", "WIF",
    "PYTH", "JUP",  "BOME", "ONDO", "CRV",  "SUSHI","MEME",
    "SHIB", "TAO",  "DYDX", "FIL",  "GRT",  "SNX",  "COMP",
]

# ── Strategy Parameters ────────────────────────────────────────────────────────
K270_FR_WINDOW   = 14       # 14d rolling mean (per K270 spec)
K275_FR_WINDOW   = 7        # 7d rolling mean (per K275 spec, shorter due to 90d OKX history)
QUARTILE         = 0.25     # top/bottom 25% for L/S sleeves
K270_COST_RATE   = 3e-4     # 3bp dYdX maker (wider: DEX liquidity thinner, K270 spec note)
K275_COST_RATE   = 2e-4     # 2bp OKX maker
K270_EVENTS_DAY  = 24       # dYdX hourly FR: panel is daily mean of hourly
K275_EVENTS_DAY  = 3        # OKX 8h FR: panel is daily sum = 3×8h events

# ── K287d Portfolio Weights (K280 main + Satellite) ────────────────────────────
K287D_MAIN_WEIGHT      = 0.80   # K280 main daemon (already running)
K287D_SATELLITE_WEIGHT = 0.20   # K287c satellite

# ── Backtest Reference Metrics ─────────────────────────────────────────────────
BT_K270_OOS_SH  = 11.854
BT_K275_OOS_SH  = 30.249
BT_SAT_OOS_SH   = 22.95     # K287c inv-vol satellite
BT_SAT_OOS_DD   = -0.000496 # K287c MaxDD
BT_SAT_WF_MIN   = 17.01
BT_SAT_K270_W   = 0.355     # inv-vol natural weight K270 within satellite
BT_SAT_K275_W   = 0.645     # inv-vol natural weight K275 within satellite
BT_K287D_SH     = 33.00     # K287d combined (K280 80% + Sat 20%) OOS Sharpe

# ── Alert Thresholds ──────────────────────────────────────────────────────────
ALERT_SAT_30D_DD_MAX    = 0.015   # Satellite 30d DD > 1.5% → REDUCE
ALERT_K270_30D_SH_MIN   = 3.0    # K270 30d Sh < 3.0 → low carry regime
ALERT_K275_30D_SH_MIN   = 3.0    # K275 30d Sh < 3.0 → low carry regime
TRADING_DAYS = 365


# ─────────────────────────────────────────────────────────────────────────────
# Metric helpers
# ─────────────────────────────────────────────────────────────────────────────

def sharpe_d(r: np.ndarray, ann: int = TRADING_DAYS) -> float:
    """Daily-return Sharpe annualised."""
    r = np.asarray(r, dtype=float)
    r = r[np.isfinite(r)]
    if len(r) < 2 or r.std(ddof=1) == 0:
        return 0.0
    return float(r.mean() / r.std(ddof=1) * math.sqrt(ann))


def max_dd(equity: np.ndarray) -> float:
    eq   = np.asarray(equity, dtype=float)
    peak = np.maximum.accumulate(eq)
    return float(((eq - peak) / (peak + 1e-12)).min())


# ─────────────────────────────────────────────────────────────────────────────
# Data loading
# ─────────────────────────────────────────────────────────────────────────────

def load_k270_panel() -> pd.DataFrame:
    """Load K270 dYdX daily FR panel (cache/k270_dydx_daily.parquet)."""
    path = CACHE / "k270_dydx_daily.parquet"
    if not path.exists():
        # Fallback: build from per-symbol files in k270_dydx/
        print("  [K270] k270_dydx_daily.parquet not found. Building from per-symbol cache...")
        sym_daily: Dict[str, pd.Series] = {}
        dydx_cache = CACHE / "k270_dydx"
        for sym in K270_SYMBOLS:
            f = dydx_cache / f"dydx_fr_{sym}.parquet"
            if not f.exists():
                continue
            try:
                df = pd.read_parquet(f)
                if "timestamp" not in df.columns:
                    df = df.reset_index()
                df["timestamp"] = pd.to_datetime(df["timestamp"])
                df = df.set_index("timestamp").sort_index()
                daily = df["dydx_fr"].resample("D").mean().dropna()
                daily.index = daily.index.normalize()
                sym_daily[sym] = daily
            except Exception as e:
                print(f"    {sym}: {e}")
        if not sym_daily:
            print("  [K270] No per-symbol cache found either!")
            return pd.DataFrame()
        panel = pd.DataFrame(sym_daily).sort_index()
        panel.to_parquet(path)
        return panel
    df = pd.read_parquet(path)
    df.index = pd.to_datetime(df.index)
    return df


def load_k275_panel() -> pd.DataFrame:
    """Load K275 OKX daily FR panel (cache/okx_fr_daily.parquet)."""
    path = CACHE / "okx_fr_daily.parquet"
    if not path.exists():
        print("  [K275] okx_fr_daily.parquet not found!")
        return pd.DataFrame()
    df = pd.read_parquet(path)
    df.index = pd.to_datetime(df.index)
    return df


def load_live_snapshot(date_str: str) -> Optional[Dict]:
    """Load today's satellite fetch snapshot JSON."""
    p = CACHE / f"k287_satellite_{date_str.replace('-', '')}.json"
    if p.exists():
        with open(p) as f:
            return json.load(f)
    return None


def load_k280_dashboard() -> Optional[Dict]:
    """Load K280 main dashboard for combined view."""
    if K280_DASHBOARD.exists():
        with open(K280_DASHBOARD) as f:
            return json.load(f)
    return None


def load_dashboard() -> Dict:
    """Load existing satellite dashboard or create empty structure."""
    if DASHBOARD_JSON.exists():
        with open(DASHBOARD_JSON) as f:
            return json.load(f)
    return {
        "architecture":      "K287d Satellite (K270 dYdX + K275 OKX)",
        "version":           "K287d v1.0",
        "backtest_sat_oos_sh":     BT_SAT_OOS_SH,
        "backtest_sat_oos_dd":     BT_SAT_OOS_DD,
        "backtest_sat_wf_min":     BT_SAT_WF_MIN,
        "backtest_sat_k270_w":     BT_SAT_K270_W,
        "backtest_sat_k275_w":     BT_SAT_K275_W,
        "backtest_k287d_combined_sh": BT_K287D_SH,
        "k287d_main_weight":       K287D_MAIN_WEIGHT,
        "k287d_satellite_weight":  K287D_SATELLITE_WEIGHT,
        "daily_records":     [],
        "alerts":            [],
        "last_update":       None,
    }


# ─────────────────────────────────────────────────────────────────────────────
# K270 Component: dYdX 14d FR Rank L/S Quartile
# ─────────────────────────────────────────────────────────────────────────────

def compute_k270_daily_pnl() -> Tuple[pd.Series, Dict]:
    """
    K270: dYdX v4 30-symbol cross-sectional FR carry.
    Signal: 14d rolling mean of daily hourly FR per symbol.
    Long bottom quartile (lowest FR) → receive from shorts (delta-neutral).
    Short top quartile (highest FR)  → receive from longs (delta-neutral).
    Dollar-neutral both sleeves. Cost: 3bp/side maker.

    dYdX panel: daily mean of hourly FR events.
    Daily PnL = FR received over 24h ≈ daily_mean_fr × 24 (hourly settlements).

    Returns (daily_pnl, signal_state_dict).
    """
    print("  [K270] Computing dYdX 14d FR carry signals...")
    panel = load_k270_panel()

    if panel.empty or len(panel.columns) < 4:
        print(f"  [K270] Panel empty or too few symbols ({len(panel.columns)})")
        return pd.Series(dtype=float, name="K270"), {"error": "panel_empty"}

    # Use available K270 universe symbols only
    available = [s for s in K270_SYMBOLS if s in panel.columns]
    panel = panel[available].copy()

    # Signal: 14d rolling mean, shift +1 (yesterday's signal → today's position)
    signal = panel.rolling(window=K270_FR_WINDOW, min_periods=max(5, K270_FR_WINDOW // 2)).mean().shift(1)

    # Dollar-neutral weights: long bottom Q, short top Q
    def _dn_weights(row: pd.Series) -> pd.Series:
        valid = row.dropna()
        n = len(valid)
        if n < 4:
            return pd.Series(0.0, index=row.index)
        n_q    = max(1, int(n * QUARTILE))
        ranked = valid.rank(ascending=True)
        longs  = ranked[ranked <= n_q].index
        shorts = ranked[ranked > n - n_q].index
        w = pd.Series(0.0, index=row.index)
        if len(longs)  > 0: w[longs]  = +1.0 / len(longs)
        if len(shorts) > 0: w[shorts] = -1.0 / len(shorts)
        return w

    weights = signal.apply(_dn_weights, axis=1)

    # dYdX panel is daily mean of hourly rates → × 24 for daily total FR received
    fr_daily = panel * K270_EVENTS_DAY

    w_lag   = weights.shift(1).fillna(0.0)
    pnl_raw = (-w_lag * fr_daily).sum(axis=1)

    # Turnover cost
    turnover = (weights - weights.shift(1).fillna(0.0)).abs().sum(axis=1)
    cost     = turnover * K270_COST_RATE
    pnl_net  = (pnl_raw - cost).dropna()
    pnl_net.name = "K270"
    pnl_net.index = pd.to_datetime(pnl_net.index).normalize()

    # Current signal state
    last_sig = signal.iloc[-1].dropna()
    n_sym    = len(last_sig)
    n_q      = max(1, int(n_sym * QUARTILE))
    if n_sym >= 4:
        ranked_last = last_sig.rank(ascending=True)
        long_today  = ranked_last[ranked_last <= n_q].index.tolist()
        short_today = ranked_last[ranked_last > n_sym - n_q].index.tolist()
    else:
        long_today, short_today = [], []

    sig_state = {
        "exchange":          "dYdX v4 (Cosmos DEX)",
        "fr_window_days":    K270_FR_WINDOW,
        "n_symbols_active":  int(n_sym),
        "n_symbols_universe": len(K270_SYMBOLS),
        "long_today":        long_today,
        "short_today":       short_today,
        "panel_last_date":   str(panel.index[-1].date()),
        "panel_n_days":      len(panel),
        "pnl_30d_mean":      round(float(pnl_net.tail(30).mean()), 8) if len(pnl_net) >= 10 else None,
        "cost_rate_bp":      K270_COST_RATE * 1e4,
    }
    print(f"  [K270] {n_sym} symbols | long={long_today} | short={short_today} | "
          f"{len(pnl_net)} trading days")
    return pnl_net, sig_state


# ─────────────────────────────────────────────────────────────────────────────
# K275 Component: OKX 7d FR Rank L/S Quartile
# ─────────────────────────────────────────────────────────────────────────────

def compute_k275_daily_pnl() -> Tuple[pd.Series, Dict]:
    """
    K275: OKX 35-symbol cross-sectional FR carry.
    Signal: 7d rolling mean of daily (summed 8h) FR per symbol.
    OKX settles 3×/day: daily panel = sum of 3 × 8h events.
    Dollar-neutral L/S quartile. Cost: 2bp/side maker.

    Returns (daily_pnl, signal_state_dict).
    """
    print("  [K275] Computing OKX 7d FR carry signals...")
    panel = load_k275_panel()

    if panel.empty or len(panel.columns) < 4:
        print(f"  [K275] Panel empty or too few symbols ({len(panel.columns)})")
        return pd.Series(dtype=float, name="K275"), {"error": "panel_empty"}

    available = [s for s in K275_SYMBOLS if s in panel.columns]
    panel = panel[available].copy()

    # Signal: 7d rolling mean, shift +1
    signal = panel.rolling(window=K275_FR_WINDOW, min_periods=max(3, K275_FR_WINDOW // 2)).mean().shift(1)

    def _dn_weights(row: pd.Series) -> pd.Series:
        valid = row.dropna()
        n = len(valid)
        if n < 4:
            return pd.Series(0.0, index=row.index)
        n_q    = max(1, int(n * QUARTILE))
        ranked = valid.rank(ascending=True)
        longs  = ranked[ranked <= n_q].index
        shorts = ranked[ranked > n - n_q].index
        w = pd.Series(0.0, index=row.index)
        if len(longs)  > 0: w[longs]  = +1.0 / len(longs)
        if len(shorts) > 0: w[shorts] = -1.0 / len(shorts)
        return w

    weights = signal.apply(_dn_weights, axis=1)

    # OKX panel stores the MEAN of 3 daily 8h events (not the sum).
    # To get the actual daily carry received, multiply MEAN × 3 (settlements/day).
    # BUG FIX (K291): missing × K275_EVENTS_DAY caused costs to dominate gross carry,
    # producing live Sh = -3.55 vs backtest Sh = +30.25.
    fr_daily = panel * K275_EVENTS_DAY

    w_lag   = weights.shift(1).fillna(0.0)
    pnl_raw = (-w_lag * fr_daily).sum(axis=1)

    turnover = (weights - weights.shift(1).fillna(0.0)).abs().sum(axis=1)
    cost     = turnover * K275_COST_RATE
    pnl_net  = (pnl_raw - cost).dropna()
    pnl_net.name = "K275"
    pnl_net.index = pd.to_datetime(pnl_net.index).normalize()

    last_sig = signal.iloc[-1].dropna()
    n_sym    = len(last_sig)
    n_q      = max(1, int(n_sym * QUARTILE))
    if n_sym >= 4:
        ranked_last = last_sig.rank(ascending=True)
        long_today  = ranked_last[ranked_last <= n_q].index.tolist()
        short_today = ranked_last[ranked_last > n_sym - n_q].index.tolist()
    else:
        long_today, short_today = [], []

    sig_state = {
        "exchange":          "OKX (CEX, 8h settlement)",
        "fr_window_days":    K275_FR_WINDOW,
        "n_symbols_active":  int(n_sym),
        "n_symbols_universe": len(K275_SYMBOLS),
        "long_today":        long_today,
        "short_today":       short_today,
        "panel_last_date":   str(panel.index[-1].date()),
        "panel_n_days":      len(panel),
        "pnl_30d_mean":      round(float(pnl_net.tail(30).mean()), 8) if len(pnl_net) >= 10 else None,
        "cost_rate_bp":      K275_COST_RATE * 1e4,
    }
    print(f"  [K275] {n_sym} symbols | long={long_today} | short={short_today} | "
          f"{len(pnl_net)} trading days")
    return pnl_net, sig_state


# ─────────────────────────────────────────────────────────────────────────────
# Inv-vol Allocator (satellite internal: K270 + K275)
# ─────────────────────────────────────────────────────────────────────────────

def inv_vol_weights(returns: Dict[str, pd.Series], window: int = 60) -> Dict[str, float]:
    """
    Inverse-volatility weights on trailing `window` days.
    Expected natural split: K270 ~35.5%, K275 ~64.5% (from K287c backtest).
    """
    aligned = pd.DataFrame(returns).dropna()
    if aligned.empty or len(aligned) < 10:
        n = len(returns)
        return {k: 1.0 / n for k in returns}
    tail = aligned.tail(window)
    vols = tail.std(ddof=1)
    inv  = 1.0 / vols.replace(0, np.nan)
    inv  = inv.dropna()
    w    = inv / inv.sum()
    return {k: round(float(v), 6) for k, v in w.items()}


# ─────────────────────────────────────────────────────────────────────────────
# Rolling Metrics
# ─────────────────────────────────────────────────────────────────────────────

def compute_rolling_metrics(pnl: pd.Series, ref_sh: float = BT_SAT_OOS_SH,
                             ref_std: float = 4.0, label: str = "satellite") -> Dict:
    """Compute rolling Sharpe, MaxDD, drift z-score."""
    if pnl.empty:
        return {}
    tail30 = pnl.tail(30)
    tail7  = pnl.tail(7)
    sh_30d = sharpe_d(tail30.values) if len(tail30) >= 10 else None
    sh_7d  = sharpe_d(tail7.values)  if len(tail7)  >= 5  else None
    sh_all = sharpe_d(pnl.values)

    eq30 = np.cumprod(1 + tail30.values) if len(tail30) >= 5 else None
    eqall= np.cumprod(1 + pnl.values)

    mdd_30d = max_dd(eq30)  if eq30 is not None else None
    mdd_all = max_dd(eqall)

    drift_z = None
    if sh_30d is not None:
        drift_z = round(abs(sh_30d - ref_sh) / (ref_std + 1e-9), 3)

    return {
        "sh_7d":   round(sh_7d,  4) if sh_7d  is not None else None,
        "sh_30d":  round(sh_30d, 4) if sh_30d is not None else None,
        "sh_all":  round(sh_all, 4),
        "mdd_30d": round(mdd_30d, 6) if mdd_30d is not None else None,
        "mdd_all": round(mdd_all, 6),
        "drift_z": drift_z,
        "n_days":  len(pnl),
        "label":   label,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Alert Generation
# ─────────────────────────────────────────────────────────────────────────────

def generate_alerts(
    sat_pnl:    pd.Series,
    k270_pnl:   pd.Series,
    k275_pnl:   pd.Series,
    weights:    Dict[str, float],
    snapshot:   Optional[Dict],
    date_str:   str,
) -> List[Dict]:
    """Generate K287d satellite alerts."""
    alerts = []

    def _add(level: str, code: str, msg: str):
        alerts.append({"date": date_str, "level": level, "code": code, "message": msg})

    # Satellite 30d DD > 1.5% → REDUCE satellite weight
    if len(sat_pnl) >= 10:
        eq30 = np.cumprod(1 + sat_pnl.tail(30).values)
        mdd30 = max_dd(eq30)
        if mdd30 < -ALERT_SAT_30D_DD_MAX:
            _add("CRITICAL", "SAT_DD_EXCEED",
                 f"Satellite 30d MaxDD = {mdd30:.4f} exceeds -{ALERT_SAT_30D_DD_MAX*100:.1f}% "
                 f"threshold. REDUCE satellite weight (20% → 10%).")

    # K270 30d Sh < 3.0 → ALERT (low dYdX carry regime)
    if len(k270_pnl) >= 10:
        k270_sh30 = sharpe_d(k270_pnl.tail(30).values)
        if k270_sh30 < ALERT_K270_30D_SH_MIN:
            _add("ALERT", "K270_LOW_SH",
                 f"K270 (dYdX) 30d rolling Sh = {k270_sh30:.2f} < {ALERT_K270_30D_SH_MIN}. "
                 f"Low carry regime on dYdX. Review FR dispersion.")

    # K275 30d Sh < 3.0 → ALERT (low OKX carry regime)
    if len(k275_pnl) >= 10:
        k275_sh30 = sharpe_d(k275_pnl.tail(30).values)
        if k275_sh30 < ALERT_K275_30D_SH_MIN:
            _add("ALERT", "K275_LOW_SH",
                 f"K275 (OKX) 30d rolling Sh = {k275_sh30:.2f} < {ALERT_K275_30D_SH_MIN}. "
                 f"Low carry regime on OKX. Check funding rate compression.")

    # dYdX exchange status (counterparty risk)
    if snapshot:
        dydx_status = snapshot.get("exchange_status", {}).get("dydx", {})
        if dydx_status.get("status") != "OK":
            _add("CRITICAL", "DYDX_EXCHANGE_ERROR",
                 f"dYdX v4 indexer status: {dydx_status.get('status')} — "
                 f"{dydx_status.get('error', 'unknown error')}. "
                 f"K270 data may be stale. Verify before trading.")

    # OKX exchange status
    if snapshot:
        okx_status = snapshot.get("exchange_status", {}).get("okx", {})
        if okx_status.get("status") != "OK":
            _add("CRITICAL", "OKX_EXCHANGE_ERROR",
                 f"OKX API status: {okx_status.get('status')} — "
                 f"{okx_status.get('error', 'unknown error')}. "
                 f"K275 data may be stale.")

    # Low liquidity (from snapshot)
    if snapshot:
        k270_liq = snapshot.get("k270", {}).get("low_liquidity", [])
        if k270_liq:
            _add("INFO", "K270_LOW_LIQ",
                 f"dYdX low-liquidity symbols (< 70% 7d coverage): {k270_liq}")
        k275_liq = snapshot.get("k275", {}).get("low_liquidity", [])
        if k275_liq:
            _add("INFO", "K275_LOW_LIQ",
                 f"OKX low-liquidity symbols (< 70% 7d coverage): {k275_liq}")

    return alerts


# ─────────────────────────────────────────────────────────────────────────────
# Dashboard Update
# ─────────────────────────────────────────────────────────────────────────────

def update_dashboard(
    date_str:   str,
    sat_weights: Dict[str, float],
    sat_pnl:    pd.Series,
    k270_pnl:   pd.Series,
    k275_pnl:   pd.Series,
    signals:    Dict[str, Dict],
    alerts:     List[Dict],
    snapshot:   Optional[Dict],
    k280_dash:  Optional[Dict],
):
    """Write updated satellite dashboard JSON."""
    dash    = load_dashboard()
    rolling = compute_rolling_metrics(sat_pnl, ref_sh=BT_SAT_OOS_SH, label="satellite")

    # Per-component 30d Sharpe
    k270_sh30 = sharpe_d(k270_pnl.tail(30).values) if len(k270_pnl) >= 10 else None
    k275_sh30 = sharpe_d(k275_pnl.tail(30).values) if len(k275_pnl) >= 10 else None

    # Satellite equity
    sat_eq_all = float(np.cumprod(1 + sat_pnl.values)[-1]) if not sat_pnl.empty else 1.0
    today_sat_pnl = float(sat_pnl.iloc[-1]) if not sat_pnl.empty else 0.0

    # K280 main equity from dashboard
    k280_total_eq = None
    k280_today_pnl = None
    if k280_dash and k280_dash.get("daily_records"):
        last_k280 = k280_dash["daily_records"][-1]
        k280_today_pnl = last_k280.get("rolling", {}).get("sh_30d")  # sh not pnl, get pnl below
        # Compute K280 equity from daily records
        k280_pnl_list = []
        for rec in k280_dash["daily_records"]:
            pnl_val = None
            # Try to extract daily PnL from records
            if "daily_pnl" in rec:
                pnl_val = rec["daily_pnl"]
            elif "rolling" in rec and rec["rolling"]:
                # Reconstruct from rolling — not ideal, use what we have
                pass
            if pnl_val is not None:
                k280_pnl_list.append(pnl_val)
        if k280_pnl_list:
            k280_total_eq = float(np.prod([1 + p for p in k280_pnl_list]))

    # Combined K287d view: 80% K280 + 20% satellite
    combined_equity_note = (
        "Combined K287d = 80% K280 main + 20% satellite. "
        "K280 equity from k280_live_dashboard.json."
    )

    today_record = {
        "date":              date_str,
        "satellite_weights": sat_weights,
        "rolling":           rolling,
        "today_sat_pnl":     round(today_sat_pnl, 8),
        "sat_equity":        round(sat_eq_all, 6),
        "k280_total_eq":     round(k280_total_eq, 6) if k280_total_eq else None,
        "component": {
            "K270": {
                "exchange":    "dYdX v4",
                "weight":      sat_weights.get("K270", 0.0),
                "ref_weight":  BT_SAT_K270_W,
                "sh_30d":      round(k270_sh30, 4) if k270_sh30 is not None else None,
                "ref_oos_sh":  BT_K270_OOS_SH,
                "signal":      signals.get("K270", {}),
            },
            "K275": {
                "exchange":    "OKX",
                "weight":      sat_weights.get("K275", 0.0),
                "ref_weight":  BT_SAT_K275_W,
                "sh_30d":      round(k275_sh30, 4) if k275_sh30 is not None else None,
                "ref_oos_sh":  BT_K275_OOS_SH,
                "signal":      signals.get("K275", {}),
            },
        },
        "alerts_today":      alerts,
        "exchange_status":   snapshot.get("exchange_status", {}) if snapshot else {},
        "backtest_ref": {
            "sat_oos_sh":          BT_SAT_OOS_SH,
            "sat_oos_dd":          BT_SAT_OOS_DD,
            "sat_wf_min":          BT_SAT_WF_MIN,
            "k287d_combined_sh":   BT_K287D_SH,
            "k270_backtest_oos_sh": BT_K270_OOS_SH,
            "k275_backtest_oos_sh": BT_K275_OOS_SH,
        },
    }

    dash["last_update"]         = datetime.now(timezone.utc).isoformat()
    dash["rolling_metrics"]     = rolling
    dash["satellite_weights"]   = sat_weights
    dash["today_sat_pnl"]       = round(today_sat_pnl, 8)
    dash["sat_equity"]          = round(sat_eq_all, 6)
    dash["combined_equity_note"] = combined_equity_note

    # Append daily record (dedup by date)
    records = dash.get("daily_records", [])
    records = [r for r in records if r.get("date") != date_str]
    records.append(today_record)
    dash["daily_records"] = sorted(records, key=lambda r: r["date"])

    # Accumulate alerts (keep last 100)
    all_alerts = dash.get("alerts", [])
    all_alerts = [a for a in all_alerts if a.get("date") != date_str]
    all_alerts.extend(alerts)
    dash["alerts"] = all_alerts[-100:]

    # Active alert flags
    dash["active_alert_flags"] = {
        "sat_dd_exceed":     any(a["code"] == "SAT_DD_EXCEED"        for a in alerts),
        "k270_low_sh":       any(a["code"] == "K270_LOW_SH"          for a in alerts),
        "k275_low_sh":       any(a["code"] == "K275_LOW_SH"          for a in alerts),
        "dydx_exchange_err": any(a["code"] == "DYDX_EXCHANGE_ERROR"  for a in alerts),
        "okx_exchange_err":  any(a["code"] == "OKX_EXCHANGE_ERROR"   for a in alerts),
        "k270_low_liq":      any(a["code"] == "K270_LOW_LIQ"         for a in alerts),
        "k275_low_liq":      any(a["code"] == "K275_LOW_LIQ"         for a in alerts),
    }

    class NaNSafe(json.JSONEncoder):
        def default(self, obj):
            if isinstance(obj, float) and math.isnan(obj):
                return None
            if isinstance(obj, np.integer):
                return int(obj)
            if isinstance(obj, np.floating):
                return None if math.isnan(float(obj)) else float(obj)
            return super().default(obj)

    with open(DASHBOARD_JSON, "w") as f:
        json.dump(dash, f, indent=2, cls=NaNSafe)
    print(f"\n  Dashboard saved: {DASHBOARD_JSON}")


# ─────────────────────────────────────────────────────────────────────────────
# Main Daily Run
# ─────────────────────────────────────────────────────────────────────────────

def run_daily(date_str: str):
    print(f"\n=== K287d Satellite Daily Paper-Trade Run — {date_str} ===\n")
    t0 = time.time()

    # Load today's fetch snapshot (optional)
    snapshot = load_live_snapshot(date_str)
    if snapshot is None:
        print(f"  INFO: No satellite fetch snapshot for {date_str}. "
              "Run k287_satellite_fetch.py first. Continuing with cached data only.")

    # ── Component PnL ──────────────────────────────────────────────────────────
    k270_pnl, k270_sig = compute_k270_daily_pnl()
    k275_pnl, k275_sig = compute_k275_daily_pnl()

    # ── Date alignment ─────────────────────────────────────────────────────────
    pnl_map: Dict[str, pd.Series] = {}
    for name, pnl in [("K270", k270_pnl), ("K275", k275_pnl)]:
        if not pnl.empty:
            idx = pd.to_datetime(pnl.index)
            if idx.tz is not None:
                idx = idx.tz_localize(None)
            pnl.index = idx.normalize()
            pnl_map[name] = pnl

    if not pnl_map:
        print("ERROR: No component PnL computed. Aborting.")
        return

    aligned = pd.DataFrame(pnl_map).sort_index().fillna(0)
    print(f"\n  Aligned panel: {aligned.index[0].date()} → "
          f"{aligned.index[-1].date()} ({len(aligned)} days)")

    # ── Inv-vol allocation (satellite internal) ────────────────────────────────
    print("\nComputing satellite inv-vol weights (K270/K275)...")
    sat_weights = inv_vol_weights(pnl_map, window=60)
    for comp in ["K270", "K275"]:
        if comp not in sat_weights:
            sat_weights[comp] = 0.0
    print(f"  Satellite weights (live inv-vol): {sat_weights}")
    print(f"  Reference OOS weights:            K270={BT_SAT_K270_W:.3f} / K275={BT_SAT_K275_W:.3f}")

    # ── Satellite PnL ──────────────────────────────────────────────────────────
    sat_pnl = pd.Series(0.0, index=aligned.index)
    for comp, w in sat_weights.items():
        if comp in aligned.columns:
            sat_pnl += aligned[comp] * w
    sat_pnl.name = "K287c_Satellite"

    today_sat_pnl = float(sat_pnl.iloc[-1]) if not sat_pnl.empty else 0.0
    today_date    = sat_pnl.index[-1].date() if not sat_pnl.empty else date_str
    sat_eq        = float(np.cumprod(1 + sat_pnl.values)[-1]) if not sat_pnl.empty else 1.0

    print(f"\n  Today ({today_date}) Satellite PnL: {today_sat_pnl:.6f}")
    print(f"  Satellite equity (cumulative):     {sat_eq:.6f}")

    # Rolling satellite Sharpe
    sat_sh_30d = sharpe_d(sat_pnl.tail(30).values) if len(sat_pnl) >= 10 else None
    print(f"  Satellite 30d Sharpe: {sat_sh_30d:.2f}" if sat_sh_30d else "  Satellite 30d Sharpe: N/A (<10d)")

    # ── K280 main dashboard ────────────────────────────────────────────────────
    k280_dash = load_k280_dashboard()
    if k280_dash:
        k280_sh_30d = k280_dash.get("rolling_metrics", {}).get("sh_30d", "N/A")
        print(f"  K280 main 30d Sharpe: {k280_sh_30d}")
    else:
        print("  K280 main dashboard: not available (run k280_daily_run.py separately)")

    # ── Alerts ─────────────────────────────────────────────────────────────────
    alerts = generate_alerts(
        sat_pnl,
        aligned.get("K270", pd.Series()),
        aligned.get("K275", pd.Series()),
        sat_weights,
        snapshot,
        date_str,
    )
    if alerts:
        print(f"\n  ALERTS ({len(alerts)}):")
        for a in alerts:
            print(f"    [{a['level']}] {a['code']}: {a['message']}")
    else:
        print("\n  No alerts triggered.")

    # ── Dashboard update ───────────────────────────────────────────────────────
    update_dashboard(
        date_str     = date_str,
        sat_weights  = sat_weights,
        sat_pnl      = sat_pnl,
        k270_pnl     = aligned.get("K270", pd.Series()),
        k275_pnl     = aligned.get("K275", pd.Series()),
        signals      = {"K270": k270_sig, "K275": k275_sig},
        alerts       = alerts,
        snapshot     = snapshot,
        k280_dash    = k280_dash,
    )

    # ── Paper trade log ────────────────────────────────────────────────────────
    log_entry = {
        "date":          str(today_date),
        "run_ts":        datetime.now(timezone.utc).isoformat(),
        "sat_weights":   sat_weights,
        "sat_daily_pnl": round(today_sat_pnl, 8),
        "sat_equity":    round(sat_eq, 8),
        "sat_sh_30d":    round(sat_sh_30d, 4) if sat_sh_30d is not None else None,
        "alerts":        [a["code"] for a in alerts],
        "elapsed_s":     round(time.time() - t0, 1),
    }
    with open(TRADES_LOG, "a") as f:
        f.write(json.dumps(log_entry) + "\n")

    elapsed = time.time() - t0
    print(f"\n=== Satellite daily run complete in {elapsed:.1f}s ===")
    print(f"  Log: {TRADES_LOG}")
    return log_entry


# ─────────────────────────────────────────────────────────────────────────────
# CLI Entry Point
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="K287d Satellite Daily Paper-Trade Run")
    parser.add_argument("--date", default=None, help="Date YYYY-MM-DD (default: today)")
    args = parser.parse_args()
    date_str = args.date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    run_daily(date_str)


if __name__ == "__main__":
    main()
