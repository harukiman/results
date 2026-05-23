"""Systematic scan of 4 NEW signal families on crypto 4H data.
OPTIMIZED: precompute expensive rolling stats, reuse across param combos.

Families:
1. Autocorrelation Regime (rolling lag-1 ACF)
2. OU Half-Life (mean-reversion speed)
3. Directional Accuracy (trend consistency)
4. Price Acceleration (2nd derivative of price)
"""

import asyncio, sys, os, json, warnings, time, itertools
warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
from datetime import datetime

sys.path.insert(0, '/Users/nekonaomichi/crypto-lab')
from engine.data import fetch_klines
from engine.backtest import run_backtest
from engine.cost_config import get_cost_params
from engine.statistical_tests import permutation_test

# ── Constants ──
IS_RATIO = 0.70
BARS_PER_YEAR = 2190
SYMBOLS = ["DOGEUSDT", "SUIUSDT", "SOLUSDT"]
PRIMARY = "DOGEUSDT"
SL_PCT = 0.03
TP_PCT = 0.10
MAX_HOLD = 42


# ── Optimized rolling autocorrelation (vectorized) ──
def fast_rolling_autocorr(returns, window):
    """Vectorized rolling lag-1 autocorrelation using numpy."""
    n = len(returns)
    result = np.full(n, np.nan)
    ret_vals = returns.values if isinstance(returns, pd.Series) else returns

    for i in range(window, n):
        x = ret_vals[i-window:i]
        if np.all(np.isnan(x)):
            continue
        x_clean = x[~np.isnan(x)]
        if len(x_clean) < 3:
            continue
        x1 = x_clean[:-1]
        x2 = x_clean[1:]
        mx1 = np.mean(x1)
        mx2 = np.mean(x2)
        s1 = np.std(x1)
        s2 = np.std(x2)
        if s1 < 1e-15 or s2 < 1e-15:
            result[i] = 0.0
            continue
        result[i] = np.mean((x1 - mx1) * (x2 - mx2)) / (s1 * s2)
    return result


# ── Optimized OU half-life (vectorized regression) ──
def fast_ou_halflife(log_price_vals, window):
    """Compute rolling OU half-life using vectorized operations."""
    n = len(log_price_vals)
    result = np.full(n, np.nan)

    for i in range(window, n):
        y = log_price_vals[i-window:i]
        y_lag = y[:-1]
        dy = np.diff(y)
        std_ylag = np.std(y_lag)
        if std_ylag < 1e-10:
            continue
        # OLS: dy = a + b*y_lag
        n_pts = len(y_lag)
        sum_x = np.sum(y_lag)
        sum_y = np.sum(dy)
        sum_xx = np.sum(y_lag * y_lag)
        sum_xy = np.sum(y_lag * dy)
        denom = n_pts * sum_xx - sum_x * sum_x
        if abs(denom) < 1e-20:
            continue
        b = (n_pts * sum_xy - sum_x * sum_y) / denom
        if b < 0:
            result[i] = -np.log(2) / b
        else:
            result[i] = 9999.0
    return result


def get_sharpe(res):
    return float(res['metrics']['sharpe_ratio'])

def get_trades(res):
    return int(res['metrics']['total_trades'])

def get_dd(res):
    return float(res['metrics']['max_drawdown_pct'])

def get_daily_returns_from_equity(res):
    eq = np.array(res['equity_curve'], dtype=float)
    if len(eq) < 2:
        return np.array([])
    bars_per_day = 6
    daily_eq = eq[::bars_per_day]
    if len(daily_eq) < 2:
        daily_eq = eq
    daily_rets = np.diff(daily_eq) / daily_eq[:-1]
    daily_rets = daily_rets[np.isfinite(daily_rets)]
    return daily_rets

def is_healthy(is_sharpe, oos_sharpe):
    if is_sharpe <= 0.5:
        return False
    if oos_sharpe <= 1.0:
        return False
    if is_sharpe > 0:
        ratio = oos_sharpe / is_sharpe
        if ratio > 3.0:
            return False
    return True

def run_bt(df, signals, cost_params):
    return run_backtest(
        df, signals,
        stop_loss_pct=SL_PCT, take_profit_pct=TP_PCT, max_hold_bars=MAX_HOLD,
        bars_per_year=BARS_PER_YEAR, leverage=1.0, **cost_params
    )


def main():
    print("=" * 70, flush=True)
    print("SYSTEMATIC SCAN: 4 New Signal Families on 4H Crypto Data", flush=True)
    print("=" * 70, flush=True)
    print(f"Scan date: {datetime.now().strftime('%Y-%m-%d %H:%M')}", flush=True)
    print(f"Symbols: {SYMBOLS}", flush=True)
    print(f"IS/OOS split: {IS_RATIO:.0%} / {1-IS_RATIO:.0%}", flush=True)
    print(f"Exit rules: SL={SL_PCT}, TP={TP_PCT}, max_hold={MAX_HOLD}", flush=True)
    print(flush=True)

    # ── Fetch Data ──
    print("Fetching data...", flush=True)
    data = {}
    cost = {}
    for sym in SYMBOLS:
        df = asyncio.run(fetch_klines(sym, "4h", 730))
        data[sym] = df
        cost[sym] = get_cost_params(sym, "4h")
        print(f"  {sym}: {len(df)} bars", flush=True)
    print(flush=True)

    # ── Precompute expensive rolling stats ──
    print("Precomputing rolling stats...", flush=True)

    # Precompute: rolling ACF for each (symbol, window)
    acf_windows = [20, 30, 50, 80]
    precomp_acf = {}
    for sym in SYMBOLS:
        returns = data[sym]['close'].pct_change().values
        for w in acf_windows:
            t0 = time.time()
            precomp_acf[(sym, w)] = fast_rolling_autocorr(
                data[sym]['close'].pct_change(), w
            )
            print(f"  ACF {sym} w={w}: {time.time()-t0:.1f}s", flush=True)

    # Precompute: OU half-life for each (symbol, window)
    hl_windows = [40, 60, 80, 120]
    precomp_hl = {}
    for sym in SYMBOLS:
        log_p = np.log(data[sym]['close'].values)
        for w in hl_windows:
            t0 = time.time()
            precomp_hl[(sym, w)] = fast_ou_halflife(log_p, w)
            print(f"  OU-HL {sym} w={w}: {time.time()-t0:.1f}s", flush=True)

    # Precompute: EMA pairs for each (symbol, fast, slow)
    ema_fasts = [10, 14, 20]
    ema_slows = [30, 40, 60, 80]
    precomp_ema = {}
    for sym in SYMBOLS:
        close = data[sym]['close']
        for ef in ema_fasts:
            ema_f = close.ewm(span=ef).mean().values
            for es in ema_slows:
                if ef >= es:
                    continue
                ema_s = close.ewm(span=es).mean().values
                precomp_ema[(sym, ef, es)] = (ema_f, ema_s)

    # Precompute: bar direction for DirAccuracy
    precomp_bardir = {}
    for sym in SYMBOLS:
        precomp_bardir[sym] = np.sign(data[sym]['close'].pct_change().values)

    # Precompute: momentum and acceleration for PriceAccel
    mom_windows = [7, 10, 14, 20]
    accel_windows = [5, 7, 10, 14]
    precomp_mom = {}
    precomp_accel = {}
    for sym in SYMBOLS:
        close = data[sym]['close']
        for mw in mom_windows:
            mom = close.pct_change(mw).values
            precomp_mom[(sym, mw)] = mom
            for aw in accel_windows:
                # accel = mom.diff(aw) => difference of momentum
                mom_s = pd.Series(mom)
                acc = mom_s.diff(aw).values
                precomp_accel[(sym, mw, aw)] = acc

    print("Precomputation done.\n", flush=True)

    # ── Helper: build signals from precomputed arrays ──
    def make_signals_from_mask_and_ema(mask, ema_f, ema_s, index):
        """mask=True means regime is active. Apply EMA cross for direction."""
        signals = np.zeros(len(index), dtype=int)
        bull = ema_f > ema_s
        bear = ema_f < ema_s
        signals[mask & bull] = 1
        signals[mask & bear] = -1
        return pd.Series(signals, index=index)

    def split_and_test(sym, signals):
        """IS/OOS backtest on a symbol."""
        df = data[sym]
        cp = cost[sym]
        n = len(df)
        split = int(n * IS_RATIO)
        res_is = run_bt(df.iloc[:split], signals.iloc[:split], cp)
        res_oos = run_bt(df.iloc[split:], signals.iloc[split:], cp)
        is_s = get_sharpe(res_is)
        oos_s = get_sharpe(res_oos)
        return {
            "is_sharpe": round(is_s, 4),
            "oos_sharpe": round(oos_s, 4),
            "is_trades": get_trades(res_is),
            "oos_trades": get_trades(res_oos),
            "is_dd": round(get_dd(res_is), 2),
            "oos_dd": round(get_dd(res_oos), 2),
            "healthy": is_healthy(is_s, oos_s),
        }

    # ── Config for all families ──
    families_config = {
        "Autocorrelation": {
            "params_grid": list(itertools.product(
                acf_windows,                       # acf_window
                [-0.05, 0.0, 0.05, 0.10, 0.15],   # acf_threshold
                ema_fasts,                         # ema_fast
                [30, 40, 60, 80],                  # ema_slow
            )),
            "param_names": ["acf_window", "acf_threshold", "ema_fast", "ema_slow"],
        },
        "OU_HalfLife": {
            "params_grid": list(itertools.product(
                hl_windows,                        # hl_window
                [50, 80, 100, 150, 200],           # hl_threshold
                ema_fasts,                         # ema_fast
                [30, 40, 60],                      # ema_slow
            )),
            "param_names": ["hl_window", "hl_threshold", "ema_fast", "ema_slow"],
        },
        "DirAccuracy": {
            "params_grid": list(itertools.product(
                [15, 20, 30, 50],                  # da_window
                [0.55, 0.60, 0.65, 0.70],          # da_threshold
                ema_fasts,                         # ema_fast
                [30, 40, 60, 80],                  # ema_slow
            )),
            "param_names": ["da_window", "da_threshold", "ema_fast", "ema_slow"],
        },
        "PriceAccel": {
            "params_grid": list(itertools.product(
                mom_windows,                       # mom_window
                accel_windows,                     # accel_window
                [0, 0.001, 0.003, 0.005],          # accel_threshold
                ema_fasts,                         # ema_fast
                [30, 40, 60],                      # ema_slow
            )),
            "param_names": ["mom_window", "accel_window", "accel_threshold", "ema_fast", "ema_slow"],
        },
    }

    total_all = sum(len(fc["params_grid"]) for fc in families_config.values())
    for fname, fc in families_config.items():
        print(f"  {fname}: {len(fc['params_grid'])} configs", flush=True)
    print(f"  TOTAL: {total_all} configs x {len(SYMBOLS)} symbols = {total_all * len(SYMBOLS)}", flush=True)
    print(flush=True)

    results = {
        "scan_date": datetime.now().strftime("%Y-%m-%d"),
        "total_configs": total_all,
        "symbols": SYMBOLS,
        "exit_rules": {"sl_pct": SL_PCT, "tp_pct": TP_PCT, "max_hold": MAX_HOLD},
        "families": {},
    }

    # ── Scan each family ──
    for fname, fc in families_config.items():
        print("=" * 60, flush=True)
        print(f"SCANNING: {fname}", flush=True)
        print("=" * 60, flush=True)

        grid = fc["params_grid"]
        pnames = fc["param_names"]
        n_combos = len(grid)

        family_results = {
            "configs_tested": n_combos,
            "healthy_count": 0,
            "multi_symbol_healthy_count": 0,
            "healthy_configs": [],
            "perm_significant": [],
            "is_sharpe_stats": {},
            "oos_sharpe_stats": {},
        }

        all_is_sharpes = {sym: [] for sym in SYMBOLS}
        all_oos_sharpes = {sym: [] for sym in SYMBOLS}
        healthy_configs = []

        t0 = time.time()
        for ci, combo in enumerate(grid):
            if (ci + 1) % 100 == 0 or ci == 0:
                elapsed = time.time() - t0
                rate = (ci + 1) / elapsed if elapsed > 0 else 999
                eta = (n_combos - ci - 1) / rate if rate > 0 else 0
                print(f"  [{ci+1}/{n_combos}] {elapsed:.0f}s, ETA {eta:.0f}s", flush=True)

            params = dict(zip(pnames, combo))

            per_symbol = {}
            for sym in SYMBOLS:
                try:
                    idx = data[sym].index
                    ef = params["ema_fast"]
                    es = params["ema_slow"]
                    if ef >= es or (sym, ef, es) not in precomp_ema:
                        per_symbol[sym] = {"is_sharpe": 0, "oos_sharpe": 0, "healthy": False, "skip": True}
                        all_is_sharpes[sym].append(0.0)
                        all_oos_sharpes[sym].append(0.0)
                        continue
                    ema_f, ema_s = precomp_ema[(sym, ef, es)]

                    # Build regime mask based on family
                    if fname == "Autocorrelation":
                        acf_w = params["acf_window"]
                        acf_th = params["acf_threshold"]
                        acf_vals = precomp_acf[(sym, acf_w)]
                        mask = acf_vals > acf_th

                    elif fname == "OU_HalfLife":
                        hl_w = params["hl_window"]
                        hl_th = params["hl_threshold"]
                        hl_vals = precomp_hl[(sym, hl_w)]
                        mask = hl_vals > hl_th

                    elif fname == "DirAccuracy":
                        da_w = params["da_window"]
                        da_th = params["da_threshold"]
                        trend_dir = np.sign(ema_f - ema_s)
                        bar_dir = precomp_bardir[sym]
                        correct = (trend_dir == bar_dir).astype(float)
                        rolling_acc = pd.Series(correct).rolling(da_w).mean().values
                        mask = rolling_acc > da_th

                    elif fname == "PriceAccel":
                        mw = params["mom_window"]
                        aw = params["accel_window"]
                        at = params["accel_threshold"]
                        accel = precomp_accel[(sym, mw, aw)]
                        # For PriceAccel, mask depends on direction
                        bull = ema_f > ema_s
                        bear = ema_f < ema_s
                        signals_arr = np.zeros(len(idx), dtype=int)
                        signals_arr[(accel > at) & bull] = 1
                        signals_arr[(accel < -at) & bear] = -1
                        signals = pd.Series(signals_arr, index=idx)
                        r = split_and_test(sym, signals)
                        per_symbol[sym] = r
                        all_is_sharpes[sym].append(r["is_sharpe"])
                        all_oos_sharpes[sym].append(r["oos_sharpe"])
                        continue

                    # For non-PriceAccel families
                    signals = make_signals_from_mask_and_ema(mask, ema_f, ema_s, idx)
                    r = split_and_test(sym, signals)
                    per_symbol[sym] = r
                    all_is_sharpes[sym].append(r["is_sharpe"])
                    all_oos_sharpes[sym].append(r["oos_sharpe"])

                except Exception as e:
                    per_symbol[sym] = {"error": str(e), "healthy": False}
                    all_is_sharpes[sym].append(0.0)
                    all_oos_sharpes[sym].append(0.0)

            primary_healthy = per_symbol.get(PRIMARY, {}).get('healthy', False)
            if primary_healthy:
                all_h = all(per_symbol.get(s, {}).get('healthy', False) for s in SYMBOLS)
                healthy_configs.append({
                    "params": params,
                    "results": per_symbol,
                    "multi_symbol_healthy": all_h,
                })

        elapsed_total = time.time() - t0
        print(f"  Completed {n_combos} configs in {elapsed_total:.1f}s ({n_combos/elapsed_total:.1f} configs/s)", flush=True)

        # ── Stats ──
        for sym in SYMBOLS:
            is_arr = np.array(all_is_sharpes[sym])
            oos_arr = np.array(all_oos_sharpes[sym])
            family_results["is_sharpe_stats"][sym] = {
                "mean": round(float(np.nanmean(is_arr)), 4),
                "median": round(float(np.nanmedian(is_arr)), 4),
                "max": round(float(np.nanmax(is_arr)), 4),
                "min": round(float(np.nanmin(is_arr)), 4),
                "pct_positive": round(float(np.mean(is_arr > 0) * 100), 1),
            }
            family_results["oos_sharpe_stats"][sym] = {
                "mean": round(float(np.nanmean(oos_arr)), 4),
                "median": round(float(np.nanmedian(oos_arr)), 4),
                "max": round(float(np.nanmax(oos_arr)), 4),
                "min": round(float(np.nanmin(oos_arr)), 4),
                "pct_positive": round(float(np.mean(oos_arr > 0) * 100), 1),
            }

        family_results["healthy_count"] = len(healthy_configs)
        n_multi = sum(1 for h in healthy_configs if h['multi_symbol_healthy'])
        family_results["multi_symbol_healthy_count"] = n_multi

        print(f"\n  HEALTHY (primary DOGE): {len(healthy_configs)} / {n_combos}", flush=True)
        print(f"  HEALTHY (all 3 symbols): {n_multi} / {n_combos}", flush=True)

        for sym in SYMBOLS:
            ist = family_results["is_sharpe_stats"][sym]
            ost = family_results["oos_sharpe_stats"][sym]
            print(f"  {sym} IS: mean={ist['mean']:.3f} med={ist['median']:.3f} max={ist['max']:.3f} %pos={ist['pct_positive']:.0f}%", flush=True)
            print(f"  {sym} OOS: mean={ost['mean']:.3f} med={ost['median']:.3f} max={ost['max']:.3f} %pos={ost['pct_positive']:.0f}%", flush=True)

        # ── Permutation tests ──
        if healthy_configs:
            healthy_configs.sort(key=lambda x: x['results'][PRIMARY]['oos_sharpe'], reverse=True)
            top_n = min(10, len(healthy_configs))
            bonferroni_threshold = 0.05 / n_combos
            print(f"\n  Permutation tests on top {top_n} healthy configs (Bonferroni p<{bonferroni_threshold:.6f})...", flush=True)

            for hi, hc in enumerate(healthy_configs[:top_n]):
                params = hc['params']
                ef = params["ema_fast"]
                es = params["ema_slow"]
                idx = data[PRIMARY].index
                ema_f, ema_s = precomp_ema[(PRIMARY, ef, es)]

                if fname == "Autocorrelation":
                    acf_vals = precomp_acf[(PRIMARY, params["acf_window"])]
                    mask = acf_vals > params["acf_threshold"]
                    signals = make_signals_from_mask_and_ema(mask, ema_f, ema_s, idx)
                elif fname == "OU_HalfLife":
                    hl_vals = precomp_hl[(PRIMARY, params["hl_window"])]
                    mask = hl_vals > params["hl_threshold"]
                    signals = make_signals_from_mask_and_ema(mask, ema_f, ema_s, idx)
                elif fname == "DirAccuracy":
                    trend_dir = np.sign(ema_f - ema_s)
                    bar_dir = precomp_bardir[PRIMARY]
                    correct = (trend_dir == bar_dir).astype(float)
                    rolling_acc = pd.Series(correct).rolling(params["da_window"]).mean().values
                    mask = rolling_acc > params["da_threshold"]
                    signals = make_signals_from_mask_and_ema(mask, ema_f, ema_s, idx)
                elif fname == "PriceAccel":
                    accel = precomp_accel[(PRIMARY, params["mom_window"], params["accel_window"])]
                    at = params["accel_threshold"]
                    bull = ema_f > ema_s
                    bear = ema_f < ema_s
                    sig_arr = np.zeros(len(idx), dtype=int)
                    sig_arr[(accel > at) & bull] = 1
                    sig_arr[(accel < -at) & bear] = -1
                    signals = pd.Series(sig_arr, index=idx)

                n = len(data[PRIMARY])
                split = int(n * IS_RATIO)
                res_oos = run_bt(data[PRIMARY].iloc[split:], signals.iloc[split:], cost[PRIMARY])
                daily_rets = get_daily_returns_from_equity(res_oos)

                if len(daily_rets) > 10:
                    perm_res = permutation_test(daily_rets, n_permutations=500, statistic="sharpe")
                    p_val = perm_res['p_value']
                    sig_bon = p_val < bonferroni_threshold
                    sig_05 = p_val < 0.05

                    entry = {
                        "params": {k: (float(v) if isinstance(v, (int, float, np.integer, np.floating)) else v) for k, v in params.items()},
                        "primary_is_sharpe": hc['results'][PRIMARY]['is_sharpe'],
                        "primary_oos_sharpe": hc['results'][PRIMARY]['oos_sharpe'],
                        "p_value": p_val,
                        "significant_nominal": sig_05,
                        "significant_bonferroni": sig_bon,
                        "multi_symbol_healthy": hc['multi_symbol_healthy'],
                        "all_symbols": hc['results'],
                    }
                    if sig_05:
                        family_results["perm_significant"].append(entry)

                    status = "BONFERRONI" if sig_bon else ("p<0.05" if sig_05 else "NOT SIG")
                    print(f"    [{hi+1}] IS={hc['results'][PRIMARY]['is_sharpe']:.2f} "
                          f"OOS={hc['results'][PRIMARY]['oos_sharpe']:.2f} "
                          f"p={p_val:.4f} [{status}] "
                          f"multi={hc['multi_symbol_healthy']} | {params}", flush=True)
                else:
                    print(f"    [{hi+1}] Insufficient returns for perm test", flush=True)

            best = healthy_configs[0]
            family_results["best"] = {
                "params": {k: (float(v) if isinstance(v, (int, float, np.integer, np.floating)) else v) for k, v in best['params'].items()},
                "results": best['results'],
            }
            family_results["healthy_configs"] = []
            for hc in healthy_configs[:5]:
                family_results["healthy_configs"].append({
                    "params": {k: (float(v) if isinstance(v, (int, float, np.integer, np.floating)) else v) for k, v in hc['params'].items()},
                    "results": hc['results'],
                    "multi_symbol_healthy": hc['multi_symbol_healthy'],
                })
        else:
            family_results["best"] = None
            family_results["healthy_configs"] = []

        # ── Verdict ──
        if len(healthy_configs) == 0:
            family_results["verdict"] = "REJECTED - No healthy configs found"
        elif n_multi == 0:
            n_ps = len(family_results["perm_significant"])
            if n_ps == 0:
                family_results["verdict"] = "REJECTED - No multi-symbol healthy, no perm significance"
            else:
                family_results["verdict"] = f"WEAK - {n_ps} nominally significant on DOGE only, no multi-symbol"
        elif len(family_results["perm_significant"]) == 0:
            family_results["verdict"] = "REJECTED - Healthy configs but none permutation-significant"
        else:
            bon_sig = [p for p in family_results["perm_significant"] if p["significant_bonferroni"]]
            n_ps = len(family_results["perm_significant"])
            if bon_sig:
                family_results["verdict"] = f"CANDIDATE - {len(bon_sig)} Bonferroni-significant configs"
            else:
                family_results["verdict"] = f"WEAK - {n_ps} nominally significant but none survive Bonferroni"

        print(f"\n  VERDICT: {family_results['verdict']}", flush=True)
        results["families"][fname] = family_results
        print(flush=True)

    # ── Overall Summary ──
    print("=" * 70, flush=True)
    print("OVERALL SUMMARY", flush=True)
    print("=" * 70, flush=True)

    any_candidate = False
    for fname, fres in results["families"].items():
        v = fres["verdict"]
        h = fres["healthy_count"]
        m = fres.get("multi_symbol_healthy_count", 0)
        p = len(fres["perm_significant"])
        print(f"  {fname}: healthy={h}, multi={m}, perm_sig={p} | {v}", flush=True)
        if "CANDIDATE" in v:
            any_candidate = True

    if any_candidate:
        results["overall_verdict"] = "POTENTIAL CANDIDATES FOUND - require further validation"
    else:
        results["overall_verdict"] = "ALL 4 FAMILIES REJECTED - no robust edge found"

    results["conclusion"] = (
        f"Scanned {total_all} configs across 4 families on {len(SYMBOLS)} symbols. "
        f"IS/OOS split: {IS_RATIO:.0%}/{1-IS_RATIO:.0%}. "
        f"Exit rules: SL={SL_PCT}, TP={TP_PCT}, max_hold={MAX_HOLD}. "
        f"Verdict: {results['overall_verdict']}"
    )
    print(f"\n  {results['conclusion']}", flush=True)

    # ── Save ──
    os.makedirs('/Users/nekonaomichi/crypto-lab/data', exist_ok=True)
    out_path = '/Users/nekonaomichi/crypto-lab/data/scan_new_families_v2.json'

    def clean_for_json(obj):
        if isinstance(obj, dict):
            return {k: clean_for_json(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [clean_for_json(v) for v in obj]
        elif isinstance(obj, (np.integer,)):
            return int(obj)
        elif isinstance(obj, (np.floating,)):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, (np.bool_,)):
            return bool(obj)
        elif isinstance(obj, pd.Timestamp):
            return str(obj)
        return obj

    with open(out_path, 'w') as f:
        json.dump(clean_for_json(results), f, indent=2, default=str)
    print(f"\n  Results saved to: {out_path}", flush=True)


if __name__ == "__main__":
    main()
