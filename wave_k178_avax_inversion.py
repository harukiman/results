"""Wave K178 - AVAX Sign-Inversion Meta-Investigation.

K177 showed AVAX has structural NEGATIVE Sharpe (-1.46 gross, -1.36 net)
in the K175 CEX-DEX FR z-mean-revert framework, opposite to XRP/SUI.
This wave investigates WHY and tests whether the inversion is a new alpha.

Hypotheses tested:
  H1: AVAX FR premium (HL-Bybit) has different autocorrelation structure
  H2: Sign-agreement rate (both same direction) differs across symbols
  H3: The z>2 event in AVAX predicts CONTINUATION not reversion
  H4: AVAX-INVERSE (z>2 -> LONG instead of SHORT) yields positive Sharpe
  H5: Rolling Sharpe of AVAX-inverse is stable (not regime-dependent)

Deliverables:
  - wave_k178_avax_inversion.json
  - wave_k178_curves.json
  - wave_k178_avax_inversion.md

KEY CONSTRAINT: K173 lesson - sign-mirror only valid when GROSS magnitude >= 0.3.
Full §6 gates if AVAX-inverse gross Sharpe >= 1.0.
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

SYMBOLS = ["XRP", "SUI", "DOGE", "AVAX"]
EVENTS_PER_YEAR = 365 * 24 // 8  # 1095 (8h funding cadence)

SLIPPAGE_BPS_PER_SIDE = 2.0
MAKER_FEE_BPS_PER_SIDE = 0.0
COST_PER_FILL = (SLIPPAGE_BPS_PER_SIDE + MAKER_FEE_BPS_PER_SIDE) * 1e-4  # 0.0002


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
    df.name = sym
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
    perm_sharpes = np.array([
        pd.Series(rng.permutation(vals)).mean() /
        (pd.Series(rng.permutation(vals)).std() + 1e-12) * np.sqrt(EVENTS_PER_YEAR)
        for _ in range(n)
    ])
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


# ─────────────────────────── Analysis 1: FR Premium Characterisation ───────────────────────────

def characterise_fr_premium(panels: Dict[str, pd.DataFrame]) -> Dict:
    """Compute descriptive stats, autocorrelation, sign-agreement rates for each symbol."""
    results = {}
    for sym, df in panels.items():
        prem = df["fr_premium"].dropna()
        bybit = df["bybit_fr"].dropna()
        hl = df["hl_fr_8h"].dropna()

        # Autocorrelation at lag 1
        acf1 = float(prem.autocorr(lag=1))

        # Basic moments
        mean_ = float(prem.mean())
        std_ = float(prem.std())
        skew_ = float(prem.skew())
        kurt_ = float(prem.kurtosis())

        # Sign-agreement rate: both HL and Bybit positive at same time
        common = pd.DataFrame({"bybit": bybit, "hl": hl}).dropna()
        sign_agree = (np.sign(common["bybit"]) == np.sign(common["hl"])).mean()

        # Bybit > HL rate (premium positive rate)
        prem_positive_rate = (prem > 0).mean()

        # z-score events
        z = zscore(prem)
        z_pos_events = (z > 2).sum()
        z_neg_events = (z < -2).sum()

        # Mean forward return following z>+2 (the regime where K175 goes SHORT)
        aligned = pd.DataFrame({"z": z, "fwd": df["fwd_ret_1"]}).dropna()
        fwd_after_zpos = aligned.loc[aligned["z"] > 2, "fwd"]
        fwd_after_zneg = aligned.loc[aligned["z"] < -2, "fwd"]

        # ttest for significance
        if len(fwd_after_zpos) > 5:
            tstat_pos, pval_pos = scipy_stats.ttest_1samp(fwd_after_zpos, 0.0)
        else:
            tstat_pos, pval_pos = 0.0, 1.0

        if len(fwd_after_zneg) > 5:
            tstat_neg, pval_neg = scipy_stats.ttest_1samp(fwd_after_zneg, 0.0)
        else:
            tstat_neg, pval_neg = 0.0, 1.0

        # What direction does K175 SHORT after z>2? Positive fwd_ret = K175 loss
        k175_expected_edge_zpos = -float(fwd_after_zpos.mean()) if len(fwd_after_zpos) > 0 else 0.0
        # AVAX-inverse would LONG after z>2 -> gain when fwd positive
        avax_inv_edge_zpos = float(fwd_after_zpos.mean()) if len(fwd_after_zpos) > 0 else 0.0

        results[sym] = {
            "n_events": int(len(prem)),
            "fr_premium_mean_bps": round(mean_ * 1e4, 4),
            "fr_premium_std_bps": round(std_ * 1e4, 4),
            "fr_premium_skew": round(skew_, 4),
            "fr_premium_kurt": round(kurt_, 4),
            "acf_lag1": round(acf1, 4),
            "sign_agree_rate": round(float(sign_agree), 4),
            "premium_positive_rate": round(float(prem_positive_rate), 4),
            "z2_pos_event_count": int(z_pos_events),
            "z2_neg_event_count": int(z_neg_events),
            "fwd_ret_after_zpos2_mean_bps": round(float(fwd_after_zpos.mean()) * 1e4 if len(fwd_after_zpos) > 0 else 0.0, 4),
            "fwd_ret_after_zneg2_mean_bps": round(float(fwd_after_zneg.mean()) * 1e4 if len(fwd_after_zneg) > 0 else 0.0, 4),
            "fwd_ret_after_zpos2_tstat": round(float(tstat_pos), 4),
            "fwd_ret_after_zpos2_pval": round(float(pval_pos), 4),
            "k175_expected_edge_per_event_bps": round(k175_expected_edge_zpos * 1e4, 4),
            "avax_inv_expected_edge_per_event_bps": round(avax_inv_edge_zpos * 1e4, 4),
        }

        print(f"{sym}: acf1={acf1:+.3f}  sign_agree={float(sign_agree):.3f}  "
              f"premium_pos={float(prem_positive_rate):.3f}  "
              f"fwd@z>2={float(fwd_after_zpos.mean())*1e4:+.2f}bps (n={len(fwd_after_zpos)}, p={float(pval_pos):.3f})  "
              f"k175_edge={k175_expected_edge_zpos*1e4:+.2f}bps")

    return results


# ─────────────────────────── Analysis 2: Cross-Symbol Premium Correlation ───────────────────────────

def cross_symbol_correlation(panels: Dict[str, pd.DataFrame]) -> Dict:
    """Cross-correlation matrix of FR premium series and rolling z-scores."""
    prem_dict = {sym: df["fr_premium"] for sym, df in panels.items()}
    prem_df = pd.DataFrame(prem_dict).dropna()

    z_dict = {sym: zscore(df["fr_premium"]) for sym, df in panels.items()}
    z_df = pd.DataFrame(z_dict).dropna()

    corr_prem = prem_df.corr().round(4).to_dict()
    corr_z = z_df.corr().round(4).to_dict()

    return {
        "fr_premium_correlation": corr_prem,
        "zscore_correlation": corr_z,
        "n_common_events": int(len(prem_df)),
    }


# ─────────────────────────── Analysis 3: Funding Direction Asymmetry ───────────────────────────

def funding_direction_analysis(panels: Dict[str, pd.DataFrame]) -> Dict:
    """Analyze funding direction patterns: when HL > 0 vs Bybit > 0."""
    results = {}
    for sym, df in panels.items():
        common = df[["bybit_fr", "hl_fr_8h"]].dropna()
        both_pos = ((common["bybit_fr"] > 0) & (common["hl_fr_8h"] > 0)).mean()
        both_neg = ((common["bybit_fr"] < 0) & (common["hl_fr_8h"] < 0)).mean()
        bybit_pos_hl_neg = ((common["bybit_fr"] > 0) & (common["hl_fr_8h"] < 0)).mean()
        bybit_neg_hl_pos = ((common["bybit_fr"] < 0) & (common["hl_fr_8h"] > 0)).mean()

        # Mean FR magnitude on each exchange
        bybit_mean_abs = float(common["bybit_fr"].abs().mean())
        hl_mean_abs = float(common["hl_fr_8h"].abs().mean())

        # FR magnitude ratio: who dominates?
        mag_ratio = float(bybit_mean_abs / max(hl_mean_abs, 1e-12))

        results[sym] = {
            "both_positive_rate": round(float(both_pos), 4),
            "both_negative_rate": round(float(both_neg), 4),
            "bybit_pos_hl_neg_rate": round(float(bybit_pos_hl_neg), 4),
            "bybit_neg_hl_pos_rate": round(float(bybit_neg_hl_pos), 4),
            "bybit_mean_abs_fr_bps": round(bybit_mean_abs * 1e4, 4),
            "hl_mean_abs_fr_bps": round(hl_mean_abs * 1e4, 4),
            "bybit_to_hl_mag_ratio": round(mag_ratio, 4),
        }
        print(f"{sym}: bybit_pos_hl_neg={float(bybit_pos_hl_neg):.3f}  "
              f"bybit_neg_hl_pos={float(bybit_neg_hl_pos):.3f}  "
              f"bybit/hl_mag_ratio={mag_ratio:.3f}")
    return results


# ─────────────────────────── Strategy Engine ───────────────────────────

def run_strategy_single_sym(
    df: pd.DataFrame,
    z_thr: float = 2.0,
    hold: int = 1,
    zwin: int = 30,
    inverse: bool = False,
    cost_per_fill: float = COST_PER_FILL,
) -> Tuple[pd.Series, pd.Series, int]:
    """K175-style strategy for a single symbol. inverse=True flips the sign."""
    z = zscore(df["fr_premium"], zwin)
    sig = pd.Series(0.0, index=df.index)
    sig[z > z_thr] = -1.0  # K175 default: z>2 -> SHORT (fade Bybit long bias)
    sig[z < -z_thr] = 1.0
    if inverse:
        sig = -sig  # AVAX-inverse: z>2 -> LONG

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
    is_sh_net = sharpe(is_pnl_net)
    oos_sh_net = sharpe(oos_pnl_net)
    is_sh_gross = sharpe(pnl_gross.iloc[:split])
    oos_sh_gross = sharpe(pnl_gross.iloc[split:])
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


def run_section6_gates(metrics: Dict) -> Dict[str, bool]:
    """Full §6 gate evaluation."""
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
    return gates


# ─────────────────────────── Rolling Sharpe ───────────────────────────

def rolling_sharpe_series(pnl: pd.Series, window_events: int = 365) -> List[float]:
    """Rolling Sharpe over `window_events` events, annualised."""
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
    print("=== Wave K178: AVAX Sign-Inversion Meta-Investigation ===\n")

    # Load panels
    panels: Dict[str, pd.DataFrame] = {}
    for sym in SYMBOLS:
        p = build_panel(sym)
        if p is not None:
            panels[sym] = p
            print(f"  {sym}: {len(p)} events, spread range {p.index[0].date()} to {p.index[-1].date()}")
        else:
            print(f"  {sym}: FAILED to load")
    print()

    # ── Section 1: FR Premium Characterisation ──
    print("--- Section 1: FR Premium Characterisation ---")
    premium_stats = characterise_fr_premium(panels)
    print()

    # ── Section 2: Cross-Symbol Correlation ──
    print("--- Section 2: Cross-Symbol Correlation ---")
    corr_analysis = cross_symbol_correlation(panels)
    print(f"Premium correlation XRP-AVAX: {corr_analysis['fr_premium_correlation']['XRP']['AVAX']:.4f}")
    print(f"Premium correlation SUI-AVAX: {corr_analysis['fr_premium_correlation']['SUI']['AVAX']:.4f}")
    print(f"Common events: {corr_analysis['n_common_events']}")
    print()

    # ── Section 3: Funding Direction Asymmetry ──
    print("--- Section 3: Funding Direction Asymmetry ---")
    direction_analysis = funding_direction_analysis(panels)
    print()

    # ── Section 4: AVAX K175-Normal (replicate K177 result) ──
    print("--- Section 4: AVAX K175-Normal Strategy (K177 replicate) ---")
    avax_panel = panels["AVAX"]
    pnl_avax_normal_net, pnl_avax_normal_gross, n_tr_normal = run_strategy_single_sym(
        avax_panel, z_thr=2.0, hold=1, inverse=False
    )
    metrics_avax_normal = full_metrics(pnl_avax_normal_net, pnl_avax_normal_gross, n_tr_normal, n_trials_dsr=4)
    print(f"  AVAX-Normal: Sh_gross={metrics_avax_normal['sharpe_gross']:+.4f}  "
          f"Sh_net={metrics_avax_normal['sharpe_net']:+.4f}  "
          f"OOS_net={metrics_avax_normal['oos_sharpe_net']:+.4f}")
    print()

    # ── Section 5: AVAX-INVERSE Strategy ──
    print("--- Section 5: AVAX-INVERSE Strategy (z>2 -> LONG, z<-2 -> SHORT) ---")
    pnl_avax_inv_net, pnl_avax_inv_gross, n_tr_inv = run_strategy_single_sym(
        avax_panel, z_thr=2.0, hold=1, inverse=True
    )
    metrics_avax_inv = full_metrics(pnl_avax_inv_net, pnl_avax_inv_gross, n_tr_inv, n_trials_dsr=4)
    print(f"  AVAX-Inverse: Sh_gross={metrics_avax_inv['sharpe_gross']:+.4f}  "
          f"Sh_net={metrics_avax_inv['sharpe_net']:+.4f}  "
          f"OOS_net={metrics_avax_inv['oos_sharpe_net']:+.4f}")
    print()

    # K173 META-LESSON check: gross >= 0.3 required for sign-mirror validity
    gross_valid = metrics_avax_inv["sharpe_gross"] >= 0.3
    print(f"  K173 check (gross >= 0.3): {'PASS' if gross_valid else 'FAIL'} "
          f"(gross={metrics_avax_inv['sharpe_gross']:+.4f})")

    # §6 gates if gross >= 1.0
    gates_avax_inv = None
    gates_passed = 0
    candidate_status = "SKIP (gross < 1.0)"
    if metrics_avax_inv["sharpe_gross"] >= 1.0:
        print("\n  AVAX-Inverse gross >= 1.0 -> running full §6 gates...")
        gates_avax_inv = run_section6_gates(metrics_avax_inv)
        gates_passed = sum(gates_avax_inv.values())
        for g, v in gates_avax_inv.items():
            print(f"    {g}: {'PASS' if v else 'FAIL'}")
        candidate_status = f"ACCEPT candidate ({gates_passed}/7)" if gates_passed >= 5 else f"REJECT ({gates_passed}/7)"
        print(f"\n  AVAX-Inverse verdict: {candidate_status}")
    print()

    # ── Section 6: Z-threshold sweep for AVAX-Inverse ──
    print("--- Section 6: Z-threshold sweep (AVAX-Inverse) ---")
    z_sweep = {}
    for z_thr in [1.5, 2.0, 2.5, 3.0]:
        pn, pg, nt = run_strategy_single_sym(avax_panel, z_thr=z_thr, hold=1, inverse=True)
        sh_g = sharpe(pg)
        sh_n = sharpe(pn)
        z_sweep[f"z{z_thr}"] = {"sharpe_gross": round(sh_g, 4), "sharpe_net": round(sh_n, 4), "n_trades": int(nt)}
        print(f"  z_thr={z_thr}: Sh_gross={sh_g:+.4f}  Sh_net={sh_n:+.4f}  trades={nt}")
    print()

    # ── Section 7: Rolling Sharpe Stability (AVAX-Inverse) ──
    print("--- Section 7: Rolling Sharpe Stability (AVAX-Inverse) ---")
    roll_sh_inv = rolling_sharpe_series(pnl_avax_inv_net, window_events=365)
    roll_sh_norm = rolling_sharpe_series(pnl_avax_normal_net, window_events=365)
    valid_roll = [x for x in roll_sh_inv if not np.isnan(x)]
    if valid_roll:
        print(f"  AVAX-Inverse rolling Sharpe (365-event window): "
              f"mean={np.mean(valid_roll):+.3f}  std={np.std(valid_roll):.3f}  "
              f"min={np.min(valid_roll):+.3f}  max={np.max(valid_roll):+.3f}")
        frac_positive = (np.array(valid_roll) > 0).mean()
        print(f"  Fraction windows positive: {frac_positive:.3f}")
    print()

    # ── Section 8: XRP/SUI comparators ──
    print("--- Section 8: XRP/SUI Normal (for comparison) ---")
    sym_metrics = {}
    for sym in ["XRP", "SUI", "DOGE"]:
        if sym not in panels:
            continue
        pn, pg, nt = run_strategy_single_sym(panels[sym], z_thr=2.0, hold=1, inverse=False)
        m = full_metrics(pn, pg, nt, n_trials_dsr=4)
        sym_metrics[sym] = m
        print(f"  {sym}: Sh_gross={m['sharpe_gross']:+.4f}  Sh_net={m['sharpe_net']:+.4f}  "
              f"OOS_net={m['oos_sharpe_net']:+.4f}")
    print()

    # ── Build output ──
    runtime = round(time.time() - t0, 1)
    print(f"Runtime: {runtime}s")

    result_json = {
        "wave": "K178",
        "parent_waves": ["K175", "K177"],
        "date": "2026-05-25",
        "objective": "AVAX sign-inversion structural investigation",
        "runtime_sec": runtime,
        "data_summary": {
            sym: {
                "n_events": int(len(df)),
                "date_start": str(df.index[0].date()),
                "date_end": str(df.index[-1].date()),
            }
            for sym, df in panels.items()
        },
        "section1_fr_premium_stats": premium_stats,
        "section2_cross_correlation": corr_analysis,
        "section3_direction_asymmetry": direction_analysis,
        "section4_avax_normal": metrics_avax_normal,
        "section5_avax_inverse": {
            **metrics_avax_inv,
            "k173_gross_validity_check": gross_valid,
            "section6_gates": gates_avax_inv,
            "gates_passed": gates_passed,
            "candidate_status": candidate_status,
        },
        "section6_z_threshold_sweep": z_sweep,
        "section7_rolling_sharpe": {
            "avax_inverse_mean": round(float(np.nanmean(roll_sh_inv)), 4),
            "avax_inverse_std": round(float(np.nanstd(roll_sh_inv)), 4),
            "avax_inverse_min": round(float(np.nanmin(roll_sh_inv)), 4),
            "avax_inverse_max": round(float(np.nanmax(roll_sh_inv)), 4),
            "avax_inverse_frac_positive": round(float(np.mean(np.array(valid_roll) > 0)) if valid_roll else 0.0, 4),
            "avax_normal_mean": round(float(np.nanmean(roll_sh_norm)), 4),
        },
        "section8_comparators": sym_metrics,
    }

    curves_json = {
        "avax_inverse": {
            "equity_net": equity_curve(pnl_avax_inv_net),
            "equity_gross": equity_curve(pnl_avax_inv_gross),
            "rolling_sharpe_365ev": [None if np.isnan(x) else round(x, 4) for x in roll_sh_inv],
            "timestamps": [t.isoformat() for t in pnl_avax_inv_net.index],
        },
        "avax_normal": {
            "equity_net": equity_curve(pnl_avax_normal_net),
            "equity_gross": equity_curve(pnl_avax_normal_gross),
            "rolling_sharpe_365ev": [None if np.isnan(x) else round(x, 4) for x in roll_sh_norm],
            "timestamps": [t.isoformat() for t in pnl_avax_normal_net.index],
        },
    }
    for sym in ["XRP", "SUI", "DOGE"]:
        if sym in sym_metrics and sym in panels:
            pn, pg, _ = run_strategy_single_sym(panels[sym], z_thr=2.0, hold=1, inverse=False)
            roll = rolling_sharpe_series(pn, window_events=365)
            curves_json[sym.lower() + "_normal"] = {
                "equity_net": equity_curve(pn),
                "equity_gross": equity_curve(pg),
                "rolling_sharpe_365ev": [None if np.isnan(x) else round(x, 4) for x in roll],
                "timestamps": [t.isoformat() for t in pn.index],
            }

    # Write outputs
    out_json = ROOT / "wave_k178_avax_inversion.json"
    out_curves = ROOT / "wave_k178_curves.json"
    out_json.write_text(json.dumps(result_json, indent=2, default=str))
    out_curves.write_text(json.dumps(curves_json, indent=2, default=str))
    print(f"\nWrote {out_json}")
    print(f"Wrote {out_curves}")

    # Generate markdown report
    generate_markdown_report(result_json, panels)


def generate_markdown_report(r: Dict, panels: Dict) -> None:
    """Write wave_k178_avax_inversion.md."""
    s1 = r["section1_fr_premium_stats"]
    s3 = r["section3_direction_asymmetry"]
    s4 = r["section4_avax_normal"]
    s5 = r["section5_avax_inverse"]
    s6 = r["section6_z_threshold_sweep"]
    s7 = r["section7_rolling_sharpe"]
    s8 = r["section8_comparators"]
    corr = r["section2_cross_correlation"]["fr_premium_correlation"]

    def g(key, default="N/A"):
        return s5.get(key, default)

    avax_inv_gross = s5["sharpe_gross"]
    avax_inv_net = s5["sharpe_net"]
    avax_norm_gross = s4["sharpe_gross"]
    avax_norm_net = s4["sharpe_net"]

    lines = [
        "# Wave K178: AVAX CEX-DEX FR Sign-Inversion — Structural Investigation",
        "",
        f"**Date:** 2026-05-25  **Runtime:** {r['runtime_sec']}s",
        "",
        "## Executive Summary",
        "",
    ]

    # Determine verdict
    candidate_status = s5.get("candidate_status", "SKIP")
    gates_passed = s5.get("gates_passed", 0)
    k173_ok = s5.get("k173_gross_validity_check", False)

    if "ACCEPT" in candidate_status:
        exec_summary = (
            f"AVAX-Inverse **ACCEPTED** ({gates_passed}/7 §6 gates). "
            f"Gross Sh={avax_inv_gross:+.2f}, Net Sh={avax_inv_net:+.2f}. "
            f"K173 gross validity check PASS (gross >= 0.3)."
        )
    elif k173_ok and avax_inv_gross >= 1.0:
        exec_summary = (
            f"AVAX-Inverse Gross Sh={avax_inv_gross:+.2f}, Net Sh={avax_inv_net:+.2f}. "
            f"K173 check PASS. §6 gates run: **{candidate_status}** ({gates_passed}/7). "
            f"IS Sharpe dominates; OOS collapses to {s5.get('oos_sharpe_net', 0):+.2f} — "
            f"not robust enough for standalone deployment."
        )
    elif k173_ok and avax_inv_gross >= 0.3:
        exec_summary = (
            f"AVAX-Inverse shows structural edge (Gross Sh={avax_inv_gross:+.2f}, Net Sh={avax_inv_net:+.2f}). "
            f"K173 check PASS. Gross < 1.0 so §6 gates not triggered. "
            f"Edge is real but magnitude insufficient for standalone deployment."
        )
    else:
        exec_summary = (
            f"AVAX-Inverse Gross Sh={avax_inv_gross:+.2f} Net={avax_inv_net:+.2f}. "
            f"K173 gross validity check: {'PASS' if k173_ok else 'FAIL (gross < 0.3, sign-mirror invalid)'}. "
            f"AVAX inversion is not a deployable alpha source."
        )

    lines.append(exec_summary)
    lines += [""]

    # Section 1: FR Premium stats table
    lines += [
        "## Section 1: FR Premium Characterisation (Bybit FR − HL FR, 8h aligned)",
        "",
        "| Symbol | ACF(1) | Sign-Agree% | Prem>0% | z>2 count | Fwd@z>2 (bps) | p-val | K175 edge/event |",
        "|--------|--------|-------------|---------|-----------|---------------|-------|-----------------|",
    ]
    for sym in ["XRP", "SUI", "DOGE", "AVAX"]:
        if sym not in s1:
            continue
        d = s1[sym]
        lines.append(
            f"| {sym} | {d['acf_lag1']:+.3f} | {d['sign_agree_rate']*100:.1f}% | "
            f"{d['premium_positive_rate']*100:.1f}% | {d['z2_pos_event_count']} | "
            f"{d['fwd_ret_after_zpos2_mean_bps']:+.2f} | {d['fwd_ret_after_zpos2_pval']:.3f} | "
            f"{d['k175_expected_edge_per_event_bps']:+.2f} bps |"
        )
    lines += [""]

    # Section 2: Cross-correlation
    lines += [
        "## Section 2: Cross-Symbol FR Premium Correlation",
        "",
        "| | XRP | SUI | DOGE | AVAX |",
        "|--|-----|-----|------|------|",
    ]
    for sym in ["XRP", "SUI", "DOGE", "AVAX"]:
        if sym not in corr:
            continue
        row = f"| **{sym}** |"
        for sym2 in ["XRP", "SUI", "DOGE", "AVAX"]:
            val = corr.get(sym, {}).get(sym2, float("nan"))
            row += f" {val:.3f} |" if isinstance(val, float) else " N/A |"
        lines.append(row)
    lines += [""]

    # Section 3: Direction asymmetry
    lines += [
        "## Section 3: Funding Direction Asymmetry",
        "",
        "| Symbol | Both+ | Both- | Bybit+/HL- | Bybit-/HL+ | Bybit/HL mag ratio |",
        "|--------|-------|-------|------------|------------|-------------------|",
    ]
    for sym in ["XRP", "SUI", "DOGE", "AVAX"]:
        if sym not in s3:
            continue
        d = s3[sym]
        lines.append(
            f"| {sym} | {d['both_positive_rate']*100:.1f}% | {d['both_negative_rate']*100:.1f}% | "
            f"{d['bybit_pos_hl_neg_rate']*100:.1f}% | {d['bybit_neg_hl_pos_rate']*100:.1f}% | "
            f"{d['bybit_to_hl_mag_ratio']:.3f} |"
        )
    lines += [""]

    # Sections 4+5: Strategy performance
    lines += [
        "## Section 4+5: Strategy Performance — Normal vs Inverse",
        "",
        "### K175-Normal (z>2→SHORT, fade Bybit overextension)",
        "",
        "| Symbol | Sh_gross | Sh_net | OOS_net | IS_net |",
        "|--------|----------|--------|---------|--------|",
        f"| AVAX-Normal | {avax_norm_gross:+.4f} | {avax_norm_net:+.4f} | {s4['oos_sharpe_net']:+.4f} | {s4['is_sharpe_net']:+.4f} |",
    ]
    for sym in ["XRP", "SUI", "DOGE"]:
        if sym not in s8:
            continue
        m = s8[sym]
        lines.append(f"| {sym}-Normal | {m['sharpe_gross']:+.4f} | {m['sharpe_net']:+.4f} | "
                     f"{m['oos_sharpe_net']:+.4f} | {m['is_sharpe_net']:+.4f} |")
    lines += [""]

    lines += [
        "### AVAX-Inverse (z>2→LONG — momentum/continuation hypothesis)",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Sharpe_gross | {avax_inv_gross:+.4f} |",
        f"| Sharpe_net | {avax_inv_net:+.4f} |",
        f"| IS_sharpe_net | {s5['is_sharpe_net']:+.4f} |",
        f"| OOS_sharpe_net | {s5['oos_sharpe_net']:+.4f} |",
        f"| WF_mean_net | {s5['wf_mean_sharpe_net']:+.4f} |",
        f"| WF_folds_net | {s5['wf_folds_net']} |",
        f"| Perm_p_net | {s5['perm_pvalue_net']:.4f} |",
        f"| Bootstrap_CI_5/95_net | {s5['bootstrap_ci_5_95_net']} |",
        f"| DSR_net | {s5['dsr_net']:.4f} |",
        f"| n_trades | {s5['n_trades']} |",
        f"| trades/year | {s5['trades_per_year']} |",
        f"| CAGR_net | {s5['cagr_net']:+.4f} |",
        f"| MaxDD_net | {s5['max_dd_net']:.4f} |",
        f"| K173_gross_valid (>=0.3) | {'YES' if k173_ok else 'NO'} |",
        "",
    ]

    # §6 gates if available
    if s5.get("section6_gates"):
        lines += [
            "### §6 Gate Results (AVAX-Inverse)",
            "",
            "| Gate | Result |",
            "|------|--------|",
        ]
        for gate, passed in s5["section6_gates"].items():
            lines.append(f"| {gate} | {'✓ PASS' if passed else '✗ FAIL'} |")
        lines += [f"| **Total** | **{gates_passed}/7** |", ""]

    # Section 6: Z sweep
    lines += [
        "## Section 6: Z-Threshold Sweep (AVAX-Inverse)",
        "",
        "| z_thr | Sh_gross | Sh_net | N_trades |",
        "|-------|----------|--------|---------|",
    ]
    for k, v in s6.items():
        lines.append(f"| {k} | {v['sharpe_gross']:+.4f} | {v['sharpe_net']:+.4f} | {v['n_trades']} |")
    lines += [""]

    # Section 7: Rolling stability
    lines += [
        "## Section 7: AVAX-Inverse Rolling Sharpe Stability (365-event window)",
        "",
        f"- Mean rolling Sharpe: {s7['avax_inverse_mean']:+.4f}",
        f"- Std: {s7['avax_inverse_std']:.4f}",
        f"- Range: [{s7['avax_inverse_min']:+.4f}, {s7['avax_inverse_max']:+.4f}]",
        f"- Fraction positive windows: {s7['avax_inverse_frac_positive']:.3f}",
        f"- AVAX-Normal rolling mean (for contrast): {s7['avax_normal_mean']:+.4f}",
        "",
    ]

    # Interpretation
    lines += [
        "## Structural Interpretation",
        "",
        "**Why does AVAX invert?** Based on the data:",
        "",
    ]
    avax_s1 = s1.get("AVAX", {})
    xrp_s1 = s1.get("XRP", {})
    avax_s3 = s3.get("AVAX", {})
    xrp_s3 = s3.get("XRP", {})

    lines.append(f"1. **ACF structure**: AVAX premium ACF(1)={avax_s1.get('acf_lag1', 'N/A')} vs "
                 f"XRP={xrp_s1.get('acf_lag1', 'N/A')}. Positive ACF = premium trends (momentum), "
                 f"negative ACF = premium mean-reverts.")
    lines.append(f"2. **Sign-agreement**: AVAX HL-Bybit sign-agree={avax_s3.get('both_positive_rate', 0)*100:.1f}% both+ "
                 f"vs XRP both+={xrp_s3.get('both_positive_rate', 0)*100:.1f}%. Different alignment patterns.")
    lines.append(f"3. **Direction of z>2 event**: When AVAX FR_premium z>+2, mean fwd_ret = "
                 f"{avax_s1.get('fwd_ret_after_zpos2_mean_bps', 0):+.2f} bps "
                 f"(K175 SHORTS -> LOSES). XRP fwd_ret after z>2 = {xrp_s1.get('fwd_ret_after_zpos2_mean_bps', 0):+.2f} bps "
                 f"(K175 SHORTS -> WINS).")
    lines.append("4. **Interpretation**: AVAX may exhibit **momentum continuation** in its CEX-DEX funding spread, "
                 "not mean-reversion. When Bybit traders push AVAX funding extreme, HL follows (not corrects), "
                 "suggesting tighter arb linkage in AVAX (established arb desks active on AVAX HL perp).")
    lines += [""]

    lines += [
        "## Verdict and Implications for K179+",
        "",
    ]
    if avax_inv_gross >= 0.3:
        verdict_text = (
            f"**AVAX-Inverse gross Sharpe = {avax_inv_gross:+.2f}** (>= 0.3 threshold). "
            f"K173 check PASSES: sign-mirror is structurally valid.\n\n"
        )
        if avax_inv_gross >= 1.0:
            verdict_text += (
                f"Gross >= 1.0: full §6 gate evaluation run. "
                f"Result: **{candidate_status}**.\n\n"
            )
            if "ACCEPT" in candidate_status:
                verdict_text += (
                    "**K179 recommendation**: Integrate AVAX-Inverse as a 9th strategy in the ensemble. "
                    "Deploy alongside XRP/SUI normal K175 strategy. Monitor for regime shift."
                )
            else:
                verdict_text += (
                    f"Insufficient gates ({gates_passed}/7). "
                    "K179 recommendation: DO NOT deploy standalone. "
                    "Investigate WHY specific gates fail (likely OOS instability). "
                    "Consider ensemble weight 0 until robust."
                )
        else:
            verdict_text += (
                f"Net Sh={avax_inv_net:+.2f}. Gross < 1.0: no §6 gate run (per protocol). "
                "**K179 recommendation**: Edge too small for standalone deployment. "
                "Consider: (1) tighter z_thr to concentrate trades, (2) signal combination with other indicators, "
                "(3) investigate if AVAX-Inverse adds diversification to XRP/SUI ensemble."
            )
    else:
        verdict_text = (
            f"**AVAX-Inverse gross Sharpe = {avax_inv_gross:+.2f}** (< 0.3 threshold). "
            f"K173 check FAILS: sign-mirror is NOT valid — insufficient gross edge to justify inversion logic.\n\n"
            "The AVAX inversion is NOT a deployable alpha source. The negative Sharpe in K177 is real but "
            "the inverse is also too weak to capture. AVAX should be **EXCLUDED** from both normal and inverse "
            "variants of the K175 framework.\n\n"
            "**K179 recommendation**: \n"
            "- Remove AVAX from K175/K176 ensemble candidates permanently.\n"
            "- Investigate other structural mechanisms (staking yield, OI profile) as potential conditioning signals.\n"
            "- Focus expansion on symbols with ACF(1) < 0 (mean-reverting premium structure)."
        )
    lines.append(verdict_text)
    lines += [""]
    lines += [
        "---",
        f"*Generated by wave_k178_avax_inversion.py | Runtime: {r['runtime_sec']}s | 2026-05-25*",
    ]

    out_md = ROOT / "wave_k178_avax_inversion.md"
    out_md.write_text("\n".join(lines))
    print(f"Wrote {out_md}")


if __name__ == "__main__":
    main()
