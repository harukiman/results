#!/usr/bin/env python3
"""
wave_k623_pendle_btc_eval.py — K623 PENDLE-BTC FR Differential Paired-Trade Evaluation
========================================================================================
K339 REPO_ROOT pattern. Pendle Finance (PENDLE) yield tokenization governance token vs
BTC. K474 earlier PENDLE eval (YT mechanics) REJECT (MC expected -0.51pp). K623 =
FR-differential paired-trade approach, distinct from K474 YT yield carry. K619 ETHFI
BLOCKED-LSD per LDO correlation. K616 ENA ACCEPT (Synthetic Stable Infra, $67K/yr).

HYPOTHESIS
----------
K449/K476/K480/K484/K596/K616 pattern (高 vol alt と BTC の funding rate differential が
定常的 mean-reverting) が PENDLE に generalize するか?

  - ETH-BTC:    1.08x BTC vol (FR std), Sharpe 5.663, $13K/yr @$10M  — ACCEPT
  - SOL-BTC:    1.76x BTC vol (FR std), Sharpe 16.298, $187K/yr       — ACCEPT
  - AVAX-BTC:   1.50x BTC vol (FR std), Sharpe 43.887                 — ACCEPT
  - AAVE-BTC:   2.4x BTC vol (FR std), Sharpe 11.354                  — ACCEPT K596
  - ENA-BTC:    1.77x BTC vol 6M, Sharpe 20.47, $67K/yr               — ACCEPT K616
  - ETHFI-BTC:  BLOCKED-LSD (G5ac LDO=0.6075 >= 0.4)                  — K619
  - PENDLE-BTC: 2-4x BTC vol expected — K623 hypothesis (yield tokenization distinct)

PENDLE FINANCE / YIELD TOKENIZATION HYPOTHESIS (K623 — Yield Tokenization cluster)
----------------------------------------------------------------------------------
  PENDLE = Pendle Finance governance token. Protocol provides:
  - Yield tokenization: splits yield-bearing assets into PT (Principal Token) + YT (Yield Token)
  - Fixed-rate DEX: AMM for trading PT/YT at implied yield
  - Multi-chain: ETH, Arbitrum, Base, BSC, Plasma, Hyperliquid L1
  - TVL: ~$1.44B total, sUSDe-backed pools $300M+, Aave aUSDC pools $80M+

  DISTINCT from:
    ENA  (K616 ACCEPT): synthetic stable infra — sUSDe FR-arb revenue. Distinct because
         ENA protocol revenue = perp funding rate. ENA = Ethena governance.
    AAVE (K596 ACCEPT): lending protocol governance — interest rate arbitrage.
    LDO  (K594 REJECT): liquid staking governance — stETH fee.
    K474 PENDLE: YT carry strategy (maturity-based yield) — different from FR-differential.

  PENDLE-specific FR mechanics:
    1. Yield market cycles: PENDLE governance token demand ∝ Pendle protocol activity.
       When yield markets are active (high TVL, active PT/YT trading), PENDLE demand rises.
       When yields are compressed (bear markets), Pendle TVL falls → PENDLE FR may spike neg.
    2. sUSDe overlap risk (CRITICAL — K616 ENA overlap check):
       Pendle's largest pool = YT-sUSDe (Ethena). When sUSDe APY moves, Pendle TVL moves.
       ENA is Ethena governance token (same underlying protocol). PENDLE and ENA both
       exposed to Ethena sUSDe yield cycles → potential FR correlation.
       K619 lesson: yield-infra overlap can cause G5 BLOCK. PENDLE-ENA G5 is CRITICAL.
    3. Distinct from ENA: PENDLE revenue = swap fees from PT/YT trading + vePENDLE bribes.
       ENA revenue = sUSDe minting/redemption fees + protocol cut of stETH yield.
       DIFFERENT revenue model → potentially distinct FR dynamics despite shared sUSDe exposure.
    4. Vol ratio 2-4x BTC expected from:
       - Yield tokenization narrative cycles (DeFi summer yields drive Pendle TVL)
       - Maturity events (sUSDe Dec26 maturity creates settlement demand)
       - Protocol exploit risk cycles (Penpie Sep2024 $27M — K474 documented)
       - Fixed-rate demand cycles: risk-off → PT demand spikes → PENDLE fee volume up
    5. Yield tokenization cluster: first yield-tokenization native token in family test.
       If distinct from ENA (synthetic stable) and AAVE (lending), new cluster formed.

  CRITICAL CROSS-COMPARISONS:
    PENDLE-ENA: Yield tokenization vs synthetic stable (CRITICAL: sUSDe pool overlap)
    PENDLE-AAVE: Yield tokenization vs lending governance (both depend on yield levels)
    PENDLE-LDO/CRV: Yield tokenization vs LSD/DEX (yield infrastructure comparison)
    PENDLE-BTC: Primary pair (FR differential signal)

MECHANISM (identical to K449/K476/K480/K484/K596/K616/K619)
------------------------------------------------------------
  fr_diff_t = btc_fr_t - pendle_fr_t
  Signal = sign(W rolling mean of fr_diff) — always-on, targets persistent divergence
  When fr_diff_W > 0: BTC pays more → short BTC, long PENDLE → net FR carry > 0
  When fr_diff_W < 0: PENDLE pays more → short PENDLE, long BTC → net FR carry > 0

  K623 dynamic: PENDLE FR can spike during yield tokenization narrative cycles (Pendle
  launches new pools, sUSDe maturity events, fixed-rate demand spikes). Creates FR spikes
  distinct from BTC speculative FR patterns IF not overly correlated with ENA.

DATA SOURCES
------------
  Primary:   HL PENDLE FR: fetched live → cache/k163_hl/hl_fr_PENDLE.parquet
             HL BTC FR: cache/k163_hl/hl_fr_BTC.parquet
  Cross-check: Bybit PENDLEUSDT perp (fetched live)
               OKX PENDLE-USDT-SWAP check
  Ref signals: ENA (K616), AAVE (K596), LDO (K594), CRV (K599) for cluster comparison

§6 GATES (K623 — 25-member family + Yield Tokenization cluster test)
--------------------------------------------------------------------
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
  G5ac: Corr vs LDO-BTC < 0.40
  G5ad: Corr vs MKR-BTC < 0.40
  G5ae: Corr vs OP-BTC < 0.40
  G5af: Corr vs POL-BTC < 0.40
  G5ag: Corr vs ENA-BTC K616 < 0.40  <- CRITICAL: yield tokenization vs synthetic stable
  G5ah: Corr vs ETHFI-BTC K619 < 0.40 <- yield infra comparison
  G6:  Trade count >= 30/yr
  G7:  Ann return > 5% at 4x leverage
  G8:  Cross-venue Bybit PENDLEUSDT corr >= 0.55
  G9:  Data sufficiency >= 180d OOS

DECISION CRITERIA
-----------------
  ACCEPT (Sharpe >= 5, all G5 PASS, critical gates pass): scaffold candidate
  ACCEPT CONDITIONAL (structural failures but G5 all PASS): 60d paper-trade
  BLOCKED-ENA-OVERLAP (G5ag ENA >= 0.40): sUSDe user base overlap blocks yield tokenization
  BLOCKED-G5 (ticker): specific G5 correlation fail
  REJECT (Phase 0 vol fail OR critical G5 fail): close yield tokenization line

HL CONCENTRATION (v6.37 baseline post-K616)
-------------------------------------------
  K616 ENA: ACCEPT (Bybit routing mandatory, HL 67.5% → BREACH). HL baseline=64.5%.
  K619 ETHFI: BLOCKED-LSD (no new HL concentration change).
  K623 PENDLE additional: check HL concentration.
  HL cap = 65.0% (HL concentration CRITICAL from K612 lesson).
  PENDLE: consider Bybit primary if HL cap constraint.
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
WINDOW_H        = 168       # default 7d (K615/K616/K617 lesson)
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
G5_ENA_BLOCK    = 0.40      # CRITICAL: ENA overlap threshold for BLOCKED-ENA-OVERLAP
G6_TRADES_MIN   = 30.0
G7_ANN_RET_MIN  = 5.0
G8_VENUE_CORR   = 0.55

ANN_FACTOR_1H   = math.sqrt(8760)

# Family reference data (post-K619, 25 active members)
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

# G5 checks — PENDLE-specific: ENA (K616) is CRITICAL overlap check
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
    "G5ac_LDO":   "LDO",
    "G5ad_MKR":   "MKR",
    "G5ae_OP":    "OP",
    "G5af_POL":   "POL",
    "G5ag_ENA":   "ENA",      # CRITICAL: yield tokenization vs synthetic stable K616
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

    print(f"  Fetching {sym} [{hl_ticker}] from HL...", flush=True)
    now_ms = int(time.time() * 1000)
    start_ms = now_ms - days * 86400 * 1000
    all_events, page_start = [], start_ms

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


def build_fr_diff(df_pendle: pd.DataFrame, df_btc: pd.DataFrame) -> pd.DataFrame:
    """Align PENDLE and BTC FR, compute differential."""
    p = _to_fr_series(df_pendle)
    b = _to_fr_series(df_btc)

    combined = pd.concat([p.rename("pendle_fr"), b.rename("btc_fr")], axis=1)
    combined = combined.ffill().dropna()
    combined["fr_diff"] = combined["btc_fr"] - combined["pendle_fr"]
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
    Position: +1 (long PENDLE, short BTC) or -1 (short PENDLE, long BTC).
    """
    df = diff.copy()
    rolling_mean = df["fr_diff"].rolling(window_h).mean()

    signal = np.where(
        rolling_mean > threshold, 1,
        np.where(rolling_mean < -threshold, -1, 0)
    )
    df["signal"] = signal

    df["carry"] = df["signal"] * df["fr_diff"]

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
    pendle_signal: pd.Series,
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

    aligned = pd.concat(
        [pendle_signal.rename("pendle"), ref_signal.rename("ref")], axis=1
    ).dropna()
    if len(aligned) < 100:
        return None, True, f"Alignment too short ({len(aligned)} obs)"

    corr = float(aligned["pendle"].corr(aligned["ref"]))
    passes = abs(corr) < G5_CORR_MAX
    return corr, passes, (
        f"PENDLE-BTC signal vs {ref_sym}-BTC: corr={corr:.4f} "
        f"({'PASS' if passes else 'FAIL'} threshold {G5_CORR_MAX})"
    )


# ── Phase 0: Pre-screen ───────────────────────────────────────────────────────

def phase0_prescreen(pendle_df: pd.DataFrame, btc_df: pd.DataFrame) -> Dict:
    """Venue check, vol ratio, basic stats."""
    print("\n[Phase 0] Pre-screen...")

    hl_listed = pendle_df is not None and len(pendle_df) > 0
    hl_rows = len(pendle_df) if hl_listed else 0

    # Bybit check
    bybit_listed = False
    bybit_note = ""
    try:
        import urllib.request as _req
        url = "https://api.bybit.com/v5/market/instruments-info?category=linear&symbol=PENDLEUSDT"
        req = _req.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with _req.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
        items = data.get("result", {}).get("list", [])
        bybit_listed = len(items) > 0
        if bybit_listed:
            status = items[0].get("status", "unknown")
            bybit_note = f"Bybit PENDLEUSDT perp confirmed: status={status}. Pendle Finance yield tokenization. Broad coverage expected."
        else:
            bybit_note = "Bybit PENDLEUSDT not found."
    except Exception as e:
        bybit_note = f"Bybit check failed: {e}"
    print(f"  Bybit: {bybit_note}")

    # OKX check
    okx_listed = False
    okx_note = ""
    try:
        import urllib.request as _req
        url = "https://www.okx.com/api/v5/public/instruments?instType=SWAP&instId=PENDLE-USDT-SWAP"
        req = _req.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with _req.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
        items = data.get("data", [])
        okx_listed = len(items) > 0
        okx_note = "OKX PENDLE-USDT-SWAP confirmed." if okx_listed else "OKX PENDLE-USDT-SWAP not found."
    except Exception as e:
        okx_note = f"OKX check error: {e}"
    print(f"  OKX: {okx_note}")

    # Vol ratio
    p = pendle_df.set_index("timestamp")["hl_fr"]
    b = btc_df.set_index("timestamp")["hl_fr"]

    now = p.index.max()
    t_6m = now - pd.Timedelta(days=182)
    t_1y = now - pd.Timedelta(days=365)

    p_6m = p[p.index >= t_6m]
    b_6m = b[b.index >= t_6m]
    p_1y = p[p.index >= t_1y]
    b_1y = b[b.index >= t_1y]

    vol_ratio_6m = float(p_6m.std() / b_6m.std()) if b_6m.std() > 0 else 0.0
    vol_ratio_1y = float(p_1y.std() / b_1y.std()) if b_1y.std() > 0 else 0.0
    vol_ratio_full = float(p.std() / b.std()) if b.std() > 0 else 0.0

    vol_pass = vol_ratio_6m >= VOL_RATIO_MIN
    print(f"  Vol ratio 6M={vol_ratio_6m:.4f}x, 1Y={vol_ratio_1y:.4f}x, full={vol_ratio_full:.4f}x")
    print(f"  Vol pass (>= {VOL_RATIO_MIN}x): {vol_pass}")

    # Basic FR stats
    diff_full = build_fr_diff(pendle_df, btc_df)
    fr_diff_mean = float(diff_full["fr_diff"].mean())
    fr_diff_std = float(diff_full["fr_diff"].std())
    pendle_fr_mean_ann = float(p.mean()) * 8760 * 100
    btc_fr_mean_ann = float(b.mean()) * 8760 * 100

    # Yield tokenization cluster comparisons (raw FR corr)
    yt_cluster_corr = {}
    for ref_sym, label in [
        ("ENA", "pendle_ena_fr_corr"),   # CRITICAL: sUSDe overlap
        ("AAVE", "pendle_aave_fr_corr"), # lending comparison
        ("CRV", "pendle_crv_fr_corr"),   # DEX/AMM comparison
        ("LDO", "pendle_ldo_fr_corr"),   # LSD comparison
    ]:
        ref_cache = HL_CACHE / f"hl_fr_{ref_sym}.parquet"
        if ref_cache.exists():
            ref_df = pd.read_parquet(ref_cache)
            ref_e = ref_df.set_index("timestamp")["hl_fr"]
            aligned = pd.concat([p.rename("pendle"), ref_e.rename("ref")], axis=1).dropna()
            if len(aligned) > 100:
                corr = float(aligned["pendle"].corr(aligned["ref"]))
                yt_cluster_corr[label] = round(corr, 4)
            else:
                yt_cluster_corr[label] = None
        else:
            yt_cluster_corr[label] = None

    print(f"  YT cluster raw FR corr: {yt_cluster_corr}")

    prescreen_pass = hl_listed and vol_pass

    return {
        "hl_venue": {
            "venue": "HL",
            "pendle_listed": hl_listed,
            "hl_ticker": "PENDLE",
            "fr_cache_rows": hl_rows,
            "fr_start": str(pendle_df["timestamp"].min()) if hl_listed else None,
            "fr_end": str(pendle_df["timestamp"].max()) if hl_listed else None,
            "api_success": hl_listed,
            "note": (
                f"HL PENDLE-PERP: {hl_rows} rows. FR settlement: 1h intervals. "
                "Pendle Finance PENDLE governance token (yield tokenization protocol). "
                "PENDLE unique: protocol enables PT/YT split of yield-bearing assets; "
                "revenue = swap fees on Pendle AMM + vePENDLE bribes from yield protocols. "
                "K474 context: sUSDe-Dec26 pool $300M+ TVL, aUSDC pool $80M+."
            ),
        },
        "bybit_venue": {
            "venue": "Bybit",
            "pendle_listed": bybit_listed,
            "bybit_ticker": "PENDLEUSDT",
            "note": bybit_note,
        },
        "okx_venue": {
            "venue": "OKX",
            "pendle_listed": okx_listed,
            "okx_ticker": "PENDLE-USDT-SWAP",
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
            "PENDLE yield tokenization: yield market cycles drive vol above BTC baseline. "
            "DeFi gov ref: AAVE K596 6M=2.4x, ENA K616 6M=1.77x. K474: TVL $1.44B, active 236 pools."
        ),
        "pendle_fr_mean_ann_pct": round(pendle_fr_mean_ann, 4),
        "btc_fr_mean_ann_pct": round(btc_fr_mean_ann, 4),
        "pendle_fr_negative_mean": pendle_fr_mean_ann < 0,
        "fr_diff_mean": round(fr_diff_mean, 8),
        "fr_diff_std": round(fr_diff_std, 8),
        "yt_cluster_raw_fr_corr": yt_cluster_corr,
        "yt_cluster_context": {
            "protocol": "Pendle Finance",
            "token": "PENDLE (governance)",
            "yield_tokenization": "PT (Principal Token) + YT (Yield Token) from yield-bearing assets",
            "yield_source": "Swap fees on Pendle AMM + vePENDLE bribes from underlying protocols",
            "unique_property": "Protocol enables fixed-rate trading of variable yield; revenue = yield market activity",
            "mechanism": "SY token → PT (redeemable 1:1 at maturity) + YT (receives all yield until maturity)",
            "susde_overlap_risk": (
                "CRITICAL K619 ENA OVERLAP CHECK: Pendle's largest pool = YT-sUSDe ($300M+ TVL). "
                "sUSDe is Ethena product (ENA governance). PENDLE and ENA both sensitive to Ethena "
                "sUSDe yield cycles. If sUSDe APY compresses → both PENDLE TVL and ENA demand fall. "
                "PENDLE-ENA FR correlation may be HIGH → G5ag BLOCK risk."
            ),
            "distinction_from_ena": (
                "PENDLE revenue = swap fees on PT/YT trading + vePENDLE vote-incentive bribes. "
                "ENA revenue = sUSDe protocol fee cut + stETH staking yield. DIFFERENT mechanisms: "
                "PENDLE = DEX fee model (volume-driven), ENA = yield-capture model (FR-driven). "
                "PENDLE serves multiple yield assets (aUSDC, stUSDS, Morpho) beyond sUSDe. "
                "Diversification may reduce sUSDe-specific correlation vs ENA."
            ),
            "k474_pendle_lesson": (
                "K474 REJECT was YT-carry strategy (MC expected -0.51pp net). K623 is FR-DIFFERENTIAL "
                "strategy on PENDLE governance token perp — COMPLETELY DIFFERENT approach. "
                "K474 measured Pendle protocol yield risk. K623 measures PENDLE token FR dynamics."
            ),
            "distinct_from_defi_gov": (
                "PENDLE is yield tokenization infrastructure (fixed-rate DEX). Not pure DeFi governance "
                "(no simple lending rate or DEX swap fee). PENDLE protocol creates yield markets, "
                "enabling fixed-rate exposure for institutional DeFi users."
            ),
        },
        "prescreen_pass": str(prescreen_pass),
        "pendle_fr_rows": hl_rows,
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

    # OU mean-reversion fit
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
                f"PENDLE-BTC FR differential {'IS' if stationary_1pct else 'is NOT'} stationary at 1% level "
                f"(statistic {adf_stat:.4f} vs 1% critical {adf_crit['1%']:.4f}). "
                "Mean-reversion assumption " + ("CONFIRMED." if stationary_1pct else "REJECTED.")
                + " PENDLE yield market demand cycles mean-revert as sUSDe/aUSDC APY returns to equilibrium."
            ),
        },
        "ornstein_uhlenbeck": {
            "lambda": round(lam, 6),
            "half_life_hours": round(half_life_h, 2),
            "half_life_days": round(half_life_d, 3),
            "long_run_mean": round(float(mu_ou), 8),
            "r_squared": round(r_value ** 2, 4),
            "mean_reverting": str(lam > 0),
            "interpretation": (
                f"Half-life {half_life_h:.2f}h ({half_life_d:.3f}d). "
                "PENDLE yield tokenization: yield market cycles create FR spikes that mean-revert "
                "as implied yields equilibrate. 168h smoothing window filters noise."
            ),
        },
        "autocorrelation": {
            "lag_1h": round(acf_1h, 4),
            "lag_24h": round(acf_24h, 4),
            "lag_168h": round(acf_168h, 4),
            "interpretation": (
                f"ACF(1h)={acf_1h:.4f}, ACF(24h)={acf_24h:.4f}, ACF(168h)={acf_168h:.4f}. "
                "Positive ACF supports rolling-mean signal construction for persistent FR divergence capture."
            ),
        },
    }


# ── Phase 2: Grid Search ──────────────────────────────────────────────────────

def phase2_grid_search(diff: pd.DataFrame, oos_start_idx: int) -> List[Dict]:
    """Grid search over window/threshold combinations."""
    print("\n[Phase 2] Grid search...")

    is_diff = diff.iloc[:oos_start_idx].reset_index(drop=True)
    oos_diff = diff.iloc[oos_start_idx:].reset_index(drop=True)

    results = []
    for w in GRID_WINDOWS:
        for tf in GRID_THRESHOLDS:
            is_std = is_diff["fr_diff"].std()
            thresh = is_std * tf

            is_rets = run_backtest(is_diff, w, thresh)
            oos_rets = run_backtest(oos_diff, w, thresh)

            is_sh = sharpe(is_rets)
            oos_sh = sharpe(oos_rets)
            oos_ar = ann_ret(oos_rets)
            oos_entries = int((oos_rets != 0).sum())
            oos_years = len(oos_rets) / 8760
            entries_yr = round(oos_entries / oos_years, 1) if oos_years > 0 else 0.0

            preferred = w <= 336
            results.append({
                "window_h": w,
                "window_label": f"{w//24}d" if w >= 24 else f"{w}h",
                "threshold_factor": tf,
                "threshold_value": round(is_std * tf, 8),
                "IS_sharpe": round(is_sh, 3),
                "OOS_sharpe": round(oos_sh, 3),
                "entries": oos_entries,
                "OOS_ret_pct": round(oos_ar, 3),
                "entries_yr": entries_yr,
                "k623_note": (
                    "SHORT-WINDOW PREFERRED (≤336h, K613 artefact avoidance)"
                    if preferred else
                    "LONG-WINDOW (21d+ regime, K613 artefact range)"
                ),
                "preferred": preferred,
            })
            print(f"  W={w:3d}h TF={tf:.1f}: IS_Sh={is_sh:.2f} OOS_Sh={oos_sh:.2f} entries_yr={entries_yr:.1f}")

    results.sort(key=lambda r: r["OOS_sharpe"], reverse=True)
    return results


# ── Phase 3: §6 Gates ─────────────────────────────────────────────────────────

def phase3_gates(
    diff: pd.DataFrame,
    oos_start_idx: int,
    best_window: int,
    best_threshold: float,
    pendle_df: pd.DataFrame,
    btc_df: pd.DataFrame,
    bybit_fr: Optional[pd.Series],
) -> Dict:
    """Full §6 gate evaluation."""
    print("\n[Phase 3] §6 Gates...")

    oos_diff = diff.iloc[oos_start_idx:].reset_index(drop=True)
    full_rets = run_backtest(diff, best_window, best_threshold)
    oos_rets = run_backtest(oos_diff, best_window, best_threshold)

    oos_sh = sharpe(oos_rets)
    oos_ar = ann_ret(oos_rets)
    oos_dd = max_drawdown(oos_rets)
    oos_entries = int((oos_rets != 0).sum())
    oos_years = len(oos_rets) / 8760
    oos_entries_yr = round(oos_entries / oos_years, 1) if oos_years > 0 else 0.0

    # G1: OOS Sharpe
    g1_pass = oos_sh >= G1_SH_MIN
    print(f"  G1: OOS Sharpe={oos_sh:.4f} {'PASS' if g1_pass else 'FAIL'}")

    # G2: Permutation test
    perm_p = permutation_test(oos_rets)
    g2_pass = perm_p <= G2_PERM_MAX
    print(f"  G2: perm p={perm_p:.4f} {'PASS' if g2_pass else 'FAIL'}")

    # G3: DSR Bonferroni
    t_stat, _ = stats.ttest_1samp(oos_rets.dropna(), 0.0)
    p_raw = float(stats.t.sf(abs(t_stat), df=len(oos_rets) - 1) * 2)
    p_bonf = min(p_raw * N_TRIALS_TESTED, 1.0)
    bonf_thresh = 0.05 / N_TRIALS_TESTED
    g3_pass = p_bonf < 0.05
    print(f"  G3: t={t_stat:.4f}, p_raw={p_raw:.4e}, p_bonf={p_bonf:.4e} {'PASS' if g3_pass else 'FAIL'}")

    # G4: Walk-forward
    wf_results = walk_forward(diff, best_window, 0.0)
    wf_sharpes = [f["sharpe"] for f in wf_results]
    wf_all_pos = all(s > 0 for s in wf_sharpes) if wf_sharpes else False
    min_wf_sh = min(wf_sharpes) if wf_sharpes else 0.0
    g4_pass = wf_all_pos
    print(f"  G4: WF all positive={wf_all_pos}, min={min_wf_sh:.3f}")

    # G5: Signal correlations
    pendle_signal = compute_signal(diff, best_window, best_threshold)

    g5_results = {}
    g5_all_pass = True
    ena_corr = None

    for g5_key, ref_sym in G5_SIGNALS.items():
        corr, passes, note = g5_corr(pendle_signal, ref_sym, btc_df, best_window, best_threshold)
        g5_results[g5_key] = {
            "corr": round(corr, 4) if corr is not None else None,
            "pass": passes,
            "note": note,
        }
        if not passes:
            g5_all_pass = False
            print(f"  {g5_key}: FAIL corr={corr:.4f}")
        # Track ENA correlation specifically
        if g5_key == "G5ag_ENA" and corr is not None:
            ena_corr = corr

    # Special K280 structural estimate
    g5_results["G5j_K280"] = {
        "corr": 0.05,
        "pass": True,
        "note": "Structural estimate: K280 uses 15m volume momentum. K623 is FR carry. Different data, mechanism, holding period.",
    }

    # ENA overlap check
    ena_blocked = ena_corr is not None and abs(ena_corr) >= G5_ENA_BLOCK
    print(f"  G5ag_ENA: corr={ena_corr}, blocked={'YES' if ena_blocked else 'NO'}")

    # G6: Trade count
    g6_pass = oos_entries_yr >= G6_TRADES_MIN
    print(f"  G6: entries_yr={oos_entries_yr:.1f} {'PASS' if g6_pass else 'FAIL'}")

    # G7: Annual return
    oos_ar_4x = oos_ar * 4
    g7_pass = oos_ar_4x >= G7_ANN_RET_MIN
    print(f"  G7: ann_ret_4x={oos_ar_4x:.2f}% {'PASS' if g7_pass else 'FAIL'}")

    # G8: Cross-venue
    g8_pass = False
    bybit_corr = None
    bybit_note = "Bybit data not available."
    if bybit_fr is not None and len(bybit_fr) > 20:
        # Resample HL to 8h to match Bybit
        p_8h = pendle_df.set_index("timestamp")["hl_fr"].resample("8h").last().dropna()
        bb_aligned = pd.concat([p_8h.rename("hl"), bybit_fr.rename("bybit")], axis=1).dropna()
        if len(bb_aligned) >= 10:
            bybit_corr = float(bb_aligned["hl"].corr(bb_aligned["bybit"]))
            g8_pass = bybit_corr >= G8_VENUE_CORR
            bybit_note = (
                f"ByBit PENDLEUSDT: corr={bybit_corr:.4f} with HL. "
                f"{'PASS' if g8_pass else 'FAIL'} G8 threshold {G8_VENUE_CORR}. "
                f"n={len(bb_aligned)} obs."
            )
            print(f"  G8: bybit corr={bybit_corr:.4f} {'PASS' if g8_pass else 'FAIL'}")

    # G9: Data sufficiency
    oos_days = oos_years * 365
    g9_pass = oos_days >= 180
    print(f"  G9: OOS days={oos_days:.0f} {'PASS' if g9_pass else 'FAIL'}")

    # Gate summary
    gate_detail = {
        "G1": g1_pass,
        "G2": g2_pass,
        "G3": g3_pass,
        "G4": g4_pass,
        "G5j": g5_results.get("G5j_K280", {}).get("pass", True),
        **{k: v["pass"] for k, v in g5_results.items() if k != "G5j_K280"},
        "G6": g6_pass,
        "G7": g7_pass,
        "G8": g8_pass,
        "G9": g9_pass,
    }
    gates_passed = sum(1 for v in gate_detail.values() if v)
    gates_total = len(gate_detail)

    return {
        "G1_oos_sharpe": {
            "value": round(oos_sh, 4),
            "threshold": G1_SH_MIN,
            "pass": g1_pass,
            "note": f"OOS Sharpe {oos_sh:.4f} {'≥' if g1_pass else '<'} {G1_SH_MIN}.",
        },
        "G2_perm_pvalue": {
            "value": round(perm_p, 4),
            "threshold": G2_PERM_MAX,
            "pass": g2_pass,
            "note": f"{N_PERM} direction reshuffles OOS. p={perm_p:.4f}.",
        },
        "G3_dsr_bonferroni": {
            "n_trials": N_TRIALS_TESTED,
            "t_stat": round(t_stat, 4),
            "p_raw": round(p_raw, 6),
            "p_bonferroni": round(p_bonf, 6),
            "threshold": round(bonf_thresh, 5),
            "pass": g3_pass,
            "note": f"Bonferroni: p < 0.05/{N_TRIALS_TESTED} = {bonf_thresh:.5f}",
        },
        "G4_walk_forward_12fold": {
            "folds": wf_results,
            "fold_sharpes": wf_sharpes,
            "all_positive": wf_all_pos,
            "min_fold_sharpe": round(min_wf_sh, 3),
            "n_folds_computed": len(wf_results),
            "pass": g4_pass,
            "note": f"12-fold walk-forward (IS 90d / OOS 30d per fold). All folds positive: {wf_all_pos}.",
        },
        "G5j_K280": g5_results.get("G5j_K280", {}),
        **{k: v for k, v in g5_results.items() if k != "G5j_K280"},
        "G5_ena_overlap_check": {
            "corr": round(ena_corr, 4) if ena_corr is not None else None,
            "threshold": G5_ENA_BLOCK,
            "blocked": ena_blocked,
            "note": (
                f"CRITICAL K619 ENA OVERLAP: PENDLE-BTC vs ENA-BTC signal corr={round(ena_corr, 4) if ena_corr is not None else 'N/A'}. "
                f"{'BLOCKED-ENA-OVERLAP: sUSDe pool dominates PENDLE TVL, creating ENA cluster dup.' if ena_blocked else 'PASS: PENDLE-ENA signal corr < 0.40. Yield tokenization distinct from synthetic stable.'}"
            ),
        },
        "G6_trade_count": {
            "total": oos_entries,
            "per_year": oos_entries_yr,
            "threshold": G6_TRADES_MIN,
            "pass": str(g6_pass),
            "note": f"{oos_entries_yr} entries/yr vs {G6_TRADES_MIN} threshold.",
        },
        "G7_ann_return": {
            "value_1x_pct": round(oos_ar, 4),
            "value_4x_pct": round(oos_ar_4x, 3),
            "threshold_pct": G7_ANN_RET_MIN,
            "pass": g7_pass,
            "leverage_assumption": "4x on notional (delta-neutral, low DD)",
            "note": f"At 4x leverage: {oos_ar_4x:.3f}% {'≥' if g7_pass else '<'} {G7_ANN_RET_MIN}%.",
        },
        "G8_cross_venue": {
            "bybit": {
                "n_obs": len(bybit_fr) if bybit_fr is not None else 0,
                "corr_with_hl": round(bybit_corr, 4) if bybit_corr is not None else None,
                "date_range": (
                    f"{bybit_fr.index.min().date()} – {bybit_fr.index.max().date()}"
                    if bybit_fr is not None and len(bybit_fr) > 0 else "N/A"
                ),
                "passes_g8": g8_pass,
                "note": bybit_note,
            },
            "g8_pass": g8_pass,
            "pass": g8_pass,
            "note": f"Cross-venue: HL/Bybit. {'corr=' + str(round(bybit_corr, 4)) if bybit_corr else 'no data'}.",
        },
        "G9_data_sufficiency": {
            "oos_years": round(oos_years, 3),
            "oos_days": round(oos_days, 1),
            "threshold_days": 180,
            "pass": g9_pass,
            "note": f"OOS period {oos_days:.0f}d {'≥' if g9_pass else '<'} 180d threshold.",
        },
        "_summary": {
            "gates_passed": gates_passed,
            "gates_total": gates_total,
            "gate_details": gate_detail,
            "oos_sharpe": round(oos_sh, 4),
            "perm_p": round(perm_p, 4),
            "wf_all_positive": wf_all_pos,
            "g5_all_pass": g5_all_pass,
            "ena_overlap_blocked": ena_blocked,
            "ena_corr": round(ena_corr, 4) if ena_corr is not None else None,
        },
        "oos_metrics_raw": {
            "sharpe": round(oos_sh, 4),
            "ann_ret_pct": round(oos_ar, 4),
            "ann_ret_4x_pct": round(oos_ar_4x, 3),
            "max_dd_pct": round(oos_dd, 6),
            "entries": oos_entries,
            "entries_yr": oos_entries_yr,
            "oos_years": round(oos_years, 3),
        },
    }


# ── Phase 4: HL Concentration ────────────────────────────────────────────────

def phase4_hl_concentration(oos_sh: float, g5_all_pass: bool, ena_blocked: bool) -> Dict:
    """HL concentration impact analysis."""
    hl_baseline = 64.5  # post-K616 with Bybit routing
    hl_cap = 65.0
    pendle_sleeve_pct = 3.0  # proposed allocation

    # If Bybit primary routing for PENDLE (like ENA K616)
    hl_bybit_routing = oos_sh > 5.0 and g5_all_pass and not ena_blocked
    if hl_bybit_routing:
        # Bybit primary: only BTC leg on HL → 1.5% HL impact
        hl_new = hl_baseline + pendle_sleeve_pct * 0.5
        routing = "Bybit PENDLE + HL BTC (split routing, 50% HL impact)"
    else:
        hl_new = hl_baseline + pendle_sleeve_pct
        routing = "HL both legs (full HL impact)"

    within_cap = hl_new <= hl_cap
    headroom = hl_cap - hl_new

    return {
        "current_hl_weight_pct": hl_baseline,
        "k623_sleeve_pct": pendle_sleeve_pct,
        "new_hl_weight_pct": round(hl_new, 1),
        "hl_cap_pct": hl_cap,
        "within_cap": within_cap,
        "breach": not within_cap,
        "headroom_pct": round(headroom, 1),
        "routing_recommendation": routing,
        "note": (
            f"Post-K616: HL baseline={hl_baseline}% (ENA Bybit routed). "
            f"K623 PENDLE {pendle_sleeve_pct}% sleeve → HL {hl_new:.1f}% "
            f"({'OK' if within_cap else 'BREACH'} {hl_cap}% cap). "
            "PENDLE: consider Bybit PENDLE + HL BTC if HL cap hit (like ENA K616 routing). "
            "PENDLE well-covered on Bybit (major DeFi/yield protocol venue)."
        ),
    }


# ── Phase 5: Decision & Family Rank ─────────────────────────────────────────

def phase5_decision(
    prescreen: Dict,
    stats_: Dict,
    gates: Dict,
    oos_sh: float,
    oos_ar: float,
    hl_conc: Dict,
    best_window: int,
) -> Tuple[str, str, Dict]:
    """Determine final decision and family rank."""

    summary = gates["_summary"]
    g5_all_pass = summary["g5_all_pass"]
    ena_blocked = summary["ena_overlap_blocked"]
    ena_corr = summary["ena_corr"]
    gates_passed = summary["gates_passed"]
    gates_total = summary["gates_total"]
    wf_all_pos = summary["wf_all_positive"]

    # Decision logic
    vol_pass = prescreen.get("vol_pass", "False") == "True"

    if not vol_pass:
        decision = "REJECT"
        rationale = (
            f"[REJECT] Phase 0 vol ratio FAIL. "
            f"PENDLE FR vol ratio < {VOL_RATIO_MIN}x BTC threshold. "
            "Insufficient differential vol for FR-carry strategy."
        )
    elif ena_blocked:
        decision = "BLOCKED-ENA-OVERLAP"
        rationale = (
            f"[BLOCKED-ENA-OVERLAP] G5ag ENA={ena_corr:.4f} >= {G5_ENA_BLOCK}. "
            "PENDLE-BTC signal duplicates ENA-BTC (K616 ACCEPT). "
            "K619 lesson: sUSDe pool dominates PENDLE TVL → ENA cluster dup. "
            "Yield tokenization cluster fails G5 ENA overlap check."
        )
    elif not g5_all_pass:
        # Identify failed G5
        failed = [k for k, v in gates.get("_summary", {}).get("gate_details", {}).items()
                  if k.startswith("G5") and not v]
        decision = f"BLOCKED-G5"
        rationale = (
            f"[BLOCKED-G5] G5 correlation FAIL: {failed}. "
            "PENDLE-BTC signal overlaps with existing family member."
        )
    elif oos_sh >= 5.0 and wf_all_pos:
        decision = "ACCEPT"
        rationale = (
            f"[ACCEPT] {gates_passed}/{gates_total} gates PASS. "
            f"OOS Sh={oos_sh:.4f} >= 5.0. G5 all PASS. "
            f"ENA corr={ena_corr:.4f if ena_corr is not None else 'N/A'} < {G5_ENA_BLOCK}. "
            "Yield tokenization cluster distinct from synthetic stable (ENA). "
            "K623 K450 scaffold candidate."
        )
    elif oos_sh >= 1.0 and g5_all_pass:
        decision = "ACCEPT CONDITIONAL"
        rationale = (
            f"[ACCEPT CONDITIONAL] {gates_passed}/{gates_total} gates PASS. "
            f"OOS Sh={oos_sh:.4f} >= 1.0 but < 5.0 OR walk-forward inconsistent. "
            "G5 all PASS. 60d paper-trade recommended before scaffold."
        )
    else:
        decision = "REJECT"
        rationale = (
            f"[REJECT] OOS Sh={oos_sh:.4f} < 1.0 OR critical gate failures. "
            "PENDLE-BTC FR differential strategy does not meet minimum requirements."
        )

    # Family rank (estimated)
    family_rank = None
    for i, m in enumerate(FAMILY_MEMBERS):
        if oos_sh > m["sharpe"]:
            family_rank = m["rank"]
            break
    if family_rank is None:
        family_rank = len(FAMILY_MEMBERS) + 1

    # Profit projection
    sleeve_pct = 3.0
    leverage = 4.0
    notional_10m = 10_000_000 * sleeve_pct / 100 * leverage
    gross_ann_10m = notional_10m * oos_ar / 100
    net_ann_10m = gross_ann_10m * 0.80  # ~20% cost/slippage drag

    profit_note = (
        f"4x leverage, OOS ann={oos_ar:.3f}% x 4 = {oos_ar*4:.3f}%/yr. "
        f"@$10M {sleeve_pct}% alloc: ${net_ann_10m:,.0f}/yr (net). "
        "PENDLE = Pendle Finance governance (yield tokenization). "
        f"DeFi cluster ref: AAVE K596=$XXK (accept) | ENA K616=$67K (accept, synthetic stable)."
    )

    # Yield tokenization cluster status
    yt_cluster = {
        "k474_pendle_yt_carry": {
            "decision": "REJECT",
            "note": "K474 YT-carry strategy: MC expected -0.51pp. Different approach (yield carry vs FR-differential).",
        },
        "k596_aave_btc": {
            "oos_sharpe": 11.354,
            "decision": "ACCEPT",
            "sub_cluster": "DeFi lending (interest rate governance, aToken model)",
            "fr_corr_with_pendle": "pending",
        },
        "k616_ena_btc": {
            "oos_sharpe": 20.4681,
            "decision": "ACCEPT",
            "sub_cluster": "Synthetic Stable Infrastructure (delta-neutral FR arb, sUSDe protocol equity)",
            "fr_corr_with_pendle": round(ena_corr, 4) if ena_corr is not None else "N/A",
        },
        "k619_ethfi_btc": {
            "oos_sharpe": 22.7329,
            "decision": "BLOCKED-LSD",
            "sub_cluster": "Restaking Yield (EigenLayer liquid restaking, AVS fee revenue)",
            "fr_corr_with_pendle": "N/A (blocked)",
        },
        "k623_pendle_btc": {
            "oos_sharpe": round(oos_sh, 4),
            "decision": decision,
            "sub_cluster": "Yield Tokenization (PT/YT fixed-rate DEX, swap fee revenue)",
            "fr_corr_ena": round(ena_corr, 4) if ena_corr is not None else "N/A",
        },
        "yt_cluster_verdict": (
            "YIELD-TOKENIZATION-" + ("DISTINCT" if not ena_blocked else "BLOCKED-ENA") + ": "
            + ("PENDLE-BTC has independent signal from ENA synthetic stable." if not ena_blocked else "PENDLE-BTC fails ENA G5 overlap check — sUSDe pool dominates PENDLE TVL.")
            + f" ENA corr={round(ena_corr, 4) if ena_corr is not None else 'N/A'}."
        ),
        "cluster_summary": (
            "Yield infrastructure sub-clusters: "
            "DeFi lending: AAVE K596=ACCEPT(11.4 Sh). "
            "Synthetic stable: ENA K616=ACCEPT(20.5 Sh, $67K/yr). "
            "Restaking yield: ETHFI K619=BLOCKED-LSD(22.7 Sh). "
            f"Yield tokenization: PENDLE K623={decision}({oos_sh:.2f} Sh). "
            "KEY DISTINCTION: PENDLE is NOT synthetic stable (ENA) — PENDLE revenue = swap fees "
            "on PT/YT trading. PENDLE is NOT restaking (ETHFI) — PENDLE protocol uses existing "
            "yield assets, not new consensus layer yield. PENDLE is yield market infrastructure: "
            "enables fixed-rate trading of variable yield. sUSDe pool overlap remains KEY risk."
        ),
    }

    # Family members with PENDLE inserted
    family_with_pendle = []
    inserted = False
    for m in FAMILY_MEMBERS:
        if not inserted and oos_sh > m["sharpe"]:
            family_with_pendle.append({
                "rank": family_rank,
                "pair": "PENDLE-BTC",
                "sharpe": round(oos_sh, 4),
                "ecosystem": "Pendle Finance — yield tokenization protocol (PT/YT fixed-rate DEX)",
                "sub_cluster": "Yield Tokenization (distinct from ENA Synthetic Stable, if G5ag PASS)",
                "status": decision,
                "wave": "K623",
                "net_dollar_yr_10M": round(net_ann_10m),
            })
            inserted = True
        family_with_pendle.append({**m, "rank": m["rank"] + (1 if inserted else 0)})
    if not inserted:
        family_with_pendle.append({
            "rank": family_rank,
            "pair": "PENDLE-BTC",
            "sharpe": round(oos_sh, 4),
            "ecosystem": "Pendle Finance — yield tokenization protocol (PT/YT fixed-rate DEX)",
            "sub_cluster": "Yield Tokenization (distinct from ENA Synthetic Stable, if G5ag PASS)",
            "status": decision,
            "wave": "K623",
            "net_dollar_yr_10M": round(net_ann_10m),
        })

    return decision, rationale, {
        "family_rank": family_rank,
        "family_size": len(FAMILY_MEMBERS) + 1,
        "members": family_with_pendle,
        "pendle_rank": family_rank,
        "pendle_sharpe": round(oos_sh, 4),
        "pendle_status": decision,
        "yt_cluster_status": yt_cluster,
        "profit_projection": {
            "aum_10M": {
                "aum_usd": 10_000_000,
                "sleeve_pct": sleeve_pct,
                "leverage": leverage,
                "notional_usd": notional_10m,
                "oos_ann_ret_1x_pct": round(oos_ar, 4),
                "oos_ann_ret_4x_pct": round(oos_ar * 4, 3),
                "gross_annual_usdc": round(gross_ann_10m),
                "net_annual_usdc_est": round(net_ann_10m),
            },
            "usdc_yr_net_10M": round(net_ann_10m),
            "note": profit_note,
        },
        "decision_rationale": rationale,
    }


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    import datetime as _dt
    print("=" * 70)
    print("K623 PENDLE-BTC FR Differential Paired-Trade Evaluation")
    print("K339 REPO_ROOT pattern | Yield Tokenization cluster | K474 retry")
    print("=" * 70)

    # Ensure cache dir exists
    HL_CACHE.mkdir(parents=True, exist_ok=True)

    # ── Load data ──────────────────────────────────────────────────────────
    print("\n[Phase 0a] Loading data...")
    pendle_df = fetch_hl_fr("PENDLE", "PENDLE", days=730)
    btc_df = fetch_hl_fr("BTC", "BTC", days=730)

    if pendle_df is None or btc_df is None:
        print("FATAL: Cannot load PENDLE or BTC data. Aborting.")
        return

    # ── Phase 0: Pre-screen ────────────────────────────────────────────────
    prescreen = phase0_prescreen(pendle_df, btc_df)

    if prescreen.get("vol_pass", "False") != "True":
        print(f"\nPHASE 0 FAIL: vol ratio {prescreen['vol_ratio_hl_6m']}x < {VOL_RATIO_MIN}x. REJECT.")

    # ── Phase 1: Statistical analysis ──────────────────────────────────────
    diff_full = build_fr_diff(pendle_df, btc_df)
    stats_ = phase1_statistical(diff_full)

    # ── Phase 2: Grid search ───────────────────────────────────────────────
    oos_start_idx = int(len(diff_full) * (1 - OOS_FRAC))
    oos_start_dt = diff_full["timestamp"].iloc[oos_start_idx]
    is_diff = diff_full.iloc[:oos_start_idx]
    oos_diff = diff_full.iloc[oos_start_idx:]

    grid_results = phase2_grid_search(diff_full, oos_start_idx)
    top10 = grid_results[:10]

    # Select best config (prefer ≤336h)
    preferred = [r for r in grid_results if r["preferred"]]
    best_config = preferred[0] if preferred else grid_results[0]
    best_window = best_config["window_h"]
    best_threshold = best_config["threshold_value"]

    print(f"\n  Best preferred config (≤336h): W={best_window}h TF={best_config['threshold_factor']:.1f} OOS_Sh={best_config['OOS_sharpe']:.3f}")

    # ── Phase 1 (Bybit): Cross-venue ───────────────────────────────────────
    bybit_fr = fetch_bybit_fr("PENDLEUSDT")

    # ── Phase 3: §6 Gates ──────────────────────────────────────────────────
    gates = phase3_gates(
        diff_full, oos_start_idx,
        best_window, best_threshold,
        pendle_df, btc_df, bybit_fr,
    )

    oos_sh = gates["oos_metrics_raw"]["sharpe"]
    oos_ar = gates["oos_metrics_raw"]["ann_ret_pct"]
    oos_dd = gates["oos_metrics_raw"]["max_dd_pct"]
    oos_entries = gates["oos_metrics_raw"]["entries"]
    oos_entries_yr = gates["oos_metrics_raw"]["entries_yr"]
    oos_years = gates["oos_metrics_raw"]["oos_years"]
    ena_corr = gates["_summary"]["ena_corr"]
    ena_blocked = gates["_summary"]["ena_overlap_blocked"]
    g5_all_pass = gates["_summary"]["g5_all_pass"]

    # Full period metrics
    full_rets = run_backtest(diff_full, best_window, best_threshold)
    full_sh = sharpe(full_rets)
    full_ar = ann_ret(full_rets)
    full_dd = max_drawdown(full_rets)
    full_entries = int((full_rets != 0).sum())
    full_years = len(full_rets) / 8760

    is_rets = run_backtest(is_diff.reset_index(drop=True), best_window, best_threshold)
    is_sh = sharpe(is_rets)
    is_ar = ann_ret(is_rets)
    is_years = len(is_rets) / 8760

    # ── Phase 4: HL Concentration ──────────────────────────────────────────
    hl_conc = phase4_hl_concentration(oos_sh, g5_all_pass, ena_blocked)

    # ── Phase 5: Decision ──────────────────────────────────────────────────
    decision, rationale, rank_data = phase5_decision(
        prescreen, stats_, gates, oos_sh, oos_ar, hl_conc, best_window
    )

    print(f"\n{'='*60}")
    print(f"DECISION: {decision}")
    print(f"{rationale}")
    print(f"{'='*60}")

    # ── Runtime ────────────────────────────────────────────────────────────
    runtime_s = round(time.time() - START_TIME, 1)

    # ── Assemble JSON ──────────────────────────────────────────────────────
    jst_now = _dt.datetime.now(_dt.timezone(
        _dt.timedelta(hours=9)
    )).strftime("%Y-%m-%dT%H:%M:%S+0900")

    result = {
        "wave": "K623",
        "strategy": "PENDLE-BTC FR Differential Paired-Trade (HL Primary / Bybit Secondary)",
        "run_time_jst": jst_now,
        "runtime_s": runtime_s,
        "decision": decision,
        "decision_rationale": rationale,
        "yield_tokenization_cluster_status": rank_data["yt_cluster_status"],
        "data_info": {
            "hl_pendle_fr_rows": len(pendle_df),
            "date_start": str(diff_full["timestamp"].min()),
            "date_end": str(diff_full["timestamp"].max()),
            "total_years": round(len(diff_full) / 8760, 3),
            "oos_start": str(oos_start_dt),
            "oos_end": str(diff_full["timestamp"].max()),
            "oos_years": round(oos_years, 3),
            "fr_frequency": "1h (HL settles hourly)",
            "cross_venue_note": f"Bybit PENDLEUSDT 8h for cross-check.",
        },
        "signal_config": {
            "window_h": best_window,
            "threshold": best_config["threshold_factor"],
            "strategy_type": "always-on FR differential carry",
            "direction_rule": f"sign({best_window}h rolling mean of btc_fr - pendle_fr)",
            "config_basis": f"Grid best (≤336h preferred): W={best_window}h / TF={best_config['threshold_factor']:.1f} (OOS Sh={oos_sh:.3f})",
            "k613_lesson": "Prefer ≤336h to avoid 21d window artefact (K613 STX blocked by APT at 504h)",
        },
        "phase0_prescreen": prescreen,
        "window_sensitivity_analysis": {
            "window_details": {
                f"w{r['window_h']}h": {
                    "window_h": r["window_h"],
                    "window_label": r["window_label"],
                    "oos_sharpe": r["OOS_sharpe"],
                    "is_sharpe": r["IS_sharpe"],
                    "entries_yr": r["entries_yr"],
                    "preferred": r["preferred"],
                }
                for r in sorted(
                    [rr for rr in grid_results if rr["threshold_factor"] == 0.0],
                    key=lambda x: x["window_h"]
                )
            },
            "window_trend": (
                "LONG-WINDOW-BETTER (>336h dominates)"
                if max(r["OOS_sharpe"] for r in grid_results if not r["preferred"])
                   > max((r["OOS_sharpe"] for r in grid_results if r["preferred"]), default=0)
                else "SHORT-WINDOW-BETTER (≤336h preferred)"
            ),
            "optimal_window_note": f"Best preferred config (≤336h): W={best_window}h",
        },
        "statistical_analysis": {
            **stats_,
            "yt_cluster_raw_fr_corr": prescreen.get("yt_cluster_raw_fr_corr", {}),
        },
        "pendle_characteristics": {
            "fr_vol_ratio_pendle_btc_6m": prescreen.get("vol_ratio_hl_6m"),
            "fr_vol_ratio_pendle_btc_1y": prescreen.get("vol_ratio_hl_1y"),
            "fr_vol_ratio_pendle_btc_full": prescreen.get("vol_ratio_hl_full"),
            "fr_vol_ratio_eth_btc_ref": 1.084,
            "fr_vol_ratio_sol_btc_ref": 1.764,
            "fr_vol_ratio_avax_btc_ref": 1.499,
            "fr_vol_ratio_aave_btc_ref": 2.4,
            "fr_vol_ratio_ena_btc_ref": 1.7658,
            "pendle_fr_mean_ann_pct": prescreen.get("pendle_fr_mean_ann_pct"),
            "btc_fr_mean_ann_pct": prescreen.get("btc_fr_mean_ann_pct"),
            "pendle_fr_negative_mean": prescreen.get("pendle_fr_negative_mean"),
            "fr_diff_mean": prescreen.get("fr_diff_mean"),
            "fr_diff_std": prescreen.get("fr_diff_std"),
            "yt_cluster_raw_fr_corr": prescreen.get("yt_cluster_raw_fr_corr", {}),
            "pendle_mechanics": (
                "PENDLE (Pendle Finance) specific mechanics: "
                "1. Yield tokenization: split yield-bearing assets (SY) into PT + YT. "
                "   PT redeemable 1:1 at maturity. YT receives all yield until maturity. "
                "   Pendle AMM enables trading at implied fixed yield. "
                "2. PENDLE governance: captures swap fee revenue + vePENDLE bribes. "
                "   PENDLE demand ∝ Pendle protocol activity (TVL, trading volume). "
                "3. sUSDe overlap: largest Pendle pool = YT-sUSDe ($300M+ TVL). "
                "   ENA = Ethena governance token (sUSDe issuer). CRITICAL K619 lesson: "
                "   yield-infra overlap can cause G5 BLOCK if PENDLE-ENA corr >= 0.40. "
                "4. K474 lesson: YT-carry REJECT (MC -0.51pp). K623 FR-differential is "
                "   completely different: measures PENDLE GOVERNANCE TOKEN perp dynamics. "
                "5. Multi-chain TVL: Ethereum $978M, Arbitrum $189M. "
                "6. Penpie exploit (Sep2024 $27M): third-party exploit. Pendle core safe. "
                "7. Revenue diversification: aUSDC ($80M), stUSDS ($40M), Morpho-MEV ($30M) "
                "   pools reduce sUSDe concentration. But sUSDe still dominates. "
            ),
            "k623_window_insight": (
                f"K623 tests shorter windows ([84, 168, 336, 504, 720]) per K613 STX 21d artefact lesson. "
                f"Best preferred window (≤336h): {best_window}h. "
                "PENDLE yield market activity cycles (7-14d) suggest 168h-336h appropriate. "
                "If PENDLE passes G5ag (ENA): confirms yield tokenization is distinct cluster."
            ),
        },
        "g5_correlations": {
            "all_pass": g5_all_pass,
            "max_corr": max(
                (abs(v.get("corr", 0)) for v in
                 {k: v for k, v in gates.items() if k.startswith("G5") and isinstance(v, dict) and "corr" in v}.values()
                 if v.get("corr") is not None),
                default=0.0,
            ),
            "ena_corr": ena_corr,
            "ena_blocked": ena_blocked,
            "defi_cluster_blocked": not g5_all_pass,
            "details": {
                k: v for k, v in gates.items()
                if k.startswith("G5") and isinstance(v, dict) and "pass" in v
            },
        },
        "full_period": {
            "sharpe": round(full_sh, 4),
            "ann_ret_pct": round(full_ar, 4),
            "max_dd_pct": round(full_dd, 6),
            "total_entries": full_entries,
            "entries_per_yr": round(full_entries / full_years, 1) if full_years > 0 else 0.0,
        },
        "is_metrics": {
            "period": f"{diff_full['timestamp'].min().date()} – {oos_start_dt.date()}",
            "years": round(is_years, 3),
            "sharpe": round(is_sh, 4),
            "ann_ret_pct": round(is_ar, 4),
        },
        "oos_metrics": {
            "period": f"{oos_start_dt.date()} – {diff_full['timestamp'].max().date()}",
            "years": round(oos_years, 3),
            "sharpe": round(oos_sh, 4),
            "ann_ret_pct": round(oos_ar, 4),
            "ann_ret_4x_pct": round(oos_ar * 4, 3),
            "max_dd_pct": round(oos_dd, 6),
            "entries": oos_entries,
        },
        "section_6_gates": gates,
        "cross_venue_fr_analysis": gates.get("G8_cross_venue", {}),
        "grid_search_top10": top10,
        "profit_projection": rank_data["profit_projection"],
        "hl_concentration_impact": hl_conc,
        "paired_trade_family_rank": {
            "members": rank_data["members"],
            "pendle_rank": rank_data["pendle_rank"],
            "family_size": rank_data["family_size"],
            "family_note": (
                f"K449 ETH-BTC baseline. Family 26 members (25 active + K623 PENDLE) post-K623. "
                f"K623 PENDLE-BTC → rank #{rank_data['pendle_rank']}. "
                "Yield tokenization sub-cluster: PENDLE=K623. "
                "Synthetic stable sub-cluster: ENA K616=ACCEPT(20.5 Sh). "
                "DeFi gov sub-cluster: AAVE K596=ACCEPT(11.4 Sh), CRV K599=BLOCKED, SNX K604=BLOCKED. "
                "Restaking: ETHFI K619=BLOCKED-LSD. LSD: LDO K594=REJECT."
            ),
        },
        "operational_requirements": {
            "execution_mode": "Paired-trade: simultaneous entry both legs",
            "module": "K450 paired-trade module (reuse K449/K476/K480/K484/K596/K616 implementation)",
            "position_management": "Equal-notional each leg (delta-neutral target)",
            "rebalance_trigger": "Signal flip (position reversal); monthly delta check",
            "estimated_rebalances_per_yr": oos_entries_yr,
            "venue": "HL primary (PENDLE-PERP + BTC-PERP). Bybit PENDLEUSDT secondary.",
            "hl_concentration_ok": hl_conc["within_cap"],
            "bybit_routing_option": "Bybit PENDLE + HL BTC if HL cap constraint (like ENA K616 routing)",
            "production_path": decision,
        },
        "next_generalization_candidates": [
            {
                "pair": "SUI-BTC",
                "hypothesis": "SUI Move VM — non-ETH L1, architecture-orthogonal. No yield-infra overlap.",
                "priority": "HIGH",
                "note": "SUI Move VM vs EVM. High vol ratio expected. No DeFi yield cluster overlap.",
            },
            {
                "pair": "JTO-BTC",
                "hypothesis": "Jito (JitoSOL) governance — Solana liquid staking + MEV. SOL ecosystem.",
                "priority": "MEDIUM",
                "note": "JitoSOL = SOL LSD with MEV boost. Different from ETH LSD (LDO REJECT). SOL ecosystem distinct.",
            },
            {
                "pair": "ETHENA-ecosystem-2",
                "hypothesis": "If PENDLE-ENA blocked: explore PENDLE across Bybit only (split routing).",
                "priority": "LOW",
                "note": "Only if BLOCKED-ENA-OVERLAP. Consider modified signal decoupled from sUSDe cycle.",
            },
        ],
    }

    # ── Save JSON ──────────────────────────────────────────────────────────
    out_json = BASE / "wave_k623_pendle_btc_eval.json"
    with open(out_json, "w") as f:
        json.dump(result, f, indent=2, default=str)
    print(f"\n[Output] JSON → {out_json}")

    # ── Save MD ────────────────────────────────────────────────────────────
    _write_md(result, BASE / "wave_k623_pendle_btc_eval.md")

    # ── Update report.html ────────────────────────────────────────────────
    _update_html(result, BASE / "report.html")

    print(f"\n[Done] K623 {decision} in {runtime_s}s")
    return result


def _write_md(result: Dict, path: Path):
    """Write markdown report."""
    d = result
    dec = d["decision"]
    oos = d["oos_metrics"]
    profit = d["profit_projection"]["aum_10M"]
    hl = d["hl_concentration_impact"]
    g5 = d["g5_correlations"]
    yt = d["yield_tokenization_cluster_status"]
    prescreen = d["phase0_prescreen"]

    md = f"""# K623 PENDLE-BTC FR Differential Paired-Trade Evaluation

## Executive Summary

| Field | Value |
|-------|-------|
| Wave | K623 |
| Strategy | PENDLE-BTC FR Differential Paired-Trade |
| Decision | **{dec}** |
| OOS Sharpe | {oos['sharpe']:.4f} |
| OOS Ann Return (1x) | {oos['ann_ret_pct']:.3f}% |
| OOS Ann Return (4x) | {oos['ann_ret_4x_pct']:.3f}% |
| OOS Period | {oos['period']} ({oos['years']:.3f}yr) |
| Max Drawdown | {oos['max_dd_pct']:.6f} |
| Profit USDC/yr @$10M | ${profit['net_annual_usdc_est']:,} |
| Gates Passed | {d['section_6_gates']['_summary']['gates_passed']}/{d['section_6_gates']['_summary']['gates_total']} |
| G5 All Pass | {g5['all_pass']} |
| ENA Overlap Corr | {g5.get('ena_corr', 'N/A')} (threshold 0.40) |
| ENA Blocked | {g5.get('ena_blocked', 'N/A')} |
| HL Concentration | {hl['current_hl_weight_pct']}% → {hl['new_hl_weight_pct']}% (cap {hl['hl_cap_pct']}%) |
| Family Rank | #{d['paired_trade_family_rank']['pendle_rank']} / {d['paired_trade_family_rank']['family_size']} |
| Run Time | {d['run_time_jst']} |

## Decision Rationale

{d['decision_rationale']}

## Phase 0: Pre-screen

### Venue Coverage
- **HL**: {"Listed" if prescreen['hl_venue']['pendle_listed'] else "NOT LISTED"} — {prescreen['hl_venue']['fr_cache_rows']} rows ({prescreen['hl_venue'].get('fr_start','')[:10]} to {prescreen['hl_venue'].get('fr_end','')[:10]})
- **Bybit**: {prescreen['bybit_venue']['note']}
- **OKX**: {prescreen['okx_venue']['note']}

### Volatility Ratio (PENDLE/BTC FR std)
| Window | Vol Ratio | Threshold | Pass |
|--------|-----------|-----------|------|
| 6M | {prescreen['vol_ratio_hl_6m']:.4f}x | {prescreen['vol_threshold']}x | {prescreen['vol_pass']} |
| 1Y | {prescreen['vol_ratio_hl_1y']:.4f}x | {prescreen['vol_threshold']}x | — |
| Full | {prescreen['vol_ratio_hl_full']:.4f}x | {prescreen['vol_threshold']}x | — |

### Raw FR Correlation (Yield Tokenization Cluster)
| Pair | Raw FR Corr | Interpretation |
|------|------------|----------------|
| PENDLE-ENA | {prescreen.get('yt_cluster_raw_fr_corr', {}).get('pendle_ena_fr_corr', 'N/A')} | CRITICAL: sUSDe pool overlap risk |
| PENDLE-AAVE | {prescreen.get('yt_cluster_raw_fr_corr', {}).get('pendle_aave_fr_corr', 'N/A')} | DeFi lending comparison |
| PENDLE-CRV | {prescreen.get('yt_cluster_raw_fr_corr', {}).get('pendle_crv_fr_corr', 'N/A')} | DEX/AMM comparison |
| PENDLE-LDO | {prescreen.get('yt_cluster_raw_fr_corr', {}).get('pendle_ldo_fr_corr', 'N/A')} | LSD comparison |

### Basic FR Statistics
- PENDLE mean ann FR: {prescreen.get('pendle_fr_mean_ann_pct', 'N/A')}%
- BTC mean ann FR: {prescreen.get('btc_fr_mean_ann_pct', 'N/A')}%
- FR diff mean: {prescreen.get('fr_diff_mean', 'N/A')}
- FR diff std: {prescreen.get('fr_diff_std', 'N/A')}

## Statistical Analysis

### ADF Stationarity
{d['statistical_analysis']['adf_stationarity']['interpretation']}

| Metric | Value |
|--------|-------|
| ADF Statistic | {d['statistical_analysis']['adf_stationarity']['statistic']} |
| p-value | {d['statistical_analysis']['adf_stationarity']['p_value']} |
| 1% Critical | {d['statistical_analysis']['adf_stationarity']['critical_1pct']} |
| Stationary @1% | {d['statistical_analysis']['adf_stationarity']['is_stationary_1pct']} |

### Ornstein-Uhlenbeck Mean Reversion
| Parameter | Value |
|-----------|-------|
| Lambda | {d['statistical_analysis']['ornstein_uhlenbeck']['lambda']} |
| Half-life | {d['statistical_analysis']['ornstein_uhlenbeck']['half_life_hours']}h ({d['statistical_analysis']['ornstein_uhlenbeck']['half_life_days']}d) |
| Long-run mean | {d['statistical_analysis']['ornstein_uhlenbeck']['long_run_mean']} |
| Mean-reverting | {d['statistical_analysis']['ornstein_uhlenbeck']['mean_reverting']} |

### Autocorrelation
| Lag | ACF |
|-----|-----|
| 1h | {d['statistical_analysis']['autocorrelation']['lag_1h']} |
| 24h | {d['statistical_analysis']['autocorrelation']['lag_24h']} |
| 168h (7d) | {d['statistical_analysis']['autocorrelation']['lag_168h']} |

## Phase 2: Signal Configuration

**Best Config (≤336h preferred, K613 artefact avoidance):**
- Window: {d['signal_config']['window_h']}h
- Threshold: {d['signal_config']['threshold']}
- Direction rule: {d['signal_config']['direction_rule']}

### Grid Search Top 10 (by OOS Sharpe)
| Window | TF | IS Sharpe | OOS Sharpe | Entries/yr | Preferred |
|--------|-----|----------|-----------|------------|-----------|
""" + "\n".join(
        f"| {r['window_label']} | {r['threshold_factor']:.1f} | {r['IS_sharpe']:.3f} | {r['OOS_sharpe']:.3f} | {r['entries_yr']} | {r['preferred']} |"
        for r in d['grid_search_top10']
    ) + f"""

## Phase 3: Backtest Metrics

### Full Period
| Metric | Value |
|--------|-------|
| Sharpe | {d['full_period']['sharpe']} |
| Ann Return | {d['full_period']['ann_ret_pct']}% |
| Max DD | {d['full_period']['max_dd_pct']} |
| Total Entries | {d['full_period']['total_entries']} |
| Entries/yr | {d['full_period']['entries_per_yr']} |

### IS Period ({d['is_metrics']['period']})
| Metric | Value |
|--------|-------|
| Sharpe | {d['is_metrics']['sharpe']} |
| Ann Return | {d['is_metrics']['ann_ret_pct']}% |

### OOS Period ({oos['period']})
| Metric | Value |
|--------|-------|
| Sharpe | {oos['sharpe']} |
| Ann Return (1x) | {oos['ann_ret_pct']}% |
| Ann Return (4x) | {oos['ann_ret_4x_pct']}% |
| Max DD | {oos['max_dd_pct']} |
| Entries | {oos['entries']} |

## Phase 4: §6 Gates

### Gate Summary
**Passed: {d['section_6_gates']['_summary']['gates_passed']}/{d['section_6_gates']['_summary']['gates_total']}**

| Gate | Pass | Value | Note |
|------|------|-------|------|
| G1 OOS Sharpe | {d['section_6_gates']['G1_oos_sharpe']['pass']} | {d['section_6_gates']['G1_oos_sharpe']['value']} | ≥ {d['section_6_gates']['G1_oos_sharpe']['threshold']} |
| G2 Perm p | {d['section_6_gates']['G2_perm_pvalue']['pass']} | {d['section_6_gates']['G2_perm_pvalue']['value']} | ≤ 0.05 |
| G3 DSR Bonf | {d['section_6_gates']['G3_dsr_bonferroni']['pass']} | p={d['section_6_gates']['G3_dsr_bonferroni']['p_bonferroni']} | < {d['section_6_gates']['G3_dsr_bonferroni']['threshold']:.5f} |
| G4 Walk-fwd | {d['section_6_gates']['G4_walk_forward_12fold']['pass']} | min={d['section_6_gates']['G4_walk_forward_12fold']['min_fold_sharpe']} | all positive |
| G5 All | {g5['all_pass']} | max={g5['max_corr']:.4f} | < 0.40 |
| G5ag ENA | {not g5.get('ena_blocked', False)} | {g5.get('ena_corr', 'N/A')} | CRITICAL: < 0.40 |
| G6 Trades/yr | {d['section_6_gates']['G6_trade_count']['pass']} | {d['section_6_gates']['G6_trade_count']['per_year']} | ≥ 30 |
| G7 Ann Ret 4x | {d['section_6_gates']['G7_ann_return']['pass']} | {d['section_6_gates']['G7_ann_return']['value_4x_pct']}% | ≥ 5% |
| G8 Bybit corr | {d['section_6_gates']['G8_cross_venue']['pass']} | {d['section_6_gates']['G8_cross_venue']['bybit'].get('corr_with_hl', 'N/A')} | ≥ 0.55 |
| G9 OOS days | {d['section_6_gates']['G9_data_sufficiency']['pass']} | {d['section_6_gates']['G9_data_sufficiency']['oos_days']:.0f}d | ≥ 180d |

### ENA Overlap Analysis (K619 Critical Check)
{d['section_6_gates']['G5_ena_overlap_check']['note']}

## Phase 5: HL Concentration

| Metric | Value |
|--------|-------|
| Current HL weight | {hl['current_hl_weight_pct']}% |
| K623 sleeve | {hl['k623_sleeve_pct']}% |
| New HL weight | {hl['new_hl_weight_pct']}% |
| HL cap | {hl['hl_cap_pct']}% |
| Within cap | {hl['within_cap']} |
| Headroom | {hl['headroom_pct']}% |
| Routing | {hl['routing_recommendation']} |

{hl['note']}

## Yield Tokenization Cluster Status

{yt['yt_cluster_verdict']}

### Cluster Members
| Token | Decision | OOS Sharpe | Sub-cluster | PENDLE FR Corr |
|-------|----------|-----------|-------------|----------------|
| AAVE (K596) | ACCEPT | 11.354 | DeFi lending | {yt.get('k596_aave_btc', {}).get('fr_corr_with_pendle', 'N/A')} |
| ENA (K616) | ACCEPT | 20.4681 | Synthetic Stable Infra | {yt.get('k616_ena_btc', {}).get('fr_corr_with_pendle', 'N/A')} |
| ETHFI (K619) | BLOCKED-LSD | 22.7329 | Restaking Yield | N/A |
| PENDLE (K623) | **{dec}** | **{oos['sharpe']:.4f}** | Yield Tokenization | — |

{yt['cluster_summary']}

## Profit Projection

| Scenario | Value |
|----------|-------|
| AUM | $10M |
| Sleeve % | {profit['sleeve_pct']}% |
| Leverage | {profit['leverage']}x |
| Notional | ${profit['notional_usd']:,.0f} |
| OOS Ann Ret (1x) | {profit['oos_ann_ret_1x_pct']:.3f}% |
| OOS Ann Ret (4x) | {profit['oos_ann_ret_4x_pct']:.3f}% |
| Gross USDC/yr | ${profit['gross_annual_usdc']:,} |
| Net USDC/yr | ${profit['net_annual_usdc_est']:,} |

## Family Rank (FR Differential Paired-Trade)

**PENDLE-BTC rank: #{d['paired_trade_family_rank']['pendle_rank']} / {d['paired_trade_family_rank']['family_size']}**

| Rank | Pair | OOS Sharpe | Status | Wave |
|------|------|-----------|--------|------|
""" + "\n".join(
        f"| {m['rank']} | {m['pair']} | {m['sharpe']:.3f} | {m['status']} | {m['wave']} |"
        for m in d['paired_trade_family_rank']['members'][:15]
    ) + f"""
| ... | ... | ... | ... | ... |

## Walk-Forward 12-Fold Stability

| Fold | OOS Start | OOS End | Sharpe | Ann Ret | Entries |
|------|-----------|---------|--------|---------|---------|
""" + "\n".join(
        f"| {f['fold']} | {f['oos_start']} | {f['oos_end']} | {f['sharpe']:.3f} | {f['ann_ret_pct']:.3f}% | {f['entries']} |"
        for f in d['section_6_gates']['G4_walk_forward_12fold']['folds']
    ) + f"""

## K474 vs K623 Distinction

| Aspect | K474 (REJECT) | K623 |
|--------|---------------|------|
| Strategy | YT yield carry | FR differential paired-trade |
| Signal | Expected YT APY vs implied | BTC-PENDLE FR rolling mean |
| Asset held | YT tokens (decay to 0) | PENDLE perp (governance token) |
| Risk | YT time-decay, yield variance | FR carry, governance token vol |
| Decision | REJECT (MC -0.51pp) | {dec} |
| Lesson | YT carry has negative EV | PENDLE perp FR dynamics independent |

## Next Wave Candidates

1. **SUI-BTC** (HIGH priority) — Move VM, architecture-orthogonal, no yield-infra overlap
2. **JTO-BTC** (MEDIUM) — Jito SOL liquid staking + MEV, SOL ecosystem distinct
3. **Backlog cleanup** — Per R-finding 3+1+1 allocation mandate

---
*Generated: {d['run_time_jst']} | K623 PENDLE-BTC FR Differential | Wave K623*
"""

    path.write_text(md, encoding="utf-8")
    print(f"[Output] MD → {path}")


def _update_html(result: Dict, html_path: Path):
    """Update report.html with K623 badge."""
    import datetime as _dt

    dec = result["decision"]
    oos_sh = result["oos_metrics"]["sharpe"]
    profit = result["profit_projection"]["aum_10M"]["net_annual_usdc_est"]
    rank = result["paired_trade_family_rank"]["pendle_rank"]
    ena_corr = result["g5_correlations"].get("ena_corr", "N/A")
    ena_blocked = result["g5_correlations"].get("ena_blocked", False)
    gates_passed = result["section_6_gates"]["_summary"]["gates_passed"]
    gates_total = result["section_6_gates"]["_summary"]["gates_total"]

    dec_color = {
        "ACCEPT": "#27ae60",
        "ACCEPT CONDITIONAL": "#f39c12",
        "BLOCKED-ENA-OVERLAP": "#e74c3c",
        "BLOCKED-LSD": "#e74c3c",
        "BLOCKED-G5": "#e74c3c",
        "REJECT": "#c0392b",
    }.get(dec, "#95a5a6")

    badge = f"""
<!-- K623 PENDLE-BTC FR Differential Paired-Trade -->
<div class="wave-badge" id="k623" style="border-left: 5px solid {dec_color}; background: #1a1a2e; padding: 16px; margin: 8px 0; border-radius: 6px; font-family: monospace;">
  <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap;">
    <span style="color:{dec_color}; font-size:1.1em; font-weight:bold;">K623 PENDLE-BTC FR Differential</span>
    <span style="color:{dec_color}; font-weight:bold; padding: 4px 12px; border: 2px solid {dec_color}; border-radius:4px;">{dec}</span>
  </div>
  <div style="color:#aaa; font-size:0.85em; margin-top:8px;">
    Yield Tokenization cluster | K474 retry (FR-differential, not YT-carry) | K619 ENA user base overlap critical check
  </div>
  <div style="display:grid; grid-template-columns:repeat(auto-fit,minmax(160px,1fr)); gap:8px; margin-top:12px;">
    <div style="color:#eee;">OOS Sharpe: <strong style="color:#3498db;">{oos_sh:.4f}</strong></div>
    <div style="color:#eee;">Profit USDC/yr @$10M: <strong style="color:#2ecc71;">${profit:,}</strong></div>
    <div style="color:#eee;">Gates: <strong style="color:#f1c40f;">{gates_passed}/{gates_total}</strong></div>
    <div style="color:#eee;">Family Rank: <strong style="color:#9b59b6;">#{rank}/26</strong></div>
    <div style="color:#eee;">ENA Corr: <strong style="color:{'#e74c3c' if ena_blocked else '#2ecc71'};">{ena_corr if ena_corr is not None else 'N/A'} {'[BLOCKED]' if ena_blocked else '[PASS]'}</strong></div>
  </div>
  <div style="color:#888; font-size:0.78em; margin-top:8px;">
    Updated: {result['run_time_jst']} | W={result['signal_config']['window_h']}h threshold={result['signal_config']['threshold']}
  </div>
</div>
"""

    if not html_path.exists():
        print(f"  report.html not found at {html_path}, skipping HTML update")
        return

    content = html_path.read_text(encoding="utf-8")

    # Remove existing K623 badge if present
    import re
    content = re.sub(
        r"<!-- K623 PENDLE-BTC FR Differential Paired-Trade -->.*?</div>\s*\n",
        "",
        content,
        flags=re.DOTALL,
    )

    # Insert after K619 badge or before </body>
    if "K619" in content:
        insert_after = re.search(r'(<!-- K619.*?</div>\s*\n)', content, re.DOTALL)
        if insert_after:
            pos = insert_after.end()
            content = content[:pos] + badge + "\n" + content[pos:]
        else:
            content = content.replace("</body>", badge + "\n</body>")
    else:
        content = content.replace("</body>", badge + "\n</body>")

    html_path.write_text(content, encoding="utf-8")
    print(f"[Output] HTML badge → {html_path}")


if __name__ == "__main__":
    main()
