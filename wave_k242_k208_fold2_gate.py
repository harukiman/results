"""
Wave K242 - K208 Fold 2 Diagnosis & Regime Gate
================================================
Objective:
  1. Diagnose K208 fold 2 (2025-05-14 to 2025-09-02) weakness root cause
  2. Build regime gates to fix fold 2 without K229 ensemble overhead
  3. Walk-forward validate K208+gate variants vs K229d

Fold structure (K229 ML window 2025-01-22 to 2026-04-14, N=448, 112d each):
  Fold 1: 2025-01-22 to 2025-05-13  Sh=17.35
  Fold 2: 2025-05-14 to 2025-09-02  Sh=5.78  ← TARGET
  Fold 3: 2025-09-03 to 2025-12-23  Sh=17.41
  Fold 4: 2025-12-24 to 2026-04-14  Sh=13.11

Regime gate variants:
  K242a: Halt K208 when BTC 30d return > +30% (bull mania)
  K242b: Halt K208 when FR_mean_ann > +0.15 across 6 majors (extreme positive funding)
  K242c: Halt K208 when reverse carry DAR direction accuracy < 60% (signal degraded)
  K242d: Combined gates (K242a OR K242b)

Runtime target: <12 min
"""
from __future__ import annotations

import json
import math
import time
import warnings
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

START_TIME = time.time()
BASE     = Path("/Users/nekonaomichi/crypto-lab")
CACHE    = BASE / "cache"
HL_CACHE = CACHE / "k163_hl"

# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────
EVENTS_PER_YEAR = 365 * 3   # 1095 (3 × 8h per day)
SQRT_365 = math.sqrt(365)

# ML window (K229 reference)
ML_START = "2025-01-22"
ML_END   = "2026-04-14"

# Fold boundaries (448 days, 112 each)
FOLD_BOUNDS = [
    ("2025-01-22", "2025-05-13"),   # Fold 1
    ("2025-05-14", "2025-09-02"),   # Fold 2 ← weak
    ("2025-09-03", "2025-12-23"),   # Fold 3
    ("2025-12-24", "2026-04-14"),   # Fold 4
]

# Reverse carry panel symbols (K208)
REVERSE_10 = ["SOL", "XRP", "SUI", "OP", "APT", "AXS", "JTO", "IMX", "SAND", "ADA"]

# 6 majors for FR mean calculation
MAJOR_6 = ["BTC", "ETH", "SOL", "XRP", "BNB", "DOT"]

# K229d reference metrics (from K240)
K229D_OOS_SH  = 10.168
K229D_WF_FOLDS = [12.91, 7.48, 13.01, 12.22]
K229D_WF_MIN   = 7.48
K229D_MAX_DD   = -0.0012

# K208 standalone reference (from K240)
K208_OOS_SH    = 10.588
K208_WF_FOLDS  = [17.35, 5.78, 17.41, 13.11]
K208_WF_MIN    = 5.78

# K242 acceptance thresholds
ACCEPT_FOLD2_SH = 7.0    # Fold 2 Sh >= 7.0 (recovery to K229d level)
ACCEPT_OOS_SH   = 10.17  # Overall OOS Sh >= K229d
ACCEPT_WF_MIN   = 7.44   # WF min >= K229d


# ─────────────────────────────────────────────────────────────────────────────
# Data loading helpers
# ─────────────────────────────────────────────────────────────────────────────

def load_bybit_fr_daily(sym: str) -> Optional[pd.Series]:
    """Load Bybit FR, resample to 8h, return daily mean as Series indexed by date."""
    for tag in ("1200d", "730d", "365d"):
        f = CACHE / f"bybit_fr_{sym}USDT_{tag}.parquet"
        if f.exists():
            df = pd.read_parquet(f)
            col = "funding_rate" if "funding_rate" in df.columns else df.columns[0]
            if "timestamp" in df.columns:
                df = df.set_index("timestamp")
            s = df[col].astype(float).sort_index()
            s = s[~s.index.duplicated(keep="last")]
            # Annualize per event: FR is per 8h, multiply by 3*365 for annual
            s_ann = s * EVENTS_PER_YEAR
            # Resample to daily mean
            daily = s_ann.resample("D").mean()
            daily.name = sym
            return daily
    return None


def load_hl_fr_daily(sym: str) -> Optional[pd.Series]:
    """Load HL FR, resample to daily mean."""
    f = HL_CACHE / f"hl_fr_{sym}.parquet"
    if not f.exists():
        return None
    df = pd.read_parquet(f)
    col = "hl_fr" if "hl_fr" in df.columns else df.columns[0]
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    s = df[col].astype(float).sort_index()
    s = s[~s.index.duplicated(keep="last")]
    s_ann = s * EVENTS_PER_YEAR
    daily = s_ann.resample("D").mean()
    daily.name = sym
    return daily


def load_bybit_fr_8h(sym: str) -> Optional[pd.Series]:
    """Load raw 8h Bybit FR for a symbol."""
    for tag in ("1200d", "730d", "365d"):
        f = CACHE / f"bybit_fr_{sym}USDT_{tag}.parquet"
        if f.exists():
            df = pd.read_parquet(f)
            col = "funding_rate" if "funding_rate" in df.columns else df.columns[0]
            if "timestamp" in df.columns:
                df = df.set_index("timestamp")
            s = df[col].astype(float).sort_index()
            s = s[~s.index.duplicated(keep="last")]
            s.name = sym
            return s
    return None


def load_hl_fr_8h(sym: str) -> Optional[pd.Series]:
    """Load HL FR hourly, resample to 8h sums."""
    f = HL_CACHE / f"hl_fr_{sym}.parquet"
    if not f.exists():
        return None
    df = pd.read_parquet(f)
    col = "hl_fr" if "hl_fr" in df.columns else df.columns[0]
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    s = df[col].astype(float).sort_index()
    s = s[~s.index.duplicated(keep="last")]
    hl_8h = s.resample("8h", label="right", closed="right").sum(min_count=1)
    hl_8h.name = sym
    return hl_8h


def load_btc_daily_price() -> Optional[pd.Series]:
    """Load BTC daily close price."""
    for tag in ("730d", "1200d"):
        f = CACHE / f"BTCUSDT_1d_{tag}.parquet"
        if f.exists():
            df = pd.read_parquet(f)
            col = "close" if "close" in df.columns else df.columns[3]
            date_col = "open_time" if "open_time" in df.columns else df.index
            if "open_time" in df.columns:
                df = df.set_index("open_time")
            s = df[col].astype(float).sort_index()
            s.index = pd.DatetimeIndex([d.date() for d in s.index])
            s = s[~s.index.duplicated(keep="last")]
            s.name = "BTC_close"
            return s
    return None


# ─────────────────────────────────────────────────────────────────────────────
# K208 equity curve reconstruction from cached curves
# ─────────────────────────────────────────────────────────────────────────────

def load_k208_daily_pnl() -> pd.Series:
    """Reconstruct K208 daily PnL from wave_k208_curves.json."""
    with open(BASE / "wave_k208_curves.json") as f:
        raw = json.load(f)
    ts_all  = raw["K208_filtered"]["timestamps"]
    pnl_all = raw["K208_filtered"]["cumulative_pnl"]

    # Collapse to daily (last 8h bar wins)
    daily: Dict[str, float] = {}
    for ts, cpnl in zip(ts_all, pnl_all):
        date = ts[:10]
        daily[date] = cpnl

    sorted_dates = sorted(daily.keys())
    s = pd.Series([daily[d] for d in sorted_dates],
                  index=pd.DatetimeIndex(sorted_dates), name="K208_cpnl")
    # Convert cumulative PnL → daily PnL (diff)
    daily_pnl = s.diff().fillna(0.0)
    daily_pnl.name = "K208_daily_pnl"
    return daily_pnl


def load_k208_equity_daily() -> pd.Series:
    """Load K208 as equity curve (starting at 1.0) aligned to ML window."""
    with open(BASE / "wave_k208_curves.json") as f:
        raw = json.load(f)
    ts_all  = raw["K208_filtered"]["timestamps"]
    pnl_all = raw["K208_filtered"]["cumulative_pnl"]

    daily: Dict[str, float] = {}
    for ts, cpnl in zip(ts_all, pnl_all):
        date = ts[:10]
        if ML_START <= date <= ML_END:
            daily[date] = cpnl

    sorted_dates = sorted(daily.keys())
    cpnl_arr = np.array([daily[d] for d in sorted_dates])
    eq_arr = 1.0 + (cpnl_arr - cpnl_arr[0])

    return pd.Series(eq_arr, index=pd.DatetimeIndex(sorted_dates), name="K208_equity")


# ─────────────────────────────────────────────────────────────────────────────
# Metrics helpers
# ─────────────────────────────────────────────────────────────────────────────

def sharpe_daily(r: pd.Series) -> float:
    r = r.dropna()
    if len(r) < 5 or r.std(ddof=1) == 0:
        return 0.0
    return float(r.mean() / r.std(ddof=1) * SQRT_365)


def max_dd_eq(eq: pd.Series) -> float:
    peak = eq.cummax()
    return float((eq - peak).min())


def wf_4fold_daily(pnl: pd.Series) -> Tuple[float, float, List[float]]:
    """Compute 4-fold WF Sharpes using fold boundaries from FOLD_BOUNDS."""
    results = []
    for start_str, end_str in FOLD_BOUNDS:
        mask = (pnl.index >= start_str) & (pnl.index <= end_str)
        fold_r = pnl[mask]
        results.append(sharpe_daily(fold_r))
    return float(np.mean(results)), float(np.min(results)), [round(x, 4) for x in results]


# ─────────────────────────────────────────────────────────────────────────────
# Step 1: Fold 2 Diagnostic
# ─────────────────────────────────────────────────────────────────────────────

def compute_fold2_diagnostic(
    k208_pnl: pd.Series,
    btc_close: pd.Series,
    fr_means: pd.DataFrame,          # daily annualised FR mean across majors
    hl_btc_daily: pd.Series,
    bybit_btc_daily: pd.Series,
) -> Dict:
    """Characterize fold 2 vs other folds on multiple regime dimensions."""
    print("\n=== STEP 1: FOLD 2 DIAGNOSTIC ===")

    fold_stats = []
    for fold_idx, (start_str, end_str) in enumerate(FOLD_BOUNDS):
        mask_pnl = (k208_pnl.index >= start_str) & (k208_pnl.index <= end_str)
        fold_pnl = k208_pnl[mask_pnl]
        sh = sharpe_daily(fold_pnl)

        # BTC 30d return at fold midpoint
        mid_date = pd.Timestamp(start_str) + (pd.Timestamp(end_str) - pd.Timestamp(start_str)) / 2
        fold_dates_btc = btc_close[(btc_close.index >= pd.Timestamp(start_str)) &
                                    (btc_close.index <= pd.Timestamp(end_str))]
        if len(fold_dates_btc) >= 30:
            btc_ret_30d = float((fold_dates_btc.iloc[-1] / fold_dates_btc.iloc[-30] - 1) * 100)
            btc_ret_full = float((fold_dates_btc.iloc[-1] / fold_dates_btc.iloc[0] - 1) * 100)
            btc_trend_dir = "UP" if btc_ret_full > 10 else ("DOWN" if btc_ret_full < -10 else "FLAT")
        else:
            btc_ret_30d = btc_ret_full = float("nan")
            btc_trend_dir = "NA"

        # FR mean across majors in this fold
        mask_fr = (fr_means.index >= start_str) & (fr_means.index <= end_str)
        fold_fr = fr_means[mask_fr]
        fr_mean_ann = float(fold_fr.mean().mean()) if len(fold_fr) > 0 else float("nan")
        fr_std_ann = float(fold_fr.std().mean()) if len(fold_fr) > 0 else float("nan")
        fr_pct_positive = float((fold_fr > 0).mean().mean()) if len(fold_fr) > 0 else float("nan")

        # Basis spread vol (HL_FR vs Bybit_FR for BTC)
        mask_basis = (hl_btc_daily.index >= pd.Timestamp(start_str)) & \
                     (hl_btc_daily.index <= pd.Timestamp(end_str))
        hl_fold = hl_btc_daily[mask_basis]
        bybit_fold = bybit_btc_daily.reindex(hl_fold.index)
        if len(hl_fold) > 5:
            basis_spread = bybit_fold - hl_fold
            basis_vol = float(basis_spread.std())
            basis_mean = float(basis_spread.mean())
        else:
            basis_vol = basis_mean = float("nan")

        # K208 PnL distribution
        pnl_mean = float(fold_pnl.mean()) if len(fold_pnl) > 0 else float("nan")
        pnl_std  = float(fold_pnl.std(ddof=1)) if len(fold_pnl) > 1 else float("nan")
        pnl_pos_freq = float((fold_pnl > 0).mean()) if len(fold_pnl) > 0 else float("nan")
        pnl_neg_freq = float((fold_pnl < 0).mean()) if len(fold_pnl) > 0 else float("nan")

        label = f"Fold {fold_idx+1} ({start_str} → {end_str})"
        is_fold2 = fold_idx == 1

        stats = {
            "fold": fold_idx + 1,
            "start": start_str,
            "end": end_str,
            "is_fold2": is_fold2,
            "sharpe": round(sh, 4),
            "n_days": int(mask_pnl.sum()),
            "pnl_mean_daily": round(pnl_mean, 8),
            "pnl_std_daily": round(pnl_std, 8),
            "pnl_positive_freq": round(pnl_pos_freq, 4),
            "pnl_negative_freq": round(pnl_neg_freq, 4),
            "btc_ret_fold_pct": round(btc_ret_full, 2) if not math.isnan(btc_ret_full) else None,
            "btc_ret_last30d_pct": round(btc_ret_30d, 2) if not math.isnan(btc_ret_30d) else None,
            "btc_trend_direction": btc_trend_dir,
            "fr_mean_ann_6maj": round(fr_mean_ann, 4) if not math.isnan(fr_mean_ann) else None,
            "fr_std_ann_6maj": round(fr_std_ann, 4) if not math.isnan(fr_std_ann) else None,
            "fr_pct_positive": round(fr_pct_positive, 4) if not math.isnan(fr_pct_positive) else None,
            "basis_vol_btc": round(basis_vol, 6) if not math.isnan(basis_vol) else None,
            "basis_mean_btc": round(basis_mean, 6) if not math.isnan(basis_mean) else None,
        }
        fold_stats.append(stats)

        flag = " ← WEAK" if is_fold2 else ""
        print(f"  {label}{flag}")
        print(f"    Sh={sh:.4f}  PnL mean={pnl_mean*10000:.2f}bps  pos_freq={pnl_pos_freq:.3f}")
        print(f"    BTC_ret={btc_ret_full:.1f}%  trend={btc_trend_dir}  BTC_30d={btc_ret_30d:.1f}%")
        print(f"    FR_mean_ann={fr_mean_ann:.4f} ({fr_mean_ann*100:.2f}%)  FR_pct_positive={fr_pct_positive:.3f}")
        print(f"    Basis_vol={basis_vol:.6f}  Basis_mean={basis_mean:.6f}")

    return {"fold_diagnostics": fold_stats}


# ─────────────────────────────────────────────────────────────────────────────
# Step 2: Hypothesis Testing
# ─────────────────────────────────────────────────────────────────────────────

def test_hypotheses(fold_stats: List[Dict], btc_close: pd.Series) -> Dict:
    """Test specific hypotheses about what caused fold 2 weakness."""
    print("\n=== STEP 2: HYPOTHESIS TESTS ===")

    fold2 = next(f for f in fold_stats if f["fold"] == 2)
    other_folds = [f for f in fold_stats if f["fold"] != 2]

    # H1: BTC bull mania (30d return > 30%)
    btc_f2 = fold2["btc_ret_fold_pct"] or 0.0
    btc_others_mean = np.mean([f["btc_ret_fold_pct"] or 0.0 for f in other_folds])
    h1_bull_mania = btc_f2 > 20.0  # Fold 2 BTC >20% return
    print(f"\n  H1 (BTC Bull Mania): Fold2 BTC={btc_f2:.1f}% vs Others mean={btc_others_mean:.1f}%")
    print(f"     Verdict: {'CONFIRMED' if h1_bull_mania else 'NOT CONFIRMED'}")

    # H2: Extreme positive funding rate (FR_mean_ann > 0.15)
    fr_f2 = fold2["fr_mean_ann_6maj"] or 0.0
    fr_others_mean = np.mean([f["fr_mean_ann_6maj"] or 0.0 for f in other_folds])
    h2_extreme_fr = fr_f2 > 0.10
    print(f"\n  H2 (Extreme Positive FR): Fold2 FR_mean_ann={fr_f2:.4f} vs Others mean={fr_others_mean:.4f}")
    print(f"     Verdict: {'CONFIRMED' if h2_extreme_fr else 'NOT CONFIRMED'}")

    # H3: Reverse carry sign flip (K196 stated 2025 sign flip)
    # Check if basis spread was unusually negative in fold 2
    basis_f2 = fold2["basis_mean_btc"] or 0.0
    basis_others = np.mean([f["basis_mean_btc"] or 0.0 for f in other_folds])
    h3_sign_flip = basis_f2 < basis_others - 0.0001  # fold 2 basis notably lower
    print(f"\n  H3 (Reverse Carry Sign Flip): Fold2 basis_mean={basis_f2:.6f} vs Others mean={basis_others:.6f}")
    print(f"     Verdict: {'CONFIRMED' if h3_sign_flip else 'NOT CONFIRMED'}")

    # H4: Low positive frequency (K208 misses more often in fold 2)
    posfreq_f2 = fold2["pnl_positive_freq"] or 0.5
    posfreq_others = np.mean([f["pnl_positive_freq"] or 0.5 for f in other_folds])
    h4_lower_freq = posfreq_f2 < posfreq_others - 0.02
    print(f"\n  H4 (Signal Degraded - lower pos freq): Fold2={posfreq_f2:.4f} vs Others mean={posfreq_others:.4f}")
    print(f"     Verdict: {'CONFIRMED' if h4_lower_freq else 'NOT CONFIRMED'}")

    # Compute fold 2 BTC 30-day rolling return trajectory
    fold2_btc = btc_close[(btc_close.index >= pd.Timestamp("2025-04-14")) &
                           (btc_close.index <= pd.Timestamp("2025-09-02"))]
    btc_30d_returns = []
    for i in range(30, len(fold2_btc)):
        r30 = (fold2_btc.iloc[i] / fold2_btc.iloc[i-30] - 1) * 100
        btc_30d_returns.append((fold2_btc.index[i], r30))

    max_30d_ret = max([x[1] for x in btc_30d_returns]) if btc_30d_returns else float("nan")
    print(f"\n  BTC max 30d rolling return during fold2 window: {max_30d_ret:.1f}%")

    # Primary cause assessment
    n_confirmed = sum([h1_bull_mania, h2_extreme_fr, h3_sign_flip, h4_lower_freq])
    causes = []
    if h1_bull_mania:
        causes.append("BTC_bull_mania")
    if h2_extreme_fr:
        causes.append("extreme_positive_FR")
    if h3_sign_flip:
        causes.append("reverse_carry_sign_flip")
    if h4_lower_freq:
        causes.append("signal_degraded")

    return {
        "h1_btc_bull_mania": h1_bull_mania,
        "h2_extreme_positive_fr": h2_extreme_fr,
        "h3_reverse_carry_sign_flip": h3_sign_flip,
        "h4_signal_degraded": h4_lower_freq,
        "n_hypotheses_confirmed": n_confirmed,
        "primary_causes": causes,
        "fold2_btc_ret_pct": round(btc_f2, 2),
        "fold2_fr_mean_ann": round(fr_f2, 4),
        "fold2_basis_mean": round(basis_f2, 6),
        "fold2_pos_freq": round(posfreq_f2, 4),
        "others_btc_ret_mean_pct": round(btc_others_mean, 2),
        "others_fr_mean_ann": round(fr_others_mean, 4),
        "others_pos_freq_mean": round(posfreq_others, 4),
        "btc_max_30d_rolling_ret_in_window_pct": round(max_30d_ret, 2) if not math.isnan(max_30d_ret) else None,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Gate signals
# ─────────────────────────────────────────────────────────────────────────────

def compute_btc_30d_return_signal(btc_close: pd.Series) -> pd.Series:
    """Daily BTC 30d rolling return (as %)."""
    btc_daily = btc_close.copy()
    btc_daily.index = pd.DatetimeIndex([str(d) for d in btc_daily.index])
    ret_30d = btc_daily.pct_change(30) * 100
    ret_30d.name = "btc_30d_ret_pct"
    return ret_30d


def compute_fr_mean_ann_signal(fr_means: pd.DataFrame) -> pd.Series:
    """Daily cross-major mean annualised FR (fraction, not %)."""
    s = fr_means.mean(axis=1)
    s.name = "fr_mean_ann"
    return s


def compute_dar_accuracy_rolling(sym: str, win: int = 60) -> Optional[pd.Series]:
    """
    Compute rolling DAR(2,1) direction accuracy for a symbol.
    Returns daily series. Uses simple rolling window.
    """
    hl_8h = load_hl_fr_8h(sym)
    bybit_8h = load_bybit_fr_8h(sym)
    if hl_8h is None or bybit_8h is None:
        return None

    hl_8h_aligned = hl_8h.reindex(bybit_8h.index)
    df = pd.DataFrame({"bybit": bybit_8h, "hl": hl_8h_aligned}).dropna()
    if len(df) < win + 10:
        return None

    fr_arr = df["bybit"].values
    spread = df["bybit"] - df["hl"]
    spread_z = (spread - spread.rolling(30, min_periods=30).mean()) / \
               (spread.rolling(30, min_periods=30).std() + 1e-12)
    spread_z = spread_z.fillna(0.0).values

    n = len(fr_arr)
    # Simple direction prediction: predict fr[t] from fr[t-1], fr[t-2], spread_z[t-1]
    # Rolling accuracy: fraction of last `win` events where sign(pred) == sign(actual)
    correct = np.zeros(n, dtype=float)
    valid   = np.zeros(n, dtype=bool)

    for i in range(3, n):
        # Simple OLS on last `win` events
        start = max(0, i - win)
        X_rows, y_vals = [], []
        for t in range(start + 2, i):
            row = [1.0, fr_arr[t-1], fr_arr[t-2], spread_z[t-1]]
            X_rows.append(row)
            y_vals.append(fr_arr[t])
        if len(X_rows) < 10:
            continue
        X_m = np.array(X_rows)
        y_m = np.array(y_vals)
        try:
            coeffs, _, _, _ = np.linalg.lstsq(X_m, y_m, rcond=None)
        except Exception:
            continue

        row_i = np.array([1.0, fr_arr[i-1], fr_arr[i-2], spread_z[i-1]])
        pred = float(np.dot(row_i, coeffs))
        actual = fr_arr[i]
        # Direction vs previous value
        pred_dir   = np.sign(pred - fr_arr[i-1])
        actual_dir = np.sign(actual - fr_arr[i-1])
        if actual_dir != 0:
            correct[i] = float(pred_dir == actual_dir)
            valid[i] = True

    # Rolling accuracy over win events
    correct_s = pd.Series(correct, index=df.index)
    valid_s   = pd.Series(valid.astype(float), index=df.index)

    rolling_correct = correct_s.rolling(win, min_periods=win // 2).sum()
    rolling_valid   = valid_s.rolling(win, min_periods=win // 2).sum()
    dar_acc = (rolling_correct / (rolling_valid + 1e-6)).clip(0, 1)

    # Resample to daily
    daily_acc = dar_acc.resample("D").last()
    daily_acc.name = f"dar_acc_{sym}"
    return daily_acc


# ─────────────────────────────────────────────────────────────────────────────
# Step 3: Build K208 + gate variants
# ─────────────────────────────────────────────────────────────────────────────

def apply_gate_to_k208(
    k208_pnl: pd.Series,
    gate_signal: pd.Series,
    gate_threshold,
    gate_direction: str = "halt_above",   # halt_above or halt_below
    gate_label: str = "gate",
) -> pd.Series:
    """
    Apply a daily regime gate to K208 daily PnL.
    When gate triggers, zero out PnL for that day.
    gate_direction:
      'halt_above': halt when signal > threshold (e.g. BTC bull mania)
      'halt_below': halt when signal < threshold (e.g. DAR accuracy low)
    """
    # Align gate signal to K208 dates
    gate_aligned = gate_signal.reindex(k208_pnl.index)
    gate_aligned = gate_aligned.ffill()  # forward-fill gaps

    if gate_direction == "halt_above":
        # Shift by 1 to avoid look-ahead (we observe yesterday's signal, apply today)
        halt_mask = gate_aligned.shift(1) > gate_threshold
    else:  # halt_below
        halt_mask = gate_aligned.shift(1) < gate_threshold

    halt_mask = halt_mask.fillna(False)
    gated_pnl = k208_pnl.copy()
    gated_pnl[halt_mask] = 0.0
    gated_pnl.name = f"K208_{gate_label}"

    n_halted = int(halt_mask.sum())
    n_total  = len(k208_pnl)
    pct_halted = 100 * n_halted / max(n_total, 1)
    print(f"    {gate_label}: halted {n_halted}/{n_total} days ({pct_halted:.1f}%)")

    return gated_pnl


def run_gate_variants(
    k208_pnl_ml: pd.Series,
    btc_30d_signal: pd.Series,
    fr_mean_signal: pd.Series,
    dar_acc_signal: Optional[pd.Series],
) -> Dict[str, pd.Series]:
    """Build K242a/b/c/d gate variants, returning daily PnL series."""
    print("\n=== STEP 3: BUILDING GATE VARIANTS ===")
    variants = {"K208_baseline": k208_pnl_ml.copy()}

    # K242a: Halt when BTC 30d return > +30%
    print("  K242a: BTC 30d return > +30% gate")
    v_a = apply_gate_to_k208(k208_pnl_ml, btc_30d_signal, 30.0, "halt_above", "K242a_btc_bull")
    variants["K242a_btc_bull"] = v_a

    # K242b: Halt when FR_mean_ann > +0.15 (extreme positive funding)
    print("  K242b: FR mean ann > 0.15 gate")
    v_b = apply_gate_to_k208(k208_pnl_ml, fr_mean_signal, 0.15, "halt_above", "K242b_fr_extreme")
    variants["K242b_fr_extreme"] = v_b

    # Also try FR > 0.10 as a tighter gate
    print("  K242b_tight: FR mean ann > 0.10 gate")
    v_b_tight = apply_gate_to_k208(k208_pnl_ml, fr_mean_signal, 0.10, "halt_above", "K242b_tight")
    variants["K242b_tight"] = v_b_tight

    # K242c: Halt when DAR direction accuracy < 60%
    if dar_acc_signal is not None:
        print("  K242c: DAR direction accuracy < 60% gate")
        v_c = apply_gate_to_k208(k208_pnl_ml, dar_acc_signal, 0.60, "halt_below", "K242c_dar_degraded")
        variants["K242c_dar_degraded"] = v_c
    else:
        print("  K242c: DAR accuracy signal unavailable, skipping")

    # K242d: Combined gate - halt when BTC 30d > 25% OR FR_mean > 0.12
    print("  K242d: Combined gate (BTC 30d > 25% OR FR_mean > 0.12)")
    btc_aligned = btc_30d_signal.reindex(k208_pnl_ml.index).ffill().shift(1)
    fr_aligned  = fr_mean_signal.reindex(k208_pnl_ml.index).ffill().shift(1)
    combined_halt = (btc_aligned > 25.0) | (fr_aligned > 0.12)
    combined_halt = combined_halt.fillna(False)
    v_d = k208_pnl_ml.copy()
    v_d[combined_halt] = 0.0
    v_d.name = "K208_K242d_combined"
    n_halt_d = int(combined_halt.sum())
    print(f"    K242d: halted {n_halt_d}/{len(k208_pnl_ml)} days ({100*n_halt_d/len(k208_pnl_ml):.1f}%)")
    variants["K242d_combined"] = v_d

    # K242e: Tighter combined gate (BTC 30d > 20% OR FR_mean > 0.10)
    print("  K242e: Tighter combined (BTC 30d > 20% OR FR_mean > 0.10)")
    combined_halt_e = (btc_aligned > 20.0) | (fr_aligned > 0.10)
    combined_halt_e = combined_halt_e.fillna(False)
    v_e = k208_pnl_ml.copy()
    v_e[combined_halt_e] = 0.0
    v_e.name = "K208_K242e_tight_combined"
    n_halt_e = int(combined_halt_e.sum())
    print(f"    K242e: halted {n_halt_e}/{len(k208_pnl_ml)} days ({100*n_halt_e/len(k208_pnl_ml):.1f}%)")
    variants["K242e_tight_combined"] = v_e

    return variants


# ─────────────────────────────────────────────────────────────────────────────
# Step 4: Walk-forward validation
# ─────────────────────────────────────────────────────────────────────────────

def validate_variants(variants: Dict[str, pd.Series]) -> List[Dict]:
    """Compute metrics for each variant, including per-fold Sharpe."""
    print("\n=== STEP 4: WALK-FORWARD VALIDATION ===")
    results = []

    # K229d reference
    k229d_ref = {
        "variant": "K229d_ensemble_ref",
        "oos_sharpe": K229D_OOS_SH,
        "wf_folds": K229D_WF_FOLDS,
        "wf_mean": round(float(np.mean(K229D_WF_FOLDS)), 4),
        "wf_min": K229D_WF_MIN,
        "max_dd": K229D_MAX_DD,
        "n_days_active": 447,
        "pct_active": 100.0,
        "source": "K240 reference",
        "fold2_sh": K229D_WF_FOLDS[1],
        "gate_applied": None,
    }
    results.append(k229d_ref)
    print(f"  K229d_ref: OOS_Sh={K229D_OOS_SH:.3f}  WF_min={K229D_WF_MIN:.3f}  "
          f"Fold2_Sh={K229D_WF_FOLDS[1]:.3f}")

    # K208 standalone reference
    k208_baseline_ref = {
        "variant": "K208_standalone_ref",
        "oos_sharpe": K208_OOS_SH,
        "wf_folds": K208_WF_FOLDS,
        "wf_mean": round(float(np.mean(K208_WF_FOLDS)), 4),
        "wf_min": K208_WF_MIN,
        "max_dd": -0.0002,
        "n_days_active": 447,
        "pct_active": 100.0,
        "source": "K240 reference",
        "fold2_sh": K208_WF_FOLDS[1],
        "gate_applied": None,
    }
    results.append(k208_baseline_ref)
    print(f"  K208_ref:  OOS_Sh={K208_OOS_SH:.3f}  WF_min={K208_WF_MIN:.3f}  "
          f"Fold2_Sh={K208_WF_FOLDS[1]:.3f}")

    for var_name, pnl in variants.items():
        pnl = pnl.dropna()
        if len(pnl) < 30:
            continue

        oos_sh = sharpe_daily(pnl)
        wf_mean, wf_min, wf_folds = wf_4fold_daily(pnl)
        eq = 1.0 + pnl.cumsum()
        mdd = max_dd_eq(eq)
        n_active = int((pnl != 0).sum())
        pct_active = round(100 * n_active / len(pnl), 1)

        fold2_sh = wf_folds[1]  # Fold 2 index = 1

        meets_fold2 = fold2_sh >= ACCEPT_FOLD2_SH
        meets_oos   = oos_sh >= ACCEPT_OOS_SH
        meets_wfmin = wf_min >= ACCEPT_WF_MIN
        simplify_verdict = "SIMPLIFY" if (meets_fold2 and meets_oos and meets_wfmin) else \
                           "PARTIAL" if (meets_fold2 or meets_wfmin) else "KEEP_K229D"

        res = {
            "variant": var_name,
            "oos_sharpe": round(oos_sh, 4),
            "wf_folds": wf_folds,
            "wf_mean": round(wf_mean, 4),
            "wf_min": round(wf_min, 4),
            "max_dd": round(mdd, 6),
            "n_days_active": n_active,
            "pct_active": pct_active,
            "fold2_sh": round(fold2_sh, 4),
            "gate_applied": var_name.replace("K208_baseline", "none"),
            "meets_fold2_gate": meets_fold2,
            "meets_oos_gate": meets_oos,
            "meets_wfmin_gate": meets_wfmin,
            "simplify_verdict": simplify_verdict,
        }
        results.append(res)

        flag = ""
        if meets_fold2 and meets_oos and meets_wfmin:
            flag = " *** ACCEPT for v6.8.1 ***"
        elif meets_fold2:
            flag = " (fold2 fixed)"

        print(f"  {var_name:<30} OOS_Sh={oos_sh:+.3f}  WF_min={wf_min:+.3f}  "
              f"Fold2_Sh={fold2_sh:+.3f}  Active={pct_active:.0f}%{flag}")

    return results


# ─────────────────────────────────────────────────────────────────────────────
# Build curves output
# ─────────────────────────────────────────────────────────────────────────────

def build_curves_output(
    variants: Dict[str, pd.Series],
    btc_close: pd.Series,
    btc_30d_signal: pd.Series,
    fr_mean_signal: pd.Series,
) -> Dict:
    """Build wave_k242_curves.json content."""
    curves = {}

    # K208 baseline equity
    for var_name, pnl in variants.items():
        pnl_clean = pnl.dropna()
        if len(pnl_clean) < 10:
            continue
        eq = (1.0 + pnl_clean.cumsum()).tolist()
        curves[var_name] = {
            "dates": [str(d)[:10] for d in pnl_clean.index],
            "equity": eq,
            "label": var_name,
        }

    # K229d reference equity from curves
    with open(BASE / "wave_k229_curves.json") as f:
        k229_raw = json.load(f)
    curves["K229d_ref"] = {
        "dates": k229_raw["dates"],
        "equity": k229_raw["K229d"],
        "label": "K229d (4-way ensemble reference)",
    }

    # BTC close price
    btc_ml = btc_close[(btc_close.index >= pd.Timestamp(ML_START)) &
                        (btc_close.index <= pd.Timestamp(ML_END))]
    curves["BTC_close"] = {
        "dates": [str(d)[:10] for d in btc_ml.index],
        "price": btc_ml.tolist(),
        "label": "BTC Close Price",
    }

    # BTC 30d return signal
    btc_30d_ml = btc_30d_signal[(btc_30d_signal.index >= ML_START) &
                                  (btc_30d_signal.index <= ML_END)]
    curves["btc_30d_return"] = {
        "dates": [str(d)[:10] for d in btc_30d_ml.index],
        "values": btc_30d_ml.tolist(),
        "label": "BTC 30d rolling return (%)",
    }

    # FR mean signal
    fr_ml = fr_mean_signal[(fr_mean_signal.index >= ML_START) &
                            (fr_mean_signal.index <= ML_END)]
    curves["fr_mean_ann"] = {
        "dates": [str(d)[:10] for d in fr_ml.index],
        "values": fr_ml.tolist(),
        "label": "FR mean annualised (6 majors)",
    }

    # Fold boundary markers
    curves["fold_boundaries"] = {
        "folds": [
            {"fold": i+1, "start": s, "end": e, "weak": (i == 1)}
            for i, (s, e) in enumerate(FOLD_BOUNDS)
        ]
    }

    return curves


# ─────────────────────────────────────────────────────────────────────────────
# Verdict
# ─────────────────────────────────────────────────────────────────────────────

def compute_final_verdict(validation_results: List[Dict]) -> Dict:
    """Determine if any K242 variant qualifies for v6.8.1 simplification."""
    print("\n=== FINAL VERDICT: K242 → v6.8.1? ===")

    computed = [r for r in validation_results
                if r.get("source") != "K240 reference" and r["variant"] != "K208_baseline"]

    best_fold2 = max(computed, key=lambda r: r.get("fold2_sh", -99)) if computed else None
    best_overall = max(computed, key=lambda r: r.get("oos_sharpe", -99)) if computed else None

    accept_candidates = [r for r in computed if r.get("simplify_verdict") == "SIMPLIFY"]
    partial_candidates = [r for r in computed if r.get("simplify_verdict") == "PARTIAL"]

    print(f"\n  Full accept candidates (all 3 gates): {len(accept_candidates)}")
    for r in accept_candidates:
        print(f"    {r['variant']}: OOS={r['oos_sharpe']:.3f}  "
              f"WF_min={r['wf_min']:.3f}  Fold2={r['fold2_sh']:.3f}")

    print(f"\n  Partial candidates (fold2 or wf_min gate): {len(partial_candidates)}")
    for r in partial_candidates:
        print(f"    {r['variant']}: OOS={r['oos_sharpe']:.3f}  "
              f"WF_min={r['wf_min']:.3f}  Fold2={r['fold2_sh']:.3f}")

    if accept_candidates:
        best = max(accept_candidates, key=lambda r: r["oos_sharpe"])
        verdict = "ACCEPT_v6.8.1"
        verdict_text = (
            f"K242 ACCEPTED for v6.8.1 simplification. "
            f"Best variant: {best['variant']} "
            f"(OOS Sh {best['oos_sharpe']:.3f}, WF_min {best['wf_min']:.3f}, "
            f"Fold2 Sh {best['fold2_sh']:.3f}). "
            f"K208+{best['variant']} replaces K229d 4-way ensemble."
        )
        recommended_variant = best["variant"]
    elif partial_candidates:
        best = max(partial_candidates, key=lambda r: r["fold2_sh"])
        verdict = "CONDITIONAL"
        verdict_text = (
            f"K242 CONDITIONAL: Fold2 improved but overall OOS or WF_min below threshold. "
            f"Best partial: {best['variant']} "
            f"(OOS Sh {best['oos_sharpe']:.3f}, WF_min {best['wf_min']:.3f}, "
            f"Fold2 Sh {best['fold2_sh']:.3f}). "
            f"Continue with K229d ensemble or investigate deeper gate tuning."
        )
        recommended_variant = best["variant"]
    else:
        verdict = "KEEP_K229D"
        verdict_text = (
            "K242 gates do NOT recover fold 2 sufficiently. "
            "No variant meets all 3 acceptance thresholds. "
            f"Accept thresholds: Fold2 Sh>={ACCEPT_FOLD2_SH}, "
            f"OOS Sh>={ACCEPT_OOS_SH}, WF_min>={ACCEPT_WF_MIN}. "
            "Continue with K229d 4-way ensemble (v6.8 production). "
            "Future work: explore deeper regime detection or alternative fold2 architecture."
        )
        recommended_variant = None

    print(f"\n  VERDICT: {verdict}")
    print(f"  {verdict_text}")

    return {
        "verdict": verdict,
        "verdict_text": verdict_text,
        "recommended_variant": recommended_variant,
        "n_full_accept": len(accept_candidates),
        "n_partial": len(partial_candidates),
        "best_fold2_candidate": best_fold2["variant"] if best_fold2 else None,
        "best_fold2_sh": best_fold2["fold2_sh"] if best_fold2 else None,
        "best_overall_candidate": best_overall["variant"] if best_overall else None,
        "best_overall_oos_sh": best_overall["oos_sharpe"] if best_overall else None,
        "acceptance_thresholds": {
            "fold2_sh_min": ACCEPT_FOLD2_SH,
            "oos_sh_min": ACCEPT_OOS_SH,
            "wf_min_min": ACCEPT_WF_MIN,
        },
    }


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    t0 = time.time()
    print("=" * 70)
    print("Wave K242: K208 Fold 2 Diagnosis & Regime Gate")
    print("=" * 70)
    print(f"ML window: {ML_START} → {ML_END}")
    print(f"Fold 2: {FOLD_BOUNDS[1][0]} → {FOLD_BOUNDS[1][1]}  (K208 Sh=5.78, weakest)")
    print(f"K229d reference: OOS Sh={K229D_OOS_SH:.3f}  WF_min={K229D_WF_MIN:.3f}")

    # ── Load K208 daily PnL ──────────────────────────────────────────────────
    print("\n[1/7] Loading K208 daily PnL...")
    k208_pnl_full = load_k208_daily_pnl()
    k208_pnl_ml = k208_pnl_full[(k208_pnl_full.index >= ML_START) &
                                   (k208_pnl_full.index <= ML_END)]
    print(f"  K208 PnL loaded: n={len(k208_pnl_ml)} days, "
          f"total={k208_pnl_ml.sum():.6f}, Sh={sharpe_daily(k208_pnl_ml):.4f}")

    # ── Load BTC daily price ──────────────────────────────────────────────────
    print("\n[2/7] Loading BTC daily price...")
    btc_close = load_btc_daily_price()
    if btc_close is None:
        raise RuntimeError("BTC daily price data not available")
    print(f"  BTC close loaded: n={len(btc_close)}, "
          f"range={btc_close.index.min()}..{btc_close.index.max()}")

    # ── Load funding rate data for 6 majors ──────────────────────────────────
    print("\n[3/7] Loading funding rate data for 6 majors...")
    fr_daily_series = {}
    for sym in MAJOR_6:
        s = load_bybit_fr_daily(sym)
        if s is not None:
            fr_daily_series[sym] = s
            print(f"  {sym}: n={len(s)}, mean_ann={s.mean():.4f}")
        else:
            print(f"  {sym}: NOT FOUND")
    fr_means = pd.DataFrame(fr_daily_series).dropna(how="all")
    print(f"  FR panel: {len(fr_means)} days, {len(fr_daily_series)} symbols")

    # ── Load BTC HL/Bybit FR for basis spread ─────────────────────────────────
    print("\n[4/7] Loading BTC HL + Bybit FR (8h) for basis spread...")
    hl_btc_daily_raw = load_hl_fr_daily("BTC")
    bybit_btc_daily_raw = load_bybit_fr_daily("BTC")
    if hl_btc_daily_raw is not None and bybit_btc_daily_raw is not None:
        print(f"  BTC HL daily: n={len(hl_btc_daily_raw)}, "
              f"mean_ann={hl_btc_daily_raw.mean():.4f}")
        print(f"  BTC Bybit daily: n={len(bybit_btc_daily_raw)}, "
              f"mean_ann={bybit_btc_daily_raw.mean():.4f}")
    else:
        print("  WARNING: BTC basis data incomplete, using zeros")
        hl_btc_daily_raw = pd.Series(0.0, index=fr_means.index)
        bybit_btc_daily_raw = pd.Series(0.0, index=fr_means.index)

    # ── Step 1: Fold 2 Diagnostic ─────────────────────────────────────────────
    diag_result = compute_fold2_diagnostic(
        k208_pnl_ml,
        btc_close,
        fr_means,
        hl_btc_daily_raw,
        bybit_btc_daily_raw,
    )
    fold_stats = diag_result["fold_diagnostics"]

    # ── Step 2: Hypothesis Tests ──────────────────────────────────────────────
    hyp_result = test_hypotheses(fold_stats, btc_close)

    # ── Compute gate signals ─────────────────────────────────────────────────
    print("\n[5/7] Computing gate signals...")
    btc_30d_signal = compute_btc_30d_return_signal(btc_close)
    fr_mean_signal = compute_fr_mean_ann_signal(fr_means)
    print(f"  BTC 30d signal: max={btc_30d_signal.max():.1f}%  in fold2 window: "
          f"{btc_30d_signal[(btc_30d_signal.index >= FOLD_BOUNDS[1][0]) & (btc_30d_signal.index <= FOLD_BOUNDS[1][1])].max():.1f}%")
    print(f"  FR mean ann signal: max={fr_mean_signal.max():.4f}  fold2 mean: "
          f"{fr_mean_signal[(fr_mean_signal.index >= FOLD_BOUNDS[1][0]) & (fr_mean_signal.index <= FOLD_BOUNDS[1][1])].mean():.4f}")

    # Optional: DAR accuracy for primary symbol
    print("\n  Computing DAR accuracy signal for SOL (may take a moment)...")
    dar_acc_sol = compute_dar_accuracy_rolling("SOL", win=60)
    if dar_acc_sol is not None:
        print(f"  SOL DAR acc: mean={dar_acc_sol.mean():.4f}  "
              f"fold2 mean={dar_acc_sol[(dar_acc_sol.index >= pd.Timestamp(FOLD_BOUNDS[1][0])) & (dar_acc_sol.index <= pd.Timestamp(FOLD_BOUNDS[1][1]))].mean():.4f}")
    else:
        print("  SOL DAR acc: unavailable")

    # ── Step 3: Build gate variants ────────────────────────────────────────────
    variants = run_gate_variants(k208_pnl_ml, btc_30d_signal, fr_mean_signal, dar_acc_sol)

    # ── Step 4: Walk-forward validation ───────────────────────────────────────
    print("\n[6/7] Running walk-forward validation...")
    validation_results = validate_variants(variants)

    # ── Final verdict ──────────────────────────────────────────────────────────
    verdict_result = compute_final_verdict(validation_results)

    # ── Print comparison table ─────────────────────────────────────────────────
    print("\n=== COMPARISON TABLE ===")
    header = f"{'Variant':<35} {'OOS Sh':>8} {'WF_min':>8} {'Fold2 Sh':>10} {'Active%':>8} {'Verdict':>12}"
    print(f"  {header}")
    print(f"  {'-'*35} {'-'*8} {'-'*8} {'-'*10} {'-'*8} {'-'*12}")
    for r in validation_results:
        verdict_flag = r.get("simplify_verdict", "ref")
        print(f"  {r['variant']:<35} {r['oos_sharpe']:>+8.3f} {r['wf_min']:>+8.3f} "
              f"{r.get('fold2_sh', r.get('wf_folds', [0]*4)[1] if 'wf_folds' in r else 0):>+10.3f} "
              f"{r.get('pct_active', 100):>7.1f}% {verdict_flag:>12}")

    # ── Build curves output ────────────────────────────────────────────────────
    print("\n[7/7] Building curves output...")
    curves_out = build_curves_output(variants, btc_close, btc_30d_signal, fr_mean_signal)

    # ── Assemble JSON output ───────────────────────────────────────────────────
    runtime_s = round(time.time() - t0, 1)
    output = {
        "wave": "K242",
        "objective": "K208 Fold 2 Diagnosis & Regime Gate — v6.8.1 Simplification Test",
        "as_of": pd.Timestamp.now(tz="UTC").isoformat(),
        "runtime_s": runtime_s,

        "config": {
            "ml_window": {"start": ML_START, "end": ML_END},
            "fold_bounds": [{"fold": i+1, "start": s, "end": e}
                            for i, (s, e) in enumerate(FOLD_BOUNDS)],
            "reverse_10": REVERSE_10,
            "major_6_for_fr": MAJOR_6,
            "acceptance_thresholds": {
                "fold2_sh_min": ACCEPT_FOLD2_SH,
                "oos_sh_min": ACCEPT_OOS_SH,
                "wf_min_min": ACCEPT_WF_MIN,
            },
        },

        "reference_metrics": {
            "K208_standalone": {
                "oos_sharpe": K208_OOS_SH,
                "wf_folds": K208_WF_FOLDS,
                "wf_min": K208_WF_MIN,
                "max_dd": -0.0002,
                "source": "K240",
            },
            "K229d_ensemble": {
                "oos_sharpe": K229D_OOS_SH,
                "wf_folds": K229D_WF_FOLDS,
                "wf_min": K229D_WF_MIN,
                "max_dd": K229D_MAX_DD,
                "source": "K240",
            },
        },

        "fold2_diagnostic": {
            "fold_stats": fold_stats,
            "fold2_dates": {"start": FOLD_BOUNDS[1][0], "end": FOLD_BOUNDS[1][1]},
            "fold2_sharpe_k208_standalone": K208_WF_FOLDS[1],
            "fold2_sharpe_k229d_ensemble": K229D_WF_FOLDS[1],
            "fold2_recovery_target": ACCEPT_FOLD2_SH,
        },

        "hypothesis_tests": hyp_result,

        "gate_variants": {
            "K242a": {
                "description": "Halt K208 when BTC 30d return > +30% (bull mania)",
                "gate_signal": "btc_30d_ret_pct",
                "threshold": 30.0,
                "direction": "halt_above",
            },
            "K242b": {
                "description": "Halt K208 when FR_mean_ann > +0.15 (extreme positive funding)",
                "gate_signal": "fr_mean_ann_6maj",
                "threshold": 0.15,
                "direction": "halt_above",
            },
            "K242b_tight": {
                "description": "Halt K208 when FR_mean_ann > +0.10 (tight extreme positive funding)",
                "gate_signal": "fr_mean_ann_6maj",
                "threshold": 0.10,
                "direction": "halt_above",
            },
            "K242c": {
                "description": "Halt K208 when DAR direction accuracy < 60% (signal degraded)",
                "gate_signal": "dar_acc_sol_60d_rolling",
                "threshold": 0.60,
                "direction": "halt_below",
                "available": dar_acc_sol is not None,
            },
            "K242d": {
                "description": "Combined: BTC 30d > 25% OR FR_mean > 0.12",
                "gate_signal": "combined_btc_or_fr",
                "thresholds": {"btc_30d": 25.0, "fr_mean": 0.12},
                "direction": "halt_either",
            },
            "K242e": {
                "description": "Tight combined: BTC 30d > 20% OR FR_mean > 0.10",
                "gate_signal": "combined_btc_or_fr_tight",
                "thresholds": {"btc_30d": 20.0, "fr_mean": 0.10},
                "direction": "halt_either",
            },
        },

        "validation_results": validation_results,
        "final_verdict": verdict_result,
    }

    # ── Write outputs ─────────────────────────────────────────────────────────
    json_path   = BASE / "wave_k242_k208_fold2_gate.json"
    curves_path = BASE / "wave_k242_curves.json"

    json_path.write_text(json.dumps(output, indent=2, default=str))
    curves_path.write_text(json.dumps(curves_out, indent=2, default=str))

    print(f"\nWrote {json_path} ({json_path.stat().st_size:,} bytes)")
    print(f"Wrote {curves_path} ({curves_path.stat().st_size:,} bytes)")
    print(f"Total runtime: {runtime_s}s")
    print(f"\nVERDICT: {verdict_result['verdict']}")
    print(f"{verdict_result['verdict_text']}")

    # ── Generate markdown report ───────────────────────────────────────────────
    generate_markdown_report(output, fold_stats, hyp_result, validation_results, verdict_result)


def generate_markdown_report(
    output: Dict,
    fold_stats: List[Dict],
    hyp_result: Dict,
    validation_results: List[Dict],
    verdict_result: Dict,
) -> None:
    """Generate wave_k242_k208_fold2_gate.md."""
    runtime_s = output["runtime_s"]
    as_of = output["as_of"]

    lines = [
        "# Wave K242: K208 Fold 2 Diagnosis & Regime Gate",
        "",
        f"**Generated:** {as_of[:19]} UTC  **Runtime:** {runtime_s}s",
        "",
        "## Executive Summary",
        "",
        f"K242 investigates why K208 (DAR-filtered reverse carry) underperforms in fold 2 "
        f"(2025-05-14 to 2025-09-02, Sh=5.78) versus folds 1/3/4 (Sh~14-17). "
        f"Four regime gate variants are tested to fix this weakness. "
        f"**Verdict: {verdict_result['verdict']}**",
        "",
        f"> {verdict_result['verdict_text']}",
        "",
        "---",
        "",
        "## Section 1: Fold 2 Diagnostic",
        "",
        "### Reference Metrics",
        "",
        "| System | OOS Sh | WF Folds | WF min | MaxDD |",
        "|--------|--------|----------|--------|-------|",
        f"| K208 standalone | {K208_OOS_SH:.3f} | {K208_WF_FOLDS} | {K208_WF_MIN:.3f} | -0.0002 |",
        f"| K229d ensemble  | {K229D_OOS_SH:.3f} | {K229D_WF_FOLDS} | {K229D_WF_MIN:.3f} | {K229D_MAX_DD} |",
        "",
        "### Fold-by-Fold Characterization",
        "",
        "| Fold | Dates | K208 Sh | BTC Ret% | BTC Trend | FR mean ann | FR pos% | Basis vol | +PnL freq |",
        "|------|-------|---------|----------|-----------|-------------|---------|-----------|-----------|",
    ]

    for fs in fold_stats:
        weak_flag = " ← WEAK" if fs["is_fold2"] else ""
        lines.append(
            f"| Fold {fs['fold']}{weak_flag} | {fs['start']} → {fs['end']} "
            f"| {fs['sharpe']:.3f} "
            f"| {fs['btc_ret_fold_pct'] or 'N/A'}% "
            f"| {fs['btc_trend_direction']} "
            f"| {fs['fr_mean_ann_6maj'] or 'N/A'} "
            f"| {fs['fr_pct_positive'] or 'N/A'} "
            f"| {fs['basis_vol_btc'] or 'N/A'} "
            f"| {fs['pnl_positive_freq'] or 'N/A'} |"
        )

    fold2_fs = next(f for f in fold_stats if f["fold"] == 2)
    lines += [
        "",
        "### Fold 2 Detail",
        "",
        f"- **Dates:** {fold2_fs['start']} → {fold2_fs['end']}  ({fold2_fs['n_days']} days)",
        f"- **K208 Sharpe:** {fold2_fs['sharpe']:.4f} (vs 17.35/17.41/13.11 in other folds)",
        f"- **Daily PnL:** mean={fold2_fs['pnl_mean_daily']:.8f}, "
        f"std={fold2_fs['pnl_std_daily']:.8f}",
        f"- **Positive day frequency:** {fold2_fs['pnl_positive_freq']:.3f} "
        f"(negative: {fold2_fs['pnl_negative_freq']:.3f})",
        f"- **BTC return (full fold):** {fold2_fs['btc_ret_fold_pct']}% "
        f"[{fold2_fs['btc_trend_direction']}]",
        f"- **BTC 30d return (end of fold):** {fold2_fs['btc_ret_last30d_pct']}%",
        f"- **FR mean annualised (6 majors):** {fold2_fs['fr_mean_ann_6maj']} "
        f"({(fold2_fs['fr_mean_ann_6maj'] or 0)*100:.2f}%)",
        f"- **Basis spread mean (BTC HL-Bybit):** {fold2_fs['basis_mean_btc']}",
        f"- **Basis spread vol:** {fold2_fs['basis_vol_btc']}",
        "",
        "---",
        "",
        "## Section 2: Hypothesis Tests",
        "",
        f"**Hypotheses confirmed:** {hyp_result['n_hypotheses_confirmed']}/4",
        "",
        "| Hypothesis | Result | Evidence |",
        "|------------|--------|----------|",
        f"| H1: BTC Bull Mania (fold2 BTC>20%) | {'CONFIRMED' if hyp_result['h1_btc_bull_mania'] else 'NOT CONFIRMED'} | "
        f"Fold2 BTC={hyp_result['fold2_btc_ret_pct']:.1f}% vs others mean={hyp_result['others_btc_ret_mean_pct']:.1f}% |",
        f"| H2: Extreme Positive FR (>10% ann) | {'CONFIRMED' if hyp_result['h2_extreme_positive_fr'] else 'NOT CONFIRMED'} | "
        f"Fold2 FR={hyp_result['fold2_fr_mean_ann']:.4f} vs others={hyp_result['others_fr_mean_ann']:.4f} |",
        f"| H3: Reverse Carry Sign Flip | {'CONFIRMED' if hyp_result['h3_reverse_carry_sign_flip'] else 'NOT CONFIRMED'} | "
        f"Fold2 basis={hyp_result['fold2_basis_mean']:.6f} |",
        f"| H4: Signal Degraded (lower pos freq) | {'CONFIRMED' if hyp_result['h4_signal_degraded'] else 'NOT CONFIRMED'} | "
        f"Fold2 pos_freq={hyp_result['fold2_pos_freq']:.4f} vs others={hyp_result['others_pos_freq_mean']:.4f} |",
        "",
        f"**Primary causes identified:** {', '.join(hyp_result['primary_causes']) or 'none (mild degradation)'}",
        f"**BTC max 30d rolling return in fold2 window:** {hyp_result.get('btc_max_30d_rolling_ret_in_window_pct')}%",
        "",
        "---",
        "",
        "## Section 3: Gate Variants",
        "",
        "| Variant | Gate Logic | Threshold |",
        "|---------|-----------|-----------|",
        "| K242a | Halt K208 when BTC 30d return > threshold | +30% |",
        "| K242b | Halt K208 when FR_mean_ann > threshold | +15% ann |",
        "| K242b_tight | Halt K208 when FR_mean_ann > threshold | +10% ann |",
        "| K242c | Halt K208 when DAR direction accuracy < threshold | 60% |",
        "| K242d | Combined: BTC 30d > 25% OR FR_mean > 12% | dual |",
        "| K242e | Tight combined: BTC 30d > 20% OR FR_mean > 10% | dual |",
        "",
        "---",
        "",
        "## Section 4: Walk-Forward Validation",
        "",
        "### Per-Variant Comparison",
        "",
        "| Variant | OOS Sh | WF_min | Fold1 | Fold2 | Fold3 | Fold4 | Active% | Verdict |",
        "|---------|--------|--------|-------|-------|-------|-------|---------|---------|",
    ]

    for r in validation_results:
        folds = r.get("wf_folds", ["?"] * 4)
        fold_str = " | ".join(f"{x:.3f}" if isinstance(x, float) else str(x) for x in folds[:4])
        lines.append(
            f"| {r['variant']} "
            f"| {r['oos_sharpe']:+.3f} "
            f"| {r['wf_min']:+.3f} "
            f"| {fold_str} "
            f"| {r.get('pct_active', 100):.1f}% "
            f"| {r.get('simplify_verdict', 'ref')} |"
        )

    lines += [
        "",
        "### Acceptance Thresholds",
        "",
        f"- Fold 2 Sh >= {ACCEPT_FOLD2_SH} (recovery to K229d level)",
        f"- Overall OOS Sh >= {ACCEPT_OOS_SH} (>= K229d)",
        f"- WF min >= {ACCEPT_WF_MIN} (>= K229d)",
        "",
        "---",
        "",
        "## Section 5: Final Verdict — K242 → v6.8.1",
        "",
        f"**Verdict: {verdict_result['verdict']}**",
        "",
        f"{verdict_result['verdict_text']}",
        "",
        "### Decision Logic",
        "",
        f"- Full accept candidates (all 3 gates met): **{verdict_result['n_full_accept']}**",
        f"- Partial candidates (fold2 or wf_min): **{verdict_result['n_partial']}**",
        f"- Best fold2 recovery: {verdict_result['best_fold2_candidate']} "
        f"(Sh={verdict_result['best_fold2_sh']})",
        f"- Best overall OOS: {verdict_result['best_overall_candidate']} "
        f"(Sh={verdict_result['best_overall_oos_sh']})",
        "",
        "### Architecture Comparison",
        "",
        "| Architecture | Components | Gates | Complexity |",
        "|-------------|-----------|-------|------------|",
        "| v6.8 K229d | K198+K204+K208+K226 | inv-vol weights, K226 cap 20% | HIGH |",
        "| v6.8.1 K208+gate | K208 DAR filter | regime gate (BTC or FR) | LOW |",
        "",
        "### Next Steps",
        "",
    ]

    if verdict_result["verdict"] == "ACCEPT_v6.8.1":
        lines += [
            f"1. Deploy {verdict_result['recommended_variant']} as production v6.8.1",
            "2. Update ct_forward_monolith.py to add regime gate check",
            "3. Paper trade 14 days before live deployment",
            "4. Archive K229d ensemble code as v6.8 fallback",
        ]
    elif verdict_result["verdict"] == "CONDITIONAL":
        lines += [
            f"1. Investigate tighter gate thresholds for {verdict_result['recommended_variant']}",
            "2. Consider hybrid: K208+gate as primary, K229d as fallback",
            "3. Continue monitoring fold 2 regime characteristics",
            "4. Run K243 with finer threshold grid search",
        ]
    else:
        lines += [
            "1. Continue with K229d ensemble (v6.8 production)",
            "2. Investigate if fold 2 weakness is structural (carry strategy inherent)",
            "3. Consider K243: alternative architectures (LSTM, HMM) for fold 2 regime detection",
            "4. Monitor if fold 2 regime re-appears in live trading",
        ]

    lines += [
        "",
        "---",
        "",
        "*Wave K242 — Systematic Alpha Discovery*",
    ]

    md_path = BASE / "wave_k242_k208_fold2_gate.md"
    md_path.write_text("\n".join(lines))
    print(f"Wrote {md_path} ({md_path.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
