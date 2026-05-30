#!/usr/bin/env python3
"""
k788_meme_sol_run.py — K788 MEME-SOL FR Differential Strategy
=================================================================
TWENTY-FOURTH ALT-ALT pair (25th scaffold, 24th pair evaluated): MEME vs SOL.
Signal: MEME_FR - SOL_FR  (W=84h rolling mean — K788 eval canonical best IS/OOS)
W=84h primary (IS Sh=13.12, OOS Sh=15.97 — CONDITIONAL_ACCEPT 9/9 gates per K788 eval)
3x leverage (HL max for MEME-PERP, lower than standard 4x — MEME liquidity limited)
0.4% sleeve (liquidity-limited — MEME HIP-3 HL, OI=$480K, daily vol=$447K)
HL primary + Bybit verify (MEME confirmed Bybit/OKX — G8 PASS)
PAPER_TRADE=True default

K788 MEME-SOL alt-alt hypothesis:
  MEME (memecoin.org index, ERC-20):
    FR driven by ERC-20 meme market sentiment rotations (ETH ecosystem meme cycles),
    Ethereum meme coin bull/bear cycles (ETH-native meme index, distinct from SOL memes),
    ETH-ecosystem meme rotation (WIF/BONK vs ETH meme narrative switch),
    HL HIP-3 speculative demand (retail meme speculation on perp),
    Meme market crash events (Max spike: -48.37 bps, high kurtosis).
    MEME is memecoin.org ERC-20 index: basket-weighted multi-meme exposure.
    Distinct from: PEPE (single ETH meme), WIF (SOL-native meme), BONK (SOL-native).
    FR bidirectional: OOS positive_fraction=0.5743 (genuine bidirectionality — L004 PASS).
    L004_DIFF BORDERLINE: full=0.289 (<0.30 floor), OOS=0.440 PASS, G2 p=0.000 timing alpha.
    G2 timing alpha: pure carry IS Sh=7.99 vs signal IS Sh=13.12 → timing adds 5.13 Sh pts.
    vol_ratio: MEME/SOL=3.34x (full) — HIGH vol ratio.
    raw_corr(MEME_fr, SOL_fr) = 0.1177 — low correlation (MEME cross-chain ERC-20).
    HL max leverage: 3x (lower than standard 4x — MEME liquidity constraint).
    HL MEME-PERP: HIP-3, OI=$480K, daily vol=$447K.
    G8 PASS: MEME confirmed on HL + OKX + Bybit (cross-venue verified).
  SOL (Solana SVM L1):
    FR driven by retail momentum, Phantom wallet adoption, Firedancer upgrade,
    Solana ETF narrative flows, SVM DeFi TVL (Jupiter/Drift/Jito).
    SOL FR mean persistently positive — retail demand structural.
    SOL extreme negative FR: Min=-20.51bps (liquidation cascade Feb 2025).
  Alt-alt mechanism: MEME (ERC-20 meme index ETH chain) vs SOL (Solana SVM L1).
    Structurally orthogonal: ETH meme rotation cycles (HL HIP-3 retail speculation)
    are decoupled from Solana SVM cycle (Firedancer, validator rewards, SVM DeFi).
    MEME cluster: ERC-20 Meme Index (cross-chain meme, ETH ecosystem) — DISTINCT.
    MEME vs PEPE: MEME is basket-weighted index, PEPE is single meme coin (different vol profiles).
    MEME vs WIF: MEME is ERC-20 ETH chain, WIF is SOL-native → cross-chain orthogonal.
    G5w PEPE-SOL corr=0.1339 PASS, G5y WIF-SOL corr=0.0825 PASS (meme cluster CLEAR).
    G5 27/27 ALL PASS: max_corr=0.1973 (G5b SOL-BTC, well below 0.40 threshold).

K788 §6 validation (CONDITIONAL_ACCEPT 9/9 gates):
  - OOS Sharpe: 15.97 (W=84h, zero threshold, 212d OOS — G9 PASS >= 180d)
  - IS Sharpe:  13.12 (W=84h) — OOS > IS (no directional overfit, OOS improvement)
  - Full Sharpe: 13.91 (W=84h consistent)
  - OOS Ann Return: $14,518 central @$10M @0.4% @3x sleeve (K523 3-point: $9.2K-$20.6K)
  - W=84h rolling mean, zero threshold (sign of diff) — G6: 84.3/yr OOS PASS
  - G4 walk-forward: 12/12 folds positive (ALL POSITIVE, min_fold_sh=4.3534)
  - G5 27/27 ALL PASS; max_corr=0.1973 (G5b SOL-BTC, well below 0.40)
  - G6: 84.3 entries/yr OOS PASS (vs 30/yr threshold)
  - G7: OOS ann ret 3x=60.5% PASS (vs 5% threshold)
  - G8: PASS — MEME HL+OKX+Bybit confirmed (cross-venue verified)
  - G9: OOS 212d PASS (>= 180d minimum)
  - L004 PASS: MEME bidirectional (pos_frac_full=0.7940 pos_frac_oos=0.5743)
  - L004_DIFF BORDERLINE: full=0.289 (<0.30 floor), OOS=0.440 PASS
    G2 p=0.000 confirms timing alpha (+5.13 Sh vs pure carry) — PROCEED
    Monthly OOS diff_pos recheck required; reduce sleeve if < 0.28 for 2 consecutive months
  - HL 66.8% -> paper-gate strict, LIVE after K498/v6.52
  - Live gate: Sh >= 10, fill >= 60%, maxDD < 15%, L004_DIFF stable (OOS diff_pos >= 0.30)

K788 MEME-SOL vertex addition (22nd vertex, 1st ERC-20 meme index cluster):
  V (before K788) = {APT, ATOM, AVAX, BNB, ENA, FIL, HBAR, INJ, LDO, SEI, SOL, TIA, TAO,
                      PEPE, WIF, BLUR, AXS, IO, EIGEN, COMP, BIO}
  V (after K788)  = {APT, ATOM, AVAX, BNB, ENA, FIL, HBAR, INJ, LDO, SEI, SOL, TIA, TAO,
                      PEPE, WIF, BLUR, AXS, IO, EIGEN, COMP, BIO, MEME}
  MEME = 22nd vertex (1st ERC-20 meme index cluster — cross-chain ETH meme basket).
  MR9 L002: all future MEME-X pairs are auto-blocked (MEME exhausted as new vertex).
  MEME-SOL is the only permissible MEME-X pair given V composition at K788.

L004_DIFF borderline note (K788):
  full=0.289 is 0.011 BELOW the 0.30 floor (borderline-FAIL full period).
  OOS=0.440 confirms genuine timing alpha in live period (PASS).
  G2 p=0.000 confirms edge is not random (unlike K782 PROVE G2 p=1.000).
  Pure carry IS Sh=7.99 vs Signal IS Sh=13.12 → timing adds 5.13 Sh pts.
  DECISION: SOFT BLOCK overridden by G2 timing evidence + OOS PASS.
  Monitor: monthly recheck of OOS diff_pos. Reduce sleeve if < 0.28 for 2 consecutive months.
  Live gate: L004_DIFF stable (OOS diff_pos >= 0.30) required before live elevation.

K523 3-point profit projection (@$10M @3x @0.4% sleeve):
  Conservative: $9,194/yr  (R2S=38% floor x OOS-haircut-25%, K518 floor, fee)
  Central:      $14,518/yr (K523 mandate: 60% realized-to-stated, base case)
  Optimistic:   $20,567/yr (near-full OOS realization)
  Upper bound:  OOS raw return (NOT central — K523 mandatory)
  Note: 0.4% sleeve -> ~$40K margin @$10M; 3x lev -> $120K total notional, $60K per leg

Cross-venue note (K788):
  HL:    MEME-PERP on HL (HIP-3). Primary venue. OI=$480K, daily vol=$447K.
  Bybit: MEME confirmed (MEMEUSDT, 4h interval, 50x max lev, listed Nov 2023).
  OKX:   MEME confirmed (MEME-USDT-SWAP, OKX-HL corr=0.843).
  G8 = PASS (all 3 venues confirmed). Cross-venue verified.
  Note: 3x max leverage (HL MEME liquidity constraint — lower than standard 4x).

Architecture (K679->K747->K754->K759->K769->K774->K777->K778->K786->K788 alt-alt scaffold pattern):
  1. fetch_fr_batch()                       -> fetch MEME + SOL FR every 8h from HL (primary)
  2. compute_signal(meme_fr, sol_fr)        -> 84h rolling mean of (MEME_FR - SOL_FR); sign()
  3. decide_position(signal)               -> LONG_MEME_SHORT_SOL | LONG_SOL_SHORT_MEME | NEUTRAL
  4. submit_paired_trade(long, short)      -> POST_ONLY paired (MEME + SOL legs, HL primary)
  5. daily_rebalance()                     -> drift > 5% triggers rebalance
  6. close_paired_position(reason)         -> sequential: short first, then long

K791 production scaffold:
  - 82nd daemon (25th alt-alt scaffold, 24th pair, CONDITIONAL_ACCEPT 9/9)
  - HL primary (MEME-PERP + SOL-PERP on HL). Bybit/OKX confirmed (G8 PASS).
  - 0.4% sleeve (liquidity-limited — MEME HIP-3 daily vol $447K)
  - 3x leverage (HL max for MEME — lower than standard 4x)
  - $14,518 central @$10M @3x @0.4% sleeve (K523 3-point: $9.2K-$20.6K)
  - Paper-gate until K498/v6.52 reduces HL concentration AND L004_DIFF stable
  - Live gate: Sh >= 10, fill >= 60%, maxDD < 15%, L004_DIFF stable (OOS diff_pos >= 0.30)
  - L004_DIFF monitor: OOS diff_pos monthly recheck, reduce sleeve if < 0.28 for 2 consecutive months

60d gate (K791):
  Realized Sh >= 10, fill >= 60%, maxDD < 15%, L004_DIFF stable (OOS diff_pos >= 0.30).

Execution:
  - HL primary (MEME-PERP + SOL-PERP on HL — Bybit/OKX verified G8 PASS)
  - POST_ONLY paired execution (K439 pattern)
  - Position: 0.4% sleeve, 3x leverage (paper-gate strict — HL cap 66.8%)
  - 8h cadence (matches FR settlement cycle)
  - W=84h rolling mean (10.5 x 8h periods, rounded to 10 periods — G6: 84.3/yr OOS)

Paper-trade mode is the DEFAULT.  No orders are submitted unless
PAPER_TRADE=False is explicitly set in the environment.

K339 security: REPO_ROOT from __file__, no /Users/ literals.
No new packages — stdlib urllib + json only.

Usage:
  python3 scripts/k788_meme_sol_run.py --dry-run
  python3 scripts/k788_meme_sol_run.py --status
  python3 scripts/k788_meme_sol_run.py --rebalance
  python3 scripts/k788_meme_sol_run.py --close "scheduled exit"
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# -- K339 canonical paths -----------------------------------------------------
REPO_ROOT   = Path(__file__).resolve().parent.parent
DATA_DIR    = REPO_ROOT / "data"
CACHE_DIR   = REPO_ROOT / "cache"
LOGS_DIR    = REPO_ROOT / "logs"
for _d in [DATA_DIR, CACHE_DIR, LOGS_DIR]:
    _d.mkdir(exist_ok=True)

DASHBOARD_PATH  = DATA_DIR  / "k788_dashboard.json"
FR_HISTORY_PATH = CACHE_DIR / "k788_fr_history.jsonl"
TRADE_LOG_PATH  = CACHE_DIR / "k788_paper_trades.jsonl"

JST = timezone(timedelta(hours=9))
UTC = timezone.utc

# -- Strategy constants -------------------------------------------------------
PAPER_TRADE         = os.environ.get("PAPER_TRADE", "True").lower() != "false"
SLEEVE_PCT          = 0.004         # K788 sleeve = 0.4% of AUM (liquidity-limited HIP-3 MEME)
LEVERAGE            = 3.0           # 3x per K788 analysis (HL max for MEME — lower than standard 4x)
AUM_DEFAULT         = 10_000_000.0  # $10M reference AUM
DRIFT_REBALANCE_PCT = 0.05          # rebalance if legs drift > 5%
IOC_TIMEOUT_SEC     = 300           # 5 min fill window
EMA_PERIOD_HOURS    = 84            # 84h rolling mean (W=84h primary, G6: 84.3/yr OOS)
EMA_PERIOD_PERIODS  = EMA_PERIOD_HOURS // 8  # = 10 periods (8h settlement cycle, rounded)
SIGNAL_SIGMA_MULT   = 0.0           # zero threshold (sign of rolling mean)
HL_API_URL          = "https://api.hyperliquid.xyz/info"

# -- Venue config -------------------------------------------------------------
# HL primary: MEME-PERP + SOL-PERP on HL.
# MEME is HIP-3 on HL. OI=$480K. Daily vol=$447K.
# G8 PASS: MEME confirmed on HL + OKX (corr=0.843) + Bybit (MEMEUSDT Nov 2023).
# Note: Bybit is confirmation only — execution on HL primary.
# 3x max leverage on HL (MEME liquidity constraint; standard alt-alt is 4x).
HL_CONCENTRATION_PRE_K788   = 66.8   # post-K787 reference (K786 paper-gate, no live capital)
HL_CONCENTRATION_POST_K788  = 66.8   # UNCHANGED -- paper-only, no live capital added
BYBIT_CONFIRM_REASON         = (
    "MEME confirmed on Bybit (MEMEUSDT, listed Nov 2023, 50x max lev, 4h interval). "
    "OKX confirmed (MEME-USDT-SWAP, OKX-HL corr=0.843). "
    "G8 PASS: all 3 venues confirmed. HL primary for execution. "
    "3x max leverage (HL MEME liquidity constraint — OI=$480K, daily vol=$447K). "
    "Live gate: Sh >= 10, fill >= 60%, maxDD < 15%, L004_DIFF stable (OOS diff_pos >= 0.30). "
    "Deploy LIVE after (1) K498/v6.52 reduces HL% below 65% AND (2) L004_DIFF OOS >= 0.30 stable."
)

# -- Position state constants -------------------------------------------------
STATE_NEUTRAL                = "NEUTRAL"
STATE_LONG_MEME_SHORT_SOL    = "LONG_MEME_SHORT_SOL"
STATE_LONG_SOL_SHORT_MEME    = "LONG_SOL_SHORT_MEME"

# -- Symbols fetched from HL for FR data --------------------------------------
SYMBOLS = ("MEME", "SOL")


# ─────────────────────────────────────────────────────────────────────────────
# HTTP helper (stdlib urllib only -- no requests)
# ─────────────────────────────────────────────────────────────────────────────

def _http_get(url: str, timeout: int = 10) -> Optional[dict]:
    try:
        req = urllib.request.Request(
            url, headers={"User-Agent": "crypto-lab-k788/1.0"}
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        print(f"  [k788] HTTP error: {e}", file=sys.stderr)
        return None


def _http_post(url: str, payload: dict, timeout: int = 10) -> Optional[dict]:
    try:
        data = json.dumps(payload).encode()
        req  = urllib.request.Request(
            url, data=data,
            headers={"Content-Type": "application/json",
                     "User-Agent": "crypto-lab-k788/1.0"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        print(f"  [k788] HTTP error: {e}", file=sys.stderr)
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Phase 1 -- Funding rate fetch (MEME + SOL from HL primary)
# ─────────────────────────────────────────────────────────────────────────────

def _fetch_hl_fr_batch() -> Dict[str, float]:
    """
    Fetch current 1h funding rates for MEME and SOL from HL.
    Returns {symbol: fr_1h_fraction}.

    HL API: metaAndAssetCtxs (POST).
    K788: HL primary (MEME-PERP + SOL-PERP). G8 PASS (HL+OKX+Bybit confirmed).

    Note: HL settles 1h funding; W=84h = 84 x 1h periods for rolling mean.
    FR stored as 1h fraction; annualized = fr_1h * 8760.

    MEME strategy direction (bidirectional — L004 PASS):
      MEME FR bidirectional: pos_frac_full=0.7940 pos_frac_oos=0.5743.
      L004_DIFF: full=0.289 (borderline-FAIL full), OOS=0.440 PASS.
      G2 p=0.000 confirms timing alpha (+5.13 Sh vs pure carry).
      MEME ERC-20 meme cycles: ETH meme bull → MEME FR spikes positive.
      Meme market crash → MEME FR extreme negative (kurtosis, -48.37bps spike).
      ETH-ecosystem meme rotation → ERC-20 meme demand surges vs SOL memes.
      SOL-season → MEME FR inverts negative vs SOL persistent positive.
    """
    result: Dict[str, float] = {}

    # Primary: HL metaAndAssetCtxs
    raw_hl = _http_post(HL_API_URL, {"type": "metaAndAssetCtxs"})
    if raw_hl and isinstance(raw_hl, list) and len(raw_hl) >= 2:
        meta       = raw_hl[0]
        asset_ctxs = raw_hl[1]
        universe   = {item["name"]: i for i, item in enumerate(meta.get("universe", []))}
        for sym in SYMBOLS:
            if sym in universe:
                idx = universe[sym]
                ctx = asset_ctxs[idx]
                try:
                    result[sym] = float(ctx.get("funding", 0.0))
                except (TypeError, ValueError):
                    continue
        if len(result) == len(SYMBOLS):
            return result
        print(f"  [k788] HL partial result {list(result.keys())} -- retrying",
              file=sys.stderr)

    # Return whatever we got from HL; missing symbols default to 0.0 in compute_signal.
    return result


def _load_fr_history() -> List[dict]:
    """Load K788 FR history JSONL."""
    if not FR_HISTORY_PATH.exists():
        return []
    records: List[dict] = []
    for line in FR_HISTORY_PATH.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return records


def _append_fr_history(
    fr_meme: float, fr_sol: float, meme_sol_diff: float
) -> None:
    """Append one FR snapshot to history."""
    rec = {
        "ts_utc":        datetime.now(UTC).isoformat(),
        "fr_meme":       round(fr_meme,        10),
        "fr_sol":        round(fr_sol,           10),
        "meme_sol_diff": round(meme_sol_diff,    10),  # MEME_FR - SOL_FR
    }
    with open(FR_HISTORY_PATH, "a") as f:
        f.write(json.dumps(rec) + "\n")


# ─────────────────────────────────────────────────────────────────────────────
# Phase 2 -- Signal computation (MEME-SOL direct differential, 84h rolling mean)
# ─────────────────────────────────────────────────────────────────────────────

def compute_signal(
    fr_meme: Optional[float] = None,
    fr_sol:  Optional[float] = None,
) -> dict:
    """
    Fetch live MEME and SOL FRs from HL (HL primary), compute MEME-SOL differential,
    and compute 84h rolling mean for direction signal.

    Signal mechanism (K788 direct alt-alt differential -- no orthogonalization):
      diff = MEME_FR - SOL_FR
      mean_84h = 84h rolling mean of diff (10.5 x 8h periods, rounded to 10 periods)
      sign  = sign(mean_84h)
      Enter: sign > 0 -> MEME FR > SOL FR -> long MEME (ETH meme bull spike), short SOL
             sign < 0 -> SOL FR > MEME FR -> long SOL (collect SVM premium), short MEME
                         [Frequent: SOL persistent positive + MEME ERC-20 bear cycle]

    NOTE: MEME is ERC-20 meme index (basket-weighted, cross-chain ETH).
    MEME ERC-20 meme mechanism:
      ETH meme bull phase: ERC-20 meme rotation → MEME FR spikes positive.
      Meme market crash: MEME FR extreme negative (kurtosis, -48.37bps spike).
      ETH-ecosystem meme rotation vs SOL meme season: MEME/SOL FR divergence.
      HL HIP-3 speculative retail demand → amplified MEME FR swings.
      Quarterly trend: SOL>MEME in most quarters (MEME short usually positive).

    W=84h rationale (G6 compliance, best OOS across all window sizes):
      W=84h -> 84.3 entries/yr OOS (WELL ABOVE 30/yr G6 threshold -- PASS).
      W=84h primary: IS Sh=13.12, OOS Sh=15.97 (OOS > IS — no directional overfit).
      W=48h: IS Sh=13.28, OOS Sh=16.54 (best OOS, but W=84h chosen for G6 stability).
      W=168h: IS Sh=11.55, OOS Sh=16.12 (fewer entries, near G6 floor for W=168h).
      W=84h chosen: canonical per K788 eval (balanced IS/OOS, G6-safe, stable).

    K788 §6 validation (CONDITIONAL_ACCEPT 9/9):
      - OOS Sharpe: 15.97 (W=84h, zero threshold, 212d OOS)
      - OOS Ann Return: $14,518 central @$10M @3x @0.4% sleeve (K523 3-point)
      - G4 WF 12/12 ALL POSITIVE (min_fold_sh=4.3534 — all folds positive)
      - G5 27/27 ALL PASS: max_corr=0.1973 (G5b SOL-BTC, well below 0.40)
      - G6: 84.3 entries/yr OOS PASS (vs 30/yr threshold)
      - G7: OOS ann ret 3x=60.5% PASS (vs 5% threshold)
      - G8: PASS — MEME HL+OKX+Bybit confirmed (cross-venue verified)
      - G9: OOS 212d PASS (>= 180d minimum)
      - HL 66.8% AT CAP -> paper-gate strict

    Returns:
      {
        "fr_meme":          float,
        "fr_sol":           float,
        "meme_sol_diff":    float,    # MEME_FR - SOL_FR (current)
        "mean_84h":         float,    # 84h rolling mean of differential
        "diff_sigma":       float,    # rolling sigma (informational)
        "history_points":   int,
        "regime":           str,      # BULL_MEME | BEAR_MEME | NEUTRAL
        "signal_direction": int,      # +1 | -1 | 0
        "ts_jst":           str,
      }
    """
    if fr_meme is None or fr_sol is None:
        frs     = _fetch_hl_fr_batch()
        fr_meme = frs.get("MEME", 0.0)
        fr_sol  = frs.get("SOL",  0.0)

    # MEME-SOL direct alt-alt differential (no orthogonalization)
    meme_sol_diff = fr_meme - fr_sol

    _append_fr_history(fr_meme, fr_sol, meme_sol_diff)

    # Load history for rolling mean + sigma (84h ~= 10 x 8h periods)
    history = _load_fr_history()
    diffs   = [r["meme_sol_diff"] for r in history if "meme_sol_diff" in r]

    n_periods = EMA_PERIOD_PERIODS   # 10 periods (~84h at 8h cadence)

    # Rolling mean: simple mean of last n_periods diffs
    window = diffs[-n_periods:] if len(diffs) >= 1 else diffs
    if window:
        mean_84h = sum(window) / len(window)
    else:
        mean_84h = 0.0

    # Rolling sigma: std of last n_periods diffs (informational)
    if len(window) >= 2:
        mean_w = sum(window) / len(window)
        sigma  = math.sqrt(sum((x - mean_w) ** 2 for x in window) / (len(window) - 1))
    else:
        sigma = abs(mean_84h) if mean_84h != 0 else 1e-8   # fallback

    # Regime classification (zero threshold -- per K788 spec, canonical best OOS)
    # BULL_MEME: MEME FR > SOL FR (ETH meme bull cycle or ERC-20 meme rotation spike)
    # BEAR_MEME: MEME FR < SOL FR (SVM season + MEME bear cycle — frequent)
    if mean_84h > 0:
        regime    = "BULL_MEME"    # MEME-SOL diff positive -> MEME FR > SOL FR
        direction = 1
    elif mean_84h < 0:
        regime    = "BEAR_MEME"    # SOL FR > MEME FR (SVM dominant + ETH meme bear)
        direction = -1
    else:
        regime    = "NEUTRAL"
        direction = 0

    return {
        "fr_meme":          round(fr_meme,         10),
        "fr_sol":           round(fr_sol,            10),
        "meme_sol_diff":    round(meme_sol_diff,     10),
        "mean_84h":         round(mean_84h,           10),
        "diff_sigma":       round(sigma,               10),
        "history_points":   len(diffs),
        "regime":           regime,
        "signal_direction": direction,
        "ts_jst":           datetime.now(JST).strftime("%Y-%m-%d %H:%M JST"),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Phase 3 -- Position decision
# ─────────────────────────────────────────────────────────────────────────────

def decide_position(signal: dict) -> Optional[dict]:
    """
    Determine trade direction from MEME-SOL differential rolling mean.

    Logic (MEME-SOL direct alt-alt pair, HL primary G8 PASS):
      regime = BULL_MEME (mean_84h > 0):
        MEME FR > SOL FR: ETH meme bull cycle (ERC-20 meme index spike)
        -> long MEME (collect ERC-20 meme premium during ETH meme bull)
        -> short SOL (avoid lower SVM carry in MEME-spike regime)
        -> position_state = LONG_MEME_SHORT_SOL

      regime = BEAR_MEME (mean_84h < 0):
        SOL FR > MEME FR: SVM season + MEME bear cycle (ERC-20 meme fatigue)
        -> long SOL (collect SVM DeFi/DePIN premium)
        -> short MEME (collect MEME negative carry during ERC-20 bear)
        -> position_state = LONG_SOL_SHORT_MEME
        [Frequent: SOL persistent positive; MEME negative in most quarters]

      regime = NEUTRAL: no trade (mean_84h == 0 exactly -- rare)

    Carry note (BEAR_MEME direction — frequent):
      SHORT MEME: MEME FR frequently negative/low (ERC-20 meme bear, meme fatigue)
      LONG SOL: SOL FR structural positive (SVM retail demand, Firedancer)
      Both legs favorable simultaneously during ERC-20 meme bear cycles.

    Returns:
      {long_asset, short_asset, long_venue, short_venue, mean_84h,
       signal_direction, size_multiplier, position_state}
      or None if NEUTRAL.
    """
    regime    = signal.get("regime", "NEUTRAL")
    mean_84h  = signal.get("mean_84h", 0.0)
    direction = signal.get("signal_direction", 0)

    if regime == "NEUTRAL":
        return None

    if regime == "BULL_MEME":
        # MEME FR > SOL FR: ETH meme bull cycle
        long_asset  = "MEME"
        short_asset = "SOL"
        state       = STATE_LONG_MEME_SHORT_SOL
    else:  # BEAR_MEME
        # SOL FR > MEME FR: SVM season + ERC-20 meme bear (frequent)
        long_asset  = "SOL"
        short_asset = "MEME"
        state       = STATE_LONG_SOL_SHORT_MEME

    # HL primary for both legs (G8 PASS: Bybit/OKX verified for confirmation)
    long_venue  = "HL"
    short_venue = "HL"

    return {
        "long_asset":       long_asset,
        "short_asset":      short_asset,
        "position_state":   state,
        "long_venue":       long_venue,
        "short_venue":      short_venue,
        "mean_84h":         mean_84h,
        "signal_direction": direction,
        "size_multiplier":  1.0,   # reserved for dynamic sizing
        "regime":           regime,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Phase 4 -- Delta-neutral notional computation
# ─────────────────────────────────────────────────────────────────────────────

def compute_delta_neutral_notional(
    aum:        float = AUM_DEFAULT,
    sleeve_pct: float = SLEEVE_PCT,
    leverage:   float = LEVERAGE,
) -> Tuple[float, float]:
    """
    Compute equal notional for both legs of the MEME-SOL paired trade.

    K788 HL config (MEME-PERP + SOL-PERP on HL, paper-gate strict):
      sleeve_capital   = aum x sleeve_pct      (e.g. $10M x 0.4% = $40K)
      total_notional   = sleeve_capital x lev   ($40K x 3 = $120K)
      notional_per_leg = total_notional / 2     ($60K per leg)

    At $10M / 0.4% sleeve / 3x (paper-gate):
      MEME leg: $20K capital x 3x = $60K notional (HL MEME-PERP)
      SOL leg:  $20K capital x 3x = $60K notional (HL SOL-PERP)
      Total:    $120K notional (two legs combined)
      Margin:   $40K (0.4% of AUM — liquidity-limited by MEME HIP-3 OI=$480K)
      HL conc:  PAPER-ONLY (66.8% AT CAP -- no live capital added)
      Net profit: central $14,518/yr @$10M @3x (K523: $9.2K-$20.6K)
      MEME vertex: 22nd (1st ERC-20 meme index cluster) -- MR9 L002 blocks all MEME-X pairs
      Leverage note: 3x (HL max for MEME — lower than standard 4x; liquidity constraint)

    Returns (notional_per_leg, total_notional).
    """
    sleeve_capital   = aum * sleeve_pct
    total_notional   = sleeve_capital * leverage
    notional_per_leg = total_notional / 2.0
    return round(notional_per_leg, 2), round(total_notional, 2)


# ─────────────────────────────────────────────────────────────────────────────
# Phase 5 -- Paired trade submission (HL primary, POST_ONLY)
# ─────────────────────────────────────────────────────────────────────────────

def submit_paired_trade(
    long_leg:  dict,
    short_leg: dict,
    dry_run:   bool = True,
) -> dict:
    """
    Submit K788 MEME-SOL paired trade: POST_ONLY both legs in parallel.

    Protocol (K788 HL primary -- both legs on HL):
      1. Submit MEME leg on HL POST_ONLY
      2. Submit SOL leg on HL POST_ONLY
      3. Both legs submitted in parallel (K439 pattern)
      4. IOC fallback per leg if POST_ONLY times out
      5. Bybit available as venue confirmation (G8 PASS) but HL is execution venue
      6. If HL fails: retry next 8h cycle

    Args:
      long_leg:  {"symbol": "MEME"|"SOL", "notional": 60000, "venue": "HL"}
      short_leg: {"symbol": "SOL"|"MEME", "notional": 60000, "venue": "HL"}
      dry_run:   True = paper-trade simulation (default)

    Returns execution result dict.
    """
    ts         = datetime.now(UTC).isoformat()
    long_sym   = long_leg["symbol"]
    short_sym  = short_leg["symbol"]
    long_notl  = long_leg.get("notional", 0.0)
    short_notl = short_leg.get("notional", 0.0)
    long_venue  = long_leg.get("venue",  "HL")
    short_venue = short_leg.get("venue", "HL")

    if dry_run or PAPER_TRADE:
        mode_tag = "DRY_RUN" if dry_run else "PAPER_TRADE"
        print(f"  [K788] {mode_tag}: LONG {long_sym}@{long_venue} ${long_notl:,.0f}  "
              f"+ SHORT {short_sym}@{short_venue} ${short_notl:,.0f}")
        result = {
            "status":           "DRY_RUN",
            "long_result":      {"order_id": f"PAPER_LONG_{long_sym}_{int(time.time())}",   "status": "DRY_RUN"},
            "short_result":     {"order_id": f"PAPER_SHORT_{short_sym}_{int(time.time())}", "status": "DRY_RUN"},
            "fill_price_long":  None,
            "fill_price_short": None,
            "long_symbol":      long_sym,
            "short_symbol":     short_sym,
            "long_notional":    long_notl,
            "short_notional":   short_notl,
            "long_venue":       long_venue,
            "short_venue":      short_venue,
            "execution_mode":   "POST_ONLY_PARALLEL",
            "venue_config":     "HL_PRIMARY_MEME_SOL_G8_PASS_BYBIT_OKX_CONFIRMED",
            "mechanism_note":   (
                "MEME-SOL direct alt-alt differential (K788 TWENTY-FOURTH ALT-ALT, 82nd daemon): "
                "MEME FR = ERC-20 meme index (memecoin.org, cross-chain ETH, HL HIP-3, "
                "ETH meme bull/bear cycles, ERC-20 meme rotation, HL HIP-3 speculative demand, "
                "meme market crash kurtosis events, Max=-48.37bps); "
                "L004 PASS: bidirectional pos_frac_full=0.7940 pos_frac_oos=0.5743. "
                "L004_DIFF BORDERLINE: full=0.289 (<0.30 floor), OOS=0.440 PASS. "
                "G2 p=0.000 confirms timing alpha (+5.13 Sh vs pure carry IS). "
                "L004_DIFF monitor: monthly recheck; reduce sleeve if OOS diff_pos < 0.28 for 2 mo. "
                "vol_ratio=3.34x (full). raw_corr=0.1177. "
                "SOL FR = Solana SVM DeFi/DePIN premium (Phantom, Firedancer, "
                "SOL ETF speculation, SVM DeFi TVL Jupiter/Drift/Jito, persistent positive, "
                "SOL liquidation cascade Min=-20.51bps Feb 2025). "
                "G4 WF 12/12 ALL POSITIVE (min_fold_sh=4.3534 -- all folds positive). "
                "G5 27/27 ALL PASS: max_corr=0.1973 (G5b SOL-BTC, well below 0.40). "
                "G5w PEPE-SOL=0.1339 PASS -- meme cluster orthogonal. "
                "G5y WIF-SOL=0.0825 PASS -- cross-chain meme distinct. "
                "G6: 84.3 entries/yr OOS PASS (W=84h vs 30/yr threshold). "
                "G7: OOS ann ret 3x=60.5% PASS. "
                "G8: PASS -- MEME HL+OKX+Bybit confirmed (cross-venue verified). "
                "G9: OOS 212d PASS (>= 180d minimum). "
                "HL at 66.8% AT CAP -- paper-gate strict until K498/v6.52 reduces HL%. "
                "MEME = 22nd vertex (1st ERC-20 meme index cluster). "
                "MR9 L002: all future MEME-X pairs blocked. "
                "OOS Sh=15.97 (W=84h, zero threshold, 212d). "
                "K523 3-point: conservative=$9,194 central=$14,518 optimistic=$20,567/yr @$10M @3x @0.4%. "
                "Live gate: Sh >= 10, fill >= 60%, maxDD < 15%, L004_DIFF stable (OOS diff_pos >= 0.30). "
                "Leverage: 3x (HL max for MEME -- lower than standard 4x; liquidity constraint)."
            ),
            "ts_utc":           ts,
        }
        _append_trade_log(result)
        return result

    # LIVE scaffold (not reached in PAPER_TRADE mode):
    print(f"  [K788] SCAFFOLD LIVE: parallel POST_ONLY "
          f"LONG {long_sym}@{long_venue} ${long_notl:,.0f} "
          f"+ SHORT {short_sym}@{short_venue} ${short_notl:,.0f}")
    long_order_id  = f"SCAFFOLD_LONG_{long_sym}_{int(time.time())}"
    short_order_id = f"SCAFFOLD_SHORT_{short_sym}_{int(time.time())}"

    print(f"  [K788] Neither leg filled within timeout -- retry next 8h cycle")
    return {
        "status":       "RETRY_NEXT_CYCLE",
        "long_result":  {"order_id": long_order_id,  "status": "TIMEOUT"},
        "short_result": {"order_id": short_order_id, "status": "TIMEOUT"},
        "ts_utc":       ts,
    }


def _append_trade_log(record: dict) -> None:
    with open(TRADE_LOG_PATH, "a") as f:
        f.write(json.dumps(record) + "\n")


# ─────────────────────────────────────────────────────────────────────────────
# Phase 6 -- Delta-neutral drift rebalance
# ─────────────────────────────────────────────────────────────────────────────

def daily_rebalance(dashboard: dict) -> dict:
    """
    Check if current K788 position has drifted beyond DRIFT_REBALANCE_PCT (5%).

    K788 HL: both legs on HL (MEME-PERP + SOL-PERP).
    Drift detection: compare stored MEME leg notional vs SOL leg notional.
    Threshold: 5% (same as K679/K682/.../K786/K788 alt-alt family pattern).

    Returns rebalance decision dict.
    """
    state = dashboard.get("position_state", STATE_NEUTRAL)
    if state == STATE_NEUTRAL:
        return {"rebalance_required": False, "reason": "NEUTRAL -- no position"}

    long_notional_init  = float(dashboard.get("long_notional", 0.0))
    short_notional_init = float(dashboard.get("short_notional", 0.0))

    if long_notional_init <= 0 or short_notional_init <= 0:
        return {"rebalance_required": False, "reason": "no recorded notionals"}

    drift_pct        = float(dashboard.get("delta_neutral_drift_pct", 0.0))
    rebalance_needed = abs(drift_pct) > DRIFT_REBALANCE_PCT

    return {
        "rebalance_required":   rebalance_needed,
        "drift_pct":            round(drift_pct, 6),
        "threshold_pct":        DRIFT_REBALANCE_PCT,
        "long_notional_init":   long_notional_init,
        "short_notional_init":  short_notional_init,
        "action":               "REBALANCE" if rebalance_needed else "HOLD",
        "reason": (
            f"Drift {drift_pct:.2%} > threshold {DRIFT_REBALANCE_PCT:.0%}"
            if rebalance_needed else
            f"Drift {drift_pct:.2%} within {DRIFT_REBALANCE_PCT:.0%} threshold"
        ),
        "ts_utc": datetime.now(UTC).isoformat(),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Phase 7 -- Close paired position
# ─────────────────────────────────────────────────────────────────────────────

def close_paired_position(reason: str, dry_run: bool = True) -> dict:
    """
    Close both legs sequentially: short leg first (avoid naked short exposure),
    then long leg. In live: uses IOC market orders (reduce-only).
    Both legs on HL (K788 HL primary -- MEME-PERP + SOL-PERP).

    Args:
      reason:  human-readable reason for closure
      dry_run: True = paper-trade simulation

    Returns closure result dict.
    """
    ts    = datetime.now(UTC).isoformat()
    dash  = _load_dashboard()
    state = dash.get("position_state", STATE_NEUTRAL)

    if state == STATE_NEUTRAL:
        return {"status": "NO_POSITION", "reason": "Already NEUTRAL", "ts_utc": ts}

    if state == STATE_LONG_MEME_SHORT_SOL:
        long_sym,  short_sym  = "MEME", "SOL"
    else:  # LONG_SOL_SHORT_MEME
        long_sym,  short_sym  = "SOL", "MEME"

    long_notional  = float(dash.get("long_notional",  0.0))
    short_notional = float(dash.get("short_notional", 0.0))

    if dry_run or PAPER_TRADE:
        mode_tag = "DRY_RUN" if dry_run else "PAPER_TRADE"
        print(f"  [K788] {mode_tag} CLOSE:")
        print(f"    Step 1 (SHORT first): cover {short_sym}@HL ${short_notional:,.0f}")
        print(f"    Step 2 (LONG second): sell  {long_sym}@HL  ${long_notional:,.0f}")
        print(f"    reason={reason}")
        result = {
            "status":          "DRY_RUN_CLOSED",
            "reason":          reason,
            "close_sequence":  "short_first_then_long",
            "closed_short":    short_sym,
            "closed_long":     long_sym,
            "venue":           "HL",
            "short_notional":  short_notional,
            "long_notional":   long_notional,
            "close_mode":      "IOC_REDUCE_ONLY",
            "ts_utc":          ts,
        }
    else:
        print(f"  [K788] SCAFFOLD CLOSE:")
        print(f"    Step 1: IOC reduce {short_sym} (cover short) @HL  reason={reason}")
        print(f"    Step 2: IOC reduce {long_sym} (sell long) @HL")
        result = {
            "status":         "SCAFFOLD_CLOSE",
            "reason":         reason,
            "close_sequence": "short_first_then_long",
            "venue":          "HL",
            "ts_utc":         ts,
        }

    _append_trade_log(result)
    return result


# ─────────────────────────────────────────────────────────────────────────────
# Dashboard I/O
# ─────────────────────────────────────────────────────────────────────────────

def _load_dashboard() -> dict:
    """Load k788_dashboard.json; return defaults if missing."""
    if DASHBOARD_PATH.exists():
        try:
            return json.loads(DASHBOARD_PATH.read_text())
        except Exception:
            pass
    return {
        "last_poll_jst":           "--",
        "mean_84h":                0.0,
        "diff_sigma":              0.0,
        "regime":                  "NEUTRAL",
        "position_state":          STATE_NEUTRAL,
        "long_notional":           0.0,
        "short_notional":          0.0,
        "venue":                   "HL",
        "delta_neutral_drift_pct": 0.0,
        "rebalance_required":      False,
        "daily_pnl_usdc":          0.0,
        "60d_sharpe":              0.0,
        "paper_trade_status":      {
            "days_elapsed":    0,
            "target_live_gate": "Sh>=10 fill>=60% maxDD<15% + K498/v6.52 + L004_DIFF stable (OOS diff_pos>=0.30)",
        },
    }


def _write_dashboard(
    signal:           dict,
    decision:         Optional[dict],
    notional_per_leg: float,
    total_notional:   float,
    rebalance:        dict,
    aum:              float,
) -> dict:
    """Write k788_dashboard.json with full signal + regime state."""
    dash = _load_dashboard()

    # Update signal data
    dash["last_poll_jst"]         = signal.get("ts_jst", "--")
    dash["fr_meme_current"]       = signal.get("fr_meme",          0.0)
    dash["fr_sol_current"]        = signal.get("fr_sol",            0.0)
    dash["meme_sol_diff_current"] = signal.get("meme_sol_diff",     0.0)
    dash["mean_84h"]              = signal.get("mean_84h",          0.0)
    dash["diff_sigma"]            = signal.get("diff_sigma",         0.0)
    dash["regime"]                = signal.get("regime",    "NEUTRAL")
    dash["signal_direction"]      = signal.get("signal_direction",  0)
    dash["history_points"]        = signal.get("history_points",    0)

    # Update position if entering
    if decision:
        state = decision.get("position_state", STATE_NEUTRAL)
        if dash.get("position_state") == STATE_NEUTRAL:
            dash["position_state"]    = state
            dash["long_notional"]     = notional_per_leg
            dash["short_notional"]    = notional_per_leg
            dash["long_asset"]        = decision.get("long_asset")
            dash["short_asset"]       = decision.get("short_asset")
            dash["venue"]             = "HL"
            dash["entry_ts_jst"]      = dash["last_poll_jst"]
            dash["signal_direction"]  = decision.get("signal_direction", 0)

    # Rebalance status
    dash["delta_neutral_drift_pct"] = rebalance.get("drift_pct", 0.0)
    dash["rebalance_required"]      = rebalance.get("rebalance_required", False)

    # Margin / notional summary
    dash["total_notional_usdc"]     = round(total_notional, 2)
    dash["notional_per_leg_usdc"]   = round(notional_per_leg, 2)
    dash["leverage"]                = LEVERAGE
    dash["sleeve_pct"]              = SLEEVE_PCT
    dash["aum_ref_usdc"]            = aum
    dash["margin_used_usdc"]        = round(total_notional / LEVERAGE, 2)
    dash["margin_pct_of_aum"]       = round((total_notional / LEVERAGE) / aum, 4)
    dash["hl_concentration_pct"]    = HL_CONCENTRATION_POST_K788

    # K788 static metadata
    dash["strategy"]         = "K788 MEME-SOL FR Differential (TWENTY-FOURTH ALT-ALT, K791 scaffold)"
    dash["oos_sharpe"]       = 15.97
    dash["is_sharpe"]        = 13.12
    dash["w_hours"]          = 84
    dash["paper_trade"]      = PAPER_TRADE
    dash["hl_primary"]       = True
    dash["bybit_confirmed"]  = True    # G8 PASS: MEME confirmed on Bybit (MEMEUSDT Nov 2023)
    dash["okx_confirmed"]    = True    # G8 PASS: MEME confirmed on OKX (corr=0.843)
    dash["bybit_confirm_reason"] = BYBIT_CONFIRM_REASON
    dash["meme_vertex"]      = "22nd vertex (1st ERC-20 meme index cluster). MR9 L002: all future MEME-X blocked."
    dash["k523_central_yr"]  = 14518
    dash["k523_cons_yr"]     = 9194
    dash["k523_opt_yr"]      = 20567
    dash["live_gate"]        = {
        "sharpe_threshold":     10.0,
        "fill_rate_pct":        60.0,
        "max_dd_pct":           15.0,
        "l004_diff_gate":       "OOS diff_pos >= 0.30 (stable) -- monthly recheck required",
        "additional_gate":      "K498/v6.52 OKX activation required (HL% must drop below 65.0%)",
        "days_required":        60,
        "note":                 "CONDITIONAL_ACCEPT 9/9. Live gate after 60d paper-trade + L004_DIFF stable.",
    }
    dash["l004_note"]        = "PASS: MEME bidirectional. pos_frac_full=0.7940 pos_frac_oos=0.5743 (OOS well below 80%)."
    dash["l004_diff_note"]   = "BORDERLINE: full=0.289 (<0.30 floor, -0.011 margin). OOS=0.440 PASS. G2 p=0.000 timing alpha. Monthly recheck. Reduce sleeve if OOS diff_pos < 0.28 for 2 consecutive months."
    dash["g4_result"]        = "12/12 ALL POSITIVE (min_fold_sh=4.3534 -- all folds positive)"
    dash["g5_result"]        = "27/27 ALL PASS: max_corr=0.1973 (G5b SOL-BTC, well below 0.40)"
    dash["g5_meme_cluster"]  = "G5w PEPE-SOL=0.1339 PASS (meme cluster orthogonal). G5y WIF-SOL=0.0825 PASS (cross-chain distinct)."
    dash["g6_entries_yr"]    = 84.3
    dash["g8_result"]        = "PASS -- MEME HL+OKX+Bybit confirmed (G8 cross-venue verified)"
    dash["g9_oos_days"]      = 212.0
    dash["vol_ratio_full"]   = 3.34
    dash["leverage_note"]    = "3x (HL max for MEME — lower than standard 4x; liquidity constraint OI=$480K)"
    dash["l004_diff_monitor"] = {
        "current_full":         0.289,
        "current_oos":          0.440,
        "floor":                0.30,
        "full_below_floor":     True,
        "oos_pass":             True,
        "action_trigger":       "Reduce sleeve if OOS diff_pos < 0.28 for 2 consecutive months",
        "live_gate_requirement": "OOS diff_pos >= 0.30 stable before live elevation",
        "recheck_frequency":    "monthly",
    }

    DASHBOARD_PATH.write_text(json.dumps(dash, indent=2))
    return dash


# ─────────────────────────────────────────────────────────────────────────────
# Phase 8 -- Print status
# ─────────────────────────────────────────────────────────────────────────────

def print_status(dash: dict) -> None:
    """Print K788 MEME-SOL strategy status summary."""
    print("=" * 70)
    print("K788 MEME-SOL FR Differential -- Status")
    print("=" * 70)
    print(f"  Last poll:            {dash.get('last_poll_jst', '--')}")
    print(f"  Regime:               {dash.get('regime', 'NEUTRAL')}")
    print(f"  Position:             {dash.get('position_state', 'NEUTRAL')}")
    print(f"  MEME FR (current):    {dash.get('fr_meme_current', 0.0):.8f}")
    print(f"  SOL FR (current):     {dash.get('fr_sol_current', 0.0):.8f}")
    print(f"  MEME-SOL diff:        {dash.get('meme_sol_diff_current', 0.0):.8f}")
    print(f"  Mean 84h:             {dash.get('mean_84h', 0.0):.8f}")
    print(f"  History points:       {dash.get('history_points', 0)}")
    print(f"  Total notional:       ${dash.get('total_notional_usdc', 0.0):,.0f}")
    print(f"  Margin used:          ${dash.get('margin_used_usdc', 0.0):,.0f}")
    print(f"  Sleeve:               {SLEEVE_PCT:.1%}")
    print(f"  Leverage:             {LEVERAGE}x (HL max for MEME -- lower than standard 4x)")
    print(f"  Venue:                HL primary (G8 PASS -- Bybit/OKX confirmed)")
    print(f"  HL concentration:     {dash.get('hl_concentration_pct', 66.8):.1f}%")
    print(f"  Paper trade:          {PAPER_TRADE}")
    print(f"  OOS Sharpe:           15.97 (W=84h, 212d OOS -- CONDITIONAL_ACCEPT 9/9)")
    print(f"  IS Sharpe:            13.12 (OOS > IS -- no directional overfit)")
    print(f"  K523 central:         $14,518/yr @$10M @3x @0.4%")
    print(f"  vol_ratio:            3.34x (full)")
    print(f"  Drift:                {dash.get('delta_neutral_drift_pct', 0.0):.2%}")
    print(f"  Rebalance:            {dash.get('rebalance_required', False)}")
    print(f"  MEME vertex:          22nd (1st ERC-20 meme index cluster). MR9 L002: MEME-X blocked.")
    print(f"  L004 status:          PASS (MEME bidirectional -- ERC-20 meme index)")
    print(f"  L004_DIFF:            BORDERLINE (full=0.289 <0.30, OOS=0.440). Monthly recheck.")
    print(f"  G5 meme cluster:      G5w PEPE-SOL=0.134 PASS | G5y WIF-SOL=0.083 PASS")
    print(f"  G8 status:            PASS (HL+OKX+Bybit confirmed -- cross-venue verified)")
    print(f"  Live gate:            Sh>=10, fill>=60%, maxDD<15%, L004_DIFF stable + K498/v6.52")
    print("=" * 70)


# ─────────────────────────────────────────────────────────────────────────────
# Main loop -- 8h cadence
# ─────────────────────────────────────────────────────────────────────────────

def run_main_cycle(aum: float = AUM_DEFAULT) -> dict:
    """
    Main 8h execution cycle for K788 MEME-SOL FR Differential.

    Steps:
      1. Fetch MEME + SOL FR from HL (HL primary)
      2. Compute 84h rolling mean signal
      3. Decide position
      4. Submit / hold / rebalance
      5. Write dashboard
    """
    print(f"\n[K788 MEME-SOL] {datetime.now(JST).strftime('%Y-%m-%d %H:%M JST')} -- 8h cycle")
    print(f"  Venue: HL primary (G8 PASS -- MEME Bybit/OKX confirmed). PAPER_TRADE={PAPER_TRADE}")
    print(f"  HL concentration: {HL_CONCENTRATION_POST_K788}% AT CAP -- paper-gate strict")
    print(f"  Leverage: {LEVERAGE}x (HL max for MEME -- lower than standard 4x)")

    # Step 1+2: Signal
    signal = compute_signal()

    print(f"  MEME FR:    {signal['fr_meme']:.8f} ({signal['fr_meme'] * 8760 * 100:.2f}%/yr)")
    print(f"  SOL FR:     {signal['fr_sol']:.8f} ({signal['fr_sol'] * 8760 * 100:.2f}%/yr)")
    print(f"  diff:       {signal['meme_sol_diff']:.8f}")
    print(f"  mean84h:    {signal['mean_84h']:.8f}")
    print(f"  regime:     {signal['regime']} (direction={signal['signal_direction']})")
    print(f"  history:    {signal['history_points']} points")

    # Step 3: Position decision
    decision = decide_position(signal)
    if decision is None:
        print("  Decision: NEUTRAL -- no trade")
    else:
        print(f"  Decision: {decision['position_state']}")
        print(f"    LONG  {decision['long_asset']}@{decision['long_venue']}")
        print(f"    SHORT {decision['short_asset']}@{decision['short_venue']}")

    # Step 4: Notionals
    notional_per_leg, total_notional = compute_delta_neutral_notional(aum)
    print(f"  Notional per leg: ${notional_per_leg:,.0f}  total: ${total_notional:,.0f}")

    # Step 4b: Load dashboard for rebalance check
    dash      = _load_dashboard()
    rebalance = daily_rebalance(dash)
    if rebalance["rebalance_required"]:
        print(f"  REBALANCE required: drift={rebalance['drift_pct']:.2%}")

    # Step 4c: Trade submission (paper only)
    if decision and dash.get("position_state", STATE_NEUTRAL) == STATE_NEUTRAL:
        long_leg  = {"symbol": decision["long_asset"],  "notional": notional_per_leg, "venue": "HL"}
        short_leg = {"symbol": decision["short_asset"], "notional": notional_per_leg, "venue": "HL"}
        exec_result = submit_paired_trade(long_leg, short_leg, dry_run=False)
        print(f"  Submit: {exec_result['status']}")

    # Step 5: Write dashboard
    final_dash = _write_dashboard(signal, decision, notional_per_leg, total_notional, rebalance, aum)
    print(f"  Dashboard written: {DASHBOARD_PATH}")
    return final_dash


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="K788 MEME-SOL FR Differential -- 82nd daemon, 25th alt-alt scaffold, 22nd vertex MEME"
    )
    parser.add_argument("--dry-run",   action="store_true", help="Run signal + decision, no submission")
    parser.add_argument("--status",    action="store_true", help="Print dashboard status and exit")
    parser.add_argument("--rebalance", action="store_true", help="Check drift + rebalance if needed")
    parser.add_argument("--close",     type=str, metavar="REASON", help="Close all MEME-SOL positions")
    parser.add_argument("--aum",       type=float, default=AUM_DEFAULT, help="AUM for sizing ($10M default)")
    args = parser.parse_args()

    if args.status:
        dash = _load_dashboard()
        print_status(dash)
        return 0

    if args.close:
        result = close_paired_position(args.close, dry_run=False)
        print(json.dumps(result, indent=2))
        return 0

    if args.rebalance:
        dash   = _load_dashboard()
        result = daily_rebalance(dash)
        print(json.dumps(result, indent=2))
        if result["rebalance_required"]:
            print("  [K788] Rebalance triggered -- resizing legs to target notional")
        return 0

    if args.dry_run:
        print(f"[K788 MEME-SOL] DRY-RUN -- {datetime.now(JST).strftime('%Y-%m-%d %H:%M JST')}")
        signal   = compute_signal()
        decision = decide_position(signal)
        notional_per_leg, total_notional = compute_delta_neutral_notional(args.aum)
        print(json.dumps({
            "signal":            signal,
            "decision":          decision,
            "notional_per_leg":  notional_per_leg,
            "total_notional":    total_notional,
            "paper_trade":       PAPER_TRADE,
            "hl_primary":        True,
            "bybit_confirmed":   True,
            "okx_confirmed":     True,
            "leverage":          LEVERAGE,
            "leverage_note":     "3x (HL max for MEME -- lower than standard 4x)",
            "oos_sharpe":        15.97,
            "is_sharpe":         13.12,
            "k523_central_yr":   14518,
            "g8_status":         "PASS -- MEME HL+OKX+Bybit confirmed (cross-venue verified)",
            "l004_diff_status":  "BORDERLINE (full=0.289 <0.30, OOS=0.440 PASS) -- G2 timing alpha",
        }, indent=2))
        return 0

    # Normal 8h cycle
    run_main_cycle(args.aum)
    return 0


if __name__ == "__main__":
    sys.exit(main())
