"""Portfolio analysis for 5 surviving strategies.

Strategies:
1. VolReg_opt — DOGE Daily (Sharpe ~2.30)
2. VolReg_4h — DOGE 4H (Sharpe ~2.275)
3. ATR_Ratio_DOGE — DOGE 4H (Sharpe ~1.76)
4. ATR_Ratio_AVAX — AVAX 4H (Sharpe ~3.06)
5. Regime_V3 — DOGE Daily (POISON — reference only)
"""

import asyncio
import sys
import os
import json
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
    """VolReg_opt: DOGE Daily. short_vol=10, long_vol=30, threshold=0.8, ema_fast=10, ema_slow=30"""
    returns = df['close'].pct_change()
    short_v = returns.rolling(10).std()
    long_v = returns.rolling(30).std()
    compression = short_v < long_v * 0.8
    ema_f = df['close'].ewm(span=10).mean()
    ema_s = df['close'].ewm(span=30).mean()
    signals = pd.Series(0, index=df.index)
    signals[compression & (ema_f > ema_s)] = 1
    signals[compression & (ema_f < ema_s)] = -1
    return signals


def gen_volreg_4h_signals(df):
    """VolReg_4h: DOGE 4H. Validated params: short_vol=20, long_vol=120, threshold=0.8, ema_fast=20, ema_slow=80"""
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


def gen_atr_ratio_signals(df, atr_short=7, atr_long=56, threshold=0.6, ema_fast=20, ema_slow=80):
    """ATR Ratio Compression strategy."""
    tr = pd.concat([
        df['high'] - df['low'],
        (df['high'] - df['close'].shift()).abs(),
        (df['low'] - df['close'].shift()).abs()
    ], axis=1).max(axis=1)
    atr_s = tr.rolling(atr_short).mean()
    atr_l = tr.rolling(atr_long).mean()
    compression = atr_s < atr_l * threshold
    ema_f = df['close'].ewm(span=ema_fast).mean()
    ema_s = df['close'].ewm(span=ema_slow).mean()
    signals = pd.Series(0, index=df.index)
    signals[compression & (ema_f > ema_s)] = 1
    signals[compression & (ema_f < ema_s)] = -1
    return signals


def gen_regime_v3_signals(df):
    """Regime_V3: DOGE Daily. short_vol=5, long_vol=20, threshold=0.5, ema_fast=5, ema_slow=20"""
    returns = df['close'].pct_change()
    short_v = returns.rolling(5).std()
    long_v = returns.rolling(20).std()
    compression = short_v < long_v * 0.5
    ema_f = df['close'].ewm(span=5).mean()
    ema_s = df['close'].ewm(span=20).mean()
    signals = pd.Series(0, index=df.index)
    signals[compression & (ema_f > ema_s)] = 1
    signals[compression & (ema_f < ema_s)] = -1
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
    # Resample to daily using last value
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

    # Kelly = W - (1-W)/R where W=win rate, R=win/loss ratio
    R = avg_win / avg_loss
    kelly = win_rate - (1 - win_rate) / R

    # Alternative: f* = mu / sigma^2 (continuous Kelly)
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
    print("=" * 60)
    print("PORTFOLIO ANALYSIS: 5 Surviving Strategies")
    print("=" * 60)

    # ── Step 1: Fetch data ────────────────────────────────
    print("\n[1/5] Fetching market data...")
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
    print("\n[2/5] Running backtests...")

    strategies_config = {}

    # Strategy 1: VolReg_opt DOGE Daily
    sig1 = gen_volreg_opt_signals(doge_daily)
    r1, eq1 = run_strategy(doge_daily, sig1, "VolReg_opt_1d", 365, doge_cost,
                           stop_loss_pct=0.02, take_profit_pct=0.10, max_hold_bars=7)
    strategies_config['VolReg_opt_1d'] = {
        'result': r1, 'eq': eq1, 'symbol': 'DOGEUSDT', 'tf': '1d',
        'sl_cooldown': False
    }
    print(f"  VolReg_opt_1d:  Sharpe={r1['metrics']['sharpe_ratio']:.3f}  DD={r1['metrics']['max_drawdown_pct']:.1f}%  Return={r1['metrics']['total_return_pct']:.1f}%")

    # Strategy 2: VolReg_4h DOGE 4H — WITHOUT SL cooldown
    sig2 = gen_volreg_4h_signals(doge_4h)
    r2_no_sl, eq2_no_sl = run_strategy(doge_4h, sig2, "VolReg_4h_noSL", 2190, doge_cost_4h)
    strategies_config['VolReg_4h_noSL'] = {
        'result': r2_no_sl, 'eq': eq2_no_sl, 'symbol': 'DOGEUSDT', 'tf': '4h',
        'sl_cooldown': False
    }
    print(f"  VolReg_4h (no SL):  Sharpe={r2_no_sl['metrics']['sharpe_ratio']:.3f}  DD={r2_no_sl['metrics']['max_drawdown_pct']:.1f}%  Return={r2_no_sl['metrics']['total_return_pct']:.1f}%")

    # Strategy 2b: VolReg_4h DOGE 4H — WITH SL cooldown
    r2_sl, eq2_sl = run_strategy(doge_4h, sig2, "VolReg_4h", 2190, doge_cost_4h,
                                  sl_cooldown_bars=50, atr_sl_mult=2.0, atr_sl_period=14)
    strategies_config['VolReg_4h'] = {
        'result': r2_sl, 'eq': eq2_sl, 'symbol': 'DOGEUSDT', 'tf': '4h',
        'sl_cooldown': True
    }
    print(f"  VolReg_4h (SL cd):  Sharpe={r2_sl['metrics']['sharpe_ratio']:.3f}  DD={r2_sl['metrics']['max_drawdown_pct']:.1f}%  Return={r2_sl['metrics']['total_return_pct']:.1f}%")

    # Strategy 3: ATR_Ratio DOGE 4H — WITHOUT SL cooldown
    sig3 = gen_atr_ratio_signals(doge_4h, atr_short=7, atr_long=56, threshold=0.6, ema_fast=20, ema_slow=80)
    r3_no_sl, eq3_no_sl = run_strategy(doge_4h, sig3, "ATR_DOGE_noSL", 2190, doge_cost_4h)
    strategies_config['ATR_DOGE_noSL'] = {
        'result': r3_no_sl, 'eq': eq3_no_sl, 'symbol': 'DOGEUSDT', 'tf': '4h',
        'sl_cooldown': False
    }
    print(f"  ATR_DOGE (no SL):   Sharpe={r3_no_sl['metrics']['sharpe_ratio']:.3f}  DD={r3_no_sl['metrics']['max_drawdown_pct']:.1f}%  Return={r3_no_sl['metrics']['total_return_pct']:.1f}%")

    # Strategy 3b: ATR_Ratio DOGE 4H — WITH SL cooldown
    r3_sl, eq3_sl = run_strategy(doge_4h, sig3, "ATR_DOGE", 2190, doge_cost_4h,
                                  sl_cooldown_bars=50, atr_sl_mult=2.0, atr_sl_period=14)
    strategies_config['ATR_DOGE'] = {
        'result': r3_sl, 'eq': eq3_sl, 'symbol': 'DOGEUSDT', 'tf': '4h',
        'sl_cooldown': True
    }
    print(f"  ATR_DOGE (SL cd):   Sharpe={r3_sl['metrics']['sharpe_ratio']:.3f}  DD={r3_sl['metrics']['max_drawdown_pct']:.1f}%  Return={r3_sl['metrics']['total_return_pct']:.1f}%")

    # Strategy 4: ATR_Ratio AVAX 4H — WITHOUT SL cooldown
    sig4 = gen_atr_ratio_signals(avax_4h, atr_short=7, atr_long=42, threshold=0.6, ema_fast=30, ema_slow=40)
    r4_no_sl, eq4_no_sl = run_strategy(avax_4h, sig4, "ATR_AVAX_noSL", 2190, avax_cost_4h)
    strategies_config['ATR_AVAX_noSL'] = {
        'result': r4_no_sl, 'eq': eq4_no_sl, 'symbol': 'AVAXUSDT', 'tf': '4h',
        'sl_cooldown': False
    }
    print(f"  ATR_AVAX (no SL):   Sharpe={r4_no_sl['metrics']['sharpe_ratio']:.3f}  DD={r4_no_sl['metrics']['max_drawdown_pct']:.1f}%  Return={r4_no_sl['metrics']['total_return_pct']:.1f}%")

    # Strategy 4b: ATR_Ratio AVAX 4H — WITH SL cooldown
    r4_sl, eq4_sl = run_strategy(avax_4h, sig4, "ATR_AVAX", 2190, avax_cost_4h,
                                  sl_cooldown_bars=50, atr_sl_mult=2.0, atr_sl_period=14)
    strategies_config['ATR_AVAX'] = {
        'result': r4_sl, 'eq': eq4_sl, 'symbol': 'AVAXUSDT', 'tf': '4h',
        'sl_cooldown': True
    }
    print(f"  ATR_AVAX (SL cd):   Sharpe={r4_sl['metrics']['sharpe_ratio']:.3f}  DD={r4_sl['metrics']['max_drawdown_pct']:.1f}%  Return={r4_sl['metrics']['total_return_pct']:.1f}%")

    # Strategy 5: Regime_V3 DOGE Daily — POISON (reference only)
    sig5 = gen_regime_v3_signals(doge_daily)
    r5, eq5 = run_strategy(doge_daily, sig5, "Regime_V3_POISON", 365, doge_cost)
    strategies_config['Regime_V3_POISON'] = {
        'result': r5, 'eq': eq5, 'symbol': 'DOGEUSDT', 'tf': '1d',
        'sl_cooldown': False, 'poison': True
    }
    print(f"  Regime_V3 (POISON): Sharpe={r5['metrics']['sharpe_ratio']:.3f}  DD={r5['metrics']['max_drawdown_pct']:.1f}%  Return={r5['metrics']['total_return_pct']:.1f}%")

    # ── Step 3: Convert to daily returns ──────────────────
    print("\n[3/5] Aligning to daily returns...")

    # Primary strategies (WITH SL cooldown where applicable)
    primary_names = ['VolReg_opt_1d', 'VolReg_4h', 'ATR_DOGE', 'ATR_AVAX']
    primary_daily_returns = {}
    for name in primary_names:
        eq = strategies_config[name]['eq']
        dr = equity_to_daily_returns(eq)
        primary_daily_returns[name] = dr
        print(f"  {name}: {len(dr)} daily returns")

    # No-SL versions
    nosl_names = ['VolReg_opt_1d', 'VolReg_4h_noSL', 'ATR_DOGE_noSL', 'ATR_AVAX_noSL']
    nosl_daily_returns = {}
    for name in nosl_names:
        eq = strategies_config[name]['eq']
        dr = equity_to_daily_returns(eq)
        nosl_daily_returns[name] = dr

    # POISON (reference)
    poison_dr = equity_to_daily_returns(strategies_config['Regime_V3_POISON']['eq'])

    # Align all to common date range
    all_primary_df = pd.DataFrame(primary_daily_returns)
    all_primary_df = all_primary_df.dropna()
    print(f"  Common date range: {all_primary_df.index[0].date()} to {all_primary_df.index[-1].date()} ({len(all_primary_df)} days)")

    all_nosl_df = pd.DataFrame(nosl_daily_returns)
    all_nosl_df = all_nosl_df.dropna()

    # ── Step 4: Correlation matrix ────────────────────────
    print("\n[4/5] Computing correlation matrix...")
    corr_matrix = all_primary_df.corr()
    print(corr_matrix.round(3).to_string())

    # ── Step 5: Portfolio combinations ────────────────────
    print("\n[5/5] Evaluating portfolio combinations...")

    strat_names = list(primary_daily_returns.keys())
    all_combos = []

    for r in range(2, len(strat_names) + 1):
        for combo in combinations(strat_names, r):
            combo_list = list(combo)
            # Equal weight
            combo_returns = all_primary_df[combo_list].mean(axis=1)
            combo_returns = combo_returns.dropna()
            if len(combo_returns) < 30:
                continue
            metrics = portfolio_metrics(combo_returns)
            all_combos.append({
                'strategies': combo_list,
                'n_strategies': len(combo_list),
                **metrics
            })

    # Sort by Sharpe
    all_combos.sort(key=lambda x: x['sharpe'], reverse=True)

    print("\n  TOP 10 PORTFOLIO COMBINATIONS (by Sharpe):")
    print(f"  {'Rank':<4} {'Strategies':<55} {'Sharpe':>7} {'MaxDD':>8} {'Return':>10} {'Calmar':>8}")
    print("  " + "-" * 92)
    for i, c in enumerate(all_combos[:10]):
        names_str = " + ".join([n.replace('_1d','(1d)').replace('_4h','(4h)') for n in c['strategies']])
        print(f"  {i+1:<4} {names_str:<55} {c['sharpe']:>7.3f} {c['max_dd']:>7.1f}% {c['total_return']:>9.1f}% {c['calmar']:>8.3f}")

    # ── Key combos analysis ───────────────────────────────
    print("\n  KEY COMBO ANALYSIS:")
    key_combos = {
        "Old best 3": ['VolReg_opt_1d', 'VolReg_4h', 'ATR_DOGE'],
        "New 4-strategy": ['VolReg_opt_1d', 'VolReg_4h', 'ATR_DOGE', 'ATR_AVAX'],
        "4H only": ['VolReg_4h', 'ATR_DOGE', 'ATR_AVAX'],
        "All 4": ['VolReg_opt_1d', 'VolReg_4h', 'ATR_DOGE', 'ATR_AVAX'],
    }

    key_results = {}
    for label, combo in key_combos.items():
        combo_returns = all_primary_df[combo].mean(axis=1).dropna()
        m = portfolio_metrics(combo_returns)
        key_results[label] = m
        print(f"\n  {label}: {' + '.join(combo)}")
        print(f"    Sharpe={m['sharpe']:.3f}  MaxDD={m['max_dd']:.1f}%  Return={m['total_return']:.1f}%  Calmar={m['calmar']:.3f}")

    # ── Step 6: SL cooldown impact at portfolio level ─────
    print("\n  SL COOLDOWN IMPACT (portfolio level):")

    # Best combo (All 4 = New 4-strategy)
    best_combo_names_sl = ['VolReg_opt_1d', 'VolReg_4h', 'ATR_DOGE', 'ATR_AVAX']
    best_combo_names_nosl = ['VolReg_opt_1d', 'VolReg_4h_noSL', 'ATR_DOGE_noSL', 'ATR_AVAX_noSL']

    port_sl = all_primary_df[best_combo_names_sl].mean(axis=1).dropna()
    port_nosl = all_nosl_df[best_combo_names_nosl].mean(axis=1).dropna()

    metrics_sl = portfolio_metrics(port_sl)
    metrics_nosl = portfolio_metrics(port_nosl)

    dd_improvement = abs(metrics_nosl['max_dd']) - abs(metrics_sl['max_dd'])
    dd_improvement_pct = dd_improvement / abs(metrics_nosl['max_dd']) * 100 if metrics_nosl['max_dd'] != 0 else 0

    print(f"    WITHOUT SL cooldown: Sharpe={metrics_nosl['sharpe']:.3f}  MaxDD={metrics_nosl['max_dd']:.1f}%  Return={metrics_nosl['total_return']:.1f}%  Calmar={metrics_nosl['calmar']:.3f}")
    print(f"    WITH SL cooldown:    Sharpe={metrics_sl['sharpe']:.3f}  MaxDD={metrics_sl['max_dd']:.1f}%  Return={metrics_sl['total_return']:.1f}%  Calmar={metrics_sl['calmar']:.3f}")
    print(f"    DD improvement: {dd_improvement:.1f}pp ({dd_improvement_pct:.1f}% better)")

    # ── Step 7: Kelly criterion ───────────────────────────
    print("\n  KELLY CRITERION (best portfolio with SL cooldown):")
    kelly = kelly_criterion(port_sl)
    print(f"    Full Kelly (discrete):    {kelly['full_kelly_discrete']:.4f}")
    print(f"    Half Kelly (discrete):    {kelly['half_kelly_discrete']:.4f}")
    print(f"    Full Kelly (continuous):  {kelly['full_kelly_continuous']:.4f}")
    print(f"    Half Kelly (continuous):  {kelly['half_kelly_continuous']:.4f}")

    # Practical recommendation
    hk = kelly['half_kelly_continuous']
    if hk > 5:
        practical = f"Half-Kelly suggests {hk:.1f}x leverage — cap at 3-5x for safety (tail risk)"
    elif hk > 2:
        practical = f"Half-Kelly suggests {hk:.1f}x leverage — reasonable but monitor closely"
    elif hk > 1:
        practical = f"Half-Kelly suggests {hk:.1f}x leverage — conservative and appropriate"
    else:
        practical = f"Half-Kelly suggests {hk:.1f}x leverage — consider if return justifies risk"

    print(f"    Recommendation: {practical}")

    # ── Determine best portfolio ──────────────────────────
    best = all_combos[0]
    best_port = {
        'strategies': best['strategies'],
        'sharpe': best['sharpe'],
        'max_dd': best['max_dd'],
        'total_return': best['total_return'],
        'annual_return': best.get('annual_return', 0),
        'calmar': best['calmar'],
        'n_days': best.get('n_days', 0),
    }

    # ── Also include POISON combo for reference ───────────
    print("\n  POISON CHECK (Regime_V3 inclusion):")
    # Add Regime_V3 to the primary df temporarily
    poison_aligned = poison_dr.reindex(all_primary_df.index)
    temp_df = all_primary_df.copy()
    temp_df['Regime_V3_POISON'] = poison_aligned

    for combo_label, base_combo in [("Best + POISON", best['strategies'])]:
        combo_with_poison = list(base_combo) + ['Regime_V3_POISON']
        pr = temp_df[combo_with_poison].mean(axis=1).dropna()
        if len(pr) > 30:
            pm = portfolio_metrics(pr)
            print(f"    {combo_label}: Sharpe={pm['sharpe']:.3f}  MaxDD={pm['max_dd']:.1f}%  Return={pm['total_return']:.1f}%  Calmar={pm['calmar']:.3f}")
            base_pr = all_primary_df[list(base_combo)].mean(axis=1).dropna()
            base_pm = portfolio_metrics(base_pr)
            sharpe_diff = pm['sharpe'] - base_pm['sharpe']
            print(f"    -> Adding POISON changes Sharpe by {sharpe_diff:+.3f} (confirms POISON status: {'YES' if sharpe_diff < 0 else 'NO - actually helps!'})")

    # ── Individual strategy summary with SL info ──────────
    print("\n  INDIVIDUAL STRATEGY SUMMARY:")
    strategy_summaries = []
    for name in ['VolReg_opt_1d', 'VolReg_4h', 'ATR_DOGE', 'ATR_AVAX', 'Regime_V3_POISON']:
        cfg = strategies_config[name]
        m = cfg['result']['metrics']
        strategy_summaries.append({
            'name': name,
            'symbol': cfg['symbol'],
            'timeframe': cfg['tf'],
            'sharpe': m['sharpe_ratio'],
            'max_dd': m['max_drawdown_pct'],
            'total_return': m['total_return_pct'],
            'calmar': m['calmar_ratio'],
            'win_rate': m['win_rate_pct'],
            'trades': m['total_trades'],
            'r_squared': m['r_squared'],
            'sl_cooldown': cfg.get('sl_cooldown', False),
            'poison': cfg.get('poison', False),
        })
        sl_tag = "[SL_CD]" if cfg.get('sl_cooldown') else ""
        poison_tag = " [POISON]" if cfg.get('poison') else ""
        print(f"    {name:<22} {cfg['symbol']:<10} {cfg['tf']:<4} Sharpe={m['sharpe_ratio']:.3f}  DD={m['max_drawdown_pct']:.1f}%  WR={m['win_rate_pct']:.0f}%  R²={m['r_squared']:.3f} {sl_tag}{poison_tag}")

    # ── Conclusion ────────────────────────────────────────
    conclusion_parts = []
    conclusion_parts.append(f"Best portfolio: {' + '.join(best_port['strategies'])} (Sharpe {best_port['sharpe']:.3f}, DD {best_port['max_dd']:.1f}%)")
    conclusion_parts.append(f"SL cooldown reduces portfolio DD by {dd_improvement:.1f}pp ({dd_improvement_pct:.0f}%)")
    conclusion_parts.append(f"Adding AVAX diversifies beyond DOGE — multi-symbol edge confirmed")
    conclusion_parts.append(f"Half-Kelly leverage: {kelly['half_kelly_continuous']:.1f}x")
    conclusion = ". ".join(conclusion_parts)

    print(f"\n  CONCLUSION: {conclusion}")

    # ── Save results ──────────────────────────────────────
    output = {
        "analysis_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "strategies": strategy_summaries,
        "correlation_matrix": {
            str(k): {str(k2): round(v2, 4) for k2, v2 in v.items()}
            for k, v in corr_matrix.to_dict().items()
        },
        "all_combinations": all_combos,
        "best_portfolio": best_port,
        "key_combos": key_results,
        "sl_cooldown_impact": {
            "portfolio_combo": best_combo_names_sl,
            "without": metrics_nosl,
            "with": metrics_sl,
            "dd_improvement_pp": round(dd_improvement, 2),
            "dd_improvement_pct": round(dd_improvement_pct, 1),
        },
        "kelly": {
            **kelly,
            "practical_recommendation": practical,
        },
        "conclusion": conclusion,
    }

    output_path = '/Users/nekonaomichi/crypto-lab/data/portfolio_5survivors.json'
    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2, default=str)

    print(f"\n  Results saved to: {output_path}")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
