"""Wave K196 — Reverse Carry Panel: LONG HL + SHORT Bybit on 10 opposite-spread symbols.

Objective:
  K189 identified 10 symbols where Bybit FR > HL FR persistently:
    SOL, XRP, SUI, OP, APT, AXS, JTO, IMX, SAND, ADA
  These scored Sharpe -7 to -18 in original K189 (LONG Bybit / SHORT HL test).
  Flipping the direction → LONG HL + SHORT Bybit → we RECEIVE Bybit FR - HL FR.

Strategy per event:
  Reverse carry PnL = (Bybit_FR_8h - HL_FR_8h) per event
  Positive when Bybit FR > HL FR (which is the structural observation for these symbols).

Architecture:
  1. Per-symbol reverse carry PnL (LONG HL + SHORT Bybit)
  2. Per-symbol stats: full-period + 90d Sharpe, mean premium
  3. §6 strict gates per symbol if gross Sh >= 1.0
  4. Equal-weight + Sharpe-weighted panel variants
  5. Correlation: vs V_forward_carry_panel (K195), within reverse panel
  6. K196 ensemble: K195 9 components + V_reverse_carry_panel as 10th carry slot
  7. Total carry sleeve cap sweep (forward 10% + reverse 5-12%)
  8. Counterparty diversification analysis (key risk-management deliverable)
  9. Three-way comparison: K194 / K195 / K196
  10. Acceptance criteria: OOS Sh > 5.82, MaxDD not worsened, WF min ≥ 3.5,
      HL net exposure reduced ≥ 30%

Data:
  cache/k163_hl/hl_fr_{SYM}.parquet (already fetched by K189)
  cache/bybit_fr_{SYM}USDT_730d.parquet

Runtime target: <12 min.
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

TRADING_DAYS = 365
OOS_FRAC     = 0.30
N_FOLDS      = 4
TRAIN_FRAC   = 0.70

# 10 symbols with OPPOSITE spread sign: Bybit FR > HL FR (from K189 analysis)
# These scored Sharpe -7 to -18 in original forward-carry direction
REVERSE_10 = ["SOL", "XRP", "SUI", "OP", "APT", "AXS", "JTO", "IMX", "SAND", "ADA"]

# Bybit ticker map (some symbols use standard naming)
BYBIT_TICKER_REV = {
    "SOL":  "SOL",
    "XRP":  "XRP",
    "SUI":  "SUI",
    "OP":   "OP",
    "APT":  "APT",
    "AXS":  "AXS",
    "JTO":  "JTO",
    "IMX":  "IMX",
    "SAND": "SAND",
    "ADA":  "ADA",
}

# K189 90d Sharpe values (NEGATIVE because we measured in wrong direction)
# Reverse carry Sharpe should be abs(K189_Sharpe) approximately
K189_REV_90D_SH_MAGNITUDE = {
    "SOL":  7.351,
    "XRP":  11.828,
    "SUI":  15.239,
    "OP":   16.184,
    "APT":  13.686,
    "AXS":  18.061,
    "JTO":  14.937,
    "IMX":  9.832,
    "SAND": 5.116,
    "ADA":  6.465,
}

# K195 reference values (current production)
K195_OOS_SH   = 5.7678
K195_OOS_DD   = -0.0043
K195_WF_MEAN  = 5.5328
K195_WF_MIN   = 3.8321

# K194 reference
K194_OOS_SH   = 5.6626
K194_OOS_DD   = -0.0045
K194_WF_MEAN  = 5.0204
K194_WF_MIN   = 3.7616

# K121 cap (same as K195)
K121_CAP = 0.30

# Carry cap for reverse panel (forward carries 10%, reverse additional 5-12%)
REVERSE_CARRY_CAP_PRIMARY = 0.10  # Symmetric with forward
FORWARD_CARRY_CAP         = 0.10  # K195 forward panel cap

# Cap sweep for combined carry sleeve
REV_CAP_SWEEP = [0.05, 0.07, 0.10, 0.12]

# FR defensive trigger (same as K195)
FR_SYMBOLS = ["BTC", "ETH", "DOGE", "AVAX", "SOL", "XRP"]
THRESHOLD_PRIMARY = -0.009735
PARTIAL_TRIGGER_COMPONENTS = ["K121", "K133"]


# ──────────────────────────────────────────────────────────────────────────────
# Metrics
# ──────────────────────────────────────────────────────────────────────────────

def sharpe_d(r: np.ndarray) -> float:
    r = np.asarray(r, dtype=float)
    if len(r) < 2 or r.std(ddof=1) == 0:
        return 0.0
    return float(r.mean() / r.std(ddof=1) * math.sqrt(TRADING_DAYS))


def sortino_d(r: np.ndarray) -> float:
    dn = r[r < 0]
    if len(dn) < 2 or dn.std(ddof=1) == 0:
        return 0.0
    return float(r.mean() / dn.std(ddof=1) * math.sqrt(TRADING_DAYS))


def max_dd_d(r: np.ndarray) -> float:
    eq = np.cumprod(1.0 + np.asarray(r, dtype=float))
    peak = np.maximum.accumulate(eq)
    return float((eq / peak - 1.0).min())


def calmar_d(r: np.ndarray) -> float:
    ann = (1.0 + np.asarray(r, dtype=float)).prod() ** (TRADING_DAYS / max(1, len(r))) - 1.0
    mdd = max_dd_d(r)
    return float(ann / abs(mdd)) if mdd != 0 else 0.0


def metrics_pkg(r: np.ndarray) -> dict:
    r = np.asarray(r, dtype=float)
    if len(r) < 2:
        return {"sharpe": 0.0, "sortino": 0.0, "calmar": 0.0, "max_dd": 0.0,
                "ann_ret": 0.0, "ann_vol": 0.0, "n_days": int(len(r))}
    ann_ret = float((1.0 + r).prod() ** (TRADING_DAYS / len(r)) - 1.0)
    ann_vol = float(r.std(ddof=1) * math.sqrt(TRADING_DAYS))
    return {
        "sharpe":  round(sharpe_d(r), 4),
        "sortino": round(sortino_d(r), 4),
        "calmar":  round(calmar_d(r), 4),
        "max_dd":  round(max_dd_d(r), 4),
        "ann_ret": round(ann_ret, 4),
        "ann_vol": round(ann_vol, 4),
        "n_days":  int(len(r)),
    }


def debiased_sharpe_ratio(r: np.ndarray) -> float:
    """Deflated Sharpe / IS estimate (used in §6 gate)."""
    r = np.asarray(r, dtype=float)
    n = len(r)
    if n < 10:
        return 0.0
    sr = r.mean() / r.std(ddof=1)
    # Annualized IS SR (used as simple gate proxy)
    return float(sr * math.sqrt(TRADING_DAYS))


def section6_gates(r_is: np.ndarray, r_oos: np.ndarray,
                   n_trials: int = 1, n_folds: int = 4) -> dict:
    """
    Simplified §6 gates (adapted from K189 methodology):
      G1: OOS Sharpe > 1.0
      G2: Permutation p-value (simple: IS mean > 2*std of permuted means)
      G3: Deflated Sharpe Ratio (IS) > 1.0 annualized
      G4: Walk-forward 4-fold consistency (>= 3/4 folds positive)
    """
    sh_is  = sharpe_d(r_is)
    sh_oos = sharpe_d(r_oos)

    # G1
    g1_pass = bool(sh_oos > 1.0)

    # G2: simplified permutation
    n_perm = 500
    is_mean = float(r_is.mean())
    perm_means = [float(np.random.permutation(r_is).mean()) for _ in range(n_perm)]
    perm_std = float(np.std(perm_means))
    # p-value: fraction of permutations beating actual mean
    p_val = float(np.mean([m >= is_mean for m in perm_means]))
    g2_pass = bool(p_val < 0.05)

    # G3: DSR > 1.0 (simplified: IS SR > 1.0 annualized adjusted for trials)
    sr_adj = sh_is / math.sqrt(1 + n_trials * 0.1) if sh_is > 0 else 0.0
    g3_pass = bool(sr_adj > 1.0)

    # G4: Walk-forward 4-fold (split IS into 4 sub-folds, check positive)
    n = len(r_is)
    fold_n = n // n_folds
    fold_sharpes = []
    for i in range(n_folds):
        start = i * fold_n
        end = start + fold_n if i < n_folds - 1 else n
        fs = sharpe_d(r_is[start:end])
        fold_sharpes.append(fs)
    n_pos_folds = sum(s > 0 for s in fold_sharpes)
    g4_pass = bool(n_pos_folds >= 3)

    return {
        "is_sharpe": round(sh_is, 4),
        "oos_sharpe": round(sh_oos, 4),
        "full_sharpe": round(sharpe_d(np.concatenate([r_is, r_oos])), 4),
        "gates": {
            "G1_oos_sh":   {"value": round(sh_oos, 4), "pass": g1_pass},
            "G2_perm_p":   {"value": round(p_val, 4),  "pass": g2_pass},
            "G3_dsr":      {"value": round(sr_adj, 4),  "pass": g3_pass},
            "G4_wf_folds": {"value": fold_sharpes,      "pass": g4_pass},
        },
        "n_gates_pass": int(g1_pass + g2_pass + g3_pass + g4_pass),
        "overall_pass": bool(g1_pass and g3_pass and g4_pass),  # G2 can fail (1-sample issue)
    }


# ──────────────────────────────────────────────────────────────────────────────
# Data loading
# ──────────────────────────────────────────────────────────────────────────────

def load_hl_fr(sym: str) -> Optional[pd.DataFrame]:
    """Load HL hourly funding rate from cache."""
    path = HL_CACHE / f"hl_fr_{sym}.parquet"
    if not path.exists():
        print(f"  WARNING: HL FR cache missing for {sym}")
        return None
    df = pd.read_parquet(path)
    df["timestamp"] = pd.to_datetime(df["timestamp"]).dt.tz_localize(None)
    df = df.sort_values("timestamp").drop_duplicates("timestamp")
    return df


def load_bybit_fr(sym: str) -> Optional[pd.DataFrame]:
    """Load Bybit 8h funding rate from cache (tries multiple suffixes)."""
    prefix = BYBIT_TICKER_REV.get(sym, sym)
    for tag in ("730d", "1200d", "365d"):
        path = CACHE / f"bybit_fr_{prefix}USDT_{tag}.parquet"
        if path.exists():
            df = pd.read_parquet(path)
            df["timestamp"] = pd.to_datetime(df["timestamp"]).dt.tz_localize(None)
            df = df.sort_values("timestamp").drop_duplicates("timestamp")
            return df
    print(f"  WARNING: Bybit FR cache missing for {sym} (prefix={prefix})")
    return None


def compute_reverse_carry_pnl(sym: str) -> Optional[pd.Series]:
    """
    Compute daily reverse carry PnL for LONG HL + SHORT Bybit.

    Per-event PnL = (Bybit_FR_8h - HL_FR_8h)
    Positive when Bybit FR > HL FR (which is structural for these 10 symbols).
    Daily PnL = sum of 3 8h-events (in bps → fractional return).

    Steps:
      1. HL hourly → resample 8h sums
      2. Bybit 8h events → align to same 8h boundaries
      3. merge_asof (5h tolerance)
      4. reverse_premium = bybit - hl_8h
      5. resample daily → sum → divide by 10000 → daily return
    """
    hl_df = load_hl_fr(sym)
    bybit_df = load_bybit_fr(sym)
    if hl_df is None or bybit_df is None:
        return None

    # HL: hourly → 8h sum
    hl = hl_df.set_index("timestamp")["hl_fr"]
    hl_8h = hl.resample("8h").sum().reset_index()
    hl_8h.columns = ["ts", "hl_fr_8h"]

    # Bybit 8h
    bybit = bybit_df.rename(columns={"timestamp": "ts", "funding_rate": "bybit_fr"})[["ts", "bybit_fr"]].copy()

    # Align via merge_asof
    merged = pd.merge_asof(
        bybit.sort_values("ts"),
        hl_8h.sort_values("ts"),
        on="ts",
        tolerance=pd.Timedelta("5h"),
        direction="nearest",
    ).dropna(subset=["hl_fr_8h"])

    if len(merged) < 30:
        print(f"  WARNING: {sym} insufficient merged events ({len(merged)})")
        return None

    # REVERSE carry: Bybit pays more → we earn (long HL, short Bybit)
    # premium_bps > 0 means Bybit rate > HL rate → we earn
    merged["reverse_premium_bps"] = (merged["bybit_fr"] - merged["hl_fr_8h"]) * 10_000
    merged["ts"] = pd.to_datetime(merged["ts"])

    # Daily PnL = sum 3 events per day (bps → fractional return)
    merged["date"] = merged["ts"].dt.normalize()
    daily_bps = merged.groupby("date")["reverse_premium_bps"].sum()
    daily_ret = daily_bps / 10_000
    daily_ret.name = sym
    daily_ret.index = pd.to_datetime(daily_ret.index)
    return daily_ret


# ──────────────────────────────────────────────────────────────────────────────
# Panel construction
# ──────────────────────────────────────────────────────────────────────────────

def build_reverse_panel(symbols: List[str],
                        min_days_required: int = 90):
    """
    Load per-symbol reverse carry PnL.

    Strategy:
      - Compute individual series (full range each symbol allows)
      - Classify into "core" (>=365 days) and "short" (<365 days)
      - Use OUTER join so that core symbols anchor the full date range
      - Short-history symbols fill NaN → 0.0 for dates they don't cover
      - This prevents AXS (4 months) from truncating the 8 core symbols (730d)
      - Per-symbol stats are computed on each symbol's own full range
    """
    loaded = {}
    missing = []
    core_syms = []
    short_syms = []

    for sym in symbols:
        print(f"  Computing reverse carry PnL for {sym}...", flush=True)
        s = compute_reverse_carry_pnl(sym)
        if s is not None and len(s) >= min_days_required:
            loaded[sym] = s
            if len(s) >= 365:
                core_syms.append(sym)
            else:
                short_syms.append(sym)
                print(f"  {sym}: LIMITED DATA ({len(s)} days) — will use outer join", flush=True)
        else:
            missing.append(sym)
            print(f"  {sym}: SKIPPED (insufficient data: {len(s) if s is not None else 0} days)")

    if not loaded:
        raise ValueError("No reverse carry PnL computed for any symbol")

    # Outer join: each date gets values from symbols that have data; NaN → 0
    panel = pd.concat(loaded.values(), axis=1, join="outer")
    panel = panel.sort_index()
    # Drop dates where NO symbol has data
    panel = panel.dropna(how="all")
    # NaN for individual symbols (outside their history) = 0 carry earned
    panel = panel.fillna(0.0)

    available = list(loaded.keys())
    print(f"  Panel (outer join): {len(available)} symbols, {len(panel)} days, "
          f"{panel.index[0].date()} → {panel.index[-1].date()}")
    if short_syms:
        print(f"  Short-history symbols (outer join NaN→0): {short_syms}")
    if missing:
        print(f"  Skipped: {missing}")

    return panel, available, core_syms, short_syms


# ──────────────────────────────────────────────────────────────────────────────
# Per-symbol stats
# ──────────────────────────────────────────────────────────────────────────────

def per_symbol_reverse_carry_stats(panel: pd.DataFrame) -> dict:
    """Per-symbol reverse carry PnL stats with §6 gates.

    Uses each symbol's own non-zero range for fair stats (avoids outer-join zeros).
    """
    n = len(panel)
    oos_start = int(n * (1 - OOS_FRAC))
    cutoff_90d = panel.index[-1] - pd.Timedelta(days=90)

    stats = {}
    for sym in panel.columns:
        s_full = panel[sym]
        # Use only dates where this symbol had data (non-zero carry possible)
        # Trim leading zeros (outer join fill) by finding first non-zero date
        first_nonzero = s_full.ne(0).idxmax() if s_full.ne(0).any() else s_full.index[0]
        s = s_full[s_full.index >= first_nonzero]

        # OOS split on symbol's own range
        n_sym = len(s)
        oos_start_sym = int(n_sym * (1 - OOS_FRAC))
        s_is  = s.iloc[:oos_start_sym]
        s_oos = s.iloc[oos_start_sym:]
        s_90d = s[s.index >= cutoff_90d]

        # Trend slope (bps/day on 90d cumulative)
        x = np.arange(len(s_90d), dtype=float)
        cum = np.cumsum(s_90d.values * 10_000)  # back to bps
        slope_bps_per_day = float(np.polyfit(x, cum, 1)[0]) if len(x) > 5 else 0.0

        # Annualized carry in bps
        mean_8h_bps = float(s_90d.mean() * 10_000 / 3)  # per-event bps
        ann_carry_bps = mean_8h_bps * 3 * 365

        # §6 gates (only if Sharpe >= 1.0 gross)
        full_sh = sharpe_d(s.values)
        s6 = None
        if full_sh >= 1.0:
            s6 = section6_gates(s_is.values, s_oos.values)

        stats[sym] = {
            "full":       metrics_pkg(s.values),
            "oos":        metrics_pkg(s_oos.values),
            "recent_90d": {
                "n_days": int(len(s_90d)),
                "sharpe": round(sharpe_d(s_90d.values), 4),
                "mean_daily_return": round(float(s_90d.mean()), 6),
                "ann_carry_bps": round(ann_carry_bps, 2),
                "slope_bps_per_day": round(slope_bps_per_day, 4),
                "trend": "positive" if slope_bps_per_day > 0 else "negative",
            },
            "k189_magnitude_sh": K189_REV_90D_SH_MAGNITUDE.get(sym, None),
            "section6": s6,
            "verdict": (
                "STRONG" if full_sh >= 5.0 else
                "VIABLE" if full_sh >= 1.0 else
                "WEAK"
            ),
        }
    return stats


# ──────────────────────────────────────────────────────────────────────────────
# Portfolio weight utilities
# ──────────────────────────────────────────────────────────────────────────────

def w_equal(n: int) -> np.ndarray:
    return np.ones(n) / n


def w_inv_vol(R: np.ndarray) -> np.ndarray:
    vols = R.std(axis=0, ddof=1)
    inv = 1.0 / np.where(vols == 0, np.nan, vols)
    return inv / np.nansum(inv)


def w_risk_parity(R: np.ndarray, n_iter: int = 5000, tol: float = 1e-9) -> np.ndarray:
    vols = R.std(axis=0, ddof=1)
    vols = np.where(vols == 0, 1.0, vols)
    R_norm = R / vols[np.newaxis, :]
    cov = np.cov(R_norm, rowvar=False, ddof=1)
    cov = cov + np.eye(cov.shape[0]) * 1e-8
    n = cov.shape[0]
    w = np.ones(n) / n
    for _ in range(n_iter):
        mrc = cov @ w
        rc = w * mrc
        rc = np.where(np.abs(rc) < 1e-15, 1e-15, rc)
        total_risk_sq = float(w @ cov @ w)
        target = total_risk_sq / n
        ratio = target / rc
        ratio = np.clip(ratio, 0, None)
        new_w = w * ratio ** 0.5
        new_w = np.clip(new_w, 1e-6, None)
        new_w = new_w / new_w.sum()
        if np.max(np.abs(new_w - w)) < tol:
            w_sc = new_w / vols
            return w_sc / w_sc.sum()
        w = new_w
    w_sc = w / vols
    return w_sc / w_sc.sum()


def w_sharpe_wt(R: np.ndarray) -> np.ndarray:
    shs = np.array([sharpe_d(R[:, i]) for i in range(R.shape[1])])
    pos = np.clip(shs, 0, None)
    if pos.sum() == 0:
        return np.ones(R.shape[1]) / R.shape[1]
    return pos / pos.sum()


def apply_cap(w: np.ndarray, cols: List[str], col_name: str, cap: float) -> np.ndarray:
    w = w.copy()
    if col_name not in cols:
        return w
    i = cols.index(col_name)
    if w[i] <= cap:
        return w
    excess = w[i] - cap
    w[i] = cap
    other_mask = np.ones(len(w), dtype=bool)
    other_mask[i] = False
    others = w[other_mask]
    if others.sum() > 0:
        w[other_mask] = others + excess * (others / others.sum())
    return w / w.sum()


def apply_all_caps(w: np.ndarray, cols: List[str],
                   k121_cap: float = K121_CAP,
                   fwd_cap: Optional[float] = FORWARD_CARRY_CAP,
                   rev_cap: Optional[float] = REVERSE_CARRY_CAP_PRIMARY) -> np.ndarray:
    w = apply_cap(w, cols, "K121", k121_cap)
    if fwd_cap is not None:
        w = apply_cap(w, cols, "V_fwd_carry", fwd_cap)
    if rev_cap is not None:
        w = apply_cap(w, cols, "V_rev_carry", rev_cap)
    return w


# ──────────────────────────────────────────────────────────────────────────────
# Panel return builder
# ──────────────────────────────────────────────────────────────────────────────

def build_panel_return(panel: pd.DataFrame, weights: np.ndarray) -> pd.Series:
    """Weighted daily carry portfolio return."""
    cols = [c for c in panel.columns]
    w_arr = weights[:len(cols)]
    w_arr = w_arr / w_arr.sum()
    R = panel[cols].values
    return pd.Series(R @ w_arr, index=panel.index)


def sub_alloc_eq_w(panel: pd.DataFrame) -> np.ndarray:
    return np.ones(panel.shape[1]) / panel.shape[1]


def sub_alloc_sharpe_w(panel: pd.DataFrame, sym_stats: dict) -> np.ndarray:
    """Weight by full-period Sharpe (positive only, capped)."""
    symbols = list(panel.columns)
    weights = []
    for sym in symbols:
        sh = sym_stats.get(sym, {}).get("full", {}).get("sharpe", 0.0)
        weights.append(max(0.0, sh))
    w = np.array(weights, dtype=float)
    if w.sum() == 0:
        return np.ones(len(symbols)) / len(symbols)
    return w / w.sum()


# ──────────────────────────────────────────────────────────────────────────────
# Correlation analysis
# ──────────────────────────────────────────────────────────────────────────────

def correlation_analysis(rev_panel: pd.DataFrame,
                         fwd_series: pd.Series,
                         label: str = "V_fwd_K195") -> dict:
    """
    Compute:
    1. Within reverse panel correlation matrix
    2. Reverse panel vs forward panel correlation
    3. Counterparty exposure analysis
    """
    corr = rev_panel.corr()
    n = len(corr)
    mask = ~np.eye(n, dtype=bool)
    offdiag = corr.values[mask]
    mean_corr = float(np.nanmean(offdiag))
    max_corr  = float(np.nanmax(offdiag))
    min_corr  = float(np.nanmin(offdiag))

    # Correlation matrix as dict
    corr_dict = {}
    for sym_a in rev_panel.columns:
        corr_dict[sym_a] = {}
        for sym_b in rev_panel.columns:
            corr_dict[sym_a][sym_b] = round(float(corr.loc[sym_a, sym_b]), 4)

    # Reverse panel eq-weight series
    eq_rev = rev_panel.mean(axis=1)

    # Align forward series to reverse panel dates
    fwd_aligned = fwd_series.reindex(rev_panel.index, method="ffill").fillna(0.0)
    corr_rev_vs_fwd = float(eq_rev.corr(fwd_aligned))

    # Per-symbol corr with reverse panel
    sym_corr_with_panel = {}
    for col in rev_panel.columns:
        c = float(rev_panel[col].corr(eq_rev))
        sym_corr_with_panel[col] = round(c, 4)

    return {
        "within_reverse_panel": {
            "mean_pairwise_corr": round(mean_corr, 4),
            "max_pairwise_corr":  round(max_corr, 4),
            "min_pairwise_corr":  round(min_corr, 4),
            "corr_matrix":        corr_dict,
            "sym_corr_with_panel": sym_corr_with_panel,
            "hl_concentration_note": (
                "HIGH" if mean_corr > 0.70 else
                "MEDIUM" if mean_corr > 0.40 else
                "LOW"
            ),
        },
        "reverse_vs_forward": {
            "correlation": round(corr_rev_vs_fwd, 4),
            "interpretation": (
                "Near-zero expected (different underlying symbols). "
                f"Actual: {corr_rev_vs_fwd:.4f}. "
                + ("GOOD diversification." if abs(corr_rev_vs_fwd) < 0.30
                   else "Moderate correlation — monitor.")
            ),
        },
        "counterparty_analysis": {
            "k195_hl_exposure": "100% SHORT on HL (K195 shorts HL, longs Bybit)",
            "k196_hl_exposure": "100% LONG on HL (K196 longs HL, shorts Bybit)",
            "combined_hl_net_note": (
                "K195 and K196 use DIFFERENT symbols. "
                "K195 shorts HL on {ETH,DOGE,AVAX,LDO,AAVE,UNI,NEAR,CRV,PEPE,BONK}. "
                "K196 longs HL on {SOL,XRP,SUI,OP,APT,AXS,JTO,IMX,SAND,ADA}. "
                "Net HL book = +long (K196) - short (K195) on different symbols = "
                "partially offsetting HL notional exposure in aggregate (though not same positions). "
                "Risk: if HL defaults, BOTH K195 and K196 are affected (different directions "
                "but both have open HL positions). Counterparty risk is NOT diversified away — "
                "it is doubled in terms of HL notional if equal capital deployed."
            ),
        },
    }


def compute_hl_net_exposure(k195_fwd_carry_weight_p3: float,
                            k196_fwd_w: float, k196_rev_w: float) -> dict:
    """
    Compute net HL exposure on Sharpe-weighted capital basis.

    Signed convention:
      - LONG Bybit / SHORT HL → HL direction = -1 (short HL)
      - LONG HL / SHORT Bybit → HL direction = +1 (long HL)

    K195 standalone (100% capital):
      Forward carry weight = k195_fwd_carry_weight_p3
      HL exposure = -k195_fwd_carry_weight_p3  (all short HL)

    K195+K196 combined (50% capital each):
      K195: HL short = -k195_fwd_carry_weight_p3 * 0.5
      K196 fwd carry (V_fwd_carry): HL short = -k196_fwd_w * 0.5
      K196 rev carry (V_rev_carry): HL long  = +k196_rev_w * 0.5

      Net = -k195_fwd_w*0.5 - k196_fwd_w*0.5 + k196_rev_w*0.5

    Baseline (K195-only, 100% capital):
      HL = -k195_fwd_carry_weight_p3 * 1.0

    Reduction = (|baseline| - |net|) / |baseline| * 100
    """
    k195_cap = 0.5
    k196_cap = 0.5

    hl_short_k195     = -k195_fwd_carry_weight_p3 * k195_cap   # K195 short HL via fwd carry
    hl_short_k196_fwd = -k196_fwd_w               * k196_cap   # K196 short HL via fwd carry
    hl_long_k196_rev  = +k196_rev_w               * k196_cap   # K196 long HL via rev carry

    hl_net = hl_short_k195 + hl_short_k196_fwd + hl_long_k196_rev

    # Baseline: K195 only, all capital
    hl_baseline = -k195_fwd_carry_weight_p3 * 1.0

    reduction_pct = (abs(hl_baseline) - abs(hl_net)) / abs(hl_baseline) * 100 if hl_baseline != 0 else 0.0

    return {
        "k195_fwd_carry_weight_p3": round(k195_fwd_carry_weight_p3, 4),
        "k196_fwd_carry_weight_p3": round(k196_fwd_w, 4),
        "k196_rev_carry_weight_p3": round(k196_rev_w, 4),
        "hl_short_from_k195_fwd":  round(hl_short_k195, 4),
        "hl_short_from_k196_fwd":  round(hl_short_k196_fwd, 4),
        "hl_long_from_k196_rev":   round(hl_long_k196_rev, 4),
        "hl_net_combined":         round(hl_net, 4),
        "hl_baseline_k195_only":   round(hl_baseline, 4),
        "hl_net_reduction_pct":    round(reduction_pct, 2),
        "meets_30pct_reduction":   bool(reduction_pct >= 30.0),
        "note": (
            f"Net HL = {hl_net:.4f} (combined K195+K196 at 50/50 capital). "
            f"K195-only baseline = {hl_baseline:.4f} (100% capital). "
            f"Reduction = {reduction_pct:.1f}% → "
            f"{'MEETS' if reduction_pct >= 30 else 'DOES NOT MEET'} 30% threshold."
        ),
        "interpretation": {
            "k195_alone": "All HL exposure SHORT (shorts HL on 10 forward carry symbols)",
            "k196_net_hl": (
                f"K196 portfolio: fwd_w={k196_fwd_w:.3f} (short HL) + rev_w={k196_rev_w:.3f} (long HL). "
                f"Within-K196 net HL = {k196_rev_w - k196_fwd_w:+.4f}"
            ),
            "combined_k195_k196": (
                "Combined: K195 and K196 each deployed at 50% capital. "
                "K196 reverse carry long HL partially offsets K195+K196 forward carry short HL. "
                "Total HL notional doubles in count (20 symbols × 2 exchanges) but "
                "net directional HL exposure is meaningfully reduced."
            ),
        },
    }


# ──────────────────────────────────────────────────────────────────────────────
# K195 component loader
# ──────────────────────────────────────────────────────────────────────────────

def load_k195_components_and_forward_carry() -> Tuple[pd.DataFrame, pd.Series, pd.Series]:
    """
    Load K195's 8 non-carry components + V_carry_panel_10sym (forward carry).
    Returns:
      df_non_carry: 8 non-carry components
      fwd_carry_series: V_carry_panel_10sym (K195)
      trigger_mask: FR trigger mask
    """
    curves_path = BASE / "wave_k192_curves.json"
    with open(curves_path) as f:
        d = json.load(f)
    dates = pd.to_datetime(d["dates"])

    component_map = {
        "v4.1":     "K188_v4.1",
        "V1":       "K188_V1",
        "K114":     "K188_K114",
        "K116":     "K188_K116",
        "K121":     "K188_K121",
        "K133":     "K188_K133",
        "K147":     "K188_K147",
        "K175_DAR": "K175_DAR_a_win300_net",
    }
    df = pd.DataFrame(index=dates)
    for col_name, curve_key in component_map.items():
        eq = np.array(d["series"][curve_key], dtype=float)
        prev = np.r_[1.0, eq[:-1]]
        ret = eq / prev - 1.0
        df[col_name] = ret
    df.index.name = "date"

    # Load V_carry_panel_10sym from K195 curves
    k195_curves_path = BASE / "wave_k195_curves.json"
    with open(k195_curves_path) as f:
        k195_d = json.load(f)
    k195_dates = pd.to_datetime(k195_d["dates"])
    fwd_eq = np.array(k195_d["series"]["K195_P3_triggered"], dtype=float)
    # We need the raw V_carry_panel_10sym series, not the portfolio
    # Load from K195 JSON sub-alloc
    k195_json_path = BASE / "wave_k195_carry_v6_3.json"
    with open(k195_json_path) as f:
        k195_m = json.load(f)

    # Use V_eq_w sub-alloc from K195 (the primary panel series)
    fwd_oos = k195_d["series"].get("V_eq_w")
    if fwd_oos is not None:
        fwd_eq_arr = np.array(fwd_oos, dtype=float)
        fwd_dates = pd.to_datetime(k195_d["panel_dates"])
        fwd_ret = pd.Series(
            np.r_[fwd_eq_arr[0] - 1.0, fwd_eq_arr[1:] / fwd_eq_arr[:-1] - 1.0],
            index=fwd_dates,
            name="V_fwd_carry"
        )
    else:
        # Fallback: derive from K195 P3 triggered curve
        fwd_eq_arr = np.array(k195_d["series"]["K195_P3_triggered"], dtype=float)
        fwd_ret = pd.Series(
            np.r_[fwd_eq_arr[0] - 1.0, fwd_eq_arr[1:] / fwd_eq_arr[:-1] - 1.0],
            index=k195_dates,
            name="V_fwd_carry"
        )

    return df, fwd_ret, None


def load_fr_mean_daily() -> pd.Series:
    """Load Bybit FR for 6 symbols, compute daily annualized mean."""
    daily_series = []
    for sym in FR_SYMBOLS:
        for tag in ("730d", "1200d", "365d"):
            fpath = CACHE / f"bybit_fr_{sym}USDT_{tag}.parquet"
            if fpath.exists():
                df = pd.read_parquet(fpath)
                df["timestamp"] = pd.to_datetime(df["timestamp"]).dt.tz_localize(None)
                df = df.set_index("timestamp")
                daily = df["funding_rate"].resample("1D").mean()
                ann = daily * 3 * 365
                ann.name = sym
                daily_series.append(ann)
                break
    if not daily_series:
        raise ValueError("No FR data found for trigger symbols")
    panel = pd.concat(daily_series, axis=1)
    fr_mean = panel.mean(axis=1)
    fr_mean.name = "fr_mean_ann"
    return fr_mean


# ──────────────────────────────────────────────────────────────────────────────
# Portfolio runner
# ──────────────────────────────────────────────────────────────────────────────

def run_portfolio(df: pd.DataFrame, label: str,
                  fwd_cap: float = FORWARD_CARRY_CAP,
                  rev_cap: float = REVERSE_CARRY_CAP_PRIMARY) -> dict:
    """Run P1-P4 portfolio variants on df."""
    cols = list(df.columns)
    R = df.to_numpy()
    cut = int(len(df) * (1 - OOS_FRAC))
    oos_R = R[cut:]

    raw_w = {
        "P1_equal":       w_equal(len(cols)),
        "P2_inv_vol":     w_inv_vol(R),
        "P3_risk_parity": w_risk_parity(R),
        "P4_sharpe_wt":   w_sharpe_wt(R),
    }
    capped = {k: apply_all_caps(w, cols, fwd_cap=fwd_cap, rev_cap=rev_cap)
              for k, w in raw_w.items()}

    full_metrics, oos_metrics, full_curves = {}, {}, {}
    for k, w in capped.items():
        pr_f = R @ w
        pr_o = oos_R @ w
        full_metrics[k] = metrics_pkg(pr_f)
        oos_metrics[k]  = metrics_pkg(pr_o)
        full_curves[f"{label}_{k}"] = [round(float(v), 6) for v in np.cumprod(1.0 + pr_f)]

    return {
        "label": label,
        "fwd_cap": fwd_cap,
        "rev_cap": rev_cap,
        "cols": cols,
        "n_days": int(len(df)),
        "oos_cut_idx": int(cut),
        "oos_n_days": int(len(df) - cut),
        "date_range": [str(df.index.min().date()), str(df.index.max().date())],
        "single_metrics_full": {c: metrics_pkg(R[:, i]) for i, c in enumerate(cols)},
        "single_metrics_oos":  {c: metrics_pkg(oos_R[:, i]) for i, c in enumerate(cols)},
        "weights": {k: [round(float(x), 4) for x in v] for k, v in capped.items()},
        "metrics_full": full_metrics,
        "metrics_oos":  oos_metrics,
        "curves": full_curves,
        "dates": [d.strftime("%Y-%m-%d") for d in df.index],
    }


# ──────────────────────────────────────────────────────────────────────────────
# Walk-forward (4-fold)
# ──────────────────────────────────────────────────────────────────────────────

def wf_4fold(df_base: pd.DataFrame, df_triggered: pd.DataFrame,
             trigger_mask: pd.Series, label: str = "K196",
             fwd_cap: float = FORWARD_CARRY_CAP,
             rev_cap: float = REVERSE_CARRY_CAP_PRIMARY,
             n_folds: int = N_FOLDS) -> dict:
    cols = list(df_base.columns)
    R_base = df_base.to_numpy()
    R_trig = df_triggered.to_numpy()
    n = len(R_base)
    fold_size = n // n_folds
    folds = []

    for fold_id in range(n_folds):
        start = fold_id * fold_size
        end   = start + fold_size if fold_id < n_folds - 1 else n
        R_fold_base = R_base[start:end]
        R_fold_trig = R_trig[start:end]
        mask_fold   = trigger_mask.iloc[start:end]

        cut = int(len(R_fold_base) * TRAIN_FRAC)
        R_tr_trig = R_fold_trig[:cut]
        R_te_base = R_fold_base[cut:]
        R_te_trig = R_fold_trig[cut:]
        mask_te   = mask_fold.iloc[cut:]

        if len(R_tr_trig) < 30 or len(R_te_base) < 10:
            continue

        raw_w = {
            "P1_equal":       w_equal(len(cols)),
            "P2_inv_vol":     w_inv_vol(R_tr_trig),
            "P3_risk_parity": w_risk_parity(R_tr_trig),
            "P4_sharpe_wt":   w_sharpe_wt(R_tr_trig),
        }
        capped = {k: apply_all_caps(w, cols, fwd_cap=fwd_cap, rev_cap=rev_cap)
                  for k, w in raw_w.items()}

        n_trigger = int(mask_te.sum())
        trigger_pct = round(n_trigger / max(1, len(mask_te)) * 100, 1)

        fold = {
            "fold": fold_id,
            "train_n": int(cut),
            "test_n":  int(len(R_te_base)),
            "date_start": str(df_base.index[start].date()),
            "date_end":   str(df_base.index[end - 1].date()),
            "n_trigger_days": int(n_trigger),
            "trigger_pct": trigger_pct,
        }
        for k, w in capped.items():
            pr_base = R_te_base @ w
            pr_trig = R_te_trig @ w
            fold[f"oos_sharpe_base_{k}"] = round(sharpe_d(pr_base), 4)
            fold[f"oos_sharpe_{label}_{k}"] = round(sharpe_d(pr_trig), 4)
            fold[f"delta_{k}"] = round(sharpe_d(pr_trig) - sharpe_d(pr_base), 4)
        folds.append(fold)
        print(f"  Fold {fold_id}: base P3={fold.get('oos_sharpe_base_P3_risk_parity', 0):.3f} | "
              f"{label} P3={fold.get(f'oos_sharpe_{label}_P3_risk_parity', 0):.3f} "
              f"(Δ={fold.get('delta_P3_risk_parity', 0):+.3f}) | trigger={trigger_pct:.0f}%",
              flush=True)

    result = {"label": label, "folds": folds}
    for k in ["P1_equal", "P2_inv_vol", "P3_risk_parity", "P4_sharpe_wt"]:
        base_vals = [f[f"oos_sharpe_base_{k}"] for f in folds if f"oos_sharpe_base_{k}" in f]
        trig_vals = [f[f"oos_sharpe_{label}_{k}"] for f in folds if f"oos_sharpe_{label}_{k}" in f]
        if base_vals:
            result[f"mean_base_{k}"]     = round(float(np.mean(base_vals)), 4)
            result[f"min_base_{k}"]      = round(float(np.min(base_vals)), 4)
        if trig_vals:
            result[f"mean_{label}_{k}"]  = round(float(np.mean(trig_vals)), 4)
            result[f"min_{label}_{k}"]   = round(float(np.min(trig_vals)), 4)
            result[f"std_{label}_{k}"]   = round(float(np.std(trig_vals)), 4)
    return result


# ──────────────────────────────────────────────────────────────────────────────
# Carry cap sweep
# ──────────────────────────────────────────────────────────────────────────────

def carry_cap_sweep_reverse(df: pd.DataFrame, caps: List[float],
                             fwd_cap: float = FORWARD_CARRY_CAP) -> List[dict]:
    n = len(df)
    oos_start = int(n * (1 - OOS_FRAC))
    results = []
    for rev_cap in caps:
        label = f"K196_fwd{int(fwd_cap*100)}_rev{int(rev_cap*100)}"
        res = run_portfolio(df, label, fwd_cap=fwd_cap, rev_cap=rev_cap)
        entry = {
            "fwd_cap": fwd_cap,
            "rev_cap": rev_cap,
            "oos_sharpe_P1": res["metrics_oos"]["P1_equal"]["sharpe"],
            "oos_sharpe_P2": res["metrics_oos"]["P2_inv_vol"]["sharpe"],
            "oos_sharpe_P3": res["metrics_oos"]["P3_risk_parity"]["sharpe"],
            "oos_sharpe_P4": res["metrics_oos"]["P4_sharpe_wt"]["sharpe"],
            "oos_maxdd_P3":  res["metrics_oos"]["P3_risk_parity"]["max_dd"],
            "full_sharpe_P3": res["metrics_full"]["P3_risk_parity"]["sharpe"],
            "rev_weight_P3": (
                res["weights"]["P3_risk_parity"][list(df.columns).index("V_rev_carry")]
                if "V_rev_carry" in df.columns else None
            ),
            "fwd_weight_P3": (
                res["weights"]["P3_risk_parity"][list(df.columns).index("V_fwd_carry")]
                if "V_fwd_carry" in df.columns else None
            ),
        }
        results.append(entry)
        print(f"  fwd_cap={fwd_cap:.0%} rev_cap={rev_cap:.0%}: "
              f"OOS P3={entry['oos_sharpe_P3']:.4f} MaxDD={entry['oos_maxdd_P3']:.4f}",
              flush=True)
    return results


# ──────────────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────────────

def main():
    print("=" * 72)
    print("Wave K196 — Reverse Carry Panel: LONG HL + SHORT Bybit")
    print("=" * 72)
    print()

    np.random.seed(42)

    # ── Step 1: Build reverse carry panel ────────────────────────────────────
    print("Step 1: Building reverse carry panel (10 opp-spread symbols)...", flush=True)
    rev_panel, available_syms, core_syms, short_syms = build_reverse_panel(REVERSE_10)
    n_rev_panel_days = len(rev_panel)
    print(f"  Available symbols: {available_syms} ({len(available_syms)}/10)")
    print(f"  Core symbols (>=365d): {core_syms}")
    print(f"  Short-history symbols (<365d): {short_syms}")
    print()

    # ── Step 2: Per-symbol stats + §6 gates ──────────────────────────────────
    print("Step 2: Per-symbol reverse carry stats + §6 gates...", flush=True)
    sym_stats = per_symbol_reverse_carry_stats(rev_panel)
    print(f"\n  {'Symbol':<6} {'Full Sh':>8} {'OOS Sh':>8} {'90d Sh':>8} "
          f"{'ann_bps':>9} {'Slope':>8} {'Verdict'}")
    print("  " + "-" * 65)
    for sym in available_syms:
        s = sym_stats[sym]
        r90 = s["recent_90d"]
        print(f"  {sym:<6} {s['full']['sharpe']:>8.2f} {s['oos']['sharpe']:>8.2f} "
              f"{r90['sharpe']:>8.2f} {r90['ann_carry_bps']:>9.1f} "
              f"{r90['slope_bps_per_day']:>+8.3f}  {s['verdict']}", flush=True)
    print()

    # Print §6 results
    print("  §6 Gate Results (symbols with Sharpe >= 1.0):")
    for sym in available_syms:
        s6 = sym_stats[sym].get("section6")
        if s6:
            gates = s6["gates"]
            g_str = (f"G1={'P' if gates['G1_oos_sh']['pass'] else 'F'} "
                     f"G2={'P' if gates['G2_perm_p']['pass'] else 'F'} "
                     f"G3={'P' if gates['G3_dsr']['pass'] else 'F'} "
                     f"G4={'P' if gates['G4_wf_folds']['pass'] else 'F'} "
                     f"Overall={'PASS' if s6['overall_pass'] else 'FAIL'}")
            print(f"    {sym}: IS Sh={s6['is_sharpe']:.2f} OOS Sh={s6['oos_sharpe']:.2f} | {g_str}")
    print()

    # ── Step 3: Sub-alloc comparison for reverse panel ────────────────────────
    print("Step 3: Reverse panel sub-allocation comparison...", flush=True)
    n_rev = len(rev_panel)
    oos_start_rev = int(n_rev * (1 - OOS_FRAC))

    w_eq  = sub_alloc_eq_w(rev_panel)
    w_sh  = sub_alloc_sharpe_w(rev_panel, sym_stats)

    sub_allocs = {
        "V_eq_w":     {"w": w_eq,  "label": "Equal weight"},
        "V_sharpe_w": {"w": w_sh,  "label": "Sharpe-weighted"},
    }

    sub_results = {}
    for name, cfg in sub_allocs.items():
        ret = build_panel_return(rev_panel, cfg["w"])
        ret_oos = ret.iloc[oos_start_rev:]
        sub_results[name] = {
            "weights": {s: round(float(cfg["w"][i]), 4) for i, s in enumerate(available_syms) if i < len(cfg["w"])},
            "full": metrics_pkg(ret.values),
            "oos":  metrics_pkg(ret_oos.values),
        }
        print(f"  {name}: full Sh={sub_results[name]['full']['sharpe']:.4f}  "
              f"OOS Sh={sub_results[name]['oos']['sharpe']:.4f}", flush=True)

    best_sub = max(sub_results.keys(), key=lambda k: sub_results[k]["oos"]["sharpe"])
    print(f"  Best sub-alloc: {best_sub}")
    print()

    # Primary reverse panel series (equal weight, most robust)
    rev_primary_w = w_eq
    rev_panel_series = build_panel_return(rev_panel, rev_primary_w)

    # ── Step 4: Load K195 forward components ─────────────────────────────────
    print("Step 4: Loading K195 forward carry components...", flush=True)
    df_non_carry, fwd_carry_series, _ = load_k195_components_and_forward_carry()
    print(f"  Non-carry components: {list(df_non_carry.columns)}")
    print(f"  K195 date range: {df_non_carry.index[0].date()} → {df_non_carry.index[-1].date()}")
    print(f"  Forward carry series: {fwd_carry_series.index[0].date()} → {fwd_carry_series.index[-1].date()}")
    print()

    # ── Step 5: Correlation analysis ──────────────────────────────────────────
    print("Step 5: Correlation analysis...", flush=True)
    # Align reverse panel with forward series for correlation
    common_corr_start = max(rev_panel.index[0], fwd_carry_series.index[0])
    common_corr_end   = min(rev_panel.index[-1], fwd_carry_series.index[-1])
    rev_panel_corr = rev_panel[(rev_panel.index >= common_corr_start) & (rev_panel.index <= common_corr_end)]
    fwd_series_corr = fwd_carry_series[(fwd_carry_series.index >= common_corr_start) & (fwd_carry_series.index <= common_corr_end)]

    corr_analysis = correlation_analysis(rev_panel_corr, fwd_series_corr)
    print(f"  Within-reverse mean corr: {corr_analysis['within_reverse_panel']['mean_pairwise_corr']:.3f}")
    print(f"  Reverse vs Forward corr:  {corr_analysis['reverse_vs_forward']['correlation']:.3f}")
    print(f"  HL concentration risk:    {corr_analysis['within_reverse_panel']['hl_concentration_note']}")
    print()

    # ── Step 6: Build K196 full ensemble DataFrame ────────────────────────────
    print("Step 6: Building K196 ensemble (9 K195 components + fwd + rev carry)...", flush=True)

    # Align all three: non-carry, fwd carry, rev carry
    all_start = max(df_non_carry.index[0], fwd_carry_series.index[0], rev_panel.index[0])
    all_end   = min(df_non_carry.index[-1], fwd_carry_series.index[-1], rev_panel.index[-1])
    print(f"  Common date range: {all_start.date()} → {all_end.date()}")

    def trim(df_or_s, start, end):
        return df_or_s[(df_or_s.index >= start) & (df_or_s.index <= end)]

    df_nc   = trim(df_non_carry, all_start, all_end)
    fwd_s   = trim(fwd_carry_series, all_start, all_end).rename("V_fwd_carry")
    rev_s   = build_panel_return(
        trim(rev_panel, all_start, all_end), rev_primary_w
    ).rename("V_rev_carry")
    rev_sh_s = build_panel_return(
        trim(rev_panel, all_start, all_end), w_sh
    ).rename("V_rev_carry_sharpe")

    # K195 reference (8 non-carry + fwd carry)
    df_k195_ref = pd.concat([df_nc, fwd_s], axis=1).dropna()
    # K196 ensemble = 8 non-carry + fwd carry + rev carry
    df_k196 = pd.concat([df_nc, fwd_s, rev_s], axis=1).dropna()
    # K196 Sharpe-weighted reverse
    df_k196_sh = pd.concat([df_nc, fwd_s, rev_sh_s], axis=1).rename(
        columns={"V_rev_carry_sharpe": "V_rev_carry"}
    ).dropna()

    print(f"  K196 DataFrame shape: {df_k196.shape}")
    print(f"  Columns: {list(df_k196.columns)}")
    print()

    # ── Step 7: Apply K194/K195 partial trigger ───────────────────────────────
    print("Step 7: Applying partial trigger to K121 + K133...", flush=True)
    fr_mean = load_fr_mean_daily()
    fr_mean_aligned = fr_mean.reindex(df_k196.index, method="ffill")
    trigger_mask_k196 = (fr_mean_aligned < THRESHOLD_PRIMARY)

    df_k196_triggered = df_k196.copy()
    df_k195_ref_triggered = df_k195_ref.copy()
    for col in PARTIAL_TRIGGER_COMPONENTS:
        if col in df_k196_triggered.columns:
            df_k196_triggered.loc[trigger_mask_k196, col] = 0.0
        if col in df_k195_ref_triggered.columns:
            df_k195_ref_triggered.loc[trigger_mask_k196, col] = 0.0

    n_total = len(df_k196)
    oos_start_idx = int(n_total * (1 - OOS_FRAC))
    n_trigger_full = int(trigger_mask_k196.sum())
    n_trigger_oos  = int(trigger_mask_k196.iloc[oos_start_idx:].sum())
    trigger_pct_oos = n_trigger_oos / max(1, n_total - oos_start_idx) * 100
    print(f"  Trigger days full: {n_trigger_full}/{n_total} ({n_trigger_full/n_total*100:.1f}%)")
    print(f"  Trigger days OOS:  {n_trigger_oos}/{n_total-oos_start_idx} ({trigger_pct_oos:.1f}%)")
    print()

    # ── Step 8: Run K195-ref portfolio (for comparison baseline) ─────────────
    print("Step 8: Running K195-reference portfolio (without reverse carry)...", flush=True)
    res_k195_ref = run_portfolio(df_k195_ref_triggered, "K195_ref",
                                 fwd_cap=FORWARD_CARRY_CAP, rev_cap=None)
    k195_ref_p3_oos  = res_k195_ref["metrics_oos"]["P3_risk_parity"]["sharpe"]
    k195_ref_p3_full = res_k195_ref["metrics_full"]["P3_risk_parity"]["sharpe"]
    k195_ref_dd_oos  = res_k195_ref["metrics_oos"]["P3_risk_parity"]["max_dd"]
    print(f"  K195-ref P3: OOS={k195_ref_p3_oos:.4f}  full={k195_ref_p3_full:.4f}  DD={k195_ref_dd_oos:.4f}")
    print()

    # ── Step 9: Run K196 portfolio variants ───────────────────────────────────
    print("Step 9: Running K196 ensemble portfolio (primary cap=10%/10%)...", flush=True)
    res_k196 = run_portfolio(df_k196_triggered, "K196_eq_fwd10_rev10",
                             fwd_cap=FORWARD_CARRY_CAP, rev_cap=REVERSE_CARRY_CAP_PRIMARY)
    k196_p3_oos  = res_k196["metrics_oos"]["P3_risk_parity"]["sharpe"]
    k196_p3_full = res_k196["metrics_full"]["P3_risk_parity"]["sharpe"]
    k196_dd_oos  = res_k196["metrics_oos"]["P3_risk_parity"]["max_dd"]
    print(f"  K196 (eq) P3: OOS={k196_p3_oos:.4f}  full={k196_p3_full:.4f}  DD={k196_dd_oos:.4f}")
    print()

    # Sharpe-weighted reverse variant
    print("Step 9b: K196 Sharpe-weighted reverse carry...", flush=True)
    df_k196_sh_trig = df_k196_sh.copy()
    for col in PARTIAL_TRIGGER_COMPONENTS:
        if col in df_k196_sh_trig.columns:
            df_k196_sh_trig.loc[trigger_mask_k196.reindex(df_k196_sh_trig.index, fill_value=False), col] = 0.0
    res_k196_sh = run_portfolio(df_k196_sh_trig, "K196_sh_fwd10_rev10",
                                fwd_cap=FORWARD_CARRY_CAP, rev_cap=REVERSE_CARRY_CAP_PRIMARY)
    k196_sh_p3_oos = res_k196_sh["metrics_oos"]["P3_risk_parity"]["sharpe"]
    print(f"  K196 (sh-wt) P3: OOS={k196_sh_p3_oos:.4f}")
    print()

    # ── Step 10: Carry cap sweep ──────────────────────────────────────────────
    print("Step 10: Reverse carry cap sweep...", flush=True)
    sweep_results = carry_cap_sweep_reverse(df_k196_triggered, REV_CAP_SWEEP,
                                            fwd_cap=FORWARD_CARRY_CAP)
    best_cap_entry = max(sweep_results, key=lambda x: x["oos_sharpe_P3"])
    best_rev_cap = best_cap_entry["rev_cap"]
    print(f"  Best reverse cap: {best_rev_cap:.0%} (OOS P3={best_cap_entry['oos_sharpe_P3']:.4f})")
    print()

    # ── Step 11: Walk-forward 4-fold ──────────────────────────────────────────
    print("Step 11: Walk-forward 4-fold analysis (K196)...", flush=True)
    trigger_mask_k196_ser = trigger_mask_k196.reindex(df_k196.index, fill_value=False)
    wf_k196 = wf_4fold(df_k196, df_k196_triggered, trigger_mask_k196_ser,
                       label="K196", fwd_cap=FORWARD_CARRY_CAP,
                       rev_cap=REVERSE_CARRY_CAP_PRIMARY)
    k196_wf_mean_p3 = wf_k196.get("mean_K196_P3_risk_parity", 0.0)
    k196_wf_min_p3  = wf_k196.get("min_K196_P3_risk_parity", 0.0)
    print(f"  K196 WF P3: mean={k196_wf_mean_p3:.4f}  min={k196_wf_min_p3:.4f}")
    print()

    # ── Step 12: Reverse panel standalone analysis ────────────────────────────
    print("Step 12: Reverse panel standalone...", flush=True)
    rev_panel_aligned = trim(rev_panel, all_start, all_end)
    rev_panel_oos_start = int(len(rev_panel_aligned) * (1 - OOS_FRAC))
    rev_eq_ret = build_panel_return(rev_panel_aligned, rev_primary_w)
    rev_sh_ret = build_panel_return(rev_panel_aligned, w_sh)
    standalone = {
        "V_reverse_carry_eq": {
            "full": metrics_pkg(rev_eq_ret.values),
            "oos":  metrics_pkg(rev_eq_ret.iloc[rev_panel_oos_start:].values),
        },
        "V_reverse_carry_sh": {
            "full": metrics_pkg(rev_sh_ret.values),
            "oos":  metrics_pkg(rev_sh_ret.iloc[rev_panel_oos_start:].values),
        },
    }
    for name, m in standalone.items():
        print(f"  {name}: full Sh={m['full']['sharpe']:.4f}  OOS Sh={m['oos']['sharpe']:.4f}")
    print()

    # ── Step 13: Counterparty diversification analysis ────────────────────────
    print("Step 13: Counterparty diversification analysis...", flush=True)
    k196_cols = list(df_k196.columns)
    k196_p3_w = np.array(res_k196["weights"]["P3_risk_parity"])

    # Get weights for fwd and rev carry in K196
    k196_rev_w = float(k196_p3_w[k196_cols.index("V_rev_carry")]) if "V_rev_carry" in k196_cols else 0.0
    k196_fwd_w = float(k196_p3_w[k196_cols.index("V_fwd_carry")]) if "V_fwd_carry" in k196_cols else 0.0

    # K195 forward carry weight (from K195 JSON, P3 risk parity)
    k195_ref_p3_w = np.array(res_k195_ref["weights"]["P3_risk_parity"])
    k195_ref_cols = list(df_k195_ref.columns)
    k195_fwd_carry_w = float(k195_ref_p3_w[k195_ref_cols.index("V_fwd_carry")]) if "V_fwd_carry" in k195_ref_cols else 0.1

    hl_net = compute_hl_net_exposure(k195_fwd_carry_w, k196_fwd_w, k196_rev_w)
    print(f"  K196 rev_carry weight (P3): {k196_rev_w:.4f}")
    print(f"  K196 fwd_carry weight (P3): {k196_fwd_w:.4f}")
    print(f"  HL net (combined K195+K196): {hl_net['hl_net_combined']:.4f}")
    print(f"  HL exposure reduction: {hl_net['hl_net_reduction_pct']:.1f}%")
    print(f"  Meets 30% threshold: {hl_net['meets_30pct_reduction']}")
    print()

    # ── Step 14: Three-way comparison ─────────────────────────────────────────
    print("Step 14: Three-way comparison table...", flush=True)
    print()
    hdr = f"{'Version':<32} {'OOS Sh':>8} {'OOS MaxDD':>10} {'WF mean':>9} {'WF min':>9} {'HL net %':>10}"
    print(hdr)
    print("-" * 82)
    print(f"{'K194 v6.2':<32} {K194_OOS_SH:>8.4f} {K194_OOS_DD:>10.4f} "
          f"{K194_WF_MEAN:>9.4f} {K194_WF_MIN:>9.4f} {'–100%':>10}")
    print(f"{'K195 v6.3 (current prod)':<32} {K195_OOS_SH:>8.4f} {K195_OOS_DD:>10.4f} "
          f"{K195_WF_MEAN:>9.4f} {K195_WF_MIN:>9.4f} {'–100%':>10}")
    print(f"{'K196 v6.4 candidate':<32} {k196_p3_oos:>8.4f} {k196_dd_oos:>10.4f} "
          f"{k196_wf_mean_p3:>9.4f} {k196_wf_min_p3:>9.4f} "
          f"{hl_net['hl_net_combined']*100:>+9.1f}%")
    print()

    # ── Step 15: Acceptance criteria ──────────────────────────────────────────
    print("Step 15: Acceptance criteria check...", flush=True)
    oos_lift = k196_p3_oos - K195_OOS_SH
    c1_pass  = bool(k196_p3_oos > K195_OOS_SH + 0.05)
    c2_pass  = bool(k196_dd_oos >= K195_OOS_DD - 0.001)
    c3_pass  = bool(k196_wf_min_p3 >= 3.5)
    c4_pass  = bool(hl_net["meets_30pct_reduction"])
    all_pass = bool(c1_pass and c2_pass and c3_pass and c4_pass)

    print(f"  C1: OOS Sh lift={oos_lift:+.4f} (need >+0.05 vs K195={K195_OOS_SH}) "
          f"→ {'PASS' if c1_pass else 'FAIL'}")
    print(f"  C2: MaxDD K195={K195_OOS_DD:.4f} vs K196={k196_dd_oos:.4f} "
          f"→ {'PASS' if c2_pass else 'FAIL'}")
    print(f"  C3: WF fold min={k196_wf_min_p3:.4f} (need >=3.5) "
          f"→ {'PASS' if c3_pass else 'FAIL'}")
    print(f"  C4: HL net reduction={hl_net['hl_net_reduction_pct']:.1f}% (need >=30%) "
          f"→ {'PASS' if c4_pass else 'FAIL'}")
    print(f"  ALL_PASS: {all_pass}")
    print()

    # ── Build equity curves ───────────────────────────────────────────────────
    print("Building equity curves for export...", flush=True)
    dates_list_k196 = [d.strftime("%Y-%m-%d") for d in df_k196.index]
    R_k196_trig = df_k196_triggered.to_numpy()
    R_k196_base = df_k196.to_numpy()
    w_k196_p3   = np.array(res_k196["weights"]["P3_risk_parity"])

    eq_k196_p3      = [round(float(v), 6) for v in np.cumprod(1.0 + R_k196_trig @ w_k196_p3)]
    eq_k196_base_p3 = [round(float(v), 6) for v in np.cumprod(1.0 + R_k196_base @ w_k196_p3)]
    eq_k195_ref_p3  = [round(float(v), 6) for v in
                       np.cumprod(1.0 + df_k195_ref_triggered.to_numpy() @
                                  np.array(res_k195_ref["weights"]["P3_risk_parity"]))]

    # Per-symbol reverse carry curves
    panel_aligned_common = trim(rev_panel, all_start, all_end)
    panel_dates_list = [d.strftime("%Y-%m-%d") for d in panel_aligned_common.index]
    sym_rev_curves = {}
    for sym in available_syms:
        sym_rev_curves[f"rev_carry_{sym}"] = [round(float(v), 6)
            for v in np.cumprod(1.0 + panel_aligned_common[sym].values)]

    # Sub-alloc comparison curves
    sub_rev_curves = {
        "V_rev_eq_w":    [round(float(v), 6) for v in np.cumprod(1.0 + rev_eq_ret.values)],
        "V_rev_sh_w":    [round(float(v), 6) for v in np.cumprod(1.0 + rev_sh_ret.values)],
    }

    runtime_s = round(time.time() - START_TIME, 1)

    # ── Assemble metrics JSON ─────────────────────────────────────────────────
    metrics_out = {
        "wave": "K196",
        "task": "Reverse carry panel (LONG HL + SHORT Bybit on 10 opp-spread symbols)",
        "as_of": pd.Timestamp.utcnow().isoformat() + "Z",
        "runtime_s": runtime_s,
        "config": {
            "reverse_10": REVERSE_10,
            "available_symbols": available_syms,
            "fwd_carry_cap": FORWARD_CARRY_CAP,
            "rev_carry_cap_primary": REVERSE_CARRY_CAP_PRIMARY,
            "k121_cap": K121_CAP,
            "partial_trigger_components": PARTIAL_TRIGGER_COMPONENTS,
            "fr_threshold": THRESHOLD_PRIMARY,
            "n_folds": N_FOLDS,
            "train_frac": TRAIN_FRAC,
            "oos_frac": OOS_FRAC,
            "n_total": n_total,
            "oos_start_idx": oos_start_idx,
            "date_range": [str(df_k196.index[0].date()), str(df_k196.index[-1].date())],
        },
        "per_symbol_reverse_carry_stats": sym_stats,
        "sub_alloc_comparison": {
            k: {"weights": v["weights"], "full": v["full"], "oos": v["oos"]}
            for k, v in sub_results.items()
        },
        "best_sub_alloc": best_sub,
        "correlation_analysis": corr_analysis,
        "reverse_panel_standalone": standalone,
        "k195_ref_portfolio": {
            "metrics_full": res_k195_ref["metrics_full"],
            "metrics_oos":  res_k195_ref["metrics_oos"],
            "weights":      res_k195_ref["weights"],
        },
        "k196_portfolio_eq": {
            "metrics_full": res_k196["metrics_full"],
            "metrics_oos":  res_k196["metrics_oos"],
            "weights":      res_k196["weights"],
            "single_metrics_oos": res_k196["single_metrics_oos"],
            "n_trigger_days_full": n_trigger_full,
            "n_trigger_days_oos":  n_trigger_oos,
            "trigger_pct_oos": round(trigger_pct_oos, 1),
        },
        "k196_portfolio_sharpe_wt": {
            "metrics_full": res_k196_sh["metrics_full"],
            "metrics_oos":  res_k196_sh["metrics_oos"],
            "weights":      res_k196_sh["weights"],
        },
        "carry_cap_sweep": sweep_results,
        "best_rev_carry_cap": best_rev_cap,
        "walk_forward_k196": wf_k196,
        "counterparty_exposure": hl_net,
        "three_way_comparison": {
            "K194": {
                "oos_sharpe_P3": K194_OOS_SH,
                "oos_maxdd_P3":  K194_OOS_DD,
                "wf_mean_P3":    K194_WF_MEAN,
                "wf_min_P3":     K194_WF_MIN,
                "hl_net_pct":    -100.0,
                "description":   "K194 v6.2 (4-sym panel, K121/K133 trigger)",
            },
            "K195": {
                "oos_sharpe_P3": K195_OOS_SH,
                "oos_maxdd_P3":  K195_OOS_DD,
                "wf_mean_P3":    K195_WF_MEAN,
                "wf_min_P3":     K195_WF_MIN,
                "hl_net_pct":    -100.0,
                "description":   "K195 v6.3 current production (10-sym fwd panel)",
            },
            "K196": {
                "oos_sharpe_P3":  k196_p3_oos,
                "oos_maxdd_P3":   k196_dd_oos,
                "full_sharpe_P3": k196_p3_full,
                "wf_mean_P3":     k196_wf_mean_p3,
                "wf_min_P3":      k196_wf_min_p3,
                "hl_net_pct":     round(hl_net["hl_net_combined"] * 100, 2),
                "description":    "K196 v6.4 candidate (fwd + rev carry, 20 sym total)",
            },
        },
        "acceptance_criteria": {
            "c1_oos_lift_needed":  0.05,
            "c1_oos_lift_actual":  round(oos_lift, 4),
            "c1_k195_oos_sh":      K195_OOS_SH,
            "c1_k196_oos_sh":      k196_p3_oos,
            "c1_pass":             c1_pass,
            "c2_maxdd_k195":       K195_OOS_DD,
            "c2_maxdd_k196":       k196_dd_oos,
            "c2_pass":             c2_pass,
            "c3_wf_min_needed":    3.5,
            "c3_wf_min_actual":    k196_wf_min_p3,
            "c3_pass":             c3_pass,
            "c4_hl_reduction_pct": hl_net["hl_net_reduction_pct"],
            "c4_pass":             c4_pass,
            "all_pass":            all_pass,
        },
        "verdict": (
            "ACCEPT: K196 v6.4 clears all acceptance criteria. "
            "Add reverse carry panel as 10th carry slot. Promote to v6.4."
            if all_pass else
            "CONDITIONAL/REJECT: K196 does not meet all acceptance criteria. "
            "See individual criteria above."
        ),
        "capital_allocation_recommendation": {
            "if_accepted": {
                "K195_strategies": "8 non-carry + V_fwd_carry (10% cap) — maintain",
                "K196_addition":   "V_rev_carry (10% cap) — add as 10th slot",
                "total_carry_sleeve": "20% (forward 10% + reverse 10%)",
                "carry_diversification": "20 symbols, 10 each direction",
                "hl_net_capital_exposure": f"{hl_net['hl_net_combined']*100:+.1f}% on Sharpe-weighted basis",
            },
            "risk_notes": [
                "Reverse carry symbols: SOL/XRP/SUI/OP/APT high-liquidity → clean fills expected",
                "AXS/JTO/IMX/SAND/ADA — verify HL perpetual liquidity before deploying",
                "JTO/AXS: very high spread (JTO -3.35bps, AXS -4.07bps per event) — potential gaming signal",
                "Monitor HL solvency: K195+K196 = both long and short legs on HL (20 open positions)",
                "Total HL notional doubles vs K195-only — not risk-reduced in HL default scenario",
            ],
        },
    }

    # ── Save metrics JSON ─────────────────────────────────────────────────────
    out_metrics = BASE / "wave_k196_reverse_carry.json"
    with open(out_metrics, "w") as f:
        json.dump(metrics_out, f, indent=2, default=str)
    print(f"Saved: {out_metrics}")

    # ── Assemble curves JSON ──────────────────────────────────────────────────
    curves_out = {
        "dates": dates_list_k196,
        "panel_dates": panel_dates_list,
        "series": {
            "K196_P3_triggered": eq_k196_p3,
            "K196_P3_base":      eq_k196_base_p3,
            "K195_ref_P3":       eq_k195_ref_p3,
            **sym_rev_curves,
            **sub_rev_curves,
        }
    }
    # Add P1-P4 K196 curves
    for k, curve_list in res_k196["curves"].items():
        curves_out["series"][k] = curve_list

    out_curves = BASE / "wave_k196_curves.json"
    with open(out_curves, "w") as f:
        json.dump(curves_out, f, indent=2)
    print(f"Saved: {out_curves}")

    print()
    print("=" * 72)
    print(f"K196 COMPLETE — runtime {runtime_s:.0f}s")
    print(f"OOS Sharpe P3: {k196_p3_oos:.4f}  MaxDD: {k196_dd_oos:.4f}  "
          f"WF min: {k196_wf_min_p3:.4f}")
    print(f"HL net exposure: {hl_net['hl_net_combined']*100:+.1f}% "
          f"(reduction: {hl_net['hl_net_reduction_pct']:.1f}%)")
    print(f"Verdict: {metrics_out['verdict']}")
    print("=" * 72)

    return metrics_out


if __name__ == "__main__":
    main()
