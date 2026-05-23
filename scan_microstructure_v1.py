"""Candlestick Microstructure Signal Scan v1 — 3 families on 4H crypto data.

Families:
  1. BodyShadowRatio (body/range ratio regime + EMA direction)
  2. ClosePosition (close within high-low range + EMA direction)
  3. RangeContractionStreak (consecutive narrow bars + EMA direction)

IS/OOS 70/30 split. Permutation test for healthy OOS configs.
Correlation check: RangeContraction vs ATR ratio (redundancy flag if >0.3).
"""
import asyncio
import itertools
import json
import sys
import os
import time
import warnings
warnings.filterwarnings("ignore")

sys.path.insert(0, os.path.dirname(__file__))

import numpy as np
import pandas as pd

from engine.data import fetch_klines
from engine.backtest import run_backtest
from engine.cost_config import get_cost_params
from engine.statistical_tests import permutation_test

SYMBOLS = ["DOGEUSDT", "SUIUSDT", "SOLUSDT"]
INTERVAL = "4h"
DAYS = 730
BARS_PER_YEAR = 2190
IS_RATIO = 0.70

# Fixed SL/TP/Hold per spec
SL_PCT = 0.03
TP_PCT = 0.10
MAX_HOLD = 42


# ── Signal Family 1: Body-Shadow Ratio Regime ────────────────────────────

def body_shadow_signal(df, bs_window=20, bs_threshold=0.65, ema_fast=14, ema_slow=40):
    """High body/range ratio = directional conviction. Trade EMA direction when conviction is high."""
    body = (df['close'] - df['open']).abs()
    total_range = df['high'] - df['low']
    body_ratio = body / (total_range + 1e-10)
    rolling_br = body_ratio.rolling(bs_window).mean()
    # High body ratio = conviction/trending
    conviction = rolling_br > bs_threshold
    ema_f = df['close'].ewm(span=ema_fast).mean()
    ema_s = df['close'].ewm(span=ema_slow).mean()
    signals = pd.Series(0, index=df.index)
    signals[conviction & (ema_f > ema_s)] = 1
    signals[conviction & (ema_f < ema_s)] = -1
    return signals


BODY_SHADOW_GRID = {
    "bs_window": [10, 15, 20, 30],
    "bs_threshold": [0.50, 0.55, 0.60, 0.65, 0.70],
    "ema_fast": [10, 14, 20],
    "ema_slow": [30, 40, 60, 80],
}


# ── Signal Family 2: Close Position Within Range ─────────────────────────

def close_position_signal(df, cp_window=15, cp_upper=0.65, cp_lower=0.35, ema_fast=14, ema_slow=40):
    """Close position: 0=at low, 1=at high. Persistent close near extremes = directional pressure."""
    cp = (df['close'] - df['low']) / (df['high'] - df['low'] + 1e-10)
    rolling_cp = cp.rolling(cp_window).mean()
    ema_f = df['close'].ewm(span=ema_fast).mean()
    ema_s = df['close'].ewm(span=ema_slow).mean()
    signals = pd.Series(0, index=df.index)
    # Bullish: close consistently near highs AND trend up
    signals[(rolling_cp > cp_upper) & (ema_f > ema_s)] = 1
    # Bearish: close consistently near lows AND trend down
    signals[(rolling_cp < cp_lower) & (ema_f < ema_s)] = -1
    return signals


CLOSE_POSITION_GRID = {
    "cp_window": [10, 15, 20, 30],
    "cp_upper": [0.55, 0.60, 0.65, 0.70],
    "cp_lower": [0.30, 0.35, 0.40, 0.45],
    "ema_fast": [10, 14, 20],
    "ema_slow": [30, 40, 60],
}


# ── Signal Family 3: Range Contraction Streak ────────────────────────────

def range_streak_signal(df, streak_window=30, streak_threshold=5, range_pct=0.7, ema_fast=14, ema_slow=40):
    """Count consecutive bars where range < rolling average * range_pct.
    Sustained contraction = building energy for breakout."""
    bar_range = df['high'] - df['low']
    avg_range = bar_range.rolling(streak_window).mean()
    contracted = bar_range < avg_range * range_pct
    # Count consecutive contracted bars
    streak = pd.Series(0, index=df.index, dtype=int)
    contracted_vals = contracted.values
    streak_vals = streak.values
    for i in range(1, len(df)):
        if contracted_vals[i]:
            streak_vals[i] = streak_vals[i-1] + 1
        else:
            streak_vals[i] = 0
    breakout = streak >= streak_threshold
    ema_f = df['close'].ewm(span=ema_fast).mean()
    ema_s = df['close'].ewm(span=ema_slow).mean()
    signals = pd.Series(0, index=df.index)
    signals[breakout & (ema_f > ema_s)] = 1
    signals[breakout & (ema_f < ema_s)] = -1
    return signals


RANGE_STREAK_GRID = {
    "streak_window": [15, 20, 30, 50],
    "streak_threshold": [3, 4, 5, 7],
    "range_pct": [0.5, 0.6, 0.7, 0.8],
    "ema_fast": [10, 14, 20],
    "ema_slow": [30, 40, 60],
}


# ── Utility ─────────────────────────────────────────────────────────────

def expand_grid(d):
    keys = list(d.keys())
    vals = [d[k] for k in keys]
    return [dict(zip(keys, combo)) for combo in itertools.product(*vals)]


def compute_atr_ratio(df, period=14):
    """ATR / close ratio — proxy for volatility. Used for redundancy check."""
    high = df['high'].values
    low = df['low'].values
    close = df['close'].values
    tr = np.zeros(len(df))
    for i in range(1, len(df)):
        tr[i] = max(high[i] - low[i], abs(high[i] - close[i-1]), abs(low[i] - close[i-1]))
    atr = pd.Series(tr, index=df.index).rolling(period).mean()
    return atr / df['close']


def compute_signal_atr_correlation(signal_indicator, df, period=14):
    """Correlation between a continuous indicator and ATR ratio.
    High correlation means the signal is just proxying volatility."""
    atr_ratio = compute_atr_ratio(df, period)
    combined = pd.DataFrame({'indicator': signal_indicator, 'atr_ratio': atr_ratio}).dropna()
    if len(combined) < 50:
        return 0.0
    return float(combined['indicator'].corr(combined['atr_ratio']))


def run_is_oos(df, signals, symbol, strat_name, params, cost_params):
    """Run IS/OOS backtest, return result dict or None."""
    n = len(df)
    is_end = int(n * IS_RATIO)

    df_is = df.iloc[:is_end].reset_index(drop=True)
    df_oos = df.iloc[is_end:].reset_index(drop=True)
    sig_is = signals.iloc[:is_end].reset_index(drop=True)
    sig_oos = signals.iloc[is_end:].reset_index(drop=True)

    try:
        res_is = run_backtest(
            df_is, sig_is,
            strategy_name=strat_name,
            params=params,
            stop_loss_pct=SL_PCT,
            take_profit_pct=TP_PCT,
            max_hold_bars=MAX_HOLD,
            bars_per_year=BARS_PER_YEAR,
            leverage=1.0,
            **cost_params,
        )
        res_oos = run_backtest(
            df_oos, sig_oos,
            strategy_name=strat_name,
            params=params,
            stop_loss_pct=SL_PCT,
            take_profit_pct=TP_PCT,
            max_hold_bars=MAX_HOLD,
            bars_per_year=BARS_PER_YEAR,
            leverage=1.0,
            **cost_params,
        )
    except Exception as e:
        return None

    is_trades = res_is['metrics'].get('total_trades', 0)
    oos_trades = res_oos['metrics'].get('total_trades', 0)
    is_sharpe = res_is['metrics'].get('sharpe_ratio', 0)
    oos_sharpe = res_oos['metrics'].get('sharpe_ratio', 0)
    is_daily = res_is['metrics'].get('return_daily_pct', 0)
    oos_daily = res_oos['metrics'].get('return_daily_pct', 0)

    if is_trades < 10 or oos_trades < 5:
        return None

    # Extract per-trade returns for permutation test
    oos_trade_pnls = [t['pnl_pct'] for t in res_oos.get('trades', [])]

    return {
        "symbol": symbol,
        "strategy": strat_name,
        "params": params,
        "is_sharpe": round(is_sharpe, 3),
        "oos_sharpe": round(oos_sharpe, 3),
        "is_trades": is_trades,
        "oos_trades": oos_trades,
        "is_return_daily_pct": round(is_daily, 4),
        "oos_return_daily_pct": round(oos_daily, 4),
        "is_max_dd": round(res_is['metrics'].get('max_drawdown_pct', 0), 2),
        "oos_max_dd": round(res_oos['metrics'].get('max_drawdown_pct', 0), 2),
        "is_win_rate": round(res_is['metrics'].get('win_rate_pct', 0), 1),
        "oos_win_rate": round(res_oos['metrics'].get('win_rate_pct', 0), 1),
        "is_pf": round(res_is['metrics'].get('profit_factor', 0), 2),
        "oos_pf": round(res_oos['metrics'].get('profit_factor', 0), 2),
        "oos_trade_pnls": oos_trade_pnls,
    }


def is_healthy(r):
    """Check if IS/OOS result passes health criteria.
    IS > 0.5, OOS > 1.0, ratio < 3x (anti-overfit)."""
    if r is None:
        return False
    is_s = r['is_sharpe']
    oos_s = r['oos_sharpe']
    if is_s < 0.5 or oos_s < 1.0:
        return False
    if is_s > 0 and oos_s > 0:
        ratio = is_s / oos_s
        if ratio > 3.0:
            return False
    return True


async def main():
    t0 = time.time()
    print("=" * 90)
    print("  CANDLESTICK MICROSTRUCTURE SIGNAL SCAN v1")
    print("  3 Families x 3 Symbols | 4H | IS/OOS 70/30 | SL=3% TP=10% Hold=42")
    print("=" * 90)

    # ── Fetch data ──
    all_data = {}
    for sym in SYMBOLS:
        print(f"\n  Fetching {sym} {INTERVAL} ({DAYS}d)...", end=" ", flush=True)
        try:
            df = await fetch_klines(sym, INTERVAL, DAYS)
            if df is not None and len(df) > 500:
                all_data[sym] = df
                print(f"{len(df)} bars OK")
            else:
                print("SKIP (insufficient data)")
        except Exception as e:
            print(f"ERROR: {e}")

    if not all_data:
        print("No data fetched. Aborting.")
        return

    # ── Correlation check: RangeContraction vs ATR (redundancy) ──
    # Also compute continuous indicators for Body-Shadow and Close-Position
    print(f"\n{'='*70}")
    print("  REDUNDANCY CHECK: Microstructure indicators vs ATR ratio")
    print(f"{'='*70}")

    atr_correlations = {}
    for sym, df in all_data.items():
        n = len(df)

        # Body-shadow ratio (continuous, rolling mean)
        body = (df['close'] - df['open']).abs()
        total_range = df['high'] - df['low']
        body_ratio = body / (total_range + 1e-10)
        rolling_br = body_ratio.rolling(20).mean()

        # Close position (continuous, rolling mean)
        cp = (df['close'] - df['low']) / (df['high'] - df['low'] + 1e-10)
        rolling_cp = cp.rolling(15).mean()

        # Range contraction indicator: rolling ratio of current range to avg range
        bar_range = df['high'] - df['low']
        avg_range = bar_range.rolling(30).mean()
        range_ratio = bar_range / (avg_range + 1e-10)

        corr_bs = compute_signal_atr_correlation(rolling_br, df)
        corr_cp = compute_signal_atr_correlation(rolling_cp, df)
        corr_rc = compute_signal_atr_correlation(range_ratio, df)

        atr_correlations[sym] = {
            "BodyShadowRatio_vs_ATR": round(corr_bs, 4),
            "ClosePosition_vs_ATR": round(corr_cp, 4),
            "RangeContraction_vs_ATR": round(corr_rc, 4),
        }
        print(f"\n  {sym}:")
        print(f"    Body-Shadow ratio vs ATR ratio:    {corr_bs:+.4f}")
        print(f"    Close Position vs ATR ratio:        {corr_cp:+.4f}")
        print(f"    Range Contraction vs ATR ratio:     {corr_rc:+.4f}")
        if abs(corr_rc) > 0.3:
            print(f"    *** WARNING: RangeContraction corr={corr_rc:+.4f} > 0.3 — likely ATR proxy ***")

    # ── Family 1: Body-Shadow Ratio ──
    print(f"\n{'='*70}")
    print("  FAMILY 1: Body-Shadow Ratio Regime")
    print(f"{'='*70}")
    bs_grid = expand_grid(BODY_SHADOW_GRID)
    print(f"  Signal param combos: {len(bs_grid)} | Symbols: {len(all_data)}")
    print(f"  Total configs: {len(bs_grid) * len(all_data)}")

    bs_results = []
    bs_total = 0
    for sym in all_data:
        df = all_data[sym]
        cost_params = get_cost_params(sym, INTERVAL)
        sym_count = 0
        sym_healthy = 0
        print(f"\n  {sym}:", end=" ", flush=True)

        for sp in bs_grid:
            bs_total += 1
            if sp['ema_fast'] >= sp['ema_slow']:
                continue
            try:
                sigs = body_shadow_signal(df, **sp)
            except Exception:
                continue
            n_sig = int((sigs != 0).sum())
            if n_sig < 20:
                continue

            res = run_is_oos(df, sigs, sym, "BodyShadowRatio", sp, cost_params)
            sym_count += 1
            if is_healthy(res):
                bs_results.append(res)
                sym_healthy += 1

        print(f"{sym_count} tested, {sym_healthy} healthy", flush=True)

    # Permutation test on healthy configs
    bs_perm_significant = []
    if bs_results:
        print(f"\n  Running permutation tests on {len(bs_results)} healthy BodyShadowRatio configs...")
        for r in bs_results:
            pnls = np.array(r['oos_trade_pnls'])
            if len(pnls) < 10:
                continue
            perm = permutation_test(pnls, n_permutations=500, statistic="mean")
            r['perm_p_value'] = perm['p_value']
            r['perm_significant'] = perm['is_significant_05']
            if perm['is_significant_05']:
                bs_perm_significant.append(r)
                print(f"    ** SIGNIFICANT: {r['symbol']} p={perm['p_value']:.4f} "
                      f"OOS Sharpe={r['oos_sharpe']:.3f} IS Sharpe={r['is_sharpe']:.3f}")

    bs_summary = {
        "configs_tested": bs_total,
        "healthy_count": len(bs_results),
        "perm_significant_count": len(bs_perm_significant),
        "perm_significant": [],
        "verdict": "",
    }
    for r in bs_perm_significant:
        r_clean = {k: v for k, v in r.items() if k != 'oos_trade_pnls'}
        bs_summary["perm_significant"].append(r_clean)

    if len(bs_perm_significant) == 0:
        bs_summary["verdict"] = "FAIL: No configs pass IS/OOS + permutation test"
    elif all(r['symbol'] == 'SUIUSDT' for r in bs_perm_significant):
        bs_summary["verdict"] = "SUSPICIOUS: All significant configs are SUI-only (known OOS trend bias)"
    else:
        bs_summary["verdict"] = f"PASS: {len(bs_perm_significant)} configs are permutation-significant"

    families = {}
    families["BodyShadowRatio"] = bs_summary
    print(f"\n  BodyShadowRatio verdict: {bs_summary['verdict']}")

    # ── Family 2: Close Position ──
    print(f"\n{'='*70}")
    print("  FAMILY 2: Close Position Within Range")
    print(f"{'='*70}")
    cp_grid = expand_grid(CLOSE_POSITION_GRID)
    print(f"  Signal param combos: {len(cp_grid)} | Symbols: {len(all_data)}")
    print(f"  Total configs: {len(cp_grid) * len(all_data)}")

    cp_results = []
    cp_total = 0
    for sym in all_data:
        df = all_data[sym]
        cost_params = get_cost_params(sym, INTERVAL)
        sym_count = 0
        sym_healthy = 0
        print(f"\n  {sym}:", end=" ", flush=True)

        for sp in cp_grid:
            cp_total += 1
            if sp['ema_fast'] >= sp['ema_slow']:
                continue
            try:
                sigs = close_position_signal(df, **sp)
            except Exception:
                continue
            n_sig = int((sigs != 0).sum())
            if n_sig < 20:
                continue

            res = run_is_oos(df, sigs, sym, "ClosePosition", sp, cost_params)
            sym_count += 1
            if is_healthy(res):
                cp_results.append(res)
                sym_healthy += 1

        print(f"{sym_count} tested, {sym_healthy} healthy", flush=True)

    cp_perm_significant = []
    if cp_results:
        print(f"\n  Running permutation tests on {len(cp_results)} healthy ClosePosition configs...")
        for r in cp_results:
            pnls = np.array(r['oos_trade_pnls'])
            if len(pnls) < 10:
                continue
            perm = permutation_test(pnls, n_permutations=500, statistic="mean")
            r['perm_p_value'] = perm['p_value']
            r['perm_significant'] = perm['is_significant_05']
            if perm['is_significant_05']:
                cp_perm_significant.append(r)
                print(f"    ** SIGNIFICANT: {r['symbol']} p={perm['p_value']:.4f} "
                      f"OOS Sharpe={r['oos_sharpe']:.3f} IS Sharpe={r['is_sharpe']:.3f}")

    cp_summary = {
        "configs_tested": cp_total,
        "healthy_count": len(cp_results),
        "perm_significant_count": len(cp_perm_significant),
        "perm_significant": [],
        "verdict": "",
    }
    for r in cp_perm_significant:
        r_clean = {k: v for k, v in r.items() if k != 'oos_trade_pnls'}
        cp_summary["perm_significant"].append(r_clean)

    if len(cp_perm_significant) == 0:
        cp_summary["verdict"] = "FAIL: No configs pass IS/OOS + permutation test"
    elif all(r['symbol'] == 'SUIUSDT' for r in cp_perm_significant):
        cp_summary["verdict"] = "SUSPICIOUS: All significant configs are SUI-only (known OOS trend bias)"
    else:
        cp_summary["verdict"] = f"PASS: {len(cp_perm_significant)} configs are permutation-significant"

    families["ClosePosition"] = cp_summary
    print(f"\n  ClosePosition verdict: {cp_summary['verdict']}")

    # ── Family 3: Range Contraction Streak ──
    print(f"\n{'='*70}")
    print("  FAMILY 3: Range Contraction Streak")
    print(f"{'='*70}")
    rc_grid = expand_grid(RANGE_STREAK_GRID)
    print(f"  Signal param combos: {len(rc_grid)} | Symbols: {len(all_data)}")
    print(f"  Total configs: {len(rc_grid) * len(all_data)}")

    rc_results = []
    rc_total = 0
    for sym in all_data:
        df = all_data[sym]
        cost_params = get_cost_params(sym, INTERVAL)
        sym_count = 0
        sym_healthy = 0
        print(f"\n  {sym}:", end=" ", flush=True)

        for sp in rc_grid:
            rc_total += 1
            if sp['ema_fast'] >= sp['ema_slow']:
                continue
            try:
                sigs = range_streak_signal(df, **sp)
            except Exception:
                continue
            n_sig = int((sigs != 0).sum())
            if n_sig < 20:
                continue

            res = run_is_oos(df, sigs, sym, "RangeContractionStreak", sp, cost_params)
            sym_count += 1
            if is_healthy(res):
                rc_results.append(res)
                sym_healthy += 1

        print(f"{sym_count} tested, {sym_healthy} healthy", flush=True)

    rc_perm_significant = []
    if rc_results:
        print(f"\n  Running permutation tests on {len(rc_results)} healthy RangeContractionStreak configs...")
        for r in rc_results:
            pnls = np.array(r['oos_trade_pnls'])
            if len(pnls) < 10:
                continue
            perm = permutation_test(pnls, n_permutations=500, statistic="mean")
            r['perm_p_value'] = perm['p_value']
            r['perm_significant'] = perm['is_significant_05']
            if perm['is_significant_05']:
                rc_perm_significant.append(r)
                print(f"    ** SIGNIFICANT: {r['symbol']} p={perm['p_value']:.4f} "
                      f"OOS Sharpe={r['oos_sharpe']:.3f} IS Sharpe={r['is_sharpe']:.3f}")

    rc_summary = {
        "configs_tested": rc_total,
        "healthy_count": len(rc_results),
        "perm_significant_count": len(rc_perm_significant),
        "perm_significant": [],
        "verdict": "",
    }
    for r in rc_perm_significant:
        r_clean = {k: v for k, v in r.items() if k != 'oos_trade_pnls'}
        rc_summary["perm_significant"].append(r_clean)

    if len(rc_perm_significant) == 0:
        rc_summary["verdict"] = "FAIL: No configs pass IS/OOS + permutation test"
    elif all(r['symbol'] == 'SUIUSDT' for r in rc_perm_significant):
        rc_summary["verdict"] = "SUSPICIOUS: All significant configs are SUI-only (known OOS trend bias)"
    else:
        rc_summary["verdict"] = f"PASS: {len(rc_perm_significant)} configs are permutation-significant"

    families["RangeContractionStreak"] = rc_summary
    print(f"\n  RangeContractionStreak verdict: {rc_summary['verdict']}")

    # ── Overall verdict ──
    total_configs = bs_total + cp_total + rc_total
    total_healthy = len(bs_results) + len(cp_results) + len(rc_results)
    total_perm = len(bs_perm_significant) + len(cp_perm_significant) + len(rc_perm_significant)

    # Check SUI-only problem
    all_perm = bs_perm_significant + cp_perm_significant + rc_perm_significant
    non_sui = [r for r in all_perm if r['symbol'] != 'SUIUSDT']

    if total_perm == 0:
        overall_verdict = "FAIL: Zero candlestick microstructure signals pass all filters. No edge found."
    elif len(non_sui) == 0:
        overall_verdict = (f"SUSPICIOUS: {total_perm} configs pass permutation but ALL are SUI-only. "
                          "Likely OOS trend bias, not genuine microstructure edge.")
    elif len(non_sui) < 3:
        overall_verdict = (f"WEAK: Only {len(non_sui)} non-SUI configs pass. Insufficient evidence "
                          "for genuine microstructure edge.")
    else:
        overall_verdict = (f"INTERESTING: {len(non_sui)} non-SUI configs pass all filters. "
                          "Worth investigating further.")

    # Check redundancy with volatility (especially RangeContraction)
    avg_corr = {}
    for indicator in ["BodyShadowRatio_vs_ATR", "ClosePosition_vs_ATR", "RangeContraction_vs_ATR"]:
        vals = [atr_correlations[sym][indicator] for sym in atr_correlations]
        avg_corr[indicator] = round(np.mean(vals), 4)

    redundancy_notes = []
    # Special focus on RangeContraction as instructed
    rc_avg = abs(avg_corr.get("RangeContraction_vs_ATR", 0))
    if rc_avg > 0.3:
        redundancy_notes.append(
            f"REDUNDANT: RangeContraction avg|corr|={rc_avg:.4f} with ATR ratio (>0.3 threshold). "
            "This is essentially an ATR compression proxy — NOT an independent microstructure signal."
        )
    # Check others too
    for indicator, val in avg_corr.items():
        if indicator == "RangeContraction_vs_ATR":
            continue
        if abs(val) > 0.5:
            redundancy_notes.append(
                f"WARNING: {indicator} avg|corr|={abs(val):.4f} > 0.5 — may be proxying volatility."
            )

    redundancy_note = " | ".join(redundancy_notes) if redundancy_notes else ""

    conclusion_parts = []
    for fam_name, fam_data in families.items():
        conclusion_parts.append(f"{fam_name}: {fam_data['verdict']}")
    if redundancy_note:
        conclusion_parts.append(redundancy_note)

    elapsed = time.time() - t0

    output = {
        "scan_name": "microstructure_v1",
        "scan_date": "2026-05-23",
        "total_configs": total_configs,
        "total_healthy": total_healthy,
        "total_perm_significant": total_perm,
        "elapsed_seconds": round(elapsed, 1),
        "atr_correlations": atr_correlations,
        "avg_atr_correlation": avg_corr,
        "redundancy_note": redundancy_note,
        "families": families,
        "overall_verdict": overall_verdict,
        "conclusion": " | ".join(conclusion_parts),
    }

    out_path = os.path.join(os.path.dirname(__file__), "data", "scan_microstructure_v1.json")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, 'w') as f:
        json.dump(output, f, indent=2, default=str)
    print(f"\n{'='*70}")
    print(f"  RESULTS SAVED: {out_path}")
    print(f"  Total configs: {total_configs} | Healthy: {total_healthy} | Perm significant: {total_perm}")
    print(f"  Elapsed: {elapsed:.1f}s")
    print(f"\n  OVERALL: {overall_verdict}")
    if redundancy_note:
        print(f"  {redundancy_note}")
    print(f"{'='*70}")


if __name__ == "__main__":
    asyncio.run(main())
