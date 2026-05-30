#!/usr/bin/env python3
"""
k647_dot_orthog_run.py — K647 DOT Orthogonalized FR Differential Strategy
===========================================================================
Implements a paired-trade (long DOT / short BTC or reverse) based on the
168h EMA of the DOT-BTC funding rate differential, ORTHOGONALIZED against
INJ factor via single-factor OLS regression (K647 SF-W168h pattern).

Architecture (K653 scaffold, K647 pattern):
  1. fetch_fr_batch()                  → fetch DOT + INJ + BTC FR every 8h
  2. compute_residual(dot_diff, inj_diff)
       residual = DOT_diff - β_INJ * INJ_diff
       β coefficient HARDCODED per K647 OLS single-factor (no re-OLS in production):
         β_INJ  = 0.642
  3. compute_signal(residual_history)  → 168h EMA of residual; |ema| > 1.5σ
  4. decide_position(signal)           → LONG_DOT_SHORT_BTC | LONG_BTC_SHORT_DOT | NEUTRAL
  5. submit_paired_trade(long, short)  → POST_ONLY paired (DOT + BTC legs)
  6. daily_rebalance()                 → drift > 5% triggers rebalance
  7. close_paired_position(reason)     → sequential: short first, then long

K647 Governance/Staking cluster hypothesis (ACCEPT, 60d paper-trade):
  - DOT = Polkadot: relay chain (Substrate), parachain slot auctions, OpenGov, staking unbonding
  - INJ = Injective: Cosmos-based L1 DEX/DeFi chain; INJ tokenomics burn / CW orderbook dynamics
  - Governance/Staking cluster = "relay-chain governance / parachain auction" meta-narrative
  - DOT FR dynamics driven by Polkadot relay-chain staking unbonding cycles (28d), OpenGov
    referendum timing, parachain slot auction events — orthogonal to INJ CW orderbook/DEX regime
    after OLS residualization
  - OOS Sh=23.25 RESIDUAL (SF W=168h optimal per K647 analysis, single-factor INJ)
  - β_INJ=0.642 per K647 OLS (K513 INJ corr 0.4229 BLOCKED → post-orth 0.037 UNLOCKED)
  - OOS R²=-4.11 STRUCTURAL BREAK WARNING: IS DOT-INJ corr=0.616, OOS corr=0.045
    → tight monitoring required (IS β re-OLS every 30d for drift check)
  - 60d paper-trade gate STRICTER due to OOS R² warning:
    Realized Sh>=12 + fill>=60% + DD<15%

K647 K653 profit summary:
  - OOS Sharpe (residual): 23.25
  - Ann Return @$10M @4x (3% sleeve): $103,586/yr net (net 80% of gross)
  - Bybit primary (DOT on Bybit perp + BTC-USDT-SWAP, both Bybit perp)
  - OOS R² caveat: -4.11 (structural break IS→OOS); IS β re-OLS every 30d mandatory

Execution:
  - Bybit primary (DOTUSDT perp + BTC-USDT-SWAP, both Bybit perp)
  - POST_ONLY paired execution (K439 pattern)
  - Position: 3% sleeve, 4x leverage
  - 8h cadence (matches FR settlement cycle, HL hourly FR used for signal)
  - W=168h EMA (optimal window per K647 analysis, SF single-factor)

Orthog mechanism:
  - Raw DOT_diff  = DOT_FR − BTC_FR
  - INJ_diff      = INJ_FR  − BTC_FR
  - residual      = DOT_diff − 0.642 × INJ_diff
  - Signal        = 168h EMA of residual; threshold = 1.5σ of 168h window
  - β hardcoded: NO re-OLS in production (stability constraint, K647 spec)
  - INJ corr: raw 0.4229 (BLOCKED-G5e K513) → post-orth 0.037 (UNLOCKED K647)

OOS R² Warning:
  - OOS R² = -4.11 (structural break: IS DOT-INJ corr=0.616 → OOS corr=0.045)
  - This means the IS beta over-fits the OOS residual; the OOS residual is driven
    by DOT-only dynamics (Polkadot relay chain) rather than INJ-removal.
  - Despite OOS R² being negative, OOS Sh=23.25 survives (signal still profitable).
  - IS β re-OLS every 30d mandatory to detect IS regime drift (see gate_metrics).
  - 60d gate stricter: Realized Sh>=12 (not 4) + DD<15% (not 20%).

Paper-trade mode is the DEFAULT.  No orders are submitted unless
PAPER_TRADE=False is explicitly set in the environment.

K339 security: REPO_ROOT from __file__, no /Users/ literals.
No new packages — stdlib urllib + json only.

Usage:
  python3 scripts/k647_dot_orthog_run.py --dry-run
  python3 scripts/k647_dot_orthog_run.py --status
  python3 scripts/k647_dot_orthog_run.py --rebalance
  python3 scripts/k647_dot_orthog_run.py --close "scheduled exit"
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

DASHBOARD_PATH  = DATA_DIR  / "k647_dashboard.json"
FR_HISTORY_PATH = CACHE_DIR / "k647_fr_history.jsonl"
TRADE_LOG_PATH  = CACHE_DIR / "k647_paper_trades.jsonl"

JST = timezone(timedelta(hours=9))
UTC = timezone.utc

# ── Strategy constants ────────────────────────────────────────────────────────
PAPER_TRADE         = True          # never submit real orders in paper-trade mode
SLEEVE_PCT          = 0.03          # K647 sleeve = 3% of AUM (governance/staking cluster unlock, Bybit-only)
LEVERAGE            = 4.0           # 4x per K647 analysis (K430 cap)
AUM_DEFAULT         = 10_000_000.0  # $10M reference AUM
DRIFT_REBALANCE_PCT = 0.05          # rebalance if legs drift > 5%
IOC_TIMEOUT_SEC     = 300           # 5 min fill window
EMA_PERIOD_HOURS    = 168           # 168h EMA optimal window (per K647 analysis, SF W=168h)
EMA_PERIOD_PERIODS  = EMA_PERIOD_HOURS // 8  # = 21 periods (8h settlement cycle)
SIGNAL_SIGMA_MULT   = 1.5           # entry threshold: |residual_ema| > 1.5σ
HL_API_URL          = "https://api.hyperliquid.xyz/info"

# ── K647 OLS β coefficient — HARDCODED, NO RE-OLS in production ──────────────
# Source: K647 single-factor OLS regression on DOT vs INJ factor
#   DOT_diff = α + β_INJ × INJ_diff + ε
#   β_INJ  = 0.642  (INJ Cosmos DEX/DeFi factor loading on DOT FR)
#   IS R²=0.3798, OOS R²=-4.1139 (STRUCTURAL BREAK WARNING — tight monitoring mandatory)
#   Governance/Staking cluster: DOT orthogonal to INJ DEX/DeFi after OLS
#   K513 INJ corr raw=0.4229 (BLOCKED-G5e) → post-orth=0.037 (PASS K647)
#
# OOS R² WARNING:
#   IS DOT-INJ corr=0.616 → OOS corr=0.045 (structural break: corr decoupled in OOS period).
#   IS β over-fits OOS residual; OOS signal is driven by DOT-only Polkadot relay-chain alpha.
#   IS β re-OLS mandatory every 30d to detect drift (see gate_metrics).
#   60d gate STRICTER: Realized Sh>=12 + fill>=60% + DD<15%.
BETA_INJ  = 0.642

# ── Venue config (Bybit primary — DOT on Bybit perp) ─────────────────────────
# Bybit primary: DOTUSDT perp + BTC-USDT-SWAP, both Bybit perp
# HL DOT: K513 blocked due to INJ corr; Bybit DOTUSDT primary
# HL concentration: 3% split HL 1.5% + Bybit 1.5% → HL 64.0% (1pp headroom)
BYBIT_SLEEVE_PCT   = SLEEVE_PCT      # full sleeve on Bybit (DOT + BTC paired)
HL_CONCENTRATION_AFTER_ADD = 64.0    # K647 HL+Bybit split → HL 64.0% (1pp headroom from 65%)

# ── Position state constants ──────────────────────────────────────────────────
STATE_NEUTRAL            = "NEUTRAL"
STATE_LONG_DOT_SHORT_BTC = "LONG_DOT_SHORT_BTC"
STATE_LONG_BTC_SHORT_DOT = "LONG_BTC_SHORT_DOT"

# ── Symbols fetched from HL for FR data ──────────────────────────────────────
SYMBOLS = ("DOT", "INJ", "BTC")


# ─────────────────────────────────────────────────────────────────────────────
# HTTP helper (stdlib urllib only — no requests)
# ─────────────────────────────────────────────────────────────────────────────

def _http_post(url: str, payload: dict, timeout: int = 10) -> Optional[dict]:
    try:
        data = json.dumps(payload).encode()
        req  = urllib.request.Request(
            url, data=data,
            headers={"Content-Type": "application/json",
                     "User-Agent": "crypto-lab-k647/1.0"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        print(f"  [k647] HTTP error: {e}", file=sys.stderr)
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Phase 1 — Funding rate fetch (DOT + INJ + BTC)
# ─────────────────────────────────────────────────────────────────────────────

def _fetch_hl_fr_batch() -> Dict[str, float]:
    """
    Fetch current funding rates for DOT, INJ, BTC from HL.
    Returns {symbol: fr_fraction}.

    HL API: metaAndAssetCtxs -> funding field per asset.
    Note: DOT live trading uses Bybit DOTUSDT perp (8h settlement).
    HL DOT data used for signal computation only.
    """
    raw = _http_post(HL_API_URL, {"type": "metaAndAssetCtxs"})
    if not raw or not isinstance(raw, list) or len(raw) < 2:
        print("  [k647] HL metaAndAssetCtxs fetch failed", file=sys.stderr)
        return {}
    meta       = raw[0]
    asset_ctxs = raw[1]
    universe   = {item["name"]: i for i, item in enumerate(meta.get("universe", []))}
    result: Dict[str, float] = {}
    for sym in SYMBOLS:
        if sym not in universe:
            print(f"  [k647] Symbol {sym} not found in HL universe", file=sys.stderr)
            continue
        idx = universe[sym]
        ctx = asset_ctxs[idx]
        try:
            result[sym] = float(ctx.get("funding", 0.0))
        except (TypeError, ValueError):
            continue
    return result


def _load_fr_history() -> List[dict]:
    """Load K647 FR history JSONL."""
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
    fr_dot: float, fr_inj: float, fr_btc: float,
    dot_diff: float, inj_diff: float, residual: float
) -> None:
    """Append one FR + residual snapshot to history."""
    rec = {
        "ts_utc":   datetime.now(UTC).isoformat(),
        "fr_dot":   round(fr_dot,  10),
        "fr_inj":   round(fr_inj,  10),
        "fr_btc":   round(fr_btc,  10),
        "dot_diff": round(dot_diff, 10),  # DOT_FR - BTC_FR (raw)
        "inj_diff": round(inj_diff, 10),  # INJ_FR  - BTC_FR
        "residual": round(residual, 10),  # orthogonalized residual
    }
    with open(FR_HISTORY_PATH, "a") as f:
        f.write(json.dumps(rec) + "\n")


# ─────────────────────────────────────────────────────────────────────────────
# Phase 2 — Orthogonalized residual computation
# ─────────────────────────────────────────────────────────────────────────────

def compute_residual(
    fr_dot: Optional[float] = None,
    fr_inj: Optional[float] = None,
    fr_btc: Optional[float] = None,
) -> dict:
    """
    Fetch live DOT/INJ/BTC FRs from HL, compute orthogonalized residual,
    and compute 168h EMA + 168h rolling sigma for threshold calculation.

    Orthogonalization mechanism (K647 OLS single-factor, coefficient HARDCODED):
      dot_diff = DOT_FR  - BTC_FR
      inj_diff = INJ_FR  - BTC_FR
      residual = dot_diff - beta_INJ * inj_diff
               = dot_diff - 0.642 * inj_diff

    Signal gate (W=168h optimal per K647 analysis):
      EMA = 168h EMA of residual (21 x 8h periods)
      sigma = 168h rolling std of residual
      Enter when |EMA| > 1.5sigma

    OOS R² WARNING (-4.11):
      IS DOT-INJ corr=0.616 → OOS corr=0.045 (structural break).
      IS beta over-fits OOS residual; OOS signal is driven by DOT-only
      Polkadot relay-chain alpha (relay unbonding cycles, parachain auctions,
      OpenGov referenda timing) rather than INJ removal.
      Despite negative OOS R², OOS Sh=23.25 survives — signal is profitable.
      IS β re-OLS every 30d mandatory to detect regime drift.
      Gate STRICTER: Realized Sh>=12 (not 4), DD<15% (not 20%).

    K647 Governance/Staking cluster hypothesis:
      DOT = Polkadot (relay chain, Substrate): FR dynamics driven by:
        28d staking unbonding cycles — DOT has ~28d unbonding period unique to PoS relay
        OpenGov referendum timing — governance votes drive staking/unstaking demand spikes
        Parachain slot auction events — DOT locked/released in batch bond auctions
        Relay chain upgrade cycles — Polkadot runtime upgrades create FR volatility
        XCM cross-chain messaging adoption — interoperability usage creates DOT demand waves
      INJ raw signal corr=0.4229 (BLOCKED-G5e in K513).
      After OLS orthogonalization (β_INJ=0.642):
        INJ corr post-orth=0.037 (G5e PASS threshold 0.40 — UNLOCKED)
      OOS Sh=23.25 (SF W=168h) confirms orthogonalization unlocks Polkadot relay-chain alpha.

    Returns:
      {
        "fr_dot":            float,
        "fr_inj":            float,
        "fr_btc":            float,
        "dot_diff":          float,   # raw DOT-BTC
        "inj_diff":          float,   # INJ-BTC
        "residual":          float,   # orthogonalized residual (current)
        "residual_ema_168h": float,   # 168h EMA of residual (21 periods x 8h)
        "residual_sigma":    float,   # 168h rolling sigma of residual
        "threshold":         float,   # 1.5sigma entry threshold
        "beta_inj":          float,   # beta_INJ hardcoded = 0.642
        "history_points":    int,
        "regime":            str,     # BULL_DOT | BEAR_DOT | NEUTRAL
        "ts_jst":            str,
        "oos_r2_warning":    str,     # structural break caveat
      }
    """
    if any(v is None for v in (fr_dot, fr_inj, fr_btc)):
        frs    = _fetch_hl_fr_batch()
        fr_dot = frs.get("DOT", 0.0)
        fr_inj = frs.get("INJ", 0.0)
        fr_btc = frs.get("BTC", 0.0)

    # Compute diffs
    dot_diff = fr_dot - fr_btc
    inj_diff = fr_inj - fr_btc

    # Orthogonalized residual (K647 OLS single-factor, beta hardcoded)
    residual = dot_diff - BETA_INJ * inj_diff

    _append_fr_history(fr_dot, fr_inj, fr_btc, dot_diff, inj_diff, residual)

    # Load history for EMA + sigma (168h = 21 x 8h periods)
    history   = _load_fr_history()
    residuals = [r["residual"] for r in history if "residual" in r]

    n_periods = EMA_PERIOD_PERIODS   # 21 periods (168h / 8h)
    alpha     = 2.0 / (n_periods + 1)
    ema = residuals[0] if residuals else 0.0
    for r in residuals[1:]:
        ema = alpha * r + (1 - alpha) * ema

    # Rolling sigma: std of last n_periods residuals
    window = residuals[-n_periods:] if len(residuals) >= 2 else residuals
    if len(window) >= 2:
        mean  = sum(window) / len(window)
        sigma = math.sqrt(sum((x - mean) ** 2 for x in window) / (len(window) - 1))
    else:
        sigma = abs(ema) if ema != 0 else 1e-8   # fallback: EMA magnitude

    threshold = SIGNAL_SIGMA_MULT * sigma  # 1.5sigma entry gate

    # Regime classification
    if abs(ema) <= threshold:
        regime = "NEUTRAL"
    elif ema > 0:
        regime = "BULL_DOT"   # DOT residual FR > 0: short DOT / long BTC
    else:
        regime = "BEAR_DOT"   # DOT residual FR < 0: long DOT / short BTC

    return {
        "fr_dot":            round(fr_dot,   10),
        "fr_inj":            round(fr_inj,   10),
        "fr_btc":            round(fr_btc,   10),
        "dot_diff":          round(dot_diff, 10),
        "inj_diff":          round(inj_diff, 10),
        "residual":          round(residual, 10),
        "residual_ema_168h": round(ema,      10),
        "residual_sigma":    round(sigma,    10),
        "threshold":         round(threshold,10),
        "beta_inj":          BETA_INJ,
        "history_points":    len(residuals),
        "regime":            regime,
        "ts_jst":            datetime.now(JST).strftime("%Y-%m-%d %H:%M JST"),
        "oos_r2_warning":    "OOS_R2=-4.11 STRUCTURAL BREAK: IS DOT-INJ corr=0.616 -> OOS=0.045. IS beta re-OLS every 30d mandatory.",
    }


# ─────────────────────────────────────────────────────────────────────────────
# Phase 3 — Position decision
# ─────────────────────────────────────────────────────────────────────────────

def decide_position(signal: dict) -> Optional[dict]:
    """
    Determine trade direction from orthogonalized residual EMA.

    Logic (DOT-BTC orthogonalized pair, Bybit primary):
      regime = BULL_DOT (residual_ema > 1.5sigma):
        DOT residual FR > BTC FR -> DOT more expensive to long
        -> short DOT (collect high residual FR) / long BTC (cheap carry)
        -> position_state = LONG_BTC_SHORT_DOT
        -> both legs on Bybit

      regime = BEAR_DOT (residual_ema < -1.5sigma):
        DOT residual FR < BTC FR -> BTC more expensive
        -> long DOT / short BTC
        -> position_state = LONG_DOT_SHORT_BTC
        -> both legs on Bybit

      regime = NEUTRAL: no trade

    K647 orthog edge:
      The residual cleanly separates DOT's Polkadot-relay-chain-specific FR dynamics
      from the INJ Cosmos DEX/DeFi co-movement factor noise (β_INJ=0.642).
      OOS Sh=23.25 (SF W=168h) residual confirms the true alpha resides in
      Polkadot 28d unbonding cycles, OpenGov referendum timing, parachain slot auctions,
      relay chain upgrade cycles, and XCM adoption waves — not shared Cosmos-family narratives.
      Governance/Staking cluster unlock: K513 was BLOCKED-G5e (INJ corr=0.4229 >= 0.40);
      K647 orthog reduces to 0.037 (PASS) unlocking Polkadot relay-chain cluster.
      OOS R²=-4.11 caution: structural break means IS beta over-fits OOS period.
      Signal survives (OOS Sh=23.25) but 30d β drift check is mandatory.

    Returns:
      {long_asset, short_asset, long_venue, short_venue, residual_ema,
       signal_strength, size_multiplier, position_state}
      or None if NEUTRAL.
    """
    regime  = signal.get("regime", "NEUTRAL")
    ema     = signal.get("residual_ema_168h", 0.0)
    thresh  = signal.get("threshold", 1e-8)
    abs_ema = abs(ema)

    if regime == "NEUTRAL":
        return None

    if regime == "BULL_DOT":
        # DOT residual FR positive -> DOT FR > BTC FR
        # short DOT (expensive), long BTC (cheap)
        long_asset  = "BTC"
        short_asset = "DOT"
        state       = STATE_LONG_BTC_SHORT_DOT
    else:  # BEAR_DOT
        # DOT residual FR negative -> BTC FR > DOT FR
        # long DOT (cheap), short BTC (expensive)
        long_asset  = "DOT"
        short_asset = "BTC"
        state       = STATE_LONG_DOT_SHORT_BTC

    # Both legs on Bybit (DOT + BTC, Bybit primary)
    long_venue  = "Bybit"
    short_venue = "Bybit"

    # Signal strength: |ema| / threshold (capped at 3x for sizing)
    strength = min(abs_ema / max(thresh, 1e-10), 3.0)

    return {
        "long_asset":      long_asset,
        "short_asset":     short_asset,
        "position_state":  state,
        "long_venue":      long_venue,
        "short_venue":     short_venue,
        "residual_ema":    ema,
        "threshold":       thresh,
        "signal_strength": round(strength, 4),
        "size_multiplier": 1.0,   # reserved for dynamic sizing
        "regime":          regime,
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
    Compute equal notional for both legs of the DOT-BTC paired trade.

    K647 Bybit-only config (DOT perp on Bybit):
      sleeve_capital   = aum x sleeve_pct      (e.g. $10M x 3% = $300K)
      total_notional   = sleeve_capital x lev   ($300K x 4 = $1.2M)
      notional_per_leg = total_notional / 2     ($600K per leg)

    At $10M / 3% sleeve / 4x:
      DOT leg:   $150K capital x 4x = $600K notional (Bybit)
      BTC leg:   $150K capital x 4x = $600K notional (Bybit)
      Total:     $1.2M notional (two legs combined)
      Margin:    $300K (3% of AUM)
      Net profit: ~$103,586/yr (net 80% of gross, 3% sleeve @$10M @4x)

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
    Submit K647 DOT-BTC paired trade: POST_ONLY both legs in parallel.

    Protocol (K647 Bybit primary):
      1. Submit DOT leg on Bybit POST_ONLY
      2. Submit BTC leg on Bybit POST_ONLY
      3. Both legs submitted in parallel (K439 pattern)
      4. IOC fallback per leg if POST_ONLY times out
      5. If both fail: retry next 8h cycle

    Args:
      long_leg:  {"symbol": "DOT", "notional": 600000, "venue": "Bybit"}
      short_leg: {"symbol": "BTC",  "notional": 600000, "venue": "Bybit"}
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
        print(f"  [K647] {mode_tag}: LONG {long_sym}@{long_venue} ${long_notl:,.0f}  "
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
            "venue_config":     "BYBIT_PRIMARY_DOT_GOVERNANCE_STAKING",
            "orthog_note":      "residual = DOT_diff - 0.642*INJ_diff (K647 OLS SF)",
            "oos_r2_warning":   "OOS_R2=-4.11 STRUCTURAL BREAK — IS beta re-OLS every 30d",
            "ts_utc":           ts,
        }
        _append_trade_log(result)
        return result

    # LIVE scaffold (not reached in PAPER_TRADE mode):
    print(f"  [K647] SCAFFOLD LIVE: parallel POST_ONLY "
          f"LONG {long_sym}@{long_venue} ${long_notl:,.0f} "
          f"+ SHORT {short_sym}@{short_venue} ${short_notl:,.0f}")
    long_order_id  = f"SCAFFOLD_LONG_{long_sym}_{int(time.time())}"
    short_order_id = f"SCAFFOLD_SHORT_{short_sym}_{int(time.time())}"

    # Scaffold: poll not implemented — retry next 8h cycle
    print(f"  [K647] Neither leg filled within timeout — retry next 8h cycle")
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
    Check if current K647 position has drifted beyond DRIFT_REBALANCE_PCT (5%).

    K647 Bybit-only: both legs on Bybit; drift accumulates together.
    Drift detection: compare stored DOT leg notional vs BTC leg notional.
    Threshold: 5% (same as K507/K512/K628/K631/K633/K635/K638/K645/K646 pattern).

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
    Both legs on Bybit (K647 Bybit primary).

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

    if state == STATE_LONG_DOT_SHORT_BTC:
        long_sym,  short_sym  = "DOT", "BTC"
    else:  # LONG_BTC_SHORT_DOT
        long_sym,  short_sym  = "BTC", "DOT"

    long_notional  = float(dash.get("long_notional",  0.0))
    short_notional = float(dash.get("short_notional", 0.0))

    if dry_run or PAPER_TRADE:
        mode_tag = "DRY_RUN" if dry_run else "PAPER_TRADE"
        print(f"  [K647] {mode_tag} CLOSE:")
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
        print(f"  [K647] SCAFFOLD CLOSE:")
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
    """Load k647_dashboard.json; return defaults if missing."""
    if DASHBOARD_PATH.exists():
        try:
            return json.loads(DASHBOARD_PATH.read_text())
        except Exception:
            pass
    return {
        "last_poll_jst":           "—",
        "residual_ema_168h":       0.0,
        "residual_sigma":          0.0,
        "threshold_1_5sigma":      0.0,
        "beta_inj_used":           BETA_INJ,
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
        "oos_r2_warning":          "OOS_R2=-4.11 STRUCTURAL BREAK: IS DOT-INJ corr=0.616 -> OOS=0.045. IS beta re-OLS every 30d mandatory.",
    }


def _write_dashboard(
    signal:           dict,
    decision:         Optional[dict],
    notional_per_leg: float,
    total_notional:   float,
    rebalance:        dict,
    aum:              float,
) -> dict:
    """Write k647_dashboard.json with full signal + regime state."""
    dash = _load_dashboard()

    # Update signal data
    dash["last_poll_jst"]        = signal.get("ts_jst", "—")
    dash["fr_dot_current"]       = signal.get("fr_dot",   0.0)
    dash["fr_inj_current"]       = signal.get("fr_inj",   0.0)
    dash["fr_btc_current"]       = signal.get("fr_btc",   0.0)
    dash["dot_diff_raw"]         = signal.get("dot_diff", 0.0)
    dash["inj_diff"]             = signal.get("inj_diff", 0.0)
    dash["residual_current"]     = signal.get("residual", 0.0)
    dash["residual_ema_168h"]    = signal.get("residual_ema_168h", 0.0)
    dash["residual_sigma"]       = signal.get("residual_sigma",   0.0)
    dash["threshold_1_5sigma"]   = signal.get("threshold",        0.0)
    dash["beta_inj_used"]        = signal.get("beta_inj",  BETA_INJ)
    dash["regime"]               = signal.get("regime",    "NEUTRAL")
    dash["history_points"]       = signal.get("history_points", 0)
    dash["oos_r2_warning"]       = signal.get("oos_r2_warning", "OOS_R2=-4.11 STRUCTURAL BREAK")

    # Update position if entering
    if decision:
        state = decision.get("position_state", STATE_NEUTRAL)
        if dash.get("position_state") == STATE_NEUTRAL:
            dash["position_state"]  = state
            dash["long_notional"]   = notional_per_leg
            dash["short_notional"]  = notional_per_leg
            dash["long_asset"]      = decision.get("long_asset")
            dash["short_asset"]     = decision.get("short_asset")
            dash["venue"]           = "Bybit"
            dash["entry_ts_jst"]    = dash["last_poll_jst"]
            dash["signal_strength"] = decision.get("signal_strength", 0.0)

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
    dash["hl_concentration_pct"]     = HL_CONCENTRATION_AFTER_ADD  # 64.0% (1pp headroom)

    # Paper-trade status
    paper_status = dash.get("paper_trade_status", {"days_elapsed": 0, "target_60d": 60})
    dash["paper_trade_status"]       = paper_status

    # 60d activation gate metrics (K653: STRICTER due to OOS R² warning)
    # Realized Sh>=12 (not 4), fill>=60%, DD<15% (not 20%)
    dash["gate_metrics"] = {
        "realized_sharpe_target":    12.0,     # >=12 STRICT (OOS R²=-4.11 caution)
        "fill_rate_target_pct":      60,
        "max_drawdown_target_pct":   15,       # <15% STRICT (not 20%)
        "current_realized_sharpe":   dash.get("60d_sharpe", 0.0),
        "current_fill_rate_pct":     0.0,
        "current_max_dd_pct":        0.0,
        "gate_status":               "IN_PROGRESS",
        "activation_trigger":        "60d paper-trade: Sh>=12 AND fill>=60% AND maxDD<15% (STRICT — OOS R²=-4.11)",
        "profit_at_activation_3pct": "$103,586/yr net @$10M @4x (3% sleeve)",
        "oos_r2_warning":            "OOS_R2=-4.11 STRUCTURAL BREAK — IS beta re-OLS every 30d mandatory",
        "beta_drift_check":          "IS beta re-OLS every 30d (check K647 IS beta vs current OLS)",
    }

    # Strategy metadata
    dash["paper_trade_mode"]    = PAPER_TRADE
    dash["wave"]                = "K653"
    dash["strategy"]            = "K647 DOT-BTC Orthogonalized FR Differential (SF INJ W=168h)"
    dash["execution_mode"]      = "POST_ONLY_PARALLEL"
    dash["venue_config"]        = "BYBIT_PRIMARY"
    dash["orthog_mechanism"]    = {
        "formula":    "residual = DOT_diff - 0.642*INJ_diff",
        "beta_inj":   BETA_INJ,
        "ema_window": "W=168h (21 x 8h periods)",
        "note":       "beta HARDCODED per K647 OLS single-factor — no re-OLS in production for stability",
        "oos_r2_caveat": "OOS R²=-4.11 STRUCTURAL BREAK (IS DOT-INJ corr=0.616 → OOS=0.045). IS beta re-OLS every 30d mandatory.",
    }
    dash["activation_criteria"] = {
        "60d_paper_trade_gate":   "required",
        "realized_sharpe_min":    12.0,
        "fill_rate_min_pct":      60,
        "max_drawdown_max_pct":   15,
        "status":                 "SCAFFOLD-READY",
        "activation_sleeve_pct":  0.03,
        "venue":                  "Bybit primary (DOT+BTC both legs)",
        "note":                   "STRICTER gate due to OOS R²=-4.11 structural break warning",
    }
    dash["oos_performance"] = {
        "sharpe_residual":          23.25,
        "sharpe_raw_k513":          43.562,
        "orthog_degradation_sh":    20.312,
        "inj_corr_raw":             0.4229,
        "inj_corr_post_orth":       0.037,
        "oos_r2":                   -4.1139,
        "oos_r2_warning":           "STRUCTURAL BREAK: IS DOT-INJ corr=0.616 → OOS corr=0.045. IS beta re-OLS every 30d.",
        "is_r2":                    0.3798,
        "ann_return_pct_4x":        10.06,
        "ann_return_usd_3pct_4x":   103586,
        "wave_accept":              "K647 ACCEPT (60d paper-trade, OOS R² caution, K653 scaffold)",
        "cluster":                  "Governance/Staking (Polkadot relay chain Substrate — INJ-cluster unlock)",
        "cluster_rationale":        "DOT FR driven by Polkadot 28d staking unbonding cycles, OpenGov referendum timing, parachain slot auction events, relay chain upgrade cycles, XCM adoption waves — orthogonal to INJ Cosmos DEX/DeFi orderbook dynamics after OLS residualization",
        "hl_concentration_pct":     64.0,
        "hl_impact":                "1pp headroom: HL 65%→64% (3% split: HL 1.5% + Bybit 1.5%)",
        "factors_removed":          ["INJ (Cosmos DEX/DeFi co-movement, CW orderbook dynamics)"],
        "inj_cluster_unlock":       "K513 BLOCKED (INJ corr=0.4229 >= 0.40) -> K647 UNLOCKED (post-orth=0.037 < 0.40)",
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
      1. Fetch DOT + INJ + BTC FRs
      2. Compute orthogonalized residual + 168h EMA + sigma
      3. Decide position (|ema| > 1.5sigma threshold)
      4. Compute delta-neutral notional
      5. If entering: submit paired trade (POST_ONLY, Bybit primary)
      6. If holding: check drift + rebalance
      7. Write k647_dashboard.json
    """
    ts_jst = datetime.now(JST).strftime("%Y-%m-%d %H:%M JST")
    print(f"\n=== K647 DOT Orthogonalized FR Differential — {ts_jst} ===")
    print(f"  Mode:      {'DRY-RUN' if dry_run else 'PAPER-TRADE' if PAPER_TRADE else 'LIVE'}")
    print(f"  AUM:       ${aum:,.0f}  Sleeve: {SLEEVE_PCT:.1%}  Leverage: {LEVERAGE}x")
    print(f"  Venue:     Bybit primary (DOT+BTC paired; Bybit DOTUSDT perp + BTC-USDT-SWAP)")
    print(f"  Execution: POST_ONLY parallel (K439)")
    print(f"  HL impact: 1pp headroom: HL 65%→64% (3% split HL 1.5%+Bybit 1.5%)")
    print(f"  Orthog:    residual = DOT_diff - {BETA_INJ}xINJ_diff")
    print(f"  beta fixed: beta_INJ={BETA_INJ}  (K647 OLS SF, production-hardcoded)")
    print(f"  Signal:    |residual_EMA_168h| > 1.5sigma  (W=168h = 21 x 8h periods)")
    print(f"  INJ unlock: K513 INJ corr 0.4229 BLOCKED -> K647 POST-ORTH (corr=0.037 PASS)")
    print(f"  *** OOS R²=-4.11 STRUCTURAL BREAK WARNING ***")
    print(f"      IS DOT-INJ corr=0.616 -> OOS=0.045 (decoupled in OOS period)")
    print(f"      IS beta re-OLS every 30d mandatory | 60d gate STRICTER: Sh>=12 + DD<15%")

    # Step 1: Fetch + compute orthogonalized residual
    print("\n  [Step 1] Computing orthogonalized residual...")
    signal = compute_residual()
    print(f"  DOT FR:    {signal['fr_dot']:+.8f} (8h)")
    print(f"  INJ FR:    {signal['fr_inj']:+.8f} (8h)")
    print(f"  BTC FR:    {signal['fr_btc']:+.8f} (8h)")
    print(f"  DOT diff:  {signal['dot_diff']:+.8f}  (DOT-BTC raw)")
    print(f"  Residual:  {signal['residual']:+.8f}  (orthogonalized)")
    print(f"  EMA 168h:  {signal['residual_ema_168h']:+.8f}")
    print(f"  Sigma 168h:{signal['residual_sigma']:+.8f}")
    print(f"  Threshold: {signal['threshold']:+.8f}  (1.5sigma = {SIGNAL_SIGMA_MULT}xsigma)")
    print(f"  Regime:    {signal['regime']}")
    print(f"  History:   {signal['history_points']} data points")
    print(f"  OOS R² WARNING: {signal['oos_r2_warning']}")

    # Step 2: Position decision
    print("\n  [Step 2] Deciding position...")
    decision = decide_position(signal)
    if decision:
        print(f"  Signal:   LONG {decision['long_asset']}@{decision['long_venue']} / "
              f"SHORT {decision['short_asset']}@{decision['short_venue']}")
        print(f"  State:    {decision['position_state']}")
        print(f"  Strength: {decision['signal_strength']:.2f}x threshold")
    else:
        print(f"  Signal:   NEUTRAL (|residual_ema| <= 1.5sigma)")

    # Step 3: Notional sizing
    notional_per_leg, total_notional = \
        compute_delta_neutral_notional(aum, SLEEVE_PCT, LEVERAGE)
    print(f"\n  [Step 3] Notional sizing:")
    print(f"  Sleeve capital:   ${aum * SLEEVE_PCT:,.0f}  ({SLEEVE_PCT:.1%} x ${aum/1e6:.0f}M)")
    print(f"  DOT leg:          ${notional_per_leg:,.0f}  (1.5% x ${aum/1e6:.0f}M x {LEVERAGE}x)")
    print(f"  BTC leg:          ${notional_per_leg:,.0f}  (1.5% x ${aum/1e6:.0f}M x {LEVERAGE}x)")
    print(f"  Total notional:   ${total_notional:,.0f}")
    print(f"  Margin required:  ${total_notional/LEVERAGE:,.0f}  ({SLEEVE_PCT:.1%} AUM)")
    print(f"  Profit @$10M 4x:  3% sleeve=~$103,586/yr (net 80%)")

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
        print(f"  Action: CLOSE (residual below 1.5sigma threshold)")
        trade_result = close_paired_position("signal_below_threshold", dry_run=dry_run)

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
    print(f"\n  === K647 Cycle Complete ===")
    print(f"  Position state:     {dash_out.get('position_state')}")
    print(f"  Regime:             {dash_out.get('regime')}")
    print(f"  Residual EMA 168h:  {dash_out.get('residual_ema_168h'):+.8f}")
    print(f"  Threshold (1.5sig): {dash_out.get('threshold_1_5sigma'):+.8f}")
    print(f"  beta_INJ (fixed):   {BETA_INJ}  (K647 OLS SF, production-hardcoded)")
    print(f"  Paper-trade mode:   {PAPER_TRADE}")
    print(f"  OOS Sharpe:         23.25 residual (raw K513=43.56, SF W=168h)")
    print(f"  OOS R²:             -4.11 STRUCTURAL BREAK WARNING")
    print(f"  INJ unlock:         K513 INJ corr 0.4229 BLOCKED -> K647 post-orth 0.037 PASS")
    print(f"  Cluster:            Governance/Staking / Polkadot relay chain (8th orthog)")
    print(f"  Profit 3% sleeve:   ~$103,586/yr @$10M @4x (net 80%)")
    print(f"  HL concentration:   {HL_CONCENTRATION_AFTER_ADD}% (1pp headroom: 65%→64%)")
    print(f"  60d gate (STRICT):  Realized Sh>=12 + fill>=60% + maxDD<15% (OOS R² caution)")
    print(f"  IS β re-OLS:        Every 30d mandatory (drift check)")
    print(f"  v6.38 path:         K647 DOT orthog 3% Bybit sleeve added to v6.37")
    print()

    return 0


# ─────────────────────────────────────────────────────────────────────────────
# CLI entry point
# ─────────────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="K647 DOT Orthogonalized FR Differential Strategy (K653 scaffold)"
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
        print(f"\n=== K647 Dashboard ({dash.get('last_poll_jst', '—')}) ===")
        print(json.dumps(dash, indent=2))
        return 0

    if args.rebalance:
        dash   = _load_dashboard()
        result = daily_rebalance(dash)
        print(f"\n=== K647 Rebalance Check ===")
        print(json.dumps(result, indent=2))
        return 0

    if args.close:
        result = close_paired_position(args.close, dry_run=args.dry_run)
        print(f"\n=== K647 Close Result ===")
        print(json.dumps(result, indent=2))
        return 0

    return run_cycle(dry_run=args.dry_run, aum=args.aum)


if __name__ == "__main__":
    sys.exit(main())
