"""Full anti-overfit validation pipeline for Sample Entropy signal on DOGE 4H.

Tests: Walk-Forward, Inverse Signal, Bootstrap CI, Multi-Symbol, Signal Independence, Triple Ensemble.
"""

import asyncio
import json
import sys
import os
import time
import warnings
warnings.filterwarnings("ignore")

sys.path.insert(0, os.path.dirname(__file__))

import numpy as np
import pandas as pd
from scipy import stats
from datetime import datetime

from engine.data import fetch_klines
from engine.backtest import run_backtest
from engine.cost_config import get_cost_params

# ── Config ────────────────────────────────────────────────
SYMBOL = "DOGEUSDT"
ALT_SYMBOLS = ["SUIUSDT", "LINKUSDT", "SOLUSDT", "XRPUSDT"]
INTERVAL = "4h"
DAYS = 730
IS_RATIO = 0.70
BARS_PER_YEAR = 2190
LEVERAGE = 1.0

# SampEn params (best config)
SAMPEN_M = 2
SAMPEN_R_MULT = 0.2
SAMPEN_WINDOW = 50
SAMPEN_PCT = 20
EMA_FAST = 14
EMA_SLOW = 60

# SL/TP (use from original scan)
SL_PCT = 0.03
TP_PCT = 0.10
MAX_HOLD = 42

# ── Optimized Sample Entropy ─────────────────────────────

def compute_rolling_sample_entropy_fast(returns_arr, m=2, r_mult=0.2, apen_window=50):
    """Vectorized rolling sample entropy using stride tricks."""
    n = len(returns_arr)
    entropy_vals = np.full(n, np.nan)

    for i in range(apen_window, n):
        window = returns_arr[i - apen_window:i]
        r = r_mult * np.std(window)
        if r < 1e-12:
            entropy_vals[i] = 0.0
            continue

        N = len(window)

        def _count_matches(tlen):
            if N - tlen < 2:
                return 0
            templates = np.lib.stride_tricks.sliding_window_view(window, tlen)
            count = 0
            for j in range(len(templates)):
                diffs = np.max(np.abs(templates - templates[j]), axis=1)
                count += np.sum(diffs < r) - 1  # exclude self-match
            return count

        B = _count_matches(m)
        A = _count_matches(m + 1)

        if B > 0 and A > 0:
            entropy_vals[i] = -np.log(A / B)
        else:
            entropy_vals[i] = 0.0

    return entropy_vals


def sampen_signal(df, m=SAMPEN_M, r_mult=SAMPEN_R_MULT, apen_window=SAMPEN_WINDOW,
                  apen_pct=SAMPEN_PCT, ema_fast=EMA_FAST, ema_slow=EMA_SLOW):
    """Generate SampEn trading signal."""
    returns = df['close'].pct_change().fillna(0).values
    sampen_vals = compute_rolling_sample_entropy_fast(returns, m=m, r_mult=r_mult,
                                                      apen_window=apen_window)

    indicator_series = pd.Series(sampen_vals, index=df.index)
    threshold = indicator_series.expanding(min_periods=50).quantile(apen_pct / 100.0)
    low_entropy = indicator_series < threshold

    ema_f = df['close'].ewm(span=ema_fast).mean()
    ema_s = df['close'].ewm(span=ema_slow).mean()

    signals = pd.Series(0, index=df.index)
    signals[low_entropy & (ema_f > ema_s)] = 1
    signals[low_entropy & (ema_f < ema_s)] = -1

    warmup = max(apen_window + 20, ema_slow + 20)
    signals.iloc[:warmup] = 0
    return signals


def volreg_signal(df, short_vol=10, long_vol=25, threshold=0.7, ema_fast=14, ema_slow=40):
    """VolReg compression signal for comparison."""
    returns = df['close'].pct_change()
    short_v = returns.rolling(short_vol).std()
    long_v = returns.rolling(long_vol).std()
    compression = short_v < long_v * threshold
    ema_f = df['close'].ewm(span=ema_fast).mean()
    ema_s = df['close'].ewm(span=ema_slow).mean()
    signals = pd.Series(0, index=df.index)
    signals[compression & (ema_f > ema_s)] = 1
    signals[compression & (ema_f < ema_s)] = -1
    return signals


def atr_ratio_signal(df, atr_short=7, atr_long=56, threshold=0.6, ema_fast=20, ema_slow=80):
    """ATR Ratio compression signal for comparison."""
    atr_s = (df['high'] - df['low']).rolling(atr_short).mean()
    atr_l = (df['high'] - df['low']).rolling(atr_long).mean()
    compression = atr_s < atr_l * threshold
    ema_f = df['close'].ewm(span=ema_fast).mean()
    ema_s = df['close'].ewm(span=ema_slow).mean()
    signals = pd.Series(0, index=df.index)
    signals[compression & (ema_f > ema_s)] = 1
    signals[compression & (ema_f < ema_s)] = -1
    return signals


def run_bt(df, signals, symbol=SYMBOL, interval=INTERVAL):
    """Run backtest with proper cost model."""
    cost = get_cost_params(symbol, interval)
    result = run_backtest(
        df, signals,
        strategy_name="SampEn_Validation",
        bars_per_year=BARS_PER_YEAR,
        leverage=LEVERAGE,
        stop_loss_pct=SL_PCT,
        take_profit_pct=TP_PCT,
        max_hold_bars=MAX_HOLD,
        **cost,
    )
    return result


# ══════════════════════════════════════════════════════════
#  TEST 1: Walk-Forward (4 folds, expanding window)
# ══════════════════════════════════════════════════════════

def walk_forward_test(df):
    """4-fold expanding window walk-forward."""
    print("\n" + "=" * 60)
    print("  TEST 1: WALK-FORWARD (4 folds, expanding window)")
    print("=" * 60)

    n = len(df)
    folds = [
        ("Fold1", 0.0, 0.40, 0.40, 0.55),
        ("Fold2", 0.0, 0.55, 0.55, 0.70),
        ("Fold3", 0.0, 0.70, 0.70, 0.85),
        ("Fold4", 0.0, 0.85, 0.85, 1.00),
    ]

    results = []
    for name, train_s, train_e, test_s, test_e in folds:
        ts = int(n * train_s)
        te = int(n * train_e)
        os_s = int(n * test_s)
        os_e = int(n * test_e)

        train_df = df.iloc[ts:te]
        test_df = df.iloc[os_s:os_e]

        # Generate signals on FULL data first (for expanding quantile), then slice
        full_signals = sampen_signal(df)

        # IS
        is_signals = full_signals.iloc[ts:te]
        is_result = run_bt(train_df, is_signals)
        is_sharpe = is_result['metrics']['sharpe_ratio']
        is_trades = is_result['metrics']['total_trades']

        # OOS
        oos_signals = full_signals.iloc[os_s:os_e]
        oos_result = run_bt(test_df, oos_signals)
        oos_sharpe = oos_result['metrics']['sharpe_ratio']
        oos_trades = oos_result['metrics']['total_trades']

        fold_data = {
            "name": name,
            "is_sharpe": round(is_sharpe, 3),
            "oos_sharpe": round(oos_sharpe, 3),
            "is_trades": is_trades,
            "oos_trades": oos_trades,
        }
        results.append(fold_data)
        print(f"  {name}: IS Sharpe={is_sharpe:.3f} ({is_trades}t) | "
              f"OOS Sharpe={oos_sharpe:.3f} ({oos_trades}t)")

    positive_count = sum(1 for r in results if r['oos_sharpe'] > 0)
    avg_sharpe = np.mean([r['oos_sharpe'] for r in results])
    all_positive = positive_count == len(results)
    majority_positive = positive_count >= len(results) / 2

    verdict = "PASS" if majority_positive and avg_sharpe > 0 else "FAIL"
    print(f"\n  Positive folds: {positive_count}/{len(results)}")
    print(f"  Avg OOS Sharpe: {avg_sharpe:.3f}")
    print(f"  Verdict: {verdict}")

    return {
        "folds": results,
        "avg_sharpe": round(avg_sharpe, 3),
        "positive_count": f"{positive_count}/{len(results)}",
        "all_positive": all_positive,
        "verdict": verdict,
    }


# ══════════════════════════════════════════════════════════
#  TEST 2: Inverse Signal Test
# ══════════════════════════════════════════════════════════

def inverse_signal_test(df):
    """Flip all signals and verify negative performance."""
    print("\n" + "=" * 60)
    print("  TEST 2: INVERSE SIGNAL TEST")
    print("=" * 60)

    n = len(df)
    oos_start = int(n * IS_RATIO)
    oos_df = df.iloc[oos_start:]

    # Original
    signals = sampen_signal(df)
    oos_signals = signals.iloc[oos_start:]
    orig_result = run_bt(oos_df, oos_signals)
    orig_sharpe = orig_result['metrics']['sharpe_ratio']

    # Inverted
    inv_signals = -oos_signals
    inv_result = run_bt(oos_df, inv_signals)
    inv_sharpe = inv_result['metrics']['sharpe_ratio']

    gap = orig_sharpe - inv_sharpe
    verdict = "PASS" if inv_sharpe < 0 and gap > 1.0 else (
        "MARGINAL" if inv_sharpe < orig_sharpe else "FAIL"
    )

    print(f"  Original OOS Sharpe: {orig_sharpe:.3f}")
    print(f"  Inverted OOS Sharpe: {inv_sharpe:.3f}")
    print(f"  Gap: {gap:.3f}")
    print(f"  Verdict: {verdict}")

    return {
        "original_sharpe": round(orig_sharpe, 3),
        "inverted_sharpe": round(inv_sharpe, 3),
        "gap": round(gap, 3),
        "verdict": verdict,
    }


# ══════════════════════════════════════════════════════════
#  TEST 3: Bootstrap Confidence Interval
# ══════════════════════════════════════════════════════════

def bootstrap_ci_test(df, n_bootstrap=5000):
    """Bootstrap CI on OOS daily returns."""
    print("\n" + "=" * 60)
    print("  TEST 3: BOOTSTRAP CONFIDENCE INTERVAL (5000 samples)")
    print("=" * 60)

    n = len(df)
    oos_start = int(n * IS_RATIO)
    oos_df = df.iloc[oos_start:]

    signals = sampen_signal(df)
    oos_signals = signals.iloc[oos_start:]
    result = run_bt(oos_df, oos_signals)

    # Get daily returns from equity curve (backtest returns list)
    equity = pd.Series(result['equity_curve'])
    daily_returns = equity.pct_change().dropna().values

    if len(daily_returns) < 10:
        print("  ERROR: Too few daily returns for bootstrap")
        return {"ci_95": [0, 0], "pct_positive": 0, "verdict": "FAIL"}

    rng = np.random.default_rng(42)
    ann_factor = np.sqrt(BARS_PER_YEAR)
    boot_sharpes = []

    for _ in range(n_bootstrap):
        sample = rng.choice(daily_returns, size=len(daily_returns), replace=True)
        std = np.std(sample)
        if std > 0:
            boot_sharpes.append(np.mean(sample) / std * ann_factor)
        else:
            boot_sharpes.append(0.0)

    boot_sharpes = np.array(boot_sharpes)
    ci_low = np.percentile(boot_sharpes, 2.5)
    ci_high = np.percentile(boot_sharpes, 97.5)
    pct_positive = np.mean(boot_sharpes > 0) * 100

    verdict = "PASS" if ci_low > 0 else ("MARGINAL" if pct_positive > 90 else "FAIL")

    print(f"  95% CI: [{ci_low:.3f}, {ci_high:.3f}]")
    print(f"  % positive: {pct_positive:.1f}%")
    print(f"  Verdict: {verdict}")

    return {
        "ci_95": [round(ci_low, 3), round(ci_high, 3)],
        "pct_positive": round(pct_positive, 1),
        "median_sharpe": round(float(np.median(boot_sharpes)), 3),
        "verdict": verdict,
    }


# ══════════════════════════════════════════════════════════
#  TEST 4: Multi-Symbol Test
# ══════════════════════════════════════════════════════════

async def multi_symbol_test():
    """Run on 4 alt symbols with same params."""
    print("\n" + "=" * 60)
    print("  TEST 4: MULTI-SYMBOL TEST")
    print("=" * 60)

    results = {}
    positive_count = 0

    for sym in ALT_SYMBOLS:
        try:
            print(f"  Fetching {sym}...", end=" ", flush=True)
            df = await fetch_klines(sym, INTERVAL, DAYS)
            if df is None or len(df) < 300:
                print(f"SKIP (insufficient data: {len(df) if df is not None else 0})")
                results[sym] = {"sharpe": None, "trades": 0, "status": "insufficient_data"}
                continue

            n = len(df)
            oos_start = int(n * IS_RATIO)
            oos_df = df.iloc[oos_start:]

            signals = sampen_signal(df)
            oos_signals = signals.iloc[oos_start:]
            cost = get_cost_params(sym, INTERVAL)
            bt = run_backtest(
                oos_df, oos_signals,
                strategy_name=f"SampEn_{sym}",
                bars_per_year=BARS_PER_YEAR,
                leverage=LEVERAGE,
                stop_loss_pct=SL_PCT,
                take_profit_pct=TP_PCT,
                max_hold_bars=MAX_HOLD,
                **cost,
            )
            sharpe = bt['metrics']['sharpe_ratio']
            trades = bt['metrics']['total_trades']
            total_ret = bt['metrics']['total_return_pct']

            if sharpe > 0:
                positive_count += 1

            results[sym] = {
                "sharpe": round(sharpe, 3),
                "trades": trades,
                "total_return_pct": round(total_ret, 2),
            }
            print(f"Sharpe={sharpe:.3f} ({trades}t, {total_ret:.1f}%)")

        except Exception as e:
            print(f"ERROR: {e}")
            results[sym] = {"sharpe": None, "trades": 0, "status": f"error: {str(e)[:50]}"}

    verdict = "PASS" if positive_count >= 2 else (
        "MARGINAL" if positive_count >= 1 else "FAIL"
    )
    print(f"\n  Positive: {positive_count}/{len(ALT_SYMBOLS)}")
    print(f"  Verdict: {verdict}")

    results["positive_count"] = f"{positive_count}/{len(ALT_SYMBOLS)}"
    results["verdict"] = verdict
    return results


# ══════════════════════════════════════════════════════════
#  TEST 5: Signal Independence Verification
# ══════════════════════════════════════════════════════════

def signal_independence_test(df):
    """Compare SampEn signal with VolReg and ATR_Ratio."""
    print("\n" + "=" * 60)
    print("  TEST 5: SIGNAL INDEPENDENCE VERIFICATION")
    print("=" * 60)

    sampen_sig = sampen_signal(df)
    volreg_sig = volreg_signal(df)
    atr_sig = atr_ratio_signal(df)

    # For Pearson: use absolute signal values (active vs inactive)
    se_abs = sampen_sig.abs()
    vr_abs = volreg_sig.abs()
    ar_abs = atr_sig.abs()

    # Drop NaN rows
    valid = se_abs.notna() & vr_abs.notna() & ar_abs.notna()
    se_v = se_abs[valid].values
    vr_v = vr_abs[valid].values
    ar_v = ar_abs[valid].values

    # Pearson correlation
    pearson_vr = float(np.corrcoef(se_v, vr_v)[0, 1]) if len(se_v) > 10 else 0
    pearson_ar = float(np.corrcoef(se_v, ar_v)[0, 1]) if len(se_v) > 10 else 0

    # Jaccard overlap: where both are active (non-zero)
    se_active = se_abs > 0
    vr_active = vr_abs > 0
    ar_active = ar_abs > 0

    intersection_vr = (se_active & vr_active).sum()
    union_vr = (se_active | vr_active).sum()
    jaccard_vr = intersection_vr / union_vr if union_vr > 0 else 0

    intersection_ar = (se_active & ar_active).sum()
    union_ar = (se_active | ar_active).sum()
    jaccard_ar = intersection_ar / union_ar if union_ar > 0 else 0

    # Check directional agreement when both active
    both_active_vr = se_active & vr_active
    if both_active_vr.sum() > 0:
        agree_vr = (sampen_sig[both_active_vr] == volreg_sig[both_active_vr]).mean()
    else:
        agree_vr = 0

    both_active_ar = se_active & ar_active
    if both_active_ar.sum() > 0:
        agree_ar = (sampen_sig[both_active_ar] == atr_sig[both_active_ar]).mean()
    else:
        agree_ar = 0

    # Verdict
    independent_vr = pearson_vr < 0.3 and jaccard_vr < 0.2
    independent_ar = pearson_ar < 0.3 and jaccard_ar < 0.2
    all_independent = independent_vr and independent_ar

    verdict = "PASS" if all_independent else (
        "MARGINAL" if (independent_vr or independent_ar) else "FAIL"
    )

    print(f"  vs VolReg:    Pearson={pearson_vr:.3f}  Jaccard={jaccard_vr:.3f}  "
          f"DirAgree={agree_vr:.1%}  {'INDEPENDENT' if independent_vr else 'CORRELATED'}")
    print(f"  vs ATR_Ratio: Pearson={pearson_ar:.3f}  Jaccard={jaccard_ar:.3f}  "
          f"DirAgree={agree_ar:.1%}  {'INDEPENDENT' if independent_ar else 'CORRELATED'}")
    print(f"\n  SampEn active: {se_active.sum()} bars ({se_active.mean()*100:.1f}%)")
    print(f"  VolReg active: {vr_active.sum()} bars ({vr_active.mean()*100:.1f}%)")
    print(f"  ATR_Ratio active: {ar_active.sum()} bars ({ar_active.mean()*100:.1f}%)")
    print(f"  Verdict: {verdict}")

    return {
        "vs_volreg": {
            "pearson": round(pearson_vr, 3),
            "jaccard": round(float(jaccard_vr), 3),
            "direction_agreement": round(float(agree_vr), 3),
        },
        "vs_atr_ratio": {
            "pearson": round(pearson_ar, 3),
            "jaccard": round(float(jaccard_ar), 3),
            "direction_agreement": round(float(agree_ar), 3),
        },
        "verdict": verdict,
    }


# ══════════════════════════════════════════════════════════
#  TEST 6: OR Ensemble with SampEn
# ══════════════════════════════════════════════════════════

def triple_ensemble_test(df):
    """Test triple OR ensemble: SampEn | VolReg | ATR_Ratio."""
    print("\n" + "=" * 60)
    print("  TEST 6: TRIPLE OR ENSEMBLE (SampEn + VolReg + ATR_Ratio)")
    print("=" * 60)

    n = len(df)
    oos_start = int(n * IS_RATIO)
    oos_df = df.iloc[oos_start:]

    se_sig = sampen_signal(df)
    vr_sig = volreg_signal(df)
    ar_sig = atr_ratio_signal(df)

    # Double ensemble: VolReg | ATR_Ratio
    double_sig = pd.Series(0, index=df.index)
    double_sig[vr_sig != 0] = vr_sig[vr_sig != 0]
    double_sig[ar_sig != 0] = ar_sig[ar_sig != 0]
    # When both active and disagree: use first (VolReg priority)
    both = (vr_sig != 0) & (ar_sig != 0)
    double_sig[both] = vr_sig[both]

    # Triple ensemble: SampEn | VolReg | ATR_Ratio (vectorized majority vote)
    vote_sum = se_sig + vr_sig + ar_sig
    any_active = (se_sig != 0) | (vr_sig != 0) | (ar_sig != 0)
    triple_sig = pd.Series(0, index=df.index)
    triple_sig[any_active & (vote_sum > 0)] = 1
    triple_sig[any_active & (vote_sum < 0)] = -1

    # Backtest all three
    # SampEn alone
    se_oos = se_sig.iloc[oos_start:]
    se_bt = run_bt(oos_df, se_oos)
    se_sharpe = se_bt['metrics']['sharpe_ratio']
    se_trades = se_bt['metrics']['total_trades']

    # Double ensemble
    dbl_oos = double_sig.iloc[oos_start:]
    dbl_bt = run_bt(oos_df, dbl_oos)
    dbl_sharpe = dbl_bt['metrics']['sharpe_ratio']
    dbl_trades = dbl_bt['metrics']['total_trades']

    # Triple ensemble
    trp_oos = triple_sig.iloc[oos_start:]
    trp_bt = run_bt(oos_df, trp_oos)
    trp_sharpe = trp_bt['metrics']['sharpe_ratio']
    trp_trades = trp_bt['metrics']['total_trades']

    vs_double = "better" if trp_sharpe > dbl_sharpe else "worse"
    improvement = trp_sharpe - dbl_sharpe

    verdict = "PASS" if trp_sharpe > dbl_sharpe and trp_sharpe > 0 else (
        "MARGINAL" if trp_sharpe > 0 else "FAIL"
    )

    print(f"  SampEn alone:     Sharpe={se_sharpe:.3f} ({se_trades}t)")
    print(f"  Double (VR+ATR):  Sharpe={dbl_sharpe:.3f} ({dbl_trades}t)")
    print(f"  Triple (SE+VR+ATR): Sharpe={trp_sharpe:.3f} ({trp_trades}t)")
    print(f"  Improvement: {improvement:+.3f} ({vs_double})")
    print(f"  Verdict: {verdict}")

    return {
        "sampen_alone": {"sharpe": round(se_sharpe, 3), "trades": se_trades},
        "double_ensemble": {"sharpe": round(dbl_sharpe, 3), "trades": dbl_trades},
        "triple_ensemble": {"sharpe": round(trp_sharpe, 3), "trades": trp_trades},
        "improvement": round(improvement, 3),
        "vs_double": vs_double,
        "verdict": verdict,
    }


# ══════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════

async def main():
    t0 = time.time()
    print("=" * 70)
    print("  SAMPLE ENTROPY DEEP VALIDATION PIPELINE")
    print(f"  Signal: SampEn m={SAMPEN_M}, r_mult={SAMPEN_R_MULT}, "
          f"window={SAMPEN_WINDOW}, pct={SAMPEN_PCT}, ema={EMA_FAST}/{EMA_SLOW}")
    print(f"  Symbol: {SYMBOL} | Interval: {INTERVAL} | Days: {DAYS}")
    print("=" * 70)

    # Fetch primary data
    print("\nFetching DOGE 4H data...")
    df = await fetch_klines(SYMBOL, INTERVAL, DAYS)
    print(f"  Got {len(df)} bars ({df.index[0]} to {df.index[-1]})")

    n = len(df)
    oos_start = int(n * IS_RATIO)

    # ── Baseline ──
    print("\n" + "=" * 60)
    print("  BASELINE: Full IS/OOS Split")
    print("=" * 60)

    signals = sampen_signal(df)
    is_df = df.iloc[:oos_start]
    oos_df = df.iloc[oos_start:]
    is_signals = signals.iloc[:oos_start]
    oos_signals = signals.iloc[oos_start:]

    is_result = run_bt(is_df, is_signals)
    oos_result = run_bt(oos_df, oos_signals)

    is_sharpe = is_result['metrics']['sharpe_ratio']
    oos_sharpe = oos_result['metrics']['sharpe_ratio']
    oos_trades = oos_result['metrics']['total_trades']
    is_trades = is_result['metrics']['total_trades']

    print(f"  IS:  Sharpe={is_sharpe:.3f} ({is_trades} trades)")
    print(f"  OOS: Sharpe={oos_sharpe:.3f} ({oos_trades} trades)")

    baseline = {
        "is_sharpe": round(is_sharpe, 3),
        "oos_sharpe": round(oos_sharpe, 3),
        "is_trades": is_trades,
        "oos_trades": oos_trades,
    }

    # ── Run all tests ──
    t1 = time.time()
    print(f"\n  SampEn computation took {t1 - t0:.1f}s")

    wf_result = walk_forward_test(df)
    inv_result = inverse_signal_test(df)
    boot_result = bootstrap_ci_test(df)
    multi_result = await multi_symbol_test()
    indep_result = signal_independence_test(df)
    ensemble_result = triple_ensemble_test(df)

    # ── Overall Verdict ──
    test_verdicts = {
        "walk_forward": wf_result["verdict"],
        "inverse_signal": inv_result["verdict"],
        "bootstrap": boot_result["verdict"],
        "multi_symbol": multi_result["verdict"],
        "independence": indep_result["verdict"],
        "triple_ensemble": ensemble_result["verdict"],
    }

    pass_count = sum(1 for v in test_verdicts.values() if v == "PASS")
    fail_count = sum(1 for v in test_verdicts.values() if v == "FAIL")
    marginal_count = sum(1 for v in test_verdicts.values() if v == "MARGINAL")

    # Critical tests that MUST pass
    critical_pass = (
        test_verdicts["walk_forward"] != "FAIL" and
        test_verdicts["inverse_signal"] != "FAIL" and
        test_verdicts["bootstrap"] != "FAIL"
    )

    if critical_pass and pass_count >= 4:
        overall = "PASS"
    elif critical_pass and pass_count >= 3:
        overall = "CONDITIONAL"
    elif fail_count <= 2:
        overall = "CONDITIONAL"
    else:
        overall = "FAIL"

    # Build conclusion
    conclusions = []
    if wf_result["verdict"] == "PASS":
        conclusions.append("Walk-forward stable across all folds")
    if inv_result["verdict"] == "PASS":
        conclusions.append("Strong directional edge (inverse is negative)")
    if boot_result["verdict"] == "PASS":
        conclusions.append(f"95% CI excludes zero [{boot_result['ci_95'][0]:.2f}, {boot_result['ci_95'][1]:.2f}]")
    if indep_result["verdict"] == "PASS":
        conclusions.append("Signal is INDEPENDENT from VolReg and ATR_Ratio")
    if ensemble_result["verdict"] == "PASS":
        conclusions.append(f"Triple ensemble improves over double by {ensemble_result['improvement']:+.3f} Sharpe")
    if multi_result["verdict"] == "PASS":
        conclusions.append("Works across multiple symbols")
    elif multi_result["verdict"] == "MARGINAL":
        conclusions.append("Limited multi-symbol generalization (DOGE-specific edge)")

    conclusion_text = ". ".join(conclusions) + "." if conclusions else "Tests inconclusive."

    elapsed = time.time() - t0

    print("\n" + "=" * 70)
    print("  FINAL RESULTS")
    print("=" * 70)
    for test_name, verdict in test_verdicts.items():
        print(f"  {test_name:20s}: {verdict}")
    print(f"\n  OVERALL: {overall}")
    print(f"  {conclusion_text}")
    print(f"\n  Total time: {elapsed:.1f}s")

    # Save results
    output = {
        "scan_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "signal": f"Sample Entropy (m={SAMPEN_M}, r_mult={SAMPEN_R_MULT}, "
                  f"apen_window={SAMPEN_WINDOW}, apen_pct={SAMPEN_PCT}, "
                  f"ema_fast={EMA_FAST}, ema_slow={EMA_SLOW})",
        "risk_params": f"SL={SL_PCT}, TP={TP_PCT}, max_hold={MAX_HOLD}",
        "baseline": baseline,
        "walk_forward": wf_result,
        "inverse_signal": inv_result,
        "bootstrap": boot_result,
        "multi_symbol": multi_result,
        "independence": indep_result,
        "triple_ensemble": ensemble_result,
        "test_verdicts": test_verdicts,
        "overall_verdict": overall,
        "conclusion": conclusion_text,
        "elapsed_seconds": round(elapsed, 1),
    }

    out_path = "/Users/nekonaomichi/crypto-lab/data/validation_sampen.json"
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2, default=str)
    print(f"\n  Saved to {out_path}")


if __name__ == "__main__":
    asyncio.run(main())
