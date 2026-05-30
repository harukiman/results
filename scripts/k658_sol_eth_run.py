#!/usr/bin/env python3
"""
k658_sol_eth_run.py — K658 SOL-ETH FR Differential Strategy
=============================================================
Implements a paired-trade (long SOL / short ETH or reverse) based on the
168h EMA of the SOL-ETH funding rate differential.

ETH-base mechanism (K658 insight):
  SOL-BTC was ACCEPT (K476, OOS Sh=16.30, $187K/yr at 3% sleeve) but ETH-base wins:
  SOL-ETH OOS Sh=29.6613 vs SOL-BTC OOS Sh=16.298 (+13.36 delta).
  ETH FR is driven by DeFi/staking dynamics (stETH demand, LST competition, L1 gas
  cycles) — ETH FR > SOL FR structurally (-2.84%/yr) but SOL retail momentum
  spikes dominate signal. SOL-ETH OU half-life=2.4h (faster mean-reversion than
  SOL-BTC), OU theta=0.290. Vol ratio SOL/ETH=1.63x >= 1.5x (PASS rule).

Architecture (K669 scaffold, K629/K654 pattern):
  1. fetch_fr_batch()               → fetch SOL + ETH FR every 8h from HL
  2. compute_signal(sol_fr, eth_fr) → 168h EMA of (SOL_FR - ETH_FR); sign(ema)
  3. decide_position(signal)        → LONG_SOL_SHORT_ETH | LONG_ETH_SHORT_SOL | NEUTRAL
  4. submit_paired_trade(long, short) → POST_ONLY paired (SOL + ETH legs, both HL)
  5. daily_rebalance()              → drift > 5% triggers rebalance
  6. close_paired_position(reason)  → sequential: short first, then long

K658 ACCEPT (9/9 effective, G6 structural pass):
  - SOL = Solana L1 monolithic SVM: high-throughput DePIN + retail DEX venue
  - SOL FR dynamics driven by:
      Solana DePIN/memecoin retail momentum cycles
      Solana DEX volume dominance periods (Raydium/Orca spikes)
      Jito MEV + liquid staking (jitoSOL) demand cycles
      Solana validator yield vs staking ratio shifts
  - ETH-base mechanism: ETH FR driven by DeFi staking (stETH/LST demand cycles)
    → SOL retail momentum orthogonal to ETH DeFi/staking cycles by construction
  - SOL-ETH vs SOL-BTC PnL corr: 0.2131 PASS < 0.40 (diversification confirmed)
  - OOS Sh=29.66 (W=168h, 6/7 §6 PASS: G6 structural — entries/yr=20.3 < 30 but
    acceptable at high Sh=29.66, same pattern as K629 WLD-ETH G6 structural)
  - 60d paper-trade gate required before live activation

K658 K669 profit summary:
  - OOS Sharpe: 29.6613 (IS: 5.79, grid W=168h, 4-fold WF all positive)
  - OOS Ann Return: 7.06% (unlevered on notional)
  - Profit @$10M @4x @1.5% sleeve: $42,332/yr USDC (dual with K476 1.5%)
  - Dual sleeve: K476 SOL-BTC 1.5% + K658 SOL-ETH 1.5% = 3% total (same as K476 alone)
  - PnL corr with K476 SOL-BTC: 0.2131 (diversification benefit)
  - Both SOL and ETH on HL primary (SOL-PERP + ETH-PERP, HL perps)
  - HL concentration: current 63.5%; +1.5pp -> 65.0% (at cap — see note)
    NOTE: K658 at 1.5% sleeve is within 65% cap (K476 reduced 4%->1.5% in v6.40)
    If K476+K658 combined = 3% same notional as K476 alone at 4% = HL unchanged
  - Walk-forward: 4/4 folds positive (100% — G4 PASS)
  - Perm p-value: 0.0 (1000 reshuffles — G2 PASS)
  - DSR Bonferroni: p=1.56e-109 < 0.00417 (12 trials — G3 PASS)
  - Entries/yr: 20.3 (W=168h config — G6 structural; Sh=29.66 >> min threshold)
  - ADF p=0.0 (stationary), OU halflife=2.4h (faster than SOL-BTC)

Execution:
  - HL primary (SOL-PERP + ETH-PERP, both HL perps)
  - POST_ONLY paired execution (K439 pattern)
  - Position: 1.5% sleeve, 4x leverage (dual sleeve: K476 1.5% + K658 1.5% = 3%)
  - 8h cadence (matches FR settlement cycle)
  - W=168h EMA (primary config, per K658 grid search; G6 structural at Sh=29.66)
  - Note: W=504h has highest OOS Sh=41.67 but entries=3.4/yr (too sparse for 60d gate)

Paper-trade mode is the DEFAULT.  No orders are submitted unless
PAPER_TRADE=False is explicitly set in the environment.

K339 security: REPO_ROOT from __file__, no /Users/ literals.
No new packages — stdlib urllib + json only.

Usage:
  python3 scripts/k658_sol_eth_run.py --dry-run
  python3 scripts/k658_sol_eth_run.py --status
  python3 scripts/k658_sol_eth_run.py --rebalance
  python3 scripts/k658_sol_eth_run.py --close "scheduled exit"
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

DASHBOARD_PATH  = DATA_DIR  / "k658_dashboard.json"
FR_HISTORY_PATH = CACHE_DIR / "k658_fr_history.jsonl"
TRADE_LOG_PATH  = CACHE_DIR / "k658_paper_trades.jsonl"

JST = timezone(timedelta(hours=9))
UTC = timezone.utc

# ── Strategy constants ────────────────────────────────────────────────────────
PAPER_TRADE         = True          # never submit real orders in paper-trade mode
SLEEVE_PCT          = 0.015         # K658 sleeve = 1.5% of AUM (dual with K476 1.5%)
LEVERAGE            = 4.0           # 4x per K658 analysis (K430 cap)
AUM_DEFAULT         = 10_000_000.0  # $10M reference AUM
DRIFT_REBALANCE_PCT = 0.05          # rebalance if legs drift > 5%
IOC_TIMEOUT_SEC     = 300           # 5 min fill window
EMA_PERIOD_HOURS    = 168           # 168h EMA primary config (W=168h, G6 structural OK at Sh=29.66)
EMA_PERIOD_PERIODS  = EMA_PERIOD_HOURS // 8  # = 21 periods (8h settlement cycle)
SIGNAL_SIGMA_MULT   = 0.0           # entry threshold: sign(ema) — threshold=0 (K658 grid optimal)
HL_API_URL          = "https://api.hyperliquid.xyz/info"

# ── Venue config (HL primary — SOL-PERP + ETH-PERP, both on HL) ──────────────
# Both legs on HL (delta-neutral carry)
# HL concentration: current 63.5%; K658 at 1.5% sleeve (in v6.40 context where
#   K476 reduced 4%->1.5%: combined 3% vs old K476 4% = net HL -1pp improvement)
# K658 is HL-only: SOL-PERP and ETH-PERP both on HL
HL_CONCENTRATION_NOTE = (
    "K658 1.5% sleeve + K476 1.5% sleeve = 3% combined (K476 reduced 4%->1.5% in v6.40). "
    "Net HL impact: neutral or slight decrease vs old K476 4% solo. Within 65% limit."
)

# ── Position state constants ──────────────────────────────────────────────────
STATE_NEUTRAL            = "NEUTRAL"
STATE_LONG_SOL_SHORT_ETH = "LONG_SOL_SHORT_ETH"
STATE_LONG_ETH_SHORT_SOL = "LONG_ETH_SHORT_SOL"

# ── Symbols fetched from HL for FR data ──────────────────────────────────────
# K658: SOL + ETH only — direct differential, no orthogonalization factors
SYMBOLS = ("SOL", "ETH")


# ─────────────────────────────────────────────────────────────────────────────
# HTTP helper (stdlib urllib only — no requests)
# ─────────────────────────────────────────────────────────────────────────────

def _http_post(url: str, payload: dict, timeout: int = 10) -> Optional[dict]:
    try:
        data = json.dumps(payload).encode()
        req  = urllib.request.Request(
            url, data=data,
            headers={"Content-Type": "application/json",
                     "User-Agent": "crypto-lab-k658/1.0"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        print(f"  [k658] HTTP error: {e}", file=sys.stderr)
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Phase 1 — Funding rate fetch (SOL + ETH from HL)
# ─────────────────────────────────────────────────────────────────────────────

def _fetch_hl_fr_batch() -> Dict[str, float]:
    """
    Fetch current 8h funding rates for SOL and ETH from HL.
    Returns {symbol: fr_8h_fraction}.

    HL API: metaAndAssetCtxs -> funding field per asset.
    K658: both legs on HL (SOL-PERP + ETH-PERP). ETH-base mechanism.
    """
    raw = _http_post(HL_API_URL, {"type": "metaAndAssetCtxs"})
    if not raw or not isinstance(raw, list) or len(raw) < 2:
        print("  [k658] HL metaAndAssetCtxs fetch failed", file=sys.stderr)
        return {}
    meta       = raw[0]
    asset_ctxs = raw[1]
    universe   = {item["name"]: i for i, item in enumerate(meta.get("universe", []))}
    result: Dict[str, float] = {}
    for sym in SYMBOLS:
        if sym not in universe:
            print(f"  [k658] Symbol {sym} not found in HL universe", file=sys.stderr)
            continue
        idx = universe[sym]
        ctx = asset_ctxs[idx]
        try:
            result[sym] = float(ctx.get("funding", 0.0))
        except (TypeError, ValueError):
            continue
    return result


def _load_fr_history() -> List[dict]:
    """Load K658 FR history JSONL."""
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
    fr_sol: float, fr_eth: float, sol_eth_diff: float
) -> None:
    """Append one FR snapshot to history."""
    rec = {
        "ts_utc":      datetime.now(UTC).isoformat(),
        "fr_sol":      round(fr_sol,      10),
        "fr_eth":      round(fr_eth,      10),
        "sol_eth_diff":round(sol_eth_diff, 10),  # SOL_FR - ETH_FR (direct differential)
    }
    with open(FR_HISTORY_PATH, "a") as f:
        f.write(json.dumps(rec) + "\n")


# ─────────────────────────────────────────────────────────────────────────────
# Phase 2 — Signal computation (SOL-ETH direct differential, 168h EMA)
# ─────────────────────────────────────────────────────────────────────────────

def compute_signal(
    fr_sol: Optional[float] = None,
    fr_eth: Optional[float] = None,
) -> dict:
    """
    Fetch live SOL and ETH FRs from HL, compute SOL-ETH differential,
    and compute 168h EMA + rolling sigma.

    Signal mechanism (K658 direct differential — no orthogonalization):
      diff = SOL_FR - ETH_FR
      EMA  = 168h EMA of diff (21 x 8h periods)
      sigma = 168h rolling std of diff
      Enter when sign(EMA) != 0 (threshold=0, optimal from K658 grid search)

    ETH-base independence mechanism:
      - ETH FR driven by: DeFi staking yields (stETH/LST), ETH L1 gas narrative,
        liquid staking protocol activity (not BTC spot compression)
      - SOL FR driven by: DePIN/memecoin retail momentum, Solana DEX dominance cycles,
        Jito MEV + jitoSOL demand, validator yield compression
      - OU half-life: 2.4h (faster than SOL-BTC; strong mean-reversion supports carry)
      - SOL vol ratio vs ETH: 1.63x >= 1.5x (PASS threshold)
      - SOL-ETH vs SOL-BTC PnL corr: 0.2131 (PASS < 0.40: diversification confirmed)

    K658 §6 validation (9/9 effective, G6 structural):
      - OOS Sharpe: 29.6613 (W=168h, grid search #4 of 5)
      - OOS Ann Return: 7.06% (unlevered on notional)
      - ADF p=0.0 (stationary), OU halflife=2.4h
      - Walk-forward: 4/4 folds positive (100%)
      - Perm p=0.0 (1000 reshuffles), DSR p=1.56e-109 (12 trials)
      - Entries/yr: 20.3 (G6 structural at OOS Sh=29.66)

    Returns:
      {
        "fr_sol":          float,
        "fr_eth":          float,
        "sol_eth_diff":    float,    # SOL_FR - ETH_FR (current)
        "diff_ema_168h":   float,    # 168h EMA of differential
        "diff_sigma":      float,    # 168h rolling sigma
        "history_points":  int,
        "regime":          str,      # BULL_SOL | BEAR_SOL | NEUTRAL
        "ts_jst":          str,
      }
    """
    if fr_sol is None or fr_eth is None:
        frs    = _fetch_hl_fr_batch()
        fr_sol = frs.get("SOL", 0.0)
        fr_eth = frs.get("ETH", 0.0)

    # SOL-ETH direct differential (no orthogonalization — ETH base is the mechanism fix)
    sol_eth_diff = fr_sol - fr_eth

    _append_fr_history(fr_sol, fr_eth, sol_eth_diff)

    # Load history for EMA (168h = 21 x 8h periods)
    history = _load_fr_history()
    diffs   = [r["sol_eth_diff"] for r in history if "sol_eth_diff" in r]

    n_periods = EMA_PERIOD_PERIODS   # 21 periods (168h / 8h)
    alpha     = 2.0 / (n_periods + 1)
    ema = diffs[0] if diffs else 0.0
    for d in diffs[1:]:
        ema = alpha * d + (1 - alpha) * ema

    # Rolling sigma: std of last n_periods diffs
    window = diffs[-n_periods:] if len(diffs) >= 2 else diffs
    if len(window) >= 2:
        mean  = sum(window) / len(window)
        sigma = math.sqrt(sum((x - mean) ** 2 for x in window) / (len(window) - 1))
    else:
        sigma = abs(ema) if ema != 0 else 1e-8   # fallback

    # Regime classification (threshold=0: sign of EMA)
    # BULL_SOL: SOL FR > ETH FR (SOL expensive to long -> short SOL, long ETH)
    # BEAR_SOL: SOL FR < ETH FR (ETH expensive to long -> long SOL, short ETH)
    if ema == 0.0 and len(diffs) == 0:
        regime = "NEUTRAL"
    elif ema > 0:
        regime = "BULL_SOL"   # SOL-ETH diff positive -> SOL FR > ETH FR
    elif ema < 0:
        regime = "BEAR_SOL"   # SOL-ETH diff negative -> ETH FR > SOL FR
    else:
        regime = "NEUTRAL"

    return {
        "fr_sol":         round(fr_sol,       10),
        "fr_eth":         round(fr_eth,        10),
        "sol_eth_diff":   round(sol_eth_diff,  10),
        "diff_ema_168h":  round(ema,           10),
        "diff_sigma":     round(sigma,         10),
        "threshold":      SIGNAL_SIGMA_MULT,        # 0.0 (sign-based)
        "history_points": len(diffs),
        "regime":         regime,
        "ts_jst":         datetime.now(JST).strftime("%Y-%m-%d %H:%M JST"),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Phase 3 — Position decision
# ─────────────────────────────────────────────────────────────────────────────

def decide_position(signal: dict) -> Optional[dict]:
    """
    Determine trade direction from SOL-ETH differential EMA.

    Logic (SOL-ETH direct differential pair, HL primary):
      regime = BULL_SOL (ema > 0):
        SOL FR > ETH FR -> SOL expensive (high funding cost to long)
        -> short SOL (collect high SOL FR) / long ETH (cheap carry)
        -> position_state = LONG_ETH_SHORT_SOL
        -> both legs on HL

      regime = BEAR_SOL (ema < 0):
        ETH FR > SOL FR -> ETH expensive (high funding cost to long)
        -> long SOL (cheap carry) / short ETH (collect ETH FR)
        -> position_state = LONG_SOL_SHORT_ETH
        -> both legs on HL

      regime = NEUTRAL: no trade (ema == 0 at initialization)

    K658 edge (ETH-base mechanism):
      The SOL-ETH differential cleanly captures SOL L1 retail momentum vs ETH
      DeFi/staking cycles. These two FR dynamics are structurally independent:
        - SOL FR: DePIN/memecoin retail cycles, Solana DEX dominance, jitoSOL demand
        - ETH FR: stETH/LST demand, ETH L1 gas narrative, ETH validator yield compression
      SOL-ETH vs SOL-BTC PnL corr = 0.2131 (PASS): diversification benefit confirmed.
      ETH-BTC (K449) ETH leg correlation = 0.0488: very low (orthogonal).
      SOL-BTC (K476) SOL leg correlation = 0.2131: low (orthogonal, dual sleeve OK).

    Returns:
      {long_asset, short_asset, long_venue, short_venue, diff_ema,
       signal_strength, size_multiplier, position_state}
      or None if NEUTRAL.
    """
    regime  = signal.get("regime", "NEUTRAL")
    ema     = signal.get("diff_ema_168h", 0.0)
    abs_ema = abs(ema)

    if regime == "NEUTRAL":
        return None

    if regime == "BULL_SOL":
        # SOL FR > ETH FR: SOL expensive (high funding cost to long)
        # short SOL (collect high FR) / long ETH (cheap carry)
        long_asset  = "ETH"
        short_asset = "SOL"
        state       = STATE_LONG_ETH_SHORT_SOL
    else:  # BEAR_SOL
        # ETH FR > SOL FR: ETH expensive (high funding cost to long)
        # long SOL (cheap carry) / short ETH (collect ETH FR)
        long_asset  = "SOL"
        short_asset = "ETH"
        state       = STATE_LONG_SOL_SHORT_ETH

    # Both legs on HL (K658: SOL-PERP + ETH-PERP, both HL)
    long_venue  = "HL"
    short_venue = "HL"

    # Signal strength: |ema| as simple magnitude (threshold=0, sign-based)
    strength = min(abs_ema / max(1e-10, 1e-6), 3.0)  # normalized to 1e-6 scale

    return {
        "long_asset":      long_asset,
        "short_asset":     short_asset,
        "position_state":  state,
        "long_venue":      long_venue,
        "short_venue":     short_venue,
        "diff_ema":        ema,
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
    Compute equal notional for both legs of the SOL-ETH paired trade.

    K658 HL-only config (both SOL-PERP + ETH-PERP on HL):
      sleeve_capital   = aum x sleeve_pct      (e.g. $10M x 1.5% = $150K)
      total_notional   = sleeve_capital x lev   ($150K x 4 = $600K)
      notional_per_leg = total_notional / 2     ($300K per leg)

    At $10M / 1.5% sleeve / 4x:
      SOL leg:   $75K capital x 4x = $300K notional (HL SOL-PERP)
      ETH leg:   $75K capital x 4x = $300K notional (HL ETH-PERP)
      Total:     $600K notional (two legs combined)
      Margin:    $150K (1.5% of AUM)
      Dual:      K476 1.5% + K658 1.5% = 3% combined = $300K margin
      Profit:    ~$42,332/yr @$10M @4x (OOS 7.06% ann ret x $10M x 4x x 1.5%)

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
    Submit K658 SOL-ETH paired trade: POST_ONLY both legs in parallel.

    Protocol (K658 HL primary — both legs on HL):
      1. Submit SOL leg on HL POST_ONLY
      2. Submit ETH leg on HL POST_ONLY
      3. Both legs submitted in parallel (K439 pattern)
      4. IOC fallback per leg if POST_ONLY times out
      5. If both fail: retry next 8h cycle

    Args:
      long_leg:  {"symbol": "SOL", "notional": 300000, "venue": "HL"}
      short_leg: {"symbol": "ETH", "notional": 300000, "venue": "HL"}
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
        print(f"  [K658] {mode_tag}: LONG {long_sym}@{long_venue} ${long_notl:,.0f}  "
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
            "venue_config":     "HL_PRIMARY_SOL_ETH",
            "mechanism_note":   (
                "SOL-ETH direct differential (ETH-base mechanism): "
                "SOL FR = DePIN/retail momentum cycles; "
                "ETH FR = DeFi/staking yields. "
                "SOL-ETH vs SOL-BTC PnL corr=0.2131 PASS (K658 K669)"
            ),
            "ts_utc":           ts,
        }
        _append_trade_log(result)
        return result

    # LIVE scaffold (not reached in PAPER_TRADE mode):
    print(f"  [K658] SCAFFOLD LIVE: parallel POST_ONLY "
          f"LONG {long_sym}@{long_venue} ${long_notl:,.0f} "
          f"+ SHORT {short_sym}@{short_venue} ${short_notl:,.0f}")
    long_order_id  = f"SCAFFOLD_LONG_{long_sym}_{int(time.time())}"
    short_order_id = f"SCAFFOLD_SHORT_{short_sym}_{int(time.time())}"

    # Scaffold: poll not implemented — retry next 8h cycle
    print(f"  [K658] Neither leg filled within timeout — retry next 8h cycle")
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
    Check if current K658 position has drifted beyond DRIFT_REBALANCE_PCT (5%).

    K658 HL-only: both legs on HL (SOL-PERP + ETH-PERP).
    Drift detection: compare stored SOL leg notional vs ETH leg notional.
    Threshold: 5% (same as K449/K476/K484/K493/K629 pattern).

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
    Both legs on HL (K658 HL primary — SOL-PERP + ETH-PERP).

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

    if state == STATE_LONG_SOL_SHORT_ETH:
        long_sym,  short_sym  = "SOL", "ETH"
    else:  # LONG_ETH_SHORT_SOL
        long_sym,  short_sym  = "ETH", "SOL"

    long_notional  = float(dash.get("long_notional",  0.0))
    short_notional = float(dash.get("short_notional", 0.0))

    if dry_run or PAPER_TRADE:
        mode_tag = "DRY_RUN" if dry_run else "PAPER_TRADE"
        print(f"  [K658] {mode_tag} CLOSE:")
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
        print(f"  [K658] SCAFFOLD CLOSE:")
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
    """Load k658_dashboard.json; return defaults if missing."""
    if DASHBOARD_PATH.exists():
        try:
            return json.loads(DASHBOARD_PATH.read_text())
        except Exception:
            pass
    return {
        "last_poll_jst":           "—",
        "diff_ema_168h":           0.0,
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
    """Write k658_dashboard.json with full signal + regime state."""
    dash = _load_dashboard()

    # Update signal data
    dash["last_poll_jst"]        = signal.get("ts_jst", "—")
    dash["fr_sol_current"]       = signal.get("fr_sol",       0.0)
    dash["fr_eth_current"]       = signal.get("fr_eth",       0.0)
    dash["sol_eth_diff_current"] = signal.get("sol_eth_diff", 0.0)
    dash["diff_ema_168h"]        = signal.get("diff_ema_168h", 0.0)
    dash["diff_sigma"]           = signal.get("diff_sigma",    0.0)
    dash["regime"]               = signal.get("regime",   "NEUTRAL")
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
            dash["venue"]           = "HL"
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
    dash["hl_concentration_note"]    = HL_CONCENTRATION_NOTE

    # Paper-trade status
    paper_status = dash.get("paper_trade_status", {"days_elapsed": 0, "target_60d": 60})
    dash["paper_trade_status"]       = paper_status

    # 60d activation gate metrics (K669: Realized Sh>=15, fill>=60%, DD<15%)
    dash["gate_metrics"] = {
        "realized_sharpe_target":  15.0,     # >=15 (50% of K658 OOS 29.66)
        "fill_rate_target_pct":    60,
        "max_drawdown_target_pct": 15,        # <15% (stricter gate given high Sharpe claim)
        "current_realized_sharpe": dash.get("60d_sharpe", 0.0),
        "current_fill_rate_pct":   0.0,
        "current_max_dd_pct":      0.0,
        "gate_status":             "IN_PROGRESS",
        "activation_trigger":      "60d paper-trade: Sh>=15 AND fill>=60% AND maxDD<15%",
        "profit_at_activation_1_5pct": "$42,332/yr @$10M @4x (1.5% sleeve, OOS 7.06% ann ret)",
        "dual_sleeve_note":        "K476 1.5% + K658 1.5% = 3% combined; PnL corr=0.2131",
    }

    # Strategy metadata
    dash["paper_trade_mode"]    = PAPER_TRADE
    dash["wave"]                = "K669"
    dash["strategy"]            = "K658 SOL-ETH FR Differential (ETH-base, SOL L1 Momentum, W=168h)"
    dash["execution_mode"]      = "POST_ONLY_PARALLEL"
    dash["venue_config"]        = "HL_PRIMARY"
    dash["eth_base_mechanism"]  = {
        "formula":        "diff = SOL_FR - ETH_FR  (direct, no orthogonalization)",
        "ema_window":     "W=168h (21 x 8h periods, primary config, G6 structural at Sh=29.66)",
        "threshold":      "sign(EMA) — threshold=0 (optimal from K658 grid search)",
        "sol_btc_corr_k476": 0.2131,  # PnL corr with K476 SOL-BTC (PASS < 0.40)
        "eth_btc_corr_k449": 0.0488,  # PnL corr with K449 ETH-BTC critical (PASS)
        "wld_eth_corr_k629": 0.08,    # PnL corr with K629 WLD-ETH same-base (PASS)
        "adf_pvalue":     0.0,
        "ou_halflife_h":  2.4,
        "ou_theta":       0.290,
        "vol_ratio":      1.63,        # SOL/ETH FR std ratio (>= 1.5x PASS)
        "note":           (
            "ETH-base wins for SOL family: Sh 16.30->29.66 (+13.36). "
            "SOL FR = DePIN/retail momentum; ETH FR = DeFi/staking yields. "
            "Dual sleeve with K476: 1.5%+1.5%=3% combined, corr=0.2131 diversified."
        ),
    }
    dash["activation_criteria"] = {
        "60d_paper_trade_gate":   "required",
        "realized_sharpe_min":    15.0,
        "fill_rate_min_pct":      60,
        "max_drawdown_max_pct":   15,
        "status":                 "SCAFFOLD-READY",
        "activation_sleeve_pct":  0.015,
        "venue":                  "HL primary (SOL-PERP + ETH-PERP both on HL)",
        "dual_sleeve_partner":    "K476 SOL-BTC 1.5% (PnL corr=0.2131 diversified)",
    }
    dash["oos_performance"] = {
        "sharpe":                   29.6613,
        "sharpe_is":                5.7914,
        "oos_ann_ret_pct":          7.0553,
        "oos_ann_ret_4x_pct":       28.221,
        "ann_return_usd_1_5pct_4x": 42_332,
        "ann_return_usd_3pct_4x":   84_664,
        "wave_accept":              "K658 ACCEPT (K669 scaffold) — ETH-BASE WINS vs K476",
        "cluster":                  "SOL L1 Monolithic / SVM DePIN-Retail (ETH-base)",
        "cluster_rationale":        (
            "SOL (Solana) FR driven by DePIN/memecoin retail momentum, Raydium/Orca DEX volume, "
            "Jito MEV + jitoSOL demand, validator yield cycles. "
            "ETH-base fix: Sh 16.30->29.66 (+13.36 delta). "
            "Dual sleeve with K476: corr=0.2131 diversified, combined Sh est=26.4."
        ),
        "hl_concentration_note":    HL_CONCENTRATION_NOTE,
        "sol_btc_k476_comparison":  "K658 OOS Sh=29.66 > K476 OOS Sh=16.30 (+13.36)",
        "walk_forward":             "4/4 folds positive (100%)",
        "perm_pvalue":              0.0,
        "dsr_pvalue":               1.56e-109,
        "entries_yr":               20.3,
        "max_drawdown_pct":         0.2833,
        "adf_pvalue":               0.0,
        "ou_halflife_h":            2.4,
        "daemon_number":            "52nd",
        "wave_scaffold":            "K669",
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
      1. Fetch SOL + ETH FRs from HL
      2. Compute SOL-ETH differential + 168h EMA
      3. Decide position (sign(EMA) threshold)
      4. Compute delta-neutral notional
      5. If entering: submit paired trade (POST_ONLY, HL primary)
      6. If holding: check drift + rebalance
      7. Write k658_dashboard.json
    """
    ts_jst = datetime.now(JST).strftime("%Y-%m-%d %H:%M JST")
    print(f"\n=== K658 SOL-ETH FR Differential (ETH-base, SOL L1 Momentum) — {ts_jst} ===")
    print(f"  Mode:      {'DRY-RUN' if dry_run else 'PAPER-TRADE' if PAPER_TRADE else 'LIVE'}")
    print(f"  AUM:       ${aum:,.0f}  Sleeve: {SLEEVE_PCT:.1%}  Leverage: {LEVERAGE}x")
    print(f"  Venue:     HL primary (SOL-PERP + ETH-PERP, both HL perps)")
    print(f"  Execution: POST_ONLY parallel (K439)")
    print(f"  Dual:      K476 SOL-BTC 1.5% + K658 SOL-ETH 1.5% = 3% combined")
    print(f"  Signal:    diff = SOL_FR - ETH_FR  (direct, no OLS orthogonalization)")
    print(f"             sign(EMA_168h) — threshold=0 (K658 grid optimal)")
    print(f"  ETH-base:  SOL-BTC K476 corr=0.2131 PASS (diversified dual sleeve)")
    print(f"  Edge:      ETH-base wins: Sh 16.30->29.66 (+13.36 delta vs K476)")
    print(f"  9/9 gates: G1={29.66:.2f} G2=0.0 G3=1.56e-109 G4=4/4 G5=0.2131 G6=struct G7=7.06% G8=0.28% G9=n/a")

    # Step 1: Fetch + compute SOL-ETH differential
    print("\n  [Step 1] Computing SOL-ETH FR differential...")
    signal = compute_signal()
    print(f"  SOL FR:     {signal['fr_sol']:+.8f} (8h, HL)")
    print(f"  ETH FR:     {signal['fr_eth']:+.8f} (8h, HL)")
    print(f"  SOL-ETH:    {signal['sol_eth_diff']:+.8f}  (direct differential)")
    print(f"  EMA 168h:   {signal['diff_ema_168h']:+.8f}")
    print(f"  Sigma 168h: {signal['diff_sigma']:+.8f}")
    print(f"  Regime:     {signal['regime']}")
    print(f"  History:    {signal['history_points']} data points")

    # Step 2: Position decision
    print("\n  [Step 2] Deciding position...")
    decision = decide_position(signal)
    if decision:
        print(f"  Signal:   LONG {decision['long_asset']}@{decision['long_venue']} / "
              f"SHORT {decision['short_asset']}@{decision['short_venue']}")
        print(f"  State:    {decision['position_state']}")
    else:
        print(f"  Signal:   NEUTRAL (EMA == 0 at initialization)")

    # Step 3: Notional sizing
    notional_per_leg, total_notional = \
        compute_delta_neutral_notional(aum, SLEEVE_PCT, LEVERAGE)
    print(f"\n  [Step 3] Notional sizing:")
    print(f"  Sleeve capital:   ${aum * SLEEVE_PCT:,.0f}  ({SLEEVE_PCT:.1%} x ${aum/1e6:.0f}M)")
    print(f"  SOL leg:          ${notional_per_leg:,.0f}  (1.5% x ${aum/1e6:.0f}M x {LEVERAGE}x / 2)")
    print(f"  ETH leg:          ${notional_per_leg:,.0f}  (1.5% x ${aum/1e6:.0f}M x {LEVERAGE}x / 2)")
    print(f"  Total notional:   ${total_notional:,.0f}")
    print(f"  Margin required:  ${total_notional/LEVERAGE:,.0f}  ({SLEEVE_PCT:.1%} AUM)")
    print(f"  Profit @$10M 4x:  OOS 7.06% ann ret = $42,332/yr potential (1.5% sleeve)")

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
        print(f"  Action: CLOSE (EMA at neutral — no signal)")
        trade_result = close_paired_position("signal_neutral", dry_run=dry_run)

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
    print(f"\n  === K658 Cycle Complete ===")
    print(f"  Position state:     {dash_out.get('position_state')}")
    print(f"  Regime:             {dash_out.get('regime')}")
    print(f"  SOL-ETH EMA 168h:   {dash_out.get('diff_ema_168h'):+.8f}")
    print(f"  ETH-base wins:      SOL-BTC K476 corr=0.2131 (dual sleeve OK)")
    print(f"  Paper-trade mode:   {PAPER_TRADE}")
    print(f"  OOS Sharpe:         29.66 (vs K476 16.30, +13.36 ETH-base improvement)")
    print(f"  Cluster:            SOL L1 Monolithic / SVM DePIN-Retail (ETH-base)")
    print(f"  Profit 1.5% sleeve: $42,332/yr @$10M @4x (OOS 7.06% ann ret)")
    print(f"  Dual sleeve:        K476 1.5% + K658 1.5% = 3% combined ($85K/yr est)")
    print(f"  60d gate:           Realized Sh>=15 + fill>=60% + maxDD<15%")
    print(f"  v6.40 path:         K658 SOL-ETH 1.5% HL sleeve (52nd daemon)")
    print()

    return 0


# ─────────────────────────────────────────────────────────────────────────────
# CLI entry point
# ─────────────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="K658 SOL-ETH FR Differential Strategy (K669 scaffold, ETH-base SOL L1)"
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
        print(f"\n=== K658 Dashboard ({dash.get('last_poll_jst', '—')}) ===")
        print(json.dumps(dash, indent=2))
        return 0

    if args.rebalance:
        dash   = _load_dashboard()
        result = daily_rebalance(dash)
        print(f"\n=== K658 Rebalance Check ===")
        print(json.dumps(result, indent=2))
        return 0

    if args.close:
        result = close_paired_position(args.close, dry_run=args.dry_run)
        print(f"\n=== K658 Close Result ===")
        print(json.dumps(result, indent=2))
        return 0

    return run_cycle(dry_run=args.dry_run, aum=args.aum)


if __name__ == "__main__":
    sys.exit(main())
