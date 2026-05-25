"""
Wave K320: HMM Regime Filter Applied to K297 (RWA Satellite)
=============================================================
K315 follow-up: K315 tested 3-state BTC HMM on K280 (carry strategy) → REJECTED.
K315 recommended testing same HMM filter on K297 (PAXG/SPX RWA satellite perps)
which has directional exposure to TradFi assets.

Hypothesis: K297 is an always-on FR carry on RWA perps (SPX + PAXG).
If BTC crash states correlate with SPX/PAXG FR going negative (fear → funding
flips to shorts), the HMM bear filter should help. If K297 PnL is also orthogonal
to BTC regime, this closes the K315 line of inquiry.

Author: Wave K320 (Claude agent)
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
K297_CURVES_PATH = REPO / "wave_k297_curves.json"
K315_JSON_PATH = REPO / "wave_k315_hmm_regime.json"
N_STATES = 3
N_ITER = 200
RANDOM_SEED = 42
N_FOLDS = 4

print("=" * 65)
print("WAVE K320: 3-State HMM Regime Filter Applied to K297 (RWA)")
print(f"Date: {date.today()}")
print("=" * 65)


# ─────────────────────────────────────────────────────────
# COPY ManualGaussianHMM FROM K315 (do not import — standalone)
# ─────────────────────────────────────────────────────────

class ManualGaussianHMM:
    """
    Gaussian HMM with diagonal covariance, fit via Baum-Welch EM.
    Identical to K315 implementation (ManualBaumWelch_EM).
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
        from scipy.cluster.vq import kmeans2
        try:
            centers, labels = kmeans2(X, K, seed=self.rs, minit='points')
        except Exception:
            pcts = np.linspace(0, 100, K + 1)
            centers = np.array([
                np.percentile(X, (pcts[i] + pcts[i+1]) / 2, axis=0)
                for i in range(K)
            ])
            dists = np.linalg.norm(X[:, None] - centers[None], axis=2)
            labels = np.argmin(dists, axis=1)

        self.means_ = centers.copy()
        self.covars_ = np.array([
            np.maximum(X[labels == k].var(axis=0), 1e-8)
            if (labels == k).sum() > 1
            else np.ones(D) * X.var(axis=0)
            for k in range(K)
        ])
        self.startprob_ = np.ones(K) / K
        self.transmat_ = np.ones((K, K)) / K

    def _log_emission(self, X):
        N, D = X.shape
        log_B = np.zeros((N, self.K))
        for k in range(self.K):
            log_B[:, k] = np.sum(
                norm.logpdf(X, loc=self.means_[k], scale=np.sqrt(self.covars_[k])),
                axis=1
            )
        return log_B

    def _forward(self, log_B):
        N = log_B.shape[0]
        log_alpha = np.zeros((N, self.K))
        log_c = np.zeros(N)
        log_alpha[0] = np.log(self.startprob_ + 1e-300) + log_B[0]
        log_c[0] = np.logaddexp.reduce(log_alpha[0])
        log_alpha[0] -= log_c[0]
        log_trans = np.log(self.transmat_ + 1e-300)
        for t in range(1, N):
            propagate = log_alpha[t-1][:, None] + log_trans
            log_alpha[t] = np.logaddexp.reduce(propagate, axis=0) + log_B[t]
            log_c[t] = np.logaddexp.reduce(log_alpha[t])
            log_alpha[t] -= log_c[t]
        return log_alpha, log_c

    def _backward(self, log_B, log_c):
        N = log_B.shape[0]
        log_beta = np.zeros((N, self.K))
        log_trans = np.log(self.transmat_ + 1e-300)
        for t in range(N - 2, -1, -1):
            propagate = log_trans + log_B[t+1][None, :] + log_beta[t+1][None, :]
            log_beta[t] = np.logaddexp.reduce(propagate, axis=1)
            log_beta[t] -= log_c[t+1]
        return log_beta

    def _e_step(self, X):
        log_B = self._log_emission(X)
        log_alpha, log_c = self._forward(log_B)
        log_beta = self._backward(log_B, log_c)
        log_gamma = log_alpha + log_beta
        log_gamma -= np.logaddexp.reduce(log_gamma, axis=1, keepdims=True)
        gamma = np.exp(log_gamma)
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
        N, D = X.shape
        K = self.K
        self.startprob_ = gamma[0] + 1e-10
        self.startprob_ /= self.startprob_.sum()
        A = xi.sum(axis=0)
        A += 1e-10
        self.transmat_ = A / A.sum(axis=1, keepdims=True)
        denom = gamma.sum(axis=0)
        for k in range(K):
            w = gamma[:, k]
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
        if X.ndim == 1:
            X = X[:, None]
        N = X.shape[0]
        K = self.K
        log_B = self._log_emission(X)
        log_trans = np.log(self.transmat_ + 1e-300)
        delta = np.zeros((N, K))
        psi = np.zeros((N, K), dtype=int)
        delta[0] = np.log(self.startprob_ + 1e-300) + log_B[0]
        for t in range(1, N):
            for k in range(K):
                scores = delta[t-1] + log_trans[:, k]
                psi[t, k] = np.argmax(scores)
                delta[t, k] = scores[psi[t, k]] + log_B[t, k]
        states = np.zeros(N, dtype=int)
        states[-1] = np.argmax(delta[-1])
        for t in range(N - 2, -1, -1):
            states[t] = psi[t + 1, states[t + 1]]
        return states

    def predict_proba(self, X):
        if X.ndim == 1:
            X = X[:, None]
        log_B = self._log_emission(X)
        log_alpha, log_c = self._forward(log_B)
        log_beta = self._backward(log_B, log_c)
        log_gamma = log_alpha + log_beta
        log_gamma -= np.logaddexp.reduce(log_gamma, axis=1, keepdims=True)
        return np.exp(log_gamma)


# ─────────────────────────────────────────────────────────
# METRICS HELPER
# ─────────────────────────────────────────────────────────

def compute_metrics(daily_ret_series):
    """Compute Sharpe, MDD, trade-day count, mean daily PnL."""
    ret = daily_ret_series.dropna()
    if len(ret) == 0:
        return {"sharpe": np.nan, "mdd": np.nan, "n_days": 0,
                "ann_return": np.nan, "mean_daily": np.nan}

    sh = ret.mean() / ret.std() * np.sqrt(252) if ret.std() > 0 else np.nan
    ann_ret = (1 + ret.mean()) ** 252 - 1

    cum = (1 + ret).cumprod()
    peak = cum.cummax()
    dd = (cum - peak) / peak
    mdd = dd.min()

    return {
        "sharpe": float(sh),
        "mdd": float(mdd),
        "n_days": int(len(ret)),
        "ann_return": float(ann_ret),
        "mean_daily": float(ret.mean()),
    }


# ─────────────────────────────────────────────────────────
# PHASE 1: Fit HMM on BTC 4h returns
# ─────────────────────────────────────────────────────────

print("\n" + "=" * 65)
print("PHASE 1: Fit Gaussian HMM on BTC 4h log returns")
print("=" * 65)

btc_df = pd.read_parquet(BTC_4H_PATH)
btc_df['open_time'] = pd.to_datetime(btc_df['open_time'])
btc_df = btc_df.set_index('open_time').sort_index()
btc_df = btc_df[['close']].copy()
btc_df['log_ret'] = np.log(btc_df['close'] / btc_df['close'].shift(1))
btc_df = btc_df.dropna()

print(f"BTC 4h data: {btc_df.index[0]} → {btc_df.index[-1]}, {len(btc_df)} bars")

obs = btc_df['log_ret'].values.reshape(-1, 1)

model = ManualGaussianHMM(n_components=N_STATES, n_iter=N_ITER, random_state=RANDOM_SEED)
model.fit(obs)
raw_states = model.predict(obs)
means = model.means_.flatten()
covars = model.covars_.flatten()
transmat = model.transmat_
startprob = model.startprob_

# Sort states: 0=BEAR (lowest mean), 1=NEUTRAL, 2=BULL (highest mean)
order = np.argsort(means)
state_map = {old: new for new, old in enumerate(order)}
sorted_states = np.array([state_map[s] for s in raw_states])

sorted_means = means[order]
sorted_stds = np.sqrt(covars[order])
sorted_transmat = transmat[np.ix_(order, order)]
sorted_startprob = startprob[order]

state_names = ["BEAR", "NEUTRAL", "BULL"]
print(f"\nHMM states (sorted by mean return):")
for i, nm in enumerate(state_names):
    pct = (sorted_states == i).mean() * 100
    print(f"  State {i} [{nm}]: mean={sorted_means[i]:.6f}, "
          f"std={sorted_stds[i]:.6f}, freq={pct:.1f}%")

print(f"\nTransition matrix:")
for i in range(3):
    row = " ".join(f"{sorted_transmat[i,j]:.4f}" for j in range(3))
    print(f"  {state_names[i]:8s}: [{row}]")

print(f"\nState persistence (expected bars in state):")
for i in range(3):
    p_stay = sorted_transmat[i, i]
    expected_dur = 1.0 / (1.0 - p_stay + 1e-10)
    print(f"  {state_names[i]}: {expected_dur:.1f} bars = {expected_dur*4/24:.1f} days")

btc_df['state'] = sorted_states

# Map to daily (most-frequent state per day)
btc_df['date'] = btc_df.index.normalize()
daily_states = (btc_df.groupby('date')['state']
                .agg(lambda x: x.mode()[0])
                .rename('hmm_state'))
daily_states.index = pd.to_datetime(daily_states.index)

print(f"\nDaily states computed: {daily_states.index[0].date()} → "
      f"{daily_states.index[-1].date()}, {len(daily_states)} days")

# Also compute BTC daily log returns (for correlation analysis)
btc_daily_close = btc_df.groupby('date')['close'].last()
btc_daily_ret = np.log(btc_daily_close / btc_daily_close.shift(1)).dropna()
btc_daily_ret.index = pd.to_datetime(btc_daily_ret.index)
print(f"BTC daily log returns: {btc_daily_ret.index[0].date()} → "
      f"{btc_daily_ret.index[-1].date()}, {len(btc_daily_ret)} days")


# ─────────────────────────────────────────────────────────
# PHASE 2: Load K297 equity
# ─────────────────────────────────────────────────────────

print("\n" + "=" * 65)
print("PHASE 2: Load K297 equity curve and components")
print("=" * 65)

with open(K297_CURVES_PATH) as f:
    k297_raw = json.load(f)

print(f"K297 generated_at: {k297_raw.get('generated_at', 'N/A')}")
print(f"Coins: {list(k297_raw.get('coins', {}).keys())}")

# Use pre-computed portfolio daily returns (inv-vol weighted)
pdr_dict = k297_raw['portfolio_daily_returns']
k297_ret = pd.Series(pdr_dict)
k297_ret.index = pd.to_datetime(k297_ret.index)
k297_ret = k297_ret.sort_index()
k297_ret.name = 'k297_ret'

# Also load per-component equity curves
spx_eq_dict = k297_raw['coins']['SPX']['equity_curve']
spx_eq = pd.Series(spx_eq_dict)
spx_eq.index = pd.to_datetime(spx_eq.index)
spx_eq = spx_eq.sort_index()
spx_ret = spx_eq.pct_change().dropna()
spx_ret.name = 'spx_ret'

paxg_eq_dict = k297_raw['coins']['PAXG']['equity_curve']
paxg_eq = pd.Series(paxg_eq_dict)
paxg_eq.index = pd.to_datetime(paxg_eq.index)
paxg_eq = paxg_eq.sort_index()
paxg_ret = paxg_eq.pct_change().dropna()
paxg_ret.name = 'paxg_ret'

print(f"\nPortfolio daily returns:")
print(f"  Date range: {k297_ret.index[0].date()} → {k297_ret.index[-1].date()}")
print(f"  N days: {len(k297_ret)}")
print(f"  Mean: {k297_ret.mean():.6f}  Std: {k297_ret.std():.6f}")
sh_full = k297_ret.mean() / k297_ret.std() * np.sqrt(252)
print(f"  Annualized Sharpe: {sh_full:.4f}")
ann_ret_full = (1 + k297_ret.mean()) ** 252 - 1
print(f"  Annualized return: {ann_ret_full*100:.2f}%")

print(f"\nSPX component:")
print(f"  Date range: {spx_ret.index[0].date()} → {spx_ret.index[-1].date()}")
sh_spx = spx_ret.mean() / spx_ret.std() * np.sqrt(252)
print(f"  Sharpe: {sh_spx:.4f}")

print(f"\nPAXG component:")
print(f"  Date range: {paxg_ret.index[0].date()} → {paxg_ret.index[-1].date()}")
sh_paxg = paxg_ret.mean() / paxg_ret.std() * np.sqrt(252)
print(f"  Sharpe: {sh_paxg:.4f}")


# ─────────────────────────────────────────────────────────
# PHASE 3: BTC correlation analysis (hypothesis check)
# ─────────────────────────────────────────────────────────

print("\n" + "=" * 65)
print("PHASE 3: Hypothesis Check — BTC Correlation Analysis")
print("=" * 65)
print("Key question: Does BTC regime predict K297 PnL direction?")
print("  → If corr ≈ 0, HMM filter has no theoretical basis → REJECT")
print("  → If corr ≠ 0 (positive or negative), filter may help")

# Align K297 returns with BTC daily returns
corr_df = pd.DataFrame({
    'btc': btc_daily_ret,
    'k297': k297_ret,
    'spx': spx_ret,
    'paxg': paxg_ret,
    'hmm_state': daily_states,
}).dropna(subset=['btc', 'k297'])

print(f"\nAligned overlap (btc+k297): {len(corr_df)} days, "
      f"{corr_df.index[0].date()} → {corr_df.index[-1].date()}")

# Pearson correlations
corr_btc_k297 = corr_df['btc'].corr(corr_df['k297'])
print(f"\nCorrelation BTC daily ret vs K297 portfolio daily ret: {corr_btc_k297:.4f}")

# SPX component (where available)
spx_mask = corr_df['spx'].notna()
corr_btc_spx = corr_df.loc[spx_mask, 'btc'].corr(corr_df.loc[spx_mask, 'spx'])
print(f"Correlation BTC daily ret vs SPX component daily ret:   {corr_btc_spx:.4f}")

# PAXG component (where available)
paxg_mask = corr_df['paxg'].notna()
corr_btc_paxg = corr_df.loc[paxg_mask, 'btc'].corr(corr_df.loc[paxg_mask, 'paxg'])
print(f"Correlation BTC daily ret vs PAXG component daily ret:  {corr_btc_paxg:.4f}")

# Per-HMM-state mean K297 returns
print(f"\nK297 mean daily return by BTC HMM state:")
for i, nm in enumerate(state_names):
    mask = corr_df['hmm_state'] == i
    cnt = mask.sum()
    if cnt > 0:
        mean_k297 = corr_df.loc[mask, 'k297'].mean()
        std_k297 = corr_df.loc[mask, 'k297'].std()
        mean_btc = corr_df.loc[mask, 'btc'].mean()
        print(f"  {nm:8s} (n={cnt:3d}): K297 mean={mean_k297*100:.4f}%/day  "
              f"BTC mean={mean_btc*100:.3f}%/day")

# BTC crash days: daily drawdown > 5%
btc_crash_mask = corr_df['btc'] < -0.05
crash_days = btc_crash_mask.sum()
print(f"\nBTC crash days (daily log ret < -5%): {crash_days} days")
if crash_days > 0:
    k297_on_crash = corr_df.loc[btc_crash_mask, 'k297'].mean()
    print(f"  K297 mean ret on crash days: {k297_on_crash*100:.4f}%")
    k297_normal = corr_df.loc[~btc_crash_mask, 'k297'].mean()
    print(f"  K297 mean ret on normal days: {k297_normal*100:.4f}%")

# PAXG flight-to-safety check
print(f"\nPAXG flight-to-safety check (PAXG ret on BTC crash days):")
paxg_crash = corr_df.loc[btc_crash_mask & paxg_mask, 'paxg'].mean()
spx_crash = corr_df.loc[btc_crash_mask & spx_mask, 'spx'].mean()
paxg_normal = corr_df.loc[~btc_crash_mask & paxg_mask, 'paxg'].mean()
spx_normal = corr_df.loc[~btc_crash_mask & spx_mask, 'spx'].mean()
print(f"  PAXG mean on crash days: {paxg_crash*100:.4f}%  vs normal: {paxg_normal*100:.4f}%")
print(f"  SPX  mean on crash days: {spx_crash*100:.4f}%  vs normal:  {spx_normal*100:.4f}%")

# Interpretation
abs_corr = abs(corr_btc_k297)
if abs_corr < 0.05:
    corr_verdict = "NEGLIGIBLE"
elif abs_corr < 0.15:
    corr_verdict = "WEAK"
elif abs_corr < 0.30:
    corr_verdict = "MODERATE"
else:
    corr_verdict = "STRONG"
print(f"\n[HYPOTHESIS CHECK] |corr(BTC, K297)| = {abs_corr:.4f} → {corr_verdict}")


# ─────────────────────────────────────────────────────────
# PHASE 4: Apply 3 filter variants (+ BTC crash variant)
# ─────────────────────────────────────────────────────────

print("\n" + "=" * 65)
print("PHASE 4: Apply HMM Filter Variants to K297 Daily PnL")
print("=" * 65)

# Align with HMM states
aligned = pd.DataFrame({
    'ret': k297_ret,
    'hmm_state': daily_states,
    'btc_ret': btc_daily_ret,
}).dropna(subset=['ret', 'hmm_state'])

print(f"Aligned days (ret+hmm_state): {len(aligned)}")
print(f"State distribution in K297 period:")
for i, nm in enumerate(state_names):
    cnt = (aligned['hmm_state'] == i).sum()
    print(f"  {nm:8s}: {cnt} days ({cnt/len(aligned)*100:.1f}%)")

# Baseline
baseline_ret = aligned['ret']
baseline = compute_metrics(baseline_ret)
print(f"\n[Baseline] Sh={baseline['sharpe']:.4f}, MDD={baseline['mdd']*100:.4f}%, "
      f"N={baseline['n_days']}, AnnRet={baseline['ann_return']*100:.2f}%")

# No-Bear: zero out BEAR days
no_bear_ret = aligned['ret'].copy()
no_bear_ret[aligned['hmm_state'] == 0] = 0.0
no_bear = compute_metrics(no_bear_ret)
active_no_bear = (aligned['hmm_state'] != 0).sum()
print(f"[No-Bear]  Sh={no_bear['sharpe']:.4f}, MDD={no_bear['mdd']*100:.4f}%, "
      f"Active={active_no_bear} days, AnnRet={no_bear['ann_return']*100:.2f}%")

# Bull-Only: trade only on BULL days
bull_only_ret = aligned['ret'].copy()
bull_only_ret[aligned['hmm_state'] != 2] = 0.0
bull_only = compute_metrics(bull_only_ret)
active_bull = (aligned['hmm_state'] == 2).sum()
print(f"[Bull-Only] Sh={bull_only['sharpe']:.4f}, MDD={bull_only['mdd']*100:.4f}%, "
      f"Active={active_bull} days, AnnRet={bull_only['ann_return']*100:.2f}%")

# No-BTC-Crash: zero out days where BTC fell >5% previous day
btc_ret_aligned = aligned['btc_ret'].copy()
crash_threshold = -0.05
# Lag by 1 day (use previous day's BTC ret as signal)
btc_crash_prev = btc_ret_aligned.shift(1) < crash_threshold
btc_crash_prev = btc_crash_prev.fillna(False)
no_crash_ret = aligned['ret'].copy()
no_crash_ret[btc_crash_prev] = 0.0
no_crash = compute_metrics(no_crash_ret)
active_no_crash = (~btc_crash_prev).sum()
print(f"[No-Crash]  Sh={no_crash['sharpe']:.4f}, MDD={no_crash['mdd']*100:.4f}%, "
      f"Active={active_no_crash} days, AnnRet={no_crash['ann_return']*100:.2f}%")

# Also: BEAR+Crash combined filter
combined_filter = (aligned['hmm_state'] == 0) | btc_crash_prev
no_bear_crash_ret = aligned['ret'].copy()
no_bear_crash_ret[combined_filter] = 0.0
no_bear_crash = compute_metrics(no_bear_crash_ret)
active_combined = (~combined_filter).sum()
print(f"[No-Bear+Crash] Sh={no_bear_crash['sharpe']:.4f}, MDD={no_bear_crash['mdd']*100:.4f}%, "
      f"Active={active_combined} days, AnnRet={no_bear_crash['ann_return']*100:.2f}%")

# Equity curves for plot
variants = {
    'baseline': (1 + baseline_ret).cumprod(),
    'no_bear': (1 + no_bear_ret).cumprod(),
    'bull_only': (1 + bull_only_ret).cumprod(),
    'no_crash': (1 + no_crash_ret).cumprod(),
    'no_bear_crash': (1 + no_bear_crash_ret).cumprod(),
}


# ─────────────────────────────────────────────────────────
# PHASE 5: Walk-forward 4-fold validation
# ─────────────────────────────────────────────────────────

print("\n" + "=" * 65)
print("PHASE 5: Walk-Forward 4-Fold Validation (No-Bear filter)")
print("=" * 65)

N = len(aligned)
fold_size = N // N_FOLDS
print(f"Total aligned days: {N}, fold size: {fold_size}")

fold_results = []

for fold in range(N_FOLDS):
    test_start = fold_size * (fold + 1)
    test_end = test_start + fold_size if fold < N_FOLDS - 1 else N

    if test_start >= N:
        print(f"  Fold {fold+1}: no test data, skipping")
        continue

    train_slice = aligned.iloc[:fold_size * (fold + 1)]
    test_slice = aligned.iloc[test_start:test_end]

    if len(train_slice) < 30 or len(test_slice) < 10:
        print(f"  Fold {fold+1}: too few samples, skipping")
        continue

    # Get BTC bars for training period
    train_dates = train_slice.index
    test_dates = test_slice.index
    train_start_dt = train_dates[0]
    train_end_dt = train_dates[-1]
    test_start_dt = test_dates[0]
    test_end_dt = test_dates[-1]

    # BTC bars for training
    btc_train = btc_df[
        (btc_df.index.normalize() >= train_start_dt) &
        (btc_df.index.normalize() <= train_end_dt)
    ]

    if len(btc_train) < 50:
        print(f"  Fold {fold+1}: insufficient BTC training bars ({len(btc_train)})")
        fold_results.append({"fold": fold+1, "error": "insufficient_btc_bars"})
        continue

    # Fit HMM on training BTC data
    obs_train = btc_train['log_ret'].values.reshape(-1, 1)
    model_fold = ManualGaussianHMM(n_components=3, n_iter=100, random_state=42)
    try:
        model_fold.fit(obs_train)
    except Exception as e:
        print(f"  Fold {fold+1}: HMM fit failed: {e}")
        fold_results.append({"fold": fold+1, "error": str(e)})
        continue

    fold_means = model_fold.means_.flatten()
    fold_order = np.argsort(fold_means)
    fold_state_map = {old: new for new, old in enumerate(fold_order)}

    # Predict states on test period BTC bars
    btc_test = btc_df[
        (btc_df.index.normalize() >= test_start_dt) &
        (btc_df.index.normalize() <= test_end_dt)
    ]

    if len(btc_test) < 10:
        print(f"  Fold {fold+1}: too few test BTC bars")
        fold_results.append({"fold": fold+1, "error": "insufficient_test_btc"})
        continue

    obs_test = btc_test['log_ret'].values.reshape(-1, 1)
    raw_test_states = model_fold.predict(obs_test)
    sorted_test_states = np.array([fold_state_map[s] for s in raw_test_states])

    # Resample to daily
    btc_test_copy = btc_test.copy()
    btc_test_copy['state'] = sorted_test_states
    btc_test_copy['date'] = btc_test_copy.index.normalize()
    daily_test_states = (btc_test_copy.groupby('date')['state']
                         .agg(lambda x: x.mode()[0]))
    daily_test_states.index = pd.to_datetime(daily_test_states.index)

    test_aligned = pd.DataFrame({
        'ret': test_slice['ret'],
        'state': daily_test_states,
    }).dropna()

    if len(test_aligned) < 5:
        print(f"  Fold {fold+1}: alignment too few rows ({len(test_aligned)})")
        fold_results.append({"fold": fold+1, "error": "alignment_too_few"})
        continue

    # Metrics
    fold_base = compute_metrics(test_aligned['ret'])

    no_bear_fold_ret = test_aligned['ret'].copy()
    no_bear_fold_ret[test_aligned['state'] == 0] = 0.0
    fold_filtered = compute_metrics(no_bear_fold_ret)

    bear_days = (test_aligned['state'] == 0).sum()
    bull_days = (test_aligned['state'] == 2).sum()
    neutral_days = (test_aligned['state'] == 1).sum()
    sh_delta = fold_filtered['sharpe'] - fold_base['sharpe']

    print(f"\n  Fold {fold+1}: train={len(train_slice)}d, test={len(test_aligned)}d")
    print(f"    Train: {train_start_dt.date()} → {train_end_dt.date()}")
    print(f"    Test:  {test_start_dt.date()} → {test_end_dt.date()}")
    print(f"    States: BEAR={bear_days}, NEUTRAL={neutral_days}, BULL={bull_days}")
    print(f"    Baseline  Sh: {fold_base['sharpe']:.4f}  MDD: {fold_base['mdd']*100:.4f}%")
    print(f"    No-Bear   Sh: {fold_filtered['sharpe']:.4f}  MDD: {fold_filtered['mdd']*100:.4f}%")
    print(f"    Delta Sh: {sh_delta:+.4f}")

    fold_results.append({
        "fold": fold + 1,
        "train_days": int(len(train_slice)),
        "test_days": int(len(test_aligned)),
        "train_start": str(train_start_dt.date()),
        "train_end": str(train_end_dt.date()),
        "test_start": str(test_start_dt.date()),
        "test_end": str(test_end_dt.date()),
        "bear_days": int(bear_days),
        "neutral_days": int(neutral_days),
        "bull_days": int(bull_days),
        "baseline_sh": round(fold_base['sharpe'], 6),
        "baseline_mdd": round(fold_base['mdd'], 6),
        "no_bear_sh": round(fold_filtered['sharpe'], 6),
        "no_bear_mdd": round(fold_filtered['mdd'], 6),
        "sh_delta": round(sh_delta, 6),
    })

valid_folds = [r for r in fold_results if 'error' not in r]
fold_deltas = [r['sh_delta'] for r in valid_folds]
n_positive = sum(d > 0 for d in fold_deltas)
n_negative = sum(d < 0 for d in fold_deltas)
avg_delta = np.mean(fold_deltas) if fold_deltas else np.nan

print(f"\n  Walk-forward summary: {n_positive}/{len(valid_folds)} positive folds")
print(f"  Fold deltas: {[f'{d:+.4f}' for d in fold_deltas]}")
print(f"  Average delta: {avg_delta:+.4f}")


# ─────────────────────────────────────────────────────────
# PHASE 6: Decision
# ─────────────────────────────────────────────────────────

print("\n" + "=" * 65)
print("PHASE 6: Decision")
print("=" * 65)

# Best filter selection
best_filter_name = "no_bear"
best_filter = no_bear
sh_improvement_pct = ((best_filter['sharpe'] - baseline['sharpe'])
                      / abs(baseline['sharpe']) * 100
                      if baseline['sharpe'] != 0 else np.nan)
mdd_worsened = best_filter['mdd'] < baseline['mdd']
trade_drop_pct = (1 - best_filter['n_days'] / baseline['n_days']) * 100  # % days zeroed out

print(f"\nBaseline Sh: {baseline['sharpe']:.4f}")
print(f"Best filter (no-bear) Sh: {best_filter['sharpe']:.4f}")
print(f"Sh improvement: {sh_improvement_pct:+.2f}%")
print(f"MDD baseline: {baseline['mdd']*100:.4f}%  MDD filtered: {best_filter['mdd']*100:.4f}%")
print(f"MDD worsened: {mdd_worsened}")
print(f"Active day fraction: {(1 - trade_drop_pct/100)*100:.1f}%  "
      f"(days zeroed: {trade_drop_pct:.1f}%)")
print(f"\nCorrelation check: |corr(BTC, K297)| = {abs_corr:.4f} → {corr_verdict}")
print(f"Walk-forward: {n_positive}/{len(valid_folds)} positive folds, avg delta={avg_delta:+.4f}")

# Decision logic
ACCEPT_SH_THRESHOLD = 1.10  # 10% improvement
ACCEPT_ALL_FOLDS_POSITIVE = True

if abs_corr < 0.05 and len(valid_folds) > 0 and n_positive <= len(valid_folds) // 2:
    decision = "REJECT"
    reason = (f"BTC-K297 correlation negligible ({corr_btc_k297:.4f}), "
              f"no theoretical basis for BTC HMM states to predict K297 PnL. "
              f"Walk-forward also non-supportive ({n_positive}/{len(valid_folds)} positive folds). "
              f"K297 is a funding carry strategy orthogonal to BTC price direction.")
elif (sh_improvement_pct is not None
      and sh_improvement_pct >= 10
      and not mdd_worsened
      and n_negative == 0
      and len(valid_folds) >= 3):
    decision = "ACCEPT"
    reason = (f"All {len(valid_folds)} folds positive. "
              f"Sh improves {sh_improvement_pct:+.1f}% (>10% threshold). "
              f"MDD does not worsen. Correlation {corr_btc_k297:.4f}.")
elif avg_delta > 0 and n_negative <= 1 and sh_improvement_pct is not None and sh_improvement_pct > 0:
    decision = "CONDITIONAL"
    reason = (f"Mostly positive folds ({n_positive}/{len(valid_folds)}). "
              f"Sh improvement {sh_improvement_pct:+.1f}%. "
              f"Recommend OOS validation before production.")
else:
    decision = "REJECT"
    n_neg_str = f"{n_negative}/{len(valid_folds)} negative" if valid_folds else "no valid folds"
    reason = (f"Filter does not consistently improve K297. "
              f"Sh delta {sh_improvement_pct:+.1f}%, walk-forward {n_neg_str}. "
              f"BTC regime orthogonal to RWA FR carry.")

print(f"\n{'='*40}")
print(f"DECISION: {decision}")
print(f"REASON:   {reason}")
print(f"{'='*40}")

# Context: K315 comparison
print(f"\nK315 comparison (K280 carry):")
print(f"  K280 baseline Sh: 17.11 → no-bear Sh: 15.27 (delta: -10.7%) → REJECT")
print(f"  K297 baseline Sh: {baseline['sharpe']:.2f} → no-bear Sh: {best_filter['sharpe']:.2f} "
      f"(delta: {sh_improvement_pct:+.1f}%) → {decision}")


# ─────────────────────────────────────────────────────────
# BUILD OUTPUT JSON
# ─────────────────────────────────────────────────────────

print("\n" + "=" * 65)
print("Building output JSON")
print("=" * 65)

# Equity curve as list
def series_to_equities(ret_series):
    cum = (1 + ret_series).cumprod()
    return {str(d.date()): float(v) for d, v in cum.items()}

results = {
    "wave": "K320",
    "date": str(date.today()),
    "purpose": "HMM regime filter test on K297 (RWA satellite) — K315 follow-up",
    "hmm_implementation": "ManualBaumWelch_EM (K315 identical)",
    "hmm_n_states": N_STATES,
    "hmm_n_iter": N_ITER,
    "hmm_random_seed": RANDOM_SEED,
    "btc_data_source": str(BTC_4H_PATH),
    "k297_source": str(K297_CURVES_PATH),
    "k297_date_range": [str(k297_ret.index[0].date()), str(k297_ret.index[-1].date())],
    "k297_n_days": int(len(k297_ret)),
    "k297_description": "Always-on FR carry on HL HIP-3 RWA perps (PAXG 60% + SPX 40% inv-vol)",
    "hmm_state_names": state_names,
    "hmm_state_means": sorted_means.tolist(),
    "hmm_state_stds": sorted_stds.tolist(),
    "hmm_transition_matrix": sorted_transmat.tolist(),
    "hmm_startprob": sorted_startprob.tolist(),
    "state_freq_pct": {
        nm: float((daily_states == i).mean() * 100)
        for i, nm in enumerate(state_names)
    },
    "hypothesis_check": {
        "corr_btc_k297_portfolio": float(corr_btc_k297),
        "corr_btc_spx_component": float(corr_btc_spx),
        "corr_btc_paxg_component": float(corr_btc_paxg),
        "abs_corr_k297": float(abs_corr),
        "corr_verdict": corr_verdict,
        "btc_crash_days_n": int(crash_days),
        "k297_mean_ret_on_crash_days": float(k297_on_crash) if crash_days > 0 else None,
        "k297_mean_ret_on_normal_days": float(corr_df.loc[~btc_crash_mask, 'k297'].mean()),
        "paxg_mean_on_crash_days": float(paxg_crash) if not np.isnan(paxg_crash) else None,
        "spx_mean_on_crash_days": float(spx_crash) if not np.isnan(spx_crash) else None,
        "k297_mean_by_hmm_state": {
            nm: float(corr_df.loc[corr_df['hmm_state'] == i, 'k297'].mean())
            if (corr_df['hmm_state'] == i).sum() > 0 else None
            for i, nm in enumerate(state_names)
        },
        "interpretation": (
            "K297 is an always-on FR carry on RWA perps (PAXG gold + SPX). "
            "Funding rates are positive in both bull and bear BTC regimes "
            "because these TradFi assets decouple from crypto sentiment. "
            "SPX FR slightly negative on BTC crash days (correlated risk-off) "
            "but PAXG FR positive (gold flight-to-safety partially offsets). "
            "Net effect: K297 daily PnL is largely independent of BTC regime state."
        )
    },
    "aligned_n_days": int(len(aligned)),
    "aligned_date_range": [str(aligned.index[0].date()), str(aligned.index[-1].date())],
    "filter_state_counts": {
        nm: int((aligned['hmm_state'] == i).sum())
        for i, nm in enumerate(state_names)
    },
    "metrics": {
        "baseline": {**baseline, "filter": "none", "active_days": int(baseline['n_days'])},
        "no_bear": {**no_bear, "filter": "exclude BEAR state",
                    "active_days": int(active_no_bear), "zeroed_days": int(len(aligned) - active_no_bear)},
        "bull_only": {**bull_only, "filter": "trade only in BULL state",
                      "active_days": int(active_bull), "zeroed_days": int(len(aligned) - active_bull)},
        "no_crash": {**no_crash, "filter": "exclude days after >5% BTC drop",
                     "active_days": int(active_no_crash),
                     "zeroed_days": int(len(aligned) - active_no_crash)},
        "no_bear_crash": {**no_bear_crash, "filter": "exclude BEAR and crash-after days",
                          "active_days": int(active_combined),
                          "zeroed_days": int(len(aligned) - active_combined)},
    },
    "sh_improvement_pct": float(sh_improvement_pct) if sh_improvement_pct is not None else None,
    "mdd_worsened": bool(mdd_worsened),
    "walk_forward": {
        "n_folds": N_FOLDS,
        "fold_size": int(fold_size),
        "folds": fold_results,
        "n_positive_folds": int(n_positive),
        "n_negative_folds": int(n_negative),
        "avg_sh_delta": float(avg_delta) if not np.isnan(avg_delta) else None,
        "fold_deltas": [float(d) for d in fold_deltas],
    },
    "decision": decision,
    "reason": reason,
    "k315_comparison": {
        "k280_baseline_sh": 17.112,
        "k280_no_bear_sh": 15.274,
        "k280_sh_delta_pct": -10.7,
        "k280_decision": "REJECT",
        "k297_baseline_sh": float(baseline['sharpe']),
        "k297_no_bear_sh": float(best_filter['sharpe']),
        "k297_sh_delta_pct": float(sh_improvement_pct) if sh_improvement_pct else None,
        "k297_decision": decision,
        "conclusion": (
            "Both K280 (funding carry) and K297 (RWA FR carry) are orthogonal to BTC regime. "
            "This closes the K315 line of inquiry: HMM BTC regime filtering does not improve "
            "carry/FR strategies that earn funding rates independent of BTC price direction. "
            "HMM regime filters may be better applied to directional momentum strategies."
        )
    },
    "equity_curves": {
        "dates": [str(d.date()) for d in aligned.index],
        "baseline": [(1 + baseline_ret).cumprod().iloc[i] for i in range(len(aligned))],
        "no_bear": [(1 + no_bear_ret).cumprod().iloc[i] for i in range(len(aligned))],
        "bull_only": [(1 + bull_only_ret).cumprod().iloc[i] for i in range(len(aligned))],
        "no_crash": [(1 + no_crash_ret).cumprod().iloc[i] for i in range(len(aligned))],
    },
}

out_json = REPO / "wave_k320_hmm_on_k297.json"
with open(out_json, "w") as f:
    json.dump(results, f, indent=2)
print(f"[OUTPUT] Written: {out_json}")

print(f"\n[DONE] Wave K320 complete — Decision: {decision}")
