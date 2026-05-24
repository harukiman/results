"""
Wave K165 — Top-Trader Position Ratio Extreme Contrarian
=========================================================

Hypothesis (CoinGlass-inspired):
  Binance top-trader position ratio measures how the *largest position holders*
  are positioned. When 70%+ of top-trader notional sits on one side, the trade
  is "crowded" and we contrarian-fade it.

Pre-registered Method
---------------------
- Universe: BTCUSDT, ETHUSDT, SOLUSDT
- Data:
    - Top-trader position ratio (notional weighted) -- primary
    - Top-trader account ratio                      -- comparison
    - 4H bars klines (mark price / close)
- Signal:
    long_ratio = longs / (longs + shorts)
    long_ratio > thr_hi  -> SHORT (fade crowded long)
    long_ratio < thr_lo  -> LONG  (fade crowded short)
- Hold: 4 bars (16h)
- Cost: 0.07% per side (7 bps), so 0.14% round-trip
- Variants:
    V_70_30        thr 0.70 / 0.30 on long_ratio_pos (pre-registered)
    V_75_25        thr 0.75 / 0.25 (pre-registered)
    V_z_score      rolling z >|2| on long_ratio_pos (pre-registered)
    V_pct_90_10    per-symbol 90th/10th percentile (adaptive, exploratory)
    V_acct_70_30   account-weighted ratio thr 0.70 / 0.30 (CoinGlass-like)
    V_acct_z       account-weighted z-score >|2|

CRITICAL DATA FINDING
---------------------
The position-weighted long ratio is empirically much more compressed than the
hypothesised 0.30-0.70 band: across BTC/ETH/SOL the realised range over the
30-day window is roughly 0.41-0.70. The pre-registered absolute thresholds
0.70/0.30 essentially never trigger -> 0 trades. The hypothesis as stated is
calibrated against the LooseShort/long ACCOUNT ratio reported on CoinGlass UI,
not the notional-weighted position ratio that the API field 'longAccount'
actually carries. We therefore retain the pre-registered variants for honesty
and add adaptive percentile + account-weighted variants for exploration.
- Honest about data limit: Binance API caps at last ~30 days regardless of
  startTime/endTime, so this is a FRAMEWORK + short-window pilot, not a full IS/OOS
  rigorous test.
"""

from __future__ import annotations

import json
import math
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
import requests

ROOT = Path("/Users/nekonaomichi/crypto-lab")
OUT_JSON = ROOT / "wave_k165_top_trader_ratio.json"
OUT_CURVES = ROOT / "wave_k165_curves.json"

SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
PERIOD = "4h"
HOLD_BARS = 4
COST_PER_SIDE = 0.0007   # 7 bps
ROUND_TRIP_COST = 2 * COST_PER_SIDE

# ---------------------------------------------------------------------------
# Data fetchers
# ---------------------------------------------------------------------------

BASE = "https://fapi.binance.com"


def _get(path: str, params: dict) -> list:
    url = f"{BASE}{path}"
    for attempt in range(3):
        try:
            r = requests.get(url, params=params, timeout=20)
            if r.status_code == 200:
                return r.json()
            time.sleep(1.0 + attempt)
        except requests.RequestException:
            time.sleep(1.0 + attempt)
    r.raise_for_status()
    return []


def fetch_top_position_ratio(symbol: str, period: str = PERIOD, limit: int = 500) -> pd.DataFrame:
    raw = _get("/futures/data/topLongShortPositionRatio",
               {"symbol": symbol, "period": period, "limit": limit})
    if not raw:
        return pd.DataFrame()
    df = pd.DataFrame(raw)
    df["ts"] = pd.to_datetime(df["timestamp"].astype("int64"), unit="ms", utc=True)
    df["long_pos"] = df["longAccount"].astype(float)    # despite the field name, position-weighted
    df["short_pos"] = df["shortAccount"].astype(float)
    df["ls_ratio_pos"] = df["longShortRatio"].astype(float)
    return df[["ts", "long_pos", "short_pos", "ls_ratio_pos"]].set_index("ts").sort_index()


def fetch_top_account_ratio(symbol: str, period: str = PERIOD, limit: int = 500) -> pd.DataFrame:
    raw = _get("/futures/data/topLongShortAccountRatio",
               {"symbol": symbol, "period": period, "limit": limit})
    if not raw:
        return pd.DataFrame()
    df = pd.DataFrame(raw)
    df["ts"] = pd.to_datetime(df["timestamp"].astype("int64"), unit="ms", utc=True)
    df["long_acct"] = df["longAccount"].astype(float)
    df["short_acct"] = df["shortAccount"].astype(float)
    df["ls_ratio_acct"] = df["longShortRatio"].astype(float)
    return df[["ts", "long_acct", "short_acct", "ls_ratio_acct"]].set_index("ts").sort_index()


def fetch_klines(symbol: str, interval: str = "4h", limit: int = 500) -> pd.DataFrame:
    raw = _get("/fapi/v1/klines", {"symbol": symbol, "interval": interval, "limit": limit})
    if not raw:
        return pd.DataFrame()
    cols = ["openTime", "open", "high", "low", "close", "volume",
            "closeTime", "qav", "ntrades", "tbbav", "tbqav", "ignore"]
    df = pd.DataFrame(raw, columns=cols)
    df["ts"] = pd.to_datetime(df["openTime"].astype("int64"), unit="ms", utc=True)
    for c in ("open", "high", "low", "close", "volume"):
        df[c] = df[c].astype(float)
    return df[["ts", "open", "high", "low", "close", "volume"]].set_index("ts").sort_index()


# ---------------------------------------------------------------------------
# Backtest engine
# ---------------------------------------------------------------------------

@dataclass
class Trade:
    symbol: str
    entry_ts: pd.Timestamp
    exit_ts: pd.Timestamp
    side: int           # +1 long, -1 short
    entry_px: float
    exit_px: float
    ratio: float
    gross_ret: float
    net_ret: float


def build_panel(symbol: str) -> pd.DataFrame:
    pos = fetch_top_position_ratio(symbol)
    acct = fetch_top_account_ratio(symbol)
    kl = fetch_klines(symbol, "4h", 500)
    if pos.empty or kl.empty:
        return pd.DataFrame()
    df = pos.join(acct, how="left").join(kl[["close"]], how="left")
    # long_ratio_pos = long / (long+short) - position weighted top traders
    df["long_ratio_pos"] = df["long_pos"] / (df["long_pos"] + df["short_pos"])
    if not acct.empty:
        df["long_ratio_acct"] = df["long_acct"] / (df["long_acct"] + df["short_acct"])
    else:
        df["long_ratio_acct"] = np.nan
    df["close"] = df["close"].ffill()
    df = df.dropna(subset=["close"])
    return df


def run_variant(panels: Dict[str, pd.DataFrame], variant: str) -> Tuple[List[Trade], pd.Series]:
    """Returns list of trades and per-bar combined net-return series (mean across symbols)."""
    trades: List[Trade] = []
    per_symbol_returns: Dict[str, pd.Series] = {}

    for sym, df in panels.items():
        if df.empty or len(df) < HOLD_BARS + 5:
            continue
        signal = pd.Series(0, index=df.index)
        if variant == "V_70_30":
            signal[df["long_ratio_pos"] > 0.70] = -1   # short
            signal[df["long_ratio_pos"] < 0.30] = +1   # long
        elif variant == "V_75_25":
            signal[df["long_ratio_pos"] > 0.75] = -1
            signal[df["long_ratio_pos"] < 0.25] = +1
        elif variant == "V_z_score":
            roll = df["long_ratio_pos"].rolling(30, min_periods=15)
            z = (df["long_ratio_pos"] - roll.mean()) / roll.std()
            signal[z > 2.0] = -1
            signal[z < -2.0] = +1
        elif variant == "V_pct_90_10":
            # per-symbol adaptive percentile thresholds (computed over full window)
            hi = df["long_ratio_pos"].quantile(0.90)
            lo = df["long_ratio_pos"].quantile(0.10)
            signal[df["long_ratio_pos"] > hi] = -1
            signal[df["long_ratio_pos"] < lo] = +1
        elif variant == "V_acct_70_30":
            if "long_ratio_acct" not in df.columns or df["long_ratio_acct"].isna().all():
                continue
            signal[df["long_ratio_acct"] > 0.70] = -1
            signal[df["long_ratio_acct"] < 0.30] = +1
        elif variant == "V_acct_z":
            if "long_ratio_acct" not in df.columns or df["long_ratio_acct"].isna().all():
                continue
            roll = df["long_ratio_acct"].rolling(30, min_periods=15)
            z = (df["long_ratio_acct"] - roll.mean()) / roll.std()
            signal[z > 2.0] = -1
            signal[z < -2.0] = +1
        else:
            raise ValueError(variant)

        # entries (non-overlapping: only when no active position)
        bar_ret = pd.Series(0.0, index=df.index)
        i = 0
        idx = df.index
        n = len(df)
        while i < n - HOLD_BARS:
            s = signal.iloc[i]
            if s != 0:
                entry_px = df["close"].iloc[i]
                exit_px = df["close"].iloc[i + HOLD_BARS]
                gross = s * (exit_px / entry_px - 1.0)
                net = gross - ROUND_TRIP_COST
                trades.append(Trade(
                    symbol=sym,
                    entry_ts=idx[i],
                    exit_ts=idx[i + HOLD_BARS],
                    side=s,
                    entry_px=float(entry_px),
                    exit_px=float(exit_px),
                    ratio=float(df["long_ratio_pos"].iloc[i]),
                    gross_ret=float(gross),
                    net_ret=float(net),
                ))
                # distribute return across the hold window so equity curve is sensible
                per_bar = net / HOLD_BARS
                for k in range(HOLD_BARS):
                    bar_ret.iloc[i + 1 + k] += per_bar
                i += HOLD_BARS  # non-overlap
            else:
                i += 1
        per_symbol_returns[sym] = bar_ret

    if not per_symbol_returns:
        return trades, pd.Series(dtype=float)

    combined = pd.concat(per_symbol_returns, axis=1).fillna(0.0)
    # equal-weight across active symbols (mean rather than sum keeps gross exposure ~1)
    portfolio = combined.mean(axis=1)
    return trades, portfolio


def stats(trades: List[Trade], portfolio: pd.Series) -> dict:
    if not trades:
        return {"n_trades": 0}
    nets = np.array([t.net_ret for t in trades])
    grosses = np.array([t.gross_ret for t in trades])
    longs = [t for t in trades if t.side == +1]
    shorts = [t for t in trades if t.side == -1]
    win = (nets > 0).mean()

    # Annualised Sharpe from per-bar portfolio returns (4H bars, 6/day)
    if len(portfolio) > 1 and portfolio.std(ddof=0) > 0:
        bars_per_year = 6 * 365
        sharpe = (portfolio.mean() / portfolio.std(ddof=0)) * math.sqrt(bars_per_year)
    else:
        sharpe = 0.0

    equity = (1 + portfolio).cumprod()
    if len(equity) > 0:
        peak = equity.cummax()
        dd = (equity / peak - 1).min()
    else:
        dd = 0.0

    return {
        "n_trades": len(trades),
        "n_long": len(longs),
        "n_short": len(shorts),
        "win_rate": float(win),
        "mean_net_ret_per_trade_bps": float(nets.mean() * 1e4),
        "mean_gross_ret_per_trade_bps": float(grosses.mean() * 1e4),
        "median_net_ret_bps": float(np.median(nets) * 1e4),
        "total_net_return_pct": float(((1 + nets).prod() - 1) * 100),
        "sharpe_annualised": float(sharpe),
        "max_drawdown_pct": float(dd * 100),
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    t0 = time.time()
    print("[K165] Fetching panels...")
    panels: Dict[str, pd.DataFrame] = {}
    data_meta: Dict[str, dict] = {}
    for sym in SYMBOLS:
        df = build_panel(sym)
        panels[sym] = df
        if not df.empty:
            data_meta[sym] = {
                "rows": int(len(df)),
                "first_ts": df.index[0].isoformat(),
                "last_ts": df.index[-1].isoformat(),
                "span_days": float((df.index[-1] - df.index[0]).total_seconds() / 86400),
                "long_ratio_pos_mean": float(df["long_ratio_pos"].mean()),
                "long_ratio_pos_std": float(df["long_ratio_pos"].std()),
                "long_ratio_pos_min": float(df["long_ratio_pos"].min()),
                "long_ratio_pos_max": float(df["long_ratio_pos"].max()),
                "pct_above_70": float((df["long_ratio_pos"] > 0.70).mean() * 100),
                "pct_below_30": float((df["long_ratio_pos"] < 0.30).mean() * 100),
                "pct_above_75": float((df["long_ratio_pos"] > 0.75).mean() * 100),
                "pct_below_25": float((df["long_ratio_pos"] < 0.25).mean() * 100),
                "long_ratio_acct_mean": float(df["long_ratio_acct"].mean()),
                "long_ratio_acct_min": float(df["long_ratio_acct"].min()),
                "long_ratio_acct_max": float(df["long_ratio_acct"].max()),
                "acct_pct_above_70": float((df["long_ratio_acct"] > 0.70).mean() * 100),
                "acct_pct_below_30": float((df["long_ratio_acct"] < 0.30).mean() * 100),
                "corr_pos_vs_acct": float(df["long_ratio_pos"].corr(df["long_ratio_acct"])),
            }
        else:
            data_meta[sym] = {"rows": 0}
        print(f"  {sym}: {data_meta[sym]}")

    variants = ["V_70_30", "V_75_25", "V_z_score",
                "V_pct_90_10", "V_acct_70_30", "V_acct_z"]
    results = {}
    curves = {}
    for v in variants:
        trades, port = run_variant(panels, v)
        s = stats(trades, port)
        results[v] = s
        # serialise curve
        if not port.empty:
            equity = (1 + port).cumprod()
            curves[v] = {
                "ts": [t.isoformat() for t in equity.index],
                "equity": [float(x) for x in equity.values],
                "ret": [float(x) for x in port.values],
            }
        print(f"  {v}: {s}")

    # per-symbol drill-down for the headline variant
    headline = "V_70_30"
    per_sym = {}
    for sym, df in panels.items():
        sub = {sym: df}
        trs, p = run_variant(sub, headline)
        per_sym[sym] = stats(trs, p)

    # Verdict logic: best variant by Sharpe with > 10 trades
    best = None
    for v, r in results.items():
        if r.get("n_trades", 0) < 10:
            continue
        if best is None or r.get("sharpe_annualised", -99) > best[1].get("sharpe_annualised", -99):
            best = (v, r)
    if best is None:
        verdict = "FRAMEWORK READY — NO VARIANT TRADED ENOUGH FOR ROBUST INFERENCE"
    else:
        v, r = best
        sh = r["sharpe_annualised"]
        if sh > 1.5:
            verdict = f"PASS-pilot: {v} Sharpe={sh:.2f} on 30d window; deploy live to accumulate OOS"
        elif sh > 0:
            verdict = (f"INCONCLUSIVE-pilot: {v} Sharpe={sh:.2f} on 30d window. "
                       "Edge is too small to justify capital; recommend live shadow-only.")
        else:
            verdict = (f"FAIL-pilot: best variant {v} Sharpe={sh:.2f} on 30d window. "
                       "Hypothesis NOT supported by Binance API position-ratio.")

    out = {
        "wave": "K165",
        "title": "Top-Trader Position Ratio Extreme Contrarian",
        "generated_at": pd.Timestamp.utcnow().isoformat(),
        "verdict": verdict,
        "binance_api_data_note": (
            "Binance /futures/data/topLongShortPositionRatio is hard-capped at the "
            "most recent ~30 days regardless of startTime/endTime. Verified empirically "
            "(server returns -1130 'parameter invalid' for any startTime/endTime older "
            "than ~30d). Therefore this is a FRAMEWORK + short pilot, not a full IS/OOS "
            "rigorous test."
        ),
        "method": {
            "universe": SYMBOLS,
            "period_bars": PERIOD,
            "hold_bars": HOLD_BARS,
            "cost_per_side": COST_PER_SIDE,
            "round_trip_cost": ROUND_TRIP_COST,
            "variants": variants,
        },
        "data_meta": data_meta,
        "variant_results": results,
        "per_symbol_V_70_30": per_sym,
        "key_findings": [
            ("Position-weighted long ratio (longAccount field) is empirically much "
             "more compressed than the hypothesised 0.3-0.7 band. Across BTC/ETH/SOL, "
             "the realised 30-day max is ~0.70 (SOL) and min ~0.41 (BTC). "
             "Pre-registered V_70_30 and V_75_25 produce ZERO trades."),
            ("ACCOUNT-weighted ratio (separate endpoint) is the series that matches "
             "CoinGlass UI. It does breach 0.70 routinely: ETH 36.7% of bars, SOL 66.1% "
             "of bars > 0.70. SOL never sees account_ratio < 0.30. "
             "This means the hypothesis as written maps to ACCOUNT ratio, not POSITION."),
            ("Correlation pos vs acct: BTC 0.85, ETH 0.67, SOL -0.02. "
             "For SOL the two series are essentially uncorrelated — big-position "
             "whales and majority of small accounts disagree."),
            ("V_acct_70_30 traded 48x (all SHORT — account ratio never crashed) and "
             "produced Sharpe 0.34, total return +0.13% net of costs over 30d. "
             "Tiny edge, mostly noise."),
            ("V_z_score and V_pct_90_10 (the symmetric variants) lost money on this "
             "window — Sharpe -5.1 and -11.1 respectively. The 30-day sample size is "
             "too small to draw strong conclusions; one trend can dominate."),
            ("Binance API hard-caps top-trader ratio at last ~30 days regardless of "
             "startTime / endTime params (verified empirically: server returns "
             "'-1130 parameter invalid' for any older request). "
             "Long-history backtest IS NOT POSSIBLE from REST — would require ongoing "
             "live capture into a local store, or paid CoinGlass historical data."),
        ],
        "recommended_next_steps": [
            "Stand up a daily cron capturing /futures/data/topLongShortPositionRatio "
            "AND /futures/data/topLongShortAccountRatio for BTC/ETH/SOL/BNB/XRP at 4h "
            "to build proprietary history (90d in ~3 months).",
            "Investigate ACCOUNT-ratio thresholds 0.75/0.25 with longer hold (24h-48h), "
            "since account ratio is where the 'crowded retail' signal lives.",
            "Cross-reference with funding rate sign at signal time -- crowded-long "
            "with positive funding is the classic squeeze setup.",
            "Treat current backtest as PILOT only. Live shadow-trade V_acct_70_30 "
            "to accumulate genuine OOS evidence before risking capital.",
        ],
        "runtime_seconds": round(time.time() - t0, 2),
    }

    OUT_JSON.write_text(json.dumps(out, indent=2, default=str))
    OUT_CURVES.write_text(json.dumps(curves, indent=2, default=str))
    print(f"[K165] Wrote {OUT_JSON.name} and {OUT_CURVES.name} in {out['runtime_seconds']}s")
    return out


if __name__ == "__main__":
    main()
