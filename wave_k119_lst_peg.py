#!/usr/bin/env python3
"""
Wave K119 — LST Peg-Break De-Leveraging Signal (LST-PBDS)

Hypothesis (from onchain-analyst TOP2):
  ETH liquid staking tokens (stETH, weETH, rsETH) often trade slightly
  below ETH on Curve.fi. When the peg breaks by > 0.3-0.5% (LST/ETH
  ratio dropping below 0.995-0.997), this signals forced unwinding of
  looping leverage stacks (~$30B in 2024-25). The signal predicts
  4-24h ETH spot/perp weakness.

  Reference events:
    * 2024-05  ezETH depeg
    * 2025-01  weETH wobble
    * (Older: May 2022 stETH-Celsius depeg, not in our 2024-26 window)

Data path attempts (documented in output):
  1. Curve.fi getPools/ethereum/main — CURRENT-state only (no history)
  2. Curve.fi getSubgraphData/ethereum — historical, very heavy, often 404
  3. DefiLlama coins price chart (https://coins.llama.fi/chart/...)
     supports paginated 4h-resolution prices per token contract on
     Ethereum. THIS IS WHAT WE USED.
  4. CoinGecko market_chart (vs_currency=eth) — works for staked-ether
     but free tier capped at 365 days. We use it for validation only.

Real peg observable:
  We fetch LST token PRICES IN USD from DefiLlama (which itself sources
  from on-chain DEX TWAPs incl. Curve, Uniswap V3, Balancer) and WETH
  price in USD on the same grid. Peg ratio = LST_USD / WETH_USD.
  Peg deviation (in bp) = (ratio - peg_baseline) * 10000, where
  peg_baseline is the trailing-30d median ratio (so we measure deviation
  from each LST's *typical* rate, not from 1.000 — important because
  wstETH/weETH carry yield drift, while pure stETH is rebasing 1:1).

Signal candidates:
  * pegdev_min_lst        = minimum over LSTs of peg deviation (most stressed)
  * pegdev_pct_below_eth  = fraction of LSTs currently > 0.3% below baseline
  * pegdev_rolling_5bar_min = minimum over last 5 bars
  * pegdev_z              = z-score vs 30d trailing distribution
  * deth_vol_z (proxy)    = ETH-realized-vol z-score MINUS BTC-vol z-score
                            (catches ETH-specific stress without LST data)

Strategy:
  When peg-break signal exceeds threshold T:
    SHORT ETHUSDT perp for hold_bars (4h grid: 1, 3, 6 bars = 4h/12h/24h)
  Re-trigger logic preserves the held position.
  Costs: taker 0.04% + slip 0.03% per side; 0.14% round trip.

Audit (§6 mini):
  * 70/30 IS/OOS split
  * Threshold sensitivity (T grid)
  * Walk-forward 4 folds
  * Block bootstrap CI (block=10, n=500) on OOS
  * Permutation test (block-shuffle, n=500)
  * DSR with N_trials = configs tested
"""
from __future__ import annotations

import json
import math
import sys
import time
import traceback
import warnings
from pathlib import Path
from typing import Any

import httpx
import numpy as np
import pandas as pd
from scipy import stats

warnings.filterwarnings('ignore')

# --------------------------- CONFIG ---------------------------------
ROOT = Path('/Users/nekonaomichi/crypto-lab')
CACHE = ROOT / 'cache'
OUT_JSON = ROOT / 'wave_k119_lst_peg.json'
OUT_CURVES = ROOT / 'wave_k119_curves.json'

ETH_PRICE_PARQUET = CACHE / 'ETHUSDT_4h_1200d.parquet'
BTC_PRICE_PARQUET = CACHE / 'BTCUSDT_4h_1200d.parquet'

# LST token contracts on Ethereum (DefiLlama coin id format)
LST_TOKENS = {
    'stETH':   '0xae7ab96520de3a18e5e111b5eaab095312d7fe84',   # Lido stETH (rebasing -> mostly ~1:1 ETH)
    'wstETH':  '0x7f39c581f595b53c5cb19bd0b3f8da6c935e2ca0',   # wrapped stETH (yield-bearing -> drifts up vs ETH)
    'weETH':   '0xcd5fe23c85820f7b72d0926fc9b05b43e359b7ee',   # ether.fi weETH
    'rsETH':   '0xa1290d69c65a6fe4df752f95823fae25cb99e5a7',   # Kelp rsETH
    'ezETH':   '0xbf5495efe5db9ce00f80364c8b423567e58d2110',   # Renzo ezETH (slow on llama API; capped at 1 retry)
}
# Per-token max wall-time for fetch (sec). Tokens with intermittent endpoint
# latency get a short cap so we don't burn 10 min on a single asset.
LST_FETCH_TIMEOUT_BUDGET = {
    'ezETH': 90,   # Llama can be very slow on this contract
}
LST_DEFAULT_BUDGET = 240
WETH = '0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2'

LLAMA_CHART = 'https://coins.llama.fi/chart'
LLAMA_MAX_POINTS = 500  # per-coin per request limit
# 4h bars over 24 months ≈ 4380 bars => need 4380/250 ≈ 18 chunks per coin if paired

CURVE_POOLS_URL = 'https://api.curve.fi/api/getPools/ethereum/main'
CURVE_SUBGRAPH_URL = 'https://api.curve.fi/api/getSubgraphData/ethereum'

# Trading costs
TAKER = 0.0004
SLIPPAGE = 0.0003
ONE_SIDE = TAKER + SLIPPAGE
ROUND_TRIP = 2 * ONE_SIDE

BARS_PER_DAY = 6  # 4h bars
SEED = 42
rng = np.random.default_rng(SEED)


def log(msg: str):
    print(f"[K119] {msg}", flush=True)


# --------------------------- DATA PROBES ----------------------------
def probe_curve_pools(timeout: float = 15.0) -> dict:
    """Document Curve.fi current-state API accessibility."""
    try:
        r = httpx.get(CURVE_POOLS_URL, timeout=timeout, follow_redirects=True)
        ok = r.status_code == 200
        info = {'status': r.status_code, 'ok': ok}
        if ok:
            d = r.json()
            pools = d.get('data', {}).get('poolData', [])
            lst_pools = [p.get('name') for p in pools
                         if any(s in p.get('name', '').lower()
                                for s in ('steth', 'frxeth', 'eeth'))]
            info['n_pools'] = len(pools)
            info['lst_pools_found'] = lst_pools[:10]
            info['note'] = ('Curve.fi returns CURRENT pool state only '
                            '(virtual_price, current balances). No '
                            'historical peg series.')
        return info
    except Exception as e:
        return {'status': -1, 'ok': False, 'err': f'{type(e).__name__}: {e}'}


def probe_curve_subgraph(timeout: float = 15.0) -> dict:
    """Curve.fi internal subgraph dump — usually 5xx/timeout."""
    try:
        r = httpx.get(CURVE_SUBGRAPH_URL, timeout=timeout, follow_redirects=True)
        return {'status': r.status_code,
                'ok': r.status_code == 200,
                'note': 'Curve.fi internal subgraph dump (historic). '
                        'In practice times out or 5xx on free access.'}
    except Exception as e:
        return {'status': -1, 'ok': False,
                'err': f'{type(e).__name__}: {e}'}


def probe_coingecko_steth(timeout: float = 20.0) -> dict:
    """CoinGecko free tier — limited to 365d but useful for validation."""
    url = ('https://api.coingecko.com/api/v3/coins/staked-ether/'
           'market_chart?vs_currency=eth&days=365')
    try:
        r = httpx.get(url, timeout=timeout, follow_redirects=True)
        if r.status_code != 200:
            return {'status': r.status_code, 'ok': False,
                    'body_head': r.text[:200]}
        d = r.json()
        prices = d.get('prices', [])
        return {'status': 200, 'ok': True,
                'n_points': len(prices),
                'first_ts': prices[0][0] if prices else None,
                'last_ts': prices[-1][0] if prices else None,
                'note': 'Free tier capped at 365d.'}
    except Exception as e:
        return {'status': -1, 'ok': False,
                'err': f'{type(e).__name__}: {e}'}


# --------------------------- DATA FETCH -----------------------------
def fetch_llama_chart_chunk(coins: list[str], start: int, span: int,
                            period: str = '4h',
                            timeout: float = 30.0) -> dict:
    """One chunk of llama coins chart. coins = list of 'ethereum:0x...'."""
    key = ','.join(coins)
    url = f'{LLAMA_CHART}/{key}'
    params = {'start': start, 'span': span, 'period': period}
    r = httpx.get(url, params=params, timeout=timeout, follow_redirects=True)
    r.raise_for_status()
    return r.json()


def fetch_llama_pair_history(lst_addr: str, weth_addr: str,
                             start_ts: int, end_ts: int,
                             period_sec: int = 4 * 3600,
                             wall_budget_sec: float = 240.0) -> pd.DataFrame:
    """Fetch paginated 4h prices for a LST and WETH between start_ts and end_ts.
       Returns DataFrame index=UTC datetime cols=[lst_usd, weth_usd, ratio].
       Hard wall-time budget so a slow endpoint can't burn all our runtime."""
    span_per_chunk = 240  # leaves margin under 250 (=500 / 2 coins)
    coins = [f'ethereum:{lst_addr}', f'ethereum:{weth_addr}']
    cur = start_ts
    all_lst = []
    all_weth = []
    n_chunks = 0
    t_start = time.time()
    n_fail = 0
    while cur < end_ts:
        if time.time() - t_start > wall_budget_sec:
            log(f"  wall budget {wall_budget_sec:.0f}s exceeded after "
                f"{n_chunks} chunks — returning partial data")
            break
        try:
            d = fetch_llama_chart_chunk(coins, cur, span_per_chunk, timeout=15.0)
        except Exception as e:
            n_fail += 1
            if n_fail >= 3:
                log(f"  3 consecutive failures, giving up on this LST")
                break
            cur += span_per_chunk * period_sec
            continue
        n_fail = 0
        lst_key = f'ethereum:{lst_addr}'
        weth_key = f'ethereum:{weth_addr}'
        if lst_key not in d.get('coins', {}) or weth_key not in d.get('coins', {}):
            cur += span_per_chunk * period_sec
            continue
        lst_pr = d['coins'][lst_key]['prices']
        weth_pr = d['coins'][weth_key]['prices']
        all_lst.extend(lst_pr)
        all_weth.extend(weth_pr)
        n_chunks += 1
        # advance cur to last timestamp + period
        if lst_pr:
            last_ts = max(lst_pr[-1]['timestamp'], weth_pr[-1]['timestamp'])
            new_cur = last_ts + period_sec
            if new_cur <= cur:
                cur += span_per_chunk * period_sec
            else:
                cur = new_cur
        else:
            cur += span_per_chunk * period_sec
        time.sleep(0.1)  # be polite

    if not all_lst or not all_weth:
        return pd.DataFrame()
    lst_df = pd.DataFrame(all_lst)
    weth_df = pd.DataFrame(all_weth)
    lst_df['ts'] = pd.to_datetime(lst_df['timestamp'], unit='s', utc=True)
    weth_df['ts'] = pd.to_datetime(weth_df['timestamp'], unit='s', utc=True)
    # Round to 4h grid (DefiLlama timestamps drift a few seconds)
    lst_df['bucket'] = lst_df['ts'].dt.floor('4H')
    weth_df['bucket'] = weth_df['ts'].dt.floor('4H')
    lst_df = lst_df.groupby('bucket')['price'].last().rename('lst_usd')
    weth_df = weth_df.groupby('bucket')['price'].last().rename('weth_usd')
    out = pd.concat([lst_df, weth_df], axis=1).dropna()
    out = out.sort_index()
    out['ratio'] = out['lst_usd'] / out['weth_usd']
    log(f"  fetched {n_chunks} chunks  -> {len(out)} aligned bars")
    return out


# --------------------------- PRICES ---------------------------------
def load_price(path: Path) -> pd.Series:
    df = pd.read_parquet(path)
    df = df.set_index('open_time').sort_index()
    df = df[~df.index.duplicated(keep='last')]
    if df.index.tz is None:
        df.index = df.index.tz_localize('UTC')
    return df['close'].astype(float)


# --------------------------- SIGNALS --------------------------------
def build_peg_signals(lst_panels: dict[str, pd.DataFrame],
                      grid: pd.DatetimeIndex) -> pd.DataFrame:
    """Build composite peg-deviation signals over a 4h grid.

    Each lst_panels[name] is a df with 'ratio' (LST_USD / WETH_USD).
    We compute peg_dev_bp (vs trailing 30d median = 180 bars) per LST,
    then aggregate.
    """
    devs = {}
    for name, df in lst_panels.items():
        s = df['ratio'].reindex(grid).ffill(limit=2)
        # Trailing baseline = 30d (180 bars) median ratio
        baseline = s.rolling(180, min_periods=30).median()
        peg_dev_bp = (s / baseline - 1.0) * 10000.0
        # Robust z-score using trailing 30d MAD
        med = s.rolling(180, min_periods=30).median()
        mad = (s - med).abs().rolling(180, min_periods=30).median()
        z = (s - med) / (1.4826 * mad.replace(0, np.nan))
        devs[f'{name}_dev_bp'] = peg_dev_bp
        devs[f'{name}_z'] = z
    df = pd.DataFrame(devs, index=grid)

    # Aggregations
    dev_cols = [c for c in df.columns if c.endswith('_dev_bp')]
    z_cols = [c for c in df.columns if c.endswith('_z')]
    df['min_dev_bp'] = df[dev_cols].min(axis=1)   # most negative (worst peg break)
    df['mean_dev_bp'] = df[dev_cols].mean(axis=1)
    df['min_z'] = df[z_cols].min(axis=1)
    df['frac_below_30bp'] = (df[dev_cols] < -30).sum(axis=1) / len(dev_cols)
    df['frac_below_50bp'] = (df[dev_cols] < -50).sum(axis=1) / len(dev_cols)
    # Rolling 5-bar min (catches brief depegs that ffill might smooth)
    df['min_dev_bp_5bar'] = df['min_dev_bp'].rolling(5, min_periods=1).min()
    df['min_z_5bar'] = df['min_z'].rolling(5, min_periods=1).min()
    return df


def build_eth_vol_proxy(eth: pd.Series, btc: pd.Series) -> pd.Series:
    """Backup proxy: ETH-specific stress = ETH realized vol z minus BTC vol z.
       Computed on rolling 30-bar (5d) window."""
    eth_ret = eth.pct_change()
    btc_ret = btc.pct_change()
    eth_vol = eth_ret.rolling(30).std()
    btc_vol = btc_ret.rolling(30).std()
    eth_vol_z = (eth_vol - eth_vol.rolling(180).mean()) / eth_vol.rolling(180).std()
    btc_vol_z = (btc_vol - btc_vol.rolling(180).mean()) / btc_vol.rolling(180).std()
    return (eth_vol_z - btc_vol_z).rename('eth_specific_stress')


# --------------------------- BACKTEST -------------------------------
def backtest_short_on_breach(price: pd.Series, signal: pd.Series,
                             threshold: float,
                             direction: str = 'below',
                             hold_bars: int = 6,
                             cost_per_side: float = ONE_SIDE) -> dict:
    """SHORT ETH for hold_bars when signal crosses threshold in `direction`.

    direction='below': trigger when signal < threshold (i.e. peg dev_bp < -30)
    direction='above': trigger when signal > threshold (i.e. z > 2.0)
    """
    idx = price.index
    px = price.values
    sig = signal.reindex(idx).values
    n = len(idx)
    pos = np.zeros(n)
    held = 0
    for i in range(n):
        s = sig[i]
        if not np.isnan(s):
            triggered = (s < threshold) if direction == 'below' else (s > threshold)
            if triggered:
                held = hold_bars  # (re-set or extend)
        if held > 0:
            pos[i] = -1.0
            held -= 1
        else:
            pos[i] = 0.0

    bar_ret = np.diff(np.log(px))
    bar_ret = np.concatenate([[0.0], bar_ret])
    pos_eff = np.concatenate([[0.0], pos[:-1]])
    pnl = pos_eff * bar_ret
    dpos = np.abs(np.diff(np.concatenate([[0.0], pos])))
    cost = dpos * cost_per_side
    pnl_net = pnl - cost
    rets = pd.Series(pnl_net, index=idx, name='ret')
    equity = (1.0 + rets).cumprod()
    return {
        'returns': rets,
        'equity': equity,
        'position': pd.Series(pos, index=idx, name='pos'),
        'n_trades': int((dpos > 0).sum()),
        'exposure_frac': float((np.abs(pos) > 0).mean()),
    }


def metrics(rets: pd.Series) -> dict:
    bars_per_year = 365 * BARS_PER_DAY
    if rets is None or len(rets) < 10:
        return {k: 0.0 for k in
                ['sharpe', 'sortino', 'calmar', 'maxdd',
                 'win_rate', 'ann_ret', 'ann_vol']} | {'n_bars': 0}
    r = rets.dropna().values
    if r.size < 10 or r.std() == 0:
        return {'sharpe': 0.0, 'sortino': 0.0, 'calmar': 0.0,
                'maxdd': 0.0, 'win_rate': 0.0, 'ann_ret': 0.0,
                'ann_vol': 0.0, 'n_bars': int(r.size)}
    mu, sd = r.mean(), r.std()
    sharpe = mu / sd * np.sqrt(bars_per_year)
    downside = r[r < 0].std() if (r < 0).any() else 0.0
    sortino = (mu / downside) * np.sqrt(bars_per_year) if downside > 0 else 0.0
    equity = (1.0 + r).cumprod()
    peak = np.maximum.accumulate(equity)
    dd = float(((equity / peak) - 1.0).min())
    ann_ret = float(equity[-1] ** (bars_per_year / len(r)) - 1.0)
    calmar = ann_ret / abs(dd) if dd < 0 else 0.0
    win = float((r > 0).mean())
    return {'sharpe': float(sharpe), 'sortino': float(sortino),
            'calmar': float(calmar), 'maxdd': dd, 'win_rate': win,
            'ann_ret': ann_ret, 'ann_vol': float(sd * np.sqrt(bars_per_year)),
            'n_bars': int(len(r))}


def block_bootstrap_sharpe(rets: pd.Series, block: int = 10,
                           n: int = 500) -> dict:
    arr = rets.dropna().values
    L = len(arr)
    if L < block * 5:
        return {'ci_lo': 0.0, 'ci_hi': 0.0, 'mean': 0.0, 'median': 0.0}
    bars_per_year = 365 * BARS_PER_DAY
    n_blocks = L // block
    sharpes = []
    for _ in range(n):
        starts = rng.integers(0, L - block + 1, size=n_blocks)
        sample = np.concatenate([arr[s:s + block] for s in starts])
        if sample.std() == 0:
            sharpes.append(0.0); continue
        sharpes.append(sample.mean() / sample.std() * np.sqrt(bars_per_year))
    sh = np.array(sharpes)
    return {'mean': float(sh.mean()),
            'median': float(np.median(sh)),
            'ci_lo': float(np.percentile(sh, 2.5)),
            'ci_hi': float(np.percentile(sh, 97.5))}


def permutation_test(price: pd.Series, signal: pd.Series,
                     threshold: float, direction: str, hold_bars: int,
                     observed_sharpe: float, n: int = 500) -> tuple[float, np.ndarray]:
    sig = signal.reindex(price.index).values.copy()
    valid = ~np.isnan(sig)
    if valid.sum() < 50:
        return 1.0, np.zeros(n)
    block = 30
    L = len(sig)
    bars_per_year = 365 * BARS_PER_DAY
    null_sh = np.zeros(n)
    for trial in range(n):
        n_blocks = L // block + 1
        starts = rng.integers(0, L - block, size=n_blocks)
        shuffled = np.concatenate([sig[s:s + block] for s in starts])[:L]
        shuf_ser = pd.Series(shuffled, index=price.index)
        res = backtest_short_on_breach(price, shuf_ser, threshold,
                                       direction=direction,
                                       hold_bars=hold_bars)
        r = res['returns'].dropna().values
        if r.size < 10 or r.std() == 0:
            null_sh[trial] = 0.0; continue
        null_sh[trial] = r.mean() / r.std() * np.sqrt(bars_per_year)
    pval = float((null_sh >= observed_sharpe).mean())
    return pval, null_sh


def walk_forward_4fold(price: pd.Series, signal: pd.Series,
                       threshold: float, direction: str,
                       hold_bars: int) -> dict:
    n = len(price)
    fold = n // 4
    fold_sh = []
    for f in range(4):
        s = f * fold
        e = (f + 1) * fold if f < 3 else n
        p_sub = price.iloc[s:e]
        sig_sub = signal.reindex(p_sub.index)
        if sig_sub.notna().sum() < 50:
            fold_sh.append(0.0); continue
        res = backtest_short_on_breach(p_sub, sig_sub, threshold,
                                       direction=direction, hold_bars=hold_bars)
        fold_sh.append(metrics(res['returns'])['sharpe'])
    return {'fold_sharpes': fold_sh,
            'mean': float(np.mean(fold_sh)),
            'std': float(np.std(fold_sh))}


def deflated_sharpe(observed_sh: float, n_trials: int,
                    n_obs: int, sk: float = 0.0, ku: float = 3.0) -> float:
    """Bailey & Lopez de Prado Deflated Sharpe approximation."""
    if n_obs < 10 or n_trials < 2:
        return 0.0
    emc = 0.5772156649
    expected_max = math.sqrt(2.0 * math.log(n_trials)) - \
        emc / math.sqrt(2.0 * math.log(n_trials))
    # variance of sharpe estimator (Mertens)
    var_sh = (1 - sk * observed_sh + (ku - 1) / 4 * observed_sh ** 2) / (n_obs - 1)
    if var_sh <= 0:
        return 0.0
    z = (observed_sh - expected_max * math.sqrt(var_sh)) / math.sqrt(var_sh)
    return float(stats.norm.cdf(z))


def event_study(price: pd.Series, signal: pd.Series, threshold: float,
                direction: str,
                horizons_bars=(1, 3, 6, 18, 36)) -> dict:
    sig = signal.reindex(price.index)
    log_px = np.log(price)
    out = {'event': {}, 'baseline': {}}
    if direction == 'below':
        ev_mask = sig < threshold
    else:
        ev_mask = sig > threshold
    base_mask = (~ev_mask) & sig.notna()
    for h in horizons_bars:
        fwd = log_px.shift(-h) - log_px
        for label, mask in [('event', ev_mask), ('baseline', base_mask)]:
            vals = fwd[mask].dropna()
            if len(vals) < 5:
                out[label][f'{h}bar'] = {'n': int(len(vals)), 'mean': 0.0,
                                         'median': 0.0, 't': 0.0, 'p': 1.0}
                continue
            t, p = stats.ttest_1samp(vals.values, 0.0)
            out[label][f'{h}bar'] = {
                'n': int(len(vals)),
                'mean': float(vals.mean()),
                'median': float(vals.median()),
                't': float(t),
                'p': float(p),
            }
    return out


# --------------------------- MAIN -----------------------------------
def main():
    t0 = time.time()
    out: dict[str, Any] = {
        'wave': 'K119',
        'task': 'lst_peg_break_de_leveraging_signal',
        'hypothesis': (
            'When ETH LST peg breaks (LST/ETH ratio falls below trailing '
            'baseline by > 30-50bp), forced unwinding of looped-leverage '
            'stacks predicts 4-24h ETH spot/perp downside.'),
        'data_attempts': [],
        'data_source_used': None,
        'real_peg_or_proxy': None,
        'caveat': '',
    }

    # 1. Probe Curve.fi (documented unaccessibility for history)
    log("probe 1: Curve.fi getPools (current state only)...")
    p1 = probe_curve_pools()
    out['data_attempts'].append({'source': 'curve.fi getPools', **p1})
    log(f"  -> ok={p1.get('ok')} status={p1.get('status')}")

    log("probe 2: Curve.fi getSubgraphData (historical)...")
    p2 = probe_curve_subgraph()
    out['data_attempts'].append({'source': 'curve.fi getSubgraphData', **p2})
    log(f"  -> ok={p2.get('ok')} status={p2.get('status')}")

    log("probe 3: CoinGecko market_chart vs ETH (validation only, 365d cap)...")
    p3 = probe_coingecko_steth()
    out['data_attempts'].append({'source': 'coingecko market_chart', **p3})
    log(f"  -> ok={p3.get('ok')} n={p3.get('n_points', 0)}")

    # 2. Pricing data (the actual backtest universe)
    log("loading ETHUSDT and BTCUSDT 4h price caches...")
    eth = load_price(ETH_PRICE_PARQUET)
    btc = load_price(BTC_PRICE_PARQUET)
    common = eth.index.intersection(btc.index)
    eth = eth.loc[common]
    btc = btc.loc[common]
    log(f"  ETH/BTC bars on common 4h grid: {len(eth)}  "
        f"{eth.index.min()} -> {eth.index.max()}")

    # Restrict backtest universe to 2024-05-01 -> end of cache (~ 2026-05)
    win_start = pd.Timestamp('2024-05-01', tz='UTC')
    eth = eth.loc[eth.index >= win_start]
    btc = btc.loc[btc.index >= win_start]
    log(f"  windowed (>=2024-05-01): {len(eth)} bars")
    grid = eth.index

    # 3. Real peg data fetch (DefiLlama coins chart)
    log("probe 4: DefiLlama coins/chart for LST/WETH USD prices (4h)...")
    win_start_ts = int(win_start.timestamp())
    win_end_ts = int(eth.index.max().timestamp()) + 4 * 3600
    log(f"  fetching {(win_end_ts - win_start_ts) // 86400} days of history")

    lst_panels = {}
    fetch_status = {}
    for name, addr in LST_TOKENS.items():
        log(f"  fetching {name} ({addr[:10]}...)...")
        budget = LST_FETCH_TIMEOUT_BUDGET.get(name, LST_DEFAULT_BUDGET)
        try:
            df = fetch_llama_pair_history(addr, WETH, win_start_ts, win_end_ts,
                                          wall_budget_sec=budget)
            if not df.empty:
                lst_panels[name] = df
                fetch_status[name] = {
                    'ok': True, 'n_bars': len(df),
                    'first': str(df.index.min()), 'last': str(df.index.max()),
                    'ratio_mean': float(df['ratio'].mean()),
                    'ratio_min': float(df['ratio'].min()),
                    'ratio_p01': float(df['ratio'].quantile(0.01)),
                }
            else:
                fetch_status[name] = {'ok': False, 'n_bars': 0,
                                      'err': 'empty after merge'}
        except Exception as e:
            fetch_status[name] = {'ok': False, 'err': f'{type(e).__name__}: {e}'}
            log(f"    -> ERR: {e}")

    out['data_attempts'].append({'source': 'defillama coins/chart 4h',
                                 'per_token_status': fetch_status})
    n_real = sum(1 for s in fetch_status.values() if s.get('ok'))
    log(f"  real-peg LSTs fetched: {n_real}/{len(LST_TOKENS)}")

    # 4. Build signals
    if n_real >= 2:
        out['real_peg_or_proxy'] = 'REAL'
        out['data_source_used'] = 'DefiLlama coins/chart 4h LST USD prices'
        log("REAL peg data available -> building peg-deviation signals.")
        sig_df = build_peg_signals(lst_panels, grid)
        signals = {
            'min_dev_bp': sig_df['min_dev_bp'],
            'min_dev_bp_5bar': sig_df['min_dev_bp_5bar'],
            'mean_dev_bp': sig_df['mean_dev_bp'],
            'min_z': sig_df['min_z'],
            'min_z_5bar': sig_df['min_z_5bar'],
            'frac_below_30bp': sig_df['frac_below_30bp'],
            'frac_below_50bp': sig_df['frac_below_50bp'],
        }
        # Thresholds per-signal-type (direction matters)
        thresh_grid = {
            'min_dev_bp':       ('below', [-20, -30, -50, -100]),
            'min_dev_bp_5bar':  ('below', [-20, -30, -50, -100]),
            'mean_dev_bp':      ('below', [-10, -20, -30, -50]),
            'min_z':            ('below', [-1.5, -2.0, -2.5, -3.0]),
            'min_z_5bar':       ('below', [-1.5, -2.0, -2.5, -3.0]),
            'frac_below_30bp':  ('above', [0.2, 0.4, 0.6]),
            'frac_below_50bp':  ('above', [0.2, 0.4, 0.6]),
        }
        out['peg_signal_summary'] = {
            name: {
                'n_obs': int(s.dropna().shape[0]),
                'min': float(s.dropna().min()) if s.dropna().size > 0 else None,
                'p01': float(s.dropna().quantile(0.01)) if s.dropna().size > 0 else None,
                'p05': float(s.dropna().quantile(0.05)) if s.dropna().size > 0 else None,
                'p50': float(s.dropna().quantile(0.5)) if s.dropna().size > 0 else None,
                'p95': float(s.dropna().quantile(0.95)) if s.dropna().size > 0 else None,
            } for name, s in signals.items()
        }
    else:
        out['real_peg_or_proxy'] = 'PROXY'
        out['data_source_used'] = ('PROXY: ETH-specific realized-vol stress '
                                   '(eth_vol_z - btc_vol_z)')
        out['caveat'] = (
            "Real LST peg data could not be fetched. Using ETH-specific "
            "realized volatility stress as a NOISY proxy. This catches the "
            "same regime (ETH stress without BTC stress) but is NOT the "
            "same signal as actual on-chain peg deviation. Findings may "
            "NOT generalize to a real-peg implementation.")
        log("REAL peg data unavailable -> using vol proxy.")
        proxy = build_eth_vol_proxy(eth, btc)
        signals = {'eth_vol_specific_stress': proxy}
        thresh_grid = {
            'eth_vol_specific_stress': ('above', [1.0, 1.5, 2.0, 2.5]),
        }

    # 5. IS/OOS split
    n_bars = len(eth)
    split_i = int(n_bars * 0.7)
    is_end = eth.index[split_i - 1]
    log(f"IS bars: {split_i}  OOS bars: {n_bars - split_i}  IS end: {is_end}")

    # 6. Grid search (signal × direction × threshold × hold)
    HOLDS = [1, 3, 6]  # 4h, 12h, 24h
    grid_results = {}
    log("running IS grid search...")
    for sig_name, sig_series in signals.items():
        direction, thr_list = thresh_grid[sig_name]
        for thr in thr_list:
            for hold in HOLDS:
                is_price = eth.loc[:is_end]
                is_sig = sig_series.loc[:is_end]
                res = backtest_short_on_breach(is_price, is_sig, thr,
                                               direction=direction,
                                               hold_bars=hold)
                m = metrics(res['returns'])
                key = f"{sig_name}|dir={direction}|thr={thr}|hold={hold}"
                grid_results[key] = {
                    'sharpe': m['sharpe'], 'maxdd': m['maxdd'],
                    'ann_ret': m['ann_ret'], 'win_rate': m['win_rate'],
                    'n_trades': res['n_trades'],
                    'exposure': res['exposure_frac'],
                    'threshold': thr,
                    'direction': direction,
                }

    if not grid_results:
        log("Empty grid — exit.")
        out['error'] = 'empty_grid'
        with open(OUT_JSON, 'w') as f:
            json.dump(out, f, indent=2, default=str)
        return out

    # Best IS
    best_key = max(grid_results, key=lambda k: grid_results[k]['sharpe'])
    log(f"Best IS: {best_key}  Sh={grid_results[best_key]['sharpe']:.3f}")
    parts = best_key.split('|')
    best_sig = parts[0]
    best_dir = parts[1].split('=')[1]
    best_thr = float(parts[2].split('=')[1])
    best_hold = int(parts[3].split('=')[1])

    # 7. OOS eval
    log("running OOS with best IS combo...")
    oos_price = eth.loc[is_end + pd.Timedelta(hours=4):]
    oos_sig = signals[best_sig].loc[is_end + pd.Timedelta(hours=4):]
    oos_res = backtest_short_on_breach(oos_price, oos_sig, best_thr,
                                       direction=best_dir, hold_bars=best_hold)
    oos_m = metrics(oos_res['returns'])
    log(f"OOS Sharpe: {oos_m['sharpe']:.3f}  MaxDD: {oos_m['maxdd']:.3f}  "
        f"Trades: {oos_res['n_trades']}  Exp: {oos_res['exposure_frac']:.2%}")

    # Full-period equity (for chart)
    full_sig = signals[best_sig]
    full_res = backtest_short_on_breach(eth, full_sig, best_thr,
                                        direction=best_dir, hold_bars=best_hold)
    full_m = metrics(full_res['returns'])

    is_res = backtest_short_on_breach(eth.loc[:is_end],
                                      full_sig.loc[:is_end], best_thr,
                                      direction=best_dir, hold_bars=best_hold)

    # 8. Robustness
    log("walk-forward 4-fold...")
    wf = walk_forward_4fold(eth, full_sig, best_thr, best_dir, best_hold)
    log(f"  fold_sharpes: {[round(x,3) for x in wf['fold_sharpes']]}")

    log("block bootstrap OOS Sharpe CI (n=500)...")
    bb = block_bootstrap_sharpe(oos_res['returns'], block=10, n=500)
    log(f"  95% CI: [{bb['ci_lo']:.3f}, {bb['ci_hi']:.3f}]")

    log("permutation test OOS (n=500)...")
    pval, null_sh = permutation_test(oos_price, oos_sig, best_thr, best_dir,
                                     best_hold, oos_m['sharpe'], n=500)
    log(f"  p_value={pval:.4f}  null median={float(np.median(null_sh)):.3f}")

    # DSR
    dsr = deflated_sharpe(oos_m['sharpe'], n_trials=len(grid_results),
                          n_obs=len(oos_res['returns'].dropna()))
    log(f"  Deflated Sharpe (P[true>0] given multiple testing): {dsr:.3f}")

    # 9. Event study (full sample)
    log("event study...")
    es = event_study(eth, full_sig, best_thr, best_dir,
                     horizons_bars=(1, 3, 6, 18, 36))

    # 10. §6 mini gates
    gates = {
        'G1_oos_sharpe_gt_0.5': bool(oos_m['sharpe'] > 0.5),
        'G2_perm_pval_lt_0.05': bool(pval < 0.05),
        'G3_bootstrap_ci_lo_gt_0': bool(bb['ci_lo'] > 0.0),
        'G4_wf_consistency': bool(sum(s > 0 for s in wf['fold_sharpes']) >= 3),
        'G5_oos_calmar_gt_0.3': bool(oos_m['calmar'] > 0.3),
        'G6_max_dd_lt_30pct': bool(oos_m['maxdd'] > -0.30),
        'G7_n_trades_gt_20': bool(oos_res['n_trades'] > 20),
        'G8_dsr_gt_0.7': bool(dsr > 0.7),
    }
    passed = sum(gates.values())
    verdict = ('ACCEPT' if passed >= 7 else
               'CONDITIONAL' if passed >= 5 else
               'REJECT')

    elapsed = time.time() - t0
    log(f"elapsed: {elapsed:.1f}s")

    # --------------------- OUTPUT ----------------------------
    out['costs'] = {'taker': TAKER, 'slippage': SLIPPAGE,
                    'one_side': ONE_SIDE, 'round_trip': ROUND_TRIP}
    out['eth_bars'] = int(len(eth))
    out['eth_range'] = [str(eth.index.min()), str(eth.index.max())]
    out['signals_tested'] = list(signals.keys())
    out['grid_n_configs'] = len(grid_results)
    out['is_grid_top10'] = dict(
        sorted(grid_results.items(),
               key=lambda kv: -kv[1]['sharpe'])[:10])
    out['best_combo'] = {
        'signal': best_sig,
        'direction': best_dir,
        'threshold': best_thr,
        'hold_bars': best_hold,
        'hold_hours': best_hold * 4,
        'is_sharpe': grid_results[best_key]['sharpe'],
    }
    out['oos_metrics'] = oos_m
    out['oos_n_trades'] = oos_res['n_trades']
    out['oos_exposure'] = oos_res['exposure_frac']
    out['is_metrics'] = metrics(is_res['returns'])
    out['full_metrics'] = full_m
    out['walk_forward_4fold'] = wf
    out['block_bootstrap_oos'] = bb
    out['permutation_oos'] = {
        'p_value': pval,
        'null_mean': float(null_sh.mean()),
        'null_median': float(np.median(null_sh)),
        'null_p95': float(np.percentile(null_sh, 95)),
    }
    out['deflated_sharpe'] = dsr
    out['event_study'] = es
    out['gates'] = gates
    out['gates_passed'] = passed
    out['verdict'] = verdict
    out['elapsed_sec'] = elapsed

    with open(OUT_JSON, 'w') as f:
        json.dump(out, f, indent=2, default=str)
    log(f"wrote {OUT_JSON}")

    # ---- Curves file ----
    def downsample(s: pd.Series, n: int = 500) -> dict:
        if len(s) <= n:
            sel = s
        else:
            step = max(1, len(s) // n)
            sel = s.iloc[::step]
        return {str(t): float(v) for t, v in sel.items()}

    curves_out = {
        'wave': 'K119',
        'is_equity':   downsample(is_res['equity']),
        'oos_equity':  downsample(oos_res['equity']),
        'full_equity': downsample(full_res['equity']),
        'eth_price':   downsample(eth),
    }
    if out['real_peg_or_proxy'] == 'REAL':
        # downsample best peg signal too
        curves_out['best_signal_series'] = downsample(full_sig.dropna())
    else:
        curves_out['best_signal_series'] = downsample(full_sig.dropna())
    with open(OUT_CURVES, 'w') as f:
        json.dump(curves_out, f, indent=2, default=str)
    log(f"wrote {OUT_CURVES}")

    # Final summary
    print("\n" + "=" * 70)
    print("WAVE K119 — LST-PBDS FINAL SUMMARY")
    print("=" * 70)
    print(f"Data source: {out['data_source_used']}")
    print(f"Real or proxy: {out['real_peg_or_proxy']}")
    print(f"ETH bars: {out['eth_bars']}  range: {out['eth_range']}")
    print(f"\nBest combo: sig={best_sig} dir={best_dir} thr={best_thr} "
          f"hold={best_hold}bars ({best_hold * 4}h)")
    print(f"IS Sharpe : {grid_results[best_key]['sharpe']:.3f}")
    print(f"OOS Sharpe: {oos_m['sharpe']:.3f}  Sortino: {oos_m['sortino']:.3f}  "
          f"Calmar: {oos_m['calmar']:.3f}  MaxDD: {oos_m['maxdd']:.3f}")
    print(f"OOS Win%  : {oos_m['win_rate']:.3f}  Trades: {oos_res['n_trades']}  "
          f"Exposure: {oos_res['exposure_frac']:.2%}")
    print(f"WF 4-fold sharpes: {[round(x,3) for x in wf['fold_sharpes']]}")
    print(f"Block bootstrap 95% CI: [{bb['ci_lo']:.3f}, {bb['ci_hi']:.3f}]")
    print(f"Permutation p: {pval:.4f}")
    print(f"DSR (multi-testing adj): {dsr:.3f}")
    print(f"Gates passed: {passed}/{len(gates)}")
    print(f"Verdict: {verdict}")
    return out


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"[K119] FATAL: {e}\n{traceback.format_exc()}", file=sys.stderr)
        sys.exit(1)
