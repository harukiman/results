"""Wave J24 — BTC.D Inflection (Researcher R7) — macro overlay using CoinGecko.

Hypothesis:
  BTC.D (BTC dominance = BTC market cap / total crypto market cap) が30日ローカルHIGH から
  3%以上下降 (3バー連続) するとき = alt season start。Alt 銘柄の ATR_Ratio が活性化する場面で
  positionサイズを1.5xに拡大する meta-overlay。

Implementation:
  - CoinGecko API (no auth): /global → 現在のBTC.D取得
  - History: CoinGecko /coins/markets historical (有料層) は使えない
  - 代替: BTC market cap / total via CoinGecko /coins/{id}/market_chart で BTC market cap 取得、
          /global/decentralized_finance_defi はdefi_market_cap_to_eth_ratio あり
  - 簡略化: BTC price 720d × constant total_supply ≈ BTC market cap proxy
  - その分母を BTC + ETH + top10 alts の合計 market cap proxy で正規化

Practical alternative: 既存OHLCV ベース proxy:
  - BTC market cap ∝ BTC close price
  - Total market cap ∝ (BTC * w_btc + ETH * w_eth + other alts * w_alts)
  - BTC.D proxy = BTC_close / (sum of BTC/ETH/major alts weighted)

Simpler: BTC return vs alts return ratio として近似:
  - 過去30日で BTC が alts より相対的に上昇 → BTC.D 上昇 (alts 弱)
  - BTC が alts より相対的に下落 → BTC.D 下落 (alts 強 / alt season)

Test: BTC.D proxy = BTC_close / mean(top 8 alts close, normalized)
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

ATR_SYMBOLS = ["OPUSDT", "WIFUSDT", "INJUSDT", "BONKUSDT",
               "DOGEUSDT", "SHIBUSDT", "ARBUSDT", "LINKUSDT"]
# Reference alt basket for BTC.D proxy
ALT_BASKET = ["ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT", "ADAUSDT",
              "DOTUSDT", "LINKUSDT", "AVAXUSDT", "DOGEUSDT", "SUIUSDT"]
ATR_PARAMS = {"atr_short": 7, "atr_long": 56, "threshold": 0.6, "ema_fast": 20, "ema_slow": 80}
ATR_EXIT = {"stop_loss_pct": 0.04, "take_profit_pct": 0.08, "max_hold_bars": 24}
VOL_Z = 1.5
DAYS = 730
BARS_PER_YEAR = 2190


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


async def get_btcd_proxy(start_dt=None):
    """Build a BTC.D proxy from BTC and alt basket prices."""
    btc = await fetch_klines("BTCUSDT", "4h", DAYS)
    btc = btc[['open_time', 'close']].rename(columns={'close': 'btc_close'})
    # Normalize at start
    btc['btc_norm'] = btc['btc_close'] / btc['btc_close'].iloc[0]

    alt_norm_list = []
    for s in ALT_BASKET:
        alt_df = await fetch_klines(s, "4h", DAYS)
        alt_aligned = pd.merge_asof(btc[['open_time']], alt_df[['open_time', 'close']].rename(columns={'close': f'{s}_close'}),
                                     on='open_time', direction='backward')
        norm = alt_aligned[f'{s}_close'] / alt_aligned[f'{s}_close'].iloc[0]
        alt_norm_list.append(norm.values)

    # alt basket = equal-weight average normalized
    alt_basket_norm = np.nanmean(alt_norm_list, axis=0)
    # BTC.D proxy = BTC_norm / (BTC_norm + alt_basket_norm)
    btc['btcd_proxy'] = btc['btc_norm'] / (btc['btc_norm'] + alt_basket_norm)
    # 30日 (180バー) rolling HH
    btc['btcd_max30'] = btc['btcd_proxy'].rolling(180).max()
    btc['btcd_drop_pct'] = (btc['btcd_proxy'] - btc['btcd_max30']) / btc['btcd_max30']
    # 3 bar consecutive降下
    btc['btcd_3bar_drop'] = btc['btcd_proxy'].diff().rolling(3).apply(lambda x: (x < 0).all() if len(x) >= 3 else False)
    # alt season trigger: drop > 3% AND 3-bar decline
    btc['alt_season'] = (btc['btcd_drop_pct'] < -0.03) & (btc['btcd_3bar_drop'].astype(bool))
    return btc[['open_time', 'btcd_proxy', 'btcd_drop_pct', 'alt_season']]


def run_bt(df, sig, sym):
    cost = get_cost_params(sym, "4h")
    return run_backtest(df, sig, strategy_name="btcd",
                        bars_per_year=BARS_PER_YEAR, leverage=1.0,
                        **ATR_EXIT, **cost)


def eq_to_daily(eq):
    eq = np.asarray(eq, dtype=float)
    d = eq[5::6]
    if len(d) < 2: d = eq[::6]
    return np.diff(d) / np.where(d[:-1] != 0, d[:-1], 1.0)


def sharpe(r, ppy=365):
    r = np.asarray(r); r = r[np.isfinite(r)]
    if len(r) < 5 or np.std(r, ddof=1) == 0: return 0.0
    return float(np.mean(r) / np.std(r, ddof=1) * np.sqrt(ppy))


async def main():
    print("=== Wave J24: BTC.D Inflection — macro overlay for ATR ===\n")

    # Build BTC.D proxy
    print("Building BTC.D proxy ...")
    btcd = await get_btcd_proxy()
    print(f"  Proxy range: {btcd['btcd_proxy'].min():.3f} - {btcd['btcd_proxy'].max():.3f}")
    n_alt_season_bars = btcd['alt_season'].sum()
    pct_alt_season = n_alt_season_bars / len(btcd) * 100
    print(f"  Alt season bars: {n_alt_season_bars}/{len(btcd)} ({pct_alt_season:.1f}%)")
    btcd_idx = btcd.set_index('open_time')

    # Load BTC vol_z for baseline filter
    btc_vz_raw = await fetch_klines("BTCUSDT", "4h", DAYS)
    btc_vz_raw['ret'] = btc_vz_raw['close'].pct_change()
    btc_vz_raw['rv'] = btc_vz_raw['ret'].rolling(60).std() * np.sqrt(BARS_PER_YEAR) * 100
    btc_vz_raw['rvm'] = btc_vz_raw['rv'].rolling(360).mean()
    btc_vz_raw['rvs'] = btc_vz_raw['rv'].rolling(360).std()
    btc_vz_raw['volz'] = (btc_vz_raw['rv'] - btc_vz_raw['rvm']) / (btc_vz_raw['rvs'] + 1e-10)
    btc_vz_idx = btc_vz_raw.set_index('open_time')

    # ── Test 3 variants ──
    # (A) Baseline: ATR + vol_z (existing best)
    # (B) Alt-season only: only trade when alt_season == True
    # (C) Alt-season size-up: 1.5x position size during alt_season (approximated by signal magnitude)
    daily_A, daily_B, daily_C = {}, {}, {}
    for s in ATR_SYMBOLS:
        df = await fetch_klines(s, "4h", DAYS)
        sig = atr_ratio_signal(df, **ATR_PARAMS)
        # vol_z filter
        aligned_vz = btc_vz_idx.reindex(df['open_time'], method='ffill')['volz'].values
        bad_vz = pd.Series(aligned_vz, index=sig.index).fillna(False) >= VOL_Z
        # alt_season state
        aligned_alt = btcd_idx.reindex(df['open_time'], method='ffill')['alt_season'].values
        alt_state = pd.Series(aligned_alt, index=sig.index).fillna(False).astype(bool)

        # (A) baseline
        sig_a = sig.copy(); sig_a[bad_vz] = 0
        if (sig_a != 0).sum() >= 5:
            r_a = run_bt(df, sig_a, s)
            daily_A[s] = eq_to_daily(r_a['equity_curve'])

        # (B) alt-season only
        sig_b = sig.copy(); sig_b[bad_vz | (~alt_state)] = 0
        if (sig_b != 0).sum() >= 3:
            r_b = run_bt(df, sig_b, s)
            daily_B[s] = eq_to_daily(r_b['equity_curve'])
        else:
            daily_B[s] = np.zeros(60)  # placeholder

        # (C) Size-up: backtest treats signal magnitude in [-1, +1] range as full position by default.
        # Approximate "1.5x during alt_season" by running normal backtest then multiplying daily ret by 1.5 when alt-season was active that day
        # This is a simplification but gives directional answer
        if (sig_a != 0).sum() >= 5:
            r_c = run_bt(df, sig_a, s)
            base_daily = eq_to_daily(r_c['equity_curve'])
            # Approximate which days were alt-season:
            # Bar idx → day idx
            n_bars = len(df)
            bars_per_day = 6
            alt_state_daily = alt_state.values[::bars_per_day][:len(base_daily)]
            if len(alt_state_daily) < len(base_daily):
                alt_state_daily = np.concatenate([alt_state_daily, [False] * (len(base_daily) - len(alt_state_daily))])
            scale = np.where(alt_state_daily, 1.5, 1.0)
            daily_C[s] = base_daily * scale

    # Aggregate portfolios
    def aggregate(daily_dict):
        if not daily_dict:
            return None
        m = min(len(v) for v in daily_dict.values())
        agg = pd.DataFrame({k: v[:m] for k, v in daily_dict.items()}).mean(axis=1).values
        return agg

    port_A = aggregate(daily_A)
    port_B = aggregate(daily_B)
    port_C = aggregate(daily_C)

    print("\n=== Portfolio comparisons ===")
    for name, p in [("(A) ATR + vol_z (baseline)", port_A),
                    ("(B) Alt-season ONLY", port_B),
                    ("(C) ATR + vol_z + 1.5x in alt-season", port_C)]:
        if p is None or len(p) < 30:
            print(f"  {name:<40} insufficient data")
            continue
        sh = sharpe(p)
        eq = np.cumprod(1 + p)
        ret = (eq[-1] - 1) * 100
        dd = (eq / np.maximum.accumulate(eq) - 1).min() * 100
        cal = abs(ret / dd) if dd != 0 else 0
        print(f"  {name:<40} Sh={sh:+.2f}  ret={ret:+.1f}%  dd={dd:+.1f}%  Calmar={cal:.2f}")

    out = {
        "wave": "J24", "name": "BTC.D Inflection macro overlay",
        "generated_at": datetime.now(timezone(timedelta(hours=9))).strftime("%Y-%m-%d %H:%M JST"),
        "alt_season_pct_bars": round(pct_alt_season, 2),
        "variants": {
            "A_baseline": {"sharpe": round(sharpe(port_A), 3) if port_A is not None else None,
                           "return_pct": round(float((np.cumprod(1 + port_A)[-1] - 1) * 100), 2) if port_A is not None else None},
            "B_alt_only": {"sharpe": round(sharpe(port_B), 3) if port_B is not None else None,
                           "return_pct": round(float((np.cumprod(1 + port_B)[-1] - 1) * 100), 2) if port_B is not None else None},
            "C_size_up": {"sharpe": round(sharpe(port_C), 3) if port_C is not None else None,
                          "return_pct": round(float((np.cumprod(1 + port_C)[-1] - 1) * 100), 2) if port_C is not None else None},
        },
    }
    Path("/Users/nekonaomichi/crypto-lab/wave_j24_btcd.json").write_text(json.dumps(out, indent=2, default=str))
    print("\nSaved.")


if __name__ == "__main__":
    asyncio.run(main())
