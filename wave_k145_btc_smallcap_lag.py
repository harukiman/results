"""Wave K145 — BTC -> Small-Cap lead-lag with liquidity bucket filter.

Hypothesis (Springer APFM 2026): small-cap altcoins specifically respond
1-3 bars after BTC moves, with stronger effect on lower-liquidity symbols.
K110 failed because of all-symbol mixing and no liquidity filter.

Pre-registered method:
1. Compute per-symbol 30-day median USD volume (liquidity proxy).
2. Bucket symbols into Large (top 10), Mid (rank 11-25), Small (rank 26-50).
3. For each small-cap symbol: at bar t, take BTC log-return at lag -1.
   - If |BTC_lag1| > thr: position same direction as BTC_lag1, hold H bars.
4. Costs: 0.04% taker + 0.03% slippage per side (~14 bp round-trip).
5. Variants: thr in {0.5%, 1%, 2%}, hold H in {3, 6}.
6. Audit: IS/OOS, WF 4-fold, permutation n=300, block-bootstrap n=300,
   DSR, cost stress. Per-bucket Sharpe comparison.

Outputs:
- /Users/nekonaomichi/crypto-lab/wave_k145_btc_smallcap_lag.json
- /Users/nekonaomichi/crypto-lab/wave_k145_curves.json
"""

from __future__ import annotations

import json
import os
import time
import warnings
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
from scipy import stats

warnings.filterwarnings("ignore")

# -----------------------------------------------------------------------------
# Config
# -----------------------------------------------------------------------------
CACHE_DIR = "/Users/nekonaomichi/crypto-lab/cache"
OUT_RESULTS = "/Users/nekonaomichi/crypto-lab/wave_k145_btc_smallcap_lag.json"
OUT_CURVES = "/Users/nekonaomichi/crypto-lab/wave_k145_curves.json"

# All available symbols at 4h_730d (non-hist_premium)
ALL_SYMBOLS = [
    "AAVE", "ADA", "APT", "ARB", "ARKM", "ATOM", "AVAX", "BNB", "BOME", "BONK",
    "BTC", "COMP", "CRV", "DOGE", "DOT", "DYDX", "ENA", "ETC", "ETH", "FET",
    "FIL", "FLOKI", "GMX", "GRT", "ICP", "IMX", "INJ", "JTO", "JUP", "LDO",
    "LINK", "LTC", "MANTA", "NEAR", "ONDO", "OP", "PEPE", "POPCAT", "PYTH",
    "RENDER", "RUNE", "SEI", "SHIB", "SNX", "SOL", "STRK", "STX", "SUI",
    "SUSHI", "TAO", "TIA", "TRX", "UNI", "WIF", "WLD", "XRP",
]

# Cost model: taker 0.04% + slippage 0.03% per side = 14 bp round-trip
COST_ROUNDTRIP = 0.0014
COST_STRESS_FACTORS = [1.0, 1.5, 2.0]

# Liquidity rolling window (in 4H bars): 30 days = 180 bars
LIQ_WINDOW_BARS = 30 * 6  # 30d * 6 bars/day

# Buckets
BUCKET_LARGE = (0, 10)       # ranks 1..10
BUCKET_MID = (10, 25)        # ranks 11..25
BUCKET_SMALL = (25, 50)      # ranks 26..50

# Variants
VARIANTS = [
    {"name": "V_thresh1pct_hold3",  "thr": 0.010, "H": 3},   # primary
    {"name": "V_thresh05pct_hold3", "thr": 0.005, "H": 3},
    {"name": "V_thresh2pct_hold3",  "thr": 0.020, "H": 3},
    {"name": "V_thresh1pct_hold6",  "thr": 0.010, "H": 6},
]
PRIMARY_VARIANT = "V_thresh1pct_hold3"

# In-sample fraction
IS_FRAC = 0.70

# Annualization for 4H bars
BARS_PER_YEAR = int(365.25 * 24 / 4)  # 2191

# Audit sizes
N_PERM = 300
N_BOOT = 300
BOOT_BLOCK = 20
WF_FOLDS = 4

RNG = np.random.default_rng(20260524)


# -----------------------------------------------------------------------------
# Data loading
# -----------------------------------------------------------------------------
def load_prices_and_volume() -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Load close prices and quote_volume (USD) for all symbols, aligned."""
    closes, qvol = {}, {}
    for s in ALL_SYMBOLS:
        p = os.path.join(CACHE_DIR, f"{s}USDT_4h_730d.parquet")
        if not os.path.exists(p):
            print(f"  skip {s}: file missing")
            continue
        d = pd.read_parquet(p, columns=["open_time", "close", "quote_volume"])
        d = d.drop_duplicates(subset=["open_time"]).sort_values("open_time")
        d = d.set_index("open_time")
        closes[s] = d["close"].astype(float)
        qvol[s] = d["quote_volume"].astype(float)
    cdf = pd.concat(closes, axis=1).sort_index()
    vdf = pd.concat(qvol, axis=1).sort_index()
    # forward fill at most 1 bar
    cdf = cdf.ffill(limit=1)
    vdf = vdf.ffill(limit=1)
    # restrict to bars where BTC is non-null (required leader)
    if "BTC" not in cdf.columns:
        raise RuntimeError("BTC missing — cannot run lead-lag")
    cdf = cdf.dropna(subset=["BTC"])
    vdf = vdf.reindex(cdf.index)
    return cdf, vdf


# -----------------------------------------------------------------------------
# Liquidity bucketing
# -----------------------------------------------------------------------------
def classify_buckets(qvol: pd.DataFrame) -> Dict[str, List[str]]:
    """Rank symbols by median rolling USD volume; produce buckets."""
    # 30-day rolling median per symbol, take median of those (robust)
    roll_med = qvol.rolling(LIQ_WINDOW_BARS, min_periods=LIQ_WINDOW_BARS // 2).median()
    # Use median across full series of the rolling median for ranking
    liq_score = roll_med.median(axis=0).dropna()
    # rank descending — top liquidity first
    ranks = liq_score.sort_values(ascending=False)
    syms_sorted = ranks.index.tolist()

    n = len(syms_sorted)
    large = syms_sorted[BUCKET_LARGE[0]:min(BUCKET_LARGE[1], n)]
    mid = syms_sorted[BUCKET_MID[0]:min(BUCKET_MID[1], n)]
    small = syms_sorted[BUCKET_SMALL[0]:min(BUCKET_SMALL[1], n)]

    return {
        "large_cap": large,
        "mid_cap": mid,
        "small_cap": small,
        "liquidity_ranking": syms_sorted,
        "liquidity_scores": {s: float(liq_score[s]) for s in syms_sorted},
    }


# -----------------------------------------------------------------------------
# Strategy core
# -----------------------------------------------------------------------------
def build_btc_signal(btc_close: pd.Series, thr: float) -> pd.Series:
    """At bar t, look at BTC log return from t-2 -> t-1 (i.e., shift(1) of the
    contemporaneous BTC log-return). If |r| > thr, position = sign(r), else 0.

    Convention: signal at index t is the trade taken AT bar t, holding from
    t+1 ... t+H (so feature is fully in past — no look-ahead).
    """
    btc_r = np.log(btc_close).diff()  # r_t = close_t / close_{t-1}
    btc_r_lag1 = btc_r.shift(1)       # r_{t-1} (BTC's last completed move)
    sig = pd.Series(0.0, index=btc_close.index)
    sig[btc_r_lag1 > thr] = 1.0
    sig[btc_r_lag1 < -thr] = -1.0
    return sig


def bar_pnl_series(sig: pd.Series, alt_close: pd.Series, H: int,
                   cost_rt: float = COST_ROUNDTRIP) -> pd.Series:
    """Non-overlapping H-bar trades; PnL booked at exit bar.

    Position taken at bar t (decided from sig[t], computed from data at t-1).
    PnL = (close_{t+H} / close_{t} - 1) * sign - cost.
    """
    sig_v = sig.values
    close_v = alt_close.values
    idx = alt_close.index
    n = len(idx)
    bar_pnl = np.zeros(n)
    i = 0
    while i < n - H:
        s = sig_v[i]
        if s != 0.0 and not np.isnan(s):
            entry = close_v[i]
            exit_p = close_v[i + H]
            if entry > 0 and not np.isnan(exit_p):
                ret = (exit_p / entry - 1.0) * s
                pnl = ret - cost_rt
                exit_i = i + H
                bar_pnl[exit_i] += pnl
            i += H + 1  # non-overlapping
        else:
            i += 1
    return pd.Series(bar_pnl, index=idx)


# -----------------------------------------------------------------------------
# Metrics
# -----------------------------------------------------------------------------
def sharpe(pnl_bar: pd.Series) -> float:
    if len(pnl_bar) < 10 or pnl_bar.std(ddof=0) == 0:
        return 0.0
    return float(pnl_bar.mean() / pnl_bar.std(ddof=0) * np.sqrt(BARS_PER_YEAR))


def equity_curve(pnl_bar: pd.Series) -> pd.Series:
    return (1.0 + pnl_bar).cumprod()


def max_drawdown(eq: pd.Series) -> float:
    if len(eq) < 2:
        return 0.0
    peak = eq.cummax()
    dd = (eq / peak - 1.0).min()
    return float(dd)


def calmar(pnl_bar: pd.Series) -> float:
    eq = equity_curve(pnl_bar)
    if len(eq) < 2:
        return 0.0
    years = (eq.index[-1] - eq.index[0]).total_seconds() / (365.25 * 86400)
    if years <= 0:
        return 0.0
    final = eq.iloc[-1]
    if final <= 0:
        return 0.0
    cagr = final ** (1 / years) - 1.0
    mdd = max_drawdown(eq)
    if mdd >= 0:
        return 0.0
    return float(cagr / abs(mdd))


def deflated_sharpe(observed_sr: float, n_trials: int, sample_size: int) -> float:
    """Bailey-Lopez de Prado DSR (normal-assumption simplified)."""
    if n_trials <= 1 or sample_size < 20:
        return 0.0
    emc = 0.5772156649
    e_max = (1 - emc) * stats.norm.ppf(1 - 1.0 / n_trials) + \
            emc * stats.norm.ppf(1 - 1.0 / (n_trials * np.e))
    sr_se = np.sqrt(1.0 / (sample_size - 1))
    z = (observed_sr - e_max * sr_se) / sr_se
    return float(stats.norm.cdf(z))


# -----------------------------------------------------------------------------
# Backtest helpers
# -----------------------------------------------------------------------------
def backtest_bucket(symbols: List[str], prices: pd.DataFrame,
                    thr: float, H: int,
                    cost_rt: float = COST_ROUNDTRIP) -> Tuple[pd.Series, Dict[str, pd.Series]]:
    """Returns (equal-weight portfolio bar pnl, dict per-symbol bar pnl)."""
    btc_close = prices["BTC"].dropna()
    sig = build_btc_signal(btc_close, thr)
    per_sym = {}
    for sym in symbols:
        if sym == "BTC" or sym not in prices.columns:
            continue
        alt_close = prices[sym].dropna()
        common = sig.index.intersection(alt_close.index)
        if len(common) < 200:
            continue
        bp = bar_pnl_series(sig.loc[common], alt_close.loc[common], H, cost_rt)
        per_sym[sym] = bp
    if not per_sym:
        return pd.Series(dtype=float), {}
    port = pd.concat(per_sym, axis=1).fillna(0.0).mean(axis=1)
    return port, per_sym


def walk_forward_sharpe(pnl: pd.Series, n_folds: int = WF_FOLDS) -> List[Dict]:
    n = len(pnl)
    fs = n // n_folds
    out = []
    for f in range(n_folds):
        seg = pnl.iloc[f * fs:(f + 1) * fs]
        out.append({
            "fold": f,
            "n": int(len(seg)),
            "sharpe": sharpe(seg),
            "ret_total": float((1 + seg).prod() - 1),
            "mdd": max_drawdown(equity_curve(seg)),
        })
    return out


def block_bootstrap_sharpe(pnl: pd.Series, n_boot: int = N_BOOT,
                           block: int = BOOT_BLOCK) -> Dict:
    arr = pnl.values
    n = len(arr)
    if n < block * 2:
        return {"mean": 0.0, "ci_lo": 0.0, "ci_hi": 0.0}
    n_blocks = n // block
    boots = np.empty(n_boot)
    for b in range(n_boot):
        starts = RNG.integers(0, n - block + 1, size=n_blocks)
        sample = np.concatenate([arr[s:s + block] for s in starts])
        if sample.std(ddof=0) == 0:
            boots[b] = 0.0
        else:
            boots[b] = sample.mean() / sample.std(ddof=0) * np.sqrt(BARS_PER_YEAR)
    lo, hi = np.quantile(boots, [0.025, 0.975])
    return {"mean": float(boots.mean()), "ci_lo": float(lo), "ci_hi": float(hi)}


def permutation_test_one_sided(symbols: List[str], prices: pd.DataFrame,
                               thr: float, H: int,
                               observed_sharpe: float,
                               n_perm: int = N_PERM) -> Dict:
    """Shuffle BTC returns (preserving sign distribution if you want;
    here we do a full circular block shuffle of the BTC return series).

    For each permutation: rebuild BTC close from permuted log-returns
    starting from same anchor; rebuild signal; compute portfolio Sharpe.
    """
    btc_r = np.log(prices["BTC"]).diff().dropna()
    n = len(btc_r)
    nulls = np.empty(n_perm)
    block = BOOT_BLOCK
    base_idx = btc_r.index
    # Pre-extract alt close arrays
    alt_data = {}
    for sym in symbols:
        if sym == "BTC" or sym not in prices.columns:
            continue
        a = prices[sym].reindex(base_idx).dropna()
        if len(a) < 200:
            continue
        alt_data[sym] = a
    if not alt_data:
        return {"p_value": 1.0, "null_mean": 0.0, "null_std": 0.0,
                "null_q95": 0.0, "observed": observed_sharpe}

    btc_r_v = btc_r.values
    btc_anchor = float(prices["BTC"].reindex(base_idx).iloc[0])

    for p in range(n_perm):
        # Block-permute BTC returns to preserve some autocorr
        starts = RNG.integers(0, n - block + 1, size=(n // block) + 1)
        perm = np.concatenate([btc_r_v[s:s + block] for s in starts])[:n]
        # Reconstruct BTC close via cumulative product of (1+exp(perm)-1)
        # simpler: just use perm as log-returns; close_t = anchor * exp(cumsum)
        synth_log_close = np.log(btc_anchor) + np.cumsum(perm)
        synth_close = pd.Series(np.exp(synth_log_close), index=base_idx)
        # Build signal from synthetic BTC
        sig = build_btc_signal(synth_close, thr)
        per_sym_p = []
        for sym, a in alt_data.items():
            common = sig.index.intersection(a.index)
            if len(common) < 200:
                continue
            bp = bar_pnl_series(sig.loc[common], a.loc[common], H, COST_ROUNDTRIP)
            per_sym_p.append(bp)
        if not per_sym_p:
            nulls[p] = 0.0
            continue
        port = pd.concat(per_sym_p, axis=1).fillna(0.0).mean(axis=1)
        nulls[p] = sharpe(port)
    p_value = float((nulls >= observed_sharpe).mean())
    return {
        "p_value": p_value,
        "null_mean": float(nulls.mean()),
        "null_std": float(nulls.std()),
        "null_q95": float(np.quantile(nulls, 0.95)),
        "observed": float(observed_sharpe),
    }


# -----------------------------------------------------------------------------
# Main pipeline
# -----------------------------------------------------------------------------
def main():
    t0 = time.time()
    print("=" * 70)
    print("Wave K145 — BTC -> Small-Cap lead-lag with liquidity filter")
    print("=" * 70)

    prices, qvol = load_prices_and_volume()
    print(f"Loaded {prices.shape[1]} symbols, {len(prices)} bars, "
          f"range {prices.index[0]} -> {prices.index[-1]}")

    # ---- 1. Bucket classification ----
    buckets = classify_buckets(qvol)
    print(f"\nLarge-cap (top 10): {buckets['large_cap']}")
    print(f"Mid-cap   (11-25): {buckets['mid_cap']}")
    print(f"Small-cap (26-50): {buckets['small_cap']}")

    # ---- 2. Per-bucket backtest across variants ----
    results_by_bucket: Dict[str, Dict] = {}
    full_pnl_store: Dict[Tuple[str, str], pd.Series] = {}  # (bucket, variant) -> pnl
    per_sym_pnl_store: Dict[Tuple[str, str], Dict[str, pd.Series]] = {}

    for bucket_name in ("large_cap", "mid_cap", "small_cap"):
        symbols = buckets[bucket_name]
        # Exclude BTC if it appears in any bucket (likely large)
        symbols_clean = [s for s in symbols if s != "BTC"]
        bucket_res = {"symbols": symbols_clean, "variants": {}}
        for v in VARIANTS:
            port, per_sym = backtest_bucket(symbols_clean, prices, v["thr"], v["H"])
            if len(port) == 0:
                continue
            split = int(len(port) * IS_FRAC)
            is_p = port.iloc[:split]
            oos_p = port.iloc[split:]
            n_is_trades = int((is_p != 0).sum())
            n_oos_trades = int((oos_p != 0).sum())
            bucket_res["variants"][v["name"]] = {
                "thr": v["thr"], "H": v["H"],
                "is_sharpe": sharpe(is_p),
                "oos_sharpe": sharpe(oos_p),
                "full_sharpe": sharpe(port),
                "is_calmar": calmar(is_p),
                "oos_calmar": calmar(oos_p),
                "is_mdd": max_drawdown(equity_curve(is_p)),
                "oos_mdd": max_drawdown(equity_curve(oos_p)),
                "is_total_ret": float((1 + is_p).prod() - 1),
                "oos_total_ret": float((1 + oos_p).prod() - 1),
                "is_trades": n_is_trades,
                "oos_trades": n_oos_trades,
                "n_symbols_used": len(per_sym),
            }
            full_pnl_store[(bucket_name, v["name"])] = port
            per_sym_pnl_store[(bucket_name, v["name"])] = per_sym
        results_by_bucket[bucket_name] = bucket_res

    # Print bucket comparison
    print("\n--- Bucket comparison (full sample Sharpe) ---")
    for v in VARIANTS:
        line = f"  {v['name']:25s}: "
        for b in ("large_cap", "mid_cap", "small_cap"):
            shv = results_by_bucket[b]["variants"].get(v["name"], {}).get("full_sharpe", float('nan'))
            line += f"{b}={shv:+.2f}  "
        print(line)

    # ---- 3. Per-symbol Sharpe within small-cap (for primary variant) ----
    primary = next(v for v in VARIANTS if v["name"] == PRIMARY_VARIANT)
    small_per_sym = per_sym_pnl_store.get(("small_cap", PRIMARY_VARIANT), {})
    per_sym_results = {}
    for sym, bp in small_per_sym.items():
        split = int(len(bp) * IS_FRAC)
        is_p = bp.iloc[:split]
        oos_p = bp.iloc[split:]
        per_sym_results[sym] = {
            "is_sharpe": sharpe(is_p),
            "oos_sharpe": sharpe(oos_p),
            "full_sharpe": sharpe(bp),
            "is_trades": int((is_p != 0).sum()),
            "oos_trades": int((oos_p != 0).sum()),
        }
    print(f"\nPer-symbol small-cap (primary variant {PRIMARY_VARIANT}):")
    sorted_syms = sorted(per_sym_results.items(),
                         key=lambda x: x[1]["full_sharpe"], reverse=True)
    for sym, r in sorted_syms[:15]:
        print(f"  {sym:8s} IS Sh={r['is_sharpe']:+.2f} ({r['is_trades']:3d} tr) "
              f"OOS Sh={r['oos_sharpe']:+.2f} ({r['oos_trades']:3d} tr) "
              f"FULL={r['full_sharpe']:+.2f}")

    # ---- 4. Deep audit on small-cap primary ----
    audit = {}
    small_primary_port = full_pnl_store.get(("small_cap", PRIMARY_VARIANT), pd.Series(dtype=float))
    if len(small_primary_port) > 0:
        split = int(len(small_primary_port) * IS_FRAC)
        port_is = small_primary_port.iloc[:split]
        port_oos = small_primary_port.iloc[split:]
        full_sh = sharpe(small_primary_port)

        # 4a Walk-forward
        wf = walk_forward_sharpe(small_primary_port, WF_FOLDS)
        print(f"\nWalk-forward (small-cap primary, {WF_FOLDS} folds):")
        for f in wf:
            print(f"  fold{f['fold']}: Sh={f['sharpe']:+.2f} ret={f['ret_total']:+.4f} mdd={f['mdd']:+.4f}")

        # 4b Block bootstrap CI
        print("Block bootstrap CI...")
        t_b = time.time()
        boot = block_bootstrap_sharpe(small_primary_port, N_BOOT, BOOT_BLOCK)
        print(f"  Boot mean={boot['mean']:+.2f} CI=[{boot['ci_lo']:+.2f}, {boot['ci_hi']:+.2f}] ({time.time()-t_b:.1f}s)")

        # 4c Permutation
        print(f"Permutation test n={N_PERM}...")
        t_p = time.time()
        perm = permutation_test_one_sided(
            buckets["small_cap"], prices, primary["thr"], primary["H"],
            observed_sharpe=full_sh, n_perm=N_PERM)
        print(f"  Observed Sh={perm['observed']:+.2f}, null mean={perm['null_mean']:+.2f}, "
              f"p={perm['p_value']:.4f} ({time.time()-t_p:.1f}s)")

        # 4d DSR
        n_trials = len(VARIANTS) * 3  # 4 variants * 3 buckets
        sample_size = int((small_primary_port != 0).sum())
        dsr = deflated_sharpe(full_sh, n_trials, sample_size)
        print(f"DSR={dsr:.4f} (n_trials={n_trials}, sample_size={sample_size})")

        # 4e Cost stress
        cost_stress = {}
        for f in COST_STRESS_FACTORS:
            cs_cost = COST_ROUNDTRIP * f
            port_s, _ = backtest_bucket(buckets["small_cap"], prices,
                                        primary["thr"], primary["H"], cs_cost)
            split_s = int(len(port_s) * IS_FRAC)
            cost_stress[f"cost_x{f}"] = {
                "cost_rt": cs_cost,
                "is_sharpe": sharpe(port_s.iloc[:split_s]),
                "oos_sharpe": sharpe(port_s.iloc[split_s:]),
                "full_sharpe": sharpe(port_s),
            }
        print("Cost stress:")
        for k, v in cost_stress.items():
            print(f"  {k}: IS={v['is_sharpe']:+.2f} OOS={v['oos_sharpe']:+.2f} FULL={v['full_sharpe']:+.2f}")

        audit = {
            "walk_forward": wf,
            "block_bootstrap": boot,
            "permutation": perm,
            "dsr": dsr,
            "n_trials": n_trials,
            "sample_size": sample_size,
            "cost_stress": cost_stress,
        }

    # ---- 5. §6 gates ----
    # Use small-cap primary OOS metrics
    small_v_metrics = results_by_bucket["small_cap"]["variants"].get(PRIMARY_VARIANT, {})
    oos_sh = small_v_metrics.get("oos_sharpe", 0.0)
    oos_trades = small_v_metrics.get("oos_trades", 0)
    oos_calmar = small_v_metrics.get("oos_calmar", 0.0)
    oos_mdd = small_v_metrics.get("oos_mdd", 0.0)
    perm_p = audit.get("permutation", {}).get("p_value", 1.0) if audit else 1.0
    boot_lo = audit.get("block_bootstrap", {}).get("ci_lo", -999.0) if audit else -999.0
    dsr = audit.get("dsr", 0.0) if audit else 0.0
    wf_metrics = audit.get("walk_forward", []) if audit else []
    pos_folds = sum(1 for f in wf_metrics if f["sharpe"] > 0)

    # Bucket-edge gate: small > large by >= 0.5 Sharpe?
    large_sh = results_by_bucket["large_cap"]["variants"].get(PRIMARY_VARIANT, {}).get("oos_sharpe", 0.0)
    bucket_edge = oos_sh - large_sh

    gates = {
        "g1_oos_sharpe_gt_1": oos_sh > 1.0,
        "g2_oos_trades_gte_30": oos_trades >= 30,
        "g3_perm_p_lt_005": perm_p < 0.05,
        "g4_bootstrap_lo_gt_0": boot_lo > 0,
        "g5_dsr_gt_095": dsr > 0.95,
        "g6_wf_3of4_positive": pos_folds >= 3,
        "g7_oos_mdd_gt_neg30": oos_mdd > -0.30,
        "g8_bucket_edge_gt_05": bucket_edge > 0.5,
    }
    n_pass = sum(gates.values())
    overall = "PASS" if n_pass >= 6 else "REJECT"
    print(f"\n§6 GATES: {n_pass}/8 — VERDICT {overall}")
    for g, ok in gates.items():
        print(f"  [{('Y' if ok else 'N')}] {g}")

    # ---- 6. Output ----
    results = {
        "wave": "K145",
        "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
        "hypothesis": "BTC -> small-cap lead-lag (1-3 bar response), "
                      "stronger on lower-liquidity symbols (Springer APFM 2026)",
        "data_range": {
            "start": str(prices.index[0]),
            "end": str(prices.index[-1]),
            "n_bars": int(len(prices)),
        },
        "config": {
            "cost_roundtrip": COST_ROUNDTRIP,
            "is_frac": IS_FRAC,
            "n_perm": N_PERM,
            "n_boot": N_BOOT,
            "boot_block": BOOT_BLOCK,
            "wf_folds": WF_FOLDS,
            "variants": VARIANTS,
            "primary_variant": PRIMARY_VARIANT,
            "bucket_ranges": {
                "large_cap": list(BUCKET_LARGE),
                "mid_cap": list(BUCKET_MID),
                "small_cap": list(BUCKET_SMALL),
            },
        },
        "buckets": {
            "large_cap": buckets["large_cap"],
            "mid_cap": buckets["mid_cap"],
            "small_cap": buckets["small_cap"],
            "liquidity_ranking": buckets["liquidity_ranking"],
            "liquidity_scores": buckets["liquidity_scores"],
        },
        "results_by_bucket": results_by_bucket,
        "per_symbol_small_cap_primary": per_sym_results,
        "audit_small_cap_primary": audit,
        "bucket_edge_vs_large": bucket_edge,
        "gates": gates,
        "n_gates_passed": n_pass,
        "verdict": overall,
    }

    with open(OUT_RESULTS, "w") as f:
        json.dump(results, f, indent=2, default=str)

    # Curves payload: equity curves per bucket (primary variant) + small per-sym
    curves = {"buckets": {}, "per_symbol_small_cap": {}}
    for b in ("large_cap", "mid_cap", "small_cap"):
        port = full_pnl_store.get((b, PRIMARY_VARIANT))
        if port is None or len(port) == 0:
            continue
        eq = equity_curve(port)
        split = int(len(port) * IS_FRAC)
        curves["buckets"][b] = {
            "timestamps": [t.isoformat() for t in eq.index],
            "equity": eq.tolist(),
            "is_end_idx": split,
        }
    for sym, bp in small_per_sym.items():
        eq = equity_curve(bp)
        curves["per_symbol_small_cap"][sym] = {
            "timestamps": [t.isoformat() for t in eq.index],
            "equity": eq.tolist(),
        }
    with open(OUT_CURVES, "w") as f:
        json.dump(curves, f, default=str)

    print(f"\nWrote {OUT_RESULTS}")
    print(f"Wrote {OUT_CURVES}")
    print(f"Total wall time: {time.time()-t0:.1f}s")


if __name__ == "__main__":
    main()
