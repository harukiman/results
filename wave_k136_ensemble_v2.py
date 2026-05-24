"""Wave K136 — K124 Ensemble v2 with K133 Integration

Tests whether adding K133 funding-reversal 5d (V_rev_3d_z15 variant) to the
existing 5-strategy K124 ensemble improves portfolio risk-adjusted metrics.

6-strategy lineup:
  1. v4.1   wave_k109_curves.json series['v4.1']
  2. V1     wave_k109_curves.json series['V1']
  3. K114   wave_k114_alcp.json    curves['full_equity']
  4. K116   wave_k116_curves.json  portfolio_equity
  5. K121   wave_k121_curves.json  weekend_ls
  6. K133   wave_k133_curves.json  V_rev_3d_z15 (NEW)

Diagnostic: also check K133 vs K129 (V_3d_z15_top3) correlation since both
belong to the funding-momentum/reversal family with same z=1.5 + 3-day window.

Portfolios: P1 equal, P2 inv-vol, P3 risk-parity, P5 sharpe-weighted.
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


# -------------------- Loaders (copied from K124 + new K133/K129) --------------------

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
    ts = pd.to_datetime(ts_iso, utc=True).tz_convert(None) if pd.to_datetime(ts_iso[0]).tzinfo else pd.to_datetime(ts_iso)
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


def load_k129(variant: str = "V_3d_z15_top3") -> pd.Series:
    """For diagnostic correlation check (not in portfolio)."""
    with open(BASE / "wave_k129_curves.json") as fp:
        d = json.load(fp)
    v = d[variant]
    s = _equity_to_daily_returns(v["equity_idx"], v["equity_curve"])
    s.name = "K129"
    return s


def assemble_returns_6() -> pd.DataFrame:
    df01 = load_v41_and_v1()
    if df01.index.tz is not None:
        df01.index = df01.index.tz_localize(None)
    s114 = load_k114()
    s116 = load_k116()
    s121 = load_k121()
    s133 = load_k133()
    df = pd.concat(
        [df01[["v4.1"]], df01[["V1"]],
         s114.to_frame(), s116.to_frame(), s121.to_frame(), s133.to_frame()],
        axis=1, join="inner"
    ).sort_index().dropna(how="any")
    return df


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
    """If K121 weight exceeds cap, clip and redistribute proportionally to others."""
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


# -------------------- Diagnostic: K133 vs K129 --------------------

def k133_vs_k129() -> dict:
    """Check K133 correlation with K129 (same family — z=1.5, 3d).

    K133 V_rev_3d_z15 is funding REVERSAL (short top funding, long bottom).
    K129 V_3d_z15_top3 is funding MOMENTUM continuation (long high funding, short low).
    So they should be negatively correlated by construction. Verify."""
    s133 = load_k133("V_rev_3d_z15")
    s129 = load_k129("V_3d_z15_top3")
    df = pd.concat([s133, s129], axis=1, join="inner").dropna()
    if len(df) < 5:
        return {"pearson": None, "spearman": None, "n": int(len(df))}
    p = float(df["K133"].corr(df["K129"], method="pearson"))
    sp = float(df["K133"].corr(df["K129"], method="spearman"))
    return {"pearson": round(p, 4), "spearman": round(sp, 4), "n": int(len(df))}


# -------------------- Pipeline --------------------

def run_pipeline():
    df = assemble_returns_6()
    cols = list(df.columns)
    print(f"Aligned daily returns: n={len(df)}  cols={cols}")
    print(f"Date range: {df.index.min().date()} -> {df.index.max().date()}")

    R = df.to_numpy()

    # Correlations
    corr_p = df.corr(method="pearson").round(4)
    corr_s = df.corr(method="spearman").round(4)
    print("\nPearson 6x6:")
    print(corr_p)

    # Single metrics
    single_full = {c: metrics_pkg(df[c].to_numpy()) for c in cols}

    # K133 family diagnostic
    diag = k133_vs_k129()
    print(f"\nK133 vs K129 (same family, opposite sign by design): "
          f"Pearson={diag['pearson']}, Spearman={diag['spearman']}, n={diag['n']}")

    # K133 vs each in ensemble (highlight)
    print("\nK133 corr vs other 5:")
    for c in cols:
        if c == "K133":
            continue
        p = corr_p.loc["K133", c]
        sp = corr_s.loc["K133", c]
        print(f"  K133 vs {c:6s}  Pearson={p:+.4f}  Spearman={sp:+.4f}")

    # Portfolio variants (full-fit)
    variants: Dict[str, np.ndarray] = {
        "P1_equal":       w_equal(len(cols)),
        "P2_inv_vol":     w_inv_vol(R),
        "P3_risk_parity": w_risk_parity(R),
        "P5_sharpe_wt":   w_sharpe(R),
    }
    # Apply K121 30% cap to all
    variants_capped = {k: apply_k121_cap(w, cols) for k, w in variants.items()}

    cut = int(len(df) * (1 - OOS_FRAC))
    oos_R = R[cut:, :]

    # OOS-fit weights (for reference)
    variants_oos_fit: Dict[str, np.ndarray] = {
        "P1_equal":       w_equal(len(cols)),
        "P2_inv_vol":     w_inv_vol(oos_R),
        "P3_risk_parity": w_risk_parity(oos_R),
        "P5_sharpe_wt":   w_sharpe(oos_R),
    }
    variants_oos_capped = {k: apply_k121_cap(w, cols) for k, w in variants_oos_fit.items()}

    # Portfolio metrics & curves
    full_metrics = {}
    oos_metrics = {}
    full_metrics_capped = {}
    oos_metrics_capped = {}
    dr_full = {}
    dates_iso = [d.strftime("%Y-%m-%d") for d in df.index]
    curves_out = {c: list(np.cumprod(1.0 + df[c].to_numpy())) for c in cols}

    single_sh = np.array([single_full[c]["sharpe"] for c in cols])

    for name, w in variants.items():
        pr = R @ w
        m = metrics_pkg(pr)
        full_metrics[name] = m
        wavg = float((w * single_sh).sum())
        dr_full[name] = round(m["sharpe"] / wavg, 4) if wavg > 0 else None
        curves_out[name] = list(np.cumprod(1.0 + pr))

        pr_oos = oos_R @ w
        oos_metrics[name] = metrics_pkg(pr_oos)

    for name, w in variants_capped.items():
        pr = R @ w
        full_metrics_capped[name] = metrics_pkg(pr)
        pr_oos = oos_R @ w
        oos_metrics_capped[name] = metrics_pkg(pr_oos)
        curves_out[name + "_cap30"] = list(np.cumprod(1.0 + pr))

    single_oos = {c: metrics_pkg(R[cut:, i]) for i, c in enumerate(cols)}

    # --------- Load K124 baseline for comparison ---------
    try:
        with open(BASE / "wave_k124_portfolio.json") as fp:
            k124 = json.load(fp)
        k124_full = k124.get("portfolio_metrics_full", {})
        k124_oos = k124.get("portfolio_metrics_oos", {})
    except Exception:
        k124_full = {}
        k124_oos = {}

    # ----- assemble output -----
    out = {
        "wave": "K136",
        "task": "6-strategy ensemble: K124 (5) + K133 (funding-reversal 3d)",
        "as_of": datetime.utcnow().isoformat() + "Z",
        "components": cols,
        "k133_variant_used": "V_rev_3d_z15",
        "n_days_aligned": int(len(df)),
        "date_range": [str(df.index.min().date()), str(df.index.max().date())],
        "oos_cut_idx": int(cut),
        "oos_n_days": int(len(df) - cut),
        "correlations": {
            "pearson":  corr_p.to_dict(),
            "spearman": corr_s.to_dict(),
        },
        "k133_vs_k129_diagnostic": diag,
        "single_metrics_full": single_full,
        "single_metrics_oos":  single_oos,
        "portfolio_weights_full_fit_uncapped":     {k: [round(float(x), 4) for x in v.tolist()] for k, v in variants.items()},
        "portfolio_weights_full_fit_cap30":        {k: [round(float(x), 4) for x in v.tolist()] for k, v in variants_capped.items()},
        "portfolio_weights_oos_fit_uncapped":      {k: [round(float(x), 4) for x in v.tolist()] for k, v in variants_oos_fit.items()},
        "portfolio_weights_oos_fit_cap30":         {k: [round(float(x), 4) for x in v.tolist()] for k, v in variants_oos_capped.items()},
        "portfolio_metrics_full_uncapped":         full_metrics,
        "portfolio_metrics_full_cap30":            full_metrics_capped,
        "portfolio_metrics_oos_uncapped":          oos_metrics,
        "portfolio_metrics_oos_cap30":             oos_metrics_capped,
        "diversification_ratio_full":              dr_full,
        "k124_baseline_full":                      k124_full,
        "k124_baseline_oos":                       k124_oos,
        "notes": [
            "K136 = K124 5-strat + K133 V_rev_3d_z15 (funding-reversal 3d, z=1.5, hold=15).",
            "K121 30% cap enforced via proportional redistribution of excess weight.",
            "OOS = last 30% by date.",
            "Diversification Ratio (DR) = port_sharpe / weighted_avg(single_sharpe). DR > 1 means ensemble adds value.",
            "K133 vs K129 diagnostic: K129 is funding-momentum continuation; K133 is reversal. Negative correlation expected by design.",
            "K124 baseline metrics loaded from wave_k124_portfolio.json for direct comparison.",
        ],
    }

    with open(BASE / "wave_k136_ensemble_v2.json", "w") as fp:
        json.dump(out, fp, indent=2, default=str)
    print(f"\nWrote wave_k136_ensemble_v2.json")

    curves_obj = {
        "dates": dates_iso,
        "series": {k: [round(float(x), 6) for x in v] for k, v in curves_out.items()},
    }
    with open(BASE / "wave_k136_curves.json", "w") as fp:
        json.dump(curves_obj, fp)
    print(f"Wrote wave_k136_curves.json")

    # ---- console report ----
    print("\n--- SINGLE STRATEGY (FULL) ---")
    for c in cols:
        m = single_full[c]
        print(f"  {c:6s}  Sh={m['sharpe']:+.3f}  Sor={m['sortino']:+.3f}  "
              f"Cal={m['calmar']:+.3f}  DD={m['max_dd']*100:+.2f}%  Vol={m['ann_vol']*100:.2f}%")

    print("\n--- PORTFOLIO (FULL, uncapped, full-fit weights) ---")
    for k, m in full_metrics.items():
        w = variants[k]
        ws = "  ".join(f"{c}={w[i]:.2f}" for i, c in enumerate(cols))
        print(f"  {k:18s}  Sh={m['sharpe']:+.3f}  DD={m['max_dd']*100:+.2f}%  "
              f"AnnRet={m['ann_ret']*100:+.2f}%  DR={dr_full[k]}")
        print(f"    w: {ws}")

    print("\n--- PORTFOLIO (FULL, K121 cap 30%, full-fit weights) ---")
    for k, m in full_metrics_capped.items():
        w = variants_capped[k]
        ws = "  ".join(f"{c}={w[i]:.2f}" for i, c in enumerate(cols))
        print(f"  {k:18s}  Sh={m['sharpe']:+.3f}  DD={m['max_dd']*100:+.2f}%  AnnRet={m['ann_ret']*100:+.2f}%")
        print(f"    w: {ws}")

    print("\n--- PORTFOLIO (OOS 30%, uncapped, weights from FULL fit) ---")
    for k, m in oos_metrics.items():
        print(f"  {k:18s}  Sh={m['sharpe']:+.3f}  DD={m['max_dd']*100:+.2f}%  AnnRet={m['ann_ret']*100:+.2f}%")

    print("\n--- PORTFOLIO (OOS 30%, K121 cap 30%, weights from FULL fit) ---")
    for k, m in oos_metrics_capped.items():
        print(f"  {k:18s}  Sh={m['sharpe']:+.3f}  DD={m['max_dd']*100:+.2f}%  AnnRet={m['ann_ret']*100:+.2f}%")

    print("\n--- K124 BASELINE (for reference) ---")
    for k, m in k124_oos.items():
        print(f"  {k:18s}  OOS Sh={m.get('sharpe'):+.3f}  DD={m.get('max_dd', 0)*100:+.2f}%")

    return out


if __name__ == "__main__":
    run_pipeline()
