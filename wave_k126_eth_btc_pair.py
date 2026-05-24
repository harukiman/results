"""
Wave K126 — ETH-BTC Funding Spread Pair (R4-15)

Hypothesis: When ETH funding > BTC funding by extreme dispersion, ETH leads BTC
in next 1-2 weeks. Use 30d z-score of (ETH - BTC) funding spread; dollar-neutral
pair trade.

Pre-registered method per task spec.
"""

import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

ROOT = Path("/Users/nekonaomichi/crypto-lab")
CACHE = ROOT / "cache"

OUT_PY_JSON = ROOT / "wave_k126_eth_btc_pair.json"
OUT_CURVES = ROOT / "wave_k126_curves.json"

RNG = np.random.default_rng(20260524)

# Costs per leg per side (taker+slippage proxy)
COST_PER_SIDE = 0.0004 + 0.0003  # 0.07%
# Pair trade has 2 legs * 2 sides (open+close) = 4 transactions
COST_PER_TRADE_PAIR = COST_PER_SIDE * 4  # 0.28% per round-trip


# ---------------------------------------------------------------------
# 1) Load + align data
# ---------------------------------------------------------------------
def load_data():
    fr_btc = pd.read_parquet(CACHE / "bybit_fr_BTCUSDT_730d.parquet")
    fr_eth = pd.read_parquet(CACHE / "bybit_fr_ETHUSDT_730d.parquet")
    btc_px = pd.read_parquet(CACHE / "BTCUSDT_4h_730d.parquet")
    eth_px = pd.read_parquet(CACHE / "ETHUSDT_4h_730d.parquet")

    fr_btc = fr_btc.rename(columns={"funding_rate": "fr_btc"}).set_index("timestamp").sort_index()
    fr_eth = fr_eth.rename(columns={"funding_rate": "fr_eth"}).set_index("timestamp").sort_index()
    fr = fr_btc.join(fr_eth, how="inner")
    fr["spread"] = fr["fr_eth"] - fr["fr_btc"]

    btc_px = btc_px.set_index("open_time").sort_index()[["close"]].rename(columns={"close": "btc_close"})
    eth_px = eth_px.set_index("open_time").sort_index()[["close"]].rename(columns={"close": "eth_close"})
    px = btc_px.join(eth_px, how="inner")
    return fr, px


# ---------------------------------------------------------------------
# 2) Build signal
# ---------------------------------------------------------------------
def build_signal(fr: pd.DataFrame, z_enter: float, z_exit: float, one_sided: bool = False) -> pd.DataFrame:
    """
    Rolling 30d (90 funding events) z-score of spread, lag 1.
    Returns DataFrame indexed by funding timestamps with column 'position'
    where +1 means long ETH/short BTC, -1 means long BTC/short ETH, 0 flat.
    """
    s = fr["spread"]
    win = 90  # 30 days * 3 fundings/day
    mu = s.rolling(win, min_periods=win).mean()
    sd = s.rolling(win, min_periods=win).std()
    z = (s - mu) / sd
    z_lag = z.shift(1)  # lag 1 — no look-ahead

    pos = pd.Series(0.0, index=fr.index)
    cur = 0.0
    for ts, zv in z_lag.items():
        if np.isnan(zv):
            pos.loc[ts] = 0.0
            cur = 0.0
            continue
        if cur == 0.0:
            if zv > z_enter:
                cur = 1.0
            elif (not one_sided) and zv < -z_enter:
                cur = -1.0
        else:
            if abs(zv) < z_exit:
                cur = 0.0
            elif cur > 0 and zv < -z_enter and (not one_sided):
                cur = -1.0
            elif cur < 0 and zv > z_enter:
                cur = 1.0
        pos.loc[ts] = cur

    out = fr.copy()
    out["z"] = z
    out["z_lag"] = z_lag
    out["position"] = pos
    return out


# ---------------------------------------------------------------------
# 3) Forward-fill onto 4H bars and compute PnL
# ---------------------------------------------------------------------
def backtest(signal_df: pd.DataFrame, px: pd.DataFrame) -> dict:
    """
    Project funding-bar positions onto 4H price bars (ffill) and compute the
    dollar-neutral pair PnL. PnL per bar = pos_prev * (eth_ret - btc_ret) / 2
    (divide by 2 because each leg is half the notional in a dollar-neutral pair).
    Costs charged on every position change (delta > 0).
    """
    pos_ff = signal_df["position"].reindex(px.index, method="ffill").fillna(0.0)

    eth_ret = px["eth_close"].pct_change().fillna(0.0)
    btc_ret = px["btc_close"].pct_change().fillna(0.0)
    pair_ret = (eth_ret - btc_ret) / 2.0  # dollar-neutral

    pos_prev = pos_ff.shift(1).fillna(0.0)
    gross = pos_prev * pair_ret

    # Costs: 0.07% per side per leg = 0.07% * 2 legs = 0.14% for any open/close.
    # When |delta pos| == 1, that's 0.14% per change. A full round trip is 0.28%.
    pos_change = (pos_ff - pos_prev).abs()
    leg_cost_per_change = COST_PER_SIDE * 2  # 2 legs simultaneous
    costs = pos_change * leg_cost_per_change

    net = gross - costs

    equity = (1.0 + net).cumprod()
    return {
        "equity": equity,
        "net_ret": net,
        "gross_ret": gross,
        "costs": costs,
        "pos": pos_ff,
        "trades_per_bar": pos_change,
    }


# ---------------------------------------------------------------------
# 4) Metrics
# ---------------------------------------------------------------------
ANN_FACTOR_4H = np.sqrt(6 * 365)  # 6 bars/day * 365


def metrics(net_ret: pd.Series, pos: pd.Series, trades_per_bar: pd.Series, equity: pd.Series) -> dict:
    if len(net_ret) == 0 or net_ret.std() == 0:
        return {
            "sharpe": 0.0, "sortino": 0.0, "calmar": 0.0, "maxdd": 0.0,
            "win_rate": 0.0, "n_trades": 0, "total_return": 0.0, "ann_return": 0.0,
            "ann_vol": 0.0, "exposure": 0.0,
        }
    mu = net_ret.mean()
    sd = net_ret.std()
    sharpe = (mu / sd) * ANN_FACTOR_4H if sd > 0 else 0.0
    downside = net_ret[net_ret < 0]
    dsd = downside.std() if len(downside) > 1 else 0.0
    sortino = (mu / dsd) * ANN_FACTOR_4H if dsd and dsd > 0 else 0.0

    eq = equity
    dd = (eq / eq.cummax() - 1.0)
    maxdd = dd.min()
    n_bars = len(net_ret)
    years = n_bars / (6 * 365)
    total_ret = eq.iloc[-1] - 1.0
    ann_ret = (eq.iloc[-1] ** (1 / years) - 1.0) if years > 0 and eq.iloc[-1] > 0 else 0.0
    calmar = ann_ret / abs(maxdd) if maxdd < 0 else 0.0

    # trades = each opening transition (pos goes nonzero from zero, or flips sign)
    # We count "trades" as the number of state changes (entries+exits).
    n_trades = int((trades_per_bar > 0).sum())

    # Win rate on bars where we hold a position
    held = net_ret[pos.shift(1).fillna(0).abs() > 0]
    win_rate = (held > 0).mean() if len(held) > 0 else 0.0
    exposure = (pos.abs() > 0).mean()

    return {
        "sharpe": float(sharpe),
        "sortino": float(sortino),
        "calmar": float(calmar),
        "maxdd": float(maxdd),
        "win_rate": float(win_rate),
        "n_trades": n_trades,
        "total_return": float(total_ret),
        "ann_return": float(ann_ret),
        "ann_vol": float(sd * ANN_FACTOR_4H),
        "exposure": float(exposure),
    }


# ---------------------------------------------------------------------
# 5) Split utilities
# ---------------------------------------------------------------------
def split_is_oos(df: pd.DataFrame, frac=0.7):
    n = len(df)
    cut = int(n * frac)
    return df.iloc[:cut], df.iloc[cut:]


def run_variant(fr, px, z_enter, z_exit, one_sided=False):
    sig = build_signal(fr, z_enter=z_enter, z_exit=z_exit, one_sided=one_sided)
    bt = backtest(sig, px)
    eq = bt["equity"]
    is_, oos = split_is_oos(eq)
    is_net = bt["net_ret"].loc[is_.index]
    oos_net = bt["net_ret"].loc[oos.index]
    is_pos = bt["pos"].loc[is_.index]
    oos_pos = bt["pos"].loc[oos.index]
    is_tr = bt["trades_per_bar"].loc[is_.index]
    oos_tr = bt["trades_per_bar"].loc[oos.index]
    return {
        "signal": sig,
        "bt": bt,
        "full": metrics(bt["net_ret"], bt["pos"], bt["trades_per_bar"], bt["equity"]),
        "is": metrics(is_net, is_pos, is_tr, (1 + is_net).cumprod()),
        "oos": metrics(oos_net, oos_pos, oos_tr, (1 + oos_net).cumprod()),
    }


# ---------------------------------------------------------------------
# 6) Walk-forward 4-fold
# ---------------------------------------------------------------------
def walk_forward(fr, px, z_enter, z_exit, one_sided=False, n_folds=4):
    sig = build_signal(fr, z_enter=z_enter, z_exit=z_exit, one_sided=one_sided)
    bt = backtest(sig, px)
    net = bt["net_ret"]; pos = bt["pos"]; tr = bt["trades_per_bar"]
    eq = bt["equity"]
    n = len(net)
    fold_size = n // n_folds
    sharpes = []
    for i in range(n_folds):
        a = i * fold_size
        b = n if i == n_folds - 1 else (i + 1) * fold_size
        seg = net.iloc[a:b]
        seg_pos = pos.iloc[a:b]
        seg_tr = tr.iloc[a:b]
        seg_eq = (1 + seg).cumprod()
        m = metrics(seg, seg_pos, seg_tr, seg_eq)
        sharpes.append(m["sharpe"])
    return sharpes


# ---------------------------------------------------------------------
# 7) Permutation test — shuffle ETH funding within rolling window
# ---------------------------------------------------------------------
def permutation_test(fr, px, z_enter, z_exit, one_sided, n_perm=500, window=90):
    real_oos_sharpe = run_variant(fr, px, z_enter, z_exit, one_sided)["oos"]["sharpe"]
    null_sharpes = []
    eth_vals = fr["fr_eth"].values.copy()
    for _ in range(n_perm):
        shuffled = eth_vals.copy()
        # shuffle ETH funding values within consecutive non-overlapping windows
        for start in range(0, len(shuffled), window):
            end = min(start + window, len(shuffled))
            block = shuffled[start:end].copy()
            RNG.shuffle(block)
            shuffled[start:end] = block
        fr_perm = fr.copy()
        fr_perm["fr_eth"] = shuffled
        fr_perm["spread"] = fr_perm["fr_eth"] - fr_perm["fr_btc"]
        try:
            res = run_variant(fr_perm, px, z_enter, z_exit, one_sided)
            null_sharpes.append(res["oos"]["sharpe"])
        except Exception:
            null_sharpes.append(0.0)
    null = np.array(null_sharpes)
    p = float(((null >= real_oos_sharpe).sum() + 1) / (len(null) + 1))
    return {
        "real_oos_sharpe": float(real_oos_sharpe),
        "null_mean": float(null.mean()),
        "null_std": float(null.std()),
        "null_p95": float(np.percentile(null, 95)),
        "p_value": p,
    }


# ---------------------------------------------------------------------
# 8) Block bootstrap CI on OOS Sharpe
# ---------------------------------------------------------------------
def block_bootstrap_ci(net_ret: pd.Series, n_boot=500, block=24):
    """Block bootstrap of 4H returns (block=24 bars = 4 days)."""
    arr = net_ret.values
    n = len(arr)
    if n < block:
        return {"ci_low": 0.0, "ci_high": 0.0, "median": 0.0}
    n_blocks = n // block
    sharpes = []
    for _ in range(n_boot):
        idx = RNG.integers(0, n_blocks, size=n_blocks)
        sample = np.concatenate([arr[i * block:(i + 1) * block] for i in idx])
        sd = sample.std()
        if sd == 0:
            sharpes.append(0.0)
        else:
            sharpes.append(sample.mean() / sd * ANN_FACTOR_4H)
    sharpes = np.array(sharpes)
    return {
        "ci_low": float(np.percentile(sharpes, 2.5)),
        "median": float(np.percentile(sharpes, 50)),
        "ci_high": float(np.percentile(sharpes, 97.5)),
    }


# ---------------------------------------------------------------------
# 9) DSR (Deflated Sharpe Ratio) with N_trials
# ---------------------------------------------------------------------
def deflated_sharpe(sharpe, n_trials, n_obs, skew=0.0, kurt=3.0):
    """Bailey & Lopez de Prado deflated Sharpe (approximate)."""
    from math import sqrt, log, erf
    if n_trials < 1 or n_obs < 2:
        return 0.0
    # Expected max SR under null
    emc = 0.5772156649  # Euler–Mascheroni
    e_max = sqrt(2 * log(n_trials)) - (emc / sqrt(2 * log(n_trials))) if n_trials > 1 else 0.0
    sr_std = sqrt((1 - skew * sharpe + (kurt - 1) / 4 * sharpe ** 2) / (n_obs - 1))
    z = (sharpe - e_max * sr_std) / max(sr_std, 1e-12)
    # Standard normal CDF
    cdf = 0.5 * (1 + erf(z / sqrt(2)))
    return float(cdf)


# ---------------------------------------------------------------------
# 10) Cost stress
# ---------------------------------------------------------------------
def cost_stress(fr, px, z_enter, z_exit, one_sided, multiplier):
    """Re-run with scaled costs."""
    global COST_PER_SIDE
    orig = COST_PER_SIDE
    COST_PER_SIDE = orig * multiplier
    try:
        res = run_variant(fr, px, z_enter, z_exit, one_sided)
        return {
            "is_sharpe": res["is"]["sharpe"],
            "oos_sharpe": res["oos"]["sharpe"],
            "full_total_return": res["full"]["total_return"],
        }
    finally:
        COST_PER_SIDE = orig


# ---------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------
def main():
    fr, px = load_data()
    print(f"[K126] Funding rows: {len(fr)}  Price rows: {len(px)}")
    print(f"[K126] Funding range: {fr.index.min()} → {fr.index.max()}")
    print(f"[K126] Price range:   {px.index.min()} → {px.index.max()}")

    # Spread stats
    spread = fr["spread"]
    spread_stats = {
        "n": int(len(spread)),
        "mean": float(spread.mean()),
        "std": float(spread.std()),
        "min": float(spread.min()),
        "max": float(spread.max()),
        "abs_mean_bps": float(spread.abs().mean() * 10000),
        "p1": float(spread.quantile(0.01)),
        "p5": float(spread.quantile(0.05)),
        "p50": float(spread.quantile(0.50)),
        "p95": float(spread.quantile(0.95)),
        "p99": float(spread.quantile(0.99)),
    }
    print(f"[K126] Spread: mean={spread_stats['mean']:.6f} std={spread_stats['std']:.6f} p99={spread_stats['p99']:.6f}")

    # When did z spikes occur historically?
    win = 90
    z_full = (spread - spread.rolling(win).mean()) / spread.rolling(win).std()
    z_extreme_pos = z_full[z_full > 1.5]
    z_extreme_neg = z_full[z_full < -1.5]
    spike_summary = {
        "n_z_gt_1p5": int(len(z_extreme_pos)),
        "n_z_lt_neg1p5": int(len(z_extreme_neg)),
        "n_z_gt_2p0": int((z_full > 2.0).sum()),
        "n_z_lt_neg2p0": int((z_full < -2.0).sum()),
        "n_total_with_zscore": int(z_full.notna().sum()),
        "first_z_gt_1p5_ts": str(z_extreme_pos.index[0]) if len(z_extreme_pos) else None,
        "last_z_gt_1p5_ts": str(z_extreme_pos.index[-1]) if len(z_extreme_pos) else None,
    }

    variants = {
        "V_z15":         dict(z_enter=1.5, z_exit=0.3, one_sided=False),
        "V_z20":         dict(z_enter=2.0, z_exit=0.3, one_sided=False),
        "V_z10":         dict(z_enter=1.0, z_exit=0.3, one_sided=False),
        "V_long_eth_only": dict(z_enter=1.5, z_exit=0.3, one_sided=True),
    }

    results = {}
    curves = {}
    for name, kw in variants.items():
        print(f"[K126] Running variant {name} ({kw})")
        r = run_variant(fr, px, **kw)
        sharpes_wf = walk_forward(fr, px, **kw, n_folds=4)
        boot = block_bootstrap_ci(r["bt"]["net_ret"].loc[r["bt"]["net_ret"].index[int(len(r["bt"]["net_ret"]) * 0.7):]],
                                  n_boot=500, block=24)
        results[name] = {
            "params": kw,
            "full": r["full"],
            "is": r["is"],
            "oos": r["oos"],
            "walk_forward_sharpes": sharpes_wf,
            "wf_mean": float(np.mean(sharpes_wf)),
            "wf_std": float(np.std(sharpes_wf)),
            "oos_bootstrap_ci": boot,
        }
        # Curves (downsample 4H equity for json size)
        eq = r["bt"]["equity"]
        idx = eq.index[::6]  # daily
        curves[name] = {
            "timestamps": [str(t) for t in idx],
            "equity": [float(v) for v in eq.loc[idx].values],
        }

    # DSR with N_trials=4 (number of variants tried)
    best_name = max(results.keys(), key=lambda k: results[k]["oos"]["sharpe"])
    best = results[best_name]
    n_obs_oos = int(len(fr) * 0.3) * 1  # in funding-bar units; we use approx
    # Use 4H bar count for n_obs
    n_obs_4h = int(len(px) * 0.3)
    dsr_prob = deflated_sharpe(best["oos"]["sharpe"], n_trials=4, n_obs=n_obs_4h)
    results["dsr_best"] = {
        "best_variant": best_name,
        "best_oos_sharpe": best["oos"]["sharpe"],
        "n_trials": 4,
        "n_obs": n_obs_4h,
        "dsr_probability": dsr_prob,
    }

    # Permutation on best
    print(f"[K126] Permutation test on {best_name} (n=500)…")
    perm = permutation_test(fr, px, **variants[best_name], n_perm=500)
    results["permutation_best"] = perm

    # Cost stress on best
    stress = {}
    for mult in [0.5, 1.0, 1.5]:
        stress[f"x{mult:.1f}"] = cost_stress(fr, px, **variants[best_name], multiplier=mult)
    results["cost_stress_best"] = stress

    # Spread summary
    results["spread_stats"] = spread_stats
    results["spike_summary"] = spike_summary
    results["meta"] = {
        "n_funding_rows": int(len(fr)),
        "n_4h_rows": int(len(px)),
        "funding_start": str(fr.index.min()),
        "funding_end": str(fr.index.max()),
        "px_start": str(px.index.min()),
        "px_end": str(px.index.max()),
        "cost_per_side": COST_PER_SIDE,
        "cost_per_trade_pair_round_trip": COST_PER_TRADE_PAIR,
        "best_variant": best_name,
    }

    OUT_PY_JSON.write_text(json.dumps(results, indent=2, default=str))
    OUT_CURVES.write_text(json.dumps(curves, indent=2))
    print(f"[K126] Wrote {OUT_PY_JSON}")
    print(f"[K126] Wrote {OUT_CURVES}")

    # ---------------- Print markdown report inline -----------------
    print("\n\n" + "=" * 70)
    print("WAVE K126 — ETH-BTC FUNDING SPREAD PAIR — MARKDOWN REPORT")
    print("=" * 70)
    print(report_md(results, spread_stats, spike_summary, variants, best_name))


def report_md(results, spread_stats, spike_summary, variants, best_name):
    lines = []
    lines.append("# Wave K126 — ETH-BTC Funding Spread Pair (R4-15)")
    lines.append("")
    lines.append("## 1. Hypothesis")
    lines.append("CoinMetrics 2026: when ETH funding > BTC funding by extreme dispersion, ETH leads BTC in next 1-2 weeks. "
                 "Trade: rolling 30d z-score of (ETH-BTC) funding spread, dollar-neutral pair (lag 1, no look-ahead).")
    lines.append("")
    lines.append("## 2. Data & Spread Time-Series Statistics")
    lines.append(f"- Funding rows: {results['meta']['n_funding_rows']} (8h cadence), 4H price rows: {results['meta']['n_4h_rows']}")
    lines.append(f"- Funding window: {results['meta']['funding_start']} → {results['meta']['funding_end']}")
    lines.append("")
    lines.append("| metric | value |")
    lines.append("|---|---|")
    lines.append(f"| mean spread | {spread_stats['mean']*1e4:.3f} bps |")
    lines.append(f"| std spread | {spread_stats['std']*1e4:.3f} bps |")
    lines.append(f"| abs mean | {spread_stats['abs_mean_bps']:.3f} bps |")
    lines.append(f"| 1st percentile | {spread_stats['p1']*1e4:.3f} bps |")
    lines.append(f"| 5th | {spread_stats['p5']*1e4:.3f} bps |")
    lines.append(f"| 50th | {spread_stats['p50']*1e4:.3f} bps |")
    lines.append(f"| 95th | {spread_stats['p95']*1e4:.3f} bps |")
    lines.append(f"| 99th | {spread_stats['p99']*1e4:.3f} bps |")
    lines.append(f"| min/max | {spread_stats['min']*1e4:.3f} / {spread_stats['max']*1e4:.3f} bps |")
    lines.append("")
    lines.append("### Z-score spike frequency (90-event rolling window)")
    lines.append(f"- |z|>1.5: pos={spike_summary['n_z_gt_1p5']}, neg={spike_summary['n_z_lt_neg1p5']} "
                 f"(out of {spike_summary['n_total_with_zscore']} valid obs)")
    lines.append(f"- |z|>2.0: pos={spike_summary['n_z_gt_2p0']}, neg={spike_summary['n_z_lt_neg2p0']}")
    if spike_summary["first_z_gt_1p5_ts"]:
        lines.append(f"- First z>1.5 spike: {spike_summary['first_z_gt_1p5_ts']}, last: {spike_summary['last_z_gt_1p5_ts']}")
    lines.append("")
    lines.append("## 3. Per-Variant Sharpe (IS 70% / OOS 30%)")
    lines.append("")
    lines.append("| variant | params | n_trades | exposure | IS Sharpe | OOS Sharpe | OOS MaxDD | OOS Calmar | OOS WinRate |")
    lines.append("|---|---|---|---|---|---|---|---|---|")
    for vn in [k for k in results if k.startswith("V_")]:
        r = results[vn]
        p = r["params"]
        ps = f"z±{p['z_enter']}/exit{p['z_exit']}{'/one-sided' if p['one_sided'] else ''}"
        lines.append(f"| {vn} | {ps} | {r['full']['n_trades']} | {r['full']['exposure']:.2%} | "
                     f"{r['is']['sharpe']:.3f} | {r['oos']['sharpe']:.3f} | "
                     f"{r['oos']['maxdd']:.2%} | {r['oos']['calmar']:.3f} | {r['oos']['win_rate']:.2%} |")
    lines.append("")
    lines.append("## 4. Walk-Forward 4-Fold (per variant)")
    lines.append("")
    lines.append("| variant | fold1 | fold2 | fold3 | fold4 | mean | std |")
    lines.append("|---|---|---|---|---|---|---|")
    for vn in [k for k in results if k.startswith("V_")]:
        r = results[vn]
        f = r["walk_forward_sharpes"]
        lines.append(f"| {vn} | {f[0]:.2f} | {f[1]:.2f} | {f[2]:.2f} | {f[3]:.2f} | {r['wf_mean']:.2f} | {r['wf_std']:.2f} |")
    lines.append("")
    lines.append("## 5. Robustness (on best variant)")
    best = results[best_name]
    perm = results["permutation_best"]
    stress = results["cost_stress_best"]
    dsr = results["dsr_best"]
    lines.append(f"**Best variant**: `{best_name}`  OOS Sharpe = {best['oos']['sharpe']:.3f}")
    lines.append("")
    lines.append("### Permutation test (n=500, shuffle ETH funding within rolling 90-bin windows)")
    lines.append(f"- real OOS Sharpe: {perm['real_oos_sharpe']:.3f}")
    lines.append(f"- null mean: {perm['null_mean']:.3f}  null std: {perm['null_std']:.3f}  null p95: {perm['null_p95']:.3f}")
    lines.append(f"- **p-value: {perm['p_value']:.4f}**")
    lines.append("")
    lines.append("### Block bootstrap CI on OOS Sharpe (n=500, block=24 bars = 4d)")
    boot = best["oos_bootstrap_ci"]
    lines.append(f"- 95% CI: [{boot['ci_low']:.3f}, {boot['ci_high']:.3f}], median: {boot['median']:.3f}")
    lines.append("")
    lines.append("### DSR (N_trials=4)")
    lines.append(f"- DSR probability (P[true SR > 0]): {dsr['dsr_probability']:.4f}")
    lines.append("")
    lines.append("### Cost stress (±50% on per-side cost)")
    lines.append("| cost mult | IS Sharpe | OOS Sharpe | full total return |")
    lines.append("|---|---|---|---|")
    for k, v in stress.items():
        lines.append(f"| {k} | {v['is_sharpe']:.3f} | {v['oos_sharpe']:.3f} | {v['full_total_return']:.2%} |")
    lines.append("")
    lines.append("## 6. §6 Mini Gates")
    best_oos = best["oos"]
    boot = best["oos_bootstrap_ci"]
    perm_p = perm["p_value"]
    wf_pos = sum(1 for s in best["walk_forward_sharpes"] if s > 0)
    cost_ok = stress["x1.5"]["oos_sharpe"] > 0
    gates = [
        ("OOS Sharpe > 1.0", best_oos["sharpe"] > 1.0, f"{best_oos['sharpe']:.3f}"),
        ("OOS MaxDD > -25%", best_oos["maxdd"] > -0.25, f"{best_oos['maxdd']:.2%}"),
        ("Permutation p < 0.05", perm_p < 0.05, f"{perm_p:.4f}"),
        ("Bootstrap CI low > 0", boot["ci_low"] > 0, f"{boot['ci_low']:.3f}"),
        ("Walk-forward >=3/4 folds Sharpe>0", wf_pos >= 3, f"{wf_pos}/4"),
        ("Cost +50% OOS Sharpe > 0", cost_ok, f"{stress['x1.5']['oos_sharpe']:.3f}"),
        ("n_trades >= 20", best["full"]["n_trades"] >= 20, f"{best['full']['n_trades']}"),
    ]
    lines.append("| Gate | Pass | Value |")
    lines.append("|---|---|---|")
    n_pass = 0
    for name, ok, val in gates:
        mark = "PASS" if ok else "FAIL"
        if ok:
            n_pass += 1
        lines.append(f"| {name} | {mark} | {val} |")
    lines.append("")
    lines.append(f"**Gate score: {n_pass}/{len(gates)}**")
    lines.append("")
    lines.append("## 7. Cost Reality Check")
    # mean |spread| per funding event in bps; theoretical funding-arb edge per cycle
    abs_mean_bps = spread_stats["abs_mean_bps"]
    p99_abs_bps = max(abs(spread_stats["p99"]), abs(spread_stats["p1"])) * 1e4
    lines.append(f"- Mean |ETH-BTC funding spread| per 8h event: **{abs_mean_bps:.3f} bps**")
    lines.append(f"- 99th-percentile abs spread per event: **{p99_abs_bps:.3f} bps**")
    lines.append(f"- Round-trip cost (open+close, 2 legs each): **{COST_PER_TRADE_PAIR*1e4:.1f} bps**")
    lines.append("")
    lines.append("Interpretation: Funding spread itself is only a *signal*, not the harvested edge — we are betting on "
                 "subsequent ETH/BTC **price** divergence. To clear 28 bps round-trip per trade, the average price-pair "
                 "move during a holding period must exceed 28 bps net. With holding periods typically several days "
                 "(funding signal mean-reverts slowly), 28 bps is feasible if the directional edge is real; if not, "
                 "cost will dominate. See OOS Sharpe & cost-stress rows above for the empirical verdict.")
    lines.append("")
    lines.append("## 8. Verdict")
    if n_pass >= 6:
        verdict = "PASS (deploy candidate)"
    elif n_pass >= 4:
        verdict = "WEAK (re-test, do not deploy yet)"
    else:
        verdict = "FAIL"
    lines.append(f"**{verdict}** — gates {n_pass}/{len(gates)}. Best variant `{best_name}`.")
    return "\n".join(lines)


if __name__ == "__main__":
    main()
