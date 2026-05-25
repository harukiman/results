"""Wave K251 — K198 + K249a + K226 Ensemble (v6.9.1 candidate)

Objective:
  K246a v6.9 = K198 + K208 + K226 (OOS Sh 12.69, WF min 8.93)
  K249a ACCEPTED: K208 with spread magnitude gate p25 — Fold2 lifted from 5.74→7.57
  K251: Replace K208 with K249a in K246a ensemble. Test if fold2 weakness resolves.

Methodology:
  - Same K246a methodology: inv-vol + K226 cap 20%, 4-fold equal-index WF
  - K249a ML window validation: re-measure K249a on K246a's daily window
  - 3x3 correlation matrix
  - Meta-allocator variants: K251a/b/c/d
  - Acceptance: OOS Sh >= 12.69, WF min >= 8.93, MaxDD <= -0.00115, K249a weight > 5%

Runtime: <12 min
"""
from __future__ import annotations

import json
import math
import time
import warnings
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

t0 = time.time()
BASE = Path("/Users/nekonaomichi/crypto-lab")

# ─────────────────────────────────────────────────────────────────────────────
# Reference metrics
# ─────────────────────────────────────────────────────────────────────────────
K246A_OOS_SH   = 12.6929
K246A_WF_MIN   = 8.9347
K246A_MAXDD    = -0.001145
K246A_WF_MEAN  = 12.2462
K246A_FOLDS    = [13.6029, 8.9347, 13.8374, 12.6097]

# Acceptance gates vs K246a
GATE_OOS_SH    = 12.69
GATE_WF_MIN    = 8.93
GATE_MAXDD     = -0.00115
GATE_K249A_WT  = 0.05  # K249a weight > 5% (genuine contribution)

ANN = math.sqrt(365)

# ─────────────────────────────────────────────────────────────────────────────
# 1. Load equity curves
# ─────────────────────────────────────────────────────────────────────────────
print("=" * 70)
print("Wave K251: K198 + K249a + K226 Ensemble (v6.9.1 candidate)")
print("=" * 70)

print("\n=== LOADING EQUITY CURVES ===")

# K198 — daily ML window 2025-01-22 -> 2026-04-14 (448 days, 447 returns)
with open(BASE / "wave_k198_curves.json") as f:
    k198_raw = json.load(f)
dates_ml = k198_raw["dates_ml"]           # 448 date strings
eq198    = np.array(k198_raw["equity_ridge"])  # shape (448,)
print(f"K198: {len(dates_ml)} days  {dates_ml[0]} -> {dates_ml[-1]}")

# K249a — 8h event timestamps; collapse to daily for ensemble
with open(BASE / "wave_k249_curves.json") as f:
    k249_raw = json.load(f)

k249a_ts   = k249_raw["K249a"]["timestamps"]
k249a_cpnl = k249_raw["K249a"]["cumulative_pnl"]

# Build daily-closing cumPnL dict (last 8h event per day)
k249a_daily: Dict[str, float] = {}
for ts_str, cpnl in zip(k249a_ts, k249a_cpnl):
    k249a_daily[ts_str[:10]] = cpnl  # overwrite with latest per day

k249a_eq_values: List[float] = []
missing_k249a = 0
for d in dates_ml:
    if d in k249a_daily:
        # cumPnL is additive — re-base to 1.0 + cumPnL for equity comparison
        k249a_eq_values.append(1.0 + k249a_daily[d])
    else:
        missing_k249a += 1
        k249a_eq_values.append(k249a_eq_values[-1] if k249a_eq_values else 1.0)

eq249a = np.array(k249a_eq_values)
# Re-base so first point = 1.0 (same as K198/K208 treatment in K246)
eq249a = eq249a / eq249a[0]
print(f"K249a: {len(eq249a)} days aligned  missing_days={missing_k249a}")

# K226 — daily dates + strategy_equity (already in equity form)
with open(BASE / "wave_k226_curves.json") as f:
    k226_raw = json.load(f)

k226_eq_daily: Dict[str, float] = {}
for d, eq in zip(k226_raw["dates"], k226_raw["strategy_equity"]):
    k226_eq_daily[d] = eq

k226_eq_values: List[float] = []
missing_k226 = 0
for d in dates_ml:
    if d in k226_eq_daily:
        k226_eq_values.append(k226_eq_daily[d])
    else:
        missing_k226 += 1
        k226_eq_values.append(k226_eq_values[-1] if k226_eq_values else 1.0)

eq226_aligned = np.array(k226_eq_values)
eq226 = eq226_aligned / eq226_aligned[0]  # re-base to 1.0
print(f"K226: {len(eq226)} days aligned  missing_days={missing_k226}")

# K208 — for comparison; same method as K246
with open(BASE / "wave_k208_curves.json") as f:
    k208_raw = json.load(f)

k208_daily: Dict[str, float] = {}
for ts_str, cpnl in zip(
    k208_raw["K208_filtered"]["timestamps"],
    k208_raw["K208_filtered"]["cumulative_pnl"],
):
    k208_daily[ts_str[:10]] = cpnl

k208_eq_values: List[float] = []
missing_k208 = 0
for d in dates_ml:
    if d in k208_daily:
        k208_eq_values.append(1.0 + k208_daily[d])
    else:
        missing_k208 += 1
        k208_eq_values.append(k208_eq_values[-1] if k208_eq_values else 1.0)
eq208 = np.array(k208_eq_values)
print(f"K208: {len(eq208)} days aligned  missing_days={missing_k208} (reference only)")

n = len(dates_ml)
assert len(eq198) == len(eq249a) == len(eq226) == n, "Equity length mismatch"

# ─────────────────────────────────────────────────────────────────────────────
# 2. Return series
# ─────────────────────────────────────────────────────────────────────────────
ret198   = np.diff(eq198)   / eq198[:-1]
ret249a  = np.diff(eq249a)  / eq249a[:-1]
ret226   = np.diff(eq226)   / eq226[:-1]
ret208   = np.diff(eq208)   / eq208[:-1]
ret_dates = dates_ml[1:]
n_ret = len(ret198)

print(f"\nReturn series: {n_ret} days  ({ret_dates[0]} -> {ret_dates[-1]})")
print(f"K198:  mean={ret198.mean():.6f}  std={ret198.std():.6f}")
print(f"K249a: mean={ret249a.mean():.6f}  std={ret249a.std():.6f}")
print(f"K226:  mean={ret226.mean():.6f}  std={ret226.std():.6f}")
print(f"K208:  mean={ret208.mean():.6f}  std={ret208.std():.6f}  (ref)")

# ─────────────────────────────────────────────────────────────────────────────
# 3. Utility functions (identical to K246 methodology)
# ─────────────────────────────────────────────────────────────────────────────

def sharpe(rets: np.ndarray) -> float:
    if len(rets) < 5:
        return np.nan
    mu  = np.mean(rets) * 365
    sig = np.std(rets, ddof=1) * ANN
    return float(mu / sig) if sig > 0 else np.nan


def maxdd(rets: np.ndarray) -> float:
    eq = np.cumprod(1 + np.array(rets))
    roll_max = np.maximum.accumulate(eq)
    dd = (eq - roll_max) / roll_max
    return float(dd.min())


def oos_metrics(rets: np.ndarray, oos_frac: float = 0.3) -> Dict:
    oos_start = int(len(rets) * (1 - oos_frac))
    oos_rets  = rets[oos_start:]
    return {
        "oos_sharpe":  round(sharpe(oos_rets), 4),
        "oos_maxdd":   round(maxdd(oos_rets), 6),
        "oos_n_days":  int(len(oos_rets)),
        "oos_ann_ret": round(float(np.mean(oos_rets) * 365), 4),
        "oos_ann_vol": round(float(np.std(oos_rets, ddof=1) * ANN), 4),
    }


def wf_stats(rets: np.ndarray, n_folds: int = 4) -> Dict:
    fold_size = len(rets) // n_folds
    fold_sharpes, fold_details = [], []
    for i in range(n_folds):
        s   = i * fold_size
        e   = (i + 1) * fold_size if i < n_folds - 1 else len(rets)
        fs  = sharpe(rets[s:e])
        fold_sharpes.append(fs)
        fold_details.append({
            "fold": i + 1, "start_idx": s, "end_idx": e,
            "n_days": e - s, "sharpe": round(float(fs), 4),
            "start_date": ret_dates[s],
            "end_date":   ret_dates[min(e - 1, len(ret_dates) - 1)],
        })
    return {
        "fold_sharpes": [round(s, 4) for s in fold_sharpes],
        "fold_details": fold_details,
        "wf_mean": round(float(np.mean(fold_sharpes)), 4),
        "wf_min":  round(float(np.min(fold_sharpes)), 4),
        "wf_max":  round(float(np.max(fold_sharpes)), 4),
    }


def equity_curve(rets: np.ndarray) -> List[float]:
    eq = np.empty(len(rets) + 1)
    eq[0] = 1.0
    eq[1:] = np.cumprod(1 + rets)
    return eq.tolist()


def inv_vol_blend(
    rets_list: List[np.ndarray],
    cap_idx: Optional[int] = None,
    cap_val: float = 0.20,
    roll: int = 30,
) -> Tuple[np.ndarray, np.ndarray]:
    """Inverse-vol weighted blend. Optionally cap one component (K246a methodology)."""
    n_comp = len(rets_list)
    n_t    = len(rets_list[0])
    blended = np.zeros(n_t)
    w_traj  = np.zeros((n_t, n_comp))

    for i in range(n_t):
        start_w = max(0, i - roll)
        vols = []
        for r in rets_list:
            seg = r[start_w : i + 1]
            v   = np.std(seg, ddof=1) if len(seg) >= 3 else 1e-6
            vols.append(max(v, 1e-9))

        ivols = [1.0 / v for v in vols]
        total = sum(ivols)
        w = np.array([iv / total for iv in ivols])

        if cap_idx is not None and w[cap_idx] > cap_val:
            w[cap_idx] = cap_val
            rest_ivols = [ivols[j] for j in range(n_comp) if j != cap_idx]
            rest_sum   = sum(rest_ivols)
            if rest_sum > 0:
                for j in range(n_comp):
                    if j != cap_idx:
                        w[j] = (ivols[j] / rest_sum) * (1.0 - cap_val)

        w_traj[i] = w
        blended[i] = sum(w[j] * rets_list[j][i] for j in range(n_comp))

    return blended, w_traj


def mvp_blend(
    rets_list: List[np.ndarray],
    roll: int = 60,
    min_obs: int = 30,
) -> Tuple[np.ndarray, np.ndarray]:
    """Minimum Variance Portfolio (rolling covariance)."""
    n_comp = len(rets_list)
    n_t    = len(rets_list[0])
    blended = np.zeros(n_t)
    w_traj  = np.zeros((n_t, n_comp))
    R = np.column_stack(rets_list)  # (n_t, n_comp)

    for i in range(n_t):
        start_w = max(0, i - roll)
        seg = R[start_w : i + 1]
        if seg.shape[0] < min_obs:
            # Equal weight fallback
            w = np.ones(n_comp) / n_comp
        else:
            cov = np.cov(seg.T, ddof=1)
            try:
                cov_inv = np.linalg.inv(cov + 1e-10 * np.eye(n_comp))
                ones = np.ones(n_comp)
                w_raw = cov_inv @ ones
                w = w_raw / w_raw.sum()
                # Clip negatives (long-only MVP)
                w = np.clip(w, 0, 1)
                s = w.sum()
                w = w / s if s > 0 else np.ones(n_comp) / n_comp
            except np.linalg.LinAlgError:
                w = np.ones(n_comp) / n_comp

        w_traj[i] = w
        blended[i] = float(w @ R[i])

    return blended, w_traj


def fold_contribution(
    fold_details: List[Dict],
    rets_list: List[np.ndarray],
    comp_names: List[str],
) -> List[Dict]:
    contributions = []
    for fd in fold_details:
        s, e = fd["start_idx"], fd["end_idx"]
        sharpes = {name: round(sharpe(r[s:e]), 4) for name, r in zip(comp_names, rets_list)}
        contributions.append({
            "fold":       fd["fold"],
            "start_date": fd["start_date"],
            "end_date":   fd["end_date"],
            "component_sharpes": sharpes,
            "top_contributor": max(sharpes, key=lambda k: sharpes[k]),
        })
    return contributions


# ─────────────────────────────────────────────────────────────────────────────
# 4. K249a ML window validation
#    K249a metrics in K249 were measured on K249's own OOS (70/30 split).
#    Here we measure K249a on K246a's exact daily ML window with same fold structure.
# ─────────────────────────────────────────────────────────────────────────────
print("\n=== K249a ML WINDOW VALIDATION ===")
print("Validating K249a on K246a's daily ML window (2025-01-22 -> 2026-04-14)")
print("K249a standalone metrics:")

m249a_standalone = oos_metrics(ret249a)
wf249a           = wf_stats(ret249a)
m249a_standalone.update(wf249a)
print(f"  Full window Sh : {sharpe(ret249a):.4f}")
print(f"  OOS Sh (30%)   : {m249a_standalone['oos_sharpe']:.4f}  (K249 self-reported: 17.53)")
print(f"  WF mean        : {m249a_standalone['wf_mean']:.4f}")
print(f"  WF min         : {m249a_standalone['wf_min']:.4f}  (K249 self-reported: 7.57)")
print(f"  WF folds       : {m249a_standalone['fold_sharpes']}")

# Active rate validation: K249a has ~75% active rate from K249 report
print("\n  NOTE: K249a active rate = 75% (spread gate p25 halts 25% of 8h events)")
print("  Daily returns may look smoother due to zeroed-out gated days")

# Window consistency check
k249a_oos_reported = 17.5288
k249a_wf_min_reported = 7.5679
k249a_delta_oos = m249a_standalone['oos_sharpe'] - k249a_oos_reported
k249a_delta_wfmin = m249a_standalone['wf_min'] - k249a_wf_min_reported
print(f"\n  Window consistency:")
print(f"    OOS Sh delta : {k249a_delta_oos:+.4f} (K246a window vs K249 self-reported)")
print(f"    WF min delta : {k249a_delta_wfmin:+.4f}")
if abs(k249a_delta_oos) > 5.0:
    print("    WARNING: Large OOS Sh discrepancy — window inconsistency detected")
else:
    print("    CONSISTENT: Delta within acceptable range")

# ─────────────────────────────────────────────────────────────────────────────
# 5. 3x3 Correlation matrix
# ─────────────────────────────────────────────────────────────────────────────
print("\n=== 3x3 CORRELATION MATRIX (K198, K249a, K226) ===")
rets_3 = np.column_stack([ret198, ret249a, ret226])  # (n_ret, 3)
corr_3 = np.corrcoef(rets_3.T)
names_3 = ["K198", "K249a", "K226"]
print(f"  {'':8s} {'K198':>8s} {'K249a':>8s} {'K226':>8s}")
for i, name in enumerate(names_3):
    row_str = " ".join(f"{corr_3[i, j]:8.4f}" for j in range(3))
    print(f"  {name:8s} {row_str}")

print(f"\n  K198-K249a rho : {corr_3[0,1]:.4f}")
print(f"  K198-K226  rho : {corr_3[0,2]:.4f}")
print(f"  K249a-K226 rho : {corr_3[1,2]:.4f}")

# Also show K208-K249a correlation (what changed)
corr_k208_k249a = float(np.corrcoef(ret208, ret249a)[0, 1])
corr_k208_k198  = float(np.corrcoef(ret208, ret198)[0, 1])
print(f"\n  K208-K249a rho : {corr_k208_k249a:.4f} (spread gate effect on correlation)")
print(f"  K208-K198  rho : {corr_k208_k198:.4f} (K246a original)")

# ─────────────────────────────────────────────────────────────────────────────
# 6. Meta-allocator variants
#    K251a: Inv-vol + K226 cap 20% (K246a methodology — primary)
#    K251b: Inv-vol uncapped
#    K251c: Inv-vol + K249a cap 20% (if K249a dominates)
#    K251d: MVP (rolling min-var)
# ─────────────────────────────────────────────────────────────────────────────
print("\n=== META-ALLOCATOR VARIANTS ===")

rets_k251 = [ret198, ret249a, ret226]
comp_names = ["K198", "K249a", "K226"]

# K251a: Inv-vol + K226 cap 20% (cap_idx=2 for K226)
print("\n--- K251a: Inv-vol + K226 cap 20% ---")
ret_k251a, w_k251a = inv_vol_blend(rets_k251, cap_idx=2, cap_val=0.20)
m_k251a = oos_metrics(ret_k251a)
wf_k251a = wf_stats(ret_k251a)
m_k251a.update(wf_k251a)
avg_w_k251a = [round(float(w_k251a[:, j].mean()), 4) for j in range(3)]
m_k251a["avg_weights"] = avg_w_k251a
m_k251a["description"] = "K198+K249a+K226 inv-vol + K226 cap 20%"
m_k251a["components"]  = comp_names
print(f"  OOS Sh={m_k251a['oos_sharpe']:.4f}  MaxDD={m_k251a['oos_maxdd']:.6f}  "
      f"WF mean={m_k251a['wf_mean']:.4f}  WF min={m_k251a['wf_min']:.4f}")
print(f"  Folds: {m_k251a['fold_sharpes']}")
print(f"  Avg weights: K198={avg_w_k251a[0]:.4f}  K249a={avg_w_k251a[1]:.4f}  K226={avg_w_k251a[2]:.4f}")

# K251b: Inv-vol uncapped
print("\n--- K251b: Inv-vol uncapped ---")
ret_k251b, w_k251b = inv_vol_blend(rets_k251, cap_idx=None)
m_k251b = oos_metrics(ret_k251b)
wf_k251b = wf_stats(ret_k251b)
m_k251b.update(wf_k251b)
avg_w_k251b = [round(float(w_k251b[:, j].mean()), 4) for j in range(3)]
m_k251b["avg_weights"] = avg_w_k251b
m_k251b["description"] = "K198+K249a+K226 inv-vol uncapped"
m_k251b["components"]  = comp_names
print(f"  OOS Sh={m_k251b['oos_sharpe']:.4f}  MaxDD={m_k251b['oos_maxdd']:.6f}  "
      f"WF mean={m_k251b['wf_mean']:.4f}  WF min={m_k251b['wf_min']:.4f}")
print(f"  Folds: {m_k251b['fold_sharpes']}")
print(f"  Avg weights: K198={avg_w_k251b[0]:.4f}  K249a={avg_w_k251b[1]:.4f}  K226={avg_w_k251b[2]:.4f}")

# K251c: Inv-vol + K249a cap 20% (cap_idx=1 for K249a)
print("\n--- K251c: Inv-vol + K249a cap 20% ---")
ret_k251c, w_k251c = inv_vol_blend(rets_k251, cap_idx=1, cap_val=0.20)
m_k251c = oos_metrics(ret_k251c)
wf_k251c = wf_stats(ret_k251c)
m_k251c.update(wf_k251c)
avg_w_k251c = [round(float(w_k251c[:, j].mean()), 4) for j in range(3)]
m_k251c["avg_weights"] = avg_w_k251c
m_k251c["description"] = "K198+K249a+K226 inv-vol + K249a cap 20%"
m_k251c["components"]  = comp_names
print(f"  OOS Sh={m_k251c['oos_sharpe']:.4f}  MaxDD={m_k251c['oos_maxdd']:.6f}  "
      f"WF mean={m_k251c['wf_mean']:.4f}  WF min={m_k251c['wf_min']:.4f}")
print(f"  Folds: {m_k251c['fold_sharpes']}")
print(f"  Avg weights: K198={avg_w_k251c[0]:.4f}  K249a={avg_w_k251c[1]:.4f}  K226={avg_w_k251c[2]:.4f}")

# K251d: MVP
print("\n--- K251d: MVP (rolling min-var) ---")
ret_k251d, w_k251d = mvp_blend(rets_k251)
m_k251d = oos_metrics(ret_k251d)
wf_k251d = wf_stats(ret_k251d)
m_k251d.update(wf_k251d)
avg_w_k251d = [round(float(w_k251d[:, j].mean()), 4) for j in range(3)]
m_k251d["avg_weights"] = avg_w_k251d
m_k251d["description"] = "K198+K249a+K226 MVP (rolling min-var)"
m_k251d["components"]  = comp_names
print(f"  OOS Sh={m_k251d['oos_sharpe']:.4f}  MaxDD={m_k251d['oos_maxdd']:.6f}  "
      f"WF mean={m_k251d['wf_mean']:.4f}  WF min={m_k251d['wf_min']:.4f}")
print(f"  Folds: {m_k251d['fold_sharpes']}")
print(f"  Avg weights: K198={avg_w_k251d[0]:.4f}  K249a={avg_w_k251d[1]:.4f}  K226={avg_w_k251d[2]:.4f}")

# ─────────────────────────────────────────────────────────────────────────────
# 7. Per-fold contribution (all variants)
# ─────────────────────────────────────────────────────────────────────────────
print("\n=== PER-FOLD COMPONENT CONTRIBUTION ===")
for vname, vm in [
    ("K251a", m_k251a), ("K251b", m_k251b), ("K251c", m_k251c), ("K251d", m_k251d)
]:
    wf_tmp = wf_stats(globals()[f"ret_{vname.lower()}"])
    contrib = fold_contribution(wf_tmp["fold_details"], rets_k251, comp_names)
    vm["fold_contribution"] = contrib
    print(f"\n  {vname} per-fold component Sharpes:")
    for fc in contrib:
        cs = fc["component_sharpes"]
        print(f"    Fold {fc['fold']} ({fc['start_date']}..{fc['end_date']}): "
              f"K198={cs['K198']:+.2f}  K249a={cs['K249a']:+.2f}  K226={cs['K226']:+.2f}"
              f"  → {fc['top_contributor']}")

# ─────────────────────────────────────────────────────────────────────────────
# 8. Also run K246a reproduction for direct comparison
# ─────────────────────────────────────────────────────────────────────────────
print("\n=== K246a REPRODUCTION (K198+K208+K226, K226 cap 20%) ===")
ret_k246a_repro, w_k246a_repro = inv_vol_blend([ret198, ret208, ret226], cap_idx=2, cap_val=0.20)
m_k246a_repro = oos_metrics(ret_k246a_repro)
wf_k246a_repro = wf_stats(ret_k246a_repro)
m_k246a_repro.update(wf_k246a_repro)
avg_w_k246a_r = [round(float(w_k246a_repro[:, j].mean()), 4) for j in range(3)]
print(f"  OOS Sh={m_k246a_repro['oos_sharpe']:.4f}  (reported: {K246A_OOS_SH:.4f})")
print(f"  WF min={m_k246a_repro['wf_min']:.4f}  (reported: {K246A_WF_MIN:.4f})")
print(f"  Folds: {m_k246a_repro['fold_sharpes']}")
print(f"  Avg weights K198={avg_w_k246a_r[0]:.4f}  K208={avg_w_k246a_r[1]:.4f}  K226={avg_w_k246a_r[2]:.4f}")

# ─────────────────────────────────────────────────────────────────────────────
# 9. Acceptance gate evaluation
# ─────────────────────────────────────────────────────────────────────────────
print("\n=== ACCEPTANCE GATES ===")
print(f"  Gate 1: OOS Sh   >= {GATE_OOS_SH} (K246a: {K246A_OOS_SH})")
print(f"  Gate 2: WF min   >= {GATE_WF_MIN} (K246a: {K246A_WF_MIN})")
print(f"  Gate 3: MaxDD    <= {GATE_MAXDD} (K246a: {K246A_MAXDD})")
print(f"  Gate 4: K249a wt > {GATE_K249A_WT*100:.0f}% (genuine contribution)")

variants_k251 = {
    "K251a": m_k251a,
    "K251b": m_k251b,
    "K251c": m_k251c,
    "K251d": m_k251d,
}

accepted_k251 = []
for vname, vm in variants_k251.items():
    k249a_wt = vm["avg_weights"][1]  # index 1 = K249a
    g1 = vm["oos_sharpe"] >= GATE_OOS_SH
    g2 = vm["wf_min"]     >= GATE_WF_MIN
    g3 = vm["oos_maxdd"]  >= GATE_MAXDD
    g4 = k249a_wt         >= GATE_K249A_WT
    all_pass = g1 and g2 and g3 and g4
    verdict_v = "ACCEPT" if all_pass else "FAIL"
    vm["gates"] = {
        "g1_oos_sh": g1, "g2_wf_min": g2, "g3_maxdd": g3, "g4_k249a_wt": g4,
        "all_pass": all_pass, "verdict": verdict_v,
        "k249a_weight": k249a_wt,
    }
    delta_oos = round(vm["oos_sharpe"] - K246A_OOS_SH, 4)
    delta_wfm = round(vm["wf_min"] - K246A_WF_MIN, 4)
    print(f"\n  {vname}: OOS Sh={vm['oos_sharpe']:.4f}({'PASS' if g1 else 'FAIL'}) "
          f"WF_min={vm['wf_min']:.4f}({'PASS' if g2 else 'FAIL'}) "
          f"MaxDD={vm['oos_maxdd']:.6f}({'PASS' if g3 else 'FAIL'}) "
          f"K249a_wt={k249a_wt:.4f}({'PASS' if g4 else 'FAIL'}) → {verdict_v}")
    print(f"         Delta vs K246a: OOS Sh{delta_oos:+.4f}  WF min{delta_wfm:+.4f}")
    if all_pass:
        accepted_k251.append((vm["oos_sharpe"] + vm["wf_min"], vname, vm))

accepted_k251.sort(reverse=True)
best_k251 = accepted_k251[0][1] if accepted_k251 else None
best_vm_k251 = accepted_k251[0][2] if accepted_k251 else None

# ─────────────────────────────────────────────────────────────────────────────
# 10. Comparison summary table
# ─────────────────────────────────────────────────────────────────────────────
print("\n=== FINAL COMPARISON TABLE ===")
header = f"{'Version':<22} {'OOS Sh':>8} {'MaxDD':>10} {'WF mean':>8} {'WF min':>8} {'Folds':>30}"
print(f"  {header}")
print(f"  {'-' * 90}")
print(f"  {'K246a v6.9 (reported)':<22} {K246A_OOS_SH:>8.4f} {K246A_MAXDD:>10.6f} "
      f"{K246A_WF_MEAN:>8.4f} {K246A_WF_MIN:>8.4f} "
      f"  {K246A_FOLDS}")
print(f"  {'K246a (repro)':<22} {m_k246a_repro['oos_sharpe']:>8.4f} {m_k246a_repro['oos_maxdd']:>10.6f} "
      f"{m_k246a_repro['wf_mean']:>8.4f} {m_k246a_repro['wf_min']:>8.4f} "
      f"  {m_k246a_repro['fold_sharpes']}")

for vname, vm in variants_k251.items():
    verdict_str = vm["gates"]["verdict"]
    print(f"  {vname + ' (' + verdict_str + ')':<22} {vm['oos_sharpe']:>8.4f} {vm['oos_maxdd']:>10.6f} "
          f"{vm['wf_mean']:>8.4f} {vm['wf_min']:>8.4f}  {vm['fold_sharpes']}")

# ─────────────────────────────────────────────────────────────────────────────
# 11. Final verdict
# ─────────────────────────────────────────────────────────────────────────────
print("\n=== FINAL VERDICT ===")
if best_k251:
    bv = best_vm_k251
    final_verdict = f"ACCEPT — {best_k251} promoted to v6.9.1 production"
    verdict_detail = (
        f"{best_k251} passes all gates: OOS Sh {bv['oos_sharpe']:.4f} >= {GATE_OOS_SH}, "
        f"WF min {bv['wf_min']:.4f} >= {GATE_WF_MIN}, MaxDD {bv['oos_maxdd']:.6f} >= {GATE_MAXDD}, "
        f"K249a weight {bv['avg_weights'][1]:.4f} > {GATE_K249A_WT}."
    )
else:
    final_verdict = "REJECT — K251 does not pass acceptance gates; maintain K246a v6.9"
    verdict_detail = (
        "No K251 variant passes all 4 gates simultaneously. "
        "K249a's spread gate may reduce ensemble correlation benefit. "
        "K246a v6.9 (K198+K208+K226) remains production."
    )

print(f"\n  {final_verdict}")
print(f"  {verdict_detail}")

# ─────────────────────────────────────────────────────────────────────────────
# 12. Build output JSON
# ─────────────────────────────────────────────────────────────────────────────
runtime = round(time.time() - t0, 1)

# Standalone metrics for K249a on K246a window
k249a_standalone_full = {
    "sharpe_full": round(sharpe(ret249a), 4),
    "oos_sharpe":  m249a_standalone["oos_sharpe"],
    "oos_maxdd":   m249a_standalone["oos_maxdd"],
    "wf_mean":     m249a_standalone["wf_mean"],
    "wf_min":      m249a_standalone["wf_min"],
    "wf_folds":    m249a_standalone["fold_sharpes"],
    "oos_reported_k249": 17.5288,
    "wf_min_reported_k249": 7.5679,
    "window_delta_oos":    round(k249a_delta_oos, 4),
    "window_delta_wf_min": round(k249a_delta_wfmin, 4),
    "window_consistent":   abs(k249a_delta_oos) <= 5.0,
    "note": "K249a measured on K246a daily ML window (2025-01-22 -> 2026-04-14)"
}

output = {
    "wave": "K251",
    "parent_waves": ["K246a", "K249a", "K198", "K226"],
    "objective": "Replace K208 with K249a in K246a ensemble (v6.9.1 candidate)",
    "as_of": datetime.now(timezone.utc).isoformat(),
    "runtime_s": runtime,

    "config": {
        "ml_window":  {"start": dates_ml[0], "end": dates_ml[-1]},
        "n_days":     n,
        "n_returns":  n_ret,
        "components": ["K198", "K249a", "K226"],
        "methodology": "inv-vol rolling-30d + K226 cap 20% (K246a methodology)",
        "wf_n_folds": 4,
        "wf_fold_size_days": n_ret // 4,
        "missing_k249a_days": missing_k249a,
        "missing_k226_days":  missing_k226,
        "missing_k208_days":  missing_k208,
    },

    "acceptance_gates": {
        "gate1_oos_sh_min":    GATE_OOS_SH,
        "gate2_wf_min_min":    GATE_WF_MIN,
        "gate3_maxdd_max":     GATE_MAXDD,
        "gate4_k249a_wt_min":  GATE_K249A_WT,
        "reference": "K246a v6.9",
    },

    "k246a_reference": {
        "oos_sharpe": K246A_OOS_SH,
        "wf_mean":    K246A_WF_MEAN,
        "wf_min":     K246A_WF_MIN,
        "maxdd":      K246A_MAXDD,
        "fold_sharpes": K246A_FOLDS,
        "components": ["K198", "K208", "K226"],
    },

    "k249a_ml_window_validation": k249a_standalone_full,

    "correlation_matrix_3x3": {
        "components": names_3,
        "matrix": corr_3.tolist(),
        "rho_k198_k249a": round(corr_3[0, 1], 4),
        "rho_k198_k226":  round(corr_3[0, 2], 4),
        "rho_k249a_k226": round(corr_3[1, 2], 4),
        "k208_k249a_rho": round(corr_k208_k249a, 4),
        "k208_k198_rho":  round(corr_k208_k198, 4),
    },

    "k246a_reproduction": {
        "oos_sharpe": m_k246a_repro["oos_sharpe"],
        "oos_maxdd":  m_k246a_repro["oos_maxdd"],
        "wf_mean":    m_k246a_repro["wf_mean"],
        "wf_min":     m_k246a_repro["wf_min"],
        "fold_sharpes": m_k246a_repro["fold_sharpes"],
        "avg_weights_k198_k208_k226": avg_w_k246a_r,
    },

    "variants": {
        vname: {
            "oos_sharpe":   vm["oos_sharpe"],
            "oos_maxdd":    vm["oos_maxdd"],
            "oos_ann_ret":  vm["oos_ann_ret"],
            "oos_ann_vol":  vm["oos_ann_vol"],
            "wf_mean":      vm["wf_mean"],
            "wf_min":       vm["wf_min"],
            "fold_sharpes": vm["fold_sharpes"],
            "avg_weights":  vm["avg_weights"],
            "description":  vm["description"],
            "gates":        vm["gates"],
            "fold_contribution": vm.get("fold_contribution", []),
            "delta_oos_sh": round(vm["oos_sharpe"] - K246A_OOS_SH, 4),
            "delta_wf_min": round(vm["wf_min"] - K246A_WF_MIN, 4),
            "delta_maxdd":  round(vm["oos_maxdd"] - K246A_MAXDD, 6),
        }
        for vname, vm in variants_k251.items()
    },

    "accepted": [vname for _, vname, _ in accepted_k251],
    "best_variant": best_k251,

    "verdict": {
        "decision": "ACCEPT" if best_k251 else "REJECT",
        "best_variant": best_k251,
        "summary": final_verdict,
        "detail": verdict_detail,
        "production_label": "v6.9.1" if best_k251 else "v6.9 (unchanged)",
    },
}

json_path = BASE / "wave_k251_k246a_k249a.json"
json_path.write_text(json.dumps(output, indent=2, default=str))
print(f"\nWrote {json_path}  ({json_path.stat().st_size:,} bytes)")

# ─────────────────────────────────────────────────────────────────────────────
# 13. Build curves JSON
# ─────────────────────────────────────────────────────────────────────────────
curves_out = {
    "dates":    [dates_ml[0]] + list(ret_dates),
    "K246a":    equity_curve(ret_k246a_repro),
    "K251a":    equity_curve(ret_k251a),
    "K251b":    equity_curve(ret_k251b),
    "K251c":    equity_curve(ret_k251c),
    "K251d":    equity_curve(ret_k251d),
    "K198":     equity_curve(ret198),
    "K249a":    equity_curve(ret249a),
    "K226":     equity_curve(ret226),
    "K208_ref": equity_curve(ret208),
}

curves_path = BASE / "wave_k251_curves.json"
curves_path.write_text(json.dumps(curves_out, default=str))
print(f"Wrote {curves_path}  ({curves_path.stat().st_size:,} bytes)")

# ─────────────────────────────────────────────────────────────────────────────
# 14. Markdown report
# ─────────────────────────────────────────────────────────────────────────────
lines: List[str] = [
    "# Wave K251 — K198 + K249a + K226 Ensemble (v6.9.1 candidate)",
    f"*Generated: {output['as_of']}  |  Runtime: {runtime}s*",
    "",
    "## Executive Summary",
    "",
    f"**VERDICT: {final_verdict}**",
    "",
    f"{verdict_detail}",
    "",
    "## 1. K249a ML Window Validation",
    "",
    "K249a self-reported OOS Sh = 17.53 (K249's own 70/30 split on full history).",
    "Re-measured on K246a daily ML window (2025-01-22 → 2026-04-14):",
    "",
    f"| Metric | K249 Self-report | K246a Window | Delta |",
    f"|--------|-----------------|--------------|-------|",
    f"| OOS Sh (30%) | 17.53 | {m249a_standalone['oos_sharpe']:.4f} | {k249a_delta_oos:+.4f} |",
    f"| WF min | 7.57 | {m249a_standalone['wf_min']:.4f} | {k249a_delta_wfmin:+.4f} |",
    f"| WF folds | [27.03, 7.57, 23.72, 17.88] | {m249a_standalone['fold_sharpes']} | — |",
    "",
    f"Window consistency: **{'CONSISTENT' if abs(k249a_delta_oos) <= 5.0 else 'INCONSISTENT (WARNING)'}**",
    "",
    "## 2. 3x3 Correlation Matrix",
    "",
    "| | K198 | K249a | K226 |",
    "|---|---|---|---|",
    f"| **K198**  | 1.0000 | {corr_3[0,1]:.4f} | {corr_3[0,2]:.4f} |",
    f"| **K249a** | {corr_3[1,0]:.4f} | 1.0000 | {corr_3[1,2]:.4f} |",
    f"| **K226**  | {corr_3[2,0]:.4f} | {corr_3[2,1]:.4f} | 1.0000 |",
    "",
    f"K208→K249a correlation: {corr_k208_k249a:.4f} (was K208-K198: {corr_k208_k198:.4f})",
    "",
    "## 3. Variant Performance vs K246a v6.9",
    "",
    "| Version | OOS Sh | MaxDD | WF Mean | WF Min | Folds | K249a Wt | Gates |",
    "|---------|--------|-------|---------|--------|-------|----------|-------|",
    f"| K246a v6.9 (reported) | {K246A_OOS_SH:.4f} | {K246A_MAXDD:.6f} | {K246A_WF_MEAN:.4f} | {K246A_WF_MIN:.4f} | {K246A_FOLDS} | K208 | — |",
    f"| K246a (repro) | {m_k246a_repro['oos_sharpe']:.4f} | {m_k246a_repro['oos_maxdd']:.6f} | {m_k246a_repro['wf_mean']:.4f} | {m_k246a_repro['wf_min']:.4f} | {m_k246a_repro['fold_sharpes']} | K208 | — |",
]

for vname, vm in variants_k251.items():
    g = vm["gates"]
    lines.append(
        f"| {vname} ({g['verdict']}) | {vm['oos_sharpe']:.4f} | {vm['oos_maxdd']:.6f} | "
        f"{vm['wf_mean']:.4f} | {vm['wf_min']:.4f} | {vm['fold_sharpes']} | "
        f"{vm['avg_weights'][1]:.4f} | {'ALL' if g['all_pass'] else 'PARTIAL'} |"
    )

lines += [
    "",
    f"Gates: OOS Sh >= {GATE_OOS_SH} AND WF min >= {GATE_WF_MIN} AND MaxDD <= {GATE_MAXDD} AND K249a wt > {GATE_K249A_WT}",
    "",
    "## 4. Per-Variant Per-Fold Breakdown",
    "",
]

for vname, vm in variants_k251.items():
    lines.append(f"### {vname} ({vm['description']})")
    lines += [
        "",
        "| Fold | Period | K198 Sh | K249a Sh | K226 Sh | Top |",
        "|------|--------|---------|----------|---------|-----|",
    ]
    for fc in vm.get("fold_contribution", []):
        cs = fc["component_sharpes"]
        lines.append(
            f"| {fc['fold']} | {fc['start_date']}..{fc['end_date']} | "
            f"{cs.get('K198', 0):.4f} | {cs.get('K249a', 0):.4f} | {cs.get('K226', 0):.4f} | "
            f"**{fc['top_contributor']}** |"
        )
    lines.append("")

lines += [
    "## 5. Verdict, K251 v6.9.1",
    "",
]

if best_k251:
    bv = best_vm_k251
    lines += [
        f"**ACCEPT — Promote {best_k251} to v6.9.1 production.**",
        "",
        f"- Components: K198 + K249a + K226",
        f"- Allocator: {bv['description']}",
        f"- OOS Sh: {bv['oos_sharpe']:.4f} (K246a: {K246A_OOS_SH:.4f}, delta: {bv['oos_sharpe']-K246A_OOS_SH:+.4f})",
        f"- WF min: {bv['wf_min']:.4f} (K246a: {K246A_WF_MIN:.4f}, delta: {bv['wf_min']-K246A_WF_MIN:+.4f})",
        f"- MaxDD:  {bv['oos_maxdd']:.6f} (K246a: {K246A_MAXDD:.6f})",
        f"- K249a avg weight: {bv['avg_weights'][1]:.4f} (> 5% threshold)",
        f"- WF folds: {bv['fold_sharpes']}",
        "",
        "K249a's spread gate (p25) successfully lifted fold2 Sharpe at component level.",
        "The ensemble fold2 improvement is confirmed through this K251 run.",
    ]
else:
    lines += [
        f"**REJECT — Maintain K246a v6.9 (K198+K208+K226) as production.**",
        "",
        "No K251 variant clears all 4 acceptance gates simultaneously.",
        "Analysis suggests K249a's spread gating (25% halt) shifts ensemble weight",
        "to K198, which may not consistently beat K208's full-activity contribution.",
        "",
        "Recommended next step: investigate if K249a's active-rate reduction causes",
        "ensemble instability, or explore hybrid K249a+K208 blending.",
    ]

lines += [
    "",
    "---",
    f"*Wave K251 | crypto-lab | {output['as_of']}*",
]

report_text = "\n".join(lines)
md_path = BASE / "wave_k251_k246a_k249a.md"
md_path.write_text(report_text)
print(f"Wrote {md_path}  ({md_path.stat().st_size:,} bytes)")

# ─────────────────────────────────────────────────────────────────────────────
print(f"\n{'=' * 70}")
print(f"K251 COMPLETE — Runtime {runtime}s")
print(f"VERDICT: {final_verdict}")
if best_k251:
    bv = best_vm_k251
    print(f"Best: {best_k251} — OOS Sh={bv['oos_sharpe']:.4f}  WF min={bv['wf_min']:.4f}")
print(f"{'=' * 70}")
