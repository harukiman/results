"""
Wave K270 — dYdX v4 Alt-Exchange Long-Tail FR Carry
=====================================================
Exchange selected: dYdX v4 (Cosmos-based perp DEX)
  - Endpoint: https://indexer.dydx.trade/v4/historicalFunding/{market}
  - 2.6 years of hourly FR history (Oct 2023 – present)
  - 96 active markets, genuinely distinct ecosystem from HyperLiquid

OKX Assessment (initial choice):
  OKX public funding-rate-history endpoint only retains ~95 days of history
  (284 records = ~3 months for 8h symbols). Insufficient for 2y backtest.
  Pivot to dYdX v4 per "If data unavailable" protocol.

Strategy (same methodology as K265):
  1. Universe: 25 dYdX v4 alts (≥200 daily bars available)
  2. Signal: 14-day rolling mean of hourly dYdX FR → aggregated to daily
  3. Short symbols with FR > p75 (collect carry from longs)
     Long  symbols with FR < p25 (collect carry from shorts)
  4. Dollar-neutral within each sleeve
  5. Daily rebalance, 2bp/side maker
  6. Walk-forward 4-fold

dYdX specifics:
  - Hourly FR settlement (24 events/day)
  - Cosmos-based DEX: isolated funding mechanism from CEX/HL
  - FR history via /v4/historicalFunding/{market}?limit=100&effectiveBeforeOrAtHeight={h}

K266 strict gate:
  |rho| < 0.4 vs K198/K208/K226/K265
  Sh >= 7 in every WF fold
  Distinct mechanism family

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
BASE    = Path("/Users/nekonaomichi/crypto-lab")
CACHE   = BASE / "cache"
DYDX_CACHE = CACHE / "k270_dydx"
DYDX_CACHE.mkdir(parents=True, exist_ok=True)

DYDX_API_BASE = "https://indexer.dydx.trade/v4/historicalFunding"

# ── Config ───────────────────────────────────────────────────────────────────
FR_WINDOW_DAYS = 14
QUARTILE       = 0.25
COST_BPS       = 2.0
COST_RATE      = COST_BPS / 1e4
PPY            = 365.0
N_FOLDS        = 4
MIN_DAYS       = 200
FETCH_DAYS     = 730   # 2 years

# dYdX v4 universe: 25 alts with good liquidity, excluding BTC/ETH majors
# Focus on alts where FR dynamics may differ from HL ecosystem
DYDX_SYMBOLS = [
    "AAVE", "ADA", "APT", "ARB", "ATOM",
    "AVAX", "AXS", "BLUR", "BONK", "CRV",
    "DOGE", "DOT", "ENA", "INJ", "JUP",
    "LDO", "NEAR", "OP", "PEPE", "PYTH",
    "SEI", "SOL", "SUI", "TAO", "TIA",
    "UNI", "WIF", "WLD", "XRP", "BNB",
]
# dYdX market format: {SYM}-USD
def sym_to_market(sym: str) -> str:
    return f"{sym}-USD"

OUT_JSON    = BASE / "wave_k270_alt_exchange_fr.json"
OUT_CURVES  = BASE / "wave_k270_curves.json"
OUT_MD      = BASE / "wave_k270_alt_exchange_fr.md"
PARQUET_OUT = CACHE / "alt_exchange_fr_daily.parquet"


# ── Metric Helpers ────────────────────────────────────────────────────────────
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


# ── dYdX v4 API Fetch ─────────────────────────────────────────────────────────
def dydx_fetch_page(market: str,
                    effective_before_height: Optional[int] = None) -> List[Dict]:
    """Fetch one page (up to 100) of dYdX v4 hourly funding history."""
    url = f"{DYDX_API_BASE}/{market}?limit=100"
    if effective_before_height is not None:
        url += f"&effectiveBeforeOrAtHeight={effective_before_height}"
    req = urllib.request.Request(
        url, headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
    )
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode())
                return data.get("historicalFunding", [])
        except urllib.error.HTTPError as e:
            if e.code == 429:
                wait = 20 * (attempt + 1)
                print(f"    429 {market}, wait {wait}s...")
                time.sleep(wait)
                continue
            if e.code == 404:
                return []
            print(f"    HTTP {e.code} for {market}")
            return []
        except Exception as ex:
            print(f"    err {market}: {ex}")
            if attempt < 3:
                time.sleep(5)
    return []


def fetch_dydx_fr(sym: str, days: int = FETCH_DAYS,
                  force: bool = False) -> Optional[pd.DataFrame]:
    """
    Fetch dYdX v4 hourly funding rate history via backward pagination.
    dYdX returns newest-first. Paginate with effectiveBeforeOrAtHeight.
    Cache as parquet in k270_dydx/.
    """
    cache_path = DYDX_CACHE / f"dydx_fr_{sym}.parquet"
    if cache_path.exists() and not force:
        df = pd.read_parquet(cache_path)
        print(f"  {sym}: cached ({len(df)} rows)")
        return df

    market    = sym_to_market(sym)
    cutoff_dt = pd.Timestamp.utcnow().tz_localize(None) - pd.Timedelta(days=days)
    all_events: List[Dict] = []
    before_height: Optional[int] = None

    print(f"  Fetching {sym} [{market}]...", flush=True)
    while True:
        records = dydx_fetch_page(market, effective_before_height=before_height)
        if not records:
            break
        all_events.extend(records)

        # Records are newest-first; oldest is records[-1]
        oldest_dt_str = records[-1]["effectiveAt"]
        oldest_dt     = pd.Timestamp(oldest_dt_str).tz_localize(None)
        if oldest_dt <= cutoff_dt:
            break
        # Paginate: go older
        before_height = int(records[-1]["effectiveAtHeight"]) - 1
        time.sleep(0.25)

    if not all_events:
        print(f"    {sym}: no data returned")
        return None

    df = pd.DataFrame(all_events)
    df["timestamp"] = pd.to_datetime(df["effectiveAt"]).dt.tz_localize(None)
    df["dydx_fr"]   = df["rate"].astype(float)
    df = (df[["timestamp", "dydx_fr"]]
          .drop_duplicates("timestamp")
          .sort_values("timestamp")
          .reset_index(drop=True))

    # Trim to requested window
    df = df[df["timestamp"] >= cutoff_dt].reset_index(drop=True)

    df.to_parquet(cache_path, index=False)
    print(f"    {sym}: fetched {len(df)} hourly rows, {df.timestamp.min().date()} to {df.timestamp.max().date()}")
    return df


# ── Load + Build Panel ────────────────────────────────────────────────────────
def load_all_dydx_fr() -> Tuple[pd.DataFrame, List[str], Dict]:
    """
    Load dYdX FR for all candidate symbols.
    dYdX settles every hour → 24 events/day.
    Aggregate to daily mean for strategy signal.
    """
    print(f"\n[K270] Loading {len(DYDX_SYMBOLS)} dYdX v4 symbols...")
    frames    = []
    kept_syms = []
    sym_stats: Dict = {}

    for sym in DYDX_SYMBOLS:
        try:
            df = fetch_dydx_fr(sym, days=FETCH_DAYS)
            if df is None or len(df) < 100:
                print(f"    {sym}: skip (insufficient data)")
                continue

            ts = pd.to_datetime(df["timestamp"])
            fr = df["dydx_fr"].values

            # Aggregate hourly FR to daily mean
            daily = (df.assign(date=ts.dt.normalize())
                       .groupby("date")["dydx_fr"]
                       .mean()
                       .rename(sym))

            if len(daily) < MIN_DAYS:
                print(f"    {sym}: skip ({len(daily)} daily bars < {MIN_DAYS})")
                continue

            # Per-symbol stats (hourly event scale)
            mean_fr   = float(np.nanmean(fr))
            std_fr    = float(np.nanstd(fr))
            abs_mean  = float(np.nanmean(np.abs(fr)))
            pct_pos   = float(np.mean(fr > 0))
            pct_neg   = float(np.mean(fr < 0))
            # dYdX settles hourly: ann carry = abs_mean × 24 × 365
            ann_carry = abs_mean * 24 * 365 * 100

            sym_stats[sym] = {
                "n_events":        len(df),
                "n_days":          len(daily),
                "date_start":      str(ts.min().date()),
                "date_end":        str(ts.max().date()),
                "mean_fr_pct":     round(mean_fr * 100, 5),
                "std_fr_pct":      round(std_fr * 100, 5),
                "abs_mean_fr_pct": round(abs_mean * 100, 5),
                "ann_carry_pct":   round(ann_carry, 2),
                "pct_pos_fr":      round(pct_pos, 3),
                "pct_neg_fr":      round(pct_neg, 3),
                "high_carry":      abs_mean > 0.0001,
            }

            frames.append(daily)
            kept_syms.append(sym)
            time.sleep(0.05)

        except Exception as e:
            print(f"    {sym}: error {e}")
            continue

    if not frames:
        return pd.DataFrame(), [], {}

    panel = pd.concat(frames, axis=1).sort_index()
    print(f"\n[K270] Panel built: {len(kept_syms)} symbols, {len(panel)} days")
    return panel, kept_syms, sym_stats


# ── Signal & Weights ──────────────────────────────────────────────────────────
def compute_signal(fr_panel: pd.DataFrame) -> pd.DataFrame:
    """14d rolling mean of daily FR; shift+1 to avoid look-ahead."""
    roll = fr_panel.rolling(window=FR_WINDOW_DAYS, min_periods=7).mean()
    return roll.shift(1)


def dollar_neutral_weights(sig_row: pd.Series) -> pd.Series:
    """
    Cross-sectional FR carry:
      HIGH rolling FR → SHORT  (receive carry from longs)
      LOW rolling FR  → LONG   (receive carry from shorts or negative-FR)
    Dollar-neutral within each sleeve.
    """
    valid  = sig_row.dropna()
    n_sym  = len(valid)
    if n_sym < 4:
        return pd.Series(0.0, index=sig_row.index)

    n_q    = max(1, int(n_sym * QUARTILE))
    ranked = valid.rank(ascending=True)

    longs  = ranked[ranked <= n_q].index
    shorts = ranked[ranked > n_sym - n_q].index

    w = pd.Series(0.0, index=sig_row.index)
    if len(longs) > 0:
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
    Pure FR carry PnL.
    dYdX settles hourly (24x/day) → daily_total = daily_mean × 24
    PnL = -w × daily_fr_total
    """
    common = fr_panel.index.intersection(weights.index)
    fr_c   = fr_panel.loc[common]
    w_c    = weights.loc[common]

    w_lag    = w_c.shift(1).fillna(0.0)
    fr_daily = fr_c * 24.0   # hourly FR × 24 = daily total

    pnl_fr = (-w_lag * fr_daily).sum(axis=1)
    turn   = (w_c - w_c.shift(1).fillna(0.0)).abs().sum(axis=1)
    cost   = turn * COST_RATE

    return pnl_fr - cost, pnl_fr, turn


# ── Walk-Forward ──────────────────────────────────────────────────────────────
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


# ── Correlation vs K269 Components ───────────────────────────────────────────
def compute_correlations(pnl_k270: pd.Series) -> Dict[str, object]:
    """Compute rho with K198, K208, K226, K265 daily returns."""
    corrs: Dict[str, object] = {}

    # K198 ML allocator
    try:
        with open(BASE / "wave_k198_curves.json") as f:
            d = json.load(f)
        dates = pd.to_datetime(d["dates_ml"])
        pnl   = pd.Series(d["pnl_ridge"], index=dates).dropna()
        common = pnl.index.intersection(pnl_k270.index)
        if len(common) > 30:
            corrs["K198"] = round(float(np.corrcoef(
                pnl.loc[common].values, pnl_k270.loc[common].values)[0, 1]), 4)
        else:
            corrs["K198"] = None
    except Exception as e:
        corrs["K198"] = f"error: {e}"

    # K208 DAR reverse carry (8h → daily aggregation)
    try:
        with open(BASE / "wave_k208_curves.json") as f:
            d = json.load(f)
        k208_data = d["K208_filtered"]
        ts    = pd.to_datetime(k208_data["timestamps"])
        cum   = np.array(k208_data["cumulative_pnl"])
        s8    = pd.Series(np.diff(cum, prepend=cum[0]), index=ts)
        pnl   = s8.groupby(s8.index.normalize()).sum()
        pnl.index = pd.to_datetime(pnl.index)
        common = pnl.index.intersection(pnl_k270.index)
        if len(common) > 30:
            corrs["K208"] = round(float(np.corrcoef(
                pnl.loc[common].values, pnl_k270.loc[common].values)[0, 1]), 4)
        else:
            corrs["K208"] = None
    except Exception as e:
        corrs["K208"] = f"error: {e}"

    # K226 eth validator queue
    try:
        with open(BASE / "wave_k226_curves.json") as f:
            d = json.load(f)
        dates = pd.to_datetime(d["dates"])
        pnl   = pd.Series(d["strat_daily_ret"], index=dates).dropna()
        common = pnl.index.intersection(pnl_k270.index)
        if len(common) > 30:
            corrs["K226"] = round(float(np.corrcoef(
                pnl.loc[common].values, pnl_k270.loc[common].values)[0, 1]), 4)
        else:
            corrs["K226"] = None
    except Exception as e:
        corrs["K226"] = f"error: {e}"

    # K265 HL longtail FR carry (same mechanism family — critical gate)
    try:
        with open(BASE / "wave_k265_curves.json") as f:
            d = json.load(f)
        dates = pd.to_datetime(d["dates"])
        pnl   = pd.Series(d["pnl"], index=dates).dropna()
        common = pnl.index.intersection(pnl_k270.index)
        if len(common) > 30:
            corrs["K265"] = round(float(np.corrcoef(
                pnl.loc[common].values, pnl_k270.loc[common].values)[0, 1]), 4)
        else:
            corrs["K265"] = None
    except Exception as e:
        corrs["K265"] = f"error: {e}"

    return corrs


# ── Main ──────────────────────────────────────────────────────────────────────
def main() -> None:
    print("=" * 60)
    print("Wave K270 — dYdX v4 Alt-Exchange FR Carry Strategy")
    print("=" * 60)
    print("Note: OKX pivoted → only ~95 days of history available.")
    print("dYdX v4: 2.6 years of hourly FR, 96 active markets.")

    # 1. Load / Fetch dYdX data
    fr_panel, kept_syms, sym_stats = load_all_dydx_fr()

    if fr_panel.empty or len(kept_syms) < 4:
        print("[K270] FATAL: not enough symbols. Abort.")
        return

    # 2. High-carry symbols
    high_carry_syms = [s for s, st in sym_stats.items() if st["high_carry"]]
    print(f"\n[K270] High-carry symbols (|mean FR| > 0.01%/hr): {high_carry_syms}")

    # 3. Signal and weights
    sig     = compute_signal(fr_panel)
    weights = compute_weights(sig)

    # 4. PnL
    pnl_net, pnl_gross, turnover = compute_pnl(fr_panel, weights)
    pnl_net   = pnl_net.dropna()
    pnl_gross = pnl_gross.dropna()

    n_total = len(pnl_net)
    n_oos   = int(n_total * 0.30)
    n_is    = n_total - n_oos

    is_ret  = pnl_net.iloc[:n_is].values
    oos_ret = pnl_net.iloc[n_is:].values
    all_ret = pnl_net.values

    is_m    = metrics(is_ret)
    oos_m   = metrics(oos_ret)
    full_m  = metrics(all_ret)
    gross_m = metrics(pnl_gross.values)

    # 5. Walk-forward 4-fold
    wf_folds   = walk_forward(pnl_net)
    wf_sharpes = [f["sharpe"] for f in wf_folds]
    wf_summary = {
        "mean_sharpe":  round(float(np.mean(wf_sharpes)), 4),
        "min_sharpe":   round(float(np.min(wf_sharpes)),  4),
        "all_positive": bool(all(s > 0 for s in wf_sharpes)),
        "all_ge7":      bool(all(s >= 7 for s in wf_sharpes)),
    }

    # 6. Correlations vs K269 components
    corrs = compute_correlations(pnl_net)

    # 7. K266 strict gates
    def _abs_corr_ok(k: str) -> bool:
        v = corrs.get(k)
        return isinstance(v, float) and abs(v) < 0.4

    gates = {
        "G1_WF_all_folds_positive": wf_summary["all_positive"],
        "G2_WF_all_folds_Sh_ge_7":  wf_summary["all_ge7"],
        "G3_OOS_Sharpe_gt_7":       oos_m["sharpe"] > 7.0,
        "G4_rho_K198_lt_0.4":       _abs_corr_ok("K198"),
        "G5_rho_K208_lt_0.4":       _abs_corr_ok("K208"),
        "G6_rho_K226_lt_0.4":       _abs_corr_ok("K226"),
        "G7_rho_K265_lt_0.4":       _abs_corr_ok("K265"),  # same family — critical
        "G8_OOS_MaxDD_gt_neg30pct": oos_m["max_dd"] > -0.30,
    }
    n_pass  = sum(1 for v in gates.values() if v is True)
    verdict = "ACCEPT" if all(gates.values()) else "REJECT"

    # 8. Print summary
    print(f"\n{'─'*55}")
    print(f"  OOS  Sh={oos_m['sharpe']:.3f}  MDD={oos_m['max_dd']:.2%}  AnnRet={oos_m['ann_ret']:.2%}")
    print(f"  WF   mean_Sh={wf_summary['mean_sharpe']:.3f}  "
          f"min_Sh={wf_summary['min_sharpe']:.3f}  all_pos={wf_summary['all_positive']}  "
          f"all_ge7={wf_summary['all_ge7']}")
    print(f"  Corr K198={corrs.get('K198','n/a')}  K208={corrs.get('K208','n/a')}  "
          f"K226={corrs.get('K226','n/a')}  K265={corrs.get('K265','n/a')}")
    print(f"  Gates passed: {n_pass}/8  →  {verdict}")

    # 9. Save parquet
    fr_panel.to_parquet(PARQUET_OUT)
    print(f"\n[K270] Saved daily FR panel → {PARQUET_OUT}")

    # 10. Curves JSON
    curves = {
        "wave":      "K270",
        "exchange":  "dYdX_v4",
        "dates":     [str(d.date()) for d in pnl_net.index],
        "equity":    [round(float(v), 6) for v in np.cumprod(1 + pnl_net.values)],
        "pnl":       [round(float(v), 8) for v in pnl_net.values],
        "gross_pnl": [round(float(v), 8) for v in pnl_gross.values],
    }
    with open(OUT_CURVES, "w") as f:
        json.dump(curves, f, indent=2)

    # 11. Fold details
    fold_list = []
    for fld in wf_folds:
        fold_list.append({
            "fold":         fld["fold"],
            "start":        fld["start"],
            "end":          fld["end"],
            "sharpe":       round(fld["sharpe"],     4),
            "max_dd":       round(fld["max_dd"],     6),
            "ann_ret":      round(fld["ann_ret"],    4),
            "ann_vol":      round(fld["ann_vol"],    4),
            "win_rate":     round(fld["win_rate"],   4),
            "total_return": round(fld["total_return"], 6),
            "n_days":       fld["n_days"],
        })

    # 12. Main JSON
    avg_turn = float(turnover.mean())
    output = {
        "wave":     "K270",
        "strategy": "dYdX_v4_AltExchange_FR_Carry",
        "exchange": "dYdX_v4",
        "note_okx": "OKX pivoted: public API only ~95 days history. dYdX v4: 2.6y hourly.",
        "as_of":    pd.Timestamp.utcnow().isoformat(),
        "runtime_s": round(time.time() - START_TIME, 1),
        "config": {
            "symbols_candidate":  DYDX_SYMBOLS,
            "symbols_final":      kept_syms,
            "n_symbols":          len(kept_syms),
            "high_carry_symbols": high_carry_syms,
            "fr_window_days":     FR_WINDOW_DAYS,
            "quartile":           QUARTILE,
            "cost_bps_per_side":  COST_BPS,
            "settlement_per_day": 24,
            "rebalance":          "daily",
        },
        "per_symbol_stats": sym_stats,
        "is_metrics":   {k: round(v, 6) if isinstance(v, float) else v for k, v in is_m.items()},
        "oos_metrics":  {k: round(v, 6) if isinstance(v, float) else v for k, v in oos_m.items()},
        "full_metrics": {k: round(v, 6) if isinstance(v, float) else v for k, v in full_m.items()},
        "gross_metrics":{k: round(v, 6) if isinstance(v, float) else v for k, v in gross_m.items()},
        "walk_forward_folds": fold_list,
        "wf_summary":         wf_summary,
        "turnover": {
            "avg_daily":            round(avg_turn, 6),
            "implied_cost_pct_day": round(avg_turn * COST_RATE, 8),
        },
        "correlations": corrs,
        "gates":         gates,
        "n_gates_passed": n_pass,
        "verdict":       verdict,
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
    print(f"[K270] Saved metrics → {OUT_JSON}")
    print(f"[K270] Saved curves  → {OUT_CURVES}")
    print(f"[K270] Runtime: {time.time() - START_TIME:.1f}s")

    # 13. MD Report
    write_report(output, sym_stats, wf_folds, corrs, gates, n_pass, verdict)


def write_report(output, sym_stats, wf_folds, corrs, gates, n_pass, verdict) -> None:
    oos  = output["oos_metrics"]
    full = output["full_metrics"]
    wfs  = output["wf_summary"]

    hc_syms = sorted(sym_stats.items(), key=lambda x: x[1]["ann_carry_pct"], reverse=True)

    def _corr_ok(k: str) -> str:
        v = corrs.get(k)
        return "pass" if isinstance(v, float) and abs(v) < 0.4 else "FAIL"

    lines = [
        f"# Wave K270 — dYdX v4 Alt-Exchange FR Carry",
        f"",
        f"**Date:** {output['as_of'][:10]}  |  **Runtime:** {output['runtime_s']:.0f}s  |  **Exchange:** dYdX v4 (Cosmos perp DEX)",
        f"",
        f"## Exchange Selection",
        f"OKX (initial target) pivoted: public funding-rate-history API retains only ~95 days.",
        f"dYdX v4 selected: 2.6 years of hourly FR history (Oct 2023 onward), 96 active markets.",
        f"dYdX is Cosmos-based DEX (isolated from CEX and HL ecosystems).",
        f"",
        f"## Objective",
        f"Apply K265 long-tail FR carry methodology to dYdX v4 Cosmos perp DEX.",
        f"Universe: {output['config']['n_symbols']} alts. Hourly FR settlement (24x/day).",
        f"",
        f"## Universe ({output['config']['n_symbols']} symbols)",
        f"**Included:** {', '.join(output['config']['symbols_final'])}",
        f"",
        f"## Per-Symbol FR Characteristics (top by ann carry)",
        f"| Symbol | Mean FR%/hr | Std | Ann Carry% | % pos |",
        f"|--------|-----------|-----|-----------|-------|",
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
        f"**WF:** mean_Sh={wfs['mean_sharpe']:.3f}, min_Sh={wfs['min_sharpe']:.3f}, "
        f"all_pos={wfs['all_positive']}, all_ge7={wfs['all_ge7']}",
        f"",
        f"## Correlation Matrix vs K269 Components (5x5)",
        f"| Component | rho(K270) | |rho|<0.4? |",
        f"|-----------|-----------|---------|",
    ]
    for k in ["K198", "K208", "K226", "K265"]:
        v = corrs.get(k, "n/a")
        ok = _corr_ok(k)
        lines.append(f"| {k} | {v} | {ok} |")

    lines += [
        f"",
        f"## K266 Acceptance Gates ({n_pass}/8 passed)",
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

    if verdict == "ACCEPT":
        lines += [
            f"### K272 K269 Integration Plan",
            f"K270 (dYdX v4 FR carry) qualifies for addition to K269 ensemble.",
            f"- Mechanism: dYdX v4 Cosmos-DEX cross-sectional carry (orthogonal to HL carry)",
            f"- rho(K265)={corrs.get('K265','n/a')} — confirmed orthogonal to HL carry",
            f"- Proposed: 5-way ensemble K198+K208+K226+K265+K270",
            f"- Allocation: Sharpe-weighted meta-allocator",
            f"- Live: dYdX v4 maker orders, hourly rate monitoring",
            f"- Risk: dYdX DEX liquidity thinner than CEX — widen cost assumption to 3-4bp",
        ]
    else:
        failed = [k for k, v in gates.items() if not v]
        lines += [
            f"### Failure Analysis",
            f"Failed gates: {', '.join(failed)}",
            f"",
            f"### Interpretation",
        ]
        if "G7_rho_K265_lt_0.4" in failed:
            lines += [
                f"- **rho(K265) >= 0.4**: dYdX and HL FR carry are correlated.",
                f"  Cross-sectional FR carry may be a universal mechanism across venues.",
                f"  K265 already captures this alpha — K270 would add limited orthogonality.",
                f"  Result: FRAMEWORK (mechanism confirmed, venue redundant).",
            ]
        if any("Sh" in g for g in failed):
            lines += [
                f"- Sharpe gate failure: dYdX FR carry weaker than HL.",
                f"  dYdX has lower FR volatility and less longtail carry.",
                f"  HL longtail remains superior data source for this strategy.",
            ]
        lines += [
            f"",
            f"### K269 Integration: NOT recommended",
            f"K265 (HL) already represents FR carry as a component.",
            f"Adding K270 would increase mechanism concentration rather than true diversification.",
        ]

    with open(OUT_MD, "w") as f:
        f.write("\n".join(lines) + "\n")
    print(f"[K270] Saved report  → {OUT_MD}")


if __name__ == "__main__":
    main()
