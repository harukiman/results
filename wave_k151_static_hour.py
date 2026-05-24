"""
Wave K151 — STATIC Hour-of-Day Bucket Strategy (K148 follow-up).

Hypothesis (K148 descriptive finding, 730d cross-symbol):
  - 00 UTC bar avg = +4.0 bps, 73% syms positive
  - 20 UTC bar avg = +3.5 bps, 82% syms positive
  - 08 UTC bar avg = -4.6 bps, 14% syms positive
  - 12 UTC bar avg = -4.7 bps, 16% syms positive

K148 with a *rolling* hour-bucket adapter ended up chasing recent outliers and
failed (combined OOS Sharpe ~ -5).  K151 fixes the hour assignment to the four
buckets above (STATIC, no adaptation, pre-registered) and tests whether the
static design saves the K148 hypothesis.

Method (pre-registered, hard-coded — no adaptation):
  - Per 4H bar:
      * 00 UTC : LONG  basket  (top-15 liquid, equal weight)
      * 20 UTC : LONG  basket
      * 08 UTC : SHORT basket
      * 12 UTC : SHORT basket
      * 04, 16 : FLAT
  - Hold: 1 bar (4H).  Cost = 0.04% + 0.03% per side (entry + exit).
  - Basket position is the equal-weight average per-symbol leg; rebalanced
    every bar.

Variants:
  V_LL_SS         : long 00+20, short 08+12   (primary)
  V_LL_only       : long 00+20, no short
  V_strict_LS     : long 20 only, short 08 only (extremes)
  V_combine_filter: V_LL_SS but skip when BTC trend down (EMA200)

Backtest + audit:
  - 730d window, IS 70% / OOS 30%
  - Portfolio Sharpe (top-15 equal-weight)
  - Walk-forward 4-fold
  - Permutation n=300 (shuffle hour labels)
  - Block bootstrap n=300
  - DSR with N_trials=4
  - Cost stress ±50%
"""

from __future__ import annotations

import json
import math
import os
import time
import warnings
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

CACHE = "/Users/nekonaomichi/crypto-lab/cache"
OUT_PY = "/Users/nekonaomichi/crypto-lab/wave_k151_static_hour.py"
OUT_JSON = "/Users/nekonaomichi/crypto-lab/wave_k151_static_hour.json"
OUT_CURVES = "/Users/nekonaomichi/crypto-lab/wave_k151_curves.json"
OUT_MD = "/Users/nekonaomichi/crypto-lab/wave_k151_static_hour.md"

BARS_PER_DAY = 6
HOURS_OF_DAY = [0, 4, 8, 12, 16, 20]
ANNUALIZER = BARS_PER_DAY * 365  # 2190

IS_FRAC = 0.70

# --- pre-registered STATIC hour buckets ---
LONG_HOURS_PRIMARY = {0, 20}
SHORT_HOURS_PRIMARY = {8, 12}
LONG_HOURS_STRICT = {20}
SHORT_HOURS_STRICT = {8}

# Costs (matches spec)
TAKER_BPS = 4.0
SLIP_BPS = 3.0
COST_PER_SIDE = (TAKER_BPS + SLIP_BPS) / 1e4  # 0.07%

# Trend filter for combine_filter variant
EMA_LEN = 200


# ---------- universe ----------
def discover_symbols() -> List[str]:
    syms = []
    for fn in sorted(os.listdir(CACHE)):
        if not fn.endswith("_4h_730d.parquet"):
            continue
        if not fn[0].isalpha():
            continue
        if fn.startswith("hist_premium"):
            continue
        sym_full = fn.replace("_4h_730d.parquet", "")
        if sym_full.endswith("USDT"):
            syms.append(sym_full.replace("USDT", ""))
    return syms


SYMBOLS = discover_symbols()


def load_symbol(sym: str) -> pd.DataFrame:
    fp = f"{CACHE}/{sym}USDT_4h_730d.parquet"
    df = pd.read_parquet(fp)[["open_time", "close", "quote_volume"]].rename(
        columns={"open_time": "ts", "quote_volume": "qvol"}
    )
    df = df.sort_values("ts").reset_index(drop=True)
    df["close"] = df["close"].astype(float)
    df["qvol"] = df["qvol"].astype(float)
    df["ret_1"] = df["close"].pct_change()
    df["hour"] = df["ts"].dt.hour.astype(int)
    return df


# ---------- position construction (STATIC) ----------
def static_signal(hour_arr: np.ndarray, long_hours: set, short_hours: set) -> np.ndarray:
    """Return signal at OPEN of bar t based purely on UTC hour (no look-ahead)."""
    sig = np.zeros(len(hour_arr), dtype=float)
    sig[np.isin(hour_arr, list(long_hours))] = 1.0
    sig[np.isin(hour_arr, list(short_hours))] = -1.0
    return sig


def apply_costs(df: pd.DataFrame, sig: np.ndarray, cost_mult: float = 1.0) -> pd.DataFrame:
    """For each bar t: signal sig[t] is taken at OPEN of bar t.  Realized PnL is
    sig[t] * ret_1[t] (close-to-close).  Cost is |sig[t] - sig[t-1]| * COST_PER_SIDE.
    """
    out = df.copy()
    out["pos"] = sig
    out["gross_ret"] = sig * out["ret_1"].fillna(0.0)
    turns = np.abs(np.diff(np.concatenate([[0.0], sig])))
    out["cost"] = turns * COST_PER_SIDE * cost_mult
    out["net_ret"] = out["gross_ret"] - out["cost"]
    return out


# ---------- metrics ----------
def sharpe(returns: np.ndarray, periods_per_year: float = ANNUALIZER) -> float:
    r = np.asarray(returns, dtype=float)
    r = r[~np.isnan(r)]
    if len(r) < 10 or r.std() == 0:
        return 0.0
    return float(r.mean() / r.std() * math.sqrt(periods_per_year))


def max_dd(returns: np.ndarray) -> float:
    r = np.asarray(returns, dtype=float)
    r = np.nan_to_num(r, nan=0.0)
    if len(r) == 0:
        return 0.0
    eq = (1 + r).cumprod()
    peak = np.maximum.accumulate(eq)
    return float(((eq - peak) / peak).min())


def win_rate(returns: np.ndarray) -> float:
    r = np.asarray(returns, dtype=float)
    r = r[~np.isnan(r) & (r != 0)]
    if len(r) == 0:
        return 0.0
    return float((r > 0).mean())


def t_stat(returns: np.ndarray) -> float:
    r = np.asarray(returns, dtype=float)
    r = r[~np.isnan(r) & (r != 0)]
    if len(r) < 5 or r.std() == 0:
        return 0.0
    return float(r.mean() / (r.std() / math.sqrt(len(r))))


# ---------- audits ----------
def block_bootstrap_sharpe(ret: np.ndarray, block: int = 20, n: int = 300, seed: int = 7) -> Tuple[float, float]:
    rng = np.random.default_rng(seed)
    r = np.asarray(ret, dtype=float)
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
    return (float(np.percentile(samples, 5)), float(np.percentile(samples, 95)))


def permutation_hour(port_rets: np.ndarray, hours: np.ndarray,
                     base_sharpe_val: float, long_hours: set, short_hours: set,
                     n: int = 300, seed: int = 42) -> Dict:
    """Null: hour-of-day label is uninformative.

    Procedure: keep the per-bar realised symbol-basket returns fixed (same series
    of bar-level idiosyncratic moves) but shuffle the 'hour' label assigned to
    each bar via a per-day permutation of {0,4,8,12,16,20}.  Then recompute
    signal, costs and Sharpe.

    The trick: under the null, the realised return at a bar does NOT depend on
    its hour.  We can express the strategy as:
      net_ret[t] = sig(hour'[t]) * realized_bar_ret[t] - turnover_cost
    where realized_bar_ret[t] is the equal-weight basket return (fixed series).

    `port_rets` is the equal-weight basket gross-of-cost per-bar return
    (i.e. r_bar averaged across the 15 symbols).
    """
    rng = np.random.default_rng(seed)
    n_bars = len(port_rets)
    null_sharpes = np.empty(n, dtype=float)

    for i in range(n):
        sh = hours.copy()
        for d0 in range(0, n_bars, BARS_PER_DAY):
            d1 = min(d0 + BARS_PER_DAY, n_bars)
            sh[d0:d1] = rng.permutation(sh[d0:d1])
        sig = static_signal(sh, long_hours, short_hours)
        turns = np.abs(np.diff(np.concatenate([[0.0], sig])))
        cost = turns * COST_PER_SIDE
        net = sig * port_rets - cost
        null_sharpes[i] = sharpe(net)

    p = float((null_sharpes >= base_sharpe_val).mean())
    return {
        "base_sharpe": float(base_sharpe_val),
        "null_mean": float(null_sharpes.mean()),
        "null_std": float(null_sharpes.std()),
        "p_value": p,
        "n": n,
    }


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
    from math import erf
    return float(0.5 * (1 + erf(z / math.sqrt(2))))


# ---------- per-symbol pipeline ----------
def slice_metrics(out: pd.DataFrame, lo: int, hi: int) -> Dict:
    sub = out.iloc[lo:hi]
    r = sub["net_ret"].values
    pos_active = (sub["pos"] != 0)
    return {
        "sharpe": sharpe(r),
        "max_dd": max_dd(r),
        "win_rate": win_rate(r),
        "n_bars": int(len(r)),
        "exposure": float(pos_active.mean()),
        "total_return": float((1 + pd.Series(r).fillna(0)).prod() - 1),
        "mean_4h_ret_bps": float(np.nan_to_num(r, nan=0.0).mean() * 1e4),
    }


def hour_distribution_table(df: pd.DataFrame) -> Dict:
    """Per-hour empirical stats over the full 730d window (descriptive)."""
    g = df.groupby("hour")["ret_1"]
    tbl = {}
    for h in HOURS_OF_DAY:
        if h in g.groups:
            s = g.get_group(h).dropna().values
        else:
            s = np.array([])
        if len(s) == 0:
            tbl[int(h)] = {"n": 0, "mean_bps": 0.0, "std_bps": 0.0,
                           "win_rate": 0.0, "t_stat": 0.0}
            continue
        tbl[int(h)] = {
            "n": int(len(s)),
            "mean_bps": float(s.mean() * 1e4),
            "std_bps": float(s.std() * 1e4),
            "win_rate": float((s > 0).mean()),
            "t_stat": float(s.mean() / (s.std() / math.sqrt(len(s)))) if s.std() > 0 else 0.0,
        }
    return tbl


def run_variant_for_symbol(df: pd.DataFrame, long_hours: set, short_hours: set,
                           filter_long: np.ndarray | None = None,
                           filter_short: np.ndarray | None = None) -> pd.DataFrame:
    """Build static signal for one symbol; optionally apply per-bar long/short filters."""
    sig = static_signal(df["hour"].values, long_hours, short_hours)
    if filter_long is not None:
        # Skip longs where filter_long == False
        mask = (sig > 0) & (~filter_long)
        sig = sig.copy()
        sig[mask] = 0.0
    if filter_short is not None:
        mask = (sig < 0) & (~filter_short)
        sig = sig.copy()
        sig[mask] = 0.0
    return apply_costs(df, sig)


# ---------- portfolio ----------
def build_portfolio_returns(per_sym_outs: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Align all per-symbol net_ret series on timestamp, equal-weight per bar."""
    frames = []
    for sym, out in per_sym_outs.items():
        s = out["net_ret"].rename(sym).copy()
        s.index = out["ts"]
        frames.append(s)
    df = pd.concat(frames, axis=1).sort_index()
    df = df.fillna(0.0)
    df["portfolio"] = df.mean(axis=1)
    return df


def build_portfolio_gross(per_sym_outs: Dict[str, pd.DataFrame]) -> pd.Series:
    """Gross (pre-cost) equal-weight basket of per-symbol *bar* returns; used as the
    underlying for the permutation test where hour labels are shuffled but realised
    moves are fixed."""
    frames = []
    for sym, out in per_sym_outs.items():
        s = out["ret_1"].rename(sym).copy()
        s.index = out["ts"]
        frames.append(s)
    df = pd.concat(frames, axis=1).sort_index().fillna(0.0)
    return df.mean(axis=1)


def equity_curve(returns: pd.Series, downsample: int = 6) -> List[Dict]:
    eq = (1 + returns.fillna(0)).cumprod()
    sel = eq.iloc[::downsample]
    return [{"ts": str(ts), "eq": float(v)} for ts, v in sel.items()]


# ---------- main ----------
def main():
    t0 = time.time()
    print("=" * 72)
    print(f"Wave K151 — STATIC Hour-of-Day Buckets — {len(SYMBOLS)} symbols")
    print("=" * 72)

    # ----- load all symbols -----
    loaded: Dict[str, pd.DataFrame] = {}
    avg_qvol: Dict[str, float] = {}
    for sym in SYMBOLS:
        try:
            df = load_symbol(sym)
            if len(df) < 100:
                continue
            loaded[sym] = df
            avg_qvol[sym] = float(df["qvol"].mean())
        except Exception as e:
            print(f"  load FAIL {sym}: {e}")

    # ----- top-15 liquid -----
    liquid_ranked = sorted(avg_qvol.items(), key=lambda kv: kv[1], reverse=True)
    top15 = [s for s, _ in liquid_ranked[:15]]
    print(f"Top-15 liquid: {top15}")

    # ----- BTC trend filter (for V_combine_filter) -----
    btc_df = loaded["BTC"]
    ema = btc_df["close"].ewm(span=EMA_LEN, adjust=False).mean()
    btc_trend_up = (btc_df["close"] > ema).values  # array aligned with btc_df rows
    # Reindex by ts to make a per-ts lookup
    btc_trend_map = pd.Series(btc_trend_up, index=btc_df["ts"])

    # ----- per-symbol per-variant runs -----
    variants = {
        "V_LL_SS":           (LONG_HOURS_PRIMARY, SHORT_HOURS_PRIMARY, False),
        "V_LL_only":         (LONG_HOURS_PRIMARY, set(),               False),
        "V_strict_LS":       (LONG_HOURS_STRICT,  SHORT_HOURS_STRICT,  False),
        "V_combine_filter":  (LONG_HOURS_PRIMARY, SHORT_HOURS_PRIMARY, True),
    }

    per_symbol_results: Dict[str, Dict] = {}
    outs_by_variant: Dict[str, Dict[str, pd.DataFrame]] = {v: {} for v in variants}

    # Pre-compute hour distribution descriptives
    for sym in top15:
        df = loaded[sym]
        per_symbol_results[sym] = {
            "n_bars": int(len(df)),
            "avg_qvol": avg_qvol[sym],
            "hour_distribution": hour_distribution_table(df),
        }
        for vname, (lh, sh_, use_filter) in variants.items():
            if use_filter:
                trend_at_ts = btc_trend_map.reindex(df["ts"]).ffill().fillna(True).values.astype(bool)
                out = run_variant_for_symbol(df, lh, sh_, filter_long=trend_at_ts, filter_short=None)
            else:
                out = run_variant_for_symbol(df, lh, sh_)
            outs_by_variant[vname][sym] = out
            n = len(out)
            cut = int(n * IS_FRAC)
            per_symbol_results[sym][vname] = {
                "IS":   slice_metrics(out, 0, cut),
                "OOS":  slice_metrics(out, cut, n),
                "FULL": slice_metrics(out, 0, n),
            }

    # ----- portfolio metrics per variant -----
    portfolio_metrics: Dict[str, Dict] = {}
    portfolio_curves: Dict[str, pd.Series] = {}
    primary_v = "V_LL_SS"

    for vname in variants:
        pf = build_portfolio_returns(outs_by_variant[vname])
        port = pf["portfolio"]
        portfolio_curves[vname] = port
        arr = port.values
        n = len(arr)
        cut = int(n * IS_FRAC)
        m = {
            "n_symbols": len([s for s in outs_by_variant[vname]]),
            "n_bars": int(n),
            "IS_sharpe": sharpe(arr[:cut]),
            "OOS_sharpe": sharpe(arr[cut:]),
            "OOS_max_dd": max_dd(arr[cut:]),
            "OOS_win_rate": win_rate(arr[cut:]),
            "OOS_total_return": float((1 + pd.Series(arr[cut:]).fillna(0)).prod() - 1),
            "FULL_sharpe": sharpe(arr),
            "FULL_max_dd": max_dd(arr),
            "FULL_total_return": float((1 + pd.Series(arr).fillna(0)).prod() - 1),
            "mean_4h_ret_bps": float(np.nan_to_num(arr, nan=0.0).mean() * 1e4),
            "exposure_overall": float((arr != 0).mean()),
        }
        portfolio_metrics[vname] = m

    # ----- walk-forward 4-fold on primary variant -----
    arr_primary = portfolio_curves[primary_v].values
    n = len(arr_primary)
    fold = n // 4
    wf = []
    for k in range(4):
        lo, hi = k * fold, (k + 1) * fold if k < 3 else n
        sub = arr_primary[lo:hi]
        wf.append({
            "fold": k,
            "n_bars": int(len(sub)),
            "sharpe": sharpe(sub),
            "max_dd": max_dd(sub),
            "mean_4h_ret_bps": float(np.nan_to_num(sub, nan=0.0).mean() * 1e4),
        })

    # ----- block bootstrap on primary OOS -----
    cut = int(n * IS_FRAC)
    primary_ci = block_bootstrap_sharpe(arr_primary[cut:], block=20, n=300)
    portfolio_metrics[primary_v]["OOS_sharpe_CI95"] = primary_ci

    # ----- permutation test on primary (hour-label shuffle) -----
    # gross basket return (pre-cost average of per-symbol ret_1)
    gross_basket = build_portfolio_gross(outs_by_variant[primary_v])
    # align hour labels to gross_basket
    sample_sym = top15[0]
    ts_index = gross_basket.index
    # map each ts to its hour using sample
    hours_arr = pd.Series(ts_index).dt.hour.values
    base_sharpe_primary = portfolio_metrics[primary_v]["FULL_sharpe"]
    perm_primary = permutation_hour(
        gross_basket.values, hours_arr, base_sharpe_primary,
        LONG_HOURS_PRIMARY, SHORT_HOURS_PRIMARY, n=300,
    )
    print(f"Permutation (V_LL_SS): base_SR={perm_primary['base_sharpe']:.3f}  "
          f"null_mean={perm_primary['null_mean']:.3f}  p={perm_primary['p_value']:.3f}")

    # ----- DSR (N_trials = 4 variants) -----
    n_oos = n - cut
    dsr_results = {v: dsr(portfolio_metrics[v]["OOS_sharpe"], n_oos, n_trials=4)
                   for v in portfolio_metrics}

    # ----- cost stress on primary -----
    cost_stress = {}
    for mult, name in [(0.5, "low"), (1.0, "base"), (1.5, "high")]:
        outs_cs = {}
        lh, shs, use_filter = variants[primary_v]
        for sym in top15:
            df = loaded[sym]
            out = apply_costs(df, static_signal(df["hour"].values, lh, shs), cost_mult=mult)
            outs_cs[sym] = out
        port_cs = build_portfolio_returns(outs_cs)["portfolio"]
        arr_cs = port_cs.values
        n_cs = len(arr_cs)
        cut_cs = int(n_cs * IS_FRAC)
        cost_stress[name] = {
            "mult": mult,
            "OOS_sharpe": sharpe(arr_cs[cut_cs:]),
            "OOS_max_dd": max_dd(arr_cs[cut_cs:]),
            "FULL_sharpe": sharpe(arr_cs),
            "FULL_total_return": float((1 + pd.Series(arr_cs).fillna(0)).prod() - 1),
        }
        print(f"  cost {name:5s} (x{mult}): OOS_SR={cost_stress[name]['OOS_sharpe']:.3f}  "
              f"FULL_SR={cost_stress[name]['FULL_sharpe']:.3f}  "
              f"DD={cost_stress[name]['OOS_max_dd']:.2%}")

    # ----- per-hour realized stats (basket level) on primary -----
    df0 = loaded[top15[0]][["ts", "hour"]].copy()
    df0 = df0.set_index("ts").reindex(gross_basket.index, method="nearest")
    hour_series = df0["hour"].values
    basket_arr = gross_basket.values
    per_hour_basket = {}
    for h in HOURS_OF_DAY:
        sel = basket_arr[hour_series == h]
        if len(sel) == 0:
            per_hour_basket[int(h)] = {"n": 0, "mean_bps": 0.0, "win_rate": 0.0, "t_stat": 0.0}
            continue
        per_hour_basket[int(h)] = {
            "n": int(len(sel)),
            "mean_bps": float(sel.mean() * 1e4),
            "std_bps": float(sel.std() * 1e4),
            "win_rate": float((sel > 0).mean()),
            "t_stat": float(sel.mean() / (sel.std() / math.sqrt(len(sel)))) if sel.std() > 0 else 0.0,
        }

    # IS/OOS split per-hour to detect regime drift
    per_hour_is = {}
    per_hour_oos = {}
    for h in HOURS_OF_DAY:
        sel_is = basket_arr[:cut][hour_series[:cut] == h]
        sel_oos = basket_arr[cut:][hour_series[cut:] == h]
        per_hour_is[int(h)] = {
            "n": int(len(sel_is)),
            "mean_bps": float(sel_is.mean() * 1e4) if len(sel_is) else 0.0,
            "win_rate": float((sel_is > 0).mean()) if len(sel_is) else 0.0,
        }
        per_hour_oos[int(h)] = {
            "n": int(len(sel_oos)),
            "mean_bps": float(sel_oos.mean() * 1e4) if len(sel_oos) else 0.0,
            "win_rate": float((sel_oos > 0).mean()) if len(sel_oos) else 0.0,
        }

    # ----- §6 mini gates on primary variant -----
    primary = portfolio_metrics[primary_v]
    gates = {
        "G1_OOS_Sharpe_gt_0.5":        primary["OOS_sharpe"] > 0.5,
        "G2_OOS_MaxDD_gt_-0.30":       primary["OOS_max_dd"] > -0.30,
        "G3_BlockBoot_CI95_low_gt_0":  primary_ci[0] > 0,
        "G4_Permutation_p_lt_0.05":    perm_primary["p_value"] < 0.05,
        "G5_DSR_gt_0.95":              ((dsr_results[primary_v] if not math.isnan(dsr_results[primary_v]) else 0) > 0.95),
        "G6_CostStress_high_OOS_sr_gt_0.3": cost_stress["high"]["OOS_sharpe"] > 0.3,
        "G7_WF_majority_pos":          (sum(1 for f in wf if f["sharpe"] > 0) >= 3),
    }
    n_pass = sum(gates.values())
    verdict = "ACCEPT" if n_pass >= 6 else "CONDITIONAL" if n_pass >= 4 else "REJECT"

    # ----- save curves -----
    curves = {v: equity_curve(portfolio_curves[v]) for v in portfolio_curves}
    with open(OUT_CURVES, "w") as f:
        json.dump(curves, f, indent=2)

    result = {
        "wave": "K151",
        "title": "STATIC Hour-of-Day Bucket Strategy (K148 follow-up)",
        "as_of": pd.Timestamp.utcnow().isoformat(),
        "n_symbols_universe": len(SYMBOLS),
        "top15_liquid": top15,
        "pre_registered_buckets": {
            "long_hours_primary": sorted(LONG_HOURS_PRIMARY),
            "short_hours_primary": sorted(SHORT_HOURS_PRIMARY),
            "long_hours_strict": sorted(LONG_HOURS_STRICT),
            "short_hours_strict": sorted(SHORT_HOURS_STRICT),
            "flat_hours": [4, 16],
            "trend_filter_ema_length": EMA_LEN,
        },
        "params": {
            "taker_bps": TAKER_BPS,
            "slip_bps": SLIP_BPS,
            "cost_per_side": COST_PER_SIDE,
            "IS_frac": IS_FRAC,
        },
        "per_symbol": per_symbol_results,
        "portfolio": portfolio_metrics,
        "walk_forward_primary": wf,
        "permutation_primary": perm_primary,
        "DSR": dsr_results,
        "cost_stress": cost_stress,
        "per_hour_basket_FULL": per_hour_basket,
        "per_hour_basket_IS": per_hour_is,
        "per_hour_basket_OOS": per_hour_oos,
        "gates": gates,
        "n_gates_pass": n_pass,
        "verdict": verdict,
        "elapsed_sec": time.time() - t0,
    }
    with open(OUT_JSON, "w") as f:
        json.dump(result, f, indent=2, default=str)

    # ----- markdown -----
    md_lines = []
    md_lines.append("# Wave K151 — STATIC Hour-of-Day Bucket Strategy")
    md_lines.append("")
    md_lines.append(f"**as_of:** {result['as_of']}  ")
    md_lines.append(f"**universe:** {len(SYMBOLS)} symbols  ")
    md_lines.append(f"**top-15 liquid:** `{top15}`  ")
    md_lines.append(f"**pre-registered buckets:** "
                    f"LONG @ {sorted(LONG_HOURS_PRIMARY)}, SHORT @ {sorted(SHORT_HOURS_PRIMARY)}, "
                    f"FLAT @ [4, 16]  ")
    md_lines.append("")
    md_lines.append("## Per-Variant Portfolio Sharpe (top-15 equal-weight)")
    md_lines.append("")
    md_lines.append("| Variant | IS SR | OOS SR | OOS DD | OOS WR | FULL SR | FULL TotRet | Mean bps/4h | Exposure |")
    md_lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|")
    for v in ["V_LL_SS", "V_LL_only", "V_strict_LS", "V_combine_filter"]:
        m = portfolio_metrics[v]
        md_lines.append(
            f"| {v} | {m['IS_sharpe']:.2f} | {m['OOS_sharpe']:.2f} | "
            f"{m['OOS_max_dd']*100:.2f}% | {m['OOS_win_rate']*100:.1f}% | "
            f"{m['FULL_sharpe']:.2f} | {m['FULL_total_return']*100:.2f}% | "
            f"{m['mean_4h_ret_bps']:+.2f} | {m['exposure_overall']*100:.1f}% |"
        )
    md_lines.append("")
    md_lines.append(f"**Primary OOS Sharpe CI95** (block bootstrap, n=300): "
                    f"[{primary_ci[0]:.3f}, {primary_ci[1]:.3f}]")
    md_lines.append("")
    md_lines.append("## Per-Hour Realised Stats (top-15 equal-weight basket, full window)")
    md_lines.append("")
    md_lines.append("| Hour UTC | n | mean bps | std bps | win rate | t-stat | IS mean bps | OOS mean bps |")
    md_lines.append("|---:|---:|---:|---:|---:|---:|---:|---:|")
    for h in HOURS_OF_DAY:
        r = per_hour_basket[h]
        ri = per_hour_is[h]
        ro = per_hour_oos[h]
        md_lines.append(
            f"| {h:02d} | {r['n']} | {r['mean_bps']:+.2f} | {r.get('std_bps', 0):.2f} | "
            f"{r['win_rate']*100:.1f}% | {r['t_stat']:+.2f} | "
            f"{ri['mean_bps']:+.2f} | {ro['mean_bps']:+.2f} |"
        )
    md_lines.append("")
    md_lines.append("## Walk-Forward 4-Fold (primary V_LL_SS)")
    md_lines.append("")
    md_lines.append("| Fold | n_bars | Sharpe | MaxDD | mean bps/4h |")
    md_lines.append("|---:|---:|---:|---:|---:|")
    for f in wf:
        md_lines.append(
            f"| {f['fold']} | {f['n_bars']} | {f['sharpe']:.2f} | "
            f"{f['max_dd']*100:.2f}% | {f['mean_4h_ret_bps']:+.2f} |"
        )
    md_lines.append("")
    md_lines.append("## Permutation (V_LL_SS, hour-label shuffle, n=300)")
    md_lines.append("")
    md_lines.append(f"- base Sharpe = **{perm_primary['base_sharpe']:.3f}**  ")
    md_lines.append(f"- null mean   = {perm_primary['null_mean']:.3f}  ")
    md_lines.append(f"- null std    = {perm_primary['null_std']:.3f}  ")
    md_lines.append(f"- p-value     = **{perm_primary['p_value']:.4f}**  ")
    md_lines.append("")
    md_lines.append("## DSR (N_trials = 4)")
    md_lines.append("")
    md_lines.append("| Variant | OOS Sharpe | DSR |")
    md_lines.append("|---|---:|---:|")
    for v in portfolio_metrics:
        md_lines.append(f"| {v} | {portfolio_metrics[v]['OOS_sharpe']:.2f} | "
                        f"{dsr_results[v]:.4f} |")
    md_lines.append("")
    md_lines.append("## Cost Stress (V_LL_SS, ±50%)")
    md_lines.append("")
    md_lines.append("| Scenario | mult | OOS SR | OOS DD | FULL SR | FULL TotRet |")
    md_lines.append("|---|---:|---:|---:|---:|---:|")
    for name in ["low", "base", "high"]:
        c = cost_stress[name]
        md_lines.append(f"| {name} | x{c['mult']} | {c['OOS_sharpe']:.3f} | "
                        f"{c['OOS_max_dd']*100:.2f}% | {c['FULL_sharpe']:.3f} | "
                        f"{c['FULL_total_return']*100:.2f}% |")
    md_lines.append("")
    md_lines.append("## §6 Mini-Gates (primary = V_LL_SS)")
    md_lines.append("")
    for k, v_ in gates.items():
        md_lines.append(f"- {'PASS' if v_ else 'FAIL'} — {k}")
    md_lines.append("")
    md_lines.append(f"**Gates passed:** {n_pass}/{len(gates)}  ")
    md_lines.append(f"**VERDICT:** **{verdict}**")
    md_lines.append("")
    md_lines.append("## Did STATIC (no rolling) save the K148 hypothesis?")
    md_lines.append("")
    k148_full_sr = -4.48  # K148 combined FULL Sharpe (from json)
    k148_oos_sr = -5.34
    k151_full_sr = portfolio_metrics[primary_v]["FULL_sharpe"]
    k151_oos_sr = portfolio_metrics[primary_v]["OOS_sharpe"]
    md_lines.append(f"- K148 (ROLLING combined): FULL SR = {k148_full_sr:+.2f}, OOS SR = {k148_oos_sr:+.2f}")
    md_lines.append(f"- K151 (STATIC primary):   FULL SR = {k151_full_sr:+.2f}, OOS SR = {k151_oos_sr:+.2f}")
    delta_full = k151_full_sr - k148_full_sr
    delta_oos = k151_oos_sr - k148_oos_sr
    md_lines.append(f"- Δ Sharpe (K151 − K148): FULL {delta_full:+.2f}, OOS {delta_oos:+.2f}")
    md_lines.append("")
    if k151_oos_sr > 0.5:
        md_lines.append("**YES — STATIC bucket saved the K148 hypothesis.** "
                        "Removing the rolling-adapter chase of recent outliers "
                        "recovers a meaningful OOS Sharpe.")
    elif k151_oos_sr > 0:
        md_lines.append("**PARTIAL — STATIC bucket recovers a positive OOS Sharpe but below the §6 acceptance threshold.** "
                        "The K148 finding is real in-sample but the edge is too small / unstable to deploy.")
    else:
        md_lines.append("**NO — even with STATIC, pre-registered buckets the strategy fails OOS.** "
                        "The K148 hourly cross-symbol pattern is a descriptive artefact that does not "
                        "translate into a tradeable, costed edge — confirming the rolling-adapter failure "
                        "was not the root cause.")
    md_lines.append("")
    md_lines.append(f"_Elapsed: {time.time() - t0:.1f}s_")

    with open(OUT_MD, "w") as f:
        f.write("\n".join(md_lines) + "\n")

    # ----- console summary -----
    print()
    print("=" * 72)
    print("PORTFOLIO METRICS (top-15 equal-weight)")
    for v in ["V_LL_SS", "V_LL_only", "V_strict_LS", "V_combine_filter"]:
        m = portfolio_metrics[v]
        print(f"  {v:18s}  IS_SR={m['IS_sharpe']:+6.2f}  OOS_SR={m['OOS_sharpe']:+6.2f}  "
              f"OOS_DD={m['OOS_max_dd']*100:+6.2f}%  FULL_SR={m['FULL_sharpe']:+6.2f}  "
              f"FULL_totRet={m['FULL_total_return']*100:+6.2f}%")
    print()
    print(f"Primary OOS CI95: [{primary_ci[0]:.3f}, {primary_ci[1]:.3f}]")
    print(f"Permutation p:    {perm_primary['p_value']:.4f}")
    print(f"DSR primary:      {dsr_results[primary_v]:.4f}")
    print()
    print("Per-hour basket (FULL):")
    for h in HOURS_OF_DAY:
        r = per_hour_basket[h]
        print(f"  H={h:02d}  n={r['n']:4d}  mean_bps={r['mean_bps']:+6.2f}  "
              f"WR={r['win_rate']*100:5.1f}%  t={r['t_stat']:+5.2f}")
    print()
    print("GATES:")
    for k, v_ in gates.items():
        print(f"  {'PASS' if v_ else 'FAIL'}  {k}")
    print(f"\nVERDICT: {verdict}  ({n_pass}/{len(gates)} gates pass)")
    print(f"Elapsed: {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
