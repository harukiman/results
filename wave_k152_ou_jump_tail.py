"""
Wave K152 — Funding OU+Jump Tail Risk Timing (arxiv 2605.06405-inspired).

Hypothesis
----------
Funding rate behaviour can be approximated by an Ornstein-Uhlenbeck mean-reverting
process plus heavy-tailed jumps.  A large jump (|z|>2.5) is an instantaneous
"crowdedness" / stress signal: leverage is being violently pulled out of one side
of the book, which historically precedes broader risk-off in spot.

Pre-registered method (simplified — no full MLE fit, just OU-style standardisation)
-----------------------------------------------------------------------------------
Per symbol per 8h funding event:
  1. mu_t  = rolling 30d mean  (90 events) of funding_rate
  2. sd_t  = rolling 30d stdev (90 events) of funding_rate
  3. z_t   = (funding_rate_t - mu_t) / sd_t
  4. lag by 1 event (use z evaluated at t-1 to act at open of bar t)

Jump detection (per symbol per event):  is_jump_t = (|z_{t-1}| > 2.5)

Market-wide stress signal at time t:
  k_t = number of symbols with is_jump_t = True   (out of 15)

Position rule (V_z25_3sym, primary):
  - enter SHORT BTC+ETH equal basket  when k_t >= 3
  - hold while k_t >= 1
  - flat when k_t == 0
  - hard max-hold = 7 days (21 events) from entry

Variants:
  - V_z25_3sym : 2.5 sigma, 3 sym threshold  (PRIMARY)
  - V_z20_3sym : 2.0 sigma, 3 sym threshold  (looser)
  - V_z25_5sym : 2.5 sigma, 5 sym threshold  (stricter)
  - V_z25_long : 2.5 sigma, 3 sym, sign reversed (contrarian)

Cost: 0.07% per side per leg (taker+slip) — applied per leg (BTC + ETH = 2 legs).

Backtest & audit
----------------
- 730d window, IS 70 / OOS 30
- Walk-forward 4-fold
- Permutation n=300 (shuffle jump-event timestamps)
- Block bootstrap n=300 on OOS
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
OUT_PY = "/Users/nekonaomichi/crypto-lab/wave_k152_ou_jump_tail.py"
OUT_JSON = "/Users/nekonaomichi/crypto-lab/wave_k152_ou_jump_tail.json"
OUT_CURVES = "/Users/nekonaomichi/crypto-lab/wave_k152_curves.json"
OUT_MD = "/Users/nekonaomichi/crypto-lab/wave_k152_ou_jump_tail.md"

# Funding cadence = 8h ; one event = 8h
EVENTS_PER_DAY = 3
ANNUALIZER = EVENTS_PER_DAY * 365  # 1095

# Rolling window for OU mu/sd
ROLL_LEN = 90  # 30 days * 3 events/day

IS_FRAC = 0.70

# Costs
TAKER_BPS = 4.0
SLIP_BPS = 3.0
COST_PER_SIDE = (TAKER_BPS + SLIP_BPS) / 1e4  # 0.07%

# Hold logic
MAX_HOLD_EVENTS = 21  # 7 days * 3 events/day

# Pre-registered FR universe: 15 most liquid 8h-funding symbols
FR_UNIVERSE_15 = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
    "DOGEUSDT", "ADAUSDT", "AVAXUSDT", "LINKUSDT", "DOTUSDT",
    "SUIUSDT", "NEARUSDT", "APTUSDT", "OPUSDT", "ARBUSDT",
]

# Trade legs (hedge basket)
TRADE_LEGS = ["BTCUSDT", "ETHUSDT"]


# ---------- loaders ----------
def load_funding(sym: str) -> pd.DataFrame:
    fp = f"{CACHE}/bybit_fr_{sym}_730d.parquet"
    df = pd.read_parquet(fp)
    df = df.sort_values("timestamp").reset_index(drop=True)
    df["fr"] = df["funding_rate"].astype(float)
    df["ts"] = pd.to_datetime(df["timestamp"])
    return df[["ts", "fr"]]


def load_price_4h(sym: str) -> pd.DataFrame:
    fp = f"{CACHE}/{sym}_4h_730d.parquet"
    df = pd.read_parquet(fp)[["open_time", "close"]].rename(columns={"open_time": "ts"})
    df = df.sort_values("ts").reset_index(drop=True)
    df["close"] = df["close"].astype(float)
    return df


def align_price_to_funding(price_df: pd.DataFrame, funding_ts: pd.Series) -> pd.Series:
    """For each 8h funding timestamp t, return the price close that prevailed at t.
    Funding events fall on 00, 08, 16 UTC; 4h bars exist at all those hours,
    so we take the close of the 4h bar starting at t (which closes at t+4h).
    We use OPEN-equivalent close == previous bar close to avoid look-ahead:
    actually we use the close of the bar whose open is exactly t (i.e. the close
    of the 4h period [t, t+4h)).  This means the price at t+4h.
    For pnl we use the close-to-close pct change of consecutive funding events.
    """
    p = price_df.set_index("ts")["close"]
    # Reindex onto funding timestamps; ffill in case of missing intermediate bars
    return p.reindex(funding_ts).ffill()


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


def block_bootstrap_sharpe(ret: np.ndarray, block: int = 12, n: int = 300, seed: int = 7) -> Tuple[float, float]:
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


# ---------- signal construction ----------
def build_z_panel(syms: List[str]) -> Tuple[pd.DataFrame, Dict[str, pd.DataFrame]]:
    """Return DataFrame indexed by ts, columns = symbols, values = lag-1 z-score."""
    raw: Dict[str, pd.DataFrame] = {}
    z_frames: Dict[str, pd.Series] = {}
    for sym in syms:
        df = load_funding(sym)
        mu = df["fr"].rolling(ROLL_LEN, min_periods=ROLL_LEN).mean()
        sd = df["fr"].rolling(ROLL_LEN, min_periods=ROLL_LEN).std()
        z = (df["fr"] - mu) / sd
        z_lag = z.shift(1)  # avoid look-ahead
        df["mu"] = mu
        df["sd"] = sd
        df["z"] = z
        df["z_lag"] = z_lag
        raw[sym] = df
        z_frames[sym] = pd.Series(z_lag.values, index=df["ts"], name=sym)
    panel = pd.concat(z_frames.values(), axis=1).sort_index()
    return panel, raw


def derive_signal_series(z_panel: pd.DataFrame,
                          z_thresh: float, k_thresh: int,
                          sign: int = -1,
                          max_hold: int = MAX_HOLD_EVENTS) -> Tuple[pd.Series, pd.Series, pd.DataFrame]:
    """Generate per-event basket position {-1, 0, +1} with k_t state machine.

    sign = -1 → SHORT basket on stress (default).
    sign = +1 → LONG  basket on stress (contrarian).

    Returns (pos_series, k_series, jump_matrix).
    """
    jump = (z_panel.abs() > z_thresh).fillna(False)
    k = jump.sum(axis=1)
    pos = np.zeros(len(k), dtype=float)
    in_pos = False
    hold = 0
    for i, kv in enumerate(k.values):
        if not in_pos:
            if kv >= k_thresh:
                in_pos = True
                hold = 1
                pos[i] = sign
            else:
                pos[i] = 0.0
        else:
            hold += 1
            if kv == 0 or hold > max_hold:
                in_pos = False
                hold = 0
                pos[i] = 0.0
            else:
                pos[i] = sign
    pos_s = pd.Series(pos, index=k.index, name="pos")
    return pos_s, k.rename("k"), jump


def basket_returns_8h(leg_syms: List[str], event_ts: pd.DatetimeIndex) -> pd.Series:
    """Equal-weight basket (BTC+ETH) close-to-close pct returns sampled at 8h funding events."""
    legs = []
    for s in leg_syms:
        p = load_price_4h(s)
        ps = align_price_to_funding(p, event_ts)
        r = ps.pct_change()
        legs.append(r.rename(s))
    df = pd.concat(legs, axis=1).sort_index().fillna(0.0)
    return df.mean(axis=1).rename("basket_ret_8h")


def apply_positions(pos: pd.Series, basket_ret: pd.Series,
                    cost_mult: float = 1.0, n_legs: int = len(TRADE_LEGS)) -> pd.DataFrame:
    df = pd.DataFrame({"pos": pos.reindex(basket_ret.index).fillna(0.0),
                        "basket_ret": basket_ret})
    df["gross_ret"] = df["pos"] * df["basket_ret"]
    # turnover in basket units; each unit-change requires entering/exiting n_legs legs
    turns = np.abs(np.diff(np.concatenate([[0.0], df["pos"].values])))
    df["cost"] = turns * COST_PER_SIDE * n_legs * cost_mult
    df["net_ret"] = df["gross_ret"] - df["cost"]
    return df


# ---------- pipeline ----------
def slice_metrics(arr: np.ndarray, exposure: np.ndarray | None = None) -> Dict:
    r = np.asarray(arr, dtype=float)
    out = {
        "sharpe": sharpe(r),
        "max_dd": max_dd(r),
        "win_rate": win_rate(r),
        "n_bars": int(len(r)),
        "total_return": float((1 + pd.Series(r).fillna(0)).prod() - 1),
        "mean_8h_ret_bps": float(np.nan_to_num(r, nan=0.0).mean() * 1e4),
    }
    if exposure is not None:
        out["exposure"] = float(np.mean(exposure != 0)) if len(exposure) else 0.0
    return out


def permutation_jump_shuffle(z_panel: pd.DataFrame, basket_ret: pd.Series,
                              base_sharpe_val: float, z_thresh: float, k_thresh: int,
                              sign: int, n: int = 300, seed: int = 42) -> Dict:
    """Null: the *timing* of the jump events is uninformative.  Procedure: for
    each symbol, randomly permute the time index of its z-score series (so the
    marginal jump-event rate is preserved per symbol, but timing is randomised).
    Then recompute pos and Sharpe.
    """
    rng = np.random.default_rng(seed)
    cols = list(z_panel.columns)
    z_vals = z_panel.values.copy()
    n_obs = len(z_panel)
    ts_index = z_panel.index
    base_ret_aligned = basket_ret.reindex(ts_index).fillna(0.0).values
    null_sharpes = np.empty(n, dtype=float)
    for i in range(n):
        z_shuf = np.empty_like(z_vals)
        for j in range(len(cols)):
            perm = rng.permutation(n_obs)
            z_shuf[:, j] = z_vals[perm, j]
        z_df = pd.DataFrame(z_shuf, index=ts_index, columns=cols)
        pos, _, _ = derive_signal_series(z_df, z_thresh, k_thresh, sign)
        pos_arr = pos.values
        turns = np.abs(np.diff(np.concatenate([[0.0], pos_arr])))
        cost = turns * COST_PER_SIDE * len(TRADE_LEGS)
        net = pos_arr * base_ret_aligned - cost
        null_sharpes[i] = sharpe(net)
    p = float((null_sharpes >= base_sharpe_val).mean())
    return {
        "base_sharpe": float(base_sharpe_val),
        "null_mean": float(null_sharpes.mean()),
        "null_std": float(null_sharpes.std()),
        "p_value": p,
        "n": n,
    }


def equity_curve(returns: pd.Series, downsample: int = 3) -> List[Dict]:
    eq = (1 + returns.fillna(0)).cumprod()
    sel = eq.iloc[::downsample]
    return [{"ts": str(ts), "eq": float(v)} for ts, v in sel.items()]


# ---------- main ----------
def main():
    t0 = time.time()
    print("=" * 72)
    print(f"Wave K152 — Funding OU+Jump Tail Risk Timing — {len(FR_UNIVERSE_15)} FR symbols")
    print("=" * 72)

    # ----- build z-panel -----
    z_panel, raw = build_z_panel(FR_UNIVERSE_15)
    print(f"z-panel shape: {z_panel.shape}")
    print(f"z-panel range: {z_panel.index.min()} -> {z_panel.index.max()}")
    valid = (~z_panel.isna()).sum(axis=1)
    valid_mask = valid == len(FR_UNIVERSE_15)
    first_valid = valid_mask.idxmax() if valid_mask.any() else z_panel.index[0]
    print(f"First fully-populated row: {first_valid}")

    # Trim to first fully-populated row to avoid OU-warmup bias
    z_panel = z_panel.loc[first_valid:].copy()
    print(f"After warmup trim: {z_panel.shape}")

    # ----- basket returns (BTC+ETH) at 8h funding cadence -----
    basket_ret = basket_returns_8h(TRADE_LEGS, z_panel.index)
    print(f"Basket return series: n={len(basket_ret)}  total={(1+basket_ret).prod()-1:+.2%}")

    # ----- variants -----
    variants = {
        "V_z25_3sym":  {"z": 2.5, "k": 3, "sign": -1},   # PRIMARY
        "V_z20_3sym":  {"z": 2.0, "k": 3, "sign": -1},
        "V_z25_5sym":  {"z": 2.5, "k": 5, "sign": -1},
        "V_z25_long":  {"z": 2.5, "k": 3, "sign": +1},   # contrarian
    }
    primary_v = "V_z25_3sym"

    portfolio_curves: Dict[str, pd.Series] = {}
    portfolio_metrics: Dict[str, Dict] = {}
    pos_series_by_v: Dict[str, pd.Series] = {}
    k_series_by_v: Dict[str, pd.Series] = {}

    for vname, params in variants.items():
        pos, k_ser, _jump = derive_signal_series(
            z_panel, params["z"], params["k"], params["sign"]
        )
        run = apply_positions(pos, basket_ret)
        pos_series_by_v[vname] = pos
        k_series_by_v[vname] = k_ser
        port = run["net_ret"]
        portfolio_curves[vname] = port
        arr = port.values
        n = len(arr)
        cut = int(n * IS_FRAC)
        pos_arr = run["pos"].values
        m = {
            "n_bars": int(n),
            "z_thresh": params["z"],
            "k_thresh": params["k"],
            "sign": params["sign"],
            "IS_sharpe": sharpe(arr[:cut]),
            "OOS_sharpe": sharpe(arr[cut:]),
            "OOS_max_dd": max_dd(arr[cut:]),
            "OOS_win_rate": win_rate(arr[cut:]),
            "OOS_total_return": float((1 + pd.Series(arr[cut:]).fillna(0)).prod() - 1),
            "FULL_sharpe": sharpe(arr),
            "FULL_max_dd": max_dd(arr),
            "FULL_total_return": float((1 + pd.Series(arr).fillna(0)).prod() - 1),
            "mean_8h_ret_bps": float(np.nan_to_num(arr, nan=0.0).mean() * 1e4),
            "exposure_overall": float((pos_arr != 0).mean()),
            "n_trades": int((np.diff(np.concatenate([[0.0], pos_arr])) != 0).sum()),
        }
        portfolio_metrics[vname] = m
        print(f"  {vname:14s}  IS_SR={m['IS_sharpe']:+5.2f}  OOS_SR={m['OOS_sharpe']:+5.2f}  "
              f"FULL_SR={m['FULL_sharpe']:+5.2f}  exposure={m['exposure_overall']*100:5.1f}%  "
              f"trades={m['n_trades']}")

    # ----- stress event frequency -----
    z_thresh_pri = variants[primary_v]["z"]
    jump_pri = (z_panel.abs() > z_thresh_pri).fillna(False)
    k_pri = jump_pri.sum(axis=1)
    stress_event_freq = {
        "z_thresh": z_thresh_pri,
        "n_events": int(len(k_pri)),
        "frac_with_any_jump": float((k_pri >= 1).mean()),
        "frac_with_3plus_jump": float((k_pri >= 3).mean()),
        "frac_with_5plus_jump": float((k_pri >= 5).mean()),
        "mean_k": float(k_pri.mean()),
        "max_k": int(k_pri.max()),
        "n_stress_entries_primary": int(((k_pri >= 3) & (pos_series_by_v[primary_v].shift(1).fillna(0) == 0)).sum()),
    }
    print(f"\nStress event freq (z>{z_thresh_pri}): any={stress_event_freq['frac_with_any_jump']*100:.2f}%  "
          f"k>=3: {stress_event_freq['frac_with_3plus_jump']*100:.2f}%  "
          f"k>=5: {stress_event_freq['frac_with_5plus_jump']*100:.2f}%  "
          f"mean_k={stress_event_freq['mean_k']:.3f}  max_k={stress_event_freq['max_k']}")

    # also tabulate per-symbol jump-event count (z>2.5)
    per_symbol_jump_count = {
        sym: int(((z_panel[sym].abs() > z_thresh_pri)).sum())
        for sym in FR_UNIVERSE_15
    }

    # ----- walk-forward 4-fold on primary -----
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
            "mean_8h_ret_bps": float(np.nan_to_num(sub, nan=0.0).mean() * 1e4),
        })

    # ----- block bootstrap on OOS primary -----
    cut = int(n * IS_FRAC)
    primary_ci = block_bootstrap_sharpe(arr_primary[cut:], block=12, n=300)
    portfolio_metrics[primary_v]["OOS_sharpe_CI95"] = primary_ci

    # ----- permutation test -----
    print("\nPermutation test (jump-time shuffle, n=300)... ", end="", flush=True)
    perm_primary = permutation_jump_shuffle(
        z_panel, basket_ret,
        portfolio_metrics[primary_v]["FULL_sharpe"],
        variants[primary_v]["z"], variants[primary_v]["k"], variants[primary_v]["sign"],
        n=300,
    )
    print(f"base={perm_primary['base_sharpe']:.3f}  null_mean={perm_primary['null_mean']:.3f}  "
          f"p={perm_primary['p_value']:.4f}")

    # ----- DSR (N_trials = 4) -----
    n_oos = n - cut
    dsr_results = {v: dsr(portfolio_metrics[v]["OOS_sharpe"], n_oos, n_trials=4)
                   for v in portfolio_metrics}

    # ----- cost stress on primary -----
    cost_stress = {}
    pos_pri = pos_series_by_v[primary_v]
    for mult, name in [(0.5, "low"), (1.0, "base"), (1.5, "high")]:
        run_cs = apply_positions(pos_pri, basket_ret, cost_mult=mult)
        arr_cs = run_cs["net_ret"].values
        n_cs = len(arr_cs)
        cut_cs = int(n_cs * IS_FRAC)
        cost_stress[name] = {
            "mult": mult,
            "OOS_sharpe": sharpe(arr_cs[cut_cs:]),
            "OOS_max_dd": max_dd(arr_cs[cut_cs:]),
            "FULL_sharpe": sharpe(arr_cs),
            "FULL_total_return": float((1 + pd.Series(arr_cs).fillna(0)).prod() - 1),
        }
        print(f"  cost {name:5s} (x{mult}): OOS_SR={cost_stress[name]['OOS_sharpe']:+.3f}  "
              f"FULL_SR={cost_stress[name]['FULL_sharpe']:+.3f}  "
              f"DD={cost_stress[name]['OOS_max_dd']*100:+.2f}%")

    # ----- §6 mini gates on primary -----
    primary = portfolio_metrics[primary_v]
    gates = {
        "G1_OOS_Sharpe_gt_0.5":        primary["OOS_sharpe"] > 0.5,
        "G2_OOS_MaxDD_gt_-0.30":       primary["OOS_max_dd"] > -0.30,
        "G3_BlockBoot_CI95_low_gt_0":  primary_ci[0] > 0,
        "G4_Permutation_p_lt_0.05":    perm_primary["p_value"] < 0.05,
        "G5_DSR_gt_0.95":              (not math.isnan(dsr_results[primary_v])) and (dsr_results[primary_v] > 0.95),
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
        "wave": "K152",
        "title": "Funding OU+Jump Tail Risk Timing (arxiv 2605.06405)",
        "as_of": pd.Timestamp.utcnow().isoformat(),
        "universe_fr": FR_UNIVERSE_15,
        "trade_legs": TRADE_LEGS,
        "params": {
            "roll_len_events": ROLL_LEN,
            "roll_len_days": ROLL_LEN / EVENTS_PER_DAY,
            "max_hold_events": MAX_HOLD_EVENTS,
            "max_hold_days": MAX_HOLD_EVENTS / EVENTS_PER_DAY,
            "taker_bps": TAKER_BPS,
            "slip_bps": SLIP_BPS,
            "cost_per_side": COST_PER_SIDE,
            "n_legs_per_basket": len(TRADE_LEGS),
            "IS_frac": IS_FRAC,
            "annualizer": ANNUALIZER,
        },
        "stress_event_frequency": stress_event_freq,
        "per_symbol_jump_count_z2p5": per_symbol_jump_count,
        "variants": {v: variants[v] for v in variants},
        "portfolio": portfolio_metrics,
        "walk_forward_primary": wf,
        "permutation_primary": perm_primary,
        "DSR": dsr_results,
        "cost_stress_primary": cost_stress,
        "gates": gates,
        "n_gates_pass": n_pass,
        "verdict": verdict,
        "elapsed_sec": time.time() - t0,
    }
    with open(OUT_JSON, "w") as f:
        json.dump(result, f, indent=2, default=str)

    # ----- markdown -----
    md_lines = []
    md_lines.append("# Wave K152 — Funding OU+Jump Tail Risk Timing")
    md_lines.append("")
    md_lines.append(f"**as_of:** {result['as_of']}  ")
    md_lines.append(f"**FR universe (15):** `{FR_UNIVERSE_15}`  ")
    md_lines.append(f"**hedge basket legs:** `{TRADE_LEGS}` (equal weight)  ")
    md_lines.append(f"**OU rolling window:** {ROLL_LEN} events ({ROLL_LEN/EVENTS_PER_DAY:.0f}d)  ")
    md_lines.append(f"**funding cadence:** 8h ({EVENTS_PER_DAY}/day, ann={ANNUALIZER})  ")
    md_lines.append(f"**max hold:** {MAX_HOLD_EVENTS} events ({MAX_HOLD_EVENTS/EVENTS_PER_DAY:.0f}d)  ")
    md_lines.append("")
    md_lines.append("## Stress event frequency (z > 2.5)")
    md_lines.append("")
    md_lines.append(f"- total events (post-warmup):   **{stress_event_freq['n_events']}**  ")
    md_lines.append(f"- fraction with any sym jump:   {stress_event_freq['frac_with_any_jump']*100:.2f}%  ")
    md_lines.append(f"- fraction with k>=3 stress:    **{stress_event_freq['frac_with_3plus_jump']*100:.2f}%**  ")
    md_lines.append(f"- fraction with k>=5 stress:    {stress_event_freq['frac_with_5plus_jump']*100:.2f}%  ")
    md_lines.append(f"- mean concurrent jumps (k):    {stress_event_freq['mean_k']:.3f}  ")
    md_lines.append(f"- max concurrent jumps:         {stress_event_freq['max_k']}  ")
    md_lines.append(f"- primary stress entries:       {stress_event_freq['n_stress_entries_primary']}  ")
    md_lines.append("")
    md_lines.append("### Per-symbol jump count (|z|>2.5)")
    md_lines.append("")
    md_lines.append("| Symbol | Jump events |")
    md_lines.append("|---|---:|")
    for s in FR_UNIVERSE_15:
        md_lines.append(f"| {s} | {per_symbol_jump_count[s]} |")
    md_lines.append("")
    md_lines.append("## Per-Variant Portfolio Sharpe (BTC+ETH equal-weight basket)")
    md_lines.append("")
    md_lines.append("| Variant | z | k | sign | IS SR | OOS SR | OOS DD | OOS WR | FULL SR | TotRet | Exp | Trades |")
    md_lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for v in ["V_z25_3sym", "V_z20_3sym", "V_z25_5sym", "V_z25_long"]:
        m = portfolio_metrics[v]
        md_lines.append(
            f"| {v} | {m['z_thresh']} | {m['k_thresh']} | {m['sign']:+d} | "
            f"{m['IS_sharpe']:+.2f} | {m['OOS_sharpe']:+.2f} | "
            f"{m['OOS_max_dd']*100:.2f}% | {m['OOS_win_rate']*100:.1f}% | "
            f"{m['FULL_sharpe']:+.2f} | {m['FULL_total_return']*100:+.2f}% | "
            f"{m['exposure_overall']*100:.1f}% | {m['n_trades']} |"
        )
    md_lines.append("")
    md_lines.append(f"**Primary OOS Sharpe CI95** (block bootstrap, n=300): "
                    f"[{primary_ci[0]:.3f}, {primary_ci[1]:.3f}]")
    md_lines.append("")
    md_lines.append("## Walk-Forward 4-Fold (primary V_z25_3sym)")
    md_lines.append("")
    md_lines.append("| Fold | n_bars | Sharpe | MaxDD | mean bps/8h |")
    md_lines.append("|---:|---:|---:|---:|---:|")
    for f in wf:
        md_lines.append(
            f"| {f['fold']} | {f['n_bars']} | {f['sharpe']:+.2f} | "
            f"{f['max_dd']*100:.2f}% | {f['mean_8h_ret_bps']:+.2f} |"
        )
    md_lines.append("")
    md_lines.append("## Permutation (V_z25_3sym, per-symbol z-time shuffle, n=300)")
    md_lines.append("")
    md_lines.append(f"- base Sharpe = **{perm_primary['base_sharpe']:+.3f}**  ")
    md_lines.append(f"- null mean   = {perm_primary['null_mean']:+.3f}  ")
    md_lines.append(f"- null std    = {perm_primary['null_std']:.3f}  ")
    md_lines.append(f"- p-value     = **{perm_primary['p_value']:.4f}**  ")
    md_lines.append("")
    md_lines.append("## DSR (N_trials = 4)")
    md_lines.append("")
    md_lines.append("| Variant | OOS Sharpe | DSR |")
    md_lines.append("|---|---:|---:|")
    for v in portfolio_metrics:
        dv = dsr_results[v]
        md_lines.append(f"| {v} | {portfolio_metrics[v]['OOS_sharpe']:+.2f} | "
                        f"{'nan' if math.isnan(dv) else f'{dv:.4f}'} |")
    md_lines.append("")
    md_lines.append("## Cost Stress (V_z25_3sym, ±50%)")
    md_lines.append("")
    md_lines.append("| Scenario | mult | OOS SR | OOS DD | FULL SR | FULL TotRet |")
    md_lines.append("|---|---:|---:|---:|---:|---:|")
    for name in ["low", "base", "high"]:
        c = cost_stress[name]
        md_lines.append(f"| {name} | x{c['mult']} | {c['OOS_sharpe']:+.3f} | "
                        f"{c['OOS_max_dd']*100:.2f}% | {c['FULL_sharpe']:+.3f} | "
                        f"{c['FULL_total_return']*100:+.2f}% |")
    md_lines.append("")
    md_lines.append("## §6 Mini-Gates (primary = V_z25_3sym)")
    md_lines.append("")
    for k_, v_ in gates.items():
        md_lines.append(f"- {'PASS' if v_ else 'FAIL'} — {k_}")
    md_lines.append("")
    md_lines.append(f"**Gates passed:** {n_pass}/{len(gates)}  ")
    md_lines.append(f"**VERDICT:** **{verdict}**")
    md_lines.append("")
    md_lines.append("## Verdict narrative")
    md_lines.append("")
    pri = portfolio_metrics[primary_v]
    if verdict == "ACCEPT":
        md_lines.append(
            f"The OU+jump tail-risk timing hypothesis **survives audit**.  "
            f"Stress events (k>=3 sym with |z|>2.5) occur in "
            f"{stress_event_freq['frac_with_3plus_jump']*100:.2f}% of 8h bars, and shorting "
            f"the BTC+ETH basket while stress persists produces OOS Sharpe "
            f"{pri['OOS_sharpe']:+.2f} with bootstrap CI95 [{primary_ci[0]:.2f}, {primary_ci[1]:.2f}] "
            f"and permutation p={perm_primary['p_value']:.3f}.  Cost stress at +50% retains "
            f"OOS Sharpe {cost_stress['high']['OOS_sharpe']:+.2f}."
        )
    elif verdict == "CONDITIONAL":
        md_lines.append(
            f"The hypothesis is **conditionally supported but not yet deployable**.  "
            f"OOS Sharpe = {pri['OOS_sharpe']:+.2f}, with "
            f"{n_pass}/{len(gates)} gates passing.  Stress events are rare "
            f"({stress_event_freq['frac_with_3plus_jump']*100:.2f}% of bars), so the OOS "
            f"sample includes only ~{int(stress_event_freq['frac_with_3plus_jump']*n_oos)} stress "
            f"observations — power may be the binding constraint.  The signed direction "
            f"is consistent with the OU+jump risk-off thesis but variance is too high to commit."
        )
    else:
        md_lines.append(
            f"The OU+jump tail-risk timing hypothesis **fails audit**.  "
            f"OOS Sharpe = {pri['OOS_sharpe']:+.2f}, OOS DD = {pri['OOS_max_dd']*100:.2f}%, "
            f"permutation p = {perm_primary['p_value']:.3f}.  "
            f"Either (a) k>=3 cross-sectional jump synchrony is too rare for statistical power "
            f"({stress_event_freq['frac_with_3plus_jump']*100:.2f}% of bars), "
            f"(b) the OU-deviation z-score does not, after costs, predict short-horizon basket "
            f"direction, or (c) the contrarian variant (V_z25_long) shows the true edge runs "
            f"opposite the hypothesised sign.  Compare V_z25_3sym vs V_z25_long to discriminate."
        )
    md_lines.append("")
    md_lines.append(f"_Elapsed: {time.time() - t0:.1f}s_")

    with open(OUT_MD, "w") as f:
        f.write("\n".join(md_lines) + "\n")

    # ----- console summary -----
    print()
    print("=" * 72)
    print("PORTFOLIO METRICS (BTC+ETH basket)")
    for v in ["V_z25_3sym", "V_z20_3sym", "V_z25_5sym", "V_z25_long"]:
        m = portfolio_metrics[v]
        print(f"  {v:14s}  IS_SR={m['IS_sharpe']:+6.2f}  OOS_SR={m['OOS_sharpe']:+6.2f}  "
              f"OOS_DD={m['OOS_max_dd']*100:+6.2f}%  FULL_SR={m['FULL_sharpe']:+6.2f}  "
              f"FULL_totRet={m['FULL_total_return']*100:+6.2f}%  trades={m['n_trades']}")
    print()
    print(f"Primary OOS CI95: [{primary_ci[0]:.3f}, {primary_ci[1]:.3f}]")
    print(f"Permutation p:    {perm_primary['p_value']:.4f}")
    print(f"DSR primary:      {dsr_results[primary_v]}")
    print()
    print("GATES:")
    for k_, v_ in gates.items():
        print(f"  {'PASS' if v_ else 'FAIL'}  {k_}")
    print(f"\nVERDICT: {verdict}  ({n_pass}/{len(gates)} gates pass)")
    print(f"Elapsed: {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
