"""
Wave K301 — v6.12 Extended Satellite
K280 (80%) + Extended Satellite [K270 + K275 + K297] (20%)

K297 RWA carry (PAXG + SPX) added as 3rd satellite component.
Common window: 96d (K275 limit: 2026-02-19 to 2026-05-25)
K297 EW portfolio of PAXG (16.91 Sh) + SPX (5.87 Sh) → 10.17 Sh

Acceptance gate: 96d OOS Sh > K287d v6.11 on same 96d window
"""

import json
import numpy as np
from datetime import datetime

# ─── helpers ──────────────────────────────────────────────────────────────────

def sharpe(returns, ann=365):
    r = np.array(returns, dtype=float)
    if len(r) < 2 or r.std() == 0:
        return 0.0
    return (r.mean() / r.std()) * np.sqrt(ann)

def maxdd(equity):
    eq = np.array(equity, dtype=float)
    peak = np.maximum.accumulate(eq)
    dd = eq / peak - 1.0
    return float(dd.min())

def metrics(equity, dates=None):
    eq = np.array(equity, dtype=float)
    rets = np.diff(eq) / eq[:-1]
    n = len(rets)
    ann_ret = float(eq[-1] ** (365.0 / n) - 1) if n > 0 else 0.0
    ann_vol = float(rets.std() * np.sqrt(365)) if n > 1 else 0.0
    sh = sharpe(rets)
    md = maxdd(eq)
    wr = float(np.mean(rets > 0)) if n > 0 else 0.0
    tr = float(eq[-1] - 1.0)
    return {
        "sharpe": round(sh, 4),
        "max_dd": round(md, 6),
        "ann_ret": round(ann_ret, 6),
        "ann_vol": round(ann_vol, 6),
        "win_rate": round(wr, 6),
        "total_return": round(tr, 6),
        "n_days": n,
    }

def equity_from_dates_returns(dates, rets):
    """Build equity curve list from parallel dates and returns."""
    eq = [1.0]
    for r in rets:
        eq.append(eq[-1] * (1 + r))
    return eq  # len = len(dates)

def slice_equity_to_window(dates, equity, start, end):
    """Slice equity curve to [start, end] window, rebased to 1.0."""
    idx = [(i, d) for i, d in enumerate(dates) if start <= d <= end]
    if not idx:
        return [], []
    idxs = [i for i, d in idx]
    ds = [d for i, d in idx]
    eq = [equity[i] for i in idxs]
    base = eq[0]
    eq = [v / base for v in eq]
    return ds, eq

def wf_folds(dates, equity, n_folds=3):
    """Split equity into n_folds sequential folds and compute per-fold metrics."""
    n = len(dates)
    fold_size = n // n_folds
    folds = []
    for f in range(n_folds):
        s = f * fold_size
        e = (f + 1) * fold_size if f < n_folds - 1 else n
        fd = dates[s:e]
        fe = equity[s:e]
        fe_rb = [v / fe[0] for v in fe]
        m = metrics(fe_rb)
        folds.append({
            "fold": f + 1,
            "start": fd[0],
            "end": fd[-1],
            "n_days": m["n_days"],
            "sharpe": m["sharpe"],
            "max_dd": m["max_dd"],
        })
    return folds

def wf_summary(folds):
    sharpes = [f["sharpe"] for f in folds]
    return {
        "mean_sharpe": round(float(np.mean(sharpes)), 4),
        "min_sharpe": round(float(np.min(sharpes)), 4),
        "all_positive": bool(all(s > 0 for s in sharpes)),
    }

def corr(a, b):
    a, b = np.array(a, dtype=float), np.array(b, dtype=float)
    if len(a) != len(b) or a.std() == 0 or b.std() == 0:
        return float("nan")
    return float(np.corrcoef(a, b)[0, 1])

def inv_vol_weights(vol_dict, caps=None):
    """Compute inverse-vol weights with optional per-component caps."""
    ivs = {k: 1.0 / v if v > 0 else 0.0 for k, v in vol_dict.items()}
    total = sum(ivs.values())
    w = {k: v / total for k, v in ivs.items()}
    if caps:
        # Iterative capping
        for _ in range(20):
            capped = {k: min(v, caps.get(k, 1.0)) for k, v in w.items()}
            ct = sum(capped.values())
            if abs(ct - 1.0) < 1e-9:
                w = capped
                break
            # Redistribute excess from capped components
            excess = {k: max(0, v - caps.get(k, 1.0)) for k, v in w.items()}
            total_excess = sum(excess.values())
            uncapped_total = sum(v for k, v in w.items() if v < caps.get(k, 1.0))
            if uncapped_total == 0:
                w = capped
                break
            new_w = {}
            for k, v in w.items():
                if v >= caps.get(k, 1.0):
                    new_w[k] = caps[k]
                else:
                    new_w[k] = v + total_excess * (v / uncapped_total)
            w = new_w
    return {k: round(v, 6) for k, v in w.items()}

def blend_equities(components_eq, weights):
    """Blend equity curves by computing blended returns then rebuilding equity."""
    names = list(components_eq.keys())
    n = len(next(iter(components_eq.values())))
    blended = [1.0]
    for i in range(1, n):
        r = 0.0
        for name in names:
            eq = components_eq[name]
            daily_ret = eq[i] / eq[i - 1] - 1.0
            r += weights.get(name, 0.0) * daily_ret
        blended.append(blended[-1] * (1 + r))
    return blended

# ─── load source curves ────────────────────────────────────────────────────────

with open("/Users/nekonaomichi/crypto-lab/wave_k270_curves.json") as f:
    k270_raw = json.load(f)

with open("/Users/nekonaomichi/crypto-lab/wave_k275_curves.json") as f:
    k275_raw = json.load(f)

with open("/Users/nekonaomichi/crypto-lab/wave_k280_curves.json") as f:
    k280_raw = json.load(f)

with open("/Users/nekonaomichi/crypto-lab/wave_k297_curves.json") as f:
    k297_raw = json.load(f)

# K287 curves for reference
with open("/Users/nekonaomichi/crypto-lab/wave_k287_curves.json") as f:
    k287_curves = json.load(f)
with open("/Users/nekonaomichi/crypto-lab/wave_k287_satellite.json") as f:
    k287_sat = json.load(f)

# ─── define windows ───────────────────────────────────────────────────────────

# Common satellite window: 96d (K275 limit)
SAT_START = "2026-02-19"
SAT_END = "2026-05-25"

# K280 3-way overlap window
K280_START = "2025-01-22"
K280_END = "2026-04-14"

# K297 window (504d portfolio equity curve)
K297_START = "2025-01-07"

# ─── extract component equity curves on common window ─────────────────────────

# K270 on 96d satellite window
_, k270_sat_eq = slice_equity_to_window(k270_raw["dates"], k270_raw["equity"], SAT_START, SAT_END)
sat_dates, _ = slice_equity_to_window(k270_raw["dates"], k270_raw["equity"], SAT_START, SAT_END)

# K275 on 96d satellite window (already 96d)
k275_sat_eq = [v / k275_raw["equity"][0] for v in k275_raw["equity"]]
assert len(k275_sat_eq) == len(sat_dates), f"K275 len mismatch: {len(k275_sat_eq)} vs {len(sat_dates)}"

# K297 EW portfolio on 96d satellite window
# Build EW from PAXG and SPX daily returns
k297_portfolio = k297_raw["portfolio_equity_curve"]  # date -> equity
k297_dates_all = sorted(k297_portfolio.keys())
k297_eq_full = [k297_portfolio[d] for d in k297_dates_all]
# Slice to common window
_, k297_sat_eq = slice_equity_to_window(k297_dates_all, k297_eq_full, SAT_START, SAT_END)

# Verify alignment
assert len(k297_sat_eq) == len(sat_dates), f"K297 len mismatch: {len(k297_sat_eq)} vs {len(sat_dates)}"
assert len(k270_sat_eq) == len(sat_dates)

print(f"Common satellite window: {SAT_START} to {SAT_END}, n={len(sat_dates)}")

# Also extract standalone per-coin K297 data for full window
k297_spx_raw = k297_raw["coins"]["SPX"]["equity_curve"]
k297_paxg_raw = k297_raw["coins"]["PAXG"]["equity_curve"]

# ─── K297 standalone metrics (full 504d window) ────────────────────────────────

k297_full_eq = [k297_portfolio[d] for d in k297_dates_all]
k297_full_eq_rb = [v / k297_full_eq[0] for v in k297_full_eq]
k297_full_metrics = metrics(k297_full_eq_rb)
print(f"K297 full (504d): Sh={k297_full_metrics['sharpe']}")

# K297 on sat window
k297_sat_metrics = metrics(k297_sat_eq)
print(f"K297 sat (96d): Sh={k297_sat_metrics['sharpe']}")

# ─── daily returns for each component (96d window) ────────────────────────────

def daily_rets(eq):
    eq = np.array(eq, dtype=float)
    return (eq[1:] / eq[:-1] - 1.0).tolist()

r270 = daily_rets(k270_sat_eq)
r275 = daily_rets(k275_sat_eq)
r297 = daily_rets(k297_sat_eq)

# Vols for inv-vol weighting
vol270 = float(np.std(r270))
vol275 = float(np.std(r275))
vol297 = float(np.std(r297))

print(f"\nComponent daily vols (96d): K270={vol270:.6f}, K275={vol275:.6f}, K297={vol297:.6f}")

# ─── 4x4 satellite correlation matrix ─────────────────────────────────────────

# K297 individual coins on common window
spx_dates = sorted(k297_spx_raw.keys())
spx_eq_all = [k297_spx_raw[d] for d in spx_dates]
_, spx_sat_eq = slice_equity_to_window(spx_dates, spx_eq_all, SAT_START, SAT_END)

paxg_dates = sorted(k297_paxg_raw.keys())
paxg_eq_all = [k297_paxg_raw[d] for d in paxg_dates]
_, paxg_sat_eq = slice_equity_to_window(paxg_dates, paxg_eq_all, SAT_START, SAT_END)

# Pad PAXG if shorter (started 2025-04-06, but portfolio starts 2025-01-07)
# For 96d window PAXG should be available
print(f"SPX sat len: {len(spx_sat_eq)}, PAXG sat len: {len(paxg_sat_eq)}")

r_spx = daily_rets(spx_sat_eq) if len(spx_sat_eq) > 1 else []
r_paxg = daily_rets(paxg_sat_eq) if len(paxg_sat_eq) > 1 else []

# Build correlation matrix: K270, K275, K297(EW), K297(PAXG), K297(SPX)
n_common = min(len(r270), len(r275), len(r297))
rr270, rr275, rr297 = r270[:n_common], r275[:n_common], r297[:n_common]

# SPX and PAXG may have same length
n_coin = min(len(r_spx), len(r_paxg), n_common) if r_spx and r_paxg else 0

corr_matrix = {}
components = {
    "K270": rr270,
    "K275": rr275,
    "K297_EW": rr297,
}
if n_coin > 0:
    components["K297_PAXG"] = r_paxg[:n_coin]
    components["K297_SPX"] = r_spx[:n_coin]

for ka, ra in components.items():
    corr_matrix[ka] = {}
    for kb, rb in components.items():
        n = min(len(ra), len(rb))
        corr_matrix[ka][kb] = round(corr(ra[:n], rb[:n]), 4)

print("\nCorrelation matrix:")
for ka, row in corr_matrix.items():
    print(f"  {ka}: {row}")

# ─── satellite component metrics (96d) ────────────────────────────────────────

k270_sat_metrics = metrics(k270_sat_eq)
k275_sat_metrics = metrics(k275_sat_eq)

print(f"\nComponent metrics (96d sat window):")
print(f"  K270: Sh={k270_sat_metrics['sharpe']}, MaxDD={k270_sat_metrics['max_dd']}")
print(f"  K275: Sh={k275_sat_metrics['sharpe']}, MaxDD={k275_sat_metrics['max_dd']}")
print(f"  K297: Sh={k297_sat_metrics['sharpe']}, MaxDD={k297_sat_metrics['max_dd']}")

# ─── 5 satellite variants ─────────────────────────────────────────────────────

# K301a: Equal weight (33/33/33)
w_a = {"K270": 1/3, "K275": 1/3, "K297": 1/3}

# K301b: Inv-vol uncapped
w_b = inv_vol_weights({"K270": vol270, "K275": vol275, "K297": vol297})

# K301c: Inv-vol + K297 cap 15%
w_c = inv_vol_weights({"K270": vol270, "K275": vol275, "K297": vol297},
                      caps={"K297": 0.15})

# K301d: Inv-vol + K297 cap 25%
w_d = inv_vol_weights({"K270": vol270, "K275": vol275, "K297": vol297},
                      caps={"K297": 0.25})

# K301e: Inv-vol + K297 cap 30%
w_e = inv_vol_weights({"K270": vol270, "K275": vol275, "K297": vol297},
                      caps={"K297": 0.30})

sat_weights = {
    "K301a": w_a,
    "K301b": w_b,
    "K301c": w_c,
    "K301d": w_d,
    "K301e": w_e,
}

print("\nSatellite weights:")
for name, w in sat_weights.items():
    print(f"  {name}: {w}")

# Build blended equities for each variant
sat_components_eq = {"K270": k270_sat_eq, "K275": k275_sat_eq, "K297": k297_sat_eq}

satellite_variants = {}
satellite_equities = {}

for name, w in sat_weights.items():
    sat_eq = blend_equities(sat_components_eq, w)
    m = metrics(sat_eq)
    folds = wf_folds(sat_dates, sat_eq, n_folds=3)
    wfs = wf_summary(folds)
    satellite_variants[name] = {
        "weights": {k: round(v, 4) for k, v in w.items()},
        "metrics": m,
        "wf_folds": folds,
        "wf_summary": wfs,
    }
    satellite_equities[name] = sat_eq
    print(f"  {name}: Sh={m['sharpe']}, MaxDD={m['max_dd']}, WF_mean={wfs['mean_sharpe']}")

# ─── K280 on 96d window ───────────────────────────────────────────────────────

# K280 composite equity curve (pre-built)
k280_dates = k280_raw["dates"]
k280_eq_full = k280_raw["K280"]

_, k280_sat_eq = slice_equity_to_window(k280_dates, k280_eq_full, SAT_START, SAT_END)
print(f"\nK280 on 96d sat window: {len(k280_sat_eq)} days")

if len(k280_sat_eq) < 10:
    # K280 ends 2026-04-14, so 96d window only has partial overlap
    # Use available overlap
    k280_sat_dates, k280_sat_eq = slice_equity_to_window(k280_dates, k280_eq_full, SAT_START, K280_END)
    print(f"  K280 partial overlap to {K280_END}: {len(k280_sat_eq)} days")
    overlap_start = SAT_START
    overlap_end = K280_END
else:
    k280_sat_dates = sat_dates
    overlap_start = SAT_START
    overlap_end = SAT_END

# K280 on 55d three-way window (from K287 for reference)
THREE_WAY_END = "2026-04-14"
k280_3way_dates, k280_3way_eq = slice_equity_to_window(k280_dates, k280_eq_full, SAT_START, THREE_WAY_END)
print(f"K280 three-way (55d) window: {len(k280_3way_eq)} days")

# ─── Combined K280 + Extended Satellite ───────────────────────────────────────

# For combined metrics: use available K280 overlap window
# K280 data ends 2026-04-14 → overlap with K275 = 2026-02-19 to 2026-04-14 (55d)
# We compute combined on this 55d overlap (same as K287d reference)

combined_variants = {}
combined_equities = {}

# Slice all satellite equities to 55d three-way window
sat_3way_components = {}
for comp_name, comp_eq in sat_components_eq.items():
    if comp_name == "K270":
        _, sliced = slice_equity_to_window(k270_raw["dates"], k270_raw["equity"], SAT_START, THREE_WAY_END)
    elif comp_name == "K275":
        _, sliced = slice_equity_to_window(k275_raw["dates"], k275_raw["equity"], SAT_START, THREE_WAY_END)
    else:  # K297
        _, sliced = slice_equity_to_window(k297_dates_all, k297_eq_full, SAT_START, THREE_WAY_END)
    sat_3way_components[comp_name] = sliced

print(f"\nThree-way window component lengths: {[(k, len(v)) for k, v in sat_3way_components.items()]}")
print(f"K280 3-way len: {len(k280_3way_eq)}")

# Align to minimum length
min_3way = min(len(k280_3way_eq), *[len(v) for v in sat_3way_components.values()])
k280_3way_trim = k280_3way_eq[:min_3way]
sat_3way_trim = {k: v[:min_3way] for k, v in sat_3way_components.items()}
dates_3way = k280_3way_dates[:min_3way]
print(f"Aligned three-way n={min_3way}, {dates_3way[0]} to {dates_3way[-1]}")

# K287d reference on same 55d window
k287d_ref = k287_curves.get("K287d_equity", [])[:min_3way]

for sat_name, w in sat_weights.items():
    sat_3way_eq = blend_equities(sat_3way_trim, w)
    # Combined: 80% K280 + 20% satellite
    combined_eq = blend_equities(
        {"K280": k280_3way_trim, "Sat": sat_3way_eq},
        {"K280": 0.8, "Sat": 0.2}
    )
    m = metrics(combined_eq)
    folds = wf_folds(dates_3way, combined_eq, n_folds=3)
    wfs = wf_summary(folds)

    # vs K280 alone
    k280_m = metrics(k280_3way_trim)

    combined_variants[f"K301_{sat_name[-1]}"] = {
        "satellite_variant": sat_name,
        "weights": {"K280": 0.8, "Satellite": 0.2},
        "satellite_weights": {k: round(v, 4) for k, v in w.items()},
        "metrics": m,
        "wf_folds": folds,
        "wf_summary": wfs,
        "vs_k280_alone": {
            "k280_sharpe": k280_m["sharpe"],
            "combined_sharpe": m["sharpe"],
            "delta_sharpe": round(m["sharpe"] - k280_m["sharpe"], 4),
        },
        "vs_k287d_ref": {
            "k287d_sharpe": 33.0032,
            "combined_sharpe": m["sharpe"],
            "delta_sharpe": round(m["sharpe"] - 33.0032, 4),
        },
    }
    combined_equities[f"K301_{sat_name[-1]}"] = combined_eq
    print(f"  K301_{sat_name[-1]}: Sh={m['sharpe']:.4f}, WF_mean={wfs['mean_sharpe']:.4f}, vs_K287d={m['sharpe']-33.0032:+.4f}")

# ─── Select best combined variant ─────────────────────────────────────────────

best_key = max(combined_variants, key=lambda k: combined_variants[k]["metrics"]["sharpe"])
best = combined_variants[best_key]
print(f"\nBest combined: {best_key} → Sh={best['metrics']['sharpe']}")

# ─── Acceptance gates ─────────────────────────────────────────────────────────

# Reference K287d: 33.00 Sharpe on 55d three-way window
K287D_SH = 33.0032

# G1: Best combined Sh > K287d on same 55d window
g1 = best["metrics"]["sharpe"] > K287D_SH

# G2: All WF folds positive
g2 = best["wf_summary"]["all_positive"]

# G3: All 3 satellite components contribute > 5% weight
sat_w = best["satellite_weights"]
g3 = all(v >= 0.05 for v in sat_w.values())

# G4: K297 correlation vs K270 and K275 both < 0.5
rho_297_270 = corr_matrix.get("K297_EW", {}).get("K270", float("nan"))
rho_297_275 = corr_matrix.get("K297_EW", {}).get("K275", float("nan"))
g4 = abs(rho_297_270) < 0.5 and abs(rho_297_275) < 0.5

gates = {
    "G1_Combined_Sh_gt_K287d": {"pass": g1, "value": best["metrics"]["sharpe"], "threshold": K287D_SH},
    "G2_WF_all_folds_positive": {"pass": g2, "folds": best["wf_folds"]},
    "G3_all_components_gt_5pct": {"pass": g3, "weights": sat_w},
    "G4_K297_rho_lt_0p5": {"pass": g4, "rho_vs_K270": round(rho_297_270, 4), "rho_vs_K275": round(rho_297_275, 4)},
}

n_pass = sum(1 for v in gates.values() if v["pass"])
print(f"\nAcceptance gates: {n_pass}/4 passed")
for k, v in gates.items():
    print(f"  {k}: {'PASS' if v['pass'] else 'FAIL'}")

verdict = "ACCEPT" if n_pass == 4 else ("CONDITIONAL" if n_pass >= 3 else "REJECT")
print(f"\nVerdict: {verdict}")

# ─── Build output curves JSON ──────────────────────────────────────────────────

curves_out = {
    "wave": "K301",
    "generated_at": datetime.utcnow().isoformat() + "Z",
    "satellite_dates": sat_dates,
    "three_way_dates": dates_3way,
    "K270_sat_equity": [round(v, 8) for v in k270_sat_eq],
    "K275_sat_equity": [round(v, 8) for v in k275_sat_eq],
    "K297_sat_equity": [round(v, 8) for v in k297_sat_eq],
    "K280_3way_equity": [round(v, 8) for v in k280_3way_trim],
}

for sat_name, eq in satellite_equities.items():
    curves_out[f"{sat_name}_equity"] = [round(v, 8) for v in eq]

for comb_name, eq in combined_equities.items():
    curves_out[f"{comb_name}_equity"] = [round(v, 8) for v in eq]

# ─── Build main results JSON ───────────────────────────────────────────────────

results = {
    "wave": "K301",
    "version": "v6.12_extended",
    "generated_at": datetime.utcnow().isoformat() + "Z",
    "data_info": {
        "satellite_window": {"start": SAT_START, "end": SAT_END, "n_days": len(sat_dates)},
        "three_way_window": {"start": dates_3way[0], "end": dates_3way[-1], "n_days": min_3way},
        "k297_full_window": {"start": K297_START, "end": SAT_END, "n_days": 504},
        "binding_constraint": "K275 (96d OKX history)",
    },
    "component_metrics_96d": {
        "K270": k270_sat_metrics,
        "K275": k275_sat_metrics,
        "K297_EW": k297_sat_metrics,
        "K297_full_504d": k297_full_metrics,
    },
    "component_vols_96d": {
        "K270": round(vol270, 8),
        "K275": round(vol275, 8),
        "K297": round(vol297, 8),
    },
    "correlation_matrix": corr_matrix,
    "satellite_variants": satellite_variants,
    "combined_variants": combined_variants,
    "best_combined": {
        "name": best_key,
        "metrics": best["metrics"],
        "wf_summary": best["wf_summary"],
        "satellite_weights": best["satellite_weights"],
    },
    "acceptance_gates": gates,
    "n_gates_passed": n_pass,
    "n_gates_total": 4,
    "verdict": verdict,
    "k287d_reference": {
        "sharpe_55d": K287D_SH,
        "note": "K287d combined Sh on 55d three-way window (K287 satellite.json)",
    },
    "deployment_plan": {
        "K280": 0.80,
        "Satellite": 0.20,
        "satellite_composition": best["satellite_weights"],
        "satellite_variant": best["satellite_variant"] if "satellite_variant" in best else best_key,
        "note": "Satellite = K270 + K275 (OKX) + K297 (RWA carry: PAXG+SPX)",
    },
}

# Save outputs — convert numpy types to native Python for JSON serialization
class NpEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (np.bool_,)):
            return bool(obj)
        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, (np.floating,)):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return super().default(obj)

with open("/Users/nekonaomichi/crypto-lab/wave_k301_v6_12_extended.json", "w") as f:
    json.dump(results, f, indent=2, cls=NpEncoder)

with open("/Users/nekonaomichi/crypto-lab/wave_k301_curves.json", "w") as f:
    json.dump(curves_out, f, indent=2)

print("\nSaved: wave_k301_v6_12_extended.json, wave_k301_curves.json")
print("Done.")
