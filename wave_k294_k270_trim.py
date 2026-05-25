"""
Wave K294 — K270 dYdX Low-OI Symbol Trim Analysis
===================================================
Objective:
  Investigate data-quality / low-OI symbols in K270 dYdX universe (30 symbols).
  Build trimmed variants:
    K294a: top 20 by Sharpe contribution (drop 10 worst)
    K294b: top 15 (more aggressive trim)
    K294c: exclude bottom 5 (gentle trim, keep 25)

  Walk-forward 4-fold per variant.
  Correlation test vs K276b (orthogonality check).
  Acceptance: best variant Sh > K270 baseline + 1.0, WF all positive, rho_K276b < 0.4.

Runtime: <10 min (all offline, parquet cache).
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
BASE       = Path("/Users/nekonaomichi/crypto-lab")
CACHE      = BASE / "cache" / "k270_dydx"

# ── Constants (replicate K270 exactly) ───────────────────────────────────────
FR_WINDOW_DAYS = 14
QUARTILE       = 0.25
COST_BPS       = 2.0
COST_RATE      = COST_BPS / 1e4
PPY            = 365.0
N_FOLDS        = 4

K270_FULL_SHARPE = 10.549536   # from wave_k270_alt_exchange_fr.json full_metrics
K270_OOS_SHARPE  = 11.854406   # OOS Sh target baseline
ACCEPTANCE_DELTA = 1.0         # best variant must beat K270 full_metrics Sh by +1.0

OUT_JSON   = BASE / "wave_k294_k270_trim.json"
OUT_CURVES = BASE / "wave_k294_curves.json"
OUT_MD     = BASE / "wave_k294_k270_trim.md"

DYDX_SYMBOLS = [
    "AAVE", "ADA", "APT", "ARB", "ATOM",
    "AVAX", "AXS", "BLUR", "BONK", "CRV",
    "DOGE", "DOT", "ENA", "INJ", "JUP",
    "LDO", "NEAR", "OP", "PEPE", "PYTH",
    "SEI", "SOL", "SUI", "TAO", "TIA",
    "UNI", "WIF", "WLD", "XRP", "BNB",
]

# Zero-FR threshold: if hourly FR is within ±1e-6, count as effectively zero
ZERO_FR_THRESH = 1e-6

# Low-OI flags (>20% zero FR or ann_carry < 2%)
LOW_OI_ZERO_PCT_THRESH = 0.20
LOW_OI_CARRY_THRESH    = 2.0   # ann_carry_pct


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


def ann_vol_fn(ret: np.ndarray) -> float:
    r = np.asarray(ret, dtype=float)
    r = r[np.isfinite(r)]
    return float(r.std() * math.sqrt(PPY))


def win_rate_fn(ret: np.ndarray) -> float:
    r = np.asarray(ret, dtype=float)
    r = r[np.isfinite(r) & (r != 0)]
    return float((r > 0).mean()) if len(r) > 0 else 0.0


def metrics(ret_arr: np.ndarray) -> dict:
    return {
        "sharpe":       sharpe(ret_arr),
        "max_dd":       max_dd(ret_arr),
        "ann_ret":      ann_ret(ret_arr),
        "ann_vol":      ann_vol_fn(ret_arr),
        "win_rate":     win_rate_fn(ret_arr),
        "total_return": float(np.nanprod(1 + ret_arr) - 1),
        "n_days":       int(np.sum(np.isfinite(ret_arr))),
    }


# ── Signal / Weights (K270 exact) ────────────────────────────────────────────
def compute_signal(fr_panel: pd.DataFrame) -> pd.DataFrame:
    return fr_panel.rolling(window=FR_WINDOW_DAYS, min_periods=7).mean().shift(1)


def dollar_neutral_weights(sig_row: pd.Series,
                            subset: List[str] | None = None) -> pd.Series:
    if subset is not None:
        sig_row = sig_row.copy()
        mask = ~sig_row.index.isin(subset)
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


def compute_weights(sig: pd.DataFrame,
                    subset: List[str] | None = None) -> pd.DataFrame:
    return sig.apply(lambda row: dollar_neutral_weights(row, subset), axis=1)


def compute_pnl(fr_panel: pd.DataFrame,
                weights: pd.DataFrame) -> Tuple[pd.Series, pd.Series]:
    common   = fr_panel.index.intersection(weights.index)
    fr_c     = fr_panel.loc[common]
    w_c      = weights.loc[common]
    w_lag    = w_c.shift(1).fillna(0.0)
    fr_daily = fr_c * 24.0
    pnl_fr   = (-w_lag * fr_daily).sum(axis=1)
    turn     = (w_c - w_c.shift(1).fillna(0.0)).abs().sum(axis=1)
    cost     = turn * COST_RATE
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


# ── Load Data ─────────────────────────────────────────────────────────────────
def load_fr_panel() -> pd.DataFrame:
    """Load all 30 parquets → daily mean FR panel."""
    print("Loading dYdX parquets...", flush=True)
    dfs: Dict[str, pd.Series] = {}
    for sym in DYDX_SYMBOLS:
        fp = CACHE / f"dydx_fr_{sym}.parquet"
        if not fp.exists():
            print(f"  WARNING: {sym} parquet missing, skipping")
            continue
        df = pd.read_parquet(fp)
        df["timestamp"] = pd.to_datetime(df["timestamp"]).dt.normalize()
        daily = df.groupby("timestamp")["dydx_fr"].mean()
        dfs[sym] = daily

    panel = pd.DataFrame(dfs)
    panel.index = pd.to_datetime(panel.index)
    panel.sort_index(inplace=True)
    print(f"  Panel: {panel.shape[0]} days × {panel.shape[1]} symbols", flush=True)
    return panel


# ── Coverage Analysis ─────────────────────────────────────────────────────────
def coverage_analysis(panel: pd.DataFrame) -> List[Dict]:
    """Per-symbol: zero-FR days, mean |FR|, std FR, data-gap classification."""
    print("\nCoverage analysis...", flush=True)
    rows = []
    for sym in panel.columns:
        col = panel[sym].dropna()
        if len(col) == 0:
            continue
        n_days         = len(col)
        zero_days      = int((col.abs() < ZERO_FR_THRESH).sum())
        pct_zero       = zero_days / n_days
        mean_abs_fr    = float(col.abs().mean())
        std_fr         = float(col.std())
        mean_fr        = float(col.mean())
        ann_carry      = mean_abs_fr * 24.0 * PPY * 100.0   # approx ann carry %
        # Low-OI flag
        low_oi = (pct_zero > LOW_OI_ZERO_PCT_THRESH) or (ann_carry < LOW_OI_CARRY_THRESH)
        rows.append({
            "symbol":        sym,
            "n_days":        n_days,
            "zero_days":     zero_days,
            "pct_zero":      round(pct_zero, 4),
            "mean_fr":       round(mean_fr, 6),
            "mean_abs_fr":   round(mean_abs_fr, 6),
            "std_fr":        round(std_fr, 6),
            "ann_carry_pct": round(ann_carry, 2),
            "low_oi_flag":   low_oi,
        })
    rows.sort(key=lambda x: x["pct_zero"], reverse=True)
    return rows


# ── Per-Symbol Sharpe Contribution ───────────────────────────────────────────
def per_symbol_contribution(fr_panel: pd.DataFrame,
                             sig: pd.DataFrame,
                             full_pnl_net: pd.Series) -> List[Dict]:
    """Leave-one-out marginal Sharpe contribution for each symbol."""
    print("\nPer-symbol marginal Sharpe contribution (LOO)...", flush=True)
    syms     = fr_panel.columns.tolist()
    full_sh  = sharpe(full_pnl_net.values)
    results  = []

    for i, sym in enumerate(syms):
        remaining = [s for s in syms if s != sym]
        w_loo     = compute_weights(sig, subset=remaining)
        pnl_loo, _ = compute_pnl(fr_panel, w_loo)
        sh_loo    = sharpe(pnl_loo.values)
        marginal  = full_sh - sh_loo   # positive = sym adds Sharpe

        # Standalone daily carry for this symbol
        fr_col = fr_panel[sym] * 24.0
        results.append({
            "symbol":          sym,
            "marginal_sharpe": round(marginal, 4),
            "sh_without":      round(sh_loo, 4),
            "ann_carry_pct":   round(float(fr_col.mean() * PPY * 100), 2),
        })
        print(f"  [{i+1:2d}/30] {sym}: marginal Sh={marginal:+.4f} (without={sh_loo:.4f})",
              flush=True)

    results.sort(key=lambda x: x["marginal_sharpe"], reverse=True)
    for rank, r in enumerate(results, 1):
        r["rank"] = rank
    return results


# ── Trimmed Variant Runner ────────────────────────────────────────────────────
def run_trimmed_variant(name: str, subset: List[str],
                        fr_panel: pd.DataFrame, sig: pd.DataFrame,
                        k276b_pnl: pd.Series) -> Tuple[Dict, pd.Series]:
    print(f"\n  [{name}] {len(subset)} symbols...", flush=True)
    w           = compute_weights(sig, subset=subset)
    pnl_net, pnl_gross = compute_pnl(fr_panel, w)
    if len(pnl_net) < 100:
        return {"name": name, "error": "insufficient data"}, pd.Series(dtype=float)

    m_full   = metrics(pnl_net.values)
    m_gross  = metrics(pnl_gross.values)
    wf_folds = walk_forward(pnl_net)
    wf_sharpes = [f["sharpe"] for f in wf_folds]

    # Correlation with K276b
    common = pnl_net.index.intersection(k276b_pnl.index)
    if len(common) >= 30:
        rho_k276b = round(float(np.corrcoef(
            pnl_net.loc[common].values,
            k276b_pnl.loc[common].values)[0, 1]), 4)
    else:
        rho_k276b = None

    result = {
        "name":         name,
        "n_symbols":    len(subset),
        "symbols":      subset,
        "full_metrics": m_full,
        "gross_metrics": m_gross,
        "walk_forward_folds": wf_folds,
        "wf_summary": {
            "mean_sharpe": round(float(np.mean(wf_sharpes)), 4),
            "min_sharpe":  round(float(np.min(wf_sharpes)), 4),
            "all_positive": all(s > 0 for s in wf_sharpes),
        },
        "rho_k276b":    rho_k276b,
        "sh_vs_k270_baseline": round(m_full["sharpe"] - K270_FULL_SHARPE, 4),
        "acceptance": {
            "sh_gt_baseline_plus1": m_full["sharpe"] > K270_FULL_SHARPE + ACCEPTANCE_DELTA,
            "wf_all_positive":      all(s > 0 for s in wf_sharpes),
            "rho_k276b_lt_0.4":    (rho_k276b is not None and abs(rho_k276b) < 0.4),
        },
    }
    print(f"    Sh={m_full['sharpe']:.4f} | WF_min={min(wf_sharpes):.4f} | rho_K276b={rho_k276b}",
          flush=True)
    return result, pnl_net


# ── K276b PnL Loader ──────────────────────────────────────────────────────────
def load_k276b_pnl() -> pd.Series:
    try:
        fp = BASE / "wave_k276_curves.json"
        with open(fp) as f:
            d = json.load(f)
        b  = d["K276b_top20"]
        dates = pd.to_datetime(b["dates"])
        return pd.Series(b["pnl"], index=dates).dropna()
    except Exception as e:
        print(f"  WARNING: Could not load K276b curves: {e}")
        return pd.Series(dtype=float)


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    print("=" * 60)
    print("Wave K294 — K270 dYdX Low-OI Symbol Trim Analysis")
    print("=" * 60)

    # 1. Load FR panel
    fr_panel = load_fr_panel()

    # 2. Coverage analysis
    coverage = coverage_analysis(fr_panel)
    low_oi_syms = [r["symbol"] for r in coverage if r["low_oi_flag"]]
    print(f"\nLow-OI symbols flagged ({len(low_oi_syms)}): {low_oi_syms}")

    # 3. Compute K270 baseline (all 30)
    print("\nComputing K270 baseline (all 30)...", flush=True)
    sig      = compute_signal(fr_panel)
    w_full   = compute_weights(sig)
    pnl_full, pnl_gross_full = compute_pnl(fr_panel, w_full)
    baseline_metrics  = metrics(pnl_full.values)
    baseline_wf       = walk_forward(pnl_full)
    print(f"  Baseline Sh={baseline_metrics['sharpe']:.4f} "
          f"(expected ~{K270_FULL_SHARPE:.4f})")

    # 4. Per-symbol Sharpe contribution
    contributions = per_symbol_contribution(fr_panel, sig, pnl_full)

    # 5. Build trimmed subsets
    ranked_syms = [r["symbol"] for r in contributions]  # best first

    k294a_syms = ranked_syms[:20]   # top 20
    k294b_syms = ranked_syms[:15]   # top 15
    k294c_syms = ranked_syms[:25]   # excl bottom 5

    # 6. Load K276b for correlation
    k276b_pnl = load_k276b_pnl()

    # 7. Run trimmed variants
    print("\nRunning trimmed variants...", flush=True)
    results   = {}
    curves    = {}

    # Baseline
    results["K270_baseline"] = {
        "name": "K270_baseline",
        "n_symbols": 30,
        "symbols": DYDX_SYMBOLS,
        "full_metrics": baseline_metrics,
        "walk_forward_folds": baseline_wf,
        "wf_summary": {
            "mean_sharpe": round(float(np.mean([f["sharpe"] for f in baseline_wf])), 4),
            "min_sharpe":  round(float(np.min([f["sharpe"] for f in baseline_wf])), 4),
            "all_positive": all(f["sharpe"] > 0 for f in baseline_wf),
        },
    }
    curves["K270_baseline"] = {
        "dates": [str(d.date()) for d in pnl_full.index],
        "pnl":   [round(v, 8) for v in pnl_full.values],
        "equity": [round(v, 8) for v in (1 + pnl_full).cumprod().values],
    }

    for name, subset in [("K294a_top20", k294a_syms),
                          ("K294b_top15", k294b_syms),
                          ("K294c_excl_bot5", k294c_syms)]:
        res, pnl_var = run_trimmed_variant(name, subset, fr_panel, sig, k276b_pnl)
        results[name] = res
        if len(pnl_var) > 0:
            curves[name] = {
                "dates":  [str(d.date()) for d in pnl_var.index],
                "pnl":    [round(v, 8) for v in pnl_var.values],
                "equity": [round(v, 8) for v in (1 + pnl_var).cumprod().values],
            }

    # 8. Find best variant
    variant_names = ["K294a_top20", "K294b_top15", "K294c_excl_bot5"]
    best_name = max(variant_names,
                    key=lambda n: results[n].get("full_metrics", {}).get("sharpe", -99))
    best_result = results[best_name]

    # 9. K287d Satellite integration projection
    best_sh   = best_result.get("full_metrics", {}).get("sharpe", 0)
    k270_sh   = K270_FULL_SHARPE
    improvement = best_sh - k270_sh
    satellite_verdict = (
        "UPGRADE_RECOMMENDED"
        if (improvement >= ACCEPTANCE_DELTA
            and best_result.get("wf_summary", {}).get("all_positive", False)
            and (best_result.get("rho_k276b") is None
                 or abs(best_result.get("rho_k276b", 1.0)) < 0.4))
        else "KEEP_CURRENT_K270"
    )

    # 10. Assemble output JSON
    runtime = time.time() - START_TIME
    output = {
        "wave": "K294",
        "strategy": "K270_dYdX_Trim_Analysis",
        "as_of": pd.Timestamp.utcnow().isoformat(),
        "runtime_s": round(runtime, 1),
        "config": {
            "zero_fr_threshold":     ZERO_FR_THRESH,
            "low_oi_zero_pct_thresh": LOW_OI_ZERO_PCT_THRESH,
            "low_oi_carry_thresh_ann_pct": LOW_OI_CARRY_THRESH,
            "acceptance_delta_sh":   ACCEPTANCE_DELTA,
        },
        "coverage_table":     coverage,
        "low_oi_symbols":     low_oi_syms,
        "per_symbol_contributions": contributions,
        "k270_baseline":      results["K270_baseline"],
        "variants": {
            "K294a_top20":       results.get("K294a_top20"),
            "K294b_top15":       results.get("K294b_top15"),
            "K294c_excl_bot5":   results.get("K294c_excl_bot5"),
        },
        "best_variant":       best_name,
        "best_sh_improvement": round(improvement, 4),
        "acceptance_gates": best_result.get("acceptance", {}),
        "satellite_verdict":  satellite_verdict,
        "k287d_projection": {
            "action": satellite_verdict,
            "replace_k270_with": best_name if satellite_verdict == "UPGRADE_RECOMMENDED" else "K270",
            "expected_sh_gain":  round(improvement, 4),
            "n_symbols_reduction": 30 - best_result.get("n_symbols", 30),
        },
    }

    # 11. Write JSON outputs
    with open(OUT_JSON, "w") as f:
        json.dump(output, f, indent=2, default=str)
    print(f"\nSaved: {OUT_JSON}")

    curves_out = {
        "wave": "K294",
        "description": "K270 baseline + trim variants equity curves",
    }
    curves_out.update(curves)
    with open(OUT_CURVES, "w") as f:
        json.dump(curves_out, f, indent=2)
    print(f"Saved: {OUT_CURVES}")

    # 12. Write markdown report
    _write_md(output, contributions, coverage)
    print(f"Saved: {OUT_MD}")
    print(f"\nDone in {runtime:.1f}s")
    return output


def _write_md(output: dict, contributions: list, coverage: list):
    lines = []
    lines.append("# Wave K294 — K270 dYdX Low-OI Symbol Trim")
    lines.append(f"*Generated: {pd.Timestamp.now('Asia/Tokyo').strftime('%Y-%m-%d %H:%M JST')}*")
    lines.append("")

    lines.append("## Coverage Table (30 symbols, sorted by % zero FR)")
    lines.append("| # | Symbol | Days | Zero Days | %Zero | MeanAbsFR | AnnCarry% | Low-OI? |")
    lines.append("|---|--------|------|-----------|-------|-----------|-----------|---------|")
    for i, r in enumerate(coverage, 1):
        flag = "YES" if r["low_oi_flag"] else "-"
        lines.append(
            f"| {i} | {r['symbol']} | {r['n_days']} | {r['zero_days']} | "
            f"{r['pct_zero']:.1%} | {r['mean_abs_fr']:.6f} | {r['ann_carry_pct']:.2f}% | {flag} |"
        )
    lines.append("")

    low_oi = output["low_oi_symbols"]
    lines.append(f"**Low-OI symbols ({len(low_oi)}):** {', '.join(low_oi) if low_oi else 'None'}")
    lines.append("")

    lines.append("## Per-Symbol Sharpe Contribution (ranked)")
    lines.append("| Rank | Symbol | MarginalSh | Sh-Without |")
    lines.append("|------|--------|------------|------------|")
    for r in contributions:
        lines.append(
            f"| {r['rank']} | {r['symbol']} | {r['marginal_sharpe']:+.4f} | {r['sh_without']:.4f} |"
        )
    lines.append("")

    lines.append("## K294 Variant Performance")
    lines.append("| Variant | N | Full Sh | WF Min Sh | WF All+ | ρ K276b | Δ vs K270 |")
    lines.append("|---------|---|---------|-----------|---------|---------|-----------|")
    baseline_sh = output["k270_baseline"]["full_metrics"]["sharpe"]
    lines.append(
        f"| K270_baseline | 30 | {baseline_sh:.4f} | "
        f"{output['k270_baseline']['wf_summary']['min_sharpe']:.4f} | "
        f"{'✓' if output['k270_baseline']['wf_summary']['all_positive'] else '✗'} | — | — |"
    )
    for vname in ["K294a_top20", "K294b_top15", "K294c_excl_bot5"]:
        v = output["variants"].get(vname)
        if not v or "error" in v:
            continue
        delta = v["full_metrics"]["sharpe"] - baseline_sh
        lines.append(
            f"| {vname} | {v['n_symbols']} | {v['full_metrics']['sharpe']:.4f} | "
            f"{v['wf_summary']['min_sharpe']:.4f} | "
            f"{'✓' if v['wf_summary']['all_positive'] else '✗'} | "
            f"{v['rho_k276b']} | {delta:+.4f} |"
        )
    lines.append("")

    lines.append("## K287d Satellite Integration Projection")
    proj = output["k287d_projection"]
    lines.append(f"- **Best variant:** `{output['best_variant']}`")
    lines.append(f"- **Sh improvement:** {output['best_sh_improvement']:+.4f}")
    lines.append(f"- **Symbol reduction:** 30 → {30 - proj['n_symbols_reduction']}")
    lines.append(f"- **Verdict:** `{output['satellite_verdict']}`")
    lines.append("")

    lines.append("## Verdict on K270 Trim Feasibility")
    gates = output.get("acceptance_gates", {})
    verdict = output["satellite_verdict"]
    lines.append(f"- Sh > K270 + 1.0: {'PASS' if gates.get('sh_gt_baseline_plus1') else 'FAIL'}")
    lines.append(f"- WF all folds positive: {'PASS' if gates.get('wf_all_positive') else 'FAIL'}")
    lines.append(f"- ρ vs K276b < 0.4: {'PASS' if gates.get('rho_k276b_lt_0.4') else 'FAIL'}")
    lines.append(f"- **Final verdict: {verdict}**")

    if verdict == "UPGRADE_RECOMMENDED":
        lines.append("")
        lines.append(
            "> Trimming K270 improves both Sharpe and operational simplicity. "
            f"Recommend replacing K270 (30 symbols) with {output['best_variant']} "
            f"in K287d Satellite allocation."
        )
    else:
        lines.append("")
        lines.append(
            "> Trimming K270 does not meet the +1.0 Sharpe acceptance threshold. "
            "Current 30-symbol K270 remains the preferred configuration."
        )

    OUT_MD.write_text("\n".join(lines))


if __name__ == "__main__":
    main()
