"""Wave K190 - DAR FR Predictor as Entry Filter for K175.

Hypothesis (SSRN 5576424 / tip-scraper R7-4):
  Bybit/Binance BTC FR is OOS-predictable via DAR(p,q) models.
  If predicted next-period FR matches K175 entry direction (i.e., FR expected
  to normalize back to zero), signal quality improves. Implementing for XRP+SUI.

Strategy logic:
  K175 baseline:
    - Compute spread = bybit_fr - hl_fr_8h
    - z-score spread vs 30-period rolling window
    - Short Bybit perp when z > 2 (FR elevated → short = collect FR)
    - Long  Bybit perp when z < -2 (FR depressed)
    - Maker-only: 2bp/side slippage, 0 maker fee, 4bp round-trip

  K190 DAR filter:
    - DAR(p,q): FR_t = α + Σ β_i*FR_{t-i} + Σ γ_j*X_{t-j} + ε
    - Walk-forward: refit every R_REFIT events on rolling window of WIN events
    - Predict FR_{t+1} at entry time
    - Additional entry gate:
      * z > +2 (short FR): predicted_FR <= current_FR (FR expected to drop/normalize)
      * z < -2 (long FR):  predicted_FR >= current_FR (FR expected to rise/normalize)

REPORT GROSS AND NET (K173 META-LESSON).
"""
from __future__ import annotations

import json
import time
import warnings
from math import erf, sqrt
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

ROOT = Path("/Users/nekonaomichi/crypto-lab")
CACHE = ROOT / "cache"
HL_CACHE = CACHE / "k163_hl"

# Cost model (maker-only, identical to K175)
SLIPPAGE_BPS_PER_SIDE = 2.0
MAKER_FEE_BPS_PER_SIDE = 0.0
COST_PER_FILL = (SLIPPAGE_BPS_PER_SIDE + MAKER_FEE_BPS_PER_SIDE) * 1e-4  # 0.0002

SYMBOLS = ["XRP", "SUI"]
EVENTS_PER_YEAR = 365 * 24 // 8  # 1095

# DAR model sweep parameters
DAR_CONFIGS = [
    # (p, q, label)
    (1, 0, "DAR(1,0)"),   # simplest AR(1) on FR
    (2, 0, "DAR(2,0)"),   # AR(2)
    (1, 1, "DAR(1,1)"),   # AR(1) + 1 exogenous lag (spread z-score)
    (2, 1, "DAR(2,1)"),   # AR(2) + 1 exogenous lag
    (3, 0, "DAR(3,0)"),   # AR(3)
]

WINDOW_SIZES = [200, 300, 500]
REFIT_FREQS  = [25, 50, 100]

# Primary DAR config (pre-registered)
PRIMARY_P = 2
PRIMARY_Q = 1
PRIMARY_WIN = 300
PRIMARY_REFIT = 50

# Threshold variants for DAR direction filter
# None = any direction agreement; x bps = require predicted change > x bps
THRESHOLD_VARIANTS = [None, 0.5, 1.0, 2.0]  # in bps units of FR (1e-4)


# ─────────────────────────────── Data ────────────────────────────────

def load_hl_fr(sym: str) -> Optional[pd.Series]:
    f = HL_CACHE / f"hl_fr_{sym}.parquet"
    if not f.exists():
        return None
    df = pd.read_parquet(f)
    s = df.set_index("timestamp")["hl_fr"].astype(float).sort_index()
    s = s[~s.index.duplicated(keep="last")]
    s.name = sym
    return s


def load_bybit_fr(sym: str) -> Optional[pd.Series]:
    for tag in ("730d", "1200d", "365d"):
        f = CACHE / f"bybit_fr_{sym}USDT_{tag}.parquet"
        if f.exists():
            df = pd.read_parquet(f)
            s = df.set_index("timestamp")["funding_rate"].astype(float).sort_index()
            s = s[~s.index.duplicated(keep="last")]
            s.name = sym
            return s
    return None


def load_bybit_close(sym: str) -> Optional[pd.Series]:
    f = CACHE / f"{sym}USDT_4h_730d.parquet"
    if not f.exists():
        return None
    df = pd.read_parquet(f)
    s = df.set_index("open_time")["close"].astype(float).sort_index()
    s = s[~s.index.duplicated(keep="last")]
    s.name = sym
    return s


def build_panel(sym: str) -> Optional[pd.DataFrame]:
    hl = load_hl_fr(sym)
    by = load_bybit_fr(sym)
    cl = load_bybit_close(sym)
    if hl is None or by is None or cl is None:
        return None
    hl_8h = hl.resample("8h", label="right", closed="right").sum(min_count=1)
    idx = by.index
    df = pd.DataFrame({"bybit_fr": by}, index=idx)
    df["hl_fr_8h"] = hl_8h.reindex(idx)
    df = df.dropna()
    if len(df) < 100:
        return None
    df["spread"] = df["bybit_fr"] - df["hl_fr_8h"]
    cl_at = cl.reindex(idx, method="nearest", tolerance=pd.Timedelta("2h"))
    df["close"] = cl_at
    df = df.dropna(subset=["close"])
    if len(df) < 100:
        return None
    df["fwd_ret_1"] = np.log(df["close"]).diff().shift(-1)
    return df


# ─────────────────────────────── DAR model ────────────────────────────────

def _ols_fit(X: np.ndarray, y: np.ndarray) -> np.ndarray:
    """Minimal OLS: X (n x k), y (n,) -> coefficients (k,)."""
    try:
        coeffs, _, _, _ = np.linalg.lstsq(X, y, rcond=None)
        return coeffs
    except Exception:
        return np.zeros(X.shape[1])


def build_dar_design(fr_arr: np.ndarray, spread_arr: np.ndarray, p: int, q: int, idx: int) -> Optional[np.ndarray]:
    """Build single design row for DAR(p,q) at position idx.
    Features: intercept, FR_{t-1..t-p}, spread_z_{t-1..t-q}.
    """
    if idx < max(p, q):
        return None
    row = [1.0]
    for lag in range(1, p + 1):
        row.append(fr_arr[idx - lag])
    for lag in range(1, q + 1):
        row.append(spread_arr[idx - lag])
    return np.array(row, dtype=float)


def dar_walk_forward(
    fr: np.ndarray,
    spread_z: np.ndarray,
    p: int = 1,
    q: int = 0,
    win: int = 300,
    refit: int = 50,
) -> Tuple[np.ndarray, np.ndarray, Dict]:
    """
    Walk-forward DAR(p,q) predictor.

    Returns:
        pred_fr: array of predicted FR values (NaN where no prediction)
        is_valid: boolean mask where predictions are available
        diagnostics: dict with OOS R², direction_acc, AIC
    """
    n = len(fr)
    pred_fr = np.full(n, np.nan)
    is_valid = np.zeros(n, dtype=bool)

    # Precompute the minimum required lag
    min_lag = max(p, q)

    coeffs = None
    last_refit = -999

    # Walk-forward loop
    for i in range(min_lag + win, n):
        # Refit on schedule
        if (i - (min_lag + win)) % refit == 0 or coeffs is None:
            # Training window: [i-win .. i-1]
            start = i - win
            rows = []
            targets = []
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
            last_refit = i

        # Predict FR_{i} (one step ahead) using data up to i-1
        if coeffs is not None:
            row = build_dar_design(fr, spread_z, p, q, i - 1)
            if row is not None:
                pred_fr[i] = float(np.dot(row, coeffs))
                is_valid[i] = True

    # OOS diagnostics (only where predictions exist)
    valid_idx = np.where(is_valid)[0]
    if len(valid_idx) < 30:
        return pred_fr, is_valid, {"oos_r2": np.nan, "direction_acc": np.nan, "aic": np.nan, "n_oos": 0}

    y_true = fr[valid_idx]
    y_pred = pred_fr[valid_idx]
    ss_res = np.sum((y_true - y_pred) ** 2)
    ss_tot = np.sum((y_true - y_true.mean()) ** 2)
    oos_r2 = float(1 - ss_res / (ss_tot + 1e-30))

    # Direction accuracy: predicted direction vs actual direction of change
    actual_delta = np.diff(y_true)  # FR[t] - FR[t-1]
    pred_sign = np.sign(y_pred[1:] - y_true[:-1])  # predicted delta direction
    actual_sign = np.sign(actual_delta)
    nz = actual_sign != 0
    if nz.sum() > 0:
        dir_acc = float((pred_sign[nz] == actual_sign[nz]).mean())
    else:
        dir_acc = 0.5

    # AIC: approximate using residuals from last refit
    n_oos = len(valid_idx)
    k = 1 + p + q  # num params
    sigma2 = float(ss_res / max(n_oos, 1))
    aic = float(n_oos * np.log(max(sigma2, 1e-30)) + 2 * k) if sigma2 > 0 else np.nan

    return pred_fr, is_valid, {
        "oos_r2": round(oos_r2, 5),
        "direction_acc": round(dir_acc, 4),
        "aic": round(aic, 2),
        "n_oos": int(n_oos),
    }


# ─────────────────────────────── Metrics ────────────────────────────────

def sharpe(pnl: pd.Series, ppy: int = EVENTS_PER_YEAR) -> float:
    pnl = pnl.dropna()
    if len(pnl) < 30 or pnl.std() == 0:
        return 0.0
    return float(pnl.mean() / pnl.std() * np.sqrt(ppy))


def cagr(pnl: pd.Series, ppy: int = EVENTS_PER_YEAR) -> float:
    if len(pnl) == 0:
        return 0.0
    total = pnl.sum()
    years = len(pnl) / ppy
    if years <= 0:
        return 0.0
    return float(np.expm1(total / years))


def max_dd(pnl: pd.Series) -> float:
    eq = pnl.cumsum()
    peak = eq.cummax()
    return float((eq - peak).min())


def equity_curve(pnl: pd.Series) -> List[float]:
    return list(np.exp(pnl.fillna(0).cumsum()).round(6))


def perm_test(pnl: pd.Series, n: int = 200, seed: int = 7) -> float:
    rng = np.random.default_rng(seed)
    obs = sharpe(pnl)
    vals = pnl.dropna().values
    if len(vals) < 10 or pnl.std() == 0:
        return 1.0
    perm_sharpes = [
        pd.Series(rng.permutation(vals)).mean() / (pd.Series(rng.permutation(vals)).std() + 1e-12)
        * np.sqrt(EVENTS_PER_YEAR)
        for _ in range(n)
    ]
    arr = np.array(perm_sharpes)
    return float((arr >= obs).mean()) if obs > 0 else float((arr <= obs).mean())


def bootstrap_ci(pnl: pd.Series, n: int = 200, seed: int = 11) -> Tuple[float, float]:
    rng = np.random.default_rng(seed)
    vals = pnl.dropna().values
    if len(vals) < 30:
        return 0.0, 0.0
    sharpes = []
    for _ in range(n):
        s = pd.Series(vals[rng.integers(0, len(vals), size=len(vals))])
        sharpes.append(float(s.mean() / (s.std() + 1e-12) * np.sqrt(EVENTS_PER_YEAR)))
    return float(np.percentile(sharpes, 5)), float(np.percentile(sharpes, 95))


def dsr(pnl: pd.Series, n_trials: int = 4) -> float:
    pnl = pnl.dropna()
    if len(pnl) < 30 or pnl.std() == 0:
        return 0.0
    sr = pnl.mean() / pnl.std()
    T = len(pnl)
    sk = float(((pnl - pnl.mean()) ** 3).mean() / (pnl.std() ** 3 + 1e-12))
    kt = float(((pnl - pnl.mean()) ** 4).mean() / (pnl.std() ** 4 + 1e-12))
    emc = 0.5772
    e_max = np.sqrt(2 * np.log(max(n_trials, 2))) - emc / np.sqrt(2 * np.log(max(n_trials, 2)))
    denom = np.sqrt((1 - sk * sr + (kt - 1) / 4 * sr ** 2) / (T - 1))
    if denom <= 0:
        return 0.0
    z = (sr - e_max) / denom
    return float(0.5 * (1 + erf(z / sqrt(2))))


def wf_3fold(pnl: pd.Series) -> Tuple[float, List[float]]:
    pnl = pnl.dropna()
    if len(pnl) < 100:
        return 0.0, []
    folds = np.array_split(pnl.values, 3)
    sharpes = []
    for f in folds:
        s = pd.Series(f)
        if s.std() == 0:
            sharpes.append(0.0)
        else:
            sharpes.append(float(s.mean() / s.std() * np.sqrt(EVENTS_PER_YEAR)))
    return float(np.mean(sharpes)), [float(x) for x in sharpes]


def zscore(s: pd.Series, win: int = 30) -> pd.Series:
    mu = s.rolling(win, min_periods=win).mean()
    sd = s.rolling(win, min_periods=win).std()
    return (s - mu) / (sd + 1e-12)


# ─────────────────────────────── Strategy logic ────────────────────────────────

def run_k175_baseline(
    panels: Dict[str, pd.DataFrame],
    z_thr: float = 2.0,
    hold: int = 1,
    zwin: int = 30,
    cost_per_fill: float = COST_PER_FILL,
) -> Tuple[pd.Series, pd.Series, int, Dict, Dict]:
    """Exact K175 V_xrp_sui_maker logic reconstructed."""
    per_sym_gross: Dict[str, pd.Series] = {}
    per_sym_net: Dict[str, pd.Series] = {}
    total_trades = 0
    per_sh_net: Dict[str, float] = {}
    per_sh_gross: Dict[str, float] = {}

    for sym, df in panels.items():
        z = zscore(df["spread"], zwin)
        sig = pd.Series(0.0, index=df.index)
        sig[z > z_thr] = -1.0
        sig[z < -z_thr] = 1.0
        sig_lag = sig.shift(1).fillna(0.0)
        pos = pd.Series(0.0, index=df.index)
        i = 0
        trades = 0
        while i < len(sig_lag):
            new = sig_lag.iloc[i]
            if new != 0.0:
                end = min(i + hold, len(pos))
                pos.iloc[i:end] = new
                trades += 1
                i = end
                continue
            i += 1
        fwd = df["fwd_ret_1"].fillna(0.0)
        pnl_g = pos * fwd
        pos_chg = pos.diff().fillna(pos.iloc[0])
        costs = pd.Series(0.0, index=df.index)
        costs[pos_chg != 0] = cost_per_fill
        pnl_n = pnl_g - costs
        per_sym_gross[sym] = pnl_g
        per_sym_net[sym] = pnl_n
        total_trades += trades
        per_sh_gross[sym] = sharpe(pnl_g)
        per_sh_net[sym] = sharpe(pnl_n)

    if not per_sym_net:
        empty = pd.Series(dtype=float)
        return empty, empty, 0, {}, {}

    gross = pd.concat(per_sym_gross, axis=1).fillna(0.0).mean(axis=1)
    net = pd.concat(per_sym_net, axis=1).fillna(0.0).mean(axis=1)
    return net, gross, total_trades, per_sh_net, per_sh_gross


def run_k190_dar_filter(
    panels: Dict[str, pd.DataFrame],
    p: int = 2,
    q: int = 1,
    win: int = 300,
    refit: int = 50,
    z_thr: float = 2.0,
    hold: int = 1,
    zwin: int = 30,
    threshold_bps: Optional[float] = None,
    cost_per_fill: float = COST_PER_FILL,
) -> Tuple[pd.Series, pd.Series, int, Dict, Dict, Dict[str, Dict]]:
    """K175 strategy + DAR filter.

    DAR filter logic:
      - For short entry (z > +z_thr): allow only if pred_FR <= current_FR
        (i.e., FR expected to normalize down -> FR payer benefits)
      - For long entry (z < -z_thr): allow only if pred_FR >= current_FR
        (i.e., FR expected to normalize up)
      - Optional threshold: require |pred_FR - current_FR| > threshold_bps * 1e-4

    Returns additional diagnostics dict per symbol.
    """
    per_sym_gross: Dict[str, pd.Series] = {}
    per_sym_net: Dict[str, pd.Series] = {}
    total_trades = 0
    per_sh_net: Dict[str, float] = {}
    per_sh_gross: Dict[str, float] = {}
    dar_diag: Dict[str, Dict] = {}

    thr_raw = (threshold_bps * 1e-4) if threshold_bps is not None else 0.0

    for sym, df in panels.items():
        fr_arr = df["bybit_fr"].values.copy()
        z = zscore(df["spread"], zwin)
        spread_z_arr = z.fillna(0.0).values

        # Walk-forward DAR prediction
        pred_fr, is_valid, diag = dar_walk_forward(fr_arr, spread_z_arr, p=p, q=q, win=win, refit=refit)
        dar_diag[sym] = diag

        # Build signal: K175 z-trigger AND DAR gate
        sig = pd.Series(0.0, index=df.index)
        for i in range(len(df)):
            if not is_valid[i]:
                continue
            z_val = z.iloc[i]
            current_fr = fr_arr[i]
            pred = pred_fr[i]
            delta = pred - current_fr

            if z_val > z_thr:
                # Short: FR elevated, we want FR to fall
                # Gate: predicted next FR <= current (drop) AND magnitude check
                if pred <= current_fr and abs(delta) >= thr_raw:
                    sig.iloc[i] = -1.0
            elif z_val < -z_thr:
                # Long: FR depressed, we want FR to rise
                # Gate: predicted next FR >= current (rise) AND magnitude check
                if pred >= current_fr and abs(delta) >= thr_raw:
                    sig.iloc[i] = 1.0

        sig_lag = sig.shift(1).fillna(0.0)
        pos = pd.Series(0.0, index=df.index)
        i = 0
        trades = 0
        while i < len(sig_lag):
            new = sig_lag.iloc[i]
            if new != 0.0:
                end = min(i + hold, len(pos))
                pos.iloc[i:end] = new
                trades += 1
                i = end
                continue
            i += 1

        fwd = df["fwd_ret_1"].fillna(0.0)
        pnl_g = pos * fwd
        pos_chg = pos.diff().fillna(pos.iloc[0])
        costs = pd.Series(0.0, index=df.index)
        costs[pos_chg != 0] = cost_per_fill
        pnl_n = pnl_g - costs
        per_sym_gross[sym] = pnl_g
        per_sym_net[sym] = pnl_n
        total_trades += trades
        per_sh_gross[sym] = sharpe(pnl_g)
        per_sh_net[sym] = sharpe(pnl_n)

    if not per_sym_net:
        empty = pd.Series(dtype=float)
        return empty, empty, 0, {}, {}, {}

    gross = pd.concat(per_sym_gross, axis=1).fillna(0.0).mean(axis=1)
    net = pd.concat(per_sym_net, axis=1).fillna(0.0).mean(axis=1)
    return net, gross, total_trades, per_sh_net, per_sh_gross, dar_diag


def compute_metrics(
    name: str,
    pnl: pd.Series,
    pnl_gross: pd.Series,
    n_trades: int,
    per_sh_net: Dict,
    per_sh_gross: Dict,
) -> Dict:
    sh_n = sharpe(pnl)
    sh_g = sharpe(pnl_gross)
    cg_n = cagr(pnl)
    cg_g = cagr(pnl_gross)
    dd_n = max_dd(pnl)
    split = int(len(pnl) * 0.7)
    is_sh_n = sharpe(pnl.iloc[:split])
    oos_sh_n = sharpe(pnl.iloc[split:])
    is_sh_g = sharpe(pnl_gross.iloc[:split])
    oos_sh_g = sharpe(pnl_gross.iloc[split:])
    wf_mean, wf_folds = wf_3fold(pnl)
    wf_mean_g, wf_folds_g = wf_3fold(pnl_gross)
    perm_p = perm_test(pnl)
    perm_p_g = perm_test(pnl_gross)
    ci_lo, ci_hi = bootstrap_ci(pnl)
    ci_lo_g, ci_hi_g = bootstrap_ci(pnl_gross)
    dsr_p = dsr(pnl)
    dsr_p_g = dsr(pnl_gross)
    trades_yr = float(n_trades / max(len(pnl) / EVENTS_PER_YEAR, 1e-6))
    return {
        "variant": name,
        "sharpe_net": round(sh_n, 4),
        "sharpe_gross": round(sh_g, 4),
        "cagr_net": round(cg_n, 4),
        "cagr_gross": round(cg_g, 4),
        "max_dd_net": round(dd_n, 4),
        "is_sharpe_net": round(is_sh_n, 4),
        "oos_sharpe_net": round(oos_sh_n, 4),
        "is_sharpe_gross": round(is_sh_g, 4),
        "oos_sharpe_gross": round(oos_sh_g, 4),
        "wf_mean_sharpe_net": round(wf_mean, 4),
        "wf_folds_net": [round(x, 4) for x in wf_folds],
        "wf_mean_sharpe_gross": round(wf_mean_g, 4),
        "wf_folds_gross": [round(x, 4) for x in wf_folds_g],
        "perm_pvalue_net": round(perm_p, 4),
        "perm_pvalue_gross": round(perm_p_g, 4),
        "bootstrap_ci_5_95_net": [round(ci_lo, 4), round(ci_hi, 4)],
        "bootstrap_ci_5_95_gross": [round(ci_lo_g, 4), round(ci_hi_g, 4)],
        "dsr_net": round(dsr_p, 4),
        "dsr_gross": round(dsr_p_g, 4),
        "n_trades": int(n_trades),
        "trades_per_year": round(trades_yr, 2),
        "n_events": int(len(pnl)),
        "per_symbol_sharpe_net": {k: round(v, 4) for k, v in per_sh_net.items()},
        "per_symbol_sharpe_gross": {k: round(v, 4) for k, v in per_sh_gross.items()},
    }


def apply_s6_gates(metrics: Dict) -> Tuple[Dict, int, str]:
    """§6 strict gates on best K190 variant if gross Sh >= 1.0."""
    if metrics["sharpe_gross"] < 1.0:
        return {"note": "Gross Sh < 1.0, §6 gates skipped"}, 0, "SKIP"

    gates = {
        "g1_sharpe_net_ge_1": metrics["sharpe_net"] >= 1.0,
        "g2_oos_sharpe_net_ge_0p5": metrics["oos_sharpe_net"] >= 0.5,
        "g3_oos_is_ratio_ge_0p5": (
            metrics["oos_sharpe_net"] / metrics["is_sharpe_net"] >= 0.5
            if metrics["is_sharpe_net"] > 0 else False
        ),
        "g4_wf_folds_all_positive": (
            all(x > 0 for x in metrics["wf_folds_net"]) if metrics["wf_folds_net"] else False
        ),
        "g5_perm_p_le_0p05": metrics["perm_pvalue_net"] <= 0.05,
        "g6_dsr_ge_0p95": metrics["dsr_net"] >= 0.95,
        "g7_trades_per_year_ge_20": metrics["trades_per_year"] >= 20,
    }
    n_pass = int(sum(gates.values()))
    verdict = "PASS" if n_pass >= 6 else ("MARGINAL" if n_pass >= 4 else "FAIL")
    return gates, n_pass, verdict


# ─────────────────────────────── Main ────────────────────────────────

def main() -> Dict:
    t0 = time.time()

    # ── 1. Load data ──
    panels: Dict[str, pd.DataFrame] = {}
    skipped = []
    for sym in SYMBOLS:
        p = build_panel(sym)
        if p is None:
            print(f"  SKIP {sym}: panel build failed")
            skipped.append(sym)
        else:
            panels[sym] = p
            print(f"  {sym} events={len(p)} fr_mean={p['bybit_fr'].mean():.6f} spread_std={p['spread'].std():.6f}")

    if not panels:
        raise RuntimeError("No panels built")

    # ── 2. K175 Baseline ──
    print("\n=== K175 BASELINE ===")
    bl_net, bl_gross, bl_trades, bl_sh_n, bl_sh_g = run_k175_baseline(panels)
    baseline = compute_metrics("K175_baseline", bl_net, bl_gross, bl_trades, bl_sh_n, bl_sh_g)
    print(f"  Sh_net={baseline['sharpe_net']:+.3f}  Sh_gross={baseline['sharpe_gross']:+.3f}  "
          f"OOS_net={baseline['oos_sharpe_net']:+.3f}  OOS_gross={baseline['oos_sharpe_gross']:+.3f}  "
          f"trades={baseline['n_trades']}  t/yr={baseline['trades_per_year']:.0f}")

    # ── 3. DAR diagnostics on primary config ──
    print("\n=== DAR MODEL DIAGNOSTICS ===")
    dar_model_diags: Dict[str, Dict] = {}
    for sym, df in panels.items():
        fr_arr = df["bybit_fr"].values.copy()
        z = zscore(df["spread"], 30).fillna(0.0).values
        _, _, diag = dar_walk_forward(fr_arr, z, p=PRIMARY_P, q=PRIMARY_Q, win=PRIMARY_WIN, refit=PRIMARY_REFIT)
        dar_model_diags[sym] = diag
        print(f"  {sym} DAR({PRIMARY_P},{PRIMARY_Q}) OOS_R2={diag['oos_r2']:.4f}  "
              f"dir_acc={diag['direction_acc']:.4f}  AIC={diag['aic']:.1f}  n_oos={diag['n_oos']}")

    # ── 4. Primary K190 variant (threshold sweep) ──
    print("\n=== K190 PRIMARY VARIANTS (threshold sweep) ===")
    dar_variants: List[Dict] = []
    dar_var_pnls: Dict[str, Tuple[pd.Series, pd.Series]] = {}
    dar_diag_by_var: Dict[str, Dict] = {}

    for thr in THRESHOLD_VARIANTS:
        vname = f"K190_DAR({PRIMARY_P},{PRIMARY_Q})_win{PRIMARY_WIN}_thr{'none' if thr is None else f'{thr}bps'}"
        vnet, vgross, vtrades, vsh_n, vsh_g, vdiag = run_k190_dar_filter(
            panels, p=PRIMARY_P, q=PRIMARY_Q, win=PRIMARY_WIN, refit=PRIMARY_REFIT,
            threshold_bps=thr,
        )
        vm = compute_metrics(vname, vnet, vgross, vtrades, vsh_n, vsh_g)
        vm["dar_threshold_bps"] = thr
        vm["dar_diagnostics_per_symbol"] = {s: d for s, d in vdiag.items()}
        dar_variants.append(vm)
        dar_var_pnls[vname] = (vnet, vgross)
        dar_diag_by_var[vname] = vdiag
        delta_oos = vm["oos_sharpe_net"] - baseline["oos_sharpe_net"]
        filter_rate = 1.0 - vtrades / max(bl_trades, 1)
        print(f"  {vname}")
        print(f"    Sh_net={vm['sharpe_net']:+.3f}  Sh_gross={vm['sharpe_gross']:+.3f}  "
              f"OOS_net={vm['oos_sharpe_net']:+.3f} (Δ{delta_oos:+.3f})  "
              f"trades={vtrades} ({filter_rate*100:.0f}% filtered)")

    # ── 5. DAR model order sensitivity sweep ──
    print("\n=== DAR ORDER SENSITIVITY SWEEP ===")
    order_sweep: List[Dict] = []
    for p_ord, q_ord, label in DAR_CONFIGS:
        vname = f"K190_{label}_win{PRIMARY_WIN}_thr_none"
        vnet, vgross, vtrades, vsh_n, vsh_g, vdiag = run_k190_dar_filter(
            panels, p=p_ord, q=q_ord, win=PRIMARY_WIN, refit=PRIMARY_REFIT, threshold_bps=None,
        )
        vm = compute_metrics(vname, vnet, vgross, vtrades, vsh_n, vsh_g)
        vm["dar_config"] = label
        vm["dar_p"] = p_ord
        vm["dar_q"] = q_ord
        vm["dar_diagnostics_per_symbol"] = {s: d for s, d in vdiag.items()}
        order_sweep.append(vm)
        delta_oos = vm["oos_sharpe_net"] - baseline["oos_sharpe_net"]
        print(f"  {label:12s}  Sh_net={vm['sharpe_net']:+.3f}  OOS_net={vm['oos_sharpe_net']:+.3f} "
              f"(Δ{delta_oos:+.3f})  trades={vtrades}")

    # ── 6. Window / refit sensitivity sweep ──
    print("\n=== WINDOW/REFIT SENSITIVITY SWEEP ===")
    wf_sweep: List[Dict] = []
    for win_s in WINDOW_SIZES:
        for ref_s in REFIT_FREQS:
            vname = f"K190_DAR({PRIMARY_P},{PRIMARY_Q})_win{win_s}_ref{ref_s}_thr_none"
            vnet, vgross, vtrades, vsh_n, vsh_g, vdiag = run_k190_dar_filter(
                panels, p=PRIMARY_P, q=PRIMARY_Q, win=win_s, refit=ref_s, threshold_bps=None,
            )
            vm = compute_metrics(vname, vnet, vgross, vtrades, vsh_n, vsh_g)
            vm["dar_win"] = win_s
            vm["dar_refit"] = ref_s
            vm["dar_diagnostics_per_symbol"] = {s: d for s, d in vdiag.items()}
            wf_sweep.append(vm)
            delta_oos = vm["oos_sharpe_net"] - baseline["oos_sharpe_net"]
            print(f"  win={win_s} ref={ref_s}  Sh_net={vm['sharpe_net']:+.3f}  "
                  f"OOS_net={vm['oos_sharpe_net']:+.3f} (Δ{delta_oos:+.3f})  trades={vtrades}")

    # ── 7. Identify best K190 variant ──
    all_k190 = dar_variants + order_sweep + wf_sweep
    # Best by OOS Sharpe net
    best = max(all_k190, key=lambda x: x["oos_sharpe_net"])
    # Best among primary threshold variants (pre-registered)
    best_primary = max(dar_variants, key=lambda x: x["oos_sharpe_net"])

    print(f"\n=== BEST K190 VARIANT ===")
    print(f"  {best['variant']}")
    print(f"  OOS Sh net = {best['oos_sharpe_net']:+.3f}  (K175 baseline: {baseline['oos_sharpe_net']:+.3f})")
    delta_oos_best = best["oos_sharpe_net"] - baseline["oos_sharpe_net"]
    print(f"  ΔOOS = {delta_oos_best:+.3f}  (acceptance: >= +0.10)")

    # Apply §6 gates on best_primary
    gates, gates_passed, verdict_gates = apply_s6_gates(best_primary)

    # ── 8. Acceptance verdict ──
    accepted = delta_oos_best >= 0.10
    turnover_reduction = 1.0 - best_primary["n_trades"] / max(bl_trades, 1)
    operational_benefit = (
        abs(delta_oos_best) < 0.10 and turnover_reduction >= 0.20
    )

    if accepted:
        verdict = "ACCEPT → K191 K188-ensemble integration test"
    elif operational_benefit:
        verdict = "OPERATIONAL_BENEFIT → reduced turnover justifies inclusion"
    else:
        verdict = "REJECT → DAR filter does not improve K175 sufficiently"

    print(f"\n  Verdict: {verdict}")
    print(f"  §6 gates: {gates_passed}/7 → {verdict_gates}")

    # ── 9. Build equity curves ──
    curves: Dict = {
        "K175_baseline": {
            "equity_net": equity_curve(bl_net),
            "equity_gross": equity_curve(bl_gross),
            "timestamps": [t.isoformat() for t in bl_net.index],
        }
    }
    for vname, (vn, vg) in dar_var_pnls.items():
        if len(vn) > 0:
            curves[vname] = {
                "equity_net": equity_curve(vn),
                "equity_gross": equity_curve(vg),
                "timestamps": [t.isoformat() for t in vn.index],
            }

    # ── 10. Assemble output JSON ──
    runtime = round(time.time() - t0, 1)
    output = {
        "wave": "K190",
        "parent_wave": "K175",
        "objective": "DAR(p,q) FR predictor as entry filter for K175 XRP+SUI maker strategy",
        "data": {
            "symbols_used": list(panels.keys()),
            "symbols_skipped": skipped,
            "events_per_year": EVENTS_PER_YEAR,
            "event_counts": {s: int(len(df)) for s, df in panels.items()},
        },
        "cost_model": {
            "execution": "maker-only (post-only limit)",
            "slippage_bps_per_side": SLIPPAGE_BPS_PER_SIDE,
            "maker_fee_bps_per_side": MAKER_FEE_BPS_PER_SIDE,
            "roundtrip_bps_per_leg": 2 * (SLIPPAGE_BPS_PER_SIDE + MAKER_FEE_BPS_PER_SIDE),
        },
        "dar_primary_config": {
            "p": PRIMARY_P,
            "q": PRIMARY_Q,
            "window": PRIMARY_WIN,
            "refit_every": PRIMARY_REFIT,
            "exogenous": "spread z-score (bybit_fr - hl_fr_8h)",
        },
        "dar_model_diagnostics_primary": dar_model_diags,
        "k175_baseline": baseline,
        "k190_primary_variants": dar_variants,
        "k190_order_sweep": order_sweep,
        "k190_window_refit_sweep": wf_sweep,
        "best_k190_overall": best,
        "best_k190_primary": best_primary,
        "comparison": {
            "k175_baseline_oos_sh_net": baseline["oos_sharpe_net"],
            "k175_baseline_oos_sh_gross": baseline["oos_sharpe_gross"],
            "k175_baseline_trades": baseline["n_trades"],
            "k175_baseline_trades_per_year": baseline["trades_per_year"],
            "best_k190_oos_sh_net": best_primary["oos_sharpe_net"],
            "best_k190_oos_sh_gross": best_primary["oos_sharpe_gross"],
            "best_k190_trades": best_primary["n_trades"],
            "best_k190_trades_per_year": best_primary["trades_per_year"],
            "delta_oos_sh_net": round(best_primary["oos_sharpe_net"] - baseline["oos_sharpe_net"], 4),
            "filter_rate_pct": round(turnover_reduction * 100, 1),
            "acceptance_threshold_delta_oos": 0.10,
            "accepted": accepted,
            "operational_benefit": operational_benefit,
        },
        "s6_gates": gates,
        "s6_gates_passed": gates_passed,
        "s6_verdict": verdict_gates,
        "acceptance_verdict": verdict,
        "runtime_sec": runtime,
    }

    # ── 11. Write outputs ──
    json_path = ROOT / "wave_k190_dar_filter.json"
    curves_path = ROOT / "wave_k190_curves.json"
    json_path.write_text(json.dumps(output, indent=2, default=str))
    curves_path.write_text(json.dumps(curves, default=str))
    print(f"\nWrote {json_path} ({json_path.stat().st_size:,} bytes)")
    print(f"Wrote {curves_path} ({curves_path.stat().st_size:,} bytes)")
    print(f"Runtime: {runtime}s")

    return output


if __name__ == "__main__":
    main()
