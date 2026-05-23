"""Wave H — Regime Analysis + TOP4 Compact Portfolio + Regime-Filtered Variants.

Goal:
  1. Characterize F2-F3 regime where ATR_Ratio fails (BTC vol, funding, momentum)
  2. Compare TOP4 (INJ/DOGE/OP/SHIB) vs 8-symbol portfolio
  3. Test regime-filtered variants: vol-down position scaling, full-stop, BTC-trend filter
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
from engine.data import fetch_klines, fetch_bybit_funding_rate
from engine.backtest import run_backtest
from engine.cost_config import get_cost_params

SYMBOLS_8 = ["OPUSDT", "WIFUSDT", "INJUSDT", "BONKUSDT",
             "DOGEUSDT", "SHIBUSDT", "ARBUSDT", "LINKUSDT"]
SYMBOLS_TOP4 = ["INJUSDT", "DOGEUSDT", "OPUSDT", "SHIBUSDT"]  # WF avg >= +2.0

ATR_PARAMS = {"atr_short": 7, "atr_long": 56, "threshold": 0.6,
              "ema_fast": 20, "ema_slow": 80}
EXIT = {"stop_loss_pct": 0.04, "take_profit_pct": 0.08, "max_hold_bars": 24}
DAYS = 730
BARS_PER_YEAR = 2190


def atr_ratio_signal(df, atr_short=7, atr_long=56, threshold=0.6,
                     ema_fast=20, ema_slow=80):
    atr_s = (df['high'] - df['low']).rolling(atr_short).mean()
    atr_l = (df['high'] - df['low']).rolling(atr_long).mean()
    compression = atr_s < atr_l * threshold
    ema_f = df['close'].ewm(span=ema_fast).mean()
    ema_s = df['close'].ewm(span=ema_slow).mean()
    sig = pd.Series(0, index=df.index)
    sig[compression & (ema_f > ema_s)] = 1
    sig[compression & (ema_f < ema_s)] = -1
    warmup = max(atr_long, ema_slow) + 5
    sig.iloc[:warmup] = 0
    return sig


def run_bt(df, sig, sym):
    cost = get_cost_params(sym, "4h")
    return run_backtest(df, sig, strategy_name="ATR_Ratio",
                        bars_per_year=BARS_PER_YEAR, leverage=1.0,
                        **EXIT, **cost)


def equity_to_daily_returns(eq):
    eq = np.asarray(eq, dtype=float)
    daily = eq[5::6]
    if len(daily) < 2:
        daily = eq[::6]
    ret = np.diff(daily) / np.where(daily[:-1] != 0, daily[:-1], 1.0)
    return ret


def sharpe(r, ppy=365):
    r = np.asarray(r)
    r = r[np.isfinite(r)]
    if len(r) < 5 or np.std(r, ddof=1) == 0:
        return 0.0
    return float(np.mean(r) / np.std(r, ddof=1) * np.sqrt(ppy))


def portfolio_metrics(daily_ret_df):
    """Compute portfolio Sharpe, total return, max DD from equal-weight daily returns."""
    port_ret = daily_ret_df.mean(axis=1)
    port_sh = sharpe(port_ret.values, ppy=365)
    port_cum = (1 + port_ret).cumprod()
    total_ret = float((port_cum.iloc[-1] - 1) * 100)
    dd = float((port_cum / port_cum.cummax() - 1).min() * 100)
    return port_sh, total_ret, dd, port_ret


# ── Regime analysis ────────────────────────────────────────────────────────

async def analyze_regime():
    """Characterize each fold's BTC market regime."""
    print("\n=== F1-F4 REGIME CHARACTERIZATION ===\n")
    btc = await fetch_klines("BTCUSDT", "4h", DAYS)
    print(f"BTC data: {len(btc)} bars, range {btc['open_time'].min()} → {btc['open_time'].max()}")

    n = len(btc)
    fold_size = n // 5
    folds_meta = []
    for i in range(5):
        s, e = fold_size * i, min(fold_size * (i + 1), n)
        sub = btc.iloc[s:e].reset_index(drop=True)
        rets = sub['close'].pct_change().dropna()
        ann_vol = rets.std() * np.sqrt(2190) * 100
        ret_total = (sub['close'].iloc[-1] / sub['close'].iloc[0] - 1) * 100
        # Range/Trend ratio: |total_return| / sum(|bar_returns|)
        sum_abs = rets.abs().sum() * 100
        trend_eff = abs(ret_total) / sum_abs if sum_abs > 0 else 0
        # ATR_Ratio activation rate
        atr_s = (sub['high'] - sub['low']).rolling(7).mean()
        atr_l = (sub['high'] - sub['low']).rolling(56).mean()
        comp = (atr_s < atr_l * 0.6).sum()
        comp_rate = comp / len(sub) * 100

        folds_meta.append({
            "fold": i,
            "start": str(sub['open_time'].iloc[0])[:10],
            "end": str(sub['open_time'].iloc[-1])[:10],
            "bars": len(sub),
            "btc_return_pct": round(ret_total, 1),
            "btc_ann_vol_pct": round(ann_vol, 1),
            "trend_efficiency": round(trend_eff, 3),
            "atr_compression_rate_pct": round(comp_rate, 1),
        })
        label = ["F0(WF train)", "F1", "F2", "F3", "F4"][i]
        print(f"  {label:<14} {folds_meta[i]['start']} → {folds_meta[i]['end']}  "
              f"ret={ret_total:+.1f}%  vol={ann_vol:.1f}%  "
              f"trend_eff={trend_eff:.2f}  atr_comp_rate={comp_rate:.1f}%")
    return folds_meta, btc


# ── Portfolio runner ───────────────────────────────────────────────────────

async def run_portfolio(symbols, label, regime_filter_fn=None, regime_label=None):
    """Run equal-weight ATR portfolio over given symbols, optional regime filter."""
    print(f"\n--- {label}", f"({regime_label})" if regime_label else "", "---")
    daily_returns = {}
    individual = {}
    for s in symbols:
        df = await fetch_klines(s, "4h", DAYS)
        sig = atr_ratio_signal(df, **ATR_PARAMS)
        if regime_filter_fn is not None:
            sig = regime_filter_fn(df, sig)
        n_sig = (sig != 0).sum()
        if n_sig < 5:
            individual[s] = {"sharpe": 0, "return_pct": 0, "trades": 0, "dd": 0}
            daily_returns[s] = np.zeros(180)
            continue
        r = run_bt(df, sig, s)
        m = r["metrics"]
        individual[s] = {
            "sharpe": round(float(m.get("sharpe_ratio") or 0), 3),
            "return_pct": round(float(m.get("total_return_pct") or 0), 2),
            "dd": round(float(m.get("max_drawdown_pct") or 0), 2),
            "trades": int(m.get("total_trades") or 0),
        }
        daily_returns[s] = equity_to_daily_returns(r["equity_curve"])

    # Align lengths
    min_len = min(len(v) for v in daily_returns.values())
    aligned = {s: v[:min_len] for s, v in daily_returns.items()}
    df_ret = pd.DataFrame(aligned)
    port_sh, total_ret, dd, _ = portfolio_metrics(df_ret)

    print(f"  銘柄数: {len(symbols)}")
    for s, m in individual.items():
        print(f"    {s:<10} Sh={m['sharpe']:+.2f} ret={m['return_pct']:+.1f}% "
              f"dd={m['dd']:+.1f}% trades={m['trades']}")
    print(f"  ポートフォリオ: Sh={port_sh:+.2f}  ret={total_ret:+.1f}%  dd={dd:+.1f}%  "
          f"Calmar={abs(total_ret/dd) if dd != 0 else 0:.2f}")

    return {
        "label": label, "regime_label": regime_label, "symbols": symbols,
        "individual": individual,
        "portfolio": {
            "sharpe": round(port_sh, 3),
            "return_pct": round(total_ret, 2),
            "max_dd_pct": round(dd, 2),
            "calmar": round(abs(total_ret/dd) if dd != 0 else 0, 2),
        }
    }


# ── Regime filters (vol-based, computed from BTC) ──────────────────────────

async def build_btc_vol_zscore():
    """Build BTC realized vol Z-score series aligned to bar dates."""
    btc = await fetch_klines("BTCUSDT", "4h", DAYS)
    btc['ret'] = btc['close'].pct_change()
    btc['rv60'] = btc['ret'].rolling(60).std() * np.sqrt(2190) * 100  # ~10 day rolling annualized vol
    btc['rv60_mean'] = btc['rv60'].rolling(360).mean()  # ~60 day baseline
    btc['rv60_std'] = btc['rv60'].rolling(360).std()
    btc['rv60_z'] = (btc['rv60'] - btc['rv60_mean']) / (btc['rv60_std'] + 1e-10)
    return btc[['open_time', 'rv60', 'rv60_z']].copy()


def make_regime_filter(btc_vol_df, vol_z_threshold, mode="off"):
    """Returns a filter function that masks signals when BTC vol_z >= threshold."""
    btc_vol_df = btc_vol_df.set_index('open_time')
    def _filter(df, sig):
        # Align BTC vol to df's open_time
        df_dates = df['open_time']
        aligned = btc_vol_df.reindex(df_dates, method='ffill')['rv60_z'].values
        bad_regime = aligned >= vol_z_threshold
        bad_regime = pd.Series(bad_regime, index=sig.index).fillna(False)
        if mode == "off":
            sig_filtered = sig.copy()
            sig_filtered[bad_regime] = 0
            return sig_filtered
        elif mode == "half":
            # Signal is binary; "half" means halve position size — but engine uses binary sig.
            # Approximate: zero out 50% of high-vol bars (every other)
            sig_filtered = sig.copy()
            half_mask = bad_regime & (np.arange(len(sig)) % 2 == 0)
            sig_filtered[half_mask] = 0
            return sig_filtered
        return sig
    return _filter


# ── Main ────────────────────────────────────────────────────────────────────

async def main():
    t0 = time.time()
    print("=== Wave H: Regime Analysis + Compact Portfolio + Filtered Variants ===")

    folds_meta, btc = await analyze_regime()

    btc_vol = await build_btc_vol_zscore()

    # Baseline: 8-symbol unfiltered
    base_8 = await run_portfolio(SYMBOLS_8, "Baseline 8銘柄 (unfiltered)")

    # TOP4 compact
    top4 = await run_portfolio(SYMBOLS_TOP4, "TOP4 INJ/DOGE/OP/SHIB")

    # Regime-filtered 8-symbol — try several vol_z thresholds
    filters_to_try = [
        ("vol_z>=0.5 → off", 0.5, "off"),
        ("vol_z>=1.0 → off", 1.0, "off"),
        ("vol_z>=1.5 → off", 1.5, "off"),
        ("vol_z>=1.0 → half", 1.0, "half"),
    ]
    filtered_results = []
    for name, thr, mode in filters_to_try:
        filt = make_regime_filter(btc_vol, thr, mode)
        r = await run_portfolio(SYMBOLS_8, f"8銘柄+filter({name})", filt, name)
        filtered_results.append(r)

    # ── Compare and pick winner ───────────────────────────────────────────
    all_results = [base_8, top4] + filtered_results
    print("\n\n=== SUMMARY TABLE ===")
    print(f"{'Variant':<40} {'Sharpe':>8} {'Return%':>9} {'DD%':>8} {'Calmar':>8}")
    for r in all_results:
        p = r["portfolio"]
        print(f"  {r['label']:<38} {p['sharpe']:>+8.2f} {p['return_pct']:>+9.1f} "
              f"{p['max_dd_pct']:>+8.1f} {p['calmar']:>8.2f}")

    # Save
    out = {
        "wave": "H",
        "name": "Regime Analysis + Compact Portfolio + Filtered Variants",
        "generated_at": datetime.now(timezone(timedelta(hours=9))).strftime("%Y-%m-%d %H:%M JST"),
        "folds": folds_meta,
        "results": all_results,
        "runtime_sec": round(time.time() - t0, 1),
    }
    Path("/Users/nekonaomichi/crypto-lab/wave_h_regime.json").write_text(json.dumps(out, indent=2, default=str))
    print(f"\nSaved to wave_h_regime.json (runtime {out['runtime_sec']}s)")


if __name__ == "__main__":
    asyncio.run(main())
