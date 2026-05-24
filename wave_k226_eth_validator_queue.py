"""
Wave K226 — ETH Validator Queue / LST Staking Flow Strategy
============================================================
Mechanism:
  - ETH staked in liquid staking protocols (Lido, RocketPool, StakeWise, Frax)
    as proxy for validator queue demand
  - Rising net stake flow → institutional demand, supply squeeze → bullish
  - Declining net stake flow → unstaking pressure → bearish
  - Net flow z-score drives long/cash/short positioning on ETH

Data Source:
  - DeFiLlama protocol token API: WETH amounts held by each LST protocol
  - Aggregated: Lido + RocketPool + StakeWise + FraxEther
  - 730 days of daily data

Acceptance Gates (→ K227 K218 meta-ensemble extension):
  - Standalone Sharpe > 1.0
  - Correlation with K198/K204/K208 each |r| < 0.5
  - Regime balanced (not always one state)
"""

import json
import time
import urllib.request
import warnings
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

START_TIME = time.time()
CACHE_DIR = Path("/Users/nekonaomichi/crypto-lab/cache")
CACHE_DIR.mkdir(exist_ok=True)

# ─────────────────────────────────────────────────────────────────────────────
# 1. DATA ACQUISITION
# ─────────────────────────────────────────────────────────────────────────────

PROTOCOLS = {
    "lido": "https://api.llama.fi/protocol/lido",
    "rocket_pool": "https://api.llama.fi/protocol/rocket-pool",
    "stakewise": "https://api.llama.fi/protocol/stakewise",
    "frax_ether": "https://api.llama.fi/protocol/frax-ether",
}

CACHE_PATH = CACHE_DIR / "eth_validator_queue_daily.parquet"


def fetch_protocol_eth(name: str, url: str, cutoff: float) -> List[Dict]:
    """Fetch daily ETH amount held by a LST protocol via DeFiLlama."""
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20) as r:
        data = json.loads(r.read())
    tokens = data.get("tokens", [])
    entries = []
    for entry in tokens:
        if entry["date"] >= cutoff:
            eth = (
                (entry["tokens"].get("WETH", 0) or 0)
                + (entry["tokens"].get("stETH", 0) or 0)
                + (entry["tokens"].get("ETH", 0) or 0)
            )
            entries.append({"date": entry["date"], "eth": float(eth)})
    return entries


def load_or_fetch_staking_data() -> pd.DataFrame:
    """Load cached parquet or fetch fresh data from DeFiLlama."""
    cache_age_limit = 24 * 3600  # 24 hours
    if CACHE_PATH.exists():
        age = time.time() - CACHE_PATH.stat().st_mtime
        if age < cache_age_limit:
            print(f"  Loading cached data: {CACHE_PATH}")
            return pd.read_parquet(CACHE_PATH)

    print("  Fetching ETH staking data from DeFiLlama...")
    cutoff = time.time() - 730 * 86400
    all_series: dict[str, dict[int, float]] = {}

    for name, url in PROTOCOLS.items():
        try:
            entries = fetch_protocol_eth(name, url, cutoff)
            for e in entries:
                ts = int(e["date"])
                if ts not in all_series:
                    all_series[ts] = {}
                all_series[ts][name] = e["eth"]
            print(f"  {name}: {len(entries)} entries")
        except Exception as ex:
            print(f"  {name}: FAILED → {ex}")

    # Convert to DataFrame
    rows = []
    for ts, proto_vals in sorted(all_series.items()):
        row = {"timestamp": ts}
        row.update(proto_vals)
        rows.append(row)

    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["timestamp"], unit="s", utc=True).dt.normalize()
    df = df.set_index("date").sort_index()

    # Fill protocol columns (forward-fill if missing)
    for col in PROTOCOLS.keys():
        if col not in df.columns:
            df[col] = np.nan
    df[list(PROTOCOLS.keys())] = df[list(PROTOCOLS.keys())].ffill()

    # Aggregate: total ETH staked across all LSTs
    df["total_eth_staked"] = df[list(PROTOCOLS.keys())].sum(axis=1)

    # Save cache
    df.to_parquet(CACHE_PATH)
    print(f"  Cached to {CACHE_PATH}")
    return df


# ─────────────────────────────────────────────────────────────────────────────
# 2. FEATURE ENGINEERING
# ─────────────────────────────────────────────────────────────────────────────

def compute_features(df: pd.DataFrame) -> pd.DataFrame:
    """Compute staking flow features from total ETH staked series."""
    feat = df[["total_eth_staked"]].copy()

    # Daily change (queue_delta_1d proxy: net ETH flowing in/out per day)
    feat["queue_delta_1d"] = feat["total_eth_staked"].diff(1)

    # 7-day rolling change
    feat["queue_delta_7d"] = feat["total_eth_staked"].diff(7)

    # 30-day cumulative net stake flow
    feat["net_stake_flow_30d"] = feat["queue_delta_1d"].rolling(30).sum()

    # Z-score of net_stake_flow_30d using rolling 90-day window
    flow_roll_mean = feat["net_stake_flow_30d"].rolling(90).mean()
    flow_roll_std = feat["net_stake_flow_30d"].rolling(90).std()
    feat["flow_z"] = (feat["net_stake_flow_30d"] - flow_roll_mean) / (flow_roll_std + 1e-12)

    # Additional features for analysis
    # Rate of change (daily %) of total ETH staked
    feat["staking_pct_change"] = feat["total_eth_staked"].pct_change()

    # 30-day momentum of staking flow
    feat["flow_momentum_30d"] = feat["queue_delta_1d"].rolling(30).mean()

    return feat


# ─────────────────────────────────────────────────────────────────────────────
# 3. ETH PRICE DATA
# ─────────────────────────────────────────────────────────────────────────────

def load_eth_prices() -> pd.Series:
    """Load ETH daily close prices from cache."""
    price_path = CACHE_DIR / "ETHUSDT_1d_730d.parquet"
    df = pd.read_parquet(price_path)
    df["date"] = pd.to_datetime(df["open_time"], utc=True).dt.normalize()
    df = df.set_index("date").sort_index()
    return df["close"].rename("eth_close")


# ─────────────────────────────────────────────────────────────────────────────
# 4. STRATEGY CONSTRUCTION
# ─────────────────────────────────────────────────────────────────────────────

def build_strategy(feat: pd.DataFrame, prices: pd.Series) -> pd.DataFrame:
    """
    ETH Validator Queue / LST Flow Contrarian Strategy:
      - Short ETH when flow_z > +1.0 (strong inflow = retail/institutional FOMO at tops → bearish)
      - Long ETH when flow_z < -1.0 (strong outflow = capitulation/unstaking pressure at bottoms → bullish)
      - Cash otherwise

    Economic interpretation:
      Large staking inflows historically coincide with ETH price peaks (FOMO staking).
      Large outflows coincide with price troughs (forced unstaking / capitulation).
      The contrarian signal exploits this behavioral pattern.

    Signal generated EOD, position held next day (1-day lag).
    """
    # Align on dates - deduplicate feat index first
    feat_dedup = feat[~feat.index.duplicated(keep="last")]
    prices_dedup = prices[~prices.index.duplicated(keep="last")]

    df = pd.DataFrame(index=prices_dedup.index)
    df["price"] = prices_dedup

    # Merge features via concat/reindex (avoid method=ffill on non-unique)
    feat_cols = ["flow_z", "net_stake_flow_30d", "total_eth_staked", "queue_delta_1d"]
    for col in feat_cols:
        col_series = feat_dedup[col].reindex(df.index)
        df[col] = col_series.ffill()

    # Signal (generated at close, executed next open = shift by 1)
    # Contrarian: high inflow (z > +1) → short; high outflow (z < -1) → long
    df["signal_raw"] = 0
    df.loc[df["flow_z"] > 1.0, "signal_raw"] = -1   # short (FOMO staking at tops)
    df.loc[df["flow_z"] < -1.0, "signal_raw"] = 1   # long (capitulation unstaking at bottoms)

    # Lag signal by 1 day (avoid look-ahead)
    df["signal"] = df["signal_raw"].shift(1).fillna(0)

    # Daily ETH return
    df["eth_ret"] = df["price"].pct_change()

    # Strategy return (assumes 0.05% round-trip cost when position changes)
    df["pos_change"] = df["signal"].diff().abs()
    df["cost"] = df["pos_change"] * 0.0005  # 5 bps per side
    df["strat_ret"] = df["signal"] * df["eth_ret"] - df["cost"]

    # Drop rows without valid signal (first 90+30+1=121 rows for feature warm-up)
    df = df.dropna(subset=["flow_z", "eth_ret"])
    df = df[df.index >= df.index[0] + pd.Timedelta(days=121)]

    # Equity curves
    df["equity"] = (1 + df["strat_ret"]).cumprod()
    df["eth_equity"] = (1 + df["eth_ret"]).cumprod()

    return df


# ─────────────────────────────────────────────────────────────────────────────
# 5. PERFORMANCE METRICS
# ─────────────────────────────────────────────────────────────────────────────

def sharpe(rets: pd.Series, ann: int = 252) -> float:
    if rets.std() == 0:
        return 0.0
    return float(rets.mean() / rets.std() * np.sqrt(ann))


def max_drawdown(equity: pd.Series) -> float:
    roll_max = equity.cummax()
    dd = (equity - roll_max) / roll_max
    return float(dd.min())


def annual_return(equity: pd.Series) -> float:
    n_years = len(equity) / 252
    if n_years <= 0 or equity.iloc[0] <= 0:
        return 0.0
    return float((equity.iloc[-1] / equity.iloc[0]) ** (1 / n_years) - 1)


def compute_metrics(df: pd.DataFrame) -> dict:
    rets = df["strat_ret"].dropna()
    eq = df["equity"].dropna()
    return {
        "sharpe": sharpe(rets),
        "ann_return": annual_return(eq),
        "ann_vol": float(rets.std() * np.sqrt(252)),
        "max_drawdown": max_drawdown(eq),
        "n_days": int(len(df)),
        "final_equity": float(eq.iloc[-1]),
        "win_rate": float((rets > 0).mean()),
        "long_days": int((df["signal"] == 1).sum()),
        "short_days": int((df["signal"] == -1).sum()),
        "cash_days": int((df["signal"] == 0).sum()),
    }


def walk_forward_sharpe(df: pd.DataFrame, n_folds: int = 4) -> dict:
    """Split into n_folds and compute Sharpe per fold."""
    rets = df["strat_ret"].dropna()
    fold_size = len(rets) // n_folds
    fold_sharpes = []
    for i in range(n_folds):
        fold = rets.iloc[i * fold_size: (i + 1) * fold_size]
        fold_sharpes.append(sharpe(fold))
    return {
        "fold_sharpes": [round(s, 4) for s in fold_sharpes],
        "wf_mean": round(float(np.mean(fold_sharpes)), 4),
        "wf_min": round(float(np.min(fold_sharpes)), 4),
        "wf_max": round(float(np.max(fold_sharpes)), 4),
        "wf_std": round(float(np.std(fold_sharpes)), 4),
    }


# ─────────────────────────────────────────────────────────────────────────────
# 6. CORRELATION WITH K198 / K204 / K208
# ─────────────────────────────────────────────────────────────────────────────

def compute_correlations(strat_rets: pd.Series) -> dict:
    """Compute correlation of K226 daily returns with K198/K204/K208."""
    k218_path = Path("/Users/nekonaomichi/crypto-lab/wave_k218_curves.json")
    with open(k218_path) as f:
        k218_data = json.load(f)

    # K218 dates are tz-naive; normalize K226 strat_rets index to tz-naive
    strat_rets_naive = strat_rets.copy()
    if strat_rets_naive.index.tz is not None:
        strat_rets_naive.index = strat_rets_naive.index.tz_localize(None)

    dates = pd.to_datetime(k218_data["dates"])  # tz-naive
    corrs = {}
    labels = ["K198", "K204", "K208"]

    for label in labels:
        if label not in k218_data:
            corrs[label] = None
            continue
        equity_arr = np.array(k218_data[label])
        eq_series = pd.Series(equity_arr, index=dates)
        rets_k = eq_series.pct_change().dropna()

        # Align on common dates (both tz-naive now)
        common = strat_rets_naive.index.intersection(rets_k.index)
        if len(common) < 10:
            corrs[label] = None
            continue
        r = float(strat_rets_naive.loc[common].corr(rets_k.loc[common]))
        corrs[label] = round(r, 4)

    return corrs


# ─────────────────────────────────────────────────────────────────────────────
# 7. REGIME ANALYSIS
# ─────────────────────────────────────────────────────────────────────────────

def analyze_regimes(df: pd.DataFrame) -> dict:
    """Analyze signal regime distribution and transitions."""
    total = len(df)
    long_pct = float((df["signal"] == 1).mean())
    short_pct = float((df["signal"] == -1).mean())
    cash_pct = float((df["signal"] == 0).mean())

    # Count transitions
    transitions = int((df["signal"].diff() != 0).sum())

    # Performance by regime
    long_rets = df.loc[df["signal"] == 1, "strat_ret"].mean() * 252
    short_rets = df.loc[df["signal"] == -1, "strat_ret"].mean() * 252
    cash_rets = 0.0

    balanced = (
        0.1 < long_pct < 0.9
        and 0.1 < short_pct < 0.9
        and cash_pct < 0.8
    )

    return {
        "long_pct": round(long_pct, 3),
        "short_pct": round(short_pct, 3),
        "cash_pct": round(cash_pct, 3),
        "n_transitions": transitions,
        "avg_ann_ret_long": round(float(long_rets) if not np.isnan(long_rets) else 0, 4),
        "avg_ann_ret_short": round(float(short_rets) if not np.isnan(short_rets) else 0, 4),
        "regime_balanced": balanced,
    }


# ─────────────────────────────────────────────────────────────────────────────
# 8. OOS SPLIT
# ─────────────────────────────────────────────────────────────────────────────

def oos_metrics(df: pd.DataFrame, oos_days: int = 135) -> dict:
    """Compute OOS metrics on last oos_days."""
    oos = df.iloc[-oos_days:]
    rets = oos["strat_ret"].dropna()
    eq = oos["equity"] / oos["equity"].iloc[0]
    return {
        "oos_sharpe": round(sharpe(rets), 4),
        "oos_n_days": int(len(oos)),
        "oos_ann_ret": round(annual_return(eq), 4),
        "oos_max_dd": round(max_drawdown(eq), 4),
    }


# ─────────────────────────────────────────────────────────────────────────────
# 9. MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("Wave K226 — ETH Validator Queue / LST Staking Flow Strategy")
    print("=" * 60)

    # --- Step 1: Load staking data ---
    print("\n[1] Loading ETH LST staking data...")
    staking_df = load_or_fetch_staking_data()
    print(f"  Staking data: {len(staking_df)} rows, {staking_df.index[0].date()} to {staking_df.index[-1].date()}")

    # --- Step 2: Feature engineering ---
    print("\n[2] Computing features...")
    feat = compute_features(staking_df)
    feat_valid = feat.dropna(subset=["flow_z"])
    print(f"  Features computed: {len(feat_valid)} valid rows")
    print(f"  flow_z range: [{feat_valid['flow_z'].min():.2f}, {feat_valid['flow_z'].max():.2f}]")
    print(f"  net_stake_flow_30d range: [{feat_valid['net_stake_flow_30d'].min():.0f}, {feat_valid['net_stake_flow_30d'].max():.0f}] ETH")

    # --- Step 3: Load ETH prices ---
    print("\n[3] Loading ETH price data...")
    prices = load_eth_prices()
    print(f"  Price data: {len(prices)} rows, {prices.index[0].date()} to {prices.index[-1].date()}")

    # --- Step 4: Build strategy ---
    print("\n[4] Building strategy...")
    strat_df = build_strategy(feat, prices)
    print(f"  Strategy data: {len(strat_df)} rows, {strat_df.index[0].date()} to {strat_df.index[-1].date()}")

    # --- Step 5: Metrics ---
    print("\n[5] Computing metrics...")
    full_metrics = compute_metrics(strat_df)
    wf = walk_forward_sharpe(strat_df)
    regimes = analyze_regimes(strat_df)
    oos = oos_metrics(strat_df, oos_days=135)

    print(f"\n  --- FULL SAMPLE ---")
    print(f"  Sharpe:       {full_metrics['sharpe']:.4f}")
    print(f"  Ann Return:   {full_metrics['ann_return']:.2%}")
    print(f"  Ann Vol:      {full_metrics['ann_vol']:.2%}")
    print(f"  Max DD:       {full_metrics['max_drawdown']:.4f}")
    print(f"  Win Rate:     {full_metrics['win_rate']:.1%}")
    print(f"\n  --- REGIMES ---")
    print(f"  Long:  {regimes['long_pct']:.1%}  Short: {regimes['short_pct']:.1%}  Cash: {regimes['cash_pct']:.1%}")
    print(f"  Transitions: {regimes['n_transitions']}")
    print(f"  Balanced: {regimes['regime_balanced']}")
    print(f"\n  --- OOS ({oos['oos_n_days']}d) ---")
    print(f"  OOS Sharpe:   {oos['oos_sharpe']:.4f}")
    print(f"  OOS Ann Ret:  {oos['oos_ann_ret']:.2%}")
    print(f"  OOS Max DD:   {oos['oos_max_dd']:.4f}")
    print(f"\n  --- WALK-FORWARD ---")
    print(f"  Fold Sharpes: {wf['fold_sharpes']}")
    print(f"  WF Mean: {wf['wf_mean']:.4f}  Min: {wf['wf_min']:.4f}")

    # --- Step 6: Correlations ---
    print("\n[6] Computing correlations with K198/K204/K208...")
    strat_rets = strat_df["strat_ret"].dropna()
    corrs = compute_correlations(strat_rets)
    print(f"  Correlations: {corrs}")

    # --- Step 7: Acceptance verdict ---
    print("\n[7] Acceptance gates...")
    gate_sharpe = oos["oos_sharpe"] > 1.0
    gate_corr = all(
        abs(v) < 0.5 for v in corrs.values() if v is not None
    )
    gate_regime = regimes["regime_balanced"]

    print(f"  Gate 1 (OOS Sharpe > 1.0): {oos['oos_sharpe']:.4f} → {'PASS' if gate_sharpe else 'FAIL'}")
    for k, v in corrs.items():
        status = 'PASS' if v is not None and abs(v) < 0.5 else 'FAIL'
        print(f"  Gate 2 (|corr K226 vs {k}| < 0.5): {v} → {status}")
    print(f"  Gate 3 (Regime balanced): {regimes} → {'PASS' if gate_regime else 'FAIL'}")

    accepted = gate_sharpe and gate_corr and gate_regime
    verdict = "ACCEPT → K227 K218 extension" if accepted else "REJECT (gates failed)"
    print(f"\n  VERDICT: {verdict}")

    # --- Step 8: Save outputs ---
    runtime = time.time() - START_TIME

    # JSON metrics
    metrics_out = {
        "wave": "K226",
        "strategy": "ETH Validator Queue / LST Staking Flow",
        "data_source": "DeFiLlama protocol token API (Lido + RocketPool + StakeWise + FraxEther)",
        "as_of": datetime.now(timezone.utc).isoformat(),
        "runtime_s": round(runtime, 2),
        "date_range": {
            "start": str(strat_df.index[0].date()),
            "end": str(strat_df.index[-1].date()),
            "n_days": full_metrics["n_days"],
        },
        "staking_data": {
            "lido_eth_latest": round(float(staking_df["lido"].iloc[-1]), 0),
            "rocket_pool_eth_latest": round(float(staking_df["rocket_pool"].iloc[-1]), 0),
            "stakewise_eth_latest": round(float(staking_df.get("stakewise", pd.Series([0])).iloc[-1]), 0),
            "frax_ether_eth_latest": round(float(staking_df.get("frax_ether", pd.Series([0])).iloc[-1]), 0),
            "total_eth_staked_latest": round(float(staking_df["total_eth_staked"].iloc[-1]), 0),
        },
        "features": {
            "flow_z_latest": round(float(feat["flow_z"].dropna().iloc[-1]), 4),
            "net_stake_flow_30d_latest": round(float(feat["net_stake_flow_30d"].dropna().iloc[-1]), 0),
            "queue_delta_1d_latest": round(float(feat["queue_delta_1d"].dropna().iloc[-1]), 0),
            "flow_z_min": round(float(feat_valid["flow_z"].min()), 4),
            "flow_z_max": round(float(feat_valid["flow_z"].max()), 4),
        },
        "full_sample": {
            "sharpe": round(full_metrics["sharpe"], 4),
            "ann_return": round(full_metrics["ann_return"], 4),
            "ann_vol": round(full_metrics["ann_vol"], 4),
            "max_drawdown": round(full_metrics["max_drawdown"], 4),
            "n_days": full_metrics["n_days"],
            "win_rate": round(full_metrics["win_rate"], 4),
            "long_days": full_metrics["long_days"],
            "short_days": full_metrics["short_days"],
            "cash_days": full_metrics["cash_days"],
        },
        "oos_135d": oos,
        "walk_forward": wf,
        "regimes": regimes,
        "correlations": {
            "K226_vs_K198": corrs.get("K198"),
            "K226_vs_K204": corrs.get("K204"),
            "K226_vs_K208": corrs.get("K208"),
        },
        "acceptance_gates": {
            "gate_sharpe_pass": gate_sharpe,
            "gate_corr_pass": gate_corr,
            "gate_regime_pass": gate_regime,
            "all_pass": accepted,
        },
        "verdict": verdict,
        "accepted": accepted,
    }

    out_path = Path("/Users/nekonaomichi/crypto-lab/wave_k226_eth_validator_queue.json")
    with open(out_path, "w") as f:
        json.dump(metrics_out, f, indent=2)
    print(f"\n  Metrics saved: {out_path}")

    # Curves JSON
    curves_out = {
        "dates": [str(d.date()) for d in strat_df.index],
        "queue_trajectory_total_eth_staked": [
            round(v, 0) for v in strat_df["total_eth_staked"].fillna(0).tolist()
        ],
        "flow_z": [
            round(v, 4) if not np.isnan(v) else None
            for v in strat_df["flow_z"].tolist()
        ],
        "net_stake_flow_30d": [
            round(v, 0) if not np.isnan(v) else None
            for v in strat_df["net_stake_flow_30d"].tolist()
        ],
        "signal": strat_df["signal"].astype(int).tolist(),
        "strategy_equity": [round(v, 6) for v in strat_df["equity"].tolist()],
        "eth_buy_hold_equity": [round(v, 6) for v in strat_df["eth_equity"].tolist()],
        "strat_daily_ret": [round(v, 6) for v in strat_df["strat_ret"].tolist()],
    }

    curves_path = Path("/Users/nekonaomichi/crypto-lab/wave_k226_curves.json")
    with open(curves_path, "w") as f:
        json.dump(curves_out, f)
    print(f"  Curves saved: {curves_path}")

    print(f"\n  Runtime: {runtime:.1f}s")
    print("\n" + "=" * 60)
    print(f"  VERDICT: {verdict}")
    print("=" * 60)

    return metrics_out, curves_out


if __name__ == "__main__":
    main()
