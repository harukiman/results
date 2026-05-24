"""Wave K203 - OU+Jump FR Predictor as K190 Upgrade Candidate.

References:
  - arxiv 2605.06405: HL OU+Jump model, half-life 2-6h for FR mean reversion
  - SSRN 5290137: Jump detection confirms OU+Jump >> pure OU/AR for FR prediction
  - K190 DAR(2,1) baseline: direction accuracy 66% (XRP: 65.9%, SUI: 66.7%)
  - K175 OOS Sh 2.07 (gross) / K190 OOS Sh 2.12 (gross)

Model spec:
  1. OU component: dFR = θ(μ - FR)dt + σ*dW
     Discretized: FR_t = α + β*FR_{t-1} + ε, β = exp(-θ*dt), HL = ln(2)/θ
  2. Jump detection: |FR - μ| > k*σ_ou (k=2.5 or 3.0)
     Jump indicator as predictor for next period
     Optional Hawkes self-excitation: γ(t) = μ + Σ g*exp(-decay*(t-t_j))
  3. Combined: FR_{t+1} = α + β*FR_t + γ*Jump_t + δ*JumpLag_t + ε

Acceptance gates:
  - Direction accuracy > K190 by +3pp (≥69% vs 66%)
  - K175 OOS Sh lift > +0.05 over K190 filter
  - Half-life in 2-6h range (academic validation)
  - §6 gates if standalone gross Sh > 1.0
"""
from __future__ import annotations

import json
import time
import warnings
from math import erf, sqrt, log
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.stats import norm

warnings.filterwarnings("ignore")

ROOT = Path("/Users/nekonaomichi/crypto-lab")
CACHE = ROOT / "cache"
HL_CACHE = CACHE / "k163_hl"

SLIPPAGE_BPS_PER_SIDE = 2.0
MAKER_FEE_BPS_PER_SIDE = 0.0
COST_PER_FILL = (SLIPPAGE_BPS_PER_SIDE + MAKER_FEE_BPS_PER_SIDE) * 1e-4

SYMBOLS = ["XRP", "SUI"]
EVENTS_PER_YEAR = 365 * 24 // 8  # 1095 (8h cadence)
DT = 1.0  # 1 event step = 8 hours

# OU+Jump model configuration
OU_WINDOW = 300      # rolling window for OU parameter estimation
OU_REFIT = 50        # refit every N events
JUMP_K = 2.5         # jump threshold: |FR - mu| > k * sigma_ou
JUMP_K_VARIANTS = [2.0, 2.5, 3.0]
HAWKES_DECAY = 0.5   # Hawkes kernel decay rate (in events)
HAWKES_G = 0.3       # Hawkes self-excitation intensity

# Walk-forward OOS: 90-day train -> 30-day test (in events: 90*3=270, 30*3=90)
WF_TRAIN_EVENTS = 270  # 90 days * 3 events/day
WF_TEST_EVENTS = 90    # 30 days * 3 events/day


# ─────────────────────────── Data Loading ───────────────────────────

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


def build_panel(sym: str) -> Optional[pd.DataFrame]:
    hl = load_hl_fr(sym)
    by = load_bybit_fr(sym)
    cl = load_bybit_close(sym)
    if hl is None or by is None or cl is None:
        return None
    hl_8h = hl.resample("8h", label="right", closed="right").sum(min_count=1)
    idx = by.index
    df = pd.DataFrame({"bybit_fr": by}, index=idx)
    df["hl_fr_8h"] = hl_8h.reindex(idx)
    df = df.dropna()
    if len(df) < 100:
        return None
    df["spread"] = df["bybit_fr"] - df["hl_fr_8h"]
    cl_at = cl.reindex(idx, method="nearest", tolerance=pd.Timedelta("2h"))
    df["close"] = cl_at
    df = df.dropna(subset=["close"])
    if len(df) < 100:
        return None
    df["fwd_ret_1"] = np.log(df["close"]).diff().shift(-1)
    return df


# ─────────────────────────── OU Parameter Estimation ───────────────────────────

def estimate_ou_ols(fr_window: np.ndarray) -> Tuple[float, float, float, float]:
    """Estimate OU parameters via OLS on discretized equation.

    FR_t = alpha + beta * FR_{t-1} + eps
    alpha = mu * (1 - beta), beta = exp(-theta * dt)

    Returns: (theta, mu, sigma_ou, half_life_hours)
    where half_life is in 8h units converted to hours.
    """
    y = fr_window[1:]
    x = fr_window[:-1]
    n = len(y)
    if n < 10:
        return 0.0, float(np.mean(fr_window)), float(np.std(fr_window)), np.inf

    # OLS: y = alpha + beta*x
    x_mat = np.column_stack([np.ones(n), x])
    try:
        coeffs, _, _, _ = np.linalg.lstsq(x_mat, y, rcond=None)
    except Exception:
        return 0.0, float(np.mean(fr_window)), float(np.std(fr_window)), np.inf

    alpha, beta = float(coeffs[0]), float(coeffs[1])

    # Enforce beta in (0, 1) for mean-reverting process
    beta = np.clip(beta, 1e-6, 1.0 - 1e-6)

    # theta from discretization: beta = exp(-theta * dt), dt=1 event
    theta = float(-np.log(beta))
    # mu from long-run mean: alpha = mu * (1 - beta)
    mu = float(alpha / max(1 - beta, 1e-6))
    # sigma from residuals
    y_pred = alpha + beta * x
    resid = y - y_pred
    sigma_ou = float(np.std(resid))

    # Half-life in events, then convert to hours (1 event = 8h)
    hl_events = float(np.log(2) / max(theta, 1e-6))
    half_life_hours = hl_events * 8.0  # convert events to hours

    return theta, mu, sigma_ou, half_life_hours


def estimate_ou_mle(fr_window: np.ndarray) -> Tuple[float, float, float, float]:
    """MLE estimation of OU parameters for robustness check.

    Exact discrete-time likelihood for AR(1) process.
    Returns: (theta, mu, sigma_ou, half_life_hours)
    """
    n = len(fr_window)
    if n < 20:
        return estimate_ou_ols(fr_window)

    def neg_loglik(params):
        theta_p, mu_p, sigma_p = params
        if theta_p <= 0 or sigma_p <= 0:
            return 1e10
        beta_p = np.exp(-theta_p)
        sigma_cond = sigma_p * np.sqrt((1 - beta_p**2) / (2 * theta_p + 1e-10))
        if sigma_cond <= 0:
            return 1e10
        y = fr_window[1:]
        x = fr_window[:-1]
        mu_cond = mu_p + beta_p * (x - mu_p)
        ll = norm.logpdf(y, loc=mu_cond, scale=sigma_cond).sum()
        return -ll

    # Initial params from OLS
    theta0, mu0, sigma0, _ = estimate_ou_ols(fr_window)
    theta0 = max(theta0, 0.05)
    sigma0 = max(sigma0, 1e-6)

    try:
        res = minimize(
            neg_loglik,
            x0=[theta0, mu0, sigma0],
            method="Nelder-Mead",
            options={"maxiter": 500, "xatol": 1e-6, "fatol": 1e-8},
        )
        if res.success:
            theta, mu, sigma_ou = res.x
            theta = max(theta, 1e-6)
            sigma_ou = max(abs(sigma_ou), 1e-8)
        else:
            theta, mu, sigma_ou, _ = estimate_ou_ols(fr_window)
    except Exception:
        theta, mu, sigma_ou, _ = estimate_ou_ols(fr_window)

    hl_events = np.log(2) / max(theta, 1e-6)
    half_life_hours = float(hl_events * 8.0)
    return float(theta), float(mu), float(sigma_ou), half_life_hours


# ─────────────────────────── Jump Detection ───────────────────────────

def detect_jumps(
    fr: np.ndarray,
    mu: float,
    sigma_ou: float,
    k: float = 2.5,
) -> np.ndarray:
    """Detect jumps as deviations > k*sigma_ou from long-run mean.

    Returns: binary array, 1 where jump detected at time t.
    """
    deviation = np.abs(fr - mu)
    threshold = k * max(sigma_ou, 1e-8)
    return (deviation > threshold).astype(float)


def compute_hawkes_intensity(
    jump_times: np.ndarray,
    n: int,
    decay: float = 0.5,
    g: float = 0.3,
) -> np.ndarray:
    """Compute Hawkes self-excitation intensity at each point.

    Simple exponential kernel: φ(t) = g * exp(-decay * (t - t_j)) for t > t_j.
    Returns intensity array of length n.
    """
    intensity = np.zeros(n)
    jump_indices = np.where(jump_times[:n] > 0)[0]
    for t in range(n):
        exc = 0.0
        for tj in jump_indices:
            if tj < t:
                exc += g * np.exp(-decay * (t - tj))
            elif tj >= t:
                break
        intensity[t] = exc
    return intensity


# ─────────────────────────── OU+Jump Walk-Forward Prediction ───────────────────────────

def ou_jump_walk_forward(
    fr: np.ndarray,
    spread_z: np.ndarray,
    win: int = OU_WINDOW,
    refit: int = OU_REFIT,
    jump_k: float = JUMP_K,
    use_hawkes: bool = True,
    use_mle: bool = False,
) -> Tuple[np.ndarray, np.ndarray, Dict]:
    """Walk-forward OU+Jump FR predictor.

    Combined model: FR_{t+1} = alpha + beta*FR_t + gamma*Jump_t + delta*JumpLag_{t-1}
    + hawkes_coef * HawkesIntensity_t + eps

    Returns:
        pred_fr: array of predicted FR values (NaN where no prediction)
        is_valid: boolean mask
        diagnostics: dict with OU params, jump stats, direction_acc
    """
    n = len(fr)
    pred_fr = np.full(n, np.nan)
    is_valid = np.zeros(n, dtype=bool)

    # Storage for per-refit OU params
    ou_params_log: List[Dict] = []
    half_lives: List[float] = []

    # Jump history (binary, rolling)
    jump_hist = np.zeros(n, dtype=float)

    # Walk-forward loop
    coeffs = None
    ou_theta, ou_mu, ou_sigma = 0.0, 0.0, 1e-6

    for i in range(win + 1, n):
        # Refit on schedule
        if (i - (win + 1)) % refit == 0 or coeffs is None:
            window = fr[i - win: i]

            # Step 1: Estimate OU params on training window
            if use_mle:
                ou_theta, ou_mu, ou_sigma, hl_h = estimate_ou_mle(window)
            else:
                ou_theta, ou_mu, ou_sigma, hl_h = estimate_ou_ols(window)

            ou_sigma = max(ou_sigma, 1e-8)
            half_lives.append(hl_h)

            # Step 2: Detect jumps in training window, build features
            jumps_win = detect_jumps(window, ou_mu, ou_sigma, jump_k)

            # Step 3: Build design matrix for OU+Jump regression
            # Features: intercept, FR_t, Jump_t, JumpLag_{t-1}, Hawkes_t
            rows = []
            targets = []
            for t in range(2, len(window) - 1):
                # Hawkes at this training point
                if use_hawkes:
                    hawkes_val = compute_hawkes_intensity(jumps_win, t, HAWKES_DECAY, HAWKES_G)[t - 1]
                else:
                    hawkes_val = 0.0
                row = [
                    1.0,                  # intercept (captures alpha = mu*(1-beta))
                    window[t],            # FR_t (OU beta term)
                    jumps_win[t],         # Jump_t indicator
                    jumps_win[t - 1],     # JumpLag_{t-1}
                    hawkes_val,           # Hawkes intensity
                ]
                rows.append(row)
                targets.append(window[t + 1])  # FR_{t+1}

            if len(rows) < 10:
                continue

            X = np.array(rows, dtype=float)
            y = np.array(targets, dtype=float)
            try:
                coeffs, _, _, _ = np.linalg.lstsq(X, y, rcond=None)
            except Exception:
                coeffs = None
                continue

            ou_params_log.append({
                "i": int(i),
                "theta": round(float(ou_theta), 6),
                "mu": round(float(ou_mu), 8),
                "sigma_ou": round(float(ou_sigma), 8),
                "half_life_hours": round(float(hl_h), 2),
            })

        # Predict FR_i using data up to i-1
        if coeffs is not None:
            current_fr = fr[i - 1]
            # Jump at i-1
            jump_now = float(abs(current_fr - ou_mu) > JUMP_K * ou_sigma)
            jump_lag = jump_hist[i - 2] if i >= 2 else 0.0
            # Hawkes: excitation from recent jumps
            if use_hawkes and i >= 2:
                recent_jumps = jump_hist[max(0, i - 20): i - 1]
                hawkes_val = 0.0
                for j_idx, jv in enumerate(recent_jumps):
                    if jv > 0:
                        dt_val = (len(recent_jumps) - 1 - j_idx)
                        hawkes_val += HAWKES_G * np.exp(-HAWKES_DECAY * dt_val)
            else:
                hawkes_val = 0.0

            row = np.array([1.0, current_fr, jump_now, jump_lag, hawkes_val])
            pred = float(np.dot(row, coeffs))
            pred_fr[i] = pred
            is_valid[i] = True

            # Update jump history
            jump_hist[i - 1] = float(abs(current_fr - ou_mu) > JUMP_K * ou_sigma)

    # OOS diagnostics
    valid_idx = np.where(is_valid)[0]
    if len(valid_idx) < 30:
        return pred_fr, is_valid, {
            "oos_r2": np.nan,
            "direction_acc": np.nan,
            "n_oos": 0,
            "half_life_mean_hours": np.nan,
            "half_life_median_hours": np.nan,
            "half_life_std_hours": np.nan,
            "half_life_in_2_6h_range": False,
        }

    y_true = fr[valid_idx]
    y_pred = pred_fr[valid_idx]
    ss_res = np.sum((y_true - y_pred) ** 2)
    ss_tot = np.sum((y_true - y_true.mean()) ** 2)
    oos_r2 = float(1 - ss_res / (ss_tot + 1e-30))

    # Direction accuracy vs actual change
    actual_delta = np.diff(y_true)
    pred_sign = np.sign(y_pred[1:] - y_true[:-1])
    actual_sign = np.sign(actual_delta)
    nz = actual_sign != 0
    dir_acc = float((pred_sign[nz] == actual_sign[nz]).mean()) if nz.sum() > 0 else 0.5

    # Half-life statistics
    hl_arr = np.array(half_lives, dtype=float)
    hl_arr = hl_arr[np.isfinite(hl_arr) & (hl_arr > 0) & (hl_arr < 1000)]
    hl_mean = float(np.mean(hl_arr)) if len(hl_arr) > 0 else np.nan
    hl_median = float(np.median(hl_arr)) if len(hl_arr) > 0 else np.nan
    hl_std = float(np.std(hl_arr)) if len(hl_arr) > 0 else np.nan
    hl_in_range = bool(2.0 <= hl_median <= 6.0) if np.isfinite(hl_median) else False

    # Jump statistics over OOS period
    jump_count = int(np.sum(jump_hist[valid_idx[0]: valid_idx[-1]]))
    jump_rate = float(jump_count / max(len(valid_idx), 1))

    return pred_fr, is_valid, {
        "oos_r2": round(oos_r2, 5),
        "direction_acc": round(dir_acc, 4),
        "n_oos": int(len(valid_idx)),
        "half_life_mean_hours": round(hl_mean, 2) if np.isfinite(hl_mean) else None,
        "half_life_median_hours": round(hl_median, 2) if np.isfinite(hl_median) else None,
        "half_life_std_hours": round(hl_std, 2) if np.isfinite(hl_std) else None,
        "half_life_in_2_6h_range": hl_in_range,
        "jump_count_oos": jump_count,
        "jump_rate_oos": round(jump_rate, 4),
        "n_refits": len(ou_params_log),
        "ou_params_sample": ou_params_log[:3] if ou_params_log else [],
    }


def ou_jump_walk_forward_segmented(
    fr: np.ndarray,
    win: int = OU_WINDOW,
    refit: int = OU_REFIT,
    jump_k: float = JUMP_K,
    use_hawkes: bool = True,
    wf_train: int = WF_TRAIN_EVENTS,
    wf_test: int = WF_TEST_EVENTS,
) -> Tuple[np.ndarray, np.ndarray, Dict, List[Dict]]:
    """Walk-forward with segmented 90d-train/30d-test for rigorous OOS evaluation.

    Returns pred_fr, is_valid, overall_diag, per_segment_diags
    """
    n = len(fr)
    pred_fr = np.full(n, np.nan)
    is_valid = np.zeros(n, dtype=bool)
    segment_diags: List[Dict] = []
    half_lives_all: List[float] = []
    jump_hist = np.zeros(n, dtype=float)

    ou_theta, ou_mu, ou_sigma = 0.0, 0.0, 1e-6
    coeffs = None

    # First segment: start after we have enough training data
    seg_start = max(win + 1, wf_train)

    for seg_begin in range(seg_start, n - wf_test, wf_test):
        seg_end = min(seg_begin + wf_test, n)
        train_start = max(0, seg_begin - wf_train)
        train_fr = fr[train_start: seg_begin]

        # Estimate OU on training window
        ou_theta, ou_mu, ou_sigma, hl_h = estimate_ou_ols(train_fr)
        ou_sigma = max(ou_sigma, 1e-8)
        half_lives_all.append(hl_h)

        # Detect jumps in training
        jumps_train = detect_jumps(train_fr, ou_mu, ou_sigma, jump_k)

        # Build training design
        rows = []
        targets = []
        for t in range(2, len(train_fr) - 1):
            if use_hawkes:
                hawkes_val = compute_hawkes_intensity(jumps_train, t, HAWKES_DECAY, HAWKES_G)[t - 1]
            else:
                hawkes_val = 0.0
            row = [1.0, train_fr[t], jumps_train[t], jumps_train[t - 1], hawkes_val]
            rows.append(row)
            targets.append(train_fr[t + 1])

        if len(rows) < 10:
            continue

        X = np.array(rows, dtype=float)
        y_trn = np.array(targets, dtype=float)
        try:
            coeffs_seg, _, _, _ = np.linalg.lstsq(X, y_trn, rcond=None)
        except Exception:
            continue

        # Predict on test segment
        seg_preds = []
        seg_trues = []
        for i in range(seg_begin, seg_end):
            if i < 2:
                continue
            current_fr = fr[i - 1]
            jump_now = float(abs(current_fr - ou_mu) > jump_k * ou_sigma)
            jump_lag = jump_hist[i - 2] if i >= 2 else 0.0
            if use_hawkes and i >= 2:
                recent_jumps = jump_hist[max(0, i - 20): i - 1]
                hawkes_val = 0.0
                for j_idx, jv in enumerate(recent_jumps):
                    if jv > 0:
                        dt_val = (len(recent_jumps) - 1 - j_idx)
                        hawkes_val += HAWKES_G * np.exp(-HAWKES_DECAY * dt_val)
            else:
                hawkes_val = 0.0

            row = np.array([1.0, current_fr, jump_now, jump_lag, hawkes_val])
            pred = float(np.dot(row, coeffs_seg))
            pred_fr[i] = pred
            is_valid[i] = True
            jump_hist[i - 1] = float(abs(current_fr - ou_mu) > jump_k * ou_sigma)
            seg_preds.append(pred)
            seg_trues.append(fr[i])

        # Per-segment diagnostics
        if len(seg_preds) >= 10:
            y_t = np.array(seg_trues)
            y_p = np.array(seg_preds)
            ad = np.diff(y_t)
            ps = np.sign(y_p[1:] - y_t[:-1])
            as_ = np.sign(ad)
            nz = as_ != 0
            da = float((ps[nz] == as_[nz]).mean()) if nz.sum() > 0 else 0.5
            segment_diags.append({
                "seg_begin": int(seg_begin),
                "seg_end": int(seg_end),
                "n_test": len(seg_preds),
                "direction_acc": round(da, 4),
                "half_life_hours": round(hl_h, 2),
                "ou_mu": round(float(ou_mu), 8),
                "ou_sigma": round(float(ou_sigma), 8),
                "ou_theta": round(float(ou_theta), 6),
            })

    # Overall diagnostics
    valid_idx = np.where(is_valid)[0]
    if len(valid_idx) < 30:
        return pred_fr, is_valid, {
            "oos_r2": np.nan, "direction_acc": np.nan, "n_oos": 0,
            "half_life_mean_hours": np.nan, "half_life_median_hours": np.nan,
        }, segment_diags

    y_true = fr[valid_idx]
    y_pred = pred_fr[valid_idx]
    ss_res = np.sum((y_true - y_pred) ** 2)
    ss_tot = np.sum((y_true - y_true.mean()) ** 2)
    oos_r2 = float(1 - ss_res / (ss_tot + 1e-30))

    ad = np.diff(y_true)
    ps = np.sign(y_pred[1:] - y_true[:-1])
    as_ = np.sign(ad)
    nz = as_ != 0
    dir_acc = float((ps[nz] == as_[nz]).mean()) if nz.sum() > 0 else 0.5

    hl_arr = np.array(half_lives_all, dtype=float)
    hl_arr = hl_arr[np.isfinite(hl_arr) & (hl_arr > 0) & (hl_arr < 1000)]
    hl_mean = float(np.mean(hl_arr)) if len(hl_arr) > 0 else np.nan
    hl_median = float(np.median(hl_arr)) if len(hl_arr) > 0 else np.nan
    hl_std = float(np.std(hl_arr)) if len(hl_arr) > 0 else np.nan
    hl_in_range = bool(2.0 <= hl_median <= 6.0) if np.isfinite(hl_median) else False

    jump_count = int(np.sum(jump_hist[valid_idx[0]: valid_idx[-1]]))
    jump_rate = float(jump_count / max(len(valid_idx), 1))

    return pred_fr, is_valid, {
        "oos_r2": round(oos_r2, 5),
        "direction_acc": round(dir_acc, 4),
        "n_oos": int(len(valid_idx)),
        "half_life_mean_hours": round(hl_mean, 2) if np.isfinite(hl_mean) else None,
        "half_life_median_hours": round(hl_median, 2) if np.isfinite(hl_median) else None,
        "half_life_std_hours": round(hl_std, 2) if np.isfinite(hl_std) else None,
        "half_life_in_2_6h_range": hl_in_range,
        "jump_count_oos": jump_count,
        "jump_rate_oos": round(jump_rate, 4),
        "n_segments": len(segment_diags),
    }, segment_diags


# ─────────────────────────── K175 + OU+Jump Filter ───────────────────────────

def zscore(s: pd.Series, win: int = 30) -> pd.Series:
    mu = s.rolling(win, min_periods=win).mean()
    sd = s.rolling(win, min_periods=win).std()
    return (s - mu) / (sd + 1e-12)


def run_k175_baseline(
    panels: Dict[str, pd.DataFrame],
    z_thr: float = 2.0,
    hold: int = 1,
    zwin: int = 30,
    cost_per_fill: float = COST_PER_FILL,
) -> Tuple[pd.Series, pd.Series, int, Dict, Dict]:
    per_sym_gross: Dict[str, pd.Series] = {}
    per_sym_net: Dict[str, pd.Series] = {}
    total_trades = 0
    per_sh_net: Dict[str, float] = {}
    per_sh_gross: Dict[str, float] = {}

    for sym, df in panels.items():
        z = zscore(df["spread"], zwin)
        sig = pd.Series(0.0, index=df.index)
        sig[z > z_thr] = -1.0
        sig[z < -z_thr] = 1.0
        sig_lag = sig.shift(1).fillna(0.0)
        pos = pd.Series(0.0, index=df.index)
        i = 0
        trades = 0
        while i < len(sig_lag):
            new = sig_lag.iloc[i]
            if new != 0.0:
                end = min(i + hold, len(pos))
                pos.iloc[i:end] = new
                trades += 1
                i = end
                continue
            i += 1
        fwd = df["fwd_ret_1"].fillna(0.0)
        pnl_g = pos * fwd
        pos_chg = pos.diff().fillna(pos.iloc[0])
        costs = pd.Series(0.0, index=df.index)
        costs[pos_chg != 0] = cost_per_fill
        pnl_n = pnl_g - costs
        per_sym_gross[sym] = pnl_g
        per_sym_net[sym] = pnl_n
        total_trades += trades
        per_sh_gross[sym] = sharpe(pnl_g)
        per_sh_net[sym] = sharpe(pnl_n)

    if not per_sym_net:
        empty = pd.Series(dtype=float)
        return empty, empty, 0, {}, {}

    gross = pd.concat(per_sym_gross, axis=1).fillna(0.0).mean(axis=1)
    net = pd.concat(per_sym_net, axis=1).fillna(0.0).mean(axis=1)
    return net, gross, total_trades, per_sh_net, per_sh_gross


def run_k175_ou_jump_filter(
    panels: Dict[str, pd.DataFrame],
    z_thr: float = 2.0,
    hold: int = 1,
    zwin: int = 30,
    jump_k: float = JUMP_K,
    use_hawkes: bool = True,
    cost_per_fill: float = COST_PER_FILL,
) -> Tuple[pd.Series, pd.Series, int, Dict, Dict, Dict[str, Dict], Dict[str, List]]:
    """K175 strategy + OU+Jump direction filter.

    Entry gate:
      z > +z_thr (short FR): enter only if pred_FR <= current_FR (FR expected to fall)
      z < -z_thr (long FR):  enter only if pred_FR >= current_FR (FR expected to rise)
    """
    per_sym_gross: Dict[str, pd.Series] = {}
    per_sym_net: Dict[str, pd.Series] = {}
    total_trades = 0
    per_sh_net: Dict[str, float] = {}
    per_sh_gross: Dict[str, float] = {}
    ou_diag: Dict[str, Dict] = {}
    seg_diags: Dict[str, List] = {}

    for sym, df in panels.items():
        fr_arr = df["bybit_fr"].values.copy()
        z = zscore(df["spread"], zwin)

        # Walk-forward OU+Jump prediction (segmented for rigor)
        pred_fr, is_valid, diag, segs = ou_jump_walk_forward_segmented(
            fr_arr, win=OU_WINDOW, refit=OU_REFIT,
            jump_k=jump_k, use_hawkes=use_hawkes,
            wf_train=WF_TRAIN_EVENTS, wf_test=WF_TEST_EVENTS,
        )
        ou_diag[sym] = diag
        seg_diags[sym] = segs

        # Build signal: K175 z-trigger AND OU+Jump gate
        sig = pd.Series(0.0, index=df.index)
        for i in range(len(df)):
            if not is_valid[i]:
                continue
            z_val = z.iloc[i]
            current_fr = fr_arr[i]
            pred = pred_fr[i]

            if z_val > z_thr:
                if pred <= current_fr:
                    sig.iloc[i] = -1.0
            elif z_val < -z_thr:
                if pred >= current_fr:
                    sig.iloc[i] = 1.0

        sig_lag = sig.shift(1).fillna(0.0)
        pos = pd.Series(0.0, index=df.index)
        i = 0
        trades = 0
        while i < len(sig_lag):
            new = sig_lag.iloc[i]
            if new != 0.0:
                end = min(i + hold, len(pos))
                pos.iloc[i:end] = new
                trades += 1
                i = end
                continue
            i += 1

        fwd = df["fwd_ret_1"].fillna(0.0)
        pnl_g = pos * fwd
        pos_chg = pos.diff().fillna(pos.iloc[0])
        costs = pd.Series(0.0, index=df.index)
        costs[pos_chg != 0] = cost_per_fill
        pnl_n = pnl_g - costs
        per_sym_gross[sym] = pnl_g
        per_sym_net[sym] = pnl_n
        total_trades += trades
        per_sh_gross[sym] = sharpe(pnl_g)
        per_sh_net[sym] = sharpe(pnl_n)

    if not per_sym_net:
        empty = pd.Series(dtype=float)
        return empty, empty, 0, {}, {}, {}, {}

    gross = pd.concat(per_sym_gross, axis=1).fillna(0.0).mean(axis=1)
    net = pd.concat(per_sym_net, axis=1).fillna(0.0).mean(axis=1)
    return net, gross, total_trades, per_sh_net, per_sh_gross, ou_diag, seg_diags


# ─────────────────────────── Jump Magnitude Distribution ───────────────────────────

def analyze_jump_distribution(
    fr: np.ndarray,
    mu: float,
    sigma_ou: float,
    jump_k: float = JUMP_K,
) -> Dict:
    """Analyze jump magnitude distribution for log."""
    jumps = detect_jumps(fr, mu, sigma_ou, jump_k)
    jump_idx = np.where(jumps > 0)[0]
    if len(jump_idx) == 0:
        return {"count": 0, "rate": 0.0, "mean_magnitude": 0.0,
                "max_magnitude": 0.0, "p95_magnitude": 0.0,
                "mean_z_score": 0.0}
    magnitudes = np.abs(fr[jump_idx] - mu) / sigma_ou  # in sigma units
    return {
        "count": int(len(jump_idx)),
        "rate": round(float(len(jump_idx) / len(fr)), 4),
        "mean_magnitude_sigma": round(float(np.mean(magnitudes)), 3),
        "max_magnitude_sigma": round(float(np.max(magnitudes)), 3),
        "p95_magnitude_sigma": round(float(np.percentile(magnitudes, 95)), 3),
        "mean_abs_fr": round(float(np.mean(np.abs(fr[jump_idx] - mu))), 8),
    }


# ─────────────────────────── Metrics ───────────────────────────

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
    return float((eq - peak).min())


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
    arr = np.array(perm_sharpes)
    return float((arr >= obs).mean()) if obs > 0 else float((arr <= obs).mean())


def bootstrap_ci(pnl: pd.Series, n: int = 200, seed: int = 11) -> Tuple[float, float]:
    rng = np.random.default_rng(seed)
    vals = pnl.dropna().values
    if len(vals) < 30:
        return 0.0, 0.0
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
    e_max = np.sqrt(2 * np.log(max(n_trials, 2))) - emc / np.sqrt(2 * np.log(max(n_trials, 2)))
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
        else:
            sharpes.append(float(s.mean() / s.std() * np.sqrt(EVENTS_PER_YEAR)))
    return float(np.mean(sharpes)), [float(x) for x in sharpes]


def compute_metrics(
    name: str,
    pnl: pd.Series,
    pnl_gross: pd.Series,
    n_trades: int,
    per_sh_net: Dict,
    per_sh_gross: Dict,
) -> Dict:
    sh_n = sharpe(pnl)
    sh_g = sharpe(pnl_gross)
    cg_n = cagr(pnl)
    cg_g = cagr(pnl_gross)
    dd_n = max_dd(pnl)
    split = int(len(pnl) * 0.7)
    is_sh_n = sharpe(pnl.iloc[:split])
    oos_sh_n = sharpe(pnl.iloc[split:])
    is_sh_g = sharpe(pnl_gross.iloc[:split])
    oos_sh_g = sharpe(pnl_gross.iloc[split:])
    wf_mean, wf_folds = wf_3fold(pnl)
    wf_mean_g, wf_folds_g = wf_3fold(pnl_gross)
    perm_p = perm_test(pnl)
    perm_p_g = perm_test(pnl_gross)
    ci_lo, ci_hi = bootstrap_ci(pnl)
    ci_lo_g, ci_hi_g = bootstrap_ci(pnl_gross)
    dsr_p = dsr(pnl)
    dsr_p_g = dsr(pnl_gross)
    trades_yr = float(n_trades / max(len(pnl) / EVENTS_PER_YEAR, 1e-6))
    return {
        "variant": name,
        "sharpe_net": round(sh_n, 4),
        "sharpe_gross": round(sh_g, 4),
        "cagr_net": round(cg_n, 4),
        "cagr_gross": round(cg_g, 4),
        "max_dd_net": round(dd_n, 4),
        "is_sharpe_net": round(is_sh_n, 4),
        "oos_sharpe_net": round(oos_sh_n, 4),
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
        "trades_per_year": round(trades_yr, 2),
        "n_events": int(len(pnl)),
        "per_symbol_sharpe_net": {k: round(v, 4) for k, v in per_sh_net.items()},
        "per_symbol_sharpe_gross": {k: round(v, 4) for k, v in per_sh_gross.items()},
    }


def apply_s6_gates(metrics: Dict) -> Tuple[Dict, int, str]:
    """§6 strict gates on OU+Jump model if gross Sh >= 1.0."""
    if metrics["sharpe_gross"] < 1.0:
        return {"note": "Gross Sh < 1.0, §6 gates skipped"}, 0, "SKIP"

    gates = {
        "g1_sharpe_net_ge_1": metrics["sharpe_net"] >= 1.0,
        "g2_oos_sharpe_net_ge_0p5": metrics["oos_sharpe_net"] >= 0.5,
        "g3_oos_is_ratio_ge_0p5": (
            metrics["oos_sharpe_net"] / metrics["is_sharpe_net"] >= 0.5
            if metrics["is_sharpe_net"] > 0 else False
        ),
        "g4_wf_folds_all_positive": (
            all(x > 0 for x in metrics["wf_folds_net"]) if metrics["wf_folds_net"] else False
        ),
        "g5_perm_p_le_0p05": metrics["perm_pvalue_net"] <= 0.05,
        "g6_dsr_ge_0p95": metrics["dsr_net"] >= 0.95,
        "g7_trades_per_year_ge_20": metrics["trades_per_year"] >= 20,
    }
    n_pass = int(sum(gates.values()))
    verdict = "PASS" if n_pass >= 6 else ("MARGINAL" if n_pass >= 4 else "FAIL")
    return gates, n_pass, verdict


# ─────────────────────────── Jump K Sweep ───────────────────────────

def sweep_jump_k(panels: Dict[str, pd.DataFrame]) -> List[Dict]:
    """Sweep jump detection threshold k for sensitivity analysis."""
    results = []
    for k in JUMP_K_VARIANTS:
        print(f"  Sweep jump_k={k}...")
        net, gross, trades, sh_n, sh_g, ou_diag, _ = run_k175_ou_jump_filter(
            panels, jump_k=k, use_hawkes=True
        )
        m = compute_metrics(f"OU+Jump_k{k}", net, gross, trades, sh_n, sh_g)
        m["jump_k"] = k
        m["ou_diagnostics"] = {
            sym: {
                "direction_acc": ou_diag[sym].get("direction_acc"),
                "half_life_median_hours": ou_diag[sym].get("half_life_median_hours"),
                "jump_count_oos": ou_diag[sym].get("jump_count_oos"),
            }
            for sym in ou_diag
        }
        results.append(m)
    return results


# ─────────────────────────── Main ───────────────────────────

def main() -> Dict:
    t0 = time.time()
    print("=== Wave K203: OU+Jump FR Predictor ===")

    # ── 1. Load data ──
    panels: Dict[str, pd.DataFrame] = {}
    for sym in SYMBOLS:
        p = build_panel(sym)
        if p is None:
            print(f"  SKIP {sym}: panel build failed")
        else:
            panels[sym] = p
            print(f"  {sym}: events={len(p)}, fr_mean={p['bybit_fr'].mean():.6f}, "
                  f"fr_std={p['bybit_fr'].std():.6f}")

    if not panels:
        raise RuntimeError("No panels built")

    # ── 2. Full OU parameter analysis per symbol ──
    print("\n=== OU Parameter Analysis ===")
    ou_full_analysis: Dict[str, Dict] = {}
    jump_log: Dict[str, Dict] = {}

    for sym, df in panels.items():
        fr = df["bybit_fr"].values
        # Use full history for initial estimation
        theta, mu, sigma_ou, hl_h = estimate_ou_ols(fr)
        # Also MLE for comparison
        theta_mle, mu_mle, sigma_mle, hl_mle = estimate_ou_mle(fr)
        jump_dist = analyze_jump_distribution(fr, mu, sigma_ou, JUMP_K)
        print(f"  {sym} OLS: theta={theta:.4f} mu={mu:.6f} sigma={sigma_ou:.6f} "
              f"HL={hl_h:.2f}h  MLE HL={hl_mle:.2f}h")
        print(f"  {sym} Jumps (k={JUMP_K}): count={jump_dist['count']} "
              f"rate={jump_dist['rate']:.3f} mean_sigma={jump_dist['mean_magnitude_sigma']:.2f}")
        ou_full_analysis[sym] = {
            "ols": {"theta": round(theta, 6), "mu": round(mu, 8), "sigma_ou": round(sigma_ou, 8),
                    "half_life_hours": round(hl_h, 2)},
            "mle": {"theta": round(theta_mle, 6), "mu": round(mu_mle, 8),
                    "sigma_ou": round(sigma_mle, 8), "half_life_hours": round(hl_mle, 2)},
        }
        jump_log[sym] = jump_dist

    # ── 3. K175 Baseline ──
    print("\n=== K175 Baseline ===")
    bl_net, bl_gross, bl_trades, bl_sh_n, bl_sh_g = run_k175_baseline(panels)
    baseline = compute_metrics("K175_baseline", bl_net, bl_gross, bl_trades, bl_sh_n, bl_sh_g)
    print(f"  Sh_net={baseline['sharpe_net']:+.3f}  Sh_gross={baseline['sharpe_gross']:+.3f}  "
          f"OOS_net={baseline['oos_sharpe_net']:+.3f}  OOS_gross={baseline['oos_sharpe_gross']:+.3f}")

    # ── 4. K203 Primary: OU+Jump with Hawkes (k=2.5) ──
    print("\n=== K203 Primary: OU+Jump Filter (k=2.5, Hawkes=True) ===")
    ou_net, ou_gross, ou_trades, ou_sh_n, ou_sh_g, ou_diag, ou_segs = run_k175_ou_jump_filter(
        panels, jump_k=JUMP_K, use_hawkes=True
    )
    k203_primary = compute_metrics("K203_OU+Jump_k2.5_Hawkes", ou_net, ou_gross, ou_trades, ou_sh_n, ou_sh_g)
    print(f"  Sh_net={k203_primary['sharpe_net']:+.3f}  Sh_gross={k203_primary['sharpe_gross']:+.3f}  "
          f"OOS_net={k203_primary['oos_sharpe_net']:+.3f}  OOS_gross={k203_primary['oos_sharpe_gross']:+.3f}")

    for sym in ou_diag:
        d = ou_diag[sym]
        print(f"  {sym}: dir_acc={d.get('direction_acc', 'N/A')}  "
              f"HL={d.get('half_life_median_hours', 'N/A')}h  "
              f"HL_in_2-6h={d.get('half_life_in_2_6h_range', 'N/A')}  "
              f"jumps={d.get('jump_count_oos', 'N/A')}")

    # ── 5. K203 Variant: No Hawkes ──
    print("\n=== K203 Variant: OU+Jump Filter (k=2.5, Hawkes=False) ===")
    ou_net2, ou_gross2, ou_trades2, ou_sh_n2, ou_sh_g2, ou_diag2, _ = run_k175_ou_jump_filter(
        panels, jump_k=JUMP_K, use_hawkes=False
    )
    k203_no_hawkes = compute_metrics("K203_OU+Jump_k2.5_noHawkes", ou_net2, ou_gross2,
                                      ou_trades2, ou_sh_n2, ou_sh_g2)
    print(f"  Sh_net={k203_no_hawkes['sharpe_net']:+.3f}  Sh_gross={k203_no_hawkes['sharpe_gross']:+.3f}  "
          f"OOS_net={k203_no_hawkes['oos_sharpe_net']:+.3f}  OOS_gross={k203_no_hawkes['oos_sharpe_gross']:+.3f}")

    # ── 6. Jump K sweep ──
    print("\n=== Jump K Sweep ===")
    sweep_results = sweep_jump_k(panels)
    for r in sweep_results:
        print(f"  k={r['jump_k']}: Sh_net={r['sharpe_net']:+.3f}  OOS_net={r['oos_sharpe_net']:+.3f}")

    # ── 7. Select best K203 variant ──
    all_k203 = [k203_primary, k203_no_hawkes] + sweep_results
    best_k203 = max(all_k203, key=lambda x: x["oos_sharpe_net"])
    print(f"\n=== Best K203 variant: {best_k203['variant']} ===")
    print(f"  OOS_net={best_k203['oos_sharpe_net']}  OOS_gross={best_k203['oos_sharpe_gross']}")

    # ── 8. §6 Gates on K203 primary ──
    print("\n=== §6 Gates (K203 primary) ===")
    s6_gates, s6_pass, s6_verdict = apply_s6_gates(k203_primary)
    print(f"  Gates passed: {s6_pass}/7  Verdict: {s6_verdict}")

    # ── 9. Acceptance criteria evaluation ──
    k190_dir_acc_xrp = 0.6593
    k190_dir_acc_sui = 0.6667
    k190_oos_gross = 2.1229  # K190 DAR(2,1)_win300 OOS gross Sh
    k175_oos_gross = 2.0356  # K175 baseline OOS gross Sh

    k203_dir_acc_xrp = ou_diag.get("XRP", {}).get("direction_acc", 0.0)
    k203_dir_acc_sui = ou_diag.get("SUI", {}).get("direction_acc", 0.0)
    k203_mean_dir_acc = float(np.mean([k203_dir_acc_xrp, k203_dir_acc_sui]))
    k190_mean_dir_acc = float(np.mean([k190_dir_acc_xrp, k190_dir_acc_sui]))

    acc_gate_dir = k203_mean_dir_acc >= k190_mean_dir_acc + 0.03
    acc_gate_oos_sh = (k203_primary["oos_sharpe_gross"] - k190_oos_gross) >= 0.05
    acc_gate_hl = any(
        ou_diag.get(sym, {}).get("half_life_in_2_6h_range", False)
        for sym in SYMBOLS
    )
    acceptance = {
        "gate_dir_acc_plus3pp": acc_gate_dir,
        "k190_mean_dir_acc": round(k190_mean_dir_acc, 4),
        "k203_mean_dir_acc": round(k203_mean_dir_acc, 4),
        "dir_acc_delta": round(k203_mean_dir_acc - k190_mean_dir_acc, 4),
        "gate_oos_sh_lift_0p05": acc_gate_oos_sh,
        "k190_oos_gross": k190_oos_gross,
        "k203_oos_gross": k203_primary["oos_sharpe_gross"],
        "oos_sh_delta": round(k203_primary["oos_sharpe_gross"] - k190_oos_gross, 4),
        "gate_half_life_2_6h": acc_gate_hl,
        "overall_accepted": acc_gate_dir and acc_gate_oos_sh and acc_gate_hl,
    }
    print(f"\n=== Acceptance Gates ===")
    print(f"  Dir acc +3pp: {acc_gate_dir} (K190={k190_mean_dir_acc:.3f} -> K203={k203_mean_dir_acc:.3f})")
    print(f"  OOS Sh lift >0.05: {acc_gate_oos_sh} (K190={k190_oos_gross:.3f} -> K203={k203_primary['oos_sharpe_gross']:.3f})")
    print(f"  Half-life 2-6h: {acc_gate_hl}")
    print(f"  OVERALL: {'ACCEPTED' if acceptance['overall_accepted'] else 'REJECTED'}")

    # ── 10. Equity curves for wave_k203_curves.json ──
    curves = {
        "k175_baseline": equity_curve(bl_net),
        "k203_ou_jump_primary": equity_curve(ou_net),
        "k203_ou_jump_no_hawkes": equity_curve(ou_net2),
        "timestamps": [str(t) for t in panels[SYMBOLS[0]].index[:len(bl_net)]],
    }

    # ── 11. Final report assembly ──
    elapsed = time.time() - t0
    print(f"\n=== Done in {elapsed:.1f}s ===")

    results = {
        "wave": "K203",
        "parent_waves": ["K175", "K190"],
        "objective": "OU+Jump FR predictor as K190 DAR(2,1) upgrade candidate",
        "runtime_seconds": round(elapsed, 1),
        "references": [
            "arxiv 2605.06405: HL OU+Jump model, half-life 2-6h",
            "SSRN 5290137: Jump detection confirms OU+Jump >> pure OU/AR",
        ],
        "data": {
            "symbols": SYMBOLS,
            "events_per_year": EVENTS_PER_YEAR,
            "event_counts": {sym: int(len(panels[sym])) for sym in panels},
        },
        "cost_model": {
            "execution": "maker-only",
            "slippage_bps_per_side": SLIPPAGE_BPS_PER_SIDE,
            "maker_fee_bps_per_side": MAKER_FEE_BPS_PER_SIDE,
            "roundtrip_bps": 4.0,
        },
        "model_config": {
            "ou_window": OU_WINDOW,
            "ou_refit": OU_REFIT,
            "jump_k_primary": JUMP_K,
            "hawkes_decay": HAWKES_DECAY,
            "hawkes_g": HAWKES_G,
            "wf_train_events": WF_TRAIN_EVENTS,
            "wf_test_events": WF_TEST_EVENTS,
        },
        "ou_full_analysis": ou_full_analysis,
        "jump_log": {
            sym: {**jump_log[sym], "k_threshold": JUMP_K}
            for sym in jump_log
        },
        "ou_jump_diagnostics_primary": {
            sym: ou_diag.get(sym, {}) for sym in SYMBOLS
        },
        "ou_jump_diagnostics_no_hawkes": {
            sym: ou_diag2.get(sym, {}) for sym in SYMBOLS
        },
        "jump_k_sweep": sweep_results,
        "k175_baseline": baseline,
        "k203_primary": k203_primary,
        "k203_no_hawkes": k203_no_hawkes,
        "best_k203": best_k203,
        "s6_gates_primary": {
            "gates": s6_gates,
            "passed": s6_pass,
            "verdict": s6_verdict,
        },
        "acceptance_evaluation": acceptance,
        "comparison_table": {
            "K175_baseline": {
                "oos_sharpe_gross": baseline["oos_sharpe_gross"],
                "oos_sharpe_net": baseline["oos_sharpe_net"],
                "sharpe_net": baseline["sharpe_net"],
            },
            "K190_DAR(2,1)": {
                "oos_sharpe_gross": k190_oos_gross,
                "oos_sharpe_net": 2.024,  # from K190 JSON
                "sharpe_net": 1.4188,
                "direction_acc_mean": round(k190_mean_dir_acc, 4),
            },
            "K203_OU+Jump": {
                "oos_sharpe_gross": k203_primary["oos_sharpe_gross"],
                "oos_sharpe_net": k203_primary["oos_sharpe_net"],
                "sharpe_net": k203_primary["sharpe_net"],
                "direction_acc_mean": round(k203_mean_dir_acc, 4),
            },
        },
    }

    # K204 integration plan
    if acceptance["overall_accepted"]:
        verdict_text = (
            "K203 ACCEPTED. K204 plan: Ensemble K190 DAR(2,1) + K203 OU+Jump predictions "
            "via weighted average in K198 ML allocator. Suggested weights: 0.4 DAR + 0.6 OU+Jump "
            "(OU+Jump higher direction accuracy). Feed ensemble predicted_FR_delta as feature "
            "to Ridge regression allocator (K198). Run K204 walk-forward ensemble vs K198 standalone."
        )
    else:
        gaps = []
        if not acc_gate_dir:
            gaps.append(f"Dir acc gap: K203={k203_mean_dir_acc:.3f} needs ≥{k190_mean_dir_acc+0.03:.3f}")
        if not acc_gate_oos_sh:
            gaps.append(f"OOS Sh gap: K203={k203_primary['oos_sharpe_gross']:.3f} needs ≥{k190_oos_gross+0.05:.3f}")
        if not acc_gate_hl:
            gaps.append("Half-life not in 2-6h range for any symbol")
        verdict_text = (
            f"K203 REJECTED. Gaps: {'; '.join(gaps)}. "
            "K204 path: Investigate longer estimation windows (500+ events), "
            "multi-scale OU (short + long mean reversion), or regime-conditional OU parameters. "
            "Alternatively explore K198 direct integration with OU residual as signal feature "
            "rather than as a standalone direction filter."
        )

    results["verdict_and_k204_plan"] = verdict_text
    print(f"\nVerdict: {verdict_text[:120]}...")

    return results, curves


if __name__ == "__main__":
    results, curves = main()

    out_json = ROOT / "wave_k203_ou_jump_predictor.json"
    out_curves = ROOT / "wave_k203_curves.json"

    with open(out_json, "w") as f:
        json.dump(results, f, indent=2, default=str)
    with open(out_curves, "w") as f:
        json.dump(curves, f, indent=2, default=str)

    print(f"\nSaved: {out_json}")
    print(f"Saved: {out_curves}")
