"""
Wave K273 — HL Long-Tail FR Short-Only Carry
=============================================
Hypothesis:
  K265 uses L/S dollar-neutral FR carry. K273 tests if the SHORT sleeve alone
  (high-FR symbols, receiving carry from longs) produces distinct alpha.

  Short-only differs from K265 (L/S neutral) in:
  - No long sleeve → directional short bias
  - Only top-quartile FR symbols → concentrated carry receiver
  - Correlation profile changes: net short = different market beta

Strategy:
  1. Universe: same HL longtail cache/hl_longtail_fr_daily.parquet (35 symbols)
  2. Signal: 14-day rolling mean of daily FR (same as K265)
  3. SHORT-ONLY: top quartile (highest FR) — no long sleeve
  4. Equal weight within short sleeve (-1/n per symbol)
  5. Daily rebalance, 2bp/side maker
  6. Walk-forward 4-fold on K272a window

Acceptance gates (K273 → K274 K272a integration):
  - WF all folds positive AND Sh >= 7 each fold
  - |rho| < 0.4 with K272a components (K198/K208/K265)
  - Mechanism distinct (short-only vs L/S neutral)

Runtime: <12 min (uses cached parquet, no new API calls).
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
BASE    = Path("/Users/nekonaomichi/crypto-lab")
CACHE   = BASE / "cache"

# ── Config ───────────────────────────────────────────────────────────────────
FR_WINDOW_DAYS = 14       # rolling mean window (same as K265)
QUARTILE       = 0.25     # top 25% for short sleeve
COST_BPS       = 2.0      # 2bp per side maker
COST_RATE      = COST_BPS / 1e4
PPY            = 365.0
N_FOLDS        = 4

OUT_JSON   = BASE / "wave_k273_short_only_fr.json"
OUT_CURVES = BASE / "wave_k273_curves.json"
OUT_MD     = BASE / "wave_k273_short_only_fr.md"
PARQUET_IN = CACHE / "hl_longtail_fr_daily.parquet"


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


# ── Signal (same as K265) ─────────────────────────────────────────────────────
def compute_signal(fr_panel: pd.DataFrame) -> pd.DataFrame:
    """14d rolling mean of daily FR, shifted +1 to avoid look-ahead."""
    roll = fr_panel.rolling(window=FR_WINDOW_DAYS, min_periods=7).mean()
    return roll.shift(1)


# ── SHORT-ONLY Weights ────────────────────────────────────────────────────────
def short_only_weights(sig_row: pd.Series) -> pd.Series:
    """
    K273 SHORT-ONLY:
      FR > 0: longs pay shorts → SHORT receives positive carry
      Take top quartile (highest FR signal) as equal-weight shorts.
      No long sleeve (key difference from K265).

    Weight convention: negative = short position.
    Each short gets weight = -1/n_shorts so gross exposure = 1.0.
    """
    valid = sig_row.dropna()
    n_sym = len(valid)
    if n_sym < 4:
        return pd.Series(0.0, index=sig_row.index)

    n_q   = max(1, int(n_sym * QUARTILE))
    ranked = valid.rank(ascending=True)

    # Short: top ranked (most positive FR) → rank n-n_q+1..n
    shorts = ranked[ranked > n_sym - n_q].index

    w = pd.Series(0.0, index=sig_row.index)
    if len(shorts) > 0:
        w[shorts] = -1.0 / len(shorts)   # negative = short
    return w


def compute_weights(sig: pd.DataFrame) -> pd.DataFrame:
    return sig.apply(short_only_weights, axis=1)


# ── PnL ──────────────────────────────────────────────────────────────────────
def compute_pnl(
    fr_panel: pd.DataFrame,
    weights: pd.DataFrame,
) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """
    Pure FR carry PnL (no price return).
    PnL per day = sum_i( -w_i * fr_daily_i )
      w_i < 0 (short), fr_daily_i > 0 → PnL > 0 (we receive carry from longs)
    daily FR = daily_mean * 24 events/day (HL hourly settlements).
    """
    common = fr_panel.index.intersection(weights.index)
    fr_c   = fr_panel.loc[common]
    w_c    = weights.loc[common]

    # Lag weights: execute at close t-1, settle on day t
    w_lag = w_c.shift(1).fillna(0.0)

    # HL daily total FR = mean_hourly * 24
    fr_daily = fr_c * 24.0

    # Carry PnL
    pnl_fr = (-w_lag * fr_daily).sum(axis=1)

    # Turnover cost
    turn   = (w_c - w_c.shift(1).fillna(0.0)).abs().sum(axis=1)
    cost   = turn * COST_RATE

    pnl_net   = pnl_fr - cost
    pnl_gross = pnl_fr
    return pnl_net, pnl_gross, turn


# ── Walk-Forward 4-Fold ───────────────────────────────────────────────────────
def walk_forward(pnl: pd.Series) -> List[Dict]:
    n         = len(pnl)
    fold_size = n // N_FOLDS
    folds     = []
    for i in range(N_FOLDS):
        s = i * fold_size
        e = s + fold_size if i < N_FOLDS - 1 else n
        fold_ret = pnl.iloc[s:e].values
        fold_m   = metrics(fold_ret)
        fold_m["fold"]  = i
        fold_m["start"] = str(pnl.index[s].date())
        fold_m["end"]   = str(pnl.index[e - 1].date())
        folds.append(fold_m)
    return folds


# ── Correlation vs K272a Components ──────────────────────────────────────────
def compute_correlations(pnl_k273: pd.Series) -> Dict:
    """
    Compute rho with K198, K208, K265 (K272a components).
    Also compute rho with K265 explicitly (same universe, different sleeve).
    """
    corrs = {}

    # K198: pnl_ridge from wave_k198_curves.json
    try:
        with open(BASE / "wave_k198_curves.json") as f:
            d = json.load(f)
        dates = pd.to_datetime(d["dates_ml"])
        pnl   = pd.Series(d["pnl_ridge"], index=dates).dropna()
        common = pnl.index.intersection(pnl_k273.index)
        if len(common) > 30:
            corrs["K198"] = round(float(np.corrcoef(
                pnl.loc[common].values, pnl_k273.loc[common].values)[0, 1]), 4)
        else:
            corrs["K198"] = None
    except Exception as e:
        corrs["K198"] = f"error: {e}"

    # K208: aggregate 8h events to daily
    try:
        with open(BASE / "wave_k208_curves.json") as f:
            d = json.load(f)
        k208_data = d["K208_filtered"]
        ts    = pd.to_datetime(k208_data["timestamps"])
        cum   = np.array(k208_data["cumulative_pnl"])
        s8    = pd.Series(np.diff(cum, prepend=cum[0]), index=ts)
        pnl   = s8.groupby(s8.index.normalize()).sum()
        pnl.index = pd.to_datetime(pnl.index)
        common = pnl.index.intersection(pnl_k273.index)
        if len(common) > 30:
            corrs["K208"] = round(float(np.corrcoef(
                pnl.loc[common].values, pnl_k273.loc[common].values)[0, 1]), 4)
        else:
            corrs["K208"] = None
    except Exception as e:
        corrs["K208"] = f"error: {e}"

    # K265: daily pnl from wave_k265_curves.json
    try:
        with open(BASE / "wave_k265_curves.json") as f:
            d = json.load(f)
        dates = pd.to_datetime(d["dates"])
        pnl   = pd.Series(d["pnl"], index=dates).dropna()
        common = pnl.index.intersection(pnl_k273.index)
        if len(common) > 30:
            corrs["K265"] = round(float(np.corrcoef(
                pnl.loc[common].values, pnl_k273.loc[common].values)[0, 1]), 4)
        else:
            corrs["K265"] = None
    except Exception as e:
        corrs["K265"] = f"error: {e}"

    return corrs


# ── Short sleeve activity stats ───────────────────────────────────────────────
def sleeve_stats(weights: pd.DataFrame) -> Dict:
    """Count avg number of shorts per day, gross exposure, etc."""
    short_mask = weights < 0
    n_short_per_day = short_mask.sum(axis=1)
    gross_exp = weights.abs().sum(axis=1)  # should ≈ 1.0 always

    # Symbols appearing in short sleeve
    short_freq = short_mask.sum() / len(weights)
    top_short_syms = short_freq.sort_values(ascending=False).head(10)

    return {
        "avg_n_shorts_per_day":  round(float(n_short_per_day.mean()), 2),
        "avg_gross_exposure":    round(float(gross_exp.mean()), 4),
        "top_short_symbols":     {k: round(float(v), 3)
                                  for k, v in top_short_syms.items()},
    }


# ── Main ──────────────────────────────────────────────────────────────────────
def main() -> None:
    print("=" * 60)
    print("Wave K273 — HL Long-Tail FR Short-Only Carry")
    print("=" * 60)

    # 1. Load cached daily FR panel (built by K265)
    print(f"\n[K273] Loading cached FR panel from {PARQUET_IN}...")
    fr_panel = pd.read_parquet(PARQUET_IN)
    fr_panel.index = pd.to_datetime(fr_panel.index)
    print(f"  Panel shape: {fr_panel.shape}")
    print(f"  Date range: {fr_panel.index[0].date()} → {fr_panel.index[-1].date()}")
    print(f"  Symbols: {list(fr_panel.columns)}")

    # 2. Compute signal (same as K265)
    sig     = compute_signal(fr_panel)
    weights = compute_weights(sig)

    # 3. Sleeve stats
    sl_stats = sleeve_stats(weights)
    print(f"\n[K273] Short sleeve: avg {sl_stats['avg_n_shorts_per_day']:.1f} symbols/day "
          f"| gross_exp={sl_stats['avg_gross_exposure']:.3f}")
    print(f"  Top short symbols: {list(sl_stats['top_short_symbols'].keys())}")

    # 4. Compute PnL
    pnl_net, pnl_gross, turnover = compute_pnl(fr_panel, weights)
    pnl_net   = pnl_net.dropna()
    pnl_gross = pnl_gross.dropna()

    n_total = len(pnl_net)
    n_oos   = int(n_total * 0.30)
    n_is    = n_total - n_oos

    is_ret  = pnl_net.iloc[:n_is].values
    oos_ret = pnl_net.iloc[n_is:].values
    all_ret = pnl_net.values

    is_m    = metrics(is_ret)
    oos_m   = metrics(oos_ret)
    full_m  = metrics(all_ret)
    gross_m = metrics(pnl_gross.values)

    print(f"\n[K273] Performance:")
    print(f"  IS    Sh={is_m['sharpe']:.3f}  MDD={is_m['max_dd']:.2%}  AnnRet={is_m['ann_ret']:.2%}")
    print(f"  OOS   Sh={oos_m['sharpe']:.3f}  MDD={oos_m['max_dd']:.2%}  AnnRet={oos_m['ann_ret']:.2%}")
    print(f"  Full  Sh={full_m['sharpe']:.3f}  MDD={full_m['max_dd']:.2%}  AnnRet={full_m['ann_ret']:.2%}")

    # 5. Walk-forward 4-fold
    wf_folds = walk_forward(pnl_net)
    wf_sharpes = [f["sharpe"] for f in wf_folds]
    wf_summary = {
        "mean_sharpe":  round(float(np.mean(wf_sharpes)), 4),
        "min_sharpe":   round(float(np.min(wf_sharpes)), 4),
        "all_positive": bool(all(s > 0 for s in wf_sharpes)),
        "all_gte_7":    bool(all(s >= 7.0 for s in wf_sharpes)),
    }

    print(f"\n[K273] Walk-Forward 4-Fold:")
    for fld in wf_folds:
        print(f"  Fold {fld['fold']} ({fld['start']} → {fld['end']}): "
              f"Sh={fld['sharpe']:.3f}  MDD={fld['max_dd']:.2%}  AnnRet={fld['ann_ret']:.2%}")
    print(f"  Summary: mean_Sh={wf_summary['mean_sharpe']:.3f}  "
          f"min_Sh={wf_summary['min_sharpe']:.3f}  "
          f"all_pos={wf_summary['all_positive']}  all_gte_7={wf_summary['all_gte_7']}")

    # 6. Correlations vs K272a components (K198, K208, K265)
    corrs = compute_correlations(pnl_net)
    print(f"\n[K273] Correlations:")
    for k, v in corrs.items():
        print(f"  rho(K273, {k}) = {v}")

    # 7. Acceptance gates
    def rho_ok(key: str) -> bool:
        v = corrs.get(key)
        return isinstance(v, float) and abs(v) < 0.4

    gates = {
        "G1_WF_all_folds_positive":      wf_summary["all_positive"],
        "G2_WF_all_folds_Sh_gte_7":      wf_summary["all_gte_7"],
        "G3_OOS_Sharpe_gte_7":           oos_m["sharpe"] >= 7.0,
        "G4_rho_K198_lt_0.4":            rho_ok("K198"),
        "G5_rho_K208_lt_0.4":            rho_ok("K208"),
        "G6_rho_K265_lt_0.4":            rho_ok("K265"),
    }
    n_pass = sum(1 for v in gates.values() if v is True)
    verdict = "ACCEPT" if all(gates.values()) else "REJECT"
    print(f"\n[K273] Gates passed: {n_pass}/{len(gates)}  →  {verdict}")
    for k, v in gates.items():
        print(f"  {'PASS' if v else 'FAIL'} {k}")

    # 8. Save curves JSON
    curves = {
        "wave":   "K273",
        "dates":  [str(d.date()) for d in pnl_net.index],
        "equity": [round(float(v), 6) for v in np.cumprod(1 + pnl_net.values)],
        "pnl":    [round(float(v), 8) for v in pnl_net.values],
        "gross_pnl": [round(float(v), 8) for v in pnl_gross.values],
    }
    with open(OUT_CURVES, "w") as f:
        json.dump(curves, f, indent=2)
    print(f"\n[K273] Saved curves → {OUT_CURVES}")

    # 9. Build fold details
    fold_list = []
    for fld in wf_folds:
        fold_list.append({
            "fold":         fld["fold"],
            "start":        fld["start"],
            "end":          fld["end"],
            "sharpe":       round(fld["sharpe"],     4),
            "max_dd":       round(fld["max_dd"],     6),
            "ann_ret":      round(fld["ann_ret"],    4),
            "ann_vol":      round(fld["ann_vol"],    4),
            "win_rate":     round(fld["win_rate"],   4),
            "total_return": round(fld["total_return"], 6),
            "n_days":       fld["n_days"],
        })

    # 10. Save main JSON
    avg_turn = float(turnover.mean())
    output = {
        "wave":     "K273",
        "strategy": "HL_LongTail_FR_ShortOnly",
        "as_of":    pd.Timestamp.utcnow().isoformat(),
        "runtime_s": round(time.time() - START_TIME, 1),
        "config": {
            "n_symbols":            len(fr_panel.columns),
            "symbols":              list(fr_panel.columns),
            "fr_window_days":       FR_WINDOW_DAYS,
            "quartile":             QUARTILE,
            "cost_bps_per_side":    COST_BPS,
            "rebalance":            "daily",
            "sleeve":               "short_only",
        },
        "sleeve_stats":     sl_stats,
        "is_metrics":       {k: round(v, 6) if isinstance(v, float) else v
                             for k, v in is_m.items()},
        "oos_metrics":      {k: round(v, 6) if isinstance(v, float) else v
                             for k, v in oos_m.items()},
        "full_metrics":     {k: round(v, 6) if isinstance(v, float) else v
                             for k, v in full_m.items()},
        "gross_metrics":    {k: round(v, 6) if isinstance(v, float) else v
                             for k, v in gross_m.items()},
        "walk_forward_folds": fold_list,
        "wf_summary":       wf_summary,
        "turnover": {
            "avg_daily":            round(avg_turn, 6),
            "implied_cost_pct_day": round(avg_turn * COST_RATE, 8),
        },
        "correlations":   corrs,
        "gates":          gates,
        "n_gates_passed": n_pass,
        "verdict":        verdict,
        "date_range": {
            "start":        str(pnl_net.index[0].date()),
            "end":          str(pnl_net.index[-1].date()),
            "is_end":       str(pnl_net.index[n_is - 1].date()),
            "oos_start":    str(pnl_net.index[n_is].date()),
            "n_days_total": n_total,
            "n_days_is":    n_is,
            "n_days_oos":   n_oos,
        },
        "comparison_vs_k265": {
            "k265_oos_sharpe": 13.10,
            "k273_oos_sharpe": round(oos_m["sharpe"], 3),
            "k273_vs_k265_rho": corrs.get("K265"),
            "mechanism_difference": "K273=short_only_carry_receiver; K265=L/S_neutral_FR_arb",
        },
    }

    with open(OUT_JSON, "w") as f:
        json.dump(output, f, indent=2)
    print(f"[K273] Saved metrics → {OUT_JSON}")

    # 11. Write markdown report
    write_report(output, wf_folds, corrs, gates, n_pass, verdict)
    print(f"[K273] Total runtime: {time.time() - START_TIME:.1f}s")


def write_report(output, wf_folds, corrs, gates, n_pass, verdict) -> None:
    oos  = output["oos_metrics"]
    is_  = output["is_metrics"]
    full = output["full_metrics"]
    wfs  = output["wf_summary"]
    sl   = output["sleeve_stats"]
    dr   = output["date_range"]
    comp = output["comparison_vs_k265"]

    lines = [
        f"# Wave K273 — HL Long-Tail FR Short-Only Carry",
        f"",
        f"**Date:** {output['as_of'][:10]}  |  **Runtime:** {output['runtime_s']:.0f}s",
        f"",
        f"## Objective",
        f"Test if K265's short sleeve alone (short high-FR symbols, no long sleeve) produces",
        f"distinct alpha vs the full L/S strategy. Universe identical: 35 HL longtail symbols.",
        f"Key difference: no long arm → directional short bias, concentrated carry.",
        f"",
        f"## Configuration",
        f"- Universe: {output['config']['n_symbols']} symbols ({', '.join(output['config']['symbols'][:10])}...)",
        f"- Signal: 14d rolling mean daily FR (shifted +1 day, no look-ahead)",
        f"- Sleeve: SHORT-ONLY top quartile ({output['config']['quartile']:.0%}) by FR",
        f"- Avg shorts per day: {sl['avg_n_shorts_per_day']:.1f}",
        f"- Top short symbols: {', '.join(list(sl['top_short_symbols'].keys()))}",
        f"- Rebalance: daily | Cost: {output['config']['cost_bps_per_side']}bp/side",
        f"",
        f"## Strategy Performance",
        f"| Period | Sharpe | MaxDD | AnnRet | WinRate |",
        f"|--------|--------|-------|--------|---------|",
        f"| IS     | {is_['sharpe']:.3f} | {is_['max_dd']:.2%} | {is_['ann_ret']:.2%} | {is_['win_rate']:.1%} |",
        f"| OOS    | {oos['sharpe']:.3f} | {oos['max_dd']:.2%} | {oos['ann_ret']:.2%} | {oos['win_rate']:.1%} |",
        f"| Full   | {full['sharpe']:.3f} | {full['max_dd']:.2%} | {full['ann_ret']:.2%} | {full['win_rate']:.1%} |",
        f"",
        f"## Walk-Forward 4-Fold",
        f"| Fold | Period | Sharpe | MaxDD | AnnRet | Win% |",
        f"|------|--------|--------|-------|--------|------|",
    ]

    for fld in wf_folds:
        lines.append(
            f"| {fld['fold']} | {fld['start']} → {fld['end']} | "
            f"{fld['sharpe']:.3f} | {fld['max_dd']:.2%} | {fld['ann_ret']:.2%} | {fld['win_rate']:.1%} |"
        )

    lines += [
        f"",
        f"**WF Summary:** mean_Sh={wfs['mean_sharpe']:.3f}  min_Sh={wfs['min_sharpe']:.3f}  "
        f"all_positive={wfs['all_positive']}  all_Sh_gte_7={wfs['all_gte_7']}",
        f"",
        f"## Correlation Matrix vs K272a Components",
        f"| Component | rho | |rho|<0.4? | Notes |",
        f"|-----------|-----|--------|-------|",
    ]

    rho_notes = {
        "K198": "ML allocator (regime-based)",
        "K208": "CEX-DEX reverse carry (majors)",
        "K265": "HL L/S FR carry (same universe)",
    }
    for k, note in rho_notes.items():
        v = corrs.get(k)
        ok = isinstance(v, float) and abs(v) < 0.4
        lines.append(f"| {k} | {v} | {'YES' if ok else 'NO'} | {note} |")

    k265_rho = corrs.get("K265")
    if isinstance(k265_rho, float) and abs(k265_rho) > 0.6:
        rho_warn = "WARNING: rho > 0.6 with K265 — not orthogonal"
    elif isinstance(k265_rho, float) and abs(k265_rho) > 0.4:
        rho_warn = "CAUTION: rho 0.4-0.6 with K265 — borderline orthogonality"
    else:
        rho_warn = "OK: |rho| < 0.4 with K265 — orthogonal"
    lines.append(f"")
    lines.append(f"**K265 orthogonality:** {rho_warn}")

    lines += [
        f"",
        f"## Comparison: K273 Short-Only vs K265 L/S",
        f"| Metric | K265 L/S | K273 Short-Only |",
        f"|--------|----------|-----------------|",
        f"| OOS Sharpe | {comp['k265_oos_sharpe']:.2f} | {comp['k273_oos_sharpe']:.3f} |",
        f"| WF min Sh | 10.1 | {wfs['min_sharpe']:.3f} |",
        f"| rho(K273,K265) | — | {comp['k273_vs_k265_rho']} |",
        f"| Mechanism | L/S neutral | Short-only bias |",
        f"| Sleeves | 2 (long+short) | 1 (short only) |",
        f"",
        f"## Acceptance Gates ({n_pass}/{len(gates)} passed)",
        f"| Gate | Status |",
        f"|------|--------|",
    ]
    for k, v in gates.items():
        lines.append(f"| {k} | {'PASS' if v else 'FAIL'} |")

    lines += [
        f"",
        f"## Verdict: {verdict}",
        f"",
    ]

    if verdict == "ACCEPT":
        lines += [
            f"### K274 K272a Integration Plan",
            f"K273 qualifies for addition to K272a (3-way → 4-way).",
            f"- Mechanism: Short-only HL longtail FR carry (orthogonal to K208 + distinct from K265)",
            f"- Allocation: equal-weight slot alongside K198/K208/K265",
            f"- Live: HL perp maker shorts at daily rebalance, 2bp cost",
            f"- Monitor: correlation with K265 monthly (same universe, divergence may increase)",
        ]
    else:
        failed = [k for k, v in gates.items() if not v]
        lines += [
            f"### Failure Analysis",
            f"Failed gates: {', '.join(failed)}",
            f"",
            f"### Interpretation",
        ]
        if any("rho_K265" in g for g in failed):
            lines.append(
                f"- High correlation with K265 expected: same universe + overlapping signal."
            )
            lines.append(
                f"  Short-only is just a sleeve subset of L/S — not independent alpha."
            )
        if any("Sh_gte_7" in g or "Sharpe_gte_7" in g for g in failed):
            lines.append(
                f"- Without long sleeve, carry is halved. Sharpe degradation expected."
            )
        lines += [
            f"",
            f"### Next Steps",
            f"- K274: Combine K273 short + independent long signal (e.g., momentum/vol-filter)",
            f"- Or: use K273 within K265's long sleeve as an enhancement rather than standalone",
            f"- Or: proceed with K272a as-is (K198+K208+K265 already accepted)",
        ]

    with open(OUT_MD, "w") as f:
        f.write("\n".join(lines) + "\n")
    print(f"[K273] Saved report → {OUT_MD}")


if __name__ == "__main__":
    main()
