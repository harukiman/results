"""
Wave K162 — Stablecoin Velocity Trigger (R6-12)
================================================================================
Hypothesis (Visa Economic Empowerment / a16z framework)
  Stablecoin VELOCITY = transaction volume / market cap.  Velocity rose
  2.6x → 6x through 2024-25.  When velocity SPIKES (deviation from its own
  rolling baseline), it signals capital is rotating ON-CHAIN — the "Great
  Rotation" from idle stablecoin balances into crypto risk-on positioning.

  Distinction from K135:
    K135 used stablecoin SUPPLY Δ (net minted balance) as the trigger.
    K162 uses VELOCITY (turnover) — a different micro-structure quantity.
    Supply can grow while velocity falls (mint-and-park); velocity can
    spike while supply is flat (active deployment).  These are economically
    orthogonal even though both ride stablecoin data.

Data honesty
  DefiLlama does NOT expose a direct "stablecoin transaction volume"
  endpoint at the time of this run.  We construct the BEST PUBLIC PROXY:

    velocity_proxy  =  DEX_daily_volume_USD  /  stablecoin_total_mcap_USD

  Rationale:
    1.  Roughly 90 % of DEX trades have a stablecoin leg (USDT/USDC/DAI).
    2.  DefiLlama /overview/dexs gives aggregate cross-chain DEX volume
        with daily granularity, ~3,600 days of history.
    3.  Stablecoin market cap from /stablecoincharts/all (USDT+USDC+DAI),
        already cached in cache/k135_stable_history.parquet.

  This proxy MISSES:
    * CEX-internal stablecoin transfers (large but private).
    * Pure on-chain peer-to-peer USDT transfers (not via DEX router).
    * Layer-2 internal volume not aggregated by DefiLlama.

  But it CAPTURES:
    * The single most economically-meaningful channel of stablecoin
      deployment for crypto risk-on (DEX → token swaps).
    * Time-series resolution sufficient for daily signal generation.

  We label results with this caveat.  This is the most rigorous public
  proxy available without paid Chainalysis / Glassnode tier-2 access.

Method (pre-registered)
  1. Daily series:  dex_vol_t  and  stable_mcap_t  (USD).
  2. velocity_t   = dex_vol_t / stable_mcap_t              (dimensionless)
  3. vel_7d_t     = velocity_t.rolling(7).mean()
  4. Signals (state machines, lag-1 execution):
       V_p90_top
         vel_7d crosses ABOVE 90th-percentile (90d-rolling)  → LONG basket
         vel_7d crosses BELOW its 90-day MEDIAN              → EXIT
       V_zscore_2
         z = (vel_7d - 90d-mean) / 90d-std
         z >  +2   → LONG ; z < 0 → EXIT
       V_combo_inflow
         (V_p90_top long-state)  AND  (7d-sum stablecoin SUPPLY Δ > 0)
         → LONG  (both velocity AND inflow positive)
         exit on either condition flipping
  5. Basket: BTC, ETH, SOL, BNB, DOGE, AVAX, LINK (equal-weight,
     same universe as K135 for like-for-like comparison).
  6. Costs: 7 bps per side per leg.
  7. Max-hold 30 days hard cap (same as K135 for comparability).

Audit
  IS / OOS 70 / 30
  Walk-forward 4-fold on portfolio
  Permutation n=200 on portfolio signal (circular-shift; one-sided SR > 0)
  Block bootstrap n=300 on OOS portfolio
  DSR with N_trials = 3 variants × 7 syms + 3 portfolios = 24
  Cost stress ×0.5 / ×1.5

Output
  wave_k162_stable_velocity.py     (this file)
  wave_k162_stable_velocity.json   (full audit)
  wave_k162_curves.json            (equity curves)

Constraints
  Python 3.11, < 15 min, no paid APIs.
"""

from __future__ import annotations

import json
import math
import os
import time
import urllib.request
import warnings
from math import erf

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

CACHE = "/Users/nekonaomichi/crypto-lab/cache"
OUT_JSON = "/Users/nekonaomichi/crypto-lab/wave_k162_stable_velocity.json"
OUT_CURVES = "/Users/nekonaomichi/crypto-lab/wave_k162_curves.json"
DEFI_STABLE_CACHE = "/Users/nekonaomichi/crypto-lab/cache/k135_stable_history.parquet"
DEX_VOL_CACHE = "/Users/nekonaomichi/crypto-lab/cache/k162_dex_vol.parquet"

# ---------- universe ----------
SYMBOLS = ["BTC", "ETH", "DOGE", "SOL", "BNB", "AVAX", "LINK"]
PRIMARY = ["BTC", "ETH"]

# ---------- design constants ----------
PERIODS_PER_YEAR = 365
IS_FRAC = 0.70

TAKER_BPS = 4.0
SLIP_BPS = 3.0
COST_PER_SIDE = (TAKER_BPS + SLIP_BPS) / 1e4   # 0.07%

VEL_SMOOTH = 7        # 7d rolling mean of raw velocity
BASELINE_WIN = 90     # rolling baseline for percentile / z-score
INFLOW_WIN = 7        # rolling sum for stablecoin supply Δ
MAX_HOLD = 30
P_HIGH = 0.90         # top trigger
EXIT_MEDIAN = 0.50    # exit when vel drops below 90d median
Z_TRIG = 2.0

VARIANTS = ["V_p90_top", "V_zscore_2", "V_combo_inflow"]


# ---------- data ----------
def fetch_dex_volume(retries: int = 3) -> pd.DataFrame:
    """DefiLlama aggregate cross-chain DEX daily volume in USD."""
    url = "https://api.llama.fi/overview/dexs?excludeTotalDataChartBreakdown=true"
    last_err = None
    for _ in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=60) as r:
                data = json.loads(r.read())
            chart = data["totalDataChart"]
            rows = [(int(ts), float(v)) for ts, v in chart if v is not None]
            df = pd.DataFrame(rows, columns=["ts_unix", "dex_vol_usd"])
            df["date"] = pd.to_datetime(df["ts_unix"], unit="s").dt.normalize()
            df = df.drop(columns="ts_unix").drop_duplicates("date").set_index("date").sort_index()
            return df
        except Exception as e:
            last_err = e
            time.sleep(2)
    raise RuntimeError(f"DefiLlama DEX volume fetch failed: {last_err}")


def load_dex_volume() -> pd.DataFrame:
    if os.path.exists(DEX_VOL_CACHE):
        try:
            df = pd.read_parquet(DEX_VOL_CACHE)
            if (pd.Timestamp.utcnow().tz_localize(None) - df.index.max()).days < 3:
                print(f"  [cache] DEX vol cache (last={df.index.max().date()})")
                return df
        except Exception:
            pass
    print("  fetching DefiLlama DEX volume...")
    df = fetch_dex_volume()
    try:
        df.to_parquet(DEX_VOL_CACHE)
    except Exception:
        pass
    return df


def load_stable_mcap() -> pd.DataFrame:
    """Re-use K135 cache (already up-to-date)."""
    if not os.path.exists(DEFI_STABLE_CACHE):
        raise FileNotFoundError(
            f"missing {DEFI_STABLE_CACHE}; run K135 first to populate cache"
        )
    df = pd.read_parquet(DEFI_STABLE_CACHE)
    print(f"  [cache] stable mcap (last={df.index.max().date()})")
    return df


def load_close_panel() -> pd.DataFrame:
    frames = []
    for sym in SYMBOLS:
        path = None
        for d in (1200, 730, 365):
            p = f"{CACHE}/{sym}USDT_1d_{d}d.parquet"
            if os.path.exists(p):
                path = p
                break
        if path is None:
            raise FileNotFoundError(f"no daily parquet for {sym}")
        df = pd.read_parquet(path)[["open_time", "close"]].rename(
            columns={"open_time": "ts"}
        )
        df["ts"] = pd.to_datetime(df["ts"]).dt.normalize()
        df = df.sort_values("ts").drop_duplicates("ts").set_index("ts")
        df = df.rename(columns={"close": sym})
        frames.append(df.astype(float))
    panel = pd.concat(frames, axis=1).sort_index()
    return panel


# ---------- signals ----------
def build_signals(stable: pd.DataFrame, dex_vol: pd.DataFrame) -> pd.DataFrame:
    """Build all variant signal series indexed by date.

    Returns DataFrame with columns:
      velocity, vel_7d, p90, p50, z, inflow7,
      V_p90_top, V_zscore_2, V_combo_inflow (each ∈ {0, +1})
    """
    # align
    common = stable.index.intersection(dex_vol.index)
    s = stable.loc[common].copy()
    v = dex_vol.loc[common, "dex_vol_usd"]

    velocity = v / s["TOTAL"]
    vel_7d = velocity.rolling(VEL_SMOOTH).mean()

    # 90d rolling 90th percentile and median
    p90 = vel_7d.rolling(BASELINE_WIN).quantile(P_HIGH)
    p50 = vel_7d.rolling(BASELINE_WIN).quantile(EXIT_MEDIAN)

    # z-score
    mu = vel_7d.rolling(BASELINE_WIN).mean()
    sd = vel_7d.rolling(BASELINE_WIN).std()
    z = (vel_7d - mu) / sd

    # inflow proxy (K135 net 7d supply Δ)
    delta = s["TOTAL"].diff()
    inflow7 = delta.rolling(INFLOW_WIN).sum()

    n = len(s)

    # ---- V_p90_top ----
    sig_p = np.zeros(n)
    state = 0
    vel = vel_7d.values
    p90_v = p90.values
    p50_v = p50.values
    for i in range(1, n):
        if np.isnan(vel[i]) or np.isnan(p90_v[i]) or np.isnan(p50_v[i]):
            sig_p[i] = state
            continue
        if state == 0 and vel[i - 1] <= p90_v[i - 1] and vel[i] > p90_v[i]:
            state = 1
        elif state == 1 and vel[i - 1] >= p50_v[i - 1] and vel[i] < p50_v[i]:
            state = 0
        sig_p[i] = state

    # ---- V_zscore_2 ----
    sig_z = np.zeros(n)
    state = 0
    z_v = z.values
    for i in range(1, n):
        if np.isnan(z_v[i]):
            sig_z[i] = state
            continue
        if state == 0 and z_v[i] > Z_TRIG:
            state = 1
        elif state == 1 and z_v[i] < 0.0:
            state = 0
        sig_z[i] = state

    # ---- V_combo_inflow ----
    # both V_p90_top AND inflow7 > 0
    sig_c = np.zeros(n)
    state = 0
    inflow_v = inflow7.values
    for i in range(1, n):
        cond_p = sig_p[i] == 1
        cond_in = (not np.isnan(inflow_v[i])) and inflow_v[i] > 0
        if state == 0 and cond_p and cond_in:
            state = 1
        elif state == 1 and (not cond_p or not cond_in):
            state = 0
        sig_c[i] = state

    out = pd.DataFrame({
        "velocity": velocity,
        "vel_7d": vel_7d,
        "p90": p90,
        "p50": p50,
        "z": z,
        "inflow7": inflow7,
        "V_p90_top": sig_p,
        "V_zscore_2": sig_z,
        "V_combo_inflow": sig_c,
    }, index=s.index)
    return out


def apply_max_hold(sig: np.ndarray, max_hold: int) -> np.ndarray:
    out = sig.copy()
    hold = 0
    last_state = 0
    forced = False
    for i in range(len(out)):
        cur = out[i]
        if forced:
            if cur == 0:
                forced = False
                last_state = 0
                hold = 0
            elif cur != last_state:
                forced = False
                last_state = cur
                hold = 1
            else:
                out[i] = 0
                continue
        else:
            if cur == 0:
                last_state = 0
                hold = 0
            elif cur == last_state:
                hold += 1
                if hold > max_hold:
                    out[i] = 0
                    forced = True
            else:
                last_state = cur
                hold = 1
    return out


# ---------- pnl ----------
def per_symbol_pnl(price: pd.Series, position: pd.Series, cost_mult: float = 1.0) -> pd.DataFrame:
    ret = price.pct_change()
    pos_lag = position.shift(1).fillna(0.0)
    pnl_gross = pos_lag * ret
    turn = (position - position.shift(1).fillna(0.0)).abs()
    cost = turn * COST_PER_SIDE * cost_mult
    return pd.DataFrame({
        "ret": ret,
        "pos_lag": pos_lag,
        "pnl_gross": pnl_gross,
        "cost": cost,
        "pnl_net": pnl_gross - cost,
    })


def variant_portfolio(price_panel: pd.DataFrame, sig: pd.Series, cost_mult: float = 1.0) -> dict:
    pnl_by_sym = {}
    master_idx = price_panel.index
    for sym in price_panel.columns:
        df = pd.concat([price_panel[sym].rename("price"), sig.rename("pos")], axis=1).dropna()
        if len(df) < 30:
            continue
        pnl = per_symbol_pnl(df["price"], df["pos"], cost_mult=cost_mult)
        pnl = pnl.reindex(master_idx).fillna(0.0)
        pnl_by_sym[sym] = pnl
    pnl_net_concat = pd.concat({k: v["pnl_net"] for k, v in pnl_by_sym.items()}, axis=1)
    active_mask = price_panel.notna()[pnl_net_concat.columns]
    n_active = active_mask.sum(axis=1).clip(lower=1)
    port = (pnl_net_concat * active_mask).sum(axis=1) / n_active
    return {"per_symbol": pnl_by_sym, "portfolio": port}


# ---------- metrics ----------
def sharpe(returns, ppy: float = PERIODS_PER_YEAR) -> float:
    r = np.asarray(returns, dtype=float)
    r = r[~np.isnan(r)]
    if len(r) < 10 or r.std() == 0:
        return 0.0
    return float(r.mean() / r.std() * math.sqrt(ppy))


def max_dd(returns) -> float:
    r = np.asarray(returns, dtype=float)
    r = r[~np.isnan(r)]
    if len(r) == 0:
        return 0.0
    eq = (1 + r).cumprod()
    peak = np.maximum.accumulate(eq)
    return float(((eq - peak) / peak).min())


def win_rate(returns) -> float:
    r = np.asarray(returns, dtype=float)
    r = r[~np.isnan(r) & (r != 0)]
    if len(r) == 0:
        return 0.0
    return float((r > 0).mean())


def block_bootstrap_sharpe(ret: np.ndarray, block: int = 20, n: int = 300, seed: int = 7):
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
    return (float(np.percentile(samples, 2.5)), float(np.percentile(samples, 97.5)))


def dsr(sharpe_ann: float, n_obs: int, n_trials: int, ppy: float = PERIODS_PER_YEAR) -> float:
    if n_obs < 30 or n_trials < 1:
        return float("nan")
    sharpe_pb = sharpe_ann / math.sqrt(ppy)
    emc = 0.5772
    sn = math.sqrt(2 * math.log(max(n_trials, 2)))
    expected_max = sn - emc / sn
    sr_std = math.sqrt((1 + 0.5 * sharpe_pb ** 2) / n_obs)
    if sr_std == 0:
        return float("nan")
    z = (sharpe_pb - expected_max * sr_std) / sr_std
    return float(0.5 * (1 + erf(z / math.sqrt(2))))


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


def walk_forward_4fold(port_returns: pd.Series) -> list:
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


def permutation_test_signal(price_panel: pd.DataFrame, sig: pd.Series, n: int = 200, seed: int = 42) -> dict:
    rng = np.random.default_rng(seed)
    base = variant_portfolio(price_panel, sig)["portfolio"]
    base_sr = sharpe(base.values)
    sig_vals = sig.values
    n_len = len(sig_vals)
    null_srs = []
    for _ in range(n):
        shift = int(rng.integers(VEL_SMOOTH * 5, max(VEL_SMOOTH * 6, n_len - VEL_SMOOTH * 5)))
        perm = np.concatenate([sig_vals[shift:], sig_vals[:shift]])
        sig_perm = pd.Series(perm, index=sig.index)
        port_perm = variant_portfolio(price_panel, sig_perm)["portfolio"]
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


def equity_curve(returns: pd.Series, every: int = 1) -> list:
    eq = (1 + returns.fillna(0)).cumprod()
    return [{"ts": str(ts.date()), "eq": float(v)} for ts, v in eq.iloc[::every].items()]


# ---------- gates ----------
def evaluate_gates(metrics: dict, perm: dict, dsr_val: float) -> dict:
    oos = metrics["OOS"]
    is_ = metrics["IS"]
    boot_lo = metrics.get("OOS_sharpe_CI95", (0, 0))[0]
    gates = {
        "G1_OOS_sharpe_ge_1": oos["sharpe"] >= 1.0,
        "G2_OOS_maxdd_gt_-30%": oos["max_dd"] > -0.30,
        "G3_OOS_boot_lower_gt_0": boot_lo > 0.0,
        "G4_perm_p_lt_5%": perm["p_value"] < 0.05,
        "G5_DSR_gt_95%": (not math.isnan(dsr_val)) and dsr_val > 0.95,
        "G6_OOSdivIS_ge_0.5": (is_["sharpe"] > 0 and oos["sharpe"] / max(is_["sharpe"], 1e-9) >= 0.5)
                              or (is_["sharpe"] <= 0 and oos["sharpe"] > 0),
    }
    gates["passed"] = sum(bool(v) for v in gates.values())
    gates["total"] = len(gates) - 1
    return gates


# ---------- main ----------
def main():
    t0 = time.time()
    print("=" * 78)
    print("Wave K162 — Stablecoin Velocity Trigger (R6-12)")
    print("=" * 78)

    print("Loading stablecoin market cap (USDT+USDC+DAI)...")
    stable = load_stable_mcap()
    print(f"  range: {stable.index.min().date()} → {stable.index.max().date()}  n={len(stable)}")

    print("Loading DefiLlama DEX volume (proxy for stablecoin tx volume)...")
    dex = load_dex_volume()
    print(f"  range: {dex.index.min().date()} → {dex.index.max().date()}  n={len(dex)}")

    print("Loading price panel (daily close)...")
    panel = load_close_panel()
    print(f"  panel shape: {panel.shape}  range: {panel.index.min().date()} → {panel.index.max().date()}")

    print("Building signals...")
    sigs = build_signals(stable, dex)
    # describe velocity over time
    vel_desc = sigs["vel_7d"].describe()
    print(f"  velocity_7d:  mean={vel_desc['mean']:.4f}  median={vel_desc['50%']:.4f}  p90={sigs['vel_7d'].quantile(0.90):.4f}  max={vel_desc['max']:.4f}")

    common = sigs.index.intersection(panel.index)
    sigs = sigs.loc[common]
    panel = panel.loc[common]
    print(f"  intersection: {len(common)} days, {common.min().date()} → {common.max().date()}")

    # velocity stats by year
    vel_by_year = sigs["vel_7d"].dropna().groupby(sigs.index.year).agg(["mean", "median", "max"])
    print("\n  velocity_7d by year:")
    for yr, row in vel_by_year.iterrows():
        print(f"    {yr}: mean={row['mean']:.4f}  median={row['median']:.4f}  max={row['max']:.4f}")

    sig_cooked = {}
    for v in VARIANTS:
        raw = sigs[v].values.astype(float)
        cooked = apply_max_hold(raw, MAX_HOLD)
        sig_cooked[v] = pd.Series(cooked, index=sigs.index)

    n_full = len(panel)
    cut = int(n_full * IS_FRAC)

    results = {
        "meta": {
            "task": "Wave K162 Stablecoin Velocity Trigger",
            "data_source": "DefiLlama DEX volume (proxy) / stablecoincharts/all (USDT+USDC+DAI)",
            "velocity_proxy_caveat": (
                "DefiLlama does not expose direct stablecoin tx volume; "
                "we use DEX_vol/stable_mcap as the most defensible public proxy. "
                "Misses CEX-internal & pure P2P transfers; captures DEX swap velocity."
            ),
            "distinct_from_k135": (
                "K135 used supply Δ; K162 uses turnover. Economically orthogonal."
            ),
            "symbols": SYMBOLS,
            "primary": PRIMARY,
            "date_range": [str(common.min().date()), str(common.max().date())],
            "n_days": n_full,
            "IS_cut": cut,
            "cost_per_side_bps": (TAKER_BPS + SLIP_BPS),
            "vel_smooth_days": VEL_SMOOTH,
            "baseline_window_days": BASELINE_WIN,
            "max_hold_days": MAX_HOLD,
            "p_high": P_HIGH,
            "exit_pct": EXIT_MEDIAN,
            "z_trigger": Z_TRIG,
            "inflow_window_days": INFLOW_WIN,
            "variants": VARIANTS,
        },
        "velocity_stats": {
            "mean": float(vel_desc["mean"]),
            "median": float(vel_desc["50%"]),
            "p90": float(sigs["vel_7d"].quantile(0.90)),
            "max": float(vel_desc["max"]),
            "by_year": {int(yr): {"mean": float(row["mean"]),
                                   "median": float(row["median"]),
                                   "max": float(row["max"])}
                        for yr, row in vel_by_year.iterrows()},
        },
        "snapshot_last": {
            "date": str(sigs.index.max().date()),
            "velocity": float(sigs["velocity"].iloc[-1]) if not np.isnan(sigs["velocity"].iloc[-1]) else None,
            "vel_7d": float(sigs["vel_7d"].iloc[-1]) if not np.isnan(sigs["vel_7d"].iloc[-1]) else None,
            "p90_90d": float(sigs["p90"].iloc[-1]) if not np.isnan(sigs["p90"].iloc[-1]) else None,
            "z_90d": float(sigs["z"].iloc[-1]) if not np.isnan(sigs["z"].iloc[-1]) else None,
            "inflow7_usd": float(sigs["inflow7"].iloc[-1]) if not np.isnan(sigs["inflow7"].iloc[-1]) else None,
        },
        "variants": {},
    }

    curves = {}

    for v in VARIANTS:
        print(f"\n— variant {v} —")
        out = variant_portfolio(panel, sig_cooked[v])
        port = out["portfolio"]
        per_sym = {}
        for sym, pnl in out["per_symbol"].items():
            per_sym[sym] = {
                "IS": slice_metrics(pnl["pnl_net"], 0, cut),
                "OOS": slice_metrics(pnl["pnl_net"], cut, n_full),
                "FULL": slice_metrics(pnl["pnl_net"], 0, n_full),
                "n_trades_approx": int((pnl["pos_lag"].diff().abs() > 0).sum()),
                "time_in_market_pct": float((pnl["pos_lag"].abs() > 0).mean() * 100),
            }
        is_m = slice_metrics(port, 0, cut)
        oos_m = slice_metrics(port, cut, n_full)
        full_m = slice_metrics(port, 0, n_full)
        ci = block_bootstrap_sharpe(port.values[cut:], block=20, n=300)
        wf = walk_forward_4fold(port)
        port_lo = variant_portfolio(panel, sig_cooked[v], cost_mult=0.5)["portfolio"]
        port_hi = variant_portfolio(panel, sig_cooked[v], cost_mult=1.5)["portfolio"]
        cost_stress = {
            "cost_x0.5_OOS_sharpe": sharpe(port_lo.values[cut:]),
            "cost_x1.0_OOS_sharpe": oos_m["sharpe"],
            "cost_x1.5_OOS_sharpe": sharpe(port_hi.values[cut:]),
        }
        print(f"  running permutation (n=200)...")
        perm = permutation_test_signal(panel, sig_cooked[v], n=200, seed=162 + VARIANTS.index(v))
        n_trials = 3 * len(SYMBOLS) + 3
        dsr_val = dsr(oos_m["sharpe"], n_full - cut, n_trials)
        gates = evaluate_gates(
            {"IS": is_m, "OOS": oos_m, "FULL": full_m, "OOS_sharpe_CI95": ci},
            perm,
            dsr_val,
        )
        print(f"  IS sr={is_m['sharpe']:.2f}  OOS sr={oos_m['sharpe']:.2f}  perm_p={perm['p_value']:.3f}  DSR={dsr_val:.3f}  gates {gates['passed']}/{gates['total']}")

        results["variants"][v] = {
            "portfolio": {
                "IS": is_m,
                "OOS": oos_m,
                "FULL": full_m,
                "OOS_sharpe_CI95": ci,
                "walk_forward_4fold": wf,
                "cost_stress": cost_stress,
                "permutation": perm,
                "DSR": dsr_val,
                "n_trials_DSR": n_trials,
                "gates": gates,
                "time_in_market_pct": float((sig_cooked[v].abs() > 0).mean() * 100),
                "n_signal_flips": int((sig_cooked[v].diff().abs() > 0).sum()),
            },
            "per_symbol": per_sym,
        }
        curves[v] = equity_curve(port, every=1)
        for sym in PRIMARY:
            if sym in out["per_symbol"]:
                curves[f"{v}__{sym}"] = equity_curve(out["per_symbol"][sym]["pnl_net"], every=1)

    # signal tail
    tail = sigs[["velocity", "vel_7d", "p90", "z", "inflow7"] + VARIANTS].tail(60)
    results["signal_tail_60d"] = [
        {
            "date": str(idx.date()),
            "velocity": float(row["velocity"]) if not math.isnan(row["velocity"]) else None,
            "vel_7d": float(row["vel_7d"]) if not math.isnan(row["vel_7d"]) else None,
            "p90": float(row["p90"]) if not math.isnan(row["p90"]) else None,
            "z": float(row["z"]) if not math.isnan(row["z"]) else None,
            "inflow7_usd": float(row["inflow7"]) if not math.isnan(row["inflow7"]) else None,
            **{v: float(row[v]) for v in VARIANTS},
        }
        for idx, row in tail.iterrows()
    ]

    # k135 cross-comparison (load if exists)
    k135_path = "/Users/nekonaomichi/crypto-lab/wave_k135_stable_supply.json"
    k135_compare = {}
    if os.path.exists(k135_path):
        try:
            with open(k135_path) as f:
                k135 = json.load(f)
            k135_compare = {
                "k135_variants_OOS_sharpe": {
                    v: k135["variants"][v]["portfolio"]["OOS"]["sharpe"]
                    for v in k135.get("variants", {})
                },
                "k135_variants_gates_passed": {
                    v: k135["variants"][v]["portfolio"]["gates"]["passed"]
                    for v in k135.get("variants", {})
                },
                "k135_date_range": k135.get("meta", {}).get("date_range"),
            }
        except Exception as e:
            k135_compare = {"error": str(e)}
    results["k135_comparison"] = k135_compare

    results["elapsed_sec"] = time.time() - t0

    with open(OUT_JSON, "w") as f:
        json.dump(results, f, indent=2, default=str)
    with open(OUT_CURVES, "w") as f:
        json.dump(curves, f, indent=2, default=str)

    print(f"\nWrote: {OUT_JSON}")
    print(f"Wrote: {OUT_CURVES}")
    print(f"Elapsed: {results['elapsed_sec']:.1f}s")

    print("\n" + "=" * 78)
    print("VARIANT SUMMARY (portfolio)")
    print("=" * 78)
    print(f"{'variant':22s}  {'IS sr':>7s}  {'OOS sr':>7s}  {'OOS DD':>7s}  {'TIM%':>5s}  {'flips':>5s}  {'perm_p':>7s}  {'DSR':>6s}  {'gates':>6s}")
    for v in VARIANTS:
        p = results["variants"][v]["portfolio"]
        print(f"{v:22s}  {p['IS']['sharpe']:>7.2f}  {p['OOS']['sharpe']:>7.2f}  {p['OOS']['max_dd']:>7.2%}  {p['time_in_market_pct']:>5.1f}  {p['n_signal_flips']:>5d}  {p['permutation']['p_value']:>7.3f}  {p['DSR']:>6.3f}  {p['gates']['passed']:>2d}/{p['gates']['total']:<2d}")


if __name__ == "__main__":
    main()
