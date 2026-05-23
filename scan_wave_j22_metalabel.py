"""Wave J22 — MetaLabel for ATR (Tip-scraper TOP4, López de Prado triple barrier).

ATR_Ratio_Compression を primary signal にして、シグナル発火時の特徴量から
「このシグナルが収益的か」を二項分類で予測。p_profit > threshold のみ約定。

メタラベル特徴量 (signal発火時の状態):
  - vol_z (BTC実現ボラのZ-スコア)
  - atr_short / atr_long ratio
  - ema_fast/ema_slow spread (%)
  - recent_returns 24h
  - rsi(14)
  - candle_body_ratio
  - rolling_vol_60bar
  - symbol_category (one-hot)

ラベル: triple barrier — entry後 [SL=-4%, TP=+8%, MH=24bars] のうちどれが先に当たるか。
  TP first → +1 (profit), SL first → 0 (loss), MH (timeout) → 0 (no clear profit)

Training: 前半365d (=H1)
Test: 後半365d (=H2)

評価:
  ATR (baseline) vs ATR + MetaFilter (p>0.5) を H2 で比較。
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

try:
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.metrics import accuracy_score, precision_score, recall_score, roc_auc_score
    SKLEARN_OK = True
except ImportError:
    SKLEARN_OK = False

ATR_SYMBOLS = ["OPUSDT", "WIFUSDT", "INJUSDT", "BONKUSDT",
               "DOGEUSDT", "SHIBUSDT", "ARBUSDT", "LINKUSDT"]
ATR_PARAMS = {"atr_short": 7, "atr_long": 56, "threshold": 0.6, "ema_fast": 20, "ema_slow": 80}
SL_PCT = 0.04
TP_PCT = 0.08
MH_BARS = 24
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


def build_features(df, vol_z_series):
    """At each bar, compute features."""
    n = len(df)
    o = df['open'].values; h = df['high'].values; l = df['low'].values; c = df['close'].values; v = df['volume'].values

    atr_s = pd.Series(h - l).rolling(ATR_PARAMS['atr_short']).mean().values
    atr_l = pd.Series(h - l).rolling(ATR_PARAMS['atr_long']).mean().values
    ema_f = pd.Series(c).ewm(span=ATR_PARAMS['ema_fast']).mean().values
    ema_s = pd.Series(c).ewm(span=ATR_PARAMS['ema_slow']).mean().values

    feat = pd.DataFrame({
        'atr_ratio': atr_s / (atr_l + 1e-12),
        'ema_spread_pct': (ema_f - ema_s) / (c + 1e-12) * 100,
        'ret_24h': pd.Series(c).pct_change(6).values,
        'ret_72h': pd.Series(c).pct_change(18).values,
        'body_ratio': (c - o) / (h - l + 1e-12),
        'wick_asym': ((h - np.maximum(o, c)) - (np.minimum(o, c) - l)) / (h - l + 1e-12),
        'rolling_vol_60': pd.Series(c).pct_change().rolling(60).std().values,
        'vol_z': vol_z_series.values,
        'volume_ratio': v / (pd.Series(v).rolling(20).mean().values + 1e-12),
    })
    return feat


def compute_triple_barrier_labels(df, sig, sl_pct, tp_pct, mh_bars):
    """For each non-zero signal bar, label as 1 if TP hits first, 0 otherwise."""
    n = len(df)
    h = df['high'].values; l = df['low'].values; c = df['close'].values
    sig_arr = sig.values
    labels = np.full(n, np.nan)

    for i in range(n - 1):
        s = sig_arr[i]
        if s == 0:
            continue
        entry_close = c[i]
        if s > 0:  # long
            tp = entry_close * (1 + tp_pct)
            sl = entry_close * (1 - sl_pct)
        else:  # short
            tp = entry_close * (1 - tp_pct)
            sl = entry_close * (1 + sl_pct)

        end_bar = min(i + 1 + mh_bars, n)
        label = 0  # default = MH timeout or SL hit
        for j in range(i + 1, end_bar):
            if s > 0:
                if l[j] <= sl:
                    label = 0  # SL hit
                    break
                if h[j] >= tp:
                    label = 1  # TP hit
                    break
            else:
                if h[j] >= sl:
                    label = 0
                    break
                if l[j] <= tp:
                    label = 1
                    break
        labels[i] = label
    return pd.Series(labels, index=df.index)


def run_bt(df, sig, sym):
    cost = get_cost_params(sym, "4h")
    return run_backtest(df, sig, strategy_name="meta", bars_per_year=BARS_PER_YEAR,
                        leverage=1.0, stop_loss_pct=SL_PCT, take_profit_pct=TP_PCT,
                        max_hold_bars=MH_BARS, **cost)


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
    if not SKLEARN_OK:
        print("sklearn not installed"); return
    print("=== Wave J22: MetaLabel for ATR (López de Prado triple barrier) ===\n")

    # Load BTC vol_z first
    btc = await fetch_klines("BTCUSDT", "4h", DAYS)
    btc['ret'] = btc['close'].pct_change()
    btc['rv'] = btc['ret'].rolling(60).std() * np.sqrt(BARS_PER_YEAR) * 100
    btc['rvm'] = btc['rv'].rolling(360).mean()
    btc['rvs'] = btc['rv'].rolling(360).std()
    btc['volz'] = (btc['rv'] - btc['rvm']) / (btc['rvs'] + 1e-10)
    btc_idx = btc.set_index('open_time')

    # Per symbol: build features + labels, split H1/H2, train + eval
    all_results = {}
    for s in ATR_SYMBOLS:
        df = await fetch_klines(s, "4h", DAYS)
        sig = atr_ratio_signal(df, **ATR_PARAMS)
        # apply vol_z >= 1.5 filter (same as production)
        aligned_vz = btc_idx.reindex(df['open_time'], method='ffill')['volz'].values
        bad = pd.Series(aligned_vz, index=sig.index).fillna(False) >= 1.5
        sig_filtered = sig.copy()
        sig_filtered[bad] = 0

        n_sig = (sig_filtered != 0).sum()
        if n_sig < 30:
            print(f"  {s:<10} TOO FEW SIGNALS ({n_sig})")
            continue

        # Features
        vol_z_series = pd.Series(aligned_vz, index=df.index).fillna(0)
        feat = build_features(df, vol_z_series)

        # Labels (only for signal bars)
        labels = compute_triple_barrier_labels(df, sig_filtered, SL_PCT, TP_PCT, MH_BARS)

        # Combine
        full = feat.copy()
        full['signal'] = sig_filtered.values
        full['label'] = labels.values
        full['bar_idx'] = np.arange(len(df))

        # Drop NaN and non-signal rows
        signal_df = full.dropna(subset=['label']).copy()
        signal_df = signal_df[signal_df['signal'] != 0].copy()

        # Split H1 (first half by bar) / H2
        half = len(df) // 2
        h1 = signal_df[signal_df['bar_idx'] < half]
        h2 = signal_df[signal_df['bar_idx'] >= half]

        if len(h1) < 20 or len(h2) < 20:
            print(f"  {s:<10} H1={len(h1)}, H2={len(h2)} — too few for ML")
            continue

        feat_cols = ['atr_ratio', 'ema_spread_pct', 'ret_24h', 'ret_72h',
                     'body_ratio', 'wick_asym', 'rolling_vol_60', 'vol_z', 'volume_ratio']

        X_train = h1[feat_cols].fillna(0).values
        y_train = h1['label'].astype(int).values
        X_test = h2[feat_cols].fillna(0).values
        y_test = h2['label'].astype(int).values

        # Train RandomForest
        clf = RandomForestClassifier(n_estimators=200, max_depth=6, min_samples_leaf=5,
                                      random_state=42, n_jobs=2, class_weight='balanced')
        clf.fit(X_train, y_train)
        y_pred = clf.predict(X_test)
        y_proba = clf.predict_proba(X_test)[:, 1] if clf.classes_[0] == 0 else clf.predict_proba(X_test)[:, 0]

        # Train metrics
        train_acc = accuracy_score(y_train, clf.predict(X_train))
        test_acc = accuracy_score(y_test, y_pred)
        try:
            test_auc = roc_auc_score(y_test, y_proba)
        except Exception:
            test_auc = None

        # H1 baseline label rate (= base TP rate)
        h1_tp_rate = float(h1['label'].mean())
        h2_tp_rate = float(h2['label'].mean())

        # Apply meta filter at multiple thresholds
        threshold_results = {}
        df_h2 = df.iloc[half:].copy().reset_index(drop=True)
        sig_h2 = sig_filtered.iloc[half:].copy().reset_index(drop=True)

        # Run baseline (no meta filter) on H2
        r_baseline = run_bt(df_h2, sig_h2, s)
        sh_baseline = float(r_baseline['metrics']['sharpe_ratio'])
        ret_baseline = float(r_baseline['metrics']['total_return_pct'])
        n_trades_baseline = int(r_baseline['metrics']['total_trades'])

        # For each threshold, filter signals using clf prediction at each signal bar
        # We need to predict proba for ALL signal bars in H2 (not just those with labels)
        # Use the same features for all bars
        feat_h2 = feat.iloc[half:].copy().reset_index(drop=True)
        feat_h2_signal_mask = sig_h2 != 0
        feat_h2_signal_features = feat_h2.loc[feat_h2_signal_mask, feat_cols].fillna(0)
        if len(feat_h2_signal_features) == 0:
            continue
        proba_signal = clf.predict_proba(feat_h2_signal_features.values)
        # Index of "label=1" class
        idx_1 = list(clf.classes_).index(1) if 1 in clf.classes_ else None
        if idx_1 is None:
            continue
        proba_1 = proba_signal[:, idx_1]

        # Build sig_meta filtered by threshold
        for thr in [0.4, 0.5, 0.55, 0.6, 0.65]:
            keep = proba_1 >= thr
            sig_meta = sig_h2.copy()
            mask_positions = feat_h2_signal_features.index
            for idx, kept in zip(mask_positions, keep):
                if not kept:
                    sig_meta.iloc[idx] = 0
            n_meta = (sig_meta != 0).sum()
            if n_meta < 3:
                threshold_results[thr] = {"sharpe": None, "n_trades": 0, "note": "too few after filter"}
                continue
            r_meta = run_bt(df_h2, sig_meta, s)
            sh_meta = float(r_meta['metrics']['sharpe_ratio'])
            ret_meta = float(r_meta['metrics']['total_return_pct'])
            n_meta_trades = int(r_meta['metrics']['total_trades'])
            threshold_results[thr] = {
                "sharpe": round(sh_meta, 3),
                "return_pct": round(ret_meta, 2),
                "n_trades": n_meta_trades,
                "delta_sharpe": round(sh_meta - sh_baseline, 3),
            }

        all_results[s] = {
            "n_signals_total": int((sig_filtered != 0).sum()),
            "h1_size": len(h1), "h2_size": len(h2),
            "h1_tp_rate": round(h1_tp_rate, 3), "h2_tp_rate": round(h2_tp_rate, 3),
            "train_accuracy": round(train_acc, 3), "test_accuracy": round(test_acc, 3),
            "test_auc": round(test_auc, 3) if test_auc is not None else None,
            "H2_baseline": {"sharpe": round(sh_baseline, 3), "return_pct": round(ret_baseline, 2),
                            "n_trades": n_trades_baseline},
            "H2_with_meta": threshold_results,
        }

        auc_str = f"{test_auc:.2f}" if test_auc is not None else "n/a"
        print(f"  {s:<10} H1={len(h1)} H2={len(h2)} | "
              f"TP rate H1={h1_tp_rate:.2f}, H2={h2_tp_rate:.2f} | "
              f"AUC={auc_str}")
        for thr, r in threshold_results.items():
            if r.get('sharpe') is None: continue
            print(f"    thr={thr}: Sh={r['sharpe']:+.2f} (Δ={r['delta_sharpe']:+.2f}) tr={r['n_trades']} vs baseline Sh={sh_baseline:+.2f}")

    # Aggregate: best threshold per symbol
    print(f"\n=== Aggregate ===")
    best_thresh_count = {0.4: 0, 0.5: 0, 0.55: 0, 0.6: 0, 0.65: 0}
    improvement_count = 0
    total_count = 0
    for s, r in all_results.items():
        bl_sh = r["H2_baseline"]["sharpe"]
        meta = r["H2_with_meta"]
        valid_thrs = [t for t, v in meta.items() if v.get("sharpe") is not None]
        if not valid_thrs:
            continue
        best_thr = max(valid_thrs, key=lambda t: meta[t]["sharpe"])
        best_sh = meta[best_thr]["sharpe"]
        best_thresh_count[best_thr] += 1
        if best_sh > bl_sh:
            improvement_count += 1
        total_count += 1
        print(f"  {s:<10} baseline Sh={bl_sh:+.2f}, best meta thr={best_thr} → Sh={best_sh:+.2f} (Δ={best_sh-bl_sh:+.2f})")

    print(f"\nMeta-filter improvement: {improvement_count}/{total_count} symbols")
    print(f"Best threshold counts: {best_thresh_count}")

    out = {
        "wave": "J22", "name": "MetaLabel for ATR (triple barrier RF classifier)",
        "generated_at": datetime.now(timezone(timedelta(hours=9))).strftime("%Y-%m-%d %H:%M JST"),
        "improvement_count": improvement_count, "total_count": total_count,
        "best_threshold_dist": best_thresh_count,
        "per_symbol": all_results,
    }
    Path("/Users/nekonaomichi/crypto-lab/wave_j22_metalabel.json").write_text(json.dumps(out, indent=2, default=str))
    print("\nSaved.")


if __name__ == "__main__":
    asyncio.run(main())
