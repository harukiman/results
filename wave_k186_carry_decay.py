"""Wave K186 - Carry Decay Empirical Test.

Temporal decay analysis of the K182 pure carry (LONG Bybit + SHORT HL) strategy.
Splits 2-year data into 3 buckets, computes per-bucket metrics, rolling 90d Sharpe,
and linear trend test to determine if carry edge is STABLE, DECAYING, or COLLAPSED.

Spread definition (from K182): premium_bps = (HL_FR_8h - Bybit_FR) * 10_000
Positive premium = HL pays more than Bybit => long Bybit / short HL earns carry.
"""
from __future__ import annotations

import json
import time
import warnings
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from scipy import stats

warnings.filterwarnings("ignore")

START = time.time()
CACHE = Path("/Users/nekonaomichi/crypto-lab/cache")
HL_CACHE = CACHE / "k163_hl"
OUT_DIR = Path("/Users/nekonaomichi/crypto-lab")

SYMBOLS = ["BTC", "ETH", "DOGE", "AVAX"]
ANNUAL_EVENTS = 3 * 365  # 3 funding events/day

# Temporal buckets
BUCKET_A_END = "2024-12-31"   # 2024 (all)
BUCKET_B_END = "2025-06-30"   # 2025 H1
# Bucket C: 2025-07-01 onwards

# Rolling window and threshold
ROLLING_DAYS = 90
ROLLING_EVENTS = ROLLING_DAYS * 3  # 270 events

# Decision threshold: most-recent 90d Sharpe vs full-period Sharpe
STABILITY_THRESHOLD = 0.50


# ---------------------------------------------------------------------------
# Data loading (mirrored from K182)
# ---------------------------------------------------------------------------

def load_hl_8h(sym: str) -> pd.DataFrame:
    """Load HL hourly FR, resample to 8h sums to match Bybit event cadence."""
    fpath = HL_CACHE / f"hl_fr_{sym}.parquet"
    df = pd.read_parquet(fpath)
    df["ts"] = pd.to_datetime(df["timestamp"])
    hl_8h = df.set_index("ts")["hl_fr"].resample("8h").sum().reset_index()
    hl_8h.columns = ["ts", "hl_fr_8h"]
    return hl_8h


def load_bybit(sym: str) -> pd.DataFrame:
    """Load Bybit 8h FR for symbol (prefer 730d, fallback to others)."""
    for suffix in ["730d", "1200d", "365d"]:
        fpath = CACHE / f"bybit_fr_{sym}USDT_{suffix}.parquet"
        if fpath.exists():
            df = pd.read_parquet(fpath)
            df["ts"] = pd.to_datetime(df["timestamp"])
            return df[["ts", "funding_rate"]].rename(columns={"funding_rate": "bybit_fr"})
    raise FileNotFoundError(f"No Bybit data for {sym}")


def build_spread(sym: str) -> Optional[pd.DataFrame]:
    """Merge HL 8h and Bybit 8h, compute premium (HL - Bybit) in bps."""
    hl = load_hl_8h(sym)
    bybit = load_bybit(sym)

    merged = pd.merge_asof(
        bybit.sort_values("ts"),
        hl.sort_values("ts"),
        on="ts",
        tolerance=pd.Timedelta("4h"),
        direction="nearest",
    ).dropna()

    # premium_bps = (HL_FR_8h - Bybit_FR) * 10000
    # Positive = HL pays more than Bybit => long Bybit / short HL earns positive carry
    merged["premium_bps"] = (merged["hl_fr_8h"] - merged["bybit_fr"]) * 10_000
    merged = merged.sort_values("ts").reset_index(drop=True)
    return merged


# ---------------------------------------------------------------------------
# Metrics helpers
# ---------------------------------------------------------------------------

def sharpe_from_series(pnl: np.ndarray) -> float:
    """Annualized Sharpe ratio from per-event PnL series."""
    pnl = np.asarray(pnl)
    if len(pnl) < 5 or pnl.std() == 0:
        return np.nan
    return float(pnl.mean() / pnl.std() * np.sqrt(ANNUAL_EVENTS))


def max_drawdown(pnl: np.ndarray) -> float:
    """Max drawdown from per-event PnL (absolute bps)."""
    cumret = np.cumsum(pnl)
    peak = np.maximum.accumulate(cumret)
    dd = cumret - peak
    return float(dd.min())


def bucket_metrics(df_bucket: pd.DataFrame) -> Dict:
    """Compute metrics for a single temporal bucket."""
    pnl = df_bucket["premium_bps"].values
    n = len(pnl)
    if n < 3:
        return {"n_events": n, "mean_spread_bps": np.nan, "sharpe": np.nan, "max_dd_bps": np.nan}
    return {
        "n_events": n,
        "mean_spread_bps": float(np.mean(pnl)),
        "sharpe": sharpe_from_series(pnl),
        "max_dd_bps": max_drawdown(pnl),
    }


# ---------------------------------------------------------------------------
# Rolling Sharpe and trend test
# ---------------------------------------------------------------------------

def compute_rolling_sharpe(df: pd.DataFrame, window: int = ROLLING_EVENTS) -> pd.DataFrame:
    """Compute rolling Sharpe (window events) for full dataset."""
    pnl = df["premium_bps"].values
    ts = df["ts"].values

    sharpes = []
    timestamps = []

    for i in range(window - 1, len(pnl)):
        window_pnl = pnl[i - window + 1: i + 1]
        sh = sharpe_from_series(window_pnl)
        sharpes.append(sh)
        timestamps.append(ts[i])

    return pd.DataFrame({"ts": timestamps, "rolling_sharpe": sharpes})


def trend_test(rolling_df: pd.DataFrame) -> Dict:
    """Linear regression of rolling Sharpe vs time. Returns slope, p-value."""
    valid = rolling_df.dropna(subset=["rolling_sharpe"])
    if len(valid) < 10:
        return {"slope": np.nan, "p_value": np.nan, "r_squared": np.nan}

    x = (pd.to_datetime(valid["ts"]) - pd.to_datetime(valid["ts"].iloc[0])).dt.total_seconds().values
    x = x / (86400 * 30)  # in months
    y = valid["rolling_sharpe"].values

    result = stats.linregress(x, y)
    return {
        "slope_per_month": float(result.slope),
        "intercept": float(result.intercept),
        "p_value": float(result.pvalue),
        "r_squared": float(result.rvalue ** 2),
        "n_points": int(len(y)),
    }


# ---------------------------------------------------------------------------
# Decision matrix
# ---------------------------------------------------------------------------

def decide(full_sharpe: float, recent_sharpe: float, recent_mean_spread: float) -> str:
    """Classify carry edge status for a symbol."""
    if np.isnan(recent_sharpe) or np.isnan(full_sharpe):
        return "INSUFFICIENT_DATA"
    if recent_sharpe < 0:
        return "COLLAPSED"
    if recent_mean_spread <= 0:
        return "COLLAPSED"  # spread flipped sign => no carry
    ratio = recent_sharpe / full_sharpe if full_sharpe > 0 else 0
    if ratio >= STABILITY_THRESHOLD:
        return "STABLE"
    return "DECAYING"


# ---------------------------------------------------------------------------
# Main analysis
# ---------------------------------------------------------------------------

def analyze_symbol(sym: str) -> Optional[Dict]:
    """Full decay analysis for one symbol."""
    print(f"\n[{sym}] Loading data...")
    df = build_spread(sym)
    if df is None or len(df) < 10:
        print(f"  [{sym}] insufficient data, skipping")
        return None

    print(f"  [{sym}] {len(df)} events | {df['ts'].min().date()} -> {df['ts'].max().date()}")

    # --- Bucket assignment ---
    ts = df["ts"]
    mask_a = ts <= BUCKET_A_END
    mask_b = (ts > BUCKET_A_END) & (ts <= BUCKET_B_END)
    mask_c = ts > BUCKET_B_END

    bucket_a = df[mask_a]
    bucket_b = df[mask_b]
    bucket_c = df[mask_c]

    print(f"  Bucket A (2024): {len(bucket_a)} events | "
          f"B (2025-H1): {len(bucket_b)} events | "
          f"C (2025-H2+): {len(bucket_c)} events")

    metrics_a = bucket_metrics(bucket_a)
    metrics_b = bucket_metrics(bucket_b)
    metrics_c = bucket_metrics(bucket_c)

    # Full-period metrics
    metrics_full = bucket_metrics(df)

    # --- Rolling Sharpe ---
    rolling_df = compute_rolling_sharpe(df)

    # Most recent 90d Sharpe (last ROLLING_EVENTS events)
    recent_data = df.tail(ROLLING_EVENTS)
    recent_sharpe = sharpe_from_series(recent_data["premium_bps"].values)
    recent_mean_spread = float(recent_data["premium_bps"].mean())

    # --- Trend test ---
    trend = trend_test(rolling_df)

    # --- Decision ---
    full_sharpe = metrics_full["sharpe"]
    decision = decide(full_sharpe, recent_sharpe, recent_mean_spread)

    print(f"  Full-period Sharpe: {full_sharpe:.2f} | Recent-90d Sharpe: {recent_sharpe:.2f} | Decision: {decision}")

    result = {
        "symbol": sym,
        "data_range": {
            "start": str(df["ts"].min().date()),
            "end": str(df["ts"].max().date()),
            "total_events": len(df),
        },
        "full_period": metrics_full,
        "bucket_A": {
            "label": "2024-all",
            "range": f"{df['ts'].min().date()} to 2024-12-31",
            **metrics_a,
        },
        "bucket_B": {
            "label": "2025-H1",
            "range": "2025-01-01 to 2025-06-30",
            **metrics_b,
        },
        "bucket_C": {
            "label": "2025-H2+2026",
            "range": "2025-07-01 to present",
            **metrics_c,
        },
        "rolling": {
            "window_days": ROLLING_DAYS,
            "window_events": ROLLING_EVENTS,
            "recent_90d_sharpe": float(recent_sharpe) if not np.isnan(recent_sharpe) else None,
            "recent_90d_mean_spread_bps": float(recent_mean_spread),
        },
        "trend_test": trend,
        "decision": decision,
    }

    return result, rolling_df


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    print("=" * 70)
    print("Wave K186 — Carry Decay Empirical Test")
    print("=" * 70)

    all_results = {}
    all_curves = {}

    for sym in SYMBOLS:
        try:
            out = analyze_symbol(sym)
            if out is None:
                continue
            result, rolling_df = out
            all_results[sym] = result

            # Store rolling Sharpe curve (convert timestamps to strings)
            rolling_df["ts_str"] = rolling_df["ts"].astype(str)
            rolling_valid = rolling_df.dropna(subset=["rolling_sharpe"])
            all_curves[sym] = {
                "timestamps": rolling_valid["ts_str"].tolist(),
                "rolling_sharpe": [
                    float(v) if not np.isnan(v) else None
                    for v in rolling_valid["rolling_sharpe"].tolist()
                ],
            }
        except Exception as e:
            print(f"  [{sym}] ERROR: {e}")
            import traceback; traceback.print_exc()

    # --- Overall verdict ---
    decisions = {sym: all_results[sym]["decision"] for sym in all_results}
    print("\n" + "=" * 70)
    print("DECISION MATRIX SUMMARY")
    print("=" * 70)
    for sym, dec in decisions.items():
        m = all_results[sym]
        print(f"  {sym:6s}  {dec:20s}  "
              f"Full Sh={m['full_period']['sharpe']:.2f}  "
              f"Recent90d Sh={m['rolling']['recent_90d_sharpe']:.2f}  "
              f"Recent Mean={m['rolling']['recent_90d_mean_spread_bps']:.4f} bps")

    n_stable = sum(1 for d in decisions.values() if d == "STABLE")
    n_decaying = sum(1 for d in decisions.values() if d == "DECAYING")
    n_collapsed = sum(1 for d in decisions.values() if d == "COLLAPSED")

    if n_collapsed > 0:
        overall_verdict = "REJECT"
        weight_cap = 0
        verdict_reason = f"{n_collapsed} symbol(s) COLLAPSED (negative recent Sharpe or negative spread). Recommend K185 REJECTION or quarantine."
    elif n_decaying > 0:
        overall_verdict = "REDUCED_WEIGHT"
        weight_cap = 7
        verdict_reason = f"{n_decaying} symbol(s) DECAYING, {n_stable} STABLE. Recommend K185 reduced weight cap 5-10%."
    else:
        overall_verdict = "FULL_WEIGHT"
        weight_cap = 17
        verdict_reason = f"All {n_stable} symbols STABLE. Recommend K185 full weight 15-20%."

    print(f"\nOverall verdict: {overall_verdict}")
    print(f"Recommended K185 weight cap: {weight_cap}%")
    print(f"Reason: {verdict_reason}")

    summary = {
        "wave": "K186",
        "timestamp": pd.Timestamp.now().isoformat(),
        "symbols_analyzed": list(all_results.keys()),
        "decisions": decisions,
        "n_stable": n_stable,
        "n_decaying": n_decaying,
        "n_collapsed": n_collapsed,
        "overall_verdict": overall_verdict,
        "recommended_weight_cap_pct": weight_cap,
        "verdict_reason": verdict_reason,
        "per_symbol": {
            sym: {k: v for k, v in all_results[sym].items() if k != "rolling_df"}
            for sym in all_results
        },
    }

    # Save JSON outputs
    out_json = OUT_DIR / "wave_k186_carry_decay.json"
    with open(out_json, "w") as f:
        json.dump(summary, f, indent=2, default=str)
    print(f"\nSaved: {out_json}")

    out_curves = OUT_DIR / "wave_k186_curves.json"
    with open(out_curves, "w") as f:
        json.dump(all_curves, f, indent=2, default=str)
    print(f"Saved: {out_curves}")

    elapsed = time.time() - START
    print(f"\nTotal runtime: {elapsed:.1f}s")

    return summary, all_results, all_curves


if __name__ == "__main__":
    result = main()
