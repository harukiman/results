"""Wave K16 — BTC/ETH ratio spread mean-reversion.

仮説:
  log(BTC/ETH) のローリング z-score が極端値の時、spread mean revert を期待。
  - z > +threshold: BTC が ETH に対し overpriced → short BTC + long ETH (z 戻り)
  - z < -threshold: BTC underpriced → long BTC + short ETH

実装はsingle-sided として:
  - 個別銘柄で signal を生成 (BTC long/short based on ratio z)
  - ETH も同様に逆方向
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

DAYS = 730
BARS_PER_YEAR = 2190


def btc_eth_ratio_signal_btc(btc_df, eth_df, zscore_window=180, z_threshold=2.0):
    """Signal for BTC side of BTC/ETH spread."""
    # Align on common time
    df = btc_df[['open_time', 'close']].rename(columns={'close': 'btc'})
    eth = eth_df[['open_time', 'close']].rename(columns={'close': 'eth'})
    df = pd.merge_asof(df.sort_values('open_time'), eth.sort_values('open_time'), on='open_time', direction='backward')
    df['ratio'] = np.log(df['btc'] / df['eth'])
    df['ratio_mean'] = df['ratio'].rolling(zscore_window).mean()
    df['ratio_std'] = df['ratio'].rolling(zscore_window).std()
    df['ratio_z'] = (df['ratio'] - df['ratio_mean']) / (df['ratio_std'] + 1e-10)

    sig = np.zeros(len(df), dtype=int)
    # z > threshold: BTC overpriced relative to ETH → short BTC
    sig[df['ratio_z'].values > z_threshold] = -1
    # z < -threshold: BTC underpriced → long BTC
    sig[df['ratio_z'].values < -z_threshold] = +1
    sig[:zscore_window + 5] = 0
    # Return as series aligned to btc_df index
    return pd.Series(sig, index=btc_df.index[:len(sig)])


def btc_eth_ratio_signal_eth(btc_df, eth_df, zscore_window=180, z_threshold=2.0):
    """Opposite signal for ETH side."""
    sig = btc_eth_ratio_signal_btc(btc_df, eth_df, zscore_window, z_threshold)
    return -sig  # flip for ETH


def run_bt(df, sig, sym, sl=0.03, tp=0.05, mhb=18):
    cost = get_cost_params(sym, "4h")
    return run_backtest(df, sig, strategy_name="K16", bars_per_year=BARS_PER_YEAR,
                        leverage=1.0, stop_loss_pct=sl, take_profit_pct=tp,
                        max_hold_bars=mhb, **cost)


def sharpe(r, ppy=365):
    r = np.asarray(r); r = r[np.isfinite(r)]
    if len(r) < 5 or np.std(r, ddof=1) == 0: return 0.0
    return float(np.mean(r) / np.std(r, ddof=1) * np.sqrt(ppy))


async def main():
    print("=== Wave K16: BTC/ETH ratio spread MR ===\n")

    btc = await fetch_klines("BTCUSDT", "4h", DAYS)
    eth = await fetch_klines("ETHUSDT", "4h", DAYS)
    print(f"BTC: {len(btc)} bars, ETH: {len(eth)} bars")

    # Parameter grid
    zscore_windows = [60, 90, 180, 360]
    z_thresholds = [1.0, 1.5, 2.0, 2.5, 3.0]
    sls = [0.02, 0.03, 0.05]
    tps = [0.03, 0.05, 0.08]
    mhbs = [6, 12, 24]

    n_grid = len(zscore_windows) * len(z_thresholds) * len(sls) * len(tps) * len(mhbs)
    print(f"Grid: {n_grid} configs × 2 sides (BTC/ETH) = {n_grid * 2} backtests\n")

    results_btc = []
    results_eth = []
    for zw in zscore_windows:
        for zt in z_thresholds:
            sig_btc = btc_eth_ratio_signal_btc(btc, eth, zscore_window=zw, z_threshold=zt)
            sig_eth = -sig_btc  # ETH side is opposite
            for sl in sls:
                for tp in tps:
                    for mhb in mhbs:
                        for label, sig, sym, results in [
                            ("BTC", sig_btc, "BTCUSDT", results_btc),
                            ("ETH", sig_eth, "ETHUSDT", results_eth),
                        ]:
                            n_sig = (sig != 0).sum()
                            if n_sig < 15:
                                continue
                            try:
                                df_target = btc if sym == "BTCUSDT" else eth
                                r = run_bt(df_target, sig, sym, sl, tp, mhb)
                                m = r['metrics']
                                sh = float(m.get('sharpe_ratio') or 0)
                                ret = float(m.get('total_return_pct') or 0)
                                dd = float(m.get('max_drawdown_pct') or 0)
                                trades = int(m.get('total_trades') or 0)
                                if trades < 15:
                                    continue
                                results.append({
                                    'side': label, 'zw': zw, 'zt': zt, 'sl': sl, 'tp': tp, 'mhb': mhb,
                                    'sharpe': round(sh, 3), 'return_pct': round(ret, 2),
                                    'dd_pct': round(dd, 2), 'trades': trades,
                                })
                            except Exception:
                                pass

    for label, results in [("BTC", results_btc), ("ETH", results_eth)]:
        results.sort(key=lambda x: x['sharpe'], reverse=True)
        print(f"\n=== Top 10 {label} side ===")
        for r in results[:10]:
            print(f"  Sh={r['sharpe']:+.2f} ret={r['return_pct']:+.1f}% dd={r['dd_pct']:+.1f}% tr={r['trades']} (zw={r['zw']}, zt={r['zt']})")
        sh_pos = sum(1 for r in results if r['sharpe'] > 0)
        sh_ge_1 = sum(1 for r in results if r['sharpe'] >= 1.0)
        sh_ge_1_5 = sum(1 for r in results if r['sharpe'] >= 1.5)
        print(f"  Sh>0: {sh_pos}/{len(results)} ({sh_pos/max(len(results),1)*100:.0f}%), ≥1: {sh_ge_1}, ≥1.5: {sh_ge_1_5}")

    out = {
        "wave": "K16", "name": "BTC/ETH ratio spread mean-reversion",
        "generated_at": datetime.now(timezone(timedelta(hours=9))).strftime("%Y-%m-%d %H:%M JST"),
        "top10_btc": results_btc[:10], "top10_eth": results_eth[:10],
    }
    Path("/Users/nekonaomichi/crypto-lab/wave_k16_btc_eth_ratio.json").write_text(json.dumps(out, indent=2, default=str))
    print("\nSaved.")


if __name__ == "__main__":
    asyncio.run(main())
