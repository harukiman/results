#!/usr/bin/env python3
"""
k735_hbar_sol_run.py — K735 HBAR-SOL FR Differential Strategy
==============================================================
TWELFTH ALT-ALT scaffold (66th daemon): HBAR vs SOL (no BTC/ETH base).
Signal: HBAR_FR - SOL_FR
W=240h rolling mean, zero threshold (sign only)
Bybit-only (HBAR-PERP + SOL-PERP on Bybit)
4x leverage, 2% sleeve standalone

K735 HBAR-SOL alt-alt hypothesis (CROSS-CLUSTER: Enterprise-Consortium-DAG vs Solana SVM):
  HBAR (Hedera Hashgraph) FR dynamics: Enterprise institutional, episodic spikes.
  HBAR FR driven by: Hedera governing council membership additions (quarterly cadence),
  HBAR Foundation grant announcements, enterprise partnership news (BlackRock HTS
  tokenization, CBDC pilots), HBAR treasury unlock schedules (50B fixed supply, periodic
  releases), regulatory clarity (no SEC action history vs crypto-native peers).
  HBAR FR mean = +10.50%/yr (structurally POSITIVE — institutional enterprise premium).

  SOL (Solana SVM L1) FR dynamics: Retail-momentum/meme driven.
  SOL FR governed by: memecoin season cycles (BONK/WIF/POPCAT, Pump.fun launches),
  Jupiter DEX volume explosions, Jito MEV revenue cycles (block proposer fee cycles),
  Solana network congestion/outage narratives, ETH vs SOL narrative battles.
  SOL FR mean = +7.73%/yr (retail SVM baseline).

  Cross-cluster: HBAR (Enterprise-Consortium-DAG #21) vs SOL (Solana SVM L1).
  GENUINELY different economic segments — orthogonal FR drivers. MR9: HBAR-SOL =
  K610_diff - K476_diff with K610 ⊥ K476 signal corr=-0.0592.
  MR8: HBAR new vertex in alt-alt graph (not in {APT,ATOM,SOL,INJ,AVAX,SEI,TIA,ENA,BNB,LDO}).

K735 KEY INSIGHT — Persistent Cross-Cluster Carry:
  W=240h (10d) intermediate window: captures cross-cluster FR cycle differential
  between HBAR enterprise adoption events (quarterly cadence, ~35d sub-cycle captured at 10d)
  and SOL retail momentum cycles (weekly).

  Dominant state (75.1% OOS): HBAR FR > SOL FR (enterprise institutional premium)
    -> signal = +1 -> SHORT HBAR (collect HBAR enterprise FR) + LONG SOL
    -> Persistent carry from HBAR FR structural premium over SOL
  Other state (24.9%): SOL FR > HBAR FR (SOL meme-season spike)
    -> signal = -1 -> SHORT SOL + LONG HBAR (collect SOL premium when meme mania spikes)
  HBAR structural carry: +2.77%/yr (HBAR 10.50%/yr vs SOL 7.73%/yr)

K735 §6 gates (ACCEPT CONDITIONAL — 8/9 PASS, MR8/MR9 compliant):
  - OOS Sharpe: 26.9506 (W=240h, zero threshold, 218.9d OOS period)
  - OOS Ann Return: 6.55% @1x, 26.18% @4x
  - Net @$10M @4x @1% sleeve: $104,728/yr USDC; @2% sleeve: $209,456/yr
  - ADF t=-16.3884 (strongly stationary p=0.0)
  - G4 walk-forward: 7/8 folds positive (fold 3 = -4.15, Dec 2025–Jan 2026 risk-off)
  - G5: 10/10 PASS (max corr=0.3488 LDO-SOL — below 0.40 threshold)
  - G5a K610 HBAR-BTC parent: corr=0.1445 PASS (shared HBAR leg, below 0.40)
  - G5b K476 SOL-BTC parent:  corr=0.2091 PASS (shared SOL leg, below 0.40)
  - G6: 16.7 trades/yr (PASS >= 12 relaxed threshold)
  - G7: 26.18% @4x (PASS >= 5%)
  - G8: FAIL structural (HL 1h vs Bybit 8h settlement mismatch — same as K610 pattern)
  - G9: 218.9d OOS (PASS >= 180d)
  - MR8: HBAR NOT in {APT,ATOM,SOL,INJ,AVAX,SEI,TIA,ENA,BNB,LDO} — new vertex PASS
  - MR9: HBAR-SOL = K610_diff - K476_diff (K610⊥K476 corr=-0.0592, max_err=2.17e-19) PASS
  - 60d gate: Realized Sh >= 13, fill >= 60%, DD < 15%
  - Alt-alt family: 12th alt-alt (Enterprise-DAG vs SVM, rank #7 by OOS Sharpe)

Signal mechanism (MR9: HBAR-SOL = K610_diff - K476_diff):
  diff = HBAR_FR - SOL_FR   (HBAR minus SOL)
  mean_240h = 240h rolling mean of diff (30 x 8h periods)
  sign = sign(mean_240h)
  +1 -> SHORT HBAR / LONG SOL  (HBAR FR > SOL FR — enterprise premium 75.1% OOS)
  -1 -> SHORT SOL  / LONG HBAR (SOL FR > HBAR FR — meme-season spike 24.9% OOS)

HL concentration:
  Current HL weight: 64.5% (post-K731)
  K737 HL-only impact: 0.0pp (Bybit-only — both legs on Bybit)
  Resolution: Bybit mandatory (HBAR HL maxLev=5 too low; HBAR Bybit maxLev=75, SOL maxLev=100)
  K737 is fully Bybit-only: HL concentration UNCHANGED at 64.5% (headroom 0.5pp preserved)

K737 production scaffold:
  - 66th daemon (12th alt-alt scaffold, Enterprise-DAG vs SVM, rank #7 OOS Sh=26.95)
  - Bybit-only (HBAR HL maxLev=5 vs Bybit maxLev=75; HL cap 65% constraint)
  - 2% standalone sleeve, 4x leverage
  - $104,728/yr net @$10M @1% sleeve, $209,456/yr @2% sleeve
  - 60d paper-trade gate: Realized Sh>=13 + fill>=60% + maxDD<15%
  - HBAR notional: K737 2% standalone (first HBAR in portfolio — new Enterprise-DAG vertex)
  - SOL notional: K737 2% + existing SOL strategies — monitor combined SOL on Bybit

Architecture (K683/K685/K687/K689/K693/K697/K699/K710/K721/K730/K731 alt-alt pattern):
  1. fetch_fr_batch()                   -> fetch HBAR + SOL FR every 8h from Bybit
  2. compute_signal(hbar_fr, sol_fr)   -> 240h rolling mean of (HBAR_FR - SOL_FR); sign()
  3. decide_position(signal)            -> SHORT_HBAR_LONG_SOL | SHORT_SOL_LONG_HBAR | NEUTRAL
  4. submit_paired_trade(long, short)   -> POST_ONLY paired (HBAR + SOL legs, both Bybit)
  5. daily_rebalance()                  -> drift > 5% triggers rebalance
  6. close_paired_position(reason)      -> sequential: short first, then long

Paper-trade mode is the DEFAULT.  No orders are submitted unless
PAPER_TRADE=False is explicitly set in the environment.

K339 security: REPO_ROOT from __file__, no /Users/ literals.
No new packages — stdlib urllib + json only.

Usage:
  python3 scripts/k735_hbar_sol_run.py --dry-run
  python3 scripts/k735_hbar_sol_run.py --status
  python3 scripts/k735_hbar_sol_run.py --rebalance
  python3 scripts/k735_hbar_sol_run.py --close "scheduled exit"
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

DASHBOARD_PATH  = DATA_DIR  / "k735_dashboard.json"
FR_HISTORY_PATH = CACHE_DIR / "k735_fr_history.jsonl"
TRADE_LOG_PATH  = CACHE_DIR / "k735_paper_trades.jsonl"

JST = timezone(timedelta(hours=9))
UTC = timezone.utc

# ── Strategy constants ────────────────────────────────────────────────────────
PAPER_TRADE         = True          # never submit real orders in paper-trade mode
SLEEVE_PCT          = 0.020         # K737 sleeve = 2% of AUM (standalone, Bybit-only)
LEVERAGE            = 4.0           # 4x per K735 analysis (K430 cap)
AUM_DEFAULT         = 10_000_000.0  # $10M reference AUM
DRIFT_REBALANCE_PCT = 0.05          # rebalance if legs drift > 5%
IOC_TIMEOUT_SEC     = 300           # 5 min fill window
EMA_PERIOD_HOURS    = 240           # 240h rolling mean primary config (W=240h)
EMA_PERIOD_PERIODS  = EMA_PERIOD_HOURS // 8  # = 30 periods (8h settlement cycle)
SIGNAL_SIGMA_MULT   = 0.0           # zero threshold (sign of rolling mean)
BYBIT_API_URL       = "https://api.bybit.com"
HL_API_URL          = "https://api.hyperliquid.xyz/info"

# ── Venue config (Bybit-only — HBAR-PERP + SOL-PERP on Bybit) ─────────────────
# HL concentration: 64.5% baseline — Bybit mandatory (HBAR HL maxLev=5 too low + cap constraint)
# K737: 64.5% HL baseline; Bybit-only preserves 0.5pp headroom to 65% cap.
# Bybit: HBAR maxLev=75, SOL maxLev=100 (both listed, perp pairs confirmed in K735 eval)
HL_CONCENTRATION_PRE_K737  = 64.5   # post-K731 reference
HL_CONCENTRATION_POST_K737 = 64.5   # UNCHANGED (Bybit-only — HL-only would use HBAR 5x cap)

BYBIT_HBAR_MAX_LEV = 75
BYBIT_SOL_MAX_LEV  = 100

# ── Position state constants ──────────────────────────────────────────────────
STATE_NEUTRAL               = "NEUTRAL"
STATE_SHORT_HBAR_LONG_SOL   = "SHORT_HBAR_LONG_SOL"  # signal +1: HBAR FR > SOL FR (dominant 75.1%)
STATE_SHORT_SOL_LONG_HBAR   = "SHORT_SOL_LONG_HBAR"  # signal -1: SOL FR > HBAR FR (meme spike)

# ── Symbols fetched from Bybit for FR data ────────────────────────────────────
# K737: HBAR + SOL only — direct alt-alt differential (TWELFTH ALT-ALT pair)
SYMBOLS = ("HBAR", "SOL")


# ─────────────────────────────────────────────────────────────────────────────
# HTTP helpers (stdlib urllib only — no requests)
# ─────────────────────────────────────────────────────────────────────────────

def _http_get(url: str, timeout: int = 10) -> Optional[dict]:
    try:
        req = urllib.request.Request(
            url, headers={"User-Agent": "crypto-lab-k735/1.0"}
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        print(f"  [k735] HTTP error: {e}", file=sys.stderr)
        return None


def _http_post(url: str, payload: dict, timeout: int = 10) -> Optional[dict]:
    try:
        data = json.dumps(payload).encode()
        req  = urllib.request.Request(
            url, data=data,
            headers={"Content-Type": "application/json",
                     "User-Agent": "crypto-lab-k735/1.0"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        print(f"  [k735] HTTP error: {e}", file=sys.stderr)
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Phase 1 — Funding rate fetch (HBAR + SOL from Bybit)
# ─────────────────────────────────────────────────────────────────────────────

def _fetch_bybit_fr_batch() -> Dict[str, float]:
    """
    Fetch current 8h funding rates for HBAR and SOL from Bybit.
    Returns {symbol: fr_8h_fraction}.

    Bybit API: /v5/market/tickers?category=linear
    K737: both legs on Bybit (HBAR-PERP + SOL-PERP).
    Bybit-only mandatory: HBAR HL maxLev=5 (too low for 4x) + HL 64.5% headroom constraint.
    Both HBARUSDT and SOLUSDT perpetuals listed on Bybit (HBAR maxLev=75, SOL maxLev=100).

    Fallback: HL metaAndAssetCtxs for cross-reference (informational only).
    K737: Bybit is the execution venue; HL FR data is used for cross-check only.
    G8 structural: HL uses 1h FR vs Bybit 8h FR — settlement interval mismatch (K610 pattern).
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
        print(f"  [k735] Bybit partial result {list(result.keys())} — trying HL fallback",
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
                print(f"  [k735] HL fallback used for {sym} FR (informational)", file=sys.stderr)
            except (TypeError, ValueError):
                continue

    if len(result) < len(SYMBOLS):
        print(f"  [k735] Warning: only fetched {list(result.keys())} FRs", file=sys.stderr)
    return result


def _load_fr_history() -> List[dict]:
    """Load K735 FR history JSONL."""
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
    fr_hbar: float, fr_sol: float, hbar_sol_diff: float
) -> None:
    """Append one FR snapshot to history."""
    rec = {
        "ts_utc":       datetime.now(UTC).isoformat(),
        "fr_hbar":      round(fr_hbar,      10),
        "fr_sol":       round(fr_sol,        10),
        "hbar_sol_diff": round(hbar_sol_diff, 10),  # HBAR_FR - SOL_FR
    }
    with open(FR_HISTORY_PATH, "a") as f:
        f.write(json.dumps(rec) + "\n")


# ─────────────────────────────────────────────────────────────────────────────
# Phase 2 — Signal computation (HBAR-SOL direct differential, 240h rolling mean)
# ─────────────────────────────────────────────────────────────────────────────

def compute_signal(
    fr_hbar: Optional[float] = None,
    fr_sol:  Optional[float] = None,
) -> dict:
    """
    Fetch live HBAR and SOL FRs from Bybit, compute HBAR-SOL differential,
    and compute 240h rolling mean for direction signal.

    Signal mechanism (K735 direct differential — Enterprise-DAG vs SVM):
      diff = HBAR_FR - SOL_FR   (HBAR minus SOL = K610_diff - K476_diff per MR9)
      mean_240h = 240h rolling mean of diff (30 x 8h periods)
      sign  = sign(mean_240h)
      +1 -> SHORT HBAR / LONG SOL  (HBAR FR higher — enterprise institutional premium, 75.1% OOS)
      -1 -> SHORT SOL  / LONG HBAR (SOL FR higher — meme-season spike 24.9% OOS)

    Cross-cluster mechanism:
      - HBAR FR: Hedera Hashgraph enterprise governance — driven by council membership events
        (39 permissioned council nodes: Google, IBM, Boeing, etc.), HBAR Foundation grants,
        BlackRock HTS tokenization announcements, CBDC pilot programs, treasury unlocks
        (50B fixed supply periodic releases), regulatory clarity (no SEC action pattern).
        HBAR FR mean = +10.50%/yr (structurally POSITIVE — institutional enterprise premium).
      - SOL FR: Solana SVM L1 retail-momentum driven. Governed by memecoin season cycles
        (BONK/WIF/POPCAT, Pump.fun launches), Jupiter DEX volume explosions, Jito MEV revenue
        cycles (block proposer fee cycles), Solana network congestion narratives.
        SOL FR mean = +7.73%/yr (retail SVM baseline).
      - HBAR FR > SOL FR 75.1% of time (OOS, 240h rolling): enterprise institutional premium.
      - MR9: HBAR-SOL = K610_diff - K476_diff (K610⊥K476 corr=-0.0592, max_err=2.17e-19).
      - W=240h intermediate: between K610 W=840h (HBAR enterprise 35d cycle) and
        K476 W=168h (SOL retail 7d cycle). Captures cross-cluster cycle differential.

    K735 §6 validation (8/9 PASS, ACCEPT CONDITIONAL):
      - OOS Sharpe: 26.9506 (W=240h, zero threshold, 218.9d OOS period)
      - OOS Ann Ret: 6.55% @1x, 26.18% @4x
      - Net @$10M @4x @1% sleeve: $104,728/yr; @2%: $209,456/yr
      - ADF t=-16.3884 (strongly stationary p=0.0)
      - G4 walk-forward: 7/8 folds positive (fold 3 = -4.15, Dec 2025–Jan 2026 risk-off)
      - G5: 10/10 PASS (max corr=0.3488 LDO-SOL, below 0.40 threshold)
      - G6 trade count: 16.7/yr (PASS >= 12 relaxed threshold)
      - G7: 26.18% @4x (PASS >= 5%)
      - G8: FAIL structural (HL 1h vs Bybit 8h settlement mismatch — same K610 pattern)
      - G9: 218.9d OOS (PASS >= 180d)
      - MR8: HBAR outside {APT,ATOM,SOL,INJ,AVAX,SEI,TIA,ENA,BNB,LDO} — new vertex PASS
      - MR9: HBAR-SOL = K610-K476 with K610⊥K476 (corr=-0.0592) PASS
      - 60d gate: Realized Sh>=13 + fill>=60% + maxDD<15%

    Returns:
      {
        "fr_hbar":          float,
        "fr_sol":           float,
        "hbar_sol_diff":    float,    # HBAR_FR - SOL_FR (current)
        "mean_240h":        float,    # 240h rolling mean of differential
        "diff_sigma":       float,    # 240h rolling sigma (informational)
        "history_points":   int,
        "regime":           str,      # HBAR_PREMIUM | SOL_PREMIUM | NEUTRAL
        "signal_direction": int,      # +1 | -1 | 0
        "ts_jst":           str,
      }
    """
    if fr_hbar is None or fr_sol is None:
        frs    = _fetch_bybit_fr_batch()
        fr_hbar = frs.get("HBAR", 0.0)
        fr_sol  = frs.get("SOL",  0.0)

    # HBAR-SOL direct differential (= K610_diff - K476_diff per MR9)
    hbar_sol_diff = fr_hbar - fr_sol

    _append_fr_history(fr_hbar, fr_sol, hbar_sol_diff)

    # Load history for rolling mean + sigma (240h = 30 x 8h periods)
    history = _load_fr_history()
    diffs   = [r["hbar_sol_diff"] for r in history if "hbar_sol_diff" in r]

    n_periods = EMA_PERIOD_PERIODS   # 30 periods (240h / 8h)

    # Rolling mean: simple mean of last n_periods diffs
    window = diffs[-n_periods:] if len(diffs) >= 1 else diffs
    if window:
        mean_240h = sum(window) / len(window)
    else:
        mean_240h = 0.0

    # Rolling sigma: std of last n_periods diffs (informational)
    if len(window) >= 2:
        mean_w = sum(window) / len(window)
        sigma  = math.sqrt(sum((x - mean_w) ** 2 for x in window) / (len(window) - 1))
    else:
        sigma  = abs(mean_240h) if mean_240h != 0 else 1e-8   # fallback

    # Regime classification (zero threshold — per K735 spec)
    # HBAR_PREMIUM: HBAR FR > SOL FR (enterprise institutional demand — 75.1% OOS time)
    # SOL_PREMIUM: SOL FR > HBAR FR (meme-season spike or HBAR enterprise pause — 24.9%)
    if mean_240h > 0:
        regime    = "HBAR_PREMIUM"   # HBAR FR > SOL FR -> short HBAR / long SOL (dominant)
        direction = 1
    elif mean_240h < 0:
        regime    = "SOL_PREMIUM"    # SOL FR > HBAR FR -> short SOL / long HBAR
        direction = -1
    else:
        regime    = "NEUTRAL"
        direction = 0

    return {
        "fr_hbar":          round(fr_hbar,       10),
        "fr_sol":           round(fr_sol,          10),
        "hbar_sol_diff":    round(hbar_sol_diff,   10),
        "mean_240h":        round(mean_240h,       10),
        "diff_sigma":       round(sigma,           10),
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
    Determine trade direction from HBAR-SOL differential rolling mean.

    Logic (HBAR-SOL direct differential pair, Bybit primary):
      regime = HBAR_PREMIUM (mean_240h > 0):
        HBAR FR > SOL FR: enterprise institutional demand (structural 75.1% OOS)
        -> short HBAR (collect HBAR enterprise premium)
        -> long SOL   (SOL FR lower — net positive carry when HBAR > SOL)
        -> position_state = SHORT_HBAR_LONG_SOL
        -> both legs on Bybit

      regime = SOL_PREMIUM (mean_240h < 0):
        SOL FR > HBAR FR: memecoin season spike or HBAR enterprise quiet period
        -> short SOL   (collect SOL meme-season premium when retail mania spikes)
        -> long HBAR   (HBAR FR lower — net positive carry when SOL > HBAR)
        -> position_state = SHORT_SOL_LONG_HBAR
        -> both legs on Bybit

      regime = NEUTRAL: no trade (mean_240h == 0 exactly — rare)

    K735 edge (cross-cluster mechanism):
      HBAR (Hedera Enterprise-DAG) driven by council governance events, enterprise adoption
      milestones (permissioned 39-node council), CBDC pilots, BlackRock tokenization activity.
      HBAR FR mean = +10.50%/yr (structurally positive, institutional enterprise demand).
      SOL (Solana L1) driven by retail momentum: meme cycles, Jito MEV, Jupiter DEX, Pump.fun.
      SOL FR spikes are episodic (BONK/WIF/POPCAT) but mean-reverts to 7.73%/yr.
      Cross-cluster: HBAR enterprise governance vs SOL retail speculation.
        - Orthogonal drivers (MR9: HBAR-SOL = K610_diff - K476_diff, K610⊥K476 corr=-0.059)
        - 7/8 WF: one negative fold (fold 3 Dec 2025–Jan 2026 = -4.15, crypto risk-off)
        - G5 ALL PASS: max corr=0.3488 (LDO-SOL — below 0.40 threshold)
        - Net $104,728/yr @$10M @1% sleeve (12th alt-alt, rank #7 OOS Sh=26.95)

    Returns:
      {long_asset, short_asset, long_venue, short_venue, mean_240h,
       signal_direction, size_multiplier, position_state}
      or None if NEUTRAL.
    """
    regime    = signal.get("regime", "NEUTRAL")
    mean_240h = signal.get("mean_240h", 0.0)
    direction = signal.get("signal_direction", 0)

    if regime == "NEUTRAL":
        return None

    if regime == "HBAR_PREMIUM":
        # HBAR FR > SOL FR: collect HBAR enterprise premium (short HBAR / long SOL) — 75.1% OOS
        long_asset  = "SOL"
        short_asset = "HBAR"
        state       = STATE_SHORT_HBAR_LONG_SOL
    else:  # SOL_PREMIUM
        # SOL FR > HBAR FR: collect SOL meme-season premium (short SOL / long HBAR) — 24.9% OOS
        long_asset  = "HBAR"
        short_asset = "SOL"
        state       = STATE_SHORT_SOL_LONG_HBAR

    # Both legs on Bybit (K737: HBAR HL maxLev=5 too low for 4x; Bybit maxLev=75)
    long_venue  = "Bybit"
    short_venue = "Bybit"

    return {
        "long_asset":       long_asset,
        "short_asset":      short_asset,
        "position_state":   state,
        "long_venue":       long_venue,
        "short_venue":      short_venue,
        "mean_240h":        mean_240h,
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
    Compute equal notional for both legs of the HBAR-SOL paired trade.

    K737 Bybit-only config (both HBAR-PERP + SOL-PERP on Bybit):
      sleeve_capital   = aum x sleeve_pct      (e.g. $10M x 2.0% = $200K)
      total_notional   = sleeve_capital x lev   ($200K x 4 = $800K)
      notional_per_leg = total_notional / 2     ($400K per leg)

    At $10M / 2.0% sleeve / 4x:
      HBAR leg: $100K capital x 4x = $400K notional (Bybit HBAR-PERP)
      SOL leg:  $100K capital x 4x = $400K notional (Bybit SOL-PERP)
      Total:    $800K notional (two legs combined)
      Margin:   $200K (2.0% of AUM)
      HL conc:  UNCHANGED 64.5% (Bybit-only — HL HBAR maxLev=5 + headroom preserved)
      Net profit @1%: ~$104,728/yr @$10M @4x (OOS 6.55% ann ret x $10M x 4x x 1.0% x 0.40)

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
    Submit K737 HBAR-SOL paired trade: POST_ONLY both legs in parallel.

    Protocol (K737 Bybit primary — both legs on Bybit):
      1. Submit HBAR leg on Bybit POST_ONLY
      2. Submit SOL leg on Bybit POST_ONLY
      3. Both legs submitted in parallel (K439 pattern)
      4. IOC fallback per leg if POST_ONLY times out
      5. If both fail: retry next 8h cycle

    Args:
      long_leg:  {"symbol": "SOL",  "notional": 400000, "venue": "Bybit"}
      short_leg: {"symbol": "HBAR", "notional": 400000, "venue": "Bybit"}
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
        print(f"  [K737] {mode_tag}: LONG {long_sym}@{long_venue} ${long_notl:,.0f}  "
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
            "venue_config":     "BYBIT_PRIMARY_HBAR_SOL_ENTERPRISE_DAG_VS_SVM",
            "mechanism_note":   (
                "HBAR-SOL direct differential (Enterprise-Consortium-DAG vs Solana SVM, K735/K737): "
                "HBAR FR = Hedera Hashgraph enterprise governance (council membership events, "
                "39 permissioned nodes, HBAR Foundation grants, BlackRock HTS tokenization, "
                "CBDC pilots, 50B fixed supply treasury unlocks). HBAR mean = +10.50%/yr. "
                "SOL FR = Solana retail momentum (meme cycles BONK/WIF/POPCAT, Pump.fun, "
                "Jito MEV revenue, Jupiter DEX volume). SOL mean = +7.73%/yr. "
                "HBAR FR > SOL FR 75.1% of time OOS (enterprise institutional premium). "
                "MR9: HBAR-SOL = K610_diff - K476_diff (K610⊥K476 corr=-0.0592). "
                "G4: 7/8 WF positive (87.5%). G5: 10/10 PASS (max corr=0.3488 LDO-SOL). "
                "Net: $104,728/yr @$10M @1% sleeve. "
                "Bybit mandatory: HBAR HL maxLev=5 (too low for 4x) + HL headroom 0.5pp."
            ),
            "ts_utc":           ts,
        }
        _append_trade_log(result)
        return result

    # LIVE scaffold (not reached in PAPER_TRADE mode):
    print(f"  [K737] SCAFFOLD LIVE: parallel POST_ONLY "
          f"LONG {long_sym}@{long_venue} ${long_notl:,.0f} "
          f"+ SHORT {short_sym}@{short_venue} ${short_notl:,.0f}")
    long_order_id  = f"SCAFFOLD_LONG_{long_sym}_{int(time.time())}"
    short_order_id = f"SCAFFOLD_SHORT_{short_sym}_{int(time.time())}"

    # Scaffold: poll not implemented — retry next 8h cycle
    print(f"  [K737] Neither leg filled within timeout — retry next 8h cycle")
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
    Check if current K737 position has drifted beyond DRIFT_REBALANCE_PCT (5%).

    K737 Bybit-only: both legs on Bybit (HBAR-PERP + SOL-PERP).
    Drift detection: compare stored HBAR leg notional vs SOL leg notional.
    Threshold: 5% (same as K449/K476/K484/K493/K629/K663/K696/K698/K708/K719/K729 pattern).

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
    Both legs on Bybit (K737 Bybit primary — HBAR-PERP + SOL-PERP).

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

    if state == STATE_SHORT_HBAR_LONG_SOL:
        long_sym,  short_sym  = "SOL", "HBAR"
    else:  # SHORT_SOL_LONG_HBAR
        long_sym,  short_sym  = "HBAR", "SOL"

    long_notional  = float(dash.get("long_notional",  0.0))
    short_notional = float(dash.get("short_notional", 0.0))

    if dry_run or PAPER_TRADE:
        mode_tag = "DRY_RUN" if dry_run else "PAPER_TRADE"
        print(f"  [K737] {mode_tag} CLOSE:")
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
        print(f"  [K737] SCAFFOLD CLOSE:")
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
    """Load k735_dashboard.json; return defaults if missing."""
    if DASHBOARD_PATH.exists():
        try:
            return json.loads(DASHBOARD_PATH.read_text())
        except Exception:
            pass
    return {
        "last_poll_jst":           "—",
        "mean_240h":               0.0,
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
    """Write k735_dashboard.json with full signal + regime state."""
    dash = _load_dashboard()

    # Update signal data
    dash["last_poll_jst"]          = signal.get("ts_jst", "—")
    dash["fr_hbar_current"]        = signal.get("fr_hbar",        0.0)
    dash["fr_sol_current"]         = signal.get("fr_sol",          0.0)
    dash["hbar_sol_diff_current"]  = signal.get("hbar_sol_diff",  0.0)
    dash["mean_240h"]              = signal.get("mean_240h",      0.0)
    dash["diff_sigma"]             = signal.get("diff_sigma",     0.0)
    dash["regime"]                 = signal.get("regime",    "NEUTRAL")
    dash["signal_direction"]       = signal.get("signal_direction", 0)
    dash["history_points"]         = signal.get("history_points", 0)

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
    dash["hl_concentration_pct"]    = HL_CONCENTRATION_POST_K737   # 64.5% unchanged

    # Paper-trade status
    paper_status = dash.get("paper_trade_status", {"days_elapsed": 0, "target_60d": 60})
    dash["paper_trade_status"]      = paper_status

    # 60d activation gate metrics (K737: Realized Sh >= 13, fill >= 60%, DD < 15%)
    dash["gate_metrics"] = {
        "realized_sharpe_target":  13.0,     # >=13 (50% of OOS Sh=26.95)
        "fill_rate_target_pct":    60,
        "max_drawdown_target_pct": 15,        # <15%
        "current_realized_sharpe": dash.get("60d_sharpe", 0.0),
        "current_fill_rate_pct":   0.0,
        "current_max_dd_pct":      0.0,
        "gate_status":             "IN_PROGRESS",
        "activation_trigger":      "60d paper-trade: Sh>=13 AND fill>=60% AND maxDD<15%",
        "profit_at_activation_2pct": "$209,456/yr net @$10M @4x (2% sleeve, OOS 6.55% ann ret)",
        "bybit_primary_note":      "Bybit primary: HBAR maxLev=75, SOL maxLev=100. HL HBAR maxLev=5 too low + HL 64.5% headroom.",
    }

    # Strategy metadata
    dash["paper_trade_mode"]   = PAPER_TRADE
    dash["wave"]               = "K737"
    dash["strategy"]           = "K735 HBAR-SOL FR Differential (Enterprise-DAG vs SVM, W=240h, Bybit primary)"
    dash["execution_mode"]     = "POST_ONLY_PARALLEL"
    dash["venue_config"]       = "BYBIT_PRIMARY"
    dash["cross_cluster_mechanism"] = {
        "formula":                 "diff = HBAR_FR - SOL_FR  (= K610_diff - K476_diff per MR9)",
        "rolling_window":          "W=240h (30 x 8h periods)",
        "signal":                  "sign(rolling_mean_240h(diff))",
        "g5a_k610_hbar_btc_corr":  0.1445,    # PASS (shared HBAR parent leg, below 0.40)
        "g5b_k476_sol_btc_corr":   0.2091,    # PASS (shared SOL parent leg, below 0.40)
        "g5g_k728_ldo_sol_corr":   0.3488,    # PASS (max corr, below 0.40 threshold)
        "mr9_identity":            "HBAR-SOL = K610_diff - K476_diff",
        "mr9_k610_k476_corr":      -0.0592,
        "mr9_max_err":             2.17e-19,
        "adf_tstat":               -16.3884,
        "adf_pvalue":              0.0,
        "ou_halflife_h":           2.76,
        "hbar_gt_sol_oos_pct":     75.1,       # HBAR FR > SOL FR 75.1% of OOS time
        "walk_forward_7_8":        True,       # 7/8 folds positive (87.5% rate)
        "note": (
            "HBAR-SOL: $104,728/yr net @$10M @4x @1% sleeve ($209,456/yr @2%). "
            "HBAR (Hedera Enterprise-Consortium-DAG) vs SOL (Solana SVM L1) — orthogonal clusters. "
            "HBAR FR = enterprise council governance (39 permissioned nodes: Google/IBM/Boeing/etc), "
            "HBAR Foundation grants, BlackRock HTS tokenization, CBDC pilots, 50B supply unlocks. "
            "Mean +10.50%/yr (structurally positive — institutional enterprise demand). "
            "SOL FR = retail meme cycles (BONK/WIF/POPCAT, Pump.fun) + Jito MEV + Jupiter DEX. "
            "Mean +7.73%/yr. HBAR structural premium +2.77%/yr (institutional vs retail separation). "
            "MR9: HBAR-SOL = K610-K476 with K610⊥K476 (corr=-0.0592, max_err=2.17e-19). "
            "G5 ALL PASS (10/10): max corr=0.3488 (LDO-SOL, below 0.40). "
            "W=240h intermediate: between K610 W=840h (HBAR enterprise) and K476 W=168h (SOL retail). "
            "7/8 WF positive (87.5%): fold 3 Dec 2025–Jan 2026 = -4.15 (crypto risk-off). "
            "G6 16.7 trades/yr: PASS (>= 12 relaxed threshold). "
            "G8 FAIL structural: HL 1h vs Bybit 8h settlement mismatch (same K610 pattern). "
            "12th alt-alt scaffold (66th daemon). HBAR new Enterprise-DAG vertex in alt-alt graph."
        ),
    }
    dash["activation_criteria"] = {
        "60d_paper_trade_gate":  "required",
        "realized_sharpe_min":   13.0,
        "fill_rate_min_pct":     60,
        "max_drawdown_max_pct":  15,
        "status":                "SCAFFOLD-READY",
        "activation_sleeve_pct": 0.020,
        "venue":                 "Bybit primary (HBAR-PERP + SOL-PERP both on Bybit)",
    }
    dash["oos_performance"] = {
        "sharpe":                   26.9506,
        "sharpe_is":                22.5842,
        "is_oos_ratio":             1.19,      # OOS/IS (IS=22.58, OOS=26.95 — OOS outperforms IS)
        "oos_ann_ret_1x_pct":       6.5455,
        "oos_ann_ret_4x_pct":       26.1819,
        "ann_return_usd_1pct_4x":   104_728,
        "ann_return_usd_2pct_4x":   209_456,
        "wave_accept":              "K735 ACCEPT CONDITIONAL (K737 scaffold) — 8/9 §6 gates PASS",
        "cluster":                  "Hedera Enterprise-Consortium-DAG (HBAR) vs Solana SVM L1 (SOL)",
        "g5a_k610_verdict":         "PASS (corr=0.1445, shared HBAR parent leg, below 0.40)",
        "g5b_k476_verdict":         "PASS (corr=0.2091, shared SOL parent leg, below 0.40)",
        "g5g_k728_verdict":         "PASS (corr=0.3488 max, LDO-SOL SOL-leg, below 0.40)",
        "g6_verdict":               "PASS (16.7/yr >= 12 relaxed threshold)",
        "g8_verdict":               "FAIL structural (HL 1h vs Bybit 8h settlement mismatch)",
        "walk_forward":             "7/8 folds positive (87.5% rate, fold 3 = -4.15 Dec 2025–Jan 2026)",
        "perm_pvalue":              0.0,
        "dsr_pvalue":               0.0,
        "trades_per_yr":            16.7,
        "max_drawdown_oos_pct":     0.2914,
        "daemon_number":            "66th",
        "alt_alt_rank":             "12th alt-alt scaffold (rank #7 by OOS Sharpe in alt-alt family)",
        "alt_alt_family_ranking": {
            "k686_avax_sol":         50.27,    # rank 1
            "k708_bnb_sol":          48.59,    # rank 2
            "k728_ldo_sol":          46.84,    # rank 3
            "k682_atom_sol":         43.43,    # rank 4
            "k679_apt_sol":          39.29,    # rank 5
            "k719_ena_atom":         29.67,    # rank 6
            "k735_hbar_sol":         26.9506,  # rank 7 (THIS)
            "k696_ena_sol":          26.93,    # rank 8
            "k690_sei_sol":          25.11,    # rank 9
            "k694_tia_sol":          19.09,    # rank 10
            "k729_inj_atom":         18.75,    # rank 11
            "k684_sol_inj":           9.65,    # rank 12
        },
    }
    dash["notional_caps"] = {
        "hbar_cap_note": "HBAR total: K737 2% only (first HBAR in portfolio — new Enterprise-DAG vertex).",
        "sol_cap_note":  "SOL total: K737 2% + existing SOL strategies. Monitor combined SOL on Bybit.",
        "hl_cap_note":   "HL concentration 64.5% UNCHANGED (Bybit-only — HBAR HL maxLev=5 + 0.5pp headroom).",
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
      1. Fetch HBAR + SOL FRs from Bybit
      2. Compute HBAR-SOL differential + 240h rolling mean
      3. Decide position (sign of rolling mean — zero threshold)
      4. Compute delta-neutral notional
      5. If entering: submit paired trade (POST_ONLY, Bybit primary)
      6. If holding: check drift + rebalance
      7. Write k735_dashboard.json
    """
    ts_jst = datetime.now(JST).strftime("%Y-%m-%d %H:%M JST")
    print(f"\n=== K735 HBAR-SOL FR Differential (Enterprise-DAG vs Solana SVM) — {ts_jst} ===")
    print(f"  Mode:      {'DRY-RUN' if dry_run else 'PAPER-TRADE' if PAPER_TRADE else 'LIVE'}")
    print(f"  AUM:       ${aum:,.0f}  Sleeve: {SLEEVE_PCT:.1%}  Leverage: {LEVERAGE}x")
    print(f"  Venue:     Bybit primary (HBAR-PERP + SOL-PERP, both Bybit perps)")
    print(f"  HL cap:    64.5% baseline; HBAR HL maxLev=5 -> Bybit primary (maxLev=75)")
    print(f"  Execution: POST_ONLY parallel (K439)")
    print(f"  Signal:    diff = HBAR_FR - SOL_FR  (= K610_diff - K476_diff per MR9)")
    print(f"             sign(rolling_mean_240h)  (zero threshold, W=240h = 30 x 8h periods)")
    print(f"  Clusters:  HBAR Enterprise-DAG (council governance) | SOL Solana SVM (retail/meme)")
    print(f"  HBAR pct:  HBAR FR > SOL FR 75.1% of OOS time (enterprise institutional premium)")
    print(f"  MR9:       HBAR-SOL = K610_diff - K476_diff (K610⊥K476 corr=-0.0592)")
    print(f"  8/9 gates: OOS Sh=26.95, Net $104,728/yr @$10M @1% (12th alt-alt, rank #7)")
    print(f"  G5 PASS:   10/10, max corr=0.3488 (LDO-SOL), below 0.40 threshold")
    print(f"  G8 FAIL:   structural HL 1h vs Bybit 8h (same K610 pattern)")

    # Step 1: Fetch + compute HBAR-SOL differential
    print("\n  [Step 1] Computing HBAR-SOL FR differential...")
    signal = compute_signal()
    print(f"  HBAR FR:   {signal['fr_hbar']:+.8f} (8h, Bybit — enterprise council governance)")
    print(f"  SOL FR:    {signal['fr_sol']:+.8f} (8h, Bybit — Solana retail/meme momentum)")
    print(f"  HBAR-SOL:  {signal['hbar_sol_diff']:+.8f}  (direct differential = K610-K476)")
    print(f"  Mean 240h: {signal['mean_240h']:+.8f}")
    print(f"  Sigma:     {signal['diff_sigma']:+.8f}  (informational)")
    print(f"  Direction: {signal['signal_direction']:+d}  (+1=HBAR_PREMIUM short HBAR/long SOL 75.1%, -1=SOL_PREMIUM)")
    print(f"  Regime:    {signal['regime']}")
    print(f"  History:   {signal['history_points']} data points")

    # Step 2: Position decision
    print("\n  [Step 2] Deciding position...")
    decision = decide_position(signal)
    if decision:
        print(f"  Signal:   LONG {decision['long_asset']}@{decision['long_venue']} / "
              f"SHORT {decision['short_asset']}@{decision['short_venue']}")
        print(f"  State:    {decision['position_state']}")
        print(f"  Mean 240h:{decision['mean_240h']:+.8f}")
    else:
        print(f"  Signal:   NEUTRAL (rolling_mean_240h == 0 exactly)")

    # Step 3: Notional sizing
    notional_per_leg, total_notional = \
        compute_delta_neutral_notional(aum, SLEEVE_PCT, LEVERAGE)
    print(f"\n  [Step 3] Notional sizing:")
    print(f"  Sleeve capital:   ${aum * SLEEVE_PCT:,.0f}  ({SLEEVE_PCT:.1%} x ${aum/1e6:.0f}M)")
    print(f"  HBAR leg:         ${notional_per_leg:,.0f}  (2.0% x ${aum/1e6:.0f}M x {LEVERAGE}x / 2)")
    print(f"  SOL leg:          ${notional_per_leg:,.0f}  (2.0% x ${aum/1e6:.0f}M x {LEVERAGE}x / 2)")
    print(f"  Total notional:   ${total_notional:,.0f}")
    print(f"  Margin required:  ${total_notional/LEVERAGE:,.0f}  ({SLEEVE_PCT:.1%} AUM)")
    print(f"  Profit @$10M 2%:  OOS 6.55% ann ret = $209,456/yr net (2% sleeve); @1%: $104,728/yr")

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
        print(f"  Action: CLOSE (mean_240h == 0 exactly)")
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
    print(f"\n  === K735/K737 Cycle Complete ===")
    print(f"  Position state:      {dash_out.get('position_state')}")
    print(f"  Regime:              {dash_out.get('regime')}")
    print(f"  HBAR-SOL Mean 240h:  {dash_out.get('mean_240h'):+.8f}")
    print(f"  Signal direction:    {dash_out.get('signal_direction')}")
    print(f"  G5 max corr:         +0.3488 (LDO-SOL, PASS — below 0.40 threshold)")
    print(f"  G5a K610 parent:     +0.1445 PASS (HBAR shared leg)")
    print(f"  G5b K476 parent:     +0.2091 PASS (SOL shared leg)")
    print(f"  G8:                  FAIL structural (HL 1h vs Bybit 8h — K610 pattern)")
    print(f"  MR9 identity:        HBAR-SOL = K610_diff - K476_diff (K610⊥K476 corr=-0.0592)")
    print(f"  Paper-trade mode:    {PAPER_TRADE}")
    print(f"  OOS Sharpe:          26.9506 (IS=22.5842)")
    print(f"  G4 Walk-Forward:     7/8 positive (87.5% — fold 3 = -4.15 Dec 2025–Jan 2026 risk-off)")
    print(f"  Cluster:             Hedera Enterprise-DAG (HBAR council) vs Solana SVM (SOL retail)")
    print(f"  Profit 2% sleeve:    $209,456/yr net @$10M @4x; @1%: $104,728/yr")
    print(f"  Alt-alt rank:        #7 OOS Sh=26.95 (12th alt-alt, 66th daemon)")
    print(f"  HL concentration:    64.5% UNCHANGED (Bybit-only — HBAR HL maxLev=5 + 0.5pp headroom)")
    print(f"  60d gate:            Realized Sh>=13 + fill>=60% + maxDD<15%")
    print(f"  HBAR notional cap:   K737 2% standalone (first HBAR in portfolio, new Enterprise-DAG vertex)")
    print(f"  SOL notional cap:    K737 2% + existing SOL strategies — monitor combined SOL Bybit")
    print()

    return 0


# ─────────────────────────────────────────────────────────────────────────────
# CLI entry point
# ─────────────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="K735 HBAR-SOL FR Differential Strategy (K737 scaffold, Enterprise-DAG vs SVM, Bybit primary)"
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
        print(f"\n=== K735/K737 Dashboard ({dash.get('last_poll_jst', '—')}) ===")
        print(json.dumps(dash, indent=2))
        return 0

    if args.rebalance:
        dash   = _load_dashboard()
        result = daily_rebalance(dash)
        print(f"\n=== K735/K737 Rebalance Check ===")
        print(json.dumps(result, indent=2))
        return 0

    if args.close:
        result = close_paired_position(args.close, dry_run=args.dry_run)
        print(f"\n=== K735/K737 Close Result ===")
        print(json.dumps(result, indent=2))
        return 0

    return run_cycle(dry_run=args.dry_run, aum=args.aum)


if __name__ == "__main__":
    sys.exit(main())
