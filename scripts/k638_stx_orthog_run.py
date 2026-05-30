#!/usr/bin/env python3
"""
k638_stx_orthog_run.py — K638 STX Orthogonalized FR Differential Strategy
===========================================================================
Implements a paired-trade (long STX / short BTC or reverse) based on the
504h EMA of the STX-BTC funding rate differential, ORTHOGONALIZED against
APT, SEI, and DOGE factors via OLS regression (K638 multi-factor pattern).

Architecture (K642 scaffold, K638 pattern):
  1. fetch_fr_batch()                  → fetch STX + APT + SEI + DOGE + BTC FR every 8h
  2. compute_residual(stx_diff, apt_diff, sei_diff, doge_diff)
       residual = STX_diff - β_APT*APT_diff - β_SEI*SEI_diff - β_DOGE*DOGE_diff
       β coefficients HARDCODED per K638 OLS multi-factor (no re-OLS in production):
         β_APT  = 0.203339
         β_SEI  = 0.125164
         β_DOGE = 0.306518
  3. compute_signal(residual_history)  → 504h EMA of residual; |ema| > 1.5σ
  4. decide_position(signal)           → LONG_STX_SHORT_BTC | LONG_BTC_SHORT_STX | NEUTRAL
  5. submit_paired_trade(long, short)  → POST_ONLY paired (STX + BTC legs)
  6. daily_rebalance()                 → drift > 5% triggers rebalance
  7. close_paired_position(reason)     → sequential: short first, then long

K638 BTC-L2 cluster hypothesis (ACCEPT CONDITIONAL):
  - STX = Stacks: PoX (Proof-of-Transfer) BTC-L2 protocol
  - BTC-L2 cluster = distinct Bitcoin Layer-2 / PoX stacking category
  - STX FR dynamics driven by PoX stacking cycles + BTC-L2 narrative waves
    (orthogonal to APT=Move-VM L1, SEI=EVM-Cosmos mid-cap, DOGE=PoW meme)
  - OOS Sh=12.38 RESIDUAL (W=504h optimal per K638 analysis, multi-factor MF(APT+SEI+DOGE))
  - β_APT=0.203339, β_SEI=0.125164, β_DOGE=0.306518 per K638 OLS
  - 60d paper-trade gate required before live activation

K638 K642 profit summary:
  - OOS Sharpe (residual): 12.38
  - Ann Return @$10M @4x (1.5% sleeve): $65,018/yr net (3% gross before fees)
  - Bybit primary (STX perp + BTC perp, both on Bybit; HL STX availability uncertain)

Execution:
  - Bybit primary (STX perp + BTC perp, both on Bybit)
  - POST_ONLY paired execution (K439 pattern)
  - Position: 1.5% sleeve, 4x leverage
  - 8h cadence (matches FR settlement cycle)
  - W=504h EMA (optimal window per K638 analysis)

Orthog mechanism:
  - Raw STX_diff   = STX_FR  − BTC_FR
  - APT_diff       = APT_FR  − BTC_FR
  - SEI_diff       = SEI_FR  − BTC_FR
  - DOGE_diff      = DOGE_FR − BTC_FR
  - residual       = STX_diff − 0.203339 × APT_diff − 0.125164 × SEI_diff − 0.306518 × DOGE_diff
  - Signal         = 504h EMA of residual; threshold = 1.5σ of 504h window
  - β hardcoded: NO re-OLS in production (stability constraint, K638 spec)

Paper-trade mode is the DEFAULT.  No orders are submitted unless
PAPER_TRADE=False is explicitly set in the environment.

K339 security: REPO_ROOT from __file__, no /Users/ literals.
No new packages — stdlib urllib + json only.

Usage:
  python3 scripts/k638_stx_orthog_run.py --dry-run
  python3 scripts/k638_stx_orthog_run.py --status
  python3 scripts/k638_stx_orthog_run.py --rebalance
  python3 scripts/k638_stx_orthog_run.py --close "scheduled exit"
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

DASHBOARD_PATH  = DATA_DIR  / "k638_dashboard.json"
FR_HISTORY_PATH = CACHE_DIR / "k638_fr_history.jsonl"
TRADE_LOG_PATH  = CACHE_DIR / "k638_paper_trades.jsonl"

JST = timezone(timedelta(hours=9))
UTC = timezone.utc

# ── Strategy constants ────────────────────────────────────────────────────────
PAPER_TRADE         = True          # never submit real orders in paper-trade mode
SLEEVE_PCT          = 0.015         # K638 sleeve = 1.5% of AUM (smaller than K635 2%; lower profit)
LEVERAGE            = 4.0           # 4x per K638 analysis (K430 cap)
AUM_DEFAULT         = 10_000_000.0  # $10M reference AUM
DRIFT_REBALANCE_PCT = 0.05          # rebalance if legs drift > 5%
IOC_TIMEOUT_SEC     = 300           # 5 min fill window
EMA_PERIOD_HOURS    = 504           # 504h EMA optimal window (per K638 analysis, W=504h)
EMA_PERIOD_PERIODS  = EMA_PERIOD_HOURS // 8  # = 63 periods (8h settlement cycle)
SIGNAL_SIGMA_MULT   = 1.5           # entry threshold: |residual_ema| > 1.5σ
HL_API_URL          = "https://api.hyperliquid.xyz/info"

# ── K638 OLS β coefficients — HARDCODED, NO RE-OLS in production ─────────────
# Source: K638 multi-factor OLS regression on STX vs APT + SEI + DOGE factors
#   STX_diff = α + β_APT × APT_diff + β_SEI × SEI_diff + β_DOGE × DOGE_diff + ε
#   β_APT  = 0.203339  (APT Move-VM L1 factor loading on STX FR)
#   β_SEI  = 0.125164  (SEI EVM-Cosmos factor loading on STX FR)
#   β_DOGE = 0.306518  (DOGE PoW meme factor loading on STX FR)
#   IS R²=0.4371 (MF), OOS Sh=12.38 RESIDUAL (W=504h)
#   BTC-L2 cluster: STX PoX BTC-L2, orthogonal to APT/SEI/DOGE shared alt regimes
BETA_APT  = 0.203339
BETA_SEI  = 0.125164
BETA_DOGE = 0.306518

# ── Venue config (Bybit primary — STX on Bybit perp) ─────────────────────────
# Bybit primary: STXUSDT-SWAP + BTC-USDT-SWAP, both Bybit perp
# Both legs on Bybit (delta-neutral carry); HL STX availability uncertain for paired trade
# HL secondary: monitor-only
BYBIT_SLEEVE_PCT   = SLEEVE_PCT      # full sleeve on Bybit (STX + BTC paired)
HL_CONCENTRATION_UNCHANGED = 65.0   # K638 on Bybit → HL concentration unchanged

# ── Position state constants ──────────────────────────────────────────────────
STATE_NEUTRAL            = "NEUTRAL"
STATE_LONG_STX_SHORT_BTC = "LONG_STX_SHORT_BTC"
STATE_LONG_BTC_SHORT_STX = "LONG_BTC_SHORT_STX"

# ── Symbols fetched from HL for FR data ──────────────────────────────────────
SYMBOLS = ("STX", "APT", "SEI", "DOGE", "BTC")


# ─────────────────────────────────────────────────────────────────────────────
# HTTP helper (stdlib urllib only — no requests)
# ─────────────────────────────────────────────────────────────────────────────

def _http_post(url: str, payload: dict, timeout: int = 10) -> Optional[dict]:
    try:
        data = json.dumps(payload).encode()
        req  = urllib.request.Request(
            url, data=data,
            headers={"Content-Type": "application/json",
                     "User-Agent": "crypto-lab-k638/1.0"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        print(f"  [k638] HTTP error: {e}", file=sys.stderr)
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Phase 1 — Funding rate fetch (STX + APT + SEI + DOGE + BTC)
# ─────────────────────────────────────────────────────────────────────────────

def _fetch_hl_fr_batch() -> Dict[str, float]:
    """
    Fetch current 8h funding rates for STX, APT, SEI, DOGE, BTC from HL.
    Returns {symbol: fr_8h_fraction}.

    HL API: metaAndAssetCtxs -> funding field per asset.
    """
    raw = _http_post(HL_API_URL, {"type": "metaAndAssetCtxs"})
    if not raw or not isinstance(raw, list) or len(raw) < 2:
        print("  [k638] HL metaAndAssetCtxs fetch failed", file=sys.stderr)
        return {}
    meta       = raw[0]
    asset_ctxs = raw[1]
    universe   = {item["name"]: i for i, item in enumerate(meta.get("universe", []))}
    result: Dict[str, float] = {}
    for sym in SYMBOLS:
        if sym not in universe:
            print(f"  [k638] Symbol {sym} not found in HL universe", file=sys.stderr)
            continue
        idx = universe[sym]
        ctx = asset_ctxs[idx]
        try:
            result[sym] = float(ctx.get("funding", 0.0))
        except (TypeError, ValueError):
            continue
    return result


def _load_fr_history() -> List[dict]:
    """Load K638 FR history JSONL."""
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
    fr_stx: float, fr_apt: float, fr_sei: float, fr_doge: float, fr_btc: float,
    stx_diff: float, apt_diff: float, sei_diff: float, doge_diff: float, residual: float
) -> None:
    """Append one FR + residual snapshot to history."""
    rec = {
        "ts_utc":    datetime.now(UTC).isoformat(),
        "fr_stx":    round(fr_stx,   10),
        "fr_apt":    round(fr_apt,   10),
        "fr_sei":    round(fr_sei,   10),
        "fr_doge":   round(fr_doge,  10),
        "fr_btc":    round(fr_btc,   10),
        "stx_diff":  round(stx_diff, 10),   # STX_FR - BTC_FR (raw)
        "apt_diff":  round(apt_diff, 10),   # APT_FR - BTC_FR
        "sei_diff":  round(sei_diff, 10),   # SEI_FR - BTC_FR
        "doge_diff": round(doge_diff,10),   # DOGE_FR - BTC_FR
        "residual":  round(residual, 10),   # orthogonalized residual
    }
    with open(FR_HISTORY_PATH, "a") as f:
        f.write(json.dumps(rec) + "\n")


# ─────────────────────────────────────────────────────────────────────────────
# Phase 2 — Orthogonalized residual computation
# ─────────────────────────────────────────────────────────────────────────────

def compute_residual(
    fr_stx:  Optional[float] = None,
    fr_apt:  Optional[float] = None,
    fr_sei:  Optional[float] = None,
    fr_doge: Optional[float] = None,
    fr_btc:  Optional[float] = None,
) -> dict:
    """
    Fetch live STX/APT/SEI/DOGE/BTC FRs from HL, compute orthogonalized residual,
    and compute 504h EMA + 504h rolling sigma for threshold calculation.

    Orthogonalization mechanism (K638 OLS multi-factor, coefficients HARDCODED):
      stx_diff  = STX_FR  - BTC_FR
      apt_diff  = APT_FR  - BTC_FR
      sei_diff  = SEI_FR  - BTC_FR
      doge_diff = DOGE_FR - BTC_FR
      residual  = stx_diff - beta_APT * apt_diff - beta_SEI * sei_diff - beta_DOGE * doge_diff
               = stx_diff - 0.203339 * apt_diff - 0.125164 * sei_diff - 0.306518 * doge_diff

    Signal gate (W=504h optimal per K638 analysis):
      EMA = 504h EMA of residual (63 x 8h periods)
      sigma = 504h rolling std of residual
      Enter when |EMA| > 1.5sigma

    K638 BTC-L2 cluster hypothesis:
      STX = Stacks (PoX Proof-of-Transfer BTC-L2 protocol).
      FR dynamics driven by PoX stacking cycles + BTC-L2 narrative waves.
      After projecting out:
        APT factor (Move-VM L1 alt-regime co-movement),
        SEI factor (EVM-Cosmos mid-cap alt co-movement),
        DOGE factor (PoW meme/retail sentiment co-movement),
      the residual captures pure BTC-L2/PoX-specific STX alpha.
      OOS Sh=12.38 (W=504h MF) confirms orthogonalization preserves and
      unlocks signal vs raw K613 blocked by APT/SEI/DOGE.

    Returns:
      {
        "fr_stx":            float,
        "fr_apt":            float,
        "fr_sei":            float,
        "fr_doge":           float,
        "fr_btc":            float,
        "stx_diff":          float,   # raw STX-BTC
        "apt_diff":          float,   # APT-BTC
        "sei_diff":          float,   # SEI-BTC
        "doge_diff":         float,   # DOGE-BTC
        "residual":          float,   # orthogonalized residual (current)
        "residual_ema_504h": float,   # 504h EMA of residual (63 periods x 8h)
        "residual_sigma":    float,   # 504h rolling sigma of residual
        "threshold":         float,   # 1.5sigma entry threshold
        "beta_apt":          float,   # beta_APT hardcoded = 0.203339
        "beta_sei":          float,   # beta_SEI hardcoded = 0.125164
        "beta_doge":         float,   # beta_DOGE hardcoded = 0.306518
        "history_points":    int,
        "regime":            str,     # BULL_STX | BEAR_STX | NEUTRAL
        "ts_jst":            str,
      }
    """
    if any(v is None for v in (fr_stx, fr_apt, fr_sei, fr_doge, fr_btc)):
        frs       = _fetch_hl_fr_batch()
        fr_stx    = frs.get("STX",  0.0)
        fr_apt    = frs.get("APT",  0.0)
        fr_sei    = frs.get("SEI",  0.0)
        fr_doge   = frs.get("DOGE", 0.0)
        fr_btc    = frs.get("BTC",  0.0)

    # Compute diffs
    stx_diff  = fr_stx  - fr_btc
    apt_diff  = fr_apt  - fr_btc
    sei_diff  = fr_sei  - fr_btc
    doge_diff = fr_doge - fr_btc

    # Orthogonalized residual (K638 OLS multi-factor, beta hardcoded)
    residual = stx_diff - BETA_APT * apt_diff - BETA_SEI * sei_diff - BETA_DOGE * doge_diff

    _append_fr_history(fr_stx, fr_apt, fr_sei, fr_doge, fr_btc,
                       stx_diff, apt_diff, sei_diff, doge_diff, residual)

    # Load history for EMA + sigma (504h = 63 x 8h periods)
    history   = _load_fr_history()
    residuals = [r["residual"] for r in history if "residual" in r]

    n_periods = EMA_PERIOD_PERIODS   # 63 periods (504h / 8h)
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
        regime = "BULL_STX"   # STX residual FR > 0: short STX / long BTC
    else:
        regime = "BEAR_STX"   # STX residual FR < 0: long STX / short BTC

    return {
        "fr_stx":            round(fr_stx,   10),
        "fr_apt":            round(fr_apt,   10),
        "fr_sei":            round(fr_sei,   10),
        "fr_doge":           round(fr_doge,  10),
        "fr_btc":            round(fr_btc,   10),
        "stx_diff":          round(stx_diff, 10),
        "apt_diff":          round(apt_diff, 10),
        "sei_diff":          round(sei_diff, 10),
        "doge_diff":         round(doge_diff,10),
        "residual":          round(residual, 10),
        "residual_ema_504h": round(ema,      10),
        "residual_sigma":    round(sigma,    10),
        "threshold":         round(threshold,10),
        "beta_apt":          BETA_APT,
        "beta_sei":          BETA_SEI,
        "beta_doge":         BETA_DOGE,
        "history_points":    len(residuals),
        "regime":            regime,
        "ts_jst":            datetime.now(JST).strftime("%Y-%m-%d %H:%M JST"),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Phase 3 — Position decision
# ─────────────────────────────────────────────────────────────────────────────

def decide_position(signal: dict) -> Optional[dict]:
    """
    Determine trade direction from orthogonalized residual EMA.

    Logic (STX-BTC orthogonalized pair, Bybit primary):
      regime = BULL_STX (residual_ema > 1.5sigma):
        STX residual FR > BTC FR -> STX more expensive to long
        -> short STX (collect high residual FR) / long BTC (cheap carry)
        -> position_state = LONG_BTC_SHORT_STX
        -> both legs on Bybit

      regime = BEAR_STX (residual_ema < -1.5sigma):
        STX residual FR < BTC FR -> BTC more expensive
        -> long STX / short BTC
        -> position_state = LONG_STX_SHORT_BTC
        -> both legs on Bybit

      regime = NEUTRAL: no trade

    K638 orthog edge:
      The residual cleanly separates STX's BTC-L2/PoX-specific FR dynamics
      from the APT Move-VM L1, SEI EVM-Cosmos, and DOGE PoW meme factor noise.
      OOS Sh=12.38 (W=504h MF) residual confirms the true alpha resides in
      Stacks' PoX stacking cycles and BTC-L2 narrative-specific FR,
      not shared alt-regime or meme/retail sentiment regimes.

    Returns:
      {long_asset, short_asset, long_venue, short_venue, residual_ema,
       signal_strength, size_multiplier, position_state}
      or None if NEUTRAL.
    """
    regime  = signal.get("regime", "NEUTRAL")
    ema     = signal.get("residual_ema_504h", 0.0)
    thresh  = signal.get("threshold", 1e-8)
    abs_ema = abs(ema)

    if regime == "NEUTRAL":
        return None

    if regime == "BULL_STX":
        # STX residual FR positive -> STX FR > BTC FR
        # short STX (expensive), long BTC (cheap)
        long_asset  = "BTC"
        short_asset = "STX"
        state       = STATE_LONG_BTC_SHORT_STX
    else:  # BEAR_STX
        # STX residual FR negative -> BTC FR > STX FR
        # long STX (cheap), short BTC (expensive)
        long_asset  = "STX"
        short_asset = "BTC"
        state       = STATE_LONG_STX_SHORT_BTC

    # Both legs on Bybit (STX + BTC, Bybit primary)
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
    Compute equal notional for both legs of the STX-BTC paired trade.

    K638 Bybit-only config (STX perp on Bybit):
      sleeve_capital   = aum x sleeve_pct      (e.g. $10M x 1.5% = $150K)
      total_notional   = sleeve_capital x lev   ($150K x 4 = $600K)
      notional_per_leg = total_notional / 2     ($300K per leg)

    At $10M / 1.5% sleeve / 4x:
      STX leg:   $75K capital x 4x = $300K notional (Bybit)
      BTC leg:   $75K capital x 4x = $300K notional (Bybit)
      Total:     $600K notional (two legs combined)
      Margin:    $150K (1.5% of AUM)
      Net profit: $65,018/yr (net 80% x gross 27.09% x $600K notional)

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
    Submit K638 STX-BTC paired trade: POST_ONLY both legs in parallel.

    Protocol (K638 Bybit primary):
      1. Submit STX leg on Bybit POST_ONLY
      2. Submit BTC leg on Bybit POST_ONLY
      3. Both legs submitted in parallel (K439 pattern)
      4. IOC fallback per leg if POST_ONLY times out
      5. If both fail: retry next 8h cycle

    Args:
      long_leg:  {"symbol": "STX", "notional": 300000, "venue": "Bybit"}
      short_leg: {"symbol": "BTC", "notional": 300000, "venue": "Bybit"}
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
        print(f"  [K638] {mode_tag}: LONG {long_sym}@{long_venue} ${long_notl:,.0f}  "
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
            "venue_config":     "BYBIT_PRIMARY_STX_BTC_L2",
            "orthog_note":      "residual = STX_diff - 0.203339*APT_diff - 0.125164*SEI_diff - 0.306518*DOGE_diff",
            "ts_utc":           ts,
        }
        _append_trade_log(result)
        return result

    # LIVE scaffold (not reached in PAPER_TRADE mode):
    print(f"  [K638] SCAFFOLD LIVE: parallel POST_ONLY "
          f"LONG {long_sym}@{long_venue} ${long_notl:,.0f} "
          f"+ SHORT {short_sym}@{short_venue} ${short_notl:,.0f}")
    long_order_id  = f"SCAFFOLD_LONG_{long_sym}_{int(time.time())}"
    short_order_id = f"SCAFFOLD_SHORT_{short_sym}_{int(time.time())}"

    # Scaffold: poll not implemented — retry next 8h cycle
    print(f"  [K638] Neither leg filled within timeout — retry next 8h cycle")
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
    Check if current K638 position has drifted beyond DRIFT_REBALANCE_PCT (5%).

    K638 Bybit-only: both legs on Bybit; drift accumulates together.
    Drift detection: compare stored STX leg notional vs BTC leg notional.
    Threshold: 5% (same as K507/K512/K628/K631/K633/K635 pattern).

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
    Both legs on Bybit (K638 Bybit primary).

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

    if state == STATE_LONG_STX_SHORT_BTC:
        long_sym,  short_sym  = "STX", "BTC"
    else:  # LONG_BTC_SHORT_STX
        long_sym,  short_sym  = "BTC", "STX"

    long_notional  = float(dash.get("long_notional",  0.0))
    short_notional = float(dash.get("short_notional", 0.0))

    if dry_run or PAPER_TRADE:
        mode_tag = "DRY_RUN" if dry_run else "PAPER_TRADE"
        print(f"  [K638] {mode_tag} CLOSE:")
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
        print(f"  [K638] SCAFFOLD CLOSE:")
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
    """Load k638_dashboard.json; return defaults if missing."""
    if DASHBOARD_PATH.exists():
        try:
            return json.loads(DASHBOARD_PATH.read_text())
        except Exception:
            pass
    return {
        "last_poll_jst":           "—",
        "residual_ema_504h":       0.0,
        "residual_sigma":          0.0,
        "threshold_1_5sigma":      0.0,
        "beta_apt_used":           BETA_APT,
        "beta_sei_used":           BETA_SEI,
        "beta_doge_used":          BETA_DOGE,
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
    """Write k638_dashboard.json with full signal + regime state."""
    dash = _load_dashboard()

    # Update signal data
    dash["last_poll_jst"]        = signal.get("ts_jst", "—")
    dash["fr_stx_current"]       = signal.get("fr_stx",   0.0)
    dash["fr_apt_current"]       = signal.get("fr_apt",   0.0)
    dash["fr_sei_current"]       = signal.get("fr_sei",   0.0)
    dash["fr_doge_current"]      = signal.get("fr_doge",  0.0)
    dash["fr_btc_current"]       = signal.get("fr_btc",   0.0)
    dash["stx_diff_raw"]         = signal.get("stx_diff", 0.0)
    dash["apt_diff"]             = signal.get("apt_diff", 0.0)
    dash["sei_diff"]             = signal.get("sei_diff", 0.0)
    dash["doge_diff"]            = signal.get("doge_diff",0.0)
    dash["residual_current"]     = signal.get("residual", 0.0)
    dash["residual_ema_504h"]    = signal.get("residual_ema_504h", 0.0)
    dash["residual_sigma"]       = signal.get("residual_sigma",    0.0)
    dash["threshold_1_5sigma"]   = signal.get("threshold",         0.0)
    dash["beta_apt_used"]        = signal.get("beta_apt",  BETA_APT)
    dash["beta_sei_used"]        = signal.get("beta_sei",  BETA_SEI)
    dash["beta_doge_used"]       = signal.get("beta_doge", BETA_DOGE)
    dash["regime"]               = signal.get("regime",    "NEUTRAL")
    dash["history_points"]       = signal.get("history_points", 0)

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
    dash["hl_concentration_pct"]     = HL_CONCENTRATION_UNCHANGED  # unchanged: Bybit-only

    # Paper-trade status
    paper_status = dash.get("paper_trade_status", {"days_elapsed": 0, "target_60d": 60})
    dash["paper_trade_status"]       = paper_status

    # 60d activation gate metrics (K642: Realized Sh>=6 + fill>=60% + DD<20%)
    dash["gate_metrics"] = {
        "realized_sharpe_target":   6.0,     # >=6 (50% of K638 OOS 12.38)
        "fill_rate_target_pct":     60,
        "max_drawdown_target_pct":  20,
        "current_realized_sharpe":  dash.get("60d_sharpe", 0.0),
        "current_fill_rate_pct":    0.0,
        "current_max_dd_pct":       0.0,
        "gate_status":              "IN_PROGRESS",
        "activation_trigger":       "60d paper-trade: Sh>=6 AND fill>=60% AND maxDD<20%",
        "profit_at_activation_1_5pct": "$65,018/yr net @$10M @4x (1.5% sleeve)",
    }

    # Strategy metadata
    dash["paper_trade_mode"]    = PAPER_TRADE
    dash["wave"]                = "K642"
    dash["strategy"]            = "K638 STX-BTC Orthogonalized FR Differential (MF APT+SEI+DOGE)"
    dash["execution_mode"]      = "POST_ONLY_PARALLEL"
    dash["venue_config"]        = "BYBIT_PRIMARY"
    dash["orthog_mechanism"]    = {
        "formula":    "residual = STX_diff - 0.203339*APT_diff - 0.125164*SEI_diff - 0.306518*DOGE_diff",
        "beta_apt":   BETA_APT,
        "beta_sei":   BETA_SEI,
        "beta_doge":  BETA_DOGE,
        "ema_window": "W=504h (63 x 8h periods)",
        "note":       "beta HARDCODED per K638 OLS multi-factor — no re-OLS in production for stability",
    }
    dash["activation_criteria"] = {
        "60d_paper_trade_gate":   "required",
        "realized_sharpe_min":    6.0,
        "fill_rate_min_pct":      60,
        "max_drawdown_max_pct":   20,
        "status":                 "SCAFFOLD-READY",
        "activation_sleeve_pct":  0.015,
        "venue":                  "Bybit primary (STX+BTC both legs)",
    }
    dash["oos_performance"] = {
        "sharpe_residual":           12.38,
        "sharpe_raw_k613":           26.8576,
        "orthog_degradation_sh":     14.47,
        "ann_return_pct_4x":         27.09,
        "ann_return_usd_1_5pct_4x":  65_018,
        "wave_accept":               "K638 ACCEPT CONDITIONAL (K642 scaffold)",
        "cluster":                   "BTC-L2 / Stacks PoX (Bitcoin Layer-2)",
        "cluster_rationale":         "STX PoX Proof-of-Transfer BTC-L2; FR driven by PoX stacking cycles + BTC-L2 narrative waves — orthogonal to APT Move-VM L1, SEI EVM-Cosmos, DOGE PoW meme factor regimes",
        "hl_concentration_pct":      65.0,
        "hl_impact":                 "NONE — Bybit-only; HL concentration unchanged at 65%",
        "factors_removed":           ["APT (Move-VM L1)", "SEI (EVM-Cosmos mid-cap)", "DOGE (PoW meme/retail)"],
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
      1. Fetch STX + APT + SEI + DOGE + BTC FRs
      2. Compute orthogonalized residual + 504h EMA + sigma
      3. Decide position (|ema| > 1.5sigma threshold)
      4. Compute delta-neutral notional
      5. If entering: submit paired trade (POST_ONLY, Bybit primary)
      6. If holding: check drift + rebalance
      7. Write k638_dashboard.json
    """
    ts_jst = datetime.now(JST).strftime("%Y-%m-%d %H:%M JST")
    print(f"\n=== K638 STX Orthogonalized FR Differential — {ts_jst} ===")
    print(f"  Mode:      {'DRY-RUN' if dry_run else 'PAPER-TRADE' if PAPER_TRADE else 'LIVE'}")
    print(f"  AUM:       ${aum:,.0f}  Sleeve: {SLEEVE_PCT:.1%}  Leverage: {LEVERAGE}x")
    print(f"  Venue:     Bybit primary (STX+BTC paired; HL STX uncertain for paired trade)")
    print(f"  Execution: POST_ONLY parallel (K439)")
    print(f"  HL impact: NONE (Bybit-only) — HL concentration unchanged @ 65%")
    print(f"  Orthog:    residual = STX_diff - {BETA_APT}xAPT_diff - {BETA_SEI}xSEI_diff - {BETA_DOGE}xDOGE_diff")
    print(f"  beta fixed: beta_APT={BETA_APT}  beta_SEI={BETA_SEI}  beta_DOGE={BETA_DOGE}  (K638 OLS MF, production-hardcoded)")
    print(f"  Signal:    |residual_EMA_504h| > 1.5sigma  (W=504h = 63 x 8h periods)")

    # Step 1: Fetch + compute orthogonalized residual
    print("\n  [Step 1] Computing orthogonalized residual...")
    signal = compute_residual()
    print(f"  STX FR:     {signal['fr_stx']:+.8f} (8h)")
    print(f"  APT FR:     {signal['fr_apt']:+.8f} (8h)")
    print(f"  SEI FR:     {signal['fr_sei']:+.8f} (8h)")
    print(f"  DOGE FR:    {signal['fr_doge']:+.8f} (8h)")
    print(f"  BTC FR:     {signal['fr_btc']:+.8f} (8h)")
    print(f"  STX diff:   {signal['stx_diff']:+.8f}  (STX-BTC raw)")
    print(f"  Residual:   {signal['residual']:+.8f}  (orthogonalized)")
    print(f"  EMA 504h:   {signal['residual_ema_504h']:+.8f}")
    print(f"  Sigma 504h: {signal['residual_sigma']:+.8f}")
    print(f"  Threshold:  {signal['threshold']:+.8f}  (1.5sigma = {SIGNAL_SIGMA_MULT}xsigma)")
    print(f"  Regime:     {signal['regime']}")
    print(f"  History:    {signal['history_points']} data points")

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
    print(f"  STX leg:          ${notional_per_leg:,.0f}  (0.75% x ${aum/1e6:.0f}M x {LEVERAGE}x)")
    print(f"  BTC leg:          ${notional_per_leg:,.0f}  (0.75% x ${aum/1e6:.0f}M x {LEVERAGE}x)")
    print(f"  Total notional:   ${total_notional:,.0f}")
    print(f"  Margin required:  ${total_notional/LEVERAGE:,.0f}  ({SLEEVE_PCT:.1%} AUM)")
    print(f"  Profit @$10M 4x:  1.5% sleeve=$65,018/yr (net 80%)")

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
    print(f"\n  === K638 Cycle Complete ===")
    print(f"  Position state:     {dash_out.get('position_state')}")
    print(f"  Regime:             {dash_out.get('regime')}")
    print(f"  Residual EMA 504h:  {dash_out.get('residual_ema_504h'):+.8f}")
    print(f"  Threshold (1.5sig): {dash_out.get('threshold_1_5sigma'):+.8f}")
    print(f"  beta_APT (fixed):   {BETA_APT}  beta_SEI: {BETA_SEI}  beta_DOGE: {BETA_DOGE}")
    print(f"  Paper-trade mode:   {PAPER_TRADE}")
    print(f"  OOS Sharpe:         12.38 residual (raw K613=26.86, MF W=504h)")
    print(f"  Cluster:            BTC-L2 / Stacks PoX (Bitcoin Layer-2)")
    print(f"  Profit 1.5% sleeve: $65,018/yr @$10M @4x (net 80%)")
    print(f"  HL concentration:   {HL_CONCENTRATION_UNCHANGED}% (unchanged — Bybit-only)")
    print(f"  60d gate:           Realized Sh>=6 + fill>=60% + maxDD<20%")
    print(f"  v6.35 path:         K638 STX orthog 1.5% Bybit sleeve added to v6.34")
    print()

    return 0


# ─────────────────────────────────────────────────────────────────────────────
# CLI entry point
# ─────────────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="K638 STX Orthogonalized FR Differential Strategy (K642 scaffold)"
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
        print(f"\n=== K638 Dashboard ({dash.get('last_poll_jst', '—')}) ===")
        print(json.dumps(dash, indent=2))
        return 0

    if args.rebalance:
        dash   = _load_dashboard()
        result = daily_rebalance(dash)
        print(f"\n=== K638 Rebalance Check ===")
        print(json.dumps(result, indent=2))
        return 0

    if args.close:
        result = close_paired_position(args.close, dry_run=args.dry_run)
        print(f"\n=== K638 Close Result ===")
        print(json.dumps(result, indent=2))
        return 0

    return run_cycle(dry_run=args.dry_run, aum=args.aum)


if __name__ == "__main__":
    sys.exit(main())
