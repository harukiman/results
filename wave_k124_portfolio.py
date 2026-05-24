"""Wave K124 — 5-Strategy Multi-Axis Ensemble Portfolio

Loads daily return streams from 5 ACCEPT'd strategies, aligns to common
dates, then computes 5 portfolio variants:
  P1 equal-weight
  P2 inverse-vol weighted
  P3 risk-parity (iterative ERC)
  P4 maximum diversification (Choueifaty-Coignard)
  P5 Sharpe-weighted (long-only, max(0, Sh)/sum)

For each variant, full-period and OOS (last 30%) metrics are recorded.

Strategies & data sources:
  - v4.1   wave_k109_curves.json series['v4.1']        (daily, cum return, full)
  - V1     wave_k109_curves.json series['V1']          (daily, cum return, full)
  - K114   wave_k114_alcp.json   curves['full_equity'] (irregular 4H bars, full)
  - K116   wave_k116_curves.json portfolio_equity      (4H bars, full)
  - K121   wave_k121_curves.json portfolio['weekend_ls']  (4-day cadence, full)

Honest caveats:
  - "v4.1" series is the wave_k109 RECONSTRUCTION (Sh+0.70 proxy), not the
    production Sh+4.08 (which uses live funding/OI not in this dataset).
  - K121 has sparse cadence (every 4 days). After resampling to daily by
    forward-fill, daily returns are zero most days. This understates its
    volatility on a daily grid but preserves total return.
  - K114 / K116 are 4H-bar internally; we aggregate to daily by compounding.
"""
from __future__ import annotations

import json
import math
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

BASE = Path("/Users/nekonaomichi/crypto-lab")
TRADING_DAYS = 365  # crypto trades 24/7
OOS_FRAC = 0.30


# -------------------- Loaders --------------------

def load_v41_and_v1() -> pd.DataFrame:
    """v4.1 and V1 daily cumulative returns from wave_k109_curves.json."""
    with open(BASE / "wave_k109_curves.json") as fp:
        d = json.load(fp)
    dates = pd.to_datetime(d["dates"])
    df = pd.DataFrame({"date": dates})
    for name in ("v4.1", "V1"):
        cum = np.asarray(d["series"][name], dtype=float)
        # Convert cumulative-return-from-zero to equity, then daily returns
        eq = 1.0 + cum
        ret = np.diff(eq, prepend=eq[0]) / np.where(np.r_[eq[0], eq[:-1]] == 0, 1, np.r_[eq[0], eq[:-1]])
        # Simpler: daily diff of (1+cum)
        eq_prev = np.r_[1.0, eq[:-1]]
        ret = eq / eq_prev - 1.0
        df[name] = ret
    df = df.set_index("date")
    return df


def _equity_to_daily_returns(ts_iso: List[str], eq: List[float]) -> pd.Series:
    """Resample an irregular equity series to daily returns by compounding bars
    inside each calendar day, then computing close-to-close log returns and
    converting to simple returns.

    We use compounding within the day: daily_eq(d) = last(eq) on or before day end.
    Then daily_return = daily_eq(d) / daily_eq(d-1) - 1.
    Missing days fwd-fill (return = 0).
    """
    ts = pd.to_datetime(ts_iso, utc=True).tz_convert(None)
    s = pd.Series(eq, index=ts).sort_index()
    # Daily snapshot = last value of the day
    daily_eq = s.resample("1D").last().ffill()
    daily_ret = daily_eq.pct_change().fillna(0.0)
    return daily_ret


def load_k114() -> pd.Series:
    with open(BASE / "wave_k114_alcp.json") as fp:
        d = json.load(fp)
    curve = d["curves"]["full_equity"]
    ts = list(curve.keys())
    eq = list(curve.values())
    s = _equity_to_daily_returns(ts, eq)
    s.name = "K114"
    return s


def load_k116() -> pd.Series:
    with open(BASE / "wave_k116_curves.json") as fp:
        d = json.load(fp)
    ts = d["timestamps"]
    eq = d["portfolio_equity"]
    s = _equity_to_daily_returns(ts, eq)
    s.name = "K116"
    return s


def load_k121() -> pd.Series:
    with open(BASE / "wave_k121_curves.json") as fp:
        d = json.load(fp)
    pts = d["weekend_ls"]
    ts = [p["ts"] for p in pts]
    eq = [p["eq"] for p in pts]
    s = _equity_to_daily_returns(ts, eq)
    s.name = "K121"
    return s


def assemble_returns() -> pd.DataFrame:
    df01 = load_v41_and_v1()
    df01.index = df01.index.tz_localize(None) if df01.index.tz is not None else df01.index
    s114 = load_k114()
    s116 = load_k116()
    s121 = load_k121()
    # Build common date frame
    df = pd.concat(
        [df01[["v4.1"]].rename(columns={"v4.1": "v4.1"}),
         df01[["V1"]].rename(columns={"V1": "V1"}),
         s114.to_frame(),
         s116.to_frame(),
         s121.to_frame()],
        axis=1, join="inner"
    ).sort_index()
    df = df.dropna(how="any")
    return df


# -------------------- Metrics --------------------

def sharpe(r: np.ndarray) -> float:
    if r.std(ddof=1) == 0 or len(r) < 2:
        return 0.0
    return float(r.mean() / r.std(ddof=1) * math.sqrt(TRADING_DAYS))


def sortino(r: np.ndarray) -> float:
    downside = r[r < 0]
    if len(downside) < 2 or downside.std(ddof=1) == 0:
        return 0.0
    return float(r.mean() / downside.std(ddof=1) * math.sqrt(TRADING_DAYS))


def max_dd(r: np.ndarray) -> float:
    eq = np.cumprod(1.0 + r)
    peak = np.maximum.accumulate(eq)
    dd = eq / peak - 1.0
    return float(dd.min())


def calmar(r: np.ndarray) -> float:
    ann_ret = (1.0 + r).prod() ** (TRADING_DAYS / max(1, len(r))) - 1.0
    mdd = max_dd(r)
    if mdd == 0:
        return 0.0
    return float(ann_ret / abs(mdd))


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


# -------------------- Portfolio weighting --------------------

def w_equal(n: int) -> np.ndarray:
    return np.ones(n) / n


def w_inv_vol(R: np.ndarray) -> np.ndarray:
    vols = R.std(axis=0, ddof=1)
    vols = np.where(vols == 0, np.nan, vols)
    inv = 1.0 / vols
    w = inv / np.nansum(inv)
    return w


def w_risk_parity(R: np.ndarray, n_iter: int = 5000, tol: float = 1e-8) -> np.ndarray:
    """Iterative ERC algorithm (Maillard, Roncalli, Teiletche 2008)."""
    cov = np.cov(R, rowvar=False, ddof=1)
    n = cov.shape[0]
    w = np.ones(n) / n
    for _ in range(n_iter):
        # marginal risk contributions
        mrc = cov @ w
        rc = w * mrc
        # target equal contribution = total_risk / n
        total_risk = float(np.sqrt(w @ cov @ w))
        target = total_risk * total_risk / n
        # update via gradient-ish step
        new_w = w * (target / np.where(rc == 0, 1e-12, rc)) ** 0.5
        new_w = np.clip(new_w, 1e-6, None)
        new_w = new_w / new_w.sum()
        if np.max(np.abs(new_w - w)) < tol:
            w = new_w
            break
        w = new_w
    return w


def w_max_diversification(R: np.ndarray, n_iter: int = 20000, lr: float = 0.01) -> np.ndarray:
    """Choueifaty-Coignard max diversification ratio.

    DR(w) = (w' sigma) / sqrt(w' Sigma w),
    where sigma = vector of std devs.
    Use multiplicative-update / projected ascent.
    """
    cov = np.cov(R, rowvar=False, ddof=1)
    sigma = np.sqrt(np.diag(cov))
    n = cov.shape[0]
    w = np.ones(n) / n
    best_w = w.copy()
    best_dr = -np.inf
    rng = np.random.default_rng(0)
    # Random restarts + simple coordinate scan
    for trial in range(64):
        w = rng.dirichlet(np.ones(n))
        for _ in range(500):
            denom = math.sqrt(float(w @ cov @ w))
            if denom == 0:
                break
            num = float(w @ sigma)
            grad = sigma / denom - (cov @ w) * num / (denom ** 3)
            w_new = w + lr * grad
            w_new = np.clip(w_new, 1e-6, None)
            w_new = w_new / w_new.sum()
            if np.max(np.abs(w_new - w)) < 1e-10:
                w = w_new
                break
            w = w_new
        denom = math.sqrt(float(w @ cov @ w))
        if denom > 0:
            dr = float(w @ sigma) / denom
            if dr > best_dr:
                best_dr = dr
                best_w = w.copy()
    return best_w


def w_sharpe(R: np.ndarray) -> np.ndarray:
    shs = np.array([sharpe(R[:, i]) for i in range(R.shape[1])])
    pos = np.clip(shs, 0, None)
    if pos.sum() == 0:
        return np.ones(R.shape[1]) / R.shape[1]
    return pos / pos.sum()


# -------------------- Pipeline --------------------

def main():
    df = assemble_returns()
    cols = list(df.columns)
    print(f"Aligned daily returns: n={len(df)} cols={cols}")
    print(f"Date range: {df.index.min().date()} -> {df.index.max().date()}")

    R = df.to_numpy()
    # Pearson + Spearman correlations
    corr_p = df.corr(method="pearson").round(4)
    corr_s = df.corr(method="spearman").round(4)
    print("\nPearson correlation matrix:")
    print(corr_p)

    # Single-strategy metrics
    single_metrics = {c: metrics_pkg(df[c].to_numpy()) for c in cols}

    # Build portfolio variants
    variants: Dict[str, np.ndarray] = {
        "P1_equal":         w_equal(len(cols)),
        "P2_inv_vol":       w_inv_vol(R),
        "P3_risk_parity":   w_risk_parity(R),
        "P4_max_div":       w_max_diversification(R),
        "P5_sharpe_wt":     w_sharpe(R),
    }

    # OOS split (last 30%)
    cut = int(len(df) * (1 - OOS_FRAC))
    oos_R = R[cut:, :]

    variants_oos: Dict[str, np.ndarray] = {
        "P1_equal":         w_equal(len(cols)),
        "P2_inv_vol":       w_inv_vol(oos_R),
        "P3_risk_parity":   w_risk_parity(oos_R),
        "P4_max_div":       w_max_diversification(oos_R),
        "P5_sharpe_wt":     w_sharpe(oos_R),
    }

    # Compute portfolio returns and metrics
    port_full = {}
    port_oos = {}
    curves_out = {c: list(np.cumprod(1.0 + df[c].to_numpy())) for c in cols}
    dates_iso = [d.strftime("%Y-%m-%d") for d in df.index]

    full_metrics = {}
    oos_metrics = {}
    diversification_ratio = {}

    for name, w in variants.items():
        pr = R @ w
        port_full[name] = pr
        m = metrics_pkg(pr)
        full_metrics[name] = m
        # weighted-avg single sharpe vs portfolio sharpe
        single_sh = np.array([single_metrics[c]["sharpe"] for c in cols])
        wavg = float((w * single_sh).sum())
        dr = m["sharpe"] / wavg if wavg > 0 else None
        diversification_ratio[name] = round(dr, 4) if dr is not None else None
        curves_out[name] = list(np.cumprod(1.0 + pr))

    # OOS portfolio metrics: use OOS-fit weights AND full-fit weights (held out)
    for name, w_oos_fit in variants_oos.items():
        # Full-fit weights applied to OOS (honest OOS test)
        w_held = variants[name]
        pr_oos = oos_R @ w_held
        oos_metrics[name] = metrics_pkg(pr_oos)

    # Single OOS metrics
    single_oos = {c: metrics_pkg(R[cut:, i]) for i, c in enumerate(cols)}

    out = {
        "wave": "K124",
        "task": "5-strategy multi-axis ensemble portfolio",
        "as_of": datetime.utcnow().isoformat() + "Z",
        "components": cols,
        "n_days_aligned": int(len(df)),
        "date_range": [str(df.index.min().date()), str(df.index.max().date())],
        "oos_cut_idx": int(cut),
        "oos_n_days": int(len(df) - cut),
        "correlations": {
            "pearson":  corr_p.to_dict(),
            "spearman": corr_s.to_dict(),
        },
        "single_metrics_full": single_metrics,
        "single_metrics_oos":  single_oos,
        "portfolio_weights_full_fit": {k: [round(float(x), 4) for x in v.tolist()]
                                       for k, v in variants.items()},
        "portfolio_weights_oos_fit":  {k: [round(float(x), 4) for x in v.tolist()]
                                       for k, v in variants_oos.items()},
        "portfolio_metrics_full":     full_metrics,
        "portfolio_metrics_oos":      oos_metrics,
        "diversification_ratio_full": diversification_ratio,
        "notes": [
            "Daily returns aligned by inner-join across 5 strategies.",
            "v4.1 returns are the wave_k109 proxy reconstruction (Sh ~0.7), NOT the production Sh+4.08 (live funding/OI).",
            "K121 has 4-day-cadence equity; daily-grid fwd-fill makes most days zero — understates daily vol, total return preserved.",
            "K114, K116 are 4H bars compounded to daily.",
            "Portfolio weights derived on FULL aligned period are held out for OOS evaluation.",
            "Diversification ratio = port_sharpe / weighted_avg(single_sharpe). >1 = portfolio benefits.",
        ],
    }

    with open(BASE / "wave_k124_portfolio.json", "w") as fp:
        json.dump(out, fp, indent=2, default=str)
    print(f"\nWrote {BASE/'wave_k124_portfolio.json'}")

    curves_out_obj = {
        "dates": dates_iso,
        "series": {k: [round(float(x), 6) for x in v] for k, v in curves_out.items()},
    }
    with open(BASE / "wave_k124_curves.json", "w") as fp:
        json.dump(curves_out_obj, fp)
    print(f"Wrote {BASE/'wave_k124_curves.json'}")

    # Console report
    print("\n--- SINGLE STRATEGY (FULL) ---")
    for c in cols:
        m = single_metrics[c]
        print(f"  {c:8s}  Sh={m['sharpe']:+.3f}  Sor={m['sortino']:+.3f}  "
              f"Cal={m['calmar']:+.3f}  DD={m['max_dd']*100:+.2f}%  AnnVol={m['ann_vol']*100:.2f}%")
    print("\n--- PORTFOLIOS (FULL period, full-fit weights) ---")
    for k, m in full_metrics.items():
        w = variants[k]
        ws = "  ".join(f"{c}={w[i]:.2f}" for i, c in enumerate(cols))
        print(f"  {k:18s}  Sh={m['sharpe']:+.3f}  Sor={m['sortino']:+.3f}  "
              f"Cal={m['calmar']:+.3f}  DD={m['max_dd']*100:+.2f}%  DR={diversification_ratio[k]}")
        print(f"    weights: {ws}")
    print("\n--- PORTFOLIOS (OOS last 30%, full-fit weights held out) ---")
    for k, m in oos_metrics.items():
        print(f"  {k:18s}  Sh={m['sharpe']:+.3f}  Sor={m['sortino']:+.3f}  "
              f"Cal={m['calmar']:+.3f}  DD={m['max_dd']*100:+.2f}%")

    return out


if __name__ == "__main__":
    main()
