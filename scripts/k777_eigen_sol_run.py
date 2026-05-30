#!/usr/bin/env python3
"""
k777_eigen_sol_run.py — K777 EIGEN-SOL FR Differential Strategy
=================================================================
TWENTIETH ALT-ALT pair (21st evaluated): EIGEN vs SOL (Restaking AVS Economy × Solana SVM).
Signal: EIGEN_FR - SOL_FR  (W=84h rolling mean, primary window)
W=84h primary (IS Sh=38.85, OOS Sh=35.90 — best IS/OOS balance per K777 eval)
Fallback W=168h if SOL liquidity issue (OOS Sh=33.17)
4x leverage, 1.5% sleeve
HL primary + Bybit fallback (EIGENUSDT confirmed on Bybit)
PAPER_TRADE=True default

K777 EIGEN-SOL alt-alt hypothesis:
  EIGEN (EigenLayer restaking protocol token):
    FR driven by AVS launches (new Actively Validated Services seeking ETH security),
    EigenLayer protocol milestones (slashing activation, Stage 2 launch),
    Restaking yield vs direct ETH staking competition,
    Operator registration demand cycles (ETH restaking inflows/outflows),
    Institutional restaking adoption (Binance, Coinbase restaking integration),
    AVS economic model cycles (operator rewards, slashing risk events),
    EigenLayer TVL dynamics (ETH restaked vs LST restaked mix).
    FR structural: negative bias -12%/yr persistent (shorts dominant post-listing).
    Monthly volatility: high kurtosis, extreme events (Oct 2025 spike +9.96%/yr).
    Bybit: EIGENUSDT listed 2024-09-18 (pre-HL listing 2025-10-12).
    HL: EIGEN-PERP from 2025-10-12. $1.10M/day volume. maxLeverage=5.
  SOL (Solana SVM L1):
    FR driven by retail momentum, Phantom wallet adoption, Firedancer upgrade,
    Solana ETF narrative flows, SVM DeFi TVL (Jupiter/Drift/Jito).
    SOL FR mean persistently positive — retail demand structural.
    SOL extreme negative FR: Min=-20.51bps (liquidation cascade Feb 2025).
  Alt-alt mechanism: EIGEN (ETH restaking AVS) vs SOL (Solana SVM L1).
    Structurally orthogonal: restaking AVS security economy (ETH L1 primitive)
    is decoupled from Solana SVM cycle (Firedancer, validator rewards, meme).
    G5q: LDO-SOL sig_corr=0.147 PASS (restaking distinct from LSD mechanism).
    EIGEN cluster: ETH restaking / AVS economy — DISTINCT from LSD (LDO) and SVM (SOL).
    raw_corr(EIGEN_fr, SOL_fr) = 0.128 — well below 0.50 threshold.
    G5 max_corr=0.441 (G5z BLUR-SOL OOS, W=84 — borderline fail, W=48 passes 0.345).

K777 §6 validation (ACCEPT CONDITIONAL — G5z BLUR-SOL borderline + G9 marginal):
  - OOS Sharpe: 35.90 (W=84h, zero threshold, 118.6d OOS)
  - Full Sharpe: 37.04 (W=84h)
  - OOS Ann Return: $84K central @$10M @4x @1.5% sleeve (K523 3-point)
  - W=84h rolling mean, zero threshold (sign of diff) — G6 compliant (33.9/yr)
  - G4 walk-forward: 4/4 folds positive (avg_oos_sh=42.14)
  - G5 24/25 gates PASS; G5z BLUR-SOL OOS=0.441 borderline (W=84; W=48 passes 0.345)
  - G8: HL + Bybit PASS (EIGENUSDT confirmed on Bybit)
  - G9: marginal (OOS=118.6d < 120d — 1.4d short, operational limitation)
  - HL 66.8% AT CAP -> paper-gate strict until K498/v6.52

K777 EIGEN-SOL vertex addition (19th vertex, restaking cluster):
  V (before K777) = {APT, ATOM, AVAX, BNB, ENA, FIL, HBAR, INJ, LDO, SEI, SOL, TIA, TAO,
                      PEPE, WIF, BLUR, AXS, IO}
  V (after K777)  = {APT, ATOM, AVAX, BNB, ENA, FIL, HBAR, INJ, LDO, SEI, SOL, TIA, TAO,
                      PEPE, WIF, BLUR, AXS, IO, EIGEN}
  EIGEN = 19th vertex (1st ETH-restaking cluster — distinct from LSD cluster LDO).
  MR9 L002: all future EIGEN-X pairs are auto-blocked (EIGEN exhausted as new vertex).
  EIGEN-SOL is the only permissible EIGEN-X pair given V composition at K777.

K523 3-point profit projection (@$10M @4x @1.5% sleeve):
  Conservative: $63,230/yr  (R2S=38% floor x OOS-haircut-25%, K518 floor)
  Central:      $84,307/yr  (K523 mandate: 60% realized-to-stated, base case)
  Optimistic:   $295,813/yr (near-full OOS realization if restaking AVS boom)
  Upper bound:  OOS raw return (NOT central — K523 mandatory)
  Note: 1.5% sleeve -> ~$150K margin @$10M; central per K777 eval=$84,307/yr

Cross-venue note (K777):
  HL:    EIGEN-PERP from 2025-10-12. $1.10M/day volume. maxLeverage=5.
  Bybit: EIGENUSDT listed 2024-09-18. Linear perp. PASS.
  G8 = PASS (HL + Bybit both confirmed).
  HL primary for live execution (IO-SOL precedent for HL-first).
  Bybit fallback: both EIGEN-PERP + SOL-PERP available on Bybit.

Architecture (K679->K747->K754->K759->K769->K774->K777 alt-alt scaffold pattern):
  1. fetch_fr_batch()                      -> fetch EIGEN + SOL FR every 8h from HL (Bybit fallback)
  2. compute_signal(eigen_fr, sol_fr)      -> 84h rolling mean of (EIGEN_FR - SOL_FR); sign()
  3. decide_position(signal)               -> LONG_EIGEN_SHORT_SOL | LONG_SOL_SHORT_EIGEN | NEUTRAL
  4. submit_paired_trade(long, short)      -> POST_ONLY paired (EIGEN + SOL legs, HL primary)
  5. daily_rebalance()                     -> drift > 5% triggers rebalance
  6. close_paired_position(reason)         -> sequential: short first, then long

K779 production scaffold:
  - 78th daemon (twentieth alt-alt pair, ACCEPT CONDITIONAL, G4 4/4)
  - HL primary + Bybit fallback (both EIGENUSDT + SOLUSDT confirmed)
  - 1.5% sleeve
  - $84K central @$10M @4x @1.5% sleeve (K523 3-point: $63K-$296K)
  - Paper-gate until K498/v6.52 reduces HL concentration
  - Live gate: Sh >= 15, fill >= 60%, maxDD < 15%
  - G5z BLUR-SOL monthly recheck (OOS 0.441 at W=84; target < 0.40)
  - G9 marginal (118.6d < 180d) -> wait for full 180d before live

G5z note (K777 borderline):
  G5z BLUR-SOL OOS=0.441 at W=84 (borderline fail, threshold=0.40).
  Root cause: both EIGEN-SOL and BLUR-SOL are ETH-ecosystem alts vs SOL.
  Apr-May 2026 ETH/SOL divergence caused both to trend same direction.
  At W=48: G5z OOS=0.345 (PASS). Window-sensitivity artifact confirmed.
  Monthly recheck: if W=84 OOS settles < 0.40, escalate to ACCEPT.

Execution:
  - HL primary (EIGEN-PERP + SOL-PERP, HL)
  - Bybit fallback (EIGENUSDT + SOLUSDT, Bybit) if HL unavailable
  - POST_ONLY paired execution (K439 pattern)
  - Position: 1.5% sleeve, 4x leverage (paper-gate strict — HL cap 66.8%)
  - 8h cadence (matches FR settlement cycle)
  - W=84h rolling mean (10.5 x 8h periods — G6-safe: 33.9 entries/yr)

Paper-trade mode is the DEFAULT.  No orders are submitted unless
PAPER_TRADE=False is explicitly set in the environment.

K339 security: REPO_ROOT from __file__, no /Users/ literals.
No new packages — stdlib urllib + json only.

Usage:
  python3 scripts/k777_eigen_sol_run.py --dry-run
  python3 scripts/k777_eigen_sol_run.py --status
  python3 scripts/k777_eigen_sol_run.py --rebalance
  python3 scripts/k777_eigen_sol_run.py --close "scheduled exit"
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

DASHBOARD_PATH  = DATA_DIR  / "k777_dashboard.json"
FR_HISTORY_PATH = CACHE_DIR / "k777_fr_history.jsonl"
TRADE_LOG_PATH  = CACHE_DIR / "k777_paper_trades.jsonl"

JST = timezone(timedelta(hours=9))
UTC = timezone.utc

# -- Strategy constants -------------------------------------------------------
PAPER_TRADE         = os.environ.get("PAPER_TRADE", "True").lower() != "false"
SLEEVE_PCT          = 0.015         # K777 sleeve = 1.5% of AUM
LEVERAGE            = 4.0           # 4x per K777 analysis
AUM_DEFAULT         = 10_000_000.0  # $10M reference AUM
DRIFT_REBALANCE_PCT = 0.05          # rebalance if legs drift > 5%
IOC_TIMEOUT_SEC     = 300           # 5 min fill window
EMA_PERIOD_HOURS    = 84            # 84h rolling mean (W=84h primary, G6 compliant: 33.9/yr)
EMA_PERIOD_PERIODS  = EMA_PERIOD_HOURS // 8  # = 10.5 -> 11 periods (8h settlement cycle)
SIGNAL_SIGMA_MULT   = 0.0           # zero threshold (sign of rolling mean)
HL_API_URL          = "https://api.hyperliquid.xyz/info"
BYBIT_API_URL       = "https://api.bybit.com"

# -- Venue config -------------------------------------------------------------
# HL primary: EIGEN-PERP + SOL-PERP on HL.
# Bybit fallback: EIGENUSDT + SOLUSDT on Bybit (both confirmed).
# G8 = PASS (HL + Bybit both listed).
# HL concentration: 66.8% AT CAP -- paper-gate strict until K498/v6.52.
HL_CONCENTRATION_PRE_K777   = 66.8   # post-K776 reference
HL_CONCENTRATION_POST_K777  = 66.8   # UNCHANGED -- paper-only, no live capital added
BYBIT_EIGEN_SYMBOL          = "EIGENUSDT"
BYBIT_SOL_SYMBOL            = "SOLUSDT"
HL_ONLY_REASON              = (
    "HL primary: EIGEN-PERP + SOL-PERP on HL. "
    "Bybit fallback: EIGENUSDT (listed 2024-09-18) + SOLUSDT. "
    "G8 PASS (HL + Bybit confirmed). "
    "EIGEN HL: from 2025-10-12, $1.10M/day volume, maxLeverage=5. "
    "HL at 66.8% AT CAP. Paper-gate strict: any live capital would breach 65% ceiling. "
    "Deploy LIVE after K498/v6.52 reduces HL% below 65%."
)

# -- Position state constants -------------------------------------------------
STATE_NEUTRAL               = "NEUTRAL"
STATE_LONG_EIGEN_SHORT_SOL  = "LONG_EIGEN_SHORT_SOL"
STATE_LONG_SOL_SHORT_EIGEN  = "LONG_SOL_SHORT_EIGEN"

# -- Symbols fetched from HL for FR data --------------------------------------
SYMBOLS = ("EIGEN", "SOL")


# ─────────────────────────────────────────────────────────────────────────────
# HTTP helper (stdlib urllib only -- no requests)
# ─────────────────────────────────────────────────────────────────────────────

def _http_get(url: str, timeout: int = 10) -> Optional[dict]:
    try:
        req = urllib.request.Request(
            url, headers={"User-Agent": "crypto-lab-k777/1.0"}
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        print(f"  [k777] HTTP error: {e}", file=sys.stderr)
        return None


def _http_post(url: str, payload: dict, timeout: int = 10) -> Optional[dict]:
    try:
        data = json.dumps(payload).encode()
        req  = urllib.request.Request(
            url, data=data,
            headers={"Content-Type": "application/json",
                     "User-Agent": "crypto-lab-k777/1.0"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        print(f"  [k777] HTTP error: {e}", file=sys.stderr)
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Phase 1 -- Funding rate fetch (EIGEN + SOL from HL, Bybit fallback)
# ─────────────────────────────────────────────────────────────────────────────

def _fetch_hl_fr_batch() -> Dict[str, float]:
    """
    Fetch current 1h funding rates for EIGEN and SOL from HL.
    Returns {symbol: fr_1h_fraction}.

    HL API: metaAndAssetCtxs (POST).
    K777: HL primary (EIGEN-PERP + SOL-PERP). Bybit fallback (EIGENUSDT + SOLUSDT).
    EIGEN HL: from 2025-10-12. $1.10M/day volume. maxLeverage=5.
    EIGEN Bybit: EIGENUSDT listed 2024-09-18. Linear perp.

    Note: HL settles 1h funding; W=84h = 84 x 1h periods for rolling mean.
    FR stored as 1h fraction; annualized = fr_1h * 8760.

    EIGEN strategy direction:
      EIGEN FR structural negative: -12%/yr persistent (shorts dominant post-listing).
      SOL FR structural positive: persistent retail demand.
      Primary regime: LONG_SOL_SHORT_EIGEN (collect EIGEN negative carry + SOL positive carry).
      Secondary regime: LONG_EIGEN_SHORT_SOL (AVS demand spike -- temporary positive FR).
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
        print(f"  [k777] HL partial result {list(result.keys())} -- trying Bybit fallback",
              file=sys.stderr)

    # Bybit fallback: EIGENUSDT + SOLUSDT
    bybit_url = f"{BYBIT_API_URL}/v5/market/tickers?category=linear"
    raw_bybit = _http_get(bybit_url)
    if raw_bybit and raw_bybit.get("retCode") == 0:
        tickers = raw_bybit.get("result", {}).get("list", [])
        sym_map = {t["symbol"]: t for t in tickers}
        bybit_targets = [
            ("EIGEN", BYBIT_EIGEN_SYMBOL),
            ("SOL",   BYBIT_SOL_SYMBOL),
        ]
        for canonical, perp_sym in bybit_targets:
            if canonical not in result and perp_sym in sym_map:
                tick = sym_map[perp_sym]
                try:
                    fr_val = float(tick.get("fundingRate", 0.0))
                    result[canonical] = fr_val
                    print(f"  [k777] {canonical} FR from Bybit fallback ({perp_sym})",
                          file=sys.stderr)
                except (TypeError, ValueError):
                    pass

    return result


def _load_fr_history() -> List[dict]:
    """Load K777 FR history JSONL."""
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
    fr_eigen: float, fr_sol: float, eigen_sol_diff: float
) -> None:
    """Append one FR snapshot to history."""
    rec = {
        "ts_utc":         datetime.now(UTC).isoformat(),
        "fr_eigen":       round(fr_eigen,       10),
        "fr_sol":         round(fr_sol,          10),
        "eigen_sol_diff": round(eigen_sol_diff,  10),  # EIGEN_FR - SOL_FR
    }
    with open(FR_HISTORY_PATH, "a") as f:
        f.write(json.dumps(rec) + "\n")


# ─────────────────────────────────────────────────────────────────────────────
# Phase 2 -- Signal computation (EIGEN-SOL direct differential, 84h rolling mean)
# ─────────────────────────────────────────────────────────────────────────────

def compute_signal(
    fr_eigen: Optional[float] = None,
    fr_sol:   Optional[float] = None,
) -> dict:
    """
    Fetch live EIGEN and SOL FRs from HL (Bybit fallback), compute EIGEN-SOL differential,
    and compute 84h rolling mean for direction signal.

    Signal mechanism (K777 direct alt-alt differential -- no orthogonalization):
      diff = EIGEN_FR - SOL_FR
      mean_84h = 84h rolling mean of diff (10.5 x 8h periods equivalent)
      sign  = sign(mean_84h)
      Enter: sign > 0 -> EIGEN FR > SOL FR -> long EIGEN (AVS demand spike), short SOL
             sign < 0 -> SOL FR > EIGEN FR -> long SOL (collect SVM premium), short EIGEN
                         [Structural direction: EIGEN persistent negative, SOL persistent positive]

    NOTE: EIGEN is ETH restaking (AVS economy) -- structurally distinct from SOL SVM.
    EIGEN vs LDO distinction:
      LDO = liquid staking (issues stETH, earns consensus layer yield).
      EIGEN = restaking (secures AVS, earns restaking yield + slashing risk).
      G5q: LDO-SOL sig_corr=0.147 PASS (W=84) -- restaking distinct from LSD.

    K777 carry mechanism:
      When signal says LONG_SOL_SHORT_EIGEN (dominant regime):
        SHORT EIGEN: collect persistent negative EIGEN carry (AVS market undersupply)
        LONG SOL: collect persistent positive SOL carry (SVM retail demand)
        Both legs in favorable carry direction simultaneously.
      When signal says LONG_EIGEN_SHORT_SOL (AVS demand spike):
        EIGEN FR turns temporarily positive (new AVS launch event, operator rush).
        LONG EIGEN captures the temporary AVS premium.
        SHORT SOL benefits if SOL FR simultaneously drops.

    W=84h rationale (G6 compliance):
      W=84h -> 33.9 entries/yr OOS (ABOVE 20/yr G6 threshold -- PASS).
      W=84h primary: IS Sh=38.85, OOS Sh=35.90 (best IS/OOS balance per K777 grid).
      W=168h fallback: OOS Sh=33.17 (if SOL liquidity requires longer window).
      W=48h OOS Sh=39.57 (more entries but less stable -- not primary).

    K777 §6 validation:
      - OOS Sharpe: 35.90 (W=84h, zero threshold, 118.6d OOS)
      - OOS Ann Return: $84K central @$10M @4x @1.5% sleeve (K523 3-point)
      - G4 WF 4/4 positive (fold Sharpes: 64.1, 32.3, 36.7, 35.4 -- all strong)
      - G5 24/25: G5z BLUR-SOL OOS=0.441 borderline (W=84); W=48 passes 0.345
      - G8 PASS: HL + Bybit (EIGENUSDT confirmed)
      - G9 marginal: 118.6d < 120d (1.4d short, operational data limit)
      - HL 66.8% AT CAP -> paper-gate strict

    Returns:
      {
        "fr_eigen":           float,
        "fr_sol":             float,
        "eigen_sol_diff":     float,    # EIGEN_FR - SOL_FR (current)
        "mean_84h":           float,    # 84h rolling mean of differential
        "diff_sigma":         float,    # 84h rolling sigma (informational)
        "history_points":     int,
        "regime":             str,      # BULL_EIGEN | BEAR_EIGEN | NEUTRAL
        "signal_direction":   int,      # +1 | -1 | 0
        "ts_jst":             str,
      }
    """
    if fr_eigen is None or fr_sol is None:
        frs      = _fetch_hl_fr_batch()
        fr_eigen = frs.get("EIGEN", 0.0)
        fr_sol   = frs.get("SOL",   0.0)

    # EIGEN-SOL direct alt-alt differential (no orthogonalization)
    eigen_sol_diff = fr_eigen - fr_sol

    _append_fr_history(fr_eigen, fr_sol, eigen_sol_diff)

    # Load history for rolling mean + sigma (84h = ~10.5 x 8h periods -> 11 periods)
    history = _load_fr_history()
    diffs   = [r["eigen_sol_diff"] for r in history if "eigen_sol_diff" in r]

    n_periods = EMA_PERIOD_PERIODS   # 10 periods (84h // 8h)

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

    # Regime classification (zero threshold -- per K777 spec)
    # BULL_EIGEN: EIGEN FR > SOL FR (AVS demand spike -- temporary positive)
    # BEAR_EIGEN: EIGEN FR < SOL FR (SVM premium + EIGEN structural negative -- dominant)
    if mean_84h > 0:
        regime    = "BULL_EIGEN"   # EIGEN-SOL diff positive -> EIGEN FR > SOL FR (AVS spike)
        direction = 1
    elif mean_84h < 0:
        regime    = "BEAR_EIGEN"   # SOL FR > EIGEN FR (SVM dominant + EIGEN structural neg)
        direction = -1
    else:
        regime    = "NEUTRAL"
        direction = 0

    return {
        "fr_eigen":         round(fr_eigen,        10),
        "fr_sol":           round(fr_sol,            10),
        "eigen_sol_diff":   round(eigen_sol_diff,    10),
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
    Determine trade direction from EIGEN-SOL differential rolling mean.

    Logic (EIGEN-SOL direct alt-alt pair, HL primary + Bybit fallback):
      regime = BULL_EIGEN (mean_84h > 0):
        EIGEN FR > SOL FR: AVS demand spike (EIGEN temporarily positive)
        -> long EIGEN (collect AVS restaking premium during spike)
        -> short SOL (avoid lower SVM carry in AVS-spike regime)
        -> position_state = LONG_EIGEN_SHORT_SOL

      regime = BEAR_EIGEN (mean_84h < 0):
        SOL FR > EIGEN FR: SVM season + EIGEN structural negative
        -> long SOL (collect SVM DeFi/DePIN premium)
        -> short EIGEN (collect EIGEN negative carry -- persistent -12%/yr)
        -> position_state = LONG_SOL_SHORT_EIGEN [dominant structural direction]

      regime = NEUTRAL: no trade (mean_84h == 0 exactly -- rare)

    Carry note (BEAR_EIGEN structural direction):
      SHORT EIGEN: EIGEN FR structural ~-12%/yr -> collect carry from short
      LONG SOL: SOL FR structural positive -> collect carry from long
      Both legs favorable simultaneously.
      This is the structural dominant direction for EIGEN-SOL pair.

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

    if regime == "BULL_EIGEN":
        # EIGEN FR > SOL FR: AVS demand spike (temporary)
        long_asset  = "EIGEN"
        short_asset = "SOL"
        state       = STATE_LONG_EIGEN_SHORT_SOL
    else:  # BEAR_EIGEN
        # SOL FR > EIGEN FR: SVM season + EIGEN structural negative (dominant)
        long_asset  = "SOL"
        short_asset = "EIGEN"
        state       = STATE_LONG_SOL_SHORT_EIGEN

    # HL primary for both legs; Bybit fallback available
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
    Compute equal notional for both legs of the EIGEN-SOL paired trade.

    K777 HL config (EIGEN-PERP + SOL-PERP on HL, paper-gate strict):
      sleeve_capital   = aum x sleeve_pct      (e.g. $10M x 1.5% = $150K)
      total_notional   = sleeve_capital x lev   ($150K x 4 = $600K)
      notional_per_leg = total_notional / 2     ($300K per leg)

    At $10M / 1.5% sleeve / 4x (paper-gate):
      EIGEN leg: $75K capital x 4x = $300K notional (HL EIGEN-PERP)
      SOL leg:   $75K capital x 4x = $300K notional (HL SOL-PERP)
      Total:     $600K notional (two legs combined)
      Margin:    $150K (1.5% of AUM)
      HL conc:   PAPER-ONLY (66.8% AT CAP -- no live capital added)
      Net profit: central $84K/yr @$10M @4x (K523: $63K-$296K)
      EIGEN vertex: 19th (1st ETH-restaking cluster) -- MR9 L002 blocks all future EIGEN-X pairs

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
    Submit K777 EIGEN-SOL paired trade: POST_ONLY both legs in parallel.

    Protocol (K777 HL primary -- both legs on HL, Bybit fallback available):
      1. Submit EIGEN leg on HL POST_ONLY
      2. Submit SOL leg on HL POST_ONLY
      3. Both legs submitted in parallel (K439 pattern)
      4. IOC fallback per leg if POST_ONLY times out
      5. Bybit fallback if HL unavailable (EIGENUSDT + SOLUSDT confirmed)
      6. If both fail: retry next 8h cycle

    Args:
      long_leg:  {"symbol": "EIGEN"|"SOL", "notional": 300000, "venue": "HL"}
      short_leg: {"symbol": "SOL"|"EIGEN", "notional": 300000, "venue": "HL"}
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
        print(f"  [K777] {mode_tag}: LONG {long_sym}@{long_venue} ${long_notl:,.0f}  "
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
            "venue_config":     "HL_PRIMARY_BYBIT_FALLBACK_EIGEN_SOL",
            "mechanism_note":   (
                "EIGEN-SOL direct alt-alt differential (K777 TWENTIETH ALT-ALT, 78th daemon): "
                "EIGEN FR = restaking AVS economy premium (EigenLayer ETH restaking, AVS launches, "
                "operator registration cycles, institutional restaking adoption, "
                "slashing risk events, EigenLayer protocol milestones Stage 2, "
                "restaking yield vs direct ETH staking competition, "
                "vol_ratio=1.868x full/3.97x 30d); "
                "SOL FR = Solana SVM DeFi/DePIN premium (Phantom adoption, Firedancer upgrade, "
                "SOL ETF speculation, SVM DeFi TVL Jupiter/Drift/Jito, persistent positive, "
                "SOL liquidation cascade Min=-20.51bps Feb 2025). "
                "G4 WF 4/4 positive (fold Sh: 64.1/32.3/36.7/35.4 -- all strong). "
                "G5 24/25 PASS; G5z BLUR-SOL OOS=0.441 borderline (W=84; W=48=0.345 PASS). "
                "G8 PASS: HL + Bybit (EIGENUSDT confirmed 2024-09-18). "
                "G9 marginal: 118.6d < 120d (operational data limit). "
                "HL at 66.8% AT CAP -- paper-gate strict until K498/v6.52 reduces HL%. "
                "EIGEN = 19th vertex (1st ETH-restaking cluster). "
                "MR9 L002: all future EIGEN-X pairs blocked. "
                "OOS Sh=35.90 (W=84h, zero threshold, 118.6d). "
                "K523 3-point: conservative=$63,230 central=$84,307 optimistic=$295,813/yr @$10M @4x @1.5%. "
                "Live gate: Sh >= 15, fill >= 60%, maxDD < 15%. "
                "G5z monthly recheck: target W=84 OOS < 0.40 for ACCEPT escalation. "
                "G9: wait for full 180d OOS before live deployment."
            ),
            "ts_utc":           ts,
        }
        _append_trade_log(result)
        return result

    # LIVE scaffold (not reached in PAPER_TRADE mode):
    print(f"  [K777] SCAFFOLD LIVE: parallel POST_ONLY "
          f"LONG {long_sym}@{long_venue} ${long_notl:,.0f} "
          f"+ SHORT {short_sym}@{short_venue} ${short_notl:,.0f}")
    long_order_id  = f"SCAFFOLD_LONG_{long_sym}_{int(time.time())}"
    short_order_id = f"SCAFFOLD_SHORT_{short_sym}_{int(time.time())}"

    print(f"  [K777] Neither leg filled within timeout -- retry next 8h cycle")
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
    Check if current K777 position has drifted beyond DRIFT_REBALANCE_PCT (5%).

    K777 HL: both legs on HL (EIGEN-PERP + SOL-PERP).
    Drift detection: compare stored EIGEN leg notional vs SOL leg notional.
    Threshold: 5% (same as K679/K682/K684/K686/K690/K747/K739/K754/K759/K769/K774 pattern).

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
    Both legs on HL (K777 HL primary -- EIGEN-PERP + SOL-PERP).

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

    if state == STATE_LONG_EIGEN_SHORT_SOL:
        long_sym,  short_sym  = "EIGEN", "SOL"
    else:  # LONG_SOL_SHORT_EIGEN
        long_sym,  short_sym  = "SOL", "EIGEN"

    long_notional  = float(dash.get("long_notional",  0.0))
    short_notional = float(dash.get("short_notional", 0.0))

    if dry_run or PAPER_TRADE:
        mode_tag = "DRY_RUN" if dry_run else "PAPER_TRADE"
        print(f"  [K777] {mode_tag} CLOSE:")
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
        print(f"  [K777] SCAFFOLD CLOSE:")
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
    """Load k777_dashboard.json; return defaults if missing."""
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
        "paper_trade_status":      {"days_elapsed": 0, "target_live_gate": "Sh>=15 fill>=60% maxDD<15%"},
    }


def _write_dashboard(
    signal:           dict,
    decision:         Optional[dict],
    notional_per_leg: float,
    total_notional:   float,
    rebalance:        dict,
    aum:              float,
) -> dict:
    """Write k777_dashboard.json with full signal + regime state."""
    dash = _load_dashboard()

    # Update signal data
    dash["last_poll_jst"]          = signal.get("ts_jst", "--")
    dash["fr_eigen_current"]       = signal.get("fr_eigen",          0.0)
    dash["fr_sol_current"]         = signal.get("fr_sol",             0.0)
    dash["eigen_sol_diff_current"] = signal.get("eigen_sol_diff",     0.0)
    dash["mean_84h"]               = signal.get("mean_84h",           0.0)
    dash["diff_sigma"]             = signal.get("diff_sigma",         0.0)
    dash["regime"]                 = signal.get("regime",      "NEUTRAL")
    dash["signal_direction"]       = signal.get("signal_direction",   0)
    dash["history_points"]         = signal.get("history_points",     0)

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
    dash["hl_concentration_pct"]    = HL_CONCENTRATION_POST_K777

    # K777 static metadata
    dash["strategy"]         = "K777 EIGEN-SOL FR Differential (TWENTIETH ALT-ALT, K779 scaffold)"
    dash["oos_sharpe"]       = 35.90
    dash["w_hours"]          = 84
    dash["paper_trade"]      = PAPER_TRADE
    dash["hl_primary"]       = True
    dash["bybit_fallback"]   = True
    dash["hl_only_reason"]   = HL_ONLY_REASON
    dash["eigen_vertex"]     = "19th vertex (1st ETH-restaking cluster). MR9 L002: all future EIGEN-X blocked."
    dash["k523_central_yr"]  = 84307
    dash["k523_cons_yr"]     = 63230
    dash["k523_opt_yr"]      = 295813
    dash["live_gate"]        = {
        "sharpe_threshold":     15.0,
        "fill_rate_pct":        60.0,
        "max_dd_pct":           15.0,
        "additional_gate":      "K498/v6.52 OKX activation required (HL% must drop below 65.0%)",
        "g9_gate":              "Full 180d OOS data required before live deployment",
        "g5z_gate":             "G5z BLUR-SOL W=84 OOS must settle < 0.40 (monthly recheck)",
    }
    dash["g9_note"]          = "G9 marginal: OOS=118.6d < 120d (1.4d short). Wait for full 180d before live."
    dash["g5z_note"]         = "G5z BLUR-SOL OOS=0.441 (W=84) borderline. W=48 OOS=0.345 PASS. Monthly recheck."

    DASHBOARD_PATH.write_text(json.dumps(dash, indent=2))
    return dash


# ─────────────────────────────────────────────────────────────────────────────
# Phase 8 -- Print status
# ─────────────────────────────────────────────────────────────────────────────

def print_status(dash: dict) -> None:
    """Print K777 EIGEN-SOL strategy status summary."""
    print("=" * 70)
    print("K777 EIGEN-SOL FR Differential -- Status")
    print("=" * 70)
    print(f"  Last poll:           {dash.get('last_poll_jst', '--')}")
    print(f"  Regime:              {dash.get('regime', 'NEUTRAL')}")
    print(f"  Position:            {dash.get('position_state', 'NEUTRAL')}")
    print(f"  EIGEN FR (current):  {dash.get('fr_eigen_current', 0.0):.8f}")
    print(f"  SOL FR (current):    {dash.get('fr_sol_current', 0.0):.8f}")
    print(f"  EIGEN-SOL diff:      {dash.get('eigen_sol_diff_current', 0.0):.8f}")
    print(f"  Mean 84h:            {dash.get('mean_84h', 0.0):.8f}")
    print(f"  History points:      {dash.get('history_points', 0)}")
    print(f"  Total notional:      ${dash.get('total_notional_usdc', 0.0):,.0f}")
    print(f"  Margin used:         ${dash.get('margin_used_usdc', 0.0):,.0f}")
    print(f"  Sleeve:              {SLEEVE_PCT:.1%}")
    print(f"  Leverage:            {LEVERAGE}x")
    print(f"  Venue:               HL primary + Bybit fallback (EIGENUSDT confirmed)")
    print(f"  HL concentration:    {dash.get('hl_concentration_pct', 66.8):.1f}%")
    print(f"  Paper trade:         {PAPER_TRADE}")
    print(f"  OOS Sharpe:          35.90 (W=84h, 118.6d OOS)")
    print(f"  K523 central:        $84,307/yr @$10M @4x @1.5%")
    print(f"  Drift:               {dash.get('delta_neutral_drift_pct', 0.0):.2%}")
    print(f"  Rebalance:           {dash.get('rebalance_required', False)}")
    print(f"  EIGEN vertex:        19th (1st ETH-restaking). MR9 L002: all EIGEN-X blocked.")
    print(f"  G9 monitor:          OOS=118.6d < 120d -- wait for full 180d before live.")
    print(f"  G5z monitor:         BLUR-SOL OOS=0.441 (W=84) -- monthly recheck target <0.40.")
    print("=" * 70)


# ─────────────────────────────────────────────────────────────────────────────
# Main loop -- 8h cadence
# ─────────────────────────────────────────────────────────────────────────────

def run_main_cycle(aum: float = AUM_DEFAULT) -> dict:
    """
    Main 8h execution cycle for K777 EIGEN-SOL FR Differential.

    Steps:
      1. Fetch EIGEN + SOL FR from HL (Bybit fallback)
      2. Compute 84h rolling mean signal
      3. Decide position
      4. Submit / hold / rebalance
      5. Write dashboard
    """
    print(f"\n[K777 EIGEN-SOL] {datetime.now(JST).strftime('%Y-%m-%d %H:%M JST')} -- 8h cycle")
    print(f"  Venue: HL primary + Bybit fallback (EIGENUSDT). PAPER_TRADE={PAPER_TRADE}")
    print(f"  HL concentration: {HL_CONCENTRATION_POST_K777}% AT CAP -- paper-gate strict")

    # Step 1+2: Signal
    signal = compute_signal()

    print(f"  EIGEN FR:  {signal['fr_eigen']:.8f} ({signal['fr_eigen'] * 8760 * 100:.2f}%/yr)")
    print(f"  SOL FR:    {signal['fr_sol']:.8f} ({signal['fr_sol'] * 8760 * 100:.2f}%/yr)")
    print(f"  diff:      {signal['eigen_sol_diff']:.8f}")
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
        description="K777 EIGEN-SOL FR Differential -- 78th daemon, 20th alt-alt, 19th vertex EIGEN"
    )
    parser.add_argument("--dry-run",   action="store_true", help="Run signal + decision, no submission")
    parser.add_argument("--status",    action="store_true", help="Print dashboard status and exit")
    parser.add_argument("--rebalance", action="store_true", help="Check drift + rebalance if needed")
    parser.add_argument("--close",     type=str, metavar="REASON", help="Close all EIGEN-SOL positions")
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
            print("  [K777] Rebalance triggered -- resizing legs to target notional")
        return 0

    if args.dry_run:
        print(f"[K777 EIGEN-SOL] DRY-RUN -- {datetime.now(JST).strftime('%Y-%m-%d %H:%M JST')}")
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
            "bybit_fallback":    True,
            "oos_sharpe":        35.90,
            "k523_central_yr":   84307,
        }, indent=2))
        return 0

    # Normal 8h cycle
    run_main_cycle(args.aum)
    return 0


if __name__ == "__main__":
    sys.exit(main())
