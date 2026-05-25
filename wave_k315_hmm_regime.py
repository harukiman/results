"""
Wave K315: 3-State HMM Regime Filter Prototype for K280
========================================================
Based on R11 finding #3 (R11-13): BTC 4h Gaussian HMM with 3 states (bull/bear/neutral)
outperforms 2-state model for 2024-2026 data. Used as K280 entry filter.

NOTE: hmmlearn not available in this environment.
      Implemented manual Gaussian HMM via EM (Baum-Welch) algorithm.
      This is mathematically equivalent to hmmlearn.GaussianHMM(covariance_type='diag').

Author: Wave K315 (Claude agent)
Date: 2026-05-25
"""

import json
import warnings
import numpy as np
import pandas as pd
from scipy.stats import norm
from pathlib import Path
from datetime import date

warnings.filterwarnings("ignore")

# ─────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────
REPO = Path("/Users/nekonaomichi/crypto-lab")
BTC_4H_PATH = REPO / "cache" / "BTCUSDT_4h_730d.parquet"
K280_CURVES_PATH = REPO / "wave_k280_curves.json"
N_STATES = 3
N_ITER = 200
RANDOM_SEED = 42
N_FOLDS = 4

# ─────────────────────────────────────────────────────────
# PHASE 0: Check hmmlearn (fallback to manual EM)
# ─────────────────────────────────────────────────────────
try:
    from hmmlearn import hmm as _hmm
    HMMLEARN_AVAILABLE = True
    print("[INFO] hmmlearn available — using GaussianHMM")
except ImportError:
    HMMLEARN_AVAILABLE = False
    print("[WARN] hmmlearn NOT available — using manual Baum-Welch EM (mathematically equivalent)")


# ─────────────────────────────────────────────────────────
# MANUAL GAUSSIAN HMM (Baum-Welch EM)
# ─────────────────────────────────────────────────────────

class ManualGaussianHMM:
    """
    Gaussian HMM with diagonal covariance, fit via Baum-Welch EM.
    Equivalent to hmmlearn.GaussianHMM(n_components=K, covariance_type='diag').
    """

    def __init__(self, n_components=3, n_iter=200, random_state=42, tol=1e-4):
        self.K = n_components
        self.n_iter = n_iter
        self.rs = random_state
        self.tol = tol
        self.rng = np.random.RandomState(random_state)

    def _init_params(self, X):
        K, N, D = self.K, len(X), X.shape[1]
        # Initialize using k-means-like assignment
        from scipy.cluster.vq import kmeans2
        try:
            centers, labels = kmeans2(X, K, seed=self.rs, minit='points')
        except Exception:
            # fallback: percentile-based
            pcts = np.linspace(0, 100, K + 1)
            centers = np.array([
                np.percentile(X, (pcts[i] + pcts[i+1]) / 2, axis=0)
                for i in range(K)
            ])
            dists = np.linalg.norm(X[:, None] - centers[None], axis=2)
            labels = np.argmin(dists, axis=1)

        # Initial means and vars
        self.means_ = centers.copy()  # (K, D)
        self.covars_ = np.array([
            np.maximum(X[labels == k].var(axis=0), 1e-8)
            if (labels == k).sum() > 1
            else np.ones(D) * X.var(axis=0)
            for k in range(K)
        ])  # (K, D)

        # Uniform start prob and transition matrix
        self.startprob_ = np.ones(K) / K
        self.transmat_ = np.ones((K, K)) / K

    def _log_emission(self, X):
        """log p(x_t | state k) for all t and k. Returns (N, K)."""
        N, D = X.shape
        log_B = np.zeros((N, self.K))
        for k in range(self.K):
            log_B[:, k] = np.sum(
                norm.logpdf(X, loc=self.means_[k], scale=np.sqrt(self.covars_[k])),
                axis=1
            )
        return log_B

    def _forward(self, log_B):
        """Log-space forward algorithm. Returns log_alpha (N, K), log_c (N,)."""
        N = log_B.shape[0]
        log_alpha = np.zeros((N, self.K))
        log_c = np.zeros(N)

        log_alpha[0] = np.log(self.startprob_ + 1e-300) + log_B[0]
        log_c[0] = np.logaddexp.reduce(log_alpha[0])
        log_alpha[0] -= log_c[0]

        log_trans = np.log(self.transmat_ + 1e-300)

        for t in range(1, N):
            # log_alpha[t, k] = log sum_j exp(log_alpha[t-1, j] + log_trans[j,k]) + log_B[t,k]
            propagate = log_alpha[t-1][:, None] + log_trans  # (K, K)
            log_alpha[t] = np.logaddexp.reduce(propagate, axis=0) + log_B[t]
            log_c[t] = np.logaddexp.reduce(log_alpha[t])
            log_alpha[t] -= log_c[t]

        return log_alpha, log_c

    def _backward(self, log_B, log_c):
        """Log-space backward algorithm. Returns log_beta (N, K)."""
        N = log_B.shape[0]
        log_beta = np.zeros((N, self.K))
        log_trans = np.log(self.transmat_ + 1e-300)

        for t in range(N - 2, -1, -1):
            # log_beta[t, j] = log sum_k exp(log_trans[j,k] + log_B[t+1,k] + log_beta[t+1,k])
            propagate = log_trans + log_B[t+1][None, :] + log_beta[t+1][None, :]  # (K, K)
            log_beta[t] = np.logaddexp.reduce(propagate, axis=1)
            log_beta[t] -= log_c[t+1]

        return log_beta

    def _e_step(self, X):
        """E-step: compute gamma (N, K) and xi (N-1, K, K)."""
        log_B = self._log_emission(X)
        log_alpha, log_c = self._forward(log_B)
        log_beta = self._backward(log_B, log_c)

        # Posterior gamma[t, k] = P(z_t=k | X)
        log_gamma = log_alpha + log_beta
        log_gamma -= np.logaddexp.reduce(log_gamma, axis=1, keepdims=True)
        gamma = np.exp(log_gamma)  # (N, K)

        # Xi[t, j, k] = P(z_t=j, z_{t+1}=k | X)
        N = X.shape[0]
        log_trans = np.log(self.transmat_ + 1e-300)
        xi = np.zeros((N - 1, self.K, self.K))
        for t in range(N - 1):
            log_xi_t = (log_alpha[t][:, None]
                        + log_trans
                        + log_B[t+1][None, :]
                        + log_beta[t+1][None, :])
            log_xi_t -= np.logaddexp.reduce(log_xi_t.ravel())
            xi[t] = np.exp(log_xi_t)

        log_likelihood = log_c.sum()
        return gamma, xi, log_likelihood

    def _m_step(self, X, gamma, xi):
        """M-step: update parameters."""
        N, D = X.shape
        K = self.K

        # Start prob
        self.startprob_ = gamma[0] + 1e-10
        self.startprob_ /= self.startprob_.sum()

        # Transition matrix
        A = xi.sum(axis=0)  # (K, K)
        A += 1e-10
        self.transmat_ = A / A.sum(axis=1, keepdims=True)

        # Means and covariances
        denom = gamma.sum(axis=0)  # (K,)
        for k in range(K):
            w = gamma[:, k]  # (N,)
            self.means_[k] = (w[:, None] * X).sum(axis=0) / (denom[k] + 1e-10)
            diff = X - self.means_[k]
            self.covars_[k] = (w[:, None] * diff**2).sum(axis=0) / (denom[k] + 1e-10)
            self.covars_[k] = np.maximum(self.covars_[k], 1e-8)

    def fit(self, X):
        if X.ndim == 1:
            X = X[:, None]
        self._init_params(X)

        prev_ll = -np.inf
        for iteration in range(self.n_iter):
            gamma, xi, ll = self._e_step(X)
            self._m_step(X, gamma, xi)
            if abs(ll - prev_ll) < self.tol:
                print(f"  [HMM] Converged at iteration {iteration+1}, LL={ll:.4f}")
                break
            prev_ll = ll
        else:
            print(f"  [HMM] Reached max iterations {self.n_iter}, LL={ll:.4f}")

        self.log_likelihood_ = ll
        return self

    def predict(self, X):
        """Viterbi decoding. Returns state sequence (N,)."""
        if X.ndim == 1:
            X = X[:, None]
        N = X.shape[0]
        K = self.K
        log_B = self._log_emission(X)
        log_trans = np.log(self.transmat_ + 1e-300)

        # Viterbi
        delta = np.zeros((N, K))
        psi = np.zeros((N, K), dtype=int)

        delta[0] = np.log(self.startprob_ + 1e-300) + log_B[0]

        for t in range(1, N):
            for k in range(K):
                scores = delta[t-1] + log_trans[:, k]
                psi[t, k] = np.argmax(scores)
                delta[t, k] = scores[psi[t, k]] + log_B[t, k]

        # Backtrack
        states = np.zeros(N, dtype=int)
        states[-1] = np.argmax(delta[-1])
        for t in range(N - 2, -1, -1):
            states[t] = psi[t + 1, states[t + 1]]

        return states

    def predict_proba(self, X):
        """Posterior state probabilities (N, K)."""
        if X.ndim == 1:
            X = X[:, None]
        log_B = self._log_emission(X)
        log_alpha, log_c = self._forward(log_B)
        log_beta = self._backward(log_B, log_c)
        log_gamma = log_alpha + log_beta
        log_gamma -= np.logaddexp.reduce(log_gamma, axis=1, keepdims=True)
        return np.exp(log_gamma)


# ─────────────────────────────────────────────────────────
# PHASE 1: Load & Fit HMM on BTC 4h returns
# ─────────────────────────────────────────────────────────

def fit_hmm_on_btc(btc_path, n_states=3, n_iter=200, random_seed=42):
    print("\n" + "="*60)
    print("PHASE 1: Fit Gaussian HMM on BTC 4h log returns")
    print("="*60)

    df = pd.read_parquet(btc_path)
    df['open_time'] = pd.to_datetime(df['open_time'])
    df = df.set_index('open_time').sort_index()
    df = df[['close']].copy()
    df['log_ret'] = np.log(df['close'] / df['close'].shift(1))
    df = df.dropna()

    print(f"BTC 4h data: {df.index[0]} → {df.index[-1]}, {len(df)} bars")

    # Observations: log returns (1D)
    obs = df['log_ret'].values.reshape(-1, 1)

    if HMMLEARN_AVAILABLE:
        from hmmlearn import hmm as _hmm
        model = _hmm.GaussianHMM(
            n_components=n_states,
            covariance_type='diag',
            n_iter=n_iter,
            random_state=random_seed
        )
        model.fit(obs)
        raw_states = model.predict(obs)
        means = model.means_.flatten()
        covars = model.covars_.flatten()
        transmat = model.transmat_
        startprob = model.startprob_
    else:
        model = ManualGaussianHMM(
            n_components=n_states,
            n_iter=n_iter,
            random_state=random_seed
        )
        model.fit(obs)
        raw_states = model.predict(obs)
        means = model.means_.flatten()
        covars = model.covars_.flatten()
        transmat = model.transmat_
        startprob = model.startprob_

    # Sort states by mean: 0=bear (lowest mean), 1=neutral, 2=bull (highest mean)
    order = np.argsort(means)  # ascending
    state_map = {old: new for new, old in enumerate(order)}
    sorted_states = np.array([state_map[s] for s in raw_states])

    sorted_means = means[order]
    sorted_stds = np.sqrt(covars[order])
    sorted_transmat = transmat[np.ix_(order, order)]

    print(f"\nHMM states (sorted by mean return):")
    state_names = ['BEAR', 'NEUTRAL', 'BULL']
    for i, name in enumerate(state_names):
        pct = (sorted_states == i).mean() * 100
        print(f"  State {i} [{name}]: mean={sorted_means[i]:.6f}, std={sorted_stds[i]:.6f}, "
              f"freq={pct:.1f}%")

    print(f"\nTransition matrix (BEAR→NEUTRAL→BULL):")
    for i in range(3):
        row = " ".join(f"{sorted_transmat[i,j]:.4f}" for j in range(3))
        print(f"  {state_names[i]:8s}: [{row}]")

    # Compute persistence (expected state duration = 1 / (1 - self-transition))
    print(f"\nState persistence (expected bars in state):")
    for i in range(3):
        p_stay = sorted_transmat[i, i]
        expected_dur = 1.0 / (1.0 - p_stay + 1e-10)
        print(f"  {state_names[i]}: {expected_dur:.1f} bars = {expected_dur*4/24:.1f} days")

    # Attach states to df
    df['raw_state'] = raw_states
    df['state'] = sorted_states

    return df, sorted_means, sorted_stds, sorted_transmat, startprob, model, order


# ─────────────────────────────────────────────────────────
# PHASE 2: Load K280 equity curve
# ─────────────────────────────────────────────────────────

def load_k280_equity(k280_path):
    print("\n" + "="*60)
    print("PHASE 2: Load K280 equity curve")
    print("="*60)

    with open(k280_path) as f:
        data = json.load(f)

    print(f"Source: {k280_path}")
    print(f"Wave: {data.get('wave', 'K280')}")
    print(f"Keys: {list(data.keys())}")

    dates = pd.to_datetime(data['dates'])
    equity = np.array(data['K280'])

    # Daily returns from cumulative equity
    pnl_series = pd.Series(equity, index=dates, name='equity')
    daily_ret = pnl_series.pct_change().dropna()

    print(f"Date range: {dates[0].date()} → {dates[-1].date()}")
    print(f"N days: {len(dates)}, N returns: {len(daily_ret)}")
    print(f"Total return: {(equity[-1] / equity[0] - 1)*100:.2f}%")
    print(f"Annualized Sharpe (raw): {daily_ret.mean() / daily_ret.std() * np.sqrt(252):.2f}")

    # Components
    components = {}
    for key in ['K198', 'K208', 'K276b_win', 'K272a_ref']:
        if key in data:
            comp_eq = np.array(data[key])
            comp_ret = pd.Series(comp_eq, index=dates).pct_change().dropna()
            components[key] = comp_ret
            print(f"  Component {key}: Sh={comp_ret.mean()/comp_ret.std()*np.sqrt(252):.2f}")

    return daily_ret, pnl_series, data


# ─────────────────────────────────────────────────────────
# PHASE 3: Filter application
# ─────────────────────────────────────────────────────────

def compute_metrics(daily_ret_series):
    """Compute Sharpe, MDD, trade days for a daily return series."""
    ret = daily_ret_series.dropna()
    if len(ret) == 0:
        return {"sharpe": np.nan, "mdd": np.nan, "n_days": 0, "ann_return": np.nan}

    sh = ret.mean() / ret.std() * np.sqrt(252) if ret.std() > 0 else np.nan
    ann_ret = (1 + ret.mean()) ** 252 - 1

    # MDD on cumulative equity
    cum = (1 + ret).cumprod()
    peak = cum.cummax()
    dd = (cum - peak) / peak
    mdd = dd.min()

    n_days = len(ret)
    return {
        "sharpe": float(sh),
        "mdd": float(mdd),
        "n_days": int(n_days),
        "ann_return": float(ann_ret)
    }


def apply_hmm_filter(btc_df, daily_ret, equity_series):
    print("\n" + "="*60)
    print("PHASE 3: Apply HMM filter to K280 daily PnL")
    print("="*60)

    # Resample 4h HMM states → daily (most frequent state per day)
    # Use UTC calendar date
    btc_df = btc_df.copy()
    btc_df['date'] = btc_df.index.normalize()
    daily_states = (btc_df.groupby('date')['state']
                    .agg(lambda x: x.mode()[0])
                    .rename('hmm_state'))
    daily_states.index = pd.to_datetime(daily_states.index)

    # Align with K280 returns
    aligned = pd.DataFrame({
        'ret': daily_ret,
        'hmm_state': daily_states
    }).dropna()

    print(f"Aligned days: {len(aligned)}")
    print(f"State distribution in K280 period:")
    state_names = ['BEAR', 'NEUTRAL', 'BULL']
    for i, name in enumerate(state_names):
        cnt = (aligned['hmm_state'] == i).sum()
        print(f"  {name}: {cnt} days ({cnt/len(aligned)*100:.1f}%)")

    # Baseline (unfiltered)
    baseline = compute_metrics(aligned['ret'])
    print(f"\nBaseline metrics:")
    print(f"  Sharpe: {baseline['sharpe']:.4f}")
    print(f"  Ann. Return: {baseline['ann_return']*100:.2f}%")
    print(f"  MDD: {baseline['mdd']*100:.2f}%")
    print(f"  Days: {baseline['n_days']}")

    # No-bear filter: trade on NEUTRAL + BULL days
    no_bear_ret = aligned['ret'].copy()
    no_bear_ret[aligned['hmm_state'] == 0] = 0.0  # zero out bear days
    no_bear = compute_metrics(no_bear_ret)
    print(f"\nNo-Bear filter (trade on NEUTRAL+BULL):")
    print(f"  Sharpe: {no_bear['sharpe']:.4f}")
    print(f"  Ann. Return: {no_bear['ann_return']*100:.2f}%")
    print(f"  MDD: {no_bear['mdd']*100:.2f}%")
    print(f"  Active Days: {(aligned['hmm_state'] != 0).sum()}")

    # Bull-only filter: trade only on BULL days
    bull_only_ret = aligned['ret'].copy()
    bull_only_ret[aligned['hmm_state'] != 2] = 0.0
    bull_only = compute_metrics(bull_only_ret)
    print(f"\nBull-Only filter:")
    print(f"  Sharpe: {bull_only['sharpe']:.4f}")
    print(f"  Ann. Return: {bull_only['ann_return']*100:.2f}%")
    print(f"  MDD: {bull_only['mdd']*100:.2f}%")
    print(f"  Active Days: {(aligned['hmm_state'] == 2).sum()}")

    return aligned, baseline, no_bear, bull_only


# ─────────────────────────────────────────────────────────
# PHASE 4: Walk-forward validation (4-fold)
# ─────────────────────────────────────────────────────────

def walk_forward_hmm(aligned_df, btc_df_full, obs_full, n_folds=4):
    """
    4-fold time-series walk-forward:
    - Fit HMM on folds 1..n-1, apply on fold n
    - Report per-fold Sharpe delta (filtered vs baseline)
    """
    print("\n" + "="*60)
    print("PHASE 4: Walk-forward validation (4-fold)")
    print("="*60)

    N = len(aligned_df)
    fold_size = N // n_folds

    per_fold_baseline_sh = []
    per_fold_filtered_sh = []

    state_names = ['BEAR', 'NEUTRAL', 'BULL']

    for fold in range(n_folds):
        # Train: folds 0..fold, Test: fold+1
        # Standard walk-forward: train on [0, fold_size*(fold+1)), test on next fold_size
        test_start = fold_size * (fold + 1)
        test_end = test_start + fold_size if fold < n_folds - 1 else N

        if test_start >= N:
            print(f"  Fold {fold+1}: no test data, skipping")
            continue

        train_slice = aligned_df.iloc[:fold_size * (fold + 1)]
        test_slice = aligned_df.iloc[test_start:test_end]

        if len(train_slice) < 30 or len(test_slice) < 10:
            print(f"  Fold {fold+1}: too few samples, skipping")
            continue

        # Get BTC data for training period
        train_dates = train_slice.index
        test_dates = test_slice.index
        train_start_dt = train_dates[0]
        train_end_dt = train_dates[-1]

        # Map train dates to BTC bars
        btc_train = btc_df_full[
            (btc_df_full.index.normalize() >= train_start_dt) &
            (btc_df_full.index.normalize() <= train_end_dt)
        ]

        if len(btc_train) < 50:
            print(f"  Fold {fold+1}: insufficient BTC bars for training ({len(btc_train)})")
            continue

        # Fit HMM on training data
        obs_train = btc_train['log_ret'].values.reshape(-1, 1)
        model_fold = ManualGaussianHMM(n_components=3, n_iter=100, random_state=42)
        try:
            model_fold.fit(obs_train)
        except Exception as e:
            print(f"  Fold {fold+1}: HMM fit failed: {e}")
            per_fold_baseline_sh.append(np.nan)
            per_fold_filtered_sh.append(np.nan)
            continue

        # Sort states by mean
        means = model_fold.means_.flatten()
        order = np.argsort(means)
        state_map = {old: new for new, old in enumerate(order)}

        # Predict on TEST data BTC bars
        test_start_dt = test_dates[0]
        test_end_dt = test_dates[-1]
        btc_test = btc_df_full[
            (btc_df_full.index.normalize() >= test_start_dt) &
            (btc_df_full.index.normalize() <= test_end_dt)
        ]

        if len(btc_test) < 10:
            print(f"  Fold {fold+1}: too few test BTC bars")
            per_fold_baseline_sh.append(np.nan)
            per_fold_filtered_sh.append(np.nan)
            continue

        obs_test = btc_test['log_ret'].values.reshape(-1, 1)
        raw_test_states = model_fold.predict(obs_test)
        sorted_test_states = np.array([state_map[s] for s in raw_test_states])

        # Resample to daily
        btc_test_copy = btc_test.copy()
        btc_test_copy['state'] = sorted_test_states
        btc_test_copy['date'] = btc_test_copy.index.normalize()
        daily_test_states = (btc_test_copy.groupby('date')['state']
                             .agg(lambda x: x.mode()[0]))
        daily_test_states.index = pd.to_datetime(daily_test_states.index)

        # Align with test equity
        test_aligned = pd.DataFrame({
            'ret': test_slice['ret'],
            'state': daily_test_states
        }).dropna()

        if len(test_aligned) < 5:
            print(f"  Fold {fold+1}: alignment produced too few rows")
            per_fold_baseline_sh.append(np.nan)
            per_fold_filtered_sh.append(np.nan)
            continue

        # Baseline metrics for this fold
        fold_base = compute_metrics(test_aligned['ret'])

        # No-bear filter
        no_bear_ret = test_aligned['ret'].copy()
        no_bear_ret[test_aligned['state'] == 0] = 0.0
        fold_filtered = compute_metrics(no_bear_ret)

        bear_days = (test_aligned['state'] == 0).sum()
        neutral_days = (test_aligned['state'] == 1).sum()
        bull_days = (test_aligned['state'] == 2).sum()

        print(f"\n  Fold {fold+1}: train={len(train_slice)}d, test={len(test_aligned)}d")
        print(f"    Train period: {train_start_dt.date()} → {train_end_dt.date()}")
        print(f"    Test  period: {test_start_dt.date()} → {test_end_dt.date()}")
        print(f"    State dist: BEAR={bear_days}, NEUTRAL={neutral_days}, BULL={bull_days}")
        print(f"    Baseline Sh: {fold_base['sharpe']:.4f} | "
              f"No-Bear Sh: {fold_filtered['sharpe']:.4f} | "
              f"Delta: {fold_filtered['sharpe'] - fold_base['sharpe']:+.4f}")
        print(f"    Baseline MDD: {fold_base['mdd']*100:.2f}% | "
              f"No-Bear MDD: {fold_filtered['mdd']*100:.2f}%")

        per_fold_baseline_sh.append(fold_base['sharpe'])
        per_fold_filtered_sh.append(fold_filtered['sharpe'])

    return per_fold_baseline_sh, per_fold_filtered_sh


# ─────────────────────────────────────────────────────────
# PHASE 5: Decision
# ─────────────────────────────────────────────────────────

def make_decision(baseline, no_bear, bull_only,
                  per_fold_baseline, per_fold_filtered):
    print("\n" + "="*60)
    print("PHASE 5: Decision")
    print("="*60)

    valid_folds = [(b, f) for b, f in zip(per_fold_baseline, per_fold_filtered)
                   if not (np.isnan(b) or np.isnan(f))]

    if len(valid_folds) == 0:
        decision = "REJECT"
        notes = "No valid walk-forward folds — insufficient data for robust evaluation."
        print(f"Decision: {decision}")
        return decision, notes

    fold_deltas = [f - b for b, f in valid_folds]
    n_positive = sum(d > 0 for d in fold_deltas)
    n_negative = sum(d < 0 for d in fold_deltas)
    avg_delta = np.mean(fold_deltas)

    # Baseline vs filtered
    sh_improvement_pct = ((no_bear['sharpe'] - baseline['sharpe'])
                          / abs(baseline['sharpe']) * 100
                          if baseline['sharpe'] != 0 else np.nan)
    mdd_worsened = no_bear['mdd'] < baseline['mdd']  # more negative = worse
    trade_drop_pct = (1 - no_bear['n_days'] / baseline['n_days']) * 100 if baseline['n_days'] > 0 else 100

    print(f"\nSummary:")
    print(f"  Full-period Sh improvement (no-bear): {sh_improvement_pct:+.1f}%")
    print(f"  MDD worsened: {mdd_worsened}")
    print(f"  Active day drop: {trade_drop_pct:.1f}%")
    print(f"  Walk-forward fold deltas: {[f'{d:+.4f}' for d in fold_deltas]}")
    print(f"  Positive folds: {n_positive}/{len(valid_folds)}")
    print(f"  Average fold delta: {avg_delta:+.4f}")

    # Decision rules
    # ACCEPT: all folds filtered Sh > baseline Sh by >=10% AND MDD <= baseline
    # REJECT: any fold significantly worsens OR trade count drops > 60%
    # CONDITIONAL: mixed evidence

    if trade_drop_pct > 60:
        decision = "REJECT"
        notes = (f"Trade day drop {trade_drop_pct:.1f}% > 60% threshold. "
                 f"Filter is too aggressive, removing too many trading days.")
    elif n_negative > len(valid_folds) // 2:
        decision = "REJECT"
        notes = (f"Majority of folds ({n_negative}/{len(valid_folds)}) show negative Sharpe delta. "
                 f"HMM regime filter does not consistently improve K280.")
    elif sh_improvement_pct is not None and sh_improvement_pct >= 10 and not mdd_worsened and n_negative == 0:
        decision = "ACCEPT"
        notes = (f"All {len(valid_folds)} folds show positive Sharpe delta. "
                 f"Full-period Sh improves by {sh_improvement_pct:.1f}%. "
                 f"MDD maintained or improved. "
                 f"HMM regime filter is a valid addition to K280.")
    elif avg_delta > 0 and n_negative <= 1:
        decision = "CONDITIONAL"
        notes = (f"Mostly positive Sharpe deltas across {len(valid_folds)} folds "
                 f"(avg delta: {avg_delta:+.4f}). "
                 f"Sh improvement {sh_improvement_pct:+.1f}% on full period. "
                 f"Recommend extended out-of-sample test before production deployment. "
                 f"Trade count drop: {trade_drop_pct:.1f}%.")
    else:
        decision = "CONDITIONAL"
        notes = (f"Mixed results: {n_positive} positive / {n_negative} negative folds. "
                 f"Avg fold delta: {avg_delta:+.4f}. "
                 f"Full-period Sh improvement: {sh_improvement_pct:+.1f}%. "
                 f"Needs further validation before production use.")

    print(f"\nDecision: {decision}")
    print(f"Notes: {notes}")
    return decision, notes


# ─────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("WAVE K315: 3-State HMM Regime Filter Prototype for K280")
    print(f"Date: {date.today()}")
    print(f"hmmlearn available: {HMMLEARN_AVAILABLE}")
    print("=" * 60)

    # Phase 1: Fit HMM
    btc_df, sorted_means, sorted_stds, sorted_transmat, startprob, model, order = \
        fit_hmm_on_btc(BTC_4H_PATH, n_states=N_STATES, n_iter=N_ITER, random_seed=RANDOM_SEED)

    # Phase 2: Load K280 equity
    daily_ret, equity_series, k280_raw = load_k280_equity(K280_CURVES_PATH)

    # Phase 3: Apply filter
    aligned, baseline, no_bear, bull_only = \
        apply_hmm_filter(btc_df, daily_ret, equity_series)

    # Phase 4: Walk-forward
    per_fold_baseline, per_fold_filtered = \
        walk_forward_hmm(aligned, btc_df, None, n_folds=N_FOLDS)

    # Phase 5: Decision
    decision, notes = make_decision(
        baseline, no_bear, bull_only,
        per_fold_baseline, per_fold_filtered
    )

    # ─── Build output JSON ───
    results = {
        "wave": "K315",
        "date": str(date.today()),
        "hmmlearn_available": HMMLEARN_AVAILABLE,
        "hmm_implementation": "hmmlearn.GaussianHMM" if HMMLEARN_AVAILABLE else "ManualBaumWelch_EM",
        "hmm_n_states": N_STATES,
        "hmm_n_iter": N_ITER,
        "hmm_random_seed": RANDOM_SEED,
        "btc_data_source": str(BTC_4H_PATH),
        "k280_source": str(K280_CURVES_PATH),
        "k280_date_range": [str(daily_ret.index[0].date()), str(daily_ret.index[-1].date())],
        "k280_n_days": len(daily_ret),
        "hmm_state_names": ["BEAR", "NEUTRAL", "BULL"],
        "hmm_state_means": sorted_means.tolist(),
        "hmm_state_stds": sorted_stds.tolist(),
        "hmm_transition_matrix": sorted_transmat.tolist(),
        "hmm_startprob": startprob[order].tolist(),
        "baseline_sh": baseline["sharpe"],
        "baseline_mdd": baseline["mdd"],
        "baseline_trades": baseline["n_days"],
        "baseline_ann_return": baseline["ann_return"],
        "no_bear_sh": no_bear["sharpe"],
        "no_bear_mdd": no_bear["mdd"],
        "no_bear_trades": no_bear["n_days"],
        "no_bear_ann_return": no_bear["ann_return"],
        "bull_only_sh": bull_only["sharpe"],
        "bull_only_mdd": bull_only["mdd"],
        "bull_only_trades": bull_only["n_days"],
        "bull_only_ann_return": bull_only["ann_return"],
        "per_fold_baseline_sh": per_fold_baseline,
        "per_fold_filtered_sh": per_fold_filtered,
        "fold_deltas": [
            round(f - b, 6) for b, f in zip(per_fold_baseline, per_fold_filtered)
            if not (np.isnan(b) or np.isnan(f))
        ],
        "decision": decision,
        "notes": notes,
        "limitations": [
            "K280 equity covers 2025-01-22 to 2026-04-14 only (~15 months) — limited walk-forward depth",
            "K280 Sharpe ~17 suggests highly risk-controlled / near-delta-neutral strategy with low daily vol",
            "hmmlearn not available; manual Baum-Welch EM used (mathematically equivalent but slower)",
            "Bayesian non-homogeneous transition matrix not implemented — standard stationary HMM used",
            "Daily PnL zeroing is a simplified filter; production would need intraday regime lookback",
        ]
    }

    out_json = REPO / "wave_k315_hmm_regime.json"
    with open(out_json, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n[OUTPUT] Written: {out_json}")

    return results, aligned, baseline, no_bear, bull_only


if __name__ == "__main__":
    results, aligned, baseline, no_bear, bull_only = main()
    print("\n[DONE] Wave K315 complete.")
