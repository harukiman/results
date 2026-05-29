"""
k280_daily_run.py — K280 v6.10.2 Daily Paper-Trade Execution
=============================================================
Architecture (K280 = K198+K208+K276b_top20 3-way, K265 upgraded to K276b):
  - K198  Ridge ML allocator          natural weight ~  2.6% (inv-vol, OOS weights)
  - K208  DAR(2,1) CEX-DEX FR carry  natural weight ~ 75.8% (inv-vol, primary alpha)
  - K276b HL 20-symbol FR L/S carry  natural weight ~ 21.6% (inv-vol, K265 upgrade)

Upgrade vs K272a (K274 scaffold):
  - K265  HL longtail 35 symbols     REPLACED by K276b_top20 (20 symbols)
  - OOS Sharpe: 16.13 → 18.46 (+2.33)
  - WF min: 9.92 → 12.97 (+3.05)
  - MaxDD: -0.000036 → -0.000013 (63% better)
  - K276b OOS weights: K198=0.026, K208=0.758, K276b=0.216

Daily workflow:
  1. Load today's live snapshot (cache/k280_live_YYYYMMDD.json)
  2. For each component: recompute daily PnL signal from cached data
       K198: Ridge ML walk-forward on K280 backtest curves
       K208: DAR(2,1) gate on CEX-DEX spread (unchanged from K272a)
       K276b: HL 20-symbol 14d FR rank → L/S quartile
  3. Inv-vol allocate (OOS expected: K198~2.6% / K208~75.8% / K276b~21.6%)
  4. Apply HLP alert scaling (from K200 monitor)
  5. Output: theoretical daily PnL, component weights, position signals
  6. Update data/k280_live_dashboard.json with rolling metrics + alerts

NO actual orders are placed. Paper-trade only.

Usage:
  python3 scripts/k280_daily_run.py
  python3 scripts/k280_daily_run.py --date 2026-05-25
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
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler

warnings.filterwarnings("ignore")

# ── Paths ──────────────────────────────────────────────────────────────────────
BASE     = Path("/Users/nekonaomichi/crypto-lab")
CACHE    = BASE / "cache"
HL_CACHE = CACHE / "k163_hl"
DATA     = BASE / "data"
DATA.mkdir(exist_ok=True)

DASHBOARD_JSON = DATA / "k280_live_dashboard.json"
TRADES_LOG     = DATA / "k280_paper_trades.jsonl"

# ── K280 Architecture Constants ────────────────────────────────────────────────
COMPONENTS         = ["K198", "K208", "K276b"]
TRADING_DAYS       = 365       # annualisation factor (crypto = 365d)
EVENTS_PER_DAY     = 3         # 3 × 8h events
EVENTS_PER_YEAR    = TRADING_DAYS * EVENTS_PER_DAY

# K208 symbols (10 majors, CEX-DEX reverse carry — unchanged from K272a)
K208_SYMS = ["SOL", "XRP", "SUI", "OP", "APT", "AXS", "JTO", "IMX", "SAND", "ADA"]

# K276b_top20 symbols (20, upgrade from K265's 35 longtail)
# Added vs K265: JUP, UNI, BOME, DOT, BONK
# Removed vs K265: ARK, BLUR, STRK, ARB, SUSHI, AVAX, BNB, CRV, DOGE, INJ, NEAR, SHIB, WIF, BTC, ETH
K276B_SYMS = [
    "ENA", "ONDO", "ATOM", "TIA", "SEI", "WLD", "RNDR", "TAO", "MEME",
    "AAVE", "PYTH", "LDO", "FET", "PEPE", "MKR", "JUP", "UNI", "BOME",
    "DOT", "BONK",
]

# DAR(2,1) parameters (K190/K208 — unchanged from K272a)
DAR_P     = 2
DAR_Q     = 1
DAR_WIN   = 300
DAR_REFIT = 50

# K198 Ridge walk-forward config (unchanged)
ML_TRAIN_DAYS = 90
ML_TEST_DAYS  = 30

# K276b signal parameters (same as K265, applied to 20-symbol universe)
K276B_FR_WINDOW = 14      # 14d rolling mean for signal
K276B_QUARTILE  = 0.25    # top/bottom 25% for L/S sleeves
K276B_COST_RATE = 2e-4    # 2bp maker cost per side

# ── K280 Backtest Reference Metrics (from wave_k280_k272a_k276b.json) ──────────
BT_OOS_SH   = 18.46    # OOS Sharpe (last 135d of 448d window)
BT_WF_MIN   = 12.97    # WF minimum fold Sharpe
BT_OOS_DD   = -1.3e-5  # OOS MaxDD (-0.000013)
BT_WF_STD   = 3.28     # approximate std across 4 WF fold Sharpes (from fold spreads)
BT_OOS_WEIGHTS = {"K198": 0.0257, "K208": 0.7582, "K276b": 0.2160}  # OOS inv-vol weights

# ── Alert Thresholds (K280 — same as K272a, MaxDD slightly tighter) ────────────
ALERT_K208_30D_SH_MIN   = 5.0    # K208 30d rolling Sharpe floor
ALERT_K276B_30D_SH_MIN  = 5.0    # K276b 30d rolling Sharpe floor
ALERT_PORT_30D_DD_MAX   = 0.003  # Portfolio 30d MaxDD ceiling (0.3%, K280 MaxDD -0.0013%)
ALERT_HLP_REDUCE        = -20.0  # HLP 7d pct → REDUCE
ALERT_HLP_HALT          = -40.0  # HLP 7d pct → HALT
ALERT_DRIFT_CRITICAL    = 2.0    # z-score vs backtest std


# ─────────────────────────────────────────────────────────────────────────────
# Metric helpers
# ─────────────────────────────────────────────────────────────────────────────

def sharpe_d(r: np.ndarray, ann: int = TRADING_DAYS) -> float:
    """Daily-return Sharpe, annualised to `ann` trading days."""
    r = np.asarray(r, dtype=float)
    r = r[~np.isnan(r)]
    if len(r) < 2 or r.std(ddof=1) == 0:
        return 0.0
    return float(r.mean() / r.std(ddof=1) * math.sqrt(ann))


def max_dd(equity: np.ndarray) -> float:
    eq   = np.asarray(equity, dtype=float)
    peak = np.maximum.accumulate(eq)
    return float(((eq - peak) / (peak + 1e-12)).min())


def rolling_sharpe_d(daily_pnl: pd.Series, window: int) -> pd.Series:
    r = daily_pnl.rolling(window)
    return (r.mean() / r.std(ddof=1) * math.sqrt(TRADING_DAYS)).fillna(0)


# ─────────────────────────────────────────────────────────────────────────────
# Data loading
# ─────────────────────────────────────────────────────────────────────────────

def load_bybit_fr(sym: str) -> Optional[pd.Series]:
    """Load Bybit FR from cache; tries multiple tag suffixes."""
    overrides = {"BONK": "1000BONK", "PEPE": "1000PEPE", "MEME": "1000MEME"}
    ticker = overrides.get(sym, sym)
    for tag in ("730d", "1200d", "365d", "135d", "180d"):
        f = CACHE / f"bybit_fr_{ticker}USDT_{tag}.parquet"
        if f.exists():
            df = pd.read_parquet(f)
            col = "funding_rate" if "funding_rate" in df.columns else df.columns[0]
            if "timestamp" in df.columns:
                df = df.set_index("timestamp")
            s = df[col].astype(float).sort_index()
            return s[~s.index.duplicated(keep="last")]
    return None


def load_hl_fr(sym: str) -> Optional[pd.Series]:
    """Load HL FR from k163_hl cache (hourly events)."""
    f = HL_CACHE / f"hl_fr_{sym}.parquet"
    if not f.exists():
        return None
    df = pd.read_parquet(f)
    col = "hl_fr" if "hl_fr" in df.columns else df.columns[0]
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    s = df[col].astype(float).sort_index()
    return s[~s.index.duplicated(keep="last")]


def load_k276b_panel() -> pd.DataFrame:
    """Load K276b_top20 daily FR panel from parquet cache (hl_k276b_fr_daily.parquet)."""
    p = CACHE / "hl_k276b_fr_daily.parquet"
    if not p.exists():
        # Fallback: try K265 longtail panel for overlapping symbols
        p_fallback = CACHE / "hl_longtail_fr_daily.parquet"
        if p_fallback.exists():
            print("  [K276b] hl_k276b_fr_daily.parquet not found. "
                  "Using K265 longtail panel for available K276b symbols.")
            df = pd.read_parquet(p_fallback)
            df.index = pd.to_datetime(df.index)
            available = [s for s in K276B_SYMS if s in df.columns]
            return df[available].copy() if available else pd.DataFrame()
        print("  [K276b] No panel cache found!")
        return pd.DataFrame()
    df = pd.read_parquet(p)
    df.index = pd.to_datetime(df.index)
    return df


def load_live_snapshot(date_str: str) -> Optional[dict]:
    """Load today's fetch snapshot JSON (k280 first, fallback to k272a)."""
    for prefix in ("k280", "k272a"):
        p = CACHE / f"{prefix}_live_{date_str.replace('-', '')}.json"
        if p.exists():
            with open(p) as f:
                return json.load(f)
    return None


def load_dashboard() -> dict:
    """Load existing dashboard JSON or create empty structure."""
    if DASHBOARD_JSON.exists():
        with open(DASHBOARD_JSON) as f:
            return json.load(f)
    return {
        "architecture":    "K280 v6.10.2 (K198+K208+K276b_top20)",
        "backtest_oos_sh": BT_OOS_SH,
        "backtest_oos_dd": BT_OOS_DD,
        "backtest_wf_min": BT_WF_MIN,
        "backtest_wf_std": BT_WF_STD,
        "backtest_oos_weights": BT_OOS_WEIGHTS,
        "daily_records":   [],
        "alerts":          [],
        "last_update":     None,
    }


# ─────────────────────────────────────────────────────────────────────────────
# K208: DAR(2,1) reverse carry PnL (unchanged from K272a)
# ─────────────────────────────────────────────────────────────────────────────

def _ols_fit(X: np.ndarray, y: np.ndarray) -> np.ndarray:
    try:
        coeffs, _, _, _ = np.linalg.lstsq(X, y, rcond=None)
        return coeffs
    except Exception:
        return np.zeros(X.shape[1])


def build_dar_design(fr_arr, spread_z_arr, p, q, idx):
    if idx < max(p, q):
        return None
    row = [1.0]
    for lag in range(1, p + 1):
        row.append(fr_arr[idx - lag])
    for lag in range(1, q + 1):
        row.append(spread_z_arr[idx - lag])
    return np.array(row, dtype=float)


def dar_walk_forward_sym(fr: np.ndarray, spread_z: np.ndarray,
                          p=DAR_P, q=DAR_Q, win=DAR_WIN, refit=DAR_REFIT
                          ) -> Tuple[np.ndarray, np.ndarray]:
    """Run DAR(p,q) walk-forward for one K208 symbol."""
    n         = len(fr)
    pred_fr   = np.full(n, np.nan)
    is_valid  = np.zeros(n, dtype=bool)
    min_lag   = max(p, q)
    coeffs    = None

    for i in range(min_lag + win, n):
        if (i - (min_lag + win)) % refit == 0 or coeffs is None:
            start = i - win
            rows, targets = [], []
            for t in range(start + min_lag, i):
                row = build_dar_design(fr, spread_z, p, q, t)
                if row is None:
                    continue
                rows.append(row)
                targets.append(fr[t])
            if len(rows) < p + q + 10:
                continue
            coeffs = _ols_fit(np.array(rows, dtype=float),
                               np.array(targets, dtype=float))

        if coeffs is not None:
            row = build_dar_design(fr, spread_z, p, q, i - 1)
            if row is not None:
                pred_fr[i]  = float(np.dot(row, coeffs))
                is_valid[i] = True

    return pred_fr, is_valid


def compute_k208_daily_pnl(as_of_date: str) -> Tuple[pd.Series, Dict]:
    """
    Compute K208 panel daily PnL (equal-weight across 10 symbols).
    Gate: enter only when DAR(2,1) predicts positive Bybit-HL spread.
    Returns (daily_pnl, signal_dict). Unchanged from K272a.
    """
    print("  [K208] Computing DAR(2,1) reverse carry signals...")
    sym_pnls: Dict[str, pd.Series] = {}
    signals:  Dict[str, Dict]      = {}

    for sym in K208_SYMS:
        bybit = load_bybit_fr(sym)
        hl    = load_hl_fr(sym)
        if bybit is None or hl is None:
            print(f"    {sym}: missing FR data, skipping")
            continue

        def _to_utc(s):
            if s.index.tz is None:
                return s.tz_localize("UTC")
            return s.tz_convert("UTC")

        bybit = _to_utc(bybit)
        hl_8h = _to_utc(hl).resample("8h", label="right", closed="right").sum(min_count=1)

        df = pd.DataFrame({"bybit_fr": bybit})
        df["hl_fr_8h"] = hl_8h.reindex(df.index)
        df = df.dropna()
        if len(df) < DAR_WIN + 50:
            print(f"    {sym}: insufficient data ({len(df)} events), skipping")
            continue

        df["spread"] = df["bybit_fr"] - df["hl_fr_8h"]
        roll_mean    = df["spread"].rolling(100).mean()
        roll_std     = df["spread"].rolling(100).std(ddof=1)
        df["spread_z"] = (df["spread"] - roll_mean) / (roll_std + 1e-12)
        df = df.dropna(subset=["spread_z"])

        pred_fr, is_valid = dar_walk_forward_sym(
            df["bybit_fr"].values, df["spread_z"].values
        )
        df["pred_bybit_fr"] = pred_fr
        df["is_valid"]      = is_valid
        df["k208_gate"]     = df["is_valid"] & (df["pred_bybit_fr"] > df["hl_fr_8h"])
        df["pnl_event"]     = df["spread"].shift(-1)
        df["k208_pnl"]      = df["pnl_event"] * df["k208_gate"].astype(float)

        df["date"] = df.index.normalize()
        daily = df.groupby("date")["k208_pnl"].sum()
        sym_pnls[sym] = daily

        valid_rows = df[df["is_valid"]]
        if not valid_rows.empty:
            last = valid_rows.iloc[-1]
            signals[sym] = {
                "pred_bybit_fr": round(float(last["pred_bybit_fr"]), 8),
                "hl_fr_8h":      round(float(last["hl_fr_8h"]), 8),
                "spread":        round(float(last["spread"]), 8),
                "gate_open":     bool(last["k208_gate"]),
                "last_ts":       str(last.name),
            }

    if not sym_pnls:
        print("  [K208] WARNING: no symbols produced PnL. Returning zeros.")
        return pd.Series(dtype=float, name="K208"), {}

    panel = pd.DataFrame(sym_pnls)
    daily_pnl = panel.mean(axis=1)
    daily_pnl.name = "K208"
    print(f"  [K208] {len(sym_pnls)} symbols, {len(daily_pnl)} trading days")
    return daily_pnl, signals


# ─────────────────────────────────────────────────────────────────────────────
# K276b: HL 20-Symbol FR L/S Quartile PnL
# ─────────────────────────────────────────────────────────────────────────────

def compute_k276b_daily_pnl() -> Tuple[pd.Series, Dict]:
    """
    K276b: HL 20-symbol cross-sectional carry (K265 upgrade with top20 universe).
    Signal: 14d rolling mean of daily FR per symbol.
    Long bottom quartile (lowest/most-negative FR) → receive from shorts.
    Short top quartile (highest positive FR) → receive from longs.
    Dollar-neutral both sleeves. Cost: 2bp/side maker.

    K276b_top20 outperforms K265:
      Sharpe 17.20 vs 8.42 (same ML window) — +8.78 delta.
      Expected OOS weight: 21.6% (vs K265's ~10% in K272a).

    Returns (daily_pnl, signal_state_dict).
    """
    print("  [K276b] Computing HL 20-symbol FR carry signals (K265 upgrade)...")

    panel = load_k276b_panel()
    if panel.empty or len(panel.columns) < 4:
        print(f"  [K276b] Panel empty or too few symbols ({len(panel.columns)})")
        return pd.Series(dtype=float, name="K276b"), {"error": "panel_empty"}

    # Available columns only (robustness if some symbols not cached)
    available = [s for s in K276B_SYMS if s in panel.columns]
    panel = panel[available].copy()

    # ── Signal: 14d rolling mean (shift +1: use yesterday's signal for today's PnL)
    signal = panel.rolling(window=K276B_FR_WINDOW, min_periods=7).mean().shift(1)

    # ── Dollar-neutral weights: long bottom Q, short top Q
    def _dn_weights(row: pd.Series) -> pd.Series:
        valid = row.dropna()
        n = len(valid)
        if n < 4:
            return pd.Series(0.0, index=row.index)
        n_q    = max(1, int(n * K276B_QUARTILE))
        ranked = valid.rank(ascending=True)
        longs  = ranked[ranked <= n_q].index
        shorts = ranked[ranked > n - n_q].index
        w = pd.Series(0.0, index=row.index)
        if len(longs)  > 0: w[longs]  = +1.0 / len(longs)
        if len(shorts) > 0: w[shorts] = -1.0 / len(shorts)
        return w

    weights = signal.apply(_dn_weights, axis=1)

    # ── PnL: daily FR receive (daily total ≈ hourly mean × 24)
    # Panel is already daily mean of hourly FR. Multiply by 24 for daily total.
    fr_daily = panel * 24.0

    # Lag weights by 1 day (execute at t-1 close, settle at t)
    w_lag    = weights.shift(1).fillna(0.0)
    pnl_raw  = (-w_lag * fr_daily).sum(axis=1)

    # Turnover cost
    turnover = (weights - weights.shift(1).fillna(0.0)).abs().sum(axis=1)
    cost     = turnover * K276B_COST_RATE
    pnl_net  = (pnl_raw - cost).dropna()
    pnl_net.name = "K276b"
    pnl_net.index = pd.to_datetime(pnl_net.index).normalize()

    # ── Current signal state
    last_sig = signal.iloc[-1].dropna()
    last_w   = weights.iloc[-1].dropna()
    n_sym    = len(last_sig)
    n_q      = max(1, int(n_sym * K276B_QUARTILE))
    if n_sym >= 4:
        ranked_last = last_sig.rank(ascending=True)
        long_today  = ranked_last[ranked_last <= n_q].index.tolist()
        short_today = ranked_last[ranked_last > n_sym - n_q].index.tolist()
    else:
        long_today  = []
        short_today = []

    sig_state = {
        "n_symbols_active": int(n_sym),
        "n_symbols_universe": len(K276B_SYMS),
        "long_today":       long_today,
        "short_today":      short_today,
        "panel_last_date":  str(panel.index[-1].date()),
        "pnl_30d_mean":     round(float(pnl_net.tail(30).mean()), 8) if len(pnl_net) >= 10 else None,
        "hl_only_syms":     ["MEME", "PYTH"],
    }
    print(f"  [K276b] {n_sym} symbols active | long={long_today} | short={short_today}")
    print(f"  [K276b] {len(pnl_net)} trading days of PnL computed")
    return pnl_net, sig_state


# ─────────────────────────────────────────────────────────────────────────────
# K198: Ridge ML Allocator Signal (updated curves path for K280)
# ─────────────────────────────────────────────────────────────────────────────

def compute_k198_daily_pnl() -> Tuple[pd.Series, Dict]:
    """
    K198 Ridge ML allocator re-run on backtest curves.
    Loads wave_k280_curves.json (K198/K208/K276b equity curves).
    Falls back to wave_k272_curves.json or wave_k246_curves.json if K280 curves not found.
    """
    print("  [K198] Loading backtest equity curves for Ridge ML allocator...")

    # Try K280 curves first (correct production source for K280 v6.10.2)
    for curves_file in ("wave_k280_curves.json", "wave_k272_curves.json", "wave_k246_curves.json"):
        try:
            with open(BASE / curves_file) as f:
                curves = json.load(f)
            print(f"  [K198] Using {curves_file}")
            break
        except FileNotFoundError:
            continue
    else:
        print("  [K198] No curves JSON found, using equal weight fallback")
        return pd.Series(dtype=float, name="K198"), {"note": "fallback_equal"}

    # Parse equity curves to daily returns
    dates   = pd.to_datetime(curves["dates"])
    eq_k198 = np.array(curves.get("K198", [1.0] * len(dates)), dtype=float)
    eq_k208 = np.array(curves.get("K208", [1.0] * len(dates)), dtype=float)
    # K280 uses K276b; K272 uses K265_win or K265; K246 may have K226
    eq_k276b = np.array(
        curves.get("K276b", curves.get("K276b_top20",
        curves.get("K265_win", curves.get("K265", [1.0] * len(dates))))), dtype=float
    )

    def eq_to_ret(eq):
        r = np.empty_like(eq)
        r[0] = 0.0
        r[1:] = eq[1:] / eq[:-1] - 1.0
        return r

    r_k198  = pd.Series(eq_to_ret(eq_k198),  index=dates)
    r_k208  = pd.Series(eq_to_ret(eq_k208),  index=dates)
    r_k276b = pd.Series(eq_to_ret(eq_k276b), index=dates)

    # Build feature matrix (rolling 30d Sharpe and vol for each component)
    feat_df = pd.DataFrame({
        "k198_sh30":  r_k198.rolling(30).mean()  / (r_k198.rolling(30).std(ddof=1)  + 1e-12)
                      * math.sqrt(TRADING_DAYS),
        "k208_sh30":  r_k208.rolling(30).mean()  / (r_k208.rolling(30).std(ddof=1)  + 1e-12)
                      * math.sqrt(TRADING_DAYS),
        "k276b_sh30": r_k276b.rolling(30).mean() / (r_k276b.rolling(30).std(ddof=1) + 1e-12)
                      * math.sqrt(TRADING_DAYS),
        "k198_vol30":  r_k198.rolling(30).std(ddof=1),
        "k208_vol30":  r_k208.rolling(30).std(ddof=1),
        "k276b_vol30": r_k276b.rolling(30).std(ddof=1),
    }).dropna()

    # Target: K198 next-30d Sharpe
    target = r_k198.rolling(30).mean().shift(-30) / (
        r_k198.rolling(30).std(ddof=1).shift(-30) + 1e-12
    ) * math.sqrt(TRADING_DAYS)

    feat_df["target"] = target
    feat_df = feat_df.dropna()

    if len(feat_df) < 60:
        print(f"  [K198] Insufficient data ({len(feat_df)} rows), using raw K198 curve")
        return r_k198, {"note": "fallback_raw", "n_rows": int(len(feat_df))}

    feats = ["k198_sh30", "k208_sh30", "k276b_sh30", "k198_vol30", "k208_vol30", "k276b_vol30"]
    X = feat_df[feats].values
    y = feat_df["target"].values

    # Walk-forward Ridge
    scaler = StandardScaler()
    ridge  = Ridge(alpha=1.0)
    preds  = np.full(len(feat_df), np.nan)
    n = len(feat_df)

    for start in range(0, n - ML_TRAIN_DAYS - ML_TEST_DAYS, ML_TEST_DAYS):
        tr_end = start + ML_TRAIN_DAYS
        te_end = min(tr_end + ML_TEST_DAYS, n)
        X_tr   = X[start:tr_end]
        y_tr   = y[start:tr_end]
        X_te   = X[tr_end:te_end]
        scaler.fit(X_tr)
        ridge.fit(scaler.transform(X_tr), y_tr)
        preds[tr_end:te_end] = ridge.predict(scaler.transform(X_te))

    feat_df["pred_sh"] = preds
    latest = feat_df.dropna(subset=["pred_sh"]).iloc[-1]
    latest_pred_sh = float(latest["pred_sh"])

    signals = {
        "predicted_sh_30d": round(latest_pred_sh, 4),
        "ridge_alpha":       1.0,
        "n_train_rows":      int(len(feat_df)),
        "features":          feats,
        "curves_source":     curves_file,
    }
    print(f"  [K198] Latest predicted Sharpe: {latest_pred_sh:.4f}")
    return r_k198, signals


# ─────────────────────────────────────────────────────────────────────────────
# Inv-vol Allocator (K280 OOS expected: K198~2.6% / K208~75.8% / K276b~21.6%)
# ─────────────────────────────────────────────────────────────────────────────

def inv_vol_weights(returns: Dict[str, pd.Series], window: int = 60) -> Dict[str, float]:
    """
    Inverse-volatility weights using trailing `window` days.
    No caps applied (K280 natural weights: K198~2.6%, K208~75.8%, K276b~21.6%).
    OOS weights from wave_k280_k272a_k276b.json: K198=0.026, K208=0.758, K276b=0.216.
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
# HLP scaling (unchanged from K272a)
# ─────────────────────────────────────────────────────────────────────────────

def get_hlp_scale_factor(snapshot: Optional[dict]) -> float:
    """
    Return carry weight scale factor from HLP 7d change:
      > -20%:            1.0 (normal)
      -20% to -40%:      0.5 (REDUCE)
      < -40%:            0.0 (HALT)
    """
    if snapshot is None:
        return 1.0
    hlp_alert = snapshot.get("hlp_alert", "OK")
    if hlp_alert == "HALT":
        return 0.0
    elif hlp_alert == "REDUCE":
        return 0.5
    return 1.0


# ─────────────────────────────────────────────────────────────────────────────
# Alert generation (updated for K276b, drift ref = 18.46)
# ─────────────────────────────────────────────────────────────────────────────

def generate_alerts(
    port_pnl:   pd.Series,
    k208_pnl:   pd.Series,
    k276b_pnl:  pd.Series,
    weights:    Dict[str, float],
    snapshot:   Optional[dict],
    date_str:   str,
) -> List[Dict]:
    """Generate K280 alert messages based on rolling metrics."""
    alerts = []

    def _add(level, code, msg):
        alerts.append({"date": date_str, "level": level, "code": code, "message": msg})

    # K208 30d rolling Sharpe
    if len(k208_pnl) >= 10:
        k208_sh_30d = sharpe_d(k208_pnl.tail(30).values)
        if k208_sh_30d < ALERT_K208_30D_SH_MIN:
            _add("ALERT", "K208_LOW_SH",
                 f"K208 30d rolling Sh = {k208_sh_30d:.2f} < threshold {ALERT_K208_30D_SH_MIN}")

    # K276b 30d rolling Sharpe
    if len(k276b_pnl) >= 10:
        k276b_sh_30d = sharpe_d(k276b_pnl.tail(30).values)
        if k276b_sh_30d < ALERT_K276B_30D_SH_MIN:
            _add("ALERT", "K276B_LOW_SH",
                 f"K276b 30d rolling Sh = {k276b_sh_30d:.2f} < threshold {ALERT_K276B_30D_SH_MIN}")

    # Portfolio 30d MaxDD (0.3% ceiling, K280 MaxDD backtest is -0.0013%)
    if len(port_pnl) >= 5:
        eq_30d  = np.cumprod(1 + port_pnl.tail(30).values)
        mdd_30d = max_dd(eq_30d)
        if mdd_30d < -ALERT_PORT_30D_DD_MAX:
            _add("ALERT", "PORT_DD_EXCEED",
                 f"Portfolio 30d MaxDD = {mdd_30d:.5f} exceeds -0.3% threshold "
                 f"(K280 MaxDD backtest: {BT_OOS_DD:.7f})")

    # HLP alert
    if snapshot:
        hlp_alert = snapshot.get("hlp_alert", "OK")
        if hlp_alert == "HALT":
            _add("CRITICAL", "HLP_HALT",
                 "HLP 7d change < -40%. HALT all reverse carry (K208 weight → 0).")
        elif hlp_alert == "REDUCE":
            _add("ALERT", "HLP_REDUCE",
                 "HLP 7d change -20% to -40%. REDUCE K208 carry weight × 0.5.")

    # K276b universe liquidity
    if snapshot and snapshot.get("k276b", {}).get("low_liquidity"):
        low = snapshot["k276b"]["low_liquidity"]
        _add("INFO", "K276B_LOW_LIQ",
             f"K276b low-liquidity symbols (< 70% daily coverage last 7d): {low}")

    # K208 spread compression (from snapshot)
    if snapshot:
        k208 = snapshot.get("k208", {})
        for sym, flag in k208.get("spread_compression", {}).items():
            if flag == "COMPRESSED":
                _add("INFO", f"SPREAD_COMPRESSED_{sym}",
                     f"{sym}: 7d spread mean < 75% of 30d mean (fold 2 risk regime)")

    # Drift score (live Sharpe vs K280 backtest OOS = 18.46)
    if len(port_pnl) >= 30:
        live_sh_30d = sharpe_d(port_pnl.tail(30).values)
        drift_z     = abs(live_sh_30d - BT_OOS_SH) / (BT_WF_STD + 1e-9)
        if drift_z > ALERT_DRIFT_CRITICAL:
            _add("CRITICAL", "DRIFT_SCORE",
                 f"Drift z-score = {drift_z:.2f} > {ALERT_DRIFT_CRITICAL}. "
                 f"Live 30d Sh = {live_sh_30d:.2f} vs K280 backtest OOS {BT_OOS_SH:.2f}")

    return alerts


# ─────────────────────────────────────────────────────────────────────────────
# Rolling metrics
# ─────────────────────────────────────────────────────────────────────────────

def compute_rolling_metrics(port_pnl: pd.Series) -> Dict:
    if port_pnl.empty:
        return {}

    tail7  = port_pnl.tail(7)
    tail30 = port_pnl.tail(30)

    sh_7d   = sharpe_d(tail7.values)  if len(tail7) >= 5  else None
    sh_30d  = sharpe_d(tail30.values) if len(tail30) >= 10 else None
    sh_all  = sharpe_d(port_pnl.values)

    eq7  = np.cumprod(1 + tail7.values)  if len(tail7) >= 2 else None
    eq30 = np.cumprod(1 + tail30.values) if len(tail30) >= 5 else None
    eqall= np.cumprod(1 + port_pnl.values)

    mdd_7d  = max_dd(eq7)  if eq7  is not None else None
    mdd_30d = max_dd(eq30) if eq30 is not None else None
    mdd_all = max_dd(eqall)

    drift_z = None
    if sh_30d is not None:
        drift_z = round(abs(sh_30d - BT_OOS_SH) / (BT_WF_STD + 1e-9), 3)

    return {
        "sh_7d":    round(sh_7d,  4) if sh_7d  is not None else None,
        "sh_30d":   round(sh_30d, 4) if sh_30d is not None else None,
        "sh_all":   round(sh_all, 4),
        "mdd_7d":   round(mdd_7d,  6) if mdd_7d  is not None else None,
        "mdd_30d":  round(mdd_30d, 6) if mdd_30d is not None else None,
        "mdd_all":  round(mdd_all, 6),
        "drift_z":  drift_z,
        "n_days":   len(port_pnl),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Dashboard update
# ─────────────────────────────────────────────────────────────────────────────

def update_dashboard(
    date_str:      str,
    weights:       Dict[str, float],
    port_pnl:      pd.Series,
    component_pnl: Dict[str, pd.Series],
    signals:       Dict[str, Dict],
    alerts:        List[Dict],
    snapshot:      Optional[dict],
    hlp_scale:     float,
):
    """Write updated K280 dashboard JSON."""
    dash    = load_dashboard()
    rolling = compute_rolling_metrics(port_pnl)

    # Component contribution (last 30d Sharpe per component)
    component_contribution = {}
    for comp in COMPONENTS:
        if comp in component_pnl and comp in weights:
            cpnl    = component_pnl[comp].tail(30)
            comp_sh = sharpe_d(cpnl.values) if len(cpnl) >= 5 else None
            component_contribution[comp] = {
                "weight":        weights.get(comp, 0.0),
                "oos_ref_weight": BT_OOS_WEIGHTS.get(comp, None),
                "sh_30d":        round(comp_sh, 4) if comp_sh is not None else None,
            }

    today_record = {
        "date":                   date_str,
        "weights":                weights,
        "hlp_scale_factor":       hlp_scale,
        "rolling":                rolling,
        "component_contribution": component_contribution,
        "signal_k198":            signals.get("K198", {}),
        "signal_k208":            signals.get("K208", {}),
        "signal_k276b":           signals.get("K276b", {}),
        "alerts_today":           alerts,
        "backtest_ref": {
            "oos_sh":        BT_OOS_SH,
            "oos_dd":        BT_OOS_DD,
            "wf_min":        BT_WF_MIN,
            "wf_std":        BT_WF_STD,
            "oos_weights":   BT_OOS_WEIGHTS,
        },
    }

    dash["last_update"]            = datetime.now(timezone.utc).isoformat()
    dash["rolling_metrics"]        = rolling
    dash["latest_weights"]         = weights
    dash["hlp_scale_factor"]       = hlp_scale
    dash["component_contribution"] = component_contribution

    # Append daily record (deduplicate by date)
    records  = dash.get("daily_records", [])
    records  = [r for r in records if r.get("date") != date_str]
    records.append(today_record)
    dash["daily_records"] = sorted(records, key=lambda r: r["date"])

    # Accumulate alerts (keep last 100)
    all_alerts = dash.get("alerts", [])
    all_alerts = [a for a in all_alerts if a.get("date") != date_str]
    all_alerts.extend(alerts)
    dash["alerts"] = all_alerts[-100:]

    # Active alert flags
    dash["active_alert_flags"] = {
        "k208_low_sh":    any(a["code"] == "K208_LOW_SH"    for a in alerts),
        "k276b_low_sh":   any(a["code"] == "K276B_LOW_SH"   for a in alerts),
        "port_dd_exceed": any(a["code"] == "PORT_DD_EXCEED"  for a in alerts),
        "hlp_alert":      snapshot.get("hlp_alert", "OK") if snapshot else "OK",
        "drift_critical": any(a["code"] == "DRIFT_SCORE"    for a in alerts),
        "k276b_low_liq":  any(a["code"] == "K276B_LOW_LIQ"  for a in alerts),
        "spread_compressed_syms": [
            a["code"].replace("SPREAD_COMPRESSED_", "")
            for a in alerts if a["code"].startswith("SPREAD_COMPRESSED_")
        ],
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
# Main daily run
# ─────────────────────────────────────────────────────────────────────────────

def run_daily(date_str: str):
    print(f"\n=== K280 v6.10.2 Daily Paper-Trade Run — {date_str} ===\n")
    t0 = time.time()

    # Load today's live snapshot (optional; fallback to cached data)
    snapshot = load_live_snapshot(date_str)
    if snapshot is None:
        print(f"  WARNING: No live snapshot for {date_str}. "
              "Run k280_live_fetch.py first. Continuing with cached data only.")

    # ── Component PnL ─────────────────────────────────────────────────────────
    k208_pnl,  k208_sig  = compute_k208_daily_pnl(date_str)
    k276b_pnl, k276b_sig = compute_k276b_daily_pnl()
    k198_pnl,  k198_sig  = compute_k198_daily_pnl()

    # ── Date alignment ────────────────────────────────────────────────────────
    pnl_map: Dict[str, pd.Series] = {}
    for name, pnl in [("K198", k198_pnl), ("K208", k208_pnl), ("K276b", k276b_pnl)]:
        if not pnl.empty:
            idx = pd.to_datetime(pnl.index)
            # Strip timezone info so all series are tz-naive before alignment
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

    # ── Inv-vol allocation ────────────────────────────────────────────────────
    print("\nComputing inv-vol weights...")
    weights = inv_vol_weights(pnl_map, window=60)
    # Fill any missing component weights
    for comp in COMPONENTS:
        if comp not in weights:
            weights[comp] = 0.0
    print(f"  Weights (natural K280 inv-vol): {weights}")
    print(f"  Reference OOS weights:          {BT_OOS_WEIGHTS}")

    # ── HLP scaling ───────────────────────────────────────────────────────────
    hlp_scale = get_hlp_scale_factor(snapshot)
    if hlp_scale < 1.0:
        # Scale K208 (reverse carry) by hlp_scale; redistribute excess
        if "K208" in weights:
            excess = weights["K208"] * (1 - hlp_scale)
            weights["K208"] *= hlp_scale
            others = {k: v for k, v in weights.items() if k != "K208" and v > 0}
            tot = sum(others.values())
            if tot > 0:
                for k in others:
                    weights[k] += excess * (weights[k] / tot)
        total = sum(weights.values())
        if total > 0:
            weights = {k: round(v / total, 6) for k, v in weights.items()}
        print(f"  After HLP scale ({hlp_scale}x): {weights}")

    # ── Portfolio PnL ─────────────────────────────────────────────────────────
    port_pnl = pd.Series(0.0, index=aligned.index)
    for comp, w in weights.items():
        if comp in aligned.columns:
            port_pnl += aligned[comp] * w
    port_pnl.name = "K280_v6.10.2"

    today_pnl  = float(port_pnl.iloc[-1]) if not port_pnl.empty else 0.0
    today_date = port_pnl.index[-1].date() if not port_pnl.empty else date_str
    total_eq   = float(np.cumprod(1 + port_pnl.values)[-1]) if not port_pnl.empty else 1.0

    print(f"\n  Today ({today_date}) estimated PnL: {today_pnl:.6f}")
    print(f"  Portfolio equity (cumulative):     {total_eq:.6f}")

    # ── Alerts ────────────────────────────────────────────────────────────────
    alerts = generate_alerts(
        port_pnl, aligned.get("K208", pd.Series()),
        aligned.get("K276b", pd.Series()),
        weights, snapshot, date_str
    )
    if alerts:
        print(f"\n  ALERTS ({len(alerts)}):")
        for a in alerts:
            print(f"    [{a['level']}] {a['code']}: {a['message']}")
    else:
        print("\n  No alerts triggered.")

    # ── Dashboard update ──────────────────────────────────────────────────────
    comp_pnls = {k: aligned[k] for k in COMPONENTS if k in aligned.columns}
    update_dashboard(
        date_str      = date_str,
        weights       = weights,
        port_pnl      = port_pnl,
        component_pnl = comp_pnls,
        signals       = {"K198": k198_sig, "K208": k208_sig, "K276b": k276b_sig},
        alerts        = alerts,
        snapshot      = snapshot,
        hlp_scale     = hlp_scale,
    )

    # ── K429 AUM Tracking (additive — safe if portfolio_aum_manager not present) ─
    # K280 is PRIMARY: updates AUM AND runs PT1 safety valve check.
    # Position sizing at next run will read updated deployed_capital from state.
    aum_metrics = {}
    try:
        import os as _os_k429
        if _os_k429.environ.get("AUM_TRACKING_ENABLED", "true").lower() != "false":
            import sys as _sys_k429
            _sys_k429.path.insert(0, str(BASE / "scripts"))
            from portfolio_aum_manager import (
                update_aum, check_pt1_safety, apply_pt1_withdrawal,
                get_current_metrics, compute_position_size, load_state,
            )
            # Convert fractional PnL to USDC using current deployed capital
            _aum_state  = load_state()
            _k280_alloc = compute_position_size("K280", _aum_state)
            _pnl_usdc   = today_pnl * _k280_alloc   # today_pnl is fractional return
            _aum_state  = update_aum(_pnl_usdc, sleeve_name="K280")

            # PT1 safety valve check (K280 = primary daemon)
            _rolling_7d = _aum_state.get("7d_rolling_return_pct", 0.0)
            if check_pt1_safety(_rolling_7d):
                print(f"\n  [K429][PT1] Firing safety valve (7d={_rolling_7d:+.3f}%)")
                apply_pt1_withdrawal()

            aum_metrics = get_current_metrics()
            print(
                f"\n  [K429] AUM=${aum_metrics.get('current_aum_usdc', 0):,.0f} | "
                f"CumPnL={aum_metrics.get('cumulative_pnl_pct', 0):+.3f}% | "
                f"7d={aum_metrics.get('7d_rolling_return_pct', 0):+.3f}% | "
                f"PT1={'ACTIVE' if aum_metrics.get('pt1_safety_active') else 'OK'}"
            )
    except Exception as _e_aum:
        print(f"  [K429] AUM tracking skipped: {_e_aum}")

    # ── Append to paper trade log ─────────────────────────────────────────────
    log_entry = {
        "date":      str(today_date),
        "run_ts":    datetime.now(timezone.utc).isoformat(),
        "weights":   weights,
        "hlp_scale": hlp_scale,
        "daily_pnl": round(today_pnl, 8),
        "total_eq":  round(total_eq, 8),
        "alerts":    [a["code"] for a in alerts],
        "elapsed_s": round(time.time() - t0, 1),
        # K429 AUM metrics (populated if AUM tracking enabled)
        "k429_aum_usdc":          aum_metrics.get("current_aum_usdc"),
        "k429_cumulative_pnl_pct": aum_metrics.get("cumulative_pnl_pct"),
        "k429_pt1_active":         aum_metrics.get("pt1_safety_active"),
    }
    with open(TRADES_LOG, "a") as f:
        f.write(json.dumps(log_entry) + "\n")

    elapsed = time.time() - t0
    print(f"\n=== Daily run complete in {elapsed:.1f}s ===")
    print(f"  Log: {TRADES_LOG}")
    return log_entry


# ─────────────────────────────────────────────────────────────────────────────
# CLI Entry Point
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="K280 v6.10.2 Daily Paper-Trade Run")
    parser.add_argument("--date", default=None, help="Date YYYY-MM-DD (default: today)")
    args = parser.parse_args()
    date_str = args.date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    run_daily(date_str)


if __name__ == "__main__":
    main()
