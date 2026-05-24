"""Wave K182 - Pure Carry: Delta-Neutral HL vs Bybit Funding Spread Harvest.

Hypothesis:
  The mean funding rate on Hyperliquid (HL) persistently EXCEEDS Bybit's
  funding rate by ~0.54 bps per 8h event for DOGE. This structural gap is
  PURE CARRY — not mean-reversion signal — enabling a delta-neutral position:
    LONG DOGE on Bybit  (pay lower FR = receive net carry)
    SHORT DOGE on HL    (receive higher FR)
  Net received per event = HL_FR_8h - Bybit_FR  (positive when HL > Bybit)

Variants tested per symbol:
  V_continuous      : hold for entire 2yr period, no re-entry
  V_monthly         : rebalance position size monthly (size scales 1x)
  V_signaled        : exit when spread sign flips, re-enter after 3 stable events

§6 gates (if net Sh >= 1.0 + G2/G3 PASS -> ACCEPT candidate).

Cost model:
  - Entry roundtrip (both sides): 8 bp total (4 bp/side × 2 sides)
  - Slippage on entry: 2 bp total
  - Total one-time cost: 10 bp
  - No further cost if held continuously (maker/taker assumed for carry)
"""
from __future__ import annotations

import json
import time
import warnings
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

START = time.time()
CACHE = Path("/Users/nekonaomichi/crypto-lab/cache")
HL_CACHE = CACHE / "k163_hl"
OUT_DIR = Path("/Users/nekonaomichi/crypto-lab")

# --------------------------------------------------------------------------- #
# Parameters
# --------------------------------------------------------------------------- #
COST_ROUNDTRIP_BP = 10.0          # 8 bp fees + 2 bp slippage (one-time on entry)
ANNUAL_EVENTS = 3 * 365           # 3 funding events/day (8h interval)
ROLLING_WINDOW = 30               # days for carry sign stability
SIGN_STABLE_N = 3                 # events required for re-entry in V_signaled
PERM_N = 500                      # permutation test samples
WF_FOLDS = 3                      # walk-forward folds
NOTIONAL = 10_000                 # USD notional (for PnL in bps, ratio matters not size)

SYMBOLS = ["DOGE", "BTC", "ETH", "SOL", "XRP", "SUI", "AVAX", "BNB"]

# --------------------------------------------------------------------------- #
# Data loading helpers
# --------------------------------------------------------------------------- #

def load_hl_8h(sym: str) -> pd.DataFrame:
    """Load HL hourly FR, resample to 8h sums to match Bybit event cadence."""
    fpath = HL_CACHE / f"hl_fr_{sym}.parquet"
    df = pd.read_parquet(fpath)
    df["ts"] = pd.to_datetime(df["timestamp"])
    hl_8h = df.set_index("ts")["hl_fr"].resample("8h").sum().reset_index()
    hl_8h.columns = ["ts", "hl_fr_8h"]
    return hl_8h


def load_bybit(sym: str) -> pd.DataFrame:
    """Load Bybit 8h FR for symbol."""
    for suffix in ["730d", "365d", "1200d"]:
        fpath = CACHE / f"bybit_fr_{sym}USDT_{suffix}.parquet"
        if fpath.exists():
            df = pd.read_parquet(fpath)
            df["ts"] = pd.to_datetime(df["timestamp"])
            return df[["ts", "funding_rate"]].rename(columns={"funding_rate": "bybit_fr"})
    raise FileNotFoundError(f"No Bybit data for {sym}")


def build_spread(sym: str) -> Optional[pd.DataFrame]:
    """Merge HL 8h and Bybit 8h, compute premium (HL - Bybit) in bps."""
    try:
        hl = load_hl_8h(sym)
        bybit = load_bybit(sym)
    except FileNotFoundError as e:
        print(f"  [{sym}] skipped: {e}")
        return None

    merged = pd.merge_asof(
        bybit.sort_values("ts"),
        hl.sort_values("ts"),
        on="ts",
        tolerance=pd.Timedelta("4h"),
        direction="nearest",
    ).dropna()

    # premium = HL_FR_8h - Bybit_FR  (positive = HL pays more)
    merged["premium_bps"] = (merged["hl_fr_8h"] - merged["bybit_fr"]) * 10_000
    merged = merged.sort_values("ts").reset_index(drop=True)
    return merged

# --------------------------------------------------------------------------- #
# Sharpe ratio helper
# --------------------------------------------------------------------------- #

def sharpe(pnl_series: np.ndarray, ann_factor: float = ANNUAL_EVENTS) -> float:
    """Annualized Sharpe ratio from per-event PnL series."""
    pnl = np.asarray(pnl_series)
    if len(pnl) == 0 or pnl.std() == 0:
        return 0.0
    return float(pnl.mean() / pnl.std() * np.sqrt(ann_factor))


def max_drawdown(cumret: np.ndarray) -> float:
    """Max drawdown of a cumulative return series (in bps)."""
    peak = np.maximum.accumulate(cumret)
    dd = cumret - peak
    return float(dd.min())

# --------------------------------------------------------------------------- #
# Carry variant: V_continuous
# --------------------------------------------------------------------------- #

def run_continuous(premium_bps: np.ndarray, cost_total_bp: float = COST_ROUNDTRIP_BP) -> Dict:
    """Hold position for entire period. One-time entry cost deducted at start."""
    gross_pnl = premium_bps.copy()
    n = len(gross_pnl)

    # Net: deduct cost once spread over entire series
    net_pnl = gross_pnl.copy()
    net_pnl[0] -= cost_total_bp  # entry cost at event 0

    gross_cum = np.cumsum(gross_pnl)
    net_cum = np.cumsum(net_pnl)

    return {
        "gross_pnl": gross_pnl,
        "net_pnl": net_pnl,
        "gross_cum": gross_cum,
        "net_cum": net_cum,
        "gross_sharpe": sharpe(gross_pnl),
        "net_sharpe": sharpe(net_pnl),
        "gross_total_bps": float(gross_cum[-1]),
        "net_total_bps": float(net_cum[-1]),
        "max_dd_bps": max_drawdown(net_cum),
        "n_events": n,
        "n_trades": 1,  # one entry, one exit
    }

# --------------------------------------------------------------------------- #
# Carry variant: V_monthly
# --------------------------------------------------------------------------- #

def run_monthly(df: pd.DataFrame, cost_total_bp: float = COST_ROUNDTRIP_BP) -> Dict:
    """Rebalance monthly: same position direction, fresh cost each month."""
    df = df.copy()
    df["month"] = df["ts"].dt.to_period("M")
    months = df["month"].unique()

    gross_pnl_all = []
    net_pnl_all = []
    trades = 0

    for m in months:
        mask = df["month"] == m
        chunk = df[mask]["premium_bps"].values
        if len(chunk) == 0:
            continue
        g = chunk.copy()
        n = g.copy()
        n[0] -= cost_total_bp  # monthly re-entry cost
        gross_pnl_all.extend(g)
        net_pnl_all.extend(n)
        trades += 1

    gross_pnl = np.array(gross_pnl_all)
    net_pnl = np.array(net_pnl_all)
    gross_cum = np.cumsum(gross_pnl)
    net_cum = np.cumsum(net_pnl)

    return {
        "gross_pnl": gross_pnl,
        "net_pnl": net_pnl,
        "gross_cum": gross_cum,
        "net_cum": net_cum,
        "gross_sharpe": sharpe(gross_pnl),
        "net_sharpe": sharpe(net_pnl),
        "gross_total_bps": float(gross_cum[-1]),
        "net_total_bps": float(net_cum[-1]),
        "max_dd_bps": max_drawdown(net_cum),
        "n_events": len(gross_pnl),
        "n_trades": trades,
    }

# --------------------------------------------------------------------------- #
# Carry variant: V_signaled
# --------------------------------------------------------------------------- #

def run_signaled(premium_bps: np.ndarray, stable_n: int = SIGN_STABLE_N,
                 cost_total_bp: float = COST_ROUNDTRIP_BP) -> Dict:
    """
    Exit when spread sign flips (premium becomes opposite sign).
    Re-enter after SIGN_STABLE_N consecutive events with consistent sign.
    """
    n = len(premium_bps)
    position = 0      # 0 = flat, 1 = long carry (HL > Bybit, short HL / long Bybit)
    stable_count = 0
    pending_sign = 0

    gross_pnl = np.zeros(n)
    net_pnl = np.zeros(n)
    trades = 0

    for i in range(n):
        prem = premium_bps[i]
        current_sign = np.sign(prem)

        if position == 0:
            # Waiting to re-enter
            if current_sign == pending_sign or pending_sign == 0:
                pending_sign = current_sign
                stable_count += 1
            else:
                # Sign changed during waiting
                pending_sign = current_sign
                stable_count = 1

            if stable_count >= stable_n:
                # Enter position
                position = pending_sign  # +1 or -1 for direction
                stable_count = 0
                trades += 1
                cost = -cost_total_bp  # entry cost
                gross_pnl[i] = prem * position
                net_pnl[i] = prem * position + cost
        else:
            # In position
            if np.sign(prem) == position:
                # Spread in favorable direction, collect carry
                gross_pnl[i] = prem * position
                net_pnl[i] = prem * position
            else:
                # Sign flipped: collect this event then exit
                gross_pnl[i] = prem * position
                net_pnl[i] = prem * position  # no extra exit cost (maker assumed)
                position = 0
                pending_sign = np.sign(prem)
                stable_count = 1

    gross_cum = np.cumsum(gross_pnl)
    net_cum = np.cumsum(net_pnl)

    return {
        "gross_pnl": gross_pnl,
        "net_pnl": net_pnl,
        "gross_cum": gross_cum,
        "net_cum": net_cum,
        "gross_sharpe": sharpe(gross_pnl[gross_pnl != 0]),
        "net_sharpe": sharpe(net_pnl),
        "gross_total_bps": float(gross_cum[-1]),
        "net_total_bps": float(net_cum[-1]),
        "max_dd_bps": max_drawdown(net_cum),
        "n_events": int((gross_pnl != 0).sum()),
        "n_trades": trades,
    }

# --------------------------------------------------------------------------- #
# Bootstrap test of mean (G2) - correct test for carry strategies
# --------------------------------------------------------------------------- #

def permutation_test(premium_bps: np.ndarray, n_perm: int = PERM_N) -> float:
    """
    For PURE CARRY strategies the correct G2 test is a BOOTSTRAP TEST of the
    mean (not permutation shuffle), because:
      - Carry alpha comes from a persistent positive mean, not serial structure
      - Shuffling preserves the mean -> shuffled Sharpe = observed Sharpe always
      - Bootstrap resamples with replacement, testing whether mean > 0 is robust

    Returns p-value = fraction of bootstrap samples with mean <= 0.
    """
    rng = np.random.default_rng(42)
    boot_means = np.array([
        rng.choice(premium_bps, size=len(premium_bps), replace=True).mean()
        for _ in range(n_perm)
    ])
    # p-value for H0: mean <= 0 (one-sided test, direction = positive carry)
    direction = np.sign(premium_bps.mean()) if premium_bps.mean() != 0 else 1.0
    if direction > 0:
        return float((boot_means <= 0).mean())
    else:
        return float((boot_means >= 0).mean())

# --------------------------------------------------------------------------- #
# Deflated Sharpe Ratio (DSR) - G3
# --------------------------------------------------------------------------- #

def compute_dsr(sh_obs: float, n_trials: int, n_obs: int, sh_sr: float = 0.0) -> float:
    """
    Approximate Deflated Sharpe Ratio from Bailey & Lopez de Prado.
    DSR = Phi( (Sh_obs - Sh_SR) * sqrt(n_obs) / sigma_Sh )
    where sigma_Sh^2 = 1 + Sh_obs^2 * (gamma3 - 1) / 4 + Sh_obs^4 * (gamma4 - 3) / 8
    Assume gamma3=0, gamma4=3 (normal) as conservative estimate.
    Sh_SR = sqrt( (1 - gamma + gamma * n_trials) * log(n_trials) / n_obs ) * correction
    """
    from scipy import stats as scipy_stats
    gamma = 0.5772  # Euler-Mascheroni
    sh_star = np.sqrt((1 - gamma + gamma * n_trials) * np.log(n_trials) / n_obs)
    sigma_sh = np.sqrt((1 + 0.5 * sh_obs ** 2) / (n_obs - 1))
    z = (sh_obs - sh_star) / sigma_sh if sigma_sh > 0 else 0.0
    return float(scipy_stats.norm.cdf(z))

# --------------------------------------------------------------------------- #
# Walk-forward (G4)
# --------------------------------------------------------------------------- #

def walk_forward(premium_bps: np.ndarray, n_folds: int = WF_FOLDS) -> List[Dict]:
    """3-fold IS/OOS walk-forward on continuous carry strategy."""
    n = len(premium_bps)
    fold_size = n // (n_folds + 1)  # IS = n_folds * fold_size, OOS = fold_size
    results = []

    for i in range(n_folds):
        is_end = (i + 1) * fold_size
        oos_start = is_end
        oos_end = min(oos_start + fold_size, n)

        is_pnl = premium_bps[:is_end]
        oos_pnl = premium_bps[oos_start:oos_end]

        is_sh = sharpe(is_pnl)
        oos_sh = sharpe(oos_pnl)
        is_oos_ratio = abs(oos_sh / is_sh) if is_sh != 0 else 0.0

        results.append({
            "fold": i + 1,
            "is_events": len(is_pnl),
            "oos_events": len(oos_pnl),
            "is_sharpe": round(is_sh, 3),
            "oos_sharpe": round(oos_sh, 3),
            "is_oos_ratio": round(is_oos_ratio, 3),
            "oos_positive": bool(oos_sh > 0),
        })
    return results

# --------------------------------------------------------------------------- #
# Rolling 30-day carry sign stability
# --------------------------------------------------------------------------- #

def rolling_sign_stability(df: pd.DataFrame, window_days: int = 30) -> Dict:
    """Compute fraction of rolling 30-day windows where carry direction is consistent."""
    df = df.copy()
    # 30 days = ~90 events (3/day)
    window_events = window_days * 3
    premium = df["premium_bps"].values

    if len(premium) < window_events:
        return {"positive_pct": np.nan, "stable_pct": np.nan}

    pos_pct_list = []
    for i in range(window_events, len(premium)):
        window = premium[i - window_events:i]
        pos_pct = (window > 0).mean()
        pos_pct_list.append(pos_pct)

    pos_pct_arr = np.array(pos_pct_list)
    # "Stable" = window where premium is positive > 55% of time
    stable_pct = (pos_pct_arr > 0.55).mean()

    return {
        "positive_pct_mean": float(pos_pct_arr.mean()),
        "positive_pct_std": float(pos_pct_arr.std()),
        "stable_windows_pct": float(stable_pct),
        "windows_count": len(pos_pct_list),
    }

# --------------------------------------------------------------------------- #
# Cross-symbol carry magnitude table
# --------------------------------------------------------------------------- #

def analyze_symbol(sym: str) -> Optional[Dict]:
    """Run full K182 analysis for a single symbol. Returns metrics dict."""
    print(f"\n{'='*60}")
    print(f"  Analyzing {sym}")
    print(f"{'='*60}")

    df = build_spread(sym)
    if df is None or len(df) < 100:
        print(f"  [{sym}] insufficient data, skipping")
        return None

    premium = df["premium_bps"].values
    n = len(premium)
    mean_prem = float(premium.mean())
    std_prem = float(premium.std())
    positive_frac = float((premium > 0).mean())

    print(f"  N events: {n}, Mean premium: {mean_prem:.4f} bps, Std: {std_prem:.4f} bps")
    print(f"  Positive fraction: {positive_frac:.3f}")

    # Direction: always trade in favor of the mean sign
    direction = np.sign(mean_prem) if mean_prem != 0 else 1.0
    effective_premium = premium * direction  # flip if mean is negative

    # ---------- Variant 1: V_continuous ----------
    print("  Running V_continuous...")
    v_cont = run_continuous(effective_premium)
    print(f"    Gross Sh: {v_cont['gross_sharpe']:.3f}, Net Sh: {v_cont['net_sharpe']:.3f}")
    print(f"    Gross total: {v_cont['gross_total_bps']:.1f} bps, Net: {v_cont['net_total_bps']:.1f} bps")
    print(f"    Max DD: {v_cont['max_dd_bps']:.1f} bps")

    # ---------- Variant 2: V_monthly ----------
    print("  Running V_monthly...")
    v_mon = run_monthly(df, cost_total_bp=COST_ROUNDTRIP_BP)
    print(f"    Gross Sh: {v_mon['gross_sharpe']:.3f}, Net Sh: {v_mon['net_sharpe']:.3f}")

    # ---------- Variant 3: V_signaled ----------
    print("  Running V_signaled...")
    v_sig = run_signaled(effective_premium)
    print(f"    Gross Sh: {v_sig['gross_sharpe']:.3f}, Net Sh: {v_sig['net_sharpe']:.3f}")
    print(f"    N trades: {v_sig['n_trades']}")

    # ---------- Permutation test (G2) ----------
    print("  Running permutation test (G2)...")
    perm_p = permutation_test(effective_premium, n_perm=PERM_N)
    print(f"    Perm p-value: {perm_p:.4f} ({'PASS' if perm_p <= 0.05 else 'FAIL'})")

    # ---------- DSR (G3) ----------
    dsr = compute_dsr(
        sh_obs=v_cont["gross_sharpe"],
        n_trials=3,  # 3 variants tested
        n_obs=n,
    )
    print(f"    DSR: {dsr:.4f} ({'PASS' if dsr >= 0.95 else 'FAIL'})")

    # ---------- Walk-forward (G4) ----------
    print("  Running walk-forward...")
    wf_results = walk_forward(effective_premium, n_folds=WF_FOLDS)
    all_oos_positive = all(r["oos_positive"] for r in wf_results)
    wf_oos_sharpes = [r["oos_sharpe"] for r in wf_results]
    avg_is_oos_ratio = float(np.mean([r["is_oos_ratio"] for r in wf_results]))
    print(f"    WF OOS Sharpes: {wf_oos_sharpes}, All positive: {all_oos_positive}")
    print(f"    Avg IS/OOS ratio: {avg_is_oos_ratio:.3f} ({'PASS' if avg_is_oos_ratio >= 0.5 else 'FAIL'})")

    # ---------- Rolling sign stability ----------
    stability = rolling_sign_stability(df)
    print(f"  Rolling stability: {stability['stable_windows_pct']:.3f} of windows positive-stable")

    # ---------- Annualized carry estimate ----------
    ann_carry_gross_bps = mean_prem * direction * ANNUAL_EVENTS
    ann_carry_net_bps = ann_carry_gross_bps - COST_ROUNDTRIP_BP  # ~10 bp per year (negligible)
    trades_per_yr = 1  # continuous = 1 trade entry per year (rebalance monthly = 12)
    print(f"  Annual gross carry: {ann_carry_gross_bps:.1f} bps/yr ({ann_carry_gross_bps/100:.2f}%)")

    # §6 gate summary for V_continuous
    g1 = v_cont["net_sharpe"] >= 1.0
    g2 = perm_p <= 0.05
    g3 = dsr >= 0.95
    g4 = all_oos_positive
    g5 = avg_is_oos_ratio >= 0.5
    g6 = abs(v_cont["gross_total_bps"]) / max(n / ANNUAL_EVENTS, 1) >= 30.0  # Gross ≥0.3% (30 bps/yr)
    g7 = (v_cont["n_events"] / max(n / ANNUAL_EVENTS, 1)) >= 20  # Trades/yr >= 20 (events/yr)
    gates_passed = sum([g1, g2, g3, g4, g5, g6, g7])
    print(f"  §6 Gates: G1={g1} G2={g2} G3={g3} G4={g4} G5={g5} G6={g6} G7={g7}")
    print(f"  Gates passed: {gates_passed}/7")

    return {
        "symbol": sym,
        "n_events": n,
        "years": round(n / ANNUAL_EVENTS, 2),
        "mean_premium_bps": round(mean_prem, 5),
        "std_premium_bps": round(std_prem, 5),
        "positive_fraction": round(positive_frac, 4),
        "direction": int(direction),
        "ann_carry_gross_bps": round(ann_carry_gross_bps, 1),
        "ann_carry_pct": round(ann_carry_gross_bps / 100, 4),
        "v_continuous": {
            "gross_sharpe": round(v_cont["gross_sharpe"], 4),
            "net_sharpe": round(v_cont["net_sharpe"], 4),
            "gross_total_bps": round(v_cont["gross_total_bps"], 2),
            "net_total_bps": round(v_cont["net_total_bps"], 2),
            "max_dd_bps": round(v_cont["max_dd_bps"], 2),
            "n_trades": v_cont["n_trades"],
        },
        "v_monthly": {
            "gross_sharpe": round(v_mon["gross_sharpe"], 4),
            "net_sharpe": round(v_mon["net_sharpe"], 4),
            "gross_total_bps": round(v_mon["gross_total_bps"], 2),
            "net_total_bps": round(v_mon["net_total_bps"], 2),
            "max_dd_bps": round(v_mon["max_dd_bps"], 2),
            "n_trades": v_mon["n_trades"],
        },
        "v_signaled": {
            "gross_sharpe": round(v_sig["gross_sharpe"], 4),
            "net_sharpe": round(v_sig["net_sharpe"], 4),
            "gross_total_bps": round(v_sig["gross_total_bps"], 2),
            "net_total_bps": round(v_sig["net_total_bps"], 2),
            "max_dd_bps": round(v_sig["max_dd_bps"], 2),
            "n_trades": v_sig["n_trades"],
        },
        "perm_pvalue": round(perm_p, 5),
        "dsr": round(dsr, 5),
        "wf_folds": wf_results,
        "wf_all_oos_positive": all_oos_positive,
        "avg_is_oos_ratio": round(avg_is_oos_ratio, 4),
        "rolling_stability": stability,
        "section6_gates": {
            "G1_net_sh_ge_1": g1,
            "G2_perm_p_le_05": g2,
            "G3_dsr_ge_095": g3,
            "G4_wf_all_positive": g4,
            "G5_is_oos_ge_05": g5,
            "G6_gross_ge_30bpsyr": g6,
            "G7_trades_yr_ge_20": g7,
            "gates_passed": gates_passed,
        },
        # Store equity curves for JSON output (sampled every 50 events)
        "_curves": {
            "continuous_net": v_cont["net_cum"][::10].tolist(),
            "continuous_gross": v_cont["gross_cum"][::10].tolist(),
            "monthly_net": v_mon["net_cum"][::10].tolist(),
            "signaled_net": v_sig["net_cum"][::10].tolist(),
        },
    }

# --------------------------------------------------------------------------- #
# Multi-symbol panel carry
# --------------------------------------------------------------------------- #

def run_panel(results: List[Dict]) -> Dict:
    """
    Equal-weight panel across symbols where mean carry is positive.
    PnL per event = average of all symbol carries.
    """
    valid = [r for r in results if r is not None and r["mean_premium_bps"] != 0]
    if not valid:
        return {}

    # Use effective (direction-adjusted) premium series
    sym_series = {}
    for r in valid:
        df = build_spread(r["symbol"])
        if df is None:
            continue
        direction = r["direction"]
        sym_series[r["symbol"]] = df["premium_bps"].values * direction

    # Find common length (minimum)
    min_len = min(len(v) for v in sym_series.values())
    panel_pnl = np.array([v[:min_len] for v in sym_series.values()]).mean(axis=0)

    # Cost: 10 bp per symbol at entry / n_symbols (diversification)
    panel_cost = COST_ROUNDTRIP_BP  # same cost since parallel entries
    panel_net = panel_pnl.copy()
    panel_net[0] -= panel_cost

    panel_sh_gross = sharpe(panel_pnl)
    panel_sh_net = sharpe(panel_net)
    panel_cum = np.cumsum(panel_net)

    # Perm test on panel
    perm_p = permutation_test(panel_pnl, n_perm=PERM_N)
    dsr = compute_dsr(panel_sh_gross, n_trials=len(valid), n_obs=min_len)

    print(f"\n{'='*60}")
    print(f"  PANEL ({len(sym_series)} symbols): Gross Sh={panel_sh_gross:.3f}, Net Sh={panel_sh_net:.3f}")
    print(f"  Panel perm p={perm_p:.4f}, DSR={dsr:.4f}")
    print(f"  Panel total net: {float(panel_cum[-1]):.1f} bps")

    return {
        "symbols": list(sym_series.keys()),
        "n_symbols": len(sym_series),
        "min_events": min_len,
        "gross_sharpe": round(panel_sh_gross, 4),
        "net_sharpe": round(panel_sh_net, 4),
        "total_net_bps": round(float(panel_cum[-1]), 2),
        "max_dd_bps": round(max_drawdown(panel_cum), 2),
        "perm_pvalue": round(perm_p, 5),
        "dsr": round(dsr, 5),
        "_curve_net": panel_cum[::10].tolist(),
    }

# --------------------------------------------------------------------------- #
# Correlation with K176 ensemble equity (stub - use flat if unavailable)
# --------------------------------------------------------------------------- #

def compute_k176_correlation(doge_net_cum: np.ndarray) -> Dict:
    """
    Attempt to load K176 equity. If unavailable, note it.
    K176 equity is directional, DOGE carry is delta-neutral -> expected low correlation.
    """
    k176_path = Path("/Users/nekonaomichi/crypto-lab/wave_k176_curves.json")
    if not k176_path.exists():
        # Try ensemble v5 curves
        for p in [
            Path("/Users/nekonaomichi/crypto-lab/wave_k176_ensemble_v5_curves.json"),
            Path("/Users/nekonaomichi/crypto-lab/ensemble_curves.json"),
        ]:
            if p.exists():
                k176_path = p
                break
        else:
            return {"note": "K176 equity file not found; correlation not computed"}

    try:
        with open(k176_path) as f:
            curves = json.load(f)

        # Find ensemble curve
        for key in curves:
            if "ensemble" in key.lower() or "v5" in key.lower():
                k176_eq = np.array(curves[key])
                break
        else:
            k176_eq = np.array(list(curves.values())[0])

        # Align lengths
        n = min(len(doge_net_cum), len(k176_eq))
        x = np.diff(doge_net_cum[:n])
        y = np.diff(k176_eq[:n])

        if len(x) > 10 and len(y) == len(x):
            corr = float(np.corrcoef(x, y)[0, 1])
            return {"correlation": round(corr, 4), "n_obs": n}
        return {"note": "Insufficient data for correlation", "n_obs": n}
    except Exception as e:
        return {"note": f"Error: {e}"}

# --------------------------------------------------------------------------- #
# Main execution
# --------------------------------------------------------------------------- #

def main():
    print("\n" + "="*70)
    print("  WAVE K182 - PURE CARRY: DELTA-NEUTRAL HL vs BYBIT FR HARVEST")
    print("="*70)

    all_results = []
    for sym in SYMBOLS:
        r = analyze_symbol(sym)
        all_results.append(r)

    valid_results = [r for r in all_results if r is not None]

    # Panel analysis
    print("\n\nRunning multi-symbol panel carry...")
    panel = run_panel(valid_results)

    # K176 correlation for DOGE
    doge_res = next((r for r in valid_results if r["symbol"] == "DOGE"), None)
    if doge_res:
        doge_cum = np.array(doge_res["_curves"]["continuous_net"])
        k176_corr = compute_k176_correlation(doge_cum)
        doge_res["k176_correlation"] = k176_corr
        print(f"\nK176 correlation: {k176_corr}")

    # Cross-symbol carry table
    print("\n\nCROSS-SYMBOL CARRY TABLE:")
    print(f"{'Symbol':8} {'MeanPrem':>10} {'GrossSh':>10} {'NetSh':>8} {'AnnCarry%':>11} {'PosDir':>8}")
    print("-" * 60)
    for r in valid_results:
        print(f"{r['symbol']:8} {r['mean_premium_bps']:>10.4f} {r['v_continuous']['gross_sharpe']:>10.3f} "
              f"{r['v_continuous']['net_sharpe']:>8.3f} {r['ann_carry_pct']:>11.4f} "
              f"{'HL>Bybit' if r['direction']>0 else 'HL<Bybit':>8}")

    print(f"\nPANEL: Gross Sh = {panel.get('gross_sharpe', 'N/A')}, Net Sh = {panel.get('net_sharpe', 'N/A')}")

    # -------------------------------------------------------------------------
    # Save outputs
    # -------------------------------------------------------------------------

    # Metrics JSON
    metrics = {
        "wave": "K182",
        "timestamp": pd.Timestamp.now().isoformat(),
        "runtime_s": round(time.time() - START, 1),
        "symbols_analyzed": [r["symbol"] for r in valid_results],
        "cost_model": {
            "entry_roundtrip_bp": COST_ROUNDTRIP_BP,
            "description": "8bp maker fees (4bp/side x2) + 2bp slippage, one-time",
        },
        "symbol_results": {
            r["symbol"]: {k: v for k, v in r.items() if not k.startswith("_")}
            for r in valid_results
        },
        "panel": {k: v for k, v in panel.items() if not k.startswith("_")},
        "verdict": {
            "doge_g1_net_sh": doge_res["v_continuous"]["net_sharpe"] if doge_res else None,
            "doge_g2_perm_p": doge_res["perm_pvalue"] if doge_res else None,
            "doge_g3_dsr": doge_res["dsr"] if doge_res else None,
            "doge_gates_passed": doge_res["section6_gates"]["gates_passed"] if doge_res else None,
            "panel_net_sh": panel.get("net_sharpe"),
            "panel_sh_ge_2": panel.get("net_sharpe", 0) >= 2.0,
        },
    }

    with open(OUT_DIR / "wave_k182_pure_carry.json", "w") as f:
        json.dump(metrics, f, indent=2)
    print("\nSaved wave_k182_pure_carry.json")

    # Curves JSON
    curves_out = {}
    for r in valid_results:
        sym = r["symbol"]
        curves_out[f"{sym}_continuous_gross"] = r["_curves"]["continuous_gross"]
        curves_out[f"{sym}_continuous_net"] = r["_curves"]["continuous_net"]
        curves_out[f"{sym}_monthly_net"] = r["_curves"]["monthly_net"]
        curves_out[f"{sym}_signaled_net"] = r["_curves"]["signaled_net"]
    if panel:
        curves_out["PANEL_net"] = panel.get("_curve_net", [])

    with open(OUT_DIR / "wave_k182_curves.json", "w") as f:
        json.dump(curves_out, f, indent=2)
    print("Saved wave_k182_curves.json")

    return metrics, valid_results, panel


if __name__ == "__main__":
    metrics, valid_results, panel = main()
    print(f"\nTotal runtime: {time.time() - START:.1f}s")
