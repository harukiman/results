"""Wave K174 - CEX vs DEX (Hyperliquid) Funding-Rate Integration (R6-1).

Hypothesis (MDPI 14/2/346):
  CEX funding LEADS DEX funding with ~61% integration coefficient. When the
  DEX (Hyperliquid) FR lags the CEX (Bybit) FR by X std-devs, expect mean-
  reversion of DEX -> CEX. Trade the DEX side accordingly: when DEX FR is
  notably BELOW CEX FR (spread > thr) it is "lagging high"; DEX FR is
  expected to catch up upward, perp price reverts down when funding settles,
  so SHORT the perp. Symmetric on the other side.

Data:
  - HL hourly FR: K163 cache at cache/k163_hl/hl_fr_{SYM}.parquet
  - Bybit 8h FR:  cache/bybit_fr_{SYM}USDT_730d.parquet
  - Common 8 symbols: BTC ETH SOL BNB DOGE AVAX LINK XRP
    (LINK missing from K163 cache -> drop, see runtime; SUI extra)

Method (pre-registered, GROSS + NET, K173 lesson):
  1. For each 8h Bybit funding event T:
       Aggregate HL hourly FR over [T-8h, T] (sum).
       spread_T = bybit_fr_T - hl_fr_8hsum_T
       Lag 1 (signal at T -> trade enters at T, exits at T + hold*8h).
  2. Signal (z-score across rolling 30-event window):
       z > +thr  -> Bybit FR much higher than HL aggregate
                    -> HL likely to catch up (rise) AND Bybit perp price
                       reverts DOWN as funding settles
                    -> SHORT Bybit perp.
       z < -thr  -> LONG Bybit perp.
  3. Hold N funding events (each 8h), exit at the close of the N-th event.
  4. Costs: 0.07% per side per leg (entry+exit).

Variants:
  - V_z2_h1   : z-score > 2, 1-event hold (primary)
  - V_z2_h3   : z-score > 2, 3-event hold
  - V_abs1bp  : |spread| > 1bp absolute threshold, 1-event hold
  - V_top_xs  : cross-section largest spread (pick 1 each side), 1-event hold

Audit: IS/OOS 70/30, WF 4-fold, perm n=300, bootstrap n=300, DSR (N=4),
       cost stress. PnL is 8h-event-based.

Correlation: vs K133 (Funding mean-reversion 7d).
"""
from __future__ import annotations

import json
import time
from math import erf, sqrt
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

ROOT = Path("/Users/nekonaomichi/crypto-lab")
CACHE = ROOT / "cache"
HL_CACHE = CACHE / "k163_hl"
COST_BPS = 0.0007  # 7 bps per side per leg

# 8 candidate symbols from K163 / Bybit overlap.
SYMBOLS = ["BTC", "ETH", "SOL", "BNB", "DOGE", "AVAX", "XRP", "SUI"]

# Funding event cadence: 8h on Bybit -> 365*24/8 = 1095 events / year.
EVENTS_PER_YEAR = 365 * 24 // 8


# ------------------------------ Data load ------------------------------


def load_hl_fr(sym: str) -> Optional[pd.Series]:
    f = HL_CACHE / f"hl_fr_{sym}.parquet"
    if not f.exists():
        return None
    df = pd.read_parquet(f)
    s = df.set_index("timestamp")["hl_fr"].astype(float).sort_index()
    s = s[~s.index.duplicated(keep="last")]
    s.name = sym
    return s


def load_bybit_fr(sym: str) -> Optional[pd.Series]:
    # Prefer 730d, fallback to longer ones.
    for tag in ("730d", "1200d", "365d"):
        f = CACHE / f"bybit_fr_{sym}USDT_{tag}.parquet"
        if f.exists():
            df = pd.read_parquet(f)
            s = df.set_index("timestamp")["funding_rate"].astype(float).sort_index()
            s = s[~s.index.duplicated(keep="last")]
            s.name = sym
            return s
    return None


def load_bybit_close(sym: str) -> Optional[pd.Series]:
    """4h close panel used to compute perp price PnL between funding events."""
    f = CACHE / f"{sym}USDT_4h_730d.parquet"
    if not f.exists():
        return None
    df = pd.read_parquet(f)
    s = df.set_index("open_time")["close"].astype(float).sort_index()
    s = s[~s.index.duplicated(keep="last")]
    s.name = sym
    return s


def build_per_symbol_event_panel(
    sym: str,
) -> Optional[pd.DataFrame]:
    """Per-symbol DataFrame indexed by Bybit funding event timestamps.

    Columns:
      bybit_fr   : 8h funding rate at event T (as reported by Bybit)
      hl_fr_8h   : sum of 8 hourly HL FRs over (T-8h, T]
      spread     : bybit_fr - hl_fr_8h
      close      : Bybit 4h close at event T (chosen 4h bar containing T)
      fwd_ret_1  : log return of close from T to T + 8h (= 1 event ahead)
    """
    hl = load_hl_fr(sym)
    by = load_bybit_fr(sym)
    cl = load_bybit_close(sym)
    if hl is None or by is None or cl is None:
        return None
    if len(hl) < 100 or len(by) < 100 or len(cl) < 100:
        return None
    # Aggregate HL hourly to 8h sums anchored at Bybit funding timestamps.
    # For each event T, sum hourly bars with index in (T-8h, T].
    # Use resample on a shifted HL series so that the resample bin label
    # corresponds to the right-edge T.
    hl_8h = hl.resample("8h", label="right", closed="right").sum(min_count=1)
    # Align Bybit FR with 8h sums via reindex (Bybit ts are exactly on 8h grid).
    idx = by.index
    df = pd.DataFrame({"bybit_fr": by}, index=idx)
    df["hl_fr_8h"] = hl_8h.reindex(idx)
    df = df.dropna()
    if len(df) < 100:
        return None
    df["spread"] = df["bybit_fr"] - df["hl_fr_8h"]
    # Map Bybit close to the event grid: take the 4h bar whose open_time
    # equals T (the bar starting at the funding ts).
    cl_at_event = cl.reindex(idx, method="nearest", tolerance=pd.Timedelta("2h"))
    df["close"] = cl_at_event
    df = df.dropna(subset=["close"])
    if len(df) < 100:
        return None
    df["fwd_ret_1"] = np.log(df["close"]).diff().shift(-1)  # T -> T+1 event ret
    return df


# ------------------------------ Strategy ------------------------------


def zscore(s: pd.Series, win: int = 30) -> pd.Series:
    mu = s.rolling(win, min_periods=win).mean()
    sd = s.rolling(win, min_periods=win).std()
    return (s - mu) / (sd + 1e-12)


def variant_z(
    panels: Dict[str, pd.DataFrame], z_thr: float, hold: int, zwin: int = 30
) -> Tuple[pd.Series, pd.Series, int, Dict[str, float], Dict[str, float]]:
    """Per-symbol independent z-score signal, equal-weight aggregation.

    Position rule (lag-1, shift signal by 1 event):
      z_{T-1} > +z_thr -> SHORT Bybit at T, hold `hold` events.
      z_{T-1} < -z_thr -> LONG  Bybit at T, hold `hold` events.

    PnL per event = position * fwd_ret_1 (8h forward log return) summed over
    held positions. Costs charged at entry and exit (each 2*COST_BPS for
    1 leg with notional 1).
    """
    per_sym_gross: Dict[str, pd.Series] = {}
    per_sym_net: Dict[str, pd.Series] = {}
    total_trades = 0
    per_sym_sh_gross: Dict[str, float] = {}
    per_sym_sh_net: Dict[str, float] = {}
    for sym, df in panels.items():
        z = zscore(df["spread"], zwin)
        sig = pd.Series(0.0, index=df.index)
        sig[z > z_thr] = -1.0
        sig[z < -z_thr] = 1.0
        sig_lag = sig.shift(1).fillna(0.0)
        # Build position by carrying forward `hold` events.
        pos = pd.Series(0.0, index=df.index)
        i = 0
        trades = 0
        last_pos = 0.0
        while i < len(sig_lag):
            new = sig_lag.iloc[i]
            if new != 0.0 and last_pos == 0.0:
                end = min(i + hold, len(pos))
                pos.iloc[i:end] = new
                last_pos = new
                trades += 1
                # Exit on bar `end` (no fill after end).
                # Continue scanning from `end` to allow re-entry next event.
                i = end
                last_pos = 0.0
                continue
            i += 1
        fwd = df["fwd_ret_1"].fillna(0.0)
        pnl_gross_sym = pos * fwd
        # Cost ledger: charge 2*COST_BPS at entry and 2*COST_BPS at exit.
        # An entry is detected where pos changes from 0 to non-zero (or sign
        # flips). Cost = 2*COST_BPS per change-event.
        pos_change = pos.diff().fillna(pos.iloc[0])
        n_entries = int((pos_change != 0).sum())
        # Approx: each entry has a paired exit; charge 4*COST_BPS per trade
        # (entry+exit, 1 leg each side... actually 1 leg total since single
        # perp; "per side per leg" -> entry cost + exit cost = 2*COST_BPS).
        # K173 used 2 legs (long+short), so 4*COST_BPS per trade. Here single
        # leg -> 2*COST_BPS per trade. We use that.
        cost_series = pd.Series(0.0, index=df.index)
        cost_series[pos_change != 0] = COST_BPS
        # Add exit cost (when pos transitions back to 0). pos_change captures
        # both entry and exit changes already.
        pnl_net_sym = pnl_gross_sym - cost_series
        per_sym_gross[sym] = pnl_gross_sym
        per_sym_net[sym] = pnl_net_sym
        total_trades += trades
        per_sym_sh_gross[sym] = sharpe(pnl_gross_sym, ppy=EVENTS_PER_YEAR)
        per_sym_sh_net[sym] = sharpe(pnl_net_sym, ppy=EVENTS_PER_YEAR)
    if not per_sym_net:
        empty = pd.Series(dtype=float)
        return empty, empty, 0, {}, {}
    gross = pd.concat(per_sym_gross, axis=1).fillna(0.0).mean(axis=1)
    net = pd.concat(per_sym_net, axis=1).fillna(0.0).mean(axis=1)
    return net, gross, total_trades, per_sym_sh_net, per_sym_sh_gross


def variant_abs(
    panels: Dict[str, pd.DataFrame], abs_thr: float, hold: int
) -> Tuple[pd.Series, pd.Series, int, Dict[str, float], Dict[str, float]]:
    """Absolute-threshold variant on raw spread."""
    per_sym_gross, per_sym_net = {}, {}
    total_trades = 0
    per_sym_sh_gross, per_sym_sh_net = {}, {}
    for sym, df in panels.items():
        sp = df["spread"]
        sig = pd.Series(0.0, index=df.index)
        sig[sp > abs_thr] = -1.0
        sig[sp < -abs_thr] = 1.0
        sig_lag = sig.shift(1).fillna(0.0)
        pos = pd.Series(0.0, index=df.index)
        i = 0
        trades = 0
        while i < len(sig_lag):
            new = sig_lag.iloc[i]
            if new != 0.0:
                end = min(i + hold, len(pos))
                pos.iloc[i:end] = new
                trades += 1
                i = end
                continue
            i += 1
        fwd = df["fwd_ret_1"].fillna(0.0)
        pnl_g = pos * fwd
        pos_change = pos.diff().fillna(pos.iloc[0])
        cost_series = pd.Series(0.0, index=df.index)
        cost_series[pos_change != 0] = COST_BPS
        pnl_n = pnl_g - cost_series
        per_sym_gross[sym] = pnl_g
        per_sym_net[sym] = pnl_n
        total_trades += trades
        per_sym_sh_gross[sym] = sharpe(pnl_g, ppy=EVENTS_PER_YEAR)
        per_sym_sh_net[sym] = sharpe(pnl_n, ppy=EVENTS_PER_YEAR)
    if not per_sym_net:
        empty = pd.Series(dtype=float)
        return empty, empty, 0, {}, {}
    gross = pd.concat(per_sym_gross, axis=1).fillna(0.0).mean(axis=1)
    net = pd.concat(per_sym_net, axis=1).fillna(0.0).mean(axis=1)
    return net, gross, total_trades, per_sym_sh_net, per_sym_sh_gross


def variant_topxs(
    panels: Dict[str, pd.DataFrame], hold: int
) -> Tuple[pd.Series, pd.Series, int, Dict[str, float], Dict[str, float]]:
    """Cross-section: each event T, pick the symbol with the largest +ve
    spread (SHORT) and the most -ve spread (LONG). Equal-weight pair."""
    # Build wide spread / fwd_ret panels on the union of all event timestamps.
    all_idx = sorted(set().union(*[df.index for df in panels.values()]))
    full = pd.DatetimeIndex(all_idx)
    sp_panel = pd.DataFrame(index=full, columns=list(panels.keys()), dtype=float)
    fwd_panel = pd.DataFrame(index=full, columns=list(panels.keys()), dtype=float)
    for sym, df in panels.items():
        sp_panel.loc[df.index, sym] = df["spread"].values
        fwd_panel.loc[df.index, sym] = df["fwd_ret_1"].values
    # Lag the spread by one event (decision at T uses T-1 info).
    sp_lag = sp_panel.shift(1)
    pnl_gross = pd.Series(0.0, index=full)
    cost = pd.Series(0.0, index=full)
    trades = 0
    holding_short: Optional[str] = None
    holding_long: Optional[str] = None
    end_idx = -1
    per_sym_sh_gross: Dict[str, float] = {s: 0.0 for s in panels}
    per_sym_sh_net: Dict[str, float] = {s: 0.0 for s in panels}
    for i in range(len(full)):
        row = sp_lag.iloc[i].dropna()
        if i > end_idx:
            holding_short = None
            holding_long = None
            if len(row) >= 2:
                short_sym = row.idxmax()
                long_sym = row.idxmin()
                if short_sym != long_sym:
                    holding_short = short_sym
                    holding_long = long_sym
                    end_idx = i + hold - 1
                    trades += 1
                    cost.iloc[i] += 2.0 * COST_BPS  # 2 legs entry
                    if i + hold < len(full):
                        cost.iloc[min(i + hold, len(full) - 1)] += 2.0 * COST_BPS
        if holding_short is not None and holding_long is not None:
            sr = fwd_panel[holding_short].iloc[i]
            lr = fwd_panel[holding_long].iloc[i]
            if not (np.isnan(sr) or np.isnan(lr)):
                pnl_gross.iloc[i] += 0.5 * (lr - sr)  # equal weight pair
    pnl_net = pnl_gross - cost
    return pnl_net, pnl_gross, trades, per_sym_sh_net, per_sym_sh_gross


# ------------------------------ Metrics ------------------------------


def sharpe(pnl: pd.Series, ppy: int = EVENTS_PER_YEAR) -> float:
    pnl = pnl.dropna()
    if len(pnl) < 30 or pnl.std() == 0:
        return 0.0
    return float(pnl.mean() / pnl.std() * np.sqrt(ppy))


def cagr(pnl: pd.Series, ppy: int = EVENTS_PER_YEAR) -> float:
    if len(pnl) == 0:
        return 0.0
    total = pnl.sum()
    years = len(pnl) / ppy
    if years <= 0:
        return 0.0
    return float(np.expm1(total / years))


def max_dd(pnl: pd.Series) -> float:
    eq = pnl.cumsum()
    peak = eq.cummax()
    dd = eq - peak
    return float(dd.min())


def equity_curve(pnl: pd.Series) -> List[float]:
    return list(np.exp(pnl.fillna(0).cumsum()).round(6))


def perm_test(pnl: pd.Series, n: int = 300, seed: int = 7) -> float:
    rng = np.random.default_rng(seed)
    obs = sharpe(pnl)
    vals = pnl.dropna().values
    if len(vals) < 10 or pnl.std() == 0:
        return 1.0
    perm_sharpes = []
    for _ in range(n):
        shuf = rng.permutation(vals)
        s = pd.Series(shuf)
        sh = s.mean() / (s.std() + 1e-12) * np.sqrt(EVENTS_PER_YEAR)
        perm_sharpes.append(sh)
    perm_sharpes = np.array(perm_sharpes)
    if obs > 0:
        return float((perm_sharpes >= obs).mean())
    return float((perm_sharpes <= obs).mean())


def bootstrap_ci(pnl: pd.Series, n: int = 300, seed: int = 11) -> Tuple[float, float]:
    rng = np.random.default_rng(seed)
    vals = pnl.dropna().values
    if len(vals) < 30:
        return (0.0, 0.0)
    sharpes = []
    for _ in range(n):
        idx = rng.integers(0, len(vals), size=len(vals))
        s = pd.Series(vals[idx])
        sh = s.mean() / (s.std() + 1e-12) * np.sqrt(EVENTS_PER_YEAR)
        sharpes.append(sh)
    return float(np.percentile(sharpes, 5)), float(np.percentile(sharpes, 95))


def dsr(pnl: pd.Series, n_trials: int = 4) -> float:
    pnl = pnl.dropna()
    if len(pnl) < 30 or pnl.std() == 0:
        return 0.0
    sr = pnl.mean() / pnl.std()
    T = len(pnl)
    sk = float(((pnl - pnl.mean()) ** 3).mean() / (pnl.std() ** 3 + 1e-12))
    kt = float(((pnl - pnl.mean()) ** 4).mean() / (pnl.std() ** 4 + 1e-12))
    emc = 0.5772
    e_max = np.sqrt(2 * np.log(max(n_trials, 2))) - emc / np.sqrt(
        2 * np.log(max(n_trials, 2))
    )
    denom = np.sqrt((1 - sk * sr + (kt - 1) / 4 * sr**2) / (T - 1))
    if denom <= 0:
        return 0.0
    z = (sr - e_max) / denom
    return float(0.5 * (1 + erf(z / sqrt(2))))


def wf_4fold(pnl: pd.Series) -> Tuple[float, List[float]]:
    pnl = pnl.dropna()
    if len(pnl) < 100:
        return 0.0, []
    folds = np.array_split(pnl.values, 4)
    sharpes = []
    for f in folds:
        s = pd.Series(f)
        if s.std() == 0:
            sharpes.append(0.0)
            continue
        sharpes.append(float(s.mean() / s.std() * np.sqrt(EVENTS_PER_YEAR)))
    return float(np.mean(sharpes)), [float(x) for x in sharpes]


def turnover(pnl: pd.Series, n_trades: int) -> float:
    if len(pnl) == 0:
        return 0.0
    years = len(pnl) / EVENTS_PER_YEAR
    return float(n_trades / max(years, 1e-6))


def cost_stress(pnl_gross: pd.Series, pnl_net: pd.Series) -> Dict:
    """Net-Sharpe at 1x/1.5x/2x of the realized cost drag.

    Realized cost = pnl_gross.sum() - pnl_net.sum(); distribute uniformly
    across bars. Baseline (1x) reproduces sharpe_net by construction.
    """
    out = {}
    if len(pnl_gross) == 0:
        return {"1x_baseline": 0.0, "1p5x": 0.0, "2x_double": 0.0}
    total_cost = float(pnl_gross.sum() - pnl_net.sum())
    per_bar_cost = total_cost / len(pnl_gross)
    for mult, label in [(1.0, "1x_baseline"), (1.5, "1p5x"), (2.0, "2x_double")]:
        adj = pnl_gross - mult * per_bar_cost
        out[label] = round(sharpe(adj), 4)
    return out


def report_variant(
    name: str,
    pnl: pd.Series,
    pnl_gross: pd.Series,
    n_trades: int,
    per_sym_sh: Dict[str, float],
    per_sym_sh_gross: Dict[str, float],
) -> Dict:
    sh = sharpe(pnl)
    sh_g = sharpe(pnl_gross)
    cg = cagr(pnl)
    dd = max_dd(pnl)
    split = int(len(pnl) * 0.7)
    is_pnl = pnl.iloc[:split]
    oos_pnl = pnl.iloc[split:]
    is_sh = sharpe(is_pnl)
    oos_sh = sharpe(oos_pnl)
    wf_mean, wf_folds = wf_4fold(pnl)
    perm_p = perm_test(pnl, n=300)
    perm_p_g = perm_test(pnl_gross, n=300)
    ci_lo, ci_hi = bootstrap_ci(pnl, n=300)
    dsr_p = dsr(pnl, n_trials=4)
    to = turnover(pnl, n_trades)
    cs = cost_stress(pnl_gross, pnl)
    return {
        "variant": name,
        "sharpe_net": round(sh, 4),
        "sharpe_gross": round(sh_g, 4),
        "cagr_net": round(cg, 4),
        "max_dd_net": round(dd, 4),
        "is_sharpe_net": round(is_sh, 4),
        "oos_sharpe_net": round(oos_sh, 4),
        "wf_mean_sharpe_net": round(wf_mean, 4),
        "wf_folds_net": [round(x, 4) for x in wf_folds],
        "perm_pvalue_net": round(perm_p, 4),
        "perm_pvalue_gross": round(perm_p_g, 4),
        "bootstrap_ci_5_95_net": [round(ci_lo, 4), round(ci_hi, 4)],
        "dsr_net": round(dsr_p, 4),
        "n_trades": int(n_trades),
        "trades_per_year": round(to, 2),
        "n_events": int(len(pnl)),
        "per_symbol_sharpe_net": {k: round(v, 4) for k, v in per_sym_sh.items()},
        "per_symbol_sharpe_gross": {
            k: round(v, 4) for k, v in per_sym_sh_gross.items()
        },
        "cost_stress_net_sharpe": cs,
    }


# ----------------------- Correlation w/ existing -----------------------


def correlation_vs_k133(pnl_event: pd.Series) -> Dict[str, float]:
    """Aggregate the K174 per-event PnL into weekly bins anchored on each
    K133 weekly timestamp (sum K174 pnl since prior K133 ts), then correlate
    the period-to-period returns."""
    p = ROOT / "wave_k133_curves.json"
    if not p.exists() or pnl_event.empty:
        return {}
    d = json.loads(p.read_text())
    pnl_event = pnl_event.dropna().sort_index()
    out: Dict[str, object] = {}
    n_common_max = 0
    for name, payload in d.items():
        k133_idx = pd.to_datetime(payload["equity_idx"]).sort_values()
        eq = pd.Series(
            payload["equity_curve"], index=k133_idx
        ).sort_index()
        k133_ret = eq.pct_change().dropna()
        # For each K133 ts, bucket K174 pnl in (prev_ts, this_ts].
        k174_bins = []
        bin_ts = []
        for i in range(1, len(k133_idx)):
            lo = k133_idx[i - 1]
            hi = k133_idx[i]
            mask = (pnl_event.index > lo) & (pnl_event.index <= hi)
            k174_bins.append(pnl_event[mask].sum())
            bin_ts.append(hi)
        k174_aligned = pd.Series(k174_bins, index=pd.DatetimeIndex(bin_ts))
        common = k174_aligned.index.intersection(k133_ret.index)
        if len(common) < 10:
            out[name] = None
            continue
        c = k174_aligned.reindex(common).corr(k133_ret.reindex(common))
        out[name] = round(float(c), 4) if pd.notna(c) else 0.0
        n_common_max = max(n_common_max, len(common))
    out["_n_common_weeks_max"] = float(n_common_max)
    return out


# ------------------------------ Main ------------------------------


def main() -> Dict:
    t0 = time.time()
    panels: Dict[str, pd.DataFrame] = {}
    skipped: List[str] = []
    for sym in SYMBOLS:
        p = build_per_symbol_event_panel(sym)
        if p is None:
            skipped.append(sym)
            continue
        panels[sym] = p
    if not panels:
        raise RuntimeError("No panels built; check cache paths.")
    print(f"Built panels: {list(panels.keys())}, skipped: {skipped}")
    for s, df in panels.items():
        print(
            f"  {s:5s} events={len(df):4d}  spread mean={df['spread'].mean():+.6f}  "
            f"std={df['spread'].std():.6f}"
        )

    variants_cfg = [
        ("V_z2_h1", "z", {"z_thr": 2.0, "hold": 1}),
        ("V_z2_h3", "z", {"z_thr": 2.0, "hold": 3}),
        ("V_abs1bp", "abs", {"abs_thr": 1e-4, "hold": 1}),
        ("V_top_xs", "topxs", {"hold": 1}),
    ]

    results: List[Dict] = []
    curves: Dict[str, Dict] = {}
    primary_pnl: Optional[pd.Series] = None
    for name, kind, kw in variants_cfg:
        if kind == "z":
            pnl, pnl_g, n_tr, per_sh, per_sh_g = variant_z(panels, **kw)
        elif kind == "abs":
            pnl, pnl_g, n_tr, per_sh, per_sh_g = variant_abs(panels, **kw)
        else:
            pnl, pnl_g, n_tr, per_sh, per_sh_g = variant_topxs(panels, **kw)
        rep = report_variant(name, pnl, pnl_g, n_tr, per_sh, per_sh_g)
        results.append(rep)
        curves[name] = {
            "equity_net": equity_curve(pnl),
            "equity_gross": equity_curve(pnl_g),
            "timestamps": [t.isoformat() for t in pnl.index],
        }
        if name == "V_z2_h1":
            primary_pnl = pnl
        print(
            f"{name:12s} Sh_net={rep['sharpe_net']:+.2f}  Sh_gross={rep['sharpe_gross']:+.2f}  "
            f"OOS={rep['oos_sharpe_net']:+.2f}  perm_p={rep['perm_pvalue_net']:.3f}  "
            f"trades={rep['n_trades']}  to/yr={rep['trades_per_year']:.0f}"
        )

    # Integration coefficient: regress hl_fr_8h_T = a + b * bybit_fr_{T-1}.
    # If b ~ 0.61 across symbols, hypothesis-aligned.
    integ = {}
    for sym, df in panels.items():
        x = df["bybit_fr"].shift(1).dropna()
        y = df["hl_fr_8h"].reindex(x.index)
        m = x.notna() & y.notna()
        if m.sum() < 30:
            integ[sym] = None
            continue
        xs = x[m].values
        ys = y[m].values
        b1, b0 = np.polyfit(xs, ys, 1)
        integ[sym] = {"b": round(float(b1), 4), "intercept": round(float(b0), 8),
                      "n": int(m.sum())}
    integ_betas = [v["b"] for v in integ.values() if isinstance(v, dict)]
    integ_mean_b = float(np.mean(integ_betas)) if integ_betas else 0.0

    corr_k133 = correlation_vs_k133(primary_pnl) if primary_pnl is not None else {}

    primary = results[0]
    gates = {
        "g1_sharpe_net_ge_1": primary["sharpe_net"] >= 1.0,
        "g2_oos_sharpe_net_ge_0p5": primary["oos_sharpe_net"] >= 0.5,
        "g3_oos_is_ratio_ge_0p5": (
            primary["oos_sharpe_net"] / primary["is_sharpe_net"] >= 0.5
            if primary["is_sharpe_net"] > 0
            else False
        ),
        "g4_wf_folds_all_positive": (
            all(x > 0 for x in primary["wf_folds_net"])
            if primary["wf_folds_net"]
            else False
        ),
        "g5_perm_p_le_0p05": primary["perm_pvalue_net"] <= 0.05,
        "g6_dsr_ge_0p95": primary["dsr_net"] >= 0.95,
        "g7_trades_per_year_ge_20": primary["trades_per_year"] >= 20,
    }
    gates_passed = int(sum(gates.values()))
    verdict = (
        "PASS"
        if gates_passed >= 6
        else ("MARGINAL" if gates_passed >= 4 else "FAIL")
    )

    summary = {
        "wave": "K174",
        "hypothesis": (
            "DEX (Hyperliquid) FR lags CEX (Bybit) FR with ~61% integration; "
            "spread mean-reversion -> trade Bybit perp."
        ),
        "data": {
            "symbols_used": list(panels.keys()),
            "symbols_skipped": skipped,
            "events_per_year_assumed": EVENTS_PER_YEAR,
            "per_symbol_event_counts": {
                s: int(len(df)) for s, df in panels.items()
            },
        },
        "integration_check": {
            "per_symbol_beta": integ,
            "mean_beta": round(integ_mean_b, 4),
            "expected_per_mdpi": 0.61,
            "ok_within_0p15": abs(integ_mean_b - 0.61) <= 0.15,
        },
        "variants": results,
        "correlations_vs_k133": corr_k133,
        "gates_primary": gates,
        "gates_passed": gates_passed,
        "gates_total": 7,
        "verdict": verdict,
        "runtime_sec": round(time.time() - t0, 1),
    }

    out_json = ROOT / "wave_k174_cex_dex_fr.json"
    out_curves = ROOT / "wave_k174_curves.json"
    out_json.write_text(json.dumps(summary, indent=2, default=str))
    out_curves.write_text(json.dumps(curves, default=str))
    print(f"\nWrote {out_json}  ({out_json.stat().st_size} bytes)")
    print(f"Wrote {out_curves} ({out_curves.stat().st_size} bytes)")
    print(
        f"Integration mean beta (HL_8h ~ Bybit_t-1) = {integ_mean_b:+.3f}  "
        f"(MDPI expected ~0.61)"
    )
    print(f"Verdict: {verdict}  ({gates_passed}/7 gates)")
    print(f"Runtime: {summary['runtime_sec']}s")
    return summary


if __name__ == "__main__":
    main()
