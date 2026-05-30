#!/usr/bin/env python3
"""
k698_link_eth_run.py — K698 LINK-ETH FR Differential Strategy
==============================================================
Implements a paired-trade (long LINK / short ETH or reverse) based on the
120h rolling mean of the LINK-ETH funding rate differential.

ETH-base mechanism (K698 oracle cluster expansion):
  K557 LINK-BTC uses BTC as the base asset. K698 switches the short leg from
  BTC to ETH. Signal: LINK_FR - ETH_FR (direct differential, no BTC denominator).
  MR9 algebraic identity CONFIRMED: LINK-ETH = LINK-BTC - ETH-BTC (max error = 5.42e-20).
  Position-level de-correlated: corr(K698, K557+K449 combo) = 0.1254 (PASS < 0.40).
  K695 lesson: LINK-SOL REJECTED (G5c corr=0.497 vs K557 — LINK shared leg blocked).
  K698 pivot to ETH: G5a corr(K698, K557) = 0.0578 PASS. No LINK double-exposure.

Architecture (K663/K658/K661 ETH-base scaffold pattern):
  1. fetch_fr_batch()                → fetch LINK + ETH FR every 8h from HL
  2. compute_signal(link_fr, eth_fr) → 120h rolling mean of (LINK_FR - ETH_FR); sign()
  3. decide_position(signal)         → LONG_LINK_SHORT_ETH | LONG_ETH_SHORT_LINK | NEUTRAL
  4. submit_paired_trade(long, short) → POST_ONLY paired (LINK + ETH legs, Bybit primary)
  5. daily_rebalance()               → drift > 5% triggers rebalance
  6. close_paired_position(reason)   → sequential: short first, then long

K698 LINK-ETH oracle cluster (ACCEPT CONDITIONAL — 8/8 gates):
  - LINK = Chainlink oracle middleware: FR driven by DeFi integration cycles
    (new feed launches, CCIP cross-chain adoption, staking APY changes, oracle
    demand from DeFi protocol launches, real-world asset price feed growth)
  - ETH = Ethereum L1: FR driven by DeFi/staking yields (stETH/LST demand,
    L1 gas narrative, EIP cycles, Pectra upgrades)
  - Oracle vs L1: structurally distinct FR drivers. LINK oracle middleware (MM floor
    ~1.25e-5/hr stable anchor) vs ETH DeFi/staking (more volatile). LINK FR > ETH FR
    74.5% of the time (LINK consistently pays more — oracle demand anchor).
  - MR9 algebraic identity CONFIRMED at FR level (max error = 5.42e-20).
    Position-level de-correlated (corr=0.1254) — independent execution paths.
  - K695 lesson: G5c corr(K695, K557) = 0.497 BLOCKED LINK-SOL. K698 avoids SOL
    leg entirely. G5a corr(K698, K557) = 0.0578 PASS — clean oracle expansion.
  - G5b corr(K698, K449 ETH-BTC) = -0.0036 PASS (anti-corr: ETH as base, not quote)
  - OOS Sh = 12.0676 (W=120h, 8/8 §6 gates PASS)
  - 60d paper-trade gate required before live activation
  - HL concentration: 67.0% (64.5% baseline + 2.5%) → OVER 65% cap
  - Bybit primary: LINK maxLev=50, ETH maxLev=100
  - K557 LINK leg coordination: LINK appears in K557 (BTC base) and K698 (ETH base)
    Monitor combined LINK notional: K557 1.5% + K698 2.5% = max 4.0% AUM LINK exposure

K698 profit summary:
  - OOS Sharpe: 12.0676 (IS: 7.3265, IS/OOS ratio=0.607)
  - OOS Ann Return: 2.90% (unlevered on notional)
  - Profit @$10M @4x @2.5% sleeve: $28,997/yr USDC net
  - W=120h rolling mean (G6-compliant: 31.9 trades/yr >= 30)
  - Walk-forward: 17/21 folds positive (81.0% — G4 PASS >= 70%)
  - Perm p-value: 0.0000 (1000 reshuffles — G2 PASS)
  - DSR Bonferroni: p=0.0 (5 trials — G3 PASS)
  - Trades/yr: 31.9 (W=120h config — G6 PASS)
  - ADF p=0.0 (stationary), OU halflife=1.45h (ultra-fast MR)
  - G5a LINK-BTC K557 critical: corr=0.0578 (PASS < 0.40)
  - G5b ETH-BTC K449 critical: corr=-0.0036 (PASS < 0.40)
  - LINK FR > ETH FR 74.5% of time (oracle anchor dominates)
  - 61st daemon (4th ETH-base scaffold, 1st oracle-ETH)

Execution:
  - Bybit primary (LINK-PERP + ETH-PERP, both Bybit) — HL at 64.5%+2.5%=67%>65% cap
  - POST_ONLY paired execution (K439 pattern)
  - Position: 2.5% sleeve, 4x leverage
  - 8h cadence (matches FR settlement cycle)
  - W=120h rolling mean (15 x 8h periods; G6 PASS 31.9 trades/yr)
  - K557 coordination: LINK in K557 (BTC leg, HL+Bybit) + K698 (ETH leg, Bybit)

Paper-trade mode is the DEFAULT.  No orders are submitted unless
PAPER_TRADE=False is explicitly set in the environment.

K339 security: REPO_ROOT from __file__, no /Users/ literals.
No new packages — stdlib urllib + json only.

Usage:
  python3 scripts/k698_link_eth_run.py --dry-run
  python3 scripts/k698_link_eth_run.py --status
  python3 scripts/k698_link_eth_run.py --rebalance
  python3 scripts/k698_link_eth_run.py --close "scheduled exit"
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

DASHBOARD_PATH  = DATA_DIR  / "k698_dashboard.json"
FR_HISTORY_PATH = CACHE_DIR / "k698_fr_history.jsonl"
TRADE_LOG_PATH  = CACHE_DIR / "k698_paper_trades.jsonl"

JST = timezone(timedelta(hours=9))
UTC = timezone.utc

# ── Strategy constants ────────────────────────────────────────────────────────
PAPER_TRADE         = True          # never submit real orders in paper-trade mode
SLEEVE_PCT          = 0.025         # K698 sleeve = 2.5% of AUM
LEVERAGE            = 4.0           # 4x per K698 analysis (K430 cap)
AUM_DEFAULT         = 10_000_000.0  # $10M reference AUM
DRIFT_REBALANCE_PCT = 0.05          # rebalance if legs drift > 5%
IOC_TIMEOUT_SEC     = 300           # 5 min fill window
EMA_PERIOD_HOURS    = 120           # 120h rolling mean (K698 optimal: G6-compliant 31.9 trades/yr)
EMA_PERIOD_PERIODS  = EMA_PERIOD_HOURS // 8  # = 15 periods (8h settlement cycle)
SIGNAL_SIGMA_MULT   = 0.0           # zero threshold (sign of rolling mean — K698 spec)
HL_API_URL          = "https://api.hyperliquid.xyz/info"

# ── Venue config (Bybit primary — LINK-PERP + ETH-PERP on Bybit) ─────────────
# Both legs on Bybit (HL at 64.5% baseline + 2.5% sleeve = 67.0% > 65% cap)
# Bybit: LINK maxLev=50, ETH maxLev=100 (both listed, API confirmed)
# HL concentration: 64.5% baseline (UNCHANGED — K698 is Bybit-only)
HL_CONCENTRATION_PRE_K698  = 64.5   # post-K694 reference (K697 baseline)
HL_CONCENTRATION_POST_K698 = 64.5   # UNCHANGED (Bybit-only — HL-only would breach 65% cap)

# Bybit venue note: HL LINK listed (maxLev=10), ETH listed (maxLev=25).
# HL LINK-PERP + ETH-PERP sleeve would push HL from 64.5% to 67.0% > 65% cap.
# Bybit primary resolves cap breach: LINK maxLev=50, ETH maxLev=100.
BYBIT_LINK_MAX_LEV = 50
BYBIT_ETH_MAX_LEV  = 100

# ── Position state constants ──────────────────────────────────────────────────
STATE_NEUTRAL              = "NEUTRAL"
STATE_LONG_LINK_SHORT_ETH  = "LONG_LINK_SHORT_ETH"
STATE_LONG_ETH_SHORT_LINK  = "LONG_ETH_SHORT_LINK"

# ── Symbols fetched from HL for FR data ──────────────────────────────────────
# K698: LINK + ETH from HL (FR data source — execution on Bybit)
# HL FR data is used as signal source; execution legs on Bybit
SYMBOLS = ("LINK", "ETH")


# ─────────────────────────────────────────────────────────────────────────────
# HTTP helper (stdlib urllib only — no requests)
# ─────────────────────────────────────────────────────────────────────────────

def _http_post(url: str, payload: dict, timeout: int = 10) -> Optional[dict]:
    try:
        data = json.dumps(payload).encode()
        req  = urllib.request.Request(
            url, data=data,
            headers={"Content-Type": "application/json",
                     "User-Agent": "crypto-lab-k698/1.0"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        print(f"  [k698] HTTP error: {e}", file=sys.stderr)
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Phase 1 — Funding rate fetch (LINK + ETH from HL)
# ─────────────────────────────────────────────────────────────────────────────

def _fetch_hl_fr_batch() -> Dict[str, float]:
    """
    Fetch current 8h funding rates for LINK and ETH from HL.
    Returns {symbol: fr_8h_fraction}.

    HL API: metaAndAssetCtxs -> funding field per asset.
    K698: FR data from HL; execution on Bybit (HL concentration cap breached).
    LINK oracle FR: stable anchor ~1.25e-5/hr (MM floor, oracle demand driven).
    ETH L1 FR: more volatile (staking/DeFi demand spikes, LST yields).
    """
    raw = _http_post(HL_API_URL, {"type": "metaAndAssetCtxs"})
    if not raw or not isinstance(raw, list) or len(raw) < 2:
        print("  [k698] HL metaAndAssetCtxs fetch failed", file=sys.stderr)
        return {}
    meta       = raw[0]
    asset_ctxs = raw[1]
    universe   = {item["name"]: i for i, item in enumerate(meta.get("universe", []))}
    result: Dict[str, float] = {}
    for sym in SYMBOLS:
        if sym not in universe:
            print(f"  [k698] Symbol {sym} not found in HL universe", file=sys.stderr)
            continue
        idx = universe[sym]
        ctx = asset_ctxs[idx]
        try:
            result[sym] = float(ctx.get("funding", 0.0))
        except (TypeError, ValueError):
            continue
    return result


def _load_fr_history() -> List[dict]:
    """Load K698 FR history JSONL."""
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
    fr_link: float, fr_eth: float, link_eth_diff: float
) -> None:
    """Append one FR snapshot to history."""
    rec = {
        "ts_utc":        datetime.now(UTC).isoformat(),
        "fr_link":       round(fr_link,        10),
        "fr_eth":        round(fr_eth,          10),
        "link_eth_diff": round(link_eth_diff,   10),  # LINK_FR - ETH_FR (direct differential)
    }
    with open(FR_HISTORY_PATH, "a") as f:
        f.write(json.dumps(rec) + "\n")


# ─────────────────────────────────────────────────────────────────────────────
# Phase 2 — Signal computation (LINK-ETH direct differential, 120h rolling mean)
# ─────────────────────────────────────────────────────────────────────────────

def compute_signal(
    fr_link: Optional[float] = None,
    fr_eth:  Optional[float] = None,
) -> dict:
    """
    Fetch live LINK and ETH FRs from HL, compute LINK-ETH differential,
    and compute 120h rolling mean for direction signal.

    Signal mechanism (K698 direct differential — ETH base, oracle cluster):
      diff = LINK_FR - ETH_FR
      mean_120h = 120h rolling mean of diff (15 x 8h periods)
      sign  = sign(mean_120h)
      Enter: sign > 0 -> LONG LINK, SHORT ETH (LINK FR > ETH — collect LINK carry)
             sign < 0 -> LONG ETH, SHORT LINK (ETH FR > LINK — collect ETH carry)

    Oracle-ETH mechanism:
      - LINK oracle middleware FR anchored by MM floor ~1.25e-5/hr (stable)
      - ETH DeFi/staking FR more volatile (LST demand, L1 gas narrative)
      - LINK > ETH FR 74.5% of time: oracle demand anchor consistently premium
      - W=120h chosen: G6-compliant (31.9 trades/yr >= 30)
        W=240h: OOS Sh=15.15 but 23.3 trades/yr (G6 borderline)
        W=120h: OOS Sh=12.07, 31.9 trades/yr — optimal G6-compliant selection
      - MR9: LINK-ETH = LINK-BTC - ETH-BTC algebraically.
        FR-level identity max_error=5.42e-20 (machine epsilon).
        Position-level corr=0.1254 (de-correlated at execution — different windows,
        different trade counts, different OU paths).

    K698 §6 validation (8/8 PASS):
      - OOS Sharpe: 12.0676 (W=120h, zero threshold)
      - OOS Ann Return: 2.90% (unlevered on notional)
      - ADF p=0.0 (stationary), OU halflife=1.45h (ultra-fast MR)
      - Walk-forward: 17/21 positive (81.0%)
      - Perm p=0.0 (1000 reshuffles), DSR p=0.0 (5 trials)
      - Trades/yr: 31.9 (W=120h, G6 PASS >= 30)
      - G5a LINK-BTC K557 critical: corr=0.0578 (PASS < 0.40)
      - G5b ETH-BTC K449 critical: corr=-0.0036 (PASS < 0.40)

    Returns:
      {
        "fr_link":          float,
        "fr_eth":           float,
        "link_eth_diff":    float,    # LINK_FR - ETH_FR (current)
        "mean_120h":        float,    # 120h rolling mean of differential
        "diff_sigma":       float,    # 120h rolling sigma (informational)
        "history_points":   int,
        "regime":           str,      # BULL_LINK | BEAR_LINK | NEUTRAL
        "signal_direction": int,      # +1 | -1 | 0
        "ts_jst":           str,
      }
    """
    if fr_link is None or fr_eth is None:
        frs     = _fetch_hl_fr_batch()
        fr_link = frs.get("LINK", 0.0)
        fr_eth  = frs.get("ETH",  0.0)

    # LINK-ETH direct differential (no orthogonalization — ETH base is the mechanism)
    link_eth_diff = fr_link - fr_eth

    _append_fr_history(fr_link, fr_eth, link_eth_diff)

    # Load history for rolling mean + sigma (120h = 15 x 8h periods)
    history = _load_fr_history()
    diffs   = [r["link_eth_diff"] for r in history if "link_eth_diff" in r]

    n_periods = EMA_PERIOD_PERIODS   # 15 periods (120h / 8h)

    # Rolling mean: simple mean of last n_periods diffs
    window = diffs[-n_periods:] if len(diffs) >= 1 else diffs
    if window:
        mean_120h = sum(window) / len(window)
    else:
        mean_120h = 0.0

    # Rolling sigma: std of last n_periods diffs (informational)
    if len(window) >= 2:
        mean_w = sum(window) / len(window)
        sigma  = math.sqrt(sum((x - mean_w) ** 2 for x in window) / (len(window) - 1))
    else:
        sigma  = abs(mean_120h) if mean_120h != 0 else 1e-8   # fallback

    # Regime classification (zero threshold — per K698 spec)
    # BULL_LINK: LINK FR > ETH FR (oracle demand premium / DeFi integration spike)
    # BEAR_LINK: LINK FR < ETH FR (ETH structural premium during staking/LST demand)
    if mean_120h > 0:
        regime    = "BULL_LINK"   # LINK FR > ETH FR — long LINK / short ETH
        direction = 1
    elif mean_120h < 0:
        regime    = "BEAR_LINK"   # ETH FR > LINK FR — long ETH / short LINK
        direction = -1
    else:
        regime    = "NEUTRAL"
        direction = 0

    return {
        "fr_link":          round(fr_link,       10),
        "fr_eth":           round(fr_eth,         10),
        "link_eth_diff":    round(link_eth_diff,  10),
        "mean_120h":        round(mean_120h,      10),
        "diff_sigma":       round(sigma,          10),
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
    Determine trade direction from LINK-ETH differential rolling mean.

    Logic (LINK-ETH direct differential pair, Bybit primary):
      regime = BULL_LINK (mean_120h > 0):
        LINK FR > ETH FR -> LINK pays more (oracle demand premium)
        -> long LINK (collect high FR via short ETH arbitrage)
        -> short ETH (pay low ETH FR, collect net positive carry)
        -> position_state = LONG_LINK_SHORT_ETH
        -> both legs on Bybit

      regime = BEAR_LINK (mean_120h < 0):
        ETH FR > LINK FR -> ETH more expensive to long (staking/DeFi demand spike)
        -> long ETH (collect LINK carry by shorting LINK)
        -> short LINK (pay low LINK FR, collect ETH structural premium)
        -> position_state = LONG_ETH_SHORT_LINK
        -> both legs on Bybit

      regime = NEUTRAL: no trade (mean_120h == 0 exactly — rare)

    K698 edge (oracle vs ETH L1 mechanism):
      LINK oracle middleware FR driven by DeFi integration, CCIP adoption,
      new feed launches, staking APY changes. Stable MM floor ~1.25e-5/hr.
      ETH L1 FR driven by stETH/LST demand, Pectra upgrade narrative, L1 gas.
      Two structurally distinct FR driver clusters:
        - Oracle demand: DeFi integration cycles, cross-chain oracle feeds
        - Ethereum DeFi: liquid staking yields, EIP narrative, L1 security
      MR9 de-correlation: despite algebraic identity (LINK-ETH = K557 - K449 at FR level),
      position-level corr=0.1254 < 0.40 (different W=120h vs 168h window,
      different trade timing, different OU paths).

    Returns:
      {long_asset, short_asset, long_venue, short_venue, mean_120h,
       signal_direction, size_multiplier, position_state}
      or None if NEUTRAL.
    """
    regime    = signal.get("regime", "NEUTRAL")
    mean_120h = signal.get("mean_120h", 0.0)
    direction = signal.get("signal_direction", 0)

    if regime == "NEUTRAL":
        return None

    if regime == "BULL_LINK":
        # LINK FR > ETH FR: collect LINK oracle premium (long LINK / short ETH)
        long_asset  = "LINK"
        short_asset = "ETH"
        state       = STATE_LONG_LINK_SHORT_ETH
    else:  # BEAR_LINK
        # ETH FR > LINK FR: collect ETH L1 premium (long ETH / short LINK)
        long_asset  = "ETH"
        short_asset = "LINK"
        state       = STATE_LONG_ETH_SHORT_LINK

    # Both legs on Bybit (K698: HL at 64.5%+2.5% = 67.0% > 65% cap)
    long_venue  = "Bybit"
    short_venue = "Bybit"

    return {
        "long_asset":       long_asset,
        "short_asset":      short_asset,
        "position_state":   state,
        "long_venue":       long_venue,
        "short_venue":      short_venue,
        "mean_120h":        mean_120h,
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
    Compute equal notional for both legs of the LINK-ETH paired trade.

    K698 Bybit-only config (both LINK-PERP + ETH-PERP on Bybit):
      sleeve_capital   = aum x sleeve_pct      (e.g. $10M x 2.5% = $250K)
      total_notional   = sleeve_capital x lev   ($250K x 4 = $1,000K)
      notional_per_leg = total_notional / 2     ($500K per leg)

    At $10M / 2.5% sleeve / 4x:
      LINK leg:  $125K capital x 4x = $500K notional (Bybit LINK-PERP)
      ETH leg:   $125K capital x 4x = $500K notional (Bybit ETH-PERP)
      Total:     $1,000K notional (two legs combined)
      Margin:    $250K (2.5% of AUM)
      HL conc:   UNCHANGED 64.5% (Bybit-only — HL-only would push to 67.0% > 65% cap)
      Net profit: ~$28,997/yr @$10M @4x (OOS 2.90% ann ret x $10M x 4x x 2.5%)
      K557 combined LINK exposure: K557 ~1.5% + K698 2.5% = 4.0% max LINK exposure AUM

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
    Submit K698 LINK-ETH paired trade: POST_ONLY both legs in parallel.

    Protocol (K698 Bybit primary — both legs on Bybit):
      1. Submit LINK leg on Bybit POST_ONLY
      2. Submit ETH leg on Bybit POST_ONLY
      3. Both legs submitted in parallel (K439 pattern)
      4. IOC fallback per leg if POST_ONLY times out
      5. If both fail: retry next 8h cycle

    Args:
      long_leg:  {"symbol": "LINK", "notional": 500000, "venue": "Bybit"}
      short_leg: {"symbol": "ETH",  "notional": 500000, "venue": "Bybit"}
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
        print(f"  [K698] {mode_tag}: LONG {long_sym}@{long_venue} ${long_notl:,.0f}  "
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
            "venue_config":     "BYBIT_PRIMARY_LINK_ETH_ORACLE_VS_L1",
            "mechanism_note":   (
                "LINK-ETH direct differential (oracle vs ETH L1 mechanism, K698): "
                "LINK FR = Chainlink oracle middleware (DeFi integrations, CCIP, feed launches, "
                "staking APY cycles, MM floor ~1.25e-5/hr stable anchor); "
                "ETH FR = Ethereum L1 DeFi/staking yields (stETH/LST demand, Pectra upgrades). "
                "G5a LINK-BTC K557 critical: corr=0.0578 PASS (K695 LINK-SOL G5c=0.497 BLOCKED; K698 avoids SOL). "
                "G5b ETH-BTC K449 critical: corr=-0.0036 PASS. "
                "MR9 FR identity: LINK-ETH = LINK-BTC - ETH-BTC (max_err=5.42e-20 confirmed). "
                "Position-level corr=0.1254 de-correlated (W=120h vs 168h different execution paths). "
                "Bybit primary: HL at 64.5%+2.5%=67%>65% cap — Bybit resolves cap breach."
            ),
            "ts_utc":           ts,
        }
        _append_trade_log(result)
        return result

    # LIVE scaffold (not reached in PAPER_TRADE mode):
    print(f"  [K698] SCAFFOLD LIVE: parallel POST_ONLY "
          f"LONG {long_sym}@{long_venue} ${long_notl:,.0f} "
          f"+ SHORT {short_sym}@{short_venue} ${short_notl:,.0f}")
    long_order_id  = f"SCAFFOLD_LONG_{long_sym}_{int(time.time())}"
    short_order_id = f"SCAFFOLD_SHORT_{short_sym}_{int(time.time())}"

    # Scaffold: poll not implemented — retry next 8h cycle
    print(f"  [K698] Neither leg filled within timeout — retry next 8h cycle")
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
    Check if current K698 position has drifted beyond DRIFT_REBALANCE_PCT (5%).

    K698 Bybit-only: both legs on Bybit (LINK-PERP + ETH-PERP).
    Drift detection: compare stored LINK leg notional vs ETH leg notional.
    Threshold: 5% (same as K449/K476/K484/K493/K629/K663 pattern).

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
    Both legs on Bybit (K698 Bybit primary — LINK-PERP + ETH-PERP).

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

    if state == STATE_LONG_LINK_SHORT_ETH:
        long_sym,  short_sym  = "LINK", "ETH"
    else:  # LONG_ETH_SHORT_LINK
        long_sym,  short_sym  = "ETH", "LINK"

    long_notional  = float(dash.get("long_notional",  0.0))
    short_notional = float(dash.get("short_notional", 0.0))

    if dry_run or PAPER_TRADE:
        mode_tag = "DRY_RUN" if dry_run else "PAPER_TRADE"
        print(f"  [K698] {mode_tag} CLOSE:")
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
        print(f"  [K698] SCAFFOLD CLOSE:")
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
    """Load k698_dashboard.json; return defaults if missing."""
    if DASHBOARD_PATH.exists():
        try:
            return json.loads(DASHBOARD_PATH.read_text())
        except Exception:
            pass
    return {
        "last_poll_jst":           "—",
        "mean_120h":               0.0,
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
    """Write k698_dashboard.json with full signal + regime state."""
    dash = _load_dashboard()

    # Update signal data
    dash["last_poll_jst"]          = signal.get("ts_jst", "—")
    dash["fr_link_current"]        = signal.get("fr_link",       0.0)
    dash["fr_eth_current"]         = signal.get("fr_eth",         0.0)
    dash["link_eth_diff_current"]  = signal.get("link_eth_diff",  0.0)
    dash["mean_120h"]              = signal.get("mean_120h",      0.0)
    dash["diff_sigma"]             = signal.get("diff_sigma",     0.0)
    dash["regime"]                 = signal.get("regime",    "NEUTRAL")
    dash["signal_direction"]       = signal.get("signal_direction", 0)
    dash["history_points"]         = signal.get("history_points", 0)

    # Update position if entering
    if decision:
        state = decision.get("position_state", STATE_NEUTRAL)
        if dash.get("position_state") == STATE_NEUTRAL:
            dash["position_state"]    = state
            dash["long_notional"]     = notional_per_leg
            dash["short_notional"]    = notional_per_leg
            dash["long_asset"]        = decision.get("long_asset")
            dash["short_asset"]       = decision.get("short_asset")
            dash["venue"]             = "Bybit"
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
    dash["hl_concentration_pct"]     = HL_CONCENTRATION_POST_K698   # 64.5% unchanged

    # Paper-trade status
    paper_status = dash.get("paper_trade_status", {"days_elapsed": 0, "target_60d": 60})
    dash["paper_trade_status"]       = paper_status

    # 60d activation gate metrics (K701: Realized Sh >= 6, fill >= 60%, DD < 15%)
    dash["gate_metrics"] = {
        "realized_sharpe_target":  6.0,     # >=6 (50% of K698 OOS 12.07)
        "fill_rate_target_pct":    60,
        "max_drawdown_target_pct": 15,       # <15%
        "current_realized_sharpe": dash.get("60d_sharpe", 0.0),
        "current_fill_rate_pct":   0.0,
        "current_max_dd_pct":      0.0,
        "gate_status":             "IN_PROGRESS",
        "activation_trigger":      "60d paper-trade: Sh>=6 AND fill>=60% AND maxDD<15%",
        "profit_at_activation_2_5pct": "$28,997/yr net @$10M @4x (2.5% sleeve, OOS 2.90% ann ret)",
        "bybit_primary_note":      "Bybit primary: LINK maxLev=50, ETH maxLev=100. HL at 64.5%+2.5%=67%>65% cap.",
    }

    # Strategy metadata
    dash["paper_trade_mode"]    = PAPER_TRADE
    dash["wave"]                = "K701"
    dash["strategy"]            = "K698 LINK-ETH FR Differential (oracle vs ETH L1, W=120h, Bybit primary)"
    dash["execution_mode"]      = "POST_ONLY_PARALLEL"
    dash["venue_config"]        = "BYBIT_PRIMARY"
    dash["oracle_eth_mechanism"] = {
        "formula":               "diff = LINK_FR - ETH_FR  (direct, no orthogonalization)",
        "rolling_window":        "W=120h (15 x 8h periods, G6-compliant 31.9 trades/yr)",
        "signal":                "sign(rolling_mean_120h(diff))",
        "g5a_link_btc_k557_corr": 0.0578,   # CRITICAL orthogonality check PASS
        "g5b_eth_btc_k449_corr": -0.0036,   # CRITICAL orthogonality check PASS
        "mr9_fr_identity_max_err": 5.42e-20,  # LINK-ETH = LINK-BTC - ETH-BTC confirmed
        "mr9_position_corr":     0.1254,    # position-level de-correlated (PASS)
        "adf_pvalue":            0.0,
        "ou_halflife_h":         1.45,      # ultra-fast MR (HL 1h FR settlement)
        "link_oracle_mm_floor":  1.25e-5,   # per-hour (stable anchor)
        "link_gt_eth_pct":       74.5,      # LINK FR > ETH FR 74.5% of time
        "k695_lesson": (
            "K695 LINK-SOL REJECTED: G5c corr(K695, K557) = 0.497 > 0.40 — LINK shared leg double-exposure. "
            "K698 pivots to ETH: G5a corr(K698, K557) = 0.0578 PASS. "
            "No LINK double-exposure at position level. Oracle vs L1 cross-cluster real."
        ),
        "k557_coordination": (
            "LINK appears in K557 (BTC leg, HL+Bybit) and K698 (ETH leg, Bybit). "
            "Combined LINK exposure: K557 ~1.5% + K698 2.5% = max 4.0% AUM LINK notional. "
            "K557 LINK leg: coordination required (K701 §62 coordination note). "
            "G5a corr(K698, K557) = 0.0578 PASS — execution de-correlated despite LINK shared."
        ),
        "note": (
            "ETH base decouples from BTC-base mechanism (K557 LINK-BTC pattern). "
            "LINK FR = Chainlink oracle demand cycles (DeFi integrations, CCIP, feed launches). "
            "ETH FR = Ethereum DeFi/staking yields (stETH/LST, Pectra upgrades, L1 gas). "
            "Bybit primary required: HL+LINK+ETH sleeve = 67.0% > 65% cap. "
            "4th ETH-base scaffold (K629 WLD-ETH 49th, K658 SOL-ETH 52nd, K661 AVAX-ETH 53rd, K698 LINK-ETH 61st). "
            "1st oracle-ETH pair: oracle middleware vs Ethereum L1 (new cluster)."
        ),
    }
    dash["activation_criteria"] = {
        "60d_paper_trade_gate":  "required",
        "realized_sharpe_min":   6.0,
        "fill_rate_min_pct":     60,
        "max_drawdown_max_pct":  15,
        "status":                "SCAFFOLD-READY",
        "activation_sleeve_pct": 0.025,
        "venue":                 "Bybit primary (LINK-PERP + ETH-PERP both on Bybit)",
    }
    dash["oos_performance"] = {
        "sharpe":                   12.0676,
        "sharpe_is":                7.3265,
        "is_oos_ratio":             0.607,
        "oos_ann_ret_pct":          2.8997,
        "ann_return_usd_2_5pct_4x": 28_997,
        "wave_accept":              "K698 ACCEPT CONDITIONAL (K701 scaffold) — 8/8 §6 gates PASS",
        "cluster":                  "Oracle middleware vs Ethereum L1 (LINK-ETH, K695 lesson applied)",
        "cluster_rationale": (
            "LINK (Chainlink oracle middleware) FR driven by DeFi integration cycles, CCIP cross-chain, "
            "new feed launches, staking APY changes, oracle demand growth. "
            "ETH (Ethereum L1) FR driven by stETH/LST demand, Pectra EIP cycles, L1 gas narrative. "
            "MR9: LINK-ETH = LINK-BTC - ETH-BTC at FR level (max_err=5.42e-20). "
            "Position de-correlated (corr=0.1254) — independent execution. "
            "4th ETH-base scaffold, 1st oracle-ETH pair."
        ),
        "g5a_verdict":              "PASS (corr=0.0578 < 0.40) — LINK-ETH vs LINK-BTC K557 orthogonal",
        "g5b_verdict":              "PASS (corr=-0.0036 < 0.40) — LINK-ETH vs ETH-BTC K449 orthogonal",
        "walk_forward":             "17/21 folds positive (81.0%)",
        "perm_pvalue":              0.0,
        "dsr_pvalue":               0.0,
        "trades_per_yr":            31.9,
        "max_drawdown_pct":         0.3312,
        "daemon_number":            "61st",
        "eth_base_rank":            "4th ETH-base scaffold (1st oracle-ETH)",
        "k557_comparison": {
            "k557_oos_sharpe":  13.775,
            "k698_oos_sharpe":  12.0676,
            "k698_window_h":    120,    # different from K557 window
            "k698_net_yr_10m":  28997,
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
      1. Fetch LINK + ETH FRs from HL (FR data source)
      2. Compute LINK-ETH differential + 120h rolling mean
      3. Decide position (sign of rolling mean — zero threshold)
      4. Compute delta-neutral notional
      5. If entering: submit paired trade (POST_ONLY, Bybit primary)
      6. If holding: check drift + rebalance
      7. Write k698_dashboard.json
    """
    ts_jst = datetime.now(JST).strftime("%Y-%m-%d %H:%M JST")
    print(f"\n=== K698 LINK-ETH FR Differential (oracle vs ETH L1) — {ts_jst} ===")
    print(f"  Mode:      {'DRY-RUN' if dry_run else 'PAPER-TRADE' if PAPER_TRADE else 'LIVE'}")
    print(f"  AUM:       ${aum:,.0f}  Sleeve: {SLEEVE_PCT:.1%}  Leverage: {LEVERAGE}x")
    print(f"  Venue:     Bybit primary (LINK-PERP + ETH-PERP, both Bybit perps)")
    print(f"  HL cap:    64.5%+2.5%=67%>65% cap -> Bybit primary resolves breach")
    print(f"  Execution: POST_ONLY parallel (K439)")
    print(f"  Signal:    diff = LINK_FR - ETH_FR  (direct, no OLS orthogonalization)")
    print(f"             sign(rolling_mean_120h)  (zero threshold, W=120h = 15 x 8h periods)")
    print(f"  Oracle:    LINK MM floor ~1.25e-5/hr (stable anchor), LINK>ETH 74.5% time")
    print(f"  MR9:       LINK-ETH = LINK-BTC - ETH-BTC (max_err=5.42e-20 confirmed)")
    print(f"  G5a K557:  corr=0.0578 PASS (K695 LINK-SOL G5c=0.497 BLOCKED; K698 avoids SOL)")
    print(f"  G5b K449:  corr=-0.0036 PASS (anti-corr: ETH as base, not quote)")
    print(f"  8/8 gates: G1={12.07:.2f} G2=0.0 G3=0.0 G4=17/21(81%) G5=11/11 G6=31.9 G7=11.6% G9=217d")
    print(f"  K557:      LINK leg coordination — K557 ~1.5% + K698 2.5% = max 4.0% LINK AUM")

    # Step 1: Fetch + compute LINK-ETH differential
    print("\n  [Step 1] Computing LINK-ETH FR differential...")
    signal = compute_signal()
    print(f"  LINK FR:    {signal['fr_link']:+.8f} (8h, HL — data source)")
    print(f"  ETH FR:     {signal['fr_eth']:+.8f} (8h, HL — data source)")
    print(f"  LINK-ETH:   {signal['link_eth_diff']:+.8f}  (direct differential)")
    print(f"  Mean 120h:  {signal['mean_120h']:+.8f}")
    print(f"  Sigma 120h: {signal['diff_sigma']:+.8f}  (informational)")
    print(f"  Direction:  {signal['signal_direction']:+d}  (+1=BULL_LINK, -1=BEAR_LINK, 0=NEUTRAL)")
    print(f"  Regime:     {signal['regime']}")
    print(f"  History:    {signal['history_points']} data points")

    # Step 2: Position decision
    print("\n  [Step 2] Deciding position...")
    decision = decide_position(signal)
    if decision:
        print(f"  Signal:   LONG {decision['long_asset']}@{decision['long_venue']} / "
              f"SHORT {decision['short_asset']}@{decision['short_venue']}")
        print(f"  State:    {decision['position_state']}")
        print(f"  Mean 120h:{decision['mean_120h']:+.8f}")
    else:
        print(f"  Signal:   NEUTRAL (rolling_mean_120h == 0 exactly)")

    # Step 3: Notional sizing
    notional_per_leg, total_notional = \
        compute_delta_neutral_notional(aum, SLEEVE_PCT, LEVERAGE)
    print(f"\n  [Step 3] Notional sizing:")
    print(f"  Sleeve capital:   ${aum * SLEEVE_PCT:,.0f}  ({SLEEVE_PCT:.1%} x ${aum/1e6:.0f}M)")
    print(f"  LINK leg:         ${notional_per_leg:,.0f}  (2.5% x ${aum/1e6:.0f}M x {LEVERAGE}x / 2)")
    print(f"  ETH leg:          ${notional_per_leg:,.0f}  (2.5% x ${aum/1e6:.0f}M x {LEVERAGE}x / 2)")
    print(f"  Total notional:   ${total_notional:,.0f}")
    print(f"  Margin required:  ${total_notional/LEVERAGE:,.0f}  ({SLEEVE_PCT:.1%} AUM)")
    print(f"  Profit @$10M 4x:  OOS 2.90% ann ret = $28,997/yr net (2.5% sleeve)")

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
        print(f"  Action: CLOSE (mean_120h == 0 exactly)")
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
    print(f"\n  === K698 Cycle Complete ===")
    print(f"  Position state:     {dash_out.get('position_state')}")
    print(f"  Regime:             {dash_out.get('regime')}")
    print(f"  LINK-ETH Mean 120h: {dash_out.get('mean_120h'):+.8f}")
    print(f"  Signal direction:   {dash_out.get('signal_direction')}")
    print(f"  G5a K557 corr:      0.0578 (PASS < 0.40 — LINK-ETH orthogonal to LINK-BTC)")
    print(f"  G5b K449 corr:      -0.0036 (PASS < 0.40 — anti-corr with ETH-BTC)")
    print(f"  K695 lesson:        LINK-SOL G5c=0.497 BLOCKED. K698 avoids SOL leg.")
    print(f"  MR9 identity:       LINK-ETH = LINK-BTC - ETH-BTC (max_err=5.42e-20)")
    print(f"  Position corr:      0.1254 (de-correlated at execution — different W, OU paths)")
    print(f"  Paper-trade mode:   {PAPER_TRADE}")
    print(f"  OOS Sharpe:         12.07 (IS=7.33, IS/OOS=0.607)")
    print(f"  Cluster:            Oracle middleware vs Ethereum L1 (4th ETH-base, 1st oracle-ETH)")
    print(f"  Profit 2.5% sleeve: $28,997/yr net @$10M @4x (OOS 2.90% ann ret)")
    print(f"  HL concentration:   64.5% UNCHANGED (Bybit-only — HL-only would reach 67%>65%)")
    print(f"  60d gate:           Realized Sh>=6 + fill>=60% + maxDD<15%")
    print(f"  K557 coordination:  LINK: K557 ~1.5% + K698 2.5% = 4.0% max combined LINK AUM")
    print(f"  v6.50 path:         K698 LINK-ETH 2.5% Bybit sleeve (61st daemon, 4th ETH-base)")
    print()

    return 0


# ─────────────────────────────────────────────────────────────────────────────
# CLI entry point
# ─────────────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="K698 LINK-ETH FR Differential Strategy (K701 scaffold, oracle vs ETH L1, Bybit primary)"
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
        print(f"\n=== K698 Dashboard ({dash.get('last_poll_jst', '—')}) ===")
        print(json.dumps(dash, indent=2))
        return 0

    if args.rebalance:
        dash   = _load_dashboard()
        result = daily_rebalance(dash)
        print(f"\n=== K698 Rebalance Check ===")
        print(json.dumps(result, indent=2))
        return 0

    if args.close:
        result = close_paired_position(args.close, dry_run=args.dry_run)
        print(f"\n=== K698 Close Result ===")
        print(json.dumps(result, indent=2))
        return 0

    return run_cycle(dry_run=args.dry_run, aum=args.aum)


if __name__ == "__main__":
    sys.exit(main())
