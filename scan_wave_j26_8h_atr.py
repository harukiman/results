"""Wave J26 — 8H ATR Portfolio deep dive.

Wave J25 で発見: 8H が 4H より mean Sharpe 良い (BTC/ETH/AVAX/ADA/LINK/DOGE 6銘柄テスト)。
本Waveでは ATR_Ratio の本番 8銘柄 (OP/WIF/INJ/BONK/DOGE/SHIB/ARB/LINK) で 8H 検証、
かつ vol_z フィルター適用版も。

8H aggregation: 4H bars × 2 → 8H
Params (scaled from 4H): atr_short=4 (was 7), atr_long=28 (was 56), ema_fast=10 (was 20), ema_slow=40 (was 80)

If 8H is genuinely better, this becomes a new candidate to combine with FOPD.
"""
import asyncio
import json
import sys
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime, timezone, timedelta

sys.path.insert(0, "/Users/nekonaomichi/crypto-lab")
from engine.data import fetch_klines
from engine.backtest import run_backtest
from engine.cost_config import get_cost_params

SYMBOLS = ["OPUSDT", "WIFUSDT", "INJUSDT", "BONKUSDT",
           "DOGEUSDT", "SHIBUSDT", "ARBUSDT", "LINKUSDT"]
# 4H params (production)
PARAMS_4H = {"atr_short": 7, "atr_long": 56, "threshold": 0.6, "ema_fast": 20, "ema_slow": 80}
# 8H params (scaled 0.5x time = 1x bar count adjustments)
# 4H baseline: 7 bars × 4h = 28h, 56×4=224h. Same TIME on 8H: 28/8=3.5≈4, 224/8=28.
PARAMS_8H = {"atr_short": 4, "atr_long": 28, "threshold": 0.6, "ema_fast": 10, "ema_slow": 40}
EXIT_4H = {"stop_loss_pct": 0.04, "take_profit_pct": 0.08, "max_hold_bars": 24}
EXIT_8H = {"stop_loss_pct": 0.04, "take_profit_pct": 0.08, "max_hold_bars": 12}  # half (8h × 12 = 4h × 24)
DAYS = 730
VOL_Z = 1.5


def aggregate_4h_to_8h(df_4h):
    df = df_4h.copy().sort_values('open_time').reset_index(drop=True)
    df['pair_idx'] = df.index // 2
    agg = df.groupby('pair_idx').agg({
        'open_time': 'first', 'open': 'first',
        'high': 'max', 'low': 'min', 'close': 'last',
        'volume': 'sum'
    }).reset_index(drop=True)
    return agg


def atr_ratio_signal(df, **k):
    atr_s = (df['high'] - df['low']).rolling(k['atr_short']).mean()
    atr_l = (df['high'] - df['low']).rolling(k['atr_long']).mean()
    comp = atr_s < atr_l * k['threshold']
    ef = df['close'].ewm(span=k['ema_fast']).mean()
    es = df['close'].ewm(span=k['ema_slow']).mean()
    sig = pd.Series(0, index=df.index)
    sig[comp & (ef > es)] = 1
    sig[comp & (ef < es)] = -1
    return sig


def run_bt(df, sig, sym, interval, exit_kw):
    cost = get_cost_params(sym, interval)
    bars_per_year = 2190 if interval == "4h" else 1095
    return run_backtest(df, sig, strategy_name="atr",
                        bars_per_year=bars_per_year, leverage=1.0,
                        **exit_kw, **cost)


def eq_to_daily(eq, bars_per_day):
    eq = np.asarray(eq, dtype=float)
    d = eq[bars_per_day-1::bars_per_day]
    if len(d) < 2: d = eq[::bars_per_day]
    return np.diff(d) / np.where(d[:-1] != 0, d[:-1], 1.0)


def sharpe(r, ppy=365):
    r = np.asarray(r); r = r[np.isfinite(r)]
    if len(r) < 5 or np.std(r, ddof=1) == 0: return 0.0
    return float(np.mean(r) / np.std(r, ddof=1) * np.sqrt(ppy))


async def main():
    print("=== Wave J26: 8H ATR portfolio deep dive ===\n")

    # Load BTC vol_z
    btc = await fetch_klines("BTCUSDT", "4h", DAYS)
    btc['ret'] = btc['close'].pct_change()
    btc['rv'] = btc['ret'].rolling(60).std() * np.sqrt(2190) * 100
    btc['rvm'] = btc['rv'].rolling(360).mean()
    btc['rvs'] = btc['rv'].rolling(360).std()
    btc['volz'] = (btc['rv'] - btc['rvm']) / (btc['rvs'] + 1e-10)
    btc_idx_4h = btc.set_index('open_time')

    # 8H BTC vol_z (aggregated)
    btc_8h = aggregate_4h_to_8h(btc)
    btc_8h['ret'] = btc_8h['close'].pct_change()
    btc_8h['rv'] = btc_8h['ret'].rolling(30).std() * np.sqrt(1095) * 100
    btc_8h['rvm'] = btc_8h['rv'].rolling(180).mean()
    btc_8h['rvs'] = btc_8h['rv'].rolling(180).std()
    btc_8h['volz'] = (btc_8h['rv'] - btc_8h['rvm']) / (btc_8h['rvs'] + 1e-10)
    btc_idx_8h = btc_8h.set_index('open_time')

    print(f"{'Symbol':<10} {'4H Sh':>10} {'4H+filt':>10} {'8H Sh':>10} {'8H+filt':>10}")
    print("-" * 60)
    daily_4h_unf, daily_8h_unf = {}, {}
    daily_4h_filt, daily_8h_filt = {}, {}
    per_sym_metrics = {}

    for s in SYMBOLS:
        df_4h = await fetch_klines(s, "4h", DAYS)
        df_8h = aggregate_4h_to_8h(df_4h)

        # 4H unfiltered
        sig_4h = atr_ratio_signal(df_4h, **PARAMS_4H)
        r = run_bt(df_4h, sig_4h, s, "4h", EXIT_4H)
        sh4_unf = float(r['metrics']['sharpe_ratio'])
        daily_4h_unf[s] = eq_to_daily(r['equity_curve'], 6)

        # 4H with vol_z filter
        sig_4h_f = sig_4h.copy()
        aligned = btc_idx_4h.reindex(df_4h['open_time'], method='ffill')['volz'].values
        bad = pd.Series(aligned, index=sig_4h.index).fillna(False) >= VOL_Z
        sig_4h_f[bad] = 0
        if (sig_4h_f != 0).sum() >= 5:
            r = run_bt(df_4h, sig_4h_f, s, "4h", EXIT_4H)
            sh4_filt = float(r['metrics']['sharpe_ratio'])
            daily_4h_filt[s] = eq_to_daily(r['equity_curve'], 6)
        else:
            sh4_filt = 0; daily_4h_filt[s] = np.zeros(60)

        # 8H unfiltered
        sig_8h = atr_ratio_signal(df_8h, **PARAMS_8H)
        if (sig_8h != 0).sum() >= 5:
            r = run_bt(df_8h, sig_8h, s, "8h", EXIT_8H)
            sh8_unf = float(r['metrics']['sharpe_ratio'])
            daily_8h_unf[s] = eq_to_daily(r['equity_curve'], 3)
        else:
            sh8_unf = 0; daily_8h_unf[s] = np.zeros(60)

        # 8H with vol_z filter
        sig_8h_f = sig_8h.copy()
        aligned8 = btc_idx_8h.reindex(df_8h['open_time'], method='ffill')['volz'].values
        bad8 = pd.Series(aligned8, index=sig_8h.index).fillna(False) >= VOL_Z
        sig_8h_f[bad8] = 0
        if (sig_8h_f != 0).sum() >= 5:
            r = run_bt(df_8h, sig_8h_f, s, "8h", EXIT_8H)
            sh8_filt = float(r['metrics']['sharpe_ratio'])
            daily_8h_filt[s] = eq_to_daily(r['equity_curve'], 3)
        else:
            sh8_filt = 0; daily_8h_filt[s] = np.zeros(60)

        per_sym_metrics[s] = {"sh_4h_unf": round(sh4_unf, 3), "sh_4h_filt": round(sh4_filt, 3),
                              "sh_8h_unf": round(sh8_unf, 3), "sh_8h_filt": round(sh8_filt, 3)}
        print(f"  {s:<10} {sh4_unf:>+10.2f} {sh4_filt:>+10.2f} {sh8_unf:>+10.2f} {sh8_filt:>+10.2f}")

    # Portfolio aggregation
    def aggregate(daily_dict):
        m = min(len(v) for v in daily_dict.values())
        return pd.DataFrame({k: v[:m] for k, v in daily_dict.items()}).mean(axis=1).values

    port_4h_unf = aggregate(daily_4h_unf)
    port_4h_filt = aggregate(daily_4h_filt)
    port_8h_unf = aggregate(daily_8h_unf)
    port_8h_filt = aggregate(daily_8h_filt)

    print("\n=== Portfolio (equal-weight) ===")
    for name, p in [("4H unfilt", port_4h_unf), ("4H +vol_z", port_4h_filt),
                    ("8H unfilt", port_8h_unf), ("8H +vol_z", port_8h_filt)]:
        if len(p) < 10:
            print(f"  {name:<20} insufficient data"); continue
        sh = sharpe(p)
        eq = np.cumprod(1 + p)
        ret = (eq[-1] - 1) * 100
        dd = (eq / np.maximum.accumulate(eq) - 1).min() * 100
        cal = abs(ret / dd) if dd != 0 else 0
        print(f"  {name:<20} Sh={sh:+.2f}  Return={ret:+.1f}%  DD={dd:+.1f}%  Calmar={cal:.2f}")

    out = {
        "wave": "J26", "name": "8H ATR Portfolio deep dive",
        "generated_at": datetime.now(timezone(timedelta(hours=9))).strftime("%Y-%m-%d %H:%M JST"),
        "per_symbol": per_sym_metrics,
        "portfolios": {
            "4h_unfilt": {"sharpe": round(sharpe(port_4h_unf), 3)},
            "4h_filt": {"sharpe": round(sharpe(port_4h_filt), 3)},
            "8h_unfilt": {"sharpe": round(sharpe(port_8h_unf), 3)},
            "8h_filt": {"sharpe": round(sharpe(port_8h_filt), 3)},
        },
    }
    Path("/Users/nekonaomichi/crypto-lab/wave_j26_8h_atr.json").write_text(json.dumps(out, indent=2, default=str))
    print("\nSaved.")


if __name__ == "__main__":
    asyncio.run(main())
