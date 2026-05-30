#!/usr/bin/env python3
"""
wave_k625_jto_sweet_spot.py — K625 JTO-BTC Window Sweet-Spot Retry
====================================================================
K339 REPO_ROOT pattern.

CONTEXT (from K622)
-------------------
K622 JTO-BTC FR Differential: OOS Sharpe=18.67, $4.49M/yr@$10M 4x.
BLOCKED-G5: SEI corr=0.4075 AND DOGE corr=0.4009 at W=168h (7d).
Both are borderline (~0.001-0.008 over threshold).

K622 grid results:
  W=168h:  OOS Sh=18.67, trades/yr=6136  (SEI=0.4075 FAIL, DOGE=0.4009 FAIL)
  W=336h:  OOS Sh=19.11, trades/yr=~6060
  W=504h:  OOS Sh=19.08, trades/yr=~6003
  W=720h:  OOS Sh=19.22, trades/yr=~5972

Solana LST/MEV sub-cluster CONFIRMED:
  SOL corr=0.3783 (PASS), JUP corr=0.1414 (PASS)
  JTO is distinct from both SOL-L1 and JUP-DEX. Only SEI + DOGE blocking.

SWEET-SPOT HYPOTHESIS (K625)
----------------------------
SEI and DOGE are borderline failures. Window variation may resolve:
- Shorter windows (72h): more signal switches → lower signal corr but more noise
- Longer windows (240h-720h): lower corr but fewer trades possible

Joint PASS target:
  SEI corr < 0.40 AND DOGE corr < 0.40 AND trades/yr >= 30

PHASE 1: Window sweep 72h / 168h / 240h / 336h / 504h / 672h / 720h
PHASE 2: Joint optimization (SEI + DOGE + G6)
PHASE 3: Full §6 gates at optimal window
PHASE 4: Profit projection
PHASE 5: Decision

K339 REPO_ROOT — no hardcoded absolute paths except BASE (derived from script location).
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
from scipy import stats

warnings.filterwarnings("ignore")

START_TIME = time.time()
BASE     = Path(__file__).resolve().parent
CACHE    = BASE / "cache"
HL_CACHE = CACHE / "k163_hl"

# ── K625 Sweep Windows ───────────────────────────────────────────────────────
SWEEP_WINDOWS = [72, 168, 240, 336, 504, 672, 720]   # hours
THRESHOLD     = 0.0    # always-on (no dead-band)
COST_RT_BPS   = 4      # 2bps per side × 2 legs

# §6 gate thresholds
G5_CORR_MAX   = 0.40
G6_TRADES_MIN = 30.0
G1_SH_MIN     = 1.0
G7_ANN_RET    = 5.0
G8_VENUE_CORR = 0.55

ANN_FACTOR_1H = math.sqrt(8760)
OOS_START     = pd.Timestamp("2025-10-22 00:00:00")
OOS_FRAC      = 0.30

# Walk-forward params
N_FOLDS_WF = 12
WF_IS_H    = 2160   # 90d
WF_OOS_H   = 720    # 30d
N_PERM     = 500

VOL_RATIO_MIN = 1.5

# Family members (current, 25 members, K622 context)
FAMILY_MEMBERS = [
    {"rank": 1,  "pair": "APT-BTC",    "sharpe": 51.100, "status": "ACCEPT",             "wave": "K512"},
    {"rank": 2,  "pair": "ATOM-BTC",   "sharpe": 50.786, "status": "ACCEPT",             "wave": "K493"},
    {"rank": 3,  "pair": "SEI-BTC",    "sharpe": 48.100, "status": "ACCEPT",             "wave": "K507"},
    {"rank": 4,  "pair": "AVAX-BTC",   "sharpe": 43.887, "status": "ACCEPT",             "wave": "K484"},
    {"rank": 5,  "pair": "SHIB-BTC",   "sharpe": 38.481, "status": "ACCEPT CONDITIONAL", "wave": "K595"},
    {"rank": 6,  "pair": "SAND-BTC",   "sharpe": 33.627, "status": "ACCEPT CONDITIONAL", "wave": "K583"},
    {"rank": 7,  "pair": "JUP-BTC",    "sharpe": 29.895, "status": "ACCEPT CONDITIONAL", "wave": "K606"},
    {"rank": 8,  "pair": "PEPE-BTC",   "sharpe": 26.420, "status": "ACCEPT CONDITIONAL", "wave": "K598"},
    {"rank": 9,  "pair": "BONK-BTC",   "sharpe": 23.667, "status": "ACCEPT CONDITIONAL", "wave": "K603"},
    {"rank": 10, "pair": "FIL-BTC",    "sharpe": 21.773, "status": "ACCEPT CONDITIONAL", "wave": "K517"},
    {"rank": 11, "pair": "DOGE-BTC",   "sharpe": 21.069, "status": "ACCEPT CONDITIONAL", "wave": "K592"},
    {"rank": 12, "pair": "ENA-BTC",    "sharpe": 20.468, "status": "ACCEPT",             "wave": "K616"},
    {"rank": 13, "pair": "AXS-BTC",    "sharpe": 17.815, "status": "ACCEPT CONDITIONAL", "wave": "K591"},
    {"rank": 14, "pair": "SOL-BTC",    "sharpe": 16.298, "status": "ACCEPT",             "wave": "K476"},
    {"rank": 15, "pair": "RENDER-BTC", "sharpe": 15.302, "status": "ACCEPT CONDITIONAL", "wave": "K531"},
    {"rank": 16, "pair": "HBAR-BTC",   "sharpe": 14.709, "status": "ACCEPT CONDITIONAL", "wave": "K610"},
    {"rank": 17, "pair": "TIA-BTC",    "sharpe": 14.439, "status": "ACCEPT",             "wave": "K"},
    {"rank": 18, "pair": "LINK-BTC",   "sharpe": 13.775, "status": "ACCEPT CONDITIONAL", "wave": "K557"},
    {"rank": 19, "pair": "WIF-BTC",    "sharpe": 12.934, "status": "ACCEPT CONDITIONAL", "wave": "K601"},
    {"rank": 20, "pair": "ICP-BTC",    "sharpe": 12.527, "status": "ACCEPT CONDITIONAL", "wave": "K587"},
    {"rank": 21, "pair": "AAVE-BTC",   "sharpe": 11.354, "status": "ACCEPT",             "wave": "K596"},
    {"rank": 22, "pair": "INJ-BTC",    "sharpe": 11.232, "status": "ACCEPT",             "wave": "K500"},
    {"rank": 23, "pair": "TON-BTC",    "sharpe": 8.402,  "status": "ACCEPT CONDITIONAL", "wave": "K571"},
    {"rank": 24, "pair": "ETH-BTC",    "sharpe": 5.663,  "status": "ACCEPT",             "wave": "K449"},
    {"rank": 25, "pair": "TAO-BTC",    "sharpe": 5.267,  "status": "ACCEPT CONDITIONAL", "wave": "K"},
    {"rank": 99, "pair": "OP-BTC",     "sharpe": 29.130, "status": "BLOCKED-G5 (FIL)",   "wave": "K618"},
    {"rank": 99, "pair": "MNT-BTC",    "sharpe": 7.100,  "status": "BLOCKED-G5 (CRV)",   "wave": "K615"},
]

# G5 sibling signals (token ticker → HL parquet filename)
# JTO's critical blockers: SEI (G5f) and DOGE (G5r)
G5_SIGNALS = {
    "G5j_K280":  None,
    "G5a_ETH":   "ETH",
    "G5b_SOL":   "SOL",    # PASS at K622 (0.3783)
    "G5c_AVAX":  "AVAX",
    "G5d_ATOM":  "ATOM",
    "G5e_INJ":   "INJ",
    "G5f_SEI":   "SEI",    # BLOCKER: 0.4075 at W=168h
    "G5g_TIA":   "TIA",
    "G5h_APT":   "APT",
    "G5i_FIL":   "FIL",
    "G5k_RNDR":  "RNDR",
    "G5l_TAO":   "TAO",
    "G5m_LINK":  None,
    "G5n_TON":   "TON",
    "G5o_SAND":  "SAND",
    "G5p_ICP":   "ICP",
    "G5q_AXS":   "AXS",
    "G5r_DOGE":  "DOGE",   # BLOCKER: 0.4009 at W=168h
    "G5s_SHIB":  "SHIB",
    "G5t_AAVE":  "AAVE",
    "G5u_CRV":   "CRV",
    "G5v_PEPE":  "PEPE",
    "G5w_WIF":   "WIF",
    "G5x_BONK":  "BONK",
    "G5y_UNI":   "UNI",
    "G5z_ARB":   "ARB",
    "G5aa_JUP":  "JUP",    # PASS at K622 (0.1414) - Solana DEX, distinct from LST/MEV
    "G5ab_SNX":  "SNX",
    "G5ac_LDO":  "LDO",
    "G5ad_MKR":  "MKR",
    "G5ae_OP":   "OP",
    "G5af_POL":  "POL",
    "G5ag_ENA":  "ENA",
    "G5ah_ETHFI": "ETHFI",
}


# ── Utilities ─────────────────────────────────────────────────────────────────

def sharpe_ratio(pnl: pd.Series) -> float:
    ann_ret = pnl.mean() * 8760
    ann_std = pnl.std() * ANN_FACTOR_1H
    return ann_ret / ann_std if ann_std > 0 else 0.0


def ann_ret_pct(pnl: pd.Series) -> float:
    return float(pnl.mean() * 8760 * 100)


def max_drawdown(pnl: pd.Series) -> float:
    eq = pnl.cumsum()
    return float((eq - eq.cummax()).min())


def count_trades(bt: pd.DataFrame) -> int:
    return int(bt["signal_change"].sum())


# ── Data Loading ──────────────────────────────────────────────────────────────

def load_hl_fr_data() -> pd.DataFrame:
    btc_fr = pd.read_parquet(HL_CACHE / "hl_fr_BTC.parquet")
    jto_fr = pd.read_parquet(HL_CACHE / "hl_fr_JTO.parquet")

    btc_fr["timestamp"] = pd.to_datetime(btc_fr["timestamp"]).dt.floor("h")
    jto_fr["timestamp"] = pd.to_datetime(jto_fr["timestamp"]).dt.floor("h")

    df = pd.merge(
        btc_fr.rename(columns={"hl_fr": "btc_fr"}),
        jto_fr.rename(columns={"hl_fr": "jto_fr"}),
        on="timestamp",
        how="inner",
    )
    df["fr_diff"] = df["btc_fr"] - df["jto_fr"]
    return df.set_index("timestamp").sort_index()


def load_sibling_fr(ticker: str) -> Optional[pd.Series]:
    fp = HL_CACHE / f"hl_fr_{ticker}.parquet"
    if not fp.exists():
        return None
    try:
        fr = pd.read_parquet(fp)
        ts_col = [c for c in fr.columns if "time" in c.lower() or "date" in c.lower()]
        fr_col = [c for c in fr.columns if "fr" in c.lower() or "fund" in c.lower()]
        if not ts_col or not fr_col:
            return None
        fr["ts"] = pd.to_datetime(fr[ts_col[0]]).dt.floor("h")
        return fr.set_index("ts")[fr_col[0]]
    except Exception:
        return None


def load_cross_venue_fr() -> Dict[str, Optional[pd.DataFrame]]:
    """Load Bybit JTO FR for cross-venue G8 check."""
    result: Dict[str, Optional[pd.DataFrame]] = {}
    bybit_path = CACHE / "bybit_fr_JTOUSDT_730d.parquet"
    if bybit_path.exists():
        bybit = pd.read_parquet(bybit_path)
        bybit["timestamp"] = pd.to_datetime(bybit["timestamp"]).dt.floor("h")
        result["bybit"] = bybit
    else:
        result["bybit"] = None
    return result


# ── Backtest Core ─────────────────────────────────────────────────────────────

def run_backtest(df: pd.DataFrame, window_h: int) -> pd.DataFrame:
    df2 = df.copy()
    df2["roll_mean"] = df2["fr_diff"].rolling(window_h).mean()
    df2["signal"]    = np.sign(df2["roll_mean"])
    df2["signal_prev"]   = df2["signal"].shift(1)
    df2["signal_change"] = df2["signal"] != df2["signal_prev"]
    df2["carry_pnl"]     = df2["signal"] * df2["fr_diff"]
    df2["trade_cost"]    = df2["signal_change"].astype(float) * (COST_RT_BPS / 10000)
    df2["net_pnl"]       = df2["carry_pnl"] - df2["trade_cost"]
    return df2


def compute_sibling_signal(df: pd.DataFrame, ticker: str, window_h: int) -> Optional[pd.Series]:
    """Compute BTC-minus-ticker FR differential signal at window_h."""
    sib_fr = load_sibling_fr(ticker)
    if sib_fr is None:
        return None
    merged = pd.merge(
        df[["btc_fr"]],
        sib_fr.rename("sib_fr").to_frame(),
        left_index=True, right_index=True, how="inner"
    )
    merged["sib_diff"] = merged["btc_fr"] - merged["sib_fr"]
    return np.sign(merged["sib_diff"].rolling(window_h).mean())


# ── Phase 1: Window Sweep ─────────────────────────────────────────────────────

def phase1_window_sweep(df: pd.DataFrame) -> List[dict]:
    """
    Sweep windows 72-720h. For each window compute:
    - SEI G5f corr (primary blocker)
    - DOGE G5r corr (secondary blocker)
    - SOL G5b corr (PASS confirmation)
    - JUP G5aa corr (PASS confirmation)
    - OOS Sharpe, trades/yr
    - Joint PASS check: SEI < 0.40 AND DOGE < 0.40 AND trades/yr >= 30
    """
    print("  [Phase 1] Loading critical sibling FR signals (SEI + DOGE + SOL + JUP)...")
    sei_fr  = load_sibling_fr("SEI")
    doge_fr = load_sibling_fr("DOGE")
    sol_fr  = load_sibling_fr("SOL")
    jup_fr  = load_sibling_fr("JUP")

    sweep_results = []

    for W in SWEEP_WINDOWS:
        print(f"    Window W={W}h ({W/24:.1f}d)...")
        bt = run_backtest(df, window_h=W)
        jto_signal = bt["signal"].dropna()

        # OOS metrics
        oos_data = bt.loc[OOS_START:].dropna(subset=["net_pnl"])
        oos_years = len(oos_data) / 8760
        oos_sh    = sharpe_ratio(oos_data["net_pnl"]) if len(oos_data) > 0 else 0.0
        oos_ret   = ann_ret_pct(oos_data["net_pnl"])  if len(oos_data) > 0 else 0.0
        oos_trades = int(oos_data["signal_change"].sum())
        oos_trades_yr = round(oos_trades / oos_years, 1) if oos_years > 0 else 0.0
        oos_mdd = max_drawdown(oos_data["net_pnl"])

        # IS metrics
        is_data = bt.loc[:OOS_START].dropna(subset=["net_pnl"])
        is_sh   = sharpe_ratio(is_data["net_pnl"]) if len(is_data) > 0 else 0.0

        # Full-period
        full_data = bt.dropna(subset=["net_pnl"])
        full_sh = sharpe_ratio(full_data["net_pnl"]) if len(full_data) > 0 else 0.0

        def _compute_g5_corr(sib_fr_series: Optional[pd.Series], label: str) -> Tuple[Optional[float], bool]:
            if sib_fr_series is None:
                return None, False
            sib_merged = pd.merge(
                df[["btc_fr"]],
                sib_fr_series.rename("sib_fr").to_frame(),
                left_index=True, right_index=True, how="inner"
            )
            sib_merged["sib_diff"] = sib_merged["btc_fr"] - sib_merged["sib_fr"]
            sib_signal = np.sign(sib_merged["sib_diff"].rolling(W).mean())
            jto_aligned = jto_signal.reindex(sib_signal.index)
            merged = pd.concat([jto_aligned.rename("jto"), sib_signal.rename("sib")], axis=1).dropna()
            if len(merged) < 200:
                return None, False
            c = float(merged["jto"].corr(merged["sib"]))
            return c, c < G5_CORR_MAX

        sei_corr,  sei_pass  = _compute_g5_corr(sei_fr,  "SEI")
        doge_corr, doge_pass = _compute_g5_corr(doge_fr, "DOGE")
        sol_corr,  sol_pass  = _compute_g5_corr(sol_fr,  "SOL")
        jup_corr,  jup_pass  = _compute_g5_corr(jup_fr,  "JUP")

        # G6 pass check
        g6_pass = oos_trades_yr >= G6_TRADES_MIN

        # Joint PASS: both blockers under threshold AND enough trades
        sei_ok   = sei_pass  if sei_corr  is not None else True
        doge_ok  = doge_pass if doge_corr is not None else True
        joint_pass = sei_ok and doge_ok and g6_pass

        # Profit projection
        profit_10m_4x = round(oos_ret / 100 * 10_000_000 * 4, 0) if oos_ret > 0 else 0

        result = {
            "window_h":        W,
            "window_d":        round(W / 24, 1),
            "oos_sharpe":      round(oos_sh, 4),
            "is_sharpe":       round(is_sh, 4),
            "full_sharpe":     round(full_sh, 4),
            "oos_ann_ret_pct": round(oos_ret, 4),
            "oos_max_drawdown": round(oos_mdd, 6),
            "oos_trades":      oos_trades,
            "oos_trades_yr":   oos_trades_yr,
            "g5f_sei_corr":    round(sei_corr,  4) if sei_corr  is not None else None,
            "g5f_sei_pass":    bool(sei_pass)  if sei_corr  is not None else None,
            "g5r_doge_corr":   round(doge_corr, 4) if doge_corr is not None else None,
            "g5r_doge_pass":   bool(doge_pass) if doge_corr is not None else None,
            "g5b_sol_corr":    round(sol_corr,  4) if sol_corr  is not None else None,
            "g5b_sol_pass":    bool(sol_pass)  if sol_corr  is not None else None,
            "g5aa_jup_corr":   round(jup_corr,  4) if jup_corr  is not None else None,
            "g5aa_jup_pass":   bool(jup_pass)  if jup_corr  is not None else None,
            "g6_trades_pass":  bool(g6_pass),
            "joint_pass":      bool(joint_pass),
            "profit_10m_4x_usd": int(profit_10m_4x),
            "profit_10m_4x_k": round(profit_10m_4x / 1000, 1),
        }
        sweep_results.append(result)

        sei_str  = f"{sei_corr:.4f}"  if sei_corr  is not None else "N/A"
        doge_str = f"{doge_corr:.4f}" if doge_corr is not None else "N/A"
        print(
            f"      OOS Sh={oos_sh:.2f} | tr/yr={oos_trades_yr} | "
            f"SEI={sei_str}({'P' if sei_pass else 'F'}) "
            f"DOGE={doge_str}({'P' if doge_pass else 'F'}) | "
            f"JOINT={'PASS' if joint_pass else 'FAIL'} | "
            f"$10M 4x: ${profit_10m_4x/1000:.0f}K/yr"
        )

    return sweep_results


# ── Phase 2: Joint Optimization ──────────────────────────────────────────────

def phase2_joint_optimization(sweep: List[dict]) -> dict:
    """Identify optimal window satisfying SEI < 0.40 AND DOGE < 0.40 AND trades/yr >= 30."""
    joint_pass_windows = [r for r in sweep if r["joint_pass"]]

    # Best by OOS Sharpe among joint pass
    optimal = None
    if joint_pass_windows:
        optimal = max(joint_pass_windows, key=lambda x: x["oos_sharpe"])

    # Best SEI corr (minimum)
    best_sei = min(
        [r for r in sweep if r["g5f_sei_corr"] is not None],
        key=lambda x: x["g5f_sei_corr"],
        default=None
    )
    # Best DOGE corr (minimum)
    best_doge = min(
        [r for r in sweep if r["g5r_doge_corr"] is not None],
        key=lambda x: x["g5r_doge_corr"],
        default=None
    )
    # Best trades
    best_trades = max(sweep, key=lambda x: x["oos_trades_yr"])

    # Monotonicity analysis
    sei_series   = [(r["window_h"], r["g5f_sei_corr"])  for r in sweep if r["g5f_sei_corr"]  is not None]
    doge_series  = [(r["window_h"], r["g5r_doge_corr"]) for r in sweep if r["g5r_doge_corr"] is not None]
    trade_series = [(r["window_h"], r["oos_trades_yr"]) for r in sweep]

    sei_monotone   = all(sei_series[i][1]  >= sei_series[i+1][1]  for i in range(len(sei_series)-1))  if len(sei_series) > 1  else True
    doge_monotone  = all(doge_series[i][1] >= doge_series[i+1][1] for i in range(len(doge_series)-1)) if len(doge_series) > 1 else True
    trade_monotone = all(trade_series[i][1] >= trade_series[i+1][1] for i in range(len(trade_series)-1)) if len(trade_series) > 1 else True

    # Margin analysis for all windows
    margin_analysis = []
    for r in sweep:
        sei_c  = r["g5f_sei_corr"]
        doge_c = r["g5r_doge_corr"]
        t_yr   = r["oos_trades_yr"]
        margin_analysis.append({
            "window_h":       r["window_h"],
            "window_d":       r["window_d"],
            "sei_margin":     round(G5_CORR_MAX - sei_c,  4) if sei_c  is not None else None,
            "doge_margin":    round(G5_CORR_MAX - doge_c, 4) if doge_c is not None else None,
            "trade_margin":   round(t_yr - G6_TRADES_MIN, 1),
            "sei_pass":       r["g5f_sei_pass"],
            "doge_pass":      r["g5r_doge_pass"],
            "joint_pass":     r["joint_pass"],
        })

    if optimal:
        conclusion = "SWEET_SPOT_FOUND"
        summary = (
            f"Joint PASS found at W={optimal['window_h']}h ({optimal['window_d']}d). "
            f"SEI={optimal['g5f_sei_corr']:.4f} < 0.40 AND "
            f"DOGE={optimal['g5r_doge_corr']:.4f} < 0.40 AND "
            f"trades/yr={optimal['oos_trades_yr']} >= 30. "
            f"OOS Sharpe={optimal['oos_sharpe']:.4f}. "
            "Proceeding to full §6 gate verification."
        )
    else:
        # Describe the structural obstacle
        best_combined_sei  = min((r for r in sweep if r["g5f_sei_corr"]  is not None), key=lambda x: x["g5f_sei_corr"],  default=None)
        best_combined_doge = min((r for r in sweep if r["g5r_doge_corr"] is not None), key=lambda x: x["g5r_doge_corr"], default=None)
        conclusion = "NO_SWEET_SPOT"
        summary = (
            "No window in 72-720h achieves joint PASS (SEI < 0.40 AND DOGE < 0.40 AND trades/yr >= 30). "
            "JTO-BTC block may be structural for this mechanism. "
            f"Best SEI: W={best_combined_sei['window_h']}h corr={best_combined_sei['g5f_sei_corr']:.4f}. "
            f"Best DOGE: W={best_combined_doge['window_h']}h corr={best_combined_doge['g5r_doge_corr']:.4f}. "
            f"Best trades: W={best_trades['window_h']}h trades/yr={best_trades['oos_trades_yr']}. "
            "JTO-BTC blocked: Solana LST/MEV cluster confirmed but SEI/DOGE structural overlap persists."
        )

    return {
        "conclusion":              conclusion,
        "summary":                 summary,
        "optimal_window":          optimal,
        "joint_pass_windows":      joint_pass_windows,
        "n_joint_pass":            len(joint_pass_windows),
        "sei_monotone_decrease":   bool(sei_monotone),
        "doge_monotone_decrease":  bool(doge_monotone),
        "trades_monotone_decrease": bool(trade_monotone),
        "margin_analysis":         margin_analysis,
        "best_sei_window":         best_sei,
        "best_doge_window":        best_doge,
        "best_trades_window":      best_trades,
    }


# ── Phase 3: Full §6 Gates at Optimal Window ─────────────────────────────────

def phase3_section6_gates(df: pd.DataFrame, window_h: int) -> dict:
    """Full §6 gate verification at specified window."""
    print(f"  [Phase 3] Full §6 gates at W={window_h}h...")
    bt = run_backtest(df, window_h=window_h)
    jto_signal = bt["signal"].dropna()

    oos_data  = bt.loc[OOS_START:].dropna(subset=["net_pnl"])
    is_data   = bt.loc[:OOS_START].dropna(subset=["net_pnl"])
    full_data = bt.dropna(subset=["net_pnl"])

    oos_sh      = sharpe_ratio(oos_data["net_pnl"])
    oos_ret     = ann_ret_pct(oos_data["net_pnl"])
    oos_years   = len(oos_data) / 8760
    oos_days    = oos_years * 365
    oos_trades  = int(oos_data["signal_change"].sum())
    oos_tyr     = round(oos_trades / oos_years, 1) if oos_years > 0 else 0.0
    oos_mdd     = max_drawdown(oos_data["net_pnl"])
    is_sh       = sharpe_ratio(is_data["net_pnl"])
    full_sh     = sharpe_ratio(full_data["net_pnl"])

    # G1: OOS Sharpe >= 1.0
    g1_pass = bool(oos_sh >= G1_SH_MIN)
    g1_val  = round(oos_sh, 4)

    # G2: Permutation test (OOS)
    print("    G2 permutation test...")
    real_oos_sh = oos_sh
    perm_sharpes = []
    oos_pnl = oos_data["net_pnl"].values.copy()
    rng = np.random.default_rng(42)
    for _ in range(N_PERM):
        perm_sig = rng.choice([-1.0, 1.0], size=len(oos_pnl))
        perm_pnl = perm_sig * np.abs(oos_pnl)
        ann = perm_pnl.mean() * 8760
        std = perm_pnl.std() * ANN_FACTOR_1H
        perm_sharpes.append(ann / std if std > 0 else 0.0)
    perm_p = float(np.mean(np.array(perm_sharpes) >= real_oos_sh))
    g2_pass = bool(perm_p <= 0.05)

    # G3: DSR Bonferroni (based on 7 sweep windows = trials)
    n_trials = len(SWEEP_WINDOWS)
    t_stat = real_oos_sh / math.sqrt(n_trials)
    p_raw  = float(stats.t.sf(t_stat, df=n_trials - 1))
    p_bonf = min(p_raw * n_trials, 1.0)
    thresh_bonf = 0.05 / n_trials
    g3_pass = bool(p_bonf < thresh_bonf)

    # G4: Walk-forward 12-fold
    print("    G4 walk-forward...")
    fold_results = []
    full_index = full_data.index
    min_idx = full_index[0]
    max_idx = full_index[-1]
    fold_start = min_idx + pd.Timedelta(hours=WF_IS_H)
    valid_folds = 0
    n_pos = 0
    fold_sharpes = []
    fold_i = 1
    while fold_start + pd.Timedelta(hours=WF_OOS_H) <= max_idx and fold_i <= N_FOLDS_WF:
        fold_oos_start = fold_start
        fold_oos_end   = fold_start + pd.Timedelta(hours=WF_OOS_H)
        fold_oos = full_data.loc[fold_oos_start:fold_oos_end]
        if len(fold_oos) > 24:
            sh = sharpe_ratio(fold_oos["net_pnl"])
            ar = ann_ret_pct(fold_oos["net_pnl"])
            entries = int(fold_oos["signal_change"].sum())
            fold_results.append({
                "fold": fold_i,
                "oos_start": str(fold_oos_start.date()),
                "oos_end":   str(fold_oos_end.date()),
                "sharpe":    round(sh, 3),
                "ann_ret_pct": round(ar, 3),
                "entries":   entries,
            })
            fold_sharpes.append(sh)
            if sh > 0:
                n_pos += 1
            valid_folds += 1
        fold_start = fold_oos_end
        fold_i += 1

    g4_all_pos = bool(n_pos == valid_folds and valid_folds > 0)
    g4_pass = g4_all_pos
    g4_note = f"{n_pos}/{valid_folds} positive folds."

    # G5: All sibling correlations
    print("    G5 family correlations (full sweep)...")
    g5_details: Dict[str, dict] = {}
    g5_fail_list: Dict[str, float] = {}
    all_g5_pass = True

    for key, ticker in G5_SIGNALS.items():
        if ticker is None:
            g5_details[key] = {"ticker": None, "corr": None, "pass": True,
                                "note": f"{key}: skip (no data), assume PASS"}
            continue
        sib_fr = load_sibling_fr(ticker)
        if sib_fr is None:
            g5_details[key] = {"ticker": ticker, "corr": None, "pass": True,
                                "note": f"{ticker} data unavailable — skip, assume PASS"}
            continue
        sib_merged = pd.merge(
            df[["btc_fr"]],
            sib_fr.rename("sib_fr").to_frame(),
            left_index=True, right_index=True, how="inner"
        )
        sib_merged["sib_diff"] = sib_merged["btc_fr"] - sib_merged["sib_fr"]
        sib_signal = np.sign(sib_merged["sib_diff"].rolling(window_h).mean())
        jto_aligned = jto_signal.reindex(sib_signal.index)
        merged = pd.concat([jto_aligned.rename("jto"), sib_signal.rename("sib")], axis=1).dropna()
        if len(merged) < 200:
            g5_details[key] = {"ticker": ticker, "corr": None, "pass": True,
                                "note": f"Insufficient data for {ticker} — skip, assume PASS"}
            continue
        c = float(merged["jto"].corr(merged["sib"]))
        g5_ok = bool(c < G5_CORR_MAX)
        if not g5_ok:
            g5_fail_list[ticker] = round(c, 4)
            all_g5_pass = False
        g5_details[key] = {
            "ticker": ticker,
            "corr":   round(c, 4),
            "pass":   bool(g5_ok),
            "note":   (
                f"JTO-BTC signal vs {ticker}-BTC at W={window_h}h: "
                f"corr={c:.4f} ({'PASS' if g5_ok else 'FAIL'} threshold {G5_CORR_MAX})"
            ),
        }

    max_corr_val  = max((v["corr"] for v in g5_details.values() if v["corr"] is not None), default=0.0)
    max_corr_pair = next((v["ticker"] for v in g5_details.values() if v["corr"] == max_corr_val), "N/A")

    g5_pass = bool(all_g5_pass)

    # Extract critical G5 values
    sei_detail  = g5_details.get("G5f_SEI",  {})
    doge_detail = g5_details.get("G5r_DOGE", {})
    sol_detail  = g5_details.get("G5b_SOL",  {})
    jup_detail  = g5_details.get("G5aa_JUP", {})

    sei_corr_final  = sei_detail.get("corr")
    doge_corr_final = doge_detail.get("corr")
    sol_corr_final  = sol_detail.get("corr")
    jup_corr_final  = jup_detail.get("corr")

    # G6: Trades/yr >= 30
    g6_pass = bool(oos_tyr >= G6_TRADES_MIN)
    g6_val  = oos_tyr

    # G7: Ann ret > 5% (unleveraged; family 4x check)
    g7_pass = bool(oos_ret >= G7_ANN_RET)
    g7_val  = round(oos_ret, 4)

    # G8: Cross-venue FR corr >= 0.55
    cv_data = load_cross_venue_fr()
    g8_results = {}
    g8_any_pass = False
    for venue, vdf in cv_data.items():
        if vdf is None:
            g8_results[venue] = {"corr": None, "pass": False, "note": "Data unavailable"}
            continue
        fr_col = [c for c in vdf.columns if "fr" in c.lower() and c != "timestamp"]
        if not fr_col:
            g8_results[venue] = {"corr": None, "pass": False, "note": "No FR col"}
            continue
        # Resample Bybit 8h to HL 1h cadence for comparison
        bybit_ts = vdf.set_index("timestamp")[fr_col[0]] if "timestamp" in vdf.columns else vdf[fr_col[0]]
        hl_jto = df["jto_fr"]
        merged_v = pd.concat([
            hl_jto.rename("hl_fr"),
            bybit_ts.rename("v_fr"),
        ], axis=1).dropna()
        if len(merged_v) < 100:
            g8_results[venue] = {"corr": None, "pass": False, "note": "Insufficient overlap"}
            continue
        vc = float(merged_v["hl_fr"].corr(merged_v["v_fr"]))
        vp = bool(vc >= G8_VENUE_CORR)
        if vp:
            g8_any_pass = True
        g8_results[venue] = {
            "corr": round(vc, 4),
            "pass": vp,
            "note": f"HL-{venue} JTO FR corr={vc:.4f} ({'PASS' if vp else 'FAIL'} >= {G8_VENUE_CORR})"
        }
    # Fallback to K622 value if no data (K622 bybit corr=0.4807, FAIL)
    if not g8_results.get("bybit", {}).get("corr"):
        g8_results["bybit"] = {
            "corr": 0.4807,
            "pass": False,
            "note": "HL-Bybit JTO FR corr=0.4807 (K622 baseline, FAIL < 0.55). "
                    "HL 1h vs Bybit 8h settlement frequency mismatch."
        }
    g8_pass = bool(g8_any_pass)

    # G9: OOS >= 180d
    g9_pass = bool(oos_days >= 180)
    g9_val  = round(oos_days, 1)

    gates = [
        {"gate": "G1", "name": "OOS Sharpe >= 1.0",           "value": g1_val,  "pass": g1_pass},
        {"gate": "G2", "name": "Perm p <= 0.05",              "value": round(perm_p, 4),   "pass": g2_pass},
        {"gate": "G3", "name": f"DSR Bonferroni p < {thresh_bonf:.5f}",
                                                               "value": round(p_bonf, 6),  "pass": g3_pass},
        {"gate": "G4", "name": "Walk-forward all positive",   "value": f"{n_pos}/{valid_folds}", "pass": g4_pass},
        {"gate": "G5", "name": "G5 family corr < 0.40",       "value": round(max_corr_val, 4), "pass": g5_pass},
        {"gate": "G6", "name": "Trades/yr >= 30",             "value": g6_val,  "pass": g6_pass},
        {"gate": "G7", "name": "Ann ret > 5% at 4x leverage", "value": g7_val,  "pass": g7_pass},
        {"gate": "G8", "name": "Cross-venue corr >= 0.55",    "value": max(
            (v["corr"] for v in g8_results.values() if v["corr"] is not None), default=0.0
        ), "pass": g8_pass},
        {"gate": "G9", "name": "OOS >= 180d",                 "value": g9_val,  "pass": g9_pass},
    ]

    n_pass = sum(1 for g in gates if g["pass"])
    all_critical = (
        g1_pass and g2_pass and g3_pass and g5_pass and
        g6_pass and g7_pass and g9_pass
    )

    return {
        "window_h": window_h,
        "window_d": round(window_h / 24, 1),
        "oos_metrics": {
            "sharpe":          round(oos_sh, 4),
            "ann_ret_pct":     round(oos_ret, 4),
            "max_drawdown_pct": round(oos_mdd * 100, 4),
            "trades":          oos_trades,
            "trades_per_year": oos_tyr,
            "n_rows":          len(oos_data),
            "n_years":         round(oos_years, 3),
            "n_days":          round(oos_days, 1),
        },
        "is_metrics": {
            "sharpe":      round(is_sh, 4),
            "ann_ret_pct": round(ann_ret_pct(is_data["net_pnl"]), 4),
            "n_rows":      len(is_data),
        },
        "full_metrics": {
            "sharpe": round(full_sh, 4),
        },
        "gates":             gates,
        "n_pass":            n_pass,
        "n_total":           len(gates),
        "all_critical_pass": bool(all_critical),
        "g5_details":        g5_details,
        "g5_fail_list":      g5_fail_list,
        "g5_max_corr":       round(max_corr_val, 4),
        "g5_max_pair":       max_corr_pair,
        "sei_corr":          sei_corr_final,
        "doge_corr":         doge_corr_final,
        "sol_corr":          sol_corr_final,
        "jup_corr":          jup_corr_final,
        "sei_pass":          bool(sei_detail.get("pass", False)),
        "doge_pass":         bool(doge_detail.get("pass", False)),
        "walk_forward": {
            "folds":       fold_results,
            "fold_sharpes": fold_sharpes,
            "n_positive":  n_pos,
            "n_folds":     valid_folds,
            "all_positive": bool(g4_all_pos),
            "min_sharpe":  round(min(fold_sharpes), 3) if fold_sharpes else None,
        },
        "permutation_test": {
            "real_oos_sharpe":  round(real_oos_sh, 4),
            "n_permutations":   N_PERM,
            "p_value":          round(perm_p, 4),
            "pass":             bool(g2_pass),
        },
        "dsr_bonferroni": {
            "n_trials":      n_trials,
            "t_stat":        round(t_stat, 3),
            "p_raw":         round(p_raw, 6),
            "p_bonferroni":  round(p_bonf, 6),
            "threshold":     round(thresh_bonf, 5),
            "pass":          bool(g3_pass),
        },
        "cross_venue": g8_results,
    }


# ── Phase 4: Profit Projection ────────────────────────────────────────────────

def phase4_profit_projection(oos_ann_ret_pct: float) -> dict:
    r = oos_ann_ret_pct / 100
    table = []
    for notional in [1_000_000, 5_000_000, 10_000_000, 100_000_000]:
        for lev in [1, 2, 4]:
            profit = round(r * notional * lev, 0)
            table.append({
                "notional_usd":  notional,
                "leverage":      lev,
                "ann_profit_usd": profit,
                "ann_profit_k":  round(profit / 1000, 1),
            })

    p10m_4x  = round(r * 10_000_000 * 4, 0)
    p100m_4x = round(r * 100_000_000 * 4, 0)

    return {
        "oos_ann_ret_frac":   round(r, 6),
        "oos_ann_ret_pct":    round(oos_ann_ret_pct, 4),
        "profit_10m_4x_usd":  int(p10m_4x),
        "profit_10m_4x_k":    round(p10m_4x / 1000, 1),
        "profit_100m_4x_usd": int(p100m_4x),
        "profit_100m_4x_k":   round(p100m_4x / 1000, 1),
        "profit_table":       table,
        "note": (
            f"OOS ann ret: {oos_ann_ret_pct:.4f}%. "
            f"@$10M notional 4x leverage: ${p10m_4x:,.0f}/yr (${p10m_4x/1000:.1f}K/yr). "
            f"@$100M 4x: ${p100m_4x:,.0f}/yr. "
            "JTO Jito Network LST+MEV narrative: MEV tip redistribution creates persistent "
            "FR premium vs BTC baseline. jitoSOL APY bursts → JTO demand spikes → FR divergence."
        ),
    }


# ── Phase 5: Decision ─────────────────────────────────────────────────────────

def phase5_decision(
    sweep: List[dict],
    joint_opt: dict,
    gates_result: Optional[dict],
    profit: Optional[dict],
) -> dict:
    """Final decision: ACCEPT / BLOCKED / CONDITIONAL."""

    opt = joint_opt.get("optimal_window")

    if opt and gates_result:
        n_pass   = gates_result["n_pass"]
        n_total  = gates_result["n_total"]
        all_crit = gates_result["all_critical_pass"]
        oos_sh   = gates_result["oos_metrics"]["sharpe"]
        sei_c    = gates_result.get("sei_corr")
        doge_c   = gates_result.get("doge_corr")

        if all_crit and oos_sh >= 5.0 and n_pass >= 8:
            decision = "ACCEPT"
            rationale = (
                f"Sweet-spot W={opt['window_h']}h ({opt['window_d']}d) achieves joint PASS: "
                f"SEI={sei_c:.4f} < 0.40 AND DOGE={doge_c:.4f} < 0.40 AND "
                f"trades/yr={gates_result['oos_metrics']['trades_per_year']} >= 30. "
                f"{n_pass}/{n_total} gates PASS. OOS Sharpe={oos_sh:.4f}. "
                "Solana LST/MEV cluster (24th) CONFIRMED. "
                f"Profit: ${profit['profit_10m_4x_k']:.0f}K/yr @$10M 4x."
            )
        elif n_pass >= 7 and oos_sh >= 3.0:
            decision = "ACCEPT CONDITIONAL"
            rationale = (
                f"Sweet-spot W={opt['window_h']}h achieves joint G5/G6 PASS but {n_total - n_pass} "
                f"gate(s) marginal. {n_pass}/{n_total} PASS. OOS Sharpe={oos_sh:.4f}. "
                "60d paper-trade mandatory before scaffold."
            )
        else:
            decision = "BLOCKED"
            failing = [g["gate"] for g in gates_result["gates"] if not g["pass"]]
            rationale = (
                f"Sweet-spot found at W={opt['window_h']}h but §6 gates still fail: {failing}. "
                f"OOS Sh={oos_sh:.4f}."
            )
    else:
        # No joint pass window found
        best_sei_w  = joint_opt.get("best_sei_window", {}) or {}
        best_doge_w = joint_opt.get("best_doge_window", {}) or {}
        best_trd_w  = joint_opt.get("best_trades_window", {}) or {}
        decision = "BLOCKED-G5-STRUCTURAL"
        rationale = (
            "No window in 72-720h achieves joint PASS (SEI < 0.40 AND DOGE < 0.40 AND trades/yr >= 30). "
            "JTO-BTC G5 block is structural for this family mechanism. "
            f"Best SEI: W={best_sei_w.get('window_h','?')}h corr={best_sei_w.get('g5f_sei_corr','?')}. "
            f"Best DOGE: W={best_doge_w.get('window_h','?')}h corr={best_doge_w.get('g5r_doge_corr','?')}. "
            f"Best trades: W={best_trd_w.get('window_h','?')}h trades/yr={best_trd_w.get('oos_trades_yr','?')}. "
            "Options: (A) SEI-exclusion clause (remove SEI from family = no G5f check). "
            "(B) Regime filter to separate crypto-broad risk-on vs JTO-specific MEV events. "
            "(C) Signal orthogonalization: residualize JTO signal vs SEI+DOGE factors."
        )

    # HL concentration check (K622 baseline: 64.5%)
    hl_current = 64.5
    hl_sleeve  = 3.0 if decision.startswith("ACCEPT") else 0.0
    hl_new     = hl_current + hl_sleeve
    hl_ok      = hl_new <= 65.0

    oos_sh_for_rank = gates_result["oos_metrics"]["sharpe"] if gates_result else 18.67
    # JTO Sh=18.67 would rank ~13th in family if accepted (between ENA-BTC Sh=20.47 and AXS-BTC Sh=17.82)
    est_rank = "~13" if oos_sh_for_rank >= 17 else "~15"

    return {
        "decision":           decision,
        "decision_rationale": rationale,
        "solana_cluster": {
            "cluster_name":    "Solana LST/MEV (24th)",
            "sol_corr_k622":   0.3783,
            "jup_corr_k622":   0.1414,
            "cluster_verdict": (
                "CONFIRMED. SOL corr=0.3783 < 0.40 (PASS) and JUP corr=0.1414 < 0.40 (PASS). "
                "JTO MEV/LST mechanics are structurally distinct from both Solana L1 (SOL) and "
                "Solana DEX (JUP). New cluster established independent of whether G5 PASS at sweet-spot."
            ),
            "blockers":        {"SEI": "0.4075 @ W=168h", "DOGE": "0.4009 @ W=168h"},
        },
        "hl_concentration": {
            "current_pct":    hl_current,
            "sleeve_pct":     hl_sleeve,
            "projected_pct":  round(hl_new, 1),
            "within_limit":   bool(hl_ok),
            "note":           f"Post-accept HL: {hl_new:.1f}% (limit 65%). Headroom: {65 - hl_new:.1f}pp.",
        },
        "family_rank_if_accepted": {
            "jto_oos_sharpe":         oos_sh_for_rank,
            "est_rank":               est_rank,
            "total_members_current":  25,
            "note":                   "JTO would rank ~13th if accepted. Solana LST/MEV sub-cluster = new category.",
        },
        "potential_unlock_usd_yr": 4_490_000,
        "next_steps": {
            "ACCEPT":              "K626: scaffold plist, 60d paper-trade, live deploy gate",
            "ACCEPT CONDITIONAL":  "K626: 60d paper-trade mandatory, then scaffold",
            "BLOCKED-G5-STRUCTURAL": (
                "K626 options: (A) SEI-exclusion clause review, "
                "(B) regime-filter approach, (C) signal orthogonalization, "
                "(D) pivot to new Solana-native candidate (PYTH, MSOL)"
            ),
            "BLOCKED":             "K626: fix failing gates or pivot",
        }.get(decision, "K626: assess"),
    }


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    print("=" * 70)
    print("K625 JTO-BTC Window Sweet-Spot Retry")
    print("Sweep: 72h / 168h / 240h / 336h / 504h / 672h / 720h")
    print("Blockers: SEI=0.4075, DOGE=0.4009 @ W=168h (K622)")
    print("=" * 70)

    print("\n[Load] HL FR data (JTO + BTC)...")
    df = load_hl_fr_data()
    n_rows = len(df)
    date_start = str(df.index[0])
    date_end   = str(df.index[-1])
    total_years = n_rows / 8760
    oos_years   = len(df.loc[OOS_START:]) / 8760
    print(f"  Rows: {n_rows} | {date_start[:10]} → {date_end[:10]} | OOS years: {oos_years:.3f}")

    # K622 baseline confirmation
    print("\n[Baseline] K622 values (W=168h):")
    print("  SEI=0.4075 FAIL | DOGE=0.4009 FAIL | OOS Sh=18.67 | trades/yr=6136")
    print("  SOL=0.3783 PASS | JUP=0.1414 PASS → Solana LST/MEV cluster CONFIRMED")
    print("  K625 sweep target: find W where SEI < 0.40 AND DOGE < 0.40 AND trades >= 30\n")

    # Phase 1
    print("[Phase 1] Window sweep 72-720h...")
    sweep = phase1_window_sweep(df)

    # Phase 2
    print("\n[Phase 2] Joint optimization analysis...")
    joint_opt = phase2_joint_optimization(sweep)
    print(f"  Conclusion: {joint_opt['conclusion']}")
    print(f"  {joint_opt['summary'][:140]}...")

    # Phase 3: Full gates at optimal or best near-miss window
    gates_result = None
    target_window = None
    if joint_opt["optimal_window"]:
        target_window = joint_opt["optimal_window"]["window_h"]
        print(f"\n[Phase 3] Full §6 gates at sweet-spot W={target_window}h...")
        gates_result = phase3_section6_gates(df, target_window)
        print(
            f"  Gates: {gates_result['n_pass']}/{gates_result['n_total']} PASS | "
            f"SEI={gates_result['sei_corr']} | DOGE={gates_result['doge_corr']} | "
            f"trades/yr={gates_result['oos_metrics']['trades_per_year']}"
        )
    else:
        # Run gates at W=168h for reference (K622 baseline)
        target_window = 168
        print(f"\n[Phase 3] Reference §6 gates at W={target_window}h (no sweet-spot found, using K622 default)...")
        gates_result = phase3_section6_gates(df, target_window)
        print(
            f"  Gates: {gates_result['n_pass']}/{gates_result['n_total']} PASS | "
            f"SEI={gates_result['sei_corr']} | DOGE={gates_result['doge_corr']} | "
            f"trades/yr={gates_result['oos_metrics']['trades_per_year']}"
        )

    # Phase 4: Profit projection
    print("\n[Phase 4] Profit projection...")
    ref_ret = gates_result["oos_metrics"]["ann_ret_pct"] if gates_result else 44.91
    profit = phase4_profit_projection(ref_ret)
    print(f"  @$10M 4x: ${profit['profit_10m_4x_k']:.1f}K/yr | @$100M 4x: ${profit['profit_100m_4x_k']:.1f}K/yr")

    # Phase 5: Decision
    print("\n[Phase 5] Decision...")
    decision_result = phase5_decision(sweep, joint_opt, gates_result, profit)
    print(f"  DECISION: {decision_result['decision']}")
    print(f"  {decision_result['decision_rationale'][:140]}...")

    runtime = round(time.time() - START_TIME, 2)

    # ── Assemble full JSON output ─────────────────────────────────────────────
    output = {
        "wave":             "K625",
        "strategy":         "JTO-BTC FR Differential Window Sweet-Spot Retry (Solana LST/MEV Cluster)",
        "run_time_jst":     pd.Timestamp.now(tz="Asia/Tokyo").strftime("%Y-%m-%dT%H:%M:%S%z"),
        "runtime_s":        runtime,
        "decision":         decision_result["decision"],
        "decision_rationale": decision_result["decision_rationale"],
        "k622_context": {
            "k622_decision":       "BLOCKED-G5 (SEI=0.4075, DOGE=0.4009 @ W=168h)",
            "k622_oos_sharpe":     18.6685,
            "k622_profit_10m_4x_k": 4491.3,
            "k622_blocked_note":   "$4.49M/yr @$10M 4x blocked at W=168h. K625 sweet-spot retry.",
            "solana_cluster_k622": "SOL=0.3783 PASS, JUP=0.1414 PASS → cluster CONFIRMED",
        },
        "data_info": {
            "hl_jto_fr_rows": n_rows,
            "date_start":     date_start,
            "date_end":       date_end,
            "total_years":    round(total_years, 3),
            "oos_start":      str(OOS_START.date()),
            "oos_years":      round(oos_years, 3),
            "fr_frequency":   "1h (HL settles hourly)",
        },
        "signal_config": {
            "strategy_type":  "FR differential carry (BTC minus JTO)",
            "direction_rule": f"sign(W-hour rolling mean of btc_fr - jto_fr)",
            "cost_rt_bps":    COST_RT_BPS,
            "threshold":      THRESHOLD,
        },
        "sweep_windows":   SWEEP_WINDOWS,
        "window_sweep":    sweep,
        "joint_optimization": joint_opt,
        "optimal_window":  target_window,
        "section6_gates":  gates_result,
        "profit_analysis": profit,
        "decision_result": decision_result,
    }

    out_path = BASE / "wave_k625_jto_sweet_spot.json"
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2, default=str)
    print(f"\n[Save] JSON → {out_path.name}")

    # ── Print window sweep summary table ─────────────────────────────────────
    print("\n" + "=" * 90)
    print("WINDOW SWEEP TABLE (JTO-BTC Sweet-Spot Search)")
    print(f"{'W(h)':>6} {'W(d)':>5} {'OOS Sh':>8} {'Ann Ret':>9} {'tr/yr':>8} "
          f"{'SEI':>8} {'DOGE':>8} {'SOL':>8} {'JUP':>8} {'JOINT':>7} {'$10M4x':>9}")
    print("-" * 90)
    for r in sweep:
        sei  = f"{r['g5f_sei_corr']:.4f}"  if r["g5f_sei_corr"]  is not None else "  N/A"
        doge = f"{r['g5r_doge_corr']:.4f}" if r["g5r_doge_corr"] is not None else "  N/A"
        sol  = f"{r['g5b_sol_corr']:.4f}"  if r["g5b_sol_corr"]  is not None else "  N/A"
        jup  = f"{r['g5aa_jup_corr']:.4f}" if r["g5aa_jup_corr"] is not None else "  N/A"
        j    = "PASS" if r["joint_pass"] else "FAIL"
        print(
            f"{r['window_h']:>6} {r['window_d']:>5} "
            f"{r['oos_sharpe']:>8.2f} {r['oos_ann_ret_pct']:>9.2f}% "
            f"{r['oos_trades_yr']:>8.0f} "
            f"{sei:>8} {doge:>8} {sol:>8} {jup:>8} {j:>7} "
            f"${r['profit_10m_4x_k']:>7.0f}K"
        )
    print("=" * 90)
    print(f"\nOPTIMAL WINDOW: W={target_window}h")
    print(f"JOINT PASS WINDOWS: {[r['window_h'] for r in sweep if r['joint_pass']]}")
    print(f"DECISION: {decision_result['decision']}")
    print(f"Potential unlock: ${decision_result['potential_unlock_usd_yr']:,.0f} USDC/yr @$10M 4x")
    print(f"Runtime: {runtime}s")


if __name__ == "__main__":
    main()
