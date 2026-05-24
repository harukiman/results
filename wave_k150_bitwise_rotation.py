"""Wave K150 — Bitwise BTC/ETH Trend Rotation (R5-6 retry of stalled K138).

Hypothesis (Bitwise 2026 outlook):
At each 4H bar, evaluate trend of BTC and ETH using an EMA filter.
  * If BOTH BTC > EMA_N AND ETH > EMA_N -> long 50/50 BTC/ETH
  * Otherwise                            -> flat (USDT)

Pre-registered method (LEAN — single asset pair, single regime logic):
1. EMA_N trend filter on close.
2. Both trends up -> long 50/50.
3. Either trend down -> flat.
4. Re-evaluate every 4H bar; rebalance only on regime change (no fees while
   inside the same regime).
5. Costs: 0.04% taker + 0.03% slippage per side. Round-trip on rotation
   is charged per leg actually traded.

Variants (lean, only 3):
- V_ema200            : EMA200 trend filter (primary / Bitwise claim)
- V_ema100            : Faster trend filter
- V_ema200_long_only  : Stricter — same as V_ema200, but ANY trend down -> flat
                        (functionally identical here since both must be up;
                         retained as named variant for the spec).

Audit:
- IS 70% / OOS 30%, single-split
- Sharpe, MaxDD, AnnRet, WinRate (on bar log-returns)
- Permutation n=200 (block-permute joint BTC/ETH return series)
- Bootstrap n=200 (block bootstrap on portfolio bar returns)
- WF 3-fold
- DSR with N_trials=3

Outputs:
- /Users/nekonaomichi/crypto-lab/wave_k150_bitwise_rotation.json
- /Users/nekonaomichi/crypto-lab/wave_k150_curves.json
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
OUT_RESULTS = "/Users/nekonaomichi/crypto-lab/wave_k150_bitwise_rotation.json"
OUT_CURVES = "/Users/nekonaomichi/crypto-lab/wave_k150_curves.json"

SYMBOLS = ["BTC", "ETH"]

# Cost: 0.04% taker + 0.03% slippage per side = 0.07% per side
COST_PER_SIDE = 0.0007  # applied per leg when leg position changes

# Variants
VARIANTS = [
    {"name": "V_ema200",           "ema": 200, "mode": "both_up"},
    {"name": "V_ema100",           "ema": 100, "mode": "both_up"},
    {"name": "V_ema200_long_only", "ema": 200, "mode": "all_up_strict"},
]
PRIMARY_VARIANT = "V_ema200"

IS_FRAC = 0.70

# Annualization for 4H bars
BARS_PER_YEAR = int(365.25 * 24 / 4)  # 2191

# Audit sizes (LEAN)
N_PERM = 200
N_BOOT = 200
BOOT_BLOCK = 20
WF_FOLDS = 3
N_TRIALS_DSR = 3  # number of variants tried

RNG = np.random.default_rng(20260524)


# -----------------------------------------------------------------------------
# Data loading
# -----------------------------------------------------------------------------
def load_prices() -> pd.DataFrame:
    closes = {}
    for s in SYMBOLS:
        p = os.path.join(CACHE_DIR, f"{s}USDT_4h_730d.parquet")
        if not os.path.exists(p):
            raise FileNotFoundError(f"missing cache: {p}")
        d = pd.read_parquet(p, columns=["open_time", "close"])
        d = d.drop_duplicates(subset=["open_time"]).sort_values("open_time")
        d = d.set_index("open_time")
        closes[s] = d["close"].astype(float)
    df = pd.concat(closes, axis=1).sort_index()
    df = df.dropna()  # require both symbols present
    return df


# -----------------------------------------------------------------------------
# Strategy core
# -----------------------------------------------------------------------------
def compute_signal(prices: pd.DataFrame, ema_n: int, mode: str) -> pd.DataFrame:
    """Return DataFrame with weight columns for BTC and ETH at each bar.

    Convention: weights at bar t are DECIDED at bar t (using info up to t),
    and APPLIED to the return realized between bar t and t+1
    (i.e., shifted forward by 1 when computing pnl).
    """
    ema = prices.ewm(span=ema_n, adjust=False, min_periods=ema_n).mean()
    above = prices > ema

    btc_up = above["BTC"]
    eth_up = above["ETH"]

    if mode == "both_up":
        in_pos = btc_up & eth_up
    elif mode == "all_up_strict":
        # Identical condition for 2-asset case; kept for spec parity
        in_pos = btc_up & eth_up
    else:
        raise ValueError(f"unknown mode {mode}")

    w_btc = np.where(in_pos, 0.5, 0.0)
    w_eth = np.where(in_pos, 0.5, 0.0)
    w = pd.DataFrame({"BTC": w_btc, "ETH": w_eth}, index=prices.index)
    # Until EMA warmed up, force flat
    warm_mask = prices.index < prices.index[ema_n - 1]
    w.loc[warm_mask] = 0.0
    return w


def backtest(prices: pd.DataFrame, weights: pd.DataFrame,
             cost_per_side: float = COST_PER_SIDE) -> Tuple[pd.Series, Dict]:
    """Return bar log-pnl series and stats dict.

    For each symbol leg, charge cost_per_side * |w_t - w_{t-1}|.
    """
    log_ret = np.log(prices).diff().fillna(0.0)
    # Weights are decided at bar t and earn return from t -> t+1
    # so realized pnl at bar t+1 uses weights from bar t.
    w_applied = weights.shift(1).fillna(0.0)
    # Per-leg cost driven by change in applied weight (= change in target one bar earlier)
    leg_turnover = (w_applied.diff().abs().fillna(0.0))
    cost_bar = leg_turnover.sum(axis=1) * cost_per_side
    gross = (w_applied * log_ret).sum(axis=1)
    net = gross - cost_bar
    stats_d = {
        "n_rebalances": int((weights.diff().abs().sum(axis=1) > 0).sum()),
        "frac_time_invested": float((w_applied.sum(axis=1) > 0).mean()),
        "n_bars": int(len(net)),
        "total_cost": float(cost_bar.sum()),
    }
    return net, stats_d


# -----------------------------------------------------------------------------
# Metrics
# -----------------------------------------------------------------------------
def sharpe(pnl_bar: pd.Series) -> float:
    if len(pnl_bar) < 10 or pnl_bar.std(ddof=0) == 0:
        return 0.0
    return float(pnl_bar.mean() / pnl_bar.std(ddof=0) * np.sqrt(BARS_PER_YEAR))


def equity_curve(pnl_bar: pd.Series) -> pd.Series:
    """Equity from log-returns: exp(cumsum)."""
    return np.exp(pnl_bar.cumsum())


def max_drawdown(eq: pd.Series) -> float:
    if len(eq) < 2:
        return 0.0
    peak = eq.cummax()
    dd = (eq / peak - 1.0).min()
    return float(dd)


def ann_return(pnl_bar: pd.Series) -> float:
    if len(pnl_bar) < 2:
        return 0.0
    years = (pnl_bar.index[-1] - pnl_bar.index[0]).total_seconds() / (365.25 * 86400)
    if years <= 0:
        return 0.0
    eq_final = float(np.exp(pnl_bar.sum()))
    if eq_final <= 0:
        return 0.0
    return float(eq_final ** (1 / years) - 1.0)


def win_rate(pnl_bar: pd.Series) -> float:
    active = pnl_bar[pnl_bar != 0]
    if len(active) == 0:
        return 0.0
    return float((active > 0).mean())


def calmar(pnl_bar: pd.Series) -> float:
    ar = ann_return(pnl_bar)
    mdd = max_drawdown(equity_curve(pnl_bar))
    if mdd >= 0:
        return 0.0
    return float(ar / abs(mdd))


def deflated_sharpe(observed_sr: float, n_trials: int, sample_size: int) -> float:
    if n_trials <= 1 or sample_size < 20:
        return 0.0
    emc = 0.5772156649
    e_max = (1 - emc) * stats.norm.ppf(1 - 1.0 / n_trials) + \
            emc * stats.norm.ppf(1 - 1.0 / (n_trials * np.e))
    sr_se = np.sqrt(1.0 / (sample_size - 1))
    z = (observed_sr - e_max * sr_se) / sr_se
    return float(stats.norm.cdf(z))


# -----------------------------------------------------------------------------
# Audit helpers
# -----------------------------------------------------------------------------
def walk_forward(pnl: pd.Series, n_folds: int = WF_FOLDS) -> List[Dict]:
    n = len(pnl)
    fs = n // n_folds
    out = []
    for f in range(n_folds):
        seg = pnl.iloc[f * fs:(f + 1) * fs]
        out.append({
            "fold": f,
            "n": int(len(seg)),
            "sharpe": sharpe(seg),
            "ann_return": ann_return(seg),
            "mdd": max_drawdown(equity_curve(seg)),
        })
    return out


def block_bootstrap(pnl: pd.Series, n_boot: int = N_BOOT,
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
    return {"mean": float(boots.mean()), "ci_lo": float(lo), "ci_hi": float(hi),
            "n_boot": n_boot, "block": block}


def permutation_test(prices: pd.DataFrame, ema_n: int, mode: str,
                     observed_sharpe: float, n_perm: int = N_PERM) -> Dict:
    """Block-permute the JOINT BTC/ETH log-return matrix to preserve cross-asset
    contemporaneous structure but destroy any persistent trend the EMA picks up.

    For each permutation: build synthetic prices from permuted joint log-returns
    (anchored at the original first close), recompute signal, recompute pnl,
    record Sharpe.
    """
    log_r = np.log(prices).diff().dropna()
    n = len(log_r)
    block = BOOT_BLOCK
    nulls = np.empty(n_perm)
    anchor_btc = float(prices["BTC"].iloc[1])  # one bar after the dropna point
    anchor_eth = float(prices["ETH"].iloc[1])

    log_r_arr = log_r.values  # shape (n, 2): cols BTC, ETH
    idx = log_r.index

    for p in range(n_perm):
        starts = RNG.integers(0, n - block + 1, size=(n // block) + 1)
        # block-permute rows JOINTLY (preserves contemporaneous corr)
        perm = np.concatenate([log_r_arr[s:s + block, :] for s in starts], axis=0)[:n]
        synth_log_btc = np.log(anchor_btc) + np.cumsum(perm[:, 0])
        synth_log_eth = np.log(anchor_eth) + np.cumsum(perm[:, 1])
        synth = pd.DataFrame({
            "BTC": np.exp(synth_log_btc),
            "ETH": np.exp(synth_log_eth),
        }, index=idx)
        w = compute_signal(synth, ema_n, mode)
        pnl_p, _ = backtest(synth, w)
        nulls[p] = sharpe(pnl_p)

    p_value = float((nulls >= observed_sharpe).mean())
    return {
        "n_perm": n_perm,
        "p_value": p_value,
        "null_mean": float(nulls.mean()),
        "null_std": float(nulls.std()),
        "null_q95": float(np.quantile(nulls, 0.95)),
        "observed": float(observed_sharpe),
    }


# -----------------------------------------------------------------------------
# Buy & hold baselines
# -----------------------------------------------------------------------------
def buy_hold(prices: pd.DataFrame, sym: str) -> pd.Series:
    return np.log(prices[sym]).diff().fillna(0.0)


def buy_hold_50_50(prices: pd.DataFrame) -> pd.Series:
    lr = np.log(prices).diff().fillna(0.0)
    return 0.5 * lr["BTC"] + 0.5 * lr["ETH"]


# -----------------------------------------------------------------------------
# Variant metrics packager
# -----------------------------------------------------------------------------
def variant_metrics(pnl: pd.Series) -> Dict:
    split = int(len(pnl) * IS_FRAC)
    is_p, oos_p = pnl.iloc[:split], pnl.iloc[split:]
    return {
        "is_sharpe": sharpe(is_p),
        "oos_sharpe": sharpe(oos_p),
        "full_sharpe": sharpe(pnl),
        "is_ann_return": ann_return(is_p),
        "oos_ann_return": ann_return(oos_p),
        "full_ann_return": ann_return(pnl),
        "is_mdd": max_drawdown(equity_curve(is_p)),
        "oos_mdd": max_drawdown(equity_curve(oos_p)),
        "full_mdd": max_drawdown(equity_curve(pnl)),
        "is_win_rate": win_rate(is_p),
        "oos_win_rate": win_rate(oos_p),
        "full_win_rate": win_rate(pnl),
        "is_calmar": calmar(is_p),
        "oos_calmar": calmar(oos_p),
        "full_calmar": calmar(pnl),
    }


# -----------------------------------------------------------------------------
# Main pipeline
# -----------------------------------------------------------------------------
def main():
    t0 = time.time()
    print("=" * 70)
    print("Wave K150 — Bitwise BTC/ETH Trend Rotation (R5-6 retry K138)")
    print("=" * 70)

    prices = load_prices()
    print(f"Loaded BTC+ETH, {len(prices)} bars, "
          f"range {prices.index[0]} -> {prices.index[-1]}")

    # ---- Run all variants ----
    variant_pnl: Dict[str, pd.Series] = {}
    variant_stats: Dict[str, Dict] = {}
    variant_results: Dict[str, Dict] = {}

    for v in VARIANTS:
        w = compute_signal(prices, v["ema"], v["mode"])
        pnl, st = backtest(prices, w)
        variant_pnl[v["name"]] = pnl
        variant_stats[v["name"]] = st
        m = variant_metrics(pnl)
        m["config"] = {"ema": v["ema"], "mode": v["mode"]}
        m["n_rebalances"] = st["n_rebalances"]
        m["frac_time_invested"] = st["frac_time_invested"]
        m["total_cost"] = st["total_cost"]
        variant_results[v["name"]] = m

    print("\n--- Variant comparison ---")
    print(f"{'variant':22s} {'IS_Sh':>7s} {'OOS_Sh':>7s} {'FULL_Sh':>8s} "
          f"{'AnnRet':>8s} {'MDD':>8s} {'WinRt':>7s} {'Rebal':>6s} {'%Invest':>8s}")
    for v in VARIANTS:
        m = variant_results[v["name"]]
        print(f"{v['name']:22s} {m['is_sharpe']:+7.2f} {m['oos_sharpe']:+7.2f} "
              f"{m['full_sharpe']:+8.2f} {m['full_ann_return']*100:+7.1f}% "
              f"{m['full_mdd']*100:+7.1f}% {m['full_win_rate']*100:6.1f}% "
              f"{m['n_rebalances']:6d} {m['frac_time_invested']*100:7.1f}%")

    # ---- Baselines ----
    bh_btc = buy_hold(prices, "BTC")
    bh_eth = buy_hold(prices, "ETH")
    bh_5050 = buy_hold_50_50(prices)
    baselines = {
        "BH_BTC": variant_metrics(bh_btc),
        "BH_ETH": variant_metrics(bh_eth),
        "BH_50_50": variant_metrics(bh_5050),
    }
    print("\n--- Baselines (no costs) ---")
    for k, m in baselines.items():
        print(f"  {k:10s} FULL Sh={m['full_sharpe']:+.2f} AnnRet={m['full_ann_return']*100:+6.1f}% "
              f"MDD={m['full_mdd']*100:+6.1f}%")

    # ---- Deep audit on primary ----
    primary_pnl = variant_pnl[PRIMARY_VARIANT]
    primary_cfg = next(v for v in VARIANTS if v["name"] == PRIMARY_VARIANT)
    full_sh = sharpe(primary_pnl)

    print(f"\n=== Deep audit on {PRIMARY_VARIANT} ===")

    wf = walk_forward(primary_pnl, WF_FOLDS)
    print(f"Walk-forward {WF_FOLDS}-fold:")
    for f in wf:
        print(f"  fold{f['fold']}: Sh={f['sharpe']:+.2f} "
              f"AnnRet={f['ann_return']*100:+6.1f}% MDD={f['mdd']*100:+6.1f}%")
    pos_folds = sum(1 for f in wf if f["sharpe"] > 0)

    t_b = time.time()
    boot = block_bootstrap(primary_pnl, N_BOOT, BOOT_BLOCK)
    print(f"Bootstrap n={N_BOOT}: mean={boot['mean']:+.2f} "
          f"CI=[{boot['ci_lo']:+.2f},{boot['ci_hi']:+.2f}] ({time.time()-t_b:.1f}s)")

    t_p = time.time()
    perm = permutation_test(prices, primary_cfg["ema"], primary_cfg["mode"],
                            observed_sharpe=full_sh, n_perm=N_PERM)
    print(f"Permutation n={N_PERM}: obs={perm['observed']:+.2f} "
          f"null_mean={perm['null_mean']:+.2f} p={perm['p_value']:.4f} "
          f"({time.time()-t_p:.1f}s)")

    sample_size = int(len(primary_pnl))
    dsr = deflated_sharpe(full_sh, N_TRIALS_DSR, sample_size)
    print(f"DSR={dsr:.4f} (n_trials={N_TRIALS_DSR}, sample_size={sample_size})")

    audit = {
        "walk_forward": wf,
        "wf_positive_folds": pos_folds,
        "block_bootstrap": boot,
        "permutation": perm,
        "dsr": dsr,
        "n_trials": N_TRIALS_DSR,
        "sample_size": sample_size,
    }

    # ---- §6 gates (lean) ----
    m = variant_results[PRIMARY_VARIANT]
    oos_sh = m["oos_sharpe"]
    oos_mdd = m["oos_mdd"]
    oos_calmar = m["oos_calmar"]
    n_rebal = m["n_rebalances"]
    bh_oos_sh = baselines["BH_50_50"]["oos_sharpe"]
    edge_vs_bh = oos_sh - bh_oos_sh

    gates = {
        "g1_oos_sharpe_gt_1":      oos_sh > 1.0,
        "g2_n_rebalances_gte_5":   n_rebal >= 5,
        "g3_perm_p_lt_005":        perm["p_value"] < 0.05,
        "g4_bootstrap_lo_gt_0":    boot["ci_lo"] > 0,
        "g5_dsr_gt_095":           dsr > 0.95,
        "g6_wf_2of3_positive":     pos_folds >= 2,
        "g7_oos_mdd_gt_neg25":     oos_mdd > -0.25,
        "g8_edge_vs_bh5050_gt_03": edge_vs_bh > 0.30,
    }
    n_pass = sum(gates.values())
    overall = "PASS" if n_pass >= 6 else "REJECT"
    print(f"\n§6 GATES: {n_pass}/8 — VERDICT {overall}")
    for g, ok in gates.items():
        print(f"  [{('Y' if ok else 'N')}] {g}")

    # ---- Bitwise claim assessment ----
    # Bitwise 2026 claim: regime rotation outperforms passive BTC/ETH.
    # We replicate IF primary OOS Sharpe > BH_50_50 OOS Sharpe AND OOS MDD better.
    replicated = (oos_sh > bh_oos_sh) and (oos_mdd > baselines["BH_50_50"]["oos_mdd"])
    print(f"\nBitwise 2026 replicate? {'YES' if replicated else 'NO'} "
          f"(OOS Sh {oos_sh:+.2f} vs BH50/50 {bh_oos_sh:+.2f}; "
          f"OOS MDD {oos_mdd*100:+.1f}% vs BH50/50 {baselines['BH_50_50']['oos_mdd']*100:+.1f}%)")

    # ---- Output JSON ----
    results = {
        "wave": "K150",
        "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
        "hypothesis": "Bitwise 2026 BTC/ETH trend rotation: 50/50 long when both "
                      "above EMA, else flat. Outperforms passive BH on Sharpe + MDD.",
        "data_range": {
            "start": str(prices.index[0]),
            "end": str(prices.index[-1]),
            "n_bars": int(len(prices)),
        },
        "config": {
            "symbols": SYMBOLS,
            "cost_per_side": COST_PER_SIDE,
            "is_frac": IS_FRAC,
            "variants": VARIANTS,
            "primary_variant": PRIMARY_VARIANT,
            "n_perm": N_PERM,
            "n_boot": N_BOOT,
            "boot_block": BOOT_BLOCK,
            "wf_folds": WF_FOLDS,
            "n_trials_dsr": N_TRIALS_DSR,
        },
        "variant_results": variant_results,
        "baselines": baselines,
        "audit_primary": audit,
        "primary_variant": PRIMARY_VARIANT,
        "edge_vs_bh50_50": edge_vs_bh,
        "gates": gates,
        "n_gates_passed": n_pass,
        "verdict": overall,
        "bitwise_2026_replicated": replicated,
    }
    with open(OUT_RESULTS, "w") as f:
        json.dump(results, f, indent=2, default=str)

    # ---- Curves ----
    curves = {"variants": {}, "baselines": {}}
    for v in VARIANTS:
        pnl = variant_pnl[v["name"]]
        eq = equity_curve(pnl)
        split = int(len(pnl) * IS_FRAC)
        curves["variants"][v["name"]] = {
            "timestamps": [t.isoformat() for t in eq.index],
            "equity": eq.tolist(),
            "is_end_idx": split,
        }
    for name, series in [("BH_BTC", bh_btc), ("BH_ETH", bh_eth), ("BH_50_50", bh_5050)]:
        eq = equity_curve(series)
        curves["baselines"][name] = {
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
