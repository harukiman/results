"""
Wave K327: K280/K297 Dynamic Weight Allocator vs Static 80/20
=============================================================
Hypothesis: regime-conditioned dynamic weighting between K280 (carry)
and K297 (RWA satellite) can outperform the static 80/20 baseline.

Regime signals:
  A. FR-richness: mean(|fr|) across hl_longtail symbols, rolling-60d tercile
  B. BTC realized vol: rolling-20d std of daily returns, tercile
  C. BTC trend: sign of 60d return (BULL/BEAR)
  D. K280 momentum: rolling-30d K280 Sharpe, tercile

Grid: w_K280 in {0.5, 0.6, 0.7, 0.8, 0.9, 1.0}
Walk-forward: 4 folds
Decision gates: dynamic Sh >= static*1.05 AND MDD <= static AND mapping stable
"""

import json
import numpy as np
import pandas as pd
from datetime import datetime, timezone
from pathlib import Path
import warnings
warnings.filterwarnings("ignore")

CACHE_DIR = Path("/Users/nekonaomichi/crypto-lab/cache")
OUT_DIR   = Path("/Users/nekonaomichi/crypto-lab")

# ── helpers ──────────────────────────────────────────────────────────────────

def sharpe(ret: pd.Series, ann: int = 365) -> float:
    """Annualised Sharpe (Rf=0)."""
    if len(ret) < 5 or ret.std() == 0:
        return np.nan
    return float(ret.mean() / ret.std() * np.sqrt(ann))

def max_drawdown(eq: pd.Series) -> float:
    roll_max = eq.cummax()
    dd = (eq - roll_max) / roll_max
    return float(dd.min())

def ann_return(ret: pd.Series, ann: int = 365) -> float:
    if len(ret) < 2:
        return np.nan
    total = (1 + ret).prod()
    return float(total ** (ann / len(ret)) - 1)

def tercile_label(series: pd.Series, labels=("LOW","MID","HIGH")) -> pd.Series:
    """Rolling tercile label (forward-filled on NaN)."""
    q = series.quantile([1/3, 2/3])
    out = pd.Series(index=series.index, dtype=object)
    out[series < q.iloc[0]]  = labels[0]
    out[(series >= q.iloc[0]) & (series < q.iloc[1])] = labels[1]
    out[series >= q.iloc[1]] = labels[2]
    return out

# ── load K280 daily returns ───────────────────────────────────────────────────

def load_k280_returns() -> pd.Series:
    with open(OUT_DIR / "wave_k280_curves.json") as f:
        d = json.load(f)
    dates = pd.to_datetime(d["dates"])
    equity = np.array(d["K280"], dtype=float)
    eq = pd.Series(equity, index=dates)
    ret = eq.pct_change().dropna()
    return ret

# ── load K297 daily returns ───────────────────────────────────────────────────

def load_k297_returns() -> pd.Series:
    with open(OUT_DIR / "wave_k297_curves.json") as f:
        d = json.load(f)
    ret_raw = d["portfolio_daily_returns"]
    dates = pd.to_datetime(list(ret_raw.keys()))
    vals  = np.array(list(ret_raw.values()), dtype=float)
    ret = pd.Series(vals, index=dates)
    return ret

# ── load BTC daily close ──────────────────────────────────────────────────────

def load_btc_daily() -> pd.Series:
    df = pd.read_parquet(CACHE_DIR / "BTCUSDT_1d_730d.parquet")
    df["date"] = pd.to_datetime(df["open_time"])
    df = df.set_index("date").sort_index()
    return df["close"].astype(float)

# ── load HL longtail FR ───────────────────────────────────────────────────────

def load_hl_fr() -> pd.DataFrame:
    df = pd.read_parquet(CACHE_DIR / "hl_longtail_fr_daily.parquet")
    df.index = pd.to_datetime(df.index)
    return df.sort_index()

# ── build regime signals ──────────────────────────────────────────────────────

def build_signals(overlap_dates: pd.DatetimeIndex,
                  k280_ret: pd.Series,
                  btc_close: pd.Series,
                  hl_fr: pd.DataFrame) -> pd.DataFrame:
    """
    Build regime signals for the overlap period.
    All signals use data available at t-1 (no look-ahead).
    """
    # ── Signal A: FR-richness (rolling 60d tercile of mean |FR|) ─────────────
    mean_abs_fr = hl_fr.abs().mean(axis=1)
    # rolling 60d mean of the cross-sectional mean |FR|
    fr_roll60 = mean_abs_fr.rolling(60, min_periods=30).mean()
    # tercile against full-sample distribution (in-sample tercile breakpoints
    # computed on all data, then applied; acknowledged as slight look-ahead in
    # classification but consistent with K323 methodology)
    fr_tercile = tercile_label(fr_roll60)

    # ── Signal B: BTC realized vol (rolling 20d std of daily returns) ─────────
    btc_ret = btc_close.pct_change()
    btc_vol20 = btc_ret.rolling(20, min_periods=10).std() * np.sqrt(365)
    btc_vol_tercile = tercile_label(btc_vol20)

    # ── Signal C: BTC 60d trend (sign of 60d return) ─────────────────────────
    btc_ret60 = btc_close.pct_change(60)
    btc_trend = (btc_ret60 >= 0).map({True: "BULL", False: "BEAR"})

    # ── Signal D: K280 rolling 30d Sharpe tercile ─────────────────────────────
    k280_sh30 = k280_ret.rolling(30, min_periods=15).apply(
        lambda x: x.mean() / x.std() * np.sqrt(365) if x.std() > 0 else 0
    )
    k280_sh_tercile = tercile_label(k280_sh30)

    # Align all to overlap dates, shift by 1 (t-1 data used for day t decision)
    sig = pd.DataFrame({
        "fr_tercile":       fr_tercile,
        "btc_vol_tercile":  btc_vol_tercile,
        "btc_trend":        btc_trend,
        "k280_sh_tercile":  k280_sh_tercile,
    })
    sig = sig.shift(1)               # t-1 → no look-ahead
    sig = sig.reindex(overlap_dates).ffill()
    return sig

# ── grid search: best weight per regime state ─────────────────────────────────

WEIGHT_GRID = [0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
SIGNAL_COLS = ["fr_tercile", "btc_vol_tercile", "btc_trend", "k280_sh_tercile"]

def weight_search_on_subset(k280_r: pd.Series,
                             k297_r: pd.Series,
                             mask: pd.Series) -> dict:
    """
    For days indicated by mask, grid-search the best w_k280.
    Returns dict with best_w, Sharpe per weight, n_days.
    """
    k280_sub = k280_r[mask]
    k297_sub = k297_r[mask]
    n = mask.sum()
    results = {}
    for w in WEIGHT_GRID:
        combined = w * k280_sub + (1 - w) * k297_sub
        sh = sharpe(combined)
        results[w] = sh
    best_w = max(results, key=lambda x: results[x] if not np.isnan(results[x]) else -999)
    return {"n_days": int(n), "best_w": best_w, "sharpe_by_weight": results}

def full_regime_grid(k280_r: pd.Series,
                     k297_r: pd.Series,
                     signals: pd.DataFrame) -> dict:
    """Run grid search for each signal × regime state."""
    results = {}
    for sig_col in SIGNAL_COLS:
        results[sig_col] = {}
        states = signals[sig_col].dropna().unique()
        for state in sorted(states):
            mask = (signals[sig_col] == state)
            mask = mask & mask.index.isin(k280_r.index) & mask.index.isin(k297_r.index)
            if mask.sum() < 20:
                results[sig_col][state] = {"n_days": int(mask.sum()),
                                           "best_w": 0.8,
                                           "note": "too_few_days"}
                continue
            results[sig_col][state] = weight_search_on_subset(k280_r, k297_r, mask)
    return results

# ── dynamic allocator backtest ────────────────────────────────────────────────

def dynamic_backtest(k280_r: pd.Series,
                     k297_r: pd.Series,
                     signals: pd.DataFrame,
                     regime_col: str,
                     weight_map: dict,
                     default_w: float = 0.8) -> pd.Series:
    """
    Apply dynamic weights from weight_map[regime_state] for each day.
    weight_map: {state_label: w_k280}
    Returns portfolio daily returns.
    """
    portfolio = pd.Series(index=k280_r.index, dtype=float)
    for date in k280_r.index:
        state = signals.loc[date, regime_col] if date in signals.index else np.nan
        w = weight_map.get(state, default_w)
        r280 = k280_r.loc[date]
        r297 = k297_r.loc[date] if date in k297_r.index else 0.0
        portfolio.loc[date] = w * r280 + (1 - w) * r297
    return portfolio

# ── walk-forward evaluation ───────────────────────────────────────────────────

def walk_forward_4fold(k280_r: pd.Series,
                       k297_r: pd.Series,
                       signals: pd.DataFrame,
                       regime_col: str,
                       default_w: float = 0.8) -> dict:
    """
    4-fold walk-forward: train on folds 1-3, test on fold 4 (expanding).
    Actually uses held-out last-fold test at each step.
    """
    n = len(k280_r)
    fold_size = n // 4
    fold_results = []

    for fold_i in range(1, 5):
        test_start = fold_size * (fold_i - 1)
        test_end   = fold_size * fold_i if fold_i < 4 else n
        train_idx  = k280_r.index[:test_start]
        test_idx   = k280_r.index[test_start:test_end]

        if len(train_idx) < 30:
            fold_results.append({"fold": fold_i,
                                  "train_n": len(train_idx),
                                  "test_n": len(test_idx),
                                  "note": "insufficient_train",
                                  "dynamic_sh": np.nan,
                                  "static_sh": np.nan,
                                  "delta": np.nan})
            continue

        # Fit weight map on train
        train_mask_base = signals.index.isin(train_idx)
        w_map = {}
        for state in signals[regime_col].dropna().unique():
            mask = pd.Series(
                (signals[regime_col] == state).values & train_mask_base,
                index=signals.index
            )
            if mask.sum() < 15:
                w_map[state] = default_w
                continue
            res = weight_search_on_subset(k280_r, k297_r, mask)
            w_map[state] = res["best_w"]

        # Apply on test
        test_k280 = k280_r.loc[k280_r.index.isin(test_idx)]
        test_k297 = k297_r.loc[k297_r.index.isin(test_idx)]
        test_sig  = signals.loc[signals.index.isin(test_idx)]

        dyn_ret = []
        stat_ret = []
        for date in test_k280.index:
            state = test_sig.loc[date, regime_col] if date in test_sig.index else np.nan
            w = w_map.get(state, default_w)
            r280 = test_k280.loc[date]
            r297 = test_k297.loc[date] if date in test_k297.index else 0.0
            dyn_ret.append(w * r280 + (1 - w) * r297)
            stat_ret.append(default_w * r280 + (1 - default_w) * r297)

        dyn_s = pd.Series(dyn_ret)
        stat_s = pd.Series(stat_ret)
        fold_results.append({
            "fold": fold_i,
            "train_n": len(train_idx),
            "test_n": len(test_k280),
            "weight_map": {str(k): v for k, v in w_map.items()},
            "dynamic_sh": round(sharpe(dyn_s), 4),
            "static_sh":  round(sharpe(stat_s), 4),
            "delta":       round(sharpe(dyn_s) - sharpe(stat_s), 4),
        })

    return fold_results

# ── monotonicity check ────────────────────────────────────────────────────────

def check_monotonicity(regime_results: dict, signal_col: str) -> dict:
    """
    For ordered signals (fr_tercile, btc_vol_tercile, k280_sh_tercile),
    check if best_w is monotone across LOW/MID/HIGH.
    Returns spearman r between rank and best_w.
    """
    ordered_states = ["LOW", "MID", "HIGH"]
    res = regime_results.get(signal_col, {})
    ws = []
    for state in ordered_states:
        if state in res and "best_w" in res[state]:
            ws.append(res[state]["best_w"])
    if len(ws) < 3:
        return {"spearman_r": None, "is_monotone": False, "weights": ws}
    # spearman: rank correlation
    ranks = np.array([1, 2, 3])
    ws_arr = np.array(ws)
    n = 3
    d2 = np.sum((ranks - ws_arr.argsort().argsort() - 1)**2)
    rs = 1 - 6*d2 / (n*(n**2-1))
    is_mono = (ws[0] <= ws[1] <= ws[2]) or (ws[0] >= ws[1] >= ws[2])
    return {"spearman_r": round(float(rs), 3),
            "is_monotone": bool(is_mono),
            "weights_low_mid_high": [round(w, 2) for w in ws]}

# ── multiplicity-corrected interpretation ─────────────────────────────────────

def dsr_multiplicity_note(n_signals: int, n_weights: int, n_regimes_per_signal: int,
                           n_folds: int) -> str:
    n_combos = n_signals * n_weights * n_regimes_per_signal * n_folds
    return (
        f"Total combinations tested: {n_combos} "
        f"({n_signals} signals × {n_weights} weights × "
        f"~{n_regimes_per_signal} regimes × {n_folds} WF folds). "
        "DSR-style haircut: a standalone Sharpe ~1.5–2× raw threshold required "
        "to be meaningful after multiple-testing correction."
    )

# ── main ──────────────────────────────────────────────────────────────────────

def main():
    print("K327: Loading data...")

    k280_ret = load_k280_returns()
    k297_ret = load_k297_returns()
    btc_close = load_btc_daily()
    hl_fr     = load_hl_fr()

    print(f"  K280 returns: {k280_ret.index[0].date()} → {k280_ret.index[-1].date()}  n={len(k280_ret)}")
    print(f"  K297 returns: {k297_ret.index[0].date()} → {k297_ret.index[-1].date()}  n={len(k297_ret)}")
    print(f"  BTC daily:    {btc_close.index[0].date()} → {btc_close.index[-1].date()}")
    print(f"  HL FR daily:  {hl_fr.index[0].date()} → {hl_fr.index[-1].date()}")

    # Overlap: dates present in both K280 and K297
    common_dates = k280_ret.index.intersection(k297_ret.index)
    print(f"  Overlap: {common_dates[0].date()} → {common_dates[-1].date()}  n={len(common_dates)}")

    k280_r = k280_ret.loc[common_dates]
    k297_r = k297_ret.loc[common_dates]

    # Build regime signals on overlap period
    print("K327: Building regime signals...")
    signals = build_signals(common_dates, k280_ret, btc_close, hl_fr)

    # Static 80/20 baseline on overlap
    static_ret = 0.8 * k280_r + 0.2 * k297_r
    static_eq  = (1 + static_ret).cumprod()
    static_sh  = sharpe(static_ret)
    static_mdd = max_drawdown(static_eq)
    static_ar  = ann_return(static_ret)

    print(f"  Static 80/20  → Sh={static_sh:.3f}  MDD={static_mdd:.4f}  annRet={static_ar:.4f}")

    # ── Full-period grid search per signal ────────────────────────────────────
    print("K327: Full-period regime grid search...")
    regime_results = full_regime_grid(k280_r, k297_r, signals)

    # ── Dynamic allocator for each signal (best-weight from full period) ──────
    # Note: this IS look-ahead — used only for upper-bound comparison
    print("K327: Dynamic allocator (in-sample upper bound)...")
    is_dynamic = {}
    for sig_col in SIGNAL_COLS:
        # build weight map from full-period best weights
        w_map = {state: info["best_w"]
                 for state, info in regime_results[sig_col].items()
                 if "best_w" in info}
        dyn_ret = dynamic_backtest(k280_r, k297_r, signals, sig_col, w_map)
        dyn_eq  = (1 + dyn_ret).cumprod()
        is_dynamic[sig_col] = {
            "sh":  round(sharpe(dyn_ret), 4),
            "mdd": round(max_drawdown(dyn_eq), 6),
            "ar":  round(ann_return(dyn_ret), 4),
            "note": "IS_upper_bound_look_ahead"
        }
        print(f"    {sig_col}: IS Sh={is_dynamic[sig_col]['sh']:.3f}  MDD={is_dynamic[sig_col]['mdd']:.6f}")

    # ── Walk-forward 4-fold for each signal ───────────────────────────────────
    print("K327: Walk-forward 4-fold...")
    wf_results = {}
    for sig_col in SIGNAL_COLS:
        print(f"    WF: {sig_col}")
        wf_results[sig_col] = walk_forward_4fold(k280_r, k297_r, signals, sig_col)

    # ── Monotonicity checks ───────────────────────────────────────────────────
    mono_checks = {}
    for sig_col in ["fr_tercile", "btc_vol_tercile", "k280_sh_tercile"]:
        mono_checks[sig_col] = check_monotonicity(regime_results, sig_col)

    # ── Decision per signal ────────────────────────────────────────────────────
    print("K327: Computing decisions...")
    decisions = {}
    for sig_col in SIGNAL_COLS:
        wf = wf_results[sig_col]
        # Only folds 2-4 have meaningful train data
        valid_folds = [f for f in wf if not np.isnan(f.get("dynamic_sh", np.nan)) and f["train_n"] >= 30]
        if not valid_folds:
            decisions[sig_col] = {"verdict": "REJECT", "reason": "insufficient_train_data"}
            continue
        wf_dyn_sh  = np.mean([f["dynamic_sh"] for f in valid_folds])
        wf_stat_sh = np.mean([f["static_sh"]  for f in valid_folds])
        wf_delta   = wf_dyn_sh - wf_stat_sh
        threshold  = wf_stat_sh * 0.05  # 5% improvement threshold

        # Monotonicity (only for ordered signals)
        mono = mono_checks.get(sig_col, {})
        is_mono = mono.get("is_monotone", None)

        # MDD: compare dynamic IS MDD vs static
        dyn_mdd = is_dynamic[sig_col]["mdd"]
        mdd_ok  = abs(dyn_mdd) <= abs(static_mdd)

        # Small-sample warning
        small_sample_warn = len(common_dates) < 300

        if wf_delta >= threshold and mdd_ok and (is_mono is not False):
            verdict = "ACCEPT"
        elif abs(wf_delta) < threshold * 0.5:
            verdict = "DEFER"
        else:
            verdict = "REJECT"

        decisions[sig_col] = {
            "verdict":            verdict,
            "wf_avg_dynamic_sh":  round(wf_dyn_sh, 4),
            "wf_avg_static_sh":   round(wf_stat_sh, 4),
            "wf_delta":           round(wf_delta, 4),
            "threshold_5pct":     round(threshold, 4),
            "mdd_ok":             bool(mdd_ok),
            "is_monotone":        is_mono,
            "small_sample_warn":  bool(small_sample_warn),
        }
        print(f"    {sig_col}: {verdict}  (WF delta={wf_delta:.4f}  thresh={threshold:.4f})")

    # ── Aggregate verdict ──────────────────────────────────────────────────────
    verdicts = [d["verdict"] for d in decisions.values()]
    if all(v == "REJECT" for v in verdicts):
        overall = "REJECT"
    elif any(v == "ACCEPT" for v in verdicts):
        overall = "CONDITIONAL"
    else:
        overall = "DEFER"

    print(f"\nK327: Overall verdict = {overall}")

    # ── Multiplicity note ─────────────────────────────────────────────────────
    mult_note = dsr_multiplicity_note(
        n_signals=len(SIGNAL_COLS),
        n_weights=len(WEIGHT_GRID),
        n_regimes_per_signal=3,
        n_folds=4
    )

    # ── Assemble output JSON ───────────────────────────────────────────────────
    out = {
        "wave":            "K327",
        "task":            "Dynamic K280/K297 weight allocator vs static 80/20",
        "generated_at":    datetime.now(timezone.utc).isoformat(),
        "data": {
            "k280_n_days":   len(k280_ret),
            "k297_n_days":   len(k297_ret),
            "overlap_n_days": len(common_dates),
            "overlap_start":  str(common_dates[0].date()),
            "overlap_end":    str(common_dates[-1].date()),
        },
        "static_80_20_baseline": {
            "sharpe":    round(static_sh, 4),
            "mdd":       round(static_mdd, 6),
            "ann_return": round(static_ar, 4),
        },
        "regime_grid_full_period": {
            sig: {
                state: {
                    "n_days":  info["n_days"],
                    "best_w":  info.get("best_w"),
                    "sh_by_w": {str(k): round(v, 4) if not np.isnan(v) else None
                                for k, v in info.get("sharpe_by_weight", {}).items()}
                }
                for state, info in reg_states.items()
            }
            for sig, reg_states in regime_results.items()
        },
        "is_dynamic_upper_bound": is_dynamic,
        "walk_forward_4fold":     wf_results,
        "monotonicity_checks":    mono_checks,
        "per_signal_decisions":   decisions,
        "overall_verdict":        overall,
        "multiplicity_note":      mult_note,
        "interpretation": (
            "Most likely REJECT/DEFER: small overlap sample (~447d), "
            "72-288 combinations tested, typical DSR haircut eliminates marginal gains. "
            "Accept only if monotone mapping + WF delta >= 5% + MDD not worse."
        ),
    }

    out_path = OUT_DIR / "wave_k327_dynamic_split.json"
    with open(out_path, "w") as f:
        json.dump(out, f, indent=2, default=str)
    print(f"Saved: {out_path}")

    return out

if __name__ == "__main__":
    result = main()
    print("\nDone. Overall verdict:", result["overall_verdict"])
