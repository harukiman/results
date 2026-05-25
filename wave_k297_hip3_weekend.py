"""
Wave K297 — HL HIP-3 RWA Perp Weekend FR Carry Strategy
==========================================================
Objective: Build and backtest a weekend FR carry strategy on HyperLiquid HIP-3
           RWA (real-world asset) perpetuals. Novel mechanism family (RWA + weekend timing).

Steps:
1. Query HL API to enumerate available markets (meta) and identify HIP-3 / RWA perps
2. Fetch FR history for XAG, XAU, and other available RWA perps
3. Compute weekend vs weekday FR breakdown
4. Backtest Friday-close → Monday-open carry position
5. Walk-forward validation
6. Correlation vs K287d components (K270, K275)
7. Write deliverable JSON + parquet cache

Author: K297 agent | 2026-05-25
"""

import json
import os
import time
import requests
import numpy as np
import pandas as pd
from datetime import datetime, timezone, timedelta
from pathlib import Path

# ─────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────
HL_INFO_URL = "https://api.hyperliquid.xyz/info"
CACHE_DIR = Path("/Users/nekonaomichi/crypto-lab/cache")
CACHE_DIR.mkdir(exist_ok=True)

MAKER_COST_PCT = 0.0007   # 7bp/side (round-trip = 14bp)
TAKER_COST_PCT = 0.0025   # 25bp/side for reference

# Weekend window: Friday 16:00 UTC → Monday 14:30 UTC
# Friday = weekday 4, Monday = weekday 0
WEEKEND_ENTRY_DOW = 4    # Friday
WEEKEND_ENTRY_HOUR = 16  # 16:00 UTC (NYSE close)
WEEKEND_EXIT_DOW = 0     # Monday
WEEKEND_EXIT_HOUR = 14   # 14:30 UTC (NYSE open ~9:30 ET)
WEEKEND_EXIT_MIN = 30

# RWA perp candidates to try
RWA_CANDIDATES = ["XAG", "XAU", "CRUDE", "WTI", "OIL", "BRENT", "NQ", "NDX", "SPX", "SPY",
                  "TSLA", "AAPL", "NVDA", "MSFT", "AMZN", "GOOGL", "META", "BRK",
                  "NIKKEI", "FTSE", "DAX", "SILVER", "GOLD", "USOIL", "NATGAS"]

OUTPUT_PREFIX = "/Users/nekonaomichi/crypto-lab/wave_k297"
RESULT_JSON = f"{OUTPUT_PREFIX}_hip3_weekend.json"
CURVES_JSON = f"{OUTPUT_PREFIX}_curves.json"
CACHE_PARQUET = CACHE_DIR / "hl_hip3_fr_daily.parquet"


# ─────────────────────────────────────────────
# STEP 1: Enumerate HL Markets
# ─────────────────────────────────────────────
def fetch_hl_meta():
    """Fetch all HL perp markets metadata."""
    try:
        r = requests.post(HL_INFO_URL, json={"type": "meta"}, timeout=30)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"[meta] Error: {e}")
        return None


def identify_rwa_perps(meta):
    """
    Identify RWA / HIP-3 perps from meta response.
    HL lists non-crypto assets with distinct ticker patterns.
    Returns dict: {symbol: market_info}
    """
    if not meta:
        return {}

    universe = meta.get("universe", [])
    rwa_markets = {}

    # Keywords that identify RWA / TradFi assets
    rwa_keywords = {
        "XAG": "Silver",
        "XAU": "Gold",
        "USOIL": "Crude Oil",
        "WTI": "WTI Crude",
        "BRENT": "Brent Crude",
        "NQ": "NASDAQ Futures",
        "NDX": "NASDAQ Index",
        "SPX": "S&P 500",
        "SPY": "S&P 500 ETF",
        "TSLA": "Tesla",
        "AAPL": "Apple",
        "NVDA": "NVIDIA",
        "MSFT": "Microsoft",
        "AMZN": "Amazon",
        "GOOGL": "Google",
        "META": "Meta",
        "COIN": "Coinbase",
        "MSTR": "MicroStrategy",
        "NATGAS": "Natural Gas",
        "SILVER": "Silver",
        "GOLD": "Gold",
    }

    all_symbols = []
    for mkt in universe:
        sym = mkt.get("name", "")
        all_symbols.append(sym)
        # Check if this is a known RWA asset
        for rwa_sym, rwa_name in rwa_keywords.items():
            if sym.upper() == rwa_sym.upper():
                rwa_markets[sym] = {
                    "name": rwa_name,
                    "market_info": mkt,
                    "max_leverage": mkt.get("maxLeverage", None),
                }
                break

    return rwa_markets, all_symbols


# ─────────────────────────────────────────────
# STEP 2: Fetch Funding Rate History
# ─────────────────────────────────────────────
def fetch_fr_history(coin, start_ms, end_ms):
    """Fetch hourly funding rate history from HL API."""
    all_records = []
    chunk_ms = 7 * 24 * 3600 * 1000  # 7-day chunks

    t = start_ms
    while t < end_ms:
        t_end = min(t + chunk_ms, end_ms)
        payload = {
            "type": "fundingHistory",
            "coin": coin,
            "startTime": t,
            "endTime": t_end,
        }
        try:
            r = requests.post(HL_INFO_URL, json=payload, timeout=30)
            r.raise_for_status()
            data = r.json()
            if data:
                all_records.extend(data)
        except Exception as e:
            print(f"  [{coin}] chunk error {t}: {e}")
        t = t_end + 1
        time.sleep(0.1)

    return all_records


def records_to_df(records, coin):
    """Convert raw FR records to DataFrame."""
    if not records:
        return pd.DataFrame()

    rows = []
    for rec in records:
        ts = rec.get("time", rec.get("timestamp", None))
        fr = rec.get("fundingRate", None)
        if ts and fr is not None:
            rows.append({"timestamp": pd.to_datetime(ts, unit="ms", utc=True),
                         "funding_rate": float(fr),
                         "coin": coin})

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows).sort_values("timestamp").drop_duplicates("timestamp")
    df.set_index("timestamp", inplace=True)
    return df


# ─────────────────────────────────────────────
# STEP 3: Weekend / Weekday Breakdown
# ─────────────────────────────────────────────
def classify_weekend(df):
    """
    Tag each hourly FR record as weekend or weekday.
    Weekend definition: Friday 16:00 UTC → Monday 14:30 UTC
    """
    df = df.copy()
    idx = df.index

    # Day of week (0=Mon, 4=Fri, 5=Sat, 6=Sun)
    dow = idx.dayofweek
    hour = idx.hour
    minute = idx.minute

    # Weekend: Saturday + Sunday entire days
    # + Friday after 16:00 UTC
    # + Monday before 14:30 UTC
    is_sat_sun = (dow == 5) | (dow == 6)
    is_friday_after = (dow == 4) & (hour >= WEEKEND_ENTRY_HOUR)
    is_monday_before = (dow == 0) & ((hour < WEEKEND_EXIT_HOUR) |
                                      ((hour == WEEKEND_EXIT_HOUR) & (minute < WEEKEND_EXIT_MIN)))

    df["is_weekend"] = is_sat_sun | is_friday_after | is_monday_before
    return df


def compute_fr_stats(df):
    """Compute weekend vs weekday FR statistics."""
    if df.empty:
        return {}

    df_c = classify_weekend(df)
    wkend = df_c[df_c["is_weekend"]]["funding_rate"]
    wkday = df_c[~df_c["is_weekend"]]["funding_rate"]

    # Annualize: funding paid every 1h → 8760 payments/year
    HOURS_PER_YEAR = 8760

    return {
        "n_total_hours": len(df_c),
        "n_weekend_hours": len(wkend),
        "n_weekday_hours": len(wkday),
        "weekend_mean_hourly": float(wkend.mean()) if len(wkend) else None,
        "weekday_mean_hourly": float(wkday.mean()) if len(wkday) else None,
        "weekend_apr": float(wkend.mean() * HOURS_PER_YEAR * 100) if len(wkend) else None,
        "weekday_apr": float(wkday.mean() * HOURS_PER_YEAR * 100) if len(wkday) else None,
        "weekend_vs_weekday_ratio": (float(wkend.mean() / wkday.mean())
                                     if len(wkday) and wkday.mean() != 0 else None),
        "weekend_pct_positive": float((wkend > 0).mean() * 100) if len(wkend) else None,
        "weekday_pct_positive": float((wkday > 0).mean() * 100) if len(wkday) else None,
        "weekend_std_hourly": float(wkend.std()) if len(wkend) else None,
        "weekday_std_hourly": float(wkday.std()) if len(wkday) else None,
    }


# ─────────────────────────────────────────────
# STEP 4: Strategy Backtest
# ─────────────────────────────────────────────
def backtest_weekend_carry(df, coin, maker_cost=MAKER_COST_PCT):
    """
    Backtest: Enter Friday 16:00 UTC, exit Monday 14:30 UTC.
    Position: LONG (collect positive funding if FR > 0).
    Net P&L per trade = sum(hourly_fr_during_hold) - round_trip_cost

    Returns dict with performance metrics + daily returns Series.
    """
    if df.empty:
        return None

    df_c = classify_weekend(df).copy()
    df_c = df_c.sort_index()

    # Find Friday 16:00 entry points
    trades = []
    processed_mondays = set()

    fri_entries = df_c[(df_c.index.dayofweek == 4) &
                       (df_c.index.hour == WEEKEND_ENTRY_HOUR)]

    for entry_ts in fri_entries.index:
        # Expected exit: next Monday 14:30 UTC
        # Find the Monday after this Friday
        days_to_monday = (7 - entry_ts.dayofweek) % 7 or 7
        # Friday=4, Monday is 3 days later
        days_ahead = 3
        exit_date = entry_ts.date() + timedelta(days=days_ahead)

        if exit_date in processed_mondays:
            continue
        processed_mondays.add(exit_date)

        exit_ts_target = pd.Timestamp(
            exit_date.year, exit_date.month, exit_date.day,
            WEEKEND_EXIT_HOUR, WEEKEND_EXIT_MIN, 0, tzinfo=timezone.utc
        )

        # Collect all FR records from entry to exit
        mask = (df_c.index >= entry_ts) & (df_c.index <= exit_ts_target)
        hold_period = df_c[mask]

        if len(hold_period) < 10:  # Require at least 10 hours data
            continue

        gross_fr = hold_period["funding_rate"].sum()
        # Round-trip maker cost (enter + exit)
        net_fr = gross_fr - 2 * maker_cost
        n_hours = len(hold_period)

        trades.append({
            "entry_ts": entry_ts,
            "exit_ts": exit_ts_target,
            "n_hours": n_hours,
            "gross_fr": float(gross_fr),
            "net_fr": float(net_fr),
            "is_positive": net_fr > 0,
        })

    if not trades:
        return None

    trades_df = pd.DataFrame(trades)
    trades_df.set_index("entry_ts", inplace=True)

    # Performance metrics
    returns = trades_df["net_fr"].values
    n_trades = len(returns)
    win_rate = float((returns > 0).mean())
    mean_return = float(returns.mean())
    std_return = float(returns.std()) if n_trades > 1 else 0.0

    # Annualize: ~52 weekends/year but trades are per-weekend
    # Each trade is ~64h hold; annualized = mean * 52
    ann_return = mean_return * 52
    ann_vol = std_return * np.sqrt(52) if std_return > 0 else 1e-9
    sharpe = ann_return / ann_vol if ann_vol > 0 else 0.0

    # Equity curve (cumulative)
    cum_returns = (1 + pd.Series(returns, index=trades_df.index)).cumprod()
    max_dd = float((cum_returns / cum_returns.cummax() - 1).min())

    # Daily returns for correlation (assign to Monday of each trade)
    daily_rets = {}
    for _, row in trades_df.iterrows():
        # Spread return over 3 days (Fri-Mon) for correlation
        for d in range(3):
            dt = (row.name + timedelta(days=d)).date()
            daily_rets[str(dt)] = row["net_fr"] / 3

    return {
        "coin": coin,
        "n_trades": n_trades,
        "win_rate": win_rate,
        "mean_net_fr_per_trade": mean_return,
        "std_net_fr_per_trade": std_return,
        "ann_return": ann_return,
        "ann_vol": ann_vol,
        "sharpe": sharpe,
        "max_dd": max_dd,
        "gross_mean_fr": float(trades_df["gross_fr"].mean()),
        "maker_cost_rt": 2 * maker_cost,
        "trades_df": trades_df,
        "daily_rets_dict": daily_rets,
        "equity_curve": cum_returns.to_dict(),
    }


# ─────────────────────────────────────────────
# STEP 5: Walk-Forward Validation
# ─────────────────────────────────────────────
def walk_forward(trades_df, n_folds=3):
    """Simple k-fold WF validation on trade-level returns."""
    if trades_df is None or len(trades_df) < n_folds * 3:
        return None

    rets = trades_df["net_fr"].values
    n = len(rets)
    fold_size = n // n_folds
    folds = []

    for i in range(n_folds):
        start = i * fold_size
        end = start + fold_size if i < n_folds - 1 else n
        fold_rets = rets[start:end]
        mean_r = float(fold_rets.mean())
        std_r = float(fold_rets.std()) if len(fold_rets) > 1 else 1e-9
        ann_r = mean_r * 52
        ann_v = std_r * np.sqrt(52)
        sh = ann_r / ann_v if ann_v > 0 else 0.0
        folds.append({
            "fold": i + 1,
            "n_trades": len(fold_rets),
            "mean_net_fr": mean_r,
            "sharpe": sh,
            "positive": mean_r > 0,
        })

    return {
        "folds": folds,
        "mean_sharpe": float(np.mean([f["sharpe"] for f in folds])),
        "all_positive": all(f["positive"] for f in folds),
    }


# ─────────────────────────────────────────────
# STEP 6: Correlation vs K287d
# ─────────────────────────────────────────────
def compute_correlations(k297_daily_rets_dict):
    """Compute |ρ| correlation with K270 and K275 daily returns."""
    correlations = {}

    # Load K270 equity curve
    try:
        with open("/Users/nekonaomichi/crypto-lab/wave_k270_curves.json") as f:
            k270_curves = json.load(f)
        # Compute daily returns from equity curve
        k270_eq = pd.Series(k270_curves.get("equity_curve", {}))
        k270_eq.index = pd.to_datetime(k270_eq.index)
        k270_dr = k270_eq.pct_change().dropna()
        k270_dr.index = k270_dr.index.astype(str)
        correlations["K270_available"] = True
    except Exception as e:
        print(f"[corr] K270 load error: {e}")
        k270_dr = None
        correlations["K270_available"] = False

    # Load K275 equity curve
    try:
        with open("/Users/nekonaomichi/crypto-lab/wave_k275_curves.json") as f:
            k275_curves = json.load(f)
        k275_eq = pd.Series(k275_curves.get("equity_curve", {}))
        k275_eq.index = pd.to_datetime(k275_eq.index)
        k275_dr = k275_eq.pct_change().dropna()
        k275_dr.index = k275_dr.index.astype(str)
        correlations["K275_available"] = True
    except Exception as e:
        print(f"[corr] K275 load error: {e}")
        k275_dr = None
        correlations["K275_available"] = False

    if not k297_daily_rets_dict:
        return correlations

    k297_dr = pd.Series(k297_daily_rets_dict)
    k297_dr.index = pd.to_datetime(k297_dr.index).astype(str)

    for name, ref_dr in [("K270", k270_dr), ("K275", k275_dr)]:
        if ref_dr is None:
            correlations[f"rho_{name}"] = None
            continue
        common = k297_dr.index.intersection(ref_dr.index)
        if len(common) < 5:
            correlations[f"rho_{name}"] = None
            correlations[f"rho_{name}_n"] = len(common)
        else:
            rho = float(k297_dr[common].corr(ref_dr[common]))
            correlations[f"rho_{name}"] = rho
            correlations[f"rho_{name}_abs"] = abs(rho)
            correlations[f"rho_{name}_n"] = len(common)

    return correlations


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
def main():
    t0 = time.time()
    print("=" * 60)
    print("Wave K297 — HL HIP-3 RWA Perp Weekend FR Carry")
    print("=" * 60)

    result = {
        "wave": "K297",
        "strategy": "HL_HIP3_RWA_Weekend_FR_Carry",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "config": {
            "entry": "Friday 16:00 UTC",
            "exit": "Monday 14:30 UTC",
            "hold_hours_approx": 64,
            "maker_cost_per_side_pct": MAKER_COST_PCT * 100,
            "round_trip_cost_pct": 2 * MAKER_COST_PCT * 100,
        },
    }

    # ── Step 1: Market Discovery ──────────────────────────────
    print("\n[1] Fetching HL market meta...")
    meta = fetch_hl_meta()

    if meta:
        rwa_markets, all_symbols = identify_rwa_perps(meta)
        result["hl_market_count"] = len(all_symbols)
        result["all_hl_symbols_sample"] = sorted(all_symbols)[:50]
        result["rwa_markets_found"] = {k: {"name": v["name"]} for k, v in rwa_markets.items()}
        print(f"  Total HL markets: {len(all_symbols)}")
        print(f"  RWA/TradFi markets found: {list(rwa_markets.keys())}")
    else:
        result["hl_market_count"] = 0
        result["rwa_markets_found"] = {}
        all_symbols = []
        rwa_markets = {}
        print("  [WARN] Could not fetch meta — proceeding with candidate list only")

    # Determine which RWA symbols to attempt fetching
    target_symbols = list(rwa_markets.keys()) if rwa_markets else []
    # Always try these specific candidates even if not in meta
    for cand in ["XAG", "XAU", "USOIL", "NQ", "SPX", "TSLA", "AAPL", "COIN", "MSTR"]:
        if cand not in target_symbols:
            target_symbols.append(cand)

    # ── Step 2: Fetch FR History ──────────────────────────────
    print(f"\n[2] Fetching FR history for {len(target_symbols)} RWA candidates...")
    print(f"    Candidates: {target_symbols}")

    # Date range: 2 years back
    end_dt = datetime.now(timezone.utc)
    start_dt = end_dt - timedelta(days=730)
    start_ms = int(start_dt.timestamp() * 1000)
    end_ms = int(end_dt.timestamp() * 1000)

    coin_dfs = {}
    fr_stats_all = {}

    for coin in target_symbols:
        print(f"  Fetching {coin}...")
        records = fetch_fr_history(coin, start_ms, end_ms)
        if records:
            df = records_to_df(records, coin)
            if not df.empty:
                coin_dfs[coin] = df
                stats = compute_fr_stats(df)
                fr_stats_all[coin] = stats
                print(f"    {coin}: {len(df)} hours | weekend APR={stats.get('weekend_apr', 'N/A'):.2f}% "
                      f"| weekday APR={stats.get('weekday_apr', 'N/A'):.2f}% "
                      f"| ratio={stats.get('weekend_vs_weekday_ratio', 'N/A')}")
            else:
                print(f"    {coin}: no data records")
        else:
            print(f"    {coin}: no data (not listed or no history)")

    result["fr_stats"] = fr_stats_all
    result["coins_with_data"] = list(coin_dfs.keys())

    # ── Step 3: Combined FR Stats Table ─────────────────────
    print(f"\n[3] FR Stats Summary — {len(coin_dfs)} coins with data:")
    if fr_stats_all:
        print(f"  {'Coin':<8} {'Weekend APR':>12} {'Weekday APR':>12} {'Ratio':>8} {'N hours':>8}")
        print("  " + "-" * 52)
        for coin, stats in sorted(fr_stats_all.items(),
                                   key=lambda x: x[1].get('weekend_apr') or 0, reverse=True):
            wa = stats.get('weekend_apr')
            wda = stats.get('weekday_apr')
            rat = stats.get('weekend_vs_weekday_ratio')
            n = stats.get('n_weekend_hours', 0)
            print(f"  {coin:<8} {wa if wa else 'N/A':>12.2f} {wda if wda else 'N/A':>12.2f} "
                  f"{rat if rat else 'N/A':>8.2f}x {n:>8}")

    # R10 claim verification
    xag_stats = fr_stats_all.get("XAG", {})
    result["r10_verification"] = {
        "claim_source": "R10-003 BitMEX Q1 2026 Report (Binance XAG data)",
        "claimed_weekend_apr": 56.69,
        "claimed_weekday_apr": 18.18,
        "claimed_ratio": 3.12,
        "note": "R10 data was from Binance, not HL; HL HIP-3 XAG may differ",
        "hl_xag_weekend_apr": xag_stats.get("weekend_apr"),
        "hl_xag_weekday_apr": xag_stats.get("weekday_apr"),
        "hl_xag_ratio": xag_stats.get("weekend_vs_weekday_ratio"),
        "hl_xag_n_hours": xag_stats.get("n_total_hours", 0),
    }

    # ── Step 4: Backtest ──────────────────────────────────────
    print(f"\n[4] Running weekend carry backtest...")
    backtest_results = {}
    all_daily_rets = {}

    for coin, df in coin_dfs.items():
        print(f"  Backtesting {coin}...")
        bt = backtest_weekend_carry(df, coin)
        if bt is None:
            print(f"    {coin}: insufficient trades")
            continue

        backtest_results[coin] = {
            "n_trades": bt["n_trades"],
            "win_rate": bt["win_rate"],
            "ann_return": bt["ann_return"],
            "ann_vol": bt["ann_vol"],
            "sharpe": bt["sharpe"],
            "max_dd": bt["max_dd"],
            "mean_net_fr_per_trade": bt["mean_net_fr_per_trade"],
            "gross_mean_fr_per_trade": bt["gross_mean_fr"],
            "maker_cost_rt": bt["maker_cost_rt"],
        }

        # WF
        wf = walk_forward(bt["trades_df"])
        if wf:
            backtest_results[coin]["walk_forward"] = wf

        # Collect daily rets
        for dt, r in bt["daily_rets_dict"].items():
            all_daily_rets[dt] = all_daily_rets.get(dt, 0) + r / max(len(coin_dfs), 1)

        print(f"    {coin}: n={bt['n_trades']}, Sh={bt['sharpe']:.2f}, "
              f"AnnRet={bt['ann_return']*100:.1f}%, WinRate={bt['win_rate']*100:.0f}%")

    result["backtest"] = backtest_results

    # Portfolio-level: equal-weight across available RWA perps
    if backtest_results:
        n_coins = len(backtest_results)
        portfolio_sharpes = [v["sharpe"] for v in backtest_results.values()]
        portfolio_ann_rets = [v["ann_return"] for v in backtest_results.values()]
        portfolio_max_dds = [v["max_dd"] for v in backtest_results.values()]

        result["portfolio_equal_weight"] = {
            "n_coins": n_coins,
            "mean_sharpe": float(np.mean(portfolio_sharpes)),
            "mean_ann_return": float(np.mean(portfolio_ann_rets)),
            "worst_max_dd": float(min(portfolio_max_dds)),
            "coins": list(backtest_results.keys()),
        }
        print(f"\n  Portfolio ({n_coins} coins): "
              f"Mean Sh={np.mean(portfolio_sharpes):.2f}, "
              f"Mean AnnRet={np.mean(portfolio_ann_rets)*100:.1f}%")

    # ── Step 5: Correlation vs K287d ────────────────────────
    print(f"\n[5] Computing correlations vs K287d components...")
    corr = compute_correlations(all_daily_rets)
    result["correlations_vs_k287d"] = corr
    for k, v in corr.items():
        if "rho" in k and isinstance(v, float):
            print(f"  {k}: {v:.3f}")

    # ── Step 6: Cache to Parquet ─────────────────────────────
    print(f"\n[6] Caching FR data to parquet...")
    if coin_dfs:
        all_dfs = []
        for coin, df in coin_dfs.items():
            df_copy = df.copy()
            df_copy["coin"] = coin
            df_copy = classify_weekend(df_copy)
            all_dfs.append(df_copy)

        combined = pd.concat(all_dfs)
        combined.to_parquet(CACHE_PARQUET)
        print(f"  Cached {len(combined)} records to {CACHE_PARQUET}")
        result["cache_parquet"] = str(CACHE_PARQUET)
        result["cache_rows"] = len(combined)
    else:
        result["cache_parquet"] = None
        result["cache_rows"] = 0
        print("  No data to cache.")

    # ── Step 7: Verdict ──────────────────────────────────────
    best_coin = None
    best_sh = 0.0
    if backtest_results:
        for coin, bt in backtest_results.items():
            if bt["sharpe"] > best_sh:
                best_sh = bt["sharpe"]
                best_coin = coin

    has_data = len(coin_dfs) > 0
    passes_sharpe = best_sh >= 1.5 if best_coin else False
    wf_ok = False
    if best_coin and "walk_forward" in backtest_results.get(best_coin, {}):
        wf_ok = backtest_results[best_coin]["walk_forward"].get("all_positive", False)

    corr_ok = True
    for key in ["rho_K270_abs", "rho_K275_abs"]:
        v = corr.get(key)
        if v is not None and v >= 0.5:
            corr_ok = False

    verdict = "FRAMEWORK_ONLY"
    k298_recommendation = "HOLD"

    if has_data and passes_sharpe and corr_ok:
        verdict = "ACCEPTED"
        k298_recommendation = "ADD_AS_SATELLITE"
    elif has_data and passes_sharpe and not corr_ok:
        verdict = "CONDITIONAL_ACCEPT"
        k298_recommendation = "ADD_SMALL_ALLOCATION"
    elif has_data and not passes_sharpe:
        verdict = "INSUFFICIENT_EDGE"
        k298_recommendation = "REJECT"
    elif not has_data:
        verdict = "FRAMEWORK_ONLY"
        k298_recommendation = "MONITOR_HL_LISTINGS"

    result["verdict"] = {
        "status": verdict,
        "k298_recommendation": k298_recommendation,
        "best_coin": best_coin,
        "best_sharpe": best_sh,
        "passes_sharpe_threshold_15": passes_sharpe,
        "wf_all_positive": wf_ok,
        "corr_ok_below_05": corr_ok,
        "rwa_data_available": has_data,
        "acceptance_criteria": {
            "Sharpe > 1.5": passes_sharpe,
            "WF folds positive": wf_ok,
            "|rho| < 0.5 vs K287d": corr_ok,
        },
    }

    result["runtime_s"] = round(time.time() - t0, 1)

    # ── Write Outputs ────────────────────────────────────────
    # Remove non-serializable objects before writing
    def serialize_result(d):
        out = {}
        for k, v in d.items():
            if isinstance(v, dict):
                out[k] = serialize_result(v)
            elif isinstance(v, (pd.DataFrame, pd.Series)):
                pass  # skip
            elif isinstance(v, np.integer):
                out[k] = int(v)
            elif isinstance(v, np.floating):
                out[k] = float(v)
            elif isinstance(v, np.ndarray):
                out[k] = v.tolist()
            else:
                out[k] = v
        return out

    result_clean = serialize_result(result)

    with open(RESULT_JSON, "w") as f:
        json.dump(result_clean, f, indent=2, default=str)
    print(f"\n[OUTPUT] Written: {RESULT_JSON}")

    # Curves JSON
    curves = {"wave": "K297", "coins": {}}
    for coin, bt in (backtest_results.items() if backtest_results else []):
        if "equity_curve" not in bt:
            continue
        curves["coins"][coin] = {
            "equity_curve": {str(k): float(v) for k, v in bt.get("equity_curve", {}).items()}
        }

    # Also aggregate portfolio curve
    if all_daily_rets:
        port_dr = pd.Series(all_daily_rets).sort_index()
        port_eq = (1 + port_dr).cumprod()
        curves["portfolio_equity_curve"] = {str(k): float(v) for k, v in port_eq.items()}

    with open(CURVES_JSON, "w") as f:
        json.dump(curves, f, indent=2, default=str)
    print(f"[OUTPUT] Written: {CURVES_JSON}")

    # Print final summary
    print("\n" + "=" * 60)
    print(f"VERDICT: {verdict}")
    print(f"K298 Recommendation: {k298_recommendation}")
    print(f"Best coin: {best_coin} (Sh={best_sh:.2f})")
    print(f"Runtime: {result['runtime_s']}s")
    print("=" * 60)

    return result_clean


if __name__ == "__main__":
    main()
