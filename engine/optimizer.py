"""Parameter grid search optimizer with walk-forward validation."""

import itertools
import logging
import multiprocessing as mp
import pandas as pd
from engine.backtest import run_backtest
from engine.strategies import STRATEGIES

log = logging.getLogger(__name__)

# ── Multiprocessing parallel execution (spawn-safe) ────

_mp_df = None  # Set per-worker by initializer
_mp_df_oos2 = None  # OOS2 holdout data
_mp_df_oos3 = None  # OOS3 holdout data (most recent period)


def _init_mp_spawn(df, df_oos2, strats_dict, df_oos3=None):
    """Initialize worker: store DataFrames and register dynamic strategies."""
    global _mp_df, _mp_df_oos2, _mp_df_oos3
    _mp_df = df
    _mp_df_oos2 = df_oos2
    _mp_df_oos3 = df_oos3
    from engine.strategies import STRATEGIES
    STRATEGIES.update(strats_dict)


def _wf_single(name):
    """Worker: walk-forward optimize one strategy. Returns (name, result|None)."""
    import logging
    _log = logging.getLogger(__name__)
    from engine.walkforward import walk_forward_optimize
    from engine.strategies import STRATEGIES
    if name not in STRATEGIES:
        _log.warning(f"WF_SINGLE: {name} NOT in STRATEGIES (worker has {len(STRATEGIES)} strategies)")
        return (name, None)
    try:
        wf = walk_forward_optimize(name, _mp_df, df_oos2=_mp_df_oos2, df_oos3=_mp_df_oos3)
        if wf["best"]:
            result = wf["best"]
            result["optimization"] = {
                "method": "walk-forward",
                "oos_metrics": wf["oos_metrics"],
                "pbo_score": wf["pbo_score"],
                "oos2_metrics": wf.get("oos2_metrics"),
                "pbo2_score": wf.get("pbo2_score", 1.0),
                "oos3_metrics": wf.get("oos3_metrics"),
                "pbo3_score": wf.get("pbo3_score", 1.0),
            }
            return (name, result)
        else:
            _log.info(f"WF_SINGLE: {name} returned no best result")
    except Exception as e:
        _log.warning(f"WF_SINGLE: {name} exception: {e}")
    return (name, None)


def create_executor(df, df_oos2, names, n_workers=6, df_oos3=None):
    """Create ProcessPoolExecutor with spawn context for async use."""
    from concurrent.futures import ProcessPoolExecutor
    from engine.strategies import STRATEGIES
    strats = {n: STRATEGIES[n] for n in names if n in STRATEGIES}
    ctx = mp.get_context("spawn")
    return ProcessPoolExecutor(
        max_workers=n_workers, mp_context=ctx,
        initializer=_init_mp_spawn, initargs=(df, df_oos2, strats, df_oos3),
    )


def _score(metrics: dict) -> float:
    """Score combining alpha, risk, and minimum trade count."""
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
    return s


def _detect_bars_per_year(df) -> int:
    """Detect bar interval from data and return annualization constant."""
    if len(df) < 2:
        return 35040
    dt = (df["open_time"].iloc[1] - df["open_time"].iloc[0]).total_seconds()
    return max(1, int(365.25 * 24 * 3600 / dt))


def optimize_strategy(name: str, df: pd.DataFrame) -> dict:
    """Grid search over parameter combinations, return best result."""
    spec = STRATEGIES[name]
    fn = spec["fn"]
    grid = spec["param_grid"]
    risk = spec.get("risk", {})
    bpy = _detect_bars_per_year(df)

    keys = list(grid.keys())
    combos = list(itertools.product(*[grid[k] for k in keys]))

    best_result = None
    best_score = -999
    all_results = []

    for combo in combos:
        params = dict(zip(keys, combo))
        try:
            signals = fn(df, **params)
            result = run_backtest(
                df, signals,
                strategy_name=name,
                params=params,
                stop_loss_pct=risk.get("stop_loss_pct", 0),
                take_profit_pct=risk.get("take_profit_pct", 0),
                trailing_stop_pct=risk.get("trailing_stop_pct", 0),
                cooldown_bars=risk.get("cooldown_bars", 0),
                bars_per_year=bpy,
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
                sl_cooldown_bars=risk.get("sl_cooldown_bars", 0),
                vol_lev_atr=risk.get("vol_lev_atr", 0),
                vol_lev_threshold=risk.get("vol_lev_threshold", 0.0),
                trend_lev_sma=risk.get("trend_lev_sma", 0),
                trend_lev_bull=risk.get("trend_lev_bull", 0.0),
                trend_lev_bear=risk.get("trend_lev_bear", 0.0),
            )
            score = _score(result["metrics"])
            all_results.append({"params": params, "score": score, "metrics": result["metrics"]})
            if score > best_score:
                best_score = score
                best_result = result
        except Exception:
            continue

    return {
        "best": best_result,
        "all_results": sorted(all_results, key=lambda x: x["score"], reverse=True),
        "total_combinations": len(combos),
    }


async def run_all_strategies(df: pd.DataFrame, optimize: bool = True,
                             use_walkforward: bool = False,
                             progress_callback=None, result_callback=None,
                             strategy_names: list[str] | None = None) -> list[dict]:
    """Run strategies. Walk-forward mode prevents overfitting."""
    bpy = _detect_bars_per_year(df)
    results = []
    names = strategy_names if strategy_names else list(STRATEGIES.keys())
    total = len(names)

    for idx, name in enumerate(names, 1):
        spec = STRATEGIES.get(name)
        if not spec:
            log.warning(f"Strategy {name} not found, skipping")
            continue
        risk = spec.get("risk", {})
        result = None

        if use_walkforward:
            from engine.walkforward import walk_forward_optimize
            try:
                wf = walk_forward_optimize(name, df)
                if wf["best"]:
                    result = wf["best"]
                    result["optimization"] = {
                        "method": "walk-forward",
                        "oos_metrics": wf["oos_metrics"],
                        "pbo_score": wf["pbo_score"],
                    }
            except Exception as e:
                log.warning(f"WF failed for {name}: {e}")
        elif optimize:
            opt = optimize_strategy(name, df)
            if opt["best"]:
                result = opt["best"]
                result["optimization"] = {
                    "total_combinations": opt["total_combinations"],
                    "top_params": opt["all_results"][:5],
                }
        else:
            fn = spec["fn"]
            params = spec["default_params"]
            signals = fn(df, **params)
            result = run_backtest(
                df, signals,
                strategy_name=name,
                params=params,
                stop_loss_pct=risk.get("stop_loss_pct", 0),
                take_profit_pct=risk.get("take_profit_pct", 0),
                trailing_stop_pct=risk.get("trailing_stop_pct", 0),
                cooldown_bars=risk.get("cooldown_bars", 0),
                bars_per_year=bpy,
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
                sl_cooldown_bars=risk.get("sl_cooldown_bars", 0),
                vol_lev_atr=risk.get("vol_lev_atr", 0),
                vol_lev_threshold=risk.get("vol_lev_threshold", 0.0),
                trend_lev_sma=risk.get("trend_lev_sma", 0),
                trend_lev_bull=risk.get("trend_lev_bull", 0.0),
                trend_lev_bear=risk.get("trend_lev_bear", 0.0),
            )

        if result:
            results.append(result)
            if result_callback:
                result_callback(result)

        # Progress logging
        log.info(f"{idx}/{total}戦略目完了 ({name})")
        print(f"\n{'='*50}", flush=True)
        print(f"  {idx}/{total}戦略目完了 ({name})", flush=True)
        if result:
            m = result["metrics"]
            print(f"  Alpha: {m['alpha_pct']}% | PF: {m['profit_factor']} | Trades: {m['total_trades']}", flush=True)
        else:
            print(f"  (結果なし)", flush=True)
        print(f"{'='*50}\n", flush=True)

        if progress_callback:
            progress_callback(idx, total, name)

    results.sort(key=lambda r: (
        r.get("walkforward", {}).get("oos_metrics", {}).get("alpha_pct", -100) * 2
        + r["metrics"]["total_return_pct"],
        r["metrics"]["sharpe_ratio"],
    ), reverse=True)
    return results
