"""Diagnose VolReg_4h DOGE degradation.

Investigation: Sharpe dropped from 2.275 (validated) to -0.23 (portfolio run).
Key finding to test: portfolio_5survivors.py uses DIFFERENT params than validate_volreg_4h.py.

Validated params:  short_vol=20, long_vol=120, threshold=0.8, ema_fast=20, ema_slow=80
Portfolio params:  short_vol=10, long_vol=25, threshold=0.7, ema_fast=14, ema_slow=40
"""

import asyncio
import sys
import os
import json
import warnings
from datetime import datetime

sys.path.insert(0, '/Users/nekonaomichi/crypto-lab')
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd

from engine.data import fetch_klines
from engine.backtest import run_backtest
from engine.cost_config import get_cost_params

BARS_PER_YEAR_4H = 2190


# ── Signal generators ─────────────────────────────────────

def volreg_signal(df, short_vol=20, long_vol=120, threshold=0.8,
                  ema_fast=20, ema_slow=80):
    """VolReg signal with configurable params."""
    close = df['close']
    returns = close.pct_change()
    short_v = returns.rolling(short_vol).std()
    long_v = returns.rolling(long_vol).std()
    compression = short_v < long_v * threshold

    ema_f = close.ewm(span=ema_fast, adjust=False).mean()
    ema_s = close.ewm(span=ema_slow, adjust=False).mean()

    signals = pd.Series(0, index=df.index)
    signals[compression & (ema_f > ema_s)] = 1
    signals[compression & (ema_f < ema_s)] = -1

    warmup = max(long_vol, ema_slow) + 10
    signals.iloc[:warmup] = 0
    return signals


def run_bt(df, signals, name="test", sl=0.0, tp=0.0, mh=0,
           sl_cooldown=0, atr_sl_mult=0.0, atr_sl_period=14):
    """Run backtest with MEXC ALT cost model."""
    cost = get_cost_params("DOGEUSDT", "4h")
    res = run_backtest(
        df, signals,
        strategy_name=name,
        stop_loss_pct=sl,
        take_profit_pct=tp,
        max_hold_bars=mh,
        bars_per_year=BARS_PER_YEAR_4H,
        leverage=1.0,
        fee_rate=cost["fee_rate"],
        slippage_rate=cost["slippage_rate"],
        forced_exit_slippage=cost["forced_exit_slippage"],
        funding_rate_8h=cost["funding_rate_8h"],
        funding_interval_bars=cost["funding_interval_bars"],
        sl_cooldown_bars=sl_cooldown,
        atr_sl_mult=atr_sl_mult,
        atr_sl_period=atr_sl_period,
    )
    return res


def extract_metrics(res):
    m = res["metrics"]
    return {
        "sharpe": round(m.get("sharpe_ratio", 0), 3),
        "sortino": round(m.get("sortino_ratio", 0), 3),
        "total_return_pct": round(m.get("total_return_pct", 0), 2),
        "max_dd_pct": round(m.get("max_drawdown_pct", 0), 2),
        "trades": m.get("total_trades", 0),
        "win_rate": round(m.get("win_rate_pct", 0), 1),
        "profit_factor": round(m.get("profit_factor", 0), 3),
        "calmar": round(m.get("calmar_ratio", 0), 3),
        "r_squared": round(m.get("r_squared", 0), 4),
        "return_daily_pct": round(m.get("return_daily_pct", 0), 4),
    }


async def main():
    print("=" * 70)
    print("  DIAGNOSE VolReg_4h DOGE — Performance Degradation Investigation")
    print("=" * 70)
    print()

    # ── Fetch data ──
    print("[1/8] Fetching DOGEUSDT 4H data (730 days)...")
    df = await fetch_klines("DOGEUSDT", "4h", 730)
    n = len(df)
    print(f"  Bars: {n}")
    print(f"  Range: {df['open_time'].iloc[0]} to {df['open_time'].iloc[-1]}")

    results = {
        "diagnosis_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "data_bars": n,
        "data_range": f"{df['open_time'].iloc[0]} to {df['open_time'].iloc[-1]}",
    }

    # ── IS/OOS split ──
    split_idx = int(n * 0.70)
    df_is = df.iloc[:split_idx].reset_index(drop=True)
    df_oos = df.iloc[split_idx:].reset_index(drop=True)
    print(f"  IS: {len(df_is)} bars ({df['open_time'].iloc[0]} to {df['open_time'].iloc[split_idx-1]})")
    print(f"  OOS: {len(df_oos)} bars ({df['open_time'].iloc[split_idx]} to {df['open_time'].iloc[-1]})")

    # ══════════════════════════════════════════════════════════
    # [2] COMPARE: Validated params vs Portfolio params
    # ══════════════════════════════════════════════════════════
    print("\n[2/8] Comparing VALIDATED params vs PORTFOLIO params...")

    # Validated params (from validate_volreg_4h.py)
    validated_params = dict(short_vol=20, long_vol=120, threshold=0.8,
                            ema_fast=20, ema_slow=80)
    validated_risk = dict(sl=0.05, tp=0.06, mh=42)

    # Portfolio params (from portfolio_5survivors.py — DIFFERENT!)
    portfolio_params = dict(short_vol=10, long_vol=25, threshold=0.7,
                            ema_fast=14, ema_slow=40)
    portfolio_risk = dict(sl=0.0, tp=0.0, mh=0,
                          sl_cooldown=50, atr_sl_mult=2.0, atr_sl_period=14)

    # Run validated params on full data
    sig_val = volreg_signal(df, **validated_params)
    res_val_full = run_bt(df, sig_val, "validated_full", **validated_risk)
    res_val_norisk = run_bt(df, sig_val, "validated_norisk")

    # Run portfolio params on full data
    sig_port = volreg_signal(df, **portfolio_params)
    res_port_full = run_bt(df, sig_port, "portfolio_full", **portfolio_risk)
    res_port_norisk = run_bt(df, sig_port, "portfolio_norisk")

    # Run portfolio params WITHOUT sl_cooldown/atr_sl (to isolate signal vs risk mgmt)
    res_port_plain = run_bt(df, sig_port, "portfolio_plain")

    m_val = extract_metrics(res_val_full)
    m_val_nr = extract_metrics(res_val_norisk)
    m_port = extract_metrics(res_port_full)
    m_port_nr = extract_metrics(res_port_norisk)
    m_port_pl = extract_metrics(res_port_plain)

    print(f"\n  VALIDATED params (SV=20, LV=120, TH=0.8, EF=20, ES=80):")
    print(f"    With risk (SL=5%, TP=6%, MH=42):  Sharpe={m_val['sharpe']:.3f}  DD={m_val['max_dd_pct']:.1f}%  Return={m_val['total_return_pct']:.1f}%  Trades={m_val['trades']}")
    print(f"    No risk management:                Sharpe={m_val_nr['sharpe']:.3f}  DD={m_val_nr['max_dd_pct']:.1f}%  Return={m_val_nr['total_return_pct']:.1f}%  Trades={m_val_nr['trades']}")

    print(f"\n  PORTFOLIO params (SV=10, LV=25, TH=0.7, EF=14, ES=40):")
    print(f"    With risk (ATR_SL=2x, CD=50):      Sharpe={m_port['sharpe']:.3f}  DD={m_port['max_dd_pct']:.1f}%  Return={m_port['total_return_pct']:.1f}%  Trades={m_port['trades']}")
    print(f"    No risk management:                Sharpe={m_port_nr['sharpe']:.3f}  DD={m_port_nr['max_dd_pct']:.1f}%  Return={m_port_nr['total_return_pct']:.1f}%  Trades={m_port_nr['trades']}")
    print(f"    Plain (no SL/TP/CD):               Sharpe={m_port_pl['sharpe']:.3f}  DD={m_port_pl['max_dd_pct']:.1f}%  Return={m_port_pl['total_return_pct']:.1f}%  Trades={m_port_pl['trades']}")

    results["param_comparison"] = {
        "validated_params": {
            "signal_params": validated_params,
            "risk_params": validated_risk,
            "with_risk": m_val,
            "no_risk": m_val_nr,
        },
        "portfolio_params": {
            "signal_params": portfolio_params,
            "risk_params": portfolio_risk,
            "with_risk": m_port,
            "no_risk": m_port_nr,
            "plain": m_port_pl,
        },
        "CRITICAL_FINDING": "Portfolio uses DIFFERENT params than validation! Params were silently changed.",
    }

    # ══════════════════════════════════════════════════════════
    # [3] IS/OOS breakdown for BOTH param sets
    # ══════════════════════════════════════════════════════════
    print("\n[3/8] IS/OOS breakdown...")

    is_oos_results = {}
    for label, params, risk in [
        ("validated", validated_params, validated_risk),
        ("portfolio", portfolio_params, dict(sl=0.0, tp=0.0, mh=0, sl_cooldown=50, atr_sl_mult=2.0, atr_sl_period=14)),
    ]:
        sig_is = volreg_signal(df_is, **params)
        sig_oos = volreg_signal(df_oos, **params)

        r_is = run_bt(df_is, sig_is, f"{label}_IS", **risk)
        r_oos = run_bt(df_oos, sig_oos, f"{label}_OOS", **risk)

        is_oos_results[label] = {
            "IS": extract_metrics(r_is),
            "OOS": extract_metrics(r_oos),
        }
        m_is = extract_metrics(r_is)
        m_oos = extract_metrics(r_oos)
        print(f"  {label:12s} IS:  Sharpe={m_is['sharpe']:.3f}  DD={m_is['max_dd_pct']:.1f}%  Return={m_is['total_return_pct']:.1f}%  Trades={m_is['trades']}")
        print(f"  {label:12s} OOS: Sharpe={m_oos['sharpe']:.3f}  DD={m_oos['max_dd_pct']:.1f}%  Return={m_oos['total_return_pct']:.1f}%  Trades={m_oos['trades']}")

    results["is_oos"] = is_oos_results

    # ══════════════════════════════════════════════════════════
    # [4] 6-month rolling window analysis — WHEN did it break?
    # ══════════════════════════════════════════════════════════
    print("\n[4/8] Rolling 6-month window analysis...")

    window_bars = 6 * 30 * 6  # ~6 months of 4H bars (1080)
    step_bars = 30 * 6  # 1-month steps (180)

    rolling_results = {"validated": [], "portfolio": []}

    for label, params, risk in [
        ("validated", validated_params, validated_risk),
        ("portfolio", portfolio_params, dict(sl=0.0, tp=0.0, mh=0, sl_cooldown=50, atr_sl_mult=2.0, atr_sl_period=14)),
    ]:
        i = 0
        while i + window_bars <= n:
            df_win = df.iloc[i:i + window_bars].reset_index(drop=True)
            sig_win = volreg_signal(df_win, **params)
            r_win = run_bt(df_win, sig_win, f"window_{i}", **risk)
            m_win = extract_metrics(r_win)

            window_start = str(df['open_time'].iloc[i])[:10]
            window_end = str(df['open_time'].iloc[min(i + window_bars - 1, n - 1)])[:10]

            rolling_results[label].append({
                "window": f"{window_start} to {window_end}",
                "start_idx": i,
                "sharpe": m_win["sharpe"],
                "total_return_pct": m_win["total_return_pct"],
                "max_dd_pct": m_win["max_dd_pct"],
                "trades": m_win["trades"],
                "win_rate": m_win["win_rate"],
            })
            i += step_bars

    print(f"\n  VALIDATED params — rolling 6-month windows:")
    for w in rolling_results["validated"]:
        status = "OK" if w["sharpe"] > 0 else "BROKEN"
        print(f"    {w['window']}  Sharpe={w['sharpe']:+.3f}  DD={w['max_dd_pct']:.1f}%  Ret={w['total_return_pct']:+.1f}%  [{status}]")

    print(f"\n  PORTFOLIO params — rolling 6-month windows:")
    for w in rolling_results["portfolio"]:
        status = "OK" if w["sharpe"] > 0 else "BROKEN"
        print(f"    {w['window']}  Sharpe={w['sharpe']:+.3f}  DD={w['max_dd_pct']:.1f}%  Ret={w['total_return_pct']:+.1f}%  [{status}]")

    results["rolling_windows"] = rolling_results

    # ══════════════════════════════════════════════════════════
    # [5] Signal frequency over time
    # ══════════════════════════════════════════════════════════
    print("\n[5/8] Signal frequency analysis...")

    signal_freq = {}
    for label, params in [("validated", validated_params), ("portfolio", portfolio_params)]:
        sig = volreg_signal(df, **params)

        # Quarterly frequency
        quarters = []
        q_size = n // 8
        for q in range(8):
            start = q * q_size
            end = min((q + 1) * q_size, n)
            chunk = sig.iloc[start:end]
            active = (chunk != 0).sum()
            long_pct = (chunk == 1).sum() / len(chunk) * 100
            short_pct = (chunk == -1).sum() / len(chunk) * 100
            flat_pct = (chunk == 0).sum() / len(chunk) * 100

            period_start = str(df['open_time'].iloc[start])[:10]
            period_end = str(df['open_time'].iloc[min(end - 1, n - 1)])[:10]

            quarters.append({
                "period": f"{period_start} to {period_end}",
                "active_pct": round((long_pct + short_pct), 1),
                "long_pct": round(long_pct, 1),
                "short_pct": round(short_pct, 1),
                "flat_pct": round(flat_pct, 1),
            })

        signal_freq[label] = quarters

    print(f"\n  VALIDATED params — signal frequency by quarter:")
    for q in signal_freq["validated"]:
        print(f"    {q['period']}  Active={q['active_pct']:.1f}%  Long={q['long_pct']:.1f}%  Short={q['short_pct']:.1f}%  Flat={q['flat_pct']:.1f}%")

    print(f"\n  PORTFOLIO params — signal frequency by quarter:")
    for q in signal_freq["portfolio"]:
        print(f"    {q['period']}  Active={q['active_pct']:.1f}%  Long={q['long_pct']:.1f}%  Short={q['short_pct']:.1f}%  Flat={q['flat_pct']:.1f}%")

    results["signal_frequency"] = signal_freq

    # ══════════════════════════════════════════════════════════
    # [6] DOGE volatility regime analysis
    # ══════════════════════════════════════════════════════════
    print("\n[6/8] DOGE volatility regime analysis...")

    returns = df['close'].pct_change()
    vol_analysis = {}

    for label, params in [("validated", validated_params), ("portfolio", portfolio_params)]:
        short_v = returns.rolling(params["short_vol"]).std()
        long_v = returns.rolling(params["long_vol"]).std()
        ratio = (short_v / long_v).dropna()
        compression = short_v < long_v * params["threshold"]

        # Quarterly vol regime
        vol_quarters = []
        q_size = n // 8
        for q in range(8):
            start = q * q_size
            end = min((q + 1) * q_size, n)

            r_chunk = ratio.iloc[start:end].dropna()
            c_chunk = compression.iloc[start:end].dropna()
            sv_chunk = short_v.iloc[start:end].dropna()
            lv_chunk = long_v.iloc[start:end].dropna()

            period_start = str(df['open_time'].iloc[start])[:10]
            period_end = str(df['open_time'].iloc[min(end - 1, n - 1)])[:10]

            vol_quarters.append({
                "period": f"{period_start} to {period_end}",
                "mean_vol_ratio": round(float(r_chunk.mean()), 3) if len(r_chunk) > 0 else 0,
                "compression_pct": round(float(c_chunk.sum() / len(c_chunk) * 100), 1) if len(c_chunk) > 0 else 0,
                "mean_short_vol": round(float(sv_chunk.mean() * 100), 3) if len(sv_chunk) > 0 else 0,
                "mean_long_vol": round(float(lv_chunk.mean() * 100), 3) if len(lv_chunk) > 0 else 0,
            })

        vol_analysis[label] = vol_quarters

    print(f"\n  VALIDATED params — vol regime by quarter:")
    for q in vol_analysis["validated"]:
        print(f"    {q['period']}  Ratio={q['mean_vol_ratio']:.3f}  Compression={q['compression_pct']:.1f}%  ShortVol={q['mean_short_vol']:.3f}%  LongVol={q['mean_long_vol']:.3f}%")

    print(f"\n  PORTFOLIO params — vol regime by quarter:")
    for q in vol_analysis["portfolio"]:
        print(f"    {q['period']}  Ratio={q['mean_vol_ratio']:.3f}  Compression={q['compression_pct']:.1f}%  ShortVol={q['mean_short_vol']:.3f}%  LongVol={q['mean_long_vol']:.3f}%")

    results["volatility_regime"] = vol_analysis

    # ══════════════════════════════════════════════════════════
    # [7] Parameter sensitivity grid
    # ══════════════════════════════════════════════════════════
    print("\n[7/8] Parameter sensitivity grid...")

    param_grid = []
    thresholds = [0.65, 0.70, 0.72, 0.75, 0.80, 0.85]
    long_vols = [25, 35, 40, 50, 80, 120]

    for th in thresholds:
        for lv in long_vols:
            sv = max(5, lv // 4)  # short_vol ~ 25% of long_vol
            ef = max(8, lv // 6)  # ema_fast
            es = max(20, lv // 2)  # ema_slow

            sig = volreg_signal(df, short_vol=sv, long_vol=lv,
                                threshold=th, ema_fast=ef, ema_slow=es)
            res = run_bt(df, sig, f"grid_th{th}_lv{lv}")
            m = extract_metrics(res)

            # Also run OOS only
            sig_oos = volreg_signal(df_oos, short_vol=sv, long_vol=lv,
                                    threshold=th, ema_fast=ef, ema_slow=es)
            res_oos = run_bt(df_oos, sig_oos, f"grid_oos_th{th}_lv{lv}")
            m_oos = extract_metrics(res_oos)

            entry = {
                "threshold": th, "long_vol": lv, "short_vol": sv,
                "ema_fast": ef, "ema_slow": es,
                "full_sharpe": m["sharpe"],
                "full_dd": m["max_dd_pct"],
                "full_return": m["total_return_pct"],
                "full_trades": m["trades"],
                "oos_sharpe": m_oos["sharpe"],
                "oos_dd": m_oos["max_dd_pct"],
                "oos_return": m_oos["total_return_pct"],
            }
            param_grid.append(entry)

    # Sort by OOS sharpe
    param_grid.sort(key=lambda x: x["oos_sharpe"], reverse=True)

    print(f"\n  Top 10 param combos by OOS Sharpe:")
    print(f"  {'TH':>5s} {'LV':>4s} {'SV':>4s} {'EF':>4s} {'ES':>4s} | {'Full_Sh':>8s} {'Full_DD':>8s} {'Full_Ret':>9s} | {'OOS_Sh':>8s} {'OOS_DD':>8s} {'OOS_Ret':>9s}")
    for g in param_grid[:10]:
        print(f"  {g['threshold']:>5.2f} {g['long_vol']:>4d} {g['short_vol']:>4d} {g['ema_fast']:>4d} {g['ema_slow']:>4d} | "
              f"{g['full_sharpe']:>+8.3f} {g['full_dd']:>7.1f}% {g['full_return']:>+8.1f}% | "
              f"{g['oos_sharpe']:>+8.3f} {g['oos_dd']:>7.1f}% {g['oos_return']:>+8.1f}%")

    print(f"\n  Bottom 5 param combos (worst OOS):")
    for g in param_grid[-5:]:
        print(f"  {g['threshold']:>5.2f} {g['long_vol']:>4d} {g['short_vol']:>4d} {g['ema_fast']:>4d} {g['ema_slow']:>4d} | "
              f"{g['full_sharpe']:>+8.3f} {g['full_dd']:>7.1f}% {g['full_return']:>+8.1f}% | "
              f"{g['oos_sharpe']:>+8.3f} {g['oos_dd']:>7.1f}% {g['oos_return']:>+8.1f}%")

    results["param_sensitivity"] = param_grid

    # ══════════════════════════════════════════════════════════
    # [8] Root cause summary
    # ══════════════════════════════════════════════════════════
    print("\n[8/8] ROOT CAUSE ANALYSIS...")

    val_sharpe = m_val["sharpe"]
    port_sharpe = m_port["sharpe"]

    # Check if validated params still work
    val_still_works = val_sharpe > 1.0

    # Check if portfolio params ever worked
    port_ever_worked = any(w["sharpe"] > 1.0 for w in rolling_results["portfolio"])

    # Check if it's a regime change vs param mismatch
    param_mismatch = True  # We already confirmed params are different

    # Find best OOS params
    best_oos = param_grid[0] if param_grid else None
    any_oos_positive = any(g["oos_sharpe"] > 0.5 for g in param_grid)

    conclusion_parts = []

    if param_mismatch:
        conclusion_parts.append(
            f"PRIMARY CAUSE: Parameter mismatch between validation and portfolio. "
            f"Validated params (SV=20,LV=120,TH=0.8) Sharpe={val_sharpe:.3f}. "
            f"Portfolio params (SV=10,LV=25,TH=0.7) Sharpe={port_sharpe:.3f}."
        )

    if val_still_works:
        conclusion_parts.append(
            f"FIXABLE: Validated params still produce Sharpe={val_sharpe:.3f}. "
            f"Fix portfolio_5survivors.py gen_volreg_4h_signals() to use correct params."
        )
    else:
        conclusion_parts.append(
            f"REGIME CHANGE: Even validated params now show Sharpe={val_sharpe:.3f}. "
            f"DOGE volatility regime may have fundamentally changed."
        )

    if any_oos_positive and best_oos:
        conclusion_parts.append(
            f"BEST OOS: TH={best_oos['threshold']}, LV={best_oos['long_vol']} "
            f"gives OOS Sharpe={best_oos['oos_sharpe']:.3f}."
        )
    else:
        conclusion_parts.append(
            "NO OOS-POSITIVE params found. Strategy concept may be dead for DOGE."
        )

    conclusion = " | ".join(conclusion_parts)

    print(f"\n  {'='*60}")
    for part in conclusion_parts:
        print(f"  {part}")
    print(f"  {'='*60}")

    results["conclusion"] = {
        "primary_cause": "parameter_mismatch" if param_mismatch and val_still_works else "regime_change",
        "validated_params_sharpe": val_sharpe,
        "portfolio_params_sharpe": port_sharpe,
        "validated_still_works": val_still_works,
        "any_oos_positive": any_oos_positive,
        "best_oos_config": best_oos,
        "fixable": val_still_works,
        "summary": conclusion,
    }

    # ── Save results ──
    output_path = '/Users/nekonaomichi/crypto-lab/data/diagnose_volreg4h.json'
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\nResults saved to {output_path}")


if __name__ == "__main__":
    asyncio.run(main())
