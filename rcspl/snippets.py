"""RCSPL snippet sampling: build (X, y) dataset from OHLCV multi-symbol data."""
import asyncio
import sys
import numpy as np
import pandas as pd
sys.path.insert(0, '/Users/nekonaomichi/crypto-lab')
from engine.data import fetch_klines
from rcspl.features import extract_features

SYMBOLS_15 = [
    'BTCUSDT','ETHUSDT','SOLUSDT','BNBUSDT','XRPUSDT',
    'DOGEUSDT','ADAUSDT','LINKUSDT','AVAXUSDT','DOTUSDT',
    'TRXUSDT','LTCUSDT','UNIUSDT','INJUSDT','ARBUSDT',
]


def regime_label(rv: np.ndarray, t: int) -> int:
    """Tercile label for current realized vol vs past 360 bars."""
    if t < 60: return 1
    past_rv = rv[max(0, t-360):t]
    past_rv = past_rv[np.isfinite(past_rv)]
    if len(past_rv) < 30: return 1
    p33, p66 = np.percentile(past_rv, [33, 66])
    if rv[t] < p33: return 0
    elif rv[t] < p66: return 1
    else: return 2


async def build_dataset(M: int = 64, N: int = 12, days: int = 730,
                         stride: int = 1, min_history: int = 200,
                         symbols: list = None):
    """Build (X, y_binary, y_ret, meta) dataset across symbols.

    Args:
        M: past window size (bars)
        N: forward window for label (bars)
        stride: sampling stride (1 = every bar)
        min_history: required min bars before sampling
    """
    if symbols is None: symbols = SYMBOLS_15
    print(f'  Loading {len(symbols)} symbols ({days}d)...')
    dfs = {}
    for s in symbols:
        try:
            df = await fetch_klines(s, '4h', days)
            if df is None or len(df) < min_history + M + N: continue
            dfs[s] = df
        except Exception as e:
            print(f'    {s}: fetch fail {e}')
    print(f'  {len(dfs)} symbols loaded')

    # Compute BTC return per bar (for concurrent feature)
    btc = dfs.get('BTCUSDT')
    if btc is None:
        raise RuntimeError('BTC data required')
    btc_dates = pd.to_datetime(btc['open_time']).values
    btc_log_ret = np.log(btc['close'].values + 1e-10)

    rows_X, rows_y_bin, rows_y_ret, rows_meta = [], [], [], []
    for sym_idx, (sym, df) in enumerate(dfs.items()):
        c = df['close'].values
        dates = pd.to_datetime(df['open_time']).values
        if sym_idx >= len(SYMBOLS_15): continue
        # RV computation
        log_c = np.log(c + 1e-10)
        rets = np.diff(log_c, prepend=log_c[0])
        rv = pd.Series(rets).rolling(60).std().fillna(0).values
        # iterate
        n = len(df)
        for t in range(min_history, n - N, stride):
            window = df.iloc[t-M+1:t+1]
            if len(window) != M: continue
            # BTC concurrent return
            try:
                btc_t = np.searchsorted(btc_dates, dates[t])
                btc_t_start = np.searchsorted(btc_dates, dates[t-M+1])
                if btc_t < len(btc_log_ret):
                    btc_ret = btc_log_ret[btc_t] - btc_log_ret[max(0, btc_t_start)]
                else:
                    btc_ret = 0.0
            except Exception:
                btc_ret = 0.0
            tercile = regime_label(rv, t)
            try:
                X = extract_features(window, symbol_id=sym_idx,
                                      n_symbols=len(SYMBOLS_15),
                                      btc_concurrent_ret=btc_ret,
                                      rv_tercile=tercile)
            except Exception:
                continue
            # Label: forward N-bar log return after cost
            cost = 0.0014  # round-trip 0.14%
            try:
                fwd_ret = log_c[t + N] - log_c[t]
            except IndexError:
                continue
            # Flat band masking: skip if |fwd_ret| < 0.5 * ATR (use rv proxy)
            atr_proxy = rv[t]
            flat_band = 0.5 * atr_proxy * np.sqrt(N)
            if abs(fwd_ret) < flat_band:
                continue
            net_ret = fwd_ret - cost  # after cost (will not affect direction much)
            y_bin = 1 if net_ret > 0 else 0
            rows_X.append(X)
            rows_y_bin.append(y_bin)
            rows_y_ret.append(fwd_ret)
            rows_meta.append({'symbol': sym, 'sym_idx': sym_idx, 't': int(t),
                              'date': str(dates[t]), 'rv_tercile': tercile})

    X_arr = np.stack(rows_X)
    y_bin_arr = np.array(rows_y_bin)
    y_ret_arr = np.array(rows_y_ret)
    meta_df = pd.DataFrame(rows_meta)
    print(f'  Built dataset: {X_arr.shape[0]} samples × {X_arr.shape[1]} features')
    return X_arr, y_bin_arr, y_ret_arr, meta_df
