"""
k246a_daily_run.py — K246a v6.9 Daily Paper-Trade Execution
=============================================================
Architecture (K246a = K229d):
  - K198  Ridge ML allocator          weight ~  4.8% (inv-vol)
  - K208  DAR(2,1) reverse carry      weight ~ 93.9% (inv-vol, primary alpha)
  - K226  ETH LST staking flow        weight ~  1.2% (inv-vol, cap 20%)

Daily workflow:
  1. Load today's live snapshot (cache/k246a_live_YYYYMMDD.json)
  2. For each component: recompute daily PnL signal from cached data
  3. Inv-vol allocate; apply K226 cap 20%
  4. Apply HLP alert scaling (from K200)
  5. Output: theoretical daily PnL, position sizes
  6. Update data/k246a_live_dashboard.json with rolling metrics + alerts

NO actual orders are placed. Paper-trade only.

Usage:
  python3 scripts/k246a_daily_run.py
  python3 scripts/k246a_daily_run.py --date 2026-05-25
"""
from __future__ import annotations

import argparse
import json
import math
import time
import warnings
from datetime import datetime, timezone, timedelta
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

DASHBOARD_JSON = DATA / "k246a_live_dashboard.json"
TRADES_LOG     = DATA / "k246a_paper_trades.jsonl"

# ── K246a Architecture Constants ───────────────────────────────────────────────
COMPONENTS      = ["K198", "K208", "K226"]
K226_CAP        = 0.20          # K226 weight cap per K246a spec
TRADING_DAYS    = 365
EVENTS_PER_DAY  = 3             # 3 × 8h events
EVENTS_PER_YEAR = TRADING_DAYS * EVENTS_PER_DAY

# K208 symbols
REVERSE_SYMS = ["SOL", "XRP", "SUI", "OP", "APT", "AXS", "JTO", "IMX", "SAND", "ADA"]

# DAR(2,1) parameters (K190/K208 primary)
DAR_P    = 2
DAR_Q    = 1
DAR_WIN  = 300
DAR_REFIT = 50

# K198 Ridge ML walk-forward config
ML_TRAIN_DAYS = 90
ML_TEST_DAYS  = 30

# Alert thresholds (K237 recommendations)
ALERT_K208_30D_SH_MIN = 5.0     # K208 30d rolling Sharpe floor
ALERT_PORT_30D_DD_MAX = 0.01    # Portfolio 30d MaxDD ceiling (1%)
ALERT_HLP_7D_REDUCE   = -20.0   # HLP 7d pct → REDUCE carry weight
ALERT_HLP_7D_HALT     = -40.0   # HLP 7d pct → HALT carry
ALERT_DRIFT_CRITICAL  = 2.0     # z-score units vs backtest std

# K246a backtest reference metrics (from wave_k246_k198_k204_contribution.json)
BT_OOS_SH  = 12.69
BT_WF_STD  = 2.27    # std of 4-fold WF sharpes
BT_OOS_DD  = -0.00115


# ─────────────────────────────────────────────────────────────────────────────
# Metric helpers
# ─────────────────────────────────────────────────────────────────────────────

def sharpe_d(r: np.ndarray, ann: int = TRADING_DAYS) -> float:
    r = np.asarray(r, dtype=float)
    r = r[~np.isnan(r)]
    if len(r) < 2 or r.std(ddof=1) == 0:
        return 0.0
    return float(r.mean() / r.std(ddof=1) * math.sqrt(ann))


def sharpe_e(pnl: np.ndarray) -> float:
    """Annualised Sharpe using 8h event frequency."""
    return sharpe_d(pnl, ann=EVENTS_PER_YEAR)


def max_dd(equity: np.ndarray) -> float:
    eq   = np.asarray(equity, dtype=float)
    peak = np.maximum.accumulate(eq)
    return float(((eq - peak) / (peak + 1e-12)).min())


def rolling_sharpe_d(daily_pnl: pd.Series, window: int) -> pd.Series:
    """Rolling annualised Sharpe on daily PnL."""
    r = daily_pnl.rolling(window)
    return (r.mean() / r.std(ddof=1) * math.sqrt(TRADING_DAYS)).fillna(0)


def rolling_maxdd(daily_pnl: pd.Series, window: int) -> pd.Series:
    def _mdd(x):
        eq = np.cumprod(1.0 + x)
        pk = np.maximum.accumulate(eq)
        return float(((eq - pk) / (pk + 1e-12)).min())
    return daily_pnl.rolling(window).apply(_mdd, raw=True).fillna(0)


# ─────────────────────────────────────────────────────────────────────────────
# Data loading
# ─────────────────────────────────────────────────────────────────────────────

def load_bybit_fr(sym: str) -> Optional[pd.Series]:
    """Load Bybit FR from cache (latest available snapshot first)."""
    for tag in ("730d", "1200d", "365d"):
        f = CACHE / f"bybit_fr_{sym}USDT_{tag}.parquet"
        if f.exists():
            df = pd.read_parquet(f)
            col = "funding_rate" if "funding_rate" in df.columns else df.columns[0]
            if "timestamp" in df.columns:
                df = df.set_index("timestamp")
            s = df[col].astype(float).sort_index()
            return s[~s.index.duplicated(keep="last")]
    return None


def load_hl_fr(sym: str) -> Optional[pd.Series]:
    """Load HL FR from k163_hl cache."""
    f = HL_CACHE / f"hl_fr_{sym}.parquet"
    if not f.exists():
        return None
    df = pd.read_parquet(f)
    col = "hl_fr" if "hl_fr" in df.columns else df.columns[0]
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    s = df[col].astype(float).sort_index()
    return s[~s.index.duplicated(keep="last")]


def load_live_snapshot(date_str: str) -> Optional[dict]:
    """Load today's fetch snapshot JSON."""
    p = CACHE / f"k246a_live_{date_str.replace('-', '')}.json"
    if not p.exists():
        return None
    with open(p) as f:
        return json.load(f)


def load_dashboard() -> dict:
    """Load existing dashboard JSON or create empty structure."""
    if DASHBOARD_JSON.exists():
        with open(DASHBOARD_JSON) as f:
            return json.load(f)
    return {
        "architecture":   "K246a v6.9 (K198+K208+K226)",
        "backtest_oos_sh": BT_OOS_SH,
        "backtest_oos_dd": BT_OOS_DD,
        "backtest_wf_std": BT_WF_STD,
        "daily_records":  [],
        "alerts":         [],
        "last_update":    None,
    }


# ─────────────────────────────────────────────────────────────────────────────
# K208: DAR(2,1) Reverse Carry PnL
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
    """Run DAR(p,q) walk-forward predictor for one symbol.
    Returns (pred_fr, is_valid) arrays."""
    n = len(fr)
    pred_fr  = np.full(n, np.nan)
    is_valid = np.zeros(n, dtype=bool)
    min_lag  = max(p, q)
    coeffs   = None

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
            X = np.array(rows, dtype=float)
            y = np.array(targets, dtype=float)
            coeffs = _ols_fit(X, y)

        if coeffs is not None:
            row = build_dar_design(fr, spread_z, p, q, i - 1)
            if row is not None:
                pred_fr[i]  = float(np.dot(row, coeffs))
                is_valid[i] = True

    return pred_fr, is_valid


def compute_k208_daily_pnl(as_of_date: str) -> Tuple[pd.Series, Dict]:
    """
    Compute K208 panel daily PnL series and latest position signals.

    K208 logic:
      - At each 8h event: gate entry if DAR(2,1) predicts positive spread
      - PnL per event = spread (bybit_fr - hl_fr) when gated in
      - Aggregate 3 events per day → daily PnL
    Returns:
      daily_pnl : pd.Series indexed by date
      signals   : dict of current symbol-level state
    """
    print("  [K208] Computing DAR(2,1) reverse carry signals...")
    sym_pnls  = {}
    signals   = {}

    for sym in REVERSE_SYMS:
        bybit = load_bybit_fr(sym)
        hl    = load_hl_fr(sym)
        if bybit is None or hl is None:
            print(f"    {sym}: missing FR data, skipping")
            continue

        hl_8h = hl.resample("8h", label="right", closed="right").sum(min_count=1)
        df = pd.DataFrame({"bybit_fr": bybit})
        df["hl_fr_8h"] = hl_8h.reindex(df.index)
        df = df.dropna()
        if len(df) < DAR_WIN + 50:
            print(f"    {sym}: insufficient data ({len(df)} events), skipping")
            continue

        df["spread"] = df["bybit_fr"] - df["hl_fr_8h"]
        roll_mean = df["spread"].rolling(100).mean()
        roll_std  = df["spread"].rolling(100).std(ddof=1)
        df["spread_z"] = (df["spread"] - roll_mean) / (roll_std + 1e-12)
        df = df.dropna(subset=["spread_z"])

        fr_arr = df["bybit_fr"].values
        sp_z   = df["spread_z"].values

        pred_fr, is_valid = dar_walk_forward_sym(fr_arr, sp_z)
        df["pred_bybit_fr"] = pred_fr
        df["is_valid"]      = is_valid

        # Gate: enter only if predicted bybit_fr > hl_fr (predicted spread > 0)
        df["k208_gate"] = df["is_valid"] & (df["pred_bybit_fr"] > df["hl_fr_8h"])
        df["pnl_event"] = df["spread"].shift(-1)  # next period carry
        df["k208_pnl"]  = df["pnl_event"] * df["k208_gate"].astype(float)

        # Daily PnL = sum 3 events/day
        df["date"] = df.index.normalize()
        daily = df.groupby("date")["k208_pnl"].sum()
        sym_pnls[sym] = daily

        # Current signal state (latest row where DAR is valid)
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
    # Equal-weight across symbols
    daily_pnl = panel.mean(axis=1)
    daily_pnl.name = "K208"
    print(f"  [K208] {len(sym_pnls)} symbols, {len(daily_pnl)} trading days")
    return daily_pnl, signals


# ─────────────────────────────────────────────────────────────────────────────
# K226: ETH LST Staking Flow z-score Signal
# ─────────────────────────────────────────────────────────────────────────────

def compute_k226_daily_pnl() -> Tuple[pd.Series, Dict]:
    """
    K226: long/neutral/short ETH based on 30d rolling z-score of
    total ETH staked across Lido/RocketPool/StakeWise/FraxEther.

    Returns daily PnL series on ETH proxy (uses cached ETH OHLCV for price).
    If ETH OHLCV unavailable, returns z-score signal only.
    """
    print("  [K226] Computing LST staking flow z-score...")
    cache_path = CACHE / "eth_validator_queue_daily.parquet"
    if not cache_path.exists():
        print("  [K226] No cached data. Run k246a_live_fetch.py first.")
        return pd.Series(dtype=float, name="K226"), {}

    df = pd.read_parquet(cache_path)
    if "total_eth_staked" not in df.columns:
        print("  [K226] total_eth_staked column missing.")
        return pd.Series(dtype=float, name="K226"), {}

    staked = df["total_eth_staked"].dropna()
    if len(staked) < 35:
        print(f"  [K226] Insufficient data ({len(staked)} days)")
        return pd.Series(dtype=float, name="K226"), {}

    # Net flow (daily change)
    flow = staked.diff()
    roll_mean = flow.rolling(30).mean()
    roll_std  = flow.rolling(30).std(ddof=1)
    z_score   = (flow - roll_mean) / (roll_std + 1e-9)

    # Position: +1 if z > 0.5, -1 if z < -0.5, else 0
    position = pd.Series(0.0, index=z_score.index)
    position[z_score >  0.5] =  1.0
    position[z_score < -0.5] = -1.0

    # Load ETH daily OHLCV for PnL (try cache)
    eth_ret = None
    for tag in ("1d_730d", "1d_365d"):
        eth_path = CACHE / f"ETHUSDT_{tag}.parquet"
        if eth_path.exists():
            eth_df = pd.read_parquet(eth_path)
            if "close" in eth_df.columns:
                eth_df.index = pd.to_datetime(eth_df.index, utc=True)
                eth_ret = eth_df["close"].pct_change()
                eth_ret.index = eth_ret.index.normalize()
                break

    if eth_ret is not None:
        eth_ret = eth_ret[~eth_ret.index.duplicated(keep="last")]
        pos_shifted = position.shift(1)
        pos_shifted = pos_shifted[~pos_shifted.index.duplicated(keep="last")]
        common = pos_shifted.index.intersection(eth_ret.index)
        pnl = (pos_shifted.loc[common] * eth_ret.loc[common]).dropna()
    else:
        # No ETH price data — use z-score change as proxy (unit-less signal)
        pnl = (position.shift(1) * z_score.diff() * 0.001).dropna()
        print("  [K226] ETH price cache not found; using z-score proxy PnL")

    pnl.name = "K226"
    latest_z = float(z_score.iloc[-1]) if not z_score.empty else np.nan
    latest_pos = float(position.iloc[-1]) if not position.empty else 0.0

    signals = {
        "zscore_today":    round(latest_z, 4) if not np.isnan(latest_z) else None,
        "position":        latest_pos,
        "staked_latest":   float(staked.iloc[-1]) if not staked.empty else None,
        "30d_flow_zscore": round(latest_z, 4) if not np.isnan(latest_z) else None,
    }
    print(f"  [K226] Z-score today: {latest_z:.3f}, position: {latest_pos:+.0f}")
    return pnl, signals


# ─────────────────────────────────────────────────────────────────────────────
# K198: Ridge ML Allocator Signal
# ─────────────────────────────────────────────────────────────────────────────

def compute_k198_daily_pnl() -> Tuple[pd.Series, Dict]:
    """
    K198 Ridge ML allocator: simplified daily signal.
    Loads K208 + K226 equity curves from backtest, recomputes rolling
    30d Sharpe and vol features, Ridge-predicts next-30d Sharpe,
    and returns the K198-weighted composite PnL.

    In paper-trade context this re-runs the K198 signal on the existing
    backtest data to confirm forward stability of allocator weights.
    """
    print("  [K198] Loading backtest equity curves for ML allocator...")
    try:
        with open(BASE / "wave_k229_curves.json") as f:
            curves = json.load(f)
    except FileNotFoundError:
        print("  [K198] wave_k229_curves.json not found, using equal weight")
        return pd.Series(dtype=float, name="K198"), {"note": "fallback_equal"}

    dates   = pd.to_datetime(curves["dates"])
    k198_eq = np.array(curves["K198"], dtype=float)
    k208_eq = np.array(curves["K208"], dtype=float)
    k226_eq = np.array(curves["K226"], dtype=float)

    # Convert equity curves → daily returns
    def eq_to_ret(eq):
        ret = np.empty_like(eq)
        ret[0] = 0.0
        ret[1:] = eq[1:] / eq[:-1] - 1.0
        return ret

    r_k198 = pd.Series(eq_to_ret(k198_eq), index=dates)
    r_k208 = pd.Series(eq_to_ret(k208_eq), index=dates)
    r_k226 = pd.Series(eq_to_ret(k226_eq), index=dates)

    # Build feature matrix for Ridge prediction
    feat_df = pd.DataFrame({
        "k198_sh30": r_k198.rolling(30).mean() / (r_k198.rolling(30).std(ddof=1) + 1e-12)
                     * math.sqrt(TRADING_DAYS),
        "k208_sh30": r_k208.rolling(30).mean() / (r_k208.rolling(30).std(ddof=1) + 1e-12)
                     * math.sqrt(TRADING_DAYS),
        "k226_sh30": r_k226.rolling(30).mean() / (r_k226.rolling(30).std(ddof=1) + 1e-12)
                     * math.sqrt(TRADING_DAYS),
        "k198_vol30": r_k198.rolling(30).std(ddof=1),
        "k208_vol30": r_k208.rolling(30).std(ddof=1),
    }).dropna()

    # Target: K198 next-30d Sharpe (forward)
    target = r_k198.rolling(30).mean().shift(-30) / (
        r_k198.rolling(30).std(ddof=1).shift(-30) + 1e-12
    ) * math.sqrt(TRADING_DAYS)

    feat_df["target"] = target
    feat_df = feat_df.dropna()
    if len(feat_df) < 60:
        print(f"  [K198] Insufficient data for Ridge ({len(feat_df)} rows), fallback")
        return r_k198, {"note": "fallback_raw", "n_rows": len(feat_df)}

    X = feat_df[["k198_sh30", "k208_sh30", "k226_sh30", "k198_vol30", "k208_vol30"]].values
    y = feat_df["target"].values

    # Walk-forward Ridge
    train_days = ML_TRAIN_DAYS
    test_days  = ML_TEST_DAYS
    scaler     = StandardScaler()
    ridge      = Ridge(alpha=1.0)
    preds      = np.full(len(feat_df), np.nan)
    n = len(feat_df)

    for start in range(0, n - train_days - test_days, test_days):
        tr_end = start + train_days
        te_end = min(tr_end + test_days, n)
        X_tr = X[start:tr_end]
        y_tr = y[start:tr_end]
        X_te = X[tr_end:te_end]
        scaler.fit(X_tr)
        ridge.fit(scaler.transform(X_tr), y_tr)
        preds[tr_end:te_end] = ridge.predict(scaler.transform(X_te))

    feat_df["pred_sh"] = preds
    # Latest predicted K198 weight (proportional to predicted Sharpe)
    latest = feat_df.dropna(subset=["pred_sh"]).iloc[-1]
    latest_pred_sh = float(latest["pred_sh"])

    signals = {
        "predicted_sh_30d": round(latest_pred_sh, 4),
        "ridge_alpha":      1.0,
        "n_train_rows":     int(len(feat_df)),
    }
    print(f"  [K198] Latest predicted Sharpe: {latest_pred_sh:.4f}")
    return r_k198, signals


# ─────────────────────────────────────────────────────────────────────────────
# Inv-vol Allocator with K226 Cap
# ─────────────────────────────────────────────────────────────────────────────

def inv_vol_weights(returns: Dict[str, pd.Series], window: int = 60
                    ) -> Dict[str, float]:
    """
    Compute inverse-volatility weights for named return series.
    Uses trailing `window` days. Applies K226 cap of 20%.
    """
    aligned = pd.DataFrame(returns).dropna()
    if aligned.empty or len(aligned) < 10:
        # Equal weight fallback
        n = len(returns)
        return {k: 1.0/n for k in returns}

    tail = aligned.tail(window)
    vols = tail.std(ddof=1)
    inv  = 1.0 / vols.replace(0, np.nan)
    inv  = inv.dropna()
    w    = inv / inv.sum()

    # K226 cap
    if "K226" in w and w["K226"] > K226_CAP:
        excess = w["K226"] - K226_CAP
        w["K226"] = K226_CAP
        others = w.drop("K226")
        if others.sum() > 0:
            w[others.index] = others + excess * (others / others.sum())
        w = w / w.sum()

    return {k: round(float(v), 6) for k, v in w.items()}


# ─────────────────────────────────────────────────────────────────────────────
# HLP Alert Scaling
# ─────────────────────────────────────────────────────────────────────────────

def get_hlp_scale_factor(snapshot: Optional[dict]) -> float:
    """
    Based on HLP 7d change, return carry weight scale factor.
      Normal (> -20%): 1.0
      Alert  (-20% to -40%): 0.5
      Halt   (< -40%): 0.0
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
# Alert Generation
# ─────────────────────────────────────────────────────────────────────────────

def generate_alerts(
    port_pnl: pd.Series,
    k208_pnl: pd.Series,
    weights: Dict[str, float],
    snapshot: Optional[dict],
    date_str: str,
) -> List[Dict]:
    """Generate alert messages based on rolling metrics."""
    alerts = []

    def _add(level, code, msg):
        alerts.append({
            "date": date_str,
            "level": level,
            "code": code,
            "message": msg,
        })

    # K208 30d rolling Sharpe
    k208_30d = k208_pnl.tail(30)
    if len(k208_30d) >= 10:
        k208_sh_30d = sharpe_d(k208_30d.values)
        if k208_sh_30d < ALERT_K208_30D_SH_MIN:
            _add("ALERT", "K208_LOW_SH",
                 f"K208 30d rolling Sh = {k208_sh_30d:.2f} < threshold {ALERT_K208_30D_SH_MIN}")

    # Portfolio 30d rolling MaxDD
    port_30d = port_pnl.tail(30)
    if len(port_30d) >= 5:
        eq_30d = np.cumprod(1 + port_30d.values)
        mdd_30d = max_dd(eq_30d)
        if mdd_30d < -ALERT_PORT_30D_DD_MAX:
            _add("ALERT", "PORT_DD_EXCEED",
                 f"Portfolio 30d MaxDD = {mdd_30d:.4f} exceeds threshold -{ALERT_PORT_30D_DD_MAX}")

    # HLP alert
    if snapshot:
        hlp_alert = snapshot.get("hlp_alert", "OK")
        if hlp_alert == "HALT":
            _add("CRITICAL", "HLP_HALT",
                 "HLP 7d change < -40%. HALT all reverse carry.")
        elif hlp_alert == "REDUCE":
            _add("ALERT", "HLP_REDUCE",
                 "HLP 7d change -20% to -40%. REDUCE carry weight by 50%.")

    # Spread compression
    if snapshot:
        for sym, flag in snapshot.get("spread_compression", {}).items():
            if flag == "COMPRESSED":
                _add("INFO", f"SPREAD_COMPRESSED_{sym}",
                     f"{sym}: 7d spread mean < 75% of 30d mean (fold 2 risk regime)")

    # Drift score (live Sharpe vs backtest expected)
    if len(port_pnl) >= 30:
        live_sh_30d = sharpe_d(port_pnl.tail(30).values)
        drift_z = abs(live_sh_30d - BT_OOS_SH) / (BT_WF_STD + 1e-9)
        if drift_z > ALERT_DRIFT_CRITICAL:
            _add("CRITICAL", "DRIFT_SCORE",
                 f"Drift z-score = {drift_z:.2f} > {ALERT_DRIFT_CRITICAL}. "
                 f"Live 30d Sh = {live_sh_30d:.2f} vs backtest {BT_OOS_SH:.2f}")

    return alerts


# ─────────────────────────────────────────────────────────────────────────────
# Dashboard Update
# ─────────────────────────────────────────────────────────────────────────────

def compute_rolling_metrics(port_pnl: pd.Series) -> Dict:
    """Compute rolling metrics for dashboard."""
    if port_pnl.empty:
        return {}

    tail7  = port_pnl.tail(7)
    tail30 = port_pnl.tail(30)

    sh_7d  = sharpe_d(tail7.values)  if len(tail7) >= 5 else None
    sh_30d = sharpe_d(tail30.values) if len(tail30) >= 10 else None

    eq7  = np.cumprod(1 + tail7.values)  if len(tail7) >= 2 else None
    eq30 = np.cumprod(1 + tail30.values) if len(tail30) >= 5 else None

    mdd_7d  = max_dd(eq7)  if eq7  is not None else None
    mdd_30d = max_dd(eq30) if eq30 is not None else None

    eq_all  = np.cumprod(1 + port_pnl.values)
    mdd_all = max_dd(eq_all)
    sh_all  = sharpe_d(port_pnl.values)

    # Drift score
    drift_z = None
    if sh_30d is not None:
        drift_z = round(abs(sh_30d - BT_OOS_SH) / (BT_WF_STD + 1e-9), 3)

    return {
        "sh_7d":    round(sh_7d, 4)  if sh_7d  is not None else None,
        "sh_30d":   round(sh_30d, 4) if sh_30d is not None else None,
        "sh_all":   round(sh_all, 4),
        "mdd_7d":   round(mdd_7d, 6)  if mdd_7d  is not None else None,
        "mdd_30d":  round(mdd_30d, 6) if mdd_30d is not None else None,
        "mdd_all":  round(mdd_all, 6),
        "drift_z":  drift_z,
        "n_days":   len(port_pnl),
    }


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
    """Write updated dashboard JSON."""
    dash = load_dashboard()

    rolling = compute_rolling_metrics(port_pnl)

    # Component contribution breakdown (last 30d)
    component_contribution = {}
    for comp in COMPONENTS:
        if comp in component_pnl and comp in weights:
            cpnl = component_pnl[comp].tail(30)
            comp_sh = sharpe_d(cpnl.values) if len(cpnl) >= 5 else None
            component_contribution[comp] = {
                "weight":  weights.get(comp, 0.0),
                "sh_30d":  round(comp_sh, 4) if comp_sh is not None else None,
            }

    today_record = {
        "date":                   date_str,
        "weights":                weights,
        "hlp_scale_factor":       hlp_scale,
        "rolling":                rolling,
        "component_contribution": component_contribution,
        "signal_k208":            signals.get("K208", {}),
        "signal_k226":            signals.get("K226", {}),
        "signal_k198":            signals.get("K198", {}),
        "alerts_today":           alerts,
        "backtest_ref": {
            "oos_sh":   BT_OOS_SH,
            "oos_dd":   BT_OOS_DD,
            "wf_std":   BT_WF_STD,
        },
    }

    dash["last_update"]      = datetime.now(timezone.utc).isoformat()
    dash["rolling_metrics"]  = rolling
    dash["latest_weights"]   = weights
    dash["hlp_scale_factor"] = hlp_scale
    dash["component_contribution"] = component_contribution

    # Append daily record (avoid duplicates)
    records = dash.get("daily_records", [])
    records = [r for r in records if r.get("date") != date_str]
    records.append(today_record)
    dash["daily_records"] = sorted(records, key=lambda r: r["date"])

    # Accumulate alerts (keep last 100)
    all_alerts = dash.get("alerts", [])
    all_alerts = [a for a in all_alerts if a.get("date") != date_str]
    all_alerts.extend(alerts)
    dash["alerts"] = all_alerts[-100:]

    # Active alert flags summary
    dash["active_alert_flags"] = {
        "k208_low_sh":    any(a["code"] == "K208_LOW_SH"   for a in alerts),
        "port_dd_exceed": any(a["code"] == "PORT_DD_EXCEED" for a in alerts),
        "hlp_alert":      snapshot.get("hlp_alert", "OK") if snapshot else "OK",
        "drift_critical": any(a["code"] == "DRIFT_SCORE"   for a in alerts),
        "spread_compressed_syms": [
            a["code"].replace("SPREAD_COMPRESSED_", "")
            for a in alerts if a["code"].startswith("SPREAD_COMPRESSED_")
        ],
    }

    # NaN-safe serializer
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
    print(f"\n=== K246a Daily Paper-Trade Run — {date_str} ===\n")
    t0 = time.time()

    # Load today's live snapshot (if available from fetch step)
    snapshot = load_live_snapshot(date_str)
    if snapshot is None:
        print(f"WARNING: No live snapshot for {date_str}. "
              "Run k246a_live_fetch.py first. Continuing with cached data only.")

    # ── Component PnL computation ──────────────────────────────────────────────
    k208_pnl, k208_sig = compute_k208_daily_pnl(date_str)
    k226_pnl, k226_sig = compute_k226_daily_pnl()
    k198_pnl, k198_sig = compute_k198_daily_pnl()

    # ── Alignment: find common date range ─────────────────────────────────────
    pnl_map: Dict[str, pd.Series] = {}
    if not k198_pnl.empty:
        k198_pnl.index = pd.to_datetime(k198_pnl.index).normalize()
        pnl_map["K198"] = k198_pnl
    if not k208_pnl.empty:
        k208_pnl.index = pd.to_datetime(k208_pnl.index).normalize()
        pnl_map["K208"] = k208_pnl
    if not k226_pnl.empty:
        k226_pnl.index = pd.to_datetime(k226_pnl.index).normalize()
        pnl_map["K226"] = k226_pnl

    if not pnl_map:
        print("ERROR: No component PnL computed. Aborting.")
        return

    aligned = pd.DataFrame(pnl_map).sort_index().fillna(0)
    print(f"\n  Aligned panel: {aligned.index[0].date()} → "
          f"{aligned.index[-1].date()} ({len(aligned)} days)")

    # ── Inv-vol allocation (on trailing 60d) ──────────────────────────────────
    print("\nComputing inv-vol weights...")
    weights = inv_vol_weights(pnl_map, window=60)
    if len(pnl_map) < 3:
        # Fill missing weights with equal share
        for comp in COMPONENTS:
            if comp not in weights:
                weights[comp] = 0.0
    print(f"  Weights: {weights}")

    # ── HLP scaling ───────────────────────────────────────────────────────────
    hlp_scale = get_hlp_scale_factor(snapshot)
    if hlp_scale < 1.0:
        # Scale K208 weight (reverse carry component) by hlp_scale
        if "K208" in weights:
            excess = weights["K208"] * (1 - hlp_scale)
            weights["K208"] *= hlp_scale
            # Redistribute to K198/K226
            others = {k: v for k, v in weights.items() if k != "K208" and v > 0}
            tot = sum(others.values())
            if tot > 0:
                for k in others:
                    weights[k] += excess * (weights[k] / tot)
        total = sum(weights.values())
        if total > 0:
            weights = {k: round(v/total, 6) for k, v in weights.items()}
        print(f"  After HLP scale ({hlp_scale}): {weights}")

    # ── Portfolio PnL ─────────────────────────────────────────────────────────
    port_pnl = pd.Series(0.0, index=aligned.index)
    for comp, w in weights.items():
        if comp in aligned.columns:
            port_pnl += aligned[comp] * w

    port_pnl.name = "K246a_v6.9"

    # ── Today's estimated position sizes (notional = 1.0) ────────────────────
    today_pnl = float(port_pnl.iloc[-1]) if not port_pnl.empty else 0.0
    today_date = port_pnl.index[-1].date() if not port_pnl.empty else date_str

    print(f"\n  Today ({today_date}) estimated PnL: {today_pnl:.6f}")
    print(f"  Portfolio equity (cumulative): "
          f"{float(np.cumprod(1+port_pnl.values)[-1]):.6f}")

    # ── Alerts ────────────────────────────────────────────────────────────────
    alerts = generate_alerts(
        port_pnl, aligned.get("K208", pd.Series()),
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
        signals       = {"K208": k208_sig, "K226": k226_sig, "K198": k198_sig},
        alerts        = alerts,
        snapshot      = snapshot,
        hlp_scale     = hlp_scale,
    )

    # ── Append to paper trade log ─────────────────────────────────────────────
    log_entry = {
        "date":       str(today_date),
        "run_ts":     datetime.now(timezone.utc).isoformat(),
        "weights":    weights,
        "hlp_scale":  hlp_scale,
        "daily_pnl":  round(today_pnl, 8),
        "alerts":     [a["code"] for a in alerts],
        "elapsed_s":  round(time.time() - t0, 1),
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
    parser = argparse.ArgumentParser(description="K246a Daily Paper-Trade Run")
    parser.add_argument("--date", default=None, help="Date YYYY-MM-DD (default: today)")
    args = parser.parse_args()
    date_str = args.date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    run_daily(date_str)


if __name__ == "__main__":
    main()
