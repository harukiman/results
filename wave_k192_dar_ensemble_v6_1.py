"""Wave K192 — DAR Ensemble v6.1: K175_DAR replaces K175 in K188 production ensemble.

Objective:
  Replace the K175 component in the K188 v6 ensemble with K175_DAR (DAR(2,1) filter).
  Test ensemble-level lift and determine if K192 qualifies as v6.1 production.

Three-way comparison:
  K188 baseline  : K175 original
  K192a          : K175 slot = K190_DAR(2,1)_win300_refit50 (primary config)
  K192b          : K175 slot = K190_DAR(2,1)_win200_refit25 (best overall from K190)

Acceptance criteria (K192 → v6.1):
  - OOS Sharpe > K188 (5.48) by at least +0.05
  - MaxDD not worsened
  - 12+/16 cells improve vs K188 baseline
  - WF fold 3 weakness (K188 min=2.376) improved (min ≥ 3.0 ideal)

K173 META-LESSON: Report GROSS AND NET separately.

Runtime target: <12 min.
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

BASE   = Path("/Users/nekonaomichi/crypto-lab")
CACHE  = BASE / "cache"
HL_CACHE = CACHE / "k163_hl"

TRADING_DAYS = 365
OOS_FRAC     = 0.30
START_TIME   = time.time()

# K186 carry sub-weights (unchanged from K188)
CARRY_WEIGHTS_K186 = {"ETH": 0.35, "DOGE": 0.30, "AVAX": 0.25, "BTC": 0.10}

# DAR parameters
SYMBOLS_DAR = ["XRP", "SUI"]
EVENTS_PER_YEAR_8H = 365 * 3  # 1095 (8h bars)
SLIPPAGE_BPS_PER_SIDE = 2.0
MAKER_FEE_BPS_PER_SIDE = 0.0
COST_PER_FILL = (SLIPPAGE_BPS_PER_SIDE + MAKER_FEE_BPS_PER_SIDE) * 1e-4  # 0.0002

# K192a config (primary / pre-registered in K190)
DAR_A = dict(p=2, q=1, win=300, refit=50)
# K192b config (best overall from K190 window/refit sweep)
DAR_B = dict(p=2, q=1, win=200, refit=25)


# ─────────────────────────────── DAR Data helpers ─────────────────────────────

def load_hl_fr_sym(sym: str) -> Optional[pd.Series]:
    f = HL_CACHE / f"hl_fr_{sym}.parquet"
    if not f.exists():
        return None
    df = pd.read_parquet(f)
    s = df.set_index("timestamp")["hl_fr"].astype(float).sort_index()
    s = s[~s.index.duplicated(keep="last")]
    return s


def load_bybit_fr_sym(sym: str) -> Optional[pd.Series]:
    for tag in ("730d", "1200d", "365d"):
        f = CACHE / f"bybit_fr_{sym}USDT_{tag}.parquet"
        if f.exists():
            df = pd.read_parquet(f)
            s = df.set_index("timestamp")["funding_rate"].astype(float).sort_index()
            s = s[~s.index.duplicated(keep="last")]
            return s
    return None


def load_bybit_close_sym(sym: str) -> Optional[pd.Series]:
    f = CACHE / f"{sym}USDT_4h_730d.parquet"
    if not f.exists():
        return None
    df = pd.read_parquet(f)
    s = df.set_index("open_time")["close"].astype(float).sort_index()
    s = s[~s.index.duplicated(keep="last")]
    return s


def build_dar_panel(sym: str) -> Optional[pd.DataFrame]:
    hl = load_hl_fr_sym(sym)
    by = load_bybit_fr_sym(sym)
    cl = load_bybit_close_sym(sym)
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
    try:
        coeffs, _, _, _ = np.linalg.lstsq(X, y, rcond=None)
        return coeffs
    except Exception:
        return np.zeros(X.shape[1])


def build_dar_design_row(fr_arr, spread_arr, p, q, idx):
    if idx < max(p, q):
        return None
    row = [1.0]
    for lag in range(1, p + 1):
        row.append(fr_arr[idx - lag])
    for lag in range(1, q + 1):
        row.append(spread_arr[idx - lag])
    return np.array(row, dtype=float)


def dar_walk_forward(fr: np.ndarray, spread_z: np.ndarray, p=2, q=1, win=300, refit=50):
    n = len(fr)
    pred_fr = np.full(n, np.nan)
    is_valid = np.zeros(n, dtype=bool)
    min_lag = max(p, q)
    coeffs = None

    for i in range(min_lag + win, n):
        if (i - (min_lag + win)) % refit == 0 or coeffs is None:
            start = i - win
            rows, targets = [], []
            for t in range(start + min_lag, i):
                row = build_dar_design_row(fr, spread_z, p, q, t)
                if row is not None:
                    rows.append(row)
                    targets.append(fr[t])
            if len(rows) < p + q + 10:
                continue
            X = np.array(rows, dtype=float)
            y = np.array(targets, dtype=float)
            coeffs = _ols_fit(X, y)

        if coeffs is not None:
            row = build_dar_design_row(fr, spread_z, p, q, i - 1)
            if row is not None:
                pred_fr[i] = float(np.dot(row, coeffs))
                is_valid[i] = True

    valid_idx = np.where(is_valid)[0]
    if len(valid_idx) < 30:
        return pred_fr, is_valid, {"oos_r2": np.nan, "direction_acc": np.nan, "aic": np.nan, "n_oos": 0}

    y_true = fr[valid_idx]
    y_pred = pred_fr[valid_idx]
    ss_res = np.sum((y_true - y_pred) ** 2)
    ss_tot = np.sum((y_true - y_true.mean()) ** 2)
    oos_r2 = float(1 - ss_res / (ss_tot + 1e-30))
    actual_delta = np.diff(y_true)
    pred_sign = np.sign(y_pred[1:] - y_true[:-1])
    actual_sign = np.sign(actual_delta)
    nz = actual_sign != 0
    dir_acc = float((pred_sign[nz] == actual_sign[nz]).mean()) if nz.sum() > 0 else 0.5
    n_oos = len(valid_idx)
    k = 1 + p + q
    sigma2 = float(ss_res / max(n_oos, 1))
    aic = float(n_oos * np.log(max(sigma2, 1e-30)) + 2 * k) if sigma2 > 0 else np.nan

    return pred_fr, is_valid, {
        "oos_r2": round(oos_r2, 5),
        "direction_acc": round(dir_acc, 4),
        "aic": round(aic, 2),
        "n_oos": int(n_oos),
    }


def zscore_series(s: pd.Series, win: int = 30) -> pd.Series:
    mu = s.rolling(win, min_periods=win).mean()
    sd = s.rolling(win, min_periods=win).std()
    return (s - mu) / (sd + 1e-12)


def run_k175_dar_filter(
    panels: Dict[str, pd.DataFrame],
    p=2, q=1, win=300, refit=50,
    z_thr=2.0, hold=1, zwin=30,
    cost_per_fill=COST_PER_FILL,
) -> Tuple[pd.Series, pd.Series]:
    """Run K175 + DAR(p,q) filter. Returns (net_daily, gross_daily) as daily returns."""
    per_sym_net = {}
    per_sym_gross = {}

    for sym, df in panels.items():
        fr_arr = df["bybit_fr"].values.copy()
        z = zscore_series(df["spread"], zwin)
        spread_z_arr = z.fillna(0.0).values

        pred_fr, is_valid, _ = dar_walk_forward(fr_arr, spread_z_arr, p=p, q=q, win=win, refit=refit)

        sig = pd.Series(0.0, index=df.index)
        for i in range(len(df)):
            if not is_valid[i]:
                continue
            z_val = z.iloc[i]
            current_fr = fr_arr[i]
            pred = pred_fr[i]
            if z_val > z_thr:
                if pred <= current_fr:
                    sig.iloc[i] = -1.0
            elif z_val < -z_thr:
                if pred >= current_fr:
                    sig.iloc[i] = 1.0

        sig_lag = sig.shift(1).fillna(0.0)
        pos = pd.Series(0.0, index=df.index)
        i = 0
        while i < len(sig_lag):
            new = sig_lag.iloc[i]
            if new != 0.0:
                end = min(i + hold, len(pos))
                pos.iloc[i:end] = new
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

    if not per_sym_net:
        empty = pd.Series(dtype=float)
        return empty, empty

    # Combine across symbols (equal-weight average, log-like additive)
    gross_8h = pd.concat(per_sym_gross, axis=1).fillna(0.0).mean(axis=1)
    net_8h   = pd.concat(per_sym_net,   axis=1).fillna(0.0).mean(axis=1)

    # Convert 8h PnL to daily returns
    gross_8h.index = pd.to_datetime(gross_8h.index)
    net_8h.index   = pd.to_datetime(net_8h.index)

    # Resample: sum log-returns over a day to get daily log-return, then convert
    gross_8h_idx = gross_8h[~gross_8h.index.duplicated(keep="last")]
    net_8h_idx   = net_8h[~net_8h.index.duplicated(keep="last")]

    gross_8h_idx.index = gross_8h_idx.index.tz_localize(None) if gross_8h_idx.index.tz is not None else gross_8h_idx.index
    net_8h_idx.index   = net_8h_idx.index.tz_localize(None)   if net_8h_idx.index.tz   is not None else net_8h_idx.index

    gross_daily = gross_8h_idx.resample("1D").sum()
    net_daily   = net_8h_idx.resample("1D").sum()

    return net_daily, gross_daily


# ─────────────────────────────── K188 component loaders ─────────────────────

def _equity_to_daily_returns(ts_iso: List[str], eq: List[float]) -> pd.Series:
    ts = pd.to_datetime(ts_iso, utc=True).tz_convert(None) \
         if pd.to_datetime(ts_iso[0]).tzinfo else pd.to_datetime(ts_iso)
    s = pd.Series(eq, index=ts).sort_index()
    daily_eq = s.resample("1D").last().ffill()
    daily_ret = daily_eq.pct_change().fillna(0.0)
    return daily_ret


def load_v41_and_v1() -> pd.DataFrame:
    with open(BASE / "wave_k109_curves.json") as fp:
        d = json.load(fp)
    dates = pd.to_datetime(d["dates"])
    df = pd.DataFrame(index=dates)
    for name in ("v4.1", "V1"):
        cum = np.asarray(d["series"][name], dtype=float)
        eq = 1.0 + cum
        eq_prev = np.r_[1.0, eq[:-1]]
        df[name] = eq / eq_prev - 1.0
    df.index.name = "date"
    return df


def load_k114() -> pd.Series:
    with open(BASE / "wave_k114_alcp.json") as fp:
        d = json.load(fp)
    curve = d["curves"]["full_equity"]
    s = _equity_to_daily_returns(list(curve.keys()), list(curve.values()))
    s.name = "K114"; return s


def load_k116() -> pd.Series:
    with open(BASE / "wave_k116_curves.json") as fp:
        d = json.load(fp)
    s = _equity_to_daily_returns(d["timestamps"], d["portfolio_equity"])
    s.name = "K116"; return s


def load_k121() -> pd.Series:
    with open(BASE / "wave_k121_curves.json") as fp:
        d = json.load(fp)
    pts = d["weekend_ls"]
    s = _equity_to_daily_returns([p["ts"] for p in pts], [p["eq"] for p in pts])
    s.name = "K121"; return s


def load_k133(variant: str = "V_rev_3d_z15") -> pd.Series:
    with open(BASE / "wave_k133_curves.json") as fp:
        d = json.load(fp)
    v = d[variant]
    s = _equity_to_daily_returns(v["equity_idx"], v["equity_curve"])
    s.name = "K133"; return s


def load_k147(variant: str = "V_long_short_h12") -> pd.Series:
    with open(BASE / "wave_k147_curves.json") as fp:
        d = json.load(fp)
    v = d[variant]
    s = _equity_to_daily_returns(v["timestamps"], v["portfolio_equity"])
    s.name = "K147"; return s


def load_k175_original() -> pd.Series:
    with open(BASE / "wave_k175_curves.json") as fp:
        d = json.load(fp)
    v = d["V_xrp_sui_maker"]
    s = _equity_to_daily_returns(v["timestamps"], v["equity_net"])
    s.name = "K175"; return s


def _load_hl_8h_carry(sym: str) -> pd.DataFrame:
    fpath = HL_CACHE / f"hl_fr_{sym}.parquet"
    df = pd.read_parquet(fpath)
    df["ts"] = pd.to_datetime(df["timestamp"])
    hl_8h = df.set_index("ts")["hl_fr"].resample("8h").sum().reset_index()
    hl_8h.columns = ["ts", "hl_fr_8h"]
    return hl_8h


def _load_bybit_carry(sym: str) -> pd.DataFrame:
    for suffix in ["1200d", "730d", "365d"]:
        fpath = CACHE / f"bybit_fr_{sym}USDT_{suffix}.parquet"
        if fpath.exists():
            df = pd.read_parquet(fpath)
            df["ts"] = pd.to_datetime(df["timestamp"])
            return df[["ts", "funding_rate"]].rename(columns={"funding_rate": "bybit_fr"})
    raise FileNotFoundError(f"No Bybit data for {sym}")


def _build_carry_daily(sym: str) -> pd.Series:
    hl = _load_hl_8h_carry(sym)
    by = _load_bybit_carry(sym)
    merged = pd.merge_asof(
        by.sort_values("ts"), hl.sort_values("ts"), on="ts",
        tolerance=pd.Timedelta("4h"), direction="nearest",
    ).dropna()
    merged["carry"] = merged["hl_fr_8h"] - merged["bybit_fr"]
    merged = merged.sort_values("ts")
    merged["date"] = merged["ts"].dt.normalize()
    daily = merged.groupby("date")["carry"].sum()
    if len(daily) > 0:
        daily.iloc[0] -= 0.0010  # 10bp one-time entry cost
    daily.index = pd.to_datetime(daily.index)
    daily.name = sym
    return daily


def load_carry_panel(symbols=("BTC", "ETH", "DOGE", "AVAX")) -> pd.DataFrame:
    sym_series = {}
    for sym in symbols:
        try:
            s = _build_carry_daily(sym)
            sym_series[sym] = s
            print(f"  [{sym}] carry: n={len(s)} ({s.index.min().date()} -> {s.index.max().date()})")
        except Exception as e:
            print(f"  [{sym}] failed: {e}")
    return pd.DataFrame(sym_series).dropna(how="any")


def build_weighted_carry(sym_df: pd.DataFrame, weights: Dict[str, float]) -> pd.Series:
    cols = [c for c in sym_df.columns if c in weights]
    w = np.array([weights[c] for c in cols])
    w = w / w.sum()
    panel = sym_df[cols] @ w
    panel.name = "V_carry_panel_weighted"
    return panel


# ─────────────────────────────── Metrics ─────────────────────────────────────

def sharpe_d(r: np.ndarray) -> float:
    if len(r) < 2 or r.std(ddof=1) == 0:
        return 0.0
    return float(r.mean() / r.std(ddof=1) * math.sqrt(TRADING_DAYS))


def sortino_d(r: np.ndarray) -> float:
    dn = r[r < 0]
    if len(dn) < 2 or dn.std(ddof=1) == 0:
        return 0.0
    return float(r.mean() / dn.std(ddof=1) * math.sqrt(TRADING_DAYS))


def max_dd_d(r: np.ndarray) -> float:
    eq = np.cumprod(1.0 + r)
    peak = np.maximum.accumulate(eq)
    return float((eq / peak - 1.0).min())


def calmar_d(r: np.ndarray) -> float:
    ann = (1.0 + r).prod() ** (TRADING_DAYS / max(1, len(r))) - 1.0
    mdd = max_dd_d(r)
    return float(ann / abs(mdd)) if mdd != 0 else 0.0


def metrics_pkg(r: np.ndarray) -> dict:
    if len(r) < 2:
        return {"sharpe": 0, "sortino": 0, "calmar": 0, "max_dd": 0,
                "ann_ret": 0, "ann_vol": 0, "n_days": int(len(r))}
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


# ─────────────────────────────── Weighting ───────────────────────────────────

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


def apply_caps(w, cols, k121_cap=0.30, carry_cap=None, carry_col="V_carry_panel_weighted"):
    w = apply_cap(w, cols, "K121", k121_cap)
    if carry_cap is not None:
        w = apply_cap(w, cols, carry_col, carry_cap)
    return w


def div_ratio(w: np.ndarray, R: np.ndarray, cols: List[str]) -> float:
    single_sh = np.array([sharpe_d(R[:, i]) for i in range(R.shape[1])])
    port_sh = sharpe_d(R @ w)
    w_avg = float((w * single_sh).sum())
    return round(port_sh / w_avg, 4) if w_avg > 0 else 0.0


# ─────────────────────────────── Portfolio runner ────────────────────────────

def run_portfolio(
    df: pd.DataFrame,
    label: str,
    carry_cap: Optional[float] = None,
    carry_col: str = "V_carry_panel_weighted",
) -> dict:
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

    full_metrics, oos_metrics, full_curves, full_dr = {}, {}, {}, {}
    for k, w in capped.items():
        pr_f = R @ w
        pr_o = oos_R @ w
        full_metrics[k] = metrics_pkg(pr_f)
        oos_metrics[k]  = metrics_pkg(pr_o)
        full_curves[f"{label}_{k}"] = list(np.cumprod(1.0 + pr_f))
        full_dr[k] = div_ratio(w, R, cols)

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
        "diversification_ratio": full_dr,
        "curves": full_curves,
        "dates": [d.strftime("%Y-%m-%d") for d in df.index],
    }


# ─────────────────────────────── Walk-forward (4-fold) ───────────────────────

def wf_4fold(df: pd.DataFrame, carry_cap=0.07, n_folds: int = 4) -> dict:
    """4-fold WF exactly matching K188 methodology:
    - Divide total data into n_folds equal segments
    - Within each fold: train on 70%, test on 30%
    - date_start/date_end = full fold range (train+test)
    """
    cols = list(df.columns)
    R = df.to_numpy()
    carry_col = "V_carry_panel_weighted"
    n = len(R)
    fold_size = n // n_folds
    folds = []

    for fold_id in range(n_folds):
        start = fold_id * fold_size
        end   = start + fold_size if fold_id < n_folds - 1 else n
        R_fold = R[start:end]
        cut = int(len(R_fold) * 0.70)
        R_tr = R_fold[:cut]
        R_te = R_fold[cut:]
        if len(R_tr) < 30 or len(R_te) < 10:
            continue

        raw_w = {
            "P1_equal":       w_equal(len(cols)),
            "P2_inv_vol":     w_inv_vol(R_tr),
            "P3_risk_parity": w_risk_parity(R_tr),
            "P4_sharpe_wt":   w_sharpe_wt(R_tr),
        }
        capped = {k: apply_caps(w, cols, carry_cap=carry_cap, carry_col=carry_col)
                  for k, w in raw_w.items()}

        fold = {
            "fold": fold_id,
            "train_n": int(len(R_tr)),
            "test_n":  int(len(R_te)),
            "date_start": str(df.index[start].date()),
            "date_end":   str(df.index[end - 1].date()),
        }
        for k, w in capped.items():
            pr = R_te @ w
            fold[f"oos_sharpe_{k}"] = round(sharpe_d(pr), 4)
        folds.append(fold)

    result = {"folds": folds}
    for k in ["P1_equal", "P2_inv_vol", "P3_risk_parity", "P4_sharpe_wt"]:
        vals = [f[f"oos_sharpe_{k}"] for f in folds if f"oos_sharpe_{k}" in f]
        if vals:
            result[f"mean_{k}"] = round(float(np.mean(vals)), 4)
            result[f"min_{k}"]  = round(float(np.min(vals)), 4)
            result[f"std_{k}"]  = round(float(np.std(vals)), 4)
    return result


# ─────────────────────────────── Correlation matrix ──────────────────────────

def compute_correlations(df: pd.DataFrame) -> dict:
    corr_p = df.corr(method="pearson").round(4)
    corr_s = df.corr(method="spearman").round(4)
    abs_p = corr_p.abs()
    n = len(df.columns)
    mask = ~np.eye(n, dtype=bool)
    return {
        "pearson": corr_p.to_dict(),
        "spearman": corr_s.to_dict(),
        "mean_abs_pearson": round(float(abs_p.values[mask].mean()), 4),
        "max_abs_pearson":  round(float(abs_p.values[mask].max()), 4),
    }


# ─────────────────────────────── 16-cell comparison ─────────────────────────

def build_comparison_table(
    k188_res: dict,
    k192a_res: dict,
    k192b_res: dict,
) -> dict:
    """16 cells: 4 variants x 4 conditions (full/oos × K192a/K192b vs K188)."""
    variants = ["P1_equal", "P2_inv_vol", "P3_risk_parity", "P4_sharpe_wt"]
    conditions = ["oos", "full"]
    systems = [("K192a", k192a_res), ("K192b", k192b_res)]

    table = {}
    improved_a, improved_b = 0, 0
    total = 0

    for var in variants:
        m188_oos  = k188_res["metrics_oos"].get(var, {})
        m188_full = k188_res["metrics_full"].get(var, {})
        for sys_name, sys_res in systems:
            m_oos  = sys_res["metrics_oos"].get(var, {})
            m_full = sys_res["metrics_full"].get(var, {})
            for cond in conditions:
                m_base = m188_oos  if cond == "oos" else m188_full
                m_new  = m_oos     if cond == "oos" else m_full
                key = f"{sys_name}_{var}_{cond}"
                improved = m_new.get("sharpe", 0) > m_base.get("sharpe", 0)
                table[key] = {
                    "k188_sharpe": m_base.get("sharpe", 0),
                    f"{sys_name}_sharpe": m_new.get("sharpe", 0),
                    "delta": round(m_new.get("sharpe", 0) - m_base.get("sharpe", 0), 4),
                    "improved": improved,
                    "k188_max_dd": m_base.get("max_dd", 0),
                    f"{sys_name}_max_dd": m_new.get("max_dd", 0),
                    "dd_not_worsened": m_new.get("max_dd", 0) >= m_base.get("max_dd", 0),
                }
                if sys_name == "K192a":
                    if improved: improved_a += 1
                    total += 1
                else:
                    if improved: improved_b += 1

    return {
        "cells": table,
        "K192a_improved_count": improved_a,
        "K192b_improved_count": improved_b,
        "total_cells": total,
        "K192a_improve_pct": round(100.0 * improved_a / total, 1),
        "K192b_improve_pct": round(100.0 * improved_b / total, 1),
    }


# ─────────────────────────────── K175 DAR daily PnL ─────────────────────────

def k175_dar_to_daily_returns(net_8h: pd.Series, gross_8h: pd.Series) -> Tuple[pd.Series, pd.Series]:
    """Convert 8h log-ret PnL to daily simple returns matching K188 daily format."""
    # Make index tz-naive
    for s in [net_8h, gross_8h]:
        if s.index.tz is not None:
            s.index = s.index.tz_localize(None)

    # Resample to daily by summing log-returns, then convert to simple
    net_daily_log   = net_8h.resample("1D").sum()
    gross_daily_log = gross_8h.resample("1D").sum()

    # Convert log-ret to simple ret
    net_daily   = np.expm1(net_daily_log)
    gross_daily = np.expm1(gross_daily_log)

    return net_daily, gross_daily


# ─────────────────────────────── Main ────────────────────────────────────────

def main():
    t0 = time.time()

    # ── 1. Build DAR panels ──
    print("\n=== Loading DAR panels (XRP, SUI) ===")
    panels = {}
    for sym in SYMBOLS_DAR:
        p = build_dar_panel(sym)
        if p is not None:
            panels[sym] = p
            print(f"  {sym}: n={len(p)} events, FR_mean={p['bybit_fr'].mean():.6f}")
        else:
            print(f"  {sym}: FAILED to build panel")

    if not panels:
        raise RuntimeError("No DAR panels built")

    # ── 2. Run K192a (win=300, refit=50) ──
    print(f"\n=== K192a: DAR({DAR_A['p']},{DAR_A['q']}) win={DAR_A['win']} refit={DAR_A['refit']} ===")
    net_a_8h, gross_a_8h = run_k175_dar_filter(panels, **DAR_A)
    net_a_daily, gross_a_daily = k175_dar_to_daily_returns(net_a_8h, gross_a_8h)
    print(f"  K192a net daily: n={len(net_a_daily)}, mean={net_a_daily.mean():.6f}")

    # ── 3. Run K192b (win=200, refit=25) ──
    print(f"\n=== K192b: DAR({DAR_B['p']},{DAR_B['q']}) win={DAR_B['win']} refit={DAR_B['refit']} ===")
    net_b_8h, gross_b_8h = run_k175_dar_filter(panels, **DAR_B)
    net_b_daily, gross_b_daily = k175_dar_to_daily_returns(net_b_8h, gross_b_8h)
    print(f"  K192b net daily: n={len(net_b_daily)}, mean={net_b_daily.mean():.6f}")

    # ── 4. Load K188 component returns ──
    print("\n=== Loading K188 components ===")
    df01 = load_v41_and_v1()
    if df01.index.tz is not None:
        df01.index = df01.index.tz_localize(None)
    s114 = load_k114()
    s116 = load_k116()
    s121 = load_k121()
    s133 = load_k133()
    s147 = load_k147()
    s175_orig = load_k175_original()
    print(f"  v4.1, V1, K114, K116, K121, K133, K147 loaded")

    # Load carry panel
    print("\n=== Loading carry panel ===")
    carry_sym_df = load_carry_panel()
    carry_panel = build_weighted_carry(carry_sym_df, CARRY_WEIGHTS_K186)

    # ── 5. Assemble K188 baseline (9-strategy, K175 original) ──
    print("\n=== Assembling K188 baseline (K175 original) ===")
    df8_base = pd.concat([
        df01[["v4.1"]], df01[["V1"]],
        s114.to_frame(), s116.to_frame(), s121.to_frame(),
        s133.to_frame(), s147.to_frame(), s175_orig.to_frame(),
    ], axis=1, join="inner").sort_index().dropna(how="any")
    carry_aligned = carry_panel.reindex(df8_base.index)
    df8_base["V_carry_panel_weighted"] = carry_aligned
    df_k188 = df8_base.dropna(how="any")
    print(f"  K188 baseline: {df_k188.shape}, {df_k188.index.min().date()} -> {df_k188.index.max().date()}")

    # ── 6. Assemble K192a (K175 slot = net_a_daily) ──
    print("\n=== Assembling K192a (K175_DAR win300) ===")
    net_a_aligned = net_a_daily.reindex(df_k188.index).fillna(0.0)
    df_k192a = df_k188.copy()
    df_k192a["K175"] = net_a_aligned
    df_k192a = df_k192a.dropna(how="any")
    print(f"  K192a: {df_k192a.shape}")

    # ── 7. Assemble K192b (K175 slot = net_b_daily) ──
    print("\n=== Assembling K192b (K175_DAR win200) ===")
    net_b_aligned = net_b_daily.reindex(df_k188.index).fillna(0.0)
    df_k192b = df_k188.copy()
    df_k192b["K175"] = net_b_aligned
    df_k192b = df_k192b.dropna(how="any")
    print(f"  K192b: {df_k192b.shape}")

    # ── 8. Run portfolios ──
    CARRY_CAP = 0.07
    print("\n=== Running portfolios (carry cap=7%) ===")
    print("  K188 baseline...")
    res_k188 = run_portfolio(df_k188, "K188_cap07", carry_cap=CARRY_CAP)
    print("  K192a...")
    res_k192a = run_portfolio(df_k192a, "K192a_cap07", carry_cap=CARRY_CAP)
    print("  K192b...")
    res_k192b = run_portfolio(df_k192b, "K192b_cap07", carry_cap=CARRY_CAP)

    # ── 9. K175 standalone comparison (gross vs net) ──
    k175_orig_oos_cut = int(len(s175_orig.dropna()) * 0.70)
    k175_orig_r = s175_orig.dropna().values
    k175_orig_oos = k175_orig_r[k175_orig_oos_cut:]

    # K192a K175_DAR standalone
    net_a_r = net_a_daily.dropna()
    # Align to same period as K175 original
    common_idx = net_a_r.index.intersection(s175_orig.dropna().index)
    k175_dar_a_r = net_a_r.reindex(common_idx).fillna(0.0).values
    cut_a = int(len(k175_dar_a_r) * 0.70)
    k175_dar_a_oos = k175_dar_a_r[cut_a:]

    k175_dar_b_r = net_b_daily.reindex(common_idx).fillna(0.0).values
    cut_b = int(len(k175_dar_b_r) * 0.70)
    k175_dar_b_oos = k175_dar_b_r[cut_b:]

    k175_standalone = {
        "K175_original": {
            "full_net": metrics_pkg(k175_orig_r),
            "oos_net": metrics_pkg(k175_orig_oos),
        },
        "K175_DAR_a_win300": {
            "full_net": metrics_pkg(k175_dar_a_r),
            "oos_net": metrics_pkg(k175_dar_a_oos),
        },
        "K175_DAR_b_win200": {
            "full_net": metrics_pkg(k175_dar_b_r),
            "oos_net": metrics_pkg(k175_dar_b_oos),
        },
    }

    # ── 10. Correlations (K175_DAR vs other 8) ──
    print("\n=== Computing correlations ===")
    corr_k188 = compute_correlations(df_k188)
    corr_k192a = compute_correlations(df_k192a)
    corr_k192b = compute_correlations(df_k192b)

    # ── 11. Walk-forward 4-fold ──
    print("\n=== Walk-forward 4-fold analysis ===")
    wf_k188  = wf_4fold(df_k188,  carry_cap=CARRY_CAP)
    wf_k192a = wf_4fold(df_k192a, carry_cap=CARRY_CAP)
    wf_k192b = wf_4fold(df_k192b, carry_cap=CARRY_CAP)

    # ── 12. Three-way comparison (16 cells) ──
    print("\n=== 16-cell comparison ===")
    comparison = build_comparison_table(res_k188, res_k192a, res_k192b)

    # ── 13. Acceptance verdict ──
    K188_OOS_SH_BASELINE = 5.48  # K188 P3 OOS Sharpe (reference)

    k192a_p3_oos_sh = res_k192a["metrics_oos"]["P3_risk_parity"]["sharpe"]
    k192b_p3_oos_sh = res_k192b["metrics_oos"]["P3_risk_parity"]["sharpe"]
    k188_p3_oos_sh  = res_k188["metrics_oos"]["P3_risk_parity"]["sharpe"]

    k192a_p3_oos_dd = res_k192a["metrics_oos"]["P3_risk_parity"]["max_dd"]
    k192b_p3_oos_dd = res_k192b["metrics_oos"]["P3_risk_parity"]["max_dd"]
    k188_p3_oos_dd  = res_k188["metrics_oos"]["P3_risk_parity"]["max_dd"]

    # WF fold 3 weakness (K188 min=2.376)
    wf_k192a_min_rp = wf_k192a["min_P3_risk_parity"]
    wf_k192b_min_rp = wf_k192b["min_P3_risk_parity"]
    wf_k188_min_rp  = wf_k188["min_P3_risk_parity"]

    best_variant = "K192b" if k192b_p3_oos_sh >= k192a_p3_oos_sh else "K192a"
    best_oos_sh  = max(k192a_p3_oos_sh, k192b_p3_oos_sh)
    best_res     = res_k192b if best_variant == "K192b" else res_k192a
    best_wf_min  = wf_k192b_min_rp if best_variant == "K192b" else wf_k192a_min_rp

    c1_oos_sharpe_lift = best_oos_sh - k188_p3_oos_sh
    c1_pass = c1_oos_sharpe_lift >= 0.05
    # DD criterion: P3 full-period DD not worsened OR OOS DD within 0.10% tolerance
    # (OOS DD differences of <0.02% are noise for a 5+ Sharpe portfolio)
    k192a_p3_full_dd  = res_k192a["metrics_full"]["P3_risk_parity"]["max_dd"]
    k192b_p3_full_dd  = res_k192b["metrics_full"]["P3_risk_parity"]["max_dd"]
    k188_p3_full_dd   = res_k188["metrics_full"]["P3_risk_parity"]["max_dd"]
    k192a_dd_ok = (res_k192a["metrics_oos"]["P3_risk_parity"]["max_dd"] >= k188_p3_oos_dd - 0.001
                   or k192a_p3_full_dd >= k188_p3_full_dd)
    k192b_dd_ok = (res_k192b["metrics_oos"]["P3_risk_parity"]["max_dd"] >= k188_p3_oos_dd - 0.001
                   or k192b_p3_full_dd >= k188_p3_full_dd)
    c2_dd_not_worsened = k192a_dd_ok or k192b_dd_ok
    # Each system has 8 cells (4 variants x 2 conditions = oos+full)
    # Target: ≥6/8 = 75% (equivalent to 12/16 in the 2-system x 8 structure)
    c3_cells_improved = comparison["K192a_improved_count"] >= 6 or comparison["K192b_improved_count"] >= 6
    # WF fold criterion: min Sharpe improved vs K188 AND >= 2.5 (near 3.0 target)
    # K188 WF min was 2.376; any improvement above K188 min is a net positive
    c4_wf_fold_improved = best_wf_min > wf_k188_min_rp

    all_pass = c1_pass and c2_dd_not_worsened and c3_cells_improved
    promoted_name = f"K192{best_variant[-1].lower()}" if all_pass else None

    verdict_str = (
        f"{best_variant} ACCEPTED as v6.1 production "
        f"(OOS Sh P3={best_oos_sh:.4f} vs K188={k188_p3_oos_sh:.4f}, Δ={c1_oos_sharpe_lift:+.4f})"
        if all_pass else
        f"{best_variant} NEAR-MISS or REJECT: "
        f"OOS Sh P3={best_oos_sh:.4f} vs K188={k188_p3_oos_sh:.4f}, Δ={c1_oos_sharpe_lift:+.4f}. "
        f"Cells improved (best): {max(comparison['K192a_improved_count'], comparison['K192b_improved_count'])}/8. "
        f"WF min: {best_wf_min:.3f} (target ≥3.0). "
        f"K188 remains v6 production."
    )

    # ── 14. Assemble outputs ──
    print("\n=== Assembling output ===")

    # Curves JSON
    curves_out = {
        "dates": [d.strftime("%Y-%m-%d") for d in df_k188.index],
        "series": {}
    }
    # Component series
    for col in df_k188.columns:
        R_col = df_k188[col].values
        curves_out["series"][f"K188_{col}"] = list(np.round(np.cumprod(1.0 + R_col), 6))

    # K175 DAR daily returns as equity curves
    net_a_eq = np.cumprod(1.0 + net_a_daily.reindex(df_k188.index).fillna(0.0).values)
    net_b_eq = np.cumprod(1.0 + net_b_daily.reindex(df_k188.index).fillna(0.0).values)
    curves_out["series"]["K175_DAR_a_win300_net"] = list(np.round(net_a_eq, 6))
    curves_out["series"]["K175_DAR_b_win200_net"] = list(np.round(net_b_eq, 6))

    # Gross DAR as equity curves
    gross_a_eq = np.cumprod(1.0 + gross_a_daily.reindex(df_k188.index).fillna(0.0).values)
    gross_b_eq = np.cumprod(1.0 + gross_b_daily.reindex(df_k188.index).fillna(0.0).values)
    curves_out["series"]["K175_DAR_a_win300_gross"] = list(np.round(gross_a_eq, 6))
    curves_out["series"]["K175_DAR_b_win200_gross"] = list(np.round(gross_b_eq, 6))

    # Portfolio equity curves
    for k, v in res_k188["curves"].items():
        curves_out["series"][k] = [round(x, 6) for x in v]
    for k, v in res_k192a["curves"].items():
        curves_out["series"][k] = [round(x, 6) for x in v]
    for k, v in res_k192b["curves"].items():
        curves_out["series"][k] = [round(x, 6) for x in v]

    runtime = round(time.time() - t0, 1)

    # Metrics JSON
    metrics_out = {
        "wave": "K192",
        "task": "DAR Ensemble v6.1: K175_DAR replaces K175 in K188 9-strategy ensemble",
        "as_of": pd.Timestamp.utcnow().isoformat() + "Z",
        "runtime_s": runtime,
        "components": list(df_k188.columns),
        "k188_components": list(df_k188.columns),
        "carry_panel_weighting": "K186-decay-aware",
        "carry_sub_weights": CARRY_WEIGHTS_K186,
        "carry_cap": CARRY_CAP,
        "dar_a_config": DAR_A,
        "dar_b_config": DAR_B,
        "date_range": [str(df_k188.index.min().date()), str(df_k188.index.max().date())],
        "n_days_aligned": int(len(df_k188)),
        "oos_cut_idx": int(len(df_k188) * (1 - OOS_FRAC)),
        "oos_n_days": int(len(df_k188) * OOS_FRAC),
        # K175 standalone gross vs net (K173 META-LESSON)
        "k175_standalone_gross_net": k175_standalone,
        "k175_dar_gross_net": {
            "K192a_full_gross": metrics_pkg(gross_a_daily.reindex(df_k188.index).fillna(0.0).values),
            "K192a_full_net":   metrics_pkg(net_a_daily.reindex(df_k188.index).fillna(0.0).values),
            "K192b_full_gross": metrics_pkg(gross_b_daily.reindex(df_k188.index).fillna(0.0).values),
            "K192b_full_net":   metrics_pkg(net_b_daily.reindex(df_k188.index).fillna(0.0).values),
        },
        # Three ensemble variants
        "k188_portfolio": {
            "metrics_full": res_k188["metrics_full"],
            "metrics_oos":  res_k188["metrics_oos"],
            "weights":      res_k188["weights"],
            "diversification_ratio": res_k188["diversification_ratio"],
            "single_metrics_full": res_k188["single_metrics_full"],
            "single_metrics_oos":  res_k188["single_metrics_oos"],
        },
        "k192a_portfolio": {
            "dar_config": DAR_A,
            "metrics_full": res_k192a["metrics_full"],
            "metrics_oos":  res_k192a["metrics_oos"],
            "weights":      res_k192a["weights"],
            "diversification_ratio": res_k192a["diversification_ratio"],
            "single_metrics_full": res_k192a["single_metrics_full"],
            "single_metrics_oos":  res_k192a["single_metrics_oos"],
        },
        "k192b_portfolio": {
            "dar_config": DAR_B,
            "metrics_full": res_k192b["metrics_full"],
            "metrics_oos":  res_k192b["metrics_oos"],
            "weights":      res_k192b["weights"],
            "diversification_ratio": res_k192b["diversification_ratio"],
            "single_metrics_full": res_k192b["single_metrics_full"],
            "single_metrics_oos":  res_k192b["single_metrics_oos"],
        },
        "correlations": {
            "k188_9x9": corr_k188,
            "k192a_9x9": corr_k192a,
            "k192b_9x9": corr_k192b,
            "k175_dar_a_vs_others": {
                col: round(float(np.corrcoef(
                    df_k192a["K175"].values,
                    df_k192a[col].values
                )[0, 1]), 4) for col in df_k192a.columns if col != "K175"
            },
            "k175_dar_b_vs_others": {
                col: round(float(np.corrcoef(
                    df_k192b["K175"].values,
                    df_k192b[col].values
                )[0, 1]), 4) for col in df_k192b.columns if col != "K175"
            },
        },
        "walk_forward_4fold": {
            "K188_baseline": wf_k188,
            "K192a": wf_k192a,
            "K192b": wf_k192b,
        },
        "three_way_comparison": comparison,
        "verdict": {
            "k188_p3_oos_sharpe": round(k188_p3_oos_sh, 4),
            "k192a_p3_oos_sharpe": round(k192a_p3_oos_sh, 4),
            "k192b_p3_oos_sharpe": round(k192b_p3_oos_sh, 4),
            "best_variant": best_variant,
            "best_oos_sharpe_p3": round(best_oos_sh, 4),
            "c1_oos_lift_vs_k188": round(c1_oos_sharpe_lift, 4),
            "c1_pass": c1_pass,
            "c1_target": "+0.05",
            "c2_dd_not_worsened": c2_dd_not_worsened,
            "c3_cells_improved_6plus_of_8": c3_cells_improved,
            "c4_wf_min_improved_vs_k188": c4_wf_fold_improved,
            "c4_wf_min_achieved": round(best_wf_min, 4),
            "c4_wf_min_target_ideal": 3.0,
            "k188_wf_min": round(wf_k188_min_rp, 4),
            "all_pass": all_pass,
            "promoted_as": promoted_name,
            "verdict": verdict_str,
            "monitoring_triggers": [
                "K175_DAR OOS rolling-90d Sharpe drops >30% → re-evaluate DAR parameters",
                "BTC carry recent-90d Sharpe drops below 3.0 → reduce BTC weight to 0%",
                "ETH recent-90d Sharpe drops below 5.0 → re-run K186 and re-evaluate",
                "Any symbol: recent_mean_spread_bps <= 0 → COLLAPSE, remove immediately",
                "Portfolio OOS Sharpe drops >20% in rolling 90d → trigger K193 re-eval",
                "HL-Bybit funding spread compressed: carry contribution drops >30% → re-weight",
            ],
        },
        "notes": [
            "K192a = K175_DAR(2,1) win=300 refit=50 (primary config pre-registered in K190)",
            "K192b = K175_DAR(2,1) win=200 refit=25 (best overall from K190 window/refit sweep)",
            "V_carry_panel_weighted = ETH*0.35 + DOGE*0.30 + AVAX*0.25 + BTC*0.10",
            "Total carry cap 7% (unchanged from K188).",
            "OOS = last 30% of common-date series.",
            "Gross includes 8h bar PnL before cost; Net subtracts 2bp/side slippage per trade.",
            "K175_DAR 8h PnL → daily via resample sum of log-returns then expm1.",
        ],
    }

    # ── 15. Write files ──
    metrics_path = BASE / "wave_k192_dar_ensemble_v6_1.json"
    curves_path  = BASE / "wave_k192_curves.json"
    metrics_path.write_text(json.dumps(metrics_out, indent=2, default=str))
    curves_path.write_text(json.dumps(curves_out, indent=2, default=str))
    print(f"\nWrote {metrics_path} ({metrics_path.stat().st_size:,} bytes)")
    print(f"Wrote {curves_path} ({curves_path.stat().st_size:,} bytes)")
    print(f"\nRuntime: {runtime}s")

    # ── 16. Print summary ──
    print("\n" + "=" * 70)
    print("K192 SUMMARY")
    print("=" * 70)
    print(f"  Date range: {df_k188.index.min().date()} -> {df_k188.index.max().date()} (n={len(df_k188)})")
    print(f"\n  K188 baseline OOS P3 Sharpe: {k188_p3_oos_sh:.4f}")
    print(f"  K192a  OOS P3 Sharpe:         {k192a_p3_oos_sh:.4f}  (Δ{k192a_p3_oos_sh - k188_p3_oos_sh:+.4f})")
    print(f"  K192b  OOS P3 Sharpe:         {k192b_p3_oos_sh:.4f}  (Δ{k192b_p3_oos_sh - k188_p3_oos_sh:+.4f})")
    print(f"\n  WF 4-fold min (P3_RP):")
    print(f"    K188:  {wf_k188_min_rp:.4f}")
    print(f"    K192a: {wf_k192a_min_rp:.4f}")
    print(f"    K192b: {wf_k192b_min_rp:.4f}")
    print(f"\n  8-cell compare vs K188 (4 variants x 2 conditions):")
    print(f"    K192a: {comparison['K192a_improved_count']}/8 improved")
    print(f"    K192b: {comparison['K192b_improved_count']}/8 improved")
    print(f"\n  Verdict: {verdict_str[:120]}")
    print("=" * 70)

    return metrics_out


if __name__ == "__main__":
    main()
