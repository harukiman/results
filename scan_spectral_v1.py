"""Spectral/Frequency-Domain Signal Scan v1 — 3 families on 4H crypto data.

Families:
  1. DominantCycle (FFT-based cycle detection + EMA direction)
  2. SpectralEntropy (frequency-domain entropy filter + EMA direction)
  3. WaveletEnergy (Haar wavelet trend/noise energy ratio + EMA direction)

IS/OOS 70/30 split. Permutation test for healthy OOS configs.
Correlation check against ATR-ratio (volatility proxy) to detect redundancy.
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


# ── Signal Family 1: Dominant Cycle (FFT-based) ────────────────────────

def dominant_cycle_signal(df, fft_window=60, power_threshold=0.3, ema_fast=14, ema_slow=40):
    """Detect dominant cycle via FFT. Trade EMA direction only when strong cycle present."""
    returns = df['close'].pct_change().fillna(0).values
    n = len(df)
    has_cycle = np.zeros(n, dtype=bool)

    for i in range(fft_window, n):
        window = returns[i - fft_window:i]
        window_centered = window - window.mean()
        fft_vals = np.fft.rfft(window_centered)
        power = np.abs(fft_vals) ** 2
        freqs = np.fft.rfftfreq(len(window_centered))
        # Valid frequency range: skip DC and very high freq
        valid = (freqs > 0.02) & (freqs < 0.45)
        if not valid.any():
            continue
        power_valid = power[valid]
        total_power = power_valid.sum()
        if total_power < 1e-20:
            continue
        dom_power_ratio = power_valid.max() / total_power
        if dom_power_ratio > power_threshold:
            has_cycle[i] = True

    ema_f = df['close'].ewm(span=ema_fast).mean()
    ema_s = df['close'].ewm(span=ema_slow).mean()

    signals = pd.Series(0, index=df.index)
    cycle_mask = pd.Series(has_cycle, index=df.index)
    signals[cycle_mask & (ema_f > ema_s)] = 1
    signals[cycle_mask & (ema_f < ema_s)] = -1
    return signals


DOMINANT_CYCLE_GRID = {
    "fft_window": [30, 60, 90, 120],
    "power_threshold": [0.15, 0.20, 0.25, 0.30, 0.35],
    "ema_fast": [10, 14, 20],
    "ema_slow": [30, 40, 60],
}


# ── Signal Family 2: Spectral Entropy ──────────────────────────────────

def spectral_entropy_signal(df, se_window=60, se_pct=25, ema_fast=14, ema_slow=40):
    """Low spectral entropy = one frequency dominates = predictable. Trade EMA direction."""
    returns = df['close'].pct_change().fillna(0).values
    n = len(df)
    se_vals = np.full(n, np.nan)

    for i in range(se_window, n):
        window = returns[i - se_window:i]
        window_centered = window - window.mean()
        fft_vals = np.fft.rfft(window_centered)
        power = np.abs(fft_vals) ** 2
        power = power[1:]  # skip DC
        total = power.sum()
        if total < 1e-20:
            continue
        psd = power / total
        # Shannon entropy in frequency domain
        psd_pos = psd[psd > 0]
        se_vals[i] = -np.sum(psd_pos * np.log2(psd_pos))

    se_series = pd.Series(se_vals, index=df.index)
    # Expanding quantile threshold
    threshold = se_series.expanding().quantile(se_pct / 100.0)
    low_entropy = se_series < threshold

    ema_f = df['close'].ewm(span=ema_fast).mean()
    ema_s = df['close'].ewm(span=ema_slow).mean()

    signals = pd.Series(0, index=df.index)
    signals[low_entropy & (ema_f > ema_s)] = 1
    signals[low_entropy & (ema_f < ema_s)] = -1
    return signals


SPECTRAL_ENTROPY_GRID = {
    "se_window": [30, 50, 60, 90],
    "se_pct": [15, 20, 25, 30],
    "ema_fast": [10, 14, 20],
    "ema_slow": [30, 40, 60, 80],
}


# ── Signal Family 3: Wavelet Energy Ratio ──────────────────────────────

def wavelet_energy_signal(df, wav_window=64, energy_threshold=0.6, ema_fast=14, ema_slow=40):
    """Haar wavelet: compare low-freq (trend) vs high-freq (noise) energy.
    When trend energy dominates (ratio > threshold), trade EMA direction."""
    returns = df['close'].pct_change().fillna(0).values
    n = len(df)
    energy_ratio = np.full(n, np.nan)

    for i in range(wav_window, n):
        window = returns[i - wav_window:i]
        w_len = len(window)
        # Ensure even length for Haar
        if w_len % 2 != 0:
            window = window[1:]
        # 1-level Haar wavelet decomposition
        approx = (window[::2] + window[1::2]) / np.sqrt(2)
        detail = (window[::2] - window[1::2]) / np.sqrt(2)
        e_low = np.sum(approx ** 2)
        e_high = np.sum(detail ** 2)
        total = e_low + e_high
        if total < 1e-20:
            energy_ratio[i] = 0.5
        else:
            energy_ratio[i] = e_low / total

    er_series = pd.Series(energy_ratio, index=df.index)
    trending = er_series > energy_threshold

    ema_f = df['close'].ewm(span=ema_fast).mean()
    ema_s = df['close'].ewm(span=ema_slow).mean()

    signals = pd.Series(0, index=df.index)
    signals[trending & (ema_f > ema_s)] = 1
    signals[trending & (ema_f < ema_s)] = -1
    return signals


WAVELET_ENERGY_GRID = {
    "wav_window": [32, 48, 64, 96],
    "energy_threshold": [0.50, 0.55, 0.60, 0.65, 0.70],
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
    # Align and drop NaN
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
    print("  SPECTRAL/FREQUENCY-DOMAIN SIGNAL SCAN v1")
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

    # ── Correlation check: compute sample spectral indicators vs ATR ──
    print(f"\n{'='*70}")
    print("  REDUNDANCY CHECK: Spectral indicators vs ATR ratio")
    print(f"{'='*70}")

    atr_correlations = {}
    for sym, df in all_data.items():
        returns = df['close'].pct_change().fillna(0).values
        n = len(df)

        # Compute rolling dominant cycle power ratio (continuous indicator)
        dc_power = np.full(n, np.nan)
        se_vals = np.full(n, np.nan)
        we_vals = np.full(n, np.nan)

        for i in range(64, n):
            window = returns[i - 60:i]
            wc = window - window.mean()
            fft_v = np.fft.rfft(wc)
            power = np.abs(fft_v) ** 2
            freqs = np.fft.rfftfreq(len(wc))
            valid = (freqs > 0.02) & (freqs < 0.45)
            if valid.any():
                pv = power[valid]
                total = pv.sum()
                if total > 1e-20:
                    dc_power[i] = pv.max() / total

            # Spectral entropy
            power_all = power[1:]
            total_all = power_all.sum()
            if total_all > 1e-20:
                psd = power_all / total_all
                psd_pos = psd[psd > 0]
                se_vals[i] = -np.sum(psd_pos * np.log2(psd_pos))

            # Wavelet energy
            w64 = returns[i - 64:i]
            approx = (w64[::2] + w64[1::2]) / np.sqrt(2)
            detail = (w64[::2] - w64[1::2]) / np.sqrt(2)
            e_low = np.sum(approx ** 2)
            e_high = np.sum(detail ** 2)
            total_e = e_low + e_high
            we_vals[i] = e_low / total_e if total_e > 1e-20 else 0.5

        dc_series = pd.Series(dc_power, index=df.index)
        se_series = pd.Series(se_vals, index=df.index)
        we_series = pd.Series(we_vals, index=df.index)

        corr_dc = compute_signal_atr_correlation(dc_series, df)
        corr_se = compute_signal_atr_correlation(se_series, df)
        corr_we = compute_signal_atr_correlation(we_series, df)

        atr_correlations[sym] = {
            "DominantCycle_power_vs_ATR": round(corr_dc, 4),
            "SpectralEntropy_vs_ATR": round(corr_se, 4),
            "WaveletEnergy_vs_ATR": round(corr_we, 4),
        }
        print(f"\n  {sym}:")
        print(f"    DominantCycle power ratio vs ATR ratio: {corr_dc:+.4f}")
        print(f"    Spectral Entropy vs ATR ratio:          {corr_se:+.4f}")
        print(f"    Wavelet Energy ratio vs ATR ratio:      {corr_we:+.4f}")

    # ── Family scans ──
    families = {}

    # ── Family 1: Dominant Cycle ──
    print(f"\n{'='*70}")
    print("  FAMILY 1: Dominant Cycle (FFT-based)")
    print(f"{'='*70}")
    dc_grid = expand_grid(DOMINANT_CYCLE_GRID)
    print(f"  Signal param combos: {len(dc_grid)} | Symbols: {len(all_data)}")
    print(f"  Total configs: {len(dc_grid) * len(all_data)}")

    dc_results = []
    dc_total = 0
    for sym in all_data:
        df = all_data[sym]
        cost_params = get_cost_params(sym, INTERVAL)
        sym_count = 0
        sym_healthy = 0
        print(f"\n  {sym}:", end=" ", flush=True)

        for sp in dc_grid:
            dc_total += 1
            # Skip if ema_fast >= ema_slow
            if sp['ema_fast'] >= sp['ema_slow']:
                continue
            try:
                sigs = dominant_cycle_signal(df, **sp)
            except Exception:
                continue
            n_sig = int((sigs != 0).sum())
            if n_sig < 20:
                continue

            res = run_is_oos(df, sigs, sym, "DominantCycle", sp, cost_params)
            sym_count += 1
            if is_healthy(res):
                dc_results.append(res)
                sym_healthy += 1

        print(f"{sym_count} tested, {sym_healthy} healthy", flush=True)

    # Permutation test on healthy configs
    dc_perm_significant = []
    if dc_results:
        print(f"\n  Running permutation tests on {len(dc_results)} healthy DominantCycle configs...")
        for r in dc_results:
            pnls = np.array(r['oos_trade_pnls'])
            if len(pnls) < 10:
                continue
            perm = permutation_test(pnls, n_permutations=500, statistic="mean")
            r['perm_p_value'] = perm['p_value']
            r['perm_significant'] = perm['is_significant_05']
            if perm['is_significant_05']:
                dc_perm_significant.append(r)
                print(f"    ** SIGNIFICANT: {r['symbol']} p={perm['p_value']:.4f} "
                      f"OOS Sharpe={r['oos_sharpe']:.3f} IS Sharpe={r['is_sharpe']:.3f}")

    dc_summary = {
        "configs_tested": dc_total,
        "healthy_count": len(dc_results),
        "perm_significant_count": len(dc_perm_significant),
        "perm_significant": [],
        "verdict": "",
    }
    for r in dc_perm_significant:
        r_clean = {k: v for k, v in r.items() if k != 'oos_trade_pnls'}
        dc_summary["perm_significant"].append(r_clean)

    if len(dc_perm_significant) == 0:
        dc_summary["verdict"] = "FAIL: No configs pass IS/OOS + permutation test"
    elif all(r['symbol'] == 'SUIUSDT' for r in dc_perm_significant):
        dc_summary["verdict"] = "SUSPICIOUS: All significant configs are SUI-only (known OOS trend bias)"
    else:
        dc_summary["verdict"] = f"PASS: {len(dc_perm_significant)} configs are permutation-significant"

    families["DominantCycle"] = dc_summary
    print(f"\n  DominantCycle verdict: {dc_summary['verdict']}")

    # ── Family 2: Spectral Entropy ──
    print(f"\n{'='*70}")
    print("  FAMILY 2: Spectral Entropy")
    print(f"{'='*70}")
    se_grid = expand_grid(SPECTRAL_ENTROPY_GRID)
    print(f"  Signal param combos: {len(se_grid)} | Symbols: {len(all_data)}")
    print(f"  Total configs: {len(se_grid) * len(all_data)}")

    se_results = []
    se_total = 0
    for sym in all_data:
        df = all_data[sym]
        cost_params = get_cost_params(sym, INTERVAL)
        sym_count = 0
        sym_healthy = 0
        print(f"\n  {sym}:", end=" ", flush=True)

        for sp in se_grid:
            se_total += 1
            if sp['ema_fast'] >= sp['ema_slow']:
                continue
            try:
                sigs = spectral_entropy_signal(df, **sp)
            except Exception:
                continue
            n_sig = int((sigs != 0).sum())
            if n_sig < 20:
                continue

            res = run_is_oos(df, sigs, sym, "SpectralEntropy", sp, cost_params)
            sym_count += 1
            if is_healthy(res):
                se_results.append(res)
                sym_healthy += 1

        print(f"{sym_count} tested, {sym_healthy} healthy", flush=True)

    se_perm_significant = []
    if se_results:
        print(f"\n  Running permutation tests on {len(se_results)} healthy SpectralEntropy configs...")
        for r in se_results:
            pnls = np.array(r['oos_trade_pnls'])
            if len(pnls) < 10:
                continue
            perm = permutation_test(pnls, n_permutations=500, statistic="mean")
            r['perm_p_value'] = perm['p_value']
            r['perm_significant'] = perm['is_significant_05']
            if perm['is_significant_05']:
                se_perm_significant.append(r)
                print(f"    ** SIGNIFICANT: {r['symbol']} p={perm['p_value']:.4f} "
                      f"OOS Sharpe={r['oos_sharpe']:.3f} IS Sharpe={r['is_sharpe']:.3f}")

    se_summary = {
        "configs_tested": se_total,
        "healthy_count": len(se_results),
        "perm_significant_count": len(se_perm_significant),
        "perm_significant": [],
        "verdict": "",
    }
    for r in se_perm_significant:
        r_clean = {k: v for k, v in r.items() if k != 'oos_trade_pnls'}
        se_summary["perm_significant"].append(r_clean)

    if len(se_perm_significant) == 0:
        se_summary["verdict"] = "FAIL: No configs pass IS/OOS + permutation test"
    elif all(r['symbol'] == 'SUIUSDT' for r in se_perm_significant):
        se_summary["verdict"] = "SUSPICIOUS: All significant configs are SUI-only (known OOS trend bias)"
    else:
        se_summary["verdict"] = f"PASS: {len(se_perm_significant)} configs are permutation-significant"

    families["SpectralEntropy"] = se_summary
    print(f"\n  SpectralEntropy verdict: {se_summary['verdict']}")

    # ── Family 3: Wavelet Energy ──
    print(f"\n{'='*70}")
    print("  FAMILY 3: Wavelet Energy Ratio")
    print(f"{'='*70}")
    we_grid = expand_grid(WAVELET_ENERGY_GRID)
    print(f"  Signal param combos: {len(we_grid)} | Symbols: {len(all_data)}")
    print(f"  Total configs: {len(we_grid) * len(all_data)}")

    we_results = []
    we_total = 0
    for sym in all_data:
        df = all_data[sym]
        cost_params = get_cost_params(sym, INTERVAL)
        sym_count = 0
        sym_healthy = 0
        print(f"\n  {sym}:", end=" ", flush=True)

        for sp in we_grid:
            we_total += 1
            if sp['ema_fast'] >= sp['ema_slow']:
                continue
            try:
                sigs = wavelet_energy_signal(df, **sp)
            except Exception:
                continue
            n_sig = int((sigs != 0).sum())
            if n_sig < 20:
                continue

            res = run_is_oos(df, sigs, sym, "WaveletEnergy", sp, cost_params)
            sym_count += 1
            if is_healthy(res):
                we_results.append(res)
                sym_healthy += 1

        print(f"{sym_count} tested, {sym_healthy} healthy", flush=True)

    we_perm_significant = []
    if we_results:
        print(f"\n  Running permutation tests on {len(we_results)} healthy WaveletEnergy configs...")
        for r in we_results:
            pnls = np.array(r['oos_trade_pnls'])
            if len(pnls) < 10:
                continue
            perm = permutation_test(pnls, n_permutations=500, statistic="mean")
            r['perm_p_value'] = perm['p_value']
            r['perm_significant'] = perm['is_significant_05']
            if perm['is_significant_05']:
                we_perm_significant.append(r)
                print(f"    ** SIGNIFICANT: {r['symbol']} p={perm['p_value']:.4f} "
                      f"OOS Sharpe={r['oos_sharpe']:.3f} IS Sharpe={r['is_sharpe']:.3f}")

    we_summary = {
        "configs_tested": we_total,
        "healthy_count": len(we_results),
        "perm_significant_count": len(we_perm_significant),
        "perm_significant": [],
        "verdict": "",
    }
    for r in we_perm_significant:
        r_clean = {k: v for k, v in r.items() if k != 'oos_trade_pnls'}
        we_summary["perm_significant"].append(r_clean)

    if len(we_perm_significant) == 0:
        we_summary["verdict"] = "FAIL: No configs pass IS/OOS + permutation test"
    elif all(r['symbol'] == 'SUIUSDT' for r in we_perm_significant):
        we_summary["verdict"] = "SUSPICIOUS: All significant configs are SUI-only (known OOS trend bias)"
    else:
        we_summary["verdict"] = f"PASS: {len(we_perm_significant)} configs are permutation-significant"

    families["WaveletEnergy"] = we_summary
    print(f"\n  WaveletEnergy verdict: {we_summary['verdict']}")

    # ── Overall verdict ──
    total_configs = dc_total + se_total + we_total
    total_healthy = len(dc_results) + len(se_results) + len(we_results)
    total_perm = len(dc_perm_significant) + len(se_perm_significant) + len(we_perm_significant)

    # Check SUI-only problem
    all_perm = dc_perm_significant + se_perm_significant + we_perm_significant
    non_sui = [r for r in all_perm if r['symbol'] != 'SUIUSDT']

    if total_perm == 0:
        overall_verdict = "FAIL: Zero spectral/frequency-domain signals pass all filters. No edge found."
    elif len(non_sui) == 0:
        overall_verdict = (f"SUSPICIOUS: {total_perm} configs pass permutation but ALL are SUI-only. "
                          "Likely OOS trend bias, not genuine spectral edge.")
    elif len(non_sui) < 3:
        overall_verdict = (f"WEAK: Only {len(non_sui)} non-SUI configs pass. Insufficient evidence "
                          "for genuine spectral edge.")
    else:
        overall_verdict = (f"INTERESTING: {len(non_sui)} non-SUI configs pass all filters. "
                          "Worth investigating further.")

    # Check redundancy with volatility
    avg_corr = {}
    for indicator in ["DominantCycle_power_vs_ATR", "SpectralEntropy_vs_ATR", "WaveletEnergy_vs_ATR"]:
        vals = [atr_correlations[sym][indicator] for sym in atr_correlations]
        avg_corr[indicator] = round(np.mean(vals), 4)

    high_corr_indicators = [k for k, v in avg_corr.items() if abs(v) > 0.5]
    redundancy_note = ""
    if high_corr_indicators:
        redundancy_note = (f"WARNING: High ATR correlation detected in {high_corr_indicators}. "
                          "These may be proxying volatility, not providing independent spectral info.")

    conclusion_parts = []
    for fam_name, fam_data in families.items():
        conclusion_parts.append(f"{fam_name}: {fam_data['verdict']}")
    if redundancy_note:
        conclusion_parts.append(redundancy_note)

    elapsed = time.time() - t0

    output = {
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

    out_path = os.path.join(os.path.dirname(__file__), "data", "scan_spectral_v1.json")
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
