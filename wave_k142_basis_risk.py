"""Wave K142 — AEA Perp Basis-RISK Sort (R5-19).

Hypothesis (Gornall/Rinaldi/Xiao 2026, "Perpetual Futures and Basis Risk"):
  Cross-sectional sort by **basis VOLATILITY** (not basis level itself like K137):
    - low basis-risk  = stable perp-spot relationship = predictable carry
    - high basis-risk = chaotic = avoid or short
    - Long low-basis-risk, short high-basis-risk (dollar-neutral)

K137 ranked by basis LEVEL (the carry itself). K142 ranks by the *VOLATILITY*
of the basis — a different axis: K137 picks who is paid most; K142 picks who
pays most reliably. The theoretical motivation is that low basis-risk names
have a stickier funding-spot link, so the realised carry is closer to the
ex-ante expected carry; high basis-risk names suffer adverse mark-to-market
even when the average funding looks attractive.

Variants pre-registered:
  V_30d_top5  — 30d rolling stdev of basis (premium), L/S top-5/bot-5
  V_60d_top5  — 60d rolling stdev, top-5/bot-5
  V_30d_top3  — 30d, more concentrated top-3/bot-3
  V_30d_z     — 30d z-score gating (|z|>1.5) — long if z<-1.5, short if z>+1.5

Backtest: 730d 4h bars, IS 70% / OOS 30%, weekly rebalance (hold 7d = 42 bars),
0.07% per side per leg, dollar-neutral. WF 4-fold, permutation n=300,
bootstrap n=300, DSR with N_trials = 4.
"""
from __future__ import annotations

import json
import sys
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
N_TRIALS_DSR = 4
WF_FOLDS = 4
HOLD_BARS = 42  # 7d weekly rebalance

# K140 universe (29 premium symbols). All also have FR+price @ 730d.
UNIVERSE_CANDIDATES = [
    "ADA", "APT", "ARB", "ARKM", "AVAX", "BNB", "BOME", "BTC", "DOGE", "DOT",
    "ENA", "ETH", "INJ", "JTO", "JUP", "LINK", "MANTA", "NEAR", "ONDO", "OP",
    "SEI", "SOL", "STRK", "SUI", "TAO", "TIA", "WIF", "WLD", "XRP",
]

t0 = time.time()


def log(msg: str) -> None:
    print(f"[{time.time() - t0:6.1f}s] {msg}", flush=True)


# ---------------------------------------------------------------------------
# Data loaders
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
# Strategy core — sort by basis VOLATILITY
# ---------------------------------------------------------------------------
def build_signal(prem: pd.DataFrame, lookback_bars: int) -> pd.DataFrame:
    """Rolling stdev of basis (premium). Higher = more chaotic = bad."""
    return prem.rolling(lookback_bars, min_periods=lookback_bars).std()


def build_weights_topk(signal_lag: pd.DataFrame, long_k: int, short_k: int) -> pd.DataFrame:
    """Long bottom-k (low basis-risk = stable), short top-k (high basis-risk = chaotic)."""
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
        long_idx = idx[order[:long_k]]   # bottom: low basis-risk
        short_idx = idx[order[-short_k:]] # top: high basis-risk
        for i in long_idx:
            w_arr[t, i] = 1.0 / long_k
        for i in short_idx:
            w_arr[t, i] = -1.0 / short_k
    return pd.DataFrame(w_arr, index=signal_lag.index, columns=syms)


def build_weights_zgate(signal_lag: pd.DataFrame, z_thresh: float) -> pd.DataFrame:
    """Cross-sectional z-score gating: long if z<-thresh, short if z>+thresh.
    Equal-weight inside each leg, then dollar-neutralise."""
    syms = list(signal_lag.columns)
    arr = signal_lag.values
    T, N = arr.shape
    w_arr = np.zeros((T, N), dtype=float)
    for t in range(T):
        row = arr[t]
        mask = ~np.isnan(row)
        if mask.sum() < 6:
            continue
        idx = np.where(mask)[0]
        vals = row[idx]
        mu = vals.mean()
        sd = vals.std(ddof=1)
        if sd == 0:
            continue
        z = (vals - mu) / sd
        long_mask = z < -z_thresh
        short_mask = z > z_thresh
        nl = long_mask.sum()
        ns = short_mask.sum()
        if nl == 0 or ns == 0:
            continue
        for k, i in enumerate(idx):
            if long_mask[k]:
                w_arr[t, i] = 0.5 / nl
            elif short_mask[k]:
                w_arr[t, i] = -0.5 / ns
    return pd.DataFrame(w_arr, index=signal_lag.index, columns=syms)


def run_variant(prem: pd.DataFrame, ret: pd.DataFrame, funding: pd.DataFrame,
                lookback_bars: int, mode: str, long_k: int = 0, short_k: int = 0,
                z_thresh: float = 1.5, hold_bars: int = HOLD_BARS) -> Dict[str, object]:
    sig = build_signal(prem, lookback_bars)
    signal_lag = sig.shift(1)

    if mode == "topk":
        fresh_w = build_weights_topk(signal_lag, long_k, short_k)
    elif mode == "zgate":
        fresh_w = build_weights_zgate(signal_lag, z_thresh)
    else:
        raise ValueError(mode)

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
        "mode": mode,
        "long_k": long_k,
        "short_k": short_k,
        "z_thresh": z_thresh,
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
    mode = out["mode"]
    long_k = out["long_k"]
    short_k = out["short_k"]
    z_thresh = out["z_thresh"]
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
        if mode == "topk":
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
        else:  # zgate
            for t in range(T):
                row = sig_perm[t]
                mask = ~np.isnan(row)
                if mask.sum() < 6:
                    continue
                idx_ = np.where(mask)[0]
                vals = row[idx_]
                mu = vals.mean()
                sd = vals.std(ddof=1)
                if sd == 0:
                    continue
                z = (vals - mu) / sd
                long_mask = z < -z_thresh
                short_mask = z > z_thresh
                nl = long_mask.sum()
                ns = short_mask.sum()
                if nl == 0 or ns == 0:
                    continue
                for kk, i in enumerate(idx_):
                    if long_mask[kk]:
                        fw[t, i] = 0.5 / nl
                    elif short_mask[kk]:
                        fw[t, i] = -0.5 / ns

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


def evaluate_variant(name: str, out: Dict, spec: Dict, prem, ret, funding,
                     n_trials_dsr: int) -> Dict:
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
    log(f"universe (PREM ∩ FUND ∩ PRICE @ 730d) -> {len(universe)} symbols: {universe}")

    if len(universe) < 6:
        out = {"wave": "K142", "error": "universe < 6", "universe": universe}
        (OUT_DIR / "wave_k142_basis_risk.json").write_text(json.dumps(out, indent=2, default=str))
        return

    log("loading panel...")
    prem, ret, funding = build_panel(universe)
    log(f"panel: {len(prem)} bars x {prem.shape[1]} symbols "
        f"({prem.index.min()} .. {prem.index.max()})")

    N = len(universe)
    # If N >= 20, use top-5/bot-5 for top5 variants; else top-3/bot-3
    k5 = 5 if N >= 20 else 3
    k3 = 3

    variants = [
        {
            "name": "V_30d_top5",
            "spec": {
                "lookback_bars": 30 * 6,  # 30d at 4h
                "mode": "topk",
                "long_k": k5, "short_k": k5,
                "hold_bars": HOLD_BARS,
            },
        },
        {
            "name": "V_60d_top5",
            "spec": {
                "lookback_bars": 60 * 6,
                "mode": "topk",
                "long_k": k5, "short_k": k5,
                "hold_bars": HOLD_BARS,
            },
        },
        {
            "name": "V_30d_top3",
            "spec": {
                "lookback_bars": 30 * 6,
                "mode": "topk",
                "long_k": k3, "short_k": k3,
                "hold_bars": HOLD_BARS,
            },
        },
        {
            "name": "V_30d_z",
            "spec": {
                "lookback_bars": 30 * 6,
                "mode": "zgate",
                "z_thresh": 1.5,
                "hold_bars": HOLD_BARS,
            },
        },
    ]

    results = []
    curves_all = {}
    for v in variants:
        log(f"running {v['name']} spec={v['spec']}")
        out = run_variant(prem, ret, funding, **v["spec"])
        m = evaluate_variant(v["name"], out, v["spec"], prem, ret, funding,
                             n_trials_dsr=N_TRIALS_DSR)
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

    # K137 / K140 comparison
    k137_v = None
    k140_v = None
    try:
        k137 = json.load(open(OUT_DIR / "wave_k137_basis_carry.json"))
        for v in k137.get("variants", []):
            if v.get("name") == "V_basis_7d_top3":
                k137_v = {
                    "full_sharpe": v["full"]["sharpe"],
                    "oos_sharpe": v["oos"]["sharpe"],
                    "perm_p": v["perm_p"],
                    "dsr_oos": v["dsr_oos"],
                    "n_universe": 6,
                }
                break
    except Exception as e:
        log(f"K137 comparison load failed: {e}")
    try:
        k140 = json.load(open(OUT_DIR / "wave_k140_basis_carry_expanded.json"))
        mr = k140.get("result", {})
        if mr:
            k140_v = {
                "full_sharpe": mr["full"]["sharpe"],
                "oos_sharpe": mr["oos"]["sharpe"],
                "perm_p": mr["perm_p"],
                "dsr_oos": mr["dsr_oos"],
                "n_universe": k140.get("n_universe"),
            }
    except Exception as e:
        log(f"K140 comparison load failed: {e}")

    summary = {
        "wave": "K142",
        "label": "AEA Perp Basis-RISK Sort (R5-19) — sort by basis VOLATILITY",
        "hypothesis": ("Gornall/Rinaldi/Xiao 2026 (AEA). Long low-basis-risk "
                       "(stable carry), short high-basis-risk (chaotic). "
                       "Different axis from K137 (basis LEVEL)."),
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
        "hold_bars": HOLD_BARS,
        "variants": results,
        "k137_v_basis_7d_top3": k137_v,
        "k140_result": k140_v,
        "wall_seconds": time.time() - t0,
    }

    (OUT_DIR / "wave_k142_basis_risk.json").write_text(
        json.dumps(summary, indent=2, default=str))
    (OUT_DIR / "wave_k142_curves.json").write_text(
        json.dumps(curves_all, default=str))

    log(f"done. wall: {time.time() - t0:.1f}s")
    print_markdown(summary)


def print_markdown(s: Dict) -> None:
    md = []
    md.append("# Wave K142 — AEA Perp Basis-RISK Sort (R5-19)")
    md.append("")
    md.append("**Hypothesis (Gornall/Rinaldi/Xiao 2026, AEA).** Cross-sectional sort "
              "by the *volatility* of the basis (premium), not its level. "
              "Low basis-risk = stable funding/perp-spot link → predictable carry → LONG. "
              "High basis-risk = chaotic → SHORT. Dollar-neutral, weekly rebalance.")
    md.append("")
    md.append(f"**Universe** ({s['n_universe']} symbols, PREM ∩ FUND ∩ PRICE @ 730d): "
              f"{', '.join(s['universe'])}")
    md.append(f"**Panel:** {s['panel_bars']} 4h bars, "
              f"{s['panel_start']} .. {s['panel_end']}")
    md.append(f"**Costs:** {s['cost_bps_per_leg']} bps / side / leg. "
              f"**Hold:** {s['hold_bars']} bars (7d). **IS/OOS:** {s['is_frac']:.0%} / "
              f"{1 - s['is_frac']:.0%}.")
    md.append(f"**Audit:** WF {s['wf_folds']}-fold, perm n={s['n_perm']}, "
              f"bootstrap n={s['n_boot']}, DSR N_trials={s['n_trials_dsr']}.")
    md.append("")
    md.append("## Per-variant headline (NET)")
    md.append("")
    md.append("| Variant | Full Sh | IS Sh | OOS Sh | OOS Ret | MaxDD | Perm-p | DSR(OOS) | WF mean | WF min |")
    md.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for v in s["variants"]:
        md.append(f"| {v['name']} | {v['full']['sharpe']:.3f} | "
                  f"{v['is']['sharpe']:.3f} | {v['oos']['sharpe']:.3f} | "
                  f"{v['oos']['total_ret']:+.4f} | {v['full']['max_dd']:.4f} | "
                  f"{v['perm_p']:.4f} | {v['dsr_oos']:.3f} | "
                  f"{v.get('wf_mean_sharpe', float('nan')):.3f} | "
                  f"{v.get('wf_min_sharpe', float('nan')):.3f} |")
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
    md.append("## vs K137 (basis LEVEL sort) and K140 (level on expanded universe)")
    md.append("")
    md.append("K137 ranks by the LEVEL of basis (carry magnitude). "
              "K142 ranks by the *VOLATILITY* of basis (stability of carry). "
              "Two orthogonal axes derived from the same premium-index data.")
    md.append("")
    if s["k137_v_basis_7d_top3"] or s["k140_result"]:
        md.append("| Wave | Variant | OOS Sh | Perm-p | DSR(OOS) | N univ |")
        md.append("|---|---|---:|---:|---:|---:|")
        if s["k137_v_basis_7d_top3"]:
            k = s["k137_v_basis_7d_top3"]
            md.append(f"| K137 | V_basis_7d_top3 | {k['oos_sharpe']:.3f} | "
                      f"{k['perm_p']:.4f} | {k['dsr_oos']:.3f} | {k['n_universe']} |")
        if s["k140_result"]:
            k = s["k140_result"]
            md.append(f"| K140 | V_basis_7d_top3 (expanded) | {k['oos_sharpe']:.3f} | "
                      f"{k['perm_p']:.4f} | {k['dsr_oos']:.3f} | {k['n_universe']} |")
        for v in s["variants"]:
            md.append(f"| K142 | {v['name']} | {v['oos']['sharpe']:.3f} | "
                      f"{v['perm_p']:.4f} | {v['dsr_oos']:.3f} | {s['n_universe']} |")
        md.append("")
    md.append("## §6 mini gates")
    md.append("")
    md.append("Per-variant gates (G1 OOS Sh ≥ 1.0, G2 perm-p < 0.05, "
              f"G3 DSR(OOS) ≥ 0.95 with N_trials={s['n_trials_dsr']}):")
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
    md.append("## AEA 2026 paper — does it replicate?")
    md.append("")
    if any_pass:
        md.append("**YES — at least one variant passes all three gates.** "
                  "The theoretical prediction (basis-risk as a priced cross-sectional "
                  "risk factor) is confirmed on the 730d crypto perp panel.")
    else:
        best = max(s["variants"], key=lambda v: v["oos"]["sharpe"])
        md.append(f"**Partial / NO replication.** Best variant: {best['name']} with "
                  f"OOS Sharpe {best['oos']['sharpe']:.2f} (perm-p {best['perm_p']:.3f}, "
                  f"DSR {best['dsr_oos']:.3f}). Sign of edge consistent with paper "
                  "is plotted in the equity curves regardless of gate outcome.")
    md.append("")
    md.append("## Verdict")
    md.append("")
    if any_pass:
        md.append("**ACCEPT.** Basis-volatility ranking adds an independent axis on top of "
                  "basis-level ranking (K137/K140). Recommend promoting the passing variant(s) "
                  "to forward-test paper and stacking with K137-family strategies "
                  "(should be low-correlated given the axes are orthogonal).")
    else:
        md.append("**DO NOT ACCEPT — REJECT/CONDITIONAL.** No variant clears all three §6 gates. "
                  "Best signs and per-fold breakdown above tell the story. "
                  "Key follow-ups: (a) confirm low correlation to K137/K140 carry strategies, "
                  "(b) consider conditioning basis-vol on funding-sign (vol means different "
                  "things when carry is positive vs negative), "
                  "(c) try interaction signal: low basis-vol AND high basis-level "
                  "(stable, high-paid carry).")
    md.append("")
    md.append(f"Wall time: {s['wall_seconds']:.1f}s")
    print("\n".join(md))


if __name__ == "__main__":
    main()
