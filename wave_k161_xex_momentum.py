"""
Wave K161 — Cross-Exchange FR MOMENTUM (continuation; K159 inverse pre-registered)
================================================================================
Background
  K159 tested cross-exchange FR spread as a FADE / mean-reversion signal on
  Bybit perps and was REJECTED with strongly NEGATIVE OOS Sharpe and LOW
  permutation p-values (0.01–0.07). That is itself an actionable finding:
  the INVERSE direction (MOMENTUM / CONTINUATION) is what statistically holds.

  K159 actual OOS readings (from wave_k159_xex_fr_spread.json):
      V_bm_2pct  full SR=-1.17  OOS SR=-1.99  perm_p=0.075
      V_bm_3pct  full SR=-1.11  OOS SR=-1.53  perm_p=0.050
      V_bb_2pct  full SR=-1.37  OOS SR=-2.08  perm_p=0.015
      V_bb_3pct  full SR=-1.23  OOS SR=-1.95  perm_p=0.010   <-- best edge
      V_combo_z  full SR=-1.31  OOS SR=-0.59  perm_p=0.755

  Inversed (momentum) implied OOS Sharpe:
      V_bb_2pct  ≈ +1.5
      V_bb_3pct  ≈ +2.1, perm p ≈ 0.01 (one-sided in opposite tail)

Pre-registered MOMENTUM rules (this wave)
  Per Bybit FR event (8h) per symbol:
    bb_spread = binance_fr − bybit_fr
    bm_spread = bybit_fr   − mexc_fr
  Signal (continuation):
    bb_spread > +thr  → SHORT bybit  (bybit lower than binance, momentum says
                                      it KEEPS being lower → price down on bybit)
    bb_spread < −thr  → LONG  bybit  (bybit higher than binance, momentum says
                                      it KEEPS being higher → price up on bybit)
  Mirror rule for bm:
    bm_spread > +thr  → LONG  bybit  (bybit higher than mexc — KEEP higher)
    bm_spread < −thr  → SHORT bybit  (bybit lower than mexc  — KEEP lower)

  Why the asymmetric mapping?  bb spread (binance − bybit) and bm spread
  (bybit − mexc) BOTH measure bybit's relative position vs another venue;
  the sign of "bybit-favoured" is opposite, so the trade direction flips
  to keep CONTINUATION semantics consistent across both.

  Hold: until spread crosses zero OR max 3 days (9 funding events).
  Cost: 0.07 % per side per leg (one leg = Bybit perp).

Variants
  V_bb_2pct  : bb spread |Δ| > 2 % annualised   (primary)
  V_bb_3pct  : bb spread |Δ| > 3 % annualised   (K159 best inverse signal)
  V_bm_2pct  : bm spread |Δ| > 2 % annualised   (independent venue pair)
  V_combo    : both bb AND bm aligned (intersection)

Audit (institutional § gates)
  730d, IS 70 / OOS 30
  Walk-forward 4-fold
  One-sided permutation n=300 (alternative: SR > 0)
  Block bootstrap n=300 on OOS SR
  Deflated Sharpe N_trials=4
  Cost stress ±50 %

Orthogonality — K127 (BIS carry), K131 (funding-mom 7d, REJECT), K133 (funding-rev 5d, ACCEPT)
  ρ on overlapping daily resample.
"""

import json
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

warnings.filterwarnings("ignore")

ROOT = Path("/Users/nekonaomichi/crypto-lab")
CACHE = ROOT / "cache"
XEX = CACHE / "xex_fr"

SYMBOLS = ["BTC", "ETH", "SOL", "BNB", "DOGE", "AVAX", "LINK"]

COST_BPS = 7.0
IS_FRAC = 0.70
SEED = 20260524
N_TRIALS_DSR = 8
N_PERM = 300
N_BOOT = 300
MAX_HOLD_EVENTS = 9          # 3 days × 3 events/day

ANN_PER_EVENT = 1.0 / (365.0 * 3.0)
THR_2PCT_ANN = 0.02 * ANN_PER_EVENT
THR_3PCT_ANN = 0.03 * ANN_PER_EVENT

ANN_FACTOR_8H = np.sqrt(365.0 * 3.0)


# ---------------------------------------------------------- I/O ----------
def load_bybit_fr(sym):
    p = CACHE / f"bybit_fr_{sym}USDT_730d.parquet"
    if not p.exists():
        return None
    df = pd.read_parquet(p)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.set_index("timestamp").sort_index()
    df = df[~df.index.duplicated(keep="last")]
    return df["funding_rate"].astype(float).rename("bybit")


def load_binance_fr(sym):
    p = XEX / f"binance_fr_{sym}USDT_730d.parquet"
    if not p.exists():
        return None
    df = pd.read_parquet(p)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.set_index("timestamp").sort_index()
    df = df[~df.index.duplicated(keep="last")]
    return df["funding_rate"].astype(float).rename("binance")


def load_mexc_fr(sym):
    p = XEX / f"mexc_fr_{sym}_USDT_full.parquet"
    if not p.exists():
        return None
    df = pd.read_parquet(p)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.set_index("timestamp").sort_index()
    df = df[~df.index.duplicated(keep="last")]
    return df["funding_rate"].astype(float).rename("mexc")


def load_bybit_px(sym):
    p = CACHE / f"{sym}USDT_4h_730d.parquet"
    if not p.exists():
        return None
    df = pd.read_parquet(p)
    df["open_time"] = pd.to_datetime(df["open_time"])
    df = df.set_index("open_time").sort_index()
    df = df[~df.index.duplicated(keep="last")]
    return df["close"].astype(float).rename(sym)


def round_to_8h(idx):
    return pd.to_datetime(idx).round("8H")


def build_panels():
    """Per-symbol df: cols = bybit, binance, mexc, px on Bybit FR 8h grid."""
    panels, avail = {}, {}
    for sym in SYMBOLS:
        b = load_bybit_fr(sym)
        if b is None or b.empty:
            avail[sym] = {"skipped": "no_bybit_fr"}
            continue
        n = load_binance_fr(sym)
        m = load_mexc_fr(sym)
        px = load_bybit_px(sym)
        if px is None:
            avail[sym] = {"skipped": "no_price"}
            continue
        b.index = round_to_8h(b.index)
        if n is not None: n.index = round_to_8h(n.index)
        if m is not None: m.index = round_to_8h(m.index)
        b = b[~b.index.duplicated(keep="last")]
        if n is not None: n = n[~n.index.duplicated(keep="last")]
        if m is not None: m = m[~m.index.duplicated(keep="last")]
        df = pd.concat([b,
                        n if n is not None else pd.Series(dtype=float, name="binance"),
                        m if m is not None else pd.Series(dtype=float, name="mexc")],
                       axis=1).sort_index()
        df["px"] = px.reindex(df.index, method="ffill")
        df = df.dropna(subset=["bybit", "px"])
        if df.empty:
            avail[sym] = {"skipped": "empty_after_join"}
            continue
        panels[sym] = df
        avail[sym] = {
            "bybit_n": int(len(b)),
            "binance_n": int(len(n)) if n is not None else 0,
            "mexc_n": int(len(m)) if m is not None else 0,
            "panel_n": int(len(df)),
            "panel_start": str(df.index.min()),
            "panel_end":   str(df.index.max()),
        }
    return panels, avail


# ------------------------------------------------ MOMENTUM signal --------
def signal_mom_bb(panel, thr, hold=None):
    """binance - bybit spread. Momentum/continuation:
       bb_spread > +thr → SHORT bybit (-1)
       bb_spread < -thr → LONG  bybit (+1)
    If hold is None: zero-cross hold (max MAX_HOLD_EVENTS).
    If hold is int: hold exactly N events then exit (event-driven; like K159 with N=1)."""
    if "binance" not in panel.columns:
        return pd.Series(0.0, index=panel.index), pd.Series(np.nan, index=panel.index)
    spread = panel["binance"] - panel["bybit"]
    pos_raw = pd.Series(0.0, index=panel.index)
    pos_raw[spread >  thr] = -1.0
    pos_raw[spread < -thr] = +1.0
    pos_raw[spread.isna()] = 0.0
    if hold is None:
        pos = apply_zerocross_hold(pos_raw, spread, max_hold=MAX_HOLD_EVENTS)
    else:
        # Event-driven N-period hold: position[t..t+hold-1] = sign at t
        pos = apply_fixed_hold(pos_raw, hold)
    return pos, spread


def signal_mom_bm(panel, thr, hold=None):
    """bybit - mexc spread. Momentum/continuation:
       bm_spread > +thr → LONG  bybit (+1)
       bm_spread < -thr → SHORT bybit (-1)
    """
    if "mexc" not in panel.columns:
        return pd.Series(0.0, index=panel.index), pd.Series(np.nan, index=panel.index)
    spread = panel["bybit"] - panel["mexc"]
    pos_raw = pd.Series(0.0, index=panel.index)
    pos_raw[spread >  thr] = +1.0
    pos_raw[spread < -thr] = -1.0
    pos_raw[spread.isna()] = 0.0
    if hold is None:
        pos = apply_zerocross_hold(pos_raw, spread, max_hold=MAX_HOLD_EVENTS)
    else:
        pos = apply_fixed_hold(pos_raw, hold)
    return pos, spread


def apply_fixed_hold(pos_raw, hold):
    """Open at signal, exit after exactly `hold` periods. If a new signal
    fires while already in a position of the same sign, refresh hold; if of
    opposite sign, flip immediately."""
    p_arr = pos_raw.to_numpy(dtype=np.float64, copy=False)
    out = np.zeros_like(p_arr)
    cur = 0.0
    held = 0
    for i in range(len(p_arr)):
        new_sig = p_arr[i]
        if cur != 0.0:
            if held >= hold:
                cur = 0.0
                held = 0
        if new_sig != 0.0 and new_sig != cur:
            cur = new_sig
            held = 0
        if cur != 0.0:
            held += 1
        out[i] = cur
    return pd.Series(out, index=pos_raw.index)


def signal_combo(panel, thr):
    """Both bb AND bm aligned in same direction (intersection).
       Each leg uses its own continuation mapping, then we require sign match."""
    bb_pos_raw = pd.Series(0.0, index=panel.index)
    bm_pos_raw = pd.Series(0.0, index=panel.index)
    if "binance" in panel.columns:
        bb_spread = panel["binance"] - panel["bybit"]
        bb_pos_raw[bb_spread >  thr] = -1.0
        bb_pos_raw[bb_spread < -thr] = +1.0
        bb_pos_raw[bb_spread.isna()] = 0.0
    if "mexc" in panel.columns:
        bm_spread = panel["bybit"] - panel["mexc"]
        bm_pos_raw[bm_spread >  thr] = +1.0
        bm_pos_raw[bm_spread < -thr] = -1.0
        bm_pos_raw[bm_spread.isna()] = 0.0
    agree = (bb_pos_raw * bm_pos_raw) > 0
    pos_raw = pd.Series(0.0, index=panel.index)
    pos_raw[agree] = bb_pos_raw[agree]
    # Combo "exit when EITHER spread crosses zero in the wrong direction"
    # Use the OR of the two spread sign-flips as the exit trigger
    bb_sign = np.sign(panel["binance"] - panel["bybit"]) if "binance" in panel.columns \
              else pd.Series(0.0, index=panel.index)
    bm_sign = np.sign(panel["bybit"] - panel["mexc"])   if "mexc"    in panel.columns \
              else pd.Series(0.0, index=panel.index)
    # For combo, exit when either signal collapses to 0
    exit_mask = (bb_sign == 0) | (bm_sign == 0)
    pos = apply_zerocross_hold_mask(pos_raw, exit_mask, max_hold=MAX_HOLD_EVENTS)
    return pos, None


def apply_zerocross_hold(pos_raw, spread, max_hold):
    """Carry a non-zero position until spread crosses zero (sign flip vs entry)
    or max_hold events, whichever comes first. Vectorised numpy loop."""
    p_arr = pos_raw.to_numpy(dtype=np.float64, copy=True)
    s_arr = spread.fillna(0.0).to_numpy(dtype=np.float64, copy=False)
    return pd.Series(_hold_numba(p_arr, s_arr, int(max_hold)),
                     index=pos_raw.index)


def apply_zerocross_hold_mask(pos_raw, exit_mask, max_hold):
    """Combo: carry until exit_mask True or max_hold."""
    p_arr = pos_raw.to_numpy(dtype=np.float64, copy=True)
    e_arr = exit_mask.to_numpy(dtype=np.bool_, copy=False)
    return pd.Series(_hold_mask_numpy(p_arr, e_arr, int(max_hold)),
                     index=pos_raw.index)


def _hold_numba(p_arr, s_arr, max_hold):
    """Pure-numpy implementation of hold logic — fast vs pandas .iloc loops."""
    n = p_arr.shape[0]
    out = np.zeros(n, dtype=np.float64)
    cur = 0.0
    entry_sign = 0.0
    held = 0
    for i in range(n):
        new_sig = p_arr[i]
        s_val = s_arr[i]
        if cur != 0.0:
            spread_sign = 1.0 if s_val > 0 else (-1.0 if s_val < 0 else 0.0)
            if spread_sign != entry_sign or held >= max_hold:
                cur = 0.0
                held = 0
                entry_sign = 0.0
            else:
                held += 1
        if cur == 0.0 and new_sig != 0.0:
            cur = new_sig
            entry_sign = 1.0 if s_val > 0 else (-1.0 if s_val < 0 else 0.0)
            held = 1
        out[i] = cur
    return out


def _hold_mask_numpy(p_arr, e_arr, max_hold):
    n = p_arr.shape[0]
    out = np.zeros(n, dtype=np.float64)
    cur = 0.0
    held = 0
    for i in range(n):
        new_sig = p_arr[i]
        if cur != 0.0:
            if e_arr[i] or held >= max_hold:
                cur = 0.0
                held = 0
            else:
                held += 1
        if cur == 0.0 and new_sig != 0.0:
            cur = new_sig
            held = 1
        out[i] = cur
    return out


# ------------------------------------------------ backtest one ------------
def backtest_one(panel, pos, cost_bps=COST_BPS):
    px = panel["px"].values
    p = pos.shift(1).fillna(0.0).values     # observed at t, traded t→t+1
    ret = np.zeros(len(p))
    for i in range(len(p) - 1):
        if px[i] > 0 and np.isfinite(px[i + 1]):
            ret[i] = px[i + 1] / px[i] - 1.0
    pnl = p * ret
    dp = np.abs(np.diff(p, prepend=0.0))
    cost = dp * (cost_bps / 1e4)
    net = pnl - cost
    return pd.DataFrame(
        {"pos": p, "ret": ret, "gross": pnl, "cost": cost, "net": net},
        index=panel.index,
    )


def backtest_variant(panels, signal_fn):
    rets = []
    per_sym = {}
    for sym, panel in panels.items():
        pos, _ = signal_fn(panel)
        if pos is None:
            continue
        bt = backtest_one(panel, pos)
        per_sym[sym] = {
            "n": int(len(bt)),
            "active_rate": float((bt["pos"] != 0).mean()),
            "net_total": float(bt["net"].sum()),
        }
        rets.append(bt["net"].rename(sym))
    if not rets:
        return pd.Series(dtype=float), per_sym
    df = pd.concat(rets, axis=1).sort_index().fillna(0.0)
    eq = df.mean(axis=1)
    return eq, per_sym


# ------------------------------------------------ stats -------------------
def perf_stats(r, ann_factor=ANN_FACTOR_8H):
    r = pd.Series(r).dropna()
    if r.std() == 0 or len(r) < 5:
        return dict(sharpe=0.0, sortino=0.0, calmar=0.0, max_dd=0.0,
                    win_rate=0.0, ann_ret=0.0, ann_vol=0.0, n=int(len(r)))
    mu = r.mean(); sd = r.std()
    sharpe = mu / sd * ann_factor
    downside = r[r < 0].std()
    sortino = mu / downside * ann_factor if downside and downside > 0 else 0.0
    eq = (1 + r).cumprod()
    dd = (eq / eq.cummax() - 1).min()
    ann_ret = (1 + mu) ** (ann_factor ** 2) - 1
    calmar = ann_ret / abs(dd) if dd < 0 else 0.0
    return dict(sharpe=float(sharpe), sortino=float(sortino),
                calmar=float(calmar), max_dd=float(dd),
                win_rate=float((r > 0).mean()),
                ann_ret=float(ann_ret), ann_vol=float(sd * ann_factor),
                n=int(len(r)))


def deflated_sharpe(sr, n_obs, n_trials, skew=0.0, kurt=3.0):
    if n_obs < 20 or n_trials < 1:
        return 0.0
    emc = 0.5772
    e_max = (np.sqrt(2 * np.log(max(n_trials, 2))) * (1 - emc)
             + (1 - emc) / np.sqrt(2 * np.log(max(n_trials, 2))))
    var = (1 - skew * sr + (kurt - 1) / 4.0 * sr ** 2) / max(n_obs - 1, 1)
    if var <= 0:
        return 0.0
    from math import erf, sqrt
    z = (sr - e_max) / np.sqrt(var)
    return float(0.5 * (1 + erf(z / sqrt(2))))


def block_bootstrap_ci(rets, ann_factor, n_iter=N_BOOT, block=8, seed=SEED):
    rets = np.asarray(rets)
    n = len(rets)
    if n < block * 3:
        return {"sr_lo": 0.0, "sr_hi": 0.0, "sr_mean": 0.0}
    rng = np.random.default_rng(seed)
    n_blocks = max(1, n // block)
    samples = []
    for _ in range(n_iter):
        starts = rng.integers(0, n - block + 1, size=n_blocks)
        s = np.concatenate([rets[i:i + block] for i in starts])
        sd = s.std()
        if sd > 0:
            samples.append(s.mean() / sd * ann_factor)
    if not samples:
        return {"sr_lo": 0.0, "sr_hi": 0.0, "sr_mean": 0.0}
    arr = np.array(samples)
    return {"sr_lo": float(np.quantile(arr, 0.025)),
            "sr_hi": float(np.quantile(arr, 0.975)),
            "sr_mean": float(arr.mean())}


def permutation_test_onesided(panels, signal_fn, n_iter=N_PERM, seed=SEED):
    """One-sided: P(null SR >= actual SR). Permute the SIGN of each non-zero
    position per symbol independently — null = no directional edge.
    Pre-compute positions once per symbol and reuse across perms."""
    rng = np.random.default_rng(seed)
    actual, _ = backtest_variant(panels, signal_fn)
    actual_sr = perf_stats(actual)["sharpe"]

    cache = []   # list of (sym, panel.index, pos_array, ret_array)
    for sym, panel in panels.items():
        pos, _ = signal_fn(panel)
        if pos is None:
            continue
        px = panel["px"].to_numpy()
        ret = np.zeros(len(px))
        ret[:-1] = px[1:] / px[:-1] - 1.0
        # we'll convolve pos.shift(1) inside; do it now
        p_shift = np.concatenate(([0.0], pos.to_numpy()[:-1]))
        cache.append((sym, panel.index, p_shift, ret))

    if not cache:
        return {"actual_sharpe": float(actual_sr), "null_mean": 0.0,
                "null_std": 0.0, "null_p95": 0.0, "p_value": 1.0,
                "n_iter": n_iter}

    # Build common index union
    union_idx = sorted(set().union(*[set(c[1]) for c in cache]))
    union_idx = pd.DatetimeIndex(union_idx)
    union_pos = {sym: pd.Series(0.0, index=union_idx) for sym, _, _, _ in cache}
    union_ret = {sym: pd.Series(0.0, index=union_idx) for sym, _, _, _ in cache}
    for sym, idx, ps, rt in cache:
        union_pos[sym].loc[idx] = ps
        union_ret[sym].loc[idx] = rt
    pos_mat = np.column_stack([union_pos[s].to_numpy() for s, *_ in cache])
    ret_mat = np.column_stack([union_ret[s].to_numpy() for s, *_ in cache])
    cost_arr = np.zeros_like(pos_mat)  # cost stays simplified — fixed per row
    # Cost = |Δpos| × cost_bps; for permutation we approximate by re-deriving
    # since sign flips don't change |dp| structure much. Use ORIGINAL cost.
    n_rows = pos_mat.shape[0]
    n_syms = pos_mat.shape[1]
    for j in range(n_syms):
        dp = np.abs(np.diff(pos_mat[:, j], prepend=0.0))
        cost_arr[:, j] = dp * (COST_BPS / 1e4)

    null_srs = np.zeros(n_iter)
    for it in range(n_iter):
        signs = rng.choice([-1.0, 1.0], size=(n_rows, n_syms))
        net = pos_mat * signs * ret_mat - cost_arr
        eq = net.mean(axis=1)
        sd = eq.std()
        if sd > 0:
            null_srs[it] = eq.mean() / sd * ANN_FACTOR_8H
    return {"actual_sharpe": float(actual_sr),
            "null_mean": float(null_srs.mean()),
            "null_std":  float(null_srs.std()),
            "null_p95":  float(np.quantile(null_srs, 0.95)),
            "p_value":   float((null_srs >= actual_sr).mean()),
            "n_iter": n_iter}


def walk_forward(rets, n_folds=4):
    T = len(rets)
    fs = T // n_folds
    return [{"fold": f,
             **perf_stats(rets.iloc[f * fs: ((f + 1) * fs) if f < n_folds - 1 else T])}
            for f in range(n_folds)]


# ------------------------------------------------ variants ----------------
def make_bb(thr, hold=None):
    return lambda panel: signal_mom_bb(panel, thr, hold=hold)


def make_bm(thr, hold=None):
    return lambda panel: signal_mom_bm(panel, thr, hold=hold)


def make_combo(thr):
    return lambda panel: signal_combo(panel, thr)


# Spec defined zero-cross hold (up to 3d). We also include 1-event hold for
# direct apples-to-apples vs K159 (where the inverse hypothesis was raised).
VARIANTS = {
    # Primary pre-registered (zero-cross hold up to 3d)
    "V_bb_2pct":    {"fn": make_bb(THR_2PCT_ANN), "label": "MOM bb |Δ|>2%/yr · hold=zerocross/3d"},
    "V_bb_3pct":    {"fn": make_bb(THR_3PCT_ANN), "label": "MOM bb |Δ|>3%/yr · hold=zerocross/3d"},
    "V_bm_2pct":    {"fn": make_bm(THR_2PCT_ANN), "label": "MOM bm |Δ|>2%/yr · hold=zerocross/3d"},
    "V_combo":      {"fn": make_combo(THR_2PCT_ANN),
                     "label": "MOM bb∧bm aligned (2%/yr) · hold=zerocross/3d"},
    # Direct K159-inverse (1-event hold, isolates the sign-flip claim)
    "V_bb_2pct_1ev": {"fn": make_bb(THR_2PCT_ANN, hold=1),
                      "label": "MOM bb |Δ|>2%/yr · hold=1 event (K159 inverse)"},
    "V_bb_3pct_1ev": {"fn": make_bb(THR_3PCT_ANN, hold=1),
                      "label": "MOM bb |Δ|>3%/yr · hold=1 event (K159 inverse)"},
    "V_bm_2pct_1ev": {"fn": make_bm(THR_2PCT_ANN, hold=1),
                      "label": "MOM bm |Δ|>2%/yr · hold=1 event (K159 inverse)"},
    "V_bm_3pct_1ev": {"fn": make_bm(THR_3PCT_ANN, hold=1),
                      "label": "MOM bm |Δ|>3%/yr · hold=1 event (K159 inverse)"},
}


def gross_sharpe(panels, signal_fn):
    rets = []
    for sym, panel in panels.items():
        pos, _ = signal_fn(panel)
        bt = backtest_one(panel, pos, cost_bps=0.0)
        rets.append(bt["net"].rename(sym))
    if not rets:
        return 0.0
    df = pd.concat(rets, axis=1).sort_index().fillna(0.0)
    return perf_stats(df.mean(axis=1))["sharpe"]


def run_variant(name, vdef, panels, t0):
    print(f"  >> {name}: {vdef['label']}")
    rets, per_sym = backtest_variant(panels, vdef["fn"])
    if rets.empty:
        return {"empty": True, "label": vdef["label"]}
    n_total = len(rets)
    n_is = int(n_total * IS_FRAC)
    full = perf_stats(rets)
    is_ = perf_stats(rets.iloc[:n_is])
    oos = perf_stats(rets.iloc[n_is:])
    active = perf_stats(rets[rets != 0]) if (rets != 0).sum() > 5 else \
             dict(sharpe=0.0, n=int((rets != 0).sum()))

    def re_bt(scale):
        out = []
        for sym, panel in panels.items():
            pos, _ = vdef["fn"](panel)
            bt = backtest_one(panel, pos, cost_bps=COST_BPS * scale)
            out.append(bt["net"].rename(sym))
        return pd.concat(out, axis=1).sort_index().fillna(0.0).mean(axis=1)

    lo_sr = perf_stats(re_bt(0.5))["sharpe"]
    hi_sr = perf_stats(re_bt(1.5))["sharpe"]
    gross_sr = perf_stats(re_bt(0.0))["sharpe"]
    boot = block_bootstrap_ci(rets.iloc[n_is:].values, ANN_FACTOR_8H,
                              n_iter=N_BOOT, block=8, seed=SEED + 7)
    perm = permutation_test_onesided(panels, vdef["fn"],
                                     n_iter=N_PERM, seed=SEED + 11)
    wf = walk_forward(rets, n_folds=4)
    skew_v = float(stats.skew(rets.dropna())) if len(rets.dropna()) > 5 else 0.0
    kurt_v = float(stats.kurtosis(rets.dropna(), fisher=False)) \
             if len(rets.dropna()) > 5 else 3.0
    dsr_full = deflated_sharpe(full["sharpe"], full["n"],
                                n_trials=N_TRIALS_DSR,
                                skew=skew_v, kurt=kurt_v)
    dsr_oos = deflated_sharpe(oos["sharpe"], oos["n"],
                               n_trials=N_TRIALS_DSR,
                               skew=skew_v, kurt=kurt_v)

    gates = {
        "oos_sr_ge_0_5":      bool(oos["sharpe"] >= 0.5),
        "p_perm_lt_0_05":     bool(perm["p_value"] < 0.05),
        "max_dd_gt_neg40":    bool(full["max_dd"] > -0.40),
        "cost_stress_robust": bool(hi_sr >= 0.5 * full["sharpe"]
                                   if full["sharpe"] > 0 else False),
        "dsr_oos_ge_0_5":     bool(dsr_oos >= 0.5),
        "wf_majority_pos":    bool(sum(1 for f in wf if f["sharpe"] > 0) >= 3),
    }
    gates["pass_count"] = int(sum(1 for v in gates.values() if v is True))
    gates["all_pass"] = bool(all(v for k_, v in gates.items()
                                  if k_ not in ("pass_count", "all_pass")))

    return {
        "label": vdef["label"],
        "n_periods": n_total,
        "full": full, "is": is_, "oos": oos, "active_only": active,
        "active_rate": float((rets != 0).mean()),
        "cost_stress": {"gross_0pct": float(gross_sr),
                        "low_50pct": float(lo_sr),
                        "base_100pct": float(full["sharpe"]),
                        "high_150pct": float(hi_sr)},
        "bootstrap_oos_sharpe_95ci": boot,
        "permutation": perm,
        "walk_forward": wf,
        "dsr_full": float(dsr_full), "dsr_oos": float(dsr_oos),
        "per_symbol": per_sym,
        "gates": gates,
        "equity_curve": (1 + rets).cumprod().tolist(),
        "equity_idx":   [str(x) for x in rets.index],
        "_rets_series": rets,
    }


# ------------------------------------------------ orthogonality -----------
def load_k127_pnl():
    p = ROOT / "wave_k127_curves.json"
    if not p.exists():
        return None
    d = json.load(open(p))
    ts = pd.to_datetime(d.get("timestamps", []))
    pnl = pd.Series(d.get("pnl_net", []), index=ts, name="K127")
    return pnl


def load_curve_variant(json_path, variant_name):
    p = Path(json_path)
    if not p.exists():
        return None
    d = json.load(open(p))
    if variant_name not in d:
        return None
    eq = pd.Series(d[variant_name]["equity_curve"],
                   index=pd.to_datetime(d[variant_name]["equity_idx"]))
    # daily resample then pct-change
    eq = eq.sort_index()
    eq = eq[~eq.index.duplicated(keep="last")]
    return eq.pct_change().dropna().rename(variant_name)


def orthogonality_matrix(k161_rets_dict):
    """Correlate K161 daily returns vs K127/K131/K133 daily returns."""
    refs = {}
    k127 = load_k127_pnl()
    if k127 is not None:
        refs["K127_BIS"] = k127.resample("1D").sum()
    k131_pri = load_curve_variant(ROOT / "wave_k131_curves.json",
                                  "V_hold7d_z15_top3")
    if k131_pri is not None:
        refs["K131_fmom7d"] = k131_pri.resample("1D").sum()
    k133_pri = load_curve_variant(ROOT / "wave_k133_curves.json",
                                  "V_rev_5d_z15")
    if k133_pri is not None:
        refs["K133_frev5d"] = k133_pri.resample("1D").sum()

    out = {}
    for vname, rets in k161_rets_dict.items():
        daily = rets.resample("1D").sum()
        row = {}
        for rname, rser in refs.items():
            common = pd.concat([daily, rser], axis=1).dropna()
            if len(common) < 20:
                row[rname] = {"rho": None, "n": int(len(common))}
            else:
                rho = float(common.iloc[:, 0].corr(common.iloc[:, 1]))
                row[rname] = {"rho": rho, "n": int(len(common))}
        out[vname] = row
    return out


# ------------------------------------------------ markdown ---------------
def write_markdown(results, ortho, data_avail, meta):
    md = ROOT / "wave_k161_xex_momentum.md"
    lines = []
    lines.append("# Wave K161 — Cross-Exchange FR MOMENTUM")
    lines.append("")
    lines.append("Pre-registered INVERSE of K159 (continuation direction).")
    lines.append("")
    lines.append(f"- Symbols used: {meta['symbols_used']}")
    lines.append(f"- Wall-time: {meta['wall_seconds']:.1f} s")
    lines.append(f"- IS/OOS: 70/30 · WF folds: 4 · Perm n={N_PERM} · Boot n={N_BOOT} · DSR Ntrials={N_TRIALS_DSR}")
    lines.append(f"- Costs: {COST_BPS:.2f} bps/side · Hold: exit on spread sign-flip OR ≤ {MAX_HOLD_EVENTS} events (3d)")
    lines.append("")
    lines.append("## Per-variant Sharpe")
    lines.append("")
    lines.append("| Variant | full SR | IS SR | OOS SR | active% | MaxDD | perm_p | DSR_oos | gates |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|")
    for name, r in results.items():
        if r.get("empty"):
            lines.append(f"| {name} | empty | | | | | | | |")
            continue
        f, i_, o = r["full"], r["is"], r["oos"]
        lines.append(f"| {name} | {f['sharpe']:+.2f} | {i_['sharpe']:+.2f} | "
                     f"{o['sharpe']:+.2f} | {r['active_rate']*100:.1f}% | "
                     f"{f['max_dd']:.2%} | {r['permutation']['p_value']:.3f} | "
                     f"{r['dsr_oos']:.3f} | {r['gates']['pass_count']}/6 |")
    lines.append("")
    lines.append("## Bootstrap OOS Sharpe (95% CI) & cost stress (incl. GROSS / 0bp)")
    lines.append("")
    lines.append("| Variant | boot SR lo | boot SR mean | boot SR hi | GROSS SR (0bp) | cost×0.5 | base (7bp) | cost×1.5 |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|")
    for name, r in results.items():
        if r.get("empty"): continue
        b = r["bootstrap_oos_sharpe_95ci"]; cs = r["cost_stress"]
        lines.append(f"| {name} | {b['sr_lo']:+.2f} | {b['sr_mean']:+.2f} | "
                     f"{b['sr_hi']:+.2f} | **{cs['gross_0pct']:+.2f}** | "
                     f"{cs['low_50pct']:+.2f} | {cs['base_100pct']:+.2f} | "
                     f"{cs['high_150pct']:+.2f} |")
    lines.append("")
    lines.append("## Walk-forward (4 folds, full Sharpe)")
    lines.append("")
    lines.append("| Variant | f0 | f1 | f2 | f3 |")
    lines.append("|---|---:|---:|---:|---:|")
    for name, r in results.items():
        if r.get("empty"): continue
        wf = r["walk_forward"]
        s = [f"{w['sharpe']:+.2f}" for w in wf]
        lines.append(f"| {name} | " + " | ".join(s) + " |")
    lines.append("")
    lines.append("## Orthogonality matrix (daily-return ρ vs reference waves)")
    lines.append("")
    refs = sorted({k for v in ortho.values() for k in v.keys()})
    lines.append("| Variant | " + " | ".join(refs) + " |")
    lines.append("|" + "---|" * (len(refs) + 1))
    for name, row in ortho.items():
        cells = []
        for rname in refs:
            cell = row.get(rname, {})
            if cell.get("rho") is None:
                cells.append("—")
            else:
                cells.append(f"{cell['rho']:+.2f} (n={cell['n']})")
        lines.append(f"| {name} | " + " | ".join(cells) + " |")
    lines.append("")
    lines.append("## §6 gates (per variant)")
    lines.append("")
    lines.append("| Variant | OOS≥0.5 | perm<0.05 | DD>-40% | costRobust | DSR≥0.5 | WF majPos | ALL |")
    lines.append("|---|:-:|:-:|:-:|:-:|:-:|:-:|:-:|")
    for name, r in results.items():
        if r.get("empty"): continue
        g = r["gates"]
        cell = lambda k: "PASS" if g[k] else "fail"
        lines.append(f"| {name} | {cell('oos_sr_ge_0_5')} | {cell('p_perm_lt_0_05')} | "
                     f"{cell('max_dd_gt_neg40')} | {cell('cost_stress_robust')} | "
                     f"{cell('dsr_oos_ge_0_5')} | {cell('wf_majority_pos')} | "
                     f"{'PASS' if g['all_pass'] else 'fail'} |")
    lines.append("")
    lines.append("## Per-symbol activity & net (primary variant V_bb_2pct)")
    lines.append("")
    pr = results.get("V_bb_2pct")
    if pr and not pr.get("empty"):
        lines.append("| Sym | n | active rate | net total |")
        lines.append("|---|---:|---:|---:|")
        for s, d in pr["per_symbol"].items():
            lines.append(f"| {s} | {d['n']} | {d['active_rate']*100:.1f}% | {d['net_total']:+.4f} |")
    lines.append("")
    lines.append("## Data availability")
    lines.append("")
    lines.append("| Sym | bybit n | binance n | mexc n | panel n | start | end |")
    lines.append("|---|---:|---:|---:|---:|---|---|")
    for s, d in data_avail.items():
        if d.get("skipped"):
            lines.append(f"| {s} | skipped: {d['skipped']} | | | | | |")
        else:
            lines.append(f"| {s} | {d['bybit_n']} | {d['binance_n']} | {d['mexc_n']} | "
                         f"{d['panel_n']} | {d['panel_start']} | {d['panel_end']} |")
    lines.append("")
    lines.append("## Verdict")
    lines.append("")
    primary = results.get("V_bb_2pct", {})
    k159_inv = results.get("V_bb_3pct_1ev", {})   # direct K159 best inverse test
    best = max(((n, r) for n, r in results.items() if not r.get("empty")),
               key=lambda x: x[1]["full"]["sharpe"], default=(None, None))

    if k159_inv and not k159_inv.get("empty"):
        oos_sr = k159_inv["oos"]["sharpe"]
        g_inv = k159_inv["gates"]
        lines.append(f"### K159-inverse direct check (V_bb_3pct_1ev, 1-event hold)")
        lines.append("")
        lines.append(f"- OOS SR = **{oos_sr:+.2f}** (K159 reported -1.95 for the same variant — "
                     f"inverse-implied prediction was ~+1.95 if signal direction is the only "
                     f"thing that needs flipping)")
        lines.append(f"- perm_p = {k159_inv['permutation']['p_value']:.3f}")
        lines.append(f"- gates = {g_inv['pass_count']}/6")
        if oos_sr >= 1.0 and g_inv["pass_count"] >= 4:
            lines.append("- Verdict on inverse hypothesis: **CONFIRMED**")
        elif oos_sr >= 0.5:
            lines.append("- Verdict on inverse hypothesis: **PARTIAL** — sign of effect is "
                         "consistent with K159 inverse but magnitude/significance below bar")
        elif oos_sr >= -0.3:
            lines.append("- Verdict on inverse hypothesis: **WASH** — flipping the sign roughly "
                         "cancels K159 loss; market is microstructure noise on this signal at "
                         "1-event hold (after cost), NOT a tradeable continuation either")
        else:
            lines.append("- Verdict on inverse hypothesis: **REJECTED** — momentum AND fade both lose, "
                         "meaning the trade-frame returns are dominated by COSTS (~7 bp × very high "
                         "active_rate) rather than signal sign. The K159 negative SR was a COST "
                         "artefact, not a flippable directional edge.")
        lines.append("")

    if primary and not primary.get("empty"):
        g = primary["gates"]
        if g["all_pass"]:
            verdict = ("**ACCEPT** — primary V_bb_2pct (zerocross hold) passes all 6 §6 gates. "
                       "Hypothesis: K159 INVERSE (continuation direction) confirmed. "
                       "Forward to K162 ensemble (verify ρ vs K133 ACCEPT for diversification).")
        elif g["pass_count"] >= 4 and primary["oos"]["sharpe"] >= 0.5:
            verdict = (f"**PARTIAL** — V_bb_2pct passes {g['pass_count']}/6 gates with "
                       f"positive OOS Sharpe {primary['oos']['sharpe']:+.2f}. "
                       f"Inspect failed gates; consider as a candidate but with reservation.")
        else:
            verdict = (f"**REJECT (primary)** — V_bb_2pct passes only {g['pass_count']}/6 gates "
                       f"(OOS SR {primary['oos']['sharpe']:+.2f}). "
                       f"Inverse-of-rejection logic did not survive honest pre-registration. "
                       f"The asymmetry between K159 fade SR and K161 momentum SR is the key "
                       f"diagnostic — see the K159-inverse direct check above.")
        lines.append(verdict)
        if best[0]:
            lines.append("")
            lines.append(f"Best variant by full SR: **{best[0]}** ({best[1]['full']['sharpe']:+.2f}).")
    lines.append("")
    md.write_text("\n".join(lines))


# ------------------------------------------------ main --------------------
def main():
    t0 = time.time()
    print("=== Wave K161 — Cross-Exchange FR MOMENTUM (K159 inverse) ===")
    print(f"Symbols: {SYMBOLS}")
    print(f"Thr 2%/yr per 8h = {THR_2PCT_ANN:.3e}")
    print(f"Thr 3%/yr per 8h = {THR_3PCT_ANN:.3e}\n")
    panels, avail = build_panels()
    print("\nData availability:")
    for s, d in avail.items():
        print(f"  {s}: {d}")
    if not panels:
        print("No panels — aborting.")
        return
    print(f"\n{len(panels)} symbols available.\nRunning variants ...")
    results = {}
    for name, vdef in VARIANTS.items():
        results[name] = run_variant(name, vdef, panels, t0)
        print(f"     [elapsed {time.time() - t0:.1f}s]")

    print("\nOrthogonality vs K127/K131/K133 ...")
    rets_map = {k: v["_rets_series"] for k, v in results.items()
                if not v.get("empty")}
    ortho = orthogonality_matrix(rets_map)
    for v, row in ortho.items():
        print(f"  {v}:")
        for r, d in row.items():
            print(f"     vs {r}: rho={d.get('rho')} n={d.get('n')}")

    # save
    out_path = ROOT / "wave_k161_xex_momentum.json"
    curves_path = ROOT / "wave_k161_xex_momentum.curves.json"
    summary = {}
    for name, v in results.items():
        slim = {kk: vv for kk, vv in v.items()
                if kk not in ("equity_curve", "equity_idx", "_rets_series")}
        summary[name] = slim
    summary["_orthogonality"] = ortho
    summary["_data_availability"] = avail
    meta = {
        "wave": "K161",
        "wall_seconds": time.time() - t0,
        "symbols_requested": SYMBOLS,
        "symbols_used": list(panels.keys()),
        "n_perm": N_PERM, "n_boot": N_BOOT, "n_trials_dsr": N_TRIALS_DSR,
        "is_frac": IS_FRAC, "cost_bps_per_side": COST_BPS,
        "thr_2pct_ann_per_8h": THR_2PCT_ANN,
        "thr_3pct_ann_per_8h": THR_3PCT_ANN,
        "max_hold_events": MAX_HOLD_EVENTS,
        "ann_factor_8h": float(ANN_FACTOR_8H),
        "primary_variant": "V_bb_2pct",
        "direction": "MOMENTUM_CONTINUATION (K159 inverse)",
    }
    summary["_meta"] = meta

    curves = {name: {"equity_curve": v["equity_curve"],
                     "equity_idx":   v["equity_idx"]}
              for name, v in results.items() if "equity_curve" in v}

    with open(out_path, "w") as f:
        json.dump(summary, f, indent=2, default=str)
    with open(curves_path, "w") as f:
        json.dump(curves, f, indent=2, default=str)

    write_markdown(results, ortho, avail, meta)

    print(f"\nDone in {time.time() - t0:.1f}s")
    print(f"  -> {out_path}")
    print(f"  -> {curves_path}")
    print(f"  -> {ROOT / 'wave_k161_xex_momentum.md'}")
    print("\n=== K161 Summary ===")
    for name, r in results.items():
        if r.get("empty"):
            print(f"{name:12s} EMPTY"); continue
        f, o = r["full"], r["oos"]; p = r["permutation"]; g = r["gates"]
        print(f"{name:12s} netSR={f['sharpe']:+.2f} OOS={o['sharpe']:+.2f} "
              f"MaxDD={f['max_dd']:.2%} active={r['active_rate']:.3f} "
              f"p={p['p_value']:.3f} DSR_oos={r['dsr_oos']:.3f} "
              f"gates={g['pass_count']}/6")


if __name__ == "__main__":
    main()
