"""
Wave K275 — OKX Perp FR Carry (Cross-Exchange Orthogonality Test)
=================================================================
Apply K265 methodology to OKX perpetual swaps exchange.
OKX settles funding every 8h (3x/day vs HL's 24x/day).
Note: OKX public API only stores ~90 days of history (vs 2yr for HL/Bybit).

Adaptation from K265:
  - Same signal logic (14d rolling mean FR, Q1/Q3 sleeves)
  - OKX universe: 30 symbols, K208 majors excluded
  - OKX FR = 8h settlement rate (multiply by 3 for daily)
  - Walk-forward: 2-fold (data constraint: ~90 days)
  - Correlations vs K265 (HL), K198, K208 on overlap window

Acceptance gates (adapted for data constraint):
  - Data fetched successfully for ≥20 symbols
  - IS Sharpe > 5.0 and OOS Sharpe > 3.0
  - |ρ| < 0.4 with K198/K208/K265 on overlap period
  - Distinct mechanism: OKX universe vs HL long-tail

Runtime target: <5 min (95d data × 30 syms = ~90 API pages).
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
CACHE.mkdir(parents=True, exist_ok=True)

OKX_FR_URL = "https://www.okx.com/api/v5/public/funding-rate-history"

# ── Config ────────────────────────────────────────────────────────────────────
FR_WINDOW_DAYS = 7        # shorter window given 90d history (vs 14d in K265)
QUARTILE       = 0.25
COST_BPS       = 2.0
COST_RATE      = COST_BPS / 1e4
PPY            = 365.0
N_FOLDS        = 2        # 2-fold WF (data constraint: ~90 days)
MIN_DAYS       = 50       # minimum daily bars to include symbol

# K208 majors excluded (same as K265)
K208_EXCLUDE = {"BTC", "ETH", "SOL", "XRP", "SUI", "OP", "APT", "AXS",
                "JTO", "IMX", "SAND", "ADA"}

# OKX perp universe (verified available, K208 majors excluded)
OKX_SYMBOLS = [
    "DOGE", "AVAX", "LINK", "ARB", "NEAR", "DOT", "ATOM",
    "BNB",  "LTC",  "UNI",  "AAVE", "INJ",  "TIA",  "SEI",
    "STRK", "WLD",  "ENA",  "BLUR", "BONK", "PEPE", "WIF",
    "PYTH", "JUP",  "BOME", "ONDO", "CRV",  "SUSHI","MEME",
    "SHIB", "TAO",  "DYDX", "FIL",  "GRT",  "SNX",  "COMP",
]

OUT_JSON    = BASE / "wave_k275_okx_fr.json"
OUT_CURVES  = BASE / "wave_k275_curves.json"
OUT_MD      = BASE / "wave_k275_okx_fr.md"
PARQUET_OUT = CACHE / "okx_fr_daily.parquet"


# ── Helpers ──────────────────────────────────────────────────────────────────
def sharpe(ret: np.ndarray) -> float:
    r = np.asarray(ret, dtype=float)
    r = r[np.isfinite(r)]
    if len(r) < 5 or r.std() == 0:
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


# ── OKX API Fetch ─────────────────────────────────────────────────────────────
def okx_fetch_page(inst_id: str, after: Optional[str] = None) -> List[Dict]:
    """Fetch one page of OKX FR history (newest first, paginate backwards via 'after')."""
    url = f"{OKX_FR_URL}?instId={inst_id}&limit=100"
    if after:
        url += f"&after={after}"
    req = urllib.request.Request(
        url, headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
    )
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = json.loads(resp.read().decode())
                if data.get("code") != "0":
                    return []
                return data.get("data", [])
        except urllib.error.HTTPError as e:
            if e.code == 429:
                wait = 20 * (attempt + 1)
                print(f"    429 {inst_id}, wait {wait}s...")
                time.sleep(wait)
                continue
            print(f"    HTTP {e.code} for {inst_id}")
            return []
        except Exception as ex:
            print(f"    err {inst_id}: {ex}")
            if attempt < 2:
                time.sleep(5)
    return []


def fetch_okx_fr(sym: str, force: bool = False) -> Optional[pd.DataFrame]:
    """Fetch OKX FR with backwards pagination; cache as parquet."""
    inst_id = f"{sym}-USDT-SWAP"
    cache_path = CACHE / f"okx_fr_{sym}.parquet"

    if cache_path.exists() and not force:
        df = pd.read_parquet(cache_path)
        print(f"  {sym}: cached ({len(df)} rows, {len(df)//3:.0f} days)")
        return df

    print(f"  Fetching {sym} [{inst_id}]...", flush=True)
    all_records: List[Dict] = []
    cursor: Optional[str] = None
    pages = 0

    while True:
        records = okx_fetch_page(inst_id, after=cursor)
        if not records:
            break
        all_records.extend(records)
        pages += 1
        cursor = records[-1]["fundingTime"]  # oldest in this page
        if len(records) < 100:
            break  # last page
        time.sleep(0.15)

    if not all_records:
        print(f"    {sym}: no data")
        return None

    df = pd.DataFrame(all_records)
    df["timestamp"] = pd.to_datetime(df["fundingTime"].astype(int), unit="ms", utc=True).dt.tz_localize(None)
    df["okx_fr"]    = df["realizedRate"].astype(float)
    df = (df[["timestamp", "okx_fr"]]
          .drop_duplicates("timestamp")
          .sort_values("timestamp")
          .reset_index(drop=True))

    df.to_parquet(cache_path, index=False)
    print(f"    {sym}: {len(df)} rows, {pages} pages, ~{len(df)//3} days")
    return df


# ── Load + Build Panel ────────────────────────────────────────────────────────
def load_all_okx_fr() -> Tuple[pd.DataFrame, List[str], Dict]:
    """Load OKX FR for all candidate symbols, aggregate to daily, return panel."""
    print(f"\n[K275] Loading {len(OKX_SYMBOLS)} OKX symbols...")
    frames     = []
    kept_syms  = []
    sym_stats  = {}

    for sym in OKX_SYMBOLS:
        try:
            df = fetch_okx_fr(sym)
            if df is None or len(df) == 0:
                continue

            ts = pd.to_datetime(df["timestamp"])
            fr = df["okx_fr"].values

            # Aggregate to daily mean of 8h events (3 events/day on OKX)
            daily = (df.assign(date=ts.dt.normalize())
                       .groupby("date")["okx_fr"]
                       .mean()
                       .rename(sym))

            n_days = len(daily)
            if n_days < MIN_DAYS:
                print(f"    {sym}: skip (only {n_days} days < {MIN_DAYS})")
                continue

            # Per-symbol FR stats
            mean_fr   = float(np.nanmean(fr))
            std_fr    = float(np.nanstd(fr))
            pct_pos   = float(np.mean(fr > 0))
            pct_neg   = float(np.mean(fr < 0))
            abs_mean  = float(np.nanmean(np.abs(fr)))
            # OKX 8h rate: annualize as 3 events/day * 365 days
            ann_carry = abs_mean * 3 * 365 * 100

            sym_stats[sym] = {
                "n_events":        len(df),
                "n_days":          n_days,
                "date_start":      str(ts.min().date()),
                "date_end":        str(ts.max().date()),
                "mean_fr_pct":     round(mean_fr * 100, 6),
                "std_fr_pct":      round(std_fr * 100, 6),
                "abs_mean_fr_pct": round(abs_mean * 100, 6),
                "ann_carry_pct":   round(ann_carry, 2),
                "pct_pos_fr":      round(pct_pos, 3),
                "pct_neg_fr":      round(pct_neg, 3),
                # OKX 8h rate > 0.01% per event = >10.95% APR (higher bar than HL)
                "high_carry":      abs_mean > 0.0001,
            }

            frames.append(daily)
            kept_syms.append(sym)

        except Exception as e:
            print(f"    {sym}: error {e}")
            continue

    panel = pd.concat(frames, axis=1).sort_index() if frames else pd.DataFrame()
    print(f"\n[K275] Panel built: {len(kept_syms)} symbols, {len(panel)} days")
    return panel, kept_syms, sym_stats


# ── Signal & Weights ──────────────────────────────────────────────────────────
def compute_signal(fr_panel: pd.DataFrame) -> pd.DataFrame:
    """7d rolling mean of daily FR, shift +1 to prevent look-ahead."""
    roll = fr_panel.rolling(window=FR_WINDOW_DAYS, min_periods=4).mean()
    return roll.shift(1)


def dollar_neutral_weights(sig_row: pd.Series) -> pd.Series:
    """
    OKX perp carry (same logic as K265):
      FR > 0: longs pay shorts → SHORT receives (short sleeve)
      FR < 0: shorts pay longs → LONG receives (long sleeve)
    High signal rank → SHORT. Low signal rank → LONG.
    """
    valid = sig_row.dropna()
    n_sym = len(valid)
    if n_sym < 4:
        return pd.Series(0.0, index=sig_row.index)

    n_q    = max(1, int(n_sym * QUARTILE))
    ranked = valid.rank(ascending=True)

    longs  = ranked[ranked <= n_q].index
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
    Pure FR carry PnL for OKX.
    OKX settles funding 3 times per day (every 8h).
    Daily FR total = mean_daily_8h_rate * 3 settlements.
    PnL per symbol per day = w * (-daily_total_fr)
    """
    common = fr_panel.index.intersection(weights.index)
    fr_c   = fr_panel.loc[common]
    w_c    = weights.loc[common]

    # Lag weights 1 day (execute at close t-1, settle on day t)
    w_lag = w_c.shift(1).fillna(0.0)

    # OKX 8h rate × 3 settlements = daily total FR
    fr_daily = fr_c * 3.0

    pnl_fr  = (-w_lag * fr_daily).sum(axis=1)
    turn    = (w_c - w_c.shift(1).fillna(0.0)).abs().sum(axis=1)
    cost    = turn * COST_RATE

    pnl_net   = pnl_fr - cost
    pnl_gross = pnl_fr
    return pnl_net, pnl_gross, turn


# ── Walk-Forward 2-Fold ───────────────────────────────────────────────────────
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


# ── Correlations vs K198/K208/K265 ───────────────────────────────────────────
def compute_correlations(pnl_k275: pd.Series) -> Dict:
    corrs = {}

    # K198
    try:
        with open(BASE / "wave_k198_curves.json") as f:
            d = json.load(f)
        dates = pd.to_datetime(d["dates_ml"])
        pnl   = pd.Series(d["pnl_ridge"], index=dates).dropna()
        common = pnl.index.intersection(pnl_k275.index)
        if len(common) > 10:
            corrs["K198"] = round(float(np.corrcoef(
                pnl.loc[common].values, pnl_k275.loc[common].values)[0, 1]), 4)
        else:
            corrs["K198"] = None
    except Exception as e:
        corrs["K198"] = f"error: {e}"

    # K208: aggregate 8h → daily
    try:
        with open(BASE / "wave_k208_curves.json") as f:
            d = json.load(f)
        k208_data = d["K208_filtered"]
        ts   = pd.to_datetime(k208_data["timestamps"])
        cum  = np.array(k208_data["cumulative_pnl"])
        s8   = pd.Series(np.diff(cum, prepend=cum[0]), index=ts)
        pnl  = s8.groupby(s8.index.normalize()).sum()
        pnl.index = pd.to_datetime(pnl.index)
        common = pnl.index.intersection(pnl_k275.index)
        if len(common) > 10:
            corrs["K208"] = round(float(np.corrcoef(
                pnl.loc[common].values, pnl_k275.loc[common].values)[0, 1]), 4)
        else:
            corrs["K208"] = None
    except Exception as e:
        corrs["K208"] = f"error: {e}"

    # K265: HL longtail FR carry (the most important comparison)
    try:
        with open(BASE / "wave_k265_curves.json") as f:
            d = json.load(f)
        dates = pd.to_datetime(d["dates"])
        pnl   = pd.Series(d["pnl"], index=dates).dropna()
        common = pnl.index.intersection(pnl_k275.index)
        if len(common) > 10:
            corrs["K265"] = round(float(np.corrcoef(
                pnl.loc[common].values, pnl_k275.loc[common].values)[0, 1]), 4)
        else:
            corrs["K265"] = None
    except Exception as e:
        corrs["K265"] = f"error: {e}"

    return corrs


# ── Main ──────────────────────────────────────────────────────────────────────
def main() -> None:
    print("=" * 60)
    print("Wave K275 — OKX Perp FR Carry")
    print("=" * 60)

    # 1. Load / Fetch data
    fr_panel, kept_syms, sym_stats = load_all_okx_fr()

    if fr_panel.empty or len(kept_syms) < 10:
        print(f"[K275] FATAL: only {len(kept_syms)} symbols. Abort.")
        _write_abort_json(len(kept_syms))
        return

    print(f"\n[K275] Using {len(kept_syms)} symbols over {len(fr_panel)} days")

    # 2. High-carry symbols
    high_carry_syms = [s for s, st in sym_stats.items() if st["high_carry"]]
    print(f"[K275] High-carry symbols: {high_carry_syms}")

    # 3. Signal & weights
    sig     = compute_signal(fr_panel)
    weights = compute_weights(sig)

    # 4. PnL
    pnl_net, pnl_gross, turnover = compute_pnl(fr_panel, weights)
    pnl_net   = pnl_net.dropna()
    pnl_gross = pnl_gross.dropna()

    n_total = len(pnl_net)
    n_oos   = max(10, int(n_total * 0.30))
    n_is    = n_total - n_oos

    is_ret  = pnl_net.iloc[:n_is].values
    oos_ret = pnl_net.iloc[n_is:].values
    all_ret = pnl_net.values

    is_m    = metrics(is_ret)
    oos_m   = metrics(oos_ret)
    full_m  = metrics(all_ret)
    gross_m = metrics(pnl_gross.values)

    # 5. Walk-forward (2-fold)
    wf_folds   = walk_forward(pnl_net)
    wf_sharpes = [f["sharpe"] for f in wf_folds]
    wf_summary = {
        "mean_sharpe":  round(float(np.mean(wf_sharpes)), 4),
        "min_sharpe":   round(float(np.min(wf_sharpes)),  4),
        "all_positive": bool(all(s > 0 for s in wf_sharpes)),
        "n_folds":      N_FOLDS,
        "note":         "2-fold (data limited to ~90d OKX history)",
    }

    # 6. Correlations
    corrs = compute_correlations(pnl_net)
    print(f"\n[K275] Correlations: {corrs}")

    # 7. Acceptance gates
    def corr_ok(key: str) -> bool:
        v = corrs.get(key)
        return isinstance(v, float) and abs(v) < 0.4

    gates = {
        "G1_data_sufficient":     len(kept_syms) >= 20,
        "G2_IS_Sharpe_gt_5":      is_m["sharpe"] > 5.0,
        "G3_OOS_Sharpe_gt_3":     oos_m["sharpe"] > 3.0,
        "G4_WF_all_folds_pos":    wf_summary["all_positive"],
        "G5_rho_K198_lt_0.4":     corr_ok("K198"),
        "G6_rho_K208_lt_0.4":     corr_ok("K208"),
        "G7_rho_K265_lt_0.4":     corr_ok("K265"),
        "G8_OOS_MaxDD_gt_neg50":  oos_m["max_dd"] > -0.50,
    }
    n_pass  = sum(1 for v in gates.values() if v is True)
    n_gates = len(gates)

    # Core gates: G1-G4 must pass; G5-G7 correlation check
    core_pass = all(gates[k] for k in ["G1_data_sufficient","G2_IS_Sharpe_gt_5",
                                        "G3_OOS_Sharpe_gt_3","G4_WF_all_folds_pos"])
    corr_pass = all(gates[k] for k in ["G5_rho_K198_lt_0.4","G6_rho_K208_lt_0.4",
                                        "G7_rho_K265_lt_0.4"])

    if core_pass and corr_pass:
        verdict = "ACCEPT — K276 K272a integration candidate"
        verdict_short = "ACCEPT"
    elif core_pass and not corr_pass:
        verdict = "CONDITIONAL — performance OK but correlated with existing strategy"
        verdict_short = "CONDITIONAL"
    else:
        failed = [k for k, v in gates.items() if not v]
        verdict = f"REJECT — fails gates: {', '.join(failed)}"
        verdict_short = "REJECT"

    # 8. Print summary
    print(f"\n{'─'*55}")
    print(f"  Symbols: {len(kept_syms)}, Days: {n_total}")
    print(f"  IS   Sh={is_m['sharpe']:.3f}  MDD={is_m['max_dd']:.2%}  AnnRet={is_m['ann_ret']:.2%}")
    print(f"  OOS  Sh={oos_m['sharpe']:.3f}  MDD={oos_m['max_dd']:.2%}  AnnRet={oos_m['ann_ret']:.2%}")
    print(f"  Full Sh={full_m['sharpe']:.3f}  MDD={full_m['max_dd']:.2%}  AnnRet={full_m['ann_ret']:.2%}")
    print(f"  WF   mean_Sh={wf_summary['mean_sharpe']:.3f}  min_Sh={wf_summary['min_sharpe']:.3f}")
    print(f"  Corr K198={corrs.get('K198','n/a')} K208={corrs.get('K208','n/a')} K265={corrs.get('K265','n/a')}")
    print(f"  Gates {n_pass}/{n_gates}  →  {verdict_short}")

    # 9. Save parquet
    fr_panel.to_parquet(PARQUET_OUT)
    print(f"\n[K275] Saved FR panel → {PARQUET_OUT}")

    # 10. Save curves JSON
    curves = {
        "wave":      "K275",
        "dates":     [str(d.date()) for d in pnl_net.index],
        "equity":    [round(float(v), 6) for v in np.cumprod(1 + pnl_net.values)],
        "pnl":       [round(float(v), 8) for v in pnl_net.values],
        "gross_pnl": [round(float(v), 8) for v in pnl_gross.values],
        "n_symbols": len(kept_syms),
        "exchange":  "OKX",
    }
    with open(OUT_CURVES, "w") as f:
        json.dump(curves, f, indent=2)

    # 11. Build fold list
    fold_list = []
    for fld in wf_folds:
        fold_list.append({
            "fold":        fld["fold"],
            "start":       fld["start"],
            "end":         fld["end"],
            "sharpe":      round(fld["sharpe"],     4),
            "max_dd":      round(fld["max_dd"],     6),
            "ann_ret":     round(fld["ann_ret"],    4),
            "ann_vol":     round(fld["ann_vol"],    4),
            "win_rate":    round(fld["win_rate"],   4),
            "total_return":round(fld["total_return"], 6),
            "n_days":      fld["n_days"],
        })

    # 12. Save main JSON
    avg_turn = float(turnover.mean())
    output = {
        "wave":     "K275",
        "strategy": "OKX_Perp_FR_Carry",
        "exchange": "OKX",
        "as_of":    pd.Timestamp.utcnow().isoformat(),
        "runtime_s": round(time.time() - START_TIME, 1),
        "data_note": "OKX public API stores ~90 days of FR history only",
        "config": {
            "symbols_final":       kept_syms,
            "n_symbols":           len(kept_syms),
            "k208_excluded":       sorted(K208_EXCLUDE),
            "high_carry_symbols":  high_carry_syms,
            "fr_window_days":      FR_WINDOW_DAYS,
            "quartile":            QUARTILE,
            "cost_bps_per_side":   COST_BPS,
            "settlement_per_day":  3,
            "rebalance":           "daily",
        },
        "per_symbol_stats": sym_stats,
        "is_metrics":    {k: round(v, 6) if isinstance(v, float) else v
                          for k, v in is_m.items()},
        "oos_metrics":   {k: round(v, 6) if isinstance(v, float) else v
                          for k, v in oos_m.items()},
        "full_metrics":  {k: round(v, 6) if isinstance(v, float) else v
                          for k, v in full_m.items()},
        "gross_metrics": {k: round(v, 6) if isinstance(v, float) else v
                          for k, v in gross_m.items()},
        "walk_forward_folds": fold_list,
        "wf_summary":         wf_summary,
        "turnover": {
            "avg_daily":            round(avg_turn, 6),
            "implied_cost_pct_day": round(avg_turn * COST_RATE, 8),
        },
        "correlations": corrs,
        "gates":        gates,
        "n_gates_passed": n_pass,
        "n_gates_total":  n_gates,
        "verdict":        verdict,
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
    print(f"[K275] Saved metrics → {OUT_JSON}")
    print(f"[K275] Saved curves  → {OUT_CURVES}")
    print(f"[K275] Runtime: {time.time() - START_TIME:.1f}s")

    write_report(output, sym_stats, wf_folds, corrs, gates, n_pass, n_gates,
                 verdict_short, verdict)


def _write_abort_json(n_syms: int) -> None:
    output = {
        "wave": "K275",
        "strategy": "OKX_Perp_FR_Carry",
        "verdict": "ABORT — insufficient symbols",
        "n_symbols": n_syms,
        "data_note": "OKX public API stores ~90 days of FR history only",
        "runtime_s": round(time.time() - START_TIME, 1),
    }
    with open(OUT_JSON, "w") as f:
        json.dump(output, f, indent=2)
    for f_path in [OUT_CURVES]:
        with open(f_path, "w") as f:
            json.dump({"wave": "K275", "dates": [], "equity": [], "pnl": []}, f)


def write_report(output, sym_stats, wf_folds, corrs, gates,
                 n_pass, n_gates, verdict_short, verdict) -> None:
    oos  = output["oos_metrics"]
    is_  = output["is_metrics"]
    full = output["full_metrics"]
    wfs  = output["wf_summary"]
    cfg  = output["config"]

    hc_syms = sorted(sym_stats.items(), key=lambda x: x[1]["ann_carry_pct"], reverse=True)

    lines = [
        f"# Wave K275 — OKX Perp FR Carry",
        f"",
        f"**Date:** {output['as_of'][:10]}  |  **Runtime:** {output['runtime_s']:.0f}s  |  **Exchange:** OKX",
        f"",
        f"**Data Note:** OKX public API stores ~90 days of FR history (vs 2yr for HL/Bybit).",
        f"Gates adapted: 2-fold WF, IS Sh>5, OOS Sh>3.",
        f"",
        f"## Objective",
        f"Apply K265 (HL longtail FR carry) methodology to OKX perps.",
        f"Test orthogonality vs K265/K198/K208. OKX settles funding 3x/day (8h intervals).",
        f"",
        f"## Universe ({cfg['n_symbols']} symbols)",
        f"**K208 Excluded:** {', '.join(cfg['k208_excluded'])}",
        f"**Included:** {', '.join(cfg['symbols_final'])}",
        f"",
        f"## Per-Symbol FR Characteristics (top 20 by annual carry)",
        f"| Symbol | Mean FR%/8h | Std | Ann Carry% | % pos |",
        f"|--------|------------|-----|-----------|-------|",
    ]

    for sym, st in hc_syms[:20]:
        lines.append(
            f"| {sym:8s} | {st['mean_fr_pct']:+.5f} | {st['std_fr_pct']:.5f} "
            f"| {st['ann_carry_pct']:.1f}% | {st['pct_pos_fr']:.0%} |"
        )

    lines += [
        f"",
        f"## Strategy Performance",
        f"| Period | Sharpe | MaxDD | AnnRet | WinRate | Days |",
        f"|--------|--------|-------|--------|---------|------|",
        f"| IS     | {is_['sharpe']:.3f} | {is_['max_dd']:.2%} | {is_['ann_ret']:.2%} | {is_['win_rate']:.1%} | {is_['n_days']} |",
        f"| OOS    | {oos['sharpe']:.3f} | {oos['max_dd']:.2%} | {oos['ann_ret']:.2%} | {oos['win_rate']:.1%} | {oos['n_days']} |",
        f"| Full   | {full['sharpe']:.3f} | {full['max_dd']:.2%} | {full['ann_ret']:.2%} | {full['win_rate']:.1%} | {full['n_days']} |",
        f"",
        f"## Walk-Forward {wfs['n_folds']}-Fold",
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
        f"**WF Summary:** mean_Sh={wfs['mean_sharpe']:.3f}, "
        f"min_Sh={wfs['min_sharpe']:.3f}, all_positive={wfs['all_positive']}",
        f"",
        f"## 4x4 Correlation Matrix (K275, K198, K208, K265 — overlap window)",
        f"| | K275 | K198 | K208 | K265 |",
        f"|---|---|---|---|---|",
        f"| K275 | 1.00 | {corrs.get('K198','n/a')} | {corrs.get('K208','n/a')} | {corrs.get('K265','n/a')} |",
        f"| K198 | {corrs.get('K198','n/a')} | 1.00 | 0.06 | 0.004 |",
        f"| K208 | {corrs.get('K208','n/a')} | 0.06 | 1.00 | 0.086 |",
        f"| K265 | {corrs.get('K265','n/a')} | 0.004 | 0.086 | 1.00 |",
        f"",
        f"## Acceptance Gates ({n_pass}/{n_gates} passed)",
        f"| Gate | Status |",
        f"|------|--------|",
    ]
    for k, v in gates.items():
        lines.append(f"| {k} | {'PASS' if v else 'FAIL'} |")

    lines += [
        f"",
        f"## Verdict: {verdict_short}",
        f"",
        f"{verdict}",
        f"",
    ]

    if verdict_short == "ACCEPT":
        lines += [
            f"### K276 K272a Integration Plan",
            f"K275 qualifies for addition to K272a (3-way → 4-way).",
            f"- Mechanism: OKX perp carry (orthogonal to HL longtail K265)",
            f"- Settlement: 3x/day (00:00/08:00/16:00 UTC)",
            f"- Equal-weight slot: 25% alongside K198/K208/K265",
            f"- Risk: OKX has shorter data history — monitor live for 30d before full allocation",
            f"- Live: OKX maker orders, 2bp target cost, rebalance at each 8h settlement",
        ]
    else:
        failed = [k for k, v in gates.items() if not v]
        lines += [
            f"### Failure / Constraint Analysis",
            f"Failed: {', '.join(failed)}",
            f"",
            f"Key constraint: OKX public API limited to ~90 days history.",
            f"Structural carry signal is present but walk-forward is underpowered.",
            f"",
            f"### Pivot Options for K276",
            f"1. Use OKX premium data API (authenticated) for 2yr history",
            f"2. Harvest OKX FR alongside HL FR in K265 as combined exchange basket",
            f"3. Continue with K272a 3-way (K198+K208+K265) — already production-quality",
        ]

    with open(OUT_MD, "w") as f:
        f.write("\n".join(lines) + "\n")
    print(f"[K275] Saved report → {OUT_MD}")


if __name__ == "__main__":
    main()
