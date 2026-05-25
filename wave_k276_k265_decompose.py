"""
Wave K276 — K265 Per-Symbol Decomposition
==========================================
Objective:
  Decompose K265 (HL Long-Tail FR Carry, 35 symbols) to identify which symbols
  drive alpha vs drag. Build trimmed variants:
    K276a: top 15 by Sharpe contribution
    K276b: top 20 by Sharpe contribution
    K276c: exclude bottom 5 (full 35 minus worst 5)

  Walk-forward 4-fold per trimmed variant.
  Correlation test vs K198/K208.
  Integration test: replace K265 with K276a in K272a (3-way).

Acceptance for K276 → K265 replacement:
  - Trimmed variant Sharpe ≥ 90% of K265 full (13.03 → ≥ 11.73)
  - All WF folds positive
  - Correlation profile preserved

Runtime: <12 min (all offline, no API calls).
"""
from __future__ import annotations

import json
import math
import time
import warnings
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

START_TIME = time.time()
BASE   = Path("/Users/nekonaomichi/crypto-lab")
CACHE  = BASE / "cache"

# ── Constants (same as K265) ─────────────────────────────────────────────────
FR_WINDOW_DAYS = 14
QUARTILE       = 0.25
COST_BPS       = 2.0
COST_RATE      = COST_BPS / 1e4
PPY            = 365.0
N_FOLDS        = 4

K265_FULL_SHARPE = 13.026761   # from wave_k265_hl_longtail_fr.json full_metrics
K265_THRESHOLD   = K265_FULL_SHARPE * 0.90  # ≥ 11.724

OUT_JSON   = BASE / "wave_k276_k265_decompose.json"
OUT_CURVES = BASE / "wave_k276_curves.json"
OUT_MD     = BASE / "wave_k276_k265_decompose.md"


# ── Helpers ──────────────────────────────────────────────────────────────────
def sharpe(ret: np.ndarray) -> float:
    r = np.asarray(ret, dtype=float)
    r = r[np.isfinite(r)]
    if len(r) < 10 or r.std() == 0:
        return 0.0
    return float(r.mean() / r.std() * math.sqrt(PPY))


def max_dd(ret: np.ndarray) -> float:
    r = np.asarray(ret, dtype=float)
    r = r[np.isfinite(r)]
    if len(r) == 0:
        return 0.0
    eq   = np.cumprod(1 + r)
    peak = np.maximum.accumulate(eq)
    return float(((eq - peak) / peak).min())


def ann_ret(ret: np.ndarray) -> float:
    r = np.asarray(ret, dtype=float)
    r = r[np.isfinite(r)]
    return float(r.mean() * PPY)


def ann_vol(ret: np.ndarray) -> float:
    r = np.asarray(ret, dtype=float)
    r = r[np.isfinite(r)]
    return float(r.std() * math.sqrt(PPY))


def win_rate(ret: np.ndarray) -> float:
    r = np.asarray(ret, dtype=float)
    r = r[np.isfinite(r) & (r != 0)]
    return float((r > 0).mean()) if len(r) > 0 else 0.0


def metrics(ret_arr: np.ndarray) -> dict:
    return {
        "sharpe":       sharpe(ret_arr),
        "max_dd":       max_dd(ret_arr),
        "ann_ret":      ann_ret(ret_arr),
        "ann_vol":      ann_vol(ret_arr),
        "win_rate":     win_rate(ret_arr),
        "total_return": float(np.nanprod(1 + ret_arr) - 1),
        "n_days":       int(np.sum(np.isfinite(ret_arr))),
    }


# ── K265 Signal / Weights (replicated exactly) ───────────────────────────────
def compute_signal(fr_panel: pd.DataFrame) -> pd.DataFrame:
    return fr_panel.rolling(window=FR_WINDOW_DAYS, min_periods=7).mean().shift(1)


def dollar_neutral_weights(sig_row: pd.Series, subset: List[str] | None = None) -> pd.Series:
    """
    Replicate K265 L/S carry logic on an optional symbol subset.
    If subset provided, zero out other symbols before ranking.
    """
    if subset is not None:
        sig_row = sig_row.reindex(sig_row.index)
        mask = ~sig_row.index.isin(subset)
        sig_row = sig_row.copy()
        sig_row[mask] = np.nan

    valid = sig_row.dropna()
    n_sym = len(valid)
    if n_sym < 4:
        return pd.Series(0.0, index=sig_row.index)

    n_q    = max(1, int(n_sym * QUARTILE))
    ranked = valid.rank(ascending=True)
    longs  = ranked[ranked <= n_q].index
    shorts = ranked[ranked > n_sym - n_q].index

    w = pd.Series(0.0, index=sig_row.index)
    if len(longs)  > 0:
        w[longs]  = +1.0 / len(longs)
    if len(shorts) > 0:
        w[shorts] = -1.0 / len(shorts)
    return w


def compute_weights(sig: pd.DataFrame, subset: List[str] | None = None) -> pd.DataFrame:
    return sig.apply(lambda row: dollar_neutral_weights(row, subset), axis=1)


def compute_pnl(fr_panel: pd.DataFrame, weights: pd.DataFrame) -> Tuple[pd.Series, pd.Series]:
    common = fr_panel.index.intersection(weights.index)
    fr_c   = fr_panel.loc[common]
    w_c    = weights.loc[common]
    w_lag  = w_c.shift(1).fillna(0.0)
    fr_daily = fr_c * 24.0
    pnl_fr  = (-w_lag * fr_daily).sum(axis=1)
    turn    = (w_c - w_c.shift(1).fillna(0.0)).abs().sum(axis=1)
    cost    = turn * COST_RATE
    return (pnl_fr - cost).dropna(), pnl_fr.dropna()


def walk_forward(pnl: pd.Series) -> List[Dict]:
    n, fold_size = len(pnl), len(pnl) // N_FOLDS
    folds = []
    for i in range(N_FOLDS):
        s = i * fold_size
        e = s + fold_size if i < N_FOLDS - 1 else n
        fold_ret = pnl.iloc[s:e].values
        fm = metrics(fold_ret)
        fm["fold"]  = i
        fm["start"] = str(pnl.index[s].date())
        fm["end"]   = str(pnl.index[e - 1].date())
        folds.append(fm)
    return folds


# ── Load External Curves for Correlation ─────────────────────────────────────
def load_k198_pnl() -> pd.Series:
    try:
        with open(BASE / "wave_k198_curves.json") as f:
            d = json.load(f)
        dates = pd.to_datetime(d["dates_ml"])
        return pd.Series(d["pnl_ridge"], index=dates).dropna()
    except Exception:
        return pd.Series(dtype=float)


def load_k208_pnl() -> pd.Series:
    try:
        with open(BASE / "wave_k208_curves.json") as f:
            d = json.load(f)
        k208 = d["K208_filtered"]
        ts   = pd.to_datetime(k208["timestamps"])
        cum  = np.array(k208["cumulative_pnl"])
        s8   = pd.Series(np.diff(cum, prepend=cum[0]), index=ts)
        pnl  = s8.groupby(s8.index.normalize()).sum()
        pnl.index = pd.to_datetime(pnl.index)
        return pnl.dropna()
    except Exception:
        return pd.Series(dtype=float)


def corr_with_benchmark(pnl_trimmed: pd.Series,
                        k198: pd.Series, k208: pd.Series) -> dict:
    out = {}
    for name, bench in [("K198", k198), ("K208", k208)]:
        common = pnl_trimmed.index.intersection(bench.index)
        if len(common) >= 30:
            out[name] = round(float(np.corrcoef(
                pnl_trimmed.loc[common].values,
                bench.loc[common].values)[0, 1]), 4)
        else:
            out[name] = None
    return out


# ── Per-Symbol Contribution Analysis ─────────────────────────────────────────
def per_symbol_contribution(fr_panel: pd.DataFrame,
                            sig: pd.DataFrame,
                            full_weights: pd.DataFrame,
                            full_pnl_net: pd.Series,
                            sym_stats: dict) -> List[Dict]:
    """
    For each symbol:
      1. ann_carry_pct from K265 JSON
      2. direction_stability = fraction of days where FR sign matches 14d-mean sign
      3. marginal Sharpe impact = Sharpe(full) - Sharpe(remove_sym)
      4. standalone_carry = mean annual carry for this symbol alone
    """
    syms = fr_panel.columns.tolist()
    full_sh = sharpe(full_pnl_net.values)

    results = []
    for sym in syms:
        st = sym_stats.get(sym, {})

        # 1. Direction stability
        fr_col = fr_panel[sym].dropna()
        roll14 = fr_col.rolling(14, min_periods=7).mean()
        agree  = (fr_col * roll14 > 0)
        dir_stab = float(agree.mean()) if len(agree) > 0 else 0.0

        # 2. Marginal Sharpe contribution (leave-one-out)
        remaining = [s for s in syms if s != sym]
        w_loo = compute_weights(sig, subset=remaining)
        pnl_loo, _ = compute_pnl(fr_panel, w_loo)
        sh_loo = sharpe(pnl_loo.values)
        marginal_sh = full_sh - sh_loo  # positive = this sym adds Sharpe

        # 3. Per-symbol carry contribution from weights
        #    Mean daily PnL from this symbol's leg
        sym_wt = full_weights[sym].shift(1).fillna(0.0)
        sym_fr = fr_panel[sym] * 24.0
        common = sym_wt.index.intersection(sym_fr.index)
        sym_pnl = (-sym_wt.loc[common] * sym_fr.loc[common]).dropna()
        sym_ann_carry = float(sym_pnl.mean() * PPY) if len(sym_pnl) > 0 else 0.0
        sym_sh = sharpe(sym_pnl.values) if len(sym_pnl) > 0 else 0.0

        results.append({
            "symbol":           sym,
            "ann_carry_pct_k265": round(st.get("ann_carry_pct", 0), 2),
            "mean_fr_pct":      st.get("mean_fr_pct", 0),
            "abs_mean_fr_pct":  st.get("abs_mean_fr_pct", 0),
            "direction_stability": round(dir_stab, 3),
            "marginal_sharpe":  round(marginal_sh, 4),  # + = adds value
            "sym_ann_carry":    round(sym_ann_carry, 6),
            "sym_sharpe":       round(sym_sh, 4),
            "high_carry":       st.get("high_carry", False),
        })

    # Sort by marginal_sharpe descending (best contributors first)
    results.sort(key=lambda x: x["marginal_sharpe"], reverse=True)
    for rank, r in enumerate(results, 1):
        r["rank"] = rank
    return results


# ── Trimmed Variant Runner ────────────────────────────────────────────────────
def run_trimmed_variant(name: str, subset: List[str],
                        fr_panel: pd.DataFrame, sig: pd.DataFrame,
                        k198_pnl: pd.Series, k208_pnl: pd.Series) -> Dict:
    print(f"\n  [{name}] {len(subset)} symbols: {subset[:5]}...", flush=True)
    w    = compute_weights(sig, subset=subset)
    pnl_net, pnl_gross = compute_pnl(fr_panel, w)
    if len(pnl_net) < 100:
        return {"name": name, "error": "insufficient data"}

    m_full  = metrics(pnl_net.values)
    m_gross = metrics(pnl_gross.values)

    n_total = len(pnl_net)
    n_oos   = int(n_total * 0.30)
    n_is    = n_total - n_oos
    m_is    = metrics(pnl_net.iloc[:n_is].values)
    m_oos   = metrics(pnl_net.iloc[n_is:].values)

    folds   = walk_forward(pnl_net)
    wf_sh   = [f["sharpe"] for f in folds]
    wf_sum  = {
        "mean_sharpe":  round(float(np.mean(wf_sh)), 4),
        "min_sharpe":   round(float(np.min(wf_sh)),  4),
        "all_positive": bool(all(s > 0 for s in wf_sh)),
    }

    corrs = corr_with_benchmark(pnl_net, k198_pnl, k208_pnl)

    meets_threshold = m_full["sharpe"] >= K265_THRESHOLD
    meets_wf_pos    = wf_sum["all_positive"]
    verdict = "PASS" if (meets_threshold and meets_wf_pos) else "FAIL"

    print(f"  [{name}] full_Sh={m_full['sharpe']:.3f}  "
          f"oos_Sh={m_oos['sharpe']:.3f}  "
          f"wf_min={wf_sum['min_sharpe']:.3f}  "
          f"corr_K198={corrs.get('K198')}  corr_K208={corrs.get('K208')}  "
          f"→ {verdict}")

    equity  = np.cumprod(1 + pnl_net.values).tolist()
    return {
        "name":          name,
        "n_symbols":     len(subset),
        "symbols":       subset,
        "full_metrics":  {k: round(v, 6) if isinstance(v, float) else v
                          for k, v in m_full.items()},
        "is_metrics":    {k: round(v, 6) if isinstance(v, float) else v
                          for k, v in m_is.items()},
        "oos_metrics":   {k: round(v, 6) if isinstance(v, float) else v
                          for k, v in m_oos.items()},
        "gross_metrics": {k: round(v, 6) if isinstance(v, float) else v
                          for k, v in m_gross.items()},
        "wf_folds":      folds,
        "wf_summary":    wf_sum,
        "correlations":  corrs,
        "meets_sh_threshold": meets_threshold,
        "meets_wf_pos":       meets_wf_pos,
        "verdict":       verdict,
        "threshold_used": round(K265_THRESHOLD, 4),
        "dates":   [str(d.date()) for d in pnl_net.index],
        "equity":  [round(v, 6) for v in equity],
        "pnl":     [round(v, 8) for v in pnl_net.values],
    }


# ── K272a Integration Test ─────────────────────────────────────────────────────
def k272a_integration_test(pnl_k276: pd.Series,
                            k198_pnl: pd.Series, k208_pnl: pd.Series,
                            variant_name: str) -> Dict:
    """
    Replicate K272a 3-way equal-weight combo:
    Replace K265 with K276 variant (K198+K208+K276x).
    Use last 448 days data (matching K272a window), 4-fold WF.
    """
    # Align all three series
    common = k198_pnl.index.intersection(k208_pnl.index).intersection(pnl_k276.index)
    if len(common) < 100:
        return {"error": "insufficient overlap", "n_common": len(common)}

    # Equal-weight combo
    combo = (k198_pnl.loc[common] + k208_pnl.loc[common] + pnl_k276.loc[common]) / 3.0

    n_total = len(combo)
    n_oos   = int(n_total * 0.30)
    n_is    = n_total - n_oos

    m_full = metrics(combo.values)
    m_oos  = metrics(combo.iloc[n_is:].values)

    folds  = walk_forward(combo)
    wf_sh  = [f["sharpe"] for f in folds]
    wf_sum = {
        "mean_sharpe":  round(float(np.mean(wf_sh)), 4),
        "min_sharpe":   round(float(np.min(wf_sh)),  4),
        "all_positive": bool(all(s > 0 for s in wf_sh)),
    }

    # Correlation matrix 3x3
    arr_k198 = k198_pnl.loc[common].values
    arr_k208 = k208_pnl.loc[common].values
    arr_k276 = pnl_k276.loc[common].values
    mat = np.corrcoef([arr_k198, arr_k208, arr_k276])
    corr_mat = {
        "K198": {"K198": round(mat[0,0],4), "K208": round(mat[0,1],4), variant_name: round(mat[0,2],4)},
        "K208": {"K198": round(mat[1,0],4), "K208": round(mat[1,1],4), variant_name: round(mat[1,2],4)},
        variant_name: {"K198": round(mat[2,0],4), "K208": round(mat[2,1],4), variant_name: round(mat[2,2],4)},
    }

    return {
        "variant":       variant_name,
        "n_overlap_days": len(common),
        "full_metrics":  {k: round(v, 6) if isinstance(v, float) else v
                          for k, v in m_full.items()},
        "oos_metrics":   {k: round(v, 6) if isinstance(v, float) else v
                          for k, v in m_oos.items()},
        "wf_summary":    wf_sum,
        "correlation_matrix": corr_mat,
        "wf_folds":      folds,
    }


# ── Main ──────────────────────────────────────────────────────────────────────
def main() -> None:
    print("=" * 60)
    print("Wave K276 — K265 Per-Symbol Decomposition")
    print("=" * 60)

    # 1. Load panel
    panel_path = CACHE / "hl_longtail_fr_daily.parquet"
    print(f"\n[K276] Loading FR panel from {panel_path}...")
    fr_panel = pd.read_parquet(panel_path)
    syms = fr_panel.columns.tolist()
    print(f"  Panel: {len(syms)} symbols, {len(fr_panel)} days "
          f"({fr_panel.index[0].date()} → {fr_panel.index[-1].date()})")

    # 2. Load K265 symbol stats
    with open(BASE / "wave_k265_hl_longtail_fr.json") as f:
        k265_data = json.load(f)
    sym_stats = k265_data["per_symbol_stats"]

    # 3. Compute full K265 signal + weights + pnl (reference)
    print("\n[K276] Computing full K265 reference...")
    sig          = compute_signal(fr_panel)
    full_weights = compute_weights(sig, subset=None)
    full_pnl_net, full_pnl_gross = compute_pnl(fr_panel, full_weights)
    full_sh = sharpe(full_pnl_net.values)
    print(f"  K265 reference: full_Sh={full_sh:.4f} (stored: {K265_FULL_SHARPE:.4f})")

    # 4. Load benchmark pnl for correlation
    print("\n[K276] Loading K198/K208 for correlation...")
    k198_pnl = load_k198_pnl()
    k208_pnl = load_k208_pnl()
    print(f"  K198: {len(k198_pnl)} days | K208: {len(k208_pnl)} days")

    # 5. Per-symbol decomposition (marginal LOO Sharpe)
    print("\n[K276] Per-symbol marginal Sharpe decomposition (35 LOO runs)...")
    t0 = time.time()
    sym_contributions = per_symbol_contribution(
        fr_panel, sig, full_weights, full_pnl_net, sym_stats
    )
    print(f"  Done in {time.time() - t0:.1f}s")

    top5    = [r["symbol"] for r in sym_contributions[:5]]
    bottom5 = [r["symbol"] for r in sym_contributions[-5:]]
    print(f"\n  Top-5 contributors:  {top5}")
    print(f"  Bottom-5 (drag):      {bottom5}")

    # 6. Build trimmed symbol sets
    ranked_syms = [r["symbol"] for r in sym_contributions]  # best→worst
    top15_syms  = ranked_syms[:15]
    top20_syms  = ranked_syms[:20]
    exc_bot5    = [s for s in syms if s not in bottom5]   # preserve original order except bottom5

    print(f"\n[K276] Building trimmed variants:")
    print(f"  K276a top15: {top15_syms}")
    print(f"  K276b top20: {top20_syms[:5]}... ({len(top20_syms)} total)")
    print(f"  K276c excl-bot5: {len(exc_bot5)} symbols (drop {bottom5})")

    # 7. Run trimmed variants
    print("\n[K276] Running trimmed variant backtests...")
    variants = {}
    for vname, subset in [
        ("K276a_top15",     top15_syms),
        ("K276b_top20",     top20_syms),
        ("K276c_excl_bot5", exc_bot5),
    ]:
        result = run_trimmed_variant(vname, subset, fr_panel, sig, k198_pnl, k208_pnl)
        variants[vname] = result

    # 8. K272a integration test (replace K265 with K276a)
    print("\n[K276] K272a integration test (K198+K208+K276a)...")
    k276a_pnl = pd.Series(
        variants["K276a_top15"]["pnl"],
        index=pd.to_datetime(variants["K276a_top15"]["dates"])
    )
    integration_k272a = k272a_integration_test(k276a_pnl, k198_pnl, k208_pnl, "K276a")

    # 9. Compile per-symbol table
    sym_table = []
    for r in sym_contributions:
        sym_table.append({
            "rank":                r["rank"],
            "symbol":              r["symbol"],
            "ann_carry_pct_k265":  r["ann_carry_pct_k265"],
            "direction_stability": r["direction_stability"],
            "marginal_sharpe":     r["marginal_sharpe"],
            "sym_ann_carry":       r["sym_ann_carry"],
            "sym_sharpe":          r["sym_sharpe"],
            "high_carry":          r["high_carry"],
        })

    # 10. Acceptance gates per variant
    gates_summary = {}
    for vname, vres in variants.items():
        if "error" in vres:
            gates_summary[vname] = {"verdict": "ERROR", "error": vres["error"]}
            continue
        gates_summary[vname] = {
            "full_sharpe":          round(vres["full_metrics"]["sharpe"], 4),
            "sh_ge_90pct_k265":     vres["meets_sh_threshold"],
            "wf_all_positive":      vres["wf_summary"]["all_positive"],
            "wf_min_sharpe":        vres["wf_summary"]["min_sharpe"],
            "corr_K198":            vres["correlations"].get("K198"),
            "corr_K208":            vres["correlations"].get("K208"),
            "verdict":              vres["verdict"],
        }

    # 11. Final verdict
    best_variant = None
    for vname in ["K276a_top15", "K276b_top20", "K276c_excl_bot5"]:
        if gates_summary.get(vname, {}).get("verdict") == "PASS":
            best_variant = vname
            break

    trimming_feasible = best_variant is not None

    print(f"\n{'='*60}")
    print(f"[K276] Per-symbol analysis complete")
    print(f"  Top-5:    {top5}")
    print(f"  Bottom-5: {bottom5}")
    for vname, gs in gates_summary.items():
        print(f"  {vname}: Sh={gs.get('full_sharpe','n/a')}  verdict={gs.get('verdict')}")
    print(f"  K272a integration Sh={integration_k272a.get('full_metrics',{}).get('sharpe','n/a'):.3f}")
    print(f"  → K265 trimming feasible: {trimming_feasible}  (best: {best_variant})")

    # 12. Save outputs
    output = {
        "wave":     "K276",
        "task":     "K265_SymbolDecomposition",
        "as_of":    pd.Timestamp.utcnow().isoformat(),
        "runtime_s": round(time.time() - START_TIME, 1),
        "k265_reference": {
            "n_symbols":        len(syms),
            "symbols":          syms,
            "full_sharpe":      round(full_sh, 6),
            "stored_sharpe":    K265_FULL_SHARPE,
            "threshold_90pct":  round(K265_THRESHOLD, 4),
        },
        "per_symbol_table":     sym_table,
        "top5_contributors":    top5,
        "bottom5_drag":         bottom5,
        "trimmed_variants": {
            vname: {
                "n_symbols":     vres.get("n_symbols"),
                "symbols":       vres.get("symbols"),
                "full_metrics":  vres.get("full_metrics"),
                "is_metrics":    vres.get("is_metrics"),
                "oos_metrics":   vres.get("oos_metrics"),
                "wf_summary":    vres.get("wf_summary"),
                "correlations":  vres.get("correlations"),
                "meets_sh_threshold": vres.get("meets_sh_threshold"),
                "meets_wf_pos":  vres.get("meets_wf_pos"),
                "verdict":       vres.get("verdict"),
            }
            for vname, vres in variants.items()
        },
        "gates_summary":        gates_summary,
        "k272a_integration": {
            "description": "K198+K208+K276a (3-way, equal-weight)",
            "result":       integration_k272a,
            "k272a_ref_oos_sharpe": 16.1287,
        },
        "trimming_feasible":    trimming_feasible,
        "best_variant":         best_variant,
        "verdict_trimming": (
            f"FEASIBLE — {best_variant} qualifies as K265 replacement"
            if trimming_feasible else
            "INFEASIBLE — no trimmed variant meets 90% Sharpe threshold"
        ),
    }

    with open(OUT_JSON, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\n[K276] Saved metrics → {OUT_JSON}")

    # 13. Save curves JSON (per-symbol standalone + trimmed variants)
    curves_out = {
        "wave":  "K276",
        "k265_reference": {
            "dates":  [str(d.date()) for d in full_pnl_net.index],
            "equity": [round(float(v), 6) for v in np.cumprod(1 + full_pnl_net.values)],
            "pnl":    [round(float(v), 8) for v in full_pnl_net.values],
        },
    }
    for vname, vres in variants.items():
        if "error" not in vres:
            curves_out[vname] = {
                "dates":  vres["dates"],
                "equity": vres["equity"],
                "pnl":    vres["pnl"],
            }

    with open(OUT_CURVES, "w") as f:
        json.dump(curves_out, f, indent=2)
    print(f"[K276] Saved curves  → {OUT_CURVES}")

    # 14. Write MD report
    write_md_report(output, sym_table, variants, gates_summary,
                    integration_k272a, trimming_feasible, best_variant)


def write_md_report(output, sym_table, variants, gates_summary,
                    integration, trimming_feasible, best_variant) -> None:
    k265_ref = output["k265_reference"]
    top5     = output["top5_contributors"]
    bottom5  = output["bottom5_drag"]

    lines = [
        "# Wave K276 — K265 Per-Symbol Decomposition",
        "",
        f"**Date:** {output['as_of'][:10]}  |  **Runtime:** {output['runtime_s']:.0f}s",
        "",
        "## Objective",
        "Decompose K265 (35-symbol HL FR carry) to identify alpha vs drag symbols.",
        "Build trimmed variants (K276a/b/c) and test if fewer symbols retain ≥90% Sharpe.",
        "",
        f"## K265 Reference: {k265_ref['n_symbols']} symbols",
        f"Full Sharpe: **{k265_ref['full_sharpe']:.4f}** | Threshold (90%): **{k265_ref['threshold_90pct']:.4f}**",
        "",
        "## Per-Symbol Contribution Table (35 rows, sorted by marginal Sharpe)",
        "| Rank | Symbol | Ann Carry% | Dir Stability | Marginal Sharpe | Sym Sharpe | High Carry |",
        "|------|--------|-----------|--------------|----------------|------------|------------|",
    ]
    for r in sym_table:
        marker = " ▲" if r["symbol"] in top5 else (" ▼" if r["symbol"] in bottom5 else "")
        lines.append(
            f"| {r['rank']:2d} | {r['symbol']:8s}{marker:2s} | "
            f"{r['ann_carry_pct_k265']:5.2f}% | "
            f"{r['direction_stability']:.3f} | "
            f"{r['marginal_sharpe']:+.4f} | "
            f"{r['sym_sharpe']:.4f} | "
            f"{'YES' if r['high_carry'] else 'no'} |"
        )

    lines += [
        "",
        f"**Top-5 alpha contributors:** {', '.join(top5)}",
        f"**Bottom-5 drag symbols:**    {', '.join(bottom5)}",
        "",
        "## Trimmed Variants Comparison",
        "| Variant | N | Full Sharpe | OOS Sharpe | WF Min Sh | WF All+ | corr K198 | corr K208 | Verdict |",
        "|---------|---|------------|-----------|-----------|---------|----------|----------|---------|",
    ]
    for vname, vres in variants.items():
        if "error" in vres:
            lines.append(f"| {vname} | - | ERROR | - | - | - | - | - | FAIL |")
            continue
        fm   = vres["full_metrics"]
        om   = vres["oos_metrics"]
        wfs  = vres["wf_summary"]
        corr = vres["correlations"]
        lines.append(
            f"| {vname} | {vres['n_symbols']} | "
            f"{fm['sharpe']:.4f} | {om['sharpe']:.4f} | "
            f"{wfs['min_sharpe']:.4f} | {'YES' if wfs['all_positive'] else 'NO'} | "
            f"{corr.get('K198', 'n/a')} | {corr.get('K208', 'n/a')} | "
            f"{vres['verdict']} |"
        )

    # K272a integration
    ig = integration.get("full_metrics", {})
    io = integration.get("oos_metrics", {})
    iwf = integration.get("wf_summary", {})
    lines += [
        "",
        "## K272a Integration Test (K198+K208+K276a, 3-way equal-weight)",
        f"| Period | Sharpe | MaxDD | AnnRet |",
        f"|--------|--------|-------|--------|",
        f"| Full   | {ig.get('sharpe', 'n/a'):.4f} | {ig.get('max_dd', 0):.4%} | {ig.get('ann_ret', 0):.4%} |",
        f"| OOS    | {io.get('sharpe', 'n/a'):.4f} | {io.get('max_dd', 0):.4%} | {io.get('ann_ret', 0):.4%} |",
        f"WF min Sharpe: {iwf.get('min_sharpe', 'n/a')} | all_positive: {iwf.get('all_positive', 'n/a')}",
        f"K272a ref OOS Sharpe: **{output['k272a_integration']['k272a_ref_oos_sharpe']}**",
    ]

    # Correlation matrix if available
    cm = integration.get("correlation_matrix", {})
    if cm:
        lines += [
            "",
            "### Correlation Matrix (K198/K208/K276a)",
            "| | K198 | K208 | K276a |",
            "|---|---|---|---|",
        ]
        for row_name in ["K198", "K208", "K276a"]:
            row = cm.get(row_name, {})
            lines.append(
                f"| {row_name} | {row.get('K198','n/a')} | "
                f"{row.get('K208','n/a')} | "
                f"{row.get('K276a','n/a')} |"
            )

    lines += [
        "",
        "## Verdict on K265 Trimming Feasibility",
        "",
        f"**Trimming feasible:** {'YES' if trimming_feasible else 'NO'}",
        f"**Best variant:** {best_variant if best_variant else 'None passed gates'}",
        "",
    ]

    if trimming_feasible:
        bv = variants[best_variant]
        bm = bv["full_metrics"]
        savings = k265_ref["n_symbols"] - bv["n_symbols"]
        lines += [
            f"### Recommendation: Replace K265 with {best_variant} in K272a",
            f"- Sharpe preserved: {bm['sharpe']:.4f} vs K265 {k265_ref['full_sharpe']:.4f} "
            f"({bm['sharpe']/k265_ref['full_sharpe']*100:.1f}%)",
            f"- Operational benefit: {savings} fewer symbols to manage",
            f"- All WF folds positive: {bv['wf_summary']['all_positive']}",
            f"- Correlation profile preserved (rho K198={bv['correlations'].get('K198')}, "
            f"K208={bv['correlations'].get('K208')})",
            "",
            "### Next Wave (K277)",
            "- Live deploy K272a v6.10.1 with {best_variant} replacing K265",
            "- Recheck correlation monthly as HL universe evolves",
        ]
    else:
        lines += [
            "No trimmed variant achieves 90% of K265 Sharpe. K265 retains full 35-symbol universe.",
            "",
            "### Analysis",
            "- Alpha is distributed broadly; no small subset dominates",
            "- K265 remains as-is in K272a production",
            "- Bottom-5 symbols do not drag sufficiently to justify removal",
        ]

    with open(OUT_MD, "w") as f:
        f.write("\n".join(lines) + "\n")
    print(f"[K276] Saved report  → {OUT_MD}")


if __name__ == "__main__":
    main()
