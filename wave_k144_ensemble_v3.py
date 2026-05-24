"""Wave K144 — K136 Ensemble v3 with K142 Integration

Tests whether adding K142 basis-vol-sort (V_30d_top5 variant) to the existing
6-strategy K136 ensemble improves portfolio risk-adjusted metrics, or if K142's
CONDITIONAL status (DSR_oos = 0.39, fails strict 0.50 DSR gate) dilutes
ensemble robustness.

7-strategy lineup:
  1. v4.1   wave_k109_curves.json series['v4.1']
  2. V1     wave_k109_curves.json series['V1']
  3. K114   wave_k114_alcp.json    curves['full_equity']
  4. K116   wave_k116_curves.json  portfolio_equity
  5. K121   wave_k121_curves.json  weekend_ls
  6. K133   wave_k133_curves.json  V_rev_3d_z15
  7. K142   wave_k142_curves.json  V_30d_top5 (NEW — CONDITIONAL/borderline)

Diagnostic: K142 vs K137 V_basis_7d_top3 (both basis-related). K137 was NOT
selected for K136 — so check if K142 brings genuinely orthogonal info or is
just a "better K137".

K142's K124-style scoring:
  OOS Sharpe +1.49  perm p=0.010  DSR_oos=0.39 (fails 0.50 strict cut)

Portfolios: P1 equal, P2 inv-vol, P3 risk-parity, P5 sharpe-weighted.
K121 retains 30% cap.
"""
from __future__ import annotations

import json
import math
from datetime import datetime
from pathlib import Path
from typing import Dict, List

import numpy as np
import pandas as pd

BASE = Path("/Users/nekonaomichi/crypto-lab")
TRADING_DAYS = 365
OOS_FRAC = 0.30


# -------------------- Loaders --------------------

def load_v41_and_v1() -> pd.DataFrame:
    with open(BASE / "wave_k109_curves.json") as fp:
        d = json.load(fp)
    dates = pd.to_datetime(d["dates"])
    df = pd.DataFrame({"date": dates})
    for name in ("v4.1", "V1"):
        cum = np.asarray(d["series"][name], dtype=float)
        eq = 1.0 + cum
        eq_prev = np.r_[1.0, eq[:-1]]
        ret = eq / eq_prev - 1.0
        df[name] = ret
    df = df.set_index("date")
    return df


def _equity_to_daily_returns(ts_iso: List[str], eq: List[float]) -> pd.Series:
    ts = (
        pd.to_datetime(ts_iso, utc=True).tz_convert(None)
        if pd.to_datetime(ts_iso[0]).tzinfo
        else pd.to_datetime(ts_iso)
    )
    s = pd.Series(eq, index=ts).sort_index()
    daily_eq = s.resample("1D").last().ffill()
    daily_ret = daily_eq.pct_change().fillna(0.0)
    return daily_ret


def load_k114() -> pd.Series:
    with open(BASE / "wave_k114_alcp.json") as fp:
        d = json.load(fp)
    curve = d["curves"]["full_equity"]
    s = _equity_to_daily_returns(list(curve.keys()), list(curve.values()))
    s.name = "K114"
    return s


def load_k116() -> pd.Series:
    with open(BASE / "wave_k116_curves.json") as fp:
        d = json.load(fp)
    s = _equity_to_daily_returns(d["timestamps"], d["portfolio_equity"])
    s.name = "K116"
    return s


def load_k121() -> pd.Series:
    with open(BASE / "wave_k121_curves.json") as fp:
        d = json.load(fp)
    pts = d["weekend_ls"]
    s = _equity_to_daily_returns([p["ts"] for p in pts], [p["eq"] for p in pts])
    s.name = "K121"
    return s


def load_k133(variant: str = "V_rev_3d_z15") -> pd.Series:
    with open(BASE / "wave_k133_curves.json") as fp:
        d = json.load(fp)
    v = d[variant]
    s = _equity_to_daily_returns(v["equity_idx"], v["equity_curve"])
    s.name = "K133"
    return s


def load_k142(variant: str = "V_30d_top5") -> pd.Series:
    """K142 stores equity as cumulative simple return (starts at 0)."""
    with open(BASE / "wave_k142_curves.json") as fp:
        d = json.load(fp)
    v = d[variant]
    eq_net = np.asarray(v["equity_net"], dtype=float)
    eq = 1.0 + eq_net
    s = _equity_to_daily_returns(v["timestamps"], list(eq))
    s.name = "K142"
    return s


def load_k137(variant: str = "V_basis_7d_top3") -> pd.Series:
    """Diagnostic loader only — K137 not in ensemble."""
    with open(BASE / "wave_k137_curves.json") as fp:
        d = json.load(fp)
    v = d[variant]
    eq_net = np.asarray(v["equity_net"], dtype=float)
    eq = 1.0 + eq_net
    s = _equity_to_daily_returns(v["timestamps"], list(eq))
    s.name = "K137"
    return s


def assemble_returns_7() -> pd.DataFrame:
    df01 = load_v41_and_v1()
    if df01.index.tz is not None:
        df01.index = df01.index.tz_localize(None)
    s114 = load_k114()
    s116 = load_k116()
    s121 = load_k121()
    s133 = load_k133()
    s142 = load_k142()
    df = pd.concat(
        [
            df01[["v4.1"]], df01[["V1"]],
            s114.to_frame(), s116.to_frame(), s121.to_frame(),
            s133.to_frame(), s142.to_frame(),
        ],
        axis=1, join="inner",
    ).sort_index().dropna(how="any")
    return df


def assemble_returns_6_from_df(df7: pd.DataFrame) -> pd.DataFrame:
    """Re-build 6-strat (K136) panel on K144's aligned window for fair head-to-head."""
    return df7[["v4.1", "V1", "K114", "K116", "K121", "K133"]].copy()


# -------------------- Metrics --------------------

def sharpe(r: np.ndarray) -> float:
    if len(r) < 2 or r.std(ddof=1) == 0:
        return 0.0
    return float(r.mean() / r.std(ddof=1) * math.sqrt(TRADING_DAYS))


def sortino(r: np.ndarray) -> float:
    dn = r[r < 0]
    if len(dn) < 2 or dn.std(ddof=1) == 0:
        return 0.0
    return float(r.mean() / dn.std(ddof=1) * math.sqrt(TRADING_DAYS))


def max_dd(r: np.ndarray) -> float:
    eq = np.cumprod(1.0 + r)
    peak = np.maximum.accumulate(eq)
    return float((eq / peak - 1.0).min())


def calmar(r: np.ndarray) -> float:
    ann = (1.0 + r).prod() ** (TRADING_DAYS / max(1, len(r))) - 1.0
    mdd = max_dd(r)
    return float(ann / abs(mdd)) if mdd != 0 else 0.0


def metrics_pkg(r: np.ndarray) -> dict:
    if len(r) < 2:
        return {"sharpe": 0, "sortino": 0, "calmar": 0, "max_dd": 0,
                "ann_ret": 0, "ann_vol": 0, "n_days": int(len(r))}
    ann_ret = (1.0 + r).prod() ** (TRADING_DAYS / len(r)) - 1.0
    ann_vol = float(r.std(ddof=1) * math.sqrt(TRADING_DAYS))
    return {
        "sharpe":  round(sharpe(r), 4),
        "sortino": round(sortino(r), 4),
        "calmar":  round(calmar(r), 4),
        "max_dd":  round(max_dd(r), 4),
        "ann_ret": round(float(ann_ret), 4),
        "ann_vol": round(ann_vol, 4),
        "n_days":  int(len(r)),
    }


# -------------------- Weighting --------------------

def w_equal(n: int) -> np.ndarray:
    return np.ones(n) / n


def w_inv_vol(R: np.ndarray) -> np.ndarray:
    vols = R.std(axis=0, ddof=1)
    inv = 1.0 / np.where(vols == 0, np.nan, vols)
    return inv / np.nansum(inv)


def w_risk_parity(R: np.ndarray, n_iter: int = 5000, tol: float = 1e-9) -> np.ndarray:
    cov = np.cov(R, rowvar=False, ddof=1)
    n = cov.shape[0]
    w = np.ones(n) / n
    for _ in range(n_iter):
        mrc = cov @ w
        rc = w * mrc
        total_risk_sq = float(w @ cov @ w)
        target = total_risk_sq / n
        new_w = w * (target / np.where(rc == 0, 1e-12, rc)) ** 0.5
        new_w = np.clip(new_w, 1e-6, None)
        new_w = new_w / new_w.sum()
        if np.max(np.abs(new_w - w)) < tol:
            return new_w
        w = new_w
    return w


def w_sharpe(R: np.ndarray) -> np.ndarray:
    shs = np.array([sharpe(R[:, i]) for i in range(R.shape[1])])
    pos = np.clip(shs, 0, None)
    if pos.sum() == 0:
        return np.ones(R.shape[1]) / R.shape[1]
    return pos / pos.sum()


def apply_k121_cap(w: np.ndarray, cols: List[str], cap: float = 0.30) -> np.ndarray:
    w = w.copy()
    if "K121" not in cols:
        return w
    i = cols.index("K121")
    if w[i] <= cap:
        return w
    excess = w[i] - cap
    w[i] = cap
    other_mask = np.ones(len(w), dtype=bool)
    other_mask[i] = False
    others = w[other_mask]
    if others.sum() > 0:
        w[other_mask] = others + excess * (others / others.sum())
    return w / w.sum()


# -------------------- Diagnostics --------------------

def k142_vs_k137() -> dict:
    """K142 (basis-vol sort, 30d window, top5) vs K137 (basis-carry, 7d, top3).

    Both are basis-themed. If highly correlated, K142 brings little new info."""
    s142 = load_k142("V_30d_top5")
    s137 = load_k137("V_basis_7d_top3")
    df = pd.concat([s142, s137], axis=1, join="inner").dropna()
    if len(df) < 5:
        return {"pearson": None, "spearman": None, "n": int(len(df))}
    p = float(df["K142"].corr(df["K137"], method="pearson"))
    sp = float(df["K142"].corr(df["K137"], method="spearman"))
    return {"pearson": round(p, 4), "spearman": round(sp, 4), "n": int(len(df))}


# -------------------- Pipeline --------------------

def fit_variants(R: np.ndarray, cols: List[str]) -> Dict[str, np.ndarray]:
    return {
        "P1_equal":       w_equal(len(cols)),
        "P2_inv_vol":     w_inv_vol(R),
        "P3_risk_parity": w_risk_parity(R),
        "P5_sharpe_wt":   w_sharpe(R),
    }


def portfolio_block(
    df: pd.DataFrame, label: str, cut: int
) -> dict:
    """Compute full/OOS portfolio metrics (uncapped + cap30) for given panel."""
    cols = list(df.columns)
    R = df.to_numpy()
    oos_R = R[cut:, :]

    variants = fit_variants(R, cols)
    variants_capped = {k: apply_k121_cap(w, cols) for k, w in variants.items()}

    single_full = {c: metrics_pkg(df[c].to_numpy()) for c in cols}
    single_oos = {c: metrics_pkg(R[cut:, i]) for i, c in enumerate(cols)}
    single_sh = np.array([single_full[c]["sharpe"] for c in cols])

    full_metrics, oos_metrics = {}, {}
    full_metrics_capped, oos_metrics_capped = {}, {}
    dr_full = {}
    curves_out = {c: list(np.cumprod(1.0 + df[c].to_numpy())) for c in cols}

    for name, w in variants.items():
        pr = R @ w
        m = metrics_pkg(pr)
        full_metrics[name] = m
        wavg = float((w * single_sh).sum())
        dr_full[name] = round(m["sharpe"] / wavg, 4) if wavg > 0 else None
        curves_out[name] = list(np.cumprod(1.0 + pr))
        oos_metrics[name] = metrics_pkg(oos_R @ w)

    for name, w in variants_capped.items():
        pr = R @ w
        full_metrics_capped[name] = metrics_pkg(pr)
        oos_metrics_capped[name] = metrics_pkg(oos_R @ w)
        curves_out[name + "_cap30"] = list(np.cumprod(1.0 + pr))

    return {
        "label": label,
        "cols": cols,
        "single_full": single_full,
        "single_oos": single_oos,
        "weights_uncapped": {k: [round(float(x), 4) for x in v.tolist()] for k, v in variants.items()},
        "weights_cap30":    {k: [round(float(x), 4) for x in v.tolist()] for k, v in variants_capped.items()},
        "full_uncapped": full_metrics,
        "full_cap30":    full_metrics_capped,
        "oos_uncapped":  oos_metrics,
        "oos_cap30":     oos_metrics_capped,
        "dr_full":       dr_full,
        "curves":        curves_out,
    }


def run_pipeline():
    df7 = assemble_returns_7()
    cols7 = list(df7.columns)
    print(f"K144 aligned daily returns: n={len(df7)}  cols={cols7}")
    print(f"Date range: {df7.index.min().date()} -> {df7.index.max().date()}")

    df6 = assemble_returns_6_from_df(df7)
    cols6 = list(df6.columns)

    R7 = df7.to_numpy()

    # Correlations 7x7
    corr_p = df7.corr(method="pearson").round(4)
    corr_s = df7.corr(method="spearman").round(4)
    print("\nPearson 7x7:")
    print(corr_p)

    # K142 vs K137 diagnostic
    diag_137 = k142_vs_k137()
    print(f"\nK142 vs K137 (both basis-themed): "
          f"Pearson={diag_137['pearson']}, Spearman={diag_137['spearman']}, n={diag_137['n']}")

    # K142 vs each other ensemble member
    print("\nK142 corr vs other 6 members:")
    for c in cols7:
        if c == "K142":
            continue
        p = corr_p.loc["K142", c]
        sp = corr_s.loc["K142", c]
        print(f"  K142 vs {c:6s}  Pearson={p:+.4f}  Spearman={sp:+.4f}")

    cut = int(len(df7) * (1 - OOS_FRAC))
    print(f"\nOOS cut idx: {cut}  OOS days: {len(df7) - cut}")

    # 7-strategy block (K144)
    blk7 = portfolio_block(df7, "K144_7strat", cut)
    # 6-strategy block (K136) on identical aligned window for apples-to-apples
    blk6 = portfolio_block(df6, "K136_6strat_realigned", cut)

    # Head-to-head deltas (cap30, OOS, full-fit weights)
    head_to_head = {}
    for variant in ("P1_equal", "P2_inv_vol", "P3_risk_parity", "P5_sharpe_wt"):
        m7 = blk7["oos_cap30"][variant]
        m6 = blk6["oos_cap30"][variant]
        head_to_head[variant] = {
            "K136_oos_sharpe":     m6["sharpe"],
            "K144_oos_sharpe":     m7["sharpe"],
            "delta_oos_sharpe":    round(m7["sharpe"] - m6["sharpe"], 4),
            "K136_oos_max_dd":     m6["max_dd"],
            "K144_oos_max_dd":     m7["max_dd"],
            "delta_oos_max_dd":    round(m7["max_dd"] - m6["max_dd"], 4),
            "K136_oos_ann_ret":    m6["ann_ret"],
            "K144_oos_ann_ret":    m7["ann_ret"],
            "delta_oos_ann_ret":   round(m7["ann_ret"] - m6["ann_ret"], 4),
            "K136_dr_full":        blk6["dr_full"][variant],
            "K144_dr_full":        blk7["dr_full"][variant],
            "delta_dr":            (round(blk7["dr_full"][variant] - blk6["dr_full"][variant], 4)
                                    if blk7["dr_full"][variant] is not None and blk6["dr_full"][variant] is not None
                                    else None),
        }

    # Load K136 original (pre-realignment) for context
    try:
        with open(BASE / "wave_k136_ensemble_v2.json") as fp:
            k136_orig = json.load(fp)
        k136_orig_oos = k136_orig.get("portfolio_metrics_oos_cap30", {})
        k136_orig_n = k136_orig.get("n_days_aligned")
    except Exception:
        k136_orig_oos = {}
        k136_orig_n = None

    # K142 K124-style metadata
    try:
        with open(BASE / "wave_k142_basis_risk.json") as fp:
            k142_meta = json.load(fp)
        k142_var = next(v for v in k142_meta["variants"] if v["name"] == "V_30d_top5")
        k142_summary = {
            "name":      k142_var["name"],
            "perm_p":    k142_var["perm_p"],
            "dsr_oos":   k142_var["dsr_oos"],
            "dsr_full":  k142_var["dsr_full"],
            "oos":       k142_var["oos"],
            "full":      k142_var["full"],
            "gates":     k142_var.get("gates"),
        }
    except Exception:
        k142_summary = {}

    out = {
        "wave": "K144",
        "task": "7-strategy ensemble v3: K136 (6) + K142 V_30d_top5 (CONDITIONAL)",
        "as_of": datetime.utcnow().isoformat() + "Z",
        "components_7": cols7,
        "components_6_baseline": cols6,
        "k142_variant_used": "V_30d_top5",
        "k142_status": "CONDITIONAL (OOS Sh=1.49, perm p=0.010, DSR_oos=0.39 fails 0.50 strict gate)",
        "n_days_aligned": int(len(df7)),
        "date_range": [str(df7.index.min().date()), str(df7.index.max().date())],
        "oos_cut_idx": int(cut),
        "oos_n_days": int(len(df7) - cut),
        "correlations": {
            "pearson":  corr_p.to_dict(),
            "spearman": corr_s.to_dict(),
        },
        "k142_vs_k137_diagnostic": diag_137,
        "k142_meta": k142_summary,
        # 7-strategy block
        "single_metrics_full_7": blk7["single_full"],
        "single_metrics_oos_7":  blk7["single_oos"],
        "weights_full_fit_uncapped_7": blk7["weights_uncapped"],
        "weights_full_fit_cap30_7":    blk7["weights_cap30"],
        "portfolio_metrics_full_uncapped_7": blk7["full_uncapped"],
        "portfolio_metrics_full_cap30_7":    blk7["full_cap30"],
        "portfolio_metrics_oos_uncapped_7":  blk7["oos_uncapped"],
        "portfolio_metrics_oos_cap30_7":     blk7["oos_cap30"],
        "diversification_ratio_full_7":      blk7["dr_full"],
        # 6-strategy block (realigned to same window)
        "single_metrics_full_6": blk6["single_full"],
        "single_metrics_oos_6":  blk6["single_oos"],
        "weights_full_fit_uncapped_6": blk6["weights_uncapped"],
        "weights_full_fit_cap30_6":    blk6["weights_cap30"],
        "portfolio_metrics_full_uncapped_6": blk6["full_uncapped"],
        "portfolio_metrics_full_cap30_6":    blk6["full_cap30"],
        "portfolio_metrics_oos_uncapped_6":  blk6["oos_uncapped"],
        "portfolio_metrics_oos_cap30_6":     blk6["oos_cap30"],
        "diversification_ratio_full_6":      blk6["dr_full"],
        # head-to-head
        "head_to_head_cap30_oos": head_to_head,
        # original K136 baseline (different window)
        "k136_original_oos_cap30": k136_orig_oos,
        "k136_original_n_days":    k136_orig_n,
        "notes": [
            "K144 = K136 6-strat + K142 V_30d_top5 (AEA basis-vol sort, 30d realized basis vol, top5 short).",
            "K142 is CONDITIONAL: OOS Sh +1.49, perm p=0.010 passes, but DSR_oos=0.39 fails 0.50 strict gate (sample-size-bound).",
            "K121 30% cap enforced via proportional redistribution of excess weight.",
            "OOS = last 30% by date. K136 baseline is REALIGNED to K144's narrower aligned window for apples-to-apples comparison.",
            "Diversification Ratio (DR) = port_sharpe / weighted_avg(single_sharpe). DR > 1 means ensemble adds value.",
            "K142 vs K137 diagnostic: both basis-themed. High correlation would mean K142 is largely 'a better K137' rather than new alpha.",
            "Recommendation logic: add K142 if (a) low corr with all 6 members (<|0.3|), (b) ensemble OOS Sh improves OR MaxDD shrinks, (c) DR does not collapse.",
        ],
    }

    with open(BASE / "wave_k144_ensemble_v3.json", "w") as fp:
        json.dump(out, fp, indent=2, default=str)
    print("\nWrote wave_k144_ensemble_v3.json")

    dates_iso = [d.strftime("%Y-%m-%d") for d in df7.index]
    # Merge curves: prefer 7-strat names; suffix 6-strat ports with "_6strat"
    curves_obj = {
        "dates": dates_iso,
        "series": {},
    }
    for k, v in blk7["curves"].items():
        curves_obj["series"][k] = [round(float(x), 6) for x in v]
    for k, v in blk6["curves"].items():
        if k in cols6:  # singles already in blk7
            continue
        curves_obj["series"][k + "_6strat"] = [round(float(x), 6) for x in v]
    with open(BASE / "wave_k144_curves.json", "w") as fp:
        json.dump(curves_obj, fp)
    print("Wrote wave_k144_curves.json")

    # ---- console report ----
    print("\n--- SINGLE STRATEGY (FULL, on K144 aligned window) ---")
    for c in cols7:
        m = blk7["single_full"][c]
        print(f"  {c:6s}  Sh={m['sharpe']:+.3f}  Sor={m['sortino']:+.3f}  "
              f"Cal={m['calmar']:+.3f}  DD={m['max_dd']*100:+.2f}%  Vol={m['ann_vol']*100:.2f}%")

    print("\n--- SINGLE STRATEGY (OOS 30%) ---")
    for c in cols7:
        m = blk7["single_oos"][c]
        print(f"  {c:6s}  OOS Sh={m['sharpe']:+.3f}  DD={m['max_dd']*100:+.2f}%  "
              f"AnnRet={m['ann_ret']*100:+.2f}%")

    print("\n--- K144 7-STRAT PORTFOLIO (FULL, uncapped, full-fit weights) ---")
    for k, m in blk7["full_uncapped"].items():
        w = blk7["weights_uncapped"][k]
        ws = "  ".join(f"{c}={w[i]:.2f}" for i, c in enumerate(cols7))
        print(f"  {k:18s}  Sh={m['sharpe']:+.3f}  DD={m['max_dd']*100:+.2f}%  "
              f"AnnRet={m['ann_ret']*100:+.2f}%  DR={blk7['dr_full'][k]}")
        print(f"    w: {ws}")

    print("\n--- K144 7-STRAT PORTFOLIO (FULL, cap30, full-fit weights) ---")
    for k, m in blk7["full_cap30"].items():
        w = blk7["weights_cap30"][k]
        ws = "  ".join(f"{c}={w[i]:.2f}" for i, c in enumerate(cols7))
        print(f"  {k:18s}  Sh={m['sharpe']:+.3f}  DD={m['max_dd']*100:+.2f}%  AnnRet={m['ann_ret']*100:+.2f}%")
        print(f"    w: {ws}")

    print("\n--- K144 7-STRAT PORTFOLIO (OOS 30%, cap30) ---")
    for k, m in blk7["oos_cap30"].items():
        print(f"  {k:18s}  Sh={m['sharpe']:+.3f}  DD={m['max_dd']*100:+.2f}%  AnnRet={m['ann_ret']*100:+.2f}%")

    print("\n--- K136 6-STRAT BASELINE (realigned to same window, OOS cap30) ---")
    for k, m in blk6["oos_cap30"].items():
        print(f"  {k:18s}  Sh={m['sharpe']:+.3f}  DD={m['max_dd']*100:+.2f}%  AnnRet={m['ann_ret']*100:+.2f}%")

    print("\n--- HEAD-TO-HEAD (OOS cap30): K136 vs K144 ---")
    for k, h in head_to_head.items():
        print(f"  {k:18s}  ΔSh={h['delta_oos_sharpe']:+.3f}  "
              f"ΔDD={h['delta_oos_max_dd']*100:+.2f}%  ΔAnnRet={h['delta_oos_ann_ret']*100:+.2f}%  ΔDR={h['delta_dr']}")

    return out


if __name__ == "__main__":
    run_pipeline()
