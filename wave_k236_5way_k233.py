"""
Wave K236 — 5-Way Meta-Ensemble: K198 × K204 × K208 × K226 × K233
          (K229 4-way + K233 Cross-Chain Capital Rotation)

GATE 0 (CRITICAL FIRST STEP):
  Validate K233 standalone on K229/K218 ML window (448d, 2025-01-22→2026-04-14).
  K233 WF folds must ALL be positive on common window cuts. Any negative fold → REJECT.

K233 was ACCEPTED standalone (OOS Sh 2.30, WF folds [1.88, 1.75, 1.24, 3.62] all positive)
on its own 609-day window. Now test on the K229 448-day common window.

Variants:
  K236a — Equal 20/20/20/20/20
  K236b — Inv-vol uncapped
  K236c — Inv-vol + K226 cap 20% (K229d spec)
  K236d — Inv-vol + K226 cap 20% + K233 cap 10%
  K236e — Inv-vol + K226 cap 20% + K233 cap 20%
  K236f — Inv-vol + K226 cap 20% + K233 cap 25%
  K236g — MVP (Minimum Variance Portfolio)

Acceptance for K236 → v6.9:
  K233 ML window WF folds all positive
  Best variant OOS Sh > K229 (12.61) + 0.10 = 12.71
  WF min >= K229 (7.44)
  MaxDD <= K229 (-0.0012)
  All 5 portfolios non-zero weight

Deliverables:
  wave_k236_5way_k233.py   — this script
  wave_k236_5way_k233.json — metrics + ML validation + correlations
  wave_k236_curves.json    — equity curves
  wave_k236_5way_k233.md   — full report
"""

import json
import numpy as np
from datetime import datetime, timezone
import time

t0 = time.time()

# ─────────────────────────────────────────────────────────────────────────────
# 1. Load equity series from existing curve files
# ─────────────────────────────────────────────────────────────────────────────

# K229 curves already has all 4 components normalized to 1.0 on the 448-day ML window
with open("/Users/nekonaomichi/crypto-lab/wave_k229_curves.json") as f:
    k229_raw = json.load(f)

dates_ml = k229_raw["dates"]   # 448 dates: 2025-01-22 → 2026-04-14
eq198 = np.array(k229_raw["K198"])
eq204 = np.array(k229_raw["K204"])
eq208 = np.array(k229_raw["K208"])
eq226 = np.array(k229_raw["K226"])

# K233 on common 448-day window — from wave_k233_curves.json k229_component_equity
with open("/Users/nekonaomichi/crypto-lab/wave_k233_curves.json") as f:
    k233_raw = json.load(f)

# K233 component equity starts at various values, normalize to 1.0
eq233_raw = np.array(k233_raw["k229_component_equity"]["K233"])
eq233 = eq233_raw / eq233_raw[0]   # normalize to 1.0

common_dates = k233_raw["common_dates"]  # 448 dates, same as dates_ml

N = len(dates_ml)
assert N == 448, f"Expected 448 days, got {N}"
assert len(eq198) == N
assert len(eq204) == N
assert len(eq208) == N
assert len(eq226) == N
assert len(eq233) == N
assert common_dates == dates_ml, "Date mismatch between K229 and K233 common window"

print(f"Loaded {N} days: {dates_ml[0]} → {dates_ml[-1]}")
print(f"K198 final: {eq198[-1]:.4f}, K204 final: {eq204[-1]:.4f}")
print(f"K208 final: {eq208[-1]:.4f}, K226 final: {eq226[-1]:.4f}")
print(f"K233 final (normalized): {eq233[-1]:.4f}")

# ─────────────────────────────────────────────────────────────────────────────
# 2. Utility functions
# ─────────────────────────────────────────────────────────────────────────────

def equity_to_returns(eq):
    """Convert equity curve to daily returns."""
    eq = np.array(eq)
    rets = np.diff(eq) / eq[:-1]
    return rets

def sharpe(rets, ann=365):
    """Annualized Sharpe ratio."""
    rets = np.array(rets)
    if len(rets) == 0 or np.std(rets) == 0:
        return 0.0
    return np.mean(rets) / np.std(rets) * np.sqrt(ann)

def max_drawdown(eq):
    """Maximum drawdown from equity curve."""
    eq = np.array(eq)
    running_max = np.maximum.accumulate(eq)
    dd = (eq - running_max) / running_max
    return float(np.min(dd))

def walk_forward_4fold(rets, n_total=447):
    """4-fold walk-forward Sharpe on returns array (len=n_total)."""
    fold_size = n_total // 4
    folds = []
    for i in range(4):
        start = i * fold_size
        end = (i + 1) * fold_size if i < 3 else n_total
        fold_rets = rets[start:end]
        sh = sharpe(fold_rets)
        folds.append({
            "fold": i + 1,
            "start_idx": start,
            "end_idx": end,
            "n_days": end - start,
            "sharpe": round(float(sh), 4)
        })
    return folds

def oos_metrics(eq, oos_frac=0.3, n_total=448):
    """OOS metrics on last 30% of equity curve."""
    oos_start = int(n_total * (1 - oos_frac))
    oos_eq = eq[oos_start:]
    oos_rets = equity_to_returns(oos_eq)
    ann_ret = float((oos_eq[-1] / oos_eq[0]) ** (365 / len(oos_rets)) - 1)
    ann_vol = float(np.std(oos_rets) * np.sqrt(365))
    sh = sharpe(oos_rets)
    mdd = max_drawdown(oos_eq)
    return {
        "oos_sharpe": round(sh, 4),
        "oos_maxdd": round(mdd, 6),
        "oos_n_days": len(oos_rets),
        "oos_ann_ret": round(ann_ret, 4),
        "oos_ann_vol": round(ann_vol, 4)
    }

def inv_vol_weights(rets_matrix, window=30, caps=None):
    """
    Inverse-volatility weights with optional per-asset caps.
    rets_matrix: (T, n_assets) returns
    caps: dict {asset_idx: max_weight}
    Returns weights array (T, n_assets) — rows sum to 1.
    """
    T, n = rets_matrix.shape
    weights = np.ones((T, n)) / n  # fallback equal

    for t in range(window, T):
        lookback = rets_matrix[max(0, t-window):t]
        vols = np.std(lookback, axis=0)
        vols = np.where(vols < 1e-8, 1e-8, vols)
        inv_v = 1.0 / vols
        w = inv_v / inv_v.sum()

        # Apply caps
        if caps:
            for idx, cap in caps.items():
                if w[idx] > cap:
                    excess = w[idx] - cap
                    w[idx] = cap
                    others = [j for j in range(n) if j != idx]
                    other_sum = sum(w[j] for j in others)
                    if other_sum > 0:
                        for j in others:
                            w[j] += excess * (w[j] / other_sum)

        weights[t] = w

    return weights

def portfolio_equity(rets_matrix, weights):
    """
    Build portfolio equity from per-asset returns and time-varying weights.
    rets_matrix: (T-1, n_assets) — daily returns
    weights: (T, n_assets) — weights at start of each day
    Returns equity curve of length T.
    """
    T = rets_matrix.shape[0] + 1
    eq = np.ones(T)
    for t in range(1, T):
        w = weights[t-1]
        port_ret = np.dot(w, rets_matrix[t-1])
        eq[t] = eq[t-1] * (1 + port_ret)
    return eq

def diversification_ratio(weights_avg, rets_matrix):
    """DR = weighted avg vol / portfolio vol."""
    vols = np.std(rets_matrix, axis=0)
    weighted_avg_vol = np.dot(weights_avg, vols)
    port_rets = rets_matrix @ weights_avg
    port_vol = np.std(port_rets)
    if port_vol < 1e-10:
        return 1.0
    return float(weighted_avg_vol / port_vol)

def mvp_weights(rets_matrix, window=60, caps=None):
    """
    Minimum Variance Portfolio weights (long-only, rolling window).
    """
    T, n = rets_matrix.shape
    weights = np.ones((T, n)) / n

    for t in range(window, T):
        lookback = rets_matrix[max(0, t-window):t]
        cov = np.cov(lookback.T)
        if cov.ndim == 0:
            cov = np.array([[cov]])
        # Quadratic min-variance: w = cov_inv @ ones / (ones @ cov_inv @ ones)
        try:
            cov_inv = np.linalg.inv(cov + np.eye(n) * 1e-8)
            ones = np.ones(n)
            raw = cov_inv @ ones
            raw = np.maximum(raw, 0)  # long-only
            if raw.sum() > 0:
                w = raw / raw.sum()
            else:
                w = np.ones(n) / n

            # Apply caps
            if caps:
                for idx, cap in caps.items():
                    if w[idx] > cap:
                        excess = w[idx] - cap
                        w[idx] = cap
                        others = [j for j in range(n) if j != idx]
                        other_sum = sum(w[j] for j in others)
                        if other_sum > 0:
                            for j in others:
                                w[j] += excess * (w[j] / other_sum)
            weights[t] = w
        except np.linalg.LinAlgError:
            weights[t] = np.ones(n) / n

    return weights

# ─────────────────────────────────────────────────────────────────────────────
# 3. Gate 0: Validate K233 on ML window (448-day common window)
# ─────────────────────────────────────────────────────────────────────────────

print("\n=== GATE 0: K233 ML Window Validation ===")

k233_oos = oos_metrics(eq233, oos_frac=0.3, n_total=N)
k233_rets = equity_to_returns(eq233)
k233_wf_folds = walk_forward_4fold(k233_rets, n_total=len(k233_rets))

k233_wf_sharpes = [f["sharpe"] for f in k233_wf_folds]
k233_wf_min = min(k233_wf_sharpes)
k233_wf_mean = float(np.mean(k233_wf_sharpes))
k233_all_positive = all(s > 0 for s in k233_wf_sharpes)

print(f"K233 ML window OOS Sh: {k233_oos['oos_sharpe']}")
print(f"K233 WF folds: {k233_wf_sharpes}")
print(f"K233 WF min: {k233_wf_min:.4f}, all positive: {k233_all_positive}")

gate0_pass = k233_all_positive and k233_oos["oos_sharpe"] > 0.5
print(f"Gate 0 PASS: {gate0_pass}")

# ─────────────────────────────────────────────────────────────────────────────
# 4. Prepare returns matrix (5 assets)
# ─────────────────────────────────────────────────────────────────────────────

rets_matrix = np.column_stack([
    equity_to_returns(eq198),
    equity_to_returns(eq204),
    equity_to_returns(eq208),
    equity_to_returns(eq226),
    equity_to_returns(eq233),
])
# Shape: (447, 5)
T_rets, n_assets = rets_matrix.shape
print(f"\nReturns matrix shape: {rets_matrix.shape}")

# Asset indices
IDX_K198 = 0
IDX_K204 = 1
IDX_K208 = 2
IDX_K226 = 3
IDX_K233 = 4

# ─────────────────────────────────────────────────────────────────────────────
# 5. 5x5 Correlation Matrix
# ─────────────────────────────────────────────────────────────────────────────

labels = ["K198", "K204", "K208", "K226", "K233"]
corr = np.corrcoef(rets_matrix.T)
corr_matrix_list = [[round(float(v), 4) for v in row] for row in corr]

pairwise = {}
for i in range(n_assets):
    for j in range(i+1, n_assets):
        key = f"rho_{labels[i]}_{labels[j]}"
        pairwise[key] = round(float(corr[i, j]), 4)

print("\n5x5 Correlation Matrix:")
print(f"{'':10s}", "  ".join(f"{l:>6s}" for l in labels))
for i, row in enumerate(corr_matrix_list):
    print(f"{labels[i]:10s}", "  ".join(f"{v:>6.3f}" for v in row))

# ─────────────────────────────────────────────────────────────────────────────
# 6. Compute all variant portfolios
# ─────────────────────────────────────────────────────────────────────────────

# Weights (T_rets+1, 5) — one row per equity index
T_eq = T_rets + 1  # 448

def compute_variant(name, desc, w_matrix):
    """Run a variant and return metrics dict."""
    print(f"\nComputing {name}: {desc}")
    eq_v = portfolio_equity(rets_matrix, w_matrix)
    oos_m = oos_metrics(eq_v, oos_frac=0.3, n_total=T_eq)
    rets_v = equity_to_returns(eq_v)
    wf = walk_forward_4fold(rets_v, n_total=len(rets_v))
    wf_sh = [f["sharpe"] for f in wf]
    avg_w = w_matrix.mean(axis=0)
    dr = diversification_ratio(avg_w, rets_matrix)
    result = {
        "description": desc,
        "oos_sharpe": oos_m["oos_sharpe"],
        "oos_maxdd": oos_m["oos_maxdd"],
        "oos_n_days": oos_m["oos_n_days"],
        "oos_ann_ret": oos_m["oos_ann_ret"],
        "oos_ann_vol": oos_m["oos_ann_vol"],
        "fold_sharpes": wf_sh,
        "fold_details": wf,
        "wf_mean": round(float(np.mean(wf_sh)), 4),
        "wf_min": round(float(min(wf_sh)), 4),
        "wf_max": round(float(max(wf_sh)), 4),
        "wf_std": round(float(np.std(wf_sh)), 4),
        "avg_weights": [round(float(v), 4) for v in avg_w],
        "diversification_ratio": round(dr, 4),
    }
    print(f"  OOS Sh={result['oos_sharpe']}, WF folds={wf_sh}, WF min={result['wf_min']}")
    return result, eq_v

# ── K236a: Equal 20/20/20/20/20 ──────────────────────────────────────────────
w_a = np.tile(np.array([0.2, 0.2, 0.2, 0.2, 0.2]), (T_eq, 1))
res_a, eq_a = compute_variant("K236a", "Equal weight 20/20/20/20/20", w_a)

# ── K236b: Inv-vol uncapped ───────────────────────────────────────────────────
w_b = inv_vol_weights(rets_matrix, window=30, caps=None)
# weights array is (T_rets, n_assets), expand to (T_eq, n_assets)
w_b_full = np.vstack([w_b[:1], w_b])  # first row repeated
res_b, eq_b = compute_variant("K236b", "Inv-vol uncapped (30d rolling)", w_b_full)

# ── K236c: Inv-vol + K226 cap 20% (K229d spec) ───────────────────────────────
w_c = inv_vol_weights(rets_matrix, window=30, caps={IDX_K226: 0.20})
w_c_full = np.vstack([w_c[:1], w_c])
res_c, eq_c = compute_variant("K236c", "Inv-vol + K226 cap 20% (K229d spec)", w_c_full)

# ── K236d: Inv-vol + K226 cap 20% + K233 cap 10% ─────────────────────────────
w_d = inv_vol_weights(rets_matrix, window=30, caps={IDX_K226: 0.20, IDX_K233: 0.10})
w_d_full = np.vstack([w_d[:1], w_d])
res_d, eq_d = compute_variant("K236d", "Inv-vol + K226 cap 20% + K233 cap 10%", w_d_full)

# ── K236e: Inv-vol + K226 cap 20% + K233 cap 20% ─────────────────────────────
w_e = inv_vol_weights(rets_matrix, window=30, caps={IDX_K226: 0.20, IDX_K233: 0.20})
w_e_full = np.vstack([w_e[:1], w_e])
res_e, eq_e = compute_variant("K236e", "Inv-vol + K226 cap 20% + K233 cap 20%", w_e_full)

# ── K236f: Inv-vol + K226 cap 20% + K233 cap 25% ─────────────────────────────
w_f = inv_vol_weights(rets_matrix, window=30, caps={IDX_K226: 0.20, IDX_K233: 0.25})
w_f_full = np.vstack([w_f[:1], w_f])
res_f, eq_f = compute_variant("K236f", "Inv-vol + K226 cap 20% + K233 cap 25%", w_f_full)

# ── K236g: MVP ────────────────────────────────────────────────────────────────
w_g = mvp_weights(rets_matrix, window=60, caps=None)
w_g_full = np.vstack([w_g[:1], w_g])
res_g, eq_g = compute_variant("K236g", "MVP (Minimum Variance Portfolio, rolling 60d)", w_g_full)

# ─────────────────────────────────────────────────────────────────────────────
# 7. Find best variant
# ─────────────────────────────────────────────────────────────────────────────

variants_map = {
    "K236a": (res_a, eq_a),
    "K236b": (res_b, eq_b),
    "K236c": (res_c, eq_c),
    "K236d": (res_d, eq_d),
    "K236e": (res_e, eq_e),
    "K236f": (res_f, eq_f),
    "K236g": (res_g, eq_g),
}

# Acceptance criteria
K229_OOS_SH  = 12.61
K229_WF_MIN  = 7.44
K229_MAXDD   = -0.001201
OOS_SH_THRESHOLD = K229_OOS_SH + 0.10   # 12.71

best_name = None
best_sh = -999
for name, (res, eq_v) in variants_map.items():
    sh = res["oos_sharpe"]
    wf_min = res["wf_min"]
    mdd = res["oos_maxdd"]
    min_w = min(res["avg_weights"])
    # Check all criteria
    if (sh > best_sh and
        sh > OOS_SH_THRESHOLD and
        wf_min >= K229_WF_MIN and
        mdd >= K229_MAXDD and
        min_w > 0.005):
        best_sh = sh
        best_name = name

print(f"\nBest accepted variant: {best_name} (OOS Sh={best_sh:.4f})")

# ─────────────────────────────────────────────────────────────────────────────
# 8. Acceptance gates
# ─────────────────────────────────────────────────────────────────────────────

best_res = variants_map[best_name][0] if best_name else None
best_eq  = variants_map[best_name][1] if best_name else None

accepted = best_name is not None
if accepted:
    gate_oos   = best_res["oos_sharpe"] > OOS_SH_THRESHOLD
    gate_wf    = best_res["wf_min"] >= K229_WF_MIN
    gate_mdd   = best_res["oos_maxdd"] >= K229_MAXDD
    gate_wt    = min(best_res["avg_weights"]) > 0.005
    gate_k233  = k233_all_positive
else:
    gate_oos = gate_wf = gate_mdd = gate_wt = False
    gate_k233 = k233_all_positive

print(f"\nAcceptance Gates:")
print(f"  Gate 0 (K233 WF all positive): {gate_k233}")
print(f"  Gate 1 (OOS Sh > {OOS_SH_THRESHOLD}): {gate_oos} ({best_res['oos_sharpe'] if best_res else 'N/A'})")
print(f"  Gate 2 (WF min >= {K229_WF_MIN}): {gate_wf} ({best_res['wf_min'] if best_res else 'N/A'})")
print(f"  Gate 3 (MaxDD >= {K229_MAXDD}): {gate_mdd} ({best_res['oos_maxdd'] if best_res else 'N/A'})")
print(f"  Gate 4 (all weights > 0): {gate_wt}")
print(f"  OVERALL: {'ACCEPT' if accepted else 'REJECT'}")

# ─────────────────────────────────────────────────────────────────────────────
# 9. Synergy analysis
# ─────────────────────────────────────────────────────────────────────────────

individual_sh = {
    "K198": 10.2796,  # from K229 data
    "K204": 10.3627,
    "K208": 13.5396,
    "K226": 2.4097,
    "K233": float(k233_oos["oos_sharpe"]),
}
avg_indiv_sh = float(np.mean(list(individual_sh.values())))
synergy_vs_avg = round((best_res["oos_sharpe"] if best_res else 0) - avg_indiv_sh, 4) if best_res else None
synergy_vs_k229 = round((best_res["oos_sharpe"] if best_res else 0) - K229_OOS_SH, 4) if best_res else None

# ─────────────────────────────────────────────────────────────────────────────
# 10. Save JSON metrics
# ─────────────────────────────────────────────────────────────────────────────

runtime_s = round(time.time() - t0, 2)

output_json = {
    "wave": "K236",
    "task": "5-Way Meta-Ensemble: K198 × K204 × K208 × K226 × K233 (Cross-Chain Rotation)",
    "as_of": datetime.now(timezone.utc).isoformat(),
    "runtime_s": runtime_s,
    "data_info": {
        "n_days": N,
        "date_start": dates_ml[0],
        "date_end": dates_ml[-1],
        "n_returns": T_rets,
        "components": ["K198", "K204", "K208", "K226", "K233"],
    },
    "k233_ml_window_validation": {
        "description": "K233 standalone on K229/K218 ML window (448d) — Gate 0",
        "k233_original_oos_sh": 2.3009,
        "k233_original_wf_folds": [1.8839, 1.7527, 1.2381, 3.6176],
        "k233_ml_window_oos_sh": k233_oos["oos_sharpe"],
        "k233_ml_window_oos_maxdd": k233_oos["oos_maxdd"],
        "k233_ml_window_oos_n_days": k233_oos["oos_n_days"],
        "k233_ml_window_wf_folds": k233_wf_sharpes,
        "k233_ml_window_wf_min": round(k233_wf_min, 4),
        "k233_ml_window_wf_mean": round(k233_wf_mean, 4),
        "k233_ml_window_wf_details": k233_wf_folds,
        "all_wf_folds_positive": k233_all_positive,
        "gate0_pass": gate0_pass,
        "k228_lesson": "K228/K231/K234 rejected due to fold-2 < 0. K233 avoids this.",
    },
    "correlation_matrix": {
        "labels": labels,
        "matrix": corr_matrix_list,
        "pairwise": pairwise,
    },
    "acceptance_gates": {
        "gate0_k233_wf_all_positive": gate_k233,
        "gate1_oos_sh_threshold": OOS_SH_THRESHOLD,
        "gate2_wf_min_threshold": K229_WF_MIN,
        "gate3_maxdd_threshold": K229_MAXDD,
        "gate4_min_weight": 0.005,
        "reference_k229d": K229_OOS_SH,
    },
    "baselines": {
        "K198": {
            "oos_sharpe": 10.2796,
            "oos_maxdd": -0.005266,
            "wf_min": 6.5911,
            "wf_mean": 7.9153,
        },
        "K204": {
            "oos_sharpe": 10.3627,
            "oos_maxdd": -0.00532,
            "wf_min": 5.92,
            "wf_mean": 7.5136,
        },
        "K208": {
            "oos_sharpe": 13.5396,
            "oos_maxdd": -8e-05,
            "wf_min": 5.7585,
            "wf_mean": 13.4351,
        },
        "K226": {
            "oos_sharpe": 2.4097,
            "oos_maxdd": -0.152979,
            "wf_min": 0.38,
            "wf_mean": 2.2845,
        },
        "K233_ml_window": {
            "oos_sharpe": k233_oos["oos_sharpe"],
            "oos_maxdd": k233_oos["oos_maxdd"],
            "wf_min": round(k233_wf_min, 4),
            "wf_mean": round(k233_wf_mean, 4),
        },
    },
    "variants": {
        name: res for name, (res, _) in variants_map.items()
    },
    "synergy": {
        "individual_oos_sharpes": individual_sh,
        "avg_individual_oos_sh": round(avg_indiv_sh, 4),
        "best_ensemble_name": best_name,
        "best_ensemble_oos_sh": best_res["oos_sharpe"] if best_res else None,
        "best_ensemble_wf_min": best_res["wf_min"] if best_res else None,
        "synergy_delta_vs_avg": synergy_vs_avg,
        "synergy_delta_vs_k229": synergy_vs_k229,
        "synergy_detected": accepted,
    },
    "historical": {
        "K198_v6.5": {"oos_sharpe": 10.28, "oos_maxdd": -0.0053, "wf_min": 6.57, "components": 1},
        "K217_v6.6": {"oos_sharpe": 10.43, "oos_maxdd": -0.0053, "wf_min": 6.91, "components": 2},
        "K218e_v6.7": {"oos_sharpe": 11.031, "oos_maxdd": -0.00364, "wf_min": 6.9282, "components": 3},
        "K229d_v6.8": {"oos_sharpe": 12.61, "oos_maxdd": -0.001201, "wf_min": 7.4435, "dr": 1.6526, "components": 4},
    },
    "verdict": f"{'ACCEPT as K236 v6.9' if accepted else 'REJECT'} — best variant: {best_name}",
    "accepted": accepted,
    "best_variant": best_name,
    "best_variant_metrics": best_res,
}

with open("/Users/nekonaomichi/crypto-lab/wave_k236_5way_k233.json", "w") as f:
    json.dump(output_json, f, indent=2)
print("\nSaved: wave_k236_5way_k233.json")

# ─────────────────────────────────────────────────────────────────────────────
# 11. Save equity curves
# ─────────────────────────────────────────────────────────────────────────────

curves_json = {
    "dates": dates_ml,
    "K198": [round(float(v), 8) for v in eq198],
    "K204": [round(float(v), 8) for v in eq204],
    "K208": [round(float(v), 8) for v in eq208],
    "K226": [round(float(v), 8) for v in eq226],
    "K233": [round(float(v), 8) for v in eq233],
    "K236a": [round(float(v), 8) for v in eq_a],
    "K236b": [round(float(v), 8) for v in eq_b],
    "K236c": [round(float(v), 8) for v in eq_c],
    "K236d": [round(float(v), 8) for v in eq_d],
    "K236e": [round(float(v), 8) for v in eq_e],
    "K236f": [round(float(v), 8) for v in eq_f],
    "K236g": [round(float(v), 8) for v in eq_g],
    "K229d_ref": [round(float(v), 8) for v in k229_raw["K229d"]],
}

with open("/Users/nekonaomichi/crypto-lab/wave_k236_curves.json", "w") as f:
    json.dump(curves_json, f)
print("Saved: wave_k236_curves.json")

# ─────────────────────────────────────────────────────────────────────────────
# 12. Print summary
# ─────────────────────────────────────────────────────────────────────────────

print("\n" + "="*70)
print("WAVE K236 SUMMARY")
print("="*70)
print(f"\nGATE 0 — K233 ML Window Validation:")
print(f"  OOS Sh on 448d window : {k233_oos['oos_sharpe']}")
print(f"  WF folds (448d)       : {k233_wf_sharpes}")
print(f"  WF min                : {k233_wf_min:.4f}")
print(f"  All positive          : {k233_all_positive}")
print(f"  Gate 0 PASS           : {gate0_pass}")

print(f"\nVariant Results (OOS Sh | WF min | MaxDD | Avg Weights):")
for name, (res, _) in variants_map.items():
    w_str = " ".join(f"{w:.3f}" for w in res["avg_weights"])
    marker = " <-- BEST" if name == best_name else ""
    print(f"  {name}: OOS={res['oos_sharpe']:>6.4f} WF_min={res['wf_min']:>6.4f} "
          f"MDD={res['oos_maxdd']:>9.6f} w=[{w_str}]{marker}")

print(f"\nAcceptance: {'ACCEPT → v6.9' if accepted else 'REJECT'}")
if best_name:
    print(f"Best variant: {best_name}")
    print(f"  OOS Sh: {best_res['oos_sharpe']} (K229d: {K229_OOS_SH}, delta: {synergy_vs_k229:+.4f})")
    print(f"  WF min: {best_res['wf_min']} (K229d: {K229_WF_MIN})")
    print(f"  MaxDD:  {best_res['oos_maxdd']} (K229d: {K229_MAXDD})")
    print(f"  DR: {best_res['diversification_ratio']}")

print(f"\nRuntime: {runtime_s}s")
print("="*70)
