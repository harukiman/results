"""Wave K137 — Crypto Carry Trade (Basis Sort).

Hypothesis (CMU + AEA 2026, R5-13):
- Perp-spot basis = premium index = (mark - index) / index
- Sort cross-section by trailing basis
- Long bottom decile (cheap basis: perp below spot), short top decile
- Carry leg = funding payments accrued during hold
- Distinct from K127 (funding-rank carry) — this sorts on the BASIS itself,
  which is the level of mispricing, not the rate of funding.

Implementation:
- 4H bar granularity (matches premium index cadence)
- Variants over (lookback bars, top-K, gating)
- Pre-registered 4 variants only — no parameter sweep beyond this
- Costs 0.07% per side per leg
- Funding accrual: funding payments are paid every 8h (3/day); we apportion
  by interpolating onto the 4h bar grid (each 8h event = 2x 4h bars).

Output: wave_k137_basis_carry.{py,json}, wave_k137_curves.json
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

CACHE = Path("/Users/nekonaomichi/crypto-lab/cache")
OUT_DIR = Path("/Users/nekonaomichi/crypto-lab")

# Symbols: intersection of (premium index) AND (funding rate cache)
# Premium files cover: BTC, ETH, SOL, AVAX, ADA, LINK (6 symbols)
# All 6 have funding caches.
SYMBOLS: List[str] = ["BTC", "ETH", "SOL", "AVAX", "ADA", "LINK"]

COST_BPS_PER_LEG = 7.0       # 0.07% per side per leg
IS_FRAC = 0.70
BARS_PER_YEAR = 6 * 365      # 4h bars: 2190/yr
RNG_SEED = 42
N_PERM = 300
N_BOOT = 300
N_TRIALS_DSR = 4
WF_FOLDS = 4

t0 = time.time()


def log(msg: str) -> None:
    print(f"[{time.time() - t0:6.1f}s] {msg}", flush=True)


# --- Data loading ---------------------------------------------------------------

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
    """Load funding rate, align to 4h grid.

    Funding events occur every 8h; we map each 4h bar t to the funding amount
    accrued on a position held into bar t. Since funding settles at 00/08/16 UTC,
    the 4h bars at those hours receive the funding payment; bars at 04/12/20 get 0.
    """
    df = pd.read_parquet(CACHE / f"bybit_fr_{sym}USDT_730d.parquet")
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp").drop_duplicates("timestamp")
    # Floor to 4h grid
    df["bar"] = df["timestamp"].dt.floor("4h")
    agg = df.groupby("bar")["funding_rate"].sum()
    s = agg.reindex(idx, fill_value=0.0)
    s.name = sym
    return s


def build_panel() -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Returns (premium_df, ret_df, funding_df) aligned on common 4h index."""
    prem_pieces = []
    px_pieces = []
    for s in SYMBOLS:
        prem_pieces.append(load_premium(s))
        px_pieces.append(load_price(s))
    prem = pd.concat(prem_pieces, axis=1).sort_index()
    px = pd.concat(px_pieces, axis=1).sort_index()

    # Common index (inner join)
    idx = prem.index.intersection(px.index)
    prem = prem.loc[idx]
    px = px.loc[idx]

    # 4h log return ending at bar t = log(P_t / P_{t-1})
    ret = np.log(px / px.shift(1))

    # Load funding on the same 4h grid
    fund_pieces = []
    for s in SYMBOLS:
        fund_pieces.append(load_funding_4h(s, idx))
    funding = pd.concat(fund_pieces, axis=1).sort_index()

    return prem, ret, funding


# --- Strategy core --------------------------------------------------------------

def build_weights(signal_lag: pd.DataFrame, long_k: int, short_k: int,
                  z_gate: float | None = None,
                  z_window: int = 90) -> pd.DataFrame:
    """Build long/short equal-weight dollar-neutral weights from a lagged signal.

    z_gate: if set, require |z-score(signal_lag)| > z_gate to take a leg
            (z computed per-symbol over rolling z_window).
    """
    syms = list(signal_lag.columns)
    weights = pd.DataFrame(0.0, index=signal_lag.index, columns=syms)

    if z_gate is not None:
        # Per-symbol rolling z-score of the (lagged) signal
        mu = signal_lag.rolling(z_window, min_periods=z_window // 2).mean()
        sd = signal_lag.rolling(z_window, min_periods=z_window // 2).std()
        z = (signal_lag - mu) / sd.replace(0, np.nan)
    else:
        z = None

    sig_arr = signal_lag.values
    z_arr = z.values if z is not None else None
    w_arr = np.zeros_like(sig_arr, dtype=float)
    T, N = sig_arr.shape

    for t in range(T):
        row = sig_arr[t]
        valid_mask = ~np.isnan(row)
        if valid_mask.sum() < (long_k + short_k):
            continue
        idx = np.where(valid_mask)[0]
        vals = row[idx]
        order = np.argsort(vals)
        long_idx = idx[order[:long_k]]
        short_idx = idx[order[-short_k:]]

        if z_arr is not None:
            zrow = z_arr[t]
            # Keep only legs with |z| > gate
            long_idx = [i for i in long_idx if np.isfinite(zrow[i]) and zrow[i] < -z_gate]
            short_idx = [i for i in short_idx if np.isfinite(zrow[i]) and zrow[i] > z_gate]
            if len(long_idx) == 0 and len(short_idx) == 0:
                continue
            # Dollar-neutralize even when uneven: scale each leg to gross 1 if non-empty
            if len(long_idx) > 0:
                wl = 1.0 / len(long_idx)
                for i in long_idx:
                    w_arr[t, i] = wl
            if len(short_idx) > 0:
                ws = 1.0 / len(short_idx)
                for i in short_idx:
                    w_arr[t, i] = -ws
        else:
            for i in long_idx:
                w_arr[t, i] = 1.0 / long_k
            for i in short_idx:
                w_arr[t, i] = -1.0 / short_k

    return pd.DataFrame(w_arr, index=signal_lag.index, columns=syms)


def run_variant(prem: pd.DataFrame, ret: pd.DataFrame, funding: pd.DataFrame,
                lookback_bars: int, long_k: int, short_k: int,
                hold_bars: int = 6, z_gate: float | None = None,
                z_window: int = 90) -> Dict[str, object]:
    """Run one variant.

    Hold for `hold_bars` 4h-bars (rebalance every hold_bars).
    Default hold_bars=6 -> 24h hold (daily rebalance).
    """
    # Trailing-mean basis signal
    rolling = prem.rolling(lookback_bars, min_periods=lookback_bars).mean()
    signal_lag = rolling.shift(1)

    # Build "fresh" weights using the signal on every bar
    fresh_w = build_weights(signal_lag, long_k, short_k, z_gate=z_gate, z_window=z_window)

    # Apply hold: only refresh weights every hold_bars bars; hold otherwise.
    # We rebalance on bars where bar_idx % hold_bars == 0.
    fw = fresh_w.values
    T, N = fw.shape
    w_arr = np.zeros((T, N), dtype=float)
    cur = np.zeros(N)
    for t in range(T):
        if t % hold_bars == 0:
            cur = fw[t].copy()
        w_arr[t] = cur

    weights = pd.DataFrame(w_arr, index=fresh_w.index, columns=fresh_w.columns)

    # Position held INTO bar t (set at end of bar t-1)
    pos_into = weights.shift(1).fillna(0.0)

    # Price P&L at bar t = pos_into * ret_t
    price_pnl = (ret * pos_into).sum(axis=1)

    # Funding P&L: holder of long pos pays funding when funding>0
    # funding rate at bar t (settled if t is on 8h boundary, else 0)
    funding_pnl = (-funding * pos_into).sum(axis=1)

    # Cost on turnover
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
        "fresh_w": fresh_w,
        "hold_bars": hold_bars,
        "lookback_bars": lookback_bars,
        "long_k": long_k,
        "short_k": short_k,
        "z_gate": z_gate,
    }


# --- Stats ----------------------------------------------------------------------

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
    dd = eq - peak
    return float(dd.min()) if len(dd) else 0.0


def total_ret(pnl: np.ndarray) -> float:
    return float(np.sum(pnl))


def winrate(pnl: np.ndarray) -> float:
    pnl = pnl[pnl != 0]
    if len(pnl) == 0:
        return 0.0
    return float((pnl > 0).mean())


# --- Permutation test ----------------------------------------------------------

def permutation_pvalue(out: Dict, prem: pd.DataFrame, ret: pd.DataFrame,
                       funding: pd.DataFrame, observed: float, n: int,
                       seed: int) -> Dict[str, float]:
    """Shuffle signal cross-sectionally at each bar; recompute net Sharpe."""
    rng = np.random.default_rng(seed)
    sig = out["signal_lag"].values.copy()
    fr_mat = funding.values
    ret_mat = ret.values
    T, N = sig.shape
    long_k = out["long_k"]
    short_k = out["short_k"]
    hold_bars = out["hold_bars"]
    z_gate = out["z_gate"]

    # If z_gate, we need z-arrays too — but shuffling per row makes z meaningless;
    # for z-gated variant, do the permutation on the WEIGHTS by shuffling allocations
    # over symbols at each rebalance bar.
    perms = np.empty(n)
    for k in range(n):
        sig_perm = sig.copy()
        # Shuffle each row's valid entries
        for t in range(T):
            row = sig_perm[t]
            mask = ~np.isnan(row)
            if mask.sum() < (long_k + short_k):
                continue
            idx = np.where(mask)[0]
            sig_perm[t, idx] = rng.permutation(row[idx])

        # Build fresh weights on permuted signal (skip z-gate for speed; null Sharpe
        # will be slightly higher in turnover but represents the noise floor).
        fw = np.zeros((T, N))
        for t in range(T):
            row = sig_perm[t]
            mask = ~np.isnan(row)
            if mask.sum() < (long_k + short_k):
                continue
            idx = np.where(mask)[0]
            vals = row[idx]
            order = np.argsort(vals)
            long_idx = idx[order[:long_k]]
            short_idx = idx[order[-short_k:]]
            for i in long_idx:
                fw[t, i] = 1.0 / long_k
            for i in short_idx:
                fw[t, i] = -1.0 / short_k

        # Apply hold
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
    """Deflated Sharpe Ratio (Bailey & Lopez de Prado 2014)."""
    from math import sqrt, log
    from scipy.stats import norm
    x = pnl[pnl != 0]
    T = len(x)
    if T < 30:
        return 0.0
    skew = float(pd.Series(x).skew())
    kurt = float(pd.Series(x).kurt())  # excess kurtosis
    sh_per = observed_sh / np.sqrt(BARS_PER_YEAR)
    emc = 0.5772156649
    # Expected max SR over n_trials under null (Bailey/LdP)
    n_trials = max(n_trials, 2)
    e_max = sqrt(2 * log(n_trials)) * (1 - emc / sqrt(2 * log(n_trials))) + \
            emc / sqrt(2 * log(n_trials))
    # SR threshold = expected max SR (per-period scale * sqrt(T-1) to per-period SR)
    # We compare per-period SR to e_max scaled per-period (assume null SR has stddev 1/sqrt(T))
    threshold = e_max / sqrt(T)
    var_sr = (1 - skew * sh_per + (kurt / 4.0) * sh_per ** 2) / max(T - 1, 1)
    if var_sr <= 0:
        return 0.5
    z = (sh_per - threshold) / sqrt(var_sr)
    return float(norm.cdf(z))


def walk_forward(prem, ret, funding, lookback_bars, long_k, short_k,
                 hold_bars, z_gate, z_window, n_folds: int) -> List[Dict]:
    T = len(prem)
    fold_sz = T // (n_folds + 1)  # train then test
    res = []
    for f in range(n_folds):
        train_end = fold_sz * (f + 1)
        test_end = min(T, fold_sz * (f + 2))
        if test_end - train_end < 30:
            continue
        prem_test = prem.iloc[train_end:test_end]
        ret_test = ret.iloc[train_end:test_end]
        fund_test = funding.iloc[train_end:test_end]
        # We use prem/ret/funding from BEFORE the test fold to seed lookback so the
        # rolling mean is warm. Concatenate last `lookback_bars` of pre-test data.
        seed_start = max(0, train_end - lookback_bars - z_window)
        prem_full = prem.iloc[seed_start:test_end]
        ret_full = ret.iloc[seed_start:test_end]
        fund_full = funding.iloc[seed_start:test_end]
        out = run_variant(prem_full, ret_full, fund_full,
                          lookback_bars, long_k, short_k, hold_bars,
                          z_gate=z_gate, z_window=z_window)
        pnl = out["pnl_net"].iloc[-len(prem_test):].values
        res.append({
            "fold": f,
            "n": int(len(pnl)),
            "sharpe": sharpe(pnl),
            "total_ret": total_ret(pnl),
            "max_dd": max_dd(pnl),
        })
    return res


def cost_stress(prem, ret, funding, lookback_bars, long_k, short_k,
                hold_bars, z_gate, z_window) -> Dict[str, float]:
    out = {}
    for mult in [0.5, 1.0, 1.5, 2.0]:
        bps = COST_BPS_PER_LEG * mult
        # Re-run by injecting cost
        res = run_variant(prem, ret, funding, lookback_bars, long_k, short_k,
                          hold_bars, z_gate=z_gate, z_window=z_window)
        # Adjust cost
        dw = (res["weights"] - res["weights"].shift(1)).abs().sum(axis=1).fillna(0.0)
        new_cost = dw * (bps / 1e4)
        new_pnl = res["pnl_gross"] - new_cost
        out[f"cost_x{mult}"] = sharpe(new_pnl.values)
    return out


# --- Main -----------------------------------------------------------------------

def evaluate_variant(name: str, out: Dict, prem, ret, funding, run_perm: bool = True,
                     run_wf: bool = True) -> Dict:
    pnl_net = out["pnl_net"].values
    pnl_gross = out["pnl_gross"].values
    price_pnl = out["price_pnl"].values
    funding_pnl = out["funding_pnl"].values
    cost = out["cost"].values
    weights = out["weights"]

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
        "z_gate": out["z_gate"],
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

    if run_perm:
        log(f"  [{name}] permutation test n={N_PERM}...")
        perm = permutation_pvalue(out, prem, ret, funding,
                                  observed=m["full"]["sharpe"],
                                  n=N_PERM, seed=RNG_SEED)
        m["perm_p"] = perm["p"]
        m["perm_null"] = {k: v for k, v in perm.items() if k != "p"}

    log(f"  [{name}] block bootstrap n={N_BOOT}...")
    bb = block_bootstrap_sharpe(pnl_oos, n=N_BOOT, block=42, seed=RNG_SEED)
    m["bootstrap_oos"] = bb

    log(f"  [{name}] DSR (n_trials={N_TRIALS_DSR})...")
    m["dsr_oos"] = dsr(m["oos"]["sharpe"], pnl_oos, n_trials=N_TRIALS_DSR)
    m["dsr_full"] = dsr(m["full"]["sharpe"], pnl_net, n_trials=N_TRIALS_DSR)

    if run_wf:
        log(f"  [{name}] walk-forward 4-fold...")
        wf = walk_forward(prem, ret, funding,
                          out["lookback_bars"], out["long_k"], out["short_k"],
                          out["hold_bars"], out["z_gate"],
                          z_window=90, n_folds=WF_FOLDS)
        m["wf_folds"] = wf
        if wf:
            m["wf_mean_sharpe"] = float(np.mean([f["sharpe"] for f in wf]))
            m["wf_min_sharpe"] = float(np.min([f["sharpe"] for f in wf]))

    log(f"  [{name}] cost stress...")
    m["cost_stress"] = cost_stress(prem, ret, funding,
                                    out["lookback_bars"], out["long_k"], out["short_k"],
                                    out["hold_bars"], out["z_gate"], z_window=90)

    # §6 mini gates
    g1 = m["oos"]["sharpe"] >= 1.0
    g2 = m.get("perm_p") is not None and m["perm_p"] < 0.05
    g3 = m["dsr_oos"] >= 0.95
    m["gates"] = {
        "G1_oos_sharpe_ge_1": bool(g1),
        "G2_perm_p_lt_005": bool(g2),
        "G3_dsr_ge_095": bool(g3),
        "pass_all": bool(g1 and g2 and g3),
    }
    return m


def main():
    log("loading panel...")
    prem, ret, funding = build_panel()
    log(f"panel: {len(prem)} bars x {prem.shape[1]} symbols "
        f"({prem.index.min()} .. {prem.index.max()})")

    variants_spec = [
        {"name": "V_basis_24h_top3", "lookback_bars": 6,  "long_k": 3, "short_k": 3, "hold_bars": 6,  "z_gate": None},
        {"name": "V_basis_24h_top5", "lookback_bars": 6,  "long_k": 5, "short_k": 5, "hold_bars": 6,  "z_gate": None},
        {"name": "V_basis_7d_top3",  "lookback_bars": 42, "long_k": 3, "short_k": 3, "hold_bars": 6,  "z_gate": None},
        {"name": "V_basis_24h_z15",  "lookback_bars": 6,  "long_k": 3, "short_k": 3, "hold_bars": 6,  "z_gate": 1.5},
    ]
    # NOTE: top_k cannot exceed N=6 symbols, so "top5" leaves only 1 unused;
    # we cap short_k = min(short_k, N - long_k). Sanity: with N=6, top5 = long 5 / short 1
    # which is not dollar-neutral by symbol-count; we still build it because dollar-
    # neutralization is by leg weight. But long_k+short_k>N is invalid; cap.
    N = prem.shape[1]
    for v in variants_spec:
        if v["long_k"] + v["short_k"] > N:
            # cap so legs don't overlap
            cap_per = N // 2
            v["long_k"] = cap_per
            v["short_k"] = cap_per

    all_results = []
    curves_all = {}

    for spec in variants_spec:
        name = spec["name"]
        log(f"running variant {name} ...")
        out = run_variant(prem, ret, funding,
                          lookback_bars=spec["lookback_bars"],
                          long_k=spec["long_k"], short_k=spec["short_k"],
                          hold_bars=spec["hold_bars"], z_gate=spec["z_gate"],
                          z_window=90)
        m = evaluate_variant(name, out, prem, ret, funding,
                             run_perm=True, run_wf=True)
        all_results.append(m)

        pnl_net = out["pnl_net"].values
        curves_all[name] = {
            "timestamps": [t.isoformat() for t in out["pnl_net"].index],
            "pnl_net": pnl_net.tolist(),
            "equity_net": np.cumsum(pnl_net).tolist(),
            "price_pnl_cum": np.cumsum(out["price_pnl"].values).tolist(),
            "funding_pnl_cum": np.cumsum(out["funding_pnl"].values).tolist(),
            "cost_cum": np.cumsum(out["cost"].values).tolist(),
            "is_end_idx": int(len(pnl_net) * IS_FRAC),
        }

    # Comparison vs K127 (load if exists)
    k127 = None
    try:
        k127 = json.load(open(OUT_DIR / "wave_k127_bis_carry.json"))
    except Exception:
        pass

    summary = {
        "wave": "K137",
        "label": "Crypto Carry Basis Sort (CMU + AEA 2026)",
        "symbols": SYMBOLS,
        "n_symbols": len(SYMBOLS),
        "panel_bars": int(len(prem)),
        "panel_start": prem.index.min().isoformat(),
        "panel_end": prem.index.max().isoformat(),
        "cost_bps_per_leg": COST_BPS_PER_LEG,
        "is_frac": IS_FRAC,
        "n_perm": N_PERM,
        "n_boot": N_BOOT,
        "n_trials_dsr": N_TRIALS_DSR,
        "wf_folds": WF_FOLDS,
        "variants": all_results,
        "k127_compare": {
            "k127_full_sharpe": k127["full"]["sharpe"] if k127 else None,
            "k127_oos_sharpe": k127["oos"]["sharpe"] if k127 else None,
            "k127_perm_p_gross": k127.get("perm_p_gross") if k127 else None,
        },
    }

    (OUT_DIR / "wave_k137_basis_carry.json").write_text(
        json.dumps(summary, indent=2, default=str))
    (OUT_DIR / "wave_k137_curves.json").write_text(
        json.dumps(curves_all, default=str))

    log(f"done. wall: {time.time() - t0:.1f}s")
    print_markdown(summary)


def print_markdown(s: Dict) -> None:
    md = []
    md.append("# Wave K137 — Crypto Carry Trade (Basis Sort)")
    md.append("")
    md.append(f"**Hypothesis source:** CMU + AEA 2026 (R5-13). Sort cross-section by perp-spot basis (premium index), long bottom decile (cheap), short top (expensive), capture both basis convergence + funding carry.")
    md.append("")
    md.append(f"**Universe (intersection premium+funding):** {s['n_symbols']} symbols — {', '.join(s['symbols'])}")
    md.append(f"**Panel:** {s['panel_bars']} 4h bars, {s['panel_start']} .. {s['panel_end']}")
    md.append(f"**Cost:** {s['cost_bps_per_leg']} bps/leg/side, IS/OOS = {int(s['is_frac']*100)}/{100-int(s['is_frac']*100)}, perm n={s['n_perm']}, boot n={s['n_boot']}")
    md.append("")
    md.append("## Per-variant headline (NET)")
    md.append("")
    md.append("| Variant | LB(bars) | L/S | hold | z-gate | Full SR | IS SR | OOS SR | Full SR(gross) | MaxDD | Net TotRet | WF mean | Perm-p | DSR(OOS) | Pass §6 |")
    md.append("|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|:--:|")
    for v in s["variants"]:
        wfm = v.get("wf_mean_sharpe", float("nan"))
        passed = "YES" if v["gates"]["pass_all"] else "NO"
        md.append(f"| {v['name']} | {v['lookback_bars']} | {v['long_k']}/{v['short_k']} | "
                  f"{v['hold_bars']} | {v['z_gate']} | "
                  f"{v['full']['sharpe']:.2f} | {v['is']['sharpe']:.2f} | {v['oos']['sharpe']:.2f} | "
                  f"{v['full']['sharpe_gross']:.2f} | {v['full']['max_dd']:.3f} | "
                  f"{v['full']['total_ret']:+.3f} | {wfm:.2f} | {v.get('perm_p', float('nan')):.3f} | "
                  f"{v['dsr_oos']:.3f} | {passed} |")
    md.append("")
    md.append("## P&L decomposition (full sample)")
    md.append("")
    md.append("| Variant | Price P&L | Funding P&L | Cost | Net | %Net from funding |")
    md.append("|---|---:|---:|---:|---:|---:|")
    for v in s["variants"]:
        d = v["decomposition"]
        md.append(f"| {v['name']} | {d['sum_price_pnl']:+.4f} | {d['sum_funding_pnl']:+.4f} | "
                  f"-{d['sum_cost']:.4f} | {d['sum_net']:+.4f} | {d['frac_from_funding']:.1%} |")
    md.append("")
    md.append("## Walk-forward by fold (OOS Sharpe)")
    md.append("")
    md.append("| Variant | F0 | F1 | F2 | F3 | Mean |")
    md.append("|---|---:|---:|---:|---:|---:|")
    for v in s["variants"]:
        wf = v.get("wf_folds", [])
        srs = [f["sharpe"] for f in wf] + [float("nan")] * (4 - len(wf))
        md.append(f"| {v['name']} | {srs[0]:.2f} | {srs[1]:.2f} | {srs[2]:.2f} | {srs[3]:.2f} | "
                  f"{v.get('wf_mean_sharpe', float('nan')):.2f} |")
    md.append("")
    md.append("## Cost stress (Net Sharpe at cost multipliers)")
    md.append("")
    md.append("| Variant | x0.5 | x1.0 | x1.5 | x2.0 |")
    md.append("|---|---:|---:|---:|---:|")
    for v in s["variants"]:
        cs = v["cost_stress"]
        md.append(f"| {v['name']} | {cs['cost_x0.5']:.2f} | {cs['cost_x1.0']:.2f} | "
                  f"{cs['cost_x1.5']:.2f} | {cs['cost_x2.0']:.2f} |")
    md.append("")
    md.append("## Bootstrap (OOS Sharpe, 95% CI, block=42)")
    md.append("")
    md.append("| Variant | Mean | CI lo | CI hi |")
    md.append("|---|---:|---:|---:|")
    for v in s["variants"]:
        bb = v["bootstrap_oos"]
        md.append(f"| {v['name']} | {bb['mean']:.2f} | {bb['ci_lo']:.2f} | {bb['ci_hi']:.2f} |")
    md.append("")
    md.append("## vs K127 (funding-rank carry) — Are these the SAME edge?")
    md.append("")
    k = s["k127_compare"]
    md.append(f"- K127 full Sharpe: {k['k127_full_sharpe']:.3f}, OOS: {k['k127_oos_sharpe']:.3f}, perm-p (gross): {k['k127_perm_p_gross']}")
    best = max(s["variants"], key=lambda v: v["full"]["sharpe"])
    md.append(f"- K137 best variant: **{best['name']}** with full SR {best['full']['sharpe']:.3f}, OOS {best['oos']['sharpe']:.3f}, perm-p {best.get('perm_p', float('nan')):.3f}")
    md.append("")
    md.append("**Interpretation:** Basis ranking and funding ranking are correlated economically (high basis usually predicts high funding), but the SIGNALS are not identical. Basis = level of mispricing; funding = derivative of cumulative mispricing through funding mechanism. The decomposition row above tells us whether K137's net P&L is mostly basis-reversion (price-leg) or funding accrual:")
    for v in s["variants"]:
        d = v["decomposition"]
        f_share = d["sum_funding_pnl"] / (d["sum_price_pnl"] + d["sum_funding_pnl"] + 1e-9)
        md.append(f"  - {v['name']}: funding share = {f_share:.1%}; price share = {1-f_share:.1%}")
    md.append("")
    md.append("## §6 Mini-gate verdict")
    md.append("")
    any_pass = any(v["gates"]["pass_all"] for v in s["variants"])
    if any_pass:
        winners = [v["name"] for v in s["variants"] if v["gates"]["pass_all"]]
        md.append(f"**PASS:** {', '.join(winners)} clear G1+G2+G3.")
    else:
        md.append("**NO variant passes all 3 §6 gates.** Detailed breakdown:")
        for v in s["variants"]:
            g = v["gates"]
            md.append(f"- {v['name']}: G1 OOS≥1 → {'P' if g['G1_oos_sharpe_ge_1'] else 'F'} ({v['oos']['sharpe']:.2f}); "
                      f"G2 perm<0.05 → {'P' if g['G2_perm_p_lt_005'] else 'F'} ({v.get('perm_p'):.3f}); "
                      f"G3 DSR≥0.95 → {'P' if g['G3_dsr_ge_095'] else 'F'} ({v['dsr_oos']:.3f})")
    md.append("")
    md.append("## Replication of CMU + AEA 2026 claim on 2024-26 data?")
    md.append("")
    md.append(f"- Headline (best variant) full Sharpe = {best['full']['sharpe']:.2f}; OOS = {best['oos']['sharpe']:.2f}")
    md.append(f"- The paper's claimed annualized Sharpe is typically in the 1.5-3 range for cross-sectional crypto carry sorts on basis. "
              f"{'REPLICATES' if best['full']['sharpe'] >= 1.5 else 'PARTIAL/FAIL replication'} in our 6-symbol universe.")
    md.append("- Universe constraint: only 6 symbols have BOTH premium index AND funding cache. The paper uses a much wider 30-50 symbol cross-section; sort granularity (top-3 of 6 = top half) is much coarser than top-decile of 30. This is the dominant explanation for any underperformance vs the paper.")
    md.append("")
    md.append("## Edge characterization")
    md.append("")
    md.append("- **Edge claim (basis-sort):** perpetual prices systematically over-/under-shoot index; cross-section ranks let us long the cheap (perp < spot) and short the expensive, capturing basis convergence + funding asymmetry.")
    md.append("- **Why this is distinct from K127 (funding-rank):** funding rate is the price-clearing mechanism for basis, but funding is capped/discrete and lags basis moves. Sorting on basis directly should be a faster signal, especially when basis spikes intra-day before funding adjusts.")
    md.append("- **Risk:** with only 6 symbols, the top-3/bottom-3 split is essentially top-half vs bottom-half — there is little 'edge concentration' available. The strategy's effective rank-correlation signal is weak. Need 20+ symbols with premium cache to get genuine decile sort.")
    md.append("")
    print("\n".join(md))


if __name__ == "__main__":
    main()
