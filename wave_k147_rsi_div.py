"""Wave K147 — Hidden Bearish/Bullish RSI Divergence at 4H (R5-16)

Hypothesis (Coinbase Crypto Market Positioning, Mar 2026):
    At 4H scale:
      hidden bearish div  : price higher-high, RSI lower-high  -> SHORT
      hidden bullish div  : price lower-low,  RSI higher-low  -> LONG

Method (pre-registered)
-----------------------
1. RSI(14) on 4H bars per symbol.
2. Swing highs/lows = local extrema in a +/-5-bar window.
3. Hidden BEARISH div at swing-high t : price > prior_swing_high_price AND
                                        rsi   < prior_swing_high_rsi
   Hidden BULLISH div at swing-low  t : price < prior_swing_low_price  AND
                                        rsi   > prior_swing_low_rsi
   Prior swing must be within 60 bars.
4. Hold H bars (12 = 2d default).
5. Costs: 0.04% maker + 0.03% taker per side -> 0.14% round-trip.
6. Universe: top 15 by 4H quote volume (clean of pure-meme symbols).

Variants
--------
- V_bearish_only_h12 : short only, H=12
- V_long_short_h12   : both,        H=12
- V_bearish_h6       : short only,  H=6
- V_bearish_h24      : short only,  H=24

Audit
-----
- 730d, IS 70% / OOS 30%
- per-symbol Sharpe, portfolio Sharpe
- 4-fold walk-forward
- One-sided permutation n=300 (sign-shuffle of signal vector)
- Block bootstrap n=300
- Deflated Sharpe (Bailey-LdP) with N_trials = 4
- Cost stress +/-50%
"""
from __future__ import annotations

import json
import math
import time
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
from scipy import stats

BASE = Path("/Users/nekonaomichi/crypto-lab")
CACHE = BASE / "cache"

BARS_PER_DAY = 6           # 24h / 4h
BARS_PER_YEAR = BARS_PER_DAY * 365   # 2190
COST_PER_SIDE = 0.0004 + 0.0003       # 0.07%
COST_ROUNDTRIP = COST_PER_SIDE * 2.0  # 0.14%

OOS_FRAC = 0.30
WF_FOLDS = 4
N_PERM = 300
N_BOOT = 300
BOOT_BLOCK = 24            # ~4 days
SWING_W = 5
LOOKBACK_BARS = 60
RSI_LEN = 14

RNG = np.random.default_rng(20260524)

# Exclude pure-meme to keep signal clean (per spec)
MEME_BLACKLIST = {
    "BOMEUSDT", "BONKUSDT", "FLOKIUSDT", "PEPEUSDT", "SHIBUSDT",
    "WIFUSDT", "MEMEUSDT", "TRUMPUSDT", "BABYDOGEUSDT", "DOGEUSDT",
}


# -----------------------------------------------------------------------------
# Loading
# -----------------------------------------------------------------------------
def list_symbols() -> List[str]:
    """Return all non-meme symbols that have a 4h_730d parquet."""
    syms = []
    for p in sorted(CACHE.glob("*_4h_730d.parquet")):
        name = p.name.replace("_4h_730d.parquet", "")
        if name.startswith("hist_premium_"):
            continue
        if name in MEME_BLACKLIST:
            continue
        syms.append(name)
    return syms


def load_bars(sym: str) -> pd.DataFrame:
    df = pd.read_parquet(CACHE / f"{sym}_4h_730d.parquet")
    df["open_time"] = pd.to_datetime(df["open_time"])
    df = df.set_index("open_time").sort_index()
    return df[["open", "high", "low", "close", "volume", "quote_volume"]]


def select_top_liquid(symbols: List[str], top_n: int = 15) -> List[str]:
    """Rank by mean quote_volume across 4H bars (last 365d)."""
    stats_list = []
    for s in symbols:
        try:
            df = load_bars(s)
            recent = df.tail(BARS_PER_DAY * 365)
            if len(recent) < BARS_PER_DAY * 180:
                continue
            stats_list.append((s, float(recent["quote_volume"].mean())))
        except Exception:
            continue
    stats_list.sort(key=lambda x: x[1], reverse=True)
    return [s for s, _ in stats_list[:top_n]]


# -----------------------------------------------------------------------------
# Indicators / divergence detection
# -----------------------------------------------------------------------------
def rsi(close: pd.Series, n: int = RSI_LEN) -> pd.Series:
    delta = close.diff()
    up = delta.clip(lower=0.0)
    dn = (-delta).clip(lower=0.0)
    # Wilder smoothing
    avg_up = up.ewm(alpha=1.0 / n, adjust=False, min_periods=n).mean()
    avg_dn = dn.ewm(alpha=1.0 / n, adjust=False, min_periods=n).mean()
    rs = avg_up / avg_dn.replace(0.0, np.nan)
    out = 100.0 - 100.0 / (1.0 + rs)
    return out.fillna(50.0)


def swing_indices(values: np.ndarray, w: int, high: bool) -> np.ndarray:
    """Return indices i where values[i] is the max (or min) over [i-w, i+w]."""
    n = len(values)
    mask = np.zeros(n, dtype=bool)
    if n < 2 * w + 1:
        return np.where(mask)[0]
    for i in range(w, n - w):
        window = values[i - w:i + w + 1]
        if high:
            if values[i] == window.max() and np.argmax(window) == w:
                mask[i] = True
        else:
            if values[i] == window.min() and np.argmin(window) == w:
                mask[i] = True
    return np.where(mask)[0]


def build_signal(close: pd.Series, mode: str = "both") -> pd.Series:
    """Return integer signal series: +1 long, -1 short, 0 flat.
    Signal is produced at the swing-bar (i.e. confirmed w bars after) and
    intended to be entered NEXT bar (caller handles shift).
    """
    rsi_s = rsi(close, RSI_LEN)
    price = close.values
    rsi_v = rsi_s.values
    n = len(close)
    sig = np.zeros(n, dtype=float)

    hi_idx = swing_indices(price, SWING_W, high=True)
    lo_idx = swing_indices(price, SWING_W, high=False)

    if mode in ("bearish", "both"):
        for k in range(1, len(hi_idx)):
            i = hi_idx[k]
            j = hi_idx[k - 1]
            if i - j > LOOKBACK_BARS or i - j < SWING_W:
                continue
            if price[i] > price[j] and rsi_v[i] < rsi_v[j]:
                sig[i] = -1.0  # hidden bearish -> short

    if mode in ("bullish", "both"):
        for k in range(1, len(lo_idx)):
            i = lo_idx[k]
            j = lo_idx[k - 1]
            if i - j > LOOKBACK_BARS or i - j < SWING_W:
                continue
            if price[i] < price[j] and rsi_v[i] > rsi_v[j]:
                # don't override if a bearish short fired same bar (rare)
                if sig[i] == 0.0:
                    sig[i] = +1.0

    return pd.Series(sig, index=close.index, name="sig_raw")


def expand_to_hold(sig_raw: pd.Series, H: int) -> pd.Series:
    """Convert sparse trigger series (-1/0/+1 at swing bar) to a position
    series that holds for H bars starting NEXT bar (no look-ahead).
    Overlapping signals are SUMMED, then clipped to +/-1 (so a flip just
    flips, doesn't double).
    """
    n = len(sig_raw)
    pos = np.zeros(n, dtype=float)
    raw = sig_raw.values
    for i in range(n):
        s = raw[i]
        if s == 0.0:
            continue
        a = i + 1
        b = min(i + 1 + H, n)
        pos[a:b] += s
    pos = np.clip(pos, -1.0, 1.0)
    return pd.Series(pos, index=sig_raw.index, name="pos")


# -----------------------------------------------------------------------------
# PnL helpers
# -----------------------------------------------------------------------------
def bar_pnl(close: pd.Series, pos: pd.Series, cost_rt: float) -> pd.Series:
    """PnL per bar: pos_t * (close_{t+1}/close_t - 1) - turnover_cost.
    pos is already next-bar-applied (built that way) -> use pos.shift(0) * ret.
    Costs are charged on |delta pos| (round-trip is two sides => cost_rt per
    full flat-to-+1-to-flat cycle).
    """
    ret = close.pct_change().shift(-1)        # ret over [t, t+1]
    pnl = pos * ret
    turnover = pos.diff().abs().fillna(pos.abs().iloc[0] if len(pos) else 0)
    # per-side cost is cost_rt / 2.
    pnl = pnl - turnover * (cost_rt / 2.0)
    return pnl.fillna(0.0)


def sharpe(pnl: pd.Series) -> float:
    if len(pnl) < 10:
        return 0.0
    s = pnl.std(ddof=0)
    if s == 0:
        return 0.0
    return float(pnl.mean() / s * np.sqrt(BARS_PER_YEAR))


def equity_curve(pnl: pd.Series) -> pd.Series:
    return (1.0 + pnl).cumprod()


def max_drawdown(eq: pd.Series) -> float:
    if len(eq) < 2:
        return 0.0
    peak = eq.cummax()
    return float((eq / peak - 1.0).min())


def annualised_return(eq: pd.Series) -> float:
    if len(eq) < 2 or eq.iloc[-1] <= 0:
        return 0.0
    years = (eq.index[-1] - eq.index[0]).total_seconds() / (365.25 * 86400)
    if years <= 0:
        return 0.0
    return float(eq.iloc[-1] ** (1.0 / years) - 1.0)


def deflated_sharpe(observed_sr: float, n_trials: int, n_obs: int) -> float:
    if n_trials <= 1 or n_obs < 20:
        return 0.0
    emc = 0.5772156649
    e_max = ((1 - emc) * stats.norm.ppf(1 - 1.0 / n_trials)
             + emc * stats.norm.ppf(1 - 1.0 / (n_trials * np.e)))
    se = math.sqrt(1.0 / (n_obs - 1))
    z = (observed_sr - e_max * se) / se
    return float(stats.norm.cdf(z))


# -----------------------------------------------------------------------------
# Variant backtest
# -----------------------------------------------------------------------------
def backtest_variant(symbols: List[str], data: Dict[str, pd.DataFrame],
                     mode: str, H: int,
                     cost_rt: float = COST_ROUNDTRIP
                     ) -> Tuple[pd.Series, Dict[str, pd.Series], Dict[str, int]]:
    """Returns (portfolio_pnl, per_sym_pnl, per_sym_trigger_count)."""
    per_sym: Dict[str, pd.Series] = {}
    counts: Dict[str, int] = {}
    for s in symbols:
        df = data[s]
        close = df["close"].astype(float)
        if len(close) < 200:
            continue
        raw = build_signal(close, mode=mode)
        pos = expand_to_hold(raw, H)
        pnl = bar_pnl(close, pos, cost_rt)
        per_sym[s] = pnl
        counts[s] = int((raw != 0).sum())
    if not per_sym:
        return pd.Series(dtype=float), {}, {}
    df_pnl = pd.concat(per_sym, axis=1).fillna(0.0)
    port = df_pnl.mean(axis=1)
    return port, per_sym, counts


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
            "ret_total": float((1 + seg).prod() - 1),
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
        sd = sample.std(ddof=0)
        boots[b] = 0.0 if sd == 0 else sample.mean() / sd * np.sqrt(BARS_PER_YEAR)
    lo, hi = np.quantile(boots, [0.025, 0.975])
    return {"mean": float(boots.mean()),
            "ci_lo": float(lo), "ci_hi": float(hi)}


def permutation_test(per_sym_pnl: Dict[str, pd.Series],
                     per_sym_pos: Dict[str, pd.Series],
                     per_sym_close: Dict[str, pd.Series],
                     observed_sharpe: float,
                     cost_rt: float,
                     n_perm: int = N_PERM) -> Dict:
    """For each permutation: independently sign-shuffle (block-permute) the
    position series of each symbol, then rebuild PnL. If the divergence rule
    has no edge, the sign assignments are exchangeable, so this is a valid
    one-sided test of `mean PnL > 0`.
    """
    syms = list(per_sym_pos.keys())
    if not syms:
        return {"p_value": 1.0, "null_mean": 0.0, "null_std": 0.0,
                "null_q95": 0.0, "observed": observed_sharpe}

    # pre-extract numpy arrays
    pos_arrs = {s: per_sym_pos[s].values.copy() for s in syms}
    ret_arrs = {s: per_sym_close[s].pct_change().shift(-1).fillna(0.0).values
                for s in syms}
    idx0 = per_sym_pos[syms[0]].index
    nulls = np.empty(n_perm)
    block = BOOT_BLOCK

    # Align everything to the union timeline by reindexing Series
    union_idx = per_sym_pos[syms[0]].index
    for s in syms[1:]:
        union_idx = union_idx.union(per_sym_pos[s].index)
    aligned_pos = {s: per_sym_pos[s].reindex(union_idx).fillna(0.0).values
                   for s in syms}
    aligned_ret = {s: per_sym_close[s].reindex(union_idx).pct_change()
                   .shift(-1).fillna(0.0).values for s in syms}
    N = len(union_idx)

    for p in range(n_perm):
        port_components = np.zeros((len(syms), N), dtype=float)
        for k, s in enumerate(syms):
            pos = aligned_pos[s]
            ret = aligned_ret[s]
            n_blocks = (N // block) + 1
            starts = RNG.integers(0, max(1, N - block + 1), size=n_blocks)
            shuf = np.concatenate([pos[st:st + block] for st in starts])[:N]
            pnl = shuf * ret
            d = np.abs(np.diff(shuf, prepend=0.0))
            pnl = pnl - d * (cost_rt / 2.0)
            port_components[k, :] = pnl
        port = port_components.mean(axis=0)
        sd = port.std(ddof=0)
        nulls[p] = 0.0 if sd == 0 else port.mean() / sd * np.sqrt(BARS_PER_YEAR)

    p_val = float((nulls >= observed_sharpe).mean())
    return {
        "p_value": p_val,
        "null_mean": float(nulls.mean()),
        "null_std": float(nulls.std()),
        "null_q95": float(np.quantile(nulls, 0.95)),
        "observed": float(observed_sharpe),
    }


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------
def main():
    t0 = time.time()
    print("[K147] start")
    all_syms = list_symbols()
    print(f"  candidate symbols: {len(all_syms)}")
    universe = select_top_liquid(all_syms, top_n=15)
    print(f"  universe (top-15 liquid, non-meme): {universe}")

    data: Dict[str, pd.DataFrame] = {}
    for s in universe:
        try:
            data[s] = load_bars(s)
        except Exception as e:
            print(f"   ! load fail {s}: {e}")
    print(f"  loaded: {len(data)} symbols, t={time.time()-t0:.1f}s")

    variants = {
        "V_bearish_only_h12": ("bearish", 12),
        "V_long_short_h12":   ("both",    12),
        "V_bearish_h6":       ("bearish",  6),
        "V_bearish_h24":      ("bearish", 24),
    }

    out_summary: Dict[str, Dict] = {}
    out_curves: Dict[str, Dict] = {}

    for vname, (mode, H) in variants.items():
        tv = time.time()
        print(f"\n[{vname}] mode={mode} H={H}")
        port, per_sym_pnl, counts = backtest_variant(universe, data, mode, H,
                                                    COST_ROUNDTRIP)
        if len(port) == 0:
            print("  no data")
            continue

        # Build per-symbol pos series for permutation
        per_sym_pos = {}
        per_sym_close = {}
        for s in universe:
            if s not in per_sym_pnl:
                continue
            close = data[s]["close"].astype(float)
            raw = build_signal(close, mode=mode)
            pos = expand_to_hold(raw, H)
            per_sym_pos[s] = pos
            per_sym_close[s] = close

        # IS / OOS split
        n = len(port)
        n_oos = int(n * OOS_FRAC)
        is_pnl = port.iloc[:-n_oos]
        oos_pnl = port.iloc[-n_oos:]

        full_eq = equity_curve(port)
        is_eq = equity_curve(is_pnl)
        oos_eq = equity_curve(oos_pnl)

        sr_full = sharpe(port)
        sr_is = sharpe(is_pnl)
        sr_oos = sharpe(oos_pnl)
        mdd_full = max_drawdown(full_eq)
        mdd_oos = max_drawdown(oos_eq)
        ann_full = annualised_return(full_eq)
        ann_oos = annualised_return(oos_eq)

        per_sym_sr = {s: sharpe(p) for s, p in per_sym_pnl.items()}

        # WF
        wf = walk_forward(port)

        # Bootstrap
        boot = block_bootstrap(port)

        # Permutation
        print(f"  permutation n={N_PERM} ...")
        perm = permutation_test(per_sym_pnl, per_sym_pos, per_sym_close,
                                sr_full, COST_ROUNDTRIP)

        # DSR
        dsr = deflated_sharpe(sr_full, n_trials=4, n_obs=len(port))

        # Cost stress
        cost_stress = {}
        for factor in (0.5, 1.0, 1.5):
            cs = COST_ROUNDTRIP * factor
            port_cs, _, _ = backtest_variant(universe, data, mode, H, cs)
            cost_stress[f"cost_x{factor}"] = {
                "cost_rt": cs,
                "sharpe": sharpe(port_cs),
                "ann_ret": annualised_return(equity_curve(port_cs)),
            }

        det_total = int(sum(counts.values()))
        det_per_sym_yr = (det_total / len(universe)) / 2.0  # ~730d = 2 yr
        det_per_sym = {s: counts.get(s, 0) for s in universe}

        out_summary[vname] = {
            "mode": mode,
            "hold_bars": H,
            "n_bars": int(n),
            "n_symbols": len(per_sym_pnl),
            "detection": {
                "total_triggers": det_total,
                "per_symbol": det_per_sym,
                "avg_per_symbol_per_year": det_per_sym_yr,
            },
            "is_oos": {
                "sharpe_full": sr_full,
                "sharpe_is": sr_is,
                "sharpe_oos": sr_oos,
                "mdd_full": mdd_full,
                "mdd_oos": mdd_oos,
                "ann_ret_full": ann_full,
                "ann_ret_oos": ann_oos,
            },
            "per_symbol_sharpe": per_sym_sr,
            "walk_forward": wf,
            "block_bootstrap": boot,
            "permutation": perm,
            "deflated_sharpe": dsr,
            "cost_stress": cost_stress,
        }

        out_curves[vname] = {
            "timestamps": [str(t) for t in port.index],
            "portfolio_pnl": port.tolist(),
            "portfolio_equity": full_eq.tolist(),
            "is_eq_last": float(is_eq.iloc[-1]) if len(is_eq) else 1.0,
            "oos_eq_last": float(oos_eq.iloc[-1]) if len(oos_eq) else 1.0,
        }

        print(f"  Sharpe full={sr_full:.3f} IS={sr_is:.3f} OOS={sr_oos:.3f}")
        print(f"  AnnRet full={ann_full*100:.2f}% OOS={ann_oos*100:.2f}%")
        print(f"  MDD  full={mdd_full*100:.2f}% OOS={mdd_oos*100:.2f}%")
        print(f"  triggers total={det_total}, avg/sym/yr={det_per_sym_yr:.1f}")
        print(f"  WF Sharpes: {[round(w['sharpe'],3) for w in wf]}")
        print(f"  Boot CI Sharpe: [{boot['ci_lo']:.3f},{boot['ci_hi']:.3f}]")
        print(f"  Perm p-value: {perm['p_value']:.4f} (null mean={perm['null_mean']:.3f})")
        print(f"  DSR: {dsr:.4f}")
        print(f"  variant time: {time.time()-tv:.1f}s")

    out = {
        "wave": "K147",
        "title": "Hidden Bearish/Bullish RSI Divergence at 4H",
        "asof": pd.Timestamp.utcnow().isoformat(),
        "params": {
            "RSI_LEN": RSI_LEN,
            "SWING_W": SWING_W,
            "LOOKBACK_BARS": LOOKBACK_BARS,
            "COST_ROUNDTRIP": COST_ROUNDTRIP,
            "BARS_PER_YEAR": BARS_PER_YEAR,
            "OOS_FRAC": OOS_FRAC,
            "WF_FOLDS": WF_FOLDS,
            "N_PERM": N_PERM,
            "N_BOOT": N_BOOT,
            "BOOT_BLOCK": BOOT_BLOCK,
            "MEME_BLACKLIST": sorted(MEME_BLACKLIST),
        },
        "universe": universe,
        "variants": out_summary,
    }

    with open(BASE / "wave_k147_rsi_div.json", "w") as fp:
        json.dump(out, fp, indent=2, default=str)
    with open(BASE / "wave_k147_curves.json", "w") as fp:
        json.dump(out_curves, fp, default=str)

    # ---- §6 mini-gates ----
    print("\n========= §6 mini-gates =========")
    for vname, s in out_summary.items():
        sr_full = s["is_oos"]["sharpe_full"]
        sr_oos  = s["is_oos"]["sharpe_oos"]
        mdd_oos = s["is_oos"]["mdd_oos"]
        p_val   = s["permutation"]["p_value"]
        dsr     = s["deflated_sharpe"]
        wf_pos  = sum(1 for w in s["walk_forward"] if w["sharpe"] > 0)
        gates = {
            "G1 full Sharpe >= 0.5":      sr_full >= 0.5,
            "G2 OOS  Sharpe >= 0.3":      sr_oos  >= 0.3,
            "G3 OOS  MDD    >= -0.30":    mdd_oos >= -0.30,
            "G4 perm p-value < 0.05":     p_val   < 0.05,
            "G5 DSR > 0.90":              dsr     >  0.90,
            "G6 WF positive folds >= 3":  wf_pos  >= 3,
        }
        passes = sum(gates.values())
        verdict = "PASS" if passes >= 5 else ("PARTIAL" if passes >= 3 else "FAIL")
        print(f"\n[{vname}] gates pass {passes}/6 -> {verdict}")
        for k, v in gates.items():
            print(f"   {k:35s} {'OK' if v else 'NO'}")

    print(f"\n[K147] total wall: {time.time()-t0:.1f}s")
    print(f"outputs:\n  {BASE/'wave_k147_rsi_div.json'}\n  {BASE/'wave_k147_curves.json'}")


if __name__ == "__main__":
    main()
