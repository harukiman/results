"""Wave K141 — Funding Sign Cluster >= 80% Contrarian (R5-18).

Hypothesis (Coinbase Institutional):
  When >= 80% of 15 perp symbols all have the same funding sign, the market is
  "crowded one-sided" — contrarian fade signal.
    - >= 80% with POSITIVE funding -> everyone is long, fade by going SHORT a basket
    - >= 80% with NEGATIVE funding -> everyone is short, fade by going LONG

Method:
  1. Per 8h funding event:
       fraction_positive_t = count(funding > 0 across 15 syms) / 15
     Lag 1 event so we never peek.
  2. Signal:
       if fraction_positive >= thr_hi -> SHORT basket (BTC + ETH + SOL equal weight)
       if fraction_positive <= thr_lo (= 1 - thr_hi) -> LONG basket
       else flat
  3. Hold: 1 day = 3 funding events (24h / 8h) -OR- until next non-flat signal.
  4. Costs: 0.07% per side per leg (= 7 bps).

Variants:
  - V_thresh_80: 80%  threshold (hi=0.80, lo=0.20)
  - V_thresh_90: 90%  threshold (stricter, fewer trades)
  - V_thresh_70: 70%  threshold (looser)
  - V_z_score:   z-score of fraction_positive over 30d (= 90 funding events),
                 |z| > 1.5 contrarian (positive z -> SHORT, negative -> LONG)

Audit:
  - 730d, IS 70% / OOS 30%
  - Portfolio Sharpe
  - WF 4-fold
  - One-sided permutation n=300 (shuffle signal sign-time)
  - Block bootstrap n=300
  - DSR N_trials=4
  - Cost stress x0.5/x1.0/x1.5/x2.0

Output:
  wave_k141_fund_cluster.{py,json}
  wave_k141_curves.json
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

ROOT = Path("/Users/nekonaomichi/crypto-lab")
CACHE = ROOT / "cache"
OUT_DIR = ROOT

# ----------------------------------------------------------------------------
# Universe (15 perp symbols)
# Direct symbol -> (FR file token, Price file token)
# BONK and SHIB are special: BONK FR is published as 1000BONK on Bybit, and we
# substitute SHIB with PEPE because no SHIB FR cache exists at 730d (we DO have
# 1000PEPE FR + PEPE price).  Funding sign is what matters; the 1000x notional
# multiplier does NOT change the sign or the per-unit-notional rate, so this
# is a valid mapping for THIS strategy (sign-based, not magnitude-based).
SYMS: List[Tuple[str, str, str]] = [
    # (label,         fr_token,         price_token)
    ("BTC",   "BTCUSDT",        "BTCUSDT"),
    ("ETH",   "ETHUSDT",        "ETHUSDT"),
    ("SOL",   "SOLUSDT",        "SOLUSDT"),
    ("BNB",   "BNBUSDT",        "BNBUSDT"),
    ("DOGE",  "DOGEUSDT",       "DOGEUSDT"),
    ("AVAX",  "AVAXUSDT",       "AVAXUSDT"),
    ("LINK",  "LINKUSDT",       "LINKUSDT"),
    ("ADA",   "ADAUSDT",        "ADAUSDT"),
    ("XRP",   "XRPUSDT",        "XRPUSDT"),
    ("INJ",   "INJUSDT",        "INJUSDT"),
    ("OP",    "OPUSDT",         "OPUSDT"),
    ("WIF",   "WIFUSDT",        "WIFUSDT"),
    ("ARB",   "ARBUSDT",        "ARBUSDT"),
    ("BONK",  "1000BONKUSDT",   "BONKUSDT"),
    ("SHIB*", "1000PEPEUSDT",   "PEPEUSDT"),   # substituted (see note)
]

BASKET = ["BTC", "ETH", "SOL"]
COST_BPS_PER_LEG = 7.0
IS_FRAC = 0.70
EVENTS_PER_DAY = 3
EVENTS_PER_YEAR = 3 * 365
RNG_SEED = 42
N_PERM = 300
N_BOOT = 300
N_TRIALS_DSR = 4
WF_FOLDS = 4

t0 = time.time()


def log(msg: str) -> None:
    print(f"[{time.time() - t0:6.1f}s] {msg}", flush=True)


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------
def load_funding(fr_token: str) -> pd.Series:
    """Load 8h funding events for a single symbol -> Series indexed by event ts."""
    df = pd.read_parquet(CACHE / f"bybit_fr_{fr_token}_730d.parquet")
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp").drop_duplicates("timestamp")
    return df.set_index("timestamp")["funding_rate"]


def load_price_4h(price_token: str) -> pd.Series:
    df = pd.read_parquet(CACHE / f"{price_token}_4h_730d.parquet")
    df["open_time"] = pd.to_datetime(df["open_time"])
    df = df.sort_values("open_time").drop_duplicates("open_time")
    return df.set_index("open_time")["close"]


def build_funding_panel() -> pd.DataFrame:
    """DataFrame (event_ts x sym) of 8h funding rates."""
    pieces = []
    for label, fr_token, _ in SYMS:
        s = load_funding(fr_token)
        s.name = label
        pieces.append(s)
    df = pd.concat(pieces, axis=1).sort_index()
    # Keep only rows where ALL 15 syms have data (start a few days late if needed)
    df = df.dropna(how="any")
    return df


def build_basket_returns(funding_index: pd.DatetimeIndex) -> pd.DataFrame:
    """Aggregate 4h price returns onto 8h funding event grid.

    Each event_ts t covers the 8h FORWARD window [t, t+8h).  We compute the
    log-return of each basket asset across that 8h window (= 2 four-hour bars).
    Returned DataFrame is indexed by funding_index and has columns = BASKET syms.
    Last event window may be partial (trimmed by data availability).
    """
    out = {}
    for sym in BASKET:
        label_match = next((s for s in SYMS if s[0] == sym), None)
        price_token = label_match[2]
        px = load_price_4h(price_token)
        # Forward 8h log-return aligned to event_ts t = log(px[t+8h] / px[t])
        # Find for each event_ts t the close at t and the close at t+8h.
        ret_series = pd.Series(index=funding_index, dtype=float)
        # Use asof on px.index
        for t in funding_index:
            t_plus = t + pd.Timedelta(hours=8)
            try:
                p0 = px.asof(t)
                p1 = px.asof(t_plus)
                if pd.notna(p0) and pd.notna(p1) and p0 > 0:
                    ret_series.loc[t] = float(np.log(p1 / p0))
            except Exception:
                pass
        out[sym] = ret_series
    return pd.DataFrame(out)


def build_basket_funding(funding_panel: pd.DataFrame) -> pd.DataFrame:
    """Per-event funding for each BASKET symbol."""
    return funding_panel[BASKET].copy()


# ---------------------------------------------------------------------------
# Signal generators
# ---------------------------------------------------------------------------
def signal_threshold(funding_panel: pd.DataFrame, thr_hi: float) -> pd.Series:
    """+1 = LONG basket (oversold/everyone short), -1 = SHORT basket (crowded long), 0 = flat."""
    thr_lo = 1.0 - thr_hi
    frac_pos = (funding_panel > 0).sum(axis=1) / funding_panel.shape[1]
    raw = pd.Series(0, index=funding_panel.index, dtype=int)
    raw[frac_pos >= thr_hi] = -1  # crowded long -> SHORT
    raw[frac_pos <= thr_lo] = +1  # crowded short -> LONG
    return raw, frac_pos


def signal_zscore(funding_panel: pd.DataFrame, lookback: int = 90, z_thr: float = 1.5):
    """z-score of fraction_positive over rolling 30d (=90 events).
    Contrarian: z > +z_thr -> SHORT (positive crowd), z < -z_thr -> LONG.
    """
    frac_pos = (funding_panel > 0).sum(axis=1) / funding_panel.shape[1]
    mu = frac_pos.rolling(lookback, min_periods=lookback).mean()
    sd = frac_pos.rolling(lookback, min_periods=lookback).std(ddof=1)
    z = (frac_pos - mu) / sd
    raw = pd.Series(0, index=funding_panel.index, dtype=int)
    raw[z >= z_thr] = -1
    raw[z <= -z_thr] = +1
    return raw, frac_pos


# ---------------------------------------------------------------------------
# Trade construction & PnL
# ---------------------------------------------------------------------------
def hold_signal(raw_sig: pd.Series, hold_events: int = 3) -> pd.Series:
    """Latch signal for hold_events events OR until a new non-zero signal appears.

    Behavior:
      - At each event t:
          if raw_sig[t] != 0: enter that side (overrides any prior position).
          else if currently holding and remaining_hold > 0: keep current pos.
          else: flat.
    """
    held = np.zeros(len(raw_sig), dtype=int)
    cur = 0
    remain = 0
    arr = raw_sig.values
    for t in range(len(arr)):
        new = arr[t]
        if new != 0:
            cur = new
            remain = hold_events
        elif remain > 0:
            remain -= 1
            # remain decremented; cur stays unless it reaches 0
            if remain == 0:
                cur = 0
        else:
            cur = 0
        held[t] = cur
    return pd.Series(held, index=raw_sig.index, dtype=int)


def lag_signal(sig: pd.Series, lag: int = 1) -> pd.Series:
    """Lag by `lag` events to avoid look-ahead."""
    return sig.shift(lag).fillna(0).astype(int)


def run_variant(funding_panel: pd.DataFrame,
                basket_ret: pd.DataFrame,
                basket_fund: pd.DataFrame,
                signal_fn,
                hold_events: int = 3) -> Dict[str, object]:
    raw, frac_pos = signal_fn(funding_panel)
    held = hold_signal(raw, hold_events=hold_events)
    sig_lagged = lag_signal(held, lag=1)

    # Equal-weight basket exposure: |w_per_leg| = 1/len(BASKET) (gross 1.0)
    n_leg = len(BASKET)
    leg_w = sig_lagged.astype(float) / n_leg  # positive -> long each leg; negative -> short

    # Per-event PnL across basket (sum across legs)
    # price_pnl_t = sum_i leg_w_t * basket_ret_t[i]
    aligned = basket_ret.loc[sig_lagged.index].fillna(0.0)
    price_pnl = aligned.mul(leg_w, axis=0).sum(axis=1)

    # Funding cost: if we are SHORT, we PAY funding (when funding>0 -> -PnL),
    # if we are LONG, we RECEIVE funding (when funding>0 -> +PnL).
    # Per leg pnl_funding_t = -leg_w_t * basket_fund_t[i]  (because short pays positive fund)
    # but leg_w already carries sign of position. The funding payment occurs at event t
    # for the position you hold INTO event t. With sig_lagged = held.shift(1), the
    # weight applied for event t corresponds to the position established at t-1 and
    # held through the 8h window ending at t -> that position pays/receives at t.
    fund_aligned = basket_fund.loc[sig_lagged.index].fillna(0.0)
    funding_pnl = (-fund_aligned).mul(leg_w, axis=0).sum(axis=1)

    # Transaction cost: when leg_w changes -> trade.
    dw = leg_w.diff().abs().fillna(leg_w.abs())  # entry from 0 also costs
    # Each event the WHOLE basket (n_leg legs) trades together when weight changes:
    # cost = |dw| * n_leg * cost_bps_per_leg  (because dw is PER-LEG)
    cost = dw * n_leg * (COST_BPS_PER_LEG / 1e4)

    pnl_gross = price_pnl + funding_pnl
    pnl_net = pnl_gross - cost

    return {
        "raw_signal": raw,
        "held_signal": held,
        "lagged_signal": sig_lagged,
        "leg_weight": leg_w,
        "frac_pos": frac_pos,
        "price_pnl": price_pnl.fillna(0.0),
        "funding_pnl": funding_pnl.fillna(0.0),
        "cost": cost.fillna(0.0),
        "pnl_gross": pnl_gross.fillna(0.0),
        "pnl_net": pnl_net.fillna(0.0),
        "hold_events": hold_events,
    }


# ---------------------------------------------------------------------------
# Stats helpers
# ---------------------------------------------------------------------------
def sharpe(x: np.ndarray) -> float:
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    if len(x) < 5:
        return 0.0
    sd = x.std(ddof=1)
    if sd == 0:
        return 0.0
    return float(x.mean() / sd * np.sqrt(EVENTS_PER_YEAR))


def max_dd(pnl: np.ndarray) -> float:
    eq = np.cumsum(pnl)
    if len(eq) == 0:
        return 0.0
    peak = np.maximum.accumulate(eq)
    return float((eq - peak).min())


def total_ret(pnl: np.ndarray) -> float:
    return float(np.sum(pnl))


def winrate(pnl: np.ndarray) -> float:
    pnl = pnl[pnl != 0]
    if len(pnl) == 0:
        return 0.0
    return float((pnl > 0).mean())


def block_bootstrap_sharpe(pnl: np.ndarray, n: int, block: int, seed: int) -> Dict:
    rng = np.random.default_rng(seed)
    T = len(pnl)
    if T < block:
        return {"mean": 0.0, "ci_lo": 0.0, "ci_hi": 0.0}
    n_blocks = max(1, int(np.ceil(T / block)))
    boots = np.empty(n)
    for k in range(n):
        starts = rng.integers(0, T - block + 1, size=n_blocks)
        chunks = [pnl[s:s + block] for s in starts]
        sample = np.concatenate(chunks)[:T]
        boots[k] = sharpe(sample)
    return {
        "mean": float(boots.mean()),
        "ci_lo": float(np.percentile(boots, 2.5)),
        "ci_hi": float(np.percentile(boots, 97.5)),
    }


def dsr(observed_sh: float, pnl: np.ndarray, n_trials: int) -> float:
    from math import sqrt, log as ln
    from scipy.stats import norm
    x = pnl[pnl != 0]
    T = len(x)
    if T < 30:
        return 0.0
    skew = float(pd.Series(x).skew())
    kurt = float(pd.Series(x).kurt())
    sh_per = observed_sh / np.sqrt(EVENTS_PER_YEAR)
    emc = 0.5772156649
    n_trials = max(n_trials, 2)
    e_max = (sqrt(2 * ln(n_trials)) * (1 - emc / sqrt(2 * ln(n_trials))) +
             emc / sqrt(2 * ln(n_trials)))
    threshold = e_max / sqrt(T)
    var_sr = (1 - skew * sh_per + (kurt / 4.0) * sh_per ** 2) / max(T - 1, 1)
    if var_sr <= 0:
        return 0.5
    z = (sh_per - threshold) / sqrt(var_sr)
    return float(norm.cdf(z))


def permutation_pvalue(funding_panel, basket_ret, basket_fund,
                       signal_fn, hold_events: int,
                       observed: float, n: int, seed: int) -> Dict[str, float]:
    """Permutation: randomly shuffle the sign of the raw signal time series.

    This destroys the relationship between cluster events and forward returns
    while preserving the SIGNAL DISTRIBUTION (same number of +1/-1/0 events,
    same hold structure on average)."""
    rng = np.random.default_rng(seed)
    raw, _ = signal_fn(funding_panel)
    raw_arr = raw.values

    perms = np.empty(n)
    aligned_ret = basket_ret.loc[raw.index].fillna(0.0).values
    aligned_fund = basket_fund.loc[raw.index].fillna(0.0).values
    n_leg = len(BASKET)

    for k in range(n):
        perm = raw_arr.copy()
        rng.shuffle(perm)
        held = _hold_arr(perm, hold_events)
        sig_lag = np.concatenate([[0], held[:-1]])
        leg_w = sig_lag.astype(float) / n_leg
        price = (aligned_ret * leg_w[:, None]).sum(axis=1)
        fund = (-aligned_fund * leg_w[:, None]).sum(axis=1)
        dw = np.abs(np.concatenate([[leg_w[0]], np.diff(leg_w)]))
        cost = dw * n_leg * (COST_BPS_PER_LEG / 1e4)
        pnl = price + fund - cost
        perms[k] = sharpe(pnl)

    p = float((np.sum(perms >= observed) + 1) / (len(perms) + 1))
    return {
        "p": p,
        "perm_mean": float(np.mean(perms)),
        "perm_p5": float(np.percentile(perms, 5)),
        "perm_p95": float(np.percentile(perms, 95)),
    }


def _hold_arr(raw: np.ndarray, hold_events: int) -> np.ndarray:
    held = np.zeros(len(raw), dtype=int)
    cur = 0
    remain = 0
    for t in range(len(raw)):
        new = raw[t]
        if new != 0:
            cur = new
            remain = hold_events
        elif remain > 0:
            remain -= 1
            if remain == 0:
                cur = 0
        else:
            cur = 0
        held[t] = cur
    return held


def walk_forward(funding_panel, basket_ret, basket_fund, signal_fn,
                 hold_events: int, n_folds: int) -> List[Dict]:
    T = len(funding_panel)
    fold_sz = T // (n_folds + 1)
    res = []
    for f in range(n_folds):
        train_end = fold_sz * (f + 1)
        test_end = min(T, fold_sz * (f + 2))
        if test_end - train_end < 30:
            continue
        # For threshold variants there is no fit; for z-score variant we need
        # the rolling lookback to be present.  Use the FULL preceding history
        # so the rolling stats are warm but ONLY evaluate over [train_end:test_end].
        fund_full = funding_panel.iloc[:test_end]
        ret_full = basket_ret.iloc[:test_end]
        fr_full = basket_fund.iloc[:test_end]
        out = run_variant(fund_full, ret_full, fr_full, signal_fn, hold_events=hold_events)
        n_test = test_end - train_end
        pnl = out["pnl_net"].iloc[-n_test:].values
        res.append({
            "fold": f,
            "n": int(len(pnl)),
            "sharpe": sharpe(pnl),
            "total_ret": total_ret(pnl),
            "max_dd": max_dd(pnl),
        })
    return res


def cost_stress(funding_panel, basket_ret, basket_fund, signal_fn,
                hold_events: int) -> Dict[str, float]:
    res = run_variant(funding_panel, basket_ret, basket_fund, signal_fn,
                      hold_events=hold_events)
    pnl_gross = res["pnl_gross"].values
    leg_w = res["leg_weight"].values
    n_leg = len(BASKET)
    dw = np.abs(np.concatenate([[leg_w[0]], np.diff(leg_w)]))
    out = {}
    for mult in [0.5, 1.0, 1.5, 2.0]:
        new_cost = dw * n_leg * (COST_BPS_PER_LEG * mult / 1e4)
        new_pnl = pnl_gross - new_cost
        out[f"cost_x{mult}"] = sharpe(new_pnl)
    return out


# ---------------------------------------------------------------------------
# Variant evaluator
# ---------------------------------------------------------------------------
def evaluate_variant(name: str, signal_fn, hold_events: int,
                     funding_panel, basket_ret, basket_fund,
                     n_trials_dsr: int) -> Tuple[Dict, Dict]:
    out = run_variant(funding_panel, basket_ret, basket_fund, signal_fn, hold_events=hold_events)
    pnl_net = out["pnl_net"].values
    pnl_gross = out["pnl_gross"].values
    price_pnl = out["price_pnl"].values
    funding_pnl = out["funding_pnl"].values
    cost = out["cost"].values

    T = len(pnl_net)
    is_end = int(T * IS_FRAC)
    pnl_is = pnl_net[:is_end]
    pnl_oos = pnl_net[is_end:]

    # Activity stats
    held = out["held_signal"].values
    lag = out["lagged_signal"].values
    n_active = int(np.sum(lag != 0))
    n_long = int(np.sum(lag == +1))
    n_short = int(np.sum(lag == -1))
    n_flips = int(np.sum(np.diff(lag) != 0))

    frac_pos = out["frac_pos"].values
    raw_sig = out["raw_signal"].values
    n_signal_long = int(np.sum(raw_sig == +1))
    n_signal_short = int(np.sum(raw_sig == -1))

    m = {
        "name": name,
        "n_events": int(T),
        "hold_events": hold_events,
        "n_raw_signal_long": n_signal_long,
        "n_raw_signal_short": n_signal_short,
        "n_held_active": n_active,
        "n_held_long": n_long,
        "n_held_short": n_short,
        "n_pos_flips": n_flips,
        "exposure_pct": float(n_active / T * 100.0),
        "frac_pos_mean": float(np.nanmean(frac_pos)),
        "frac_pos_p5":  float(np.nanpercentile(frac_pos, 5)),
        "frac_pos_p50": float(np.nanpercentile(frac_pos, 50)),
        "frac_pos_p95": float(np.nanpercentile(frac_pos, 95)),
        "full": {
            "sharpe": sharpe(pnl_net),
            "sharpe_gross": sharpe(pnl_gross),
            "max_dd": max_dd(pnl_net),
            "total_ret": total_ret(pnl_net),
            "winrate": winrate(pnl_net),
        },
        "is": {
            "sharpe": sharpe(pnl_is),
            "total_ret": total_ret(pnl_is),
            "max_dd": max_dd(pnl_is),
            "n": int(len(pnl_is)),
        },
        "oos": {
            "sharpe": sharpe(pnl_oos),
            "total_ret": total_ret(pnl_oos),
            "max_dd": max_dd(pnl_oos),
            "winrate": winrate(pnl_oos),
            "n": int(len(pnl_oos)),
        },
        "decomposition": {
            "sum_price_pnl": float(np.sum(price_pnl)),
            "sum_funding_pnl": float(np.sum(funding_pnl)),
            "sum_cost": float(np.sum(cost)),
            "sum_net": float(np.sum(pnl_net)),
        },
    }

    log(f"  [{name}] permutation test n={N_PERM}...")
    perm = permutation_pvalue(funding_panel, basket_ret, basket_fund,
                              signal_fn, hold_events,
                              observed=m["full"]["sharpe"], n=N_PERM, seed=RNG_SEED)
    m["perm_p"] = perm["p"]
    m["perm_null"] = {k: v for k, v in perm.items() if k != "p"}

    log(f"  [{name}] block bootstrap n={N_BOOT}...")
    bb = block_bootstrap_sharpe(pnl_oos, n=N_BOOT, block=21, seed=RNG_SEED)
    m["bootstrap_oos"] = bb

    log(f"  [{name}] DSR (n_trials={n_trials_dsr})...")
    m["dsr_oos"] = dsr(m["oos"]["sharpe"], pnl_oos, n_trials=n_trials_dsr)
    m["dsr_full"] = dsr(m["full"]["sharpe"], pnl_net, n_trials=n_trials_dsr)
    m["n_trials_dsr"] = n_trials_dsr

    log(f"  [{name}] walk-forward {WF_FOLDS}-fold...")
    wf = walk_forward(funding_panel, basket_ret, basket_fund, signal_fn,
                      hold_events=hold_events, n_folds=WF_FOLDS)
    m["wf_folds"] = wf
    if wf:
        m["wf_mean_sharpe"] = float(np.mean([f["sharpe"] for f in wf]))
        m["wf_min_sharpe"] = float(np.min([f["sharpe"] for f in wf]))

    log(f"  [{name}] cost stress...")
    m["cost_stress"] = cost_stress(funding_panel, basket_ret, basket_fund,
                                   signal_fn, hold_events=hold_events)

    g1 = m["oos"]["sharpe"] >= 1.0
    g2 = m["perm_p"] < 0.05
    g3 = m["dsr_oos"] >= 0.95
    m["gates"] = {
        "G1_oos_sharpe_ge_1": bool(g1),
        "G2_perm_p_lt_005": bool(g2),
        "G3_dsr_ge_095": bool(g3),
        "pass_all": bool(g1 and g2 and g3),
    }

    curve = {
        "timestamps": [t.isoformat() for t in out["pnl_net"].index],
        "pnl_net": out["pnl_net"].values.tolist(),
        "equity_net": np.cumsum(out["pnl_net"].values).tolist(),
        "price_pnl_cum": np.cumsum(price_pnl).tolist(),
        "funding_pnl_cum": np.cumsum(funding_pnl).tolist(),
        "cost_cum": np.cumsum(cost).tolist(),
        "frac_pos": np.nan_to_num(frac_pos, nan=0.0).tolist(),
        "raw_signal": raw_sig.tolist(),
        "lagged_signal": lag.tolist(),
        "is_end_idx": int(len(pnl_net) * IS_FRAC),
    }
    return m, curve


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    log(f"Loading panel for {len(SYMS)} symbols ...")
    fund_panel = build_funding_panel()
    log(f"funding panel: {fund_panel.shape[0]} events x {fund_panel.shape[1]} syms "
        f"({fund_panel.index.min()} .. {fund_panel.index.max()})")

    log("Building basket 8h forward returns for BTC, ETH, SOL ...")
    basket_ret = build_basket_returns(fund_panel.index)
    basket_fund = build_basket_funding(fund_panel)
    log(f"basket_ret: shape={basket_ret.shape}, nan_frac={basket_ret.isna().mean().mean():.4f}")

    # Cluster regime frequency (descriptive)
    frac_pos = (fund_panel > 0).sum(axis=1) / fund_panel.shape[1]
    regime_freq = {
        "frac_ge_70": float((frac_pos >= 0.70).mean()),
        "frac_ge_80": float((frac_pos >= 0.80).mean()),
        "frac_ge_90": float((frac_pos >= 0.90).mean()),
        "frac_le_30": float((frac_pos <= 0.30).mean()),
        "frac_le_20": float((frac_pos <= 0.20).mean()),
        "frac_le_10": float((frac_pos <= 0.10).mean()),
        "frac_pos_mean":  float(frac_pos.mean()),
        "frac_pos_p50":   float(frac_pos.quantile(0.50)),
        "frac_pos_p05":   float(frac_pos.quantile(0.05)),
        "frac_pos_p95":   float(frac_pos.quantile(0.95)),
    }
    log(f"Regime freq @ 80%+: {regime_freq['frac_ge_80']*100:.2f}%; "
        f"@ 90%+: {regime_freq['frac_ge_90']*100:.2f}%; "
        f"@ 70%+: {regime_freq['frac_ge_70']*100:.2f}%")

    variants = [
        ("V_thresh_80", lambda fp: signal_threshold(fp, 0.80)),
        ("V_thresh_90", lambda fp: signal_threshold(fp, 0.90)),
        ("V_thresh_70", lambda fp: signal_threshold(fp, 0.70)),
        ("V_z_score",   lambda fp: signal_zscore(fp, lookback=90, z_thr=1.5)),
    ]

    results = []
    curves = {}
    for name, fn in variants:
        log(f"--- variant {name} ---")
        m, curve = evaluate_variant(name, fn, hold_events=3,
                                    funding_panel=fund_panel,
                                    basket_ret=basket_ret,
                                    basket_fund=basket_fund,
                                    n_trials_dsr=N_TRIALS_DSR)
        log(f"   full Sh={m['full']['sharpe']:.3f}  OOS Sh={m['oos']['sharpe']:.3f}  "
            f"perm-p={m['perm_p']:.4f}  DSR-OOS={m['dsr_oos']:.3f}  "
            f"gates={'PASS' if m['gates']['pass_all'] else 'FAIL'}")
        results.append(m)
        curves[name] = curve

    summary = {
        "wave": "K141",
        "label": "Funding sign cluster >=80% contrarian (R5-18)",
        "hypothesis": (
            "When fraction_positive across 15 perp symbols is extreme (>=80% or "
            "<=20%), the market is one-sided; fade by going SHORT (resp. LONG) "
            "an equal-weight BTC+ETH+SOL basket."
        ),
        "universe_15": [s[0] for s in SYMS],
        "universe_map": [{"label": s[0], "fr_token": s[1], "price_token": s[2]} for s in SYMS],
        "basket": BASKET,
        "cost_bps_per_leg": COST_BPS_PER_LEG,
        "is_frac": IS_FRAC,
        "events_per_day": EVENTS_PER_DAY,
        "events_per_year": EVENTS_PER_YEAR,
        "n_events_total": int(fund_panel.shape[0]),
        "panel_start": fund_panel.index.min().isoformat(),
        "panel_end": fund_panel.index.max().isoformat(),
        "regime_freq": regime_freq,
        "n_perm": N_PERM,
        "n_boot": N_BOOT,
        "n_trials_dsr": N_TRIALS_DSR,
        "wf_folds": WF_FOLDS,
        "variants": results,
        "wall_seconds": time.time() - t0,
    }

    (OUT_DIR / "wave_k141_fund_cluster.json").write_text(
        json.dumps(summary, indent=2, default=str))
    (OUT_DIR / "wave_k141_curves.json").write_text(
        json.dumps(curves, default=str))

    log(f"done. wall: {time.time() - t0:.1f}s")
    print_markdown(summary)


def print_markdown(s: Dict) -> None:
    md = []
    md.append("# Wave K141 — Funding Sign Cluster >=80% Contrarian (R5-18)")
    md.append("")
    md.append(f"**Hypothesis:** {s['hypothesis']}")
    md.append("")
    md.append(f"**Universe (15):** {', '.join(s['universe_15'])}")
    md.append("  - Note: BONK uses 1000BONK FR (Bybit naming); SHIB* is "
              "substituted with PEPE because no SHIB FR cache exists at 730d. "
              "Funding-rate sign is what matters; the 1000x notional multiplier "
              "does NOT change the sign or per-unit rate.")
    md.append(f"**Basket (executed):** {' + '.join(s['basket'])} equal-weight")
    md.append(f"**Panel:** {s['n_events_total']} 8h events "
              f"({s['panel_start']} .. {s['panel_end']}), "
              f"IS {int(s['is_frac']*100)}% / OOS {int((1-s['is_frac'])*100)}%, "
              f"cost {s['cost_bps_per_leg']:.1f} bps/leg.")
    md.append("")
    md.append("## Cluster regime frequency")
    md.append("")
    rf = s["regime_freq"]
    md.append("| Slice | Frequency |")
    md.append("|---|---:|")
    md.append(f"| fraction_pos >= 90% | {rf['frac_ge_90']*100:.2f}% |")
    md.append(f"| fraction_pos >= 80% | {rf['frac_ge_80']*100:.2f}% |")
    md.append(f"| fraction_pos >= 70% | {rf['frac_ge_70']*100:.2f}% |")
    md.append(f"| fraction_pos <= 30% | {rf['frac_le_30']*100:.2f}% |")
    md.append(f"| fraction_pos <= 20% | {rf['frac_le_20']*100:.2f}% |")
    md.append(f"| fraction_pos <= 10% | {rf['frac_le_10']*100:.2f}% |")
    md.append(f"| mean fraction_pos   | {rf['frac_pos_mean']:.3f} |")
    md.append(f"| p05/p50/p95         | {rf['frac_pos_p05']:.3f} / "
              f"{rf['frac_pos_p50']:.3f} / {rf['frac_pos_p95']:.3f} |")
    md.append("")
    md.append("## Per-variant metrics")
    md.append("")
    md.append("| Variant | n_sig+ | n_sig- | held_exp% | Full Sh | Gross Sh | OOS Sh | "
              "OOS TotRet | Perm-p | DSR-OOS | WF mean Sh | Gates |")
    md.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|:--:|")
    for v in s["variants"]:
        g = v["gates"]
        gates_str = ("G1=" + ("P" if g["G1_oos_sharpe_ge_1"] else "F") +
                     " G2=" + ("P" if g["G2_perm_p_lt_005"] else "F") +
                     " G3=" + ("P" if g["G3_dsr_ge_095"] else "F"))
        wf_mean = v.get("wf_mean_sharpe", float("nan"))
        md.append(
            f"| {v['name']} | {v['n_raw_signal_long']} | {v['n_raw_signal_short']} | "
            f"{v['exposure_pct']:.1f} | {v['full']['sharpe']:.3f} | "
            f"{v['full']['sharpe_gross']:.3f} | {v['oos']['sharpe']:.3f} | "
            f"{v['oos']['total_ret']:+.4f} | {v['perm_p']:.4f} | "
            f"{v['dsr_oos']:.4f} | {wf_mean:.3f} | {gates_str} |"
        )
    md.append("")
    md.append("## Decomposition (per variant)")
    md.append("")
    md.append("| Variant | Sum Price | Sum Funding | Sum Cost | Sum Net |")
    md.append("|---|---:|---:|---:|---:|")
    for v in s["variants"]:
        d = v["decomposition"]
        md.append(f"| {v['name']} | {d['sum_price_pnl']:+.4f} | "
                  f"{d['sum_funding_pnl']:+.4f} | -{d['sum_cost']:.4f} | "
                  f"{d['sum_net']:+.4f} |")
    md.append("")
    md.append("## Walk-forward 4-fold OOS Sharpe (per fold)")
    md.append("")
    md.append("| Variant | F0 | F1 | F2 | F3 | mean | min |")
    md.append("|---|---:|---:|---:|---:|---:|---:|")
    for v in s["variants"]:
        wfs = v.get("wf_folds", [])
        sharpes = {f["fold"]: f["sharpe"] for f in wfs}
        vals = [sharpes.get(i, float("nan")) for i in range(4)]
        md.append(
            f"| {v['name']} | {vals[0]:.3f} | {vals[1]:.3f} | "
            f"{vals[2]:.3f} | {vals[3]:.3f} | "
            f"{v.get('wf_mean_sharpe', float('nan')):.3f} | "
            f"{v.get('wf_min_sharpe', float('nan')):.3f} |"
        )
    md.append("")
    md.append("## Cost stress (Full Sharpe at cost multiplier)")
    md.append("")
    md.append("| Variant | x0.5 | x1.0 | x1.5 | x2.0 |")
    md.append("|---|---:|---:|---:|---:|")
    for v in s["variants"]:
        cs = v["cost_stress"]
        md.append(f"| {v['name']} | {cs['cost_x0.5']:.3f} | {cs['cost_x1.0']:.3f} | "
                  f"{cs['cost_x1.5']:.3f} | {cs['cost_x2.0']:.3f} |")
    md.append("")
    md.append("## Bootstrap OOS Sharpe (95% CI, block=21)")
    md.append("")
    md.append("| Variant | mean | CI lo | CI hi |")
    md.append("|---|---:|---:|---:|")
    for v in s["variants"]:
        bb = v["bootstrap_oos"]
        md.append(f"| {v['name']} | {bb['mean']:.3f} | {bb['ci_lo']:.3f} | "
                  f"{bb['ci_hi']:.3f} |")
    md.append("")
    md.append("## §6 mini gates (per variant)")
    md.append("")
    md.append("| Variant | G1 OOS Sh>=1.0 | G2 Perm-p<0.05 | G3 DSR(OOS)>=0.95 | Pass all |")
    md.append("|---|:--:|:--:|:--:|:--:|")
    for v in s["variants"]:
        g = v["gates"]
        md.append(
            f"| {v['name']} | "
            f"{v['oos']['sharpe']:.3f} {'P' if g['G1_oos_sharpe_ge_1'] else 'F'} | "
            f"{v['perm_p']:.4f} {'P' if g['G2_perm_p_lt_005'] else 'F'} | "
            f"{v['dsr_oos']:.4f} {'P' if g['G3_dsr_ge_095'] else 'F'} | "
            f"{'YES' if g['pass_all'] else 'no'} |"
        )
    md.append("")
    md.append("## Verdict")
    md.append("")
    accepted = [v for v in s["variants"] if v["gates"]["pass_all"]]
    if accepted:
        names = ", ".join([v["name"] for v in accepted])
        md.append(f"**ACCEPT** the following variant(s): {names}. "
                  "Coinbase Institutional's crowded-funding contrarian hypothesis is "
                  "supported under 4-variant DSR adjustment with OOS Sharpe >=1.0 and "
                  "perm-p<0.05 on this 730d perp universe.")
    else:
        md.append("**DO NOT ACCEPT.** No variant passes all three §6 gates. "
                  "The crowded-funding contrarian hypothesis FAILS on this 730d "
                  "perp universe under the 4-variant DSR adjustment.")
        md.append("")
        md.append("Diagnostic notes:")
        # Best variant for context
        best = max(s["variants"], key=lambda v: v["oos"]["sharpe"])
        g = best["gates"]
        reasons = []
        if not g["G1_oos_sharpe_ge_1"]:
            reasons.append(f"best OOS Sharpe is only {best['oos']['sharpe']:.2f} "
                           f"({best['name']})")
        if not g["G2_perm_p_lt_005"]:
            reasons.append(f"best perm-p is {best['perm_p']:.3f}")
        if not g["G3_dsr_ge_095"]:
            reasons.append(f"best DSR(OOS) is {best['dsr_oos']:.3f}")
        md.append(f"  - {'; '.join(reasons)}.")
        # Regime base rate sanity
        rf = s["regime_freq"]
        md.append(f"  - Cluster regime is rare: only {rf['frac_ge_80']*100:.1f}% of "
                  f"events satisfy fraction_pos>=80%, "
                  f"{rf['frac_le_20']*100:.1f}% satisfy <=20% -> "
                  "limited trade count; may be a power issue rather than a "
                  "true-null rejection.")
        md.append("  - Funding is dominated by POSITIVE side: mean fraction_pos = "
                  f"{rf['frac_pos_mean']:.3f}; LONG-side ('crowded short' fade) is "
                  "essentially never triggered.")
    md.append("")
    md.append(f"Wall time: {s['wall_seconds']:.1f}s")
    print("\n".join(md))


if __name__ == "__main__":
    main()
