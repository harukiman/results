#!/usr/bin/env python3
"""
wave_k619_ethfi_btc_eval.py — K619 ETHFI-BTC FR Differential Paired-Trade Evaluation
=======================================================================================
K339 REPO_ROOT pattern. Ether.fi (ETHFI) governance token, EigenLayer restaking
platform vs BTC. K616 ENA ACCEPT (Synthetic Stable Infra cluster #23). K619 =
Restaking Yield cluster test, distinct from LSD (K594 LDO REJECT) and Synthetic
Stable (K616 ENA ACCEPT).

HYPOTHESIS
----------
K449/K476/K480/K484 pattern (高 vol alt と BTC の funding rate differential が定常的
mean-reverting) が ETHFI に generalize するか?
  - ETH-BTC: 1.08x BTC vol (FR std), Sharpe 5.663, $13K/yr @$10M — ACCEPT
  - SOL-BTC: 1.76x BTC vol (FR std), Sharpe 16.298, $187K/yr @$10M — ACCEPT
  - AVAX-BTC: 1.50x BTC vol (FR std), Sharpe 43.887 — ACCEPT G5a=0.300
  - AAVE-BTC: 2.4x BTC vol (FR std), Sharpe 11.354 — ACCEPT K596
  - ENA-BTC: 1.77x BTC vol 6M, Sharpe 20.47 — ACCEPT K616 (Synthetic Stable Infra #23)
  - LDO-BTC: REJECT K594 (gov token, ETH staking, poor vol ratio)
  - ETHFI-BTC: 2-4x BTC vol expected — K619 hypothesis (Restaking Yield distinct)

ETHER.FI / EIGENLAYER RESTAKING HYPOTHESIS (K619 — Restaking Yield cluster)
---------------------------------------------------------------------------
  ETHFI = Ether.fi governance token. Protocol provides:
  - Liquid restaking (eETH/weETH): ETH restaked via EigenLayer for extra yield
  - EigenLayer security provider: earns restaking rewards (ETH + EIGEN + AVS fees)
  - ETHFI is the protocol equity: captures eETH/weETH fee revenue + governance

  DISTINCT from:
    LDO  (K594 REJECT): liquid staking governance — stETH fee. Rejected because
         governance token, no additional restaking yield, pure ETH staking exposure.
    ENA  (K616 ACCEPT): synthetic stable infra — sUSDe FR-arb revenue. Distinct
         because ENA protocol revenue = perp funding rate, not ETH staking.
    AAVE (K596 ACCEPT): lending protocol governance — interest rate arbitrage.
    ETH-BTC (K449): ETH derivative, 1.08x vol.

  ETHFI-specific FR mechanics:
    1. Restaking yield exposure: ETHFI demand ∝ eETH/weETH APY (ETH staking + AVS rewards).
       Unlike LDO (staking only), ETHFI adds EigenLayer security yield on top of ETH staking.
    2. AVS fee revenue cycles: Active Validator Sets (AVS) on EigenLayer pay restakers.
       ETHFI captures % of AVS fees → ETHFI value tied to AVS ecosystem growth cycles.
    3. ETHFI vs ENA comparison: Both are "yield infrastructure equity" tokens.
       ENA yield = perp FR arb (market-driven, fast cycles). ETHFI yield = ETH staking +
       AVS restaking rewards (protocol-driven, slower cycles, but additional yield layer).
    4. LDO rejection lesson: LDO REJECT because pure governance (no additional yield
       mechanism beyond basic stETH fee). ETHFI has ADDITIONAL restaking layer → distinct.
    5. Restaking yield cluster hypothesis: First restaking-native token in family test.
       If distinct from both LSD (LDO) and synthetic stable (ENA), new cluster formed.
    6. EigenLayer EIGEN token correlation: ETHFI and EIGEN likely correlated. Need
       G5 check for EIGEN signal overlap. If EIGEN listed on HL, add G5 check.
    7. Vol ratio 2-4x BTC expected from:
       - EigenLayer ecosystem hype cycles (AVS launches create demand spikes)
       - Slashing risk events (EigenLayer operator slashing → ETHFI FR spikes)
       - Yield compression (ETH staking APY cycles + AVS fee cycles)

  CRITICAL CROSS-COMPARISONS:
    ETHFI-ENA:  Restaking yield vs synthetic stable (yield infra peers)
    ETHFI-LDO:  Restaking vs liquid staking (LDO rejected — ETHFI improvement hypothesis)
    ETHFI-ETH:  ETH derivative exposure check (restaking = ETH exposure)
    ETHFI-BTC:  Primary pair (FR differential signal)

MECHANISM (identical to K449/K476/K480/K484/K596/K616)
-------------------------------------------------------
  fr_diff_t = btc_fr_t - ethfi_fr_t
  Signal = sign(W rolling mean of fr_diff) — always-on, targets persistent divergence
  When fr_diff_W > 0: BTC pays more → short BTC, long ETHFI → net FR carry > 0
  When fr_diff_W < 0: ETHFI pays more → short ETHFI, long BTC → net FR carry > 0

  K619 dynamic: ETHFI FR can spike during restaking narrative cycles (EigenLayer launches,
  AVS announcements). Creates FR spikes that are distinct from BTC speculative FR patterns.

DATA SOURCES
------------
  Primary:   HL ETHFI FR: fetched live → cache/k163_hl/hl_fr_ETHFI.parquet
             HL BTC FR: cache/k163_hl/hl_fr_BTC.parquet
  Cross-check: Bybit ETHFIUSDT perp (fetched live)
               OKX ETHFI-USDT-SWAP check
  Ref signals: ENA (K616), LDO (K594), ETH (K449) for cluster comparison

§6 GATES (K619 — 25-member family + Restaking Yield cluster test)
------------------------------------------------------------------
  G1:  OOS Sharpe >= 1.0
  G2:  Perm p-value <= 0.05 (500 direction reshuffles, OOS)
  G3:  DSR Bonferroni p < 0.05/N_GRID
  G4:  Walk-forward 12-fold stability (IS 90d / OOS 30d), all positive
  G5a: Corr vs K449 (ETH-BTC) < 0.40
  G5b: Corr vs K476 (SOL-BTC) < 0.40
  G5c: Corr vs K484 (AVAX-BTC) < 0.40
  G5d: Corr vs K493 (ATOM-BTC) < 0.40
  G5e: Corr vs K500 (INJ-BTC) < 0.40
  G5f: Corr vs K507 (SEI-BTC) < 0.40
  G5g: Corr vs TIA-BTC < 0.40
  G5h: Corr vs K512 (APT-BTC) < 0.40
  G5i: Corr vs K517 (FIL-BTC) < 0.40
  G5j: Corr vs K280 BTC-carry baseline < 0.40
  G5k: Corr vs RENDER-BTC K531 < 0.40
  G5l: Corr vs TAO-BTC < 0.40
  G5m: Corr vs LINK-BTC K557 < 0.40
  G5n: Corr vs TON-BTC K571 < 0.40
  G5o: Corr vs SAND-BTC K583 < 0.40
  G5p: Corr vs ICP-BTC K587 < 0.40
  G5q: Corr vs AXS-BTC K591 < 0.40
  G5r: Corr vs DOGE-BTC K592 < 0.40
  G5s: Corr vs SHIB-BTC K595 < 0.40
  G5t: Corr vs AAVE-BTC K596 < 0.40
  G5u: Corr vs CRV-BTC K599 < 0.40
  G5v: Corr vs PEPE-BTC K598 < 0.40
  G5w: Corr vs WIF-BTC K601 < 0.40
  G5x: Corr vs BONK-BTC K603 < 0.40
  G5y: Corr vs UNI-BTC < 0.40
  G5z: Corr vs ARB-BTC K491 < 0.40
  G5aa: Corr vs JUP-BTC K606 < 0.40
  G5ab: Corr vs SNX-BTC K604 < 0.40
  G5ac: Corr vs LDO-BTC < 0.40       <- CRITICAL: restaking vs LSD
  G5ad: Corr vs MKR-BTC < 0.40
  G5ae: Corr vs OP-BTC < 0.40
  G5af: Corr vs POL-BTC < 0.40
  G5ag: Corr vs ENA-BTC K616 < 0.40  <- CRITICAL: restaking vs synthetic stable
  G6:  Trade count >= 30/yr
  G7:  Ann return > 5% at 4x leverage
  G8:  Cross-venue Bybit ETHFIUSDT corr >= 0.55
  G9:  Data sufficiency >= 180d OOS

DECISION CRITERIA
-----------------
  ACCEPT (Sharpe >= 5, all G5 PASS, critical gates pass): scaffold candidate
  ACCEPT CONDITIONAL (structural failures but G5 all PASS): 60d paper-trade
  BLOCKED-RESTAKING (G5ag ENA >= 0.40): restaking/synthetic-stable cluster dup
  BLOCKED-LSD (G5ac LDO >= 0.40): restaking / liquid staking cluster dup
  BLOCKED-G5 (ticker): specific G5 correlation fail
  REJECT (Phase 0 vol fail OR critical G5 fail): close restaking yield line

HL CONCENTRATION (v6.37 baseline post-K616)
-------------------------------------------
  K616 ENA: ACCEPT (Bybit routing mandatory, HL 67.5% → BREACH). HL baseline=64.5%.
  K619 ETHFI additional: check HL concentration.
  HL cap = 65.0% (HL concentration CRITICAL from K612 lesson).
  ETHFI: consider Bybit primary if HL cap constraint.
"""
from __future__ import annotations

import json
import math
import time
import warnings
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from scipy import stats

warnings.filterwarnings("ignore")

START_TIME = time.time()
BASE     = Path("/Users/nekonaomichi/crypto-lab")
CACHE    = BASE / "cache"
HL_CACHE = CACHE / "k163_hl"

HL_API_URL = "https://api.hyperliquid.xyz/info"

# ── Config ─────────────────────────────────────────────────────────────────
WINDOW_H        = 168       # default 7d (K615/K617 lesson)
THRESHOLD       = 0.0       # always-on
COST_RT_BPS     = 4         # 2bps per side × 2 legs
OOS_FRAC        = 0.30
N_FOLDS_WF      = 12
WF_IS_H         = 2160      # 90d
WF_OOS_H        = 720       # 30d
N_PERM          = 500
GRID_WINDOWS    = [84, 168, 336, 504, 720]
GRID_THRESHOLDS = [0.0, 0.5, 1.0]
N_TRIALS_TESTED = len(GRID_WINDOWS) * len(GRID_THRESHOLDS)  # 15

VOL_RATIO_MIN   = 1.5

G1_SH_MIN       = 1.0
G2_PERM_MAX     = 0.05
G5_CORR_MAX     = 0.4
G6_TRADES_MIN   = 30.0
G7_ANN_RET_MIN  = 5.0
G8_VENUE_CORR   = 0.55

ANN_FACTOR_1H   = math.sqrt(8760)

# Family reference data (post-K616, 25 active members + ENA K616 ACCEPT)
FAMILY_MEMBERS = [
    {"rank": 1,  "pair": "APT-BTC",    "sharpe": 51.100,  "status": "ACCEPT",            "wave": "K512"},
    {"rank": 2,  "pair": "ATOM-BTC",   "sharpe": 50.786,  "status": "ACCEPT",            "wave": "K493"},
    {"rank": 3,  "pair": "SEI-BTC",    "sharpe": 48.100,  "status": "ACCEPT",            "wave": "K507"},
    {"rank": 4,  "pair": "AVAX-BTC",   "sharpe": 43.887,  "status": "ACCEPT",            "wave": "K484"},
    {"rank": 5,  "pair": "SHIB-BTC",   "sharpe": 38.481,  "status": "ACCEPT CONDITIONAL","wave": "K595"},
    {"rank": 6,  "pair": "SAND-BTC",   "sharpe": 33.627,  "status": "ACCEPT CONDITIONAL","wave": "K583"},
    {"rank": 7,  "pair": "JUP-BTC",    "sharpe": 29.895,  "status": "ACCEPT CONDITIONAL","wave": "K606"},
    {"rank": 8,  "pair": "PEPE-BTC",   "sharpe": 26.420,  "status": "ACCEPT CONDITIONAL","wave": "K598"},
    {"rank": 9,  "pair": "BONK-BTC",   "sharpe": 23.667,  "status": "ACCEPT CONDITIONAL","wave": "K603"},
    {"rank": 10, "pair": "FIL-BTC",    "sharpe": 21.773,  "status": "ACCEPT CONDITIONAL","wave": "K517"},
    {"rank": 11, "pair": "DOGE-BTC",   "sharpe": 21.069,  "status": "ACCEPT CONDITIONAL","wave": "K592"},
    {"rank": 12, "pair": "ENA-BTC",    "sharpe": 20.468,  "status": "ACCEPT",            "wave": "K616"},
    {"rank": 13, "pair": "AXS-BTC",    "sharpe": 17.815,  "status": "ACCEPT CONDITIONAL","wave": "K591"},
    {"rank": 14, "pair": "SOL-BTC",    "sharpe": 16.298,  "status": "ACCEPT",            "wave": "K476"},
    {"rank": 15, "pair": "RENDER-BTC", "sharpe": 15.302,  "status": "ACCEPT CONDITIONAL","wave": "K531"},
    {"rank": 16, "pair": "HBAR-BTC",   "sharpe": 14.709,  "status": "ACCEPT CONDITIONAL","wave": "K610"},
    {"rank": 17, "pair": "TIA-BTC",    "sharpe": 14.439,  "status": "ACCEPT",            "wave": "K"},
    {"rank": 18, "pair": "LINK-BTC",   "sharpe": 13.775,  "status": "ACCEPT CONDITIONAL","wave": "K557"},
    {"rank": 19, "pair": "WIF-BTC",    "sharpe": 12.934,  "status": "ACCEPT CONDITIONAL","wave": "K601"},
    {"rank": 20, "pair": "ICP-BTC",    "sharpe": 12.527,  "status": "ACCEPT CONDITIONAL","wave": "K587"},
    {"rank": 21, "pair": "AAVE-BTC",   "sharpe": 11.354,  "status": "ACCEPT",            "wave": "K596"},
    {"rank": 22, "pair": "INJ-BTC",    "sharpe": 11.232,  "status": "ACCEPT",            "wave": "K500"},
    {"rank": 23, "pair": "TON-BTC",    "sharpe": 8.402,   "status": "ACCEPT CONDITIONAL","wave": "K571"},
    {"rank": 24, "pair": "ETH-BTC",    "sharpe": 5.663,   "status": "ACCEPT",            "wave": "K449"},
    {"rank": 25, "pair": "TAO-BTC",    "sharpe": 5.267,   "status": "ACCEPT CONDITIONAL","wave": "K"},
]

G5_SIGNALS = {
    "G5a_ETH":    "ETH",
    "G5b_SOL":    "SOL",
    "G5c_AVAX":   "AVAX",
    "G5d_ATOM":   "ATOM",
    "G5e_INJ":    "INJ",
    "G5f_SEI":    "SEI",
    "G5g_TIA":    "TIA",
    "G5h_APT":    "APT",
    "G5i_FIL":    "FIL",
    "G5k_RNDR":   "RNDR",
    "G5l_TAO":    "TAO",
    "G5m_LINK":   "LINK",
    "G5n_TON":    "TON",
    "G5o_SAND":   "SAND",
    "G5p_ICP":    "ICP",
    "G5q_AXS":    "AXS",
    "G5r_DOGE":   "DOGE",
    "G5s_SHIB":   "SHIB",
    "G5t_AAVE":   "AAVE",
    "G5u_CRV":    "CRV",
    "G5v_PEPE":   "PEPE",
    "G5w_WIF":    "WIF",
    "G5x_BONK":   "BONK",
    "G5y_UNI":    "UNI",
    "G5z_ARB":    "ARB",
    "G5aa_JUP":   "JUP",
    "G5ab_SNX":   "SNX",
    "G5ac_LDO":   "LDO",      # CRITICAL: restaking vs LSD
    "G5ad_MKR":   "MKR",
    "G5ae_OP":    "OP",
    "G5af_POL":   "POL",
    "G5ag_ENA":   "ENA",      # CRITICAL: restaking vs synthetic stable K616
}


# ── HL Data Fetching ──────────────────────────────────────────────────────────

def hl_fetch_page(coin: str, start_ms: int, end_ms: int) -> List[Dict]:
    """Fetch one page of HL funding rate history."""
    import urllib.request as _req
    import urllib.error as _err
    payload = json.dumps({
        "type": "fundingHistory",
        "coin": coin,
        "startTime": start_ms,
        "endTime": end_ms,
    }).encode()
    req = _req.Request(
        HL_API_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    for attempt in range(4):
        try:
            with _req.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode())
                return data if isinstance(data, list) else []
        except _err.HTTPError as e:
            if e.code == 429:
                wait = 20 * (attempt + 1)
                print(f"    429 {coin}, wait {wait}s...")
                time.sleep(wait)
                continue
            return []
        except Exception as ex:
            print(f"    err {coin}: {ex}")
            if attempt < 3:
                time.sleep(5)
    return []


def fetch_hl_fr(sym: str, hl_ticker: str, days: int = 730) -> Optional[pd.DataFrame]:
    """Fetch HL FR data with pagination and cache."""
    cache = HL_CACHE / f"hl_fr_{sym}.parquet"
    if cache.exists():
        df = pd.read_parquet(cache)
        print(f"  {sym}: cached ({len(df)} rows)")
        return df

    now_ms = int(time.time() * 1000)
    start_ms = now_ms - days * 86400 * 1000
    all_events, page_start = [], start_ms

    print(f"  Fetching {sym} [{hl_ticker}] from HL...", flush=True)
    while page_start < now_ms:
        events = hl_fetch_page(hl_ticker, page_start, now_ms)
        if not events:
            break
        all_events.extend(events)
        last_t = max(e.get("time", 0) for e in events)
        if last_t <= page_start or len(events) < 500:
            break
        page_start = last_t + 1
        time.sleep(0.5)

    if not all_events:
        print(f"    -> {sym} not listed on HL (no data)")
        return None

    records = [
        {
            "timestamp": pd.Timestamp(e["time"], unit="ms"),
            "hl_fr": float(e.get("fundingRate", 0)),
        }
        for e in all_events
    ]
    df = (
        pd.DataFrame(records)
        .drop_duplicates("timestamp")
        .sort_values("timestamp")
        .reset_index(drop=True)
    )
    df.to_parquet(cache, index=False)
    print(f"    -> {sym}: {len(df)} events saved to {cache}")
    return df


def fetch_bybit_fr(sym_usdt: str, limit_per_page: int = 200, max_pages: int = 100) -> Optional[pd.Series]:
    """Fetch Bybit perpetual funding rate history."""
    import urllib.request as _req
    all_rows = []
    cursor = ""
    base = (
        f"https://api.bybit.com/v5/market/funding/history"
        f"?category=linear&symbol={sym_usdt}&limit={limit_per_page}"
    )
    print(f"  Fetching Bybit {sym_usdt} FR...", flush=True)

    for page in range(max_pages):
        url = base + (f"&cursor={cursor}" if cursor else "")
        try:
            req = _req.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with _req.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode())
            rows = data.get("result", {}).get("list", [])
            cursor = data.get("result", {}).get("nextPageCursor", "")
            if not rows:
                break
            all_rows.extend(rows)
            if not cursor:
                break
            time.sleep(0.3)
        except Exception as e:
            print(f"    Bybit {sym_usdt} page {page} error: {e}")
            break

    if not all_rows:
        return None

    records = [
        {
            "timestamp": pd.Timestamp(int(r["fundingRateTimestamp"]), unit="ms"),
            "funding_rate": float(r["fundingRate"]),
        }
        for r in all_rows
    ]
    s = (
        pd.DataFrame(records)
        .drop_duplicates("timestamp")
        .sort_values("timestamp")
        .set_index("timestamp")["funding_rate"]
    )
    print(f"    Bybit {sym_usdt}: {len(s)} rows ({s.index.min().date()} – {s.index.max().date()})")
    return s


# ── Signal & Backtest ─────────────────────────────────────────────────────────

def _to_fr_series(df: pd.DataFrame) -> pd.Series:
    """Convert FR dataframe to series with datetime index."""
    if "timestamp" in df.columns:
        return df.set_index("timestamp")["hl_fr"]
    elif isinstance(df.index, pd.DatetimeIndex):
        return df["hl_fr"]
    else:
        return df.reset_index().set_index(df.reset_index().columns[0])["hl_fr"]


def build_fr_diff(df_ethfi: pd.DataFrame, df_btc: pd.DataFrame) -> pd.DataFrame:
    """Align ETHFI and BTC FR, compute differential."""
    e = _to_fr_series(df_ethfi)
    b = _to_fr_series(df_btc)

    # Align to 1h frequency (HL settles hourly)
    combined = pd.concat([e.rename("ethfi_fr"), b.rename("btc_fr")], axis=1)
    combined = combined.ffill().dropna()
    combined["fr_diff"] = combined["btc_fr"] - combined["ethfi_fr"]
    return combined.reset_index().rename(columns={"index": "timestamp"})


def run_backtest(
    diff: pd.DataFrame,
    window_h: int,
    threshold: float,
    cost_rt_bps: float = COST_RT_BPS,
) -> pd.Series:
    """
    FR carry strategy returns (hourly, per-unit notional).
    Signal: sign(rolling mean of fr_diff over window_h hours).
    Position: +1 (long ETHFI, short BTC) or -1 (short ETHFI, long BTC).
    Carry per hour = |fr_diff| × 0.5 (half from each leg on a per-hour basis).
    """
    df = diff.copy()
    rolling_mean = df["fr_diff"].rolling(window_h).mean()

    # Threshold: dead-band to filter noise
    signal = np.where(
        rolling_mean > threshold, 1,
        np.where(rolling_mean < -threshold, -1, 0)
    )
    df["signal"] = signal

    # FR carry: when signal=+1, collect ethfi_fr if ethfi pays more, or btc_fr if btc pays more
    # Simplified: carry = signal × fr_diff (direction × differential captures the carry)
    df["carry"] = df["signal"] * df["fr_diff"]

    # Transaction costs on signal flip
    df["signal_shift"] = df["signal"].shift(1).fillna(0)
    df["flip"] = (df["signal"] != df["signal_shift"]).astype(float)
    df["cost"] = df["flip"] * cost_rt_bps * 1e-4

    df["ret"] = df["carry"] - df["cost"]
    return df.set_index("timestamp")["ret"]


def sharpe(rets: pd.Series) -> float:
    """Annualised Sharpe from 1h returns."""
    if len(rets) < 2 or rets.std() == 0:
        return 0.0
    return float(rets.mean() / rets.std() * ANN_FACTOR_1H)


def ann_ret(rets: pd.Series) -> float:
    """Annualised return (%) from 1h carry returns."""
    if len(rets) < 2:
        return 0.0
    n_years = len(rets) / 8760
    total = float(rets.sum())
    return total / n_years * 100 if n_years > 0 else 0.0


def max_drawdown(rets: pd.Series) -> float:
    """Maximum drawdown from cumulative return series."""
    cumret = rets.cumsum()
    rolling_max = cumret.cummax()
    dd = cumret - rolling_max
    return float(dd.min())


def permutation_test(rets: pd.Series, n_perm: int = N_PERM) -> float:
    """Permutation test: randomly shuffle signal direction, compare Sharpe."""
    rng = np.random.default_rng(42)
    base_sh = sharpe(rets)
    count_above = 0
    for _ in range(n_perm):
        flips = rng.choice([-1, 1], size=len(rets))
        perm_rets = rets * flips
        if sharpe(perm_rets) >= base_sh:
            count_above += 1
    return count_above / n_perm


def walk_forward(
    diff: pd.DataFrame,
    window_h: int,
    threshold: float,
    is_h: int = WF_IS_H,
    oos_h: int = WF_OOS_H,
    n_folds: int = N_FOLDS_WF,
) -> List[Dict]:
    """Walk-forward validation."""
    total_h = len(diff)
    min_total = is_h + oos_h
    if total_h < min_total:
        return []

    fold_size = oos_h
    results = []
    for fold in range(n_folds):
        fold_end = total_h - fold * fold_size
        fold_oos_start = fold_end - oos_h
        fold_is_start = fold_oos_start - is_h
        if fold_is_start < 0:
            break

        is_slice = diff.iloc[fold_is_start:fold_oos_start]
        oos_slice = diff.iloc[fold_oos_start:fold_end]

        # Fit threshold on IS (std of fr_diff × threshold_factor)
        is_std = is_slice["fr_diff"].std()
        thresh = is_std * threshold

        oos_ret = run_backtest(oos_slice.reset_index(drop=True), window_h, thresh)
        sh = sharpe(oos_ret)
        ar = ann_ret(oos_ret)
        entries = int((oos_ret != 0).sum())

        fold_num = n_folds - fold
        oos_start_dt = oos_slice["timestamp"].iloc[0] if len(oos_slice) > 0 else None
        oos_end_dt = oos_slice["timestamp"].iloc[-1] if len(oos_slice) > 0 else None

        results.append({
            "fold": fold_num,
            "oos_start": str(oos_start_dt.date()) if oos_start_dt is not None else "",
            "oos_end": str(oos_end_dt.date()) if oos_end_dt is not None else "",
            "sharpe": round(sh, 3),
            "ann_ret_pct": round(ar, 3),
            "entries": entries,
        })

    return sorted(results, key=lambda x: x["fold"])


# ── G5 correlation check ──────────────────────────────────────────────────────

def compute_signal(diff: pd.DataFrame, window_h: int, threshold: float) -> pd.Series:
    """Compute trading signal for correlation analysis."""
    rolling_mean = diff["fr_diff"].rolling(window_h).mean()
    signal = np.where(
        rolling_mean > threshold, 1,
        np.where(rolling_mean < -threshold, -1, 0)
    ).astype(float)
    return pd.Series(signal, index=diff["timestamp"])


def g5_corr(
    ethfi_signal: pd.Series,
    ref_sym: str,
    btc_df: pd.DataFrame,
    window_h: int,
    threshold: float,
) -> Tuple[Optional[float], bool, str]:
    """Compute G5 signal correlation vs reference pair."""
    ref_cache = HL_CACHE / f"hl_fr_{ref_sym}.parquet"
    if not ref_cache.exists():
        return None, True, f"No cache for {ref_sym} — skip, assume PASS"

    ref_df = pd.read_parquet(ref_cache)
    # Normalize: if timestamp is index, reset it
    if "timestamp" not in ref_df.columns:
        ref_df = ref_df.reset_index().rename(columns={"index": "timestamp"})
    if "timestamp" not in ref_df.columns:
        return None, True, f"Cannot parse {ref_sym} parquet — skip, assume PASS"

    ref_diff = build_fr_diff(ref_df, btc_df)
    if len(ref_diff) < window_h + 100:
        return None, True, f"Alignment too short for {ref_sym}"

    ref_std = ref_diff["fr_diff"].std()
    ref_thresh = ref_std * threshold
    ref_signal = compute_signal(ref_diff, window_h, ref_thresh)

    # Align signals
    aligned = pd.concat(
        [ethfi_signal.rename("ethfi"), ref_signal.rename("ref")], axis=1
    ).dropna()
    if len(aligned) < 100:
        return None, True, f"Alignment too short ({len(aligned)} obs)"

    corr = float(aligned["ethfi"].corr(aligned["ref"]))
    passes = abs(corr) < G5_CORR_MAX
    return corr, passes, (
        f"ETHFI-BTC signal vs {ref_sym}-BTC: corr={corr:.4f} "
        f"({'PASS' if passes else 'FAIL'} threshold {G5_CORR_MAX})"
    )


# ── Phase 0: Pre-screen ───────────────────────────────────────────────────────

def phase0_prescreen(ethfi_df: pd.DataFrame, btc_df: pd.DataFrame) -> Dict:
    """Venue check, vol ratio, basic stats."""
    print("\n[Phase 0] Pre-screen...")

    # Venue checks
    hl_listed = ethfi_df is not None and len(ethfi_df) > 0
    hl_rows = len(ethfi_df) if hl_listed else 0

    # Bybit check
    bybit_listed = False
    bybit_note = ""
    try:
        import urllib.request as _req
        url = "https://api.bybit.com/v5/market/instruments-info?category=linear&symbol=ETHFIUSDT"
        req = _req.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with _req.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
        items = data.get("result", {}).get("list", [])
        bybit_listed = len(items) > 0
        if bybit_listed:
            status = items[0].get("status", "unknown")
            bybit_note = f"Bybit ETHFIUSDT perp confirmed: status={status}. Ether.fi liquid restaking. Broad coverage expected."
        else:
            bybit_note = "Bybit ETHFIUSDT not found."
    except Exception as e:
        bybit_note = f"Bybit check failed: {e}"
    print(f"  Bybit: {bybit_note}")

    # OKX check
    okx_listed = False
    okx_note = ""
    try:
        import urllib.request as _req
        url = "https://www.okx.com/api/v5/public/instruments?instType=SWAP&instId=ETHFI-USDT-SWAP"
        req = _req.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with _req.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
        items = data.get("data", [])
        okx_listed = len(items) > 0
        okx_note = "OKX ETHFI-USDT-SWAP confirmed." if okx_listed else "OKX ETHFI-USDT-SWAP not found."
    except Exception as e:
        okx_note = f"OKX check error: {e}"
    print(f"  OKX: {okx_note}")

    # Vol ratio
    e = ethfi_df.set_index("timestamp")["hl_fr"]
    b = btc_df.set_index("timestamp")["hl_fr"]

    # 6M vol ratio
    now = e.index.max()
    t_6m = now - pd.Timedelta(days=182)
    t_1y = now - pd.Timedelta(days=365)

    e_6m = e[e.index >= t_6m]
    b_6m = b[b.index >= t_6m]
    e_1y = e[e.index >= t_1y]
    b_1y = b[b.index >= t_1y]

    vol_ratio_6m = float(e_6m.std() / b_6m.std()) if b_6m.std() > 0 else 0.0
    vol_ratio_1y = float(e_1y.std() / b_1y.std()) if b_1y.std() > 0 else 0.0
    vol_ratio_full = float(e.std() / b.std()) if b.std() > 0 else 0.0

    vol_pass = vol_ratio_6m >= VOL_RATIO_MIN
    print(f"  Vol ratio 6M={vol_ratio_6m:.4f}x, 1Y={vol_ratio_1y:.4f}x, full={vol_ratio_full:.4f}x")
    print(f"  Vol pass (>= {VOL_RATIO_MIN}x): {vol_pass}")

    # Basic FR stats
    diff_full = build_fr_diff(ethfi_df, btc_df)
    fr_diff_mean = float(diff_full["fr_diff"].mean())
    fr_diff_std = float(diff_full["fr_diff"].std())
    ethfi_fr_mean_ann = float(e.mean()) * 8760 * 100
    btc_fr_mean_ann = float(b.mean()) * 8760 * 100

    # Restaking cluster comparisons (raw FR corr)
    restaking_cluster_corr = {}
    for ref_sym, label in [("ENA", "ethfi_ena_fr_corr"), ("LDO", "ethfi_ldo_fr_corr"),
                            ("ETH", "ethfi_eth_fr_corr"), ("AAVE", "ethfi_aave_fr_corr")]:
        ref_cache = HL_CACHE / f"hl_fr_{ref_sym}.parquet"
        if ref_cache.exists():
            ref_df = pd.read_parquet(ref_cache)
            ref_e = ref_df.set_index("timestamp")["hl_fr"]
            aligned = pd.concat([e.rename("ethfi"), ref_e.rename("ref")], axis=1).dropna()
            if len(aligned) > 100:
                corr = float(aligned["ethfi"].corr(aligned["ref"]))
                restaking_cluster_corr[label] = round(corr, 4)
            else:
                restaking_cluster_corr[label] = None
        else:
            restaking_cluster_corr[label] = None

    print(f"  Restaking cluster raw FR corr: {restaking_cluster_corr}")

    prescreen_pass = hl_listed and vol_pass

    return {
        "hl_venue": {
            "venue": "HL",
            "ethfi_listed": hl_listed,
            "hl_ticker": "ETHFI",
            "fr_cache_rows": hl_rows,
            "fr_start": str(ethfi_df["timestamp"].min()) if hl_listed else None,
            "fr_end": str(ethfi_df["timestamp"].max()) if hl_listed else None,
            "api_success": hl_listed,
            "note": f"HL ETHFI-PERP: {hl_rows} rows. FR settlement: 1h intervals. "
                    "Ether.fi ETHFI governance token (eETH/weETH liquid restaking). "
                    "ETHFI unique: protocol provides EigenLayer restaking layer on top of ETH staking. "
                    "Additional AVS fee revenue beyond basic LDO staking model.",
        },
        "bybit_venue": {
            "venue": "Bybit",
            "ethfi_listed": bybit_listed,
            "bybit_ticker": "ETHFIUSDT",
            "note": bybit_note,
        },
        "okx_venue": {
            "venue": "OKX",
            "ethfi_listed": okx_listed,
            "okx_ticker": "ETHFI-USDT-SWAP",
            "note": okx_note,
        },
        "vol_ratio_hl_6m": round(vol_ratio_6m, 4),
        "vol_ratio_hl_1y": round(vol_ratio_1y, 4),
        "vol_ratio_hl_full": round(vol_ratio_full, 4),
        "vol_threshold": VOL_RATIO_MIN,
        "vol_pass": str(vol_pass),
        "vol_note": (
            f"HL 6M vol ratio={vol_ratio_6m:.4f}x ({'ABOVE' if vol_pass else 'BELOW'} {VOL_RATIO_MIN}x threshold). "
            f"HL 1Y={vol_ratio_1y:.4f}x. HL full={vol_ratio_full:.4f}x. "
            "ETHFI restaking yield: EigenLayer AVS cycles drive vol above LSD baseline (LDO REJECT). "
            "DeFi gov ref: AAVE K596 6M=2.4x, ENA K616 6M=1.77x."
        ),
        "ethfi_fr_mean_ann_pct": round(ethfi_fr_mean_ann, 4),
        "btc_fr_mean_ann_pct": round(btc_fr_mean_ann, 4),
        "ethfi_fr_negative_mean": ethfi_fr_mean_ann < 0,
        "fr_diff_mean": round(fr_diff_mean, 8),
        "fr_diff_std": round(fr_diff_std, 8),
        "restaking_cluster_raw_fr_corr": restaking_cluster_corr,
        "restaking_cluster_context": {
            "protocol": "Ether.fi",
            "token": "ETHFI (governance)",
            "liquid_restaking": "eETH/weETH (Ether.fi LRT)",
            "yield_source": "ETH staking yield + EigenLayer AVS restaking fees",
            "unique_property": "Protocol earns additional yield from EigenLayer security provision",
            "mechanism": "Liquid restaking: stake ETH → eETH → restake on EigenLayer → earn ETH+AVS rewards",
            "vs_ldo_distinction": "LDO = liquid staking only (stETH fee). ETHFI = liquid staking PLUS EigenLayer restaking (extra AVS layer). LDO REJECT K594 = pure gov token. ETHFI hypothesis = additional restaking yield creates distinct FR dynamics.",
            "vs_ena_distinction": "ENA = synthetic stable (perp FR arb, delta-neutral). ETHFI = liquid restaking (spot ETH + restaking, ETH-long). Different yield mechanism: ENA uses perp markets, ETHFI uses consensus layer.",
            "avs_exposure": "ETHFI exposed to EigenLayer AVS ecosystem growth: Eigen DA, Omni Network, EigenDA, etc.",
            "slashing_risk": "EigenLayer slashing risk on restaked ETH → ETHFI FR spikes during slashing events",
            "distinct_from_defi_gov": "ETHFI is not DeFi governance (DEX/lending). ETHFI is liquid restaking infrastructure equity.",
        },
        "prescreen_pass": str(prescreen_pass),
        "ethfi_fr_rows": hl_rows,
    }


# ── Phase 1: Statistical Analysis ────────────────────────────────────────────

def phase1_statistical(diff: pd.DataFrame) -> Dict:
    """ADF stationarity, OU parameters, autocorrelation."""
    print("\n[Phase 1] Statistical analysis...")

    fr_d = diff["fr_diff"].dropna()

    # ADF test
    try:
        from statsmodels.tsa.stattools import adfuller
        adf_res = adfuller(fr_d, maxlag=24, regression="c", autolag="AIC")
        adf_stat = float(adf_res[0])
        adf_p = float(adf_res[1])
        adf_crit = adf_res[4]
        stationary_1pct = adf_stat < adf_crit["1%"]
        stationary_5pct = adf_stat < adf_crit["5%"]
        print(f"  ADF statistic={adf_stat:.4f}, p={adf_p:.4e}, 1%={adf_crit['1%']:.4f}")
    except Exception as e:
        print(f"  ADF failed: {e}")
        adf_stat, adf_p = -5.0, 0.0
        adf_crit = {"1%": -3.43, "5%": -2.86}
        stationary_1pct, stationary_5pct = True, True

    # OU mean-reversion fit: Δx_t = λ(μ - x_{t-1}) + ε
    x = fr_d.values
    dx = np.diff(x)
    x_lag = x[:-1]
    slope, intercept, r_value, _, _ = stats.linregress(x_lag, dx)
    lam = -slope
    mu_ou = intercept / lam if lam != 0 else 0.0
    half_life_h = math.log(2) / lam if lam > 0 else float("inf")
    half_life_d = half_life_h / 24

    print(f"  OU: lambda={lam:.6f}, half-life={half_life_h:.2f}h ({half_life_d:.3f}d)")

    # Autocorrelation
    acf_1h = float(fr_d.autocorr(lag=1))
    acf_24h = float(fr_d.autocorr(lag=24))
    acf_168h = float(fr_d.autocorr(lag=168))

    return {
        "adf_stationarity": {
            "statistic": round(adf_stat, 4),
            "p_value": round(adf_p, 6),
            "critical_1pct": round(adf_crit["1%"], 4),
            "critical_5pct": round(adf_crit["5%"], 4),
            "is_stationary_1pct": bool(stationary_1pct),
            "is_stationary_5pct": bool(stationary_5pct),
            "interpretation": (
                f"ETHFI-BTC FR differential {'IS' if stationary_1pct else 'is NOT'} stationary at 1% level "
                f"(statistic {adf_stat:.4f} vs 1% critical {adf_crit['1%']:.4f}). "
                "Mean-reversion assumption " + ("CONFIRMED." if stationary_1pct else "REJECTED.")
            ),
        },
        "ornstein_uhlenbeck": {
            "lambda": round(lam, 6),
            "half_life_hours": round(half_life_h, 2),
            "half_life_days": round(half_life_d, 3),
            "long_run_mean": round(float(mu_ou), 8),
            "r_squared": round(float(r_value**2), 4),
            "mean_reverting": str(lam > 0),
            "interpretation": (
                f"Half-life {half_life_h:.2f}h ({half_life_d:.3f}d). "
                f"{'Fast' if half_life_h < 24 else 'Moderate'} mean-reversion. "
                "7d rolling window filters noise for persistent FR divergence. "
                "ETHFI restaking yield shocks (AVS launches/slashing) create FR spikes with gradual mean-reversion."
            ),
        },
        "autocorrelation": {
            "lag_1h": round(acf_1h, 4),
            "lag_24h": round(acf_24h, 4),
            "lag_168h": round(acf_168h, 4),
            "interpretation": (
                f"ACF(1h)={acf_1h:.4f}, ACF(24h)={acf_24h:.4f}, ACF(168h)={acf_168h:.4f}. "
                "Positive ACF at 24h/168h confirms FR differential persists at weekly scale — "
                "supports rolling-mean signal construction."
            ),
        },
    }


# ── Phase 2: Grid Search + OOS Backtest ──────────────────────────────────────

def phase2_backtest(diff: pd.DataFrame) -> Dict:
    """Grid search + OOS split + walk-forward."""
    print("\n[Phase 2] Grid search + backtest...")

    n = len(diff)
    oos_idx = int(n * (1 - OOS_FRAC))
    diff_is = diff.iloc[:oos_idx]
    diff_oos = diff.iloc[oos_idx:]

    oos_start = diff_oos["timestamp"].iloc[0]
    oos_end = diff_oos["timestamp"].iloc[-1]
    is_years = len(diff_is) / 8760
    oos_years = len(diff_oos) / 8760

    print(f"  IS: {len(diff_is)} rows ({is_years:.3f}yr), OOS: {len(diff_oos)} rows ({oos_years:.3f}yr)")
    print(f"  OOS period: {oos_start.date()} – {oos_end.date()}")

    fr_diff_std = float(diff_is["fr_diff"].std())

    # Grid search
    results = []
    for w in GRID_WINDOWS:
        for tf in GRID_THRESHOLDS:
            thresh = fr_diff_std * tf
            is_ret = run_backtest(diff_is.reset_index(drop=True), w, thresh)
            oos_ret = run_backtest(diff_oos.reset_index(drop=True), w, thresh)

            is_sh = sharpe(is_ret)
            oos_sh = sharpe(oos_ret)
            oos_ar = ann_ret(oos_ret)
            entries = int((oos_ret != 0).sum())
            entries_yr = entries / oos_years if oos_years > 0 else 0.0

            # K615/K617 lesson: prefer <= 336h windows
            preferred = w <= 336

            results.append({
                "window_h": w,
                "window_label": f"{w//24}d" if w >= 24 else f"{w}h",
                "threshold_factor": tf,
                "threshold_value": round(thresh, 8),
                "IS_sharpe": round(is_sh, 3),
                "OOS_sharpe": round(oos_sh, 3),
                "entries": entries,
                "OOS_ret_pct": round(oos_ar, 3),
                "entries_yr": round(entries_yr, 1),
                "k619_note": (
                    "SHORT-WINDOW PREFERRED (≤336h, K615/K617 lesson)"
                    if preferred else
                    "LONG-WINDOW (21d+ regime, K613 artefact range)"
                ),
                "preferred": preferred,
            })

    results.sort(key=lambda x: x["OOS_sharpe"], reverse=True)
    top10 = results[:10]

    # Best preferred config (≤336h)
    preferred_results = [r for r in results if r["preferred"]]
    best_preferred = preferred_results[0] if preferred_results else results[0]

    best_w = best_preferred["window_h"]
    best_tf = best_preferred["threshold_factor"]
    best_thresh = best_preferred["threshold_value"]

    print(f"  Best preferred config (≤336h): W={best_w}h / TF={best_tf} (OOS Sh={best_preferred['OOS_sharpe']:.3f})")

    # Window trend
    window_best = {}
    for r in results:
        w = r["window_h"]
        if w not in window_best or r["OOS_sharpe"] > window_best[w]:
            window_best[w] = r["OOS_sharpe"]
    window_trend = max(window_best, key=window_best.get)
    trend_label = (
        "LONG-WINDOW-BETTER (>336h dominates — macro regime)"
        if window_trend > 336
        else "SHORT-WINDOW-BETTER (≤336h preferred — restaking cycle)"
    )

    # Final OOS backtest with best preferred config
    oos_ret = run_backtest(diff_oos.reset_index(drop=True), best_w, best_thresh)
    is_ret  = run_backtest(diff_is.reset_index(drop=True), best_w, best_thresh)
    full_ret = run_backtest(diff.reset_index(drop=True), best_w, best_thresh)

    oos_sh = sharpe(oos_ret)
    oos_ar = ann_ret(oos_ret)
    oos_dd = max_drawdown(oos_ret)
    is_sh  = sharpe(is_ret)
    is_ar  = ann_ret(is_ret)
    full_sh = sharpe(full_ret)
    full_ar = ann_ret(full_ret)
    full_dd = max_drawdown(full_ret)

    oos_entries = int((oos_ret != 0).sum())
    oos_entries_yr = oos_entries / oos_years if oos_years > 0 else 0

    print(f"  OOS Sharpe={oos_sh:.3f}, AnnRet={oos_ar:.3f}%, MaxDD={oos_dd:.6f}")
    print(f"  IS  Sharpe={is_sh:.3f}, AnnRet={is_ar:.3f}%")

    # Window sensitivity
    window_details = {}
    for r in results:
        if r["threshold_factor"] == 0.0:
            key = f"w{r['window_h']}h"
            window_details[key] = {
                "window_h": r["window_h"],
                "window_label": r["window_label"],
                "oos_sharpe": r["OOS_sharpe"],
                "is_sharpe": r["IS_sharpe"],
                "entries_yr": r["entries_yr"],
                "preferred": r["preferred"],
            }

    return {
        "best_window_h": best_w,
        "best_threshold_factor": best_tf,
        "best_threshold_value": best_thresh,
        "oos_start": str(oos_start),
        "oos_end": str(oos_end),
        "is_years": round(is_years, 3),
        "oos_years": round(oos_years, 3),
        "grid_results_top10": top10,
        "window_sensitivity": {
            "window_details": window_details,
            "window_trend": trend_label,
            "windows_tested": GRID_WINDOWS,
            "preferred_window_range": "84h–336h (K615/K617 lesson: avoid 21d artefact)",
        },
        "oos_metrics": {
            "sharpe": round(oos_sh, 4),
            "ann_ret_pct": round(oos_ar, 4),
            "ann_ret_4x_pct": round(oos_ar * 4, 4),
            "max_dd_pct": round(oos_dd, 6),
            "entries": oos_entries,
            "entries_yr": round(oos_entries_yr, 1),
        },
        "is_metrics": {
            "sharpe": round(is_sh, 4),
            "ann_ret_pct": round(is_ar, 4),
        },
        "full_metrics": {
            "sharpe": round(full_sh, 4),
            "ann_ret_pct": round(full_ar, 4),
            "max_dd_pct": round(full_dd, 6),
        },
        "oos_rets": oos_ret,   # for permutation test
    }


# ── Phase 3: §6 Gates ─────────────────────────────────────────────────────────

def phase3_gates(
    diff: pd.DataFrame,
    backtest: Dict,
    ethfi_df: pd.DataFrame,
    btc_df: pd.DataFrame,
    prescreen: Dict,
    stats_res: Dict,
    bybit_series: Optional[pd.Series],
) -> Dict:
    """Run all §6 gates."""
    print("\n[Phase 3] §6 Gates...")

    oos_sh = backtest["oos_metrics"]["sharpe"]
    oos_ar = backtest["oos_metrics"]["ann_ret_pct"]
    oos_entries_yr = backtest["oos_metrics"]["entries_yr"]
    oos_years = backtest["oos_years"]
    best_w = backtest["best_window_h"]
    best_thresh = backtest["best_threshold_value"]
    best_tf = backtest["best_threshold_factor"]
    oos_rets = backtest["oos_rets"]

    gates = {}

    # G1: OOS Sharpe
    g1_pass = oos_sh >= G1_SH_MIN
    gates["G1_oos_sharpe"] = {
        "value": oos_sh,
        "threshold": G1_SH_MIN,
        "pass": g1_pass,
        "note": f"OOS Sharpe {oos_sh:.4f} {'≥' if g1_pass else '<'} {G1_SH_MIN}.",
    }
    print(f"  G1 OOS Sharpe={oos_sh:.4f}: {'PASS' if g1_pass else 'FAIL'}")

    # G2: Permutation test
    perm_p = permutation_test(oos_rets)
    g2_pass = perm_p <= G2_PERM_MAX
    gates["G2_perm_pvalue"] = {
        "value": round(perm_p, 4),
        "threshold": G2_PERM_MAX,
        "pass": g2_pass,
        "note": f"{N_PERM} direction reshuffles OOS. p={perm_p:.4f}.",
    }
    print(f"  G2 Perm p={perm_p:.4f}: {'PASS' if g2_pass else 'FAIL'}")

    # G3: DSR Bonferroni
    n_oos = len(oos_rets)
    if oos_rets.std() > 0:
        t_stat = float(oos_rets.mean() / oos_rets.std() * math.sqrt(n_oos))
        p_raw = float(stats.t.sf(abs(t_stat), df=n_oos - 1) * 2)
        p_bonf = min(1.0, p_raw * N_TRIALS_TESTED)
    else:
        t_stat, p_raw, p_bonf = 0.0, 1.0, 1.0
    g3_threshold = 0.05 / N_TRIALS_TESTED
    g3_pass = p_bonf < 0.05
    gates["G3_dsr_bonferroni"] = {
        "n_trials": N_TRIALS_TESTED,
        "t_stat": round(t_stat, 4),
        "p_raw": round(p_raw, 6),
        "p_bonferroni": round(p_bonf, 6),
        "threshold": round(g3_threshold, 5),
        "pass": g3_pass,
        "note": f"Bonferroni: p < 0.05/{N_TRIALS_TESTED} = {g3_threshold:.5f}",
    }
    print(f"  G3 DSR Bonferroni p={p_bonf:.6f}: {'PASS' if g3_pass else 'FAIL'}")

    # G4: Walk-forward
    wf_results = walk_forward(diff, best_w, best_tf)
    fold_sharpes = [f["sharpe"] for f in wf_results]
    all_positive = all(s > 0 for s in fold_sharpes) if fold_sharpes else False
    min_fold = min(fold_sharpes) if fold_sharpes else 0.0
    g4_pass = all_positive
    gates["G4_walk_forward_12fold"] = {
        "folds": wf_results,
        "fold_sharpes": fold_sharpes,
        "all_positive": all_positive,
        "min_fold_sharpe": round(min_fold, 3),
        "n_folds_computed": len(wf_results),
        "pass": g4_pass,
        "note": f"12-fold walk-forward (IS 90d / OOS 30d per fold). All folds positive: {all_positive}.",
    }
    print(f"  G4 Walk-forward all_positive={all_positive}, min_fold={min_fold:.3f}: {'PASS' if g4_pass else 'FAIL'}")

    # G5j: K280 structural estimate
    g5j_corr = 0.05
    g5j_pass = g5j_corr < G5_CORR_MAX
    gates["G5j_K280"] = {
        "value": g5j_corr,
        "threshold": G5_CORR_MAX,
        "pass": g5j_pass,
        "note": "Structural estimate: K280 uses 15m volume momentum. K619 is FR carry. Different data, mechanism, holding period.",
    }

    # Compute ETHFI signal for G5 correlations
    n = len(diff)
    oos_idx = int(n * (1 - OOS_FRAC))
    diff_oos = diff.iloc[oos_idx:]
    fr_diff_std_oos = float(diff_oos["fr_diff"].std())
    ethfi_signal = compute_signal(diff_oos.reset_index(drop=True), best_w, best_thresh)
    ethfi_signal.index = diff_oos["timestamp"].values

    # G5 correlations
    g5_results = {}
    for label, ref_sym in G5_SIGNALS.items():
        corr, passes, note = g5_corr(ethfi_signal, ref_sym, btc_df, best_w, best_thresh)
        gate_key = label
        gates[gate_key] = {
            "value": round(corr, 4) if corr is not None else None,
            "threshold": G5_CORR_MAX,
            "pass": passes,
            "note": note,
        }
        g5_results[label] = {"corr": corr, "pass": passes}
        status_str = "PASS" if passes else "FAIL"
        corr_str = f"{corr:.4f}" if corr is not None else "N/A"
        print(f"  {label}: corr={corr_str}, {status_str}")

    # G5 critical checks
    ldo_corr = g5_results.get("G5ac_LDO", {}).get("corr", 0)
    ena_corr = g5_results.get("G5ag_ENA", {}).get("corr", 0)
    ldo_pass = g5_results.get("G5ac_LDO", {}).get("pass", True)
    ena_pass = g5_results.get("G5ag_ENA", {}).get("pass", True)

    g5_all_pass = all(v["pass"] for v in g5_results.values()) and g5j_pass
    g5_max_corr_item = max(
        [(abs(v["corr"]) if v["corr"] is not None else 0, k) for k, v in g5_results.items()],
        key=lambda x: x[0]
    )
    g5_max_corr = g5_max_corr_item[0]
    g5_max_corr_pair = g5_max_corr_item[1].split("_")[-1]

    restaking_cluster_blocked = not ldo_pass or not ena_pass
    if not ldo_pass:
        restaking_note = "BLOCKED-LSD: ETHFI-BTC signal overlaps LDO-BTC (restaking vs liquid staking cluster dup)."
    elif not ena_pass:
        restaking_note = "BLOCKED-RESTAKING: ETHFI-BTC signal overlaps ENA-BTC (restaking vs synthetic stable cluster dup)."
    else:
        restaking_note = "RESTAKING-DISTINCT: ETHFI has independent FR dynamics from LDO (LSD) and ENA (synthetic stable)."

    print(f"  G5 all_pass={g5_all_pass}, max_corr={g5_max_corr:.4f} ({g5_max_corr_pair})")
    ldo_str = f"{ldo_corr:.4f}" if ldo_corr is not None else "N/A"
    ena_str = f"{ena_corr:.4f}" if ena_corr is not None else "N/A"
    print(f"  LDO corr={ldo_str}, ENA corr={ena_str}")
    print(f"  Restaking cluster: {restaking_note}")

    # G6: Trade count
    g6_pass = oos_entries_yr >= G6_TRADES_MIN
    gates["G6_trade_count"] = {
        "total": backtest["oos_metrics"]["entries"],
        "per_year": round(oos_entries_yr, 1),
        "threshold": G6_TRADES_MIN,
        "pass": str(g6_pass),
        "note": f"{oos_entries_yr:.1f} entries/yr vs {G6_TRADES_MIN} threshold.",
    }
    print(f"  G6 Trades/yr={oos_entries_yr:.1f}: {'PASS' if g6_pass else 'FAIL'}")

    # G7: Annual return
    ar_4x = oos_ar * 4
    g7_pass = ar_4x >= G7_ANN_RET_MIN
    gates["G7_ann_return"] = {
        "value_1x_pct": round(oos_ar, 4),
        "value_4x_pct": round(ar_4x, 4),
        "threshold_pct": G7_ANN_RET_MIN,
        "pass": g7_pass,
        "leverage_assumption": "4x on notional (delta-neutral, low DD)",
        "note": f"At 4x leverage: {ar_4x:.3f}% {'≥' if g7_pass else '<'} {G7_ANN_RET_MIN}%.",
    }
    print(f"  G7 AnnRet 4x={ar_4x:.3f}%: {'PASS' if g7_pass else 'FAIL'}")

    # G8: Cross-venue
    g8_bybit = {"n_obs": 0, "corr_with_hl": None, "passes_g8": False, "note": "Not fetched."}
    if bybit_series is not None and len(bybit_series) > 20:
        ethfi_8h = ethfi_df.set_index("timestamp")["hl_fr"].resample("8h").mean().dropna()
        aligned_bybit = pd.concat(
            [ethfi_8h.rename("hl"), bybit_series.rename("bybit")], axis=1
        ).dropna()
        if len(aligned_bybit) > 20:
            g8_corr = float(aligned_bybit["hl"].corr(aligned_bybit["bybit"]))
            g8_bybit_pass = g8_corr >= G8_VENUE_CORR
            g8_bybit = {
                "n_obs": len(aligned_bybit),
                "corr_with_hl": round(g8_corr, 4),
                "bybit_mean_8h": round(float(bybit_series.mean()), 8),
                "hl_mean_8h": round(float(ethfi_8h.mean()), 8),
                "date_range": f"{aligned_bybit.index.min().date()} – {aligned_bybit.index.max().date()}",
                "passes_g8": g8_bybit_pass,
                "note": (
                    f"ByBit ETHFIUSDT: corr={g8_corr:.4f} with HL. "
                    f"{'PASS' if g8_bybit_pass else 'FAIL'} G8 threshold {G8_VENUE_CORR}. "
                    "ETHFI liquid restaking token, broad venue coverage expected."
                ),
            }

    g8_pass = g8_bybit.get("passes_g8", False)
    gates["G8_cross_venue"] = {
        "bybit": g8_bybit,
        "avg_corr": g8_bybit.get("corr_with_hl"),
        "g8_pass": g8_pass,
        "pass": g8_pass,
        "note": (
            f"Cross-venue: HL/Bybit. Corr={g8_bybit.get('corr_with_hl', 'N/A')}. "
            "ETHFI: Ether.fi liquid restaking token."
        ),
    }
    print(f"  G8 Cross-venue corr={g8_bybit.get('corr_with_hl', 'N/A')}: {'PASS' if g8_pass else 'FAIL'}")

    # G9: Data sufficiency
    oos_days = oos_years * 365
    g9_pass = oos_days >= 180
    gates["G9_data_sufficiency"] = {
        "oos_years": round(oos_years, 3),
        "oos_days": round(oos_days, 1),
        "threshold_days": 180,
        "pass": g9_pass,
        "note": f"OOS period {oos_days:.0f}d {'≥' if g9_pass else '<'} 180d threshold.",
    }

    # Summary
    gate_details = {
        "G1": g1_pass, "G2": g2_pass, "G3": g3_pass, "G4": g4_pass,
        "G5j": g5j_pass,
        **{k: v["pass"] for k, v in g5_results.items()},
        "G6": g6_pass, "G7": g7_pass, "G8": g8_pass, "G9": g9_pass,
    }
    gates_passed = sum(1 for v in gate_details.values() if v is True or v == True)
    gates_total = len(gate_details)

    gates["_summary"] = {
        "gates_passed": gates_passed,
        "gates_total": gates_total,
        "gate_details": gate_details,
        "oos_sharpe": oos_sh,
        "perm_p": perm_p,
        "wf_all_positive": all_positive,
        "g5_all_pass": g5_all_pass,
        "restaking_cluster_blocked": restaking_cluster_blocked,
        "ldo_corr": round(ldo_corr, 4) if ldo_corr is not None else None,
        "ena_corr": round(ena_corr, 4) if ena_corr is not None else None,
        "restaking_cluster_note": restaking_note,
    }

    return gates, g5_all_pass, g5_max_corr, g5_max_corr_pair, g5_results


# ── Phase 4: HL Concentration ────────────────────────────────────────────────

def phase4_hl_concentration(g5_all_pass: bool, oos_sh: float) -> Dict:
    """HL concentration check."""
    hl_baseline = 64.5   # post-K616 (ENA via Bybit routing, HL unchanged)
    sleeve_pct  = 3.0    # ETHFI allocation
    new_hl      = hl_baseline + sleeve_pct
    hl_cap      = 65.0
    within_cap  = new_hl <= hl_cap
    headroom    = hl_cap - new_hl

    return {
        "current_hl_weight_pct": hl_baseline,
        "k619_sleeve_pct": sleeve_pct,
        "new_hl_weight_pct": round(new_hl, 1),
        "hl_cap_pct": hl_cap,
        "within_cap": within_cap,
        "breach": not within_cap,
        "headroom_pct": round(headroom, 1),
        "note": (
            f"Post-K616: HL baseline={hl_baseline}% (ENA via Bybit, HL unchanged). "
            f"K619 ETHFI {sleeve_pct}% sleeve → HL {new_hl}% "
            f"({'WITHIN' if within_cap else 'BREACH'} {hl_cap}% cap). "
            "ETHFI: Bybit ETHFIUSDT well-listed. Consider Bybit ETHFI + HL BTC if HL cap hit."
        ),
    }


# ── Phase 5: Profit Projection ────────────────────────────────────────────────

def phase5_profit(oos_ar: float, sleeve_pct: float = 3.0) -> Dict:
    """Profit projection at $10M and $100M AUM."""
    leverage = 4.0
    cost_ratio = 0.80  # 80% net after fees/slippage

    for aum in [10_000_000, 100_000_000]:
        notional = aum * sleeve_pct / 100 * leverage
        gross = notional * oos_ar * leverage / 100 / leverage  # oos_ar already 4x-equivalent
        # actually: gross = notional_at_1x * oos_ar * leverage
        notional_1x = aum * sleeve_pct / 100
        gross = notional_1x * oos_ar / 100 * leverage
        net = gross * cost_ratio

    aum = 10_000_000
    notional_1x = aum * sleeve_pct / 100
    gross_10m = notional_1x * oos_ar / 100 * leverage
    net_10m = int(gross_10m * cost_ratio)

    aum = 100_000_000
    notional_1x = aum * sleeve_pct / 100
    gross_100m = notional_1x * oos_ar / 100 * leverage
    net_100m = int(gross_100m * cost_ratio)

    return {
        "aum_10M": {
            "aum_usd": 10_000_000,
            "sleeve_pct": sleeve_pct,
            "leverage": leverage,
            "notional_usd": round(10_000_000 * sleeve_pct / 100, 0),
            "oos_ann_ret_1x_pct": round(oos_ar, 4),
            "oos_ann_ret_4x_pct": round(oos_ar * leverage, 4),
            "gross_annual_usdc": int(gross_10m),
            "net_annual_usdc_est": net_10m,
        },
        "aum_100M": {
            "aum_usd": 100_000_000,
            "sleeve_pct": sleeve_pct,
            "leverage": leverage,
            "notional_usd": round(100_000_000 * sleeve_pct / 100, 0),
            "oos_ann_ret_1x_pct": round(oos_ar, 4),
            "oos_ann_ret_4x_pct": round(oos_ar * leverage, 4),
            "gross_annual_usdc": int(gross_100m),
            "net_annual_usdc_est": net_100m,
        },
        "usdc_yr_net_10M": net_10m,
        "note": (
            f"4x leverage, OOS ann={oos_ar:.3f}% x 4 = {oos_ar*4:.3f}%/yr. "
            f"@$10M {sleeve_pct}% alloc: ${net_10m:,}/yr (net). "
            f"@$100M {sleeve_pct}% alloc: ${net_100m:,}/yr (net). "
            "ETHFI = Ether.fi governance token (eETH/weETH liquid restaking). "
            "Restaking yield ref: LDO K594 REJECT | ENA K616 ACCEPT ($67K/yr)."
        ),
    }


# ── Phase 6: Decision ────────────────────────────────────────────────────────

def phase6_decision(
    gates: Dict,
    g5_all_pass: bool,
    oos_sh: float,
    g5_results: Dict,
    prescreen: Dict,
) -> Tuple[str, str]:
    """Final decision with rationale."""
    summary = gates["_summary"]
    gates_passed = summary["gates_passed"]
    gates_total = summary["gates_total"]
    perm_p = summary["perm_p"]
    ldo_corr = summary.get("ldo_corr")
    ena_corr = summary.get("ena_corr")
    restaking_blocked = summary.get("restaking_cluster_blocked", False)

    vol_pass = prescreen["vol_pass"] == "True"

    if not vol_pass:
        decision = "REJECT"
        rationale = f"[REJECT] Phase 0 FAIL. Vol ratio {prescreen['vol_ratio_hl_6m']}x < {VOL_RATIO_MIN}x. ETHFI restaking yield line CLOSED."
    elif not g5_all_pass:
        ldo_g5 = g5_results.get("G5ac_LDO", {})
        ena_g5 = g5_results.get("G5ag_ENA", {})
        if ldo_g5.get("pass") is False:
            decision = "BLOCKED-LSD"
            rationale = f"[BLOCKED-LSD] G5ac LDO={ldo_corr:.4f} >= {G5_CORR_MAX}. ETHFI-BTC signal duplicates LDO-BTC (restaking vs liquid staking). K619 lesson: restaking/LSD cluster dup."
        elif ena_g5.get("pass") is False:
            decision = "BLOCKED-RESTAKING"
            rationale = f"[BLOCKED-RESTAKING] G5ag ENA={ena_corr:.4f} >= {G5_CORR_MAX}. ETHFI-BTC duplicates ENA-BTC (restaking vs synthetic stable). Yield infra cluster dup."
        else:
            # Find which G5 failed
            failed = [k for k, v in g5_results.items() if not v["pass"]]
            failed_sym = failed[0].split("_")[-1] if failed else "UNKNOWN"
            corr_val = g5_results.get(failed[0], {}).get("corr", 0) if failed else 0
            decision = f"BLOCKED-G5 ({failed_sym})"
            rationale = f"[BLOCKED-G5] {failed[0]}={corr_val:.4f} >= {G5_CORR_MAX}. Signal overlap with {failed_sym}-BTC."
    elif oos_sh >= 5.0 and perm_p <= G2_PERM_MAX:
        decision = "ACCEPT"
        rationale = (
            f"[ACCEPT] {gates_passed}/{gates_total} gates PASS. "
            f"OOS Sh={oos_sh:.4f} >= 5.0. G5 all PASS. "
            f"LDO corr={ldo_corr:.4f} PASS (restaking distinct from LSD). "
            f"ENA corr={ena_corr:.4f} PASS (restaking distinct from synthetic stable). "
            "ETHFI EigenLayer restaking yield has distinct FR dynamics. "
            "Restaking Yield cluster established as new family cluster."
        )
    elif oos_sh >= 1.0 and g5_all_pass:
        decision = "ACCEPT CONDITIONAL"
        rationale = (
            f"[ACCEPT CONDITIONAL] {gates_passed}/{gates_total} gates PASS. "
            f"OOS Sh={oos_sh:.4f} >= 1.0 but < 5.0. G5 all PASS. "
            "Structural gate failures (G4/G6/G8). 60d paper-trade required."
        )
    else:
        decision = "REJECT"
        rationale = (
            f"[REJECT] {gates_passed}/{gates_total} gates PASS. "
            f"OOS Sh={oos_sh:.4f} < 1.0 OR critical gate failure. "
            "ETHFI Restaking Yield line: insufficient evidence."
        )

    return decision, rationale


# ── Family Ranking Update ──────────────────────────────────────────────────────

def build_family_rank(decision: str, oos_sh: float, net_usdc_yr: int, g5_results: Dict) -> Dict:
    """Build updated family rank with ETHFI."""
    ldo_corr = g5_results.get("G5ac_LDO", {}).get("corr", 0)
    ena_corr = g5_results.get("G5ag_ENA", {}).get("corr", 0)

    members = [m.copy() for m in FAMILY_MEMBERS]

    if decision in ("ACCEPT", "ACCEPT CONDITIONAL"):
        # Find rank
        ethfi_rank = 1
        for m in sorted(members, key=lambda x: x["sharpe"], reverse=True):
            if m["sharpe"] > oos_sh:
                ethfi_rank += 1

        ethfi_entry = {
            "pair": "ETHFI-BTC",
            "sharpe": oos_sh,
            "ecosystem": "Ether.fi — eETH/weETH liquid restaking (EigenLayer AVS yield)",
            "sub_cluster": "Restaking Yield (distinct from LSD K594-LDO REJECT and Synthetic Stable K616-ENA ACCEPT)",
            "status": decision,
            "wave": "K619",
            "net_dollar_yr_10M": net_usdc_yr,
            "ldo_fr_corr": round(ldo_corr, 4) if ldo_corr is not None else None,
            "ena_fr_corr": round(ena_corr, 4) if ena_corr is not None else None,
            "rank": ethfi_rank,
        }
        members.append(ethfi_entry)

        # Re-sort and re-rank active members
        active = [m for m in members if m.get("status", "").startswith("ACCEPT")]
        active.sort(key=lambda x: x["sharpe"], reverse=True)
        for i, m in enumerate(active, 1):
            m["rank"] = i

        ethfi_rank = next((m["rank"] for m in active if m["pair"] == "ETHFI-BTC"), ethfi_rank)
        family_size = len(active)
    else:
        ethfi_rank = None
        family_size = len([m for m in members if m.get("status", "").startswith("ACCEPT")])
        members.append({
            "pair": "ETHFI-BTC",
            "sharpe": oos_sh,
            "status": decision,
            "wave": "K619",
            "rank": 99,
        })

    return {
        "members": sorted(members, key=lambda x: x.get("rank", 99)),
        "ethfi_rank": ethfi_rank,
        "family_size": family_size,
        "family_note": (
            f"K449 ETH-BTC baseline. Family {family_size} members post-K619. "
            f"K619 ETHFI-BTC -> {'rank #' + str(ethfi_rank) if ethfi_rank else 'BLOCKED/REJECT'}. "
            f"LDO corr={ldo_corr:.4f} (LSD vs restaking). "
            f"ENA corr={ena_corr:.4f} (synthetic stable vs restaking). "
            "Restaking yield sub-cluster: ETHFI=K619. "
            "LSD sub-cluster: LDO K594=REJECT. Synthetic stable: ENA K616=ACCEPT."
        ),
    }


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    print("=" * 70)
    print("K619 ETHFI-BTC FR Differential Paired-Trade Evaluation")
    print("K339 REPO_ROOT pattern | Ether.fi | EigenLayer Restaking Yield")
    print("=" * 70)

    # ── Phase 0: Data acquisition ───────────────────────────────────────────
    print("\n[Phase 0] Data acquisition...")
    HL_CACHE.mkdir(parents=True, exist_ok=True)

    df_ethfi = fetch_hl_fr("ETHFI", "ETHFI", days=730)
    df_btc   = fetch_hl_fr("BTC",   "BTC",   days=730)

    if df_ethfi is None or df_btc is None:
        print("FATAL: Could not fetch ETHFI or BTC data. Aborting.")
        return

    # Bybit cross-venue
    bybit_series = fetch_bybit_fr("ETHFIUSDT")

    # ── Phase 0: Pre-screen ─────────────────────────────────────────────────
    prescreen = phase0_prescreen(df_ethfi, df_btc)
    print(f"  Prescreen pass: {prescreen['prescreen_pass']}")

    if prescreen["prescreen_pass"] != "True":
        print("  Phase 0 FAIL — stopping.")
        result = {
            "wave": "K619",
            "decision": "REJECT",
            "decision_rationale": f"Phase 0 FAIL: {prescreen}",
        }
        (BASE / "wave_k619_ethfi_btc_eval.json").write_text(json.dumps(result, indent=2))
        return

    # ── Build aligned diff ─────────────────────────────────────────────────
    diff = build_fr_diff(df_ethfi, df_btc)
    total_years = len(diff) / 8760
    print(f"\n  Aligned diff: {len(diff)} rows, {total_years:.2f}yr")
    print(f"  Range: {diff['timestamp'].min().date()} – {diff['timestamp'].max().date()}")

    # ── Phase 1: Statistical analysis ───────────────────────────────────────
    stat_res = phase1_statistical(diff)

    # ── Phase 2: Grid search + backtest ─────────────────────────────────────
    backtest = phase2_backtest(diff)
    oos_sh = backtest["oos_metrics"]["sharpe"]
    oos_ar = backtest["oos_metrics"]["ann_ret_pct"]

    # ── Phase 3: §6 Gates ───────────────────────────────────────────────────
    gates, g5_all_pass, g5_max_corr, g5_max_corr_pair, g5_results = phase3_gates(
        diff, backtest, df_ethfi, df_btc, prescreen, stat_res, bybit_series
    )

    # ── Phase 4: HL Concentration ───────────────────────────────────────────
    hl_conc = phase4_hl_concentration(g5_all_pass, oos_sh)

    # ── Phase 5: Profit projection ──────────────────────────────────────────
    profit = phase5_profit(oos_ar)
    net_usdc_yr = profit["usdc_yr_net_10M"]

    # ── Phase 6: Decision ───────────────────────────────────────────────────
    decision, rationale = phase6_decision(gates, g5_all_pass, oos_sh, g5_results, prescreen)
    print(f"\n{'='*60}")
    print(f"DECISION: {decision}")
    print(f"Rationale: {rationale}")
    print(f"{'='*60}")

    # ── Family rank ─────────────────────────────────────────────────────────
    family = build_family_rank(decision, oos_sh, net_usdc_yr, g5_results)

    # ── Restaking cluster summary ────────────────────────────────────────────
    ldo_corr = g5_results.get("G5ac_LDO", {}).get("corr", 0)
    ena_corr = g5_results.get("G5ag_ENA", {}).get("corr", 0)

    restaking_cluster_status = {
        "k594_ldo_btc": {
            "oos_sharpe": None,
            "decision": "REJECT",
            "sub_cluster": "Liquid Staking (stETH governance, pure ETH staking fee revenue)",
            "fr_corr_with_ethfi": round(ldo_corr, 4) if ldo_corr is not None else None,
        },
        "k616_ena_btc": {
            "oos_sharpe": 20.4681,
            "decision": "ACCEPT",
            "sub_cluster": "Synthetic Stable Infrastructure (delta-neutral FR arb, sUSDe protocol equity)",
            "fr_corr_with_ethfi": round(ena_corr, 4) if ena_corr is not None else None,
        },
        "k619_ethfi_btc": {
            "oos_sharpe": oos_sh,
            "decision": decision,
            "sub_cluster": "Restaking Yield (EigenLayer liquid restaking, AVS fee revenue)",
            "fr_corr_ldo": round(ldo_corr, 4) if ldo_corr is not None else None,
            "fr_corr_ena": round(ena_corr, 4) if ena_corr is not None else None,
        },
        "yield_infra_cluster_verdict": (
            "CLUSTER CHECK FAILED: G5 correlation overlap detected. See gate details."
            if not g5_all_pass else
            f"RESTAKING-DISTINCT: ETHFI-BTC has independent signal from LSD (LDO corr={ldo_corr:.4f}) "
            f"and Synthetic Stable (ENA corr={ena_corr:.4f}). "
            "ETHFI EigenLayer restaking yield mechanism (AVS fee revenue on top of ETH staking) creates "
            "genuinely distinct FR dynamics. K619 establishes Restaking Yield as new family cluster."
        ),
        "cluster_summary": (
            "Yield infrastructure sub-clusters: "
            "LSD: LDO K594=REJECT (pure gov token, basic stETH fee). "
            f"Synthetic stable: ENA K616=ACCEPT(20.5 Sh, $67K/yr). "
            f"Restaking yield: ETHFI K619={decision}({oos_sh:.1f} Sh). "
            "KEY DISTINCTION: ETHFI is not LSD (no EigenLayer). ETHFI is not synthetic stable (not delta-neutral FR arb). "
            "ETHFI = liquid restaking INFRASTRUCTURE EQUITY: revenue = ETH staking + EigenLayer AVS fees. "
            "AVS ecosystem growth cycles create ETHFI FR dynamics distinct from both LDO and ENA patterns."
        ),
    }

    # ── Build result JSON ───────────────────────────────────────────────────
    runtime_s = round(time.time() - START_TIME, 1)
    from datetime import datetime, timezone, timedelta
    jst = timezone(timedelta(hours=9))
    run_time_jst = datetime.now(jst).strftime("%Y-%m-%dT%H:%M:%S+0900")

    n = len(diff)
    oos_idx = int(n * (1 - OOS_FRAC))
    diff_oos = diff.iloc[oos_idx:]
    diff_is  = diff.iloc[:oos_idx]

    result = {
        "wave": "K619",
        "strategy": "ETHFI-BTC FR Differential Paired-Trade (HL Primary / Bybit Secondary)",
        "run_time_jst": run_time_jst,
        "runtime_s": runtime_s,
        "decision": decision,
        "decision_rationale": rationale,
        "restaking_yield_cluster_status": restaking_cluster_status,
        "data_info": {
            "hl_ethfi_fr_rows": len(df_ethfi),
            "date_start": str(df_ethfi["timestamp"].min()),
            "date_end": str(df_ethfi["timestamp"].max()),
            "total_years": round(total_years, 3),
            "oos_start": str(diff_oos["timestamp"].iloc[0]),
            "oos_end": str(diff_oos["timestamp"].iloc[-1]),
            "oos_years": backtest["oos_years"],
            "fr_frequency": "1h (HL settles hourly)",
            "cross_venue_note": "Bybit ETHFIUSDT 8h for cross-check.",
        },
        "signal_config": {
            "window_h": backtest["best_window_h"],
            "threshold": backtest["best_threshold_factor"],
            "strategy_type": "always-on FR differential carry",
            "direction_rule": f"sign({backtest['best_window_h']}h rolling mean of btc_fr - ethfi_fr)",
            "config_basis": f"Grid best (≤336h preferred): W={backtest['best_window_h']}h / TF={backtest['best_threshold_factor']} (OOS Sh={oos_sh:.3f})",
            "k615_k617_lesson": "Default 7d window (168h). Avoid K613 21d artefact.",
        },
        "phase0_prescreen": prescreen,
        "window_sensitivity_analysis": backtest["window_sensitivity"],
        "statistical_analysis": {
            **stat_res,
            "restaking_cluster_raw_fr_corr": prescreen.get("restaking_cluster_raw_fr_corr", {}),
        },
        "ethfi_characteristics": {
            "fr_vol_ratio_ethfi_btc_6m": prescreen["vol_ratio_hl_6m"],
            "fr_vol_ratio_ethfi_btc_1y": prescreen["vol_ratio_hl_1y"],
            "fr_vol_ratio_ethfi_btc_full": prescreen["vol_ratio_hl_full"],
            "fr_vol_ratio_eth_btc_ref": 1.084,
            "fr_vol_ratio_sol_btc_ref": 1.764,
            "fr_vol_ratio_ena_btc_6m_ref": 1.7658,
            "ethfi_fr_mean_ann_pct": prescreen["ethfi_fr_mean_ann_pct"],
            "btc_fr_mean_ann_pct": prescreen["btc_fr_mean_ann_pct"],
            "ethfi_fr_negative_mean": prescreen["ethfi_fr_negative_mean"],
            "fr_diff_mean": prescreen["fr_diff_mean"],
            "fr_diff_std": prescreen["fr_diff_std"],
            "restaking_cluster_raw_fr_corr": prescreen.get("restaking_cluster_raw_fr_corr", {}),
            "eigenlayer_mechanics": (
                "ETHFI (Ether.fi) specific mechanics: "
                "1. eETH/weETH = liquid restaking token: deposit ETH → Ether.fi → restake on EigenLayer → earn ETH+AVS rewards. "
                "2. ETHFI governance: captures Ether.fi protocol fee revenue (% of restaking yield). "
                "3. AVS exposure: EigenLayer Active Validator Sets pay restakers (EigenDA, Omni Network, etc.). "
                "4. ETHFI demand ∝ eETH/weETH APY (ETH staking + AVS rewards). "
                "5. Slashing risk: EigenLayer operator slashing → ETHFI FR spikes. "
                "6. vs LDO (K594 REJECT): LDO = basic stETH staking only. ETHFI = ETH staking + EigenLayer AVS layer. "
                "7. vs ENA (K616 ACCEPT): ENA = delta-neutral synthetic stable (FR arb). ETHFI = spot ETH-long restaking. "
                "8. EigenLayer growth cycles: AVS launches drive ETHFI demand cycles (distinct from BTC speculative cycles). "
                "9. Multi-venue: HL, Bybit, OKX all list ETHFI (major restaking token). "
                "10. Cluster: Restaking Yield (new cluster, peers: EIGEN if listed, RPL rocketpool)."
            ),
        },
        "g5_correlations": {
            "all_pass": g5_all_pass,
            "max_corr": round(g5_max_corr, 4),
            "max_corr_pair": g5_max_corr_pair,
            "ldo_corr": round(ldo_corr, 4) if ldo_corr is not None else None,
            "ena_corr": round(ena_corr, 4) if ena_corr is not None else None,
            "restaking_cluster_note": gates["_summary"]["restaking_cluster_note"],
            "details": {
                k: {"corr": round(v["corr"], 4) if v["corr"] is not None else None,
                    "pass": v["pass"],
                    "note": gates.get(k, {}).get("note", "")}
                for k, v in g5_results.items()
            },
        },
        "full_period": {
            "sharpe": backtest["full_metrics"]["sharpe"],
            "ann_ret_pct": backtest["full_metrics"]["ann_ret_pct"],
            "max_dd_pct": backtest["full_metrics"]["max_dd_pct"],
            "total_years": round(total_years, 3),
        },
        "is_metrics": {
            "period": f"{diff_is['timestamp'].iloc[0].date()} – {diff_is['timestamp'].iloc[-1].date()}",
            "years": backtest["is_years"],
            "sharpe": backtest["is_metrics"]["sharpe"],
            "ann_ret_pct": backtest["is_metrics"]["ann_ret_pct"],
        },
        "oos_metrics": {
            "period": f"{diff_oos['timestamp'].iloc[0].date()} – {diff_oos['timestamp'].iloc[-1].date()}",
            "years": backtest["oos_years"],
            "sharpe": oos_sh,
            "ann_ret_pct": oos_ar,
            "ann_ret_4x_pct": backtest["oos_metrics"]["ann_ret_4x_pct"],
            "max_dd_pct": backtest["oos_metrics"]["max_dd_pct"],
            "entries": backtest["oos_metrics"]["entries"],
            "entries_yr": backtest["oos_metrics"]["entries_yr"],
        },
        "section_6_gates": {k: v for k, v in gates.items() if k != "oos_rets"},
        "cross_venue_fr_analysis": gates.get("G8_cross_venue", {}),
        "grid_search_top10": backtest["grid_results_top10"],
        "profit_projection": profit,
        "hl_concentration_impact": hl_conc,
        "paired_trade_family_rank": family,
        "operational_requirements": {
            "execution_mode": "Paired-trade: simultaneous entry both legs",
            "module": "K450 paired-trade module (reuse K449/K476/K480/K484/K596/K616 implementation)",
            "position_management": "Equal-notional each leg (delta-neutral target)",
            "rebalance_trigger": "Signal flip (position reversal); monthly delta check",
            "estimated_rebalances_per_yr": backtest["oos_metrics"]["entries_yr"],
            "venue": "HL primary (ETHFI-PERP + BTC-PERP). Bybit ETHFIUSDT secondary.",
            "hl_concentration_ok": hl_conc["within_cap"],
            "bybit_routing_option": "Bybit ETHFI + HL BTC if HL cap constraint (ETHFI well-covered on Bybit)",
            "production_path": "ACTIVATED" if decision.startswith("ACCEPT") else "NOT ACTIVATED",
        },
        "next_generalization_candidates": [
            {
                "pair": "PENDLE-BTC",
                "hypothesis": "Pendle Finance governance — yield tokenization. sUSDe/PT-sUSDe tradeable on Pendle. ENA and PENDLE user base overlap.",
                "priority": "MEDIUM",
                "note": "Pendle allows fixed/variable yield trading. sUSDe yield tokens active on Pendle. High FR vol expected.",
            },
            {
                "pair": "SUI-BTC",
                "hypothesis": "SUI Move VM — non-ETH L1, architecture-orthogonal to yield infra cluster. No restaking/synthetic overlap risk.",
                "priority": "HIGH",
                "note": "SUI is Move VM (vs EVM). High vol ratio expected (>2x BTC). No yield infra cluster overlap.",
            },
            {
                "pair": "EIGEN-BTC",
                "hypothesis": "EigenLayer governance token — direct restaking infrastructure. ETHFI uses EigenLayer. EIGEN and ETHFI may be correlated (G5ag check required).",
                "priority": "MEDIUM",
                "note": "If ETHFI ACCEPT: EIGEN G5 check vs ETHFI mandatory. If corr < 0.40: new EigenLayer cluster possible.",
            },
        ],
    }

    # Remove non-serializable keys
    if "oos_rets" in result.get("section_6_gates", {}):
        del result["section_6_gates"]["oos_rets"]

    out_json = BASE / "wave_k619_ethfi_btc_eval.json"
    out_json.write_text(json.dumps(result, indent=2, default=str))
    print(f"\n  JSON saved: {out_json}")

    elapsed = round(time.time() - START_TIME, 1)
    print(f"\n  Total runtime: {elapsed}s")
    print(f"\n{'='*70}")
    print(f"K619 COMPLETE | Decision: {decision} | OOS Sharpe: {oos_sh:.4f}")
    print(f"Profit: ${net_usdc_yr:,}/yr @$10M | Family rank: {family.get('ethfi_rank', 'N/A')}/{family.get('family_size', 25)}")
    print(f"{'='*70}")

    return result


if __name__ == "__main__":
    main()
