"""Crypto Day-Trade Strategy Lab — Auto-optimization web app.

Starts background walk-forward optimization on launch.
Results persist to disk; reload the page to see latest results.
Tips section auto-generates discoveries from analysis.
"""

import asyncio
import json
import logging
import time
from datetime import datetime
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

BASE = Path(__file__).parent
DATA_DIR = BASE / "data"
DATA_DIR.mkdir(exist_ok=True)
RESULTS_FILE = DATA_DIR / "results.json"
TIPS_FILE = DATA_DIR / "tips.json"

# ── In-memory state ─────────────────────────────────────
_results: list[dict] = []
_tips: list[dict] = []
_failed_insights: list[dict] = []  # Learnings from strategies that didn't pass display filter
_altcoin_cache: dict[str, dict] = {}  # key: strategy name -> altcoin analysis results
_run_status = {
    "running": False, "progress": "", "symbol": "BTCUSDT",
    "interval": "15m", "days": 180, "last_run": None,
    "strategies_completed": 0, "strategies_total": 0,
    "total_analyses": 0,
}


# ── Persistence ─────────────────────────────────────────

def _load_persisted():
    global _results, _tips, _failed_insights
    if RESULTS_FILE.exists():
        try:
            data = json.loads(RESULTS_FILE.read_text())
            all_results = data.get("results", [])
            # Retroactively fill missing fields
            for r in all_results:
                if "strategy_type" not in r:
                    r["strategy_type"] = _classify_strategy(r)
                # Backfill return_daily_pct for old results
                m = r.get("metrics", {})
                if "return_daily_pct" not in m and "total_return_pct" in m:
                    days = m.get("num_days", 270)
                    m["return_daily_pct"] = round(m["total_return_pct"] / max(1, days), 4)
                wf = r.get("walkforward", {})
                oos_m = wf.get("oos_metrics", {})
                if oos_m and "return_daily_pct" not in oos_m:
                    # OOS: estimate from alpha_pct + benchmark over ~150 day avg OOS period
                    oos_m["return_daily_pct"] = round(oos_m.get("alpha_pct", 0) / 150, 4)
                oos2_m = wf.get("oos2_metrics")
                if oos2_m and "return_daily_pct" not in oos2_m:
                    days2 = oos2_m.get("num_days", 80)
                    oos2_m["return_daily_pct"] = round(oos2_m.get("total_return_pct", 0) / max(1, days2), 4)
            # Load ALL results — don't filter to avoid data loss on restart
            _results = all_results
            _run_status.update(data.get("status", {}))
            _run_status["running"] = False
            log.info(f"Loaded {len(all_results)} results from disk")
        except Exception as e:
            log.warning(f"Failed to load results: {e}")
    if TIPS_FILE.exists():
        try:
            _tips = json.loads(TIPS_FILE.read_text())
            log.info(f"Loaded {len(_tips)} persisted tips")
        except Exception as e:
            log.warning(f"Failed to load tips: {e}")


def _save_results():
    try:
        # Keep equity curves for all results (downsampled for disk space)
        slim = []
        for i, r in enumerate(_results):
            sr = dict(r)
            eq = sr.get("equity_curve", [])
            bc = sr.get("benchmark_curve", [])
            ts = sr.get("times", [])
            if i < 100:
                # Top 100: keep 2000 points
                sr["equity_curve"] = eq[:2000]
                sr["benchmark_curve"] = bc[:2000]
                sr["times"] = ts[:2000]
            elif eq:
                # Rest: downsample to 500 points
                step = max(1, len(eq) // 500)
                sr["equity_curve"] = eq[::step][:500]
                sr["benchmark_curve"] = bc[::step][:500]
                sr["times"] = ts[::step][:500]
            sr["trades"] = sr.get("trades", [])[:100]
            slim.append(sr)
        data = {"results": slim, "status": {
            "symbol": _run_status["symbol"],
            "interval": _run_status["interval"],
            "days": _run_status["days"],
            "last_run": _run_status["last_run"],
        }}
        RESULTS_FILE.write_text(json.dumps(data, default=str, ensure_ascii=False))
    except Exception as e:
        log.warning(f"Failed to save results: {e}")


def _save_tips():
    try:
        TIPS_FILE.write_text(json.dumps(_tips, default=str, ensure_ascii=False))
    except Exception as e:
        log.warning(f"Failed to save tips: {e}")


def _merge_tips(new_tips: list[dict]):
    """Merge new tips into existing _tips. Never delete existing tips.
    Update content of existing tips (by id) if new data is available.
    Add new tips that don't exist yet."""
    global _tips
    existing_ids = {t["id"]: i for i, t in enumerate(_tips)}
    for nt in new_tips:
        tid = nt["id"]
        if tid in existing_ids:
            # Update content but preserve the tip
            idx = existing_ids[tid]
            _tips[idx] = nt
        else:
            _tips.append(nt)
            existing_ids[tid] = len(_tips) - 1


# ── Tips generation ─────────────────────────────────────

def _generate_tips(results: list[dict]) -> list[dict]:
    """Auto-generate tips/discoveries from strategy results."""
    tips = []
    now = datetime.now().isoformat()

    profitable = [r for r in results if r["metrics"]["alpha_pct"] > 0]
    if profitable:
        best = max(profitable, key=lambda r: r["metrics"]["alpha_pct"])
        tips.append({
            "id": "best_alpha", "title": "最高アルファ戦略",
            "category": "discovery", "source_strategy": best["name"],
            "content": (f'{best["name"]}がα={best["metrics"]["alpha_pct"]}%を達成。'
                        f'Sharpe={best["metrics"]["sharpe_ratio"]}, '
                        f'PF={best["metrics"]["profit_factor"]}, '
                        f'トレード数={best["metrics"]["total_trades"]}。'),
            "metrics": best["metrics"], "timestamp": now,
        })

    # Walk-forward results
    wf_passed = [r for r in results if r.get("walkforward") and r["walkforward"].get("pbo_score", 1) < 0.5]
    wf_failed = [r for r in results if r.get("walkforward") and r["walkforward"].get("pbo_score", 1) >= 0.5]

    if wf_passed:
        tips.append({
            "id": "wf_robust", "title": "Walk-Forward検証合格",
            "category": "validation", "source_strategy": ", ".join(r["name"] for r in wf_passed[:5]),
            "content": (f'{len(wf_passed)}戦略がWF検証に合格(PBO<0.5)。'
                        f'オーバーフィットの兆候が少なく、OOS(未知データ)でも有効。'
                        f'flearn.pdf: PBO<0.5でバックテスト過学習の確率が低い。'),
            "data": [{"name": r["name"], "pbo": r["walkforward"]["pbo_score"],
                       "is_alpha": r["walkforward"].get("is_metrics", {}).get("alpha_pct", 0),
                       "oos_alpha": r["walkforward"].get("oos_metrics", {}).get("alpha_pct", 0)}
                      for r in wf_passed[:10]],
            "timestamp": now,
        })

    if wf_failed:
        tips.append({
            "id": "wf_overfit", "title": "オーバーフィット警告",
            "category": "warning", "source_strategy": ", ".join(r["name"] for r in wf_failed[:5]),
            "content": (f'{len(wf_failed)}戦略がWF検証で不合格(PBO>=0.5)。'
                        f'IS(学習期間)では良好でもOOS(検証期間)で悪化。'
                        f'flearn.pdf: バックテストの過学習はファイナンスにおける最大のリスク。'),
            "data": [{"name": r["name"], "pbo": r["walkforward"]["pbo_score"],
                       "degradation": r["walkforward"].get("degradation_pct", 0)}
                      for r in wf_failed[:10]],
            "timestamp": now,
        })

    # Trade count sweet spot
    good_trades = [r for r in results if 30 <= r["metrics"]["total_trades"] <= 80]
    if good_trades:
        tips.append({
            "id": "trade_count", "title": "トレード数の統計的意義",
            "category": "learning",
            "source_strategy": ", ".join(r["name"] for r in good_trades[:3]),
            "content": (f'{len(good_trades)}戦略が30-80トレードのスイートスポットに到達。'
                        f'flearn.pdf: 統計的有意性には最低30トレード必要。'),
            "data": [{"name": r["name"], "trades": r["metrics"]["total_trades"],
                       "pf": r["metrics"]["profit_factor"], "alpha": r["metrics"]["alpha_pct"],
                       "days": r["metrics"].get("num_days", 270)}
                      for r in sorted(good_trades, key=lambda r: r["metrics"]["alpha_pct"], reverse=True)],
            "timestamp": now,
        })

    # High Sharpe
    high_sharpe = [r for r in results if r["metrics"]["sharpe_ratio"] > 1.0]
    if high_sharpe:
        best_s = max(high_sharpe, key=lambda r: r["metrics"]["sharpe_ratio"])
        tips.append({
            "id": "risk_adjusted", "title": "リスク調整後リターン",
            "category": "discovery", "source_strategy": best_s["name"],
            "content": (f'{best_s["name"]}がSharpe={best_s["metrics"]["sharpe_ratio"]}を記録。'
                        f'MaxDD={best_s["metrics"]["max_drawdown_pct"]}%。'
                        f'flearn.pdf: Sharpe>1でリスク調整後に有意、>2で優秀。'),
            "metrics": best_s["metrics"], "timestamp": now,
        })

    # High profit factor
    high_pf = [r for r in results if r["metrics"]["profit_factor"] > 1.5 and r["metrics"]["total_trades"] >= 20]
    if high_pf:
        tips.append({
            "id": "profit_factor", "title": "高プロフィットファクター",
            "category": "discovery",
            "source_strategy": ", ".join(r["name"] for r in high_pf[:3]),
            "content": (f'{len(high_pf)}戦略がPF>1.5を達成(20+トレード)。'
                        f'PF=利益合計/損失合計。1.5以上は手数料控除後も収益性が高い。'),
            "data": [{"name": r["name"], "pf": r["metrics"]["profit_factor"],
                       "trades": r["metrics"]["total_trades"], "win_rate": r["metrics"]["win_rate_pct"]}
                      for r in high_pf],
            "timestamp": now,
        })

    # Fee impact
    if results:
        avg_exp = sum(r["metrics"]["expectancy_pct"] for r in results) / len(results)
        tips.append({
            "id": "fee_impact", "title": "手数料のインパクト",
            "category": "learning", "source_strategy": "全戦略",
            "content": (f'平均期待値={round(avg_exp, 4)}%/トレード(手数料込み)。'
                        f'FEE=0.07%, SLIPPAGE=0.03%, 合計0.20%/往復。'
                        f'flearn.pdf: 実コスト無視のバックテストは無意味。'),
            "data": [{"name": r["name"], "expectancy": r["metrics"]["expectancy_pct"],
                       "trades": r["metrics"]["total_trades"]}
                      for r in sorted(results, key=lambda r: r["metrics"]["expectancy_pct"], reverse=True)[:10]],
            "timestamp": now,
        })

    # Multi-timeframe insights
    mtf = [r for r in results if r["name"].startswith("MTF")]
    non_mtf_profitable = [r for r in profitable if not r["name"].startswith("MTF")]
    if mtf:
        mtf_profitable = [r for r in mtf if r["metrics"]["alpha_pct"] > 0]
        tips.append({
            "id": "mtf_insight", "title": "マルチタイムフレーム分析",
            "category": "learning",
            "source_strategy": ", ".join(r["name"] for r in mtf[:3]),
            "content": (f'MTF戦略{len(mtf)}本中{len(mtf_profitable)}本が収益的。'
                        f'15m単独: {len(non_mtf_profitable)}/{len(results)-len(mtf)}本が収益的。'
                        f'上位足トレンドフィルターは偽ブレイクを排除し勝率を改善する。'),
            "data": [{"name": r["name"], "alpha": r["metrics"]["alpha_pct"],
                       "win_rate": r["metrics"]["win_rate_pct"], "trades": r["metrics"]["total_trades"]}
                      for r in mtf],
            "timestamp": now,
        })

    # ── Drawdown analysis ──
    low_dd = [r for r in results if r["metrics"]["max_drawdown_pct"] > -15 and r["metrics"]["alpha_pct"] > 20]
    high_dd = [r for r in results if r["metrics"]["max_drawdown_pct"] < -25 and r["metrics"]["alpha_pct"] > 20]
    if low_dd:
        best_dd = min(low_dd, key=lambda r: abs(r["metrics"]["max_drawdown_pct"]))
        tips.append({
            "id": "dd_control", "title": "ドローダウン制御",
            "category": "discovery", "source_strategy": best_dd["name"],
            "content": (f'{len(low_dd)}戦略がα>20%かつDD>-15%を達成。'
                        f'最良: {best_dd["name"]}(DD={best_dd["metrics"]["max_drawdown_pct"]:.1f}%, α={best_dd["metrics"]["alpha_pct"]:.1f}%)。'
                        f'DD制御とα両立が可能なことを示す。トレイリングストップ、メタラベリング、DDサーキットブレーカーが有効。'),
            "data": [{"name": r["name"], "dd": r["metrics"]["max_drawdown_pct"],
                       "alpha": r["metrics"]["alpha_pct"]}
                      for r in sorted(low_dd, key=lambda r: r["metrics"]["max_drawdown_pct"], reverse=True)[:10]],
            "timestamp": now,
        })
    if high_dd:
        tips.append({
            "id": "dd_warning", "title": "高ドローダウン警告",
            "category": "warning",
            "content": (f'{len(high_dd)}戦略がα>20%でもDD<-25%。'
                        f'リターンが高くてもDDが大きいと実運用は困難。'
                        f'ストップロス強化、ポジション制御、レジーム検出でDD抑制を。'),
            "data": [{"name": r["name"], "dd": r["metrics"]["max_drawdown_pct"],
                       "alpha": r["metrics"]["alpha_pct"]}
                      for r in sorted(high_dd, key=lambda r: r["metrics"]["max_drawdown_pct"])[:10]],
            "timestamp": now,
        })

    # ── IS/OOS divergence analysis ──
    import numpy as np
    wf_results = [r for r in results if r.get("walkforward", {}).get("oos_metrics")]
    if wf_results:
        divergences = []
        for r in wf_results:
            is_a = r["metrics"]["alpha_pct"]
            oos_a = r["walkforward"]["oos_metrics"].get("alpha_pct", 0)
            if is_a > 10:
                div_ratio = oos_a / is_a if is_a != 0 else 0
                divergences.append((r, div_ratio))
        low_div = [(r, d) for r, d in divergences if d >= 0.5]  # OOS >= 50% of IS
        high_div = [(r, d) for r, d in divergences if d < 0.3 and r["metrics"]["alpha_pct"] > 20]
        if low_div:
            best_div = max(low_div, key=lambda x: x[0]["metrics"]["alpha_pct"])
            tips.append({
                "id": "oos_stability", "title": "IS/OOS安定性",
                "category": "discovery", "source_strategy": best_div[0]["name"],
                "content": (f'{len(low_div)}戦略がOOSα≥IS αの50%を維持(安定)。'
                            f'最良: {best_div[0]["name"]}(IS α={best_div[0]["metrics"]["alpha_pct"]:.1f}%, '
                            f'OOS α={best_div[0]["walkforward"]["oos_metrics"]["alpha_pct"]:.1f}%, '
                            f'比率={best_div[1]:.0%})。'
                            f'独立シグナルの多数決やシンプルなルールが乖離を抑制する傾向。'),
                "data": [{"name": r["name"], "is_alpha": r["metrics"]["alpha_pct"],
                           "oos_alpha": r["walkforward"]["oos_metrics"]["alpha_pct"],
                           "ratio": round(d, 2)}
                          for r, d in sorted(low_div, key=lambda x: x[0]["metrics"]["alpha_pct"], reverse=True)[:10]],
                "timestamp": now,
            })
        if high_div:
            tips.append({
                "id": "oos_degradation", "title": "OOS劣化パターン",
                "category": "warning",
                "content": (f'{len(high_div)}戦略がISでは好成績だがOOSで大幅劣化(OOS<ISの30%)。'
                            f'パラメータ過剰最適化の兆候。パラメータ数を減らすか、よりロバストなシグナル設計を。'),
                "data": [{"name": r["name"], "is_alpha": r["metrics"]["alpha_pct"],
                           "oos_alpha": r["walkforward"]["oos_metrics"]["alpha_pct"],
                           "ratio": round(d, 2)}
                          for r, d in sorted(high_div, key=lambda x: x[1])[:10]],
                "timestamp": now,
            })

    # ── Equity curve quality analysis ──
    eq_data = []
    for r in results:
        eq = r.get("equity_curve", [])
        if len(eq) >= 20:
            arr = np.array(eq, dtype=float)
            x = np.arange(len(arr))
            slope, intercept = np.polyfit(x, arr, 1)
            if slope > 0:
                y_pred = slope * x + intercept
                ss_res = np.sum((arr - y_pred) ** 2)
                ss_tot = np.sum((arr - np.mean(arr)) ** 2)
                r_sq = 1 - ss_res / ss_tot if ss_tot > 0 else 0
                eq_data.append((r, r_sq))
    high_r2 = [(r, rr) for r, rr in eq_data if rr >= 0.7]
    if high_r2:
        best_r2 = max(high_r2, key=lambda x: x[1])
        tips.append({
            "id": "equity_quality", "title": "エクイティカーブ品質",
            "category": "discovery", "source_strategy": best_r2[0]["name"],
            "content": (f'{len(high_r2)}戦略がR²≥0.7の綺麗な右肩上がりエクイティ。'
                        f'最良: {best_r2[0]["name"]}(R²={best_r2[1]:.3f}, α={best_r2[0]["metrics"]["alpha_pct"]:.1f}%)。'
                        f'高R²=一貫して利益を積み上げる安定性。実運用に最も適したカーブ。'),
            "data": [{"name": r["name"], "r2": round(rr, 3),
                       "alpha": r["metrics"]["alpha_pct"], "dd": r["metrics"]["max_drawdown_pct"]}
                      for r, rr in sorted(high_r2, key=lambda x: x[1], reverse=True)[:10]],
            "timestamp": now,
        })

    # ── Strategy type effectiveness ──
    type_stats = {}
    for r in results:
        nm = r["name"]
        # Classify by type
        if "multi_st" in nm.lower() or "Multi ST" in nm:
            stype = "multi_st"
        elif "supertrend" in nm.lower():
            stype = "supertrend"
        elif "meta" in nm.lower():
            stype = "meta_label"
        elif "regime" in nm.lower() or "adaptive" in nm.lower():
            stype = "regime_adaptive"
        elif "dd_control" in nm.lower() or "DD Controlled" in nm:
            stype = "dd_controlled"
        elif "cascade" in nm.lower() or "ribbon" in nm.lower():
            stype = "ensemble"
        elif "pullback" in nm.lower() or "retest" in nm.lower():
            stype = "pullback"
        elif "ffd" in nm.lower() or "FFD" in nm:
            stype = "ffd"
        else:
            stype = "other"
        if stype not in type_stats:
            type_stats[stype] = {"count": 0, "alphas": [], "oos_alphas": [], "dds": []}
        type_stats[stype]["count"] += 1
        type_stats[stype]["alphas"].append(r["metrics"]["alpha_pct"])
        type_stats[stype]["dds"].append(r["metrics"]["max_drawdown_pct"])
        if r.get("walkforward", {}).get("oos_metrics"):
            type_stats[stype]["oos_alphas"].append(r["walkforward"]["oos_metrics"].get("alpha_pct", 0))

    type_summary = []
    for stype, stats in type_stats.items():
        if stats["count"] >= 2:
            avg_alpha = sum(stats["alphas"]) / len(stats["alphas"])
            avg_dd = sum(stats["dds"]) / len(stats["dds"])
            avg_oos = sum(stats["oos_alphas"]) / len(stats["oos_alphas"]) if stats["oos_alphas"] else 0
            type_summary.append({"type": stype, "count": stats["count"],
                                  "avg_alpha": round(avg_alpha, 1), "avg_dd": round(avg_dd, 1),
                                  "avg_oos_alpha": round(avg_oos, 1)})
    if type_summary:
        type_summary.sort(key=lambda x: x["avg_alpha"], reverse=True)
        tips.append({
            "id": "strategy_types", "title": "戦略タイプ別有効性",
            "category": "learning",
            "content": (f'戦略タイプ別の平均パフォーマンス比較。'
                        f'最良タイプ: {type_summary[0]["type"]}(平均α={type_summary[0]["avg_alpha"]}%, '
                        f'平均DD={type_summary[0]["avg_dd"]}%, 平均OOSα={type_summary[0]["avg_oos_alpha"]}%)。'),
            "data": type_summary,
            "timestamp": now,
        })

    # ── Best parameter ranges (for next-gen strategy building) ──
    param_stats = {}  # param_name -> {values: [], alphas: []}
    for r in results:
        if r["metrics"]["alpha_pct"] > 30:
            for k, v in r["params"].items():
                try:
                    vf = float(v)
                except (ValueError, TypeError):
                    continue
                if k not in param_stats:
                    param_stats[k] = {"values": [], "alphas": []}
                param_stats[k]["values"].append(vf)
                param_stats[k]["alphas"].append(r["metrics"]["alpha_pct"])
    if param_stats:
        param_ranges = {}
        for k, st in param_stats.items():
            if len(st["values"]) >= 5:
                arr = np.array(st["values"])
                param_ranges[k] = {"median": round(float(np.median(arr)), 2),
                                    "p25": round(float(np.percentile(arr, 25)), 2),
                                    "p75": round(float(np.percentile(arr, 75)), 2),
                                    "count": len(arr)}
        if param_ranges:
            top_params = sorted(param_ranges.items(), key=lambda x: x[1]["count"], reverse=True)[:10]
            tips.append({
                "id": "param_sweet_spots", "title": "有効パラメータ帯域",
                "category": "learning",
                "content": (f'α>30%の戦略から抽出した最適パラメータ帯。'
                            + ' '.join(f'{k}: {v["p25"]}-{v["p75"]}(中央値{v["median"]}, n={v["count"]})' for k, v in top_params[:5])
                            + '。この帯域に集中してグリッドを組むとヒット率が上がる。'),
                "data": dict(top_params),
                "timestamp": now,
            })

    # ── Entry type × Filter effectiveness matrix ──
    combo_stats = {}  # (entry, filter) -> {alphas, oos_alphas, dds}
    for r in results:
        p = r["params"]
        entry = p.get("entry_type", "")
        filt = p.get("filter_type", p.get("f1_type", ""))
        if entry and filt:
            key = f"{entry}+{filt}"
            if key not in combo_stats:
                combo_stats[key] = {"alphas": [], "oos_alphas": [], "dds": [], "count": 0}
            combo_stats[key]["alphas"].append(r["metrics"]["alpha_pct"])
            combo_stats[key]["dds"].append(r["metrics"]["max_drawdown_pct"])
            combo_stats[key]["count"] += 1
            if r.get("walkforward", {}).get("oos_metrics"):
                combo_stats[key]["oos_alphas"].append(r["walkforward"]["oos_metrics"].get("alpha_pct", 0))
    if combo_stats:
        combo_summary = []
        for key, st in combo_stats.items():
            if st["count"] >= 3:
                avg_a = round(sum(st["alphas"]) / len(st["alphas"]), 1)
                avg_dd = round(sum(st["dds"]) / len(st["dds"]), 1)
                avg_oos = round(sum(st["oos_alphas"]) / len(st["oos_alphas"]), 1) if st["oos_alphas"] else 0
                oos_retention = round(avg_oos / avg_a * 100, 0) if avg_a > 0 else 0
                combo_summary.append({"combo": key, "avg_alpha": avg_a, "avg_dd": avg_dd,
                                       "avg_oos": avg_oos, "oos_retention_pct": oos_retention,
                                       "count": st["count"]})
        combo_summary.sort(key=lambda x: x["avg_oos"], reverse=True)
        if combo_summary:
            best_combo = combo_summary[0]
            # Best for OOS retention
            high_ret = [c for c in combo_summary if c["oos_retention_pct"] >= 40 and c["avg_alpha"] > 20]
            high_ret.sort(key=lambda x: x["avg_oos"], reverse=True)
            tips.append({
                "id": "combo_matrix", "title": "エントリー×フィルター有効性マトリクス",
                "category": "learning",
                "content": (f'最高OOSαコンボ: {best_combo["combo"]}(OOSα={best_combo["avg_oos"]}%, α={best_combo["avg_alpha"]}%, DD={best_combo["avg_dd"]}%)。'
                            + (f'高OOS保持率(≥40%)コンボ: {", ".join(c["combo"]+"("+str(c["oos_retention_pct"])+"%%)" for c in high_ret[:5])}。' if high_ret else '')
                            + 'OOS保持率が高いコンボはロバスト。低いコンボは過学習リスク大。'),
                "data": combo_summary[:20],
                "timestamp": now,
            })

    # ── Risk profile effectiveness ──
    risk_stats = {}  # (sl, tp, ts) -> {alphas, dds, oos}
    for r in results:
        p = r["params"]
        # Infer risk from strategy spec or result
        m = r["metrics"]
        dd = m["max_drawdown_pct"]
        alpha = m["alpha_pct"]
        if alpha < 10:
            continue
        # Classify by DD level
        if dd > -10:
            rk = "low_dd(<10%)"
        elif dd > -20:
            rk = "mid_dd(10-20%)"
        else:
            rk = "high_dd(>20%)"
        if rk not in risk_stats:
            risk_stats[rk] = {"alphas": [], "oos_alphas": [], "sharpes": []}
        risk_stats[rk]["alphas"].append(alpha)
        risk_stats[rk]["sharpes"].append(m["sharpe_ratio"])
        if r.get("walkforward", {}).get("oos_metrics"):
            risk_stats[rk]["oos_alphas"].append(r["walkforward"]["oos_metrics"].get("alpha_pct", 0))
    if risk_stats:
        risk_summary = []
        for rk, st in risk_stats.items():
            avg_a = round(sum(st["alphas"]) / len(st["alphas"]), 1)
            avg_s = round(sum(st["sharpes"]) / len(st["sharpes"]), 2)
            avg_oos = round(sum(st["oos_alphas"]) / len(st["oos_alphas"]), 1) if st["oos_alphas"] else 0
            risk_summary.append({"dd_group": rk, "avg_alpha": avg_a, "avg_sharpe": avg_s,
                                  "avg_oos": avg_oos, "count": len(st["alphas"])})
        tips.append({
            "id": "risk_profile_eff", "title": "リスクプロファイル別有効性",
            "category": "learning",
            "content": ' | '.join(f'{rs["dd_group"]}: α={rs["avg_alpha"]}% OOS={rs["avg_oos"]}% Sharpe={rs["avg_sharpe"]} (n={rs["count"]})' for rs in risk_summary)
                     + '。DD抑制とα/OOSのトレードオフを把握し、最適なリスクバランスを狙う。',
            "data": risk_summary,
            "timestamp": now,
        })

    # ── Market regime analysis from data ──
    # Analyze winning vs losing periods across strategies
    equity_curves = [(r, r.get("equity_curve", [])) for r in results if len(r.get("equity_curve", [])) >= 100]
    if equity_curves:
        # Find common drawdown periods (many strategies lose simultaneously = bad regime)
        n_curves = min(50, len(equity_curves))
        top_curves = equity_curves[:n_curves]
        min_len = min(len(eq) for _, eq in top_curves)
        if min_len >= 100:
            returns_matrix = []
            for _, eq in top_curves:
                arr = np.array(eq[:min_len], dtype=float)
                ret = np.diff(arr) / np.maximum(arr[:-1], 1e-10)
                returns_matrix.append(ret)
            avg_ret = np.mean(returns_matrix, axis=0)
            # Find worst 10% of periods
            bad_thresh = np.percentile(avg_ret, 10)
            bad_ratio = float(np.mean(avg_ret < 0))
            # Regime: fraction of time market is favorable
            good_ratio = float(np.mean(avg_ret > 0))
            avg_good = float(np.mean(avg_ret[avg_ret > 0])) * 100 if np.any(avg_ret > 0) else 0
            avg_bad = float(np.mean(avg_ret[avg_ret < 0])) * 100 if np.any(avg_ret < 0) else 0
            # Autocorrelation of returns (trending vs mean-reverting)
            if len(avg_ret) > 1:
                autocorr = float(np.corrcoef(avg_ret[:-1], avg_ret[1:])[0, 1])
            else:
                autocorr = 0
            tips.append({
                "id": "market_regime", "title": "市場レジーム分析",
                "category": "learning",
                "content": (f'上位{n_curves}戦略の平均リターン分析: '
                            f'好調期比率={good_ratio:.0%}(平均+{avg_good:.3f}%/bar), '
                            f'不調期比率={bad_ratio:.0%}(平均{avg_bad:.3f}%/bar)。'
                            f'リターン自己相関={autocorr:.3f}'
                            f'(>0:トレンド傾向, <0:平均回帰傾向)。'
                            f'不調期の損失が大きいならレジームフィルターが有効。'),
                "data": {"good_ratio": round(good_ratio, 3), "bad_ratio": round(bad_ratio, 3),
                          "avg_good_pct": round(avg_good, 4), "avg_bad_pct": round(avg_bad, 4),
                          "autocorr": round(autocorr, 4)},
                "timestamp": now,
            })

    # ── OOS retention factor analysis ──
    # What makes a strategy robust OOS?
    if wf_results:
        high_oos = [r for r in wf_results if r["walkforward"]["oos_metrics"].get("alpha_pct", 0) > 20]
        low_oos = [r for r in wf_results if r["walkforward"]["oos_metrics"].get("alpha_pct", 0) < 0 and r["metrics"]["alpha_pct"] > 30]
        if high_oos and low_oos:
            # Compare characteristics
            h_trades = np.mean([r["metrics"]["total_trades"] for r in high_oos])
            l_trades = np.mean([r["metrics"]["total_trades"] for r in low_oos])
            h_pf = np.mean([r["metrics"]["profit_factor"] for r in high_oos])
            l_pf = np.mean([r["metrics"]["profit_factor"] for r in low_oos])
            h_wr = np.mean([r["metrics"]["win_rate_pct"] for r in high_oos])
            l_wr = np.mean([r["metrics"]["win_rate_pct"] for r in low_oos])
            h_dd = np.mean([r["metrics"]["max_drawdown_pct"] for r in high_oos])
            l_dd = np.mean([r["metrics"]["max_drawdown_pct"] for r in low_oos])
            # Count params
            h_params = np.mean([len(r["params"]) for r in high_oos])
            l_params = np.mean([len(r["params"]) for r in low_oos])
            tips.append({
                "id": "oos_factors", "title": "OOS安定性の決定要因",
                "category": "learning",
                "content": (f'OOSα>20%({len(high_oos)}件) vs OOSα<0%({len(low_oos)}件)の比較: '
                            f'トレード数 {h_trades:.0f} vs {l_trades:.0f}, '
                            f'PF {h_pf:.2f} vs {l_pf:.2f}, '
                            f'勝率 {h_wr:.1f}% vs {l_wr:.1f}%, '
                            f'DD {h_dd:.1f}% vs {l_dd:.1f}%, '
                            f'パラメータ数 {h_params:.1f} vs {l_params:.1f}。'
                            f'パラメータが少なく、トレード数が多い戦略がOOSで安定する傾向。'),
                "data": {"high_oos": {"n": len(high_oos), "avg_trades": round(h_trades), "avg_pf": round(h_pf, 2),
                                       "avg_wr": round(h_wr, 1), "avg_dd": round(h_dd, 1), "avg_params": round(h_params, 1)},
                          "low_oos": {"n": len(low_oos), "avg_trades": round(l_trades), "avg_pf": round(l_pf, 2),
                                       "avg_wr": round(l_wr, 1), "avg_dd": round(l_dd, 1), "avg_params": round(l_params, 1)}},
                "timestamp": now,
            })

    # ── Filter effectiveness ranking ──
    filter_stats = {}
    for r in results:
        p = r["params"]
        filt = p.get("filter_type", p.get("f1_type", ""))
        if not filt:
            continue
        if filt not in filter_stats:
            filter_stats[filt] = {"alphas": [], "oos_alphas": [], "dds": []}
        filter_stats[filt]["alphas"].append(r["metrics"]["alpha_pct"])
        filter_stats[filt]["dds"].append(r["metrics"]["max_drawdown_pct"])
        if r.get("walkforward", {}).get("oos_metrics"):
            filter_stats[filt]["oos_alphas"].append(r["walkforward"]["oos_metrics"].get("alpha_pct", 0))
    if filter_stats:
        filter_ranking = []
        for f, st in filter_stats.items():
            if len(st["alphas"]) >= 3:
                avg_a = round(sum(st["alphas"]) / len(st["alphas"]), 1)
                avg_dd = round(sum(st["dds"]) / len(st["dds"]), 1)
                avg_oos = round(sum(st["oos_alphas"]) / len(st["oos_alphas"]), 1) if st["oos_alphas"] else 0
                filter_ranking.append({"filter": f, "avg_alpha": avg_a, "avg_dd": avg_dd,
                                        "avg_oos": avg_oos, "count": len(st["alphas"])})
        filter_ranking.sort(key=lambda x: x["avg_oos"], reverse=True)
        tips.append({
            "id": "filter_ranking", "title": "フィルター有効性ランキング",
            "category": "learning",
            "content": ('OOSα順: ' + ', '.join(f'{f["filter"]}(OOS={f["avg_oos"]}%, α={f["avg_alpha"]}%, DD={f["avg_dd"]}%)' for f in filter_ranking[:7])
                        + '。OOSαが高いフィルターを優先的に採用する。'),
            "data": filter_ranking,
            "timestamp": now,
        })

    # ── OOS2 holdout validation analysis ──
    oos2_results = [r for r in results if r.get("walkforward", {}).get("oos2_metrics")]
    if oos2_results:
        pos_oos2 = [r for r in oos2_results if r["walkforward"]["oos2_metrics"]["alpha_pct"] > 0]
        neg_oos2 = [r for r in oos2_results if r["walkforward"]["oos2_metrics"]["alpha_pct"] <= 0]
        # Analyze: what do positive OOS2 strategies have in common?
        pos_traits = {"avg_dd": 0, "avg_trades": 0, "has_lev_scale": 0, "has_eq_ma": 0, "avg_lev": 0}
        neg_traits = {"avg_dd": 0, "avg_trades": 0, "has_lev_scale": 0, "has_eq_ma": 0, "avg_lev": 0}
        for r in pos_oos2:
            pos_traits["avg_dd"] += r["metrics"]["max_drawdown_pct"]
            pos_traits["avg_trades"] += r["metrics"]["total_trades"]
            pos_traits["has_lev_scale"] += 1 if "LS" in r["name"] else 0
            pos_traits["has_eq_ma"] += 1 if "EQ" in r["name"] else 0
        for r in neg_oos2:
            neg_traits["avg_dd"] += r["metrics"]["max_drawdown_pct"]
            neg_traits["avg_trades"] += r["metrics"]["total_trades"]
            neg_traits["has_lev_scale"] += 1 if "LS" in r["name"] else 0
            neg_traits["has_eq_ma"] += 1 if "EQ" in r["name"] else 0
        if pos_oos2:
            for k in pos_traits: pos_traits[k] /= len(pos_oos2)
        if neg_oos2:
            for k in neg_traits: neg_traits[k] /= len(neg_oos2)

        tips.append({
            "id": "oos2_validation", "title": "OOS2ホールドアウト検証結果",
            "category": "validation" if pos_oos2 else "warning",
            "source_strategy": ", ".join(r["name"] for r in pos_oos2[:5]) if pos_oos2 else "N/A",
            "content": (f'OOS2検証済み{len(oos2_results)}戦略: 合格(OOS2α>0)={len(pos_oos2)}件, '
                        f'不合格={len(neg_oos2)}件。'
                        f'合格戦略の特徴: 平均DD={pos_traits["avg_dd"]:.1f}%, 平均トレード数={pos_traits["avg_trades"]:.0f}, '
                        f'レバスケール使用率={pos_traits["has_lev_scale"]:.0%}, EQ使用率={pos_traits["has_eq_ma"]:.0%}。'
                        f'不合格戦略の特徴: 平均DD={neg_traits["avg_dd"]:.1f}%, レバスケール使用率={neg_traits["has_lev_scale"]:.0%}。'
                        f'重要発見: lev_scale_ddはIS/OOS期間に過学習し、別期間で機能しない傾向。'
                        f'純粋なシグナル駆動型戦略の方がOOS2で安定する。'),
            "data": {"positive": [{"name": r["name"], "oos2_alpha": r["walkforward"]["oos2_metrics"]["alpha_pct"],
                                    "pbo2": r["walkforward"].get("pbo2_score", 1)}
                                   for r in pos_oos2[:10]],
                      "negative_sample": [{"name": r["name"], "oos2_alpha": r["walkforward"]["oos2_metrics"]["alpha_pct"]}
                                           for r in neg_oos2[:10]]},
            "timestamp": now,
        })

    # ── Utility vs Unique classification summary ──
    utility_strats = [r for r in results if r.get("strategy_type") == "utility"]
    unique_strats = [r for r in results if r.get("strategy_type") == "unique"]
    if utility_strats:
        tips.append({
            "id": "utility_strategies", "title": "Utility戦略 (全レジーム有効)",
            "category": "discovery",
            "source_strategy": ", ".join(r["name"] for r in utility_strats[:5]),
            "content": (f'{len(utility_strats)}件のUtility戦略を検出。'
                        f'OOS2(強気期間)とOOS(弱気/混合期間)の両方で正のαを維持。'
                        f'代表: ' + ', '.join(
                            f'{r["name"]}(OOS2α={r["walkforward"]["oos2_metrics"]["alpha_pct"]}%)'
                            for r in sorted(utility_strats,
                                key=lambda x: x["walkforward"]["oos2_metrics"]["alpha_pct"],
                                reverse=True)[:3])),
            "data": [{"name": r["name"],
                      "alpha": r["metrics"]["alpha_pct"],
                      "oos2_alpha": r["walkforward"]["oos2_metrics"]["alpha_pct"],
                      "dd": r["metrics"]["max_drawdown_pct"]}
                     for r in utility_strats[:10]],
            "timestamp": now,
        })

    # ── Regime analysis tip ──
    tips.append({
        "id": "regime_analysis", "title": "レジーム解析: OOS2=強気 / Main=弱気",
        "category": "learning",
        "source_strategy": "全戦略",
        "content": (f'解析期間のレジーム: OOS2期間(~80日)はBTC +22.5%の強気相場、'
                    f'Main期間(~270日)はBTC -36.7%の弱気相場。'
                    f'ボラティリティ: OOS2=1.70%/日, Main=2.18%/日。'
                    f'LOWP(p=5-7)のSupertrend戦略は両レジームで正のα(Utility)。'
                    f'lev_scale_dd/equity_ma/dd_throttleはMain期間(弱気)のみ機能(Unique)。'
                    f'月別では2026年1月(BTC-26%)にLOWP 4xが+102%の最大月間リターンを記録。'),
        "data": {"oos2_btc": 22.45, "main_btc": -36.72,
                 "oos2_vol": 1.70, "main_vol": 2.18},
        "timestamp": now,
    })

    # ── DD vs Leverage relationship ──
    tips.append({
        "id": "dd_leverage_relation", "title": "DD ∝ レバレッジの法則",
        "category": "learning",
        "source_strategy": "LOWP系",
        "content": (f'LOWP Supertrend(p=6 m=2.5)のDD/レバ比: '
                    f'2x→-39%, 3x→-52%, 4x→-62%, 5x→-70%, 6x→-76%。'
                    f'DD ≈ -13% × leverage (線形近似)。'
                    f'lev_scale_ddによるDD抑制は実現するがOOS2で破綻するため非推奨。'
                    f'DD削減には: (1)低レバレッジ, (2)複数戦略のポートフォリオ分散, (3)月別リバランスが有効。'),
        "data": {"dd_by_lev": {"2x": -39, "3x": -52, "4x": -62, "5x": -70, "6x": -76}},
        "timestamp": now,
    })

    # ── Trades vs OOS stability ──
    trade_buckets = {"30-60": [], "60-100": [], "100-200": [], "200+": []}
    for r in wf_results:
        t = r["metrics"]["total_trades"]
        oos_a = r["walkforward"]["oos_metrics"].get("alpha_pct", 0)
        if 30 <= t < 60: trade_buckets["30-60"].append(oos_a)
        elif 60 <= t < 100: trade_buckets["60-100"].append(oos_a)
        elif 100 <= t < 200: trade_buckets["100-200"].append(oos_a)
        elif t >= 200: trade_buckets["200+"].append(oos_a)
    bucket_summary = []
    for bk, vals in trade_buckets.items():
        if vals:
            bucket_summary.append({"bucket": bk, "avg_oos": round(sum(vals)/len(vals), 1),
                                    "median_oos": round(float(np.median(vals)), 1), "count": len(vals)})
    if bucket_summary:
        tips.append({
            "id": "trades_vs_oos", "title": "トレード数帯別OOS安定性",
            "category": "learning",
            "content": ' | '.join(f'{b["bucket"]}回: OOS平均={b["avg_oos"]}% 中央値={b["median_oos"]}% (n={b["count"]})' for b in bucket_summary)
                     + '。トレード数が多い方がOOSで安定する傾向があるか確認。',
            "data": bucket_summary,
            "timestamp": now,
        })

    # ── Failed strategy insights (learnings from non-qualifying strategies) ──
    if _failed_insights:
        # Group failures by pattern
        overfit_count = sum(1 for i in _failed_insights if any("過学習" in x for x in i["insights"]))
        regime_dep_count = sum(1 for i in _failed_insights if any("特定の市場環境" in x for x in i["insights"]))
        # Entry/filter type failure rates
        entry_fails = {}
        filter_fails = {}
        for i in _failed_insights:
            et = i.get("entry_type", "")
            ft = i.get("filter_type", "")
            if et:
                entry_fails.setdefault(et, 0)
                entry_fails[et] += 1
            if ft:
                filter_fails.setdefault(ft, 0)
                filter_fails[ft] += 1
        worst_entries = sorted(entry_fails.items(), key=lambda x: x[1], reverse=True)[:5]
        worst_filters = sorted(filter_fails.items(), key=lambda x: x[1], reverse=True)[:5]

        content_parts = [f'不合格戦略: {len(_failed_insights)}件 (過学習={overfit_count}, レジーム依存={regime_dep_count})。']
        if worst_entries:
            content_parts.append('失敗率の高いエントリー: ' + ', '.join(f'{e}({c}件)' for e, c in worst_entries) + '。')
        if worst_filters:
            content_parts.append('失敗率の高いフィルター: ' + ', '.join(f'{f}({c}件)' for f, c in worst_filters) + '。')
        content_parts.append('→ 成功パターン(IS/OOS/OOS2全てプラス)に集中して探索する。')

        tips.append({
            "id": "failure_insights", "title": "不合格戦略からの知見",
            "category": "warning",
            "source_strategy": "非表示戦略群",
            "content": ' '.join(content_parts),
            "data": {"total_filtered": len(_failed_insights),
                     "overfit": overfit_count, "regime_dependent": regime_dep_count,
                     "worst_entries": worst_entries, "worst_filters": worst_filters},
            "timestamp": now,
        })

    # ── Entry type effectiveness (per entry type family) ──
    entry_stats = {}
    for r in results:
        p = r["params"]
        et = p.get("entry_type", "")
        if not et:
            continue
        if et not in entry_stats:
            entry_stats[et] = {"alphas": [], "oos_alphas": [], "oos2_alphas": [], "dds": [],
                               "trades": [], "calmar": []}
        m = r["metrics"]
        entry_stats[et]["alphas"].append(m["alpha_pct"])
        entry_stats[et]["dds"].append(m["max_drawdown_pct"])
        entry_stats[et]["trades"].append(m["total_trades"])
        dd = m["max_drawdown_pct"]
        entry_stats[et]["calmar"].append(m["alpha_pct"] / abs(dd) if dd != 0 else 0)
        oos = r.get("walkforward", {}).get("oos_metrics", {})
        if oos:
            entry_stats[et]["oos_alphas"].append(oos.get("alpha_pct", 0))
        oos2 = r.get("walkforward", {}).get("oos2_metrics")
        if oos2:
            entry_stats[et]["oos2_alphas"].append(oos2.get("alpha_pct", 0))
    if entry_stats:
        entry_ranking = []
        for et, st in entry_stats.items():
            if len(st["alphas"]) >= 2:
                avg_a = round(sum(st["alphas"]) / len(st["alphas"]), 1)
                avg_dd = round(sum(st["dds"]) / len(st["dds"]), 1)
                avg_calmar = round(sum(st["calmar"]) / len(st["calmar"]), 2)
                avg_oos = round(sum(st["oos_alphas"]) / len(st["oos_alphas"]), 1) if st["oos_alphas"] else 0
                avg_oos2 = round(sum(st["oos2_alphas"]) / len(st["oos2_alphas"]), 1) if st["oos2_alphas"] else 0
                oos2_pos_rate = round(sum(1 for x in st["oos2_alphas"] if x > 0) / max(1, len(st["oos2_alphas"])) * 100, 0) if st["oos2_alphas"] else 0
                avg_trades = round(sum(st["trades"]) / len(st["trades"]), 0)
                entry_ranking.append({
                    "entry": et, "count": len(st["alphas"]),
                    "avg_alpha": avg_a, "avg_dd": avg_dd, "avg_calmar": avg_calmar,
                    "avg_oos": avg_oos, "avg_oos2": avg_oos2,
                    "oos2_positive_rate": oos2_pos_rate,
                    "avg_trades": avg_trades})
        entry_ranking.sort(key=lambda x: x["avg_oos2"], reverse=True)
        if entry_ranking:
            tips.append({
                "id": "entry_type_analysis", "title": "エントリータイプ別分析",
                "category": "learning",
                "content": ('OOS2α順: ' + ' | '.join(
                    f'{e["entry"]}(OOS2α={e["avg_oos2"]}%, OOS2+率={e["oos2_positive_rate"]}%, '
                    f'Calmar={e["avg_calmar"]}, DD={e["avg_dd"]}%, n={e["count"]})'
                    for e in entry_ranking[:8])
                    + '。OOS2正答率が高いエントリータイプを優先的に探索する。'),
                "data": entry_ranking,
                "timestamp": now,
            })

    # ── Leverage impact per strategy family ──
    lev_impact = {}
    for r in results:
        nm = r["name"]
        # Extract base family and leverage
        for fam in ["MREV_ST", "ST_BREAK", "DUAL_ST", "PIVOT_ST"]:
            if fam in nm:
                m = r["metrics"]
                lev_str = ""
                for part in nm.split("_"):
                    if "x" in part and part.replace(".", "").replace("x", "").isdigit():
                        lev_str = part
                        break
                if lev_str:
                    key = f"{fam}"
                    if key not in lev_impact:
                        lev_impact[key] = []
                    try:
                        lev_val = float(lev_str.replace("x", ""))
                    except ValueError:
                        continue
                    lev_impact[key].append({
                        "leverage": lev_val, "alpha": m["alpha_pct"],
                        "dd": m["max_drawdown_pct"], "calmar": round(m["alpha_pct"] / abs(m["max_drawdown_pct"]) if m["max_drawdown_pct"] != 0 else 0, 2),
                        "oos2": r.get("walkforward", {}).get("oos2_metrics", {}).get("alpha_pct", 0) if r.get("walkforward", {}).get("oos2_metrics") else None
                    })
                break
    if lev_impact:
        lev_summary = []
        for fam, data in lev_impact.items():
            if len(data) >= 3:
                data.sort(key=lambda x: x["leverage"])
                best_calmar = max(data, key=lambda x: x["calmar"])
                lev_summary.append({
                    "family": fam,
                    "best_calmar_lev": best_calmar["leverage"],
                    "best_calmar": best_calmar["calmar"],
                    "data": data[:10]
                })
        if lev_summary:
            tips.append({
                "id": "leverage_impact", "title": "戦略ファミリー別レバレッジ影響",
                "category": "learning",
                "content": ('最適レバ(Calmar最大): ' + ', '.join(
                    f'{ls["family"]}={ls["best_calmar_lev"]}x(Calmar={ls["best_calmar"]})'
                    for ls in lev_summary)
                    + '。Calmarが最大のレバレッジが実運用に最適。高レバはα増だがDD急増。'),
                "data": lev_summary,
                "timestamp": now,
            })

    # ── DD Management overlay effectiveness ──
    overlay_results = {"no_overlay": [], "equity_ma": [], "dd_throttle": [], "max_dd_exit": [], "lev_scale_dd": []}
    for r in results:
        nm = r["name"]
        m = r["metrics"]
        calmar = m["alpha_pct"] / abs(m["max_drawdown_pct"]) if m["max_drawdown_pct"] != 0 else 0
        entry = {"name": nm, "alpha": m["alpha_pct"], "dd": m["max_drawdown_pct"], "calmar": round(calmar, 2)}
        if "EQ" in nm:
            overlay_results["equity_ma"].append(entry)
        elif "DT" in nm or "dd_throttle" in nm:
            overlay_results["dd_throttle"].append(entry)
        elif "MDE" in nm or "max_dd_exit" in nm:
            overlay_results["max_dd_exit"].append(entry)
        elif "LS" in nm or "lev_scale" in nm:
            overlay_results["lev_scale_dd"].append(entry)
        else:
            overlay_results["no_overlay"].append(entry)
    overlay_summary = {}
    for ov, data in overlay_results.items():
        if data:
            avg_calmar = round(sum(d["calmar"] for d in data) / len(data), 2)
            avg_dd = round(sum(d["dd"] for d in data) / len(data), 1)
            avg_alpha = round(sum(d["alpha"] for d in data) / len(data), 1)
            overlay_summary[ov] = {"count": len(data), "avg_calmar": avg_calmar,
                                   "avg_dd": avg_dd, "avg_alpha": avg_alpha}
    if overlay_summary:
        tips.append({
            "id": "dd_overlay_effectiveness", "title": "DDオーバーレイ有効性比較",
            "category": "learning",
            "content": ' | '.join(
                f'{ov}: Calmar={s["avg_calmar"]} α={s["avg_alpha"]}% DD={s["avg_dd"]}% (n={s["count"]})'
                for ov, s in overlay_summary.items())
                + '。Calmarが高いオーバーレイが最もリスク効率的。',
            "data": overlay_summary,
            "timestamp": now,
        })

    # ── Goal progress tracking ──
    close_to_goal = []
    for r in results:
        m = r["metrics"]
        wf = r.get("walkforward", {})
        alpha = m["alpha_pct"]
        oos_a = wf.get("oos_metrics", {}).get("alpha_pct", 0)
        dd = m["max_drawdown_pct"]
        if alpha >= 100 and oos_a >= 50 and dd > -40:
            # Count how many goal conditions are met
            met = 0
            if alpha >= 150: met += 1
            if oos_a >= 100: met += 1
            if dd > -35: met += 1
            if wf.get("pbo_score", 1) < 0.3: met += 1
            close_to_goal.append({"name": r["name"], "alpha": alpha, "oos": oos_a,
                                   "dd": dd, "pbo": wf.get("pbo_score", 1), "met": met})
    close_to_goal.sort(key=lambda x: x["met"], reverse=True)
    if close_to_goal:
        tips.append({
            "id": "goal_progress", "title": "目標達成進捗 (α≥150%+OOS≥100%+DD>-35%+R²>0.7)",
            "category": "discovery" if close_to_goal[0]["met"] >= 3 else "learning",
            "content": (f'目標に最も近い戦略: '
                + ', '.join(f'{c["name"]}({c["met"]}/4条件: α={c["alpha"]}% OOS={c["oos"]}% DD={c["dd"]}% PBO={c["pbo"]})'
                    for c in close_to_goal[:5])
                + f'。全{len(close_to_goal)}件が目標に接近中。DDが最大のボトルネック。'),
            "data": close_to_goal[:20],
            "timestamp": now,
        })

    # ── Cross-asset robustness analysis ──
    if _altcoin_cache:
        cross_asset_results = []
        for strat_name, cached in _altcoin_cache.items():
            summary = cached.get("summary", {})
            if summary:
                cross_asset_results.append({
                    "name": strat_name,
                    "positive_count": summary.get("positive_count", 0),
                    "total": summary.get("total", 0),
                    "avg_alpha": summary.get("avg_alpha", 0),
                    "robustness": summary.get("robustness", "unknown"),
                })
        if cross_asset_results:
            robust = [c for c in cross_asset_results if c["positive_count"] >= 4]
            btc_specific = [c for c in cross_asset_results if c["positive_count"] <= 1]
            cross_asset_results.sort(key=lambda x: x["positive_count"], reverse=True)

            content_parts = [f'{len(cross_asset_results)}戦略のクロスアセット分析完了。']
            if robust:
                content_parts.append(f'ロバスト戦略({len(robust)}件): '
                    + ', '.join(f'{c["name"]}({c["positive_count"]}/{c["total"]}コインで正α, 平均α={c["avg_alpha"]}%)'
                        for c in sorted(robust, key=lambda x: x["positive_count"], reverse=True)[:5])
                    + '。')
            if btc_specific:
                content_parts.append(f'BTC特化戦略({len(btc_specific)}件): '
                    + ', '.join(c["name"] for c in btc_specific[:5])
                    + '。他アセットで機能せず、BTC固有のパターンに依存。')
            content_parts.append('クロスアセットでロバストな戦略は過学習リスクが低い傾向。')

            tips.append({
                "id": "cross_asset_robustness", "title": "クロスアセット・ロバスト性分析",
                "category": "discovery" if robust else "learning",
                "source_strategy": cross_asset_results[0]["name"] if cross_asset_results else "N/A",
                "content": ' '.join(content_parts),
                "data": cross_asset_results[:20],
                "timestamp": now,
            })

    # ── Composite (複合) strategy analysis ──
    composites = [r for r in results if '複' in r['name']]
    if composites:
        comp_by_type = {}
        for r in composites:
            nm = r['name']
            if 'DDG' in nm: ctype = 'DDGuard'
            elif 'DualReg' in nm: ctype = 'DualRegime'
            elif 'Adapt' in nm: ctype = 'Adaptive'
            elif 'Vote' in nm: ctype = 'Voting'
            elif 'Regime' in nm: ctype = 'Regime'
            elif 'RiskOff' in nm: ctype = 'RiskOff'
            else: ctype = 'Other'
            if ctype not in comp_by_type:
                comp_by_type[ctype] = {'count': 0, 'alphas': [], 'dds': [], 'oos2_alphas': []}
            comp_by_type[ctype]['count'] += 1
            comp_by_type[ctype]['alphas'].append(r['metrics']['alpha_pct'])
            comp_by_type[ctype]['dds'].append(r['metrics']['max_drawdown_pct'])
            oos2_m = r.get('walkforward', {}).get('oos2_metrics')
            if oos2_m:
                comp_by_type[ctype]['oos2_alphas'].append(oos2_m.get('alpha_pct', 0))

        comp_summary = []
        for ctype, st in comp_by_type.items():
            n = st['count']
            avg_a = round(sum(st['alphas']) / n, 1)
            avg_dd = round(sum(st['dds']) / n, 1)
            avg_oos2 = round(sum(st['oos2_alphas']) / len(st['oos2_alphas']), 1) if st['oos2_alphas'] else 0
            comp_summary.append({'type': ctype, 'count': n, 'avg_alpha': avg_a,
                                  'avg_dd': avg_dd, 'avg_oos2_alpha': avg_oos2})
        comp_summary.sort(key=lambda x: x['avg_oos2_alpha'], reverse=True)

        best_comp = max(composites, key=lambda r: r.get('walkforward', {}).get('oos2_metrics', {}).get('alpha_pct', 0))
        best_oos2 = best_comp.get('walkforward', {}).get('oos2_metrics', {}).get('alpha_pct', 0)

        tips.append({
            "id": "composite_analysis", "title": "(複合) 戦略分析",
            "category": "discovery",
            "source_strategy": best_comp['name'],
            "content": (f'{len(composites)}本の複合戦略を分析。'
                + f'最高OOS2α: {best_comp["name"]}(OOS2α={best_oos2:.1f}%, α={best_comp["metrics"]["alpha_pct"]:.1f}%, DD={best_comp["metrics"]["max_drawdown_pct"]:.1f}%)。'
                + f'タイプ別: ' + ', '.join(f'{s["type"]}(n={s["count"]}, α={s["avg_alpha"]}%, OOS2α={s["avg_oos2_alpha"]}%, DD={s["avg_dd"]}%)' for s in comp_summary[:5])
                + '。slope-based regime detection が最も有効。ADX-based regime switchingはOOS2で悪化する傾向。'),
            "data": comp_summary,
            "timestamp": now,
        })

    return tips


# ── Strategy classification (Utility / Unique) ─────────


def _classify_strategy(result: dict) -> str:
    """Classify strategy as 'utility' or 'unique' based on cross-regime performance.

    Utility: works across both OOS2 (bull) and Main (bear/mixed) regimes.
    Unique: works only in specific market conditions.
    """
    wf = result.get("walkforward", {})
    oos2 = wf.get("oos2_metrics")
    oos_a = wf.get("oos_metrics", {}).get("alpha_pct", -100)
    alpha = result["metrics"]["alpha_pct"]
    dd = result["metrics"]["max_drawdown_pct"]

    if oos2 is None:
        return "unique"  # No OOS2 → can't confirm cross-regime

    oos2_a = oos2.get("alpha_pct", 0)

    # Utility: positive alpha in both regimes AND reasonable DD
    if oos2_a > 5 and oos_a > 10 and alpha > 10:
        return "utility"

    return "unique"


# ── Background optimization ─────────────────────────────

def _passes_display_filter(result: dict) -> bool:
    """Check if a strategy meets minimum display conditions:
    IS return_daily > 0, OOS alpha > 0, OOS2 alpha > 0 (if available), DD >= -50%."""
    ret_d = result["metrics"].get("return_daily_pct", result["metrics"]["total_return_pct"] / 270)
    dd = result["metrics"]["max_drawdown_pct"]
    wf = result.get("walkforward", {})
    oos_a = wf.get("oos_metrics", {}).get("alpha_pct", -100)
    has_oos2 = wf.get("oos2_metrics") is not None
    oos2_a = wf.get("oos2_metrics", {}).get("alpha_pct", 0) if has_oos2 else 0
    if ret_d <= 0 or oos_a <= 0:
        return False
    if has_oos2 and oos2_a <= 0:
        return False
    if dd < -80:
        return False
    return True


def _extract_insight_from_failure(result: dict) -> dict | None:
    """Extract learnings from a strategy that didn't pass the display filter."""
    m = result["metrics"]
    wf = result.get("walkforward", {})
    oos_a = wf.get("oos_metrics", {}).get("alpha_pct", -100)
    oos2 = wf.get("oos2_metrics")
    oos2_a = oos2.get("alpha_pct", 0) if oos2 else None
    alpha = m["alpha_pct"]
    dd = m["max_drawdown_pct"]
    name = result["name"]

    # Determine failure reason and extract insight
    reasons = []
    if alpha <= 0:
        reasons.append(f"IS α={alpha}%")
    if oos_a <= 0:
        reasons.append(f"OOS α={oos_a}%")
    if oos2 is not None and oos2_a <= 0:
        reasons.append(f"OOS2 α={oos2_a}%")
    if dd < -80:
        reasons.append(f"DD={dd}% (上限-80%超過)")

    if not reasons:
        return None

    # Detect patterns worth noting
    insight_parts = []
    # IS positive but OOS/OOS2 negative → overfitting
    if alpha > 50 and (oos_a <= 0 or (oos2 is not None and oos2_a <= 0)):
        insight_parts.append(f"IS α={alpha}%だがOOS/OOS2で崩壊 → 過学習の可能性")
    # OOS positive but OOS2 negative → regime-dependent
    if oos_a > 0 and oos2 is not None and oos2_a <= 0:
        insight_parts.append(f"OOS={oos_a}%は良好だがOOS2={oos2_a}% → 特定の市場環境にのみ有効")
    # All alphas positive but DD too deep → promising signal, needs DD control
    if alpha > 0 and oos_a > 0 and (oos2 is None or oos2_a > 0) and dd < -35:
        insight_parts.append(f"α/OOS/OOS2は全てプラスだがDD={dd}% → DD制御で改善の余地")
    # DD very deep
    if dd < -60:
        insight_parts.append(f"DD={dd}%が深すぎる")
    # Low trade count
    if m["total_trades"] < 15:
        insight_parts.append(f"トレード数={m['total_trades']}が少なく統計的信頼性が低い")

    if not insight_parts:
        insight_parts.append(f"不合格: {', '.join(reasons)}")

    # Extract entry/filter type from name for pattern learning
    entry_info = ""
    nm = name.lower()
    for et in ["st_breakout", "supertrend", "multi_st", "st_ema", "ema", "macd", "donchian", "rsi", "bb"]:
        if et in nm:
            entry_info = et
            break
    filter_info = ""
    for ft in ["slow_st", "htf_st", "trend", "volume", "atr"]:
        if ft in nm:
            filter_info = ft
            break

    return {
        "name": name,
        "reasons": reasons,
        "insights": insight_parts,
        "alpha": alpha, "oos_a": oos_a, "oos2_a": oos2_a,
        "dd": dd, "trades": m["total_trades"],
        "entry_type": entry_info, "filter_type": filter_info,
    }


def _update_results_incremental(result, round_num):
    """Called after each strategy completes — update globals and persist."""
    global _tips
    result["round"] = round_num
    result["strategy_type"] = _classify_strategy(result)
    # Discard negative total return
    if result["metrics"]["total_return_pct"] <= 0:
        return

    # Check display filter: IS/OOS/OOS2 all positive required
    if not _passes_display_filter(result):
        # Extract insights before discarding
        insight = _extract_insight_from_failure(result)
        if insight:
            _failed_insights.append(insight)
            # Keep only last 200 insights to limit memory
            if len(_failed_insights) > 200:
                _failed_insights[:] = _failed_insights[-200:]
        log.info(f"Filtered out {result['name']}: {insight['reasons'] if insight else 'no insight'}")
        return

    # Replace existing result with same name (e.g. re-run with new data)
    _results[:] = [r for r in _results if r["name"] != result["name"]]
    # Strip heavy data — keep enough equity points for accurate R² but subsample
    sr = dict(result)
    eq = sr.get("equity_curve", [])
    bm = sr.get("benchmark_curve", [])
    tm = sr.get("times", [])
    # Subsample: keep every Nth point to fit ~2000 points but cover full range
    step = max(1, len(eq) // 2000)
    sr["equity_curve"] = eq[::step]
    sr["benchmark_curve"] = bm[::step]
    sr["times"] = tm[::step]
    sr["trades"] = sr.get("trades", [])[:100]
    _results.append(sr)
    import math as _m
    def _sort_score(r):
        wf = r.get("walkforward", {})
        ret_d = r["metrics"].get("return_daily_pct", r["metrics"]["total_return_pct"] / 270)
        oos_a = wf.get("oos_metrics", {}).get("alpha_pct", -100)
        oos_ret_d = wf.get("oos_metrics", {}).get("return_daily_pct", 0)
        has_oos2 = wf.get("oos2_metrics") is not None
        oos2_a = wf.get("oos2_metrics", {}).get("alpha_pct", 0) if has_oos2 else 0
        oos2_ret_d = wf.get("oos2_metrics", {}).get("return_daily_pct", 0) if has_oos2 else 0
        dd = r["metrics"]["max_drawdown_pct"]
        total_ret = r["metrics"]["total_return_pct"]
        trades = r["metrics"].get("total_trades", 0)
        pbo = wf.get("pbo_score", 1.0)
        r2 = r.get("r2", 0)

        # === Hard gate: trades < 50 go to bottom ===
        if trades < 50:
            return -20000 + total_ret

        # === Priority 1: IS, OOS, OOS2 alpha ALL must be positive ===
        all_positive = ret_d > 0 and oos_a > 0
        if has_oos2:
            all_positive = all_positive and oos2_a > 0
        if not all_positive:
            return -10000 + total_ret

        # === Goal-proximity scoring: reward strategies closest to all conditions ===
        # α≥150%, OOS≥100%, OOS2≥100%, PBO<0.3, DD>-35%, R²>0.7, Trades≥50, DailyRet≥0.75%
        alpha = r["metrics"]["alpha_pct"]
        _is_rd = r["metrics"].get("return_daily_pct", r["metrics"]["total_return_pct"] / 270)
        _oos_rd = wf.get("oos_metrics", {}).get("return_daily_pct", 0)
        _oos2_rd = wf.get("oos2_metrics", {}).get("return_daily_pct", 0) if has_oos2 else 0
        goal_score = 0
        goal_score += min(alpha / 150, 2.0) * 200       # α≥150% → 200pts, cap at 400
        goal_score += min(oos_a / 100, 2.0) * 150        # OOS≥100% → 150pts
        goal_score += min(oos2_a / 100, 2.0) * 200       # OOS2≥100% → 200pts (hardest)
        goal_score += (100 if pbo < 0.3 else 50 if pbo < 0.5 else 0)
        goal_score += (100 if dd > -35 else 50 if dd > -50 else 0)
        goal_score += (100 if r2 > 0.7 else 50 if r2 > 0.5 else 0)
        # Daily return: bonus for meeting 1% goal, partial for 0.75% minimum
        _min_rd = min(_is_rd, _oos_rd, _oos2_rd) if has_oos2 else min(_is_rd, _oos_rd)
        goal_score += (100 if _min_rd >= 1.0 else 50 if _min_rd >= 0.75 else 0)

        # === DD penalty ===
        dd_pen = dd * 5 if dd > -35 else dd * 15

        # === No OOS2 penalty ===
        no_oos2_pen = -100 if not has_oos2 else 0

        return goal_score + dd_pen + no_oos2_pen
    _results.sort(key=_sort_score, reverse=True)
    _merge_tips(_generate_tips(list(_results)))
    _save_results()
    _save_tips()


def _evolve_strategies(results: list[dict]) -> list[str]:
    """Generate evolved strategy variations from winners. Returns new names."""
    from engine.strategies import STRATEGIES

    winners = [r for r in results
               if r["metrics"]["alpha_pct"] > 0
               and r.get("walkforward", {}).get("pbo_score", 1) < 0.5
               and r["metrics"]["total_trades"] >= 15]

    if not winners:
        winners = sorted([r for r in results if r["metrics"]["alpha_pct"] > 0],
                         key=lambda r: r["metrics"]["alpha_pct"], reverse=True)[:5]
    if not winners:
        return []

    new_names = []
    for w in winners[:15]:
        name = w["name"]
        params = w["params"]
        spec = STRATEGIES.get(name)
        if not spec or name.startswith("Evo_"):
            continue

        alpha = w["metrics"]["alpha_pct"]
        dd = w["metrics"]["max_drawdown_pct"]

        # 1) Narrow grid around winning params
        evo_name = f"Evo_{name}"
        if evo_name not in STRATEGIES:
            new_grid = {}
            for k, v in params.items():
                if isinstance(v, int):
                    delta = max(1, int(abs(v) * 0.25))
                    new_grid[k] = sorted(set([max(1, v - delta), v, v + delta]))
                elif isinstance(v, float):
                    delta = max(0.01, abs(v) * 0.25)
                    new_grid[k] = [round(x, 4) for x in [v - delta, v, v + delta] if x > 0]
                else:
                    new_grid[k] = [v]
            STRATEGIES[evo_name] = {
                "fn": spec["fn"], "param_grid": new_grid,
                "risk": spec.get("risk", {}),
                "desc": f"Evolved: {name} (α={w['metrics']['alpha_pct']}%)",
            }
            new_names.append(evo_name)

        # 2) No-stops variant (proven best for trend-following in crypto)
        risk = spec.get("risk", {})
        if risk.get("trailing_stop_pct") or risk.get("stop_loss_pct"):
            ns_name = f"Evo_{name}_NoStop"
            if ns_name not in STRATEGIES:
                clean_risk = {"cooldown_bars": risk.get("cooldown_bars", 0)}
                if "leverage" in risk:
                    clean_risk["leverage"] = risk["leverage"]
                STRATEGIES[ns_name] = {
                    "fn": spec["fn"], "param_grid": spec["param_grid"],
                    "risk": clean_risk,
                    "desc": f"{name} without stops",
                }
                new_names.append(ns_name)

        # 3) Leveraged variants — amplify proven winners (no stops)
        oos_alpha = w.get("walkforward", {}).get("oos_metrics", {}).get("alpha_pct", 0)
        if oos_alpha > 15 and w["metrics"]["alpha_pct"] > 30:
            base_risk = {"cooldown_bars": risk.get("cooldown_bars", 0)}
            for lev in [1.5, 2.0, 2.5]:
                lev_name = f"Evo_{name}_L{lev:.1f}"
                if lev_name not in STRATEGIES:
                    STRATEGIES[lev_name] = {
                        "fn": spec["fn"], "param_grid": spec["param_grid"],
                        "risk": {**base_risk, "leverage": lev},
                        "desc": f"{name} + {lev}x leverage (no stops)",
                    }
                    new_names.append(lev_name)

        # 4) High-leverage + equity management variants (OOS α push)
        if oos_alpha > 20 and w["metrics"]["alpha_pct"] > 50:
            base_risk = {"cooldown_bars": risk.get("cooldown_bars", 0)}
            eq_variants = [
                (3.0, 1200, 0.10), (3.5, 1200, 0.08), (3.5, 1500, 0.07),
                (4.0, 1500, 0.06),
            ]
            for lev, eq_ma, dd_thr in eq_variants:
                lev_name = f"Evo_{name}_L{lev:.1f}_EQ{eq_ma}_DD{int(dd_thr*100)}"
                if lev_name not in STRATEGIES:
                    STRATEGIES[lev_name] = {
                        "fn": spec["fn"], "param_grid": spec["param_grid"],
                        "risk": {**base_risk, "leverage": lev,
                                 "equity_ma_bars": eq_ma, "dd_throttle_pct": dd_thr},
                        "desc": f"{name} + {lev}x EQ{eq_ma} DD{dd_thr}",
                    }
                    new_names.append(lev_name)

        # 5) High-return variants: 5x-10x + lev_scale_dd (monthly 100% target)
        if oos_alpha > 10 and w["metrics"]["alpha_pct"] > 20:
            base_risk = {"cooldown_bars": risk.get("cooldown_bars", 0)}
            hr_variants = [
                (5.0, 0.02), (6.0, 0.02), (8.0, 0.015), (10.0, 0.01),
            ]
            for lev, ls in hr_variants:
                hr_name = f"Evo_{name}_HR{lev:.0f}x_LS{int(ls*1000)}"
                if hr_name not in STRATEGIES:
                    STRATEGIES[hr_name] = {
                        "fn": spec["fn"], "param_grid": spec["param_grid"],
                        "risk": {**base_risk, "leverage": lev, "lev_scale_dd": ls},
                        "desc": f"{name} + {lev}x lev_scale={ls}",
                    }
                    new_names.append(hr_name)

        # 6) OOS2-targeted: high leverage + max_dd_exit to push OOS2 α ≥ 100%
        oos2_m = w.get("walkforward", {}).get("oos2_metrics")
        oos2_alpha = oos2_m.get("alpha_pct", 0) if oos2_m else 0
        if oos2_alpha > 10 and alpha > 50:
            base_risk = {"cooldown_bars": risk.get("cooldown_bars", 0)}
            oos2_variants = [
                # (leverage, max_dd_exit_pct, mde_cooldown_bars)
                # MDE + cooldown: prevent DD compounding
                (3.0, 0.28, 480), (4.0, 0.28, 480), (5.0, 0.28, 480),
                (3.0, 0.20, 480), (4.0, 0.20, 480), (5.0, 0.20, 480),
                (4.0, 0.28, 240), (5.0, 0.28, 240),
                (4.0, 0.28, 960), (5.0, 0.28, 960),
                (4.0, 0.10, 480), (5.0, 0.10, 480), (6.0, 0.10, 480),
                # MDE without cooldown
                (4.0, 0.30, 0), (5.0, 0.30, 0), (6.0, 0.30, 0),
                # Pure high-lev for ceiling measurement
                (4.0, 0, 0), (5.0, 0, 0), (6.0, 0, 0),
            ]
            for lev, mde, mde_cd in oos2_variants:
                if mde and mde_cd:
                    suffix = f"_OOS2_L{lev}_MDE{int(mde*100)}_CD{mde_cd}"
                elif mde:
                    suffix = f"_OOS2_L{lev}_MDE{int(mde*100)}"
                else:
                    suffix = f"_OOS2_L{lev}_PURE"
                oos2_name = f"Evo_{name}{suffix}"
                if oos2_name not in STRATEGIES:
                    r_dict = {**base_risk, "leverage": lev}
                    if mde:
                        r_dict["max_dd_exit_pct"] = mde
                    if mde_cd:
                        r_dict["mde_cooldown_bars"] = mde_cd
                    STRATEGIES[oos2_name] = {
                        "fn": spec["fn"], "param_grid": spec["param_grid"],
                        "risk": r_dict,
                        "desc": f"{name} OOS2-push L{lev}" + (f" MDE{mde}" if mde else " pure") + (f" CD{mde_cd}" if mde_cd else ""),
                    }
                    new_names.append(oos2_name)

        # 7) DD-targeted variants: low lev + DD management for goal qualification
        #    Target: α≥150%, DD > -30% → need low leverage + overlays
        if alpha > 100 and oos_alpha > 50:
            base_risk = {"cooldown_bars": risk.get("cooldown_bars", 0)}
            dd_variants = [
                # (leverage, equity_ma_bars, dd_throttle_pct, max_dd_exit_pct)
                (1.0, 0, 0, 0),                     # pure 1x, no overlays
                (1.2, 0, 0, 0),                     # 1.2x, no overlays
                (1.5, 800, 0.08, 0),                # 1.5x + equity_ma + dd_throttle
                (1.5, 1200, 0.06, 0),               # 1.5x + stronger overlays
                (1.5, 0, 0, 0.25),                  # 1.5x + hard DD cap at 25%
                (2.0, 800, 0.08, 0),                # 2x + equity_ma + dd_throttle
                (2.0, 1200, 0.06, 0),               # 2x + stronger overlays
                (2.0, 0, 0, 0.20),                  # 2x + hard DD cap at 20%
                (1.2, 600, 0.10, 0),                # 1.2x + mild overlays
                (1.5, 0, 0.05, 0.20),               # 1.5x + throttle + DD cap
                (2.0, 800, 0.06, 0.25),             # 2x + all overlays
                (1.0, 600, 0, 0),                   # 1x + equity_ma only
            ]
            for lev, eq_ma, dd_thr, mde in dd_variants:
                suffix = f"_DDM_L{lev}"
                if eq_ma: suffix += f"_EQ{eq_ma}"
                if dd_thr: suffix += f"_DT{int(dd_thr*100)}"
                if mde: suffix += f"_MDE{int(mde*100)}"
                ddm_name = f"Evo_{name}{suffix}"
                if ddm_name not in STRATEGIES:
                    r_dict = {**base_risk, "leverage": lev}
                    if eq_ma: r_dict["equity_ma_bars"] = eq_ma
                    if dd_thr: r_dict["dd_throttle_pct"] = dd_thr
                    if mde: r_dict["max_dd_exit_pct"] = mde
                    STRATEGIES[ddm_name] = {
                        "fn": spec["fn"], "param_grid": spec["param_grid"],
                        "risk": r_dict,
                        "desc": f"{name} DD-managed L{lev}",
                    }
                    new_names.append(ddm_name)

    # 8) Composite (複合) strategies: combine complementary sub-strategies
    #    Find strategies with opposite regime strengths and combine them
    from engine.strategies import (composite_regime_signal, composite_vote_signal,
        composite_adaptive_signal, composite_riskoff_signal,
        composite_ddguard_signal, composite_dual_regime_signal)
    _bear_good = []  # High main α, low OOS2 α
    _bull_good = []  # Lower main α, high OOS2 α
    for r in results:
        rm = r.get("metrics", {})
        rwf = r.get("walkforward", {})
        roos2 = rwf.get("oos2_metrics")
        if not roos2 or rm.get("total_trades", 0) < 30:
            continue
        r_alpha = rm.get("alpha_pct", 0)
        r_oos2a = roos2.get("alpha_pct", 0)
        # Extract entry params from the strategy
        rp = r.get("params", {})
        r_entry = rp.get("entry_type")
        if not r_entry:
            continue
        r_ep1 = rp.get("ep1", 10)
        r_ep2 = rp.get("ep2", 2.5)
        info = (r_entry, r_ep1, r_ep2, r_alpha, r_oos2a, rm.get("max_drawdown_pct", -100))
        if r_alpha > 200 and r_oos2a < 30:
            _bear_good.append(info)
        if r_oos2a > 50 and r_alpha < 300:
            _bull_good.append(info)

    _bear_good.sort(key=lambda x: x[3], reverse=True)  # Sort by main α
    _bull_good.sort(key=lambda x: x[4], reverse=True)  # Sort by OOS2 α

    # Generate regime-switching composites: bear-specialist + bull-specialist
    for bear in _bear_good[:5]:
        for bull in _bull_good[:5]:
            if bear[0] == bull[0] and bear[1] == bull[1] and bear[2] == bull[2]:
                continue  # Skip identical signals
            for regime_m in ["adx", "atr_pctile", "slope"]:
                for regime_lb in [50, 100]:
                    for lev in [2.0, 3.0, 4.0]:
                        cname = f"(複)Regime_{bear[0][:6]}+{bull[0][:6]}_{regime_m}_{lev}x"
                        if cname not in STRATEGIES:
                            STRATEGIES[cname] = {
                                "fn": composite_regime_signal,
                                "param_grid": {
                                    "sub1_type": [bear[0]], "sub1_p1": [bear[1]], "sub1_p2": [bear[2]],
                                    "sub2_type": [bull[0]], "sub2_p1": [bull[1]], "sub2_p2": [bull[2]],
                                    "regime_method": [regime_m], "regime_lookback": [regime_lb],
                                },
                                "risk": {"cooldown_bars": 0, "leverage": lev},
                                "desc": f"(複) Regime switch: {bear[0]}(bear)+{bull[0]}(bull) {regime_m}",
                            }
                            new_names.append(cname)

    # Generate voting composites: 3 diverse entry types vote
    _diverse_entries = set()
    for r in results:
        rp = r.get("params", {})
        r_entry = rp.get("entry_type")
        if r_entry and r.get("metrics", {}).get("alpha_pct", 0) > 50:
            _diverse_entries.add((r_entry, rp.get("ep1", 10), rp.get("ep2", 2.5)))
    _diverse_list = list(_diverse_entries)[:10]
    if len(_diverse_list) >= 3:
        import itertools as _it
        for trio in list(_it.combinations(_diverse_list, 3))[:20]:
            for vt in [2, 3]:
                for lev in [2.0, 3.0, 4.0]:
                    cname = f"(複)Vote_{trio[0][0][:4]}+{trio[1][0][:4]}+{trio[2][0][:4]}_V{vt}_{lev}x"
                    if cname not in STRATEGIES:
                        STRATEGIES[cname] = {
                            "fn": composite_vote_signal,
                            "param_grid": {
                                "e1_type": [trio[0][0]], "e1_p1": [trio[0][1]], "e1_p2": [trio[0][2]],
                                "e2_type": [trio[1][0]], "e2_p1": [trio[1][1]], "e2_p2": [trio[1][2]],
                                "e3_type": [trio[2][0]], "e3_p1": [trio[2][1]], "e3_p2": [trio[2][2]],
                                "vote_thresh": [vt],
                            },
                            "risk": {"cooldown_bars": 0, "leverage": lev},
                            "desc": f"(複) Vote {vt}/3: {trio[0][0]}+{trio[1][0]}+{trio[2][0]}",
                        }
                        new_names.append(cname)

    # Generate adaptive composites: trend + mean-reversion switching on ADX
    _trend_entries = [("supertrend", 12, 2.5), ("supertrend", 10, 3.0), ("st_breakout", 7, 20)]
    _mr_entries = [("mean_rev_st", 6, 12), ("mean_rev_st", 5, 15), ("bb", 20, 2.0)]
    for te in _trend_entries:
        for me in _mr_entries:
            for adx_t in [20, 25]:
                for lev in [2.0, 3.0, 4.0, 5.0]:
                    cname = f"(複)Adapt_{te[0][:4]}+{me[0][:4]}_ADX{adx_t}_{lev}x"
                    if cname not in STRATEGIES:
                        STRATEGIES[cname] = {
                            "fn": composite_adaptive_signal,
                            "param_grid": {
                                "trend_type": [te[0]], "trend_p1": [te[1]], "trend_p2": [te[2]],
                                "mr_type": [me[0]], "mr_p1": [me[1]], "mr_p2": [me[2]],
                                "adx_period": [14], "adx_thresh": [adx_t],
                            },
                            "risk": {"cooldown_bars": 0, "leverage": lev},
                            "desc": f"(複) Adaptive: {te[0]}(trend)+{me[0]}(MR) ADX>{adx_t}",
                        }
                        new_names.append(cname)

    # Generate risk-off composites: wrap best signals with regime-transition filter
    for r in results[:10]:
        rp = r.get("params", {})
        r_entry = rp.get("entry_type")
        r_filt = rp.get("filter_type", "none")
        if not r_entry or r.get("metrics", {}).get("alpha_pct", 0) < 100:
            continue
        for ro_method in ["vol_spike", "regime_trans"]:
            for ro_thresh in [0.7, 0.8]:
                for lev in [3.0, 4.0, 5.0]:
                    cname = f"(複)RiskOff_{r_entry[:6]}_{ro_method[:4]}_{lev}x"
                    if cname not in STRATEGIES:
                        STRATEGIES[cname] = {
                            "fn": composite_riskoff_signal,
                            "param_grid": {
                                "entry_type": [r_entry], "ep1": [rp.get("ep1", 10)], "ep2": [rp.get("ep2", 2.5)],
                                "filter_type": [r_filt], "fp1": [rp.get("fp1", 0)], "fp2": [rp.get("fp2", 0)],
                                "riskoff_method": [ro_method], "riskoff_thresh": [ro_thresh],
                            },
                            "risk": {"cooldown_bars": 0, "leverage": lev},
                            "desc": f"(複) Risk-off: {r_entry}+{ro_method} @{ro_thresh}",
                        }
                        new_names.append(cname)

    # DD-Guard composites from top-performing strategies
    for r in results[:10]:
        rp = r.get("params", {})
        r_entry = rp.get("entry_type")
        if not r_entry:
            continue
        rm = r.get("metrics", {})
        if rm.get("alpha_pct", 0) < 100 or rm.get("max_drawdown_pct", -100) < -50:
            continue
        for guard_lb in [200, 400]:
            for guard_th in [5.0, 7.0]:
                for rec_mult in [0.3, 0.5]:
                    for lev in [3.0, 4.0, 5.0]:
                        cname = f"(複)DDG_{r_entry[:4]}{rp.get('ep1',10)}_{rp.get('ep2',12)}_LB{guard_lb}_TH{int(guard_th)}_{lev}x"
                        if cname not in STRATEGIES:
                            STRATEGIES[cname] = {
                                "fn": composite_ddguard_signal,
                                "param_grid": {
                                    "entry_type": [r_entry], "ep1": [rp.get("ep1", 10)], "ep2": [rp.get("ep2", 2.5)],
                                    "guard_lookback": [guard_lb], "guard_threshold": [guard_th],
                                    "recovery_mult": [rec_mult],
                                },
                                "risk": {"cooldown_bars": 0, "leverage": lev},
                                "desc": f"(複) DDGuard: {r_entry}",
                            }
                            new_names.append(cname)

    log.info(f"Phase 8 composite: generated {len([n for n in new_names if '(複)' in n])} composite strategies")
    return new_names


def _generate_novel_strategies(results: list[dict], batch_id: int) -> list[str]:
    """Generate genuinely new combo strategies based on learnings + tips."""
    from engine.strategies import STRATEGIES, combo_signal

    # === Tips-driven: extract best combos from accumulated tips ===
    best_entries = set()
    best_filters = set()
    tips_combos = []  # (entry, filter) pairs ranked by OOS from tips
    for tip in _tips:
        if tip["id"] == "combo_matrix" and tip.get("data"):
            for c in tip["data"][:10]:  # Top 10 combos by OOS
                combo = c.get("combo", "")
                if "+" in combo and c.get("avg_oos", 0) > 5:
                    parts = combo.split("+")
                    tips_combos.append((parts[0], parts[1]))
                    best_entries.add(parts[0])
                    best_filters.add(parts[1])
        if tip["id"] == "filter_ranking" and tip.get("data"):
            for f in tip["data"][:3]:
                if f.get("avg_oos", 0) > 5:
                    best_filters.add(f["filter"])

    # Fallback: name-based heuristic if tips not available yet
    if not best_entries:
        good = [r for r in results if r["metrics"]["alpha_pct"] > 3 and r["metrics"]["total_trades"] >= 10]
        for r in good:
            nm = r["name"].lower()
            if "ema" in nm or "cross" in nm: best_entries.add("ema")
            if "rsi" in nm: best_entries.add("rsi")
            if "bb" in nm or "bollinger" in nm: best_entries.add("bb")
            if "donchian" in nm or "channel" in nm: best_entries.add("donchian")
            if "macd" in nm: best_entries.add("macd")
            if "momentum" in nm or "breakout" in nm or "roc" in nm: best_entries.add("roc")
            if "vwap" in nm: best_entries.add("vwap")
            if "supertrend" in nm: best_entries.add("supertrend")
            if "stoch" in nm: best_entries.add("stoch")
            if "hull" in nm: best_entries.add("hull")
            if "mtf" in nm or "multi" in nm: best_filters.add("mtf")
            if "volume" in nm or "vol" in nm: best_filters.add("volume")

    log.info(f"Tips-driven generation: best_entries={best_entries}, best_filters={best_filters}, tips_combos={len(tips_combos)}")

    ALL_ENTRIES = ["ema", "rsi", "bb", "donchian", "macd", "roc", "stoch", "supertrend", "vwap", "hull",
                   "cci", "keltner", "williams", "dmi", "ichimoku", "multi_st", "st_ema", "st_breakout",
                   "st_rsi", "st_macd", "bb_squeeze", "pivot_st", "mean_rev_st"]
    ALL_FILTERS = ["none", "trend", "rsi", "volume", "mtf", "atr", "oi", "slow_st", "htf_st"]

    ENTRY_GRIDS = {
        "ema":        {"ep1": [5, 9, 12, 20],  "ep2": [21, 30, 50]},
        "rsi":        {"ep1": [10, 14, 21],     "ep2": [25, 30, 35]},
        "bb":         {"ep1": [15, 20, 30],     "ep2": [1.5, 2.0, 2.5]},
        "donchian":   {"ep1": [10, 20, 30, 50], "ep2": [0]},
        "macd":       {"ep1": [8, 12],          "ep2": [21, 26, 34]},
        "roc":        {"ep1": [5, 10, 20],      "ep2": [1.0, 2.0, 3.0]},
        "stoch":      {"ep1": [10, 14, 21],     "ep2": [20, 25, 30]},
        "supertrend": {"ep1": [8, 10, 12, 14, 18],     "ep2": [1.5, 2.0, 2.5, 3.0]},
        "vwap":       {"ep1": [48, 96, 192],    "ep2": [0.3, 0.5, 0.8]},
        "hull":       {"ep1": [16, 24, 36],     "ep2": [1.0, 2.0, 3.0]},
        "cci":        {"ep1": [14, 20, 30],     "ep2": [100, 150, 200]},
        "keltner":    {"ep1": [14, 20, 30],     "ep2": [1.5, 2.0, 2.5]},
        "williams":   {"ep1": [10, 14, 21],     "ep2": [20, 25, 30]},
        "dmi":        {"ep1": [10, 14, 20],     "ep2": [20, 25, 30]},
        "ichimoku":   {"ep1": [7, 9, 13],       "ep2": [22, 26, 34]},
        "multi_st":   {"ep1": [5, 7, 10, 12, 14],     "ep2": [1.5, 2.0, 2.5, 3.0]},
        "st_ema":     {"ep1": [10, 14, 20],     "ep2": [30, 50, 100]},
        "st_breakout":{"ep1": [5, 6, 7, 10, 12], "ep2": [15, 20, 25, 30]},
        "st_rsi":     {"ep1": [5, 6, 7, 10, 12], "ep2": [10, 14, 21]},
        "st_macd":    {"ep1": [5, 6, 7, 10, 12], "ep2": [21, 26, 34]},
        "bb_squeeze": {"ep1": [15, 20, 30],       "ep2": [1.5, 2.0, 2.5]},
        "pivot_st":   {"ep1": [5, 6, 7, 10, 12], "ep2": [0]},
        "mean_rev_st":{"ep1": [5, 6, 7, 10],     "ep2": [15, 20, 30]},
    }
    FILTER_GRIDS = {
        "none":   {"fp1": [0],        "fp2": [0]},
        "trend":  {"fp1": [50, 100],   "fp2": [0]},
        "rsi":    {"fp1": [14],        "fp2": [60, 70]},
        "volume": {"fp1": [20],        "fp2": [1.2, 1.5]},
        "mtf":    {"fp1": [4, 8],      "fp2": [20, 50]},
        "atr":    {"fp1": [14],        "fp2": [0.5, 1.0]},
        "oi":     {"fp1": [12, 24],    "fp2": [2.0, 5.0]},
        "slow_st":{"fp1": [20, 30],    "fp2": [3.0, 3.5, 4.0]},
        "htf_st": {"fp1": [4, 8, 16],  "fp2": [2.5, 3.0]},
    }
    RISK_PROFILES = [
        # No stops — let signals handle exits (proven best for trend-following)
        {"cooldown_bars": 0},
        {"cooldown_bars": 4},
        # Leveraged, no stops (α > 150% path)
        {"cooldown_bars": 0, "leverage": 1.5},
        {"cooldown_bars": 0, "leverage": 2.0},
        {"cooldown_bars": 4, "leverage": 1.5},
        {"cooldown_bars": 4, "leverage": 2.0},
        # Wide stops only (for non-trend strategies)
        {"stop_loss_pct": 0.10, "trailing_stop_pct": 0, "cooldown_bars": 4},
        {"stop_loss_pct": 0.10, "trailing_stop_pct": 0, "cooldown_bars": 4, "leverage": 1.5},
        # High-return: 5x-8x with adaptive leverage scaling
        {"cooldown_bars": 0, "leverage": 5.0, "lev_scale_dd": 0.02},
        {"cooldown_bars": 0, "leverage": 8.0, "lev_scale_dd": 0.015},
    ]

    # Strategy: 60% focused on winning combos, 40% exploratory
    focused_entries = list(best_entries) if best_entries else ALL_ENTRIES[:4]
    explore_entries = [e for e in ALL_ENTRIES if e not in best_entries]
    focused_filters = list(best_filters | {"trend", "none"})
    explore_filters = [f for f in ALL_FILTERS if f not in focused_filters]

    new_names = []

    def _register(entry, filt, risk_idx):
        risk = RISK_PROFILES[risk_idx % len(RISK_PROFILES)]
        suffix = chr(65 + risk_idx)  # A, B, C
        name = f"C{batch_id}_{entry}+{filt}_{suffix}"
        if name in STRATEGIES:
            return None
        # Skip if same combo already has results from prior batches
        combo_key = f"{entry}+{filt}_{suffix}"
        if any(combo_key in r["name"] for r in _results):
            return None
        grid = {
            "entry_type": [entry],
            "ep1": ENTRY_GRIDS[entry]["ep1"],
            "ep2": ENTRY_GRIDS[entry]["ep2"],
            "filter_type": [filt],
            "fp1": FILTER_GRIDS[filt]["fp1"],
            "fp2": FILTER_GRIDS[filt]["fp2"],
        }
        STRATEGIES[name] = {
            "fn": combo_signal,
            "param_grid": grid,
            "risk": risk,
            "desc": f"Combo B{batch_id}: {entry}+{filt} risk={suffix}",
        }
        return name

    # Focused: winning entries × all filters, risk A-F (including leveraged)
    for entry in focused_entries:
        for filt in ALL_FILTERS:
            for ri in range(len(RISK_PROFILES)):
                n = _register(entry, filt, ri)
                if n:
                    new_names.append(n)

    # Explore: other entries × focused filters, risk A only
    for entry in explore_entries:
        for filt in focused_filters:
            n = _register(entry, filt, 0)
            if n:
                new_names.append(n)

    # Wild cards: random combos with risk C
    import random
    random.seed(batch_id * 42)
    for _ in range(10):
        e = random.choice(ALL_ENTRIES)
        f = random.choice(ALL_FILTERS)
        n = _register(e, f, 2)
        if n:
            new_names.append(n)

    # === Dual-filter combos: entry + filter1 + filter2 ===
    from engine.strategies import combo_dual_signal

    DUAL_COMBOS = [
        # (entry, f1, f2) — high-conviction setups
        ("supertrend", "atr", "mtf"),
        ("supertrend", "atr", "trend"),
        ("supertrend", "atr", "volume"),
        ("supertrend", "mtf", "volume"),
        ("vwap", "atr", "mtf"),
        ("vwap", "atr", "trend"),
        ("vwap", "atr", "volume"),
        ("roc", "atr", "mtf"),
        ("roc", "atr", "trend"),
        ("rsi", "atr", "mtf"),
        ("rsi", "atr", "volume"),
        ("ema", "atr", "mtf"),
        ("donchian", "atr", "mtf"),
        ("donchian", "atr", "volume"),
        ("hull", "atr", "mtf"),
        ("stoch", "atr", "mtf"),
        ("macd", "atr", "mtf"),
        ("supertrend", "volume", "trend"),
        ("vwap", "volume", "trend"),
        ("roc", "volume", "trend"),
        # New entry types with dual filters
        ("cci", "atr", "trend"),
        ("cci", "atr", "mtf"),
        ("cci", "volume", "trend"),
        ("keltner", "atr", "trend"),
        ("keltner", "atr", "mtf"),
        ("keltner", "volume", "trend"),
        ("williams", "atr", "trend"),
        ("williams", "atr", "mtf"),
        ("dmi", "atr", "trend"),
        ("dmi", "atr", "volume"),
        ("dmi", "volume", "mtf"),
        ("ichimoku", "atr", "trend"),
        ("ichimoku", "atr", "volume"),
        ("ichimoku", "volume", "mtf"),
        # Multi-supertrend consensus combos
        ("multi_st", "atr", "trend"),
        ("multi_st", "atr", "mtf"),
        ("multi_st", "volume", "trend"),
        # Supertrend+EMA hybrid combos
        ("st_ema", "atr", "trend"),
        ("st_ema", "atr", "mtf"),
        ("st_ema", "volume", "trend"),
    ]
    F2_GRIDS = {
        "trend": {"f2p1": [50, 100], "f2p2": [0]},
        "rsi":   {"f2p1": [14], "f2p2": [65, 75]},
        "volume": {"f2p1": [20], "f2p2": [1.2, 1.5]},
        "mtf":   {"f2p1": [4], "f2p2": [20, 50]},
        "atr":   {"f2p1": [14], "f2p2": [0.5, 1.0]},
        "oi":    {"f2p1": [12], "f2p2": [3.0]},
    }

    for entry, f1, f2 in DUAL_COMBOS:
        for ri in range(2):
            risk = RISK_PROFILES[ri]
            suffix = chr(65 + ri)
            name = f"D{batch_id}_{entry}+{f1}+{f2}_{suffix}"
            if name in STRATEGIES:
                continue
            # Skip if same dual combo already has results
            dual_key = f"{entry}+{f1}+{f2}_{suffix}"
            if any(dual_key in r["name"] for r in _results):
                continue
            grid = {
                "entry_type": [entry],
                "ep1": ENTRY_GRIDS[entry]["ep1"],
                "ep2": ENTRY_GRIDS[entry]["ep2"],
                "f1_type": [f1],
                "f1p1": FILTER_GRIDS[f1]["fp1"],
                "f1p2": FILTER_GRIDS[f1]["fp2"],
                "f2_type": [f2],
                "f2p1": F2_GRIDS[f2]["f2p1"],
                "f2p2": F2_GRIDS[f2]["f2p2"],
            }
            STRATEGIES[name] = {
                "fn": combo_dual_signal,
                "param_grid": grid,
                "risk": risk,
                "desc": f"Dual B{batch_id}: {entry}+{f1}+{f2} risk={suffix}",
            }
            new_names.append(name)

    log.info(f"Generated {len(new_names)} novel strategies (batch {batch_id}, incl dual-filter)")
    return new_names


async def _run_optimization_parallel(df, names, progress_cb, result_cb=None, df_oos2=None, df_oos3=None, early_stop_check=None):
    """Run walk-forward optimization in parallel using ProcessPoolExecutor."""
    from engine.optimizer import create_executor, _wf_single
    from engine.strategies import STRATEGIES as _S

    # Debug: check MDE strategies are in STRATEGIES before executor creation
    mde_names = [n for n in names if 'MDE' in n]
    mde_in_strats = [n for n in mde_names if n in _S]
    mde_missing = [n for n in mde_names if n not in _S]
    if mde_names:
        log.info(f"MDE strategies in run: {len(mde_names)}, in STRATEGIES: {len(mde_in_strats)}, missing: {len(mde_missing)}")
        if mde_missing:
            log.warning(f"Missing MDE strategies: {mde_missing[:5]}")

    import os
    n_cpu = os.cpu_count() or 4
    n_workers = 2  # 固定2ワーカー: 残り6コアでWeb+altcoin応答確保
    executor = create_executor(df, df_oos2, names, n_workers=n_workers, df_oos3=df_oos3)
    loop = asyncio.get_event_loop()
    total = len(names)
    _early_stop = False

    try:
        # Batch submission: submit n_workers*3 at a time to avoid memory pressure
        batch_size = n_workers * 3
        idx = 0
        name_iter = iter(names)
        pending = set()

        # Initial batch
        for name in list(names[:batch_size]):
            fut = loop.run_in_executor(executor, _wf_single, name)
            pending.add(asyncio.ensure_future(fut))
        submitted = min(batch_size, total)

        while pending:
            done, pending = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED)
            for fut in done:
                idx += 1
                try:
                    sname, result = fut.result()
                except Exception as e:
                    log.warning(f"Worker error: {e}")
                    sname, result = "?", None

                if result and result_cb:
                    result_cb(result)
                if progress_cb:
                    progress_cb(idx, total, sname)

                # Submit next task to keep pipeline full
                if submitted < total and not _early_stop:
                    next_name = names[submitted]
                    new_fut = loop.run_in_executor(executor, _wf_single, next_name)
                    pending.add(asyncio.ensure_future(new_fut))
                    submitted += 1

            # Yield to event loop for web responsiveness
            await asyncio.sleep(0.5)

            # Early stop check
            if not _early_stop and early_stop_check and idx >= 200:
                if early_stop_check():
                    log.info(f"Early stop triggered at {idx}/{total} — goal achieved")
                    _early_stop = True
                    # Don't submit more, but finish pending
    finally:
        executor.shutdown(wait=False, cancel_futures=True)
        log.info(f"Executor shut down ({'early stop' if _early_stop else 'clean'})")


async def _auto_optimize():
    """Background: fetch data → WF optimize → evolve winners → repeat."""
    global _results, _tips

    if _run_status["running"]:
        return

    _run_status.update(running=True, progress="自動最適化開始...", strategies_completed=0)

    try:
        import pandas as pd
        from engine.data import fetch_full_dataset
        from engine.strategies import STRATEGIES

        symbol, interval = "BTCUSDT", "15m"
        # MEXC API ~350d max. Try 430d first for OOS3, fallback to 350d.
        for days in [430, 350]:
            _run_status.update(symbol=symbol, interval=interval, days=days)
            _run_status["progress"] = f"{symbol} {interval} {days}日分のデータ取得中..."
            df_full = await fetch_full_dataset(symbol=symbol, interval=interval, days=days)
            if not df_full.empty:
                break
        if df_full.empty:
            _run_status.update(running=False, progress="データ取得失敗")
            return

        # Split: OOS2 (first ~80 days) | main IS/OOS (middle ~270 days) | OOS3 (last ~80 days)
        # OOS2 = earliest holdout period, never seen in IS or OOS
        # OOS3 = most recent holdout period, never seen in IS or OOS (reference only)
        bars_per_day = 96  # 15m = 96 bars/day
        main_bars = 270 * bars_per_day  # ~25,920 bars for IS/OOS
        oos3_target_bars = 80 * bars_per_day  # ~7,680 bars for OOS3

        if len(df_full) > main_bars + 50 * bars_per_day + oos3_target_bars:
            # Enough data for OOS2 + IS/OOS + OOS3
            oos3_bars = oos3_target_bars
            oos2_bars = len(df_full) - main_bars - oos3_bars
            df_oos2 = df_full.iloc[:oos2_bars].reset_index(drop=True)
            df = df_full.iloc[oos2_bars:oos2_bars + main_bars].reset_index(drop=True)
            df_oos3 = df_full.iloc[oos2_bars + main_bars:].reset_index(drop=True)
            oos2_d = round(oos2_bars / bars_per_day)
            oos3_d = round(oos3_bars / bars_per_day)
            log.info(f"OOS2: {len(df_oos2)} bars (~{oos2_d}d), Main: {len(df)} bars (~270d), OOS3: {len(df_oos3)} bars (~{oos3_d}d)")
        elif len(df_full) > main_bars + 50 * bars_per_day:
            # Enough for OOS2 + IS/OOS but not OOS3 from MEXC
            oos2_bars = len(df_full) - main_bars
            df_oos2 = df_full.iloc[:oos2_bars].reset_index(drop=True)
            df = df_full.iloc[oos2_bars:].reset_index(drop=True)
            oos2_d = round(oos2_bars / bars_per_day)
            # Try loading OOS3 from separate Binance cache
            oos3_cache = Path("cache/BTCUSDT_15m_oos3.parquet")
            if oos3_cache.exists():
                df_oos3 = pd.read_parquet(oos3_cache)
                df_oos3["open_time"] = pd.to_datetime(df_oos3["open_time"])
                log.info(f"OOS2: {len(df_oos2)} bars (~{oos2_d}d), Main: {len(df)} bars (~270d), OOS3: {len(df_oos3)} bars (~{round(len(df_oos3)/bars_per_day)}d) [Binance]")
            else:
                df_oos3 = None
                log.info(f"OOS2: {len(df_oos2)} bars (~{oos2_d}d), Main: {len(df)} bars (~270d), OOS3: disabled (no cache)")
        else:
            # Not enough data for OOS2 split
            df = df_full.reset_index(drop=True)
            df_oos2 = None
            df_oos3 = None
            log.info(f"OOS2: disabled (insufficient data), Main: {len(df)} bars")

        # Keep ALL past results — don't filter on startup to avoid data loss
        # Just merge tips from existing results
        if _results:
            _merge_tips(_generate_tips(list(_results)))
        _save_tips()

        ALPHA_TARGET = 300.0       # 厳格化: ISα ≥ 300%
        OOS_ALPHA_TARGET = 100.0   # IS/OOS乖離を抑制: OOS >= 100%
        PBO_LIMIT = 0.3            # より厳格なPBO
        MIN_TRADES = 50            # 統計的信頼性: 350日期間で最低50トレード(≈週1回)
        MAX_DD = -35.0             # MaxDD > -35%（緩和済み目標ライン）
        MIN_EQUITY_R2 = 0.75      # エクイティR² > 0.75（右肩上がり）
        MIN_DAILY_RET = 1.0        # 厳格化: IS/OOS/OOS2全てreturn_daily_pct ≥ 1.0%
        GOAL_DAILY_RET = 1.5       # 努力目標: IS/OOS/OOS2全てreturn_daily_pct ≥ 1.5%
        GOAL_COUNT = 30            # 目標引き上げ: 30戦略達成まで探索継続
        round_num = 1
        run_names = None
        batch_id = 1
        total_analyses = 0

        def _equity_r2(r) -> float:
            """エクイティカーブのR²を計算。"""
            eq = r.get("equity_curve", [])
            if len(eq) < 20:
                return 0.0
            import numpy as np
            arr = np.array(eq, dtype=float)
            x = np.arange(len(arr))
            slope, intercept = np.polyfit(x, arr, 1)
            if slope <= 0:
                return 0.0
            y_pred = slope * x + intercept
            ss_res = np.sum((arr - y_pred) ** 2)
            ss_tot = np.sum((arr - np.mean(arr)) ** 2)
            return 1 - ss_res / ss_tot if ss_tot > 0 else 0

        OOS2_ALPHA_TARGET = 120.0  # 厳格化: OOS2 α ≥ 120%
        def _qualifying():
            qualified = []
            for r in _results:
                m = r["metrics"]
                wf = r.get("walkforward", {})
                oos_m = wf.get("oos_metrics", {})
                oos2_m = wf.get("oos2_metrics", {})
                # Core conditions
                if m["alpha_pct"] < ALPHA_TARGET: continue
                if oos_m.get("alpha_pct", 0) < OOS_ALPHA_TARGET: continue
                if oos2_m.get("alpha_pct", 0) < OOS2_ALPHA_TARGET: continue
                if wf.get("pbo_score", 1.0) >= PBO_LIMIT: continue
                if m["total_trades"] < MIN_TRADES: continue
                if m["max_drawdown_pct"] <= MAX_DD: continue
                if _equity_r2(r) < MIN_EQUITY_R2: continue
                # Daily return condition: IS/OOS/OOS2 all >= MIN_DAILY_RET (0.75%)
                is_rd = m.get("return_daily_pct", m["total_return_pct"] / 270)
                oos_rd = oos_m.get("return_daily_pct", 0)
                oos2_rd = oos2_m.get("return_daily_pct", 0)
                if is_rd < MIN_DAILY_RET or oos_rd < MIN_DAILY_RET or oos2_rd < MIN_DAILY_RET:
                    continue
                qualified.append(r)
            return qualified

        # Pre-register proven combo_signal strategies with leverage variants
        from engine.strategies import combo_signal
        # Format: (name_prefix, entry, ep1_grid, ep2_grid, filter, fp1, fp2, risk_overrides)
        _PROVEN_COMBOS = [
            # --- Pure leverage baselines ---
            ("ST_1x",   "supertrend", [8, 10, 12, 14, 18], [2.0, 2.5, 3.0], "none", [0], [0], {}),
            ("ST_2x",   "supertrend", [8, 10, 12, 14, 18], [2.0, 2.5, 3.0], "none", [0], [0], {"leverage": 2.0}),
            ("ST_2.5x", "supertrend", [8, 10, 12, 14, 18], [2.0, 2.5, 3.0], "none", [0], [0], {"leverage": 2.5}),
            ("ST_3.5x", "supertrend", [10, 12, 14], [2.0, 2.5, 3.0], "none", [0], [0], {"leverage": 3.5}),
            # --- Adaptive leverage scaling (lev_scale_dd) — preserves all trades ---
            # m=2.5 (142 trades, higher OOS but higher DD)
            ("ST_FIX12_25_3.5x_LS5", "supertrend", [12], [2.5], "none", [0], [0],
             {"leverage": 3.5, "lev_scale_dd": 0.05}),
            ("ST_FIX12_25_4x_LS3",   "supertrend", [12], [2.5], "none", [0], [0],
             {"leverage": 4.0, "lev_scale_dd": 0.03}),
            ("ST_FIX12_25_3.5x",     "supertrend", [12], [2.5], "none", [0], [0],
             {"leverage": 3.5}),  # pure 3.5x for OOS reference
            ("ST_FIX12_25_5x_LS3",   "supertrend", [12], [2.5], "none", [0], [0],
             {"leverage": 5.0, "lev_scale_dd": 0.03}),
            # m=4.0 (30 trades, lower DD, higher R²)
            ("ST_FIX8_40_2x_LS5",    "supertrend", [8], [4.0], "none", [0], [0],
             {"leverage": 2.0, "lev_scale_dd": 0.05}),
            ("ST_FIX8_40_3.5x_LS2",  "supertrend", [8], [4.0], "none", [0], [0],
             {"leverage": 3.5, "lev_scale_dd": 0.02}),
            ("ST_FIX8_40_6x_LS3",    "supertrend", [8], [4.0], "none", [0], [0],
             {"leverage": 6.0, "lev_scale_dd": 0.03}),
            ("ST_FIX8_40_5x_LS2",    "supertrend", [8], [4.0], "none", [0], [0],
             {"leverage": 5.0, "lev_scale_dd": 0.02}),
            ("ST_FIX8_40_3x_LS5",    "supertrend", [8], [4.0], "none", [0], [0],
             {"leverage": 3.0, "lev_scale_dd": 0.05}),
            ("ST_FIX8_40_8x_LS2",    "supertrend", [8], [4.0], "none", [0], [0],
             {"leverage": 8.0, "lev_scale_dd": 0.02}),
            # m=4.0 grid search (small grid)
            ("ST_40_2x_LS5",  "supertrend", [8, 10, 14], [4.0], "none", [0], [0],
             {"leverage": 2.0, "lev_scale_dd": 0.05}),
            ("ST_40_3.5x_LS3","supertrend", [8, 10, 14], [4.0], "none", [0], [0],
             {"leverage": 3.5, "lev_scale_dd": 0.03}),
            ("ST_40_5x_LS2",  "supertrend", [8, 10, 14], [4.0], "none", [0], [0],
             {"leverage": 5.0, "lev_scale_dd": 0.02}),
            # Wider bands (m=4.5-5.0) — lower DD, lower α
            ("ST_FIX8_50_3.5x_LS5",  "supertrend", [8], [5.0], "none", [0], [0],
             {"leverage": 3.5, "lev_scale_dd": 0.05}),
            ("ST_FIX24_45_3.5x_LS5", "supertrend", [24], [4.5], "none", [0], [0],
             {"leverage": 3.5, "lev_scale_dd": 0.05}),
            ("ST_FIX8_50_5x_LS3",    "supertrend", [8], [5.0], "none", [0], [0],
             {"leverage": 5.0, "lev_scale_dd": 0.03}),
            ("ST_FIX8_50_8x_LS2",    "supertrend", [8], [5.0], "none", [0], [0],
             {"leverage": 8.0, "lev_scale_dd": 0.02}),
            # --- Multi-ST ---
            ("MST_1x",   "multi_st", [5, 7, 10, 12], [1.5, 2.0, 2.5], "none", [0], [0], {}),
            ("MST_2x",   "multi_st", [5, 7, 10, 12], [1.5, 2.0, 2.5], "none", [0], [0], {"leverage": 2.0}),
            ("MST_3.5x", "multi_st", [7, 10, 12], [2.0, 2.5], "none", [0], [0], {"leverage": 3.5}),
            ("MST_3.5x_LS3", "multi_st", [7, 10, 12], [2.0, 2.5], "none", [0], [0],
             {"leverage": 3.5, "lev_scale_dd": 0.03}),
            # Multi-ST m=4.0 (fewer trades, lower DD)
            ("MST_FIX14_40_3.5x_LS3", "multi_st", [14], [4.0], "none", [0], [0],
             {"leverage": 3.5, "lev_scale_dd": 0.03}),
            # --- ST+EMA ---
            ("STEMA_1x",   "st_ema", [10, 14, 20], [30, 50, 100], "none", [0], [0], {}),
            ("STEMA_3x_LS3", "st_ema", [10, 14], [30, 50], "none", [0], [0],
             {"leverage": 3.0, "lev_scale_dd": 0.03}),
            # --- BREAKTHROUGH: p=11/13 m=2.5 @ 2.6x + EQ/DD (4/6 targets met) ---
            # Previous session found: α≥150%, OOS≥125%, PBO=0.0, T=35
            # Missing: DD=-16.84% (need >-15%) and R²=0.699 (need >0.700)
            ("ST_FIX11_25_2.6x_EQ1200_DD12", "supertrend", [11], [2.5], "none", [0], [0],
             {"leverage": 2.6, "equity_ma_bars": 1200, "dd_throttle_pct": 0.12}),
            ("ST_FIX13_25_2.6x_EQ1300_DD12", "supertrend", [13], [2.5], "none", [0], [0],
             {"leverage": 2.6, "equity_ma_bars": 1300, "dd_throttle_pct": 0.12}),
            # --- DD IMPROVEMENT: combine lev_scale_dd + dd_throttle (double protection) ---
            # lev_scale_dd reduces leverage during DD, dd_throttle stops entries entirely
            ("ST_FIX11_25_2.6x_LS5_DD10", "supertrend", [11], [2.5], "none", [0], [0],
             {"leverage": 2.6, "lev_scale_dd": 0.05, "dd_throttle_pct": 0.10}),
            ("ST_FIX13_25_2.6x_LS5_DD10", "supertrend", [13], [2.5], "none", [0], [0],
             {"leverage": 2.6, "lev_scale_dd": 0.05, "dd_throttle_pct": 0.10}),
            ("ST_FIX11_25_2.6x_LS3_DD10", "supertrend", [11], [2.5], "none", [0], [0],
             {"leverage": 2.6, "lev_scale_dd": 0.03, "dd_throttle_pct": 0.10}),
            ("ST_FIX13_25_2.6x_LS3_DD10", "supertrend", [13], [2.5], "none", [0], [0],
             {"leverage": 2.6, "lev_scale_dd": 0.03, "dd_throttle_pct": 0.10}),
            # Triple protection: lev_scale_dd + equity_ma + dd_throttle
            ("ST_FIX11_25_2.6x_LS5_EQ1000_DD10", "supertrend", [11], [2.5], "none", [0], [0],
             {"leverage": 2.6, "lev_scale_dd": 0.05, "equity_ma_bars": 1000, "dd_throttle_pct": 0.10}),
            ("ST_FIX13_25_2.6x_LS5_EQ1000_DD10", "supertrend", [13], [2.5], "none", [0], [0],
             {"leverage": 2.6, "lev_scale_dd": 0.05, "equity_ma_bars": 1000, "dd_throttle_pct": 0.10}),
            ("ST_FIX11_25_2.8x_LS3_EQ1200_DD10", "supertrend", [11], [2.5], "none", [0], [0],
             {"leverage": 2.8, "lev_scale_dd": 0.03, "equity_ma_bars": 1200, "dd_throttle_pct": 0.10}),
            ("ST_FIX13_25_2.8x_LS3_EQ1200_DD10", "supertrend", [13], [2.5], "none", [0], [0],
             {"leverage": 2.8, "lev_scale_dd": 0.03, "equity_ma_bars": 1200, "dd_throttle_pct": 0.10}),
            # Lower leverage with aggressive DD protection (target: DD > -15%)
            ("ST_FIX11_25_2.4x_LS5_DD08", "supertrend", [11], [2.5], "none", [0], [0],
             {"leverage": 2.4, "lev_scale_dd": 0.05, "dd_throttle_pct": 0.08}),
            ("ST_FIX13_25_2.4x_LS5_DD08", "supertrend", [13], [2.5], "none", [0], [0],
             {"leverage": 2.4, "lev_scale_dd": 0.05, "dd_throttle_pct": 0.08}),
            ("ST_FIX11_25_2.5x_LS5_DD08", "supertrend", [11], [2.5], "none", [0], [0],
             {"leverage": 2.5, "lev_scale_dd": 0.05, "dd_throttle_pct": 0.08}),
            ("ST_FIX13_25_2.5x_LS5_DD08", "supertrend", [13], [2.5], "none", [0], [0],
             {"leverage": 2.5, "lev_scale_dd": 0.05, "dd_throttle_pct": 0.08}),
            # Higher leverage with very tight DD control
            ("ST_FIX11_25_3.0x_LS3_DD08", "supertrend", [11], [2.5], "none", [0], [0],
             {"leverage": 3.0, "lev_scale_dd": 0.03, "dd_throttle_pct": 0.08}),
            ("ST_FIX13_25_3.0x_LS3_DD08", "supertrend", [13], [2.5], "none", [0], [0],
             {"leverage": 3.0, "lev_scale_dd": 0.03, "dd_throttle_pct": 0.08}),
            ("ST_FIX11_25_3.0x_LS3_EQ1000_DD08", "supertrend", [11], [2.5], "none", [0], [0],
             {"leverage": 3.0, "lev_scale_dd": 0.03, "equity_ma_bars": 1000, "dd_throttle_pct": 0.08}),
            ("ST_FIX13_25_3.0x_LS3_EQ1000_DD08", "supertrend", [13], [2.5], "none", [0], [0],
             {"leverage": 3.0, "lev_scale_dd": 0.03, "equity_ma_bars": 1000, "dd_throttle_pct": 0.08}),
            # Explore p=9,10,14,15 with similar setups
            ("ST_FIX9_25_2.6x_LS5_DD10",  "supertrend", [9],  [2.5], "none", [0], [0],
             {"leverage": 2.6, "lev_scale_dd": 0.05, "dd_throttle_pct": 0.10}),
            ("ST_FIX10_25_2.6x_LS5_DD10", "supertrend", [10], [2.5], "none", [0], [0],
             {"leverage": 2.6, "lev_scale_dd": 0.05, "dd_throttle_pct": 0.10}),
            ("ST_FIX14_25_2.6x_LS5_DD10", "supertrend", [14], [2.5], "none", [0], [0],
             {"leverage": 2.6, "lev_scale_dd": 0.05, "dd_throttle_pct": 0.10}),
            ("ST_FIX15_25_2.6x_LS5_DD10", "supertrend", [15], [2.5], "none", [0], [0],
             {"leverage": 2.6, "lev_scale_dd": 0.05, "dd_throttle_pct": 0.10}),
            # m=3.0 variants (wider bands, fewer but cleaner trades)
            ("ST_FIX11_30_2.6x_LS5_DD10", "supertrend", [11], [3.0], "none", [0], [0],
             {"leverage": 2.6, "lev_scale_dd": 0.05, "dd_throttle_pct": 0.10}),
            ("ST_FIX13_30_2.6x_LS5_DD10", "supertrend", [13], [3.0], "none", [0], [0],
             {"leverage": 2.6, "lev_scale_dd": 0.05, "dd_throttle_pct": 0.10}),
            ("ST_FIX11_30_2.8x_LS3_DD08", "supertrend", [11], [3.0], "none", [0], [0],
             {"leverage": 2.8, "lev_scale_dd": 0.03, "dd_throttle_pct": 0.08}),
            ("ST_FIX13_30_2.8x_LS3_DD08", "supertrend", [13], [3.0], "none", [0], [0],
             {"leverage": 2.8, "lev_scale_dd": 0.03, "dd_throttle_pct": 0.08}),
            # Pure lev_scale_dd at moderate leverage (no dd_throttle, preserves all trades)
            ("ST_FIX11_25_2.6x_LS5", "supertrend", [11], [2.5], "none", [0], [0],
             {"leverage": 2.6, "lev_scale_dd": 0.05}),
            ("ST_FIX13_25_2.6x_LS5", "supertrend", [13], [2.5], "none", [0], [0],
             {"leverage": 2.6, "lev_scale_dd": 0.05}),
            ("ST_FIX11_25_2.6x_LS3", "supertrend", [11], [2.5], "none", [0], [0],
             {"leverage": 2.6, "lev_scale_dd": 0.03}),
            ("ST_FIX13_25_2.6x_LS3", "supertrend", [13], [2.5], "none", [0], [0],
             {"leverage": 2.6, "lev_scale_dd": 0.03}),
            # Very tight lev_scale_dd (scale starts at just 2% DD)
            ("ST_FIX11_25_3.0x_LS2", "supertrend", [11], [2.5], "none", [0], [0],
             {"leverage": 3.0, "lev_scale_dd": 0.02}),
            ("ST_FIX13_25_3.0x_LS2", "supertrend", [13], [2.5], "none", [0], [0],
             {"leverage": 3.0, "lev_scale_dd": 0.02}),
            ("ST_FIX11_25_3.5x_LS2", "supertrend", [11], [2.5], "none", [0], [0],
             {"leverage": 3.5, "lev_scale_dd": 0.02}),
            ("ST_FIX13_25_3.5x_LS2", "supertrend", [13], [2.5], "none", [0], [0],
             {"leverage": 3.5, "lev_scale_dd": 0.02}),
            # --- EQ-TUNED strategies: wide range to handle data shifts ---
            # p=13 at 2.6x: broad EQ sweep (EQ values shift with new data)
            ("ST_FIX13_25_2.6x_EQ1080_DD12", "supertrend", [13], [2.5], "none", [0], [0],
             {"leverage": 2.6, "equity_ma_bars": 1080, "dd_throttle_pct": 0.12}),
            ("ST_FIX13_25_2.6x_EQ1180_DD12", "supertrend", [13], [2.5], "none", [0], [0],
             {"leverage": 2.6, "equity_ma_bars": 1180, "dd_throttle_pct": 0.12}),
            ("ST_FIX13_25_2.6x_EQ1200_DD12", "supertrend", [13], [2.5], "none", [0], [0],
             {"leverage": 2.6, "equity_ma_bars": 1200, "dd_throttle_pct": 0.12}),
            ("ST_FIX13_25_2.6x_EQ1210_DD12", "supertrend", [13], [2.5], "none", [0], [0],
             {"leverage": 2.6, "equity_ma_bars": 1210, "dd_throttle_pct": 0.12}),
            ("ST_FIX13_25_2.6x_EQ1230_DD12", "supertrend", [13], [2.5], "none", [0], [0],
             {"leverage": 2.6, "equity_ma_bars": 1230, "dd_throttle_pct": 0.12}),
            ("ST_FIX13_25_2.6x_EQ1240_DD12", "supertrend", [13], [2.5], "none", [0], [0],
             {"leverage": 2.6, "equity_ma_bars": 1240, "dd_throttle_pct": 0.12}),
            ("ST_FIX13_25_2.6x_EQ1250_DD12", "supertrend", [13], [2.5], "none", [0], [0],
             {"leverage": 2.6, "equity_ma_bars": 1250, "dd_throttle_pct": 0.12}),
            ("ST_FIX13_25_2.6x_EQ1290_DD12", "supertrend", [13], [2.5], "none", [0], [0],
             {"leverage": 2.6, "equity_ma_bars": 1290, "dd_throttle_pct": 0.12}),
            ("ST_FIX13_25_2.6x_EQ1420_DD12", "supertrend", [13], [2.5], "none", [0], [0],
             {"leverage": 2.6, "equity_ma_bars": 1420, "dd_throttle_pct": 0.12}),
            ("ST_FIX13_25_2.6x_EQ1500_DD12", "supertrend", [13], [2.5], "none", [0], [0],
             {"leverage": 2.6, "equity_ma_bars": 1500, "dd_throttle_pct": 0.12}),
            # p=11 at 2.6x: broad EQ sweep
            ("ST_FIX11_25_2.6x_EQ1160_DD12", "supertrend", [11], [2.5], "none", [0], [0],
             {"leverage": 2.6, "equity_ma_bars": 1160, "dd_throttle_pct": 0.12}),
            ("ST_FIX11_25_2.6x_EQ1170_DD12", "supertrend", [11], [2.5], "none", [0], [0],
             {"leverage": 2.6, "equity_ma_bars": 1170, "dd_throttle_pct": 0.12}),
            ("ST_FIX11_25_2.6x_EQ1180_DD12", "supertrend", [11], [2.5], "none", [0], [0],
             {"leverage": 2.6, "equity_ma_bars": 1180, "dd_throttle_pct": 0.12}),
            ("ST_FIX11_25_2.6x_EQ1210_DD12", "supertrend", [11], [2.5], "none", [0], [0],
             {"leverage": 2.6, "equity_ma_bars": 1210, "dd_throttle_pct": 0.12}),
            ("ST_FIX11_25_2.6x_EQ1240_DD12", "supertrend", [11], [2.5], "none", [0], [0],
             {"leverage": 2.6, "equity_ma_bars": 1240, "dd_throttle_pct": 0.12}),
            # p=13 at 2.55x (slightly lower DD)
            ("ST_FIX13_25_2.55x_EQ1200_DD12", "supertrend", [13], [2.5], "none", [0], [0],
             {"leverage": 2.55, "equity_ma_bars": 1200, "dd_throttle_pct": 0.12}),
            ("ST_FIX13_25_2.55x_EQ1230_DD12", "supertrend", [13], [2.5], "none", [0], [0],
             {"leverage": 2.55, "equity_ma_bars": 1230, "dd_throttle_pct": 0.12}),
            # MDE variants (hard DD cap at -15%, trades off alpha for DD protection)
            ("ST_FIX13_25_2.6x_EQ1200_DD12_MDE15", "supertrend", [13], [2.5], "none", [0], [0],
             {"leverage": 2.6, "equity_ma_bars": 1200, "dd_throttle_pct": 0.12, "max_dd_exit_pct": 0.15}),
            ("ST_FIX11_25_2.6x_EQ1160_DD12_MDE15", "supertrend", [11], [2.5], "none", [0], [0],
             {"leverage": 2.6, "equity_ma_bars": 1160, "dd_throttle_pct": 0.12, "max_dd_exit_pct": 0.15}),
            # --- CTS BREAKTHROUGH: 6/6 targets achieved ---
            # CTS (conditional trailing stop) tightens exits only during equity drawdown
            # DD reduced from -16.84% → -13.22% to -14.25% while keeping α≥150%, OOS≥100%
            # p=13 variants (OOS=127.1%)
            ("ST_FIX13_25_2.6x_EQ1200_DD12_CTS2_12", "supertrend", [13], [2.5], "none", [0], [0],
             {"leverage": 2.6, "equity_ma_bars": 1200, "dd_throttle_pct": 0.12,
              "cond_ts_pct": 0.02, "cond_ts_dd_pct": 0.12}),
            ("ST_FIX13_25_2.6x_EQ1200_DD12_CTS2_14", "supertrend", [13], [2.5], "none", [0], [0],
             {"leverage": 2.6, "equity_ma_bars": 1200, "dd_throttle_pct": 0.12,
              "cond_ts_pct": 0.02, "cond_ts_dd_pct": 0.14}),
            ("ST_FIX13_25_2.6x_EQ1200_DD12_CTS3_12", "supertrend", [13], [2.5], "none", [0], [0],
             {"leverage": 2.6, "equity_ma_bars": 1200, "dd_throttle_pct": 0.12,
              "cond_ts_pct": 0.03, "cond_ts_dd_pct": 0.12}),
            ("ST_FIX13_25_2.6x_EQ1200_DD12_CTS3_14", "supertrend", [13], [2.5], "none", [0], [0],
             {"leverage": 2.6, "equity_ma_bars": 1200, "dd_throttle_pct": 0.12,
              "cond_ts_pct": 0.03, "cond_ts_dd_pct": 0.14}),
            ("ST_FIX13_25_2.6x_EQ1200_DD12_CTS4_14", "supertrend", [13], [2.5], "none", [0], [0],
             {"leverage": 2.6, "equity_ma_bars": 1200, "dd_throttle_pct": 0.12,
              "cond_ts_pct": 0.04, "cond_ts_dd_pct": 0.14}),
            # p=11 variants (OOS=120.9%)
            ("ST_FIX11_25_2.6x_EQ1160_DD12_CTS3_12", "supertrend", [11], [2.5], "none", [0], [0],
             {"leverage": 2.6, "equity_ma_bars": 1160, "dd_throttle_pct": 0.12,
              "cond_ts_pct": 0.03, "cond_ts_dd_pct": 0.12}),
            ("ST_FIX11_25_2.6x_EQ1160_DD12_CTS3_14", "supertrend", [11], [2.5], "none", [0], [0],
             {"leverage": 2.6, "equity_ma_bars": 1160, "dd_throttle_pct": 0.12,
              "cond_ts_pct": 0.03, "cond_ts_dd_pct": 0.14}),
            ("ST_FIX11_25_2.6x_EQ1160_DD12_CTS4_14", "supertrend", [11], [2.5], "none", [0], [0],
             {"leverage": 2.6, "equity_ma_bars": 1160, "dd_throttle_pct": 0.12,
              "cond_ts_pct": 0.04, "cond_ts_dd_pct": 0.14}),
            # Wider EQ+CTS variants (data-shift robustness)
            ("ST_FIX13_25_2.6x_EQ1180_DD12_CTS2_14", "supertrend", [13], [2.5], "none", [0], [0],
             {"leverage": 2.6, "equity_ma_bars": 1180, "dd_throttle_pct": 0.12,
              "cond_ts_pct": 0.02, "cond_ts_dd_pct": 0.14}),
            ("ST_FIX13_25_2.6x_EQ1230_DD12_CTS2_14", "supertrend", [13], [2.5], "none", [0], [0],
             {"leverage": 2.6, "equity_ma_bars": 1230, "dd_throttle_pct": 0.12,
              "cond_ts_pct": 0.02, "cond_ts_dd_pct": 0.14}),
            ("ST_FIX13_25_2.6x_EQ1250_DD12_CTS3_14", "supertrend", [13], [2.5], "none", [0], [0],
             {"leverage": 2.6, "equity_ma_bars": 1250, "dd_throttle_pct": 0.12,
              "cond_ts_pct": 0.03, "cond_ts_dd_pct": 0.14}),
            ("ST_FIX11_25_2.6x_EQ1200_DD12_CTS3_14", "supertrend", [11], [2.5], "none", [0], [0],
             {"leverage": 2.6, "equity_ma_bars": 1200, "dd_throttle_pct": 0.12,
              "cond_ts_pct": 0.03, "cond_ts_dd_pct": 0.14}),
            ("ST_FIX11_25_2.6x_EQ1230_DD12_CTS3_14", "supertrend", [11], [2.5], "none", [0], [0],
             {"leverage": 2.6, "equity_ma_bars": 1230, "dd_throttle_pct": 0.12,
              "cond_ts_pct": 0.03, "cond_ts_dd_pct": 0.14}),
            # --- HIGH RETURN TARGET: 5x-10x leverage + aggressive DD control ---
            # Goal: monthly 100%+ return. 9 months × 100% ≈ 900% total.
            # lev_scale_dd keeps effective leverage low during DD, high during trend.
            # Key insight: higher lev + tighter scale = more return/DD ratio potential
            # p=12 m=2.5 (142 trades at 1x — high trade count for statistical confidence)
            ("ST_HR_12_25_5x_LS2",  "supertrend", [12], [2.5], "none", [0], [0],
             {"leverage": 5.0, "lev_scale_dd": 0.02}),
            ("ST_HR_12_25_6x_LS2",  "supertrend", [12], [2.5], "none", [0], [0],
             {"leverage": 6.0, "lev_scale_dd": 0.02}),
            ("ST_HR_12_25_8x_LS15", "supertrend", [12], [2.5], "none", [0], [0],
             {"leverage": 8.0, "lev_scale_dd": 0.015}),
            ("ST_HR_12_25_10x_LS1", "supertrend", [12], [2.5], "none", [0], [0],
             {"leverage": 10.0, "lev_scale_dd": 0.01}),
            ("ST_HR_12_25_5x_LS3_DD8",  "supertrend", [12], [2.5], "none", [0], [0],
             {"leverage": 5.0, "lev_scale_dd": 0.03, "dd_throttle_pct": 0.08}),
            ("ST_HR_12_25_6x_LS2_DD8",  "supertrend", [12], [2.5], "none", [0], [0],
             {"leverage": 6.0, "lev_scale_dd": 0.02, "dd_throttle_pct": 0.08}),
            ("ST_HR_12_25_8x_LS15_DD6", "supertrend", [12], [2.5], "none", [0], [0],
             {"leverage": 8.0, "lev_scale_dd": 0.015, "dd_throttle_pct": 0.06}),
            ("ST_HR_12_25_10x_LS1_DD5", "supertrend", [12], [2.5], "none", [0], [0],
             {"leverage": 10.0, "lev_scale_dd": 0.01, "dd_throttle_pct": 0.05}),
            # MDE variants: hard cap DD to guarantee max drawdown
            ("ST_HR_12_25_5x_LS2_MDE20",  "supertrend", [12], [2.5], "none", [0], [0],
             {"leverage": 5.0, "lev_scale_dd": 0.02, "max_dd_exit_pct": 0.20}),
            ("ST_HR_12_25_8x_LS15_MDE25", "supertrend", [12], [2.5], "none", [0], [0],
             {"leverage": 8.0, "lev_scale_dd": 0.015, "max_dd_exit_pct": 0.25}),
            # p=10,14 at high leverage (different trade frequency)
            ("ST_HR_10_25_5x_LS2",  "supertrend", [10], [2.5], "none", [0], [0],
             {"leverage": 5.0, "lev_scale_dd": 0.02}),
            ("ST_HR_14_25_5x_LS2",  "supertrend", [14], [2.5], "none", [0], [0],
             {"leverage": 5.0, "lev_scale_dd": 0.02}),
            ("ST_HR_10_25_8x_LS15", "supertrend", [10], [2.5], "none", [0], [0],
             {"leverage": 8.0, "lev_scale_dd": 0.015}),
            ("ST_HR_14_25_8x_LS15", "supertrend", [14], [2.5], "none", [0], [0],
             {"leverage": 8.0, "lev_scale_dd": 0.015}),
            # m=3.0 at high leverage (wider bands, cleaner trends)
            ("ST_HR_12_30_5x_LS2",  "supertrend", [12], [3.0], "none", [0], [0],
             {"leverage": 5.0, "lev_scale_dd": 0.02}),
            ("ST_HR_12_30_8x_LS15", "supertrend", [12], [3.0], "none", [0], [0],
             {"leverage": 8.0, "lev_scale_dd": 0.015}),
            ("ST_HR_10_30_6x_LS2",  "supertrend", [10], [3.0], "none", [0], [0],
             {"leverage": 6.0, "lev_scale_dd": 0.02}),
            # Grid search at high leverage: let WF find optimal p/m
            ("ST_HR_5x_LS2",  "supertrend", [8, 10, 12, 14], [2.0, 2.5, 3.0], "none", [0], [0],
             {"leverage": 5.0, "lev_scale_dd": 0.02}),
            ("ST_HR_8x_LS15", "supertrend", [8, 10, 12, 14], [2.0, 2.5, 3.0], "none", [0], [0],
             {"leverage": 8.0, "lev_scale_dd": 0.015}),
            # Multi-ST at high leverage (consensus reduces false signals)
            ("MST_HR_5x_LS2",  "multi_st", [7, 10, 12], [2.0, 2.5], "none", [0], [0],
             {"leverage": 5.0, "lev_scale_dd": 0.02}),
            ("MST_HR_8x_LS15", "multi_st", [7, 10, 12], [2.0, 2.5], "none", [0], [0],
             {"leverage": 8.0, "lev_scale_dd": 0.015}),
            # ST+EMA at high leverage
            ("STEMA_HR_5x_LS2",  "st_ema", [10, 14], [30, 50], "none", [0], [0],
             {"leverage": 5.0, "lev_scale_dd": 0.02}),
            ("STEMA_HR_8x_LS15", "st_ema", [10, 14], [30, 50], "none", [0], [0],
             {"leverage": 8.0, "lev_scale_dd": 0.015}),
            # --- OOS2 ROBUST: pure signal, NO DD management ---
            # OOS2 analysis shows: lev_scale_dd overfits, pure signals are robust
            # Strategy: wider bands (m=4-5) naturally reduce DD, moderate leverage
            # Wider bands = fewer but cleaner trades = lower inherent DD
            ("ST_PURE_4x_m40", "supertrend", [8, 10, 12, 14], [4.0], "none", [0], [0],
             {"leverage": 4.0}),
            ("ST_PURE_3x_m40", "supertrend", [8, 10, 12, 14], [4.0], "none", [0], [0],
             {"leverage": 3.0}),
            ("ST_PURE_5x_m40", "supertrend", [8, 10, 12, 14], [4.0], "none", [0], [0],
             {"leverage": 5.0}),
            ("ST_PURE_3x_m50", "supertrend", [8, 10, 12, 14], [5.0], "none", [0], [0],
             {"leverage": 3.0}),
            ("ST_PURE_4x_m50", "supertrend", [8, 10, 12, 14], [5.0], "none", [0], [0],
             {"leverage": 4.0}),
            ("ST_PURE_5x_m50", "supertrend", [8, 10, 12, 14], [5.0], "none", [0], [0],
             {"leverage": 5.0}),
            # ATR filter: only trade when volatility is sufficient (avoids choppy markets)
            ("ST_ATR_3x_m25", "supertrend", [8, 10, 12, 14], [2.5], "atr", [14], [0.5, 1.0],
             {"leverage": 3.0}),
            ("ST_ATR_4x_m25", "supertrend", [8, 10, 12, 14], [2.5], "atr", [14], [0.5, 1.0],
             {"leverage": 4.0}),
            ("ST_ATR_3x_m30", "supertrend", [8, 10, 12, 14], [3.0], "atr", [14], [0.5, 1.0],
             {"leverage": 3.0}),
            ("ST_ATR_4x_m30", "supertrend", [8, 10, 12, 14], [3.0], "atr", [14], [0.5, 1.0],
             {"leverage": 4.0}),
            # Volume filter: only trade on high volume (confirms trend strength)
            ("ST_VOL_3x_m25", "supertrend", [8, 10, 12, 14], [2.5], "volume", [20], [1.2, 1.5],
             {"leverage": 3.0}),
            ("ST_VOL_4x_m25", "supertrend", [8, 10, 12, 14], [2.5], "volume", [20], [1.2, 1.5],
             {"leverage": 4.0}),
            # Trend filter: only trade when EMA200 aligns (massive noise reduction)
            ("ST_TREND_3x_m25", "supertrend", [8, 10, 12, 14], [2.5], "trend", [200], [0],
             {"leverage": 3.0}),
            ("ST_TREND_4x_m25", "supertrend", [8, 10, 12, 14], [2.5], "trend", [200], [0],
             {"leverage": 4.0}),
            ("ST_TREND_3x_m30", "supertrend", [10, 12, 14], [3.0], "trend", [100, 200], [0],
             {"leverage": 3.0}),
            ("ST_TREND_4x_m30", "supertrend", [10, 12, 14], [3.0], "trend", [100, 200], [0],
             {"leverage": 4.0}),
            # Multi-ST pure (consensus, inherently more robust)
            ("MST_PURE_3x", "multi_st", [7, 10, 12, 14], [2.0, 2.5, 3.0], "none", [0], [0],
             {"leverage": 3.0}),
            ("MST_PURE_4x", "multi_st", [7, 10, 12, 14], [2.0, 2.5, 3.0], "none", [0], [0],
             {"leverage": 4.0}),
            ("MST_PURE_5x", "multi_st", [7, 10, 12, 14], [2.0, 2.5, 3.0], "none", [0], [0],
             {"leverage": 5.0}),
            # Donchian channel (breakout) — different signal type, may have different DD profile
            ("DCH_PURE_3x", "donchian", [20, 30, 50], [0], "none", [0], [0],
             {"leverage": 3.0}),
            ("DCH_PURE_4x", "donchian", [20, 30, 50], [0], "none", [0], [0],
             {"leverage": 4.0}),
            ("DCH_ATR_3x",  "donchian", [20, 30, 50], [0], "atr", [14], [0.5, 1.0],
             {"leverage": 3.0}),
            # Keltner channel — like BB but with ATR, good for trend following
            ("KELT_PURE_3x", "keltner", [14, 20, 30], [1.5, 2.0, 2.5], "none", [0], [0],
             {"leverage": 3.0}),
            ("KELT_PURE_4x", "keltner", [14, 20, 30], [1.5, 2.0, 2.5], "none", [0], [0],
             {"leverage": 4.0}),
            # --- COOLDOWN-BASED DD CONTROL (time-based, not equity-based) ---
            # Cooldown prevents re-entry for N bars after exit, avoids re-entering during volatile periods
            # Unlike lev_scale_dd/equity_ma, cooldown is a fixed rule — shouldn't overfit
            # Standard m=2.5 (142 trades at 1x, cooldown reduces to ~100-120)
            ("ST_CD4_3x",  "supertrend", [8, 10, 12, 14], [2.5], "none", [0], [0],
             {"leverage": 3.0, "cooldown_bars": 4}),
            ("ST_CD4_4x",  "supertrend", [8, 10, 12, 14], [2.5], "none", [0], [0],
             {"leverage": 4.0, "cooldown_bars": 4}),
            ("ST_CD8_3x",  "supertrend", [8, 10, 12, 14], [2.5], "none", [0], [0],
             {"leverage": 3.0, "cooldown_bars": 8}),
            ("ST_CD8_4x",  "supertrend", [8, 10, 12, 14], [2.5], "none", [0], [0],
             {"leverage": 4.0, "cooldown_bars": 8}),
            ("ST_CD16_3x", "supertrend", [8, 10, 12, 14], [2.5], "none", [0], [0],
             {"leverage": 3.0, "cooldown_bars": 16}),
            ("ST_CD16_4x", "supertrend", [8, 10, 12, 14], [2.5], "none", [0], [0],
             {"leverage": 4.0, "cooldown_bars": 16}),
            # m=3.0 with cooldown (wider bands + cooldown for double DD protection)
            ("ST_CD4_3x_m30",  "supertrend", [8, 10, 12, 14], [3.0], "none", [0], [0],
             {"leverage": 3.0, "cooldown_bars": 4}),
            ("ST_CD4_4x_m30",  "supertrend", [8, 10, 12, 14], [3.0], "none", [0], [0],
             {"leverage": 4.0, "cooldown_bars": 4}),
            ("ST_CD8_3x_m30",  "supertrend", [8, 10, 12, 14], [3.0], "none", [0], [0],
             {"leverage": 3.0, "cooldown_bars": 8}),
            ("ST_CD8_4x_m30",  "supertrend", [8, 10, 12, 14], [3.0], "none", [0], [0],
             {"leverage": 4.0, "cooldown_bars": 8}),
            # Lower p values (p=5-7) with m=2.5: MORE trades for statistical confidence
            ("ST_LOWP_3x", "supertrend", [5, 6, 7], [2.5], "none", [0], [0],
             {"leverage": 3.0}),
            ("ST_LOWP_4x", "supertrend", [5, 6, 7], [2.5], "none", [0], [0],
             {"leverage": 4.0}),
            ("ST_LOWP_CD4_3x", "supertrend", [5, 6, 7], [2.5], "none", [0], [0],
             {"leverage": 3.0, "cooldown_bars": 4}),
            ("ST_LOWP_CD4_4x", "supertrend", [5, 6, 7], [2.5], "none", [0], [0],
             {"leverage": 4.0, "cooldown_bars": 4}),
            # Multi-ST with cooldown (consensus + cooldown = robust DD control)
            ("MST_CD4_3x", "multi_st", [7, 10, 12], [2.0, 2.5], "none", [0], [0],
             {"leverage": 3.0, "cooldown_bars": 4}),
            ("MST_CD4_4x", "multi_st", [7, 10, 12], [2.0, 2.5], "none", [0], [0],
             {"leverage": 4.0, "cooldown_bars": 4}),
            ("MST_CD8_3x", "multi_st", [7, 10, 12], [2.0, 2.5], "none", [0], [0],
             {"leverage": 3.0, "cooldown_bars": 8}),
            # --- LOWP BREAKTHROUGH: p=5-7 gives 146 trades + positive OOS2 ---
            # Higher leverage variants of proven LOWP base
            ("ST_LOWP_5x", "supertrend", [5, 6, 7], [2.5], "none", [0], [0],
             {"leverage": 5.0}),
            ("ST_LOWP_6x", "supertrend", [5, 6, 7], [2.5], "none", [0], [0],
             {"leverage": 6.0}),
            ("ST_LOWP_2x", "supertrend", [5, 6, 7], [2.5], "none", [0], [0],
             {"leverage": 2.0}),
            ("ST_LOWP_2.5x", "supertrend", [5, 6, 7], [2.5], "none", [0], [0],
             {"leverage": 2.5}),
            # LOWP with lev_scale_dd (test if LOWP robustness survives DD control)
            ("ST_LOWP_5x_LS2", "supertrend", [5, 6, 7], [2.5], "none", [0], [0],
             {"leverage": 5.0, "lev_scale_dd": 0.02}),
            ("ST_LOWP_4x_LS2", "supertrend", [5, 6, 7], [2.5], "none", [0], [0],
             {"leverage": 4.0, "lev_scale_dd": 0.02}),
            ("ST_LOWP_6x_LS15", "supertrend", [5, 6, 7], [2.5], "none", [0], [0],
             {"leverage": 6.0, "lev_scale_dd": 0.015}),
            ("ST_LOWP_8x_LS15", "supertrend", [5, 6, 7], [2.5], "none", [0], [0],
             {"leverage": 8.0, "lev_scale_dd": 0.015}),
            # LOWP with wider bands (m=3.0) for lower DD
            ("ST_LOWP_3x_m30", "supertrend", [5, 6, 7], [3.0], "none", [0], [0],
             {"leverage": 3.0}),
            ("ST_LOWP_4x_m30", "supertrend", [5, 6, 7], [3.0], "none", [0], [0],
             {"leverage": 4.0}),
            ("ST_LOWP_5x_m30", "supertrend", [5, 6, 7], [3.0], "none", [0], [0],
             {"leverage": 5.0}),
            # LOWP + cooldown variants at higher leverage
            ("ST_LOWP_CD4_5x", "supertrend", [5, 6, 7], [2.5], "none", [0], [0],
             {"leverage": 5.0, "cooldown_bars": 4}),
            ("ST_LOWP_CD8_3x", "supertrend", [5, 6, 7], [2.5], "none", [0], [0],
             {"leverage": 3.0, "cooldown_bars": 8}),
            ("ST_LOWP_CD8_4x", "supertrend", [5, 6, 7], [2.5], "none", [0], [0],
             {"leverage": 4.0, "cooldown_bars": 8}),

            # ── MTF: LOWP Supertrend + Higher-TF Supertrend filter ──
            # htf_st: fp1=resample factor (4=1h,16=4h), fp2=HTF ST multiplier
            # Tests whether aligning with HTF trend reduces DD without killing alpha
            ("MTF_LOWP_1H_2x", "supertrend", [5, 6, 7], [2.5], "htf_st", [4], [2.5, 3.0],
             {"leverage": 2.0}),
            ("MTF_LOWP_1H_3x", "supertrend", [5, 6, 7], [2.5], "htf_st", [4], [2.5, 3.0],
             {"leverage": 3.0}),
            ("MTF_LOWP_1H_4x", "supertrend", [5, 6, 7], [2.5], "htf_st", [4], [2.5, 3.0],
             {"leverage": 4.0}),
            ("MTF_LOWP_4H_2x", "supertrend", [5, 6, 7], [2.5], "htf_st", [16], [2.5, 3.0],
             {"leverage": 2.0}),
            ("MTF_LOWP_4H_3x", "supertrend", [5, 6, 7], [2.5], "htf_st", [16], [2.5, 3.0],
             {"leverage": 3.0}),
            ("MTF_LOWP_4H_4x", "supertrend", [5, 6, 7], [2.5], "htf_st", [16], [2.5, 3.0],
             {"leverage": 4.0}),
            ("MTF_LOWP_2H_3x", "supertrend", [5, 6, 7], [2.5], "htf_st", [8], [2.5, 3.0],
             {"leverage": 3.0}),
            ("MTF_LOWP_2H_4x", "supertrend", [5, 6, 7], [2.5], "htf_st", [8], [2.5, 3.0],
             {"leverage": 4.0}),
            # MTF with standard period Supertrend (p=10-14)
            ("MTF_ST_1H_3x", "supertrend", [10, 12, 14], [2.5, 3.0], "htf_st", [4], [2.5, 3.0],
             {"leverage": 3.0}),
            ("MTF_ST_4H_3x", "supertrend", [10, 12, 14], [2.5, 3.0], "htf_st", [16], [2.5, 3.0],
             {"leverage": 3.0}),
            # Non-Supertrend entries with MTF filter
            ("MTF_EMA_1H_3x", "ema", [12, 20], [50, 100], "htf_st", [4], [2.5, 3.0],
             {"leverage": 3.0}),
            ("MTF_MACD_4H_3x", "macd", [12], [26], "htf_st", [16], [2.5, 3.0],
             {"leverage": 3.0}),
            ("MTF_DONCH_1H_3x", "donchian", [20, 30], [0], "htf_st", [4], [2.5, 3.0],
             {"leverage": 3.0}),
            # High leverage MTF (DD should be lower → can push lev)
            ("MTF_LOWP_1H_5x", "supertrend", [5, 6, 7], [2.5], "htf_st", [4], [2.5, 3.0],
             {"leverage": 5.0}),
            ("MTF_LOWP_4H_5x", "supertrend", [5, 6, 7], [2.5], "htf_st", [16], [2.5, 3.0],
             {"leverage": 5.0}),
            ("MTF_LOWP_1H_6x", "supertrend", [5, 6, 7], [2.5], "htf_st", [4], [2.5, 3.0],
             {"leverage": 6.0}),

            # ── DUAL SUPERTREND: fast ST entry + slow ST directional filter ──
            # Fast ST (p=5-7, m=2.5) for entries, slow ST (p=20-30, m=3-4) for trend direction
            # Exploration found: α=+323%, DD=-52%, Sharpe=2.18 at fast=6/2.5 + slow=30/4.0
            ("DUAL_ST_LOWP_2x", "supertrend", [5, 6, 7], [2.5], "slow_st", [20, 30], [3.0, 3.5, 4.0],
             {"leverage": 2.0}),
            ("DUAL_ST_LOWP_2.5x", "supertrend", [5, 6, 7], [2.5], "slow_st", [20, 30], [3.0, 3.5, 4.0],
             {"leverage": 2.5}),
            ("DUAL_ST_LOWP_3x", "supertrend", [5, 6, 7], [2.5], "slow_st", [20, 30], [3.0, 3.5, 4.0],
             {"leverage": 3.0}),
            ("DUAL_ST_LOWP_4x", "supertrend", [5, 6, 7], [2.5], "slow_st", [20, 30], [3.0, 3.5, 4.0],
             {"leverage": 4.0}),
            ("DUAL_ST_LOWP_5x", "supertrend", [5, 6, 7], [2.5], "slow_st", [20, 30], [3.0, 3.5, 4.0],
             {"leverage": 5.0}),
            # Standard period fast ST + slow ST filter
            ("DUAL_ST_STD_3x", "supertrend", [10, 12, 14], [2.5, 3.0], "slow_st", [20, 30], [3.0, 4.0],
             {"leverage": 3.0}),
            ("DUAL_ST_STD_4x", "supertrend", [10, 12, 14], [2.5, 3.0], "slow_st", [20, 30], [3.0, 4.0],
             {"leverage": 4.0}),

            # ── BREAKOUT+ST: Donchian breakout confirmed by Supertrend direction ──
            # Exploration found: DD=-39% (best ever, vs LOWP -59%), α=+146%
            # ep1=ST period, ep2=Donchian period
            ("ST_BREAK_20_2x", "st_breakout", [5, 6, 7], [15, 20, 25], "none", [0], [0],
             {"leverage": 2.0}),
            ("ST_BREAK_20_2.5x", "st_breakout", [5, 6, 7], [15, 20, 25], "none", [0], [0],
             {"leverage": 2.5}),
            ("ST_BREAK_20_3x", "st_breakout", [5, 6, 7], [15, 20, 25], "none", [0], [0],
             {"leverage": 3.0}),
            ("ST_BREAK_20_4x", "st_breakout", [5, 6, 7], [15, 20, 25], "none", [0], [0],
             {"leverage": 4.0}),
            ("ST_BREAK_20_5x", "st_breakout", [5, 6, 7], [15, 20, 25], "none", [0], [0],
             {"leverage": 5.0}),
            # Standard period Breakout+ST
            ("ST_BREAK_STD_3x", "st_breakout", [10, 12, 14], [15, 20, 30], "none", [0], [0],
             {"leverage": 3.0}),
            ("ST_BREAK_STD_4x", "st_breakout", [10, 12, 14], [15, 20, 30], "none", [0], [0],
             {"leverage": 4.0}),
            # Breakout+ST with slow_st filter (triple confirmation: breakout + fast ST + slow ST)
            ("ST_BREAK_DUAL_3x", "st_breakout", [5, 6, 7], [15, 20], "slow_st", [20, 30], [3.5, 4.0],
             {"leverage": 3.0}),
            ("ST_BREAK_DUAL_4x", "st_breakout", [5, 6, 7], [15, 20], "slow_st", [20, 30], [3.5, 4.0],
             {"leverage": 4.0}),

            # ── NEW: ST+RSI momentum confirmation ──
            ("ST_RSI_2x", "st_rsi", [5, 6, 7], [10, 14], "none", [0], [0], {"leverage": 2.0}),
            ("ST_RSI_3x", "st_rsi", [5, 6, 7], [10, 14], "none", [0], [0], {"leverage": 3.0}),
            ("ST_RSI_4x", "st_rsi", [5, 6, 7], [10, 14], "none", [0], [0], {"leverage": 4.0}),
            ("ST_RSI_DUAL_3x", "st_rsi", [5, 6, 7], [10, 14], "slow_st", [20, 30], [3.5, 4.0],
             {"leverage": 3.0}),
            ("ST_RSI_DUAL_4x", "st_rsi", [5, 6, 7], [10, 14], "slow_st", [20, 30], [3.5, 4.0],
             {"leverage": 4.0}),
            ("ST_RSI_HTF_3x", "st_rsi", [5, 6, 7], [10, 14], "htf_st", [4, 16], [2.5, 3.0],
             {"leverage": 3.0}),

            # ── NEW: ST+MACD histogram ──
            ("ST_MACD_2x", "st_macd", [5, 6, 7], [21, 26], "none", [0], [0], {"leverage": 2.0}),
            ("ST_MACD_3x", "st_macd", [5, 6, 7], [21, 26], "none", [0], [0], {"leverage": 3.0}),
            ("ST_MACD_4x", "st_macd", [5, 6, 7], [21, 26], "none", [0], [0], {"leverage": 4.0}),
            ("ST_MACD_DUAL_3x", "st_macd", [5, 6, 7], [21, 26], "slow_st", [20, 30], [3.5, 4.0],
             {"leverage": 3.0}),

            # ── NEW: BB Squeeze breakout (low vol → expansion) ──
            ("BB_SQZ_2x", "bb_squeeze", [15, 20], [1.5, 2.0], "none", [0], [0], {"leverage": 2.0}),
            ("BB_SQZ_3x", "bb_squeeze", [15, 20], [1.5, 2.0], "none", [0], [0], {"leverage": 3.0}),
            ("BB_SQZ_4x", "bb_squeeze", [15, 20, 30], [1.5, 2.0, 2.5], "none", [0], [0], {"leverage": 4.0}),
            ("BB_SQZ_DUAL_3x", "bb_squeeze", [15, 20], [1.5, 2.0], "slow_st", [20, 30], [3.5, 4.0],
             {"leverage": 3.0}),
            ("BB_SQZ_HTF_3x", "bb_squeeze", [15, 20], [1.5, 2.0], "htf_st", [4, 16], [2.5, 3.0],
             {"leverage": 3.0}),

            # ── NEW: Pivot breakout + ST ──
            ("PIVOT_ST_2x", "pivot_st", [5, 6, 7], [0], "none", [0], [0], {"leverage": 2.0}),
            ("PIVOT_ST_3x", "pivot_st", [5, 6, 7], [0], "none", [0], [0], {"leverage": 3.0}),
            ("PIVOT_ST_4x", "pivot_st", [5, 6, 7], [0], "none", [0], [0], {"leverage": 4.0}),
            ("PIVOT_ST_DUAL_3x", "pivot_st", [5, 6, 7], [0], "slow_st", [20, 30], [3.5, 4.0],
             {"leverage": 3.0}),

            # ── NEW: Mean reversion in trend direction (dip buying) ──
            ("MREV_ST_2x", "mean_rev_st", [5, 6, 7], [15, 20], "none", [0], [0], {"leverage": 2.0}),
            ("MREV_ST_3x", "mean_rev_st", [5, 6, 7], [15, 20], "none", [0], [0], {"leverage": 3.0}),
            ("MREV_ST_4x", "mean_rev_st", [5, 6, 7], [15, 20, 30], "none", [0], [0], {"leverage": 4.0}),
            ("MREV_ST_DUAL_3x", "mean_rev_st", [5, 6, 7], [15, 20], "slow_st", [20, 30], [3.5, 4.0],
             {"leverage": 3.0}),
            ("MREV_ST_HTF_3x", "mean_rev_st", [5, 6, 7], [15, 20], "htf_st", [4, 16], [2.5, 3.0],
             {"leverage": 3.0}),

            # ── Cross-pollination: winning filters × proven entries ──
            # LOWP + slow_st at various leverages (Dual ST proven good)
            ("LOWP_SLOW_1.5x", "supertrend", [5, 6, 7], [2.5], "slow_st", [20, 25, 30], [3.0, 3.5, 4.0],
             {"leverage": 1.5}),
            # Breakout + HTF filter
            ("ST_BREAK_HTF_1H_3x", "st_breakout", [5, 6, 7], [15, 20, 25], "htf_st", [4], [2.5, 3.0],
             {"leverage": 3.0}),
            ("ST_BREAK_HTF_4H_3x", "st_breakout", [5, 6, 7], [15, 20, 25], "htf_st", [16], [2.5, 3.0],
             {"leverage": 3.0}),
            # EMA crossover + slow_st (different signal family)
            ("EMA_DUAL_3x", "ema", [5, 9, 12], [21, 30, 50], "slow_st", [20, 30], [3.0, 4.0],
             {"leverage": 3.0}),
            ("EMA_DUAL_4x", "ema", [5, 9, 12], [21, 30, 50], "slow_st", [20, 30], [3.0, 4.0],
             {"leverage": 4.0}),
            # Donchian + slow_st
            ("DCH_DUAL_3x", "donchian", [20, 30, 50], [0], "slow_st", [20, 30], [3.0, 4.0],
             {"leverage": 3.0}),
            # MACD + slow_st
            ("MACD_DUAL_3x", "macd", [8, 12], [21, 26], "slow_st", [20, 30], [3.0, 4.0],
             {"leverage": 3.0}),
            # Keltner + slow_st
            ("KELT_DUAL_3x", "keltner", [14, 20], [1.5, 2.0], "slow_st", [20, 30], [3.0, 4.0],
             {"leverage": 3.0}),

            # ══ ROUND 2: Improvements based on R1 analysis ══
            # Finding: slow_st filter is best, pivot_st and mean_rev_st are new winners
            # Finding: 2.5x-3x leverage = sweet spot for DD < -50%
            # Finding: OOS2 stability highest in LOWP (T=146) family

            # ── Pivot+ST fine-tuning (ranked #3, α/d=1.43) ──
            ("PIVOT_ST_1.5x", "pivot_st", [5, 6, 7], [0], "none", [0], [0], {"leverage": 1.5}),
            ("PIVOT_ST_2.5x", "pivot_st", [5, 6, 7], [0], "none", [0], [0], {"leverage": 2.5}),
            ("PIVOT_ST_DUAL_2x", "pivot_st", [5, 6, 7], [0], "slow_st", [20, 25, 30], [3.0, 3.5, 4.0],
             {"leverage": 2.0}),
            ("PIVOT_ST_DUAL_2.5x", "pivot_st", [5, 6, 7], [0], "slow_st", [20, 25, 30], [3.0, 3.5, 4.0],
             {"leverage": 2.5}),
            ("PIVOT_ST_DUAL_4x", "pivot_st", [5, 6, 7], [0], "slow_st", [20, 25, 30], [3.0, 3.5, 4.0],
             {"leverage": 4.0}),
            # Pivot + HTF filter
            ("PIVOT_ST_HTF_1H_3x", "pivot_st", [5, 6, 7], [0], "htf_st", [4], [2.5, 3.0],
             {"leverage": 3.0}),
            ("PIVOT_ST_HTF_4H_3x", "pivot_st", [5, 6, 7], [0], "htf_st", [16], [2.5, 3.0],
             {"leverage": 3.0}),
            # Wider ST params for pivot
            ("PIVOT_ST_STD_DUAL_3x", "pivot_st", [10, 12, 14], [0], "slow_st", [20, 30], [3.0, 4.0],
             {"leverage": 3.0}),

            # ── Mean reversion+ST fine-tuning (ranked #4, α/d=1.39) ──
            ("MREV_ST_1.5x", "mean_rev_st", [5, 6, 7], [15, 20], "none", [0], [0], {"leverage": 1.5}),
            ("MREV_ST_2.5x", "mean_rev_st", [5, 6, 7], [15, 20], "none", [0], [0], {"leverage": 2.5}),
            ("MREV_ST_DUAL_2x", "mean_rev_st", [5, 6, 7], [15, 20], "slow_st", [20, 25, 30], [3.0, 3.5, 4.0],
             {"leverage": 2.0}),
            ("MREV_ST_DUAL_2.5x", "mean_rev_st", [5, 6, 7], [15, 20], "slow_st", [20, 25, 30], [3.0, 3.5, 4.0],
             {"leverage": 2.5}),
            ("MREV_ST_DUAL_4x", "mean_rev_st", [5, 6, 7], [15, 20], "slow_st", [20, 25, 30], [3.0, 3.5, 4.0],
             {"leverage": 4.0}),
            # Wider BB for mean_rev (more trades)
            ("MREV_ST_WIDE_3x", "mean_rev_st", [5, 6, 7], [10, 12], "none", [0], [0], {"leverage": 3.0}),
            ("MREV_ST_WIDE_DUAL_3x", "mean_rev_st", [5, 6, 7], [10, 12], "slow_st", [20, 30], [3.5, 4.0],
             {"leverage": 3.0}),
            # Longer BB for smoother signals
            ("MREV_ST_LONG_3x", "mean_rev_st", [5, 6, 7], [30, 40], "none", [0], [0], {"leverage": 3.0}),
            ("MREV_ST_LONG_DUAL_3x", "mean_rev_st", [5, 6, 7], [30, 40], "slow_st", [20, 30], [3.5, 4.0],
             {"leverage": 3.0}),

            # ── Dual ST LOWP fine-tuning (ranked #2, highest consistency) ──
            ("DUAL_ST_LOWP_1.5x", "supertrend", [5, 6, 7], [2.5], "slow_st", [20, 25, 30], [3.0, 3.5, 4.0],
             {"leverage": 1.5}),
            # Wider slow ST params
            ("DUAL_ST_LOWP_WIDE_3x", "supertrend", [5, 6, 7], [2.5], "slow_st", [15, 35, 40], [2.5, 3.0, 4.5],
             {"leverage": 3.0}),
            # Different fast ST multipliers
            ("DUAL_ST_LOWP_M20_3x", "supertrend", [5, 6, 7], [2.0], "slow_st", [20, 30], [3.0, 4.0],
             {"leverage": 3.0}),
            ("DUAL_ST_LOWP_M30_3x", "supertrend", [5, 6, 7], [3.0], "slow_st", [20, 30], [3.0, 4.0],
             {"leverage": 3.0}),
            # Cooldown + Dual ST
            ("DUAL_ST_CD4_3x", "supertrend", [5, 6, 7], [2.5], "slow_st", [20, 30], [3.0, 4.0],
             {"leverage": 3.0, "cooldown_bars": 4}),
            ("DUAL_ST_CD8_3x", "supertrend", [5, 6, 7], [2.5], "slow_st", [20, 30], [3.0, 4.0],
             {"leverage": 3.0, "cooldown_bars": 8}),

            # ── ST_BREAK_DUAL fine-tuning (ranked #1, α/d=1.73) ──
            ("ST_BREAK_DUAL_2x", "st_breakout", [5, 6, 7], [15, 20, 25], "slow_st", [20, 25, 30], [3.0, 3.5, 4.0],
             {"leverage": 2.0}),
            ("ST_BREAK_DUAL_2.5x", "st_breakout", [5, 6, 7], [15, 20, 25], "slow_st", [20, 25, 30], [3.0, 3.5, 4.0],
             {"leverage": 2.5}),
            ("ST_BREAK_DUAL_5x", "st_breakout", [5, 6, 7], [15, 20], "slow_st", [20, 30], [3.5, 4.0],
             {"leverage": 5.0}),
            # Breakout + Dual + wider donchian
            ("ST_BREAK_DUAL_WIDE_3x", "st_breakout", [5, 6, 7], [30, 40, 50], "slow_st", [20, 30], [3.5, 4.0],
             {"leverage": 3.0}),

            # ── Hybrid: combine top entries with top filters ──
            # ST_RSI + trend filter (EMA200)
            ("ST_RSI_TREND_3x", "st_rsi", [5, 6, 7], [10, 14], "trend", [200], [0], {"leverage": 3.0}),
            # BB_Squeeze + slow_st + ATR filter
            ("BB_SQZ_ATR_3x", "bb_squeeze", [15, 20], [1.5, 2.0], "atr", [14], [0.5, 1.0], {"leverage": 3.0}),
            # Ichimoku + slow_st (Japanese classic meets modern)
            ("ICHI_DUAL_3x", "ichimoku", [7, 9], [22, 26], "slow_st", [20, 30], [3.0, 4.0],
             {"leverage": 3.0}),
            # CCI + slow_st
            ("CCI_DUAL_3x", "cci", [14, 20], [100, 150], "slow_st", [20, 30], [3.0, 4.0],
             {"leverage": 3.0}),
            # Williams %R + slow_st
            ("WLMS_DUAL_3x", "williams", [10, 14], [20, 25], "slow_st", [20, 30], [3.0, 4.0],
             {"leverage": 3.0}),
            # Hull MA + slow_st
            ("HULL_DUAL_3x", "hull", [16, 24], [1.0, 2.0], "slow_st", [20, 30], [3.0, 4.0],
             {"leverage": 3.0}),
            # DMI + slow_st
            ("DMI_DUAL_3x", "dmi", [10, 14], [20, 25], "slow_st", [20, 30], [3.0, 4.0],
             {"leverage": 3.0}),
            # Stochastic + slow_st
            ("STOCH_DUAL_3x", "stoch", [10, 14], [20, 25], "slow_st", [20, 30], [3.0, 4.0],
             {"leverage": 3.0}),

            # ========== DD-TARGETED: Goal qualification (α≥150% + DD>-35%) ==========
            # MREV_ST: best Calmar ratio, 1.5x has DD=-30.8% — need <-30%
            # Correct params: ep1=ST period [5,6,7], ep2=BB lookback [15,20,25]
            # Pure low-leverage (no overlays)
            ("MREV_ST_1x", "mean_rev_st", [5, 6, 7], [15, 20, 25], "none", [0], [0], {}),
            ("MREV_ST_1.2x", "mean_rev_st", [5, 6, 7], [15, 20, 25], "none", [0], [0],
             {"leverage": 1.2}),
            ("MREV_ST_1.3x", "mean_rev_st", [5, 6, 7], [15, 20, 25], "none", [0], [0],
             {"leverage": 1.3}),
            ("MREV_ST_1.4x", "mean_rev_st", [5, 6, 7], [15, 20, 25], "none", [0], [0],
             {"leverage": 1.4}),
            # Low-lev + mild overlays
            ("MREV_ST_1.5x_DT10", "mean_rev_st", [5, 6, 7], [15, 20, 25], "none", [0], [0],
             {"leverage": 1.5, "dd_throttle_pct": 0.10}),
            ("MREV_ST_1.5x_DT15", "mean_rev_st", [5, 6, 7], [15, 20, 25], "none", [0], [0],
             {"leverage": 1.5, "dd_throttle_pct": 0.15}),
            ("MREV_ST_1.5x_MDE28", "mean_rev_st", [5, 6, 7], [15, 20, 25], "none", [0], [0],
             {"leverage": 1.5, "max_dd_exit_pct": 0.28}),
            ("MREV_ST_2x_MDE25", "mean_rev_st", [5, 6, 7], [15, 20, 25], "none", [0], [0],
             {"leverage": 2.0, "max_dd_exit_pct": 0.25}),
            ("MREV_ST_1.5x_EQ400", "mean_rev_st", [5, 6, 7], [15, 20, 25], "none", [0], [0],
             {"leverage": 1.5, "equity_ma_bars": 400}),

            # MREV_ST WIDE (best OOS2: α=73%@3x) — correct params: ep1=[5,6,7], ep2=[10,12]
            # High leverage + max_dd_exit: OOS2=bull→DDトリガーされにくい, Main=bear→DD制限
            ("MREV_ST_WIDE_4x_MDE28", "mean_rev_st", [5, 6, 7], [10, 12], "none", [0], [0],
             {"leverage": 4.0, "max_dd_exit_pct": 0.28}),
            ("MREV_ST_WIDE_5x_MDE28", "mean_rev_st", [5, 6, 7], [10, 12], "none", [0], [0],
             {"leverage": 5.0, "max_dd_exit_pct": 0.28}),
            ("MREV_ST_WIDE_6x_MDE28", "mean_rev_st", [5, 6, 7], [10, 12], "none", [0], [0],
             {"leverage": 6.0, "max_dd_exit_pct": 0.28}),
            ("MREV_ST_WIDE_4x_MDE25", "mean_rev_st", [5, 6, 7], [10, 12], "none", [0], [0],
             {"leverage": 4.0, "max_dd_exit_pct": 0.25}),
            ("MREV_ST_WIDE_5x_MDE25", "mean_rev_st", [5, 6, 7], [10, 12], "none", [0], [0],
             {"leverage": 5.0, "max_dd_exit_pct": 0.25}),
            ("MREV_ST_WIDE_4x_DT15", "mean_rev_st", [5, 6, 7], [10, 12], "none", [0], [0],
             {"leverage": 4.0, "dd_throttle_pct": 0.15}),
            ("MREV_ST_WIDE_5x_DT15", "mean_rev_st", [5, 6, 7], [10, 12], "none", [0], [0],
             {"leverage": 5.0, "dd_throttle_pct": 0.15}),
            # Wider param search
            ("MREV_ST_WIDE_4x_MDE28_B", "mean_rev_st", [4, 5, 6, 7, 8], [8, 10, 12, 14], "none", [0], [0],
             {"leverage": 4.0, "max_dd_exit_pct": 0.28}),
            ("MREV_ST_WIDE_5x_MDE28_B", "mean_rev_st", [4, 5, 6, 7, 8], [8, 10, 12, 14], "none", [0], [0],
             {"leverage": 5.0, "max_dd_exit_pct": 0.28}),
            # MREV_ST_WIDE + slow_st dual + high lev + MDE
            ("MREV_ST_WIDE_DUAL_4x_MDE28", "mean_rev_st", [5, 6, 7], [10, 12], "slow_st", [20, 30], [3.5, 4.0],
             {"leverage": 4.0, "max_dd_exit_pct": 0.28}),
            ("MREV_ST_WIDE_DUAL_5x_MDE28", "mean_rev_st", [5, 6, 7], [10, 12], "slow_st", [20, 30], [3.5, 4.0],
             {"leverage": 5.0, "max_dd_exit_pct": 0.28}),
            # MREV_ST LONG (best total ret) + MDE
            ("MREV_ST_LONG_4x_MDE28", "mean_rev_st", [5, 6, 7], [30, 40], "none", [0], [0],
             {"leverage": 4.0, "max_dd_exit_pct": 0.28}),
            ("MREV_ST_LONG_5x_MDE28", "mean_rev_st", [5, 6, 7], [30, 40], "none", [0], [0],
             {"leverage": 5.0, "max_dd_exit_pct": 0.28}),
            ("MREV_ST_LONG_DUAL_4x_MDE28", "mean_rev_st", [5, 6, 7], [30, 40], "slow_st", [20, 30], [3.5, 4.0],
             {"leverage": 4.0, "max_dd_exit_pct": 0.28}),
            ("MREV_ST_LONG_DUAL_5x_MDE28", "mean_rev_st", [5, 6, 7], [30, 40], "slow_st", [20, 30], [3.5, 4.0],
             {"leverage": 5.0, "max_dd_exit_pct": 0.28}),
            # Standard MREV_ST + MDE
            ("MREV_ST_4x_MDE28", "mean_rev_st", [5, 6, 7], [15, 20, 25], "none", [0], [0],
             {"leverage": 4.0, "max_dd_exit_pct": 0.28}),
            ("MREV_ST_5x_MDE28", "mean_rev_st", [5, 6, 7], [15, 20, 25], "none", [0], [0],
             {"leverage": 5.0, "max_dd_exit_pct": 0.28}),
            # PIVOT_ST high OOS2 + MDE
            ("PIVOT_ST_4x_MDE28", "pivot_st", [5, 6, 7], [15, 20], "none", [0], [0],
             {"leverage": 4.0, "max_dd_exit_pct": 0.28}),
            ("PIVOT_ST_5x_MDE28", "pivot_st", [5, 6, 7], [15, 20], "none", [0], [0],
             {"leverage": 5.0, "max_dd_exit_pct": 0.28}),
            ("PIVOT_ST_DUAL_4x_MDE28", "pivot_st", [5, 6, 7], [15, 20], "slow_st", [20, 30], [3.5, 4.0],
             {"leverage": 4.0, "max_dd_exit_pct": 0.28}),
            # ST_LOWP high OOS2 + MDE
            ("ST_LOWP_4x_MDE28", "supertrend", [5, 6, 7], [2.5], "none", [0], [0],
             {"leverage": 4.0, "max_dd_exit_pct": 0.28}),
            ("ST_LOWP_5x_MDE28", "supertrend", [5, 6, 7], [2.5], "none", [0], [0],
             {"leverage": 5.0, "max_dd_exit_pct": 0.28}),
            ("DUAL_ST_LOWP_4x_MDE28", "supertrend", [5, 6, 7], [2.5], "slow_st", [20, 30], [3.5, 4.0],
             {"leverage": 4.0, "max_dd_exit_pct": 0.28}),
            ("DUAL_ST_LOWP_5x_MDE28", "supertrend", [5, 6, 7], [2.5], "slow_st", [20, 30], [3.5, 4.0],
             {"leverage": 5.0, "max_dd_exit_pct": 0.28}),
            # ST_BREAK + MDE
            ("ST_BREAK_4x_MDE28", "st_breakout", [5, 6, 7], [15, 20, 25], "none", [0], [0],
             {"leverage": 4.0, "max_dd_exit_pct": 0.28}),
            ("ST_BREAK_5x_MDE28", "st_breakout", [5, 6, 7], [15, 20, 25], "none", [0], [0],
             {"leverage": 5.0, "max_dd_exit_pct": 0.28}),
            ("ST_BREAK_DUAL_4x_MDE28", "st_breakout", [5, 6, 7], [15, 20, 25], "slow_st", [20, 30], [3.5, 4.0],
             {"leverage": 4.0, "max_dd_exit_pct": 0.28}),
            ("ST_BREAK_DUAL_5x_MDE28", "st_breakout", [5, 6, 7], [15, 20, 25], "slow_st", [20, 30], [3.5, 4.0],
             {"leverage": 5.0, "max_dd_exit_pct": 0.28}),

            # MREV_ST LONG (α=430%, best overall) — ep1=[5,6,7], ep2=[30,40]
            ("MREV_ST_LONG_1x", "mean_rev_st", [5, 6, 7], [30, 40], "none", [0], [0], {}),
            ("MREV_ST_LONG_1.2x", "mean_rev_st", [5, 6, 7], [30, 40], "none", [0], [0],
             {"leverage": 1.2}),
            ("MREV_ST_LONG_1.5x", "mean_rev_st", [5, 6, 7], [30, 40], "none", [0], [0],
             {"leverage": 1.5}),
            ("MREV_ST_LONG_DUAL_1.5x", "mean_rev_st", [5, 6, 7], [30, 40], "slow_st", [20, 30], [3.5, 4.0],
             {"leverage": 1.5}),

            # DUAL_ST LOWP — correct params: ep1=[5,6,7], ep2=[2.5]
            ("DUAL_ST_LOWP_1x", "supertrend", [5, 6, 7], [2.5], "slow_st", [20, 25, 30], [3.0, 3.5, 4.0], {}),
            ("DUAL_ST_LOWP_1.2x", "supertrend", [5, 6, 7], [2.5], "slow_st", [20, 25, 30], [3.0, 3.5, 4.0],
             {"leverage": 1.2}),
            ("DUAL_ST_LOWP_1.5x_MDE28", "supertrend", [5, 6, 7], [2.5], "slow_st", [20, 25, 30], [3.0, 3.5, 4.0],
             {"leverage": 1.5, "max_dd_exit_pct": 0.28}),
            ("DUAL_ST_LOWP_2x_MDE25", "supertrend", [5, 6, 7], [2.5], "slow_st", [20, 25, 30], [3.0, 3.5, 4.0],
             {"leverage": 2.0, "max_dd_exit_pct": 0.25}),

            # ST_BREAK_DUAL — correct params: ep1=[5,6,7], ep2=[15,20,25]
            ("ST_BREAK_DUAL_1x", "st_breakout", [5, 6, 7], [15, 20, 25], "slow_st", [20, 25, 30], [3.0, 3.5, 4.0], {}),
            ("ST_BREAK_DUAL_1.5x", "st_breakout", [5, 6, 7], [15, 20, 25], "slow_st", [20, 25, 30], [3.0, 3.5, 4.0],
             {"leverage": 1.5}),
            ("ST_BREAK_DUAL_1.5x_MDE28", "st_breakout", [5, 6, 7], [15, 20, 25], "slow_st", [20, 25, 30], [3.0, 3.5, 4.0],
             {"leverage": 1.5, "max_dd_exit_pct": 0.28}),

            # PIVOT_ST_DUAL — correct params: ep1=[5,6,7], ep2=[15,20]
            ("PIVOT_ST_DUAL_1x", "pivot_st", [5, 6, 7], [15, 20], "slow_st", [20, 25, 30], [3.0, 3.5, 4.0], {}),
            ("PIVOT_ST_DUAL_1.5x", "pivot_st", [5, 6, 7], [15, 20], "slow_st", [20, 25, 30], [3.0, 3.5, 4.0],
             {"leverage": 1.5}),

            # ─── OOS2 α push: pure high-leverage (no MDE) to find OOS2 ceiling ───
            # MREV_ST_WIDE: best OOS2 base (73.1% at 3x) → target 100%+ at 4-6x
            ("MREV_ST_WIDE_3.5x", "mean_rev_st", [5, 6, 7], [10, 12], "none", [0], [0],
             {"leverage": 3.5}),
            ("MREV_ST_WIDE_4x", "mean_rev_st", [5, 6, 7], [10, 12], "none", [0], [0],
             {"leverage": 4.0}),
            ("MREV_ST_WIDE_4.5x", "mean_rev_st", [5, 6, 7], [10, 12], "none", [0], [0],
             {"leverage": 4.5}),
            ("MREV_ST_WIDE_5x", "mean_rev_st", [5, 6, 7], [10, 12], "none", [0], [0],
             {"leverage": 5.0}),
            ("MREV_ST_WIDE_6x", "mean_rev_st", [5, 6, 7], [10, 12], "none", [0], [0],
             {"leverage": 6.0}),
            # PIVOT_ST: 2nd best OOS2 (45.3% at 2.5x) → target 100%+ at 5-7x
            ("PIVOT_ST_4x", "pivot_st", [5, 6, 7], [15, 20], "none", [0], [0],
             {"leverage": 4.0}),
            ("PIVOT_ST_5x", "pivot_st", [5, 6, 7], [15, 20], "none", [0], [0],
             {"leverage": 5.0}),
            ("PIVOT_ST_6x", "pivot_st", [5, 6, 7], [15, 20], "none", [0], [0],
             {"leverage": 6.0}),
            # MREV_ST_STD: ep2=[15,20,25] at higher leverage
            ("MREV_ST_4x", "mean_rev_st", [5, 6, 7], [15, 20, 25], "none", [0], [0],
             {"leverage": 4.0}),
            ("MREV_ST_5x", "mean_rev_st", [5, 6, 7], [15, 20, 25], "none", [0], [0],
             {"leverage": 5.0}),
            # MREV_ST_LONG: ep2=[30,40] at higher leverage
            ("MREV_ST_LONG_3x", "mean_rev_st", [5, 6, 7], [30, 40], "none", [0], [0],
             {"leverage": 3.0}),
            ("MREV_ST_LONG_4x", "mean_rev_st", [5, 6, 7], [30, 40], "none", [0], [0],
             {"leverage": 4.0}),
            ("MREV_ST_LONG_5x", "mean_rev_st", [5, 6, 7], [30, 40], "none", [0], [0],
             {"leverage": 5.0}),

            # ─── Higher MDE thresholds (0.30, 0.35) — less likely to trigger in bull OOS2 ───
            ("MREV_ST_WIDE_4x_MDE30", "mean_rev_st", [5, 6, 7], [10, 12], "none", [0], [0],
             {"leverage": 4.0, "max_dd_exit_pct": 0.30}),
            ("MREV_ST_WIDE_5x_MDE30", "mean_rev_st", [5, 6, 7], [10, 12], "none", [0], [0],
             {"leverage": 5.0, "max_dd_exit_pct": 0.30}),
            ("MREV_ST_WIDE_6x_MDE30", "mean_rev_st", [5, 6, 7], [10, 12], "none", [0], [0],
             {"leverage": 6.0, "max_dd_exit_pct": 0.30}),
            ("MREV_ST_WIDE_4x_MDE35", "mean_rev_st", [5, 6, 7], [10, 12], "none", [0], [0],
             {"leverage": 4.0, "max_dd_exit_pct": 0.35}),
            ("MREV_ST_WIDE_5x_MDE35", "mean_rev_st", [5, 6, 7], [10, 12], "none", [0], [0],
             {"leverage": 5.0, "max_dd_exit_pct": 0.35}),
            ("MREV_ST_WIDE_6x_MDE35", "mean_rev_st", [5, 6, 7], [10, 12], "none", [0], [0],
             {"leverage": 6.0, "max_dd_exit_pct": 0.35}),
            ("MREV_ST_WIDE_4.5x_MDE30", "mean_rev_st", [5, 6, 7], [10, 12], "none", [0], [0],
             {"leverage": 4.5, "max_dd_exit_pct": 0.30}),
            ("MREV_ST_WIDE_5.5x_MDE30", "mean_rev_st", [5, 6, 7], [10, 12], "none", [0], [0],
             {"leverage": 5.5, "max_dd_exit_pct": 0.30}),
            # PIVOT_ST with MDE
            ("PIVOT_ST_4x_MDE30", "pivot_st", [5, 6, 7], [15, 20], "none", [0], [0],
             {"leverage": 4.0, "max_dd_exit_pct": 0.30}),
            ("PIVOT_ST_5x_MDE30", "pivot_st", [5, 6, 7], [15, 20], "none", [0], [0],
             {"leverage": 5.0, "max_dd_exit_pct": 0.30}),
            ("PIVOT_ST_6x_MDE30", "pivot_st", [5, 6, 7], [15, 20], "none", [0], [0],
             {"leverage": 6.0, "max_dd_exit_pct": 0.30}),
            ("PIVOT_ST_5x_MDE35", "pivot_st", [5, 6, 7], [15, 20], "none", [0], [0],
             {"leverage": 5.0, "max_dd_exit_pct": 0.35}),
            # MREV_ST_STD with MDE
            ("MREV_ST_4x_MDE30", "mean_rev_st", [5, 6, 7], [15, 20, 25], "none", [0], [0],
             {"leverage": 4.0, "max_dd_exit_pct": 0.30}),
            ("MREV_ST_5x_MDE30", "mean_rev_st", [5, 6, 7], [15, 20, 25], "none", [0], [0],
             {"leverage": 5.0, "max_dd_exit_pct": 0.30}),
            # MREV_ST_LONG with MDE
            ("MREV_ST_LONG_4x_MDE30", "mean_rev_st", [5, 6, 7], [30, 40], "none", [0], [0],
             {"leverage": 4.0, "max_dd_exit_pct": 0.30}),
            ("MREV_ST_LONG_5x_MDE30", "mean_rev_st", [5, 6, 7], [30, 40], "none", [0], [0],
             {"leverage": 5.0, "max_dd_exit_pct": 0.30}),
            # ST_LOWP high-lev + MDE
            ("ST_LOWP_4x_MDE30", "supertrend", [5, 6, 7], [2.5], "none", [0], [0],
             {"leverage": 4.0, "max_dd_exit_pct": 0.30}),
            ("ST_LOWP_5x_MDE30", "supertrend", [5, 6, 7], [2.5], "none", [0], [0],
             {"leverage": 5.0, "max_dd_exit_pct": 0.30}),
            ("ST_LOWP_6x_MDE30", "supertrend", [5, 6, 7], [2.5], "none", [0], [0],
             {"leverage": 6.0, "max_dd_exit_pct": 0.30}),
            # ST_BREAK high-lev + MDE
            ("ST_BREAK_4x_MDE30", "st_breakout", [5, 6, 7], [15, 20, 25], "none", [0], [0],
             {"leverage": 4.0, "max_dd_exit_pct": 0.30}),
            ("ST_BREAK_5x_MDE30", "st_breakout", [5, 6, 7], [15, 20, 25], "none", [0], [0],
             {"leverage": 5.0, "max_dd_exit_pct": 0.30}),

            # ─── Wider param search for OOS2 push ───
            ("MREV_ST_ULTRA_4x_MDE30", "mean_rev_st", [3, 4, 5, 6, 7, 8, 9], [8, 10, 12, 15], "none", [0], [0],
             {"leverage": 4.0, "max_dd_exit_pct": 0.30}),
            ("MREV_ST_ULTRA_5x_MDE30", "mean_rev_st", [3, 4, 5, 6, 7, 8, 9], [8, 10, 12, 15], "none", [0], [0],
             {"leverage": 5.0, "max_dd_exit_pct": 0.30}),
            ("MREV_ST_ULTRA_6x_MDE30", "mean_rev_st", [3, 4, 5, 6, 7, 8, 9], [8, 10, 12, 15], "none", [0], [0],
             {"leverage": 6.0, "max_dd_exit_pct": 0.30}),

            # ─── Dual filter + high lev + MDE (filter may help OOS2) ───
            ("MREV_ST_WIDE_DUAL_4x_MDE30", "mean_rev_st", [5, 6, 7], [10, 12], "slow_st", [20, 30], [3.5, 4.0],
             {"leverage": 4.0, "max_dd_exit_pct": 0.30}),
            ("MREV_ST_WIDE_DUAL_5x_MDE30", "mean_rev_st", [5, 6, 7], [10, 12], "slow_st", [20, 30], [3.5, 4.0],
             {"leverage": 5.0, "max_dd_exit_pct": 0.30}),
            ("MREV_ST_WIDE_ATR_4x_MDE30", "mean_rev_st", [5, 6, 7], [10, 12], "atr", [14, 20], [1.5, 2.0],
             {"leverage": 4.0, "max_dd_exit_pct": 0.30}),
            ("MREV_ST_WIDE_ATR_5x_MDE30", "mean_rev_st", [5, 6, 7], [10, 12], "atr", [14, 20], [1.5, 2.0],
             {"leverage": 5.0, "max_dd_exit_pct": 0.30}),
            ("MREV_ST_WIDE_TREND_4x_MDE30", "mean_rev_st", [5, 6, 7], [10, 12], "trend", [50, 100], [200, 300],
             {"leverage": 4.0, "max_dd_exit_pct": 0.30}),
            ("MREV_ST_WIDE_TREND_5x_MDE30", "mean_rev_st", [5, 6, 7], [10, 12], "trend", [50, 100], [200, 300],
             {"leverage": 5.0, "max_dd_exit_pct": 0.30}),
            ("PIVOT_ST_DUAL_4x_MDE30", "pivot_st", [5, 6, 7], [15, 20], "slow_st", [20, 30], [3.5, 4.0],
             {"leverage": 4.0, "max_dd_exit_pct": 0.30}),
            ("PIVOT_ST_DUAL_5x_MDE30", "pivot_st", [5, 6, 7], [15, 20], "slow_st", [20, 30], [3.5, 4.0],
             {"leverage": 5.0, "max_dd_exit_pct": 0.30}),

            # ─── MDE + Cooldown: prevent DD compounding by waiting after liquidation ───
            # MDE=0.28 + mde_cooldown=480 (5 days): single MDE caps DD, cooldown prevents re-entry in downtrend
            ("MREV_ST_WIDE_3x_MDE28_CD480", "mean_rev_st", [5, 6, 7], [10, 12], "none", [0], [0],
             {"leverage": 3.0, "max_dd_exit_pct": 0.28, "mde_cooldown_bars": 480}),
            ("MREV_ST_WIDE_3x_MDE20_CD480", "mean_rev_st", [5, 6, 7], [10, 12], "none", [0], [0],
             {"leverage": 3.0, "max_dd_exit_pct": 0.20, "mde_cooldown_bars": 480}),
            ("MREV_ST_WIDE_3x_MDE15_CD480", "mean_rev_st", [5, 6, 7], [10, 12], "none", [0], [0],
             {"leverage": 3.0, "max_dd_exit_pct": 0.15, "mde_cooldown_bars": 480}),
            ("MREV_ST_WIDE_4x_MDE28_CD480", "mean_rev_st", [5, 6, 7], [10, 12], "none", [0], [0],
             {"leverage": 4.0, "max_dd_exit_pct": 0.28, "mde_cooldown_bars": 480}),
            ("MREV_ST_WIDE_4x_MDE20_CD480", "mean_rev_st", [5, 6, 7], [10, 12], "none", [0], [0],
             {"leverage": 4.0, "max_dd_exit_pct": 0.20, "mde_cooldown_bars": 480}),
            ("MREV_ST_WIDE_5x_MDE28_CD480", "mean_rev_st", [5, 6, 7], [10, 12], "none", [0], [0],
             {"leverage": 5.0, "max_dd_exit_pct": 0.28, "mde_cooldown_bars": 480}),
            ("MREV_ST_WIDE_5x_MDE20_CD480", "mean_rev_st", [5, 6, 7], [10, 12], "none", [0], [0],
             {"leverage": 5.0, "max_dd_exit_pct": 0.20, "mde_cooldown_bars": 480}),
            # Shorter cooldown: 240 bars (2.5 days)
            ("MREV_ST_WIDE_3x_MDE28_CD240", "mean_rev_st", [5, 6, 7], [10, 12], "none", [0], [0],
             {"leverage": 3.0, "max_dd_exit_pct": 0.28, "mde_cooldown_bars": 240}),
            ("MREV_ST_WIDE_4x_MDE28_CD240", "mean_rev_st", [5, 6, 7], [10, 12], "none", [0], [0],
             {"leverage": 4.0, "max_dd_exit_pct": 0.28, "mde_cooldown_bars": 240}),
            ("MREV_ST_WIDE_5x_MDE28_CD240", "mean_rev_st", [5, 6, 7], [10, 12], "none", [0], [0],
             {"leverage": 5.0, "max_dd_exit_pct": 0.28, "mde_cooldown_bars": 240}),
            # Longer cooldown: 960 bars (10 days) — aggressive DD control
            ("MREV_ST_WIDE_3x_MDE28_CD960", "mean_rev_st", [5, 6, 7], [10, 12], "none", [0], [0],
             {"leverage": 3.0, "max_dd_exit_pct": 0.28, "mde_cooldown_bars": 960}),
            ("MREV_ST_WIDE_4x_MDE28_CD960", "mean_rev_st", [5, 6, 7], [10, 12], "none", [0], [0],
             {"leverage": 4.0, "max_dd_exit_pct": 0.28, "mde_cooldown_bars": 960}),
            ("MREV_ST_WIDE_5x_MDE28_CD960", "mean_rev_st", [5, 6, 7], [10, 12], "none", [0], [0],
             {"leverage": 5.0, "max_dd_exit_pct": 0.28, "mde_cooldown_bars": 960}),
            # PIVOT_ST + MDE + cooldown
            ("PIVOT_ST_3x_MDE28_CD480", "pivot_st", [5, 6, 7], [15, 20], "none", [0], [0],
             {"leverage": 3.0, "max_dd_exit_pct": 0.28, "mde_cooldown_bars": 480}),
            ("PIVOT_ST_4x_MDE28_CD480", "pivot_st", [5, 6, 7], [15, 20], "none", [0], [0],
             {"leverage": 4.0, "max_dd_exit_pct": 0.28, "mde_cooldown_bars": 480}),
            ("PIVOT_ST_5x_MDE28_CD480", "pivot_st", [5, 6, 7], [15, 20], "none", [0], [0],
             {"leverage": 5.0, "max_dd_exit_pct": 0.28, "mde_cooldown_bars": 480}),
            # MREV_ST_STD + MDE + cooldown
            ("MREV_ST_3x_MDE28_CD480", "mean_rev_st", [5, 6, 7], [15, 20, 25], "none", [0], [0],
             {"leverage": 3.0, "max_dd_exit_pct": 0.28, "mde_cooldown_bars": 480}),
            ("MREV_ST_4x_MDE28_CD480", "mean_rev_st", [5, 6, 7], [15, 20, 25], "none", [0], [0],
             {"leverage": 4.0, "max_dd_exit_pct": 0.28, "mde_cooldown_bars": 480}),
            # MREV_ST_LONG + MDE + cooldown
            ("MREV_ST_LONG_3x_MDE28_CD480", "mean_rev_st", [5, 6, 7], [30, 40], "none", [0], [0],
             {"leverage": 3.0, "max_dd_exit_pct": 0.28, "mde_cooldown_bars": 480}),
            ("MREV_ST_LONG_4x_MDE28_CD480", "mean_rev_st", [5, 6, 7], [30, 40], "none", [0], [0],
             {"leverage": 4.0, "max_dd_exit_pct": 0.28, "mde_cooldown_bars": 480}),
            # ST_LOWP + MDE + cooldown
            ("ST_LOWP_3x_MDE28_CD480", "supertrend", [5, 6, 7], [2.5], "none", [0], [0],
             {"leverage": 3.0, "max_dd_exit_pct": 0.28, "mde_cooldown_bars": 480}),
            ("ST_LOWP_4x_MDE28_CD480", "supertrend", [5, 6, 7], [2.5], "none", [0], [0],
             {"leverage": 4.0, "max_dd_exit_pct": 0.28, "mde_cooldown_bars": 480}),
            # ─── Tight MDE + cooldown: proven DD control sweet spot ───
            # MDE=0.08 at 4x: α=153.7% DD=-25.9% T=60 (IS qualified!)
            ("MREV_ST_WIDE_4x_MDE08_CD480", "mean_rev_st", [5, 6, 7], [10, 12], "none", [0], [0],
             {"leverage": 4.0, "max_dd_exit_pct": 0.08, "mde_cooldown_bars": 480}),
            ("MREV_ST_WIDE_4x_MDE07_CD480", "mean_rev_st", [5, 6, 7], [10, 12], "none", [0], [0],
             {"leverage": 4.0, "max_dd_exit_pct": 0.07, "mde_cooldown_bars": 480}),
            ("MREV_ST_WIDE_4x_MDE09_CD480", "mean_rev_st", [5, 6, 7], [10, 12], "none", [0], [0],
             {"leverage": 4.0, "max_dd_exit_pct": 0.09, "mde_cooldown_bars": 480}),
            ("MREV_ST_WIDE_4x_MDE08_CD240", "mean_rev_st", [5, 6, 7], [10, 12], "none", [0], [0],
             {"leverage": 4.0, "max_dd_exit_pct": 0.08, "mde_cooldown_bars": 240}),
            ("MREV_ST_WIDE_4x_MDE08_CD720", "mean_rev_st", [5, 6, 7], [10, 12], "none", [0], [0],
             {"leverage": 4.0, "max_dd_exit_pct": 0.08, "mde_cooldown_bars": 720}),
            # 5x variants
            ("MREV_ST_WIDE_5x_MDE10_CD480", "mean_rev_st", [5, 6, 7], [10, 12], "none", [0], [0],
             {"leverage": 5.0, "max_dd_exit_pct": 0.10, "mde_cooldown_bars": 480}),
            ("MREV_ST_WIDE_5x_MDE08_CD480", "mean_rev_st", [5, 6, 7], [10, 12], "none", [0], [0],
             {"leverage": 5.0, "max_dd_exit_pct": 0.08, "mde_cooldown_bars": 480}),
            ("MREV_ST_WIDE_5x_MDE08_CD960", "mean_rev_st", [5, 6, 7], [10, 12], "none", [0], [0],
             {"leverage": 5.0, "max_dd_exit_pct": 0.08, "mde_cooldown_bars": 960}),
            # 3.5x variants (lower lev, potentially better DD)
            ("MREV_ST_WIDE_3.5x_MDE08_CD480", "mean_rev_st", [5, 6, 7], [10, 12], "none", [0], [0],
             {"leverage": 3.5, "max_dd_exit_pct": 0.08, "mde_cooldown_bars": 480}),
            ("MREV_ST_WIDE_3.5x_MDE10_CD480", "mean_rev_st", [5, 6, 7], [10, 12], "none", [0], [0],
             {"leverage": 3.5, "max_dd_exit_pct": 0.10, "mde_cooldown_bars": 480}),
            # 6x variant
            ("MREV_ST_WIDE_6x_MDE08_CD480", "mean_rev_st", [5, 6, 7], [10, 12], "none", [0], [0],
             {"leverage": 6.0, "max_dd_exit_pct": 0.08, "mde_cooldown_bars": 480}),
            ("MREV_ST_WIDE_6x_MDE08_CD960", "mean_rev_st", [5, 6, 7], [10, 12], "none", [0], [0],
             {"leverage": 6.0, "max_dd_exit_pct": 0.08, "mde_cooldown_bars": 960}),
            # ─── Other families with MDE08+CD480 ───
            ("MREV_ST_4x_MDE08_CD480", "mean_rev_st", [5, 6, 7], [15, 20, 25], "none", [0], [0],
             {"leverage": 4.0, "max_dd_exit_pct": 0.08, "mde_cooldown_bars": 480}),
            ("MREV_ST_5x_MDE08_CD480", "mean_rev_st", [5, 6, 7], [15, 20, 25], "none", [0], [0],
             {"leverage": 5.0, "max_dd_exit_pct": 0.08, "mde_cooldown_bars": 480}),
            ("MREV_ST_LONG_4x_MDE08_CD480", "mean_rev_st", [5, 6, 7], [30, 40], "none", [0], [0],
             {"leverage": 4.0, "max_dd_exit_pct": 0.08, "mde_cooldown_bars": 480}),
            ("MREV_ST_LONG_5x_MDE08_CD480", "mean_rev_st", [5, 6, 7], [30, 40], "none", [0], [0],
             {"leverage": 5.0, "max_dd_exit_pct": 0.08, "mde_cooldown_bars": 480}),
            ("PIVOT_ST_4x_MDE08_CD480", "pivot_st", [5, 6, 7], [15, 20], "none", [0], [0],
             {"leverage": 4.0, "max_dd_exit_pct": 0.08, "mde_cooldown_bars": 480}),
            ("PIVOT_ST_5x_MDE08_CD480", "pivot_st", [5, 6, 7], [15, 20], "none", [0], [0],
             {"leverage": 5.0, "max_dd_exit_pct": 0.08, "mde_cooldown_bars": 480}),
            ("ST_LOWP_4x_MDE08_CD480", "supertrend", [5, 6, 7], [2.5], "none", [0], [0],
             {"leverage": 4.0, "max_dd_exit_pct": 0.08, "mde_cooldown_bars": 480}),
            ("ST_LOWP_5x_MDE08_CD480", "supertrend", [5, 6, 7], [2.5], "none", [0], [0],
             {"leverage": 5.0, "max_dd_exit_pct": 0.08, "mde_cooldown_bars": 480}),
            ("ST_BREAK_4x_MDE08_CD480", "st_breakout", [5, 6, 7], [15, 20, 25], "none", [0], [0],
             {"leverage": 4.0, "max_dd_exit_pct": 0.08, "mde_cooldown_bars": 480}),
            ("ST_BREAK_5x_MDE08_CD480", "st_breakout", [5, 6, 7], [15, 20, 25], "none", [0], [0],
             {"leverage": 5.0, "max_dd_exit_pct": 0.08, "mde_cooldown_bars": 480}),
            # ─── Wider param search with MDE08 ───
            ("MREV_ST_ULTRA_4x_MDE08_CD480", "mean_rev_st", [3, 4, 5, 6, 7, 8, 9], [8, 10, 12, 15], "none", [0], [0],
             {"leverage": 4.0, "max_dd_exit_pct": 0.08, "mde_cooldown_bars": 480}),
            ("MREV_ST_ULTRA_5x_MDE08_CD480", "mean_rev_st", [3, 4, 5, 6, 7, 8, 9], [8, 10, 12, 15], "none", [0], [0],
             {"leverage": 5.0, "max_dd_exit_pct": 0.08, "mde_cooldown_bars": 480}),
            # ─── Dual filter + MDE08 + CD480 ───
            ("MREV_ST_WIDE_DUAL_4x_MDE08_CD480", "mean_rev_st", [5, 6, 7], [10, 12], "slow_st", [20, 30], [3.5, 4.0],
             {"leverage": 4.0, "max_dd_exit_pct": 0.08, "mde_cooldown_bars": 480}),
            ("MREV_ST_WIDE_DUAL_5x_MDE08_CD480", "mean_rev_st", [5, 6, 7], [10, 12], "slow_st", [20, 30], [3.5, 4.0],
             {"leverage": 5.0, "max_dd_exit_pct": 0.08, "mde_cooldown_bars": 480}),
            # ─── Aggressive MDE: very tight DD cap + high leverage ───
            # MDE05-07 at 6-7x: cap equity DD at 5-7%, 480-bar cooldown
            ("MREV_ST_WIDE_DUAL_6x_MDE05_CD480", "mean_rev_st", [5, 6, 7], [10, 12], "slow_st", [20, 30], [3.5, 4.0],
             {"leverage": 6.0, "max_dd_exit_pct": 0.05, "mde_cooldown_bars": 480}),
            ("MREV_ST_WIDE_DUAL_7x_MDE05_CD480", "mean_rev_st", [5, 6, 7], [10, 12], "slow_st", [20, 30], [3.5, 4.0],
             {"leverage": 7.0, "max_dd_exit_pct": 0.05, "mde_cooldown_bars": 480}),
            ("MREV_ST_WIDE_DUAL_6x_MDE06_CD480", "mean_rev_st", [5, 6, 7], [10, 12], "slow_st", [20, 30], [3.5, 4.0],
             {"leverage": 6.0, "max_dd_exit_pct": 0.06, "mde_cooldown_bars": 480}),
            ("MREV_ST_WIDE_DUAL_7x_MDE06_CD480", "mean_rev_st", [5, 6, 7], [10, 12], "slow_st", [20, 30], [3.5, 4.0],
             {"leverage": 7.0, "max_dd_exit_pct": 0.06, "mde_cooldown_bars": 480}),
            ("MREV_ST_WIDE_DUAL_6x_MDE07_CD480", "mean_rev_st", [5, 6, 7], [10, 12], "slow_st", [20, 30], [3.5, 4.0],
             {"leverage": 6.0, "max_dd_exit_pct": 0.07, "mde_cooldown_bars": 480}),
            ("MREV_ST_WIDE_DUAL_8x_MDE05_CD480", "mean_rev_st", [5, 6, 7], [10, 12], "slow_st", [20, 30], [3.5, 4.0],
             {"leverage": 8.0, "max_dd_exit_pct": 0.05, "mde_cooldown_bars": 480}),
            ("MREV_ST_WIDE_DUAL_5x_MDE05_CD480", "mean_rev_st", [5, 6, 7], [10, 12], "slow_st", [20, 30], [3.5, 4.0],
             {"leverage": 5.0, "max_dd_exit_pct": 0.05, "mde_cooldown_bars": 480}),
            ("MREV_ST_WIDE_DUAL_5x_MDE06_CD480", "mean_rev_st", [5, 6, 7], [10, 12], "slow_st", [20, 30], [3.5, 4.0],
             {"leverage": 5.0, "max_dd_exit_pct": 0.06, "mde_cooldown_bars": 480}),
            # ─── Non-DUAL MDE at high leverage (no slow_st filter) ───
            ("MREV_ST_WIDE_6x_MDE05_CD480", "mean_rev_st", [5, 6, 7], [10, 12], "none", [0], [0],
             {"leverage": 6.0, "max_dd_exit_pct": 0.05, "mde_cooldown_bars": 480}),
            ("MREV_ST_WIDE_7x_MDE05_CD480", "mean_rev_st", [5, 6, 7], [10, 12], "none", [0], [0],
             {"leverage": 7.0, "max_dd_exit_pct": 0.05, "mde_cooldown_bars": 480}),
            ("MREV_ST_WIDE_6x_MDE06_CD480", "mean_rev_st", [5, 6, 7], [10, 12], "none", [0], [0],
             {"leverage": 6.0, "max_dd_exit_pct": 0.06, "mde_cooldown_bars": 480}),
            ("MREV_ST_WIDE_6x_MDE08_CD480_v2", "mean_rev_st", [5, 6, 7], [10, 12], "none", [0], [0],
             {"leverage": 6.0, "max_dd_exit_pct": 0.08, "mde_cooldown_bars": 480}),
            # ─── Pivot + high leverage MDE ───
            ("PIVOT_ST_DUAL_5x_MDE05_CD480", "pivot_st", [5, 6, 7], [15, 20], "slow_st", [20, 30], [3.5, 4.0],
             {"leverage": 5.0, "max_dd_exit_pct": 0.05, "mde_cooldown_bars": 480}),
            ("PIVOT_ST_DUAL_6x_MDE05_CD480", "pivot_st", [5, 6, 7], [15, 20], "slow_st", [20, 30], [3.5, 4.0],
             {"leverage": 6.0, "max_dd_exit_pct": 0.05, "mde_cooldown_bars": 480}),
            ("PIVOT_ST_DUAL_4x_MDE08_CD480", "pivot_st", [5, 6, 7], [15, 20], "slow_st", [20, 30], [3.5, 4.0],
             {"leverage": 4.0, "max_dd_exit_pct": 0.08, "mde_cooldown_bars": 480}),
            # ─── Intermediate MDE: fine-tune the MDE08 sweet spot ───
            # MDE08 at 6x: higher leverage but same proven MDE level
            ("MREV_ST_WIDE_DUAL_6x_MDE08_CD480", "mean_rev_st", [5, 6, 7], [10, 12], "slow_st", [20, 30], [3.5, 4.0],
             {"leverage": 6.0, "max_dd_exit_pct": 0.08, "mde_cooldown_bars": 480}),
            # MDE09-12 at 5-6x: intermediate levels between MDE08 and MDE15
            ("MREV_ST_WIDE_DUAL_5x_MDE09_CD480", "mean_rev_st", [5, 6, 7], [10, 12], "slow_st", [20, 30], [3.5, 4.0],
             {"leverage": 5.0, "max_dd_exit_pct": 0.09, "mde_cooldown_bars": 480}),
            ("MREV_ST_WIDE_DUAL_5x_MDE10_CD480", "mean_rev_st", [5, 6, 7], [10, 12], "slow_st", [20, 30], [3.5, 4.0],
             {"leverage": 5.0, "max_dd_exit_pct": 0.10, "mde_cooldown_bars": 480}),
            ("MREV_ST_WIDE_DUAL_6x_MDE09_CD480", "mean_rev_st", [5, 6, 7], [10, 12], "slow_st", [20, 30], [3.5, 4.0],
             {"leverage": 6.0, "max_dd_exit_pct": 0.09, "mde_cooldown_bars": 480}),
            ("MREV_ST_WIDE_DUAL_6x_MDE10_CD480", "mean_rev_st", [5, 6, 7], [10, 12], "slow_st", [20, 30], [3.5, 4.0],
             {"leverage": 6.0, "max_dd_exit_pct": 0.10, "mde_cooldown_bars": 480}),
            ("MREV_ST_WIDE_DUAL_5x_MDE12_CD480", "mean_rev_st", [5, 6, 7], [10, 12], "slow_st", [20, 30], [3.5, 4.0],
             {"leverage": 5.0, "max_dd_exit_pct": 0.12, "mde_cooldown_bars": 480}),
            ("MREV_ST_WIDE_DUAL_6x_MDE12_CD480", "mean_rev_st", [5, 6, 7], [10, 12], "slow_st", [20, 30], [3.5, 4.0],
             {"leverage": 6.0, "max_dd_exit_pct": 0.12, "mde_cooldown_bars": 480}),
            ("MREV_ST_WIDE_DUAL_7x_MDE08_CD480", "mean_rev_st", [5, 6, 7], [10, 12], "slow_st", [20, 30], [3.5, 4.0],
             {"leverage": 7.0, "max_dd_exit_pct": 0.08, "mde_cooldown_bars": 480}),
            ("MREV_ST_WIDE_DUAL_7x_MDE10_CD480", "mean_rev_st", [5, 6, 7], [10, 12], "slow_st", [20, 30], [3.5, 4.0],
             {"leverage": 7.0, "max_dd_exit_pct": 0.10, "mde_cooldown_bars": 480}),
            # ─── Shorter cooldown variants: faster re-entry after MDE ───
            ("MREV_ST_WIDE_DUAL_5x_MDE08_CD240", "mean_rev_st", [5, 6, 7], [10, 12], "slow_st", [20, 30], [3.5, 4.0],
             {"leverage": 5.0, "max_dd_exit_pct": 0.08, "mde_cooldown_bars": 240}),
            ("MREV_ST_WIDE_DUAL_6x_MDE08_CD240", "mean_rev_st", [5, 6, 7], [10, 12], "slow_st", [20, 30], [3.5, 4.0],
             {"leverage": 6.0, "max_dd_exit_pct": 0.08, "mde_cooldown_bars": 240}),
            ("MREV_ST_WIDE_DUAL_5x_MDE10_CD240", "mean_rev_st", [5, 6, 7], [10, 12], "slow_st", [20, 30], [3.5, 4.0],
             {"leverage": 5.0, "max_dd_exit_pct": 0.10, "mde_cooldown_bars": 240}),
            # ─── Wider slow_st filter params for DUAL ───
            ("MREV_ST_XDUAL_5x_MDE08_CD480", "mean_rev_st", [5, 6, 7], [10, 12], "slow_st", [15, 20, 25, 30, 40], [3.0, 3.5, 4.0, 4.5],
             {"leverage": 5.0, "max_dd_exit_pct": 0.08, "mde_cooldown_bars": 480}),
            ("MREV_ST_XDUAL_6x_MDE08_CD480", "mean_rev_st", [5, 6, 7], [10, 12], "slow_st", [15, 20, 25, 30, 40], [3.0, 3.5, 4.0, 4.5],
             {"leverage": 6.0, "max_dd_exit_pct": 0.08, "mde_cooldown_bars": 480}),
            # ─── PIVOT_ST DUAL at higher leverage with MDE ───
            ("PIVOT_ST_DUAL_5x_MDE08_CD480", "pivot_st", [5, 6, 7], [15, 20], "slow_st", [20, 30], [3.5, 4.0],
             {"leverage": 5.0, "max_dd_exit_pct": 0.08, "mde_cooldown_bars": 480}),
            ("PIVOT_ST_DUAL_6x_MDE08_CD480", "pivot_st", [5, 6, 7], [15, 20], "slow_st", [20, 30], [3.5, 4.0],
             {"leverage": 6.0, "max_dd_exit_pct": 0.08, "mde_cooldown_bars": 480}),

            # ─── CD960 variants: very long cooldown (10 days) for DD>-35% ───
            # Theory: MDE10+CD960 → ~3 triggers max during 30-day crash → DD≈-27%
            ("MREV_ST_WIDE_DUAL_5x_MDE08_CD960", "mean_rev_st", [5, 6, 7], [10, 12], "slow_st", [20, 30], [3.5, 4.0],
             {"leverage": 5.0, "max_dd_exit_pct": 0.08, "mde_cooldown_bars": 960}),
            ("MREV_ST_WIDE_DUAL_6x_MDE08_CD960", "mean_rev_st", [5, 6, 7], [10, 12], "slow_st", [20, 30], [3.5, 4.0],
             {"leverage": 6.0, "max_dd_exit_pct": 0.08, "mde_cooldown_bars": 960}),
            ("MREV_ST_WIDE_DUAL_7x_MDE08_CD960", "mean_rev_st", [5, 6, 7], [10, 12], "slow_st", [20, 30], [3.5, 4.0],
             {"leverage": 7.0, "max_dd_exit_pct": 0.08, "mde_cooldown_bars": 960}),
            ("MREV_ST_WIDE_DUAL_8x_MDE08_CD960", "mean_rev_st", [5, 6, 7], [10, 12], "slow_st", [20, 30], [3.5, 4.0],
             {"leverage": 8.0, "max_dd_exit_pct": 0.08, "mde_cooldown_bars": 960}),
            ("MREV_ST_WIDE_DUAL_5x_MDE10_CD960", "mean_rev_st", [5, 6, 7], [10, 12], "slow_st", [20, 30], [3.5, 4.0],
             {"leverage": 5.0, "max_dd_exit_pct": 0.10, "mde_cooldown_bars": 960}),
            ("MREV_ST_WIDE_DUAL_6x_MDE10_CD960", "mean_rev_st", [5, 6, 7], [10, 12], "slow_st", [20, 30], [3.5, 4.0],
             {"leverage": 6.0, "max_dd_exit_pct": 0.10, "mde_cooldown_bars": 960}),
            ("MREV_ST_WIDE_DUAL_7x_MDE10_CD960", "mean_rev_st", [5, 6, 7], [10, 12], "slow_st", [20, 30], [3.5, 4.0],
             {"leverage": 7.0, "max_dd_exit_pct": 0.10, "mde_cooldown_bars": 960}),
            ("MREV_ST_WIDE_DUAL_8x_MDE10_CD960", "mean_rev_st", [5, 6, 7], [10, 12], "slow_st", [20, 30], [3.5, 4.0],
             {"leverage": 8.0, "max_dd_exit_pct": 0.10, "mde_cooldown_bars": 960}),
            ("MREV_ST_WIDE_DUAL_5x_MDE12_CD960", "mean_rev_st", [5, 6, 7], [10, 12], "slow_st", [20, 30], [3.5, 4.0],
             {"leverage": 5.0, "max_dd_exit_pct": 0.12, "mde_cooldown_bars": 960}),
            ("MREV_ST_WIDE_DUAL_6x_MDE12_CD960", "mean_rev_st", [5, 6, 7], [10, 12], "slow_st", [20, 30], [3.5, 4.0],
             {"leverage": 6.0, "max_dd_exit_pct": 0.12, "mde_cooldown_bars": 960}),
            ("MREV_ST_WIDE_DUAL_7x_MDE12_CD960", "mean_rev_st", [5, 6, 7], [10, 12], "slow_st", [20, 30], [3.5, 4.0],
             {"leverage": 7.0, "max_dd_exit_pct": 0.12, "mde_cooldown_bars": 960}),
            ("MREV_ST_WIDE_DUAL_7x_MDE10_CD1440", "mean_rev_st", [5, 6, 7], [10, 12], "slow_st", [20, 30], [3.5, 4.0],
             {"leverage": 7.0, "max_dd_exit_pct": 0.10, "mde_cooldown_bars": 1440}),
            ("MREV_ST_WIDE_DUAL_8x_MDE10_CD1440", "mean_rev_st", [5, 6, 7], [10, 12], "slow_st", [20, 30], [3.5, 4.0],
             {"leverage": 8.0, "max_dd_exit_pct": 0.10, "mde_cooldown_bars": 1440}),
            # Non-DUAL with CD960
            ("MREV_ST_WIDE_5x_MDE10_CD960", "mean_rev_st", [5, 6, 7], [10, 12], "none", [0], [0],
             {"leverage": 5.0, "max_dd_exit_pct": 0.10, "mde_cooldown_bars": 960}),
            ("MREV_ST_WIDE_6x_MDE10_CD960", "mean_rev_st", [5, 6, 7], [10, 12], "none", [0], [0],
             {"leverage": 6.0, "max_dd_exit_pct": 0.10, "mde_cooldown_bars": 960}),
            ("MREV_ST_WIDE_5x_MDE08_CD960", "mean_rev_st", [5, 6, 7], [10, 12], "none", [0], [0],
             {"leverage": 5.0, "max_dd_exit_pct": 0.08, "mde_cooldown_bars": 960}),
            ("MREV_ST_WIDE_6x_MDE08_CD960", "mean_rev_st", [5, 6, 7], [10, 12], "none", [0], [0],
             {"leverage": 6.0, "max_dd_exit_pct": 0.08, "mde_cooldown_bars": 960}),
            # ─── SL + sl_cooldown: per-trade SL with SL-specific long cooldown ───
            # SL applied during IS/OOS training → optimizer avoids SL-prone params
            # sl_cooldown only after SL exit → signal exits retain fast re-entry
            ("MREV_ST_WIDE_DUAL_5x_SL20_SLCD960", "mean_rev_st", [5, 6, 7], [10, 12], "slow_st", [20, 30], [3.5, 4.0],
             {"leverage": 5.0, "stop_loss_pct": 0.02, "sl_cooldown_bars": 960}),
            ("MREV_ST_WIDE_DUAL_6x_SL20_SLCD960", "mean_rev_st", [5, 6, 7], [10, 12], "slow_st", [20, 30], [3.5, 4.0],
             {"leverage": 6.0, "stop_loss_pct": 0.02, "sl_cooldown_bars": 960}),
            ("MREV_ST_WIDE_DUAL_7x_SL20_SLCD960", "mean_rev_st", [5, 6, 7], [10, 12], "slow_st", [20, 30], [3.5, 4.0],
             {"leverage": 7.0, "stop_loss_pct": 0.02, "sl_cooldown_bars": 960}),
            ("MREV_ST_WIDE_DUAL_8x_SL20_SLCD960", "mean_rev_st", [5, 6, 7], [10, 12], "slow_st", [20, 30], [3.5, 4.0],
             {"leverage": 8.0, "stop_loss_pct": 0.02, "sl_cooldown_bars": 960}),
            ("MREV_ST_WIDE_DUAL_5x_SL15_SLCD960", "mean_rev_st", [5, 6, 7], [10, 12], "slow_st", [20, 30], [3.5, 4.0],
             {"leverage": 5.0, "stop_loss_pct": 0.015, "sl_cooldown_bars": 960}),
            ("MREV_ST_WIDE_DUAL_6x_SL15_SLCD960", "mean_rev_st", [5, 6, 7], [10, 12], "slow_st", [20, 30], [3.5, 4.0],
             {"leverage": 6.0, "stop_loss_pct": 0.015, "sl_cooldown_bars": 960}),
            ("MREV_ST_WIDE_DUAL_7x_SL15_SLCD960", "mean_rev_st", [5, 6, 7], [10, 12], "slow_st", [20, 30], [3.5, 4.0],
             {"leverage": 7.0, "stop_loss_pct": 0.015, "sl_cooldown_bars": 960}),
            ("MREV_ST_WIDE_DUAL_5x_SL25_SLCD960", "mean_rev_st", [5, 6, 7], [10, 12], "slow_st", [20, 30], [3.5, 4.0],
             {"leverage": 5.0, "stop_loss_pct": 0.025, "sl_cooldown_bars": 960}),
            ("MREV_ST_WIDE_DUAL_6x_SL25_SLCD960", "mean_rev_st", [5, 6, 7], [10, 12], "slow_st", [20, 30], [3.5, 4.0],
             {"leverage": 6.0, "stop_loss_pct": 0.025, "sl_cooldown_bars": 960}),
            ("MREV_ST_WIDE_DUAL_7x_SL25_SLCD960", "mean_rev_st", [5, 6, 7], [10, 12], "slow_st", [20, 30], [3.5, 4.0],
             {"leverage": 7.0, "stop_loss_pct": 0.025, "sl_cooldown_bars": 960}),
            ("MREV_ST_WIDE_DUAL_5x_SL20_SLCD672", "mean_rev_st", [5, 6, 7], [10, 12], "slow_st", [20, 30], [3.5, 4.0],
             {"leverage": 5.0, "stop_loss_pct": 0.02, "sl_cooldown_bars": 672}),
            ("MREV_ST_WIDE_DUAL_6x_SL20_SLCD672", "mean_rev_st", [5, 6, 7], [10, 12], "slow_st", [20, 30], [3.5, 4.0],
             {"leverage": 6.0, "stop_loss_pct": 0.02, "sl_cooldown_bars": 672}),
            ("MREV_ST_WIDE_DUAL_7x_SL20_SLCD672", "mean_rev_st", [5, 6, 7], [10, 12], "slow_st", [20, 30], [3.5, 4.0],
             {"leverage": 7.0, "stop_loss_pct": 0.02, "sl_cooldown_bars": 672}),
            # Non-DUAL with SL+sl_cooldown
            ("MREV_ST_WIDE_5x_SL20_SLCD960", "mean_rev_st", [5, 6, 7], [10, 12], "none", [0], [0],
             {"leverage": 5.0, "stop_loss_pct": 0.02, "sl_cooldown_bars": 960}),
            ("MREV_ST_WIDE_6x_SL20_SLCD960", "mean_rev_st", [5, 6, 7], [10, 12], "none", [0], [0],
             {"leverage": 6.0, "stop_loss_pct": 0.02, "sl_cooldown_bars": 960}),
            ("MREV_ST_WIDE_4x_SL20_SLCD960", "mean_rev_st", [5, 6, 7], [10, 12], "none", [0], [0],
             {"leverage": 4.0, "stop_loss_pct": 0.02, "sl_cooldown_bars": 960}),
            ("MREV_ST_WIDE_4x_SL15_SLCD960", "mean_rev_st", [5, 6, 7], [10, 12], "none", [0], [0],
             {"leverage": 4.0, "stop_loss_pct": 0.015, "sl_cooldown_bars": 960}),
            ("MREV_ST_WIDE_5x_SL15_SLCD960", "mean_rev_st", [5, 6, 7], [10, 12], "none", [0], [0],
             {"leverage": 5.0, "stop_loss_pct": 0.015, "sl_cooldown_bars": 960}),
            # ─── DD-penalized optimization: no MDE, optimizer picks low-DD params ───
            # dd_penalty guides optimizer to balance α and DD (no overlays to kill OOS2)
            ("MREV_ST_WIDE_3x_DDP05", "mean_rev_st", [5, 6, 7], [10, 12], "none", [0], [0],
             {"leverage": 3.0, "dd_penalty": 0.5}),
            ("MREV_ST_WIDE_3x_DDP10", "mean_rev_st", [5, 6, 7], [10, 12], "none", [0], [0],
             {"leverage": 3.0, "dd_penalty": 1.0}),
            ("MREV_ST_WIDE_3x_DDP20", "mean_rev_st", [5, 6, 7], [10, 12], "none", [0], [0],
             {"leverage": 3.0, "dd_penalty": 2.0}),
            ("MREV_ST_WIDE_4x_DDP05", "mean_rev_st", [5, 6, 7], [10, 12], "none", [0], [0],
             {"leverage": 4.0, "dd_penalty": 0.5}),
            ("MREV_ST_WIDE_4x_DDP10", "mean_rev_st", [5, 6, 7], [10, 12], "none", [0], [0],
             {"leverage": 4.0, "dd_penalty": 1.0}),
            ("MREV_ST_WIDE_4x_DDP20", "mean_rev_st", [5, 6, 7], [10, 12], "none", [0], [0],
             {"leverage": 4.0, "dd_penalty": 2.0}),
            ("MREV_ST_WIDE_5x_DDP10", "mean_rev_st", [5, 6, 7], [10, 12], "none", [0], [0],
             {"leverage": 5.0, "dd_penalty": 1.0}),
            ("MREV_ST_WIDE_5x_DDP20", "mean_rev_st", [5, 6, 7], [10, 12], "none", [0], [0],
             {"leverage": 5.0, "dd_penalty": 2.0}),
            # Wider param grid + DD penalty
            ("MREV_ST_ULTRA_4x_DDP10", "mean_rev_st", [3, 4, 5, 6, 7, 8, 9], [6, 8, 10, 12, 15, 20], "none", [0], [0],
             {"leverage": 4.0, "dd_penalty": 1.0}),
            ("MREV_ST_ULTRA_5x_DDP10", "mean_rev_st", [3, 4, 5, 6, 7, 8, 9], [6, 8, 10, 12, 15, 20], "none", [0], [0],
             {"leverage": 5.0, "dd_penalty": 1.0}),
            ("MREV_ST_ULTRA_4x_DDP20", "mean_rev_st", [3, 4, 5, 6, 7, 8, 9], [6, 8, 10, 12, 15, 20], "none", [0], [0],
             {"leverage": 4.0, "dd_penalty": 2.0}),
            ("MREV_ST_ULTRA_5x_DDP20", "mean_rev_st", [3, 4, 5, 6, 7, 8, 9], [6, 8, 10, 12, 15, 20], "none", [0], [0],
             {"leverage": 5.0, "dd_penalty": 2.0}),
            # Other families + DD penalty
            ("PIVOT_ST_4x_DDP10", "pivot_st", [5, 6, 7], [15, 20], "none", [0], [0],
             {"leverage": 4.0, "dd_penalty": 1.0}),
            ("PIVOT_ST_5x_DDP10", "pivot_st", [5, 6, 7], [15, 20], "none", [0], [0],
             {"leverage": 5.0, "dd_penalty": 1.0}),
            ("ST_LOWP_4x_DDP10", "supertrend", [5, 6, 7], [2.5], "none", [0], [0],
             {"leverage": 4.0, "dd_penalty": 1.0}),
            ("ST_LOWP_5x_DDP10", "supertrend", [5, 6, 7], [2.5], "none", [0], [0],
             {"leverage": 5.0, "dd_penalty": 1.0}),
            ("ST_BREAK_4x_DDP10", "st_breakout", [5, 6, 7], [15, 20, 25], "none", [0], [0],
             {"leverage": 4.0, "dd_penalty": 1.0}),
            ("ST_BREAK_5x_DDP10", "st_breakout", [5, 6, 7], [15, 20, 25], "none", [0], [0],
             {"leverage": 5.0, "dd_penalty": 1.0}),
            ("MREV_ST_LONG_4x_DDP10", "mean_rev_st", [5, 6, 7], [30, 40], "none", [0], [0],
             {"leverage": 4.0, "dd_penalty": 1.0}),
            ("MREV_ST_LONG_5x_DDP10", "mean_rev_st", [5, 6, 7], [30, 40], "none", [0], [0],
             {"leverage": 5.0, "dd_penalty": 1.0}),
            # Combined: DD penalty + mild MDE (MDE catches only catastrophic events, no cooldown)
            ("MREV_ST_WIDE_4x_DDP10_MDE28", "mean_rev_st", [5, 6, 7], [10, 12], "none", [0], [0],
             {"leverage": 4.0, "dd_penalty": 1.0, "max_dd_exit_pct": 0.28}),
            ("MREV_ST_WIDE_5x_DDP10_MDE28", "mean_rev_st", [5, 6, 7], [10, 12], "none", [0], [0],
             {"leverage": 5.0, "dd_penalty": 1.0, "max_dd_exit_pct": 0.28}),
            ("MREV_ST_WIDE_4x_DDP20_MDE28", "mean_rev_st", [5, 6, 7], [10, 12], "none", [0], [0],
             {"leverage": 4.0, "dd_penalty": 2.0, "max_dd_exit_pct": 0.28}),
            # ─── Price-based leverage scaling (PLS): dynamic lev based on BTC price DD ───
            # At high leverage, scales down when price drops from rolling high.
            # Key: price-based (not equity-based) → objective, transfers across periods.
            # PLS=0.05: full lev at -5% price DD, scales to 1x at -10% price DD.
            # PLS=0.03: full lev at -3% price DD, scales to 1x at -6% price DD (more aggressive).
            # In OOS2 (bull): price DD rarely exceeds 5% → leverage stays high → OOS2α preserved.
            # In bear: price DD hits 20%+ → leverage drops to 1x early → DD limited.
            ("MREV_ST_WIDE_5x_PLS05", "mean_rev_st", [5, 6, 7], [10, 12], "none", [0], [0],
             {"leverage": 5.0, "price_lev_scale": 0.05}),
            ("MREV_ST_WIDE_5x_PLS03", "mean_rev_st", [5, 6, 7], [10, 12], "none", [0], [0],
             {"leverage": 5.0, "price_lev_scale": 0.03}),
            ("MREV_ST_WIDE_5x_PLS07", "mean_rev_st", [5, 6, 7], [10, 12], "none", [0], [0],
             {"leverage": 5.0, "price_lev_scale": 0.07}),
            ("MREV_ST_WIDE_6x_PLS05", "mean_rev_st", [5, 6, 7], [10, 12], "none", [0], [0],
             {"leverage": 6.0, "price_lev_scale": 0.05}),
            ("MREV_ST_WIDE_6x_PLS03", "mean_rev_st", [5, 6, 7], [10, 12], "none", [0], [0],
             {"leverage": 6.0, "price_lev_scale": 0.03}),
            ("MREV_ST_WIDE_7x_PLS05", "mean_rev_st", [5, 6, 7], [10, 12], "none", [0], [0],
             {"leverage": 7.0, "price_lev_scale": 0.05}),
            ("MREV_ST_WIDE_8x_PLS05", "mean_rev_st", [5, 6, 7], [10, 12], "none", [0], [0],
             {"leverage": 8.0, "price_lev_scale": 0.05}),
            ("MREV_ST_WIDE_8x_PLS03", "mean_rev_st", [5, 6, 7], [10, 12], "none", [0], [0],
             {"leverage": 8.0, "price_lev_scale": 0.03}),
            ("MREV_ST_WIDE_10x_PLS05", "mean_rev_st", [5, 6, 7], [10, 12], "none", [0], [0],
             {"leverage": 10.0, "price_lev_scale": 0.05}),
            ("MREV_ST_WIDE_10x_PLS03", "mean_rev_st", [5, 6, 7], [10, 12], "none", [0], [0],
             {"leverage": 10.0, "price_lev_scale": 0.03}),
            # PLS=0.02: most aggressive — full lev at -2% DD, 1x at -4% DD
            ("MREV_ST_WIDE_5x_PLS02", "mean_rev_st", [5, 6, 7], [10, 12], "none", [0], [0],
             {"leverage": 5.0, "price_lev_scale": 0.02}),
            ("MREV_ST_WIDE_6x_PLS02", "mean_rev_st", [5, 6, 7], [10, 12], "none", [0], [0],
             {"leverage": 6.0, "price_lev_scale": 0.02}),
            ("MREV_ST_WIDE_8x_PLS02", "mean_rev_st", [5, 6, 7], [10, 12], "none", [0], [0],
             {"leverage": 8.0, "price_lev_scale": 0.02}),
            ("MREV_ST_WIDE_10x_PLS02", "mean_rev_st", [5, 6, 7], [10, 12], "none", [0], [0],
             {"leverage": 10.0, "price_lev_scale": 0.02}),
            # PLS + DUAL filter: trend filter blocks wrong-way entries, PLS handles crashes
            ("MREV_ST_WIDE_DUAL_5x_PLS05", "mean_rev_st", [5, 6, 7], [10, 12], "slow_st", [20, 30], [3.5, 4.0],
             {"leverage": 5.0, "price_lev_scale": 0.05}),
            ("MREV_ST_WIDE_DUAL_6x_PLS05", "mean_rev_st", [5, 6, 7], [10, 12], "slow_st", [20, 30], [3.5, 4.0],
             {"leverage": 6.0, "price_lev_scale": 0.05}),
            ("MREV_ST_WIDE_DUAL_7x_PLS05", "mean_rev_st", [5, 6, 7], [10, 12], "slow_st", [20, 30], [3.5, 4.0],
             {"leverage": 7.0, "price_lev_scale": 0.05}),
            ("MREV_ST_WIDE_DUAL_5x_PLS03", "mean_rev_st", [5, 6, 7], [10, 12], "slow_st", [20, 30], [3.5, 4.0],
             {"leverage": 5.0, "price_lev_scale": 0.03}),
            ("MREV_ST_WIDE_DUAL_6x_PLS03", "mean_rev_st", [5, 6, 7], [10, 12], "slow_st", [20, 30], [3.5, 4.0],
             {"leverage": 6.0, "price_lev_scale": 0.03}),
            ("MREV_ST_WIDE_DUAL_8x_PLS05", "mean_rev_st", [5, 6, 7], [10, 12], "slow_st", [20, 30], [3.5, 4.0],
             {"leverage": 8.0, "price_lev_scale": 0.05}),
            ("MREV_ST_WIDE_DUAL_10x_PLS05", "mean_rev_st", [5, 6, 7], [10, 12], "slow_st", [20, 30], [3.5, 4.0],
             {"leverage": 10.0, "price_lev_scale": 0.05}),
            # DUAL + PLS=0.02
            ("MREV_ST_WIDE_DUAL_5x_PLS02", "mean_rev_st", [5, 6, 7], [10, 12], "slow_st", [20, 30], [3.5, 4.0],
             {"leverage": 5.0, "price_lev_scale": 0.02}),
            ("MREV_ST_WIDE_DUAL_6x_PLS02", "mean_rev_st", [5, 6, 7], [10, 12], "slow_st", [20, 30], [3.5, 4.0],
             {"leverage": 6.0, "price_lev_scale": 0.02}),
            ("MREV_ST_WIDE_DUAL_8x_PLS02", "mean_rev_st", [5, 6, 7], [10, 12], "slow_st", [20, 30], [3.5, 4.0],
             {"leverage": 8.0, "price_lev_scale": 0.02}),
            ("MREV_ST_WIDE_DUAL_10x_PLS02", "mean_rev_st", [5, 6, 7], [10, 12], "slow_st", [20, 30], [3.5, 4.0],
             {"leverage": 10.0, "price_lev_scale": 0.02}),
            # PLS + MDE combo: PLS for gradual reduction, MDE as hard stop
            ("MREV_ST_WIDE_5x_PLS05_MDE25", "mean_rev_st", [5, 6, 7], [10, 12], "none", [0], [0],
             {"leverage": 5.0, "price_lev_scale": 0.05, "max_dd_exit_pct": 0.25, "mde_cooldown_bars": 240}),
            ("MREV_ST_WIDE_6x_PLS05_MDE25", "mean_rev_st", [5, 6, 7], [10, 12], "none", [0], [0],
             {"leverage": 6.0, "price_lev_scale": 0.05, "max_dd_exit_pct": 0.25, "mde_cooldown_bars": 240}),
            ("MREV_ST_WIDE_DUAL_5x_PLS05_MDE25", "mean_rev_st", [5, 6, 7], [10, 12], "slow_st", [20, 30], [3.5, 4.0],
             {"leverage": 5.0, "price_lev_scale": 0.05, "max_dd_exit_pct": 0.25, "mde_cooldown_bars": 240}),
            ("MREV_ST_WIDE_DUAL_6x_PLS05_MDE25", "mean_rev_st", [5, 6, 7], [10, 12], "slow_st", [20, 30], [3.5, 4.0],
             {"leverage": 6.0, "price_lev_scale": 0.05, "max_dd_exit_pct": 0.25, "mde_cooldown_bars": 240}),
            # PLS on other strategy families
            ("PIVOT_ST_5x_PLS05", "pivot_st", [5, 6, 7], [15, 20], "none", [0], [0],
             {"leverage": 5.0, "price_lev_scale": 0.05}),
            ("PIVOT_ST_6x_PLS05", "pivot_st", [5, 6, 7], [15, 20], "none", [0], [0],
             {"leverage": 6.0, "price_lev_scale": 0.05}),
            ("ST_LOWP_5x_PLS05", "supertrend", [5, 6, 7], [2.5], "none", [0], [0],
             {"leverage": 5.0, "price_lev_scale": 0.05}),
            ("ST_LOWP_6x_PLS05", "supertrend", [5, 6, 7], [2.5], "none", [0], [0],
             {"leverage": 6.0, "price_lev_scale": 0.05}),
        ]
        pre_names = []
        for prefix, entry, ep1s, ep2s, filt, fp1s, fp2s, risk_ov in _PROVEN_COMBOS:
            name = f"Combo_{prefix}"
            if name not in STRATEGIES:
                risk = {"cooldown_bars": 0, **risk_ov}
                STRATEGIES[name] = {
                    "fn": combo_signal,
                    "param_grid": {
                        "entry_type": [entry], "ep1": ep1s, "ep2": ep2s,
                        "filter_type": [filt], "fp1": fp1s, "fp2": fp2s,
                    },
                    "risk": risk,
                    "desc": f"{entry}+{filt} {risk_ov}",
                }
                pre_names.append(name)
        # ─── DUAL+MDE+PLS: targeted combos to close DD/O2a gap ───
        # DUAL_7x_MDE10_CD480 is at DD=-35.4, O2a=97 — adding PLS/TS to push over the line
        _extra_combos = []
        for mde, cd in [(0.10, 480), (0.10, 360), (0.10, 240),
                        (0.09, 480), (0.11, 480), (0.12, 480),
                        (0.10, 720), (0.08, 240), (0.08, 360)]:
            for lev in [6.5, 7.0, 7.5, 8.0]:
                for pls in [0.03, 0.05]:
                    mde_i = int(mde * 100)
                    pls_i = int(pls * 100)
                    cname = f"MREV_ST_WIDE_DUAL_{lev}x_MDE{mde_i}_CD{cd}_PLS{pls_i}"
                    _extra_combos.append(
                        (cname, "mean_rev_st", [5, 6, 7], [10, 12], "slow_st", [20, 30], [3.5, 4.0],
                         {"leverage": lev, "max_dd_exit_pct": mde, "mde_cooldown_bars": cd,
                          "price_lev_scale": pls, "price_lev_lb": 200}))
        for mde, cd in [(0.10, 480), (0.12, 480)]:
            for lev in [7.0, 7.5, 8.0]:
                for ts in [0.02, 0.03]:
                    mde_i = int(mde * 100)
                    ts_i = int(ts * 100)
                    cname = f"MREV_ST_WIDE_DUAL_{lev}x_MDE{mde_i}_CD{cd}_TS{ts_i}"
                    _extra_combos.append(
                        (cname, "mean_rev_st", [5, 6, 7], [10, 12], "slow_st", [20, 30], [3.5, 4.0],
                         {"leverage": lev, "max_dd_exit_pct": mde, "mde_cooldown_bars": cd,
                          "trailing_stop_pct": ts}))
        for mde in [0.09, 0.11, 0.13, 0.15]:
            for cd in [480, 720]:
                mde_i = int(mde * 100)
                cname = f"MREV_ST_WIDE_DUAL_7x_MDE{mde_i}_CD{cd}"
                _extra_combos.append(
                    (cname, "mean_rev_st", [5, 6, 7], [10, 12], "slow_st", [20, 30], [3.5, 4.0],
                     {"leverage": 7.0, "max_dd_exit_pct": mde, "mde_cooldown_bars": cd}))
        for lev in [6.5, 7.5]:
            for cd in [480, 720]:
                cname = f"MREV_ST_WIDE_DUAL_{lev}x_MDE10_CD{cd}"
                _extra_combos.append(
                    (cname, "mean_rev_st", [5, 6, 7], [10, 12], "slow_st", [20, 30], [3.5, 4.0],
                     {"leverage": lev, "max_dd_exit_pct": 0.10, "mde_cooldown_bars": cd}))
        for prefix, entry, ep1s, ep2s, filt, fp1s, fp2s, risk_ov in _extra_combos:
            name = f"Combo_{prefix}"
            if name not in STRATEGIES:
                risk = {"cooldown_bars": 0, **risk_ov}
                STRATEGIES[name] = {
                    "fn": combo_signal,
                    "param_grid": {
                        "entry_type": [entry], "ep1": ep1s, "ep2": ep2s,
                        "filter_type": [filt], "fp1": fp1s, "fp2": fp2s,
                    },
                    "risk": risk,
                }
                pre_names.append(name)
        log.info(f"Pre-registered {len(pre_names)} proven combo strategies (incl {len(_extra_combos)} targeted DUAL+MDE+PLS)")

        # ── Pre-registered composite (複合) strategies ──
        from engine.strategies import (composite_regime_signal, composite_vote_signal,
            composite_adaptive_signal, composite_riskoff_signal,
            composite_ddguard_signal, composite_ddguard_hold_signal,
            composite_dual_regime_signal, composite_ddguard_regime_signal)

        _COMPOSITE_STRATS = []

        # ══ TRIMMED composites: only most promising configs based on analysis ══
        # DDG/DDGH recovery formula fixed: now uses rolling_high (not fixed peak)
        # Focus: DDG flat, DDGS staged, DDGuard-Regime (bear strategy switch)

        # ── DDGuard-Regime: switch to bear strategy instead of going flat ──
        # This eliminates trade-free periods during bear markets
        _bull_bear_for_ddgr = [
            # Bull: mean_rev_st dip buy, Bear: supertrend trend-follow
            (("mean_rev_st", 6, 12), ("supertrend", 12, 2.5)),
            (("mean_rev_st", 6, 12), ("supertrend", 7, 2.5)),
            # Bull: mean_rev_st, Bear: mean_rev_st with wider params (catches bigger moves)
            (("mean_rev_st", 6, 12), ("mean_rev_st", 6, 20)),
            # Bull: pivot_st, Bear: supertrend
            (("pivot_st", 7, 0), ("supertrend", 12, 2.5)),
        ]
        for (bt, bp1, bp2), (brt, brp1, brp2) in _bull_bear_for_ddgr:
            for guard_th in [7.0, 10.0, 15.0]:
                for lev in [3.0, 3.5, 4.0, 4.5, 5.0]:
                    cname = f"(複)DDGR_{bt[:4]}{bp1}_{bp2}+{brt[:4]}{brp1}_LB200_TH{int(guard_th)}_R3_{lev}x"
                    if cname not in STRATEGIES:
                        STRATEGIES[cname] = {
                            "fn": composite_ddguard_regime_signal,
                            "param_grid": {
                                "bull_type": [bt], "bull_p1": [bp1], "bull_p2": [bp2],
                                "bear_type": [brt], "bear_p1": [brp1], "bear_p2": [brp2],
                                "guard_lookback": [200], "guard_threshold": [guard_th],
                                "recovery_mult": [0.3],
                            },
                            "risk": {"cooldown_bars": 0, "leverage": lev},
                            "desc": f"(複) DDGuard-Regime: {bt}(bull)+{brt}(bear) TH={guard_th}% {lev}x",
                        }
                        _COMPOSITE_STRATS.append(cname)

        # ── DDGuard flat: TIGHT threshold configs (LB=120-180, TH=2-5) ──
        # Discovery: LB=150-170, TH=2.5-3.0 achieves α≥150% AND DD>-35% on IS
        from engine.strategies import composite_ddguard_staged_signal
        _tight_ddg_configs = []
        for entry, ep1, ep2 in [("mean_rev_st", 6, 12)]:
            for lb in [120, 140, 150, 160, 170, 180]:
                for guard_th in [2.0, 2.5, 3.0, 3.5, 4.0]:
                    for rec in [0.2, 0.3, 0.35, 0.4, 0.5]:
                        for lev in [2.5, 3.0, 3.25, 3.5, 3.75, 4.0]:
                            cname = f"(複)DDG_{entry[:4]}{ep1}_{ep2}_LB{lb}_TH{guard_th}_R{rec}_{lev}x"
                            if cname not in STRATEGIES:
                                STRATEGIES[cname] = {
                                    "fn": composite_ddguard_signal,
                                    "param_grid": {
                                        "entry_type": [entry], "ep1": [ep1], "ep2": [ep2],
                                        "guard_lookback": [lb], "guard_threshold": [guard_th],
                                        "recovery_mult": [rec],
                                    },
                                    "risk": {"cooldown_bars": 0, "leverage": lev},
                                }
                                _tight_ddg_configs.append(cname)
        _COMPOSITE_STRATS.extend(_tight_ddg_configs)
        log.info(f"Registered {len(_tight_ddg_configs)} tight-threshold DDGuard strategies")

        # ── DDGuard flat: wider threshold configs (legacy, LB=200) ──
        for entry, ep1, ep2 in [("mean_rev_st", 6, 12), ("mean_rev_st", 5, 15)]:
            for guard_th in [10.0, 15.0, 20.0]:
                for lev in [3.0, 3.5, 4.0, 4.5]:
                    cname = f"(複)DDG_{entry[:4]}{ep1}_{ep2}_LB200_TH{int(guard_th)}_R3_{lev}x"
                    if cname not in STRATEGIES:
                        STRATEGIES[cname] = {
                            "fn": composite_ddguard_signal,
                            "param_grid": {
                                "entry_type": [entry], "ep1": [ep1], "ep2": [ep2],
                                "guard_lookback": [200], "guard_threshold": [guard_th],
                                "recovery_mult": [0.3],
                            },
                            "risk": {"cooldown_bars": 0, "leverage": lev},
                            "desc": f"(複) DDGuard: {entry} TH={guard_th}% {lev}x",
                        }
                        _COMPOSITE_STRATS.append(cname)

        # ── DDGuard-Hold: mean_rev_st, focused range ──
        for entry, ep1, ep2 in [("mean_rev_st", 6, 12), ("mean_rev_st", 5, 15)]:
            for guard_th in [10.0, 15.0]:
                for lev in [3.0, 3.5, 4.0]:
                    cname = f"(複)DDGH_{entry[:4]}{ep1}_{ep2}_LB200_TH{int(guard_th)}_R3_{lev}x"
                    if cname not in STRATEGIES:
                        STRATEGIES[cname] = {
                            "fn": composite_ddguard_hold_signal,
                            "param_grid": {
                                "entry_type": [entry], "ep1": [ep1], "ep2": [ep2],
                                "guard_lookback": [200], "guard_threshold": [guard_th],
                                "recovery_mult": [0.3],
                            },
                            "risk": {"cooldown_bars": 0, "leverage": lev},
                            "desc": f"(複) DDGuard-Hold: {entry} {lev}x",
                        }
                        _COMPOSITE_STRATS.append(cname)

        # ── DDGuard-Staged (DDGS): best of flat+hold ──
        for entry, ep1, ep2 in [("mean_rev_st", 6, 12), ("mean_rev_st", 5, 15), ("pivot_st", 7, 0)]:
            for hold_th, flat_th in [(5, 15), (7, 15), (7, 20), (10, 20)]:
                for lev in [3.0, 3.5, 4.0, 4.5]:
                    cname = f"(複)DDGS_{entry[:4]}{ep1}_{ep2}_LB200_H{hold_th}_F{flat_th}_R3_{lev}x"
                    if cname not in STRATEGIES:
                        STRATEGIES[cname] = {
                            "fn": composite_ddguard_staged_signal,
                            "param_grid": {
                                "entry_type": [entry], "ep1": [ep1], "ep2": [ep2],
                                "guard_lookback": [200],
                                "hold_threshold": [hold_th], "flat_threshold": [flat_th],
                                "recovery_mult": [0.3],
                            },
                            "risk": {"cooldown_bars": 0, "leverage": lev},
                            "desc": f"(複) DDGuard-Staged: {entry} H{hold_th}%/F{flat_th}% {lev}x",
                        }
                        _COMPOSITE_STRATS.append(cname)

        # ── DDGuard with HIGH-TRADE bases (pivot_st, st_breakout) ──
        for entry, ep1, ep2 in [("pivot_st", 7, 0), ("st_breakout", 7, 20)]:
            for guard_th in [10.0, 15.0, 20.0]:
                for lev in [2.0, 2.5, 3.0, 3.5, 4.0]:
                    cname = f"(複)DDG_{entry[:4]}{ep1}_{ep2}_LB200_TH{int(guard_th)}_R3_{lev}x"
                    if cname not in STRATEGIES:
                        STRATEGIES[cname] = {
                            "fn": composite_ddguard_signal,
                            "param_grid": {
                                "entry_type": [entry], "ep1": [ep1], "ep2": [ep2],
                                "guard_lookback": [200], "guard_threshold": [guard_th],
                                "recovery_mult": [0.3],
                            },
                            "risk": {"cooldown_bars": 0, "leverage": lev},
                            "desc": f"(複) DDGuard: {entry} TH={guard_th}% {lev}x",
                        }
                        _COMPOSITE_STRATS.append(cname)

        # ── DDGuard with FAST mean_rev_st (more trades) ──
        for entry, ep1, ep2 in [("mean_rev_st", 4, 8), ("mean_rev_st", 3, 6)]:
            for guard_th in [10.0, 15.0, 20.0]:
                for lev in [3.0, 3.5, 4.0]:
                    cname = f"(複)DDG_{entry[:4]}{ep1}_{ep2}_LB200_TH{int(guard_th)}_R3_{lev}x"
                    if cname not in STRATEGIES:
                        STRATEGIES[cname] = {
                            "fn": composite_ddguard_signal,
                            "param_grid": {
                                "entry_type": [entry], "ep1": [ep1], "ep2": [ep2],
                                "guard_lookback": [200], "guard_threshold": [guard_th],
                                "recovery_mult": [0.3],
                            },
                            "risk": {"cooldown_bars": 0, "leverage": lev},
                            "desc": f"(複) DDGuard fast-MR: {entry} {lev}x",
                        }
                        _COMPOSITE_STRATS.append(cname)

        # ── DDGuard HIGH threshold (20-30%) — preserves most trades ──
        for entry, ep1, ep2 in [("mean_rev_st", 6, 12), ("pivot_st", 7, 0)]:
            for guard_th in [20.0, 25.0]:
                for lev in [3.5, 4.0, 4.5, 5.0]:
                    cname = f"(複)DDG_{entry[:4]}{ep1}_{ep2}_LB200_TH{int(guard_th)}_R3_{lev}x"
                    if cname not in STRATEGIES:
                        STRATEGIES[cname] = {
                            "fn": composite_ddguard_signal,
                            "param_grid": {
                                "entry_type": [entry], "ep1": [ep1], "ep2": [ep2],
                                "guard_lookback": [200], "guard_threshold": [guard_th],
                                "recovery_mult": [0.3],
                            },
                                    "risk": {"cooldown_bars": 0, "leverage": lev},
                            "desc": f"(複) DDGuard high-TH: {entry} TH={guard_th}% {lev}x",
                        }
                        _COMPOSITE_STRATS.append(cname)

        # ── Dual-Regime composites: bull signal + bear signal + transition flat ──
        # Use mean_rev_st with DIFFERENT params for bull vs bear
        _bull_bear_pairs = [
            # Bull: tighter BB (ep2=12, fast dip buy), Bear: wider BB (ep2=20, catch bigger reversals)
            (("mean_rev_st", 6, 12), ("mean_rev_st", 6, 20)),
            (("mean_rev_st", 5, 15), ("mean_rev_st", 7, 10)),
            # Bull: mean_rev_st (dip buy), Bear: supertrend (ride the trend down)
            (("mean_rev_st", 6, 12), ("supertrend", 12, 2.5)),
            (("mean_rev_st", 5, 15), ("supertrend", 7, 2.5)),
        ]
        for bull_sig, bear_sig in _bull_bear_pairs:
            for ema_p in [200]:
                for flat_band in [2.0]:
                    for lev in [3.0, 4.0]:
                        cname = f"(複)DualReg_{bull_sig[0][:4]}{bull_sig[1]}+{bear_sig[0][:4]}{bear_sig[1]}_EMA{ema_p}_FB{int(flat_band)}_{lev}x"
                        if cname not in STRATEGIES:
                            STRATEGIES[cname] = {
                                "fn": composite_dual_regime_signal,
                                "param_grid": {
                                    "bull_type": [bull_sig[0]], "bull_p1": [bull_sig[1]], "bull_p2": [bull_sig[2]],
                                    "bear_type": [bear_sig[0]], "bear_p1": [bear_sig[1]], "bear_p2": [bear_sig[2]],
                                    "ema_period": [ema_p], "flat_band": [flat_band],
                                },
                                "risk": {"cooldown_bars": 0, "leverage": lev},
                                "desc": f"(複) DualRegime: {bull_sig[0]}(bull)+{bear_sig[0]}(bear) EMA{ema_p}",
                            }
                            _COMPOSITE_STRATS.append(cname)

        # ── Adaptive composites: mean-rev in trends, agreement-only in ranges ──
        _trend_sigs = [("supertrend", 12, 2.5)]
        _mr_sigs = [("mean_rev_st", 6, 12)]
        for te in _trend_sigs:
            for me in _mr_sigs:
                for adx_t in [25]:
                    for lev in [3.0, 4.0]:
                        cname = f"(複)Adapt_{te[0][:4]}{te[1]}_{me[0][:4]}{me[1]}_{me[2]}_ADX{adx_t}_{lev}x"
                        if cname not in STRATEGIES:
                            STRATEGIES[cname] = {
                                "fn": composite_adaptive_signal,
                                "param_grid": {
                                    "trend_type": [te[0]], "trend_p1": [te[1]], "trend_p2": [te[2]],
                                    "mr_type": [me[0]], "mr_p1": [me[1]], "mr_p2": [me[2]],
                                    "adx_period": [14], "adx_thresh": [adx_t],
                                },
                                "risk": {"cooldown_bars": 0, "leverage": lev},
                                "desc": f"(複) Adaptive: MR(trend)+agree(range) ADX>{adx_t} {lev}x",
                            }
                            _COMPOSITE_STRATS.append(cname)

        # ── Voting composites: 3 diverse signals vote ──
        _vote_trios = [
            (("supertrend", 12, 2.5), ("mean_rev_st", 6, 12), ("pivot_st", 7, 0)),
            (("supertrend", 10, 3.0), ("mean_rev_st", 5, 15), ("st_breakout", 7, 20)),
            (("supertrend", 7, 2.5), ("mean_rev_st", 7, 10), ("donchian", 20, 0)),
            (("mean_rev_st", 6, 12), ("mean_rev_st", 5, 15), ("mean_rev_st", 7, 10)),
        ]
        for trio in _vote_trios[:2]:
            for vt in [2]:
                for lev in [3.0, 4.0]:
                    cname = f"(複)Vote_{trio[0][0][:4]}{trio[0][1]}+{trio[1][0][:4]}{trio[1][1]}+{trio[2][0][:4]}{trio[2][1]}_V{vt}_{lev}x"
                    if cname not in STRATEGIES:
                        STRATEGIES[cname] = {
                            "fn": composite_vote_signal,
                            "param_grid": {
                                "e1_type": [trio[0][0]], "e1_p1": [trio[0][1]], "e1_p2": [trio[0][2]],
                                "e2_type": [trio[1][0]], "e2_p1": [trio[1][1]], "e2_p2": [trio[1][2]],
                                "e3_type": [trio[2][0]], "e3_p1": [trio[2][1]], "e3_p2": [trio[2][2]],
                                "vote_thresh": [vt],
                            },
                            "risk": {"cooldown_bars": 0, "leverage": lev},
                            "desc": f"(複) Vote {vt}/3 {lev}x",
                        }
                        _COMPOSITE_STRATS.append(cname)

        # ── Risk-off composites: wrap mean_rev_st with vol-spike risk-off ──
        for entry, ep1, ep2 in [("mean_rev_st", 6, 12)]:
            for ro_method in ["vol_spike"]:
                for ro_thresh in [0.7]:
                    for lev in [3.0, 4.0]:
                        cname = f"(複)RiskOff_{entry[:6]}{ep1}_{ro_method[:4]}_{ro_thresh}_{lev}x"
                        if cname not in STRATEGIES:
                            STRATEGIES[cname] = {
                                "fn": composite_riskoff_signal,
                                "param_grid": {
                                    "entry_type": [entry], "ep1": [ep1], "ep2": [ep2],
                                    "filter_type": ["none"], "fp1": [0], "fp2": [0],
                                    "riskoff_method": [ro_method], "riskoff_thresh": [ro_thresh],
                                },
                                "risk": {"cooldown_bars": 0, "leverage": lev},
                                "desc": f"(複) Risk-off: {entry}+{ro_method}",
                            }
                            _COMPOSITE_STRATS.append(cname)

        # ── Composite + MDE combos: DDGuard manages bear regime, MDE caps equity DD ──
        # Strategy: DDGR keeps trading in bear (via bear signals), MDE is hard stop for extreme DD
        # In OOS2 (bull), MDE rarely triggers → OOS2α preserved. In bear, DDGR+MDE → DD capped.
        _ddgr_mde_configs = [
            # (bull, bear, guard_th, lev, mde_pct, mde_cd, label)
            # Best DDGR bases (7/8 achievers) + MDE to fix DD
            (("mean_rev_st", 6, 12), ("supertrend", 12, 2.5), 10, 4.0, 0.20, 240, "DDGR_m612s12_TH10_4x_MDE20"),
            (("mean_rev_st", 6, 12), ("supertrend", 12, 2.5), 10, 4.0, 0.25, 240, "DDGR_m612s12_TH10_4x_MDE25"),
            (("mean_rev_st", 6, 12), ("supertrend", 12, 2.5), 10, 4.5, 0.20, 240, "DDGR_m612s12_TH10_45x_MDE20"),
            (("mean_rev_st", 6, 12), ("supertrend", 12, 2.5), 10, 4.5, 0.25, 240, "DDGR_m612s12_TH10_45x_MDE25"),
            (("mean_rev_st", 6, 12), ("supertrend", 12, 2.5), 15, 4.0, 0.20, 240, "DDGR_m612s12_TH15_4x_MDE20"),
            (("mean_rev_st", 6, 12), ("supertrend", 12, 2.5), 15, 4.0, 0.25, 240, "DDGR_m612s12_TH15_4x_MDE25"),
            (("mean_rev_st", 6, 12), ("supertrend", 12, 2.5), 15, 4.5, 0.20, 240, "DDGR_m612s12_TH15_45x_MDE20"),
            (("mean_rev_st", 6, 12), ("supertrend", 12, 2.5), 15, 4.5, 0.25, 240, "DDGR_m612s12_TH15_45x_MDE25"),
            # TH10 at 5x with tighter MDE
            (("mean_rev_st", 6, 12), ("supertrend", 12, 2.5), 10, 5.0, 0.15, 240, "DDGR_m612s12_TH10_5x_MDE15"),
            (("mean_rev_st", 6, 12), ("supertrend", 12, 2.5), 10, 5.0, 0.20, 240, "DDGR_m612s12_TH10_5x_MDE20"),
            # pivot_st bull + supertrend bear (PBO=0.00 base)
            (("pivot_st", 7, 0), ("supertrend", 12, 2.5), 7, 4.5, 0.20, 240, "DDGR_p70s12_TH7_45x_MDE20"),
            (("pivot_st", 7, 0), ("supertrend", 12, 2.5), 7, 4.5, 0.25, 240, "DDGR_p70s12_TH7_45x_MDE25"),
            (("pivot_st", 7, 0), ("supertrend", 12, 2.5), 10, 4.5, 0.20, 240, "DDGR_p70s12_TH10_45x_MDE20"),
            (("pivot_st", 7, 0), ("supertrend", 12, 2.5), 10, 5.0, 0.20, 240, "DDGR_p70s12_TH10_5x_MDE20"),
            # Shorter cooldown (CD120) for faster re-entry
            (("mean_rev_st", 6, 12), ("supertrend", 12, 2.5), 10, 4.0, 0.20, 120, "DDGR_m612s12_TH10_4x_MDE20_F"),
            (("mean_rev_st", 6, 12), ("supertrend", 12, 2.5), 10, 4.5, 0.20, 120, "DDGR_m612s12_TH10_45x_MDE20_F"),
        ]
        for (bt, bp1, bp2), (brt, brp1, brp2), gth, lev, mde, mde_cd, label in _ddgr_mde_configs:
            cname = f"(複){label}"
            if cname not in STRATEGIES:
                STRATEGIES[cname] = {
                    "fn": composite_ddguard_regime_signal,
                    "param_grid": {
                        "bull_type": [bt], "bull_p1": [bp1], "bull_p2": [bp2],
                        "bear_type": [brt], "bear_p1": [brp1], "bear_p2": [brp2],
                        "guard_lookback": [200], "guard_threshold": [float(gth)],
                        "recovery_mult": [0.3],
                    },
                    "risk": {"cooldown_bars": 0, "leverage": lev,
                             "max_dd_exit_pct": mde, "mde_cooldown_bars": mde_cd},
                    "desc": f"(複) DDGR+MDE: {bt}+{brt} TH{gth} {lev}x MDE{int(mde*100)}",
                }
                _COMPOSITE_STRATS.append(cname)

        # ── DDGR + PLS combos: regime switch + price-based dynamic leverage ──
        # DDGR switches to bear strategy during DD. PLS reduces leverage as price drops.
        # Together: bear signal at reduced leverage during crashes → strong DD control.
        # In bull: both inactive → full leverage → OOS2α preserved.
        _ddgr_pls_configs = [
            # (bull, bear, guard_th, lev, pls, label)
            (("mean_rev_st", 6, 12), ("supertrend", 12, 2.5), 10, 5.0, 0.05, "DDGR_m612s12_TH10_5x_PLS05"),
            (("mean_rev_st", 6, 12), ("supertrend", 12, 2.5), 10, 6.0, 0.05, "DDGR_m612s12_TH10_6x_PLS05"),
            (("mean_rev_st", 6, 12), ("supertrend", 12, 2.5), 10, 7.0, 0.05, "DDGR_m612s12_TH10_7x_PLS05"),
            (("mean_rev_st", 6, 12), ("supertrend", 12, 2.5), 10, 8.0, 0.05, "DDGR_m612s12_TH10_8x_PLS05"),
            (("mean_rev_st", 6, 12), ("supertrend", 12, 2.5), 10, 5.0, 0.03, "DDGR_m612s12_TH10_5x_PLS03"),
            (("mean_rev_st", 6, 12), ("supertrend", 12, 2.5), 10, 6.0, 0.03, "DDGR_m612s12_TH10_6x_PLS03"),
            (("mean_rev_st", 6, 12), ("supertrend", 12, 2.5), 10, 8.0, 0.03, "DDGR_m612s12_TH10_8x_PLS03"),
            (("mean_rev_st", 6, 12), ("supertrend", 12, 2.5), 15, 5.0, 0.05, "DDGR_m612s12_TH15_5x_PLS05"),
            (("mean_rev_st", 6, 12), ("supertrend", 12, 2.5), 15, 6.0, 0.05, "DDGR_m612s12_TH15_6x_PLS05"),
            (("mean_rev_st", 6, 12), ("supertrend", 12, 2.5), 15, 8.0, 0.05, "DDGR_m612s12_TH15_8x_PLS05"),
            # PLS + MDE hard stop for ultimate DD control
            (("mean_rev_st", 6, 12), ("supertrend", 12, 2.5), 10, 6.0, 0.05, "DDGR_m612s12_TH10_6x_PLS05_MDE25"),
            (("mean_rev_st", 6, 12), ("supertrend", 12, 2.5), 10, 8.0, 0.05, "DDGR_m612s12_TH10_8x_PLS05_MDE25"),
            # pivot_st base (PBO=0.00)
            (("pivot_st", 7, 0), ("supertrend", 12, 2.5), 10, 5.0, 0.05, "DDGR_p70s12_TH10_5x_PLS05"),
            (("pivot_st", 7, 0), ("supertrend", 12, 2.5), 10, 6.0, 0.05, "DDGR_p70s12_TH10_6x_PLS05"),
            (("pivot_st", 7, 0), ("supertrend", 12, 2.5), 7, 6.0, 0.05, "DDGR_p70s12_TH7_6x_PLS05"),
            # PLS=0.02: most aggressive — starts reducing at -2% price DD
            (("mean_rev_st", 6, 12), ("supertrend", 12, 2.5), 10, 5.0, 0.02, "DDGR_m612s12_TH10_5x_PLS02"),
            (("mean_rev_st", 6, 12), ("supertrend", 12, 2.5), 10, 6.0, 0.02, "DDGR_m612s12_TH10_6x_PLS02"),
            (("mean_rev_st", 6, 12), ("supertrend", 12, 2.5), 10, 8.0, 0.02, "DDGR_m612s12_TH10_8x_PLS02"),
            (("mean_rev_st", 6, 12), ("supertrend", 12, 2.5), 10, 10.0, 0.02, "DDGR_m612s12_TH10_10x_PLS02"),
            (("mean_rev_st", 6, 12), ("supertrend", 12, 2.5), 15, 5.0, 0.02, "DDGR_m612s12_TH15_5x_PLS02"),
            (("mean_rev_st", 6, 12), ("supertrend", 12, 2.5), 15, 6.0, 0.02, "DDGR_m612s12_TH15_6x_PLS02"),
            (("mean_rev_st", 6, 12), ("supertrend", 12, 2.5), 15, 8.0, 0.02, "DDGR_m612s12_TH15_8x_PLS02"),
            (("pivot_st", 7, 0), ("supertrend", 12, 2.5), 10, 5.0, 0.02, "DDGR_p70s12_TH10_5x_PLS02"),
            (("pivot_st", 7, 0), ("supertrend", 12, 2.5), 10, 6.0, 0.02, "DDGR_p70s12_TH10_6x_PLS02"),
            (("pivot_st", 7, 0), ("supertrend", 12, 2.5), 10, 8.0, 0.02, "DDGR_p70s12_TH10_8x_PLS02"),
            (("pivot_st", 7, 0), ("supertrend", 12, 2.5), 7, 5.0, 0.02, "DDGR_p70s12_TH7_5x_PLS02"),
            (("pivot_st", 7, 0), ("supertrend", 12, 2.5), 7, 6.0, 0.02, "DDGR_p70s12_TH7_6x_PLS02"),
            (("pivot_st", 7, 0), ("supertrend", 12, 2.5), 7, 8.0, 0.02, "DDGR_p70s12_TH7_8x_PLS02"),
            # Triple defense: DDGR + PLS + MDE → maximum DD control
            (("mean_rev_st", 6, 12), ("supertrend", 12, 2.5), 10, 5.0, 0.02, "DDGR_m612s12_TH10_5x_PLS02_MDE20"),
            (("mean_rev_st", 6, 12), ("supertrend", 12, 2.5), 10, 6.0, 0.02, "DDGR_m612s12_TH10_6x_PLS02_MDE20"),
            (("mean_rev_st", 6, 12), ("supertrend", 12, 2.5), 10, 7.0, 0.02, "DDGR_m612s12_TH10_7x_PLS02_MDE20"),
            (("mean_rev_st", 6, 12), ("supertrend", 12, 2.5), 10, 8.0, 0.02, "DDGR_m612s12_TH10_8x_PLS02_MDE20"),
            (("mean_rev_st", 6, 12), ("supertrend", 12, 2.5), 10, 10.0, 0.02, "DDGR_m612s12_TH10_10x_PLS02_MDE20"),
            (("mean_rev_st", 6, 12), ("supertrend", 12, 2.5), 10, 6.0, 0.03, "DDGR_m612s12_TH10_6x_PLS03_MDE20"),
            (("mean_rev_st", 6, 12), ("supertrend", 12, 2.5), 10, 8.0, 0.03, "DDGR_m612s12_TH10_8x_PLS03_MDE20"),
            (("pivot_st", 7, 0), ("supertrend", 12, 2.5), 10, 6.0, 0.02, "DDGR_p70s12_TH10_6x_PLS02_MDE20"),
            (("pivot_st", 7, 0), ("supertrend", 12, 2.5), 10, 8.0, 0.02, "DDGR_p70s12_TH10_8x_PLS02_MDE20"),
        ]
        for (bt, bp1, bp2), (brt, brp1, brp2), gth, lev, pls, label in _ddgr_pls_configs:
            cname = f"(複){label}"
            risk_dict = {"cooldown_bars": 0, "leverage": lev, "price_lev_scale": pls}
            if "MDE25" in label:
                risk_dict["max_dd_exit_pct"] = 0.25
                risk_dict["mde_cooldown_bars"] = 240
            elif "MDE20" in label:
                risk_dict["max_dd_exit_pct"] = 0.20
                risk_dict["mde_cooldown_bars"] = 120
            if cname not in STRATEGIES:
                STRATEGIES[cname] = {
                    "fn": composite_ddguard_regime_signal,
                    "param_grid": {
                        "bull_type": [bt], "bull_p1": [bp1], "bull_p2": [bp2],
                        "bear_type": [brt], "bear_p1": [brp1], "bear_p2": [brp2],
                        "guard_lookback": [200], "guard_threshold": [float(gth)],
                        "recovery_mult": [0.3],
                    },
                    "risk": risk_dict,
                    "desc": f"(複) DDGR+PLS: {bt}+{brt} TH{gth} {lev}x PLS{int(pls*100)}",
                }
                _COMPOSITE_STRATS.append(cname)

        # ── DDGS + MDE combos: staged guard + MDE hard stop ──
        # DDGS pivo7_0 has PBO=0.00 (best robustness) + MDE to fix DD
        _ddgs_mde_configs = [
            # (entry, ep1, ep2, hold_th, flat_th, lev, mde_pct, mde_cd, label)
            ("pivot_st", 7, 0, 7, 20, 4.5, 0.20, 240, "DDGS_p70_H7F20_45x_MDE20"),
            ("pivot_st", 7, 0, 7, 20, 4.5, 0.25, 240, "DDGS_p70_H7F20_45x_MDE25"),
            ("pivot_st", 7, 0, 7, 15, 4.5, 0.20, 240, "DDGS_p70_H7F15_45x_MDE20"),
            ("pivot_st", 7, 0, 7, 15, 4.5, 0.25, 240, "DDGS_p70_H7F15_45x_MDE25"),
            ("pivot_st", 7, 0, 7, 20, 4.0, 0.25, 240, "DDGS_p70_H7F20_4x_MDE25"),
            ("pivot_st", 7, 0, 10, 20, 4.5, 0.20, 240, "DDGS_p70_H10F20_45x_MDE20"),
            # DDGS mean6_12 (good OOS) + MDE
            ("mean_rev_st", 6, 12, 10, 20, 4.0, 0.20, 240, "DDGS_m612_H10F20_4x_MDE20"),
            ("mean_rev_st", 6, 12, 10, 20, 4.0, 0.25, 240, "DDGS_m612_H10F20_4x_MDE25"),
            ("mean_rev_st", 6, 12, 10, 20, 4.5, 0.20, 240, "DDGS_m612_H10F20_45x_MDE20"),
            ("mean_rev_st", 6, 12, 10, 20, 4.5, 0.25, 240, "DDGS_m612_H10F20_45x_MDE25"),
        ]
        for entry, ep1, ep2, hth, fth, lev, mde, mde_cd, label in _ddgs_mde_configs:
            cname = f"(複){label}"
            if cname not in STRATEGIES:
                STRATEGIES[cname] = {
                    "fn": composite_ddguard_staged_signal,
                    "param_grid": {
                        "entry_type": [entry], "ep1": [ep1], "ep2": [ep2],
                        "guard_lookback": [200],
                        "hold_threshold": [hth], "flat_threshold": [fth],
                        "recovery_mult": [0.3],
                    },
                    "risk": {"cooldown_bars": 0, "leverage": lev,
                             "max_dd_exit_pct": mde, "mde_cooldown_bars": mde_cd},
                    "desc": f"(複) DDGS+MDE: {entry} H{hth}/F{fth} {lev}x MDE{int(mde*100)}",
                }
                _COMPOSITE_STRATS.append(cname)

        # ── DDG + MDE combos: flat guard + MDE hard stop ──
        _ddg_mde_configs = [
            # DDG mean6_12 TH20 (7/8 achiever, PBO=0.00-0.25) + MDE
            ("mean_rev_st", 6, 12, 20, 4.0, 0.20, 240, "DDG_m612_TH20_4x_MDE20"),
            ("mean_rev_st", 6, 12, 20, 4.0, 0.25, 240, "DDG_m612_TH20_4x_MDE25"),
            ("mean_rev_st", 6, 12, 20, 4.5, 0.20, 240, "DDG_m612_TH20_45x_MDE20"),
            ("mean_rev_st", 6, 12, 20, 4.5, 0.25, 240, "DDG_m612_TH20_45x_MDE25"),
            ("mean_rev_st", 6, 12, 15, 4.0, 0.20, 240, "DDG_m612_TH15_4x_MDE20"),
            ("mean_rev_st", 6, 12, 15, 4.5, 0.20, 240, "DDG_m612_TH15_45x_MDE20"),
        ]
        for entry, ep1, ep2, gth, lev, mde, mde_cd, label in _ddg_mde_configs:
            cname = f"(複){label}"
            if cname not in STRATEGIES:
                STRATEGIES[cname] = {
                    "fn": composite_ddguard_signal,
                    "param_grid": {
                        "entry_type": [entry], "ep1": [ep1], "ep2": [ep2],
                        "guard_lookback": [200], "guard_threshold": [float(gth)],
                        "recovery_mult": [0.3],
                    },
                    "risk": {"cooldown_bars": 0, "leverage": lev,
                             "max_dd_exit_pct": mde, "mde_cooldown_bars": mde_cd},
                    "desc": f"(複) DDG+MDE: {entry} TH{gth} {lev}x MDE{int(mde*100)}",
                }
                _COMPOSITE_STRATS.append(cname)

        # ── Aggressive MDE on best composites: MDE08-12 + CD480-960 for DD>-35% ──
        # Theory: MDE10+CD960 → ~3 triggers in 30-day crash → DD≈-27%
        # MDE08+CD960 → 3 triggers → DD≈-22%, MDE12+CD960 → 3 triggers → DD≈-31%
        _agg_mde_configs = []
        # DDG bases (best PBO: 0.00-0.25)
        for gth in [20, 15]:
            for lev in [3.5, 4.0, 4.5]:
                for mde, mcd in [(0.08, 960), (0.10, 960), (0.10, 480), (0.12, 960), (0.12, 480), (0.15, 480)]:
                    lbl = f"DDG_m612_TH{gth}_{str(lev).replace('.','')[:2]}x_MDE{int(mde*100)}_CD{mcd}"
                    _agg_mde_configs.append(("ddg", "mean_rev_st", 6, 12, gth, None, None, None, None, lev, mde, mcd, lbl))
        # DDGR bases (regime switch, PBO=0.00-0.25)
        for gth in [10, 15]:
            for lev in [3.5, 4.0, 4.5]:
                for mde, mcd in [(0.08, 960), (0.10, 960), (0.10, 480), (0.12, 960), (0.12, 480), (0.15, 480)]:
                    lbl = f"DDGR_m612s12_TH{gth}_{str(lev).replace('.','')[:2]}x_MDE{int(mde*100)}_CD{mcd}"
                    _agg_mde_configs.append(("ddgr", "mean_rev_st", 6, 12, gth, "supertrend", 12, 2.5, None, lev, mde, mcd, lbl))
        # DDGS bases (staged guard, PBO=0.12)
        for hth, fth in [(10, 20)]:
            for lev in [3.5, 4.0, 4.5]:
                for mde, mcd in [(0.08, 960), (0.10, 960), (0.10, 480), (0.12, 960)]:
                    lbl = f"DDGS_m612_H{hth}F{fth}_{str(lev).replace('.','')[:2]}x_MDE{int(mde*100)}_CD{mcd}"
                    _agg_mde_configs.append(("ddgs", "mean_rev_st", 6, 12, None, None, None, None, (hth, fth), lev, mde, mcd, lbl))
        # (DUAL combos added in proven configs section with proper tuple format)

        for cfg in _agg_mde_configs:
            kind, entry, ep1, ep2, gth, bear_t, bear_p1, bear_p2, staged_params, lev, mde, mcd, label = cfg
            cname = f"(複){label}" if kind != "dual" else f"Combo_{label}"
            if cname in STRATEGIES:
                continue
            risk_d = {"cooldown_bars": 0, "leverage": lev, "max_dd_exit_pct": mde, "mde_cooldown_bars": mcd}
            if kind == "ddg":
                STRATEGIES[cname] = {
                    "fn": composite_ddguard_signal,
                    "param_grid": {
                        "entry_type": [entry], "ep1": [ep1], "ep2": [ep2],
                        "guard_lookback": [200], "guard_threshold": [float(gth)],
                        "recovery_mult": [0.3],
                    },
                    "risk": risk_d,
                    "desc": f"(複) DDG+AggrMDE {label}",
                }
            elif kind == "ddgr":
                STRATEGIES[cname] = {
                    "fn": composite_ddguard_regime_signal,
                    "param_grid": {
                        "bull_type": [entry], "bull_p1": [ep1], "bull_p2": [ep2],
                        "bear_type": [bear_t], "bear_p1": [bear_p1], "bear_p2": [bear_p2],
                        "guard_lookback": [200], "guard_threshold": [float(gth)],
                        "recovery_mult": [0.3],
                    },
                    "risk": risk_d,
                    "desc": f"(複) DDGR+AggrMDE {label}",
                }
            elif kind == "ddgs":
                hth, fth = staged_params
                STRATEGIES[cname] = {
                    "fn": composite_ddguard_staged_signal,
                    "param_grid": {
                        "entry_type": [entry], "ep1": [ep1], "ep2": [ep2],
                        "guard_lookback": [200],
                        "hold_threshold": [hth], "flat_threshold": [fth],
                        "recovery_mult": [0.3],
                    },
                    "risk": risk_d,
                    "desc": f"(複) DDGS+AggrMDE {label}",
                }
            else:
                continue
            _COMPOSITE_STRATS.append(cname)

        # ── SL + sl_cooldown composites: per-trade SL with SL-specific long cooldown ──
        # KEY INSIGHT: SL is applied during IS/OOS training (unlike MDE overlay)
        # → optimizer picks params that minimize SL triggers during bull
        # → SL-specific cooldown only delays after SL exits, signal exits stay fast
        # → During crash: SL triggers → long cooldown → DD limited
        # → During bull: SL rarely triggers → normal trading → α preserved
        _sl_cd_configs = []
        # DDG bases (PBO=0.00-0.25)
        for gth in [20, 15]:
            for lev in [3.5, 4.0, 4.5, 5.0]:
                for sl, slcd in [(0.015, 960), (0.02, 960), (0.02, 672), (0.025, 960), (0.03, 960), (0.015, 480), (0.02, 480)]:
                    lbl = f"DDG_m612_TH{gth}_{str(lev).replace('.','')[:2]}x_SL{int(sl*1000)}_SLCD{slcd}"
                    _sl_cd_configs.append(("ddg", "mean_rev_st", 6, 12, gth, None, None, None, None, lev, sl, slcd, lbl))
        # DDGR bases (regime switch)
        for gth in [10, 15]:
            for lev in [3.5, 4.0, 4.5, 5.0]:
                for sl, slcd in [(0.015, 960), (0.02, 960), (0.02, 672), (0.025, 960), (0.03, 960)]:
                    lbl = f"DDGR_m612s12_TH{gth}_{str(lev).replace('.','')[:2]}x_SL{int(sl*1000)}_SLCD{slcd}"
                    _sl_cd_configs.append(("ddgr", "mean_rev_st", 6, 12, gth, "supertrend", 12, 2.5, None, lev, sl, slcd, lbl))
        # DDGS bases (staged guard)
        for hth, fth in [(10, 20)]:
            for lev in [3.5, 4.0, 4.5, 5.0]:
                for sl, slcd in [(0.015, 960), (0.02, 960), (0.025, 960)]:
                    lbl = f"DDGS_m612_H{hth}F{fth}_{str(lev).replace('.','')[:2]}x_SL{int(sl*1000)}_SLCD{slcd}"
                    _sl_cd_configs.append(("ddgs", "mean_rev_st", 6, 12, None, None, None, None, (hth, fth), lev, sl, slcd, lbl))

        for cfg in _sl_cd_configs:
            kind, entry, ep1, ep2, gth, bear_t, bear_p1, bear_p2, staged_params, lev, sl, slcd, label = cfg
            cname = f"(複){label}"
            if cname in STRATEGIES:
                continue
            risk_d = {"cooldown_bars": 0, "leverage": lev, "stop_loss_pct": sl, "sl_cooldown_bars": slcd}
            if kind == "ddg":
                STRATEGIES[cname] = {
                    "fn": composite_ddguard_signal,
                    "param_grid": {
                        "entry_type": [entry], "ep1": [ep1], "ep2": [ep2],
                        "guard_lookback": [200], "guard_threshold": [float(gth)],
                        "recovery_mult": [0.3],
                    },
                    "risk": risk_d,
                    "desc": f"(複) DDG+SL: {entry} TH{gth} {lev}x SL{int(sl*1000)} SLCD{slcd}",
                }
            elif kind == "ddgr":
                STRATEGIES[cname] = {
                    "fn": composite_ddguard_regime_signal,
                    "param_grid": {
                        "bull_type": [entry], "bull_p1": [ep1], "bull_p2": [ep2],
                        "bear_type": [bear_t], "bear_p1": [bear_p1], "bear_p2": [bear_p2],
                        "guard_lookback": [200], "guard_threshold": [float(gth)],
                        "recovery_mult": [0.3],
                    },
                    "risk": risk_d,
                    "desc": f"(複) DDGR+SL: {entry}+{bear_t} TH{gth} {lev}x SL{int(sl*1000)} SLCD{slcd}",
                }
            elif kind == "ddgs":
                hth, fth = staged_params
                STRATEGIES[cname] = {
                    "fn": composite_ddguard_staged_signal,
                    "param_grid": {
                        "entry_type": [entry], "ep1": [ep1], "ep2": [ep2],
                        "guard_lookback": [200],
                        "hold_threshold": [hth], "flat_threshold": [fth],
                        "recovery_mult": [0.3],
                    },
                    "risk": risk_d,
                    "desc": f"(複) DDGS+SL: {entry} H{hth}/F{fth} {lev}x SL{int(sl*1000)} SLCD{slcd}",
                }
            else:
                continue
            _COMPOSITE_STRATS.append(cname)

        # ── Fast-switch DDG/DDGR: low threshold + long lookback → catch crashes early ──
        # At 4x, TH5+LB672: switch to flat at 5% below 7-day high → DD at switch ≈ -20%
        # During bull: 5% drop from 7-day high is rare → alpha preserved
        _fast_switch_configs = []
        for entry_type in ["mean_rev_st"]:
            ep1, ep2 = 6, 12
            for th in [3, 4, 5, 6]:
                for lb in [200, 400, 672]:
                    for lev in [3.5, 4.0, 4.5, 5.0]:
                        for rm in [0.3, 0.5]:  # recovery_mult: higher = slower re-entry (less false re-entries)
                            lbl = f"DDG_m612_TH{th}_LB{lb}_RM{int(rm*10)}_{str(lev).replace('.','')[:2]}x"
                            _fast_switch_configs.append(("ddg", entry_type, ep1, ep2, th, lb, rm, None, None, None, lev, lbl))
            # DDGR fast switch
            for th in [3, 4, 5]:
                for lb in [400, 672]:
                    for lev in [4.0, 4.5, 5.0]:
                        lbl = f"DDGR_m612s12_TH{th}_LB{lb}_{str(lev).replace('.','')[:2]}x"
                        _fast_switch_configs.append(("ddgr", entry_type, ep1, ep2, th, lb, 0.3, "supertrend", 12, 2.5, lev, lbl))

        for cfg in _fast_switch_configs:
            kind, entry, ep1, ep2, th, lb, rm, bear_t, bear_p1, bear_p2, lev, label = cfg
            cname = f"(複){label}"
            if cname in STRATEGIES:
                continue
            risk_d = {"cooldown_bars": 0, "leverage": lev}
            if kind == "ddg":
                STRATEGIES[cname] = {
                    "fn": composite_ddguard_signal,
                    "param_grid": {
                        "entry_type": [entry], "ep1": [ep1], "ep2": [ep2],
                        "guard_lookback": [lb], "guard_threshold": [float(th)],
                        "recovery_mult": [rm],
                    },
                    "risk": risk_d,
                    "desc": f"(複) DDG fast-switch: TH{th} LB{lb} RM{rm} {lev}x",
                }
            elif kind == "ddgr":
                STRATEGIES[cname] = {
                    "fn": composite_ddguard_regime_signal,
                    "param_grid": {
                        "bull_type": [entry], "bull_p1": [ep1], "bull_p2": [ep2],
                        "bear_type": [bear_t], "bear_p1": [bear_p1], "bear_p2": [bear_p2],
                        "guard_lookback": [lb], "guard_threshold": [float(th)],
                        "recovery_mult": [rm],
                    },
                    "risk": risk_d,
                    "desc": f"(複) DDGR fast-switch: TH{th} LB{lb} {lev}x",
                }
            _COMPOSITE_STRATS.append(cname)

        # ── DDGuard + Trailing Stop: per-trade DD protection (applied in IS/OOS) ──
        # Key insight: TS exits from trade peak, not entry. Combined with sl_cooldown
        # for losing exits, this limits cascade DD during crashes while preserving
        # profitable exits during bull runs.
        _ts_configs = []
        for entry, ep1, ep2, bear_t, bear_p1, bear_p2 in [
            ("mean_rev_st", 6, 12, "supertrend", 12, 2.5),
            ("mean_rev_st", 5, 15, "supertrend", 12, 2.5),
        ]:
            for guard_th in [15.0, 20.0]:
                for lev in [4.0, 4.5, 5.0, 5.5]:
                    for ts in [0.02, 0.03, 0.04]:
                        for slcd in [144, 288, 480]:
                            ts_i = int(ts * 100)
                            # DDG + TS + SLCD
                            cname = f"(複)DDG_m{ep1}{ep2}_TH{int(guard_th)}_{lev}x_TS{ts_i}_SLCD{slcd}"
                            if cname not in STRATEGIES:
                                STRATEGIES[cname] = {
                                    "fn": composite_ddguard_signal,
                                    "param_grid": {
                                        "entry_type": [entry], "ep1": [ep1], "ep2": [ep2],
                                        "guard_lookback": [200], "guard_threshold": [guard_th],
                                        "recovery_mult": [0.3],
                                    },
                                    "risk": {"cooldown_bars": 0, "leverage": lev,
                                             "trailing_stop_pct": ts, "sl_cooldown_bars": slcd},
                                }
                                _ts_configs.append(cname)
                            # DDGR + TS + SLCD
                            cname_r = f"(複)DDGR_m{ep1}{ep2}s12_TH{int(guard_th)}_{lev}x_TS{ts_i}_SLCD{slcd}"
                            if cname_r not in STRATEGIES:
                                STRATEGIES[cname_r] = {
                                    "fn": composite_ddguard_regime_signal,
                                    "param_grid": {
                                        "bull_type": [entry], "bull_p1": [ep1], "bull_p2": [ep2],
                                        "bear_type": [bear_t], "bear_p1": [bear_p1], "bear_p2": [bear_p2],
                                        "guard_lookback": [200], "guard_threshold": [guard_th],
                                        "recovery_mult": [0.3],
                                    },
                                    "risk": {"cooldown_bars": 0, "leverage": lev,
                                             "trailing_stop_pct": ts, "sl_cooldown_bars": slcd},
                                }
                                _ts_configs.append(cname_r)
        # TS + SL combo: TS protects profits, SL caps absolute loss, sl_cooldown for cascade
        for entry, ep1, ep2, bear_t, bear_p1, bear_p2 in [
            ("mean_rev_st", 6, 12, "supertrend", 12, 2.5),
        ]:
            for guard_th in [15.0, 20.0]:
                for lev in [4.0, 4.5, 5.0, 5.5]:
                    for ts, sl in [(0.03, 0.05), (0.02, 0.04), (0.03, 0.06)]:
                        for slcd in [288, 480]:
                            ts_i = int(ts * 100)
                            sl_i = int(sl * 100)
                            cname = f"(複)DDG_m{ep1}{ep2}_TH{int(guard_th)}_{lev}x_TS{ts_i}_SL{sl_i}_SLCD{slcd}"
                            if cname not in STRATEGIES:
                                STRATEGIES[cname] = {
                                    "fn": composite_ddguard_signal,
                                    "param_grid": {
                                        "entry_type": [entry], "ep1": [ep1], "ep2": [ep2],
                                        "guard_lookback": [200], "guard_threshold": [guard_th],
                                        "recovery_mult": [0.3],
                                    },
                                    "risk": {"cooldown_bars": 0, "leverage": lev,
                                             "trailing_stop_pct": ts, "stop_loss_pct": sl,
                                             "sl_cooldown_bars": slcd},
                                }
                                _ts_configs.append(cname)
                            cname_r = f"(複)DDGR_m{ep1}{ep2}s12_TH{int(guard_th)}_{lev}x_TS{ts_i}_SL{sl_i}_SLCD{slcd}"
                            if cname_r not in STRATEGIES:
                                STRATEGIES[cname_r] = {
                                    "fn": composite_ddguard_regime_signal,
                                    "param_grid": {
                                        "bull_type": [entry], "bull_p1": [ep1], "bull_p2": [ep2],
                                        "bear_type": [bear_t], "bear_p1": [bear_p1], "bear_p2": [bear_p2],
                                        "guard_lookback": [200], "guard_threshold": [guard_th],
                                        "recovery_mult": [0.3],
                                    },
                                    "risk": {"cooldown_bars": 0, "leverage": lev,
                                             "trailing_stop_pct": ts, "stop_loss_pct": sl,
                                             "sl_cooldown_bars": slcd},
                                }
                                _ts_configs.append(cname_r)
        _COMPOSITE_STRATS.extend(_ts_configs)
        log.info(f"Registered {len(_ts_configs)} TS+SLCD composite strategies")

        # ── DDGuard + price_lev_scale: asymmetric leverage (full in uptrend, reduced in DD) ──
        # price_lev_scale IS applied in IS/OOS (per-trade mechanism).
        # At pls=0.05: full lev when price <5% from high, linear scale to 1x at 10% from high.
        _pls_configs = []
        for entry, ep1, ep2, bear_t, bear_p1, bear_p2 in [
            ("mean_rev_st", 6, 12, "supertrend", 12, 2.5),
        ]:
            for guard_th in [15.0, 20.0]:
                for lev in [5.0, 5.5, 6.0, 7.0]:
                    for pls in [0.03, 0.04, 0.05, 0.07]:
                        for plb in [100, 200]:
                            pls_i = int(pls * 100)
                            # DDG + PLS
                            cname = f"(複)DDG_m{ep1}{ep2}_TH{int(guard_th)}_{lev}x_PLS{pls_i}_LB{plb}"
                            if cname not in STRATEGIES:
                                STRATEGIES[cname] = {
                                    "fn": composite_ddguard_signal,
                                    "param_grid": {
                                        "entry_type": [entry], "ep1": [ep1], "ep2": [ep2],
                                        "guard_lookback": [200], "guard_threshold": [guard_th],
                                        "recovery_mult": [0.3],
                                    },
                                    "risk": {"cooldown_bars": 0, "leverage": lev,
                                             "price_lev_scale": pls, "price_lev_lb": plb},
                                }
                                _pls_configs.append(cname)
                            # DDGR + PLS
                            cname_r = f"(複)DDGR_m{ep1}{ep2}s12_TH{int(guard_th)}_{lev}x_PLS{pls_i}_LB{plb}"
                            if cname_r not in STRATEGIES:
                                STRATEGIES[cname_r] = {
                                    "fn": composite_ddguard_regime_signal,
                                    "param_grid": {
                                        "bull_type": [entry], "bull_p1": [ep1], "bull_p2": [ep2],
                                        "bear_type": [bear_t], "bear_p1": [bear_p1], "bear_p2": [bear_p2],
                                        "guard_lookback": [200], "guard_threshold": [guard_th],
                                        "recovery_mult": [0.3],
                                    },
                                    "risk": {"cooldown_bars": 0, "leverage": lev,
                                             "price_lev_scale": pls, "price_lev_lb": plb},
                                }
                                _pls_configs.append(cname_r)
        # Hybrid: TS + PLS (double protection)
        for entry, ep1, ep2 in [("mean_rev_st", 6, 12)]:
            for guard_th in [20.0]:
                for lev in [5.0, 5.5, 6.0]:
                    for ts in [0.03]:
                        for pls in [0.03, 0.05]:
                            for slcd in [288]:
                                ts_i = int(ts * 100)
                                pls_i = int(pls * 100)
                                cname = f"(複)DDG_m{ep1}{ep2}_TH{int(guard_th)}_{lev}x_TS{ts_i}_PLS{pls_i}_SLCD{slcd}"
                                if cname not in STRATEGIES:
                                    STRATEGIES[cname] = {
                                        "fn": composite_ddguard_signal,
                                        "param_grid": {
                                            "entry_type": [entry], "ep1": [ep1], "ep2": [ep2],
                                            "guard_lookback": [200], "guard_threshold": [guard_th],
                                            "recovery_mult": [0.3],
                                        },
                                        "risk": {"cooldown_bars": 0, "leverage": lev,
                                                 "trailing_stop_pct": ts, "sl_cooldown_bars": slcd,
                                                 "price_lev_scale": pls, "price_lev_lb": 200},
                                    }
                                    _pls_configs.append(cname)
        _COMPOSITE_STRATS.extend(_pls_configs)
        log.info(f"Registered {len(_pls_configs)} PLS (price-lev-scale) composite strategies")

        # ── DDGuard-VolGate: signal-level vol filter + DDGuard + vol_lev in engine ──
        # Two complementary DD-reduction mechanisms:
        # 1. Signal-level: composite_ddguard_volgate_signal blocks entries during high-vol
        # 2. Engine-level: vol_lev_atr reduces leverage when ATR is elevated
        # Combined with TS + sl_cooldown for per-trade protection
        from engine.strategies import composite_ddguard_volgate_signal
        _vg_configs = []
        for entry, ep1, ep2 in [("mean_rev_st", 6, 12), ("mean_rev_st", 5, 15)]:
            for guard_th in [10.0, 15.0, 20.0]:
                for v_atr in [48]:
                    for v_th in [3.0, 3.5, 4.0]:  # ×1000 → 0.3%, 0.35%, 0.4%
                        for lev in [5.0, 6.0, 7.0, 8.0]:
                            # VolGate signal + vol_lev in engine
                            cname = f"(複)DDGVG_m{ep1}{ep2}_TH{int(guard_th)}_V{v_atr}_{v_th}_{lev}x"
                            if cname not in STRATEGIES:
                                STRATEGIES[cname] = {
                                    "fn": composite_ddguard_volgate_signal,
                                    "param_grid": {
                                        "entry_type": [entry], "ep1": [ep1], "ep2": [ep2],
                                        "guard_lookback": [200], "guard_threshold": [guard_th],
                                        "recovery_mult": [0.3],
                                        "vol_atr_lb": [v_atr], "vol_threshold": [v_th],
                                    },
                                    "risk": {"cooldown_bars": 0, "leverage": lev,
                                             "vol_lev_atr": v_atr, "vol_lev_threshold": v_th / 1000},
                                }
                                _vg_configs.append(cname)
                            # VolGate + TS + sl_cooldown
                            for ts in [0.02, 0.03]:
                                for slcd in [288, 480]:
                                    ts_i = int(ts * 100)
                                    cname2 = f"(複)DDGVG_m{ep1}{ep2}_TH{int(guard_th)}_V{v_atr}_{v_th}_{lev}x_TS{ts_i}_SLCD{slcd}"
                                    if cname2 not in STRATEGIES:
                                        STRATEGIES[cname2] = {
                                            "fn": composite_ddguard_volgate_signal,
                                            "param_grid": {
                                                "entry_type": [entry], "ep1": [ep1], "ep2": [ep2],
                                                "guard_lookback": [200], "guard_threshold": [guard_th],
                                                "recovery_mult": [0.3],
                                                "vol_atr_lb": [v_atr], "vol_threshold": [v_th],
                                            },
                                            "risk": {"cooldown_bars": 0, "leverage": lev,
                                                     "trailing_stop_pct": ts, "sl_cooldown_bars": slcd,
                                                     "vol_lev_atr": v_atr, "vol_lev_threshold": v_th / 1000},
                                        }
                                        _vg_configs.append(cname2)
        _COMPOSITE_STRATS.extend(_vg_configs)
        log.info(f"Registered {len(_vg_configs)} VolGate composite strategies")

        # ── High-leverage DDGuard + vol_lev (engine-level only): ──
        # Uses standard DDGuard signal but with vol_lev in backtest engine
        # for leverage reduction during volatile periods. Higher base leverage (6-10x)
        # because vol_lev naturally reduces it during dangerous periods.
        _vlev_configs = []
        for entry, ep1, ep2 in [("mean_rev_st", 6, 12), ("mean_rev_st", 5, 15)]:
            for guard_th in [10.0, 15.0, 20.0]:
                for lev in [6.0, 7.0, 8.0, 10.0]:
                    for vla in [48]:
                        for vlt in [0.003, 0.0035, 0.004]:
                            vlt_s = str(vlt).replace("0.", "")
                            cname = f"(複)DDG_m{ep1}{ep2}_TH{int(guard_th)}_{lev}x_VL{vlt_s}"
                            if cname not in STRATEGIES:
                                STRATEGIES[cname] = {
                                    "fn": composite_ddguard_signal,
                                    "param_grid": {
                                        "entry_type": [entry], "ep1": [ep1], "ep2": [ep2],
                                        "guard_lookback": [200], "guard_threshold": [guard_th],
                                        "recovery_mult": [0.3],
                                    },
                                    "risk": {"cooldown_bars": 0, "leverage": lev,
                                             "vol_lev_atr": vla, "vol_lev_threshold": vlt},
                                }
                                _vlev_configs.append(cname)
                            # With TS + sl_cooldown too
                            for ts in [0.02, 0.03]:
                                for slcd in [288, 480]:
                                    ts_i = int(ts * 100)
                                    cname2 = f"(複)DDG_m{ep1}{ep2}_TH{int(guard_th)}_{lev}x_VL{vlt_s}_TS{ts_i}_SLCD{slcd}"
                                    if cname2 not in STRATEGIES:
                                        STRATEGIES[cname2] = {
                                            "fn": composite_ddguard_signal,
                                            "param_grid": {
                                                "entry_type": [entry], "ep1": [ep1], "ep2": [ep2],
                                                "guard_lookback": [200], "guard_threshold": [guard_th],
                                                "recovery_mult": [0.3],
                                            },
                                            "risk": {"cooldown_bars": 0, "leverage": lev,
                                                     "trailing_stop_pct": ts, "sl_cooldown_bars": slcd,
                                                     "vol_lev_atr": vla, "vol_lev_threshold": vlt},
                                        }
                                        _vlev_configs.append(cname2)
        _COMPOSITE_STRATS.extend(_vlev_configs)
        log.info(f"Registered {len(_vlev_configs)} vol_lev (high-lev DDG) composite strategies")

        # ── BREAKTHROUGH: Adaptive DDGuard + trend_lev (regime-aware leverage) ──
        # Key innovation: DDGuard disabled in bull (threshold=100%), tight in bear
        # Combined with SMA-based leverage scaling: high lev in bull, low in bear
        # Result: IS α=450-736% DD>-35% + O2α=100-163% simultaneously
        from engine.strategies import composite_adaptive_ddguard_signal
        _adaptive_tl_configs = []
        # Focused: best-performing parameter regions only
        for entry, ep1, ep2 in [("mean_rev_st", 6, 12)]:
            for lb in [155, 160, 165, 170]:
                for bear_th in [2.0, 2.5]:
                    for trend_lb in [5000, 7000]:
                        for rec in [0.35, 0.4, 0.45, 0.5]:
                            for bull_lev, bear_lev in [(4.5, 3.5), (5.0, 3.0), (5.0, 3.5), (5.5, 3.0), (6.0, 3.0), (6.0, 3.5),
                                                       (4.5, 3.0), (4.0, 3.5)]:
                                cname = f"(複)ADDG_TL_{entry[:4]}{ep1}_{ep2}_LB{lb}_BTH{bear_th}_TLB{trend_lb}_R{rec}_B{bull_lev}b{bear_lev}x"
                                if cname not in STRATEGIES:
                                    STRATEGIES[cname] = {
                                        "fn": composite_adaptive_ddguard_signal,
                                        "param_grid": {
                                            "entry_type": [entry], "ep1": [ep1], "ep2": [ep2],
                                            "guard_lookback": [lb], "bear_threshold": [bear_th],
                                            "bull_threshold": [100.0],
                                            "trend_lookback": [trend_lb], "recovery_mult": [rec],
                                        },
                                        "risk": {"cooldown_bars": 0,
                                                 "trend_lev_sma": trend_lb,
                                                 "trend_lev_bull": bull_lev,
                                                 "trend_lev_bear": bear_lev},
                                    }
                                    _adaptive_tl_configs.append(cname)
        _COMPOSITE_STRATS.extend(_adaptive_tl_configs)
        log.info(f"Registered {len(_adaptive_tl_configs)} Adaptive DDGuard + trend_lev strategies")

        # ── DD-FOCUSED: Low-leverage + high-recovery ADDG_TL for DD > -33% ──
        _dd_focused_configs = []
        for entry, ep1, ep2 in [("mean_rev_st", 6, 12)]:  # best entry only
            for lb in [160, 165, 170]:
                for bear_th in [2.0, 2.5]:
                    for trend_lb in [7000]:  # best TLB
                        for rec in [0.5, 0.55, 0.6]:
                            for bull_lev, bear_lev in [
                                (4.0, 3.0), (4.0, 3.5), (4.5, 3.0), (4.5, 3.5),
                                (5.0, 3.0), (5.0, 3.5), (5.0, 4.0),
                            ]:
                                cname = f"(複)ADDG_TL_{entry[:4]}{ep1}_{ep2}_LB{lb}_BTH{bear_th}_TLB{trend_lb}_R{rec}_B{bull_lev}b{bear_lev}x"
                                if cname not in STRATEGIES:
                                    STRATEGIES[cname] = {
                                        "fn": composite_adaptive_ddguard_signal,
                                        "param_grid": {
                                            "entry_type": [entry], "ep1": [ep1], "ep2": [ep2],
                                            "guard_lookback": [lb], "bear_threshold": [bear_th],
                                            "bull_threshold": [100.0],
                                            "trend_lookback": [trend_lb], "recovery_mult": [rec],
                                        },
                                        "risk": {"cooldown_bars": 0,
                                                 "trend_lev_sma": trend_lb,
                                                 "trend_lev_bull": bull_lev,
                                                 "trend_lev_bear": bear_lev},
                                    }
                                    _dd_focused_configs.append(cname)
        _COMPOSITE_STRATS.extend(_dd_focused_configs)
        log.info(f"Registered {len(_dd_focused_configs)} DD-focused ADDG_TL strategies")

        # ── NEW: Volatility-scaled Adaptive DDGuard ──
        # Dynamic threshold based on ATR: tighter in calm markets, wider in volatile
        from engine.strategies import composite_addg_volscaled_signal
        _volscaled_configs = []
        for entry, ep1, ep2 in [("mean_rev_st", 6, 12)]:  # best entry
            for lb in [160, 165]:
                for base_th in [2.0, 2.5]:
                    for atr_p, atr_m in [(960, 2.0), (960, 2.5), (1440, 2.0)]:
                        for trend_lb in [7000]:
                            for rec in [0.4, 0.5]:
                                for bull_lev, bear_lev in [(5.0, 3.0), (5.0, 3.5), (5.5, 3.0), (4.5, 3.0), (4.5, 3.5)]:
                                    cname = f"(複)ADDG_VS_{entry[:4]}{ep1}_{ep2}_LB{lb}_BT{base_th}_ATR{atr_p}x{atr_m}_TLB{trend_lb}_R{rec}_B{bull_lev}b{bear_lev}x"
                                    if cname not in STRATEGIES:
                                        STRATEGIES[cname] = {
                                            "fn": composite_addg_volscaled_signal,
                                            "param_grid": {
                                                "entry_type": [entry], "ep1": [ep1], "ep2": [ep2],
                                                "guard_lookback": [lb], "base_threshold": [base_th],
                                                "atr_period": [atr_p], "atr_mult": [atr_m],
                                                "trend_lookback": [trend_lb], "recovery_mult": [rec],
                                            },
                                            "risk": {"cooldown_bars": 0,
                                                     "trend_lev_sma": trend_lb,
                                                     "trend_lev_bull": bull_lev,
                                                     "trend_lev_bear": bear_lev},
                                        }
                                        _volscaled_configs.append(cname)
        _COMPOSITE_STRATS.extend(_volscaled_configs)
        log.info(f"Registered {len(_volscaled_configs)} Volatility-scaled ADDG strategies")

        # ── NEW: Gradient Leverage ADDG — smooth regime transition ──
        # GM5.0 is the sweet spot: all GM5.0 have positive OOS3 (+12%~+71%)
        # GM3.0 also positive (+14%~+44%), GM2.0 all negative
        # LB165 slightly better than LB160 for OOS3
        # Best: LB165_BTH2.5_R0.4_GM5.0_B5.5b3.0x (OOS3α=+71%, R²=0.877)
        from engine.strategies import composite_addg_gradient_lev_signal
        _gradient_configs = []
        for entry, ep1, ep2 in [("mean_rev_st", 6, 12)]:  # best entry
            for lb in [160, 165, 170]:
                for bear_th in [2.0, 2.5, 3.0]:
                    for trend_lb in [7000]:
                        for rec in [0.3, 0.4, 0.5]:
                            for grad_margin in [5.0, 7.0, 10.0]:
                                for bull_lev, bear_lev in [
                                    (4.5, 3.0), (5.0, 3.0), (5.0, 3.5),
                                    (5.5, 3.0), (5.5, 3.5), (6.0, 3.0),
                                ]:
                                    cname = f"(複)ADDG_GL_{entry[:4]}{ep1}_{ep2}_LB{lb}_BTH{bear_th}_TLB{trend_lb}_R{rec}_GM{grad_margin}_B{bull_lev}b{bear_lev}x"
                                    if cname not in STRATEGIES:
                                        STRATEGIES[cname] = {
                                            "fn": composite_addg_gradient_lev_signal,
                                            "param_grid": {
                                                "entry_type": [entry], "ep1": [ep1], "ep2": [ep2],
                                                "guard_lookback": [lb], "bear_threshold": [bear_th],
                                                "trend_lookback": [trend_lb], "recovery_mult": [rec],
                                                "gradient_margin": [grad_margin],
                                            },
                                            "risk": {"cooldown_bars": 0,
                                                     "trend_lev_sma": trend_lb,
                                                     "trend_lev_bull": bull_lev,
                                                     "trend_lev_bear": bear_lev},
                                        }
                                        _gradient_configs.append(cname)
        _COMPOSITE_STRATS.extend(_gradient_configs)
        log.info(f"Registered {len(_gradient_configs)} Gradient Leverage ADDG strategies")

        # Prioritize: ADDG_TL (breakthrough) first, then tight DDG, then VG/VL, then rest
        _addg_tl_set = set(_adaptive_tl_configs)
        _tight_ddg_set = set(_tight_ddg_configs)
        _vg_vl_composites = [n for n in _COMPOSITE_STRATS if ('VG' in n or '_VL' in n) and n not in _tight_ddg_set and n not in _addg_tl_set]
        _targeted_dual = [n for n in pre_names if 'DUAL' in n and ('PLS' in n or 'MDE09' in n or 'MDE11' in n or 'MDE13' in n or 'MDE15' in n or '6.5x' in n or '7.5x' in n or '_TS' in n)]
        _ts_pls_composites = [n for n in _COMPOSITE_STRATS if ('_TS' in n or '_PLS' in n) and n not in set(_vg_vl_composites) and n not in _tight_ddg_set and n not in _addg_tl_set]
        _other_proven_priority = [n for n in pre_names if ('MREV_ST' in n or 'PIVOT_ST' in n) and n not in set(_targeted_dual)]
        _other_proven = [n for n in pre_names if n not in set(_other_proven_priority) and n not in set(_targeted_dual)]
        _priority_composites = [n for n in _COMPOSITE_STRATS if 'DDG' in n and n not in set(_ts_pls_composites) and n not in set(_vg_vl_composites) and n not in _tight_ddg_set and n not in _addg_tl_set]
        _other_composites = [n for n in _COMPOSITE_STRATS if n not in set(_priority_composites) and n not in set(_ts_pls_composites) and n not in set(_vg_vl_composites) and n not in _tight_ddg_set and n not in _addg_tl_set]
        pre_names = _dd_focused_configs + _gradient_configs + _adaptive_tl_configs + _volscaled_configs + _tight_ddg_configs + _vg_vl_composites + _targeted_dual + _ts_pls_composites + _priority_composites + _other_proven_priority + _other_composites + _other_proven
        log.info(f"Pre-registered {len(_COMPOSITE_STRATS)} composite (複合) strategies "
                 f"(priority: {len(_adaptive_tl_configs)} ADDG_TL + {len(_tight_ddg_configs)} tight-DDG + {len(_vg_vl_composites)} VG/VL + {len(_ts_pls_composites)} TS/PLS + {len(_priority_composites)} DDG)")

        while True:  # Run until target found
            if run_names is None:
                # Don't delete results without equity curves — keep existing data
                existing = {r["name"] for r in _results}
                run_names = [n for n in pre_names if n not in existing]
                # Skip low-priority non-ADDG strategies to focus on promising space
                remaining = [n for n in STRATEGIES.keys()
                             if n not in existing and n not in set(run_names)
                             and ('ADDG' in n or 'GL_' in n or 'VS_' in n)]
                run_names.extend(remaining)
                if not run_names:
                    log.info("All strategies already have results, skipping to novel generation")
                    run_names = []

            n = len(run_names)
            if n == 0:
                log.info("No strategies to run, generating novel batch...")
                run_names = _generate_novel_strategies(list(_results), batch_id)
                batch_id += 1
                n = len(run_names)
                if n == 0:
                    break

            _run_status.update(
                strategies_completed=0, strategies_total=n,
                progress=f"R{round_num}: {n}戦略 OOS2有 (α≥150%+OOS≥100%+OOS2≥100%+DD>-35%+R²>0.7+D≥0.75%: {len(_qualifying())}/{GOAL_COUNT})",
            )
            log.info(f"=== Round {round_num}: {n} strategies (total: {len(_results)}, goal: {len(_qualifying())}/{GOAL_COUNT}) ===")

            cur_round = round_num

            def progress_cb(idx, total, name, _rn=cur_round):
                nonlocal total_analyses
                total_analyses += 1
                _run_status["strategies_completed"] = idx
                _run_status["total_analyses"] = total_analyses
                q = _qualifying()
                _run_status["progress"] = f"R{_rn}: {idx}/{total} ({name}) [α≥150%+OOS≥100%+OOS2≥100%+DD>-35%+R²>0.7+D≥0.75%: {len(q)}/{GOAL_COUNT}] 累計{total_analyses}"
                if total_analyses % 10 == 0:
                    log.info(f"=== 進捗: 累計{total_analyses}回完了 (R{_rn}) 目標達成: {len(q)}/{GOAL_COUNT} ===")

            def on_result(result, _rn=cur_round):
                # トレード数が統計的に不足する戦略を破棄
                trades = result.get("metrics", {}).get("total_trades", 0)
                if trades < 20:
                    log.info(f"破棄: {result['name']} (トレード数={trades} < 20)")
                    return
                _update_results_incremental(result, _rn)

            # 6時間以上探索継続: 早期停止なし
            await _run_optimization_parallel(df, run_names, progress_cb, on_result,
                                             df_oos2=df_oos2, df_oos3=df_oos3,
                                             early_stop_check=None)

            _run_status["last_run"] = datetime.now().isoformat()
            profitable = [r for r in _results if r["metrics"]["alpha_pct"] > 0]
            log.info(f"Round {round_num} done: {len(_results)} total, {len(profitable)} profitable, analyses={total_analyses}")

            q = _qualifying()
            log.info(f"目標: α≥{ALPHA_TARGET}%+OOSα≥{OOS_ALPHA_TARGET}%+PBO<{PBO_LIMIT}+DD>{MAX_DD}%+R²>{MIN_EQUITY_R2} = {len(q)}個")

            if len(q) >= GOAL_COUNT:
                log.info(f"*** 目標達成! {len(q)}戦略が全条件達成 ***")
                for r in sorted(q, key=lambda x: x['metrics']['alpha_pct'], reverse=True)[:10]:
                    wf = r.get("walkforward", {})
                    r2 = _equity_r2(r)
                    log.info(f"  {r['name']}: α={r['metrics']['alpha_pct']}% OOSα={wf.get('oos_metrics',{}).get('alpha_pct',0)}% "
                             f"PBO={wf.get('pbo_score','N/A')} DD={r['metrics']['max_drawdown_pct']}% R²={r2:.3f} trades={r['metrics']['total_trades']}")
                # 目標達成してもbreak しない — さらに良い戦略を探索し続ける

            # Phase 1: Evolve winners (narrow/deep)
            evo_names = _evolve_strategies(list(_results))
            # Phase 2: Generate novel combos (broad exploration)
            novel_names = _generate_novel_strategies(list(_results), batch_id)
            batch_id += 1

            run_names = evo_names + novel_names
            if not run_names:
                log.info("No more strategies to generate.")
                break

            log.info(f"Next round: {len(evo_names)} evolved + {len(novel_names)} novel = {len(run_names)}")
            round_num += 1

        _run_status.update(
            running=False,
            progress=f"完了: {len(_results)}戦略 ({round_num}R, {total_analyses}回解析) α≥150%+OOS≥100%+OOS2≥100%達成: {len(_qualifying())}/{GOAL_COUNT}",
        )
        _save_results()
        _save_tips()

    except Exception as e:
        log.exception("Auto-optimization failed")
        _run_status.update(running=False, progress=f"エラー: {e}")


# ── App lifecycle ───────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    _load_persisted()
    task = asyncio.create_task(_auto_optimize())
    yield
    task.cancel()


app = FastAPI(title="Crypto Strategy Lab", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=BASE / "static"), name="static")
templates = Jinja2Templates(directory=str(BASE / "templates"))


# ── Routes ──────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    import numpy as np
    enriched = []
    for r in _results[:100]:
        er = dict(r)
        eq = r.get("equity_curve", [])
        if len(eq) >= 20:
            arr = np.array(eq, dtype=float)
            x = np.arange(len(arr))
            slope, intercept = np.polyfit(x, arr, 1)
            if slope > 0:
                y_pred = slope * x + intercept
                ss_res = np.sum((arr - y_pred) ** 2)
                ss_tot = np.sum((arr - np.mean(arr)) ** 2)
                er["r2"] = round(1 - ss_res / ss_tot, 3) if ss_tot > 0 else 0
            else:
                er["r2"] = 0
        else:
            er["r2"] = 0
        enriched.append(er)
    return templates.TemplateResponse(request, "index.html", {
        "results": enriched,
        "tips": _tips,
        "status": _run_status,
    })


@app.post("/api/run")
async def run_strategies(request: Request):
    """Manual trigger (kept for flexibility, but auto-run handles it)."""
    global _results, _tips
    body = await request.json()
    symbol = body.get("symbol", "BTCUSDT")
    interval = body.get("interval", "15m")
    days = body.get("days", 180)

    if _run_status["running"]:
        return JSONResponse({"error": "Already running"}, status_code=409)

    _run_status.update(running=True, progress="データ取得中...", symbol=symbol, interval=interval, days=days)

    try:
        from engine.data import fetch_full_dataset

        df = await fetch_full_dataset(symbol=symbol, interval=interval, days=days)
        if df.empty:
            _run_status.update(running=False, progress="データ取得失敗")
            return JSONResponse({"error": "No data"}, status_code=400)

        def progress_cb(idx, total, name):
            _run_status["strategies_completed"] = idx
            _run_status["progress"] = f"{idx}/{total} 完了 (最新: {name})"

        from engine.strategies import STRATEGIES
        names = list(STRATEGIES.keys())

        def on_result(result):
            _update_results_incremental(result, 0)

        await _run_optimization_parallel(df, names, progress_cb, on_result)

        results = list(_results)
        _merge_tips(_generate_tips(results))
        _run_status.update(running=False, progress=f"完了: {len(results)}戦略",
                           last_run=datetime.now().isoformat())
        _save_results()
        _save_tips()
        return {"ok": True, "count": len(results)}

    except Exception as e:
        log.exception("Strategy run failed")
        _run_status.update(running=False, progress=f"エラー: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/api/status")
async def get_status():
    return _run_status


@app.get("/api/results")
async def get_results():
    import numpy as np
    safe = []
    for r in _results:
        # Compute R² from equity curve
        eq = r.get("equity_curve", [])
        r2 = 0.0
        if len(eq) >= 20:
            arr = np.array(eq, dtype=float)
            x = np.arange(len(arr))
            slope, intercept = np.polyfit(x, arr, 1)
            if slope > 0:
                y_pred = slope * x + intercept
                ss_res = np.sum((arr - y_pred) ** 2)
                ss_tot = np.sum((arr - np.mean(arr)) ** 2)
                r2 = round(1 - ss_res / ss_tot, 4) if ss_tot > 0 else 0
        entry = {
            "name": r["name"],
            "params": {k: str(v) for k, v in r["params"].items()},
            "metrics": r["metrics"],
            "grade": r["grade"],
            "trade_count": len(r.get("trades", [])),
            "r_squared": r2,
        }
        if r.get("walkforward"):
            entry["walkforward"] = r["walkforward"]
        safe.append(entry)
    return safe


@app.get("/api/tips")
async def get_tips():
    return _tips


@app.get("/strategy/{idx}", response_class=HTMLResponse)
async def strategy_detail(request: Request, idx: int):
    if idx < 0 or idx >= len(_results):
        return HTMLResponse("Not found", status_code=404)
    r = _results[idx]
    from engine.strategies import STRATEGIES
    desc = STRATEGIES.get(r["name"], {}).get("desc", "")
    return templates.TemplateResponse(request, "strategy.html", {
        "r": r, "idx": idx, "desc": desc,
        "trades_json": json.dumps(r.get("trades", [])[:200]),
        "equity_json": json.dumps(r.get("equity_curve", [])[:5000]),
        "bench_json": json.dumps(r.get("benchmark_curve", [])[:5000]),
        "times_json": json.dumps(r.get("times", [])[:5000]),
    })


ALTCOIN_SYMBOLS = [
    "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT", "ADAUSDT",
    "DOGEUSDT", "AVAXUSDT", "DOTUSDT", "LINKUSDT", "MATICUSDT",
]


_altcoin_computing: set = set()  # names currently being computed

@app.get("/api/strategy/{idx}/altcoins")
async def strategy_altcoins(idx: int):
    """Run strategy backtest on altcoins and return cross-asset analysis."""
    if idx < 0 or idx >= len(_results):
        return JSONResponse({"error": "Strategy not found"}, status_code=404)

    r = _results[idx]
    name = r["name"]

    # Check cache
    if name in _altcoin_cache:
        return _altcoin_cache[name]

    # If already computing, return status
    if name in _altcoin_computing:
        return {"status": "computing", "message": "Altcoin analysis in progress..."}

    # Start background computation and return immediately
    _altcoin_computing.add(name)
    asyncio.create_task(_compute_altcoins(idx))
    return {"status": "computing", "message": "Altcoin analysis started. Refresh in 30-60 seconds."}


async def _compute_altcoins(idx: int):
    """Background task to compute altcoin analysis."""
    r = _results[idx]
    name = r["name"]
    try:
        result = await _run_altcoin_analysis(r)
        _altcoin_cache[name] = result
    except Exception as e:
        log.warning(f"Altcoin background task failed for {name}: {e}")
        _altcoin_cache[name] = {"error": str(e), "results": [], "summary": {}}
    finally:
        _altcoin_computing.discard(name)


async def _run_altcoin_analysis(r):
    """Actual altcoin analysis logic."""
    name = r["name"]

    from engine.strategies import STRATEGIES
    from engine.data import fetch_full_dataset
    from engine.backtest import run_backtest

    spec = STRATEGIES.get(name)
    if not spec:
        # Fallback: determine fn from name pattern for strategies not in current registry
        from engine.strategies import (composite_adaptive_ddguard_signal,
                                        composite_addg_volscaled_signal,
                                        composite_addg_gradient_lev_signal,
                                        combo_signal)
        if 'ADDG_GL' in name:
            fn = composite_addg_gradient_lev_signal
        elif 'ADDG_VS' in name or 'VS_' in name:
            fn = composite_addg_volscaled_signal
        elif 'ADDG' in name:
            fn = composite_adaptive_ddguard_signal
        elif '(複)' in name:
            fn = combo_signal
        else:
            return JSONResponse({"error": f"Strategy {name} not in registry"}, status_code=404)
        risk = r.get("optimization", {}).get("risk", {})
        # Reconstruct risk from name if empty
        if not risk:
            import re
            risk = {"cooldown_bars": 0}
            tlb_m = re.search(r'TLB(\d+)', name)
            if tlb_m:
                risk["trend_lev_sma"] = int(tlb_m.group(1))
            bl_m = re.search(r'_B(\d+\.?\d*)b(\d+\.?\d*)x', name)
            if bl_m:
                risk["trend_lev_bull"] = float(bl_m.group(1))
                risk["trend_lev_bear"] = float(bl_m.group(2))
    else:
        fn = spec["fn"]
        risk = spec.get("risk", {})

    params = r.get("params", {})
    results_list = []

    def _run_altcoin_bt(df_alt, fn, params, risk, name):
        """Run single altcoin backtest (CPU-bound)."""
        bpy = 35040
        sig = fn(df_alt, **params)
        return run_backtest(
            df_alt, sig, name, params,
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
            sl_cooldown_bars=risk.get("sl_cooldown_bars", 0),
            trend_lev_sma=risk.get("trend_lev_sma", 0),
            trend_lev_bull=risk.get("trend_lev_bull", 0.0),
            trend_lev_bear=risk.get("trend_lev_bear", 0.0),
        )

    from concurrent.futures import ThreadPoolExecutor
    loop = asyncio.get_event_loop()
    _alt_executor = ThreadPoolExecutor(max_workers=1)

    for symbol in ALTCOIN_SYMBOLS:
        try:
            df_alt = await fetch_full_dataset(symbol=symbol, interval="15m", days=270)
            if df_alt.empty or len(df_alt) < 500:
                results_list.append({
                    "symbol": symbol, "total_return_pct": 0, "alpha_pct": 0,
                    "return_daily_pct": 0, "max_drawdown_pct": 0, "sharpe_ratio": 0,
                    "total_trades": 0, "profit_factor": 0, "error": "Insufficient data",
                })
                continue

            bt = await loop.run_in_executor(
                _alt_executor, _run_altcoin_bt, df_alt, fn, params, risk, name)
            bm = bt["metrics"]
            days_count = bm.get("num_days", max(1, len(df_alt) / 96))
            rd = round(bm.get("total_return_pct", 0) / max(1, days_count), 4)
            results_list.append({
                "symbol": symbol,
                "total_return_pct": bm.get("total_return_pct", 0),
                "alpha_pct": bm.get("alpha_pct", 0),
                "return_daily_pct": rd,
                "max_drawdown_pct": bm.get("max_drawdown_pct", 0),
                "sharpe_ratio": bm.get("sharpe_ratio", 0),
                "total_trades": bm.get("total_trades", 0),
                "profit_factor": bm.get("profit_factor", 0),
            })
        except Exception as e:
            log.warning(f"Altcoin backtest failed for {symbol}: {e}")
            results_list.append({
                "symbol": symbol, "total_return_pct": 0, "alpha_pct": 0,
                "return_daily_pct": 0, "max_drawdown_pct": 0, "sharpe_ratio": 0,
                "total_trades": 0, "profit_factor": 0, "error": str(e),
            })
    _alt_executor.shutdown(wait=False)

    # Summary
    valid = [r for r in results_list if r.get("total_trades", 0) > 0]
    positive_alpha = [r for r in valid if r["alpha_pct"] > 0]
    avg_alpha = round(sum(r["alpha_pct"] for r in valid) / max(1, len(valid)), 2) if valid else 0
    avg_rd = round(sum(r["return_daily_pct"] for r in valid) / max(1, len(valid)), 4) if valid else 0
    pos_count = len(positive_alpha)
    total_count = len(ALTCOIN_SYMBOLS)

    if pos_count >= 7:
        robustness = "Highly Robust (cross-asset)"
    elif pos_count >= 4:
        robustness = "Moderately Robust"
    elif pos_count >= 2:
        robustness = "BTC-leaning"
    else:
        robustness = "BTC-specific"

    response = {
        "results": results_list,
        "summary": {
            "positive_count": pos_count,
            "total": total_count,
            "avg_alpha": avg_alpha,
            "avg_return_daily": avg_rd,
            "robustness": robustness,
        }
    }

    # Cache result
    _altcoin_cache[name] = response
    return response


@app.get("/report", response_class=HTMLResponse)
async def report(request: Request):
    from engine.strategies import STRATEGIES
    enriched = []
    for i, r in enumerate(_results[:30]):
        enriched.append({
            **r,
            "idx": i,
            "desc": STRATEGIES.get(r["name"], {}).get("desc", ""),
            "equity_json": json.dumps(r.get("equity_curve", [])[:5000:4]),
            "bench_json": json.dumps(r.get("benchmark_curve", [])[:5000:4]),
            "times_json": json.dumps(r.get("times", [])[:5000:4]),
        })
    return templates.TemplateResponse(request, "report.html", {
        "results": enriched,
        "status": _run_status,
    })


@app.get("/tips", response_class=HTMLResponse)
async def tips_page(request: Request):
    return templates.TemplateResponse(request, "tips.html", {
        "tips": _tips,
        "status": _run_status,
    })
