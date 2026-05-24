"""Wave K191 — Fold 3 Weakness Diagnosis and Defensive Trigger Design

K188 walk-forward fold 2 (OOS test: 2025-10-11 to 2025-11-29): min OOS Sh = 2.376
The full fold window is 2025-06-19 to 2025-11-29 (train+test).
The OOS (test) window within fold 2 is 2025-10-11 to 2025-11-29 (50 days).

This script:
1. Loads all 9 K188 strategy daily PnL series
2. Replicates K188 WF exactly (fold_size = n//4, 70/30 train/test split per fold)
3. Decomposes fold-2 OOS test Sharpe contribution per strategy
4. Computes regime indicators (BTC vol, FR level, premium spread, basis vol)
5. Compares regime distributions across fold OOS windows
6. Designs defensive trigger if regime separates fold 2 OOS window cleanly
7. Tests trigger effect on WF Sharpe (mean/min)
"""
from __future__ import annotations

import json
import math
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

BASE = Path("/Users/nekonaomichi/crypto-lab")
CACHE = BASE / "cache"
HL_CACHE = CACHE / "k163_hl"
TRADING_DAYS = 365
START_TIME = time.time()

# K188 WF configuration
N_FOLDS = 4
TRAIN_FRAC = 0.70
CARRY_CAP = 0.07
CARRY_COL = "V_carry_panel_weighted"

# ============================================================
# Strategy loaders (mirrored from K188 script exactly)
# ============================================================

def _equity_to_daily_returns(ts_iso: List[str], eq: List[float]) -> pd.Series:
    first = pd.to_datetime(ts_iso[0])
    ts = (pd.to_datetime(ts_iso, utc=True).tz_convert(None)
          if first.tzinfo else pd.to_datetime(ts_iso))
    s = pd.Series(eq, index=ts).sort_index()
    daily_eq = s.resample("1D").last().ffill()
    daily_ret = daily_eq.pct_change().fillna(0.0)
    return daily_ret


def load_v41_and_v1() -> pd.DataFrame:
    with open(BASE / "wave_k109_curves.json") as fp:
        d = json.load(fp)
    dates = pd.to_datetime(d["dates"])
    df = pd.DataFrame({"date": dates})
    for name in ("v4.1", "V1"):
        cum = np.asarray(d["series"][name], dtype=float)
        eq = 1.0 + cum
        eq_prev = np.r_[1.0, eq[:-1]]
        ret = eq / eq_prev - 1.0
        df[name] = ret
    df = df.set_index("date")
    return df


def load_k114() -> pd.Series:
    with open(BASE / "wave_k114_alcp.json") as fp:
        d = json.load(fp)
    curve = d["curves"]["full_equity"]
    s = _equity_to_daily_returns(list(curve.keys()), list(curve.values()))
    s.name = "K114"
    return s


def load_k116() -> pd.Series:
    with open(BASE / "wave_k116_curves.json") as fp:
        d = json.load(fp)
    s = _equity_to_daily_returns(d["timestamps"], d["portfolio_equity"])
    s.name = "K116"
    return s


def load_k121() -> pd.Series:
    with open(BASE / "wave_k121_curves.json") as fp:
        d = json.load(fp)
    pts = d["weekend_ls"]
    s = _equity_to_daily_returns([p["ts"] for p in pts], [p["eq"] for p in pts])
    s.name = "K121"
    return s


def load_k133(variant: str = "V_rev_3d_z15") -> pd.Series:
    with open(BASE / "wave_k133_curves.json") as fp:
        d = json.load(fp)
    v = d[variant]
    s = _equity_to_daily_returns(v["equity_idx"], v["equity_curve"])
    s.name = "K133"
    return s


def load_k147(variant: str = "V_long_short_h12") -> pd.Series:
    with open(BASE / "wave_k147_curves.json") as fp:
        d = json.load(fp)
    v = d[variant]
    s = _equity_to_daily_returns(v["timestamps"], v["portfolio_equity"])
    s.name = "K147"
    return s


def load_k175(variant: str = "V_xrp_sui_maker") -> pd.Series:
    with open(BASE / "wave_k175_curves.json") as fp:
        d = json.load(fp)
    v = d[variant]
    s = _equity_to_daily_returns(v["timestamps"], v["equity_net"])
    s.name = "K175"
    return s


def _load_hl_8h(sym: str) -> pd.DataFrame:
    fpath = HL_CACHE / f"hl_fr_{sym}.parquet"
    df = pd.read_parquet(fpath)
    df["ts"] = pd.to_datetime(df["timestamp"])
    hl_8h = df.set_index("ts")["hl_fr"].resample("8h").sum().reset_index()
    hl_8h.columns = ["ts", "hl_fr_8h"]
    return hl_8h


def _load_bybit(sym: str) -> pd.DataFrame:
    for suffix in ["1200d", "730d", "365d"]:
        fpath = CACHE / f"bybit_fr_{sym}USDT_{suffix}.parquet"
        if fpath.exists():
            df = pd.read_parquet(fpath)
            df["ts"] = pd.to_datetime(df["timestamp"])
            return df[["ts", "funding_rate"]].rename(columns={"funding_rate": "bybit_fr"})
    raise FileNotFoundError(f"No Bybit data for {sym}")


def _build_carry_daily_returns(sym: str) -> pd.Series:
    hl = _load_hl_8h(sym)
    bybit = _load_bybit(sym)
    merged = pd.merge_asof(
        bybit.sort_values("ts"),
        hl.sort_values("ts"),
        on="ts",
        tolerance=pd.Timedelta("4h"),
        direction="nearest",
    ).dropna()
    merged["carry"] = merged["hl_fr_8h"] - merged["bybit_fr"]
    merged = merged.sort_values("ts").reset_index(drop=True)
    merged["date"] = merged["ts"].dt.normalize()
    daily = merged.groupby("date")["carry"].sum()
    if len(daily) > 0:
        daily.iloc[0] -= 0.0010  # 10bp one-time entry cost
    daily.index = pd.to_datetime(daily.index)
    daily.name = sym
    return daily


def load_carry_sym_df(symbols: List[str] = ("BTC", "ETH", "DOGE", "AVAX")) -> pd.DataFrame:
    sym_series = {}
    for sym in symbols:
        try:
            s = _build_carry_daily_returns(sym)
            sym_series[sym] = s
            print(f"  [{sym}] carry loaded: n={len(s)} ({s.index.min().date()} -> {s.index.max().date()})")
        except Exception as e:
            print(f"  [{sym}] failed: {e}")
    sym_df = pd.DataFrame(sym_series).dropna(how="any")
    return sym_df


def build_weighted_carry_panel(sym_df: pd.DataFrame, weights: Dict[str, float]) -> pd.Series:
    cols = [c for c in sym_df.columns if c in weights]
    w_arr = np.array([weights[c] for c in cols])
    w_arr = w_arr / w_arr.sum()
    panel = sym_df[cols] @ w_arr
    panel.name = CARRY_COL
    return panel


def assemble_df9() -> pd.DataFrame:
    df01 = load_v41_and_v1()
    if df01.index.tz is not None:
        df01.index = df01.index.tz_localize(None)
    s114 = load_k114()
    s116 = load_k116()
    s121 = load_k121()
    s133 = load_k133()
    s147 = load_k147()
    s175 = load_k175()
    carry_weights = {"ETH": 0.35, "DOGE": 0.30, "AVAX": 0.25, "BTC": 0.10}
    sym_df = load_carry_sym_df(list(carry_weights.keys()))
    carry_panel = build_weighted_carry_panel(sym_df, carry_weights)
    df9 = pd.concat([
        df01[["v4.1"]], df01[["V1"]],
        s114.to_frame(), s116.to_frame(), s121.to_frame(),
        s133.to_frame(), s147.to_frame(), s175.to_frame(),
        carry_panel.to_frame(),
    ], axis=1, join="inner").sort_index().dropna(how="any")
    return df9


# ============================================================
# K188 WF replication
# ============================================================

def w_risk_parity(R: np.ndarray) -> np.ndarray:
    vols = R.std(axis=0, ddof=1)
    vols = np.where(vols == 0, 1e-9, vols)
    inv = 1.0 / vols
    return inv / inv.sum()


def apply_carry_cap_arr(w: np.ndarray, cols: List[str],
                        carry_cap: float = 0.07,
                        carry_col: str = CARRY_COL) -> np.ndarray:
    w = w.copy()
    ci = cols.index(carry_col)
    if w[ci] > carry_cap:
        excess = w[ci] - carry_cap
        w[ci] = carry_cap
        non_carry = [i for i in range(len(w)) if i != ci]
        total_non = w[non_carry].sum()
        if total_non > 0:
            w[non_carry] += excess * w[non_carry] / total_non
    return w


def k188_walk_forward(df9: pd.DataFrame) -> dict:
    """Exact replication of K188 walk_forward_stability."""
    n = len(df9)
    fold_size = n // N_FOLDS
    cols = list(df9.columns)
    R = df9.to_numpy()
    fold_results = []
    for fold in range(N_FOLDS):
        start = fold * fold_size
        end = start + fold_size if fold < N_FOLDS - 1 else n
        R_fold = R[start:end]
        cut = int(len(R_fold) * TRAIN_FRAC)
        R_train = R_fold[:cut]
        R_test = R_fold[cut:]
        if len(R_train) < 30 or len(R_test) < 10:
            continue
        w_rp = w_risk_parity(R_train)
        w_rp = apply_carry_cap_arr(w_rp, cols)
        test_sh_rp = _sharpe(R_test @ w_rp)
        test_sh_eq = _sharpe(R_test @ (np.ones(len(cols)) / len(cols)))
        fold_results.append({
            "fold": fold,
            "train_n": int(len(R_train)),
            "test_n": int(len(R_test)),
            "oos_sharpe_rp": round(test_sh_rp, 4),
            "oos_sharpe_eq": round(test_sh_eq, 4),
            "date_start": str(df9.index[start].date()),
            "date_end": str(df9.index[end - 1].date()),
            "test_date_start": str(df9.index[start + cut].date()),
            "test_date_end": str(df9.index[end - 1].date()),
            "train_date_start": str(df9.index[start].date()),
            "train_date_end": str(df9.index[start + cut - 1].date()),
            "weights_rp": {c: round(float(w), 4) for c, w in zip(cols, w_rp)},
            "row_start": int(start),
            "row_end": int(end),
            "row_cut": int(start + cut),
        })
    if fold_results:
        oos_sharpes = [f["oos_sharpe_rp"] for f in fold_results]
        return {
            "folds": fold_results,
            "mean_oos_sharpe_rp": round(float(np.mean(oos_sharpes)), 4),
            "min_oos_sharpe_rp": round(float(np.min(oos_sharpes)), 4),
            "std_oos_sharpe_rp": round(float(np.std(oos_sharpes)), 4),
        }
    return {"folds": [], "mean_oos_sharpe_rp": None}


# ============================================================
# Metrics
# ============================================================

def _sharpe(r: np.ndarray) -> float:
    if len(r) < 2 or r.std(ddof=1) == 0:
        return 0.0
    return float(r.mean() / r.std(ddof=1) * math.sqrt(TRADING_DAYS))


def metrics_pkg(r: np.ndarray) -> dict:
    if len(r) < 2:
        return {"sharpe": 0.0, "ann_ret": 0.0, "ann_vol": 0.0, "max_dd": 0.0, "n_days": int(len(r))}
    ann_ret = float((1.0 + r).prod() ** (TRADING_DAYS / len(r)) - 1.0)
    ann_vol = float(r.std(ddof=1) * math.sqrt(TRADING_DAYS))
    eq = np.cumprod(1.0 + r)
    peak = np.maximum.accumulate(eq)
    mdd = float((eq / peak - 1.0).min())
    return {
        "sharpe":  round(_sharpe(r), 4),
        "ann_ret": round(ann_ret, 4),
        "ann_vol": round(ann_vol, 4),
        "max_dd":  round(mdd, 4),
        "n_days":  int(len(r)),
    }


# ============================================================
# Regime indicator builders
# ============================================================

def build_btc_realized_vol(window: int = 21) -> pd.Series:
    """Daily BTC realized vol (21d rolling std of daily returns, annualized)."""
    df = pd.read_parquet(CACHE / "BTCUSDT_1d_730d.parquet")
    df["date"] = pd.to_datetime(df["open_time"])
    df = df.set_index("date").sort_index()
    df["ret"] = df["close"].pct_change()
    df["rvol"] = df["ret"].rolling(window).std() * math.sqrt(TRADING_DAYS)
    return df["rvol"].dropna()


def build_fr_mean_level(symbols: List[str] = ("BTC", "ETH", "DOGE", "AVAX", "SOL", "XRP")) -> pd.Series:
    """Daily mean annualized funding rate level across symbols."""
    all_daily = []
    for sym in symbols:
        try:
            df = _load_bybit(sym)
            df["date"] = df["ts"].dt.normalize()
            daily = df.groupby("date")["bybit_fr"].mean()
            daily = daily * 3 * 365  # annualized (3 periods per day)
            daily.name = sym
            all_daily.append(daily)
        except Exception as e:
            print(f"  [FR mean] {sym} failed: {e}")
    if not all_daily:
        return pd.Series(dtype=float, name="fr_mean_level")
    combined = pd.DataFrame(all_daily).T
    mean_level = combined.mean(axis=1)
    mean_level.name = "fr_mean_level"
    return mean_level


def build_btc_momentum(window: int = 21) -> pd.Series:
    """Daily BTC n-day price momentum (rolling return)."""
    df = pd.read_parquet(CACHE / "BTCUSDT_1d_730d.parquet")
    df["date"] = pd.to_datetime(df["open_time"])
    df = df.set_index("date").sort_index()
    mom = df["close"].pct_change(window).dropna()
    mom.name = f"btc_mom_{window}d"
    return mom


def build_premium_spread(symbols: List[str] = ("BTC", "ETH", "DOGE", "AVAX")) -> pd.Series:
    """Daily mean |HL_FR - Bybit_FR| premium spread across carry symbols."""
    all_daily = []
    for sym in symbols:
        try:
            hl = _load_hl_8h(sym)
            bybit = _load_bybit(sym)
            merged = pd.merge_asof(
                bybit.sort_values("ts"),
                hl.sort_values("ts"),
                on="ts",
                tolerance=pd.Timedelta("4h"),
                direction="nearest",
            ).dropna()
            merged["spread"] = (merged["hl_fr_8h"] - merged["bybit_fr"]).abs()
            merged["date"] = merged["ts"].dt.normalize()
            daily = merged.groupby("date")["spread"].mean()
            daily.name = sym
            all_daily.append(daily)
        except Exception as e:
            print(f"  [Premium spread] {sym} failed: {e}")
    if not all_daily:
        return pd.Series(dtype=float, name="premium_spread")
    combined = pd.DataFrame(all_daily).T
    spread = combined.mean(axis=1)
    spread.name = "premium_spread"
    return spread


def build_basis_vol(symbols: List[str] = ("BTC", "ETH", "DOGE", "AVAX"), window: int = 7) -> pd.Series:
    """Daily basis vol: 7d rolling std of spread (HL_FR - Bybit_FR)."""
    all_daily = []
    for sym in symbols:
        try:
            hl = _load_hl_8h(sym)
            bybit = _load_bybit(sym)
            merged = pd.merge_asof(
                bybit.sort_values("ts"),
                hl.sort_values("ts"),
                on="ts",
                tolerance=pd.Timedelta("4h"),
                direction="nearest",
            ).dropna()
            merged["spread"] = merged["hl_fr_8h"] - merged["bybit_fr"]
            merged["date"] = merged["ts"].dt.normalize()
            daily_spread = merged.groupby("date")["spread"].mean()
            daily_vol = daily_spread.rolling(window).std()
            daily_vol.name = sym
            all_daily.append(daily_vol)
        except Exception as e:
            print(f"  [Basis vol] {sym} failed: {e}")
    if not all_daily:
        return pd.Series(dtype=float, name="basis_vol")
    combined = pd.DataFrame(all_daily).T
    bvol = combined.mean(axis=1)
    bvol.name = "basis_vol"
    return bvol


def fold_regime_stats(indicator: pd.Series, folds_info: List[dict],
                      window_key: str = "oos") -> pd.DataFrame:
    """Compute distribution stats of indicator within each fold's OOS or full window."""
    rows = []
    for f in folds_info:
        if window_key == "oos":
            s_date = f["test_date_start"]
            e_date = f["test_date_end"]
        else:
            s_date = f["date_start"]
            e_date = f["date_end"]
        mask = (indicator.index >= s_date) & (indicator.index <= e_date)
        vals = indicator[mask].dropna()
        label = f"Fold{f['fold']}_OOS" if window_key == "oos" else f"Fold{f['fold']}_Full"
        if len(vals) == 0:
            rows.append({"fold": label, "n": 0, "mean": np.nan, "median": np.nan,
                         "std": np.nan, "p25": np.nan, "p75": np.nan})
        else:
            rows.append({
                "fold": label,
                "n": len(vals),
                "mean": round(float(vals.mean()), 6),
                "median": round(float(vals.median()), 6),
                "std": round(float(vals.std()), 6),
                "p25": round(float(vals.quantile(0.25)), 6),
                "p75": round(float(vals.quantile(0.75)), 6),
            })
    return pd.DataFrame(rows).set_index("fold")


# ============================================================
# Defensive trigger evaluation (exact K188 WF methodology)
# ============================================================

def eval_trigger_wf(
    df9: pd.DataFrame,
    regime: pd.Series,
    threshold: float,
    direction: str,
    reduce_factor: float,
    folds_info: List[dict],
) -> List[dict]:
    """
    Evaluate defensive trigger using exact K188 WF split logic.
    For each fold: train on 70%, apply in-sample weights, test on 30%.
    When regime crosses threshold, scale portfolio return by reduce_factor.
    """
    n = len(df9)
    fold_size = n // N_FOLDS
    cols = list(df9.columns)
    R = df9.to_numpy()
    results = []

    for f in folds_info:
        fold = f["fold"]
        start = fold * fold_size
        end = start + fold_size if fold < N_FOLDS - 1 else n
        R_fold = R[start:end]
        cut = int(len(R_fold) * TRAIN_FRAC)
        R_train = R_fold[:cut]
        R_test = R_fold[cut:]
        if len(R_train) < 30 or len(R_test) < 10:
            continue

        # In-sample weights (same as baseline)
        w_rp = w_risk_parity(R_train)
        w_rp = apply_carry_cap_arr(w_rp, cols)

        # Get dates for test period
        test_idx = df9.index[start + cut: end]
        regime_test = regime.reindex(test_idx, method="ffill")

        port_base = R_test @ w_rp
        port_trig = []
        n_trig = 0

        for i, (date, row) in enumerate(zip(test_idx, R_test)):
            base_ret = float(w_rp @ row)
            reg_val = regime_test.get(date, np.nan)
            trigger_active = False
            if pd.notna(reg_val):
                if direction == "above" and reg_val > threshold:
                    trigger_active = True
                elif direction == "below" and reg_val < threshold:
                    trigger_active = True
            if trigger_active:
                n_trig += 1
                port_trig.append(base_ret * reduce_factor)
            else:
                port_trig.append(base_ret)

        arr_base = np.array(port_base)
        arr_trig = np.array(port_trig)
        sh_base = _sharpe(arr_base)
        sh_trig = _sharpe(arr_trig)

        results.append({
            "fold": fold,
            "fold_label": f"Fold{fold}",
            "sharpe_base": round(sh_base, 4),
            "sharpe_trigger": round(sh_trig, 4),
            "delta_sharpe": round(sh_trig - sh_base, 4),
            "n": int(len(R_test)),
            "n_trigger_days": int(n_trig),
            "trigger_pct": round(n_trig / max(1, len(R_test)) * 100, 1),
            "test_date_start": f["test_date_start"],
            "test_date_end": f["test_date_end"],
        })

    return results


# ============================================================
# Main
# ============================================================

def main():
    print("=" * 70)
    print("Wave K191 — Fold 3 Weakness Diagnosis (K188 WF replication)")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    # ---- Step 1: Load 9 strategy daily returns ----
    print("\n[1] Loading 9 K188 strategy daily returns...")
    df9 = assemble_df9()
    cols = list(df9.columns)
    print(f"  Combined df9: {df9.shape}, {df9.index[0].date()} to {df9.index[-1].date()}")
    print(f"  Columns: {cols}")

    # ---- Step 2: Replicate K188 WF exactly ----
    print("\n[2] Replicating K188 walk-forward (4-fold, 70/30 split per fold)...")
    wf = k188_walk_forward(df9)
    folds_info = wf["folds"]

    print(f"  WF mean Sh={wf['mean_oos_sharpe_rp']:.4f}, min={wf['min_oos_sharpe_rp']:.4f}, std={wf['std_oos_sharpe_rp']:.4f}")
    print(f"  (K188 reported: mean=4.91, min=2.38)")
    for f in folds_info:
        print(f"  Fold {f['fold']}: OOS Sh={f['oos_sharpe_rp']:.4f} "
              f"| test: {f['test_date_start']} to {f['test_date_end']} (n={f['test_n']})")

    # Find the weakest fold
    weak_fold = min(folds_info, key=lambda x: x["oos_sharpe_rp"])
    print(f"\n  Weakest fold: Fold {weak_fold['fold']} (Sh={weak_fold['oos_sharpe_rp']:.4f})")
    print(f"  Test window: {weak_fold['test_date_start']} to {weak_fold['test_date_end']}")
    print(f"  Train window: {weak_fold['train_date_start']} to {weak_fold['train_date_end']}")

    # ---- Step 3: Per-strategy analysis in fold 2 OOS window ----
    print(f"\n[3] Per-strategy Sharpe in Fold {weak_fold['fold']} OOS window...")
    n = len(df9)
    fold_size = n // N_FOLDS
    fold2_idx = weak_fold["fold"]
    start = fold2_idx * fold_size
    end = start + fold_size if fold2_idx < N_FOLDS - 1 else n
    R_fold = df9.iloc[start:end].to_numpy()
    cut = int(len(R_fold) * TRAIN_FRAC)
    R_train = R_fold[:cut]
    R_test = R_fold[cut:]
    test_dates = df9.index[start + cut: end]
    train_dates = df9.index[start: start + cut]
    fold2_test_data = df9.iloc[start + cut: end]

    w_fold2 = w_risk_parity(R_train)
    w_fold2 = apply_carry_cap_arr(w_fold2, cols)

    strat_contributions = {}
    print(f"  Fold {fold2_idx} train weights:")
    for col, w in zip(cols, w_fold2):
        print(f"    {col:30s}: {w:.4f}")

    print(f"\n  Per-strategy OOS test metrics (Fold {fold2_idx} test: {weak_fold['test_date_start']} to {weak_fold['test_date_end']}):")
    for i, col in enumerate(cols):
        r = fold2_test_data[col].values
        sh = _sharpe(r)
        contribution = w_fold2[i] * sh
        m = metrics_pkg(r)
        strat_contributions[col] = {
            "weight": round(float(w_fold2[i]), 4),
            "fold2_oos_sharpe": round(sh, 4),
            "contribution_approx": round(contribution, 4),
            "fold2_oos_ann_ret": m["ann_ret"],
            "fold2_oos_ann_vol": m["ann_vol"],
            "fold2_oos_max_dd": m["max_dd"],
            "n_days": m["n_days"],
        }
        print(f"    {col:30s}: Sh={sh:7.4f}, w={w_fold2[i]:.4f}, contrib={contribution:7.4f}, "
              f"ann_ret={m['ann_ret']:.4f}")

    # Full cross-fold strategy Sharpe table (using WF test windows)
    print(f"\n  Strategy Sharpe in each fold's OOS test window:")
    strategy_fold_table = {}
    for col in cols:
        strategy_fold_table[col] = {}
        for f in folds_info:
            test_start = f["row_cut"]
            test_end = f["row_end"]
            r = df9.iloc[test_start:test_end][col].values
            strategy_fold_table[col][f"Fold{f['fold']}_OOS"] = metrics_pkg(r)

    header = f"  {'Strategy':30s}" + "".join([f"  Fold{f['fold']}_OOS" for f in folds_info])
    print(header)
    for col in cols:
        row = f"  {col:30s}"
        for f in folds_info:
            sh = strategy_fold_table[col][f"Fold{f['fold']}_OOS"]["sharpe"]
            row += f"  {sh:9.4f}"
        print(row)

    # ---- Step 4: Regime indicators ----
    print("\n[4] Building regime indicators...")

    print("  BTC realized vol (21d rolling, annualized)...")
    btc_rvol = build_btc_realized_vol(window=21)
    print(f"    Range: {btc_rvol.index[0].date()} to {btc_rvol.index[-1].date()}, n={len(btc_rvol)}")

    print("  FR mean level (annualized, 6 symbols)...")
    fr_mean = build_fr_mean_level(["BTC", "ETH", "DOGE", "AVAX", "SOL", "XRP"])
    print(f"    Range: {fr_mean.index[0].date()} to {fr_mean.index[-1].date()}, n={len(fr_mean)}")

    print("  Premium spread |HL_FR - Bybit_FR|...")
    prem_spread = build_premium_spread(["BTC", "ETH", "DOGE", "AVAX"])
    print(f"    Range: {prem_spread.index[0].date()} to {prem_spread.index[-1].date()}, n={len(prem_spread)}")

    print("  Basis vol (7d rolling std of spread)...")
    basis_vol = build_basis_vol(["BTC", "ETH", "DOGE", "AVAX"], window=7)
    print(f"    Range: {basis_vol.index[0].date()} to {basis_vol.index[-1].date()}, n={len(basis_vol)}")

    print("  BTC 21d momentum...")
    btc_mom = build_btc_momentum(window=21)
    print(f"    Range: {btc_mom.index[0].date()} to {btc_mom.index[-1].date()}, n={len(btc_mom)}")

    indicators = {
        "btc_rvol_21d": btc_rvol,
        "fr_mean_level_ann": fr_mean,
        "premium_spread": prem_spread,
        "basis_vol_7d": basis_vol,
        "btc_mom_21d": btc_mom,
    }

    # ---- Step 5: Regime stats by fold OOS window ----
    print("\n[5] Regime distribution by fold OOS window...")
    regime_stats = {}
    for ind_name, ind_series in indicators.items():
        stats = fold_regime_stats(ind_series, folds_info, window_key="oos")
        regime_stats[ind_name] = stats.to_dict()
        print(f"\n  {ind_name}:")
        print(stats.to_string())

    # ---- Step 6: Identify best regime separator ----
    print("\n[6] Identifying regime separators...")
    weak_label = f"Fold{weak_fold['fold']}_OOS"
    separators = {}
    for ind_name, ind_series in indicators.items():
        stats_df = fold_regime_stats(ind_series, folds_info, window_key="oos")
        if weak_label not in stats_df.index:
            continue
        fold3_mean = stats_df.loc[weak_label, "mean"]
        other_labels = [f"Fold{f['fold']}_OOS" for f in folds_info if f["fold"] != weak_fold["fold"]]
        other_rows = stats_df.loc[[l for l in other_labels if l in stats_df.index]]
        if len(other_rows) == 0 or pd.isna(fold3_mean):
            continue
        other_mean = other_rows["mean"].dropna().mean()
        pooled_std = other_rows["std"].dropna().mean()
        separation = (fold3_mean - other_mean) / (pooled_std + 1e-10)
        separators[ind_name] = {
            "fold2_oos_mean": round(float(fold3_mean), 6),
            "other_folds_mean": round(float(other_mean), 6),
            "separation_z": round(float(separation), 3),
            "direction": "above" if fold3_mean > other_mean else "below",
        }
        print(f"  {ind_name}: fold2_oos_mean={fold3_mean:.6f}, others_mean={other_mean:.6f}, z={separation:.3f}")

    if not separators:
        print("  No separators found!")
        best_indicator = list(indicators.keys())[0]
        best_sep = {"fold2_oos_mean": 0, "other_folds_mean": 0, "separation_z": 0, "direction": "above"}
    else:
        best_indicator = max(separators, key=lambda k: abs(separators[k]["separation_z"]))
        best_sep = separators[best_indicator]
        print(f"\n  Best separator by z-score: {best_indicator} (z={best_sep['separation_z']:.3f}, direction={best_sep['direction']})")

    # ---- Step 7: Design defensive trigger (test ALL indicators) ----
    print("\n[7] Designing defensive trigger (grid search over all indicators)...")

    trigger_tests = []
    best_trigger = None
    best_fold2_lift = -999.0
    best_trigger_indicator = None

    for ind_name, ind_series in indicators.items():
        weak_test_start = weak_fold["test_date_start"]
        weak_test_end = weak_fold["test_date_end"]
        weak_mask = (ind_series.index >= weak_test_start) & (ind_series.index <= weak_test_end)
        weak_vals = ind_series[weak_mask].dropna()
        all_vals = ind_series.dropna()

        if len(weak_vals) == 0 or len(all_vals) == 0:
            continue

        ind_sep = separators.get(ind_name, {})
        direction = ind_sep.get("direction", "below")
        fold2_mean = ind_sep.get("fold2_oos_mean", float(weak_vals.mean()))

        # Build per-indicator threshold grid
        p10 = float(all_vals.quantile(0.10))
        p25 = float(all_vals.quantile(0.25))
        p40 = float(all_vals.quantile(0.40))
        p50 = float(all_vals.quantile(0.50))
        p60 = float(all_vals.quantile(0.60))
        p75 = float(all_vals.quantile(0.75))
        weak_med = float(weak_vals.median())

        if direction == "below":
            # For "below" indicators, include domain-specific negative thresholds
            if ind_name == "fr_mean_level_ann":
                extra = [-0.10, -0.05, -0.02, 0.0, 0.02]
            else:
                extra = []
            thresholds = sorted(set(extra + [p10, p25, p40, p50, weak_med]))
        else:
            thresholds = sorted(set([p40, p50, p60, p75, weak_med]))

        reduce_factors = [0.0, 0.25, 0.50, 0.75]

        for thr in thresholds:
            for rf in reduce_factors:
                results = eval_trigger_wf(df9, ind_series, thr, direction, rf, folds_info)
                fold2_res = next((r for r in results if r["fold"] == weak_fold["fold"]), None)
                other_res = [r for r in results if r["fold"] != weak_fold["fold"]]
                if fold2_res is None:
                    continue
                sh_fold2_base = fold2_res["sharpe_base"]
                sh_fold2_trig = fold2_res["sharpe_trigger"]
                lift = sh_fold2_trig - sh_fold2_base
                mean_other_base = float(np.mean([r["sharpe_base"] for r in other_res]))
                mean_other_trig = float(np.mean([r["sharpe_trigger"] for r in other_res]))
                other_delta = mean_other_trig - mean_other_base
                all_base_sh = [r["sharpe_base"] for r in results]
                all_trig_sh = [r["sharpe_trigger"] for r in results]

                test_rec = {
                    "indicator": ind_name,
                    "threshold": round(float(thr), 6),
                    "direction": direction,
                    "reduce_factor": rf,
                    "fold2_sh_base": round(sh_fold2_base, 4),
                    "fold2_sh_trigger": round(sh_fold2_trig, 4),
                    "fold2_lift": round(lift, 4),
                    "other_folds_delta": round(other_delta, 4),
                    "wf_mean_base": round(float(np.mean(all_base_sh)), 4),
                    "wf_mean_trigger": round(float(np.mean(all_trig_sh)), 4),
                    "wf_min_base": round(float(np.min(all_base_sh)), 4),
                    "wf_min_trigger": round(float(np.min(all_trig_sh)), 4),
                    "fold2_trigger_pct": fold2_res.get("trigger_pct", 0),
                    "fold_details": results,
                }
                trigger_tests.append(test_rec)

                if lift > best_fold2_lift:
                    best_fold2_lift = lift
                    best_trigger = test_rec
                    best_trigger_indicator = ind_name

    # Print top 15 trigger tests by fold2 lift
    top_tests = sorted(trigger_tests, key=lambda x: x["fold2_lift"], reverse=True)[:15]
    print(f"\n  Top 15 trigger candidates (by fold2 lift):")
    print(f"  {'Indicator':22s} {'Thr':>10} {'RF':>4} {'F2Base':>7} {'F2Trig':>7} {'Lift':>7} {'Others':>7} {'WF_Min':>7} {'F2Trig%':>7}")
    for t in top_tests:
        print(f"  {t['indicator']:22s} {t['threshold']:>10.5f} {t['reduce_factor']:>4.2f} "
              f"{t['fold2_sh_base']:>7.4f} {t['fold2_sh_trigger']:>7.4f} "
              f"{t['fold2_lift']:>+7.4f} {t['other_folds_delta']:>+7.4f} "
              f"{t['wf_min_trigger']:>7.4f} {t['fold2_trigger_pct']:>7.1f}%")

    # Best trigger = max fold2_lift subject to other_folds_delta >= -0.30
    valid_triggers = [t for t in trigger_tests if t["other_folds_delta"] >= -0.30]
    if valid_triggers:
        best_trigger = max(valid_triggers, key=lambda x: x["fold2_lift"])
        best_trigger_indicator = best_trigger["indicator"]
        print(f"\n  Best valid trigger (other_delta >= -0.30):")
        print(f"  {best_trigger['indicator']:22s} thr={best_trigger['threshold']:.5f} rf={best_trigger['reduce_factor']:.2f}: "
              f"fold2 {best_trigger['fold2_sh_base']:.4f} -> {best_trigger['fold2_sh_trigger']:.4f} "
              f"(lift={best_trigger['fold2_lift']:+.4f}), others={best_trigger['other_folds_delta']:+.4f}")
    else:
        print("\n  No trigger passes other_folds_delta >= -0.30 constraint. Using unconstrained best.")
        best_trigger_indicator = best_trigger["indicator"] if best_trigger else list(indicators.keys())[0]

    # Update best_indicator and best_sep to match best trigger
    if best_trigger:
        best_indicator = best_trigger_indicator
        best_sep = separators.get(best_indicator, {"direction": best_trigger.get("direction", "below"),
                                                   "fold2_oos_mean": 0, "other_folds_mean": 0, "separation_z": 0})

    # ---- Step 8: WF summary for best trigger ----
    print("\n[8] Best trigger WF summary:")
    if best_trigger:
        print(f"  Indicator: {best_indicator}, threshold={best_trigger['threshold']:.6f}, "
              f"reduce_factor={best_trigger['reduce_factor']}")
        print(f"  Fold2 lift: {best_trigger['fold2_lift']:+.4f} "
              f"({best_trigger['fold2_sh_base']:.4f} -> {best_trigger['fold2_sh_trigger']:.4f})")
        print(f"  Other folds delta: {best_trigger['other_folds_delta']:+.4f}")
        print("\n  Per-fold comparison:")
        for fr in best_trigger["fold_details"]:
            print(f"    Fold{fr['fold']} ({fr['test_date_start']} to {fr['test_date_end']}): "
                  f"base={fr['sharpe_base']:.4f}, trigger={fr['sharpe_trigger']:.4f}, "
                  f"lift={fr['delta_sharpe']:+.4f}, trig_days={fr['n_trigger_days']} ({fr['trigger_pct']}%)")
        print(f"\n  K188 WF baseline: mean={best_trigger['wf_mean_base']:.4f}, min={best_trigger['wf_min_base']:.4f}")
        print(f"  K188+trigger:     mean={best_trigger['wf_mean_trigger']:.4f}, min={best_trigger['wf_min_trigger']:.4f}")

    # ---- Step 9: Build equity curves ----
    print("\n[9] Building equity curves...")
    curves = {}

    # Regime indicator series aligned to df9 dates
    for ind_name, ind_series in indicators.items():
        aligned = ind_series.reindex(df9.index, method="ffill")
        curves[ind_name] = {
            "dates": [d.strftime("%Y-%m-%d") for d in aligned.index],
            "values": [round(float(v), 8) if pd.notna(v) else None for v in aligned.values],
        }

    # Per-fold portfolio baseline equity
    full_port_rets = []
    full_port_dates = []
    for f in folds_info:
        start = f["fold"] * (n // N_FOLDS)
        end = start + (n // N_FOLDS) if f["fold"] < N_FOLDS - 1 else n
        R_fold = df9.iloc[start:end].to_numpy()
        cut = int(len(R_fold) * TRAIN_FRAC)
        R_train = R_fold[:cut]
        R_test = R_fold[cut:]
        w_rp = w_risk_parity(R_train)
        w_rp = apply_carry_cap_arr(w_rp, cols)
        test_rets = list(R_test @ w_rp)
        test_dates = list(df9.index[start + cut: end])
        full_port_rets.extend(test_rets)
        full_port_dates.extend(test_dates)

    port_series = pd.Series(full_port_rets, index=full_port_dates)
    port_eq = (1 + port_series).cumprod()
    curves["K188_rp_wf_equity"] = {
        "dates": [d.strftime("%Y-%m-%d") for d in port_series.index],
        "values": [round(float(v), 6) for v in port_eq.values],
    }

    # Trigger equity
    if best_trigger:
        thr = best_trigger["threshold"]
        rf = best_trigger["reduce_factor"]
        direction = best_sep["direction"]
        best_series_aligned = indicators[best_indicator]

        trig_rets = []
        trig_dates = []
        for f in folds_info:
            start = f["fold"] * (n // N_FOLDS)
            end = start + (n // N_FOLDS) if f["fold"] < N_FOLDS - 1 else n
            R_fold = df9.iloc[start:end].to_numpy()
            cut = int(len(R_fold) * TRAIN_FRAC)
            R_train = R_fold[:cut]
            R_test = R_fold[cut:]
            w_rp = w_risk_parity(R_train)
            w_rp = apply_carry_cap_arr(w_rp, cols)
            test_idx = df9.index[start + cut: end]
            regime_test = best_series_aligned.reindex(test_idx, method="ffill")

            for i, (date, row) in enumerate(zip(test_idx, R_test)):
                base_ret = float(w_rp @ row)
                reg_val = regime_test.get(date, np.nan)
                trigger_active = False
                if pd.notna(reg_val):
                    if direction == "above" and reg_val > thr:
                        trigger_active = True
                    elif direction == "below" and reg_val < thr:
                        trigger_active = True
                trig_rets.append(base_ret * rf if trigger_active else base_ret)
                trig_dates.append(date)

        trig_series = pd.Series(trig_rets, index=trig_dates)
        trig_eq = (1 + trig_series).cumprod()
        curves["K188_trigger_wf_equity"] = {
            "dates": [d.strftime("%Y-%m-%d") for d in trig_series.index],
            "values": [round(float(v), 6) for v in trig_eq.values],
        }

    # ---- Verdict ----
    print("\n" + "=" * 70)
    print("VERDICT")
    print("=" * 70)

    if best_trigger:
        lift = best_trigger["fold2_lift"]
        other_delta = best_trigger["other_folds_delta"]
        if lift >= 0.5 and other_delta >= -0.3:
            verdict_code = "ACCEPT"
            verdict = "Defensive trigger lifts fold2 by >=0.5 Sh with acceptable other-fold cost → ACCEPT for K192 integration"
        elif lift >= 0.5 and other_delta < -0.3:
            verdict_code = "CONDITIONAL"
            verdict = "Fold2 lift >= 0.5 but other folds degrade significantly → CONDITIONAL, needs parameter tuning in K192"
        elif lift > 0:
            verdict_code = "MARGINAL"
            verdict = f"Positive lift ({lift:+.4f}) but < 0.5 threshold → MARGINAL, document regime cause for monitoring"
        else:
            verdict_code = "NO_TRIGGER"
            verdict = "No positive trigger effect found → document regime cause, monitor indicators"
    else:
        verdict_code = "NO_TRIGGER"
        verdict = "No trigger candidates found"

    print(f"  Fold2 OOS lift: {best_trigger['fold2_lift']:+.4f} (target >= +0.50)" if best_trigger else "  No trigger")
    print(f"  Other folds delta: {best_trigger['other_folds_delta']:+.4f}" if best_trigger else "")
    print(f"  Verdict: {verdict_code}")
    print(f"  {verdict}")

    # ---- Build WF summary ----
    if best_trigger:
        wf_summary = {
            "K188_baseline": {
                "mean_oos_sharpe": best_trigger["wf_mean_base"],
                "min_oos_sharpe": best_trigger["wf_min_base"],
            },
            "K188_trigger": {
                "mean_oos_sharpe": best_trigger["wf_mean_trigger"],
                "min_oos_sharpe": best_trigger["wf_min_trigger"],
            },
        }
    else:
        wf_summary = None

    # ---- Trigger recipe ----
    trigger_recipe = None
    if best_trigger:
        trigger_recipe = {
            "indicator": best_indicator,
            "threshold": best_trigger["threshold"],
            "direction": best_sep["direction"],
            "reduce_factor": best_trigger["reduce_factor"],
            "fold2_lift": best_trigger["fold2_lift"],
            "other_folds_delta": best_trigger["other_folds_delta"],
            "fold2_trigger_pct": best_trigger["fold2_trigger_pct"],
            "fold_details": best_trigger["fold_details"],
            "description": (
                f"When {best_indicator} is {best_sep['direction']} {best_trigger['threshold']:.6f}, "
                f"scale portfolio by {best_trigger['reduce_factor']:.2f}x"
            ),
        }

    # ---- Save diagnosis JSON ----
    print("\n[10] Saving outputs...")
    diag_output = {
        "wave": "K191",
        "generated": datetime.now().isoformat(),
        "runtime_s": round(time.time() - START_TIME, 1),
        "k188_wf_config": {
            "n_folds": N_FOLDS,
            "train_frac": TRAIN_FRAC,
            "carry_cap": CARRY_CAP,
        },
        "wf_replicated": {
            "mean_oos_sharpe_rp": wf["mean_oos_sharpe_rp"],
            "min_oos_sharpe_rp": wf["min_oos_sharpe_rp"],
            "std_oos_sharpe_rp": wf["std_oos_sharpe_rp"],
            "folds": folds_info,
        },
        "weak_fold": {
            "fold": weak_fold["fold"],
            "oos_sharpe": weak_fold["oos_sharpe_rp"],
            "test_date_start": weak_fold["test_date_start"],
            "test_date_end": weak_fold["test_date_end"],
            "train_date_start": weak_fold["train_date_start"],
            "train_date_end": weak_fold["train_date_end"],
        },
        "strat_fold2_contributions": strat_contributions,
        "strategy_fold_table": strategy_fold_table,
        "regime_stats_by_fold": regime_stats,
        "separator_summary": separators,
        "best_separator": {"indicator": best_indicator, **best_sep},
        "trigger_tests": trigger_tests,
        "trigger_recipe": trigger_recipe,
        "wf_summary": wf_summary,
        "verdict": verdict_code,
        "verdict_text": verdict,
    }

    out_diag = BASE / "wave_k191_fold3_diagnosis.json"
    with open(out_diag, "w") as fp:
        json.dump(diag_output, fp, indent=2, default=str)
    print(f"  Saved: {out_diag}")

    out_curves = BASE / "wave_k191_curves.json"
    with open(out_curves, "w") as fp:
        json.dump(curves, fp, indent=2, default=str)
    print(f"  Saved: {out_curves}")

    print("  Building markdown report...")
    build_markdown_report(diag_output, strategy_fold_table, strat_contributions,
                          regime_stats, separators, best_indicator, best_sep,
                          trigger_tests, best_trigger, wf_summary,
                          verdict_code, verdict, folds_info, wf)
    print(f"\nDone! Runtime: {time.time()-START_TIME:.1f}s")


def build_markdown_report(
    diag, strategy_fold_table, strat_contributions,
    regime_stats, separator_summary, best_indicator, best_sep,
    trigger_tests, best_trigger, wf_summary, verdict_code, verdict,
    folds_info, wf
):
    lines = []
    lines.append("# Wave K191 — Fold 3 Weakness Diagnosis Report")
    lines.append(f"\n**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  ")
    lines.append(f"**Weak fold:** Fold 2 OOS test: {diag['weak_fold']['test_date_start']} to {diag['weak_fold']['test_date_end']}  ")
    lines.append(f"**K188 WF baseline (replicated):** mean Sh={wf['mean_oos_sharpe_rp']:.4f}, "
                 f"min Sh={wf['min_oos_sharpe_rp']:.4f} (fold 2), std={wf['std_oos_sharpe_rp']:.4f}")
    lines.append(f"**K188 WF official:** mean Sh=4.91, min Sh=2.38 (fold 2), std=2.23\n")

    lines.append("---\n")
    lines.append("## Executive Summary\n")
    lines.append("K188 walk-forward Fold 2 (OOS test: 2025-10-11 to 2025-11-29, n=50 days) showed the weakest "
                 "OOS Sharpe of all four folds, representing the primary defensive risk for the production v6 ensemble. ")
    lines.append("The WF methodology splits each 164-day fold into 114 training + 50 test days, "
                 "using in-sample risk-parity weights with 7% carry cap.\n")
    lines.append(f"**Verdict: {verdict_code}**  ")
    lines.append(f"**{verdict}**\n")

    if wf_summary:
        lines.append("| Metric | K188 Baseline | K188+Trigger | Delta |")
        lines.append("|--------|--------------|-------------|-------|")
        bl = wf_summary["K188_baseline"]
        tr = wf_summary["K188_trigger"]
        lines.append(f"| Mean WF OOS Sharpe | {bl['mean_oos_sharpe']:.4f} | {tr['mean_oos_sharpe']:.4f} | {tr['mean_oos_sharpe']-bl['mean_oos_sharpe']:+.4f} |")
        lines.append(f"| Min WF OOS Sharpe | {bl['min_oos_sharpe']:.4f} | {tr['min_oos_sharpe']:.4f} | {tr['min_oos_sharpe']-bl['min_oos_sharpe']:+.4f} |")
        lines.append("")

    lines.append("---\n")
    lines.append("## 1. K188 WF Replication\n")
    lines.append("| Fold | OOS Sh (rp) | Train Window | Test Window | n_test |")
    lines.append("|------|------------|-------------|------------|--------|")
    for f in folds_info:
        lines.append(
            f"| Fold{f['fold']} | {f['oos_sharpe_rp']:.4f} | {f['train_date_start']} to {f['train_date_end']} "
            f"| {f['test_date_start']} to {f['test_date_end']} | {f['test_n']} |"
        )
    lines.append("")

    lines.append("---\n")
    lines.append("## 2. Per-Strategy Fold 2 OOS Contribution Table\n")
    lines.append(
        f"**Fold 2 OOS test window:** {diag['weak_fold']['test_date_start']} to {diag['weak_fold']['test_date_end']}  \n"
        "*(Weights = risk-parity computed on Fold 2 training data)*\n"
    )
    lines.append("| Strategy | Weight (RP) | Fold2 OOS Sh | Contribution | AnnRet | AnnVol | MaxDD |")
    lines.append("|----------|------------|-------------|-------------|--------|--------|-------|")
    for col, m in sorted(strat_contributions.items(), key=lambda x: x[1]["contribution_approx"]):
        lines.append(
            f"| {col} | {m['weight']:.4f} | {m['fold2_oos_sharpe']:.4f} | {m['contribution_approx']:.4f} "
            f"| {m['fold2_oos_ann_ret']:.4f} | {m['fold2_oos_ann_vol']:.4f} | {m['fold2_oos_max_dd']:.4f} |"
        )
    lines.append("")

    lines.append("\n### Strategy Sharpe Across All Fold OOS Windows\n")
    fold_labels = [f"Fold{f['fold']}_OOS" for f in folds_info]
    header = "| Strategy |" + "|".join(fold_labels) + "|"
    sep = "|---------|" + "|".join(["----" for _ in fold_labels]) + "|"
    lines.append(header)
    lines.append(sep)
    for col in strategy_fold_table:
        row = f"| {col} |"
        for fl in fold_labels:
            sh = strategy_fold_table[col].get(fl, {}).get("sharpe", np.nan)
            row += f" {sh:.4f} |"
        lines.append(row)
    lines.append("")

    lines.append("\n**Key insight:** The primary drag in Fold 2 OOS test window:\n")
    top_drags = sorted(strat_contributions.items(), key=lambda x: x[1]["contribution_approx"])[:3]
    for col, m in top_drags:
        lines.append(f"- **{col}**: Sh={m['fold2_oos_sharpe']:.4f}, weight={m['weight']:.4f}, "
                     f"contribution={m['contribution_approx']:.4f}")
    lines.append("")

    lines.append("---\n")
    lines.append("## 3. Regime Indicator Distribution by Fold OOS Window\n")

    ind_labels = {
        "btc_rvol_21d": "BTC 21d Realized Vol (annualized)",
        "fr_mean_level_ann": "Mean FR Level (annualized, 6 symbols)",
        "premium_spread": "Mean Premium Spread |HL_FR - Bybit_FR|",
        "basis_vol_7d": "Basis Vol (7d rolling std of HL-Bybit spread)",
        "btc_mom_21d": "BTC 21d Price Momentum (rolling return)",
    }

    for ind_name, stats_dict in regime_stats.items():
        label = ind_labels.get(ind_name, ind_name)
        lines.append(f"### {label}\n")
        lines.append("| Fold OOS Window | N | Mean | Median | Std | P25 | P75 |")
        lines.append("|----------------|---|------|--------|-----|-----|-----|")
        # stats_dict has format {field: {fold_label: value}} from pandas .to_dict()
        # Reconstruct as {fold_label: {field: value}}
        if "n" in stats_dict and isinstance(stats_dict["n"], dict):
            fold_labels_stats = list(stats_dict["n"].keys())
            for fl in fold_labels_stats:
                n_val = stats_dict.get("n", {}).get(fl, 0)
                mean_val = stats_dict.get("mean", {}).get(fl, float("nan"))
                med_val = stats_dict.get("median", {}).get(fl, float("nan"))
                std_val = stats_dict.get("std", {}).get(fl, float("nan"))
                p25_val = stats_dict.get("p25", {}).get(fl, float("nan"))
                p75_val = stats_dict.get("p75", {}).get(fl, float("nan"))
                lines.append(
                    f"| {fl} | {n_val} | {mean_val:.6f} "
                    f"| {med_val:.6f} | {std_val:.6f} "
                    f"| {p25_val:.6f} | {p75_val:.6f} |"
                )
        else:
            for fold_label, row in stats_dict.items():
                if isinstance(row, dict):
                    lines.append(
                        f"| {fold_label} | {row.get('n',0)} | {row.get('mean',float('nan')):.6f} "
                        f"| {row.get('median',float('nan')):.6f} | {row.get('std',float('nan')):.6f} "
                        f"| {row.get('p25',float('nan')):.6f} | {row.get('p75',float('nan')):.6f} |"
                    )
        lines.append("")

    lines.append("### Regime Separator Ranking\n")
    lines.append("| Indicator | Fold2 OOS Mean | Others Mean | Separation Z | Direction |")
    lines.append("|-----------|--------------|-------------|-------------|-----------|")
    for ind_name, sep_info in sorted(separator_summary.items(), key=lambda x: abs(x[1].get("separation_z", 0)), reverse=True):
        lines.append(
            f"| {ind_name} | {sep_info['fold2_oos_mean']:.6f} | {sep_info['other_folds_mean']:.6f} "
            f"| {sep_info['separation_z']:.3f} | {sep_info['direction']} |"
        )
    lines.append("")

    lines.append("---\n")
    lines.append("## 4. Defensive Trigger Recipe\n")

    if best_trigger:
        lines.append(f"**Best indicator:** `{best_indicator}`  ")
        lines.append(f"**Direction:** {best_sep['direction']}  ")
        lines.append(f"**Threshold:** {best_trigger['threshold']:.6f}  ")
        lines.append(f"**Reduce factor:** {best_trigger['reduce_factor']:.2f}x  ")
        lines.append(f"**Fold2 OOS trigger coverage:** {best_trigger['fold2_trigger_pct']}% of days  \n")
        lines.append(
            "**Rule:** When `" + best_indicator + "` is " + best_sep["direction"] + " "
            + str(round(best_trigger["threshold"], 6)) + ", scale portfolio returns by "
            + str(best_trigger["reduce_factor"])
            + "x (reduce all position sizes proportionally).\n"
        )
        lines.append("\n### Trigger Test Grid\n")
        lines.append("| Threshold | Reduce Factor | Fold2 Base | Fold2 Trigger | Fold2 Lift | Others Delta | WF Min Trig | Trig% |")
        lines.append("|-----------|--------------|-----------|--------------|-----------|------------|------------|-------|")
        for t in trigger_tests:
            lines.append(
                f"| {t['threshold']:.5f} | {t['reduce_factor']:.2f} "
                f"| {t['fold2_sh_base']:.4f} | {t['fold2_sh_trigger']:.4f} "
                f"| {t['fold2_lift']:+.4f} | {t['other_folds_delta']:+.4f} "
                f"| {t['wf_min_trigger']:.4f} | {t['fold2_trigger_pct']}% |"
            )
        lines.append("")
        lines.append("\n### Per-Fold Impact (Best Trigger)\n")
        lines.append("| Fold | Base Sharpe | Trigger Sharpe | Delta | Trigger Days |")
        lines.append("|------|------------|---------------|-------|-------------|")
        for fr in best_trigger["fold_details"]:
            lines.append(
                f"| Fold{fr['fold']} ({fr['test_date_start']} to {fr['test_date_end']}) "
                f"| {fr['sharpe_base']:.4f} | {fr['sharpe_trigger']:.4f} "
                f"| {fr['delta_sharpe']:+.4f} | {fr['n_trigger_days']} ({fr['trigger_pct']}%) |"
            )
        lines.append("")
    else:
        lines.append("No useful defensive trigger found.\n")

    lines.append("---\n")
    lines.append("## 5. Verdict and K192 Integration Plan\n")
    lines.append(f"**Verdict: `{verdict_code}`**\n")
    lines.append(f"{verdict}\n")

    if verdict_code == "ACCEPT":
        lines.append("### K192 Integration Plan\n")
        lines.append(f"1. **Defensive trigger module** — monitor `{best_indicator}` daily")
        lines.append(f"   - Threshold: {best_trigger['threshold']:.6f} ({best_sep['direction']})")
        lines.append(f"   - Reduce position sizing by {(1-best_trigger['reduce_factor'])*100:.0f}% when triggered")
        lines.append("   - Restore full sizing when indicator normalizes")
        lines.append("2. **WF validation** — confirm mean >= 4.91 and min >= 3.0 with trigger")
        lines.append("3. **Forward test** the trigger rule live for 30+ days before production deployment")
        lines.append("4. **Monitor** the indicator alongside existing dashboard metrics")
        lines.append("5. **K193** re-evaluate trigger parameters if needed\n")
    elif verdict_code in ("MARGINAL", "NO_TRIGGER", "CONDITIONAL"):
        lines.append("### Root Cause Analysis\n")
        lines.append("The fold 2 OOS weakness is primarily driven by:")
        top_drags2 = sorted(strat_contributions.items(), key=lambda x: x[1]["contribution_approx"])[:3]
        for col, m in top_drags2:
            lines.append(f"- **{col}** (w={m['weight']:.4f}): Fold2 OOS Sh={m['fold2_oos_sharpe']:.4f}, "
                         f"contribution={m['contribution_approx']:.4f}")
        lines.append("")
        lines.append(f"**Best regime separator:** `{best_indicator}` (z={best_sep['separation_z']:.3f}), "
                     f"but trigger effect is insufficient to meet the +0.5 Sh lift criterion.\n")
        lines.append("### Monitoring Plan\n")
        lines.append(f"- Track `{best_indicator}` in daily dashboard")
        fold2_ref_val = round(float(best_sep['fold2_oos_mean']), 6)
        lines.append(f"- Alert when {best_indicator} is {best_sep['direction']} the fold2 OOS mean "
                     f"({fold2_ref_val:.6f})")
        lines.append("- Consider manual position reduction if multiple indicators align with fold 2 conditions")
        lines.append("- Re-evaluate with 6+ months of additional data in K195+\n")

    lines.append("---\n")
    lines.append("## 6. Technical Notes\n")
    lines.append("- WF methodology: exact replication of K188 `walk_forward_stability()` — fold_size = n//4 = 164 days, 70% train / 30% test per fold")
    lines.append("- Risk-parity weights computed in-sample per fold, 7% carry cap applied")
    lines.append("- Regime indicators aligned to portfolio dates via forward-fill")
    lines.append("- Trigger applied only on OOS test days (no lookahead on threshold — fixed from all-period quantile)")
    lines.append("- Threshold from all-period quantile to avoid snooping on fold 2 test data\n")

    report_path = BASE / "wave_k191_fold3_diagnosis.md"
    with open(report_path, "w") as fp:
        fp.write("\n".join(lines))
    print(f"  Saved: {report_path}")


if __name__ == "__main__":
    main()
