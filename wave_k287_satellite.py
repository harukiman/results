"""
Wave K287 — Satellite Portfolio: K270 + K275 as Separate Allocation
Objective: Test K270 (dYdX, 731d) + K275 (OKX, 96d) as satellite alongside K280 main.

Variants:
  K287a: K270 50% + K275 50%
  K287b: K270 70% + K275 30%
  K287c: K270 inv-vol + K275 inv-vol
  K287d: K280 80% + Satellite 20%  (using K287c as satellite)
  K287e: K280 90% + Satellite 10%
"""

import json
import numpy as np
from datetime import datetime

# ── Load source curves ─────────────────────────────────────────────────────────
with open("/Users/nekonaomichi/crypto-lab/wave_k270_curves.json") as f:
    k270_curves = json.load(f)
with open("/Users/nekonaomichi/crypto-lab/wave_k275_curves.json") as f:
    k275_curves = json.load(f)
with open("/Users/nekonaomichi/crypto-lab/wave_k280_curves.json") as f:
    k280_curves = json.load(f)

# ── Load result files for metadata ────────────────────────────────────────────
with open("/Users/nekonaomichi/crypto-lab/wave_k270_alt_exchange_fr.json") as f:
    k270_res = json.load(f)
with open("/Users/nekonaomichi/crypto-lab/wave_k275_okx_fr.json") as f:
    k275_res = json.load(f)
with open("/Users/nekonaomichi/crypto-lab/wave_k280_k272a_k276b.json") as f:
    k280_res = json.load(f)

# ── Align series to common windows ────────────────────────────────────────────
# K270: 2024-05-25 → 2026-05-25 (731d)
# K275: 2026-02-19 → 2026-05-25 (96d)
# K280: 2025-01-22 → 2026-04-14 (448d)

k270_dates = k270_curves["dates"]
k275_dates = k275_curves["dates"]
k280_dates = k280_curves["dates"]

# Build date-indexed pnl series (daily returns)
def equity_to_daily_returns(equity_list):
    eq = np.array(equity_list, dtype=float)
    ret = np.zeros(len(eq))
    ret[1:] = np.diff(eq) / eq[:-1]
    return ret

k270_eq = np.array(k270_curves["equity"], dtype=float)
k275_eq = np.array(k275_curves["equity"], dtype=float)
k280_eq = np.array(k280_curves["K280"], dtype=float)

k270_ret = equity_to_daily_returns(k270_eq)
k275_ret = equity_to_daily_returns(k275_eq)
k280_ret = equity_to_daily_returns(k280_eq)

k270_map = {d: k270_ret[i] for i, d in enumerate(k270_dates)}
k275_map = {d: k275_ret[i] for i, d in enumerate(k275_dates)}
k280_map = {d: k280_ret[i] for i, d in enumerate(k280_dates)}

# Common window: K275 limited = 96d (2026-02-19 → 2026-05-25)
sat_dates_sorted = sorted(set(k270_dates) & set(k275_dates))
print(f"[Satellite window] {sat_dates_sorted[0]} → {sat_dates_sorted[-1]}, {len(sat_dates_sorted)} days")

# Combined window for K280 + Satellite (all three overlap)
all3_dates_sorted = sorted(set(k270_dates) & set(k275_dates) & set(k280_dates))
print(f"[3-way overlap] {all3_dates_sorted[0]} → {all3_dates_sorted[-1]}, {len(all3_dates_sorted)} days")

# ── Helper functions ───────────────────────────────────────────────────────────
def metrics(returns_arr, n_days_per_year=365):
    r = np.array(returns_arr)
    ann_ret = np.mean(r) * n_days_per_year
    ann_vol = np.std(r, ddof=1) * np.sqrt(n_days_per_year)
    sharpe = ann_ret / ann_vol if ann_vol > 0 else 0.0
    eq = np.cumprod(1 + r)
    roll_max = np.maximum.accumulate(eq)
    dd = eq / roll_max - 1
    max_dd = float(np.min(dd))
    win_rate = float(np.mean(r > 0))
    total_ret = float(eq[-1] - 1)
    n_days = len(r)
    return {
        "sharpe": round(float(sharpe), 4),
        "max_dd": round(max_dd, 6),
        "ann_ret": round(float(ann_ret), 6),
        "ann_vol": round(float(ann_vol), 6),
        "win_rate": round(win_rate, 6),
        "total_return": round(total_ret, 6),
        "n_days": n_days,
    }

def equity_curve(returns_arr):
    r = np.array(returns_arr)
    return list(np.cumprod(1 + r))

def walk_forward(returns_arr, dates_list, n_folds=3):
    n = len(returns_arr)
    fold_size = n // n_folds
    folds = []
    for i in range(n_folds):
        start = i * fold_size
        end = start + fold_size if i < n_folds - 1 else n
        fold_ret = returns_arr[start:end]
        m = metrics(fold_ret)
        folds.append({
            "fold": i + 1,
            "start": dates_list[start],
            "end": dates_list[end - 1],
            "n_days": end - start,
            "sharpe": m["sharpe"],
            "max_dd": m["max_dd"],
        })
    return folds

def correlation(r1, r2):
    r1, r2 = np.array(r1), np.array(r2)
    if np.std(r1) == 0 or np.std(r2) == 0:
        return 0.0
    return float(np.corrcoef(r1, r2)[0, 1])

# ── Extract aligned return arrays ─────────────────────────────────────────────
k270_sat = np.array([k270_map[d] for d in sat_dates_sorted])
k275_sat = np.array([k275_map[d] for d in sat_dates_sorted])

# Vol for inv-vol weighting
vol_270 = np.std(k270_sat, ddof=1)
vol_275 = np.std(k275_sat, ddof=1)
inv_vol_sum = (1 / vol_270) + (1 / vol_275)
w_270_invvol = (1 / vol_270) / inv_vol_sum
w_275_invvol = (1 / vol_275) / inv_vol_sum

print(f"[Inv-vol weights] K270: {w_270_invvol:.4f}, K275: {w_275_invvol:.4f}")

# ── Build satellite variants ───────────────────────────────────────────────────
variants = {
    "K287a": (k270_sat * 0.50 + k275_sat * 0.50, 0.50, 0.50),
    "K287b": (k270_sat * 0.70 + k275_sat * 0.30, 0.70, 0.30),
    "K287c": (k270_sat * w_270_invvol + k275_sat * w_275_invvol, w_270_invvol, w_275_invvol),
}

satellite_results = {}
for name, (sat_ret, w270, w275) in variants.items():
    m = metrics(sat_ret)
    wf = walk_forward(sat_ret, sat_dates_sorted, n_folds=3)
    wf_sharpes = [f["sharpe"] for f in wf]
    satellite_results[name] = {
        "weights": {"K270": round(w270, 4), "K275": round(w275, 4)},
        "metrics": m,
        "wf_folds": wf,
        "wf_summary": {
            "mean_sharpe": round(float(np.mean(wf_sharpes)), 4),
            "min_sharpe": round(float(np.min(wf_sharpes)), 4),
            "all_positive": all(s > 0 for s in wf_sharpes),
        },
        "equity_curve": [round(v, 8) for v in equity_curve(sat_ret)],
    }
    print(f"[{name}] Sh={m['sharpe']:.2f}, MaxDD={m['max_dd']:.6f}, WF_min={min(wf_sharpes):.2f}")

# ── Best satellite = K287c (inv-vol) for combined tests ───────────────────────
best_sat_name = "K287c"
best_sat_ret = variants[best_sat_name][0]

# ── Correlation: satellite vs K280 (on 3-way overlap) ─────────────────────────
k280_3way = np.array([k280_map[d] for d in all3_dates_sorted])
k270_3way = np.array([k270_map[d] for d in all3_dates_sorted])
k275_3way = np.array([k275_map[d] for d in all3_dates_sorted])

_, w270_c, w275_c = variants[best_sat_name]
sat_3way = k270_3way * w270_c + k275_3way * w275_c

rho_sat_k280 = correlation(sat_3way, k280_3way)
rho_k270_k280 = correlation(k270_3way, k280_3way)
rho_k275_k280 = correlation(k275_3way, k280_3way)
print(f"[Correlation] Satellite vs K280: {rho_sat_k280:.4f}")
print(f"[Correlation] K270 vs K280: {rho_k270_k280:.4f}")
print(f"[Correlation] K275 vs K280: {rho_k275_k280:.4f}")

# ── Combined portfolio tests (K287d, K287e) ────────────────────────────────────
# K280 standalone reference (3-way window)
k280_standalone_m = metrics(k280_3way)

combined_results = {}
for name, w_sat, w_k280 in [("K287d", 0.20, 0.80), ("K287e", 0.10, 0.90)]:
    combined_ret = k280_3way * w_k280 + sat_3way * w_sat
    m = metrics(combined_ret)
    wf = walk_forward(combined_ret, all3_dates_sorted, n_folds=3)
    wf_sharpes = [f["sharpe"] for f in wf]
    combined_results[name] = {
        "weights": {"K280": w_k280, "Satellite": w_sat, "satellite_variant": best_sat_name},
        "metrics": m,
        "wf_folds": wf,
        "wf_summary": {
            "mean_sharpe": round(float(np.mean(wf_sharpes)), 4),
            "min_sharpe": round(float(np.min(wf_sharpes)), 4),
            "all_positive": all(s > 0 for s in wf_sharpes),
        },
        "vs_k280_alone": {
            "k280_sharpe": k280_standalone_m["sharpe"],
            "combined_sharpe": m["sharpe"],
            "delta_sharpe": round(m["sharpe"] - k280_standalone_m["sharpe"], 4),
            "k280_maxdd": k280_standalone_m["max_dd"],
            "combined_maxdd": m["max_dd"],
        },
        "equity_curve": [round(v, 8) for v in equity_curve(combined_ret)],
    }
    print(f"[{name}] Sh={m['sharpe']:.2f}, MaxDD={m['max_dd']:.6f}, vs K280 delta={m['sharpe']-k280_standalone_m['sharpe']:+.2f}")

# ── Acceptance gates (Satellite standalone) ────────────────────────────────────
best = satellite_results[best_sat_name]
gates_satellite = {
    "G1_Satellite_Sh_gt_5": best["metrics"]["sharpe"] > 5.0,
    "G2_WF_all_folds_positive": best["wf_summary"]["all_positive"],
    "G3_rho_Satellite_vs_K280_lt_0.5": rho_sat_k280 < 0.5,
    "G4_Combined_Sh_gt_K280": any(
        v["vs_k280_alone"]["delta_sharpe"] > 0 for v in combined_results.values()
    ),
}
n_passed = sum(gates_satellite.values())
verdict = "ACCEPT" if all(gates_satellite.values()) else f"PARTIAL ({n_passed}/4)"
print(f"\n[Gates] {gates_satellite}")
print(f"[Verdict] {verdict}")

# ── Assemble final JSON output ─────────────────────────────────────────────────
output = {
    "wave": "K287",
    "task": "Satellite Portfolio: K270 (dYdX) + K275 (OKX) as separate allocation",
    "as_of": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
    "data_info": {
        "k270_window": {"start": k270_dates[0], "end": k270_dates[-1], "n_days": len(k270_dates)},
        "k275_window": {"start": k275_dates[0], "end": k275_dates[-1], "n_days": len(k275_dates)},
        "k280_window": {"start": k280_dates[0], "end": k280_dates[-1], "n_days": len(k280_dates)},
        "satellite_common_window": {
            "start": sat_dates_sorted[0], "end": sat_dates_sorted[-1],
            "n_days": len(sat_dates_sorted)
        },
        "three_way_overlap": {
            "start": all3_dates_sorted[0], "end": all3_dates_sorted[-1],
            "n_days": len(all3_dates_sorted)
        },
    },
    "source_metrics": {
        "K270_OOS": k270_res["oos_metrics"],
        "K270_WF": k270_res["wf_summary"],
        "K275_OOS": k275_res["oos_metrics"],
        "K275_WF": k275_res["wf_summary"],
        "K280_OOS_Sh": k280_res["k280_results"]["oos_sharpe"],
        "K280_OOS_MaxDD": k280_res["k280_results"]["oos_maxdd"],
    },
    "inv_vol_weights": {"K270": round(w_270_invvol, 4), "K275": round(w_275_invvol, 4)},
    "satellite_variants": {
        k: {kk: vv for kk, vv in v.items() if kk != "equity_curve"}
        for k, v in satellite_results.items()
    },
    "correlations": {
        "sat_vs_k280_3way": round(rho_sat_k280, 4),
        "k270_vs_k280_3way": round(rho_k270_k280, 4),
        "k275_vs_k280_3way": round(rho_k275_k280, 4),
    },
    "k280_standalone_3way": k280_standalone_m,
    "combined_variants": {
        k: {kk: vv for kk, vv in v.items() if kk != "equity_curve"}
        for k, v in combined_results.items()
    },
    "acceptance_gates": gates_satellite,
    "n_gates_passed": n_passed,
    "n_gates_total": len(gates_satellite),
    "verdict": verdict,
    "satellite_deployment_plan": {
        "recommended_satellite": best_sat_name,
        "recommended_combined": "K287d" if combined_results["K287d"]["vs_k280_alone"]["delta_sharpe"] > 0 else "K287e",
        "capital_split": {
            "K280_main": "80-90% of total capital",
            "Satellite": "10-20% of total capital",
            "rationale": "K270 MaxDD too risky for K280 near-zero architecture; operational separation preserves K280 properties while adding diversified alpha"
        },
        "operational_notes": [
            "K270 runs on dYdX v4 — separate exchange account",
            "K275 runs on OKX — separate exchange account",
            "K280 runs on existing infrastructure",
            "Rebalance satellite monthly or on 5% drift threshold",
            "Monitor satellite MaxDD threshold: stop if satellite DD > -1.5% (half of K270 full-period MaxDD)",
        ]
    }
}

with open("/Users/nekonaomichi/crypto-lab/wave_k287_satellite.json", "w") as f:
    json.dump(output, f, indent=2)
print("\n[SAVED] wave_k287_satellite.json")

# ── Curves JSON ───────────────────────────────────────────────────────────────
curves_out = {
    "wave": "K287",
    "satellite_dates": sat_dates_sorted,
    "three_way_dates": all3_dates_sorted,
    "K270_sat_equity": [round(v, 8) for v in equity_curve(k270_sat)],
    "K275_sat_equity": [round(v, 8) for v in equity_curve(k275_sat)],
    "K287a_equity": satellite_results["K287a"]["equity_curve"],
    "K287b_equity": satellite_results["K287b"]["equity_curve"],
    "K287c_equity": satellite_results["K287c"]["equity_curve"],
    "K287d_equity": combined_results["K287d"]["equity_curve"],
    "K287e_equity": combined_results["K287e"]["equity_curve"],
    "K280_3way_equity": [round(v, 8) for v in equity_curve(k280_3way)],
}

with open("/Users/nekonaomichi/crypto-lab/wave_k287_curves.json", "w") as f:
    json.dump(curves_out, f, indent=2)
print("[SAVED] wave_k287_curves.json")

# ── Print summary ─────────────────────────────────────────────────────────────
print("\n" + "="*60)
print("WAVE K287 SATELLITE PORTFOLIO SUMMARY")
print("="*60)
print(f"\nSatellite window: {sat_dates_sorted[0]} → {sat_dates_sorted[-1]} ({len(sat_dates_sorted)}d)")
print(f"3-way overlap:    {all3_dates_sorted[0]} → {all3_dates_sorted[-1]} ({len(all3_dates_sorted)}d)")
print(f"\nInv-vol weights: K270={w_270_invvol:.3f}, K275={w_275_invvol:.3f}")
print(f"\n{'Variant':<10} {'Sh':>8} {'MaxDD':>10} {'WF_min':>8} {'WF_all+':>8}")
print("-"*50)
for name, res in satellite_results.items():
    m = res["metrics"]
    wf = res["wf_summary"]
    print(f"{name:<10} {m['sharpe']:>8.2f} {m['max_dd']:>10.6f} {wf['min_sharpe']:>8.2f} {str(wf['all_positive']):>8}")
print(f"\nK280 standalone (55d): Sh={k280_standalone_m['sharpe']:.2f}, MaxDD={k280_standalone_m['max_dd']:.6f}")
print(f"\n{'Variant':<10} {'Sh':>8} {'MaxDD':>10} {'dSh vs K280':>12}")
print("-"*44)
for name, res in combined_results.items():
    m = res["metrics"]
    d = res["vs_k280_alone"]["delta_sharpe"]
    print(f"{name:<10} {m['sharpe']:>8.2f} {m['max_dd']:>10.6f} {d:>+12.2f}")
print(f"\nCorrelation Satellite vs K280: {rho_sat_k280:.4f}")
print(f"Gates passed: {n_passed}/{len(gates_satellite)}")
print(f"Verdict: {verdict}")
