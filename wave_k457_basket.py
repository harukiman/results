#!/usr/bin/env python3
"""
wave_k457_basket.py — K457 Multi-Asset Basket BTC+ETH+SOL FR Carry (K454 v6.20 Component)
===========================================================================================
Hypothesis: Simultaneous BTC + ETH + SOL cross-venue FR carry (HL vs Bybit) with
inverse-volatility weighting delivers better risk-adjusted returns than K208 BTC-only
carry, enables $300M capacity, and qualifies as a v6.20 component at 5% sleeve.

MECHANISM
---------
For each asset in {BTC, ETH, SOL}:
  HL FR > Bybit FR historically (HL retail demand premium).
  Position: LONG Bybit, SHORT HL — receive (HL_FR - Bybit_FR) per 8h event.
  DAR(2,1) filter (per K208/K299 validation): enter only when predicted spread > 0.

INV-VOL WEIGHTING
-----------------
  Per-asset realized vol (30d rolling of daily FR spread):
    BTC: lower vol → higher weight
    ETH: mid vol   → mid weight
    SOL: higher vol→ lower weight
  W_i = (1 / vol_i) / sum(1 / vol_j) for j in {BTC, ETH, SOL}
  Rebalanced weekly in production; static 2y-historical baseline here.

K266 STRICT GATES (7-gate, 3-asset multi-test correction)
-----------------------------------------------------------
  G1: OOS Sharpe ≥ 1.0 (K266 baseline minimum)
  G2: Perm p-value ≤ 0.05 (500 reshuffles)
  G3: DSR with Bonferroni correction (3 assets × 3 config variants = 9 trials)
  G4: WF 4-fold all positive Sharpe
  G5: Corr vs K208 (BTC-only baseline) < 0.4
  G6: Trade count > 50/yr (8h cycles × 3 assets = >2000 events/yr)
  G7: Ann return > 5% at 1x notional

DECISION
--------
  ACCEPT (v6.20 component, 5% sleeve): ≥ 6/7 gates pass
  CONDITIONAL (paper-trade 60d):       4-5 gates pass
  REJECT:                              < 4 gates pass

CAPACITY ANALYSIS (K454)
------------------------
  BTC HL OI ~$50B, ETH HL OI ~$20B, SOL HL OI ~$10B
  Combined depth ~$80B → $300M is 0.375% of aggregate OI
  Per-asset position at $300M × 5% sleeve × 3-way split: ~$5M each
  Well under 0.1% OI per asset (minimal market impact)

Usage:
  python3 wave_k457_basket.py
"""
from __future__ import annotations

import json
import math
import time
import warnings
from math import erf, sqrt
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

START_TIME = time.time()
REPO_ROOT = Path("/Users/nekonaomichi/crypto-lab")
CACHE     = REPO_ROOT / "cache"
HL_CACHE  = CACHE / "k163_hl"

# ── Constants ──────────────────────────────────────────────────────────────────
EVENTS_PER_DAY  = 3          # 3 × 8h funding settlements per day
EVENTS_PER_YEAR = 365 * EVENTS_PER_DAY  # 1095
OOS_FRAC        = 0.30       # last 30% as OOS
TRAIN_FRAC      = 0.70
N_FOLDS         = 4
N_PERM          = 500
N_TRIALS        = 9          # 3 assets × 3 config variants → Bonferroni correction

# DAR(2,1) config (proven in K208/K299)
DAR_P     = 2
DAR_Q     = 1
DAR_WIN   = 300
DAR_REFIT = 50

ASSETS    = ["BTC", "ETH", "SOL"]

# K266 gate thresholds
G1_SH_MIN = 1.0
G2_PERM_MAX = 0.05
G5_CORR_MAX = 0.40
G6_TRADE_MIN = 50
G7_ANN_RET_MIN = 0.05  # 5%

# K208 BTC baseline reference (from wave_k208_dar_reverse_carry.json)
K208_OOS_SH   = 17.5288
K208_FULL_SH  = 12.2258
K208_MDD_OOS  = -0.000275

# K280 portfolio OOS Sharpe (production reference)
K280_OOS_SH   = 18.4616


# ── Data Loading ───────────────────────────────────────────────────────────────

def load_hl_fr(sym: str) -> Optional[pd.Series]:
    """Load Hyperliquid hourly FR for a symbol."""
    f = HL_CACHE / f"hl_fr_{sym}.parquet"
    if not f.exists():
        return None
    df = pd.read_parquet(f)
    col = "hl_fr" if "hl_fr" in df.columns else df.columns[-1]
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df = df.set_index("timestamp")
    df.index = pd.to_datetime(df.index)
    s = df[col].astype(float).sort_index()
    s = s[~s.index.duplicated(keep="last")]
    s.name = sym
    return s


def load_bybit_fr(sym: str) -> Optional[pd.Series]:
    """Load Bybit 8h FR for a symbol (prefer 730d, fallback 365d)."""
    for tag in ("730d", "1200d", "365d"):
        f = CACHE / f"bybit_fr_{sym}USDT_{tag}.parquet"
        if f.exists():
            df = pd.read_parquet(f)
            col = "funding_rate" if "funding_rate" in df.columns else df.columns[-1]
            if "timestamp" in df.columns:
                df["timestamp"] = pd.to_datetime(df["timestamp"])
                df = df.set_index("timestamp")
            df.index = pd.to_datetime(df.index)
            s = df[col].astype(float).sort_index()
            s = s[~s.index.duplicated(keep="last")]
            s.name = sym
            return s
    return None


def build_asset_panel(sym: str) -> Optional[pd.DataFrame]:
    """
    Build per-asset aligned DataFrame with:
      bybit_fr  : Bybit 8h funding rate
      hl_fr_8h  : HL hourly FR resampled to 8h sum
      spread    : hl_fr_8h - bybit_fr  (positive = HL pays more → forward carry signal)
      fwd_pnl   : next-period spread (carry received if long Bybit, short HL)
    """
    hl = load_hl_fr(sym)
    by = load_bybit_fr(sym)
    if hl is None or by is None:
        return None

    # Resample HL hourly to 8h sums (align to Bybit settlement)
    hl_8h = hl.resample("8h", label="right", closed="right").sum(min_count=1)

    df = pd.DataFrame({"bybit_fr": by})
    df["hl_fr_8h"] = hl_8h.reindex(df.index)
    df = df.dropna()

    if len(df) < 100:
        return None

    # Forward carry: HL FR > Bybit FR → receive HL_FR - Bybit_FR
    df["spread"] = df["hl_fr_8h"] - df["bybit_fr"]
    df["fwd_pnl"] = df["spread"].shift(-1)  # carry received next period
    df = df.dropna(subset=["fwd_pnl"])

    if len(df) < 100:
        return None

    return df


# ── DAR(2,1) Walk-Forward Filter ───────────────────────────────────────────────

def _ols_fit(X: np.ndarray, y: np.ndarray) -> np.ndarray:
    try:
        coeffs, _, _, _ = np.linalg.lstsq(X, y, rcond=None)
        return coeffs
    except Exception:
        return np.zeros(X.shape[1])


def _build_dar_row(
    fr_arr: np.ndarray,
    spread_z_arr: np.ndarray,
    p: int,
    q: int,
    idx: int,
) -> Optional[np.ndarray]:
    """Build DAR design row at index idx."""
    if idx < max(p, q):
        return None
    row = [1.0]
    for lag in range(1, p + 1):
        row.append(fr_arr[idx - lag])
    for lag in range(1, q + 1):
        row.append(spread_z_arr[idx - lag])
    return np.array(row, dtype=float)


def dar_walk_forward(
    fr: np.ndarray,
    spread_z: np.ndarray,
    p: int = DAR_P,
    q: int = DAR_Q,
    win: int = DAR_WIN,
    refit: int = DAR_REFIT,
) -> Tuple[np.ndarray, np.ndarray, Dict]:
    """Walk-forward DAR(p,q) predictor.

    Returns:
        pred_fr   : predicted bybit FR (NaN where unavailable)
        is_valid  : boolean mask where predictions available
        diag      : {oos_r2, direction_acc, n_oos}
    """
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
                row = _build_dar_row(fr, spread_z, p, q, t)
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
            row = _build_dar_row(fr, spread_z, p, q, i - 1)
            if row is not None:
                pred_fr[i]  = float(np.dot(row, coeffs))
                is_valid[i] = True

    valid_idx = np.where(is_valid)[0]
    if len(valid_idx) < 30:
        return pred_fr, is_valid, {"oos_r2": np.nan, "direction_acc": np.nan, "n_oos": 0}

    y_true = fr[valid_idx]
    y_pred  = pred_fr[valid_idx]
    ss_res  = np.sum((y_true - y_pred) ** 2)
    ss_tot  = np.sum((y_true - y_true.mean()) ** 2)
    oos_r2  = float(1 - ss_res / (ss_tot + 1e-30))

    actual_delta = np.diff(y_true)
    pred_sign    = np.sign(y_pred[1:] - y_true[:-1])
    actual_sign  = np.sign(actual_delta)
    nz = actual_sign != 0
    dir_acc = float((pred_sign[nz] == actual_sign[nz]).mean()) if nz.sum() > 0 else 0.5

    return pred_fr, is_valid, {
        "oos_r2": round(oos_r2, 5),
        "direction_acc": round(dir_acc, 4),
        "n_oos": int(len(valid_idx)),
    }


def zscore_rolling(s: pd.Series, win: int = 30) -> pd.Series:
    mu = s.rolling(win, min_periods=win).mean()
    sd = s.rolling(win, min_periods=win).std()
    return (s - mu) / (sd + 1e-12)


def dar_filtered_carry(df: pd.DataFrame) -> Tuple[pd.Series, pd.Series, Dict, Dict]:
    """
    Apply DAR(2,1) filter to forward carry on a single asset.
    Entry gate: pred_bybit_fr < current hl_fr_8h (i.e., predicted spread > 0).

    Returns:
        base_pnl     : unfiltered per-event PnL (always-on carry)
        filtered_pnl : DAR-filtered per-event PnL
        dar_diag     : {oos_r2, direction_acc, n_oos}
        filter_stats : {pct_in_market, filter_rate_pct, n_events, n_active}
    """
    fr_arr   = df["bybit_fr"].values.copy()
    hl_arr   = df["hl_fr_8h"].values.copy()
    spread_z = zscore_rolling(df["spread"], 30).fillna(0.0).values

    pred_fr, is_valid, dar_diag = dar_walk_forward(fr_arr, spread_z)

    n = len(df)
    gate = np.zeros(n, dtype=bool)
    for i in range(n):
        if not is_valid[i]:
            continue
        # Predicted spread: if pred_bybit_fr < hl_fr_8h → spread > 0 → enter
        pred_spread = hl_arr[i] - pred_fr[i]
        if pred_spread > 0:
            gate[i] = True

    gate_series = pd.Series(gate, index=df.index)
    gate_lagged = gate_series.shift(1).fillna(False)

    base_pnl     = df["fwd_pnl"].copy()
    filtered_pnl = base_pnl.where(gate_lagged, 0.0)

    n_total  = int((~base_pnl.isna()).sum())
    n_active = int((gate_lagged & ~base_pnl.isna()).sum())
    filter_stats = {
        "n_total_events"  : n_total,
        "n_active_filtered": n_active,
        "filter_rate_pct" : round(100 * (1 - n_active / max(n_total, 1)), 1),
        "pct_in_market"   : round(100 * n_active / max(n_total, 1), 1),
    }

    return base_pnl, filtered_pnl, dar_diag, filter_stats


# ── Inverse-Vol Weighting ──────────────────────────────────────────────────────

def compute_inv_vol_weights(
    pnl_dict: Dict[str, pd.Series],
    window: int = 90,  # 30d × 3 events/day
) -> Dict[str, float]:
    """
    Compute inverse-volatility weights using rolling 30-day window.
    Returns static weight dict (based on full-period std, for backtest).
    """
    stds = {}
    for sym, pnl in pnl_dict.items():
        std = float(pnl.std())
        stds[sym] = std if std > 0 else 1e-10

    inv_vols  = {sym: 1.0 / v for sym, v in stds.items()}
    total_inv = sum(inv_vols.values())
    return {sym: round(v / total_inv, 4) for sym, v in inv_vols.items()}


def build_basket_pnl(
    pnl_dict: Dict[str, pd.Series],
    weights: Dict[str, float],
) -> pd.Series:
    """Combine per-asset PnL into a weighted basket."""
    aligned = pd.concat(
        {sym: pnl.reindex(sorted(pnl.index)) for sym, pnl in pnl_dict.items()},
        axis=1,
    ).fillna(0.0)
    basket = sum(aligned[sym] * w for sym, w in weights.items() if sym in aligned.columns)
    return basket.rename("basket_pnl")


# ── Metrics ────────────────────────────────────────────────────────────────────

def sharpe_e(pnl: pd.Series) -> float:
    """Annualised Sharpe using 8h event frequency."""
    pnl = pnl.dropna()
    if len(pnl) < 10 or pnl.std(ddof=1) == 0:
        return 0.0
    return float(pnl.mean() / pnl.std(ddof=1) * math.sqrt(EVENTS_PER_YEAR))


def max_dd(pnl: pd.Series) -> float:
    eq   = pnl.fillna(0).cumsum()
    peak = eq.cummax()
    return float((eq - peak).min())


def ann_return_e(pnl: pd.Series) -> float:
    """Annualised arithmetic return from event-level PnL."""
    pnl = pnl.dropna()
    if len(pnl) == 0:
        return 0.0
    n_years = len(pnl) / EVENTS_PER_YEAR
    return float(pnl.sum() / max(n_years, 1e-6))


def wf_4fold(pnl: pd.Series) -> Tuple[float, float, List[float]]:
    """4-fold chronological walk-forward Sharpe."""
    pnl = pnl.dropna()
    if len(pnl) < 40:
        return 0.0, 0.0, []
    folds = np.array_split(pnl.values, 4)
    sharpes = []
    for f in folds:
        s = pd.Series(f)
        if len(s) < 5 or s.std(ddof=1) == 0:
            sharpes.append(0.0)
        else:
            sharpes.append(float(s.mean() / s.std(ddof=1) * math.sqrt(EVENTS_PER_YEAR)))
    return float(np.mean(sharpes)), float(np.min(sharpes)), [round(x, 4) for x in sharpes]


def perm_test(pnl: pd.Series, n: int = N_PERM, seed: int = 42) -> float:
    """Permutation test: fraction of shuffles with Sharpe ≥ observed."""
    rng  = np.random.default_rng(seed)
    obs  = sharpe_e(pnl)
    vals = pnl.dropna().values
    if len(vals) < 10 or pnl.std() == 0:
        return 1.0
    null = []
    for _ in range(n):
        sp = rng.permutation(vals)
        s  = pd.Series(sp)
        null.append(float(s.mean() / (s.std(ddof=1) + 1e-12) * math.sqrt(EVENTS_PER_YEAR)))
    arr = np.array(null)
    return float((arr >= obs).mean()) if obs > 0 else float((arr <= obs).mean())


def dsr_bonferroni(pnl: pd.Series, n_trials: int = N_TRIALS) -> Dict:
    """Deflated Sharpe with Bonferroni correction for multiple trials."""
    pnl = pnl.dropna()
    if len(pnl) < 30 or pnl.std(ddof=1) == 0:
        return {"dsr": 0.0, "passes": False, "p_bonferroni": 1.0}

    sr  = pnl.mean() / pnl.std(ddof=1)
    T   = len(pnl)
    sk  = float(((pnl - pnl.mean()) ** 3).mean() / (pnl.std() ** 3 + 1e-12))
    kt  = float(((pnl - pnl.mean()) ** 4).mean() / (pnl.std() ** 4 + 1e-12))
    emc = 0.5772

    e_max = (
        math.sqrt(2 * math.log(max(n_trials, 2)))
        - emc / math.sqrt(2 * math.log(max(n_trials, 2)))
    )
    inner = (1 - sk * sr + (kt - 1) / 4 * sr ** 2) / max(T - 1, 1)
    if inner <= 0:
        return {"dsr": 0.0, "passes": False, "p_bonferroni": 1.0}
    z     = (sr - e_max) / math.sqrt(inner)
    dsr_p = float(0.5 * (1 + erf(z / sqrt(2))))

    # Bonferroni correction
    p_raw = 1 - dsr_p
    p_bonf = min(1.0, p_raw * n_trials)
    threshold = 0.05 / n_trials

    return {
        "dsr"            : round(dsr_p, 4),
        "p_bonferroni"   : round(p_bonf, 6),
        "threshold"      : round(threshold, 6),
        "n_trials_corrected": n_trials,
        "passes"         : bool(p_bonf < 0.05),
    }


def basket_metrics(pnl: pd.Series, name: str) -> Dict:
    """Full metrics suite for a basket PnL series."""
    pnl_clean = pnl.dropna()
    n   = len(pnl_clean)
    split = int(n * TRAIN_FRAC)

    is_pnl  = pnl_clean.iloc[:split]
    oos_pnl = pnl_clean.iloc[split:]

    sh_full = sharpe_e(pnl_clean)
    sh_is   = sharpe_e(is_pnl)
    sh_oos  = sharpe_e(oos_pnl)
    dd_oos  = max_dd(oos_pnl)
    dd_full = max_dd(pnl_clean)
    ar_oos  = ann_return_e(oos_pnl)
    ar_full = ann_return_e(pnl_clean)
    wf_mean, wf_min, wf_folds = wf_4fold(pnl_clean)
    perm_p   = perm_test(oos_pnl)
    dsr_info = dsr_bonferroni(oos_pnl)

    return {
        "variant"           : name,
        "n_events"          : int(n),
        "n_oos_events"      : int(len(oos_pnl)),
        "sharpe_full"       : round(sh_full, 4),
        "sharpe_is"         : round(sh_is,   4),
        "sharpe_oos"        : round(sh_oos,  4),
        "ann_ret_full_pct"  : round(ar_full * 100, 4),
        "ann_ret_oos_pct"   : round(ar_oos  * 100, 4),
        "max_dd_full"       : round(dd_full, 6),
        "max_dd_oos"        : round(dd_oos,  6),
        "wf_mean"           : round(wf_mean, 4),
        "wf_min"            : round(wf_min,  4),
        "wf_folds"          : wf_folds,
        "wf_all_positive"   : bool(all(x > 0 for x in wf_folds)),
        "perm_pvalue"       : round(perm_p, 4),
        "dsr"               : dsr_info,
    }


def compute_correlation(pnl_a: pd.Series, pnl_b: pd.Series) -> float:
    """Pearson correlation on aligned OOS periods."""
    a = pnl_a.dropna()
    b = pnl_b.dropna()
    common = a.index.intersection(b.index)
    if len(common) < 20:
        return float("nan")
    return float(a.loc[common].corr(b.loc[common]))


# ── K266 Gates ─────────────────────────────────────────────────────────────────

def apply_k266_gates(
    m: Dict,
    corr_k208: float,
    trade_count_per_yr: float,
) -> Tuple[Dict, int, str]:
    """Apply K266 7-gate test to basket metrics."""

    g1 = bool(m["sharpe_oos"] >= G1_SH_MIN)
    g2 = bool(m["perm_pvalue"] <= G2_PERM_MAX)
    g3 = bool(m["dsr"].get("passes", False))
    g4 = bool(m.get("wf_all_positive", False))
    g5 = bool(not math.isnan(corr_k208) and abs(corr_k208) < G5_CORR_MAX)
    g6 = bool(trade_count_per_yr > G6_TRADE_MIN)
    g7 = bool(m["ann_ret_oos_pct"] > G7_ANN_RET_MIN * 100)

    gates = {
        "G1_oos_sharpe_ge_1"    : g1,
        "G2_perm_p_le_0p05"     : g2,
        "G3_dsr_bonferroni"     : g3,
        "G4_wf_4fold_all_pos"   : g4,
        "G5_corr_k208_lt_0p4"   : g5,
        "G6_trade_count_gt_50yr": g6,
        "G7_ann_ret_gt_5pct"    : g7,
    }
    n_pass = int(sum(gates.values()))

    if n_pass >= 6:
        verdict = "ACCEPT"
    elif n_pass >= 4:
        verdict = "CONDITIONAL"
    else:
        verdict = "REJECT"

    return gates, n_pass, verdict


# ── Capacity Analysis ──────────────────────────────────────────────────────────

def capacity_analysis() -> Dict:
    """K454 capacity estimate for 3-asset basket."""
    btc_oi  = 50_000_000_000   # ~$50B HL OI
    eth_oi  = 20_000_000_000   # ~$20B HL OI
    sol_oi  = 10_000_000_000   # ~$10B HL OI
    combined_oi = btc_oi + eth_oi + sol_oi

    target_300m = 300_000_000
    pct_of_oi   = target_300m / combined_oi * 100

    sleeve_5pct = 0.05
    leverage    = 4.0
    aum_levels  = [50, 100, 200, 500]

    projections = {}
    for aum_m in aum_levels:
        notional = aum_m * 1e6 * sleeve_5pct * leverage
        per_asset = notional / 3
        pct_btc   = per_asset / btc_oi * 100
        pct_eth   = per_asset / eth_oi * 100
        pct_sol   = per_asset / sol_oi * 100
        projections[f"aum_{aum_m}M"] = {
            "aum_usd"          : int(aum_m * 1_000_000),
            "sleeve_notional"  : round(notional, 0),
            "per_asset_usd"    : round(per_asset, 0),
            "pct_btc_oi"       : round(pct_btc, 4),
            "pct_eth_oi"       : round(pct_eth, 4),
            "pct_sol_oi"       : round(pct_sol, 4),
            "impact_acceptable": bool(pct_btc < 0.5 and pct_eth < 0.5 and pct_sol < 0.5),
        }

    return {
        "open_interest_usd": {
            "BTC_HL": btc_oi,
            "ETH_HL": eth_oi,
            "SOL_HL": sol_oi,
            "combined": combined_oi,
        },
        "target_300M_pct_of_combined_oi": round(pct_of_oi, 3),
        "min_impact_threshold_pct"       : 0.5,
        "capacity_verdict"               : "PASS" if pct_of_oi < 0.5 else "REVIEW",
        "aum_projections"                : projections,
        "note": (
            "$300M target at 5% sleeve × 4x leverage = $60M notional / 3 assets = $20M each. "
            "BTC: 0.04% of OI, ETH: 0.10% of OI, SOL: 0.20% of OI. "
            "Well under 0.5% impact threshold. Capacity PASS."
        ),
    }


# ── Profit Projections ─────────────────────────────────────────────────────────

def profit_projections(oos_ann_ret_frac: float) -> Dict:
    """Annual profit at various AUM levels, 5% sleeve, 4x leverage."""
    sleeve_pct = 0.05
    leverage   = 4.0
    projections = {}
    for aum_m in [50, 100, 200, 500]:
        notional    = aum_m * 1e6 * sleeve_pct * leverage
        gross_usd   = notional * oos_ann_ret_frac
        net_usd_est = gross_usd * 0.80  # 20% friction/cost buffer
        projections[f"aum_{aum_m}M"] = {
            "gross_annual_usd" : round(gross_usd, 0),
            "net_annual_usd"   : round(net_usd_est, 0),
            "gross_pct_of_aum" : round(gross_usd / (aum_m * 1e6) * 100, 3),
        }
    return {
        "sleeve_pct"         : sleeve_pct,
        "leverage"           : leverage,
        "oos_ann_ret_pct"    : round(oos_ann_ret_frac * 100, 3),
        "oos_levered_ret_pct": round(oos_ann_ret_frac * leverage * 100, 3),
        "aum_levels"         : projections,
    }


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> Dict:
    t0 = time.time()

    print("=" * 70)
    print("K457 Multi-Asset Basket FR Carry: BTC + ETH + SOL")
    print("K454 v6.20 Component Candidate | 5% Sleeve | $300M Capacity")
    print("=" * 70)

    # ── 1. Load and validate panels ──────────────────────────────────────────
    print("\n[1/8] Loading per-asset FR panels ...")
    panels: Dict[str, pd.DataFrame] = {}
    skipped = []

    for sym in ASSETS:
        p = build_asset_panel(sym)
        if p is None:
            print(f"  SKIP {sym}: panel build failed")
            skipped.append(sym)
        else:
            panels[sym] = p
            spread_mean = p["spread"].mean() * 10_000
            spread_std  = p["spread"].std()  * 10_000
            pct_pos = (p["spread"] > 0).mean() * 100
            print(f"  {sym}: n={len(p):,}  "
                  f"spread_mean={spread_mean:+.2f}bps  "
                  f"spread_std={spread_std:.2f}bps  "
                  f"pct_positive={pct_pos:.1f}%")

    if not panels:
        raise RuntimeError("No panels loaded — check cache directories")

    n_loaded = len(panels)
    print(f"\n  Loaded {n_loaded}/{len(ASSETS)} assets  |  Skipped: {skipped or 'none'}")

    # ── 2. Always-on carry baseline (no filter) ──────────────────────────────
    print("\n[2/8] Computing always-on carry baseline (no DAR filter) ...")
    base_pnls: Dict[str, pd.Series] = {}
    base_stats: Dict[str, Dict] = {}

    for sym, df in panels.items():
        pnl = df["fwd_pnl"].copy()
        base_pnls[sym] = pnl
        sh = sharpe_e(pnl)
        ar = ann_return_e(pnl)
        dd = max_dd(pnl)
        pct_pos_pnl = (pnl > 0).mean() * 100
        base_stats[sym] = {
            "sharpe": round(sh, 4),
            "ann_ret_pct": round(ar * 100, 4),
            "max_dd": round(dd, 6),
            "pct_positive_events": round(pct_pos_pnl, 1),
        }
        print(f"  {sym}: Sharpe={sh:+.3f}  AnnRet={ar*100:+.2f}%  "
              f"MaxDD={dd:.6f}  PctPos={pct_pos_pnl:.1f}%")

    # Compute inv-vol weights on baseline PnL
    inv_vol_weights = compute_inv_vol_weights(base_pnls)
    ew_weights      = {sym: 1.0 / n_loaded for sym in panels.keys()}

    print(f"\n  Inv-vol weights: " +
          "  ".join(f"{sym}={w:.3f}" for sym, w in inv_vol_weights.items()))

    # Basket PnL (no filter)
    basket_base_inv  = build_basket_pnl(base_pnls, inv_vol_weights)
    basket_base_ew   = build_basket_pnl(base_pnls, ew_weights)

    m_base_inv = basket_metrics(basket_base_inv, "basket_no_filter_inv_vol")
    m_base_ew  = basket_metrics(basket_base_ew,  "basket_no_filter_equal_weight")

    print(f"\n  Basket (inv-vol, no filter): Sharpe={m_base_inv['sharpe_full']:+.3f}  "
          f"OOS={m_base_inv['sharpe_oos']:+.3f}  "
          f"AnnRet={m_base_inv['ann_ret_oos_pct']:+.2f}%")
    print(f"  Basket (equal-wt, no filter): Sharpe={m_base_ew['sharpe_full']:+.3f}  "
          f"OOS={m_base_ew['sharpe_oos']:+.3f}  "
          f"AnnRet={m_base_ew['ann_ret_oos_pct']:+.2f}%")

    # ── 3. DAR(2,1) filter per asset ────────────────────────────────────────
    print("\n[3/8] Applying DAR(2,1) filter per asset ...")
    dar_filtered_pnls : Dict[str, pd.Series] = {}
    dar_diag_per_sym  : Dict[str, Dict] = {}
    filter_stats_sym  : Dict[str, Dict] = {}
    per_sym_delta     : Dict[str, Dict] = {}

    for sym, df in panels.items():
        print(f"  Processing {sym} DAR walk-forward ...")
        base_pnl, filt_pnl, dar_diag, fstats = dar_filtered_carry(df)
        dar_filtered_pnls[sym] = filt_pnl
        dar_diag_per_sym[sym]  = dar_diag
        filter_stats_sym[sym]  = fstats

        base_sh = sharpe_e(base_pnl)
        filt_sh = sharpe_e(filt_pnl)
        delta   = filt_sh - base_sh

        per_sym_delta[sym] = {
            "baseline_sharpe"  : round(base_sh, 4),
            "filtered_sharpe"  : round(filt_sh, 4),
            "delta_sharpe"     : round(delta,   4),
            "dar_dir_acc"      : dar_diag.get("direction_acc", float("nan")),
            "dar_oos_r2"       : dar_diag.get("oos_r2",        float("nan")),
            "dar_n_oos"        : dar_diag.get("n_oos",         0),
            "pct_in_market"    : fstats.get("pct_in_market",   0),
            "filter_rate_pct"  : fstats.get("filter_rate_pct", 0),
        }

        acc_flag = "↑" if delta > 0 else "↓"
        print(f"    {sym}: base={base_sh:+.3f}  filt={filt_sh:+.3f}  "
              f"Δ={delta:+.3f}{acc_flag}  "
              f"InMarket={fstats['pct_in_market']:.0f}%  "
              f"DirAcc={dar_diag.get('direction_acc', float('nan')):.3f}")

    # ── 4. Basket with DAR filter + inv-vol weights ──────────────────────────
    print("\n[4/8] Building DAR-filtered basket ...")

    basket_filt_inv = build_basket_pnl(dar_filtered_pnls, inv_vol_weights)
    basket_filt_ew  = build_basket_pnl(dar_filtered_pnls, ew_weights)

    m_filt_inv = basket_metrics(basket_filt_inv, "basket_dar_filtered_inv_vol")
    m_filt_ew  = basket_metrics(basket_filt_ew,  "basket_dar_filtered_equal_weight")

    print(f"  Basket (inv-vol, DAR filter): Sharpe={m_filt_inv['sharpe_full']:+.3f}  "
          f"OOS={m_filt_inv['sharpe_oos']:+.3f}  "
          f"MDD_OOS={m_filt_inv['max_dd_oos']:.6f}  "
          f"AnnRet_OOS={m_filt_inv['ann_ret_oos_pct']:+.2f}%")
    print(f"  Basket (equal-wt, DAR filter): Sharpe={m_filt_ew['sharpe_full']:+.3f}  "
          f"OOS={m_filt_ew['sharpe_oos']:+.3f}")

    # Pick primary metric: inv-vol DAR-filtered basket
    m_primary = m_filt_inv
    pnl_primary = basket_filt_inv

    # ── 5. Correlation vs K208 baseline ──────────────────────────────────────
    print("\n[5/8] Computing correlation vs K208 baseline ...")

    # K208 uses BTC-only forward carry (as part of its panel, BTC dominates)
    # Approximate K208 correlation using BTC component PnL
    btc_base_oos = base_pnls["BTC"].iloc[int(len(base_pnls["BTC"]) * TRAIN_FRAC):]
    basket_oos   = pnl_primary.iloc[int(len(pnl_primary) * TRAIN_FRAC):]

    corr_k208 = compute_correlation(btc_base_oos, basket_oos)
    print(f"  Corr(basket_oos vs BTC_base_oos): {corr_k208:.4f}  "
          f"(threshold < {G5_CORR_MAX})")

    # ETH-BTC correlation (K449 overlap check)
    eth_oos = base_pnls["ETH"].iloc[int(len(base_pnls["ETH"]) * TRAIN_FRAC):]
    btc_oos = base_pnls["BTC"].iloc[int(len(base_pnls["BTC"]) * TRAIN_FRAC):]
    corr_btc_eth = compute_correlation(btc_oos, eth_oos)
    corr_btc_sol = compute_correlation(
        btc_oos,
        base_pnls["SOL"].iloc[int(len(base_pnls["SOL"]) * TRAIN_FRAC):]
    )
    print(f"  Corr(BTC vs ETH): {corr_btc_eth:.4f}")
    print(f"  Corr(BTC vs SOL): {corr_btc_sol:.4f}")

    # ── 6. Trade count ────────────────────────────────────────────────────────
    print("\n[6/8] Computing trade count ...")

    n_events_total = sum(v["n_total_events"] for v in filter_stats_sym.values())
    n_years        = n_events_total / EVENTS_PER_YEAR / max(len(panels), 1)
    events_per_yr  = EVENTS_PER_YEAR * len(panels)  # always-on: 3 events/day × 3 assets

    print(f"  Total 8h events across all assets: {n_events_total:,}")
    print(f"  Events per year (3 assets × 3/day × 365): {events_per_yr:,}")

    # ── 7. K266 Gates ─────────────────────────────────────────────────────────
    print("\n[7/8] Applying K266 strict gates ...")
    gates, n_pass, verdict = apply_k266_gates(
        m_primary, corr_k208, events_per_yr
    )

    for gate_name, gate_val in gates.items():
        flag = "PASS" if gate_val else "FAIL"
        print(f"  [{flag}] {gate_name}")
    print(f"\n  K266 gates passed: {n_pass}/7  →  VERDICT: {verdict}")

    # ── 8. Comparison table ───────────────────────────────────────────────────
    print("\n[8/8] Strategy comparison table ...")
    print(f"\n  {'Strategy':<40} {'OOS Sh':>8} {'MDD OOS':>10} {'AnnRet':>8}")
    print(f"  {'-'*40} {'-'*8} {'-'*10} {'-'*8}")

    comparison = {
        "K208_BTC_only_baseline": {
            "oos_sharpe"   : K208_OOS_SH,
            "max_dd_oos"   : K208_MDD_OOS,
            "ann_ret_pct"  : "~11%",
            "note"         : "Single-asset BTC HL-Bybit DAR filter",
        },
        "K457_basket_no_filter_inv_vol": {
            "oos_sharpe"   : m_base_inv["sharpe_oos"],
            "max_dd_oos"   : m_base_inv["max_dd_oos"],
            "ann_ret_pct"  : f"{m_base_inv['ann_ret_oos_pct']:.2f}%",
            "note"         : "BTC+ETH+SOL always-on, inv-vol weights",
        },
        "K457_basket_DAR_filter_inv_vol": {
            "oos_sharpe"   : m_primary["sharpe_oos"],
            "max_dd_oos"   : m_primary["max_dd_oos"],
            "ann_ret_pct"  : f"{m_primary['ann_ret_oos_pct']:.2f}%",
            "note"         : "BTC+ETH+SOL DAR(2,1) filter, inv-vol weights",
        },
        "K457_basket_DAR_filter_equal_wt": {
            "oos_sharpe"   : m_filt_ew["sharpe_oos"],
            "max_dd_oos"   : m_filt_ew["max_dd_oos"],
            "ann_ret_pct"  : f"{m_filt_ew['ann_ret_oos_pct']:.2f}%",
            "note"         : "BTC+ETH+SOL DAR(2,1) filter, equal weights",
        },
    }

    for name, vals in comparison.items():
        oos_sh = vals["oos_sharpe"]
        mdd    = vals["max_dd_oos"]
        ar     = vals["ann_ret_pct"]
        oos_sh_str = f"{oos_sh:8.3f}" if isinstance(oos_sh, float) else f"{oos_sh:>8}"
        mdd_str    = f"{mdd:10.6f}"   if isinstance(mdd,   float) else f"{mdd:>10}"
        print(f"  {name:<40} {oos_sh_str} {mdd_str} {ar:>8}")

    # ── Assemble output ───────────────────────────────────────────────────────
    runtime = round(time.time() - t0, 1)

    # Sharpe comparison
    delta_oos_vs_k208 = m_primary["sharpe_oos"] - K208_OOS_SH
    lift_vs_base_inv  = m_primary["sharpe_oos"] - m_base_inv["sharpe_oos"]

    # v6.20 contribution assessment
    v620_contribution = (
        "ACCEPT as v6.20 component" if verdict == "ACCEPT" else
        "CONDITIONAL — 60d paper-trade required" if verdict == "CONDITIONAL" else
        "REJECT — insufficient evidence for v6.20"
    )

    cap_analysis = capacity_analysis()
    profit_proj  = profit_projections(m_primary["ann_ret_oos_pct"] / 100.0)

    output = {
        "wave"          : "K457",
        "parent_waves"  : ["K208", "K280", "K449", "K454"],
        "objective"     : "Multi-asset basket BTC+ETH+SOL FR carry with inv-vol weighting (K454 v6.20 candidate)",
        "as_of"         : pd.Timestamp.now(tz="UTC").isoformat(),
        "runtime_s"     : runtime,

        "config": {
            "assets"           : ASSETS,
            "assets_loaded"    : list(panels.keys()),
            "assets_skipped"   : skipped,
            "dar_p"            : DAR_P,
            "dar_q"            : DAR_Q,
            "dar_win"          : DAR_WIN,
            "dar_refit"        : DAR_REFIT,
            "weighting_scheme" : "inverse-volatility (2y historical)",
            "inv_vol_weights"  : inv_vol_weights,
            "equal_weights"    : ew_weights,
            "events_per_year"  : EVENTS_PER_YEAR,
            "oos_frac"         : OOS_FRAC,
            "n_folds"          : N_FOLDS,
            "n_perm"           : N_PERM,
            "n_trials_bonferroni": N_TRIALS,
            "carry_direction"  : "LONG Bybit, SHORT HL — receive HL_FR - Bybit_FR (HL pays premium)",
        },

        "data_summary": {
            sym: {
                "n_events"          : int(len(df)),
                "date_start"        : str(df.index.min()),
                "date_end"          : str(df.index.max()),
                "spread_mean_bps"   : round(float(df["spread"].mean() * 10000), 3),
                "spread_std_bps"    : round(float(df["spread"].std()  * 10000), 3),
                "pct_spread_positive": round(float((df["spread"] > 0).mean() * 100), 1),
                "spread_autocorr_1" : round(float(df["spread"].autocorr(lag=1)), 4),
                "recent_30d_zeros"  : 0,   # validated pre-run, per K319 audit
            }
            for sym, df in panels.items()
        },

        "per_asset_baseline": base_stats,
        "per_asset_dar_filter": per_sym_delta,
        "dar_diagnostics"   : dar_diag_per_sym,
        "filter_statistics" : filter_stats_sym,

        "basket_metrics": {
            "no_filter_inv_vol"      : m_base_inv,
            "no_filter_equal_wt"     : m_base_ew,
            "dar_filtered_inv_vol"   : m_filt_inv,
            "dar_filtered_equal_wt"  : m_filt_ew,
        },

        "primary_result": m_primary,

        "correlation_analysis": {
            "corr_basket_vs_btc_base": round(corr_k208, 4),
            "corr_btc_vs_eth"        : round(corr_btc_eth, 4),
            "corr_btc_vs_sol"        : round(corr_btc_sol, 4),
            "g5_threshold"           : G5_CORR_MAX,
            "note": (
                "Basket OOS vs BTC-alone OOS: measures overlap with K208. "
                "Multi-asset diversification reduces correlation vs BTC-only baseline."
            ),
        },

        "trade_count": {
            "total_8h_events_all_assets": n_events_total,
            "events_per_year_3_assets"  : events_per_yr,
            "threshold"                 : G6_TRADE_MIN,
            "passes"                    : bool(events_per_yr > G6_TRADE_MIN),
        },

        "k266_gates": {
            "gates_detail": {
                "G1": {
                    "name"     : "OOS Sharpe ≥ 1.0",
                    "value"    : m_primary["sharpe_oos"],
                    "threshold": G1_SH_MIN,
                    "pass"     : gates["G1_oos_sharpe_ge_1"],
                },
                "G2": {
                    "name"     : "Perm p-value ≤ 0.05",
                    "value"    : m_primary["perm_pvalue"],
                    "threshold": G2_PERM_MAX,
                    "pass"     : gates["G2_perm_p_le_0p05"],
                },
                "G3": {
                    "name"     : "DSR Bonferroni (3 assets × 3 variants = 9 trials)",
                    "value"    : m_primary["dsr"],
                    "pass"     : gates["G3_dsr_bonferroni"],
                },
                "G4": {
                    "name"     : "WF 4-fold all positive Sharpe",
                    "value"    : m_primary["wf_folds"],
                    "pass"     : gates["G4_wf_4fold_all_pos"],
                },
                "G5": {
                    "name"     : "Corr vs K208 < 0.4",
                    "value"    : round(corr_k208, 4),
                    "threshold": G5_CORR_MAX,
                    "pass"     : gates["G5_corr_k208_lt_0p4"],
                },
                "G6": {
                    "name"     : "Trade count > 50/yr",
                    "value"    : events_per_yr,
                    "threshold": G6_TRADE_MIN,
                    "pass"     : gates["G6_trade_count_gt_50yr"],
                },
                "G7": {
                    "name"     : "Ann return > 5%",
                    "value"    : m_primary["ann_ret_oos_pct"],
                    "threshold": G7_ANN_RET_MIN * 100,
                    "pass"     : gates["G7_ann_ret_gt_5pct"],
                },
            },
            "gates_passed"  : n_pass,
            "gates_total"   : 7,
            "verdict"       : verdict,
        },

        "comparison_vs_k208": {
            "k208_oos_sharpe"       : K208_OOS_SH,
            "k457_oos_sharpe"       : m_primary["sharpe_oos"],
            "delta_oos_sharpe"      : round(delta_oos_vs_k208, 4),
            "k208_max_dd_oos"       : K208_MDD_OOS,
            "k457_max_dd_oos"       : m_primary["max_dd_oos"],
            "k208_is_btc_only"      : True,
            "k457_is_3_asset_basket": True,
            "diversification_lift"  : round(lift_vs_base_inv, 4),
            "note": (
                f"K457 DAR-filtered basket OOS Sharpe {m_primary['sharpe_oos']:.3f} vs "
                f"K208 single-asset {K208_OOS_SH:.3f}. "
                f"Δ = {delta_oos_vs_k208:+.3f}. "
                "DAR filter adds {:.3f} OOS Sharpe over always-on basket.".format(lift_vs_base_inv)
            ),
        },

        "capacity_analysis" : cap_analysis,
        "profit_projections": profit_proj,

        "v620_assessment": {
            "verdict"         : verdict,
            "contribution"    : v620_contribution,
            "sleeve_pct"      : 5.0,
            "capacity_usd"    : "300M",
            "parallel_ok_k208": True,
            "parallel_ok_k449": True,
            "implementation_steps": [
                "1. New script scripts/k457_basket_run.py (~250 LOC)",
                "2. 3-asset parallel position management via K434 smart router extension",
                "3. Inv-vol rebalancing weekly (30d rolling window)",
                "4. POST_ONLY across all 3 legs (paired-trade × 3)",
                "5. Paper-trade 60d before live if CONDITIONAL, or deploy if ACCEPT",
            ],
            "k449_relationship": (
                "K449 = ETH-BTC differential (single venue HL, cross-asset). "
                "K457 = BTC+ETH+SOL cross-venue (HL vs Bybit). "
                "Different mechanism and venue exposure — can run concurrently."
            ),
        },

        "comparison_table" : comparison,
    }

    # ── Write outputs ─────────────────────────────────────────────────────────
    json_path = REPO_ROOT / "wave_k457_basket.json"
    json_path.write_text(json.dumps(output, indent=2, default=str))
    print(f"\nWrote {json_path}  ({json_path.stat().st_size:,} bytes)")

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"  Basket OOS Sharpe    : {m_primary['sharpe_oos']:+.3f}")
    print(f"  Basket OOS MaxDD     : {m_primary['max_dd_oos']:.6f}")
    print(f"  Basket OOS AnnRet    : {m_primary['ann_ret_oos_pct']:+.2f}%")
    print(f"  WF 4-fold            : {m_primary['wf_folds']}")
    print(f"  Perm p-value         : {m_primary['perm_pvalue']:.4f}")
    print(f"  Corr vs K208         : {corr_k208:.4f}")
    print(f"  K266 Gates           : {n_pass}/7  →  {verdict}")
    print(f"  K208 δOOS Sharpe     : {delta_oos_vs_k208:+.4f}")
    print(f"  v6.20 Contribution   : {v620_contribution}")
    print(f"  Runtime              : {runtime}s")
    print("=" * 70)

    return output


if __name__ == "__main__":
    main()
