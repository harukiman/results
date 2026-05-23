"""Forward Test Scaffold — Top portfolio (ATR×8 + vol_z≥1.5 filter).

目的:
  §6 G3 改善ルート #1 = フォワードテストで OOS データ累積、DSR の罰則を軽減。
  毎日実行 (launchctl 経由) で:
    1. 最新4Hデータ取得
    2. シグナル生成 (ATR + vol_z filter)
    3. ペーパー約定をログ
    4. 累積エクイティを report.html セクションに反映

実装:
  - シングルJSONファイルに「累積トレード+エクイティ+メトリクス」保存
  - 各実行で新バーがあれば追記、無ければ no-op
  - レジーム状態 (vol_z) も同時記録
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
from engine.data import fetch_klines

SYMBOLS = ["OPUSDT", "WIFUSDT", "INJUSDT", "BONKUSDT",
           "DOGEUSDT", "SHIBUSDT", "ARBUSDT", "LINKUSDT"]
ATR_PARAMS = {"atr_short": 7, "atr_long": 56, "threshold": 0.6,
              "ema_fast": 20, "ema_slow": 80}
EXIT = {"stop_loss_pct": 0.04, "take_profit_pct": 0.08, "max_hold_bars": 24}
VOL_Z_THRESHOLD = 1.5
DAYS = 730  # historical baseline for state computation
BARS_PER_YEAR = 2190
FORWARD_STATE_PATH = Path("/Users/nekonaomichi/crypto-lab/forward_state.json")
FORWARD_TEST_START_DATE = "2026-05-24"  # OOS start (today)


def atr_ratio_signal(df, atr_short=7, atr_long=56, threshold=0.6,
                     ema_fast=20, ema_slow=80):
    atr_s = (df['high'] - df['low']).rolling(atr_short).mean()
    atr_l = (df['high'] - df['low']).rolling(atr_long).mean()
    compression = atr_s < atr_l * threshold
    ema_f = df['close'].ewm(span=ema_fast).mean()
    ema_s = df['close'].ewm(span=ema_slow).mean()
    sig = pd.Series(0, index=df.index)
    sig[compression & (ema_f > ema_s)] = 1
    sig[compression & (ema_f < ema_s)] = -1
    warmup = max(atr_long, ema_slow) + 5
    sig.iloc[:warmup] = 0
    return sig


async def get_btc_volz():
    btc = await fetch_klines("BTCUSDT", "4h", DAYS)
    btc['ret'] = btc['close'].pct_change()
    btc['rv'] = btc['ret'].rolling(60).std() * np.sqrt(BARS_PER_YEAR) * 100
    btc['rvm'] = btc['rv'].rolling(360).mean()
    btc['rvs'] = btc['rv'].rolling(360).std()
    btc['volz'] = (btc['rv'] - btc['rvm']) / (btc['rvs'] + 1e-10)
    return btc[['open_time', 'volz']].copy()


async def main():
    """Single forward-test snapshot. Idempotent (won't double-log existing bars)."""
    print(f"=== Forward Test Snapshot — {datetime.now().isoformat()} ===")
    if FORWARD_STATE_PATH.exists():
        state = json.loads(FORWARD_STATE_PATH.read_text())
        last_bar_logged = state.get("last_bar_logged")
        print(f"  Loaded state: last_bar={last_bar_logged}, n_signals={len(state.get('signals_log', []))}")
    else:
        state = {
            "forward_test_start": FORWARD_TEST_START_DATE,
            "strategy": "ATR_Ratio × 8 + vol_z>=1.5",
            "symbols": SYMBOLS,
            "params": ATR_PARAMS,
            "exit": EXIT,
            "signals_log": [],   # list of {timestamp, symbol, signal, vol_z, filtered}
            "metrics_history": [],  # list of {timestamp, cum_signals, n_active}
            "last_bar_logged": None,
        }
        print(f"  Initialized new forward test state")

    btc_vz = await get_btc_volz()

    # For each symbol, fetch latest bars (incremental cache)
    new_signals = 0
    latest_bar_time = None
    for s in SYMBOLS:
        df = await fetch_klines(s, "4h", 90)  # last 90 days for warmup + recent
        sig = atr_ratio_signal(df, **ATR_PARAMS)
        # Align vol_z
        btc = btc_vz.set_index('open_time')
        aligned = btc.reindex(df['open_time'], method='ffill')['volz'].values
        vz_series = pd.Series(aligned, index=df.index).fillna(0)
        bad_regime = vz_series >= VOL_Z_THRESHOLD
        sig_filtered = sig.copy()
        sig_filtered[bad_regime] = 0

        # Take last bar
        last_idx = len(df) - 1
        bar_time = df['open_time'].iloc[last_idx]
        if latest_bar_time is None or bar_time > latest_bar_time:
            latest_bar_time = bar_time

        # Was already logged?
        bar_str = bar_time.isoformat()
        if state["last_bar_logged"] and bar_str <= state["last_bar_logged"]:
            continue

        sig_val = int(sig.iloc[last_idx])
        sig_f_val = int(sig_filtered.iloc[last_idx])
        vz_val = float(vz_series.iloc[last_idx])

        state["signals_log"].append({
            "timestamp": bar_str,
            "symbol": s,
            "raw_signal": sig_val,
            "vol_z": round(vz_val, 3),
            "regime_off": bool(bad_regime.iloc[last_idx]),
            "filtered_signal": sig_f_val,
            "close": float(df['close'].iloc[last_idx]),
        })
        if sig_f_val != 0:
            new_signals += 1
            print(f"  ACTIVE: {s:<10} sig={sig_f_val:+d} vol_z={vz_val:+.2f} close={df['close'].iloc[last_idx]:.4f}")
        else:
            status = "regime_off" if bad_regime.iloc[last_idx] else "no_signal"
            print(f"  {status:<10} {s:<10} vol_z={vz_val:+.2f}")

    if latest_bar_time:
        state["last_bar_logged"] = latest_bar_time.isoformat()

    # Update metrics history
    if state["signals_log"]:
        # Calculate cumulative active signals
        df_log = pd.DataFrame(state["signals_log"])
        cum_active = (df_log["filtered_signal"] != 0).sum()
        state["metrics_history"].append({
            "snapshot_time": datetime.now(timezone(timedelta(hours=9))).strftime("%Y-%m-%d %H:%M JST"),
            "last_bar": state["last_bar_logged"],
            "total_logged_bars": len(state["signals_log"]),
            "active_signals": int(cum_active),
            "new_signals_this_run": new_signals,
        })

    FORWARD_STATE_PATH.write_text(json.dumps(state, indent=2, default=str))
    print(f"\nSaved: {FORWARD_STATE_PATH}")
    print(f"  Total logged bars: {len(state['signals_log'])}")
    print(f"  Active signals (cumulative): {sum(1 for s in state['signals_log'] if s['filtered_signal'] != 0)}")
    print(f"  New signals this run: {new_signals}")


if __name__ == "__main__":
    asyncio.run(main())
