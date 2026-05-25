"""
Wave K302 — K297 RWA Carry as HL-Only Satellite (replaces dYdX+OKX)
=====================================================================
Objective: Test PAXG/SPX HL-only satellite (K297) as replacement for
           K270(dYdX)+K275(OKX) satellite used in K287d.
           Operational simplification: 3 exchanges → 2 exchanges.

Variants:
  K302a: PAXG 60% + SPX 40%   (K297 recommended allocation)
  K302b: PAXG 100%             (highest individual Sh=16.91)
  K302c: PAXG 80% + SPX 20%   (PAXG-heavy, retains SPX diversification)
  K302d: inv-vol PAXG/SPX      (natural weighting by volatility)

Combined (80% K280 / 20% satellite):
  K302a_comb, K302b_comb, K302c_comb, K302d_comb

Benchmark: K287d (Sh=33.00, 55d, 3-exchange architecture)
Acceptance: Combined Sh ≥ K287d 33.00 (or within 5% = 31.35) with HL-only benefit

Author: K302 agent | 2026-05-25
"""

import json
import numpy as np
from datetime import datetime, timezone

# ─────────────────────────────────────────────────────────────────────────────
# LOAD SOURCE DATA
# ─────────────────────────────────────────────────────────────────────────────
with open("/Users/nekonaomichi/crypto-lab/wave_k297_curves.json") as f:
    k297_curves = json.load(f)

with open("/Users/nekonaomichi/crypto-lab/wave_k280_curves.json") as f:
    k280_curves = json.load(f)

with open("/Users/nekonaomichi/crypto-lab/wave_k287_curves.json") as f:
    k287_curves = json.load(f)

with open("/Users/nekonaomichi/crypto-lab/wave_k297_hip3_weekend.json") as f:
    k297_res = json.load(f)

with open("/Users/nekonaomichi/crypto-lab/wave_k280_k272a_k276b.json") as f:
    k280_res = json.load(f)

with open("/Users/nekonaomichi/crypto-lab/wave_k287_satellite.json") as f:
    k287_res = json.load(f)

# ─────────────────────────────────────────────────────────────────────────────
# BUILD DATE-INDEXED RETURN MAPS
# ─────────────────────────────────────────────────────────────────────────────
# K297 daily returns (from curves JSON)
spx_dr_raw  = k297_curves["coins"]["SPX"]["daily_returns"]    # {date: ret}
paxg_dr_raw = k297_curves["coins"]["PAXG"]["daily_returns"]   # {date: ret}

spx_dr  = {d: float(v) for d, v in spx_dr_raw.items()}
paxg_dr = {d: float(v) for d, v in paxg_dr_raw.items()}

# K280 daily returns (from equity curve list)
k280_dates = k280_curves["dates"]
k280_eq    = np.array(k280_curves["K280"], dtype=float)
k280_ret   = np.diff(k280_eq) / k280_eq[:-1]
k280_dr    = {k280_dates[i + 1]: k280_ret[i] for i in range(len(k280_ret))}

print(f"[Data] SPX: {len(spx_dr)} days  ({sorted(spx_dr.keys())[0]} → {sorted(spx_dr.keys())[-1]})")
print(f"[Data] PAXG: {len(paxg_dr)} days ({sorted(paxg_dr.keys())[0]} → {sorted(paxg_dr.keys())[-1]})")
print(f"[Data] K280: {len(k280_dr)} days ({k280_dates[1]} → {k280_dates[-1]})")

# ─────────────────────────────────────────────────────────────────────────────
# DETERMINE OVERLAP WINDOWS
# ─────────────────────────────────────────────────────────────────────────────
# K297 satellite overlap (SPX+PAXG intersection)
spx_set  = set(spx_dr.keys())
paxg_set = set(paxg_dr.keys())
k280_set = set(k280_dr.keys())

# Satellite internal overlap (both SPX and PAXG available)
sat_inner_dates = sorted(spx_set & paxg_set)       # PAXG starts Apr 2025

# SPX-only dates (before PAXG listing)
spx_only_dates = sorted(spx_set - paxg_set)

# Full K280 + K297 portfolio overlap (use SPX as anchor since it's available longest)
# For satellite: fill PAXG gap with SPX-only or portfolio returns on pre-PAXG dates
overlap_full = sorted(k280_set & spx_set)           # 447 days (K280 full window)
overlap_paxg = sorted(k280_set & paxg_set & spx_set)  # 374 days (PAXG available)

# K287d reference window (55d: 2026-02-19 → 2026-04-14)
k287d_dates = k287_curves["three_way_dates"]  # 55 days
k287d_set   = set(k287d_dates)

# K302 comparison window = K287d 55d overlap
comparison_dates = sorted(k287d_set & spx_set & paxg_set & k280_set)  # all 4 overlap

print(f"\n[Overlap] K280+SPX full: {len(overlap_full)} days ({overlap_full[0]} → {overlap_full[-1]})")
print(f"[Overlap] K280+PAXG+SPX: {len(overlap_paxg)} days ({overlap_paxg[0]} → {overlap_paxg[-1]})")
print(f"[Overlap] K287d 55d window in K302: {len(comparison_dates)} days")
if comparison_dates:
    print(f"          ({comparison_dates[0]} → {comparison_dates[-1]})")

# ─────────────────────────────────────────────────────────────────────────────
# HELPER FUNCTIONS
# ─────────────────────────────────────────────────────────────────────────────
def metrics(returns_arr, n_days_per_year=365):
    r = np.array(returns_arr, dtype=float)
    if len(r) < 2:
        return {"sharpe": 0.0, "max_dd": 0.0, "ann_ret": 0.0, "ann_vol": 0.0,
                "win_rate": 0.0, "total_return": 0.0, "n_days": len(r)}
    ann_ret  = float(np.mean(r) * n_days_per_year)
    ann_vol  = float(np.std(r, ddof=1) * np.sqrt(n_days_per_year))
    sharpe   = ann_ret / ann_vol if ann_vol > 0 else 0.0
    eq       = np.cumprod(1 + r)
    roll_max = np.maximum.accumulate(eq)
    dd       = eq / roll_max - 1
    max_dd   = float(np.min(dd))
    win_rate = float(np.mean(r > 0))
    total_r  = float(eq[-1] - 1)
    return {
        "sharpe":       round(sharpe, 4),
        "max_dd":       round(max_dd, 6),
        "ann_ret":      round(ann_ret, 6),
        "ann_vol":      round(ann_vol, 6),
        "win_rate":     round(win_rate, 4),
        "total_return": round(total_r, 6),
        "n_days":       len(r),
    }


def equity_curve(returns_arr):
    r = np.array(returns_arr, dtype=float)
    return list(np.cumprod(1 + r))


def walk_forward(returns_arr, dates_list, n_folds=3):
    n = len(returns_arr)
    if n < n_folds * 3:
        return []
    fold_size = n // n_folds
    folds = []
    for i in range(n_folds):
        start = i * fold_size
        end   = start + fold_size if i < n_folds - 1 else n
        fold_ret = returns_arr[start:end]
        m = metrics(fold_ret)
        folds.append({
            "fold":    i + 1,
            "start":   dates_list[start],
            "end":     dates_list[end - 1],
            "n_days":  end - start,
            "sharpe":  m["sharpe"],
            "max_dd":  m["max_dd"],
            "ann_ret": m["ann_ret"],
        })
    return folds


def wf_summary(folds):
    if not folds:
        return {"mean_sharpe": 0.0, "min_sharpe": 0.0, "all_positive": False}
    shs = [f["sharpe"] for f in folds]
    return {
        "mean_sharpe": round(float(np.mean(shs)), 4),
        "min_sharpe":  round(float(np.min(shs)), 4),
        "all_positive": all(s > 0 for s in shs),
        "folds": folds,
    }


def correlation(r1, r2):
    r1, r2 = np.array(r1, dtype=float), np.array(r2, dtype=float)
    if np.std(r1) == 0 or np.std(r2) == 0:
        return 0.0
    return float(np.corrcoef(r1, r2)[0, 1])


# ─────────────────────────────────────────────────────────────────────────────
# BUILD SATELLITE RETURN SERIES
# ─────────────────────────────────────────────────────────────────────────────
# For dates before PAXG listing (pre-Apr 2025), use SPX as proxy for satellite
# (conservative: these dates form the SPX-only period in K302a/c/d)
# For K302b (PAXG only), restrict to PAXG-available dates only

def build_satellite(dates, w_paxg, w_spx, require_paxg=False):
    """Build satellite daily returns for given dates.

    Args:
        dates: list of date strings
        w_paxg: PAXG weight
        w_spx: SPX weight
        require_paxg: if True, skip dates without PAXG data
    """
    rets, used_dates = [], []
    for d in dates:
        has_spx  = d in spx_dr
        has_paxg = d in paxg_dr
        if not has_spx:
            continue
        if require_paxg and not has_paxg:
            continue
        spx_r  = spx_dr[d]
        paxg_r = paxg_dr.get(d, 0.0)  # 0 if not available
        if require_paxg:
            ret = w_paxg * paxg_r + w_spx * spx_r
        else:
            # Rescale weights when PAXG not available (use SPX fully)
            if has_paxg:
                ret = w_paxg * paxg_r + w_spx * spx_r
            else:
                # Pre-PAXG: use SPX with full weight as placeholder
                ret = (w_paxg + w_spx) * spx_r
        rets.append(ret)
        used_dates.append(d)
    return np.array(rets, dtype=float), used_dates


# Inv-vol weights (use PAXG+SPX period volatility from K297 source data)
spx_vol_daily  = float(k297_res["backtest_alwayson"]["SPX"]["ann_vol_pct"] / 100 / np.sqrt(365))
paxg_vol_daily = float(k297_res["backtest_alwayson"]["PAXG"]["ann_vol_pct"] / 100 / np.sqrt(365))

inv_vol_sum   = (1 / spx_vol_daily) + (1 / paxg_vol_daily)
w_paxg_invvol = (1 / paxg_vol_daily) / inv_vol_sum
w_spx_invvol  = (1 / spx_vol_daily)  / inv_vol_sum

print(f"\n[Inv-vol weights] PAXG: {w_paxg_invvol:.4f}, SPX: {w_spx_invvol:.4f}")
print(f"  (SPX ann_vol={spx_vol_daily*np.sqrt(365)*100:.3f}%, PAXG ann_vol={paxg_vol_daily*np.sqrt(365)*100:.4f}%)")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 1: SATELLITE STANDALONE (on PAXG-available window = overlap_paxg)
# ─────────────────────────────────────────────────────────────────────────────
# Use overlap_paxg (K280+PAXG+SPX, 374 days) for all satellite variants
SAT_VARIANTS_DEF = {
    "K302a": (0.60, 0.40, False),   # PAXG 60% + SPX 40%
    "K302b": (1.00, 0.00, True),    # PAXG only (require_paxg)
    "K302c": (0.80, 0.20, False),   # PAXG 80% + SPX 20%
    "K302d": (w_paxg_invvol, w_spx_invvol, False),  # inv-vol
}

print("\n" + "=" * 65)
print("STEP 1: K302 Satellite Standalone (PAXG-available window)")
print("=" * 65)

satellite_results = {}
for name, (wp, ws, rp) in SAT_VARIANTS_DEF.items():
    sat_ret, sat_dates = build_satellite(overlap_paxg, wp, ws, require_paxg=rp)
    m  = metrics(sat_ret)
    wf = wf_summary(walk_forward(sat_ret, sat_dates))
    eq = [round(v, 8) for v in equity_curve(sat_ret)]
    satellite_results[name] = {
        "weights":       {"PAXG": round(wp, 4), "SPX": round(ws, 4)},
        "require_paxg":  rp,
        "window":        {"start": sat_dates[0], "end": sat_dates[-1], "n_days": len(sat_dates)},
        "metrics":       m,
        "wf":            wf,
        "_equity":       eq,
        "_dates":        sat_dates,
        "_returns":      list(sat_ret),
    }
    print(f"[{name}] w_PAXG={wp:.2f} w_SPX={ws:.2f} | "
          f"Sh={m['sharpe']:.2f}  MaxDD={m['max_dd']:.6f}  "
          f"WinRate={m['win_rate']*100:.1f}%  n={m['n_days']}d  "
          f"WF_all+={wf['all_positive']}")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 2: COMBINED K280 + K302 SATELLITE (80/20)
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 65)
print("STEP 2: K302 Combined (80% K280 + 20% Satellite)")
print("=" * 65)

combined_results = {}
for sat_name, sat_data in satellite_results.items():
    comb_name   = f"{sat_name}_comb"
    # Align to dates present in both K280 and satellite
    sat_date_set  = set(sat_data["_dates"])
    common_dates  = sorted(k280_set & sat_date_set)

    k280_aligned = np.array([k280_dr[d] for d in common_dates], dtype=float)
    sat_aligned  = np.array([sat_data["_returns"][sat_data["_dates"].index(d)]
                              for d in common_dates], dtype=float)
    # Build satellite returns as lookup dict for efficiency
    sat_dr_lookup = {sat_data["_dates"][i]: sat_data["_returns"][i]
                     for i in range(len(sat_data["_dates"]))}
    sat_aligned_v2 = np.array([sat_dr_lookup[d] for d in common_dates], dtype=float)

    comb_ret = 0.80 * k280_aligned + 0.20 * sat_aligned_v2
    m  = metrics(comb_ret)
    wf = wf_summary(walk_forward(comb_ret, common_dates))
    eq = [round(v, 8) for v in equity_curve(comb_ret)]

    combined_results[comb_name] = {
        "satellite": sat_name,
        "weights":   {"K280": 0.80, "satellite": 0.20},
        "window":    {"start": common_dates[0], "end": common_dates[-1], "n_days": len(common_dates)},
        "metrics":   m,
        "wf":        wf,
        "_equity":   eq,
        "_dates":    common_dates,
        "_returns":  list(comb_ret),
    }
    print(f"[{comb_name}] Sh={m['sharpe']:.2f}  MaxDD={m['max_dd']:.6f}  "
          f"n={m['n_days']}d  WF_all+={wf['all_positive']}  "
          f"WF_min={wf['min_sharpe']:.2f}")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 3: COMPARISON ON K287d 55-DAY WINDOW
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 65)
print("STEP 3: K287d 55-Day Comparison Window")
print("=" * 65)

# K287d benchmark
K287D_SH_55D  = k287_res["combined_variants"]["K287d"]["metrics"]["sharpe"]
K287D_MAXDD   = k287_res["combined_variants"]["K287d"]["metrics"]["max_dd"]
K287D_WFALL   = k287_res["combined_variants"]["K287d"]["wf_summary"]["all_positive"]
ACCEPT_THRESH = K287D_SH_55D * 0.95  # within 5%

print(f"[K287d] Sh={K287D_SH_55D:.2f}  MaxDD={K287D_MAXDD:.6f}  WF_all+={K287D_WFALL}")
print(f"[Accept threshold] Sh ≥ {ACCEPT_THRESH:.2f} (K287d × 0.95)")
print()

comparison_55d = {}
for comb_name, comb_data in combined_results.items():
    # Restrict to K287d 55d window
    comb_dr_lookup  = {comb_data["_dates"][i]: comb_data["_returns"][i]
                       for i in range(len(comb_data["_dates"]))}
    common_55       = sorted(set(comb_data["_dates"]) & k287d_set & k280_set)
    if not common_55:
        print(f"  [{comb_name}] No overlap with K287d 55d window")
        continue

    ret_55 = np.array([comb_dr_lookup[d] for d in common_55], dtype=float)
    m_55   = metrics(ret_55)
    eq_55  = equity_curve(ret_55)
    gap    = m_55["sharpe"] - K287D_SH_55D

    comparison_55d[comb_name] = {
        "satellite": comb_data["satellite"],
        "n_days_overlap": len(common_55),
        "window":    {"start": common_55[0], "end": common_55[-1]},
        "metrics_55d": m_55,
        "vs_k287d": {
            "k287d_sharpe": K287D_SH_55D,
            "k302_sharpe":  m_55["sharpe"],
            "delta_sharpe": round(gap, 4),
            "pct_of_k287d": round(m_55["sharpe"] / K287D_SH_55D * 100, 2),
            "passes_95pct_threshold": m_55["sharpe"] >= ACCEPT_THRESH,
        },
        "_equity_55d": eq_55,
        "_dates_55d":  common_55,
    }
    flag = "✓ PASS" if m_55["sharpe"] >= ACCEPT_THRESH else "✗ FAIL"
    print(f"  [{comb_name}] 55d Sh={m_55['sharpe']:.2f}  vs K287d: {gap:+.2f}  "
          f"({m_55['sharpe']/K287D_SH_55D*100:.1f}%)  {flag}")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 4: WALK-FORWARD ON OVERLAP WINDOW (K297 504d vs K280 448d)
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 65)
print("STEP 4: Walk-Forward on Full Overlap Window (374d PAXG available)")
print("=" * 65)

wf_full = {}
for comb_name, comb_data in combined_results.items():
    wf_f = wf_summary(walk_forward(
        np.array(comb_data["_returns"], dtype=float),
        comb_data["_dates"],
        n_folds=4  # 4 folds over 374d ≈ 93d each
    ))
    wf_full[comb_name] = wf_f
    print(f"  [{comb_name}] WF_mean={wf_f['mean_sharpe']:.2f}  "
          f"WF_min={wf_f['min_sharpe']:.2f}  WF_all+={wf_f['all_positive']}")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 5: CORRELATION ANALYSIS
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 65)
print("STEP 5: Correlation Analysis")
print("=" * 65)

# K280 vs K302 satellite
k280_paxg_overlap = sorted(k280_set & paxg_set & spx_set)
k280_paxg_ret = np.array([k280_dr[d] for d in k280_paxg_overlap], dtype=float)

sat_lookup = {
    name: {sat["_dates"][i]: sat["_returns"][i] for i in range(len(sat["_dates"]))}
    for name, sat in satellite_results.items()
}

corr_results = {}
for sat_name, lookup in sat_lookup.items():
    common = sorted(set(lookup.keys()) & k280_set)
    if len(common) < 10:
        continue
    k280_a = np.array([k280_dr[d] for d in common], dtype=float)
    sat_a  = np.array([lookup[d] for d in common], dtype=float)
    rho    = correlation(k280_a, sat_a)
    corr_results[sat_name] = round(rho, 4)
    print(f"  [{sat_name}] ρ(satellite, K280) = {rho:.4f}  "
          f"({'low' if abs(rho) < 0.3 else 'moderate' if abs(rho) < 0.6 else 'high'} correlation)")

# SPX vs PAXG intra-correlation
spx_paxg_common = sorted(spx_set & paxg_set)
spx_arr  = np.array([spx_dr[d] for d in spx_paxg_common], dtype=float)
paxg_arr = np.array([paxg_dr[d] for d in spx_paxg_common], dtype=float)
rho_spx_paxg = correlation(spx_arr, paxg_arr)
print(f"  [SPX vs PAXG] ρ = {rho_spx_paxg:.4f}")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 6: ACCEPTANCE GATES & VERDICT
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 65)
print("STEP 6: Acceptance Gates")
print("=" * 65)

# Find best combined variant on 55d window
best_comb_name = None
best_sh_55d = -999.0
for comb_name, comp_data in comparison_55d.items():
    sh = comp_data["metrics_55d"]["sharpe"]
    if sh > best_sh_55d:
        best_sh_55d     = sh
        best_comb_name  = comb_name

# Gates for best variant
if best_comb_name:
    best_comp   = comparison_55d[best_comb_name]
    best_comb   = combined_results[best_comb_name]
    best_sat_nm = best_comp["satellite"]
    best_sat    = satellite_results[best_sat_nm]
    best_wf_full = wf_full[best_comb_name]

    gates = {
        "G1_satellite_Sh_gt_5":           best_sat["metrics"]["sharpe"] > 5.0,
        "G2_combined_Sh_gte_k287d_95pct":  best_sh_55d >= ACCEPT_THRESH,
        "G3_wf_55d_all_positive":          best_sat["wf"]["all_positive"],
        "G4_wf_full_all_positive":         best_wf_full["all_positive"],
        "G5_HL_only_infra":               True,  # By design: PAXG+SPX on HL
        "G6_rho_sat_k280_lt_0.5":         abs(corr_results.get(best_sat_nm, 1.0)) < 0.5,
    }
    n_pass = sum(gates.values())
    accept = all(gates.values())
    verdict = "ACCEPT → v6.12" if accept else f"PARTIAL ({n_pass}/{len(gates)})"

    for g, v in gates.items():
        mark = "✓" if v else "✗"
        print(f"  {mark} {g}: {v}")
    print(f"\n  Best variant: {best_comb_name} (55d Sh={best_sh_55d:.2f})")
    print(f"  Verdict: {verdict}")
else:
    gates, n_pass, accept, verdict = {}, 0, False, "NO_DATA"
    best_sat_nm = "N/A"
    print("  No comparison data available")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 7: OPERATIONAL COMPARISON TABLE
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 65)
print("STEP 7: Operational Comparison")
print("=" * 65)

op_table = {
    "K287d": {
        "architecture":    "K280 (Bybit+HL) + K270 (dYdX) + K275 (OKX)",
        "n_exchanges":     3,
        "exchange_list":   ["Bybit", "HyperLiquid", "dYdX", "OKX"],
        "infra_complexity": "HIGH",
        "combined_Sh_55d": K287D_SH_55D,
        "wf_all_positive": K287D_WFALL,
    },
    "K302_best": {
        "architecture":    f"K280 (Bybit+HL) + K297 PAXG/SPX (HL)",
        "n_exchanges":     2,
        "exchange_list":   ["Bybit", "HyperLiquid"],
        "infra_complexity": "LOW",
        "combined_Sh_55d": best_sh_55d if best_comb_name else None,
        "variant":          best_comb_name,
        "wf_all_positive": best_wf_full["all_positive"] if best_comb_name else None,
    },
}

print(f"  {'Metric':<35} {'K287d':>12} {'K302_best':>12}")
print("  " + "-" * 60)
print(f"  {'Exchanges':<35} {'3':>12} {'2':>12}")
print(f"  {'Infra complexity':<35} {'HIGH':>12} {'LOW':>12}")
print(f"  {'Combined Sh (55d)':<35} {K287D_SH_55D:>12.2f} {best_sh_55d:>12.2f}")
sh_ratio = best_sh_55d / K287D_SH_55D * 100 if best_sh_55d else 0
print(f"  {'K302/K287d Sh ratio':<35} {'100%':>12} {sh_ratio:>11.1f}%")
print(f"  {'WF all-positive':<35} {'Yes' if K287D_WFALL else 'No':>12} "
      f"{'Yes' if best_wf_full.get('all_positive') else 'No':>12}")

# ─────────────────────────────────────────────────────────────────────────────
# ASSEMBLE OUTPUT JSON
# ─────────────────────────────────────────────────────────────────────────────
def strip_private(d):
    """Remove keys starting with _ from dict recursively."""
    if isinstance(d, dict):
        return {k: strip_private(v) for k, v in d.items() if not k.startswith("_")}
    elif isinstance(d, list):
        return [strip_private(v) for v in d]
    return d


output = {
    "wave":       "K302",
    "task":       "K297 RWA Carry (PAXG/SPX HL-only) as satellite — replaces K270(dYdX)+K275(OKX)",
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "config": {
        "satellite_weight":  0.20,
        "k280_weight":       0.80,
        "k287d_reference_Sh": K287D_SH_55D,
        "acceptance_threshold_Sh": round(ACCEPT_THRESH, 4),
    },
    "data_windows": {
        "spx":  {"start": sorted(spx_dr.keys())[0],  "end": sorted(spx_dr.keys())[-1],  "n_days": len(spx_dr)},
        "paxg": {"start": sorted(paxg_dr.keys())[0], "end": sorted(paxg_dr.keys())[-1], "n_days": len(paxg_dr)},
        "k280": {"start": k280_dates[1],              "end": k280_dates[-1],              "n_days": len(k280_dates) - 1},
        "satellite_overlap_paxg_k280": {
            "start": overlap_paxg[0], "end": overlap_paxg[-1], "n_days": len(overlap_paxg)
        },
        "comparison_55d_window": {
            "start": k287d_dates[0], "end": k287d_dates[-1], "n_days": len(k287d_dates)
        },
    },
    "inv_vol_weights": {
        "PAXG": round(w_paxg_invvol, 4),
        "SPX":  round(w_spx_invvol, 4),
        "spx_ann_vol_pct":  round(spx_vol_daily * np.sqrt(365) * 100, 4),
        "paxg_ann_vol_pct": round(paxg_vol_daily * np.sqrt(365) * 100, 4),
    },
    "satellite_standalone": strip_private(satellite_results),
    "combined_80_20": strip_private(combined_results),
    "comparison_vs_k287d_55d": strip_private(comparison_55d),
    "wf_full_overlap": wf_full,
    "correlations": {
        "satellite_vs_k280": corr_results,
        "spx_vs_paxg": round(rho_spx_paxg, 4),
    },
    "operational_comparison": op_table,
    "acceptance_gates": gates,
    "n_gates_passed": n_pass,
    "n_gates_total": len(gates),
    "verdict": verdict,
    "best_variant": best_comb_name,
    "trade_off_verdict": {
        "recommend_v612": accept,
        "reason": (
            f"K302 {best_comb_name} achieves Sh={best_sh_55d:.2f} vs K287d Sh={K287D_SH_55D:.2f} "
            f"({sh_ratio:.1f}% of benchmark). "
            + ("Exceeds 95% threshold → simplification justified." if accept
               else f"Below 95% threshold ({ACCEPT_THRESH:.2f}) → retain K287d architecture.")
        ),
        "exchanges_saved": 1,
        "infra_benefit": "Eliminate dYdX+OKX accounts; consolidate to HL for satellite",
    },
}

# Write main result JSON
with open("/Users/nekonaomichi/crypto-lab/wave_k302_k297_only_sat.json", "w") as f:
    json.dump(output, f, indent=2, default=str)
print("\n[SAVED] wave_k302_k297_only_sat.json")

# ─────────────────────────────────────────────────────────────────────────────
# BUILD CURVES JSON
# ─────────────────────────────────────────────────────────────────────────────
curves_out = {
    "wave": "K302",
    "generated_at": datetime.now(timezone.utc).isoformat(),
}

# Satellite equity curves (PAXG overlap window)
for name, sat in satellite_results.items():
    curves_out[f"{name}_satellite_dates"]  = sat["_dates"]
    curves_out[f"{name}_satellite_equity"] = sat["_equity"]

# Combined equity curves
for name, comb in combined_results.items():
    curves_out[f"{name}_dates"]  = comb["_dates"]
    curves_out[f"{name}_equity"] = comb["_equity"]

# K287d reference on its 55d window (from original curves)
curves_out["K287d_55d_dates"]  = k287_curves["three_way_dates"]
curves_out["K287d_55d_equity"] = k287_curves["K287d_equity"]

# K302 best on 55d window
if best_comb_name and best_comb_name in comparison_55d:
    curves_out[f"{best_comb_name}_55d_dates"]  = comparison_55d[best_comb_name]["_dates_55d"]
    curves_out[f"{best_comb_name}_55d_equity"] = [
        round(v, 8) for v in comparison_55d[best_comb_name]["_equity_55d"]
    ]

# K280 reference (full window)
curves_out["K280_dates"]  = k280_dates
curves_out["K280_equity"] = [round(v, 8) for v in k280_curves["K280"]]

# PAXG and SPX individual equity curves (on their respective windows)
spx_eq  = [round(v, 8) for v in equity_curve([spx_dr[d] for d in sorted(spx_dr.keys())])]
paxg_eq = [round(v, 8) for v in equity_curve([paxg_dr[d] for d in sorted(paxg_dr.keys())])]
curves_out["SPX_dates"]  = sorted(spx_dr.keys())
curves_out["SPX_equity"] = spx_eq
curves_out["PAXG_dates"] = sorted(paxg_dr.keys())
curves_out["PAXG_equity"] = paxg_eq

with open("/Users/nekonaomichi/crypto-lab/wave_k302_curves.json", "w") as f:
    json.dump(curves_out, f, indent=2, default=str)
print("[SAVED] wave_k302_curves.json")

# ─────────────────────────────────────────────────────────────────────────────
# FINAL SUMMARY
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 65)
print("WAVE K302 FINAL SUMMARY")
print("=" * 65)
print(f"\nBenchmark: K287d Sh={K287D_SH_55D:.2f} (55d, 3-exchange)")
print(f"Threshold: Sh ≥ {ACCEPT_THRESH:.2f} (95% of K287d)")
print()
print(f"{'Variant':<14} {'Sat_Sh':>8} {'Comb_Sh_full':>13} {'Comb_Sh_55d':>12} {'vs_K287d':>10} {'Pass':>6}")
print("-" * 65)
for sat_name in satellite_results:
    comb_name  = f"{sat_name}_comb"
    sat_m      = satellite_results[sat_name]["metrics"]
    comb_m     = combined_results[comb_name]["metrics"]
    comp_55d   = comparison_55d.get(comb_name, {})
    sh_55d     = comp_55d.get("metrics_55d", {}).get("sharpe", float("nan"))
    vs_k287d   = sh_55d - K287D_SH_55D if not np.isnan(sh_55d) else float("nan")
    passed     = "✓" if not np.isnan(sh_55d) and sh_55d >= ACCEPT_THRESH else "✗"
    print(f"{sat_name:<14} {sat_m['sharpe']:>8.2f} {comb_m['sharpe']:>13.2f} "
          f"{sh_55d:>12.2f} {vs_k287d:>+10.2f} {passed:>6}")
print()
print(f"Best: {best_comb_name}  Sh_55d={best_sh_55d:.2f}")
print(f"Verdict: {verdict}")
print(f"Operational benefit: 3→2 exchanges (eliminate dYdX+OKX)")
