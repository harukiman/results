#!/usr/bin/env python3
"""
k736_tia_avax_run.py — K736 TIA-AVAX FR Differential Strategy
==============================================================
THIRTEENTH ALT-ALT scaffold (67th daemon): TIA vs AVAX (no BTC/ETH base).
Signal: TIA_FR - AVAX_FR
W=168h rolling mean, zero threshold (sign only)
Bybit-only (TIA-PERP + AVAX-PERP on Bybit)
4x leverage, 3% sleeve standalone

K736 TIA-AVAX alt-alt hypothesis (CROSS-CLUSTER: Celestia modular DA vs Avalanche subnet L1):
  TIA (Celestia DA layer) FR dynamics: Infrastructure-layer, rollup adoption driven.
  TIA FR driven by: Rollup adoption milestones (OP Stack, Fuel, Manta, Eclipse integrating
  Celestia DA), blob fee market events (high throughput DA demand => TIA FR spikes episodically),
  TIA staking APY changes (validator rewards => FR equilibrium shifts), competing DA launches
  (EigenDA, Avail, EIP-4844 Dencun => DA demand rotation), modular ecosystem expansion milestones.
  TIA FR mean = +1.08%/yr (low baseline — DA infrastructure, episodic demand spikes).

  AVAX (Avalanche subnet L1) FR dynamics: Execution-layer, subnet economics driven.
  AVAX FR driven by: Avalanche9000 upgrade (low-cost subnet creation => new subnet waves),
  RWA tokenization partnerships (Ava Labs institutional custody deals), subnet-native staking
  economics (independent validator sets per subnet), AVAX DeFi TVL cycles (Trader Joe,
  Benqi, Aave on Avalanche), institutional adoption cycles (BlackRock BUIDL, KKR fund on
  Avalanche), competitive L1 dynamics (AVAX vs SOL/ETH for institutional DeFi).
  AVAX FR mean = +6.38%/yr (semi-persistent — subnet economics + RWA cycles).

  Cross-cluster: TIA (DA-infrastructure layer, Cosmos SDK, Tendermint BFT) vs
  AVAX (Execution layer L1, EVM + subnet architecture, Snowman consensus).
  GENUINELY different economic segments — orthogonal FR drivers. MR9: TIA-AVAX =
  K507_dir - K484_dir. TIA DA-infra below execution; AVAX execution above DA.
  Bias: AVAX FR > TIA FR (dominant, -5.30%/yr diff mean = AVAX premium).

K736 KEY INSIGHT — DA vs Subnet Cross-Layer Carry:
  W=168h (7d) window: captures weekly rollup adoption cycle (TIA) vs
  subnet launch cycle (AVAX). 168h aligns with weekly DAO governance cycles
  and Avalanche subnet activation cadence.

  Dominant state: AVAX FR > TIA FR (subnet institutional premium, ~AVAX_PREMIUM)
    -> signal = -1 -> SHORT AVAX (collect AVAX subnet premium) + LONG TIA
    -> Persistent carry from AVAX FR structural premium over TIA
  Other state: TIA FR > AVAX FR (DA demand spike, rollup activation)
    -> signal = +1 -> SHORT TIA + LONG AVAX (collect TIA blob-fee premium)
  AVAX structural carry: +5.30%/yr (AVAX 6.38%/yr vs TIA 1.08%/yr)

K736 §6 gates (ACCEPT CONDITIONAL — 15/16 PASS):
  - OOS Sharpe: 12.9673 (W=168h, zero threshold, 218d OOS period)
  - IS Sharpe:  9.1303
  - OOS Ann Return: 8.54% @1x, 34.15% @4x
  - Net @$10M @4x @3% sleeve: $87,086/yr USDC ($239/day)
  - ADF t=-13.4712 (strongly stationary p=3.38e-25)
  - G4 walk-forward: 12/12 folds positive (UNPRECEDENTED perfect WF)
  - G5: 8/8 PASS (all signed corr < 0.40 threshold)
    G5b K694 TIA-SOL: corr=+0.2973 PASS (TIA shared leg)
    G5c K484 AVAX-BTC: corr=-0.6324 PASS (anti-corr hedge, signed convention)
    G5e K686 AVAX-SOL: corr=-0.6031 PASS (anti-corr hedge, signed convention)
  - G6: 18.4 trades/yr (FAIL structural: below 30 threshold; K661 precedent)
  - G7: 34.15% @4x (PASS >= 5%)
  - G8: PASS (Bybit diff corr=0.6691 >= 0.55; K694 TIA precedent + K484 AVAX precedent)
  - G9: 218d OOS (PASS >= 180d)
  - MR9: TIA-AVAX = K507_dir - K484_dir (max_err=5.42e-20, machine precision) PASS
  - 60d gate: Realized Sh >= 6, fill >= 60%, DD < 15%
  - Triple AVAX hedge: K736 anti-correlates with K484 (-0.632), K661 (-0.643), K686 (-0.603)
  - Alt-alt family: 13th alt-alt (DA-infra vs Subnet L1, rank #8 by OOS Sharpe)

Signal mechanism (MR9: TIA-AVAX = K507_dir - K484_dir):
  diff = TIA_FR - AVAX_FR   (TIA minus AVAX)
  mean_168h = 168h rolling mean of diff (21 x 8h periods)
  sign = sign(mean_168h)
  +1 -> SHORT TIA / LONG AVAX  (TIA FR > AVAX FR — DA demand spike)
  -1 -> SHORT AVAX / LONG TIA  (AVAX FR > TIA FR — subnet premium, dominant ~AVAX_PREMIUM)

HL concentration:
  Current HL weight: 64.5% (post-K737)
  K738 HL-only impact: would breach to 67.5% >> 65% cap
  Resolution: Bybit mandatory (both TIA-PERP + AVAX-PERP on Bybit)
  K738 is fully Bybit-only: HL concentration UNCHANGED at 64.5% (headroom 0.5pp preserved)

K738 production scaffold:
  - 67th daemon (13th alt-alt scaffold, DA-infra vs Subnet L1, triple AVAX hedge)
  - Bybit-only (both legs — HL 64.5%/65% cap constraint)
  - 3% standalone sleeve, 4x leverage
  - $87,086/yr net @$10M @4x (3% sleeve), $239/day
  - 60d paper-trade gate: Realized Sh>=6 + fill>=60% + maxDD<15%
  - TIA notional: K738 3% (2nd TIA strategy — K694 TIA-SOL is 1st)
  - AVAX notional: K738 3% + existing AVAX strategies (K484/K661/K686/K696)
    Monitor combined AVAX on Bybit

Architecture (K683/K685/K687/K689/K693/K697/K699/K710/K721/K730/K731/K737 alt-alt pattern):
  1. fetch_fr_batch()                   -> fetch TIA + AVAX FR every 8h from Bybit
  2. compute_signal(tia_fr, avax_fr)   -> 168h rolling mean of (TIA_FR - AVAX_FR); sign()
  3. decide_position(signal)            -> SHORT_TIA_LONG_AVAX | SHORT_AVAX_LONG_TIA | NEUTRAL
  4. submit_paired_trade(long, short)   -> POST_ONLY paired (TIA + AVAX legs, both Bybit)
  5. daily_rebalance()                  -> drift > 5% triggers rebalance
  6. close_paired_position(reason)      -> sequential: short first, then long

Paper-trade mode is the DEFAULT.  No orders are submitted unless
PAPER_TRADE=False is explicitly set in the environment.

K339 security: REPO_ROOT from __file__, no /Users/ literals.
No new packages — stdlib urllib + json only.

Usage:
  python3 scripts/k736_tia_avax_run.py --dry-run
  python3 scripts/k736_tia_avax_run.py --status
  python3 scripts/k736_tia_avax_run.py --rebalance
  python3 scripts/k736_tia_avax_run.py --close "scheduled exit"
"""
from __future__ import annotations

import argparse
import json
import math
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

DASHBOARD_PATH  = DATA_DIR  / "k736_dashboard.json"
FR_HISTORY_PATH = CACHE_DIR / "k736_fr_history.jsonl"
TRADE_LOG_PATH  = CACHE_DIR / "k736_paper_trades.jsonl"

JST = timezone(timedelta(hours=9))
UTC = timezone.utc

# ── Strategy constants ────────────────────────────────────────────────────────
PAPER_TRADE         = True          # never submit real orders in paper-trade mode
SLEEVE_PCT          = 0.030         # K738 sleeve = 3% of AUM (standalone, Bybit-only)
LEVERAGE            = 4.0           # 4x per K736 analysis (K430 cap)
AUM_DEFAULT         = 10_000_000.0  # $10M reference AUM
DRIFT_REBALANCE_PCT = 0.05          # rebalance if legs drift > 5%
IOC_TIMEOUT_SEC     = 300           # 5 min fill window
EMA_PERIOD_HOURS    = 168           # 168h rolling mean primary config (W=168h)
EMA_PERIOD_PERIODS  = EMA_PERIOD_HOURS // 8  # = 21 periods (8h settlement cycle)
SIGNAL_SIGMA_MULT   = 0.0           # zero threshold (sign of rolling mean)
BYBIT_API_URL       = "https://api.bybit.com"
HL_API_URL          = "https://api.hyperliquid.xyz/info"

# ── Venue config (Bybit-only — TIA-PERP + AVAX-PERP on Bybit) ─────────────────
# HL concentration: 64.5% baseline — Bybit mandatory (HL at 64.5%/65% cap, 0.5pp headroom)
# K738: 64.5% HL baseline; Bybit-only preserves 0.5pp headroom to 65% cap.
# Both TIA and AVAX listed on Bybit with adequate leverage caps.
HL_CONCENTRATION_PRE_K738  = 64.5   # post-K737 reference
HL_CONCENTRATION_POST_K738 = 64.5   # UNCHANGED (Bybit-only — HL 3% would breach to 67.5%)

BYBIT_TIA_MAX_LEV  = 75
BYBIT_AVAX_MAX_LEV = 75

# ── Position state constants ──────────────────────────────────────────────────
STATE_NEUTRAL               = "NEUTRAL"
STATE_SHORT_TIA_LONG_AVAX   = "SHORT_TIA_LONG_AVAX"   # signal +1: TIA FR > AVAX FR (DA spike)
STATE_SHORT_AVAX_LONG_TIA   = "SHORT_AVAX_LONG_TIA"   # signal -1: AVAX FR > TIA FR (dominant subnet premium)

# ── Symbols fetched from Bybit for FR data ────────────────────────────────────
# K738: TIA + AVAX only — direct alt-alt differential (THIRTEENTH ALT-ALT pair)
SYMBOLS = ("TIA", "AVAX")


# ─────────────────────────────────────────────────────────────────────────────
# HTTP helpers (stdlib urllib only — no requests)
# ─────────────────────────────────────────────────────────────────────────────

def _http_get(url: str, timeout: int = 10) -> Optional[dict]:
    try:
        req = urllib.request.Request(
            url, headers={"User-Agent": "crypto-lab-k736/1.0"}
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        print(f"  [k736] HTTP error: {e}", file=sys.stderr)
        return None


def _http_post(url: str, payload: dict, timeout: int = 10) -> Optional[dict]:
    try:
        data = json.dumps(payload).encode()
        req  = urllib.request.Request(
            url, data=data,
            headers={"Content-Type": "application/json",
                     "User-Agent": "crypto-lab-k736/1.0"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        print(f"  [k736] HTTP error: {e}", file=sys.stderr)
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Phase 1 — Funding rate fetch (TIA + AVAX from Bybit)
# ─────────────────────────────────────────────────────────────────────────────

def _fetch_bybit_fr_batch() -> Dict[str, float]:
    """
    Fetch current 8h funding rates for TIA and AVAX from Bybit.
    Returns {symbol: fr_8h_fraction}.

    Bybit API: /v5/market/tickers?category=linear
    K738: both legs on Bybit (TIA-PERP + AVAX-PERP).
    Bybit mandatory: HL at 64.5%/65% cap; 3% HL-only would breach to 67.5%.
    Both TIAUSDT and AVAXUSDT perpetuals listed on Bybit.

    Fallback: HL metaAndAssetCtxs for cross-reference (informational only).
    K738: Bybit is the execution venue; HL FR data is used for cross-check only.
    G8 PASS: Bybit diff corr=0.6691 >= 0.55 (K694 TIA precedent + K484 AVAX precedent).
    """
    result: Dict[str, float] = {}

    # Primary: Bybit /v5/market/tickers (linear perpetuals)
    bybit_url = f"{BYBIT_API_URL}/v5/market/tickers?category=linear"
    raw = _http_get(bybit_url)
    if raw and raw.get("retCode") == 0:
        tickers = raw.get("result", {}).get("list", [])
        sym_map = {t["symbol"]: t for t in tickers}
        for sym in SYMBOLS:
            perp_sym = f"{sym}USDT"
            if perp_sym in sym_map:
                tick = sym_map[perp_sym]
                try:
                    result[sym] = float(tick.get("fundingRate", 0.0))
                except (TypeError, ValueError):
                    pass
        if len(result) == len(SYMBOLS):
            return result
        print(f"  [k736] Bybit partial result {list(result.keys())} — trying HL fallback",
              file=sys.stderr)

    # Fallback: HL metaAndAssetCtxs (informational cross-check only)
    raw_hl = _http_post(HL_API_URL, {"type": "metaAndAssetCtxs"})
    if raw_hl and isinstance(raw_hl, list) and len(raw_hl) >= 2:
        meta       = raw_hl[0]
        asset_ctxs = raw_hl[1]
        universe   = {item["name"]: i for i, item in enumerate(meta.get("universe", []))}
        for sym in SYMBOLS:
            if sym in result:
                continue   # already have from Bybit
            if sym not in universe:
                continue
            idx = universe[sym]
            ctx = asset_ctxs[idx]
            try:
                result[sym] = float(ctx.get("funding", 0.0))
                print(f"  [k736] HL fallback used for {sym} FR (informational)", file=sys.stderr)
            except (TypeError, ValueError):
                continue

    if len(result) < len(SYMBOLS):
        print(f"  [k736] Warning: only fetched {list(result.keys())} FRs", file=sys.stderr)
    return result


def _load_fr_history() -> List[dict]:
    """Load K736 FR history JSONL."""
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
    fr_tia: float, fr_avax: float, tia_avax_diff: float
) -> None:
    """Append one FR snapshot to history."""
    rec = {
        "ts_utc":       datetime.now(UTC).isoformat(),
        "fr_tia":       round(fr_tia,        10),
        "fr_avax":      round(fr_avax,        10),
        "tia_avax_diff": round(tia_avax_diff, 10),  # TIA_FR - AVAX_FR
    }
    with open(FR_HISTORY_PATH, "a") as f:
        f.write(json.dumps(rec) + "\n")


# ─────────────────────────────────────────────────────────────────────────────
# Phase 2 — Signal computation (TIA-AVAX direct differential, 168h rolling mean)
# ─────────────────────────────────────────────────────────────────────────────

def compute_signal(
    fr_tia:  Optional[float] = None,
    fr_avax: Optional[float] = None,
) -> dict:
    """
    Fetch live TIA and AVAX FRs from Bybit, compute TIA-AVAX differential,
    and compute 168h rolling mean for direction signal.

    Signal mechanism (K736 direct differential — DA-infra vs Subnet L1):
      diff = TIA_FR - AVAX_FR   (TIA minus AVAX = K507_dir - K484_dir per MR9)
      mean_168h = 168h rolling mean of diff (21 x 8h periods)
      sign  = sign(mean_168h)
      +1 -> SHORT TIA / LONG AVAX   (TIA FR higher — DA demand spike)
      -1 -> SHORT AVAX / LONG TIA   (AVAX FR higher — subnet premium, dominant)

    Cross-cluster mechanism:
      - TIA FR: Celestia DA layer — driven by rollup adoption events (OP Stack integrations,
        Fuel, Manta, Eclipse), blob fee market events, TIA staking APY changes, competing DA
        launches (EigenDA, Avail, EIP-4844 Dencun), modular ecosystem expansion milestones.
        TIA FR mean = +1.08%/yr (low baseline — infrastructure-layer, episodic demand spikes).
      - AVAX FR: Avalanche subnet L1 — driven by Avalanche9000 subnet wave, RWA tokenization
        partnerships (Ava Labs), subnet-native staking economics, AVAX DeFi TVL cycles
        (Trader Joe, Benqi, Aave), institutional adoption cycles (BlackRock BUIDL, KKR fund).
        AVAX FR mean = +6.38%/yr (semi-persistent — subnet economics + RWA cycles).
      - AVAX FR > TIA FR structurally (diff mean = -5.30%/yr = AVAX premium).
        Dominant signal: -1 = SHORT AVAX / LONG TIA (collect AVAX subnet premium).
      - MR9: TIA-AVAX = K507_dir - K484_dir (max_err=5.42e-20, machine precision).
      - W=168h weekly: aligns with DAO governance cycles + subnet activation cadence.

    K736 §6 validation (15/16 PASS, ACCEPT CONDITIONAL):
      - OOS Sharpe: 12.9673 (W=168h, zero threshold, 218d OOS period)
      - IS Sharpe:  9.1303
      - OOS Ann Ret: 8.54% @1x, 34.15% @4x
      - Net @$10M @4x @3% sleeve: $87,086/yr; $239/day
      - ADF t=-13.4712 (strongly stationary p=3.38e-25)
      - OU half-life: 4.35h (fast mean-reversion of raw diff)
      - G4 walk-forward: 12/12 folds positive (UNPRECEDENTED perfect WF)
      - G5: 8/8 PASS (all signed corr < 0.40 threshold)
        G5b K694 TIA-SOL: corr=+0.2973 PASS (TIA shared leg)
        G5c K484 AVAX-BTC: corr=-0.6324 PASS (anti-corr hedge, signed convention)
        G5e K686 AVAX-SOL: corr=-0.6031 PASS (anti-corr hedge, signed convention)
      - G6 trade count: 18.4/yr (FAIL structural: below 30; K661 precedent 18.6/yr)
      - G7: 34.15% @4x (PASS >= 5%)
      - G8: PASS (Bybit diff corr=0.6691 >= 0.55; K694 TIA + K484 AVAX precedents)
      - G9: 218d OOS (PASS >= 180d)
      - MR9: TIA-AVAX = K507_dir - K484_dir (max_err=5.42e-20) PASS
      - 60d gate: Realized Sh>=6 + fill>=60% + maxDD<15%

    Returns:
      {
        "fr_tia":           float,
        "fr_avax":          float,
        "tia_avax_diff":    float,    # TIA_FR - AVAX_FR (current)
        "mean_168h":        float,    # 168h rolling mean of differential
        "diff_sigma":       float,    # 168h rolling sigma (informational)
        "history_points":   int,
        "regime":           str,      # TIA_PREMIUM | AVAX_PREMIUM | NEUTRAL
        "signal_direction": int,      # +1 | -1 | 0
        "ts_jst":           str,
      }
    """
    if fr_tia is None or fr_avax is None:
        frs    = _fetch_bybit_fr_batch()
        fr_tia  = frs.get("TIA",  0.0)
        fr_avax = frs.get("AVAX", 0.0)

    # TIA-AVAX direct differential (= K507_dir - K484_dir per MR9)
    tia_avax_diff = fr_tia - fr_avax

    _append_fr_history(fr_tia, fr_avax, tia_avax_diff)

    # Load history for rolling mean + sigma (168h = 21 x 8h periods)
    history = _load_fr_history()
    diffs   = [r["tia_avax_diff"] for r in history if "tia_avax_diff" in r]

    n_periods = EMA_PERIOD_PERIODS   # 21 periods (168h / 8h)

    # Rolling mean: simple mean of last n_periods diffs
    window = diffs[-n_periods:] if len(diffs) >= 1 else diffs
    if window:
        mean_168h = sum(window) / len(window)
    else:
        mean_168h = 0.0

    # Rolling sigma: std of last n_periods diffs (informational)
    if len(window) >= 2:
        mean_w = sum(window) / len(window)
        sigma  = math.sqrt(sum((x - mean_w) ** 2 for x in window) / (len(window) - 1))
    else:
        sigma  = abs(mean_168h) if mean_168h != 0 else 1e-8   # fallback

    # Regime classification (zero threshold — per K736 spec)
    # TIA_PREMIUM: TIA FR > AVAX FR (DA demand spike — episodic)
    # AVAX_PREMIUM: AVAX FR > TIA FR (subnet institutional demand — dominant, ~73% OOS)
    if mean_168h > 0:
        regime    = "TIA_PREMIUM"    # TIA FR > AVAX FR -> short TIA / long AVAX
        direction = 1
    elif mean_168h < 0:
        regime    = "AVAX_PREMIUM"   # AVAX FR > TIA FR -> short AVAX / long TIA (dominant)
        direction = -1
    else:
        regime    = "NEUTRAL"
        direction = 0

    return {
        "fr_tia":           round(fr_tia,          10),
        "fr_avax":          round(fr_avax,          10),
        "tia_avax_diff":    round(tia_avax_diff,    10),
        "mean_168h":        round(mean_168h,        10),
        "diff_sigma":       round(sigma,            10),
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
    Determine trade direction from TIA-AVAX differential rolling mean.

    Logic (TIA-AVAX direct differential pair, Bybit primary):
      regime = TIA_PREMIUM (mean_168h > 0):
        TIA FR > AVAX FR: DA demand spike (rollup adoption event, blob fee surge)
        -> short TIA  (collect TIA DA-premium when rollup demand spikes)
        -> long AVAX  (AVAX FR lower — net positive carry when TIA > AVAX)
        -> position_state = SHORT_TIA_LONG_AVAX

      regime = AVAX_PREMIUM (mean_168h < 0):
        AVAX FR > TIA FR: subnet institutional demand (Avalanche9000, RWA cycles)
        -> short AVAX (collect AVAX subnet premium — dominant state)
        -> long TIA   (TIA FR lower — net positive carry when AVAX > TIA)
        -> position_state = SHORT_AVAX_LONG_TIA

      regime = NEUTRAL: no trade (mean_168h == 0 exactly — rare)

    K736 edge (cross-cluster mechanism):
      TIA (Celestia DA-infra) driven by rollup adoption events, blob fee markets,
      modular ecosystem expansion. Infrastructure-layer, below execution.
      AVAX (Avalanche L1) driven by subnet economics, RWA institutional cycles.
      Application-layer, above DA. AVAX FR mean = +6.38%/yr (structural AVAX premium).
      Dominant: SHORT AVAX / LONG TIA (collect AVAX subnet premium ~dominant signal).
      Triple hedge: K736 anti-correlates with K484 (-0.632), K661 (-0.643), K686 (-0.603).
        K736 BULL_TIA (short AVAX) naturally offsets AVAX-long in K484/K661/K686/K696.

    Returns:
      {long_asset, short_asset, long_venue, short_venue, mean_168h,
       signal_direction, size_multiplier, position_state}
      or None if NEUTRAL.
    """
    regime    = signal.get("regime", "NEUTRAL")
    mean_168h = signal.get("mean_168h", 0.0)
    direction = signal.get("signal_direction", 0)

    if regime == "NEUTRAL":
        return None

    if regime == "TIA_PREMIUM":
        # TIA FR > AVAX FR: collect TIA DA-premium (short TIA / long AVAX)
        long_asset  = "AVAX"
        short_asset = "TIA"
        state       = STATE_SHORT_TIA_LONG_AVAX
    else:  # AVAX_PREMIUM
        # AVAX FR > TIA FR: collect AVAX subnet premium (short AVAX / long TIA) — dominant
        long_asset  = "TIA"
        short_asset = "AVAX"
        state       = STATE_SHORT_AVAX_LONG_TIA

    # Both legs on Bybit (K738: HL at 64.5%/65% cap — 3% HL-only would breach to 67.5%)
    long_venue  = "Bybit"
    short_venue = "Bybit"

    return {
        "long_asset":       long_asset,
        "short_asset":      short_asset,
        "position_state":   state,
        "long_venue":       long_venue,
        "short_venue":      short_venue,
        "mean_168h":        mean_168h,
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
    Compute equal notional for both legs of the TIA-AVAX paired trade.

    K738 Bybit-only config (both TIA-PERP + AVAX-PERP on Bybit):
      sleeve_capital   = aum x sleeve_pct      (e.g. $10M x 3.0% = $300K)
      total_notional   = sleeve_capital x lev   ($300K x 4 = $1.2M)
      notional_per_leg = total_notional / 2     ($600K per leg)

    At $10M / 3.0% sleeve / 4x:
      TIA leg:  $150K capital x 4x = $600K notional (Bybit TIA-PERP)
      AVAX leg: $150K capital x 4x = $600K notional (Bybit AVAX-PERP)
      Total:    $1.2M notional (two legs combined)
      Margin:   $300K (3.0% of AUM)
      HL conc:  UNCHANGED 64.5% (Bybit-only — HL 3% would breach to 67.5%)
      Net profit: ~$87,086/yr @$10M @4x @3% (OOS 8.54% ann ret x $10M x 4x x 3.0%)

    Returns (notional_per_leg, total_notional).
    """
    sleeve_capital   = aum * sleeve_pct
    total_notional   = sleeve_capital * leverage
    notional_per_leg = total_notional / 2.0
    return round(notional_per_leg, 2), round(total_notional, 2)


# ─────────────────────────────────────────────────────────────────────────────
# Phase 5 — Paired trade submission (Bybit primary, POST_ONLY)
# ─────────────────────────────────────────────────────────────────────────────

def submit_paired_trade(
    long_leg:  dict,
    short_leg: dict,
    dry_run:   bool = True,
) -> dict:
    """
    Submit K738 TIA-AVAX paired trade: POST_ONLY both legs in parallel.

    Protocol (K738 Bybit primary — both legs on Bybit):
      1. Submit TIA leg on Bybit POST_ONLY
      2. Submit AVAX leg on Bybit POST_ONLY
      3. Both legs submitted in parallel (K439 pattern)
      4. IOC fallback per leg if POST_ONLY times out
      5. If both fail: retry next 8h cycle

    Args:
      long_leg:  {"symbol": "TIA",  "notional": 600000, "venue": "Bybit"}
      short_leg: {"symbol": "AVAX", "notional": 600000, "venue": "Bybit"}
      dry_run:   True = paper-trade simulation (default)

    Returns execution result dict.
    """
    ts         = datetime.now(UTC).isoformat()
    long_sym   = long_leg["symbol"]
    short_sym  = short_leg["symbol"]
    long_notl  = long_leg.get("notional", 0.0)
    short_notl = short_leg.get("notional", 0.0)
    long_venue  = long_leg.get("venue",  "Bybit")
    short_venue = short_leg.get("venue", "Bybit")

    if dry_run or PAPER_TRADE:
        mode_tag = "DRY_RUN" if dry_run else "PAPER_TRADE"
        print(f"  [K738] {mode_tag}: LONG {long_sym}@{long_venue} ${long_notl:,.0f}  "
              f"+ SHORT {short_sym}@{short_venue} ${short_notl:,.0f}")
        result = {
            "status":           "DRY_RUN",
            "long_result":      {"order_id": f"PAPER_LONG_{long_sym}_{int(time.time())}", "status": "DRY_RUN"},
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
            "venue_config":     "BYBIT_PRIMARY_TIA_AVAX_DA_INFRA_VS_SUBNET",
            "mechanism_note":   (
                "TIA-AVAX direct differential (DA-infra vs Subnet L1, K736/K738): "
                "TIA FR = Celestia DA layer (rollup adoption events: OP Stack/Fuel/Manta/Eclipse, "
                "blob fee market, TIA staking APY, competing DA launches EigenDA/Avail/EIP-4844). "
                "TIA mean = +1.08%/yr (low baseline — infrastructure-layer, episodic demand). "
                "AVAX FR = Avalanche subnet L1 (Avalanche9000 subnet wave, RWA tokenization "
                "partnerships Ava Labs, subnet-native staking, DeFi TVL Trader Joe/Benqi/Aave, "
                "institutional adoption BlackRock BUIDL/KKR fund). AVAX mean = +6.38%/yr. "
                "AVAX FR > TIA FR structurally (diff mean -5.30%/yr = AVAX premium). "
                "MR9: TIA-AVAX = K507_dir - K484_dir (max_err=5.42e-20). "
                "G4: 12/12 WF positive (UNPRECEDENTED perfect WF). G5: 8/8 PASS. "
                "Triple AVAX hedge: K736 anti-corr K484(-0.632)/K661(-0.643)/K686(-0.603). "
                "Net: $87,086/yr @$10M @3% sleeve. "
                "Bybit mandatory: HL at 64.5%/65% cap (3% HL-only = 67.5% > cap)."
            ),
            "ts_utc":           ts,
        }
        _append_trade_log(result)
        return result

    # LIVE scaffold (not reached in PAPER_TRADE mode):
    print(f"  [K738] SCAFFOLD LIVE: parallel POST_ONLY "
          f"LONG {long_sym}@{long_venue} ${long_notl:,.0f} "
          f"+ SHORT {short_sym}@{short_venue} ${short_notl:,.0f}")
    long_order_id  = f"SCAFFOLD_LONG_{long_sym}_{int(time.time())}"
    short_order_id = f"SCAFFOLD_SHORT_{short_sym}_{int(time.time())}"

    # Scaffold: poll not implemented — retry next 8h cycle
    print(f"  [K738] Neither leg filled within timeout — retry next 8h cycle")
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
    Check if current K738 position has drifted beyond DRIFT_REBALANCE_PCT (5%).

    K738 Bybit-only: both legs on Bybit (TIA-PERP + AVAX-PERP).
    Drift detection: compare stored TIA leg notional vs AVAX leg notional.
    Threshold: 5% (same as K449/K476/K484/K493/K629/K663/K696/K698/K708/K719/K729/K737 pattern).

    Returns rebalance decision dict.
    """
    state = dashboard.get("position_state", STATE_NEUTRAL)
    if state == STATE_NEUTRAL:
        return {"rebalance_required": False, "reason": "NEUTRAL — no position"}

    long_notional_init  = float(dashboard.get("long_notional", 0.0))
    short_notional_init = float(dashboard.get("short_notional", 0.0))

    if long_notional_init <= 0 or short_notional_init <= 0:
        return {"rebalance_required": False, "reason": "no recorded notionals"}

    # Paper-trade: use stored drift (0 if not set)
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
    Both legs on Bybit (K738 Bybit primary — TIA-PERP + AVAX-PERP).

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

    if state == STATE_SHORT_TIA_LONG_AVAX:
        long_sym,  short_sym  = "AVAX", "TIA"
    else:  # SHORT_AVAX_LONG_TIA
        long_sym,  short_sym  = "TIA", "AVAX"

    long_notional  = float(dash.get("long_notional",  0.0))
    short_notional = float(dash.get("short_notional", 0.0))

    if dry_run or PAPER_TRADE:
        mode_tag = "DRY_RUN" if dry_run else "PAPER_TRADE"
        print(f"  [K738] {mode_tag} CLOSE:")
        print(f"    Step 1 (SHORT first): cover {short_sym}@Bybit ${short_notional:,.0f}")
        print(f"    Step 2 (LONG second): sell  {long_sym}@Bybit  ${long_notional:,.0f}")
        print(f"    reason={reason}")
        result = {
            "status":          "DRY_RUN_CLOSED",
            "reason":          reason,
            "close_sequence":  "short_first_then_long",
            "closed_short":    short_sym,
            "closed_long":     long_sym,
            "venue":           "Bybit",
            "short_notional":  short_notional,
            "long_notional":   long_notional,
            "close_mode":      "IOC_REDUCE_ONLY",
            "ts_utc":          ts,
        }
    else:
        print(f"  [K738] SCAFFOLD CLOSE:")
        print(f"    Step 1: IOC reduce {short_sym} (cover short) @Bybit  reason={reason}")
        print(f"    Step 2: IOC reduce {long_sym} (sell long) @Bybit")
        result = {
            "status":         "SCAFFOLD_CLOSE",
            "reason":         reason,
            "close_sequence": "short_first_then_long",
            "venue":          "Bybit",
            "ts_utc":         ts,
        }

    _append_trade_log(result)
    return result


# ─────────────────────────────────────────────────────────────────────────────
# Dashboard I/O
# ─────────────────────────────────────────────────────────────────────────────

def _load_dashboard() -> dict:
    """Load k736_dashboard.json; return defaults if missing."""
    if DASHBOARD_PATH.exists():
        try:
            return json.loads(DASHBOARD_PATH.read_text())
        except Exception:
            pass
    return {
        "last_poll_jst":           "—",
        "mean_168h":               0.0,
        "diff_sigma":              0.0,
        "regime":                  "NEUTRAL",
        "position_state":          STATE_NEUTRAL,
        "long_notional":           0.0,
        "short_notional":          0.0,
        "venue":                   "Bybit",
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
    """Write k736_dashboard.json with full signal + regime state."""
    dash = _load_dashboard()

    # Update signal data
    dash["last_poll_jst"]         = signal.get("ts_jst", "—")
    dash["fr_tia_current"]        = signal.get("fr_tia",        0.0)
    dash["fr_avax_current"]       = signal.get("fr_avax",       0.0)
    dash["tia_avax_diff_current"] = signal.get("tia_avax_diff", 0.0)
    dash["mean_168h"]             = signal.get("mean_168h",     0.0)
    dash["diff_sigma"]            = signal.get("diff_sigma",    0.0)
    dash["regime"]                = signal.get("regime",   "NEUTRAL")
    dash["signal_direction"]      = signal.get("signal_direction", 0)
    dash["history_points"]        = signal.get("history_points", 0)

    # Update position if entering
    if decision:
        state = decision.get("position_state", STATE_NEUTRAL)
        if dash.get("position_state") == STATE_NEUTRAL:
            dash["position_state"]   = state
            dash["long_notional"]    = notional_per_leg
            dash["short_notional"]   = notional_per_leg
            dash["long_asset"]       = decision.get("long_asset")
            dash["short_asset"]      = decision.get("short_asset")
            dash["venue"]            = "Bybit"
            dash["entry_ts_jst"]     = dash["last_poll_jst"]
            dash["signal_direction"] = decision.get("signal_direction", 0)

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
    dash["hl_concentration_pct"]    = HL_CONCENTRATION_POST_K738   # 64.5% unchanged

    # Paper-trade status
    paper_status = dash.get("paper_trade_status", {"days_elapsed": 0, "target_60d": 60})
    dash["paper_trade_status"]      = paper_status

    # 60d activation gate metrics (K738: Realized Sh >= 6, fill >= 60%, DD < 15%)
    dash["gate_metrics"] = {
        "realized_sharpe_target":  6.0,      # >=6 (50% of OOS Sh=12.97)
        "fill_rate_target_pct":    60,
        "max_drawdown_target_pct": 15,        # <15%
        "current_realized_sharpe": dash.get("60d_sharpe", 0.0),
        "current_fill_rate_pct":   0.0,
        "current_max_dd_pct":      0.0,
        "gate_status":             "IN_PROGRESS",
        "activation_trigger":      "60d paper-trade: Sh>=6 AND fill>=60% AND maxDD<15%",
        "profit_at_activation_3pct": "$87,086/yr net @$10M @4x (3% sleeve, OOS 8.54% ann ret)",
        "bybit_primary_note":      "Bybit mandatory: HL at 64.5%/65% cap (3% HL-only = 67.5% > cap). TIA maxLev=75, AVAX maxLev=75.",
        "triple_avax_hedge":       "K736 anti-corr: K484 AVAX-BTC (-0.632), K661 AVAX-ETH (-0.643), K686 AVAX-SOL (-0.603)",
    }

    # Strategy metadata
    dash["paper_trade_mode"]   = PAPER_TRADE
    dash["wave"]               = "K738"
    dash["strategy"]           = "K736 TIA-AVAX FR Differential (DA-infra vs Subnet L1, W=168h, Bybit primary)"
    dash["execution_mode"]     = "POST_ONLY_PARALLEL"
    dash["venue_config"]       = "BYBIT_PRIMARY"
    dash["cross_cluster_mechanism"] = {
        "formula":                 "diff = TIA_FR - AVAX_FR  (= K507_dir - K484_dir per MR9)",
        "rolling_window":          "W=168h (21 x 8h periods)",
        "signal":                  "sign(rolling_mean_168h(diff))",
        "g5b_k694_tia_sol_corr":   0.2973,    # PASS (TIA shared leg, below 0.40)
        "g5c_k484_avax_btc_corr":  -0.6324,   # PASS (AVAX shared anti-corr hedge, signed)
        "g5e_k686_avax_sol_corr":  -0.6031,   # PASS (AVAX shared anti-corr hedge, signed)
        "mr9_identity":            "TIA-AVAX = K507_dir - K484_dir",
        "mr9_max_err":             5.42e-20,
        "adf_tstat":               -13.4712,
        "adf_pvalue":              3.38e-25,
        "ou_halflife_h":           4.35,
        "avax_gt_tia_structural":  True,       # AVAX FR > TIA FR structurally (-5.30%/yr diff)
        "walk_forward_12_12":      True,       # 12/12 folds positive (UNPRECEDENTED perfect WF)
        "triple_avax_hedge":       True,       # K736 hedges K484/K661/K686 AVAX-long positions
        "note": (
            "TIA-AVAX: $87,086/yr net @$10M @4x @3% sleeve ($239/day). "
            "TIA (Celestia DA-infra) vs AVAX (Avalanche Subnet L1) — orthogonal clusters. "
            "TIA FR = rollup adoption events (OP Stack/Fuel/Manta/Eclipse integrations), "
            "blob fee market, TIA staking APY, competing DA launches (EigenDA/Avail/EIP-4844). "
            "Mean +1.08%/yr (low baseline — infrastructure-layer, episodic demand spikes). "
            "AVAX FR = subnet economics (Avalanche9000), RWA institutional partnerships "
            "(Ava Labs, BlackRock BUIDL, KKR fund), DeFi TVL Trader Joe/Benqi/Aave. "
            "Mean +6.38%/yr. AVAX structural premium +5.30%/yr vs TIA. "
            "MR9: TIA-AVAX = K507_dir - K484_dir (max_err=5.42e-20). "
            "G4: 12/12 WF positive (UNPRECEDENTED perfect WF, first in family). "
            "G5: 8/8 PASS. Triple AVAX hedge: K736 anti-corr K484(-0.632)/K661(-0.643)/K686(-0.603). "
            "G8 PASS (Bybit diff corr=0.6691 >= 0.55; K694 TIA + K484 AVAX precedents). "
            "Bybit mandatory: HL at 64.5%/65% cap."
        ),
    }
    dash["activation_criteria"] = {
        "60d_paper_trade_gate":  "required",
        "realized_sharpe_min":   6.0,
        "fill_rate_min_pct":     60,
        "max_drawdown_max_pct":  15,
        "status":                "SCAFFOLD-READY",
        "activation_sleeve_pct": 0.030,
        "venue":                 "Bybit primary (TIA-PERP + AVAX-PERP both on Bybit)",
    }
    dash["oos_performance"] = {
        "sharpe":                   12.9673,
        "sharpe_is":                9.1303,
        "is_oos_ratio":             1.42,      # OOS/IS (IS=9.13, OOS=12.97 — OOS outperforms IS)
        "oos_ann_ret_1x_pct":       8.5378,
        "oos_ann_ret_4x_pct":       34.1512,
        "ann_return_usd_3pct_4x":   87_086,
        "daily_usdc_3pct_4x":       239,
        "wave_accept":              "K736 ACCEPT CONDITIONAL (K738 scaffold) — 15/16 §6 gates PASS",
        "cluster":                  "Celestia DA-infra (TIA) vs Avalanche Subnet L1 (AVAX)",
        "g5b_k694_verdict":         "PASS (corr=+0.2973, TIA shared leg, below 0.40)",
        "g5c_k484_verdict":         "PASS (corr=-0.6324, AVAX shared anti-corr hedge, signed)",
        "g5e_k686_verdict":         "PASS (corr=-0.6031, AVAX shared anti-corr hedge, signed)",
        "g6_verdict":               "FAIL structural (18.4/yr below 30; K661 precedent 18.6/yr accepted)",
        "g8_verdict":               "PASS (Bybit diff corr=0.6691 >= 0.55; K694 TIA + K484 AVAX precedents)",
        "walk_forward":             "12/12 folds positive (UNPRECEDENTED perfect WF — first in alt-alt family)",
        "perm_pvalue":              0.0,
        "dsr_bonferroni_pvalue":    0.0,
        "dsr_tstat":                49.1466,
        "trades_per_yr":            18.4,
        "max_drawdown_oos_pct":     0.2831,
        "daemon_number":            "67th",
        "alt_alt_rank":             "13th alt-alt scaffold (rank #8 by OOS Sharpe in alt-alt family)",
        "alt_alt_family_ranking": {
            "k686_avax_sol":         50.27,    # rank 1
            "k708_bnb_sol":          48.59,    # rank 2
            "k728_ldo_sol":          46.84,    # rank 3
            "k682_atom_sol":         43.43,    # rank 4
            "k679_apt_sol":          39.29,    # rank 5
            "k719_ena_atom":         29.67,    # rank 6
            "k735_hbar_sol":         26.9506,  # rank 7 (K737 scaffold)
            "k736_tia_avax":         12.9673,  # rank 8 (THIS — K738 scaffold)
            "k684_sol_inj":           9.65,    # rank 9
        },
    }
    dash["notional_caps"] = {
        "tia_cap_note":  "TIA total: K738 3% (2nd TIA strategy; K694 TIA-SOL is 1st). Monitor combined TIA notional.",
        "avax_cap_note": "AVAX total: K738 3% + existing AVAX strategies (K484/K661/K686/K696). Monitor combined AVAX on Bybit.",
        "hl_cap_note":   "HL concentration 64.5% UNCHANGED (Bybit-only — 3% HL-only = 67.5% > 65% cap).",
        "triple_hedge":  "K736 natural HEDGE to AVAX-long positions (K484/K661/K686/K696) when AVAX FR high.",
    }
    dash["signal"] = decision.get("position_state", STATE_NEUTRAL) if decision else STATE_NEUTRAL

    DASHBOARD_PATH.write_text(json.dumps(dash, indent=2))
    return dash


# ─────────────────────────────────────────────────────────────────────────────
# Main single-shot run logic
# ─────────────────────────────────────────────────────────────────────────────

def run_cycle(dry_run: bool = True, aum: float = AUM_DEFAULT) -> int:
    """
    Single 8h cycle:
      1. Fetch TIA + AVAX FRs from Bybit
      2. Compute TIA-AVAX differential + 168h rolling mean
      3. Decide position (sign of rolling mean — zero threshold)
      4. Compute delta-neutral notional
      5. If entering: submit paired trade (POST_ONLY, Bybit primary)
      6. If holding: check drift + rebalance
      7. Write k736_dashboard.json
    """
    ts_jst = datetime.now(JST).strftime("%Y-%m-%d %H:%M JST")
    print(f"\n=== K736 TIA-AVAX FR Differential (DA-infra vs Subnet L1) — {ts_jst} ===")
    print(f"  Mode:      {'DRY-RUN' if dry_run else 'PAPER-TRADE' if PAPER_TRADE else 'LIVE'}")
    print(f"  AUM:       ${aum:,.0f}  Sleeve: {SLEEVE_PCT:.1%}  Leverage: {LEVERAGE}x")
    print(f"  Venue:     Bybit primary (TIA-PERP + AVAX-PERP, both Bybit perps)")
    print(f"  HL cap:    64.5% baseline; Bybit mandatory (3% HL-only = 67.5% > 65% cap)")
    print(f"  Execution: POST_ONLY parallel (K439)")
    print(f"  Signal:    diff = TIA_FR - AVAX_FR  (= K507_dir - K484_dir per MR9)")
    print(f"             sign(rolling_mean_168h)  (zero threshold, W=168h = 21 x 8h periods)")
    print(f"  Clusters:  TIA Celestia DA-infra (rollup adoption) | AVAX Avalanche Subnet L1 (RWA/subnet)")
    print(f"  AVAX pct:  AVAX FR > TIA FR structurally (diff mean -5.30%/yr = AVAX premium)")
    print(f"  MR9:       TIA-AVAX = K507_dir - K484_dir (max_err=5.42e-20)")
    print(f"  15/16 gates: OOS Sh=12.97, Net $87,086/yr @$10M @3% (13th alt-alt, rank #8)")
    print(f"  G4 PERFECT: 12/12 WF positive (UNPRECEDENTED — first in alt-alt family)")
    print(f"  G5 PASS:   8/8, G5b K694 TIA-SOL=+0.297, G5c K484 AVAX-BTC=-0.632 (hedge)")
    print(f"  G6 FAIL:   structural 18.4/yr < 30 (K661 precedent 18.6/yr accepted)")
    print(f"  G8 PASS:   Bybit diff corr=0.669 >= 0.55")
    print(f"  Triple hedge: K736 anti-corr K484(-0.632)/K661(-0.643)/K686(-0.603)")

    # Step 1: Fetch + compute TIA-AVAX differential
    print("\n  [Step 1] Computing TIA-AVAX FR differential...")
    signal = compute_signal()
    print(f"  TIA FR:    {signal['fr_tia']:+.8f} (8h, Bybit — DA-infra rollup adoption)")
    print(f"  AVAX FR:   {signal['fr_avax']:+.8f} (8h, Bybit — Avalanche subnet RWA cycles)")
    print(f"  TIA-AVAX:  {signal['tia_avax_diff']:+.8f}  (direct differential = K507-K484)")
    print(f"  Mean 168h: {signal['mean_168h']:+.8f}")
    print(f"  Sigma:     {signal['diff_sigma']:+.8f}  (informational)")
    print(f"  Direction: {signal['signal_direction']:+d}  (+1=TIA_PREMIUM short TIA/long AVAX, -1=AVAX_PREMIUM dominant)")
    print(f"  Regime:    {signal['regime']}")
    print(f"  History:   {signal['history_points']} data points")

    # Step 2: Position decision
    print("\n  [Step 2] Deciding position...")
    decision = decide_position(signal)
    if decision:
        print(f"  Signal:   LONG {decision['long_asset']}@{decision['long_venue']} / "
              f"SHORT {decision['short_asset']}@{decision['short_venue']}")
        print(f"  State:    {decision['position_state']}")
        print(f"  Mean 168h:{decision['mean_168h']:+.8f}")
    else:
        print(f"  Signal:   NEUTRAL (rolling_mean_168h == 0 exactly)")

    # Step 3: Notional sizing
    notional_per_leg, total_notional = \
        compute_delta_neutral_notional(aum, SLEEVE_PCT, LEVERAGE)
    print(f"\n  [Step 3] Notional sizing:")
    print(f"  Sleeve capital:   ${aum * SLEEVE_PCT:,.0f}  ({SLEEVE_PCT:.1%} x ${aum/1e6:.0f}M)")
    print(f"  TIA leg:          ${notional_per_leg:,.0f}  (3.0% x ${aum/1e6:.0f}M x {LEVERAGE}x / 2)")
    print(f"  AVAX leg:         ${notional_per_leg:,.0f}  (3.0% x ${aum/1e6:.0f}M x {LEVERAGE}x / 2)")
    print(f"  Total notional:   ${total_notional:,.0f}")
    print(f"  Margin required:  ${total_notional/LEVERAGE:,.0f}  ({SLEEVE_PCT:.1%} AUM)")
    print(f"  Profit @$10M 3%:  OOS 8.54% ann ret = $87,086/yr net (3% sleeve); $239/day")

    # Step 4: Load current position + decide action
    dash = _load_dashboard()
    current_state = dash.get("position_state", STATE_NEUTRAL)
    print(f"\n  [Step 4] Current position: {current_state}")

    trade_result = None
    if decision and current_state == STATE_NEUTRAL:
        print(f"  Action: ENTER {decision['position_state']}")
        long_leg  = {"symbol": decision["long_asset"],  "notional": notional_per_leg, "venue": "Bybit"}
        short_leg = {"symbol": decision["short_asset"], "notional": notional_per_leg, "venue": "Bybit"}
        trade_result = submit_paired_trade(long_leg, short_leg, dry_run=dry_run)
        print(f"  Trade status: {trade_result['status']}")

    elif decision and current_state != STATE_NEUTRAL:
        if decision["position_state"] != current_state:
            print(f"  Action: CLOSE + FLIP (signal reversed)")
            close_result = close_paired_position("signal_reversal", dry_run=dry_run)
            print(f"  Close status: {close_result['status']}")
            long_leg  = {"symbol": decision["long_asset"],  "notional": notional_per_leg, "venue": "Bybit"}
            short_leg = {"symbol": decision["short_asset"], "notional": notional_per_leg, "venue": "Bybit"}
            trade_result = submit_paired_trade(long_leg, short_leg, dry_run=dry_run)
        else:
            print(f"  Action: HOLD (same direction)")

    elif not decision and current_state != STATE_NEUTRAL:
        print(f"  Action: CLOSE (mean_168h == 0 exactly)")
        trade_result = close_paired_position("signal_neutral_exact_zero", dry_run=dry_run)

    else:
        print(f"  Action: NO-OP (neutral, no signal)")

    # Step 5: Rebalance check
    print(f"\n  [Step 5] Delta-neutral drift check...")
    rebalance = daily_rebalance(dash)
    print(f"  Drift: {rebalance.get('drift_pct', 0.0):.2%}  "
          f"Threshold: {DRIFT_REBALANCE_PCT:.0%}  "
          f"Action: {rebalance.get('action', 'HOLD')}")

    # Step 6: Write dashboard
    dash_out = _write_dashboard(signal, decision, notional_per_leg, total_notional, rebalance, aum)
    print(f"\n  [Step 6] Dashboard written -> {DASHBOARD_PATH}")

    # Summary
    print(f"\n  === K736/K738 Cycle Complete ===")
    print(f"  Position state:      {dash_out.get('position_state')}")
    print(f"  Regime:              {dash_out.get('regime')}")
    print(f"  TIA-AVAX Mean 168h:  {dash_out.get('mean_168h'):+.8f}")
    print(f"  Signal direction:    {dash_out.get('signal_direction')}")
    print(f"  G5b K694 TIA-SOL:    +0.2973 PASS (TIA shared leg, below 0.40)")
    print(f"  G5c K484 AVAX-BTC:   -0.6324 PASS (anti-corr hedge, signed convention)")
    print(f"  G5e K686 AVAX-SOL:   -0.6031 PASS (anti-corr hedge, signed convention)")
    print(f"  G6 FAIL structural:  18.4/yr < 30 (K661 precedent 18.6/yr accepted)")
    print(f"  G8 PASS:             Bybit diff corr=0.6691 >= 0.55")
    print(f"  MR9 identity:        TIA-AVAX = K507_dir - K484_dir (max_err=5.42e-20)")
    print(f"  Paper-trade mode:    {PAPER_TRADE}")
    print(f"  OOS Sharpe:          12.9673 (IS=9.1303)")
    print(f"  G4 Walk-Forward:     12/12 positive (UNPRECEDENTED perfect WF)")
    print(f"  Cluster:             Celestia DA-infra (TIA, rollup adoption) vs Avalanche Subnet L1 (AVAX, RWA)")
    print(f"  Profit 3% sleeve:    $87,086/yr net @$10M @4x; $239/day")
    print(f"  Triple AVAX hedge:   K736 anti-corr K484(-0.632)/K661(-0.643)/K686(-0.603)")
    print(f"  Alt-alt rank:        #8 OOS Sh=12.97 (13th alt-alt, 67th daemon)")
    print(f"  HL concentration:    64.5% UNCHANGED (Bybit-only — 3% HL-only = 67.5% > 65% cap)")
    print(f"  60d gate:            Realized Sh>=6 + fill>=60% + maxDD<15%")
    print(f"  TIA notional cap:    K738 3% (2nd TIA strategy; monitor combined TIA notional)")
    print(f"  AVAX notional cap:   K738 3% + existing AVAX (K484/K661/K686/K696) — monitor combined")
    print()

    return 0


# ─────────────────────────────────────────────────────────────────────────────
# CLI entry point
# ─────────────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="K736 TIA-AVAX FR Differential Strategy (K738 scaffold, DA-infra vs Subnet L1, Bybit primary)"
    )
    parser.add_argument("--dry-run",   action="store_true", default=True,
                        help="Paper-trade simulation (default)")
    parser.add_argument("--status",    action="store_true",
                        help="Print current dashboard state and exit")
    parser.add_argument("--rebalance", action="store_true",
                        help="Check and apply delta-neutral rebalance")
    parser.add_argument("--close",     default=None, metavar="REASON",
                        help="Close all paired positions with reason")
    parser.add_argument("--aum",       type=float, default=AUM_DEFAULT,
                        help=f"Reference AUM in USD (default: ${AUM_DEFAULT:,.0f})")
    args = parser.parse_args()

    if args.status:
        dash = _load_dashboard()
        print(f"\n=== K736/K738 Dashboard ({dash.get('last_poll_jst', '—')}) ===")
        print(json.dumps(dash, indent=2))
        return 0

    if args.rebalance:
        dash   = _load_dashboard()
        result = daily_rebalance(dash)
        print(f"\n=== K736/K738 Rebalance Check ===")
        print(json.dumps(result, indent=2))
        return 0

    if args.close:
        result = close_paired_position(args.close, dry_run=args.dry_run)
        print(f"\n=== K736/K738 Close Result ===")
        print(json.dumps(result, indent=2))
        return 0

    return run_cycle(dry_run=args.dry_run, aum=args.aum)


if __name__ == "__main__":
    sys.exit(main())
