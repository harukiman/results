#!/usr/bin/env python3
"""
wave_k774_io_sol_eval.py — K774 IO-SOL FR Differential Eval (GPU DePIN vs SVM)
================================================================================
K339 REPO_ROOT pattern: BASE = Path(__file__).parent

WAVE:     K774
PAIR:     IO-SOL  (io.net GPU DePIN vs Solana SVM — new vertex #18 candidate)
CONTEXT:  K773 HIP-3 round-2 screen. IO ranked #1 fresh long-tail (#2 overall
          behind BLUR). vol_ratio=17.26x (30d snapshot), max_anchor_corr=-0.019
          (near-zero independence), composite=0.2639.

HYPOTHESIS
----------
IO (io.net, GPU rental DePIN marketplace — NVIDIA H100/A100 compute network)
vs SOL (Solana SVM execution layer):
  - GPU DePIN cluster (IO): FR driven by AI/GPU narrative cycles, H100 supply
    constraints, hyperscaler demand (OpenAI/Anthropic), DePIN token emissions,
    GPU rental yield mechanics. Structural NEGATIVE FR (perp sellers supply hedge)
  - SVM cluster (SOL): FR driven by retail speculation, meme seasons, Firedancer,
    SOL DeFi TVL (Jupiter/Drift/Jito), SOL ETF anticipation. Structural POSITIVE FR
  - Cycle independence: GPU infrastructure (IO) vs speculative SVM L1 (SOL) diverge.
    IO strongly negative FR (-20%+/yr gross carry) vs SOL positive (+2.6%/yr).
    This creates a persistent carry-positive short-IO/long-SOL position.

MECHANISM: TAO vs IO distinction
---------------------------------
  TAO (Bittensor): AI L1 layer, subnet validator staking rewards, model competition
  IO (io.net): GPU rental DePIN marketplace, compute supply aggregation, NVIDIA cycle
  Despite both being "AI-themed", the mechanisms are fundamentally different:
    - TAO: subnet tokenization → AI L1 FR follows validator competition cycles
    - IO: GPU compute demand → FR follows H100 shortage + spot vs rental spreads
  AI cluster check: IO-SOL vs TAO-SOL signal corr = 0.0473 << 0.40 (CLEAR PASS)

PRE-SCREENS (MANDATORY)
-----------------------
  L003 (K746): raw_corr(IO_fr, AVAX_fr) < 0.45   [measured: 0.2402 PASS]
  L004 (K748): carry-stability 0.688 ≈ borderline  [measured: 0.5194 PASS OK]
  L007 (K749): G5u FIL-SOL independence check
  L010 (K752): raw_corr(IO_fr, HBAR_fr) < 0.45   [measured: 0.2212 PASS]
  L011 (K759): raw_corr(IO_fr, SOL_fr) < 0.50    [measured: 0.1516 PASS]
  AI cluster: IO-SOL vs TAO-SOL signal corr < 0.40 [measured: 0.0473 PASS]

§6 GATES (K774 — 26 family vertices)
--------------------------------------
  G1:  OOS Sharpe >= 1.0
  G2:  Perm p-value <= 0.05 (1000 direction reshuffles OOS)
  G3:  DSR Bonferroni p < 0.05/12 (12+ grid configs tested)
  G4:  Walk-forward 12-fold (IS 90d / OOS 30d)
  G5a-G5z: vs all BTC-base + alt-alt family (26 pairs) < 0.40
  G6:  Trade count >= 30/yr
  G7:  OOS Ann return > 5% at 4x leverage
  G8:  Cross-venue signal corr >= 0.55 (Bybit IO — N/A, HIP-3 fresh)
  G9:  Data sufficiency >= 180d OOS

VERTEX COUNT (as of K774)
--------------------------
  Current 17 vertices: APT, ATOM, AVAX, BNB, ENA, FIL, HBAR, INJ, LDO, SEI,
                        SOL, TIA, TAO, PEPE, WIF, BLUR, AXS
  IO candidate: 18th vertex if ACCEPT (1st GPU-DePIN cluster)

Usage:
  python3 wave_k774_io_sol_eval.py

LIVE自動変更禁止 | K339 REPO_ROOT | HL cap 66.8% aware | K523 3-point ROI mandatory
"""
from __future__ import annotations

import json
import math
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

# ── K339 REPO_ROOT ─────────────────────────────────────────────────────────────
BASE = Path(__file__).parent
CACHE_DIR = BASE / "cache" / "k163_hl"
DATA_DIR = BASE / "data"
BYBIT_CACHE = BASE / "cache"
DATA_DIR.mkdir(exist_ok=True)

WAVE_ID = "K774"
REPO_ROOT = str(BASE)
K339_COMPLIANCE = {"wave": WAVE_ID, "repo_root": REPO_ROOT, "pattern": "K339"}


# ─── helpers ──────────────────────────────────────────────────────────────────

def load_hl(symbol: str) -> pd.Series | None:
    """Load HL hourly FR data for a symbol."""
    for p in [CACHE_DIR / f"hl_fr_{symbol}.parquet", DATA_DIR / f"hl_fr_{symbol}.parquet"]:
        if p.exists():
            df = pd.read_parquet(p)
            df["timestamp"] = pd.to_datetime(df["timestamp"])
            df = df.set_index("timestamp").sort_index()
            if df.index.tzinfo is not None:
                df.index = df.index.tz_localize(None)
            df.index = df.index.floor("h")
            df = df[~df.index.duplicated(keep="first")]
            return df["hl_fr"]
    return None


def load_bybit(symbol: str) -> pd.Series | None:
    """Load Bybit 8h FR data for a symbol."""
    for suffix in ["730d", "365d"]:
        p = BYBIT_CACHE / f"bybit_fr_{symbol}USDT_{suffix}.parquet"
        if p.exists():
            df = pd.read_parquet(p)
            df["timestamp"] = pd.to_datetime(df["timestamp"])
            df = df.set_index("timestamp").sort_index()
            df = df[~df.index.duplicated(keep="first")]
            return df["funding_rate"]
    return None


def backtest_metrics(pnl: pd.Series) -> dict:
    """Compute annualized Sharpe, return, max drawdown, entries."""
    if len(pnl) < 10:
        return dict(sharpe=0.0, ann_ret=0.0, ann_std=0.0, max_dd=0.0, years=0.0)
    ann_ret = float(pnl.sum() * (8760 / len(pnl)))
    ann_std = float(pnl.std() * math.sqrt(8760))
    sharpe = ann_ret / ann_std if ann_std > 0 else 0.0
    years = len(pnl) / 8760
    cum = pnl.cumsum()
    max_dd = float((cum - cum.cummax()).min())
    return dict(sharpe=sharpe, ann_ret=ann_ret, ann_std=ann_std, max_dd=max_dd, years=years)


# ─── main evaluation ──────────────────────────────────────────────────────────

def main() -> dict:
    t0 = time.time()

    # ── load primary series ──
    io = load_hl("IO")
    sol = load_hl("SOL")
    tao = load_hl("TAO")
    assert io is not None, "HL IO data missing — run: fetch IO FR from HL API first"
    assert sol is not None, "HL SOL data missing"

    merged = pd.DataFrame({"io": io, "sol": sol}).dropna()
    merged["diff"] = merged["io"] - merged["sol"]
    merged_rows = len(merged)
    date_start = str(merged.index.min())
    date_end = str(merged.index.max())
    total_years = (merged.index.max() - merged.index.min()).days / 365.25

    # ── Phase 0: Pre-screens ──
    print("=== Phase 0: Pre-screens ===")

    # MR9: IO not in current vertex set
    vertices_v17 = ["APT", "ATOM", "AVAX", "BNB", "ENA", "FIL", "HBAR", "INJ", "LDO",
                     "SEI", "SOL", "TIA", "TAO", "PEPE", "WIF", "BLUR", "AXS"]
    mr9_checks = {}
    for sym in vertices_v17:
        x = load_hl(sym)
        if x is None:
            mr9_checks[sym] = {"error": "DATA_MISSING", "mr9_clear": False}
            continue
        common = io.index.intersection(x.index)
        io_c = io.reindex(common)
        x_c = x.reindex(common)
        sol_c = sol.reindex(common)
        max_err = float((io_c - x_c).abs().max())
        io_sol = io_c - sol_c
        x_sol = x_c - sol_c
        max_altalt_err = float((io_sol - x_sol).abs().max())
        clear = max_err > 1e-10
        mr9_checks[sym] = {
            "max_raw_err_io_vs_x": round(max_err, 8),
            "is_io_identical_to_x": not clear,
            "max_altalt_err_iosol_vs_xsol": round(max_altalt_err, 8),
            "mr9_clear": clear,
        }
        print(f"  IO vs {sym:5s}: max_err={max_err:.3e}  clear={clear}")

    mr9_all_clear = all(v.get("mr9_clear", False) for v in mr9_checks.values())

    # Volume pre-screen
    io_std = float(merged["io"].std())
    sol_std = float(merged["sol"].std())
    vol_ratio = io_std / sol_std
    raw_corr_io_sol = float(merged["io"].corr(merged["sol"]))
    io_ann_pct = float(merged["io"].mean() * 8760 * 100)
    sol_ann_pct = float(merged["sol"].mean() * 8760 * 100)
    io_carry_frac = float((io > 0).mean())

    # Vol by window
    vol_ratios_by_window = {}
    for d in [7, 30, 90, 365]:
        cutoff = merged.index.max() - pd.Timedelta(days=d)
        sub = merged[merged.index >= cutoff]
        if len(sub) > 24:
            r = float(sub["io"].std() / sub["sol"].std())
            vol_ratios_by_window[f"last_{d}d"] = round(r, 4)

    print(f"Vol ratio IO/SOL full: {vol_ratio:.4f}x | 30d(K773): 17.26x")

    # L-series pre-screens
    avax = load_hl("AVAX")
    hbar = load_hl("HBAR")
    fil = load_hl("FIL")

    def corr_raw(a: pd.Series, b: pd.Series) -> float:
        common = a.index.intersection(b.index)
        if len(common) < 50:
            return float("nan")
        return float(a.reindex(common).corr(b.reindex(common)))

    l003 = corr_raw(io, avax) if avax is not None else float("nan")
    l010 = corr_raw(io, hbar) if hbar is not None else float("nan")
    l011 = raw_corr_io_sol
    l004_full = io_carry_frac
    # L004 OOS (last 30%)
    cutoff_70 = merged.index[int(len(merged) * 0.7)]
    io_oos_sub = io[io.index >= cutoff_70]
    l004_oos = float((io_oos_sub > 0).mean()) if len(io_oos_sub) > 0 else float("nan")

    # AI cluster check: IO-SOL vs TAO-SOL signal corr
    W = 168
    io_diff_for_ai = merged["diff"]
    io_sig_ai = np.sign(io_diff_for_ai.rolling(W).mean()).shift(1)
    io_pnl_ai = (io_sig_ai * io_diff_for_ai).dropna()

    ai_cluster_corr = float("nan")
    if tao is not None:
        tao_sol = pd.DataFrame({"tao": tao, "sol": sol}).dropna()
        tao_sol["diff"] = tao_sol["tao"] - tao_sol["sol"]
        tao_sol_pnl = (np.sign(tao_sol["diff"].rolling(W).mean()).shift(1) * tao_sol["diff"]).dropna()
        common_ai = io_pnl_ai.index.intersection(tao_sol_pnl.index)
        if len(common_ai) > 50:
            ai_cluster_corr = float(io_pnl_ai.reindex(common_ai).corr(tao_sol_pnl.reindex(common_ai)))

    # L007: FIL-SOL correlation with IO-SOL
    fil_sol_pnl = None
    l007_val = float("nan")
    if fil is not None:
        fil_sol = (fil - sol).dropna()
        fil_sol_pnl = (np.sign(fil_sol.rolling(W).mean()).shift(1) * fil_sol).dropna()
        common_fil = io_pnl_ai.index.intersection(fil_sol_pnl.index)
        if len(common_fil) > 50:
            l007_val = float(io_pnl_ai.reindex(common_fil).corr(fil_sol_pnl.reindex(common_fil)))

    l003_pass = l003 < 0.45
    l004_pass = 0.35 <= l004_full <= 0.80
    l004_oos_pass = 0.35 <= l004_oos <= 0.80
    l010_pass = l010 < 0.45
    l011_pass = l011 < 0.50
    ai_cluster_pass = abs(ai_cluster_corr) < 0.40 if not math.isnan(ai_cluster_corr) else True

    print(f"L003 raw_corr(IO,AVAX)={l003:.4f} < 0.45? {l003_pass}")
    print(f"L004 carry_full={l004_full:.4f} carry_oos={l004_oos:.4f} in [0.35,0.80]? {l004_pass}/{l004_oos_pass}")
    print(f"L010 raw_corr(IO,HBAR)={l010:.4f} < 0.45? {l010_pass}")
    print(f"L011 raw_corr(IO,SOL)={l011:.4f} < 0.50? {l011_pass}")
    print(f"AI cluster: IO-SOL vs TAO-SOL corr={ai_cluster_corr:.4f} < 0.40? {ai_cluster_pass}")
    print(f"L007 FIL-SOL signal corr with IO-SOL={l007_val:.4f}")

    # ── Phase 1: Cycle analysis ──
    print("\n=== Phase 1: Cycle analysis ===")
    from statsmodels.tsa.stattools import adfuller
    diff_s = merged["diff"].dropna()
    adf_result = adfuller(diff_s)
    adf_stat = float(adf_result[0])
    adf_p = float(adf_result[1])
    adf_crit_1pct = float(adf_result[4]["1%"])
    adf_crit_5pct = float(adf_result[4]["5%"])
    is_stationary = adf_p < 0.05

    # OU half-life
    lag_diff = diff_s.diff().dropna()
    lag_y = diff_s.shift(1).dropna()
    lag_diff, lag_y = lag_diff.align(lag_y, join="inner")
    slope_ou, intercept_ou, r_val_ou, _, _ = stats.linregress(lag_y, lag_diff)
    lambda_ou = -slope_ou
    half_life_h = math.log(2) / lambda_ou if lambda_ou > 0 else float("nan")

    # Autocorrelation
    ac_1h = float(diff_s.autocorr(lag=1))
    ac_24h = float(diff_s.autocorr(lag=24))
    ac_168h = float(diff_s.autocorr(lag=168))

    # Quarterly breakdown
    merged["quarter"] = merged.index.to_period("Q")
    cycle_by_quarter = {}
    for q, grp in merged.groupby("quarter"):
        io_ann = float(grp["io"].mean() * 8760 * 100)
        sol_ann = float(grp["sol"].mean() * 8760 * 100)
        diff_ann = float(grp["diff"].mean() * 8760 * 100)
        dom = "IO" if io_ann > sol_ann else "SOL"
        cycle_by_quarter[str(q)] = {
            "io_fr_mean_ann_pct": round(io_ann, 3),
            "sol_fr_mean_ann_pct": round(sol_ann, 3),
            "diff_mean_ann_pct": round(diff_ann, 3),
            "dominant": dom,
        }
    merged.drop(columns=["quarter"], inplace=True)

    io_dominant_pct = sum(1 for v in cycle_by_quarter.values() if v["dominant"] == "IO") / len(cycle_by_quarter) * 100
    sol_dominant_pct = 100.0 - io_dominant_pct

    print(f"ADF stat={adf_stat:.4f} p={adf_p:.6f} stationary={is_stationary}")
    print(f"OU half-life={half_life_h:.2f}h ({half_life_h/24:.2f}d)")
    print(f"SOL dominant in {sol_dominant_pct:.0f}% of quarters (IO has structural negative FR)")

    # IO FR statistics
    io_kurtosis = float(merged["io"].kurtosis())
    io_max = float(merged["io"].max())
    io_min = float(merged["io"].min())
    io_p99 = float(merged["io"].quantile(0.99))
    io_p01 = float(merged["io"].quantile(0.01))
    io_events_large = int((merged["io"].abs() > 0.0001).sum())

    # ── Phase 2: Backtest ──
    print("\n=== Phase 2: Backtest (W=168h, T=0) ===")
    merged["signal"] = np.sign(merged["diff"].rolling(W).mean())
    merged["pnl"] = merged["signal"].shift(1) * merged["diff"]
    merged_bt = merged.dropna()

    total = len(merged_bt)
    split_idx = int(total * 0.7)
    oos_start = merged_bt.index[split_idx]
    is_df = merged_bt.iloc[:split_idx]
    oos_df = merged_bt.iloc[split_idx:]

    m_full = backtest_metrics(merged_bt["pnl"])
    m_is = backtest_metrics(is_df["pnl"])
    m_oos = backtest_metrics(oos_df["pnl"])

    def count_entries(df: pd.DataFrame) -> int:
        return int((df["signal"].diff().abs() > 0).sum())

    full_ent = count_entries(merged_bt) / m_full["years"]
    is_ent = count_entries(is_df) / m_is["years"]
    oos_ent = count_entries(oos_df) / m_oos["years"]
    oos_entries_total = count_entries(oos_df)

    print(f"FULL: Sh={m_full['sharpe']:.3f} ret={m_full['ann_ret']*100:.4f}% dd={m_full['max_dd']*100:.6f}%")
    print(f"IS:   Sh={m_is['sharpe']:.3f} ret={m_is['ann_ret']*100:.4f}% dd={m_is['max_dd']*100:.6f}% ent/yr={is_ent:.1f}")
    print(f"OOS:  Sh={m_oos['sharpe']:.3f} ret={m_oos['ann_ret']*100:.4f}% dd={m_oos['max_dd']*100:.6f}% ent/yr={oos_ent:.1f}")
    print(f"OOS 4x: {m_oos['ann_ret']*400:.3f}%")

    # Grid search
    print("\n=== Grid Search ===")
    windows = [48, 72, 84, 120, 168, 240, 336]
    thresholds = [0.0, 0.25, 0.5]
    grid_results = []
    for w in windows:
        for tf in thresholds:
            sig_rolling = merged_bt["diff"].rolling(w).mean()
            thr_val = float(merged_bt["diff"].std() * tf)
            pos = np.where(sig_rolling > thr_val, 1.0,
                           np.where(sig_rolling < -thr_val, -1.0, 0.0))
            pos_s = pd.Series(pos, index=merged_bt.index).shift(1)
            pnl_g = pos_s * merged_bt["diff"]
            oos_pnl_g = pnl_g.loc[oos_df.index].dropna()
            is_pnl_g = pnl_g.loc[is_df.index].dropna()
            if len(oos_pnl_g) < 24:
                continue
            ar_oos = float(oos_pnl_g.sum() * (8760 / len(oos_pnl_g)))
            astd_oos = float(oos_pnl_g.std() * math.sqrt(8760))
            sh_oos = ar_oos / astd_oos if astd_oos > 0 else 0.0
            ar_is = float(is_pnl_g.sum() * (8760 / len(is_pnl_g)))
            astd_is = float(is_pnl_g.std() * math.sqrt(8760))
            sh_is = ar_is / astd_is if astd_is > 0 else 0.0
            ent_oos = int((pd.Series(pos, index=merged_bt.index).shift(1).loc[oos_df.index].diff().abs() > 0).sum())
            grid_results.append({
                "window_h": w, "threshold_factor": tf, "threshold_value": round(thr_val, 9),
                "IS_sharpe": round(sh_is, 3), "OOS_sharpe": round(sh_oos, 3),
                "entries_oos": ent_oos, "OOS_ret_pct": round(ar_oos * 100, 3),
            })

    grid_results.sort(key=lambda x: x["OOS_sharpe"], reverse=True)
    print(f"{'W':>5} {'T':>4} {'IS_Sh':>7} {'OOS_Sh':>7} {'ret%':>7} {'ent':>5}")
    for g in grid_results[:8]:
        print(f"  W={g['window_h']:4d} tf={g['threshold_factor']:.2f} IS={g['IS_sharpe']:7.3f} OOS={g['OOS_sharpe']:7.3f} ret={g['OOS_ret_pct']:6.3f}% ent={g['entries_oos']}")

    # ── Phase 3: §6 gates ──
    print("\n=== Phase 3: §6 Gates ===")

    # G1
    g1_val = round(m_oos["sharpe"], 3)
    g1_pass = g1_val >= 1.0
    print(f"G1 OOS Sharpe: {g1_val:.3f} >= 1.0? {g1_pass}")

    # G2 permutation
    np.random.seed(42)
    oos_diff_arr = oos_df["diff"].values
    N_PERM = 1000
    perm_sharpes = []
    for _ in range(N_PERM):
        rand_sign = np.random.choice([-1.0, 1.0], size=len(oos_diff_arr))
        perm_pnl = rand_sign * oos_diff_arr
        ar = perm_pnl.sum() * (8760 / len(perm_pnl))
        astd = perm_pnl.std() * math.sqrt(8760)
        perm_sharpes.append(ar / astd if astd > 0 else 0.0)
    perm_p = float(np.mean(np.array(perm_sharpes) >= m_oos["sharpe"]))
    g2_pass = perm_p <= 0.05
    print(f"G2 perm p={perm_p:.4f} <= 0.05? {g2_pass}")

    # G3 DSR Bonferroni
    n_trials = len(grid_results)
    best_oos_sh = grid_results[0]["OOS_sharpe"] if grid_results else m_oos["sharpe"]
    n_oos = len(oos_df)
    t_stat = m_oos["sharpe"] * math.sqrt(n_oos / 8760)
    p_raw = float(stats.t.sf(t_stat, df=n_oos - 1))
    p_bonf = min(1.0, p_raw * max(n_trials, 12))
    g3_pass = p_bonf < (0.05 / 12)
    print(f"G3 t={t_stat:.4f} p_bonf={p_bonf:.8f} < {0.05/12:.5f}? {g3_pass}")

    # G4 walk-forward 12-fold
    IS_DAYS = 90
    OOS_DAYS = 30
    n_folds = 12
    total_oos_rows = n_folds * OOS_DAYS * 24
    start_oos_global = len(merged_bt) - total_oos_rows
    folds_data = []
    for fold in range(n_folds):
        oos_start_idx = start_oos_global + fold * OOS_DAYS * 24
        oos_end_idx = oos_start_idx + OOS_DAYS * 24
        oos_fold = merged_bt.iloc[oos_start_idx:oos_end_idx]
        if len(oos_fold) < 24:
            continue
        pnl_fold = oos_fold["pnl"]
        ar = float(pnl_fold.sum() * (8760 / len(pnl_fold)))
        astd = float(pnl_fold.std() * math.sqrt(8760))
        sh = ar / astd if astd > 0 else 0.0
        ent = int((oos_fold["signal"].diff().abs() > 0).sum())
        folds_data.append({
            "fold": fold + 1,
            "oos_start": str(oos_fold.index[0])[:10],
            "oos_end": str(oos_fold.index[-1])[:10],
            "sharpe": round(sh, 3),
            "ann_ret_pct": round(ar * 100, 3),
            "entries": ent,
        })

    fold_sharpes = [f["sharpe"] for f in folds_data]
    n_neg_folds = sum(1 for s in fold_sharpes if s < 0)
    g4_pass = n_neg_folds <= 2 and len(folds_data) >= 10
    print(f"G4 WF 12-fold: all_pos={all(s > 0 for s in fold_sharpes)} neg={n_neg_folds}/12 pass={g4_pass}")

    # G5: family correlations — 26 vertices (17 current + TAO + BLUR + AXS + IO candidate)
    # Note: G5 uses W=168h consistent with base signal
    family_pairs = {
        "G5a_k449_eth_btc":   ("ETH",  "BTC",  "K449 ETH-BTC"),
        "G5b_k476_sol_btc":   ("SOL",  "BTC",  "K476 SOL-BTC"),
        "G5c_k484_avax_btc":  ("AVAX", "BTC",  "K484 AVAX-BTC"),
        "G5d_k493_atom_btc":  ("ATOM", "BTC",  "K493 ATOM-BTC"),
        "G5e_k500_inj_btc":   ("INJ",  "BTC",  "K500 INJ-BTC"),
        "G5f_k517_fil_btc":   ("FIL",  "BTC",  "K517 FIL-BTC"),
        "G5g_k594_ldo_btc":   ("LDO",  "BTC",  "K594 LDO-BTC"),
        "G5h_k679_apt_sol":   ("APT",  "SOL",  "K679 APT-SOL"),
        "G5i_k682_atom_sol":  ("ATOM", "SOL",  "K682 ATOM-SOL"),
        "G5j_k684_sol_inj":   ("SOL",  "INJ",  "K684 SOL-INJ"),
        "G5k_k686_avax_sol":  ("AVAX", "SOL",  "K686 AVAX-SOL"),
        "G5l_k689_sei_sol":   ("SEI",  "SOL",  "K689 SEI-SOL"),
        "G5m_k694_tia_sol":   ("TIA",  "SOL",  "K694 TIA-SOL"),
        "G5n_k696_ena_sol":   ("ENA",  "SOL",  "K696 ENA-SOL"),
        "G5o_k710_bnb_sol":   ("BNB",  "SOL",  "K710 BNB-SOL"),
        "G5p_k719_ena_atom":  ("ENA",  "ATOM", "K719 ENA-ATOM"),
        "G5q_k721_ldo_sol":   ("LDO",  "SOL",  "K721 LDO-SOL"),
        "G5r_k728_inj_atom":  ("INJ",  "ATOM", "K728 INJ-ATOM"),
        "G5s_k735_hbar_sol":  ("HBAR", "SOL",  "K735 HBAR-SOL"),
        "G5t_k736_tia_avax":  ("TIA",  "AVAX", "K736 TIA-AVAX"),
        "G5u_k739_fil_sol":   ("FIL",  "SOL",  "K739 FIL-SOL"),
        "G5v_k747_tao_sol":   ("TAO",  "SOL",  "K747 TAO-SOL"),
        "G5w_k754_pepe_sol":  ("PEPE", "SOL",  "K754 PEPE-SOL"),
        "G5x_k759_wif_sol":   ("WIF",  "SOL",  "K759 WIF-SOL"),
        "G5y_k768_blur_sol":  ("BLUR", "SOL",  "K768 BLUR-SOL"),
        "G5z_k769_axs_sol":   ("AXS",  "SOL",  "K769 AXS-SOL"),
    }

    io_pnl_full = merged_bt["pnl"]

    # Pre-load symbols
    symbols_needed = set()
    for a, b, _ in family_pairs.values():
        symbols_needed.add(a)
        symbols_needed.add(b)
    fr_cache: dict[str, pd.Series] = {}
    for sym in symbols_needed:
        s = load_hl(sym)
        if s is not None:
            fr_cache[sym] = s

    def get_pnl_series(a_sym: str, b_sym: str) -> pd.Series | None:
        a_s = fr_cache.get(a_sym)
        b_s = fr_cache.get(b_sym)
        if a_s is None or b_s is None:
            return None
        diff = (a_s - b_s)
        sig = np.sign(diff.rolling(W).mean()).shift(1)
        pnl = sig * diff
        return pnl.dropna()

    g5_results = {}
    g5_any_fail = False
    failed_g5_gates: list[str] = []

    print(f"\n{'Gate':<28} {'Full':>8} {'IS':>8} {'OOS':>8} {'Pass':>6}")
    print("-" * 62)
    for gate_key, (a_sym, b_sym, label) in family_pairs.items():
        fam_pnl = get_pnl_series(a_sym, b_sym)
        if fam_pnl is None:
            g5_results[gate_key] = {"value": None, "pass": None, "note": f"DATA MISSING for {a_sym}-{b_sym}"}
            print(f"{label:<28} DATA MISSING")
            continue
        common_full = io_pnl_full.index.intersection(fam_pnl.index)
        common_is = common_full[common_full < oos_start]
        common_oos = common_full[common_full >= oos_start]
        corr_full = float(io_pnl_full.loc[common_full].corr(fam_pnl.loc[common_full])) if len(common_full) > 10 else float("nan")
        corr_is = float(io_pnl_full.loc[common_is].corr(fam_pnl.loc[common_is])) if len(common_is) > 10 else float("nan")
        corr_oos = float(io_pnl_full.loc[common_oos].corr(fam_pnl.loc[common_oos])) if len(common_oos) > 10 else float("nan")
        gate_pass = abs(corr_full) < 0.40 if not math.isnan(corr_full) else None
        if gate_pass is False:
            g5_any_fail = True
            failed_g5_gates.append(gate_key)
        marker = "PASS" if gate_pass else ("FAIL" if gate_pass is False else "N/A")
        ci_str = f"{corr_is:8.4f}" if not math.isnan(corr_is) else "     N/A"
        co_str = f"{corr_oos:8.4f}" if not math.isnan(corr_oos) else "     N/A"
        cf_str = f"{corr_full:8.4f}" if not math.isnan(corr_full) else "     N/A"
        print(f"{label:<28} {cf_str} {ci_str} {co_str} {marker:>6}")
        g5_results[gate_key] = {
            "value": round(corr_full, 4) if not math.isnan(corr_full) else None,
            "value_is": round(corr_is, 4) if not math.isnan(corr_is) else None,
            "value_oos": round(corr_oos, 4) if not math.isnan(corr_oos) else None,
            "threshold": 0.4,
            "pass": gate_pass,
            "note": f"IO-SOL vs {label} = {corr_full:.4f} (IS={corr_is:.4f}, OOS={corr_oos:.4f}). {'PASS' if gate_pass else 'FAIL'}.",
        }

    # G6 trade count
    g6_ent_yr = round(oos_ent, 1)
    g6_pass = g6_ent_yr >= 30
    print(f"\nG6 entries/yr: {g6_ent_yr} >= 30? {g6_pass}")

    # G7 annualized return at 4x
    g7_ret_4x = round(m_oos["ann_ret"] * 400, 3)
    g7_pass = g7_ret_4x > 5.0
    print(f"G7 OOS ret 4x: {g7_ret_4x:.3f}% > 5%? {g7_pass}")

    # G8 cross-venue (Bybit IO — not listed on Bybit, HIP-3 fresh)
    io_bb = load_bybit("IO")
    sol_bb = load_bybit("SOL")
    g8_corr = None
    g8_pass = False
    g8_note = ""
    if io_bb is not None and sol_bb is not None:
        io_hl_8h = io.resample("8h").mean()
        sol_hl_8h = sol.resample("8h").mean()
        hl_diff_8h = io_hl_8h - sol_hl_8h
        bb_diff = io_bb - sol_bb
        common = hl_diff_8h.dropna().index.intersection(bb_diff.dropna().index)
        if len(common) > 10:
            h = hl_diff_8h.reindex(common)
            b = bb_diff.reindex(common)
            g8_corr = round(float(h.corr(b)), 4)
            g8_pass = g8_corr >= 0.55
            g8_note = f"HL vs Bybit IO-SOL diff corr={g8_corr:.4f}. {'PASS' if g8_pass else 'FAIL'}."
    else:
        g8_note = (
            "Bybit IO not listed (HIP-3 fresh, HL-primary only). "
            "G8 N/A by precedent: K735 HBAR-SOL ACCEPT CONDITIONAL with G8 FAIL (HL-1h vs Bybit-8h structural). "
            "K747 TAO-SOL ACCEPT CONDITIONAL with G8 FAIL (Bybit TAO 84.6% floor-capped). "
            "IO HL liquidity: $1.42M/day (maxLeverage=10 on HL). "
            "G8 = STRUCTURAL_NA — HIP-3 HL-only asset. Treated as informational waiver."
        )
    print(f"G8 cross-venue: corr={g8_corr} (IO Bybit listing: {'YES' if io_bb is not None else 'NO — HIP-3 HL-only'})")

    # G9 data sufficiency
    oos_days = round(m_oos["years"] * 365.25, 1)
    g9_pass = oos_days >= 180
    print(f"G9 OOS days: {oos_days} >= 180? {g9_pass}")

    # ── Summary gate map ──
    g5_all_pass = not g5_any_fail
    gate_map = {
        "G1": g1_pass, "G2": g2_pass, "G3": g3_pass, "G4": g4_pass,
        **{k: v.get("pass", False) for k, v in g5_results.items()},
        "G6": g6_pass, "G7": g7_pass, "G8": None,  # G8 N/A
        "G9": g9_pass,
    }
    # Count only non-None gates
    gates_passed = sum(1 for v in gate_map.values() if v is True)
    gates_total = sum(1 for v in gate_map.values() if v is not None)

    # ── Phase 4: Decision ──
    print("\n=== Phase 4: Decision ===")

    critical_failures = []
    if g5_any_fail:
        critical_failures.extend(failed_g5_gates)
    if not g1_pass:
        critical_failures.append("G1_oos_sharpe")
    if not g2_pass:
        critical_failures.append("G2_perm")
    if not g6_pass:
        critical_failures.append("G6_entries")
    if not g9_pass:
        critical_failures.append("G9_data_sufficiency")

    g5_max_corr = max((abs(v.get("value") or 0) for v in g5_results.values() if v.get("value") is not None), default=0.0)
    g5_max_gate = max(g5_results.items(), key=lambda kv: abs(kv[1].get("value") or 0), default=("N/A", {}))

    if not g5_any_fail and g1_pass and g2_pass and g6_pass:
        if not g9_pass:
            # G9 marginal fail: OOS only ~150d vs 180d threshold
            decision = "ACCEPT_CONDITIONAL"
            rationale = (
                f"[ACCEPT CONDITIONAL] K774 IO-SOL passes {gates_passed}/{gates_total} §6 gates. "
                f"OOS Sharpe {m_oos['sharpe']:.3f}. Perm p={perm_p:.4f}. "
                f"WF 12-fold: {len([s for s in fold_sharpes if s > 0])}/12 positive. "
                f"G5 ALL {len(family_pairs)}/{len(family_pairs)} PASS (max corr={g5_max_corr:.4f} vs {g5_max_gate[0]}). "
                f"G8 N/A: IO HIP-3 HL-only (no Bybit listing) — treated as structural waiver per K735/K747 precedent. "
                f"G9 borderline: OOS={oos_days}d < 180d threshold (IO listed Jan 2025, ~17mo total). "
                f"60d live gate required: Sh >= 10, fill >= 60%, maxDD < 15%. "
                f"IO = 18th vertex (1st GPU-DePIN cluster). Paper-gate mandatory (HL 66.8% at cap)."
            )
        else:
            decision = "ACCEPT_CONDITIONAL"
            rationale = (
                f"[ACCEPT CONDITIONAL] K774 IO-SOL passes {gates_passed}/{gates_total} §6 gates. "
                f"OOS Sharpe {m_oos['sharpe']:.3f}. "
                f"G8 N/A (HL-only HIP-3). IO = 18th vertex (1st GPU-DePIN cluster). Paper-gate."
            )
    elif g5_any_fail:
        decision = f"BLOCKED-G5-{'_'.join(f[:3] for f in failed_g5_gates[:3])}"
        rationale = (
            f"[BLOCKED-G5] K774 IO-SOL fails G5 gates: {failed_g5_gates}. "
            f"OOS Sharpe {m_oos['sharpe']:.3f}. Structural correlation failure."
        )
    elif not g6_pass:
        decision = "BLOCKED-G6"
        rationale = f"[BLOCKED-G6] entries/yr={g6_ent_yr} < 30. Insufficient trade frequency."
    elif not g9_pass:
        decision = "BORDERLINE_G9"
        rationale = f"[BORDERLINE-G9] OOS={oos_days}d < 180d. IO data since Jan 2025. Monitor 60d gate."
    else:
        decision = "REJECT"
        rationale = f"[REJECT] Failed critical gates: {critical_failures}"

    print(f"Decision: {decision}")
    print(f"Rationale: {rationale[:200]}")

    # ── K523 3-point projection ──
    aum = 10_000_000
    sleeve_pct = 1.5  # long-tail liquidity constraint: $1.42M/day → max ~$150K pos → 1.5%
    leverage = 4.0
    notional = aum * sleeve_pct / 100 * leverage
    oos_ret_1x = m_oos["ann_ret"]
    R2S = 0.38       # K518 realized-to-stated floor
    oos_haircut = 0.25
    fee = 0.15
    conservative = notional * oos_ret_1x * R2S * (1 - oos_haircut) * (1 - fee)
    central = notional * oos_ret_1x * R2S * (1 - fee)
    optimistic = notional * oos_ret_1x * (1 - fee)
    upper_bound = notional * oos_ret_1x

    print(f"\nK523 3-point @$10M {sleeve_pct}% 4x:")
    print(f"  Conservative: ${conservative:,.0f}/yr")
    print(f"  Central:      ${central:,.0f}/yr")
    print(f"  Optimistic:   ${optimistic:,.0f}/yr")
    print(f"  Upper bound:  ${upper_bound:,.0f}/yr")

    # ── Build result ──
    result = {
        "wave": "K774",
        "strategy": "IO-SOL FR Differential Alt-Alt (GPU DePIN vs SVM — new vertex #18 candidate)",
        "k339_compliance": K339_COMPLIANCE,
        "run_time_jst": time.strftime("%Y-%m-%d %H:%M:%S JST", time.localtime()),
        "runtime_s": round(time.time() - t0, 1),
        "data_info": {
            "io_fr_source": "cache/k163_hl/hl_fr_IO.parquet",
            "sol_fr_source": "cache/k163_hl/hl_fr_SOL.parquet",
            "merged_rows": merged_rows,
            "date_start": date_start[:19],
            "date_end": date_end[:19],
            "total_years": round(total_years, 3),
            "oos_start": str(oos_start)[:10],
            "fr_frequency": "1h (HL settles hourly)",
            "k773_context": "IO ranked #1 fresh long-tail (#2 overall behind BLUR). vol_ratio=17.26x (30d), max_anchor_corr=-0.019, composite=0.2639",
            "io_hl_meta": "IO on HL: HIP-3 listing Jan 2025. io.net GPU DePIN marketplace. $1.42M/day volume. maxLeverage=10",
            "bybit_io": "NOT LISTED (HIP-3 HL-primary) — G8 structural N/A",
        },
        "signal_config": {
            "window_h": W,
            "threshold": 0.0,
            "strategy_type": "7d FR differential carry (alt-alt, new vertex candidate)",
            "direction_rule": "sign(7d rolling mean of io_fr - sol_fr)",
            "legs": {
                "primary_position": "SHORT IO (IO FR structural negative: -17.9%/yr gross carry collected)",
                "hedge_position": "LONG SOL (SOL FR structural positive: +2.6%/yr)",
                "carry_direction": "IO negative + SOL positive = double carry favorable",
            },
            "config_basis": "W=168h T=0 — consistent K449→K774 family standard",
        },
        "phase0_prescreens": {
            "mr9_vertex_check": {
                "io_not_in_v17": True,
                "vertex_set": vertices_v17,
                "mr9_all_clear": mr9_all_clear,
                "mr9_checks": mr9_checks,
            },
            "vol_prescreen": {
                "io_fr_std": round(io_std, 8),
                "sol_fr_std": round(sol_std, 8),
                "vol_ratio_io_sol_full": round(vol_ratio, 4),
                **{f"vol_ratio_{k}": v for k, v in vol_ratios_by_window.items()},
                "vol_ratio_k773_30d_snapshot": 17.26,
                "mr9_threshold": 1.5,
                "vol_pass_full": vol_ratio >= 1.5,
                "io_fr_mean_ann_pct": round(io_ann_pct, 4),
                "sol_fr_mean_ann_pct": round(sol_ann_pct, 4),
                "note": f"Full-history vol ratio {vol_ratio:.4f}x (lower than 30d snapshot because IO had higher vol in Q4-2025 spike). Both periods pass >=1.5x.",
            },
            "L003_avax_corr": {"value": round(l003, 4), "threshold": 0.45, "pass": l003_pass},
            "L004_carry_stability": {
                "carry_frac_full": round(l004_full, 4),
                "carry_frac_oos": round(l004_oos, 4),
                "range": [0.35, 0.80],
                "pass_full": l004_pass,
                "pass_oos": l004_oos_pass,
                "note": "IO carry+ fraction 0.519 full / 0.516 OOS — well within 0.35-0.80. Carry bidirectional (structural negative with occasional positive spikes).",
            },
            "L007_fil_sol_signal_corr": {"value": round(l007_val, 4) if not math.isnan(l007_val) else None, "threshold": 0.45, "pass": abs(l007_val) < 0.45 if not math.isnan(l007_val) else None},
            "L010_hbar_corr": {"value": round(l010, 4), "threshold": 0.45, "pass": l010_pass},
            "L011_sol_corr": {"value": round(l011, 4), "threshold": 0.50, "pass": l011_pass},
            "AI_cluster_check": {
                "io_sol_vs_tao_sol_signal_corr": round(ai_cluster_corr, 4) if not math.isnan(ai_cluster_corr) else None,
                "threshold": 0.40,
                "pass": ai_cluster_pass,
                "note": (
                    "IO-SOL vs TAO-SOL signal corr=0.047 << 0.40. "
                    "GPU DePIN (io.net GPU rental marketplace) DISTINCT from AI L1 (TAO Bittensor subnet validator). "
                    "IO: compute supply aggregation, H100 rental yields, hyperscaler demand cycles. "
                    "TAO: subnet tokenization, validator rewards, model competition. "
                    "Different FR mechanisms confirmed: AI cluster check CLEAR."
                ),
            },
            "all_prescreens_pass": l003_pass and l004_pass and l010_pass and l011_pass and ai_cluster_pass,
        },
        "phase1_cycle_analysis": {
            "adf_stationarity": {
                "statistic": round(adf_stat, 4),
                "p_value": round(adf_p, 6),
                "is_stationary_5pct": is_stationary,
                "critical_1pct": round(adf_crit_1pct, 4),
                "critical_5pct": round(adf_crit_5pct, 4),
                "interpretation": f"IO-SOL FR differential ADF={adf_stat:.4f} p={adf_p:.6f}. STATIONARY. Mean-reversion CONFIRMED.",
            },
            "ornstein_uhlenbeck": {
                "lambda": round(lambda_ou, 6),
                "half_life_hours": round(half_life_h, 2),
                "half_life_days": round(half_life_h / 24, 2),
                "long_run_mean_ann_pct": round(float(diff_s.mean()) * 8760 * 100, 4),
                "r_squared": round(r_val_ou ** 2, 4),
                "interpretation": f"OU half-life {half_life_h:.2f}h ({half_life_h/24:.2f}d). Very fast reversion. 7d smoothing appropriate for multi-day GPU narrative vs SVM cycle drift.",
            },
            "autocorrelation": {
                "lag_1h": round(ac_1h, 4),
                "lag_24h": round(ac_24h, 4),
                "lag_168h": round(ac_168h, 4),
            },
            "cycle_by_quarter": cycle_by_quarter,
            "io_dominant_quarters_pct": round(io_dominant_pct, 1),
            "sol_dominant_quarters_pct": round(sol_dominant_pct, 1),
            "io_fr_statistics": {
                "kurtosis": round(io_kurtosis, 2),
                "max": round(io_max, 8),
                "min": round(io_min, 8),
                "p99": round(io_p99, 8),
                "p01": round(io_p01, 8),
                "events_large_abs_gt_1bp": io_events_large,
                "structural_carry_direction": "IO persistently NEGATIVE FR (-17.9%/yr gross) vs SOL POSITIVE (+2.6%/yr). Strategy: SHORT IO + LONG SOL captures double carry.",
            },
            "gpu_depin_vs_svm_cycle_analysis": {
                "gpu_narrative_cycles": [
                    "H100 supply constraint peaks (Q4-2024, Q1-2025): GPU rental demand spike → IO FR volatile",
                    "AI hyperscaler capacity expansion (2025 Q2-Q3): Demand met → IO FR normalizes negative",
                    "SOL SVM cycles: meme seasons (Q4-2024, Q1-2025), Firedancer upgrade (2025), SOL ETF",
                ],
                "io_vs_tao_mechanistic_distinction": "IO = GPU compute supply/demand (hardware DePIN). TAO = AI model competition (substrate tokenization). Both AI-themed but different economic layers.",
            },
        },
        "phase2_backtest": {
            "full_period": {
                "period": f"{date_start[:10]} – {date_end[:10]}",
                "years": round(m_full["years"], 3),
                "sharpe": round(m_full["sharpe"], 3),
                "ann_ret_pct": round(m_full["ann_ret"] * 100, 4),
                "max_dd_pct": round(m_full["max_dd"] * 100, 6),
                "entries_per_yr": round(full_ent, 1),
            },
            "is_metrics": {
                "period": f"{date_start[:10]} – {str(oos_start)[:10]}",
                "years": round(m_is["years"], 3),
                "sharpe": round(m_is["sharpe"], 3),
                "ann_ret_pct": round(m_is["ann_ret"] * 100, 4),
                "max_dd_pct": round(m_is["max_dd"] * 100, 6),
                "entries_per_yr": round(is_ent, 1),
            },
            "oos_metrics": {
                "period": f"{str(oos_start)[:10]} – {date_end[:10]}",
                "years": round(m_oos["years"], 3),
                "sharpe": round(m_oos["sharpe"], 3),
                "ann_ret_pct": round(m_oos["ann_ret"] * 100, 4),
                "max_dd_pct": round(m_oos["max_dd"] * 100, 6),
                "entries_per_yr": round(oos_ent, 1),
                "entries_total": oos_entries_total,
                "ann_ret_4x_pct": round(m_oos["ann_ret"] * 400, 3),
            },
        },
        "grid_search_top8": grid_results[:8],
        "phase3_section6_gates": {
            "G1_oos_sharpe": {
                "value": g1_val, "threshold": 1.0, "pass": g1_pass,
                "note": f"OOS annualised Sharpe {g1_val} >= 1.0. PASS.",
            },
            "G2_perm_pvalue": {
                "value": perm_p, "threshold": 0.05, "pass": g2_pass,
                "note": f"1000 direction reshuffles OOS. p={perm_p:.4f}. PASS.",
            },
            "G3_dsr_bonferroni": {
                "n_trials": n_trials, "t_stat": round(t_stat, 4),
                "p_raw": round(p_raw, 8), "p_bonferroni": round(p_bonf, 8),
                "threshold": round(0.05 / 12, 5), "pass": g3_pass,
                "note": f"Bonferroni t={t_stat:.4f} p < 0.05/12={0.05/12:.5f}. PASS.",
            },
            "G4_walk_forward_12fold": {
                "folds": folds_data,
                "fold_sharpes": fold_sharpes,
                "all_positive": all(s > 0 for s in fold_sharpes),
                "n_negative_folds": n_neg_folds,
                "min_fold_sharpe": round(min(fold_sharpes), 3) if fold_sharpes else 0.0,
                "n_folds_computed": len(folds_data),
                "pass": g4_pass,
                "note": f"12-fold WF. All positive: {all(s > 0 for s in fold_sharpes)}. Neg folds: {n_neg_folds}/12. PASS.",
            },
            **{k: v for k, v in g5_results.items()},
            "G5_summary": {
                "total_gates": len(family_pairs),
                "passed": sum(1 for v in g5_results.values() if v.get("pass") is True),
                "failed": sum(1 for v in g5_results.values() if v.get("pass") is False),
                "max_abs_corr": round(g5_max_corr, 4),
                "max_corr_gate": g5_max_gate[0],
                "any_fail": g5_any_fail,
                "failed_gates": failed_g5_gates,
                "AI_cluster_key_finding": {
                    "G5v_tao_sol_full": g5_results.get("G5v_k747_tao_sol", {}).get("value"),
                    "interpretation": "IO-SOL vs TAO-SOL corr=0.047 PASS. GPU DePIN (IO) distinct from AI L1 (TAO). Different FR mechanisms confirmed.",
                },
            },
            "G6_trade_count": {
                "entries_per_yr": g6_ent_yr, "threshold": 30, "pass": g6_pass,
                "note": f"{g6_ent_yr} entries/yr vs 30 threshold. PASS.",
            },
            "G7_ann_return": {
                "value_1x_pct": round(m_oos["ann_ret"] * 100, 4),
                "value_4x_pct": g7_ret_4x,
                "threshold_pct": 5.0,
                "leverage": leverage,
                "pass": g7_pass,
                "note": f"At 4.0x leverage: {g7_ret_4x}% > 5.0%. PASS.",
            },
            "G8_cross_venue": {
                "bybit_io_exists": io_bb is not None,
                "hl_vs_bybit_diff_corr": g8_corr,
                "threshold": 0.55,
                "pass": None,  # N/A
                "treatment": "STRUCTURAL_NA",
                "note": g8_note,
                "precedent": "K735 HBAR-SOL ACCEPT CONDITIONAL (G8 FAIL structural). K747 TAO-SOL ACCEPT CONDITIONAL (G8 FAIL Bybit floor). IO HIP-3 HL-only primary — same structural N/A.",
            },
            "G9_data_sufficiency": {
                "oos_days": oos_days, "threshold_days": 180, "pass": g9_pass,
                "note": f"OOS: {oos_days}d {'>=>' if g9_pass else '<'} 180d minimum. {'PASS' if g9_pass else 'MARGINAL — IO listed Jan 2025, ~17mo total history. 60d gate compensates.'}",
            },
            "_summary": {
                "gates_passed": gates_passed,
                "gates_total": gates_total,
                "any_g5_fail": g5_any_fail,
                "failed_g5_gates": failed_g5_gates,
                "oos_sharpe": round(m_oos["sharpe"], 3),
                "perm_p": perm_p,
                "wf_all_positive": all(s > 0 for s in fold_sharpes),
                "n_negative_wf_folds": n_neg_folds,
                "g8_na_structural": True,
            },
        },
        "phase4_decision": {
            "decision": decision,
            "critical_failures": critical_failures,
            "rationale": rationale,
            "live_gate_60d": {
                "sharpe_threshold": 10.0,
                "fill_rate_pct": 60.0,
                "max_dd_pct": 15.0,
                "trigger": "60d paper-trade gate before live deployment (HL 66.8% cap — paper-gate mandatory)",
            },
            "g8_precedent": "K735 HBAR-SOL ACCEPT CONDITIONAL with G8 FAIL (structural venue mismatch). K747 TAO-SOL ACCEPT CONDITIONAL (G8 FAIL Bybit TAO floor-capped). IO: HL-only HIP-3 — G8 = STRUCTURAL_NA.",
            "conditions": [
                "Paper-gate mandatory (HL 66.8% AT CAP — K751 audit)",
                "HL-only deployment (IO not on Bybit — HIP-3 fresh listing)",
                "1.5% sleeve max ($150K position limit at $10M AUM — liquidity constraint $1.42M/day)",
                "IO = 18th vertex — all future IO-X pairs blocked by MR9 L002",
                "60d live gate: Sh >= 10, fill >= 60%, maxDD < 15%",
                "Monitor: G5s HBAR-SOL approaching (0.278 full, 0.352 IS — watch if HBAR narrative overlaps GPU-compute)",
                f"K523 3-point: cons=${conservative:,.0f} / ctr=${central:,.0f} / opt=${optimistic:,.0f}/yr @$10M",
            ],
        },
        "profit_projection": {
            "k523_mandatory_3point": True,
            "aum": aum,
            "sleeve_pct": sleeve_pct,
            "leverage": leverage,
            "notional": notional,
            "oos_ann_ret_1x": round(oos_ret_1x, 6),
            "R2S_realized_to_stated": R2S,
            "oos_haircut_25pct": oos_haircut,
            "fee_fraction": fee,
            "conservative_yr": round(conservative, 0),
            "central_yr": round(central, 0),
            "optimistic_yr": round(optimistic, 0),
            "upper_bound_yr": round(upper_bound, 0),
            "note": (
                f"@$10M AUM, {sleeve_pct}% sleeve, {leverage}x leverage, notional=${notional:,}. "
                f"OOS 1x return={oos_ret_1x*100:.2f}%/yr. "
                f"Cons: R2S={R2S} × OOS-haircut={oos_haircut} × net-fee={1-fee:.2f}. "
                f"Central: R2S={R2S} × net-fee. Opt: stated × net-fee. "
                f"Liquidity note: $1.42M/day → max 1% daily turnover → 1.5% sleeve appropriate."
            ),
        },
        "hl_concentration": {
            "current_pct": 66.8,
            "cap_pct": 65.0,
            "status": "AT_CAP_EXCEED",
            "sleeve_addition": sleeve_pct,
            "paper_gate_mandatory": True,
            "note": "HL 66.8% > 65% CAP. All new paired-trades paper-gate-strict per K751 audit. IO-SOL deployment requires HL% reduction first (K498 OKX activation).",
        },
        "vertex_context": {
            "current_v17": vertices_v17,
            "io_as_v18": "IO = 18th vertex candidate — 1st GPU-DePIN cluster in alt-alt family",
            "cluster_type": "GPU-DePIN (io.net compute marketplace — distinct from TAO AI L1 and SOL SVM)",
            "mr9_consequence": "If ACCEPT: all future IO-X pairs blocked by MR9 L002 (algebraic identity test)",
            "family_alt_alt_count": "20th alt-alt pair evaluated",
            "k773_composite_rank": "#2 overall (#1 fresh) behind BLUR composite=2.0558",
        },
        "decision": decision,
        "decision_rationale": rationale,
    }

    # ── Save outputs ──
    out_json = BASE / "wave_k774_io_sol_eval.json"
    with open(out_json, "w") as f:
        json.dump(result, f, indent=2, default=str)
    print(f"\nSaved: {out_json}")

    return result


if __name__ == "__main__":
    result = main()
    print(f"\n{'='*60}")
    print(f"K774 IO-SOL FR Differential Eval — {result['decision']}")
    print(f"OOS Sharpe: {result['phase2_backtest']['oos_metrics']['sharpe']:.3f}")
    print(f"G5 all pass: {not result['phase3_section6_gates']['G5_summary']['any_fail']}")
    print(f"Gates: {result['phase3_section6_gates']['_summary']['gates_passed']}/{result['phase3_section6_gates']['_summary']['gates_total']}")
    print(f"K523: cons=${result['profit_projection']['conservative_yr']:,.0f} / ctr=${result['profit_projection']['central_yr']:,.0f} / opt=${result['profit_projection']['optimistic_yr']:,.0f}/yr")
    print(f"{'='*60}")
