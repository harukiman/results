"""Wave G — Broad Universe Validation.

Re-validates the 5 main survivor strategy families across a 26-symbol universe,
spanning 7 tiers (Major/LargeCap/MidCap/SmallCap/L2/DeFi/Meme).

Goal:
  - Distinguish broad-edge strategies (work across many symbols) from
    symbol-specific overfits (work only on the original survivor symbol).
  - Identify which symbols, beyond DOGE/AVAX/SUI/BONK, host genuine alpha.
  - Produce a consolidated per-strategy, per-tier finding sheet.

5 strategy families with frozen best parameters:
  1. VolReg_4h       — vol compression + EMA trend
  2. ATR_Ratio       — H-L range compression + EMA trend
  3. SampEn          — entropy-based regularity detection + EMA trend
  4. Vol_Smile_Skew  — semi-variance asymmetry (fear/euphoria)
  5. MemeMomentum    — EMA cross + RSI + volume confirm (meme-tuned)
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

# ── Universe (27 symbols, 7 tiers) ──────────────────────────────────────────

TIERS = {
    "Major":    ["BTCUSDT", "ETHUSDT"],
    "LargeCap": ["SOLUSDT", "BNBUSDT", "XRPUSDT"],
    "MidCap":   ["ADAUSDT", "DOTUSDT", "LINKUSDT", "AVAXUSDT", "ATOMUSDT", "LTCUSDT"],
    "SmallCap": ["SUIUSDT", "APTUSDT", "NEARUSDT", "INJUSDT", "TIAUSDT", "SEIUSDT"],
    "L2":       ["ARBUSDT", "OPUSDT"],
    "DeFi":     ["UNIUSDT", "AAVEUSDT"],
    "Meme":     ["DOGEUSDT", "PEPEUSDT", "SHIBUSDT", "BONKUSDT", "WIFUSDT"],
}
SYMBOL_TO_TIER = {s: t for t, syms in TIERS.items() for s in syms}
ALL_SYMBOLS = [s for syms in TIERS.values() for s in syms]

BARS_PER_YEAR = 2190  # 4h bars
DAYS = 730


# ── Signal functions (best params frozen from survivor scans) ───────────────

def volreg_signal(df, short_vol=10, long_vol=25, threshold=0.7,
                  ema_fast=14, ema_slow=40):
    returns = df['close'].pct_change()
    short_v = returns.rolling(short_vol).std()
    long_v = returns.rolling(long_vol).std()
    compression = short_v < long_v * threshold
    ema_f = df['close'].ewm(span=ema_fast).mean()
    ema_s = df['close'].ewm(span=ema_slow).mean()
    sig = pd.Series(0, index=df.index)
    sig[compression & (ema_f > ema_s)] = 1
    sig[compression & (ema_f < ema_s)] = -1
    warmup = max(long_vol, ema_slow) + 5
    sig.iloc[:warmup] = 0
    return sig


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


def _sampen_fast(returns_arr, m=2, r_mult=0.2, apen_window=50):
    n = len(returns_arr)
    out = np.full(n, np.nan)
    for i in range(apen_window, n):
        window = returns_arr[i - apen_window:i]
        r = r_mult * np.std(window)
        if r < 1e-12:
            out[i] = 0.0
            continue
        def _cnt(tlen):
            if len(window) - tlen < 2:
                return 0
            tpls = np.lib.stride_tricks.sliding_window_view(window, tlen)
            c = 0
            for j in range(len(tpls)):
                d = np.max(np.abs(tpls - tpls[j]), axis=1)
                c += np.sum(d < r) - 1
            return c
        B = _cnt(m)
        A = _cnt(m + 1)
        out[i] = -np.log(A / B) if (A > 0 and B > 0) else 0.0
    return out


def sampen_signal(df, m=2, r_mult=0.2, apen_window=50, apen_pct=20,
                  ema_fast=20, ema_slow=80):
    returns = df['close'].pct_change().fillna(0).values
    vals = _sampen_fast(returns, m=m, r_mult=r_mult, apen_window=apen_window)
    s = pd.Series(vals, index=df.index)
    thr = s.expanding(min_periods=50).quantile(apen_pct / 100.0)
    low_e = s < thr
    ema_f = df['close'].ewm(span=ema_fast).mean()
    ema_s = df['close'].ewm(span=ema_slow).mean()
    sig = pd.Series(0, index=df.index)
    sig[low_e & (ema_f > ema_s)] = 1
    sig[low_e & (ema_f < ema_s)] = -1
    warmup = max(apen_window + 20, ema_slow + 20)
    sig.iloc[:warmup] = 0
    return sig


def vol_smile_skew_signal(df, window=24, skew_threshold=1.0, trend_window=40):
    returns = df['close'].pct_change()
    rv = returns.values
    up_sq = pd.Series(np.where(rv > 0, rv, 0.0) ** 2, index=df.index)
    dn_sq = pd.Series(np.where(rv < 0, rv, 0.0) ** 2, index=df.index)
    up_vol = up_sq.rolling(window, min_periods=window // 2).mean().apply(np.sqrt)
    dn_vol = dn_sq.rolling(window, min_periods=window // 2).mean().apply(np.sqrt)
    skew_r = (up_vol / (dn_vol + 1e-10)) - 1.0
    trend_ma = df['close'].rolling(trend_window).mean()
    up_t = df['close'] > trend_ma
    dn_t = df['close'] < trend_ma
    skew_mean = skew_r.rolling(window * 3).mean()
    skew_std = skew_r.rolling(window * 3).std()
    skew_z = (skew_r - skew_mean) / (skew_std + 1e-10)
    sig = pd.Series(0, index=df.index)
    sig[(skew_z < -skew_threshold) & up_t] = 1
    sig[(skew_z > skew_threshold) & dn_t] = -1
    warmup = max(window * 4, trend_window) + 20
    sig.iloc[:warmup] = 0
    return sig


def meme_momentum_signal(df, ema_fast=5, ema_slow=21, rsi_period=14,
                         rsi_lower=35, rsi_upper=65, vol_mult=1.3, vol_lookback=15):
    ef = df["close"].ewm(span=ema_fast, adjust=False).mean()
    es = df["close"].ewm(span=ema_slow, adjust=False).mean()
    d = df["close"].diff()
    gain = d.where(d > 0, 0).ewm(span=rsi_period, adjust=False).mean()
    loss = (-d.where(d < 0, 0)).ewm(span=rsi_period, adjust=False).mean()
    rs = gain / loss.replace(0, np.nan)
    rsi = 100 - 100 / (1 + rs)
    vma = df["volume"].rolling(vol_lookback, min_periods=5).mean()
    vc = df["volume"] > vma * vol_mult
    bull = (ef > es) & (ef.shift(1) <= es.shift(1))
    bear = (ef < es) & (ef.shift(1) >= es.shift(1))
    sig = pd.Series(0, index=df.index)
    sig[bull & (rsi > rsi_lower) & (rsi < rsi_upper) & vc] = 1
    sig[bear & (rsi > rsi_lower) & (rsi < rsi_upper) & vc] = -1
    regime = sig.copy()
    cur = 0
    for i in range(len(regime)):
        if sig.iloc[i] != 0:
            cur = sig.iloc[i]
        regime.iloc[i] = cur
    warmup = max(ema_slow, vol_lookback) + 5
    regime.iloc[:warmup] = 0
    return regime


# ── Strategy registry (frozen best params + exit rules) ─────────────────────

STRATEGIES = {
    "VolReg_4h": {
        "fn": volreg_signal,
        "params": {"short_vol": 10, "long_vol": 25, "threshold": 0.7,
                   "ema_fast": 14, "ema_slow": 40},
        "exit":  {"stop_loss_pct": 0.04, "take_profit_pct": 0.06, "max_hold_bars": 24},
        "anchor_symbol": "DOGEUSDT",
        "anchor_sharpe": 2.275,
    },
    "ATR_Ratio_Compression": {
        "fn": atr_ratio_signal,
        "params": {"atr_short": 7, "atr_long": 56, "threshold": 0.6,
                   "ema_fast": 20, "ema_slow": 80},
        "exit":  {"stop_loss_pct": 0.04, "take_profit_pct": 0.08, "max_hold_bars": 24},
        "anchor_symbol": "AVAXUSDT",
        "anchor_sharpe": 3.06,
    },
    "SampEn": {
        "fn": sampen_signal,
        "params": {"m": 2, "r_mult": 0.2, "apen_window": 50, "apen_pct": 20,
                   "ema_fast": 20, "ema_slow": 80},
        "exit":  {"stop_loss_pct": 0.04, "take_profit_pct": 0.08, "max_hold_bars": 24},
        "anchor_symbol": "DOGEUSDT",
        "anchor_sharpe": 2.26,
    },
    "Vol_Smile_Skew": {
        "fn": vol_smile_skew_signal,
        "params": {"window": 24, "skew_threshold": 1.0, "trend_window": 40},
        "exit":  {"stop_loss_pct": 0.02, "take_profit_pct": 0.06, "max_hold_bars": 24},
        "anchor_symbol": "SUIUSDT",
        "anchor_sharpe": 2.286,
    },
    "MemeMomentum": {
        "fn": meme_momentum_signal,
        "params": {"ema_fast": 5, "ema_slow": 21, "rsi_period": 14,
                   "rsi_lower": 35, "rsi_upper": 65, "vol_mult": 1.3, "vol_lookback": 15},
        "exit":  {"stop_loss_pct": 0.05, "take_profit_pct": 0.15, "max_hold_bars": 30},
        "anchor_symbol": "BONKUSDT",
        "anchor_sharpe": 2.341,
    },
}


# ── Backtest helper ─────────────────────────────────────────────────────────

def run_one(df, sig, strat_name, symbol, exit_params):
    try:
        cost = get_cost_params(symbol, "4h")
        result = run_backtest(
            df, sig, strategy_name=strat_name,
            bars_per_year=BARS_PER_YEAR, leverage=1.0,
            **exit_params, **cost,
        )
        m = result["metrics"]
        return {
            "sharpe": round(float(m.get("sharpe_ratio", 0) or 0), 3),
            "return_pct": round(float(m.get("total_return_pct", 0) or 0), 2),
            "max_dd_pct": round(float(m.get("max_drawdown_pct", 0) or 0), 2),
            "trades": int(m.get("total_trades", 0) or 0),
            "win_rate": round(float(m.get("win_rate_pct", 0) or 0), 2),
        }
    except Exception as e:
        return {"error": str(e), "sharpe": None, "return_pct": None,
                "max_dd_pct": None, "trades": 0, "win_rate": None}


# ── Main scan ───────────────────────────────────────────────────────────────

async def main():
    t_start = time.time()
    print(f"=== Wave G: Broad Universe Validation ===")
    print(f"Universe: {len(ALL_SYMBOLS)} symbols across {len(TIERS)} tiers")
    print(f"Strategies: {len(STRATEGIES)}")
    print(f"Total backtests: {len(ALL_SYMBOLS) * len(STRATEGIES)}")
    print()

    data_cache = {}
    print("Loading data ...")
    for sym in ALL_SYMBOLS:
        try:
            df = await fetch_klines(sym, "4h", DAYS)
            if df is None or df.empty or len(df) < 200:
                print(f"  {sym:<10} SKIP (insufficient data)")
                continue
            data_cache[sym] = df
            print(f"  {sym:<10} {len(df)} bars")
        except Exception as e:
            print(f"  {sym:<10} ERROR {e}")

    print(f"\nLoaded {len(data_cache)} symbols. Beginning scan ...\n")

    results = {}  # results[strat][symbol] = metrics
    for strat_name, strat in STRATEGIES.items():
        print(f"--- {strat_name} ---")
        results[strat_name] = {}
        sig_fn = strat["fn"]
        params = strat["params"]
        exits = strat["exit"]

        for sym in ALL_SYMBOLS:
            if sym not in data_cache:
                results[strat_name][sym] = {"skipped": True}
                continue
            df = data_cache[sym]
            try:
                sig = sig_fn(df, **params)
                n_sig = (sig != 0).sum()
                if n_sig < 5:
                    results[strat_name][sym] = {"trades": 0, "sharpe": 0.0,
                                                "note": "too few signals", "n_signal_bars": int(n_sig)}
                    continue
                m = run_one(df, sig, strat_name, sym, exits)
                m["n_signal_bars"] = int(n_sig)
                m["tier"] = SYMBOL_TO_TIER[sym]
                results[strat_name][sym] = m
                if m.get("sharpe") is not None:
                    flag = "★" if m["sharpe"] >= 1.5 else ("+" if m["sharpe"] >= 0.5 else " ")
                    print(f"  {flag} {sym:<10} Sh={m['sharpe']:>+5.2f}  ret={m['return_pct']:>+7.1f}%  "
                          f"dd={m['max_dd_pct']:>+6.1f}%  trades={m['trades']:>4}  WR={m['win_rate']:>5.1f}%")
                else:
                    print(f"    {sym:<10} ERROR")
            except Exception as e:
                results[strat_name][sym] = {"error": str(e)}
                print(f"    {sym:<10} EXC {e}")
        print()

    # ── Per-strategy summary ─────────────────────────────────────────────
    print(f"\n{'='*70}")
    print("CONSOLIDATED FINDINGS")
    print(f"{'='*70}\n")

    summary = {}
    for strat_name, by_sym in results.items():
        valid = [(s, r) for s, r in by_sym.items()
                 if isinstance(r, dict) and r.get("sharpe") is not None
                 and r.get("trades", 0) >= 5]
        if not valid:
            continue
        valid.sort(key=lambda x: x[1]["sharpe"], reverse=True)

        n_total = len(valid)
        n_pos = sum(1 for _, r in valid if r["sharpe"] > 0)
        n_strong = sum(1 for _, r in valid if r["sharpe"] >= 1.0)
        n_excellent = sum(1 for _, r in valid if r["sharpe"] >= 2.0)
        top3 = valid[:3]
        # Per-tier breakdown
        tier_pos = {t: 0 for t in TIERS}
        tier_total = {t: 0 for t in TIERS}
        for s, r in valid:
            tier_pos[r["tier"]] += (1 if r["sharpe"] > 0 else 0)
            tier_total[r["tier"]] += 1

        summary[strat_name] = {
            "n_symbols_tested": n_total,
            "n_sharpe_positive": n_pos,
            "n_sharpe_ge_1": n_strong,
            "n_sharpe_ge_2": n_excellent,
            "breadth_rate": round(n_pos / n_total, 3) if n_total else 0,
            "top3": [{"symbol": s, **r} for s, r in top3],
            "tier_breakdown": {t: f"{tier_pos[t]}/{tier_total[t]}" for t in TIERS},
        }

        print(f"### {strat_name}")
        print(f"  Anchor: {STRATEGIES[strat_name]['anchor_symbol']} "
              f"(scan Sharpe {STRATEGIES[strat_name]['anchor_sharpe']})")
        print(f"  Breadth: {n_pos}/{n_total} positive ({n_pos/n_total*100:.0f}%), "
              f"{n_strong} ≥1.0, {n_excellent} ≥2.0")
        print(f"  Top 3:")
        for s, r in top3:
            print(f"    {s:<10} [{r['tier']:<8}] Sh={r['sharpe']:+.2f}  "
                  f"ret={r['return_pct']:+.1f}%  dd={r['max_dd_pct']:+.1f}%  trades={r['trades']}")
        print(f"  Tier breakdown (positive/tested):")
        for t in TIERS:
            print(f"    {t:<10} {tier_pos[t]}/{tier_total[t]}")
        print()

    # ── Save results ─────────────────────────────────────────────────────
    out = {
        "wave": "G",
        "name": "Broad Universe Validation",
        "generated_at": datetime.now(timezone(timedelta(hours=9))).strftime("%Y-%m-%d %H:%M JST"),
        "universe": {"tiers": TIERS, "n_symbols": len(ALL_SYMBOLS),
                     "n_loaded": len(data_cache)},
        "strategies": {k: {kk: vv for kk, vv in v.items() if kk != "fn"}
                       for k, v in STRATEGIES.items()},
        "results_by_strategy": results,
        "summary": summary,
        "runtime_sec": round(time.time() - t_start, 1),
    }
    Path("/Users/nekonaomichi/crypto-lab/wave_g_broad_universe.json").write_text(json.dumps(out, indent=2, default=str))
    print(f"\nSaved to wave_g_broad_universe.json (runtime {out['runtime_sec']}s)")


if __name__ == "__main__":
    asyncio.run(main())
