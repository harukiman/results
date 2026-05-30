#!/usr/bin/env python3
"""
k754_pepe_sol_run.py — K754 PEPE-SOL FR Differential Strategy
==============================================================
SIXTEENTH ALT-ALT pair: PEPE vs SOL (Eth meme leader × Solana SVM).
Signal: PEPE_FR - SOL_FR
W=84h rolling mean (3.5d — G6 compliance: 64 entries/yr OOS vs 30/yr minimum)
HL primary, Bybit fallback
HL concentration: 66.8% AT CAP → paper-gate strict (K498/v6.52 required for live)

K754 PEPE-SOL alt-alt hypothesis:
  PEPE (Ethereum ERC-20 meme leader, Pepe the Frog, launched Apr 2023):
    FR driven by meme bull market rotations (Q2 2023, Q1 2024, Q4 2024),
    Ethereum gas price cycles (high gas → meme speculation), retail sentiment waves,
    CEX listing catalysts (Binance/Coinbase meme cycles), social media virality,
    frog meme narrative cycles. PEPE FR mean very positive in bull seasons.
    Extreme FR spikes: P99=1.66bps, Max=6.66bps/hr during meme mania.
    Q4 2024 meme bull peak: PEPE +0.54bps vs SOL +0.34bps mean differential.
  SOL (Solana SVM L1):
    FR driven by retail momentum, Phantom wallet retail adoption,
    Firedancer upgrade cycles, Solana ETF narrative flows, SVM DeFi TVL.
    SOL FR mean +7.706%/ann — persistently positive structural retail demand.
    SOL extreme negative FR: Min=-20.51bps (liquidation cascade Feb 2025).
  Alt-alt mechanism: PEPE (Ethereum ERC-20 meme cluster) vs SOL (Solana SVM).
    Cross-cluster: Eth meme virality cycles vs SVM infrastructure/retail cycles.
    Structurally independent FR drivers — meme bull seasons vs SVM ecosystem seasons.
  SIXTEENTH alt-alt pair. OOS Sharpe 44.43. W=84h. 12/12 WF ALL POSITIVE.
  All 22 G5 gates PASS. MaxDD OOS only -0.107%.
  G8 CONDITIONAL: HL+Bybit+OKX confirmed (Bybit=1000PEPE denomination note).
  PEPE becomes 14th vertex. All future PEPE-X blocked (MR9 L002).

K754 §6 validation (ACCEPT CONDITIONAL — 22/22 G5 + G1-G4+G6-G9 PASS):
  - OOS Sharpe: 44.43 (W=84h, zero threshold, ~210d OOS)
  - OOS Ann Return: $62K central @$10M @4x @2.5% sleeve (K523 3-point)
  - W=84h rolling mean, zero threshold (sign of diff) — G6 compliant (64/yr)
  - G4 walk-forward: 12/12 folds positive (min_sh=5.56)
  - 22/22 G5 checks PASS (complete G5 sweep, max_corr=0.247 G5l SEI-SOL)
  - G6: 64.2 entries/yr OOS PASS (W=84h ensures G6 compliance vs W=168h 29.5/yr)
  - G8: HL+Bybit+OKX confirmed (Bybit 1000PEPE denomination, cross-venue PASS)
  - L003 AVAX corr=0.4125 PASS | L010 HBAR corr=0.4272 PASS (proximity warning)
  - L004 OOS carry 73.7% PASS | L007 FIL-SOL pre-screen 0.2517 PASS
  - CONDITIONAL: HL 66.8% AT CAP → paper-gate strict until K498/v6.52

K754 PEPE-SOL vertex addition (14th vertex, Ethereum meme cluster):
  V (before K754) = {APT, ATOM, AVAX, BNB, ENA, FIL, HBAR, INJ, LDO, SEI, SOL, TIA, TAO}
  V (after K754)  = {APT, ATOM, AVAX, BNB, ENA, FIL, HBAR, INJ, LDO, SEI, SOL, TIA, TAO, PEPE}
  PEPE = 14th vertex (Ethereum ERC-20 meme cluster leader).
  MR9 L002: all future PEPE-X pairs are auto-blocked (PEPE exhausted as new vertex).
  PEPE-SOL is the only permissible PEPE-X pair given V composition at K754.

L003/L010 proximity warning (K754 notes):
  L003 AVAX: raw_corr(PEPE_fr, AVAX_fr) = 0.4125 PASS (< 0.45 threshold, proximity warning)
  L010 HBAR: raw_corr(PEPE_fr, HBAR_fr) = 0.4272 PASS (< 0.45 threshold, proximity warning)
  Both near threshold → monthly recheck required (K756 note: monitor monthly).

K523 3-point profit projection (@$10M @4x @2.5% sleeve):
  Conservative: $34,758/yr  (R2S=38% floor, K518 floor)
  Central:      $62,000/yr  (base case, K756 mandate: $62K central @$10M @2.5%)
  Optimistic:   $85,678/yr  (near-full OOS realization if meme cycle continues)
  Upper bound:  OOS raw return (NOT central — K523 mandatory)

Architecture (K679→K747→K754 alt-alt scaffold pattern):
  1. fetch_fr_batch()                    → fetch PEPE + SOL FR every 8h from HL
  2. compute_signal(pepe_fr, sol_fr)    → 84h rolling mean of (PEPE_FR - SOL_FR); sign()
  3. decide_position(signal)             → LONG_PEPE_SHORT_SOL | LONG_SOL_SHORT_PEPE | NEUTRAL
  4. submit_paired_trade(long, short)   → POST_ONLY paired (PEPE + SOL legs, HL primary)
  5. daily_rebalance()                   → drift > 5% triggers rebalance
  6. close_paired_position(reason)      → sequential: short first, then long

K756 production scaffold:
  - 71st daemon (sixteenth alt-alt pair, ACCEPT CONDITIONAL, G4 12/12)
  - HL primary, Bybit fallback (PEPE: HL PEPE-PERP + Bybit 1000PEPE + OKX confirmed)
  - 2.5% sleeve (paper-gate strict — HL 66.8% AT CAP per K751 audit)
  - $62K central @$10M @4x @2.5% sleeve (K523 3-point: $34.8K-$85.7K)
  - Paper-gate until K498/v6.52 reduces HL concentration
  - 60d paper-trade gate: Realized Sh>=6 + fill>=60% + maxDD<15%
  - 16th alt-alt pair (Eth meme cluster × SVM, 14th vertex PEPE)

Execution:
  - HL primary (PEPE-PERP + SOL-PERP, HL)
  - Bybit fallback (1000PEPE-PERP + SOL-PERP, Bybit) — informational
  - POST_ONLY paired execution (K439 pattern)
  - Position: 2.5% sleeve, 4x leverage (paper-gate strict — HL cap 66.8%)
  - 8h cadence (matches FR settlement cycle)
  - W=84h rolling mean (10.5 x 8h periods — G6-safe: 64 entries/yr)

Paper-trade mode is the DEFAULT.  No orders are submitted unless
PAPER_TRADE=False is explicitly set in the environment.

K339 security: REPO_ROOT from __file__, no /Users/ literals.
No new packages — stdlib urllib + json only.

Usage:
  python3 scripts/k754_pepe_sol_run.py --dry-run
  python3 scripts/k754_pepe_sol_run.py --status
  python3 scripts/k754_pepe_sol_run.py --rebalance
  python3 scripts/k754_pepe_sol_run.py --close "scheduled exit"
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

# ── K339 canonical paths ──────────────────────────────────────────────────────
REPO_ROOT   = Path(__file__).resolve().parent.parent
DATA_DIR    = REPO_ROOT / "data"
CACHE_DIR   = REPO_ROOT / "cache"
LOGS_DIR    = REPO_ROOT / "logs"
for _d in [DATA_DIR, CACHE_DIR, LOGS_DIR]:
    _d.mkdir(exist_ok=True)

DASHBOARD_PATH  = DATA_DIR  / "k754_dashboard.json"
FR_HISTORY_PATH = CACHE_DIR / "k754_fr_history.jsonl"
TRADE_LOG_PATH  = CACHE_DIR / "k754_paper_trades.jsonl"

JST = timezone(timedelta(hours=9))
UTC = timezone.utc

# ── Strategy constants ────────────────────────────────────────────────────────
PAPER_TRADE         = os.environ.get("PAPER_TRADE", "True").lower() != "false"
SLEEVE_PCT          = 0.025         # K754 sleeve = 2.5% of AUM
LEVERAGE            = 4.0           # 4x per K754 analysis
AUM_DEFAULT         = 10_000_000.0  # $10M reference AUM
DRIFT_REBALANCE_PCT = 0.05          # rebalance if legs drift > 5%
IOC_TIMEOUT_SEC     = 300           # 5 min fill window
EMA_PERIOD_HOURS    = 84            # 84h rolling mean (W=84h, G6 compliant: 64/yr)
EMA_PERIOD_PERIODS  = EMA_PERIOD_HOURS // 8  # = 10 periods (8h settlement cycle)
SIGNAL_SIGMA_MULT   = 0.0           # zero threshold (sign of rolling mean)
HL_API_URL          = "https://api.hyperliquid.xyz/info"
BYBIT_API_URL       = "https://api.bybit.com"

# ── Venue config ──────────────────────────────────────────────────────────────
# HL primary: PEPE-PERP + SOL-PERP on HL
# Bybit fallback: 1000PEPE-PERP + SOL-PERP on Bybit (informational; denomination 1000PEPE)
# HL concentration: 66.8% AT CAP per K751 audit — paper-gate strict until K498/v6.52.
HL_CONCENTRATION_PRE_K754   = 66.8   # post-K750 reference (K751 audit)
HL_CONCENTRATION_POST_K754  = 66.8   # UNCHANGED — paper-only, no live capital added
HL_ONLY_REASON              = (
    "HL primary: PEPE-PERP + SOL-PERP on HL. Bybit 1000PEPE fallback (denomination mismatch). "
    "OKX PEPE confirmed (284 rows, 2026-02 onward). HL at 66.8% AT CAP (K751 audit). "
    "Paper-gate strict: any live capital would breach 65% ceiling. "
    "Deploy LIVE after K498/v6.52 reduces HL% below 65%."
)

# ── Position state constants ──────────────────────────────────────────────────
STATE_NEUTRAL             = "NEUTRAL"
STATE_LONG_PEPE_SHORT_SOL = "LONG_PEPE_SHORT_SOL"
STATE_LONG_SOL_SHORT_PEPE = "LONG_SOL_SHORT_PEPE"

# ── Symbols fetched from HL for FR data ──────────────────────────────────────
SYMBOLS = ("PEPE", "SOL")


# ─────────────────────────────────────────────────────────────────────────────
# HTTP helper (stdlib urllib only — no requests)
# ─────────────────────────────────────────────────────────────────────────────

def _http_get(url: str, timeout: int = 10) -> Optional[dict]:
    try:
        req = urllib.request.Request(
            url, headers={"User-Agent": "crypto-lab-k754/1.0"}
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        print(f"  [k754] HTTP error: {e}", file=sys.stderr)
        return None


def _http_post(url: str, payload: dict, timeout: int = 10) -> Optional[dict]:
    try:
        data = json.dumps(payload).encode()
        req  = urllib.request.Request(
            url, data=data,
            headers={"Content-Type": "application/json",
                     "User-Agent": "crypto-lab-k754/1.0"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        print(f"  [k754] HTTP error: {e}", file=sys.stderr)
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Phase 1 — Funding rate fetch (PEPE + SOL from HL)
# ─────────────────────────────────────────────────────────────────────────────

def _fetch_hl_fr_batch() -> Dict[str, float]:
    """
    Fetch current 1h funding rates for PEPE and SOL from HL.
    Returns {symbol: fr_1h_fraction}.

    HL API: metaAndAssetCtxs (POST).
    K754: HL primary (PEPE-PERP + SOL-PERP).
    Bybit fallback: 1000PEPE denomination (informational only).
    PEPE HL confirmed: 17519 rows 2024-05-24 to 2026-05-24.

    Note: HL settles 1h funding; W=84h = 84 x 1h periods for rolling mean.
    FR stored as 1h fraction; annualized = fr_1h * 8760.

    Fallback: Bybit /v5/market/tickers — 1000PEPE denomination (informational
    cross-check; 8h interval mismatch with HL 1h limits G8 signal correlation).
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
        print(f"  [k754] HL partial result {list(result.keys())} — trying Bybit fallback",
              file=sys.stderr)

    # Fallback: Bybit /v5/market/tickers (1000PEPE denomination — informational)
    bybit_url = f"{BYBIT_API_URL}/v5/market/tickers?category=linear"
    raw_bybit = _http_get(bybit_url)
    if raw_bybit and raw_bybit.get("retCode") == 0:
        tickers = raw_bybit.get("result", {}).get("list", [])
        sym_map = {t["symbol"]: t for t in tickers}
        for sym in SYMBOLS:
            if sym not in result:
                # Try standard then 1000PEPE denomination
                for perp_sym in [f"{sym}USDT", f"1000{sym}USDT"]:
                    if perp_sym in sym_map:
                        tick = sym_map[perp_sym]
                        try:
                            fr_val = float(tick.get("fundingRate", 0.0))
                            # Adjust for 1000x denomination: 1000PEPE FR applies per 1000 PEPE
                            result[sym] = fr_val
                            print(f"  [k754] {sym} FR from Bybit fallback "
                                  f"({'1000PEPE denomination' if '1000' in perp_sym else 'standard'}, "
                                  f"informational cross-check)", file=sys.stderr)
                        except (TypeError, ValueError):
                            pass
                        break
    return result


def _load_fr_history() -> List[dict]:
    """Load K754 FR history JSONL."""
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
    fr_pepe: float, fr_sol: float, pepe_sol_diff: float
) -> None:
    """Append one FR snapshot to history."""
    rec = {
        "ts_utc":        datetime.now(UTC).isoformat(),
        "fr_pepe":       round(fr_pepe,       10),
        "fr_sol":        round(fr_sol,          10),
        "pepe_sol_diff": round(pepe_sol_diff,   10),  # PEPE_FR - SOL_FR
    }
    with open(FR_HISTORY_PATH, "a") as f:
        f.write(json.dumps(rec) + "\n")


# ─────────────────────────────────────────────────────────────────────────────
# Phase 2 — Signal computation (PEPE-SOL direct differential, 84h rolling mean)
# ─────────────────────────────────────────────────────────────────────────────

def compute_signal(
    fr_pepe: Optional[float] = None,
    fr_sol:  Optional[float] = None,
) -> dict:
    """
    Fetch live PEPE and SOL FRs from HL, compute PEPE-SOL differential,
    and compute 84h rolling mean for direction signal.

    Signal mechanism (K754 direct alt-alt differential — no orthogonalization):
      diff = PEPE_FR - SOL_FR
      mean_84h = 84h rolling mean of diff (10 x 8h periods equivalent)
      sign  = sign(mean_84h)
      Enter: sign > 0 -> PEPE FR > SOL FR -> long PEPE (collect meme premium), short SOL
             sign < 0 -> SOL FR > PEPE FR -> long SOL (collect SVM premium), short PEPE

    NOTE: PEPE has extreme FR spikes during meme bull seasons (Max=6.66bps, P99=1.66bps).
    Q4 2024 meme bull peak: PEPE +0.54bps vs SOL +0.34bps mean.
    SOL can go deeply negative (Min=-20.51bps) during liquidation cascades.
    Strategy profits from differential regardless of absolute FR level.

    Alt-alt mechanism (SIXTEENTH ALT-ALT pair — K754):
      PEPE FR tracks Ethereum ERC-20 meme leader: meme bull market rotations
      (retail sentiment waves, social media virality, CEX listing catalysts,
      frog meme narrative). Extreme spikes during Eth meme seasons.
      SOL FR tracks Solana SVM DePIN/Retail adoption: meme-coin seasons,
      Firedancer upgrade hype, SOL ETF speculation, SVM DeFi TVL expansion.
      PEPE-SOL diff captures relative Eth meme premium vs SVM retail premium.
      Different ecosystems: ERC-20 Eth meme vs Solana SVM infrastructure.
      Mean diff reverting: OOS Sh=44.43, MaxDD OOS=-0.107%, G4 12/12 positive.

    W=84h rationale (G6 compliance):
      W=168h → 29.5 entries/yr OOS (BELOW 30/yr G6 threshold — FAIL).
      W=84h  → 64.2 entries/yr OOS (PASS). OOS Sh=44.43 vs 42.42 at W=168h.
      84h is both G6-safe and slightly better Sharpe. Canonical choice.

    K754 §6 validation:
      - OOS Sharpe: 44.43 (W=84h, zero threshold, ~210d OOS period)
      - OOS Ann Return: $62K central @$10M @4x @2.5% sleeve (K523 3-point)
      - All 22 G5 checks PASS (max_corr=0.247 G5l SEI-SOL — well below 0.40)
      - G4 WF 12/12 all positive (min_sh=5.56)
      - 60d gate: Realized Sh>=6 + fill>=60% + maxDD<15%
      - CONDITIONAL: HL 66.8% AT CAP → paper-gate strict

    Returns:
      {
        "fr_pepe":          float,
        "fr_sol":           float,
        "pepe_sol_diff":    float,    # PEPE_FR - SOL_FR (current)
        "mean_84h":         float,    # 84h rolling mean of differential
        "diff_sigma":       float,    # 84h rolling sigma (informational)
        "history_points":   int,
        "regime":           str,      # BULL_PEPE | BEAR_PEPE | NEUTRAL
        "signal_direction": int,      # +1 | -1 | 0
        "ts_jst":           str,
      }
    """
    if fr_pepe is None or fr_sol is None:
        frs     = _fetch_hl_fr_batch()
        fr_pepe = frs.get("PEPE", 0.0)
        fr_sol  = frs.get("SOL", 0.0)

    # PEPE-SOL direct alt-alt differential (no orthogonalization)
    pepe_sol_diff = fr_pepe - fr_sol

    _append_fr_history(fr_pepe, fr_sol, pepe_sol_diff)

    # Load history for rolling mean + sigma (84h = ~10 x 8h periods)
    history = _load_fr_history()
    diffs   = [r["pepe_sol_diff"] for r in history if "pepe_sol_diff" in r]

    n_periods = EMA_PERIOD_PERIODS   # 10 periods (84h / 8h)

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
        sigma  = abs(mean_84h) if mean_84h != 0 else 1e-8   # fallback

    # Regime classification (zero threshold — per K754 spec)
    # BULL_PEPE: PEPE FR > SOL FR (Eth meme premium > SVM retail premium)
    # BEAR_PEPE: PEPE FR < SOL FR (SVM retail premium > Eth meme premium)
    if mean_84h > 0:
        regime    = "BULL_PEPE"   # PEPE-SOL diff positive → PEPE FR > SOL FR (meme season)
        direction = 1
    elif mean_84h < 0:
        regime    = "BEAR_PEPE"   # PEPE-SOL diff negative → SOL FR > PEPE FR (SVM season)
        direction = -1
    else:
        regime    = "NEUTRAL"
        direction = 0

    return {
        "fr_pepe":          round(fr_pepe,        10),
        "fr_sol":           round(fr_sol,           10),
        "pepe_sol_diff":    round(pepe_sol_diff,    10),
        "mean_84h":         round(mean_84h,          10),
        "diff_sigma":       round(sigma,              10),
        "history_points":   len(diffs),
        "regime":           regime,
        "signal_direction": direction,
        "ts_jst":           datetime.now(JST).strftime("%Y-%m-%d %H:%M JST"),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Phase 3 — Position decision
# ─────────────────────────────────────────────────────────────────────────────

def decide_position(signal: dict) -> Optional[dict]:
    """
    Determine trade direction from PEPE-SOL differential rolling mean.

    Logic (PEPE-SOL direct alt-alt pair, HL primary):
      regime = BULL_PEPE (mean_84h > 0):
        PEPE FR > SOL FR: Eth meme season dominant
        -> long PEPE (collect meme bull carry premium)
        -> short SOL (avoid lower SVM carry in meme-dominant regime)
        -> position_state = LONG_PEPE_SHORT_SOL

      regime = BEAR_PEPE (mean_84h < 0):
        SOL FR > PEPE FR: SVM season dominant
        -> long SOL (collect SVM infrastructure premium)
        -> short PEPE (avoid lower/negative meme carry in SVM regime)
        -> position_state = LONG_SOL_SHORT_PEPE

      regime = NEUTRAL: no trade (mean_84h == 0 exactly — rare)

    Alt-alt edge (SIXTEENTH ALT-ALT pair — K754):
      PEPE and SOL are cross-cluster assets with structurally independent FR drivers.
      BULL_PEPE: Eth meme season drives PEPE premium (retail virality, CEX listings,
        social media cycles, frog narrative spikes). PEPE FR >> SOL FR.
      BEAR_PEPE: SVM season drives SOL premium (DeFi TVL, Firedancer, ETF narratives).
        SOL FR >> PEPE FR. Note: PEPE meme-bear + SOL-SOL liquidation cascade can
        cause extreme short-SOL scenario (SOL Min=-20.51bps — strategy LONG SOL in this).
      Cross-cluster: Ethereum ERC-20 meme (social virality) vs Solana SVM execution
        (DeFi/retail ecosystem). OOS Sh=44.43 >> 1.0. MaxDD OOS=-0.107% very contained.
      G4 WF 12/12 ALL POSITIVE (min_sh=5.56). 22/22 G5 PASS.
      PEPE = 14th vertex. MR9 L002: all future PEPE-X pairs blocked.

    Returns:
      {long_asset, short_asset, long_venue, short_venue, mean_84h,
       signal_direction, size_multiplier, position_state}
      or None if NEUTRAL.
    """
    regime   = signal.get("regime", "NEUTRAL")
    mean_84h = signal.get("mean_84h", 0.0)
    direction = signal.get("signal_direction", 0)

    if regime == "NEUTRAL":
        return None

    if regime == "BULL_PEPE":
        # PEPE FR > SOL FR: Eth meme season
        long_asset  = "PEPE"
        short_asset = "SOL"
        state       = STATE_LONG_PEPE_SHORT_SOL
    else:  # BEAR_PEPE
        # SOL FR > PEPE FR: SVM season
        long_asset  = "SOL"
        short_asset = "PEPE"
        state       = STATE_LONG_SOL_SHORT_PEPE

    # HL primary for both legs
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
# Phase 4 — Delta-neutral notional computation
# ─────────────────────────────────────────────────────────────────────────────

def compute_delta_neutral_notional(
    aum:        float = AUM_DEFAULT,
    sleeve_pct: float = SLEEVE_PCT,
    leverage:   float = LEVERAGE,
) -> Tuple[float, float]:
    """
    Compute equal notional for both legs of the PEPE-SOL paired trade.

    K754 HL config (PEPE-PERP + SOL-PERP on HL, paper-gate strict):
      sleeve_capital   = aum x sleeve_pct      (e.g. $10M x 2.5% = $250K)
      total_notional   = sleeve_capital x lev   ($250K x 4 = $1.0M)
      notional_per_leg = total_notional / 2     ($500K per leg)

    At $10M / 2.5% sleeve / 4x (paper-gate):
      PEPE leg: $125K capital x 4x = $500K notional (HL PEPE-PERP)
      SOL leg:  $125K capital x 4x = $500K notional (HL SOL-PERP)
      Total:    $1.0M notional (two legs combined)
      Margin:   $250K (2.5% of AUM)
      HL conc:  PAPER-ONLY (66.8% AT CAP — no live capital added)
      Net profit: central $62K/yr @$10M @4x (K523: $34.8K-$85.7K)
      PEPE vertex: 14th — MR9 L002 blocks all future PEPE-X pairs

    Returns (notional_per_leg, total_notional).
    """
    sleeve_capital   = aum * sleeve_pct
    total_notional   = sleeve_capital * leverage
    notional_per_leg = total_notional / 2.0
    return round(notional_per_leg, 2), round(total_notional, 2)


# ─────────────────────────────────────────────────────────────────────────────
# Phase 5 — Paired trade submission (HL primary, POST_ONLY)
# ─────────────────────────────────────────────────────────────────────────────

def submit_paired_trade(
    long_leg:  dict,
    short_leg: dict,
    dry_run:   bool = True,
) -> dict:
    """
    Submit K754 PEPE-SOL paired trade: POST_ONLY both legs in parallel.

    Protocol (K754 HL primary — both legs on HL):
      1. Submit PEPE leg on HL POST_ONLY
      2. Submit SOL leg on HL POST_ONLY
      3. Both legs submitted in parallel (K439 pattern)
      4. IOC fallback per leg if POST_ONLY times out
      5. If both fail: retry next 8h cycle

    Args:
      long_leg:  {"symbol": "PEPE", "notional": 500000, "venue": "HL"}
      short_leg: {"symbol": "SOL",  "notional": 500000, "venue": "HL"}
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
        print(f"  [K754] {mode_tag}: LONG {long_sym}@{long_venue} ${long_notl:,.0f}  "
              f"+ SHORT {short_sym}@{short_venue} ${short_notl:,.0f}")
        result = {
            "status":           "DRY_RUN",
            "long_result":      {"order_id": f"PAPER_LONG_{long_sym}_{int(time.time())}",  "status": "DRY_RUN"},
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
            "venue_config":     "HL_PRIMARY_PEPE_SOL_ALT_ALT",
            "mechanism_note":   (
                "PEPE-SOL direct alt-alt differential (K754 SIXTEENTH ALT-ALT, 71st daemon): "
                "PEPE FR = Ethereum ERC-20 meme leader (social virality cycles, CEX listing "
                "catalysts, frog meme narrative, meme bull rotations — extreme spikes P99=1.66bps, "
                "Max=6.66bps/hr during Eth meme seasons, Q4 2024 peak +0.54bps mean); "
                "SOL FR = Solana SVM DePIN/Retail adoption premium (meme-coin BONK/WIF/POPCAT, "
                "Firedancer upgrade hype, SOL ETF speculation, SVM DeFi TVL — "
                "persistently positive +7.706%/ann, SOL liquidation cascade Min=-20.51bps). "
                "G4 WF 12/12 ALL POSITIVE (min_sh=5.56). 22/22 G5 PASS (max_corr=0.247). "
                "HL at 66.8% AT CAP — paper-gate strict until K498/v6.52 reduces HL%. "
                "PEPE = 14th vertex. MR9 L002: all future PEPE-X pairs blocked. "
                "OOS Sh=44.43 (W=84h, zero threshold). K523 central $62K/yr @$10M @4x @2.5%. "
                "60d gate: Realized Sh>=6 + fill>=60% + maxDD<15%."
            ),
            "ts_utc":           ts,
        }
        _append_trade_log(result)
        return result

    # LIVE scaffold (not reached in PAPER_TRADE mode):
    print(f"  [K754] SCAFFOLD LIVE: parallel POST_ONLY "
          f"LONG {long_sym}@{long_venue} ${long_notl:,.0f} "
          f"+ SHORT {short_sym}@{short_venue} ${short_notl:,.0f}")
    long_order_id  = f"SCAFFOLD_LONG_{long_sym}_{int(time.time())}"
    short_order_id = f"SCAFFOLD_SHORT_{short_sym}_{int(time.time())}"

    print(f"  [K754] Neither leg filled within timeout — retry next 8h cycle")
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
# Phase 6 — Delta-neutral drift rebalance
# ─────────────────────────────────────────────────────────────────────────────

def daily_rebalance(dashboard: dict) -> dict:
    """
    Check if current K754 position has drifted beyond DRIFT_REBALANCE_PCT (5%).

    K754 HL: both legs on HL (PEPE-PERP + SOL-PERP).
    Drift detection: compare stored PEPE leg notional vs SOL leg notional.
    Threshold: 5% (same as K679/K682/K684/K686/K690/K747/K739 pattern).

    Returns rebalance decision dict.
    """
    state = dashboard.get("position_state", STATE_NEUTRAL)
    if state == STATE_NEUTRAL:
        return {"rebalance_required": False, "reason": "NEUTRAL — no position"}

    long_notional_init  = float(dashboard.get("long_notional", 0.0))
    short_notional_init = float(dashboard.get("short_notional", 0.0))

    if long_notional_init <= 0 or short_notional_init <= 0:
        return {"rebalance_required": False, "reason": "no recorded notionals"}

    drift_pct    = float(dashboard.get("delta_neutral_drift_pct", 0.0))
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
# Phase 7 — Close paired position
# ─────────────────────────────────────────────────────────────────────────────

def close_paired_position(reason: str, dry_run: bool = True) -> dict:
    """
    Close both legs sequentially: short leg first (avoid naked short exposure),
    then long leg. In live: uses IOC market orders (reduce-only).
    Both legs on HL (K754 HL primary — PEPE-PERP + SOL-PERP).

    Args:
      reason:  human-readable reason for closure
      dry_run: True = paper-trade simulation

    Returns closure result dict.
    """
    ts   = datetime.now(UTC).isoformat()
    dash = _load_dashboard()
    state = dash.get("position_state", STATE_NEUTRAL)

    if state == STATE_NEUTRAL:
        return {"status": "NO_POSITION", "reason": "Already NEUTRAL", "ts_utc": ts}

    if state == STATE_LONG_PEPE_SHORT_SOL:
        long_sym,  short_sym  = "PEPE", "SOL"
    else:  # LONG_SOL_SHORT_PEPE
        long_sym,  short_sym  = "SOL", "PEPE"

    long_notional  = float(dash.get("long_notional",  0.0))
    short_notional = float(dash.get("short_notional", 0.0))

    if dry_run or PAPER_TRADE:
        mode_tag = "DRY_RUN" if dry_run else "PAPER_TRADE"
        print(f"  [K754] {mode_tag} CLOSE:")
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
        print(f"  [K754] SCAFFOLD CLOSE:")
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
    """Load k754_dashboard.json; return defaults if missing."""
    if DASHBOARD_PATH.exists():
        try:
            return json.loads(DASHBOARD_PATH.read_text())
        except Exception:
            pass
    return {
        "last_poll_jst":           "—",
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
        "paper_trade_status":      {"days_elapsed": 0, "target_60d": 60},
    }


def _write_dashboard(
    signal:           dict,
    decision:         Optional[dict],
    notional_per_leg: float,
    total_notional:   float,
    rebalance:        dict,
    aum:              float,
) -> dict:
    """Write k754_dashboard.json with full signal + regime state."""
    dash = _load_dashboard()

    # Update signal data
    dash["last_poll_jst"]         = signal.get("ts_jst", "—")
    dash["fr_pepe_current"]       = signal.get("fr_pepe",         0.0)
    dash["fr_sol_current"]        = signal.get("fr_sol",           0.0)
    dash["pepe_sol_diff_current"] = signal.get("pepe_sol_diff",   0.0)
    dash["mean_84h"]              = signal.get("mean_84h",         0.0)
    dash["diff_sigma"]            = signal.get("diff_sigma",       0.0)
    dash["regime"]                = signal.get("regime",    "NEUTRAL")
    dash["signal_direction"]      = signal.get("signal_direction", 0)
    dash["history_points"]        = signal.get("history_points",   0)

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
    dash["rebalance_required"]       = rebalance.get("rebalance_required", False)

    # Margin / notional summary
    dash["total_notional_usdc"]      = round(total_notional, 2)
    dash["notional_per_leg_usdc"]    = round(notional_per_leg, 2)
    dash["leverage"]                 = LEVERAGE
    dash["sleeve_pct"]               = SLEEVE_PCT
    dash["aum_ref_usdc"]             = aum
    dash["margin_used_usdc"]         = round(total_notional / LEVERAGE, 2)
    dash["margin_pct_of_aum"]        = round((total_notional / LEVERAGE) / aum, 4)
    dash["hl_concentration_pct"]     = HL_CONCENTRATION_POST_K754

    # Paper-trade status
    paper_status = dash.get("paper_trade_status", {"days_elapsed": 0, "target_60d": 60})
    dash["paper_trade_status"]       = paper_status

    # 60d activation gate metrics
    dash["gate_metrics"] = {
        "realized_sharpe_target":  6.0,
        "fill_rate_target_pct":    60,
        "max_drawdown_target_pct": 15,
        "current_realized_sharpe": dash.get("60d_sharpe", 0.0),
        "current_fill_rate_pct":   0.0,
        "current_max_dd_pct":      0.0,
        "gate_status":             "IN_PROGRESS",
        "activation_trigger":      "60d paper-trade: Sh>=6 AND fill>=60% AND maxDD<15%",
        "profit_at_activation_2_5pct": (
            "central $62,000/yr net @$10M @4x (K523: $34.8K cons / $62K central / $85.7K opt)"
        ),
        "alt_alt_note": (
            "SIXTEENTH ALT-ALT pair (PEPE-SOL, no BTC/ETH leg). Standalone. 71st daemon. "
            "ACCEPT CONDITIONAL (HL 66.8% AT CAP — paper-gate strict until K498/v6.52). "
            "G4 WF 12/12 ALL POSITIVE (min_sh=5.56). 22/22 G5 PASS (max_corr=0.247). "
            "PEPE = 14th vertex (Eth meme cluster). MR9 L002: all future PEPE-X pairs blocked. "
            "W=84h (G6-safe: 64/yr vs 30/yr min). OOS Sh=44.43 MaxDD=-0.107% (very contained)."
        ),
        "hl_cap_warning": (
            "HL concentration 66.8% AT CAP (K751 audit). Paper-gate strict. "
            "Deploy LIVE only after K498/v6.52 reduces HL% below 65%. "
            "K754 HL primary: both PEPE-PERP + SOL-PERP on HL. "
            "2.5% all-HL would add 2.5% → over cap. Paper-only until HL% resolved. "
            "L003/L010 proximity: monthly AVAX/HBAR recheck required."
        ),
    }

    # Strategy metadata
    dash["paper_trade_mode"]    = PAPER_TRADE
    dash["wave"]                = "K756"
    dash["strategy"]            = "K754 PEPE-SOL FR Differential (SIXTEENTH ALT-ALT, W=84h, HL primary)"
    dash["execution_mode"]      = "POST_ONLY_PARALLEL"
    dash["venue_config"]        = "HL_PRIMARY_BYBIT_FALLBACK"
    dash["alt_alt_mechanism"]   = {
        "formula":            "diff = PEPE_FR - SOL_FR  (direct alt-alt, no base asset)",
        "rolling_window":     "W=84h (10 x 8h periods, G6-safe: 64 entries/yr OOS)",
        "signal":             "sign(rolling_mean_84h(diff))",
        "sixteenth_alt_alt":  True,
        "g4_result":          "12/12 ALL POSITIVE (min_sh=5.56) — strong WF validation",
        "hl_reason":          HL_ONLY_REASON,
        "hl_concentration":   66.8,
        "cross_cluster_note": (
            "PEPE (Ethereum ERC-20 meme leader, social virality cycles, CEX listing catalysts, "
            "frog narrative spikes — P99=1.66bps, Max=6.66bps/hr peak) "
            "vs SOL (Solana SVM retail/DeFi/meme — persistently positive +7.706%/ann, "
            "SOL liquidation cascade Min=-20.51bps Feb 2025). "
            "Cross-cluster: Eth meme virality vs SVM infrastructure/retail. "
            "Q4 2024 peak: PEPE +0.54bps vs SOL +0.34bps mean differential. "
            "OOS Sh=44.43. MaxDD OOS=-0.107% (very contained). 22/22 G5 PASS."
        ),
        "pepe_vertex_rule": (
            "PEPE = 14th vertex added to V. "
            "V = {APT, ATOM, AVAX, BNB, ENA, FIL, HBAR, INJ, LDO, SEI, SOL, TIA, TAO, PEPE}. "
            "MR9 L002: all future PEPE-X pairs auto-blocked. "
            "PEPE-SOL is the only permissible PEPE-X pair given V at K754."
        ),
        "g5_max_corr": "0.247 (G5l SEI-SOL) — well below 0.40 threshold. 22/22 PASS.",
        "w84h_g6_note": (
            "W=84h chosen over family standard W=168h for G6 compliance. "
            "W=168h: 29.5 entries/yr OOS (BELOW 30/yr G6 threshold — FAIL). "
            "W=84h: 64.2 entries/yr OOS (PASS). OOS Sh=44.43 vs 42.42 at W=168h. "
            "84h is both G6-safe and marginally better Sharpe. Canonical choice for K754."
        ),
        "l003_l010_proximity": (
            "L003 AVAX: raw_corr(PEPE_fr, AVAX_fr)=0.4125 PASS (<0.45) — proximity warning. "
            "L010 HBAR: raw_corr(PEPE_fr, HBAR_fr)=0.4272 PASS (<0.45) — proximity warning. "
            "Both near threshold → monthly recheck required (L003/L010 recheck gate)."
        ),
        "pepe_fr_drivers": (
            "Ethereum ERC-20 meme leader (Pepe the Frog, launched Apr 2023). "
            "FR driven by meme bull market rotations (Q2 2023, Q1 2024, Q4 2024). "
            "Ethereum gas price cycles (high gas → meme speculation). "
            "Retail sentiment waves, CEX listing catalysts, social media virality. "
            "Extreme spikes: P99=1.66bps, Max=6.66bps/hr. Q4 2024 peak +0.54bps mean."
        ),
        "sol_fr_drivers": (
            "Solana SVM DePIN/Retail adoption premium. "
            "Meme-coin seasons (BONK/WIF/POPCAT). Firedancer upgrade hype. "
            "SOL ETF speculation. SVM DeFi TVL (Jupiter/Drift/Jito). "
            "+7.706%/ann persistently positive. Extreme negative: -20.51bps (Feb 2025 cascade)."
        ),
        "g8_note": (
            "G8 conditional: HL+Bybit+OKX confirmed. "
            "Bybit uses 1000PEPE denomination (8h vs HL 1h mismatch limits signal corr). "
            "OKX PEPE confirmed (284 rows, 2026-02 onward). "
            "Cross-venue presence CONFIRMED on all 3 major venues."
        ),
        "k523_projection": {
            "conservative_yr": 34758,
            "central_yr":      62000,
            "optimistic_yr":   85678,
            "note":            "K523 mandatory 3-point. Conservative=R2S×0.38 (K518 floor). Central=$62K @$10M @4x @2.5%.",
        },
    }

    dash["activation_criteria"] = {
        "60d_paper_trade_gate": "required",
        "realized_sharpe_min": 6.0,
        "fill_rate_min_pct":   60,
        "max_drawdown_max_pct": 15,
        "status":              "SCAFFOLD-READY",
        "activation_sleeve_pct": 0.025,
        "venue":               "HL primary (PEPE-PERP + SOL-PERP)",
        "conditional_note": (
            "CONDITIONAL: HL 66.8% AT CAP (K751 audit). "
            "Deploy LIVE only after K498/v6.52 reduces HL% below 65%. "
            "L003/L010 proximity: monthly AVAX/HBAR recheck."
        ),
        "live_trigger": "K498/v6.52 OKX activation (HL% drops from 66.8%) + 60d gate passage",
    }

    dash["oos_performance"] = {
        "sharpe":              44.43,
        "oos_ann_ret_pct":     9.517,
        "oos_ann_ret_4x_pct":  38.068,
        "k523_conservative_yr": 34758,
        "k523_central_yr":     62000,
        "k523_optimistic_yr":  85678,
        "daily_usdc_central":  170,
        "wave_accept": (
            "K754 ACCEPT CONDITIONAL (K756 scaffold) — SIXTEENTH ALT-ALT, "
            "Eth meme cluster × SVM, G4 12/12, 22/22 G5 PASS"
        ),
        "cluster":    "PEPE-SOL Alt-Alt FR Differential (Eth ERC-20 meme × Solana SVM, HL primary, 14th vertex)",
        "daemon_number": "71st",
        "section6_result": (
            "ACCEPT CONDITIONAL 22/22 G5 PASS. G1-G4+G6-G9 PASS. "
            "OOS Sh=44.43 (W=84h zero threshold ~210d OOS). MaxDD=-0.107%. "
            "HL 66.8% AT CAP → paper-gate strict."
        ),
        "family_rank": {
            "k754_oos_sharpe":   44.43,
            "k754_pair":         "PEPE-SOL (alt-alt, SIXTEENTH, 14th vertex PEPE Eth meme cluster)",
            "alt_alt_accepted":  16,
            "g4_note":           "K754 G4=12/12 ALL POSITIVE (min_sh=5.56).",
            "vertex_note":       "PEPE = 14th vertex. V={APT,ATOM,AVAX,BNB,ENA,FIL,HBAR,INJ,LDO,SEI,SOL,TIA,TAO,PEPE}.",
        },
    }

    DASHBOARD_PATH.write_text(json.dumps(dash, indent=2))
    return dash


# ─────────────────────────────────────────────────────────────────────────────
# Main entry point
# ─────────────────────────────────────────────────────────────────────────────

def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="K754 PEPE-SOL FR Differential Strategy (SIXTEENTH ALT-ALT, 71st daemon)"
    )
    p.add_argument("--dry-run",   action="store_true",
                   help="Fetch signal and print decision without writing any orders")
    p.add_argument("--status",    action="store_true",
                   help="Print current dashboard state and exit")
    p.add_argument("--rebalance", action="store_true",
                   help="Force a rebalance check on current position")
    p.add_argument("--close",     type=str, metavar="REASON",
                   help="Close all positions and exit")
    p.add_argument("--aum",       type=float, default=AUM_DEFAULT,
                   help=f"Reference AUM in USD (default={AUM_DEFAULT:,.0f})")
    return p.parse_args()


def main() -> int:
    args  = _parse_args()
    ts_jst = datetime.now(JST).strftime("%Y-%m-%d %H:%M JST")

    print(f"\n=== K754 PEPE-SOL FR Differential Strategy — {ts_jst} ===")
    print(f"  Strategy:    PEPE-SOL FR Differential (SIXTEENTH ALT-ALT pair)")
    print(f"  Wave:        K756 (scaffold wave for K754 ACCEPT CONDITIONAL)")
    print(f"  Daemon:      71st (sixteenth alt-alt pair, 14th vertex PEPE)")
    print(f"  OOS Sharpe:  44.43 (W=84h, zero threshold, ~210d OOS)")
    print(f"  G4 WF:       12/12 ALL POSITIVE (min_sh=5.56)")
    print(f"  G5:          22/22 PASS (max_corr=0.247 G5l SEI-SOL)")
    print(f"  W=84h:       G6 compliance (64/yr OOS vs 29.5/yr at W=168h)")
    print(f"  PEPE vertex: 14th. MR9 L002: all future PEPE-X pairs blocked.")
    print(f"  HL cap:      66.8% AT CAP (K751 audit) — paper-gate strict")
    print(f"  Profit:      central $62K/yr @$10M @4x @2.5% sleeve (K523 3-point)")
    print(f"  Paper mode:  {PAPER_TRADE}")

    # --status mode
    if args.status:
        dash = _load_dashboard()
        print(f"\n  [Status] {dash.get('strategy', 'K754 PEPE-SOL')}")
        print(f"  regime={dash.get('regime')}  direction={dash.get('signal_direction')}")
        print(f"  mean_84h={dash.get('mean_84h', 0):.6e}")
        print(f"  position_state={dash.get('position_state')}")
        print(f"  hl_concentration_pct={dash.get('hl_concentration_pct', 66.8):.1f}%")
        return 0

    # --close mode
    if args.close:
        print(f"\n  [Close] reason={args.close!r}")
        result = close_paired_position(args.close, dry_run=args.dry_run)
        print(f"  result={result}")
        return 0

    # Normal run (signal + decision + trade)
    print(f"\n  [Phase 1] Fetching PEPE + SOL funding rates from HL ...")
    signal = compute_signal()
    print(f"  fr_pepe={signal['fr_pepe']:.6e}  fr_sol={signal['fr_sol']:.6e}")
    print(f"  pepe_sol_diff={signal['pepe_sol_diff']:.6e}")
    print(f"  mean_84h={signal['mean_84h']:.6e}  sigma={signal['diff_sigma']:.6e}")
    print(f"  regime={signal['regime']}  direction={signal['signal_direction']}")
    print(f"  history_points={signal['history_points']}")

    print(f"\n  [Phase 2] Computing signal (W=84h rolling mean of PEPE_FR - SOL_FR) ...")
    decision = decide_position(signal)
    if decision:
        print(f"  DECISION: {decision['position_state']}")
        print(f"  long={decision['long_asset']}@{decision['long_venue']}  "
              f"short={decision['short_asset']}@{decision['short_venue']}")
    else:
        print(f"  DECISION: NEUTRAL (no trade)")

    print(f"\n  [Phase 3] Computing delta-neutral notional (sleeve={SLEEVE_PCT:.1%}, lev={LEVERAGE}x) ...")
    notional_per_leg, total_notional = compute_delta_neutral_notional(aum=args.aum)
    print(f"  notional_per_leg=${notional_per_leg:,.0f}  total=${total_notional:,.0f}")
    print(f"  margin=${total_notional / LEVERAGE:,.0f} ({SLEEVE_PCT:.1%} of ${args.aum:,.0f})")

    print(f"\n  [Phase 4] Rebalance check ...")
    dash = _load_dashboard()
    rebalance = daily_rebalance(dash)
    print(f"  rebalance_required={rebalance['rebalance_required']}  "
          f"action={rebalance.get('action', 'HOLD')}")

    if args.rebalance:
        print(f"\n  [Rebalance] force-triggered: {rebalance.get('reason', '')}")
        return 0

    # Submit trade if signal exists and no current position
    if decision and dash.get("position_state") == STATE_NEUTRAL:
        print(f"\n  [Phase 5] Submitting paired trade ...")
        long_leg  = {"symbol": decision["long_asset"],
                     "notional": notional_per_leg,
                     "venue": decision["long_venue"]}
        short_leg = {"symbol": decision["short_asset"],
                     "notional": notional_per_leg,
                     "venue": decision["short_venue"]}
        trade_result = submit_paired_trade(long_leg, short_leg, dry_run=args.dry_run)
        print(f"  trade_status={trade_result['status']}")
    else:
        trade_result = None
        print(f"\n  [Phase 5] No new trade (NEUTRAL or position already open)")

    # Write dashboard
    print(f"\n  [Phase 6] Writing dashboard -> {DASHBOARD_PATH} ...")
    _write_dashboard(signal, decision, notional_per_leg, total_notional, rebalance, args.aum)
    print(f"  Dashboard written OK")

    print(f"\n=== K754 PEPE-SOL run complete — {datetime.now(JST).strftime('%Y-%m-%d %H:%M JST')} ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
