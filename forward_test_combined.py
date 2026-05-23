"""Forward Test — Combined Portfolio (50% ATR + 50% FOPD).

Tracks BOTH strategies' signals in one daemon. Each 4h tick:
  - ATR signals on 8 symbols + vol_z filter
  - FOPD signals on 6 symbols (FR + OI z-scores)
  - Log every active signal with timestamp + close + filter state
  - Cumulative metrics: signals_total / active_now / regime status

State file: forward_state_combined.json
"""
import asyncio
import json
import sys
import time
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime, timezone, timedelta

sys.path.insert(0, "/Users/nekonaomichi/crypto-lab")
from engine.data import fetch_klines, fetch_bybit_funding_rate, fetch_historical_metrics

ATR_SYMBOLS = ["OPUSDT", "WIFUSDT", "INJUSDT", "BONKUSDT",
               "DOGEUSDT", "SHIBUSDT", "ARBUSDT", "LINKUSDT"]
FOPD_BEST = {
    "BNBUSDT":  {"fr": 1.0, "oi": 0.5, "ret": 1.5, "sl": 0.04, "tp": 0.06, "mhb": 6},
    "AVAXUSDT": {"fr": 2.0, "oi": 1.0, "ret": 1.5, "sl": 0.04, "tp": 0.06, "mhb": 6},
    "ETHUSDT":  {"fr": 1.5, "oi": 1.5, "ret": 0.5, "sl": 0.04, "tp": 0.06, "mhb": 6},
    "ADAUSDT":  {"fr": 2.0, "oi": 0.5, "ret": 0.5, "sl": 0.04, "tp": 0.06, "mhb": 6},
    "LINKUSDT": {"fr": 1.0, "oi": 0.5, "ret": 1.0, "sl": 0.04, "tp": 0.06, "mhb": 6},
    "DOTUSDT":  {"fr": 2.0, "oi": 1.0, "ret": 1.0, "sl": 0.04, "tp": 0.06, "mhb": 6},
}
ATR_PARAMS = {"atr_short": 7, "atr_long": 56, "threshold": 0.6, "ema_fast": 20, "ema_slow": 80}
ATR_EXIT = {"stop_loss_pct": 0.04, "take_profit_pct": 0.08, "max_hold_bars": 24}
VOL_Z = 1.5
DAYS_HISTORY = 730
BARS_PER_YEAR = 2190
STATE_PATH = Path("/Users/nekonaomichi/crypto-lab/forward_state_combined.json")
START_DATE = "2026-05-24"


def atr_ratio_signal(df, **k):
    atr_s = (df['high'] - df['low']).rolling(k['atr_short']).mean()
    atr_l = (df['high'] - df['low']).rolling(k['atr_long']).mean()
    comp = atr_s < atr_l * k['threshold']
    ef = df['close'].ewm(span=k['ema_fast']).mean()
    es = df['close'].ewm(span=k['ema_slow']).mean()
    sig = pd.Series(0, index=df.index)
    sig[comp & (ef > es)] = 1
    sig[comp & (ef < es)] = -1
    warmup = max(k['atr_long'], k['ema_slow']) + 5
    sig.iloc[:warmup] = 0
    return sig


def fopd_signal(df, fr_series, oi_series, fr_z, oi_z, ret_z, w=180):
    df_w = df.copy().sort_values('open_time').reset_index(drop=True)
    df_w['open_time'] = pd.to_datetime(df_w['open_time']).astype('datetime64[ns]')
    if fr_series is not None and not fr_series.empty:
        fr_df = fr_series.copy()
        fr_df['timestamp'] = pd.to_datetime(fr_df['timestamp']).astype('datetime64[ns]')
        fr_df = fr_df.sort_values('timestamp').reset_index(drop=True)
        m = pd.merge_asof(df_w[['open_time']], fr_df.rename(columns={'timestamp':'open_time'}), on='open_time', direction='backward')
        fr = m['funding_rate'].fillna(0).values
    else:
        fr = np.zeros(len(df_w))
    if oi_series is not None and not oi_series.empty and 'oi' in oi_series.columns:
        oi_df = oi_series.copy()
        oi_df['timestamp'] = pd.to_datetime(oi_df['timestamp']).astype('datetime64[ns]')
        oi_df = oi_df.sort_values('timestamp').reset_index(drop=True)
        mo = pd.merge_asof(df_w[['open_time']], oi_df[['timestamp','oi']].rename(columns={'timestamp':'open_time'}), on='open_time', direction='backward')
        oi_vals = mo['oi'].ffill().bfill().values
    else:
        oi_vals = np.full(len(df_w), np.nan)
    oi_chg = pd.Series(oi_vals, index=df_w.index).pct_change(6).fillna(0).values
    ret = pd.Series(df_w['close'].values, index=df_w.index).pct_change(6).fillna(0).values
    def zscore(s, win=w):
        return ((s - s.rolling(win).mean()) / (s.rolling(win).std() + 1e-12)).fillna(0).values
    fr_z_v = zscore(pd.Series(fr))
    oi_z_v = zscore(pd.Series(oi_chg))
    ret_z_v = zscore(pd.Series(ret))
    long_s = (fr_z_v < -fr_z) & (oi_z_v < -oi_z) & (ret_z_v < -ret_z)
    short_s = (fr_z_v > fr_z) & (oi_z_v > oi_z) & (ret_z_v > ret_z)
    sig = np.zeros(len(df_w), dtype=int)
    sig[long_s] = +1; sig[short_s] = -1; sig[:w + 10] = 0
    return pd.Series(sig, index=df_w.index)


async def get_btc_volz():
    btc = await fetch_klines("BTCUSDT", "4h", DAYS_HISTORY)
    btc['ret'] = btc['close'].pct_change()
    btc['rv'] = btc['ret'].rolling(60).std() * np.sqrt(BARS_PER_YEAR) * 100
    btc['rvm'] = btc['rv'].rolling(360).mean()
    btc['rvs'] = btc['rv'].rolling(360).std()
    btc['volz'] = (btc['rv'] - btc['rvm']) / (btc['rvs'] + 1e-10)
    return btc[['open_time', 'volz']]


async def main():
    print(f"=== Combined Forward Test Snapshot — {datetime.now().isoformat()} ===")
    if STATE_PATH.exists():
        state = json.loads(STATE_PATH.read_text())
    else:
        state = {
            "start_date": START_DATE,
            "strategy": "50% ATR + 50% FOPD",
            "atr_symbols": ATR_SYMBOLS,
            "fopd_symbols": list(FOPD_BEST.keys()),
            "signals_log": [],
            "metrics_history": [],
            "last_bar_logged": None,
        }

    btc_vz = await get_btc_volz()
    btc_idx = btc_vz.set_index('open_time')

    new_signals = 0
    latest_bar_time = None

    # ── ATR ──
    for s in ATR_SYMBOLS:
        df = await fetch_klines(s, "4h", 90)
        sig = atr_ratio_signal(df, **ATR_PARAMS)
        aligned = btc_idx.reindex(df['open_time'], method='ffill')['volz'].values
        vz_series = pd.Series(aligned, index=df.index).fillna(0)
        bad = vz_series >= VOL_Z

        last_idx = len(df) - 1
        bar_time = df['open_time'].iloc[last_idx]
        if latest_bar_time is None or bar_time > latest_bar_time:
            latest_bar_time = bar_time
        bar_str = bar_time.isoformat()
        if state["last_bar_logged"] and bar_str <= state["last_bar_logged"]:
            continue
        sig_val = int(sig.iloc[last_idx])
        sig_f_val = int(0 if bad.iloc[last_idx] else sig_val)
        vz_val = float(vz_series.iloc[last_idx])
        state["signals_log"].append({
            "timestamp": bar_str, "strategy": "ATR", "symbol": s,
            "raw_signal": sig_val, "vol_z": round(vz_val, 3),
            "regime_off": bool(bad.iloc[last_idx]),
            "filtered_signal": sig_f_val,
            "close": float(df['close'].iloc[last_idx]),
        })
        if sig_f_val != 0:
            new_signals += 1
            print(f"  [ATR ACTIVE] {s:<10} sig={sig_f_val:+d} vol_z={vz_val:+.2f}")

    # ── FOPD ──
    for s, p in FOPD_BEST.items():
        df = await fetch_klines(s, "4h", 365)  # need longer for z-score
        try:
            fr_df = await fetch_bybit_funding_rate(s, 365)
        except:
            fr_df = None
        try:
            oi_df = await fetch_historical_metrics(s, 365)
        except:
            oi_df = None
        if fr_df is None or oi_df is None:
            continue
        sig = fopd_signal(df, fr_df, oi_df, p["fr"], p["oi"], p["ret"])
        last_idx = len(df) - 1
        bar_time = df['open_time'].iloc[last_idx]
        bar_str = bar_time.isoformat()
        if state["last_bar_logged"] and bar_str <= state["last_bar_logged"]:
            continue
        sig_val = int(sig.iloc[last_idx])
        state["signals_log"].append({
            "timestamp": bar_str, "strategy": "FOPD", "symbol": s,
            "raw_signal": sig_val,
            "filtered_signal": sig_val,  # FOPD has no additional vol_z filter
            "close": float(df['close'].iloc[last_idx]),
        })
        if sig_val != 0:
            new_signals += 1
            print(f"  [FOPD ACTIVE] {s:<10} sig={sig_val:+d}")

    if latest_bar_time:
        state["last_bar_logged"] = latest_bar_time.isoformat()

    state["metrics_history"].append({
        "snapshot_time": datetime.now(timezone(timedelta(hours=9))).strftime("%Y-%m-%d %H:%M JST"),
        "last_bar": state["last_bar_logged"],
        "total_logged_bars": len(state["signals_log"]),
        "active_signals_cumulative": sum(1 for s in state["signals_log"] if s.get('filtered_signal', 0) != 0),
        "new_signals_this_run": new_signals,
    })

    STATE_PATH.write_text(json.dumps(state, indent=2, default=str))
    print(f"\n  Total logged bars: {len(state['signals_log'])}")
    print(f"  Active signals (cumulative): {sum(1 for s in state['signals_log'] if s.get('filtered_signal', 0) != 0)}")
    print(f"  New signals this run: {new_signals}")
    print(f"Saved: {STATE_PATH}")


if __name__ == "__main__":
    asyncio.run(main())
