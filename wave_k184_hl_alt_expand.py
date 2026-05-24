"""Wave K184 - HL Mid-Cap Alt Universe Expansion.

Objective:
  K183 screened all 8 existing HL-cached symbols (BTC/ETH/SOL/BNB/AVAX/DOGE/XRP/SUI).
  Only XRP and SUI passed the K175-family lag-filter (lag=1 signed-edge > +30 bps).
  K184 expands the HL universe to 5 popular mid-cap alts on Hyperliquid:
    ARB, INJ, TAO, NEAR, JTO

  These are expected to show distinct funding spread behavior from the majors.
  Bybit FR already cached for all 5. Price data also already cached.
  Need to fetch HL FR data (hourly) via Hyperliquid public API.

Data pipeline:
  1. Fetch HL hourly FR for each symbol (paginated, 500 events/call, sleep 1s)
  2. Save to cache/k163_hl/hl_fr_{SYM}.parquet (same format as existing K163 cache)
  3. Build 8h event panels: HL sum -> Bybit cadence alignment
  4. Lag-1 filter analysis (K183 criterion: z>2 tail lag1_short_bps > 30 bps)
  5. K175 backtest for any passing candidates
  6. §6 strict gates if gross Sh >= 1.0
  7. Multi-symbol combined variant if 2+ candidates pass

§6 strict gates:
  G1 OOS Sh >= 1.0, G2 Perm p <= 0.05, G3 DSR >= 0.95
  G4 WF folds all positive, G5 IS/OOS ratio >= 0.5
  G6 Gross Sh >= 0.3, G7 Trades/yr >= 20

Cost model: Maker-only, 2 bp/side slippage, 0 maker fee (4 bps round-trip).
Report GROSS AND NET separately.
"""
from __future__ import annotations

import json
import time
from math import erf, sqrt
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import urllib.request
import urllib.error

ROOT = Path("/Users/nekonaomichi/crypto-lab")
CACHE = ROOT / "cache"
HL_CACHE = CACHE / "k163_hl"

# Maker-only execution cost model
SLIPPAGE_BPS_PER_SIDE = 2.0
MAKER_FEE_BPS_PER_SIDE = 0.0
COST_PER_FILL = (SLIPPAGE_BPS_PER_SIDE + MAKER_FEE_BPS_PER_SIDE) * 1e-4  # 0.0002

# 8h Bybit funding cadence
EVENTS_PER_YEAR = 365 * 24 // 8  # 1095

# Target new symbols
NEW_SYMBOLS = ["ARB", "INJ", "TAO", "NEAR", "JTO"]

# K183/K180 filter criterion
LAG1_EDGE_ABS_THRESHOLD_BPS = 30.0

# Hyperliquid API
HL_API_URL = "https://api.hyperliquid.xyz/info"


# ================================================================ HL Data Fetch

def hl_fetch_funding_page(coin: str, start_ms: int, end_ms: int, retries: int = 5) -> List[Dict]:
    """Fetch one page of HL funding history (max 500 events). Retries on 429."""
    import urllib.request, json as _json, urllib.error
    payload = _json.dumps({
        "type": "fundingHistory",
        "coin": coin,
        "startTime": start_ms,
        "endTime": end_ms,
    }).encode()
    req = urllib.request.Request(
        HL_API_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = _json.loads(resp.read().decode())
                return data if isinstance(data, list) else []
        except urllib.error.HTTPError as e:
            if e.code == 429:
                wait = 10 * (attempt + 1)
                print(f"    429 rate-limit for {coin}, waiting {wait}s (attempt {attempt+1}/{retries})...")
                time.sleep(wait)
                continue
            print(f"    HTTP {e.code} for {coin}: {e.reason}")
            return []
        except Exception as e:
            print(f"    Error fetching {coin}: {e}")
            return []
    print(f"    Exhausted retries for {coin}")
    return []


def fetch_hl_fr_full(sym: str, days: int = 730) -> Optional[pd.DataFrame]:
    """
    Fetch full HL funding history for a symbol via paginated API calls.
    Returns DataFrame with columns: timestamp (datetime64[ns]), hl_fr (float64)
    """
    now_ms = int(time.time() * 1000)
    start_ms = now_ms - days * 86400 * 1000
    end_ms = now_ms

    all_events = []
    page_start = start_ms
    page_num = 0

    print(f"  Fetching HL FR for {sym} ({days}d, paginated)...")
    while page_start < end_ms:
        events = hl_fetch_funding_page(sym, page_start, end_ms)
        if not events:
            # Symbol may not exist or no more data
            break
        all_events.extend(events)
        page_num += 1
        # Advance to next page: use last event time + 1ms
        last_time = max(e.get("time", 0) for e in events)
        if last_time <= page_start or len(events) < 500:
            break  # no more pages
        page_start = last_time + 1
        time.sleep(1.0)  # respect rate limits
        print(f"    Page {page_num}: {len(events)} events, last_time={pd.Timestamp(last_time, unit='ms')}")

    if not all_events:
        return None

    # Parse events: each event has 'time' (ms), 'coin', 'fundingRate'
    records = []
    for e in all_events:
        ts = pd.Timestamp(e.get("time", 0), unit="ms")
        fr = float(e.get("fundingRate", 0))
        records.append({"timestamp": ts, "hl_fr": fr})

    df = pd.DataFrame(records)
    df = df.drop_duplicates("timestamp").sort_values("timestamp").reset_index(drop=True)
    print(f"    Total: {len(df)} events  [{df['timestamp'].min()} - {df['timestamp'].max()}]")
    return df


def load_or_fetch_hl_fr(sym: str, force_fetch: bool = False) -> Optional[pd.DataFrame]:
    """Load HL FR from cache or fetch via API."""
    cache_path = HL_CACHE / f"hl_fr_{sym}.parquet"
    if cache_path.exists() and not force_fetch:
        df = pd.read_parquet(cache_path)
        print(f"  {sym}: Loaded HL FR from cache ({len(df)} rows)")
        return df
    # Fetch from API
    df = fetch_hl_fr_full(sym, days=730)
    if df is not None and len(df) > 0:
        HL_CACHE.mkdir(parents=True, exist_ok=True)
        df.to_parquet(cache_path, index=False)
        print(f"  {sym}: Saved HL FR to {cache_path} ({len(df)} rows)")
    return df


# ================================================================ Data Load

def load_hl_fr_series(sym: str) -> Optional[pd.Series]:
    f = HL_CACHE / f"hl_fr_{sym}.parquet"
    if not f.exists():
        return None
    df = pd.read_parquet(f)
    s = df.set_index("timestamp")["hl_fr"].astype(float).sort_index()
    s = s[~s.index.duplicated(keep="last")]
    s.name = sym
    return s


def load_bybit_fr(sym: str) -> Optional[pd.Series]:
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
    for tag in ("4h_730d", "4h_365d", "1h_730d", "1h_365d", "1d_730d"):
        f = CACHE / f"{sym}USDT_{tag}.parquet"
        if f.exists():
            df = pd.read_parquet(f)
            time_col = "open_time" if "open_time" in df.columns else df.columns[0]
            s = df.set_index(time_col)["close"].astype(float).sort_index()
            s = s[~s.index.duplicated(keep="last")]
            s.name = sym
            return s
    return None


def build_panel(sym: str) -> Optional[pd.DataFrame]:
    """Build 8h-frequency event panel with spread and forward returns."""
    hl = load_hl_fr_series(sym)
    by = load_bybit_fr(sym)
    cl = load_bybit_close(sym)

    if hl is None or by is None or cl is None:
        missing = []
        if hl is None: missing.append("HL_FR")
        if by is None: missing.append("Bybit_FR")
        if cl is None: missing.append("Price")
        print(f"  {sym}: Missing data: {missing}")
        return None
    if len(hl) < 50 or len(by) < 50 or len(cl) < 50:
        print(f"  {sym}: Insufficient data (hl={len(hl)}, by={len(by)}, cl={len(cl)})")
        return None

    # HL is hourly; sum into 8h buckets to match Bybit settlement cadence
    hl_8h = hl.resample("8h", label="right", closed="right").sum(min_count=1)

    idx = by.index
    df = pd.DataFrame({"bybit_fr": by}, index=idx)
    df["hl_fr_8h"] = hl_8h.reindex(idx)
    df = df.dropna()
    if len(df) < 50:
        print(f"  {sym}: After alignment only {len(df)} events")
        return None

    # Spread = Bybit - HL
    df["spread"] = df["bybit_fr"] - df["hl_fr_8h"]

    # Price at event
    cl_at_event = cl.reindex(idx, method="nearest", tolerance=pd.Timedelta("4h"))
    df["close"] = cl_at_event
    df = df.dropna(subset=["close"])
    if len(df) < 50:
        print(f"  {sym}: After price join only {len(df)} events")
        return None

    df["log_ret"] = np.log(df["close"]).diff()
    df["fwd_ret_1"] = df["log_ret"].shift(-1)  # K175 trade period
    df["fwd_ret_2"] = df["log_ret"].shift(-2)   # persistence check
    return df


# ================================================================ Z-score

def zscore_series(s: pd.Series, win: int = 30) -> pd.Series:
    mu = s.rolling(win, min_periods=win).mean()
    sd = s.rolling(win, min_periods=win).std()
    return (s - mu) / (sd + 1e-12)


# ================================================================ Lag Analysis

def compute_lag_analysis(df: pd.DataFrame, z_thr: float = 2.0, win: int = 30) -> Dict:
    """Compute per-tail signed-edge at K180/K183 lag conventions."""
    z = zscore_series(df["spread"], win)
    df2 = df.copy()
    df2["z"] = z
    df2 = df2.dropna(subset=["z"])

    result = {}
    for tail_name, mask, sign in [
        ("z_above_2", df2["z"] > z_thr, -1.0),    # short: profit = -fwd_ret
        ("z_below_neg2", df2["z"] < -z_thr, 1.0),  # long:  profit = +fwd_ret
    ]:
        tail_df = df2[mask]
        n = len(tail_df)
        if n < 5:
            result[tail_name] = {"n": n, "note": "insufficient events"}
            continue

        lag_info = {}
        for lag_key, col in [
            ("lag0_concurrent", "log_ret"),
            ("lag0_k180", "fwd_ret_1"),
            ("lag1_k180", "fwd_ret_2"),
        ]:
            vals = tail_df[col].dropna()
            n_valid = len(vals)
            if n_valid < 3:
                lag_info[lag_key] = {"n": n_valid, "note": "insufficient"}
                continue
            mean_fwd_bps = float(vals.mean() * 1e4)
            signed_edge_bps = float(sign * vals.mean() * 1e4)
            std_bps = float(vals.std() * 1e4)
            tstat = float(vals.mean() / (vals.std() / np.sqrt(n_valid) + 1e-12))
            lag_info[lag_key] = {
                "n": n_valid,
                "mean_fwd_ret_bps": round(mean_fwd_bps, 2),
                "signed_edge_bps": round(signed_edge_bps, 2),
                "std_bps": round(std_bps, 2),
                "tstat": round(tstat, 3),
            }
        result[tail_name] = {"n": n, "lags": lag_info}

    z_above = result.get("z_above_2", {})
    k180_lag0_short = None
    k180_lag1_short = None
    if "lags" in z_above:
        if "lag0_k180" in z_above["lags"]:
            k180_lag0_short = z_above["lags"]["lag0_k180"]["signed_edge_bps"]
        if "lag1_k180" in z_above["lags"]:
            k180_lag1_short = z_above["lags"]["lag1_k180"]["signed_edge_bps"]

    z_below = result.get("z_below_neg2", {})
    k180_lag0_long = None
    k180_lag1_long = None
    if "lags" in z_below:
        if "lag0_k180" in z_below["lags"]:
            k180_lag0_long = z_below["lags"]["lag0_k180"]["signed_edge_bps"]
        if "lag1_k180" in z_below["lags"]:
            k180_lag1_long = z_below["lags"]["lag1_k180"]["signed_edge_bps"]

    passes_filter = (
        k180_lag1_short is not None and k180_lag1_short > LAG1_EDGE_ABS_THRESHOLD_BPS
    )

    return {
        "tails": result,
        "k180_lag0_short_bps": k180_lag0_short,
        "k180_lag1_short_bps": k180_lag1_short,
        "k180_lag0_long_bps": k180_lag0_long,
        "k180_lag1_long_bps": k180_lag1_long,
        "passes_k175_filter": passes_filter,
        "filter_criterion": (
            f"z>2 tail: K180 lag=1 (fwd_ret_2) signed_edge > {LAG1_EDGE_ABS_THRESHOLD_BPS} bps"
        ),
    }


# ================================================================ Metrics

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


def perm_test(pnl: pd.Series, n: int = 200, seed: int = 7) -> float:
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


def bootstrap_ci(pnl: pd.Series, n: int = 200, seed: int = 11) -> Tuple[float, float]:
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


def wf_3fold(pnl: pd.Series) -> Tuple[float, List[float]]:
    pnl = pnl.dropna()
    if len(pnl) < 100:
        return 0.0, []
    folds = np.array_split(pnl.values, 3)
    sharpes = []
    for f in folds:
        s = pd.Series(f)
        if s.std() == 0:
            sharpes.append(0.0)
            continue
        sharpes.append(float(s.mean() / s.std() * np.sqrt(EVENTS_PER_YEAR)))
    return float(np.mean(sharpes)), [float(x) for x in sharpes]


# ================================================================ Strategy

def variant_z(
    panels: Dict[str, pd.DataFrame],
    z_thr: float = 2.0,
    hold: int = 1,
    zwin: int = 30,
    cost_per_fill: float = COST_PER_FILL,
) -> Tuple[pd.Series, pd.Series, int, Dict[str, float], Dict[str, float]]:
    """K175-identical execution logic (sig.shift(1), equal-weight panel aggregation)."""
    per_sym_gross: Dict[str, pd.Series] = {}
    per_sym_net: Dict[str, pd.Series] = {}
    total_trades = 0
    per_sym_sh_gross: Dict[str, float] = {}
    per_sym_sh_net: Dict[str, float] = {}

    for sym, df in panels.items():
        z = zscore_series(df["spread"], zwin)
        sig = pd.Series(0.0, index=df.index)
        sig[z > z_thr] = -1.0
        sig[z < -z_thr] = 1.0
        sig_lag = sig.shift(1).fillna(0.0)
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
                i = end
                last_pos = 0.0
                continue
            i += 1
        fwd = df["fwd_ret_1"].fillna(0.0)
        pnl_gross_sym = pos * fwd
        pos_change = pos.diff().fillna(pos.iloc[0])
        cost_series = pd.Series(0.0, index=df.index)
        cost_series[pos_change != 0] = cost_per_fill
        pnl_net_sym = pnl_gross_sym - cost_series
        per_sym_gross[sym] = pnl_gross_sym
        per_sym_net[sym] = pnl_net_sym
        total_trades += trades
        per_sym_sh_gross[sym] = sharpe(pnl_gross_sym)
        per_sym_sh_net[sym] = sharpe(pnl_net_sym)

    if not per_sym_net:
        empty = pd.Series(dtype=float)
        return empty, empty, 0, {}, {}

    gross = pd.concat(per_sym_gross, axis=1).fillna(0.0).mean(axis=1)
    net = pd.concat(per_sym_net, axis=1).fillna(0.0).mean(axis=1)
    return net, gross, total_trades, per_sym_sh_net, per_sym_sh_gross


def run_full_backtest(
    name: str,
    panels: Dict[str, pd.DataFrame],
    z_thr: float = 2.0,
    hold: int = 1,
    n_trials: int = 5,
) -> Tuple[Dict, Dict]:
    """Run K175 backtest + §6 gate evaluation."""
    pnl_net, pnl_gross, n_trades, per_sh_net, per_sh_gross = variant_z(
        panels, z_thr=z_thr, hold=hold
    )
    sh_net = sharpe(pnl_net)
    sh_gross = sharpe(pnl_gross)
    cg_net = cagr(pnl_net)
    cg_gross = cagr(pnl_gross)
    dd_net = max_dd(pnl_net)
    split = int(len(pnl_net) * 0.7)
    is_pnl = pnl_net.iloc[:split]
    oos_pnl = pnl_net.iloc[split:]
    is_sh = sharpe(is_pnl)
    oos_sh = sharpe(oos_pnl)
    is_sh_g = sharpe(pnl_gross.iloc[:split])
    oos_sh_g = sharpe(pnl_gross.iloc[split:])
    wf_mean, wf_folds = wf_3fold(pnl_net)
    perm_p = perm_test(pnl_net, n=200)
    ci_lo, ci_hi = bootstrap_ci(pnl_net, n=200)
    dsr_val = dsr(pnl_net, n_trials=n_trials)
    trades_per_year = float(n_trades / max(len(pnl_net) / EVENTS_PER_YEAR, 1e-6))

    # §6 strict gates
    gates = {
        "G1_OOS_Sh_ge_1": oos_sh >= 1.0,
        "G2_perm_p_le_0p05": perm_p <= 0.05,
        "G3_DSR_ge_0p95": dsr_val >= 0.95,
        "G4_WF_folds_all_positive": all(x > 0 for x in wf_folds) if wf_folds else False,
        "G5_IS_OOS_ratio_ge_0p5": (oos_sh / is_sh >= 0.5) if is_sh > 0 else False,
        "G6_Gross_Sh_ge_0p3": sh_gross >= 0.3,
        "G7_Trades_yr_ge_20": trades_per_year >= 20,
    }
    gates_passed = sum(gates.values())
    if sh_gross >= 1.0:
        verdict = "PASS" if gates_passed >= 6 else ("MARGINAL" if gates_passed >= 4 else "FAIL")
    else:
        verdict = "FAIL_GROSS_LOW"

    metrics = {
        "variant": name,
        "symbols": sorted(panels.keys()),
        "n_events": int(len(pnl_net)),
        "sharpe_gross": round(sh_gross, 4),
        "sharpe_net": round(sh_net, 4),
        "cagr_gross": round(cg_gross, 4),
        "cagr_net": round(cg_net, 4),
        "max_dd_net": round(dd_net, 4),
        "is_sharpe_gross": round(is_sh_g, 4),
        "is_sharpe_net": round(is_sh, 4),
        "oos_sharpe_gross": round(oos_sh_g, 4),
        "oos_sharpe_net": round(oos_sh, 4),
        "wf_mean_sharpe_net": round(wf_mean, 4),
        "wf_folds_net": [round(x, 4) for x in wf_folds],
        "perm_pvalue_net": round(perm_p, 4),
        "bootstrap_ci_5_95_net": [round(ci_lo, 4), round(ci_hi, 4)],
        "dsr_net": round(dsr_val, 4),
        "n_trades": int(n_trades),
        "trades_per_year": round(trades_per_year, 2),
        "per_symbol_sharpe_gross": {k: round(v, 4) for k, v in per_sh_gross.items()},
        "per_symbol_sharpe_net": {k: round(v, 4) for k, v in per_sh_net.items()},
        "gates": {k: bool(v) for k, v in gates.items()},
        "gates_passed": int(gates_passed),
        "gates_total": 7,
        "verdict": verdict,
    }

    curves = {
        "timestamps": [t.isoformat() for t in pnl_net.index],
        "equity_gross": equity_curve(pnl_gross),
        "equity_net": equity_curve(pnl_net),
    }
    return metrics, curves


# ================================================================ Main

def main() -> Dict:
    t0 = time.time()
    print("=" * 70)
    print("Wave K184 - HL Mid-Cap Alt Universe Expansion")
    print(f"Target symbols: {NEW_SYMBOLS}")
    print("=" * 70)

    # ---- Step 1: Fetch/Load HL FR data
    print("\n[Step 1] Fetching HL FR data for new symbols...")
    hl_data_status: Dict[str, Dict] = {}
    for sym in NEW_SYMBOLS:
        print(f"\n  Processing {sym}...")
        df = load_or_fetch_hl_fr(sym, force_fetch=False)
        if df is None or len(df) == 0:
            hl_data_status[sym] = {"status": "fetch_failed", "n_rows": 0}
            print(f"  {sym}: HL FR fetch FAILED")
        else:
            hl_data_status[sym] = {
                "status": "ok",
                "n_rows": len(df),
                "date_start": str(df["timestamp"].min().date()),
                "date_end": str(df["timestamp"].max().date()),
            }

    # ---- Step 2: Build panels
    print("\n[Step 2] Building 8h event panels...")
    all_panels: Dict[str, pd.DataFrame] = {}
    panel_meta: Dict[str, Dict] = {}
    for sym in NEW_SYMBOLS:
        if hl_data_status.get(sym, {}).get("status") != "ok":
            panel_meta[sym] = {"status": "missing_hl_data"}
            continue
        p = build_panel(sym)
        if p is None:
            panel_meta[sym] = {"status": "panel_build_failed"}
            continue
        all_panels[sym] = p
        panel_meta[sym] = {
            "status": "ok",
            "n_events": int(len(p)),
            "date_start": str(p.index.min().date()),
            "date_end": str(p.index.max().date()),
            "spread_mean_bps": round(float(p["spread"].mean() * 1e4), 4),
            "spread_std_bps": round(float(p["spread"].std() * 1e4), 4),
            "hl_data_n_rows": hl_data_status[sym]["n_rows"],
            "bybit_fr_cache": f"cache/bybit_fr_{sym}USDT_730d.parquet",
            "hl_fr_cache": f"cache/k163_hl/hl_fr_{sym}.parquet",
        }
        print(
            f"  {sym}: {len(p)} events  [{p.index.min().date()} - {p.index.max().date()}]  "
            f"spread={p['spread'].mean()*1e4:+.4f} bps (mean)  std={p['spread'].std()*1e4:.4f} bps"
        )

    if not all_panels:
        print("\nERROR: No panels built for any symbol. Aborting.")
        return {}

    # ---- Step 3: Lag analysis
    print("\n[Step 3] Lag Analysis (K183 criterion: z>2 lag1_short > 30 bps)")
    print("-" * 70)
    lag_results: Dict[str, Dict] = {}
    for sym, df in all_panels.items():
        la = compute_lag_analysis(df, z_thr=2.0, win=30)
        lag_results[sym] = la
        lag0s = la.get("k180_lag0_short_bps")
        lag1s = la.get("k180_lag1_short_bps")
        lag0l = la.get("k180_lag0_long_bps")
        lag1l = la.get("k180_lag1_long_bps")
        passes = la.get("passes_k175_filter", False)
        n_above = la["tails"].get("z_above_2", {}).get("n", 0)
        n_below = la["tails"].get("z_below_neg2", {}).get("n", 0)
        verdict_str = "PASS" if passes else "FAIL"
        # Format None as N/A
        def fmt_bps(v):
            return f"{v:+6.1f}" if v is not None else "   N/A"
        print(
            f"  {sym:5s}: lag0_short={fmt_bps(lag0s)} bps  lag1_short={fmt_bps(lag1s)} bps  "
            f"lag0_long={fmt_bps(lag0l)} bps  lag1_long={fmt_bps(lag1l)} bps  "
            f"n_short={n_above}  n_long={n_below}  -> {verdict_str}"
        )

    # Lag summary table
    lag_summary_table: Dict[str, Dict] = {}
    for sym in NEW_SYMBOLS:
        if sym not in lag_results:
            lag_summary_table[sym] = {
                "status": panel_meta.get(sym, {}).get("status", "missing"),
                "n_events": None,
            }
            continue
        la = lag_results[sym]
        n_above = la["tails"].get("z_above_2", {}).get("n", 0)
        n_below = la["tails"].get("z_below_neg2", {}).get("n", 0)
        lag_summary_table[sym] = {
            "n_events": panel_meta[sym]["n_events"],
            "date_range": f"{panel_meta[sym]['date_start']} to {panel_meta[sym]['date_end']}",
            "spread_mean_bps": panel_meta[sym]["spread_mean_bps"],
            "spread_std_bps": panel_meta[sym]["spread_std_bps"],
            "n_z_above_2": n_above,
            "n_z_below_neg2": n_below,
            "lag0_short_bps": la.get("k180_lag0_short_bps"),
            "lag1_short_bps": la.get("k180_lag1_short_bps"),
            "lag0_long_bps": la.get("k180_lag0_long_bps"),
            "lag1_long_bps": la.get("k180_lag1_long_bps"),
            "passes_filter": la.get("passes_k175_filter", False),
        }

    # Candidates
    candidates = [
        sym for sym in NEW_SYMBOLS
        if sym in lag_results and lag_results[sym].get("passes_k175_filter", False)
    ]
    excluded = [sym for sym in NEW_SYMBOLS if sym not in candidates]
    print(f"\nCandidates passing K175 lag filter: {candidates}")
    print(f"Excluded (fail lag filter): {excluded}")

    # ---- Step 4: K175 backtests on candidates
    print("\n[Step 4] K175 V_{{sym}}_maker Backtests (2 bp/side maker cost)")
    print("-" * 70)

    all_metrics: List[Dict] = []
    all_curves: Dict[str, Dict] = {}

    # Per-symbol single variants for candidates
    for sym in candidates:
        panels_single = {sym: all_panels[sym]}
        name = f"V_{sym}_maker"
        m, c = run_full_backtest(name, panels_single, n_trials=5)
        all_metrics.append(m)
        all_curves[name] = c
        print(
            f"  {name:22s}  Sh_gross={m['sharpe_gross']:+.3f}  Sh_net={m['sharpe_net']:+.3f}  "
            f"OOS_net={m['oos_sharpe_net']:+.3f}  perm_p={m['perm_pvalue_net']:.3f}  "
            f"trades/yr={m['trades_per_year']:.0f}  gates={m['gates_passed']}/7  {m['verdict']}"
        )

    # Combined variant if 2+ candidates
    if len(candidates) >= 2:
        combined_panels = {s: all_panels[s] for s in candidates}
        m, c = run_full_backtest("V_alts_combined", combined_panels, n_trials=5)
        all_metrics.append(m)
        all_curves["V_alts_combined"] = c
        print(
            f"  {'V_alts_combined':22s}  Sh_gross={m['sharpe_gross']:+.3f}  Sh_net={m['sharpe_net']:+.3f}  "
            f"OOS_net={m['oos_sharpe_net']:+.3f}  perm_p={m['perm_pvalue_net']:.3f}  "
            f"trades/yr={m['trades_per_year']:.0f}  gates={m['gates_passed']}/7  {m['verdict']}"
        )

    # XRP+SUI+candidates combined if candidates exist
    xrp_sui_syms = []
    for s in ["XRP", "SUI"]:
        if (HL_CACHE / f"hl_fr_{s}.parquet").exists():
            p = build_panel(s)
            if p is not None:
                xrp_sui_syms.append(s)
                all_panels[s] = p

    if candidates and xrp_sui_syms:
        all_combined = list(xrp_sui_syms) + list(candidates)
        combined_panels = {s: all_panels[s] for s in all_combined if s in all_panels}
        m, c = run_full_backtest("V_xrp_sui_alts_combined", combined_panels, n_trials=5)
        all_metrics.append(m)
        all_curves["V_xrp_sui_alts_combined"] = c
        print(
            f"  {'V_xrp_sui_alts_combined':22s}  Sh_gross={m['sharpe_gross']:+.3f}  Sh_net={m['sharpe_net']:+.3f}  "
            f"OOS_net={m['oos_sharpe_net']:+.3f}  perm_p={m['perm_pvalue_net']:.3f}  "
            f"trades/yr={m['trades_per_year']:.0f}  gates={m['gates_passed']}/7  {m['verdict']}"
        )

    # Even for non-candidates, run single backtest for documentation
    non_candidates = [s for s in NEW_SYMBOLS if s in all_panels and s not in candidates]
    for sym in non_candidates:
        panels_single = {sym: all_panels[sym]}
        name = f"V_{sym}_maker_INFO"
        m, c = run_full_backtest(name, panels_single, n_trials=5)
        all_metrics.append(m)
        all_curves[name] = c
        print(
            f"  {name:22s}  Sh_gross={m['sharpe_gross']:+.3f}  Sh_net={m['sharpe_net']:+.3f}  "
            f"OOS_net={m['oos_sharpe_net']:+.3f}  perm_p={m['perm_pvalue_net']:.3f}  "
            f"trades/yr={m['trades_per_year']:.0f}  [INFO only, failed lag filter]"
        )

    # ---- Step 5: ACCEPT summary
    print("\n[Step 5] §6 Gate Summary")
    print("-" * 70)
    accept_candidates = []
    for m in all_metrics:
        if m["verdict"] == "PASS":
            accept_candidates.append(m["variant"])
        print(
            f"  {m['variant']:30s}  Sh_gross={m['sharpe_gross']:+.3f}  Sh_net={m['sharpe_net']:+.3f}  "
            f"OOS_net={m['oos_sharpe_net']:+.3f}  verdict={m['verdict']}"
        )
    print(f"\nACCEPT candidates: {accept_candidates}")

    runtime = round(time.time() - t0, 1)

    # ---- Assemble output JSON
    output = {
        "wave": "K184",
        "parent_wave": "K183",
        "date": "2026-05-25",
        "objective": "HL mid-cap alt universe expansion: ARB/INJ/TAO/NEAR/JTO lag-filter screening",
        "runtime_sec": runtime,
        "cost_model": {
            "slippage_bps_per_side": SLIPPAGE_BPS_PER_SIDE,
            "maker_fee_bps_per_side": MAKER_FEE_BPS_PER_SIDE,
            "cost_per_fill_bps": SLIPPAGE_BPS_PER_SIDE + MAKER_FEE_BPS_PER_SIDE,
            "round_trip_bps": 2 * (SLIPPAGE_BPS_PER_SIDE + MAKER_FEE_BPS_PER_SIDE),
        },
        "lag_convention": {
            "k180_lag0": "fwd_ret_1: return at t+1 after signal at t (K175 trade period)",
            "k180_lag1": "fwd_ret_2: return at t+2 (persistence check, FILTER KEY)",
            "filter_field": "k180_lag1_short_bps (z>2 tail)",
            "filter_threshold_bps": LAG1_EDGE_ABS_THRESHOLD_BPS,
        },
        "new_symbols_targeted": NEW_SYMBOLS,
        "hl_data_acquisition": hl_data_status,
        "panel_meta": panel_meta,
        "lag_summary_table": lag_summary_table,
        "lag_analysis_full": lag_results,
        "candidates": candidates,
        "excluded_symbols": excluded,
        "backtests": all_metrics,
        "accept_candidates": accept_candidates,
        "k185_integration_recommendation": {
            "description": "K185 integration: add ACCEPT candidates to K176 ensemble if any pass",
            "new_symbols_passing_gates": accept_candidates,
            "action": (
                f"Add {accept_candidates} as new K176 strategy slots."
                if accept_candidates
                else "No new symbols pass §6 gates. K176 ensemble remains at 8 strategies. "
                     "K185 should explore alternative mid-cap alt strategies or different lag windows."
            ),
        },
    }

    out_json = ROOT / "wave_k184_hl_alt_expand.json"
    out_json.write_text(json.dumps(output, indent=2, default=str))
    print(f"\nWrote {out_json} ({out_json.stat().st_size:,} bytes)")

    if all_curves:
        out_curves = ROOT / "wave_k184_curves.json"
        out_curves.write_text(json.dumps(all_curves, default=str))
        print(f"Wrote {out_curves} ({out_curves.stat().st_size:,} bytes)")

    print(f"\nRuntime: {runtime}s")
    print("=" * 70)
    print("ACCEPT candidates and K185 integration recommendation:")
    print("=" * 70)
    if accept_candidates:
        for c in accept_candidates:
            print(f"  NEW ACCEPT -> {c}: Recommend K185 integration into K176 ensemble")
    else:
        print("  No new alt symbols pass §6 gates.")
        print("  K176 ensemble remains at 8 strategies (v5, XRP+SUI via K175).")
        print("  K185 recommendation: try wider z_thr windows (1.5/1.75) or")
        print("  alternative alt families (L1s: APT, SUI-adjacent, etc.)")
    print("=" * 70)

    return output


if __name__ == "__main__":
    main()
