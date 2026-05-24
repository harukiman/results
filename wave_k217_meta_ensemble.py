"""
Wave K217 — Meta-Ensemble: K198 × K204 Portfolio Combination
Goal: Harvest K198 fold-4 alpha AND K204 WF-min stability simultaneously.

Variants:
  K217a — Fixed 50/50 blend
  K217b — Inverse-volatility weighted (rolling 30d vol)
  K217c — Rolling 90d Sharpe-weighted
  K217d — Recency-biased toward K198 (exponential decay weighting)

Acceptance gate (v6.6 production):
  OOS Sh  > 10.33  (+0.05 vs K198 10.28)
  WF min  > 6.57   (beats K198 WF min)
  MaxDD   ≤ -0.0053
"""

import json
import numpy as np
from datetime import datetime, timezone
import time

t0 = time.time()

# ─────────────────────────────────────────────
# 1. Load equity series
# ─────────────────────────────────────────────
with open("/Users/nekonaomichi/crypto-lab/wave_k198_curves.json") as f:
    k198_raw = json.load(f)
with open("/Users/nekonaomichi/crypto-lab/wave_k204_curves.json") as f:
    k204_raw = json.load(f)

dates   = k198_raw["dates_ml"]          # 448 days, 2025-01-22 → 2026-05-14
eq198   = np.array(k198_raw["equity_ridge"])
eq204   = np.array(k204_raw["equity_k204"])

assert len(dates) == len(eq198) == len(eq204), "Length mismatch"
n = len(dates)

# Daily returns  (geometric)
ret198 = np.diff(eq198) / eq198[:-1]
ret204 = np.diff(eq204) / eq204[:-1]
# align to same index domain (n-1 days after day 0)
ret_dates = dates[1:]   # n-1 return dates

# ─────────────────────────────────────────────
# 2. Correlation analysis
# ─────────────────────────────────────────────
rho = float(np.corrcoef(ret198, ret204)[0, 1])
print(f"K198 × K204 daily return correlation: ρ = {rho:.4f}")
if rho > 0.95:
    print("WARNING: ρ > 0.95 — high correlation, diversification gain is limited.")

# ─────────────────────────────────────────────
# 3. Utility functions
# ─────────────────────────────────────────────
ANN = np.sqrt(365)

def sharpe(rets):
    """Annualised Sharpe (daily rets)."""
    if len(rets) < 5:
        return np.nan
    mu  = np.mean(rets) * 365
    sig = np.std(rets, ddof=1) * ANN
    return float(mu / sig) if sig > 0 else np.nan

def maxdd(rets):
    """Maximum drawdown (negative number)."""
    eq = np.cumprod(1 + np.array(rets))
    roll_max = np.maximum.accumulate(eq)
    dd = (eq - roll_max) / roll_max
    return float(dd.min())

def wf_stats(rets, n_folds=4):
    """Walk-forward 4-fold: chronological splits on the return series."""
    fold_size = len(rets) // n_folds
    fold_sharpes = []
    for i in range(n_folds):
        start = i * fold_size
        end   = (i + 1) * fold_size if i < n_folds - 1 else len(rets)
        fold_sharpes.append(sharpe(rets[start:end]))
    return {
        "fold_sharpes": [round(s, 4) for s in fold_sharpes],
        "wf_mean":      round(float(np.mean(fold_sharpes)), 4),
        "wf_min":       round(float(np.min(fold_sharpes)), 4),
        "wf_max":       round(float(np.max(fold_sharpes)), 4),
        "wf_std":       round(float(np.std(fold_sharpes, ddof=1)), 4),
    }

def oos_metrics(rets, oos_frac=0.3):
    """OOS metrics on final oos_frac of the return series."""
    oos_start = int(len(rets) * (1 - oos_frac))
    oos_rets  = rets[oos_start:]
    return {
        "oos_sharpe": round(sharpe(oos_rets), 4),
        "oos_maxdd":  round(maxdd(oos_rets), 6),
        "oos_n_days": len(oos_rets),
        "oos_ann_ret": round(float(np.mean(oos_rets) * 365), 4),
        "oos_ann_vol": round(float(np.std(oos_rets, ddof=1) * ANN), 4),
    }

def equity_curve(rets):
    """Rebuild equity curve from returns."""
    eq = np.empty(len(rets) + 1)
    eq[0] = 1.0
    eq[1:] = np.cumprod(1 + rets)
    return eq.tolist()

# ─────────────────────────────────────────────
# 4. Baseline (K198 and K204 solo metrics on same return series)
# ─────────────────────────────────────────────
print("\n--- Baseline metrics on ML-window returns ---")
baseline = {}
for name, rets in [("K198", ret198), ("K204", ret204)]:
    m = oos_metrics(rets)
    w = wf_stats(rets)
    m.update(w)
    baseline[name] = m
    print(f"{name}: OOS Sh={m['oos_sharpe']:.4f}  MaxDD={m['oos_maxdd']:.4f}  "
          f"WF mean={m['wf_mean']:.4f}  WF min={m['wf_min']:.4f}")

# ─────────────────────────────────────────────
# 5. Meta-allocator variants
# ─────────────────────────────────────────────
variants = {}

# ── K217a: Fixed 50/50 ──────────────────────
print("\n--- K217a: Fixed 50/50 ---")
ret_a = 0.5 * ret198 + 0.5 * ret204
m = oos_metrics(ret_a)
w = wf_stats(ret_a)
m.update(w)
m["description"] = "Fixed 50/50 blend"
variants["K217a"] = m
print(f"K217a: OOS Sh={m['oos_sharpe']:.4f}  MaxDD={m['oos_maxdd']:.4f}  "
      f"WF mean={m['wf_mean']:.4f}  WF min={m['wf_min']:.4f}")

# ── K217b: Inverse-volatility weighted (rolling 30d) ──
print("\n--- K217b: Inverse-vol weighted (30d rolling) ---")
ROLL = 30
inv_vol_rets = np.zeros(len(ret198))
for i in range(len(ret198)):
    start_w = max(0, i - ROLL)
    vol198 = np.std(ret198[start_w:i+1], ddof=1) if i - start_w >= 2 else 1e-6
    vol204 = np.std(ret204[start_w:i+1], ddof=1) if i - start_w >= 2 else 1e-6
    iv198 = 1.0 / max(vol198, 1e-9)
    iv204 = 1.0 / max(vol204, 1e-9)
    total = iv198 + iv204
    w198 = iv198 / total
    w204 = iv204 / total
    inv_vol_rets[i] = w198 * ret198[i] + w204 * ret204[i]

m = oos_metrics(inv_vol_rets)
w = wf_stats(inv_vol_rets)
m.update(w)
m["description"] = "Inverse-vol weighted (30d rolling)"
variants["K217b"] = m
print(f"K217b: OOS Sh={m['oos_sharpe']:.4f}  MaxDD={m['oos_maxdd']:.4f}  "
      f"WF mean={m['wf_mean']:.4f}  WF min={m['wf_min']:.4f}")

# ── K217c: Rolling 90d Sharpe-weighted ──────
print("\n--- K217c: Rolling 90d Sharpe-weighted ---")
ROLL_SH = 90
sh_rets = np.zeros(len(ret198))
for i in range(len(ret198)):
    start_w = max(0, i - ROLL_SH)
    seg198 = ret198[start_w:i+1]
    seg204 = ret204[start_w:i+1]
    sh198 = sharpe(seg198) if len(seg198) >= 10 else 0.0
    sh204 = sharpe(seg204) if len(seg204) >= 10 else 0.0
    # Convert to non-negative weights (floor at 0)
    sh198c = max(sh198, 0.0)
    sh204c = max(sh204, 0.0)
    total = sh198c + sh204c
    if total < 1e-9:
        w198, w204 = 0.5, 0.5
    else:
        w198, w204 = sh198c / total, sh204c / total
    sh_rets[i] = w198 * ret198[i] + w204 * ret204[i]

m = oos_metrics(sh_rets)
w = wf_stats(sh_rets)
m.update(w)
m["description"] = "Rolling 90d Sharpe-weighted"
variants["K217c"] = m
print(f"K217c: OOS Sh={m['oos_sharpe']:.4f}  MaxDD={m['oos_maxdd']:.4f}  "
      f"WF mean={m['wf_mean']:.4f}  WF min={m['wf_min']:.4f}")

# ── K217d: Recency-biased toward K198 (fold-4 alpha) ─
print("\n--- K217d: Recency-biased K198 (exponential decay, 60d half-life) ---")
n_ret = len(ret198)
half_life = 60  # days
lam = np.log(2) / half_life
# Weight K198 more in recent period (later indices = more recent)
# Map each day index 0..n_ret-1 → days_from_end
days_from_end = np.arange(n_ret - 1, -1, -1)
decay = np.exp(-lam * days_from_end)   # recent = high weight
# Normalise to [0.5, 0.9] for K198
w198_d = 0.5 + 0.4 * (decay - decay.min()) / (decay.max() - decay.min())
w204_d = 1.0 - w198_d
rec_rets = w198_d * ret198 + w204_d * ret204

m = oos_metrics(rec_rets)
w = wf_stats(rec_rets)
m.update(w)
m["description"] = "Recency-biased toward K198 (60d half-life, K198 weight 0.50→0.90)"
m["k198_weight_range"] = [round(float(w198_d.min()), 3), round(float(w198_d.max()), 3)]
variants["K217d"] = m
print(f"K217d: OOS Sh={m['oos_sharpe']:.4f}  MaxDD={m['oos_maxdd']:.4f}  "
      f"WF mean={m['wf_mean']:.4f}  WF min={m['wf_min']:.4f}")

# ─────────────────────────────────────────────
# 6. Select best variant
# ─────────────────────────────────────────────
K198_OOS_SH = 10.28
K198_WF_MIN = 6.57
K198_MAXDD  = -0.0053
GATE_OOS_SH = K198_OOS_SH + 0.05   # 10.33
GATE_WF_MIN = K198_WF_MIN           # > 6.57
GATE_MAXDD  = K198_MAXDD            # ≤ -0.0053

print("\n--- Acceptance Gate ---")
print(f"Gates: OOS Sh > {GATE_OOS_SH:.2f}  |  WF min > {GATE_WF_MIN:.2f}  |  MaxDD ≤ {GATE_MAXDD:.4f}")

candidates = []
for vname, vm in variants.items():
    sh_pass  = vm["oos_sharpe"] > GATE_OOS_SH
    wf_pass  = vm["wf_min"] > GATE_WF_MIN
    dd_pass  = vm["oos_maxdd"] >= GATE_MAXDD
    all_pass = sh_pass and wf_pass and dd_pass
    score    = vm["oos_sharpe"] + vm["wf_min"]  # composite rank
    print(f"  {vname}: OOS={vm['oos_sharpe']:.4f}({'✓' if sh_pass else '✗'})  "
          f"WFmin={vm['wf_min']:.4f}({'✓' if wf_pass else '✗'})  "
          f"MaxDD={vm['oos_maxdd']:.4f}({'✓' if dd_pass else '✗'})  "
          f"→ {'PASS' if all_pass else 'FAIL'}")
    if all_pass:
        candidates.append((score, vname, vm))

candidates.sort(reverse=True)
best_name  = candidates[0][1] if candidates else None
best_vm    = candidates[0][2] if candidates else None
accepted   = best_name is not None

# ─────────────────────────────────────────────
# 7. Synergy check
# ─────────────────────────────────────────────
print("\n--- Synergy Check ---")
avg198 = oos_metrics(ret198)["oos_sharpe"]
avg204 = oos_metrics(ret204)["oos_sharpe"]
avg_individual = (avg198 + avg204) / 2.0
if best_vm:
    synergy_sh = best_vm["oos_sharpe"] - avg_individual
    synergy_detected = synergy_sh > 0.02
    print(f"Average of individuals: {avg_individual:.4f}  |  "
          f"Best ensemble: {best_vm['oos_sharpe']:.4f}  |  "
          f"Synergy Δ: {synergy_sh:+.4f}  ({'GENUINE' if synergy_detected else 'NO SYNERGY'})")
else:
    synergy_sh = 0.0
    synergy_detected = False
    print("No accepted candidate — no synergy measurement.")

# WF-min synergy
if best_vm:
    avg_wf_min = (baseline["K198"]["wf_min"] + baseline["K204"]["wf_min"]) / 2
    wf_synergy = best_vm["wf_min"] - avg_wf_min
    print(f"WF-min avg of individuals: {avg_wf_min:.4f}  |  "
          f"Best ensemble WF-min: {best_vm['wf_min']:.4f}  |  Δ: {wf_synergy:+.4f}")

# ─────────────────────────────────────────────
# 8. Build equity curves for output
# ─────────────────────────────────────────────
curves = {
    "K198":  equity_curve(ret198),
    "K204":  equity_curve(ret204),
    "K217a": equity_curve(0.5 * ret198 + 0.5 * ret204),
    "K217b": equity_curve(inv_vol_rets),
    "K217c": equity_curve(sh_rets),
    "K217d": equity_curve(rec_rets),
    "dates": [dates[0]] + list(ret_dates),  # n dates total
}

# ─────────────────────────────────────────────
# 9. Save JSON outputs
# ─────────────────────────────────────────────
runtime = round(time.time() - t0, 2)

verdict = (
    f"ACCEPT as K217 v6.6 — best variant: {best_name}"
    if accepted
    else "REJECT — no variant passes all acceptance gates"
)

result = {
    "wave": "K217",
    "task": "Meta-Ensemble: K198 × K204 portfolio combination",
    "as_of": datetime.now(timezone.utc).isoformat(),
    "runtime_s": runtime,
    "correlation": {
        "k198_k204_daily_rho": round(rho, 4),
        "high_correlation_flag": rho > 0.95,
        "interpretation": (
            "Low diversification potential — effectively K198 alone" if rho > 0.95
            else "Meaningful diversification possible"
        ),
    },
    "acceptance_gates": {
        "oos_sharpe_threshold": GATE_OOS_SH,
        "wf_min_threshold": GATE_WF_MIN,
        "maxdd_threshold": GATE_MAXDD,
    },
    "baselines": baseline,
    "variants": variants,
    "synergy": {
        "avg_individual_oos_sh": round(avg_individual, 4),
        "best_ensemble_oos_sh":  round(best_vm["oos_sharpe"], 4) if best_vm else None,
        "synergy_delta_oos_sh":  round(synergy_sh, 4),
        "synergy_detected":      synergy_detected,
        "avg_individual_wf_min": round((baseline["K198"]["wf_min"] + baseline["K204"]["wf_min"]) / 2, 4),
        "best_ensemble_wf_min":  round(best_vm["wf_min"], 4) if best_vm else None,
        "wf_min_delta":          round(wf_synergy, 4) if best_vm else None,
    },
    "verdict": verdict,
    "accepted": accepted,
    "best_variant": best_name,
    "best_variant_metrics": best_vm,
    "five_way_comparison": {
        "K198_v6.5":   {"oos_sharpe": 10.28, "oos_maxdd": -0.0053, "wf_mean": 7.91, "wf_min": 6.57},
        "K204_rejected":{"oos_sharpe": 10.36, "oos_maxdd": -0.0053, "wf_mean": 7.55, "wf_min": 6.02},
        "K217a_50_50": {"oos_sharpe": variants["K217a"]["oos_sharpe"], "oos_maxdd": variants["K217a"]["oos_maxdd"],
                        "wf_mean": variants["K217a"]["wf_mean"], "wf_min": variants["K217a"]["wf_min"]},
        "K217b_inv_vol":{"oos_sharpe": variants["K217b"]["oos_sharpe"], "oos_maxdd": variants["K217b"]["oos_maxdd"],
                         "wf_mean": variants["K217b"]["wf_mean"], "wf_min": variants["K217b"]["wf_min"]},
        "K217c_sharpe_wt":{"oos_sharpe": variants["K217c"]["oos_sharpe"], "oos_maxdd": variants["K217c"]["oos_maxdd"],
                           "wf_mean": variants["K217c"]["wf_mean"], "wf_min": variants["K217c"]["wf_min"]},
        "K217d_recency":{"oos_sharpe": variants["K217d"]["oos_sharpe"], "oos_maxdd": variants["K217d"]["oos_maxdd"],
                         "wf_mean": variants["K217d"]["wf_mean"], "wf_min": variants["K217d"]["wf_min"]},
    },
}

with open("/Users/nekonaomichi/crypto-lab/wave_k217_meta_ensemble.json", "w") as f:
    json.dump(result, f, indent=2)
print("\nSaved: wave_k217_meta_ensemble.json")

with open("/Users/nekonaomichi/crypto-lab/wave_k217_curves.json", "w") as f:
    json.dump(curves, f)
print("Saved: wave_k217_curves.json")

print(f"\nRuntime: {runtime}s")
print(f"\nVERDICT: {verdict}")
