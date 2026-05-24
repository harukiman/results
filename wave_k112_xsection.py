#!/usr/bin/env python3
"""
Wave K112 — Cross-Section Multi-Factor Sort (Long-Short)

5 factors: Momentum (30d skip 1d), Reversal (-7d), Vol (-30d realized vol),
Liquidity (inverse 30d USD volume), Carry (BTC funding proxy).

Universe: 20 MEXC perps, 4h bars, 730d. Rebalance weekly/3-day/daily.
Long top 5, short bottom 5, dollar-neutral.
"""
from __future__ import annotations
import json
import time
import warnings
from pathlib import Path
import numpy as np
import pandas as pd

warnings.filterwarnings('ignore')

CACHE = Path('/Users/nekonaomichi/crypto-lab/cache')
OUT_JSON = Path('/Users/nekonaomichi/crypto-lab/wave_k112_xsection.json')
OUT_CURVES = Path('/Users/nekonaomichi/crypto-lab/wave_k112_curves.json')

UNIVERSE = [
    'BTC', 'ETH', 'SOL', 'BNB', 'DOGE', 'AVAX', 'LINK', 'ADA',
    'XRP', 'INJ', 'OP', 'ARB', 'DOT', 'APT', 'ATOM', 'AAVE',
    'WIF', 'BONK', 'SHIB', 'FLOKI',
]

# 4h bars per day = 6; 30d = 180 bars; 7d = 42; 1d = 6
BARS_PER_DAY = 6
LOOKBACK_MOM = 30 * BARS_PER_DAY   # 180
SKIP_MOM = 1 * BARS_PER_DAY        # 6
LOOKBACK_REV = 7 * BARS_PER_DAY    # 42
LOOKBACK_VOL = 30 * BARS_PER_DAY   # 180
LOOKBACK_LIQ = 30 * BARS_PER_DAY   # 180

CADENCES = {
    'weekly': 7 * BARS_PER_DAY,   # 42
    '3day':   3 * BARS_PER_DAY,   # 18
    'daily':  1 * BARS_PER_DAY,   # 6
}

# Costs
TAKER = 0.0004
SLIPPAGE = 0.0003
ONE_SIDE = TAKER + SLIPPAGE   # 0.07% per side

TOP_K = 5
BOT_K = 5
SEED = 42
rng = np.random.default_rng(SEED)


def log(msg: str):
    print(f"[K112] {msg}", flush=True)


# ----------------------------- DATA ---------------------------------
def load_panel() -> tuple[pd.DataFrame, pd.DataFrame]:
    closes = {}
    qvols = {}
    for sym in UNIVERSE:
        p = CACHE / f"{sym}USDT_4h_730d.parquet"
        if not p.exists():
            log(f"skip {sym}: no parquet")
            continue
        df = pd.read_parquet(p)
        df = df.set_index('open_time').sort_index()
        df = df[~df.index.duplicated(keep='last')]
        closes[sym] = df['close']
        qvols[sym] = df['quote_volume']
    close_df = pd.DataFrame(closes)
    qv_df = pd.DataFrame(qvols)
    # align on union of timestamps, then ffill small gaps (max 2 bars)
    close_df = close_df.sort_index().ffill(limit=2).dropna(how='all')
    qv_df = qv_df.sort_index().reindex(close_df.index).fillna(0.0)
    # Drop initial rows where >50% of universe is NaN
    coverage = close_df.notna().mean(axis=1)
    close_df = close_df[coverage > 0.5]
    qv_df = qv_df.reindex(close_df.index)
    log(f"panel: {close_df.shape}, cols={list(close_df.columns)}")
    return close_df, qv_df


# --------------------------- FACTORS --------------------------------
def compute_factors(close: pd.DataFrame, qv: pd.DataFrame) -> dict[str, pd.DataFrame]:
    log_close = np.log(close)
    ret1 = log_close.diff()

    # Momentum: return from t-180 to t-6 (skip last day)
    mom = (log_close.shift(SKIP_MOM) - log_close.shift(LOOKBACK_MOM))

    # Reversal: -1 * 7d return (recent)
    rev = -1.0 * (log_close - log_close.shift(LOOKBACK_REV))

    # Vol: -1 * 30d realized vol of 4h returns
    vol = -1.0 * ret1.rolling(LOOKBACK_VOL, min_periods=LOOKBACK_VOL // 2).std()

    # Liquidity: inverse 30d USD avg volume (small = better => negative log volume)
    liq_avg = qv.rolling(LOOKBACK_LIQ, min_periods=LOOKBACK_LIQ // 2).mean()
    liq = -1.0 * np.log(liq_avg.replace(0.0, np.nan))

    # Carry: use BTC's 24h price drift sign × magnitude as universe-wide funding proxy
    # Approx: positive 24h drift => longs likely paying funding => penalize long bias.
    # Construct as a cross-sectional factor: use each symbol's own 24h drift sign as carry proxy.
    # Convention: high "carry" score = expected positive return on long.
    # Use -sign(24h ret) so symbols that recently dropped (likely shorts paying) get long bias.
    drift24 = (log_close - log_close.shift(BARS_PER_DAY))
    carry = -drift24.rolling(3 * BARS_PER_DAY, min_periods=BARS_PER_DAY).mean()

    # Lag by 1 bar to avoid look-ahead
    factors = {
        'mom': mom.shift(1),
        'rev': rev.shift(1),
        'vol': vol.shift(1),
        'liq': liq.shift(1),
        'carry': carry.shift(1),
    }
    return factors


def zscore_xs(df: pd.DataFrame) -> pd.DataFrame:
    """Cross-sectional z-score per row."""
    mu = df.mean(axis=1)
    sd = df.std(axis=1).replace(0.0, np.nan)
    return (df.sub(mu, axis=0)).div(sd, axis=0)


# ---------------------- PORTFOLIO BACKTEST --------------------------
def build_weights(score: pd.Series, top_k: int, bot_k: int) -> pd.Series:
    """Equal weight long top_k, short bot_k. Sum long = 1, sum short = -1."""
    valid = score.dropna()
    if len(valid) < top_k + bot_k:
        return pd.Series(0.0, index=score.index)
    longs = valid.nlargest(top_k).index
    shorts = valid.nsmallest(bot_k).index
    w = pd.Series(0.0, index=score.index)
    w.loc[longs] = 1.0 / top_k
    w.loc[shorts] = -1.0 / bot_k
    return w


def backtest(
    close: pd.DataFrame,
    factors: dict[str, pd.DataFrame],
    weights_blend: dict[str, float],
    cadence_bars: int,
    cost_per_side: float = ONE_SIDE,
) -> dict:
    """Run a cross-sectional L/S backtest.

    Returns dict with equity, returns, weights time-series, turnover.
    """
    # Composite score = weighted sum of z-scored factors
    zfac = {k: zscore_xs(v) for k, v in factors.items()}
    composite = None
    for k, w in weights_blend.items():
        if w == 0:
            continue
        comp_k = zfac[k] * w
        composite = comp_k if composite is None else composite.add(comp_k, fill_value=0.0)
    composite = composite / sum(abs(v) for v in weights_blend.values() if v != 0)

    idx = close.index
    n = len(idx)
    # Forward 1-bar returns of each asset (used for portfolio PnL)
    ret_fwd = close.pct_change().shift(-1)  # return realized between t and t+1

    # Determine rebalance bars: first valid bar where composite has >= top_k+bot_k assets
    valid_mask = composite.notna().sum(axis=1) >= (TOP_K + BOT_K)
    first_valid = valid_mask.idxmax() if valid_mask.any() else None
    if first_valid is None:
        return {'error': 'no valid bars'}

    start_i = idx.get_loc(first_valid)
    rebal_bars = list(range(start_i, n, cadence_bars))

    w_curr = pd.Series(0.0, index=close.columns)
    weights_history = []
    pnl_bar = np.zeros(n)
    turnover_bar = np.zeros(n)

    next_rebal_idx = 0
    for i in range(start_i, n - 1):
        if next_rebal_idx < len(rebal_bars) and i == rebal_bars[next_rebal_idx]:
            new_w = build_weights(composite.iloc[i], TOP_K, BOT_K)
            # turnover & cost
            turnover = (new_w - w_curr).abs().sum()
            turnover_bar[i] = turnover
            pnl_bar[i] -= turnover * cost_per_side
            w_curr = new_w
            next_rebal_idx += 1
        # accumulate bar PnL (held over current 4h bar)
        r = ret_fwd.iloc[i].fillna(0.0)
        bar_pnl = (w_curr * r).sum()
        pnl_bar[i] += bar_pnl
        weights_history.append((idx[i], w_curr.copy()))

    ret_series = pd.Series(pnl_bar[start_i:n - 1], index=idx[start_i:n - 1])
    equity = (1.0 + ret_series).cumprod()
    return {
        'returns': ret_series,
        'equity': equity,
        'turnover_total': float(np.sum(turnover_bar)),
        'n_rebal': len(rebal_bars),
    }


def metrics(rets: pd.Series, bars_per_year: int = 365 * BARS_PER_DAY) -> dict:
    if rets is None or len(rets) < 10:
        return {'sharpe': 0.0, 'sortino': 0.0, 'calmar': 0.0, 'maxdd': 0.0,
                'win_rate': 0.0, 'ann_ret': 0.0, 'ann_vol': 0.0, 'n_bars': len(rets) if rets is not None else 0}
    mu = rets.mean()
    sd = rets.std()
    sharpe = (mu / sd) * np.sqrt(bars_per_year) if sd > 0 else 0.0
    downside = rets[rets < 0].std()
    sortino = (mu / downside) * np.sqrt(bars_per_year) if downside and downside > 0 else 0.0
    equity = (1.0 + rets).cumprod()
    peak = equity.cummax()
    dd = (equity / peak - 1.0).min()
    ann_ret = (equity.iloc[-1]) ** (bars_per_year / len(rets)) - 1.0 if len(rets) > 0 else 0.0
    calmar = ann_ret / abs(dd) if dd < 0 else 0.0
    win = (rets > 0).mean()
    return {
        'sharpe': float(sharpe),
        'sortino': float(sortino),
        'calmar': float(calmar),
        'maxdd': float(dd),
        'win_rate': float(win),
        'ann_ret': float(ann_ret),
        'ann_vol': float(sd * np.sqrt(bars_per_year)),
        'n_bars': int(len(rets)),
    }


# ------------------------- AUDIT / §6 -------------------------------
def block_bootstrap_sharpe(rets: pd.Series, block: int = 20, n: int = 500) -> dict:
    arr = rets.values
    L = len(arr)
    if L < block * 5:
        return {'ci_lo': 0.0, 'ci_hi': 0.0, 'mean': 0.0}
    sharpes = []
    bars_per_year = 365 * BARS_PER_DAY
    n_blocks = L // block
    for _ in range(n):
        idx = rng.integers(0, L - block + 1, size=n_blocks)
        sample = np.concatenate([arr[i:i + block] for i in idx])
        mu = sample.mean()
        sd = sample.std()
        s = (mu / sd) * np.sqrt(bars_per_year) if sd > 0 else 0.0
        sharpes.append(s)
    sharpes = np.array(sharpes)
    return {
        'mean': float(sharpes.mean()),
        'ci_lo': float(np.percentile(sharpes, 2.5)),
        'ci_hi': float(np.percentile(sharpes, 97.5)),
    }


def permutation_test(
    close: pd.DataFrame,
    factors: dict[str, pd.DataFrame],
    weights_blend: dict[str, float],
    cadence_bars: int,
    observed_sharpe: float,
    n: int = 500,
) -> float:
    """Shuffle factor values across symbols within each row, then run cheap PnL calc."""
    zfac = {k: zscore_xs(v) for k, v in factors.items()}
    composite = None
    for k, w in weights_blend.items():
        if w == 0:
            continue
        comp_k = zfac[k] * w
        composite = comp_k if composite is None else composite.add(comp_k, fill_value=0.0)
    composite = composite / sum(abs(v) for v in weights_blend.values() if v != 0)

    idx = close.index
    n_bars = len(idx)
    ret_fwd = close.pct_change().shift(-1).fillna(0.0)
    valid_mask = composite.notna().sum(axis=1) >= (TOP_K + BOT_K)
    first_valid = valid_mask.idxmax() if valid_mask.any() else None
    if first_valid is None:
        return 1.0
    start_i = idx.get_loc(first_valid)
    rebal_bars = list(range(start_i, n_bars, cadence_bars))

    # Cheap: precompute fwd returns array
    syms = list(close.columns)
    comp_arr = composite[syms].values
    ret_arr = ret_fwd[syms].values

    bars_per_year = 365 * BARS_PER_DAY
    null_sharpes = np.zeros(n)
    n_syms = len(syms)

    for trial in range(n):
        # Shuffle composite within each rebalance row
        shuffled_signs = np.zeros((n_bars, n_syms))
        for rb in rebal_bars:
            row = comp_arr[rb].copy()
            mask = ~np.isnan(row)
            if mask.sum() < TOP_K + BOT_K:
                continue
            valid_vals = row[mask]
            rng.shuffle(valid_vals)
            row_perm = row.copy()
            row_perm[mask] = valid_vals
            # build weights
            order = np.argsort(-row_perm)  # descending; NaNs go to end via stability
            # valid only
            valid_idx = np.where(mask)[0]
            sorted_valid = sorted(valid_idx, key=lambda j: -row_perm[j])
            longs = sorted_valid[:TOP_K]
            shorts = sorted_valid[-BOT_K:]
            w_row = np.zeros(n_syms)
            w_row[longs] = 1.0 / TOP_K
            w_row[shorts] = -1.0 / BOT_K
            shuffled_signs[rb] = w_row

        # Hold weights between rebalances
        w_curr = np.zeros(n_syms)
        pnl = np.zeros(n_bars)
        next_rb = 0
        for i in range(start_i, n_bars - 1):
            if next_rb < len(rebal_bars) and i == rebal_bars[next_rb]:
                new_w = shuffled_signs[i]
                turnover = np.abs(new_w - w_curr).sum()
                pnl[i] -= turnover * ONE_SIDE
                w_curr = new_w
                next_rb += 1
            r = np.nan_to_num(ret_arr[i])
            pnl[i] += float((w_curr * r).sum())
        rets = pnl[start_i:n_bars - 1]
        mu = rets.mean()
        sd = rets.std()
        s = (mu / sd) * np.sqrt(bars_per_year) if sd > 0 else 0.0
        null_sharpes[trial] = s

    pval = float((null_sharpes >= observed_sharpe).mean())
    return pval, null_sharpes


def deflated_sharpe(sr: float, n_trials: int, n_bars: int) -> float:
    """Bailey & Lopez de Prado DSR approximation (assume normal returns)."""
    if n_bars < 10:
        return 0.0
    from math import sqrt, log
    # Expected max SR under null, using Bailey's formula
    emc = 0.5772156649  # Euler-Mascheroni
    e_max = sqrt(2 * log(max(n_trials, 2))) * (1 - emc) + emc * 1 / sqrt(2 * log(max(n_trials, 2)) + 1e-9)
    # DSR ~ Prob(SR_obs > E[max SR null]) via z-statistic on annualized scale
    # Use simple normal-approx: z = (SR_obs - e_max) * sqrt(n_bars - 1)
    from scipy.stats import norm
    z = (sr - e_max) * sqrt(max(n_bars - 1, 1))
    return float(norm.cdf(z))


def walk_forward_4fold(close: pd.DataFrame, factors: dict[str, pd.DataFrame],
                       best_blend: dict[str, float], cadence_bars: int) -> dict:
    n = len(close)
    fold_size = n // 4
    sharpes = []
    for f in range(4):
        start = f * fold_size
        end = (f + 1) * fold_size if f < 3 else n
        sub_close = close.iloc[start:end]
        sub_factors = {k: v.iloc[start:end] for k, v in factors.items()}
        res = backtest(sub_close, sub_factors, best_blend, cadence_bars)
        if 'error' in res:
            sharpes.append(0.0)
            continue
        m = metrics(res['returns'])
        sharpes.append(m['sharpe'])
    return {'fold_sharpes': sharpes, 'mean': float(np.mean(sharpes)), 'std': float(np.std(sharpes))}


# --------------------------- MAIN -----------------------------------
def main():
    t0 = time.time()
    log("loading panel...")
    close, qv = load_panel()
    log(f"panel rows: {len(close)} cols: {len(close.columns)}")
    log("computing factors...")
    factors = compute_factors(close, qv)

    # Split 70/30
    split_i = int(len(close) * 0.7)
    is_close = close.iloc[:split_i]
    is_qv = qv.iloc[:split_i]
    is_factors = {k: v.iloc[:split_i] for k, v in factors.items()}
    oos_close = close.iloc[split_i:]
    oos_factors = {k: v.iloc[split_i:] for k, v in factors.items()}
    log(f"IS bars: {len(is_close)}  OOS bars: {len(oos_close)}")

    # 1) Per-factor standalone Sharpe (use weekly cadence, on FULL panel; then IS)
    factor_names = ['mom', 'rev', 'vol', 'liq', 'carry']
    per_factor_full = {}
    per_factor_is = {}
    for fn in factor_names:
        blend = {k: (1.0 if k == fn else 0.0) for k in factor_names}
        res_full = backtest(close, factors, blend, CADENCES['weekly'])
        per_factor_full[fn] = metrics(res_full['returns']) if 'returns' in res_full else {}
        res_is = backtest(is_close, is_factors, blend, CADENCES['weekly'])
        per_factor_is[fn] = metrics(res_is['returns']) if 'returns' in res_is else {}
        log(f"  factor {fn:5s}  full Sh={per_factor_full[fn].get('sharpe',0):.3f}  IS Sh={per_factor_is[fn].get('sharpe',0):.3f}")

    # 2) Composite blends to test (IS)
    blends = {
        'uniform':         {'mom': 0.2, 'rev': 0.2, 'vol': 0.2, 'liq': 0.2, 'carry': 0.2},
        'mom_only':        {'mom': 1.0, 'rev': 0.0, 'vol': 0.0, 'liq': 0.0, 'carry': 0.0},
        'rev_only':        {'mom': 0.0, 'rev': 1.0, 'vol': 0.0, 'liq': 0.0, 'carry': 0.0},
        'vol_only':        {'mom': 0.0, 'rev': 0.0, 'vol': 1.0, 'liq': 0.0, 'carry': 0.0},
        'liq_only':        {'mom': 0.0, 'rev': 0.0, 'vol': 0.0, 'liq': 1.0, 'carry': 0.0},
        'carry_only':      {'mom': 0.0, 'rev': 0.0, 'vol': 0.0, 'liq': 0.0, 'carry': 1.0},
        'mom_vol':         {'mom': 0.5, 'rev': 0.0, 'vol': 0.5, 'liq': 0.0, 'carry': 0.0},
        'mom_rev':         {'mom': 0.5, 'rev': 0.5, 'vol': 0.0, 'liq': 0.0, 'carry': 0.0},
        'mom_vol_liq':     {'mom': 1/3, 'rev': 0.0, 'vol': 1/3, 'liq': 1/3, 'carry': 0.0},
        'mom_rev_vol':     {'mom': 1/3, 'rev': 1/3, 'vol': 1/3, 'liq': 0.0, 'carry': 0.0},
        'no_carry':        {'mom': 0.25, 'rev': 0.25, 'vol': 0.25, 'liq': 0.25, 'carry': 0.0},
        'no_liq':          {'mom': 0.25, 'rev': 0.25, 'vol': 0.25, 'liq': 0.0, 'carry': 0.25},
        'mom_heavy':       {'mom': 0.5, 'rev': 0.125, 'vol': 0.125, 'liq': 0.125, 'carry': 0.125},
        'vol_heavy':       {'mom': 0.125, 'rev': 0.125, 'vol': 0.5, 'liq': 0.125, 'carry': 0.125},
        'rev_heavy':       {'mom': 0.125, 'rev': 0.5, 'vol': 0.125, 'liq': 0.125, 'carry': 0.125},
    }
    log(f"testing {len(blends)} blends × {len(CADENCES)} cadences (IS)...")
    is_grid = {}
    for cad_name, cad_bars in CADENCES.items():
        for blend_name, blend in blends.items():
            res = backtest(is_close, is_factors, blend, cad_bars)
            if 'error' in res:
                continue
            m = metrics(res['returns'])
            is_grid[f"{cad_name}::{blend_name}"] = {
                'sharpe': m['sharpe'],
                'maxdd': m['maxdd'],
                'ann_ret': m['ann_ret'],
                'n_rebal': res['n_rebal'],
            }

    # Best IS combo
    best_key = max(is_grid, key=lambda k: is_grid[k]['sharpe'])
    best_cad, best_blend_name = best_key.split('::')
    best_blend = blends[best_blend_name]
    log(f"BEST IS: {best_key}  Sh={is_grid[best_key]['sharpe']:.3f}")

    # Cadence sensitivity using uniform blend
    cad_sens = {}
    for cad_name, cad_bars in CADENCES.items():
        res = backtest(is_close, is_factors, blends['uniform'], cad_bars)
        cad_sens[cad_name] = metrics(res['returns'])['sharpe']

    # 3) OOS evaluation of best
    log(f"running OOS with {best_cad} / {best_blend_name}...")
    oos_res = backtest(oos_close, oos_factors, best_blend, CADENCES[best_cad])
    oos_metrics = metrics(oos_res['returns'])
    log(f"OOS Sharpe: {oos_metrics['sharpe']:.3f}  MaxDD: {oos_metrics['maxdd']:.3f}")

    # Full-period equity for chart
    full_res = backtest(close, factors, best_blend, CADENCES[best_cad])
    full_metrics = metrics(full_res['returns'])

    # 4) Mini §6 audit on OOS
    # Walk-forward 4-fold (on full data, using best blend)
    log("walk-forward 4-fold...")
    wf = walk_forward_4fold(close, factors, best_blend, CADENCES[best_cad])

    # Block bootstrap on OOS
    log("block bootstrap CI (OOS)...")
    bb = block_bootstrap_sharpe(oos_res['returns'], block=20, n=500)

    # Permutation test on OOS
    log("permutation test (OOS, n=500)...")
    pval, null_sh = permutation_test(
        oos_close, oos_factors, best_blend, CADENCES[best_cad],
        observed_sharpe=oos_metrics['sharpe'], n=500
    )
    log(f"perm p-value: {pval:.4f}  null median: {float(np.median(null_sh)):.3f}")

    # DSR with N_trials = 5 factors × 3 cadences × 15 blends = (factors only counted once)
    # Per spec: 5 factors × 3 cadences × 4 weight blends = 60. We tested 15 blends, so 45 cadence-blend combos.
    # Use the larger of the two = 60.
    n_trials = 5 * 3 * 4
    dsr = deflated_sharpe(oos_metrics['sharpe'], n_trials, oos_metrics['n_bars'])
    log(f"DSR (N_trials={n_trials}): {dsr:.4f}")

    # PBO approximation: % folds where best-IS rank flips to bottom half OOS
    # Cheap: compare IS top-3 blends to OOS Sharpe
    is_blend_oos = {}
    for blend_name, blend in blends.items():
        res = backtest(oos_close, oos_factors, blend, CADENCES[best_cad])
        is_blend_oos[blend_name] = metrics(res['returns'])['sharpe']
    is_only_sh = {bn: is_grid[f"{best_cad}::{bn}"]['sharpe'] for bn in blends}
    sorted_is = sorted(blends.keys(), key=lambda b: -is_only_sh[b])
    sorted_oos = sorted(blends.keys(), key=lambda b: -is_blend_oos[b])
    median_oos = np.median([is_blend_oos[b] for b in blends])
    # PBO ~ fraction of top-IS strategies that end up below median OOS
    top3 = sorted_is[:3]
    pbo_approx = float(np.mean([is_blend_oos[b] < median_oos for b in top3]))

    elapsed = time.time() - t0
    log(f"elapsed: {elapsed:.1f}s")

    # ----------------------- WRITE OUTPUTS -------------------------
    out = {
        'wave': 'K112',
        'task': 'cross_section_multi_factor_LS',
        'universe': UNIVERSE,
        'n_symbols': len(close.columns),
        'panel_bars': len(close),
        'split': {'is_bars': len(is_close), 'oos_bars': len(oos_close)},
        'per_factor_standalone_full': per_factor_full,
        'per_factor_standalone_is': per_factor_is,
        'cadence_sensitivity_is_uniform': cad_sens,
        'is_grid': is_grid,
        'best_is': {
            'key': best_key,
            'cadence': best_cad,
            'blend_name': best_blend_name,
            'blend': best_blend,
            'sharpe': is_grid[best_key]['sharpe'],
            'maxdd': is_grid[best_key]['maxdd'],
            'ann_ret': is_grid[best_key]['ann_ret'],
        },
        'oos_metrics': oos_metrics,
        'full_metrics': full_metrics,
        'walk_forward_4fold': wf,
        'block_bootstrap_oos': bb,
        'permutation_oos': {
            'p_value': pval,
            'null_mean': float(null_sh.mean()),
            'null_median': float(np.median(null_sh)),
            'null_p95': float(np.percentile(null_sh, 95)),
        },
        'deflated_sharpe_oos': {
            'value': dsr,
            'n_trials': n_trials,
        },
        'pbo_approx': pbo_approx,
        'oos_sharpe_by_blend': is_blend_oos,
        'gates': {
            'G1_oos_sharpe_gt_0.5': bool(oos_metrics['sharpe'] > 0.5),
            'G2_pbo_lt_0.3': bool(pbo_approx < 0.3),
            'G3_dsr_gt_0': bool(dsr > 0.5),  # interpret DSR > 0.5 as "edge after deflation"
        },
        'costs': {'taker': TAKER, 'slippage': SLIPPAGE, 'per_side': ONE_SIDE},
        'elapsed_sec': elapsed,
    }
    with open(OUT_JSON, 'w') as f:
        json.dump(out, f, indent=2, default=str)
    log(f"wrote {OUT_JSON}")

    # Curves
    curves = {
        'wave': 'K112',
        'best_key': best_key,
        'is_equity': {str(t): float(v) for t, v in
                      backtest(is_close, is_factors, best_blend, CADENCES[best_cad])['equity'].items()},
        'oos_equity': {str(t): float(v) for t, v in oos_res['equity'].items()},
        'full_equity': {str(t): float(v) for t, v in full_res['equity'].items()},
    }
    with open(OUT_CURVES, 'w') as f:
        json.dump(curves, f, default=str)
    log(f"wrote {OUT_CURVES}")

    # Print final summary
    print("\n" + "=" * 70)
    print("WAVE K112 — FINAL SUMMARY")
    print("=" * 70)
    print(f"Best IS combo: cadence={best_cad}  blend={best_blend_name}  Sh={is_grid[best_key]['sharpe']:.3f}")
    print(f"OOS Sharpe: {oos_metrics['sharpe']:.3f}  Sortino: {oos_metrics['sortino']:.3f}  "
          f"Calmar: {oos_metrics['calmar']:.3f}  MaxDD: {oos_metrics['maxdd']:.3f}  Win%: {oos_metrics['win_rate']:.3f}")
    print(f"WF 4-fold: mean={wf['mean']:.3f}  folds={wf['fold_sharpes']}")
    print(f"BootCI95%: [{bb['ci_lo']:.3f}, {bb['ci_hi']:.3f}]")
    print(f"Perm p-value: {pval:.4f}")
    print(f"DSR: {dsr:.4f}")
    print(f"PBO~ {pbo_approx:.2f}")
    print(f"Gates: {out['gates']}")
    return out


if __name__ == '__main__':
    main()
