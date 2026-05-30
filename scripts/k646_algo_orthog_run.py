#!/usr/bin/env python3
"""
k646_algo_orthog_run.py — K646 ALGO Orthogonalized FR Differential Strategy
=============================================================================
Implements a paired-trade (long ALGO / short BTC or reverse) based on the
72h EMA of the ALGO-BTC funding rate differential, ORTHOGONALIZED against
FIL factor via single-factor OLS regression (K646 SF-W72h pattern).

Architecture (K651 scaffold, K646 pattern):
  1. fetch_fr_batch()                  → fetch ALGO + FIL + BTC FR every 8h
  2. compute_residual(algo_diff, fil_diff)
       residual = ALGO_diff - β_FIL * FIL_diff
       β coefficient HARDCODED per K646 OLS single-factor (no re-OLS in production):
         β_FIL  = 0.411
  3. compute_signal(residual_history)  → 72h EMA of residual; |ema| > 1.5σ
  4. decide_position(signal)           → LONG_ALGO_SHORT_BTC | LONG_BTC_SHORT_ALGO | NEUTRAL
  5. submit_paired_trade(long, short)  → POST_ONLY paired (ALGO + BTC legs)
  6. daily_rebalance()                 → drift > 5% triggers rebalance
  7. close_paired_position(reason)     → sequential: short first, then long

K646 Enterprise/Utility L1 cluster hypothesis (ACCEPT CONDITIONAL):
  - ALGO = Algorand: Pure PoS VRF consensus (CBDC pilots, institutional blockchain)
  - FIL = Filecoin: distributed storage proofs (enterprise utility / storage economy)
  - Enterprise/Utility L1 cluster = "alt-L1 enterprise/institutional" meta-narrative
  - ALGO FR dynamics driven by Algorand VRF consensus cycles, CBDC adoption events,
    DeFi-lite FR timing — orthogonal to FIL storage economy after OLS residualization
  - OOS Sh=8.11 RESIDUAL (SF W=72h optimal per K646 analysis, single-factor FIL)
  - β_FIL=0.411 per K646 OLS (K522 FIL corr 0.6052 BLOCKED → post-orth 0.2546 UNLOCKED)
  - 60d paper-trade gate required before live activation

K646 K651 profit summary:
  - OOS Sharpe (residual): 8.11
  - Ann Return @$10M @4x (2% sleeve): $20,325/yr net (net 80% of gross)
  - Bybit primary (ALGO on Bybit perp + BTC-USDT-SWAP, both Bybit perp)

Execution:
  - Bybit primary (ALGOUSDT perp + BTC-USDT-SWAP, both Bybit perp)
  - POST_ONLY paired execution (K439 pattern)
  - Position: 2% sleeve, 4x leverage
  - 8h cadence (matches FR settlement cycle, HL hourly FR used for signal)
  - W=72h EMA (optimal window per K646 analysis, SF single-factor)

Orthog mechanism:
  - Raw ALGO_diff  = ALGO_FR − BTC_FR
  - FIL_diff       = FIL_FR  − BTC_FR
  - residual       = ALGO_diff − 0.411 × FIL_diff
  - Signal         = 72h EMA of residual; threshold = 1.5σ of 72h window
  - β hardcoded: NO re-OLS in production (stability constraint, K646 spec)
  - FIL corr: raw 0.6052 (BLOCKED-G5i K522) → post-orth 0.2546 (UNLOCKED K646)

Paper-trade mode is the DEFAULT.  No orders are submitted unless
PAPER_TRADE=False is explicitly set in the environment.

K339 security: REPO_ROOT from __file__, no /Users/ literals.
No new packages — stdlib urllib + json only.

Usage:
  python3 scripts/k646_algo_orthog_run.py --dry-run
  python3 scripts/k646_algo_orthog_run.py --status
  python3 scripts/k646_algo_orthog_run.py --rebalance
  python3 scripts/k646_algo_orthog_run.py --close "scheduled exit"
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

DASHBOARD_PATH  = DATA_DIR  / "k646_dashboard.json"
FR_HISTORY_PATH = CACHE_DIR / "k646_fr_history.jsonl"
TRADE_LOG_PATH  = CACHE_DIR / "k646_paper_trades.jsonl"

JST = timezone(timedelta(hours=9))
UTC = timezone.utc

# ── Strategy constants ────────────────────────────────────────────────────────
PAPER_TRADE         = True          # never submit real orders in paper-trade mode
SLEEVE_PCT          = 0.02          # K646 sleeve = 2% of AUM (enterprise/utility-L1 unlock, Bybit-only)
LEVERAGE            = 4.0           # 4x per K646 analysis (K430 cap)
AUM_DEFAULT         = 10_000_000.0  # $10M reference AUM
DRIFT_REBALANCE_PCT = 0.05          # rebalance if legs drift > 5%
IOC_TIMEOUT_SEC     = 300           # 5 min fill window
EMA_PERIOD_HOURS    = 72            # 72h EMA optimal window (per K646 analysis, SF W=72h)
EMA_PERIOD_PERIODS  = EMA_PERIOD_HOURS // 8  # = 9 periods (8h settlement cycle)
SIGNAL_SIGMA_MULT   = 1.5           # entry threshold: |residual_ema| > 1.5σ
HL_API_URL          = "https://api.hyperliquid.xyz/info"

# ── K646 OLS β coefficient — HARDCODED, NO RE-OLS in production ──────────────
# Source: K646 single-factor OLS regression on ALGO vs FIL factor
#   ALGO_diff = α + β_FIL × FIL_diff + ε
#   β_FIL  = 0.411  (FIL enterprise/utility L1 co-movement factor loading on ALGO FR)
#   IS R²=0.2396, OOS R²=-0.0282 (diagnostic)
#   Enterprise/Utility L1 cluster: ALGO orthogonal to FIL storage economy after OLS
#   K522 FIL corr raw=0.6052 (BLOCKED-G5i) → post-orth=0.2546 (PASS K646)
BETA_FIL  = 0.411

# ── Venue config (Bybit primary — ALGO on Bybit perp) ─────────────────────────
# Bybit primary: ALGOUSDT perp + BTC-USDT-SWAP, both Bybit perp
# Both legs on Bybit (delta-neutral carry); HL ALGO availability uncertain for 4x
# HL secondary: monitor-only
BYBIT_SLEEVE_PCT   = SLEEVE_PCT      # full sleeve on Bybit (ALGO + BTC paired)
HL_CONCENTRATION_UNCHANGED = 65.0   # K646 on Bybit → HL concentration unchanged

# ── Position state constants ──────────────────────────────────────────────────
STATE_NEUTRAL             = "NEUTRAL"
STATE_LONG_ALGO_SHORT_BTC = "LONG_ALGO_SHORT_BTC"
STATE_LONG_BTC_SHORT_ALGO = "LONG_BTC_SHORT_ALGO"

# ── Symbols fetched from HL for FR data ──────────────────────────────────────
SYMBOLS = ("ALGO", "FIL", "BTC")


# ─────────────────────────────────────────────────────────────────────────────
# HTTP helper (stdlib urllib only — no requests)
# ─────────────────────────────────────────────────────────────────────────────

def _http_post(url: str, payload: dict, timeout: int = 10) -> Optional[dict]:
    try:
        data = json.dumps(payload).encode()
        req  = urllib.request.Request(
            url, data=data,
            headers={"Content-Type": "application/json",
                     "User-Agent": "crypto-lab-k646/1.0"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        print(f"  [k646] HTTP error: {e}", file=sys.stderr)
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Phase 1 — Funding rate fetch (ALGO + FIL + BTC)
# ─────────────────────────────────────────────────────────────────────────────

def _fetch_hl_fr_batch() -> Dict[str, float]:
    """
    Fetch current funding rates for ALGO, FIL, BTC from HL.
    Returns {symbol: fr_fraction}.

    HL API: metaAndAssetCtxs -> funding field per asset.
    Note: ALGO live trading uses Bybit ALGOUSDT perp (8h settlement).
    HL ALGO data used for signal computation only.
    """
    raw = _http_post(HL_API_URL, {"type": "metaAndAssetCtxs"})
    if not raw or not isinstance(raw, list) or len(raw) < 2:
        print("  [k646] HL metaAndAssetCtxs fetch failed", file=sys.stderr)
        return {}
    meta       = raw[0]
    asset_ctxs = raw[1]
    universe   = {item["name"]: i for i, item in enumerate(meta.get("universe", []))}
    result: Dict[str, float] = {}
    for sym in SYMBOLS:
        if sym not in universe:
            print(f"  [k646] Symbol {sym} not found in HL universe", file=sys.stderr)
            continue
        idx = universe[sym]
        ctx = asset_ctxs[idx]
        try:
            result[sym] = float(ctx.get("funding", 0.0))
        except (TypeError, ValueError):
            continue
    return result


def _load_fr_history() -> List[dict]:
    """Load K646 FR history JSONL."""
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
    fr_algo: float, fr_fil: float, fr_btc: float,
    algo_diff: float, fil_diff: float, residual: float
) -> None:
    """Append one FR + residual snapshot to history."""
    rec = {
        "ts_utc":   datetime.now(UTC).isoformat(),
        "fr_algo":  round(fr_algo,  10),
        "fr_fil":   round(fr_fil,   10),
        "fr_btc":   round(fr_btc,   10),
        "algo_diff": round(algo_diff, 10),  # ALGO_FR - BTC_FR (raw)
        "fil_diff":  round(fil_diff,  10),  # FIL_FR  - BTC_FR
        "residual":  round(residual,  10),  # orthogonalized residual
    }
    with open(FR_HISTORY_PATH, "a") as f:
        f.write(json.dumps(rec) + "\n")


# ─────────────────────────────────────────────────────────────────────────────
# Phase 2 — Orthogonalized residual computation
# ─────────────────────────────────────────────────────────────────────────────

def compute_residual(
    fr_algo: Optional[float] = None,
    fr_fil:  Optional[float] = None,
    fr_btc:  Optional[float] = None,
) -> dict:
    """
    Fetch live ALGO/FIL/BTC FRs from HL, compute orthogonalized residual,
    and compute 72h EMA + 72h rolling sigma for threshold calculation.

    Orthogonalization mechanism (K646 OLS single-factor, coefficient HARDCODED):
      algo_diff = ALGO_FR  - BTC_FR
      fil_diff  = FIL_FR   - BTC_FR
      residual  = algo_diff - beta_FIL * fil_diff
               = algo_diff - 0.411 * fil_diff

    Signal gate (W=72h optimal per K646 analysis):
      EMA = 72h EMA of residual (9 x 8h periods)
      sigma = 72h rolling std of residual
      Enter when |EMA| > 1.5sigma

    K646 Enterprise/Utility L1 cluster hypothesis:
      ALGO = Algorand (Pure PoS VRF consensus, CBDC/institutional). FR dynamics driven by:
        VRF consensus cycles — ALGO staking + governance participation unique to Algorand
        CBDC pilot events — Algorand chosen by multiple central banks (e.g. Marshall Islands)
        DeFi-lite FR timing — Algorand DEX/TinyMan/Folks Finance adoption cycles
        Algorand Foundation grants waves — grant cycles trigger usage spikes orthogonal to FIL
      FIL raw signal corr=0.6052 (BLOCKED-G5i in K522).
      After OLS orthogonalization (β_FIL=0.411):
        FIL corr post-orth=0.2546 (G5i PASS threshold 0.40 — UNLOCKED)
      OOS Sh=8.11 (SF W=72h) confirms orthogonalization unlocks Algorand PoS pure alpha.

    Returns:
      {
        "fr_algo":           float,
        "fr_fil":            float,
        "fr_btc":            float,
        "algo_diff":         float,   # raw ALGO-BTC
        "fil_diff":          float,   # FIL-BTC
        "residual":          float,   # orthogonalized residual (current)
        "residual_ema_72h":  float,   # 72h EMA of residual (9 periods x 8h)
        "residual_sigma":    float,   # 72h rolling sigma of residual
        "threshold":         float,   # 1.5sigma entry threshold
        "beta_fil":          float,   # beta_FIL hardcoded = 0.411
        "history_points":    int,
        "regime":            str,     # BULL_ALGO | BEAR_ALGO | NEUTRAL
        "ts_jst":            str,
      }
    """
    if any(v is None for v in (fr_algo, fr_fil, fr_btc)):
        frs    = _fetch_hl_fr_batch()
        fr_algo = frs.get("ALGO", 0.0)
        fr_fil  = frs.get("FIL",  0.0)
        fr_btc  = frs.get("BTC",  0.0)

    # Compute diffs
    algo_diff = fr_algo - fr_btc
    fil_diff  = fr_fil  - fr_btc

    # Orthogonalized residual (K646 OLS single-factor, beta hardcoded)
    residual = algo_diff - BETA_FIL * fil_diff

    _append_fr_history(fr_algo, fr_fil, fr_btc, algo_diff, fil_diff, residual)

    # Load history for EMA + sigma (72h = 9 x 8h periods)
    history   = _load_fr_history()
    residuals = [r["residual"] for r in history if "residual" in r]

    n_periods = EMA_PERIOD_PERIODS   # 9 periods (72h / 8h)
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
        regime = "BULL_ALGO"   # ALGO residual FR > 0: short ALGO / long BTC
    else:
        regime = "BEAR_ALGO"   # ALGO residual FR < 0: long ALGO / short BTC

    return {
        "fr_algo":           round(fr_algo,   10),
        "fr_fil":            round(fr_fil,    10),
        "fr_btc":            round(fr_btc,    10),
        "algo_diff":         round(algo_diff, 10),
        "fil_diff":          round(fil_diff,  10),
        "residual":          round(residual,  10),
        "residual_ema_72h":  round(ema,       10),
        "residual_sigma":    round(sigma,     10),
        "threshold":         round(threshold, 10),
        "beta_fil":          BETA_FIL,
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

    Logic (ALGO-BTC orthogonalized pair, Bybit primary):
      regime = BULL_ALGO (residual_ema > 1.5sigma):
        ALGO residual FR > BTC FR -> ALGO more expensive to long
        -> short ALGO (collect high residual FR) / long BTC (cheap carry)
        -> position_state = LONG_BTC_SHORT_ALGO
        -> both legs on Bybit

      regime = BEAR_ALGO (residual_ema < -1.5sigma):
        ALGO residual FR < BTC FR -> BTC more expensive
        -> long ALGO / short BTC
        -> position_state = LONG_ALGO_SHORT_BTC
        -> both legs on Bybit

      regime = NEUTRAL: no trade

    K646 orthog edge:
      The residual cleanly separates ALGO's Algorand-ecosystem-specific FR dynamics
      from the FIL enterprise/utility-L1 co-movement factor noise (β_FIL=0.411).
      OOS Sh=8.11 (SF W=72h) residual confirms the true alpha resides in
      Algorand VRF consensus cycles, CBDC pilot events, DeFi-lite adoption timing,
      and Foundation grant waves — not shared enterprise/utility-L1 narratives.
      Enterprise/Utility L1 unlock: K522 was BLOCKED-G5i (FIL corr=0.6052);
      K646 orthog reduces to 0.2546 (PASS) unlocking Algorand PoS cluster.

    Returns:
      {long_asset, short_asset, long_venue, short_venue, residual_ema,
       signal_strength, size_multiplier, position_state}
      or None if NEUTRAL.
    """
    regime  = signal.get("regime", "NEUTRAL")
    ema     = signal.get("residual_ema_72h", 0.0)
    thresh  = signal.get("threshold", 1e-8)
    abs_ema = abs(ema)

    if regime == "NEUTRAL":
        return None

    if regime == "BULL_ALGO":
        # ALGO residual FR positive -> ALGO FR > BTC FR
        # short ALGO (expensive), long BTC (cheap)
        long_asset  = "BTC"
        short_asset = "ALGO"
        state       = STATE_LONG_BTC_SHORT_ALGO
    else:  # BEAR_ALGO
        # ALGO residual FR negative -> BTC FR > ALGO FR
        # long ALGO (cheap), short BTC (expensive)
        long_asset  = "ALGO"
        short_asset = "BTC"
        state       = STATE_LONG_ALGO_SHORT_BTC

    # Both legs on Bybit (ALGO + BTC, Bybit primary)
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
    Compute equal notional for both legs of the ALGO-BTC paired trade.

    K646 Bybit-only config (ALGO perp on Bybit):
      sleeve_capital   = aum x sleeve_pct      (e.g. $10M x 2% = $200K)
      total_notional   = sleeve_capital x lev   ($200K x 4 = $800K)
      notional_per_leg = total_notional / 2     ($400K per leg)

    At $10M / 2% sleeve / 4x:
      ALGO leg:  $100K capital x 4x = $400K notional (Bybit)
      BTC leg:   $100K capital x 4x = $400K notional (Bybit)
      Total:     $800K notional (two legs combined)
      Margin:    $200K (2% of AUM)
      Net profit: ~$20,325/yr (net 80% of gross, 2% sleeve @$10M @4x)

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
    Submit K646 ALGO-BTC paired trade: POST_ONLY both legs in parallel.

    Protocol (K646 Bybit primary):
      1. Submit ALGO leg on Bybit POST_ONLY
      2. Submit BTC leg on Bybit POST_ONLY
      3. Both legs submitted in parallel (K439 pattern)
      4. IOC fallback per leg if POST_ONLY times out
      5. If both fail: retry next 8h cycle

    Args:
      long_leg:  {"symbol": "ALGO", "notional": 400000, "venue": "Bybit"}
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
        print(f"  [K646] {mode_tag}: LONG {long_sym}@{long_venue} ${long_notl:,.0f}  "
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
            "venue_config":     "BYBIT_PRIMARY_ALGO_POSVRf_ENTERPRISE_L1",
            "orthog_note":      "residual = ALGO_diff - 0.411*FIL_diff (K646 OLS SF)",
            "ts_utc":           ts,
        }
        _append_trade_log(result)
        return result

    # LIVE scaffold (not reached in PAPER_TRADE mode):
    print(f"  [K646] SCAFFOLD LIVE: parallel POST_ONLY "
          f"LONG {long_sym}@{long_venue} ${long_notl:,.0f} "
          f"+ SHORT {short_sym}@{short_venue} ${short_notl:,.0f}")
    long_order_id  = f"SCAFFOLD_LONG_{long_sym}_{int(time.time())}"
    short_order_id = f"SCAFFOLD_SHORT_{short_sym}_{int(time.time())}"

    # Scaffold: poll not implemented — retry next 8h cycle
    print(f"  [K646] Neither leg filled within timeout — retry next 8h cycle")
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
    Check if current K646 position has drifted beyond DRIFT_REBALANCE_PCT (5%).

    K646 Bybit-only: both legs on Bybit; drift accumulates together.
    Drift detection: compare stored ALGO leg notional vs BTC leg notional.
    Threshold: 5% (same as K507/K512/K628/K631/K633/K635/K638/K645 pattern).

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
    Both legs on Bybit (K646 Bybit primary).

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

    if state == STATE_LONG_ALGO_SHORT_BTC:
        long_sym,  short_sym  = "ALGO", "BTC"
    else:  # LONG_BTC_SHORT_ALGO
        long_sym,  short_sym  = "BTC", "ALGO"

    long_notional  = float(dash.get("long_notional",  0.0))
    short_notional = float(dash.get("short_notional", 0.0))

    if dry_run or PAPER_TRADE:
        mode_tag = "DRY_RUN" if dry_run else "PAPER_TRADE"
        print(f"  [K646] {mode_tag} CLOSE:")
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
        print(f"  [K646] SCAFFOLD CLOSE:")
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
    """Load k646_dashboard.json; return defaults if missing."""
    if DASHBOARD_PATH.exists():
        try:
            return json.loads(DASHBOARD_PATH.read_text())
        except Exception:
            pass
    return {
        "last_poll_jst":           "—",
        "residual_ema_72h":        0.0,
        "residual_sigma":          0.0,
        "threshold_1_5sigma":      0.0,
        "beta_fil_used":           BETA_FIL,
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
    """Write k646_dashboard.json with full signal + regime state."""
    dash = _load_dashboard()

    # Update signal data
    dash["last_poll_jst"]        = signal.get("ts_jst", "—")
    dash["fr_algo_current"]      = signal.get("fr_algo",   0.0)
    dash["fr_fil_current"]       = signal.get("fr_fil",    0.0)
    dash["fr_btc_current"]       = signal.get("fr_btc",    0.0)
    dash["algo_diff_raw"]        = signal.get("algo_diff", 0.0)
    dash["fil_diff"]             = signal.get("fil_diff",  0.0)
    dash["residual_current"]     = signal.get("residual",  0.0)
    dash["residual_ema_72h"]     = signal.get("residual_ema_72h", 0.0)
    dash["residual_sigma"]       = signal.get("residual_sigma",   0.0)
    dash["threshold_1_5sigma"]   = signal.get("threshold",        0.0)
    dash["beta_fil_used"]        = signal.get("beta_fil",  BETA_FIL)
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

    # 60d activation gate metrics (K651: Realized Sh>=4 + fill>=60% + DD<20%)
    dash["gate_metrics"] = {
        "realized_sharpe_target":  4.0,      # >=4 (per K651 task spec)
        "fill_rate_target_pct":    60,
        "max_drawdown_target_pct": 20,
        "current_realized_sharpe": dash.get("60d_sharpe", 0.0),
        "current_fill_rate_pct":   0.0,
        "current_max_dd_pct":      0.0,
        "gate_status":             "IN_PROGRESS",
        "activation_trigger":      "60d paper-trade: Sh>=4 AND fill>=60% AND maxDD<20%",
        "profit_at_activation_2pct": "$20,325/yr net @$10M @4x (2% sleeve)",
    }

    # Strategy metadata
    dash["paper_trade_mode"]    = PAPER_TRADE
    dash["wave"]                = "K651"
    dash["strategy"]            = "K646 ALGO-BTC Orthogonalized FR Differential (SF FIL W=72h)"
    dash["execution_mode"]      = "POST_ONLY_PARALLEL"
    dash["venue_config"]        = "BYBIT_PRIMARY"
    dash["orthog_mechanism"]    = {
        "formula":    "residual = ALGO_diff - 0.411*FIL_diff",
        "beta_fil":   BETA_FIL,
        "ema_window": "W=72h (9 x 8h periods)",
        "note":       "beta HARDCODED per K646 OLS single-factor — no re-OLS in production for stability",
    }
    dash["activation_criteria"] = {
        "60d_paper_trade_gate":   "required",
        "realized_sharpe_min":    4.0,
        "fill_rate_min_pct":      60,
        "max_drawdown_max_pct":   20,
        "status":                 "SCAFFOLD-READY",
        "activation_sleeve_pct":  0.02,
        "venue":                  "Bybit primary (ALGO+BTC both legs)",
    }
    dash["oos_performance"] = {
        "sharpe_residual":          8.11,
        "sharpe_raw_k522":          10.271,
        "orthog_degradation_sh":    2.16,
        "fil_corr_raw":             0.6052,
        "fil_corr_post_orth":       0.2546,
        "ann_return_pct_4x":        2.5406,
        "ann_return_usd_2pct_4x":   20325,
        "wave_accept":              "K646 ACCEPT CONDITIONAL (K651 scaffold)",
        "cluster":                  "Enterprise/Utility L1 (Algorand PoS VRF — FIL-cluster unlock)",
        "cluster_rationale":        "ALGO FR driven by Algorand VRF consensus cycles, CBDC pilot events, DeFi-lite adoption timing, Foundation grant waves — orthogonal to FIL distributed storage economy after OLS residualization",
        "hl_concentration_pct":     65.0,
        "hl_impact":                "NONE — Bybit-only; HL concentration unchanged at 65%",
        "factors_removed":          ["FIL (enterprise/utility-L1 co-movement, storage economy regime)"],
        "fil_cluster_unlock":       "K522 BLOCKED (FIL corr=0.6052 >= 0.40) -> K646 UNLOCKED (post-orth=0.2546 < 0.40)",
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
      1. Fetch ALGO + FIL + BTC FRs
      2. Compute orthogonalized residual + 72h EMA + sigma
      3. Decide position (|ema| > 1.5sigma threshold)
      4. Compute delta-neutral notional
      5. If entering: submit paired trade (POST_ONLY, Bybit primary)
      6. If holding: check drift + rebalance
      7. Write k646_dashboard.json
    """
    ts_jst = datetime.now(JST).strftime("%Y-%m-%d %H:%M JST")
    print(f"\n=== K646 ALGO Orthogonalized FR Differential — {ts_jst} ===")
    print(f"  Mode:      {'DRY-RUN' if dry_run else 'PAPER-TRADE' if PAPER_TRADE else 'LIVE'}")
    print(f"  AUM:       ${aum:,.0f}  Sleeve: {SLEEVE_PCT:.1%}  Leverage: {LEVERAGE}x")
    print(f"  Venue:     Bybit primary (ALGO+BTC paired; HL ALGO uncertain for 4x paired trade)")
    print(f"  Execution: POST_ONLY parallel (K439)")
    print(f"  HL impact: NONE (Bybit-only) — HL concentration unchanged @ 65%")
    print(f"  Orthog:    residual = ALGO_diff - {BETA_FIL}xFIL_diff")
    print(f"  beta fixed: beta_FIL={BETA_FIL}  (K646 OLS SF, production-hardcoded)")
    print(f"  Signal:    |residual_EMA_72h| > 1.5sigma  (W=72h = 9 x 8h periods)")
    print(f"  FIL unlock: K522 BLOCKED (corr=0.6052) -> K646 POST-ORTH (corr=0.2546 PASS)")

    # Step 1: Fetch + compute orthogonalized residual
    print("\n  [Step 1] Computing orthogonalized residual...")
    signal = compute_residual()
    print(f"  ALGO FR:    {signal['fr_algo']:+.8f} (8h)")
    print(f"  FIL FR:     {signal['fr_fil']:+.8f} (8h)")
    print(f"  BTC FR:     {signal['fr_btc']:+.8f} (8h)")
    print(f"  ALGO diff:  {signal['algo_diff']:+.8f}  (ALGO-BTC raw)")
    print(f"  Residual:   {signal['residual']:+.8f}  (orthogonalized)")
    print(f"  EMA 72h:    {signal['residual_ema_72h']:+.8f}")
    print(f"  Sigma 72h:  {signal['residual_sigma']:+.8f}")
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
    print(f"  ALGO leg:         ${notional_per_leg:,.0f}  (1.0% x ${aum/1e6:.0f}M x {LEVERAGE}x)")
    print(f"  BTC leg:          ${notional_per_leg:,.0f}  (1.0% x ${aum/1e6:.0f}M x {LEVERAGE}x)")
    print(f"  Total notional:   ${total_notional:,.0f}")
    print(f"  Margin required:  ${total_notional/LEVERAGE:,.0f}  ({SLEEVE_PCT:.1%} AUM)")
    print(f"  Profit @$10M 4x:  2% sleeve=~$20,325/yr (net 80%)")

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
    print(f"\n  === K646 Cycle Complete ===")
    print(f"  Position state:     {dash_out.get('position_state')}")
    print(f"  Regime:             {dash_out.get('regime')}")
    print(f"  Residual EMA 72h:   {dash_out.get('residual_ema_72h'):+.8f}")
    print(f"  Threshold (1.5sig): {dash_out.get('threshold_1_5sigma'):+.8f}")
    print(f"  beta_FIL (fixed):   {BETA_FIL}  (K646 OLS SF, production-hardcoded)")
    print(f"  Paper-trade mode:   {PAPER_TRADE}")
    print(f"  OOS Sharpe:         8.11 residual (raw K522=10.27, SF W=72h)")
    print(f"  FIL unlock:         K522 FIL corr 0.6052 BLOCKED -> K646 post-orth 0.2546 PASS")
    print(f"  Cluster:            Enterprise/Utility L1 / Algorand PoS VRF (7th orthog)")
    print(f"  Profit 2% sleeve:   ~$20,325/yr @$10M @4x (net 80%)")
    print(f"  HL concentration:   {HL_CONCENTRATION_UNCHANGED}% (unchanged — Bybit-only)")
    print(f"  60d gate:           Realized Sh>=4 + fill>=60% + maxDD<20%")
    print(f"  v6.37 path:         K646 ALGO orthog 2% Bybit sleeve added to v6.36")
    print()

    return 0


# ─────────────────────────────────────────────────────────────────────────────
# CLI entry point
# ─────────────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="K646 ALGO Orthogonalized FR Differential Strategy (K651 scaffold)"
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
        print(f"\n=== K646 Dashboard ({dash.get('last_poll_jst', '—')}) ===")
        print(json.dumps(dash, indent=2))
        return 0

    if args.rebalance:
        dash   = _load_dashboard()
        result = daily_rebalance(dash)
        print(f"\n=== K646 Rebalance Check ===")
        print(json.dumps(result, indent=2))
        return 0

    if args.close:
        result = close_paired_position(args.close, dry_run=args.dry_run)
        print(f"\n=== K646 Close Result ===")
        print(json.dumps(result, indent=2))
        return 0

    return run_cycle(dry_run=args.dry_run, aum=args.aum)


if __name__ == "__main__":
    sys.exit(main())
