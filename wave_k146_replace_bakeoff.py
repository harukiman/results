"""Wave K146 — K116 vs K142 REPLACE Bake-Off

K144 found K142 (AEA basis-vol XS) is +0.62 correlated with K116 (vol_only XS),
i.e. they ride the same vol-risk-premium factor. K144 rejected *adding* K142.
This wave tests whether REPLACING K116 with K142 yields a strict upgrade.

Three ensembles (each evaluated under P1/P2/P3/P5 with K121 cap 30%):

  A  K136 baseline       : v4.1, V1, K114, K116,  K121, K133   (current dominant)
  B  K136-alt-K142       : v4.1, V1, K114, K142,  K121, K133   (K142 replaces K116)
  C  7-strat (K144 ref)  : v4.1, V1, K114, K116,  K121, K133, K142

Method
------
1. Load all daily return series (re-use K144 loaders).
2. Inner-join to the same dates that *all 7* series share (so A/B/C are evaluated
   on the SAME calendar) — apples-to-apples.
3. For each ensemble, compute four portfolio variants:
     P1 equal, P2 inv-vol, P3 risk-parity, P5 sharpe-weighted.
4. Compare Sharpe (full / OOS), MaxDD (OOS), DR, AnnRet, AnnVol.
5. Decision rules:
     A > B           -> K116 stays
     B > A           -> K142 wins, swap
     C > A AND C > B -> keep both
"""
from __future__ import annotations

import json
import math
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

BASE = Path("/Users/nekonaomichi/crypto-lab")
TRADING_DAYS = 365
OOS_FRAC = 0.30


# -------------------- Loaders (mirror K144) --------------------

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


def _equity_to_daily_returns(ts_iso: List[str], eq: List[float]) -> pd.Series:
    ts = (
        pd.to_datetime(ts_iso, utc=True).tz_convert(None)
        if pd.to_datetime(ts_iso[0]).tzinfo
        else pd.to_datetime(ts_iso)
    )
    s = pd.Series(eq, index=ts).sort_index()
    daily_eq = s.resample("1D").last().ffill()
    daily_ret = daily_eq.pct_change().fillna(0.0)
    return daily_ret


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


def load_k142(variant: str = "V_30d_top5") -> pd.Series:
    with open(BASE / "wave_k142_curves.json") as fp:
        d = json.load(fp)
    v = d[variant]
    eq_net = np.asarray(v["equity_net"], dtype=float)
    eq = 1.0 + eq_net
    s = _equity_to_daily_returns(v["timestamps"], list(eq))
    s.name = "K142"
    return s


def assemble_all_7() -> pd.DataFrame:
    df01 = load_v41_and_v1()
    if df01.index.tz is not None:
        df01.index = df01.index.tz_localize(None)
    s114 = load_k114()
    s116 = load_k116()
    s121 = load_k121()
    s133 = load_k133()
    s142 = load_k142()
    df = pd.concat(
        [df01[["v4.1"]], df01[["V1"]],
         s114.to_frame(), s116.to_frame(), s121.to_frame(),
         s133.to_frame(), s142.to_frame()],
        axis=1, join="inner",
    ).sort_index().dropna(how="any")
    return df


# -------------------- Metrics --------------------

def sharpe(r: np.ndarray) -> float:
    if len(r) < 2 or r.std(ddof=1) == 0:
        return 0.0
    return float(r.mean() / r.std(ddof=1) * math.sqrt(TRADING_DAYS))


def sortino(r: np.ndarray) -> float:
    dn = r[r < 0]
    if len(dn) < 2 or dn.std(ddof=1) == 0:
        return 0.0
    return float(r.mean() / dn.std(ddof=1) * math.sqrt(TRADING_DAYS))


def max_dd(r: np.ndarray) -> float:
    eq = np.cumprod(1.0 + r)
    peak = np.maximum.accumulate(eq)
    return float((eq / peak - 1.0).min())


def calmar(r: np.ndarray) -> float:
    ann = (1.0 + r).prod() ** (TRADING_DAYS / max(1, len(r))) - 1.0
    mdd = max_dd(r)
    return float(ann / abs(mdd)) if mdd != 0 else 0.0


def metrics_pkg(r: np.ndarray) -> dict:
    if len(r) < 2:
        return {"sharpe": 0, "sortino": 0, "calmar": 0, "max_dd": 0,
                "ann_ret": 0, "ann_vol": 0, "n_days": int(len(r))}
    ann_ret = (1.0 + r).prod() ** (TRADING_DAYS / len(r)) - 1.0
    ann_vol = float(r.std(ddof=1) * math.sqrt(TRADING_DAYS))
    return {
        "sharpe":  round(sharpe(r), 4),
        "sortino": round(sortino(r), 4),
        "calmar":  round(calmar(r), 4),
        "max_dd":  round(max_dd(r), 4),
        "ann_ret": round(float(ann_ret), 4),
        "ann_vol": round(ann_vol, 4),
        "n_days":  int(len(r)),
    }


# -------------------- Weighting --------------------

def w_equal(n: int) -> np.ndarray:
    return np.ones(n) / n


def w_inv_vol(R: np.ndarray) -> np.ndarray:
    vols = R.std(axis=0, ddof=1)
    inv = 1.0 / np.where(vols == 0, np.nan, vols)
    return inv / np.nansum(inv)


def w_risk_parity(R: np.ndarray, n_iter: int = 5000, tol: float = 1e-9) -> np.ndarray:
    cov = np.cov(R, rowvar=False, ddof=1)
    n = cov.shape[0]
    w = np.ones(n) / n
    for _ in range(n_iter):
        mrc = cov @ w
        rc = w * mrc
        total_risk_sq = float(w @ cov @ w)
        target = total_risk_sq / n
        new_w = w * (target / np.where(rc == 0, 1e-12, rc)) ** 0.5
        new_w = np.clip(new_w, 1e-6, None)
        new_w = new_w / new_w.sum()
        if np.max(np.abs(new_w - w)) < tol:
            return new_w
        w = new_w
    return w


def w_sharpe(R: np.ndarray) -> np.ndarray:
    shs = np.array([sharpe(R[:, i]) for i in range(R.shape[1])])
    pos = np.clip(shs, 0, None)
    if pos.sum() == 0:
        return np.ones(R.shape[1]) / R.shape[1]
    return pos / pos.sum()


def apply_k121_cap(w: np.ndarray, cols: List[str], cap: float = 0.30) -> np.ndarray:
    w = w.copy()
    if "K121" not in cols:
        return w
    i = cols.index("K121")
    if w[i] <= cap:
        return w
    excess = w[i] - cap
    w[i] = cap
    other_mask = np.ones(len(w), dtype=bool)
    other_mask[i] = False
    others = w[other_mask]
    if others.sum() > 0:
        w[other_mask] = others + excess * (others / others.sum())
    return w / w.sum()


# -------------------- Pipeline --------------------

def fit_variants(R: np.ndarray, cols: List[str]) -> Dict[str, np.ndarray]:
    return {
        "P1_equal":       w_equal(len(cols)),
        "P2_inv_vol":     w_inv_vol(R),
        "P3_risk_parity": w_risk_parity(R),
        "P5_sharpe_wt":   w_sharpe(R),
    }


def portfolio_block(df: pd.DataFrame, label: str, cut: int) -> dict:
    cols = list(df.columns)
    R = df.to_numpy()
    oos_R = R[cut:, :]

    variants = fit_variants(R, cols)
    variants_capped = {k: apply_k121_cap(w, cols) for k, w in variants.items()}

    single_full = {c: metrics_pkg(df[c].to_numpy()) for c in cols}
    single_oos = {c: metrics_pkg(R[cut:, i]) for i, c in enumerate(cols)}
    single_sh_full = np.array([single_full[c]["sharpe"] for c in cols])
    single_sh_oos = np.array([single_oos[c]["sharpe"] for c in cols])

    full_metrics, oos_metrics = {}, {}
    full_metrics_capped, oos_metrics_capped = {}, {}
    dr_full, dr_oos = {}, {}
    curves_out = {c: list(np.cumprod(1.0 + df[c].to_numpy())) for c in cols}

    for name, w in variants.items():
        pr = R @ w
        m = metrics_pkg(pr)
        full_metrics[name] = m
        wavg = float((w * single_sh_full).sum())
        dr_full[name] = round(m["sharpe"] / wavg, 4) if wavg > 0 else None
        curves_out[name] = list(np.cumprod(1.0 + pr))
        m_oos = metrics_pkg(oos_R @ w)
        oos_metrics[name] = m_oos
        wavg_oos = float((w * single_sh_oos).sum())
        dr_oos[name] = round(m_oos["sharpe"] / wavg_oos, 4) if wavg_oos > 0 else None

    for name, w in variants_capped.items():
        pr = R @ w
        full_metrics_capped[name] = metrics_pkg(pr)
        oos_metrics_capped[name] = metrics_pkg(oos_R @ w)
        curves_out[name + "_cap30"] = list(np.cumprod(1.0 + pr))

    return {
        "label": label,
        "cols": cols,
        "single_full": single_full,
        "single_oos": single_oos,
        "weights_uncapped": {k: [round(float(x), 4) for x in v.tolist()] for k, v in variants.items()},
        "weights_cap30":    {k: [round(float(x), 4) for x in v.tolist()] for k, v in variants_capped.items()},
        "full_uncapped": full_metrics,
        "full_cap30":    full_metrics_capped,
        "oos_uncapped":  oos_metrics,
        "oos_cap30":     oos_metrics_capped,
        "dr_full":       dr_full,
        "dr_oos":        dr_oos,
        "curves":        curves_out,
    }


# -------------------- Decision Engine --------------------

def _score(b: dict, variant: str, key: str = "oos_cap30") -> Tuple[float, float, float, float]:
    """Return (oos_sharpe, oos_max_dd_abs, oos_ann_ret, dr_full) for a variant."""
    m = b[key][variant]
    return (
        m["sharpe"],
        abs(m["max_dd"]),
        m["ann_ret"],
        b["dr_full"][variant] if b["dr_full"][variant] is not None else float("nan"),
    )


def head_to_head(blk_a: dict, blk_b: dict) -> dict:
    """Per-variant deltas (B - A) on OOS cap30 + DR.

    Positive delta_sharpe / delta_ann_ret = B wins.
    Negative delta_max_dd (closer to zero from above; B has smaller |DD|) = B wins.
    """
    out = {}
    for v in ("P1_equal", "P2_inv_vol", "P3_risk_parity", "P5_sharpe_wt"):
        a = blk_a["oos_cap30"][v]
        b = blk_b["oos_cap30"][v]
        out[v] = {
            "A_oos_sharpe":  a["sharpe"],
            "B_oos_sharpe":  b["sharpe"],
            "delta_sharpe":  round(b["sharpe"] - a["sharpe"], 4),
            "A_oos_max_dd":  a["max_dd"],
            "B_oos_max_dd":  b["max_dd"],
            "delta_max_dd":  round(b["max_dd"] - a["max_dd"], 4),
            "A_oos_ann_ret": a["ann_ret"],
            "B_oos_ann_ret": b["ann_ret"],
            "delta_ann_ret": round(b["ann_ret"] - a["ann_ret"], 4),
            "A_dr_full":     blk_a["dr_full"][v],
            "B_dr_full":     blk_b["dr_full"][v],
            "delta_dr_full": (round(blk_b["dr_full"][v] - blk_a["dr_full"][v], 4)
                              if blk_a["dr_full"][v] is not None and blk_b["dr_full"][v] is not None
                              else None),
        }
    return out


def winner_per_variant(blk_a: dict, blk_b: dict, blk_c: dict) -> dict:
    """Pick winner per variant using lexicographic priority:
       OOS Sharpe (higher), then OOS MaxDD (smaller |DD|), then OOS AnnRet (higher).
    """
    winners = {}
    for v in ("P1_equal", "P2_inv_vol", "P3_risk_parity", "P5_sharpe_wt"):
        scores = {
            "A": _score(blk_a, v),
            "B": _score(blk_b, v),
            "C": _score(blk_c, v),
        }
        # ordering key: maximize Sh, minimize |DD|, maximize AnnRet
        ranked = sorted(
            scores.items(),
            key=lambda kv: (-kv[1][0], kv[1][1], -kv[1][2]),
        )
        winners[v] = {
            "winner": ranked[0][0],
            "scores": {k: {"oos_sharpe": s[0], "oos_max_dd_abs": round(s[1], 4),
                           "oos_ann_ret": s[2], "dr_full": s[3]}
                       for k, s in scores.items()},
            "ranking": [r[0] for r in ranked],
        }
    return winners


def overall_recommendation(winners: dict, blk_a: dict, blk_b: dict, blk_c: dict) -> dict:
    """Aggregate: count wins, and break ties via mean OOS Sharpe across the 4 variants."""
    tally = {"A": 0, "B": 0, "C": 0}
    for v in winners.values():
        tally[v["winner"]] += 1
    mean_sh = {
        "A": float(np.mean([blk_a["oos_cap30"][v]["sharpe"] for v in
                            ("P1_equal", "P2_inv_vol", "P3_risk_parity", "P5_sharpe_wt")])),
        "B": float(np.mean([blk_b["oos_cap30"][v]["sharpe"] for v in
                            ("P1_equal", "P2_inv_vol", "P3_risk_parity", "P5_sharpe_wt")])),
        "C": float(np.mean([blk_c["oos_cap30"][v]["sharpe"] for v in
                            ("P1_equal", "P2_inv_vol", "P3_risk_parity", "P5_sharpe_wt")])),
    }
    mean_dd = {
        k: float(np.mean([abs(blk["oos_cap30"][v]["max_dd"]) for v in
                          ("P1_equal", "P2_inv_vol", "P3_risk_parity", "P5_sharpe_wt")]))
        for k, blk in (("A", blk_a), ("B", blk_b), ("C", blk_c))
    }
    # Decide top:  most variant wins → tie-break by mean OOS Sharpe → tie-break by smaller mean |DD|.
    ranked = sorted(
        tally.keys(),
        key=lambda k: (-tally[k], -mean_sh[k], mean_dd[k]),
    )
    top = ranked[0]
    decision_rule = "A>B → K116 stays. B>A → K142 wins/swap. C>A&C>B → keep both."
    if top == "A":
        verdict = "A wins → KEEP K116 (drop K142). K142 is REDUNDANT, not an upgrade."
    elif top == "B":
        verdict = "B wins → SWAP K116 for K142. K142 is a STRICT UPGRADE."
    else:
        verdict = "C wins → KEEP BOTH. K116 and K142 are COMPLEMENTARY despite +0.62 correlation."
    return {
        "variant_wins": tally,
        "mean_oos_sharpe": {k: round(v, 4) for k, v in mean_sh.items()},
        "mean_oos_max_dd_abs": {k: round(v, 4) for k, v in mean_dd.items()},
        "ranking": ranked,
        "top": top,
        "decision_rule": decision_rule,
        "verdict": verdict,
    }


def substitutability_call(blk_a: dict, blk_b: dict, blk_c: dict, corr_a_b: float) -> dict:
    """K116 vs K142: substitutable, complementary, or neither?

    - SUBSTITUTABLE: A ~ B (similar metrics) AND C ~ A (no incremental gain).
    - COMPLEMENTARY: C > A AND C > B (each adds something).
    - NEITHER:       results are noisy/inconclusive.
    """
    mean_a = float(np.mean([blk_a["oos_cap30"][v]["sharpe"] for v in
                            ("P1_equal", "P2_inv_vol", "P3_risk_parity", "P5_sharpe_wt")]))
    mean_b = float(np.mean([blk_b["oos_cap30"][v]["sharpe"] for v in
                            ("P1_equal", "P2_inv_vol", "P3_risk_parity", "P5_sharpe_wt")]))
    mean_c = float(np.mean([blk_c["oos_cap30"][v]["sharpe"] for v in
                            ("P1_equal", "P2_inv_vol", "P3_risk_parity", "P5_sharpe_wt")]))
    delta_ab = abs(mean_a - mean_b)
    incr_c_vs_ab = mean_c - max(mean_a, mean_b)
    if incr_c_vs_ab > 0.05 and delta_ab < 0.15:
        verdict = "COMPLEMENTARY — both add orthogonal info despite +0.62 corr"
    elif delta_ab < 0.10 and incr_c_vs_ab < 0.02:
        verdict = "SUBSTITUTABLE — same factor, picking either gives similar result"
    elif mean_a > mean_b + 0.10 and incr_c_vs_ab < 0.02:
        verdict = "K116 DOMINATES — K142 is a noisier version"
    elif mean_b > mean_a + 0.10 and incr_c_vs_ab < 0.02:
        verdict = "K142 DOMINATES — K116 is the noisier version"
    else:
        verdict = "NEITHER — inconclusive; correlation alone does not determine substitutability"
    return {
        "mean_oos_sharpe_A": round(mean_a, 4),
        "mean_oos_sharpe_B": round(mean_b, 4),
        "mean_oos_sharpe_C": round(mean_c, 4),
        "abs_delta_AB":       round(delta_ab, 4),
        "incr_C_vs_max_AB":   round(incr_c_vs_ab, 4),
        "pearson_K116_K142":  round(corr_a_b, 4),
        "verdict": verdict,
    }


def run_pipeline():
    t0 = datetime.utcnow()
    df7 = assemble_all_7()
    print(f"Aligned daily returns (7-strat join): n={len(df7)}  cols={list(df7.columns)}")
    print(f"Date range: {df7.index.min().date()} -> {df7.index.max().date()}")

    cut = int(len(df7) * (1 - OOS_FRAC))
    print(f"OOS cut idx: {cut}  OOS days: {len(df7) - cut}")

    # Build the three panels on the SAME calendar
    cols_A = ["v4.1", "V1", "K114", "K116", "K121", "K133"]
    cols_B = ["v4.1", "V1", "K114", "K142", "K121", "K133"]
    cols_C = ["v4.1", "V1", "K114", "K116", "K121", "K133", "K142"]

    df_A = df7[cols_A].copy()
    df_B = df7[cols_B].copy()
    df_C = df7[cols_C].copy()

    blk_A = portfolio_block(df_A, "A_K136_baseline", cut)
    blk_B = portfolio_block(df_B, "B_K136alt_K142", cut)
    blk_C = portfolio_block(df_C, "C_7strat_both", cut)

    # Correlations 7x7 (for context)
    corr_p = df7.corr(method="pearson").round(4)
    corr_s = df7.corr(method="spearman").round(4)
    corr_k116_k142 = float(corr_p.loc["K116", "K142"])
    print(f"\nK116 vs K142 Pearson corr: {corr_k116_k142:+.4f}")

    # Head-to-heads
    h2h_BvsA = head_to_head(blk_A, blk_B)  # B − A
    h2h_CvsA = head_to_head(blk_A, blk_C)  # C − A
    h2h_CvsB = head_to_head(blk_B, blk_C)  # C − B

    winners = winner_per_variant(blk_A, blk_B, blk_C)
    overall = overall_recommendation(winners, blk_A, blk_B, blk_C)
    subst = substitutability_call(blk_A, blk_B, blk_C, corr_k116_k142)

    elapsed = (datetime.utcnow() - t0).total_seconds()

    out = {
        "wave": "K146",
        "task": "K116 vs K142 REPLACE bake-off (A baseline / B swap / C both)",
        "as_of": datetime.utcnow().isoformat() + "Z",
        "elapsed_sec": round(elapsed, 2),
        "n_days_aligned": int(len(df7)),
        "date_range": [str(df7.index.min().date()), str(df7.index.max().date())],
        "oos_cut_idx": int(cut),
        "oos_n_days": int(len(df7) - cut),
        "ensembles": {
            "A": {"label": "K136 baseline (K116)",   "members": cols_A},
            "B": {"label": "K136-alt (K142 swap)",   "members": cols_B},
            "C": {"label": "7-strat (K116 + K142)",  "members": cols_C},
        },
        "correlations_7x7": {
            "pearson":  corr_p.to_dict(),
            "spearman": corr_s.to_dict(),
        },
        "k116_vs_k142_pearson": round(corr_k116_k142, 4),

        # Per-ensemble blocks
        "A_block": {
            "cols":           blk_A["cols"],
            "single_full":    blk_A["single_full"],
            "single_oos":     blk_A["single_oos"],
            "weights_uncapped": blk_A["weights_uncapped"],
            "weights_cap30":    blk_A["weights_cap30"],
            "full_uncapped":  blk_A["full_uncapped"],
            "full_cap30":     blk_A["full_cap30"],
            "oos_uncapped":   blk_A["oos_uncapped"],
            "oos_cap30":      blk_A["oos_cap30"],
            "dr_full":        blk_A["dr_full"],
            "dr_oos":         blk_A["dr_oos"],
        },
        "B_block": {
            "cols":           blk_B["cols"],
            "single_full":    blk_B["single_full"],
            "single_oos":     blk_B["single_oos"],
            "weights_uncapped": blk_B["weights_uncapped"],
            "weights_cap30":    blk_B["weights_cap30"],
            "full_uncapped":  blk_B["full_uncapped"],
            "full_cap30":     blk_B["full_cap30"],
            "oos_uncapped":   blk_B["oos_uncapped"],
            "oos_cap30":      blk_B["oos_cap30"],
            "dr_full":        blk_B["dr_full"],
            "dr_oos":         blk_B["dr_oos"],
        },
        "C_block": {
            "cols":           blk_C["cols"],
            "single_full":    blk_C["single_full"],
            "single_oos":     blk_C["single_oos"],
            "weights_uncapped": blk_C["weights_uncapped"],
            "weights_cap30":    blk_C["weights_cap30"],
            "full_uncapped":  blk_C["full_uncapped"],
            "full_cap30":     blk_C["full_cap30"],
            "oos_uncapped":   blk_C["oos_uncapped"],
            "oos_cap30":      blk_C["oos_cap30"],
            "dr_full":        blk_C["dr_full"],
            "dr_oos":         blk_C["dr_oos"],
        },

        "head_to_head": {
            "B_minus_A": h2h_BvsA,
            "C_minus_A": h2h_CvsA,
            "C_minus_B": h2h_CvsB,
        },
        "winner_per_variant": winners,
        "overall_recommendation": overall,
        "substitutability": subst,
        "notes": [
            "All three ensembles evaluated on the SAME aligned calendar (inner-join over all 7 series).",
            "K121 capped at 30% via proportional excess redistribution.",
            "OOS = last 30% of dates.",
            "Diversification Ratio (DR) = portfolio_sharpe / weighted_avg(single_sharpe).",
            "Winner-per-variant priority: OOS Sharpe (higher), then |OOS MaxDD| (smaller), then OOS AnnRet (higher).",
            "Decision logic: A>B → K116 stays; B>A → swap; C>A&C>B → keep both.",
            "Substitutability test: small ΔAB and small incremental gain of C → substitutable factors.",
        ],
    }

    with open(BASE / "wave_k146_replace_bakeoff.json", "w") as fp:
        json.dump(out, fp, indent=2, default=str)
    print("Wrote wave_k146_replace_bakeoff.json")

    # Curves output for HTML chart use
    dates_iso = [d.strftime("%Y-%m-%d") for d in df7.index]
    curves_obj = {"dates": dates_iso, "series": {}}
    # Singles (use the 7-strat block so we cover everything once)
    for c in df7.columns:
        curves_obj["series"][c] = [round(float(x), 6)
                                    for x in np.cumprod(1.0 + df7[c].to_numpy()).tolist()]
    # Portfolios per ensemble (with cap30 variants kept separately)
    for tag, blk in (("A", blk_A), ("B", blk_B), ("C", blk_C)):
        for k, v in blk["curves"].items():
            if k in df7.columns:
                continue  # already added
            curves_obj["series"][f"{tag}_{k}"] = [round(float(x), 6) for x in v]
    with open(BASE / "wave_k146_curves.json", "w") as fp:
        json.dump(curves_obj, fp)
    print("Wrote wave_k146_curves.json")

    # ---- console report ----
    print("\n--- SINGLE STRATEGY (FULL) on K146 aligned window ---")
    for c in df7.columns:
        m = blk_C["single_full"][c]
        print(f"  {c:6s}  Sh={m['sharpe']:+.3f}  Sor={m['sortino']:+.3f}  "
              f"Cal={m['calmar']:+.3f}  DD={m['max_dd']*100:+.2f}%  Vol={m['ann_vol']*100:.2f}%")

    print("\n--- SINGLE STRATEGY (OOS 30%) ---")
    for c in df7.columns:
        m = blk_C["single_oos"][c]
        print(f"  {c:6s}  OOS Sh={m['sharpe']:+.3f}  DD={m['max_dd']*100:+.2f}%  "
              f"AnnRet={m['ann_ret']*100:+.2f}%")

    for tag, blk in (("A K136 baseline (K116)", blk_A),
                     ("B K136-alt (K142 swap)", blk_B),
                     ("C 7-strat (both)",       blk_C)):
        print(f"\n--- {tag}  OOS cap30 ---")
        for k, m in blk["oos_cap30"].items():
            w = blk["weights_cap30"][k]
            ws = " ".join(f"{c}={w[i]:.2f}" for i, c in enumerate(blk["cols"]))
            print(f"  {k:18s}  Sh={m['sharpe']:+.3f}  DD={m['max_dd']*100:+.2f}%  "
                  f"AnnRet={m['ann_ret']*100:+.2f}%  Vol={m['ann_vol']*100:.2f}%  "
                  f"DR_full={blk['dr_full'][k]}")
            print(f"    w: {ws}")

    print("\n--- HEAD-TO-HEAD (OOS cap30) ---")
    for label, h in (("B-A", h2h_BvsA), ("C-A", h2h_CvsA), ("C-B", h2h_CvsB)):
        print(f"\n  {label}:")
        for k, d in h.items():
            print(f"    {k:18s} ΔSh={d['delta_sharpe']:+.3f}  "
                  f"ΔDD={d['delta_max_dd']*100:+.2f}%  ΔAnnRet={d['delta_ann_ret']*100:+.2f}%  "
                  f"ΔDR={d['delta_dr_full']}")

    print("\n--- WINNER PER VARIANT (OOS cap30) ---")
    for v, info in winners.items():
        print(f"  {v:18s}  winner={info['winner']}  ranking={info['ranking']}")

    print("\n--- OVERALL RECOMMENDATION ---")
    for k, v in overall.items():
        print(f"  {k}: {v}")

    print("\n--- SUBSTITUTABILITY CALL ---")
    for k, v in subst.items():
        print(f"  {k}: {v}")

    print(f"\nElapsed: {elapsed:.2f}s")

    return out


if __name__ == "__main__":
    run_pipeline()
