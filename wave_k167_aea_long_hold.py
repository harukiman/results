"""Wave K167 — AEA Basis-RISK Sort (LONGER HOLD REVIVAL).

Context
-------
K142 implemented the Gornall/Rinaldi/Xiao 2026 "Perpetual Futures and Basis Risk"
axis: cross-sectional sort by the *volatility* of perp-basis (premium).
  - Low basis-risk -> stable carry -> LONG
  - High basis-risk -> chaotic     -> SHORT
K142 (7d hold) showed full Sharpe ~1.18 / OOS Sharpe ~1.49 but flagged
CONDITIONAL because DSR(OOS) ~ 0.39 (sample-bound).

K144 measured rho(K142, K116) = +0.62 -> K142 rides the same vol-risk-premium
factor as K116 (weekly XS vol). K146 confirmed K116 dominates K142 in the
replace bake-off. The two are functionally redundant at 7d hold.

K167 hypothesis
---------------
Stretching the hold horizon out to ~monthly may decorrelate basis-vol from
weekly XS-vol (K116). The basis-vol signal contains *level-of-microstructure-
calm* information that should compound over weeks: a name with structurally
quiet basis for 30 days is a different beast from one whose 30d vol just
mean-reverted. Longer hold both:
  (a) downweights short-lived vol mean-reversion (which is K116's bread-and-
      butter), pushing K167 toward the cross-sectional carry-stability cohort, and
  (b) cuts turnover -> cost frees up and DSR multiple-testing pressure drops.

If rho(K167, K116) drops materially below the 0.62 K142 baseline (target <0.4),
K167 becomes a viable ensemble candidate.

Variants (pre-registered)
-------------------------
  V_30d_h21 — 30d basis_vol lookback, 21d (504 bar) hold  -- PRIMARY
  V_60d_h28 — 60d basis_vol lookback, 28d (672 bar) hold  -- slower / smoother
  V_30d_h14 — 30d basis_vol lookback, 14d (336 bar) hold  -- bridging anchor

Method
------
Per symbol per 4h bar:
  - Compute rolling 30d (or 60d) stdev of premium_close (basis_vol).
  - Cross-sectional rank, lag 1 bar (no look-ahead).
  - Long bottom-5, short top-5 (or top-3/bot-3 if universe < 20).
  - Equal-weight inside each leg, dollar-neutral.
  - Hold position for hold_bars (only rebalance on t % hold_bars == 0).
  - Costs 0.07% per side per leg.

Audit
-----
730d 4h panel, IS/OOS 70/30. WF 4-fold. Permutation n=300, bootstrap n=300,
DSR (N_trials = 3 -- 3 hold variants of the same signal family).

K116 correlation
----------------
Re-runs the daily-return overlap on the same calendar as K142/K116 comparison.
Reports rho(K167, K116) for each variant. If primary rho < 0.4 -> ensemble
candidate. If rho < 0.55 -> measurable improvement vs K142's 0.62.
"""
from __future__ import annotations

import json
import math
import time
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

ROOT = Path("/Users/nekonaomichi/crypto-lab")
CACHE = ROOT / "cache"
OUT_DIR = ROOT

COST_BPS_PER_LEG = 7.0
IS_FRAC = 0.70
BARS_PER_YEAR = 6 * 365  # 4h bars per year = 2190
RNG_SEED = 42
N_PERM = 300
N_BOOT = 300
N_TRIALS_DSR = 3  # 3 hold variants
WF_FOLDS = 4
TRADING_DAYS = 365  # for daily return correlation with K116

# Same K140-expansion universe used in K142
UNIVERSE_CANDIDATES = [
    "ADA", "APT", "ARB", "ARKM", "AVAX", "BNB", "BOME", "BTC", "DOGE", "DOT",
    "ENA", "ETH", "INJ", "JTO", "JUP", "LINK", "MANTA", "NEAR", "ONDO", "OP",
    "SEI", "SOL", "STRK", "SUI", "TAO", "TIA", "WIF", "WLD", "XRP",
]

t0 = time.time()


def log(msg: str) -> None:
    print(f"[{time.time() - t0:6.1f}s] {msg}", flush=True)


# ---------------------------------------------------------------------------
# Data loaders (mirror K142)
# ---------------------------------------------------------------------------
def load_premium(sym: str) -> pd.Series:
    df = pd.read_parquet(CACHE / f"hist_premium_{sym}USDT_4h_730d.parquet")
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp").drop_duplicates("timestamp")
    s = df.set_index("timestamp")["premium_close"]
    s.name = sym
    return s


def load_price(sym: str) -> pd.Series:
    df = pd.read_parquet(CACHE / f"{sym}USDT_4h_730d.parquet")
    df["open_time"] = pd.to_datetime(df["open_time"])
    df = df.sort_values("open_time").drop_duplicates("open_time")
    s = df.set_index("open_time")["close"]
    s.name = sym
    return s


def load_funding_4h(sym: str, idx: pd.DatetimeIndex) -> pd.Series:
    df = pd.read_parquet(CACHE / f"bybit_fr_{sym}USDT_730d.parquet")
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp").drop_duplicates("timestamp")
    df["bar"] = df["timestamp"].dt.floor("4h")
    agg = df.groupby("bar")["funding_rate"].sum()
    s = agg.reindex(idx, fill_value=0.0)
    s.name = sym
    return s


def discover_universe() -> List[str]:
    have = []
    for s in UNIVERSE_CANDIDATES:
        pf = CACHE / f"hist_premium_{s}USDT_4h_730d.parquet"
        ff = CACHE / f"bybit_fr_{s}USDT_730d.parquet"
        kf = CACHE / f"{s}USDT_4h_730d.parquet"
        if pf.exists() and ff.exists() and kf.exists():
            have.append(s)
    return have


def build_panel(symbols: List[str]) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    prem = pd.concat([load_premium(s) for s in symbols], axis=1).sort_index()
    px = pd.concat([load_price(s) for s in symbols], axis=1).sort_index()
    idx = prem.index.intersection(px.index)
    prem = prem.loc[idx]
    px = px.loc[idx]
    ret = np.log(px / px.shift(1))
    funding = pd.concat([load_funding_4h(s, idx) for s in symbols], axis=1).sort_index()
    return prem, ret, funding


# ---------------------------------------------------------------------------
# Strategy core — basis-vol cross sectional sort, longer hold
# ---------------------------------------------------------------------------
def build_signal(prem: pd.DataFrame, lookback_bars: int) -> pd.DataFrame:
    return prem.rolling(lookback_bars, min_periods=lookback_bars).std()


def build_weights_topk(signal_lag: pd.DataFrame, long_k: int, short_k: int) -> pd.DataFrame:
    syms = list(signal_lag.columns)
    sig_arr = signal_lag.values
    T, N = sig_arr.shape
    w_arr = np.zeros((T, N), dtype=float)
    for t in range(T):
        row = sig_arr[t]
        mask = ~np.isnan(row)
        if mask.sum() < (long_k + short_k):
            continue
        idx = np.where(mask)[0]
        vals = row[idx]
        order = np.argsort(vals)
        long_idx = idx[order[:long_k]]    # bottom: low basis-risk
        short_idx = idx[order[-short_k:]]  # top: high basis-risk
        for i in long_idx:
            w_arr[t, i] = 1.0 / long_k
        for i in short_idx:
            w_arr[t, i] = -1.0 / short_k
    return pd.DataFrame(w_arr, index=signal_lag.index, columns=syms)


def run_variant(prem: pd.DataFrame, ret: pd.DataFrame, funding: pd.DataFrame,
                lookback_bars: int, long_k: int, short_k: int,
                hold_bars: int) -> Dict[str, object]:
    sig = build_signal(prem, lookback_bars)
    signal_lag = sig.shift(1)

    fresh_w = build_weights_topk(signal_lag, long_k, short_k)
    fw = fresh_w.values
    T, N = fw.shape
    w_arr = np.zeros((T, N), dtype=float)
    cur = np.zeros(N)
    for t in range(T):
        if t % hold_bars == 0:
            cur = fw[t].copy()
        w_arr[t] = cur
    weights = pd.DataFrame(w_arr, index=fresh_w.index, columns=fresh_w.columns)

    pos_into = weights.shift(1).fillna(0.0)
    price_pnl = (ret * pos_into).sum(axis=1)
    funding_pnl = (-funding * pos_into).sum(axis=1)
    dw = (weights - weights.shift(1)).abs().sum(axis=1).fillna(0.0)
    cost = dw * (COST_BPS_PER_LEG / 1e4)
    pnl_gross = price_pnl + funding_pnl
    pnl_net = pnl_gross - cost

    return {
        "weights": weights,
        "pnl_net": pnl_net.fillna(0.0),
        "pnl_gross": pnl_gross.fillna(0.0),
        "price_pnl": price_pnl.fillna(0.0),
        "funding_pnl": funding_pnl.fillna(0.0),
        "cost": cost.fillna(0.0),
        "signal_lag": signal_lag,
        "hold_bars": hold_bars,
        "lookback_bars": lookback_bars,
        "long_k": long_k,
        "short_k": short_k,
    }


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------
def sharpe(x: np.ndarray) -> float:
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    if len(x) < 5:
        return 0.0
    sd = x.std(ddof=1)
    if sd == 0:
        return 0.0
    return float(x.mean() / sd * np.sqrt(BARS_PER_YEAR))


def max_dd(pnl: np.ndarray) -> float:
    eq = np.cumsum(pnl)
    peak = np.maximum.accumulate(eq)
    return float((eq - peak).min()) if len(eq) else 0.0


def total_ret(pnl: np.ndarray) -> float:
    return float(np.sum(pnl))


def winrate(pnl: np.ndarray) -> float:
    pnl = pnl[pnl != 0]
    if len(pnl) == 0:
        return 0.0
    return float((pnl > 0).mean())


def permutation_pvalue(out: Dict, prem: pd.DataFrame, ret: pd.DataFrame,
                       funding: pd.DataFrame, observed: float, n: int,
                       seed: int) -> Dict[str, float]:
    rng = np.random.default_rng(seed)
    sig = out["signal_lag"].values.copy()
    fr_mat = funding.values
    ret_mat = ret.values
    T, N = sig.shape
    long_k = out["long_k"]
    short_k = out["short_k"]
    hold_bars = out["hold_bars"]

    perms = np.empty(n)
    for k in range(n):
        sig_perm = sig.copy()
        for t in range(T):
            row = sig_perm[t]
            mask = ~np.isnan(row)
            if mask.sum() < 6:
                continue
            idx_ = np.where(mask)[0]
            sig_perm[t, idx_] = rng.permutation(row[idx_])

        fw = np.zeros((T, N))
        for t in range(T):
            row = sig_perm[t]
            mask = ~np.isnan(row)
            if mask.sum() < (long_k + short_k):
                continue
            idx_ = np.where(mask)[0]
            vals = row[idx_]
            order = np.argsort(vals)
            long_idx = idx_[order[:long_k]]
            short_idx = idx_[order[-short_k:]]
            for i in long_idx:
                fw[t, i] = 1.0 / long_k
            for i in short_idx:
                fw[t, i] = -1.0 / short_k

        w = np.zeros_like(fw)
        cur = np.zeros(N)
        for t in range(T):
            if t % hold_bars == 0:
                cur = fw[t].copy()
            w[t] = cur
        pos_into = np.vstack([np.zeros((1, N)), w[:-1]])
        ppnl = np.nansum(ret_mat * pos_into, axis=1)
        fpnl = np.nansum(-fr_mat * pos_into, axis=1)
        dw = np.abs(w - np.vstack([np.zeros((1, N)), w[:-1]])).sum(axis=1)
        cost = dw * (COST_BPS_PER_LEG / 1e4)
        pnl = np.nan_to_num(ppnl + fpnl - cost, nan=0.0, posinf=0.0, neginf=0.0)
        perms[k] = sharpe(pnl)

    p = float((np.sum(perms >= observed) + 1) / (len(perms) + 1))
    return {
        "p": p,
        "perm_mean": float(np.mean(perms)),
        "perm_p5": float(np.percentile(perms, 5)),
        "perm_p95": float(np.percentile(perms, 95)),
    }


def block_bootstrap_sharpe(pnl: np.ndarray, n: int, block: int, seed: int) -> Dict:
    rng = np.random.default_rng(seed)
    T = len(pnl)
    if T < block:
        return {"mean": 0.0, "ci_lo": 0.0, "ci_hi": 0.0}
    n_blocks = max(1, int(np.ceil(T / block)))
    boots = np.empty(n)
    for k in range(n):
        starts = rng.integers(0, T - block + 1, size=n_blocks)
        chunks = [pnl[s:s + block] for s in starts]
        sample = np.concatenate(chunks)[:T]
        boots[k] = sharpe(sample)
    return {
        "mean": float(boots.mean()),
        "ci_lo": float(np.percentile(boots, 2.5)),
        "ci_hi": float(np.percentile(boots, 97.5)),
    }


def dsr(observed_sh: float, pnl: np.ndarray, n_trials: int) -> float:
    from math import sqrt, log as ln
    from scipy.stats import norm
    x = pnl[pnl != 0]
    T = len(x)
    if T < 30:
        return 0.0
    skew = float(pd.Series(x).skew())
    kurt = float(pd.Series(x).kurt())
    sh_per = observed_sh / np.sqrt(BARS_PER_YEAR)
    emc = 0.5772156649
    n_trials = max(n_trials, 2)
    e_max = (sqrt(2 * ln(n_trials)) * (1 - emc / sqrt(2 * ln(n_trials))) +
             emc / sqrt(2 * ln(n_trials)))
    threshold = e_max / sqrt(T)
    var_sr = (1 - skew * sh_per + (kurt / 4.0) * sh_per ** 2) / max(T - 1, 1)
    if var_sr <= 0:
        return 0.5
    z = (sh_per - threshold) / sqrt(var_sr)
    return float(norm.cdf(z))


def walk_forward(prem, ret, funding, spec, n_folds: int) -> List[Dict]:
    T = len(prem)
    fold_sz = T // (n_folds + 1)
    res = []
    for f in range(n_folds):
        train_end = fold_sz * (f + 1)
        test_end = min(T, fold_sz * (f + 2))
        if test_end - train_end < 30:
            continue
        seed_start = max(0, train_end - spec["lookback_bars"] - 90)
        prem_full = prem.iloc[seed_start:test_end]
        ret_full = ret.iloc[seed_start:test_end]
        fund_full = funding.iloc[seed_start:test_end]
        out = run_variant(prem_full, ret_full, fund_full, **spec)
        n_test = test_end - train_end
        pnl = out["pnl_net"].iloc[-n_test:].values
        res.append({
            "fold": f,
            "n": int(len(pnl)),
            "sharpe": sharpe(pnl),
            "total_ret": total_ret(pnl),
            "max_dd": max_dd(pnl),
        })
    return res


def cost_stress(prem, ret, funding, spec) -> Dict[str, float]:
    res = run_variant(prem, ret, funding, **spec)
    dw = (res["weights"] - res["weights"].shift(1)).abs().sum(axis=1).fillna(0.0)
    pnl_gross = res["pnl_gross"]
    out = {}
    for mult in [0.5, 1.0, 1.5, 2.0]:
        new_cost = dw * (COST_BPS_PER_LEG * mult / 1e4)
        new_pnl = pnl_gross - new_cost
        out[f"cost_x{mult}"] = sharpe(new_pnl.values)
    return out


# ---------------------------------------------------------------------------
# K116 correlation (daily returns)
# ---------------------------------------------------------------------------
def _equity_to_daily_returns(ts_iso, eq):
    ts = pd.to_datetime(ts_iso)
    if ts.tz is not None:
        ts = ts.tz_convert(None)
    s = pd.Series(eq, index=ts).sort_index()
    daily_eq = s.resample("1D").last().ffill()
    return daily_eq.pct_change().fillna(0.0)


def load_k116_daily() -> pd.Series:
    with open(ROOT / "wave_k116_curves.json") as fp:
        d = json.load(fp)
    s = _equity_to_daily_returns(d["timestamps"], d["portfolio_equity"])
    s.name = "K116"
    return s


def pnl_to_daily_returns(pnl_net: pd.Series) -> pd.Series:
    """K167 PnL is bar-level; equity = 1 + cumsum -> resample daily."""
    eq = 1.0 + pnl_net.cumsum()
    return _equity_to_daily_returns(list(eq.index), list(eq.values))


def correlation_vs_k116(k167_daily: pd.Series, k116_daily: pd.Series) -> Dict[str, float]:
    df = pd.concat([k167_daily.rename("K167"), k116_daily.rename("K116")],
                   axis=1, join="inner").dropna()
    if len(df) < 30:
        return {"rho": None, "n_overlap": int(len(df))}
    rho = float(df["K167"].corr(df["K116"]))
    return {"rho": rho, "n_overlap": int(len(df))}


# ---------------------------------------------------------------------------
# Variant evaluator
# ---------------------------------------------------------------------------
def evaluate_variant(name: str, out: Dict, spec: Dict, prem, ret, funding,
                     n_trials_dsr: int, k116_daily: pd.Series) -> Dict:
    pnl_net = out["pnl_net"].values
    pnl_gross = out["pnl_gross"].values
    price_pnl = out["price_pnl"].values
    funding_pnl = out["funding_pnl"].values
    cost = out["cost"].values

    T = len(pnl_net)
    is_end = int(T * IS_FRAC)
    pnl_is = pnl_net[:is_end]
    pnl_oos = pnl_net[is_end:]

    m = {
        "name": name,
        "n_bars": int(T),
        "spec": spec,
        "full": {
            "sharpe": sharpe(pnl_net),
            "sharpe_gross": sharpe(pnl_gross),
            "max_dd": max_dd(pnl_net),
            "total_ret": total_ret(pnl_net),
            "winrate": winrate(pnl_net),
        },
        "is": {
            "sharpe": sharpe(pnl_is),
            "total_ret": total_ret(pnl_is),
            "max_dd": max_dd(pnl_is),
            "n": int(len(pnl_is)),
        },
        "oos": {
            "sharpe": sharpe(pnl_oos),
            "total_ret": total_ret(pnl_oos),
            "max_dd": max_dd(pnl_oos),
            "winrate": winrate(pnl_oos),
            "n": int(len(pnl_oos)),
        },
        "decomposition": {
            "sum_price_pnl": float(np.sum(price_pnl)),
            "sum_funding_pnl": float(np.sum(funding_pnl)),
            "sum_cost": float(np.sum(cost)),
            "sum_net": float(np.sum(pnl_net)),
            "frac_from_funding": float(np.sum(funding_pnl) /
                                       max(abs(np.sum(price_pnl) + np.sum(funding_pnl)), 1e-9)),
        },
    }

    log(f"  [{name}] permutation test n={N_PERM}...")
    perm = permutation_pvalue(out, prem, ret, funding,
                              observed=m["full"]["sharpe"], n=N_PERM, seed=RNG_SEED)
    m["perm_p"] = perm["p"]
    m["perm_null"] = {k: v for k, v in perm.items() if k != "p"}

    log(f"  [{name}] block bootstrap n={N_BOOT}...")
    bb = block_bootstrap_sharpe(pnl_oos, n=N_BOOT, block=42, seed=RNG_SEED)
    m["bootstrap_oos"] = bb

    log(f"  [{name}] DSR (n_trials={n_trials_dsr})...")
    m["dsr_oos"] = dsr(m["oos"]["sharpe"], pnl_oos, n_trials=n_trials_dsr)
    m["dsr_full"] = dsr(m["full"]["sharpe"], pnl_net, n_trials=n_trials_dsr)
    m["n_trials_dsr"] = n_trials_dsr

    log(f"  [{name}] walk-forward {WF_FOLDS}-fold...")
    wf = walk_forward(prem, ret, funding, spec, n_folds=WF_FOLDS)
    m["wf_folds"] = wf
    if wf:
        m["wf_mean_sharpe"] = float(np.mean([f["sharpe"] for f in wf]))
        m["wf_min_sharpe"] = float(np.min([f["sharpe"] for f in wf]))

    log(f"  [{name}] cost stress...")
    m["cost_stress"] = cost_stress(prem, ret, funding, spec)

    log(f"  [{name}] correlation vs K116...")
    daily = pnl_to_daily_returns(out["pnl_net"])
    m["vs_k116"] = correlation_vs_k116(daily, k116_daily)

    g1 = m["oos"]["sharpe"] >= 1.0
    g2 = m["perm_p"] < 0.05
    g3 = m["dsr_oos"] >= 0.95
    m["gates"] = {
        "G1_oos_sharpe_ge_1": bool(g1),
        "G2_perm_p_lt_005": bool(g2),
        "G3_dsr_ge_095": bool(g3),
        "pass_all": bool(g1 and g2 and g3),
    }
    return m


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    universe = discover_universe()
    log(f"universe (PREM x FUND x PRICE @ 730d) -> {len(universe)} symbols: {universe}")

    if len(universe) < 6:
        out = {"wave": "K167", "error": "universe < 6", "universe": universe}
        (OUT_DIR / "wave_k167_aea_long_hold.json").write_text(
            json.dumps(out, indent=2, default=str))
        return

    log("loading panel...")
    prem, ret, funding = build_panel(universe)
    log(f"panel: {len(prem)} bars x {prem.shape[1]} symbols "
        f"({prem.index.min()} .. {prem.index.max()})")

    log("loading K116 daily returns for correlation...")
    try:
        k116_daily = load_k116_daily()
        log(f"K116 daily series: {len(k116_daily)} days "
            f"({k116_daily.index.min()} .. {k116_daily.index.max()})")
    except Exception as e:
        log(f"WARN: failed to load K116: {e}")
        k116_daily = pd.Series(dtype=float, name="K116")

    N = len(universe)
    k5 = 5 if N >= 20 else 3

    # 4h bars: 6 bars per day
    variants = [
        {
            "name": "V_30d_h21",
            "spec": {
                "lookback_bars": 30 * 6,
                "long_k": k5, "short_k": k5,
                "hold_bars": 21 * 6,  # 21d -> 126 bars (monthly)
            },
        },
        {
            "name": "V_60d_h28",
            "spec": {
                "lookback_bars": 60 * 6,
                "long_k": k5, "short_k": k5,
                "hold_bars": 28 * 6,  # 28d -> 168 bars (~monthly, slower lookback)
            },
        },
        {
            "name": "V_30d_h14",
            "spec": {
                "lookback_bars": 30 * 6,
                "long_k": k5, "short_k": k5,
                "hold_bars": 14 * 6,  # 14d -> 84 bars (bridging anchor)
            },
        },
    ]

    results = []
    curves_all = {}
    for v in variants:
        log(f"running {v['name']} spec={v['spec']}")
        out = run_variant(prem, ret, funding, **v["spec"])
        m = evaluate_variant(v["name"], out, v["spec"], prem, ret, funding,
                             n_trials_dsr=N_TRIALS_DSR, k116_daily=k116_daily)
        results.append(m)

        pnl_net = out["pnl_net"].values
        curves_all[v["name"]] = {
            "timestamps": [t.isoformat() for t in out["pnl_net"].index],
            "pnl_net": pnl_net.tolist(),
            "equity_net": np.cumsum(pnl_net).tolist(),
            "price_pnl_cum": np.cumsum(out["price_pnl"].values).tolist(),
            "funding_pnl_cum": np.cumsum(out["funding_pnl"].values).tolist(),
            "cost_cum": np.cumsum(out["cost"].values).tolist(),
            "is_end_idx": int(len(pnl_net) * IS_FRAC),
        }

    # K142 / K146 reference loaders
    k142_v = None
    try:
        k142 = json.load(open(OUT_DIR / "wave_k142_basis_risk.json"))
        for v in k142.get("variants", []):
            if v.get("name") == "V_30d_top5":
                k142_v = {
                    "full_sharpe": v["full"]["sharpe"],
                    "oos_sharpe": v["oos"]["sharpe"],
                    "perm_p": v["perm_p"],
                    "dsr_oos": v["dsr_oos"],
                    "hold_bars": 42,  # 7d
                    "rho_vs_k116": 0.62,  # K144 finding
                }
                break
    except Exception as e:
        log(f"K142 ref load failed: {e}")

    summary = {
        "wave": "K167",
        "label": "AEA Basis-RISK Sort — LONGER HOLD revival (3-4 week rebalance)",
        "hypothesis": ("Longer hold horizon may decorrelate basis-vol from K116's "
                       "weekly XS-vol mode. Target rho < 0.4 -> ensemble candidate."),
        "universe": universe,
        "n_universe": len(universe),
        "panel_bars": int(len(prem)),
        "panel_start": prem.index.min().isoformat(),
        "panel_end": prem.index.max().isoformat(),
        "cost_bps_per_leg": COST_BPS_PER_LEG,
        "is_frac": IS_FRAC,
        "n_perm": N_PERM,
        "n_boot": N_BOOT,
        "n_trials_dsr": N_TRIALS_DSR,
        "wf_folds": WF_FOLDS,
        "variants": results,
        "k142_v30d_top5_reference": k142_v,
        "wall_seconds": time.time() - t0,
    }

    (OUT_DIR / "wave_k167_aea_long_hold.json").write_text(
        json.dumps(summary, indent=2, default=str))
    (OUT_DIR / "wave_k167_curves.json").write_text(
        json.dumps(curves_all, default=str))

    log(f"done. wall: {time.time() - t0:.1f}s")
    print_markdown(summary)


def print_markdown(s: Dict) -> None:
    md = []
    md.append("# Wave K167 — AEA Basis-RISK Sort, LONGER HOLD revival")
    md.append("")
    md.append("**Hypothesis.** Stretching the hold horizon from K142's 7d "
              "out to ~monthly (21-28d) may decorrelate basis-vol XS ranking "
              "from K116's weekly XS-vol mode. K142 had rho(K142, K116)=+0.62 "
              "and was redundant in K146. K167 target: rho < 0.4 "
              "(ensemble-candidate threshold) or < 0.55 (measurable improvement).")
    md.append("")
    md.append(f"**Universe** ({s['n_universe']} symbols, PREM x FUND x PRICE @ 730d): "
              f"{', '.join(s['universe'])}")
    md.append(f"**Panel:** {s['panel_bars']} 4h bars, "
              f"{s['panel_start']} .. {s['panel_end']}")
    md.append(f"**Costs:** {s['cost_bps_per_leg']} bps / side / leg. "
              f"**IS/OOS:** {s['is_frac']:.0%} / {1 - s['is_frac']:.0%}.")
    md.append(f"**Audit:** WF {s['wf_folds']}-fold, perm n={s['n_perm']}, "
              f"bootstrap n={s['n_boot']}, DSR N_trials={s['n_trials_dsr']}.")
    md.append("")
    md.append("## Per-variant headline (NET)")
    md.append("")
    md.append("| Variant | Hold(d) | Full Sh | IS Sh | OOS Sh | OOS Ret | MaxDD | Perm-p | DSR(OOS) | WF mean | WF min | rho K116 |")
    md.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for v in s["variants"]:
        hold_d = v["spec"]["hold_bars"] / 6.0
        rho = v["vs_k116"].get("rho")
        rho_s = f"{rho:+.3f}" if rho is not None else "n/a"
        md.append(f"| {v['name']} | {hold_d:.0f} | "
                  f"{v['full']['sharpe']:.3f} | "
                  f"{v['is']['sharpe']:.3f} | {v['oos']['sharpe']:.3f} | "
                  f"{v['oos']['total_ret']:+.4f} | {v['full']['max_dd']:.4f} | "
                  f"{v['perm_p']:.4f} | {v['dsr_oos']:.3f} | "
                  f"{v.get('wf_mean_sharpe', float('nan')):.3f} | "
                  f"{v.get('wf_min_sharpe', float('nan')):.3f} | "
                  f"{rho_s} |")
    md.append("")
    md.append("## K167 vs K116 correlation -- did stretching the hold help?")
    md.append("")
    md.append("**K142 (7d hold) baseline:** rho(K142, K116) = +0.62 (K144 finding).")
    md.append("")
    md.append("| Variant | Hold(d) | rho(K167, K116) | n daily overlap | Improvement vs K142 |")
    md.append("|---|---:|---:|---:|---|")
    for v in s["variants"]:
        hold_d = v["spec"]["hold_bars"] / 6.0
        vs = v["vs_k116"]
        rho = vs.get("rho")
        n = vs.get("n_overlap")
        rho_s = f"{rho:+.3f}" if rho is not None else "n/a"
        if rho is None:
            improvement = "no overlap"
        else:
            delta = abs(rho) - 0.62
            if abs(rho) < 0.40:
                improvement = f"YES - ensemble candidate (drop {delta:+.2f})"
            elif abs(rho) < 0.55:
                improvement = f"PARTIAL - measurable drop ({delta:+.2f})"
            else:
                improvement = f"NO - still redundant ({delta:+.2f})"
        md.append(f"| {v['name']} | {hold_d:.0f} | {rho_s} | {n} | {improvement} |")
    md.append("")
    md.append("## P&L decomposition (full window)")
    md.append("")
    md.append("| Variant | Price P&L | Funding P&L | Cost | Net | % from funding |")
    md.append("|---|---:|---:|---:|---:|---:|")
    for v in s["variants"]:
        d = v["decomposition"]
        md.append(f"| {v['name']} | {d['sum_price_pnl']:+.4f} | "
                  f"{d['sum_funding_pnl']:+.4f} | -{d['sum_cost']:.4f} | "
                  f"{d['sum_net']:+.4f} | {d['frac_from_funding']:.1%} |")
    md.append("")
    md.append("## Cost stress (full Sharpe)")
    md.append("")
    md.append("| Variant | x0.5 | x1.0 | x1.5 | x2.0 |")
    md.append("|---|---:|---:|---:|---:|")
    for v in s["variants"]:
        cs = v["cost_stress"]
        md.append(f"| {v['name']} | {cs['cost_x0.5']:.3f} | {cs['cost_x1.0']:.3f} | "
                  f"{cs['cost_x1.5']:.3f} | {cs['cost_x2.0']:.3f} |")
    md.append("")
    md.append("## Walk-forward (per fold OOS Sharpe)")
    md.append("")
    md.append("| Variant | f0 | f1 | f2 | f3 | mean | min |")
    md.append("|---|---:|---:|---:|---:|---:|---:|")
    for v in s["variants"]:
        f = {fld["fold"]: fld["sharpe"] for fld in v.get("wf_folds", [])}
        row = [f"| {v['name']} "]
        for k in range(4):
            row.append(f"| {f.get(k, float('nan')):.3f} ")
        row.append(f"| {v.get('wf_mean_sharpe', float('nan')):.3f} ")
        row.append(f"| {v.get('wf_min_sharpe', float('nan')):.3f} |")
        md.append("".join(row))
    md.append("")
    md.append("## Bootstrap OOS Sharpe (95% CI, block=42)")
    md.append("")
    md.append("| Variant | Mean | CI lo | CI hi |")
    md.append("|---|---:|---:|---:|")
    for v in s["variants"]:
        bb = v["bootstrap_oos"]
        md.append(f"| {v['name']} | {bb['mean']:.3f} | {bb['ci_lo']:.3f} | {bb['ci_hi']:.3f} |")
    md.append("")
    md.append("## vs K142 (7d hold, original AEA basis-vol)")
    md.append("")
    k142_v = s.get("k142_v30d_top5_reference")
    if k142_v:
        md.append("| Wave | Variant | Hold | OOS Sh | Perm-p | DSR(OOS) | rho K116 |")
        md.append("|---|---|---:|---:|---:|---:|---:|")
        md.append(f"| K142 | V_30d_top5 (ref) | 7d | "
                  f"{k142_v['oos_sharpe']:.3f} | {k142_v['perm_p']:.4f} | "
                  f"{k142_v['dsr_oos']:.3f} | +0.620 |")
        for v in s["variants"]:
            hold_d = v["spec"]["hold_bars"] / 6.0
            rho = v["vs_k116"].get("rho")
            rho_s = f"{rho:+.3f}" if rho is not None else "n/a"
            md.append(f"| K167 | {v['name']} | {hold_d:.0f}d | "
                      f"{v['oos']['sharpe']:.3f} | {v['perm_p']:.4f} | "
                      f"{v['dsr_oos']:.3f} | {rho_s} |")
        md.append("")
    md.append("## Section 6 mini-gates")
    md.append("")
    md.append("Per-variant gates (G1 OOS Sh >= 1.0, G2 perm-p < 0.05, "
              f"G3 DSR(OOS) >= 0.95 with N_trials={s['n_trials_dsr']}):")
    md.append("")
    md.append("| Variant | G1 | G2 | G3 | Pass-all |")
    md.append("|---|:--:|:--:|:--:|:--:|")
    any_pass = False
    for v in s["variants"]:
        g = v["gates"]
        if g["pass_all"]:
            any_pass = True
        md.append(f"| {v['name']} | "
                  f"{'PASS' if g['G1_oos_sharpe_ge_1'] else 'FAIL'} | "
                  f"{'PASS' if g['G2_perm_p_lt_005'] else 'FAIL'} | "
                  f"{'PASS' if g['G3_dsr_ge_095'] else 'FAIL'} | "
                  f"{'YES' if g['pass_all'] else 'NO'} |")
    md.append("")
    md.append("## Verdict")
    md.append("")

    # Decision logic
    best = max(s["variants"], key=lambda v: v["oos"]["sharpe"])
    best_rho = best["vs_k116"].get("rho")
    best_rho_abs = abs(best_rho) if best_rho is not None else 1.0

    if any_pass and best_rho_abs < 0.40:
        md.append("**ACCEPT - ensemble candidate.** A passing variant with "
                  f"|rho| = {best_rho_abs:.2f} < 0.40 indicates the longer "
                  "hold meaningfully decorrelated basis-vol from K116's weekly "
                  "XS-vol mode. Recommend forward-test and inclusion in the "
                  "next ensemble bake-off.")
    elif any_pass and best_rho_abs < 0.55:
        md.append("**CONDITIONAL.** A variant passes all gates and |rho| "
                  f"= {best_rho_abs:.2f} represents measurable decorrelation "
                  "vs K142's 0.62 baseline, but still above the 0.40 ensemble "
                  "threshold. Recommend: rerun K146-style replace bake-off "
                  "with K167 substituting K116 to test whether the residual "
                  "shared variance is offset by improved Sharpe.")
    elif any_pass:
        md.append("**REJECT FOR ENSEMBLE (PASS QUANT GATES).** Gates clear "
                  f"but |rho| = {best_rho_abs:.2f} >= 0.55 means K167 is still "
                  "K116's twin -- longer hold did not decorrelate the mode. "
                  "The signal is real; the basis-vol axis is fundamentally "
                  "the same risk factor as the K116 XS-vol axis at all tested "
                  "horizons. Recommend: abandon this direction, pursue an "
                  "interaction signal (basis-vol gated by funding-sign) or "
                  "switch to time-series rather than cross-sectional framing.")
    else:
        md.append("**REJECT.** No variant clears all three Section 6 gates. "
                  f"Best variant: {best['name']} with OOS Sharpe "
                  f"{best['oos']['sharpe']:.2f} (perm-p {best['perm_p']:.3f}, "
                  f"DSR {best['dsr_oos']:.3f}, rho vs K116 = "
                  f"{best_rho_abs:.2f}). "
                  "Stretching the hold horizon did not deliver. "
                  "Follow-ups: (a) interaction of basis-vol with funding-sign, "
                  "(b) basis-vol z-score gating with longer hold, "
                  "(c) drop the AEA direction and pursue K163/K166 in parallel.")
    md.append("")
    md.append(f"Wall time: {s['wall_seconds']:.1f}s")
    print("\n".join(md))


if __name__ == "__main__":
    main()
