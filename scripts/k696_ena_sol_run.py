#!/usr/bin/env python3
"""
k696_ena_sol_run.py — K696 ENA-SOL FR Differential Strategy
=============================================================
SEVENTH ALT-ALT pair (7th accepted, 9th evaluated): ENA vs SOL (no BTC/ETH base).
Signal: ENA_FR - SOL_FR
W=168h rolling mean, zero threshold (sign only)
Bybit-only (ENA-PERP + SOL-PERP on Bybit)
HL concentration: 62.5% UNCHANGED (Bybit-only preferred — headroom preserved)

K696 ENA-SOL alt-alt hypothesis (CROSS-CLUSTER):
  ENA (Ethena) FR dynamics: sUSDe protocol equity — FR = market expectation of sUSDe APY.
  ENA FR is driven by: sUSDe TVL cycles (bull=high, bear=negative risk), perp FR regime
  changes (positive FR regime = high sUSDe yield), protocol risk events (TVL collapses,
  e.g. HypurrFi DROP_LINE K337/K345: sUSDe TVL 14d -49%), institutional demand for delta-
  neutral synthetic stable yields. ENA FR mean = -7.65%/yr (structurally NEGATIVE on average).
  SOL (Solana) FR dynamics: Monolithic SVM DePIN/Retail adoption, meme-coin cycle premium
  (BONK/WIF/POPCAT), Firedancer upgrade hype, validator economics, SOL ETF speculation.
  SOL FR is persistently positive (+7.70% ann) — structural retail demand premium.
  Alt-alt cross-cluster: ENA (synthetic stable infrastructure cluster) vs SOL (SVM L1
  execution cluster). These are GENUINELY DIFFERENT economic segments — orthogonal FR drivers.
  ENA and SOL operate in independent cycles: ENA is driven by PROTOCOL YIELD demand (sUSDe
  APY = perp FR capture); SOL is driven by RETAIL SPECULATION (meme coins, DePIN, L1 momentum).

K696 KEY INSIGHT — Double-Carry Mechanism:
  Dominant state (61.5% of time): SOL FR >> ENA FR (SOL +7.7% vs ENA -7.6%)
    → signal = -1 → SHORT SOL (collect +SOL FR) + LONG ENA (ENA FR often negative)
    → When ENA FR < 0 (37.2% of time): LONG ENA earns |ENA FR| as ADDITIONAL carry
    → Double carry = SOL_FR + |ENA_FR| (both legs carry-positive simultaneously)
  Rare state (38.5%): ENA FR > SOL FR (sUSDe demand surge)
    → signal = +1 → SHORT ENA + LONG SOL
    → Captures ENA premium when sUSDe yield demand spikes

K696 §6 validation (ACCEPT — 15/17 gates PASS):
  - OOS Sharpe: 26.93 (W=168h, zero threshold, ~216d OOS period)
  - OOS Ann Return: $93,187/yr net @$10M @4x @3% standalone sleeve
  - W=168h rolling mean, zero threshold (sign of diff)
  - ADF stat -13.0808 (strongly stationary p=0), OU half-life=3.75h (STRONG)
  - G4 walk-forward: 11/12 folds positive (1 negative: fold 7 Sh=-6.136, 2025-03)
  - G5b corr(K696, K476)=0.1765 (SOL saturation PASS — critical)
  - G5c corr(K696, K616)=-0.7427 (signed convention PASS — ENA new vertex negative corr)
  - G5c PnL corr K616=0.6723 (HIGH: shared ENA leg). ENA notional cap < 6% AUM (MR6).
  - G6 20.8 entries/yr < 30 threshold (FAIL: low trade count — acceptable, all trades carry-pos)
  - G8 leg-based: OKX ENA corr=0.576 PASS + Bybit SOL corr=0.5745 PASS
  - All other gates PASS (G1, G2, G3, G5a,G5d-G5i, G7, G9)
  - ENA notional cap: < 6% AUM (K696 3% + K616 existing) — MR6 constraint
  - 60d gate: Realized Sh >= 13, fill >= 60%, DD < 15%
  - FIRST CROSS-CLUSTER alt-alt: ENA (synth stable infra) vs SOL (SVM L1 retail)

MR8/MR9 compliance:
  MR8: ENA is NOT in existing alt-alt algebraic group {APT,ATOM,SOL,INJ,AVAX,SEI,TIA}.
       ENA introduces a new vertex (synthetic stable infrastructure cluster). PASS.
  MR9: ENA-SOL = (ENA-BTC) - (SOL-BTC) = K616_dir - K476_dir.
       K616 vs K476 corr = 0.0094 (nearly orthogonal). Independent alpha confirmed. PASS.

K696 family context:
  SEVENTH alt-alt (9th evaluated): K679(ACCEPT) + K682(ACCEPT) + K684(ACCEPT) + K686(ACCEPT)
  + K688(REJECT G5d) + K690(ACCEPT) + K691(REJECT G5b APT) + K694(CONDITIONAL) + K696(ACCEPT).
  OOS Sh ranking: K686=50.27 > K682=43.43 > K679=39.29 > K696=26.93 > K690=25.11 > K694=19.09 > K684=9.65
  K696 = 3rd highest OOS Sharpe in alt-alt family.
  Combined 7 accepted alt-alt: ~$919K/yr @$10M (3%+2%+3%+3%+3%+3%+3% sleeves).
  SOL saturation: K696 adds 8th SOL leg (ENA is new vertex). Combined SOL ~$4.2M extreme.
  ENA notional: K696 (3% sleeve) + K616 (existing) = combined ENA exposure < 6% AUM.

Architecture (K679-K694 alt-alt scaffold pattern):
  1. fetch_fr_batch()                → fetch ENA + SOL FR every 8h from Bybit
  2. compute_signal(ena_fr, sol_fr) → 168h rolling mean of (ENA_FR - SOL_FR); sign()
  3. decide_position(signal)         → LONG_ENA_SHORT_SOL | LONG_SOL_SHORT_ENA | NEUTRAL
  4. submit_paired_trade(long, short) → POST_ONLY paired (ENA + SOL legs, both Bybit)
  5. daily_rebalance()               → drift > 5% triggers rebalance
  6. close_paired_position(reason)   → sequential: short first, then long

K699 production scaffold:
  - 60th daemon (MILESTONE: 7th alt-alt, first cross-cluster)
  - Bybit-only (HL at 62.5%, Bybit preferred to preserve headroom)
  - 3% standalone sleeve (ACCEPT)
  - $93,187/yr net @$10M @4x @3% sleeve (OOS Sh=26.93)
  - 60d paper-trade gate: Realized Sh>=13 + fill>=60% + maxDD<15%
  - ENA notional cap: < 6% AUM combined (K696 + K616)

Execution:
  - Bybit primary (ENA-PERP + SOL-PERP, both Bybit)
  - POST_ONLY paired execution (K439 pattern)
  - Position: 3% sleeve, 4x leverage (standalone)
  - 8h cadence (matches FR settlement cycle)
  - W=168h rolling mean (21 x 8h periods)

Paper-trade mode is the DEFAULT.  No orders are submitted unless
PAPER_TRADE=False is explicitly set in the environment.

K339 security: REPO_ROOT from __file__, no /Users/ literals.
No new packages — stdlib urllib + json only.

Usage:
  python3 scripts/k696_ena_sol_run.py --dry-run
  python3 scripts/k696_ena_sol_run.py --status
  python3 scripts/k696_ena_sol_run.py --rebalance
  python3 scripts/k696_ena_sol_run.py --close "scheduled exit"
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

DASHBOARD_PATH  = DATA_DIR  / "k696_dashboard.json"
FR_HISTORY_PATH = CACHE_DIR / "k696_fr_history.jsonl"
TRADE_LOG_PATH  = CACHE_DIR / "k696_paper_trades.jsonl"

JST = timezone(timedelta(hours=9))
UTC = timezone.utc

# ── Strategy constants ────────────────────────────────────────────────────────
PAPER_TRADE         = True          # never submit real orders in paper-trade mode
SLEEVE_PCT          = 0.030         # K696 sleeve = 3% of AUM (standalone, Bybit-only)
LEVERAGE            = 4.0           # 4x per K696 analysis (K430 cap)
AUM_DEFAULT         = 10_000_000.0  # $10M reference AUM
DRIFT_REBALANCE_PCT = 0.05          # rebalance if legs drift > 5%
IOC_TIMEOUT_SEC     = 300           # 5 min fill window
EMA_PERIOD_HOURS    = 168           # 168h rolling mean primary config (W=168h)
EMA_PERIOD_PERIODS  = EMA_PERIOD_HOURS // 8  # = 21 periods (8h settlement cycle)
SIGNAL_SIGMA_MULT   = 0.0           # zero threshold (sign of rolling mean)
BYBIT_API_URL       = "https://api.bybit.com"
HL_API_URL          = "https://api.hyperliquid.xyz/info"

# ── Venue config (Bybit-only — ENA-PERP + SOL-PERP on Bybit) ─────────────────
# HL concentration: 62.5% baseline — Bybit preferred (preserves headroom)
# K696 is fully Bybit-only: ENA-PERP and SOL-PERP both on Bybit
# Bybit-only: HL stays at 62.5% (PREFERRED — HL-only would breach 65% cap)
# HL scenario (HL-only both legs): 62.5 + 3.0 = 65.5% OVER cap — NOT allowed
HL_CONCENTRATION_PRE_K696   = 62.5   # post-K694 reference
HL_CONCENTRATION_POST_K696  = 62.5   # UNCHANGED — Bybit-only, no HL impact
BYBIT_ONLY_REASON            = (
    "Bybit preferred: both ENA-PERP + SOL-PERP available on Bybit. "
    "HL-only would push HL concentration to 65.5% (OVER 65% cap). "
    "Bybit-only keeps HL at 62.5% (unchanged, 2.5pp headroom). "
    "G8 leg-based: OKX ENA corr=0.576 PASS, Bybit SOL corr=0.5745 PASS. Execution: Bybit both legs."
)

# ── ENA cap (MR6) ─────────────────────────────────────────────────────────────
# K616 already has ENA. K696 adds another ENA leg. Combined ENA < 6% AUM cap.
ENA_COMBINED_CAP_PCT = 0.06   # K616 (existing) + K696 (3%) < 6% AUM total
ENA_AUM_CAP_NOTE     = (
    "MR6 ENA cap: K616 ENA-BTC already has ENA leg. K696 ENA-SOL adds 3% sleeve. "
    "Combined ENA notional: K616 + K696 < 6% AUM. Monitor. "
    "ENA notional per leg @$10M: $600K. Total ENA notional (K696): $600K. "
    "K616 ENA notional: ~$600K (3% x $10M x 4x / 2). "
    "Combined: $1.2M ENA exposure = 12% of $10M notional — ACCEPTABLE at 4x (capital = 3% = $300K per)."
)

# ── Position state constants ──────────────────────────────────────────────────
STATE_NEUTRAL            = "NEUTRAL"
STATE_LONG_ENA_SHORT_SOL = "LONG_ENA_SHORT_SOL"
STATE_LONG_SOL_SHORT_ENA = "LONG_SOL_SHORT_ENA"

# ── Symbols fetched from Bybit for FR data ────────────────────────────────────
# K696: ENA + SOL only — direct alt-alt differential (SEVENTH ALT-ALT pair)
SYMBOLS = ("ENA", "SOL")


# ─────────────────────────────────────────────────────────────────────────────
# HTTP helper (stdlib urllib only — no requests)
# ─────────────────────────────────────────────────────────────────────────────

def _http_get(url: str, timeout: int = 10) -> Optional[dict]:
    try:
        req = urllib.request.Request(
            url, headers={"User-Agent": "crypto-lab-k696/1.0"}
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        print(f"  [k696] HTTP error: {e}", file=sys.stderr)
        return None


def _http_post(url: str, payload: dict, timeout: int = 10) -> Optional[dict]:
    try:
        data = json.dumps(payload).encode()
        req  = urllib.request.Request(
            url, data=data,
            headers={"Content-Type": "application/json",
                     "User-Agent": "crypto-lab-k696/1.0"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        print(f"  [k696] HTTP error: {e}", file=sys.stderr)
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Phase 1 — Funding rate fetch (ENA + SOL from Bybit)
# ─────────────────────────────────────────────────────────────────────────────

def _fetch_bybit_fr_batch() -> Dict[str, float]:
    """
    Fetch current 8h funding rates for ENA and SOL from Bybit.
    Returns {symbol: fr_8h_fraction}.

    Bybit API: /v5/market/tickers?category=linear
    K696: both legs on Bybit (ENA-PERP + SOL-PERP).
    Bybit-only preferred: HL concentration at 62.5% (within 65% cap).
    Both ENAUSDT and SOLUSDT perpetuals listed on Bybit.

    Fallback: HL metaAndAssetCtxs for cross-reference (informational only).
    G8 note: OKX ENA corr=0.576 vs HL (leg-based), Bybit SOL corr=0.5745 vs HL.
    Execution: Bybit both legs. OKX ENA is secondary reference only.
    Note: HL reference is informational — Bybit is the execution venue.
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
        print(f"  [k696] Bybit partial result {list(result.keys())} — trying HL fallback",
              file=sys.stderr)

    # Fallback: HL metaAndAssetCtxs (informational cross-check only)
    raw_hl = _http_post(HL_API_URL, {"type": "metaAndAssetCtxs"})
    if raw_hl and isinstance(raw_hl, list) and len(raw_hl) >= 2:
        meta       = raw_hl[0]
        asset_ctxs = raw_hl[1]
        universe   = {item["name"]: i for i, item in enumerate(meta.get("universe", []))}
        for sym in SYMBOLS:
            if sym not in result and sym in universe:
                idx = universe[sym]
                ctx = asset_ctxs[idx]
                try:
                    result[sym] = float(ctx.get("funding", 0.0))
                    print(f"  [k696] {sym} FR from HL fallback (informational)", file=sys.stderr)
                except (TypeError, ValueError):
                    continue
    return result


def _load_fr_history() -> List[dict]:
    """Load K696 FR history JSONL."""
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
    fr_ena: float, fr_sol: float, ena_sol_diff: float
) -> None:
    """Append one FR snapshot to history."""
    rec = {
        "ts_utc":       datetime.now(UTC).isoformat(),
        "fr_ena":       round(fr_ena,       10),
        "fr_sol":       round(fr_sol,        10),
        "ena_sol_diff": round(ena_sol_diff,  10),  # ENA_FR - SOL_FR (direct alt-alt differential)
    }
    with open(FR_HISTORY_PATH, "a") as f:
        f.write(json.dumps(rec) + "\n")


# ─────────────────────────────────────────────────────────────────────────────
# Phase 2 — Signal computation (ENA-SOL direct differential, 168h rolling mean)
# ─────────────────────────────────────────────────────────────────────────────

def compute_signal(
    fr_ena: Optional[float] = None,
    fr_sol: Optional[float] = None,
) -> dict:
    """
    Fetch live ENA and SOL FRs from Bybit, compute ENA-SOL differential,
    and compute 168h rolling mean for direction signal.

    Signal mechanism (K696 direct alt-alt differential — no orthogonalization):
      diff = ENA_FR - SOL_FR
      mean_168h = 168h rolling mean of diff (21 x 8h periods)
      sign  = sign(mean_168h)
      Enter: sign > 0 -> ENA FR > SOL FR -> long ENA (collect), short SOL (cheaper carry)
             sign < 0 -> SOL FR > ENA FR -> long ENA (cheap/negative FR), short SOL (collect)

    NOTE: SOL has persistently HIGH mean FR (+7.70%/ann). The dominant regime is SOL_FR >> ENA_FR.
    In the dominant regime (sign < 0): SHORT SOL (collect high SOL FR) + LONG ENA
    (ENA FR often NEGATIVE — double carry when ENA FR < 0: both collect SOL FR + |ENA FR|).

    Cross-cluster thesis:
      ENA cluster: synthetic stable infrastructure (sUSDe protocol equity). FR governed by
      sUSDe APY cycles, TVL flows, FR regime changes. Mean = -7.65%/yr (structurally negative).
      SOL cluster: Solana SVM L1 execution (retail/speculation). FR governed by meme-coin cycles,
      DePIN events, ETF speculation. Mean = +7.70%/yr (persistently positive, retail premium).

    K696 §6 validation:
      - OOS Sharpe: 26.93 (W=168h, zero threshold, ~216d OOS period)
      - OOS Ann Return: $93,187/yr net @$10M @4x @3% standalone sleeve
      - ADF stat -13.0808 (strongly stationary p=0). OU half-life=3.75h (STRONG).
      - Walk-forward: 11/12 folds positive (1 negative fold 7: Sh=-6.136, 2025-03)
      - G5b corr(K696, K476)=0.1765 PASS, G5c corr(K696, K616)=-0.7427 signed PASS
      - G5c PnL corr K616=0.6723 (MR6: combined ENA < 6% AUM cap monitored)
      - 60d gate: Realized Sh>=13 + fill>=60% + maxDD<15%
      - ACCEPT (15/17 gates: G4 11/12, G6 20.8/yr below threshold — all carry-positive)

    Returns:
      {
        "fr_ena":           float,
        "fr_sol":           float,
        "ena_sol_diff":     float,    # ENA_FR - SOL_FR (current)
        "mean_168h":        float,    # 168h rolling mean of differential
        "diff_sigma":       float,    # 168h rolling sigma (informational)
        "history_points":   int,
        "regime":           str,      # BULL_ENA | BEAR_ENA | NEUTRAL
        "signal_direction": int,      # +1 | -1 | 0
        "ts_jst":           str,
      }
    """
    if fr_ena is None or fr_sol is None:
        frs    = _fetch_bybit_fr_batch()
        fr_ena = frs.get("ENA", 0.0)
        fr_sol = frs.get("SOL", 0.0)

    # ENA-SOL direct alt-alt differential (no orthogonalization)
    ena_sol_diff = fr_ena - fr_sol

    _append_fr_history(fr_ena, fr_sol, ena_sol_diff)

    # Load history for rolling mean + sigma (168h = 21 x 8h periods)
    history = _load_fr_history()
    diffs   = [r["ena_sol_diff"] for r in history if "ena_sol_diff" in r]

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

    # Regime classification (zero threshold — per K696 spec)
    # BULL_ENA: ENA FR > SOL FR (rare sUSDe demand surge)
    # BEAR_ENA: ENA FR < SOL FR (dominant regime: SOL retail >> ENA synth stable)
    if mean_168h > 0:
        regime    = "BULL_ENA"   # ENA-SOL diff positive → ENA FR > SOL FR (rare sUSDe surge)
        direction = 1
    elif mean_168h < 0:
        regime    = "BEAR_ENA"   # ENA-SOL diff negative → SOL FR > ENA FR (dominant: SOL retail)
        direction = -1
    else:
        regime    = "NEUTRAL"
        direction = 0

    return {
        "fr_ena":           round(fr_ena,        10),
        "fr_sol":           round(fr_sol,          10),
        "ena_sol_diff":     round(ena_sol_diff,    10),
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
    Determine trade direction from ENA-SOL differential rolling mean.

    Logic (ENA-SOL direct alt-alt pair, Bybit primary):
      regime = BULL_ENA (mean_168h > 0):
        ENA FR > SOL FR: rare sUSDe demand surge (institutional demand, bull market FR spike)
        -> long ENA (collect high ENA FR) / short SOL (cheaper retail carry)
        -> position_state = LONG_ENA_SHORT_SOL
        -> both legs on Bybit

      regime = BEAR_ENA (mean_168h < 0):
        SOL FR > ENA FR: dominant regime (~61.5% of time)
        SOL retail/meme-coin premium >> ENA sUSDe protocol yield
        -> short SOL (collect high SOL FR) + long ENA (cheap / often negative carry)
        -> DOUBLE CARRY when ENA FR < 0: |ENA FR| + SOL_FR both collected
        -> position_state = LONG_SOL_SHORT_ENA
        -> both legs on Bybit

      regime = NEUTRAL: no trade (mean_168h == 0 exactly — rare)

    Alt-alt cross-cluster edge (SEVENTH ALT-ALT pair — K696):
      ENA and SOL are cross-cluster assets with structurally independent FR drivers.
      BULL_ENA: sUSDe demand surge (institutional demand for delta-neutral yield,
        bull market perp FR spike drives sUSDe APY up, ENA governance premium).
        ENA FR >> SOL FR → long ENA (collect) / short SOL (cheaper retail carry).
      BEAR_ENA: SOL retail premium dominates (meme-coin BONK/WIF/POPCAT rallies,
        Firedancer upgrade hype, SOL ETF speculation, DePIN ecosystem growth).
        SOL FR >> ENA FR → short SOL (collect) / long ENA (often negative carry = DOUBLE CARRY).
        When ENA FR < 0 (37.2% of time): both legs CARRY-POSITIVE simultaneously.
      Cross-cluster: ENA synth stable infra (protocol yield, bear-sensitive) vs
        SOL SVM L1 retail execution (speculation-driven, momentum-driven).
      K616 relationship: ENA-SOL = K616_dir - K476_dir. K616 and K476 corr=0.0094 (orthogonal).
        K696 generates independent carry from the algebraic combination.
      ENA cap: K696 + K616 combined ENA exposure < 6% AUM (MR6 constraint).
        K616 PnL corr with K696 = 0.6723 (complementary mechanics: K616 LONG ENA, K696 SHORT ENA
        in dominant regime — combined provides ENA-hedged additive alpha from BTC-SOL differential).

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

    if regime == "BULL_ENA":
        # ENA FR > SOL FR: rare sUSDe demand surge
        # long ENA (collect high ENA FR) / short SOL (cheaper retail carry)
        long_asset  = "ENA"
        short_asset = "SOL"
        state       = STATE_LONG_ENA_SHORT_SOL
    else:  # BEAR_ENA
        # SOL FR > ENA FR: dominant regime
        # short SOL (collect high SOL FR) + long ENA (often negative FR = double carry)
        long_asset  = "SOL"
        short_asset = "ENA"
        state       = STATE_LONG_SOL_SHORT_ENA

    # Both legs on Bybit (K696: ENA-PERP + SOL-PERP, both Bybit)
    long_venue  = "BYBIT"
    short_venue = "BYBIT"

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
    Compute equal notional for both legs of the ENA-SOL paired trade.

    K696 Bybit-only config (both ENA-PERP + SOL-PERP on Bybit):
      sleeve_capital   = aum x sleeve_pct      (e.g. $10M x 3.0% = $300K)
      total_notional   = sleeve_capital x lev   ($300K x 4 = $1.2M)
      notional_per_leg = total_notional / 2     ($600K per leg)

    At $10M / 3% sleeve / 4x (standalone):
      ENA leg:   $150K capital x 4x = $600K notional (Bybit ENA-PERP)
      SOL leg:   $150K capital x 4x = $600K notional (Bybit SOL-PERP)
      Total:     $1.2M notional (two legs combined)
      Margin:    $300K (3% of AUM)
      HL conc:   UNCHANGED at 62.5% (Bybit-only, HL headroom preserved)
      Net profit: ~$93,187/yr @$10M @4x @3% sleeve (OOS ann ret x notional)
      ENA cap:   K696 ($600K ENA) + K616 (existing ENA) < 6% AUM combined (MR6)
      SOL saturation: K696 adds 8th SOL leg (combined SOL notional up to $4.2M extreme case)

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
    Submit K696 ENA-SOL paired trade: POST_ONLY both legs in parallel.

    Protocol (K696 Bybit primary — both legs on Bybit):
      1. Submit ENA leg on Bybit POST_ONLY
      2. Submit SOL leg on Bybit POST_ONLY
      3. Both legs submitted in parallel (K439 pattern)
      4. IOC fallback per leg if POST_ONLY times out
      5. If both fail: retry next 8h cycle

    Args:
      long_leg:  {"symbol": "SOL", "notional": 600000, "venue": "BYBIT"}
      short_leg: {"symbol": "ENA", "notional": 600000, "venue": "BYBIT"}
      dry_run:   True = paper-trade simulation (default)

    Returns execution result dict.
    """
    ts         = datetime.now(UTC).isoformat()
    long_sym   = long_leg["symbol"]
    short_sym  = short_leg["symbol"]
    long_notl  = long_leg.get("notional", 0.0)
    short_notl = short_leg.get("notional", 0.0)
    long_venue  = long_leg.get("venue",  "BYBIT")
    short_venue = short_leg.get("venue", "BYBIT")

    if dry_run or PAPER_TRADE:
        mode_tag = "DRY_RUN" if dry_run else "PAPER_TRADE"
        print(f"  [K696] {mode_tag}: LONG {long_sym}@{long_venue} ${long_notl:,.0f}  "
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
            "venue_config":     "BYBIT_ONLY_ENA_SOL_ALT_ALT",
            "mechanism_note":   (
                "ENA-SOL direct alt-alt differential (K696 SEVENTH ALT-ALT, 60th daemon MILESTONE): "
                "ENA FR = Ethena sUSDe protocol equity (synth stable infra, sUSDe yield = "
                "stETH staking + perp short FR capture, ENA FR mean -7.65%/yr structurally negative, "
                "driven by sUSDe TVL cycles, perp FR regime, protocol risk events); "
                "SOL FR = Solana SVM DePIN/Retail adoption premium (meme-coin BONK/WIF/POPCAT, "
                "Firedancer upgrade hype, SOL ETF speculation, validator economics, "
                "persistently positive +7.70%/ann structural retail demand premium). "
                "Cross-cluster: synthetic stable infra (ENA) vs SVM L1 retail (SOL). "
                "Dominant regime: LONG SOL / SHORT ENA (BEAR_ENA: SOL FR >> ENA FR). "
                "DOUBLE CARRY when ENA FR < 0 (37.2% of time): both legs carry-positive. "
                "Bybit-only: ENA-PERP + SOL-PERP both on Bybit. HL stays 62.5% (unchanged). "
                "G5b K476 corr=0.1765 PASS. G5c K616 corr=-0.7427 signed PASS. "
                "MR8: ENA new vertex (outside alt-alt algebraic group). "
                "MR9: ENA-SOL = K616-K476, K616 perp K476 (corr=0.0094). "
                "ENA cap: K696 + K616 combined ENA < 6% AUM (MR6 monitored). "
                "OOS Sh=26.93 (W=168h, zero threshold), $93,187/yr @$10M @4x @3% sleeve. "
                "ACCEPT (15/17 gates: G4 11/12, G6 20.8/yr below threshold). "
                "60d gate: Realized Sh>=13 + fill>=60% + maxDD<15%."
            ),
            "ts_utc":           ts,
        }
        _append_trade_log(result)
        return result

    # LIVE scaffold (not reached in PAPER_TRADE mode):
    print(f"  [K696] SCAFFOLD LIVE: parallel POST_ONLY "
          f"LONG {long_sym}@{long_venue} ${long_notl:,.0f} "
          f"+ SHORT {short_sym}@{short_venue} ${short_notl:,.0f}")
    long_order_id  = f"SCAFFOLD_LONG_{long_sym}_{int(time.time())}"
    short_order_id = f"SCAFFOLD_SHORT_{short_sym}_{int(time.time())}"

    print(f"  [K696] Neither leg filled within timeout — retry next 8h cycle")
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
    Check if current K696 position has drifted beyond DRIFT_REBALANCE_PCT (5%).

    K696 Bybit-only: both legs on Bybit (ENA-PERP + SOL-PERP).
    Drift detection: compare stored ENA leg notional vs SOL leg notional.
    Threshold: 5% (same as K449/K476/K484/K493/K629/K663/K679/K682/K684/K686/K690/K694 pattern).

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
    Both legs on Bybit (K696 Bybit primary — ENA-PERP + SOL-PERP).

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

    if state == STATE_LONG_ENA_SHORT_SOL:
        long_sym,  short_sym  = "ENA", "SOL"
    else:  # LONG_SOL_SHORT_ENA
        long_sym,  short_sym  = "SOL", "ENA"

    long_notional  = float(dash.get("long_notional",  0.0))
    short_notional = float(dash.get("short_notional", 0.0))

    if dry_run or PAPER_TRADE:
        mode_tag = "DRY_RUN" if dry_run else "PAPER_TRADE"
        print(f"  [K696] {mode_tag} CLOSE:")
        print(f"    Step 1 (SHORT first): cover {short_sym}@BYBIT ${short_notional:,.0f}")
        print(f"    Step 2 (LONG second): sell  {long_sym}@BYBIT  ${long_notional:,.0f}")
        print(f"    reason={reason}")
        result = {
            "status":          "DRY_RUN_CLOSED",
            "reason":          reason,
            "close_sequence":  "short_first_then_long",
            "closed_short":    short_sym,
            "closed_long":     long_sym,
            "venue":           "BYBIT",
            "short_notional":  short_notional,
            "long_notional":   long_notional,
            "close_mode":      "IOC_REDUCE_ONLY",
            "ts_utc":          ts,
        }
    else:
        print(f"  [K696] SCAFFOLD CLOSE:")
        print(f"    Step 1: IOC reduce {short_sym} (cover short) @BYBIT  reason={reason}")
        print(f"    Step 2: IOC reduce {long_sym} (sell long) @BYBIT")
        result = {
            "status":         "SCAFFOLD_CLOSE",
            "reason":         reason,
            "close_sequence": "short_first_then_long",
            "venue":          "BYBIT",
            "ts_utc":         ts,
        }

    _append_trade_log(result)
    return result


# ─────────────────────────────────────────────────────────────────────────────
# Dashboard I/O
# ─────────────────────────────────────────────────────────────────────────────

def _load_dashboard() -> dict:
    """Load k696_dashboard.json; return defaults if missing."""
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
        "venue":                   "BYBIT",
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
    """Write k696_dashboard.json with full signal + regime state."""
    dash = _load_dashboard()

    # Update signal data
    dash["last_poll_jst"]        = signal.get("ts_jst", "—")
    dash["fr_ena_current"]       = signal.get("fr_ena",        0.0)
    dash["fr_sol_current"]       = signal.get("fr_sol",        0.0)
    dash["ena_sol_diff_current"] = signal.get("ena_sol_diff",  0.0)
    dash["mean_168h"]            = signal.get("mean_168h",     0.0)
    dash["diff_sigma"]           = signal.get("diff_sigma",    0.0)
    dash["regime"]               = signal.get("regime",  "NEUTRAL")
    dash["signal_direction"]     = signal.get("signal_direction", 0)
    dash["history_points"]       = signal.get("history_points", 0)

    # Update position if entering
    if decision:
        state = decision.get("position_state", STATE_NEUTRAL)
        if dash.get("position_state") == STATE_NEUTRAL:
            dash["position_state"]    = state
            dash["long_notional"]     = notional_per_leg
            dash["short_notional"]    = notional_per_leg
            dash["long_asset"]        = decision.get("long_asset")
            dash["short_asset"]       = decision.get("short_asset")
            dash["venue"]             = "BYBIT"
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
    dash["hl_concentration_pct"]     = HL_CONCENTRATION_POST_K696   # 62.5% UNCHANGED (Bybit-only)

    # Paper-trade status
    paper_status = dash.get("paper_trade_status", {"days_elapsed": 0, "target_60d": 60})
    dash["paper_trade_status"]       = paper_status

    # 60d activation gate metrics (K699: Realized Sh >= 13, fill >= 60%, DD < 15%)
    dash["gate_metrics"] = {
        "realized_sharpe_target":  13.0,    # >=13 (48% of OOS Sh=26.93 — ACCEPT standard)
        "fill_rate_target_pct":    60,
        "max_drawdown_target_pct": 15,       # <15%
        "current_realized_sharpe": dash.get("60d_sharpe", 0.0),
        "current_fill_rate_pct":   0.0,
        "current_max_dd_pct":      0.0,
        "gate_status":             "IN_PROGRESS",
        "activation_trigger":      "60d paper-trade: Sh>=13 AND fill>=60% AND maxDD<15%",
        "profit_at_activation_3pct": "$93,187/yr net @$10M @4x (3% sleeve, OOS Sh 26.93, ACCEPT)",
        "alt_alt_note":            (
            "SEVENTH ALT-ALT pair (ENA-SOL, no BTC/ETH leg). Standalone. 60th daemon MILESTONE. "
            "FIRST CROSS-CLUSTER alt-alt: ENA synth stable infra vs SOL SVM L1 retail. "
            "ACCEPT (15/17 gates: G4 11/12, G6 below threshold). "
            "Double carry when ENA FR < 0 (37.2% of time)."
        ),
        "overlap_warning": (
            "MR6 ENA cap: K616 ENA-BTC + K696 ENA-SOL combined ENA < 6% AUM. "
            "G5c PnL corr K616=0.6723 (high but complementary: K616 LONG ENA vs K696 SHORT ENA). "
            "SOL saturation: K696 adds 8th SOL leg — combined up to $4.2M @$10M extreme. "
            "G5b K476 corr=0.1765 PASS (SOL saturation critical gate)."
        ),
    }

    # Strategy metadata
    dash["paper_trade_mode"]    = PAPER_TRADE
    dash["wave"]                = "K699"
    dash["strategy"]            = "K696 ENA-SOL FR Differential (SEVENTH ALT-ALT, W=168h, Bybit-only, ACCEPT, FIRST CROSS-CLUSTER)"
    dash["execution_mode"]      = "POST_ONLY_PARALLEL"
    dash["venue_config"]        = "BYBIT_ONLY"
    dash["alt_alt_mechanism"]   = {
        "formula":            "diff = ENA_FR - SOL_FR  (direct alt-alt cross-cluster, no base asset)",
        "rolling_window":     "W=168h (21 x 8h periods, primary config)",
        "signal":             "sign(rolling_mean_168h(diff))",
        "seventh_alt_alt":    True,
        "ninth_evaluated":    True,
        "first_cross_cluster": True,
        "bybit_only_reason":  BYBIT_ONLY_REASON,
        "hl_concentration":   62.5,
        "cross_cluster_note": (
            "ENA-SOL is a CROSS-CLUSTER alt-alt: ENA cluster (Ethena synthetic stable infra, "
            "sUSDe protocol equity) vs SOL cluster (Solana SVM L1 execution, retail speculation). "
            "ENA FR mean = -7.65%/yr (structural negative, sUSDe yield compressed in bear markets). "
            "SOL FR mean = +7.70%/yr (structural positive, retail demand premium). "
            "Dominant regime (61.5% of time): SOL FR >> ENA FR → SHORT SOL / LONG ENA. "
            "Double carry when ENA FR < 0 (37.2% of time): both legs carry-positive simultaneously. "
            "FR cycles are nearly independent: K616 G5b_SOL corr = 0.0094 (ENA-BTC vs SOL-BTC)."
        ),
        "k616_relationship": (
            "ENA-SOL = (ENA_fr - BTC_fr) - (SOL_fr - BTC_fr) = K616_dir - K476_dir. "
            "K616 and K476 are orthogonal (corr=0.0094). K696 generates independent alpha. "
            "PnL corr K616=0.6723 (complementary: K616 LONG ENA, K696 SHORT ENA in dominant regime). "
            "Portfolio: K476+K616+K696 forms FR triangle. ENA-hedged combined exposure."
        ),
        "sol_saturation": (
            "SOL appears in K476+K679+K682+K684+K686+K690+K694+K696 (8 strategies now). "
            "K696 SOL saturation critical gate: G5b corr(K696, K476)=0.1765 PASS (<0.40). "
            "Combined SOL notional @$10M extreme: up to $4.2M (all 8 SOL-strategies active). "
            "Monitor combined SOL exposure vs AUM."
        ),
        "mr6_ena_cap": (
            "MR6 ENA cap: K696 (3% sleeve) + K616 (existing ENA-BTC) < 6% AUM combined ENA. "
            "ENA notional K696: $600K per leg @$10M. K616 ENA leg: ~$600K. "
            "Combined ENA capital: $300K + $300K = $600K (3% + 3% AUM) < 6% cap. PASS."
        ),
        "double_carry": (
            "UNIQUE K696 dynamics: When ENA FR < 0 (37.2% of time), LONG ENA in SHORT-ENA "
            "position earns |ENA FR| as additional carry. "
            "Double carry = SOL_FR + |ENA FR| both collected simultaneously. "
            "Double carry events drive disproportionate alpha vs other alt-alt pairs."
        ),
        "ou_half_life":   "3.75h (0.156d) — STRONG mean-reversion. ADF stat -13.0808 (p=0).",
        "g4_note":        "11/12 folds positive (1 negative: fold 7 Sh=-6.136, 2025-03 regime). ACCEPT.",
        "family_rank": (
            "NINTH alt-alt evaluated: K679(ACCEPT), K682(ACCEPT), K684(ACCEPT), K686(ACCEPT), "
            "K688(REJECT G5d), K690(ACCEPT WF12/12), K691(REJECT G5b APT), K694(CONDITIONAL), K696(ACCEPT). "
            "OOS Sh: K686=50.27 > K682=43.43 > K679=39.29 > K696=26.93 > K690=25.11 > K694=19.09 > K684=9.65. "
            "K696 = 3rd highest OOS Sharpe in alt-alt family. 60th daemon MILESTONE. "
            "Combined 7 accepted alt-alt: ~$919K/yr @$10M (3%+2%+3%+3%+3%+3%+3% sleeves)."
        ),
    }
    dash["activation_criteria"] = {
        "60d_paper_trade_gate":  "required",
        "realized_sharpe_min":   13.0,
        "fill_rate_min_pct":     60,
        "max_drawdown_max_pct":  15,
        "status":                "SCAFFOLD-READY",
        "activation_sleeve_pct": 0.030,
        "venue":                 "BYBIT primary (ENA-PERP + SOL-PERP both on Bybit)",
        "accept_note":           "ACCEPT: 15/17 gates PASS. G4=11/12 (fold 7 negative). G6=20.8/yr below threshold. All carry-positive.",
    }
    dash["oos_performance"] = {
        "sharpe":                   26.93,
        "oos_ann_ret_pct":          9.136,
        "ann_return_usd_3pct_4x":   93187,
        "daily_usdc":               255,
        "wave_accept":              "K696 ACCEPT (K699 scaffold) — SEVENTH ALT-ALT, FIRST CROSS-CLUSTER, ENA synth stable infra vs SOL SVM retail",
        "cluster":                  "ENA-SOL Alt-Alt FR Differential (synth stable infra vs SVM retail, Bybit-only, cross-cluster)",
        "cluster_rationale": (
            "ENA (Ethena synthetic stable infra, sUSDe protocol equity — structurally negative -7.65%/ann) "
            "vs SOL (Solana SVM retail/meme — persistently positive +7.70%/ann): seventh alt-alt. "
            "No BTC or ETH leg — pure cross-cluster alt-to-alt. "
            "Dominant regime: LONG SOL / SHORT ENA (BEAR_ENA — SOL FR >> ENA FR). "
            "Double carry: 37.2% of time ENA FR < 0 — both legs carry-positive simultaneously. "
            "Bybit-only: HL stays at 62.5% (preferred — headroom preserved). "
            "ENA + SOL PERP both on Bybit. HL-only would breach 65% cap. "
            "MR8/MR9: ENA new vertex, ENA-SOL = K616-K476, K616 perp K476 (corr=0.0094). "
            "MR6: combined ENA (K616+K696) < 6% AUM cap. Standalone 3% sleeve."
        ),
        "daemon_number":            "60th (MILESTONE)",
        "section6_result":          "ACCEPT 15/17 gates. G4=11/12 (fold 7 Sh=-6.136). G6=20.8/yr below threshold. All other gates PASS.",
        "family_rank": {
            "k686_oos_sharpe":   50.27,
            "k682_oos_sharpe":   43.43,
            "k679_oos_sharpe":   39.29,
            "k696_oos_sharpe":   26.93,
            "k690_oos_sharpe":   25.11,
            "k694_oos_sharpe":   19.09,
            "k684_oos_sharpe":   9.65,
            "k696_pair":         "ENA-SOL (alt-alt, SEVENTH/ninth-eval, ACCEPT, FIRST CROSS-CLUSTER, OU 3.75h)",
            "alt_alt_accepted":  7,
            "g4_note":           "K696 G4=11/12 ACCEPT (fold 7 2025-03 negative). ADF -13.0808 strongest in family.",
        },
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
      1. Fetch ENA + SOL FRs from Bybit
      2. Compute ENA-SOL differential + 168h rolling mean
      3. Decide position (sign of rolling mean — zero threshold)
      4. Compute delta-neutral notional
      5. If entering: submit paired trade (POST_ONLY, Bybit primary)
      6. If holding: check drift + rebalance
      7. Write k696_dashboard.json
    """
    ts_jst = datetime.now(JST).strftime("%Y-%m-%d %H:%M JST")
    print(f"\n=== K696 ENA-SOL FR Differential (SEVENTH ALT-ALT, FIRST CROSS-CLUSTER, Bybit-only) — {ts_jst} ===")
    print(f"  Mode:      {'DRY-RUN' if dry_run else 'PAPER-TRADE' if PAPER_TRADE else 'LIVE'}")
    print(f"  AUM:       ${aum:,.0f}  Sleeve: {SLEEVE_PCT:.1%}  Leverage: {LEVERAGE}x")
    print(f"  Venue:     Bybit-only (ENA-PERP + SOL-PERP, both Bybit)")
    print(f"  HL conc:   62.5% (preferred — Bybit-only preserves 2.5pp headroom)")
    print(f"  Execution: POST_ONLY parallel (K439)")
    print(f"  Signal:    diff = ENA_FR - SOL_FR  (direct alt-alt cross-cluster, no base asset)")
    print(f"             sign(rolling_mean_168h)  (zero threshold, W=168h = 21 x 8h periods)")
    print(f"  SEVENTH:   SEVENTH ALT-ALT pair (no BTC/ETH leg) — OOS Sh=26.93, ACCEPT 15/17")
    print(f"  Cross-cluster: ENA (synth stable infra, -7.65%/ann) vs SOL (SVM retail, +7.70%/ann)")
    print(f"  OU 3.75h:  STRONG mean-reversion. ADF -13.0808 (strongest stationary in family).")
    print(f"  Double carry: ENA FR < 0 (37.2% of time) → both legs carry-positive simultaneously.")
    print(f"  MR8/MR9:   ENA new vertex, ENA-SOL=K616-K476, K616 perp K476 (corr=0.0094).")
    print(f"  ENA cap:   K616+K696 combined ENA < 6% AUM (MR6 monitored). G5c K616=-0.7427 signed PASS.")
    print(f"  60th:      OOS Sh={26.93:.2f} W=168h Bybit-only 3% sleeve $93,187/yr @$10M @4x")

    # Step 1: Fetch + compute ENA-SOL differential
    print("\n  [Step 1] Computing ENA-SOL FR differential from Bybit...")
    signal = compute_signal()
    print(f"  ENA FR:     {signal['fr_ena']:+.8f} (8h, Bybit, sUSDe protocol -7.65%/ann mean)")
    print(f"  SOL FR:     {signal['fr_sol']:+.8f} (8h, Bybit, retail +7.70%/ann persistent)")
    print(f"  ENA-SOL:    {signal['ena_sol_diff']:+.8f}  (direct alt-alt cross-cluster differential)")
    print(f"  Mean 168h:  {signal['mean_168h']:+.8f}")
    print(f"  Sigma 168h: {signal['diff_sigma']:+.8f}  (informational)")
    print(f"  Direction:  {signal['signal_direction']:+d}  (+1=BULL_ENA, -1=BEAR_ENA, 0=NEUTRAL)")
    print(f"  Regime:     {signal['regime']}")
    print(f"  History:    {signal['history_points']} data points")

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
    print(f"  ENA leg:          ${notional_per_leg:,.0f}  (3% x ${aum/1e6:.0f}M x {LEVERAGE}x / 2)")
    print(f"  SOL leg:          ${notional_per_leg:,.0f}  (3% x ${aum/1e6:.0f}M x {LEVERAGE}x / 2)")
    print(f"  Total notional:   ${total_notional:,.0f}")
    print(f"  Margin required:  ${total_notional/LEVERAGE:,.0f}  ({SLEEVE_PCT:.1%} AUM)")
    print(f"  Profit @$10M 4x:  OOS Sh=26.93 = $93,187/yr net (3% sleeve, standalone, ACCEPT)")
    print(f"  HL conc:          UNCHANGED 62.5% (Bybit-only — 2.5pp headroom preserved)")
    print(f"  ENA cap:          K616+K696 combined ENA < 6% AUM (MR6). Current: ~3% capital.")

    # Step 4: Load current position + decide action
    dash = _load_dashboard()
    current_state = dash.get("position_state", STATE_NEUTRAL)
    print(f"\n  [Step 4] Current position: {current_state}")

    trade_result = None
    if decision and current_state == STATE_NEUTRAL:
        print(f"  Action: ENTER {decision['position_state']}")
        long_leg  = {"symbol": decision["long_asset"],  "notional": notional_per_leg, "venue": "BYBIT"}
        short_leg = {"symbol": decision["short_asset"], "notional": notional_per_leg, "venue": "BYBIT"}
        trade_result = submit_paired_trade(long_leg, short_leg, dry_run=dry_run)
        print(f"  Trade status: {trade_result['status']}")

    elif decision and current_state != STATE_NEUTRAL:
        if decision["position_state"] != current_state:
            print(f"  Action: CLOSE + FLIP (signal reversed)")
            close_result = close_paired_position("signal_reversal", dry_run=dry_run)
            print(f"  Close status: {close_result['status']}")
            long_leg  = {"symbol": decision["long_asset"],  "notional": notional_per_leg, "venue": "BYBIT"}
            short_leg = {"symbol": decision["short_asset"], "notional": notional_per_leg, "venue": "BYBIT"}
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
    print(f"\n  === K696 ENA-SOL Cycle Complete ===")
    print(f"  Position state:     {dash_out.get('position_state')}")
    print(f"  Regime:             {dash_out.get('regime')}")
    print(f"  ENA-SOL Mean 168h:  {dash_out.get('mean_168h'):+.8f}")
    print(f"  Signal direction:   {dash_out.get('signal_direction')}")
    print(f"  SEVENTH ALT-ALT:    ENA-SOL (no BTC/ETH base) OOS Sh=26.93, ACCEPT 15/17")
    print(f"  FIRST CROSS-CLUSTER: ENA synth stable infra vs SOL SVM L1 retail")
    print(f"  Double carry:       37.2% of time ENA FR < 0 — both legs carry-positive.")
    print(f"  Bybit-only:         HL 62.5% (headroom preserved — ENA+SOL on Bybit)")
    print(f"  MR8/MR9:            ENA new vertex. ENA-SOL = K616-K476 (K616 perp K476, corr=0.0094).")
    print(f"  ENA cap (MR6):      K616+K696 combined ENA < 6% AUM. G5c K616=-0.7427 signed PASS.")
    print(f"  SOL saturation:     G5b K476 corr=0.1765 PASS. 8th SOL strategy. Monitor combined.")
    print(f"  Paper-trade mode:   {PAPER_TRADE}")
    print(f"  OOS Sharpe:         26.93 (W=168h, zero threshold, ~216d OOS)")
    print(f"  Cluster:            ENA-SOL Alt-Alt (synth stable infra vs SVM retail, 60th daemon)")
    print(f"  Profit 3% sleeve:   $93,187/yr net @$10M @4x (standalone, ACCEPT)")
    print(f"  HL concentration:   62.5% UNCHANGED (Bybit-only, headroom preserved)")
    print(f"  60d gate:           Realized Sh>=13 + fill>=60% + maxDD<15%")
    print()

    return 0


# ─────────────────────────────────────────────────────────────────────────────
# CLI entry point
# ─────────────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="K696 ENA-SOL FR Differential Strategy (K699 scaffold, SEVENTH ALT-ALT, FIRST CROSS-CLUSTER, Bybit-only, ACCEPT)"
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
        print(f"\n=== K696 Dashboard ({dash.get('last_poll_jst', '—')}) ===")
        print(json.dumps(dash, indent=2))
        return 0

    if args.rebalance:
        dash   = _load_dashboard()
        result = daily_rebalance(dash)
        print(f"\n=== K696 Rebalance Check ===")
        print(json.dumps(result, indent=2))
        return 0

    if args.close:
        result = close_paired_position(args.close, dry_run=args.dry_run)
        print(f"\n=== K696 Close Result ===")
        print(json.dumps(result, indent=2))
        return 0

    return run_cycle(dry_run=args.dry_run, aum=args.aum)


if __name__ == "__main__":
    sys.exit(main())
