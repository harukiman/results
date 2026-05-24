"""
Wave K132 — Realized vs Implied Funding Term-Structure (R4-20)

Hypothesis (QuantJourney substack):
- Compare 8H realized funding vs 7d annualized funding (term spread).
- Steepening (8h >> 7d avg) = aggressive long-leverage build → risk-off precursor → SHORT
- Flattening (8h ≈ 7d) / Inverted = squeeze risk faded → LONG

Method (pre-registered):
1. Per symbol per 8H funding event:
   - instant_fr  = latest 8H funding rate (the just-printed event)
   - mean_7d_fr  = trailing 7-day mean (21 events) of funding rate, LAGGED by 1 event
                   (so we use only known data at decision time)
   - term_spread = instant_fr - mean_7d_fr     [positive = steepening]
2. Signal (apply at next 4H bar after event):
   - term_spread > +5bp  → SHORT
   - term_spread < -5bp  → LONG
   - else flat
3. Hold: 24h (6 × 4H bars)
4. Per-symbol equal-weight portfolio
5. Costs: 0.07% per side (0.04% taker + 0.03% slippage)
6. Vol target 10% annual via ex-post leverage scaling on OOS

Variants:
- V_5bp   : threshold ±5bp default
- V_3bp   : looser ±3bp
- V_10bp  : stricter ±10bp
- V_zscore: z-score of (instant - mean_7d) rolling 30d, |z|>1 trigger

P&L decomposition: funding income/cost vs price PnL.
"""

from __future__ import annotations

import json
import math
import os
import sys
import time
import warnings
from math import erf

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

CACHE = "/Users/nekonaomichi/crypto-lab/cache"
OUT_PY = "/Users/nekonaomichi/crypto-lab/wave_k132_funding_ts.py"
OUT_JSON = "/Users/nekonaomichi/crypto-lab/wave_k132_funding_ts.json"
OUT_CURVES = "/Users/nekonaomichi/crypto-lab/wave_k132_curves.json"

# --------- universe ----------
# SHIB has no FR cache → 14 symbols
SYMBOLS = [
    "BTC", "ETH", "SOL", "BNB", "DOGE", "AVAX", "LINK",
    "ADA", "XRP", "INJ", "OP", "WIF", "BONK", "ARB",
]
FR_SYMBOL_MAP = {  # for FR cache filename, BONK uses 1000BONK
    "BONK": "1000BONKUSDT",
}

BARS_PER_DAY = 6     # 4H bars
FUND_PER_DAY = 3     # 8H funding events
HOLD_BARS = 6        # 24h hold = 6 × 4H bars
ROLL_EVENTS_7D = 21  # 7d × 3 events/day

IS_FRAC = 0.70

TAKER_BPS = 4.0
SLIP_BPS = 3.0
COST_PER_SIDE = (TAKER_BPS + SLIP_BPS) / 1e4  # 0.07%

VOL_TARGET_ANNUAL = 0.10

# Threshold variants (in fr units: 5bp = 0.0005)
VARIANTS = {
    "V_5bp": {"kind": "abs", "thresh": 0.0005},
    "V_3bp": {"kind": "abs", "thresh": 0.0003},
    "V_10bp": {"kind": "abs", "thresh": 0.0010},
    "V_zscore": {"kind": "z", "window": 30 * FUND_PER_DAY, "thresh": 1.0},  # 30d z-window
}


# --------- data loading ----------
def fr_symbol(sym: str) -> str:
    return FR_SYMBOL_MAP.get(sym, f"{sym}USDT")


def load_symbol(sym: str) -> pd.DataFrame:
    """Return 4H DataFrame with funding events attached.

    Columns:
      ts, close, ret_1, funding_event (raw 8h rate on event bars else NaN),
      funding_paid (0 outside events; raw fr at event bars; long side pays positive),
      instant_fr (per-event, ffilled at event bars only),
      mean_7d_fr (trailing 21-event mean, LAGGED 1 event),
      term_spread (instant_fr - mean_7d_fr),
      z_spread (z-score of term_spread rolling V_zscore window).
    """
    px = pd.read_parquet(f"{CACHE}/{sym}USDT_4h_730d.parquet")
    frfile = f"{CACHE}/bybit_fr_{fr_symbol(sym)}_730d.parquet"
    fr = pd.read_parquet(frfile)

    px = (
        px[["open_time", "close"]]
        .rename(columns={"open_time": "ts"})
        .sort_values("ts")
        .reset_index(drop=True)
    )
    fr = fr.sort_values("timestamp").reset_index(drop=True)

    # FR-event-level series with rolling stats
    fr_only = fr.copy()
    fr_only["mean_7d_fr"] = (
        fr_only["funding_rate"].rolling(ROLL_EVENTS_7D, min_periods=ROLL_EVENTS_7D).mean()
    )
    # Lag mean_7d_fr by 1 event (so at the moment instant_fr just printed,
    # we compare against PRIOR 7d mean — strictly using past data)
    fr_only["mean_7d_fr"] = fr_only["mean_7d_fr"].shift(1)
    fr_only["term_spread"] = fr_only["funding_rate"] - fr_only["mean_7d_fr"]
    # Z-score rolling window
    zw = VARIANTS["V_zscore"]["window"]
    rmean = fr_only["term_spread"].rolling(zw, min_periods=zw).mean().shift(1)
    rstd = fr_only["term_spread"].rolling(zw, min_periods=zw).std().shift(1)
    fr_only["z_spread"] = (fr_only["term_spread"] - rmean) / rstd.replace(0, np.nan)

    # Attach event-level series to 4H bars by timestamp join
    fr_indexed = fr_only.set_index("timestamp")
    px = px.set_index("ts")
    px["funding_event"] = fr_indexed["funding_rate"].reindex(px.index)
    px["instant_fr"] = fr_indexed["funding_rate"].reindex(px.index)
    px["mean_7d_fr"] = fr_indexed["mean_7d_fr"].reindex(px.index)
    px["term_spread"] = fr_indexed["term_spread"].reindex(px.index)
    px["z_spread"] = fr_indexed["z_spread"].reindex(px.index)
    px = px.reset_index()

    # Forward-fill signal-input series across non-event 4H bars,
    # then lag by 1 bar so signal at bar t is decided using data known at bar t-1 close
    for col in ["instant_fr", "mean_7d_fr", "term_spread", "z_spread"]:
        px[col] = px[col].ffill().shift(1)

    # funding paid per bar: nonzero on bars where a funding event occurred
    px["funding_paid"] = px["funding_event"].fillna(0.0)

    px["close"] = px["close"].astype(float)
    px["ret_1"] = px["close"].pct_change()
    return px


# --------- signal ----------
def build_signal_threshold(df: pd.DataFrame, thresh: float) -> pd.Series:
    """Threshold variant: short when term_spread > thresh, long when < -thresh, hold HOLD_BARS."""
    raw = pd.Series(0, index=df.index, dtype=int)
    raw[df["term_spread"] > thresh] = -1   # steepening → SHORT
    raw[df["term_spread"] < -thresh] = 1   # flattening/inverted → LONG
    return apply_hold(raw, HOLD_BARS)


def build_signal_zscore(df: pd.DataFrame, thresh: float) -> pd.Series:
    raw = pd.Series(0, index=df.index, dtype=int)
    raw[df["z_spread"] > thresh] = -1
    raw[df["z_spread"] < -thresh] = 1
    return apply_hold(raw, HOLD_BARS)


def apply_hold(raw_signal: pd.Series, hold_bars: int) -> pd.Series:
    """Convert event-triggered raw signal into position held for hold_bars.

    Rule: on bar t, if raw[t] != 0, position becomes raw[t] for [t, t+hold_bars-1].
    Last trigger wins on overlap (re-entry).
    """
    pos = np.zeros(len(raw_signal), dtype=int)
    arr = raw_signal.values
    n = len(arr)
    i = 0
    while i < n:
        if arr[i] != 0:
            end = min(n, i + hold_bars)
            pos[i:end] = arr[i]
            i = end
        else:
            i += 1
    return pd.Series(pos, index=raw_signal.index)


# --------- backtest ----------
def apply_costs_and_funding(df: pd.DataFrame, pos: pd.Series, cost_mult: float = 1.0) -> pd.DataFrame:
    """Return df with strategy returns.

    Decomposition columns:
      ret_price_only: pos_next * ret_1
      ret_funding   : -pos_next * funding_paid  (long pays positive fr)
      cost          : per-side cost on position changes
      ret_strat_net : sum of all three
    """
    out = df.copy()
    pos = pos.fillna(0).astype(int)
    pos_next = pos.shift(1).fillna(0)
    turns = (pos - pos.shift(1).fillna(0)).abs()
    cost = turns * COST_PER_SIDE * cost_mult

    ret_price = pos_next * out["ret_1"]
    ret_fund = -pos_next * out["funding_paid"]

    out["pos"] = pos
    out["pos_next"] = pos_next
    out["ret_price_only"] = ret_price
    out["ret_funding"] = ret_fund
    out["cost"] = cost
    out["ret_strat_net"] = ret_price + ret_fund - cost
    return out


# --------- metrics ----------
PERIODS_PER_YEAR = BARS_PER_DAY * 365  # 2190


def sharpe(returns: np.ndarray, periods_per_year: float = PERIODS_PER_YEAR) -> float:
    r = np.asarray(returns)
    r = r[~np.isnan(r)]
    if len(r) < 10 or r.std() == 0:
        return 0.0
    return float(r.mean() / r.std() * math.sqrt(periods_per_year))


def max_dd(returns: np.ndarray) -> float:
    r = np.asarray(returns)
    r = r[~np.isnan(r)]
    if len(r) == 0:
        return 0.0
    eq = (1 + r).cumprod()
    peak = np.maximum.accumulate(eq)
    dd = (eq - peak) / peak
    return float(dd.min())


def win_rate(returns: np.ndarray) -> float:
    r = np.asarray(returns)
    r = r[~np.isnan(r) & (r != 0)]
    if len(r) == 0:
        return 0.0
    return float((r > 0).mean())


def vol_target_scale(returns: np.ndarray, target_annual: float = VOL_TARGET_ANNUAL) -> np.ndarray:
    r = np.asarray(returns)
    r = np.nan_to_num(r, nan=0.0)
    realized_vol = r.std() * math.sqrt(PERIODS_PER_YEAR)
    if realized_vol == 0:
        return r
    k = target_annual / realized_vol
    return r * k


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


# --------- per-symbol run ----------
def run_symbol(sym: str) -> dict:
    df = load_symbol(sym)
    n = len(df)
    cut = int(n * IS_FRAC)

    res = {"symbol": sym, "n_bars": n, "variants": {}, "term_spread_stats": {}, "pnl_decomp": {}}
    outs_by_variant = {}

    for vname, vparams in VARIANTS.items():
        if vparams["kind"] == "abs":
            pos = build_signal_threshold(df, vparams["thresh"])
        else:
            pos = build_signal_zscore(df, vparams["thresh"])
        out = apply_costs_and_funding(df, pos)
        outs_by_variant[vname] = out

        def slice_metrics(out: pd.DataFrame, lo: int, hi: int) -> dict:
            sub = out.iloc[lo:hi]
            r = sub["ret_strat_net"].values
            rp = sub["ret_price_only"].values
            rf = sub["ret_funding"].values
            return {
                "sharpe": sharpe(r),
                "max_dd": max_dd(r),
                "win_rate": win_rate(r),
                "n_bars": int(len(r)),
                "exposure": float((sub["pos_next"] != 0).mean()),
                "long_frac": float((sub["pos_next"] > 0).mean()),
                "short_frac": float((sub["pos_next"] < 0).mean()),
                "total_return": float((1 + pd.Series(r).fillna(0)).prod() - 1),
                "price_pnl_sum": float(pd.Series(rp).fillna(0).sum()),
                "funding_pnl_sum": float(pd.Series(rf).fillna(0).sum()),
                "cost_sum": float(pd.Series(sub["cost"]).fillna(0).sum()),
            }

        res["variants"][vname] = {
            "IS": slice_metrics(out, 0, cut),
            "OOS": slice_metrics(out, cut, n),
            "FULL": slice_metrics(out, 0, n),
        }

    # term_spread distribution (using event-only rows since 4H ffill duplicates)
    ts_event = df.loc[df["funding_event"].notna(), "term_spread"].dropna()
    if len(ts_event):
        res["term_spread_stats"] = {
            "n_events": int(len(ts_event)),
            "mean": float(ts_event.mean()),
            "std": float(ts_event.std()),
            "p05": float(ts_event.quantile(0.05)),
            "p25": float(ts_event.quantile(0.25)),
            "p50": float(ts_event.quantile(0.50)),
            "p75": float(ts_event.quantile(0.75)),
            "p95": float(ts_event.quantile(0.95)),
            "max": float(ts_event.max()),
            "min": float(ts_event.min()),
            "frac_gt_5bp": float((ts_event > 0.0005).mean()),
            "frac_lt_neg5bp": float((ts_event < -0.0005).mean()),
            "frac_gt_3bp": float((ts_event > 0.0003).mean()),
            "frac_lt_neg3bp": float((ts_event < -0.0003).mean()),
        }

    return res, outs_by_variant


# --------- portfolio ----------
def build_portfolio(per_sym_outs: dict[str, pd.DataFrame]) -> pd.Series:
    frames = []
    for sym, out in per_sym_outs.items():
        s = out["ret_strat_net"].rename(sym).copy()
        s.index = out["ts"]
        frames.append(s)
    df = pd.concat(frames, axis=1).sort_index()
    df = df.fillna(0.0)
    return df.mean(axis=1)


def build_portfolio_decomp(per_sym_outs: dict[str, pd.DataFrame], col: str) -> pd.Series:
    frames = []
    for sym, out in per_sym_outs.items():
        s = out[col].rename(sym).copy()
        s.index = out["ts"]
        frames.append(s)
    df = pd.concat(frames, axis=1).sort_index()
    df = df.fillna(0.0)
    return df.mean(axis=1)


# --------- walk-forward ----------
def walk_forward_4fold(per_sym_outs: dict[str, pd.DataFrame]) -> list[dict]:
    port = build_portfolio(per_sym_outs)
    n = len(port)
    fold_size = n // 4
    wf = []
    for k in range(4):
        lo, hi = k * fold_size, (k + 1) * fold_size if k < 3 else n
        sub = port.values[lo:hi]
        wf.append({
            "fold": k,
            "sharpe": sharpe(sub),
            "max_dd": max_dd(sub),
            "total_return": float((1 + pd.Series(sub).fillna(0)).prod() - 1),
            "n_bars": int(len(sub)),
        })
    return wf


# --------- permutation ----------
def permutation_test_portfolio(per_sym_outs: dict[str, pd.DataFrame], n: int = 300, seed: int = 42) -> dict:
    """Shuffle SIGN of each symbol's ret_strat_net within blocks; recompute portfolio Sharpe.

    This destroys any directional edge of the underlying signal while preserving the magnitude
    distribution and per-symbol correlation structure.
    """
    rng = np.random.default_rng(seed)
    base_port = build_portfolio(per_sym_outs)
    base_arr = base_port.values
    base_sr = sharpe(base_arr)
    n_obs = len(base_arr)
    block = 20
    null_sharpes = []

    # Pre-collect per-sym arrays aligned to common index
    syms = list(per_sym_outs.keys())
    aligned = {}
    for sym in syms:
        s = per_sym_outs[sym]["ret_strat_net"].copy()
        s.index = per_sym_outs[sym]["ts"]
        aligned[sym] = s
    big = pd.concat(aligned, axis=1).fillna(0.0).sort_index()

    arrs = big.values  # shape (T, n_sym)
    T, k = arrs.shape

    for _ in range(n):
        # block-wise sign flip per symbol independently
        sign = np.ones_like(arrs)
        n_blocks = T // block + 1
        flips = rng.choice([-1, 1], size=(n_blocks, k))
        for b in range(n_blocks):
            lo = b * block
            hi = min(T, lo + block)
            sign[lo:hi, :] = flips[b, :]
        perm = arrs * sign
        port_perm = perm.mean(axis=1)
        null_sharpes.append(sharpe(port_perm))

    null_sharpes = np.array(null_sharpes)
    p = float((null_sharpes >= base_sr).mean())
    return {
        "base_sharpe": float(base_sr),
        "null_mean": float(null_sharpes.mean()),
        "null_std": float(null_sharpes.std()),
        "null_p95": float(np.percentile(null_sharpes, 95)),
        "p_value": p,
    }


# --------- curves ----------
def equity_curve(returns: pd.Series, every: int = 6) -> list[dict]:
    eq = (1 + returns.fillna(0)).cumprod()
    return [
        {"ts": str(ts), "eq": float(v)}
        for ts, v in eq.iloc[::every].items()
    ]


# --------- main ----------
def main():
    t0 = time.time()
    print("=" * 78)
    print("Wave K132 — Realized vs Implied Funding Term-Structure (R4-20)")
    print("=" * 78)

    all_results = {}
    outs_by_variant_per_sym = {v: {} for v in VARIANTS.keys()}
    for sym in SYMBOLS:
        try:
            res, outs_by_v = run_symbol(sym)
            all_results[sym] = res
            for vname, out in outs_by_v.items():
                outs_by_variant_per_sym[vname][sym] = out
            v5 = res["variants"]["V_5bp"]
            print(f"  {sym:5s} n={res['n_bars']:5d}  "
                  f"V5: IS_SR={v5['IS']['sharpe']:6.2f}  OOS_SR={v5['OOS']['sharpe']:6.2f}  "
                  f"OOS_exp={v5['OOS']['exposure']:.2%}  "
                  f"long={v5['OOS']['long_frac']:.2%} short={v5['OOS']['short_frac']:.2%}")
        except Exception as e:
            print(f"  {sym}: FAILED — {e}")
            continue

    # Portfolio metrics per variant
    portfolio_metrics = {}
    curves = {}
    for vname in VARIANTS.keys():
        ps = outs_by_variant_per_sym[vname]
        if not ps:
            continue
        port = build_portfolio(ps)
        n_full = len(port)
        cut = int(n_full * IS_FRAC)
        arr = port.values
        # Vol target scale on OOS (informational)
        oos = arr[cut:]
        oos_vt = vol_target_scale(oos)
        ci = block_bootstrap_sharpe(oos, block=20, n=300)

        # decomposition
        port_price = build_portfolio_decomp(ps, "ret_price_only")
        port_fund = build_portfolio_decomp(ps, "ret_funding")
        port_cost = build_portfolio_decomp(ps, "cost")

        portfolio_metrics[vname] = {
            "n_symbols": len(ps),
            "IS_sharpe": sharpe(arr[:cut]),
            "OOS_sharpe": sharpe(arr[cut:]),
            "OOS_sharpe_voltgt10pct": sharpe(oos_vt),
            "OOS_sharpe_CI95": ci,
            "OOS_max_dd": max_dd(arr[cut:]),
            "OOS_win_rate": win_rate(arr[cut:]),
            "FULL_sharpe": sharpe(arr),
            "FULL_total_return": float((1 + pd.Series(arr).fillna(0)).prod() - 1),
            "OOS_price_pnl": float(pd.Series(port_price.values[cut:]).fillna(0).sum()),
            "OOS_funding_pnl": float(pd.Series(port_fund.values[cut:]).fillna(0).sum()),
            "OOS_cost": float(pd.Series(port_cost.values[cut:]).fillna(0).sum()),
            "OOS_net_pnl": float(pd.Series(arr[cut:]).fillna(0).sum()),
        }
        curves[vname] = equity_curve(port, every=6)

    # Walk-forward on default variant V_5bp
    wf = walk_forward_4fold(outs_by_variant_per_sym["V_5bp"])

    # Permutation test on V_5bp portfolio
    print("Permutation test (V_5bp portfolio, n=300)...")
    perm = permutation_test_portfolio(outs_by_variant_per_sym["V_5bp"], n=300)
    print(f"  base SR={perm['base_sharpe']:.3f} null_mean={perm['null_mean']:.3f} "
          f"null_p95={perm['null_p95']:.3f} p={perm['p_value']:.3f}")

    # Cost stress ±50% on V_5bp
    cost_stress = {}
    base_outs = outs_by_variant_per_sym["V_5bp"]
    n_full = len(build_portfolio(base_outs))
    cut = int(n_full * IS_FRAC)
    for mult, name in [(0.5, "low"), (1.0, "base"), (1.5, "high")]:
        stressed = {}
        for sym in SYMBOLS:
            try:
                df = load_symbol(sym)
                pos = build_signal_threshold(df, VARIANTS["V_5bp"]["thresh"])
                stressed[sym] = apply_costs_and_funding(df, pos, cost_mult=mult)
            except Exception:
                continue
        port = build_portfolio(stressed)
        oos = port.values[cut:]
        cost_stress[name] = {
            "OOS_sharpe": sharpe(oos),
            "OOS_max_dd": max_dd(oos),
        }

    # DSR (4 trials — 4 variants)
    n_oos = n_full - cut
    dsr_map = {}
    for vname, m in portfolio_metrics.items():
        dsr_map[vname] = dsr(m["OOS_sharpe"], n_oos, n_trials=len(VARIANTS))

    # §6 gates — primary V_5bp
    pri = portfolio_metrics["V_5bp"]
    gates = {
        "G1_OOS_Sharpe_gt_0.5":         pri["OOS_sharpe"] > 0.5,
        "G2_OOS_MaxDD_gt_-0.30":        pri["OOS_max_dd"] > -0.30,
        "G3_BlockBoot_CI95_low_gt_0":   pri["OOS_sharpe_CI95"][0] > 0,
        "G4_Perm_p_lt_0.05":            perm["p_value"] < 0.05,
        "G5_DSR_gt_0.95":               (dsr_map["V_5bp"] if not math.isnan(dsr_map["V_5bp"]) else 0) > 0.95,
        "G6_CostStress_high_OOS_sr_gt_0.3": cost_stress["high"]["OOS_sharpe"] > 0.3,
    }
    n_pass = sum(gates.values())
    verdict = (
        "ACCEPT" if n_pass >= 5
        else "CONDITIONAL" if n_pass >= 3
        else "REJECT"
    )

    # Save curves
    with open(OUT_CURVES, "w") as f:
        json.dump(curves, f, indent=2)

    result = {
        "wave": "K132",
        "title": "Realized vs Implied Funding Term-Structure (R4-20)",
        "as_of": pd.Timestamp.utcnow().isoformat(),
        "symbols": SYMBOLS,
        "n_symbols": len(SYMBOLS),
        "thresholds_bp": {"V_5bp": 5, "V_3bp": 3, "V_10bp": 10},
        "zscore_window_days": 30,
        "hold_bars_24h": HOLD_BARS,
        "costs": {"taker_bps": TAKER_BPS, "slip_bps": SLIP_BPS, "per_side_pct": COST_PER_SIDE * 100},
        "per_symbol": all_results,
        "portfolio": portfolio_metrics,
        "walk_forward_V_5bp": wf,
        "permutation_test_V_5bp": perm,
        "cost_stress_V_5bp": cost_stress,
        "DSR": dsr_map,
        "gates": gates,
        "n_gates_pass": n_pass,
        "verdict": verdict,
        "elapsed_sec": time.time() - t0,
    }
    with open(OUT_JSON, "w") as f:
        json.dump(result, f, indent=2, default=str)

    print()
    print("=" * 78)
    print("PORTFOLIO (V_5bp default)")
    print(f"  IS  Sharpe: {pri['IS_sharpe']:.3f}")
    print(f"  OOS Sharpe: {pri['OOS_sharpe']:.3f}  CI95=[{pri['OOS_sharpe_CI95'][0]:.2f},{pri['OOS_sharpe_CI95'][1]:.2f}]")
    print(f"  OOS MaxDD : {pri['OOS_max_dd']:.2%}")
    print(f"  OOS net pnl: {pri['OOS_net_pnl']:+.4f} = price {pri['OOS_price_pnl']:+.4f} + fund {pri['OOS_funding_pnl']:+.4f} - cost {pri['OOS_cost']:+.4f}")

    print()
    print("VARIANT COMPARISON (OOS Sharpe / MaxDD / total_return):")
    for vname, m in portfolio_metrics.items():
        print(f"  {vname:9s} OOS_SR={m['OOS_sharpe']:6.2f}  DD={m['OOS_max_dd']:6.2%}  "
              f"FULL_ret={m['FULL_total_return']:+7.2%}")

    print()
    print("Cost stress OOS Sharpe:")
    for k, v in cost_stress.items():
        print(f"  {k:5s}: SR={v['OOS_sharpe']:.3f}  DD={v['OOS_max_dd']:.2%}")

    print()
    print("GATES:")
    for k, v in gates.items():
        print(f"  {k}: {'PASS' if v else 'FAIL'}")
    print(f"\nVERDICT: {verdict} ({n_pass}/6 gates pass)")
    print(f"Elapsed: {time.time()-t0:.1f}s")


if __name__ == "__main__":
    main()
