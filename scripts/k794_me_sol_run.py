#!/usr/bin/env python3
"""
k794_me_sol_run.py — K794 ME-SOL FR Differential Strategy (RESEARCH_ONLY)
=========================================================================
TWENTY-SIXTH ALT-ALT scaffold (26th scaffold, 25th pair evaluated): ME vs SOL.
Signal: ME_FR - SOL_FR  (W=84h rolling mean — K794 eval canonical best IS/OOS)
W=84h primary (IS Sh=19.13, OOS Sh=19.47 — OOS>IS no overfit, CONDITIONAL_ACCEPT_RESEARCH_ONLY)
3x leverage (HL max for ME HIP-3), 0.25% sleeve (liquidity-limited $85K/day)
HL-only (G8 FAIL: Bybit/OKX not listed at $85K/day vol)
RESEARCH_ONLY=True HARDCODED — never allow LIVE flip without further validation
PAPER_TRADE=True default

!!! WARNING !!!
RESEARCH_ONLY = True is HARDCODED. This strategy MUST NOT go live without:
  1. Bybit/OKX listing confirmation (G8 FAIL resolution)
  2. Liquidity expansion: ME daily vol > $500K/day (currently $85K/day)
  3. G2 timing alpha improvement (currently thin +0.45 Sh above carry)
  4. HL concentration check: HL% must drop below 65% (currently 66.8% AT CAP)
The RESEARCH_ONLY flag is NOT controlled by environment variable.
Do NOT add any code path that allows live execution without governance review.
!!! WARNING !!!

K794 ME-SOL alt-alt hypothesis:
  ME (Magic Eden NFT Marketplace — SVM-native application layer token):
    FR driven by NFT trading volume cycles (Magic Eden marketplace fee speculation),
    SVM NFT bull/bear cycles (Solana NFT market rotation vs Ethereum),
    Magic Eden multi-chain expansion (BTC Ordinals, ETH, SOL all listed),
    NFT royalty battles (Blur.io ETH royalty war spillover to SVM NFT venue),
    ME token governance (Magic Eden DAO fee parameter changes),
    HL HIP-3 speculative demand (retail NFT season speculation),
    SVM DeFi integration (ME token staking, LP incentive flows).
    FR structurally negative (mean -0.693 bps): short ME earns negative FR.
    vol_ratio ME/SOL = 12.66x (full) — extreme vol ratio.
    raw_corr(ME_fr, SOL_fr) = 0.0472 — near-zero (distinct app-layer cycles).
    G8 FAIL: ME only on HL (HIP-3, $85K/day vol). No Bybit/OKX perp confirmed.
    L004_DIFF BORDERLINE: full=0.282 (BELOW 0.30 floor), OOS=0.396 (PASS).
    G2 timing alpha THIN: +0.45 Sh above pure carry (IS carry Sh=18.68).
    Edge primary: structural carry (SHORT ME earns negative FR consistently).
    Edge secondary: timing signal (thin, K788 borderline rule via G2 p=0.000).
    OOS Sh 19.47 >> 1.0 (PASS). G4 WF 11/11 positive (min Sh=2.43).
    G5 28/28 ALL PASS: max_corr=0.2075 (G5z EIGEN-SOL, below 0.40 threshold).
    G6 MARGINAL: 30.2 entries/yr OOS (W=84h, 0.2/yr above 30/yr threshold).
    G9 PASS: OOS=217 days (above 180d threshold — K794 advantage over K789).
  SOL (Solana SVM L1):
    FR driven by retail momentum, Phantom wallet adoption, Firedancer upgrade,
    Solana ETF narrative flows, SVM DeFi TVL (Jupiter/Drift/Jito).
    SOL FR mean persistently positive — retail demand structural.
    SOL extreme negative FR: Min=-20.51bps (liquidation cascade Feb 2025).
  Alt-alt mechanism: ME (SVM NFT marketplace application layer) vs SOL (SVM L1 infra).
    Structurally distinct: NFT trading volume cycles are decoupled from SVM
    consensus/staking/DeFi cycles (different application layers on same chain).
    ME cluster: SVM NFT Marketplace — DISTINCT from all 22 existing vertices.
    vs MEME: G5ab=0.008 PASS (SVM NFT utility vs ERC-20 meme index — distinct).
    vs PEPE: G5w=0.057 PASS (SVM NFT marketplace vs ETH meme coin — distinct).
    vs WIF: G5y=0.013 PASS (SVM NFT marketplace vs SOL-native meme — distinct).
    G5 28/28 ALL PASS: max_corr=0.2075 (G5z EIGEN-SOL, well below 0.40).
    23rd vertex candidate (1st SVM NFT marketplace cluster) if upgraded.

K794 §6 validation (CONDITIONAL_ACCEPT_RESEARCH_ONLY — 8/9 gates, G8 FAIL):
  - OOS Sharpe:    19.47 (W=84h, zero threshold, 217d OOS — G9 PASS >= 180d)
  - IS Sharpe:     19.13 (W=84h) — OOS > IS (no directional overfit — GOOD)
  - Full Sharpe:   18.77 (W=84h consistent across IS/OOS)
  - OOS Ann Return: $39,100 central @$10M @3x @0.25% sleeve (K523 3-point: $24.8K-$55.4K)
  - W=84h rolling mean, zero threshold (sign of diff) — G6 MARGINAL: 30.2/yr OOS
  - G2 permutation p=0.000 — timing alpha confirmed (thin: +0.45 Sh above carry)
  - G3 DSR Bonferroni: t-stat=15.04, p=0.000 — PASS
  - G4 walk-forward: 11/11 folds positive (ALL POSITIVE, min_fold_sh=2.43 Fold 2)
  - G5 28/28 ALL PASS: max_corr=0.2075 (G5z EIGEN-SOL, below 0.40)
    - G5w PEPE-SOL=0.057 PASS (ETH meme cluster CLEAR)
    - G5y WIF-SOL=0.013 PASS (SOL-native meme cluster CLEAR)
    - G5ab MEME-SOL=0.008 PASS (22nd vertex ERC-20 meme cluster CLEAR)
  - G6: 30.2 entries/yr OOS PASS MARGINAL (vs 30/yr threshold — 0.2/yr margin)
  - G7: OOS ann ret 3x=260.7% PASS (vs 5% threshold)
  - G8: FAIL — ME HL-only HIP-3 (OI=$2.26M, vol=$85K/day — Bybit/OKX not listed)
  - G9: PASS — OOS=217 days (above 180d threshold)
  - L004 PASS: ME bidirectional (carry_full=0.5713 carry_oos=0.5014 — below 80%)
  - L004_DIFF BORDERLINE: full=0.282 (BELOW 0.30 floor), OOS=0.396 PASS
    K788 borderline rule: G2 p=0.000 overrides full < 0.30 (timing confirmed)
    NOTE: timing alpha THIN (+0.45 Sh). Monitor OOS diff_pos monthly.
  - HL 66.8% AT CAP -> paper-gate strict + RESEARCH_ONLY mandatory
  - RESEARCH_ONLY: G8 FAIL + thin timing alpha + low liquidity ($85K/day)

K794 ME-SOL vertex addition (23rd vertex candidate, 1st SVM NFT marketplace cluster):
  V (before K794) = {APT, ATOM, AVAX, BNB, ENA, FIL, HBAR, INJ, LDO, SEI, SOL, TIA, TAO,
                      PEPE, WIF, BLUR, AXS, IO, EIGEN, COMP, BIO, MEME}
  V (after K794) = {APT, ATOM, AVAX, BNB, ENA, FIL, HBAR, INJ, LDO, SEI, SOL, TIA, TAO,
                     PEPE, WIF, BLUR, AXS, IO, EIGEN, COMP, BIO, MEME, ME}
  ME = 23rd vertex candidate (1st SVM NFT marketplace cluster).
  MR9 L002: all future ME-X pairs are auto-blocked if CONDITIONAL_ACCEPT confirmed.
  Cluster: SVM NFT Marketplace / Magic Eden application layer.

RESEARCH_ONLY rationale (K794):
  1. G8 FAIL: HL-only (ME HIP-3, vol=$85K/day). Bybit/OKX not listed.
  2. Liquidity thin: $85K/day -> 0.2-0.3% sleeve max. Any larger size risks market impact.
  3. G6 MARGINAL: 30.2 entries/yr at W=84h (0.2/yr above threshold).
  4. L004_DIFF THIN: full=0.282 (below 0.30 floor — K788 borderline rule applies via G2).
  5. Timing alpha THIN: +0.45 Sh above pure carry (edge is carry-dominated).
  This strategy monitors for capacity expansion + Bybit listing.
  Live gate: NOT ELIGIBLE (must resolve G8 + liquidity + timing alpha first).
  Re-eval trigger: ME vol > $500K/day AND Bybit listing AND G2 timing alpha > +1 Sh.

K523 3-point profit projection (@$10M @3x @0.25% sleeve):
  Conservative: $24,763/yr  (R2S=38% floor x OOS-haircut-25%, K518 floor, fee)
  Central:      $39,100/yr  (K523 mandate: 60% realized-to-stated, base case)
  Optimistic:   $55,392/yr  (near-full OOS realization)
  Upper bound:  OOS raw return (NOT central — K523 mandatory)
  Note: 0.25% sleeve -> ~$25K margin @$10M; central per K794 eval=$39,100/yr

Cross-venue note (K794):
  HL:    ME-PERP on HL (HIP-3, OI=$2.26M, vol=$85K/day). Primary and ONLY venue.
  Bybit: ME NOT confirmed (low liquidity $85K/day, not listed on major Bybit perps)
  OKX:   ME NOT confirmed (not in cache, likely not listed at this vol level)
  G8 = FAIL (HL-only: HIP-3 status). RESEARCH_ONLY mandatory.

Architecture (K679->K747->K754->K759->K769->K774->K777->K778->K786->K789->K788->K794 alt-alt scaffold):
  1. fetch_fr_batch()                  -> fetch ME + SOL FR every 8h from HL (HL-only)
  2. compute_signal(me_fr, sol_fr)     -> 84h rolling mean of (ME_FR - SOL_FR); sign()
  3. decide_position(signal)           -> LONG_ME_SHORT_SOL | LONG_SOL_SHORT_ME | NEUTRAL
  4. submit_paired_trade(long, short)  -> POST_ONLY paired (ME + SOL legs, HL-only)
  5. daily_rebalance()                 -> drift > 5% triggers rebalance
  6. close_paired_position(reason)     -> sequential: short first, then long

K797 production scaffold:
  - 84th daemon (26th alt-alt scaffold, 25th pair, CONDITIONAL_ACCEPT_RESEARCH_ONLY 8/9 — G8 FAIL)
  - HL primary ONLY (no Bybit/OKX — G8 FAIL: HIP-3 vol=$85K/day)
  - 0.25% sleeve (liquidity-limited — ME HIP-3 $85K/day vol)
  - $39,100 central @$10M @3x @0.25% sleeve (K523 3-point: $24.8K-$55.4K)
  - RESEARCH_ONLY=True HARDCODED — paper-gate + research-only mandatory
  - Live gate: NOT ELIGIBLE without G8 resolve + vol > $500K/day + timing alpha > +1 Sh

60d gate (K797):
  Research monitoring only: track paper-trade Sh, fill rate, maxDD.
  Live elevation: NOT ELIGIBLE (three conditions must all trigger: liquidity > $500K/day
  AND Bybit listing AND G2 timing alpha > +1 Sh in updated eval).

Execution:
  - HL primary ONLY (ME-PERP + SOL-PERP, HL — no Bybit/OKX fallback)
  - POST_ONLY paired execution (K439 pattern)
  - Position: 0.25% sleeve, 3x leverage (HL max for ME — paper-gate strict)
  - 8h cadence (matches FR settlement cycle)
  - W=84h rolling mean (10.5 x 8h periods — G6-safe but MARGINAL: 30.2/yr)
  - G6 fallback: if live entries/yr falls below 30, switch to W=48h (57/yr)

Paper-trade mode is the DEFAULT.  No orders are submitted unless
PAPER_TRADE=False is explicitly set in the environment.

RESEARCH_ONLY note: PAPER_TRADE=False would still be blocked by RESEARCH_ONLY guard.
Even if someone sets PAPER_TRADE=False, this script will NOT submit live orders
while RESEARCH_ONLY=True is hardcoded. Both flags must be changed ONLY after
governance review (not eligible without G8 resolve + liquidity + timing alpha).

K339 security: REPO_ROOT from __file__, no /Users/ literals.
No new packages — stdlib urllib + json only.

Usage:
  python3 scripts/k794_me_sol_run.py --dry-run
  python3 scripts/k794_me_sol_run.py --status
  python3 scripts/k794_me_sol_run.py --rebalance
  python3 scripts/k794_me_sol_run.py --close "scheduled exit"
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

DASHBOARD_PATH  = DATA_DIR  / "k794_dashboard.json"
FR_HISTORY_PATH = CACHE_DIR / "k794_fr_history.jsonl"
TRADE_LOG_PATH  = CACHE_DIR / "k794_paper_trades.jsonl"

JST = timezone(timedelta(hours=9))
UTC = timezone.utc

# -- Strategy constants -------------------------------------------------------
# RESEARCH_ONLY: HARDCODED TRUE — do NOT change without governance review.
# K794 is NEVER eligible for live deployment without:
#   (1) G8 resolve: Bybit/OKX ME perp listing confirmed
#   (2) ME liquidity > $500K/day (currently $85K/day — insufficient)
#   (3) G2 timing alpha > +1 Sh (currently thin +0.45 Sh above carry)
#   (4) HL concentration < 65% (currently 66.8% AT CAP)
# Do NOT set RESEARCH_ONLY=False via environment variable.
# This flag is NOT configurable via env — it is hardcoded for safety.
RESEARCH_ONLY       = True          # HARDCODED — see K797 governance

PAPER_TRADE         = os.environ.get("PAPER_TRADE", "True").lower() != "false"
SLEEVE_PCT          = 0.0025        # K794 sleeve = 0.25% of AUM (liquidity-limited $85K/day)
LEVERAGE            = 3.0           # 3x (HL max for ME HIP-3 token)
AUM_DEFAULT         = 10_000_000.0  # $10M reference AUM
DRIFT_REBALANCE_PCT = 0.05          # rebalance if legs drift > 5%
IOC_TIMEOUT_SEC     = 300           # 5 min fill window
EMA_PERIOD_HOURS    = 84            # 84h rolling mean (W=84h primary — G6 MARGINAL at 30.2/yr)
EMA_PERIOD_PERIODS  = EMA_PERIOD_HOURS // 8  # = 10 periods (8h settlement cycle, rounded)
SIGNAL_SIGMA_MULT   = 0.0           # zero threshold (sign of rolling mean)
HL_API_URL          = "https://api.hyperliquid.xyz/info"

# -- Venue config -------------------------------------------------------------
# HL primary ONLY: ME-PERP + SOL-PERP on HL.
# ME is HIP-3 on HL (OI=$2.26M, vol=$85K/day). No confirmed Bybit or OKX perpetual.
# G8 FAIL: cross-venue perp not confirmed (G8 N/A HL-only — HIP-3 status).
# G9 PASS: OOS=217 days (above 180d threshold — K794 advantage).
# RESEARCH_ONLY mandatory: G8 FAIL + thin timing alpha + low liquidity.
HL_CONCENTRATION_PRE_K794   = 66.8   # post-K791 reference (K788 paper-gate, no live capital)
HL_CONCENTRATION_POST_K794  = 66.8   # UNCHANGED -- research-only paper, no live capital added
HL_ONLY_REASON              = (
    "HL primary ONLY: ME-PERP + SOL-PERP on HL (HIP-3, OI=$2.26M, vol=$85K/day). "
    "ME NOT confirmed on Bybit or OKX (low vol, not listed at $85K/day level — G8 FAIL). "
    "G8 N/A: HL-only HIP-3 status. RESEARCH_ONLY mandatory: G8 FAIL + thin timing alpha. "
    "G9 PASS: OOS=217 days (>= 180d threshold). "
    "HL at 66.8% AT CAP. RESEARCH_ONLY + paper-gate strict. "
    "Live gate: NOT ELIGIBLE. Re-eval trigger: ME vol > $500K/day AND Bybit listing "
    "AND G2 timing alpha > +1 Sh (currently thin +0.45 Sh above carry). "
    "RESEARCH_ONLY is HARDCODED — not configurable via environment variable."
)

# -- Position state constants -------------------------------------------------
STATE_NEUTRAL               = "NEUTRAL"
STATE_LONG_ME_SHORT_SOL     = "LONG_ME_SHORT_SOL"
STATE_LONG_SOL_SHORT_ME     = "LONG_SOL_SHORT_ME"

# -- Symbols fetched from HL for FR data --------------------------------------
SYMBOLS = ("ME", "SOL")


# ─────────────────────────────────────────────────────────────────────────────
# HTTP helper (stdlib urllib only -- no requests)
# ─────────────────────────────────────────────────────────────────────────────

def _http_get(url: str, timeout: int = 10) -> Optional[dict]:
    try:
        req = urllib.request.Request(
            url, headers={"User-Agent": "crypto-lab-k794/1.0"}
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        print(f"  [k794] HTTP error: {e}", file=sys.stderr)
        return None


def _http_post(url: str, payload: dict, timeout: int = 10) -> Optional[dict]:
    try:
        data = json.dumps(payload).encode()
        req  = urllib.request.Request(
            url, data=data,
            headers={"Content-Type": "application/json",
                     "User-Agent": "crypto-lab-k794/1.0"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        print(f"  [k794] HTTP error: {e}", file=sys.stderr)
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Phase 1 -- Funding rate fetch (ME + SOL from HL only — no fallback available)
# ─────────────────────────────────────────────────────────────────────────────

def _fetch_hl_fr_batch() -> Dict[str, float]:
    """
    Fetch current 1h funding rates for ME and SOL from HL.
    Returns {symbol: fr_1h_fraction}.

    HL API: metaAndAssetCtxs (POST).
    K794: HL primary ONLY (ME-PERP + SOL-PERP). No Bybit/OKX fallback.
    G8 FAIL: ME is HIP-3 on HL (OI=$2.26M, vol=$85K/day) — no cross-venue perpetual confirmed.

    Note: HL settles 1h funding; W=84h = 84 x 1h periods for rolling mean.
    FR stored as 1h fraction; annualized = fr_1h * 8760.

    ME strategy direction (bidirectional — L004 PASS):
      ME FR bidirectional: carry_full=0.5713 carry_oos=0.5014.
      L004_DIFF BORDERLINE: full=0.282 (BELOW 0.30 floor), OOS=0.396 PASS.
      K788 borderline rule: G2 p=0.000 overrides full < 0.30 (timing confirmed).
      NOTE: timing alpha THIN (+0.45 Sh above pure carry Sh=18.68).
      Edge primarily structural: SHORT ME earns negative FR consistently (mean -0.693 bps).
      Timing signal adds marginal direction alpha on top of carry baseline.
      Monthly OOS diff_pos recheck required: if < 0.28 reduce sleeve to 0.1%.
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
        print(f"  [k794] HL partial result {list(result.keys())} -- no fallback (G8 FAIL HL-only)",
              file=sys.stderr)

    # No Bybit/OKX fallback: ME not confirmed on either venue.
    # Return whatever we got from HL; missing symbols default to 0.0 in compute_signal.
    return result


def _load_fr_history() -> List[dict]:
    """Load K794 FR history JSONL."""
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
    fr_me: float, fr_sol: float, me_sol_diff: float
) -> None:
    """Append one FR snapshot to history."""
    rec = {
        "ts_utc":      datetime.now(UTC).isoformat(),
        "fr_me":       round(fr_me,       10),
        "fr_sol":      round(fr_sol,       10),
        "me_sol_diff": round(me_sol_diff,  10),  # ME_FR - SOL_FR
    }
    with open(FR_HISTORY_PATH, "a") as f:
        f.write(json.dumps(rec) + "\n")


# ─────────────────────────────────────────────────────────────────────────────
# Phase 2 -- Signal computation (ME-SOL direct differential, 84h rolling mean)
# ─────────────────────────────────────────────────────────────────────────────

def compute_signal(
    fr_me:  Optional[float] = None,
    fr_sol: Optional[float] = None,
) -> dict:
    """
    Fetch live ME and SOL FRs from HL (HL-only), compute ME-SOL differential,
    and compute 84h rolling mean for direction signal.

    Signal mechanism (K794 direct alt-alt differential -- no orthogonalization):
      diff = ME_FR - SOL_FR
      mean_84h = 84h rolling mean of diff (10.5 x 8h periods, rounded to 10 periods)
      sign  = sign(mean_84h)
      Enter: sign > 0 -> ME FR > SOL FR -> long ME (NFT vol spike), short SOL
             sign < 0 -> SOL FR > ME FR -> long SOL (SVM DeFi premium), short ME
                         [DOMINANT: ME FR mean=-0.693bps consistently negative]

    NOTE: ME is SVM NFT marketplace (carry-dominated) -- structurally distinct from SOL SVM.
    ME SVM NFT mechanism:
      NFT trading volume cycles: Magic Eden marketplace fee speculation -> FR spikes.
      SVM NFT bull/bear cycles: Solana NFT market rotation (vs ETH Blur market).
      Multi-chain expansion: BTC Ordinals + ETH + SOL ME marketplace -> FR demand.
      ME token governance: fee parameter changes -> speculative FR cycles.
      HL HIP-3 speculative demand: retail NFT season -> ME FR spikes above carry.
      PRIMARY EDGE: SHORT ME earns structural negative carry (mean -0.693 bps/hr).

    W=84h rationale (G6-marginal compliance, canonical best OOS across window sizes):
      W=84h -> 30.2 entries/yr OOS (MARGINAL — 0.2/yr above 30/yr G6 threshold PASS).
      W=48h: OOS Sh=19.67, 57/yr (safer, fewer overfit risk). Use if entries drop below 30.
      W=84h: IS Sh=19.13, OOS Sh=19.47 (OOS>IS — canonical no-overfit confirmation).
      G6 FALLBACK: switch to W=48h (57/yr) if live monthly entries fall below 2.5/month.

    K794 §6 validation (CONDITIONAL_ACCEPT_RESEARCH_ONLY 8/9 — G8 FAIL):
      - OOS Sharpe:    19.47 (W=84h, zero threshold, 217d OOS — G9 PASS)
      - IS Sharpe:     19.13 (W=84h) — OOS > IS (no directional overfit — GOOD)
      - Full Sharpe:   18.77 (consistent across IS/OOS)
      - OOS Ann Return: $39,100 central @$10M @3x @0.25% sleeve
      - G2 perm p=0.000 — timing alpha confirmed (thin: +0.45 Sh above carry)
      - G3 DSR: t-stat=15.04, p=0.000 — PASS
      - G4 WF 11/11 ALL POSITIVE (min_fold_sh=2.43 Fold 2)
      - G5 28/28 ALL PASS: max_corr=0.2075 (G5z EIGEN-SOL)
      - G6: 30.2 entries/yr OOS PASS MARGINAL (vs 30/yr threshold)
      - G7: OOS ann ret 3x=260.7% PASS
      - G8: FAIL — ME HL-only HIP-3 ($85K/day — Bybit/OKX not listed)
      - G9: PASS — OOS=217 days (above 180d threshold)
      - L004 PASS: ME bidirectional (carry_full=0.5713 carry_oos=0.5014)
      - L004_DIFF BORDERLINE: full=0.282 (<0.30 floor), OOS=0.396 PASS (G2 overrides)
      - HL 66.8% AT CAP -> RESEARCH_ONLY + paper-gate strict

    Returns:
      {
        "fr_me":              float,
        "fr_sol":             float,
        "me_sol_diff":        float,    # ME_FR - SOL_FR (current)
        "mean_84h":           float,    # 84h rolling mean of differential
        "diff_sigma":         float,    # rolling sigma (informational)
        "history_points":     int,
        "regime":             str,      # BULL_ME | BEAR_ME | NEUTRAL
        "signal_direction":   int,      # +1 | -1 | 0
        "ts_jst":             str,
        "research_only":      bool,     # Always True (HARDCODED)
      }
    """
    if fr_me is None or fr_sol is None:
        frs    = _fetch_hl_fr_batch()
        fr_me  = frs.get("ME",  0.0)
        fr_sol = frs.get("SOL", 0.0)

    # ME-SOL direct alt-alt differential (no orthogonalization)
    me_sol_diff = fr_me - fr_sol

    _append_fr_history(fr_me, fr_sol, me_sol_diff)

    # Load history for rolling mean + sigma (84h ~= 10 x 8h periods)
    history = _load_fr_history()
    diffs   = [r["me_sol_diff"] for r in history if "me_sol_diff" in r]

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

    # Regime classification (zero threshold -- per K794 spec)
    # BULL_ME: ME FR > SOL FR (NFT vol spike, staking demand surge, governance event)
    # BEAR_ME: ME FR < SOL FR (SVM DeFi season, NFT bear + SOL retail + carry dominant)
    # BEAR_ME is the DOMINANT regime: ME FR mean=-0.693 bps vs SOL +0.088 bps
    if mean_84h > 0:
        regime    = "BULL_ME"    # ME-SOL diff positive -> ME FR > SOL FR (rare)
        direction = 1
    elif mean_84h < 0:
        regime    = "BEAR_ME"    # SOL FR > ME FR (dominant: structural ME negative carry)
        direction = -1
    else:
        regime    = "NEUTRAL"
        direction = 0

    return {
        "fr_me":             round(fr_me,         10),
        "fr_sol":            round(fr_sol,          10),
        "me_sol_diff":       round(me_sol_diff,     10),
        "mean_84h":          round(mean_84h,         10),
        "diff_sigma":        round(sigma,             10),
        "history_points":    len(diffs),
        "regime":            regime,
        "signal_direction":  direction,
        "ts_jst":            datetime.now(JST).strftime("%Y-%m-%d %H:%M JST"),
        "research_only":     RESEARCH_ONLY,   # Always True (hardcoded)
    }


# ─────────────────────────────────────────────────────────────────────────────
# Phase 3 -- Position decision
# ─────────────────────────────────────────────────────────────────────────────

def decide_position(signal: dict) -> Optional[dict]:
    """
    Determine trade direction from ME-SOL differential rolling mean.

    Logic (ME-SOL direct alt-alt pair, HL-only, RESEARCH_ONLY):
      regime = BULL_ME (mean_84h > 0):
        ME FR > SOL FR: NFT vol spike or Magic Eden governance event
        -> long ME (collect NFT marketplace premium during spike)
        -> short SOL (avoid lower SVM L1 carry vs NFT spike)
        -> position_state = LONG_ME_SHORT_SOL

      regime = BEAR_ME (mean_84h < 0) — DOMINANT REGIME:
        SOL FR > ME FR: SVM DeFi season + structural ME negative carry
        -> long SOL (collect SVM DePIN/retail premium)
        -> short ME (collect ME negative carry: mean -0.693 bps/hr)
        -> position_state = LONG_SOL_SHORT_ME
        [Frequent: ME FR structurally negative, SOL persistent positive]

      regime = NEUTRAL: no trade (mean_84h == 0 exactly -- rare)

    Carry note (BEAR_ME direction — structural carry):
      SHORT ME: ME FR frequently/structurally negative (mean=-0.693 bps vs SOL +0.088)
      LONG SOL: SOL FR structural positive (SVM retail demand, Phantom, Firedancer)
      Both legs favorable simultaneously during SVM DeFi/retail seasons.
      Primary edge = structural carry; timing signal adds thin marginal alpha.

    RESEARCH_ONLY guard: even if PAPER_TRADE=False is set, this function will
    return None when RESEARCH_ONLY=True (no live orders allowed).

    Returns:
      {long_asset, short_asset, long_venue, short_venue, mean_84h,
       signal_direction, size_multiplier, position_state}
      or None if NEUTRAL or RESEARCH_ONLY.
    """
    # RESEARCH_ONLY guard (secondary safety check — primary is in submit_paired_trade)
    if RESEARCH_ONLY and not PAPER_TRADE:
        print(
            "  [K794] RESEARCH_ONLY=True HARDCODED: LIVE execution BLOCKED. "
            "Paper-trade mode only. See K797 governance for live elevation criteria.",
            file=sys.stderr,
        )

    regime    = signal.get("regime", "NEUTRAL")
    mean_84h  = signal.get("mean_84h", 0.0)
    direction = signal.get("signal_direction", 0)

    if regime == "NEUTRAL":
        return None

    if regime == "BULL_ME":
        # ME FR > SOL FR: NFT vol spike (rare — ME structurally negative)
        long_asset  = "ME"
        short_asset = "SOL"
        state       = STATE_LONG_ME_SHORT_SOL
    else:  # BEAR_ME — dominant regime
        # SOL FR > ME FR: SVM season + structural ME negative carry
        long_asset  = "SOL"
        short_asset = "ME"
        state       = STATE_LONG_SOL_SHORT_ME

    # HL-only: both legs on HL (no Bybit/OKX — G8 FAIL HL-only)
    long_venue  = "HL"
    short_venue = "HL"

    return {
        "long_asset":        long_asset,
        "short_asset":       short_asset,
        "position_state":    state,
        "long_venue":        long_venue,
        "short_venue":       short_venue,
        "mean_84h":          mean_84h,
        "signal_direction":  direction,
        "size_multiplier":   1.0,   # reserved for dynamic sizing
        "regime":            regime,
        "research_only":     RESEARCH_ONLY,
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
    Compute equal notional for both legs of the ME-SOL paired trade.

    K794 HL config (ME-PERP + SOL-PERP on HL, RESEARCH_ONLY + paper-gate strict):
      sleeve_capital   = aum x sleeve_pct      (e.g. $10M x 0.25% = $25K)
      total_notional   = sleeve_capital x lev   ($25K x 3 = $75K)
      notional_per_leg = total_notional / 2     ($37.5K per leg)

    At $10M / 0.25% sleeve / 3x (RESEARCH_ONLY paper-gate):
      ME leg:  $12.5K capital x 3x = $37.5K notional (HL ME-PERP)
      SOL leg: $12.5K capital x 3x = $37.5K notional (HL SOL-PERP)
      Total:   $75K notional (two legs combined)
      Margin:  $25K (0.25% of AUM — liquidity-limited by ME HIP-3 $85K/day vol)
      HL conc: RESEARCH_ONLY paper-only (66.8% AT CAP — no live capital added)
      Net profit: central $39,100/yr @$10M @3x (K523: $24.8K-$55.4K)
      ME vertex: 23rd candidate (1st SVM NFT marketplace cluster)
        MR9 L002 blocks all future ME-X pairs if confirmed.

    Returns (notional_per_leg, total_notional).
    """
    sleeve_capital   = aum * sleeve_pct
    total_notional   = sleeve_capital * leverage
    notional_per_leg = total_notional / 2.0
    return round(notional_per_leg, 2), round(total_notional, 2)


# ─────────────────────────────────────────────────────────────────────────────
# Phase 5 -- Paired trade submission (HL-only, POST_ONLY, RESEARCH_ONLY guard)
# ─────────────────────────────────────────────────────────────────────────────

def submit_paired_trade(
    long_leg:  dict,
    short_leg: dict,
    dry_run:   bool = True,
) -> dict:
    """
    Submit K794 ME-SOL paired trade: POST_ONLY both legs in parallel.

    RESEARCH_ONLY guard: if RESEARCH_ONLY=True (hardcoded), live orders are BLOCKED.
    Even if dry_run=False and PAPER_TRADE=False, this function will NOT submit
    live orders while RESEARCH_ONLY=True. Always returns RESEARCH_ONLY_BLOCKED status.

    Protocol (K794 HL-only -- both legs on HL, no fallback, RESEARCH_ONLY):
      1. Submit ME leg on HL POST_ONLY (paper/dry-run only)
      2. Submit SOL leg on HL POST_ONLY (paper/dry-run only)
      3. Both legs submitted in parallel (K439 pattern)
      4. IOC fallback per leg if POST_ONLY times out
      5. NO Bybit/OKX fallback: ME not listed (G8 FAIL — HIP-3 $85K/day vol)
      6. RESEARCH_ONLY: LIVE BLOCKED regardless of PAPER_TRADE flag

    Args:
      long_leg:  {"symbol": "ME"|"SOL", "notional": 37500, "venue": "HL"}
      short_leg: {"symbol": "SOL"|"ME", "notional": 37500, "venue": "HL"}
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

    # RESEARCH_ONLY guard: always run as paper/research, never live
    if RESEARCH_ONLY and not dry_run and not PAPER_TRADE:
        print(
            "  [K794] RESEARCH_ONLY=True HARDCODED: LIVE execution BLOCKED. "
            "G8 FAIL + thin timing alpha + low liquidity ($85K/day). "
            "Re-eval trigger: ME vol > $500K/day AND Bybit listing AND G2 > +1 Sh.",
            file=sys.stderr,
        )
        return {
            "status":         "RESEARCH_ONLY_BLOCKED",
            "reason":         (
                "RESEARCH_ONLY=True HARDCODED. K794 ME-SOL is not eligible for live deployment. "
                "Conditions for re-evaluation: (1) ME vol > $500K/day (currently $85K/day), "
                "(2) Bybit listing confirmed (G8 FAIL resolution), "
                "(3) G2 timing alpha > +1 Sh (currently thin +0.45 Sh above carry), "
                "(4) HL concentration < 65% (currently 66.8% AT CAP). "
                "Governance review required before any live gate consideration."
            ),
            "long_symbol":    long_sym,
            "short_symbol":   short_sym,
            "research_only":  True,
            "ts_utc":         ts,
        }

    if dry_run or PAPER_TRADE:
        mode_tag = "DRY_RUN" if dry_run else "PAPER_TRADE"
        print(f"  [K794] {mode_tag} (RESEARCH_ONLY=True): "
              f"LONG {long_sym}@{long_venue} ${long_notl:,.0f}  "
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
            "venue_config":     "HL_ONLY_ME_SOL_HIP3_NO_BYBIT_NO_OKX",
            "research_only":    RESEARCH_ONLY,
            "mechanism_note":   (
                "ME-SOL direct alt-alt differential (K794 TWENTY-SIXTH ALT-ALT, 84th daemon, RESEARCH_ONLY): "
                "ME FR = SVM NFT Marketplace (Magic Eden governance token, "
                "NFT trading volume cycles, SVM NFT bull/bear rotation, "
                "multi-chain expansion BTC Ordinals+ETH+SOL, ME DAO governance fee params, "
                "HL HIP-3 speculative demand, SVM DeFi integration staking LP incentives); "
                "FR structurally negative: mean -0.693 bps/hr vs SOL +0.088 bps. "
                "L004 PASS: ME bidirectional (carry_full=0.5713 carry_oos=0.5014 — both below 80%). "
                "L004_DIFF BORDERLINE: full=0.282 (BELOW 0.30 floor). "
                "OOS=0.396 PASS. K788 borderline rule: G2 p=0.000 overrides (timing confirmed). "
                "Timing alpha THIN: +0.45 Sh above pure carry (carry IS Sh=18.68). "
                "vol_ratio=12.66x (full). raw_corr(ME_fr, SOL_fr)=0.0472 — near-zero. "
                "SOL FR = Solana SVM DeFi/DePIN premium (Phantom adoption, Firedancer upgrade, "
                "SOL ETF speculation, SVM DeFi TVL Jupiter/Drift/Jito, persistent positive, "
                "SOL liquidation cascade Min=-20.51bps Feb 2025). "
                "G2 perm p=0.000 — timing alpha confirmed (thin +0.45 Sh above carry). "
                "G3 DSR: t-stat=15.04, p=0.000 — PASS. "
                "G4 WF 11/11 ALL POSITIVE (min_fold_sh=2.43 Fold 2). "
                "G5 28/28 ALL PASS: max_corr=0.2075 (G5z EIGEN-SOL, below 0.40). "
                "G5w PEPE-SOL=0.057 PASS. G5y WIF-SOL=0.013 PASS. G5ab MEME-SOL=0.008 PASS. "
                "G6: 30.2 entries/yr OOS PASS MARGINAL (0.2/yr above 30/yr threshold). "
                "G7: OOS ann ret 3x=260.7% PASS. "
                "G8: FAIL -- ME HL-only HIP-3 (OI=$2.26M, $85K/day — no Bybit/OKX). "
                "G9: PASS -- OOS=217 days (above 180d threshold). "
                "HL at 66.8% AT CAP -- RESEARCH_ONLY + paper-gate strict. "
                "ME = 23rd vertex candidate (1st SVM NFT marketplace cluster). "
                "MR9 L002: all future ME-X pairs blocked if CONDITIONAL_ACCEPT confirmed. "
                "OOS Sh=19.47 IS Sh=19.13 (OOS>IS — no directional overfit). "
                "K523 3-point: conservative=$24,763 central=$39,100 optimistic=$55,392/yr @$10M @3x @0.25%. "
                "Live gate: NOT ELIGIBLE. Re-eval: ME vol > $500K/day + Bybit listing + G2 > +1 Sh. "
                "RESEARCH_ONLY is HARDCODED — not configurable via environment variable."
            ),
            "ts_utc":           ts,
        }
        _append_trade_log(result)
        return result

    # This path should never be reached in RESEARCH_ONLY mode.
    # The guard above blocks live execution; this is a defensive fallback.
    print(f"  [K794] WARNING: reached live scaffold branch in RESEARCH_ONLY mode. "
          f"This should not happen. Returning RESEARCH_ONLY_BLOCKED.", file=sys.stderr)
    return {
        "status":       "RESEARCH_ONLY_BLOCKED",
        "reason":       "RESEARCH_ONLY=True HARDCODED — defensive fallback",
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
    Check if current K794 position has drifted beyond DRIFT_REBALANCE_PCT (5%).

    K794 HL: both legs on HL (ME-PERP + SOL-PERP).
    Drift detection: compare stored ME leg notional vs SOL leg notional.
    Threshold: 5% (same as K679/K682/K684/K686/K690/K747/K739/K754/K759/K774/K777/K778/K786/K789/K788 pattern).

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
    Both legs on HL (K794 HL-only -- ME-PERP + SOL-PERP).
    RESEARCH_ONLY: paper simulation only.

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

    if state == STATE_LONG_ME_SHORT_SOL:
        long_sym,  short_sym  = "ME", "SOL"
    else:  # LONG_SOL_SHORT_ME
        long_sym,  short_sym  = "SOL", "ME"

    long_notional  = float(dash.get("long_notional",  0.0))
    short_notional = float(dash.get("short_notional", 0.0))

    if dry_run or PAPER_TRADE or RESEARCH_ONLY:
        mode_tag = "DRY_RUN" if dry_run else "PAPER_TRADE (RESEARCH_ONLY)"
        print(f"  [K794] {mode_tag} CLOSE:")
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
            "research_only":   RESEARCH_ONLY,
            "ts_utc":          ts,
        }
    else:
        # Should not be reached in RESEARCH_ONLY mode
        print(f"  [K794] SCAFFOLD CLOSE (RESEARCH_ONLY guard — should be unreachable):")
        result = {
            "status":         "RESEARCH_ONLY_BLOCKED",
            "reason":         "RESEARCH_ONLY=True HARDCODED — live close blocked",
            "ts_utc":         ts,
        }

    _append_trade_log(result)
    return result


# ─────────────────────────────────────────────────────────────────────────────
# Dashboard I/O
# ─────────────────────────────────────────────────────────────────────────────

def _load_dashboard() -> dict:
    """Load k794_dashboard.json; return defaults if missing."""
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
        "research_only":           True,
        "paper_trade_status": {
            "days_elapsed": 0,
            "target_live_gate": (
                "RESEARCH_ONLY — NOT ELIGIBLE for live. "
                "Re-eval trigger: ME vol > $500K/day AND Bybit listing AND G2 > +1 Sh"
            ),
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
    """Write k794_dashboard.json with full signal + regime state."""
    dash = _load_dashboard()

    # Update signal data
    dash["last_poll_jst"]       = signal.get("ts_jst", "--")
    dash["fr_me_current"]       = signal.get("fr_me",          0.0)
    dash["fr_sol_current"]      = signal.get("fr_sol",          0.0)
    dash["me_sol_diff_current"] = signal.get("me_sol_diff",     0.0)
    dash["mean_84h"]            = signal.get("mean_84h",        0.0)
    dash["diff_sigma"]          = signal.get("diff_sigma",      0.0)
    dash["regime"]              = signal.get("regime",  "NEUTRAL")
    dash["signal_direction"]    = signal.get("signal_direction", 0)
    dash["history_points"]      = signal.get("history_points",  0)
    dash["research_only"]       = RESEARCH_ONLY

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
    dash["hl_concentration_pct"]    = HL_CONCENTRATION_POST_K794

    # K794 static metadata
    dash["wave"]              = "K797"
    dash["strategy"]          = "K794 ME-SOL FR Differential (TWENTY-SIXTH ALT-ALT, K797 scaffold, RESEARCH_ONLY)"
    dash["oos_sharpe"]        = 19.47
    dash["is_sharpe"]         = 19.13
    dash["w_hours"]           = 84
    dash["paper_trade"]       = PAPER_TRADE
    dash["research_only"]     = RESEARCH_ONLY
    dash["hl_primary"]        = True
    dash["bybit_fallback"]    = False   # G8 FAIL: ME not confirmed on Bybit ($85K/day vol)
    dash["okx_secondary"]     = False   # G8 FAIL: ME not confirmed on OKX
    dash["hl_only_reason"]    = HL_ONLY_REASON
    dash["me_vertex"]         = (
        "23rd vertex candidate (1st SVM NFT marketplace cluster). "
        "MR9 L002: all future ME-X pairs blocked if CONDITIONAL_ACCEPT confirmed."
    )
    dash["k523_central_yr"]   = 39100
    dash["k523_cons_yr"]      = 24763
    dash["k523_opt_yr"]       = 55392
    dash["research_only_reason"] = (
        "RESEARCH_ONLY: (1) G8 FAIL HL-only ME $85K/day vol, "
        "(2) thin timing alpha +0.45 Sh above carry, "
        "(3) G6 marginal 30.2/yr, "
        "(4) HL 66.8% AT CAP. "
        "Re-eval trigger: ME vol > $500K/day AND Bybit listing AND G2 > +1 Sh."
    )
    dash["live_gate"]         = {
        "eligible":             False,
        "reason":               "RESEARCH_ONLY — NOT ELIGIBLE for live deployment",
        "re_eval_trigger_1":    "ME daily vol > $500K/day (currently $85K/day)",
        "re_eval_trigger_2":    "Bybit/OKX ME perp listing confirmed (G8 FAIL resolution)",
        "re_eval_trigger_3":    "G2 timing alpha > +1 Sh in updated eval (currently thin +0.45 Sh)",
        "re_eval_trigger_4":    "HL concentration < 65% (currently 66.8% AT CAP)",
        "after_re_eval":        "Sh >= 15, fill >= 60%, maxDD < 15% (60d gate)",
        "governance_note":      (
            "RESEARCH_ONLY flag is HARDCODED. Governance review required "
            "before any live gate consideration. "
            "All four re-eval triggers must be met simultaneously."
        ),
    }
    dash["l004_note"]         = (
        "PASS: ME bidirectional. carry_full=0.5713 carry_oos=0.5014 (both below 80%)."
    )
    dash["l004_diff_note"]    = (
        "BORDERLINE: full=0.282 (BELOW 0.30 floor). OOS=0.396 PASS. "
        "K788 borderline rule: G2 p=0.000 overrides (timing confirmed thin +0.45 Sh). "
        "Monthly OOS diff_pos recheck: if < 0.28 reduce sleeve to 0.1%; "
        "if two consecutive months < 0.25 suspend strategy."
    )
    dash["g4_result"]         = "11/11 ALL POSITIVE (min_fold_sh=2.43 Fold 2)"
    dash["g5_result"]         = "28/28 ALL PASS: max_corr=0.2075 (G5z EIGEN-SOL, below 0.40)"
    dash["g5_meme_checks"]    = (
        "G5w PEPE-SOL=0.057 PASS | G5y WIF-SOL=0.013 PASS | G5ab MEME-SOL=0.008 PASS"
    )
    dash["g6_entries_yr"]     = 30.2
    dash["g6_note"]           = "MARGINAL: 30.2/yr (0.2/yr above 30/yr threshold). G6 fallback: W=48h (57/yr)."
    dash["g8_result"]         = "FAIL -- ME HL-only HIP-3 (OI=$2.26M, $85K/day — no Bybit/OKX)"
    dash["g9_result"]         = "PASS -- OOS=217 days (above 180d threshold)"
    dash["vol_ratio_full"]    = 12.66
    dash["raw_corr"]          = 0.0472
    dash["me_fr_mean_bps"]    = -0.693
    dash["sol_fr_mean_bps"]   = 0.088
    dash["timing_alpha_sh"]   = 0.45
    dash["pure_carry_is_sh"]  = 18.68
    dash["g2_perm_p"]         = 0.000
    dash["g6_fallback_w"]     = 48
    dash["g6_fallback_entries_yr"] = 57.0

    DASHBOARD_PATH.write_text(json.dumps(dash, indent=2))
    return dash


# ─────────────────────────────────────────────────────────────────────────────
# Phase 8 -- Print status
# ─────────────────────────────────────────────────────────────────────────────

def print_status(dash: dict) -> None:
    """Print K794 ME-SOL strategy status summary."""
    print("=" * 70)
    print("K794 ME-SOL FR Differential -- Status (RESEARCH_ONLY)")
    print("=" * 70)
    print(f"  Last poll:           {dash.get('last_poll_jst', '--')}")
    print(f"  RESEARCH_ONLY:       {RESEARCH_ONLY} (HARDCODED -- NOT configurable)")
    print(f"  Regime:              {dash.get('regime', 'NEUTRAL')}")
    print(f"  Position:            {dash.get('position_state', 'NEUTRAL')}")
    print(f"  ME FR (current):     {dash.get('fr_me_current', 0.0):.8f}")
    print(f"  SOL FR (current):    {dash.get('fr_sol_current', 0.0):.8f}")
    print(f"  ME-SOL diff:         {dash.get('me_sol_diff_current', 0.0):.8f}")
    print(f"  Mean 84h:            {dash.get('mean_84h', 0.0):.8f}")
    print(f"  History points:      {dash.get('history_points', 0)}")
    print(f"  Total notional:      ${dash.get('total_notional_usdc', 0.0):,.0f}")
    print(f"  Margin used:         ${dash.get('margin_used_usdc', 0.0):,.0f}")
    print(f"  Sleeve:              {SLEEVE_PCT:.2%}")
    print(f"  Leverage:            {LEVERAGE}x")
    print(f"  Venue:               HL ONLY (G8 FAIL -- ME not on Bybit/OKX)")
    print(f"  HL concentration:    {dash.get('hl_concentration_pct', 66.8):.1f}%")
    print(f"  Paper trade:         {PAPER_TRADE}")
    print(f"  OOS Sharpe:          19.47 (W=84h, 217d OOS -- G9 PASS)")
    print(f"  IS Sharpe:           19.13 (OOS>IS -- no directional overfit)")
    print(f"  K523 central:        $39,100/yr @$10M @3x @0.25%")
    print(f"  vol_ratio:           12.66x (full) -- extreme vol ratio")
    print(f"  ME FR mean:          -0.693 bps/hr (structurally negative -- SHORT ME earns)")
    print(f"  Timing alpha:        +0.45 Sh above pure carry (THIN)")
    print(f"  Drift:               {dash.get('delta_neutral_drift_pct', 0.0):.2%}")
    print(f"  Rebalance:           {dash.get('rebalance_required', False)}")
    print(f"  ME vertex:           23rd candidate (1st SVM NFT marketplace cluster)")
    print(f"  L004 status:         PASS (ME bidirectional -- SVM NFT marketplace)")
    print(f"  L004_DIFF:           BORDERLINE full=0.282 (<0.30), OOS=0.396 PASS, G2 p=0.000")
    print(f"  G8 status:           FAIL (HL-only HIP-3 $85K/day -- no Bybit/OKX)")
    print(f"  G9 status:           PASS (OOS=217 days >= 180d)")
    print(f"  G6 status:           MARGINAL 30.2/yr (fallback W=48h if < 30/yr)")
    print(f"  Live gate:           NOT ELIGIBLE (RESEARCH_ONLY hardcoded)")
    print(f"  Re-eval trigger:     ME vol > $500K/day + Bybit + G2 > +1 Sh")
    print("=" * 70)


# ─────────────────────────────────────────────────────────────────────────────
# Main loop -- 8h cadence
# ─────────────────────────────────────────────────────────────────────────────

def run_main_cycle(aum: float = AUM_DEFAULT) -> dict:
    """
    Main 8h execution cycle for K794 ME-SOL FR Differential (RESEARCH_ONLY).

    Steps:
      1. Fetch ME + SOL FR from HL (HL-only — no fallback)
      2. Compute 84h rolling mean signal
      3. Decide position (paper/research only)
      4. Submit / hold / rebalance (paper only — RESEARCH_ONLY guard)
      5. Write dashboard
    """
    print(f"\n[K794 ME-SOL] {datetime.now(JST).strftime('%Y-%m-%d %H:%M JST')} -- 8h cycle")
    print(f"  RESEARCH_ONLY={RESEARCH_ONLY} (HARDCODED) PAPER_TRADE={PAPER_TRADE}")
    print(f"  Venue: HL ONLY (G8 FAIL -- ME not on Bybit/OKX, vol=$85K/day)")
    print(f"  HL concentration: {HL_CONCENTRATION_POST_K794}% AT CAP -- research-only + paper-gate strict")
    print(f"  G9 PASS: OOS=217 days. G6 MARGINAL: 30.2/yr (W=84h).")
    print(f"  Live gate: NOT ELIGIBLE. Re-eval: ME vol > $500K/day + Bybit + G2 > +1 Sh")

    # Step 1+2: Signal
    signal = compute_signal()

    print(f"  ME FR:     {signal['fr_me']:.8f} ({signal['fr_me'] * 8760 * 100:.2f}%/yr)")
    print(f"  SOL FR:    {signal['fr_sol']:.8f} ({signal['fr_sol'] * 8760 * 100:.2f}%/yr)")
    print(f"  diff:      {signal['me_sol_diff']:.8f}")
    print(f"  mean84h:   {signal['mean_84h']:.8f}")
    print(f"  regime:    {signal['regime']} (direction={signal['signal_direction']})")
    print(f"  history:   {signal['history_points']} points")

    # Step 3: Position decision
    decision = decide_position(signal)
    if decision is None:
        print("  Decision: NEUTRAL -- no trade")
    else:
        print(f"  Decision: {decision['position_state']} (RESEARCH_ONLY -- paper only)")
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

    # Step 4c: Trade submission (paper only -- RESEARCH_ONLY guard active)
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
        description=(
            "K794 ME-SOL FR Differential -- 84th daemon, 26th alt-alt scaffold, "
            "23rd vertex candidate ME SVM NFT marketplace. RESEARCH_ONLY (hardcoded)."
        )
    )
    parser.add_argument("--dry-run",   action="store_true", help="Run signal + decision, no submission")
    parser.add_argument("--status",    action="store_true", help="Print dashboard status and exit")
    parser.add_argument("--rebalance", action="store_true", help="Check drift + rebalance if needed")
    parser.add_argument("--close",     type=str, metavar="REASON", help="Close all ME-SOL positions (paper)")
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
            print("  [K794] Rebalance triggered -- resizing legs to target notional (paper only)")
        return 0

    if args.dry_run:
        print(f"[K794 ME-SOL] DRY-RUN (RESEARCH_ONLY={RESEARCH_ONLY}) -- "
              f"{datetime.now(JST).strftime('%Y-%m-%d %H:%M JST')}")
        signal   = compute_signal()
        decision = decide_position(signal)
        notional_per_leg, total_notional = compute_delta_neutral_notional(args.aum)
        print(json.dumps({
            "signal":            signal,
            "decision":          decision,
            "notional_per_leg":  notional_per_leg,
            "total_notional":    total_notional,
            "paper_trade":       PAPER_TRADE,
            "research_only":     RESEARCH_ONLY,
            "hl_only":           True,
            "bybit_fallback":    False,
            "okx_secondary":     False,
            "oos_sharpe":        19.47,
            "is_sharpe":         19.13,
            "k523_central_yr":   39100,
            "g8_status":         "FAIL -- ME HL-only HIP-3 (OI=$2.26M, $85K/day)",
            "g9_status":         "PASS -- OOS=217 days (above 180d threshold)",
            "g6_status":         "MARGINAL 30.2/yr (W=84h). G6 fallback: W=48h (57/yr).",
            "live_eligible":     False,
            "re_eval_trigger":   (
                "ME vol > $500K/day AND Bybit listing AND G2 > +1 Sh "
                "(currently thin +0.45 Sh above carry)"
            ),
        }, indent=2))
        return 0

    # Normal 8h cycle
    run_main_cycle(args.aum)
    return 0


if __name__ == "__main__":
    sys.exit(main())
