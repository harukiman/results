"""RCSPL feature extraction — 40+ hand-crafted features from a chart snippet.

Input: past M-bar window (DataFrame with open/high/low/close/volume).
Output: feature vector (numpy array).

All features computed strictly within the window — no look-ahead.
"""
import numpy as np
import pandas as pd


def extract_features(window: pd.DataFrame, symbol_id: int = 0, n_symbols: int = 15,
                     btc_concurrent_ret: float = 0.0, rv_tercile: int = 1) -> np.ndarray:
    """Extract feature vector from a single chart snippet.

    Args:
        window: DataFrame with columns open, high, low, close, volume (M rows)
        symbol_id: integer 0..n_symbols-1 for one-hot
        n_symbols: total symbols (for one-hot dimension)
        btc_concurrent_ret: BTC return over same window
        rv_tercile: 0/1/2 for low/mid/high realized vol regime
    Returns:
        feature vector (np.ndarray)
    """
    c = window['close'].values
    o = window['open'].values
    h = window['high'].values
    l = window['low'].values
    v = window['volume'].values

    log_c = np.log(c + 1e-10)
    returns = np.diff(log_c, prepend=log_c[0])
    M = len(c)

    feats = []

    # 1. Returns (cumulative over various horizons)
    feats.append(log_c[-1] - log_c[0])             # full window return
    feats.append(log_c[-1] - log_c[max(0, M-4)])   # last 4 bars
    feats.append(log_c[-1] - log_c[max(0, M-12)])  # last 12 bars
    feats.append(log_c[-1] - log_c[max(0, M-32)])  # last 32 bars

    # 2. Realized volatility
    feats.append(np.std(returns))                   # full window std
    feats.append(np.std(returns[-16:]) if M >= 16 else np.std(returns))  # recent
    # vol-of-vol: std of rolling std
    rolling_std = pd.Series(returns).rolling(8).std().dropna()
    feats.append(rolling_std.std() if len(rolling_std) > 1 else 0.0)

    # 3. Range
    hl_ratio = (h - l) / (c + 1e-10)
    feats.append(np.mean(hl_ratio))                # mean HL/C
    feats.append(np.max(hl_ratio))                 # max HL/C
    # Drawdown within window
    cummax = np.maximum.accumulate(c)
    dd_in_window = ((c - cummax) / (cummax + 1e-10)).min()
    feats.append(dd_in_window)
    # Runup within window
    cummin = np.minimum.accumulate(c)
    runup_in_window = ((c - cummin) / (cummin + 1e-10)).max()
    feats.append(runup_in_window)

    # 4. Shape
    # Linear slope of log-prices (per-bar)
    x = np.arange(M)
    slope, intercept = np.polyfit(x, log_c, 1)
    feats.append(slope)
    # R^2 of linear fit
    pred = slope * x + intercept
    ss_res = np.sum((log_c - pred) ** 2)
    ss_tot = np.sum((log_c - log_c.mean()) ** 2) + 1e-10
    r2 = 1 - ss_res / ss_tot
    feats.append(r2)
    # AR(1) of returns
    if M >= 4:
        ret_lag = np.corrcoef(returns[:-1], returns[1:])[0, 1] if np.std(returns) > 0 else 0.0
    else:
        ret_lag = 0.0
    feats.append(0.0 if np.isnan(ret_lag) else ret_lag)
    # Hurst proxy via RS analysis (simplified)
    if M >= 32:
        mean_ret = returns.mean()
        cumdev = np.cumsum(returns - mean_ret)
        R = cumdev.max() - cumdev.min()
        S = returns.std() + 1e-10
        rs = R / S
        hurst_proxy = np.log(rs + 1e-10) / np.log(M)
    else:
        hurst_proxy = 0.5
    feats.append(hurst_proxy)

    # 5. Volume
    log_v = np.log(v + 1)
    feats.append(np.mean(log_v))                   # mean log volume
    feats.append(np.std(log_v))                    # std log volume
    feats.append(log_v[-1] - np.mean(log_v))       # last vs mean (z-like)
    # Volume-return correlation (proxy for OBV-style signal)
    if M >= 4 and np.std(v) > 0 and np.std(returns) > 0:
        vr_corr = np.corrcoef(returns, log_v)[0, 1]
        feats.append(0.0 if np.isnan(vr_corr) else vr_corr)
    else:
        feats.append(0.0)

    # 6. Position within window
    cur_pos = (c[-1] - l.min()) / (h.max() - l.min() + 1e-10)
    feats.append(cur_pos)

    # 7. Cross-asset
    feats.append(btc_concurrent_ret)

    # 8. Regime
    feats.append(float(rv_tercile))

    # 9. Symbol one-hot
    onehot = np.zeros(n_symbols)
    if 0 <= symbol_id < n_symbols:
        onehot[symbol_id] = 1.0
    feats.extend(onehot)

    return np.asarray(feats, dtype=np.float64)


FEATURE_NAMES = [
    'ret_full', 'ret_4', 'ret_12', 'ret_32',
    'std_full', 'std_16', 'vol_of_vol',
    'mean_hl_ratio', 'max_hl_ratio', 'dd_in_window', 'runup_in_window',
    'slope', 'slope_r2', 'ar1', 'hurst_proxy',
    'mean_log_vol', 'std_log_vol', 'last_vol_dev', 'vol_ret_corr',
    'cur_pos_in_window',
    'btc_concurrent_ret', 'rv_tercile',
]


def get_feature_names(n_symbols: int = 15) -> list:
    return FEATURE_NAMES + [f'sym_{i}' for i in range(n_symbols)]
