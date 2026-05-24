"""Wave K140 — Expand Premium-Index Cache + Re-run K137 V_basis_7d_top3.

K137 V_basis_7d_top3 was CONDITIONAL:
  OOS Sharpe +1.17, perm-p 0.003, but DSR=0.28 FAIL because of small
  6-symbol universe (BTC/ETH/SOL/AVAX/ADA/LINK).

K140 fixes this by:
  (1) Fetching premium-index cache for 23 candidate symbols that already
      have FR + price caches: APT, ARB, ARKM, BNB, BOME, DOGE, DOT, ENA,
      INJ, JTO, JUP, MANTA, NEAR, ONDO, OP, SEI, STRK, SUI, TAO, TIA, WIF,
      WLD, XRP.
  (2) Re-running ONE pre-registered variant (V_basis_7d_top3) on the
      enlarged universe (expecting 12-20 symbols after intersection).
  (3) With N_trials_dsr=1 (pre-registered single config -> no selection bias).

Output:
  wave_k140_basis_carry_expanded.{py,json}
  wave_k140_curves.json
"""
from __future__ import annotations

import asyncio
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

# Make engine importable
sys.path.insert(0, str(ROOT))
from engine.data import fetch_historical_premium_index  # noqa: E402

# ----------------------------------------------------------------------------
# Symbols we want to add to the premium cache.
# These all already have bybit_fr_<S>USDT_730d AND <S>USDT_4h_730d.
CANDIDATE_ADDS = [
    "APT", "ARB", "ARKM", "BNB", "BOME", "DOGE", "DOT", "ENA",
    "INJ", "JTO", "JUP", "MANTA", "NEAR", "ONDO", "OP", "SEI",
    "STRK", "SUI", "TAO", "TIA", "WIF", "WLD", "XRP",
]
# Existing premium cache (730d): BTC, ETH, SOL, AVAX, ADA, LINK
EXISTING_PREM = ["BTC", "ETH", "SOL", "AVAX", "ADA", "LINK"]

COST_BPS_PER_LEG = 7.0
IS_FRAC = 0.70
BARS_PER_YEAR = 6 * 365  # 4h bars per year = 2190
RNG_SEED = 42
N_PERM = 300
N_BOOT = 300
N_TRIALS_DSR_SINGLE = 1   # K140: single pre-registered variant -> N=1
WF_FOLDS = 4

t0 = time.time()


def log(msg: str) -> None:
    print(f"[{time.time() - t0:6.1f}s] {msg}", flush=True)


# ---------------------------------------------------------------------------
# Step 1: fetch missing premium indices with concurrency cap
# ---------------------------------------------------------------------------
async def fetch_one(sym: str, sem: asyncio.Semaphore) -> Tuple[str, bool, int, str]:
    sym_full = f"{sym}USDT"
    cache_file = CACHE / f"hist_premium_{sym_full}_4h_730d.parquet"
    if cache_file.exists():
        try:
            df = pd.read_parquet(cache_file)
            if len(df) > 200:
                return (sym, True, len(df), "already cached")
        except Exception:
            pass
    async with sem:
        try:
            df = await fetch_historical_premium_index(symbol=sym_full, interval="4h", days=730)
            if df is None or len(df) == 0:
                return (sym, False, 0, "empty df returned")
            return (sym, True, len(df), "fetched")
        except Exception as e:
            return (sym, False, 0, f"err: {e}")


async def fetch_all(symbols: List[str], max_concurrent: int = 4) -> List[Tuple[str, bool, int, str]]:
    sem = asyncio.Semaphore(max_concurrent)
    tasks = [fetch_one(s, sem) for s in symbols]
    return await asyncio.gather(*tasks)


def step1_expand_cache() -> Dict[str, object]:
    log(f"Step 1: fetching premium for {len(CANDIDATE_ADDS)} symbols (max 4 concurrent)")
    res = asyncio.run(fetch_all(CANDIDATE_ADDS, max_concurrent=4))
    ok = [r for r in res if r[1]]
    fail = [r for r in res if not r[1]]
    log(f"  ok={len(ok)} fail={len(fail)}")
    for r in res:
        log(f"    {r[0]:>6}: {'OK ' if r[1] else 'FAIL'} rows={r[2]:>5}  ({r[3]})")
    return {
        "candidates_requested": CANDIDATE_ADDS,
        "n_requested": len(CANDIDATE_ADDS),
        "n_ok": len(ok),
        "n_fail": len(fail),
        "fetch_log": [
            {"symbol": r[0], "ok": r[1], "rows": r[2], "msg": r[3]} for r in res
        ],
    }


# ---------------------------------------------------------------------------
# Step 2: data loading (mirrors K137)
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
    """Symbols with PREM ∩ FUND ∩ PRICE all available at 730d."""
    cand = sorted(set(EXISTING_PREM + CANDIDATE_ADDS))
    have = []
    for s in cand:
        pf = CACHE / f"hist_premium_{s}USDT_4h_730d.parquet"
        ff = CACHE / f"bybit_fr_{s}USDT_730d.parquet"
        kf = CACHE / f"{s}USDT_4h_730d.parquet"
        if pf.exists() and ff.exists() and kf.exists():
            try:
                _ = pd.read_parquet(pf, columns=["timestamp"])
                _ = pd.read_parquet(ff, columns=["timestamp"])
                _ = pd.read_parquet(kf, columns=["open_time"])
                have.append(s)
            except Exception:
                pass
    return have


def build_panel(symbols: List[str]) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    prem_pieces = []
    px_pieces = []
    for s in symbols:
        prem_pieces.append(load_premium(s))
        px_pieces.append(load_price(s))
    prem = pd.concat(prem_pieces, axis=1).sort_index()
    px = pd.concat(px_pieces, axis=1).sort_index()
    idx = prem.index.intersection(px.index)
    prem = prem.loc[idx]
    px = px.loc[idx]
    ret = np.log(px / px.shift(1))
    fund_pieces = []
    for s in symbols:
        fund_pieces.append(load_funding_4h(s, idx))
    funding = pd.concat(fund_pieces, axis=1).sort_index()
    return prem, ret, funding


# ---------------------------------------------------------------------------
# Strategy core (identical to K137)
# ---------------------------------------------------------------------------
def build_weights(signal_lag: pd.DataFrame, long_k: int, short_k: int) -> pd.DataFrame:
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
        long_idx = idx[order[:long_k]]
        short_idx = idx[order[-short_k:]]
        for i in long_idx:
            w_arr[t, i] = 1.0 / long_k
        for i in short_idx:
            w_arr[t, i] = -1.0 / short_k
    return pd.DataFrame(w_arr, index=signal_lag.index, columns=syms)


def run_variant(prem: pd.DataFrame, ret: pd.DataFrame, funding: pd.DataFrame,
                lookback_bars: int, long_k: int, short_k: int,
                hold_bars: int = 6) -> Dict[str, object]:
    rolling = prem.rolling(lookback_bars, min_periods=lookback_bars).mean()
    signal_lag = rolling.shift(1)
    fresh_w = build_weights(signal_lag, long_k, short_k)

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
            if mask.sum() < (long_k + short_k):
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


def walk_forward(prem, ret, funding, lookback_bars, long_k, short_k,
                 hold_bars, n_folds: int) -> List[Dict]:
    T = len(prem)
    fold_sz = T // (n_folds + 1)
    res = []
    for f in range(n_folds):
        train_end = fold_sz * (f + 1)
        test_end = min(T, fold_sz * (f + 2))
        if test_end - train_end < 30:
            continue
        seed_start = max(0, train_end - lookback_bars - 90)
        prem_full = prem.iloc[seed_start:test_end]
        ret_full = ret.iloc[seed_start:test_end]
        fund_full = funding.iloc[seed_start:test_end]
        out = run_variant(prem_full, ret_full, fund_full,
                          lookback_bars, long_k, short_k, hold_bars)
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


def cost_stress(prem, ret, funding, lookback_bars, long_k, short_k,
                hold_bars) -> Dict[str, float]:
    res = run_variant(prem, ret, funding, lookback_bars, long_k, short_k, hold_bars)
    dw = (res["weights"] - res["weights"].shift(1)).abs().sum(axis=1).fillna(0.0)
    pnl_gross = res["pnl_gross"]
    out = {}
    for mult in [0.5, 1.0, 1.5, 2.0]:
        new_cost = dw * (COST_BPS_PER_LEG * mult / 1e4)
        new_pnl = pnl_gross - new_cost
        out[f"cost_x{mult}"] = sharpe(new_pnl.values)
    return out


# ---------------------------------------------------------------------------
# Evaluate variant
# ---------------------------------------------------------------------------
def evaluate_variant(name: str, out: Dict, prem, ret, funding,
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
        "lookback_bars": out["lookback_bars"],
        "long_k": out["long_k"],
        "short_k": out["short_k"],
        "hold_bars": out["hold_bars"],
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
    wf = walk_forward(prem, ret, funding,
                      out["lookback_bars"], out["long_k"], out["short_k"],
                      out["hold_bars"], n_folds=WF_FOLDS)
    m["wf_folds"] = wf
    if wf:
        m["wf_mean_sharpe"] = float(np.mean([f["sharpe"] for f in wf]))
        m["wf_min_sharpe"] = float(np.min([f["sharpe"] for f in wf]))

    log(f"  [{name}] cost stress...")
    m["cost_stress"] = cost_stress(prem, ret, funding,
                                   out["lookback_bars"], out["long_k"], out["short_k"],
                                   out["hold_bars"])

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
    # Step 1
    fetch_summary = step1_expand_cache()

    # Step 2: build universe (PREM ∩ FUND ∩ PRICE all at 730d)
    universe = discover_universe()
    log(f"Step 2: universe (PREM ∩ FUND ∩ PRICE @ 730d) -> {len(universe)} symbols: {universe}")

    if len(universe) < 6:
        log("ERROR: universe < 6 symbols. Cannot proceed.")
        out = {
            "wave": "K140",
            "fetch_summary": fetch_summary,
            "universe": universe,
            "error": "universe < 6 symbols",
        }
        (OUT_DIR / "wave_k140_basis_carry_expanded.json").write_text(json.dumps(out, indent=2, default=str))
        return

    log("loading panel...")
    prem, ret, funding = build_panel(universe)
    log(f"panel: {len(prem)} bars x {prem.shape[1]} symbols "
        f"({prem.index.min()} .. {prem.index.max()})")

    # Decide variant config based on universe size
    N = len(universe)
    if N >= 20:
        long_k, short_k = 5, 5
        variant_name = "V_basis_7d_top5"
    elif N >= 12:
        long_k, short_k = 3, 3
        variant_name = "V_basis_7d_top3"
    else:
        long_k, short_k = 3, 3
        variant_name = "V_basis_7d_top3"

    spec = {
        "name": variant_name,
        "lookback_bars": 42,    # 42 * 4h = 7 days
        "long_k": long_k,
        "short_k": short_k,
        "hold_bars": 6,         # 24h hold
    }

    log(f"running variant {variant_name} (L/S={long_k}/{short_k}, lookback=42, hold=6) ...")
    out = run_variant(prem, ret, funding,
                      lookback_bars=spec["lookback_bars"],
                      long_k=spec["long_k"], short_k=spec["short_k"],
                      hold_bars=spec["hold_bars"])
    m = evaluate_variant(variant_name, out, prem, ret, funding,
                         n_trials_dsr=N_TRIALS_DSR_SINGLE)

    pnl_net = out["pnl_net"].values
    curves_all = {
        variant_name: {
            "timestamps": [t.isoformat() for t in out["pnl_net"].index],
            "pnl_net": pnl_net.tolist(),
            "equity_net": np.cumsum(pnl_net).tolist(),
            "price_pnl_cum": np.cumsum(out["price_pnl"].values).tolist(),
            "funding_pnl_cum": np.cumsum(out["funding_pnl"].values).tolist(),
            "cost_cum": np.cumsum(out["cost"].values).tolist(),
            "is_end_idx": int(len(pnl_net) * IS_FRAC),
        }
    }

    # Pull K137 comparison
    try:
        k137 = json.load(open(OUT_DIR / "wave_k137_basis_carry.json"))
        k137_v = next((v for v in k137["variants"] if v["name"] == "V_basis_7d_top3"), None)
    except Exception:
        k137_v = None

    summary = {
        "wave": "K140",
        "label": "K137 re-run on expanded premium-index universe",
        "fetch_summary": fetch_summary,
        "universe": universe,
        "n_universe": len(universe),
        "k137_universe": ["BTC", "ETH", "SOL", "AVAX", "ADA", "LINK"],
        "k137_n_universe": 6,
        "panel_bars": int(len(prem)),
        "panel_start": prem.index.min().isoformat(),
        "panel_end": prem.index.max().isoformat(),
        "cost_bps_per_leg": COST_BPS_PER_LEG,
        "is_frac": IS_FRAC,
        "n_perm": N_PERM,
        "n_boot": N_BOOT,
        "n_trials_dsr_single": N_TRIALS_DSR_SINGLE,
        "wf_folds": WF_FOLDS,
        "spec": spec,
        "result": m,
        "k137_v_basis_7d_top3": (
            {
                "full_sharpe": k137_v["full"]["sharpe"],
                "oos_sharpe": k137_v["oos"]["sharpe"],
                "perm_p": k137_v["perm_p"],
                "dsr_oos": k137_v["dsr_oos"],
                "n_universe": 6,
            } if k137_v else None
        ),
        "wall_seconds": time.time() - t0,
    }

    (OUT_DIR / "wave_k140_basis_carry_expanded.json").write_text(
        json.dumps(summary, indent=2, default=str))
    (OUT_DIR / "wave_k140_curves.json").write_text(
        json.dumps(curves_all, default=str))

    log(f"done. wall: {time.time() - t0:.1f}s")
    print_markdown(summary)


def print_markdown(s: Dict) -> None:
    md = []
    md.append("# Wave K140 — Premium-Index Cache Expansion + K137 Re-run")
    md.append("")
    md.append("**Motivation:** K137 V_basis_7d_top3 was CONDITIONAL — OOS Sharpe +1.17, "
              "perm-p 0.003, but DSR = 0.28 (FAIL G3) because the universe of 6 symbols "
              "is too narrow for a meaningful cross-section. K140 expands the premium-index "
              "cache and re-runs the SAME pre-registered variant on a larger universe.")
    md.append("")
    md.append("## Step 1 — Premium-index cache expansion")
    md.append("")
    fs = s["fetch_summary"]
    md.append(f"Candidate symbols: {fs['n_requested']} (those with FR + price caches @ 730d already)")
    md.append(f"Fetch result: **{fs['n_ok']} OK** / **{fs['n_fail']} FAIL**")
    md.append("")
    md.append("| Symbol | Status | Rows | Note |")
    md.append("|---|---|---:|---|")
    for r in fs["fetch_log"]:
        st = "OK" if r["ok"] else "FAIL"
        md.append(f"| {r['symbol']} | {st} | {r['rows']} | {r['msg']} |")
    md.append("")
    md.append("## Step 2 — Final universe")
    md.append("")
    md.append(f"Universe = PREM ∩ FUND ∩ PRICE @ 730d → **{s['n_universe']} symbols**: "
              f"{', '.join(s['universe'])}")
    md.append(f"K137 baseline universe: 6 symbols ({', '.join(s['k137_universe'])})")
    md.append(f"Expansion factor: ×{s['n_universe']/s['k137_n_universe']:.1f}")
    md.append(f"Panel: {s['panel_bars']} 4h bars, {s['panel_start']} .. {s['panel_end']}")
    md.append("")
    md.append("## Step 3 — Re-run K137 V_basis_7d_top3")
    md.append("")
    spec = s["spec"]
    md.append(f"Variant: **{spec['name']}** — lookback {spec['lookback_bars']} bars (7d), "
              f"long/short k = {spec['long_k']}/{spec['short_k']}, hold {spec['hold_bars']} bars (24h), "
              f"cost {s['cost_bps_per_leg']} bps/leg.")
    md.append("")
    m = s["result"]
    md.append("### Headline metrics (NET)")
    md.append("")
    md.append("| Metric | Value |")
    md.append("|---|---:|")
    md.append(f"| Full Sharpe | {m['full']['sharpe']:.3f} |")
    md.append(f"| Full Sharpe (gross) | {m['full']['sharpe_gross']:.3f} |")
    md.append(f"| IS Sharpe | {m['is']['sharpe']:.3f} |")
    md.append(f"| OOS Sharpe | {m['oos']['sharpe']:.3f} |")
    md.append(f"| OOS Total Ret | {m['oos']['total_ret']:+.4f} |")
    md.append(f"| Full Max DD | {m['full']['max_dd']:.4f} |")
    md.append(f"| Full Total Ret | {m['full']['total_ret']:+.4f} |")
    md.append(f"| Full Winrate | {m['full']['winrate']:.3f} |")
    md.append(f"| Perm-p | {m['perm_p']:.4f} |")
    md.append(f"| DSR(OOS) | {m['dsr_oos']:.4f} |")
    md.append(f"| DSR(Full) | {m['dsr_full']:.4f} |")
    md.append(f"| WF mean Sharpe | {m.get('wf_mean_sharpe', float('nan')):.3f} |")
    md.append(f"| WF min Sharpe | {m.get('wf_min_sharpe', float('nan')):.3f} |")
    md.append("")
    md.append("### P&L decomposition")
    md.append("")
    d = m["decomposition"]
    md.append("| Component | Value |")
    md.append("|---|---:|")
    md.append(f"| Price P&L | {d['sum_price_pnl']:+.4f} |")
    md.append(f"| Funding P&L | {d['sum_funding_pnl']:+.4f} |")
    md.append(f"| Cost | -{d['sum_cost']:.4f} |")
    md.append(f"| Net | {d['sum_net']:+.4f} |")
    md.append(f"| % from funding | {d['frac_from_funding']:.1%} |")
    md.append("")
    md.append("### Walk-forward folds (OOS Sharpe per fold)")
    md.append("")
    md.append("| Fold | n | Sharpe | TotRet | MaxDD |")
    md.append("|---:|---:|---:|---:|---:|")
    for f in m.get("wf_folds", []):
        md.append(f"| {f['fold']} | {f['n']} | {f['sharpe']:.3f} | {f['total_ret']:+.4f} | {f['max_dd']:.4f} |")
    md.append("")
    md.append("### Cost stress")
    md.append("")
    cs = m["cost_stress"]
    md.append("| x0.5 | x1.0 | x1.5 | x2.0 |")
    md.append("|---:|---:|---:|---:|")
    md.append(f"| {cs['cost_x0.5']:.3f} | {cs['cost_x1.0']:.3f} | {cs['cost_x1.5']:.3f} | {cs['cost_x2.0']:.3f} |")
    md.append("")
    md.append("### Bootstrap OOS Sharpe (95% CI, block=42)")
    md.append("")
    bb = m["bootstrap_oos"]
    md.append(f"Mean {bb['mean']:.3f}, CI [{bb['ci_lo']:.3f}, {bb['ci_hi']:.3f}]")
    md.append("")
    md.append("## §6 mini gates")
    md.append("")
    g = m["gates"]
    md.append("| Gate | Threshold | Value | Pass |")
    md.append("|---|---|---:|:--:|")
    md.append(f"| G1 OOS Sharpe ≥ 1.0 | 1.0 | {m['oos']['sharpe']:.3f} | "
              f"{'PASS' if g['G1_oos_sharpe_ge_1'] else 'FAIL'} |")
    md.append(f"| G2 Perm-p < 0.05 | 0.05 | {m['perm_p']:.4f} | "
              f"{'PASS' if g['G2_perm_p_lt_005'] else 'FAIL'} |")
    md.append(f"| G3 DSR(OOS) ≥ 0.95 (N_trials={m['n_trials_dsr']}) | 0.95 | {m['dsr_oos']:.4f} | "
              f"{'PASS' if g['G3_dsr_ge_095'] else 'FAIL'} |")
    md.append("")
    md.append(f"**Pass all 3 gates: {'YES — accept' if g['pass_all'] else 'NO'}**")
    md.append("")
    md.append("## K137 vs K140 comparison")
    md.append("")
    k = s["k137_v_basis_7d_top3"]
    if k:
        md.append("| Metric | K137 (N=6) | K140 (N=" + str(s["n_universe"]) + ") | Δ |")
        md.append("|---|---:|---:|---:|")
        md.append(f"| Full Sharpe | {k['full_sharpe']:.3f} | {m['full']['sharpe']:.3f} | "
                  f"{m['full']['sharpe'] - k['full_sharpe']:+.3f} |")
        md.append(f"| OOS Sharpe | {k['oos_sharpe']:.3f} | {m['oos']['sharpe']:.3f} | "
                  f"{m['oos']['sharpe'] - k['oos_sharpe']:+.3f} |")
        md.append(f"| Perm-p | {k['perm_p']:.4f} | {m['perm_p']:.4f} | "
                  f"{m['perm_p'] - k['perm_p']:+.4f} |")
        md.append(f"| DSR(OOS) | {k['dsr_oos']:.4f} | {m['dsr_oos']:.4f} | "
                  f"{m['dsr_oos'] - k['dsr_oos']:+.4f} |")
    md.append("")
    md.append("## Verdict")
    md.append("")
    if g["pass_all"]:
        md.append("**ACCEPT.** Expanding the universe lifted DSR through the 0.95 threshold while "
                  "preserving (or improving) the OOS Sharpe and statistical significance. This becomes "
                  "a new accepted strategy.")
    else:
        reasons = []
        if not g["G1_oos_sharpe_ge_1"]:
            reasons.append(f"OOS Sharpe {m['oos']['sharpe']:.2f} < 1.0")
        if not g["G2_perm_p_lt_005"]:
            reasons.append(f"perm-p {m['perm_p']:.3f} ≥ 0.05")
        if not g["G3_dsr_ge_095"]:
            reasons.append(f"DSR(OOS) {m['dsr_oos']:.3f} < 0.95")
        md.append(f"**DO NOT ACCEPT.** Reason(s): {'; '.join(reasons)}.")
        md.append("")
        if not g["G3_dsr_ge_095"]:
            md.append("Note on DSR: K140 uses N_trials=1 (pre-registered single config, no selection "
                      "from K137). If DSR still fails despite the larger universe, the signal needs "
                      "more bars (extend cache from 730d) or stronger raw Sharpe.")
    md.append("")
    md.append(f"Wall time: {s['wall_seconds']:.1f}s")
    print("\n".join(md))


if __name__ == "__main__":
    main()
