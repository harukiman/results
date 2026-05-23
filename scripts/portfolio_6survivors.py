"""Portfolio analysis for 6 surviving validated strategies.

Strategies:
1. VolReg_opt — DOGE Daily (SV=10, LV=25, TH=0.7, EF=14, ES=40)
2. VolReg_4h — DOGE 4H (SV=20, LV=120, TH=0.8, EF=20, ES=80) — FIXED
3. ATR_Ratio_DOGE — DOGE 4H (AS=7, AL=56, TH=0.6, EF=20, ES=80)
4. ATR_Ratio_AVAX — AVAX 4H (AS=7, AL=42, TH=0.6, EF=30, ES=40)
5. SampEn — DOGE 4H (m=2, r=0.2, w=50, pct=20, EF=14, ES=60) — NEW
6. Regime_V3 — DOGE Daily (RSI-based regime) — included for correlation, may exclude
"""

import asyncio
import sys
import os
import json
import time
import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
from itertools import combinations
from datetime import datetime

sys.path.insert(0, '/Users/nekonaomichi/crypto-lab')
from engine.data import fetch_klines
from engine.backtest import run_backtest
from engine.cost_config import get_cost_params


# ── Signal generators ──────────────────────────────────────

def gen_volreg_opt_signals(df):
    """VolReg_opt: DOGE Daily. SV=10, LV=25, TH=0.7, EF=14, ES=40"""
    returns = df['close'].pct_change()
    short_v = returns.rolling(10).std()
    long_v = returns.rolling(25).std()
    compression = short_v < long_v * 0.7
    ema_f = df['close'].ewm(span=14).mean()
    ema_s = df['close'].ewm(span=40).mean()
    signals = pd.Series(0, index=df.index)
    signals[compression & (ema_f > ema_s)] = 1
    signals[compression & (ema_f < ema_s)] = -1
    return signals


def gen_volreg_4h_signals(df):
    """VolReg_4h: DOGE 4H. SV=20, LV=120, TH=0.8, EF=20, ES=80 — FIXED params"""
    returns = df['close'].pct_change()
    short_v = returns.rolling(20).std()
    long_v = returns.rolling(120).std()
    compression = short_v < long_v * 0.8
    ema_f = df['close'].ewm(span=20).mean()
    ema_s = df['close'].ewm(span=80).mean()
    signals = pd.Series(0, index=df.index)
    signals[compression & (ema_f > ema_s)] = 1
    signals[compression & (ema_f < ema_s)] = -1
    return signals


def gen_atr_ratio_doge_signals(df):
    """ATR_Ratio DOGE: 4H. AS=7, AL=56, TH=0.6, EF=20, ES=80"""
    atr_short = (df['high'] - df['low']).rolling(7).mean()
    atr_long = (df['high'] - df['low']).rolling(56).mean()
    compression = atr_short / atr_long < 0.6
    ema_f = df['close'].ewm(span=20).mean()
    ema_s = df['close'].ewm(span=80).mean()
    signals = pd.Series(0, index=df.index)
    signals[compression & (ema_f > ema_s)] = 1
    signals[compression & (ema_f < ema_s)] = -1
    return signals


def gen_atr_ratio_avax_signals(df):
    """ATR_Ratio AVAX: 4H. AS=7, AL=42, TH=0.6, EF=30, ES=40"""
    atr_short = (df['high'] - df['low']).rolling(7).mean()
    atr_long = (df['high'] - df['low']).rolling(42).mean()
    compression = atr_short / atr_long < 0.6
    ema_f = df['close'].ewm(span=30).mean()
    ema_s = df['close'].ewm(span=40).mean()
    signals = pd.Series(0, index=df.index)
    signals[compression & (ema_f > ema_s)] = 1
    signals[compression & (ema_f < ema_s)] = -1
    return signals


def compute_rolling_sample_entropy_fast(returns_arr, m=2, r_mult=0.2, apen_window=50):
    """Vectorized rolling sample entropy using stride tricks."""
    n = len(returns_arr)
    entropy_vals = np.full(n, np.nan)

    for i in range(apen_window, n):
        window = returns_arr[i - apen_window:i]
        r = r_mult * np.std(window)
        if r < 1e-12:
            entropy_vals[i] = 0.0
            continue

        N = len(window)

        def _count_matches(tlen):
            if N - tlen < 2:
                return 0
            templates = np.lib.stride_tricks.sliding_window_view(window, tlen)
            count = 0
            for j in range(len(templates)):
                diffs = np.max(np.abs(templates - templates[j]), axis=1)
                count += np.sum(diffs < r) - 1  # exclude self-match
            return count

        B = _count_matches(m)
        A = _count_matches(m + 1)

        if B > 0 and A > 0:
            entropy_vals[i] = -np.log(A / B)
        else:
            entropy_vals[i] = 0.0

    return entropy_vals


def gen_sampen_signals(df):
    """SampEn: DOGE 4H. m=2, r=0.2, window=50, pct=20, EF=14, ES=60"""
    returns = df['close'].pct_change().fillna(0).values
    sampen_vals = compute_rolling_sample_entropy_fast(returns, m=2, r_mult=0.2,
                                                      apen_window=50)

    indicator_series = pd.Series(sampen_vals, index=df.index)
    threshold = indicator_series.expanding(min_periods=50).quantile(0.20)
    low_entropy = indicator_series < threshold

    ema_f = df['close'].ewm(span=14).mean()
    ema_s = df['close'].ewm(span=60).mean()

    signals = pd.Series(0, index=df.index)
    signals[low_entropy & (ema_f > ema_s)] = 1
    signals[low_entropy & (ema_f < ema_s)] = -1

    warmup = max(50 + 20, 60 + 20)
    signals.iloc[:warmup] = 0
    return signals


def gen_regime_v3_signals(df):
    """Regime_V3: DOGE Daily. RSI-based regime detection."""
    import ta
    returns = df['close'].pct_change()
    ret_rolling = returns.rolling(20).sum()
    vol_rolling = returns.rolling(20).std()
    vol_median = vol_rolling.rolling(60).median()
    vol_q75 = vol_rolling.rolling(60).quantile(0.75)
    ema_f = df['close'].ewm(span=12).mean()
    ema_s = df['close'].ewm(span=26).mean()
    signals = pd.Series(0, index=df.index)
    bull = (ret_rolling > 0) & (vol_rolling < vol_median)
    bear = (ret_rolling < 0) & (vol_rolling < vol_median)
    high_vol = vol_rolling > vol_q75
    signals[bull & (ema_f > ema_s)] = 1
    signals[bear & (ema_f < ema_s)] = -1
    rsi = ta.momentum.RSIIndicator(df['close'], 14).rsi()
    signals[high_vol & (rsi < 30)] = 1
    signals[high_vol & (rsi > 70)] = -1
    return signals


# ── Backtest wrapper ───────────────────────────────────────

def run_strategy(df, signals, name, bars_per_year, cost_params, **risk_params):
    """Run backtest and return result dict with equity curve as Series."""
    result = run_backtest(
        df, signals,
        strategy_name=name,
        bars_per_year=bars_per_year,
        **cost_params,
        **risk_params
    )
    # Build equity curve as pd.Series with open_time index
    eq = pd.Series(result['equity_curve'], index=df.index[:len(result['equity_curve'])])
    eq.index = df['open_time'].iloc[:len(eq)]
    return result, eq


# ── Daily return extraction ────────────────────────────────

def equity_to_daily_returns(eq_series):
    """Convert equity curve (indexed by datetime) to daily returns."""
    daily_eq = eq_series.resample('D').last().dropna()
    daily_ret = daily_eq.pct_change().dropna()
    return daily_ret


# ── Portfolio metrics ──────────────────────────────────────

def portfolio_metrics(daily_returns):
    """Compute portfolio-level metrics from daily returns Series."""
    if daily_returns.empty or daily_returns.std() == 0:
        return {'sharpe': 0, 'max_dd': 0, 'total_return': 0, 'calmar': 0, 'annual_return': 0}

    ann_factor = np.sqrt(365)
    sharpe = daily_returns.mean() / daily_returns.std() * ann_factor

    # Equity curve from daily returns
    eq = (1 + daily_returns).cumprod()
    peak = eq.cummax()
    dd = (eq - peak) / peak
    max_dd = dd.min()

    total_return = eq.iloc[-1] / eq.iloc[0] - 1
    n_days = len(daily_returns)
    annual_return = (1 + total_return) ** (365 / max(n_days, 1)) - 1
    calmar = annual_return / abs(max_dd) if max_dd != 0 else 0

    return {
        'sharpe': round(sharpe, 3),
        'max_dd': round(max_dd * 100, 2),
        'total_return': round(total_return * 100, 2),
        'annual_return': round(annual_return * 100, 2),
        'calmar': round(calmar, 3),
        'n_days': n_days,
    }


def kelly_criterion(daily_returns):
    """Compute Kelly criterion from daily returns."""
    if daily_returns.empty:
        return {'full_kelly': 0, 'half_kelly': 0}

    wins = daily_returns[daily_returns > 0]
    losses = daily_returns[daily_returns < 0]

    if len(wins) == 0 or len(losses) == 0:
        return {'full_kelly': 0, 'half_kelly': 0}

    win_rate = len(wins) / len(daily_returns)
    avg_win = wins.mean()
    avg_loss = abs(losses.mean())

    if avg_loss == 0:
        return {'full_kelly': 0, 'half_kelly': 0}

    R = avg_win / avg_loss
    kelly = win_rate - (1 - win_rate) / R

    # Continuous: f* = mu / sigma^2
    mu = daily_returns.mean() * 365
    sigma = daily_returns.std() * np.sqrt(365)
    continuous_kelly = mu / (sigma ** 2) if sigma > 0 else 0

    return {
        'full_kelly_discrete': round(kelly, 4),
        'half_kelly_discrete': round(kelly / 2, 4),
        'full_kelly_continuous': round(continuous_kelly, 4),
        'half_kelly_continuous': round(continuous_kelly / 2, 4),
    }


# ── Main ───────────────────────────────────────────────────

async def main():
    t0 = time.time()
    print("=" * 70)
    print("  PORTFOLIO ANALYSIS: 6 Surviving Validated Strategies")
    print("=" * 70)

    # ── Step 1: Fetch data ────────────────────────────────
    print("\n[1/7] Fetching market data...")
    doge_daily = await fetch_klines("DOGEUSDT", "1d", 730)
    doge_4h = await fetch_klines("DOGEUSDT", "4h", 730)
    avax_4h = await fetch_klines("AVAXUSDT", "4h", 730)

    print(f"  DOGE Daily: {len(doge_daily)} bars")
    print(f"  DOGE 4H:    {len(doge_4h)} bars")
    print(f"  AVAX 4H:    {len(avax_4h)} bars")

    # Cost params
    doge_cost = get_cost_params("DOGEUSDT", "1d")
    doge_cost_4h = get_cost_params("DOGEUSDT", "4h")
    avax_cost_4h = get_cost_params("AVAXUSDT", "4h")

    # ── Step 2: Generate signals & run backtests ──────────
    print("\n[2/7] Generating signals...")

    strategies = {}

    # Strategy 1: VolReg_opt DOGE Daily
    print("  Generating VolReg_opt signals...", flush=True)
    sig1 = gen_volreg_opt_signals(doge_daily)
    r1, eq1 = run_strategy(doge_daily, sig1, "VolReg_opt_1d", 365, doge_cost)
    strategies['VolReg_opt_1d'] = {
        'result': r1, 'eq': eq1, 'symbol': 'DOGEUSDT', 'tf': '1d',
        'df': doge_daily, 'signals': sig1,
    }
    print(f"    Sharpe={r1['metrics']['sharpe_ratio']:.3f}  DD={r1['metrics']['max_drawdown_pct']:.1f}%  Return={r1['metrics']['total_return_pct']:.1f}%  Trades={r1['metrics']['total_trades']}")

    # Strategy 2: VolReg_4h DOGE 4H — FIXED params
    print("  Generating VolReg_4h signals...", flush=True)
    sig2 = gen_volreg_4h_signals(doge_4h)
    r2, eq2 = run_strategy(doge_4h, sig2, "VolReg_4h", 2190, doge_cost_4h)
    strategies['VolReg_4h'] = {
        'result': r2, 'eq': eq2, 'symbol': 'DOGEUSDT', 'tf': '4h',
        'df': doge_4h, 'signals': sig2,
    }
    print(f"    Sharpe={r2['metrics']['sharpe_ratio']:.3f}  DD={r2['metrics']['max_drawdown_pct']:.1f}%  Return={r2['metrics']['total_return_pct']:.1f}%  Trades={r2['metrics']['total_trades']}")

    # Strategy 3: ATR_Ratio DOGE 4H
    print("  Generating ATR_Ratio_DOGE signals...", flush=True)
    sig3 = gen_atr_ratio_doge_signals(doge_4h)
    r3, eq3 = run_strategy(doge_4h, sig3, "ATR_DOGE_4h", 2190, doge_cost_4h)
    strategies['ATR_DOGE_4h'] = {
        'result': r3, 'eq': eq3, 'symbol': 'DOGEUSDT', 'tf': '4h',
        'df': doge_4h, 'signals': sig3,
    }
    print(f"    Sharpe={r3['metrics']['sharpe_ratio']:.3f}  DD={r3['metrics']['max_drawdown_pct']:.1f}%  Return={r3['metrics']['total_return_pct']:.1f}%  Trades={r3['metrics']['total_trades']}")

    # Strategy 4: ATR_Ratio AVAX 4H
    print("  Generating ATR_Ratio_AVAX signals...", flush=True)
    sig4 = gen_atr_ratio_avax_signals(avax_4h)
    r4, eq4 = run_strategy(avax_4h, sig4, "ATR_AVAX_4h", 2190, avax_cost_4h)
    strategies['ATR_AVAX_4h'] = {
        'result': r4, 'eq': eq4, 'symbol': 'AVAXUSDT', 'tf': '4h',
        'df': avax_4h, 'signals': sig4,
    }
    print(f"    Sharpe={r4['metrics']['sharpe_ratio']:.3f}  DD={r4['metrics']['max_drawdown_pct']:.1f}%  Return={r4['metrics']['total_return_pct']:.1f}%  Trades={r4['metrics']['total_trades']}")

    # Strategy 5: SampEn DOGE 4H — NEW (slow computation)
    print("  Generating SampEn signals (this is slow ~60-120s)...", flush=True)
    t_sampen = time.time()
    sig5 = gen_sampen_signals(doge_4h)
    print(f"    SampEn computation: {time.time() - t_sampen:.1f}s")
    r5, eq5 = run_strategy(doge_4h, sig5, "SampEn_4h", 2190, doge_cost_4h)
    strategies['SampEn_4h'] = {
        'result': r5, 'eq': eq5, 'symbol': 'DOGEUSDT', 'tf': '4h',
        'df': doge_4h, 'signals': sig5,
    }
    print(f"    Sharpe={r5['metrics']['sharpe_ratio']:.3f}  DD={r5['metrics']['max_drawdown_pct']:.1f}%  Return={r5['metrics']['total_return_pct']:.1f}%  Trades={r5['metrics']['total_trades']}")

    # Strategy 6: Regime_V3 DOGE Daily
    print("  Generating Regime_V3 signals...", flush=True)
    sig6 = gen_regime_v3_signals(doge_daily)
    r6, eq6 = run_strategy(doge_daily, sig6, "Regime_V3_1d", 365, doge_cost)
    strategies['Regime_V3_1d'] = {
        'result': r6, 'eq': eq6, 'symbol': 'DOGEUSDT', 'tf': '1d',
        'df': doge_daily, 'signals': sig6,
    }
    print(f"    Sharpe={r6['metrics']['sharpe_ratio']:.3f}  DD={r6['metrics']['max_drawdown_pct']:.1f}%  Return={r6['metrics']['total_return_pct']:.1f}%  Trades={r6['metrics']['total_trades']}")

    # ── Step 3: OOS-only backtests ────────────────────────
    print("\n[3/7] Running OOS-only backtests (last 30%)...")

    oos_strategies = {}
    for name, cfg in strategies.items():
        df = cfg['df']
        signals = cfg['signals']
        n = len(df)
        oos_start = int(n * 0.70)
        oos_df = df.iloc[oos_start:].reset_index(drop=True)
        oos_signals = signals.iloc[oos_start:].reset_index(drop=True)

        bpy = 365 if cfg['tf'] == '1d' else 2190
        cost = get_cost_params(cfg['symbol'], cfg['tf'])

        oos_result = run_backtest(
            oos_df, oos_signals,
            strategy_name=f"{name}_OOS",
            bars_per_year=bpy,
            **cost,
        )
        oos_eq = pd.Series(oos_result['equity_curve'],
                           index=oos_df.index[:len(oos_result['equity_curve'])])
        oos_eq.index = oos_df['open_time'].iloc[:len(oos_eq)]

        oos_strategies[name] = {
            'result': oos_result, 'eq': oos_eq,
        }
        m = oos_result['metrics']
        print(f"  {name:<18} OOS: Sharpe={m['sharpe_ratio']:.3f}  DD={m['max_drawdown_pct']:.1f}%  "
              f"Return={m['total_return_pct']:.1f}%  Trades={m['total_trades']}")

    # ── Step 4: Convert to daily returns ──────────────────
    print("\n[4/7] Converting to daily returns...")

    all_names = list(strategies.keys())
    daily_returns_full = {}
    daily_returns_oos = {}

    for name in all_names:
        # Full period
        eq_full = strategies[name]['eq']
        dr_full = equity_to_daily_returns(eq_full)
        daily_returns_full[name] = dr_full

        # OOS period
        eq_oos = oos_strategies[name]['eq']
        dr_oos = equity_to_daily_returns(eq_oos)
        daily_returns_oos[name] = dr_oos
        print(f"  {name:<18} Full: {len(dr_full)} days  OOS: {len(dr_oos)} days")

    # Align to common dates
    full_df = pd.DataFrame(daily_returns_full).dropna()
    oos_df_aligned = pd.DataFrame(daily_returns_oos).dropna()
    print(f"\n  Common full range: {full_df.index[0].date()} to {full_df.index[-1].date()} ({len(full_df)} days)")
    print(f"  Common OOS range:  {oos_df_aligned.index[0].date()} to {oos_df_aligned.index[-1].date()} ({len(oos_df_aligned)} days)")

    # ── Step 5: Correlation matrix ────────────────────────
    print("\n[5/7] Computing correlation matrix (full period)...")
    corr_full = full_df.corr()
    print("\n  FULL PERIOD CORRELATION:")
    print(corr_full.round(3).to_string())

    print("\n  OOS PERIOD CORRELATION:")
    corr_oos = oos_df_aligned.corr()
    print(corr_oos.round(3).to_string())

    # ── Step 6: Portfolio combinations ────────────────────
    print("\n[6/7] Evaluating all portfolio combinations (OOS period)...")

    strat_names = list(daily_returns_oos.keys())
    all_combos = []

    for r in range(2, len(strat_names) + 1):
        for combo in combinations(strat_names, r):
            combo_list = list(combo)
            combo_returns = oos_df_aligned[combo_list].mean(axis=1).dropna()
            if len(combo_returns) < 30:
                continue
            metrics = portfolio_metrics(combo_returns)
            all_combos.append({
                'strategies': combo_list,
                'n_strategies': len(combo_list),
                **metrics
            })

    # Sort by Calmar ratio (as specified)
    all_combos.sort(key=lambda x: x['calmar'], reverse=True)

    print(f"\n  TOP 15 PORTFOLIO COMBINATIONS (by Calmar):")
    print(f"  {'Rank':<4} {'N':>2} {'Strategies':<65} {'Sharpe':>7} {'MaxDD':>8} {'Calmar':>8} {'Return':>10}")
    print("  " + "-" * 104)
    for i, c in enumerate(all_combos[:15]):
        names_str = " + ".join(c['strategies'])
        print(f"  {i+1:<4} {c['n_strategies']:>2} {names_str:<65} {c['sharpe']:>7.3f} {c['max_dd']:>7.1f}% {c['calmar']:>8.3f} {c['total_return']:>9.1f}%")

    # Also sort by Sharpe for comparison
    sharpe_sorted = sorted(all_combos, key=lambda x: x['sharpe'], reverse=True)
    print(f"\n  TOP 10 PORTFOLIO COMBINATIONS (by Sharpe):")
    print(f"  {'Rank':<4} {'N':>2} {'Strategies':<65} {'Sharpe':>7} {'MaxDD':>8} {'Calmar':>8} {'Return':>10}")
    print("  " + "-" * 104)
    for i, c in enumerate(sharpe_sorted[:10]):
        names_str = " + ".join(c['strategies'])
        print(f"  {i+1:<4} {c['n_strategies']:>2} {names_str:<65} {c['sharpe']:>7.3f} {c['max_dd']:>7.1f}% {c['calmar']:>8.3f} {c['total_return']:>9.1f}%")

    # ── Exclude Regime_V3 combos for "recommended" best ──
    print("\n  ANALYSIS: Excluding Regime_V3 (DD risk)...")
    combos_no_regime = [c for c in all_combos if 'Regime_V3_1d' not in c['strategies']]
    combos_no_regime_sharpe = sorted(combos_no_regime, key=lambda x: x['sharpe'], reverse=True)
    combos_no_regime_calmar = sorted(combos_no_regime, key=lambda x: x['calmar'], reverse=True)

    print(f"\n  TOP 5 WITHOUT Regime_V3 (by Calmar):")
    for i, c in enumerate(combos_no_regime_calmar[:5]):
        names_str = " + ".join(c['strategies'])
        print(f"  {i+1}. {names_str:<60} Sharpe={c['sharpe']:.3f}  DD={c['max_dd']:.1f}%  Calmar={c['calmar']:.3f}  Return={c['total_return']:.1f}%")

    print(f"\n  TOP 5 WITHOUT Regime_V3 (by Sharpe):")
    for i, c in enumerate(combos_no_regime_sharpe[:5]):
        names_str = " + ".join(c['strategies'])
        print(f"  {i+1}. {names_str:<60} Sharpe={c['sharpe']:.3f}  DD={c['max_dd']:.1f}%  Calmar={c['calmar']:.3f}  Return={c['total_return']:.1f}%")

    # ── Step 7: Kelly criterion for best portfolio ────────
    print("\n[7/7] Computing Kelly criterion...")

    # Best by Calmar (excluding Regime_V3)
    best_calmar = combos_no_regime_calmar[0]
    best_calmar_returns = oos_df_aligned[best_calmar['strategies']].mean(axis=1).dropna()
    kelly_calmar = kelly_criterion(best_calmar_returns)

    # Best by Sharpe (excluding Regime_V3)
    best_sharpe = combos_no_regime_sharpe[0]
    best_sharpe_returns = oos_df_aligned[best_sharpe['strategies']].mean(axis=1).dropna()
    kelly_sharpe = kelly_criterion(best_sharpe_returns)

    print(f"\n  Best by Calmar: {' + '.join(best_calmar['strategies'])}")
    print(f"    Sharpe={best_calmar['sharpe']:.3f}  MaxDD={best_calmar['max_dd']:.1f}%  Calmar={best_calmar['calmar']:.3f}  Return={best_calmar['total_return']:.1f}%")
    print(f"    Full Kelly (continuous):  {kelly_calmar['full_kelly_continuous']:.4f}")
    print(f"    Half Kelly (continuous):  {kelly_calmar['half_kelly_continuous']:.4f}")

    print(f"\n  Best by Sharpe: {' + '.join(best_sharpe['strategies'])}")
    print(f"    Sharpe={best_sharpe['sharpe']:.3f}  MaxDD={best_sharpe['max_dd']:.1f}%  Calmar={best_sharpe['calmar']:.3f}  Return={best_sharpe['total_return']:.1f}%")
    print(f"    Full Kelly (continuous):  {kelly_sharpe['full_kelly_continuous']:.4f}")
    print(f"    Half Kelly (continuous):  {kelly_sharpe['half_kelly_continuous']:.4f}")

    # ── SampEn addition impact ────────────────────────────
    print("\n  SAMPEN ADDITION IMPACT:")
    # Compare portfolios with/without SampEn
    base_without_sampen = ['VolReg_opt_1d', 'VolReg_4h', 'ATR_DOGE_4h', 'ATR_AVAX_4h']
    base_with_sampen = base_without_sampen + ['SampEn_4h']

    port_without = oos_df_aligned[base_without_sampen].mean(axis=1).dropna()
    port_with = oos_df_aligned[base_with_sampen].mean(axis=1).dropna()

    m_without = portfolio_metrics(port_without)
    m_with = portfolio_metrics(port_with)

    print(f"  4-strategy (no SampEn): Sharpe={m_without['sharpe']:.3f}  DD={m_without['max_dd']:.1f}%  Calmar={m_without['calmar']:.3f}  Return={m_without['total_return']:.1f}%")
    print(f"  5-strategy (+SampEn):   Sharpe={m_with['sharpe']:.3f}  DD={m_with['max_dd']:.1f}%  Calmar={m_with['calmar']:.3f}  Return={m_with['total_return']:.1f}%")

    sharpe_delta = m_with['sharpe'] - m_without['sharpe']
    dd_delta = abs(m_without['max_dd']) - abs(m_with['max_dd'])
    print(f"  SampEn impact: Sharpe {sharpe_delta:+.3f}  DD {dd_delta:+.1f}pp")

    # ── Regime_V3 impact ──────────────────────────────────
    print("\n  REGIME_V3 IMPACT:")
    port_6_all = oos_df_aligned[all_names].mean(axis=1).dropna()
    m_6_all = portfolio_metrics(port_6_all)
    print(f"  All 6 strategies:  Sharpe={m_6_all['sharpe']:.3f}  DD={m_6_all['max_dd']:.1f}%  Calmar={m_6_all['calmar']:.3f}  Return={m_6_all['total_return']:.1f}%")
    print(f"  5 recommended:     Sharpe={m_with['sharpe']:.3f}  DD={m_with['max_dd']:.1f}%  Calmar={m_with['calmar']:.3f}  Return={m_with['total_return']:.1f}%")

    # ── Individual strategy summary ───────────────────────
    print("\n  INDIVIDUAL STRATEGY SUMMARY (FULL + OOS):")
    print(f"  {'Strategy':<18} {'Symbol':<10} {'TF':>4} {'Full Sharpe':>12} {'OOS Sharpe':>12} {'OOS DD':>8} {'OOS Ret':>10} {'OOS Trades':>10}")
    print("  " + "-" * 84)

    individual_perf = {}
    for name in all_names:
        full_m = strategies[name]['result']['metrics']
        oos_m = oos_strategies[name]['result']['metrics']
        sym = strategies[name]['symbol']
        tf = strategies[name]['tf']
        print(f"  {name:<18} {sym:<10} {tf:>4} {full_m['sharpe_ratio']:>12.3f} {oos_m['sharpe_ratio']:>12.3f} {oos_m['max_drawdown_pct']:>7.1f}% {oos_m['total_return_pct']:>9.1f}% {oos_m['total_trades']:>10}")

        individual_perf[name] = {
            'symbol': sym,
            'timeframe': tf,
            'full_sharpe': round(full_m['sharpe_ratio'], 3),
            'full_dd': round(full_m['max_drawdown_pct'], 2),
            'full_return': round(full_m['total_return_pct'], 2),
            'full_trades': full_m['total_trades'],
            'oos_sharpe': round(oos_m['sharpe_ratio'], 3),
            'oos_dd': round(oos_m['max_drawdown_pct'], 2),
            'oos_return': round(oos_m['total_return_pct'], 2),
            'oos_trades': oos_m['total_trades'],
            'oos_win_rate': round(oos_m['win_rate_pct'], 1),
            'oos_calmar': round(oos_m['calmar_ratio'], 3),
        }

    # ── Practical recommendation ──────────────────────────
    hk = kelly_calmar['half_kelly_continuous']
    if hk > 5:
        practical_lev = f"{min(hk, 5):.1f}x (cap at 3-5x for tail risk)"
    elif hk > 2:
        practical_lev = f"{hk:.1f}x (reasonable, monitor closely)"
    elif hk > 1:
        practical_lev = f"{hk:.1f}x (conservative, appropriate)"
    else:
        practical_lev = f"{hk:.1f}x (low — consider if return justifies risk)"

    # ── Conclusion ────────────────────────────────────────
    conclusion_parts = []
    conclusion_parts.append(f"Best portfolio by Calmar: {' + '.join(best_calmar['strategies'])} "
                           f"(Sharpe {best_calmar['sharpe']:.3f}, DD {best_calmar['max_dd']:.1f}%, Calmar {best_calmar['calmar']:.3f})")
    if sharpe_delta > 0:
        conclusion_parts.append(f"SampEn ADDS value: +{sharpe_delta:.3f} Sharpe when added to 4-strategy portfolio")
    else:
        conclusion_parts.append(f"SampEn impact: {sharpe_delta:+.3f} Sharpe (marginal)")
    conclusion_parts.append(f"Half-Kelly leverage: {hk:.1f}x")
    conclusion_parts.append(f"Recommended: {practical_lev}")
    conclusion = ". ".join(conclusion_parts)

    print(f"\n{'='*70}")
    print(f"  CONCLUSION: {conclusion}")
    print(f"{'='*70}")

    elapsed = time.time() - t0
    print(f"\n  Total time: {elapsed:.1f}s")

    # ── Save results ──────────────────────────────────────
    output = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "individual_performance": individual_perf,
        "correlation_matrix": {
            "full_period": {
                str(k): {str(k2): round(v2, 4) for k2, v2 in v.items()}
                for k, v in corr_full.to_dict().items()
            },
            "oos_period": {
                str(k): {str(k2): round(v2, 4) for k2, v2 in v.items()}
                for k, v in corr_oos.to_dict().items()
            },
        },
        "best_portfolio": {
            "by_calmar": {
                "strategies": best_calmar['strategies'],
                "sharpe": best_calmar['sharpe'],
                "max_dd": best_calmar['max_dd'],
                "calmar": best_calmar['calmar'],
                "total_return": best_calmar['total_return'],
                "annual_return": best_calmar.get('annual_return', 0),
            },
            "by_sharpe": {
                "strategies": best_sharpe['strategies'],
                "sharpe": best_sharpe['sharpe'],
                "max_dd": best_sharpe['max_dd'],
                "calmar": best_sharpe['calmar'],
                "total_return": best_sharpe['total_return'],
                "annual_return": best_sharpe.get('annual_return', 0),
            },
        },
        "all_portfolios_top10": [
            {
                'strategies': c['strategies'],
                'sharpe': c['sharpe'],
                'max_dd': c['max_dd'],
                'calmar': c['calmar'],
                'total_return': c['total_return'],
                'annual_return': c.get('annual_return', 0),
            }
            for c in all_combos[:10]
        ],
        "sampen_addition_impact": {
            "without_sampen": m_without,
            "with_sampen": m_with,
            "sharpe_delta": round(sharpe_delta, 3),
            "dd_improvement_pp": round(dd_delta, 2),
        },
        "regime_v3_impact": {
            "all_6": m_6_all,
            "recommended_5": m_with,
        },
        "half_kelly": round(hk, 4),
        "kelly_details": kelly_calmar,
        "practical_leverage": practical_lev,
        "conclusion": conclusion,
        "elapsed_seconds": round(elapsed, 1),
    }

    output_path = '/Users/nekonaomichi/crypto-lab/data/portfolio_6survivors.json'
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2, default=str)

    print(f"\n  Results saved to: {output_path}")


if __name__ == "__main__":
    asyncio.run(main())
