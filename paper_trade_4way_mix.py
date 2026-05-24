"""Wave K17 — Paper Trading Scaffold for 4-way mix (新ベスト, §6 8/8 PASS).

実運用準備 (Wave K13 認定):
  85% × 80/10/10 + 15% × vol_z MR (BTC/ETH/SOL/BNB)
  5 strategy axes, 16 symbols

呼び出すたびに最新4Hバーがあれば 5 axes 全てのシグナルを処理:
  軸1: ATR 4H × 8 銘柄 (vol_z fil)
  軸2: FOPD 4H × 6 銘柄
  軸3: 8H BONK + SHIB
  軸4: vol_MR × 4 (BTC/ETH/SOL/BNB) ← Wave K11 追加

状態保存: paper_trades_4way.json
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

STATE_PATH = Path("/Users/nekonaomichi/crypto-lab/paper_trades_4way.json")
START_DATE = "2026-05-24"
INITIAL_CAPITAL = 10000.0  # USD
LEVERAGE = 3.0  # 保守的 (Kelly Quarter は 10x だが初回は 3x)
TAKER_FEE = 0.0004  # 0.04% (MEXC standard)
SLIPPAGE = 0.0003  # 0.03% per side

ATR_SYMBOLS = ["OPUSDT", "WIFUSDT", "INJUSDT", "BONKUSDT",
               "DOGEUSDT", "SHIBUSDT", "ARBUSDT", "LINKUSDT"]
FOPD_BEST = {
    "BNBUSDT":  {"fr": 1.0, "oi": 0.5, "ret": 1.5, "sl": 0.04, "tp": 0.06, "mhb": 6},
    "AVAXUSDT": {"fr": 2.0, "oi": 1.0, "ret": 1.5, "sl": 0.04, "tp": 0.06, "mhb": 6},
    "ETHUSDT":  {"fr": 1.5, "oi": 1.5, "ret": 0.5, "sl": 0.04, "tp": 0.06, "mhb": 6},
    "ADAUSDT":  {"fr": 2.0, "oi": 0.5, "ret": 0.5, "sl": 0.04, "tp": 0.06, "mhb": 6},
    "LINKUSDT": {"fr": 1.0, "oi": 0.5, "ret": 1.0, "sl": 0.04, "tp": 0.06, "mhb": 6},
}
ATR_PARAMS_4H = {"atr_short": 7, "atr_long": 56, "threshold": 0.6, "ema_fast": 20, "ema_slow": 80}
ATR_PARAMS_8H = {"atr_short": 4, "atr_long": 28, "threshold": 0.6, "ema_fast": 10, "ema_slow": 40}
EXIT_4H = {"sl": 0.04, "tp": 0.08, "mhb": 24}  # in bars
EXIT_8H = {"sl": 0.04, "tp": 0.08, "mhb": 12}
VOL_Z = 1.5

# Portfolio weights (v3 mix: 5-axis v2 × 0.80 + OI capit × 0.20, Wave K49e)
W_ATR = 0.272       # 0.34 × 0.80
W_FOPD = 0.272      # 0.34 × 0.80
W_BONK_8H = 0.068   # 0.085 × 0.80
W_SHIB_8H = 0.068   # 0.085 × 0.80
W_VOL_MR = 0.120    # 0.15 × 0.80
W_OI_CAPIT = 0.200  # 6番目軸 (Wave K49)

# OI capitulation params (Wave K49)
OI_CAPIT_SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "DOGEUSDT", "AVAXUSDT", "LINKUSDT"]
OI_CAPIT_PARAMS = {
    "window": 120,        # lookback for z-score
    "z_thresh": 2.0,      # OI z-score threshold (negative for capit)
    "ret_z_thresh": 1.0,  # price z-score threshold (negative for capit)
    "hold_bars": 12,      # 48h hold
    "sl": 0.04,
    "tp": 0.06,
}

# vol_MR per symbol params (Wave K11)
VOL_MR_BEST = {
    "BTCUSDT":  {"vol_z_low": -1.0, "vol_z_high": 1.0, "trend_window": 10, "sl": 0.04, "tp": 0.06, "mhb": 12},
    "ETHUSDT":  {"vol_z_low": -2.0, "vol_z_high": 1.0, "trend_window": 20, "sl": 0.04, "tp": 0.06, "mhb": 12},
    "SOLUSDT":  {"vol_z_low": -1.5, "vol_z_high": 2.0, "trend_window": 10, "sl": 0.04, "tp": 0.06, "mhb": 12},
    "BNBUSDT":  {"vol_z_low": -1.5, "vol_z_high": 1.0, "trend_window": 10, "sl": 0.04, "tp": 0.06, "mhb": 12},
}


def aggregate_4h_to_8h(df_4h):
    df = df_4h.copy().sort_values('open_time').reset_index(drop=True)
    df['pair_idx'] = df.index // 2
    return df.groupby('pair_idx').agg({
        'open_time': 'first', 'open': 'first', 'high': 'max', 'low': 'min',
        'close': 'last', 'volume': 'sum'
    }).reset_index(drop=True)


def atr_ratio_signal(df, **k):
    atr_s = (df['high'] - df['low']).rolling(k['atr_short']).mean()
    atr_l = (df['high'] - df['low']).rolling(k['atr_long']).mean()
    comp = atr_s < atr_l * k['threshold']
    ef = df['close'].ewm(span=k['ema_fast']).mean()
    es = df['close'].ewm(span=k['ema_slow']).mean()
    sig = pd.Series(0, index=df.index)
    sig[comp & (ef > es)] = 1
    sig[comp & (ef < es)] = -1
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


def load_or_init_state():
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text())
    return {
        "start_date": START_DATE,
        "strategy": "v3 mix (ATR×8 + FOPD×5 + BONK_8H + SHIB_8H + vol_MR + OI_capit×7) — K49 §6 7/8 PASS",
        "initial_capital_usd": INITIAL_CAPITAL,
        "leverage": LEVERAGE,
        "equity_usd": INITIAL_CAPITAL,
        "open_positions": [],  # list of {entry_bar, symbol, strategy, side, entry_price, sl, tp, expiry_bar, size_usd}
        "closed_trades": [],   # list of {entry/exit details + pnl_usd}
        "snapshots": [],       # list of {timestamp, equity, n_open, n_total}
        "last_processed_bar": {},  # per symbol: last bar timestamp
    }


def save_state(state):
    STATE_PATH.write_text(json.dumps(state, indent=2, default=str))


async def get_btc_volz_4h():
    btc = await fetch_klines("BTCUSDT", "4h", 90)
    btc['ret'] = btc['close'].pct_change()
    btc['rv'] = btc['ret'].rolling(60).std() * np.sqrt(2190) * 100
    btc['rvm'] = btc['rv'].rolling(360).mean()
    btc['rvs'] = btc['rv'].rolling(360).std()
    btc['volz'] = (btc['rv'] - btc['rvm']) / (btc['rvs'] + 1e-10)
    return btc


async def get_btc_volz_8h():
    # Need full 90+ days to get rolling 180-bar baseline
    btc_4h = await fetch_klines("BTCUSDT", "4h", 90)
    btc_8h = aggregate_4h_to_8h(btc_4h)
    btc_8h['ret'] = btc_8h['close'].pct_change()
    btc_8h['rv'] = btc_8h['ret'].rolling(30).std() * np.sqrt(1095) * 100
    btc_8h['rvm'] = btc_8h['rv'].rolling(180).mean()
    btc_8h['rvs'] = btc_8h['rv'].rolling(180).std()
    btc_8h['volz'] = (btc_8h['rv'] - btc_8h['rvm']) / (btc_8h['rvs'] + 1e-10)
    return btc_8h


async def process_atr_strategy(state, btc_volz_4h, weight):
    """ATR 4H × 8 銘柄 (vol_z fil 付き)."""
    n_new_signals = 0
    for s in ATR_SYMBOLS:
        df = await fetch_klines(s, "4h", 90)
        sig = atr_ratio_signal(df, **ATR_PARAMS_4H)
        # vol_z filter
        btc_idx = btc_volz_4h.set_index('open_time')
        aligned = btc_idx.reindex(df['open_time'], method='ffill')['volz'].values
        bad = pd.Series(aligned, index=sig.index).fillna(False) >= VOL_Z
        sig[bad] = 0
        # Last bar
        last_idx = len(df) - 1
        bar_time = df['open_time'].iloc[last_idx].isoformat()
        last_processed = state['last_processed_bar'].get(f"ATR_{s}", "")
        if bar_time <= last_processed:
            continue
        state['last_processed_bar'][f"ATR_{s}"] = bar_time
        sig_val = int(sig.iloc[last_idx])
        close = float(df['close'].iloc[last_idx])
        if sig_val == 0:
            continue
        # Open new paper position
        size_usd = state['equity_usd'] * weight / 8 * state['leverage']  # weight / N symbols × leverage
        position = {
            "entry_bar": bar_time, "symbol": s, "strategy": "ATR_4H",
            "side": "long" if sig_val > 0 else "short", "entry_price": close,
            "sl": close * (1 - 0.04) if sig_val > 0 else close * (1 + 0.04),
            "tp": close * (1 + 0.08) if sig_val > 0 else close * (1 - 0.08),
            "expiry_bar_offset": 24, "size_usd": size_usd,
        }
        state['open_positions'].append(position)
        n_new_signals += 1
        print(f"  [ATR_4H NEW] {s:<10} {position['side']:<5} entry=${close:.4f} size=${size_usd:.0f}")
    return n_new_signals


async def process_fopd_strategy(state, weight):
    """FOPD 4H × 6 銘柄 (no extra filter)."""
    n_new_signals = 0
    for s, p in FOPD_BEST.items():
        df = await fetch_klines(s, "4h", 365)
        try:
            fr_df = await fetch_bybit_funding_rate(s, 365)
        except: fr_df = None
        try:
            oi_df = await fetch_historical_metrics(s, 365)
        except: oi_df = None
        if fr_df is None or oi_df is None:
            continue
        sig = fopd_signal(df, fr_df, oi_df, p["fr"], p["oi"], p["ret"])
        last_idx = len(df) - 1
        bar_time = df['open_time'].iloc[last_idx].isoformat()
        last_processed = state['last_processed_bar'].get(f"FOPD_{s}", "")
        if bar_time <= last_processed:
            continue
        state['last_processed_bar'][f"FOPD_{s}"] = bar_time
        sig_val = int(sig.iloc[last_idx])
        close = float(df['close'].iloc[last_idx])
        if sig_val == 0:
            continue
        size_usd = state['equity_usd'] * weight / 6 * state['leverage']
        position = {
            "entry_bar": bar_time, "symbol": s, "strategy": "FOPD_4H",
            "side": "long" if sig_val > 0 else "short", "entry_price": close,
            "sl": close * (1 - p["sl"]) if sig_val > 0 else close * (1 + p["sl"]),
            "tp": close * (1 + p["tp"]) if sig_val > 0 else close * (1 - p["tp"]),
            "expiry_bar_offset": p["mhb"], "size_usd": size_usd,
        }
        state['open_positions'].append(position)
        n_new_signals += 1
        print(f"  [FOPD_4H NEW] {s:<10} {position['side']:<5} entry=${close:.4f}")
    return n_new_signals


async def process_8h_meme(state, btc_volz_8h, weight):
    """8H BONK + SHIB with vol_z filter."""
    n_new_signals = 0
    for s in ["BONKUSDT", "SHIBUSDT"]:
        df_4h = await fetch_klines(s, "4h", 90)
        df_8h = aggregate_4h_to_8h(df_4h)
        sig = atr_ratio_signal(df_8h, **ATR_PARAMS_8H)
        btc_idx = btc_volz_8h.set_index('open_time')
        aligned = btc_idx.reindex(df_8h['open_time'], method='ffill')['volz'].values
        bad = pd.Series(aligned, index=sig.index).fillna(False) >= VOL_Z
        sig[bad] = 0
        last_idx = len(df_8h) - 1
        bar_time = df_8h['open_time'].iloc[last_idx].isoformat()
        last_processed = state['last_processed_bar'].get(f"8H_{s}", "")
        if bar_time <= last_processed:
            continue
        state['last_processed_bar'][f"8H_{s}"] = bar_time
        sig_val = int(sig.iloc[last_idx])
        close = float(df_8h['close'].iloc[last_idx])
        if sig_val == 0:
            continue
        # weight already accounts for per-strategy weight
        size_usd = state['equity_usd'] * weight * state['leverage']
        position = {
            "entry_bar": bar_time, "symbol": s, "strategy": "ATR_8H",
            "side": "long" if sig_val > 0 else "short", "entry_price": close,
            "sl": close * (1 - 0.04) if sig_val > 0 else close * (1 + 0.04),
            "tp": close * (1 + 0.08) if sig_val > 0 else close * (1 - 0.08),
            "expiry_bar_offset": 12, "size_usd": size_usd,
        }
        state['open_positions'].append(position)
        n_new_signals += 1
        print(f"  [ATR_8H NEW] {s:<10} {position['side']:<5} entry=${close:.6f}")
    return n_new_signals


async def manage_open_positions(state):
    """Close open positions if SL/TP/expiry hit on latest 4H bar."""
    closed = 0
    pnl_total = 0.0
    still_open = []
    for pos in state['open_positions']:
        # Fetch current price (latest 4H bar)
        try:
            df = await fetch_klines(pos['symbol'], "4h", 30)
        except Exception:
            still_open.append(pos)
            continue
        # entry_bar parse
        entry_dt = pd.to_datetime(pos['entry_bar'])
        # bars since entry
        mask = df['open_time'] > entry_dt
        bars_since = mask.sum()
        # Check SL/TP via high/low between entry and now
        recent = df[mask]
        exit_reason = None
        exit_price = None
        for idx, row in recent.iterrows():
            if pos['side'] == "long":
                if row['low'] <= pos['sl']:
                    exit_reason = "SL"; exit_price = pos['sl']; break
                if row['high'] >= pos['tp']:
                    exit_reason = "TP"; exit_price = pos['tp']; break
            else:  # short
                if row['high'] >= pos['sl']:
                    exit_reason = "SL"; exit_price = pos['sl']; break
                if row['low'] <= pos['tp']:
                    exit_reason = "TP"; exit_price = pos['tp']; break
        if exit_reason is None and bars_since >= pos['expiry_bar_offset']:
            exit_reason = "MH"; exit_price = float(df['close'].iloc[-1])
        if exit_reason is not None:
            # Compute PnL
            if pos['side'] == "long":
                pct = (exit_price - pos['entry_price']) / pos['entry_price']
            else:
                pct = (pos['entry_price'] - exit_price) / pos['entry_price']
            # Apply costs (in + out)
            pct -= 2 * (TAKER_FEE + SLIPPAGE)
            pnl_usd = pos['size_usd'] * pct
            state['closed_trades'].append({
                **pos, "exit_price": exit_price, "exit_reason": exit_reason,
                "pnl_pct": round(pct, 6), "pnl_usd": round(pnl_usd, 2),
            })
            state['equity_usd'] += pnl_usd
            closed += 1
            pnl_total += pnl_usd
            print(f"  [CLOSED] {pos['symbol']:<10} {pos['side']:<5} {exit_reason} pnl=${pnl_usd:+.2f} ({pct*100:+.2f}%)")
        else:
            still_open.append(pos)
    state['open_positions'] = still_open
    return closed, pnl_total


def btc_vol_mr_signal_local(df, vol_z_low, vol_z_high, trend_window):
    close = df['close'].values
    ret = np.zeros_like(close)
    ret[1:] = (close[1:] - close[:-1]) / close[:-1]
    rv = pd.Series(ret).rolling(60).std() * np.sqrt(2190) * 100
    rvm = rv.rolling(360).mean()
    rvs = rv.rolling(360).std()
    vol_z = ((rv - rvm) / (rvs + 1e-10)).fillna(0).values
    ema_fast = pd.Series(close).ewm(span=trend_window).mean().values
    ema_slow = pd.Series(close).ewm(span=trend_window * 3).mean().values
    bullish = ema_fast > ema_slow
    bearish = ema_fast < ema_slow
    recent_ret = pd.Series(close).pct_change(6).fillna(0).values
    sig = np.zeros(len(df), dtype=int)
    sig[(vol_z < vol_z_low) & bullish] = +1
    sig[(vol_z < vol_z_low) & bearish] = -1
    sig[(vol_z > vol_z_high) & (recent_ret < -0.05)] = +1
    sig[(vol_z > vol_z_high) & (recent_ret > 0.05)] = -1
    sig[:380] = 0
    return pd.Series(sig, index=df.index)


async def process_vol_mr_strategy(state, weight):
    """vol_MR 4 symbols (BTC/ETH/SOL/BNB), Wave K11 best params."""
    n_new = 0
    for sym, p in VOL_MR_BEST.items():
        df = await fetch_klines(sym, "4h", 365)  # need long history for vol_z calc
        sig = btc_vol_mr_signal_local(df, p["vol_z_low"], p["vol_z_high"], p["trend_window"])
        last_idx = len(df) - 1
        bar_time = df['open_time'].iloc[last_idx].isoformat()
        last_processed = state['last_processed_bar'].get(f"VOL_MR_{sym}", "")
        if bar_time <= last_processed:
            continue
        state['last_processed_bar'][f"VOL_MR_{sym}"] = bar_time
        sig_val = int(sig.iloc[last_idx])
        if sig_val == 0:
            continue
        close = float(df['close'].iloc[last_idx])
        size_usd = state['equity_usd'] * weight / 4 * state['leverage']  # weight / 4 symbols
        position = {
            "entry_bar": bar_time, "symbol": sym, "strategy": "vol_MR_4H",
            "side": "long" if sig_val > 0 else "short", "entry_price": close,
            "sl": close * (1 - p["sl"]) if sig_val > 0 else close * (1 + p["sl"]),
            "tp": close * (1 + p["tp"]) if sig_val > 0 else close * (1 - p["tp"]),
            "expiry_bar_offset": p["mhb"], "size_usd": size_usd,
        }
        state['open_positions'].append(position)
        n_new += 1
        print(f"  [VOL_MR NEW] {sym:<10} {position['side']:<5} entry=${close:.2f}")
    return n_new


async def process_oi_capit_strategy(state, weight):
    """OI Capitulation 7 銘柄 portfolio (Wave K49). Signal: OI z<=-2 AND price z<=-1 → LONG."""
    n_new = 0
    for sym in OI_CAPIT_SYMBOLS:
        try:
            df = await fetch_klines(sym, "4h", 90)
            oi = await fetch_historical_metrics(sym, 90)
        except Exception:
            continue
        if df is None or oi is None or len(df) < 130:
            continue
        oi = oi.copy()
        oi['timestamp'] = pd.to_datetime(oi['timestamp']).astype('datetime64[ns]')
        df['open_time'] = pd.to_datetime(df['open_time']).astype('datetime64[ns]')
        m = pd.merge_asof(df[['open_time','close']].sort_values('open_time'),
                          oi[['timestamp','oi']].rename(columns={'timestamp':'open_time'}).sort_values('open_time'),
                          on='open_time', direction='backward')
        m['ret_n'] = m['close'].pct_change(6)
        m['oi_delta_n'] = m['oi'].pct_change(6)
        w = OI_CAPIT_PARAMS['window']
        ret_z = (m['ret_n'] - m['ret_n'].rolling(w).mean()) / (m['ret_n'].rolling(w).std() + 1e-10)
        oi_z = (m['oi_delta_n'] - m['oi_delta_n'].rolling(w).mean()) / (m['oi_delta_n'].rolling(w).std() + 1e-10)
        last_idx = len(m) - 1
        if not (np.isfinite(oi_z.iloc[last_idx]) and np.isfinite(ret_z.iloc[last_idx])):
            continue
        bar_time = m['open_time'].iloc[last_idx].isoformat()
        last_processed = state['last_processed_bar'].get(f"OI_CAPIT_{sym}", "")
        if bar_time <= last_processed:
            continue
        state['last_processed_bar'][f"OI_CAPIT_{sym}"] = bar_time
        # Trigger: OI capit pattern
        if oi_z.iloc[last_idx] > -OI_CAPIT_PARAMS['z_thresh'] or ret_z.iloc[last_idx] > -OI_CAPIT_PARAMS['ret_z_thresh']:
            continue
        close = float(m['close'].iloc[last_idx])
        size_usd = state['equity_usd'] * weight / len(OI_CAPIT_SYMBOLS) * state['leverage']
        position = {
            "entry_bar": bar_time, "symbol": sym, "strategy": "OI_capit",
            "side": "long", "entry_price": close,
            "sl": close * (1 - OI_CAPIT_PARAMS['sl']),
            "tp": close * (1 + OI_CAPIT_PARAMS['tp']),
            "expiry_bar_offset": OI_CAPIT_PARAMS['hold_bars'],
            "size_usd": size_usd,
        }
        state['open_positions'].append(position)
        n_new += 1
        print(f"  [OI_CAPIT NEW] {sym:<10} LONG entry=${close:.4f} oi_z={float(oi_z.iloc[last_idx]):.2f} ret_z={float(ret_z.iloc[last_idx]):.2f}")
    return n_new


async def main():
    t0 = time.time()
    print(f"=== 4-way Paper Trade Snapshot — {datetime.now().isoformat()} ===")
    state = load_or_init_state()
    print(f"  Strategy: {state.get('strategy', 'N/A')}")
    print(f"  Initial: ${state['initial_capital_usd']:.0f} | Current equity: ${state['equity_usd']:.2f}")
    print(f"  Open positions: {len(state['open_positions'])}")

    # First close any positions due
    print("\n[Managing existing positions]")
    n_closed, pnl_closed = await manage_open_positions(state)
    print(f"  Closed: {n_closed}, total PnL: ${pnl_closed:+.2f}")

    # Then process new signals (6 axes — v3)
    print("\n[Generating new signals — 6 strategy axes (v3)]")
    btc_4h = await get_btc_volz_4h()
    btc_8h = await get_btc_volz_8h()

    n_atr = await process_atr_strategy(state, btc_4h, W_ATR)
    n_fopd = await process_fopd_strategy(state, W_FOPD)
    n_bonk = await process_8h_meme_single(state, btc_8h, "BONKUSDT", W_BONK_8H)
    n_shib = await process_8h_meme_single(state, btc_8h, "SHIBUSDT", W_SHIB_8H)
    n_vol_mr = await process_vol_mr_strategy(state, W_VOL_MR)
    n_oi = await process_oi_capit_strategy(state, W_OI_CAPIT)  # Wave K49 NEW axis

    total_new = n_atr + n_fopd + n_bonk + n_shib + n_vol_mr + n_oi
    print(f"\n  Total new signals: {total_new}")
    print(f"  Currently open: {len(state['open_positions'])}")

    # Snapshot
    state['snapshots'].append({
        "snapshot_time": datetime.now(timezone(timedelta(hours=9))).strftime("%Y-%m-%d %H:%M JST"),
        "equity_usd": round(state['equity_usd'], 2),
        "n_open": len(state['open_positions']),
        "n_closed_this_run": n_closed,
        "pnl_closed_this_run_usd": round(pnl_closed, 2),
        "n_new_signals_this_run": total_new,
        "axes_signals": {"ATR": n_atr, "FOPD": n_fopd, "BONK_8H": n_bonk, "SHIB_8H": n_shib, "vol_MR": n_vol_mr, "OI_capit": n_oi},
        "total_closed_trades": len(state['closed_trades']),
    })

    save_state(state)
    print(f"\nSaved. Runtime {time.time()-t0:.1f}s")


# Single-symbol 8H Meme processor (vertical refactor since BONK and SHIB are separate)
async def process_8h_meme_single(state, btc_volz_8h, symbol, weight):
    df_4h = await fetch_klines(symbol, "4h", 90)
    df_8h = aggregate_4h_to_8h(df_4h)
    sig = atr_ratio_signal(df_8h, **ATR_PARAMS_8H)
    btc_idx = btc_volz_8h.set_index('open_time')
    aligned = btc_idx.reindex(df_8h['open_time'], method='ffill')['volz'].values
    bad = pd.Series(aligned, index=sig.index).fillna(False) >= VOL_Z
    sig[bad] = 0
    last_idx = len(df_8h) - 1
    bar_time = df_8h['open_time'].iloc[last_idx].isoformat()
    last_processed = state['last_processed_bar'].get(f"8H_{symbol}", "")
    if bar_time <= last_processed:
        return 0
    state['last_processed_bar'][f"8H_{symbol}"] = bar_time
    sig_val = int(sig.iloc[last_idx])
    close = float(df_8h['close'].iloc[last_idx])
    if sig_val == 0:
        return 0
    size_usd = state['equity_usd'] * weight * state['leverage']
    position = {
        "entry_bar": bar_time, "symbol": symbol, "strategy": "ATR_8H",
        "side": "long" if sig_val > 0 else "short", "entry_price": close,
        "sl": close * (1 - 0.04) if sig_val > 0 else close * (1 + 0.04),
        "tp": close * (1 + 0.08) if sig_val > 0 else close * (1 - 0.08),
        "expiry_bar_offset": 12, "size_usd": size_usd,
    }
    state['open_positions'].append(position)
    print(f"  [ATR_8H NEW] {symbol:<10} {position['side']:<5} entry=${close:.6f}")
    return 1


if __name__ == "__main__":
    asyncio.run(main())
