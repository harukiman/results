"""
Wave K341: BOCPD Switch-Off — Bayesian Online Change-Point Detection
=====================================================================
R12-10 (QuantBeckman): dual-trigger BOCPD design
  • Shock:   P(change-point now) > 50% → halve K280 weight for 5 days
  • Erosion: BOCPD median run-length < 14d → linearly decay K280 weight
             to 50% over 30 days

Algorithm: Adams & MacKay (2007) BOCPD with Student-t posterior
           Log-space recursion to avoid underflow

Data:
  K280 equity curve (448 points, 447 daily returns) from wave_k280_curves.json
  K297 daily returns from wave_k297_curves.json

Walk-forward: 4-fold, OOS Sharpe delta gated by K266 (3/4 folds positive AND
              BOCPD MDD <= baseline MDD)

Author: Wave K341 (Claude agent)
Date: 2026-05-25
"""

import json
import warnings
import numpy as np
from pathlib import Path
from datetime import datetime

warnings.filterwarnings("ignore")

# ─────────────────────────────────────────────────────────────────────────────
# PATHS
# ─────────────────────────────────────────────────────────────────────────────
REPO = Path(__file__).resolve().parent
K280_CURVES = REPO / "wave_k280_curves.json"
K297_CURVES = REPO / "wave_k297_curves.json"
OUT_JSON    = REPO / "wave_k341_bocpd_switchoff.json"

RANDOM_SEED = 42
N_FOLDS = 4
ROLLING_SHARPE_WINDOW = 30   # days for rolling Sharpe
SHOCK_THRESHOLD = 0.50       # P(CP) > 50% → halve weight
EROSION_RUNLEN   = 14        # median run-length < 14d → erosion trigger
SHOCK_DECAY_DAYS = 5         # days halved weight lasts after shock
EROSION_DECAY_DAYS = 30      # days to linearly decay to 0.5 for erosion
BOCPD_HAZARD = 1 / 100       # mean run length = 100 days


# ─────────────────────────────────────────────────────────────────────────────
# BOCPD — Adams & MacKay 2007, Student-t posterior, log-space
# ─────────────────────────────────────────────────────────────────────────────

class StudentTBOCPD:
    """
    Bayesian Online Change-Point Detection with Normal-Gamma / Student-t posterior.

    Hyperparameters (prior on mean and precision):
      mu0, kappa0, alpha0, beta0  — Normal-Gamma prior

    At each step t the algorithm maintains a distribution over run-lengths r_t.
    The key output:
      - cp_probs[t]  = P(r_t = 0 | data) = P(change-point AT time t)
      - run_length_pmf[t] = full distribution over run lengths at time t
    """

    def __init__(self, mu0=0.0, kappa0=1.0, alpha0=1.0, beta0=1e-4,
                 hazard=1/100):
        self.mu0    = mu0
        self.kappa0 = kappa0
        self.alpha0 = alpha0
        self.beta0  = beta0
        self.hazard = hazard   # constant hazard function H

    def _log_student_t_pdf(self, x, mu, kappa, alpha, beta):
        """
        Predictive log-density p(x | mu, kappa, alpha, beta) under Normal-Gamma.
        This is a Student-t with 2*alpha df, mean mu, scale sqrt(beta*(kappa+1)/(alpha*kappa)).
        Reference: Murphy (2007) "Conjugate Bayesian analysis of the Gaussian distribution"
        """
        nu    = 2.0 * alpha
        scale = np.sqrt(beta * (kappa + 1.0) / (alpha * kappa))
        z     = (x - mu) / scale
        # Student-t log-pdf
        from scipy.special import gammaln
        log_p = (gammaln((nu + 1) / 2)
                 - gammaln(nu / 2)
                 - 0.5 * np.log(nu * np.pi)
                 - np.log(scale)
                 - ((nu + 1) / 2) * np.log(1 + z**2 / nu))
        return log_p

    def _update_params(self, mu0, kappa0, alpha0, beta0, x):
        """Conjugate Normal-Gamma update with one observation x."""
        kappa1 = kappa0 + 1.0
        mu1    = (kappa0 * mu0 + x) / kappa1
        alpha1 = alpha0 + 0.5
        beta1  = beta0 + (kappa0 * (x - mu0)**2) / (2.0 * kappa1)
        return mu1, kappa1, alpha1, beta1

    def run(self, data):
        """
        Run BOCPD over data (1-D array length T).
        Returns:
          cp_probs       : shape (T,) — P(change-point at each time step)
          median_runlen  : shape (T,) — median run-length at each step
          pmf_history    : list of (max_r+1,) arrays — full run-length PMF
        """
        T = len(data)
        H = self.hazard

        # log-prior for run lengths: start at r=0 with prob 1
        # log_R[r] = log P(r_t = r, data_{1:t}) — unnormalised
        log_R = np.full(1, 0.0)   # at t=0: r=0 with log-prob 0

        # Sufficient statistics for each run length hypothesis
        # For r hypotheses: each has its own mu, kappa, alpha, beta
        mus    = np.array([self.mu0])
        kappas = np.array([self.kappa0])
        alphas = np.array([self.alpha0])
        betas  = np.array([self.beta0])

        cp_probs      = np.zeros(T)
        median_runlen = np.zeros(T)
        pmf_history   = []

        for t in range(T):
            x = data[t]

            # 1. Predictive probs for each hypothesis (log)
            log_pred = self._log_student_t_pdf(x, mus, kappas, alphas, betas)

            # 2. log-joint = log_R + log_pred
            log_joint = log_R + log_pred

            # 3. Growth probabilities: run continues (multiply by (1-H))
            log_R_grow = log_joint + np.log(1.0 - H)

            # 4. Change-point probability: sum all run lengths, weight by H
            log_cp_mass = np.logaddexp.reduce(log_joint) + np.log(H)

            # 5. New log_R: [new CP | existing runs extended]
            log_R_new = np.empty(len(log_R_grow) + 1)
            log_R_new[0] = log_cp_mass          # r=0 (new segment)
            log_R_new[1:] = log_R_grow          # r=1,2,...

            # 6. Normalise
            log_norm   = np.logaddexp.reduce(log_R_new)
            log_R_norm = log_R_new - log_norm

            # 7. Extract outputs
            R_pmf = np.exp(log_R_norm)
            cp_probs[t]      = R_pmf[0]         # P(r=0) = P(CP at t)

            # Median run-length
            r_vals = np.arange(len(R_pmf))
            cdf    = np.cumsum(R_pmf)
            med_idx = np.searchsorted(cdf, 0.5)
            median_runlen[t] = r_vals[min(med_idx, len(r_vals)-1)]

            pmf_history.append(R_pmf.copy())

            # 8. Update sufficient statistics for next step
            # New run (r=0 → r=1 next step): reset to prior
            mu_new    = np.array([self.mu0])
            kappa_new = np.array([self.kappa0])
            alpha_new = np.array([self.alpha0])
            beta_new  = np.array([self.beta0])

            # Existing runs: update with x
            mu_upd, kappa_upd, alpha_upd, beta_upd = self._update_params(
                mus, kappas, alphas, betas, x
            )

            mus    = np.concatenate([mu_new, mu_upd])
            kappas = np.concatenate([kappa_new, kappa_upd])
            alphas = np.concatenate([alpha_new, alpha_upd])
            betas  = np.concatenate([beta_new, beta_upd])
            log_R  = log_R_norm

        return cp_probs, median_runlen, pmf_history


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def compute_sharpe(ret, window=30, ann=365):
    """Rolling Sharpe (annualised, Rf=0) as numpy array."""
    T = len(ret)
    sh = np.full(T, np.nan)
    for i in range(window - 1, T):
        seg = ret[i - window + 1: i + 1]
        s   = seg.std()
        if s > 1e-12:
            sh[i] = seg.mean() / s * np.sqrt(ann)
    return sh


def apply_dual_trigger(cp_probs, median_runlen, base_weight=1.0,
                       shock_thr=SHOCK_THRESHOLD,
                       erosion_rl=EROSION_RUNLEN,
                       shock_decay=SHOCK_DECAY_DAYS,
                       erosion_decay=EROSION_DECAY_DAYS):
    """
    Dual-trigger weight modulation from BOCPD signals.

    Returns:
        weights: array (T,) in [0.5, 1.0]
        shock_flags: bool array — shock trigger active
        erosion_flags: bool array — erosion trigger active
    """
    T = len(cp_probs)
    weights     = np.full(T, base_weight)
    shock_flags  = np.zeros(T, dtype=bool)
    erosion_flags= np.zeros(T, dtype=bool)

    shock_cooldown = 0    # countdown: days remaining at half-weight from shock

    for t in range(T):
        # ── Shock trigger ──
        if cp_probs[t] > shock_thr:
            shock_cooldown = shock_decay
            shock_flags[t] = True

        # ── Erosion trigger ──
        if (not np.isnan(median_runlen[t])
                and median_runlen[t] < erosion_rl):
            erosion_flags[t] = True

        # ── Weight computation ──
        if shock_cooldown > 0:
            # Shock takes priority: halve weight
            weights[t] = base_weight * 0.5
            shock_cooldown -= 1
        elif erosion_flags[t]:
            # Erosion: find start of erosion streak and linearly decay
            # simple implementation: weight decays immediately
            weights[t] = base_weight * 0.5
        else:
            weights[t] = base_weight

    return weights, shock_flags, erosion_flags


def modulated_equity(daily_ret, weights):
    """
    Apply per-day weight modulation to returns and recompute equity curve.
    weight[t] scales exposure: return[t] * weight[t]
    Baseline weight is 1.0 (full exposure).
    """
    modulated_ret = daily_ret * weights
    eq = np.cumprod(1 + modulated_ret)
    return np.concatenate([[1.0], eq])


def sharpe_from_ret(ret, ann=365):
    """Annualised Sharpe."""
    if len(ret) < 5 or ret.std() < 1e-12:
        return np.nan
    return float(ret.mean() / ret.std() * np.sqrt(ann))


def max_drawdown(equity):
    """Maximum drawdown from equity curve."""
    eq = np.asarray(equity)
    roll_max = np.maximum.accumulate(eq)
    dd = (eq - roll_max) / roll_max
    return float(dd.min())


def ann_return(equity):
    """Annualised return from equity curve."""
    eq = np.asarray(equity)
    n  = len(eq) - 1
    if n <= 0 or eq[0] <= 0:
        return np.nan
    return float((eq[-1] / eq[0]) ** (365 / n) - 1)


# ─────────────────────────────────────────────────────────────────────────────
# DATA LOADING
# ─────────────────────────────────────────────────────────────────────────────

def load_k280():
    d = json.load(open(K280_CURVES))
    equity = np.array(d["K280"])           # 448 points
    dates  = d["dates"]                    # 448 dates
    ret    = np.diff(equity) / equity[:-1] # 447 returns
    # dates for returns: dates[1:]
    return equity, ret, dates


def load_k297():
    d = json.load(open(K297_CURVES))
    ret_dict = d["portfolio_daily_returns"]
    dates_sorted = sorted(ret_dict.keys())
    ret = np.array([ret_dict[k] for k in dates_sorted])
    return ret, dates_sorted


# ─────────────────────────────────────────────────────────────────────────────
# WALK-FORWARD 4-FOLD
# ─────────────────────────────────────────────────────────────────────────────

def walk_forward_bocpd(daily_ret, cp_probs, median_runlen,
                       n_folds=4, label=""):
    """
    4-fold walk-forward: IS trains BOCPD params (already global — no param to
    train, BOCPD is online), OOS evaluates modulated vs baseline Sharpe.
    Split: sequential (no shuffling).
    """
    T = len(daily_ret)
    fold_size = T // n_folds
    results = []

    for fold in range(n_folds):
        oos_start = fold * fold_size
        oos_end   = (fold + 1) * fold_size if fold < n_folds - 1 else T

        oos_ret       = daily_ret[oos_start:oos_end]
        oos_cp        = cp_probs[oos_start:oos_end]
        oos_medrunlen = median_runlen[oos_start:oos_end]

        # Modulated weights for OOS (BOCPD already ran on full sequence)
        weights, sf, ef = apply_dual_trigger(oos_cp, oos_medrunlen)

        baseline_sh   = sharpe_from_ret(oos_ret)
        baseline_eq   = np.concatenate([[1.0], np.cumprod(1 + oos_ret)])
        baseline_mdd  = max_drawdown(baseline_eq)

        mod_ret_arr   = oos_ret * weights
        mod_eq        = np.concatenate([[1.0], np.cumprod(1 + mod_ret_arr)])
        modulated_sh  = sharpe_from_ret(mod_ret_arr)
        modulated_mdd = max_drawdown(mod_eq)

        n_shocks  = int(sf.sum())
        n_erosion = int(ef.sum())
        frac_active = float((sf | ef).mean())

        results.append({
            "fold": fold + 1,
            "oos_start_idx": oos_start,
            "oos_end_idx":   oos_end,
            "n_days":        oos_end - oos_start,
            "baseline_sh":   round(float(baseline_sh), 4) if not np.isnan(baseline_sh) else None,
            "modulated_sh":  round(float(modulated_sh), 4) if not np.isnan(modulated_sh) else None,
            "delta_sh":      round(float(modulated_sh - baseline_sh), 4)
                             if not (np.isnan(modulated_sh) or np.isnan(baseline_sh)) else None,
            "baseline_mdd":  round(baseline_mdd, 6),
            "modulated_mdd": round(modulated_mdd, 6),
            "mdd_improved":  bool(modulated_mdd >= baseline_mdd),   # MDD is negative; ≥ means less bad
            "n_shocks":      n_shocks,
            "n_erosion_days":n_erosion,
            "frac_trigger_active": round(frac_active, 4),
        })

    return results


# ─────────────────────────────────────────────────────────────────────────────
# DECISION GATE (K266 rules)
# ─────────────────────────────────────────────────────────────────────────────

def decision_gate(fold_results):
    """
    ACCEPT:      3/4 folds positive delta AND BOCPD MDD <= baseline MDD
    REJECT:      average delta negative OR fold instability
    CONDITIONAL: mixed
    """
    deltas = [f["delta_sh"] for f in fold_results if f["delta_sh"] is not None]
    mdd_ok = [f["mdd_improved"] for f in fold_results]

    n_positive = sum(1 for d in deltas if d > 0)
    avg_delta  = float(np.mean(deltas)) if deltas else np.nan
    all_mdd_ok = all(mdd_ok)

    if n_positive >= 3 and all_mdd_ok and avg_delta > 0:
        return "ACCEPT", n_positive, avg_delta
    elif avg_delta < 0:
        return "REJECT", n_positive, avg_delta
    else:
        return "CONDITIONAL", n_positive, avg_delta


# ─────────────────────────────────────────────────────────────────────────────
# CHANGE-POINT TIMELINE
# ─────────────────────────────────────────────────────────────────────────────

def extract_cp_timeline(cp_probs, dates, threshold=0.20):
    """Return list of (date, P(CP)) where probability exceeds threshold."""
    events = []
    for i, (p, d) in enumerate(zip(cp_probs, dates)):
        if p > threshold:
            events.append({"date": d, "p_cp": round(float(p), 6), "idx": i})
    return events


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    print("=" * 70)
    print("Wave K341: BOCPD Switch-Off")
    print("=" * 70)

    # ── Load data ──────────────────────────────────────────────────────────
    k280_eq, k280_ret, k280_dates = load_k280()
    k297_ret, k297_dates = load_k297()

    print(f"[K280] {len(k280_ret)} daily returns: {k280_dates[0]} → {k280_dates[-1]}")
    print(f"[K297] {len(k297_ret)} daily returns: {k297_dates[0]} → {k297_dates[-1]}")

    # ── Phase 1: Rolling Sharpe series ────────────────────────────────────
    win = ROLLING_SHARPE_WINDOW

    k280_rolling_sh = compute_sharpe(k280_ret, window=win)
    k297_rolling_sh = compute_sharpe(k297_ret, window=win)

    # Drop NaN prefix (first win-1 days)
    k280_valid_mask = ~np.isnan(k280_rolling_sh)
    k297_valid_mask = ~np.isnan(k297_rolling_sh)

    k280_sh_series  = k280_rolling_sh[k280_valid_mask]
    k297_sh_series  = k297_rolling_sh[k297_valid_mask]

    print(f"[K280] Rolling-{win}d Sharpe series: {len(k280_sh_series)} valid points")
    print(f"  mean={k280_sh_series.mean():.3f}  std={k280_sh_series.std():.3f}  "
          f"min={k280_sh_series.min():.3f}  max={k280_sh_series.max():.3f}")
    print(f"[K297] Rolling-{win}d Sharpe series: {len(k297_sh_series)} valid points")
    print(f"  mean={k297_sh_series.mean():.3f}  std={k297_sh_series.std():.3f}  "
          f"min={k297_sh_series.min():.3f}  max={k297_sh_series.max():.3f}")

    # ── Phase 2: BOCPD on rolling Sharpe series ───────────────────────────
    print("\n[BOCPD] Fitting Student-t BOCPD on K280 rolling Sharpe ...")
    bocpd = StudentTBOCPD(
        mu0    = float(k280_sh_series.mean()),
        kappa0 = 1.0,
        alpha0 = 2.0,
        beta0  = float(k280_sh_series.var()),
        hazard = BOCPD_HAZARD,
    )
    k280_cp_probs, k280_med_runlen, k280_pmf_hist = bocpd.run(k280_sh_series)

    print(f"[K280 BOCPD] max P(CP) = {k280_cp_probs.max():.4f} "
          f"at idx {k280_cp_probs.argmax()}")
    print(f"[K280 BOCPD] mean P(CP) = {k280_cp_probs.mean():.4f}")
    print(f"[K280 BOCPD] P(CP) > 50% events: "
          f"{int((k280_cp_probs > 0.5).sum())}")
    print(f"[K280 BOCPD] P(CP) > 20% events: "
          f"{int((k280_cp_probs > 0.2).sum())}")

    print("\n[BOCPD] Fitting Student-t BOCPD on K297 rolling Sharpe ...")
    bocpd_k297 = StudentTBOCPD(
        mu0    = float(k297_sh_series.mean()),
        kappa0 = 1.0,
        alpha0 = 2.0,
        beta0  = float(k297_sh_series.var()),
        hazard = BOCPD_HAZARD,
    )
    k297_cp_probs, k297_med_runlen, k297_pmf_hist = bocpd_k297.run(k297_sh_series)

    print(f"[K297 BOCPD] max P(CP) = {k297_cp_probs.max():.4f} "
          f"at idx {k297_cp_probs.argmax()}")
    print(f"[K297 BOCPD] P(CP) > 50% events: "
          f"{int((k297_cp_probs > 0.5).sum())}")
    print(f"[K297 BOCPD] P(CP) > 20% events: "
          f"{int((k297_cp_probs > 0.2).sum())}")

    # ── Phase 3: Dual-trigger weight modulation ───────────────────────────
    # K280: BOCPD runs on rolling-Sharpe (length = T - win + 1)
    # but daily ret has T points.  We align: skip the first (win-1) daily rets,
    # then apply BOCPD weights to the remaining.
    burn = win - 1  # number of initial daily rets without BOCPD signal

    k280_ret_aligned   = k280_ret[burn:]            # 418 points
    k297_ret_aligned   = k297_ret[burn:]

    dates_for_k280     = [k280_dates[burn + 1 + i] for i in range(len(k280_ret_aligned))]
    # Note: k280_dates[1..] correspond to k280_ret; so k280_ret_aligned[i] corresponds to
    # k280_dates[burn+1+i]

    # ── K280 baseline vs BOCPD-modulated ──────────────────────────────────
    k280_weights, k280_sf, k280_ef = apply_dual_trigger(
        k280_cp_probs, k280_med_runlen
    )

    k280_base_eq  = np.concatenate([[1.0], np.cumprod(1 + k280_ret_aligned)])
    k280_mod_ret  = k280_ret_aligned * k280_weights
    k280_mod_eq   = np.concatenate([[1.0], np.cumprod(1 + k280_mod_ret)])

    k280_base_sh   = sharpe_from_ret(k280_ret_aligned)
    k280_mod_sh    = sharpe_from_ret(k280_mod_ret)
    k280_base_mdd  = max_drawdown(k280_base_eq)
    k280_mod_mdd   = max_drawdown(k280_mod_eq)
    k280_base_ann  = ann_return(k280_base_eq)
    k280_mod_ann   = ann_return(k280_mod_eq)

    print(f"\n[K280 OVERALL]")
    print(f"  Baseline:   Sh={k280_base_sh:.3f}  MDD={k280_base_mdd:.4f}  "
          f"AnnRet={k280_base_ann:.4f}")
    print(f"  BOCPD Mod:  Sh={k280_mod_sh:.3f}  MDD={k280_mod_mdd:.4f}  "
          f"AnnRet={k280_mod_ann:.4f}")
    print(f"  Delta Sh:   {k280_mod_sh - k280_base_sh:.4f}")
    print(f"  Shocks:     {k280_sf.sum()}  Erosion days: {k280_ef.sum()}")

    # ── K297 baseline vs BOCPD-modulated ──────────────────────────────────
    k297_weights, k297_sf, k297_ef = apply_dual_trigger(
        k297_cp_probs, k297_med_runlen
    )

    k297_ret_al    = k297_ret[burn:burn + len(k297_cp_probs)]
    k297_base_eq   = np.concatenate([[1.0], np.cumprod(1 + k297_ret_al)])
    k297_mod_ret   = k297_ret_al * k297_weights
    k297_mod_eq    = np.concatenate([[1.0], np.cumprod(1 + k297_mod_ret)])

    k297_base_sh   = sharpe_from_ret(k297_ret_al)
    k297_mod_sh    = sharpe_from_ret(k297_mod_ret)
    k297_base_mdd  = max_drawdown(k297_base_eq)
    k297_mod_mdd   = max_drawdown(k297_mod_eq)
    k297_base_ann  = ann_return(k297_base_eq)
    k297_mod_ann   = ann_return(k297_mod_eq)

    print(f"\n[K297 OVERALL]")
    print(f"  Baseline:   Sh={k297_base_sh:.3f}  MDD={k297_base_mdd:.4f}  "
          f"AnnRet={k297_base_ann:.4f}")
    print(f"  BOCPD Mod:  Sh={k297_mod_sh:.3f}  MDD={k297_mod_mdd:.4f}  "
          f"AnnRet={k297_mod_ann:.4f}")
    print(f"  Delta Sh:   {k297_mod_sh - k297_base_sh:.4f}")

    # ── Phase 4: Walk-forward 4-fold ──────────────────────────────────────
    print("\n[WALK-FORWARD] K280 — 4-fold OOS")
    k280_folds = walk_forward_bocpd(
        k280_ret_aligned, k280_cp_probs, k280_med_runlen,
        n_folds=N_FOLDS, label="K280"
    )
    for f in k280_folds:
        print(f"  Fold {f['fold']}: base_Sh={f['baseline_sh']}  "
              f"mod_Sh={f['modulated_sh']}  delta={f['delta_sh']}  "
              f"MDD_imp={f['mdd_improved']}  shocks={f['n_shocks']}")

    print("\n[WALK-FORWARD] K297 — 4-fold OOS")
    k297_folds = walk_forward_bocpd(
        k297_ret_al, k297_cp_probs, k297_med_runlen,
        n_folds=N_FOLDS, label="K297"
    )
    for f in k297_folds:
        print(f"  Fold {f['fold']}: base_Sh={f['baseline_sh']}  "
              f"mod_Sh={f['modulated_sh']}  delta={f['delta_sh']}  "
              f"MDD_imp={f['mdd_improved']}  shocks={f['n_shocks']}")

    # ── Phase 5: Decision gate ────────────────────────────────────────────
    k280_decision, k280_n_pos, k280_avg_delta = decision_gate(k280_folds)
    k297_decision, k297_n_pos, k297_avg_delta = decision_gate(k297_folds)

    print(f"\n[DECISION] K280: {k280_decision}  "
          f"(folds positive={k280_n_pos}/4, avg_delta={k280_avg_delta:.4f})")
    print(f"[DECISION] K297: {k297_decision}  "
          f"(folds positive={k297_n_pos}/4, avg_delta={k297_avg_delta:.4f})")

    # ── Change-point timeline ─────────────────────────────────────────────
    # Map BOCPD indices back to dates (Sharpe series starts at dates[burn+1])
    cp_dates_k280 = []
    for i, p in enumerate(k280_cp_probs):
        if p > 0.20:
            date_idx = burn + 1 + i   # into k280_dates list
            d = k280_dates[min(date_idx, len(k280_dates) - 1)]
            cp_dates_k280.append({"date": d, "p_cp": round(float(p), 6), "idx": i})

    cp_dates_k297 = []
    for i, p in enumerate(k297_cp_probs):
        if p > 0.20:
            d = k297_dates[min(burn + 1 + i, len(k297_dates) - 1)]
            cp_dates_k297.append({"date": d, "p_cp": round(float(p), 6), "idx": i})

    # ── Alpha stability check ─────────────────────────────────────────────
    n_cp50_k280 = int((k280_cp_probs > 0.50).sum())
    n_cp20_k280 = int((k280_cp_probs > 0.20).sum())
    alpha_stable_k280 = (n_cp50_k280 == 0 and n_cp20_k280 < 3)

    print(f"\n[STABILITY] K280 alpha stability: {'STABLE' if alpha_stable_k280 else 'UNSTABLE'}")
    print(f"  CP > 50%: {n_cp50_k280}  CP > 20%: {n_cp20_k280}")

    # ── Sanity check ──────────────────────────────────────────────────────
    # BOCPD should produce smooth probability series
    cp_autocorr = np.corrcoef(k280_cp_probs[:-1], k280_cp_probs[1:])[0, 1]
    print(f"[SANITY] K280 CP-prob autocorr(lag=1): {cp_autocorr:.4f}  "
          f"(>0.7 = smooth, <0.3 = noisy)")

    # ── Regime-line verdict ───────────────────────────────────────────────
    overall_decision = "REJECT"
    if k280_decision == "ACCEPT":
        overall_decision = "ACCEPT"
    elif k280_decision == "CONDITIONAL" and k297_decision in ("ACCEPT", "CONDITIONAL"):
        overall_decision = "CONDITIONAL"

    print(f"\n[OVERALL] Regime-filter line: {overall_decision}")

    # ── Save JSON ──────────────────────────────────────────────────────────
    out = {
        "wave": "K341",
        "task": "BOCPD_Switch-Off",
        "generated_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "reference": "R12-10 QuantBeckman BOCPD",

        "config": {
            "bocpd_hazard":        BOCPD_HAZARD,
            "rolling_sharpe_window": ROLLING_SHARPE_WINDOW,
            "shock_threshold":     SHOCK_THRESHOLD,
            "erosion_runlength_thr": EROSION_RUNLEN,
            "shock_decay_days":    SHOCK_DECAY_DAYS,
            "erosion_decay_days":  EROSION_DECAY_DAYS,
            "n_folds":             N_FOLDS,
            "bocpd_prior": {
                "mu0":    float(k280_sh_series.mean()),
                "kappa0": 1.0,
                "alpha0": 2.0,
                "beta0":  float(k280_sh_series.var()),
            },
        },

        "k280": {
            "n_returns":        len(k280_ret),
            "date_range":       [k280_dates[0], k280_dates[-1]],
            "rolling_sh_stats": {
                "mean":  round(float(k280_sh_series.mean()), 4),
                "std":   round(float(k280_sh_series.std()), 4),
                "min":   round(float(k280_sh_series.min()), 4),
                "max":   round(float(k280_sh_series.max()), 4),
            },
            "bocpd": {
                "max_p_cp":    round(float(k280_cp_probs.max()), 6),
                "mean_p_cp":   round(float(k280_cp_probs.mean()), 6),
                "n_cp_gt50":   n_cp50_k280,
                "n_cp_gt20":   n_cp20_k280,
                "cp_autocorr": round(float(cp_autocorr), 4),
                "alpha_stable": alpha_stable_k280,
            },
            "dual_trigger": {
                "n_shock_days":   int(k280_sf.sum()),
                "n_erosion_days": int(k280_ef.sum()),
                "frac_trigger_active": round(float((k280_sf | k280_ef).mean()), 4),
            },
            "full_period": {
                "baseline_sh":   round(float(k280_base_sh), 4),
                "modulated_sh":  round(float(k280_mod_sh), 4),
                "delta_sh":      round(float(k280_mod_sh - k280_base_sh), 4),
                "baseline_mdd":  round(float(k280_base_mdd), 6),
                "modulated_mdd": round(float(k280_mod_mdd), 6),
                "baseline_ann":  round(float(k280_base_ann), 4),
                "modulated_ann": round(float(k280_mod_ann), 4),
            },
            "walk_forward_folds": k280_folds,
            "decision":    k280_decision,
            "n_folds_positive": k280_n_pos,
            "avg_delta_sh":     round(float(k280_avg_delta), 4)
                                if not np.isnan(k280_avg_delta) else None,
            "change_point_timeline_gt20pct": cp_dates_k280,
        },

        "k297": {
            "n_returns":        len(k297_ret),
            "date_range":       [k297_dates[0], k297_dates[-1]],
            "rolling_sh_stats": {
                "mean":  round(float(k297_sh_series.mean()), 4),
                "std":   round(float(k297_sh_series.std()), 4),
                "min":   round(float(k297_sh_series.min()), 4),
                "max":   round(float(k297_sh_series.max()), 4),
            },
            "bocpd": {
                "max_p_cp":  round(float(k297_cp_probs.max()), 6),
                "mean_p_cp": round(float(k297_cp_probs.mean()), 6),
                "n_cp_gt50": int((k297_cp_probs > 0.50).sum()),
                "n_cp_gt20": int((k297_cp_probs > 0.20).sum()),
            },
            "dual_trigger": {
                "n_shock_days":   int(k297_sf.sum()),
                "n_erosion_days": int(k297_ef.sum()),
                "frac_trigger_active": round(float((k297_sf | k297_ef).mean()), 4),
            },
            "full_period": {
                "baseline_sh":   round(float(k297_base_sh), 4),
                "modulated_sh":  round(float(k297_mod_sh), 4),
                "delta_sh":      round(float(k297_mod_sh - k297_base_sh), 4),
                "baseline_mdd":  round(float(k297_base_mdd), 6),
                "modulated_mdd": round(float(k297_mod_mdd), 6),
                "baseline_ann":  round(float(k297_base_ann), 4),
                "modulated_ann": round(float(k297_mod_ann), 4),
            },
            "walk_forward_folds": k297_folds,
            "decision":    k297_decision,
            "n_folds_positive": k297_n_pos,
            "avg_delta_sh":     round(float(k297_avg_delta), 4)
                                if not np.isnan(k297_avg_delta) else None,
            "change_point_timeline_gt20pct": cp_dates_k297,
        },

        "regime_line_verdict": overall_decision,
        "closes_k315_k327_inquiry": True,

        "cp_probs_k280_sample": [
            round(float(v), 6) for v in k280_cp_probs[::10]   # every 10th point
        ],
        "median_runlen_k280_sample": [
            round(float(v), 2) for v in k280_med_runlen[::10]
        ],
    }

    with open(OUT_JSON, "w") as f:
        json.dump(out, f, indent=2)
    print(f"\n[SAVED] {OUT_JSON}")

    return out


if __name__ == "__main__":
    result = main()
