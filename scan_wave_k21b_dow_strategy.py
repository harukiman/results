"""Wave K21b — Day-of-week bias を実トレード戦略化.

仮説: Wed long, Thu short が全銘柄で一貫 → トレード可能
- Wed (UTC 0-24): Long position
- Thu (UTC 0-24): Short position
- 他の曜日: flat
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

SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "DOGEUSDT"]
DAYS = 730


def dow_signal(df, long_dow=2, short_dow=3):
    """Day-of-week signal. UTC dayofweek: Mon=0, ..., Wed=2, Thu=3, Sun=6.

    long on Wed (dow=2), short on Thu (dow=3), flat else.
    """
    dow = df['open_time'].dt.dayofweek
    sig = np.zeros(len(df), dtype=int)
    sig[dow == long_dow] = +1
    sig[dow == short_dow] = -1
    return pd.Series(sig, index=df.index)


def sharpe(r, ppy=365):
    r = np.asarray(r); r = r[np.isfinite(r)]
    if len(r) < 5 or np.std(r, ddof=1) == 0: return 0.0
    return float(np.mean(r) / np.std(r, ddof=1) * np.sqrt(ppy))


def eq_to_daily(eq, bpd=6):
    eq = np.asarray(eq, dtype=float)
    d = eq[bpd-1::bpd]
    if len(d) < 2: d = eq[::bpd]
    return np.diff(d) / np.where(d[:-1] != 0, d[:-1], 1.0)


def run_bt(df, sig, sym, sl=0.04, tp=0.04, mhb=6):
    cost = get_cost_params(sym, "4h")
    return run_backtest(df, sig, strategy_name="K21",
                        bars_per_year=2190, leverage=1.0,
                        stop_loss_pct=sl, take_profit_pct=tp,
                        max_hold_bars=mhb, **cost)


async def main():
    print("=== Wave K21b: Day-of-week strategy ===\n")

    results = []
    daily_returns_per_sym = {}
    for s in SYMBOLS:
        df = await fetch_klines(s, "4h", DAYS)
        sig = dow_signal(df, long_dow=2, short_dow=3)
        r = run_bt(df, sig, s, sl=0.04, tp=0.04, mhb=6)
        m = r['metrics']
        sh = float(m['sharpe_ratio'])
        ret = float(m['total_return_pct'])
        dd = float(m['max_drawdown_pct'])
        trades = int(m['total_trades'])
        results.append({"symbol": s, "sharpe": round(sh, 3), "return_pct": round(ret, 2),
                        "dd_pct": round(dd, 2), "trades": trades})
        print(f"  {s:<10} Sh={sh:+.2f} ret={ret:+.1f}% dd={dd:+.1f}% trades={trades}")
        daily_returns_per_sym[s] = eq_to_daily(r['equity_curve'])

    # Equal-weight portfolio
    min_l = min(len(v) for v in daily_returns_per_sym.values())
    port = pd.DataFrame({k: v[:min_l] for k, v in daily_returns_per_sym.items()}).mean(axis=1).values
    sh_port = sharpe(port)
    eq = np.cumprod(1 + port)
    ret_port = (eq[-1] - 1) * 100
    dd_port = (eq / np.maximum.accumulate(eq) - 1).min() * 100
    cal_port = abs(ret_port / dd_port) if dd_port != 0 else 0
    print(f"\n=== Portfolio (5-symbol equal-weight) ===")
    print(f"  Sharpe: {sh_port:+.2f}, Return: {ret_port:+.1f}%, DD: {dd_port:+.1f}%, Calmar: {cal_port:.2f}")

    # H1/H2 stability
    n = min_l
    h1 = port[:n//2]
    h2 = port[n//2:]
    print(f"\n=== H1/H2 Period Stability ===")
    for name, p in [("H1", h1), ("H2", h2)]:
        s = sharpe(p)
        eq2 = np.cumprod(1 + p)
        ret2 = (eq2[-1] - 1) * 100
        dd2 = (eq2 / np.maximum.accumulate(eq2) - 1).min() * 100
        print(f"  {name}: Sh={s:+.2f}, Return={ret2:+.1f}%, DD={dd2:+.1f}%")

    Path("/Users/nekonaomichi/crypto-lab/wave_k21b_dow.json").write_text(json.dumps({
        "wave": "K21b", "name": "Day-of-week strategy",
        "per_symbol": results,
        "portfolio": {"sharpe": round(sh_port, 3), "return_pct": round(float(ret_port), 2),
                       "max_dd_pct": round(float(dd_port), 2), "calmar": round(cal_port, 2)},
    }, indent=2, default=str))
    print("\nSaved.")


if __name__ == "__main__":
    asyncio.run(main())
