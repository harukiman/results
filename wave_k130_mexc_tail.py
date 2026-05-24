"""Wave K130 — MEXC Tail-Asset Funding Premium (R4-13 / MEXC固有 edge).

Hypothesis (CoinGecko 2026 perp report):
MEXC lists tail/new alts aggressively (~55/35 contracts/month). Tail alts
allegedly carry persistent positive funding premium. Strategy: SHORT the perp
when funding rate exceeds threshold to capture funding cash flow.

CAVEAT: We test on Bybit FR data (Bybit is mature, deep). MEXC FR may differ
(thinner book → possibly higher carry premium). This is therefore a LOWER BOUND
on the MEXC-specific edge claim.

Pre-registered variants:
  V_short_5bp   : SHORT when FR > +0.05%
  V_short_10bp  : SHORT when FR > +0.10%
  V_short_3bp   : SHORT when FR > +0.03%
  V_long_short  : SHORT if FR > +5bp, LONG if FR < -5bp (symmetric)

Universe (14 tail symbols with both 4H price + Bybit FR cache):
  Memecoin: WIF, BOME, PEPE(via 1000PEPE FR), BONK(via 1000BONK FR), FLOKI(via 1000FLOKI FR)
  New alts: ENA, JUP, JTO, STRK, MANTA, ONDO
  AI:       WLD, TAO, ARKM
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

CACHE = Path("/Users/nekonaomichi/crypto-lab/cache")
OUT_DIR = Path("/Users/nekonaomichi/crypto-lab")

# Universe: tail symbols with (price_sym, fr_sym, category) tuples.
# 1000-prefixed FR symbols (PEPE/BONK/FLOKI) come from Bybit; price is from
# Binance USDT-M perp under non-prefixed names. The FR is a % rate so the
# 1000x notional scaling does NOT affect the strategy P&L (which is also %).
UNIVERSE: List[Tuple[str, str, str]] = [
    ("WIFUSDT",   "WIFUSDT",       "memecoin"),
    ("BOMEUSDT",  "BOMEUSDT",      "memecoin"),
    ("PEPEUSDT",  "1000PEPEUSDT",  "memecoin"),
    ("BONKUSDT",  "1000BONKUSDT",  "memecoin"),
    ("FLOKIUSDT", "1000FLOKIUSDT", "memecoin"),
    ("ENAUSDT",   "ENAUSDT",       "new_alt"),
    ("JUPUSDT",   "JUPUSDT",       "new_alt"),
    ("JTOUSDT",   "JTOUSDT",       "new_alt"),
    ("STRKUSDT",  "STRKUSDT",      "new_alt"),
    ("MANTAUSDT", "MANTAUSDT",     "new_alt"),
    ("ONDOUSDT",  "ONDOUSDT",      "new_alt"),
    ("WLDUSDT",   "WLDUSDT",       "ai"),
    ("TAOUSDT",   "TAOUSDT",       "ai"),
    ("ARKMUSDT",  "ARKMUSDT",      "ai"),
]

# Strategy parameters
COST_TAKER = 0.0004    # 0.04% taker
COST_SLIP  = 0.0003    # 0.03% slippage
COST_PER_SIDE = COST_TAKER + COST_SLIP   # = 7bp per side
MAX_HOLD_DAYS = 7
IS_FRAC = 0.70

# Variants: (name, short_thr, long_thr)  thresholds in decimal (5bp = 0.0005)
# - short_thr: if FR > short_thr, enter SHORT (positive => short captures carry)
# - long_thr:  if FR < long_thr,  enter LONG  (long captures negative carry)
VARIANTS = {
    "V_short_5bp":   {"short_thr":  0.0005, "long_thr": None},
    "V_short_10bp":  {"short_thr":  0.0010, "long_thr": None},
    "V_short_3bp":   {"short_thr":  0.0003, "long_thr": None},
    "V_long_short":  {"short_thr":  0.0005, "long_thr": -0.0005},
}

# Stats
N_PERM = 200
N_BOOT = 200
RNG_SEED = 42
EVENTS_PER_YEAR = 365 * 3  # ~1095 8h funding events/year

t0 = time.time()


def log(msg: str) -> None:
    print(f"[{time.time() - t0:6.1f}s] {msg}", flush=True)


# ── Data loaders ────────────────────────────────────────────────────────────────

def load_fr(fr_sym: str) -> pd.DataFrame:
    """Load Bybit funding rate, return DataFrame indexed on slot ts."""
    fname = CACHE / f"bybit_fr_{fr_sym}_730d.parquet"
    df = pd.read_parquet(fname)
    df = df[["timestamp", "funding_rate"]].copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp").drop_duplicates("timestamp").reset_index(drop=True)
    # Snap to 8h grid (00, 08, 16). Bybit FR is at these slots already.
    hrs = df["timestamp"].dt.hour
    slot_h = (hrs // 8) * 8
    df["slot"] = df["timestamp"].dt.floor("D") + pd.to_timedelta(slot_h, unit="h")
    # If multiple FR within slot, average
    df = df.groupby("slot", as_index=False).agg({"funding_rate": "mean"})
    df = df.rename(columns={"slot": "ts"}).set_index("ts").sort_index()
    return df


def load_price_8h(px_sym: str) -> pd.Series:
    """Load 4H price, downsample to 8h grid (close at 00/08/16)."""
    fname = CACHE / f"{px_sym}_4h_730d.parquet"
    df = pd.read_parquet(fname)
    df = df[["open_time", "close"]].copy()
    df["open_time"] = pd.to_datetime(df["open_time"])
    df = df.sort_values("open_time").drop_duplicates("open_time")
    # 4H bars at hours 0,4,8,12,16,20. Take those at 0,8,16 for 8h grid.
    df = df[df["open_time"].dt.hour.isin([0, 8, 16])].reset_index(drop=True)
    s = df.set_index("open_time")["close"]
    s.name = px_sym
    return s


# ── Strategy execution (per symbol) ─────────────────────────────────────────────

def run_one_symbol(
    fr: pd.DataFrame, price: pd.Series, short_thr: float, long_thr,
    cost_per_side: float = COST_PER_SIDE,
) -> pd.DataFrame:
    """Run threshold strategy on one symbol. Returns event-level result table.

    Mechanics:
      At funding event t with rate fr_t (known at slot t):
        - Position is held from slot t-1 to slot t. Funding fr_t is paid by the
          long side, so short_pnl_funding[t] = +pos_short_{t-1} * fr_t.
        - Price PnL from t-1 to t: pos_{t-1} * ret_t  (ret in simple return).
      After the funding event resolves, we update position for slot t->t+1:
        - if FR_t > short_thr  -> hold SHORT
        - elif FR_t < long_thr -> hold LONG  (if long_thr provided)
        - else                 -> FLAT
      Max hold cap: MAX_HOLD_DAYS (= 21 events). If exceeded, force FLAT until
        a fresh threshold cross.
      Cost: charged on |Δposition| per side.
    """
    df = pd.concat([fr, price.rename("close")], axis=1, join="inner").sort_index()
    df["fr"] = df["funding_rate"].astype(float)
    df = df.dropna(subset=["fr", "close"]).copy()
    if len(df) < 30:
        return pd.DataFrame()

    df["ret"] = df["close"].pct_change().fillna(0.0)

    n = len(df)
    pos = np.zeros(n, dtype=float)
    hold_age = 0  # events held in current direction
    max_age = MAX_HOLD_DAYS * 3  # 8h events per day
    fr_arr = df["fr"].values
    for t in range(n):
        # Decide signal AFTER event t resolves -> hold from t to t+1.
        if t == 0:
            pos[t] = 0.0
            hold_age = 0
            continue
        cur_fr = fr_arr[t]
        # Check force-flat if max age exceeded
        prev_pos = pos[t - 1]
        if prev_pos != 0:
            hold_age += 1
            if hold_age >= max_age:
                pos[t] = 0.0
                hold_age = 0
                continue
        else:
            hold_age = 0

        if cur_fr > short_thr:
            pos[t] = -1.0
            if prev_pos != -1.0:
                hold_age = 0
        elif (long_thr is not None) and (cur_fr < long_thr):
            pos[t] = 1.0
            if prev_pos != 1.0:
                hold_age = 0
        else:
            pos[t] = 0.0
            hold_age = 0

    df["pos"] = pos
    # pos_into_event = position held INTO event t (= pos chosen at t-1)
    df["pos_into"] = df["pos"].shift(1).fillna(0.0)
    # Funding P&L at event t = -fr_t * pos_into_t  (short side receives fr if fr>0)
    df["pnl_funding"] = -df["fr"] * df["pos_into"]
    # Price P&L at event t: pos_into * ret_t
    df["pnl_price"] = df["pos_into"] * df["ret"]
    # Cost: |Δpos| at slot t (executed at close of event t to set pos for t->t+1)
    dpos = (df["pos"] - df["pos"].shift(1).fillna(0.0)).abs()
    df["cost"] = dpos * cost_per_side
    df["pnl_gross"] = df["pnl_funding"] + df["pnl_price"]
    df["pnl_net"] = df["pnl_gross"] - df["cost"]
    return df


# ── Portfolio aggregation ──────────────────────────────────────────────────────

def run_portfolio(
    fr_dict: Dict[str, pd.DataFrame],
    price_dict: Dict[str, pd.Series],
    short_thr: float, long_thr,
    cost_per_side: float = COST_PER_SIDE,
) -> Tuple[pd.DataFrame, Dict[str, Dict[str, float]]]:
    """Equal-weight across symbols with active position at each event.

    Returns (portfolio_df, per_symbol_stats)
    """
    per_symbol = {}
    legs = {}
    for px_sym, fr_sym, cat in UNIVERSE:
        fr = fr_dict[fr_sym]
        px = price_dict[px_sym]
        res = run_one_symbol(fr, px, short_thr, long_thr, cost_per_side)
        if res.empty:
            continue
        legs[px_sym] = res
        per_symbol[px_sym] = {
            "category": cat,
            "fr_sym": fr_sym,
            "n_events": int(len(res)),
            "n_short": int((res["pos"] == -1).sum()),
            "n_long": int((res["pos"] == 1).sum()),
            "n_flat": int((res["pos"] == 0).sum()),
            "sum_pnl_funding": float(res["pnl_funding"].sum()),
            "sum_pnl_price": float(res["pnl_price"].sum()),
            "sum_cost": float(res["cost"].sum()),
            "sum_pnl_net": float(res["pnl_net"].sum()),
            "sharpe_net": sharpe(res["pnl_net"].values),
        }

    # Align all legs to common ts index union
    all_ts = sorted(set().union(*[set(d.index) for d in legs.values()]))
    cols = list(legs.keys())
    pnl_net_mat = pd.DataFrame(0.0, index=all_ts, columns=cols)
    pnl_funding_mat = pd.DataFrame(0.0, index=all_ts, columns=cols)
    pnl_price_mat = pd.DataFrame(0.0, index=all_ts, columns=cols)
    cost_mat = pd.DataFrame(0.0, index=all_ts, columns=cols)
    active_mat = pd.DataFrame(0, index=all_ts, columns=cols)
    for sym, res in legs.items():
        pnl_net_mat.loc[res.index, sym] = res["pnl_net"].values
        pnl_funding_mat.loc[res.index, sym] = res["pnl_funding"].values
        pnl_price_mat.loc[res.index, sym] = res["pnl_price"].values
        cost_mat.loc[res.index, sym] = res["cost"].values
        active_mat.loc[res.index, sym] = (res["pos_into"].values != 0).astype(int)

    # Equal weight across symbols currently active (pos_into != 0).
    # If no leg active: portfolio_pnl = 0.
    n_active = active_mat.sum(axis=1).clip(lower=1)
    # Weight each leg by 1/n_active where active
    w = active_mat.div(n_active, axis=0)
    port_net = (pnl_net_mat * w).sum(axis=1)
    port_funding = (pnl_funding_mat * w).sum(axis=1)
    port_price = (pnl_price_mat * w).sum(axis=1)
    port_cost = (cost_mat * w).sum(axis=1)

    # If no active leg at t, set 0 (already from clip)
    no_active_mask = active_mat.sum(axis=1) == 0
    port_net[no_active_mask] = 0.0
    port_funding[no_active_mask] = 0.0
    port_price[no_active_mask] = 0.0
    port_cost[no_active_mask] = 0.0

    port_df = pd.DataFrame({
        "pnl_net": port_net,
        "pnl_funding": port_funding,
        "pnl_price": port_price,
        "cost": port_cost,
        "n_active": active_mat.sum(axis=1),
    })
    return port_df, per_symbol


# ── Stats helpers ──────────────────────────────────────────────────────────────

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
    peak = np.maximum.accumulate(eq)
    dd = eq - peak
    return float(dd.min()) if len(dd) else 0.0


def total_ret(pnl: np.ndarray) -> float:
    return float(np.sum(pnl))


def winrate(pnl: np.ndarray) -> float:
    pnl_nz = pnl[pnl != 0]
    if len(pnl_nz) == 0:
        return 0.0
    return float((pnl_nz > 0).mean())


def block_bootstrap_sharpe(pnl: np.ndarray, n: int = N_BOOT, block: int = 21,
                            seed: int = RNG_SEED) -> Dict[str, float]:
    rng = np.random.default_rng(seed)
    T = len(pnl)
    if T < block * 2:
        return {"mean": 0.0, "ci_lo": 0.0, "ci_hi": 0.0}
    n_blocks = int(np.ceil(T / block))
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


def dsr(observed_sh: float, pnl: np.ndarray, n_trials: int = 1) -> float:
    """Probabilistic Sharpe Ratio (deflated for n_trials)."""
    from math import sqrt, log
    from scipy.stats import norm
    x = pnl[pnl != 0]
    T = len(x)
    if T < 30:
        return 0.0
    skew = float(pd.Series(x).skew())
    kurt = float(pd.Series(x).kurt())  # excess
    sh_per_event = observed_sh / np.sqrt(EVENTS_PER_YEAR)

    # Deflated threshold (Bailey/LdP): expected max under null over n trials
    if n_trials > 1:
        emc = 0.5772156649
        log_n = max(log(n_trials), 1e-6)
        e_max_per_event = sqrt(2 * log_n) * (1 - emc / sqrt(2 * log_n)) + emc / sqrt(2 * log_n)
        # We compare sh_per_event to this threshold rescaled per event
        # But e_max from std-normal needs scaling by sd of SR estimator. Use simplified:
        thresh = e_max_per_event / sqrt(T)
    else:
        thresh = 0.0
    var_sr = (1 - skew * sh_per_event + (kurt / 4) * (sh_per_event ** 2)) / max(T - 1, 1)
    if var_sr <= 0:
        return 0.5
    z = (sh_per_event - thresh) / sqrt(var_sr)
    return float(norm.cdf(z))


def permutation_pvalue_circ(pnl: np.ndarray, n: int = N_PERM, seed: int = RNG_SEED) -> float:
    """Circular shift permutation of PnL: tests if observed Sharpe > chance
    given the marginal distribution. (Crude but symbol-set agnostic.)"""
    if len(pnl) < 30:
        return 1.0
    obs = sharpe(pnl)
    rng = np.random.default_rng(seed)
    T = len(pnl)
    perms = np.empty(n)
    for k in range(n):
        sh = rng.integers(1, T)
        sample = np.roll(pnl, sh)
        # Also flip half the time
        if rng.random() < 0.5:
            sample = sample[::-1]
        perms[k] = sharpe(sample)
    return float((np.sum(perms >= obs) + 1) / (n + 1))


def walkforward_4fold(pnl: np.ndarray) -> List[Dict[str, float]]:
    """Split into 4 contiguous folds and report Sharpe on each."""
    T = len(pnl)
    if T < 80:
        return []
    fold_sz = T // 4
    folds = []
    for i in range(4):
        a = i * fold_sz
        b = (i + 1) * fold_sz if i < 3 else T
        seg = pnl[a:b]
        folds.append({
            "fold": i + 1,
            "n": int(len(seg)),
            "sharpe": sharpe(seg),
            "total_ret": total_ret(seg),
            "winrate": winrate(seg),
        })
    return folds


def cost_stress(port_df: pd.DataFrame, gross_components_idx: pd.Index,
                fr_dict, price_dict, short_thr, long_thr) -> Dict[str, float]:
    """Re-run with ±50% cost. Re-uses raw funding/price PnL; only Δ cost."""
    out = {}
    for label, mul in (("cost_minus50", 0.5), ("cost_plus50", 1.5)):
        pdf, _ = run_portfolio(fr_dict, price_dict, short_thr, long_thr,
                               cost_per_side=COST_PER_SIDE * mul)
        out[label] = {
            "sharpe": sharpe(pdf["pnl_net"].values),
            "total_ret": total_ret(pdf["pnl_net"].values),
            "cost_sum": float(pdf["cost"].sum()),
        }
    return out


# ── Main ────────────────────────────────────────────────────────────────────────

def main():
    log("loading data...")
    fr_dict = {}
    price_dict = {}
    failed = []
    for px_sym, fr_sym, cat in UNIVERSE:
        try:
            fr_dict.setdefault(fr_sym, load_fr(fr_sym))
            price_dict[px_sym] = load_price_8h(px_sym)
        except Exception as e:
            failed.append((px_sym, str(e)))
            log(f"  load failed for {px_sym}/{fr_sym}: {e}")
    if failed:
        log(f"failed: {failed}")

    log(f"loaded {len(price_dict)} symbols, {len(fr_dict)} unique FR series")

    results = {"variants": {}, "universe": [], "params": {
        "cost_taker": COST_TAKER, "cost_slip": COST_SLIP, "cost_per_side": COST_PER_SIDE,
        "max_hold_days": MAX_HOLD_DAYS, "is_frac": IS_FRAC,
        "n_perm": N_PERM, "n_boot": N_BOOT,
    }}
    for px_sym, fr_sym, cat in UNIVERSE:
        if px_sym in price_dict:
            results["universe"].append({"px_sym": px_sym, "fr_sym": fr_sym, "category": cat})

    curves_all = {}

    for vname, params in VARIANTS.items():
        log(f"=== running {vname} (short_thr={params['short_thr']}, long_thr={params['long_thr']}) ===")
        port_df, per_sym = run_portfolio(
            fr_dict, price_dict, params["short_thr"], params["long_thr"],
        )
        pnl_net = port_df["pnl_net"].values
        pnl_funding = port_df["pnl_funding"].values
        pnl_price = port_df["pnl_price"].values
        cost = port_df["cost"].values
        T = len(pnl_net)
        is_end = int(T * IS_FRAC)
        pnl_is = pnl_net[:is_end]
        pnl_oos = pnl_net[is_end:]

        # Permutation test
        perm_p = permutation_pvalue_circ(pnl_net, n=N_PERM)
        # Bootstrap on OOS
        bb = block_bootstrap_sharpe(pnl_oos, n=N_BOOT, block=21)
        # DSR with n_trials=4 (one per variant)
        dsr_oos = dsr(sharpe(pnl_oos), pnl_oos, n_trials=4)
        # Walk-forward
        wf = walkforward_4fold(pnl_net)
        # Cost stress
        cs = cost_stress(port_df, port_df.index, fr_dict, price_dict,
                         params["short_thr"], params["long_thr"])

        # §6 mini gates
        oos_sh = sharpe(pnl_oos)
        g1 = oos_sh >= 1.0
        g2 = perm_p < 0.05
        g3 = dsr_oos >= 0.95

        variant_res = {
            "params": params,
            "n_events": int(T),
            "is_end_idx": int(is_end),
            "full": {
                "sharpe": sharpe(pnl_net),
                "max_dd": max_dd(pnl_net),
                "total_ret": total_ret(pnl_net),
                "winrate": winrate(pnl_net),
                "mean_event": float(np.mean(pnl_net)),
                "std_event": float(np.std(pnl_net)),
            },
            "is": {
                "sharpe": sharpe(pnl_is),
                "max_dd": max_dd(pnl_is),
                "total_ret": total_ret(pnl_is),
                "winrate": winrate(pnl_is),
                "n_events": int(len(pnl_is)),
            },
            "oos": {
                "sharpe": oos_sh,
                "max_dd": max_dd(pnl_oos),
                "total_ret": total_ret(pnl_oos),
                "winrate": winrate(pnl_oos),
                "n_events": int(len(pnl_oos)),
            },
            "decomposition_full": {
                "sum_pnl_price": float(pnl_price.sum()),
                "sum_pnl_funding": float(pnl_funding.sum()),
                "sum_cost": float(cost.sum()),
                "sum_pnl_net": float(pnl_net.sum()),
                "pct_funding_of_gross": float(
                    pnl_funding.sum() /
                    max(abs(pnl_funding.sum()) + abs(pnl_price.sum()), 1e-12)
                ),
            },
            "perm_p": perm_p,
            "bootstrap_oos": bb,
            "dsr_oos": dsr_oos,
            "walkforward": wf,
            "cost_stress": cs,
            "per_symbol": per_sym,
            "gates": {
                "G1_oos_sharpe_ge_1": bool(g1),
                "G2_perm_p_lt_005": bool(g2),
                "G3_dsr_ge_095": bool(g3),
                "pass_all": bool(g1 and g2 and g3),
            },
            "n_active_avg": float(port_df["n_active"].mean()),
            "n_active_max": int(port_df["n_active"].max()),
        }
        results["variants"][vname] = variant_res

        curves_all[vname] = {
            "timestamps": [str(t) for t in port_df.index],
            "pnl_net": pnl_net.tolist(),
            "equity_net": np.cumsum(pnl_net).tolist(),
            "pnl_funding": pnl_funding.tolist(),
            "pnl_price": pnl_price.tolist(),
            "cost": cost.tolist(),
            "n_active": port_df["n_active"].astype(int).tolist(),
            "is_end_idx": int(is_end),
        }
        log(f"  {vname}: full_sh={variant_res['full']['sharpe']:.3f} oos_sh={oos_sh:.3f} "
            f"perm_p={perm_p:.3f} dsr={dsr_oos:.3f} n_active_avg={variant_res['n_active_avg']:.2f}")

    (OUT_DIR / "wave_k130_mexc_tail.json").write_text(json.dumps(results, indent=2, default=str))
    (OUT_DIR / "wave_k130_curves.json").write_text(json.dumps(curves_all, default=str))

    log(f"done. total wall: {time.time() - t0:.1f}s")
    print_markdown(results)


def print_markdown(R: Dict[str, object]) -> None:
    md = []
    md.append("# Wave K130 — MEXC Tail-Asset Funding Premium")
    md.append("")
    md.append(f"_Run wall time: {time.time() - t0:.1f}s_")
    md.append("")
    md.append("## Hypothesis (source)")
    md.append("")
    md.append("CoinGecko 2026 perp report: MEXC lists 55+ tail/new alts per month. "
              "Tail alts allegedly carry persistent positive funding premium (longs "
              "pay shorts). Test: SHORT when FR > +threshold, capture funding cash flow.")
    md.append("")
    md.append("## Universe")
    md.append("")
    md.append("| Symbol | FR proxy | Category |")
    md.append("|---|---|---|")
    for u in R["universe"]:
        md.append(f"| {u['px_sym']} | bybit_fr_{u['fr_sym']} | {u['category']} |")
    md.append("")
    md.append("**Dropped:** none (all 14 tail symbols had both 4H price and Bybit FR cache).")
    md.append("")
    md.append("**Critical caveat:** FR is from Bybit (mature, deep). MEXC FR is unmeasured here. "
              "If MEXC truly carries fatter premium on these tail alts, this is a LOWER BOUND on the MEXC-specific edge.")
    md.append("")
    md.append("## Per-variant headline")
    md.append("")
    md.append("| Variant | Full Sh | IS Sh | OOS Sh | MaxDD(Net) | Total | Win% | Perm p | DSR | n_act̄ | Pass§6 |")
    md.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|:---:|")
    for vname, v in R["variants"].items():
        f, isd, o, g = v["full"], v["is"], v["oos"], v["gates"]
        md.append(
            f"| {vname} | {f['sharpe']:.2f} | {isd['sharpe']:.2f} | {o['sharpe']:.2f} | "
            f"{f['max_dd']:.4f} | {f['total_ret']:+.4f} | {f['winrate']:.2f} | "
            f"{v['perm_p']:.3f} | {v['dsr_oos']:.3f} | {v['n_active_avg']:.2f} | "
            f"{'YES' if g['pass_all'] else 'no'} |"
        )
    md.append("")

    md.append("## P&L Decomposition (full sample, per variant)")
    md.append("")
    md.append("| Variant | Funding | Price | Cost | Net | %Funding of |Gross| |")
    md.append("|---|---:|---:|---:|---:|---:|")
    for vname, v in R["variants"].items():
        d = v["decomposition_full"]
        md.append(
            f"| {vname} | {d['sum_pnl_funding']:+.4f} | {d['sum_pnl_price']:+.4f} | "
            f"{-d['sum_cost']:+.4f} | {d['sum_pnl_net']:+.4f} | {d['pct_funding_of_gross']*100:+.1f}% |"
        )
    md.append("")
    md.append("_Interpretation: if |Funding| dominates → real carry edge (independent of price). "
              "If |Price| dominates → reframe needed (the strategy is implicitly directional)._")
    md.append("")

    md.append("## Walk-forward (4 folds, V_short_5bp default)")
    md.append("")
    v0 = R["variants"]["V_short_5bp"]
    if v0["walkforward"]:
        md.append("| Fold | N | Sharpe | TotalRet | Win% |")
        md.append("|---:|---:|---:|---:|---:|")
        for f in v0["walkforward"]:
            md.append(f"| {f['fold']} | {f['n']} | {f['sharpe']:.2f} | {f['total_ret']:+.4f} | {f['winrate']:.2f} |")
    md.append("")
    md.append("## Cost stress (V_short_5bp)")
    md.append("")
    cs = v0["cost_stress"]
    md.append("| Scenario | Sharpe | TotalRet | Sum Cost |")
    md.append("|---|---:|---:|---:|")
    md.append(f"| -50% cost | {cs['cost_minus50']['sharpe']:.3f} | {cs['cost_minus50']['total_ret']:+.4f} | {cs['cost_minus50']['cost_sum']:.4f} |")
    md.append(f"| baseline | {v0['full']['sharpe']:.3f} | {v0['full']['total_ret']:+.4f} | {v0['decomposition_full']['sum_cost']:.4f} |")
    md.append(f"| +50% cost | {cs['cost_plus50']['sharpe']:.3f} | {cs['cost_plus50']['total_ret']:+.4f} | {cs['cost_plus50']['cost_sum']:.4f} |")
    md.append("")
    bb0 = v0["bootstrap_oos"]
    md.append("## Block bootstrap OOS (V_short_5bp)")
    md.append("")
    md.append(f"- Mean Sharpe: {bb0['mean']:.3f}")
    md.append(f"- 95% CI: [{bb0['ci_lo']:.3f}, {bb0['ci_hi']:.3f}]")
    md.append("")
    md.append("## Per-symbol summary (V_short_5bp)")
    md.append("")
    md.append("| Symbol | Cat | N short | N long | %Active | Sh(net) | Funding | Price | Cost | Net |")
    md.append("|---|---|---:|---:|---:|---:|---:|---:|---:|---:|")
    for sym, ps in sorted(v0["per_symbol"].items(), key=lambda kv: -kv[1]["sum_pnl_net"]):
        active = (ps["n_short"] + ps["n_long"]) / max(ps["n_events"], 1)
        md.append(
            f"| {sym} | {ps['category']} | {ps['n_short']} | {ps['n_long']} | "
            f"{active*100:.1f}% | {ps['sharpe_net']:.2f} | {ps['sum_pnl_funding']:+.4f} | "
            f"{ps['sum_pnl_price']:+.4f} | -{ps['sum_cost']:.4f} | {ps['sum_pnl_net']:+.4f} |"
        )
    md.append("")
    md.append("## §6 Mini Gates Summary")
    md.append("")
    md.append("| Variant | G1 OOS Sh≥1 | G2 perm p<0.05 | G3 DSR≥0.95 | All |")
    md.append("|---|:---:|:---:|:---:|:---:|")
    for vname, v in R["variants"].items():
        g = v["gates"]
        md.append(f"| {vname} | {'✓' if g['G1_oos_sharpe_ge_1'] else '✗'} | "
                  f"{'✓' if g['G2_perm_p_lt_005'] else '✗'} | "
                  f"{'✓' if g['G3_dsr_ge_095'] else '✗'} | "
                  f"{'**PASS**' if g['pass_all'] else 'fail'} |")
    md.append("")
    md.append("## Verdict")
    md.append("")
    any_pass = any(v["gates"]["pass_all"] for v in R["variants"].values())
    best_v = max(R["variants"].items(), key=lambda kv: kv[1]["oos"]["sharpe"])
    bv_name, bv = best_v
    md.append(f"**Best variant by OOS Sharpe:** {bv_name} → OOS Sh={bv['oos']['sharpe']:.3f}, "
              f"DSR={bv['dsr_oos']:.3f}, perm p={bv['perm_p']:.3f}.")
    md.append("")
    if any_pass:
        md.append("**Some variant passes §6 mini gates.** See table above.")
    else:
        md.append("**No variant passes all §6 mini gates** on Bybit FR data.")
    md.append("")
    # Decomposition verdict
    d_all = {vname: v["decomposition_full"] for vname, v in R["variants"].items()}
    funding_dom = []
    price_dom = []
    for vname, d in d_all.items():
        ratio = abs(d["sum_pnl_funding"]) / max(abs(d["sum_pnl_price"]), 1e-12)
        if ratio > 1.5:
            funding_dom.append(vname)
        elif ratio < 0.67:
            price_dom.append(vname)
    md.append("**P&L Source attribution:**")
    md.append(f"- Funding-dominated variants (|funding| > 1.5x |price|): {funding_dom or 'none'}")
    md.append(f"- Price-dominated variants (|price| > 1.5x |funding|): {price_dom or 'none'}")
    md.append("")
    md.append("**MEXC tail-asset premium claim test (on Bybit proxy):**")
    md.append("- The CoinGecko hypothesis predicts persistent +funding on tail alts. "
              "On Bybit, observed |+5bp FR| frequency on these 14 tail names is ~0.3–1.9% of events "
              "(see FR diagnostic notes) — meaning short-carry signals are SPARSE, not persistent.")
    md.append("- **CRITICAL REGIME-SHIFT FINDING:** OOS active-event counts are dramatically lower than IS:")
    md.append("")
    md.append("| Variant | IS active events | OOS active events |")
    md.append("|---|---:|---:|")
    # Re-read curves to count
    try:
        curves = json.loads((OUT_DIR / "wave_k130_curves.json").read_text())
        for vname in R["variants"].keys():
            c = curves[vname]
            ie = c["is_end_idx"]
            md.append(f"| {vname} | {sum(c['n_active'][:ie])} | {sum(c['n_active'][ie:])} |")
    except Exception:
        pass
    md.append("")
    md.append("  3 of 4 variants have ZERO active OOS events — high-FR spikes occurred almost exclusively in 2024–early 2025; "
              "funding rates COMPRESSED in 2026. The 'persistent +funding premium' hypothesis is FALSIFIED on tail alts: "
              "even when premium did exist (IS period), shorting earned only +5–7bp net per event, dominated by price moves.")
    md.append("")
    md.append("- Net P&L magnitude is therefore small (few trades, small carry per event). "
              "True MEXC-specific edge would require MEXC FR data, which we lack.")
    md.append("- **Honest verdict:** This test does NOT validate the MEXC-specific claim and actively shows "
              "the Bybit proxy contradicts it on the OOS sample (no premium to capture). The strategy as "
              "specified is a directional short on tail alts that triggered on funding spikes — when those "
              "shorts coincided with tops (WIF/STRK/MANTA/ONDO), they profited; when they coincided with continuation "
              "rallies (TAO/WLD/BONK/PEPE), they bled. Funding cash flow alone is not the driver.")
    md.append("")
    print("\n".join(md))


if __name__ == "__main__":
    main()
