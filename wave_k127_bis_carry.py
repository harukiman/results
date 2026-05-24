"""Wave K127 (retry, LEAN) — BIS WP1087 Crypto Carry Cross-Section.

Hypothesis: cross-sectional sort on perpetual funding rate.
Long bottom-decile (cheap-to-fund), short top-decile (expensive-to-fund),
dollar-neutral, rebalanced every 8h funding event.

Pre-registered single variant — no parameter sweep.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

CACHE = Path("/Users/nekonaomichi/crypto-lab/cache")
OUT_DIR = Path("/Users/nekonaomichi/crypto-lab")

# 13 of the 15 requested symbols (BONK/SHIB lack bybit_fr cache).
SYMBOLS: List[str] = [
    "BTC", "ETH", "SOL", "BNB", "DOGE", "AVAX", "LINK",
    "ADA", "XRP", "INJ", "OP", "WIF", "ARB",
]
MISSING_FR: List[str] = ["BONK", "SHIB"]

# --- Strategy params (pre-registered single variant) ----------------------------
LOOKBACK_EVENTS = 21          # 21 funding events ~= 7 days at 8h cadence
LONG_K = 3                    # bottom-3
SHORT_K = 3                   # top-3
COST_BPS_PER_LEG = 7.0        # 0.07% = 7bps per side per leg (entry + exit)
IS_FRAC = 0.70

# Resampling: align funding events onto fixed 8h grid (00, 08, 16 UTC).
FUNDING_HOURS = [0, 8, 16]

# Stat params
N_PERM = 100
N_BOOT = 200
RNG_SEED = 42

t0 = time.time()


def log(msg: str) -> None:
    print(f"[{time.time() - t0:6.1f}s] {msg}", flush=True)


# --- Data loading ---------------------------------------------------------------

def load_fr(sym: str) -> pd.DataFrame:
    df = pd.read_parquet(CACHE / f"bybit_fr_{sym}USDT_730d.parquet")
    df = df[["timestamp", "funding_rate"]].copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp").drop_duplicates("timestamp")
    # Align to 8h grid: sum funding paid within each 8h bucket whose end is at 00/08/16 UTC.
    # Bucket label is the funding event time. For 4h schedules we sum the two halves.
    # Drop rows that don't fall on a 4-hour grid to avoid odd labels.
    # Floor to 8h slot ending at 00/08/16.
    ts = df["timestamp"]
    # Map each timestamp to the next-occurring 00/08/16 slot at or after it.
    hours = ts.dt.hour
    slot_h = ((hours // 8) * 8).astype(int)
    slot_ts = ts.dt.floor("D") + pd.to_timedelta(slot_h, unit="h")
    df["slot"] = slot_ts
    agg = df.groupby("slot")["funding_rate"].sum().to_frame(f"{sym}")
    agg.index.name = "ts"
    return agg


def load_price(sym: str) -> pd.Series:
    df = pd.read_parquet(CACHE / f"{sym}USDT_4h_730d.parquet")
    df = df[["open_time", "close"]].copy()
    df["open_time"] = pd.to_datetime(df["open_time"])
    df = df.sort_values("open_time").drop_duplicates("open_time")
    df = df.set_index("open_time")["close"]
    df.name = sym
    return df


def build_panel() -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Returns (funding_df: rate at each 8h slot, ret_df: 8h log returns ending at slot)."""
    fr_pieces = []
    px_pieces = []
    for s in SYMBOLS:
        try:
            fr_pieces.append(load_fr(s))
            px_pieces.append(load_price(s))
        except Exception as e:
            log(f"  load failed for {s}: {e}")
    funding = pd.concat(fr_pieces, axis=1)
    funding = funding.sort_index()

    # Build 8h price series: take close at 00/08/16 UTC.
    pxwide = pd.concat(px_pieces, axis=1)
    # Pick rows whose hour is in {0,8,16}
    pxwide = pxwide[pxwide.index.hour.isin(FUNDING_HOURS)]
    pxwide = pxwide.sort_index()

    # Align panels to common index
    idx = funding.index.intersection(pxwide.index)
    funding = funding.loc[idx]
    pxwide = pxwide.loc[idx]

    # 8h log return ending at slot t = log(P_t / P_{t-1_slot})
    ret = np.log(pxwide / pxwide.shift(1))
    return funding, ret


# --- Strategy core --------------------------------------------------------------

def run_strategy(funding: pd.DataFrame, ret: pd.DataFrame) -> Dict[str, object]:
    """Run cross-sectional carry strategy and return all diagnostic outputs."""
    syms = list(funding.columns)
    N = len(syms)

    # Trailing-mean funding signal (lag 1: known BEFORE event t executes)
    # Use only past LOOKBACK_EVENTS events ending at t-1.
    rolling = funding.rolling(LOOKBACK_EVENTS, min_periods=LOOKBACK_EVENTS).mean()
    signal = rolling.shift(1)  # lag 1: rank based on info known before t

    # Build weights at each timestamp.
    weights = pd.DataFrame(0.0, index=funding.index, columns=syms)
    has_signal = signal.notna()

    for t in funding.index:
        row = signal.loc[t]
        valid = row.dropna()
        if len(valid) < (LONG_K + SHORT_K):
            continue
        # ranks: ascending; smallest = cheapest funding = long
        ranks = valid.rank(method="first", ascending=True)
        long_syms = ranks.nsmallest(LONG_K).index
        short_syms = ranks.nlargest(SHORT_K).index
        # Equal weight within each leg; gross exposure = 2 (1 long, 1 short).
        # Dollar-neutral: +1/LONG_K each long, -1/SHORT_K each short.
        for s in long_syms:
            weights.at[t, s] = 1.0 / LONG_K
        for s in short_syms:
            weights.at[t, s] = -1.0 / SHORT_K

    # Funding P&L: long receives -fr*pos (you pay if fr>0 and you're long).
    # Convention: holder of long pays funding when fr>0. So long_pnl_funding = -fr * w_long_pos.
    # We hold position w_t over the 8h until next event t+1, paying funding at t+1.
    pos_held = weights.shift(0)  # weights set at t are held from t to t+1
    # Funding paid at next event applies to position held from t to t+1, using fr at t+1.
    funding_pnl = (-funding * pos_held.shift(1).reindex_like(funding)).sum(axis=1)
    # Above: at event t+1, funding rate fr_{t+1} on position pos_{t}. Implement directly:
    # Compute pnl_funding_per_event[t] = sum_i -fr[t,i] * pos_held_through_event_at_t[i]
    # The position "held into" event t was set at t-1.
    pos_into_event = weights.shift(1)
    funding_pnl = (-funding * pos_into_event).sum(axis=1)

    # Price P&L: ret at event t is log return between event t-1 and event t.
    # Position held was set at event t-1, so price_pnl[t] = sum_i w[t-1,i] * ret[t,i]
    price_pnl = (ret * pos_into_event).sum(axis=1)

    # Trading cost: turnover at event t = sum |w_t - w_{t-1}|; cost = turnover * bps_per_leg.
    # Each unit of |Δw| corresponds to half-leg trade (one side). For round trip,
    # entering a long+short pair gross |Δw| = 2 already. We charge bps_per_leg per |Δw| unit.
    dw = (weights - weights.shift(1)).abs().sum(axis=1)
    cost_per_event = dw * (COST_BPS_PER_LEG / 1e4)

    pnl_gross = price_pnl + funding_pnl
    pnl_net = pnl_gross - cost_per_event

    pnl_net = pnl_net.fillna(0.0)
    pnl_gross = pnl_gross.fillna(0.0)
    price_pnl = price_pnl.fillna(0.0)
    funding_pnl = funding_pnl.fillna(0.0)
    cost_per_event = cost_per_event.fillna(0.0)

    return {
        "weights": weights,
        "pnl_net": pnl_net,
        "pnl_gross": pnl_gross,
        "price_pnl": price_pnl,
        "funding_pnl": funding_pnl,
        "cost": cost_per_event,
        "pos_into_event": pos_into_event,
        "signal": signal,
    }


# --- Stats ----------------------------------------------------------------------

EVENTS_PER_YEAR = 365 * 3  # ~1095 8h events


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
    pnl = pnl[pnl != 0]
    if len(pnl) == 0:
        return 0.0
    return float((pnl > 0).mean())


# --- Permutation test ----------------------------------------------------------

def permutation_pvalue(signal: pd.DataFrame, ret: pd.DataFrame, funding: pd.DataFrame,
                       observed_sharpe_net: float, observed_sharpe_gross: float,
                       n: int = N_PERM, seed: int = RNG_SEED):
    """Shuffle ranks across symbols at each timestep; refit weights; recompute Sharpe.

    Returns one-sided p-values for both net and gross Sharpe under the null of no
    cross-sectional rank signal. Net p-value is confounded by trading cost / turnover
    differences; gross p-value isolates the rank-order alpha cleanly.
    """
    rng = np.random.default_rng(seed)
    sym_arr = np.array(list(funding.columns))
    syms = list(funding.columns)
    N = len(syms)

    # Pre-compute matrices
    sig_mat = signal.values  # T x N
    fr_mat = funding.values
    ret_mat = ret.values

    perm_sharpes_net = np.empty(n)
    perm_sharpes_gross = np.empty(n)
    T = sig_mat.shape[0]
    for k in range(n):
        # For each row, shuffle the signal across symbols
        sig_perm = sig_mat.copy()
        for t in range(T):
            row = sig_perm[t]
            valid_mask = ~np.isnan(row)
            if valid_mask.sum() < (LONG_K + SHORT_K):
                continue
            idx = np.where(valid_mask)[0]
            shuffled = rng.permutation(row[idx])
            sig_perm[t, idx] = shuffled

        # Compute weights from sig_perm (lag already in signal)
        w = np.zeros_like(sig_perm)
        for t in range(T):
            row = sig_perm[t]
            valid_mask = ~np.isnan(row)
            if valid_mask.sum() < (LONG_K + SHORT_K):
                continue
            idx = np.where(valid_mask)[0]
            vals = row[idx]
            order = np.argsort(vals)
            long_idx = idx[order[:LONG_K]]
            short_idx = idx[order[-SHORT_K:]]
            w[t, long_idx] = 1.0 / LONG_K
            w[t, short_idx] = -1.0 / SHORT_K

        pos_into = np.vstack([np.zeros((1, N)), w[:-1]])
        # PnL at event t
        pnl_price = np.nansum(ret_mat * pos_into, axis=1)
        pnl_fund = np.nansum(-fr_mat * pos_into, axis=1)
        dw = np.abs(w - np.vstack([np.zeros((1, N)), w[:-1]])).sum(axis=1)
        cost = dw * (COST_BPS_PER_LEG / 1e4)
        pnl_gross_v = pnl_price + pnl_fund
        pnl = pnl_gross_v - cost
        pnl = np.nan_to_num(pnl, nan=0.0, posinf=0.0, neginf=0.0)
        pnl_gross_v = np.nan_to_num(pnl_gross_v, nan=0.0, posinf=0.0, neginf=0.0)
        perm_sharpes_net[k] = sharpe(pnl)
        perm_sharpes_gross[k] = sharpe(pnl_gross_v)

    p_net = float((np.sum(perm_sharpes_net >= observed_sharpe_net) + 1) / (len(perm_sharpes_net) + 1))
    p_gross = float((np.sum(perm_sharpes_gross >= observed_sharpe_gross) + 1) / (len(perm_sharpes_gross) + 1))
    return {
        "p_net": p_net,
        "p_gross": p_gross,
        "perm_sharpes_net": perm_sharpes_net,
        "perm_sharpes_gross": perm_sharpes_gross,
    }


# --- Block bootstrap ----------------------------------------------------------

def block_bootstrap_sharpe(pnl: np.ndarray, n: int = N_BOOT, block: int = 21,
                            seed: int = RNG_SEED) -> Dict[str, float]:
    rng = np.random.default_rng(seed)
    T = len(pnl)
    n_blocks = max(1, int(np.ceil(T / block)))
    boots = np.empty(n)
    for k in range(n):
        starts = rng.integers(0, T - block + 1, size=n_blocks)
        chunks = [pnl[s:s + block] for s in starts]
        sample = np.concatenate(chunks)[:T]
        boots[k] = sharpe(sample)
    boots.sort()
    return {
        "mean": float(boots.mean()),
        "ci_lo": float(np.percentile(boots, 2.5)),
        "ci_hi": float(np.percentile(boots, 97.5)),
        "samples": boots.tolist(),
    }


def dsr(observed_sh: float, pnl: np.ndarray, n_trials: int = 1) -> float:
    """Deflated Sharpe ratio via Bailey & López de Prado (simplified)."""
    from math import sqrt, log
    from scipy.stats import norm
    x = pnl[pnl != 0]
    T = len(x)
    if T < 30:
        return 0.0
    skew = float(pd.Series(x).skew())
    kurt = float(pd.Series(x).kurt())  # excess kurtosis
    sh_per_event = observed_sh / np.sqrt(EVENTS_PER_YEAR)

    # Expected max Sharpe over N trials under null (Bailey/LdP approx)
    emc = 0.5772156649
    e_max = sqrt(2 * log(max(n_trials, 2))) * (1 - emc / sqrt(2 * log(max(n_trials, 2)))) + \
            emc / sqrt(2 * log(max(n_trials, 2)))
    # Variance of SR estimator
    var_sr = (1 - skew * sh_per_event + (kurt / 4) * sh_per_event ** 2) / (T - 1)
    if var_sr <= 0:
        return 0.5
    dsr_z = (sh_per_event - e_max * 0 - 0) / sqrt(var_sr)  # threshold is 0 since n_trials=1
    # When n_trials=1, deflation is minimal; we just use a standard SR significance test.
    z = sh_per_event * sqrt(T) / sqrt(1 - skew * sh_per_event + (kurt / 4) * sh_per_event ** 2)
    p = 1 - norm.cdf(z)
    return float(1 - p)  # probabilistic Sharpe ratio (PSR), equivalent when n_trials=1


# --- Main -----------------------------------------------------------------------

def main():
    log("loading data...")
    funding, ret = build_panel()
    log(f"panel: {funding.shape[0]} events x {funding.shape[1]} symbols")
    log(f"date range: {funding.index.min()} .. {funding.index.max()}")

    log("running strategy...")
    out = run_strategy(funding, ret)
    pnl_net = out["pnl_net"].values
    pnl_gross = out["pnl_gross"].values
    price_pnl = out["price_pnl"].values
    funding_pnl = out["funding_pnl"].values
    cost = out["cost"].values
    weights = out["weights"]
    signal_df = out["signal"]

    T = len(pnl_net)
    # IS/OOS split
    is_end = int(T * IS_FRAC)
    pnl_is = pnl_net[:is_end]
    pnl_oos = pnl_net[is_end:]

    metrics = {
        "n_events": int(T),
        "n_symbols": int(funding.shape[1]),
        "symbols_used": list(funding.columns),
        "symbols_missing_fr": MISSING_FR,
        "lookback_events": LOOKBACK_EVENTS,
        "long_k": LONG_K,
        "short_k": SHORT_K,
        "cost_bps_per_leg": COST_BPS_PER_LEG,
        "is_frac": IS_FRAC,
        "full": {
            "sharpe": sharpe(pnl_net),
            "sharpe_gross": sharpe(pnl_gross),
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
            "sharpe": sharpe(pnl_oos),
            "max_dd": max_dd(pnl_oos),
            "total_ret": total_ret(pnl_oos),
            "winrate": winrate(pnl_oos),
            "n_events": int(len(pnl_oos)),
        },
    }

    # Per-symbol time spent long vs short
    per_sym = {}
    for s in weights.columns:
        col = weights[s]
        n_total = (col != 0).sum()
        n_long = (col > 0).sum()
        n_short = (col < 0).sum()
        per_sym[s] = {
            "n_long": int(n_long),
            "n_short": int(n_short),
            "n_total": int(n_total),
            "pct_long": float(n_long / max(1, T)),
            "pct_short": float(n_short / max(1, T)),
        }
    metrics["per_symbol"] = per_sym

    # Decomposition
    metrics["decomposition"] = {
        "sum_price_pnl": float(np.sum(price_pnl)),
        "sum_funding_pnl": float(np.sum(funding_pnl)),
        "sum_cost": float(np.sum(cost)),
        "sum_net": float(np.sum(pnl_net)),
    }

    # Permutation test (use OOS for primary)
    log("running permutation test (n=100)...")
    try:
        perm_res = permutation_pvalue(
            signal_df, ret, funding,
            observed_sharpe_net=metrics["full"]["sharpe"],
            observed_sharpe_gross=metrics["full"]["sharpe_gross"],
            n=N_PERM, seed=RNG_SEED,
        )
        metrics["perm_p_net"] = perm_res["p_net"]
        metrics["perm_p_gross"] = perm_res["p_gross"]
        # Backward-compatible field used by G2: gross is the clean signal-only test.
        metrics["perm_p"] = perm_res["p_gross"]
        for label, arr in (("net", perm_res["perm_sharpes_net"]),
                            ("gross", perm_res["perm_sharpes_gross"])):
            metrics[f"perm_sharpes_{label}_summary"] = {
                "mean": float(np.mean(arr)),
                "p5": float(np.percentile(arr, 5)),
                "p95": float(np.percentile(arr, 95)),
            }
    except Exception as e:
        log(f"perm test failed: {e}")
        metrics["perm_p"] = None
        metrics["perm_p_net"] = None
        metrics["perm_p_gross"] = None

    log("running block bootstrap (n=200)...")
    try:
        bb = block_bootstrap_sharpe(pnl_oos, n=N_BOOT, block=21, seed=RNG_SEED)
        bb_no_samples = {k: v for k, v in bb.items() if k != "samples"}
        metrics["bootstrap_oos"] = bb_no_samples
    except Exception as e:
        log(f"bootstrap failed: {e}")
        metrics["bootstrap_oos"] = None

    log("computing DSR...")
    try:
        metrics["dsr_oos"] = dsr(metrics["oos"]["sharpe"], pnl_oos, n_trials=1)
    except Exception as e:
        log(f"dsr failed: {e}")
        metrics["dsr_oos"] = None

    # §6 mini gates
    g1 = metrics["oos"]["sharpe"] >= 1.0
    g2 = (metrics.get("perm_p") is not None) and (metrics["perm_p"] < 0.05)
    g3 = (metrics.get("dsr_oos") is not None) and (metrics["dsr_oos"] >= 0.95)
    metrics["gates"] = {
        "G1_oos_sharpe_ge_1": bool(g1),
        "G2_perm_p_lt_005": bool(g2),
        "G3_dsr_ge_095": bool(g3),
        "pass_all": bool(g1 and g2 and g3),
    }

    # Curves
    curves = {
        "timestamps": [t.isoformat() for t in funding.index],
        "pnl_net": pnl_net.tolist(),
        "equity_net": np.cumsum(pnl_net).tolist(),
        "pnl_gross": pnl_gross.tolist(),
        "price_pnl": price_pnl.tolist(),
        "funding_pnl": funding_pnl.tolist(),
        "cost": cost.tolist(),
        "is_end_idx": int(is_end),
    }

    (OUT_DIR / "wave_k127_bis_carry.json").write_text(json.dumps(metrics, indent=2, default=str))
    (OUT_DIR / "wave_k127_curves.json").write_text(json.dumps(curves, default=str))

    log(f"done. total wall: {time.time() - t0:.1f}s")

    # Print markdown
    print_markdown(metrics)


def print_markdown(m: Dict[str, object]) -> None:
    g = m["gates"]
    p = m["full"]
    o = m["oos"]
    isd = m["is"]
    dec = m["decomposition"]
    sym_ranked = sorted(m["per_symbol"].items(), key=lambda kv: -kv[1]["n_long"])

    md = []
    md.append("# Wave K127 — BIS Crypto Carry Cross-Section (LEAN retry)")
    md.append("")
    md.append(f"**Universe:** {m['n_symbols']} symbols — {', '.join(m['symbols_used'])}")
    md.append(f"**Missing FR cache:** {', '.join(m['symbols_missing_fr']) or 'none'}")
    md.append(f"**Events:** {m['n_events']} (8h cadence); IS={isd['n_events']} / OOS={o['n_events']}")
    md.append("")
    md.append("## Headline performance (NET)")
    md.append("")
    md.append(f"| Window | Sharpe | MaxDD | TotalRet | Win% | N |")
    md.append(f"|---|---:|---:|---:|---:|---:|")
    md.append(f"| Full | {p['sharpe']:.3f} | {p['max_dd']:.4f} | {p['total_ret']:.4f} | {p['winrate']:.3f} | {m['n_events']} |")
    md.append(f"| IS (70%) | {isd['sharpe']:.3f} | {isd['max_dd']:.4f} | {isd['total_ret']:.4f} | {isd['winrate']:.3f} | {isd['n_events']} |")
    md.append(f"| OOS (30%) | {o['sharpe']:.3f} | {o['max_dd']:.4f} | {o['total_ret']:.4f} | {o['winrate']:.3f} | {o['n_events']} |")
    md.append(f"| Full GROSS | {p['sharpe_gross']:.3f} | — | — | — | — |")
    md.append("")
    md.append("## P&L Decomposition (full sample)")
    md.append("")
    md.append(f"| Component | Sum |")
    md.append(f"|---|---:|")
    md.append(f"| Price-return P&L | {dec['sum_price_pnl']:+.4f} |")
    md.append(f"| Funding P&L (received - paid) | {dec['sum_funding_pnl']:+.4f} |")
    md.append(f"| Trading cost (subtracted) | -{dec['sum_cost']:.4f} |")
    md.append(f"| **Net** | **{dec['sum_net']:+.4f}** |")
    md.append("")
    md.append("## Per-symbol exposure (events long / short, % of total events)")
    md.append("")
    md.append("| Symbol | Long | Short | %Long | %Short |")
    md.append("|---|---:|---:|---:|---:|")
    for s, ps in sym_ranked:
        md.append(f"| {s} | {ps['n_long']} | {ps['n_short']} | {ps['pct_long']:.1%} | {ps['pct_short']:.1%} |")
    md.append("")
    md.append("## Statistical tests")
    md.append("")
    md.append(f"- **Permutation p-value (NET Sharpe)** (shuffle ranks, n={N_PERM}): {m.get('perm_p_net')}")
    md.append(f"- **Permutation p-value (GROSS Sharpe, signal-only)** (n={N_PERM}): {m.get('perm_p_gross')}")
    psn = m.get("perm_sharpes_net_summary", {})
    psg = m.get("perm_sharpes_gross_summary", {})
    if psn:
        md.append(f"  - Null dist NET Sharpe: mean={psn['mean']:.2f}, 5/95%ile=[{psn['p5']:.2f}, {psn['p95']:.2f}]")
    if psg:
        md.append(f"  - Null dist GROSS Sharpe: mean={psg['mean']:.2f}, 5/95%ile=[{psg['p5']:.2f}, {psg['p95']:.2f}]")
    bb = m.get("bootstrap_oos")
    if bb:
        md.append(f"- **Block bootstrap OOS Sharpe** (n={N_BOOT}, block=21): mean={bb['mean']:.3f}, 95% CI [{bb['ci_lo']:.3f}, {bb['ci_hi']:.3f}]")
    md.append(f"- **DSR/PSR (OOS, n_trials=1)**: {m.get('dsr_oos')}")
    md.append("")
    md.append("## §6 Mini Gates")
    md.append("")
    md.append(f"- **G1 OOS Sharpe ≥ 1.0:** {'PASS' if g['G1_oos_sharpe_ge_1'] else 'FAIL'} (got {o['sharpe']:.3f})")
    md.append(f"- **G2 Permutation p < 0.05:** {'PASS' if g['G2_perm_p_lt_005'] else 'FAIL'} (got {m.get('perm_p')})")
    md.append(f"- **G3 DSR ≥ 0.95:** {'PASS' if g['G3_dsr_ge_095'] else 'FAIL'} (got {m.get('dsr_oos')})")
    md.append(f"- **Pass all 3:** {'YES' if g['pass_all'] else 'NO'}")
    md.append("")
    md.append("## Verdict")
    md.append("")
    bis_claim = (p["sharpe"] >= 7.0)
    if g["pass_all"]:
        md.append("**Strategy passes all 3 mini gates.** The BIS-style cross-sectional carry signal in the 13-symbol universe carries statistically meaningful edge after costs.")
    else:
        md.append("**Strategy does NOT clear all 3 mini gates.** See gate breakdown above.")
    md.append("")
    md.append(f"**BIS Sharpe 7-12 claim replication:** observed full-sample Sharpe = **{p['sharpe']:.2f}** → BIS-band {'REPLICATES' if bis_claim else 'DOES NOT REPLICATE'}.")
    print("\n".join(md))


if __name__ == "__main__":
    main()
