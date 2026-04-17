"""Multi-split train/test validation with averaged PBO + OOS2 holdout.

4 split points (40/60, 50/50, 60/40, 70/30) averaged for robust overfitting detection.
OOS2: completely separate holdout period never seen during IS/OOS.
"""

import logging
import itertools
import math
import numpy as np
import pandas as pd
from engine.backtest import run_backtest
from engine.strategies import STRATEGIES

log = logging.getLogger(__name__)

PURGE_BARS = 16
SPLIT_RATIOS = [0.4, 0.5, 0.6, 0.7]


def _score(metrics: dict, dd_penalty: float = 0.0) -> float:
    """Score combining alpha, risk, and minimum trade count.

    dd_penalty: weight for DD penalty (0=none, 0.5=moderate, 1.0=strong).
    When dd_penalty > 0, deep DD reduces score, guiding optimizer
    toward params that balance alpha and drawdown.
    """
    trades = metrics.get("total_trades", 0)
    if trades < 2:
        return -999
    alpha = metrics.get("alpha_pct", 0)
    pf = metrics.get("profit_factor", 0)
    dd = metrics.get("max_drawdown_pct", -100)
    s = alpha
    if pf > 1:
        s += min(pf - 1, 3) * 2
    if dd > -5:
        s += 1
    # DD penalty: penalize DD worse than -20%
    if dd_penalty > 0 and dd < -20:
        s -= (abs(dd) - 20) * dd_penalty
    return s


def _detect_bpy(df) -> int:
    if len(df) < 2:
        return 35040
    dt = (df["open_time"].iloc[1] - df["open_time"].iloc[0]).total_seconds()
    return max(1, int(365.25 * 24 * 3600 / dt))


def _pbo_single(is_alpha: float, oos_alpha: float) -> float:
    """Compute PBO for a single IS/OOS comparison."""
    if is_alpha > 0 and oos_alpha < 0:
        return 1.0
    elif is_alpha > 0 and oos_alpha < is_alpha * 0.3:
        return 0.5
    return 0.0


def _grid_search(fn, df, combos, keys, name, risk, bpy):
    """Run grid search on a dataframe, return (best_params, best_metrics, best_score).

    Note: equity_ma_bars, dd_throttle_pct, CTS, MDE are NOT applied during IS/OOS.
    They are overlays applied only in the final full-dataset run.
    SL/TP/TS/sl_cooldown ARE applied — they are per-trade stop mechanisms.
    """
    best_score = -999
    best_params = None
    best_metrics = None
    lev = risk.get("leverage", 1.0)
    dd_pen = risk.get("dd_penalty", 0.0)
    for combo in combos:
        params = dict(zip(keys, combo))
        try:
            sig = fn(df, **params)
            res = run_backtest(df, sig, name, params,
                               risk.get("stop_loss_pct", 0), risk.get("take_profit_pct", 0),
                               risk.get("trailing_stop_pct", 0), risk.get("cooldown_bars", 0), bpy,
                               leverage=lev,
                               price_lev_scale=risk.get("price_lev_scale", 0.0),
                               price_lev_lb=risk.get("price_lev_lb", 200),
                               sl_cooldown_bars=risk.get("sl_cooldown_bars", 0),
                               vol_lev_atr=risk.get("vol_lev_atr", 0),
                               vol_lev_threshold=risk.get("vol_lev_threshold", 0.0))
            sc = _score(res["metrics"], dd_penalty=dd_pen)
            if sc > best_score:
                best_score = sc
                best_params = params
                best_metrics = res["metrics"]
        except Exception:
            continue
    return best_params, best_metrics, best_score


def walk_forward_optimize(name: str, df: pd.DataFrame,
                          df_oos2: pd.DataFrame | None = None) -> dict:
    """Multi-split validation with optional OOS2 holdout.

    Args:
        name: strategy name in STRATEGIES registry
        df: main dataset for IS/OOS walk-forward
        df_oos2: separate holdout data for OOS2 validation (never seen in IS/OOS)
    """
    spec = STRATEGIES[name]
    fn = spec["fn"]
    grid = spec["param_grid"]
    risk = spec.get("risk", {})
    bpy = _detect_bpy(df)

    keys = list(grid.keys())
    combos = list(itertools.product(*[grid[k] for k in keys]))
    n = len(df)

    bars_per_day = bpy / 365.25

    pbo_scores = []
    oos_alphas = []
    oos_returns_daily = []
    best_params_overall = None
    best_score_overall = -999
    best_is_metrics = None

    for ratio in SPLIT_RATIOS:
        split = int(n * ratio)
        df_train = df.iloc[:split].reset_index(drop=True)
        df_test = df.iloc[split + PURGE_BARS:].reset_index(drop=True)

        if len(df_test) < 50 or len(df_train) < 100:
            pbo_scores.append(1.0)
            oos_alphas.append(0)
            oos_returns_daily.append(0)
            continue

        bp, bm, bs = _grid_search(fn, df_train, combos, keys, name, risk, bpy)

        if bp is None:
            pbo_scores.append(1.0)
            oos_alphas.append(0)
            oos_returns_daily.append(0)
            continue

        # Eval on test (SL/TP/TS/sl_cooldown included; EQ/DDT/CTS/MDE excluded)
        try:
            sig_test = fn(df_test, **bp)
            test_res = run_backtest(df_test, sig_test, name, bp,
                                    risk.get("stop_loss_pct", 0), risk.get("take_profit_pct", 0),
                                    risk.get("trailing_stop_pct", 0), risk.get("cooldown_bars", 0), bpy,
                                    leverage=risk.get("leverage", 1.0),
                                    price_lev_scale=risk.get("price_lev_scale", 0.0),
                                    price_lev_lb=risk.get("price_lev_lb", 200),
                                    sl_cooldown_bars=risk.get("sl_cooldown_bars", 0),
                               vol_lev_atr=risk.get("vol_lev_atr", 0),
                               vol_lev_threshold=risk.get("vol_lev_threshold", 0.0))
            oos_m = test_res["metrics"]
        except Exception:
            oos_m = {}

        is_alpha = bm.get("alpha_pct", 0)
        oos_alpha = oos_m.get("alpha_pct", 0)
        oos_alphas.append(oos_alpha)
        oos_days = max(1, len(df_test) / bars_per_day)
        oos_ret_daily = oos_m.get("total_return_pct", 0) / oos_days
        oos_returns_daily.append(oos_ret_daily)
        pbo_scores.append(_pbo_single(is_alpha, oos_alpha))

        if bs > best_score_overall:
            best_score_overall = bs
            best_params_overall = bp
            best_is_metrics = bm

    if best_params_overall is None:
        return {"best": None, "oos_metrics": None, "is_metrics": None,
                "pbo_score": 1.0, "oos2_metrics": None, "pbo2_score": 1.0}

    avg_pbo = round(sum(pbo_scores) / len(pbo_scores), 3) if pbo_scores else 1.0
    avg_oos_alpha = round(sum(oos_alphas) / len(oos_alphas), 4) if oos_alphas else 0
    avg_oos_ret_daily = round(sum(oos_returns_daily) / len(oos_returns_daily), 4) if oos_returns_daily else 0

    # Full dataset run with best params (all overlays applied)
    try:
        sig_full = fn(df, **best_params_overall)
        final = run_backtest(df, sig_full, name, best_params_overall,
                             risk.get("stop_loss_pct", 0), risk.get("take_profit_pct", 0),
                             risk.get("trailing_stop_pct", 0), risk.get("cooldown_bars", 0), bpy,
                             leverage=risk.get("leverage", 1.0),
                             equity_ma_bars=risk.get("equity_ma_bars", 0),
                             dd_throttle_pct=risk.get("dd_throttle_pct", 0.0),
                             lev_scale_dd=risk.get("lev_scale_dd", 0.0),
                             cond_ts_pct=risk.get("cond_ts_pct", 0.0),
                             cond_ts_dd_pct=risk.get("cond_ts_dd_pct", 0.0),
                             max_dd_exit_pct=risk.get("max_dd_exit_pct", 0.0),
                             mde_cooldown_bars=risk.get("mde_cooldown_bars", 0),
                             price_lev_scale=risk.get("price_lev_scale", 0.0),
                             price_lev_lb=risk.get("price_lev_lb", 200),
                             sl_cooldown_bars=risk.get("sl_cooldown_bars", 0))
        final["walkforward"] = {
            "oos_metrics": {"alpha_pct": round(avg_oos_alpha * final["metrics"].get("num_days", 270) / max(1, len(SPLIT_RATIOS)), 2),
                            "return_daily_pct": avg_oos_ret_daily},
            "is_metrics": best_is_metrics,
            "pbo_score": avg_pbo,
            "n_splits": len(SPLIT_RATIOS),
            "pbo_per_split": pbo_scores,
            "oos_per_split": [round(a, 4) for a in oos_alphas],
        }
    except Exception:
        final = None

    # ── OOS2: holdout validation on completely unseen data ──
    oos2_metrics = None
    pbo2_score = 1.0
    if final is not None and df_oos2 is not None and len(df_oos2) >= 100:
        try:
            bpy2 = _detect_bpy(df_oos2)
            sig_oos2 = fn(df_oos2, **best_params_overall)
            oos2_res = run_backtest(
                df_oos2, sig_oos2, name, best_params_overall,
                risk.get("stop_loss_pct", 0), risk.get("take_profit_pct", 0),
                risk.get("trailing_stop_pct", 0), risk.get("cooldown_bars", 0), bpy2,
                leverage=risk.get("leverage", 1.0),
                equity_ma_bars=risk.get("equity_ma_bars", 0),
                dd_throttle_pct=risk.get("dd_throttle_pct", 0.0),
                lev_scale_dd=risk.get("lev_scale_dd", 0.0),
                cond_ts_pct=risk.get("cond_ts_pct", 0.0),
                cond_ts_dd_pct=risk.get("cond_ts_dd_pct", 0.0),
                max_dd_exit_pct=risk.get("max_dd_exit_pct", 0.0),
                mde_cooldown_bars=risk.get("mde_cooldown_bars", 0),
                price_lev_scale=risk.get("price_lev_scale", 0.0),
                price_lev_lb=risk.get("price_lev_lb", 200),
                sl_cooldown_bars=risk.get("sl_cooldown_bars", 0))
            oos2_m = oos2_res["metrics"]
            oos2_alpha = oos2_m.get("alpha_pct", 0)
            oos2_days = oos2_m.get("num_days", max(1, len(df_oos2) / bars_per_day))
            oos2_alpha_daily = oos2_alpha / max(1, oos2_days)
            oos2_ret_daily = oos2_m.get("total_return_pct", 0) / max(1, oos2_days)
            oos2_metrics = {
                "alpha_pct": oos2_alpha,
                "return_daily_pct": round(oos2_ret_daily, 4),
                "num_days": round(oos2_days, 1),
                "total_return_pct": oos2_m.get("total_return_pct", 0),
                "benchmark_return_pct": oos2_m.get("benchmark_return_pct", 0),
                "max_drawdown_pct": oos2_m.get("max_drawdown_pct", 0),
                "total_trades": oos2_m.get("total_trades", 0),
                "sharpe_ratio": oos2_m.get("sharpe_ratio", 0),
                "profit_factor": oos2_m.get("profit_factor", 0),
            }
            # PBO2: compare IS daily alpha vs OOS2 daily alpha
            is_alpha_daily = best_is_metrics.get("alpha_pct", 0) / max(1, best_is_metrics.get("num_days", 270)) if best_is_metrics else 0
            pbo2_score = round(_pbo_single(is_alpha_daily, oos2_alpha_daily), 3)

            final["walkforward"]["oos2_metrics"] = oos2_metrics
            final["walkforward"]["pbo2_score"] = pbo2_score
        except Exception as e:
            log.warning(f"OOS2 eval failed for {name}: {e}")

    return {
        "best": final,
        "oos_metrics": {"alpha_pct": round(avg_oos_alpha * (n / bars_per_day) / max(1, len(SPLIT_RATIOS)), 2),
                        "return_daily_pct": avg_oos_ret_daily},
        "is_metrics": best_is_metrics,
        "pbo_score": avg_pbo,
        "oos2_metrics": oos2_metrics,
        "pbo2_score": pbo2_score,
    }
