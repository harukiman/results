"""Wave K180 - DOGE Asymmetric Tail Mechanism Investigation.

K178 discovered:
  DOGE z>2 -> next-event return = -43.94 bps (very strong K175-favorable edge, comparable to XRP -49 bps)
  BUT K177 DOGE aggregate K175-Normal net Sh = -0.19 (slightly negative)
  This is a TAIL ASYMMETRY: gain side (z>2 short) wins, but losses elsewhere (likely z<-2 long) cancel them out.

Goal: confirm mechanism and test if ONE-TAIL-ONLY DOGE K175 variant (only z>2 short, never trade z<-2 long)
is a viable ACCEPT candidate.

Required variants:
  V_doge_z2_short_only   : z>2 -> SHORT only (no z<-2 trades)
  V_doge_z2_long_only    : z<-2 -> LONG only (sanity; should be much worse)
  V_doge_asymmetric_z    : z>2 SHORT + z<-1.5 LONG (different threshold per tail)
  V_doge_aggregate       : standard both-tails z>2 (replicate K177 result)

Sweeps:
  z-threshold: [1.5, 2.0, 2.5, 3.0]
  lookback window: [30, 60, 90 events]

§6 gates if best variant gross >= 1.0:
  G1 OOS Sharpe net >= 1.0
  G2 Perm p <= 0.05
  G3 DSR >= 0.95
  G4 WF folds all positive
  G5 IS/OOS ratio >= 0.5
  G6 Gross Sharpe >= 0.3
  G7 Trades/year >= 20

K173 META-LESSON: Report GROSS and NET separately.
"""
from __future__ import annotations

import json
import time
from math import erf, sqrt
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from scipy import stats as scipy_stats

ROOT = Path("/Users/nekonaomichi/crypto-lab")
CACHE = ROOT / "cache"
HL_CACHE = CACHE / "k163_hl"

# Maker-only execution cost model (K175-identical)
SLIPPAGE_BPS_PER_SIDE = 2.0
MAKER_FEE_BPS_PER_SIDE = 0.0
COST_PER_FILL = (SLIPPAGE_BPS_PER_SIDE + MAKER_FEE_BPS_PER_SIDE) * 1e-4  # 0.0002

# 8h Bybit funding cadence
EVENTS_PER_YEAR = 365 * 24 // 8  # 1095


# ─────────────────────────── Data Loading ───────────────────────────

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

    # Aggregate HL 1h -> 8h (same cadence as Bybit)
    hl_8h = hl.resample("8h", label="right", closed="right").sum(min_count=1)

    idx = by.index
    df = pd.DataFrame({"bybit_fr": by}, index=idx)
    df["hl_fr_8h"] = hl_8h.reindex(idx)
    df = df.dropna()

    # FR premium = Bybit - HL (positive = Bybit more bullish than HL)
    df["fr_premium"] = df["bybit_fr"] - df["hl_fr_8h"]

    cl_at_event = cl.reindex(idx, method="nearest", tolerance=pd.Timedelta("2h"))
    df["close"] = cl_at_event
    df = df.dropna(subset=["close"])

    df["fwd_ret_1"] = np.log(df["close"]).diff().shift(-1)
    df.attrs["symbol"] = sym
    return df


# ─────────────────────────── Stats Utilities ───────────────────────────

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
    return float(np.expm1(total / max(years, 1e-6)))


def max_dd(pnl: pd.Series) -> float:
    eq = pnl.fillna(0).cumsum()
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
    perm_sharpes = []
    for _ in range(n):
        perm_vals = rng.permutation(vals)
        s = pd.Series(perm_vals)
        perm_sharpes.append(float(s.mean() / (s.std() + 1e-12) * np.sqrt(EVENTS_PER_YEAR)))
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
    e_max = np.sqrt(2 * np.log(max(n_trials, 2))) - emc / np.sqrt(2 * np.log(max(n_trials, 2)))
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
        sharpes.append(float(s.mean() / (s.std() + 1e-12) * np.sqrt(EVENTS_PER_YEAR)) if s.std() > 0 else 0.0)
    return float(np.mean(sharpes)), [float(x) for x in sharpes]


def zscore(s: pd.Series, win: int = 30) -> pd.Series:
    mu = s.rolling(win, min_periods=win).mean()
    sd = s.rolling(win, min_periods=win).std()
    return (s - mu) / (sd + 1e-12)


# ─────────────────────────── Per-Event Tail Analysis ───────────────────────────

def per_event_tail_analysis(df: pd.DataFrame, z_thr: float = 2.0, zwin: int = 30) -> Dict:
    """Decompose events into z>+thr (SHORT tail) and z<-thr (LONG tail).
    For each tail: count, mean fwd return, std, t-stat, Sharpe contribution, per-event PnL.
    """
    z = zscore(df["fr_premium"], zwin)
    aligned = pd.DataFrame({
        "z": z,
        "fwd": df["fwd_ret_1"],
    }).dropna()

    short_events = aligned[aligned["z"] > z_thr]
    long_events = aligned[aligned["z"] < -z_thr]
    neutral_events = aligned[(aligned["z"] >= -z_thr) & (aligned["z"] <= z_thr)]

    # K175 positions:
    # z>+thr -> SHORT Bybit: profit when price falls (fwd_ret < 0)
    # z<-thr -> LONG Bybit: profit when price rises (fwd_ret > 0)
    short_pnl = -short_events["fwd"]  # SHORT: profit = -fwd_ret
    long_pnl = long_events["fwd"]     # LONG:  profit = +fwd_ret

    def tail_stats(pnl: pd.Series, fwd: pd.Series, tag: str) -> Dict:
        n = len(pnl)
        if n == 0:
            return {"count": 0, "mean_fwd_bps": 0.0, "mean_pnl_bps": 0.0, "std_bps": 0.0,
                    "tstat": 0.0, "pval": 1.0, "sharpe_annualized": 0.0, "win_rate": 0.0}
        fwd_vals = fwd.values
        mean_fwd = float(fwd_vals.mean()) * 1e4
        mean_pnl = float(pnl.values.mean()) * 1e4
        std = float(pnl.values.std()) * 1e4
        tstat, pval = scipy_stats.ttest_1samp(pnl.values, 0.0) if n > 5 else (0.0, 1.0)
        # Sharpe annualized: per-event mean/std * sqrt(events_per_year)
        sh = float(pnl.values.mean() / (pnl.values.std() + 1e-12) * np.sqrt(EVENTS_PER_YEAR)) if n > 5 else 0.0
        win_rate = float((pnl.values > 0).mean())
        return {
            "count": int(n),
            "mean_fwd_bps": round(mean_fwd, 4),
            "mean_pnl_bps": round(mean_pnl, 4),
            "std_bps": round(std, 4),
            "tstat": round(float(tstat), 4),
            "pval": round(float(pval), 4),
            "sharpe_annualized": round(sh, 4),
            "win_rate": round(win_rate, 4),
        }

    return {
        "z_threshold": z_thr,
        "lookback_window": zwin,
        "n_total_events": int(len(aligned)),
        "short_tail": tail_stats(short_pnl, short_events["fwd"], "short"),
        "long_tail": tail_stats(long_pnl, long_events["fwd"], "long"),
        "neutral_events_count": int(len(neutral_events)),
        "short_pnl_cumsum_bps": [round(x * 1e4, 4) for x in short_pnl.cumsum().values],
        "long_pnl_cumsum_bps": [round(x * 1e4, 4) for x in long_pnl.cumsum().values],
    }


# ─────────────────────────── Strategy Engine ───────────────────────────

def run_strategy_one_tail(
    df: pd.DataFrame,
    z_thr_short: float = 2.0,
    z_thr_long: float = 2.0,
    only_short: bool = False,
    only_long: bool = False,
    hold: int = 1,
    zwin: int = 30,
    cost_per_fill: float = COST_PER_FILL,
) -> Tuple[pd.Series, pd.Series, int]:
    """Asymmetric K175 variant.

    z_thr_short: threshold for SHORT signal (z > z_thr_short)
    z_thr_long:  threshold for LONG signal (z < -z_thr_long)
    only_short:  if True, only trade SHORT direction
    only_long:   if True, only trade LONG direction
    """
    z = zscore(df["fr_premium"], zwin)

    sig = pd.Series(0.0, index=df.index)
    if not only_long:
        sig[z > z_thr_short] = -1.0  # SHORT signal
    if not only_short:
        sig[z < -z_thr_long] = 1.0   # LONG signal

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
    pnl_gross = pos * fwd
    pos_change = pos.diff().fillna(pos.iloc[0])
    cost_series = pd.Series(0.0, index=df.index)
    cost_series[pos_change != 0] = cost_per_fill
    pnl_net = pnl_gross - cost_series

    return pnl_net, pnl_gross, trades


def full_metrics(
    pnl_net: pd.Series,
    pnl_gross: pd.Series,
    n_trades: int,
    n_trials_dsr: int = 4,
) -> Dict:
    sh_net = sharpe(pnl_net)
    sh_gross = sharpe(pnl_gross)
    split = int(len(pnl_net) * 0.7)
    is_pnl_net = pnl_net.iloc[:split]
    oos_pnl_net = pnl_net.iloc[split:]
    is_pnl_gross = pnl_gross.iloc[:split]
    oos_pnl_gross = pnl_gross.iloc[split:]
    is_sh_net = sharpe(is_pnl_net)
    oos_sh_net = sharpe(oos_pnl_net)
    is_sh_gross = sharpe(is_pnl_gross)
    oos_sh_gross = sharpe(oos_pnl_gross)
    wf_mean, wf_folds = wf_3fold(pnl_net)
    wf_mean_g, wf_folds_g = wf_3fold(pnl_gross)
    perm_p = perm_test(pnl_net, n=200)
    perm_p_g = perm_test(pnl_gross, n=200)
    ci_lo, ci_hi = bootstrap_ci(pnl_net, n=200)
    ci_lo_g, ci_hi_g = bootstrap_ci(pnl_gross, n=200)
    dsr_p = dsr(pnl_net, n_trials=n_trials_dsr)
    dsr_p_g = dsr(pnl_gross, n_trials=n_trials_dsr)
    years = len(pnl_net) / EVENTS_PER_YEAR
    tpy = round(n_trades / max(years, 1e-6), 2)
    return {
        "sharpe_net": round(sh_net, 4),
        "sharpe_gross": round(sh_gross, 4),
        "cagr_net": round(cagr(pnl_net), 4),
        "cagr_gross": round(cagr(pnl_gross), 4),
        "max_dd_net": round(max_dd(pnl_net), 4),
        "is_sharpe_net": round(is_sh_net, 4),
        "oos_sharpe_net": round(oos_sh_net, 4),
        "is_sharpe_gross": round(is_sh_gross, 4),
        "oos_sharpe_gross": round(oos_sh_gross, 4),
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
        "trades_per_year": tpy,
        "n_events": int(len(pnl_net)),
    }


def run_section6_gates(metrics: Dict) -> Tuple[Dict[str, bool], int]:
    """Full §6 gate evaluation. Returns (gates_dict, n_passed)."""
    gates = {
        "G1_oos_sharpe_net_ge_1": metrics["oos_sharpe_net"] >= 1.0,
        "G2_perm_p_le_0p05": metrics["perm_pvalue_net"] <= 0.05,
        "G3_dsr_ge_0p95": metrics["dsr_net"] >= 0.95,
        "G4_wf_folds_all_positive": all(x > 0 for x in metrics["wf_folds_net"]) if metrics["wf_folds_net"] else False,
        "G5_is_oos_ratio_ge_0p5": (
            metrics["oos_sharpe_net"] / metrics["is_sharpe_net"] >= 0.5
            if metrics["is_sharpe_net"] > 0 else False
        ),
        "G6_gross_ge_0p3": metrics["sharpe_gross"] >= 0.3,
        "G7_trades_per_year_ge_20": metrics["trades_per_year"] >= 20,
    }
    n_passed = sum(gates.values())
    return gates, n_passed


# ─────────────────────────── Rolling Sharpe ───────────────────────────

def rolling_sharpe_series(pnl: pd.Series, window_events: int = 365) -> List[float]:
    out = []
    for i in range(len(pnl)):
        if i < window_events:
            out.append(float("nan"))
            continue
        w = pnl.iloc[i - window_events:i]
        if w.std() == 0:
            out.append(0.0)
        else:
            out.append(float(w.mean() / w.std() * np.sqrt(EVENTS_PER_YEAR)))
    return out


# ─────────────────────────── Main ───────────────────────────

def main() -> None:
    t0 = time.time()
    print("=== Wave K180: DOGE Asymmetric Tail Mechanism Investigation ===\n")

    # Load DOGE panel
    doge = build_panel("DOGE")
    if doge is None:
        print("ERROR: failed to build DOGE panel")
        return

    print(f"DOGE panel: {len(doge)} events, {doge.index[0].date()} to {doge.index[-1].date()}")
    print(f"  fr_premium stats: mean={doge['fr_premium'].mean()*1e4:+.4f}bps, "
          f"std={doge['fr_premium'].std()*1e4:.4f}bps, "
          f"skew={doge['fr_premium'].skew():+.4f}")
    print()

    # ── Section 1: Per-Event Tail Decomposition ──
    print("--- Section 1: Per-Event Tail Decomposition (z=2.0, win=30) ---")
    tail_analysis_main = per_event_tail_analysis(doge, z_thr=2.0, zwin=30)
    st = tail_analysis_main["short_tail"]
    lt = tail_analysis_main["long_tail"]
    print(f"  Total events: {tail_analysis_main['n_total_events']}")
    print(f"  SHORT tail (z>+2.0): n={st['count']}, mean_fwd={st['mean_fwd_bps']:+.2f}bps, "
          f"mean_pnl={st['mean_pnl_bps']:+.2f}bps, Sh={st['sharpe_annualized']:+.4f}, "
          f"p={st['pval']:.4f}, win={st['win_rate']:.3f}")
    print(f"  LONG tail  (z<-2.0): n={lt['count']}, mean_fwd={lt['mean_fwd_bps']:+.2f}bps, "
          f"mean_pnl={lt['mean_pnl_bps']:+.2f}bps, Sh={lt['sharpe_annualized']:+.4f}, "
          f"p={lt['pval']:.4f}, win={lt['win_rate']:.3f}")
    print(f"  Neutral events: {tail_analysis_main['neutral_events_count']}")
    print()

    # Tail analysis across different z thresholds and windows
    print("--- Section 1b: Tail Analysis Sweep ---")
    tail_sweep = {}
    for zwin in [30, 60, 90]:
        for zthr in [1.5, 2.0, 2.5, 3.0]:
            ta = per_event_tail_analysis(doge, z_thr=zthr, zwin=zwin)
            key = f"win{zwin}_z{zthr}"
            tail_sweep[key] = {
                "short_n": ta["short_tail"]["count"],
                "short_pnl_bps": ta["short_tail"]["mean_pnl_bps"],
                "short_sh": ta["short_tail"]["sharpe_annualized"],
                "short_pval": ta["short_tail"]["pval"],
                "long_n": ta["long_tail"]["count"],
                "long_pnl_bps": ta["long_tail"]["mean_pnl_bps"],
                "long_sh": ta["long_tail"]["sharpe_annualized"],
                "long_pval": ta["long_tail"]["pval"],
            }
            print(f"  win={zwin} z={zthr}: SHORT n={ta['short_tail']['count']:3d} "
                  f"pnl={ta['short_tail']['mean_pnl_bps']:+6.2f}bps sh={ta['short_tail']['sharpe_annualized']:+.3f} "
                  f"| LONG n={ta['long_tail']['count']:3d} "
                  f"pnl={ta['long_tail']['mean_pnl_bps']:+6.2f}bps sh={ta['long_tail']['sharpe_annualized']:+.3f}")
    print()

    # ── Section 2: Aggregate Baseline (K177 replicate) ──
    print("--- Section 2: V_doge_aggregate (K177 replicate, both tails) ---")
    pnl_agg_net, pnl_agg_gross, n_agg = run_strategy_one_tail(
        doge, z_thr_short=2.0, z_thr_long=2.0, only_short=False, only_long=False
    )
    m_agg = full_metrics(pnl_agg_net, pnl_agg_gross, n_agg)
    print(f"  V_doge_aggregate: Sh_gross={m_agg['sharpe_gross']:+.4f}  "
          f"Sh_net={m_agg['sharpe_net']:+.4f}  "
          f"IS_net={m_agg['is_sharpe_net']:+.4f}  OOS_net={m_agg['oos_sharpe_net']:+.4f}  "
          f"trades={n_agg}")
    print()

    # ── Section 3: V_doge_z2_short_only (PRIMARY) ──
    print("--- Section 3: V_doge_z2_short_only (PRIMARY HYPOTHESIS) ---")
    pnl_so_net, pnl_so_gross, n_so = run_strategy_one_tail(
        doge, z_thr_short=2.0, only_short=True
    )
    m_so = full_metrics(pnl_so_net, pnl_so_gross, n_so)
    print(f"  V_doge_z2_short_only: Sh_gross={m_so['sharpe_gross']:+.4f}  "
          f"Sh_net={m_so['sharpe_net']:+.4f}  "
          f"IS_net={m_so['is_sharpe_net']:+.4f}  OOS_net={m_so['oos_sharpe_net']:+.4f}  "
          f"trades={n_so}  tpy={m_so['trades_per_year']}")
    print(f"    DSR_net={m_so['dsr_net']:.4f}  perm_p_net={m_so['perm_pvalue_net']:.4f}  "
          f"WF_folds={m_so['wf_folds_net']}")
    print()

    # ── Section 4: V_doge_z2_long_only (SANITY) ──
    print("--- Section 4: V_doge_z2_long_only (SANITY - should be worse) ---")
    pnl_lo_net, pnl_lo_gross, n_lo = run_strategy_one_tail(
        doge, z_thr_long=2.0, only_long=True
    )
    m_lo = full_metrics(pnl_lo_net, pnl_lo_gross, n_lo)
    print(f"  V_doge_z2_long_only: Sh_gross={m_lo['sharpe_gross']:+.4f}  "
          f"Sh_net={m_lo['sharpe_net']:+.4f}  "
          f"IS_net={m_lo['is_sharpe_net']:+.4f}  OOS_net={m_lo['oos_sharpe_net']:+.4f}  "
          f"trades={n_lo}")
    print()

    # ── Section 5: V_doge_asymmetric_z variants ──
    print("--- Section 5: V_doge_asymmetric_z (asymmetric thresholds) ---")
    asym_variants = {}
    for z_short, z_long in [(2.0, 1.5), (2.0, 2.5), (2.5, 1.5), (2.5, 2.0), (1.5, 2.0)]:
        key = f"short_z{z_short}_long_z{z_long}"
        pn, pg, nt = run_strategy_one_tail(
            doge, z_thr_short=z_short, z_thr_long=z_long, only_short=False, only_long=False
        )
        m = full_metrics(pn, pg, nt)
        asym_variants[key] = m
        print(f"  {key}: Sh_gross={m['sharpe_gross']:+.4f}  "
              f"Sh_net={m['sharpe_net']:+.4f}  OOS_net={m['oos_sharpe_net']:+.4f}  trades={nt}")
    print()

    # ── Section 6: Z-threshold sweep (SHORT-ONLY) ──
    print("--- Section 6: Z-threshold sweep (V_doge_short_only) ---")
    z_thr_sweep = {}
    for zthr in [1.5, 2.0, 2.5, 3.0]:
        pn, pg, nt = run_strategy_one_tail(
            doge, z_thr_short=zthr, only_short=True
        )
        sh_g = sharpe(pg)
        sh_n = sharpe(pn)
        oos_sh_n = sharpe(pn.iloc[int(len(pn) * 0.7):])
        key = f"z{zthr}"
        z_thr_sweep[key] = {
            "sharpe_gross": round(sh_g, 4),
            "sharpe_net": round(sh_n, 4),
            "oos_sharpe_net": round(oos_sh_n, 4),
            "n_trades": int(nt),
        }
        print(f"  z_thr={zthr}: Sh_gross={sh_g:+.4f}  Sh_net={sh_n:+.4f}  "
              f"OOS_net={oos_sh_n:+.4f}  trades={nt}")
    print()

    # ── Section 7: Lookback window sweep (SHORT-ONLY) ──
    print("--- Section 7: Lookback window sweep (V_doge_short_only, z=2.0) ---")
    win_sweep = {}
    for zwin in [30, 60, 90]:
        pn, pg, nt = run_strategy_one_tail(
            doge, z_thr_short=2.0, only_short=True, zwin=zwin
        )
        sh_g = sharpe(pg)
        sh_n = sharpe(pn)
        oos_sh_n = sharpe(pn.iloc[int(len(pn) * 0.7):])
        key = f"win{zwin}"
        win_sweep[key] = {
            "sharpe_gross": round(sh_g, 4),
            "sharpe_net": round(sh_n, 4),
            "oos_sharpe_net": round(oos_sh_n, 4),
            "n_trades": int(nt),
        }
        print(f"  zwin={zwin}: Sh_gross={sh_g:+.4f}  Sh_net={sh_n:+.4f}  "
              f"OOS_net={oos_sh_n:+.4f}  trades={nt}")
    print()

    # ── Section 8: §6 Gates (if gross >= 1.0) ──
    print("--- Section 8: §6 Gate Evaluation ---")
    gates_so = None
    gates_passed = 0
    candidate_status = "SKIP (gross < 1.0)"

    # Find best variant by gross Sharpe
    all_variants = {
        "V_doge_aggregate": m_agg,
        "V_doge_z2_short_only": m_so,
        "V_doge_z2_long_only": m_lo,
    }
    all_variants.update({f"V_asym_{k}": v for k, v in asym_variants.items()})

    best_name = max(all_variants, key=lambda k: all_variants[k]["sharpe_gross"])
    best_m = all_variants[best_name]
    print(f"  Best variant by gross Sharpe: {best_name} = {best_m['sharpe_gross']:+.4f}")

    if best_m["sharpe_gross"] >= 1.0:
        print(f"\n  {best_name} gross >= 1.0 -> running full §6 gates...")
        gates_so, gates_passed = run_section6_gates(best_m)
        for g, v in gates_so.items():
            print(f"    {g}: {'PASS' if v else 'FAIL'}")

        # Also check critical gates G1+G2+G3
        g1 = gates_so.get("G1_oos_sharpe_net_ge_1", False)
        g2 = gates_so.get("G2_perm_p_le_0p05", False)
        g3 = gates_so.get("G3_dsr_ge_0p95", False)
        critical_pass = g1 and g2 and g3

        if gates_passed >= 4 and critical_pass:
            candidate_status = f"ACCEPT ({gates_passed}/7, G1+G2+G3 all pass)"
        elif gates_passed >= 4:
            candidate_status = f"CONDITIONAL ({gates_passed}/7, critical gates missing)"
        else:
            candidate_status = f"REJECT ({gates_passed}/7)"
        print(f"\n  Verdict: {candidate_status}")
    elif m_so["sharpe_gross"] >= 0.3:
        # Still run gates for V_doge_z2_short_only if gross >= 0.3
        print(f"\n  V_doge_z2_short_only gross={m_so['sharpe_gross']:+.4f} >= 0.3 but < 1.0 -> partial gates...")
        gates_so, gates_passed = run_section6_gates(m_so)
        for g, v in gates_so.items():
            print(f"    {g}: {'PASS' if v else 'FAIL'}")
        candidate_status = f"REJECT (gross < 1.0, partial gates: {gates_passed}/7)"
        print(f"\n  Verdict: {candidate_status}")
    else:
        gates_so, gates_passed = run_section6_gates(m_so)
        print(f"  V_doge_z2_short_only gross={m_so['sharpe_gross']:+.4f} < 0.3 -> REJECT")
        candidate_status = f"REJECT (gross={m_so['sharpe_gross']:+.4f} < 0.3)"

    print()

    # ── Section 9: Rolling Sharpe Stability ──
    print("--- Section 9: Rolling Sharpe Stability ---")
    roll_sh_so = rolling_sharpe_series(pnl_so_net, window_events=365)
    roll_sh_agg = rolling_sharpe_series(pnl_agg_net, window_events=365)
    valid_so = [x for x in roll_sh_so if not np.isnan(x)]
    valid_agg = [x for x in roll_sh_agg if not np.isnan(x)]
    if valid_so:
        frac_pos = (np.array(valid_so) > 0).mean()
        print(f"  V_doge_short_only rolling Sh (365-event): mean={np.mean(valid_so):+.3f}  "
              f"std={np.std(valid_so):.3f}  min={np.min(valid_so):+.3f}  max={np.max(valid_so):+.3f}  "
              f"frac_positive={frac_pos:.3f}")
    if valid_agg:
        frac_pos_agg = (np.array(valid_agg) > 0).mean()
        print(f"  V_doge_aggregate rolling Sh (365-event): mean={np.mean(valid_agg):+.3f}  "
              f"std={np.std(valid_agg):.3f}  frac_positive={frac_pos_agg:.3f}")
    print()

    # ── Build equity curves ──
    print("--- Building equity curves ---")
    # Main variant curves
    timestamps = [str(t.date()) for t in doge.index]
    curves = {
        "timestamps": timestamps,
        "V_doge_aggregate_gross": equity_curve(pnl_agg_gross),
        "V_doge_aggregate_net": equity_curve(pnl_agg_net),
        "V_doge_z2_short_only_gross": equity_curve(pnl_so_gross),
        "V_doge_z2_short_only_net": equity_curve(pnl_so_net),
        "V_doge_z2_long_only_gross": equity_curve(pnl_lo_gross),
        "V_doge_z2_long_only_net": equity_curve(pnl_lo_net),
        "rolling_sharpe_short_only": roll_sh_so,
        "rolling_sharpe_aggregate": roll_sh_agg,
        # Tail decomposition (cumulative PnL)
        "short_tail_cumsum_bps": tail_analysis_main["short_pnl_cumsum_bps"],
        "long_tail_cumsum_bps": tail_analysis_main["long_pnl_cumsum_bps"],
    }

    # Add best asymmetric variant curves
    if asym_variants:
        best_asym_key = max(asym_variants, key=lambda k: asym_variants[k]["sharpe_gross"])
        z_short_best = float(best_asym_key.split("_")[1].replace("z", ""))
        z_long_best = float(best_asym_key.split("_")[3].replace("z", ""))
        pn_asym, pg_asym, _ = run_strategy_one_tail(
            doge, z_thr_short=z_short_best, z_thr_long=z_long_best,
        )
        curves["V_asym_best_gross"] = equity_curve(pg_asym)
        curves["V_asym_best_net"] = equity_curve(pn_asym)
        curves["V_asym_best_label"] = best_asym_key

    runtime = round(time.time() - t0, 1)
    print(f"\nRuntime: {runtime}s")

    # ── Assemble JSON output ──
    result_json = {
        "wave": "K180",
        "parent_waves": ["K175", "K177", "K178"],
        "date": "2026-05-25",
        "objective": "DOGE asymmetric tail mechanism - one-tail-only K175 variant",
        "runtime_sec": runtime,
        "cost_model": {
            "slippage_bps_per_side": SLIPPAGE_BPS_PER_SIDE,
            "maker_fee_bps_per_side": MAKER_FEE_BPS_PER_SIDE,
            "cost_per_fill_bps": COST_PER_FILL * 1e4,
            "round_trip_bps": COST_PER_FILL * 2e4,
        },
        "data_summary": {
            "symbol": "DOGE",
            "n_events": int(len(doge)),
            "date_start": str(doge.index[0].date()),
            "date_end": str(doge.index[-1].date()),
            "fr_premium_mean_bps": round(float(doge["fr_premium"].mean()) * 1e4, 4),
            "fr_premium_std_bps": round(float(doge["fr_premium"].std()) * 1e4, 4),
        },
        "per_event_tail_analysis": {
            k: v for k, v in tail_analysis_main.items()
            if k not in ("short_pnl_cumsum_bps", "long_pnl_cumsum_bps")
        },
        "tail_sweep": tail_sweep,
        "variants": {
            "V_doge_aggregate": m_agg,
            "V_doge_z2_short_only": m_so,
            "V_doge_z2_long_only": m_lo,
        },
        "asymmetric_variants": {f"V_asym_{k}": v for k, v in asym_variants.items()},
        "z_thr_sweep_short_only": z_thr_sweep,
        "lookback_win_sweep_short_only": win_sweep,
        "section6_gates": {
            "evaluated_on": "V_doge_z2_short_only",
            "gates": gates_so,
            "gates_passed": gates_passed,
            "candidate_status": candidate_status,
            "best_variant_name": best_name,
            "best_variant_gross": best_m["sharpe_gross"],
        },
        "rolling_sharpe": {
            "window_events": 365,
            "short_only_mean": round(float(np.nanmean(roll_sh_so)), 4) if roll_sh_so else 0.0,
            "short_only_frac_positive": round(float(np.mean([x > 0 for x in valid_so])), 4) if valid_so else 0.0,
            "aggregate_mean": round(float(np.nanmean(roll_sh_agg)), 4) if roll_sh_agg else 0.0,
            "aggregate_frac_positive": round(float(np.mean([x > 0 for x in valid_agg])), 4) if valid_agg else 0.0,
        },
        "k180_verdict": candidate_status,
        "k181_recommendation": (
            "Proceed to K181 K176->9-strategy ensemble integration test"
            if ("ACCEPT" in candidate_status or ("CONDITIONAL" in candidate_status and gates_passed >= 5))
            else "REJECT - do not integrate into K176 ensemble at this time"
        ),
    }

    # Save JSON outputs
    out_json = ROOT / "wave_k180_doge_tail_asym.json"
    out_curves = ROOT / "wave_k180_curves.json"
    with open(out_json, "w") as f:
        json.dump(result_json, f, indent=2, default=str)
    with open(out_curves, "w") as f:
        json.dump(curves, f, indent=2, default=str)

    print(f"\nSaved: {out_json}")
    print(f"Saved: {out_curves}")
    print(f"\n{'='*60}")
    print(f"K180 FINAL VERDICT: {candidate_status}")
    print(f"{'='*60}")

    # ── Build Markdown Report ──
    build_markdown_report(result_json, m_so, m_agg, m_lo, gates_so, gates_passed, candidate_status)


def build_markdown_report(
    result_json: Dict,
    m_so: Dict,
    m_agg: Dict,
    m_lo: Dict,
    gates: Optional[Dict],
    gates_passed: int,
    candidate_status: str,
) -> None:
    ta = result_json["per_event_tail_analysis"]
    st = ta["short_tail"]
    lt = ta["long_tail"]
    data = result_json["data_summary"]
    cost = result_json["cost_model"]

    report = f"""# Wave K180: DOGE Asymmetric Tail Mechanism Investigation

**Date:** 2026-05-25
**Runtime:** {result_json['runtime_sec']}s
**Parent waves:** K175, K177, K178

## Executive Summary

K178 revealed DOGE has a strong K175-favorable SHORT signal (z>2 → -43.94 bps next-event return)
comparable to XRP's -49 bps edge. Yet the K177 DOGE aggregate Sharpe (net) was -0.19.
This wave tests the **tail asymmetry hypothesis**: the z>2 SHORT tail has genuine edge while the
z<-2 LONG tail destroys aggregate performance. If confirmed, a one-tail-only DOGE variant could
be a standalone ACCEPT candidate for integration into the K176 ensemble.

**K180 Verdict: {candidate_status}**

---

## 1. Data Summary

| Item | Value |
|------|-------|
| Symbol | DOGE |
| Events | {data['n_events']} |
| Date range | {data['date_start']} → {data['date_end']} |
| FR premium mean | {data['fr_premium_mean_bps']:+.4f} bps |
| FR premium std | {data['fr_premium_std_bps']:.4f} bps |
| Cost model | {cost['cost_per_fill_bps']:.0f} bps/fill, {cost['round_trip_bps']:.0f} bps round-trip |

---

## 2. Per-Event Tail Decomposition

Window=30 events, z-threshold=2.0.

| Tail | Direction | Count | Mean fwd return | Mean PnL | Sharpe | p-value | Win rate |
|------|-----------|-------|-----------------|----------|--------|---------|----------|
| SHORT (z>+2) | SELL Bybit | {st['count']} | {st['mean_fwd_bps']:+.2f} bps | {st['mean_pnl_bps']:+.2f} bps | {st['sharpe_annualized']:+.4f} | {st['pval']:.4f} | {st['win_rate']:.3f} |
| LONG (z<-2) | BUY Bybit | {lt['count']} | {lt['mean_fwd_bps']:+.2f} bps | {lt['mean_pnl_bps']:+.2f} bps | {lt['sharpe_annualized']:+.4f} | {lt['pval']:.4f} | {lt['win_rate']:.3f} |

**Interpretation:**
- SHORT tail (z>2): mean PnL = {st['mean_pnl_bps']:+.2f} bps, Sh = {st['sharpe_annualized']:+.4f} → confirms K178 discovery
- LONG tail (z<-2): mean PnL = {lt['mean_pnl_bps']:+.2f} bps, Sh = {lt['sharpe_annualized']:+.4f} → {"NEGATIVE = drag on aggregate" if lt['sharpe_annualized'] < 0 else "POSITIVE = contributes positively"}
- Asymmetry confirmed: SHORT edge {">> LONG edge (tail asymmetry verified)" if abs(st['mean_pnl_bps']) > abs(lt['mean_pnl_bps']) else "~ LONG edge (symmetric)"}

---

## 3. Variant Comparison (GROSS and NET)

All variants use z=2.0, win=30 events, 2 bp/side maker cost.

| Variant | Sh Gross | Sh Net | IS Sh Net | OOS Sh Net | Trades | TPY |
|---------|----------|--------|-----------|------------|--------|-----|
| V_doge_aggregate (K177 replicate) | {m_agg['sharpe_gross']:+.4f} | {m_agg['sharpe_net']:+.4f} | {m_agg['is_sharpe_net']:+.4f} | {m_agg['oos_sharpe_net']:+.4f} | {m_agg['n_trades']} | {m_agg['trades_per_year']} |
| V_doge_z2_short_only (PRIMARY) | {m_so['sharpe_gross']:+.4f} | {m_so['sharpe_net']:+.4f} | {m_so['is_sharpe_net']:+.4f} | {m_so['oos_sharpe_net']:+.4f} | {m_so['n_trades']} | {m_so['trades_per_year']} |
| V_doge_z2_long_only (SANITY) | {m_lo['sharpe_gross']:+.4f} | {m_lo['sharpe_net']:+.4f} | {m_lo['is_sharpe_net']:+.4f} | {m_lo['oos_sharpe_net']:+.4f} | {m_lo['n_trades']} | {m_lo['trades_per_year']} |

**K173 META-LESSON applied:** Gross and Net reported separately throughout.

---

## 4. Z-Threshold Sweep (V_doge_short_only)

| Z-threshold | Sh Gross | Sh Net | OOS Sh Net | Trades |
|-------------|----------|--------|------------|--------|
"""
    for k, v in result_json["z_thr_sweep_short_only"].items():
        report += f"| {k} | {v['sharpe_gross']:+.4f} | {v['sharpe_net']:+.4f} | {v['oos_sharpe_net']:+.4f} | {v['n_trades']} |\n"

    report += """
---

## 5. Lookback Window Sweep (V_doge_short_only, z=2.0)

| Window | Sh Gross | Sh Net | OOS Sh Net | Trades |
|--------|----------|--------|------------|--------|
"""
    for k, v in result_json["lookback_win_sweep_short_only"].items():
        report += f"| {k} | {v['sharpe_gross']:+.4f} | {v['sharpe_net']:+.4f} | {v['oos_sharpe_net']:+.4f} | {v['n_trades']} |\n"

    report += f"""
---

## 6. V_doge_z2_short_only Full Metrics

| Metric | Value |
|--------|-------|
| Sharpe (GROSS) | {m_so['sharpe_gross']:+.4f} |
| Sharpe (NET) | {m_so['sharpe_net']:+.4f} |
| CAGR (NET) | {m_so['cagr_net']:+.4f} |
| Max DD (NET) | {m_so['max_dd_net']:+.4f} |
| IS Sharpe (NET) | {m_so['is_sharpe_net']:+.4f} |
| OOS Sharpe (NET) | {m_so['oos_sharpe_net']:+.4f} |
| IS/OOS Ratio | {m_so['oos_sharpe_net']/max(m_so['is_sharpe_net'], 0.001):+.4f} |
| WF Fold Sharpes | {m_so['wf_folds_net']} |
| Perm p-value (NET) | {m_so['perm_pvalue_net']:.4f} |
| DSR (NET) | {m_so['dsr_net']:.4f} |
| Bootstrap CI 5-95 (NET) | {m_so['bootstrap_ci_5_95_net']} |
| N Trades | {m_so['n_trades']} |
| Trades/Year | {m_so['trades_per_year']} |

---

## 7. §6 Gate Evaluation

"""
    if gates:
        report += f"Evaluated on: **{result_json['section6_gates']['evaluated_on']}**\n\n"
        report += "| Gate | Threshold | Result |\n|------|-----------|--------|\n"
        gate_desc = {
            "G1_oos_sharpe_net_ge_1": "OOS Sharpe Net >= 1.0",
            "G2_perm_p_le_0p05": "Perm p-value <= 0.05",
            "G3_dsr_ge_0p95": "DSR >= 0.95",
            "G4_wf_folds_all_positive": "WF all folds positive",
            "G5_is_oos_ratio_ge_0p5": "IS/OOS ratio >= 0.5",
            "G6_gross_ge_0p3": "Gross Sharpe >= 0.3",
            "G7_trades_per_year_ge_20": "Trades/year >= 20",
        }
        for g, v in gates.items():
            report += f"| {g} | {gate_desc.get(g, '')} | {'**PASS**' if v else 'FAIL'} |\n"
        report += f"\n**Gates passed: {gates_passed}/7**\n"
    else:
        report += "Not evaluated (gross < 0.3 or not triggered).\n"

    report += f"""
---

## 8. Rolling Sharpe Stability

| Metric | V_doge_short_only | V_doge_aggregate |
|--------|-------------------|-----------------|
| Mean rolling Sharpe (365-event) | {result_json['rolling_sharpe']['short_only_mean']:+.4f} | {result_json['rolling_sharpe']['aggregate_mean']:+.4f} |
| Fraction windows positive | {result_json['rolling_sharpe']['short_only_frac_positive']:.3f} | {result_json['rolling_sharpe']['aggregate_frac_positive']:.3f} |

---

## 9. Verdict and Implications for K176 Ensemble

**K180 Verdict: {candidate_status}**

### Mechanism Summary
- The DOGE tail asymmetry hypothesis is {"CONFIRMED" if st['mean_pnl_bps'] > 0 and lt['sharpe_annualized'] < st['sharpe_annualized'] else "PARTIALLY CONFIRMED / INCONCLUSIVE"}.
- SHORT tail (z>+2): PnL = {st['mean_pnl_bps']:+.2f} bps/event, Sh = {st['sharpe_annualized']:+.4f} (n={st['count']})
- LONG tail (z<-2): PnL = {lt['mean_pnl_bps']:+.2f} bps/event, Sh = {lt['sharpe_annualized']:+.4f} (n={lt['count']})
- Isolation of SHORT tail {"improves" if m_so['sharpe_gross'] > m_agg['sharpe_gross'] else "does not improve"} gross Sharpe vs aggregate ({m_so['sharpe_gross']:+.4f} vs {m_agg['sharpe_gross']:+.4f})

### K181 Recommendation
{result_json['k181_recommendation']}

### If REJECT - Next Steps
1. Investigate DOGE FR premium autocorrelation structure (why does z<-2 fail to predict reversion?)
2. Test DOGE with price-momentum filter: only trade SHORT when recent trend confirms
3. Consider DOGE as a component in a multi-symbol K175 basket with XRP+SUI (managed exposure)
4. Explore DOGE funding-rate-only mean-reversion (without CEX-DEX premium as the signal)
"""

    out_md = ROOT / "wave_k180_doge_tail_asym.md"
    with open(out_md, "w") as f:
        f.write(report)
    print(f"Saved: {out_md}")


if __name__ == "__main__":
    main()
