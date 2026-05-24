"""Wave K175 - K174 Salvage: XRP/SUI + Maker-Only Execution.

Hypothesis carry-over (MDPI 14/2/346):
  K174 confirmed CEX (Bybit) -> DEX (HL) FR integration mean-beta ~ 0.61.
  GROSS edge was REAL but small (V_z2_h1 Sharpe_gross = +0.19) and net-killed
  by 28 bps round-trip taker cost. Per-symbol audit showed XRP (+1.46 gross,
  +1.13 net) and SUI (+0.90 gross, +0.71 net) carried essentially ALL of the
  positive signal. Other 6 symbols were near-zero / negative.

K175 hypothesis:
  Restricting to XRP+SUI AND switching to a maker-only execution model
  (post-only limit fills near top-of-book) reduces round-trip cost from
  ~14bps/side*2 = 28bps to ~2bps/side*2 = 8bps. Combined with the symbol
  filter the strategy should clear the gross-to-net cliff.

Cost model (maker-only):
  - Maker fee:      0 bps (assume worst-case; Bybit VIP often pays rebate)
  - Slippage:       2 bps per side (tight post-only on liquid XRP/SUI perps)
  - Round-trip per leg = entry (2bp) + exit (2bp) = 4 bps
  - Total cost per trade (single-leg perp) = 4 bps  (vs K174 14 bps)

Variants (pre-registered):
  V_xrp_sui_maker      : XRP+SUI panel, z>2, hold=1   PRIMARY
  V_xrp_only           : XRP alone, z>2, hold=1
  V_sui_only           : SUI alone, z>2, hold=1
  V_xrp_sui_maker_h3   : XRP+SUI panel, z>2, hold=3

Audit: IS/OOS 70/30, WF 3-fold, perm n=200, bootstrap n=200,
       DSR (N_trials=4 same as K174 universe choices), cost stress
       at 3bp / 8bp / 14bp round-trip levels.

REPORT GROSS AND NET (K173 lesson).
"""
from __future__ import annotations

import json
import time
from math import erf, sqrt
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

ROOT = Path("/Users/nekonaomichi/crypto-lab")
CACHE = ROOT / "cache"
HL_CACHE = CACHE / "k163_hl"

# Maker-only execution cost model.
# Single-leg perp: cost charged once per fill -> entry + exit = round-trip.
# Round-trip total in bps = 2 * SLIPPAGE_PER_SIDE_BPS (+ maker fee = 0).
SLIPPAGE_BPS_PER_SIDE = 2.0
MAKER_FEE_BPS_PER_SIDE = 0.0
COST_PER_FILL = (SLIPPAGE_BPS_PER_SIDE + MAKER_FEE_BPS_PER_SIDE) * 1e-4  # 0.0002

# K174 taker comparator: 14 bps per fill (entry+exit -> 28 bps round-trip).
COST_PER_FILL_K174 = 0.0007  # for "vs K174 same window" comparison

SYMBOLS = ["XRP", "SUI"]

# 8h Bybit funding cadence
EVENTS_PER_YEAR = 365 * 24 // 8  # 1095


# ------------------------------ Data load ------------------------------


def load_hl_fr(sym: str) -> Optional[pd.Series]:
    f = HL_CACHE / f"hl_fr_{sym}.parquet"
    if not f.exists():
        return None
    df = pd.read_parquet(f)
    s = df.set_index("timestamp")["hl_fr"].astype(float).sort_index()
    s = s[~s.index.duplicated(keep="last")]
    s.name = sym
    return s


def load_bybit_fr(sym: str) -> Optional[pd.Series]:
    for tag in ("730d", "1200d", "365d"):
        f = CACHE / f"bybit_fr_{sym}USDT_{tag}.parquet"
        if f.exists():
            df = pd.read_parquet(f)
            s = df.set_index("timestamp")["funding_rate"].astype(float).sort_index()
            s = s[~s.index.duplicated(keep="last")]
            s.name = sym
            return s
    return None


def load_bybit_close(sym: str) -> Optional[pd.Series]:
    f = CACHE / f"{sym}USDT_4h_730d.parquet"
    if not f.exists():
        return None
    df = pd.read_parquet(f)
    s = df.set_index("open_time")["close"].astype(float).sort_index()
    s = s[~s.index.duplicated(keep="last")]
    s.name = sym
    return s


def build_per_symbol_event_panel(sym: str) -> Optional[pd.DataFrame]:
    hl = load_hl_fr(sym)
    by = load_bybit_fr(sym)
    cl = load_bybit_close(sym)
    if hl is None or by is None or cl is None:
        return None
    if len(hl) < 100 or len(by) < 100 or len(cl) < 100:
        return None
    hl_8h = hl.resample("8h", label="right", closed="right").sum(min_count=1)
    idx = by.index
    df = pd.DataFrame({"bybit_fr": by}, index=idx)
    df["hl_fr_8h"] = hl_8h.reindex(idx)
    df = df.dropna()
    if len(df) < 100:
        return None
    df["spread"] = df["bybit_fr"] - df["hl_fr_8h"]
    cl_at_event = cl.reindex(idx, method="nearest", tolerance=pd.Timedelta("2h"))
    df["close"] = cl_at_event
    df = df.dropna(subset=["close"])
    if len(df) < 100:
        return None
    df["fwd_ret_1"] = np.log(df["close"]).diff().shift(-1)
    return df


# ------------------------------ Strategy ------------------------------


def zscore(s: pd.Series, win: int = 30) -> pd.Series:
    mu = s.rolling(win, min_periods=win).mean()
    sd = s.rolling(win, min_periods=win).std()
    return (s - mu) / (sd + 1e-12)


def variant_z(
    panels: Dict[str, pd.DataFrame],
    z_thr: float,
    hold: int,
    zwin: int = 30,
    cost_per_fill: float = COST_PER_FILL,
) -> Tuple[pd.Series, pd.Series, int, Dict[str, float], Dict[str, float]]:
    """K174 V_z2_h1 logic. Equal-weight aggregation across supplied panels.

    Position rule (lag-1, K174-identical):
      z_{T-1} > +z_thr -> SHORT Bybit perp at T, hold `hold` events.
      z_{T-1} < -z_thr -> LONG  Bybit perp at T, hold `hold` events.

    Cost: `cost_per_fill` charged on each position-change event (entry & exit).
    """
    per_sym_gross: Dict[str, pd.Series] = {}
    per_sym_net: Dict[str, pd.Series] = {}
    total_trades = 0
    per_sym_sh_gross: Dict[str, float] = {}
    per_sym_sh_net: Dict[str, float] = {}
    for sym, df in panels.items():
        z = zscore(df["spread"], zwin)
        sig = pd.Series(0.0, index=df.index)
        sig[z > z_thr] = -1.0
        sig[z < -z_thr] = 1.0
        sig_lag = sig.shift(1).fillna(0.0)
        pos = pd.Series(0.0, index=df.index)
        i = 0
        trades = 0
        last_pos = 0.0
        while i < len(sig_lag):
            new = sig_lag.iloc[i]
            if new != 0.0 and last_pos == 0.0:
                end = min(i + hold, len(pos))
                pos.iloc[i:end] = new
                last_pos = new
                trades += 1
                i = end
                last_pos = 0.0
                continue
            i += 1
        fwd = df["fwd_ret_1"].fillna(0.0)
        pnl_gross_sym = pos * fwd
        pos_change = pos.diff().fillna(pos.iloc[0])
        cost_series = pd.Series(0.0, index=df.index)
        cost_series[pos_change != 0] = cost_per_fill
        pnl_net_sym = pnl_gross_sym - cost_series
        per_sym_gross[sym] = pnl_gross_sym
        per_sym_net[sym] = pnl_net_sym
        total_trades += trades
        per_sym_sh_gross[sym] = sharpe(pnl_gross_sym)
        per_sym_sh_net[sym] = sharpe(pnl_net_sym)
    if not per_sym_net:
        empty = pd.Series(dtype=float)
        return empty, empty, 0, {}, {}
    gross = pd.concat(per_sym_gross, axis=1).fillna(0.0).mean(axis=1)
    net = pd.concat(per_sym_net, axis=1).fillna(0.0).mean(axis=1)
    return net, gross, total_trades, per_sym_sh_net, per_sym_sh_gross


# ------------------------------ Metrics ------------------------------


def sharpe(pnl: pd.Series, ppy: int = EVENTS_PER_YEAR) -> float:
    pnl = pnl.dropna()
    if len(pnl) < 30 or pnl.std() == 0:
        return 0.0
    return float(pnl.mean() / pnl.std() * np.sqrt(ppy))


def cagr(pnl: pd.Series, ppy: int = EVENTS_PER_YEAR) -> float:
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
        sh = s.mean() / (s.std() + 1e-12) * np.sqrt(EVENTS_PER_YEAR)
        perm_sharpes.append(sh)
    perm_sharpes = np.array(perm_sharpes)
    if obs > 0:
        return float((perm_sharpes >= obs).mean())
    return float((perm_sharpes <= obs).mean())


def bootstrap_ci(pnl: pd.Series, n: int = 200, seed: int = 11) -> Tuple[float, float]:
    rng = np.random.default_rng(seed)
    vals = pnl.dropna().values
    if len(vals) < 30:
        return (0.0, 0.0)
    sharpes = []
    for _ in range(n):
        idx = rng.integers(0, len(vals), size=len(vals))
        s = pd.Series(vals[idx])
        sh = s.mean() / (s.std() + 1e-12) * np.sqrt(EVENTS_PER_YEAR)
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
    e_max = np.sqrt(2 * np.log(max(n_trials, 2))) - emc / np.sqrt(
        2 * np.log(max(n_trials, 2))
    )
    denom = np.sqrt((1 - sk * sr + (kt - 1) / 4 * sr**2) / (T - 1))
    if denom <= 0:
        return 0.0
    z = (sr - e_max) / denom
    return float(0.5 * (1 + erf(z / sqrt(2))))


def wf_3fold(pnl: pd.Series) -> Tuple[float, List[float]]:
    pnl = pnl.dropna()
    if len(pnl) < 100:
        return 0.0, []
    folds = np.array_split(pnl.values, 3)
    sharpes = []
    for f in folds:
        s = pd.Series(f)
        if s.std() == 0:
            sharpes.append(0.0)
            continue
        sharpes.append(float(s.mean() / s.std() * np.sqrt(EVENTS_PER_YEAR)))
    return float(np.mean(sharpes)), [float(x) for x in sharpes]


def turnover(pnl: pd.Series, n_trades: int) -> float:
    if len(pnl) == 0:
        return 0.0
    years = len(pnl) / EVENTS_PER_YEAR
    return float(n_trades / max(years, 1e-6))


def cost_stress_explicit(
    panels: Dict[str, pd.DataFrame], z_thr: float, hold: int, fill_bps: float
) -> Dict[str, float]:
    """Re-run V at an explicit per-fill cost level."""
    pnl_net, pnl_gross, n_tr, _, _ = variant_z(
        panels, z_thr=z_thr, hold=hold, cost_per_fill=fill_bps * 1e-4
    )
    return {
        "sharpe_net": round(sharpe(pnl_net), 4),
        "sharpe_gross": round(sharpe(pnl_gross), 4),
        "n_trades": int(n_tr),
    }


def report_variant(
    name: str,
    pnl: pd.Series,
    pnl_gross: pd.Series,
    n_trades: int,
    per_sym_sh: Dict[str, float],
    per_sym_sh_gross: Dict[str, float],
    panels: Dict[str, pd.DataFrame],
    z_thr: float,
    hold: int,
) -> Dict:
    sh = sharpe(pnl)
    sh_g = sharpe(pnl_gross)
    cg = cagr(pnl)
    cg_g = cagr(pnl_gross)
    dd = max_dd(pnl)
    split = int(len(pnl) * 0.7)
    is_pnl = pnl.iloc[:split]
    oos_pnl = pnl.iloc[split:]
    is_sh = sharpe(is_pnl)
    oos_sh = sharpe(oos_pnl)
    is_sh_g = sharpe(pnl_gross.iloc[:split])
    oos_sh_g = sharpe(pnl_gross.iloc[split:])
    wf_mean, wf_folds = wf_3fold(pnl)
    wf_mean_g, wf_folds_g = wf_3fold(pnl_gross)
    perm_p = perm_test(pnl, n=200)
    perm_p_g = perm_test(pnl_gross, n=200)
    ci_lo, ci_hi = bootstrap_ci(pnl, n=200)
    ci_lo_g, ci_hi_g = bootstrap_ci(pnl_gross, n=200)
    dsr_p = dsr(pnl, n_trials=4)
    dsr_p_g = dsr(pnl_gross, n_trials=4)
    to = turnover(pnl, n_trades)
    cs = {
        "3bp_roundtrip": cost_stress_explicit(panels, z_thr, hold, 1.5),  # 1.5/side
        "8bp_roundtrip_primary": cost_stress_explicit(panels, z_thr, hold, 4.0),
        "14bp_roundtrip": cost_stress_explicit(panels, z_thr, hold, 7.0),
        "28bp_roundtrip_k174_taker": cost_stress_explicit(panels, z_thr, hold, 14.0),
    }
    return {
        "variant": name,
        "sharpe_net": round(sh, 4),
        "sharpe_gross": round(sh_g, 4),
        "cagr_net": round(cg, 4),
        "cagr_gross": round(cg_g, 4),
        "max_dd_net": round(dd, 4),
        "is_sharpe_net": round(is_sh, 4),
        "oos_sharpe_net": round(oos_sh, 4),
        "is_sharpe_gross": round(is_sh_g, 4),
        "oos_sharpe_gross": round(oos_sh_g, 4),
        "wf_mean_sharpe_net": round(wf_mean, 4),
        "wf_folds_net": [round(x, 4) for x in wf_folds],
        "wf_mean_sharpe_gross": round(wf_mean_g, 4),
        "wf_folds_gross": [round(x, 4) for x in wf_folds_g],
        "perm_pvalue_net": round(perm_p, 4),
        "perm_pvalue_gross": round(perm_p_g, 4),
        "bootstrap_ci_5_95_net": [round(ci_lo, 4), round(ci_hi, 4)],
        "bootstrap_ci_5_95_gross": [round(ci_lo_g, 4), round(ci_hi_g, 4)],
        "dsr_net": round(dsr_p, 4),
        "dsr_gross": round(dsr_p_g, 4),
        "n_trades": int(n_trades),
        "trades_per_year": round(to, 2),
        "n_events": int(len(pnl)),
        "per_symbol_sharpe_net": {k: round(v, 4) for k, v in per_sym_sh.items()},
        "per_symbol_sharpe_gross": {
            k: round(v, 4) for k, v in per_sym_sh_gross.items()
        },
        "cost_stress_explicit_per_fill_bps": cs,
    }


# ------------------------------ Main ------------------------------


def main() -> Dict:
    t0 = time.time()
    panels: Dict[str, pd.DataFrame] = {}
    skipped: List[str] = []
    for sym in SYMBOLS:
        p = build_per_symbol_event_panel(sym)
        if p is None:
            skipped.append(sym)
            continue
        panels[sym] = p
    if not panels:
        raise RuntimeError("No panels built; check cache paths.")
    print(f"Built panels: {list(panels.keys())}, skipped: {skipped}")
    for s, df in panels.items():
        print(
            f"  {s:5s} events={len(df):4d}  spread mean={df['spread'].mean():+.6f}  "
            f"std={df['spread'].std():.6f}"
        )

    # Variants
    xrp_panel = {"XRP": panels["XRP"]} if "XRP" in panels else {}
    sui_panel = {"SUI": panels["SUI"]} if "SUI" in panels else {}

    variants_cfg = [
        ("V_xrp_sui_maker",    panels,    {"z_thr": 2.0, "hold": 1}),  # PRIMARY
        ("V_xrp_only",         xrp_panel, {"z_thr": 2.0, "hold": 1}),
        ("V_sui_only",         sui_panel, {"z_thr": 2.0, "hold": 1}),
        ("V_xrp_sui_maker_h3", panels,    {"z_thr": 2.0, "hold": 3}),
    ]

    results: List[Dict] = []
    curves: Dict[str, Dict] = {}
    primary_pnl: Optional[pd.Series] = None
    primary_pnl_gross: Optional[pd.Series] = None
    for name, panel_subset, kw in variants_cfg:
        if not panel_subset:
            continue
        pnl, pnl_g, n_tr, per_sh, per_sh_g = variant_z(
            panel_subset, cost_per_fill=COST_PER_FILL, **kw
        )
        rep = report_variant(
            name, pnl, pnl_g, n_tr, per_sh, per_sh_g,
            panel_subset, kw["z_thr"], kw["hold"]
        )
        results.append(rep)
        curves[name] = {
            "equity_net": equity_curve(pnl),
            "equity_gross": equity_curve(pnl_g),
            "timestamps": [t.isoformat() for t in pnl.index],
        }
        if name == "V_xrp_sui_maker":
            primary_pnl = pnl
            primary_pnl_gross = pnl_g
        print(
            f"{name:22s} Sh_net={rep['sharpe_net']:+.2f}  "
            f"Sh_gross={rep['sharpe_gross']:+.2f}  "
            f"OOS_net={rep['oos_sharpe_net']:+.2f}  perm_p={rep['perm_pvalue_net']:.3f}  "
            f"trades={rep['n_trades']}  to/yr={rep['trades_per_year']:.0f}"
        )

    # K174 same-window comparison (XRP/SUI subset, K174 taker cost 7bp/fill).
    k174_taker_pnl_net, k174_taker_pnl_gross, k174_n_tr, k174_per_sh, k174_per_sh_g = (
        variant_z(panels, z_thr=2.0, hold=1, cost_per_fill=COST_PER_FILL_K174)
    )
    k174_compare = {
        "description": (
            "K174 V_z2_h1 logic restricted to XRP/SUI only, with K174 TAKER cost "
            "(7bp/fill = 14bp roundtrip per leg). For apples-to-apples comparison "
            "of the COST change alone."
        ),
        "sharpe_net_k174_cost": round(sharpe(k174_taker_pnl_net), 4),
        "sharpe_gross": round(sharpe(k174_taker_pnl_gross), 4),
        "per_symbol_sharpe_net_k174_cost": {
            k: round(v, 4) for k, v in k174_per_sh.items()
        },
        "per_symbol_sharpe_gross": {k: round(v, 4) for k, v in k174_per_sh_g.items()},
        "delta_sharpe_net_maker_vs_taker": round(
            sharpe(primary_pnl) - sharpe(k174_taker_pnl_net), 4
        )
        if primary_pnl is not None
        else None,
    }
    curves["V_xrp_sui_K174TakerCost"] = {
        "equity_net": equity_curve(k174_taker_pnl_net),
        "equity_gross": equity_curve(k174_taker_pnl_gross),
        "timestamps": [t.isoformat() for t in k174_taker_pnl_net.index],
    }

    # Primary gates (K174-equivalent gate set, evaluated on V_xrp_sui_maker NET).
    primary = results[0]
    gates = {
        "g1_sharpe_net_ge_1": primary["sharpe_net"] >= 1.0,
        "g2_oos_sharpe_net_ge_0p5": primary["oos_sharpe_net"] >= 0.5,
        "g3_oos_is_ratio_ge_0p5": (
            primary["oos_sharpe_net"] / primary["is_sharpe_net"] >= 0.5
            if primary["is_sharpe_net"] > 0
            else False
        ),
        "g4_wf_folds_all_positive": (
            all(x > 0 for x in primary["wf_folds_net"])
            if primary["wf_folds_net"]
            else False
        ),
        "g5_perm_p_le_0p05": primary["perm_pvalue_net"] <= 0.05,
        "g6_dsr_ge_0p95": primary["dsr_net"] >= 0.95,
        "g7_trades_per_year_ge_20": primary["trades_per_year"] >= 20,
    }
    gates_passed = int(sum(gates.values()))
    verdict = (
        "PASS"
        if gates_passed >= 6
        else ("MARGINAL" if gates_passed >= 4 else "FAIL")
    )

    summary = {
        "wave": "K175",
        "parent_wave": "K174",
        "hypothesis": (
            "K174 GROSS edge concentrated in XRP/SUI (per-symbol gross Sharpe "
            "+1.46/+0.90); restrict to those two symbols AND replace 7bp/fill "
            "taker cost with 2bp/fill maker cost; expect net-positive edge."
        ),
        "cost_model": {
            "execution": "maker-only (post-only limit at top-of-book)",
            "slippage_bps_per_side": SLIPPAGE_BPS_PER_SIDE,
            "maker_fee_bps_per_side": MAKER_FEE_BPS_PER_SIDE,
            "cost_per_fill_bps": (SLIPPAGE_BPS_PER_SIDE + MAKER_FEE_BPS_PER_SIDE),
            "roundtrip_total_bps_per_leg": 2
            * (SLIPPAGE_BPS_PER_SIDE + MAKER_FEE_BPS_PER_SIDE),
            "k174_taker_roundtrip_bps_for_compare": 14.0 * 2,
            "cost_reduction_factor_vs_k174": round(
                (14.0 * 2) / max(2 * (SLIPPAGE_BPS_PER_SIDE + MAKER_FEE_BPS_PER_SIDE), 1e-6),
                2,
            ),
        },
        "data": {
            "symbols_used": list(panels.keys()),
            "symbols_skipped": skipped,
            "events_per_year_assumed": EVENTS_PER_YEAR,
            "per_symbol_event_counts": {
                s: int(len(df)) for s, df in panels.items()
            },
        },
        "variants": results,
        "k174_same_window_comparison": k174_compare,
        "gates_primary": gates,
        "gates_passed": gates_passed,
        "gates_total": 7,
        "verdict": verdict,
        "runtime_sec": round(time.time() - t0, 1),
    }

    out_json = ROOT / "wave_k175_xrp_sui_maker.json"
    out_curves = ROOT / "wave_k175_curves.json"
    out_json.write_text(json.dumps(summary, indent=2, default=str))
    out_curves.write_text(json.dumps(curves, default=str))
    print(f"\nWrote {out_json} ({out_json.stat().st_size} bytes)")
    print(f"Wrote {out_curves} ({out_curves.stat().st_size} bytes)")
    print(f"\nMaker-cost roundtrip (per leg) = {2*(SLIPPAGE_BPS_PER_SIDE+MAKER_FEE_BPS_PER_SIDE):.1f} bps  "
          f"vs K174 28 bps  ({summary['cost_model']['cost_reduction_factor_vs_k174']}x reduction)")
    print(f"Verdict: {verdict}  ({gates_passed}/7 gates)")
    print(f"Runtime: {summary['runtime_sec']}s")
    return summary


if __name__ == "__main__":
    main()
