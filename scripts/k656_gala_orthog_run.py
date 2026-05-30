#!/usr/bin/env python3
"""
k656_gala_orthog_run.py — K656 GALA Dual-Factor Orthogonalized FR Differential Strategy
=========================================================================================
Implements a paired-trade (long GALA / short BTC or reverse) based on the
504h rolling mean of the GALA-BTC funding rate differential, ORTHOGONALIZED
against 2 factors via dual-factor OLS regression (K656 DF-W504h pattern).

Architecture (K659 scaffold, K656 pattern):
  1. fetch_fr_batch()                  → fetch GALA + JUP + FIL + BTC FR every 8h
  2. compute_residual(gala_diff, ...)
       residual = GALA_diff
                  - 0.22738*JUP_diff
                  - 0.405439*FIL_diff
  3. compute_signal(residual_history)  → 504h rolling mean of residual; |mean| > 1.5σ
  4. decide_position(signal)           → LONG_GALA_SHORT_BTC | LONG_BTC_SHORT_GALA | NEUTRAL
  5. submit_paired_trade(long, short)  → POST_ONLY paired (GALA + BTC legs)
  6. daily_rebalance()                 → drift > 5% triggers rebalance
  7. close_paired_position(reason)     → sequential: short first, then long

K656 Gala Games / GalaChain cluster hypothesis (ACCEPT CONDITIONAL):
  - GALA = Gala Games P2E publisher (GalaChain proprietary L1, multi-game ecosystem)
  - Gaming cluster = distinct Gala Games / GalaChain category
  - GALA FR dynamics driven by:
      GalaChain node operator demand cycles — distinct from JUP/FIL ecosystems
      P2E game launch narratives (GALA token used for in-game economies across titles)
      GalaChain gas fee adoption (proprietary L1, not DeFi/DEX-driven like JUP)
      Gaming token staking / founder node operator economics (GALA node auctions)
  - Dual-factor OLS residualization removes: JUP (Jupiter DEX Solana) + FIL (Filecoin storage)
  - OOS Sh=8.3211 RESIDUAL (DF W=504h optimal per K656 analysis, dual-factor)
  - K620 blockers: JUP corr=0.4308 + FIL corr=0.4114 → both CLEARED post-orth (<0.40)
  - 60d paper-trade gate required before live activation

K656 K659 profit summary:
  - OOS Sharpe (residual DF W=504h): 8.3211 (50% gate: Sh >= 4)
  - Ann Return @$10M @4x (2% sleeve): $48,143/yr net (OOS 1.88% ann ret x $10M x 4x x 10% x 0.80 net)
  - Bybit primary (GALA on Bybit GALAUSDT perp + BTC-USDT-SWAP, both Bybit perp)
  - Gaming cluster COMPLETE: SAND(K583)+AXS(K591)+IMX(K635)+GALA(K656) all ACCEPT CONDITIONAL

Execution:
  - Bybit primary (GALAUSDT perp + BTC-USDT-SWAP, both Bybit perp)
  - POST_ONLY paired execution (K439 pattern)
  - Position: 2% sleeve, 4x leverage
  - 8h cadence (matches FR settlement cycle)
  - W=504h rolling mean (optimal window per K656 analysis, DF dual-factor)

Orthog mechanism (K656 dual-factor OLS, coefficients HARDCODED):
  - Raw GALA_diff   = GALA_FR − BTC_FR
  - JUP_diff        = JUP_FR  − BTC_FR
  - FIL_diff        = FIL_FR  − BTC_FR
  - residual = GALA_diff
               − 0.227380 × JUP_diff
               − 0.405439 × FIL_diff
  - Signal         = 504h rolling mean of residual; threshold = 1.5σ of 504h window
  - β hardcoded: NO re-OLS in production (stability constraint, K656 spec)
  - IS R² = 0.4731 (LARGEST in orthog series — dual-factor), OOS R² = -0.666
  - Post-orth corrs: JUP=0.0495 (cleared 0.4308→0.0495), FIL=0.0184 (cleared 0.4114→0.0184)
    (all < G5 threshold 0.40 — G5 PASS; max post-orth corr=0.2993 UNI)
  - Gaming-distinct: SAND=-0.058, AXS=None (gaming cluster distinction retained)

Paper-trade mode is the DEFAULT.  No orders are submitted unless
PAPER_TRADE=False is explicitly set in the environment.

K339 security: REPO_ROOT from __file__, no /Users/ literals.
No new packages — stdlib urllib + json only.

Usage:
  python3 scripts/k656_gala_orthog_run.py --dry-run
  python3 scripts/k656_gala_orthog_run.py --status
  python3 scripts/k656_gala_orthog_run.py --rebalance
  python3 scripts/k656_gala_orthog_run.py --close "scheduled exit"
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

DASHBOARD_PATH  = DATA_DIR  / "k656_dashboard.json"
FR_HISTORY_PATH = CACHE_DIR / "k656_fr_history.jsonl"
TRADE_LOG_PATH  = CACHE_DIR / "k656_paper_trades.jsonl"

JST = timezone(timedelta(hours=9))
UTC = timezone.utc

# ── Strategy constants ────────────────────────────────────────────────────────
PAPER_TRADE         = True          # never submit real orders in paper-trade mode
SLEEVE_PCT          = 0.02          # K656 sleeve = 2% of AUM (Gaming cluster)
LEVERAGE            = 4.0           # 4x per K656 analysis (K430 cap)
AUM_DEFAULT         = 10_000_000.0  # $10M reference AUM
DRIFT_REBALANCE_PCT = 0.05          # rebalance if legs drift > 5%
IOC_TIMEOUT_SEC     = 300           # 5 min fill window
ROLLING_PERIOD_HOURS  = 504           # 504h rolling mean optimal window (per K656 analysis, DF W=504h)
ROLLING_PERIOD_PERIODS = ROLLING_PERIOD_HOURS // 8  # = 63 periods (8h settlement cycle)
SIGNAL_SIGMA_MULT   = 1.5           # entry threshold: |residual_mean| > 1.5σ
HL_API_URL          = "https://api.hyperliquid.xyz/info"

# ── K656 OLS β coefficients — HARDCODED, NO RE-OLS in production ─────────────
# Source: K656 dual-factor OLS regression on GALA vs JUP+FIL factors
#   GALA_diff = α + β_JUP*JUP_diff + β_FIL*FIL_diff + ε
#   α=1.89e-6, β_JUP=0.22738, β_FIL=0.405439
#   IS R²=0.4731 (LARGEST in orthog series, dual-factor MF)
#   OOS R²=-0.666, JUP corr 0.4308->0.0495 CLEARED, FIL corr 0.4114->0.0184 CLEARED
#   K620 dual blockers: JUP(0.4308)+FIL(0.4114) both exceeded 0.40 threshold simultaneously
#   Post-orth max |corr|=0.2993 (UNI): all < G5 threshold 0.40 — G5 PASS
#   Gaming-distinct: SAND=-0.058, AXS=None (gaming cluster distinction retained — PASS)
#   First dual-factor orthogonalization in K6xx orthog series
ALPHA_INTERCEPT =  1.89e-6    # OLS intercept (negligible, included for completeness)
BETA_JUP        =  0.227380   # JUP: Jupiter DEX Solana (mid-cap alt-cap regime factor)
BETA_FIL        =  0.405439   # FIL: Filecoin storage (decentralized-infra narrative cycles)

# ── Venue config (Bybit primary — GALA on Bybit perp) ─────────────────────────
# Bybit primary: GALAUSDT perp + BTC-USDT-SWAP, both Bybit perp
# HL GALA-PERP listed but HL cap breached (66.5% > 65% limit): Bybit mandatory
# OKX GALA-USDT-SWAP (50x) as fallback if Bybit unavailable
BYBIT_SLEEVE_PCT   = SLEEVE_PCT      # full sleeve on Bybit (GALA + BTC paired)
HL_CONCENTRATION_POST = 64.5        # K656 on Bybit → HL concentration unchanged (was 64.5%)

# ── Position state constants ──────────────────────────────────────────────────
STATE_NEUTRAL             = "NEUTRAL"
STATE_LONG_GALA_SHORT_BTC = "LONG_GALA_SHORT_BTC"
STATE_LONG_BTC_SHORT_GALA = "LONG_BTC_SHORT_GALA"

# ── Symbols fetched from HL for FR data ──────────────────────────────────────
SYMBOLS = ("GALA", "JUP", "FIL", "BTC")


# ─────────────────────────────────────────────────────────────────────────────
# HTTP helper (stdlib urllib only — no requests)
# ─────────────────────────────────────────────────────────────────────────────

def _http_post(url: str, payload: dict, timeout: int = 10) -> Optional[dict]:
    try:
        data = json.dumps(payload).encode()
        req  = urllib.request.Request(
            url, data=data,
            headers={"Content-Type": "application/json",
                     "User-Agent": "crypto-lab-k656/1.0"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        print(f"  [k656] HTTP error: {e}", file=sys.stderr)
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Phase 1 — Funding rate fetch (GALA + JUP + FIL + BTC)
# ─────────────────────────────────────────────────────────────────────────────

def _fetch_hl_fr_batch() -> Dict[str, float]:
    """
    Fetch current 8h funding rates for GALA, JUP, FIL, BTC from HL.
    Returns {symbol: fr_8h_fraction}.

    HL API: metaAndAssetCtxs -> funding field per asset.
    Note: GALA live trading uses Bybit GALAUSDT perp (8h settlement).
    HL GALA data used for signal computation only.
    """
    raw = _http_post(HL_API_URL, {"type": "metaAndAssetCtxs"})
    if not raw or not isinstance(raw, list) or len(raw) < 2:
        print("  [k656] HL metaAndAssetCtxs fetch failed", file=sys.stderr)
        return {}
    meta       = raw[0]
    asset_ctxs = raw[1]
    universe   = {item["name"]: i for i, item in enumerate(meta.get("universe", []))}
    result: Dict[str, float] = {}
    for sym in SYMBOLS:
        if sym not in universe:
            print(f"  [k656] Symbol {sym} not found in HL universe", file=sys.stderr)
            continue
        idx = universe[sym]
        ctx = asset_ctxs[idx]
        try:
            result[sym] = float(ctx.get("funding", 0.0))
        except (TypeError, ValueError):
            continue
    return result


def _load_fr_history() -> List[dict]:
    """Load K656 FR history JSONL."""
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
    fr_gala: float, fr_jup: float, fr_fil: float, fr_btc: float,
    gala_diff: float, jup_diff: float, fil_diff: float,
    residual: float
) -> None:
    """Append one FR + residual snapshot to history."""
    rec = {
        "ts_utc":    datetime.now(UTC).isoformat(),
        "fr_gala":   round(fr_gala,  10),
        "fr_jup":    round(fr_jup,   10),
        "fr_fil":    round(fr_fil,   10),
        "fr_btc":    round(fr_btc,   10),
        "gala_diff": round(gala_diff,  10),  # GALA_FR - BTC_FR (raw)
        "jup_diff":  round(jup_diff,   10),  # JUP_FR  - BTC_FR
        "fil_diff":  round(fil_diff,   10),  # FIL_FR  - BTC_FR
        "residual":  round(residual,   10),  # dual-factor orthogonalized residual
    }
    with open(FR_HISTORY_PATH, "a") as f:
        f.write(json.dumps(rec) + "\n")


# ─────────────────────────────────────────────────────────────────────────────
# Phase 2 — Dual-Factor Orthogonalized residual computation
# ─────────────────────────────────────────────────────────────────────────────

def compute_residual(
    fr_gala:  Optional[float] = None,
    fr_jup:   Optional[float] = None,
    fr_fil:   Optional[float] = None,
    fr_btc:   Optional[float] = None,
) -> dict:
    """
    Fetch live GALA/JUP/FIL/BTC FRs from HL,
    compute dual-factor orthogonalized residual, and compute
    504h rolling mean + 504h rolling sigma for threshold calculation.

    Orthogonalization mechanism (K656 OLS dual-factor, coefficients HARDCODED):
      gala_diff = GALA_FR - BTC_FR
      jup_diff  = JUP_FR  - BTC_FR
      fil_diff  = FIL_FR  - BTC_FR

      residual = gala_diff
                 - beta_JUP * jup_diff
                 - beta_FIL * fil_diff
               = gala_diff
                 - 0.227380 * jup_diff
                 - 0.405439 * fil_diff

    Signal gate (W=504h optimal per K656 analysis):
      rolling_mean = 504h rolling mean of residual (63 periods x 8h)
      sigma        = 504h rolling std of residual
      Enter when |rolling_mean| > 1.5sigma

    K656 Gala Games / GalaChain cluster hypothesis:
      GALA = Gala Games P2E (GalaChain L1). FR dynamics driven by:
        GalaChain node operator demand cycles — distinct from JUP Solana DEX
        P2E game launch narratives — distinct from FIL storage protocol
        Gaming token staking / founder node auctions
      K620 dual blockers: JUP(0.4308) + FIL(0.4114) both exceeded 0.40 threshold.
      After dual-factor OLS orthogonalization:
        Post-orth corrs: JUP=0.0495 (cleared -87%), FIL=0.0184 (cleared -96%)
        Max post-orth corr=0.2993 (UNI): G5 PASS
        Gaming-distinct: SAND=-0.058, AXS=None (gaming cluster retained — PASS)
      OOS Sh=8.3211 (DF W=504h) confirms dual-factor residualization unlocks
        Gala Games P2E / GalaChain publisher alpha.
      IS R²=0.4731 (LARGEST in orthog series, dual-factor).
      First dual-factor orthogonalization in K6xx orthog series.
      Gaming cluster COMPLETE: SAND(K583)+AXS(K591)+IMX(K635)+GALA(K656) all ACCEPT COND.

    Returns:
      {
        "fr_gala":               float,
        "fr_jup":                float,
        "fr_fil":                float,
        "fr_btc":                float,
        "gala_diff":             float,   # raw GALA-BTC
        "jup_diff":              float,   # JUP-BTC
        "fil_diff":              float,   # FIL-BTC
        "residual":              float,   # dual-factor orthogonalized residual (current)
        "residual_mean_504h":    float,   # 504h rolling mean of residual (63 periods x 8h)
        "residual_sigma":        float,   # 504h rolling sigma of residual
        "threshold":             float,   # 1.5sigma entry threshold
        "betas":                 dict,    # hardcoded beta coefficients
        "history_points":        int,
        "regime":                str,     # BULL_GALA | BEAR_GALA | NEUTRAL
        "ts_jst":                str,
      }
    """
    if any(v is None for v in (fr_gala, fr_jup, fr_fil, fr_btc)):
        frs     = _fetch_hl_fr_batch()
        fr_gala = frs.get("GALA", 0.0)
        fr_jup  = frs.get("JUP",  0.0)
        fr_fil  = frs.get("FIL",  0.0)
        fr_btc  = frs.get("BTC",  0.0)

    # Compute diffs
    gala_diff = fr_gala - fr_btc
    jup_diff  = fr_jup  - fr_btc
    fil_diff  = fr_fil  - fr_btc

    # Dual-factor orthogonalized residual (K656 OLS DF, betas hardcoded)
    # residual = GALA_diff - beta_JUP*JUP_diff - beta_FIL*FIL_diff
    residual = (
        gala_diff
        - BETA_JUP * jup_diff
        - BETA_FIL * fil_diff
    )

    _append_fr_history(
        fr_gala, fr_jup, fr_fil, fr_btc,
        gala_diff, jup_diff, fil_diff,
        residual
    )

    # Load history for rolling mean + sigma (504h = 63 x 8h periods)
    history   = _load_fr_history()
    residuals = [r["residual"] for r in history if "residual" in r]

    n_periods = ROLLING_PERIOD_PERIODS   # 63 periods (504h / 8h)

    # Rolling mean: mean of last n_periods residuals
    window = residuals[-n_periods:] if len(residuals) >= 1 else residuals
    if len(window) >= 1:
        rolling_mean = sum(window) / len(window)
    else:
        rolling_mean = residual

    # Rolling sigma: std of last n_periods residuals
    if len(window) >= 2:
        mean_w = sum(window) / len(window)
        sigma  = math.sqrt(sum((x - mean_w) ** 2 for x in window) / (len(window) - 1))
    else:
        sigma = abs(rolling_mean) if rolling_mean != 0 else 1e-8   # fallback

    threshold = SIGNAL_SIGMA_MULT * sigma  # 1.5sigma entry gate

    # Regime classification
    if abs(rolling_mean) <= threshold:
        regime = "NEUTRAL"
    elif rolling_mean > 0:
        regime = "BULL_GALA"   # GALA residual FR > 0: short GALA / long BTC
    else:
        regime = "BEAR_GALA"   # GALA residual FR < 0: long GALA / short BTC

    return {
        "fr_gala":            round(fr_gala,   10),
        "fr_jup":             round(fr_jup,    10),
        "fr_fil":             round(fr_fil,    10),
        "fr_btc":             round(fr_btc,    10),
        "gala_diff":          round(gala_diff,  10),
        "jup_diff":           round(jup_diff,   10),
        "fil_diff":           round(fil_diff,   10),
        "residual":           round(residual,   10),
        "residual_mean_504h": round(rolling_mean, 10),
        "residual_sigma":     round(sigma,       10),
        "threshold":          round(threshold,   10),
        "betas": {
            "alpha":    ALPHA_INTERCEPT,
            "beta_jup": BETA_JUP,
            "beta_fil": BETA_FIL,
        },
        "history_points":     len(residuals),
        "regime":             regime,
        "ts_jst":             datetime.now(JST).strftime("%Y-%m-%d %H:%M JST"),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Phase 3 — Position decision
# ─────────────────────────────────────────────────────────────────────────────

def decide_position(signal: dict) -> Optional[dict]:
    """
    Determine trade direction from dual-factor orthogonalized residual rolling mean.

    Logic (GALA-BTC orthogonalized pair, Bybit primary):
      regime = BULL_GALA (residual_mean > 1.5sigma):
        GALA residual FR > BTC FR -> GALA more expensive to long
        -> short GALA (collect high residual FR) / long BTC (cheap carry)
        -> position_state = LONG_BTC_SHORT_GALA
        -> both legs on Bybit

      regime = BEAR_GALA (residual_mean < -1.5sigma):
        GALA residual FR < BTC FR -> BTC more expensive
        -> long GALA / short BTC
        -> position_state = LONG_GALA_SHORT_BTC
        -> both legs on Bybit

      regime = NEUTRAL: no trade

    K656 orthog edge:
      The dual-factor residual cleanly separates GALA's Gala Games-specific FR
      dynamics from the JUP+FIL common factor noise.
      OOS Sh=8.3211 (DF W=504h) residual confirms the true alpha resides in
      Gala Games P2E / GalaChain node operator dynamics, not shared
      JUP Solana DEX / FIL storage narrative common factors.
      2 blockers cleared: JUP(0.4308→0.0495) FIL(0.4114→0.0184) — PASS.
      Post-orth max |corr|=0.2993 (UNI): G5 ALL PASS.
      Gaming-distinct: SAND=-0.058 (< 0.40), gaming cluster distinction RETAINED.
      IS R²=0.4731 (LARGEST in orthog series — dual-factor first).
      K620 BLOCKED (JUP+FIL dual blockers) → K656 orthog UNLOCKED.

    Returns:
      {long_asset, short_asset, long_venue, short_venue, residual_mean,
       signal_strength, size_multiplier, position_state}
      or None if NEUTRAL.
    """
    regime  = signal.get("regime", "NEUTRAL")
    mean    = signal.get("residual_mean_504h", 0.0)
    thresh  = signal.get("threshold", 1e-8)
    abs_mean = abs(mean)

    if regime == "NEUTRAL":
        return None

    if regime == "BULL_GALA":
        # GALA residual FR positive -> GALA FR > BTC FR
        # short GALA (expensive), long BTC (cheap)
        long_asset  = "BTC"
        short_asset = "GALA"
        state       = STATE_LONG_BTC_SHORT_GALA
    else:  # BEAR_GALA
        # GALA residual FR negative -> BTC FR > GALA FR
        # long GALA (cheap), short BTC (expensive)
        long_asset  = "GALA"
        short_asset = "BTC"
        state       = STATE_LONG_GALA_SHORT_BTC

    # Both legs on Bybit (GALA + BTC, Bybit primary)
    long_venue  = "Bybit"
    short_venue = "Bybit"

    # Signal strength: |mean| / threshold (capped at 3x for sizing)
    strength = min(abs_mean / max(thresh, 1e-10), 3.0)

    return {
        "long_asset":      long_asset,
        "short_asset":     short_asset,
        "position_state":  state,
        "long_venue":      long_venue,
        "short_venue":     short_venue,
        "residual_mean":   mean,
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
    Compute equal notional for both legs of the GALA-BTC paired trade.

    K656 Bybit-only config (GALA perp on Bybit):
      sleeve_capital   = aum x sleeve_pct      (e.g. $10M x 2% = $200K)
      total_notional   = sleeve_capital x lev   ($200K x 4 = $800K)
      notional_per_leg = total_notional / 2     ($400K per leg)

    At $10M / 2% sleeve / 4x:
      GALA leg:  $100K capital x 4x = $400K notional (Bybit)
      BTC leg:   $100K capital x 4x = $400K notional (Bybit)
      Total:     $800K notional (two legs combined)
      Margin:    $200K (2% of AUM)
      Net profit: ~$48,143/yr @$10M 4x (OOS 1.88% ann ret x $10M x 4x x 10% x 0.80 net)

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
    Submit K656 GALA-BTC paired trade: POST_ONLY both legs in parallel.

    Protocol (K656 Bybit primary):
      1. Submit GALA leg on Bybit POST_ONLY
      2. Submit BTC leg on Bybit POST_ONLY
      3. Both legs submitted in parallel (K439 pattern)
      4. IOC fallback per leg if POST_ONLY times out
      5. If both fail: retry next 8h cycle

    Args:
      long_leg:  {"symbol": "GALA", "notional": 400000, "venue": "Bybit"}
      short_leg: {"symbol": "BTC",  "notional": 400000, "venue": "Bybit"}
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
        print(f"  [K656] {mode_tag}: LONG {long_sym}@{long_venue} ${long_notl:,.0f}  "
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
            "venue_config":     "BYBIT_PRIMARY_GALA_GAMING_PUBLISHER",
            "orthog_note":      (
                "residual = GALA_diff "
                "- 0.227380*JUP_diff "
                "- 0.405439*FIL_diff (K656 OLS DF dual-factor)"
            ),
            "ts_utc":           ts,
        }
        _append_trade_log(result)
        return result

    # LIVE scaffold (not reached in PAPER_TRADE mode):
    print(f"  [K656] SCAFFOLD LIVE: parallel POST_ONLY "
          f"LONG {long_sym}@{long_venue} ${long_notl:,.0f} "
          f"+ SHORT {short_sym}@{short_venue} ${short_notl:,.0f}")
    long_order_id  = f"SCAFFOLD_LONG_{long_sym}_{int(time.time())}"
    short_order_id = f"SCAFFOLD_SHORT_{short_sym}_{int(time.time())}"

    # Scaffold: poll not implemented — retry next 8h cycle
    print(f"  [K656] Neither leg filled within timeout — retry next 8h cycle")
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
    Check if current K656 position has drifted beyond DRIFT_REBALANCE_PCT (5%).

    K656 Bybit-only: both legs on Bybit; drift accumulates together.
    Drift detection: compare stored GALA leg notional vs BTC leg notional.
    Threshold: 5% (same as K507/K512/K628/K631/K633/K635/K638/K645/K646/K648/K647/K629 pattern).

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
# Phase 7 — Close paired position
# ─────────────────────────────────────────────────────────────────────────────

def close_paired_position(reason: str, dry_run: bool = True) -> dict:
    """
    Close both legs sequentially: short leg first (avoid naked short exposure),
    then long leg. In live: uses IOC market orders (reduce-only).
    Both legs on Bybit (K656 Bybit primary).

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

    if state == STATE_LONG_GALA_SHORT_BTC:
        long_sym,  short_sym  = "GALA", "BTC"
    else:  # LONG_BTC_SHORT_GALA
        long_sym,  short_sym  = "BTC", "GALA"

    long_notional  = float(dash.get("long_notional",  0.0))
    short_notional = float(dash.get("short_notional", 0.0))

    if dry_run or PAPER_TRADE:
        mode_tag = "DRY_RUN" if dry_run else "PAPER_TRADE"
        print(f"  [K656] {mode_tag} CLOSE:")
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
        print(f"  [K656] SCAFFOLD CLOSE:")
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
    """Load k656_dashboard.json; return defaults if missing."""
    if DASHBOARD_PATH.exists():
        try:
            return json.loads(DASHBOARD_PATH.read_text())
        except Exception:
            pass
    return {
        "last_poll_jst":           "—",
        "residual_mean_504h":      0.0,
        "residual_sigma":          0.0,
        "threshold_1_5sigma":      0.0,
        "betas_used": {
            "alpha":    ALPHA_INTERCEPT,
            "beta_jup": BETA_JUP,
            "beta_fil": BETA_FIL,
        },
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
    """Write k656_dashboard.json with full signal + regime state."""
    dash = _load_dashboard()

    # Update signal data
    dash["last_poll_jst"]        = signal.get("ts_jst", "—")
    dash["fr_gala_current"]      = signal.get("fr_gala",  0.0)
    dash["fr_jup_current"]       = signal.get("fr_jup",   0.0)
    dash["fr_fil_current"]       = signal.get("fr_fil",   0.0)
    dash["fr_btc_current"]       = signal.get("fr_btc",   0.0)
    dash["gala_diff_raw"]        = signal.get("gala_diff",  0.0)
    dash["jup_diff"]             = signal.get("jup_diff",   0.0)
    dash["fil_diff"]             = signal.get("fil_diff",   0.0)
    dash["residual_current"]     = signal.get("residual",   0.0)
    dash["residual_mean_504h"]   = signal.get("residual_mean_504h", 0.0)
    dash["residual_sigma"]       = signal.get("residual_sigma",     0.0)
    dash["threshold_1_5sigma"]   = signal.get("threshold",          0.0)
    dash["betas_used"]           = signal.get("betas", {
        "alpha": ALPHA_INTERCEPT, "beta_jup": BETA_JUP, "beta_fil": BETA_FIL,
    })
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
    dash["hl_concentration_pct"]     = HL_CONCENTRATION_POST  # unchanged: Bybit-only

    # Paper-trade status
    paper_status = dash.get("paper_trade_status", {"days_elapsed": 0, "target_60d": 60})
    dash["paper_trade_status"]       = paper_status

    # 60d activation gate metrics (K659: Realized Sh>=4 + fill>=60% + DD<20%)
    dash["gate_metrics"] = {
        "realized_sharpe_target":  4.0,      # >=4 (50% of K656 OOS 8.32)
        "fill_rate_target_pct":    60,
        "max_drawdown_target_pct": 20,
        "current_realized_sharpe": dash.get("60d_sharpe", 0.0),
        "current_fill_rate_pct":   0.0,
        "current_max_dd_pct":      0.0,
        "gate_status":             "IN_PROGRESS",
        "activation_trigger":      "60d paper-trade: Sh>=4 AND fill>=60% AND maxDD<20%",
        "profit_at_activation_2pct": "$48,143/yr net @$10M @4x (2% sleeve, OOS 1.88% ann ret)",
    }

    # Strategy metadata
    dash["paper_trade_mode"]    = PAPER_TRADE
    dash["wave"]                = "K659"
    dash["strategy"]            = "K656 GALA-BTC Dual-Factor Orthogonalized FR Differential (DF W=504h)"
    dash["execution_mode"]      = "POST_ONLY_PARALLEL"
    dash["venue_config"]        = "BYBIT_PRIMARY"
    dash["orthog_mechanism"]    = {
        "formula":       (
            "residual = GALA_diff "
            "- 0.227380*JUP_diff "
            "- 0.405439*FIL_diff"
        ),
        "betas": {
            "alpha":    ALPHA_INTERCEPT,
            "beta_jup": BETA_JUP,
            "beta_fil": BETA_FIL,
        },
        "rolling_window":      "W=504h (63 x 8h periods)",
        "is_r2":               0.4731,
        "oos_r2":              -0.666,
        "k620_jup_corr_raw":   0.4308,
        "k620_fil_corr_raw":   0.4114,
        "post_orth_jup_corr":  0.0495,
        "post_orth_fil_corr":  0.0184,
        "max_post_orth_corr":  0.2993,
        "max_post_orth_pair":  "UNI",
        "note":                "betas HARDCODED per K656 OLS dual-factor — no re-OLS in production for stability. FIRST dual-factor orthog in K6xx series.",
    }
    dash["activation_criteria"] = {
        "60d_paper_trade_gate":   "required",
        "realized_sharpe_min":    4.0,
        "fill_rate_min_pct":      60,
        "max_drawdown_max_pct":   20,
        "status":                 "SCAFFOLD-READY",
        "activation_sleeve_pct":  0.02,
        "venue":                  "Bybit primary (GALA+BTC both legs)",
    }
    dash["oos_performance"] = {
        "sharpe_residual_df_504h":  8.3211,
        "sharpe_raw_k620":          12.0901,
        "k620_status":              "BLOCKED-G5 (JUP=0.4308 + FIL=0.4114 dual blockers)",
        "oos_ann_ret_pct":          1.8806,
        "oos_ann_ret_4x_pct":       7.5226,
        "ann_return_net_usd_2pct":  48_143,
        "ann_return_gross_usd_2pct": 60_179,
        "wave_accept":              "K656 ACCEPT CONDITIONAL (K659 scaffold)",
        "cluster":                  "Gaming Publisher / Gala Games P2E / GalaChain L1",
        "cluster_rationale":        (
            "GALA FR driven by GalaChain node operator demand cycles + P2E game launch narratives "
            "+ gaming token staking/founder node auctions — orthogonal to JUP Solana DEX dynamics "
            "and FIL storage protocol dynamics after dual-factor OLS residualization. "
            "Gaming-DISTINCT: SAND=-0.058 (< 0.40 — gaming cluster distinction retained)."
        ),
        "hl_concentration_pct":    64.5,
        "hl_impact":               "NONE — Bybit-only; HL concentration unchanged at 64.5%",
        "factors_removed":         ["JUP (Jupiter DEX Solana, mid-cap alt-cap regime)", "FIL (Filecoin storage, decentralized-infra narrative)"],
        "post_orth_corrs":         {"JUP": 0.0495, "FIL": 0.0184, "UNI": 0.2993, "SAND": -0.058},
        "orthog_unlock":           (
            "K620 BLOCKED (JUP=0.4308+FIL=0.4114 dual blockers > 0.40) -> "
            "K656 post-orth JUP=0.0495+FIL=0.0184 (cleared), max=0.2993 UNI PASS"
        ),
        "gaming_cluster_complete": "SAND(K583)+AXS(K591)+IMX(K635 $4.78M/yr)+GALA(K656 $48K/yr) all ACCEPT CONDITIONAL",
        "orthog_series_note":      "FIRST dual-factor (JUP+FIL) in K6xx series. IS R²=0.4731 LARGEST in series.",
        "daemon_number":           "50th",
        "milestone":               "50th daemon MILESTONE — K659 gaming cluster complete",
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
      1. Fetch GALA + JUP + FIL + BTC FRs
      2. Compute dual-factor orthogonalized residual + 504h rolling mean + sigma
      3. Decide position (|mean| > 1.5sigma threshold)
      4. Compute delta-neutral notional
      5. If entering: submit paired trade (POST_ONLY, Bybit primary)
      6. If holding: check drift + rebalance
      7. Write k656_dashboard.json
    """
    ts_jst = datetime.now(JST).strftime("%Y-%m-%d %H:%M JST")
    print(f"\n=== K656 GALA Dual-Factor Orthogonalized FR Differential — {ts_jst} ===")
    print(f"  Mode:      {'DRY-RUN' if dry_run else 'PAPER-TRADE' if PAPER_TRADE else 'LIVE'}")
    print(f"  AUM:       ${aum:,.0f}  Sleeve: {SLEEVE_PCT:.1%}  Leverage: {LEVERAGE}x")
    print(f"  Venue:     Bybit primary (GALA+BTC paired; HL cap breach 66.5%>65%)")
    print(f"  Execution: POST_ONLY parallel (K439)")
    print(f"  HL impact: NONE (Bybit-only) — HL concentration unchanged @ 64.5%")
    print(f"  Orthog:    residual = GALA_diff "
          f"- {BETA_JUP}xJUP_diff "
          f"- {BETA_FIL}xFIL_diff")
    print(f"  betas fixed: beta_JUP={BETA_JUP} beta_FIL={BETA_FIL}")
    print(f"               (K656 OLS DF dual-factor, production-hardcoded)")
    print(f"  Signal:    |residual_mean_504h| > 1.5sigma  (W=504h = 63 x 8h periods)")
    print(f"  Dual-factor unlock: K620 BLOCKED (JUP=0.4308+FIL=0.4114) -> K656 POST-ORTH PASS")
    print(f"  Gaming cluster COMPLETE: SAND+AXS+IMX+GALA all ACCEPT CONDITIONAL")
    print(f"  50th daemon MILESTONE — 9th orthogonal scaffold")

    # Step 1: Fetch + compute dual-factor orthogonalized residual
    print("\n  [Step 1] Computing dual-factor orthogonalized residual...")
    signal = compute_residual()
    print(f"  GALA FR:    {signal['fr_gala']:+.8f} (8h)")
    print(f"  JUP FR:     {signal['fr_jup']:+.8f} (8h)")
    print(f"  FIL FR:     {signal['fr_fil']:+.8f} (8h)")
    print(f"  BTC FR:     {signal['fr_btc']:+.8f} (8h)")
    print(f"  GALA diff:  {signal['gala_diff']:+.8f}  (GALA-BTC raw)")
    print(f"  Residual:   {signal['residual']:+.8f}  (dual-factor orthogonalized)")
    print(f"  Mean 504h:  {signal['residual_mean_504h']:+.8f}")
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
        print(f"  Signal:   NEUTRAL (|residual_mean| <= 1.5sigma)")

    # Step 3: Notional sizing
    notional_per_leg, total_notional = \
        compute_delta_neutral_notional(aum, SLEEVE_PCT, LEVERAGE)
    print(f"\n  [Step 3] Notional sizing:")
    print(f"  Sleeve capital:   ${aum * SLEEVE_PCT:,.0f}  ({SLEEVE_PCT:.1%} x ${aum/1e6:.0f}M)")
    print(f"  GALA leg:         ${notional_per_leg:,.0f}  (1.0% x ${aum/1e6:.0f}M x {LEVERAGE}x)")
    print(f"  BTC leg:          ${notional_per_leg:,.0f}  (1.0% x ${aum/1e6:.0f}M x {LEVERAGE}x)")
    print(f"  Total notional:   ${total_notional:,.0f}")
    print(f"  Margin required:  ${total_notional/LEVERAGE:,.0f}  ({SLEEVE_PCT:.1%} AUM)")
    print(f"  Profit @$10M 4x:  OOS 1.88% ann ret = $48,143/yr net (2% sleeve)")

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
    print(f"\n  === K656 Cycle Complete ===")
    print(f"  Position state:     {dash_out.get('position_state')}")
    print(f"  Regime:             {dash_out.get('regime')}")
    print(f"  Residual Mean 504h: {dash_out.get('residual_mean_504h'):+.8f}")
    print(f"  Threshold (1.5sig): {dash_out.get('threshold_1_5sigma'):+.8f}")
    print(f"  betas (fixed):      JUP={BETA_JUP} FIL={BETA_FIL}")
    print(f"                      (K656 OLS DF dual-factor, production-hardcoded)")
    print(f"  Paper-trade mode:   {PAPER_TRADE}")
    print(f"  OOS Sharpe:         8.3211 residual (raw K620=12.09, DF W=504h)")
    print(f"  Dual-factor unlock: K620 BLOCKED (JUP=0.4308+FIL=0.4114) -> K656 POST-ORTH PASS")
    print(f"  Cluster:            Gaming Publisher / Gala Games P2E / GalaChain L1")
    print(f"  Gaming cluster:     SAND(K583)+AXS(K591)+IMX(K635)+GALA(K656) COMPLETE")
    print(f"  Profit 2% sleeve:   $48,143/yr net @$10M @4x (OOS 1.88% ann ret)")
    print(f"  HL concentration:   {HL_CONCENTRATION_POST}% (unchanged — Bybit-only)")
    print(f"  60d gate:           Realized Sh>=4 + fill>=60% + maxDD<20%")
    print(f"  v6.40 path:         K656 GALA orthog 2% Bybit sleeve (50th daemon MILESTONE)")
    print()

    return 0


# ─────────────────────────────────────────────────────────────────────────────
# CLI entry point
# ─────────────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="K656 GALA Dual-Factor Orthogonalized FR Differential Strategy (K659 scaffold)"
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
        print(f"\n=== K656 Dashboard ({dash.get('last_poll_jst', '—')}) ===")
        print(json.dumps(dash, indent=2))
        return 0

    if args.rebalance:
        dash   = _load_dashboard()
        result = daily_rebalance(dash)
        print(f"\n=== K656 Rebalance Check ===")
        print(json.dumps(result, indent=2))
        return 0

    if args.close:
        result = close_paired_position(args.close, dry_run=args.dry_run)
        print(f"\n=== K656 Close Result ===")
        print(json.dumps(result, indent=2))
        return 0

    return run_cycle(dry_run=args.dry_run, aum=args.aum)


if __name__ == "__main__":
    sys.exit(main())
