"""
Wave K159 — Cross-Exchange FR Spread Arb Signal (R6-15)
=======================================================
Hypothesis
  When MEXC funding rate diverges from Binance/Bybit by >2-3% annualized on
  alt-coin perps, the LAGGING venue tends to converge toward the others.
  Use the spread as a DIRECTIONAL BIAS signal on the venue we already trade
  (Bybit — that's where our existing infra is). NOT a capital-arbitrage idea
  (which would need cross-margin between exchanges); this is a price-prediction
  read on Bybit perps using cross-exchange FR information.

Data
  Bybit FR  : local cache  (bybit_fr_<sym>USDT_730d.parquet) — 730d
  Binance FR: free REST    (https://fapi.binance.com/fapi/v1/fundingRate)
              paginated by startTime, 1000-rec chunks
  MEXC FR   : free REST    (https://contract.mexc.com/api/v1/contract/funding_rate/history)
              paginated by page_num/page_size; oldest ~Dec 2024 → < 730d
  Bybit Px  : local 4h kline cache → resampled to FR-event grid (ffill)

Symbols (top liquid majors)
  BTC, ETH, SOL, BNB, DOGE, AVAX, LINK

Pre-registered method (per 8h funding event per symbol)
  1. Build synchronised triple (bybit_fr, binance_fr, mexc_fr) at Bybit FR ts
  2. spread_bm = bybit_fr − mexc_fr
     spread_bb = binance_fr − bybit_fr
  3. Threshold (per-event):
        2% annualised  = 0.02 / (365*3) ≈ 1.826e-5
        3% annualised  ≈ 2.740e-5
     NB: spec said 6.85e-5 for "2% per 8h" — that's "2% per year ÷ 3 events
     ÷ 365 = 1.826e-5" — closer; the spec figure 6.85e-5 corresponds to
     roughly 7.5% annualised. We compute BOTH 2% and 3% variants AND a
     z-score variant for robustness, and report ALL.
  4. Signal: bybit lags ⇒ bybit FR will converge toward the OTHER exchange.
        Spec rule:
          if bybit_fr > mexc_fr + thr   → bybit "too high" → short Bybit
          if bybit_fr < mexc_fr − thr   → bybit "too low"  → long Bybit
        Same logic for spread_bb (bybit vs binance), where binance is the
        anchor. We trade Bybit perp.
  5. Position: open at funding ts, hold until spread narrows (sign flip or
        |spread|<thr/2) OR 1 funding event max (8h). We use a SIMPLE 1-event
        hold for pre-registration cleanliness — captures the immediate
        convergence and limits look-ahead.
  6. Costs: 0.07 % per side per leg (one leg only — Bybit perp).

Variants
  V_bm_2pct : trade on |bybit-mexc|     > 2 % annualised
  V_bm_3pct : trade on |bybit-mexc|     > 3 % annualised
  V_bb_2pct : trade on |binance-bybit|  > 2 % annualised
  V_bb_3pct : trade on |binance-bybit|  > 3 % annualised
  V_combo_z : trade when combined z-score |z| > 2  (using 60-event rolling)

Backtest stats
  Honest 730d / 70-30 IS-OOS (subject to overlap window between exchanges)
  Walk-forward 4-fold
  Permutation n=200 (shuffle signal sign per event)
  Block bootstrap n=200 on OOS Sharpe
  Deflated Sharpe with N_trials = 5
  Cost stress ±50 %
"""

import json
import time
import urllib.request
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

warnings.filterwarnings("ignore")

ROOT = Path("/Users/nekonaomichi/crypto-lab")
CACHE = ROOT / "cache"
FETCH_DIR = ROOT / "cache" / "xex_fr"
FETCH_DIR.mkdir(parents=True, exist_ok=True)

SYMBOLS = ["BTC", "ETH", "SOL", "BNB", "DOGE", "AVAX", "LINK"]

COST_BPS = 7.0
IS_FRAC = 0.70
SEED = 20260524
N_TRIALS_DSR = 5
N_PERM = 200
N_BOOT = 200

# Annualised → per-8h conversion (3 events / day × 365)
ANN_PER_EVENT = 1.0 / (365.0 * 3.0)
THR_2PCT_ANN = 0.02 * ANN_PER_EVENT   # ≈ 1.826e-5
THR_3PCT_ANN = 0.03 * ANN_PER_EVENT   # ≈ 2.740e-5

ANN_FACTOR_8H = np.sqrt(365.0 * 3.0)   # 8h returns → annual SR

PX_FILE_OVERRIDES = {
    "BONK": "BONKUSDT_4h_730d.parquet",
}


# --------------------------------------------------------------------- I/O bybit
def load_bybit_fr(sym):
    p = CACHE / f"bybit_fr_{sym}USDT_730d.parquet"
    if not p.exists():
        return None
    df = pd.read_parquet(p)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.set_index("timestamp").sort_index()
    df = df[~df.index.duplicated(keep="last")]
    return df["funding_rate"].astype(float).rename("bybit")


def load_bybit_px(sym):
    fname = PX_FILE_OVERRIDES.get(sym, f"{sym}USDT_4h_730d.parquet")
    p = CACHE / fname
    if not p.exists():
        return None
    df = pd.read_parquet(p)
    df["open_time"] = pd.to_datetime(df["open_time"])
    df = df.set_index("open_time").sort_index()
    df = df[~df.index.duplicated(keep="last")]
    return df["close"].astype(float).rename(sym)


# --------------------------------------------------------------------- I/O binance
def fetch_binance_fr(sym, days=730, sleep=0.20):
    """Returns Series of FR indexed by ts (ms)."""
    cache_path = FETCH_DIR / f"binance_fr_{sym}USDT_{days}d.parquet"
    if cache_path.exists():
        df = pd.read_parquet(cache_path)
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df = df.set_index("timestamp").sort_index()
        return df["funding_rate"].astype(float).rename("binance")

    end_ms = int(time.time() * 1000)
    start_ms = end_ms - days * 86400 * 1000
    base = "https://fapi.binance.com/fapi/v1/fundingRate"
    out = []
    cursor = start_ms
    n_iter = 0
    while cursor < end_ms and n_iter < 50:
        url = f"{base}?symbol={sym}USDT&startTime={cursor}&limit=1000"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "k159-research"})
            data = json.loads(urllib.request.urlopen(req, timeout=15).read())
        except Exception as e:
            print(f"     binance fetch err {sym} iter={n_iter}: {e}")
            break
        if not data:
            break
        out.extend(data)
        last_ts = data[-1]["fundingTime"]
        if last_ts <= cursor:
            break
        cursor = last_ts + 1
        n_iter += 1
        time.sleep(sleep)

    if not out:
        return None
    df = pd.DataFrame(out)
    df["timestamp"] = pd.to_datetime(df["fundingTime"], unit="ms")
    df["funding_rate"] = df["fundingRate"].astype(float)
    df = df[["timestamp", "funding_rate"]].drop_duplicates("timestamp").sort_values("timestamp")
    df.to_parquet(cache_path, index=False)
    return df.set_index("timestamp")["funding_rate"].astype(float).rename("binance")


# --------------------------------------------------------------------- I/O mexc
def fetch_mexc_fr(sym, sleep=0.25):
    """MEXC paginates page_num/page_size; oldest page = highest page_num."""
    cache_path = FETCH_DIR / f"mexc_fr_{sym}_USDT_full.parquet"
    if cache_path.exists():
        df = pd.read_parquet(cache_path)
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df = df.set_index("timestamp").sort_index()
        return df["funding_rate"].astype(float).rename("mexc")

    base = "https://contract.mexc.com/api/v1/contract/funding_rate/history"
    sym_m = f"{sym}_USDT"
    # First request to get totalPage
    page_size = 100
    out = []
    try:
        req = urllib.request.Request(
            f"{base}?symbol={sym_m}&page_num=1&page_size={page_size}",
            headers={"User-Agent": "k159-research"},
        )
        first = json.loads(urllib.request.urlopen(req, timeout=15).read())
    except Exception as e:
        print(f"     mexc first-page err {sym}: {e}")
        return None
    if not first.get("success"):
        return None
    total_pages = first["data"]["totalPage"]
    out.extend(first["data"]["resultList"])
    for pg in range(2, total_pages + 1):
        try:
            req = urllib.request.Request(
                f"{base}?symbol={sym_m}&page_num={pg}&page_size={page_size}",
                headers={"User-Agent": "k159-research"},
            )
            data = json.loads(urllib.request.urlopen(req, timeout=15).read())
            out.extend(data["data"]["resultList"])
        except Exception as e:
            print(f"     mexc page={pg} err {sym}: {e}")
            break
        time.sleep(sleep)

    if not out:
        return None
    df = pd.DataFrame(out)
    df["timestamp"] = pd.to_datetime(df["settleTime"], unit="ms")
    df["funding_rate"] = df["fundingRate"].astype(float)
    df = df[["timestamp", "funding_rate"]].drop_duplicates("timestamp").sort_values("timestamp")
    df.to_parquet(cache_path, index=False)
    return df.set_index("timestamp")["funding_rate"].astype(float).rename("mexc")


# --------------------------------------------------------------------- panels
def round_to_8h(idx):
    """Snap a DatetimeIndex to nearest 8h boundary for sync between venues."""
    return pd.to_datetime(idx).round("8H")


def build_triplet_panel():
    """Return dict[sym] = (df with cols bybit, binance, mexc, px) on Bybit FR grid."""
    panels = {}
    data_avail = {}
    for sym in SYMBOLS:
        print(f"  {sym}: bybit cache ... ", end="")
        b = load_bybit_fr(sym)
        if b is None or b.empty:
            print("MISSING")
            data_avail[sym] = {"bybit_n": 0, "binance_n": 0, "mexc_n": 0, "overlap_n": 0}
            continue
        print(f"{len(b)} ev | binance fetch ... ", end="", flush=True)
        n = fetch_binance_fr(sym)
        if n is None:
            print("MISSING | ", end="")
            n = pd.Series(dtype=float, name="binance")
        else:
            print(f"{len(n)} ev | ", end="")
        print(f"mexc fetch ... ", end="", flush=True)
        m = fetch_mexc_fr(sym)
        if m is None:
            print("MISSING")
            m = pd.Series(dtype=float, name="mexc")
        else:
            print(f"{len(m)} ev")

        # Snap each to 8h grid
        b.index = round_to_8h(b.index)
        if not n.empty:
            n.index = round_to_8h(n.index)
        if not m.empty:
            m.index = round_to_8h(m.index)

        b = b[~b.index.duplicated(keep="last")]
        n = n[~n.index.duplicated(keep="last")] if not n.empty else n
        m = m[~m.index.duplicated(keep="last")] if not m.empty else m

        # Concat and align on union of triple ts
        df = pd.concat([b, n, m], axis=1).sort_index()

        # Price (Bybit) on FR grid
        px = load_bybit_px(sym)
        if px is None:
            print(f"     {sym}: no price cache, skipping")
            data_avail[sym] = {"bybit_n": int(len(b)), "binance_n": int(len(n)),
                               "mexc_n": int(len(m)), "overlap_n": 0,
                               "skipped_reason": "no_price"}
            continue
        px_at = px.reindex(df.index, method="ffill").rename("px")
        df["px"] = px_at

        # Trading row: need bybit fr + px and at least ONE of (binance, mexc)
        df = df.dropna(subset=["bybit", "px"])
        df = df[~(df["binance"].isna() & df["mexc"].isna())]

        panels[sym] = df
        data_avail[sym] = {
            "bybit_n": int(len(b)),
            "binance_n": int(len(n)),
            "mexc_n": int(len(m)),
            "overlap_n": int(len(df)),
            "overlap_start": str(df.index.min()) if len(df) else None,
            "overlap_end":   str(df.index.max()) if len(df) else None,
        }

    return panels, data_avail


# --------------------------------------------------------------------- signal logic
def signal_threshold_pair(panel, anchor_col, thr, mode="bm"):
    """
    Per-event signal:
      mode bm: bybit - mexc;     anchor_col = 'mexc'
      mode bb: binance - bybit;  anchor_col = 'binance'

    Spec:
      bybit > anchor + thr → bybit too rich → short bybit → pos=-1
      bybit < anchor - thr → bybit too cheap → long bybit  → pos=+1
      else 0
    """
    if mode == "bm":
        spread = panel["bybit"] - panel[anchor_col]
    elif mode == "bb":
        spread = panel["binance"] - panel["bybit"]
    else:
        raise ValueError(mode)

    pos = pd.Series(0.0, index=panel.index)
    if mode == "bm":
        # bybit minus mexc: positive = bybit too high → short bybit
        pos[spread >  thr] = -1.0
        pos[spread < -thr] = +1.0
    else:
        # binance minus bybit: positive = binance higher = bybit too low → long bybit
        pos[spread >  thr] = +1.0
        pos[spread < -thr] = -1.0

    return pos, spread


def signal_combo_z(panel, z_thr=2.0, window=60):
    """
    Combine bm and bb spread z-scores. Sign convention: +1 means long-bybit-favoured.
      bm_signed = -(bybit - mexc)     (positive → bybit cheap → long)
      bb_signed = +(binance - bybit)  (positive → binance high → bybit too low → long)
    """
    bm = -(panel["bybit"] - panel["mexc"])
    bb =  (panel["binance"] - panel["bybit"])
    z_bm = (bm - bm.rolling(window, min_periods=window // 3).mean()) / \
           bm.rolling(window, min_periods=window // 3).std()
    z_bb = (bb - bb.rolling(window, min_periods=window // 3).mean()) / \
           bb.rolling(window, min_periods=window // 3).std()
    z_combo = pd.concat([z_bm, z_bb], axis=1).mean(axis=1)
    pos = pd.Series(0.0, index=panel.index)
    pos[z_combo >  z_thr] = +1.0
    pos[z_combo < -z_thr] = -1.0
    return pos, z_combo


# --------------------------------------------------------------------- backtest
def backtest_one_symbol(panel, pos, cost_bps=COST_BPS):
    """
    Hold one funding event (8h). Enter at t (after FR settle / open),
    exit at t+1 (next open). r = px[t+1]/px[t] − 1.
    Cost charged on |Δposition| (1 leg, so cost per side = cost_bps).
    """
    px = panel["px"].values
    p = pos.shift(1).fillna(0.0).values   # signal observed at t, traded for t→t+1
    # Returns over 1 funding event ≈ 8 hours
    ret = np.zeros(len(p))
    for i in range(len(p) - 1):
        if px[i] > 0 and np.isfinite(px[i + 1]):
            ret[i] = px[i + 1] / px[i] - 1.0
    pnl = p * ret
    # Cost on position change
    dp = np.abs(np.diff(p, prepend=0.0))
    cost = dp * (cost_bps / 1e4)
    net = pnl - cost
    return pd.DataFrame({
        "pos": p,
        "ret": ret,
        "gross_pnl": pnl,
        "cost": cost,
        "net": net,
    }, index=panel.index)


def backtest_variant(panels, signal_fn, **fn_kwargs):
    """signal_fn(panel) -> (pos, _)."""
    all_rets = []
    per_sym = {}
    for sym, panel in panels.items():
        # If signal requires binance for bb variants — drop NaN rows of that col
        try:
            pos, _ = signal_fn(panel)
        except Exception:
            continue
        bt = backtest_one_symbol(panel, pos)
        per_sym[sym] = {
            "n_periods": int(len(bt)),
            "n_active": int((bt["pos"] != 0).sum()),
            "active_rate": float((bt["pos"] != 0).mean()),
            "net_total": float(bt["net"].sum()),
        }
        all_rets.append(bt["net"].rename(sym))

    if not all_rets:
        return pd.Series(dtype=float), per_sym

    df = pd.concat(all_rets, axis=1).sort_index().fillna(0.0)
    # Equal-weight across active symbols per row (so single-symbol triggers
    # don't dominate by chance — but normalise by COUNT of symbols present,
    # not active, to avoid leverage spikes)
    eq = df.mean(axis=1)
    return eq, per_sym


# --------------------------------------------------------------------- stats
def perf_stats(rets, ann_factor=ANN_FACTOR_8H):
    rets = pd.Series(rets).dropna()
    if rets.std() == 0 or len(rets) < 5:
        return dict(sharpe=0.0, sortino=0.0, calmar=0.0, max_dd=0.0,
                    win_rate=0.0, ann_ret=0.0, ann_vol=0.0, n=int(len(rets)))
    mu = rets.mean(); sd = rets.std()
    sharpe = mu / sd * ann_factor
    downside = rets[rets < 0].std()
    sortino = mu / downside * ann_factor if downside and downside > 0 else 0.0
    equity = (1 + rets).cumprod()
    peak = equity.cummax()
    dd = (equity / peak - 1).min()
    ann_ret = (1 + mu) ** (ann_factor ** 2) - 1
    calmar = ann_ret / abs(dd) if dd < 0 else 0.0
    win_rate = float((rets > 0).mean())
    return dict(sharpe=float(sharpe), sortino=float(sortino),
                calmar=float(calmar), max_dd=float(dd),
                win_rate=win_rate, ann_ret=float(ann_ret),
                ann_vol=float(sd * ann_factor), n=int(len(rets)))


def deflated_sharpe(sr, n_obs, n_trials, skew=0.0, kurt=3.0):
    if n_obs < 20 or n_trials < 1:
        return 0.0
    emc = 0.5772
    e_max = np.sqrt(2 * np.log(max(n_trials, 2))) * (1 - emc) + \
            (1 - emc) / np.sqrt(2 * np.log(max(n_trials, 2)))
    var = (1 - skew * sr + (kurt - 1) / 4.0 * sr ** 2) / max(n_obs - 1, 1)
    if var <= 0:
        return 0.0
    from math import erf, sqrt
    z = (sr - e_max) / np.sqrt(var)
    return float(0.5 * (1 + erf(z / sqrt(2))))


def block_bootstrap_ci(rets, ann_factor, n_iter=N_BOOT, block=8, seed=SEED):
    rets = np.asarray(rets)
    n = len(rets)
    if n < block * 3:
        return {"sr_lo": 0.0, "sr_hi": 0.0, "sr_mean": 0.0}
    rng = np.random.default_rng(seed)
    n_blocks = max(1, n // block)
    sr_samples = []
    for _ in range(n_iter):
        starts = rng.integers(0, n - block + 1, size=n_blocks)
        sample = np.concatenate([rets[s:s + block] for s in starts])
        s = sample.std()
        if s > 0:
            sr_samples.append(sample.mean() / s * ann_factor)
    if not sr_samples:
        return {"sr_lo": 0.0, "sr_hi": 0.0, "sr_mean": 0.0}
    arr = np.array(sr_samples)
    return {"sr_lo": float(np.quantile(arr, 0.025)),
            "sr_hi": float(np.quantile(arr, 0.975)),
            "sr_mean": float(arr.mean())}


def permutation_test(panels, signal_fn, n_iter=N_PERM, seed=SEED):
    """
    Permute the SIGN of each non-zero position per symbol independently.
    Null: signal direction has no edge over its absolute size/timing.
    """
    rng = np.random.default_rng(seed)
    actual_rets, _ = backtest_variant(panels, signal_fn)
    actual_sr = perf_stats(actual_rets)["sharpe"]

    null_srs = np.zeros(n_iter)
    for it in range(n_iter):
        rets_list = []
        for sym, panel in panels.items():
            try:
                pos, _ = signal_fn(panel)
            except Exception:
                continue
            sign = rng.choice([-1.0, 1.0], size=len(pos))
            permuted = pos * sign
            bt = backtest_one_symbol(panel, permuted)
            rets_list.append(bt["net"].rename(sym))
        if rets_list:
            df = pd.concat(rets_list, axis=1).sort_index().fillna(0.0)
            r = df.mean(axis=1)
            null_srs[it] = perf_stats(r)["sharpe"]

    return {"actual_sharpe": float(actual_sr),
            "null_mean": float(null_srs.mean()),
            "null_std": float(null_srs.std()),
            "null_p95": float(np.quantile(null_srs, 0.95)),
            "p_value": float((null_srs >= actual_sr).mean()),
            "n_iter": n_iter}


def walk_forward(rets, n_folds=4):
    T = len(rets)
    fold_size = T // n_folds
    out = []
    for f in range(n_folds):
        s = f * fold_size
        e = (f + 1) * fold_size if f < n_folds - 1 else T
        out.append({"fold": f, **perf_stats(rets.iloc[s:e])})
    return out


# --------------------------------------------------------------------- variants
def make_sig_bm(thr):
    return lambda panel: signal_threshold_pair(panel, "mexc", thr, mode="bm")


def make_sig_bb(thr):
    return lambda panel: signal_threshold_pair(panel, "binance", thr, mode="bb")


def sig_combo_z(panel):
    return signal_combo_z(panel, z_thr=2.0, window=60)


VARIANTS = {
    "V_bm_2pct":  {"fn": make_sig_bm(THR_2PCT_ANN), "thr_ann": 0.02,
                   "anchor": "mexc",    "label": "|bybit-mexc| > 2%/yr"},
    "V_bm_3pct":  {"fn": make_sig_bm(THR_3PCT_ANN), "thr_ann": 0.03,
                   "anchor": "mexc",    "label": "|bybit-mexc| > 3%/yr"},
    "V_bb_2pct":  {"fn": make_sig_bb(THR_2PCT_ANN), "thr_ann": 0.02,
                   "anchor": "binance", "label": "|binance-bybit| > 2%/yr"},
    "V_bb_3pct":  {"fn": make_sig_bb(THR_3PCT_ANN), "thr_ann": 0.03,
                   "anchor": "binance", "label": "|binance-bybit| > 3%/yr"},
    "V_combo_z":  {"fn": sig_combo_z, "thr_ann": None,
                   "anchor": "both",    "label": "|z(bm,bb)| > 2 (60-ev)"},
}


def run_variant(name, vdef, panels):
    print(f"  >> {name}: {vdef['label']}")
    rets, per_sym = backtest_variant(panels, vdef["fn"])
    if rets.empty:
        return {"empty": True, "label": vdef["label"]}

    n_total = len(rets)
    n_is = int(n_total * IS_FRAC)
    full = perf_stats(rets)
    is_ = perf_stats(rets.iloc[:n_is])
    oos = perf_stats(rets.iloc[n_is:])

    # Active period only stats (excluding 0-position events)
    nonzero = rets[rets != 0]
    active = perf_stats(nonzero) if len(nonzero) > 5 else \
             dict(sharpe=0.0, n=int(len(nonzero)))

    # Cost stress
    def re_bt(scale):
        out = []
        for sym, panel in panels.items():
            pos, _ = vdef["fn"](panel)
            bt = backtest_one_symbol(panel, pos, cost_bps=COST_BPS * scale)
            out.append(bt["net"].rename(sym))
        return pd.concat(out, axis=1).sort_index().fillna(0.0).mean(axis=1)

    lo_sr = perf_stats(re_bt(0.5))["sharpe"]
    hi_sr = perf_stats(re_bt(1.5))["sharpe"]

    boot = block_bootstrap_ci(rets.iloc[n_is:].values, ANN_FACTOR_8H,
                              n_iter=N_BOOT, block=8, seed=SEED + 7)
    perm = permutation_test(panels, vdef["fn"], n_iter=N_PERM, seed=SEED + 11)
    wf = walk_forward(rets, n_folds=4)

    skew_v = float(stats.skew(rets.dropna())) if len(rets.dropna()) > 5 else 0.0
    kurt_v = float(stats.kurtosis(rets.dropna(), fisher=False)) if len(rets.dropna()) > 5 else 3.0
    dsr_full = deflated_sharpe(full["sharpe"], full["n"],
                                n_trials=N_TRIALS_DSR, skew=skew_v, kurt=kurt_v)
    dsr_oos = deflated_sharpe(oos["sharpe"], oos["n"],
                               n_trials=N_TRIALS_DSR, skew=skew_v, kurt=kurt_v)

    # §6 gates (lab institutional bar)
    gates = {
        "oos_sr_ge_0_5":      bool(oos["sharpe"] >= 0.5),
        "p_perm_lt_0_05":     bool(perm["p_value"] < 0.05),
        "max_dd_gt_neg40":    bool(full["max_dd"] > -0.40),
        "cost_stress_robust": bool(hi_sr >= 0.5 * full["sharpe"]
                                   if full["sharpe"] > 0 else False),
        "dsr_oos_ge_0_5":     bool(dsr_oos >= 0.5),
        "wf_majority_pos":    bool(sum(1 for f in wf if f["sharpe"] > 0) >= 3),
    }
    gates["pass_count"] = int(sum(1 for v in gates.values() if v is True))
    gates["all_pass"] = bool(all(v for k_, v in gates.items()
                                  if k_ not in ("pass_count", "all_pass")))

    return {
        "label": vdef["label"],
        "anchor": vdef["anchor"],
        "thr_ann": vdef["thr_ann"],
        "n_periods": n_total,
        "full": full,
        "is": is_,
        "oos": oos,
        "active_only": active,
        "active_rate": float((rets != 0).mean()),
        "cost_stress": {"low_50pct": float(lo_sr),
                        "base_100pct": float(full["sharpe"]),
                        "high_150pct": float(hi_sr)},
        "bootstrap_oos_sharpe_95ci": boot,
        "permutation": perm,
        "walk_forward": wf,
        "dsr_full": dsr_full,
        "dsr_oos": dsr_oos,
        "per_symbol": per_sym,
        "gates": gates,
        "equity_curve": (1 + rets).cumprod().tolist(),
        "equity_idx":   [str(x) for x in rets.index],
        "_rets_series": rets,
    }


# --------------------------------------------------------------------- spread distribution
def spread_diagnostics(panels):
    """Cross-sectional spread distribution stats."""
    out = {}
    for sym, panel in panels.items():
        sub = panel.dropna(subset=["bybit"])
        bm = (sub["bybit"] - sub["mexc"]).dropna() if "mexc" in sub else pd.Series([])
        bb = (sub["binance"] - sub["bybit"]).dropna() if "binance" in sub else pd.Series([])
        out[sym] = {
            "bm": {
                "n": int(len(bm)),
                "mean": float(bm.mean()) if len(bm) else None,
                "std":  float(bm.std())  if len(bm) else None,
                "p05":  float(bm.quantile(0.05)) if len(bm) else None,
                "p50":  float(bm.quantile(0.50)) if len(bm) else None,
                "p95":  float(bm.quantile(0.95)) if len(bm) else None,
                "abs_p95_ann_pct": float(bm.abs().quantile(0.95) / ANN_PER_EVENT * 100) if len(bm) else None,
                "frac_gt_2pct_ann": float((bm.abs() > THR_2PCT_ANN).mean()) if len(bm) else None,
                "frac_gt_3pct_ann": float((bm.abs() > THR_3PCT_ANN).mean()) if len(bm) else None,
            },
            "bb": {
                "n": int(len(bb)),
                "mean": float(bb.mean()) if len(bb) else None,
                "std":  float(bb.std())  if len(bb) else None,
                "p05":  float(bb.quantile(0.05)) if len(bb) else None,
                "p50":  float(bb.quantile(0.50)) if len(bb) else None,
                "p95":  float(bb.quantile(0.95)) if len(bb) else None,
                "abs_p95_ann_pct": float(bb.abs().quantile(0.95) / ANN_PER_EVENT * 100) if len(bb) else None,
                "frac_gt_2pct_ann": float((bb.abs() > THR_2PCT_ANN).mean()) if len(bb) else None,
                "frac_gt_3pct_ann": float((bb.abs() > THR_3PCT_ANN).mean()) if len(bb) else None,
            },
        }
    return out


# --------------------------------------------------------------------- main
def main():
    t0 = time.time()
    print("=== Wave K159 — Cross-Exchange FR Spread Arb ===")
    print(f"Symbols: {SYMBOLS}")
    print(f"Thr 2% ann / 8h = {THR_2PCT_ANN:.3e}")
    print(f"Thr 3% ann / 8h = {THR_3PCT_ANN:.3e}\n")

    print("Fetching triplet panels (this may take 2-4 min for first run)...")
    panels, data_avail = build_triplet_panel()

    print("\nData availability:")
    for sym, d in data_avail.items():
        print(f"  {sym}: {d}")

    if not panels:
        print("No symbols passed — aborting.")
        return

    print("\nSpread distributions:")
    spread_stats = spread_diagnostics(panels)
    for sym, d in spread_stats.items():
        bm = d["bm"]; bb = d["bb"]
        print(f"  {sym}: bm n={bm['n']:4d} p95_ann={bm['abs_p95_ann_pct']} %  "
              f"frac>2%={bm['frac_gt_2pct_ann']}; "
              f"bb n={bb['n']:4d} p95_ann={bb['abs_p95_ann_pct']} %  "
              f"frac>2%={bb['frac_gt_2pct_ann']}")

    print("\nRunning variants ...")
    results = {}
    for name, vdef in VARIANTS.items():
        results[name] = run_variant(name, vdef, panels)
        print(f"     [elapsed {time.time() - t0:.1f}s]")

    # ----------------------------- save
    out_path = ROOT / "wave_k159_xex_fr_spread.json"
    curves_path = ROOT / "wave_k159_curves.json"

    summary = {}
    for name, v in results.items():
        slim = {kk: vv for kk, vv in v.items()
                if kk not in ("equity_curve", "equity_idx", "_rets_series")}
        summary[name] = slim
    summary["_data_availability"] = data_avail
    summary["_spread_diagnostics"] = spread_stats
    summary["_meta"] = {
        "wave": "K159",
        "wall_seconds": time.time() - t0,
        "symbols_requested": SYMBOLS,
        "symbols_used": list(panels.keys()),
        "n_perm": N_PERM,
        "n_boot": N_BOOT,
        "n_trials_dsr": N_TRIALS_DSR,
        "is_frac": IS_FRAC,
        "cost_bps_per_side": COST_BPS,
        "thr_2pct_ann_per_8h": THR_2PCT_ANN,
        "thr_3pct_ann_per_8h": THR_3PCT_ANN,
        "ann_factor_8h": float(ANN_FACTOR_8H),
        "primary_variant": "V_bm_2pct",
    }

    curves = {}
    for name, v in results.items():
        if "equity_curve" in v:
            curves[name] = {"equity_curve": v["equity_curve"],
                            "equity_idx":   v["equity_idx"]}

    with open(out_path, "w") as f:
        json.dump(summary, f, indent=2, default=str)
    with open(curves_path, "w") as f:
        json.dump(curves, f, indent=2, default=str)

    elapsed = time.time() - t0
    print(f"\nDone in {elapsed:.1f}s")
    print(f"  -> {out_path}")
    print(f"  -> {curves_path}")

    print("\n=== K159 Summary ===")
    for name, r in results.items():
        if r.get("empty"):
            print(f"{name:12s} EMPTY")
            continue
        full = r["full"]; oos = r["oos"]; perm = r["permutation"]; g = r["gates"]
        print(f"{name:12s} netSR={full['sharpe']:+.2f} OOS={oos['sharpe']:+.2f} "
              f"MaxDD={full['max_dd']:.2%} activeRate={r['active_rate']:.3f} "
              f"p={perm['p_value']:.3f} DSR_oos={r['dsr_oos']:.3f} "
              f"gates={g['pass_count']}/6")


if __name__ == "__main__":
    main()
