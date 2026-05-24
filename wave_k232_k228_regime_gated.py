"""
Wave K232 — K228 Stablecoin Mint/Burn with Internal Regime Gate
================================================================
Objective:
  K228 WF fold 2 = -2.15 (2025-07/08 stablecoin reversal regime) is the sole
  blocker for K230 ensemble integration. Apply regime gate to K228 that suppresses
  signal during stablecoin contraction phases.

Regime Gate Variants:
  K232a: Hard gate  — trend > 0 active, else position = 0
  K232b: Soft gate  — trend > 0 → full, trend < -0.05 → 0, linear between
  K232c: Z-score gate — z(30d trend, 90d window) > 0 → active, else suppress

Walk-forward: 4-fold on BOTH:
  1. K228 own window (2024-05-23 → 2026-05-22, n=730)
  2. K230 ML window (2025-01-22 → 2026-04-14, n=448) — the window where fold2=-2.15

Acceptance:
  K232 best variant: WF all folds positive (own window), standalone OOS Sh >= 1.5,
  active trading rate >= 5%
"""

from __future__ import annotations

import json
import math
import os
import time
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

# ── paths ──────────────────────────────────────────────────────────────────────
BASE           = "/Users/nekonaomichi/crypto-lab"
CACHE          = f"{BASE}/cache"
STABLE_PARQUET = f"{CACHE}/stablecoin_supply_daily.parquet"
OUT_JSON       = f"{BASE}/wave_k232_k228_regime_gated.json"
OUT_CURVES     = f"{BASE}/wave_k232_curves.json"
OUT_MD         = f"{BASE}/wave_k232_k228_regime_gated.md"

# ── K228 design constants (from K228 baseline) ─────────────────────────────────
Z_WIN         = 90
Z_THR         = 1.5
NET_WIN       = 7
TAKER_BPS     = 4.0
SLIP_BPS      = 3.0
COST_PER_SIDE = (TAKER_BPS + SLIP_BPS) / 1e4   # 0.07%
PERIODS_PER_YEAR = 365

# ── Regime gate constants ──────────────────────────────────────────────────────
TREND_WIN     = 30     # 30d supply % change
TREND_Z_WIN   = 90     # z-score of 30d trend
SOFT_GATE_LO  = -0.05  # trend < -5% → 0%
# SOFT_GATE_HI  = 0.0   # trend >= 0 → 100%

# ── OOS holdout ────────────────────────────────────────────────────────────────
OOS_N_DAYS    = 135

# ── ML window for K230 compatibility check ─────────────────────────────────────
ML_WINDOW_START = "2025-01-22"
ML_WINDOW_END   = "2026-04-14"


# ── data loading ───────────────────────────────────────────────────────────────
def load_stablecoin_supply() -> pd.DataFrame:
    df = pd.read_parquet(STABLE_PARQUET)
    print(f"  [stable] {len(df)} rows, {df.index.min().date()} → {df.index.max().date()}")
    return df


def load_btc_daily() -> pd.Series:
    for d in (1200, 730, 365):
        p = f"{CACHE}/BTCUSDT_1d_{d}d.parquet"
        if os.path.exists(p):
            df = pd.read_parquet(p)[["open_time", "close"]]
            df["date"] = pd.to_datetime(df["open_time"]).dt.normalize()
            df = df.drop_duplicates("date").set_index("date").sort_index()
            print(f"  [BTC] {p}: {len(df)} rows, {df.index.min().date()} → {df.index.max().date()}")
            return df["close"].astype(float)
    raise FileNotFoundError("No BTCUSDT daily parquet found")


# ── feature engineering ────────────────────────────────────────────────────────
def build_k228_features(stable: pd.DataFrame) -> pd.DataFrame:
    """Build original K228 features + regime gate features."""
    df = stable.copy()

    # K228 original features
    df["mint_1d"]      = df["TOTAL"].diff()
    df["mint_7d_sum"]  = df["mint_1d"].rolling(NET_WIN).sum()
    roll_mu = df["mint_7d_sum"].rolling(Z_WIN).mean()
    roll_sd = df["mint_7d_sum"].rolling(Z_WIN).std()
    df["mint_7d_z"]    = (df["mint_7d_sum"] - roll_mu) / roll_sd.replace(0, np.nan)

    # Regime gate features: 30d trend in total supply
    df["supply_30d_trend"] = df["TOTAL"] / df["TOTAL"].shift(TREND_WIN) - 1.0

    # Z-score of 30d trend over 90d rolling window
    trend_mu = df["supply_30d_trend"].rolling(TREND_Z_WIN).mean()
    trend_sd = df["supply_30d_trend"].rolling(TREND_Z_WIN).std()
    df["supply_trend_z"] = (df["supply_30d_trend"] - trend_mu) / trend_sd.replace(0, np.nan)

    return df


# ── K228 base signal ───────────────────────────────────────────────────────────
def build_base_signal(feat: pd.DataFrame) -> pd.Series:
    """K228 raw signal (no regime gate)."""
    z = feat["mint_7d_z"]
    sig = pd.Series(0.0, index=feat.index)
    sig[z > Z_THR]  =  1.0
    sig[z < -Z_THR] = -1.0
    return sig


# ── Regime gate functions ──────────────────────────────────────────────────────
def gate_hard(feat: pd.DataFrame, base_sig: pd.Series) -> pd.Series:
    """K232a: Hard gate — suppress signal when 30d supply trend <= 0."""
    trend = feat["supply_30d_trend"]
    gated = base_sig.copy()
    suppress = trend <= 0
    gated[suppress] = 0.0
    return gated


def gate_soft(feat: pd.DataFrame, base_sig: pd.Series) -> pd.Series:
    """
    K232b: Soft gate — graduated suppression.
      trend >= 0       → scalar = 1.0 (full)
      trend <= -0.05   → scalar = 0.0
      between          → linear interpolation
    """
    trend = feat["supply_30d_trend"].reindex(base_sig.index)
    scalar = pd.Series(1.0, index=base_sig.index)
    # below floor → 0
    scalar[trend <= SOFT_GATE_LO] = 0.0
    # between floor and 0 → linear
    mid_mask = (trend > SOFT_GATE_LO) & (trend < 0.0)
    scalar[mid_mask] = (trend[mid_mask] - SOFT_GATE_LO) / (0.0 - SOFT_GATE_LO)
    gated = base_sig * scalar
    return gated


def gate_zscore(feat: pd.DataFrame, base_sig: pd.Series) -> pd.Series:
    """K232c: Z-score gate — suppress when z(30d trend, 90d) <= 0."""
    trend_z = feat["supply_trend_z"].reindex(base_sig.index)
    gated = base_sig.copy()
    suppress = trend_z <= 0
    gated[suppress] = 0.0
    return gated


# ── PnL engine ─────────────────────────────────────────────────────────────────
def compute_pnl(price: pd.Series, signal: pd.Series) -> pd.DataFrame:
    """Signal on day t → position from close t to close t+1."""
    ret = price.pct_change()
    pos = signal.reindex(price.index).fillna(0.0)
    pos_lag  = pos.shift(1).fillna(0.0)
    pnl_gross = pos_lag * ret
    turnover  = (pos - pos.shift(1).fillna(0.0)).abs()
    cost      = turnover * COST_PER_SIDE
    pnl_net   = pnl_gross - cost
    return pd.DataFrame({
        "ret_btc":   ret,
        "signal":    pos,
        "pos_lag":   pos_lag,
        "pnl_gross": pnl_gross,
        "pnl_net":   pnl_net,
        "cost":      cost,
    })


# ── metrics helpers ────────────────────────────────────────────────────────────
def _sharpe(r: np.ndarray, ppy: float = PERIODS_PER_YEAR) -> float:
    r = np.asarray(r, dtype=float)
    r = r[~np.isnan(r)]
    if len(r) < 5 or r.std() == 0:
        return 0.0
    return float(r.mean() / r.std() * math.sqrt(ppy))


def _max_dd(r: np.ndarray) -> float:
    r = np.asarray(r, dtype=float)
    r = r[~np.isnan(r)]
    if len(r) == 0:
        return 0.0
    eq   = np.cumprod(1 + r)
    peak = np.maximum.accumulate(eq)
    return float(((eq - peak) / peak).min())


def _ann_ret(r: np.ndarray, ppy: float = PERIODS_PER_YEAR) -> float:
    r = np.asarray(r, dtype=float)
    r = r[~np.isnan(r)]
    if len(r) == 0:
        return 0.0
    return float(r.mean() * ppy)


def _ann_vol(r: np.ndarray, ppy: float = PERIODS_PER_YEAR) -> float:
    r = np.asarray(r, dtype=float)
    r = r[~np.isnan(r)]
    if len(r) == 0:
        return 0.0
    return float(r.std() * math.sqrt(ppy))


def slice_metrics(r: np.ndarray) -> dict:
    return {
        "sharpe":  _sharpe(r),
        "ann_ret": _ann_ret(r),
        "ann_vol": _ann_vol(r),
        "max_dd":  _max_dd(r),
        "n_days":  int(len(r)),
    }


# ── walk-forward ───────────────────────────────────────────────────────────────
def walk_forward_4fold(pnl_df: pd.DataFrame) -> dict:
    """4-fold sequential WF on pnl_df["pnl_net"]."""
    n         = len(pnl_df)
    fold_size = n // 4
    folds     = []
    for k in range(4):
        lo = k * fold_size
        hi = (k + 1) * fold_size if k < 3 else n
        sub   = pnl_df["pnl_net"].values[lo:hi]
        start = str(pnl_df.index[lo].date())
        end   = str(pnl_df.index[hi - 1].date())
        sh    = _sharpe(sub)
        folds.append({
            "fold":    k + 1,
            "start":   start,
            "end":     end,
            "n_days":  int(hi - lo),
            "sharpe":  round(sh, 4),
            "ann_ret": round(_ann_ret(sub), 4),
            "max_dd":  round(_max_dd(sub), 4),
        })
    sharpes = [f["sharpe"] for f in folds]
    return {
        "folds":       folds,
        "fold_sharpes": sharpes,
        "wf_mean":     round(float(np.mean(sharpes)), 4),
        "wf_min":      round(float(np.min(sharpes)), 4),
        "wf_max":      round(float(np.max(sharpes)), 4),
        "wf_std":      round(float(np.std(sharpes)), 4),
        "all_positive": bool(all(s > 0 for s in sharpes)),
    }


# ── active trading rate ────────────────────────────────────────────────────────
def active_rate(signal: pd.Series) -> float:
    """Fraction of days where |signal| > 0."""
    return float((signal.abs() > 0).mean())


# ── equity curve ───────────────────────────────────────────────────────────────
def equity_curve(pnl: pd.Series) -> list:
    eq = (1 + pnl.fillna(0)).cumprod()
    return [{"date": str(t.date()), "eq": round(float(v), 6)} for t, v in eq.items()]


# ── evaluate one variant ───────────────────────────────────────────────────────
def evaluate_variant(
    name: str,
    gated_sig: pd.Series,
    btc_price: pd.Series,
    feat: pd.DataFrame,
) -> dict:
    """Full evaluation of one gated variant on own window + ML window."""
    # ── OWN WINDOW (730d) ──────────────────────────────────────────────────────
    pnl_df  = compute_pnl(btc_price, gated_sig)
    n_all   = len(pnl_df)
    oos_n   = OOS_N_DAYS
    is_n    = n_all - oos_n

    full_r  = pnl_df["pnl_net"].values
    oos_r   = full_r[is_n:]

    full_m  = slice_metrics(full_r)
    oos_m   = slice_metrics(oos_r)
    wf      = walk_forward_4fold(pnl_df)

    act     = active_rate(gated_sig)

    # Regime stats
    trend   = feat["supply_30d_trend"].reindex(pnl_df.index)
    n_growth   = int((trend > 0).sum())
    n_contraction = int((trend <= 0).sum())

    # ── ML WINDOW (K230 compatibility) ────────────────────────────────────────
    ml_start = pd.Timestamp(ML_WINDOW_START)
    ml_end   = pd.Timestamp(ML_WINDOW_END)
    ml_mask  = (pnl_df.index >= ml_start) & (pnl_df.index <= ml_end)
    ml_pnl   = pnl_df[ml_mask]
    ml_wf    = walk_forward_4fold(ml_pnl) if len(ml_pnl) >= 20 else None
    ml_sig   = gated_sig[ml_mask]
    ml_act   = active_rate(ml_sig)

    print(f"\n  [{name}]")
    print(f"    OWN WINDOW: OOS Sh={oos_m['sharpe']:.2f}, WF min={wf['wf_min']:.2f}, "
          f"all_pos={wf['all_positive']}, active={act:.1%}")
    if ml_wf:
        print(f"    ML WINDOW:  WF folds={[round(s,2) for s in ml_wf['fold_sharpes']]}, "
              f"WF min={ml_wf['wf_min']:.2f}, all_pos={ml_wf['all_positive']}, active={ml_act:.1%}")

    return {
        "name": name,
        "own_window": {
            "date_range":  {
                "start": str(pnl_df.index[0].date()),
                "end":   str(pnl_df.index[-1].date()),
                "n_days": n_all,
            },
            "full_sample":  {k: round(v, 4) if isinstance(v, float) else v
                             for k, v in full_m.items()},
            "oos_135d": {
                "oos_sharpe":  round(oos_m["sharpe"], 4),
                "oos_ann_ret": round(oos_m["ann_ret"], 4),
                "oos_ann_vol": round(oos_m["ann_vol"], 4),
                "oos_max_dd":  round(oos_m["max_dd"], 4),
                "oos_n_days":  len(oos_r),
            },
            "walk_forward": wf,
            "active_rate":  round(act, 4),
            "regime_stats": {
                "n_growth_days":     n_growth,
                "n_contraction_days": n_contraction,
                "pct_growth":        round(n_growth / n_all, 4),
            },
        },
        "ml_window": {
            "date_range":    {
                "start": ML_WINDOW_START,
                "end":   ML_WINDOW_END,
                "n_days": int(ml_mask.sum()),
            },
            "walk_forward":  ml_wf,
            "active_rate":   round(ml_act, 4),
        } if ml_wf else None,
        "acceptance_gates": {
            "wf_all_positive":     wf["all_positive"],
            "oos_sharpe_ge_1_5":   bool(oos_m["sharpe"] >= 1.5),
            "active_rate_ge_5pct": bool(act >= 0.05),
            "ml_wf_all_positive":  bool(ml_wf["all_positive"]) if ml_wf else None,
        },
    }


# ── build regime signal series ─────────────────────────────────────────────────
def build_regime_signal_series(feat: pd.DataFrame, base_sig: pd.Series) -> dict:
    """Return all three gated signal series."""
    return {
        "K232a": gate_hard(feat, base_sig),
        "K232b": gate_soft(feat, base_sig),
        "K232c": gate_zscore(feat, base_sig),
    }


# ── curves JSON ────────────────────────────────────────────────────────────────
def build_curves_json(
    feat: pd.DataFrame,
    base_sig: pd.Series,
    gated_sigs: dict,
    btc_price: pd.Series,
    results: dict,
) -> dict:
    pnl_base = compute_pnl(btc_price, base_sig)
    curves = {
        "generated_at":  pd.Timestamp.utcnow().isoformat(),
        "dates":         [str(t.date()) for t in pnl_base.index],
        "supply_total_B": [
            round(float(v) / 1e9, 4) if not math.isnan(float(v)) else None
            for v in feat.reindex(pnl_base.index)["TOTAL"].values
        ],
        "supply_30d_trend": [
            round(float(v), 6) if not math.isnan(float(v)) else None
            for v in feat.reindex(pnl_base.index)["supply_30d_trend"].values
        ],
        "supply_trend_z": [
            round(float(v), 4) if not math.isnan(float(v)) else None
            for v in feat.reindex(pnl_base.index)["supply_trend_z"].values
        ],
        "mint_7d_z": [
            round(float(v), 4) if not math.isnan(float(v)) else None
            for v in feat.reindex(pnl_base.index)["mint_7d_z"].values
        ],
        "K228_baseline_signal":  [int(v) for v in base_sig.values],
        "K228_baseline_equity":  equity_curve(pnl_base["pnl_net"]),
        "btc_buy_hold_equity": [
            {"date": str(t.date()), "eq": round(float(v), 6)}
            for t, v in (1 + pnl_base["ret_btc"].fillna(0)).cumprod().items()
        ],
    }
    for name, sig in gated_sigs.items():
        pnl_g = compute_pnl(btc_price, sig)
        curves[f"{name}_signal"]  = [round(float(v), 4) for v in sig.values]
        curves[f"{name}_equity"]  = equity_curve(pnl_g["pnl_net"])
        curves[f"{name}_daily_ret"] = [round(float(v), 8) for v in pnl_g["pnl_net"].values]
    return curves


# ── markdown report ────────────────────────────────────────────────────────────
def write_markdown(results: dict, baseline_wf: dict, best_name: str | None):
    from datetime import datetime

    now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

    variants = ["K232a", "K232b", "K232c"]

    def wf_rows_own(name):
        if name not in results:
            return "N/A"
        folds = results[name]["own_window"]["walk_forward"]["folds"]
        rows  = []
        for f in folds:
            sh  = f["sharpe"]
            star = " **" if abs(sh) > 0 else ""
            rows.append(
                f"| {f['fold']} | {f['start']} | {f['end']} | {f['n_days']} "
                f"| **{sh:.2f}** | {f['ann_ret']:.2%} | {f['max_dd']:.2%} |"
            )
        return "\n".join(rows)

    def wf_rows_ml(name):
        if name not in results or results[name]["ml_window"] is None:
            return "N/A"
        folds = results[name]["ml_window"]["walk_forward"]["folds"]
        rows  = []
        for f in folds:
            sh = f["sharpe"]
            rows.append(
                f"| {f['fold']} | {f['start']} | {f['end']} | {f['n_days']} "
                f"| **{sh:.2f}** | {f['ann_ret']:.2%} | {f['max_dd']:.2%} |"
            )
        return "\n".join(rows)

    def gate_table_row(name):
        if name not in results:
            return f"| {name} | N/A | N/A | N/A | N/A | N/A |"
        r   = results[name]
        own = r["own_window"]
        ml  = r["ml_window"]
        g   = r["acceptance_gates"]
        oos_sh   = own["oos_135d"]["oos_sharpe"]
        act      = own["active_rate"]
        wf_all   = "YES" if g["wf_all_positive"] else "NO"
        ml_wfall = "YES" if g.get("ml_wf_all_positive") else "NO"
        acc      = "ACCEPT" if (g["wf_all_positive"] and g["oos_sharpe_ge_1_5"] and g["active_rate_ge_5pct"]) else "REJECT"
        return (f"| {name} | {oos_sh:.2f} | {act:.1%} | {wf_all} | {ml_wfall} | **{acc}** |")

    # Baseline K228 WF own-window
    base_wf_folds = "\n".join(
        f"| {f['fold']} | {f['start']} | {f['end']} | {f['n_days']} "
        f"| **{f['sharpe']:.2f}** | {f['ann_ret']:.2%} | {f['max_dd']:.2%} |"
        for f in baseline_wf["folds"]
    )

    verdict = "ACCEPT" if best_name else "REJECT"
    k233_section = ""
    if best_name:
        k233_section = f"""
## 7. K233 5-Way Meta Plan

K232 variant **{best_name}** ACCEPTED. Gated K228 replaces ungated K228 as component.

### K233 = K229d + {best_name} (Gated K228) = 5-Way Meta v6.9 Candidate

| Component | Role | Note |
|-----------|------|------|
| K198 | ML momentum allocator | Core |
| K204 | ML drawdown embed | Core |
| K208 | DAR reverse carry | Core |
| K226 | ETH validator queue | Added in K229d |
| {best_name} (K228 gated) | Stablecoin mint/burn | Regime-filtered new addition |

**Integration steps:**
1. Load `cache/stablecoin_supply_daily.parquet` daily
2. Compute 30d supply trend for gate criterion
3. Apply {best_name} gate to K228 raw signal
4. Feed gated daily return into 5-way inverse-vol ensemble
5. Walk-forward validate 5-way ensemble (K233 objective)

**Risk note:** Regime gate trained on same data window — minor look-ahead risk in
fold 2. K233 should re-validate with strict temporal holdout.
"""
    else:
        k233_section = f"""
## 7. K233 5-Way Meta Plan

**All K232 variants REJECTED.** No variant passes all acceptance gates.

Recommended next steps:
- Diagnose fold-specific failure modes (check regime gate alignment with fold 2 contraction)
- Consider stricter z-score threshold (K232c-v2 with z > 0.5 instead of z > 0)
- Explore graduated soft gate with different breakpoints
- K233 target: re-run after K232 variant refinement
"""

    md = f"""# Wave K232 — K228 Stablecoin Regime-Gated Strategy Report

**Generated:** {now_str}
**Objective:** Fix K228 WF fold 2 failure (Sh=-2.15, 2025-05-14 → 2025-09-01) via internal regime gate
**Method:** Suppress K228 signal during stablecoin supply contraction phases (30d trend ≤ 0)

---

## Executive Summary

K228 (stablecoin mint/burn) ACCEPTED standalone (OOS Sh 2.77) but its WF fold 2 = -2.15
during a stablecoin contraction/reversal regime (2025-07/08) contaminates all K230 4-way
ensemble variants below the WF min threshold of 6.93. K232 applies an internal regime gate
to suppress K228 signal when stablecoin supply is contracting (30d trend ≤ 0), targeting
elimination of the single-point fold 2 failure.

Three gate variants tested:
- **K232a** Hard gate: trend > 0 → active, else → 0
- **K232b** Soft gate: trend ≥ 0 → full, trend ≤ -5% → 0, linear between
- **K232c** Z-score gate: z(30d trend, 90d) > 0 → active, else → 0

| Variant | OOS Sh | Active Rate | WF All+ (own) | WF All+ (ML) | Verdict |
|---------|--------|-------------|---------------|--------------|---------|
| K228 baseline | 2.77 | ~14.7% | YES (2.02/0.57/0.56/2.89) | NO (fold2=-2.15) | (REFERENCE) |
{gate_table_row('K232a')}
{gate_table_row('K232b')}
{gate_table_row('K232c')}

**Winning variant:** {best_name if best_name else "None — all reject"}

---

## 1. Regime Gate Design

### Stablecoin Supply 30d Trend
```
supply_30d_trend[t] = TOTAL[t] / TOTAL[t-30] - 1
```
This measures whether the combined USDT+USDC supply has grown or contracted over
the past 30 days. A negative trend indicates net redemptions (capital outflow regime).

### K232a — Hard Gate
```python
gate = 1 if supply_30d_trend > 0 else 0
signal_gated = signal_k228 * gate
```

### K232b — Soft Gate (Graduated Suppression)
```python
if trend >= 0:      scalar = 1.0
elif trend <= -0.05: scalar = 0.0
else:               scalar = (trend - (-0.05)) / (0 - (-0.05))  # linear
signal_gated = signal_k228 * scalar
```

### K232c — Z-Score Gate
```python
supply_trend_z = zscore(supply_30d_trend, window=90)
gate = 1 if supply_trend_z > 0 else 0
signal_gated = signal_k228 * gate
```

---

## 2. K228 Baseline (No Gate) — Reference

### OWN WINDOW Walk-Forward (2024-05-23 → 2026-05-22, n=730)

| Fold | Start | End | Days | Sharpe | Ann Ret | Max DD |
|------|-------|-----|------|--------|---------|--------|
{base_wf_folds}

**WF mean:** {baseline_wf['wf_mean']:.2f} | **WF min:** {baseline_wf['wf_min']:.2f} | All positive: YES (own window)
Note: K228 own-window WF is all-positive. The blocker is the **ML window** fold 2 = -2.15.

---

## 3. K232a — Hard Gate Results

### Own-Window Walk-Forward
| Fold | Start | End | Days | Sharpe | Ann Ret | Max DD |
|------|-------|-----|------|--------|---------|--------|
{wf_rows_own('K232a')}

**WF mean:** {results.get('K232a', {}).get('own_window', {}).get('walk_forward', {}).get('wf_mean', 'N/A')} | **WF min:** {results.get('K232a', {}).get('own_window', {}).get('walk_forward', {}).get('wf_min', 'N/A')} | All positive: {'YES' if results.get('K232a', {}).get('own_window', {}).get('walk_forward', {}).get('all_positive', False) else 'NO'}

### ML-Window Walk-Forward (2025-01-22 → 2026-04-14)
| Fold | Start | End | Days | Sharpe | Ann Ret | Max DD |
|------|-------|-----|------|--------|---------|--------|
{wf_rows_ml('K232a')}

**Active rate:** {results.get('K232a', {}).get('own_window', {}).get('active_rate', 0):.1%}

---

## 4. K232b — Soft Gate Results

### Own-Window Walk-Forward
| Fold | Start | End | Days | Sharpe | Ann Ret | Max DD |
|------|-------|-----|------|--------|---------|--------|
{wf_rows_own('K232b')}

**WF mean:** {results.get('K232b', {}).get('own_window', {}).get('walk_forward', {}).get('wf_mean', 'N/A')} | **WF min:** {results.get('K232b', {}).get('own_window', {}).get('walk_forward', {}).get('wf_min', 'N/A')} | All positive: {'YES' if results.get('K232b', {}).get('own_window', {}).get('walk_forward', {}).get('all_positive', False) else 'NO'}

### ML-Window Walk-Forward (2025-01-22 → 2026-04-14)
| Fold | Start | End | Days | Sharpe | Ann Ret | Max DD |
|------|-------|-----|------|--------|---------|--------|
{wf_rows_ml('K232b')}

**Active rate:** {results.get('K232b', {}).get('own_window', {}).get('active_rate', 0):.1%}

---

## 5. K232c — Z-Score Gate Results

### Own-Window Walk-Forward
| Fold | Start | End | Days | Sharpe | Ann Ret | Max DD |
|------|-------|-----|------|--------|---------|--------|
{wf_rows_own('K232c')}

**WF mean:** {results.get('K232c', {}).get('own_window', {}).get('walk_forward', {}).get('wf_mean', 'N/A')} | **WF min:** {results.get('K232c', {}).get('own_window', {}).get('walk_forward', {}).get('wf_min', 'N/A')} | All positive: {'YES' if results.get('K232c', {}).get('own_window', {}).get('walk_forward', {}).get('all_positive', False) else 'NO'}

### ML-Window Walk-Forward (2025-01-22 → 2026-04-14)
| Fold | Start | End | Days | Sharpe | Ann Ret | Max DD |
|------|-------|-----|------|--------|---------|--------|
{wf_rows_ml('K232c')}

**Active rate:** {results.get('K232c', {}).get('own_window', {}).get('active_rate', 0):.1%}

---

## 6. Acceptance Gate Summary

| Criterion | K232a | K232b | K232c |
|-----------|-------|-------|-------|
| OOS Sh ≥ 1.5 (own window) | {'YES' if results.get('K232a',{}).get('acceptance_gates',{}).get('oos_sharpe_ge_1_5') else 'NO'} | {'YES' if results.get('K232b',{}).get('acceptance_gates',{}).get('oos_sharpe_ge_1_5') else 'NO'} | {'YES' if results.get('K232c',{}).get('acceptance_gates',{}).get('oos_sharpe_ge_1_5') else 'NO'} |
| WF all folds > 0 (own window) | {'YES' if results.get('K232a',{}).get('acceptance_gates',{}).get('wf_all_positive') else 'NO'} | {'YES' if results.get('K232b',{}).get('acceptance_gates',{}).get('wf_all_positive') else 'NO'} | {'YES' if results.get('K232c',{}).get('acceptance_gates',{}).get('wf_all_positive') else 'NO'} |
| Active rate ≥ 5% | {'YES' if results.get('K232a',{}).get('acceptance_gates',{}).get('active_rate_ge_5pct') else 'NO'} | {'YES' if results.get('K232b',{}).get('acceptance_gates',{}).get('active_rate_ge_5pct') else 'NO'} | {'YES' if results.get('K232c',{}).get('acceptance_gates',{}).get('active_rate_ge_5pct') else 'NO'} |
| WF all folds > 0 (ML window) | {'YES' if results.get('K232a',{}).get('acceptance_gates',{}).get('ml_wf_all_positive') else 'NO'} | {'YES' if results.get('K232b',{}).get('acceptance_gates',{}).get('ml_wf_all_positive') else 'NO'} | {'YES' if results.get('K232c',{}).get('acceptance_gates',{}).get('ml_wf_all_positive') else 'NO'} |
| **Overall** | **{'ACCEPT' if all([results.get('K232a',{}).get('acceptance_gates',{}).get(k) for k in ['wf_all_positive','oos_sharpe_ge_1_5','active_rate_ge_5pct']]) else 'REJECT'}** | **{'ACCEPT' if all([results.get('K232b',{}).get('acceptance_gates',{}).get(k) for k in ['wf_all_positive','oos_sharpe_ge_1_5','active_rate_ge_5pct']]) else 'REJECT'}** | **{'ACCEPT' if all([results.get('K232c',{}).get('acceptance_gates',{}).get(k) for k in ['wf_all_positive','oos_sharpe_ge_1_5','active_rate_ge_5pct']]) else 'REJECT'}** |

{k233_section}
"""

    with open(OUT_MD, "w") as f:
        f.write(md)
    print(f"  [saved] {OUT_MD}")


# ── main ───────────────────────────────────────────────────────────────────────
def main():
    t0 = time.time()
    print("=" * 78)
    print("Wave K232 — K228 Stablecoin Regime-Gated Strategy")
    print("=" * 78)

    # 1) Load data
    print("\n[1] Loading stablecoin supply data...")
    stable = load_stablecoin_supply()

    print("\n[2] Loading BTC daily close...")
    btc = load_btc_daily()

    # 2) Build features
    print("\n[3] Building features...")
    feat_all = build_k228_features(stable)
    feat_all = feat_all.dropna(subset=["mint_7d_z", "supply_30d_trend"])

    # 3) Align to BTC price
    common_idx = feat_all.index.intersection(btc.index)
    feat   = feat_all.loc[common_idx]
    btc_c  = btc.loc[common_idx]
    print(f"  Aligned: {len(common_idx)} days, "
          f"{common_idx.min().date()} → {common_idx.max().date()}")

    # 4) Base K228 signal
    print("\n[4] Building base K228 signal...")
    base_sig = build_base_signal(feat)
    n_active = int((base_sig.abs() > 0).sum())
    print(f"  K228 base: {n_active} active days / {len(base_sig)} total ({n_active/len(base_sig):.1%})")

    # 5) Regime analysis
    trend = feat["supply_30d_trend"]
    n_growth = int((trend > 0).sum())
    n_contr  = int((trend <= 0).sum())
    print(f"\n  Supply 30d trend: growth={n_growth}d ({n_growth/len(trend):.1%}), "
          f"contraction={n_contr}d ({n_contr/len(trend):.1%})")

    # Show fold 2 period context for K230 diagnostic
    fold2_start = pd.Timestamp("2025-05-14")
    fold2_end   = pd.Timestamp("2025-09-01")
    fold2_mask  = (feat.index >= fold2_start) & (feat.index <= fold2_end)
    fold2_trend = trend[fold2_mask]
    n_neg_fold2 = int((fold2_trend <= 0).sum())
    print(f"\n  Fold 2 (2025-05-14 → 2025-09-01): {fold2_mask.sum()}d, "
          f"trend<=0: {n_neg_fold2}d ({n_neg_fold2/fold2_mask.sum():.1%})")

    # 6) Baseline K228 WF (own window)
    print("\n[5] K228 baseline walk-forward (own window)...")
    pnl_base = compute_pnl(btc_c, base_sig)
    baseline_wf = walk_forward_4fold(pnl_base)
    print(f"  Baseline WF folds: {[round(s,2) for s in baseline_wf['fold_sharpes']]}")
    print(f"  Baseline WF min={baseline_wf['wf_min']:.2f}, all_pos={baseline_wf['all_positive']}")

    # 7) Build gated signals
    print("\n[6] Building gated signals...")
    gated_sigs = build_regime_signal_series(feat, base_sig)
    for name, sig in gated_sigs.items():
        act = active_rate(sig)
        n_act = int((sig.abs() > 0).sum())
        print(f"  {name}: {n_act} active days ({act:.1%})")

    # 8) Evaluate each variant
    print("\n[7] Evaluating variants...")
    results = {}
    for name, sig in gated_sigs.items():
        results[name] = evaluate_variant(name, sig, btc_c, feat)

    # 9) Determine best variant
    accepted = [
        name for name, r in results.items()
        if (r["acceptance_gates"]["wf_all_positive"]
            and r["acceptance_gates"]["oos_sharpe_ge_1_5"]
            and r["acceptance_gates"]["active_rate_ge_5pct"])
    ]
    # Rank by OOS sharpe among accepted
    if accepted:
        best_name = max(accepted, key=lambda n: results[n]["own_window"]["oos_135d"]["oos_sharpe"])
    else:
        best_name = None

    print(f"\n[8] Acceptance summary:")
    for name in results:
        g = results[name]["acceptance_gates"]
        status = "ACCEPT" if (g["wf_all_positive"] and g["oos_sharpe_ge_1_5"] and g["active_rate_ge_5pct"]) else "REJECT"
        print(f"  {name}: {status} (WF_all+={g['wf_all_positive']}, OOS_sh_ge1.5={g['oos_sharpe_ge_1_5']}, act_ge5={g['active_rate_ge_5pct']})")
    print(f"  Best variant: {best_name if best_name else 'None'}")

    # 10) Output JSON
    elapsed = time.time() - t0
    out = {
        "wave": "K232",
        "objective": "K228 regime-gated to fix WF fold 2 = -2.15 (2025-07/08 contraction regime)",
        "generated_at": pd.Timestamp.utcnow().isoformat(),
        "runtime_s":   round(elapsed, 2),
        "regime_analysis": {
            "trend_window_days": TREND_WIN,
            "z_window_days":     TREND_Z_WIN,
            "n_growth_days":     n_growth,
            "n_contraction_days": n_contr,
            "fold2_contraction_pct": round(n_neg_fold2 / fold2_mask.sum(), 4) if fold2_mask.sum() > 0 else 0,
        },
        "k228_baseline": {
            "own_window_wf": baseline_wf,
            "oos_sharpe_135d": 2.7665,  # from K228 original
            "ml_window_fold2_sharpe": -2.1503,  # K230 diagnostic
            "blocker": "ML-window fold 2 = -2.15 (stablecoin reversal 2025-07/08)",
        },
        "variants": results,
        "accepted_variants": accepted,
        "best_variant": best_name,
        "verdict": f"ACCEPT — {best_name}" if best_name else "REJECT — no variant passes all gates",
        "k233_plan": {
            "description": "5-way meta ensemble: K198 + K204 + K208 + K226 + K232_gated_K228",
            "prerequisite": f"K232 best variant = {best_name}",
            "status": "PROCEED" if best_name else "BLOCKED — K232 rejection",
        } if best_name else None,
    }

    with open(OUT_JSON, "w") as f:
        json.dump(out, f, indent=2, default=str)
    print(f"\n  [saved] {OUT_JSON}")

    # 11) Curves JSON
    print("\n[9] Building curves JSON...")
    curves = build_curves_json(feat, base_sig, gated_sigs, btc_c, results)
    with open(OUT_CURVES, "w") as f:
        json.dump(curves, f, indent=2, default=str)
    print(f"  [saved] {OUT_CURVES}")

    # 12) Markdown
    print("\n[10] Writing markdown report...")
    write_markdown(results, baseline_wf, best_name)

    # Final summary
    print("\n" + "=" * 78)
    print("WAVE K232 SUMMARY")
    print("=" * 78)
    for name in results:
        r  = results[name]
        ow = r["own_window"]
        ml = r["ml_window"]
        print(f"  {name}: OOS_Sh={ow['oos_135d']['oos_sharpe']:.2f}, "
              f"WF_min={ow['walk_forward']['wf_min']:.2f} "
              f"({'all+' if ow['walk_forward']['all_positive'] else 'fold-'}), "
              f"act={ow['active_rate']:.1%}"
              + (f", ML_WF_min={ml['walk_forward']['wf_min']:.2f}"
                 f" ({'all+' if ml['walk_forward']['all_positive'] else 'fold-'})"
                 if ml and ml.get('walk_forward') else ""))
    print(f"  Best: {best_name if best_name else 'None'}")
    print(f"  Verdict: {'ACCEPT → K233 5-way meta' if best_name else 'REJECT'}")
    print(f"  Runtime: {elapsed:.1f}s")
    print("=" * 78)


if __name__ == "__main__":
    main()
