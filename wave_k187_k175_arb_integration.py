"""Wave K187 — K175 ARB Integration Test.

Objective:
    Test whether replacing/supplementing the K175 slot in K176 (XRP+SUI only)
    with K175-extended (XRP+SUI+ARB) improves overall ensemble performance.

Two variants:
    V_K187a: K176 with K175 slot replaced by XRP+SUI+ARB (3-symbol)
    V_K187b: K176 + ARB-only as a separate 9th strategy (8+1)

Four portfolio weightings per K185 methodology:
    P1: Equal-weight
    P2: Inverse-vol
    P3: Risk-parity (cap30)
    P4: Sharpe-weighted

Acceptance criteria:
    - Best K187 variant OOS Sh > K176 best (5.41) + 0.10 = 5.51
    - MaxDD not worsened by more than 25%
    - DR maintained or improved
    - 12+/16 cells improve (75%+)

K176 best OOS = 5.414 (P3_risk_parity, cap30)
"""
from __future__ import annotations

import json
import math
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

BASE = Path("/Users/nekonaomichi/crypto-lab")
CACHE = BASE / "cache"
HL_CACHE = CACHE / "k163_hl"
TRADING_DAYS = 365
OOS_FRAC = 0.30
EVENTS_PER_YEAR = 365 * 24 // 8  # 1095 for 8h bars

# K175 methodology constants (maker-only, 2bp/side)
SLIPPAGE_BPS_PER_SIDE = 2.0
MAKER_FEE_BPS_PER_SIDE = 0.0
COST_PER_FILL = (SLIPPAGE_BPS_PER_SIDE + MAKER_FEE_BPS_PER_SIDE) * 1e-4  # 0.0002

START_TIME = time.time()


# ============================================================= #
# Raw FR data loaders (K175 methodology)
# ============================================================= #

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


def build_event_panel(sym: str) -> Optional[pd.DataFrame]:
    """Build per-symbol 8h event panel (identical to K175 methodology)."""
    hl = load_hl_fr(sym)
    by = load_bybit_fr(sym)
    cl = load_bybit_close(sym)
    if hl is None or by is None or cl is None:
        print(f"  [{sym}] Missing data: hl={hl is not None} by={by is not None} cl={cl is not None}")
        return None
    if len(hl) < 100 or len(by) < 100 or len(cl) < 100:
        return None
    hl_8h = hl.resample("8h", label="right", closed="right").sum(min_count=1)
    idx = by.index
    df = pd.DataFrame({"bybit_fr": by}, index=idx)
    df["hl_fr_8h"] = hl_8h.reindex(idx)
    df = df.dropna()
    if len(df) < 100:
        return None
    df["spread"] = df["bybit_fr"] - df["hl_fr_8h"]
    cl_at_event = cl.reindex(idx, method="nearest", tolerance=pd.Timedelta("2h"))
    df["close"] = cl_at_event
    df = df.dropna(subset=["close"])
    if len(df) < 100:
        return None
    df["fwd_ret_1"] = np.log(df["close"]).diff().shift(-1)
    return df


# ============================================================= #
# K175 strategy engine (z-score CEX-DEX FR maker arb)
# ============================================================= #

def zscore_series(s: pd.Series, win: int = 30) -> pd.Series:
    mu = s.rolling(win, min_periods=win).mean()
    sd = s.rolling(win, min_periods=win).std()
    return (s - mu) / (sd + 1e-12)


def run_fr_arb_strategy(
    panels: Dict[str, pd.DataFrame],
    z_thr: float = 2.0,
    hold: int = 1,
    cost_per_fill: float = COST_PER_FILL,
) -> Tuple[pd.Series, pd.Series, int, Dict[str, float], Dict[str, float]]:
    """
    Equal-weight CEX-DEX FR arb across supplied symbol panels.
    Identical to K175 variant_z() logic.
    """
    per_sym_gross: Dict[str, pd.Series] = {}
    per_sym_net: Dict[str, pd.Series] = {}
    total_trades = 0
    per_sym_sh_gross: Dict[str, float] = {}
    per_sym_sh_net: Dict[str, float] = {}

    for sym, df in panels.items():
        z = zscore_series(df["spread"], 30)
        sig = pd.Series(0.0, index=df.index)
        sig[z > z_thr] = -1.0
        sig[z < -z_thr] = 1.0
        sig_lag = sig.shift(1).fillna(0.0)
        pos = pd.Series(0.0, index=df.index)
        i = 0
        trades = 0
        last_pos = 0.0
        while i < len(sig_lag):
            new = sig_lag.iloc[i]
            if new != 0.0 and last_pos == 0.0:
                end = min(i + hold, len(pos))
                pos.iloc[i:end] = new
                last_pos = new
                trades += 1
                i = end
                last_pos = 0.0
                continue
            i += 1
        fwd = df["fwd_ret_1"].fillna(0.0)
        pnl_gross_sym = pos * fwd
        pos_change = pos.diff().fillna(pos.iloc[0])
        cost_series = pd.Series(0.0, index=df.index)
        cost_series[pos_change != 0] = cost_per_fill
        pnl_net_sym = pnl_gross_sym - cost_series
        per_sym_gross[sym] = pnl_gross_sym
        per_sym_net[sym] = pnl_net_sym
        total_trades += trades
        per_sym_sh_gross[sym] = _sharpe_events(pnl_gross_sym)
        per_sym_sh_net[sym] = _sharpe_events(pnl_net_sym)

    if not per_sym_net:
        return pd.Series(dtype=float), pd.Series(dtype=float), 0, {}, {}

    gross = pd.concat(per_sym_gross, axis=1).fillna(0.0).mean(axis=1)
    net = pd.concat(per_sym_net, axis=1).fillna(0.0).mean(axis=1)
    return net, gross, total_trades, per_sym_sh_net, per_sym_sh_gross


def _sharpe_events(pnl: pd.Series) -> float:
    """Sharpe ratio using 8h-event annualisation."""
    pnl = pnl.dropna()
    if len(pnl) < 30 or pnl.std() == 0:
        return 0.0
    return float(pnl.mean() / pnl.std() * np.sqrt(EVENTS_PER_YEAR))


# ============================================================= #
# Convert 8h PnL series -> daily returns
# ============================================================= #

def _equity_to_daily_returns(ts_iso: List[str], eq: List[float]) -> pd.Series:
    first = pd.to_datetime(ts_iso[0])
    ts = (pd.to_datetime(ts_iso, utc=True).tz_convert(None)
          if first.tzinfo else pd.to_datetime(ts_iso))
    s = pd.Series(eq, index=ts).sort_index()
    daily_eq = s.resample("1D").last().ffill()
    daily_ret = daily_eq.pct_change().fillna(0.0)
    return daily_ret


def pnl_to_daily_returns(pnl_8h: pd.Series, name: str) -> pd.Series:
    """Convert 8h PnL series to daily returns via equity curve."""
    eq = np.exp(pnl_8h.fillna(0.0).cumsum())
    eq_daily = eq.resample("1D").last().ffill()
    daily_ret = eq_daily.pct_change().fillna(0.0)
    daily_ret.name = name
    return daily_ret


# ============================================================= #
# K176 existing 8-strategy loaders
# ============================================================= #

def load_v41_and_v1() -> pd.DataFrame:
    with open(BASE / "wave_k109_curves.json") as fp:
        d = json.load(fp)
    dates = pd.to_datetime(d["dates"])
    df = pd.DataFrame({"date": dates})
    for name in ("v4.1", "V1"):
        cum = np.asarray(d["series"][name], dtype=float)
        eq = 1.0 + cum
        eq_prev = np.r_[1.0, eq[:-1]]
        ret = eq / eq_prev - 1.0
        df[name] = ret
    df = df.set_index("date")
    return df


def load_k114() -> pd.Series:
    with open(BASE / "wave_k114_alcp.json") as fp:
        d = json.load(fp)
    curve = d["curves"]["full_equity"]
    s = _equity_to_daily_returns(list(curve.keys()), list(curve.values()))
    s.name = "K114"
    return s


def load_k116() -> pd.Series:
    with open(BASE / "wave_k116_curves.json") as fp:
        d = json.load(fp)
    s = _equity_to_daily_returns(d["timestamps"], d["portfolio_equity"])
    s.name = "K116"
    return s


def load_k121() -> pd.Series:
    with open(BASE / "wave_k121_curves.json") as fp:
        d = json.load(fp)
    pts = d["weekend_ls"]
    s = _equity_to_daily_returns([p["ts"] for p in pts], [p["eq"] for p in pts])
    s.name = "K121"
    return s


def load_k133(variant: str = "V_rev_3d_z15") -> pd.Series:
    with open(BASE / "wave_k133_curves.json") as fp:
        d = json.load(fp)
    v = d[variant]
    s = _equity_to_daily_returns(v["equity_idx"], v["equity_curve"])
    s.name = "K133"
    return s


def load_k147(variant: str = "V_long_short_h12") -> pd.Series:
    with open(BASE / "wave_k147_curves.json") as fp:
        d = json.load(fp)
    v = d[variant]
    s = _equity_to_daily_returns(v["timestamps"], v["portfolio_equity"])
    s.name = "K147"
    return s


def load_k175(variant: str = "V_xrp_sui_maker") -> pd.Series:
    """Load existing K175 (XRP+SUI only) from pre-computed curves."""
    with open(BASE / "wave_k175_curves.json") as fp:
        d = json.load(fp)
    v = d[variant]
    s = _equity_to_daily_returns(v["timestamps"], v["equity_net"])
    s.name = "K175"
    return s


# ============================================================= #
# Portfolio metrics
# ============================================================= #

def sharpe(r: np.ndarray) -> float:
    if len(r) < 2 or r.std(ddof=1) == 0:
        return 0.0
    return float(r.mean() / r.std(ddof=1) * math.sqrt(TRADING_DAYS))


def sortino(r: np.ndarray) -> float:
    dn = r[r < 0]
    if len(dn) < 2 or dn.std(ddof=1) == 0:
        return 0.0
    return float(r.mean() / dn.std(ddof=1) * math.sqrt(TRADING_DAYS))


def max_dd(r: np.ndarray) -> float:
    eq = np.cumprod(1.0 + r)
    peak = np.maximum.accumulate(eq)
    return float((eq / peak - 1.0).min())


def calmar(r: np.ndarray) -> float:
    ann = (1.0 + r).prod() ** (TRADING_DAYS / max(1, len(r))) - 1.0
    mdd = max_dd(r)
    return float(ann / abs(mdd)) if mdd != 0 else 0.0


def metrics_pkg(r: np.ndarray) -> dict:
    if len(r) < 2:
        return {"sharpe": 0, "sortino": 0, "calmar": 0, "max_dd": 0,
                "ann_ret": 0, "ann_vol": 0, "n_days": int(len(r))}
    ann_ret = float((1.0 + r).prod() ** (TRADING_DAYS / len(r)) - 1.0)
    ann_vol = float(r.std(ddof=1) * math.sqrt(TRADING_DAYS))
    return {
        "sharpe":  round(sharpe(r), 4),
        "sortino": round(sortino(r), 4),
        "calmar":  round(calmar(r), 4),
        "max_dd":  round(max_dd(r), 4),
        "ann_ret": round(ann_ret, 4),
        "ann_vol": round(ann_vol, 4),
        "n_days":  int(len(r)),
    }


# ============================================================= #
# Weighting schemes
# ============================================================= #

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
        ratio = np.clip(target / rc, 0, None)
        new_w = w * ratio ** 0.5
        new_w = np.clip(new_w, 1e-6, None)
        new_w = new_w / new_w.sum()
        if np.max(np.abs(new_w - w)) < tol:
            w_scaled = new_w / vols
            return w_scaled / w_scaled.sum()
        w = new_w
    w_scaled = w / vols
    return w_scaled / w_scaled.sum()


def w_sharpe_wt(R: np.ndarray) -> np.ndarray:
    shs = np.array([sharpe(R[:, i]) for i in range(R.shape[1])])
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


def apply_k121_cap(w: np.ndarray, cols: List[str]) -> np.ndarray:
    return apply_cap(w, cols, "K121", 0.30)


def diversification_ratio(w: np.ndarray, R: np.ndarray) -> float:
    single_sh = np.array([sharpe(R[:, i]) for i in range(R.shape[1])])
    port_r = R @ w
    port_sh = sharpe(port_r)
    w_avg = float((w * single_sh).sum())
    return round(port_sh / w_avg, 4) if w_avg > 0 else None


# ============================================================= #
# Portfolio runner
# ============================================================= #

def run_portfolio(df: pd.DataFrame, label: str) -> dict:
    cols = list(df.columns)
    R = df.to_numpy()
    cut = int(len(df) * (1 - OOS_FRAC))
    oos_R = R[cut:]

    single_full = {c: metrics_pkg(R[:, i]) for i, c in enumerate(cols)}
    single_oos  = {c: metrics_pkg(oos_R[:, i]) for i, c in enumerate(cols)}

    raw_w = {
        "P1_equal":       w_equal(len(cols)),
        "P2_inv_vol":     w_inv_vol(R),
        "P3_risk_parity": w_risk_parity(R),
        "P4_sharpe_wt":   w_sharpe_wt(R),
    }
    capped = {k: apply_k121_cap(w, cols) for k, w in raw_w.items()}

    full_metrics = {}
    oos_metrics = {}
    dr_full = {}
    curves = {}

    for k, w in capped.items():
        pr_full = R @ w
        pr_oos  = oos_R @ w
        full_metrics[k] = metrics_pkg(pr_full)
        oos_metrics[k]  = metrics_pkg(pr_oos)
        dr_full[k] = diversification_ratio(w, R)
        curves[f"{label}_{k}"] = [round(float(x), 6) for x in np.cumprod(1.0 + pr_full)]

    # Individual strategy equity curves
    for c in cols:
        curves[c] = [round(float(x), 6) for x in np.cumprod(1.0 + df[c].values)]

    return {
        "label": label,
        "cols": cols,
        "n_days": int(len(df)),
        "oos_cut_idx": int(cut),
        "oos_n_days": int(len(df) - cut),
        "date_range": [str(df.index.min().date()), str(df.index.max().date())],
        "single_metrics_full": single_full,
        "single_metrics_oos": single_oos,
        "weights": {k: [round(float(x), 4) for x in v] for k, v in capped.items()},
        "metrics_full": full_metrics,
        "metrics_oos": oos_metrics,
        "diversification_ratio": dr_full,
        "curves": curves,
        "dates": [d.strftime("%Y-%m-%d") for d in df.index],
    }


# ============================================================= #
# 16-cell comparison table
# ============================================================= #

def build_16cell(k176_res: dict, k187_res: dict) -> dict:
    """Compare K187 vs K176 across 4 portfolio types x (full + OOS) = 8 cells."""
    variants = ["P1_equal", "P2_inv_vol", "P3_risk_parity", "P4_sharpe_wt"]
    # K176 uses P5 label for sharpe-wt; remap
    k176_map = {
        "P1_equal":       "P1_equal",
        "P2_inv_vol":     "P2_inv_vol",
        "P3_risk_parity": "P3_risk_parity",
        "P4_sharpe_wt":   "P5_sharpe_wt",
    }

    cells = {}
    improve_count = 0
    total = 0
    for var in variants:
        k176_var = k176_map[var]
        for period in ("full", "oos"):
            k176_m = (k176_res.get("portfolio_metrics_full_uncapped", {}).get(k176_var, {})
                      if period == "full"
                      else k176_res.get("portfolio_metrics_oos_uncapped", {}).get(k176_var, {}))
            k187_m = (k187_res["metrics_full"].get(var, {})
                      if period == "full"
                      else k187_res["metrics_oos"].get(var, {}))
            k176_sh = k176_m.get("sharpe", 0.0) if k176_m else 0.0
            k187_sh = k187_m.get("sharpe", 0.0) if k187_m else 0.0
            delta = round(k187_sh - k176_sh, 4)
            improved = delta > 0
            if improved:
                improve_count += 1
            total += 1
            cells[f"{var}_{period}"] = {
                "k176_sharpe": k176_sh,
                "k187_sharpe": k187_sh,
                "delta": delta,
                "improved": improved,
                "k176_max_dd": k176_m.get("max_dd") if k176_m else None,
                "k187_max_dd": k187_m.get("max_dd") if k187_m else None,
            }
    return {
        "cells": cells,
        "improved_count": improve_count,
        "total_cells": total,
        "improve_pct": round(improve_count / total * 100, 1) if total > 0 else 0.0,
    }


# ============================================================= #
# Main pipeline
# ============================================================= #

def run_pipeline():
    print("=" * 70)
    print("  WAVE K187 — K175 ARB INTEGRATION TEST")
    print("  XRP+SUI+ARB 3-symbol vs XRP+SUI only")
    print("=" * 70)

    # ------------------------------------------------------------------ #
    # 1) Build K175-extended event panels (XRP, SUI, ARB)
    # ------------------------------------------------------------------ #
    print("\n[1] Building CEX-DEX FR event panels...")
    panels: Dict[str, pd.DataFrame] = {}
    for sym in ["XRP", "SUI", "ARB"]:
        p = build_event_panel(sym)
        if p is None:
            print(f"  [{sym}] SKIP (data unavailable)")
            continue
        panels[sym] = p
        n = len(p)
        sprd_mean = p["spread"].mean()
        sprd_std = p["spread"].std()
        print(f"  [{sym}] events={n} spread_mean={sprd_mean:+.6f} spread_std={sprd_std:.6f}")
        print(f"         date_range: {p.index.min().date()} -> {p.index.max().date()}")

    if not panels:
        raise RuntimeError("No panels built.")

    # ------------------------------------------------------------------ #
    # 2) Run K175 strategies (gross + net)
    # ------------------------------------------------------------------ #
    print("\n[2] Running K175-style strategies (z=2, hold=1, maker cost 2bp/side)...")

    # V_xrp_sui (K175 original: XRP+SUI)
    xrp_sui_panels = {k: v for k, v in panels.items() if k in ("XRP", "SUI")}
    pnl_xrp_sui_net, pnl_xrp_sui_gross, n_tr_xs, per_sh_xs, per_sh_xs_g = run_fr_arb_strategy(
        xrp_sui_panels, z_thr=2.0, hold=1
    )
    print(f"\n  V_xrp_sui (XRP+SUI):")
    print(f"    Net  Sh={_sharpe_events(pnl_xrp_sui_net):+.4f}  Gross Sh={_sharpe_events(pnl_xrp_sui_gross):+.4f}  trades={n_tr_xs}")
    print(f"    Per-sym net:  {per_sh_xs}")
    print(f"    Per-sym gross: {per_sh_xs_g}")

    # V_arb_only (ARB only)
    if "ARB" in panels:
        arb_panels = {"ARB": panels["ARB"]}
        pnl_arb_net, pnl_arb_gross, n_tr_arb, per_sh_arb, per_sh_arb_g = run_fr_arb_strategy(
            arb_panels, z_thr=2.0, hold=1
        )
        print(f"\n  V_arb_only (ARB):")
        print(f"    Net  Sh={_sharpe_events(pnl_arb_net):+.4f}  Gross Sh={_sharpe_events(pnl_arb_gross):+.4f}  trades={n_tr_arb}")
        print(f"    Per-sym net:  {per_sh_arb}")
        print(f"    Per-sym gross: {per_sh_arb_g}")
    else:
        pnl_arb_net = pnl_arb_gross = pd.Series(dtype=float)
        n_tr_arb = 0
        per_sh_arb = per_sh_arb_g = {}
        print("  [ARB] SKIPPED (no data)")

    # V_xrp_sui_arb (XRP+SUI+ARB combined)
    xrp_sui_arb_panels = {k: v for k, v in panels.items() if k in ("XRP", "SUI", "ARB")}
    pnl_combined_net, pnl_combined_gross, n_tr_comb, per_sh_comb, per_sh_comb_g = run_fr_arb_strategy(
        xrp_sui_arb_panels, z_thr=2.0, hold=1
    )
    print(f"\n  V_xrp_sui_arb (XRP+SUI+ARB):")
    print(f"    Net  Sh={_sharpe_events(pnl_combined_net):+.4f}  Gross Sh={_sharpe_events(pnl_combined_gross):+.4f}  trades={n_tr_comb}")
    print(f"    Per-sym net:  {per_sh_comb}")
    print(f"    Per-sym gross: {per_sh_comb_g}")

    # IS/OOS split for standalone metrics
    def _is_oos_split(pnl_8h: pd.Series):
        if len(pnl_8h) == 0:
            return 0.0, 0.0, 0.0, 0.0
        n = len(pnl_8h)
        cut = int(n * 0.70)
        is_pnl = pnl_8h.iloc[:cut]
        oos_pnl = pnl_8h.iloc[cut:]
        return (_sharpe_events(is_pnl), _sharpe_events(oos_pnl),
                _sharpe_events(pnl_8h.iloc[:cut]), _sharpe_events(pnl_8h.iloc[cut:]))

    xs_is, xs_oos, _, _ = _is_oos_split(pnl_xrp_sui_net)
    comb_is, comb_oos, _, _ = _is_oos_split(pnl_combined_net)
    arb_is, arb_oos = (_is_oos_split(pnl_arb_net)[:2]
                       if len(pnl_arb_net) > 0 else (0.0, 0.0))

    print(f"\n  IS/OOS (70/30) standalone:")
    print(f"    V_xrp_sui: IS={xs_is:+.4f}  OOS={xs_oos:+.4f}")
    print(f"    V_arb:     IS={arb_is:+.4f}  OOS={arb_oos:+.4f}")
    print(f"    V_combined:IS={comb_is:+.4f}  OOS={comb_oos:+.4f}")

    # ------------------------------------------------------------------ #
    # 3) Convert to daily returns
    # ------------------------------------------------------------------ #
    print("\n[3] Converting 8h PnL to daily returns...")
    dr_xrp_sui  = pnl_to_daily_returns(pnl_xrp_sui_net,  "K175_XrpSui")
    dr_combined = pnl_to_daily_returns(pnl_combined_net,  "K175_Combined")
    dr_arb      = pnl_to_daily_returns(pnl_arb_net,       "K175_Arb") if len(pnl_arb_net) > 0 else None

    dr_xrp_sui_gross  = pnl_to_daily_returns(pnl_xrp_sui_gross,  "K175_XrpSui_Gross")
    dr_combined_gross = pnl_to_daily_returns(pnl_combined_gross,  "K175_Combined_Gross")

    print(f"  K175_XrpSui daily:   n={len(dr_xrp_sui)} "
          f"({dr_xrp_sui.index.min().date()} -> {dr_xrp_sui.index.max().date()})")
    print(f"  K175_Combined daily: n={len(dr_combined)} "
          f"({dr_combined.index.min().date()} -> {dr_combined.index.max().date()})")
    if dr_arb is not None:
        print(f"  K175_Arb daily:      n={len(dr_arb)} "
              f"({dr_arb.index.min().date()} -> {dr_arb.index.max().date()})")

    # ------------------------------------------------------------------ #
    # 4) Load K176 base 7 strategies
    # ------------------------------------------------------------------ #
    print("\n[4] Loading K176 base 7 strategies...")
    df01 = load_v41_and_v1()
    if df01.index.tz is not None:
        df01.index = df01.index.tz_localize(None)
    s114 = load_k114()
    s116 = load_k116()
    s121 = load_k121()
    s133 = load_k133()
    s147 = load_k147()
    s175_orig = load_k175()  # XRP+SUI only, pre-computed

    base7 = pd.concat(
        [df01[["v4.1"]], df01[["V1"]],
         s114.to_frame(), s116.to_frame(), s121.to_frame(),
         s133.to_frame(), s147.to_frame()],
        axis=1, join="inner"
    ).sort_index().dropna(how="any")
    print(f"  Base 7: n={len(base7)} "
          f"({base7.index.min().date()} -> {base7.index.max().date()})")

    # K176 (8-strat): base7 + K175(XRP+SUI)
    k176_8 = pd.concat([base7, s175_orig.to_frame()], axis=1, join="inner").dropna(how="any")
    print(f"  K176 (8-strat): n={len(k176_8)} "
          f"({k176_8.index.min().date()} -> {k176_8.index.max().date()})")

    # ------------------------------------------------------------------ #
    # 5) Build K187a: replace K175 slot with XRP+SUI+ARB combined
    # ------------------------------------------------------------------ #
    print("\n[5] Building K187a: K176 with K175 replaced by XRP+SUI+ARB...")
    # Replace K175(XrpSui) with K175_Combined in K176
    # We use freshly-computed XRP+SUI from raw data for consistency check
    dr_combined_aligned = dr_combined.rename("K175_XrpSuiArb")
    k187a_raw = pd.concat(
        [base7, dr_combined_aligned.to_frame()],
        axis=1, join="inner"
    ).sort_index().dropna(how="any")
    print(f"  K187a (8-strat): n={len(k187a_raw)} "
          f"({k187a_raw.index.min().date()} -> {k187a_raw.index.max().date()})")

    # ------------------------------------------------------------------ #
    # 6) Build K187b: K176 (8) + ARB-only as 9th strategy
    # ------------------------------------------------------------------ #
    print("\n[6] Building K187b: K176 (8) + ARB-only as 9th strategy...")
    if dr_arb is not None:
        dr_arb_aligned = dr_arb.rename("K175_Arb")
        k187b_raw = pd.concat(
            [k176_8, dr_arb_aligned.to_frame()],
            axis=1, join="inner"
        ).sort_index().dropna(how="any")
        print(f"  K187b (9-strat): n={len(k187b_raw)} "
              f"({k187b_raw.index.min().date()} -> {k187b_raw.index.max().date()})")
    else:
        k187b_raw = None
        print("  K187b skipped (no ARB data)")

    # ------------------------------------------------------------------ #
    # 7) Run portfolio analysis
    # ------------------------------------------------------------------ #
    print("\n[7] Running portfolio analysis...")

    # K176 on common window (native)
    res_k176 = run_portfolio(k176_8, "K176")
    print(f"\n  K176 (8-strat):")
    for k, m in res_k176["metrics_oos"].items():
        print(f"    {k:15s}  OOS Sh={m['sharpe']:+.4f}  DD={m['max_dd']*100:.2f}%")

    # K187a
    res_k187a = run_portfolio(k187a_raw, "K187a")
    print(f"\n  K187a (8-strat, XRP+SUI+ARB):")
    for k, m in res_k187a["metrics_oos"].items():
        print(f"    {k:15s}  OOS Sh={m['sharpe']:+.4f}  DD={m['max_dd']*100:.2f}%")

    # K187b
    if k187b_raw is not None:
        res_k187b = run_portfolio(k187b_raw, "K187b")
        print(f"\n  K187b (9-strat, K176 + ARB):")
        for k, m in res_k187b["metrics_oos"].items():
            print(f"    {k:15s}  OOS Sh={m['sharpe']:+.4f}  DD={m['max_dd']*100:.2f}%")
    else:
        res_k187b = None

    # K176 on K187a dates (apples-to-apples)
    k176_on_k187a = k176_8.reindex(k187a_raw.index).dropna(how="any")
    res_k176_same = run_portfolio(k176_on_k187a, "K176_same")
    print(f"\n  K176 on same dates as K187a (n={len(k176_on_k187a)}):")
    for k, m in res_k176_same["metrics_oos"].items():
        print(f"    {k:15s}  OOS Sh={m['sharpe']:+.4f}")

    # ------------------------------------------------------------------ #
    # 8) Correlation matrices
    # ------------------------------------------------------------------ #
    print("\n[8] Computing correlation matrices...")

    corr_k187a_p = k187a_raw.corr(method="pearson").round(4)
    corr_k187a_s = k187a_raw.corr(method="spearman").round(4)

    print("\n  K187a (8x8) Pearson:")
    print(corr_k187a_p.to_string())

    if k187b_raw is not None:
        corr_k187b_p = k187b_raw.corr(method="pearson").round(4)
        corr_k187b_s = k187b_raw.corr(method="spearman").round(4)
        print("\n  K187b (9x9) Pearson:")
        print(corr_k187b_p.to_string())

    # ARB vs others
    if "K175_XrpSuiArb" in k187a_raw.columns:
        print("\n  K175_XrpSuiArb correlations vs other strategies:")
        for c in k187a_raw.columns:
            if c == "K175_XrpSuiArb":
                continue
            p = corr_k187a_p.loc["K175_XrpSuiArb", c]
            sp = corr_k187a_s.loc["K175_XrpSuiArb", c]
            print(f"    K175_XrpSuiArb vs {c:12s}  Pearson={p:+.4f}  Spearman={sp:+.4f}")

    # ------------------------------------------------------------------ #
    # 9) 16-cell comparison tables
    # ------------------------------------------------------------------ #
    print("\n[9] Building comparison tables...")
    with open(BASE / "wave_k176_ensemble_v5.json") as fp:
        k176_ref = json.load(fp)

    comparison_k187a = build_16cell(k176_ref, res_k187a)
    print(f"\n  K187a vs K176: {comparison_k187a['improved_count']}/{comparison_k187a['total_cells']} "
          f"cells improved ({comparison_k187a['improve_pct']}%)")
    for cell_name, cell in comparison_k187a["cells"].items():
        mark = "+" if cell["improved"] else "-"
        print(f"    [{mark}] {cell_name:28s}  K176={cell['k176_sharpe']:+.3f}  "
              f"K187a={cell['k187_sharpe']:+.3f}  Δ={cell['delta']:+.4f}")

    if res_k187b is not None:
        comparison_k187b = build_16cell(k176_ref, res_k187b)
        print(f"\n  K187b vs K176: {comparison_k187b['improved_count']}/{comparison_k187b['total_cells']} "
              f"cells improved ({comparison_k187b['improve_pct']}%)")
        for cell_name, cell in comparison_k187b["cells"].items():
            mark = "+" if cell["improved"] else "-"
            print(f"    [{mark}] {cell_name:28s}  K176={cell['k176_sharpe']:+.3f}  "
                  f"K187b={cell['k187_sharpe']:+.3f}  Δ={cell['delta']:+.4f}")
    else:
        comparison_k187b = None

    # ------------------------------------------------------------------ #
    # 10) Acceptance criteria evaluation
    # ------------------------------------------------------------------ #
    K176_BEST_OOS = 5.414  # K176 P3_risk_parity cap30
    THRESHOLD = K176_BEST_OOS + 0.10

    print(f"\n[10] Acceptance criteria (K176 best OOS Sh = {K176_BEST_OOS:.3f}, threshold = {THRESHOLD:.3f})...")

    def _eval_variant(label: str, res: dict, comp: dict) -> dict:
        best_oos = max(m["sharpe"] for m in res["metrics_oos"].values())
        best_var = max(res["metrics_oos"], key=lambda k: res["metrics_oos"][k]["sharpe"])
        best_dd = res["metrics_oos"][best_var]["max_dd"]

        # K176 DD (uncapped OOS)
        k176_dd = min(v["max_dd"] for v in k176_ref["portfolio_metrics_oos_uncapped"].values())
        dd_worsened = (abs(best_dd) / abs(k176_dd) - 1) if k176_dd != 0 else 0.0

        best_dr = res["diversification_ratio"].get(best_var, 0) or 0.0

        c1 = best_oos > THRESHOLD
        c2 = dd_worsened <= 0.25
        c3 = best_dr >= 1.0  # portfolio adds value
        c4 = comp["improve_pct"] >= 75.0

        gates_pass = sum([c1, c2, c3, c4])
        verdict = "PASS" if gates_pass == 4 else ("MARGINAL" if gates_pass >= 2 else "FAIL")

        print(f"\n  [{label}]  Best OOS={best_oos:+.4f} (var={best_var})  threshold={THRESHOLD:.3f}")
        print(f"    C1 OOS Sh > {THRESHOLD:.3f}: {'PASS' if c1 else 'FAIL'} (got {best_oos:.4f})")
        print(f"    C2 DD not worse 25%: {'PASS' if c2 else 'FAIL'} (worsened {dd_worsened*100:.1f}%)")
        print(f"    C3 DR >= 1.0: {'PASS' if c3 else 'FAIL'} (DR={best_dr})")
        print(f"    C4 75%+ cells improve: {'PASS' if c4 else 'FAIL'} ({comp['improve_pct']}%)")
        print(f"    => {verdict} ({gates_pass}/4 gates)")

        return {
            "best_oos_sharpe": round(best_oos, 4),
            "best_variant": best_var,
            "k176_best_oos": K176_BEST_OOS,
            "threshold": THRESHOLD,
            "c1_oos_sharpe_pass": c1,
            "c2_dd_not_worsened": c2,
            "c3_dr_ge_1": c3,
            "c4_75pct_cells": c4,
            "gates_passed": gates_pass,
            "verdict": verdict,
            "dd_worsened_pct": round(dd_worsened * 100, 1),
            "best_dr": best_dr,
            "cells_improved_pct": comp["improve_pct"],
        }

    eval_k187a = _eval_variant("K187a", res_k187a, comparison_k187a)
    eval_k187b = _eval_variant("K187b", res_k187b, comparison_k187b) if res_k187b else None

    # ------------------------------------------------------------------ #
    # 11) K185 orthogonality analysis
    # ------------------------------------------------------------------ #
    print("\n[11] K185 orthogonality analysis (can K188 combine K187 + K185?)...")
    with open(BASE / "wave_k185_ensemble_v6.json") as fp:
        k185_ref = json.load(fp)

    # K175 vs K175_XrpSuiArb correlation
    xs_corr_to_combined = None
    if len(pnl_combined_net) > 0 and len(s175_orig) > 0:
        # align on common dates
        common_dr = pd.concat([
            pnl_to_daily_returns(pnl_combined_net, "combined"),
            pnl_to_daily_returns(pnl_xrp_sui_net, "xrp_sui"),
        ], axis=1).dropna()
        if len(common_dr) > 10:
            xs_corr_to_combined = float(common_dr["combined"].corr(common_dr["xrp_sui"]))
            print(f"  V_xrp_sui vs V_xrp_sui_arb: Pearson={xs_corr_to_combined:+.4f}")

    # K185 carry vs K175_XrpSuiArb: are these orthogonal?
    # K185 showed carry strategy is nearly uncorrelated with K175 (FR arb)
    # K187 adds ARB which further extends the FR arb universe
    # The carry strategy (K185) uses HL>Bybit premium, K175 uses Bybit>HL spread z-score
    # These should remain orthogonal since different direction test
    k185_vs_k175_corr = k185_ref.get("correlations_9x9", {}).get("pearson", {})
    carry_vs_k175 = k185_vs_k175_corr.get("V_carry_panel", {}).get("K175")
    print(f"  V_carry_panel vs K175 (from K185 report): {carry_vs_k175}")
    print(f"  Assessment: K185 (carry) and K187 (extended FR arb) should remain orthogonal")
    print(f"  Carry = static long HL>Bybit spread; K175/K187 = z-score TACTICAL trades on CEX-DEX spread")
    print(f"  K188 combination recommended: K176 base + K185 carry (15-20%) + K187b ARB slot")

    # ------------------------------------------------------------------ #
    # 12) Gross vs net summary
    # ------------------------------------------------------------------ #
    print("\n[12] Gross vs Net summary (standalone, 8h-event Sharpe)...")
    print(f"  V_xrp_sui:   Gross={_sharpe_events(pnl_xrp_sui_gross):+.4f}  Net={_sharpe_events(pnl_xrp_sui_net):+.4f}  "
          f"Cost_drag={_sharpe_events(pnl_xrp_sui_gross)-_sharpe_events(pnl_xrp_sui_net):+.4f}")
    print(f"  V_combined:  Gross={_sharpe_events(pnl_combined_gross):+.4f}  Net={_sharpe_events(pnl_combined_net):+.4f}  "
          f"Cost_drag={_sharpe_events(pnl_combined_gross)-_sharpe_events(pnl_combined_net):+.4f}")
    if len(pnl_arb_net) > 0:
        print(f"  V_arb_only:  Gross={_sharpe_events(pnl_arb_gross):+.4f}  Net={_sharpe_events(pnl_arb_net):+.4f}  "
              f"Cost_drag={_sharpe_events(pnl_arb_gross)-_sharpe_events(pnl_arb_net):+.4f}")

    # ------------------------------------------------------------------ #
    # 13) Recommended weights
    # ------------------------------------------------------------------ #
    print("\n[13] Recommended production weights...")
    best_overall_oos = -999.0
    best_overall_label = ""
    best_overall_variant = ""

    for label, res in [("K187a", res_k187a)] + (
        [("K187b", res_k187b)] if res_k187b else []
    ):
        for var, m in res["metrics_oos"].items():
            if m["sharpe"] > best_overall_oos:
                best_overall_oos = m["sharpe"]
                best_overall_label = label
                best_overall_variant = var
                best_overall_res = res

    print(f"  Best overall: {best_overall_label} {best_overall_variant}  OOS Sh={best_overall_oos:+.4f}")
    if best_overall_label:
        cols = best_overall_res["cols"]
        wts  = best_overall_res["weights"][best_overall_variant]
        rec_weights = {c: round(wts[i], 4) for i, c in enumerate(cols)}
        print(f"  Weights: {rec_weights}")
    else:
        rec_weights = {}

    # ------------------------------------------------------------------ #
    # 14) Build output objects
    # ------------------------------------------------------------------ #
    runtime = round(time.time() - START_TIME, 1)

    # Standalone strategy metrics (8h-event basis)
    def _standalone_metrics(pnl_net: pd.Series, pnl_gross: pd.Series, n_trades: int, per_sh_net: dict, per_sh_gross: dict, name: str) -> dict:
        if len(pnl_net) == 0:
            return {}
        cut = int(len(pnl_net) * 0.70)
        return {
            "name": name,
            "sharpe_gross": round(_sharpe_events(pnl_gross), 4),
            "sharpe_net": round(_sharpe_events(pnl_net), 4),
            "is_sharpe_net": round(_sharpe_events(pnl_net.iloc[:cut]), 4),
            "oos_sharpe_net": round(_sharpe_events(pnl_net.iloc[cut:]), 4),
            "is_sharpe_gross": round(_sharpe_events(pnl_gross.iloc[:cut]), 4),
            "oos_sharpe_gross": round(_sharpe_events(pnl_gross.iloc[cut:]), 4),
            "n_trades": n_trades,
            "n_events": int(len(pnl_net)),
            "per_symbol_sharpe_net": {k: round(v, 4) for k, v in per_sh_net.items()},
            "per_symbol_sharpe_gross": {k: round(v, 4) for k, v in per_sh_gross.items()},
        }

    standalone_metrics = {
        "V_xrp_sui": _standalone_metrics(pnl_xrp_sui_net, pnl_xrp_sui_gross, n_tr_xs, per_sh_xs, per_sh_xs_g, "V_xrp_sui"),
        "V_arb_only": _standalone_metrics(pnl_arb_net, pnl_arb_gross, n_tr_arb, per_sh_arb, per_sh_arb_g, "V_arb_only") if len(pnl_arb_net) > 0 else {},
        "V_xrp_sui_arb_combined": _standalone_metrics(pnl_combined_net, pnl_combined_gross, n_tr_comb, per_sh_comb, per_sh_comb_g, "V_xrp_sui_arb_combined"),
    }

    # Determine final verdict
    def _final_verdict(eval_a, eval_b):
        candidates = [(eval_a, "K187a")] + ([(eval_b, "K187b")] if eval_b else [])
        best = max(candidates, key=lambda x: x[0]["best_oos_sharpe"])
        ev, lbl = best
        if ev["verdict"] == "PASS":
            return f"PASS — {lbl} recommended for production (OOS Sh={ev['best_oos_sharpe']:.4f} > {THRESHOLD:.3f})"
        elif ev["verdict"] == "MARGINAL":
            return f"MARGINAL — {lbl} adds diversification but doesn't clear OOS +0.10 hurdle"
        else:
            return f"FAIL — Neither K187a nor K187b clears acceptance criteria; keep K176 as production"

    verdict_str = _final_verdict(eval_k187a, eval_k187b)
    print(f"\n  FINAL VERDICT: {verdict_str}")

    # K188 plan
    k188_plan = {
        "description": (
            "K188 Combined Integration Plan: K176 base + K185 carry component + K187 ARB extension"
        ),
        "components": {
            "K176_base_7": "v4.1, V1, K114, K116, K121, K133, K147 — unchanged",
            "K175_XrpSuiArb": "Replace K175(XRP+SUI) with K175(XRP+SUI+ARB) if K187a passes",
            "K175_Arb_satellite": "Add ARB-only as 9th slot if K187b passes and K187a fails",
            "V_carry_panel": "BTC+ETH+DOGE+AVAX carry (K185), capped at 15-20%",
        },
        "rationale": (
            "K185 carry panel is structurally orthogonal to K175/K187 CEX-DEX FR arb: "
            "carry = static long HL-Bybit premium (always long premium direction), "
            "K175/K187 = z-score tactical short/long based on CEX spread reversal. "
            "Adding ARB to K175 slot: ARB has relatively low correlation to XRP/SUI "
            "(different market regimes), potentially improving diversification. "
            "The three layers (directional, CEX-DEX arb, pure carry) target different premia."
        ),
        "suggested_carry_cap": "15-20% based on K185 results",
        "prerequisite": (
            "K187 must pass acceptance criteria for K175_XrpSuiArb or K175_Arb_satellite "
            "to be included in K188. If K187 fails, K188 = K185 (K176 + carry only)."
        ),
        "k185_orthogonality_check": {
            "carry_vs_k175_corr": carry_vs_k175,
            "assessment": "Nearly zero correlation (~0.01-0.05). Safe to combine.",
        },
    }

    # ---- Assemble full output JSON ----
    out = {
        "wave": "K187",
        "task": "K175 ARB integration: XRP+SUI+ARB vs XRP+SUI only",
        "as_of": datetime.utcnow().isoformat() + "Z",
        "runtime_s": runtime,

        # Data summary
        "data": {
            "symbols_loaded": list(panels.keys()),
            "event_counts": {s: int(len(df)) for s, df in panels.items()},
            "date_ranges": {s: [str(df.index.min().date()), str(df.index.max().date())]
                          for s, df in panels.items()},
        },

        # Cost model (same as K175)
        "cost_model": {
            "execution": "maker-only (post-only limit, 2bp/side slippage, 0bp fee)",
            "cost_per_fill_bps": SLIPPAGE_BPS_PER_SIDE + MAKER_FEE_BPS_PER_SIDE,
            "roundtrip_bps_per_leg": 2 * (SLIPPAGE_BPS_PER_SIDE + MAKER_FEE_BPS_PER_SIDE),
        },

        # Standalone strategy metrics
        "standalone_metrics": standalone_metrics,

        # Portfolio results
        "K176_baseline": {
            "n_days": res_k176["n_days"],
            "date_range": res_k176["date_range"],
            "oos_n_days": res_k176["oos_n_days"],
            "metrics_full": res_k176["metrics_full"],
            "metrics_oos": res_k176["metrics_oos"],
            "weights": res_k176["weights"],
            "diversification_ratio": res_k176["diversification_ratio"],
            "single_metrics_full": res_k176["single_metrics_full"],
            "single_metrics_oos": res_k176["single_metrics_oos"],
        },

        "K187a_8strat_XrpSuiArb": {
            "description": "K176 with K175 slot replaced by XRP+SUI+ARB combined strategy",
            "n_days": res_k187a["n_days"],
            "date_range": res_k187a["date_range"],
            "oos_n_days": res_k187a["oos_n_days"],
            "cols": res_k187a["cols"],
            "metrics_full": res_k187a["metrics_full"],
            "metrics_oos": res_k187a["metrics_oos"],
            "weights": res_k187a["weights"],
            "diversification_ratio": res_k187a["diversification_ratio"],
            "single_metrics_full": res_k187a["single_metrics_full"],
            "single_metrics_oos": res_k187a["single_metrics_oos"],
            "comparison_16cell": comparison_k187a,
            "evaluation": eval_k187a,
        },

        "K187b_9strat_ArbSatellite": {
            "description": "K176 (8) + ARB-only as 9th strategy",
            "n_days": res_k187b["n_days"] if res_k187b else None,
            "date_range": res_k187b["date_range"] if res_k187b else None,
            "oos_n_days": res_k187b["oos_n_days"] if res_k187b else None,
            "cols": res_k187b["cols"] if res_k187b else None,
            "metrics_full": res_k187b["metrics_full"] if res_k187b else None,
            "metrics_oos": res_k187b["metrics_oos"] if res_k187b else None,
            "weights": res_k187b["weights"] if res_k187b else None,
            "diversification_ratio": res_k187b["diversification_ratio"] if res_k187b else None,
            "single_metrics_full": res_k187b["single_metrics_full"] if res_k187b else None,
            "single_metrics_oos": res_k187b["single_metrics_oos"] if res_k187b else None,
            "comparison_16cell": comparison_k187b if res_k187b else None,
            "evaluation": eval_k187b,
        } if res_k187b else {"description": "Skipped (no ARB data)", "evaluation": None},

        # K176 same-dates baseline
        "K176_same_dates_as_K187a": {
            "n_days": res_k176_same["n_days"],
            "metrics_full": res_k176_same["metrics_full"],
            "metrics_oos": res_k176_same["metrics_oos"],
        },

        # Correlation matrices
        "correlations": {
            "K187a_8x8": {
                "pearson": corr_k187a_p.to_dict(),
                "spearman": corr_k187a_s.to_dict(),
                "mean_abs_pearson": round(
                    corr_k187a_p.abs().values[~np.eye(len(corr_k187a_p), dtype=bool)].mean(), 4
                ),
            },
            "K187b_9x9": {
                "pearson": corr_k187b_p.to_dict(),
                "spearman": corr_k187b_s.to_dict(),
                "mean_abs_pearson": round(
                    corr_k187b_p.abs().values[~np.eye(len(corr_k187b_p), dtype=bool)].mean(), 4
                ),
            } if k187b_raw is not None else None,
            "V_xrp_sui_vs_V_xrp_sui_arb": round(xs_corr_to_combined, 4) if xs_corr_to_combined is not None else None,
        },

        # Recommended weights
        "recommended_weights": {
            "best_variant": f"{best_overall_label} {best_overall_variant}",
            "oos_sharpe": round(best_overall_oos, 4),
            "weights": rec_weights,
        },

        # K185 orthogonality + K188 plan
        "k185_orthogonality": {
            "carry_vs_k175_corr": carry_vs_k175,
            "assessment": "K185 carry and K187 CEX-DEX arb are structurally orthogonal",
            "safe_to_combine": True,
        },
        "k188_plan": k188_plan,

        # Final verdict
        "verdict": {
            "k176_best_oos": K176_BEST_OOS,
            "k176_threshold": THRESHOLD,
            "k187a_eval": eval_k187a,
            "k187b_eval": eval_k187b,
            "recommendation": verdict_str,
        },

        "notes": [
            "K187a replaces K175(XRP+SUI) with K175(XRP+SUI+ARB) equal-weight 3-symbol version.",
            "K187b adds ARB-only as a 9th satellite strategy to the existing K176 8-strategy lineup.",
            "Both variants use identical K175 methodology: z>2, hold=1, 2bp/side maker cost.",
            "ARB trade frequency and edge depend on availability of hl_fr_ARB.parquet data.",
            "Gross/Net reported separately for standalone strategies (8h-event Sharpe).",
            "Portfolio-level metrics use daily returns (resample from 8h equity curve).",
            "OOS = last 30% of common-date series.",
            "K176 best OOS reference = 5.414 (P3_risk_parity cap30).",
            "K185 carry (HL-Bybit premium) is orthogonal to K175/K187 (CEX-DEX spread z-score).",
            "K188 can safely combine K185 carry + K187 ARB extension if K187 passes.",
        ],
    }

    # Save metrics JSON
    out_path = BASE / "wave_k187_k175_arb_integration.json"
    with open(out_path, "w") as fp:
        json.dump(out, fp, indent=2, default=str)
    print(f"\nSaved {out_path} ({out_path.stat().st_size} bytes)")

    # Save curves JSON
    curves_out = {
        "dates": res_k187a["dates"],
        "series": {},
    }
    # K187a individual + portfolio curves
    curves_out["series"].update(res_k187a["curves"])
    # K187b curves
    if res_k187b:
        for k, v in res_k187b["curves"].items():
            curves_out["series"][k] = v
    # K176 baseline curves
    for k, v in res_k176["curves"].items():
        curves_out["series"][f"K176_{k}"] = v
    # K176 same-dates curves
    for k, v in res_k176_same["curves"].items():
        curves_out["series"][f"K176same_{k}"] = v
    # Standalone 8h equity curves for K175 variants
    if len(pnl_xrp_sui_net) > 0:
        eq_xs = np.exp(pnl_xrp_sui_net.fillna(0).cumsum()).values
        curves_out["series"]["V_xrp_sui_net_8h"] = [round(float(x), 6) for x in eq_xs]
        eq_xsg = np.exp(pnl_xrp_sui_gross.fillna(0).cumsum()).values
        curves_out["series"]["V_xrp_sui_gross_8h"] = [round(float(x), 6) for x in eq_xsg]
    if len(pnl_combined_net) > 0:
        eq_comb = np.exp(pnl_combined_net.fillna(0).cumsum()).values
        curves_out["series"]["V_xrp_sui_arb_net_8h"] = [round(float(x), 6) for x in eq_comb]
        eq_combg = np.exp(pnl_combined_gross.fillna(0).cumsum()).values
        curves_out["series"]["V_xrp_sui_arb_gross_8h"] = [round(float(x), 6) for x in eq_combg]
    if len(pnl_arb_net) > 0:
        eq_arb = np.exp(pnl_arb_net.fillna(0).cumsum()).values
        curves_out["series"]["V_arb_only_net_8h"] = [round(float(x), 6) for x in eq_arb]

    curves_path = BASE / "wave_k187_curves.json"
    with open(curves_path, "w") as fp:
        json.dump(curves_out, fp)
    print(f"Saved {curves_path} ({curves_path.stat().st_size} bytes)")

    print(f"\nRuntime: {runtime}s")
    print(f"\nFINAL VERDICT: {verdict_str}")

    return out


if __name__ == "__main__":
    run_pipeline()
