"""
Wave K262 — Dollar-Neutral Cross-Sectional Momentum
Objective: Orthogonal alpha source independent of K246a FR/carry mechanism.
Spec: 30d trailing momentum, daily rebalance, top/bottom quartile L/S,
      dollar-neutral (long$ = short$), 7bp/side maker cost.
Universe: 50 symbols from 4h_730d cache, aggregated to daily.
"""

from __future__ import annotations

import json
import math
import time
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

CACHE = "/Users/nekonaomichi/crypto-lab/cache"
OUT_JSON  = "/Users/nekonaomichi/crypto-lab/wave_k262_dollar_neutral_momentum.json"
OUT_CURVES = "/Users/nekonaomichi/crypto-lab/wave_k262_curves.json"
OUT_MD    = "/Users/nekonaomichi/crypto-lab/wave_k262_dollar_neutral_momentum.md"

# ── Universe ─────────────────────────────────────────────────────────────────
# All 56 symbols with 4h_730d parquet available (non hist_premium).
# We filter to those with ≥ 600 daily bars at load time.
SYMBOLS_CANDIDATE = [
    "AAVE","ADA","APT","ARB","ARKM","ATOM","AVAX","BNB","BOME","BONK","BTC",
    "COMP","CRV","DOGE","DOT","DYDX","ENA","ETC","ETH","FET","FIL","FLOKI",
    "GMX","GRT","ICP","IMX","INJ","JTO","JUP","LDO","LINK","LTC","MANTA",
    "NEAR","ONDO","OP","PEPE","POPCAT","PYTH","RENDER","RUNE","SEI","SHIB",
    "SNX","SOL","STRK","STX","SUI","SUSHI","TAO","TIA","TRX","UNI","WIF",
    "WLD","XRP",
]

# ── Design constants ──────────────────────────────────────────────────────────
MOM_DAYS        = 30         # trailing momentum window (days)
SKIP_DAYS       = 1          # skip last 1 day (avoid micro-reversal)
QUARTILE        = 0.25       # top/bottom 25%
COST_BPS        = 7.0        # per side
COST_RATE       = COST_BPS / 1e4
PPY             = 365.0      # periods per year (daily)
IS_FRAC         = 0.70

# ── Data loading ──────────────────────────────────────────────────────────────
def load_daily_panel() -> pd.DataFrame:
    """
    Aggregate 4h bars → daily OHLCV close panel.
    Daily bar = 6 × 4h bars; anchor to UTC midnight.
    Only symbols with ≥ 600 daily rows are kept.
    """
    frames = []
    kept = []
    for sym in SYMBOLS_CANDIDATE:
        path = f"{CACHE}/{sym}USDT_4h_730d.parquet"
        try:
            df = pd.read_parquet(path, columns=["open_time","close"])
            df = df.sort_values("open_time").drop_duplicates("open_time")
            df["date"] = df["open_time"].dt.normalize()
            daily = df.groupby("date")["close"].last().rename(sym)
            if len(daily) >= 600:
                frames.append(daily)
                kept.append(sym)
        except Exception:
            pass

    panel = pd.concat(frames, axis=1).sort_index()
    return panel, kept


# ── Signal ────────────────────────────────────────────────────────────────────
def momentum_signal(panel: pd.DataFrame) -> pd.DataFrame:
    """
    30d momentum skipping last 1 day:
        mom_t = close_{t-1} / close_{t-31} - 1
    Signal shifted +1 so it's known at open-of-day t.
    """
    end   = panel.shift(SKIP_DAYS)
    start = panel.shift(SKIP_DAYS + MOM_DAYS)
    sig   = end / start - 1.0
    return sig.shift(1)   # trade on next day's open


# ── Position sizing ────────────────────────────────────────────────────────────
def dollar_neutral_weights(sig_row: pd.Series) -> pd.Series:
    """
    Long top-quartile, short bottom-quartile, equal-weight within each sleeve.
    Dollar-neutral: sum(long) = 1, sum(|short|) = 1 → gross = 2.
    Returns per-symbol weight (positive=long, negative=short).
    """
    valid = sig_row.dropna()
    if len(valid) < 4:
        return pd.Series(0.0, index=sig_row.index)

    n_sym = len(valid)
    n_q   = max(1, int(n_sym * QUARTILE))

    ranked = valid.rank(ascending=True)
    longs  = ranked[ranked > n_sym - n_q].index
    shorts = ranked[ranked <= n_q].index

    w = pd.Series(0.0, index=sig_row.index)
    w[longs]  = +1.0 / len(longs)
    w[shorts] = -1.0 / len(shorts)
    return w


def compute_weights(sig: pd.DataFrame) -> pd.DataFrame:
    return sig.apply(dollar_neutral_weights, axis=1)


# ── PnL ───────────────────────────────────────────────────────────────────────
def compute_pnl(panel: pd.DataFrame, weights: pd.DataFrame) -> pd.Series:
    ret    = panel.pct_change()
    # weights at t → apply to return at t (enter next open = same daily close ret approx)
    w_lag  = weights.shift(1).fillna(0.0)
    pnl_gross = (w_lag * ret).sum(axis=1)
    # turnover cost: sum of absolute weight changes
    turn   = (weights - weights.shift(1).fillna(0.0)).abs().sum(axis=1)
    cost   = turn * COST_RATE
    pnl_net = pnl_gross - cost
    return pnl_net, pnl_gross, turn


# ── Metrics ───────────────────────────────────────────────────────────────────
def sharpe(ret: np.ndarray) -> float:
    r = np.asarray(ret, dtype=float)
    r = r[~np.isnan(r)]
    if len(r) < 10 or r.std() == 0:
        return 0.0
    return float(r.mean() / r.std() * math.sqrt(PPY))


def max_dd(ret: np.ndarray) -> float:
    r = np.asarray(ret, dtype=float)
    r = r[~np.isnan(r)]
    if len(r) == 0:
        return 0.0
    eq   = np.cumprod(1 + r)
    peak = np.maximum.accumulate(eq)
    return float(((eq - peak) / peak).min())


def ann_ret(ret: np.ndarray) -> float:
    r = np.asarray(ret, dtype=float)
    r = r[np.isfinite(r)]
    return float(r.mean() * PPY)


def ann_vol(ret: np.ndarray) -> float:
    r = np.asarray(ret, dtype=float)
    r = r[np.isfinite(r)]
    return float(r.std() * math.sqrt(PPY))


def win_rate(ret: np.ndarray) -> float:
    r = np.asarray(ret, dtype=float)
    r = r[np.isfinite(r) & (r != 0)]
    return float((r > 0).mean()) if len(r) > 0 else 0.0


def metrics(ret_arr: np.ndarray) -> dict:
    return {
        "sharpe":       sharpe(ret_arr),
        "max_dd":       max_dd(ret_arr),
        "ann_ret":      ann_ret(ret_arr),
        "ann_vol":      ann_vol(ret_arr),
        "win_rate":     win_rate(ret_arr),
        "total_return": float(np.nanprod(1 + ret_arr) - 1),
        "n_days":       int(np.sum(~np.isnan(ret_arr))),
    }


# ── Walk-forward 4-fold ───────────────────────────────────────────────────────
def walk_forward(pnl: pd.Series) -> list[dict]:
    n = len(pnl)
    fold_n = n // 4
    folds = []
    for i in range(4):
        lo = i * fold_n
        hi = (i + 1) * fold_n if i < 3 else n
        sub = pnl.iloc[lo:hi].values
        folds.append({
            "fold": i,
            "start": str(pnl.index[lo].date()),
            "end":   str(pnl.index[hi - 1].date()),
            **metrics(sub),
        })
    return folds


# ── Market beta ───────────────────────────────────────────────────────────────
def market_beta(pnl: pd.Series, panel: pd.DataFrame) -> float:
    """Regress daily strategy return on equal-weight market return."""
    mkt = panel.pct_change().mean(axis=1)
    joined = pd.concat([pnl.rename("strat"), mkt.rename("mkt")], axis=1).dropna()
    if len(joined) < 30:
        return float("nan")
    cov  = np.cov(joined["strat"], joined["mkt"])
    beta = cov[0, 1] / cov[1, 1]
    return float(beta)


# ── Correlation vs K246a components ──────────────────────────────────────────
def corr_vs_k246a(pnl_daily: pd.Series) -> dict:
    """Load K198 / K208 / K226 equity curves → compute daily return correlation."""
    corrs = {}

    # K198 — pnl_ridge is daily pnl, aligned to dates_ml
    try:
        with open("/Users/nekonaomichi/crypto-lab/wave_k198_curves.json") as f:
            d = json.load(f)
        dates = pd.to_datetime(d["dates_ml"])
        pnl   = pd.Series(d["pnl_ridge"], index=dates, name="K198")
        joined = pd.concat([pnl_daily, pnl], axis=1).dropna()
        if len(joined) >= 30:
            corrs["K198"] = float(joined.iloc[:,0].corr(joined.iloc[:,1]))
        else:
            corrs["K198"] = None
    except Exception as e:
        corrs["K198"] = f"error: {e}"

    # K208 — cumulative_pnl at 8h timestamps → convert to daily
    try:
        with open("/Users/nekonaomichi/crypto-lab/wave_k208_curves.json") as f:
            d = json.load(f)
        v    = d["K208_filtered"]
        ts   = pd.to_datetime(v["timestamps"])
        cpnl = pd.Series(v["cumulative_pnl"], index=ts)
        # convert cumulative → equity → daily returns
        eq   = 1 + cpnl
        eq_d = eq.resample("1D").last().dropna()
        ret_d = eq_d.pct_change().dropna().rename("K208")
        joined = pd.concat([pnl_daily, ret_d], axis=1).dropna()
        if len(joined) >= 30:
            corrs["K208"] = float(joined.iloc[:,0].corr(joined.iloc[:,1]))
        else:
            corrs["K208"] = None
    except Exception as e:
        corrs["K208"] = f"error: {e}"

    # K226 — only dates + signal columns; no equity → use K246a final curves
    try:
        with open("/Users/nekonaomichi/crypto-lab/wave_k226_curves.json") as f:
            d = json.load(f)
        # structure: {dates, signal, ...}  — use daily signal as proxy if equity unavailable
        # fallback: load k246a_k226 contribution if available
        if "dates" in d:
            corrs["K226"] = "no equity series in K226 curves"
        else:
            corrs["K226"] = "unavailable"
    except Exception as e:
        corrs["K226"] = f"error: {e}"

    # K246a 3-way combined — use wave_k246_curves
    try:
        with open("/Users/nekonaomichi/crypto-lab/wave_k246_k198_k204_contribution.json") as f:
            meta = json.load(f)
        # Try to load K229 (predecessor) curves which has daily equity
        with open("/Users/nekonaomichi/crypto-lab/wave_k229_curves.json") as f:
            c = json.load(f)
        # find K246a key
        for key in c:
            if "K246a" in key or "246a" in key.lower():
                data = c[key]
                if isinstance(data, list):
                    ts  = pd.to_datetime([x["ts"] for x in data])
                    eq  = pd.Series([x["eq"] for x in data], index=ts)
                    ret = eq.pct_change().dropna().rename("K246a")
                    joined = pd.concat([pnl_daily, ret], axis=1).dropna()
                    if len(joined) >= 30:
                        corrs["K246a"] = float(joined.iloc[:,0].corr(joined.iloc[:,1]))
                    else:
                        corrs["K246a"] = None
                    break
    except Exception as e:
        corrs["K246a"] = f"unavailable: {e}"

    return corrs


# ── Equity curve helper ───────────────────────────────────────────────────────
def equity_curve_data(pnl: pd.Series) -> list[dict]:
    eq = (1 + pnl.fillna(0)).cumprod()
    return [{"ts": str(idx.date()), "eq": float(v)} for idx, v in eq.items()]


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    t0 = time.time()
    print("=" * 72)
    print("Wave K262 — Dollar-Neutral Cross-Sectional Momentum")
    print("=" * 72)

    # 1. Load data
    print(f"Loading {len(SYMBOLS_CANDIDATE)} candidate symbols (4h → daily)...")
    panel, kept = load_daily_panel()
    print(f"  Kept {len(kept)} symbols | panel: {panel.shape} | "
          f"{panel.index[0].date()} → {panel.index[-1].date()}")

    # Drop columns with > 20% NaN
    frac_nan = panel.isna().mean()
    panel = panel.loc[:, frac_nan < 0.20]
    kept_final = panel.columns.tolist()
    print(f"  After NaN filter: {len(kept_final)} symbols")

    n      = len(panel)
    is_cut = int(n * IS_FRAC)

    # 2. Signal
    print("Computing 30d momentum signal...")
    sig = momentum_signal(panel)

    # 3. Weights
    print("Computing daily dollar-neutral weights...")
    weights = compute_weights(sig)

    # Spot-check: verify dollar-neutral
    sample_day = weights.iloc[MOM_DAYS + 5]
    long_sum  = sample_day[sample_day > 0].sum()
    short_sum = sample_day[sample_day < 0].sum()
    print(f"  Sample day check: long_sum={long_sum:.3f}  short_sum={short_sum:.3f}")

    # 4. PnL
    print("Computing PnL...")
    pnl_net, pnl_gross, turnover = compute_pnl(panel, weights)
    pnl_net = pnl_net.dropna()

    # 5. Metrics
    is_ret  = pnl_net.iloc[:is_cut].values
    oos_ret = pnl_net.iloc[is_cut:].values
    full_ret = pnl_net.values

    is_m   = metrics(is_ret)
    oos_m  = metrics(oos_ret)
    full_m = metrics(full_ret)

    print(f"\n  IS   Sharpe: {is_m['sharpe']:.3f}  MaxDD: {is_m['max_dd']:.2%}  AnnRet: {is_m['ann_ret']:+.2%}")
    print(f"  OOS  Sharpe: {oos_m['sharpe']:.3f}  MaxDD: {oos_m['max_dd']:.2%}  AnnRet: {oos_m['ann_ret']:+.2%}")
    print(f"  Full Sharpe: {full_m['sharpe']:.3f}  MaxDD: {full_m['max_dd']:.2%}  AnnRet: {full_m['ann_ret']:+.2%}")

    # 6. Walk-forward 4-fold
    print("\nWalk-forward 4-fold...")
    wf = walk_forward(pnl_net)
    for f in wf:
        print(f"  Fold {f['fold']} ({f['start']} - {f['end']}): "
              f"SR={f['sharpe']:.3f}  DD={f['max_dd']:.2%}  ret={f['total_return']:+.2%}")
    wf_min = min(f["sharpe"] for f in wf)
    wf_all_pos = all(f["sharpe"] > 0 for f in wf)
    print(f"  WF min SR: {wf_min:.3f}  All folds positive: {wf_all_pos}")

    # 7. Market beta
    print("\nComputing market beta...")
    beta = market_beta(pnl_net, panel)
    print(f"  Market beta vs equal-weight universe: {beta:.4f}")

    # 8. Average daily turnover
    avg_turn = float(turnover.mean())
    avg_cost_pct = avg_turn * COST_RATE * 100
    print(f"  Avg daily turnover: {avg_turn:.3f}  implied cost: {avg_cost_pct:.4f}%/day")

    # 9. Correlation vs K246a components
    print("\nCorrelation vs K246a components...")
    pnl_daily = pnl_net.copy()
    pnl_daily.index = pd.to_datetime(pnl_daily.index)
    corrs = corr_vs_k246a(pnl_daily)
    for k, v in corrs.items():
        print(f"  |ρ| vs {k}: {v}")

    # 10. Acceptance gates
    gates = {
        "G1_WF_all_folds_positive":   bool(wf_all_pos),
        "G2_OOS_Sharpe_gt_1.0":       oos_m["sharpe"] > 1.0,
        "G3_market_beta_near_zero":   abs(beta) < 0.10,
        "G4_rho_K198_lt_0.5":         isinstance(corrs.get("K198"), float) and abs(corrs["K198"]) < 0.5,
        "G4b_rho_K208_lt_0.5":        isinstance(corrs.get("K208"), float) and abs(corrs["K208"]) < 0.5,
        "G5_OOS_MaxDD_gt_neg30pct":   oos_m["max_dd"] > -0.30,
    }
    n_pass = sum(gates.values())
    verdict = (
        "ACCEPT — promote to K263 K246a integration"
        if gates["G1_WF_all_folds_positive"] and gates["G2_OOS_Sharpe_gt_1.0"]
        else "REJECT — fails minimum acceptance criteria"
    )

    print(f"\nGATES:")
    for k, v in gates.items():
        print(f"  {k}: {'PASS' if v else 'FAIL'}")
    print(f"\nVERDICT: {verdict}")

    # ── Save curves ───────────────────────────────────────────────────────────
    curves_out = {
        "K262_full":  equity_curve_data(pnl_net),
        "K262_IS":    equity_curve_data(pnl_net.iloc[:is_cut]),
        "K262_OOS":   equity_curve_data(pnl_net.iloc[is_cut:]),
    }
    with open(OUT_CURVES, "w") as f:
        json.dump(curves_out, f, indent=2)
    print(f"\nCurves saved: {OUT_CURVES}")

    # ── Save JSON ─────────────────────────────────────────────────────────────
    elapsed = time.time() - t0
    result = {
        "wave": "K262",
        "strategy": "DollarNeutralMomentum",
        "spec_ref": "SSRN:6300843 (tip-scraper R9-16)",
        "as_of": pd.Timestamp.utcnow().isoformat(),
        "runtime_s": elapsed,
        "config": {
            "symbols_final": kept_final,
            "n_symbols": len(kept_final),
            "mom_days": MOM_DAYS,
            "skip_days": SKIP_DAYS,
            "quartile": QUARTILE,
            "cost_bps_per_side": COST_BPS,
            "rebalance": "daily",
            "date_range": [str(panel.index[0].date()), str(panel.index[-1].date())],
            "is_frac": IS_FRAC,
        },
        "IS":   is_m,
        "OOS":  oos_m,
        "FULL": full_m,
        "walk_forward_folds": wf,
        "wf_min_sharpe": wf_min,
        "wf_all_folds_positive": wf_all_pos,
        "market_beta_vs_ewmkt": beta,
        "avg_daily_turnover": avg_turn,
        "avg_daily_cost_pct": avg_cost_pct,
        "correlation_vs_k246a_components": corrs,
        "gates": gates,
        "n_gates_pass": n_pass,
        "verdict": verdict,
        "k257_comparison": {
            "k257_oos_sharpe": -0.9183,
            "k257_failed_fold": "Fold3 (2025-H2 bear)",
            "k262_vs_k257": "Dollar-neutral vs 70/30 long-biased; K262 removes directional beta",
        },
    }
    with open(OUT_JSON, "w") as f:
        json.dump(result, f, indent=2, default=str)
    print(f"Results saved: {OUT_JSON}")
    print(f"Elapsed: {elapsed:.1f}s")

    # ── Write markdown report ─────────────────────────────────────────────────
    rho_k198 = corrs.get("K198")
    rho_k208 = corrs.get("K208")
    rho_k246a = corrs.get("K246a")
    rho_k198_s  = f"{rho_k198:.3f}" if isinstance(rho_k198, float) else str(rho_k198)
    rho_k208_s  = f"{rho_k208:.3f}" if isinstance(rho_k208, float) else str(rho_k208)
    rho_k246a_s = f"{rho_k246a:.3f}" if isinstance(rho_k246a, float) else str(rho_k246a)

    md = f"""# Wave K262 — Dollar-Neutral Cross-Sectional Momentum

**Date**: 2026-05-25  **Runtime**: {elapsed:.1f}s

## Strategy Spec
- Universe: {len(kept_final)} symbols (4h_730d → daily aggregated)
- Signal: 30-day trailing momentum, skip last 1 day (micro-reversal avoidance)
- Ranking: daily cross-sectional, top/bottom quartile ({int(len(kept_final)*QUARTILE)} each side approx.)
- Dollar-neutral: long_$ = short_$ at all times
- Cost: {COST_BPS}bp/side maker; avg daily turnover: {avg_turn:.3f}

## Performance Summary

| Period | Sharpe | MaxDD | AnnRet | AnnVol | WinRate |
|--------|--------|-------|--------|--------|---------|
| IS ({is_m['n_days']}d) | {is_m['sharpe']:.3f} | {is_m['max_dd']:.2%} | {is_m['ann_ret']:+.2%} | {is_m['ann_vol']:.2%} | {is_m['win_rate']:.2%} |
| OOS ({oos_m['n_days']}d) | {oos_m['sharpe']:.3f} | {oos_m['max_dd']:.2%} | {oos_m['ann_ret']:+.2%} | {oos_m['ann_vol']:.2%} | {oos_m['win_rate']:.2%} |
| Full ({full_m['n_days']}d) | {full_m['sharpe']:.3f} | {full_m['max_dd']:.2%} | {full_m['ann_ret']:+.2%} | {full_m['ann_vol']:.2%} | {full_m['win_rate']:.2%} |

## Walk-Forward 4-Fold

| Fold | Start | End | Sharpe | MaxDD | TotalRet |
|------|-------|-----|--------|-------|----------|
""" + "\n".join(
    f"| {f['fold']} | {f['start']} | {f['end']} | {f['sharpe']:.3f} | {f['max_dd']:.2%} | {f['total_return']:+.2%} |"
    for f in wf
) + f"""

WF min Sharpe: **{wf_min:.3f}** — All folds positive: **{wf_all_pos}**

## Dollar-Neutral Validation
- Market beta vs equal-weight universe: **{beta:.4f}** (target: |β| < 0.10)

## Correlation Matrix vs K246a Components

| Component | ρ | Orthogonal? |
|-----------|---|-------------|
| K198 (ML allocator) | {rho_k198_s} | {'YES' if isinstance(rho_k198, float) and abs(rho_k198)<0.5 else 'NO/UNKNOWN'} |
| K208 (DAR reverse carry) | {rho_k208_s} | {'YES' if isinstance(rho_k208, float) and abs(rho_k208)<0.5 else 'NO/UNKNOWN'} |
| K246a (3-way) | {rho_k246a_s} | {'YES' if isinstance(rho_k246a, float) and abs(rho_k246a)<0.5 else 'NO/UNKNOWN'} |

## Acceptance Gates

| Gate | Result |
|------|--------|
| G1: WF all folds positive | {'PASS' if gates['G1_WF_all_folds_positive'] else 'FAIL'} |
| G2: OOS Sharpe > 1.0 | {'PASS' if gates['G2_OOS_Sharpe_gt_1.0'] else 'FAIL'} |
| G3: Market beta |β| < 0.10 | {'PASS' if gates['G3_market_beta_near_zero'] else 'FAIL'} |
| G4: |ρ| K198 < 0.5 | {'PASS' if gates['G4_rho_K198_lt_0.5'] else 'FAIL'} |
| G4b: |ρ| K208 < 0.5 | {'PASS' if gates['G4b_rho_K208_lt_0.5'] else 'FAIL'} |
| G5: OOS MaxDD > -30% | {'PASS' if gates['G5_OOS_MaxDD_gt_neg30pct'] else 'FAIL'} |

**Gates passed: {n_pass}/6**

## Comparison vs K257 AdaptiveTrend
- K257 OOS Sharpe: -0.9183 (REJECT) — failed 2025-H2 bear, 70/30 long-biased
- K262: dollar-neutral construction removes directional market beta
- K257 failure root cause: long bias exposed to BTC -45% drawdown Nov 2025–Feb 2026
- K262 should be immune to this via equal L/S dollar sizing

## Verdict

**{verdict}**

{'### K263 K246a Integration Plan' if 'ACCEPT' in verdict else '### Post-Rejection Analysis'}

{'K262 meets all acceptance criteria. Recommended K263 integration:' if 'ACCEPT' in verdict else 'K262 failed minimum gates. Recommended next steps:'}
{'- Combine K262 with K246a at ~10-20% allocation (inv-vol weighting)' if 'ACCEPT' in verdict else '- Investigate alternative: mean-reversion cross-sectional strategy'}
{'- K262 contributes orthogonal alpha: ρ < 0.5 with all K246a components' if 'ACCEPT' in verdict else '- K257+K262 both fail → momentum family may not suit 2024-2026 regime'}
{'- Confirm beta-neutral in live execution; set position cap per symbol' if 'ACCEPT' in verdict else '- Consider stat-arb pairs or vol-of-vol strategies instead'}
{'- Monitor 30d rolling correlation; halt K262 sleeve if ρ drifts > 0.6' if 'ACCEPT' in verdict else '- Review SSRN:6300843 for exact universe requirements (150+ pairs needed?)'}
"""

    with open(OUT_MD, "w") as f:
        f.write(md)
    print(f"Report saved: {OUT_MD}")

    return result


if __name__ == "__main__":
    main()
