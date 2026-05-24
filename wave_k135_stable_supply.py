"""
Wave K135 — Stablecoin Supply Δ Risk-On Signal (R5-15)

Hypothesis (Boston Fed Stablecoins 2025 paper):
- USDC/USDT supply growth is a leading indicator of altcoin rallies.
- Weekly net stablecoin flow turning from negative to positive precedes
  altcoin upmoves. The cross of 7d net flow above (below) zero is a risk-on
  (risk-off) signal.

Method (pre-registered):
1. Fetch daily aggregate stablecoin market cap history from DefiLlama
   (per-asset endpoint: stablecoincharts/all?stablecoin={id}), summing
   USDT (id=1) + USDC (id=2) + DAI (id=5).
2. Compute daily Δ = cap_t - cap_{t-1}.
3. Rolling 7-day sum of Δ → weekly net flow (in $).
4. Signal:
   - V_long_only_zero_cross : net→pos cross => LONG basket. Hold until net→neg
     cross OR 30-day max.
   - V_long_short : net>0 => long, net<0 => short, hold until flip / 30d.
   - V_strict_threshold : same as long-only but threshold ±$500M instead of 0.
   - V_z_score : z-score of 7d flow vs 90d baseline, |z| > 1.5 triggers (long
     if z>+1.5, exit if z<-1.5; long-only).
5. Apply to BTCUSDT, ETHUSDT (primary) and 5 alts (DOGE, SOL, BNB, AVAX, LINK).
6. Per-symbol Sharpe + equal-weighted portfolio.
7. Costs: 0.07% per side per leg (round-trip 0.14%).

Audit:
- Whatever date range is intersection of DefiLlama + Binance daily.
- IS / OOS = 70% / 30%
- Per-symbol & portfolio Sharpe
- Walk-forward 4-fold on portfolio
- Permutation n=300 on portfolio signal (shuffle signal series, keep return
  series and entry-event timing distribution)
- Block bootstrap n=300 on OOS portfolio returns
- DSR with N_trials = 4 variants × 7 syms + 1 portfolio = 29
- Cost stress ×0.5 / ×1.5

Notes / honesty:
- Daily granularity (no intraday). Signal evaluated at daily close, executed
  next day's open-to-close return (we use close-to-close with one-bar
  lag of the signal).
- Stablecoin aggregate is in USD market cap; we don't isolate "real" inflow
  vs minted-but-on-bridge tokens. DefiLlama deduplicates across chains.
- 30d max-hold = 30 calendar bars (we use daily bars only — no intraday).
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
OUT_JSON = "/Users/nekonaomichi/crypto-lab/wave_k135_stable_supply.json"
OUT_CURVES = "/Users/nekonaomichi/crypto-lab/wave_k135_curves.json"
DEFI_CACHE = "/Users/nekonaomichi/crypto-lab/cache/k135_stable_history.parquet"

# ---------- universe ----------
SYMBOLS = ["BTC", "ETH", "DOGE", "SOL", "BNB", "AVAX", "LINK"]
PRIMARY = ["BTC", "ETH"]

# ---------- design constants ----------
PERIODS_PER_YEAR = 365            # daily bars
IS_FRAC = 0.70

TAKER_BPS = 4.0
SLIP_BPS = 3.0
COST_PER_SIDE = (TAKER_BPS + SLIP_BPS) / 1e4   # 0.07%

NET_FLOW_WIN = 7      # rolling 7-day sum of Δ
MAX_HOLD = 30         # hard exit after 30 calendar days
Z_WIN = 90            # baseline window for z-score
Z_TRIG = 1.5

# Variants
VARIANTS = ["V_long_only_zero_cross", "V_long_short", "V_strict_threshold", "V_z_score"]
STRICT_THRESHOLD_USD = 5.0e8       # ±$500M


# ---------- data ----------
def fetch_defillama_stablecoin(stablecoin_id: int, retries: int = 3) -> pd.DataFrame:
    url = f"https://stablecoins.llama.fi/stablecoincharts/all?stablecoin={stablecoin_id}"
    last_err = None
    for _ in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=60) as r:
                data = json.loads(r.read())
            rows = []
            for d in data:
                ts = int(d["date"])
                tot = d.get("totalCirculatingUSD") or d.get("totalCirculating") or {}
                cap = float(tot.get("peggedUSD", 0.0))
                rows.append((ts, cap))
            df = pd.DataFrame(rows, columns=["ts_unix", "cap_usd"])
            df["date"] = pd.to_datetime(df["ts_unix"], unit="s").dt.normalize()
            df = df.drop(columns="ts_unix").drop_duplicates("date").set_index("date").sort_index()
            return df
        except Exception as e:
            last_err = e
            time.sleep(2)
    raise RuntimeError(f"DefiLlama fetch failed for id={stablecoin_id}: {last_err}")


def load_stable_aggregate() -> pd.DataFrame:
    """Returns daily aggregate stablecoin market cap (USDT+USDC+DAI) in USD,
    cached locally to avoid re-hitting DefiLlama."""
    if os.path.exists(DEFI_CACHE):
        try:
            df = pd.read_parquet(DEFI_CACHE)
            # cache valid if last row is within ~3 days of today
            if (pd.Timestamp.utcnow().tz_localize(None) - df.index.max()).days < 3:
                print(f"  [cache] using {DEFI_CACHE} (last={df.index.max().date()})")
                return df
        except Exception:
            pass

    parts = {}
    for sid, sym in [(1, "USDT"), (2, "USDC"), (5, "DAI")]:
        print(f"  fetching DefiLlama: {sym} (id={sid})...")
        d = fetch_defillama_stablecoin(sid)
        d = d.rename(columns={"cap_usd": sym})
        parts[sym] = d

    df = pd.concat(parts.values(), axis=1).sort_index()
    df = df.fillna(0.0)
    df["TOTAL"] = df[["USDT", "USDC", "DAI"]].sum(axis=1)
    try:
        df.to_parquet(DEFI_CACHE)
    except Exception:
        pass
    return df


def load_close_panel() -> pd.DataFrame:
    """Daily close panel for the 7 symbols (intersect on date)."""
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


# ---------- signal construction ----------
def build_signals(stable: pd.DataFrame) -> pd.DataFrame:
    """Build all four signal series indexed by date.

    Each column ∈ {-1, 0, +1} (target position MULTIPLIER, before max-hold logic).
    """
    s = stable.copy()
    s["delta"] = s["TOTAL"].diff()
    s["net7"] = s["delta"].rolling(NET_FLOW_WIN).sum()

    # ---- V_long_only_zero_cross ----
    # state machine: enter long when net7 crosses >0, exit when crosses <0
    sig_lo = np.zeros(len(s))
    state = 0
    net = s["net7"].values
    for i in range(1, len(s)):
        if np.isnan(net[i]) or np.isnan(net[i - 1]):
            sig_lo[i] = state
            continue
        if state == 0 and net[i - 1] <= 0 and net[i] > 0:
            state = 1
        elif state == 1 and net[i - 1] >= 0 and net[i] < 0:
            state = 0
        sig_lo[i] = state

    # ---- V_long_short ----
    sig_ls = np.zeros(len(s))
    state = 0
    for i in range(1, len(s)):
        if np.isnan(net[i]) or np.isnan(net[i - 1]):
            sig_ls[i] = state
            continue
        if net[i - 1] <= 0 and net[i] > 0:
            state = 1
        elif net[i - 1] >= 0 and net[i] < 0:
            state = -1
        sig_ls[i] = state

    # ---- V_strict_threshold ----
    sig_st = np.zeros(len(s))
    state = 0
    for i in range(1, len(s)):
        if np.isnan(net[i]) or np.isnan(net[i - 1]):
            sig_st[i] = state
            continue
        if state == 0 and net[i - 1] <= +STRICT_THRESHOLD_USD and net[i] > +STRICT_THRESHOLD_USD:
            state = 1
        elif state == 1 and net[i - 1] >= -STRICT_THRESHOLD_USD and net[i] < -STRICT_THRESHOLD_USD:
            state = 0
        sig_st[i] = state

    # ---- V_z_score ----
    mu = s["net7"].rolling(Z_WIN).mean()
    sd = s["net7"].rolling(Z_WIN).std()
    z = (s["net7"] - mu) / sd
    sig_z = np.zeros(len(s))
    state = 0
    z_arr = z.values
    for i in range(1, len(s)):
        if np.isnan(z_arr[i]):
            sig_z[i] = state
            continue
        if state == 0 and z_arr[i] > Z_TRIG:
            state = 1
        elif state == 1 and z_arr[i] < -Z_TRIG:
            state = 0
        sig_z[i] = state

    out = pd.DataFrame({
        "net7": s["net7"],
        "V_long_only_zero_cross": sig_lo,
        "V_long_short": sig_ls,
        "V_strict_threshold": sig_st,
        "V_z_score": sig_z,
    }, index=s.index)
    return out


def apply_max_hold(sig: np.ndarray, max_hold: int) -> np.ndarray:
    """Force-exit a non-zero position if it has been held > max_hold consecutive
    bars without flipping. Returns a new array.
    """
    out = sig.copy()
    hold = 0
    last_state = 0
    forced_exit_until_flip = False
    for i in range(len(out)):
        cur = out[i]
        if forced_exit_until_flip:
            # remain at 0 until the underlying signal flips to a different non-zero value
            if cur == 0:
                forced_exit_until_flip = False
                last_state = 0
                hold = 0
            elif cur != last_state:
                forced_exit_until_flip = False
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
                    forced_exit_until_flip = True
            else:
                last_state = cur
                hold = 1
    return out


# ---------- pnl ----------
def per_symbol_pnl(price: pd.Series, position: pd.Series, cost_mult: float = 1.0) -> pd.DataFrame:
    """Daily PnL for one symbol given a target position series ∈ {-1,0,+1}.

    Position taken at close[t] earns close[t]→close[t+1] return — i.e. we lag
    the position by 1 bar relative to the return series.
    Cost = |Δpos| × per-side cost.
    """
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
    """Run a single variant signal across all symbols, return per-symbol pnl
    series and an equal-weight portfolio series.

    Each per-symbol pnl DataFrame is REINDEXED to the price_panel master index
    (so slicing by integer position is consistent across symbols and matches
    the global IS/OOS cut). Missing rows -> 0.0 pnl_net.
    """
    pnl_by_sym = {}
    master_idx = price_panel.index
    for sym in price_panel.columns:
        df = pd.concat([price_panel[sym].rename("price"), sig.rename("pos")], axis=1).dropna()
        if len(df) < 30:
            continue
        pnl = per_symbol_pnl(df["price"], df["pos"], cost_mult=cost_mult)
        pnl = pnl.reindex(master_idx).fillna(0.0)
        pnl_by_sym[sym] = pnl
    # equal-weight portfolio (each symbol contributes only when its price exists;
    # average over the *active* symbols per bar).
    pnl_net_concat = pd.concat({k: v["pnl_net"] for k, v in pnl_by_sym.items()}, axis=1)
    # active-mask: a symbol is active when its price was available (we tracked
    # via pos_lag presence above). We use the original mask from price_panel.
    active_mask = price_panel.notna()
    # Align active_mask to the per-symbol pnl columns
    active_mask = active_mask[pnl_net_concat.columns]
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
    """Deflated Sharpe Ratio (Bailey & López de Prado 2014).

    Inputs are an *annualized* Sharpe; we convert to per-bar before applying
    the formula because the SR-variance expression assumes per-observation SR.
    """
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


def permutation_test_signal(price_panel: pd.DataFrame, sig: pd.Series, n: int = 300, seed: int = 42) -> dict:
    """Circular-shift the signal series by random offsets. Preserves signal's own
    autocorrelation / time-in-market while destroying its alignment to returns.
    """
    rng = np.random.default_rng(seed)
    base = variant_portfolio(price_panel, sig)["portfolio"]
    base_sr = sharpe(base.values)
    sig_vals = sig.values
    n_len = len(sig_vals)
    null_srs = []
    for _ in range(n):
        shift = int(rng.integers(NET_FLOW_WIN * 3, n_len - NET_FLOW_WIN * 3))
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
    """§6 gates:
    G1 OOS Sharpe >= 1.0
    G2 OOS max_dd > -0.30 (i.e. min drawdown not worse than -30%)
    G3 OOS bootstrap lower-CI Sharpe > 0
    G4 Permutation p-value < 0.05
    G5 DSR > 0.95
    G6 OOS / IS Sharpe ratio >= 0.5 (no severe IS overfit)
    """
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
    print("Wave K135 — Stablecoin Supply Δ Risk-On Signal (R5-15)")
    print("=" * 78)

    # 1) data
    print("Loading DefiLlama stablecoin aggregate...")
    stable = load_stable_aggregate()
    print(f"  stable shape: {stable.shape}  range: {stable.index.min().date()} → {stable.index.max().date()}")
    print(f"  last TOTAL: ${stable['TOTAL'].iloc[-1] / 1e9:.1f}B  (USDT ${stable['USDT'].iloc[-1]/1e9:.1f}B, USDC ${stable['USDC'].iloc[-1]/1e9:.1f}B, DAI ${stable['DAI'].iloc[-1]/1e9:.1f}B)")

    print("Loading price panel (daily close)...")
    panel = load_close_panel()
    print(f"  panel shape: {panel.shape}  range: {panel.index.min().date()} → {panel.index.max().date()}")

    # 2) align to intersection
    sigs = build_signals(stable)
    common = sigs.index.intersection(panel.index)
    sigs = sigs.loc[common]
    panel = panel.loc[common]
    print(f"  intersection: {len(common)} days, {common.min().date()} → {common.max().date()}")

    # 3) apply max-hold to signals
    sig_cooked = {}
    for v in VARIANTS:
        raw = sigs[v].values.astype(float)
        cooked = apply_max_hold(raw, MAX_HOLD)
        sig_cooked[v] = pd.Series(cooked, index=sigs.index)

    # 4) per-variant: per-symbol + portfolio
    n_full = len(panel)
    cut = int(n_full * IS_FRAC)

    results = {
        "meta": {
            "task": "Wave K135 Stablecoin Supply Delta Risk-On",
            "data_source": "DefiLlama stablecoincharts/all per-asset (USDT id=1, USDC id=2, DAI id=5)",
            "symbols": SYMBOLS,
            "primary": PRIMARY,
            "date_range": [str(common.min().date()), str(common.max().date())],
            "n_days": n_full,
            "IS_cut": cut,
            "cost_per_side_bps": (TAKER_BPS + SLIP_BPS),
            "net_flow_window_days": NET_FLOW_WIN,
            "max_hold_days": MAX_HOLD,
            "z_window_days": Z_WIN,
            "z_trigger": Z_TRIG,
            "strict_threshold_usd": STRICT_THRESHOLD_USD,
            "variants": VARIANTS,
        },
        "stablecoin_last": {
            "date": str(stable.index.max().date()),
            "USDT_usd": float(stable["USDT"].iloc[-1]),
            "USDC_usd": float(stable["USDC"].iloc[-1]),
            "DAI_usd": float(stable["DAI"].iloc[-1]),
            "TOTAL_usd": float(stable["TOTAL"].iloc[-1]),
            "net7_last_usd": float(sigs["net7"].iloc[-1]),
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
        # cost stress on full series
        port_lo = variant_portfolio(panel, sig_cooked[v], cost_mult=0.5)["portfolio"]
        port_hi = variant_portfolio(panel, sig_cooked[v], cost_mult=1.5)["portfolio"]
        cost_stress = {
            "cost_x0.5_OOS_sharpe": sharpe(port_lo.values[cut:]),
            "cost_x1.0_OOS_sharpe": oos_m["sharpe"],
            "cost_x1.5_OOS_sharpe": sharpe(port_hi.values[cut:]),
        }
        # permutation (only on this variant; n=200 to fit time budget)
        print(f"  running permutation (n=200)...")
        perm = permutation_test_signal(panel, sig_cooked[v], n=200, seed=42 + VARIANTS.index(v))
        # DSR
        n_trials = 4 * len(SYMBOLS) + 4  # variants × syms + portfolios
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
        # also save per-symbol curves for primary
        for sym in PRIMARY:
            if sym in out["per_symbol"]:
                curves[f"{v}__{sym}"] = equity_curve(out["per_symbol"][sym]["pnl_net"], every=1)

    # 5) signal series snapshot (last 60 days)
    tail = sigs[["net7"] + VARIANTS].tail(60)
    results["signal_tail_60d"] = [
        {
            "date": str(idx.date()),
            "net7_usd": float(row["net7"]) if not math.isnan(row["net7"]) else None,
            **{v: float(row[v]) for v in VARIANTS},
        }
        for idx, row in tail.iterrows()
    ]

    results["elapsed_sec"] = time.time() - t0

    with open(OUT_JSON, "w") as f:
        json.dump(results, f, indent=2, default=str)
    with open(OUT_CURVES, "w") as f:
        json.dump(curves, f, indent=2, default=str)

    print(f"\nWrote: {OUT_JSON}")
    print(f"Wrote: {OUT_CURVES}")
    print(f"Elapsed: {results['elapsed_sec']:.1f}s")

    # print summary
    print("\n" + "=" * 78)
    print("VARIANT SUMMARY (portfolio)")
    print("=" * 78)
    print(f"{'variant':28s}  {'IS sr':>7s}  {'OOS sr':>7s}  {'OOS DD':>7s}  {'TIM%':>5s}  {'perm_p':>7s}  {'DSR':>6s}  {'gates':>6s}")
    for v in VARIANTS:
        p = results["variants"][v]["portfolio"]
        print(f"{v:28s}  {p['IS']['sharpe']:>7.2f}  {p['OOS']['sharpe']:>7.2f}  {p['OOS']['max_dd']:>7.2%}  {p['time_in_market_pct']:>5.1f}  {p['permutation']['p_value']:>7.3f}  {p['DSR']:>6.3f}  {p['gates']['passed']:>2d}/{p['gates']['total']:<2d}")


if __name__ == "__main__":
    main()
