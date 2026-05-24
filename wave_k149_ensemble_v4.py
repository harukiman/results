"""Wave K149 — K136 Ensemble + K147 Hidden RSI Divergence Integration

Tests whether adding K147 hidden RSI divergence 4H (V_long_short_h12 variant)
to the existing 6-strategy K136 ensemble improves portfolio risk-adjusted metrics.

7-strategy lineup:
  1. v4.1   wave_k109_curves.json series['v4.1']
  2. V1     wave_k109_curves.json series['V1']
  3. K114   wave_k114_alcp.json    curves['full_equity']
  4. K116   wave_k116_curves.json  portfolio_equity
  5. K121   wave_k121_curves.json  weekend_ls
  6. K133   wave_k133_curves.json  V_rev_3d_z15
  7. K147   wave_k147_curves.json  V_long_short_h12 (NEW — hidden RSI divergence 4H)

Diagnostic focus:
  - K147 vs K116 (vol_only): both technical signals — overlap?
  - K147 vs K133 (funding-reversal): both reversal-themed — overlap?
  - K147 vs K121 (weekend mom): both calendar-ish — overlap?

Portfolios: P1 equal, P2 inv-vol, P3 risk-parity, P5 sharpe-weighted.
K121 30% cap applied.
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
    first = pd.to_datetime(ts_iso[0])
    ts = pd.to_datetime(ts_iso, utc=True).tz_convert(None) if first.tzinfo else pd.to_datetime(ts_iso)
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


def load_k147(variant: str = "V_long_short_h12") -> pd.Series:
    with open(BASE / "wave_k147_curves.json") as fp:
        d = json.load(fp)
    v = d[variant]
    s = _equity_to_daily_returns(v["timestamps"], v["portfolio_equity"])
    s.name = "K147"
    return s


def assemble_returns_6() -> pd.DataFrame:
    """K136 baseline lineup (for direct head-to-head comparison on common dates)."""
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


def assemble_returns_7() -> pd.DataFrame:
    """K149 = K136 + K147."""
    df01 = load_v41_and_v1()
    if df01.index.tz is not None:
        df01.index = df01.index.tz_localize(None)
    s114 = load_k114()
    s116 = load_k116()
    s121 = load_k121()
    s133 = load_k133()
    s147 = load_k147()
    df = pd.concat(
        [df01[["v4.1"]], df01[["V1"]],
         s114.to_frame(), s116.to_frame(), s121.to_frame(),
         s133.to_frame(), s147.to_frame()],
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


# -------------------- Portfolio runner --------------------

def run_portfolio(df: pd.DataFrame, label: str) -> dict:
    """Run all 4 portfolio variants on a given aligned returns DataFrame."""
    cols = list(df.columns)
    R = df.to_numpy()
    cut = int(len(df) * (1 - OOS_FRAC))
    oos_R = R[cut:, :]

    single_full = {c: metrics_pkg(df[c].to_numpy()) for c in cols}
    single_oos = {c: metrics_pkg(R[cut:, i]) for i, c in enumerate(cols)}

    variants = {
        "P1_equal":       w_equal(len(cols)),
        "P2_inv_vol":     w_inv_vol(R),
        "P3_risk_parity": w_risk_parity(R),
        "P5_sharpe_wt":   w_sharpe(R),
    }
    variants_capped = {k: apply_k121_cap(w, cols) for k, w in variants.items()}

    variants_oos_fit = {
        "P1_equal":       w_equal(len(cols)),
        "P2_inv_vol":     w_inv_vol(oos_R),
        "P3_risk_parity": w_risk_parity(oos_R),
        "P5_sharpe_wt":   w_sharpe(oos_R),
    }
    variants_oos_capped = {k: apply_k121_cap(w, cols) for k, w in variants_oos_fit.items()}

    full_metrics = {}
    oos_metrics = {}
    full_metrics_capped = {}
    oos_metrics_capped = {}
    curves_out = {c: list(np.cumprod(1.0 + df[c].to_numpy())) for c in cols}
    dr_full = {}
    single_sh = np.array([single_full[c]["sharpe"] for c in cols])

    for name, w in variants.items():
        pr = R @ w
        m = metrics_pkg(pr)
        full_metrics[name] = m
        wavg = float((w * single_sh).sum())
        dr_full[name] = round(m["sharpe"] / wavg, 4) if wavg > 0 else None
        curves_out[f"{label}_{name}"] = list(np.cumprod(1.0 + pr))
        oos_metrics[name] = metrics_pkg(oos_R @ w)

    for name, w in variants_capped.items():
        pr = R @ w
        full_metrics_capped[name] = metrics_pkg(pr)
        oos_metrics_capped[name] = metrics_pkg(oos_R @ w)
        curves_out[f"{label}_{name}_cap30"] = list(np.cumprod(1.0 + pr))

    return {
        "label": label,
        "cols": cols,
        "n_days": int(len(df)),
        "oos_cut_idx": int(cut),
        "oos_n_days": int(len(df) - cut),
        "date_range": [str(df.index.min().date()), str(df.index.max().date())],
        "single_metrics_full": single_full,
        "single_metrics_oos": single_oos,
        "weights_full_uncapped": {k: [round(float(x), 4) for x in v.tolist()] for k, v in variants.items()},
        "weights_full_cap30":     {k: [round(float(x), 4) for x in v.tolist()] for k, v in variants_capped.items()},
        "weights_oos_uncapped":   {k: [round(float(x), 4) for x in v.tolist()] for k, v in variants_oos_fit.items()},
        "weights_oos_cap30":      {k: [round(float(x), 4) for x in v.tolist()] for k, v in variants_oos_capped.items()},
        "metrics_full_uncapped":  full_metrics,
        "metrics_full_cap30":     full_metrics_capped,
        "metrics_oos_uncapped":   oos_metrics,
        "metrics_oos_cap30":      oos_metrics_capped,
        "diversification_ratio_full": dr_full,
        "curves": curves_out,
        "dates": [d.strftime("%Y-%m-%d") for d in df.index],
    }


# -------------------- Pipeline --------------------

def run_pipeline():
    # 1) K149 7-strategy ensemble
    df7 = assemble_returns_7()
    cols7 = list(df7.columns)
    print(f"K149 (7-strat) aligned: n={len(df7)} cols={cols7}")
    print(f"Date range: {df7.index.min().date()} -> {df7.index.max().date()}")

    # 2) K136 baseline (6 strategies) — aligned to its own common dates
    df6 = assemble_returns_6()
    cols6 = list(df6.columns)
    print(f"K136 (6-strat) aligned: n={len(df6)} cols={cols6}")
    print(f"Date range: {df6.index.min().date()} -> {df6.index.max().date()}")

    # 3) Apples-to-apples: K136 on the same dates as K149 (so the comparison
    #    isn't biased by date-range differences)
    df6_on7 = df6.reindex(df7.index).dropna(how="any")
    print(f"K136 reindexed onto K149 dates: n={len(df6_on7)}")

    # 4) Correlations (7x7 on K149 universe)
    corr_p = df7.corr(method="pearson").round(4)
    corr_s = df7.corr(method="spearman").round(4)
    print("\nPearson 7x7:")
    print(corr_p)

    # 5) K147 vs each — highlight
    print("\nK147 correlations vs other 6:")
    for c in cols7:
        if c == "K147":
            continue
        p = corr_p.loc["K147", c]
        sp = corr_s.loc["K147", c]
        print(f"  K147 vs {c:6s}  Pearson={p:+.4f}  Spearman={sp:+.4f}")

    # 6) Run portfolios for K149 and K136-on-K149 dates
    out149 = run_portfolio(df7, "K149")
    out136_same = run_portfolio(df6_on7, "K136same")

    # 7) Also run K136 on its native universe (full date range)
    out136_native = run_portfolio(df6, "K136native")

    # 8) Comparison object
    head_to_head = {}
    for k in ["P1_equal", "P2_inv_vol", "P3_risk_parity", "P5_sharpe_wt"]:
        head_to_head[k] = {
            "k136_same_dates_full_uncapped": out136_same["metrics_full_uncapped"][k],
            "k149_full_uncapped":            out149["metrics_full_uncapped"][k],
            "delta_sharpe_full_uncapped":    round(
                out149["metrics_full_uncapped"][k]["sharpe"]
                - out136_same["metrics_full_uncapped"][k]["sharpe"], 4),
            "k136_same_dates_full_cap30":    out136_same["metrics_full_cap30"][k],
            "k149_full_cap30":               out149["metrics_full_cap30"][k],
            "delta_sharpe_full_cap30":       round(
                out149["metrics_full_cap30"][k]["sharpe"]
                - out136_same["metrics_full_cap30"][k]["sharpe"], 4),
            "k136_same_dates_oos_uncapped":  out136_same["metrics_oos_uncapped"][k],
            "k149_oos_uncapped":             out149["metrics_oos_uncapped"][k],
            "delta_sharpe_oos_uncapped":     round(
                out149["metrics_oos_uncapped"][k]["sharpe"]
                - out136_same["metrics_oos_uncapped"][k]["sharpe"], 4),
            "k136_same_dates_oos_cap30":     out136_same["metrics_oos_cap30"][k],
            "k149_oos_cap30":                out149["metrics_oos_cap30"][k],
            "delta_sharpe_oos_cap30":        round(
                out149["metrics_oos_cap30"][k]["sharpe"]
                - out136_same["metrics_oos_cap30"][k]["sharpe"], 4),
        }

    # 9) Load native K136 file for reference
    try:
        with open(BASE / "wave_k136_ensemble_v2.json") as fp:
            k136file = json.load(fp)
    except Exception:
        k136file = {}

    # --- assemble output ---
    out = {
        "wave": "K149",
        "task": "7-strategy ensemble: K136 (6) + K147 hidden RSI div 4H (V_long_short_h12)",
        "as_of": datetime.utcnow().isoformat() + "Z",
        "components": cols7,
        "k147_variant_used": "V_long_short_h12",
        "n_days_aligned": int(len(df7)),
        "date_range": [str(df7.index.min().date()), str(df7.index.max().date())],
        "oos_cut_idx": out149["oos_cut_idx"],
        "oos_n_days": out149["oos_n_days"],
        "correlations": {
            "pearson":  corr_p.to_dict(),
            "spearman": corr_s.to_dict(),
        },
        "k147_pairwise_focus": {
            c: {"pearson": float(corr_p.loc["K147", c]),
                "spearman": float(corr_s.loc["K147", c])}
            for c in cols7 if c != "K147"
        },
        "single_metrics_full": out149["single_metrics_full"],
        "single_metrics_oos":  out149["single_metrics_oos"],
        "portfolio_weights_full_fit_uncapped": out149["weights_full_uncapped"],
        "portfolio_weights_full_fit_cap30":    out149["weights_full_cap30"],
        "portfolio_weights_oos_fit_uncapped":  out149["weights_oos_uncapped"],
        "portfolio_weights_oos_fit_cap30":     out149["weights_oos_cap30"],
        "portfolio_metrics_full_uncapped":     out149["metrics_full_uncapped"],
        "portfolio_metrics_full_cap30":        out149["metrics_full_cap30"],
        "portfolio_metrics_oos_uncapped":      out149["metrics_oos_uncapped"],
        "portfolio_metrics_oos_cap30":         out149["metrics_oos_cap30"],
        "diversification_ratio_full":          out149["diversification_ratio_full"],
        "head_to_head_k136_vs_k149_same_dates": head_to_head,
        "k136_same_dates_summary": {
            "n_days":                 out136_same["n_days"],
            "metrics_full_uncapped":  out136_same["metrics_full_uncapped"],
            "metrics_full_cap30":     out136_same["metrics_full_cap30"],
            "metrics_oos_uncapped":   out136_same["metrics_oos_uncapped"],
            "metrics_oos_cap30":      out136_same["metrics_oos_cap30"],
            "weights_full_cap30":     out136_same["weights_full_cap30"],
        },
        "k136_native_summary": {
            "n_days":                 out136_native["n_days"],
            "date_range":             out136_native["date_range"],
            "metrics_full_uncapped":  out136_native["metrics_full_uncapped"],
            "metrics_full_cap30":     out136_native["metrics_full_cap30"],
            "metrics_oos_uncapped":   out136_native["metrics_oos_uncapped"],
            "metrics_oos_cap30":      out136_native["metrics_oos_cap30"],
        },
        "notes": [
            "K149 = K136 6-strat + K147 V_long_short_h12 (hidden RSI div 4H).",
            "Head-to-head uses K136 reindexed onto K149 common dates for apples-to-apples comparison.",
            "K121 30% cap enforced via proportional redistribution.",
            "OOS = last 30% of common-date series.",
            "Diversification Ratio (DR) = port_sharpe / weighted_avg(single_sharpe). DR > 1 = ensemble adds value.",
            "K147 thematic overlap focus: vs K116 (technical), K133 (reversal), K121 (calendar).",
        ],
    }

    with open(BASE / "wave_k149_ensemble_v4.json", "w") as fp:
        json.dump(out, fp, indent=2, default=str)
    print(f"\nWrote wave_k149_ensemble_v4.json")

    # Curves file — merge K149 single + portfolios + same-date K136 portfolios
    all_curves = {}
    all_curves.update(out149["curves"])
    # Also dump K136-on-same-dates portfolios for visual comparison
    for k, v in out136_same["curves"].items():
        if k.startswith("K136same_"):
            all_curves[k] = v

    curves_obj = {
        "dates": out149["dates"],
        "series": {k: [round(float(x), 6) for x in v] for k, v in all_curves.items()},
        "k136_native_dates": out136_native["dates"],
        "k136_native_series": {k: [round(float(x), 6) for x in v]
                                for k, v in out136_native["curves"].items()
                                if k.startswith("K136native_")},
    }
    with open(BASE / "wave_k149_curves.json", "w") as fp:
        json.dump(curves_obj, fp)
    print(f"Wrote wave_k149_curves.json")

    # ---- console report ----
    print("\n--- SINGLE STRATEGY (FULL, K149 dates) ---")
    for c in cols7:
        m = out149["single_metrics_full"][c]
        print(f"  {c:6s}  Sh={m['sharpe']:+.3f}  Sor={m['sortino']:+.3f}  "
              f"Cal={m['calmar']:+.3f}  DD={m['max_dd']*100:+.2f}%  "
              f"AnnRet={m['ann_ret']*100:+.2f}%  Vol={m['ann_vol']*100:.2f}%")

    print("\n--- K149 PORTFOLIO (FULL, uncapped) ---")
    for k, m in out149["metrics_full_uncapped"].items():
        w = out149["weights_full_uncapped"][k]
        ws = "  ".join(f"{c}={w[i]:.2f}" for i, c in enumerate(cols7))
        print(f"  {k:18s}  Sh={m['sharpe']:+.3f}  DD={m['max_dd']*100:+.2f}%  "
              f"AnnRet={m['ann_ret']*100:+.2f}%  DR={out149['diversification_ratio_full'][k]}")
        print(f"    w: {ws}")

    print("\n--- K149 PORTFOLIO (FULL, cap30) ---")
    for k, m in out149["metrics_full_cap30"].items():
        w = out149["weights_full_cap30"][k]
        ws = "  ".join(f"{c}={w[i]:.2f}" for i, c in enumerate(cols7))
        print(f"  {k:18s}  Sh={m['sharpe']:+.3f}  DD={m['max_dd']*100:+.2f}%  AnnRet={m['ann_ret']*100:+.2f}%")
        print(f"    w: {ws}")

    print("\n--- K149 OOS (uncapped) ---")
    for k, m in out149["metrics_oos_uncapped"].items():
        print(f"  {k:18s}  Sh={m['sharpe']:+.3f}  DD={m['max_dd']*100:+.2f}%  AnnRet={m['ann_ret']*100:+.2f}%")

    print("\n--- K149 OOS (cap30) ---")
    for k, m in out149["metrics_oos_cap30"].items():
        print(f"  {k:18s}  Sh={m['sharpe']:+.3f}  DD={m['max_dd']*100:+.2f}%  AnnRet={m['ann_ret']*100:+.2f}%")

    print("\n--- HEAD-TO-HEAD K136(same dates) vs K149 — Sharpe delta ---")
    for k, v in head_to_head.items():
        print(f"  {k:18s}  full_uncap Δ={v['delta_sharpe_full_uncapped']:+.4f}  "
              f"full_cap30 Δ={v['delta_sharpe_full_cap30']:+.4f}  "
              f"oos_uncap Δ={v['delta_sharpe_oos_uncapped']:+.4f}  "
              f"oos_cap30 Δ={v['delta_sharpe_oos_cap30']:+.4f}")

    return out


if __name__ == "__main__":
    run_pipeline()
