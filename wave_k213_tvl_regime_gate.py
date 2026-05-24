"""Wave K213 — Ethena TVL Rule-Based Regime Gate for K198 (v6.6 candidate).

Objective:
  Apply K211 prescription Option B: use Ethena TVL as a rule-based regime gate,
  bypassing ML estimation entirely. Three variants tested:

  Variant A (K213a): Defensive halt
    When eth_tvl_change_30d < -0.15 → set V_rev_carry & V_fwd_carry weights = 0,
    redistribute to remaining strategies proportionally.

  Variant B (K213b): Offensive boost
    When eth_tvl_change_30d > +0.10 → boost V_rev_carry to CARRY_REV_CAP max
    (consistent with K206 Variant B which showed +0.0587 OOS Sh lift).

  Variant C (K213c): Both rules combined.

Background:
  - K198 v6.5 production: Ridge ML allocator, 51 features, OOS Sh 10.28, WF min 6.57
  - K207 REJECT: global Ethena features into ML, OOS Sh 8.87
  - K211 REJECT: carry-specific interaction, OOS Sh 8.81 (real signal, suppressed by
    ML estimation variance + cap binding)
  - K206 finding: TVL lag-corr negative at all lags 0-14d, but Variant B (boost on TVL
    growth) showed positive carry lift — interpreted as TVL growth capturing carry
    magnitude or risk environment rather than direction alone.

Implementation:
  1. Load K198 WF weight series (already computed, bypass re-running ML)
  2. Load Ethena TVL, compute daily eth_tvl_change_30d (7d lag for look-ahead safety)
  3. Apply rule overrides to K198's daily weights
  4. Recompute returns from modified weights × strategy returns
  5. Walk-forward fold analysis + OOS comparison

Acceptance:
  Best variant OOS Sh >= 10.28 (K198)
  MaxDD <= -0.0053 (K198)
  WF min >= 6.57 (K198)
  Rule firing rate <= 30%

Runtime: <12 min
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
BASE   = Path("/Users/nekonaomichi/crypto-lab")
CACHE  = BASE / "cache"

TRADING_DAYS = 365
OOS_FRAC     = 0.30
N_FOLDS      = 4

# K198 v6.5 acceptance baseline
K198_OOS_SH  = 10.28
K198_OOS_DD  = -0.0053
K198_WF_MEAN = 7.91
K198_WF_MIN  = 6.57

# K211 reference (rejected)
K211_OOS_SH  = 8.81

# Carry strategy caps from K198
CARRY_FWD_CAP  = 0.10   # K198 forward cap
CARRY_REV_CAP  = 0.10   # K198 reverse cap

# TVL regime thresholds (from K211 prescription)
TVL_DROP_THRESHOLD  = -0.15   # Variant A: halt on TVL decline < -15%
TVL_GROW_THRESHOLD  = +0.10   # Variant B: boost on TVL growth > +10%

# Anti-look-ahead lag for TVL signal
TVL_LAG_DAYS = 7

# Strategy names (K198 order)
STRATEGY_NAMES = [
    "v4.1", "V1", "K114", "K116", "K121", "K133",
    "K147", "K175_DAR", "V_fwd_carry", "V_rev_carry",
]


# ─────────────────────────────────────────────────────────────────────────────
# Metrics
# ─────────────────────────────────────────────────────────────────────────────

def sharpe_d(r: np.ndarray) -> float:
    r = np.asarray(r, dtype=float)
    if len(r) < 2 or r.std(ddof=1) == 0:
        return 0.0
    return float(r.mean() / r.std(ddof=1) * math.sqrt(TRADING_DAYS))


def max_dd_d(r: np.ndarray) -> float:
    eq = np.cumprod(1.0 + np.asarray(r, dtype=float))
    peak = np.maximum.accumulate(eq)
    return float((eq / peak - 1.0).min())


def sortino_d(r: np.ndarray) -> float:
    dn = r[r < 0]
    if len(dn) < 2 or dn.std(ddof=1) == 0:
        return 0.0
    return float(r.mean() / dn.std(ddof=1) * math.sqrt(TRADING_DAYS))


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


def wf_fold_sharpes(pnl: np.ndarray, n_folds: int = N_FOLDS) -> dict:
    n = len(pnl)
    fold_size = n // n_folds
    sharpes = []
    for i in range(n_folds):
        start = i * fold_size
        end   = start + fold_size if i < n_folds - 1 else n
        sharpes.append(round(sharpe_d(pnl[start:end]), 4))
    return {
        "fold_sharpes": sharpes,
        "mean": round(float(np.mean(sharpes)), 4),
        "min":  round(float(np.min(sharpes)), 4),
        "max":  round(float(np.max(sharpes)), 4),
        "std":  round(float(np.std(sharpes)), 4),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Data loading
# ─────────────────────────────────────────────────────────────────────────────

def load_component_returns() -> pd.DataFrame:
    """Load all 10 K196/K198 component daily return series."""
    with open(BASE / "wave_k192_curves.json") as f:
        k192 = json.load(f)
    k192_dates = pd.to_datetime(k192["dates"])

    component_map = {
        "v4.1":     "K188_v4.1",
        "V1":       "K188_V1",
        "K114":     "K188_K114",
        "K116":     "K188_K116",
        "K121":     "K188_K121",
        "K133":     "K188_K133",
        "K147":     "K188_K147",
        "K175_DAR": "K175_DAR_a_win300_net",
    }
    base_df = pd.DataFrame(index=k192_dates)
    for col_name, curve_key in component_map.items():
        eq = np.array(k192["series"][curve_key], dtype=float)
        prev = np.r_[1.0, eq[:-1]]
        base_df[col_name] = eq / prev - 1.0
    base_df.index.name = "date"

    with open(BASE / "wave_k195_curves.json") as f:
        k195 = json.load(f)
    k195_dates = pd.to_datetime(k195["panel_dates"])
    fwd_eq = np.array(k195["series"]["V_eq_w"], dtype=float)
    fwd_ret = pd.Series(
        np.r_[fwd_eq[0] - 1.0, fwd_eq[1:] / fwd_eq[:-1] - 1.0],
        index=k195_dates, name="V_fwd_carry",
    )

    with open(BASE / "wave_k196_curves.json") as f:
        k196 = json.load(f)
    k196_dates = pd.to_datetime(k196["panel_dates"])
    rev_eq = np.array(k196["series"]["V_rev_eq_w"], dtype=float)
    rev_ret = pd.Series(
        np.r_[rev_eq[0] - 1.0, rev_eq[1:] / rev_eq[:-1] - 1.0],
        index=k196_dates, name="V_rev_carry",
    )

    all_start = max(base_df.index[0], fwd_ret.index[0], rev_ret.index[0])
    all_end   = min(base_df.index[-1], fwd_ret.index[-1], rev_ret.index[-1])
    base_trimmed = base_df[(base_df.index >= all_start) & (base_df.index <= all_end)]
    fwd_trimmed  = fwd_ret[(fwd_ret.index >= all_start) & (fwd_ret.index <= all_end)]
    rev_trimmed  = rev_ret[(rev_ret.index >= all_start) & (rev_ret.index <= all_end)]

    df = pd.concat([base_trimmed, fwd_trimmed, rev_trimmed], axis=1).dropna()
    print(f"  Component returns: {df.shape[0]} days x {df.shape[1]} strategies")
    print(f"  Date range: {df.index[0].date()} -> {df.index[-1].date()}")
    return df


def load_k198_weights() -> pd.DataFrame:
    """
    Load K198 walk-forward weight trajectory from wave_k198_curves.json.
    Returns DataFrame with dates as index and strategy columns.
    """
    with open(BASE / "wave_k198_curves.json") as f:
        curves = json.load(f)

    dates = pd.to_datetime(curves["weight_trajectory_dates"])
    wt = curves["weight_trajectory"]   # dict: strategy -> list of floats
    weights_df = pd.DataFrame(wt, index=dates)
    weights_df.index.name = "date"
    print(f"  K198 weight trajectory: {len(dates)} days, "
          f"{dates[0].date()} -> {dates[-1].date()}")
    print(f"  Strategies: {list(wt.keys())}")
    return weights_df


def load_ethena_tvl(lag_days: int = TVL_LAG_DAYS) -> Tuple[pd.Series, pd.Series]:
    """
    Load Ethena TVL cache, compute:
      eth_tvl_change_30d: 30-day % change (lagged by lag_days to prevent look-ahead)
      eth_tvl_raw:        raw TVL for reporting
    """
    tvl_df = pd.read_parquet(CACHE / "ethena_tvl_daily.parquet")
    tvl = tvl_df["tvl"]

    if tvl.index.tz is not None:
        tvl.index = tvl.index.tz_localize(None)

    eth_change_30d = tvl.pct_change(30)
    eth_change_30d = eth_change_30d.shift(lag_days)   # anti-look-ahead
    eth_change_30d.name = "eth_tvl_change_30d"

    print(f"  Ethena TVL: {len(tvl)} rows, "
          f"{tvl.index[0].date()} -> {tvl.index[-1].date()}")
    print(f"  eth_tvl_change_30d (lag={lag_days}d): "
          f"mean={eth_change_30d.dropna().mean():.4f}, "
          f"std={eth_change_30d.dropna().std():.4f}")
    print(f"  TVL drop regime (< {TVL_DROP_THRESHOLD}): "
          f"{(eth_change_30d.dropna() < TVL_DROP_THRESHOLD).sum()} days")
    print(f"  TVL grow regime (> {TVL_GROW_THRESHOLD}): "
          f"{(eth_change_30d.dropna() > TVL_GROW_THRESHOLD).sum()} days")

    return eth_change_30d, tvl


# ─────────────────────────────────────────────────────────────────────────────
# Rule-based regime gate application
# ─────────────────────────────────────────────────────────────────────────────

def apply_variant_a(
    weights_df: pd.DataFrame,
    eth_change: pd.Series,
    cols: List[str],
    drop_threshold: float = TVL_DROP_THRESHOLD,
) -> Tuple[pd.DataFrame, int, int]:
    """
    Variant A: Halt carry when TVL drops sharply.
    When eth_tvl_change_30d < drop_threshold:
      - Set V_rev_carry = 0, V_fwd_carry = 0
      - Redistribute freed weight proportionally to remaining strategies

    Returns: modified weights_df, n_days_fired, n_days_total
    """
    w = weights_df.copy()
    tvl_aligned = eth_change.reindex(w.index, method="ffill")
    fire_mask = tvl_aligned < drop_threshold
    n_fired = int(fire_mask.sum())

    carry_cols = [c for c in ["V_rev_carry", "V_fwd_carry"] if c in cols]
    other_cols  = [c for c in cols if c not in carry_cols]

    for idx in w.index[fire_mask]:
        freed = sum(w.loc[idx, c] for c in carry_cols)
        for c in carry_cols:
            w.loc[idx, c] = 0.0
        others_sum = sum(w.loc[idx, c] for c in other_cols)
        if others_sum > 0:
            for c in other_cols:
                w.loc[idx, c] += freed * (w.loc[idx, c] / others_sum)
        # Renormalize
        total = w.loc[idx, cols].sum()
        if total > 0:
            w.loc[idx, cols] = w.loc[idx, cols] / total

    return w, n_fired, len(w)


def apply_variant_b(
    weights_df: pd.DataFrame,
    eth_change: pd.Series,
    cols: List[str],
    grow_threshold: float = TVL_GROW_THRESHOLD,
    boost_target: float = CARRY_REV_CAP,
) -> Tuple[pd.DataFrame, int, int]:
    """
    Variant B: Boost V_rev_carry when TVL grows strongly.
    When eth_tvl_change_30d > grow_threshold:
      - Set V_rev_carry to max(current_weight, boost_target)
      - Reduce remaining strategies proportionally to maintain sum=1

    K206 finding: Variant B (boost on growth) showed +0.0587 OOS Sh lift.
    """
    w = weights_df.copy()
    tvl_aligned = eth_change.reindex(w.index, method="ffill")
    fire_mask = tvl_aligned > grow_threshold
    n_fired = int(fire_mask.sum())

    rev_col = "V_rev_carry"
    if rev_col not in cols:
        return w, 0, len(w)

    other_cols = [c for c in cols if c != rev_col]

    for idx in w.index[fire_mask]:
        current_rev = w.loc[idx, rev_col]
        if current_rev >= boost_target:
            continue  # already at cap, no change needed
        delta = boost_target - current_rev
        w.loc[idx, rev_col] = boost_target
        # Reduce others proportionally
        others_sum = sum(w.loc[idx, c] for c in other_cols)
        if others_sum >= delta:
            for c in other_cols:
                w.loc[idx, c] -= delta * (w.loc[idx, c] / others_sum)
        else:
            # Reduce others to zero then any residual from rev too
            reduction = delta - others_sum
            for c in other_cols:
                w.loc[idx, c] = 0.0
            w.loc[idx, rev_col] = boost_target - reduction
        # Renormalize
        total = w.loc[idx, cols].sum()
        if total > 0:
            w.loc[idx, cols] = w.loc[idx, cols] / total

    return w, n_fired, len(w)


def apply_variant_c(
    weights_df: pd.DataFrame,
    eth_change: pd.Series,
    cols: List[str],
    drop_threshold: float = TVL_DROP_THRESHOLD,
    grow_threshold: float = TVL_GROW_THRESHOLD,
    boost_target: float = CARRY_REV_CAP,
) -> Tuple[pd.DataFrame, int, int, int]:
    """
    Variant C: Both rules combined.
    - Drop rule applied first (defensive)
    - Grow rule applied to days not already in drop regime
    Returns: modified weights_df, n_drop_fired, n_grow_fired, n_total
    """
    tvl_aligned = eth_change.reindex(weights_df.index, method="ffill")
    drop_mask   = tvl_aligned < drop_threshold
    grow_mask   = (tvl_aligned > grow_threshold) & ~drop_mask   # no overlap

    # Apply drop rule
    w_after_a, n_drop, _ = apply_variant_a(weights_df, eth_change, cols, drop_threshold)
    # Apply grow rule on top (grow_mask already excludes drop days)
    w_final, n_grow, _ = apply_variant_b(w_after_a, eth_change, cols, grow_threshold, boost_target)

    # Recount (grow rule may have touched some days already halted by drop, but grow_mask prevents overlap)
    n_drop = int(drop_mask.sum())
    n_grow = int(grow_mask.sum())
    return w_final, n_drop, n_grow, len(weights_df)


def compute_portfolio_returns(
    weights_df: pd.DataFrame,
    returns_df: pd.DataFrame,
) -> pd.Series:
    """
    Compute daily portfolio returns given weight and returns DataFrames.
    Align on common dates.
    """
    cols = [c for c in weights_df.columns if c in returns_df.columns]
    common_idx = weights_df.index.intersection(returns_df.index)

    w = weights_df.loc[common_idx, cols].values
    r = returns_df.loc[common_idx, cols].values
    pnl = np.einsum("ij,ij->i", w, r)   # dot product per row
    return pd.Series(pnl, index=common_idx, name="pnl")


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    print("=" * 72)
    print("Wave K213 -- Ethena TVL Rule-Based Regime Gate for K198")
    print("=" * 72)
    print()

    np.random.seed(42)

    # ── Step 1: Load component returns ───────────────────────────────────────
    print("Step 1: Loading component returns...", flush=True)
    df_all = load_component_returns()
    cols = list(df_all.columns)
    print()

    # ── Step 2: Load FR trigger (K198 applies FR trigger before allocation) ──
    print("Step 2: Applying K198 FR trigger to component returns...", flush=True)
    FR_SYMBOLS    = ["BTC", "ETH", "DOGE", "AVAX", "SOL", "XRP"]
    FR_THRESHOLD  = -0.009735
    FR_COMPONENTS = ["K121", "K133"]

    daily_series = []
    for sym in FR_SYMBOLS:
        for tag in ("730d", "1200d", "365d"):
            fpath = CACHE / f"bybit_fr_{sym}USDT_{tag}.parquet"
            if fpath.exists():
                dfr = pd.read_parquet(fpath)
                dfr["timestamp"] = pd.to_datetime(dfr["timestamp"]).dt.tz_localize(None)
                dfr = dfr.set_index("timestamp")
                daily = dfr["funding_rate"].resample("1D").mean()
                ann   = daily * 3 * 365
                ann.name = sym
                daily_series.append(ann)
                break

    if daily_series:
        fr_panel = pd.concat(daily_series, axis=1)
        fr_mean  = fr_panel.mean(axis=1)
        fr_mean.name = "fr_mean_ann"
        fr_aligned = fr_mean.reindex(df_all.index, method="ffill")
        trigger_mask = fr_aligned < FR_THRESHOLD
        df_triggered = df_all.copy()
        for comp in FR_COMPONENTS:
            if comp in df_triggered.columns:
                df_triggered.loc[trigger_mask, comp] = 0.0
        n_trigger = int(trigger_mask.sum())
        print(f"  FR trigger fires {n_trigger}/{len(df_all)} days "
              f"({n_trigger/len(df_all)*100:.1f}%)")
    else:
        df_triggered = df_all.copy()
        print("  WARNING: no FR data, skipping FR trigger")
    print()

    # ── Step 3: Load K198 walk-forward weights ────────────────────────────────
    print("Step 3: Loading K198 ML walk-forward weights...", flush=True)
    k198_weights = load_k198_weights()
    print()

    # ── Step 4: Load Ethena TVL signal ───────────────────────────────────────
    print("Step 4: Loading Ethena TVL signal (lag=7d)...", flush=True)
    eth_change_30d, tvl_raw = load_ethena_tvl(lag_days=TVL_LAG_DAYS)
    print()

    # ── Step 5: Compute K198 baseline returns (no TVL override) ──────────────
    print("Step 5: Computing K198 baseline portfolio returns...", flush=True)
    pnl_k198 = compute_portfolio_returns(k198_weights, df_triggered)
    print(f"  K198 baseline: {len(pnl_k198)} days, "
          f"{pnl_k198.index[0].date()} -> {pnl_k198.index[-1].date()}")

    # OOS cut
    oos_cut = int(len(pnl_k198) * (1 - OOS_FRAC))
    pnl_k198_oos = pnl_k198.values[oos_cut:]
    m_k198_oos   = metrics_pkg(pnl_k198_oos)
    wf_k198      = wf_fold_sharpes(pnl_k198.values)
    print(f"  K198 (re-derived) OOS Sh={m_k198_oos['sharpe']:.4f}, "
          f"MaxDD={m_k198_oos['max_dd']:.4f}, "
          f"WF min={wf_k198['min']:.4f}")
    print()

    # ── Step 6: Variant A — halt carry on TVL drop ───────────────────────────
    print("Step 6: Variant A — halt carry when eth_tvl_change_30d < -0.15...", flush=True)
    wa, n_a_fired, n_a_total = apply_variant_a(k198_weights, eth_change_30d, cols)
    pnl_a = compute_portfolio_returns(wa, df_triggered)
    fire_rate_a = n_a_fired / n_a_total
    print(f"  Variant A fires: {n_a_fired}/{n_a_total} days ({fire_rate_a*100:.1f}%)")

    pnl_a_oos = pnl_a.values[oos_cut:]
    m_a_oos   = metrics_pkg(pnl_a_oos)
    wf_a      = wf_fold_sharpes(pnl_a.values)
    print(f"  Variant A OOS Sh={m_a_oos['sharpe']:.4f}, "
          f"MaxDD={m_a_oos['max_dd']:.4f}, "
          f"WF min={wf_a['min']:.4f}")
    print()

    # ── Step 7: Variant B — boost carry on TVL growth ─────────────────────────
    print("Step 7: Variant B — boost V_rev_carry when eth_tvl_change_30d > +0.10...", flush=True)
    wb, n_b_fired, n_b_total = apply_variant_b(k198_weights, eth_change_30d, cols)
    pnl_b = compute_portfolio_returns(wb, df_triggered)
    fire_rate_b = n_b_fired / n_b_total
    print(f"  Variant B fires: {n_b_fired}/{n_b_total} days ({fire_rate_b*100:.1f}%)")

    pnl_b_oos = pnl_b.values[oos_cut:]
    m_b_oos   = metrics_pkg(pnl_b_oos)
    wf_b      = wf_fold_sharpes(pnl_b.values)
    print(f"  Variant B OOS Sh={m_b_oos['sharpe']:.4f}, "
          f"MaxDD={m_b_oos['max_dd']:.4f}, "
          f"WF min={wf_b['min']:.4f}")
    print()

    # ── Step 8: Variant C — both rules combined ────────────────────────────────
    print("Step 8: Variant C — both halt and boost rules combined...", flush=True)
    wc, n_c_drop, n_c_grow, n_c_total = apply_variant_c(k198_weights, eth_change_30d, cols)
    pnl_c = compute_portfolio_returns(wc, df_triggered)
    fire_rate_c = (n_c_drop + n_c_grow) / n_c_total
    print(f"  Variant C fires: drop={n_c_drop} days, grow={n_c_grow} days, "
          f"total={(n_c_drop+n_c_grow)}/{n_c_total} ({fire_rate_c*100:.1f}%)")

    pnl_c_oos = pnl_c.values[oos_cut:]
    m_c_oos   = metrics_pkg(pnl_c_oos)
    wf_c      = wf_fold_sharpes(pnl_c.values)
    print(f"  Variant C OOS Sh={m_c_oos['sharpe']:.4f}, "
          f"MaxDD={m_c_oos['max_dd']:.4f}, "
          f"WF min={wf_c['min']:.4f}")
    print()

    # ── Step 9: Rule firing rate analysis ─────────────────────────────────────
    print("Step 9: Rule firing rate analysis...", flush=True)
    tvl_aligned_k198 = eth_change_30d.reindex(k198_weights.index, method="ffill")
    n_drop_days = int((tvl_aligned_k198 < TVL_DROP_THRESHOLD).sum())
    n_grow_days = int((tvl_aligned_k198 > TVL_GROW_THRESHOLD).sum())
    n_neutral    = n_b_total - n_drop_days - n_grow_days
    print(f"  TVL drop regime (<{TVL_DROP_THRESHOLD}): {n_drop_days} days "
          f"({n_drop_days/n_b_total*100:.1f}%)")
    print(f"  TVL grow regime (>{TVL_GROW_THRESHOLD}): {n_grow_days} days "
          f"({n_grow_days/n_b_total*100:.1f}%)")
    print(f"  Neutral (no trigger):             {n_neutral} days "
          f"({n_neutral/n_b_total*100:.1f}%)")

    # check acceptance criterion: rule firing <= 30%
    accept_fire_a = fire_rate_a <= 0.30
    accept_fire_b = fire_rate_b <= 0.30
    accept_fire_c = fire_rate_c <= 0.30
    print(f"  Fire rate <= 30%: A={fire_rate_a:.1%} ({'PASS' if accept_fire_a else 'FAIL'}), "
          f"B={fire_rate_b:.1%} ({'PASS' if accept_fire_b else 'FAIL'}), "
          f"C={fire_rate_c:.1%} ({'PASS' if accept_fire_c else 'FAIL'})")
    print()

    # ── Step 10: Weight change analysis ───────────────────────────────────────
    print("Step 10: Carry weight trajectory analysis...", flush=True)
    for variant_name, variant_w in [("A", wa), ("B", wb), ("C", wc)]:
        for carry in ["V_rev_carry", "V_fwd_carry"]:
            if carry in variant_w.columns:
                orig = k198_weights[carry]
                mod  = variant_w[carry]
                changed = (orig - mod).abs() > 1e-8
                n_changed = int(changed.sum())
                mean_mod = float(mod.mean())
                mean_orig = float(orig.mean())
                print(f"  Variant {variant_name} {carry}: "
                      f"orig_mean={mean_orig:.4f}, mod_mean={mean_mod:.4f}, "
                      f"n_days_changed={n_changed}")
    print()

    # ── Step 11: Acceptance evaluation ────────────────────────────────────────
    print("Step 11: Acceptance evaluation (gate: OOS Sh >= K198, MaxDD <= K198, WF min >= K198)...", flush=True)
    variants = {
        "K213a": {
            "oos": m_a_oos, "wf": wf_a, "fire_rate": fire_rate_a,
            "n_fired": n_a_fired, "fire_accept": accept_fire_a,
        },
        "K213b": {
            "oos": m_b_oos, "wf": wf_b, "fire_rate": fire_rate_b,
            "n_fired": n_b_fired, "fire_accept": accept_fire_b,
        },
        "K213c": {
            "oos": m_c_oos, "wf": wf_c, "fire_rate": fire_rate_c,
            "n_fired": n_c_drop + n_c_grow, "fire_accept": accept_fire_c,
        },
    }

    best_variant = None
    best_sh = -999.0
    results = {}

    for vname, vdata in variants.items():
        sh_pass  = vdata["oos"]["sharpe"] >= K198_OOS_SH
        mdd_pass = vdata["oos"]["max_dd"] >= K198_OOS_DD
        wf_pass  = vdata["wf"]["min"] >= K198_WF_MIN
        fire_pass = vdata["fire_accept"]
        all_pass = sh_pass and mdd_pass and wf_pass and fire_pass

        print(f"  {vname}:")
        print(f"    OOS Sh={vdata['oos']['sharpe']:.4f} >= {K198_OOS_SH} -> {'PASS' if sh_pass else 'FAIL'}")
        print(f"    MaxDD={vdata['oos']['max_dd']:.4f} >= {K198_OOS_DD} -> {'PASS' if mdd_pass else 'FAIL'}")
        print(f"    WF min={vdata['wf']['min']:.4f} >= {K198_WF_MIN} -> {'PASS' if wf_pass else 'FAIL'}")
        print(f"    Fire rate={vdata['fire_rate']:.1%} <= 30% -> {'PASS' if fire_pass else 'FAIL'}")
        print(f"    ALL PASS: {all_pass}")

        results[vname] = {
            "oos_sharpe":  vdata["oos"]["sharpe"],
            "oos_maxdd":   vdata["oos"]["max_dd"],
            "oos_sortino": vdata["oos"]["sortino"],
            "oos_calmar":  vdata["oos"]["calmar"],
            "oos_ann_ret": vdata["oos"]["ann_ret"],
            "oos_ann_vol": vdata["oos"]["ann_vol"],
            "oos_n_days":  vdata["oos"]["n_days"],
            "wf_mean":     vdata["wf"]["mean"],
            "wf_min":      vdata["wf"]["min"],
            "wf_max":      vdata["wf"]["max"],
            "wf_std":      vdata["wf"]["std"],
            "wf_fold_sharpes": vdata["wf"]["fold_sharpes"],
            "fire_rate":   round(vdata["fire_rate"], 4),
            "n_fired":     vdata["n_fired"],
            "fire_rate_pass": fire_pass,
            "sh_pass":     sh_pass,
            "mdd_pass":    mdd_pass,
            "wf_min_pass": wf_pass,
            "all_pass":    all_pass,
            "lift_vs_k198_oos_sh": round(vdata["oos"]["sharpe"] - K198_OOS_SH, 4),
        }

        if vdata["oos"]["sharpe"] > best_sh:
            best_sh = vdata["oos"]["sharpe"]
            best_variant = vname

    print()
    print(f"  Best variant by OOS Sh: {best_variant} ({best_sh:.4f})")
    print()

    # ── Step 12: Overall verdict ─────────────────────────────────────────────
    print("Step 12: Verdict...", flush=True)
    best_r = results[best_variant]
    best_pass = best_r["all_pass"]

    if best_pass:
        verdict = (
            f"ACCEPT: {best_variant} clears all K213 acceptance gates. "
            f"OOS Sh={best_r['oos_sharpe']:.4f} (+{best_r['lift_vs_k198_oos_sh']:+.4f} vs K198), "
            f"MaxDD={best_r['oos_maxdd']:.4f}, WF min={best_r['wf_min']:.4f}, "
            f"fire rate={best_r['fire_rate']:.1%}. "
            f"Deploy as v6.6: K198 ML allocator + {best_variant} TVL regime gate."
        )
        deploy_recommendation = (
            f"Deploy {best_variant}: attach TVL regime gate post-allocation, "
            f"refresh monthly alongside ML refit. "
            "Monitoring: check TVL feed daily, alert if TVL gap > 2d stale."
        )
    else:
        # Check if any variant partially passes
        any_sh = any(r["sh_pass"] for r in results.values())
        any_mdd = any(r["mdd_pass"] for r in results.values())
        any_wf = any(r["wf_min_pass"] for r in results.values())

        if any_sh and any_mdd:
            verdict = (
                f"PARTIAL: {best_variant} improves OOS Sh and MaxDD but fails WF min gate. "
                f"OOS Sh={best_r['oos_sharpe']:.4f}, MaxDD={best_r['oos_maxdd']:.4f}, "
                f"WF min={best_r['wf_min']:.4f} (req {K198_WF_MIN}). "
                "Recommend: investigate threshold sensitivity (±5ppt on TVL thresholds) in K214."
            )
        elif best_sh > K198_OOS_SH - 0.5:
            verdict = (
                f"NEAR-MISS: {best_variant} OOS Sh={best_sh:.4f} close to K198 baseline {K198_OOS_SH}. "
                "TVL regime gate adds structure but insufficient standalone lift. "
                "Recommend: combine with momentum or volatility filter for K214."
            )
        else:
            verdict = (
                "REJECT: No K213 variant meets all acceptance gates. "
                f"Best OOS Sh={best_sh:.4f} vs K198 baseline {K198_OOS_SH}. "
                "TVL rule-based gate does not improve K198 systematically. "
                "K198 v6.5 remains production allocator. "
                "Recommend: K214 investigate asymmetric threshold optimization or "
                "TVL-momentum interaction as a third feature dimension."
            )
        deploy_recommendation = "No deployment recommended. K198 v6.5 retained."

    print(f"  VERDICT: {verdict}")
    print(f"  DEPLOYMENT: {deploy_recommendation}")
    print()

    elapsed = round(time.time() - START_TIME, 1)
    print(f"Total runtime: {elapsed}s")
    print()

    # ── Step 13: Build equity curves for output ─────────────────────────────
    print("Step 13: Building equity curves...", flush=True)

    def equity_curve(pnl: pd.Series) -> List[float]:
        return [round(float(v), 6) for v in np.cumprod(1.0 + pnl.values)]

    def date_strs(idx) -> List[str]:
        return [str(d.date()) for d in idx]

    # Load K198 official curves for comparison overlay
    with open(BASE / "wave_k198_curves.json") as f:
        k198_stored = json.load(f)

    # TVL series for overlay
    tvl_overlay_dates = [str(d.date()) for d in tvl_raw.index]
    tvl_overlay_values = [round(float(v) / 1e9, 4) for v in tvl_raw.values]  # in billions

    # eth_tvl_change_30d aligned to k198 dates
    tvl_chg_k198 = eth_change_30d.reindex(k198_weights.index, method="ffill")
    drop_regime_flag = (tvl_chg_k198 < TVL_DROP_THRESHOLD).astype(int)
    grow_regime_flag = (tvl_chg_k198 > TVL_GROW_THRESHOLD).astype(int)

    curves_out = {
        "wave": "K213",
        "dates_k213": date_strs(pnl_k198.index),
        "equity_k198_baseline":   equity_curve(pnl_k198),
        "equity_k213a":           equity_curve(pnl_a),
        "equity_k213b":           equity_curve(pnl_b),
        "equity_k213c":           equity_curve(pnl_c),
        "returns_k198_baseline":  [round(float(v), 8) for v in pnl_k198.values],
        "returns_k213a":          [round(float(v), 8) for v in pnl_a.values],
        "returns_k213b":          [round(float(v), 8) for v in pnl_b.values],
        "returns_k213c":          [round(float(v), 8) for v in pnl_c.values],
        "tvl_overlay": {
            "dates":  tvl_overlay_dates,
            "tvl_bn": tvl_overlay_values,
        },
        "tvl_change_30d_aligned": {
            "dates":  date_strs(pnl_k198.index),
            "values": [round(float(v), 6) if not np.isnan(v) else None
                       for v in tvl_chg_k198.values],
            "drop_regime_flag": drop_regime_flag.tolist(),
            "grow_regime_flag": grow_regime_flag.tolist(),
        },
        "carry_weights_k213a": {
            "dates":       date_strs(wa.index),
            "V_rev_carry": [round(float(v), 4) for v in wa["V_rev_carry"].values] if "V_rev_carry" in wa.columns else [],
            "V_fwd_carry": [round(float(v), 4) for v in wa["V_fwd_carry"].values] if "V_fwd_carry" in wa.columns else [],
        },
        "carry_weights_k213b": {
            "dates":       date_strs(wb.index),
            "V_rev_carry": [round(float(v), 4) for v in wb["V_rev_carry"].values] if "V_rev_carry" in wb.columns else [],
            "V_fwd_carry": [round(float(v), 4) for v in wb["V_fwd_carry"].values] if "V_fwd_carry" in wb.columns else [],
        },
        "carry_weights_k213c": {
            "dates":       date_strs(wc.index),
            "V_rev_carry": [round(float(v), 4) for v in wc["V_rev_carry"].values] if "V_rev_carry" in wc.columns else [],
            "V_fwd_carry": [round(float(v), 4) for v in wc["V_fwd_carry"].values] if "V_fwd_carry" in wc.columns else [],
        },
        "k198_stored_equity": k198_stored["equity_ridge"],
        "k198_stored_dates":  k198_stored["dates_ml"],
    }

    out_curves = BASE / "wave_k213_curves.json"
    with open(out_curves, "w") as f:
        json.dump(curves_out, f, indent=2)
    print(f"  Saved: {out_curves}")
    print()

    # ── Step 14: Save main JSON output ─────────────────────────────────────
    print("Step 14: Saving main metrics JSON...", flush=True)

    output = {
        "wave": "K213",
        "task": "Ethena TVL rule-based regime gate for K198 (v6.6 candidate)",
        "as_of": pd.Timestamp.now(tz="UTC").isoformat(),
        "runtime_s": elapsed,
        "config": {
            "strategies": cols,
            "tvl_drop_threshold": TVL_DROP_THRESHOLD,
            "tvl_grow_threshold": TVL_GROW_THRESHOLD,
            "tvl_lag_days": TVL_LAG_DAYS,
            "carry_rev_cap": CARRY_REV_CAP,
            "carry_fwd_cap": CARRY_FWD_CAP,
            "k198_oos_sh_baseline": K198_OOS_SH,
            "k198_oos_dd_baseline": K198_OOS_DD,
            "k198_wf_min_baseline": K198_WF_MIN,
            "oos_frac": OOS_FRAC,
            "n_folds": N_FOLDS,
            "date_range": [
                str(pnl_k198.index[0].date()),
                str(pnl_k198.index[-1].date()),
            ],
            "n_days_total": len(pnl_k198),
            "n_oos_days": len(pnl_k198) - oos_cut,
        },
        "tvl_regime_stats": {
            "n_total_days":   n_a_total,
            "n_drop_days":    n_drop_days,
            "n_grow_days":    n_grow_days,
            "n_neutral_days": n_neutral,
            "pct_drop":       round(n_drop_days / n_a_total, 4),
            "pct_grow":       round(n_grow_days / n_a_total, 4),
            "pct_neutral":    round(n_neutral / n_a_total, 4),
        },
        "comparison_table": {
            "K198_v6_5_baseline": {
                "description": "K198 Ridge ML, 51 features, 90d window (production v6.5)",
                "oos_sharpe": round(m_k198_oos["sharpe"], 4),
                "oos_maxdd":  round(m_k198_oos["max_dd"], 4),
                "wf_mean":    wf_k198["mean"],
                "wf_min":     wf_k198["min"],
                "wf_fold_sharpes": wf_k198["fold_sharpes"],
                "note": "Re-derived from stored weights x returns (may differ marginally from original K198 reported metrics)",
            },
            "K213a_halt_on_drop": {
                "description": "K198 + halt V_rev/fwd_carry when eth_tvl_change_30d < -0.15",
                **results["K213a"],
            },
            "K213b_boost_on_grow": {
                "description": "K198 + boost V_rev_carry to 10% cap when eth_tvl_change_30d > +0.10",
                **results["K213b"],
            },
            "K213c_both_rules": {
                "description": "K198 + both halt (drop) and boost (grow) rules combined",
                **results["K213c"],
            },
        },
        "best_variant": best_variant,
        "best_variant_lift_vs_k198": round(best_sh - K198_OOS_SH, 4),
        "acceptance_gates": {
            "oos_sh_threshold": K198_OOS_SH,
            "oos_dd_threshold": K198_OOS_DD,
            "wf_min_threshold": K198_WF_MIN,
            "fire_rate_max": 0.30,
            "k213a_all_pass": results["K213a"]["all_pass"],
            "k213b_all_pass": results["K213b"]["all_pass"],
            "k213c_all_pass": results["K213c"]["all_pass"],
            "any_variant_passes": any(r["all_pass"] for r in results.values()),
        },
        "verdict": verdict,
        "deploy_recommendation": deploy_recommendation,
        "methodology_note": (
            "K213 applies TVL regime gates AFTER K198 ML allocation. "
            "No ML re-training required. Gate operates on post-allocation weights. "
            "7-day TVL lag prevents look-ahead bias. "
            "FR trigger (K121, K133 zeroed on negative FR) applied before gate."
        ),
        "k211_prior_context": (
            "K211 used carry-specific ML interaction features (eth_x_V_rev_carry, "
            "eth_x_V_fwd_carry) and was REJECTED (OOS Sh 8.81). "
            "K213 bypasses ML entirely with a direct rule gate. "
            "If K213 also rejects, the TVL signal may not be implementable within "
            "the current K198 Ridge ML architecture."
        ),
    }

    out_json = BASE / "wave_k213_tvl_regime_gate.json"
    with open(out_json, "w") as f:
        json.dump(output, f, indent=2)
    print(f"  Saved: {out_json}")
    print()

    # ── Final comparison table ────────────────────────────────────────────────
    print("=" * 72)
    print("FINAL COMPARISON TABLE")
    print("=" * 72)
    print(f"{'Version':<35} {'OOS Sh':>8} {'OOS MaxDD':>10} {'WF Mean':>8} {'WF Min':>8} {'Fire%':>7}")
    print("-" * 72)
    print(f"{'K198 v6.5 baseline (re-derived)':<35} "
          f"{m_k198_oos['sharpe']:>8.4f} {m_k198_oos['max_dd']:>10.4f} "
          f"{wf_k198['mean']:>8.4f} {wf_k198['min']:>8.4f} {'N/A':>7}")
    for vname, vr in results.items():
        label = {"K213a": "K213a halt (TVL<-15%)",
                 "K213b": "K213b boost (TVL>+10%)",
                 "K213c": "K213c combined"}[vname]
        print(f"  {label:<33} "
              f"{vr['oos_sharpe']:>8.4f} {vr['oos_maxdd']:>10.4f} "
              f"{vr['wf_mean']:>8.4f} {vr['wf_min']:>8.4f} "
              f"{vr['fire_rate']*100:>6.1f}%")
    print("-" * 72)
    print(f"\n  Best variant: {best_variant}  "
          f"(OOS Sh lift vs K198: {best_sh - K198_OOS_SH:+.4f})")
    print(f"\n  VERDICT: {verdict[:120]}...")
    print(f"\n  DEPLOYMENT: {deploy_recommendation}")
    print(f"\nRuntime: {elapsed:.1f}s")
    print("Done.")

    return output


if __name__ == "__main__":
    main()
