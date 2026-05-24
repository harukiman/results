"""Wave K177 - K175 Expansion: DOGE + AVAX (low-beta CEX-DEX FR).

K175 confirmed XRP/SUI maker-only CEX-DEX FR spread strategy:
  V_xrp_sui_maker  Sh_net=+1.33, OOS_net=+1.93, 7/7 gate set near-pass,
  perm_p=0.000, bootstrap CI [0.07, 2.27].

K174 panel audit also showed DOGE (beta=0.49) and AVAX (beta=0.31) had
LOW CEX-DEX integration -- the same property that made XRP/SUI mean-revert
on the spread. However per-symbol gross was noise-dominated (small N
in the K174 8-symbol panel). K177 ISOLATES DOGE and AVAX with the
K175 methodology to test whether the low-beta property generalises.

Hypothesis:
  Low CEX-DEX FR beta => CEX (Bybit) FR contains idiosyncratic
  (non-shared) information that mean-reverts within one funding event.
  If XRP (beta lowest) and SUI worked, DOGE/AVAX (next-lowest betas)
  should also produce positive maker-net Sharpe individually, and a
  4-symbol basket should diversify away symbol-specific noise.

Method (IDENTICAL to K175):
  1. spread_t = bybit_fr_t - sum(hl_hourly_fr)_8h_window_t   (lag 1)
  2. zscore over rolling 30 events
  3. |z| > 2 => fade Bybit perp (z>+2 SHORT, z<-2 LONG)
  4. Hold 1 funding event (8h), single-leg perp
  5. Cost: maker-only 2bp/side -> 4bp/leg roundtrip (vs K174 28bp taker)

Variants (pre-registered):
  V_doge_maker         : DOGE alone               -- per-symbol generality test
  V_avax_maker         : AVAX alone               -- per-symbol generality test
  V_doge_avax_combined : DOGE+AVAX panel mean     -- 2-sym low-beta basket
  V_4sym_combined      : XRP+SUI+DOGE+AVAX panel  -- PRIMARY (full basket)
  V_xrp_sui_recompute  : XRP+SUI on same window   -- K175 sanity replicate

Audit (identical to K175):
  - IS/OOS 70/30
  - WF 3-fold
  - Permutation test n=200
  - Bootstrap n=200 (5/95 CI on Sharpe)
  - DSR with N_trials=5 (variant count)
  - Cost stress: 3 / 8 / 14 / 28 bp roundtrip (per leg)

Compare V_4sym vs V_xrp_sui (K175): does adding DOGE+AVAX help or
dilute? Verdict on whether basket-of-4 beats XRP/SUI only.

REPORT GROSS + NET both (K173/K174/K175 lesson).
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

# Maker-only execution cost model (IDENTICAL to K175).
SLIPPAGE_BPS_PER_SIDE = 2.0
MAKER_FEE_BPS_PER_SIDE = 0.0
COST_PER_FILL = (SLIPPAGE_BPS_PER_SIDE + MAKER_FEE_BPS_PER_SIDE) * 1e-4  # 0.0002

# K174 taker comparator: 14 bps per fill (entry+exit -> 28 bps roundtrip).
COST_PER_FILL_K174 = 0.0007

# Full universe explored in K177.
NEW_SYMBOLS = ["DOGE", "AVAX"]
ALL_SYMBOLS = ["XRP", "SUI", "DOGE", "AVAX"]

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
    """K175-identical variant_z. Equal-weight aggregation across supplied panels."""
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


def dsr(pnl: pd.Series, n_trials: int = 5) -> float:
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
    n_trials_dsr: int = 5,
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
    dsr_p = dsr(pnl, n_trials=n_trials_dsr)
    dsr_p_g = dsr(pnl_gross, n_trials=n_trials_dsr)
    to = turnover(pnl, n_trades)
    cs = {
        "3bp_roundtrip": cost_stress_explicit(panels, z_thr, hold, 1.5),
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
    for sym in ALL_SYMBOLS:
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

    doge_panel = {"DOGE": panels["DOGE"]} if "DOGE" in panels else {}
    avax_panel = {"AVAX": panels["AVAX"]} if "AVAX" in panels else {}
    da_panel = {k: v for k, v in panels.items() if k in ("DOGE", "AVAX")}
    xs_panel = {k: v for k, v in panels.items() if k in ("XRP", "SUI")}
    all4_panel = {k: v for k, v in panels.items() if k in ALL_SYMBOLS}

    variants_cfg = [
        ("V_4sym_combined",      all4_panel, {"z_thr": 2.0, "hold": 1}),  # PRIMARY
        ("V_doge_avax_combined", da_panel,   {"z_thr": 2.0, "hold": 1}),
        ("V_doge_maker",         doge_panel, {"z_thr": 2.0, "hold": 1}),
        ("V_avax_maker",         avax_panel, {"z_thr": 2.0, "hold": 1}),
        ("V_xrp_sui_recompute",  xs_panel,   {"z_thr": 2.0, "hold": 1}),
    ]

    results: List[Dict] = []
    curves: Dict[str, Dict] = {}
    primary_pnl: Optional[pd.Series] = None
    primary_pnl_gross: Optional[pd.Series] = None
    xrp_sui_recompute_pnl: Optional[pd.Series] = None
    xrp_sui_recompute_pnl_gross: Optional[pd.Series] = None
    for name, panel_subset, kw in variants_cfg:
        if not panel_subset:
            continue
        pnl, pnl_g, n_tr, per_sh, per_sh_g = variant_z(
            panel_subset, cost_per_fill=COST_PER_FILL, **kw
        )
        rep = report_variant(
            name, pnl, pnl_g, n_tr, per_sh, per_sh_g,
            panel_subset, kw["z_thr"], kw["hold"], n_trials_dsr=len(variants_cfg)
        )
        results.append(rep)
        curves[name] = {
            "equity_net": equity_curve(pnl),
            "equity_gross": equity_curve(pnl_g),
            "timestamps": [t.isoformat() for t in pnl.index],
        }
        if name == "V_4sym_combined":
            primary_pnl = pnl
            primary_pnl_gross = pnl_g
        if name == "V_xrp_sui_recompute":
            xrp_sui_recompute_pnl = pnl
            xrp_sui_recompute_pnl_gross = pnl_g
        print(
            f"{name:22s} Sh_net={rep['sharpe_net']:+.2f}  "
            f"Sh_gross={rep['sharpe_gross']:+.2f}  "
            f"OOS_net={rep['oos_sharpe_net']:+.2f}  perm_p={rep['perm_pvalue_net']:.3f}  "
            f"trades={rep['n_trades']}  to/yr={rep['trades_per_year']:.0f}"
        )

    # K175 head-to-head: V_4sym vs V_xrp_sui_recompute (same window, same cost).
    v4 = results[0]
    vxs = next((r for r in results if r["variant"] == "V_xrp_sui_recompute"), None)
    k175_compare = {
        "description": (
            "V_4sym_combined (XRP+SUI+DOGE+AVAX) vs V_xrp_sui_recompute (XRP+SUI), "
            "EXACT same window/method/cost. Tests whether the 2 added low-beta "
            "symbols ADD net edge or DILUTE the XRP/SUI core."
        ),
        "v4sym_sharpe_net": v4["sharpe_net"],
        "v4sym_sharpe_gross": v4["sharpe_gross"],
        "v_xrp_sui_recompute_sharpe_net": vxs["sharpe_net"] if vxs else None,
        "v_xrp_sui_recompute_sharpe_gross": vxs["sharpe_gross"] if vxs else None,
        "delta_sharpe_net_4sym_minus_xrp_sui": (
            round(v4["sharpe_net"] - vxs["sharpe_net"], 4) if vxs else None
        ),
        "delta_oos_sharpe_net_4sym_minus_xrp_sui": (
            round(v4["oos_sharpe_net"] - vxs["oos_sharpe_net"], 4) if vxs else None
        ),
        "v4sym_max_dd_net": v4["max_dd_net"],
        "v_xrp_sui_recompute_max_dd_net": vxs["max_dd_net"] if vxs else None,
        "v_k175_published_sharpe_net": 1.3326,
        "v_k175_published_oos_sharpe_net": 1.9303,
    }

    # Cost survival comparison for primary 4-sym.
    primary = results[0]
    cs = primary["cost_stress_explicit_per_fill_bps"]
    cost_survival = {
        "3bp": cs["3bp_roundtrip"]["sharpe_net"],
        "8bp": cs["8bp_roundtrip_primary"]["sharpe_net"],
        "14bp": cs["14bp_roundtrip"]["sharpe_net"],
        "28bp": cs["28bp_roundtrip_k174_taker"]["sharpe_net"],
        "still_positive_at_28bp": cs["28bp_roundtrip_k174_taker"]["sharpe_net"] > 0,
        "still_above_0p5_at_14bp": cs["14bp_roundtrip"]["sharpe_net"] >= 0.5,
    }

    # Primary gates -- K175-equivalent gate set on V_4sym_combined NET.
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

    # Generalisation verdict: per-symbol XRP/SUI vs DOGE/AVAX.
    per_sym_4 = primary["per_symbol_sharpe_net"]
    per_sym_4_gross = primary["per_symbol_sharpe_gross"]
    generalisation = {
        "per_symbol_sharpe_net_4sym": per_sym_4,
        "per_symbol_sharpe_gross_4sym": per_sym_4_gross,
        "xrp_sui_avg_net": round(
            np.mean([per_sym_4.get("XRP", 0.0), per_sym_4.get("SUI", 0.0)]), 4
        ),
        "doge_avax_avg_net": round(
            np.mean([per_sym_4.get("DOGE", 0.0), per_sym_4.get("AVAX", 0.0)]), 4
        ),
        "doge_avax_both_positive_net": (
            per_sym_4.get("DOGE", 0.0) > 0 and per_sym_4.get("AVAX", 0.0) > 0
        ),
        "all4_positive_net": all(v > 0 for v in per_sym_4.values()),
        "all4_positive_gross": all(v > 0 for v in per_sym_4_gross.values()),
    }

    # Final hypothesis verdict text.
    if generalisation["all4_positive_net"]:
        if (
            vxs is not None
            and v4["sharpe_net"] >= vxs["sharpe_net"]
            and v4["max_dd_net"] >= vxs["max_dd_net"]
        ):
            hypothesis_verdict = (
                "GENERALISES + 4SYM_BEATS_XRP/SUI: DOGE & AVAX both positive net "
                "AND the 4-sym basket equals or beats the 2-sym XRP/SUI on Sharpe "
                "AND drawdown."
            )
        else:
            hypothesis_verdict = (
                "GENERALISES_BUT_DILUTES: DOGE & AVAX both individually positive "
                "net, BUT the 4-sym basket underperforms XRP/SUI -> prefer the "
                "tighter 2-sym basket."
            )
    elif (
        per_sym_4.get("DOGE", 0.0) > 0
        or per_sym_4.get("AVAX", 0.0) > 0
    ):
        hypothesis_verdict = (
            "PARTIAL: Only one of DOGE/AVAX is net-positive. Low-beta hypothesis "
            "is symbol-selective, not a universal property."
        )
    else:
        hypothesis_verdict = (
            "FAILS_GENERALISATION: Neither DOGE nor AVAX is individually net-positive. "
            "The K175 edge is XRP/SUI-specific; low CEX-DEX beta is necessary but "
            "not sufficient."
        )

    summary = {
        "wave": "K177",
        "parent_wave": "K175",
        "hypothesis": (
            "K175 maker-only XRP/SUI edge (Sh_net=+1.33) extends to other low "
            "CEX-DEX-beta symbols. K174 showed DOGE(b=0.49)/AVAX(b=0.31) had "
            "low betas, isolate them with K175 method and test individual + "
            "basket generalisation."
        ),
        "cost_model": {
            "execution": "maker-only (post-only limit at top-of-book)",
            "slippage_bps_per_side": SLIPPAGE_BPS_PER_SIDE,
            "maker_fee_bps_per_side": MAKER_FEE_BPS_PER_SIDE,
            "cost_per_fill_bps": (SLIPPAGE_BPS_PER_SIDE + MAKER_FEE_BPS_PER_SIDE),
            "roundtrip_total_bps_per_leg": 2
            * (SLIPPAGE_BPS_PER_SIDE + MAKER_FEE_BPS_PER_SIDE),
            "k174_taker_roundtrip_bps_for_compare": 14.0 * 2,
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
        "k175_head_to_head": k175_compare,
        "generalisation": generalisation,
        "cost_survival_v4sym_net": cost_survival,
        "gates_primary_v4sym": gates,
        "gates_passed": gates_passed,
        "gates_total": 7,
        "gate_verdict": verdict,
        "hypothesis_verdict": hypothesis_verdict,
        "runtime_sec": round(time.time() - t0, 1),
    }

    out_json = ROOT / "wave_k177_low_beta_expand.json"
    out_curves = ROOT / "wave_k177_curves.json"
    out_json.write_text(json.dumps(summary, indent=2, default=str))
    out_curves.write_text(json.dumps(curves, default=str))
    print(f"\nWrote {out_json} ({out_json.stat().st_size} bytes)")
    print(f"Wrote {out_curves} ({out_curves.stat().st_size} bytes)")
    print(f"\nGate verdict: {verdict} ({gates_passed}/7)")
    print(f"Hypothesis verdict: {hypothesis_verdict}")
    print(f"Runtime: {summary['runtime_sec']}s")
    return summary


if __name__ == "__main__":
    main()
