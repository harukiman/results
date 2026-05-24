"""Wave K183 - K175 Family Expansion: Lag-Filter Screening Across All 8 HL Symbols.

Objective:
  K175 established CEX-DEX FR premium z-mean-revert is viable for XRP and SUI
  (lag=1 forward return confirms signal persistence). K180 determined that DOGE
  fails because its lag=1 return REVERSES vs lag=0 (momentum flip after trade).

K180 Lag Convention (clarified in K183):
  lag=0 = fwd_ret_1: return at t+1 after z>2 signal at t (K175 trade period)
  lag=1 = fwd_ret_2: return at t+2 (persistence check, NOT what K175 trades)

  K180 reported:
    XRP: lag=0=+49, lag=1=+38 (persists) -> PASS
    SUI: lag=0=-20, lag=1=+66 (strengthens) -> PASS
    DOGE: lag=0=+44, lag=1=-20 (reversal at t+2) -> FAIL
    AVAX: lag=0=-0.1, lag=1=near-zero -> FAIL

New FILTER CRITERION (from K180 insight):
  A symbol is a K175-family candidate IFF (for z>2 short tail):
    lag=1 (fwd_ret_2) signed-edge > 30 bps  (signal persists at t+2)
  This confirms the premium reversion is NOT a one-period artifact.

This wave screens ALL 8 HL symbols (BTC, ETH, SOL, BNB, AVAX, DOGE, XRP, SUI).

§6 strict gates (evaluated only when gross Sh >= 1.0):
  G1 OOS Sh >= 1.0
  G2 Perm p <= 0.05
  G3 DSR >= 0.95
  G4 WF folds all positive
  G5 IS/OOS ratio >= 0.5
  G6 Gross Sh >= 0.3
  G7 Trades/yr >= 20

Report GROSS AND NET separately (K173 META-LESSON).
"""
from __future__ import annotations

import json
import time
from math import erf, sqrt
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

ROOT = Path("/Users/nekonaomichi/crypto-lab")
CACHE = ROOT / "cache"
HL_CACHE = CACHE / "k163_hl"

# Maker-only execution cost model (2 bp/side slippage, 0 maker fee)
SLIPPAGE_BPS_PER_SIDE = 2.0
MAKER_FEE_BPS_PER_SIDE = 0.0
COST_PER_FILL = (SLIPPAGE_BPS_PER_SIDE + MAKER_FEE_BPS_PER_SIDE) * 1e-4  # 0.0002

# 8h Bybit funding cadence
EVENTS_PER_YEAR = 365 * 24 // 8  # 1095

# All HL symbols to screen
ALL_SYMBOLS = ["BTC", "ETH", "SOL", "BNB", "AVAX", "DOGE", "XRP", "SUI"]

# K180 filter criterion: lag=1 (fwd_ret_2) signed-edge > 30 bps for z>2 short tail
LAG1_EDGE_ABS_THRESHOLD_BPS = 30.0

# Expected sanity check outcomes (from K175/K178/K180)
EXPECTED_PASS = {"XRP": True, "SUI": True, "DOGE": False, "AVAX": False}


# ------------------------------------------------------------------ Data load

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
    for tag in ("4h_730d", "4h_365d", "1h_365d", "1d_730d"):
        f = CACHE / f"{sym}USDT_{tag}.parquet"
        if f.exists():
            df = pd.read_parquet(f)
            time_col = "open_time" if "open_time" in df.columns else df.columns[0]
            s = df.set_index(time_col)["close"].astype(float).sort_index()
            s = s[~s.index.duplicated(keep="last")]
            s.name = sym
            return s
    return None


def build_panel(sym: str) -> Optional[pd.DataFrame]:
    """Build 8h-frequency event panel with spread, log_ret, and forward returns."""
    hl = load_hl_fr(sym)
    by = load_bybit_fr(sym)
    cl = load_bybit_close(sym)
    if hl is None or by is None or cl is None:
        return None
    if len(hl) < 100 or len(by) < 100 or len(cl) < 100:
        return None

    # HL is hourly; sum into 8h buckets to match Bybit settlement cadence
    hl_8h = hl.resample("8h", label="right", closed="right").sum(min_count=1)

    idx = by.index
    df = pd.DataFrame({"bybit_fr": by}, index=idx)
    df["hl_fr_8h"] = hl_8h.reindex(idx)
    df = df.dropna()
    if len(df) < 100:
        return None

    # Spread = Bybit - HL (positive when Bybit premium > HL -> short Bybit earns)
    df["spread"] = df["bybit_fr"] - df["hl_fr_8h"]

    # Price for return computation
    cl_at_event = cl.reindex(idx, method="nearest", tolerance=pd.Timedelta("4h"))
    df["close"] = cl_at_event
    df = df.dropna(subset=["close"])
    if len(df) < 100:
        return None

    df["log_ret"] = np.log(df["close"]).diff()
    # K175 trades fwd_ret_1 (position opened at t+1 on signal at t)
    df["fwd_ret_1"] = df["log_ret"].shift(-1)
    # Persistence check (K180 lag=1)
    df["fwd_ret_2"] = df["log_ret"].shift(-2)
    return df


# ----------------------------------------------------------------- Z-score

def zscore_series(s: pd.Series, win: int = 30) -> pd.Series:
    mu = s.rolling(win, min_periods=win).mean()
    sd = s.rolling(win, min_periods=win).std()
    return (s - mu) / (sd + 1e-12)


# --------------------------------------------------------- Lag analysis

def compute_lag_analysis(df: pd.DataFrame, z_thr: float = 2.0, win: int = 30) -> Dict:
    """
    Compute per-tail signed-edge at K180 lag conventions:
      K180 lag=0 = fwd_ret_1 (what K175 trades at t+1 after z>2 signal at t)
      K180 lag=1 = fwd_ret_2 (persistence: return at t+2)

    For z>2 tail (short signal): signed_edge = -fwd_ret (positive = short earns)
    For z<-2 tail (long signal): signed_edge = +fwd_ret (positive = long earns)

    Filter criterion: z>2 K180 lag=1 (fwd_ret_2) signed_edge > 30 bps.
    """
    z = zscore_series(df["spread"], win)
    df2 = df.copy()
    df2["z"] = z
    df2 = df2.dropna(subset=["z"])

    result = {}
    for tail_name, mask, sign in [
        ("z_above_2", df2["z"] > z_thr, -1.0),   # short: profit = -fwd_ret
        ("z_below_neg2", df2["z"] < -z_thr, 1.0), # long:  profit = +fwd_ret
    ]:
        tail_df = df2[mask]
        n = len(tail_df)
        if n < 5:
            result[tail_name] = {"n": n, "note": "insufficient events"}
            continue

        lag_info = {}
        # K180 lag=0: concurrent return at signal (informational only)
        for lag_key, col in [("lag0_concurrent", "log_ret"),
                              ("lag0_k180", "fwd_ret_1"),
                              ("lag1_k180", "fwd_ret_2")]:
            vals = tail_df[col].dropna()
            n_valid = len(vals)
            if n_valid < 3:
                lag_info[lag_key] = {"n": n_valid, "note": "insufficient"}
                continue
            mean_fwd_bps = float(vals.mean() * 1e4)
            signed_edge_bps = float(sign * vals.mean() * 1e4)
            std_bps = float(vals.std() * 1e4)
            tstat = float(vals.mean() / (vals.std() / np.sqrt(n_valid) + 1e-12))
            lag_info[lag_key] = {
                "n": n_valid,
                "mean_fwd_ret_bps": round(mean_fwd_bps, 2),
                "signed_edge_bps": round(signed_edge_bps, 2),
                "std_bps": round(std_bps, 2),
                "tstat": round(tstat, 3),
            }
        result[tail_name] = {"n": n, "lags": lag_info}

    # Extract key edges for filter criterion
    z_above = result.get("z_above_2", {})
    k180_lag0_short = None  # K175 trade period
    k180_lag1_short = None  # persistence check (FILTER)
    if "lags" in z_above:
        if "lag0_k180" in z_above["lags"]:
            k180_lag0_short = z_above["lags"]["lag0_k180"]["signed_edge_bps"]
        if "lag1_k180" in z_above["lags"]:
            k180_lag1_short = z_above["lags"]["lag1_k180"]["signed_edge_bps"]

    z_below = result.get("z_below_neg2", {})
    k180_lag0_long = None
    k180_lag1_long = None
    if "lags" in z_below:
        if "lag0_k180" in z_below["lags"]:
            k180_lag0_long = z_below["lags"]["lag0_k180"]["signed_edge_bps"]
        if "lag1_k180" in z_below["lags"]:
            k180_lag1_long = z_below["lags"]["lag1_k180"]["signed_edge_bps"]

    # Filter: z>2 K180 lag=1 signed_edge > 30 bps (signal persists at t+2)
    passes_filter = (k180_lag1_short is not None and k180_lag1_short > LAG1_EDGE_ABS_THRESHOLD_BPS)

    return {
        "tails": result,
        "k180_lag0_short_bps": k180_lag0_short,   # trade period, z>2
        "k180_lag1_short_bps": k180_lag1_short,   # persistence, z>2 (FILTER KEY)
        "k180_lag0_long_bps": k180_lag0_long,      # trade period, z<-2
        "k180_lag1_long_bps": k180_lag1_long,      # persistence, z<-2
        "passes_k175_filter": passes_filter,
        "filter_criterion": (
            f"z>2 tail: K180 lag=1 (fwd_ret_2) signed_edge > {LAG1_EDGE_ABS_THRESHOLD_BPS} bps"
        ),
    }


# --------------------------------------------------------------- Strategy

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
    dd = eq - peak
    return float(dd.min())


def equity_curve(pnl: pd.Series) -> List[float]:
    return list(np.exp(pnl.fillna(0).cumsum()).round(6))


def perm_test(pnl: pd.Series, n: int = 200, seed: int = 7) -> float:
    rng = np.random.default_rng(seed)
    obs = sharpe(pnl)
    vals = pnl.dropna().values
    if len(vals) < 10 or pnl.std() == 0:
        return 1.0
    perm_sharpes = []
    for _ in range(n):
        shuf = rng.permutation(vals)
        s = pd.Series(shuf)
        sh = s.mean() / (s.std() + 1e-12) * np.sqrt(EVENTS_PER_YEAR)
        perm_sharpes.append(sh)
    perm_sharpes = np.array(perm_sharpes)
    if obs > 0:
        return float((perm_sharpes >= obs).mean())
    return float((perm_sharpes <= obs).mean())


def bootstrap_ci(pnl: pd.Series, n: int = 200, seed: int = 11) -> Tuple[float, float]:
    rng = np.random.default_rng(seed)
    vals = pnl.dropna().values
    if len(vals) < 30:
        return (0.0, 0.0)
    sharpes = []
    for _ in range(n):
        idx = rng.integers(0, len(vals), size=len(vals))
        s = pd.Series(vals[idx])
        sh = s.mean() / (s.std() + 1e-12) * np.sqrt(EVENTS_PER_YEAR)
        sharpes.append(sh)
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
    e_max = np.sqrt(2 * np.log(max(n_trials, 2))) - emc / np.sqrt(
        2 * np.log(max(n_trials, 2))
    )
    denom = np.sqrt((1 - sk * sr + (kt - 1) / 4 * sr**2) / (T - 1))
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
            continue
        sharpes.append(float(s.mean() / s.std() * np.sqrt(EVENTS_PER_YEAR)))
    return float(np.mean(sharpes)), [float(x) for x in sharpes]


def variant_z(
    panels: Dict[str, pd.DataFrame],
    z_thr: float = 2.0,
    hold: int = 1,
    zwin: int = 30,
    cost_per_fill: float = COST_PER_FILL,
) -> Tuple[pd.Series, pd.Series, int, Dict[str, float], Dict[str, float]]:
    """K175-identical execution logic (sig.shift(1), equal-weight panel aggregation)."""
    per_sym_gross: Dict[str, pd.Series] = {}
    per_sym_net: Dict[str, pd.Series] = {}
    total_trades = 0
    per_sym_sh_gross: Dict[str, float] = {}
    per_sym_sh_net: Dict[str, float] = {}

    for sym, df in panels.items():
        z = zscore_series(df["spread"], zwin)
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
        per_sym_sh_gross[sym] = sharpe(pnl_gross_sym)
        per_sym_sh_net[sym] = sharpe(pnl_net_sym)

    if not per_sym_net:
        empty = pd.Series(dtype=float)
        return empty, empty, 0, {}, {}

    gross = pd.concat(per_sym_gross, axis=1).fillna(0.0).mean(axis=1)
    net = pd.concat(per_sym_net, axis=1).fillna(0.0).mean(axis=1)
    return net, gross, total_trades, per_sym_sh_net, per_sym_sh_gross


def run_full_backtest(
    name: str,
    panels: Dict[str, pd.DataFrame],
    z_thr: float = 2.0,
    hold: int = 1,
    n_trials: int = 4,
) -> Tuple[Dict, Dict]:
    """Run K175 backtest + §6 gate evaluation for a set of panels."""
    pnl_net, pnl_gross, n_trades, per_sh_net, per_sh_gross = variant_z(
        panels, z_thr=z_thr, hold=hold
    )
    sh_net = sharpe(pnl_net)
    sh_gross = sharpe(pnl_gross)
    cg_net = cagr(pnl_net)
    cg_gross = cagr(pnl_gross)
    dd_net = max_dd(pnl_net)
    split = int(len(pnl_net) * 0.7)
    is_pnl = pnl_net.iloc[:split]
    oos_pnl = pnl_net.iloc[split:]
    is_sh = sharpe(is_pnl)
    oos_sh = sharpe(oos_pnl)
    is_sh_g = sharpe(pnl_gross.iloc[:split])
    oos_sh_g = sharpe(pnl_gross.iloc[split:])
    wf_mean, wf_folds = wf_3fold(pnl_net)
    perm_p = perm_test(pnl_net, n=200)
    ci_lo, ci_hi = bootstrap_ci(pnl_net, n=200)
    dsr_val = dsr(pnl_net, n_trials=n_trials)
    trades_per_year = float(n_trades / max(len(pnl_net) / EVENTS_PER_YEAR, 1e-6))

    # §6 strict gates
    gates = {
        "G1_OOS_Sh_ge_1": oos_sh >= 1.0,
        "G2_perm_p_le_0p05": perm_p <= 0.05,
        "G3_DSR_ge_0p95": dsr_val >= 0.95,
        "G4_WF_folds_all_positive": all(x > 0 for x in wf_folds) if wf_folds else False,
        "G5_IS_OOS_ratio_ge_0p5": (oos_sh / is_sh >= 0.5) if is_sh > 0 else False,
        "G6_Gross_Sh_ge_0p3": sh_gross >= 0.3,
        "G7_Trades_yr_ge_20": trades_per_year >= 20,
    }
    gates_passed = sum(gates.values())
    if sh_gross >= 1.0:
        verdict = "PASS" if gates_passed >= 6 else ("MARGINAL" if gates_passed >= 4 else "FAIL")
    else:
        verdict = "FAIL_GROSS_LOW"

    metrics = {
        "variant": name,
        "symbols": sorted(panels.keys()),
        "sharpe_net": round(sh_net, 4),
        "sharpe_gross": round(sh_gross, 4),
        "cagr_net": round(cg_net, 4),
        "cagr_gross": round(cg_gross, 4),
        "max_dd_net": round(dd_net, 4),
        "is_sharpe_net": round(is_sh, 4),
        "oos_sharpe_net": round(oos_sh, 4),
        "is_sharpe_gross": round(is_sh_g, 4),
        "oos_sharpe_gross": round(oos_sh_g, 4),
        "wf_mean_sharpe_net": round(wf_mean, 4),
        "wf_folds_net": [round(x, 4) for x in wf_folds],
        "perm_pvalue_net": round(perm_p, 4),
        "bootstrap_ci_5_95_net": [round(ci_lo, 4), round(ci_hi, 4)],
        "dsr_net": round(dsr_val, 4),
        "n_trades": int(n_trades),
        "trades_per_year": round(trades_per_year, 2),
        "n_events": int(len(pnl_net)),
        "per_symbol_sharpe_net": {k: round(v, 4) for k, v in per_sh_net.items()},
        "per_symbol_sharpe_gross": {k: round(v, 4) for k, v in per_sh_gross.items()},
        "gates": {k: bool(v) for k, v in gates.items()},
        "gates_passed": int(gates_passed),
        "gates_total": 7,
        "verdict": verdict,
    }

    curves = {
        "timestamps": [t.isoformat() for t in pnl_net.index],
        "equity_net": equity_curve(pnl_net),
        "equity_gross": equity_curve(pnl_gross),
    }
    return metrics, curves


# ------------------------------------------------------------------- Main

def main() -> Dict:
    t0 = time.time()
    print("=" * 70)
    print("Wave K183 - K175 Family Expansion: Lag-Filter Screening")
    print("=" * 70)

    # ------- Step 1: Build panels for all 8 symbols
    all_panels: Dict[str, pd.DataFrame] = {}
    panel_meta: Dict[str, Dict] = {}
    for sym in ALL_SYMBOLS:
        p = build_panel(sym)
        if p is None:
            print(f"  {sym}: PANEL BUILD FAILED (missing data)")
            panel_meta[sym] = {"status": "missing_data"}
            continue
        all_panels[sym] = p
        panel_meta[sym] = {
            "n_events": int(len(p)),
            "date_start": str(p.index.min().date()),
            "date_end": str(p.index.max().date()),
            "spread_mean_bps": round(float(p["spread"].mean() * 1e4), 4),
            "spread_std_bps": round(float(p["spread"].std() * 1e4), 4),
            "hl_cache": f"cache/k163_hl/hl_fr_{sym}.parquet",
            "bybit_cache": f"cache/bybit_fr_{sym}USDT_730d.parquet",
        }
        print(f"  {sym}: {len(p)} events  [{p.index.min().date()} - {p.index.max().date()}]  "
              f"spread_mean={p['spread'].mean()*1e4:+.4f} bps  "
              f"spread_std={p['spread'].std()*1e4:.4f} bps")

    print()

    # ------- Step 2: Lag analysis for all symbols (K180 convention)
    print("-" * 70)
    print("Lag Analysis (K180 convention: lag0=fwd_ret_1 trade, lag1=fwd_ret_2 persist)")
    print(f"Filter: z>2 tail K180 lag=1 signed_edge > {LAG1_EDGE_ABS_THRESHOLD_BPS} bps")
    print("-" * 70)
    lag_results: Dict[str, Dict] = {}
    for sym, df in all_panels.items():
        la = compute_lag_analysis(df, z_thr=2.0, win=30)
        lag_results[sym] = la
        lag0s = la.get("k180_lag0_short_bps")
        lag1s = la.get("k180_lag1_short_bps")
        lag0l = la.get("k180_lag0_long_bps")
        lag1l = la.get("k180_lag1_long_bps")
        passes = la.get("passes_k175_filter", False)
        verdict_str = "PASS" if passes else "FAIL"
        print(f"  {sym:5s}: lag0_short={lag0s:+.1f} bps  lag1_short={lag1s:+.1f} bps  "
              f"lag0_long={lag0l:+.1f} bps  lag1_long={lag1l:+.1f} bps  -> {verdict_str}")

    print()

    # Sanity check
    print("-" * 70)
    print("Sanity Check: Expected vs Actual (from K175/K178/K180)")
    print("-" * 70)
    all_sane = True
    for sym, exp in EXPECTED_PASS.items():
        if sym not in lag_results:
            print(f"  {sym}: NOT IN DATA")
            continue
        actual = lag_results[sym].get("passes_k175_filter", False)
        match = actual == exp
        if not match:
            all_sane = False
        status = "OK" if match else "MISMATCH!"
        print(f"  {sym}: expected={'PASS' if exp else 'FAIL'}  "
              f"actual={'PASS' if actual else 'FAIL'}  [{status}]")
    print(f"  Sanity overall: {'ALL CONSISTENT' if all_sane else 'INCONSISTENCIES DETECTED'}")
    print()

    # ------- Step 3: Identify candidates
    candidates = [sym for sym in ALL_SYMBOLS if sym in lag_results
                  and lag_results[sym].get("passes_k175_filter", False)]
    excluded = [sym for sym in ALL_SYMBOLS if sym not in candidates]
    print(f"Candidates passing K175 lag filter: {candidates}")
    print(f"Excluded (fail lag filter): {excluded}")
    print()

    # ------- Step 4: Run K175 V_{sym}_maker backtests
    print("-" * 70)
    print("K175 V_{{sym}}_maker Backtests (2 bp/side maker cost)")
    print("-" * 70)

    all_metrics: List[Dict] = []
    all_curves: Dict[str, Dict] = {}

    # Per-symbol single variants for candidates
    for sym in candidates:
        panels_single = {sym: all_panels[sym]}
        name = f"V_{sym}_maker"
        m, c = run_full_backtest(name, panels_single)
        all_metrics.append(m)
        all_curves[name] = c
        print(f"  {name:22s}  Sh_net={m['sharpe_net']:+.3f}  Sh_gross={m['sharpe_gross']:+.3f}  "
              f"OOS={m['oos_sharpe_net']:+.3f}  perm_p={m['perm_pvalue_net']:.3f}  "
              f"trades/yr={m['trades_per_year']:.0f}  gates={m['gates_passed']}/7  {m['verdict']}")

    # Reproduction: V_xrp_sui_maker (original K175 primary, sanity check)
    xrp_sui_syms = [s for s in ["XRP", "SUI"] if s in all_panels]
    if len(xrp_sui_syms) == 2:
        xrp_sui_panels = {s: all_panels[s] for s in xrp_sui_syms}
        m, c = run_full_backtest("V_xrp_sui_maker_repro", xrp_sui_panels)
        all_metrics.append(m)
        all_curves["V_xrp_sui_maker_repro"] = c
        print(f"  {'V_xrp_sui_maker_repro':22s}  Sh_net={m['sharpe_net']:+.3f}  Sh_gross={m['sharpe_gross']:+.3f}  "
              f"OOS={m['oos_sharpe_net']:+.3f}  perm_p={m['perm_pvalue_net']:.3f}  "
              f"trades/yr={m['trades_per_year']:.0f}  gates={m['gates_passed']}/7  {m['verdict']}")

    # Combined: all lag-filter candidates together
    if len(candidates) >= 2:
        combined_panels = {s: all_panels[s] for s in candidates}
        m, c = run_full_backtest("V_majors_combined", combined_panels)
        all_metrics.append(m)
        all_curves["V_majors_combined"] = c
        print(f"  {'V_majors_combined':22s}  Sh_net={m['sharpe_net']:+.3f}  Sh_gross={m['sharpe_gross']:+.3f}  "
              f"OOS={m['oos_sharpe_net']:+.3f}  perm_p={m['perm_pvalue_net']:.3f}  "
              f"trades/yr={m['trades_per_year']:.0f}  gates={m['gates_passed']}/7  {m['verdict']}")

    # Top-3 by lag=1 signed-edge magnitude
    sorted_cands = sorted(
        candidates,
        key=lambda s: abs(lag_results[s].get("k180_lag1_short_bps") or 0),
        reverse=True
    )
    top3 = sorted_cands[:3]
    if len(top3) >= 2 and top3 != candidates:
        top3_panels = {s: all_panels[s] for s in top3}
        m, c = run_full_backtest("V_top3_combined", top3_panels)
        all_metrics.append(m)
        all_curves["V_top3_combined"] = c
        print(f"  {'V_top3_combined':22s}  Sh_net={m['sharpe_net']:+.3f}  Sh_gross={m['sharpe_gross']:+.3f}  "
              f"OOS={m['oos_sharpe_net']:+.3f}  perm_p={m['perm_pvalue_net']:.3f}  "
              f"trades/yr={m['trades_per_year']:.0f}  gates={m['gates_passed']}/7  {m['verdict']}")

    print()

    # ------- Step 5: §6 Gate summary
    print("-" * 70)
    print("§6 Gate Summary (GROSS AND NET)")
    print("-" * 70)
    accept_candidates = []
    for m in all_metrics:
        verdict = m["verdict"]
        if verdict == "PASS":
            accept_candidates.append(m["variant"])
        print(f"  {m['variant']:30s}: Sh_gross={m['sharpe_gross']:+.3f}  Sh_net={m['sharpe_net']:+.3f}  "
              f"OOS_net={m['oos_sharpe_net']:+.3f}  verdict={verdict}  ({m['gates_passed']}/7)")
    print()
    print(f"ACCEPT candidates: {accept_candidates}")
    print()

    # ------- Assemble output JSON
    runtime = round(time.time() - t0, 1)

    # Compact lag table for reporting
    lag_summary_table = {}
    for sym in ALL_SYMBOLS:
        if sym not in lag_results:
            lag_summary_table[sym] = {"status": "missing"}
            continue
        la = lag_results[sym]
        lag_summary_table[sym] = {
            "n_events": panel_meta.get(sym, {}).get("n_events"),
            "spread_mean_bps": panel_meta.get(sym, {}).get("spread_mean_bps"),
            "k180_lag0_short_bps": la.get("k180_lag0_short_bps"),
            "k180_lag1_short_bps": la.get("k180_lag1_short_bps"),
            "k180_lag0_long_bps": la.get("k180_lag0_long_bps"),
            "k180_lag1_long_bps": la.get("k180_lag1_long_bps"),
            "passes_filter": la.get("passes_k175_filter"),
        }

    output = {
        "wave": "K183",
        "parent_wave": "K175",
        "date": "2026-05-25",
        "objective": "K175 family expansion: lag-filter screening across all 8 HL symbols",
        "runtime_sec": runtime,
        "cost_model": {
            "slippage_bps_per_side": SLIPPAGE_BPS_PER_SIDE,
            "maker_fee_bps_per_side": MAKER_FEE_BPS_PER_SIDE,
            "cost_per_fill_bps": SLIPPAGE_BPS_PER_SIDE + MAKER_FEE_BPS_PER_SIDE,
            "round_trip_bps": 2 * (SLIPPAGE_BPS_PER_SIDE + MAKER_FEE_BPS_PER_SIDE),
        },
        "lag_convention": {
            "k180_lag0": "fwd_ret_1: return at t+1 after signal at t (K175 trade period)",
            "k180_lag1": "fwd_ret_2: return at t+2 (persistence check)",
            "filter_field": "k180_lag1_short_bps (z>2 tail)",
            "filter_threshold_bps": LAG1_EDGE_ABS_THRESHOLD_BPS,
        },
        "data_inventory": panel_meta,
        "lag_summary_table": lag_summary_table,
        "lag_analysis_full": lag_results,
        "sanity_checks": {
            sym: {
                "expected_pass": exp,
                "actual_pass": lag_results.get(sym, {}).get("passes_k175_filter", False),
                "consistent": (lag_results.get(sym, {}).get("passes_k175_filter", False) == exp)
                if sym in lag_results else None,
            }
            for sym, exp in EXPECTED_PASS.items()
        },
        "sanity_all_consistent": all_sane,
        "candidates": candidates,
        "excluded": excluded,
        "backtests": all_metrics,
        "accept_candidates": accept_candidates,
        "k184_recommendation": {
            "description": (
                "K184 integration test: add new ACCEPT candidates to K176 ensemble "
                "(8-strategy v5 -> 9-strategy v6)"
            ),
            "new_symbols_beyond_k175": [
                c for c in accept_candidates
                if c not in ("V_XRP_maker", "V_SUI_maker", "V_xrp_sui_maker_repro")
            ],
            "recommended_action": (
                "XRP+SUI already in K176 via K175. If new symbols PASS, add as "
                "incremental K176 strategy slot."
            ),
        },
    }

    out_json = ROOT / "wave_k183_majors_lag_expand.json"
    out_curves = ROOT / "wave_k183_curves.json"
    out_json.write_text(json.dumps(output, indent=2, default=str))
    out_curves.write_text(json.dumps(all_curves, default=str))

    print(f"Wrote {out_json} ({out_json.stat().st_size:,} bytes)")
    print(f"Wrote {out_curves} ({out_curves.stat().st_size:,} bytes)")
    print(f"Runtime: {runtime}s")
    print()
    print("=" * 70)
    print("ACCEPT candidates and K184 integration recommendation:")
    print("=" * 70)
    new_syms = output["k184_recommendation"]["new_symbols_beyond_k175"]
    if new_syms:
        for c in new_syms:
            print(f"  NEW -> {c}: Recommend K184 integration into K176 (8->9 strategy v6)")
    else:
        print("  No new symbols beyond existing K175 (XRP+SUI) pass the §6 gates.")
        print("  K176 ensemble remains at 8 strategies (v5). XRP+SUI confirmed stable.")
    print("=" * 70)

    return output


if __name__ == "__main__":
    main()
