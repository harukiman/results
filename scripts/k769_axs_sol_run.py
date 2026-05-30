#!/usr/bin/env python3
"""
k769_axs_sol_run.py — K769 AXS-SOL FR Differential Strategy
============================================================
EIGHTEENTH ALT-ALT pair: AXS vs SOL (Gaming P2E leader × Solana SVM).
Signal: AXS_FR - SOL_FR
W=168h rolling mean (7d — standard family window; G6 compliant: 31.1/yr OOS)
HL primary (Jan 2026+ data), Bybit primary for backtest (730d history)
HL concentration: 66.8% AT CAP → paper-gate strict (K498/v6.52 required for live)

K769 AXS-SOL alt-alt hypothesis:
  AXS (Axie Infinity — Gaming P2E token, RON-chain governance):
    FR driven by Gaming P2E adoption cycles (Axie Origins seasonal content),
    SLP burn/mint economics (in-game token mechanics),
    AXS staking reward cycles (treasury governance APR),
    NFT Axie breeding demand (marketplace liquidity cycles),
    Southeast Asian retail speculation (Philippines/Indonesia primary markets),
    P2E tournament event spikes (Axie World Championship),
    Ronin sidechain upgrade events (RON airdrop, bridge activity).
    FR erratic: 41% positive (full period), 32% OOS (net negative bias — gaming bear).
    Vol ratio vs SOL: 5.24x (Bybit full), 6.37x (30d), 8.88x (OOS), 16.23x (HL 1h).
  SOL (Solana SVM L1):
    FR driven by retail momentum, Phantom wallet adoption, Firedancer upgrade,
    Solana ETF narrative flows, SVM DeFi TVL (Jupiter/Drift/Jito).
    SOL FR mean +8.82%/ann — persistently positive structural retail demand.
    SOL extreme negative FR: Min=-20.51bps (liquidation cascade Feb 2025).
  Alt-alt mechanism: AXS (Gaming P2E, RON-chain) vs SOL (Solana SVM L1).
    Structurally orthogonal: Gaming P2E cycle (Axie game versions, SLP economics)
    is decoupled from Solana SVM cycle (Firedancer, validator rewards, meme).
    Historical: 2021 AXS P2E peak (8000+ USD) was independent of SOL SVM narrative.
    raw_corr(AXS_fr, SOL_fr) = 0.19 (Bybit) — essentially orthogonal.
    G5 max_corr=-0.2796 (G5n ENA-SOL) ALL PASS (no corr approaching 0.40).
  EIGHTEENTH alt-alt pair. OOS Sharpe 16.0543. W=168h. 12/12 WF ALL POSITIVE.
  All G5 gates PASS. MaxDD OOS only -0.5311%.
  G8: HL+Bybit confirmed (AXS HL from 2026-01-18, Bybit primary for backtest).
  AXS becomes 16th vertex. All future AXS-X blocked (MR9 L002).

K769 §6 validation (CLEAN ACCEPT — G1-G9 ALL PASS):
  - OOS Sharpe: 16.0543 (W=168h, zero threshold, ~211d OOS)
  - OOS Ann Return: $124K central @$10M @4x @1.5% sleeve (K523 3-point)
  - W=168h rolling mean, zero threshold (sign of diff) — G6 compliant (31.1/yr)
  - G4 walk-forward: 12/12 folds positive (min_sh=5.9193)
  - G5 all gates PASS (max_corr=-0.2796 G5n ENA-SOL — all well below 0.40)
  - Sleeve 1.5% (long-tail liquidity constraint — AXS smaller than major L1)
  - G8: HL+Bybit confirmed (AXS HL from 2026-01-18; Bybit 730d primary for backtest)
  - HL 66.8% AT CAP → paper-gate strict until K498/v6.52

K769 AXS-SOL vertex addition (16th vertex, Gaming P2E cluster):
  V (before K769) = {APT, ATOM, AVAX, BNB, ENA, FIL, HBAR, INJ, LDO, SEI, SOL, TIA, TAO, PEPE, WIF}
  V (after K769)  = {APT, ATOM, AVAX, BNB, ENA, FIL, HBAR, INJ, LDO, SEI, SOL, TIA, TAO, PEPE, WIF, AXS}
  AXS = 16th vertex (Gaming P2E cluster — Axie Infinity).
  MR9 L002: all future AXS-X pairs are auto-blocked (AXS exhausted as new vertex).
  AXS-SOL is the only permissible AXS-X pair given V composition at K769.

K523 3-point profit projection (@$10M @4x @1.5% sleeve):
  Conservative: $78,337/yr  (R2S=38% floor, K518 floor, OOS haircut 25%)
  Central:      $123,689/yr (K523 mandate: 60% realized-to-stated, base case)
  Optimistic:   $175,227/yr (near-full OOS realization if Gaming P2E cycle peaks)
  Upper bound:  OOS raw return (NOT central — K523 mandatory)
  Note: 1.5% sleeve → ~$150K margin @$10M; central per K769 eval json=$123,689/yr

Cross-venue note (K769):
  HL: AXS listed from 2026-01-18 (3040 rows ~127d — limited IS period).
  Bybit: AXSUSDT 730d primary (2024-05-25 to 2026-05-24, 3184 rows, 8h intervals).
  Primary backtest on Bybit (longer history). HL for OOS 1h-resolution confirmation.
  OKX: not yet cached (G8 partial — HL+Bybit PASS, OKX pending).

Architecture (K679→K747→K754→K759→K769 alt-alt scaffold pattern):
  1. fetch_fr_batch()                  → fetch AXS + SOL FR every 8h from HL
  2. compute_signal(axs_fr, sol_fr)   → 168h rolling mean of (AXS_FR - SOL_FR); sign()
  3. decide_position(signal)           → LONG_AXS_SHORT_SOL | LONG_SOL_SHORT_AXS | NEUTRAL
  4. submit_paired_trade(long, short) → POST_ONLY paired (AXS + SOL legs, HL primary)
  5. daily_rebalance()                 → drift > 5% triggers rebalance
  6. close_paired_position(reason)    → sequential: short first, then long

K771 production scaffold:
  - 76th daemon (eighteenth alt-alt pair, CLEAN ACCEPT, G4 12/12)
  - HL primary, Bybit fallback (AXS: HL AXS-PERP from 2026-01-18 + Bybit AXSUSDT)
  - 1.5% sleeve (long-tail liquidity constraint)
  - $124K central @$10M @4x @1.5% sleeve (K523 3-point: $78K-$175K)
  - Paper-gate until K498/v6.52 reduces HL concentration
  - 60d paper-trade gate: Realized Sh>=6 + fill>=60% + maxDD<15%
  - 18th alt-alt pair (Gaming P2E cluster × SVM, 16th vertex AXS)

Execution:
  - HL primary (AXS-PERP + SOL-PERP, HL)
  - Bybit fallback (AXSUSDT-PERP + SOL-PERP, Bybit) — informational
  - POST_ONLY paired execution (K439 pattern)
  - Position: 1.5% sleeve, 4x leverage (paper-gate strict — HL cap 66.8%)
  - 8h cadence (matches FR settlement cycle)
  - W=168h rolling mean (21 x 8h periods — G6-safe: 31.1 entries/yr)

Paper-trade mode is the DEFAULT.  No orders are submitted unless
PAPER_TRADE=False is explicitly set in the environment.

K339 security: REPO_ROOT from __file__, no /Users/ literals.
No new packages — stdlib urllib + json only.

Usage:
  python3 scripts/k769_axs_sol_run.py --dry-run
  python3 scripts/k769_axs_sol_run.py --status
  python3 scripts/k769_axs_sol_run.py --rebalance
  python3 scripts/k769_axs_sol_run.py --close "scheduled exit"
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

DASHBOARD_PATH  = DATA_DIR  / "k769_dashboard.json"
FR_HISTORY_PATH = CACHE_DIR / "k769_fr_history.jsonl"
TRADE_LOG_PATH  = CACHE_DIR / "k769_paper_trades.jsonl"

JST = timezone(timedelta(hours=9))
UTC = timezone.utc

# ── Strategy constants ────────────────────────────────────────────────────────
PAPER_TRADE         = os.environ.get("PAPER_TRADE", "True").lower() != "false"
SLEEVE_PCT          = 0.015         # K769 sleeve = 1.5% of AUM (long-tail liquidity constraint)
LEVERAGE            = 4.0           # 4x per K769 analysis
AUM_DEFAULT         = 10_000_000.0  # $10M reference AUM
DRIFT_REBALANCE_PCT = 0.05          # rebalance if legs drift > 5%
IOC_TIMEOUT_SEC     = 300           # 5 min fill window
EMA_PERIOD_HOURS    = 168           # 168h rolling mean (W=168h, G6 compliant: 31.1/yr)
EMA_PERIOD_PERIODS  = EMA_PERIOD_HOURS // 8  # = 21 periods (8h settlement cycle)
SIGNAL_SIGMA_MULT   = 0.0           # zero threshold (sign of rolling mean)
HL_API_URL          = "https://api.hyperliquid.xyz/info"
BYBIT_API_URL       = "https://api.bybit.com"

# ── Venue config ──────────────────────────────────────────────────────────────
# HL primary: AXS-PERP + SOL-PERP on HL (AXS listed from 2026-01-18)
# Bybit fallback: AXSUSDT-PERP + SOL-PERP on Bybit (primary for backtest, informational live)
# HL concentration: 66.8% AT CAP — paper-gate strict until K498/v6.52.
HL_CONCENTRATION_PRE_K769   = 66.8   # post-K761 reference
HL_CONCENTRATION_POST_K769  = 66.8   # UNCHANGED — paper-only, no live capital added
HL_ONLY_REASON              = (
    "HL primary: AXS-PERP + SOL-PERP on HL. Bybit AXSUSDT fallback (informational). "
    "AXS HL listed from 2026-01-18 (3040 rows ~127d). Bybit primary for backtest (730d). "
    "HL at 66.8% AT CAP. Paper-gate strict: any live capital would breach 65% ceiling. "
    "Deploy LIVE after K498/v6.52 reduces HL% below 65%."
)

# ── Position state constants ──────────────────────────────────────────────────
STATE_NEUTRAL            = "NEUTRAL"
STATE_LONG_AXS_SHORT_SOL = "LONG_AXS_SHORT_SOL"
STATE_LONG_SOL_SHORT_AXS = "LONG_SOL_SHORT_AXS"

# ── Symbols fetched from HL for FR data ──────────────────────────────────────
SYMBOLS = ("AXS", "SOL")


# ─────────────────────────────────────────────────────────────────────────────
# HTTP helper (stdlib urllib only — no requests)
# ─────────────────────────────────────────────────────────────────────────────

def _http_get(url: str, timeout: int = 10) -> Optional[dict]:
    try:
        req = urllib.request.Request(
            url, headers={"User-Agent": "crypto-lab-k769/1.0"}
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        print(f"  [k769] HTTP error: {e}", file=sys.stderr)
        return None


def _http_post(url: str, payload: dict, timeout: int = 10) -> Optional[dict]:
    try:
        data = json.dumps(payload).encode()
        req  = urllib.request.Request(
            url, data=data,
            headers={"Content-Type": "application/json",
                     "User-Agent": "crypto-lab-k769/1.0"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        print(f"  [k769] HTTP error: {e}", file=sys.stderr)
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Phase 1 — Funding rate fetch (AXS + SOL from HL)
# ─────────────────────────────────────────────────────────────────────────────

def _fetch_hl_fr_batch() -> Dict[str, float]:
    """
    Fetch current 1h funding rates for AXS and SOL from HL.
    Returns {symbol: fr_1h_fraction}.

    HL API: metaAndAssetCtxs (POST).
    K769: HL primary (AXS-PERP + SOL-PERP).
    Bybit fallback: AXSUSDT denomination (informational; 8h interval cross-check).
    AXS HL confirmed: 3040 rows 2026-01-18 to 2026-05-24.

    Note: HL settles 1h funding; W=168h = 168 x 1h periods for rolling mean.
    FR stored as 1h fraction; annualized = fr_1h * 8760.

    Fallback: Bybit /v5/market/tickers — AXSUSDT denomination (informational
    cross-check; 8h interval vs HL 1h settlement — signal cross-check only).
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
        print(f"  [k769] HL partial result {list(result.keys())} — trying Bybit fallback",
              file=sys.stderr)

    # Fallback: Bybit /v5/market/tickers (AXSUSDT denomination — informational)
    bybit_url = f"{BYBIT_API_URL}/v5/market/tickers?category=linear"
    raw_bybit = _http_get(bybit_url)
    if raw_bybit and raw_bybit.get("retCode") == 0:
        tickers = raw_bybit.get("result", {}).get("list", [])
        sym_map = {t["symbol"]: t for t in tickers}
        for sym in SYMBOLS:
            if sym not in result:
                for perp_sym in [f"{sym}USDT", f"{sym}USDC"]:
                    if perp_sym in sym_map:
                        tick = sym_map[perp_sym]
                        try:
                            fr_val = float(tick.get("fundingRate", 0.0))
                            result[sym] = fr_val
                            print(f"  [k769] {sym} FR from Bybit fallback "
                                  f"({perp_sym}, informational cross-check)", file=sys.stderr)
                        except (TypeError, ValueError):
                            pass
                        break
    return result


def _load_fr_history() -> List[dict]:
    """Load K769 FR history JSONL."""
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
    fr_axs: float, fr_sol: float, axs_sol_diff: float
) -> None:
    """Append one FR snapshot to history."""
    rec = {
        "ts_utc":       datetime.now(UTC).isoformat(),
        "fr_axs":       round(fr_axs,       10),
        "fr_sol":       round(fr_sol,         10),
        "axs_sol_diff": round(axs_sol_diff,   10),  # AXS_FR - SOL_FR
    }
    with open(FR_HISTORY_PATH, "a") as f:
        f.write(json.dumps(rec) + "\n")


# ─────────────────────────────────────────────────────────────────────────────
# Phase 2 — Signal computation (AXS-SOL direct differential, 168h rolling mean)
# ─────────────────────────────────────────────────────────────────────────────

def compute_signal(
    fr_axs: Optional[float] = None,
    fr_sol: Optional[float] = None,
) -> dict:
    """
    Fetch live AXS and SOL FRs from HL, compute AXS-SOL differential,
    and compute 168h rolling mean for direction signal.

    Signal mechanism (K769 direct alt-alt differential — no orthogonalization):
      diff = AXS_FR - SOL_FR
      mean_168h = 168h rolling mean of diff (21 x 8h periods equivalent)
      sign  = sign(mean_168h)
      Enter: sign > 0 -> AXS FR > SOL FR -> long AXS (collect P2E gaming premium), short SOL
             sign < 0 -> SOL FR > AXS FR -> long SOL (collect SVM premium), short AXS

    NOTE: AXS is Gaming P2E — structurally orthogonal to SOL SVM infrastructure.
    During SOL liquidation cascades (SOL min=-20.51bps), AXS cascade is independent
    (gaming cycle not correlated to SOL margin calls). Strategy captures differential.
    OOS raw_corr(AXS_fr, SOL_fr) = 0.1182 (near-zero OOS vs 0.19 full-period).

    Alt-alt mechanism (EIGHTEENTH ALT-ALT pair — K769):
      AXS FR tracks Gaming P2E adoption cycles: Axie Origins seasonal content,
      SLP burn/mint mechanics, AXS staking reward cycles, NFT breeding demand,
      Southeast Asian retail (Philippines/Indonesia P2E markets),
      P2E tournament events (Axie World Championship), Ronin sidechain upgrades.
      Vol ratio: 5.24x (Bybit full), 6.37x (30d), 8.88x (OOS), 16.23x (HL 1h).
      SOL FR tracks Solana SVM: DePIN, Phantom adoption, Firedancer, SOL ETF,
      SVM DeFi TVL (Jupiter/Drift/Jito). +8.82%/ann persistent. Min=-20.51bps.
      AXS-SOL diff captures relative Gaming P2E premium vs SVM infrastructure.
      raw_corr(AXS, SOL) = 0.19 (Bybit) — essentially orthogonal.
      G5 max_corr=-0.2796 (G5n ENA-SOL) ALL PASS.

    W=168h rationale (G6 compliance):
      W=168h → 31.1 entries/yr OOS (ABOVE 20/yr long-tail G6 threshold — PASS).
      W=80h  → 34.5 entries/yr OOS (best config OOS Sh=16.98, marginally higher).
      W=168h chosen as family standard window for consistency with alt-alt family.
      W=48h: 63.9/yr OOS Sh=16.53 — also PASS but more entries than needed.
      W=168h canonical for K769 (family standard; G6-compliant 31.1/yr).

    K769 §6 validation:
      - OOS Sharpe: 16.0543 (W=168h, zero threshold, ~211d OOS period)
      - OOS Ann Return: $124K central @$10M @4x @1.5% sleeve (K523 3-point)
      - All G5 checks PASS (max_corr=-0.2796 G5n ENA-SOL — all well below 0.40)
      - G4 WF 12/12 all positive (min_sh=5.9193, mean_sh=16.8423)
      - 60d gate: Realized Sh>=6 + fill>=60% + maxDD<15%
      - HL 66.8% AT CAP → paper-gate strict

    Returns:
      {
        "fr_axs":           float,
        "fr_sol":           float,
        "axs_sol_diff":     float,    # AXS_FR - SOL_FR (current)
        "mean_168h":        float,    # 168h rolling mean of differential
        "diff_sigma":       float,    # 168h rolling sigma (informational)
        "history_points":   int,
        "regime":           str,      # BULL_AXS | BEAR_AXS | NEUTRAL
        "signal_direction": int,      # +1 | -1 | 0
        "ts_jst":           str,
      }
    """
    if fr_axs is None or fr_sol is None:
        frs    = _fetch_hl_fr_batch()
        fr_axs = frs.get("AXS", 0.0)
        fr_sol = frs.get("SOL", 0.0)

    # AXS-SOL direct alt-alt differential (no orthogonalization)
    axs_sol_diff = fr_axs - fr_sol

    _append_fr_history(fr_axs, fr_sol, axs_sol_diff)

    # Load history for rolling mean + sigma (168h = ~21 x 8h periods)
    history = _load_fr_history()
    diffs   = [r["axs_sol_diff"] for r in history if "axs_sol_diff" in r]

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

    # Regime classification (zero threshold — per K769 spec)
    # BULL_AXS: AXS FR > SOL FR (Gaming P2E cycle dominant)
    # BEAR_AXS: AXS FR < SOL FR (SVM infrastructure premium dominant)
    if mean_168h > 0:
        regime    = "BULL_AXS"   # AXS-SOL diff positive → AXS FR > SOL FR (P2E season)
        direction = 1
    elif mean_168h < 0:
        regime    = "BEAR_AXS"   # AXS-SOL diff negative → SOL FR > AXS FR (SVM season)
        direction = -1
    else:
        regime    = "NEUTRAL"
        direction = 0

    return {
        "fr_axs":           round(fr_axs,        10),
        "fr_sol":           round(fr_sol,          10),
        "axs_sol_diff":     round(axs_sol_diff,    10),
        "mean_168h":        round(mean_168h,        10),
        "diff_sigma":       round(sigma,             10),
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
    Determine trade direction from AXS-SOL differential rolling mean.

    Logic (AXS-SOL direct alt-alt pair, HL primary):
      regime = BULL_AXS (mean_168h > 0):
        AXS FR > SOL FR: Gaming P2E season dominant
        -> long AXS (collect P2E gaming rotation premium)
        -> short SOL (avoid lower SVM infra carry in P2E-dominant regime)
        -> position_state = LONG_AXS_SHORT_SOL

      regime = BEAR_AXS (mean_168h < 0):
        SOL FR > AXS FR: SVM infrastructure season dominant
        -> long SOL (collect SVM DePIN/DeFi premium)
        -> short AXS (avoid lower/negative P2E carry in SVM regime)
        -> position_state = LONG_SOL_SHORT_AXS

      regime = NEUTRAL: no trade (mean_168h == 0 exactly — rare)

    Alt-alt edge (EIGHTEENTH ALT-ALT pair — K769):
      AXS and SOL are structurally distinct assets with orthogonal FR timing.
      BULL_AXS: Gaming P2E adoption drives AXS premium (Axie Origins releases,
        AXS staking rewards, SLP burning mechanics, P2E tournament events,
        Southeast Asian retail speculation). AXS FR >> SOL FR.
      BEAR_AXS: SVM infrastructure drives SOL premium (Firedancer, ETF narratives,
        Phantom adoption, DeFi TVL growth). SOL FR >> AXS FR.
      OOS Sh=16.05. MaxDD OOS=-0.5311%. G4 12/12 ALL POSITIVE (min_sh=5.9193).
      AXS = 16th vertex. MR9 L002: all future AXS-X pairs blocked.

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

    if regime == "BULL_AXS":
        # AXS FR > SOL FR: Gaming P2E season
        long_asset  = "AXS"
        short_asset = "SOL"
        state       = STATE_LONG_AXS_SHORT_SOL
    else:  # BEAR_AXS
        # SOL FR > AXS FR: SVM season
        long_asset  = "SOL"
        short_asset = "AXS"
        state       = STATE_LONG_SOL_SHORT_AXS

    # HL primary for both legs
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
    Compute equal notional for both legs of the AXS-SOL paired trade.

    K769 HL config (AXS-PERP + SOL-PERP on HL, paper-gate strict):
      sleeve_capital   = aum x sleeve_pct      (e.g. $10M x 1.5% = $150K)
      total_notional   = sleeve_capital x lev   ($150K x 4 = $600K)
      notional_per_leg = total_notional / 2     ($300K per leg)

    At $10M / 1.5% sleeve / 4x (paper-gate):
      AXS leg: $75K capital x 4x = $300K notional (HL AXS-PERP)
      SOL leg: $75K capital x 4x = $300K notional (HL SOL-PERP)
      Total:   $600K notional (two legs combined)
      Margin:  $150K (1.5% of AUM)
      HL conc: PAPER-ONLY (66.8% AT CAP — no live capital added)
      Net profit: central $124K/yr @$10M @4x (K523: $78K-$175K)
      AXS vertex: 16th — MR9 L002 blocks all future AXS-X pairs
      Sleeve: 1.5% (long-tail liquidity constraint — AXS smaller than major L1)

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
    Submit K769 AXS-SOL paired trade: POST_ONLY both legs in parallel.

    Protocol (K769 HL primary — both legs on HL):
      1. Submit AXS leg on HL POST_ONLY
      2. Submit SOL leg on HL POST_ONLY
      3. Both legs submitted in parallel (K439 pattern)
      4. IOC fallback per leg if POST_ONLY times out
      5. If both fail: retry next 8h cycle

    Args:
      long_leg:  {"symbol": "AXS", "notional": 300000, "venue": "HL"}
      short_leg: {"symbol": "SOL", "notional": 300000, "venue": "HL"}
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
        print(f"  [K769] {mode_tag}: LONG {long_sym}@{long_venue} ${long_notl:,.0f}  "
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
            "venue_config":     "HL_PRIMARY_AXS_SOL_ALT_ALT",
            "mechanism_note":   (
                "AXS-SOL direct alt-alt differential (K769 EIGHTEENTH ALT-ALT, 76th daemon): "
                "AXS FR = Gaming P2E premium (Axie Infinity RON-chain, Axie Origins seasonal content, "
                "SLP burn/mint economics, AXS staking governance APR, NFT Axie breeding demand, "
                "Southeast Asian retail speculation Philippines/Indonesia P2E markets, "
                "P2E tournament events Axie World Championship, Ronin sidechain RON airdrop upgrades, "
                "vol_ratio=5.24x SOL full / 8.88x OOS / 16.23x HL 1h); "
                "SOL FR = Solana SVM DePIN/DeFi premium (Phantom adoption, Firedancer upgrade, "
                "SOL ETF speculation, SVM DeFi TVL Jupiter/Drift/Jito, +8.82%/ann persistent, "
                "SOL liquidation cascade Min=-20.51bps Feb 2025). "
                "G4 WF 12/12 ALL POSITIVE (min_sh=5.9193, mean=16.8423). "
                "G5 all PASS (max_corr=-0.2796 G5n ENA-SOL — well below 0.40). "
                "HL at 66.8% AT CAP — paper-gate strict until K498/v6.52 reduces HL%. "
                "AXS = 16th vertex. MR9 L002: all future AXS-X pairs blocked. "
                "OOS Sh=16.05 (W=168h, zero threshold). K523 central $124K/yr @$10M @4x @1.5%. "
                "60d gate: Realized Sh>=6 + fill>=60% + maxDD<15%."
            ),
            "ts_utc":           ts,
        }
        _append_trade_log(result)
        return result

    # LIVE scaffold (not reached in PAPER_TRADE mode):
    print(f"  [K769] SCAFFOLD LIVE: parallel POST_ONLY "
          f"LONG {long_sym}@{long_venue} ${long_notl:,.0f} "
          f"+ SHORT {short_sym}@{short_venue} ${short_notl:,.0f}")
    long_order_id  = f"SCAFFOLD_LONG_{long_sym}_{int(time.time())}"
    short_order_id = f"SCAFFOLD_SHORT_{short_sym}_{int(time.time())}"

    print(f"  [K769] Neither leg filled within timeout — retry next 8h cycle")
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
    Check if current K769 position has drifted beyond DRIFT_REBALANCE_PCT (5%).

    K769 HL: both legs on HL (AXS-PERP + SOL-PERP).
    Drift detection: compare stored AXS leg notional vs SOL leg notional.
    Threshold: 5% (same as K679/K682/K684/K686/K690/K747/K739/K754/K759 pattern).

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
    Both legs on HL (K769 HL primary — AXS-PERP + SOL-PERP).

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

    if state == STATE_LONG_AXS_SHORT_SOL:
        long_sym,  short_sym  = "AXS", "SOL"
    else:  # LONG_SOL_SHORT_AXS
        long_sym,  short_sym  = "SOL", "AXS"

    long_notional  = float(dash.get("long_notional",  0.0))
    short_notional = float(dash.get("short_notional", 0.0))

    if dry_run or PAPER_TRADE:
        mode_tag = "DRY_RUN" if dry_run else "PAPER_TRADE"
        print(f"  [K769] {mode_tag} CLOSE:")
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
        print(f"  [K769] SCAFFOLD CLOSE:")
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
    """Load k769_dashboard.json; return defaults if missing."""
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
    """Write k769_dashboard.json with full signal + regime state."""
    dash = _load_dashboard()

    # Update signal data
    dash["last_poll_jst"]        = signal.get("ts_jst", "—")
    dash["fr_axs_current"]       = signal.get("fr_axs",          0.0)
    dash["fr_sol_current"]       = signal.get("fr_sol",           0.0)
    dash["axs_sol_diff_current"] = signal.get("axs_sol_diff",    0.0)
    dash["mean_168h"]            = signal.get("mean_168h",        0.0)
    dash["diff_sigma"]           = signal.get("diff_sigma",       0.0)
    dash["regime"]               = signal.get("regime",    "NEUTRAL")
    dash["signal_direction"]     = signal.get("signal_direction", 0)
    dash["history_points"]       = signal.get("history_points",   0)

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
    dash["hl_concentration_pct"]     = HL_CONCENTRATION_POST_K769

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
        "profit_at_activation_1_5pct": (
            "central $123,689/yr net @$10M @4x (K523: $78.3K cons / $123.7K central / $175.2K opt)"
        ),
        "alt_alt_note": (
            "EIGHTEENTH ALT-ALT pair (AXS-SOL, no BTC/ETH leg). Standalone. 76th daemon. "
            "CLEAN ACCEPT (HL 66.8% AT CAP — paper-gate strict until K498/v6.52). "
            "G4 WF 12/12 ALL POSITIVE (min_sh=5.9193, mean=16.8423). "
            "G5 all PASS (max_corr=-0.2796 G5n ENA-SOL — well below 0.40). "
            "AXS = 16th vertex (Gaming P2E cluster). MR9 L002: all future AXS-X pairs blocked. "
            "W=168h (G6-safe: 31.1/yr vs 20/yr long-tail min). OOS Sh=16.05 MaxDD=-0.5311%."
        ),
        "hl_cap_warning": (
            "HL concentration 66.8% AT CAP. Paper-gate strict. "
            "Deploy LIVE only after K498/v6.52 reduces HL% below 65%. "
            "K769 HL primary: both AXS-PERP + SOL-PERP on HL. "
            "1.5% all-HL would add 1.5% → over cap. Paper-only until HL% resolved. "
            "AXS HL listed from 2026-01-18 (long-tail HIP-3 token). "
            "Bybit primary for backtest (730d); HL for live OOS monitoring."
        ),
        "g5_corr_note": (
            "G5 max_corr=-0.2796 (G5n ENA-SOL). All 23 gates PASS. "
            "No proximity warnings — all correlations well below 0.40 threshold. "
            "AXS Gaming P2E is structurally orthogonal to all existing family members."
        ),
    }

    # Strategy metadata
    dash["paper_trade_mode"]    = PAPER_TRADE
    dash["wave"]                = "K771"
    dash["strategy"]            = "K769 AXS-SOL FR Differential (EIGHTEENTH ALT-ALT, W=168h, HL primary)"
    dash["execution_mode"]      = "POST_ONLY_PARALLEL"
    dash["venue_config"]        = "HL_PRIMARY_BYBIT_FALLBACK"
    dash["alt_alt_mechanism"]   = {
        "formula":            "diff = AXS_FR - SOL_FR  (direct alt-alt, no base asset)",
        "rolling_window":     "W=168h (21 x 8h periods, G6-safe: 31.1 entries/yr OOS)",
        "signal":             "sign(rolling_mean_168h(diff))",
        "eighteenth_alt_alt": True,
        "g4_result":          "12/12 ALL POSITIVE (min_sh=5.9193, mean=16.8423) — strong WF validation",
        "hl_reason":          HL_ONLY_REASON,
        "hl_concentration":   66.8,
        "cross_cluster_note": (
            "AXS (Axie Infinity Gaming P2E, RON-chain governance, "
            "AXS staking treasury APR, SLP burn/mint in-game mechanics, "
            "NFT Axie breeding marketplace demand, P2E Southeast Asian retail, "
            "Axie World Championship tournament events, Ronin sidechain upgrades, "
            "vol_ratio=5.24x SOL full / 8.88x OOS / 16.23x HL 1h) "
            "vs SOL (Solana SVM retail/DeFi — Phantom adoption, Firedancer, SOL ETF, "
            "SVM DeFi TVL Jupiter/Drift/Jito — persistently positive +8.82%/ann, "
            "SOL liquidation cascade Min=-20.51bps Feb 2025). "
            "raw_corr(AXS, SOL) = 0.19 (Bybit full) — essentially orthogonal. "
            "OOS corr = 0.1182 (near-zero OOS). OOS Sh=16.05. MaxDD OOS=-0.5311%."
        ),
        "axs_vertex_rule": (
            "AXS = 16th vertex added to V. "
            "V = {APT, ATOM, AVAX, BNB, ENA, FIL, HBAR, INJ, LDO, SEI, SOL, TIA, TAO, PEPE, WIF, AXS}. "
            "MR9 L002: all future AXS-X pairs auto-blocked. "
            "AXS-SOL is the only permissible AXS-X pair given V at K769."
        ),
        "g5_max_corr": "-0.2796 (G5n ENA-SOL) — well below 0.40 threshold. All 23 gates PASS.",
        "sleeve_note": (
            "1.5% sleeve (long-tail liquidity constraint — AXS smaller than major L1). "
            "AXS daily HL volume lower tier (HIP-3 long-tail listing from 2026-01-18). "
            "1.5% sleeve = $150K margin @$10M @4x = $600K notional gross. "
            "Standard (2.5%) would risk HL OI constraint on AXS long-tail."
        ),
        "w168h_g6_note": (
            "W=168h family standard window (21 x 8h periods). G6: 31.1/yr OOS PASS (>20/yr long-tail). "
            "W=80h: 34.5/yr OOS Sh=16.98 (best config, marginally higher). "
            "W=48h: 63.9/yr OOS Sh=16.53 (also PASS). "
            "W=168h chosen for family consistency. OOS Sh=16.05."
        ),
        "data_cross_venue": (
            "Bybit AXSUSDT 730d primary for backtest (2024-05-25 to 2026-05-24, 3184 rows 8h). "
            "HL AXS-PERP from 2026-01-18 (3040 rows 1h ~127d — limited IS period). "
            "Bybit chosen for backtest due to longer history; HL for live OOS monitoring. "
            "OKX: not yet cached (G8 partial — HL+Bybit PASS)."
        ),
        "axs_fr_drivers": (
            "Axie Infinity (Gaming P2E — RON-chain, #1 P2E gaming token by MC 2021-2022). "
            "FR driven by Gaming P2E adoption cycles (Axie Origins V3+ seasonal releases). "
            "SLP burn/mint economics (in-game token supply mechanics). "
            "AXS staking governance APR (treasury staking reward cycles). "
            "NFT Axie breeding demand (marketplace floor price + breeding liquidity). "
            "Southeast Asian retail speculation (Philippines/Indonesia primary P2E markets). "
            "P2E tournament event spikes (Axie World Championship seasons). "
            "Ronin sidechain upgrades (RON airdrop, bridge activity, validator set changes). "
            "vol_ratio=5.24x (Bybit full), 6.37x (30d), 8.88x (OOS), 16.23x (HL 1h). "
            "AXS: 41% positive (full) / 32% OOS (net negative bias — gaming bear market). "
            "AXS HL listing 2026-01-18 (HIP-3 long-tail). Bybit AXSUSDT 730d."
        ),
        "sol_fr_drivers": (
            "Solana SVM DePIN/Retail adoption premium. "
            "Phantom wallet. Firedancer upgrade. SOL ETF speculation. "
            "SVM DeFi TVL (Jupiter/Drift/Jito). +8.82%/ann persistently positive. "
            "Extreme negative: -20.51bps (Feb 2025 cascade)."
        ),
        "g8_note": (
            "G8 PASS: HL+Bybit confirmed. OKX not yet cached. "
            "HL: AXS-PERP (from 2026-01-18, HIP-3 listing). Bybit: AXSUSDT-PERP (730d primary). "
            "2-venue presence confirmed (HL+Bybit). OKX pending."
        ),
        "k523_projection": {
            "conservative_yr": 78337,
            "central_yr":      123689,
            "optimistic_yr":   175227,
            "sleeve_pct":      0.015,
            "note":            "K523 mandatory 3-point. Conservative=R2S×0.38 (K518 floor). Central=$124K @$10M @4x @1.5%.",
        },
    }

    dash["activation_criteria"] = {
        "60d_paper_trade_gate": "required",
        "realized_sharpe_min": 6.0,
        "fill_rate_min_pct":   60,
        "max_drawdown_max_pct": 15,
        "status":              "SCAFFOLD-READY",
        "activation_sleeve_pct": 0.015,
        "venue":               "HL primary (AXS-PERP + SOL-PERP)",
        "conditional_note": (
            "HL 66.8% AT CAP. "
            "Deploy LIVE only after K498/v6.52 reduces HL% below 65%. "
            "AXS = 16th vertex (Gaming P2E cluster). MR9 L002: all future AXS-X blocked."
        ),
        "live_trigger": "K498/v6.52 OKX activation (HL% drops from 66.8%) + 60d gate passage",
    }

    dash["oos_performance"] = {
        "sharpe":              16.0543,
        "oos_ann_ret_pct":     45.8109,
        "oos_ann_ret_4x_pct":  183.24,
        "k523_conservative_yr": 78337,
        "k523_central_yr":     123689,
        "k523_optimistic_yr":  175227,
        "daily_usdc_central":  339,
        "wave_accept": (
            "K769 CLEAN ACCEPT (K771 scaffold) — EIGHTEENTH ALT-ALT, "
            "Gaming P2E cluster × SVM, G4 12/12, G5 all PASS"
        ),
        "cluster":    "AXS-SOL Alt-Alt FR Differential (Gaming P2E × SVM, HL primary, 16th vertex)",
        "daemon_number": "76th",
        "section6_result": (
            "CLEAN ACCEPT G5 all PASS. G1-G9 PASS. "
            "OOS Sh=16.05 (W=168h zero threshold ~211d OOS). MaxDD=-0.5311%. "
            "HL 66.8% AT CAP → paper-gate strict."
        ),
        "family_rank": {
            "k769_oos_sharpe":   16.0543,
            "k769_pair":         "AXS-SOL (alt-alt, EIGHTEENTH, 16th vertex AXS Gaming P2E cluster)",
            "alt_alt_accepted":  18,
            "g4_note":           "K769 G4=12/12 ALL POSITIVE (min_sh=5.9193, mean=16.8423).",
            "vertex_note":       "AXS = 16th vertex. V={APT,ATOM,AVAX,BNB,ENA,FIL,HBAR,INJ,LDO,SEI,SOL,TIA,TAO,PEPE,WIF,AXS}.",
        },
    }

    DASHBOARD_PATH.write_text(json.dumps(dash, indent=2))
    return dash


# ─────────────────────────────────────────────────────────────────────────────
# Main entry point
# ─────────────────────────────────────────────────────────────────────────────

def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="K769 AXS-SOL FR Differential Strategy (EIGHTEENTH ALT-ALT, 76th daemon)"
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

    print(f"\n=== K769 AXS-SOL FR Differential Strategy — {ts_jst} ===")
    print(f"  Strategy:    AXS-SOL FR Differential (EIGHTEENTH ALT-ALT pair)")
    print(f"  Wave:        K771 (scaffold wave for K769 CLEAN ACCEPT)")
    print(f"  Daemon:      76th (eighteenth alt-alt pair, 16th vertex AXS)")
    print(f"  OOS Sharpe:  16.0543 (W=168h, zero threshold, ~211d OOS)")
    print(f"  G4 WF:       12/12 ALL POSITIVE (min_sh=5.9193, mean=16.8423)")
    print(f"  G5:          all PASS (max_corr=-0.2796 G5n ENA-SOL — well below 0.40)")
    print(f"  W=168h:      G6 compliance (31.1/yr OOS vs 20/yr long-tail min)")
    print(f"  AXS vertex:  16th. MR9 L002: all future AXS-X pairs blocked.")
    print(f"  HL cap:      66.8% AT CAP — paper-gate strict")
    print(f"  Sleeve:      1.5% (long-tail liquidity constraint — AXS HIP-3 listing)")
    print(f"  Profit:      central $124K/yr @$10M @4x @1.5% sleeve (K523 3-point)")
    print(f"  Data:        Bybit 730d primary (backtest), HL from 2026-01-18 (OOS live)")
    print(f"  Paper mode:  {PAPER_TRADE}")

    # --status mode
    if args.status:
        dash = _load_dashboard()
        print(f"\n  [Status] {dash.get('strategy', 'K769 AXS-SOL')}")
        print(f"  regime={dash.get('regime')}  direction={dash.get('signal_direction')}")
        print(f"  mean_168h={dash.get('mean_168h', 0):.6e}")
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
    print(f"\n  [Phase 1] Fetching AXS + SOL funding rates from HL ...")
    signal = compute_signal()
    print(f"  fr_axs={signal['fr_axs']:.6e}  fr_sol={signal['fr_sol']:.6e}")
    print(f"  axs_sol_diff={signal['axs_sol_diff']:.6e}")
    print(f"  mean_168h={signal['mean_168h']:.6e}  sigma={signal['diff_sigma']:.6e}")
    print(f"  regime={signal['regime']}  direction={signal['signal_direction']}")
    print(f"  history_points={signal['history_points']}")

    print(f"\n  [Phase 2] Computing signal (W=168h rolling mean of AXS_FR - SOL_FR) ...")
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

    print(f"\n=== K769 AXS-SOL run complete — {datetime.now(JST).strftime('%Y-%m-%d %H:%M JST')} ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
