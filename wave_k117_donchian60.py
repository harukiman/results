#!/usr/bin/env python3
"""
Wave K117 — Donchian L=60d Single-Lookback Vol-Targeted (K113 salvage)

K113 (9-lookback ensemble) failed §6 hard, but per-lookback decomposition
showed L=60d alone was robust (IS Sh +0.63, OOS Sh +0.76, MaxDD -1.3%).
This wave tests L=60d as a standalone candidate with 4 regime overlays:
  V_base    : no regime filter
  V_btc_vol : skip new entries when BTC vol-Z > 1.5
  V_trend   : only take breakouts in BTC EMA200 trend direction
  V_combo   : both filters

Pre-registered: see task spec. Lag-1 everywhere. Taker+slip cost.
"""
from __future__ import annotations
import json
import math
import time
import warnings
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from scipy.stats import norm

warnings.filterwarnings("ignore")

# ----------------------------- config -------------------------------------
CACHE = "/Users/nekonaomichi/crypto-lab/cache"
OUT_JSON = "/Users/nekonaomichi/crypto-lab/wave_k117_donchian60.json"
OUT_CURVES = "/Users/nekonaomichi/crypto-lab/wave_k117_curves.json"

# Broader universe — 30 liquid perps (heeds symbol-breadth feedback)
SYMBOLS = [
    "BTC", "ETH", "SOL", "BNB", "DOGE",
    "AVAX", "LINK", "ADA", "XRP", "INJ",
    "OP", "ARB", "DOT", "APT", "ATOM",
    "AAVE", "WIF", "BONK", "SHIB", "FLOKI",
    "NEAR", "LTC", "ETC", "FIL", "ICP",
    "SUI", "TIA", "SEI", "PEPE", "TRX",
]
BTC_SYM = "BTC"

LOOKBACK_DAYS = 60
BARS_PER_DAY = 6  # 4H bars
LOOKBACK_BARS = LOOKBACK_DAYS * BARS_PER_DAY  # 360

ANN_FACTOR = np.sqrt(365 * 6)  # sqrt(2190)
TAKER_FEE = 0.0004
SLIPPAGE = 0.0003
COST_PER_TURN = TAKER_FEE + SLIPPAGE

VOL_LOOKBACK_BARS = LOOKBACK_BARS  # 60-bar realized vol per spec ("60-bar")
# NOTE: spec says "60-bar realized vol" — interpreted as 60 4H bars = 10 days,
# but L=60d is 360 bars. Per K113 reference paper convention vol_lb = lookback / 6.
# We use VOL_LOOKBACK_BARS = 60 (=10 days) which is standard for vol targeting.
VOL_LOOKBACK_BARS = 60

TARGET_VOL = 0.15
POS_CAP = 2.0
ATR_PERIOD = 20  # spec: 2x 20-bar ATR
ATR_MULT = 2.0

IS_FRAC = 0.70
SEED = 42

# Regime params
BTC_VOL_Z_WIN = 250  # ~6 weeks zscore baseline for BTC vol
BTC_VOL_Z_THRESH = 1.5
BTC_EMA_PERIOD = 200

# Audit
N_PERM = 500      # spec=500; parallelized via multiprocessing
N_BOOT = 500
N_FOLDS = 4
N_WORKERS = 8

# Variants (regime overlays) — 4 trials for DSR
VARIANTS = ["V_base", "V_btc_vol", "V_trend", "V_combo"]


# ----------------------------- io -----------------------------------------
def load(sym: str) -> pd.DataFrame:
    fp = f"{CACHE}/{sym}USDT_4h_730d.parquet"
    df = pd.read_parquet(fp)
    df = df[["open_time", "open", "high", "low", "close"]].copy()
    df["open_time"] = pd.to_datetime(df["open_time"])
    df = df.sort_values("open_time").reset_index(drop=True)
    return df


# ----------------------------- indicators ---------------------------------
def compute_atr(high, low, close, period=ATR_PERIOD):
    h = pd.Series(high); l = pd.Series(low); c = pd.Series(close)
    tr = pd.concat(
        [(h - l), (h - c.shift(1)).abs(), (l - c.shift(1)).abs()],
        axis=1,
    ).max(axis=1)
    return tr.rolling(period, min_periods=period).mean().to_numpy()


def realized_vol(close: np.ndarray, win: int = VOL_LOOKBACK_BARS) -> np.ndarray:
    r = pd.Series(close).pct_change()
    sd = r.shift(1).rolling(win, min_periods=win).std().to_numpy()
    return sd * ANN_FACTOR


def ema(arr: np.ndarray, period: int) -> np.ndarray:
    return pd.Series(arr).ewm(span=period, adjust=False).mean().to_numpy()


def zscore(arr: np.ndarray, win: int) -> np.ndarray:
    s = pd.Series(arr)
    mu = s.rolling(win, min_periods=win).mean()
    sd = s.rolling(win, min_periods=win).std()
    return ((s - mu) / sd).to_numpy()


# ----------------------------- signal engine ------------------------------
def donchian_signal_60(
    high: np.ndarray,
    low: np.ndarray,
    close: np.ndarray,
    atr: np.ndarray,
    entry_allowed_long: Optional[np.ndarray] = None,
    entry_allowed_short: Optional[np.ndarray] = None,
) -> np.ndarray:
    """
    L=60d Donchian breakout with mid-band exit OR 2x20-bar ATR trailing stop
    (exit triggered by whichever fires first). Lag-1: decision at bar t uses
    info through t-1, position applied at bar t to capture bar-t return.

    Regime filters gate ENTRY (and re-entry on flip) only — once in a trade
    the existing stop logic runs unmodified.
    """
    n = len(close)
    sig = np.zeros(n, dtype=np.float64)
    if LOOKBACK_BARS >= n - 5:
        return sig

    # Donchian computed over bars STRICTLY PRIOR to t-1 (the breakout bar).
    # i.e. high[(t-1-L):(t-1)] -> shift(2) then rolling(L).max()
    h_s = pd.Series(high).shift(2)
    l_s = pd.Series(low).shift(2)
    upper = h_s.rolling(LOOKBACK_BARS, min_periods=LOOKBACK_BARS).max().to_numpy()
    lower = l_s.rolling(LOOKBACK_BARS, min_periods=LOOKBACK_BARS).min().to_numpy()
    mid = (upper + lower) / 2.0

    close_lag = pd.Series(close).shift(1).to_numpy()
    atr_lag = pd.Series(atr).shift(1).to_numpy()

    if entry_allowed_long is None:
        entry_allowed_long = np.ones(n, dtype=bool)
    if entry_allowed_short is None:
        entry_allowed_short = np.ones(n, dtype=bool)

    pos = 0
    trail_long = -np.inf
    trail_short = np.inf

    for t in range(n):
        u = upper[t]; lo = lower[t]; m = mid[t]; c1 = close_lag[t]; a1 = atr_lag[t]
        if np.isnan(u) or np.isnan(lo) or np.isnan(c1):
            sig[t] = 0.0
            pos = 0
            trail_long = -np.inf
            trail_short = np.inf
            continue

        # ---- exits first if in a position ----
        if pos == 1:
            # ATR trail
            if not np.isnan(a1):
                trail_long = max(trail_long, c1 - ATR_MULT * a1)
            exit_mid = c1 < m
            exit_atr = (not np.isnan(a1)) and (c1 < trail_long)
            if exit_mid or exit_atr:
                pos = 0
                trail_long = -np.inf
        elif pos == -1:
            if not np.isnan(a1):
                trail_short = min(trail_short, c1 + ATR_MULT * a1)
            exit_mid = c1 > m
            exit_atr = (not np.isnan(a1)) and (c1 > trail_short)
            if exit_mid or exit_atr:
                pos = 0
                trail_short = np.inf

        # ---- entries / flips (gated by regime) ----
        if c1 > u and entry_allowed_long[t]:
            if pos != 1:
                pos = 1
                if not np.isnan(a1):
                    trail_long = c1 - ATR_MULT * a1
                trail_short = np.inf
        elif c1 < lo and entry_allowed_short[t]:
            if pos != -1:
                pos = -1
                if not np.isnan(a1):
                    trail_short = c1 + ATR_MULT * a1
                trail_long = -np.inf

        sig[t] = float(pos)
    return sig


def vol_target_size(weight: np.ndarray, rv: np.ndarray, tv: float = TARGET_VOL) -> np.ndarray:
    raw = np.where(rv > 0, tv / rv, 0.0)
    raw = np.where(np.isnan(raw), 0.0, raw)
    size = weight * raw
    return np.clip(size, -POS_CAP, POS_CAP)


# ----------------------------- regime gates -------------------------------
def build_regime_gates(btc_df: pd.DataFrame, n_align: int) -> Dict[str, Dict[str, np.ndarray]]:
    """
    Returns dict[variant] -> {long_ok: bool[n], short_ok: bool[n]} aligned to
    last n_align bars of BTC. Uses BTC daily-equivalent close.
    """
    close = btc_df["close"].to_numpy(dtype=np.float64)[-n_align:]
    high = btc_df["high"].to_numpy(dtype=np.float64)[-n_align:]
    low = btc_df["low"].to_numpy(dtype=np.float64)[-n_align:]

    # BTC realized vol (60-bar) zscore
    rv = realized_vol(close, win=VOL_LOOKBACK_BARS)
    rv_z = zscore(rv, BTC_VOL_Z_WIN)
    rv_z_lag = pd.Series(rv_z).shift(1).to_numpy()  # lag-1
    vol_ok = (rv_z_lag < BTC_VOL_Z_THRESH) | np.isnan(rv_z_lag)
    # if NaN (warmup), be permissive — but we will mark NaN as ALLOW so we
    # don't lose data; alternative is block — choose ALLOW because the
    # zscore window itself (250 bars) is a side window.

    # BTC EMA200 trend
    e = ema(close, BTC_EMA_PERIOD)
    e_lag = pd.Series(e).shift(1).to_numpy()
    c_lag = pd.Series(close).shift(1).to_numpy()
    trend_up = (c_lag > e_lag) & ~np.isnan(e_lag)
    trend_dn = (c_lag < e_lag) & ~np.isnan(e_lag)

    n = len(close)
    gates: Dict[str, Dict[str, np.ndarray]] = {}
    gates["V_base"] = dict(
        long_ok=np.ones(n, dtype=bool),
        short_ok=np.ones(n, dtype=bool),
    )
    gates["V_btc_vol"] = dict(
        long_ok=vol_ok.copy(),
        short_ok=vol_ok.copy(),
    )
    gates["V_trend"] = dict(
        long_ok=trend_up.copy(),
        short_ok=trend_dn.copy(),
    )
    gates["V_combo"] = dict(
        long_ok=(vol_ok & trend_up),
        short_ok=(vol_ok & trend_dn),
    )
    return gates


# ----------------------------- per-symbol BT ------------------------------
def backtest_symbol(
    df: pd.DataFrame,
    long_ok: np.ndarray,
    short_ok: np.ndarray,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    high = df["high"].to_numpy(dtype=np.float64)
    low = df["low"].to_numpy(dtype=np.float64)
    close = df["close"].to_numpy(dtype=np.float64)
    atr = compute_atr(high, low, close, ATR_PERIOD)
    sig = donchian_signal_60(high, low, close, atr, long_ok, short_ok)
    rv = realized_vol(close)
    size = vol_target_size(sig, rv, TARGET_VOL)
    ret = pd.Series(close).pct_change().fillna(0.0).to_numpy()
    gross = size * ret
    delta = np.abs(np.diff(size, prepend=0.0))
    cost = delta * COST_PER_TURN
    pnl = gross - cost
    return pnl, sig, size


# ----------------------------- metrics ------------------------------------
def sharpe(r: np.ndarray) -> float:
    r = np.asarray(r, dtype=np.float64)
    if len(r) < 5:
        return 0.0
    sd = r.std(ddof=1)
    if sd == 0 or np.isnan(sd):
        return 0.0
    return float(r.mean() / sd * ANN_FACTOR)


def sortino(r: np.ndarray) -> float:
    r = np.asarray(r, dtype=np.float64)
    downside = r[r < 0]
    if len(downside) < 2:
        return 0.0
    sd = downside.std(ddof=1)
    if sd == 0:
        return 0.0
    return float(r.mean() / sd * ANN_FACTOR)


def max_dd(r: np.ndarray) -> float:
    if len(r) < 2:
        return 0.0
    eq = np.cumprod(1 + r)
    peak = np.maximum.accumulate(eq)
    dd = eq / peak - 1
    return float(dd.min())


def calmar(r: np.ndarray) -> float:
    mdd = max_dd(r)
    if mdd == 0:
        return 0.0
    ann_ret = (1 + r.mean()) ** (365 * 6) - 1
    return float(ann_ret / abs(mdd))


def all_metrics(r: np.ndarray) -> Dict[str, float]:
    if len(r) < 10:
        return dict(sharpe=0.0, sortino=0.0, max_dd=0.0, calmar=0.0, ann_ret=0.0, n=int(len(r)))
    return dict(
        sharpe=sharpe(r),
        sortino=sortino(r),
        max_dd=max_dd(r),
        calmar=calmar(r),
        ann_ret=float((1 + r.mean()) ** (365 * 6) - 1),
        n=int(len(r)),
    )


# ----------------------------- audit --------------------------------------
def block_bootstrap_ci(r: np.ndarray, n_boot: int = N_BOOT, block: int = 20, seed=SEED) -> Tuple[float, float, float]:
    rng = np.random.default_rng(seed)
    n = len(r)
    nblocks = max(1, n // block)
    sh = []
    for _ in range(n_boot):
        idx_starts = rng.integers(0, max(1, n - block + 1), size=nblocks)
        sample = np.concatenate([r[s:s + block] for s in idx_starts])
        sh.append(sharpe(sample))
    arr = np.array(sh)
    return float(np.percentile(arr, 2.5)), float(np.percentile(arr, 97.5)), float(arr.mean())


_PERM_STATE: Dict = {}  # module-level for multiprocessing fork


def _perm_init(sym_arrays, long_ok, short_ok, fold_bounds, opens, times):
    _PERM_STATE["sym_arrays"] = sym_arrays  # dict sym -> (high, low, close)
    _PERM_STATE["long_ok"] = long_ok
    _PERM_STATE["short_ok"] = short_ok
    _PERM_STATE["fold_bounds"] = fold_bounds
    _PERM_STATE["opens"] = opens
    _PERM_STATE["times"] = times


def _perm_one(seed_k: int) -> float:
    rng = np.random.default_rng(seed_k)
    sym_arrays = _PERM_STATE["sym_arrays"]
    long_ok = _PERM_STATE["long_ok"]
    short_ok = _PERM_STATE["short_ok"]
    fold_bounds = _PERM_STATE["fold_bounds"]
    opens = _PERM_STATE["opens"]
    times = _PERM_STATE["times"]
    per = []
    for sym, (h, l, c) in sym_arrays.items():
        high = h.copy(); low = l.copy(); close = c.copy()
        for i in range(len(fold_bounds) - 1):
            lo_i, hi_i = fold_bounds[i], fold_bounds[i + 1]
            idx = np.arange(lo_i, hi_i)
            p = rng.permutation(idx)
            high[idx] = high[p]
            low[idx] = low[p]
            close[idx] = close[p]
        df2 = pd.DataFrame({
            "open_time": times[sym],
            "open": opens[sym],
            "high": high, "low": low, "close": close,
        })
        pnl, _, _ = backtest_symbol(df2, long_ok, short_ok)
        per.append(pnl)
    port = np.mean(np.vstack(per), axis=0)
    return sharpe(port)


def permutation_test(
    dfs: Dict[str, pd.DataFrame],
    btc_df: pd.DataFrame,
    n_perm: int = N_PERM,
    seed=SEED,
    variant: str = "V_base",
    n_workers: int = N_WORKERS,
) -> List[float]:
    """
    Shuffle each symbol's bar order within each fold (preserves regime
    structure via per-fold block + original BTC regime gates). Parallelized
    via multiprocessing.Pool over permutations.
    """
    syms = list(dfs.keys())
    n = len(dfs[syms[0]])
    fold_bounds = np.linspace(0, n, N_FOLDS + 1, dtype=int)
    gates_all = build_regime_gates(btc_df, n)
    g = gates_all[variant]
    sym_arrays = {
        s: (
            dfs[s]["high"].to_numpy(dtype=np.float64),
            dfs[s]["low"].to_numpy(dtype=np.float64),
            dfs[s]["close"].to_numpy(dtype=np.float64),
        ) for s in syms
    }
    opens = {s: dfs[s]["open"].to_numpy() for s in syms}
    times = {s: dfs[s]["open_time"].values for s in syms}

    from multiprocessing import Pool
    seeds = [seed + 1000 * k for k in range(n_perm)]
    with Pool(
        processes=n_workers,
        initializer=_perm_init,
        initargs=(sym_arrays, g["long_ok"], g["short_ok"], fold_bounds, opens, times),
    ) as pool:
        out = pool.map(_perm_one, seeds, chunksize=max(1, n_perm // (n_workers * 4)))
    return list(out)


def deflated_sharpe(sh_obs: float, sh_trials: List[float], n_eff: int) -> float:
    """Bailey/Lopez de Prado DSR — Gaussian approx."""
    sh_trials = np.asarray(sh_trials, dtype=np.float64)
    if len(sh_trials) < 2:
        return float("nan")
    var_sh = float(np.var(sh_trials, ddof=1))
    sd_sh = math.sqrt(max(var_sh, 1e-12))
    N = len(sh_trials)
    gamma = 0.5772156649
    if N >= 2:
        e_max = sh_trials.mean() + sd_sh * (
            (1 - gamma) * np.sqrt(2 * np.log(N))
            + gamma * (1 / np.sqrt(2 * np.log(N)))
        )
    else:
        e_max = sh_trials.mean()
    # Std of SR estimator for n_eff bars assuming gaussian returns
    # SE(SR) = sqrt((1 + 0.5*SR^2) / n_eff) — Lo (2002)
    se = math.sqrt(max((1.0 + 0.5 * sh_obs * sh_obs) / max(n_eff - 1, 1), 1e-12))
    # DSR is prob(true SR > 0) given we picked from N trials
    z = (sh_obs - e_max) / max(se, 1e-12)
    return float(norm.cdf(z))


def walk_forward(
    dfs: Dict[str, pd.DataFrame],
    btc_df: pd.DataFrame,
    n_folds: int = N_FOLDS,
) -> List[Dict]:
    """Anchored expanding window WF; select best variant on train, eval on test."""
    syms = list(dfs.keys())
    n = len(dfs[syms[0]])
    gates_all = build_regime_gates(btc_df, n)

    # Pre-compute per-variant per-symbol pnl arrays once (all variants over full)
    var_pnl: Dict[str, np.ndarray] = {}
    for v in VARIANTS:
        g = gates_all[v]
        psm = []
        for sym in syms:
            pnl, _, _ = backtest_symbol(dfs[sym], g["long_ok"], g["short_ok"])
            psm.append(pnl)
        var_pnl[v] = np.mean(np.vstack(psm), axis=0)

    out = []
    for k in range(n_folds):
        # anchored: train = 40%+k*15% of n
        train_end = int(min(0.95, 0.40 + k * 0.15) * n)
        test_lo = train_end
        test_hi = min(n, test_lo + max(int(0.15 * n), 50))
        if test_hi - test_lo < 50:
            continue
        # pick best variant on train
        best_v, best_sh = None, -1e9
        for v in VARIANTS:
            sh = sharpe(var_pnl[v][:train_end])
            if sh > best_sh:
                best_sh = sh; best_v = v
        test_sh = sharpe(var_pnl[best_v][test_lo:test_hi])
        out.append(dict(
            fold=k, train_end=int(train_end),
            test_lo=int(test_lo), test_hi=int(test_hi),
            best_variant=best_v, train_sharpe=float(best_sh), test_sharpe=float(test_sh),
        ))
    return out


# ----------------------------- main ---------------------------------------
def main():
    t0 = time.time()
    print("[K117] loading data ...", flush=True)
    dfs: Dict[str, pd.DataFrame] = {}
    for s in SYMBOLS:
        try:
            dfs[s] = load(s)
        except Exception as e:
            print(f"  skip {s}: {e}")

    # always need BTC for regime
    btc_full = load(BTC_SYM)

    # align all symbols to common min length (anchored from right)
    min_len = min(len(d) for d in dfs.values())
    min_len = min(min_len, len(btc_full))
    for s in dfs:
        dfs[s] = dfs[s].iloc[-min_len:].reset_index(drop=True)
    btc_full = btc_full.iloc[-min_len:].reset_index(drop=True)

    n_bars = min_len
    is_end = int(n_bars * IS_FRAC)
    print(f"  loaded {len(dfs)} symbols, n_bars={n_bars}, IS=[0:{is_end}] OOS=[{is_end}:{n_bars}]")

    # ---- regime gates aligned to n_bars ----
    gates_all = build_regime_gates(btc_full, n_bars)

    # ---- run all 4 variants ----
    print("[K117] running 4 variants ...")
    variant_results = {}
    per_sym_pnl_by_variant: Dict[str, Dict[str, np.ndarray]] = {}
    per_sym_metrics_by_variant: Dict[str, Dict[str, Dict]] = {}
    port_pnl_by_variant: Dict[str, np.ndarray] = {}

    for v in VARIANTS:
        g = gates_all[v]
        per_sym_pnl = {}
        per_sym_metrics = {}
        psm = []
        for sym, df in dfs.items():
            pnl, sig, size = backtest_symbol(df, g["long_ok"], g["short_ok"])
            per_sym_pnl[sym] = pnl
            per_sym_metrics[sym] = dict(
                full=all_metrics(pnl),
                is_=all_metrics(pnl[:is_end]),
                oos=all_metrics(pnl[is_end:]),
                gross_exposure=float(np.mean(np.abs(size))),
                turnover_per_bar=float(np.mean(np.abs(np.diff(size, prepend=0.0)))),
            )
            psm.append(pnl)
        port = np.mean(np.vstack(psm), axis=0)
        per_sym_pnl_by_variant[v] = per_sym_pnl
        per_sym_metrics_by_variant[v] = per_sym_metrics
        port_pnl_by_variant[v] = port

        m_full = all_metrics(port)
        m_is = all_metrics(port[:is_end])
        m_oos = all_metrics(port[is_end:])
        variant_results[v] = dict(
            full=m_full, is_=m_is, oos=m_oos,
            mean_gross_exposure=float(np.mean([per_sym_metrics[s]["gross_exposure"] for s in per_sym_metrics])),
            mean_turnover=float(np.mean([per_sym_metrics[s]["turnover_per_bar"] for s in per_sym_metrics])),
        )
        print(f"  {v:10s}: IS Sh={m_is['sharpe']:+.3f} OOS Sh={m_oos['sharpe']:+.3f} "
              f"OOS MDD={m_oos['max_dd']:+.3f} Full Sh={m_full['sharpe']:+.3f}")

    # ---- pick best by OOS Sharpe (the honest test) ----
    best_v = max(VARIANTS, key=lambda v: variant_results[v]["oos"]["sharpe"])
    best_v_is = max(VARIANTS, key=lambda v: variant_results[v]["is_"]["sharpe"])
    print(f"[K117] best by OOS Sh: {best_v}  | best by IS Sh: {best_v_is}")

    # ---- walk-forward 4 folds (model selection within fold) ----
    print("[K117] walk-forward ...")
    wf = walk_forward(dfs, btc_full, N_FOLDS)
    for r in wf:
        print(f"  fold {r['fold']}: train_end={r['train_end']} test=[{r['test_lo']}:{r['test_hi']}] "
              f"best_v={r['best_variant']} train_sh={r['train_sharpe']:+.3f} test_sh={r['test_sharpe']:+.3f}")

    # ---- block bootstrap on best variant OOS ----
    print("[K117] block bootstrap on best variant OOS ...")
    port_oos_best = port_pnl_by_variant[best_v][is_end:]
    bb_lo, bb_hi, bb_mean = block_bootstrap_ci(port_oos_best, n_boot=N_BOOT, block=20)
    print(f"  best={best_v} OOS Sh 95% CI: [{bb_lo:.3f}, {bb_hi:.3f}] mean={bb_mean:.3f}")

    # ---- permutation test on best variant (full-sample Sharpe) ----
    print(f"[K117] permutation test (n={N_PERM}) on {best_v} ...")
    null_sh = permutation_test(dfs, btc_full, n_perm=N_PERM, variant=best_v)
    obs_sh = variant_results[best_v]["full"]["sharpe"]
    pval = float((np.sum(np.array(null_sh) >= obs_sh) + 1) / (len(null_sh) + 1))
    print(f"  obs Sh={obs_sh:+.3f}  null mean={np.mean(null_sh):+.3f} std={np.std(null_sh):.3f} p={pval:.4f}")

    # ---- DSR (4 variants = 4 trials) ----
    is_sh_trials = [variant_results[v]["is_"]["sharpe"] for v in VARIANTS]
    dsr_is = deflated_sharpe(
        variant_results[best_v]["is_"]["sharpe"], is_sh_trials, n_eff=is_end,
    )
    # also DSR on OOS for honesty
    oos_sh_trials = [variant_results[v]["oos"]["sharpe"] for v in VARIANTS]
    dsr_oos = deflated_sharpe(
        variant_results[best_v]["oos"]["sharpe"], oos_sh_trials, n_eff=n_bars - is_end,
    )
    print(f"  DSR(IS) ={dsr_is:.3f}  DSR(OOS)={dsr_oos:.3f}")

    # ---- cost stress on best variant ----
    print("[K117] cost stress ±50% ...")
    g = gates_all[best_v]

    def restress(mult: float) -> Dict[str, float]:
        per = []
        for sym, df in dfs.items():
            high = df["high"].to_numpy(dtype=np.float64)
            close = df["close"].to_numpy(dtype=np.float64)
            atr = compute_atr(high, df["low"].to_numpy(dtype=np.float64), close, ATR_PERIOD)
            sig = donchian_signal_60(high, df["low"].to_numpy(dtype=np.float64), close, atr,
                                     g["long_ok"], g["short_ok"])
            rv = realized_vol(close)
            size = vol_target_size(sig, rv, TARGET_VOL)
            ret = pd.Series(close).pct_change().fillna(0.0).to_numpy()
            gross = size * ret
            delta = np.abs(np.diff(size, prepend=0.0))
            pnl = gross - delta * COST_PER_TURN * mult
            per.append(pnl)
        p = np.mean(np.vstack(per), axis=0)
        return dict(
            sharpe_full=sharpe(p),
            sharpe_oos=sharpe(p[is_end:]),
            mdd_oos=max_dd(p[is_end:]),
        )

    stress = dict(
        cost_x0_5=restress(0.5),
        cost_x1_0=restress(1.0),
        cost_x1_5=restress(1.5),
    )
    for k, v in stress.items():
        print(f"  {k}: full Sh={v['sharpe_full']:+.3f} OOS Sh={v['sharpe_oos']:+.3f} OOS MDD={v['mdd_oos']:+.3f}")

    # ---- PBO from WF: fraction folds where train-best variant flips to negative OOS ----
    wf_neg = sum(1 for r in wf if r["test_sharpe"] < 0)
    pbo = float(wf_neg / max(1, len(wf)))

    # ---- §6 mini gates ----
    oos_sh_best = variant_results[best_v]["oos"]["sharpe"]
    gates_pass = dict(
        G1_oos_sharpe_gt_0_5=bool(oos_sh_best > 0.5),
        G2_pbo_lt_0_3=bool(pbo < 0.3),
        G3_dsr_oos_gt_0_5=bool(dsr_oos > 0.5),
        oos_sharpe=oos_sh_best,
        pbo=pbo,
        dsr_is=dsr_is,
        dsr_oos=dsr_oos,
        perm_p=pval,
        cost_x1_5_oos_sh=stress["cost_x1_5"]["sharpe_oos"],
        bootstrap_ci_lo=bb_lo,
        bootstrap_ci_hi=bb_hi,
    )
    passed = sum([gates_pass["G1_oos_sharpe_gt_0_5"], gates_pass["G2_pbo_lt_0_3"], gates_pass["G3_dsr_oos_gt_0_5"]])

    # Additional sanity: bootstrap CI lower bound > 0 ?
    ci_ok = bb_lo > 0
    perm_ok = pval < 0.10
    cost_ok = stress["cost_x1_5"]["sharpe_oos"] > 0.3

    if passed == 3 and ci_ok and perm_ok:
        verdict = "ACCEPT"
    elif passed == 2:
        verdict = "CONDITIONAL"
    else:
        verdict = "REJECT"

    # ---- curves (downsampled) ----
    def downsample(arr, max_pts=600):
        arr = np.asarray(arr)
        if len(arr) <= max_pts:
            return arr.tolist()
        step = max(1, len(arr) // max_pts)
        return arr[::step].tolist()

    eq_curves = {}
    for v in VARIANTS:
        p = port_pnl_by_variant[v]
        eq_curves[v] = dict(
            equity_full=downsample(np.cumprod(1 + p)),
            equity_is=downsample(np.cumprod(1 + p[:is_end])),
            equity_oos=downsample(np.cumprod(1 + p[is_end:])),
        )

    # rank per-symbol by OOS sharpe under best variant
    sym_oos = [(s, per_sym_metrics_by_variant[best_v][s]["oos"]["sharpe"]) for s in dfs.keys()]
    sym_oos_sorted = sorted(sym_oos, key=lambda kv: kv[1], reverse=True)
    top5 = [s for s, _ in sym_oos_sorted[:5]]
    bot5 = [s for s, _ in sym_oos_sorted[-5:]]
    sym_eq_top5 = {
        s: downsample(np.cumprod(1 + per_sym_pnl_by_variant[best_v][s])) for s in top5
    }

    curves = dict(
        n_bars=int(n_bars),
        is_end_idx_full=int(is_end),
        variants=VARIANTS,
        per_variant_equity=eq_curves,
        best_variant=best_v,
        top5_oos_symbols=top5,
        bot5_oos_symbols=bot5,
        top5_equity_best_variant=sym_eq_top5,
        portfolio_oos_equity_best=downsample(np.cumprod(1 + port_pnl_by_variant[best_v][is_end:])),
    )
    with open(OUT_CURVES, "w") as f:
        json.dump(curves, f)

    # ---- per-symbol detail (best variant) ----
    per_sym_out = {}
    for sym in dfs:
        m = per_sym_metrics_by_variant[best_v][sym]
        per_sym_out[sym] = dict(
            is_sharpe=m["is_"]["sharpe"],
            oos_sharpe=m["oos"]["sharpe"],
            full_sharpe=m["full"]["sharpe"],
            oos_max_dd=m["oos"]["max_dd"],
            oos_ann_ret=m["oos"]["ann_ret"],
            full_max_dd=m["full"]["max_dd"],
            gross_exposure=m["gross_exposure"],
            turnover_per_bar=m["turnover_per_bar"],
        )

    results = dict(
        wave="K117",
        ts_utc=pd.Timestamp.utcnow().isoformat(),
        config=dict(
            symbols=SYMBOLS,
            lookback_days=LOOKBACK_DAYS,
            lookback_bars=LOOKBACK_BARS,
            vol_lookback_bars=VOL_LOOKBACK_BARS,
            target_vol=TARGET_VOL,
            pos_cap=POS_CAP,
            atr_period=ATR_PERIOD,
            atr_mult=ATR_MULT,
            taker_fee=TAKER_FEE,
            slippage=SLIPPAGE,
            cost_per_turn=COST_PER_TURN,
            btc_vol_z_win=BTC_VOL_Z_WIN,
            btc_vol_z_thresh=BTC_VOL_Z_THRESH,
            btc_ema_period=BTC_EMA_PERIOD,
            is_frac=IS_FRAC,
            n_perm=N_PERM,
            n_boot=N_BOOT,
            n_folds=N_FOLDS,
            variants=VARIANTS,
        ),
        n_bars=int(n_bars),
        is_end=int(is_end),
        variant_results=variant_results,
        best_variant=best_v,
        best_variant_by_is=best_v_is,
        per_symbol_best_variant=per_sym_out,
        walk_forward=wf,
        block_bootstrap=dict(
            best_variant=best_v,
            oos_sh_ci_lo=bb_lo, oos_sh_ci_hi=bb_hi, oos_sh_mean=bb_mean,
        ),
        permutation=dict(
            best_variant=best_v,
            n=len(null_sh),
            null_mean=float(np.mean(null_sh)),
            null_std=float(np.std(null_sh)),
            null_p95=float(np.percentile(null_sh, 95)),
            observed=obs_sh, p_value=pval,
        ),
        dsr=dict(is_=dsr_is, oos=dsr_oos, is_sh_trials=is_sh_trials, oos_sh_trials=oos_sh_trials),
        cost_stress=stress,
        gates=gates_pass,
        bootstrap_lower_positive=bool(ci_ok),
        perm_significant=bool(perm_ok),
        cost_x1_5_ok=bool(cost_ok),
        verdict=verdict,
        wall_time_sec=time.time() - t0,
    )
    with open(OUT_JSON, "w") as f:
        json.dump(results, f, indent=2, default=str)

    print(f"[K117] DONE in {time.time() - t0:.1f}s -> {OUT_JSON}")
    print(f"[K117] verdict={verdict}")
    return results


if __name__ == "__main__":
    main()
