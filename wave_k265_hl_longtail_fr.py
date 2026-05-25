"""
Wave K265 — HL Long-Tail Funding Rate Carry
============================================
Hypothesis (tip-scraper R9-04):
  HL lower-liquidity (long-tail) perps carry 20-60% APR funding vs ~4% for majors.
  Exploit via pure HL cross-sectional carry: short high-FR, long low/negative-FR.
  Universe is distinct from K208 (major CEX-DEX spread), making K265 orthogonal.

Strategy:
  1. Universe: HL longtail symbols (NOT K208 REVERSE_10 majors)
  2. Signal: 14-day rolling mean of hourly HL FR → aggregated to 8h periods
  3. Short symbols with FR > p75 (collect from longs)
     Long  symbols with FR < p25 (collect from shorts, or near-negative FR)
  4. Dollar-neutral within each sleeve
  5. 8h rebalance (daily-level aggregation in backtest), 2bp/side maker
  6. Walk-forward 4-fold

Data: Primarily existing HL cache (k163_hl), fetching new longtail symbols as needed.
K208 symbols excluded: SOL, XRP, SUI, OP, APT, AXS, JTO, IMX, SAND, ADA

Runtime: <12 min.
"""
from __future__ import annotations

import json
import math
import time
import urllib.request
import urllib.error
import warnings
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

START_TIME = time.time()
BASE     = Path("/Users/nekonaomichi/crypto-lab")
CACHE    = BASE / "cache"
HL_CACHE = CACHE / "k163_hl"
HL_CACHE.mkdir(parents=True, exist_ok=True)

HL_API_URL = "https://api.hyperliquid.xyz/info"

# ── Config ───────────────────────────────────────────────────────────────────
FR_WINDOW_DAYS = 14       # rolling mean window for signal
QUARTILE       = 0.25     # top/bottom 25%
COST_BPS       = 2.0      # 2bp per side maker
COST_RATE      = COST_BPS / 1e4
PPY            = 365.0
N_FOLDS        = 4
MIN_EVENTS     = 2000     # min hourly events to include symbol (~83 days)

# K208 majors to EXCLUDE (K265 must be orthogonal to K208 reverse carry panel)
K208_EXCLUDE = {"SOL", "XRP", "SUI", "OP", "APT", "AXS", "JTO", "IMX", "SAND", "ADA"}

# Existing symbols in k163_hl cache
CACHE_SYMBOLS = [
    "AAVE", "ADA", "APT", "ARB", "ATOM", "AVAX", "AXS",
    "BNB", "BONK", "BTC", "CRV", "DOGE", "DOT", "ETH",
    "FET", "IMX", "INJ", "JTO", "LDO", "MKR", "NEAR",
    "OP", "PEPE", "RNDR", "SAND", "SHIB", "SOL", "SUI",
    "SUSHI", "TAO", "UNI", "WIF", "XRP",
]

# HL tickers for symbols where HL uses different name (kXXX form)
HL_TICKER_MAP = {
    "PEPE":  "kPEPE",
    "BONK":  "kBONK",
    "SHIB":  "kSHIB",
    "FLOKI": "kFLOKI",
}

# New longtail symbols to fetch (not yet in cache)
NEW_SYMBOLS = [
    ("TIA",  "TIA"),
    ("JUP",  "JUP"),
    ("BOME", "BOME"),
    ("ENA",  "ENA"),
    ("STRK", "STRK"),
    ("PYTH", "PYTH"),
    ("MEME", "MEME"),
    ("WLD",  "WLD"),
    ("SEI",  "SEI"),
    ("ONDO", "ONDO"),
    ("ARK",  "ARK"),
    ("BLUR", "BLUR"),
]

OUT_JSON    = BASE / "wave_k265_hl_longtail_fr.json"
OUT_CURVES  = BASE / "wave_k265_curves.json"
OUT_MD      = BASE / "wave_k265_hl_longtail_fr.md"
PARQUET_OUT = CACHE / "hl_longtail_fr_daily.parquet"


# ── Helpers ──────────────────────────────────────────────────────────────────
def sharpe(ret: np.ndarray) -> float:
    r = np.asarray(ret, dtype=float)
    r = r[np.isfinite(r)]
    if len(r) < 10 or r.std() == 0:
        return 0.0
    return float(r.mean() / r.std() * math.sqrt(PPY))


def max_dd(ret: np.ndarray) -> float:
    r = np.asarray(ret, dtype=float)
    r = r[np.isfinite(r)]
    if len(r) == 0:
        return 0.0
    eq   = np.cumprod(1 + r)
    peak = np.maximum.accumulate(eq)
    return float(((eq - peak) / peak).min())


def ann_ret(ret: np.ndarray) -> float:
    r = np.asarray(ret, dtype=float)
    r = r[np.isfinite(r)]
    return float(r.mean() * PPY)


def ann_vol(ret: np.ndarray) -> float:
    r = np.asarray(ret, dtype=float)
    r = r[np.isfinite(r)]
    return float(r.std() * math.sqrt(PPY))


def win_rate(ret: np.ndarray) -> float:
    r = np.asarray(ret, dtype=float)
    r = r[np.isfinite(r) & (r != 0)]
    return float((r > 0).mean()) if len(r) > 0 else 0.0


def metrics(ret_arr: np.ndarray) -> dict:
    return {
        "sharpe":       sharpe(ret_arr),
        "max_dd":       max_dd(ret_arr),
        "ann_ret":      ann_ret(ret_arr),
        "ann_vol":      ann_vol(ret_arr),
        "win_rate":     win_rate(ret_arr),
        "total_return": float(np.nanprod(1 + ret_arr) - 1),
        "n_days":       int(np.sum(np.isfinite(ret_arr))),
    }


# ── HL API Fetch ──────────────────────────────────────────────────────────────
def hl_fetch_page(coin: str, start_ms: int, end_ms: int) -> List[Dict]:
    payload = json.dumps({
        "type": "fundingHistory",
        "coin": coin,
        "startTime": start_ms,
        "endTime": end_ms
    }).encode()
    req = urllib.request.Request(
        HL_API_URL, data=payload,
        headers={"Content-Type": "application/json"}, method="POST"
    )
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode())
                return data if isinstance(data, list) else []
        except urllib.error.HTTPError as e:
            if e.code == 429:
                wait = 15 * (attempt + 1)
                print(f"    429 {coin}, wait {wait}s...")
                time.sleep(wait)
                continue
            if e.code == 500:
                return []
            print(f"    HTTP {e.code} for {coin}")
            return []
        except Exception as ex:
            print(f"    err {coin}: {ex}")
            if attempt < 3:
                time.sleep(5)
    return []


def fetch_hl_fr(sym: str, hl_ticker: str, days: int = 730,
                force: bool = False) -> Optional[pd.DataFrame]:
    """Fetch HL FR with pagination; cache as parquet."""
    cache = HL_CACHE / f"hl_fr_{sym}.parquet"
    if cache.exists() and not force:
        df = pd.read_parquet(cache)
        print(f"  {sym}: cached ({len(df)} rows)")
        return df

    now_ms   = int(time.time() * 1000)
    start_ms = now_ms - days * 86400 * 1000
    all_events: List[Dict] = []
    page_start = start_ms

    print(f"  Fetching {sym} [{hl_ticker}]...", flush=True)
    while page_start < now_ms:
        events = hl_fetch_page(hl_ticker, page_start, now_ms)
        if not events:
            break
        all_events.extend(events)
        last_t = max(e.get("time", 0) for e in events)
        if last_t <= page_start or len(events) < 500:
            break
        page_start = last_t + 1
        time.sleep(1.0)

    if not all_events:
        print(f"    {sym}: no data returned")
        return None

    df = pd.DataFrame(all_events)
    df["timestamp"] = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_localize(None)
    df["hl_fr"]     = df["fundingRate"].astype(float)
    df = df[["timestamp", "hl_fr"]].drop_duplicates("timestamp").sort_values("timestamp").reset_index(drop=True)

    df.to_parquet(cache, index=False)
    print(f"    {sym}: fetched {len(df)} rows")
    return df


# ── Load + Build Panel ────────────────────────────────────────────────────────
def load_all_hl_fr() -> Tuple[pd.DataFrame, List[str], Dict]:
    """
    Load HL FR for all candidate symbols (cache + new fetch).
    Aggregate to daily mean (≈3 × 8h events per day, hourly data on HL).
    Returns (daily_fr_panel, kept_syms, per_sym_stats).
    """
    # Step 1: existing cache symbols (filter out K208 exclusions)
    load_list: List[Tuple[str, str]] = []
    for sym in CACHE_SYMBOLS:
        if sym in K208_EXCLUDE:
            continue
        ticker = HL_TICKER_MAP.get(sym, sym)
        load_list.append((sym, ticker))

    # Step 2: new longtail symbols
    existing_syms = {s for s, _ in load_list}
    for sym, ticker in NEW_SYMBOLS:
        if sym not in existing_syms and sym not in K208_EXCLUDE:
            load_list.append((sym, ticker))

    print(f"\n[K265] Loading {len(load_list)} candidate symbols...")
    frames     = []
    kept_syms  = []
    sym_stats  = {}

    for sym, ticker in load_list:
        try:
            df = fetch_hl_fr(sym, ticker, days=730)
            if df is None or len(df) < MIN_EVENTS:
                print(f"    {sym}: skip (n={len(df) if df is not None else 0} < {MIN_EVENTS})")
                continue

            ts = pd.to_datetime(df["timestamp"])
            fr = df["hl_fr"].values

            # Aggregate to daily mean
            daily = (df.assign(date=ts.dt.normalize())
                       .groupby("date")["hl_fr"]
                       .mean()
                       .rename(sym))

            if len(daily) < 200:
                print(f"    {sym}: skip (only {len(daily)} daily bars)")
                continue

            # Per-symbol FR statistics
            mean_fr = float(np.nanmean(fr))
            std_fr  = float(np.nanstd(fr))
            pct_pos = float(np.mean(fr > 0))
            pct_neg = float(np.mean(fr < 0))
            abs_mean = float(np.nanmean(np.abs(fr)))
            ann_carry_pct = abs_mean * 24 * 365 * 100  # per hourly event × 24/day × 365

            sym_stats[sym] = {
                "n_events":       len(df),
                "n_days":         len(daily),
                "date_start":     str(ts.min().date()),
                "date_end":       str(ts.max().date()),
                "mean_fr_pct":    round(mean_fr * 100, 5),
                "std_fr_pct":     round(std_fr * 100, 5),
                "abs_mean_fr_pct":round(abs_mean * 100, 5),
                "ann_carry_pct":  round(ann_carry_pct, 2),
                "pct_pos_fr":     round(pct_pos, 3),
                "pct_neg_fr":     round(pct_neg, 3),
                "high_carry":     abs_mean > 0.0001,   # |mean FR| > 0.01% per event
            }

            frames.append(daily)
            kept_syms.append(sym)
            time.sleep(0.05)

        except Exception as e:
            print(f"    {sym}: error {e}")
            continue

    panel = pd.concat(frames, axis=1).sort_index() if frames else pd.DataFrame()
    print(f"\n[K265] Panel built: {len(kept_syms)} symbols, {len(panel)} days")
    return panel, kept_syms, sym_stats


# ── Signal & Weights ──────────────────────────────────────────────────────────
def compute_signal(fr_panel: pd.DataFrame) -> pd.DataFrame:
    """
    14d rolling mean of daily FR (signal = yesterday's known FR state).
    Shift +1 to avoid look-ahead: signal at day t is computed at close of t-1.
    """
    roll = fr_panel.rolling(window=FR_WINDOW_DAYS, min_periods=7).mean()
    return roll.shift(1)


def dollar_neutral_weights(sig_row: pd.Series) -> pd.Series:
    """
    FR carry logic (HL perps, funding settles every hour):
      FR > 0: longs pay shorts → as SHORT you RECEIVE positive carry
      FR < 0: shorts pay longs → as LONG you RECEIVE negative-FR carry

    Signal = rolling mean FR:
      HIGH signal (most positive FR) → SHORT (receive from longs)  → short sleeve
      LOW signal  (most negative FR) → LONG  (receive from shorts) → long sleeve

    Both sleeves earn carry; combined = long-short dollar-neutral FR capture.
    """
    valid = sig_row.dropna()
    n_sym = len(valid)
    if n_sym < 4:
        return pd.Series(0.0, index=sig_row.index)

    n_q   = max(1, int(n_sym * QUARTILE))
    ranked = valid.rank(ascending=True)

    # Long: bottom ranked (most negative / lowest FR) → rank 1..n_q
    longs  = ranked[ranked <= n_q].index
    # Short: top ranked (most positive FR) → rank n-n_q+1..n
    shorts = ranked[ranked > n_sym - n_q].index

    w = pd.Series(0.0, index=sig_row.index)
    if len(longs)  > 0:
        w[longs]  = +1.0 / len(longs)
    if len(shorts) > 0:
        w[shorts] = -1.0 / len(shorts)
    return w


def compute_weights(sig: pd.DataFrame) -> pd.DataFrame:
    return sig.apply(dollar_neutral_weights, axis=1)


# ── PnL ──────────────────────────────────────────────────────────────────────
def compute_pnl(fr_panel: pd.DataFrame,
                weights: pd.DataFrame) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """
    Pure FR carry PnL (no price return component — this is a pure funding strategy).
    At each daily rebalance point we hold into 3 × 8h settlement events.
    PnL per symbol per day = w * (-daily_total_fr)
      - Long (w>0), FR>0 → pays → pnl = -w*fr < 0 (unfavorable, so we avoid these)
      - Short (w<0), FR>0 → receives → pnl = -w*fr > 0 (favorable, K265 targets these)
      - Long (w>0), FR<0 → receives from shorts → pnl = -w*fr > 0 (favorable)

    Daily FR: sum of ~24 hourly events. We stored daily MEAN of hourly events.
    HL typically has events every ~1h, so ~24 per day.
    FR per event is already scaled to the settlement interval.
    So daily total = mean_hourly_fr * 24.

    For cross-sectional comparison, we use daily mean directly (ranking is ordinal).
    For absolute carry PnL: multiply by number of events/day (~24 hourly on HL).
    """
    common = fr_panel.index.intersection(weights.index)
    fr_c   = fr_panel.loc[common]
    w_c    = weights.loc[common]

    # Lag weights by 1 day (execute at close t-1, settle on day t)
    w_lag = w_c.shift(1).fillna(0.0)

    # HL hourly FR: daily total = mean * 24 events/day
    # (FR rate already per-event, settled each hour)
    fr_daily = fr_c * 24.0

    # FR carry PnL: receiver (short when FR>0, long when FR<0) earns
    pnl_fr = (-w_lag * fr_daily).sum(axis=1)

    # Turnover cost: daily weight change × cost
    turn   = (w_c - w_c.shift(1).fillna(0.0)).abs().sum(axis=1)
    cost   = turn * COST_RATE

    pnl_net   = pnl_fr - cost
    pnl_gross = pnl_fr
    return pnl_net, pnl_gross, turn


# ── Walk-Forward 4-Fold ───────────────────────────────────────────────────────
def walk_forward(pnl: pd.Series) -> List[Dict]:
    n         = len(pnl)
    fold_size = n // N_FOLDS
    folds     = []
    for i in range(N_FOLDS):
        s = i * fold_size
        e = s + fold_size if i < N_FOLDS - 1 else n
        fold_ret = pnl.iloc[s:e].values
        fold_m   = metrics(fold_ret)
        fold_m["fold"]  = i
        fold_m["start"] = str(pnl.index[s].date())
        fold_m["end"]   = str(pnl.index[e - 1].date())
        folds.append(fold_m)
    return folds


# ── Correlation vs K246a Components ──────────────────────────────────────────
def compute_correlations(pnl_k265: pd.Series) -> Dict[str, float]:
    """Compute |ρ| with K198, K208, K226 daily returns."""
    corrs = {}

    # K198: use pnl_ridge from wave_k198_curves.json
    try:
        with open(BASE / "wave_k198_curves.json") as f:
            d = json.load(f)
        dates = pd.to_datetime(d["dates_ml"])
        pnl   = pd.Series(d["pnl_ridge"], index=dates).dropna()
        common = pnl.index.intersection(pnl_k265.index)
        if len(common) > 30:
            corrs["K198"] = round(float(np.corrcoef(
                pnl.loc[common].values, pnl_k265.loc[common].values)[0, 1]), 4)
        else:
            corrs["K198"] = None
    except Exception as e:
        corrs["K198"] = f"error: {e}"

    # K208: use K208_filtered cumulative_pnl → aggregate 8h events to daily
    try:
        with open(BASE / "wave_k208_curves.json") as f:
            d = json.load(f)
        k208_data = d["K208_filtered"]
        # timestamps are ISO strings at 8h cadence
        ts    = pd.to_datetime(k208_data["timestamps"])
        cum   = np.array(k208_data["cumulative_pnl"])
        s8    = pd.Series(np.diff(cum, prepend=cum[0]), index=ts)
        # aggregate to daily sum of 8h returns
        pnl   = s8.groupby(s8.index.normalize()).sum()
        pnl.index = pd.to_datetime(pnl.index)
        common = pnl.index.intersection(pnl_k265.index)
        if len(common) > 30:
            corrs["K208"] = round(float(np.corrcoef(
                pnl.loc[common].values, pnl_k265.loc[common].values)[0, 1]), 4)
        else:
            corrs["K208"] = None
    except Exception as e:
        corrs["K208"] = f"error: {e}"

    # K226: use strat_daily_ret from wave_k226_curves.json
    try:
        with open(BASE / "wave_k226_curves.json") as f:
            d = json.load(f)
        dates = pd.to_datetime(d["dates"])
        pnl   = pd.Series(d["strat_daily_ret"], index=dates).dropna()
        common = pnl.index.intersection(pnl_k265.index)
        if len(common) > 30:
            corrs["K226"] = round(float(np.corrcoef(
                pnl.loc[common].values, pnl_k265.loc[common].values)[0, 1]), 4)
        else:
            corrs["K226"] = None
    except Exception as e:
        corrs["K226"] = f"error: {e}"

    return corrs


# ── Main ──────────────────────────────────────────────────────────────────────
def main() -> None:
    print("=" * 60)
    print("Wave K265 — HL Long-Tail FR Carry Strategy")
    print("=" * 60)

    # 1. Load / Fetch data
    fr_panel, kept_syms, sym_stats = load_all_hl_fr()

    if fr_panel.empty or len(kept_syms) < 4:
        print("[K265] FATAL: not enough symbols. Abort.")
        return

    # 2. Identify high-carry longtail symbols
    high_carry_syms = [s for s, st in sym_stats.items() if st["high_carry"]]
    print(f"\n[K265] High-carry symbols (|mean FR| > 0.01%/event): {high_carry_syms}")

    # 3. Compute signal and weights
    sig     = compute_signal(fr_panel)
    weights = compute_weights(sig)

    # 4. Compute PnL
    pnl_net, pnl_gross, turnover = compute_pnl(fr_panel, weights)
    pnl_net   = pnl_net.dropna()
    pnl_gross = pnl_gross.dropna()

    n_total = len(pnl_net)
    n_oos   = int(n_total * 0.30)
    n_is    = n_total - n_oos

    is_ret  = pnl_net.iloc[:n_is].values
    oos_ret = pnl_net.iloc[n_is:].values
    all_ret = pnl_net.values

    is_m   = metrics(is_ret)
    oos_m  = metrics(oos_ret)
    full_m = metrics(all_ret)
    gross_m = metrics(pnl_gross.values)

    # 5. Walk-forward
    wf_folds = walk_forward(pnl_net)
    wf_sharpes = [f["sharpe"] for f in wf_folds]
    wf_summary = {
        "mean_sharpe": round(float(np.mean(wf_sharpes)), 4),
        "min_sharpe":  round(float(np.min(wf_sharpes)),  4),
        "all_positive": bool(all(s > 0 for s in wf_sharpes)),
    }

    # 6. Correlations vs K246a components
    corrs = compute_correlations(pnl_net)

    # 7. Acceptance gates
    gates = {
        "G1_WF_all_folds_positive": wf_summary["all_positive"],
        "G2_OOS_Sharpe_gt_1.0":    oos_m["sharpe"] > 1.0,
        "G3_rho_K198_lt_0.4":      isinstance(corrs.get("K198"), float) and abs(corrs["K198"]) < 0.4,
        "G4_rho_K208_lt_0.4":      isinstance(corrs.get("K208"), float) and abs(corrs["K208"]) < 0.4,
        "G5_rho_K226_lt_0.4":      isinstance(corrs.get("K226"), float) and abs(corrs["K226"]) < 0.4,
        "G6_OOS_MaxDD_gt_neg30pct": oos_m["max_dd"] > -0.30,
    }
    n_pass  = sum(1 for v in gates.values() if v is True)
    verdict = "ACCEPT" if all(gates.values()) else f"REJECT — fails gates"

    # 8. Print summary
    print(f"\n{'─'*50}")
    print(f"  OOS  Sh={oos_m['sharpe']:.3f}  MDD={oos_m['max_dd']:.2%}  "
          f"AnnRet={oos_m['ann_ret']:.2%}")
    print(f"  WF   mean_Sh={wf_summary['mean_sharpe']:.3f}  "
          f"min_Sh={wf_summary['min_sharpe']:.3f}  "
          f"all_pos={wf_summary['all_positive']}")
    print(f"  Corr K198={corrs.get('K198', 'n/a')}  K208={corrs.get('K208', 'n/a')}  "
          f"K226={corrs.get('K226', 'n/a')}")
    print(f"  Gates passed: {n_pass}/6  →  {verdict}")

    # 9. Save parquet cache of daily FR panel
    fr_panel.to_parquet(PARQUET_OUT)
    print(f"\n[K265] Saved daily FR panel → {PARQUET_OUT}")

    # 10. Save curves JSON
    curves = {
        "wave":   "K265",
        "dates":  [str(d.date()) for d in pnl_net.index],
        "equity": [round(float(v), 6) for v in np.cumprod(1 + pnl_net.values)],
        "pnl":    [round(float(v), 8) for v in pnl_net.values],
        "gross_pnl": [round(float(v), 8) for v in pnl_gross.values],
    }
    with open(OUT_CURVES, "w") as f:
        json.dump(curves, f, indent=2)

    # 11. Build per-fold details
    fold_list = []
    for fld in wf_folds:
        fold_list.append({
            "fold":        fld["fold"],
            "start":       fld["start"],
            "end":         fld["end"],
            "sharpe":      round(fld["sharpe"],    4),
            "max_dd":      round(fld["max_dd"],    6),
            "ann_ret":     round(fld["ann_ret"],   4),
            "ann_vol":     round(fld["ann_vol"],   4),
            "win_rate":    round(fld["win_rate"],  4),
            "total_return":round(fld["total_return"], 6),
            "n_days":      fld["n_days"],
        })

    # 12. Save main JSON
    avg_turn  = float(turnover.mean())
    output = {
        "wave":     "K265",
        "strategy": "HL_LongTail_FR_Carry",
        "as_of":    pd.Timestamp.utcnow().isoformat(),
        "runtime_s": round(time.time() - START_TIME, 1),
        "config": {
            "symbols_final":     kept_syms,
            "n_symbols":         len(kept_syms),
            "k208_excluded":     sorted(K208_EXCLUDE),
            "high_carry_symbols": high_carry_syms,
            "fr_window_days":    FR_WINDOW_DAYS,
            "quartile":          QUARTILE,
            "cost_bps_per_side": COST_BPS,
            "rebalance":         "daily (8h aggregated)",
        },
        "per_symbol_stats":    sym_stats,
        "is_metrics":          {k: round(v, 6) if isinstance(v, float) else v
                                for k, v in is_m.items()},
        "oos_metrics":         {k: round(v, 6) if isinstance(v, float) else v
                                for k, v in oos_m.items()},
        "full_metrics":        {k: round(v, 6) if isinstance(v, float) else v
                                for k, v in full_m.items()},
        "gross_metrics":       {k: round(v, 6) if isinstance(v, float) else v
                                for k, v in gross_m.items()},
        "walk_forward_folds":  fold_list,
        "wf_summary":          wf_summary,
        "turnover": {
            "avg_daily":              round(avg_turn, 6),
            "implied_cost_pct_day":   round(avg_turn * COST_RATE, 8),
        },
        "correlations": corrs,
        "gates":        gates,
        "n_gates_passed": n_pass,
        "verdict":      verdict,
        "date_range": {
            "start":        str(pnl_net.index[0].date()),
            "end":          str(pnl_net.index[-1].date()),
            "is_end":       str(pnl_net.index[n_is - 1].date()),
            "oos_start":    str(pnl_net.index[n_is].date()),
            "n_days_total": n_total,
            "n_days_is":    n_is,
            "n_days_oos":   n_oos,
        },
    }

    with open(OUT_JSON, "w") as f:
        json.dump(output, f, indent=2)
    print(f"[K265] Saved metrics → {OUT_JSON}")
    print(f"[K265] Saved curves  → {OUT_CURVES}")
    print(f"[K265] Runtime: {time.time() - START_TIME:.1f}s")

    # 13. Write MD report
    write_report(output, sym_stats, wf_folds, corrs, gates, n_pass, verdict)


def write_report(output, sym_stats, wf_folds, corrs, gates, n_pass, verdict) -> None:
    """Write compact markdown report (<100 lines)."""
    oos = output["oos_metrics"]
    full = output["full_metrics"]
    wfs  = output["wf_summary"]

    # High-carry table sorted by ann_carry_pct
    hc_syms = sorted(sym_stats.items(), key=lambda x: x[1]["ann_carry_pct"], reverse=True)

    lines = [
        f"# Wave K265 — HL Long-Tail FR Carry",
        f"",
        f"**Date:** {output['as_of'][:10]}  |  **Runtime:** {output['runtime_s']:.0f}s",
        f"",
        f"## Objective",
        f"Exploit HL long-tail perp funding rates (tip R9-04: 20-60% APR vs 4% for majors).",
        f"Pure HL cross-sectional carry. Universe excludes K208 majors (orthogonal).",
        f"",
        f"## Universe ({output['config']['n_symbols']} symbols)",
        f"**Excluded (K208):** {', '.join(output['config']['k208_excluded'])}",
        f"**Included:** {', '.join(output['config']['symbols_final'])}",
        f"",
        f"## Per-Symbol FR Characteristics (top by carry)",
        f"| Symbol | Mean FR%/event | Std | Ann Carry% | % pos |",
        f"|--------|---------------|-----|-----------|-------|",
    ]

    for sym, st in hc_syms[:20]:
        lines.append(
            f"| {sym:8s} | {st['mean_fr_pct']:+.5f} | {st['std_fr_pct']:.5f} "
            f"| {st['ann_carry_pct']:.1f}% | {st['pct_pos_fr']:.0%} |"
        )

    lines += [
        f"",
        f"## Strategy Performance",
        f"| Period | Sharpe | MaxDD | AnnRet | WinRate |",
        f"|--------|--------|-------|--------|---------|",
        f"| IS     | {output['is_metrics']['sharpe']:.3f} | {output['is_metrics']['max_dd']:.2%} | {output['is_metrics']['ann_ret']:.2%} | {output['is_metrics']['win_rate']:.1%} |",
        f"| OOS    | {oos['sharpe']:.3f} | {oos['max_dd']:.2%} | {oos['ann_ret']:.2%} | {oos['win_rate']:.1%} |",
        f"| Full   | {full['sharpe']:.3f} | {full['max_dd']:.2%} | {full['ann_ret']:.2%} | {full['win_rate']:.1%} |",
        f"",
        f"## Walk-Forward 4-Fold",
        f"| Fold | Period | Sharpe | MaxDD | AnnRet |",
        f"|------|--------|--------|-------|--------|",
    ]

    for fld in wf_folds:
        lines.append(
            f"| {fld['fold']} | {fld['start']}→{fld['end']} | "
            f"{fld['sharpe']:.3f} | {fld['max_dd']:.2%} | {fld['ann_ret']:.2%} |"
        )

    lines += [
        f"",
        f"**WF Summary:** mean_Sh={wfs['mean_sharpe']:.3f}, min_Sh={wfs['min_sharpe']:.3f}, all_positive={wfs['all_positive']}",
        f"",
        f"## Correlation vs K246a Components",
        f"| Component | ρ | |ρ|<0.4? |",
        f"|-----------|---|--------|",
        f"| K198 | {corrs.get('K198', 'n/a')} | {'✓' if isinstance(corrs.get('K198'), float) and abs(corrs['K198']) < 0.4 else '✗'} |",
        f"| K208 | {corrs.get('K208', 'n/a')} | {'✓' if isinstance(corrs.get('K208'), float) and abs(corrs['K208']) < 0.4 else '✗'} |",
        f"| K226 | {corrs.get('K226', 'n/a')} | {'✓' if isinstance(corrs.get('K226'), float) and abs(corrs['K226']) < 0.4 else '✗'} |",
        f"",
        f"## Acceptance Gates ({n_pass}/6 passed)",
        f"| Gate | Status |",
        f"|------|--------|",
    ]
    for k, v in gates.items():
        lines.append(f"| {k} | {'PASS' if v else 'FAIL'} |")

    lines += [
        f"",
        f"## Verdict: {verdict}",
        f"",
    ]

    if "ACCEPT" in verdict:
        lines += [
            f"### K266 K246a Integration Plan",
            f"K265 qualifies for addition to K246a (3-way → 4-way).",
            f"- Mechanism: HL longtail carry capture (orthogonal to K208 CEX-DEX spread)",
            f"- Equal-weight slot: 25% allocation alongside K198/K208/K226",
            f"- Monitor: recheck correlation monthly (HL universe composition changes)",
            f"- Live: use HL perp maker orders, target 8h rebalance at 00:00/08:00/16:00 UTC",
        ]
    else:
        failed = [k for k, v in gates.items() if not v]
        lines += [
            f"### Failure Analysis",
            f"Failed gates: {', '.join(failed)}",
            f"",
            f"### Next Steps",
            f"- Tighten FR window (7d vs 14d) to improve signal decay",
            f"- Apply volatility scaling per symbol",
            f"- Consider only pure longtail (exclude BTC/ETH/BNB/DOGE)",
            f"- Investigate fold-level regime differences",
        ]

    with open(OUT_MD, "w") as f:
        f.write("\n".join(lines) + "\n")
    print(f"[K265] Saved report  → {OUT_MD}")


if __name__ == "__main__":
    main()
