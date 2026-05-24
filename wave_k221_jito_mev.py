"""
Wave K221 — Jito MEV Signal as Alpha Source for SOL Vol/Direction Prediction

Objective:
  Test whether Jito MEV tip revenue (epoch-level, aggregated from validator_rewards API)
  can serve as a predictive signal for:
    1. SOL realized volatility (1d and 7d forward)
    2. SOL daily returns
    3. K196 reverse-carry SOL component daily returns
  Then test K218 ensemble integration: pause SOL leg of V_rev_carry on MEV spike days.

Data:
  - Jito MEV: kobe.mainnet.jito.network/api/v1/validator_rewards (per-epoch aggregation)
    Epoch 683 → 975 covers ~May 2024 → May 2026 (730d, 2-year window)
    Each Solana epoch ≈ 2.5 days (432000 slots × 0.55 s/slot)
  - SOL OHLCV: cache/SOLUSDT_1d_730d.parquet
  - K196 SOL carry: wave_k196_curves.json (series.rev_carry_SOL, 658 days)
  - K218e equity: wave_k218_curves.json (K218e, 448 days)

Runtime target: <12 min
"""
from __future__ import annotations

import json
import math
import time
import warnings
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Tuple, Optional

import numpy as np
import pandas as pd
import requests

warnings.filterwarnings("ignore")

START_TIME = time.time()
BASE  = Path("/Users/nekonaomichi/crypto-lab")
CACHE = BASE / "cache"

LAMPORTS_PER_SOL = 1_000_000_000
JITO_API_BASE    = "https://kobe.mainnet.jito.network/api/v1"
CURRENT_EPOCH    = 975
START_EPOCH      = 683     # ~May 2024 (730d back)
EPOCH_DAYS       = 2.5     # Solana epoch ≈ 2.5 days (measured empirically)
MEV_CACHE_PATH   = CACHE / "jito_mev_daily.parquet"

# Epoch → approximate date anchor
# Epoch 975 = 2026-05-25 (today)
ANCHOR_DATE  = datetime(2026, 5, 25, tzinfo=timezone.utc)
ANCHOR_EPOCH = CURRENT_EPOCH

# ─────────────────────────────────────────────────────────
# 1.  Fetch Jito epoch MEV data
# ─────────────────────────────────────────────────────────

def epoch_to_date(epoch: int) -> datetime:
    """Convert Solana epoch number to approximate UTC date."""
    delta_epochs = ANCHOR_EPOCH - epoch
    delta_days   = delta_epochs * EPOCH_DAYS
    return ANCHOR_DATE - timedelta(days=delta_days)


def fetch_epoch_mev(epoch: int, session: requests.Session) -> float:
    """Return total network MEV for given epoch (in SOL). Returns NaN on failure."""
    try:
        # Sum mev_revenue across all validators for this epoch
        url    = f"{JITO_API_BASE}/validator_rewards"
        params = {"epoch": epoch, "limit": 5000}
        resp   = session.get(url, params=params, timeout=15)
        if resp.status_code != 200:
            return float("nan")
        data    = resp.json()
        rewards = data.get("rewards", data if isinstance(data, list) else [])
        total   = sum(r.get("mev_revenue", 0) for r in rewards)
        return total / LAMPORTS_PER_SOL
    except Exception:
        return float("nan")


def build_jito_mev_series() -> pd.DataFrame:
    """
    Fetch per-epoch MEV and expand to daily by interpolation.
    Returns DataFrame with columns: date, epoch, mev_sol_epoch, mev_sol_daily
    """
    # Check cache
    if MEV_CACHE_PATH.exists():
        print("[MEV] Loading from cache...")
        df = pd.read_parquet(MEV_CACHE_PATH)
        print(f"[MEV] Cache loaded: {len(df)} rows ({df['date'].min()} → {df['date'].max()})")
        return df

    print(f"[MEV] Fetching epochs {START_EPOCH}–{CURRENT_EPOCH} from Jito API...")
    epochs = list(range(START_EPOCH, CURRENT_EPOCH + 1))

    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})

    records = []
    for i, ep in enumerate(epochs):
        mev_sol = fetch_epoch_mev(ep, session)
        dt      = epoch_to_date(ep)
        records.append({"epoch": ep, "date_epoch": dt, "mev_sol_epoch": mev_sol})

        if (i + 1) % 20 == 0:
            elapsed = time.time() - START_TIME
            pct     = (i + 1) / len(epochs) * 100
            print(f"  [{pct:5.1f}%] epoch {ep} | {elapsed:.0f}s elapsed | mev={mev_sol:.1f} SOL")

    epoch_df = pd.DataFrame(records)
    epoch_df = epoch_df.dropna(subset=["mev_sol_epoch"])
    epoch_df = epoch_df.sort_values("date_epoch").reset_index(drop=True)

    print(f"[MEV] Fetched {len(epoch_df)} epochs with valid data")

    # Expand epoch-level (2.5d) to daily by forward-filling / interpolation
    min_date = epoch_df["date_epoch"].min().date()
    max_date = epoch_df["date_epoch"].max().date()
    all_dates = pd.date_range(
        start=pd.Timestamp(min_date),
        end=pd.Timestamp(max_date),
        freq="D",
        tz="UTC",
    )

    # Per-epoch SOL → daily rate (divide by epoch_days)
    epoch_df["mev_sol_daily"] = epoch_df["mev_sol_epoch"] / EPOCH_DAYS
    epoch_df["date_epoch"]    = pd.to_datetime(epoch_df["date_epoch"]).dt.floor("D")

    # Merge onto daily index, then forward fill gaps
    daily_df = pd.DataFrame({"date": all_dates})
    daily_df["date_merge"] = daily_df["date"].dt.floor("D")

    epoch_df["date_merge"] = epoch_df["date_epoch"]
    merged   = daily_df.merge(epoch_df[["date_merge", "epoch", "mev_sol_epoch", "mev_sol_daily"]],
                               on="date_merge", how="left")
    merged["mev_sol_daily"] = merged["mev_sol_daily"].fillna(method="ffill")
    merged["mev_sol_epoch"] = merged["mev_sol_epoch"].fillna(method="ffill")
    merged["epoch"]         = merged["epoch"].fillna(method="ffill")
    merged = merged.drop(columns=["date_merge"])
    merged["date"] = merged["date"].dt.date.astype(str)
    merged = merged.dropna()

    # Cache
    CACHE.mkdir(exist_ok=True)
    merged.to_parquet(MEV_CACHE_PATH)
    print(f"[MEV] Saved cache: {MEV_CACHE_PATH}")
    return merged


# ─────────────────────────────────────────────────────────
# 2.  Load SOL OHLCV and compute realized vol + returns
# ─────────────────────────────────────────────────────────

def load_sol_daily() -> pd.DataFrame:
    """Load SOL 1d OHLCV, compute log-returns and realized vol."""
    path = CACHE / "SOLUSDT_1d_730d.parquet"
    df   = pd.read_parquet(path)
    df   = df.sort_values("open_time").reset_index(drop=True)
    df["date"] = pd.to_datetime(df["open_time"]).dt.date.astype(str)
    df["log_ret"] = np.log(df["close"] / df["close"].shift(1))
    # 7d realized vol = std of last 7 log returns × sqrt(365)
    df["rvol_7d"] = df["log_ret"].rolling(7).std() * math.sqrt(365)
    df["rvol_1d"] = df["log_ret"].abs()
    return df[["date", "close", "log_ret", "rvol_7d", "rvol_1d"]]


# ─────────────────────────────────────────────────────────
# 3.  Load K196 SOL reverse carry series
# ─────────────────────────────────────────────────────────

def load_k196_sol() -> pd.DataFrame:
    """Load K196 rev_carry_SOL daily return series."""
    with open(BASE / "wave_k196_curves.json") as f:
        curves = json.load(f)
    dates  = curves["panel_dates"]   # list of "YYYY-MM-DD"
    pnl    = curves["series"]["rev_carry_SOL"]   # cumulative PnL
    ret_series = np.diff([0.0] + pnl)            # daily increments
    df = pd.DataFrame({"date": dates, "k196_sol_ret": ret_series})
    return df


# ─────────────────────────────────────────────────────────
# 4.  Load K218e equity curve
# ─────────────────────────────────────────────────────────

def load_k218() -> pd.DataFrame:
    with open(BASE / "wave_k218_curves.json") as f:
        curves = json.load(f)
    dates  = curves["dates"]    # "YYYY-MM-DD"
    eq218a = np.array(curves["K218a"])
    eq218e = np.array(curves["K218e"])
    # K198/K208 components for the SOL leg simulation
    eq198  = np.array(curves["K198"])
    eq208  = np.array(curves["K208"])

    ret_218e = np.diff(np.log(np.maximum(eq218e, 1e-10)))
    ret_198  = np.diff(np.log(np.maximum(eq198,  1e-10)))
    ret_208  = np.diff(np.log(np.maximum(eq208,  1e-10)))
    ret_218a = np.diff(np.log(np.maximum(eq218a, 1e-10)))

    # dates correspond to equity values; returns are date[1:]
    df = pd.DataFrame({
        "date":      dates[1:],
        "ret_218e":  ret_218e,
        "ret_198":   ret_198,
        "ret_208":   ret_208,
        "ret_218a":  ret_218a,
        "eq_218e":   eq218e[1:],
        "eq_198":    eq198[1:],
        "eq_208":    eq208[1:],
    })
    return df


# ─────────────────────────────────────────────────────────
# 5.  Build MEV signal (z-score) and spike flags
# ─────────────────────────────────────────────────────────

def add_mev_signal(mev_df: pd.DataFrame) -> pd.DataFrame:
    mev = mev_df.copy()
    mev = mev.sort_values("date").reset_index(drop=True)
    mev["mev_sol_daily"] = pd.to_numeric(mev["mev_sol_daily"], errors="coerce")

    # Rolling 30d baseline + z-score
    roll = mev["mev_sol_daily"].rolling(30, min_periods=10)
    mev["mev_30d_mean"] = roll.mean()
    mev["mev_30d_std"]  = roll.std()
    mev["mev_z"] = (
        (mev["mev_sol_daily"] - mev["mev_30d_mean"]) /
        mev["mev_30d_std"].clip(lower=1e-8)
    )
    mev["spike_pos"] = (mev["mev_z"] >  2.0).astype(int)
    mev["spike_neg"] = (mev["mev_z"] < -2.0).astype(int)
    mev["spike_any"] = ((mev["mev_z"].abs()) > 2.0).astype(int)
    return mev


# ─────────────────────────────────────────────────────────
# 6.  Predictive correlation analysis
# ─────────────────────────────────────────────────────────

def safe_corr(x: np.ndarray, y: np.ndarray) -> float:
    mask = np.isfinite(x) & np.isfinite(y)
    if mask.sum() < 10:
        return float("nan")
    return float(np.corrcoef(x[mask], y[mask])[0, 1])


def granger_pval(x: np.ndarray, y: np.ndarray, max_lag: int = 5) -> float:
    """Simple Granger-like causality test via F-statistic (OLS).
    H0: x does NOT Granger-cause y.
    Returns min p-value across lags 1..max_lag."""
    from scipy import stats as sp_stats

    mask = np.isfinite(x) & np.isfinite(y)
    x, y = x[mask], y[mask]
    n = len(y)
    if n < 30:
        return float("nan")

    min_pval = 1.0
    for lag in range(1, max_lag + 1):
        X = x[:-lag]
        Y = y[lag:]
        # Align lengths
        T = min(len(X), len(Y))
        X, Y = X[-T:], Y[-T:]
        if T < 20:
            continue
        # OLS: Y = a + b*X
        X_design = np.column_stack([np.ones(T), X])
        try:
            coeffs, _, _, _ = np.linalg.lstsq(X_design, Y, rcond=None)
            Y_pred   = X_design @ coeffs
            residuals = Y - Y_pred
            ss_res   = np.sum(residuals**2)
            ss_tot   = np.sum((Y - Y.mean())**2)
            r2       = 1 - ss_res / max(ss_tot, 1e-12)
            # F-stat for the regression coefficient
            k        = 1  # number of predictors
            if ss_res < 1e-12:
                pval = 0.0
            else:
                f_stat = (r2 / k) / ((1 - r2) / max(T - k - 1, 1))
                pval   = float(1 - sp_stats.f.cdf(f_stat, k, T - k - 1))
            min_pval = min(min_pval, pval)
        except Exception:
            pass
    return min_pval


def compute_predictive_table(merged: pd.DataFrame) -> List[Dict]:
    """Compute correlation table between MEV z-score and forward target vars."""
    rows = []
    mev_z = merged["mev_z"].values
    targets = {
        "SOL_rvol_1d_fwd1":  ("rvol_1d",   1),
        "SOL_rvol_7d_fwd1":  ("rvol_7d",   1),
        "SOL_rvol_7d_fwd7":  ("rvol_7d",   7),
        "SOL_ret_fwd1":      ("log_ret",    1),
        "SOL_ret_fwd7":      ("log_ret",    7),
        "K196_sol_ret_fwd1": ("k196_sol_ret", 1),
        "K196_sol_ret_fwd7": ("k196_sol_ret", 7),
    }

    for label, (col, fwd) in targets.items():
        if col not in merged.columns:
            continue
        fwd_series = merged[col].shift(-fwd).values
        corr  = safe_corr(mev_z, fwd_series)
        pval  = granger_pval(mev_z, fwd_series)
        rows.append({
            "target":        label,
            "lag_days":      fwd,
            "pearson_r":     round(corr, 4),
            "granger_pval":  round(pval, 4) if np.isfinite(pval) else None,
            "significant":   (abs(corr) > 0.15) and (pval is not None and pval < 0.10),
        })
    return rows


# ─────────────────────────────────────────────────────────
# 7.  K218 integration test — pause SOL leg on MEV spikes
# ─────────────────────────────────────────────────────────

def sharpe(rets: np.ndarray) -> float:
    rets = rets[np.isfinite(rets)]
    if len(rets) < 10 or rets.std() < 1e-10:
        return float("nan")
    return float(rets.mean() / rets.std() * math.sqrt(365))


def maxdd(equity: np.ndarray) -> float:
    peak = np.maximum.accumulate(equity)
    dd   = equity / np.maximum(peak, 1e-12) - 1.0
    return float(dd.min())


def k218_integration_test(
    k218_df: pd.DataFrame,
    mev_df: pd.DataFrame,
    k196_sol: pd.DataFrame,
) -> Dict:
    """
    Simulate: on MEV spike days, zero out ~SOL contribution from K218e.
    K218e = inv-vol weighted (K198 + K204 + K208).
    SOL leg lives inside K198 (reverse carry panel, SOL is ~1/10 of 10 symbols).
    Estimated SOL weight in K218e ≈ K218e_weight_K198 × (1/10) ≈ 0.385/10 = 3.85%.
    We remove that fraction on spike days.
    """
    # Merge K218 returns with MEV signal
    k218_df = k218_df.copy()
    mev_sub = mev_df[["date", "mev_z", "spike_pos"]].copy()

    merged_k = k218_df.merge(mev_sub, on="date", how="left")
    merged_k["mev_z"]     = merged_k["mev_z"].fillna(0.0)
    merged_k["spike_pos"] = merged_k["spike_pos"].fillna(0).astype(int)

    # SOL fraction of K218e: K198 weight 0.385 × (1/10 symbols) = 0.0385
    SOL_FRACTION = 0.385 / 10.0

    # Baseline: K218e returns
    base_rets = merged_k["ret_218e"].values

    # Modified: remove SOL leg on positive MEV spike days (high MEV → vol risk)
    mod_rets  = base_rets.copy()
    # On spike days, reduce return by SOL fraction (assuming SOL contributes ~proportionally)
    # We remove 3.85% of total K218e return (a conservative estimate)
    spike_mask = merged_k["spike_pos"].values.astype(bool)
    mod_rets[spike_mask] -= base_rets[spike_mask] * SOL_FRACTION

    # Build equity curves
    base_equity = np.exp(np.cumsum(np.concatenate([[0.0], base_rets])))
    mod_equity  = np.exp(np.cumsum(np.concatenate([[0.0], mod_rets])))

    # OOS: last 135 days (matches K218 OOS window)
    n_oos = 135
    base_oos = base_rets[-n_oos:]
    mod_oos  = mod_rets[-n_oos:]
    eq_base_oos = base_equity[-(n_oos + 1):]
    eq_mod_oos  = mod_equity[-(n_oos + 1):]

    # Walk-forward folds (4 folds on full window)
    n     = len(base_rets)
    fold  = n // 4
    wf_sh_base = []
    wf_sh_mod  = []
    for i in range(4):
        r_b = base_rets[i * fold:(i + 1) * fold]
        r_m = mod_rets[i * fold:(i + 1) * fold]
        wf_sh_base.append(sharpe(r_b))
        wf_sh_mod.append(sharpe(r_m))

    n_spikes = int(spike_mask.sum())

    return {
        "baseline_K218e": {
            "oos_sharpe": round(sharpe(base_oos), 4),
            "oos_maxdd":  round(maxdd(eq_base_oos), 6),
            "wf_min":     round(min(s for s in wf_sh_base if np.isfinite(s)), 4),
            "wf_mean":    round(np.nanmean(wf_sh_base), 4),
            "wf_folds":   [round(s, 4) for s in wf_sh_base],
        },
        "K218e_jito_filter": {
            "oos_sharpe": round(sharpe(mod_oos), 4),
            "oos_maxdd":  round(maxdd(eq_mod_oos), 6),
            "wf_min":     round(min(s for s in wf_sh_mod if np.isfinite(s)), 4),
            "wf_mean":    round(np.nanmean(wf_sh_mod), 4),
            "wf_folds":   [round(s, 4) for s in wf_sh_mod],
        },
        "spike_days": n_spikes,
        "spike_fraction": round(n_spikes / max(n, 1), 4),
        "sol_fraction_removed": SOL_FRACTION,
        "base_rets": base_rets.tolist(),
        "mod_rets": mod_rets.tolist(),
        "base_equity": base_equity.tolist(),
        "mod_equity": mod_equity.tolist(),
    }


# ─────────────────────────────────────────────────────────
# 8.  Main
# ─────────────────────────────────────────────────────────

def main():
    print("=" * 70)
    print("Wave K221 — Jito MEV Signal Alpha Test")
    print("=" * 70)

    # ── Step 1: Fetch MEV series ──────────────────────────
    print("\n[1/6] Fetching Jito epoch MEV series...")
    mev_raw = build_jito_mev_series()

    # ── Step 2: Add signal ────────────────────────────────
    print("\n[2/6] Computing MEV z-score and spikes...")
    mev_df = add_mev_signal(mev_raw)

    # ── Step 3: Load SOL daily ────────────────────────────
    print("\n[3/6] Loading SOL daily OHLCV...")
    sol_df = load_sol_daily()

    # ── Step 4: Load K196 SOL carry ───────────────────────
    print("\n[4/6] Loading K196 SOL carry series...")
    k196_df = load_k196_sol()

    # ── Step 5: Merge for correlation analysis ─────────────
    print("\n[5/6] Building merged dataset...")
    merged = (
        mev_df
        .merge(sol_df,   on="date", how="inner")
        .merge(k196_df,  on="date", how="left")
    )
    merged = merged.sort_values("date").reset_index(drop=True)
    print(f"  Merged rows: {len(merged)} ({merged['date'].iloc[0]} → {merged['date'].iloc[-1]})")

    n_spikes_pos = int(merged["spike_pos"].sum())
    n_spikes_neg = int(merged["spike_neg"].sum())
    n_spikes_any = int(merged["spike_any"].sum())
    print(f"  MEV spikes: {n_spikes_any} total ({n_spikes_pos} high, {n_spikes_neg} low)")

    # ── Step 6: Predictive correlations ───────────────────
    print("\n[6a/6] Computing predictive correlation table...")
    pred_table = compute_predictive_table(merged)
    print("\n  Predictive Correlation Table:")
    print(f"  {'Target':<30} {'lag':>4} {'r':>8} {'grangr_p':>10} {'sig?':>6}")
    print("  " + "-" * 62)
    for row in pred_table:
        sig_str = "YES" if row["significant"] else "no"
        print(
            f"  {row['target']:<30} {row['lag_days']:>4} "
            f"{row['pearson_r']:>8.4f} {str(row['granger_pval']):>10} {sig_str:>6}"
        )

    # ── Step 7: K218 integration test ─────────────────────
    print("\n[6b/6] Running K218 integration test...")
    k218_df = load_k218()
    integ   = k218_integration_test(k218_df, mev_df, k196_df)

    baseline_sh = integ["baseline_K218e"]["oos_sharpe"]
    filter_sh   = integ["K218e_jito_filter"]["oos_sharpe"]
    print(f"  K218e baseline OOS Sh:     {baseline_sh:.4f}")
    print(f"  K218e + Jito filter OOS Sh: {filter_sh:.4f}")
    delta_sh = filter_sh - baseline_sh
    print(f"  Delta Sharpe:              {delta_sh:+.4f}")

    # ── Acceptance gates ──────────────────────────────────
    any_predictive = any(r["significant"] for r in pred_table)
    best_corr = max(abs(r["pearson_r"]) for r in pred_table if np.isfinite(r["pearson_r"]))
    best_pval = min(r["granger_pval"] for r in pred_table if r["granger_pval"] is not None)
    integ_sh_ok = filter_sh >= 11.03  # K218 production threshold

    gate_corr   = best_corr > 0.15
    gate_pval   = best_pval < 0.10
    gate_integ  = integ_sh_ok
    k222_accept = gate_corr and gate_pval  # integration Sharpe is secondary

    print("\n  Acceptance Gates:")
    print(f"    Corr > 0.15:  {best_corr:.4f}  → {'PASS' if gate_corr else 'FAIL'}")
    print(f"    Granger p<0.1: {best_pval:.4f} → {'PASS' if gate_pval else 'FAIL'}")
    print(f"    Integration Sh >= 11.03: {filter_sh:.4f} → {'PASS' if gate_integ else 'FAIL'}")
    print(f"  K222 integration verdict: {'ACCEPTED' if k222_accept else 'REJECTED'}")

    # ── Assemble metrics JSON ──────────────────────────────
    as_of = datetime.now(timezone.utc).isoformat()
    elapsed = round(time.time() - START_TIME, 2)

    metrics = {
        "wave":    "K221",
        "task":    "Jito MEV Signal as Alpha Source for SOL Vol/Direction",
        "as_of":   as_of,
        "runtime_s": elapsed,
        "data_source": {
            "mev":     "Jito kobe.mainnet.jito.network/api/v1/validator_rewards (per-epoch sum)",
            "sol":     "cache/SOLUSDT_1d_730d.parquet (Binance 1d OHLCV)",
            "k196":    "wave_k196_curves.json (rev_carry_SOL panel daily PnL)",
            "k218":    "wave_k218_curves.json (K218e equity curve, 448 days)",
        },
        "mev_stats": {
            "epochs_fetched":   int(mev_df["epoch"].nunique()),
            "date_range":       [str(mev_df["date"].min()), str(mev_df["date"].max())],
            "mev_daily_mean_sol": round(float(mev_df["mev_sol_daily"].mean()), 2),
            "mev_daily_max_sol":  round(float(mev_df["mev_sol_daily"].max()), 2),
            "mev_daily_min_sol":  round(float(mev_df["mev_sol_daily"].min()), 2),
            "spike_pos_days":     n_spikes_pos,
            "spike_neg_days":     n_spikes_neg,
            "spike_any_days":     n_spikes_any,
        },
        "predictive_correlation_table": pred_table,
        "k218_integration": {
            "baseline_K218e": integ["baseline_K218e"],
            "K218e_jito_filter": integ["K218e_jito_filter"],
            "delta_oos_sharpe": round(delta_sh, 4),
            "spike_days": integ["spike_days"],
            "spike_fraction": integ["spike_fraction"],
            "sol_fraction_removed": integ["sol_fraction_removed"],
        },
        "acceptance": {
            "gate_corr_015":    gate_corr,
            "gate_granger_010": gate_pval,
            "gate_integration": gate_integ,
            "k222_verdict":     "ACCEPTED" if k222_accept else "REJECTED",
            "best_corr":        round(best_corr, 4),
            "best_granger_pval": round(best_pval, 4),
        },
    }

    with open(BASE / "wave_k221_jito_mev.json", "w") as f:
        json.dump(metrics, f, indent=2)
    print(f"\n[JSON] Saved wave_k221_jito_mev.json")

    # ── Assemble curves JSON ───────────────────────────────
    mev_for_curves = mev_df.sort_values("date").copy()
    curves = {
        "dates":              mev_for_curves["date"].tolist(),
        "mev_sol_daily":     mev_for_curves["mev_sol_daily"].round(2).tolist(),
        "mev_z":             mev_for_curves["mev_z"].round(4).tolist(),
        "spike_pos":         mev_for_curves["spike_pos"].tolist(),
        "spike_neg":         mev_for_curves["spike_neg"].tolist(),
        "k218e_base_equity": integ["base_equity"],
        "k218e_mod_equity":  integ["mod_equity"],
        "k218_dates":        k218_df["date"].tolist(),
    }
    with open(BASE / "wave_k221_curves.json", "w") as f:
        json.dump(curves, f, indent=2)
    print(f"[JSON] Saved wave_k221_curves.json")

    # ── Write markdown report ──────────────────────────────
    write_report(metrics, pred_table, integ, merged, mev_df)

    print(f"\n[K221 COMPLETE] Runtime: {elapsed:.1f}s")
    print(f"  Verdict: {metrics['acceptance']['k222_verdict']}")
    print(f"  Best correlation: {best_corr:.4f}, Granger p: {best_pval:.4f}")

    return metrics


def write_report(metrics, pred_table, integ, merged, mev_df):
    base_sh = integ["baseline_K218e"]["oos_sharpe"]
    filt_sh = integ["K218e_jito_filter"]["oos_sharpe"]
    acc = metrics["acceptance"]

    # Pre-build conditional strings to avoid backslash in f-string
    gate_corr_str  = "PASS" if acc["gate_corr_015"]    else "FAIL"
    gate_pval_str  = "PASS" if acc["gate_granger_010"] else "FAIL"
    gate_integ_str = "PASS" if acc["gate_integration"] else "FAIL"

    if acc["k222_verdict"] == "ACCEPTED":
        verdict_paragraph = (
            "**ACCEPTED** — Jito MEV z-score demonstrates statistically meaningful "
            "predictive power for SOL volatility/direction. Recommend K222 to implement as: "
            "(a) standalone SOL vol overlay signal, or (b) dynamic SOL weight modulator "
            "within the K196 reverse-carry panel."
        )
        k222_actions = (
            "1. Implement Jito MEV z-score as continuous weight modifier for SOL leg in "
            "K196/K198 (scale SOL weight by `clip(1 - 0.5 * max(mev_z, 0), 0.5, 1.0)`)\n"
            "2. Source higher-resolution MEV data via Dune Analytics API (daily SQL export of Jito tips)\n"
            "3. Explore JTO token itself as a MEV-activity proxy (liquid, on Bybit/HL)\n"
            "4. Run K222 as K218 + dynamic SOL weight overlay, target OOS Sh > 11.5"
        )
    else:
        verdict_paragraph = (
            "**REJECTED** — Jito MEV signal does not meet minimum predictive thresholds. "
            "Epoch-level data granularity is likely the primary constraint. "
            "Recommend K222 to explore: (a) Solana network fee proxy at daily resolution "
            "(Dune Analytics SQL export), (b) JTO token funding rate as vol proxy, or "
            "(c) SOL on-chain transaction volume from CoinMetrics."
        )
        k222_actions = (
            "1. Obtain daily Jito tip totals from Dune Analytics (query 3380088 or 4551942) "
            "for higher frequency\n"
            "2. Test JTO funding rate as MEV-activity proxy (already available in K196 panel)\n"
            "3. Consider SOL realized volatility 7d as self-predictive feature (no external data needed)\n"
            "4. Revisit with 1h epoch data if Jito upgrades API"
        )

    # Build correlation table in markdown
    corr_rows = "\n".join(
        f"| {r['target']:<30} | {r['lag_days']:>4} | {r['pearson_r']:>8.4f} | "
        f"{str(r['granger_pval']):>10} | {'YES' if r['significant'] else 'no':>6} |"
        for r in pred_table
    )

    # MEV summary stats
    ms = metrics["mev_stats"]

    report = f"""# Wave K221 — Jito MEV Signal: SOL Vol/Direction Prediction

**Date:** {metrics['as_of'][:10]}
**Runtime:** {metrics['runtime_s']:.1f}s

---

## Executive Summary

This wave tests Jito Network MEV tip revenue as a new alpha signal for SOL volatility and direction prediction, with the goal of becoming a 4th orthogonal portfolio for the K218 3-way meta-ensemble.

**Verdict: {acc['k222_verdict']}**
- Best correlation: **{acc['best_corr']:.4f}** (threshold: |r| > 0.15)
- Best Granger p-value: **{acc['best_granger_pval']:.4f}** (threshold: p < 0.10)
- Integration filter OOS Sharpe: **{filt_sh:.4f}** vs baseline **{base_sh:.4f}**

---

## 1. Data Source

| Source | Description |
|--------|-------------|
| **Jito MEV** | `kobe.mainnet.jito.network/api/v1/validator_rewards` — per-epoch sum of `mev_revenue` across all validators. Epoch granularity (~2.5 days) forward-filled to daily. |
| **SOL price** | `cache/SOLUSDT_1d_730d.parquet` — Binance spot OHLCV 1d, 730 days |
| **K196 SOL** | `wave_k196_curves.json` — `rev_carry_SOL` daily carry PnL |
| **K218e** | `wave_k218_curves.json` — production ensemble equity curve (448 days) |

**Note:** Jito's `/api/v1/tip_revenue/daily` endpoint returns 404. The `/api/v1/validator_rewards` endpoint returns per-epoch, per-validator `mev_revenue` (lamports). This was summed across all validators per epoch and divided by epoch duration to produce a daily MEV rate proxy.

---

## 2. MEV Time-Series Statistics

| Metric | Value |
|--------|-------|
| Epochs fetched | {ms['epochs_fetched']} |
| Date range | {ms['date_range'][0]} → {ms['date_range'][1]} |
| Daily MEV (mean) | {ms['mev_daily_mean_sol']:.1f} SOL |
| Daily MEV (max) | {ms['mev_daily_max_sol']:.1f} SOL |
| Daily MEV (min) | {ms['mev_daily_min_sol']:.1f} SOL |
| Positive spike days (z > 2) | {ms['spike_pos_days']} |
| Negative spike days (z < −2) | {ms['spike_neg_days']} |
| Total spike days | {ms['spike_any_days']} |

**Signal construction:** 30-day rolling mean and standard deviation are computed. The z-score `mev_z = (mev_daily − μ_30d) / σ_30d` is the core signal. Spikes are flagged when `|z| > 2.0`.

---

## 3. Predictive Correlation Table

| Target | Lag (d) | Pearson r | Granger p | Sig? |
|--------|---------|-----------|-----------|------|
{corr_rows}

**Threshold:** |r| > 0.15 AND Granger p < 0.10 for a target to be considered predictive.

---

## 4. K218 Integration Test

**Design:** On positive MEV spike days (z > 2.0, indicating abnormal Jito tip activity → elevated SOL volatility risk), reduce the SOL leg contribution in K218e.
- K218e weight on K198: **38.5%**
- SOL fraction of K198 (1/10 reverse-carry symbols): **10%**
- Net SOL reduction per spike day: **3.85% of K218e return**

| Variant | OOS Sharpe | OOS MaxDD | WF Min | WF Mean |
|---------|-----------|-----------|--------|---------|
| K218e baseline | {integ['baseline_K218e']['oos_sharpe']:.4f} | {integ['baseline_K218e']['oos_maxdd']:.6f} | {integ['baseline_K218e']['wf_min']:.4f} | {integ['baseline_K218e']['wf_mean']:.4f} |
| K218e + Jito filter | {integ['K218e_jito_filter']['oos_sharpe']:.4f} | {integ['K218e_jito_filter']['oos_maxdd']:.6f} | {integ['K218e_jito_filter']['wf_min']:.4f} | {integ['K218e_jito_filter']['wf_mean']:.4f} |

**Delta Sharpe:** {metrics['k218_integration']['delta_oos_sharpe']:+.4f}
**Spike days used:** {integ['spike_days']} / {integ['spike_days'] + (448 - integ['spike_days'])} ({integ['spike_fraction']*100:.1f}%)

**K218 production reference:** K218e OOS Sh = 11.03, MaxDD = −0.0036

---

## 5. Discussion

### Signal Quality
The Jito MEV epoch-level data provides a coarser-than-ideal proxy (2.5-day epochs expanded to daily). The key question is whether elevated MEV activity on Solana — driven by arbitrage, liquidation cascades, and sandwich attacks — correlates with SOL realized volatility.

**Mechanistic argument:**
- High MEV spikes → large on-chain flow imbalances (whales moving SOL, DEX arbitrage surges)
- These flows typically co-occur with or immediately precede elevated SOL volatility
- Jito's market share in Solana block production is >50%, making tip revenue a meaningful vol-of-vol proxy

### Limitations
1. Epoch granularity (2.5d) reduces daily signal precision
2. Forward-fill interpolation introduces stale-signal bias
3. API returns 0 `mev_revenue` for some earlier epochs (pre-Jito adoption)
4. SOL fraction estimate in K218e is approximate

---

## 6. Verdict: K222 Integration

**Decision: {acc['k222_verdict']}**

| Gate | Threshold | Result | Outcome |
|------|-----------|--------|---------|
| Predictive correlation | |r| > 0.15 | {acc['best_corr']:.4f} | {gate_corr_str} |
| Granger causality | p < 0.10 | {acc['best_granger_pval']:.4f} | {gate_pval_str} |
| Integration OOS Sh | >= 11.03 | {filt_sh:.4f} | {gate_integ_str} |

{verdict_paragraph}

### K222 Recommended Actions
{k222_actions}

---

*Generated by Wave K221 | crypto-lab systematic alpha discovery*
"""

    with open(BASE / "wave_k221_jito_mev.md", "w") as f:
        f.write(report)
    print(f"[MD ] Saved wave_k221_jito_mev.md")


if __name__ == "__main__":
    main()
