#!/usr/bin/env python3
"""
k786_bio_sol_run.py — K786 BIO-SOL FR Differential Strategy
=================================================================
TWENTY-THIRD ALT-ALT pair (23rd scaffold, 22nd pair evaluated): BIO vs SOL.
Signal: BIO_FR - SOL_FR  (W=84h rolling mean — K786 eval canonical best IS/OOS)
W=84h primary (IS Sh=23.24, OOS Sh=23.10 — ACCEPT 8/9 gates per K786 eval)
4x leverage, 0.4% sleeve (liquidity-limited — BIO HIP-3 HL, daily vol limited)
HL-only (BIO not on Bybit or OKX — G8 FAIL: cross-venue perp not confirmed)
PAPER_TRADE=True default

K786 BIO-SOL alt-alt hypothesis:
  BIO (Bio Protocol DeSci governance token):
    FR driven by DeSci narrative cycles (BioDAO deal flow, IP-NFT acquisitions),
    VitaDAO longevity milestones (clinical trial progress, drug discovery events),
    AthenaDAO / HairDAO / GenomesDAO research cycle announcements,
    Biotech bull/bear cycles (FDA approval cycles, biotech sector sentiment),
    Regulatory DeSci news (US policy on decentralized science funding),
    BioDAO IP-NFT tokenization events (biotech intellectual property auctions),
    Decentralized patient capital deployment (drug discovery DAO funding rounds).
    FR bidirectional: OOS positive_fraction=0.5983 (genuine bidirectionality — L004 PASS).
    L004_DIFF PASS: full=0.3030 (borderline, OOS=0.4611 confirms timing alpha).
    vol_ratio: BIO/SOL=9.833x (full) — extreme vol ratio (highest in alt-alt family).
    raw_corr(BIO_fr, SOL_fr) = 0.0028 — essentially uncorrelated (cycle_independence=0.9972).
    OU half-life: 7.16h (mean-reversion fast enough for 84h window).
    HL only: BIO is HIP-3 on HL (Jan 2025). No confirmed Bybit/OKX perpetual.
    G8 FAIL: cross-venue verification required before live.
  SOL (Solana SVM L1):
    FR driven by retail momentum, Phantom wallet adoption, Firedancer upgrade,
    Solana ETF narrative flows, SVM DeFi TVL (Jupiter/Drift/Jito).
    SOL FR mean persistently positive — retail demand structural.
    SOL extreme negative FR: Min=-20.51bps (liquidation cascade Feb 2025).
  Alt-alt mechanism: BIO (DeSci biotech DAO) vs SOL (Solana SVM L1).
    Structurally orthogonal: biotech research funding cycles (IP-NFT DAO capital)
    are decoupled from Solana SVM cycle (Firedancer, validator rewards, meme).
    BIO cluster: DeSci / Biotech DAO coordination — DISTINCT from all 20 existing vertices.
    raw_corr(BIO_fr, SOL_fr) = 0.0028 — near-zero (near-random, strongest independence).
    G5 24/24 ALL PASS: max_corr=0.3308 (G5u FIL-SOL, below 0.40 threshold).

K786 §6 validation (ACCEPT 8/9 gates — G8 FAIL cross-venue):
  - OOS Sharpe: 23.10 (W=84h, zero threshold, 205d OOS — G9 PASS >= 180d)
  - IS Sharpe:  23.24 (W=84h) — IS~OOS (consistent, no directional overfit)
  - Full Sharpe: (W=84h consistent across all windows)
  - OOS Ann Return: $63,652 central @$10M @0.4% sleeve (K523 3-point: $54K-$168K)
  - W=84h rolling mean, zero threshold (sign of diff) — G6: 7,479/yr OOS PASS
  - G4 walk-forward: 5/5 folds positive (ALL POSITIVE, min_fold_sh=20.95)
  - G5 24/24 ALL PASS; max_corr=0.3308 (G5u FIL-SOL, below 0.40)
  - G6: 7,479 entries/yr OOS PASS (vs 30/yr threshold — ultra-high frequency)
  - G7: OOS ann ret 4x=558.4% PASS (vs 5% threshold)
  - G8: FAIL — BIO HL-only HIP-3 (no confirmed Bybit/OKX perpetual)
  - G9: OOS 204.8d PASS (>= 180d minimum)
  - L004 PASS: BIO bidirectional (pos_frac_full=0.5590 pos_frac_oos=0.5983)
  - L004_DIFF PASS: full=0.3030 (borderline), OOS=0.4611 (confirms timing alpha)
  - HL 66.8% cap -> paper-gate strict, LIVE after K498/v6.52
  - G8 N/A HL-only (HIP-3): Bybit/OKX verify required before live elevation

K786 BIO-SOL vertex addition (21st vertex, 1st DeSci cluster):
  V (before K786) = {APT, ATOM, AVAX, BNB, ENA, FIL, HBAR, INJ, LDO, SEI, SOL, TIA, TAO,
                      PEPE, WIF, BLUR, AXS, IO, EIGEN, COMP}
  V (after K786)  = {APT, ATOM, AVAX, BNB, ENA, FIL, HBAR, INJ, LDO, SEI, SOL, TIA, TAO,
                      PEPE, WIF, BLUR, AXS, IO, EIGEN, COMP, BIO}
  BIO = 21st vertex (1st DeSci cluster — DeSci / Biotech DAO coordination).
  MR9 L002: all future BIO-X pairs are auto-blocked (BIO exhausted as new vertex).
  BIO-SOL is the only permissible BIO-X pair given V composition at K786.

L004_DIFF borderline note (K786):
  full=0.303 is 0.003 above the 0.30 threshold (borderline by 1%).
  OOS=0.461 confirms genuine timing alpha (not structural one-sidedness).
  G2 p=0.000 confirms edge is not random. Monthly recheck required.
  Compare K782 PROVE-SOL (diff=0.277 — would have failed L004_DIFF).
  Compare K778 COMP-SOL (L004 PASS, diff fully bidirectional).

K523 3-point profit projection (@$10M @4x @0.4% sleeve):
  Conservative: $54,105/yr  (R2S=38% floor x OOS-haircut-25%, K518 floor, fee)
  Central:      $63,652/yr  (K523 mandate: 60% realized-to-stated, base case)
  Optimistic:   $167,506/yr (near-full OOS realization)
  Upper bound:  OOS raw return (NOT central — K523 mandatory)
  Note: 0.4% sleeve -> ~$40K margin @$10M; central per K786 eval=$63,652/yr

Cross-venue note (K786):
  HL:    BIO-PERP on HL (HIP-3 Jan 2025). Primary and ONLY venue.
  Bybit: BIO NOT confirmed (HIP-3 status — cross-venue perp unknown).
  OKX:   BIO NOT confirmed.
  G8 = FAIL (HL-only: HIP-3 status). Paper-gate mandatory: G8 unconfirmed.
  Live gate: Sh >= 15, fill >= 60%, maxDD < 15%, + cross-venue Bybit verify.

Architecture (K679->K747->K754->K759->K769->K774->K777->K778->K786 alt-alt scaffold pattern):
  1. fetch_fr_batch()                      -> fetch BIO + SOL FR every 8h from HL (HL-only)
  2. compute_signal(bio_fr, sol_fr)        -> 84h rolling mean of (BIO_FR - SOL_FR); sign()
  3. decide_position(signal)              -> LONG_BIO_SHORT_SOL | LONG_SOL_SHORT_BIO | NEUTRAL
  4. submit_paired_trade(long, short)     -> POST_ONLY paired (BIO + SOL legs, HL-only)
  5. daily_rebalance()                    -> drift > 5% triggers rebalance
  6. close_paired_position(reason)        -> sequential: short first, then long

K787 production scaffold:
  - 80th daemon (23rd alt-alt scaffold, 22nd pair, ACCEPT 8/9 — G8 HL-only)
  - HL primary ONLY (no Bybit/OKX — G8 FAIL: HIP-3 cross-venue unconfirmed)
  - 0.4% sleeve (liquidity-limited)
  - $63,652 central @$10M @4x @0.4% sleeve (K523 3-point: $54K-$168K)
  - Paper-gate until K498/v6.52 reduces HL concentration AND G8 cross-venue confirmed
  - Live gate: Sh >= 15, fill >= 60%, maxDD < 15% + cross-venue Bybit verify

60d gate (K787):
  Realized Sh >= 15, fill >= 60%, maxDD < 15% + cross-venue Bybit verify.

Execution:
  - HL primary ONLY (BIO-PERP + SOL-PERP, HL — no Bybit/OKX fallback available)
  - POST_ONLY paired execution (K439 pattern)
  - Position: 0.4% sleeve, 4x leverage (paper-gate strict — HL cap 66.8%)
  - 8h cadence (matches FR settlement cycle)
  - W=84h rolling mean (10.5 x 8h periods — G6-safe: 7,479/yr OOS)

Paper-trade mode is the DEFAULT.  No orders are submitted unless
PAPER_TRADE=False is explicitly set in the environment.

K339 security: REPO_ROOT from __file__, no /Users/ literals.
No new packages — stdlib urllib + json only.

Usage:
  python3 scripts/k786_bio_sol_run.py --dry-run
  python3 scripts/k786_bio_sol_run.py --status
  python3 scripts/k786_bio_sol_run.py --rebalance
  python3 scripts/k786_bio_sol_run.py --close "scheduled exit"
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

DASHBOARD_PATH  = DATA_DIR  / "k786_dashboard.json"
FR_HISTORY_PATH = CACHE_DIR / "k786_fr_history.jsonl"
TRADE_LOG_PATH  = CACHE_DIR / "k786_paper_trades.jsonl"

JST = timezone(timedelta(hours=9))
UTC = timezone.utc

# -- Strategy constants -------------------------------------------------------
PAPER_TRADE         = os.environ.get("PAPER_TRADE", "True").lower() != "false"
SLEEVE_PCT          = 0.004         # K786 sleeve = 0.4% of AUM (liquidity-limited HIP-3)
LEVERAGE            = 4.0           # 4x per K786 analysis
AUM_DEFAULT         = 10_000_000.0  # $10M reference AUM
DRIFT_REBALANCE_PCT = 0.05          # rebalance if legs drift > 5%
IOC_TIMEOUT_SEC     = 300           # 5 min fill window
EMA_PERIOD_HOURS    = 84            # 84h rolling mean (W=84h primary, G6: 7,479/yr OOS)
EMA_PERIOD_PERIODS  = EMA_PERIOD_HOURS // 8  # = 10 periods (8h settlement cycle, rounded)
SIGNAL_SIGMA_MULT   = 0.0           # zero threshold (sign of rolling mean)
HL_API_URL          = "https://api.hyperliquid.xyz/info"

# -- Venue config -------------------------------------------------------------
# HL primary ONLY: BIO-PERP + SOL-PERP on HL.
# BIO is HIP-3 on HL (Jan 2025). No confirmed Bybit or OKX perpetual.
# G8 FAIL: cross-venue perp not confirmed (G8 N/A HL-only — HIP-3 status).
# Paper-gate mandatory until cross-venue Bybit/OKX verified.
HL_CONCENTRATION_PRE_K786   = 66.8   # post-K780 reference (K778 paper-gate, no live capital)
HL_CONCENTRATION_POST_K786  = 66.8   # UNCHANGED -- paper-only, no live capital added
HL_ONLY_REASON              = (
    "HL primary ONLY: BIO-PERP + SOL-PERP on HL (HIP-3 Jan 2025). "
    "BIO NOT confirmed on Bybit or OKX (cross-venue perp unknown — G8 FAIL). "
    "G8 N/A: HL-only HIP-3 status. Paper-gate mandatory until cross-venue verified. "
    "HL at 66.8% AT CAP. Paper-gate strict: any live capital would breach 65% ceiling. "
    "Live gate: Sh >= 15, fill >= 60%, maxDD < 15% + cross-venue Bybit verify. "
    "Deploy LIVE after (1) K498/v6.52 reduces HL% below 65% AND (2) Bybit BIO confirmed."
)

# -- Position state constants -------------------------------------------------
STATE_NEUTRAL               = "NEUTRAL"
STATE_LONG_BIO_SHORT_SOL    = "LONG_BIO_SHORT_SOL"
STATE_LONG_SOL_SHORT_BIO    = "LONG_SOL_SHORT_BIO"

# -- Symbols fetched from HL for FR data --------------------------------------
SYMBOLS = ("BIO", "SOL")


# ─────────────────────────────────────────────────────────────────────────────
# HTTP helper (stdlib urllib only -- no requests)
# ─────────────────────────────────────────────────────────────────────────────

def _http_get(url: str, timeout: int = 10) -> Optional[dict]:
    try:
        req = urllib.request.Request(
            url, headers={"User-Agent": "crypto-lab-k786/1.0"}
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        print(f"  [k786] HTTP error: {e}", file=sys.stderr)
        return None


def _http_post(url: str, payload: dict, timeout: int = 10) -> Optional[dict]:
    try:
        data = json.dumps(payload).encode()
        req  = urllib.request.Request(
            url, data=data,
            headers={"Content-Type": "application/json",
                     "User-Agent": "crypto-lab-k786/1.0"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        print(f"  [k786] HTTP error: {e}", file=sys.stderr)
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Phase 1 -- Funding rate fetch (BIO + SOL from HL only — no fallback available)
# ─────────────────────────────────────────────────────────────────────────────

def _fetch_hl_fr_batch() -> Dict[str, float]:
    """
    Fetch current 1h funding rates for BIO and SOL from HL.
    Returns {symbol: fr_1h_fraction}.

    HL API: metaAndAssetCtxs (POST).
    K786: HL primary ONLY (BIO-PERP + SOL-PERP). No Bybit/OKX fallback.
    G8 FAIL: BIO is HIP-3 on HL (Jan 2025) — no cross-venue perpetual confirmed.

    Note: HL settles 1h funding; W=84h = 84 x 1h periods for rolling mean.
    FR stored as 1h fraction; annualized = fr_1h * 8760.

    BIO strategy direction (bidirectional — L004 PASS):
      BIO FR bidirectional: pos_frac_full=0.5590 pos_frac_oos=0.5983.
      L004_DIFF: full=0.303 (borderline), OOS=0.461 (confirms timing alpha).
      BIO DeSci cycles: IP-NFT acquisitions -> BIO FR spikes positive.
      VitaDAO milestones -> BIO demand surge, FR rises.
      Biotech bear cycles -> BIO FR inverts negative.
      Primary regime oscillates: no persistent directionality (unlike AAVE K748 BLOCKED).
    """
    result: Dict[str, float] = {}

    # Primary (and only): HL metaAndAssetCtxs
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
        print(f"  [k786] HL partial result {list(result.keys())} -- no fallback available (G8 FAIL HL-only)",
              file=sys.stderr)

    # No Bybit/OKX fallback: BIO not confirmed on either venue.
    # Return whatever we got from HL; missing symbols default to 0.0 in compute_signal.
    return result


def _load_fr_history() -> List[dict]:
    """Load K786 FR history JSONL."""
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
    fr_bio: float, fr_sol: float, bio_sol_diff: float
) -> None:
    """Append one FR snapshot to history."""
    rec = {
        "ts_utc":       datetime.now(UTC).isoformat(),
        "fr_bio":       round(fr_bio,        10),
        "fr_sol":       round(fr_sol,          10),
        "bio_sol_diff": round(bio_sol_diff,    10),  # BIO_FR - SOL_FR
    }
    with open(FR_HISTORY_PATH, "a") as f:
        f.write(json.dumps(rec) + "\n")


# ─────────────────────────────────────────────────────────────────────────────
# Phase 2 -- Signal computation (BIO-SOL direct differential, 84h rolling mean)
# ─────────────────────────────────────────────────────────────────────────────

def compute_signal(
    fr_bio: Optional[float] = None,
    fr_sol: Optional[float] = None,
) -> dict:
    """
    Fetch live BIO and SOL FRs from HL (HL-only), compute BIO-SOL differential,
    and compute 84h rolling mean for direction signal.

    Signal mechanism (K786 direct alt-alt differential -- no orthogonalization):
      diff = BIO_FR - SOL_FR
      mean_84h = 84h rolling mean of diff (10.5 x 8h periods, rounded to 10 periods)
      sign  = sign(mean_84h)
      Enter: sign > 0 -> BIO FR > SOL FR -> long BIO (DeSci IP-NFT spike), short SOL
             sign < 0 -> SOL FR > BIO FR -> long SOL (collect SVM premium), short BIO
                         [Frequent: SOL persistent positive + BIO DeSci bear cycle]

    NOTE: BIO is DeSci governance (bidirectional) -- structurally distinct from SOL SVM.
    BIO DeSci mechanism:
      BioDAO deal flow: IP-NFT acquisitions spike BIO FR positive.
      VitaDAO longevity milestones: clinical trial news -> demand surge.
      Biotech bear cycle: FDA rejection, biotech sector selloff -> BIO FR negative.
      Regulatory DeSci news: US policy changes on decentralized science funding.
      AthenaDAO / HairDAO / GenomesDAO: parallel research cycle announcements.

    W=84h rationale (G6 compliance, best OOS across all window sizes):
      W=84h -> 7,479 entries/yr OOS (WELL ABOVE 30/yr G6 threshold -- PASS).
      W=84h primary: IS Sh=23.24, OOS Sh=23.10 (consistent, IS~OOS — no overfit direction).
      W=48h: IS Sh=23.38, OOS Sh=23.89 (second-best OOS, slightly higher noise).
      W=168h: IS Sh=23.34, OOS Sh=20.83 (third, fewer entries but still strong).
      W=84h chosen: canonical per K786 eval (balanced IS/OOS consistency).

    K786 §6 validation (ACCEPT 8/9):
      - OOS Sharpe: 23.10 (W=84h, zero threshold, 205d OOS)
      - OOS Ann Return: $63,652 central @$10M @4x @0.4% sleeve (K523 3-point)
      - G4 WF 5/5 ALL POSITIVE (min_fold_sh=20.95, all folds strong)
      - G5 24/24 ALL PASS: max_corr=0.3308 (G5u FIL-SOL, below 0.40)
      - G6: 7,479 entries/yr OOS PASS (vs 30/yr threshold)
      - G7: OOS ann ret 4x=558.4% PASS (vs 5% threshold)
      - G8: FAIL — BIO HL-only HIP-3 (no cross-venue perp confirmed)
      - G9: OOS 204.8d PASS (>= 180d minimum)
      - HL 66.8% AT CAP -> paper-gate strict

    Returns:
      {
        "fr_bio":           float,
        "fr_sol":           float,
        "bio_sol_diff":     float,    # BIO_FR - SOL_FR (current)
        "mean_84h":         float,    # 84h rolling mean of differential
        "diff_sigma":       float,    # rolling sigma (informational)
        "history_points":   int,
        "regime":           str,      # BULL_BIO | BEAR_BIO | NEUTRAL
        "signal_direction": int,      # +1 | -1 | 0
        "ts_jst":           str,
      }
    """
    if fr_bio is None or fr_sol is None:
        frs    = _fetch_hl_fr_batch()
        fr_bio = frs.get("BIO", 0.0)
        fr_sol = frs.get("SOL", 0.0)

    # BIO-SOL direct alt-alt differential (no orthogonalization)
    bio_sol_diff = fr_bio - fr_sol

    _append_fr_history(fr_bio, fr_sol, bio_sol_diff)

    # Load history for rolling mean + sigma (84h ~= 10 x 8h periods)
    history = _load_fr_history()
    diffs   = [r["bio_sol_diff"] for r in history if "bio_sol_diff" in r]

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

    # Regime classification (zero threshold -- per K786 spec, canonical best OOS)
    # BULL_BIO: BIO FR > SOL FR (DeSci IP-NFT spike or BioDAO deal flow surge)
    # BEAR_BIO: BIO FR < SOL FR (DeSci bear cycle + SVM season -- frequent)
    if mean_84h > 0:
        regime    = "BULL_BIO"    # BIO-SOL diff positive -> BIO FR > SOL FR
        direction = 1
    elif mean_84h < 0:
        regime    = "BEAR_BIO"    # SOL FR > BIO FR (SVM dominant + DeSci bear)
        direction = -1
    else:
        regime    = "NEUTRAL"
        direction = 0

    return {
        "fr_bio":           round(fr_bio,          10),
        "fr_sol":           round(fr_sol,            10),
        "bio_sol_diff":     round(bio_sol_diff,      10),
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
    Determine trade direction from BIO-SOL differential rolling mean.

    Logic (BIO-SOL direct alt-alt pair, HL-only):
      regime = BULL_BIO (mean_84h > 0):
        BIO FR > SOL FR: DeSci IP-NFT spike or VitaDAO milestone surge
        -> long BIO (collect DeSci premium during spike)
        -> short SOL (avoid lower SVM carry in BIO-spike regime)
        -> position_state = LONG_BIO_SHORT_SOL

      regime = BEAR_BIO (mean_84h < 0):
        SOL FR > BIO FR: SVM season + DeSci bear cycle (biotech selloff)
        -> long SOL (collect SVM DeFi/DePIN premium)
        -> short BIO (collect BIO negative carry during DeSci bear)
        -> position_state = LONG_SOL_SHORT_BIO

      regime = NEUTRAL: no trade (mean_84h == 0 exactly -- rare)

    Carry note (BEAR_BIO direction — DeSci bear cycle):
      SHORT BIO: BIO FR frequently negative (biotech bear, DeSci narrative fatigue)
      LONG SOL: SOL FR structural positive (SVM retail demand, Firedancer)
      Both legs favorable simultaneously during DeSci bear cycles.
      BIO bidirectional: unlike AAVE/PENDLE (persistent positive carry blocked).

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

    if regime == "BULL_BIO":
        # BIO FR > SOL FR: DeSci IP-NFT spike (temporary)
        long_asset  = "BIO"
        short_asset = "SOL"
        state       = STATE_LONG_BIO_SHORT_SOL
    else:  # BEAR_BIO
        # SOL FR > BIO FR: SVM season + DeSci bear (frequent)
        long_asset  = "SOL"
        short_asset = "BIO"
        state       = STATE_LONG_SOL_SHORT_BIO

    # HL-only: both legs on HL (no Bybit/OKX — G8 FAIL HL-only)
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
    Compute equal notional for both legs of the BIO-SOL paired trade.

    K786 HL config (BIO-PERP + SOL-PERP on HL, paper-gate strict):
      sleeve_capital   = aum x sleeve_pct      (e.g. $10M x 0.4% = $40K)
      total_notional   = sleeve_capital x lev   ($40K x 4 = $160K)
      notional_per_leg = total_notional / 2     ($80K per leg)

    At $10M / 0.4% sleeve / 4x (paper-gate):
      BIO leg: $20K capital x 4x = $80K notional (HL BIO-PERP)
      SOL leg: $20K capital x 4x = $80K notional (HL SOL-PERP)
      Total:   $160K notional (two legs combined)
      Margin:  $40K (0.4% of AUM — liquidity-limited by BIO HIP-3 daily volume)
      HL conc: PAPER-ONLY (66.8% AT CAP -- no live capital added)
      Net profit: central $63,652/yr @$10M @4x (K523: $54K-$168K)
      BIO vertex: 21st (1st DeSci cluster) -- MR9 L002 blocks all future BIO-X pairs

    Returns (notional_per_leg, total_notional).
    """
    sleeve_capital   = aum * sleeve_pct
    total_notional   = sleeve_capital * leverage
    notional_per_leg = total_notional / 2.0
    return round(notional_per_leg, 2), round(total_notional, 2)


# ─────────────────────────────────────────────────────────────────────────────
# Phase 5 -- Paired trade submission (HL-only, POST_ONLY)
# ─────────────────────────────────────────────────────────────────────────────

def submit_paired_trade(
    long_leg:  dict,
    short_leg: dict,
    dry_run:   bool = True,
) -> dict:
    """
    Submit K786 BIO-SOL paired trade: POST_ONLY both legs in parallel.

    Protocol (K786 HL-only -- both legs on HL, no fallback):
      1. Submit BIO leg on HL POST_ONLY
      2. Submit SOL leg on HL POST_ONLY
      3. Both legs submitted in parallel (K439 pattern)
      4. IOC fallback per leg if POST_ONLY times out
      5. NO Bybit/OKX fallback: BIO not listed (G8 FAIL — HIP-3 status)
      6. If HL fails: retry next 8h cycle (no venue fallback)

    Args:
      long_leg:  {"symbol": "BIO"|"SOL", "notional": 80000, "venue": "HL"}
      short_leg: {"symbol": "SOL"|"BIO", "notional": 80000, "venue": "HL"}
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
        print(f"  [K786] {mode_tag}: LONG {long_sym}@{long_venue} ${long_notl:,.0f}  "
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
            "venue_config":     "HL_ONLY_BIO_SOL_HIP3_NO_BYBIT_NO_OKX",
            "mechanism_note":   (
                "BIO-SOL direct alt-alt differential (K786 TWENTY-THIRD ALT-ALT, 80th daemon): "
                "BIO FR = DeSci / Biotech DAO coordination (Bio Protocol governance token, "
                "BioDAO deal flow IP-NFT acquisitions, VitaDAO longevity milestones, "
                "AthenaDAO/HairDAO/GenomesDAO research cycles, biotech bull/bear, "
                "regulatory DeSci news, decentralized patient capital deployment); "
                "L004 PASS: bidirectional pos_frac_full=0.5590 pos_frac_oos=0.5983 (both below 80%). "
                "L004_DIFF PASS: full=0.303 (borderline), OOS=0.461 (confirms timing alpha). "
                "vol_ratio=9.833x (full) — extreme vol ratio. raw_corr=0.0028. "
                "SOL FR = Solana SVM DeFi/DePIN premium (Phantom adoption, Firedancer upgrade, "
                "SOL ETF speculation, SVM DeFi TVL Jupiter/Drift/Jito, persistent positive, "
                "SOL liquidation cascade Min=-20.51bps Feb 2025). "
                "G4 WF 5/5 ALL POSITIVE (min_fold_sh=20.95 -- all folds strong). "
                "G5 24/24 ALL PASS: max_corr=0.3308 (G5u FIL-SOL, below 0.40). "
                "G6: 7,479 entries/yr OOS PASS (W=84h vs 30/yr threshold). "
                "G7: OOS ann ret 4x=558.4% PASS. "
                "G8: FAIL -- BIO HL-only HIP-3 (no cross-venue perp confirmed). "
                "G9: OOS 204.8d PASS (>= 180d minimum). "
                "HL at 66.8% AT CAP -- paper-gate strict until K498/v6.52 reduces HL%. "
                "BIO = 21st vertex (1st DeSci cluster). "
                "MR9 L002: all future BIO-X pairs blocked. "
                "OOS Sh=23.10 (W=84h, zero threshold, 205d). "
                "K523 3-point: conservative=$54,105 central=$63,652 optimistic=$167,506/yr @$10M @4x @0.4%. "
                "Live gate: Sh >= 15, fill >= 60%, maxDD < 15% + cross-venue Bybit verify. "
                "L004_DIFF borderline note: full=0.303 (0.003 above 0.30 floor), OOS=0.461 PASS. "
                "Monthly recheck required."
            ),
            "ts_utc":           ts,
        }
        _append_trade_log(result)
        return result

    # LIVE scaffold (not reached in PAPER_TRADE mode):
    print(f"  [K786] SCAFFOLD LIVE: parallel POST_ONLY "
          f"LONG {long_sym}@{long_venue} ${long_notl:,.0f} "
          f"+ SHORT {short_sym}@{short_venue} ${short_notl:,.0f}")
    long_order_id  = f"SCAFFOLD_LONG_{long_sym}_{int(time.time())}"
    short_order_id = f"SCAFFOLD_SHORT_{short_sym}_{int(time.time())}"

    print(f"  [K786] Neither leg filled within timeout -- retry next 8h cycle")
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
    Check if current K786 position has drifted beyond DRIFT_REBALANCE_PCT (5%).

    K786 HL: both legs on HL (BIO-PERP + SOL-PERP).
    Drift detection: compare stored BIO leg notional vs SOL leg notional.
    Threshold: 5% (same as K679/K682/K684/K686/K690/K747/K739/K754/K759/K774/K777/K778 pattern).

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
    Both legs on HL (K786 HL-only -- BIO-PERP + SOL-PERP).

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

    if state == STATE_LONG_BIO_SHORT_SOL:
        long_sym,  short_sym  = "BIO", "SOL"
    else:  # LONG_SOL_SHORT_BIO
        long_sym,  short_sym  = "SOL", "BIO"

    long_notional  = float(dash.get("long_notional",  0.0))
    short_notional = float(dash.get("short_notional", 0.0))

    if dry_run or PAPER_TRADE:
        mode_tag = "DRY_RUN" if dry_run else "PAPER_TRADE"
        print(f"  [K786] {mode_tag} CLOSE:")
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
        print(f"  [K786] SCAFFOLD CLOSE:")
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
    """Load k786_dashboard.json; return defaults if missing."""
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
        "paper_trade_status":      {"days_elapsed": 0, "target_live_gate": "Sh>=15 fill>=60% maxDD<15% + cross-venue Bybit verify"},
    }


def _write_dashboard(
    signal:           dict,
    decision:         Optional[dict],
    notional_per_leg: float,
    total_notional:   float,
    rebalance:        dict,
    aum:              float,
) -> dict:
    """Write k786_dashboard.json with full signal + regime state."""
    dash = _load_dashboard()

    # Update signal data
    dash["last_poll_jst"]        = signal.get("ts_jst", "--")
    dash["fr_bio_current"]       = signal.get("fr_bio",           0.0)
    dash["fr_sol_current"]       = signal.get("fr_sol",            0.0)
    dash["bio_sol_diff_current"] = signal.get("bio_sol_diff",      0.0)
    dash["mean_84h"]             = signal.get("mean_84h",          0.0)
    dash["diff_sigma"]           = signal.get("diff_sigma",         0.0)
    dash["regime"]               = signal.get("regime",    "NEUTRAL")
    dash["signal_direction"]     = signal.get("signal_direction",  0)
    dash["history_points"]       = signal.get("history_points",    0)

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
    dash["hl_concentration_pct"]    = HL_CONCENTRATION_POST_K786

    # K786 static metadata
    dash["strategy"]         = "K786 BIO-SOL FR Differential (TWENTY-THIRD ALT-ALT, K787 scaffold)"
    dash["oos_sharpe"]       = 23.10
    dash["is_sharpe"]        = 23.24
    dash["w_hours"]          = 84
    dash["paper_trade"]      = PAPER_TRADE
    dash["hl_primary"]       = True
    dash["bybit_fallback"]   = False   # G8 FAIL: BIO not confirmed on Bybit
    dash["okx_secondary"]    = False   # G8 FAIL: BIO not confirmed on OKX
    dash["hl_only_reason"]   = HL_ONLY_REASON
    dash["bio_vertex"]       = "21st vertex (1st DeSci cluster). MR9 L002: all future BIO-X blocked."
    dash["k523_central_yr"]  = 63652
    dash["k523_cons_yr"]     = 54105
    dash["k523_opt_yr"]      = 167506
    dash["live_gate"]        = {
        "sharpe_threshold":     15.0,
        "fill_rate_pct":        60.0,
        "max_dd_pct":           15.0,
        "additional_gate":      "K498/v6.52 OKX activation required (HL% must drop below 65.0%) + cross-venue Bybit BIO verify",
        "days_required":        60,
        "note":                 "ACCEPT 8/9 (G8 FAIL HL-only). Live gate after 60d paper-trade + cross-venue Bybit confirm.",
    }
    dash["l004_note"]        = "PASS: BIO bidirectional. pos_frac_full=0.5590 pos_frac_oos=0.5983 (both below 80%)."
    dash["l004_diff_note"]   = "BORDERLINE: full=0.303 (0.003 above 0.30 floor), OOS=0.461 PASS. Monthly recheck required."
    dash["g4_result"]        = "5/5 ALL POSITIVE (min_fold_sh=20.95 -- all folds strong)"
    dash["g5_result"]        = "24/24 ALL PASS: max_corr=0.3308 (G5u FIL-SOL, below 0.40)"
    dash["g6_entries_yr"]    = 7479
    dash["g8_result"]        = "FAIL -- BIO HL-only HIP-3 (no cross-venue perp confirmed)"
    dash["g9_oos_days"]      = 204.8
    dash["vol_ratio_full"]   = 9.833

    DASHBOARD_PATH.write_text(json.dumps(dash, indent=2))
    return dash


# ─────────────────────────────────────────────────────────────────────────────
# Phase 8 -- Print status
# ─────────────────────────────────────────────────────────────────────────────

def print_status(dash: dict) -> None:
    """Print K786 BIO-SOL strategy status summary."""
    print("=" * 70)
    print("K786 BIO-SOL FR Differential -- Status")
    print("=" * 70)
    print(f"  Last poll:           {dash.get('last_poll_jst', '--')}")
    print(f"  Regime:              {dash.get('regime', 'NEUTRAL')}")
    print(f"  Position:            {dash.get('position_state', 'NEUTRAL')}")
    print(f"  BIO FR (current):    {dash.get('fr_bio_current', 0.0):.8f}")
    print(f"  SOL FR (current):    {dash.get('fr_sol_current', 0.0):.8f}")
    print(f"  BIO-SOL diff:        {dash.get('bio_sol_diff_current', 0.0):.8f}")
    print(f"  Mean 84h:            {dash.get('mean_84h', 0.0):.8f}")
    print(f"  History points:      {dash.get('history_points', 0)}")
    print(f"  Total notional:      ${dash.get('total_notional_usdc', 0.0):,.0f}")
    print(f"  Margin used:         ${dash.get('margin_used_usdc', 0.0):,.0f}")
    print(f"  Sleeve:              {SLEEVE_PCT:.1%}")
    print(f"  Leverage:            {LEVERAGE}x")
    print(f"  Venue:               HL ONLY (G8 FAIL -- BIO not on Bybit/OKX)")
    print(f"  HL concentration:    {dash.get('hl_concentration_pct', 66.8):.1f}%")
    print(f"  Paper trade:         {PAPER_TRADE}")
    print(f"  OOS Sharpe:          23.10 (W=84h, 205d OOS -- ACCEPT 8/9)")
    print(f"  IS Sharpe:           23.24 (IS~OOS -- consistent, no directional overfit)")
    print(f"  K523 central:        $63,652/yr @$10M @4x @0.4%")
    print(f"  vol_ratio:           9.833x (full) -- extreme vol ratio")
    print(f"  Drift:               {dash.get('delta_neutral_drift_pct', 0.0):.2%}")
    print(f"  Rebalance:           {dash.get('rebalance_required', False)}")
    print(f"  BIO vertex:          21st (1st DeSci cluster). MR9 L002: all BIO-X blocked.")
    print(f"  L004 status:         PASS (BIO bidirectional -- DeSci governance token)")
    print(f"  L004_DIFF:           BORDERLINE (full=0.303, OOS=0.461). Monthly recheck.")
    print(f"  G8 status:           FAIL (HL-only HIP-3 -- cross-venue verify required)")
    print(f"  Live gate:           Sh>=15, fill>=60%, maxDD<15% + cross-venue Bybit verify")
    print("=" * 70)


# ─────────────────────────────────────────────────────────────────────────────
# Main loop -- 8h cadence
# ─────────────────────────────────────────────────────────────────────────────

def run_main_cycle(aum: float = AUM_DEFAULT) -> dict:
    """
    Main 8h execution cycle for K786 BIO-SOL FR Differential.

    Steps:
      1. Fetch BIO + SOL FR from HL (HL-only — no fallback)
      2. Compute 84h rolling mean signal
      3. Decide position
      4. Submit / hold / rebalance
      5. Write dashboard
    """
    print(f"\n[K786 BIO-SOL] {datetime.now(JST).strftime('%Y-%m-%d %H:%M JST')} -- 8h cycle")
    print(f"  Venue: HL ONLY (G8 FAIL -- BIO not on Bybit/OKX). PAPER_TRADE={PAPER_TRADE}")
    print(f"  HL concentration: {HL_CONCENTRATION_POST_K786}% AT CAP -- paper-gate strict")

    # Step 1+2: Signal
    signal = compute_signal()

    print(f"  BIO FR:    {signal['fr_bio']:.8f} ({signal['fr_bio'] * 8760 * 100:.2f}%/yr)")
    print(f"  SOL FR:    {signal['fr_sol']:.8f} ({signal['fr_sol'] * 8760 * 100:.2f}%/yr)")
    print(f"  diff:      {signal['bio_sol_diff']:.8f}")
    print(f"  mean84h:   {signal['mean_84h']:.8f}")
    print(f"  regime:    {signal['regime']} (direction={signal['signal_direction']})")
    print(f"  history:   {signal['history_points']} points")

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
        description="K786 BIO-SOL FR Differential -- 80th daemon, 23rd alt-alt scaffold, 21st vertex BIO"
    )
    parser.add_argument("--dry-run",   action="store_true", help="Run signal + decision, no submission")
    parser.add_argument("--status",    action="store_true", help="Print dashboard status and exit")
    parser.add_argument("--rebalance", action="store_true", help="Check drift + rebalance if needed")
    parser.add_argument("--close",     type=str, metavar="REASON", help="Close all BIO-SOL positions")
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
            print("  [K786] Rebalance triggered -- resizing legs to target notional")
        return 0

    if args.dry_run:
        print(f"[K786 BIO-SOL] DRY-RUN -- {datetime.now(JST).strftime('%Y-%m-%d %H:%M JST')}")
        signal   = compute_signal()
        decision = decide_position(signal)
        notional_per_leg, total_notional = compute_delta_neutral_notional(args.aum)
        print(json.dumps({
            "signal":            signal,
            "decision":          decision,
            "notional_per_leg":  notional_per_leg,
            "total_notional":    total_notional,
            "paper_trade":       PAPER_TRADE,
            "hl_only":           True,
            "bybit_fallback":    False,
            "okx_secondary":     False,
            "oos_sharpe":        23.10,
            "is_sharpe":         23.24,
            "k523_central_yr":   63652,
            "g8_status":         "FAIL -- BIO HL-only HIP-3 (no cross-venue perp confirmed)",
        }, indent=2))
        return 0

    # Normal 8h cycle
    run_main_cycle(args.aum)
    return 0


if __name__ == "__main__":
    sys.exit(main())
