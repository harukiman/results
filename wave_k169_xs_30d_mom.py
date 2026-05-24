"""
Wave K169 — XS 30-day Momentum (R5-12, subnet study generalization)

Hypothesis (arxiv 2603.29751):
- A cross-sectional 30-day winners-minus-losers strategy on the subnet study
  universe shows NW t-stat 3.69 with ~0.68%/day mean spread.
- K169 tests whether this **pure 30d momentum** signal generalizes to MEXC
  perp universe (top liquidity, mainly large-mid caps with reliable 4H bars).

Distinction vs K134 (Dobrynskaya):
- K134 combined a short-horizon (21d) mom sleeve with a long-horizon (60d)
  reversal sleeve. K169 tests **single horizon (30d) pure momentum** — the
  raw subnet finding without any reversal switch.

Method (pre-registered, single composite design):
1. Build 4H close panel for top-30 liquid symbols (drop pure-meme noise floor).
2. At each weekly rebalance (every 42 4H bars = 7 days):
   - mom_30d = 30-day lookback return per symbol, SKIPPING the last 1 day
     to avoid the well-documented 1-day reversal contamination.
     i.e. mom = P_{t-1d} / P_{t-31d} - 1, then shifted +1 bar so signal is
     known at decision time.
3. Cross-sectional rank per rebalance bar:
   - Long top-N by mom_30d
   - Short bottom-N
   - Equal weight, dollar-neutral, gross = 2.0 (V_top5_w7 default).
4. Hold positions until next rebalance.
5. Costs: 0.07% per side per leg.

Variants:
- V_top5_w7  : 5L/5S, weekly (primary)
- V_top10_w7 : broader 10L/10S, weekly
- V_top5_w14 : 5L/5S, bi-weekly
- V_top3_w7  : concentrated 3L/3S, weekly

Audit:
- 730d, IS 70% / OOS 30%
- Per-variant Portfolio Sharpe
- WF 4-fold on primary
- Permutation n=300 (shuffle XS ranks per rebalance)
- Block bootstrap n=300 on OOS
- DSR with N_trials = 4
- Cost stress ±50% on primary
- Correlation with K134 / K116 / K133 portfolio curves
"""

from __future__ import annotations

import json
import math
import time
import warnings
from math import erf

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

CACHE = "/Users/nekonaomichi/crypto-lab/cache"
OUT_JSON = "/Users/nekonaomichi/crypto-lab/wave_k169_xs_30d_mom.json"
OUT_CURVES = "/Users/nekonaomichi/crypto-lab/wave_k169_curves.json"

# ---------- universe ----------
# Top ~30 by liquidity + reliable 4H 730d availability (drop pure-meme noise).
# Memes intentionally kept light (DOGE, SHIB, PEPE only — drop BONK, WIF,
# POPCAT, FLOKI, BOME so the panel is dominated by L1/L2/DeFi names).
SYMBOLS = [
    "BTC", "ETH", "SOL", "XRP", "BNB", "ADA", "TRX", "DOGE", "LINK", "AVAX",
    "DOT", "LTC", "ATOM", "NEAR", "ARB", "OP", "APT", "SUI", "FIL", "ETC",
    "INJ", "TIA", "ICP", "AAVE", "UNI", "RUNE", "SEI", "PEPE", "SHIB", "ENA",
]

# ---------- design constants ----------
BARS_PER_DAY = 6                          # 4H bars
PERIODS_PER_YEAR = BARS_PER_DAY * 365     # 2190
LOOKBACK_TOTAL_BARS = 31 * BARS_PER_DAY   # 31 days back
SKIP_BARS = 1 * BARS_PER_DAY              # skip last 1 day (1-day reversal)
LOOKBACK_END_BARS = SKIP_BARS             # window end = t - 1d
LOOKBACK_START_BARS = LOOKBACK_TOTAL_BARS # window start = t - 31d
# → window length 30d (from t-31d to t-1d)

REBAL_BARS_W7 = 7 * BARS_PER_DAY          # 42 bars
REBAL_BARS_W14 = 14 * BARS_PER_DAY        # 84 bars

IS_FRAC = 0.70

TAKER_BPS = 4.0
SLIP_BPS = 3.0
COST_PER_SIDE = (TAKER_BPS + SLIP_BPS) / 1e4   # 0.07%

VARIANTS = {
    "V_top5_w7":  {"top_n": 5,  "rebal_bars": REBAL_BARS_W7,  "primary": True},
    "V_top10_w7": {"top_n": 10, "rebal_bars": REBAL_BARS_W7,  "primary": False},
    "V_top5_w14": {"top_n": 5,  "rebal_bars": REBAL_BARS_W14, "primary": False},
    "V_top3_w7":  {"top_n": 3,  "rebal_bars": REBAL_BARS_W7,  "primary": False},
}


# ---------- data ----------
def load_close_panel() -> pd.DataFrame:
    """Wide panel of 4H close prices: index=ts, columns=symbol."""
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


def mom_30d_signal(panel: pd.DataFrame) -> pd.DataFrame:
    """30-day lookback skipping last 1 day:
       mom_t = P_{t-1d} / P_{t-31d} - 1
       then shifted +1 so signal at t is decision-time known.
    """
    end = panel.shift(LOOKBACK_END_BARS)      # P_{t-1d}
    start = panel.shift(LOOKBACK_START_BARS)  # P_{t-31d}
    sig = end / start - 1.0
    return sig.shift(1)


# ---------- positions ----------
def cross_sectional_long_short(
    sig_df: pd.DataFrame, top_n: int
) -> pd.DataFrame:
    """At each row, long top_n / short bottom_n by sig. Equal-weighted,
    dollar-neutral. Per-leg weight = 1/top_n so gross = 2.0.
    """
    out = pd.DataFrame(0.0, index=sig_df.index, columns=sig_df.columns)
    arr = sig_df.values
    n_rows, _ = arr.shape
    w_each = 1.0 / top_n
    for i in range(n_rows):
        row = arr[i, :]
        valid = ~np.isnan(row)
        if valid.sum() < 2 * top_n:
            continue
        idx_valid = np.where(valid)[0]
        order = idx_valid[np.argsort(row[idx_valid])]  # ascending
        shorts = order[:top_n]
        longs = order[-top_n:]
        out.iloc[i, longs] = w_each
        out.iloc[i, shorts] = -w_each
    return out


def rebalance_only(weights_full: pd.DataFrame, rebal_bars: int) -> pd.DataFrame:
    """Hold weights from rebalance bar until next rebalance bar."""
    n = len(weights_full)
    mask = np.zeros(n, dtype=bool)
    mask[::rebal_bars] = True
    held = weights_full.where(
        pd.Series(mask, index=weights_full.index), other=np.nan
    )
    held = held.ffill().fillna(0.0)
    return held


# ---------- pnl ----------
def variant_pnl(
    panel: pd.DataFrame, sig: pd.DataFrame, top_n: int,
    rebal_bars: int, cost_mult: float = 1.0,
) -> pd.DataFrame:
    raw_w = cross_sectional_long_short(sig, top_n)
    held = rebalance_only(raw_w, rebal_bars)
    ret = panel.pct_change()
    w_lagged = held.shift(1).fillna(0.0)
    pnl_gross = (w_lagged * ret).sum(axis=1)
    turn = (held - held.shift(1).fillna(0.0)).abs().sum(axis=1)
    cost = turn * COST_PER_SIDE * cost_mult
    return pd.DataFrame({
        "pnl_gross": pnl_gross,
        "cost": cost,
        "pnl_net": pnl_gross - cost,
    })


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


def block_bootstrap_sharpe(
    ret: np.ndarray, block: int = 20, n: int = 300, seed: int = 7
) -> tuple[float, float]:
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
        lo = k * fold_size
        hi = (k + 1) * fold_size if k < 3 else n
        sub = port_returns.values[lo:hi]
        wf.append({
            "fold": k,
            "sharpe": sharpe(sub),
            "max_dd": max_dd(sub),
            "total_return": float((1 + pd.Series(sub).fillna(0)).prod() - 1),
            "n_bars": int(len(sub)),
        })
    return wf


# ---------- permutation ----------
def permutation_test(
    panel: pd.DataFrame, sig: pd.DataFrame, top_n: int, rebal_bars: int,
    n: int = 300, seed: int = 42,
) -> dict:
    """Shuffle XS sig values among valid symbols at each rebalance bar.
    Destroys directional edge, keeps schedule + leg sizes + turnover structure.
    """
    rng = np.random.default_rng(seed)
    base_port = variant_pnl(panel, sig, top_n, rebal_bars)["pnl_net"]
    base_sr = sharpe(base_port.values)

    n_rows = len(panel)
    rebal_idx = np.arange(0, n_rows, rebal_bars)
    null_srs = []

    sig_vals = sig.values  # base reference (may be read-only view)
    for _ in range(n):
        sp = sig_vals.copy()  # writable copy
        for r in rebal_idx:
            row = sp[r, :].copy()
            v = ~np.isnan(row)
            if v.sum() >= 2 * top_n:
                perm = rng.permutation(row[v])
                row[v] = perm
                sp[r, :] = row
        sig_perm = pd.DataFrame(sp, index=sig.index, columns=sig.columns)
        port_perm = variant_pnl(panel, sig_perm, top_n, rebal_bars)["pnl_net"]
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


# ---------- correlation with related strategies ----------
def load_external_curves() -> dict[str, pd.Series]:
    """Load equity curves from K134, K116, K133 and convert to per-step
    returns indexed by ts where possible.
    """
    out = {}

    # K134 — V_60_40
    try:
        with open("/Users/nekonaomichi/crypto-lab/wave_k134_curves.json") as f:
            d = json.load(f)
        if "V_60_40" in d and len(d["V_60_40"]) > 0:
            ts = pd.to_datetime([x["ts"] for x in d["V_60_40"]])
            eq = pd.Series([x["eq"] for x in d["V_60_40"]], index=ts)
            out["K134_V_60_40"] = eq.pct_change().dropna()
    except Exception as e:
        print(f"  K134 curve load failed: {e}")

    # K116 — portfolio_equity (timestamps aligned)
    try:
        with open("/Users/nekonaomichi/crypto-lab/wave_k116_curves.json") as f:
            d = json.load(f)
        ts = pd.to_datetime(d["timestamps"])
        eq = pd.Series(d["portfolio_equity"], index=ts)
        out["K116_vol_only"] = eq.pct_change().dropna()
    except Exception as e:
        print(f"  K116 curve load failed: {e}")

    # K133 — V_rev_7d_z15 (no timestamps, only equity_curve list).
    # We assume daily-ish cadence; for correlation we need a shared timeline,
    # so we record but skip if mismatched.
    try:
        with open("/Users/nekonaomichi/crypto-lab/wave_k133_curves.json") as f:
            d = json.load(f)
        if "V_rev_7d_z15" in d:
            eq_list = d["V_rev_7d_z15"]["equity_curve"]
            # no timestamps: skip alignment-based correlation; mark as unavailable
            out["K133_V_rev_7d_z15__no_ts"] = pd.Series(eq_list)
    except Exception as e:
        print(f"  K133 curve load failed: {e}")

    return out


def corr_with_externals(port: pd.Series, ext: dict[str, pd.Series]) -> dict:
    """Resample everything to 1D returns aligned on union index."""
    out = {}
    p_daily = (1 + port.fillna(0)).resample("1D").prod() - 1

    for name, r in ext.items():
        if "__no_ts" in name:
            out[name] = {"corr": None, "note": "no timestamps, alignment impossible"}
            continue
        try:
            r_daily = (1 + r.fillna(0)).resample("1D").prod() - 1
            joined = pd.concat(
                [p_daily.rename("k169"), r_daily.rename("ext")], axis=1
            ).dropna()
            if len(joined) < 30:
                out[name] = {"corr": None, "n_overlap": int(len(joined)), "note": "insufficient overlap"}
            else:
                out[name] = {
                    "corr": float(joined["k169"].corr(joined["ext"])),
                    "n_overlap": int(len(joined)),
                }
        except Exception as e:
            out[name] = {"corr": None, "error": str(e)}
    return out


# ---------- main ----------
def main():
    t0 = time.time()
    print("=" * 78)
    print("Wave K169 — XS 30-day Momentum (R5-12, subnet study generalization)")
    print("=" * 78)

    print(f"Loading {len(SYMBOLS)} symbols...")
    panel = load_close_panel()
    panel = panel.dropna(how="all")
    print(f"  panel shape: {panel.shape}  range: {panel.index.min()} → {panel.index.max()}")
    n_full = len(panel)
    cut = int(n_full * IS_FRAC)

    print("Computing 30d (skip-1d) momentum signal...")
    sig = mom_30d_signal(panel)

    # Per-variant
    print("Running variants...")
    portfolio_metrics = {}
    curves = {}
    pnl_dict = {}
    primary_name = None
    for vname, vp in VARIANTS.items():
        pnl = variant_pnl(panel, sig, vp["top_n"], vp["rebal_bars"])
        port = pnl["pnl_net"]
        pnl_dict[vname] = port
        ci = block_bootstrap_sharpe(port.values[cut:], block=20, n=300)
        portfolio_metrics[vname] = {
            "params": {"top_n": vp["top_n"], "rebal_bars": vp["rebal_bars"], "primary": vp["primary"]},
            "IS": slice_metrics(port, 0, cut),
            "OOS": slice_metrics(port, cut, n_full),
            "FULL": slice_metrics(port, 0, n_full),
            "OOS_sharpe_CI95": ci,
        }
        curves[vname] = equity_curve(port, every=6)
        if vp["primary"]:
            primary_name = vname

    pri_port = pnl_dict[primary_name]
    pri_metrics = portfolio_metrics[primary_name]

    # Walk-forward
    print(f"Walk-forward 4-fold ({primary_name})...")
    wf = walk_forward_4fold(pri_port)

    # Permutation
    print(f"Permutation test ({primary_name}, n=300)...")
    pri_params = VARIANTS[primary_name]
    perm = permutation_test(
        panel, sig, pri_params["top_n"], pri_params["rebal_bars"], n=300, seed=42
    )
    print(f"  base SR={perm['base_sharpe']:.3f}  null_mean={perm['null_mean']:.3f}  "
          f"null_p95={perm['null_p95']:.3f}  p={perm['p_value']:.3f}")

    # Cost stress on primary
    print(f"Cost stress ±50% ({primary_name})...")
    cost_stress = {}
    for mult, name in [(0.5, "low"), (1.0, "base"), (1.5, "high")]:
        pnl_s = variant_pnl(panel, sig, pri_params["top_n"],
                            pri_params["rebal_bars"], cost_mult=mult)["pnl_net"]
        cost_stress[name] = {
            "OOS_sharpe": sharpe(pnl_s.values[cut:]),
            "OOS_max_dd": max_dd(pnl_s.values[cut:]),
            "OOS_total_return": float((1 + pd.Series(pnl_s.values[cut:]).fillna(0)).prod() - 1),
        }

    # DSR over 4 variants
    n_oos = n_full - cut
    dsr_map = {
        v: dsr(m["OOS"]["sharpe"], n_oos, n_trials=len(VARIANTS))
        for v, m in portfolio_metrics.items()
    }

    # External correlations
    print("Loading external curves (K134/K116/K133)...")
    ext = load_external_curves()
    print(f"  loaded {len(ext)} external curves")
    corrs = corr_with_externals(pri_port, ext)
    for k, v in corrs.items():
        print(f"  corr {k}: {v}")

    # §6 mini gates — primary variant
    pri = pri_metrics
    gates = {
        "G1_OOS_Sharpe_gt_0.5":          pri["OOS"]["sharpe"] > 0.5,
        "G2_OOS_MaxDD_gt_-0.30":         pri["OOS"]["max_dd"] > -0.30,
        "G3_BlockBoot_CI95_low_gt_0":    pri["OOS_sharpe_CI95"][0] > 0,
        "G4_Perm_p_lt_0.05":             perm["p_value"] < 0.05,
        "G5_DSR_gt_0.95":                (dsr_map[primary_name] if not math.isnan(dsr_map[primary_name]) else 0) > 0.95,
        "G6_CostStress_high_OOS_sr_gt_0.3": cost_stress["high"]["OOS_sharpe"] > 0.3,
    }
    n_pass = sum(gates.values())
    verdict = (
        "ACCEPT" if n_pass >= 5
        else "CONDITIONAL" if n_pass >= 3
        else "REJECT"
    )

    # Subnet generalizes? heuristic
    subnet_target_daily = 0.0068  # 0.68%/day quoted spread
    pri_daily = pri["OOS"]["ann_return"] / 365 if pri["OOS"]["n_bars"] > 0 else 0
    subnet_generalizes = (
        pri["OOS"]["sharpe"] > 0.5 and perm["p_value"] < 0.05
        and pri["OOS"]["total_return"] > 0
    )

    # Persist
    with open(OUT_CURVES, "w") as f:
        json.dump(curves, f, indent=2)

    result = {
        "wave": "K169",
        "title": "XS 30-day Momentum (R5-12, subnet study generalization)",
        "as_of": pd.Timestamp.utcnow().isoformat(),
        "symbols": SYMBOLS,
        "n_symbols": len(SYMBOLS),
        "panel_shape": list(panel.shape),
        "panel_range": [str(panel.index.min()), str(panel.index.max())],
        "design": {
            "bars_per_day": BARS_PER_DAY,
            "lookback_total_bars": LOOKBACK_TOTAL_BARS,
            "skip_bars": SKIP_BARS,
            "lookback_window": "P_{t-1d}/P_{t-31d}-1 (30d effective)",
            "rebal_bars_w7": REBAL_BARS_W7,
            "rebal_bars_w14": REBAL_BARS_W14,
            "is_frac": IS_FRAC,
            "costs": {"taker_bps": TAKER_BPS, "slip_bps": SLIP_BPS, "per_side_pct": COST_PER_SIDE * 100},
            "primary_variant": primary_name,
        },
        "variants": {k: v for k, v in VARIANTS.items()},
        "portfolio": portfolio_metrics,
        "walk_forward_primary": wf,
        "permutation_test_primary": perm,
        "cost_stress_primary": cost_stress,
        "DSR": dsr_map,
        "external_correlations": corrs,
        "subnet_generalization": {
            "subnet_target_daily_pct": subnet_target_daily * 100,
            "k169_OOS_implied_daily_pct": pri_daily * 100,
            "criteria": "OOS_SR>0.5 AND perm_p<0.05 AND OOS_total_ret>0",
            "generalizes": bool(subnet_generalizes),
        },
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
    print(f"PRIMARY VARIANT: {primary_name}")
    print(f"  IS  Sharpe: {pri['IS']['sharpe']:.3f}")
    print(f"  OOS Sharpe: {pri['OOS']['sharpe']:.3f}  "
          f"CI95=[{pri['OOS_sharpe_CI95'][0]:.2f},{pri['OOS_sharpe_CI95'][1]:.2f}]")
    print(f"  OOS MaxDD : {pri['OOS']['max_dd']:.2%}")
    print(f"  OOS TotRet: {pri['OOS']['total_return']:+.2%}")
    print(f"  OOS AnnRet: {pri['OOS']['ann_return']:+.2%}")
    print(f"  OOS AnnVol: {pri['OOS']['ann_vol']:.2%}")
    print(f"  OOS WinRt : {pri['OOS']['win_rate']:.2%}")

    print()
    print("VARIANT COMPARISON:")
    print(f"  {'variant':12s} {'IS_SR':>7s} {'OOS_SR':>7s} {'OOS_DD':>8s} "
          f"{'FULL_ret':>9s} {'DSR':>6s}")
    for v, m in portfolio_metrics.items():
        print(f"  {v:12s} {m['IS']['sharpe']:7.2f} {m['OOS']['sharpe']:7.2f} "
              f"{m['OOS']['max_dd']:8.2%} {m['FULL']['total_return']:+9.2%} "
              f"{dsr_map[v]:6.2f}")

    print()
    print("WALK-FORWARD PRIMARY:")
    for f_ in wf:
        print(f"  fold{f_['fold']}: SR={f_['sharpe']:6.2f}  "
              f"DD={f_['max_dd']:7.2%}  ret={f_['total_return']:+7.2%}")

    print()
    print("COST STRESS PRIMARY OOS:")
    for k, v in cost_stress.items():
        print(f"  {k:5s}: SR={v['OOS_sharpe']:6.2f}  DD={v['OOS_max_dd']:7.2%}  "
              f"ret={v['OOS_total_return']:+7.2%}")

    print()
    print("CORRELATIONS WITH RELATED STRATEGIES:")
    for k, v in corrs.items():
        print(f"  {k}: {v}")

    print()
    print(f"SUBNET GENERALIZATION: {'YES' if subnet_generalizes else 'NO'}")
    print(f"  K169 OOS implied daily ret: {pri_daily*100:.3f}%  vs subnet target 0.68%")

    print()
    print(f"GATES ({primary_name} primary):")
    for k, v in gates.items():
        print(f"  {k}: {'PASS' if v else 'FAIL'}")
    print(f"\nVERDICT: {verdict} ({n_pass}/6 gates pass)")
    print(f"Elapsed: {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
