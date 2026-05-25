"""
Wave K281: K272a Upgrade — K265 → K276c_excl_bot5 (K198+K208+K276c 3-way)
Replace K265 in K272a with K276c_excl_bot5 (30 symbols, only worst 5 dropped).

K276c_excl_bot5 standalone: Full Sh=24.03, WF min=20.90 (BEST K276 variant)
K272a v6.10.1 reference: OOS Sh=16.13, WF min=9.92, MaxDD=-0.000036
Acceptance: OOS Sh > 16.33 (+0.20), WF min >= 9.92, MaxDD <= -0.000036, all weights non-zero

Comparison waves:
  K278: K272a + K276a_top15 (15 sym) → OOS Sh=16.22, WF min=11.23 → REJECTED
  K280: K272a + K276b_top20 (20 sym) → running
  K281: K272a + K276c_excl_bot5 (30 sym) ← THIS WAVE
"""

import json
import numpy as np
from datetime import datetime
import time

START = time.time()

# ─── Load curves ──────────────────────────────────────────────────────────────
with open("/Users/nekonaomichi/crypto-lab/wave_k246_curves.json") as f:
    d246 = json.load(f)

with open("/Users/nekonaomichi/crypto-lab/wave_k276_curves.json") as f:
    d276 = json.load(f)

with open("/Users/nekonaomichi/crypto-lab/wave_k272_curves.json") as f:
    d272c = json.load(f)

# ─── Window: K272a ML window (2025-01-22 → 2026-04-14, 448 days) ─────────────
WIN_DATES = d246["dates"]
WIN_START = WIN_DATES[0]
WIN_END   = WIN_DATES[-1]
N_WIN     = len(WIN_DATES)   # 448
print(f"Window: {WIN_START} → {WIN_END}  ({N_WIN} days)")

# ─── Equity → log-return PnL ──────────────────────────────────────────────────
def eq_to_pnl(eq):
    r = np.diff(np.log(np.array(eq)))
    return np.concatenate([[0.0], r])

# K198, K208 on window (already aligned to 448-day window)
eq_k198 = np.array(d246["K198"])
eq_k208 = np.array(d246["K208"])
pnl_k198 = eq_to_pnl(eq_k198)
pnl_k208 = eq_to_pnl(eq_k208)

# K276c_excl_bot5: slice to K272a ML window
k276c_data   = d276["K276c_excl_bot5"]
k276c_dates  = k276c_data["dates"]
k276c_equity = np.array(k276c_data["equity"])
k276c_pnl_full = eq_to_pnl(k276c_equity)
k276c_idx = {d: i for i, d in enumerate(k276c_dates)}

missing_k276c = [d for d in WIN_DATES if d not in k276c_idx]
if missing_k276c:
    print(f"WARNING: {len(missing_k276c)} dates missing from K276c_excl_bot5")

win_k276c_slots = [k276c_idx[d] for d in WIN_DATES if d in k276c_idx]
pnl_k276c_win   = np.array([k276c_pnl_full[i] for i in win_k276c_slots])
eq_k276c_win    = np.exp(np.cumsum(pnl_k276c_win))
eq_k276c_win    = eq_k276c_win / eq_k276c_win[0]
print(f"K276c_excl_bot5 window slice: {len(pnl_k276c_win)} days (expected 448)")

# ─── Statistics helpers ───────────────────────────────────────────────────────
def sharpe(pnl, ann=252):
    pnl = np.array(pnl)
    mu  = np.mean(pnl) * ann
    sd  = np.std(pnl, ddof=1) * np.sqrt(ann)
    return float(mu / sd) if sd > 1e-12 else 0.0

def maxdd(eq):
    eq = np.array(eq)
    rm = np.maximum.accumulate(eq)
    return float(np.min((eq - rm) / rm))

def ann_ret(eq, ann=252):
    eq = np.array(eq)
    total = eq[-1] / eq[0] - 1
    return float((1 + total) ** (ann / len(eq)) - 1)

def ann_vol(pnl, ann=252):
    return float(np.std(np.array(pnl), ddof=1) * np.sqrt(ann))

def metrics(pnl_arr):
    pnl = np.array(pnl_arr)
    eq  = np.exp(np.cumsum(pnl))
    eq  = eq / eq[0]
    return {
        "sharpe":   round(sharpe(pnl), 4),
        "max_dd":   round(maxdd(eq), 6),
        "ann_ret":  round(ann_ret(eq), 6),
        "ann_vol":  round(ann_vol(pnl), 6),
        "win_rate": round(float(np.mean(pnl > 0)), 6),
        "n_days":   int(len(pnl)),
    }

# ─── K276c ML-window standalone validation (PRIMARY HEADER) ───────────────────
k276c_win_m = metrics(pnl_k276c_win)
print(f"\n=== K276c_excl_bot5 on K272a ML window (PRIMARY CHECK) ===")
print(f"  Sh={k276c_win_m['sharpe']:.4f}  MDD={k276c_win_m['max_dd']:.6f}  "
      f"AnnRet={k276c_win_m['ann_ret']:.4f}  AnnVol={k276c_win_m['ann_vol']:.4f}")

# Compare vs K265 on same window
pnl_k265_win_ref = eq_to_pnl(np.array(d272c["K265_win"]))
k265_win_m = metrics(pnl_k265_win_ref)
print(f"  K265 on same window: Sh={k265_win_m['sharpe']:.4f}  MDD={k265_win_m['max_dd']:.6f}")
print(f"  K276c vs K265 delta: dSh={k276c_win_m['sharpe']-k265_win_m['sharpe']:+.4f}")

# K276c standalone full-period metrics (from K276 decompose — 733 days)
K276C_FULL_SH  = 24.0246
K276C_WF_MIN   = 20.8994
print(f"  K276c standalone (full period): Sh={K276C_FULL_SH}  WF_min={K276C_WF_MIN}")

# ─── 3-way components: K198, K208, K276c ─────────────────────────────────────
LABELS_3 = ["K198", "K208", "K276c"]
pnls_3   = [pnl_k198, pnl_k208, pnl_k276c_win]

# ─── K276c symbols (30 symbols, excl ARK/BLUR/STRK/ARB/SUSHI) ────────────────
K276C_SYMBOLS = [
    "AAVE", "ATOM", "AVAX", "BNB", "BONK", "BTC", "CRV", "DOGE", "DOT", "ETH",
    "FET", "INJ", "LDO", "MKR", "NEAR", "PEPE", "RNDR", "SHIB", "TAO", "UNI",
    "WIF", "TIA", "JUP", "BOME", "ENA", "PYTH", "MEME", "WLD", "SEI", "ONDO"
]
K276C_DROPPED = ["ARK", "BLUR", "STRK", "ARB", "SUSHI"]

# ─── Allocator ────────────────────────────────────────────────────────────────
def inv_vol_weights(pnl_list, caps=None):
    """Inverse-vol weights with optional per-index caps (iterative)."""
    vols = np.array([np.std(p, ddof=1) for p in pnl_list])
    vols = np.where(vols < 1e-12, 1e-12, vols)
    w = 1.0 / vols
    w = w / w.sum()
    if caps:
        for _ in range(100):
            changed = False
            for idx, cap in caps.items():
                if w[idx] > cap:
                    excess = w[idx] - cap
                    w[idx] = cap
                    others = [k for k in range(len(w)) if k != idx]
                    ow = w[others]
                    if ow.sum() > 1e-12:
                        w[others] += excess * ow / ow.sum()
                    changed = True
            if not changed:
                break
    return w / w.sum()

def portfolio_pnl_fixed(pnls, weights):
    return sum(w * np.array(p) for w, p in zip(weights, pnls))

# ─── K272a acceptance thresholds ──────────────────────────────────────────────
K272A_OOS_SH  = 16.13
K272A_WF_MIN  = 9.92
K272A_WF_MEAN = 13.04
K272A_MAX_DD  = -0.000036
K281_SH_MIN   = K272A_OOS_SH + 0.20   # 16.33

OOS_DAYS = 135
N_FOLDS  = 4

print(f"\nK272a v6.10.1 reference: OOS_Sh={K272A_OOS_SH}  WF_min={K272A_WF_MIN}  MaxDD={K272A_MAX_DD}")
print(f"K281 acceptance: OOS_Sh >= {K281_SH_MIN}  WF_min >= {K272A_WF_MIN}  MaxDD >= {K272A_MAX_DD}")

# ─── 3x3 Correlation matrix ───────────────────────────────────────────────────
print(f"\n=== 3x3 Correlation matrix ({'/'.join(LABELS_3)}) ===")
corr_3 = {}
for i, si in enumerate(LABELS_3):
    corr_3[si] = {}
    for j, sj in enumerate(LABELS_3):
        c = float(np.corrcoef(pnls_3[i], pnls_3[j])[0, 1])
        corr_3[si][sj] = round(c, 4)
    print(f"  {si}: " + "  ".join(f"{LABELS_3[j]}={corr_3[si][LABELS_3[j]]:+.4f}" for j in range(3)))

# ─── Walk-forward 4-fold ──────────────────────────────────────────────────────
print(f"\n=== Walk-forward 4-fold (K281: K198+K208+K276c_excl_bot5) ===")
fold_size = N_WIN // N_FOLDS
fold_list = []

for fi in range(N_FOLDS):
    s = fi * fold_size
    e = (fi + 1) * fold_size if fi < N_FOLDS - 1 else N_WIN

    # OOS: this fold
    pnl_oos_fold = [p[s:e] for p in pnls_3]

    # IS: everything except this fold
    is_mask = list(range(0, s)) + list(range(e, N_WIN))
    pnl_is  = [p[is_mask] for p in pnls_3]

    w_fold   = inv_vol_weights(pnl_is, caps=None)   # K272a methodology: no caps
    pnl_port = portfolio_pnl_fixed(pnl_oos_fold, w_fold)

    fm = metrics(pnl_port)
    fm["fold"]       = fi + 1
    fm["start_date"] = WIN_DATES[s]
    fm["end_date"]   = WIN_DATES[e - 1]
    fm["weights"]    = {LABELS_3[i]: round(float(w_fold[i]), 4) for i in range(3)}
    fold_list.append(fm)

    w_str = " ".join(f"{LABELS_3[i]}={w_fold[i]:.3f}" for i in range(3))
    print(f"  Fold {fi+1} [{WIN_DATES[s]}→{WIN_DATES[e-1]}]: "
          f"Sh={fm['sharpe']:.4f}  MDD={fm['max_dd']:.6f}  [{w_str}]")

fold_sharpes = [f["sharpe"] for f in fold_list]
wf_mean = float(np.mean(fold_sharpes))
wf_min  = float(np.min(fold_sharpes))
wf_all_pos = bool(all(s > 0 for s in fold_sharpes))
print(f"  WF mean={wf_mean:.4f}  WF min={wf_min:.4f}  All positive: {wf_all_pos}")

# ─── Pseudo-OOS (last 135 days) ───────────────────────────────────────────────
oos_s        = N_WIN - OOS_DAYS
pnl_is_o     = [p[:oos_s] for p in pnls_3]
w_oos        = inv_vol_weights(pnl_is_o, caps=None)
pnl_oos_port = portfolio_pnl_fixed([p[oos_s:] for p in pnls_3], w_oos)
oos_m        = metrics(pnl_oos_port)
oos_sh       = oos_m["sharpe"]
oos_mdd      = oos_m["max_dd"]

w_str_oos = " ".join(f"{LABELS_3[i]}={w_oos[i]:.3f}" for i in range(3))
print(f"\n=== Pseudo-OOS (last {OOS_DAYS}d, IS trained on {oos_s}d) ===")
print(f"  OOS Sh={oos_sh:.4f}  OOS MDD={oos_mdd:.6f}  [{w_str_oos}]")

# ─── Acceptance gates ─────────────────────────────────────────────────────────
all_weights_nonzero = bool(all(float(w_oos[i]) > 1e-6 for i in range(3)))
g1_oos_sh  = bool(oos_sh  >= K281_SH_MIN)
g2_wf_min  = bool(wf_min  >= K272A_WF_MIN)
g3_maxdd   = bool(oos_mdd >= K272A_MAX_DD)
g4_nonzero = all_weights_nonzero
accept     = g1_oos_sh and g2_wf_min and g3_maxdd and g4_nonzero

print(f"\n=== Acceptance gates vs K272a v6.10.1 ===")
print(f"  G1 OOS_Sh >= {K281_SH_MIN}: {oos_sh:.4f}  → {'PASS' if g1_oos_sh else 'FAIL'}")
print(f"  G2 WF_min >= {K272A_WF_MIN}: {wf_min:.4f}  → {'PASS' if g2_wf_min else 'FAIL'}")
print(f"  G3 MaxDD  >= {K272A_MAX_DD}: {oos_mdd:.6f}  → {'PASS' if g3_maxdd else 'FAIL'}")
print(f"  G4 All weights non-zero: {all_weights_nonzero}  → {'PASS' if g4_nonzero else 'FAIL'}")
print(f"  VERDICT: {'ACCEPT → K281 v6.10.3' if accept else 'REJECT — K272a v6.10.1 remains production'}")

# ─── Comparison table ─────────────────────────────────────────────────────────
print(f"\n=== K281 vs K278 vs K272a comparison ===")
print(f"  {'Version':<30} {'OOS Sh':>8} {'WF mean':>8} {'WF min':>8} {'MaxDD':>12} {'Verdict':>10}")
print(f"  {'K272a v6.10.1 (K265, 35sym)':<30} {K272A_OOS_SH:>8.2f} {K272A_WF_MEAN:>8.2f} {K272A_WF_MIN:>8.2f} {K272A_MAX_DD:>12.6f} {'PROD':>10}")
print(f"  {'K278 (K276a_top15, 15sym)':<30} {'16.2218':>8} {'13.9213':>8} {'11.2298':>8} {'-0.000036':>12} {'REJECT':>10}")
print(f"  {'K281 (K276c_excl_bot5, 30sym)':<30} {oos_sh:>8.4f} {wf_mean:>8.4f} {wf_min:>8.4f} {oos_mdd:>12.6f} {'ACCEPT' if accept else 'REJECT':>10}")
delta_sh = oos_sh - K272A_OOS_SH
print(f"  Delta K281 vs K272a: dOOS_Sh={delta_sh:+.4f}  dWF_min={wf_min-K272A_WF_MIN:+.4f}")

# ─── Verdict on best K265 variant for K272a ───────────────────────────────────
print(f"\n=== Verdict on best K265 variant for K272a ===")
print(f"  K276a_top15 (15 sym): OOS Sh=16.22, WF min=11.23 → dSh=+0.09 vs K272a → REJECT (below +0.20 threshold)")
print(f"  K276b_top20 (20 sym): K280 running → results pending")
print(f"  K276c_excl_bot5 (30 sym): OOS Sh={oos_sh:.2f}, WF min={wf_min:.2f} → dSh={delta_sh:+.2f} → {'ACCEPT' if accept else 'REJECT'}")
if accept:
    print(f"  RECOMMENDATION: Promote K281 (K276c_excl_bot5) as K272a v6.10.3 production")
    print(f"  K276c is the optimal K265 replacement — max symbols (30) retains diversity while removing only clear drag")
else:
    print(f"  RECOMMENDATION: K272a v6.10.1 (K265) remains production")
    print(f"  Among tested K276 variants, K276c is closest but all fail ensemble promotion threshold")

# ─── Equity curves ────────────────────────────────────────────────────────────
w_full = inv_vol_weights(pnls_3, caps=None)
pnl_k281_port = portfolio_pnl_fixed(pnls_3, w_full)
eq_k281 = np.exp(np.cumsum(pnl_k281_port))
eq_k281 = eq_k281 / eq_k281[0]

# K272a best overlay
eq_k272a = np.array(d272c["K272_best"])

# ─── Save curves ──────────────────────────────────────────────────────────────
runtime = round(time.time() - START, 2)

curves = {
    "wave":   "K281",
    "dates":  WIN_DATES,
    "K198":   [round(float(x), 8) for x in eq_k198.tolist()],
    "K208":   [round(float(x), 8) for x in eq_k208.tolist()],
    "K276c_win": [round(float(x), 8) for x in eq_k276c_win.tolist()],
    "K281":   [round(float(x), 8) for x in eq_k281.tolist()],
    "K272a_ref": [round(float(x), 8) for x in eq_k272a.tolist()],
    "full_weights": {LABELS_3[i]: round(float(w_full[i]), 4) for i in range(3)},
    "oos_weights":  {LABELS_3[i]: round(float(w_oos[i]), 4) for i in range(3)},
}
with open("/Users/nekonaomichi/crypto-lab/wave_k281_curves.json", "w") as f:
    json.dump(curves, f, indent=2)
print("\nSaved: wave_k281_curves.json")

# ─── Save metrics JSON ────────────────────────────────────────────────────────
class NpEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.bool_):    return bool(obj)
        if isinstance(obj, np.integer):  return int(obj)
        if isinstance(obj, np.floating): return float(obj)
        return super().default(obj)

results = {
    "wave":    "K281",
    "task":    "K272a Upgrade: K265 → K276c_excl_bot5 (K198+K208+K276c 3-way)",
    "as_of":   datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
    "runtime_s": runtime,

    "data_info": {
        "n_days":    N_WIN,
        "date_start": WIN_START,
        "date_end":   WIN_END,
        "components": LABELS_3,
        "k276c_n_symbols": 30,
        "k276c_symbols":   K276C_SYMBOLS,
        "k276c_dropped":   K276C_DROPPED,
        "k276c_note":      "excl worst-5 (ARK/BLUR/STRK/ARB/SUSHI) from K265's 35 symbols",
        "oos_days":   OOS_DAYS,
        "n_folds":    N_FOLDS,
    },

    "k276c_ml_window_standalone": {
        "note": "K276c_excl_bot5 on K272a ML window (2025-01-22 → 2026-04-14) — PRIMARY CHECK",
        "metrics": k276c_win_m,
        "k265_on_same_window": k265_win_m,
        "delta_sharpe_vs_k265": round(k276c_win_m["sharpe"] - k265_win_m["sharpe"], 4),
        "k276c_full_period_sh": K276C_FULL_SH,
        "k276c_full_period_wf_min": K276C_WF_MIN,
    },

    "correlation_matrix_3x3": corr_3,

    "k272a_production_ref": {
        "version":    "v6.10.1",
        "components": ["K198", "K208", "K265"],
        "oos_sharpe": K272A_OOS_SH,
        "wf_mean":    K272A_WF_MEAN,
        "wf_min":     K272A_WF_MIN,
        "max_dd":     K272A_MAX_DD,
    },

    "k281_results": {
        "oos_sharpe":  round(oos_sh, 4),
        "oos_maxdd":   round(oos_mdd, 6),
        "oos_ann_ret": oos_m["ann_ret"],
        "oos_ann_vol": oos_m["ann_vol"],
        "wf_mean":     round(wf_mean, 4),
        "wf_min":      round(wf_min, 4),
        "wf_all_pos":  wf_all_pos,
        "oos_weights": {LABELS_3[i]: round(float(w_oos[i]), 4) for i in range(3)},
        "full_weights": {LABELS_3[i]: round(float(w_full[i]), 4) for i in range(3)},
        "delta_oos_sh_vs_k272a": round(oos_sh - K272A_OOS_SH, 4),
        "delta_wf_min_vs_k272a": round(wf_min - K272A_WF_MIN, 4),
        "fold_details": fold_list,
    },

    "acceptance": {
        "thresholds": {
            "oos_sh_min":  K281_SH_MIN,
            "wf_min_min":  K272A_WF_MIN,
            "max_dd_max":  K272A_MAX_DD,
        },
        "gates": {
            "g1_oos_sh":          bool(g1_oos_sh),
            "g2_wf_min":          bool(g2_wf_min),
            "g3_maxdd":           bool(g3_maxdd),
            "g4_weights_nonzero": bool(g4_nonzero),
            "accept":             bool(accept),
        },
        "verdict": "K281 ACCEPTED → v6.10.3 PRODUCTION" if accept else "K281 REJECTED — K272a v6.10.1 REMAINS PRODUCTION",
    },

    "k276_variant_comparison": {
        "note": "Verdict on best K265 variant for K272a",
        "K278_K276a_top15": {
            "n_symbols": 15,
            "oos_sharpe": 16.2218,
            "wf_min": 11.2298,
            "delta_sh": "+0.09",
            "verdict": "REJECT — dSh below +0.20 threshold",
        },
        "K280_K276b_top20": {
            "n_symbols": 20,
            "status": "pending — K280 still running",
        },
        "K281_K276c_excl_bot5": {
            "n_symbols": 30,
            "oos_sharpe": round(oos_sh, 4),
            "wf_min": round(wf_min, 4),
            "delta_sh": f"{delta_sh:+.4f}",
            "verdict": "ACCEPT → v6.10.3" if accept else "REJECT",
        },
        "recommendation": (
            "K276c_excl_bot5 is the optimal K265 replacement: max symbol diversity (30), "
            "removes only clear drag symbols (ARK/BLUR/STRK/ARB/SUSHI). "
            "Standalone Sh=24.03 vs K276a=17.99 vs K276b=22.87."
        ),
    },
}

with open("/Users/nekonaomichi/crypto-lab/wave_k281_k272a_k276c.json", "w") as f:
    json.dump(results, f, indent=2, cls=NpEncoder)
print("Saved: wave_k281_k272a_k276c.json")
print(f"\nDone in {runtime}s")
