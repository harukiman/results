"""
Wave K240: K208 Standalone vs K229d Ensemble — Honest Head-to-Head Comparison
Runtime target: <12 min (typically <1 min for bootstrap)
"""
import json, numpy as np
from collections import OrderedDict
from datetime import datetime

# ── Config ───────────────────────────────────────────────────────────────────
ML_START = "2025-01-22"
ML_END   = "2026-04-14"
N_FOLDS  = 4
N_BOOT   = 1000
SEED     = 42
rng      = np.random.default_rng(SEED)

# ── Load K208 standalone (8h bars → daily end-of-day cumulative PnL) ─────────
with open("/Users/nekonaomichi/crypto-lab/wave_k208_curves.json") as f:
    k208_raw = json.load(f)

ts_all  = k208_raw["K208_filtered"]["timestamps"]
pnl_all = k208_raw["K208_filtered"]["cumulative_pnl"]

daily_k208: OrderedDict = OrderedDict()
for i, t in enumerate(ts_all):
    date = t[:10]
    if ML_START <= date <= ML_END:
        daily_k208[date] = pnl_all[i]   # last 8h bar wins

dates_k208 = list(daily_k208.keys())
equity_k208 = np.array([daily_k208[d] for d in dates_k208])

# Convert cumulative PnL → daily returns
# PnL is additive; daily return = diff of cumulative PnL (fraction of some notional)
# But K229 is stored as equity multiplier starting at 1.0.
# Normalise K208 to equity curve starting at 1.0
pnl_start = equity_k208[0]
pnl_end   = equity_k208[-1]
equity_k208_norm = 1.0 + (equity_k208 - pnl_start)   # translate so day-0 = 1.0
ret_k208 = np.diff(equity_k208_norm)                  # daily absolute changes

# ── Load K229d ensemble (already daily equity multiplier) ────────────────────
with open("/Users/nekonaomichi/crypto-lab/wave_k229_curves.json") as f:
    k229_raw = json.load(f)

dates_k229 = k229_raw["dates"]          # 448 dates, ML_START..ML_END
equity_k229 = np.array(k229_raw["K229d"])
ret_k229 = np.diff(equity_k229)         # daily PnL as fraction of starting capital

# ── Align dates (should already match, but verify) ───────────────────────────
assert dates_k208 == dates_k229, (
    f"Date mismatch: k208[{len(dates_k208)}] vs k229[{len(dates_k229)}]"
)
dates = dates_k208
N = len(ret_k208)
assert N == len(ret_k229) == 447, f"Expected 447 return days, got K208:{N} K229:{len(ret_k229)}"

# ── Metrics helper ────────────────────────────────────────────────────────────
def sharpe(r: np.ndarray) -> float:
    if r.std() == 0:
        return 0.0
    return float(r.mean() / r.std() * np.sqrt(365))

def max_dd(equity: np.ndarray) -> float:
    peak = np.maximum.accumulate(equity)
    dd = (equity - peak) / peak
    return float(dd.min())

def calmar(r: np.ndarray, eq: np.ndarray) -> float:
    ann_ret = float((eq[-1] / eq[0]) ** (365 / len(r)) - 1)
    mdd = abs(max_dd(eq))
    return ann_ret / mdd if mdd > 0 else np.nan

def skewkurt(r: np.ndarray):
    n = len(r)
    mu, sigma = r.mean(), r.std()
    if sigma == 0:
        return 0.0, 0.0
    sk = float(np.mean(((r - mu) / sigma) ** 3))
    ku = float(np.mean(((r - mu) / sigma) ** 4) - 3)
    return sk, ku

def wf_sharpes(r: np.ndarray, n_folds: int = 4):
    fold_size = len(r) // n_folds
    sharpes = []
    for i in range(n_folds):
        fold_r = r[i * fold_size: (i + 1) * fold_size]
        sharpes.append(sharpe(fold_r))
    return sharpes

def full_metrics(r: np.ndarray, eq: np.ndarray, label: str) -> dict:
    wf = wf_sharpes(r, N_FOLDS)
    sk, ku = skewkurt(r)
    return {
        "label":   label,
        "oos_sharpe": sharpe(r),
        "wf_fold_sharpes": [round(x, 4) for x in wf],
        "wf_min":  round(min(wf), 4),
        "max_dd":  round(max_dd(eq), 4),
        "calmar":  round(calmar(r, eq), 4),
        "skew":    round(sk, 4),
        "kurt":    round(ku, 4),
        "n_days":  len(r),
    }

# ── Bootstrap CI ─────────────────────────────────────────────────────────────
def bootstrap_sharpe_ci(r: np.ndarray, n: int = N_BOOT, seed_rng=None) -> dict:
    if seed_rng is None:
        seed_rng = rng
    boot = [sharpe(seed_rng.choice(r, size=len(r), replace=True)) for _ in range(n)]
    boot = np.array(boot)
    return {
        "mean":  round(float(boot.mean()), 4),
        "p2_5": round(float(np.percentile(boot, 2.5)), 4),
        "p97_5":round(float(np.percentile(boot, 97.5)), 4),
    }

def bootstrap_diff_ci(r1: np.ndarray, r2: np.ndarray, n: int = N_BOOT) -> dict:
    """Pairwise bootstrap: K208 - K229 Sharpe difference."""
    diffs = []
    idx = np.arange(len(r1))
    for _ in range(n):
        s = rng.choice(idx, size=len(idx), replace=True)
        diffs.append(sharpe(r1[s]) - sharpe(r2[s]))
    diffs = np.array(diffs)
    return {
        "mean":  round(float(diffs.mean()), 4),
        "p2_5": round(float(np.percentile(diffs, 2.5)), 4),
        "p97_5":round(float(np.percentile(diffs, 97.5)), 4),
        "prob_k208_better": round(float((diffs > 0).mean()), 4),
    }

# ── Compute ───────────────────────────────────────────────────────────────────
m_k208 = full_metrics(ret_k208, equity_k208_norm, "K208_standalone")
m_k229 = full_metrics(ret_k229, equity_k229, "K229d_ensemble")

ci_k208 = bootstrap_sharpe_ci(ret_k208)
ci_k229 = bootstrap_sharpe_ci(ret_k229)
diff_ci  = bootstrap_diff_ci(ret_k208, ret_k229)

# ── Decision ──────────────────────────────────────────────────────────────────
sh_k208 = m_k208["oos_sharpe"]
sh_k229 = m_k229["oos_sharpe"]
wf_min_k208 = m_k208["wf_min"]
wf_min_k229 = m_k229["wf_min"]

if sh_k208 >= sh_k229 and wf_min_k208 >= wf_min_k229 - 0.5:
    decision = "SIMPLIFY: K208 standalone dominates or matches K229d on both Sharpe and WF stability"
elif sh_k229 > sh_k208 and diff_ci["p2_5"] < 0:
    decision = "KEEP K229d: ensemble adds value (K229d Sharpe higher, but difference CI includes zero)"
elif sh_k208 > sh_k229 and wf_min_k208 < wf_min_k229:
    decision = "K208 + RISK OVERLAY: K208 Sharpe better but WF stability worse; add position limits"
else:
    decision = "SIMPLIFY: K208 standalone is competitive; K229d complexity not statistically justified"

# ── Save results ──────────────────────────────────────────────────────────────
result = {
    "window": {"start": ML_START, "end": ML_END, "n_days": 448, "n_return_days": 447},
    "metrics": {
        "K208_standalone": m_k208,
        "K229d_ensemble":  m_k229,
    },
    "bootstrap_ci": {
        "K208_standalone": ci_k208,
        "K229d_ensemble":  ci_k229,
    },
    "pairwise_diff_K208_minus_K229": diff_ci,
    "decision": decision,
}

with open("/Users/nekonaomichi/crypto-lab/wave_k240_k208_standalone.json", "w") as f:
    json.dump(result, f, indent=2)

# Equity curves for charting
curves = {
    "dates": dates,
    "K208_standalone": equity_k208_norm.tolist(),
    "K229d_ensemble":  equity_k229.tolist(),
}
with open("/Users/nekonaomichi/crypto-lab/wave_k240_curves.json", "w") as f:
    json.dump(curves, f, indent=2)

# ── Print summary ─────────────────────────────────────────────────────────────
print("=" * 62)
print("Wave K240: K208 Standalone vs K229d Ensemble")
print(f"Window: {ML_START} → {ML_END}  ({N} daily returns)")
print("=" * 62)
print(f"{'Metric':<22} {'K208':>10} {'K229d':>10}")
print("-" * 42)
print(f"{'OOS Sharpe':<22} {sh_k208:>10.4f} {sh_k229:>10.4f}")
print(f"{'WF min Sharpe':<22} {wf_min_k208:>10.4f} {wf_min_k229:>10.4f}")
print(f"{'MaxDD':<22} {m_k208['max_dd']:>10.4f} {m_k229['max_dd']:>10.4f}")
print(f"{'Calmar':<22} {m_k208['calmar']:>10.4f} {m_k229['calmar']:>10.4f}")
print(f"{'Skew':<22} {m_k208['skew']:>10.4f} {m_k229['skew']:>10.4f}")
print(f"{'Kurt':<22} {m_k208['kurt']:>10.4f} {m_k229['kurt']:>10.4f}")
print()
print(f"K208 WF folds: {m_k208['wf_fold_sharpes']}")
print(f"K229 WF folds: {m_k229['wf_fold_sharpes']}")
print()
print("Bootstrap CI (OOS Sharpe, 95%):")
print(f"  K208: {ci_k208['p2_5']} – {ci_k208['p97_5']}  (mean {ci_k208['mean']})")
print(f"  K229: {ci_k229['p2_5']} – {ci_k229['p97_5']}  (mean {ci_k229['mean']})")
print()
print("Pairwise diff K208 - K229d:")
print(f"  mean={diff_ci['mean']}, 95% CI [{diff_ci['p2_5']}, {diff_ci['p97_5']}]")
print(f"  P(K208 > K229) = {diff_ci['prob_k208_better']:.0%}")
print()
print("DECISION:", decision)
print("=" * 62)
print("Saved: wave_k240_k208_standalone.json, wave_k240_curves.json")
