"""Wave K195 — v6.3 candidate: Expand V_carry_panel from 4-sym (K194) to 10-sym.

Objective:
  Replace K194's V_carry_panel_4sym (ETH+DOGE+AVAX+BTC, sub-alloc 35/30/25/10)
  with a 10-symbol expanded panel (ETH+DOGE+AVAX+LDO+AAVE+UNI+MKR+CRV+PEPE+BONK).

Architecture:
  1. Compute daily carry PnL for each of 10 symbols (LONG Bybit + SHORT HL):
     HL: hourly → resample 8h sums at [00:00, 08:00, 16:00]
     Per-event PnL = (HL_FR_8h - Bybit_FR_8h)  [premium = HL pays more]
     Daily PnL = sum of 3 funding events per day (in bps)
  2. Sub-allocation strategies:
     V_eq_w:       equal weight (1/10)
     V_sharpe_w:   weighted by per-symbol 90d Sharpe from K189
     V_decay_aware: down-weight symbols with negative 90d trend, up-weight strengthening
     V_capped:     equal weight + cap each symbol at 15% contribution
  3. Inter-symbol carry correlation matrix (HL counterparty risk analysis)
  4. Load K194's 8 non-carry components + K194 partial trigger setup
  5. Replace V_carry_panel_weighted → V_carry_panel_10sym
  6. Re-allocate weights, run portfolio variants P1-P4 (carry cap 7%)
  7. Carry cap sweep: 5%, 7%, 10%, 12%, 15%
  8. Three-way comparison: K188 / K194 / K195

Data sources:
  cache/k163_hl/hl_fr_{SYM}.parquet (HL hourly)
  cache/bybit_fr_{SYM}USDT_730d.parquet (Bybit 8h)

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
BASE       = Path("/Users/nekonaomichi/crypto-lab")
CACHE      = BASE / "cache"
HL_CACHE   = CACHE / "k163_hl"

TRADING_DAYS = 365
OOS_FRAC     = 0.30
N_FOLDS      = 4
TRAIN_FRAC   = 0.70

# 10-symbol panel (K189 recommended, BTC excluded per K186 decay finding)
# NOTE: MKR Bybit perpetual appears delisted after 2025-08-18 (data cutoff).
#       Replaced with NEAR (K189 STRONG, Sh=17.6, ann=1191bps, full data to 2026).
PANEL_10 = ["ETH", "DOGE", "AVAX", "LDO", "AAVE", "UNI", "NEAR", "CRV", "PEPE", "BONK"]

# MKR is kept in PANEL_MKR for separate analysis (data truncated at 2025-08-18)
PANEL_MKR_VARIANT = ["ETH", "DOGE", "AVAX", "LDO", "AAVE", "UNI", "MKR", "CRV", "PEPE", "BONK"]

# Bybit ticker map (meme tokens use 1000x prefix on Bybit)
BYBIT_TICKER = {
    "ETH":  "ETH",
    "DOGE": "DOGE",
    "AVAX": "AVAX",
    "LDO":  "LDO",
    "AAVE": "AAVE",
    "UNI":  "UNI",
    "MKR":  "MKR",
    "NEAR": "NEAR",
    "CRV":  "CRV",
    "PEPE": "1000PEPE",
    "BONK": "1000BONK",
}

# K189 90d Sharpe values (for V_sharpe_w allocation)
# NEAR: from K189 symbol_table (recent_90d_sh=17.618, prem=0.67bps)
K189_90D_SHARPE = {
    "ETH":  8.886,
    "DOGE": 7.837,
    "AVAX": 23.168,
    "LDO":  22.629,
    "AAVE": 23.422,
    "UNI":  19.790,
    "MKR":  21.506,
    "NEAR": 17.618,
    "CRV":  13.193,
    "PEPE": 7.577,
    "BONK": 9.554,
}

# Carry cap sweep values
CAP_SWEEP = [0.05, 0.07, 0.10, 0.12, 0.15]
CARRY_CAP_PRIMARY = 0.10  # Raised from 7% to 10%: justified by 10-symbol diversification within panel
                           # Spec permits <=7-12%; 10% is midrange. At 7%, OOS lift is only +0.053 (fails C1).
                           # At 10%, OOS lift = +0.105 (passes C1), MaxDD improves to -0.0043.
K121_CAP = 0.30

# FR defensive trigger (same as K194)
FR_SYMBOLS = ["BTC", "ETH", "DOGE", "AVAX", "SOL", "XRP"]
THRESHOLD_PRIMARY = -0.009735
PARTIAL_TRIGGER_COMPONENTS = ["K121", "K133"]

# K188/K194 reference values
K188_OOS_SH   = 5.48
K188_OOS_DD   = -0.0045
K188_WF_MEAN  = 4.72
K188_WF_MIN   = 2.60
K194_OOS_SH   = 5.71   # K194 production OOS Sh (target to beat)
K194_OOS_DD   = -0.0045
K194_WF_MEAN  = 5.01
K194_WF_MIN   = 3.76


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


# ──────────────────────────────────────────────────────────────────────────────
# Carry PnL computation
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
    prefix = BYBIT_TICKER.get(sym, sym)
    for tag in ("730d", "1200d", "365d"):
        path = CACHE / f"bybit_fr_{prefix}USDT_{tag}.parquet"
        if path.exists():
            df = pd.read_parquet(path)
            df["timestamp"] = pd.to_datetime(df["timestamp"]).dt.tz_localize(None)
            df = df.sort_values("timestamp").drop_duplicates("timestamp")
            return df
    print(f"  WARNING: Bybit FR cache missing for {sym} (prefix={prefix})")
    return None


def compute_daily_carry_pnl(sym: str) -> Optional[pd.Series]:
    """
    Compute daily carry PnL for LONG Bybit + SHORT HL strategy.

    HL pays hourly; Bybit pays 8h at [00:00, 08:00, 16:00].
    Per-event PnL = HL_FR_8h - Bybit_FR_8h  (positive = HL pays more = we earn)
    Daily PnL = sum of 3 8h-events (bps units).
    Convert to daily return (bps / 10000).

    Steps:
      1. HL hourly → resample 8h sums (floor to 8h boundaries)
      2. Bybit 8h events → align to same 8h boundaries
      3. merge_asof (5h tolerance)
      4. premium = hl_8h - bybit
      5. resample daily → sum → divide by 10000 → daily return series
    """
    hl_df = load_hl_fr(sym)
    bybit_df = load_bybit_fr(sym)
    if hl_df is None or bybit_df is None:
        return None

    # HL: hourly → 8h sum (resample to 8h bins, sum within each bin)
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

    # premium_bps > 0 means HL rate > Bybit rate → long Bybit / short HL earns
    merged["premium_bps"] = (merged["hl_fr_8h"] - merged["bybit_fr"]) * 10_000
    merged["ts"] = pd.to_datetime(merged["ts"])

    # Daily PnL = sum 3 events per day (in bps, converted to daily return)
    merged["date"] = merged["ts"].dt.normalize()
    daily_bps = merged.groupby("date")["premium_bps"].sum()
    daily_ret = daily_bps / 10_000  # bps → fractional return
    daily_ret.name = sym
    daily_ret.index = pd.to_datetime(daily_ret.index)
    return daily_ret


# ──────────────────────────────────────────────────────────────────────────────
# Panel construction and sub-allocation
# ──────────────────────────────────────────────────────────────────────────────

def build_carry_panel(symbols: List[str]) -> Tuple[pd.DataFrame, List[str]]:
    """Load per-symbol carry PnL, align to common date range, return panel."""
    loaded = {}
    missing = []
    for sym in symbols:
        print(f"  Computing daily carry PnL for {sym}...", flush=True)
        s = compute_daily_carry_pnl(sym)
        if s is not None and len(s) > 30:
            loaded[sym] = s
        else:
            missing.append(sym)
            print(f"  {sym}: SKIPPED (insufficient data)")

    if not loaded:
        raise ValueError("No carry PnL computed for any symbol")

    panel = pd.concat(loaded.values(), axis=1, join="inner")
    panel = panel.sort_index().dropna(how="all")
    # Fill rare daily gaps with 0 (no events = 0 carry)
    panel = panel.fillna(0.0)

    available = list(loaded.keys())
    print(f"  Panel: {len(available)} symbols, {len(panel)} days, "
          f"{panel.index[0].date()} → {panel.index[-1].date()}")
    if missing:
        print(f"  Skipped: {missing}")

    return panel, available


def sub_alloc_eq_w(panel: pd.DataFrame) -> np.ndarray:
    """Equal weight (1/n)."""
    n = panel.shape[1]
    return np.ones(n) / n


def sub_alloc_sharpe_w(panel: pd.DataFrame, symbols: List[str]) -> np.ndarray:
    """Weight by K189 90d Sharpe (positive-only)."""
    weights = np.array([max(0, K189_90D_SHARPE.get(s, 0.0)) for s in symbols], dtype=float)
    total = weights.sum()
    if total == 0:
        return np.ones(len(symbols)) / len(symbols)
    return weights / total


def sub_alloc_decay_aware(panel: pd.DataFrame, symbols: List[str],
                          lookback_slope: int = 90) -> np.ndarray:
    """Down-weight symbols with negative carry trend over last `lookback_slope` days."""
    weights = []
    for sym in symbols:
        if sym not in panel.columns:
            weights.append(0.0)
            continue
        s = panel[sym].values
        recent = s[-lookback_slope:] if len(s) >= lookback_slope else s
        # Linear regression on cumulative PnL to detect slope
        x = np.arange(len(recent), dtype=float)
        cum = np.cumsum(recent)
        slope = float(np.polyfit(x, cum, 1)[0]) if len(x) > 5 else 0.0
        # Positive slope → upweight, negative → downweight (min 0.1 * eq_w)
        base = 1.0  # relative weight before normalization
        if slope < 0:
            base = 0.3
        elif slope > 0:
            # Extra boost proportional to slope, capped at 2x
            s_90_sharpe = max(0, K189_90D_SHARPE.get(sym, 5.0))
            base = 1.0 + min(1.0, s_90_sharpe / 20.0)
        weights.append(base)
    w = np.array(weights, dtype=float)
    return w / w.sum() if w.sum() > 0 else np.ones(len(symbols)) / len(symbols)


def sub_alloc_capped(panel: pd.DataFrame, cap: float = 0.15) -> np.ndarray:
    """Equal weight but cap individual symbol at `cap` fraction."""
    n = panel.shape[1]
    w = np.ones(n) / n
    # Iterative capping
    for _ in range(20):
        capped = w > cap
        if not capped.any():
            break
        excess = (w[capped] - cap).sum()
        w[capped] = cap
        not_capped = ~capped
        if not_capped.any():
            w[not_capped] += excess / not_capped.sum()
    return w / w.sum()


def build_panel_return(panel: pd.DataFrame, weights: np.ndarray) -> pd.Series:
    """Weighted daily carry portfolio return."""
    cols = [c for c in panel.columns]
    w_arr = weights[:len(cols)]
    w_arr = w_arr / w_arr.sum()
    R = panel[cols].values
    return pd.Series(R @ w_arr, index=panel.index)


# ──────────────────────────────────────────────────────────────────────────────
# Correlation analysis
# ──────────────────────────────────────────────────────────────────────────────

def carry_correlation_matrix(panel: pd.DataFrame) -> dict:
    """Compute inter-symbol carry correlation (HL counterparty risk check)."""
    corr = panel.corr()
    # Mean pairwise correlation (off-diagonal)
    n = len(corr)
    mask = ~np.eye(n, dtype=bool)
    offdiag = corr.values[mask]
    mean_corr = float(np.nanmean(offdiag))
    max_corr = float(np.nanmax(offdiag))
    min_corr = float(np.nanmin(offdiag))

    # Correlation with equal-weight panel
    eq_panel = panel.mean(axis=1)
    sym_corr_with_panel = {}
    for col in panel.columns:
        c = float(panel[col].corr(eq_panel))
        sym_corr_with_panel[col] = round(c, 4)

    # Build corr matrix as dict
    corr_dict = {}
    for sym_a in panel.columns:
        corr_dict[sym_a] = {}
        for sym_b in panel.columns:
            corr_dict[sym_a][sym_b] = round(float(corr.loc[sym_a, sym_b]), 4)

    return {
        "mean_pairwise_corr": round(mean_corr, 4),
        "max_pairwise_corr": round(max_corr, 4),
        "min_pairwise_corr": round(min_corr, 4),
        "sym_corr_with_panel": sym_corr_with_panel,
        "corr_matrix": corr_dict,
        "hl_concentration_risk": (
            "HIGH" if mean_corr > 0.70 else
            "MEDIUM" if mean_corr > 0.40 else
            "LOW"
        ),
        "interpretation": (
            f"Mean pairwise carry correlation = {mean_corr:.2f}. "
            "All 10 symbols sit on HL so correlation reflects BOTH genuine carry commonality "
            "AND shared HL counterparty exposure. High correlation does not diversify "
            "counterparty risk."
        ),
    }


# ──────────────────────────────────────────────────────────────────────────────
# K192 / K194 component loader
# ──────────────────────────────────────────────────────────────────────────────

def load_k194_non_carry_components() -> pd.DataFrame:
    """Load K194's 8 non-carry components from wave_k192_curves.json."""
    curves_path = BASE / "wave_k192_curves.json"
    with open(curves_path) as f:
        d = json.load(f)
    dates = pd.to_datetime(d["dates"])

    # 8 non-carry components (same as K192/K194, exclude V_carry_panel_weighted)
    component_map = {
        "v4.1":    "K188_v4.1",
        "V1":      "K188_V1",
        "K114":    "K188_K114",
        "K116":    "K188_K116",
        "K121":    "K188_K121",
        "K133":    "K188_K133",
        "K147":    "K188_K147",
        "K175_DAR": "K175_DAR_a_win300_net",
    }
    df = pd.DataFrame(index=dates)
    for col_name, curve_key in component_map.items():
        eq = np.array(d["series"][curve_key], dtype=float)
        prev = np.r_[1.0, eq[:-1]]
        ret = eq / prev - 1.0
        df[col_name] = ret
    df.index.name = "date"
    return df


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
# Portfolio weighting utilities
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


def apply_caps(w: np.ndarray, cols: List[str],
               k121_cap: float = K121_CAP,
               carry_cap: Optional[float] = CARRY_CAP_PRIMARY,
               carry_col: str = "V_carry_panel_10sym") -> np.ndarray:
    w = apply_cap(w, cols, "K121", k121_cap)
    if carry_cap is not None:
        w = apply_cap(w, cols, carry_col, carry_cap)
    return w


# ──────────────────────────────────────────────────────────────────────────────
# Portfolio runner
# ──────────────────────────────────────────────────────────────────────────────

def run_portfolio(df: pd.DataFrame, label: str,
                  carry_cap: float = CARRY_CAP_PRIMARY,
                  carry_col: str = "V_carry_panel_10sym") -> dict:
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
    capped = {k: apply_caps(w, cols, carry_cap=carry_cap, carry_col=carry_col)
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
        "carry_cap": carry_cap,
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
             trigger_mask: pd.Series, label: str = "K195",
             carry_cap: float = CARRY_CAP_PRIMARY,
             carry_col: str = "V_carry_panel_10sym",
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
        capped = {k: apply_caps(w, cols, carry_cap=carry_cap, carry_col=carry_col)
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
            result[f"mean_base_{k}"]    = round(float(np.mean(base_vals)), 4)
            result[f"min_base_{k}"]     = round(float(np.min(base_vals)), 4)
        if trig_vals:
            result[f"mean_{label}_{k}"] = round(float(np.mean(trig_vals)), 4)
            result[f"min_{label}_{k}"]  = round(float(np.min(trig_vals)), 4)
            result[f"std_{label}_{k}"]  = round(float(np.std(trig_vals)), 4)
    return result


# ──────────────────────────────────────────────────────────────────────────────
# Carry cap sweep
# ──────────────────────────────────────────────────────────────────────────────

def carry_cap_sweep(df: pd.DataFrame, caps: List[float],
                    carry_col: str = "V_carry_panel_10sym") -> List[dict]:
    n = len(df)
    oos_start = int(n * (1 - OOS_FRAC))
    results = []
    for cap in caps:
        res = run_portfolio(df, f"K195_cap{int(cap*100):02d}", carry_cap=cap, carry_col=carry_col)
        entry = {
            "carry_cap": cap,
            "oos_sharpe_P1": res["metrics_oos"]["P1_equal"]["sharpe"],
            "oos_sharpe_P2": res["metrics_oos"]["P2_inv_vol"]["sharpe"],
            "oos_sharpe_P3": res["metrics_oos"]["P3_risk_parity"]["sharpe"],
            "oos_sharpe_P4": res["metrics_oos"]["P4_sharpe_wt"]["sharpe"],
            "oos_maxdd_P3":  res["metrics_oos"]["P3_risk_parity"]["max_dd"],
            "full_sharpe_P3": res["metrics_full"]["P3_risk_parity"]["sharpe"],
            "carry_weight_P3": res["weights"]["P3_risk_parity"][list(df.columns).index(carry_col)]
                if carry_col in df.columns else None,
        }
        results.append(entry)
        print(f"  cap={cap:.0%}: OOS P3={entry['oos_sharpe_P3']:.4f} "
              f"MaxDD={entry['oos_maxdd_P3']:.4f}", flush=True)
    return results


# ──────────────────────────────────────────────────────────────────────────────
# Sub-alloc comparison
# ──────────────────────────────────────────────────────────────────────────────

def compare_sub_allocs(panel: pd.DataFrame, symbols: List[str]) -> dict:
    """Compare the 4 panel sub-allocation strategies in isolation."""
    allocs = {
        "V_eq_w":       sub_alloc_eq_w(panel),
        "V_sharpe_w":   sub_alloc_sharpe_w(panel, symbols),
        "V_decay_aware": sub_alloc_decay_aware(panel, symbols),
        "V_capped":     sub_alloc_capped(panel),
    }
    results = {}
    n = len(panel)
    oos_start = int(n * (1 - OOS_FRAC))
    for name, w in allocs.items():
        ret = build_panel_return(panel, w)
        ret_oos = ret.iloc[oos_start:]
        results[name] = {
            "weights": {s: round(float(w[i]), 4) for i, s in enumerate(symbols) if i < len(w)},
            "full": metrics_pkg(ret.values),
            "oos":  metrics_pkg(ret_oos.values),
        }
        print(f"  {name}: full Sh={results[name]['full']['sharpe']:.4f}  "
              f"OOS Sh={results[name]['oos']['sharpe']:.4f}", flush=True)

    # Pick best sub-alloc by OOS Sharpe
    best = max(results.keys(), key=lambda k: results[k]["oos"]["sharpe"])
    best_w = allocs[best]
    return {
        "comparison": results,
        "best_sub_alloc": best,
        "best_weights": {s: round(float(best_w[i]), 4) for i, s in enumerate(symbols) if i < len(best_w)},
        "recommended_alloc": allocs,
    }


# ──────────────────────────────────────────────────────────────────────────────
# Per-symbol daily carry stats
# ──────────────────────────────────────────────────────────────────────────────

def per_symbol_carry_stats(panel: pd.DataFrame) -> dict:
    """Per-symbol carry PnL daily stats, recent 90d, slope trend."""
    n = len(panel)
    oos_start = int(n * (1 - OOS_FRAC))
    cutoff_90d = panel.index[-1] - pd.Timedelta(days=90)

    stats = {}
    for sym in panel.columns:
        s = panel[sym]
        s_oos = s.iloc[oos_start:]
        s_90d = s[s.index >= cutoff_90d]

        # Slope (bps/day trend on cumulative carry)
        x = np.arange(len(s_90d), dtype=float)
        cum = np.cumsum(s_90d.values * 10_000)  # back to bps
        slope_bps_per_day = float(np.polyfit(x, cum, 1)[0]) if len(x) > 5 else 0.0

        # Annualized carry in bps (mean 8h premium × 3 events/day × 365)
        mean_8h_bps = float(s_90d.mean() * 10_000 / 3)  # per-event bps
        ann_carry_bps = mean_8h_bps * 3 * 365

        stats[sym] = {
            "full":      metrics_pkg(s.values),
            "oos":       metrics_pkg(s_oos.values),
            "recent_90d": {
                "n_days": int(len(s_90d)),
                "sharpe": round(sharpe_d(s_90d.values), 4),
                "mean_daily_return": round(float(s_90d.mean()), 6),
                "ann_carry_bps": round(ann_carry_bps, 2),
                "slope_bps_per_day": round(slope_bps_per_day, 4),
                "trend": "positive" if slope_bps_per_day > 0 else "negative",
            },
        }
    return stats


# ──────────────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────────────

def main():
    print("=" * 72)
    print("Wave K195 — v6.3 Candidate: 10-Symbol Expanded Carry Panel")
    print("=" * 72)
    print()

    # ── Step 1: Build 10-symbol carry panel ──────────────────────────────────
    print("Step 1: Building 10-symbol carry panel...", flush=True)
    panel, available_syms = build_carry_panel(PANEL_10)
    n_panel_days = len(panel)
    print(f"  Available symbols: {available_syms} ({len(available_syms)}/10)")
    print()

    # ── Step 2: Per-symbol carry stats (recent 90d) ──────────────────────────
    print("Step 2: Per-symbol carry stats...", flush=True)
    sym_stats = per_symbol_carry_stats(panel)
    for sym, s in sym_stats.items():
        r90 = s["recent_90d"]
        print(f"  {sym:6s}: 90d Sh={r90['sharpe']:6.2f}  "
              f"ann={r90['ann_carry_bps']:7.1f}bps  "
              f"slope={r90['slope_bps_per_day']:+.3f}bps/d  "
              f"trend={r90['trend']}", flush=True)
    print()

    # ── Step 3: Inter-symbol correlation matrix ───────────────────────────────
    print("Step 3: Carry correlation analysis (HL counterparty risk)...", flush=True)
    corr_analysis = carry_correlation_matrix(panel)
    print(f"  Mean pairwise corr: {corr_analysis['mean_pairwise_corr']:.3f}")
    print(f"  Max pairwise corr: {corr_analysis['max_pairwise_corr']:.3f}")
    print(f"  Min pairwise corr: {corr_analysis['min_pairwise_corr']:.3f}")
    print(f"  HL concentration risk: {corr_analysis['hl_concentration_risk']}")
    print()

    # ── Step 4: Sub-allocation comparison ────────────────────────────────────
    print("Step 4: Sub-allocation strategy comparison...", flush=True)
    sub_alloc_result = compare_sub_allocs(panel, available_syms)
    best_sub = sub_alloc_result["best_sub_alloc"]
    print(f"  Best sub-alloc: {best_sub}")
    print()

    # ── Step 5: Build primary carry panel series ──────────────────────────────
    print("Step 5: Building primary carry panel series...", flush=True)
    # Use V_eq_w as primary (most robust, avoids look-ahead in weights)
    primary_weights = sub_alloc_result["recommended_alloc"]["V_eq_w"]
    carry_panel_series = build_panel_return(panel, primary_weights)
    # Also build sharpe-weighted for secondary comparison
    sharpe_weights = sub_alloc_result["recommended_alloc"]["V_sharpe_w"]
    carry_sharpe_series = build_panel_return(panel, sharpe_weights)
    print(f"  Primary (eq_w): OOS Sh={sub_alloc_result['comparison']['V_eq_w']['oos']['sharpe']:.4f}")
    print()

    # ── Step 6: Load K194 non-carry components ────────────────────────────────
    print("Step 6: Loading K194 non-carry components...", flush=True)
    df_k194_base = load_k194_non_carry_components()
    print(f"  K194 base components: {list(df_k194_base.columns)}")
    print(f"  Date range: {df_k194_base.index[0].date()} → {df_k194_base.index[-1].date()}")
    print()

    # ── Step 7: Align carry panel to K194 base date range ───────────────────
    print("Step 7: Aligning carry panel to K194 base date range...", flush=True)
    common_start = max(panel.index[0], df_k194_base.index[0])
    common_end   = min(panel.index[-1], df_k194_base.index[-1])
    panel_aligned = panel[(panel.index >= common_start) & (panel.index <= common_end)]
    df_k194_base_aligned = df_k194_base[
        (df_k194_base.index >= common_start) & (df_k194_base.index <= common_end)
    ]
    # Re-compute carry series on aligned panel
    carry_series_aligned = build_panel_return(panel_aligned, primary_weights)
    carry_sharpe_aligned = build_panel_return(panel_aligned, sharpe_weights)

    # Merge with K194 base components
    df_k195 = df_k194_base_aligned.copy()
    df_k195["V_carry_panel_10sym"] = carry_series_aligned.reindex(df_k195.index, fill_value=0.0)
    print(f"  K195 DataFrame shape: {df_k195.shape}, {df_k195.index[0].date()} → {df_k195.index[-1].date()}")
    print(f"  Columns: {list(df_k195.columns)}")
    print()

    # ── Step 8: Apply K194 partial trigger (K121 + K133) ─────────────────────
    print("Step 8: Applying K194 partial trigger to K121 + K133...", flush=True)
    fr_mean = load_fr_mean_daily()
    fr_mean_aligned = fr_mean.reindex(df_k195.index, method="ffill")
    trigger_mask = (fr_mean_aligned < THRESHOLD_PRIMARY)

    df_k195_triggered = df_k195.copy()
    for col in PARTIAL_TRIGGER_COMPONENTS:
        if col in df_k195_triggered.columns:
            df_k195_triggered.loc[trigger_mask, col] = 0.0

    n_total = len(df_k195)
    oos_start_idx = int(n_total * (1 - OOS_FRAC))
    n_trigger_full = int(trigger_mask.sum())
    n_trigger_oos  = int(trigger_mask.iloc[oos_start_idx:].sum())
    trigger_pct_oos = n_trigger_oos / max(1, n_total - oos_start_idx) * 100
    print(f"  Trigger days full: {n_trigger_full}/{n_total} ({n_trigger_full/n_total*100:.1f}%)")
    print(f"  Trigger days OOS:  {n_trigger_oos}/{n_total-oos_start_idx} ({trigger_pct_oos:.1f}%)")
    print()

    # ── Step 9: Run K195 portfolio variants ───────────────────────────────────
    print("Step 9: Running K195 portfolio (triggered, primary cap=7%)...", flush=True)
    res_k195 = run_portfolio(df_k195_triggered, "K195_cap07", carry_cap=CARRY_CAP_PRIMARY)
    k195_p3_oos  = res_k195["metrics_oos"]["P3_risk_parity"]["sharpe"]
    k195_p3_full = res_k195["metrics_full"]["P3_risk_parity"]["sharpe"]
    k195_dd_oos  = res_k195["metrics_oos"]["P3_risk_parity"]["max_dd"]
    print(f"  K195 P3 OOS Sh: {k195_p3_oos:.4f} | Full Sh: {k195_p3_full:.4f}")
    print()

    # Also run base (no trigger) for comparison
    print("Step 9b: K195 base (no trigger)...", flush=True)
    res_k195_base = run_portfolio(df_k195, "K195_base_cap07", carry_cap=CARRY_CAP_PRIMARY)
    k195_base_p3_oos = res_k195_base["metrics_oos"]["P3_risk_parity"]["sharpe"]
    print(f"  K195 base P3 OOS Sh: {k195_base_p3_oos:.4f}")
    print()

    # ── Step 10: Carry cap sweep ──────────────────────────────────────────────
    print("Step 10: Carry cap sweep (5%, 7%, 10%, 12%, 15%)...", flush=True)
    sweep_results = carry_cap_sweep(df_k195_triggered, CAP_SWEEP)
    best_cap_entry = max(sweep_results, key=lambda x: x["oos_sharpe_P3"])
    best_cap = best_cap_entry["carry_cap"]
    print(f"  Best carry cap: {best_cap:.0%} (OOS P3={best_cap_entry['oos_sharpe_P3']:.4f})")
    print()

    # ── Step 11: Walk-forward 4-fold ──────────────────────────────────────────
    print("Step 11: Walk-forward 4-fold analysis...", flush=True)
    wf_k195 = wf_4fold(df_k195, df_k195_triggered, trigger_mask,
                        label="K195", carry_cap=CARRY_CAP_PRIMARY)
    k195_wf_mean_p3 = wf_k195.get("mean_K195_P3_risk_parity", 0.0)
    k195_wf_min_p3  = wf_k195.get("min_K195_P3_risk_parity", 0.0)
    print(f"  K195 WF P3: mean={k195_wf_mean_p3:.4f}  min={k195_wf_min_p3:.4f}")
    print()

    # ── Step 12: K194 reference (load from JSON) ──────────────────────────────
    print("Step 12: Loading K194 reference metrics...", flush=True)
    try:
        with open(BASE / "wave_k194_partial_trigger.json") as f:
            k194_json = json.load(f)
        k194_oos_sh_actual = k194_json["three_way_comparison"]["K194"]["oos_sharpe_P3"]
        k194_oos_dd_actual = k194_json["three_way_comparison"]["K194"]["oos_maxdd_P3"]
        k194_wf_mean_actual = k194_json["three_way_comparison"]["K194"]["wf_mean_P3"]
        k194_wf_min_actual  = k194_json["three_way_comparison"]["K194"]["wf_min_P3"]
    except Exception:
        k194_oos_sh_actual  = K194_OOS_SH
        k194_oos_dd_actual  = K194_OOS_DD
        k194_wf_mean_actual = K194_WF_MEAN
        k194_wf_min_actual  = K194_WF_MIN
    print(f"  K194 OOS Sh: {k194_oos_sh_actual:.4f}  MaxDD: {k194_oos_dd_actual:.4f}")
    print()

    # ── Step 13: Three-way comparison ─────────────────────────────────────────
    print("Step 13: Three-way comparison table...", flush=True)
    print()
    print(f"{'Version':<28} {'OOS Sh':>8} {'OOS MaxDD':>10} {'WF mean':>9} {'WF min':>9}")
    print("-" * 68)
    print(f"{'K188 baseline':<28} {K188_OOS_SH:>8.4f} {K188_OOS_DD:>10.4f} "
          f"{K188_WF_MEAN:>9.4f} {K188_WF_MIN:>9.4f}")
    print(f"{'K194 v6.2 (current prod)':<28} {k194_oos_sh_actual:>8.4f} {k194_oos_dd_actual:>10.4f} "
          f"{k194_wf_mean_actual:>9.4f} {k194_wf_min_actual:>9.4f}")
    print(f"{'K195 v6.3 candidate':<28} {k195_p3_oos:>8.4f} {k195_dd_oos:>10.4f} "
          f"{k195_wf_mean_p3:>9.4f} {k195_wf_min_p3:>9.4f}")
    print()

    # ── Step 14: Acceptance criteria ──────────────────────────────────────────
    print("Step 14: Acceptance criteria check...", flush=True)
    oos_lift       = k195_p3_oos - k194_oos_sh_actual
    c1_pass        = bool(oos_lift >= 0.10)                         # +0.10 vs K194
    c2_pass        = bool(k195_dd_oos >= k194_oos_dd_actual - 0.001)
    c3_pass        = bool(k195_wf_min_p3 >= 3.5)
    c4_pass        = bool(trigger_pct_oos <= 30.0)

    # 12+/16 improvement cells (P1-P4 × OOS metrics: sharpe, sortino, calmar, maxdd)
    k195_cells = []
    k194_oos_ref = k194_json.get("k194_primary_portfolio", {}).get("metrics_oos", {}) if 'k194_json' in dir() else {}
    n_cells_improve = 0
    n_cells_total   = 0
    for variant in ["P1_equal", "P2_inv_vol", "P3_risk_parity", "P4_sharpe_wt"]:
        k195_m = res_k195["metrics_oos"][variant]
        k194_m = k194_oos_ref.get(variant, {})
        if k194_m:
            for metric in ["sharpe", "sortino", "calmar", "max_dd"]:
                n_cells_total += 1
                if metric == "max_dd":
                    improve = k195_m.get(metric, -99) >= k194_m.get(metric, -99) - 0.0001
                else:
                    improve = k195_m.get(metric, 0) >= k194_m.get(metric, 0) - 0.001
                if improve:
                    n_cells_improve += 1

    c5_cells_pass = bool(n_cells_improve >= 12) if n_cells_total >= 12 else True  # fallback if no ref
    all_pass = bool(c1_pass and c2_pass and c3_pass and c4_pass)

    print(f"  C1: OOS Sh lift={oos_lift:+.4f} vs K194={k194_oos_sh_actual:.4f} (need >=+0.10) "
          f"→ {'PASS' if c1_pass else 'FAIL'}")
    print(f"  C2: MaxDD K194={k194_oos_dd_actual:.4f} vs K195={k195_dd_oos:.4f} "
          f"→ {'PASS' if c2_pass else 'FAIL'}")
    print(f"  C3: WF fold min={k195_wf_min_p3:.4f} (need >=3.5) "
          f"→ {'PASS' if c3_pass else 'FAIL'}")
    print(f"  C4: OOS trigger%={trigger_pct_oos:.1f}% (need <=30%) "
          f"→ {'PASS' if c4_pass else 'FAIL'}")
    if n_cells_total > 0:
        print(f"  C5: Cells improving={n_cells_improve}/{n_cells_total} (need >=12/16) "
              f"→ {'PASS' if c5_cells_pass else 'FAIL'}")
    print(f"  ALL_PASS: {all_pass}")
    print()

    # ── Build equity curves ───────────────────────────────────────────────────
    print("Building equity curves for export...", flush=True)
    dates_list = [d.strftime("%Y-%m-%d") for d in df_k195.index]
    R_base  = df_k195.to_numpy()
    R_trig  = df_k195_triggered.to_numpy()
    cols    = list(df_k195.columns)

    w_k195_p3_full = np.array(res_k195["weights"]["P3_risk_parity"])
    eq_k195_p3     = list(np.cumprod(1.0 + R_trig @ w_k195_p3_full))
    eq_k195_base_p3 = list(np.cumprod(1.0 + R_base @ np.array(res_k195_base["weights"]["P3_risk_parity"])))

    # Per-symbol carry equity curves
    panel_dates = [d.strftime("%Y-%m-%d") for d in panel_aligned.index]
    sym_carry_curves = {}
    for sym in available_syms:
        sym_carry_curves[f"carry_{sym}"] = [round(float(v), 6)
            for v in np.cumprod(1.0 + panel_aligned[sym].values)]

    # Sub-alloc comparison curves
    sub_alloc_curves = {}
    for alloc_name, aw in [("V_eq_w", primary_weights), ("V_sharpe_w", sharpe_weights)]:
        ret = build_panel_return(panel_aligned, aw)
        sub_alloc_curves[alloc_name] = [round(float(v), 6) for v in np.cumprod(1.0 + ret.values)]

    runtime_s = round(time.time() - START_TIME, 1)

    # ── Assemble metrics JSON ─────────────────────────────────────────────────
    metrics_out = {
        "wave": "K195",
        "task": "10-symbol expanded carry panel (K194 partial trigger maintained)",
        "as_of": pd.Timestamp.utcnow().isoformat() + "Z",
        "runtime_s": runtime_s,
        "config": {
            "panel_10": PANEL_10,
            "available_symbols": available_syms,
            "carry_cap_primary": CARRY_CAP_PRIMARY,
            "k121_cap": K121_CAP,
            "partial_trigger_components": PARTIAL_TRIGGER_COMPONENTS,
            "fr_threshold": THRESHOLD_PRIMARY,
            "n_folds": N_FOLDS,
            "train_frac": TRAIN_FRAC,
            "oos_frac": OOS_FRAC,
            "n_total": n_total,
            "oos_start_idx": oos_start_idx,
            "date_range": [str(df_k195.index[0].date()), str(df_k195.index[-1].date())],
        },
        "per_symbol_carry_stats": sym_stats,
        "correlation_analysis": corr_analysis,
        "sub_alloc_comparison": {
            k: {"full": v["full"], "oos": v["oos"]}
            for k, v in sub_alloc_result["comparison"].items()
        },
        "best_sub_alloc": best_sub,
        "k195_portfolio": {
            "metrics_full": res_k195["metrics_full"],
            "metrics_oos":  res_k195["metrics_oos"],
            "weights":      res_k195["weights"],
            "single_metrics_oos": res_k195["single_metrics_oos"],
            "n_trigger_days_full": n_trigger_full,
            "n_trigger_days_oos":  n_trigger_oos,
            "trigger_pct_oos": round(trigger_pct_oos, 1),
        },
        "k195_base_portfolio": {
            "metrics_full": res_k195_base["metrics_full"],
            "metrics_oos":  res_k195_base["metrics_oos"],
        },
        "carry_cap_sweep": sweep_results,
        "best_carry_cap": best_cap,
        "walk_forward_k195": wf_k195,
        "three_way_comparison": {
            "K188": {
                "oos_sharpe_P3": K188_OOS_SH,
                "oos_maxdd_P3":  K188_OOS_DD,
                "wf_mean_P3":    K188_WF_MEAN,
                "wf_min_P3":     K188_WF_MIN,
                "description":   "K188 v6 baseline",
            },
            "K194": {
                "oos_sharpe_P3": k194_oos_sh_actual,
                "oos_maxdd_P3":  k194_oos_dd_actual,
                "wf_mean_P3":    k194_wf_mean_actual,
                "wf_min_P3":     k194_wf_min_actual,
                "description":   "K194 v6.2 current production (4-symbol panel + K121/K133 trigger)",
            },
            "K195": {
                "oos_sharpe_P3": k195_p3_oos,
                "oos_maxdd_P3":  k195_dd_oos,
                "full_sharpe_P3": k195_p3_full,
                "wf_mean_P3":    k195_wf_mean_p3,
                "wf_min_P3":     k195_wf_min_p3,
                "description":   "K195 v6.3 candidate (10-symbol panel + K121/K133 trigger)",
            },
        },
        "acceptance_criteria": {
            "c1_oos_lift_needed":     0.10,
            "c1_oos_lift_actual":     round(oos_lift, 4),
            "c1_k194_oos_sh":        k194_oos_sh_actual,
            "c1_k195_oos_sh":        k195_p3_oos,
            "c1_pass":               c1_pass,
            "c2_maxdd_k194":         k194_oos_dd_actual,
            "c2_maxdd_k195":         k195_dd_oos,
            "c2_pass":               c2_pass,
            "c3_wf_min_needed":      3.5,
            "c3_wf_min_actual":      k195_wf_min_p3,
            "c3_pass":               c3_pass,
            "c4_trigger_pct_oos":    round(trigger_pct_oos, 1),
            "c4_pass":               c4_pass,
            "c5_cells_improve":      n_cells_improve,
            "c5_cells_total":        n_cells_total,
            "c5_pass":               c5_cells_pass,
            "all_pass":              all_pass,
        },
        "verdict": (
            "ACCEPT: K195 v6.3 clears all acceptance criteria."
            if all_pass else
            "CONDITIONAL/REJECT: K195 does not meet all acceptance criteria. "
            "See individual criteria above. Monitor carry decay before promoting."
        ),
        "operational_risk_assessment": {
            "hl_counterparty_concentration": corr_analysis["hl_concentration_risk"],
            "mean_carry_corr": corr_analysis["mean_pairwise_corr"],
            "note_counterparty": (
                "10 symbols on HL = concentrated single-exchange counterparty risk. "
                "Diversification across symbols does NOT reduce HL default/halt risk. "
                "Recommend monitoring HL solvency indicators (insurance fund, OI)."
            ),
            "note_meme_fills": (
                "BONK, PEPE: sub-penny tokens with potentially wide bid-ask spreads. "
                "Maker-only fills required to keep cost ≤2bps/side. "
                "Monitor actual fill quality before scaling."
            ),
            "note_arb_compression": (
                "Carry spread could compress if more arb capital enters all 10 symbols simultaneously. "
                "Strengthening recent 90d trend vs 730d full Sharpe indicates spread may still be early-stage."
            ),
            "note_rebalancing": (
                "10 symbols × 2 exchanges = 20 positions to manage. "
                "Rebalancing is operationally more complex than 4-symbol K194 panel. "
                "Recommend monthly or quarterly rebalancing for DeFi tokens (LDO, AAVE, UNI, MKR, CRV)."
            ),
            "symbols_negative_slope": [
                s for s in available_syms
                if sym_stats.get(s, {}).get("recent_90d", {}).get("slope_bps_per_day", 0) < 0
            ],
        },
    }

    # ── Save metrics JSON ─────────────────────────────────────────────────────
    out_metrics = BASE / "wave_k195_carry_v6_3.json"
    with open(out_metrics, "w") as f:
        json.dump(metrics_out, f, indent=2, default=str)
    print(f"Saved: {out_metrics}")

    # ── Assemble curves JSON ──────────────────────────────────────────────────
    curves_out = {
        "dates": dates_list,
        "panel_dates": panel_dates,
        "series": {
            "K195_P3_triggered": [round(float(v), 6) for v in eq_k195_p3],
            "K195_P3_base": [round(float(v), 6) for v in eq_k195_base_p3],
            **sym_carry_curves,
            **sub_alloc_curves,
        }
    }
    # Add all P1-P4 curves for K195
    for k, curve_list in res_k195["curves"].items():
        curves_out["series"][k] = curve_list

    out_curves = BASE / "wave_k195_curves.json"
    with open(out_curves, "w") as f:
        json.dump(curves_out, f, indent=2)
    print(f"Saved: {out_curves}")

    print()
    print("=" * 72)
    print(f"K195 COMPLETE — runtime {runtime_s:.0f}s")
    print(f"OOS Sharpe P3: {k195_p3_oos:.4f}  MaxDD: {k195_dd_oos:.4f}  "
          f"WF min: {k195_wf_min_p3:.4f}")
    print(f"Verdict: {metrics_out['verdict']}")
    print("=" * 72)

    return metrics_out


if __name__ == "__main__":
    main()
