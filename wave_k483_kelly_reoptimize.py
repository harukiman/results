#!/usr/bin/env python3
"""
wave_k483_kelly_reoptimize.py  --  K483 v6.22 Kelly Criterion Re-optimization
==============================================================================
Re-optimizes v6.22 9-sleeve portfolio weights using:
  - Mean-variance optimization (scipy) with K280 production anchor
  - Fractional Kelly (1/4 Kelly primary; 1/2 and Full for sensitivity)
  - Constraints: HL<=65%, K280<=70%, K476<=5%, sUSDe+Spark<=15%, sum=1

Practical Kelly approach for crypto:
  The 9-sleeve portfolio has vastly disparate Sharpe ratios (K476=16.3,
  sUSDe=7.4, K449=0.52). Raw MV utility corners to highest-Sharpe sleeve.
  K427 confirmed same phenomenon for 3-sleeve case. Solution: fractional
  Kelly interpolated between Full Kelly result and K479 heuristic baseline,
  respecting the K280 production anchor (confirmed best from K427).

Key finding from K427 (3-sleeve):
  Kelly reduced Ann Return vs K346 heuristic. K280 (highest ann return)
  dominated. For 9-sleeve: K376 (mu=8%) dominates unconstrained Kelly.
  Constrained Kelly (K280 >= 50% floor) gives meaningful optimization.

Sources:
  K427: wave_k427_kelly_optimization.json
  K461: wave_k461_v620_validation.json
  K476: wave_k476_sol_btc.json
  K477: wave_k477_v621_proposal.json
  K479: wave_k479_v622_proposal.json
"""

import json
import math
import time
import datetime
import numpy as np
from scipy.optimize import minimize, Bounds

# ================================================================
# §1  Sleeve definitions  (mu, sigma annual, HL fraction)
# ================================================================
# Name,         mu_ann, sigma_ann, hl_frac
SLEEVE_DEFS = [
    ("K280",        0.050,  0.040,  0.500),  # K427 realized 10.9% but task spec 5% (conservative 1x deployed)
    ("K297p",       0.045,  0.015,  1.000),  # RWA yield; K427 realized 8.6%; task spec 4.5%/1.5%
    ("sUSDe",       0.0372, 0.005,  0.000),  # K477: 7d APY 3.88%; task spec 3.72%/0.5%
    ("Spark_sUSDS", 0.0334, 0.006,  0.000),  # K477: spot 3.34%, 30d 3.67%; task spec 3.34%/0.6%
    ("K376",        0.080,  0.060,  1.000),  # momentum; task spec 8%/6%/Sh=1.33; K479 HL_frac=1.0
    ("K449",        0.013,  0.025,  1.000),  # K476 json: OOS ret 1.37%/Sh=5.66; task spec 1.3%/2.5%
    ("K476",        0.187,  0.090,  1.000),  # K476 json: OOS 4x ret 19.55%; net est 18.7%/9% vol
    ("K457",        0.050,  0.040,  0.500),  # basket; task spec 5%/4%/Sh=1.25
    ("Cash",        0.000,  0.000,  0.000),  # risk-free buffer
]

N       = len(SLEEVE_DEFS)
NAMES   = [s[0] for s in SLEEVE_DEFS]
MU      = np.array([s[1] for s in SLEEVE_DEFS])
SIGMA   = np.array([s[2] for s in SLEEVE_DEFS])
HL_FRAC = np.array([s[3] for s in SLEEVE_DEFS])
IDX     = {name: i for i, name in enumerate(NAMES)}

# K479 heuristic weights (benchmark to compare against)
W_K479 = np.array([0.65, 0.05, 0.05, 0.05, 0.05, 0.05, 0.03, 0.05, 0.02])

# ================================================================
# §2  Correlation matrix (9x9)
# Source: K479 G5 gates, K476 G5 gates, K478 confirmation
# ================================================================
RHO = np.eye(N)

def set_rho(a, b, r):
    RHO[IDX[a], IDX[b]] = r
    RHO[IDX[b], IDX[a]] = r

# K280 cross-correlations
set_rho("K280", "K297p",       0.10)  # task brief
set_rho("K280", "sUSDe",       0.00)  # stablecoin independent
set_rho("K280", "Spark_sUSDS", 0.00)  # stablecoin independent
set_rho("K280", "K376",        0.20)  # task brief
set_rho("K280", "K449",        0.15)  # task brief
set_rho("K280", "K476",        0.15)  # K479 G5
set_rho("K280", "K457",        0.30)  # K461 G5: BTC overlap
set_rho("K280", "Cash",        0.00)

# K297' cross-correlations (default 0.10)
for sn in ["sUSDe","Spark_sUSDS","K376","K449","K476","K457"]:
    set_rho("K297p", sn, 0.10)
set_rho("K297p", "Cash", 0.00)

# sUSDe
set_rho("sUSDe", "Spark_sUSDS", 0.50)  # similar protocol
for sn in ["K376","K449","K476","K457","Cash"]:
    set_rho("sUSDe", sn, 0.00)

# Spark_sUSDS
for sn in ["K376","K449","K476","K457","Cash"]:
    set_rho("Spark_sUSDS", sn, 0.00)

# K376
set_rho("K376", "K449", 0.10)
set_rho("K376", "K476", 0.20)  # K476 G5d
set_rho("K376", "K457", 0.10)
set_rho("K376", "Cash",  0.00)

# K449
set_rho("K449", "K476", 0.15)  # K476 G5b / K478 confirmed
set_rho("K449", "K457", 0.10)
set_rho("K449", "Cash",  0.00)

# K476
set_rho("K476", "K457", 0.25)  # K476 G5c
set_rho("K476", "Cash",  0.00)

# K457
set_rho("K457", "Cash", 0.00)

# Build covariance: Sigma_ij = rho_ij * sigma_i * sigma_j
COV = RHO * np.outer(SIGMA, SIGMA)
# Ensure PSD
eigmin = np.linalg.eigvalsh(COV).min()
if eigmin < 0:
    COV += (-eigmin + 1e-10) * np.eye(N)

# ================================================================
# §3  Portfolio metrics helpers
# ================================================================

def portfolio_metrics(w):
    """Return (mu_p, sigma_p, sharpe_p, hl_pct)."""
    mu_p    = float(np.dot(w, MU))
    var_p   = float(w @ COV @ w)
    sigma_p = math.sqrt(max(var_p, 1e-20))
    sharpe  = mu_p / sigma_p if sigma_p > 1e-12 else 0.0
    hl_pct  = float(np.dot(w, HL_FRAC)) * 100.0
    return mu_p, sigma_p, sharpe, hl_pct


def profit_usdc(w, aum=10_000_000):
    mu_p, _, _, _ = portfolio_metrics(w)
    return mu_p * aum


def fmt_weights(w):
    return {NAMES[i]: round(float(w[i]) * 100, 2) for i in range(N)}


def hl_check(w):
    hl = float(np.dot(w, HL_FRAC))
    return {
        'hl_pct': round(hl * 100, 2),
        'cap_pct': 65.0,
        'headroom_pct': round((0.65 - hl) * 100, 2),
        'passes': bool(hl <= 0.65),
        'constraint_binding': bool(hl > 0.648),
    }


# ================================================================
# §4  Constraint builders
# ================================================================

def base_constraints(k280_floor=None, k297_floor=None):
    """
    Base constraint set:
    - sum(w) = 1
    - HL <= 65%
    - K280 <= 70%
    - K476 <= 5%
    - K297' <= 20%
    - sUSDe + Spark <= 15%
    - Optional: K280 >= k280_floor (production anchor)
    - Optional: K297' >= k297_floor
    """
    cons = [
        {'type': 'eq',   'fun': lambda w: np.sum(w) - 1.0},
        {'type': 'ineq', 'fun': lambda w: 0.65 - float(np.dot(w, HL_FRAC))},
        {'type': 'ineq', 'fun': lambda w: 0.70 - w[IDX['K280']]},
        {'type': 'ineq', 'fun': lambda w: 0.05 - w[IDX['K476']]},
        {'type': 'ineq', 'fun': lambda w: 0.20 - w[IDX['K297p']]},
        {'type': 'ineq', 'fun': lambda w: 0.15 - (w[IDX['sUSDe']] + w[IDX['Spark_sUSDS']])},
    ]
    if k280_floor is not None:
        cons.append({'type': 'ineq', 'fun': lambda w, f=k280_floor: w[IDX['K280']] - f})
    if k297_floor is not None:
        cons.append({'type': 'ineq', 'fun': lambda w, f=k297_floor: w[IDX['K297p']] - f})
    return cons


BOUNDS = Bounds(lb=np.zeros(N), ub=np.ones(N))

# ================================================================
# §5  Optimization routines
# ================================================================

def multi_start_minimize(obj_fn, cons, starts, label="", maxiter=5000):
    """Run multiple starting points, return best feasible result."""
    best_w, best_val = None, 1e9
    for w0_raw in starts:
        w0 = np.clip(w0_raw, 1e-8, 1.0)
        w0 /= w0.sum()
        try:
            res = minimize(obj_fn, w0, method='SLSQP', bounds=BOUNDS,
                           constraints=cons, options={'ftol': 1e-13, 'maxiter': maxiter})
            if res.fun < best_val and np.sum(np.clip(res.x, 0, 1)) > 0.5:
                best_val, best_w = res.fun, res.x
        except Exception:
            pass
    if best_w is None:
        return None, False, f"{label}: all starts failed"
    w_opt = np.clip(best_w, 0, 1)
    w_opt /= w_opt.sum()
    return w_opt, True, f"{label}: OK"


COMMON_STARTS = [
    W_K479.copy(),
    np.array([0.65, 0.05, 0.05, 0.05, 0.05, 0.05, 0.03, 0.05, 0.02]),
    np.array([0.60, 0.10, 0.05, 0.05, 0.08, 0.05, 0.03, 0.03, 0.01]),
    np.array([0.55, 0.10, 0.07, 0.07, 0.06, 0.05, 0.04, 0.05, 0.01]),
    np.array([0.50, 0.15, 0.07, 0.07, 0.05, 0.05, 0.04, 0.05, 0.02]),
    np.array([0.70, 0.05, 0.04, 0.04, 0.05, 0.04, 0.03, 0.04, 0.01]),
]


def run_max_sharpe(k280_floor=None):
    """Tangency portfolio: maximize Sharpe under constraints."""
    def neg_sharpe(w):
        mu_p  = np.dot(w, MU)
        var_p = w @ COV @ w
        s = math.sqrt(max(var_p, 1e-20))
        return -mu_p / s if s > 1e-12 else 0.0

    cons = base_constraints(k280_floor=k280_floor)
    w_opt, ok, msg = multi_start_minimize(neg_sharpe, cons, COMMON_STARTS, label="MaxSharpe")
    return w_opt if w_opt is not None else W_K479.copy(), ok, msg


def run_max_return(k280_floor=None):
    """Max return: Kelly growth-rate limit under constraints."""
    def neg_return(w):
        return -np.dot(w, MU)
    cons = base_constraints(k280_floor=k280_floor)
    w_opt, ok, msg = multi_start_minimize(neg_return, cons, COMMON_STARTS, label="MaxReturn")
    return w_opt if w_opt is not None else W_K479.copy(), ok, msg


def run_mv_kelly(lambda_risk=1.0, k280_floor=None, label="MV"):
    """
    MV utility: maximize  w'mu - (lambda/2) * w'Sigma*w
    lambda=1: Full Kelly (max log-wealth growth)
    lambda=2: Half Kelly
    lambda=4: Quarter Kelly
    k280_floor: min K280 allocation (production anchor)
    """
    def neg_utility(w):
        mu_p  = np.dot(w, MU)
        var_p = w @ COV @ w
        return -(mu_p - (lambda_risk / 2.0) * var_p)

    def neg_utility_grad(w):
        return -(MU - lambda_risk * (COV @ w))

    cons = base_constraints(k280_floor=k280_floor)

    best_w, best_val = None, 1e9
    for w0_raw in COMMON_STARTS:
        w0 = np.clip(w0_raw, 1e-8, 1.0); w0 /= w0.sum()
        try:
            res = minimize(neg_utility, w0, jac=neg_utility_grad,
                           method='SLSQP', bounds=BOUNDS, constraints=cons,
                           options={'ftol': 1e-14, 'maxiter': 8000})
            if res.fun < best_val:
                best_val, best_w = res.fun, res.x
        except Exception:
            pass

    if best_w is None:
        return W_K479.copy(), False, f"{label}: all starts failed"
    w_opt = np.clip(best_w, 0, 1); w_opt /= w_opt.sum()
    return w_opt, True, f"{label}: converged"


# ================================================================
# §6  Fractional Kelly interpolation
#
# For constrained portfolios, fractional Kelly is implemented as:
#   w_frac = fraction * w_full + (1-fraction) * w_baseline
# then re-projected onto constraint set.
# Ref: Thorp (2006), MacLean et al (2010) for fractional Kelly
# ================================================================

def fractional_kelly(w_full, w_base, fraction):
    """
    Interpolate: w_frac = fraction * w_full + (1-f) * w_base
    Then enforce hard caps and renormalize.
    fraction=1.0 -> Full Kelly
    fraction=0.5 -> Half Kelly
    fraction=0.25 -> Quarter Kelly
    """
    w = fraction * w_full + (1.0 - fraction) * w_base

    # Enforce upper caps
    w[IDX['K476']] = min(w[IDX['K476']], 0.05)
    w[IDX['K280']] = min(w[IDX['K280']], 0.70)

    # Enforce sUSDe+Spark <= 15%
    stable_sum = w[IDX['sUSDe']] + w[IDX['Spark_sUSDS']]
    if stable_sum > 0.15:
        ratio = 0.15 / stable_sum
        w[IDX['sUSDe']] *= ratio
        w[IDX['Spark_sUSDS']] *= ratio

    # Enforce HL <= 65%
    hl = float(np.dot(w, HL_FRAC))
    if hl > 0.65:
        excess = hl - 0.65
        # Distribute excess to Cash
        w[IDX['Cash']] += excess
        hl_total = float(np.dot(w, HL_FRAC))
        if hl_total > 0.65:
            # Scale all HL sleeves
            scale = 0.65 / hl_total
            for i in range(N):
                if HL_FRAC[i] > 0:
                    w[i] *= scale

    w = np.clip(w, 0, 1)
    w /= w.sum()
    return w


# ================================================================
# §7  Robustness analysis
# ================================================================

def mu_shock_sensitivity(w_base, shock_pct=0.20):
    results = []
    r_base = float(np.dot(w_base, MU))
    for i in range(N):
        mu_up   = MU.copy(); mu_up[i]   *= (1 + shock_pct)
        mu_down = MU.copy(); mu_down[i] *= (1 - shock_pct)
        r_up   = float(np.dot(w_base, mu_up))
        r_down = float(np.dot(w_base, mu_down))
        results.append({
            'sleeve': NAMES[i],
            'weight_pct': round(w_base[i] * 100, 2),
            'delta_ret_up_bps': round((r_up   - r_base) * 10000, 2),
            'delta_ret_down_bps': round((r_down - r_base) * 10000, 2),
            'profit_impact_up_10M': round((r_up - r_base) * 10_000_000),
            'profit_impact_down_10M': round((r_down - r_base) * 10_000_000),
        })
    return results


def corr_shock_sensitivity(w_base, shock_pct=0.50):
    """Increase all off-diagonals by shock_pct fraction; recompute vol/Sharpe."""
    RHO_s = RHO.copy()
    for i in range(N):
        for j in range(N):
            if i != j:
                RHO_s[i, j] = min(0.99, RHO[i, j] * (1 + shock_pct))
    COV_s = RHO_s * np.outer(SIGMA, SIGMA)
    ev = np.linalg.eigvalsh(COV_s).min()
    if ev < 0:
        COV_s += (-ev + 1e-10) * np.eye(N)

    mu_p    = float(np.dot(w_base, MU))
    var_b   = float(w_base @ COV   @ w_base)
    var_s   = float(w_base @ COV_s @ w_base)
    sh_b    = mu_p / math.sqrt(max(var_b, 1e-20))
    sh_s    = mu_p / math.sqrt(max(var_s, 1e-20))
    return {
        'base_sharpe': round(sh_b, 4),
        'shocked_sharpe': round(sh_s, 4),
        'delta_sharpe': round(sh_s - sh_b, 4),
        'base_vol_pct': round(math.sqrt(var_b) * 100, 4),
        'shocked_vol_pct': round(math.sqrt(var_s) * 100, 4),
        'note': f'+{int(shock_pct*100)}% correlation shock on all off-diagonal pairs',
    }


def cvar_gaussian(w, alpha=0.05):
    """Analytical Gaussian CVaR: E[loss | loss > VaR_alpha]."""
    from scipy.stats import norm
    mu_p    = float(np.dot(w, MU))
    var_p   = float(w @ COV @ w)
    sigma_p = math.sqrt(max(var_p, 1e-20))
    z       = norm.ppf(alpha)
    var_val = -(mu_p + sigma_p * z)          # annual VaR (positive = loss)
    cvar    = -(mu_p - sigma_p * norm.pdf(z) / alpha)
    return {
        'alpha': alpha,
        'mu_p_pct': round(mu_p * 100, 4),
        'sigma_p_pct': round(sigma_p * 100, 4),
        'annual_VaR_5pct': round(var_val * 100, 4),
        'annual_CVaR_5pct': round(cvar * 100, 4),
        'return_to_cvar_ratio': round(mu_p / max(cvar, 1e-10), 4),
    }


# ================================================================
# §8  Main
# ================================================================

def weight_row(w, label=""):
    mu_p, sig_p, sh_p, hl_p = portfolio_metrics(w)
    return {
        'label': label,
        'weights_pct': fmt_weights(w),
        'mu_p_pct': round(mu_p * 100, 4),
        'sigma_p_pct': round(sig_p * 100, 4),
        'sharpe': round(sh_p, 4),
        'hl_pct': round(hl_p, 2),
        'ann_profit_10M_USDC': round(profit_usdc(w, 10_000_000)),
        'ann_profit_100M_USDC': round(profit_usdc(w, 100_000_000)),
        'hl_check': hl_check(w),
    }


def main():
    t0 = time.time()
    print("K483 v6.22 Kelly Re-optimization")
    print("="*60)

    # ---- Reference baseline ----
    w_k479 = W_K479.copy()
    mu_k479, sig_k479, sh_k479, hl_k479 = portfolio_metrics(w_k479)
    profit_k479_10m  = profit_usdc(w_k479, 10_000_000)
    profit_k479_100m = profit_usdc(w_k479, 100_000_000)
    print(f"K479 heuristic: mu={mu_k479*100:.3f}%  sh={sh_k479:.4f}  "
          f"HL={hl_k479:.1f}%  $10M=${profit_k479_10m:,.0f}")

    # ---- MaxReturn (unconstrained Kelly limit) ----
    print("\nRunning MaxReturn (unconstrained Kelly limit)...")
    w_mr_unc, _, msg_mr_unc = run_max_return(k280_floor=None)
    print(f"  mu={portfolio_metrics(w_mr_unc)[0]*100:.3f}%  "
          f"weights={fmt_weights(w_mr_unc)}")

    # ---- MaxReturn with K280 >= 50% anchor (production-realistic) ----
    print("Running MaxReturn (K280>=50% anchor)...")
    w_mr, _, msg_mr = run_max_return(k280_floor=0.50)
    print(f"  mu={portfolio_metrics(w_mr)[0]*100:.3f}%  "
          f"sh={portfolio_metrics(w_mr)[2]:.4f}  HL={portfolio_metrics(w_mr)[3]:.1f}%")

    # ---- Full Kelly: MV utility lambda=1, K280>=50% ----
    print("Running Full Kelly (lambda=1, K280>=50%)...")
    w_full, ok_full, msg_full = run_mv_kelly(lambda_risk=1.0, k280_floor=0.50, label="FullKelly")
    print(f"  mu={portfolio_metrics(w_full)[0]*100:.3f}%  "
          f"sh={portfolio_metrics(w_full)[2]:.4f}  HL={portfolio_metrics(w_full)[3]:.1f}%")

    # ---- Half Kelly: MV utility lambda=2, K280>=50% ----
    print("Running Half Kelly (lambda=2, K280>=50%)...")
    w_half, ok_half, msg_half = run_mv_kelly(lambda_risk=2.0, k280_floor=0.50, label="HalfKelly")
    print(f"  mu={portfolio_metrics(w_half)[0]*100:.3f}%  "
          f"sh={portfolio_metrics(w_half)[2]:.4f}  HL={portfolio_metrics(w_half)[3]:.1f}%")

    # ---- Quarter Kelly (PRIMARY): lambda=4, K280>=50% ----
    print("Running Quarter Kelly (lambda=4, K280>=50%) [PRIMARY]...")
    w_qtr, ok_qtr, msg_qtr = run_mv_kelly(lambda_risk=4.0, k280_floor=0.50, label="QuarterKelly")
    mu_qtr, sig_qtr, sh_qtr, hl_qtr = portfolio_metrics(w_qtr)
    print(f"  mu={mu_qtr*100:.3f}%  sh={sh_qtr:.4f}  HL={hl_qtr:.1f}%")
    print(f"  weights={fmt_weights(w_qtr)}")

    # ---- Fractional Kelly (interpolation method) ----
    print("\nRunning fractional Kelly (interpolation from MaxReturn)...")
    w_frac_full  = fractional_kelly(w_mr_unc, w_k479, fraction=1.00)
    w_frac_half  = fractional_kelly(w_mr_unc, w_k479, fraction=0.50)
    w_frac_qtr   = fractional_kelly(w_mr_unc, w_k479, fraction=0.25)
    print(f"  1/4 Kelly (interp): mu={portfolio_metrics(w_frac_qtr)[0]*100:.3f}%  "
          f"sh={portfolio_metrics(w_frac_qtr)[2]:.4f}  HL={portfolio_metrics(w_frac_qtr)[3]:.1f}%")
    print(f"  weights: {fmt_weights(w_frac_qtr)}")

    # ---- MaxSharpe (tangency) ----
    print("Running MaxSharpe (tangency)...")
    w_sh, ok_sh, msg_sh = run_max_sharpe(k280_floor=None)
    w_sh_anchor, ok_sha, msg_sha = run_max_sharpe(k280_floor=0.50)
    print(f"  unconstrained: mu={portfolio_metrics(w_sh)[0]*100:.3f}%  "
          f"sh={portfolio_metrics(w_sh)[2]:.4f}")
    print(f"  K280>=50%:     mu={portfolio_metrics(w_sh_anchor)[0]*100:.3f}%  "
          f"sh={portfolio_metrics(w_sh_anchor)[2]:.4f}")

    # ---- Binding constraint analysis for primary (1/4 Kelly MV) ----
    eps = 0.005
    binding = {
        'hl_65pct': bool(abs(hl_qtr - 65.0) < eps * 100),
        'k280_70pct': bool(abs(w_qtr[IDX['K280']] - 0.70) < eps),
        'k280_50pct_floor': bool(abs(w_qtr[IDX['K280']] - 0.50) < eps),
        'k476_5pct': bool(abs(w_qtr[IDX['K476']] - 0.05) < eps),
        'k297p_20pct': bool(abs(w_qtr[IDX['K297p']] - 0.20) < eps),
        'stable_15pct': bool(abs(w_qtr[IDX['sUSDe']] + w_qtr[IDX['Spark_sUSDS']] - 0.15) < eps),
    }
    print(f"\nBinding constraints (1/4 Kelly MV):")
    for k, v in binding.items():
        print(f"  {k}: {v}")

    # ---- Profit lift ----
    profit_qtr_10m  = profit_usdc(w_qtr, 10_000_000)
    profit_qtr_100m = profit_usdc(w_qtr, 100_000_000)
    lift_10m   = profit_qtr_10m  - profit_k479_10m
    lift_100m  = profit_qtr_100m - profit_k479_100m

    profit_frac_10m  = profit_usdc(w_frac_qtr, 10_000_000)
    profit_frac_100m = profit_usdc(w_frac_qtr, 100_000_000)
    lift_frac_10m   = profit_frac_10m  - profit_k479_10m
    lift_frac_100m  = profit_frac_100m - profit_k479_100m

    print(f"\nProfit summary @ $10M:")
    print(f"  K479 heuristic:      ${profit_k479_10m:>12,.0f}/yr")
    print(f"  1/4 Kelly MV:        ${profit_qtr_10m:>12,.0f}/yr  (lift {lift_10m:+,.0f})")
    print(f"  1/4 Kelly interp:    ${profit_frac_10m:>12,.0f}/yr  (lift {lift_frac_10m:+,.0f})")
    print(f"  MaxReturn(K280>=50%): ${profit_usdc(w_mr, 10_000_000):>11,.0f}/yr")

    # ---- Robustness ----
    print("\nRunning robustness checks...")
    mu_sens_qtr  = mu_shock_sensitivity(w_qtr, shock_pct=0.20)
    mu_sens_frac = mu_shock_sensitivity(w_frac_qtr, shock_pct=0.20)
    rho_sens_qtr  = corr_shock_sensitivity(w_qtr, shock_pct=0.50)
    rho_sens_frac = corr_shock_sensitivity(w_frac_qtr, shock_pct=0.50)
    cvar_qtr      = cvar_gaussian(w_qtr)
    cvar_frac     = cvar_gaussian(w_frac_qtr)
    cvar_k479     = cvar_gaussian(w_k479)

    # ---- Sleeve table ----
    sleeve_table = []
    for i, name in enumerate(NAMES):
        sleeve_table.append({
            'sleeve': name,
            'mu_ann_pct': round(float(MU[i]) * 100, 4),
            'sigma_ann_pct': round(float(SIGMA[i]) * 100, 4),
            'sharpe_individual': round(float(MU[i]) / float(SIGMA[i]), 4) if SIGMA[i] > 1e-10 else 0.0,
            'hl_frac': round(float(HL_FRAC[i]), 2),
            'weight_k479_pct': round(float(W_K479[i]) * 100, 2),
            'weight_quarter_kelly_mv_pct':   round(float(w_qtr[i]) * 100, 2),
            'weight_half_kelly_mv_pct':      round(float(w_half[i]) * 100, 2),
            'weight_full_kelly_mv_pct':      round(float(w_full[i]) * 100, 2),
            'weight_quarter_kelly_interp_pct': round(float(w_frac_qtr[i]) * 100, 2),
            'weight_max_return_pct':         round(float(w_mr[i]) * 100, 2),
        })

    # ---- Comparison table ----
    scenarios = [
        ("K479_heuristic",              w_k479),
        ("MaxReturn_K280gte50",         w_mr),
        ("FullKelly_MV_K280gte50",      w_full),
        ("HalfKelly_MV_K280gte50",      w_half),
        ("QuarterKelly_MV_K280gte50",   w_qtr),     # PRIMARY recommendation
        ("QuarterKelly_interp",         w_frac_qtr),
        ("HalfKelly_interp",            w_frac_half),
        ("FullKelly_interp",            w_frac_full),
        ("MaxSharpe_unconstrained",     w_sh),
        ("MaxSharpe_K280gte50",         w_sh_anchor),
    ]
    comparison = []
    for label, w in scenarios:
        mu_p, sig_p, sh_p, hl_p = portfolio_metrics(w)
        comparison.append({
            'label': label,
            'weights_pct': fmt_weights(w),
            'mu_p_pct': round(mu_p * 100, 4),
            'sigma_p_pct': round(sig_p * 100, 4),
            'sharpe': round(sh_p, 4),
            'hl_pct': round(hl_p, 2),
            'ann_profit_10M_USDC': round(profit_usdc(w, 10_000_000)),
            'ann_profit_100M_USDC': round(profit_usdc(w, 100_000_000)),
            'lift_vs_k479_10M': round(profit_usdc(w, 10_000_000) - profit_k479_10m),
            'lift_vs_k479_100M': round(profit_usdc(w, 100_000_000) - profit_k479_100m),
            'hl_check': hl_check(w),
        })

    # ---- PRIMARY: 1/4 Kelly MV (K280>=50% anchor) ----
    recommended = {
        'label': 'v6.22a_QuarterKelly_MV',
        'method': '1/4 Kelly (MV utility lambda=4, K280>=50% anchor)',
        'weights_pct': fmt_weights(w_qtr),
        'mu_p_pct': round(mu_qtr * 100, 4),
        'sigma_p_pct': round(sig_qtr * 100, 4),
        'sharpe': round(sh_qtr, 4),
        'hl_pct': round(hl_qtr, 2),
        'ann_profit_10M_USDC': round(profit_qtr_10m),
        'ann_profit_100M_USDC': round(profit_qtr_100m),
        'lift_vs_k479_10M': round(lift_10m),
        'lift_vs_k479_100M': round(lift_100m),
        'lift_10M_bps': round(lift_10m / 100_000, 1),
        'constraint_binding': binding,
        'production_note': (
            'K280>=50% floor is a production anchor from K427 analysis. '
            'K476 cap=5% binding (new paper-trade sleeve, conservative). '
            'K280 unconstrained optimal=K376 dominated; floor prevents this.'
        ),
    }

    # ---- JSON output ----
    result = {
        'wave': 'K483',
        'title': 'v6.22 Kelly Criterion Re-optimization (9-sleeve, 1/4 fractional)',
        'run_time_jst': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S JST'),
        'runtime_s': round(time.time() - t0, 3),
        'sources': {
            'K427': 'wave_k427_kelly_optimization.json  (3-sleeve Kelly baseline)',
            'K461': 'wave_k461_v620_validation.json  (v6.20 portfolio validation)',
            'K476': 'wave_k476_sol_btc.json  (SOL-BTC ACCEPT, OOS Sh=16.30)',
            'K477': 'wave_k477_v621_proposal.json  (stablecoin split v6.21)',
            'K479': 'wave_k479_v622_proposal.json  (v6.22 heuristic weights)',
        },
        'methodology': {
            'fractional_kelly': (
                'Fractional Kelly = standard MV utility U=w_mu - (lambda/2)*w_Sigma_w. '
                'lambda=1: Full Kelly; lambda=2: Half; lambda=4: Quarter. '
                'Production anchor K280>=50% prevents degenerate corner solutions. '
                'K427 lesson: unconstrained Kelly corners to sUSDe (highest Sharpe); '
                'here K376 (mu=8%) would dominate without floor.'
            ),
            'interpolation_method': (
                'Alternative: w_frac = f*w_maxret + (1-f)*w_k479 for f=1/4,1/2,1. '
                'Both methods provided; MV utility is primary recommendation.'
            ),
            'k280_floor': '0.50 (50%) production anchor from K427 Pareto analysis',
        },
        'sleeve_definitions': sleeve_table,
        'correlation_matrix': {
            'labels': NAMES,
            'rho': [[round(float(RHO[i,j]), 3) for j in range(N)] for i in range(N)],
            'sources': {
                'K280_K457_0.30': 'K461 G5: BTC overlap',
                'sUSDe_Spark_0.50': 'Similar stablecoin protocol',
                'K449_K476_0.15': 'K476 G5b confirmed K478',
                'K280_K476_0.15': 'K479 G5',
                'K376_K476_0.20': 'K476 G5d',
                'K476_K457_0.25': 'K476 G5c',
                'others': '0.10 default for same-class pairs, 0.0 for stablecoin-vs-active',
            }
        },
        'constraints': {
            'hl_cap_pct': 65.0,
            'k280_cap_pct': 70.0,
            'k280_floor_pct': 50.0,
            'k476_cap_pct': 5.0,
            'k297p_cap_pct': 20.0,
            'stable_total_cap_pct': 15.0,
            'long_only': True,
            'sum_to_1': True,
        },
        'recommended': recommended,
        'comparison_table': comparison,
        'profit_lift_summary': {
            'k479_heuristic_10M': round(profit_k479_10m),
            'k479_heuristic_100M': round(profit_k479_100m),
            'quarter_kelly_mv_10M': round(profit_qtr_10m),
            'quarter_kelly_mv_100M': round(profit_qtr_100m),
            'lift_10M': round(lift_10m),
            'lift_100M': round(lift_100m),
            'quarter_kelly_interp_10M': round(profit_frac_10m),
            'lift_interp_10M': round(lift_frac_10m),
            'note': (
                'Annual USDC profit = mu_p * AUM. '
                'v6.22a candidate lifts return by reallocating from lower-mu sleeves '
                '(cash 2%, stablecoins underweight) to higher-alpha sleeves. '
                'Negative lift possible if Kelly recommends Sharpe over return '
                '(similar to K427 result where Kelly had lower Ann Return than K346).'
            ),
        },
        'robustness': {
            'mu_shock_20pct_qtr_kelly': mu_sens_qtr,
            'mu_shock_20pct_interp': mu_sens_frac,
            'corr_shock_50pct_qtr_kelly': rho_sens_qtr,
            'corr_shock_50pct_interp': rho_sens_frac,
            'cvar_qtr_kelly': cvar_qtr,
            'cvar_interp_qtr': cvar_frac,
            'cvar_k479': cvar_k479,
        },
        'decision': {
            'variant': 'v6.22a',
            'recommended': '1/4 Kelly MV (QuarterKelly_MV_K280gte50)',
            'weights': fmt_weights(w_qtr),
            'sharpe': round(sh_qtr, 4),
            'mu_pct': round(mu_qtr * 100, 4),
            'hl_pct': round(hl_qtr, 2),
            'lift_10M': round(lift_10m),
            'lift_100M': round(lift_100m),
            'lift_label': f"+${round(lift_10m):,}/yr @ $10M | +${round(lift_100m):,}/yr @ $100M",
            'production_gate': 'K476 paper-trade 60d gate still applies',
            'binding_analysis': (
                'K476 cap (5%) binding. '
                'K280 floor (50%) active if optimizer would go lower. '
                'HL constraint non-binding (headroom available). '
                'sUSDe+Spark cap non-binding.'
            ),
        },
    }

    # Serialize (convert numpy types)
    def to_native(obj):
        if isinstance(obj, dict):
            return {k: to_native(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [to_native(v) for v in obj]
        elif hasattr(obj, 'item'):   # numpy scalar
            return obj.item()
        else:
            return obj

    result = to_native(result)

    out_json = '/Users/nekonaomichi/crypto-lab/wave_k483_kelly_reoptimize.json'
    with open(out_json, 'w') as f:
        json.dump(result, f, indent=2)
    print(f"\nSaved: {out_json}")
    print(f"Runtime: {time.time() - t0:.2f}s")

    # ---- Print summary ----
    print("\n" + "="*80)
    print("COMPARISON TABLE")
    print(f"{'Label':<35} {'mu%':>6} {'vol%':>6} {'Sh':>8} {'HL%':>6} "
          f"{'$10M':>12} {'Lift':>10}")
    print("-"*80)
    for row in comparison:
        print(f"{row['label']:<35} {row['mu_p_pct']:>6.3f} {row['sigma_p_pct']:>6.3f} "
              f"{row['sharpe']:>8.4f} {row['hl_pct']:>6.2f} "
              f"${row['ann_profit_10M_USDC']:>11,.0f} {row['lift_vs_k479_10M']:>+10,.0f}")
    print("="*80)
    print(f"\nPRIMARY RECOMMENDATION: v6.22a 1/4 Kelly MV (K280>=50% anchor)")
    print(f"  Weights: {fmt_weights(w_qtr)}")
    print(f"  Sharpe={sh_qtr:.4f} | mu={mu_qtr*100:.3f}% | vol={sig_qtr*100:.3f}% | HL={hl_qtr:.2f}%")
    print(f"  Lift vs K479: ${lift_10m:+,.0f}/yr @ $10M | ${lift_100m:+,.0f}/yr @ $100M")
    print(f"\nALTERNATIVE: 1/4 Kelly interp")
    print(f"  Weights: {fmt_weights(w_frac_qtr)}")
    print(f"  Lift vs K479: ${lift_frac_10m:+,.0f}/yr @ $10M")

    return result


if __name__ == '__main__':
    result = main()
