"""Wave K171 - Cross-Chain Negative Spillover (R5-5).

Hypothesis (arxiv 2602.23762): When token A surges (large positive return),
same-chain token B reverses (negative return). Capital rotates within L1
ecosystems.

Method (pre-registered):
  1. Per 4H bar, compute 24h log return per symbol (rolling 6 bars).
  2. Within each chain, identify "surge" symbol = max trailing 24h return.
  3. If surge return > threshold:
       LONG surge symbol (continue momentum)
       SHORT equal-weight basket of other same-chain symbols (rotation away)
  4. Hold for N bars (24h = 6 bars).
  5. Costs: 0.07% per side per leg (entry+exit).

Variants:
  - V_5pct_h24   (primary): 5% threshold, 24h hold
  - V_3pct_h12             : 3% threshold, 12h hold
  - V_10pct_h48            : 10% threshold, 48h hold
  - V_eth_ecosystem_only   : ETH chain only

Audit: WF 4-fold, perm n=200, bootstrap n=200, DSR. Cost 7bps/side/leg.
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


def chain_signals(
    log_ret: pd.DataFrame,
    chain_syms: List[str],
    threshold: float,
    lookback_bars: int,
    hold_bars: int,
) -> pd.DataFrame:
    """For one chain, generate per-bar pnl from (LONG surge, SHORT others).

    Returns DataFrame indexed by time with column 'pnl' (gross of any further cost
    adjustment - costs already baked in).
    """
    syms_in_chain = [s for s in chain_syms if s in log_ret.columns]
    if len(syms_in_chain) < 2:
        return pd.DataFrame(index=log_ret.index, columns=["pnl"], data=0.0)

    sub = log_ret[syms_in_chain]
    # trailing lookback-bar cumulative log return
    trail = sub.rolling(lookback_bars).sum()

    pnl = pd.Series(0.0, index=sub.index)
    trades = 0
    bar_indices = np.arange(len(sub))
    times = sub.index

    # iterate forward; if surge > threshold at t, open at t->t+1 close, hold hold_bars
    # We compute realized pnl per entry distributed over the hold window for capital
    # accounting simplicity: assign full pnl at entry bar's t (already-known signal).
    # To avoid look-ahead: use trail computed at bar t (closes up to t), enter at next bar.
    next_log_ret = sub.shift(-1)  # log return realized in bar t+1

    # Robust to all-NaN rows
    all_nan = trail.isna().all(axis=1)
    surge_sym = pd.Series(index=trail.index, dtype=object)
    surge_val = pd.Series(index=trail.index, dtype=float)
    nz = trail[~all_nan]
    if len(nz) > 0:
        surge_sym.loc[nz.index] = nz.idxmax(axis=1, skipna=True)
        surge_val.loc[nz.index] = nz.max(axis=1, skipna=True)
    valid = surge_val.fillna(-np.inf) > threshold

    held_until = -1  # last bar index of current hold (exclusive end)
    current_long: Optional[str] = None
    current_shorts: List[str] = []
    entry_t: Optional[int] = None

    for i in range(len(sub) - 1):
        if i >= held_until:
            # position closed - check new signal at bar i (entry at i+1)
            if valid.iloc[i]:
                long_sym = surge_sym.iloc[i]
                short_syms = [s for s in syms_in_chain if s != long_sym]
                if not short_syms:
                    continue
                current_long = long_sym
                current_shorts = short_syms
                entry_t = i
                held_until = i + hold_bars
                trades += 1
                # entry cost: long 1 leg + short basket (1 unit total = N short positions
                # each weight 1/N, but costs are per-asset). Conservative: count basket
                # as 1 "leg" -> entry costs = 2 legs * COST_BPS at entry.
                # Per task: "0.07% per side per leg" -> entry has 2 legs (long+short).
                pnl.iloc[i + 1] -= 2.0 * COST_BPS
        # accrue pnl while position open at bar i+1 (i.e., open during bar i+1)
        if current_long is not None and (i + 1) <= held_until and i >= (entry_t or 0):
            long_r = next_log_ret[current_long].iloc[i]
            short_r = next_log_ret[current_shorts].iloc[i].mean()
            if not (np.isnan(long_r) or np.isnan(short_r)):
                pnl.iloc[i + 1] += long_r - short_r
            # exit cost at hold end
            if (i + 1) == held_until:
                pnl.iloc[i + 1] -= 2.0 * COST_BPS
                current_long = None
                current_shorts = []
                entry_t = None

    return pd.DataFrame({"pnl": pnl, "n_trades": [trades] * len(pnl)}, index=sub.index)


def run_variant(
    log_ret: pd.DataFrame,
    chain_set: Dict[str, List[str]],
    threshold: float,
    lookback_bars: int,
    hold_bars: int,
) -> Tuple[pd.Series, int]:
    """Aggregate pnl across chains (equal weight across active chains)."""
    pnls = []
    total_trades = 0
    for chain_name, syms in chain_set.items():
        if len([s for s in syms if s in log_ret.columns]) < 2:
            continue
        out = chain_signals(log_ret, syms, threshold, lookback_bars, hold_bars)
        pnls.append(out["pnl"])
        total_trades += int(out["n_trades"].iloc[0])
    if not pnls:
        return pd.Series(0.0, index=log_ret.index), 0
    agg = pd.concat(pnls, axis=1).mean(axis=1)  # equal-weight chain
    return agg, total_trades


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


def perm_test(pnl: pd.Series, n: int = 200, seed: int = 7) -> float:
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


def bootstrap_ci(pnl: pd.Series, n: int = 200, seed: int = 11) -> Tuple[float, float]:
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
    """Deflated Sharpe ratio approximation (Bailey & Lopez de Prado)."""
    pnl = pnl.dropna()
    if len(pnl) < 30 or pnl.std() == 0:
        return 0.0
    sr = pnl.mean() / pnl.std()
    T = len(pnl)
    # skew/kurt
    sk = float(((pnl - pnl.mean()) ** 3).mean() / (pnl.std() ** 3 + 1e-12))
    kt = float(((pnl - pnl.mean()) ** 4).mean() / (pnl.std() ** 4 + 1e-12))
    # expected max sharpe under null
    emc = 0.5772
    e_max = np.sqrt(2 * np.log(max(n_trials, 2))) - emc / np.sqrt(2 * np.log(max(n_trials, 2)))
    denom = np.sqrt((1 - sk * sr + (kt - 1) / 4 * sr ** 2) / (T - 1))
    if denom <= 0:
        return 0.0
    z = (sr - e_max) / denom
    # CDF
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


def report_variant(name: str, pnl: pd.Series, n_trades: int) -> Dict:
    sh = sharpe(pnl)
    cg = cagr(pnl)
    dd = max_dd(pnl)
    # IS/OOS 70/30
    split = int(len(pnl) * 0.7)
    is_pnl = pnl.iloc[:split]
    oos_pnl = pnl.iloc[split:]
    is_sh = sharpe(is_pnl)
    oos_sh = sharpe(oos_pnl)
    wf_mean, wf_folds = wf_4fold(pnl)
    perm_p = perm_test(pnl)
    ci_lo, ci_hi = bootstrap_ci(pnl)
    dsr_p = dsr(pnl, n_trials=4)
    to = turnover(pnl, n_trades)
    return {
        "variant": name,
        "sharpe": round(sh, 4),
        "cagr": round(cg, 4),
        "max_dd": round(dd, 4),
        "is_sharpe": round(is_sh, 4),
        "oos_sharpe": round(oos_sh, 4),
        "wf_mean_sharpe": round(wf_mean, 4),
        "wf_folds": [round(x, 4) for x in wf_folds],
        "perm_pvalue": round(perm_p, 4),
        "bootstrap_ci_5_95": [round(ci_lo, 4), round(ci_hi, 4)],
        "dsr": round(dsr_p, 4),
        "n_trades": int(n_trades),
        "trades_per_year": round(to, 2),
        "n_bars": int(len(pnl)),
    }


# ---------- Main ----------


def main() -> Dict:
    t0 = time.time()
    all_syms = sorted({s for syms in CHAINS.values() for s in syms})
    panel = load_panel(all_syms)
    log_ret = make_log_returns(panel)
    # restrict to bars where ETH/BTC present
    log_ret = log_ret.dropna(how="all")
    print(f"Panel shape: {panel.shape}, log_ret: {log_ret.shape}")
    print(f"Symbols loaded: {len(panel.columns)}")

    # surge frequency diagnostic (whole universe, 24h trailing)
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
    for name, thr, lb, hold, chain_set in variants_cfg:
        pnl, n_tr = run_variant(log_ret, chain_set, thr, lb, hold)
        rep = report_variant(name, pnl, n_tr)
        results.append(rep)
        curves[name] = {
            "equity": equity_curve(pnl),
            "timestamps": [t.isoformat() for t in pnl.index],
        }
        print(
            f"{name:30s} Sharpe={rep['sharpe']:+.2f}  CAGR={rep['cagr']:+.3f}  "
            f"OOS={rep['oos_sharpe']:+.2f}  perm_p={rep['perm_pvalue']:.3f}  "
            f"DSR={rep['dsr']:.3f}  trades={rep['n_trades']}"
        )

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

    summary = {
        "wave": "K171",
        "hypothesis": "cross-chain negative spillover after surge",
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
        "gates_primary": gates,
        "gates_passed": gates_passed,
        "verdict": verdict,
        "runtime_sec": round(time.time() - t0, 1),
    }

    out_json = ROOT / "wave_k171_xchain_spillover.json"
    out_curves = ROOT / "wave_k171_curves.json"
    out_json.write_text(json.dumps(summary, indent=2))
    out_curves.write_text(json.dumps(curves))
    print(f"\nWrote {out_json}  ({out_json.stat().st_size} bytes)")
    print(f"Wrote {out_curves} ({out_curves.stat().st_size} bytes)")
    print(f"Verdict: {verdict}  ({gates_passed}/7 gates)")
    print(f"Runtime: {summary['runtime_sec']}s")
    return summary


if __name__ == "__main__":
    main()
