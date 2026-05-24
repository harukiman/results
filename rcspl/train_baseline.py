"""RCSPL Week-1 baseline: LightGBM on hand-crafted features.

Validation:
- Time-based split (60% train / 10% gap / 30% test)
- OOS AUC, accuracy, per-symbol breakdown
- Translates probability → signal → run_backtest comparison
"""
import asyncio
import sys
import json
import numpy as np
import pandas as pd
from pathlib import Path

sys.path.insert(0, '/Users/nekonaomichi/crypto-lab')

from rcspl.snippets import build_dataset


async def main():
    print('=== RCSPL Week-1 Baseline (Wave K108) ===\n')
    M, N = 64, 12
    X, y_bin, y_ret, meta = await build_dataset(M=M, N=N, stride=4)  # stride=4 → ~25% of bars
    print(f'\n  Dataset summary:')
    print(f'    X shape: {X.shape}')
    print(f'    y_bin balance: {y_bin.mean()*100:.1f}% positive (long-favorable)')
    print(f'    y_ret mean/std: {y_ret.mean()*100:+.3f}% / {y_ret.std()*100:.3f}%')
    print(f'    Symbols: {meta["symbol"].nunique()}')

    # Time-based split: sort by t
    meta = meta.reset_index(drop=True)
    meta['global_idx'] = np.arange(len(meta))
    # Sort by date for time-based split
    meta_sorted = meta.sort_values(['symbol', 't']).reset_index(drop=True)
    sort_order = meta_sorted['global_idx'].values
    X_s = X[sort_order]
    y_bin_s = y_bin[sort_order]
    y_ret_s = y_ret[sort_order]
    meta_s = meta_sorted.reset_index(drop=True)

    n = len(X_s)
    train_end = int(n * 0.60)
    gap_end = int(n * 0.70)  # 10% gap for embargo
    X_tr, y_tr = X_s[:train_end], y_bin_s[:train_end]
    X_te, y_te = X_s[gap_end:], y_bin_s[gap_end:]
    y_ret_te = y_ret_s[gap_end:]
    meta_te = meta_s.iloc[gap_end:].reset_index(drop=True)
    print(f'\n  Split: train {len(X_tr)} | gap {gap_end - train_end} | test {len(X_te)}')

    # Train LightGBM
    try:
        import lightgbm as lgb
    except ImportError:
        print('  lightgbm not installed; falling back to sklearn'); return
    print('\n  Training LightGBM...')
    train_data = lgb.Dataset(X_tr, label=y_tr)
    params = {
        'objective': 'binary',
        'metric': 'auc',
        'learning_rate': 0.05,
        'num_leaves': 31,
        'min_data_in_leaf': 50,
        'feature_fraction': 0.8,
        'bagging_fraction': 0.8,
        'bagging_freq': 5,
        'verbose': -1,
        'random_state': 42,
    }
    model = lgb.train(params, train_data, num_boost_round=200,
                       valid_sets=[lgb.Dataset(X_te, label=y_te)],
                       callbacks=[lgb.early_stopping(20), lgb.log_evaluation(0)])

    # Predict
    p_te = model.predict(X_te)
    auc = float(np.mean((p_te > 0.5) == y_te))  # simple accuracy
    from sklearn.metrics import roc_auc_score, log_loss
    auc_real = roc_auc_score(y_te, p_te)
    ll = log_loss(y_te, np.clip(p_te, 1e-6, 1-1e-6))
    print(f'\n  OOS Metrics:')
    print(f'    AUC: {auc_real:.4f}')
    print(f'    Accuracy: {((p_te > 0.5) == y_te).mean():.4f}')
    print(f'    Log loss: {ll:.4f}')
    print(f'    Baseline (y_te.mean()): {y_te.mean():.4f}')

    # Per-symbol breakdown
    print(f'\n  Per-symbol OOS AUC:')
    for sym in sorted(meta_te['symbol'].unique()):
        mask = (meta_te['symbol'] == sym).values
        if mask.sum() < 20: continue
        try:
            sym_auc = roc_auc_score(y_te[mask], p_te[mask])
            print(f'    {sym:<10}  n={mask.sum():>4}  AUC={sym_auc:.3f}  mean_p={p_te[mask].mean():.3f}')
        except Exception:
            pass

    # Translate prob → signal → Sharpe
    print(f'\n  Signal-based Sharpe (long if p>0.55, short if p<0.45):')
    sig = np.zeros(len(p_te), dtype=int)
    sig[p_te > 0.55] = 1
    sig[p_te < 0.45] = -1
    cost = 0.0014
    pnl = sig * y_ret_te - np.abs(sig) * cost
    pnl_active = pnl[sig != 0]
    if len(pnl_active) >= 30:
        sh = float(np.mean(pnl_active) / (np.std(pnl_active) + 1e-10) * np.sqrt(365 / (N * 4 / 24)))
        tot = float(np.sum(pnl_active) * 100)
        wr = float((pnl_active > 0).mean())
        print(f'    Pseudo-Sharpe: {sh:+.2f}')
        print(f'    Total return: {tot:+.1f}%')
        print(f'    Active trades: {len(pnl_active)} ({(sig!=0).mean()*100:.1f}% of bars)')
        print(f'    Win rate: {wr:.2%}')

    # Feature importance
    print(f'\n  Top 10 feature importance:')
    importance = model.feature_importance(importance_type='gain')
    from rcspl.features import get_feature_names
    names = get_feature_names()
    if len(names) == len(importance):
        sorted_idx = np.argsort(importance)[::-1][:10]
        for i in sorted_idx:
            print(f'    {names[i]:<22}  {importance[i]:.1f}')

    # Save
    out = {
        'wave': 'K108',
        'M': M, 'N': N,
        'n_samples': int(n),
        'n_features': X.shape[1],
        'oos_auc': float(auc_real),
        'oos_accuracy': float(((p_te > 0.5) == y_te).mean()),
        'oos_log_loss': float(ll),
        'pseudo_sharpe': float(sh) if len(pnl_active) >= 30 else None,
    }
    json.dump(out, open('/Users/nekonaomichi/crypto-lab/rcspl_baseline.json', 'w'), default=str, indent=2)
    print(f'\n  Saved rcspl_baseline.json')


if __name__ == '__main__':
    asyncio.run(main())
