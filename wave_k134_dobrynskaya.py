"""
Wave K134 — Dobrynskaya Crypto Momentum & Reversal Switch (R5-11)

Hypothesis (Dobrynskaya SSRN 3913263):
- Positive cross-sectional momentum at 2-4 week horizons.
- Long-term reversal beyond 1 month.
- Switching strategy: long top winners by short lookback (~21d) AND long losers
  by long lookback (~60d) → cross-sectional combo.

Method (pre-registered, single composite design):
1. At each weekly rebalance (every 42 4H bars = 7 days):
   - mom_21d  = 21-day lookback return per symbol (cross-sectional momentum)
   - rev_60d  = 60-day lookback return per symbol (cross-sectional reversal)
   - both lookbacks LAGGED by 1 bar to avoid look-ahead at decision time.
2. Rank symbols cross-sectionally on each signal.
3. Sleeves:
   - Momentum sleeve: long top-3 by mom_21d, short bottom-3 (dollar-neutral)
   - Reversal sleeve: long bottom-3 by rev_60d, short top-3 (dollar-neutral)
4. Combine sleeves per variant weights (V_60_40 default).
5. Hold positions until next rebalance (7d = 42 bars).
6. Costs: 0.07% per side per leg.

Variants:
- V_60_40: mom 60% / rev 40% (paper-style switching emphasis on mom)
- V_50_50: equal blend
- V_70_30: mom heavy
- V_30_70: reversal heavy
- V_mom_only: 100% mom (baseline isolating mom sleeve)
- V_rev_only: 100% reversal (baseline isolating rev sleeve)

Audit:
- 730d, IS 70% / OOS 30%
- Per-variant Portfolio Sharpe
- WF 4-fold on default variant
- Permutation n=300 (shuffle ranks within cross-section per rebalance)
- Block bootstrap n=300 on portfolio
- DSR with N_trials = 6
- Cost stress ±50% on default variant
"""

from __future__ import annotations

import json
import math
import os
import time
import warnings
from math import erf

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

CACHE = "/Users/nekonaomichi/crypto-lab/cache"
OUT_JSON = "/Users/nekonaomichi/crypto-lab/wave_k134_dobrynskaya.json"
OUT_CURVES = "/Users/nekonaomichi/crypto-lab/wave_k134_curves.json"

# ---------- universe (top ~35 by median dollar volume, all with 4380+ bars) ----------
SYMBOLS = [
    "BTC", "ETH", "SOL", "XRP", "DOGE", "SUI", "PEPE", "BNB", "ADA", "TRX",
    "LINK", "LTC", "AVAX", "ENA", "TAO", "WIF", "NEAR", "ARB", "APT", "WLD",
    "SHIB", "ONDO", "DOT", "POPCAT", "AAVE", "UNI", "SEI", "BONK", "FIL", "OP",
    "ETC", "FET", "ICP", "INJ", "TIA",
]

# ---------- design constants ----------
BARS_PER_DAY = 6                  # 4H bars
PERIODS_PER_YEAR = BARS_PER_DAY * 365  # 2190
LOOKBACK_MOM_BARS = 21 * BARS_PER_DAY  # 21d × 6 = 126
LOOKBACK_REV_BARS = 60 * BARS_PER_DAY  # 60d × 6 = 360
REBAL_BARS = 7 * BARS_PER_DAY     # 7d × 6 = 42
TOP_N = 3                         # long-3 / short-3 per sleeve

IS_FRAC = 0.70

TAKER_BPS = 4.0
SLIP_BPS = 3.0
COST_PER_SIDE = (TAKER_BPS + SLIP_BPS) / 1e4   # 0.07%

VARIANTS = {
    "V_60_40":   {"w_mom": 0.60, "w_rev": 0.40},
    "V_50_50":   {"w_mom": 0.50, "w_rev": 0.50},
    "V_70_30":   {"w_mom": 0.70, "w_rev": 0.30},
    "V_30_70":   {"w_mom": 0.30, "w_rev": 0.70},
    "V_mom_only":{"w_mom": 1.00, "w_rev": 0.00},
    "V_rev_only":{"w_mom": 0.00, "w_rev": 1.00},
}


# ---------- data ----------
def load_close_panel() -> pd.DataFrame:
    """Return wide panel of 4H close prices: index=ts, columns=symbol."""
    frames = []
    for sym in SYMBOLS:
        p = f"{CACHE}/{sym}USDT_4h_730d.parquet"
        df = pd.read_parquet(p)[["open_time", "close"]].rename(
            columns={"open_time": "ts"}
        )
        df = df.sort_values("ts").drop_duplicates("ts").set_index("ts")
        df = df.rename(columns={"close": sym})
        frames.append(df.astype(float))
    panel = pd.concat(frames, axis=1).sort_index()
    return panel


def lookback_return(panel: pd.DataFrame, lb_bars: int) -> pd.DataFrame:
    """Return (P_t / P_{t-lb} - 1), then SHIFT 1 bar so signal is known at t."""
    lret = panel / panel.shift(lb_bars) - 1.0
    return lret.shift(1)


# ---------- signal / positions ----------
def cross_sectional_ranks_to_positions(
    sig_df: pd.DataFrame,
    long_top: bool,
    top_n: int,
) -> pd.DataFrame:
    """At each row, rank symbols cross-sectionally; long top_n / short bottom_n,
    or flipped if long_top=False (i.e. long losers, short winners — reversal).
    Returns dollar-neutral weights (sum = 0, gross = 2.0).
    """
    out = pd.DataFrame(0.0, index=sig_df.index, columns=sig_df.columns)
    arr = sig_df.values
    n_rows, n_cols = arr.shape
    w_each = 1.0 / top_n  # per-leg weight
    for i in range(n_rows):
        row = arr[i, :]
        valid = ~np.isnan(row)
        if valid.sum() < 2 * top_n:
            continue
        idx_valid = np.where(valid)[0]
        order = idx_valid[np.argsort(row[idx_valid])]  # ascending
        if long_top:
            longs = order[-top_n:]
            shorts = order[:top_n]
        else:
            # reversal sleeve: long losers (low rev_60d), short winners (high rev_60d)
            longs = order[:top_n]
            shorts = order[-top_n:]
        out.iloc[i, longs] = w_each
        out.iloc[i, shorts] = -w_each
    return out


def rebalance_only(weights_full: pd.DataFrame, rebal_bars: int) -> pd.DataFrame:
    """Hold weights from rebalance bar until next rebalance bar (ffill in between)."""
    n = len(weights_full)
    mask = np.zeros(n, dtype=bool)
    mask[::rebal_bars] = True
    held = weights_full.where(
        pd.Series(mask, index=weights_full.index), other=np.nan
    )
    held = held.ffill().fillna(0.0)
    return held


def build_sleeve_weights(
    panel: pd.DataFrame, lb_bars: int, long_top: bool
) -> pd.DataFrame:
    """Full pipeline for one sleeve: lookback → cross-sectional rank → rebalanced
    weights (held REBAL_BARS).
    """
    sig = lookback_return(panel, lb_bars)
    raw_w = cross_sectional_ranks_to_positions(sig, long_top, TOP_N)
    held = rebalance_only(raw_w, REBAL_BARS)
    return held


# ---------- pnl ----------
def sleeve_pnl(weights: pd.DataFrame, panel: pd.DataFrame, cost_mult: float = 1.0) -> pd.DataFrame:
    """Compute per-bar net return for a sleeve.

    weights at bar t apply to bar-t→t+1 return (we shift weights by 1 bar
    so position taken at t earns at t+1).
    Cost = sum over symbols of |Δweight| × per-side cost.
    """
    ret = panel.pct_change()
    w_lagged = weights.shift(1).fillna(0.0)
    pnl_gross = (w_lagged * ret).sum(axis=1)
    turn = (weights - weights.shift(1).fillna(0.0)).abs().sum(axis=1)
    cost = turn * COST_PER_SIDE * cost_mult
    out = pd.DataFrame({
        "pnl_gross": pnl_gross,
        "cost": cost,
        "pnl_net": pnl_gross - cost,
    })
    return out


def combine_sleeves(
    mom_pnl: pd.DataFrame, rev_pnl: pd.DataFrame, w_mom: float, w_rev: float
) -> pd.Series:
    return w_mom * mom_pnl["pnl_net"] + w_rev * rev_pnl["pnl_net"]


# ---------- metrics ----------
def sharpe(returns: np.ndarray, ppy: float = PERIODS_PER_YEAR) -> float:
    r = np.asarray(returns)
    r = r[~np.isnan(r)]
    if len(r) < 10 or r.std() == 0:
        return 0.0
    return float(r.mean() / r.std() * math.sqrt(ppy))


def max_dd(returns: np.ndarray) -> float:
    r = np.asarray(returns)
    r = r[~np.isnan(r)]
    if len(r) == 0:
        return 0.0
    eq = (1 + r).cumprod()
    peak = np.maximum.accumulate(eq)
    return float(((eq - peak) / peak).min())


def win_rate(returns: np.ndarray) -> float:
    r = np.asarray(returns)
    r = r[~np.isnan(r) & (r != 0)]
    if len(r) == 0:
        return 0.0
    return float((r > 0).mean())


def block_bootstrap_sharpe(ret: np.ndarray, block: int = 20, n: int = 300, seed: int = 7) -> tuple[float, float]:
    rng = np.random.default_rng(seed)
    r = np.asarray(ret)
    r = r[~np.isnan(r)]
    if len(r) < block * 2:
        return (0.0, 0.0)
    n_blocks = max(1, len(r) // block)
    samples = []
    for _ in range(n):
        starts = rng.integers(0, len(r) - block, size=n_blocks)
        sample = np.concatenate([r[s:s + block] for s in starts])
        samples.append(sharpe(sample))
    samples = np.array(samples)
    return (float(np.percentile(samples, 2.5)), float(np.percentile(samples, 97.5)))


def dsr(sharpe_val: float, n_obs: int, n_trials: int) -> float:
    if n_obs < 30 or n_trials < 1:
        return float("nan")
    emc = 0.5772
    sn = math.sqrt(2 * math.log(max(n_trials, 2)))
    expected_max = sn - emc / sn
    sr_std = math.sqrt((1 + 0.5 * sharpe_val ** 2) / n_obs)
    if sr_std == 0:
        return float("nan")
    z = (sharpe_val - expected_max * sr_std) / sr_std
    return float(0.5 * (1 + erf(z / math.sqrt(2))))


def equity_curve(returns: pd.Series, every: int = 6) -> list[dict]:
    eq = (1 + returns.fillna(0)).cumprod()
    return [
        {"ts": str(ts), "eq": float(v)}
        for ts, v in eq.iloc[::every].items()
    ]


# ---------- walk-forward ----------
def walk_forward_4fold(port_returns: pd.Series) -> list[dict]:
    n = len(port_returns)
    fold_size = n // 4
    wf = []
    for k in range(4):
        lo, hi = k * fold_size, (k + 1) * fold_size if k < 3 else n
        sub = port_returns.values[lo:hi]
        wf.append({
            "fold": k,
            "sharpe": sharpe(sub),
            "max_dd": max_dd(sub),
            "total_return": float((1 + pd.Series(sub).fillna(0)).prod() - 1),
            "n_bars": int(len(sub)),
        })
    return wf


# ---------- permutation test ----------
def permutation_test_xs(
    panel: pd.DataFrame,
    w_mom: float,
    w_rev: float,
    n: int = 300,
    seed: int = 42,
) -> dict:
    """Shuffle cross-sectional ranks at each rebalance bar (destroys directional
    edge while keeping rebalance schedule, leg sizes and turnover identical).
    """
    rng = np.random.default_rng(seed)

    # Base
    w_mom_df = build_sleeve_weights(panel, LOOKBACK_MOM_BARS, long_top=True)
    w_rev_df = build_sleeve_weights(panel, LOOKBACK_REV_BARS, long_top=False)
    pnl_mom = sleeve_pnl(w_mom_df, panel)
    pnl_rev = sleeve_pnl(w_rev_df, panel)
    base_port = combine_sleeves(pnl_mom, pnl_rev, w_mom, w_rev)
    base_sr = sharpe(base_port.values)

    # Lookback returns for shuffling
    sig_mom = lookback_return(panel, LOOKBACK_MOM_BARS)
    sig_rev = lookback_return(panel, LOOKBACK_REV_BARS)
    sym_cols = panel.columns
    n_cols = len(sym_cols)
    null_srs = []

    n_rows = len(panel)
    rebal_idx = np.arange(0, n_rows, REBAL_BARS)

    for _ in range(n):
        sig_mom_perm = sig_mom.copy()
        sig_rev_perm = sig_rev.copy()
        # At each rebalance index, shuffle valid symbols' signal values across columns
        for r in rebal_idx:
            row_m = sig_mom.iloc[r].values.copy()
            row_r = sig_rev.iloc[r].values.copy()
            vm = ~np.isnan(row_m)
            vr = ~np.isnan(row_r)
            if vm.sum() >= 2 * TOP_N:
                perm = rng.permutation(row_m[vm])
                row_m[vm] = perm
                sig_mom_perm.iloc[r] = row_m
            if vr.sum() >= 2 * TOP_N:
                perm = rng.permutation(row_r[vr])
                row_r[vr] = perm
                sig_rev_perm.iloc[r] = row_r

        # Only need values at rebalance bars; we already keep all others same (they'll be ffilled out)
        # but rebalance_only resets weights only at rebalance bars from full sig — okay since same rows
        wm = cross_sectional_ranks_to_positions(sig_mom_perm, True, TOP_N)
        wr = cross_sectional_ranks_to_positions(sig_rev_perm, False, TOP_N)
        wm = rebalance_only(wm, REBAL_BARS)
        wr = rebalance_only(wr, REBAL_BARS)
        pm = sleeve_pnl(wm, panel)
        pr = sleeve_pnl(wr, panel)
        port_perm = combine_sleeves(pm, pr, w_mom, w_rev)
        null_srs.append(sharpe(port_perm.values))

    null_srs = np.array(null_srs)
    p = float((null_srs >= base_sr).mean())
    return {
        "base_sharpe": float(base_sr),
        "null_mean": float(null_srs.mean()),
        "null_std": float(null_srs.std()),
        "null_p95": float(np.percentile(null_srs, 95)),
        "p_value": p,
        "n": int(n),
    }


# ---------- per-variant metrics ----------
def slice_metrics(port: pd.Series, lo: int, hi: int) -> dict:
    sub = port.iloc[lo:hi].values
    return {
        "sharpe": sharpe(sub),
        "max_dd": max_dd(sub),
        "win_rate": win_rate(sub),
        "n_bars": int(len(sub)),
        "total_return": float((1 + pd.Series(sub).fillna(0)).prod() - 1),
        "ann_return": float(pd.Series(sub).fillna(0).mean() * PERIODS_PER_YEAR),
        "ann_vol": float(pd.Series(sub).fillna(0).std() * math.sqrt(PERIODS_PER_YEAR)),
    }


# ---------- main ----------
def main():
    t0 = time.time()
    print("=" * 78)
    print("Wave K134 — Dobrynskaya Crypto Momentum & Reversal Switch (R5-11)")
    print("=" * 78)

    print(f"Loading {len(SYMBOLS)} symbols...")
    panel = load_close_panel()
    panel = panel.dropna(how="all")
    print(f"  panel shape: {panel.shape}  range: {panel.index.min()} → {panel.index.max()}")
    n_full = len(panel)
    cut = int(n_full * IS_FRAC)

    # Build the two underlying sleeves once
    print("Building sleeves...")
    w_mom_df = build_sleeve_weights(panel, LOOKBACK_MOM_BARS, long_top=True)
    w_rev_df = build_sleeve_weights(panel, LOOKBACK_REV_BARS, long_top=False)
    pnl_mom = sleeve_pnl(w_mom_df, panel)
    pnl_rev = sleeve_pnl(w_rev_df, panel)

    # Per-variant
    portfolio_metrics = {}
    curves = {}
    for vname, vp in VARIANTS.items():
        port = combine_sleeves(pnl_mom, pnl_rev, vp["w_mom"], vp["w_rev"])
        ci = block_bootstrap_sharpe(port.values[cut:], block=20, n=300)
        portfolio_metrics[vname] = {
            "weights": vp,
            "IS": slice_metrics(port, 0, cut),
            "OOS": slice_metrics(port, cut, n_full),
            "FULL": slice_metrics(port, 0, n_full),
            "OOS_sharpe_CI95": ci,
        }
        curves[vname] = equity_curve(port, every=6)

    # Sleeve-only diagnostics
    sleeve_metrics = {
        "mom_solo_OOS": slice_metrics(pnl_mom["pnl_net"], cut, n_full),
        "rev_solo_OOS": slice_metrics(pnl_rev["pnl_net"], cut, n_full),
        "mom_solo_IS":  slice_metrics(pnl_mom["pnl_net"], 0, cut),
        "rev_solo_IS":  slice_metrics(pnl_rev["pnl_net"], 0, cut),
        "mom_solo_FULL": slice_metrics(pnl_mom["pnl_net"], 0, n_full),
        "rev_solo_FULL": slice_metrics(pnl_rev["pnl_net"], 0, n_full),
        "sleeve_correlation_FULL": float(
            pnl_mom["pnl_net"].fillna(0).corr(pnl_rev["pnl_net"].fillna(0))
        ),
    }

    # Walk-forward on default V_60_40
    print("Walk-forward 4-fold (V_60_40)...")
    default_port = combine_sleeves(pnl_mom, pnl_rev, 0.60, 0.40)
    wf = walk_forward_4fold(default_port)

    # Permutation test on V_60_40
    print("Permutation test (V_60_40, n=300)...")
    perm = permutation_test_xs(panel, 0.60, 0.40, n=300, seed=42)
    print(f"  base SR={perm['base_sharpe']:.3f}  null_mean={perm['null_mean']:.3f}  "
          f"null_p95={perm['null_p95']:.3f}  p={perm['p_value']:.3f}")

    # Cost stress ±50% on V_60_40
    print("Cost stress ±50% (V_60_40)...")
    cost_stress = {}
    for mult, name in [(0.5, "low"), (1.0, "base"), (1.5, "high")]:
        pnl_mom_s = sleeve_pnl(w_mom_df, panel, cost_mult=mult)
        pnl_rev_s = sleeve_pnl(w_rev_df, panel, cost_mult=mult)
        port_s = combine_sleeves(pnl_mom_s, pnl_rev_s, 0.60, 0.40)
        cost_stress[name] = {
            "OOS_sharpe": sharpe(port_s.values[cut:]),
            "OOS_max_dd": max_dd(port_s.values[cut:]),
            "OOS_total_return": float((1 + pd.Series(port_s.values[cut:]).fillna(0)).prod() - 1),
        }

    # DSR with 6 trials (6 variants)
    n_oos = n_full - cut
    dsr_map = {
        v: dsr(m["OOS"]["sharpe"], n_oos, n_trials=len(VARIANTS))
        for v, m in portfolio_metrics.items()
    }

    # §6 mini gates — primary V_60_40
    pri = portfolio_metrics["V_60_40"]
    gates = {
        "G1_OOS_Sharpe_gt_0.5":         pri["OOS"]["sharpe"] > 0.5,
        "G2_OOS_MaxDD_gt_-0.30":        pri["OOS"]["max_dd"] > -0.30,
        "G3_BlockBoot_CI95_low_gt_0":   pri["OOS_sharpe_CI95"][0] > 0,
        "G4_Perm_p_lt_0.05":            perm["p_value"] < 0.05,
        "G5_DSR_gt_0.95":               (dsr_map["V_60_40"] if not math.isnan(dsr_map["V_60_40"]) else 0) > 0.95,
        "G6_CostStress_high_OOS_sr_gt_0.3": cost_stress["high"]["OOS_sharpe"] > 0.3,
    }
    n_pass = sum(gates.values())
    verdict = (
        "ACCEPT" if n_pass >= 5
        else "CONDITIONAL" if n_pass >= 3
        else "REJECT"
    )

    # Persist
    with open(OUT_CURVES, "w") as f:
        json.dump(curves, f, indent=2)

    result = {
        "wave": "K134",
        "title": "Dobrynskaya Crypto Momentum & Reversal Switch (R5-11)",
        "as_of": pd.Timestamp.utcnow().isoformat(),
        "symbols": SYMBOLS,
        "n_symbols": len(SYMBOLS),
        "panel_shape": list(panel.shape),
        "panel_range": [str(panel.index.min()), str(panel.index.max())],
        "design": {
            "bars_per_day": BARS_PER_DAY,
            "lookback_mom_bars": LOOKBACK_MOM_BARS,
            "lookback_rev_bars": LOOKBACK_REV_BARS,
            "rebal_bars": REBAL_BARS,
            "top_n_per_leg": TOP_N,
            "is_frac": IS_FRAC,
            "costs": {"taker_bps": TAKER_BPS, "slip_bps": SLIP_BPS, "per_side_pct": COST_PER_SIDE * 100},
        },
        "variants": VARIANTS,
        "portfolio": portfolio_metrics,
        "sleeves_solo": sleeve_metrics,
        "walk_forward_V_60_40": wf,
        "permutation_test_V_60_40": perm,
        "cost_stress_V_60_40": cost_stress,
        "DSR": dsr_map,
        "gates": gates,
        "n_gates_pass": n_pass,
        "verdict": verdict,
        "elapsed_sec": time.time() - t0,
    }
    with open(OUT_JSON, "w") as f:
        json.dump(result, f, indent=2, default=str)

    # Print summary
    print()
    print("=" * 78)
    print("PORTFOLIO (V_60_40 default)")
    pri_oos = pri["OOS"]
    print(f"  IS  Sharpe: {pri['IS']['sharpe']:.3f}")
    print(f"  OOS Sharpe: {pri_oos['sharpe']:.3f}  CI95=[{pri['OOS_sharpe_CI95'][0]:.2f},{pri['OOS_sharpe_CI95'][1]:.2f}]")
    print(f"  OOS MaxDD : {pri_oos['max_dd']:.2%}")
    print(f"  OOS TotRet: {pri_oos['total_return']:+.2%}")
    print(f"  OOS Vol   : {pri_oos['ann_vol']:.2%}")

    print()
    print("VARIANT COMPARISON:")
    print(f"  {'variant':12s} {'IS_SR':>7s} {'OOS_SR':>7s} {'OOS_DD':>8s} {'FULL_ret':>9s} {'DSR':>6s}")
    for v, m in portfolio_metrics.items():
        print(f"  {v:12s} {m['IS']['sharpe']:7.2f} {m['OOS']['sharpe']:7.2f} "
              f"{m['OOS']['max_dd']:8.2%} {m['FULL']['total_return']:+9.2%} {dsr_map[v]:6.2f}")

    print()
    print("SLEEVES SOLO (informational — which is the real edge?):")
    sm = sleeve_metrics
    print(f"  mom_only OOS: SR={sm['mom_solo_OOS']['sharpe']:6.2f}  DD={sm['mom_solo_OOS']['max_dd']:.2%}  ret={sm['mom_solo_OOS']['total_return']:+.2%}")
    print(f"  rev_only OOS: SR={sm['rev_solo_OOS']['sharpe']:6.2f}  DD={sm['rev_solo_OOS']['max_dd']:.2%}  ret={sm['rev_solo_OOS']['total_return']:+.2%}")
    print(f"  mom_only IS : SR={sm['mom_solo_IS']['sharpe']:6.2f}  DD={sm['mom_solo_IS']['max_dd']:.2%}  ret={sm['mom_solo_IS']['total_return']:+.2%}")
    print(f"  rev_only IS : SR={sm['rev_solo_IS']['sharpe']:6.2f}  DD={sm['rev_solo_IS']['max_dd']:.2%}  ret={sm['rev_solo_IS']['total_return']:+.2%}")
    print(f"  mom-rev correlation: {sm['sleeve_correlation_FULL']:+.3f}")

    print()
    print("WALK-FORWARD V_60_40:")
    for f in wf:
        print(f"  fold{f['fold']}: SR={f['sharpe']:6.2f}  DD={f['max_dd']:7.2%}  ret={f['total_return']:+7.2%}")

    print()
    print("COST STRESS V_60_40 OOS:")
    for k, v in cost_stress.items():
        print(f"  {k:5s}: SR={v['OOS_sharpe']:6.2f}  DD={v['OOS_max_dd']:7.2%}  ret={v['OOS_total_return']:+7.2%}")

    print()
    print("GATES (V_60_40 primary):")
    for k, v in gates.items():
        print(f"  {k}: {'PASS' if v else 'FAIL'}")
    print(f"\nVERDICT: {verdict} ({n_pass}/6 gates pass)")
    print(f"Elapsed: {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
