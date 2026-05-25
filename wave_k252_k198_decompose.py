"""Wave K252 — K198 Sub-Component Decomposition for Fold 2 Stabilization Analysis.

Objective:
  Decompose K198's 10 sub-components to identify which sub(s) drive
  fold 2 (2025-05-14 to 2025-09-01) outperformance vs K208.

Data sources:
  - wave_k192_curves.json  -> 8 base sub equity series (v4.1, V1, K114, K116, K121, K133, K147, K175_DAR)
  - wave_k195_curves.json  -> V_fwd_carry (V_eq_w panel)
  - wave_k196_curves.json  -> V_rev_carry (V_rev_eq_w panel)
  - wave_k198_curves.json  -> Ridge weight trajectory + blended PnL

Runtime: <12 min (typically <60s)
"""

from __future__ import annotations
import json
import math
import time
from pathlib import Path

import numpy as np
import pandas as pd

START = time.time()
BASE = Path("/Users/nekonaomichi/crypto-lab")

TRADING_DAYS = 365

# ── Fold definitions (from K229 ML window, 4-fold chronological) ─────────────
FOLD_DATES = [
    ("1", "2025-01-23", "2025-05-13"),
    ("2", "2025-05-14", "2025-09-01"),   # fold 2 = K198 stabilizer window
    ("3", "2025-09-02", "2025-12-21"),
    ("4", "2025-12-22", "2026-04-14"),
]

OOS_START = "2026-01-01"  # approx final 30% of ML window


# ─────────────────────────────────────────────────────────────────────────────
# Metrics
# ─────────────────────────────────────────────────────────────────────────────

def sharpe(r: np.ndarray) -> float:
    r = np.asarray(r, dtype=float)
    r = r[~np.isnan(r)]
    if len(r) < 2 or r.std(ddof=1) == 0:
        return 0.0
    return float(r.mean() / r.std(ddof=1) * math.sqrt(TRADING_DAYS))


def ann_ret(r: np.ndarray) -> float:
    r = np.asarray(r, dtype=float)
    r = r[~np.isnan(r)]
    if len(r) == 0:
        return 0.0
    return float((1.0 + r).prod() ** (TRADING_DAYS / len(r)) - 1.0)


def max_dd(r: np.ndarray) -> float:
    r = np.asarray(r, dtype=float)
    eq = np.cumprod(1.0 + r)
    peak = np.maximum.accumulate(eq)
    return float((eq / peak - 1.0).min())


# ─────────────────────────────────────────────────────────────────────────────
# Data loading
# ─────────────────────────────────────────────────────────────────────────────

def load_sub_returns() -> pd.DataFrame:
    """Load all 10 K198 sub-component daily return series aligned on common dates."""
    # --- 8 base components from K192 ---
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
        prev = np.r_[eq[0], eq[:-1]]          # day-0 ret = 0 (baseline)
        ret = eq / prev - 1.0
        ret[0] = 0.0                           # first day zero by construction
        base_df[col_name] = ret
    base_df.index.name = "date"

    # --- Forward carry from K195 ---
    with open(BASE / "wave_k195_curves.json") as f:
        k195 = json.load(f)
    k195_dates = pd.to_datetime(k195["panel_dates"])
    fwd_eq = np.array(k195["series"]["V_eq_w"], dtype=float)
    fwd_ret = pd.Series(
        np.r_[0.0, fwd_eq[1:] / fwd_eq[:-1] - 1.0],
        index=k195_dates,
        name="V_fwd_carry",
    )

    # --- Reverse carry from K196 ---
    with open(BASE / "wave_k196_curves.json") as f:
        k196 = json.load(f)
    k196_dates = pd.to_datetime(k196["panel_dates"])
    rev_eq = np.array(k196["series"]["V_rev_eq_w"], dtype=float)
    rev_ret = pd.Series(
        np.r_[0.0, rev_eq[1:] / rev_eq[:-1] - 1.0],
        index=k196_dates,
        name="V_rev_carry",
    )

    # --- Align on common dates ---
    all_start = max(base_df.index[0], fwd_ret.index[0], rev_ret.index[0])
    all_end   = min(base_df.index[-1], fwd_ret.index[-1], rev_ret.index[-1])

    df = pd.concat([
        base_df[(base_df.index >= all_start) & (base_df.index <= all_end)],
        fwd_ret[(fwd_ret.index >= all_start) & (fwd_ret.index <= all_end)],
        rev_ret[(rev_ret.index >= all_start) & (rev_ret.index <= all_end)],
    ], axis=1).sort_index()

    print(f"  Sub-component returns: {df.shape[0]} days × {df.shape[1]} series")
    print(f"  Date range: {df.index[0].date()} → {df.index[-1].date()}")
    return df


def load_k198_weights() -> pd.DataFrame:
    """Load K198 Ridge weight trajectory."""
    with open(BASE / "wave_k198_curves.json") as f:
        c = json.load(f)
    dates = pd.to_datetime(c["weight_trajectory_dates"])
    wt = c["weight_trajectory"]
    df = pd.DataFrame(wt, index=dates)
    df.index.name = "date"
    return df


def load_k198_blended_pnl() -> pd.Series:
    """Load K198 blended Ridge PnL series."""
    with open(BASE / "wave_k198_curves.json") as f:
        c = json.load(f)
    dates = pd.to_datetime(c["weight_trajectory_dates"])
    pnl   = np.array(c["pnl_ridge"], dtype=float)
    return pd.Series(pnl, index=dates, name="K198_blended")


# ─────────────────────────────────────────────────────────────────────────────
# Per-fold analysis
# ─────────────────────────────────────────────────────────────────────────────

def fold_slice(series: pd.DataFrame, fold_start: str, fold_end: str) -> pd.DataFrame:
    return series[(series.index >= fold_start) & (series.index <= fold_end)]


def fold_sharpes(df: pd.DataFrame) -> dict:
    """Per-fold Sharpe for each column in df."""
    result = {}
    for fname, fs, fe in FOLD_DATES:
        sl = fold_slice(df, fs, fe)
        result[f"fold{fname}"] = {
            col: round(sharpe(sl[col].values), 4)
            for col in df.columns
        }
    return result


def reconstruct_k198_weighted_daily(sub_ret: pd.DataFrame, wt_df: pd.DataFrame) -> pd.Series:
    """
    Reconstruct K198 blended return using the stored Ridge weight trajectory.
    Weight[t] from wt_df is applied to sub_ret[t].
    """
    common = sub_ret.index.intersection(wt_df.index)
    sub_c = sub_ret.loc[common]
    wt_c  = wt_df.loc[common]

    # align columns (sub_ret has 10 columns; wt_df also 10 in same order)
    cols = [c for c in wt_df.columns if c in sub_c.columns]
    daily_ret = (sub_c[cols].values * wt_c[cols].values).sum(axis=1)
    return pd.Series(daily_ret, index=common, name="K198_reconstructed")


# ─────────────────────────────────────────────────────────────────────────────
# Per-sub weighted contribution in each fold
# ─────────────────────────────────────────────────────────────────────────────

def fold_weighted_contributions(
    sub_ret: pd.DataFrame,
    wt_df: pd.DataFrame,
) -> dict:
    """
    Weighted daily PnL contribution per sub per fold.
    Returns {fold_name: {sub: weighted_sharpe}}.
    """
    result = {}
    for fname, fs, fe in FOLD_DATES:
        sr_sl = fold_slice(sub_ret, fs, fe)
        wt_sl = fold_slice(wt_df, fs, fe)
        common = sr_sl.index.intersection(wt_sl.index)
        sr_c = sr_sl.loc[common]
        wt_c = wt_sl.loc[common]

        cols = [c for c in wt_df.columns if c in sr_c.columns]
        weighted_pnl = {}
        for col in cols:
            w_pnl = sr_c[col].values * wt_c[col].values
            weighted_pnl[col] = {
                "avg_weight":  round(float(wt_c[col].mean()), 4),
                "sub_sharpe":  round(sharpe(sr_c[col].values), 4),
                "contrib_sh":  round(sharpe(w_pnl), 4),
                "contrib_ann_ret": round(ann_ret(w_pnl), 4),
            }
        result[f"fold{fname}"] = weighted_pnl
    return result


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    print("=== Wave K252: K198 Sub-Component Decomposition ===")

    # 1. Load data
    print("\n[1] Loading sub-component returns...")
    sub_ret = load_sub_returns()

    print("\n[2] Loading K198 Ridge weight trajectory...")
    wt_df = load_k198_weights()

    print("\n[3] Loading K198 blended PnL...")
    k198_blended = load_k198_blended_pnl()

    # 2. Standalone per-sub Sharpe per fold
    print("\n[4] Computing standalone per-sub Sharpe per fold...")
    # Restrict to ML window dates (K198 weight trajectory dates)
    ml_start = wt_df.index[0]
    ml_end   = wt_df.index[-1]
    sub_ml = sub_ret[(sub_ret.index >= ml_start) & (sub_ret.index <= ml_end)]

    standalone_folds = fold_sharpes(sub_ml)

    # 3. K198 weight averages per fold
    print("\n[5] Computing K198 Ridge weight averages per fold...")
    weight_by_fold = {}
    for fname, fs, fe in FOLD_DATES:
        sl = fold_slice(wt_df, fs, fe)
        weight_by_fold[f"fold{fname}"] = {
            col: round(float(sl[col].mean()), 4) for col in wt_df.columns
        }

    # 4. Reconstruct K198 blended from weights and check alignment
    print("\n[6] Reconstructing K198 blended return from weights...")
    k198_recon = reconstruct_k198_weighted_daily(sub_ret, wt_df)

    # correlation between stored blended and reconstructed (sanity check)
    common_idx = k198_blended.index.intersection(k198_recon.index)
    corr_sanity = float(np.corrcoef(
        k198_blended.loc[common_idx].values,
        k198_recon.loc[common_idx].values
    )[0, 1])
    print(f"  Sanity check — corr(stored_blended, reconstructed): {corr_sanity:.6f}")

    # 5. Weighted contribution per sub per fold
    print("\n[7] Computing weighted PnL contribution per sub per fold...")
    wt_contrib = fold_weighted_contributions(sub_ml, wt_df)

    # 6. Build fold 2 summary table
    fold2_data = standalone_folds.get("fold2", {})
    fold2_wts  = weight_by_fold.get("fold2", {})
    fold2_contrib = wt_contrib.get("fold2", {})

    print("\n──────────────────────────────────────────────────────")
    print("FOLD 2 (2025-05-14 to 2025-09-01) — Sub-Component Summary")
    print("──────────────────────────────────────────────────────")
    print(f"{'Sub':<15} {'Avg_Wt':>8} {'Sub_Sh':>8} {'Wtd_Sh':>8} {'AnnRet%':>10}")
    print("─" * 55)

    fold2_rows = []
    for sub in wt_df.columns:
        if sub not in fold2_contrib:
            continue
        row = fold2_contrib[sub]
        standalone_sh = fold2_data.get(sub, None)
        print(
            f"{sub:<15} {row['avg_weight']:>8.4f} "
            f"{standalone_sh if standalone_sh is not None else '-':>8} "
            f"{row['contrib_sh']:>8.4f} "
            f"{row['contrib_ann_ret']*100:>9.2f}%"
        )
        fold2_rows.append({
            "sub": sub,
            "avg_weight_fold2":     row["avg_weight"],
            "standalone_sharpe_fold2": standalone_sh,
            "contrib_sharpe_fold2":  row["contrib_sh"],
            "contrib_ann_ret_fold2": row["contrib_ann_ret"],
        })
    print("─" * 55)

    # 7. Identify dominant sub in fold 2
    sorted_by_contrib = sorted(fold2_rows, key=lambda x: x["contrib_sharpe_fold2"], reverse=True)
    top_subs = [r for r in sorted_by_contrib if r["contrib_sharpe_fold2"] > 0]
    top1 = sorted_by_contrib[0] if sorted_by_contrib else None

    print(f"\nTop sub by weighted Sharpe contribution in fold 2: {top1['sub'] if top1 else 'N/A'}")
    if top1:
        cumulative_top1 = top1["contrib_sharpe_fold2"]
        # Rough dominance: top sub contributes >50% of K198 fold2 Sh (7.37)
        k198_fold2_sh = 7.3739
        dominance_pct = cumulative_top1 / k198_fold2_sh * 100 if k198_fold2_sh != 0 else 0
        print(f"  Top sub weighted Sh = {cumulative_top1:.4f}, K198 fold2 Sh = {k198_fold2_sh:.4f}")
        print(f"  Dominance: {dominance_pct:.1f}% of K198 fold2 Sharpe")

    # 8. Cross-fold comparison table
    print("\n──────────────────────────────────────────────────────")
    print("STANDALONE SHARPE per sub per fold")
    print("──────────────────────────────────────────────────────")
    header = f"{'Sub':<15}"
    for fname, _, _ in FOLD_DATES:
        header += f" {'F'+fname:>8}"
    print(header)
    print("─" * 48)
    for sub in wt_df.columns:
        row = f"{sub:<15}"
        for fname, _, _ in FOLD_DATES:
            sh = standalone_folds.get(f"fold{fname}", {}).get(sub, None)
            row += f" {sh if sh is not None else '-':>8}"
        print(row)
    print("─" * 48)

    # 9. K198 weight evolution
    print("\n──────────────────────────────────────────────────────")
    print("K198 RIDGE WEIGHT AVERAGES per sub per fold")
    print("──────────────────────────────────────────────────────")
    header = f"{'Sub':<15}"
    for fname, _, _ in FOLD_DATES:
        header += f" {'F'+fname:>8}"
    print(header)
    print("─" * 48)
    for sub in wt_df.columns:
        row = f"{sub:<15}"
        for fname, _, _ in FOLD_DATES:
            w = weight_by_fold.get(f"fold{fname}", {}).get(sub, None)
            row += f" {w if w is not None else '-':>8}"
        print(row)
    print("─" * 48)

    # 10. Verdict on simplification
    print("\n──────────────────────────────────────────────────────")
    print("VERDICT ON K198 SIMPLIFICATION FEASIBILITY")
    print("──────────────────────────────────────────────────────")

    top3_subs = sorted_by_contrib[:3]
    top3_contrib = sum(r["contrib_sharpe_fold2"] for r in top3_subs if r["contrib_sharpe_fold2"] > 0)

    # Check if single sub dominates (>60% of K198 fold2 Sh)
    k198_fold2_sh = 7.3739
    if top1 and dominance_pct > 60:
        verdict = "POSSIBLE_SIMPLIFICATION"
        verdict_text = (
            f"Single sub '{top1['sub']}' contributes {dominance_pct:.1f}% of fold2 Sharpe.\n"
            f"  Consider replacing K198 with '{top1['sub']}' in K246a variant test.\n"
            f"  NOTE: verify that '{top1['sub']}' also holds in other folds before promoting."
        )
    else:
        verdict = "GENUINE_ENSEMBLE"
        verdict_text = (
            f"No single sub dominates fold 2 (top sub contributes {dominance_pct:.1f}% < 60%).\n"
            f"  K198 fold 2 strength = genuine ensemble diversification.\n"
            f"  Replacing K198 with any single sub would degrade fold 2 performance.\n"
            f"  Recommendation: KEEP K198 as ensemble — cannot simplify further."
        )

    print(f"  Verdict: {verdict}")
    print(f"  {verdict_text}")
    print(f"  Top 3 contributors in fold 2: {', '.join(r['sub'] for r in top3_subs)}")
    print(f"  Combined top-3 weighted Sharpe: {top3_contrib:.4f} vs K198 fold2 Sh: {k198_fold2_sh:.4f}")

    # ─────────────────────────────────────────────────────────────────────────
    # Build output JSON
    # ─────────────────────────────────────────────────────────────────────────
    runtime = round(time.time() - START, 2)
    out_json = {
        "wave": "K252",
        "task": "K198 Sub-Component Decomposition — Fold 2 Stabilization Analysis",
        "as_of": pd.Timestamp.utcnow().isoformat(),
        "runtime_s": runtime,
        "data_info": {
            "n_days_ml_window": int(len(sub_ml)),
            "ml_window_start": str(sub_ml.index[0].date()),
            "ml_window_end":   str(sub_ml.index[-1].date()),
            "sub_components":  list(wt_df.columns),
            "sanity_corr_stored_vs_reconstructed": round(corr_sanity, 6),
        },
        "fold_definitions": [
            {"fold": f, "start": s, "end": e} for f, s, e in FOLD_DATES
        ],
        "standalone_sharpe_per_fold": standalone_folds,
        "weight_by_fold": weight_by_fold,
        "weighted_contribution_per_fold": wt_contrib,
        "fold2_summary": {
            "fold2_start": "2025-05-14",
            "fold2_end":   "2025-09-01",
            "k198_fold2_sharpe": k198_fold2_sh,
            "k208_fold2_sharpe": 5.7585,
            "k198_advantage_vs_k208": round(k198_fold2_sh - 5.7585, 4),
            "sub_ranking_by_contrib_sharpe": fold2_rows,
            "top_contributor": {
                "sub":          top1["sub"] if top1 else None,
                "contrib_sh":   top1["contrib_sharpe_fold2"] if top1 else None,
                "dominance_pct": round(dominance_pct, 1) if top1 else None,
            },
        },
        "verdict": {
            "code":        verdict,
            "description": verdict_text,
            "top3_subs":   [r["sub"] for r in top3_subs],
            "top3_combined_contrib_sh": round(top3_contrib, 4),
        },
    }

    out_path = BASE / "wave_k252_k198_decompose.json"
    with open(out_path, "w") as f:
        json.dump(out_json, f, indent=2, default=str)
    print(f"\n  JSON saved: {out_path}")

    # ─────────────────────────────────────────────────────────────────────────
    # Build equity curves JSON (per-sub equity on ML window)
    # ─────────────────────────────────────────────────────────────────────────
    curves_out = {
        "dates": [str(d.date()) for d in sub_ml.index],
        "series": {},
    }
    for col in sub_ml.columns:
        eq = (1.0 + sub_ml[col]).cumprod().tolist()
        curves_out["series"][col] = [round(v, 8) for v in eq]

    # Also add K198 blended (reconstructed)
    k198_ml = k198_recon[(k198_recon.index >= ml_start) & (k198_recon.index <= ml_end)]
    k198_ml_aligned = k198_ml.reindex(sub_ml.index).fillna(0.0)
    curves_out["series"]["K198_blended"] = [
        round(v, 8) for v in (1.0 + k198_ml_aligned).cumprod().tolist()
    ]

    curves_path = BASE / "wave_k252_curves.json"
    with open(curves_path, "w") as f:
        json.dump(curves_out, f)
    print(f"  Curves saved: {curves_path}")

    print(f"\n  Total runtime: {runtime:.2f}s")
    return out_json


if __name__ == "__main__":
    main()
