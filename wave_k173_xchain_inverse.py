"""Wave K173 - Same-Chain CO-MOVEMENT (Inverse of K171).

Hypothesis: K171 (LONG surge, SHORT same-chain basket) was REJECT with
perm p=0.000 in WRONG direction (Sh -1.38 primary). The INVERSE direction
should target Sh ~+1.38 with same statistical significance:

  After +5% 24h surge in chain:
    SHORT surge symbol (mean revert)
    LONG equal-weight basket of other same-chain symbols (co-movement)

This mirrors the K131->K133 pattern (flipped sign of REJECT REJECT
hypothesis).

Method (pre-registered):
  1. Per 4H bar, compute 24h log return per symbol (rolling 6 bars).
  2. Within each chain, identify "surge" symbol = max trailing 24h return.
  3. If surge return > threshold:
       SHORT surge symbol (mean revert)
       LONG equal-weight basket of other same-chain symbols
  4. Hold for N bars (24h = 6 bars).
  5. Costs: 0.07% per side per leg (entry+exit).

Variants:
  - V_5pct_h24   (primary, K171 direct inverse): 5% threshold, 24h hold
  - V_3pct_h12             : 3% threshold, 12h hold
  - V_10pct_h48            : 10% threshold, 48h hold
  - V_eth_ecosystem_only   : ETH chain only

Audit: WF 4-fold, perm n=300, bootstrap n=300, DSR. Cost 7bps/side/leg.

Correlation: vs K124-cached daily series of K149 ensemble members
(v4.1, V1, K114, K116, K121) plus K133, K147 reload.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

ROOT = Path("/Users/nekonaomichi/crypto-lab")
CACHE = ROOT / "cache"
COST_BPS = 0.0007  # 7 bps per side per leg

# Same chains as K171 (same available cached symbols)
CHAINS: Dict[str, List[str]] = {
    "ETH": ["ETH", "ARB", "OP", "LDO", "AAVE", "UNI", "GRT", "SNX", "ENA"],
    "SOL": ["SOL", "JTO", "JUP", "WIF", "BONK", "BOME", "PYTH", "RENDER"],
    "BNB": ["BNB"],  # CAKE missing
    "BTC": ["BTC", "RUNE"],  # ORDI missing
    "ALT": ["ADA", "DOT", "AVAX", "NEAR", "ATOM", "LINK", "XRP", "DOGE", "SHIB", "PEPE"],
}


def load_close(sym: str) -> Optional[pd.Series]:
    f = CACHE / f"{sym}USDT_4h_730d.parquet"
    if not f.exists():
        return None
    df = pd.read_parquet(f)
    s = df.set_index("open_time")["close"].astype(float).sort_index()
    s.name = sym
    s = s[~s.index.duplicated(keep="last")]
    return s


def load_panel(syms: List[str]) -> pd.DataFrame:
    cols = []
    for s in syms:
        cs = load_close(s)
        if cs is not None and len(cs) > 1000:
            cols.append(cs)
    panel = pd.concat(cols, axis=1).sort_index()
    return panel


def make_log_returns(panel: pd.DataFrame) -> pd.DataFrame:
    return np.log(panel).diff()


def chain_signals_inverse(
    log_ret: pd.DataFrame,
    chain_syms: List[str],
    threshold: float,
    lookback_bars: int,
    hold_bars: int,
) -> pd.DataFrame:
    """For one chain, generate per-bar pnl from (SHORT surge, LONG basket).

    This is K171 with sign flipped: pnl = long_basket_avg - short_surge.
    Returns both gross (no cost) and net (with cost) pnl.
    """
    syms_in_chain = [s for s in chain_syms if s in log_ret.columns]
    if len(syms_in_chain) < 2:
        return pd.DataFrame(
            index=log_ret.index, columns=["pnl", "pnl_gross", "n_trades"], data=0.0
        )

    sub = log_ret[syms_in_chain]
    trail = sub.rolling(lookback_bars).sum()

    pnl_net = pd.Series(0.0, index=sub.index)
    pnl_gross = pd.Series(0.0, index=sub.index)
    trades = 0
    next_log_ret = sub.shift(-1)

    all_nan = trail.isna().all(axis=1)
    surge_sym = pd.Series(index=trail.index, dtype=object)
    surge_val = pd.Series(index=trail.index, dtype=float)
    nz = trail[~all_nan]
    if len(nz) > 0:
        surge_sym.loc[nz.index] = nz.idxmax(axis=1, skipna=True)
        surge_val.loc[nz.index] = nz.max(axis=1, skipna=True)
    valid = surge_val.fillna(-np.inf) > threshold

    held_until = -1
    current_short: Optional[str] = None  # symbol being SHORTED (the surger)
    current_longs: List[str] = []        # basket LONGED (co-movement)
    entry_t: Optional[int] = None

    for i in range(len(sub) - 1):
        if i >= held_until:
            if valid.iloc[i]:
                surge = surge_sym.iloc[i]
                long_syms = [s for s in syms_in_chain if s != surge]
                if not long_syms:
                    continue
                current_short = surge
                current_longs = long_syms
                entry_t = i
                held_until = i + hold_bars
                trades += 1
                # 2 legs (short surger + long basket): 2 * COST at entry
                pnl_net.iloc[i + 1] -= 2.0 * COST_BPS
        if current_short is not None and (i + 1) <= held_until and i >= (entry_t or 0):
            short_r = next_log_ret[current_short].iloc[i]
            long_r = next_log_ret[current_longs].iloc[i].mean()
            if not (np.isnan(short_r) or np.isnan(long_r)):
                gross = long_r - short_r
                pnl_net.iloc[i + 1] += gross
                pnl_gross.iloc[i + 1] += gross
            if (i + 1) == held_until:
                pnl_net.iloc[i + 1] -= 2.0 * COST_BPS
                current_short = None
                current_longs = []
                entry_t = None

    return pd.DataFrame(
        {"pnl": pnl_net, "pnl_gross": pnl_gross, "n_trades": [trades] * len(pnl_net)},
        index=sub.index,
    )


def run_variant(
    log_ret: pd.DataFrame,
    chain_set: Dict[str, List[str]],
    threshold: float,
    lookback_bars: int,
    hold_bars: int,
) -> Tuple[pd.Series, pd.Series, int, Dict[str, float], Dict[str, float]]:
    """Aggregate pnl across chains (equal weight). Returns (net, gross, n_trades, per_chain_net_sh, per_chain_gross_sh)."""
    pnls_net = []
    pnls_gross = []
    total_trades = 0
    per_chain_sh: Dict[str, float] = {}
    per_chain_gross_sh: Dict[str, float] = {}
    for chain_name, syms in chain_set.items():
        if len([s for s in syms if s in log_ret.columns]) < 2:
            continue
        out = chain_signals_inverse(log_ret, syms, threshold, lookback_bars, hold_bars)
        pnls_net.append(out["pnl"].rename(chain_name))
        pnls_gross.append(out["pnl_gross"].rename(chain_name))
        total_trades += int(out["n_trades"].iloc[0])
        per_chain_sh[chain_name] = sharpe(out["pnl"])
        per_chain_gross_sh[chain_name] = sharpe(out["pnl_gross"])
    if not pnls_net:
        return pd.Series(0.0, index=log_ret.index), pd.Series(0.0, index=log_ret.index), 0, {}, {}
    df_net = pd.concat(pnls_net, axis=1)
    df_gross = pd.concat(pnls_gross, axis=1)
    return df_net.mean(axis=1), df_gross.mean(axis=1), total_trades, per_chain_sh, per_chain_gross_sh


# ---------- Metrics ----------


def sharpe(pnl: pd.Series, ppy: int = 6 * 365) -> float:
    pnl = pnl.dropna()
    if pnl.std() == 0 or len(pnl) < 30:
        return 0.0
    return float(pnl.mean() / pnl.std() * np.sqrt(ppy))


def cagr(pnl: pd.Series, ppy: int = 6 * 365) -> float:
    if len(pnl) == 0:
        return 0.0
    total = pnl.sum()
    years = len(pnl) / ppy
    if years <= 0:
        return 0.0
    return float(np.expm1(total / years))


def max_dd(pnl: pd.Series) -> float:
    eq = pnl.cumsum()
    peak = eq.cummax()
    dd = eq - peak
    return float(dd.min())


def equity_curve(pnl: pd.Series) -> List[float]:
    return list(np.exp(pnl.fillna(0).cumsum()).round(6))


def perm_test(pnl: pd.Series, n: int = 300, seed: int = 7) -> float:
    rng = np.random.default_rng(seed)
    obs = sharpe(pnl)
    vals = pnl.dropna().values
    if len(vals) < 10 or pnl.std() == 0:
        return 1.0
    perm_sharpes = []
    for _ in range(n):
        shuf = rng.permutation(vals)
        s = pd.Series(shuf)
        sh = s.mean() / (s.std() + 1e-12) * np.sqrt(6 * 365)
        perm_sharpes.append(sh)
    perm_sharpes = np.array(perm_sharpes)
    if obs > 0:
        p = float((perm_sharpes >= obs).mean())
    else:
        p = float((perm_sharpes <= obs).mean())
    return p


def bootstrap_ci(pnl: pd.Series, n: int = 300, seed: int = 11) -> Tuple[float, float]:
    rng = np.random.default_rng(seed)
    vals = pnl.dropna().values
    if len(vals) < 30:
        return (0.0, 0.0)
    sharpes = []
    for _ in range(n):
        idx = rng.integers(0, len(vals), size=len(vals))
        s = pd.Series(vals[idx])
        sh = s.mean() / (s.std() + 1e-12) * np.sqrt(6 * 365)
        sharpes.append(sh)
    return float(np.percentile(sharpes, 5)), float(np.percentile(sharpes, 95))


def dsr(pnl: pd.Series, n_trials: int = 4) -> float:
    pnl = pnl.dropna()
    if len(pnl) < 30 or pnl.std() == 0:
        return 0.0
    sr = pnl.mean() / pnl.std()
    T = len(pnl)
    sk = float(((pnl - pnl.mean()) ** 3).mean() / (pnl.std() ** 3 + 1e-12))
    kt = float(((pnl - pnl.mean()) ** 4).mean() / (pnl.std() ** 4 + 1e-12))
    emc = 0.5772
    e_max = np.sqrt(2 * np.log(max(n_trials, 2))) - emc / np.sqrt(2 * np.log(max(n_trials, 2)))
    denom = np.sqrt((1 - sk * sr + (kt - 1) / 4 * sr ** 2) / (T - 1))
    if denom <= 0:
        return 0.0
    z = (sr - e_max) / denom
    from math import erf, sqrt
    return float(0.5 * (1 + erf(z / sqrt(2))))


def wf_4fold(pnl: pd.Series) -> Tuple[float, List[float]]:
    pnl = pnl.dropna()
    if len(pnl) < 100:
        return 0.0, []
    folds = np.array_split(pnl.values, 4)
    sharpes = []
    for f in folds:
        s = pd.Series(f)
        if s.std() == 0:
            sharpes.append(0.0)
            continue
        sharpes.append(float(s.mean() / s.std() * np.sqrt(6 * 365)))
    return float(np.mean(sharpes)), [float(x) for x in sharpes]


def turnover(pnl: pd.Series, n_trades: int) -> float:
    if len(pnl) == 0:
        return 0.0
    bars_per_year = 6 * 365
    years = len(pnl) / bars_per_year
    return float(n_trades / max(years, 1e-6))


def cost_stress(pnl_gross: pd.Series, n_trades: int, base_cost: float = COST_BPS) -> Dict:
    """Sensitivity to cost (entry+exit, 2 legs each side)."""
    # gross_pnl already has cost baked at 7bps. recover gross by adding back
    # 2 legs * cost at entry + 2 legs * cost at exit per trade = 4*cost*n_trades total.
    pnl_addback = 4.0 * base_cost * n_trades
    # but distributed; compute simple sharpe at multiples by scaling the cost.
    out = {}
    for mult, label in [(1.0, "1x_baseline"), (1.5, "1p5x"), (2.0, "2x_double")]:
        delta_cost = (mult - 1.0) * 4.0 * base_cost * n_trades / max(len(pnl_gross), 1)
        adj = pnl_gross - delta_cost
        out[label] = round(sharpe(adj), 4)
    return out


def report_variant(
    name: str,
    pnl: pd.Series,
    pnl_gross: pd.Series,
    n_trades: int,
    per_chain_sh: Dict[str, float],
    per_chain_gross_sh: Dict[str, float],
) -> Dict:
    sh = sharpe(pnl)
    sh_gross = sharpe(pnl_gross)
    cg = cagr(pnl)
    dd = max_dd(pnl)
    split = int(len(pnl) * 0.7)
    is_pnl = pnl.iloc[:split]
    oos_pnl = pnl.iloc[split:]
    is_sh = sharpe(is_pnl)
    oos_sh = sharpe(oos_pnl)
    wf_mean, wf_folds = wf_4fold(pnl)
    perm_p = perm_test(pnl, n=300)
    perm_p_gross = perm_test(pnl_gross, n=300)
    ci_lo, ci_hi = bootstrap_ci(pnl, n=300)
    dsr_p = dsr(pnl, n_trials=4)
    to = turnover(pnl, n_trades)
    cs = cost_stress(pnl, n_trades)
    return {
        "variant": name,
        "sharpe": round(sh, 4),
        "sharpe_gross": round(sh_gross, 4),
        "cagr": round(cg, 4),
        "max_dd": round(dd, 4),
        "is_sharpe": round(is_sh, 4),
        "oos_sharpe": round(oos_sh, 4),
        "wf_mean_sharpe": round(wf_mean, 4),
        "wf_folds": [round(x, 4) for x in wf_folds],
        "perm_pvalue": round(perm_p, 4),
        "perm_pvalue_gross": round(perm_p_gross, 4),
        "bootstrap_ci_5_95": [round(ci_lo, 4), round(ci_hi, 4)],
        "dsr": round(dsr_p, 4),
        "n_trades": int(n_trades),
        "trades_per_year": round(to, 2),
        "n_bars": int(len(pnl)),
        "per_chain_sharpe": {k: round(v, 4) for k, v in per_chain_sh.items()},
        "per_chain_gross_sharpe": {k: round(v, 4) for k, v in per_chain_gross_sh.items()},
        "cost_stress": cs,
    }


# ---------- Correlation w/ existing strategies ----------


def load_k124_daily_series() -> pd.DataFrame:
    """Daily equity series for K149 ensemble members from K124 cache."""
    p = ROOT / "wave_k124_curves.json"
    if not p.exists():
        return pd.DataFrame()
    d = json.loads(p.read_text())
    dates = pd.to_datetime(d["dates"])
    series = d["series"]
    df = pd.DataFrame({k: pd.Series(v, index=dates) for k, v in series.items()})
    return df


def correlations_vs_existing(pnl_4h: pd.Series) -> Dict[str, float]:
    """Daily-aggregated correlation vs K149 ensemble members."""
    if pnl_4h.empty:
        return {}
    # resample 4h pnl to daily pnl
    daily_pnl = pnl_4h.resample("1D").sum()
    k124 = load_k124_daily_series()
    if k124.empty:
        return {}
    # k124 series are equity curves -> diff to get daily returns
    k124_ret = k124.pct_change().dropna(how="all")
    common_idx = daily_pnl.index.intersection(k124_ret.index)
    if len(common_idx) < 30:
        return {"_n_common_days": float(len(common_idx))}
    corrs = {}
    sub = daily_pnl.reindex(common_idx)
    for col in k124_ret.columns:
        rhs = k124_ret[col].reindex(common_idx)
        c = sub.corr(rhs)
        corrs[col] = round(float(c), 4) if pd.notna(c) else 0.0
    corrs["_n_common_days"] = float(len(common_idx))
    return corrs


# ---------- Main ----------


def main() -> Dict:
    t0 = time.time()
    all_syms = sorted({s for syms in CHAINS.values() for s in syms})
    panel = load_panel(all_syms)
    log_ret = make_log_returns(panel)
    log_ret = log_ret.dropna(how="all")
    print(f"Panel shape: {panel.shape}, log_ret: {log_ret.shape}")
    print(f"Symbols loaded: {len(panel.columns)}")

    trail24 = log_ret.rolling(6).sum()
    max_per_bar = trail24.max(axis=1)
    freq_5pct = float((max_per_bar > 0.05).mean())
    freq_3pct = float((max_per_bar > 0.03).mean())
    freq_10pct = float((max_per_bar > 0.10).mean())
    print(f"Surge freq (24h):  3%={freq_3pct:.3f}  5%={freq_5pct:.3f}  10%={freq_10pct:.3f}")

    variants_cfg = [
        ("V_5pct_h24", 0.05, 6, 6, CHAINS),
        ("V_3pct_h12", 0.03, 6, 3, CHAINS),
        ("V_10pct_h48", 0.10, 6, 12, CHAINS),
        ("V_eth_ecosystem_only", 0.05, 6, 6, {"ETH": CHAINS["ETH"]}),
    ]

    results = []
    curves = {}
    primary_pnl = None
    primary_pnl_gross = None
    for name, thr, lb, hold, chain_set in variants_cfg:
        pnl, pnl_gross, n_tr, per_chain, per_chain_gross = run_variant(
            log_ret, chain_set, thr, lb, hold
        )
        rep = report_variant(name, pnl, pnl_gross, n_tr, per_chain, per_chain_gross)
        results.append(rep)
        curves[name] = {
            "equity": equity_curve(pnl),
            "equity_gross": equity_curve(pnl_gross),
            "timestamps": [t.isoformat() for t in pnl.index],
        }
        if name == "V_5pct_h24":
            primary_pnl = pnl
            primary_pnl_gross = pnl_gross
        print(
            f"{name:30s} Sh_net={rep['sharpe']:+.2f}  Sh_gross={rep['sharpe_gross']:+.2f}  "
            f"OOS={rep['oos_sharpe']:+.2f}  perm_p={rep['perm_pvalue']:.3f}  "
            f"trades={rep['n_trades']}"
        )

    # Correlations vs existing strategies
    corrs = correlations_vs_existing(primary_pnl) if primary_pnl is not None else {}

    primary = results[0]
    gates = {
        "g1_sharpe_ge_1": primary["sharpe"] >= 1.0,
        "g2_oos_sharpe_ge_0p5": primary["oos_sharpe"] >= 0.5,
        "g3_oos_vs_is_ratio_ge_0p5": (
            primary["oos_sharpe"] / primary["is_sharpe"] >= 0.5
            if primary["is_sharpe"] > 0
            else False
        ),
        "g4_wf_folds_all_positive": all(x > 0 for x in primary["wf_folds"]),
        "g5_perm_p_le_0p05": primary["perm_pvalue"] <= 0.05,
        "g6_dsr_ge_0p95": primary["dsr"] >= 0.95,
        "g7_trades_per_year_ge_20": primary["trades_per_year"] >= 20,
    }
    gates_passed = sum(gates.values())
    verdict = "PASS" if gates_passed >= 6 else ("MARGINAL" if gates_passed >= 4 else "FAIL")

    # K171 inverse check: primary Sh should be +ve and ~ +1.38 (mirror)
    k171_primary_sh = -1.3819  # from cached K171 result (net of costs)
    # Costs are direction-symmetric: both K171 and K173 pay the same costs.
    # GROSS K173 = -GROSS K171 by construction. Net differs because both
    # incur identical cost drag. Truer K171-inverse hypothesis: gross Sh > 0.
    inverse_check = {
        "k171_primary_sharpe_net": k171_primary_sh,
        "k173_primary_sharpe_net": primary["sharpe"],
        "k173_primary_sharpe_gross": primary["sharpe_gross"],
        "expected_mirror_sharpe_net": round(-k171_primary_sh, 4),
        "sign_flipped_net": primary["sharpe"] > 0,
        "sign_flipped_gross": primary["sharpe_gross"] > 0,
        "mirror_residual_net": round(primary["sharpe"] - (-k171_primary_sh), 4),
        "mirror_within_0p3_net": abs(primary["sharpe"] - (-k171_primary_sh)) <= 0.3,
        "note": (
            "Costs are direction-symmetric (~28bps round-trip x trades/yr). "
            "Both K171 and K173 NET are dragged by same cost. GROSS sign should flip."
        ),
    }

    summary = {
        "wave": "K173",
        "hypothesis": "same-chain co-movement after surge (K171 inverse)",
        "data": {
            "tf": "4h",
            "lookback_days": 730,
            "n_symbols": len(panel.columns),
            "symbols": list(panel.columns),
            "chains": {k: [s for s in v if s in panel.columns] for k, v in CHAINS.items()},
            "n_bars": int(len(log_ret)),
        },
        "surge_frequency": {
            "thr_3pct": round(freq_3pct, 4),
            "thr_5pct": round(freq_5pct, 4),
            "thr_10pct": round(freq_10pct, 4),
        },
        "variants": results,
        "k171_inverse_check": inverse_check,
        "correlations_vs_k149_members": corrs,
        "gates_primary": gates,
        "gates_passed": gates_passed,
        "verdict": verdict,
        "runtime_sec": round(time.time() - t0, 1),
    }

    out_json = ROOT / "wave_k173_xchain_inverse.json"
    out_curves = ROOT / "wave_k173_curves.json"
    out_json.write_text(json.dumps(summary, indent=2))
    out_curves.write_text(json.dumps(curves))
    print(f"\nWrote {out_json}  ({out_json.stat().st_size} bytes)")
    print(f"Wrote {out_curves} ({out_curves.stat().st_size} bytes)")
    print(f"K171 inverse: K171_net={k171_primary_sh:+.3f} -> K173_net={primary['sharpe']:+.3f}  "
          f"K173_gross={primary['sharpe_gross']:+.3f}")
    print(f"Verdict: {verdict}  ({gates_passed}/7 gates)")
    print(f"Runtime: {summary['runtime_sec']}s")
    return summary


if __name__ == "__main__":
    main()
