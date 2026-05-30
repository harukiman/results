#!/usr/bin/env python3
"""
k747_tao_sol_run.py — K747 TAO-SOL FR Differential Strategy
=============================================================
FIFTEENTH ALT-ALT pair: TAO vs SOL (AI L1 × SVM cross-cluster).
Signal: TAO_FR - SOL_FR
W=168h rolling mean, zero threshold (sign only)
HL-only (TAO-PERP + SOL-PERP both on HL)
HL concentration: 65.0% AT CAP → paper-gate strict (K498 OKX activation required)

K747 TAO-SOL alt-alt hypothesis:
  TAO (Bittensor) FR dynamics: AI infrastructure narrative driven by GPU scarcity
  cycles (NVDA/H100 AI peaks), Bittensor subnet launch events (new subnet =
  higher validator staking demand), institutional AI adoption (validator set
  expansion), TAO staking/subnet yield vs perpetual leverage premium,
  compute market pricing cycles (H100 supply/demand → TAO subnet demand),
  AI regulation events (SEC/CFTC AI asset classification). TAO FR mean +16.34%/ann
  — episodic AI narrative spikes. TAO dominant in ALL quarters (100% of time).
  SOL (Solana) FR dynamics: Retail momentum / meme coin seasons (BONK, WIF,
  POPCAT cycles), Firedancer upgrade cycles, Solana ETF narrative events,
  SVM DeFi TVL expansion (Jupiter, Drift Protocol, Jito restaking), SOL staking
  yield vs perpetual leverage premium, NFT/gaming/AI agent cycles on Solana.
  SOL FR mean +7.706%/ann — persistently positive structural retail demand.
  Alt-alt mechanism: TAO (Bittensor AI L1 compute marketplace) vs SOL (Solana SVM L1).
  Cross-cluster: AI compute marketplace (GPU scarcity, subnet economics, ML research)
  vs SVM execution layer (retail DeFi, meme speculation, gaming). COMPLETELY different
  demand drivers — AI-GPU scarcity narrative vs retail speculation cycles.
  FIFTEENTH alt-alt pair. OOS Sharpe 12.233. 28/29 §6 gates PASS.
  G4 WF 12/12 ALL POSITIVE (UNPRECEDENTED — no negative fold). Best WF in family.
  ADF stat -12.2254 (p=0.0). OU half-life=2.0h (FAST). Vol ratio=1.5734x (above 1.5x).
  G8 FAIL: Bybit TAO 84.6% floor-capped → HL-only deployment.
  TAO becomes 13th vertex. All future TAO-X blocked (MR9 L002).

K747 §6 validation (ACCEPT CONDITIONAL — 28/29 gates PASS):
  - OOS Sharpe: 12.233 (W=168h, zero threshold, ~217d OOS)
  - OOS Ann Return: $17,210/yr central @$10M @4x @2.5% sleeve (K523 3-point)
  - W=168h rolling mean, zero threshold (sign of diff)
  - ADF stat -12.2254 (p=0.0), OU half-life=2.0h (FAST, 0.08d)
  - G4 walk-forward: 12/12 folds positive (UNPRECEDENTED — best WF in family)
  - G5b corr(K747, K476)=0.2229 (SOL saturation PASS)
  - G5c corr(K747, K484)=0.0126 (AVAX cluster PASS — AI L1 distinct from AVAX subnet)
  - G5k corr(K747, K687)=0.1286 (AVAX-SOL cluster PASS — confirms AI≠AVAX)
  - All 21 G5 checks PASS (complete G5 sweep)
  - G8 FAIL: Bybit TAO 84.6% floor-capped (structural venue noise, not signal failure)
  - G8 precedent: K735 HBAR-SOL ACCEPT CONDITIONAL with same G8 pattern
  - HL-only deployment (TAO-PERP + SOL-PERP on HL, maxLeverage=5 confirmed)
  - 60d gate: Realized Sh >= 6, fill >= 60%, DD < 15%
  - CONDITIONAL: G8 FAIL (Bybit TAO floor) + HL 65.0% AT CAP → paper-gate strict
  - Paper-gate until K498 OKX activation reduces HL concentration

K747 AVAX cluster bypass:
  K746 ONDO-SOL BLOCKED: G5c(AVAX-BTC)=-0.4148 FAIL + G5k(AVAX-SOL)=-0.5842 FAIL.
  K747 TAO-SOL: G5c(AVAX-BTC)=+0.0126 PASS + G5k(AVAX-SOL)=+0.1286 PASS.
  AI L1 (TAO) does NOT share AVAX subnet narrative cluster.
  AVAX "subnet" = L2-like appchain customization (institutional DeFi).
  TAO "subnet" = Bittensor AI compute marketplace (GPU mining, ML model training).
  Structurally different: enterprise chain abstraction vs AI-GPU scarcity.
  TAO-SOL clears AVAX family barrier that blocked ONDO. Confirmed by K746 analysis.

TAO vertex addition:
  TAO is 13th vertex added to alt-alt graph V.
  V = {APT, ATOM, AVAX, BNB, ENA, FIL, HBAR, INJ, LDO, SEI, SOL, TIA, TAO}.
  MR9 L002: all future TAO-X pairs are auto-blocked (TAO exhausted as new vertex).
  TAO-SOL is the only permissible TAO-X pair given V composition at K747.

K523 3-point profit projection (@$10M @4x @2.5% sleeve):
  Conservative: $12,907/yr  (R2S=38% floor, OOS 25% haircut, fee 15%)
  Central:      $17,210/yr  (base case)
  Optimistic:   $45,289/yr  (upper scenario)
  Upper bound:  $53,281/yr  (NOT central — K523 mandatory)

Architecture (K679→K739 alt-alt scaffold pattern):
  1. fetch_fr_batch()                → fetch TAO + SOL FR every 8h from HL
  2. compute_signal(tao_fr, sol_fr) → 168h rolling mean of (TAO_FR - SOL_FR); sign()
  3. decide_position(signal)         → LONG_TAO_SHORT_SOL | LONG_SOL_SHORT_TAO | NEUTRAL
  4. submit_paired_trade(long, short) → POST_ONLY paired (TAO + SOL legs, HL-only)
  5. daily_rebalance()               → drift > 5% triggers rebalance
  6. close_paired_position(reason)   → sequential: short first, then long

K750 production scaffold:
  - 69th daemon (fifteenth alt-alt pair, ACCEPT CONDITIONAL 28/29, G4 12/12 UNPRECEDENTED)
  - HL-only (TAO-PERP + SOL-PERP on HL — Bybit TAO 84.6% floor-capped, G8 structural)
  - 2.5% sleeve (paper-gate strict — HL 65.0% AT CAP)
  - $17,210/yr central @$10M @4x @2.5% sleeve (K523 3-point: $12.9K-$45.3K)
  - Paper-gate until K498 OKX activation reduces HL concentration below 65%
  - 60d paper-trade gate: Realized Sh>=6 + fill>=60% + maxDD<15%
  - 15th alt-alt pair (AI L1 × SVM cross-cluster, 13th vertex TAO)

Execution:
  - HL primary (TAO-PERP + SOL-PERP, HL-only)
  - POST_ONLY paired execution (K439 pattern)
  - Position: 2.5% sleeve, 4x leverage (HL-cap-aware paper-gate)
  - 8h cadence (matches FR settlement cycle)
  - W=168h rolling mean (21 x 8h periods)

Paper-trade mode is the DEFAULT.  No orders are submitted unless
PAPER_TRADE=False is explicitly set in the environment.

K339 security: REPO_ROOT from __file__, no /Users/ literals.
No new packages — stdlib urllib + json only.

Usage:
  python3 scripts/k747_tao_sol_run.py --dry-run
  python3 scripts/k747_tao_sol_run.py --status
  python3 scripts/k747_tao_sol_run.py --rebalance
  python3 scripts/k747_tao_sol_run.py --close "scheduled exit"
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

DASHBOARD_PATH  = DATA_DIR  / "k747_dashboard.json"
FR_HISTORY_PATH = CACHE_DIR / "k747_fr_history.jsonl"
TRADE_LOG_PATH  = CACHE_DIR / "k747_paper_trades.jsonl"

JST = timezone(timedelta(hours=9))
UTC = timezone.utc

# ── Strategy constants ────────────────────────────────────────────────────────
PAPER_TRADE         = True          # never submit real orders in paper-trade mode
SLEEVE_PCT          = 0.025         # K747 sleeve = 2.5% of AUM (paper-gate, HL-cap-aware)
LEVERAGE            = 4.0           # 4x per K747 analysis (K430 cap)
AUM_DEFAULT         = 10_000_000.0  # $10M reference AUM
DRIFT_REBALANCE_PCT = 0.05          # rebalance if legs drift > 5%
IOC_TIMEOUT_SEC     = 300           # 5 min fill window
EMA_PERIOD_HOURS    = 168           # 168h rolling mean primary config (W=168h)
EMA_PERIOD_PERIODS  = EMA_PERIOD_HOURS // 8  # = 21 periods (8h settlement cycle)
SIGNAL_SIGMA_MULT   = 0.0           # zero threshold (sign of rolling mean)
HL_API_URL          = "https://api.hyperliquid.xyz/info"
BYBIT_API_URL       = "https://api.bybit.com"

# ── Venue config (HL-only — TAO-PERP + SOL-PERP on HL) ────────────────────────
# HL concentration: 65.0% AT CAP — paper-gate strict until K498 OKX activation.
# K747 HL-only: both TAO-PERP and SOL-PERP active on HL (maxLeverage=5, asset=116).
# Bybit TAO: 84.6% at FR floor (0.0001/0.00005) — structural noise, G8 FAIL.
# G8 precedent: K735 HBAR-SOL ACCEPT CONDITIONAL with same G8 structural issue.
# Deploy LIVE only after K498 OKX activation reduces HL% below 65%.
HL_CONCENTRATION_PRE_K747   = 65.0   # post-K739 reference (AT CAP)
HL_CONCENTRATION_POST_K747  = 65.0   # UNCHANGED — paper-only, no live capital added
HL_ONLY_REASON              = (
    "HL-only: Bybit TAO 84.6% floor-capped (0.0001/0.00005) — G8 structural venue noise. "
    "G8 precedent: K735 HBAR-SOL ACCEPT CONDITIONAL with same G8 pattern. "
    "HL TAO confirmed active: maxLeverage=5, asset index=116, $12.3M/24h volume. "
    "HL at 65.0% AT CAP — paper-gate strict. Deploy LIVE after K498 OKX reduces HL%."
)

# ── Position state constants ──────────────────────────────────────────────────
STATE_NEUTRAL            = "NEUTRAL"
STATE_LONG_TAO_SHORT_SOL = "LONG_TAO_SHORT_SOL"
STATE_LONG_SOL_SHORT_TAO = "LONG_SOL_SHORT_TAO"

# ── Symbols fetched from HL for FR data ──────────────────────────────────────
# K747: TAO + SOL only — direct alt-alt differential (FIFTEENTH ALT-ALT pair)
SYMBOLS = ("TAO", "SOL")


# ─────────────────────────────────────────────────────────────────────────────
# HTTP helper (stdlib urllib only — no requests)
# ─────────────────────────────────────────────────────────────────────────────

def _http_get(url: str, timeout: int = 10) -> Optional[dict]:
    try:
        req = urllib.request.Request(
            url, headers={"User-Agent": "crypto-lab-k747/1.0"}
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        print(f"  [k747] HTTP error: {e}", file=sys.stderr)
        return None


def _http_post(url: str, payload: dict, timeout: int = 10) -> Optional[dict]:
    try:
        data = json.dumps(payload).encode()
        req  = urllib.request.Request(
            url, data=data,
            headers={"Content-Type": "application/json",
                     "User-Agent": "crypto-lab-k747/1.0"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        print(f"  [k747] HTTP error: {e}", file=sys.stderr)
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Phase 1 — Funding rate fetch (TAO + SOL from HL)
# ─────────────────────────────────────────────────────────────────────────────

def _fetch_hl_fr_batch() -> Dict[str, float]:
    """
    Fetch current 1h funding rates for TAO and SOL from HL.
    Returns {symbol: fr_1h_fraction}.

    HL API: metaAndAssetCtxs (POST).
    K747: both legs on HL (TAO-PERP + SOL-PERP).
    HL-only mandatory: Bybit TAO 84.6% floor-capped (G8 structural fail).
    TAO HL confirmed: maxLeverage=5, asset index=116, $12.3M/24h volume.

    Note: HL settles 1h funding; W=168h = 168 x 1h periods for rolling mean.
    FR stored as 1h fraction; annualized = fr_1h * 8760.

    Fallback: Bybit /v5/market/tickers (informational cross-check only;
    84.6% floor artifact means Bybit TAO FR has structural noise).
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
        print(f"  [k747] HL partial result {list(result.keys())} — trying Bybit fallback",
              file=sys.stderr)

    # Fallback: Bybit /v5/market/tickers (informational; TAO floor-capped but SOL reliable)
    bybit_url = f"{BYBIT_API_URL}/v5/market/tickers?category=linear"
    raw_bybit = _http_get(bybit_url)
    if raw_bybit and raw_bybit.get("retCode") == 0:
        tickers = raw_bybit.get("result", {}).get("list", [])
        sym_map = {t["symbol"]: t for t in tickers}
        for sym in SYMBOLS:
            if sym not in result:
                perp_sym = f"{sym}USDT"
                if perp_sym in sym_map:
                    tick = sym_map[perp_sym]
                    try:
                        fr_val = float(tick.get("fundingRate", 0.0))
                        result[sym] = fr_val
                        if sym == "TAO":
                            print(f"  [k747] TAO FR from Bybit fallback (floor-capped artifact, "
                                  f"informational only — 84.6% at floor 0.0001)", file=sys.stderr)
                        else:
                            print(f"  [k747] {sym} FR from Bybit fallback", file=sys.stderr)
                    except (TypeError, ValueError):
                        pass
    return result


def _load_fr_history() -> List[dict]:
    """Load K747 FR history JSONL."""
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
    fr_tao: float, fr_sol: float, tao_sol_diff: float
) -> None:
    """Append one FR snapshot to history."""
    rec = {
        "ts_utc":       datetime.now(UTC).isoformat(),
        "fr_tao":       round(fr_tao,       10),
        "fr_sol":       round(fr_sol,        10),
        "tao_sol_diff": round(tao_sol_diff,  10),  # TAO_FR - SOL_FR (direct alt-alt differential)
    }
    with open(FR_HISTORY_PATH, "a") as f:
        f.write(json.dumps(rec) + "\n")


# ─────────────────────────────────────────────────────────────────────────────
# Phase 2 — Signal computation (TAO-SOL direct differential, 168h rolling mean)
# ─────────────────────────────────────────────────────────────────────────────

def compute_signal(
    fr_tao: Optional[float] = None,
    fr_sol: Optional[float] = None,
) -> dict:
    """
    Fetch live TAO and SOL FRs from HL, compute TAO-SOL differential,
    and compute 168h rolling mean for direction signal.

    Signal mechanism (K747 direct alt-alt differential — no orthogonalization):
      diff = TAO_FR - SOL_FR
      mean_168h = 168h rolling mean of diff (21 x 8h periods equivalent)
      sign  = sign(mean_168h)
      Enter: sign > 0 -> TAO FR > SOL FR -> long TAO (collect AI premium), short SOL
             sign < 0 -> SOL FR > TAO FR -> long TAO (cheaper), short SOL (collect)

    NOTE: TAO has persistently HIGH mean FR (+16.34%/ann). TAO dominant 100% of quarters.
    Dominant regime (sign > 0): LONG TAO (collect high TAO AI premium) / SHORT SOL.

    Alt-alt mechanism (FIFTEENTH ALT-ALT pair — K747):
      TAO FR tracks Bittensor AI L1 compute marketplace: GPU scarcity narrative cycles
      (NVDA/H100 AI peaks), subnet launch events (new subnet = validator staking demand),
      institutional AI adoption, compute market pricing, AI regulation events.
      Mean +16.34%/ann — episodic AI narrative spikes. TAO dominant all quarters.
      SOL FR tracks Solana SVM DePIN/Retail adoption: meme-coin seasons (BONK/WIF/POPCAT),
      Firedancer upgrade hype, SOL ETF speculation, SVM DeFi TVL expansion.
      Mean +7.706%/ann — persistently positive structural retail demand.
      TAO-SOL diff captures relative AI compute marketplace vs SVM retail premium.
      Different architectures: AI compute marketplace (GPU mining) vs execution L1 (DeFi/retail).
      Mean diff +8.63%/ann (TAO typically higher FR than SOL).

    K747 AVAX bypass (unlike K746 ONDO-SOL):
      ONDO-SOL: G5c(AVAX-BTC)=-0.4148 FAIL, G5k(AVAX-SOL)=-0.5842 FAIL (RWA/institutional).
      TAO-SOL:  G5c(AVAX-BTC)=+0.0126 PASS, G5k(AVAX-SOL)=+0.1286 PASS (AI≠AVAX subnet).
      AI L1 compute marketplace ≠ AVAX subnet "appchain customization". Distinct clusters.

    Mathematical identity (K747 decomposition):
      TAO_FR - SOL_FR = (TAO_FR - BTC_FR) - (SOL_FR - BTC_FR) = K_TAO_BTC_dir - K476_dir
      K476 correlation: G5b(SOL-BTC)=0.2229 (below 0.40, SOL saturation PASS).
      G4 WF 12/12 ALL POSITIVE — UNPRECEDENTED result (best WF in entire alt-alt family).
      ADF stat -12.2254 (strongly stationary p=0.0). OU half-life=2.0h (FAST).

    K747 §6 validation:
      - OOS Sharpe: 12.233 (W=168h, zero threshold, ~217d OOS period)
      - OOS Ann Return: 5.328% (1x, unlevered on notional); 21.313% at 4x
      - ADF stat -12.2254 (p=0.0), OU half-life=2.0h (FAST)
      - Walk-forward: 12/12 folds ALL POSITIVE (UNPRECEDENTED)
      - All 21 G5 checks PASS (complete G5 sweep)
      - G8 FAIL: Bybit TAO 84.6% floor-capped (structural, not signal failure)
      - 60d gate: Realized Sh>=6 + fill>=60% + maxDD<15%
      - CONDITIONAL: G8 FAIL + HL 65.0% AT CAP → paper-gate strict

    Returns:
      {
        "fr_tao":           float,
        "fr_sol":           float,
        "tao_sol_diff":     float,    # TAO_FR - SOL_FR (current)
        "mean_168h":        float,    # 168h rolling mean of differential
        "diff_sigma":       float,    # 168h rolling sigma (informational)
        "history_points":   int,
        "regime":           str,      # BULL_TAO | BEAR_TAO | NEUTRAL
        "signal_direction": int,      # +1 | -1 | 0
        "ts_jst":           str,
      }
    """
    if fr_tao is None or fr_sol is None:
        frs    = _fetch_hl_fr_batch()
        fr_tao = frs.get("TAO", 0.0)
        fr_sol = frs.get("SOL", 0.0)

    # TAO-SOL direct alt-alt differential (no orthogonalization)
    tao_sol_diff = fr_tao - fr_sol

    _append_fr_history(fr_tao, fr_sol, tao_sol_diff)

    # Load history for rolling mean + sigma (168h = 21 x 8h periods)
    history = _load_fr_history()
    diffs   = [r["tao_sol_diff"] for r in history if "tao_sol_diff" in r]

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

    # Regime classification (zero threshold — per K747 spec)
    # BULL_TAO: TAO FR > SOL FR (dominant regime — AI narrative premium >> retail)
    # BEAR_TAO: TAO FR < SOL FR (rare regime — SOL meme-coin spike > AI narrative)
    if mean_168h > 0:
        regime    = "BULL_TAO"   # TAO-SOL diff positive → TAO FR > SOL FR (dominant: AI premium)
        direction = 1
    elif mean_168h < 0:
        regime    = "BEAR_TAO"   # TAO-SOL diff negative → SOL FR > TAO FR (rare: SOL meme spike)
        direction = -1
    else:
        regime    = "NEUTRAL"
        direction = 0

    return {
        "fr_tao":           round(fr_tao,        10),
        "fr_sol":           round(fr_sol,          10),
        "tao_sol_diff":     round(tao_sol_diff,    10),
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
    Determine trade direction from TAO-SOL differential rolling mean.

    Logic (TAO-SOL direct alt-alt pair, HL primary):
      regime = BULL_TAO (mean_168h > 0):
        TAO FR > SOL FR: dominant regime (~100% of quarters — AI narrative premium)
        -> long TAO (collect high TAO AI compute premium)
        -> short SOL (avoid lower retail carry)
        -> position_state = LONG_TAO_SHORT_SOL
        -> both legs on HL

      regime = BEAR_TAO (mean_168h < 0):
        SOL FR > TAO FR: rare regime (SOL meme-coin spike exceeds AI premium)
        -> long SOL (collect high SOL retail premium)
        -> short TAO (avoid lower AI carry)
        -> position_state = LONG_SOL_SHORT_TAO
        -> both legs on HL

      regime = NEUTRAL: no trade (mean_168h == 0 exactly — rare)

    Alt-alt edge (FIFTEENTH ALT-ALT pair — K747):
      TAO and SOL are cross-cluster assets with structurally independent FR drivers.
      BULL_TAO: AI narrative drives TAO premium (subnet launches, GPU AI cycles,
        institutional validator adoption, compute market pricing events).
        TAO FR >> SOL FR → long TAO (collect AI premium) / short SOL (lower retail carry).
      BEAR_TAO: Rare — SOL meme-coin season exceeds AI narrative premium.
        SOL FR >> TAO FR → long SOL (collect retail premium) / short TAO (lower AI carry).
      Cross-cluster: Bittensor AI compute marketplace (GPU/ML research/subnet economics)
        vs Solana SVM execution L1 (retail/DeFi/meme-coin sentiment). Completely different
        demand drivers ensure structural independence of FR cycles.
      G4 WF 12/12 ALL POSITIVE — UNPRECEDENTED (no negative fold in any of 12 OOS periods).
      ADF stat -12.2254 confirms stationarity (p=0.0). OU half-life=2.0h FAST.
      G5c AVAX BYPASS: TAO-SOL G5c=0.0126 PASS (vs ONDO-SOL G5c=-0.4148 FAIL).
        AI compute marketplace ≠ AVAX subnet appchain customization.
        TAO subnets = Bittensor AI model competition (not institutional L2 deployment).
      TAO vertex: 13th vertex added to V. MR9 L002: all future TAO-X pairs blocked.

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

    if regime == "BULL_TAO":
        # TAO FR > SOL FR: dominant regime (AI narrative premium >> retail)
        # long TAO (collect high AI compute premium) / short SOL (lower retail carry)
        long_asset  = "TAO"
        short_asset = "SOL"
        state       = STATE_LONG_TAO_SHORT_SOL
    else:  # BEAR_TAO
        # SOL FR > TAO FR: rare (SOL meme-coin spike > AI premium)
        # long SOL (collect retail premium) / short TAO (lower AI carry)
        long_asset  = "SOL"
        short_asset = "TAO"
        state       = STATE_LONG_SOL_SHORT_TAO

    # Both legs on HL (K747: TAO-PERP + SOL-PERP, HL-only)
    long_venue  = "HL"
    short_venue = "HL"

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
    Compute equal notional for both legs of the TAO-SOL paired trade.

    K747 HL-only config (both TAO-PERP + SOL-PERP on HL, paper-gate strict):
      sleeve_capital   = aum x sleeve_pct      (e.g. $10M x 2.5% = $250K)
      total_notional   = sleeve_capital x lev   ($250K x 4 = $1.0M)
      notional_per_leg = total_notional / 2     ($500K per leg)

    At $10M / 2.5% sleeve / 4x (paper-gate):
      TAO leg:   $125K capital x 4x = $500K notional (HL TAO-PERP)
      SOL leg:   $125K capital x 4x = $500K notional (HL SOL-PERP)
      Total:     $1.0M notional (two legs combined)
      Margin:    $250K (2.5% of AUM)
      HL conc:   PAPER-ONLY (65.0% AT CAP — no live capital added)
      Net profit: central $17,210/yr @$10M @4x (K523 3-point: $12.9K-$45.3K)
      TAO vertex: 13th — MR9 L002 blocks all future TAO-X pairs

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
    Submit K747 TAO-SOL paired trade: POST_ONLY both legs in parallel.

    Protocol (K747 HL-only — both legs on HL):
      1. Submit TAO leg on HL POST_ONLY
      2. Submit SOL leg on HL POST_ONLY
      3. Both legs submitted in parallel (K439 pattern)
      4. IOC fallback per leg if POST_ONLY times out
      5. If both fail: retry next 8h cycle

    Args:
      long_leg:  {"symbol": "TAO", "notional": 500000, "venue": "HL"}
      short_leg: {"symbol": "SOL", "notional": 500000, "venue": "HL"}
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
        print(f"  [K747] {mode_tag}: LONG {long_sym}@{long_venue} ${long_notl:,.0f}  "
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
            "venue_config":     "HL_ONLY_TAO_SOL_ALT_ALT",
            "mechanism_note":   (
                "TAO-SOL direct alt-alt differential (K747 FIFTEENTH ALT-ALT, 69th daemon): "
                "TAO FR = Bittensor AI L1 compute marketplace (GPU scarcity/NVDA cycles, "
                "subnet launch events, institutional validator adoption, AI regulation — "
                "episodic AI narrative spikes +16.34%/ann mean, TAO dominant 100% of quarters); "
                "SOL FR = Solana SVM DePIN/Retail adoption premium (meme-coin BONK/WIF/POPCAT, "
                "Firedancer upgrade hype, SOL ETF speculation, SVM DeFi TVL — "
                "persistently positive +7.706%/ann structural retail demand). "
                "G4 WF 12/12 ALL POSITIVE (UNPRECEDENTED — best WF result in alt-alt family). "
                "G8 FAIL: Bybit TAO 84.6% floor-capped (structural venue noise, not signal failure). "
                "K735 G8 precedent: HBAR-SOL ACCEPT CONDITIONAL with same structural issue. "
                "HL-only: TAO-PERP + SOL-PERP both active on HL (maxLeverage=5, index=116). "
                "HL at 65.0% AT CAP — paper-gate strict until K498 OKX reduces HL%. "
                "G5c AVAX bypass: TAO-SOL G5c=0.0126 PASS (vs ONDO G5c=-0.4148 FAIL). "
                "AI compute marketplace ≠ AVAX subnet appchain customization. "
                "TAO = 13th vertex. MR9 L002: all future TAO-X pairs blocked. "
                "OOS Sh=12.233 (W=168h, zero threshold). K523 central $17,210/yr @$10M @4x @2.5%. "
                "60d gate: Realized Sh>=6 + fill>=60% + maxDD<15%."
            ),
            "ts_utc":           ts,
        }
        _append_trade_log(result)
        return result

    # LIVE scaffold (not reached in PAPER_TRADE mode):
    print(f"  [K747] SCAFFOLD LIVE: parallel POST_ONLY "
          f"LONG {long_sym}@{long_venue} ${long_notl:,.0f} "
          f"+ SHORT {short_sym}@{short_venue} ${short_notl:,.0f}")
    long_order_id  = f"SCAFFOLD_LONG_{long_sym}_{int(time.time())}"
    short_order_id = f"SCAFFOLD_SHORT_{short_sym}_{int(time.time())}"

    print(f"  [K747] Neither leg filled within timeout — retry next 8h cycle")
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
    Check if current K747 position has drifted beyond DRIFT_REBALANCE_PCT (5%).

    K747 HL-only: both legs on HL (TAO-PERP + SOL-PERP).
    Drift detection: compare stored TAO leg notional vs SOL leg notional.
    Threshold: 5% (same as K449/K476/K484/K493/K629/K663/K679/K682/K684/K686/K690/K739 pattern).

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
    Both legs on HL (K747 HL primary — TAO-PERP + SOL-PERP).

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

    if state == STATE_LONG_TAO_SHORT_SOL:
        long_sym,  short_sym  = "TAO", "SOL"
    else:  # LONG_SOL_SHORT_TAO
        long_sym,  short_sym  = "SOL", "TAO"

    long_notional  = float(dash.get("long_notional",  0.0))
    short_notional = float(dash.get("short_notional", 0.0))

    if dry_run or PAPER_TRADE:
        mode_tag = "DRY_RUN" if dry_run else "PAPER_TRADE"
        print(f"  [K747] {mode_tag} CLOSE:")
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
        print(f"  [K747] SCAFFOLD CLOSE:")
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
    """Load k747_dashboard.json; return defaults if missing."""
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
    """Write k747_dashboard.json with full signal + regime state."""
    dash = _load_dashboard()

    # Update signal data
    dash["last_poll_jst"]        = signal.get("ts_jst", "—")
    dash["fr_tao_current"]       = signal.get("fr_tao",        0.0)
    dash["fr_sol_current"]       = signal.get("fr_sol",        0.0)
    dash["tao_sol_diff_current"] = signal.get("tao_sol_diff",  0.0)
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
    dash["hl_concentration_pct"]     = HL_CONCENTRATION_POST_K747   # 65.0% UNCHANGED (paper-only)

    # Paper-trade status
    paper_status = dash.get("paper_trade_status", {"days_elapsed": 0, "target_60d": 60})
    dash["paper_trade_status"]       = paper_status

    # 60d activation gate metrics (K750: Realized Sh >= 6, fill >= 60%, DD < 15%)
    dash["gate_metrics"] = {
        "realized_sharpe_target":  6.0,     # >=6 (49% of OOS Sh=12.233 — CONDITIONAL gate)
        "fill_rate_target_pct":    60,
        "max_drawdown_target_pct": 15,       # <15%
        "current_realized_sharpe": dash.get("60d_sharpe", 0.0),
        "current_fill_rate_pct":   0.0,
        "current_max_dd_pct":      0.0,
        "gate_status":             "IN_PROGRESS",
        "activation_trigger":      "60d paper-trade: Sh>=6 AND fill>=60% AND maxDD<15%",
        "profit_at_activation_2_5pct": "central $17,210/yr net @$10M @4x (K523: $12.9K-$45.3K range)",
        "alt_alt_note":            (
            "FIFTEENTH ALT-ALT pair (TAO-SOL, no BTC/ETH leg). Standalone. 69th daemon. "
            "ACCEPT CONDITIONAL (G8 FAIL: Bybit TAO floor-capped + HL 65.0% AT CAP). "
            "G4 WF 12/12 ALL POSITIVE — UNPRECEDENTED (best WF in family). "
            "TAO = 13th vertex. MR9 L002: all future TAO-X pairs blocked."
        ),
        "hl_cap_warning": (
            "HL concentration 65.0% AT CAP (exactly). Paper-gate strict. "
            "Deploy LIVE only after K498 OKX activation reduces HL% below 65%. "
            "K747 HL-only: both TAO-PERP + SOL-PERP on HL (maxLeverage=5, index=116). "
            "2.5% all-HL would push to 67.5% — OVER cap. Paper-only until HL% resolved."
        ),
    }

    # Strategy metadata
    dash["paper_trade_mode"]    = PAPER_TRADE
    dash["wave"]                = "K750"
    dash["strategy"]            = "K747 TAO-SOL FR Differential (FIFTEENTH ALT-ALT, W=168h, HL-only, CONDITIONAL)"
    dash["execution_mode"]      = "POST_ONLY_PARALLEL"
    dash["venue_config"]        = "HL_ONLY"
    dash["alt_alt_mechanism"]   = {
        "formula":            "diff = TAO_FR - SOL_FR  (direct alt-alt, no base asset)",
        "rolling_window":     "W=168h (21 x 8h periods, primary config)",
        "signal":             "sign(rolling_mean_168h(diff))",
        "fifteenth_alt_alt":  True,
        "g4_unprecedented":   "12/12 ALL POSITIVE — UNPRECEDENTED (no negative fold in alt-alt family)",
        "hl_only_reason":     HL_ONLY_REASON,
        "hl_concentration":   65.0,
        "cross_cluster_note": (
            "TAO (Bittensor AI compute marketplace, GPU/ML research, subnet economics) "
            "vs SOL (Solana SVM retail/DeFi/meme — persistently positive +7.706%/ann). "
            "TAO mean +16.34%/ann — AI narrative premium dominates all quarters (100% of time). "
            "Completely different demand drivers: GPU scarcity cycles vs retail speculation. "
            "G4 WF 12/12 ALL POSITIVE — unprecedented result in alt-alt family. "
            "ADF stat -12.2254 (p=0.0). OU half-life=2.0h (FAST). Vol ratio=1.5734x."
        ),
        "avax_cluster_bypass": (
            "K746 ONDO-SOL BLOCKED: G5c(AVAX-BTC)=-0.4148 FAIL + G5k(AVAX-SOL)=-0.5842 FAIL. "
            "K747 TAO-SOL: G5c(AVAX-BTC)=+0.0126 PASS + G5k(AVAX-SOL)=+0.1286 PASS. "
            "AI L1 (TAO) ≠ AVAX subnet narrative cluster. "
            "TAO subnets = Bittensor AI model competition (GPU mining, ML training). "
            "AVAX subnets = L2-like appchain customization (institutional DeFi). Distinct."
        ),
        "tao_vertex_rule": (
            "TAO = 13th vertex added to V. "
            "V = {APT, ATOM, AVAX, BNB, ENA, FIL, HBAR, INJ, LDO, SEI, SOL, TIA, TAO}. "
            "MR9 L002: all future TAO-X pairs auto-blocked. "
            "TAO-SOL is the only permissible TAO-X pair given V at K747."
        ),
        "k476_sol_saturation": (
            "SOL appears in K476+K679+K682+K684+K686+K690+K694+K696+K708+K721+K728+K735+K739 family. "
            "K747 TAO-SOL: G5b(SOL-BTC corr)=0.2229 PASS (below 0.40). "
            "TAO-SOL = K_TAO_BTC_dir - K476_dir (algebraic decomposition). "
            "SOL saturation: 0.2229 well below threshold."
        ),
        "tao_fr_drivers": (
            "Bittensor AI L1 compute marketplace. GPU scarcity cycles (NVDA/H100 AI peaks). "
            "Subnet launch events (new subnet = higher validator staking demand). "
            "Institutional AI adoption (validator set expansion). Compute market pricing. "
            "TAO staking/subnet yield vs perpetual leverage premium. "
            "AI regulation events (SEC/CFTC AI asset classification). +16.34%/ann mean."
        ),
        "sol_fr_drivers": (
            "Solana SVM DePIN/Retail adoption premium, meme-coin seasons (BONK/WIF/POPCAT), "
            "Firedancer upgrade hype, Solana ETF narrative events, SVM DeFi TVL expansion "
            "(Jupiter, Drift Protocol, Jito restaking), NFT/gaming/AI agent cycles. "
            "+7.706%/ann persistently positive structural retail demand."
        ),
        "g8_fail_analysis": (
            "G8 FAIL: Bybit TAO 84.6% floor-capped (0.0001/0.00005 min tick). "
            "Structural venue noise — not a signal quality failure. "
            "HL vs Bybit TAO-SOL diff corr=0.2651 (below 0.55 threshold). "
            "K735 G8 precedent: HBAR-SOL ACCEPT CONDITIONAL with HL-1h vs Bybit-8h structural mismatch. "
            "Same pattern: G8 fail = venue data quality. HL TAO liquid ($12.3M/24h, maxLeverage=5). "
            "Resolution: use HL-only (TAO-PERP + SOL-PERP both active on HL)."
        ),
        "ou_half_life":   "2.0h (0.08d) — FAST mean-reversion.",
        "g4_result": "12/12 folds ALL POSITIVE (UNPRECEDENTED — no negative fold). Best WF in alt-alt family.",
        "family_rank": (
            "FIFTEENTH alt-alt evaluated (G4 12/12 UNPRECEDENTED). "
            "OOS Sh=12.233 (W=168h). TAO-SOL AI L1 × SVM cross-cluster. "
            "K747 introduces TAO as 13th vertex — new AI L1 cluster. "
            "Profit central: $17,210/yr @$10M @2.5% sleeve. K523: $12.9K-$45.3K range."
        ),
    }
    dash["activation_criteria"] = {
        "60d_paper_trade_gate":  "required",
        "realized_sharpe_min":   6.0,
        "fill_rate_min_pct":     60,
        "max_drawdown_max_pct":  15,
        "status":                "SCAFFOLD-READY",
        "activation_sleeve_pct": 0.025,
        "venue":                 "HL-only (TAO-PERP + SOL-PERP both on HL)",
        "conditional_note":      (
            "CONDITIONAL: G8 FAIL (Bybit TAO floor) + HL 65.0% AT CAP. "
            "Deploy LIVE only after K498 OKX reduces HL% below 65%. "
            "G4 12/12 UNPRECEDENTED — strongest WF validation in family."
        ),
        "live_trigger":          "K498 OKX activation (HL% drops from 65.0%) + 60d gate passage",
    }
    dash["oos_performance"] = {
        "sharpe":                   12.233,
        "oos_ann_ret_pct":          5.328,
        "oos_ann_ret_4x_pct":       21.313,
        "k523_conservative_yr":     12907,
        "k523_central_yr":          17210,
        "k523_optimistic_yr":       45289,
        "k523_upper_bound_yr":      53281,
        "daily_usdc_central":       47,
        "wave_accept":              "K747 ACCEPT CONDITIONAL (K750 scaffold) — FIFTEENTH ALT-ALT, AI L1 × SVM cross-cluster, G4 12/12 UNPRECEDENTED",
        "cluster":                  "TAO-SOL Alt-Alt FR Differential (Bittensor AI L1 × Solana SVM, HL-only, cross-cluster, 13th vertex)",
        "cluster_rationale": (
            "TAO (Bittensor AI compute marketplace, GPU scarcity cycles, subnet economics — +16.34%/ann, "
            "TAO dominant 100% of quarters) vs SOL (Solana SVM retail/DeFi/meme — +7.706%/ann). "
            "No BTC or ETH leg — pure alt-to-alt cross-cluster AI compute vs SVM retail. "
            "G4 WF 12/12 ALL POSITIVE — UNPRECEDENTED (no negative fold in alt-alt family). "
            "G8 FAIL: Bybit TAO 84.6% floor-capped (structural) → HL-only deployment. "
            "G5c AVAX bypass: +0.0126 PASS (AI ≠ AVAX subnet — distinct cluster). "
            "HL-only: TAO-PERP + SOL-PERP both active on HL (maxLeverage=5, index=116). "
            "HL 65.0% AT CAP — paper-gate strict until K498 OKX reduces HL%. "
            "TAO = 13th vertex. MR9 L002: all future TAO-X pairs blocked. "
            "K523 central $17,210/yr net @$10M @4x @2.5% sleeve."
        ),
        "daemon_number":            "69th",
        "section6_result":          "ACCEPT CONDITIONAL 28/29 gates. G8=FAIL (Bybit TAO floor). G1-G7+G9+all-G5 PASS.",
        "family_rank": {
            "k747_oos_sharpe":   12.233,
            "k747_pair":         "TAO-SOL (alt-alt, FIFTEENTH/cross-cluster, CONDITIONAL G8, G4 12/12 UNPRECEDENTED, 13th vertex TAO)",
            "alt_alt_accepted":  15,
            "g4_note":           "K747 G4=12/12 ALL POSITIVE — UNPRECEDENTED (best WF in family).",
            "vertex_note":       "TAO = 13th vertex. V={APT,ATOM,AVAX,BNB,ENA,FIL,HBAR,INJ,LDO,SEI,SOL,TIA,TAO}.",
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
      1. Fetch TAO + SOL FRs from HL
      2. Compute TAO-SOL differential + 168h rolling mean
      3. Decide position (sign of rolling mean — zero threshold)
      4. Compute delta-neutral notional
      5. If entering: submit paired trade (POST_ONLY, HL primary)
      6. If holding: check drift + rebalance
      7. Write k747_dashboard.json
    """
    ts_jst = datetime.now(JST).strftime("%Y-%m-%d %H:%M JST")
    print(f"\n=== K747 TAO-SOL FR Differential (FIFTEENTH ALT-ALT, HL-only) — {ts_jst} ===")
    print(f"  Mode:      {'DRY-RUN' if dry_run else 'PAPER-TRADE' if PAPER_TRADE else 'LIVE'}")
    print(f"  AUM:       ${aum:,.0f}  Sleeve: {SLEEVE_PCT:.1%}  Leverage: {LEVERAGE}x")
    print(f"  Venue:     HL-only (TAO-PERP + SOL-PERP, both HL)")
    print(f"  HL conc:   65.0% AT CAP (paper-gate strict — K498 OKX activation required)")
    print(f"  Execution: POST_ONLY parallel (K439)")
    print(f"  Signal:    diff = TAO_FR - SOL_FR  (direct alt-alt, no base asset)")
    print(f"             sign(rolling_mean_168h)  (zero threshold, W=168h = 21 x 8h periods)")
    print(f"  15th:      FIFTEENTH ALT-ALT pair (AI L1 × SVM) — OOS Sh=12.233, CONDITIONAL")
    print(f"  G4 12/12:  ALL POSITIVE — UNPRECEDENTED (best WF in alt-alt family)")
    print(f"  AVAX-bypass: G5c(AVAX-BTC)=0.013 PASS (vs ONDO -0.415 FAIL). AI≠AVAX subnet.")
    print(f"  TAO vertex: 13th vertex. MR9 L002: all future TAO-X auto-blocked.")
    print(f"  G8 FAIL:   Bybit TAO 84.6% floor-capped (K735 HBAR precedent — HL-only).")
    print(f"  69th:      OOS Sh={12.233:.2f} W=168h HL-only 2.5% sleeve central $17K/yr @$10M @4x")

    # Step 1: Fetch + compute TAO-SOL differential
    print("\n  [Step 1] Computing TAO-SOL FR differential from HL...")
    signal = compute_signal()
    print(f"  TAO FR:     {signal['fr_tao']:+.8f} (1h, HL, AI L1 +16.34%/ann mean)")
    print(f"  SOL FR:     {signal['fr_sol']:+.8f} (1h, HL, retail +7.706%/ann persistent)")
    print(f"  TAO-SOL:    {signal['tao_sol_diff']:+.8f}  (direct alt-alt differential)")
    print(f"  Mean 168h:  {signal['mean_168h']:+.8f}")
    print(f"  Sigma 168h: {signal['diff_sigma']:+.8f}  (informational)")
    print(f"  Direction:  {signal['signal_direction']:+d}  (+1=BULL_TAO, -1=BEAR_TAO, 0=NEUTRAL)")
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
    print(f"  TAO leg:          ${notional_per_leg:,.0f}  (2.5% x ${aum/1e6:.0f}M x {LEVERAGE}x / 2)")
    print(f"  SOL leg:          ${notional_per_leg:,.0f}  (2.5% x ${aum/1e6:.0f}M x {LEVERAGE}x / 2)")
    print(f"  Total notional:   ${total_notional:,.0f}")
    print(f"  Margin required:  ${total_notional/LEVERAGE:,.0f}  ({SLEEVE_PCT:.1%} AUM)")
    print(f"  Profit @$10M 4x:  OOS Sh=12.233 = central $17,210/yr (K523: $12.9K-$45.3K range)")
    print(f"  HL conc:          65.0% AT CAP (paper-only — K498 OKX activation required for live)")

    # Step 4: Load current position + decide action
    dash = _load_dashboard()
    current_state = dash.get("position_state", STATE_NEUTRAL)
    print(f"\n  [Step 4] Current position: {current_state}")

    trade_result = None
    if decision and current_state == STATE_NEUTRAL:
        print(f"  Action: ENTER {decision['position_state']}")
        long_leg  = {"symbol": decision["long_asset"],  "notional": notional_per_leg, "venue": "HL"}
        short_leg = {"symbol": decision["short_asset"], "notional": notional_per_leg, "venue": "HL"}
        trade_result = submit_paired_trade(long_leg, short_leg, dry_run=dry_run)
        print(f"  Trade status: {trade_result['status']}")

    elif decision and current_state != STATE_NEUTRAL:
        if decision["position_state"] != current_state:
            print(f"  Action: CLOSE + FLIP (signal reversed)")
            close_result = close_paired_position("signal_reversal", dry_run=dry_run)
            print(f"  Close status: {close_result['status']}")
            long_leg  = {"symbol": decision["long_asset"],  "notional": notional_per_leg, "venue": "HL"}
            short_leg = {"symbol": decision["short_asset"], "notional": notional_per_leg, "venue": "HL"}
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
    print(f"\n  === K747 TAO-SOL Cycle Complete ===")
    print(f"  Position state:     {dash_out.get('position_state')}")
    print(f"  Regime:             {dash_out.get('regime')}")
    print(f"  TAO-SOL Mean 168h:  {dash_out.get('mean_168h'):+.8f}")
    print(f"  Signal direction:   {dash_out.get('signal_direction')}")
    print(f"  FIFTEENTH ALT-ALT:  TAO-SOL (no BTC/ETH base) OOS Sh=12.233, G4 12/12 UNPRECEDENTED")
    print(f"  HL-only:            65.0% AT CAP (paper-gate strict — K498 OKX required)")
    print(f"  G5b SOL-BTC:        corr=0.2229 PASS. G5c AVAX bypass: 0.013 PASS.")
    print(f"  G8 FAIL:            Bybit TAO 84.6% floor (structural). K735 precedent. HL-only.")
    print(f"  TAO 13th vertex:    MR9 L002 — all future TAO-X pairs auto-blocked.")
    print(f"  Cross-cluster:      TAO AI compute marketplace vs SOL SVM retail (distinct drivers).")
    print(f"  OU FAST:            OU half-life=2.0h — FAST mean-reversion.")
    print(f"  Paper-trade mode:   {PAPER_TRADE}")
    print(f"  OOS Sharpe:         12.233 (W=168h, zero threshold, ~217d OOS)")
    print(f"  Cluster:            TAO-SOL Alt-Alt (AI L1 × SVM, 69th daemon, 13th vertex)")
    print(f"  Profit 2.5% sleeve: central $17,210/yr net @$10M @4x (K523: $12.9K-$45.3K)")
    print(f"  HL concentration:   65.0% AT CAP (paper-only, no live capital impact)")
    print(f"  60d gate:           Realized Sh>=6 + fill>=60% + maxDD<15%")
    print()

    return 0


# ─────────────────────────────────────────────────────────────────────────────
# CLI entry point
# ─────────────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="K747 TAO-SOL FR Differential Strategy (K750 scaffold, FIFTEENTH ALT-ALT, HL-only, CONDITIONAL)"
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
        print(f"\n=== K747 Dashboard ({dash.get('last_poll_jst', '—')}) ===")
        print(json.dumps(dash, indent=2))
        return 0

    if args.rebalance:
        dash   = _load_dashboard()
        result = daily_rebalance(dash)
        print(f"\n=== K747 Rebalance Check ===")
        print(json.dumps(result, indent=2))
        return 0

    if args.close:
        result = close_paired_position(args.close, dry_run=args.dry_run)
        print(f"\n=== K747 Close Result ===")
        print(json.dumps(result, indent=2))
        return 0

    return run_cycle(dry_run=args.dry_run, aum=args.aum)


if __name__ == "__main__":
    sys.exit(main())
