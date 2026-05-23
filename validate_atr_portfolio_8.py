"""ATR_Ratio_Compression 8-symbol portfolio — correlation + Walk-Forward stress.

Validates the Wave G core portfolio recommendation:
  OP, WIF, INJ, BONK, DOGE, SHIB, ARB, LINK

For each symbol:
  - Walk-Forward 4-fold (each fold must be Sharpe > 0)
  - Returns time series for correlation matrix

Then:
  - Pairwise daily-return correlation
  - Average pairwise correlation
  - Equal-weight portfolio Sharpe vs sum of individual Sharpes
"""
import asyncio
import json
import sys
import time
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

PARAMS = {"atr_short": 7, "atr_long": 56, "threshold": 0.6,
          "ema_fast": 20, "ema_slow": 80}
EXIT = {"stop_loss_pct": 0.04, "take_profit_pct": 0.08, "max_hold_bars": 24}
DAYS = 730
BARS_PER_YEAR = 2190


def atr_ratio_signal(df, atr_short=7, atr_long=56, threshold=0.6,
                     ema_fast=20, ema_slow=80):
    atr_s = (df['high'] - df['low']).rolling(atr_short).mean()
    atr_l = (df['high'] - df['low']).rolling(atr_long).mean()
    compression = atr_s < atr_l * threshold
    ema_f = df['close'].ewm(span=ema_fast).mean()
    ema_s = df['close'].ewm(span=ema_slow).mean()
    sig = pd.Series(0, index=df.index)
    sig[compression & (ema_f > ema_s)] = 1
    sig[compression & (ema_f < ema_s)] = -1
    warmup = max(atr_long, ema_slow) + 5
    sig.iloc[:warmup] = 0
    return sig


def run_bt(df, sig, sym):
    cost = get_cost_params(sym, "4h")
    return run_backtest(df, sig, strategy_name="ATR_Ratio",
                        bars_per_year=BARS_PER_YEAR, leverage=1.0,
                        **EXIT, **cost)


def equity_to_daily_returns(eq):
    eq = np.asarray(eq, dtype=float)
    # 4h bars → 6 per day; sample every 6th
    daily = eq[5::6]
    if len(daily) < 2:
        daily = eq[::6]
    ret = np.diff(daily) / np.where(daily[:-1] != 0, daily[:-1], 1.0)
    return ret


def sharpe(r, ppy=365):
    r = np.asarray(r)
    r = r[np.isfinite(r)]
    if len(r) < 5 or np.std(r, ddof=1) == 0:
        return 0.0
    return float(np.mean(r) / np.std(r, ddof=1) * np.sqrt(ppy))


def walk_forward(df, sym):
    n = len(df)
    fold_size = n // 5
    folds = []
    for i in range(4):
        train_end = fold_size * (i + 1)
        test_start = train_end
        test_end = min(train_end + fold_size, n)
        if test_end - test_start < 50:
            folds.append(None)
            continue
        df_test = df.iloc[test_start:test_end].reset_index(drop=True)
        sig = atr_ratio_signal(df_test, **PARAMS)
        if (sig != 0).sum() < 3:
            folds.append(0.0)
            continue
        r = run_bt(df_test, sig, sym)
        folds.append(round(r["metrics"]["sharpe_ratio"], 3))
    return folds


async def main():
    t0 = time.time()
    print(f"=== ATR_Ratio 8-Symbol Portfolio Validation ===\n")

    data = {}
    print("Loading data ...")
    for s in SYMBOLS:
        df = await fetch_klines(s, "4h", DAYS)
        data[s] = df
        print(f"  {s:<10} {len(df)} bars")
    print()

    results = {}
    daily_returns = {}

    for s in SYMBOLS:
        df = data[s]
        sig = atr_ratio_signal(df, **PARAMS)
        n_sig = (sig != 0).sum()
        r = run_bt(df, sig, s)
        m = r["metrics"]

        # Walk-Forward
        wf = walk_forward(df, s)
        wf_pass = all(x is not None and x > 0 for x in wf)

        # Daily returns for correlation
        d_ret = equity_to_daily_returns(r["equity_curve"])
        daily_returns[s] = d_ret

        results[s] = {
            "sharpe": round(float(m.get("sharpe_ratio", 0) or 0), 3),
            "return_pct": round(float(m.get("total_return_pct", 0) or 0), 2),
            "max_dd_pct": round(float(m.get("max_drawdown_pct", 0) or 0), 2),
            "win_rate": round(float(m.get("win_rate_pct", 0) or 0), 2),
            "trades": int(m.get("total_trades", 0) or 0),
            "signal_bars": int(n_sig),
            "wf_folds": wf,
            "wf_pass": wf_pass,
            "wf_avg": round(np.nanmean([x for x in wf if x is not None]), 3) if any(x is not None for x in wf) else None,
        }
        flag = "✓ WF 4/4" if wf_pass else "✗ WF FAIL"
        print(f"{s:<10} Sh={results[s]['sharpe']:+.2f} ret={results[s]['return_pct']:+.1f}% "
              f"dd={results[s]['max_dd_pct']:+.1f}% trades={results[s]['trades']:>3}  "
              f"WF={wf}  {flag}")

    # ── Correlation matrix ───────────────────────────────────────────────
    print("\n── Daily return correlation matrix ──")
    aligned = {}
    min_len = min(len(v) for v in daily_returns.values())
    for s, r in daily_returns.items():
        aligned[s] = r[:min_len]
    df_ret = pd.DataFrame(aligned)
    corr = df_ret.corr()
    print(f"  (n={min_len} daily observations per symbol)")
    print(corr.round(2).to_string())

    # Pairwise mean (off-diag)
    n_sym = len(SYMBOLS)
    off = corr.values[np.triu_indices(n_sym, k=1)]
    mean_corr = float(np.mean(off))
    max_corr = float(np.max(off))
    min_corr = float(np.min(off))
    print(f"\n  Pairwise corr: mean={mean_corr:+.3f}, max={max_corr:+.3f}, min={min_corr:+.3f}")

    # ── Equal-weight portfolio ──────────────────────────────────────────
    port_ret = df_ret.mean(axis=1)
    port_sharpe = sharpe(port_ret.values, ppy=365)
    individual_sharpes = [results[s]["sharpe"] for s in SYMBOLS if results[s]["sharpe"] > 0]
    mean_indiv = float(np.mean(individual_sharpes))
    # Annualized portfolio return + max DD
    port_cum = (1 + port_ret).cumprod()
    port_total_ret_pct = (port_cum.iloc[-1] - 1) * 100
    running_max = port_cum.cummax()
    port_dd = (port_cum / running_max - 1).min() * 100

    print(f"\n── Equal-weight portfolio ──")
    print(f"  Daily-return Sharpe: {port_sharpe:+.2f}")
    print(f"  Total return:        {port_total_ret_pct:+.1f}%")
    print(f"  Max drawdown:        {port_dd:+.1f}%")
    print(f"  Mean individual Sh:  {mean_indiv:+.2f}")
    diversification_ratio = port_sharpe / mean_indiv if mean_indiv > 0 else 0
    print(f"  分散効果 (port/mean): {diversification_ratio:.2f} (>1 で分散効果あり)")

    # ── WF pass count ───────────────────────────────────────────────────
    wf_passes = sum(1 for s in SYMBOLS if results[s]["wf_pass"])
    print(f"\n── Walk-Forward summary ──")
    print(f"  WF 4/4 pass: {wf_passes}/{len(SYMBOLS)} symbols")
    for s in SYMBOLS:
        if not results[s]["wf_pass"]:
            print(f"    ✗ {s}: {results[s]['wf_folds']}")

    # Save
    out = {
        "strategy": "ATR_Ratio_Compression",
        "params": PARAMS,
        "exit": EXIT,
        "symbols": SYMBOLS,
        "generated_at": datetime.now(timezone(timedelta(hours=9))).strftime("%Y-%m-%d %H:%M JST"),
        "per_symbol": results,
        "correlation_matrix": corr.round(4).to_dict(),
        "pairwise_corr": {"mean": round(mean_corr, 4), "max": round(max_corr, 4), "min": round(min_corr, 4)},
        "portfolio_eq_weight": {
            "sharpe": round(port_sharpe, 3),
            "total_return_pct": round(float(port_total_ret_pct), 2),
            "max_dd_pct": round(float(port_dd), 2),
            "mean_individual_sharpe": round(mean_indiv, 3),
            "diversification_ratio": round(diversification_ratio, 3),
        },
        "wf_passes": f"{wf_passes}/{len(SYMBOLS)}",
        "runtime_sec": round(time.time() - t0, 1),
    }
    Path("/Users/nekonaomichi/crypto-lab/atr_portfolio_8.json").write_text(json.dumps(out, indent=2, default=str))
    print(f"\nSaved to atr_portfolio_8.json (runtime {out['runtime_sec']}s)")


if __name__ == "__main__":
    asyncio.run(main())
