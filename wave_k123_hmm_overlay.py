#!/usr/bin/env python3
"""
Wave K123 — HMM Regime-Conditional Trend Overlay.

Hypothesis (R3 #45): Fit a 2-3 state Gaussian HMM on {return, |return|, range_pct}
features per symbol and use the regime label as a filter overlay on an EMA-cross
trend strategy. Test whether trading only in the "turbulent" state (highest
|return|/range) improves OOS Sharpe vs the unfiltered baseline.

Method:
    * Symbols: BTC, ETH, SOL, BNB, DOGE, AVAX, LINK, ADA, XRP, INJ
    * Bars  : 4H, 730d cache
    * Features lag 1 : log_return, |log_return|, range_pct = (high-low)/close
    * HMM   : GaussianHMM (full covar), k in {2,3} — pick min BIC per (sym, fold)
    * Baseline trend : EMA20 - EMA60 cross, sign() with 1-bar exec lag
    * Variants
        V_base       : raw trend
        V_turbulent  : trade only when state == highest-|return| state
        V_non_consol : trade except when state == lowest-range state (consol)
    * 4-fold walk-forward, refit HMM in each fold; lag 1 everywhere
    * Permutation test (n=500): shuffle state labels within fold OOS window
    * Block bootstrap CI on portfolio OOS Sharpe (B=1000, block=24)
    * DSR with N_trials = 3 (variants)
    * Cost stress ±50 %  (base = 5 bps round trip)

Outputs:
    wave_k123_hmm_overlay.json     summary results
    wave_k123_curves.json          per-symbol & portfolio equity curves
"""

from __future__ import annotations

import json
import os
import sys
import time
import warnings
from dataclasses import dataclass
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

try:
    from hmmlearn.hmm import GaussianHMM

    HMM_BACKEND = "hmmlearn.GaussianHMM"
except ImportError:  # pragma: no cover - fallback documented in report
    from sklearn.mixture import GaussianMixture  # noqa: F401

    HMM_BACKEND = "sklearn.GaussianMixture (fallback)"

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
CACHE_DIR = "/Users/nekonaomichi/crypto-lab/cache"
OUT_JSON = "/Users/nekonaomichi/crypto-lab/wave_k123_hmm_overlay.json"
OUT_CURVES = "/Users/nekonaomichi/crypto-lab/wave_k123_curves.json"

SYMBOLS = ["BTC", "ETH", "SOL", "BNB", "DOGE", "AVAX", "LINK", "ADA", "XRP", "INJ"]
TF = "4h_730d"

EMA_FAST = 20
EMA_SLOW = 60
COST_BPS = 5.0  # round-trip cost in bps per position flip
N_FOLDS = 4
HMM_STATES = [2, 3]
HMM_ITER = 200
PERM_N = 500
BOOT_N = 1000
BOOT_BLOCK = 24
RNG_SEED = 20260524
BARS_PER_YEAR = 365 * 6  # 4h bars

VARIANTS = ["V_base", "V_turbulent", "V_non_consol"]

# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------


def load_bars(sym: str) -> pd.DataFrame:
    path = os.path.join(CACHE_DIR, f"{sym}USDT_{TF}.parquet")
    df = pd.read_parquet(path)
    df = df.copy()
    df["ts"] = pd.to_datetime(df["open_time"])
    df = df.sort_values("ts").reset_index(drop=True)
    df = df[["ts", "open", "high", "low", "close", "volume"]]
    return df


def make_features(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["ret"] = np.log(out["close"]).diff()
    out["abs_ret"] = out["ret"].abs()
    out["range_pct"] = (out["high"] - out["low"]) / out["close"]
    out["ema_f"] = out["close"].ewm(span=EMA_FAST, adjust=False).mean()
    out["ema_s"] = out["close"].ewm(span=EMA_SLOW, adjust=False).mean()
    out = out.dropna().reset_index(drop=True)
    return out


# ---------------------------------------------------------------------------
# HMM helpers
# ---------------------------------------------------------------------------


def fit_hmm(X: np.ndarray, k: int, seed: int) -> Tuple[object, float, float]:
    """Return (model, log_lik, bic). NaN BIC if fit failed."""
    try:
        model = GaussianHMM(
            n_components=k,
            covariance_type="full",
            n_iter=HMM_ITER,
            random_state=seed,
            tol=1e-3,
        )
        model.fit(X)
        ll = model.score(X)
        # parameter count: startprob (k-1) + transmat (k*(k-1)) + means (k*d)
        # + covar full (k*d*(d+1)/2)
        d = X.shape[1]
        n_params = (k - 1) + k * (k - 1) + k * d + k * d * (d + 1) / 2
        n = X.shape[0]
        bic = -2.0 * ll + n_params * np.log(n)
        return model, ll, bic
    except Exception:
        return None, -np.inf, np.inf


def pick_best_hmm(X: np.ndarray, seed: int) -> Tuple[object, int, Dict[int, float]]:
    bics: Dict[int, float] = {}
    best_k = None
    best_model = None
    best_bic = np.inf
    for k in HMM_STATES:
        model, _, bic = fit_hmm(X, k, seed)
        bics[k] = float(bic)
        if model is not None and bic < best_bic:
            best_bic = bic
            best_k = k
            best_model = model
    return best_model, best_k, bics


def label_states(model, X: np.ndarray) -> np.ndarray:
    if model is None:
        return np.zeros(len(X), dtype=int)
    try:
        return model.predict(X)
    except Exception:
        return np.zeros(len(X), dtype=int)


def state_stats(states: np.ndarray, ret: np.ndarray, rng: np.ndarray) -> Dict[int, Dict]:
    out: Dict[int, Dict] = {}
    for s in np.unique(states):
        m = states == s
        if m.sum() == 0:
            continue
        out[int(s)] = {
            "n": int(m.sum()),
            "frac": float(m.mean()),
            "mean_ret": float(ret[m].mean()),
            "vol": float(ret[m].std(ddof=1)) if m.sum() > 1 else 0.0,
            "mean_abs_ret": float(np.abs(ret[m]).mean()),
            "mean_range": float(rng[m].mean()),
        }
    return out


def turbulent_state(stats: Dict[int, Dict]) -> int:
    return max(stats.keys(), key=lambda s: stats[s]["mean_abs_ret"])


def consolidation_state(stats: Dict[int, Dict]) -> int:
    return min(stats.keys(), key=lambda s: stats[s]["mean_range"])


# ---------------------------------------------------------------------------
# Trend signal & backtest
# ---------------------------------------------------------------------------


def trend_signal(df: pd.DataFrame) -> np.ndarray:
    raw = np.sign(df["ema_f"].values - df["ema_s"].values)
    return raw


def apply_overlay(raw: np.ndarray, states: np.ndarray, turb: int, cons: int, variant: str) -> np.ndarray:
    if variant == "V_base":
        sig = raw.copy()
    elif variant == "V_turbulent":
        sig = np.where(states == turb, raw, 0.0)
    elif variant == "V_non_consol":
        sig = np.where(states != cons, raw, 0.0)
    else:
        raise ValueError(variant)
    return sig


def pnl_from_signal(sig: np.ndarray, ret: np.ndarray, cost_bps: float) -> np.ndarray:
    # Lag 1: position at bar t is sig[t-1]
    pos = np.concatenate([[0.0], sig[:-1]])
    flips = np.abs(np.diff(np.concatenate([[0.0], pos])))
    cost = flips * (cost_bps / 1e4)
    pnl = pos * ret - cost
    return pnl


def sharpe(pnl: np.ndarray, ann: float = BARS_PER_YEAR) -> float:
    if len(pnl) < 5:
        return 0.0
    sd = pnl.std(ddof=1)
    if sd == 0 or not np.isfinite(sd):
        return 0.0
    return float(pnl.mean() / sd * np.sqrt(ann))


def maxdd(eq: np.ndarray) -> float:
    if len(eq) == 0:
        return 0.0
    peak = np.maximum.accumulate(eq)
    dd = (eq - peak)
    return float(dd.min())


# ---------------------------------------------------------------------------
# Walk-forward
# ---------------------------------------------------------------------------


@dataclass
class FoldResult:
    sym: str
    fold: int
    train_idx: Tuple[int, int]
    test_idx: Tuple[int, int]
    k_chosen: int
    bics: Dict[int, float]
    state_stats: Dict[int, Dict]
    turb_state: int
    cons_state: int
    is_sharpe: Dict[str, float]
    oos_sharpe: Dict[str, float]
    oos_pnl: Dict[str, np.ndarray]
    oos_ret: np.ndarray
    oos_states: np.ndarray


def walk_forward(sym: str) -> List[FoldResult]:
    df = load_bars(sym)
    df = make_features(df)
    n = len(df)

    feat_cols = ["ret", "abs_ret", "range_pct"]
    X_all = df[feat_cols].values.astype(np.float64)
    ret = df["ret"].values

    # 4-fold expanding-window walk forward
    # use first 30 % as initial train, then 4 OOS chunks of (n-30%)/4
    base_train = int(n * 0.30)
    remain = n - base_train
    fold_len = remain // N_FOLDS
    results: List[FoldResult] = []

    for f in range(N_FOLDS):
        tr_lo = 0
        tr_hi = base_train + f * fold_len
        te_lo = tr_hi
        te_hi = te_lo + fold_len if f < N_FOLDS - 1 else n
        if te_hi - te_lo < 50:
            continue

        X_tr = X_all[tr_lo:tr_hi]
        # standardize on train
        mu = X_tr.mean(axis=0)
        sd = X_tr.std(axis=0)
        sd[sd == 0] = 1.0
        X_tr_n = (X_tr - mu) / sd

        seed = RNG_SEED + 17 * f + hash(sym) % 1000
        model, k_best, bics = pick_best_hmm(X_tr_n, seed=seed)

        # apply to full series (train + test) for stats; compute test labels
        X_full = X_all[tr_lo:te_hi]
        X_full_n = (X_full - mu) / sd
        states_full = label_states(model, X_full_n)

        stats = state_stats(
            states_full[: tr_hi - tr_lo],
            ret[tr_lo:tr_hi],
            df["range_pct"].values[tr_lo:tr_hi],
        )
        turb = turbulent_state(stats)
        cons = consolidation_state(stats)

        # IS metrics
        is_pnl_var: Dict[str, float] = {}
        for v in VARIANTS:
            raw = trend_signal(df.iloc[tr_lo:tr_hi])
            sig = apply_overlay(raw, states_full[: tr_hi - tr_lo], turb, cons, v)
            pnl = pnl_from_signal(sig, ret[tr_lo:tr_hi], COST_BPS)
            is_pnl_var[v] = sharpe(pnl)

        # OOS metrics
        oos_states = states_full[tr_hi - tr_lo :]
        oos_ret = ret[te_lo:te_hi]
        oos_pnl: Dict[str, np.ndarray] = {}
        oos_sh: Dict[str, float] = {}
        for v in VARIANTS:
            raw = trend_signal(df.iloc[te_lo:te_hi])
            sig = apply_overlay(raw, oos_states, turb, cons, v)
            pnl = pnl_from_signal(sig, oos_ret, COST_BPS)
            oos_pnl[v] = pnl
            oos_sh[v] = sharpe(pnl)

        results.append(
            FoldResult(
                sym=sym,
                fold=f,
                train_idx=(tr_lo, tr_hi),
                test_idx=(te_lo, te_hi),
                k_chosen=int(k_best) if k_best is not None else 0,
                bics={int(k): float(v) for k, v in bics.items()},
                state_stats={int(k): v for k, v in stats.items()},
                turb_state=int(turb),
                cons_state=int(cons),
                is_sharpe=is_pnl_var,
                oos_sharpe=oos_sh,
                oos_pnl=oos_pnl,
                oos_ret=oos_ret,
                oos_states=oos_states,
            )
        )

    return results


# ---------------------------------------------------------------------------
# Audit
# ---------------------------------------------------------------------------


def block_bootstrap_sharpe(pnl: np.ndarray, n_boot: int, block: int, seed: int) -> Tuple[float, float]:
    rng = np.random.default_rng(seed)
    n = len(pnl)
    if n < block * 2:
        return (np.nan, np.nan)
    n_blocks = n // block
    sharpes = np.empty(n_boot)
    for b in range(n_boot):
        starts = rng.integers(0, n - block, size=n_blocks)
        sample = np.concatenate([pnl[s : s + block] for s in starts])
        sharpes[b] = sharpe(sample)
    lo, hi = np.percentile(sharpes, [2.5, 97.5])
    return float(lo), float(hi)


def permutation_test(
    raw: np.ndarray,
    states: np.ndarray,
    turb: int,
    cons: int,
    ret: np.ndarray,
    variant: str,
    observed: float,
    n_perm: int,
    seed: int,
) -> float:
    if variant == "V_base":
        # baseline is invariant to state permutation -> p = NaN
        return float("nan")
    rng = np.random.default_rng(seed)
    states = states.copy()
    hits = 0
    for _ in range(n_perm):
        perm = rng.permutation(states)
        sig = apply_overlay(raw, perm, turb, cons, variant)
        pnl = pnl_from_signal(sig, ret, COST_BPS)
        if sharpe(pnl) >= observed:
            hits += 1
    return (hits + 1) / (n_perm + 1)


def dsr(sr_hat: float, n_obs: int, n_trials: int, skew: float = 0.0, kurt: float = 3.0) -> float:
    """Deflated Sharpe Ratio (Bailey & Lopez de Prado 2014)."""
    from scipy.stats import norm

    if n_obs < 30 or not np.isfinite(sr_hat):
        return float("nan")
    # SR0 ~ E[max SR] under null (no skill) across N_trials
    em = (1 - np.euler_gamma) * norm.ppf(1 - 1.0 / max(n_trials, 2)) + np.euler_gamma * norm.ppf(
        1 - 1.0 / (max(n_trials, 2) * np.e)
    )
    var_sr = (1 - skew * sr_hat + (kurt - 1) / 4 * sr_hat**2) / (n_obs - 1)
    if var_sr <= 0:
        return float("nan")
    z = (sr_hat - em * np.sqrt(var_sr)) / np.sqrt(var_sr)
    return float(norm.cdf(z))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    t0 = time.time()
    print(f"[K123] backend = {HMM_BACKEND}", flush=True)

    per_sym: Dict[str, Dict] = {}
    portfolio_oos: Dict[str, List[np.ndarray]] = {v: [] for v in VARIANTS}
    portfolio_dates: Dict[str, List[pd.Timestamp]] = {v: [] for v in VARIANTS}

    # we'll build a per-symbol-aligned matrix of OOS pnl
    sym_oos_pnl: Dict[str, Dict[str, np.ndarray]] = {}
    sym_oos_ts: Dict[str, np.ndarray] = {}
    sym_per_fold: Dict[str, List[Dict]] = {}

    for sym in SYMBOLS:
        t_sym = time.time()
        folds = walk_forward(sym)
        if not folds:
            print(f"[K123] {sym}: NO folds")
            continue

        # concat OOS across folds
        oos_pnl_concat: Dict[str, np.ndarray] = {v: np.concatenate([f.oos_pnl[v] for f in folds]) for v in VARIANTS}
        oos_ret_concat = np.concatenate([f.oos_ret for f in folds])
        sym_oos_pnl[sym] = oos_pnl_concat

        # IS Sharpe = mean across folds (each fold has its own train-only sharpe)
        is_sh = {v: float(np.mean([f.is_sharpe[v] for f in folds])) for v in VARIANTS}
        oos_sh = {v: sharpe(oos_pnl_concat[v]) for v in VARIANTS}

        # equity curves
        eq = {v: np.cumsum(oos_pnl_concat[v]) for v in VARIANTS}
        dd = {v: maxdd(eq[v]) for v in VARIANTS}

        # state stats aggregated (first fold representative)
        sym_per_fold[sym] = [
            {
                "fold": f.fold,
                "k_chosen": f.k_chosen,
                "bics": f.bics,
                "state_stats": f.state_stats,
                "turb_state": f.turb_state,
                "cons_state": f.cons_state,
                "is_sharpe": f.is_sharpe,
                "oos_sharpe": f.oos_sharpe,
                "train_idx": list(f.train_idx),
                "test_idx": list(f.test_idx),
            }
            for f in folds
        ]

        # k_best counts
        k_counts: Dict[int, int] = {}
        for f in folds:
            k_counts[f.k_chosen] = k_counts.get(f.k_chosen, 0) + 1

        # permutation test per fold for V_turbulent and V_non_consol, take median p
        perm_p: Dict[str, float] = {}
        for v in ["V_turbulent", "V_non_consol"]:
            ps = []
            for f in folds:
                raw = trend_signal(load_bars(sym).pipe(make_features).iloc[f.test_idx[0] : f.test_idx[1]])
                p = permutation_test(
                    raw=raw,
                    states=f.oos_states,
                    turb=f.turb_state,
                    cons=f.cons_state,
                    ret=f.oos_ret,
                    variant=v,
                    observed=f.oos_sharpe[v],
                    n_perm=PERM_N,
                    seed=RNG_SEED + 7 * f.fold + (hash(sym) % 1000),
                )
                ps.append(p)
            perm_p[v] = float(np.nanmedian(ps))
        perm_p["V_base"] = float("nan")

        # cost stress
        stress = {}
        for cost_mult, label in [(0.5, "cost_-50pct"), (1.5, "cost_+50pct")]:
            stress[label] = {}
            for v in VARIANTS:
                pnl_chunks = []
                for f in folds:
                    raw = trend_signal(load_bars(sym).pipe(make_features).iloc[f.test_idx[0] : f.test_idx[1]])
                    sig = apply_overlay(raw, f.oos_states, f.turb_state, f.cons_state, v)
                    pnl_chunks.append(pnl_from_signal(sig, f.oos_ret, COST_BPS * cost_mult))
                stress[label][v] = sharpe(np.concatenate(pnl_chunks))

        per_sym[sym] = {
            "n_folds": len(folds),
            "k_counts": k_counts,
            "is_sharpe": is_sh,
            "oos_sharpe": oos_sh,
            "oos_maxdd": dd,
            "perm_p_value_median": perm_p,
            "cost_stress": stress,
            "n_oos_bars": int(len(oos_ret_concat)),
        }
        print(
            f"[K123] {sym}: OOS Sharpe base={oos_sh['V_base']:+.2f}  "
            f"turb={oos_sh['V_turbulent']:+.2f}  nonC={oos_sh['V_non_consol']:+.2f}  "
            f"({time.time() - t_sym:.1f}s)",
            flush=True,
        )

    # ---------------- Portfolio (equal-weight) ----------------
    # align by index after concat — different syms have different OOS lengths
    # but all start at index 0 of OOS region. Pad to min length.
    min_len = min(len(pnl["V_base"]) for pnl in sym_oos_pnl.values())
    port_pnl: Dict[str, np.ndarray] = {}
    for v in VARIANTS:
        stack = np.stack([sym_oos_pnl[sym][v][:min_len] for sym in sym_oos_pnl], axis=0)
        port_pnl[v] = stack.mean(axis=0)

    port_sh = {v: sharpe(port_pnl[v]) for v in VARIANTS}
    port_dd = {v: maxdd(np.cumsum(port_pnl[v])) for v in VARIANTS}

    # block bootstrap CI for portfolio
    port_ci = {}
    for v in VARIANTS:
        lo, hi = block_bootstrap_sharpe(port_pnl[v], BOOT_N, BOOT_BLOCK, seed=RNG_SEED + hash(v) % 1000)
        port_ci[v] = {"sharpe": port_sh[v], "ci95_lo": lo, "ci95_hi": hi}

    # DSR
    port_dsr = {v: dsr(port_sh[v], len(port_pnl[v]), n_trials=3) for v in VARIANTS}

    # cost stress portfolio
    port_stress = {}
    for label in ["cost_-50pct", "cost_+50pct"]:
        port_stress[label] = {}
        for v in VARIANTS:
            vals = [per_sym[s]["cost_stress"][label][v] for s in per_sym]
            port_stress[label][v] = float(np.mean(vals))

    # ---------------- §6 mini gates ----------------
    best_overlay = max(["V_turbulent", "V_non_consol"], key=lambda v: port_sh[v])
    gates = {
        "improves_baseline_oos": bool(port_sh[best_overlay] > port_sh["V_base"]),
        "improves_baseline_delta": float(port_sh[best_overlay] - port_sh["V_base"]),
        "best_overlay": best_overlay,
        "perm_p_lt_005_majority": bool(
            np.mean(
                [
                    per_sym[s]["perm_p_value_median"][best_overlay] < 0.05
                    for s in per_sym
                    if not np.isnan(per_sym[s]["perm_p_value_median"][best_overlay])
                ]
            )
            > 0.5
        ),
        "ci_lower_positive": bool(port_ci[best_overlay]["ci95_lo"] > 0),
        "dsr_gt_095": bool(np.isfinite(port_dsr[best_overlay]) and port_dsr[best_overlay] > 0.95),
        "cost_stress_robust": bool(
            port_stress["cost_+50pct"][best_overlay] > 0
            and port_stress["cost_+50pct"][best_overlay] >= 0.5 * port_sh[best_overlay]
        ),
        "n_symbols_with_overlay_better": int(
            sum(
                1
                for s in per_sym
                if per_sym[s]["oos_sharpe"][best_overlay] > per_sym[s]["oos_sharpe"]["V_base"]
            )
        ),
    }

    # which symbol benefits most
    deltas = {s: per_sym[s]["oos_sharpe"][best_overlay] - per_sym[s]["oos_sharpe"]["V_base"] for s in per_sym}
    sym_best = max(deltas, key=deltas.get)

    # ---------------- Verdict ----------------
    gates_passed = sum(
        [
            gates["improves_baseline_oos"],
            gates["perm_p_lt_005_majority"],
            gates["ci_lower_positive"],
            gates["dsr_gt_095"],
            gates["cost_stress_robust"],
        ]
    )
    if gates_passed >= 4 and gates["improves_baseline_delta"] > 0.20:
        verdict = "ACCEPT"
    elif gates_passed >= 3 and gates["improves_baseline_oos"]:
        verdict = "CONDITIONAL"
    else:
        verdict = "REJECT"

    summary = {
        "wave": "K123",
        "title": "HMM Regime-Conditional Trend Overlay",
        "backend": HMM_BACKEND,
        "config": {
            "symbols": SYMBOLS,
            "timeframe": TF,
            "ema_fast": EMA_FAST,
            "ema_slow": EMA_SLOW,
            "cost_bps_round_trip": COST_BPS,
            "n_folds": N_FOLDS,
            "hmm_states_tried": HMM_STATES,
            "perm_n": PERM_N,
            "boot_n": BOOT_N,
            "boot_block": BOOT_BLOCK,
            "variants": VARIANTS,
        },
        "per_symbol": per_sym,
        "per_symbol_folds": sym_per_fold,
        "portfolio": {
            "oos_sharpe": port_sh,
            "oos_maxdd": port_dd,
            "ci95": port_ci,
            "dsr": port_dsr,
            "cost_stress": port_stress,
            "n_oos_bars": int(min_len),
        },
        "gates": gates,
        "delta_per_symbol": deltas,
        "symbol_most_helped": sym_best,
        "verdict": verdict,
        "wall_seconds": round(time.time() - t0, 1),
    }

    with open(OUT_JSON, "w") as f:
        json.dump(summary, f, indent=2, default=float)

    # curves
    curves = {
        "portfolio": {v: np.cumsum(port_pnl[v]).tolist() for v in VARIANTS},
        "per_symbol": {
            sym: {v: np.cumsum(sym_oos_pnl[sym][v]).tolist() for v in VARIANTS} for sym in sym_oos_pnl
        },
    }
    with open(OUT_CURVES, "w") as f:
        json.dump(curves, f)

    print(f"\n[K123] DONE in {summary['wall_seconds']}s — verdict {verdict}")
    print(f"[K123] portfolio OOS Sharpe  base={port_sh['V_base']:+.2f}  "
          f"turb={port_sh['V_turbulent']:+.2f}  nonC={port_sh['V_non_consol']:+.2f}")
    print(f"[K123] best overlay = {best_overlay}, delta = {gates['improves_baseline_delta']:+.2f}")
    print(f"[K123] DSR ({best_overlay}) = {port_dsr[best_overlay]:.3f}")


if __name__ == "__main__":
    main()
