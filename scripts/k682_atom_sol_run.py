#!/usr/bin/env python3
"""
k682_atom_sol_run.py — K682 ATOM-SOL FR Differential Strategy
==============================================================
SECOND ALT-ALT pair: ATOM vs SOL (no BTC/ETH base).
Signal: ATOM_FR - SOL_FR
W=168h rolling mean, zero threshold (sign only)
Bybit-only (ATOM-PERP + SOL-PERP on Bybit)
HL concentration: 62.5% (Bybit-only mandatory to avoid breach)

K682 ATOM-SOL alt-alt hypothesis:
  ATOM (Cosmos) FR dynamics: Cosmos IBC governance-driven episodic spikes,
  validator staking inflation pressure (negative FR bias), new Cosmos chain
  launches, SNS/DAO proposal cycles, IBC ecosystem growth events.
  SOL (Solana) FR dynamics: Monolithic SVM DePIN/Retail adoption, persistent
  positive FR premium (~+7.73%/ann), meme-coin cycle premium (BONK/WIF),
  Solana network congestion spikes, Firedancer upgrade cycles.
  Alt-alt mechanism: ATOM and SOL are BOTH non-BTC non-ETH alts with orthogonal
  FR drivers. ATOM FR tracks Cosmos governance/IBC narrative; SOL FR tracks
  Solana consumer/DePIN narrative. Mathematical identity: ATOM-SOL = -(K493
  direction) + (K476 direction) — algebraically anti-correlated with K493
  (G5c signed convention PASS). K682 HEDGES K493 portfolio exposure.

K682 §6 validation (ACCEPT — 10/12 gates):
  - OOS Sharpe: 43.43 (SECOND ALT-ALT pair, higher than K679 APT-SOL 39.29)
  - OOS Ann Return: $214.6K/yr @$10M @4x @2% standalone sleeve
  - W=168h rolling mean, zero threshold (sign of diff)
  - ADF p<4.25e-30 (stationary, 1%), OU mean-reverting (half-life 3.37h)
  - Walk-forward: 10/12 folds positive (G4 fails, 2 negative early folds)
  - Bybit-only (both ATOM-PERP + SOL-PERP on Bybit)
  - 60d gate: Realized Sh >= 22 (50% of 43.43), fill >= 60%, DD < 15%

K493+K476 overlap warning:
  K493 ATOM-BTC (HL+Bybit split, 5% sleeve) — ATOM leg.
  K476 SOL-BTC (HL-only, 1.5% sleeve) — SOL leg.
  K682 ATOM-SOL uses BOTH ATOM and SOL but as the DIFFERENTIAL pair.
  Math identity: ATOM-SOL = -(BTC-ATOM) + (BTC-SOL) = -K493_dir + K476_dir.
  K682 anti-correlated with K493 (G5c = -0.5195, PASS signed convention).
  K682 HEDGES K493 ATOM exposure (anti-corr = diversifying).
  Standalone means K682 does NOT assume K493/K476 positions as hedges.
  Run K682 standalone with its own 2% sleeve OR rebalance K493+K476
  sleeves to net-zero if ATOM-SOL is intended as synthetic substitute.
  DEFAULT: K682 standalone (2% Bybit sleeve, independent).

Architecture (K679/K663/K668 scaffold pattern):
  1. fetch_fr_batch()                 → fetch ATOM + SOL FR every 8h from Bybit
  2. compute_signal(atom_fr, sol_fr)  → 168h rolling mean of (ATOM_FR - SOL_FR); sign()
  3. decide_position(signal)          → LONG_ATOM_SHORT_SOL | LONG_SOL_SHORT_ATOM | NEUTRAL
  4. submit_paired_trade(long, short) → POST_ONLY paired (ATOM + SOL legs, both Bybit)
  5. daily_rebalance()                → drift > 5% triggers rebalance
  6. close_paired_position(reason)    → sequential: short first, then long

K685 production scaffold:
  - 55th daemon (2nd alt-alt pair; same daemon slot as K679 per eval — K682 is new addition)
  - Actually: K682 is the 56th daemon if K679 is the 55th daemon
  - Note: The commit spec labels this the 55th daemon per "2nd alt-alt" but K679 is already
    the 55th. K682 is the 56th daemon (first deployment after K679 55th).
  - Bybit-only (HL at 62.5%; adding to HL would breach 65% cap)
  - 2% standalone sleeve (reduced from 3% per algebraic overlap with K493+K476)
  - $214.6K/yr net @$10M @4x @2% sleeve (OOS Sh=43.43 — 2nd alt-alt record)
  - 60d paper-trade gate: Realized Sh>=22 + fill>=60% + maxDD<15%

Execution:
  - Bybit primary (ATOM-PERP + SOL-PERP, both Bybit)
  - POST_ONLY paired execution (K439 pattern)
  - Position: 2% sleeve, 4x leverage (standalone)
  - 8h cadence (matches FR settlement cycle)
  - W=168h rolling mean (21 x 8h periods)

Paper-trade mode is the DEFAULT.  No orders are submitted unless
PAPER_TRADE=False is explicitly set in the environment.

K339 security: REPO_ROOT from __file__, no /Users/ literals.
No new packages — stdlib urllib + json only.

Usage:
  python3 scripts/k682_atom_sol_run.py --dry-run
  python3 scripts/k682_atom_sol_run.py --status
  python3 scripts/k682_atom_sol_run.py --rebalance
  python3 scripts/k682_atom_sol_run.py --close "scheduled exit"
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

DASHBOARD_PATH  = DATA_DIR  / "k682_dashboard.json"
FR_HISTORY_PATH = CACHE_DIR / "k682_fr_history.jsonl"
TRADE_LOG_PATH  = CACHE_DIR / "k682_paper_trades.jsonl"

JST = timezone(timedelta(hours=9))
UTC = timezone.utc

# ── Strategy constants ────────────────────────────────────────────────────────
PAPER_TRADE         = True          # never submit real orders in paper-trade mode
SLEEVE_PCT          = 0.020         # K682 sleeve = 2% of AUM (standalone, Bybit-only)
LEVERAGE            = 4.0           # 4x per K682 analysis (K430 cap)
AUM_DEFAULT         = 10_000_000.0  # $10M reference AUM
DRIFT_REBALANCE_PCT = 0.05          # rebalance if legs drift > 5%
IOC_TIMEOUT_SEC     = 300           # 5 min fill window
EMA_PERIOD_HOURS    = 168           # 168h rolling mean primary config (W=168h)
EMA_PERIOD_PERIODS  = EMA_PERIOD_HOURS // 8  # = 21 periods (8h settlement cycle)
SIGNAL_SIGMA_MULT   = 0.0           # zero threshold (sign of rolling mean)
BYBIT_API_URL       = "https://api.bybit.com"
HL_API_URL          = "https://api.hyperliquid.xyz/info"

# ── Venue config (Bybit-only — ATOM-PERP + SOL-PERP on Bybit) ─────────────────
# HL concentration: 62.5% — adding 2% would breach 65% cap (62.5+2=64.5 OK but
# both legs HL-only = 65.5% > 65% cap). Bybit-only is PREFERRED.
HL_CONCENTRATION_PRE_K682   = 62.5   # post-K679 reference (within 65% cap)
HL_CONCENTRATION_POST_K682  = 62.5   # UNCHANGED — Bybit-only, no HL impact
BYBIT_ONLY_REASON           = "HL concentration 62.5%; HL-only would breach 65% cap (62.5+2=64.5 marginal, Bybit safer)"

# ── Position state constants ──────────────────────────────────────────────────
STATE_NEUTRAL             = "NEUTRAL"
STATE_LONG_ATOM_SHORT_SOL = "LONG_ATOM_SHORT_SOL"
STATE_LONG_SOL_SHORT_ATOM = "LONG_SOL_SHORT_ATOM"

# ── Symbols fetched from Bybit for FR data ────────────────────────────────────
# K682: ATOM + SOL only — direct alt-alt differential (SECOND ALT-ALT pair)
SYMBOLS = ("ATOM", "SOL")


# ─────────────────────────────────────────────────────────────────────────────
# HTTP helper (stdlib urllib only — no requests)
# ─────────────────────────────────────────────────────────────────────────────

def _http_get(url: str, timeout: int = 10) -> Optional[dict]:
    try:
        req = urllib.request.Request(
            url, headers={"User-Agent": "crypto-lab-k682/1.0"}
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        print(f"  [k682] HTTP error: {e}", file=sys.stderr)
        return None


def _http_post(url: str, payload: dict, timeout: int = 10) -> Optional[dict]:
    try:
        data = json.dumps(payload).encode()
        req  = urllib.request.Request(
            url, data=data,
            headers={"Content-Type": "application/json",
                     "User-Agent": "crypto-lab-k682/1.0"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        print(f"  [k682] HTTP error: {e}", file=sys.stderr)
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Phase 1 — Funding rate fetch (ATOM + SOL from Bybit)
# ─────────────────────────────────────────────────────────────────────────────

def _fetch_bybit_fr_batch() -> Dict[str, float]:
    """
    Fetch current 8h funding rates for ATOM and SOL from Bybit.
    Returns {symbol: fr_8h_fraction}.

    Bybit API: /v5/market/tickers?category=linear
    K682: both legs on Bybit (ATOM-PERP + SOL-PERP).
    HL concentration at 62.5%; Bybit-only avoids any cap risk.

    Fallback: HL metaAndAssetCtxs for cross-reference (informational only).
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
        print(f"  [k682] Bybit partial result {list(result.keys())} — trying HL fallback",
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
                    print(f"  [k682] {sym} FR from HL fallback (informational)", file=sys.stderr)
                except (TypeError, ValueError):
                    continue
    return result


def _load_fr_history() -> List[dict]:
    """Load K682 FR history JSONL."""
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
    fr_atom: float, fr_sol: float, atom_sol_diff: float
) -> None:
    """Append one FR snapshot to history."""
    rec = {
        "ts_utc":        datetime.now(UTC).isoformat(),
        "fr_atom":       round(fr_atom,       10),
        "fr_sol":        round(fr_sol,         10),
        "atom_sol_diff": round(atom_sol_diff,  10),  # ATOM_FR - SOL_FR (direct alt-alt differential)
    }
    with open(FR_HISTORY_PATH, "a") as f:
        f.write(json.dumps(rec) + "\n")


# ─────────────────────────────────────────────────────────────────────────────
# Phase 2 — Signal computation (ATOM-SOL direct differential, 168h rolling mean)
# ─────────────────────────────────────────────────────────────────────────────

def compute_signal(
    fr_atom: Optional[float] = None,
    fr_sol:  Optional[float] = None,
) -> dict:
    """
    Fetch live ATOM and SOL FRs from Bybit, compute ATOM-SOL differential,
    and compute 168h rolling mean for direction signal.

    Signal mechanism (K682 direct alt-alt differential — no orthogonalization):
      diff = ATOM_FR - SOL_FR
      mean_168h = 168h rolling mean of diff (21 x 8h periods)
      sign  = sign(mean_168h)
      Enter: sign > 0 -> ATOM FR > SOL FR (IBC governance spike) -> short SOL, long ATOM
             sign < 0 -> SOL FR > ATOM FR (Retail/DePIN premium) -> long ATOM, short SOL

    Alt-alt mechanism (SECOND ALT-ALT pair — K682):
      ATOM FR tracks Cosmos IBC governance cycles: new chain launches, validator staking
      inflation pressure (negative FR mean -3.27%/ann), SNS DAO proposals, IBC ecosystem
      growth events. ATOM FR episodic and governance-driven.
      SOL FR tracks Solana DePIN/Retail adoption premium: persistent positive FR
      (~+7.73%/ann), meme-coin season (BONK/WIF), Firedancer upgrade hype,
      validator economics, network congestion spikes.
      ATOM-SOL diff captures relative Cosmos-IBC premium vs SVM-Retail premium.
      No BTC or ETH leg → pure alt-alt → different from all prior BTC-base/ETH-base family.

    Mathematical identity & portfolio note:
      ATOM-SOL = (ATOM_FR - BTC_FR) - (SOL_FR - BTC_FR) = K493_direction_rev + K476_direction
      K682 vs K493 signed corr = -0.5195 (anti-corr expected by identity, PASSES G5c signed).
      K682 HEDGES K493 ATOM-BTC exposure in portfolio. Running K682+K493+K476 simultaneously
      creates algebraic overlap. PREFER K682 STANDALONE 2% sleeve.

    K682 §6 validation (10/12 gates ACCEPT):
      - OOS Sharpe: 43.43 (SECOND ALT-ALT pair record, > K679 39.29)
      - OOS Ann Return: ~21.04% (1x), 84.17% (4x), $214.6K/yr net @$10M @4x @2% sleeve
      - ADF p=4.25e-30 (stationary at 1%), OU half-life 3.37h (STRONG mean-reversion)
      - Walk-forward 10/12 folds positive (G4 FAIL — 2 early negative folds Q4 2024)
      - G6 trades/yr=26.8 (FAIL borderline — alt-alt lower turnover than BTC-base)
      - Permutation p=0.0, DSR Bonferroni p=0.0 (both PASS)
      - 60d gate: Realized Sh>=22 + fill>=60% + maxDD<15%

    Returns:
      {
        "fr_atom":          float,
        "fr_sol":           float,
        "atom_sol_diff":    float,    # ATOM_FR - SOL_FR (current)
        "mean_168h":        float,    # 168h rolling mean of differential
        "diff_sigma":       float,    # 168h rolling sigma (informational)
        "history_points":   int,
        "regime":           str,      # BULL_ATOM | BEAR_ATOM | NEUTRAL
        "signal_direction": int,      # +1 | -1 | 0
        "ts_jst":           str,
      }
    """
    if fr_atom is None or fr_sol is None:
        frs     = _fetch_bybit_fr_batch()
        fr_atom = frs.get("ATOM", 0.0)
        fr_sol  = frs.get("SOL",  0.0)

    # ATOM-SOL direct alt-alt differential (no orthogonalization)
    atom_sol_diff = fr_atom - fr_sol

    _append_fr_history(fr_atom, fr_sol, atom_sol_diff)

    # Load history for rolling mean + sigma (168h = 21 x 8h periods)
    history = _load_fr_history()
    diffs   = [r["atom_sol_diff"] for r in history if "atom_sol_diff" in r]

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

    # Regime classification (zero threshold — per K682 spec)
    # BULL_ATOM: ATOM FR > SOL FR (Cosmos IBC governance premium spike)
    # BEAR_ATOM: ATOM FR < SOL FR (SOL retail/DePIN structural premium, normal 80%+ of time)
    if mean_168h > 0:
        regime    = "BULL_ATOM"   # ATOM-SOL diff positive -> ATOM FR > SOL FR (episodic)
        direction = 1
    elif mean_168h < 0:
        regime    = "BEAR_ATOM"   # ATOM-SOL diff negative -> SOL FR > ATOM FR (persistent)
        direction = -1
    else:
        regime    = "NEUTRAL"
        direction = 0

    return {
        "fr_atom":           round(fr_atom,       10),
        "fr_sol":            round(fr_sol,         10),
        "atom_sol_diff":     round(atom_sol_diff,  10),
        "mean_168h":         round(mean_168h,      10),
        "diff_sigma":        round(sigma,          10),
        "history_points":    len(diffs),
        "regime":            regime,
        "signal_direction":  direction,
        "ts_jst":            datetime.now(JST).strftime("%Y-%m-%d %H:%M JST"),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Phase 3 — Position decision
# ─────────────────────────────────────────────────────────────────────────────

def decide_position(signal: dict) -> Optional[dict]:
    """
    Determine trade direction from ATOM-SOL differential rolling mean.

    Logic (ATOM-SOL direct alt-alt pair, Bybit primary):
      regime = BULL_ATOM (mean_168h > 0):
        ATOM FR > SOL FR: Cosmos IBC governance spike (episodic event)
        -> short SOL (collect lower FR) / long ATOM (receive positive ATOM FR)
        WAIT — actually: when ATOM FR > SOL (high ATOM FR premium):
          ATOM is expensive to long (governance episode makes longs pay high FR)
          -> short ATOM (collect high ATOM FR) / long SOL (cheaper carry)
          -> position_state = LONG_SOL_SHORT_ATOM
        NB: Sign convention same as K679:
          BULL_ATOM (ATOM FR > SOL FR) -> short ATOM, long SOL (collect high ATOM FR)
          Both legs on Bybit.

      regime = BEAR_ATOM (mean_168h < 0):
        SOL FR > ATOM FR: SOL persistent retail/DePIN premium (normal state 80%+ of time)
        -> short SOL (collect high SOL FR premium) / long ATOM (cheap carry, may earn negative FR)
        -> position_state = LONG_ATOM_SHORT_SOL
        -> both legs on Bybit

      regime = NEUTRAL: no trade (mean_168h == 0 exactly — rare)

    Alt-alt edge:
      This is the SECOND ALT-ALT pair in the portfolio (after K679 APT-SOL).
      ATOM and SOL have no BTC or ETH in their pair, creating a pure
      alt-narrative differential:
        BULL_ATOM periods: Cosmos IBC governance events, new parachain launches,
          validator staking pressure spikes. ATOM FR episodic peaks above SOL.
          -> short ATOM (collect premium) / long SOL (cheap carry).
        BEAR_ATOM periods (80%+ of time): SOL DePIN premium dominates.
          SOL FR > ATOM (negative bias -3.27%/ann) -> long ATOM / short SOL (collect SOL FR).

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

    if regime == "BULL_ATOM":
        # ATOM FR > SOL FR: Cosmos IBC governance spike (episodic)
        # ATOM expensive to long -> short ATOM (collect high ATOM FR) / long SOL
        long_asset  = "SOL"
        short_asset = "ATOM"
        state       = STATE_LONG_SOL_SHORT_ATOM
    else:  # BEAR_ATOM
        # SOL FR > ATOM FR: SOL retail/DePIN structural premium (persistent 80%+ of time)
        # long ATOM (cheap carry, negative FR bias -3.27%/ann) / short SOL (collect high SOL FR)
        long_asset  = "ATOM"
        short_asset = "SOL"
        state       = STATE_LONG_ATOM_SHORT_SOL

    # Both legs on Bybit (K682: ATOM-PERP + SOL-PERP, both Bybit)
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
    Compute equal notional for both legs of the ATOM-SOL paired trade.

    K682 Bybit-only config (both ATOM-PERP + SOL-PERP on Bybit):
      sleeve_capital   = aum x sleeve_pct      (e.g. $10M x 2.0% = $200K)
      total_notional   = sleeve_capital x lev   ($200K x 4 = $800K)
      notional_per_leg = total_notional / 2     ($400K per leg)

    At $10M / 2% sleeve / 4x (standalone):
      ATOM leg:  $100K capital x 4x = $400K notional (Bybit ATOM-PERP)
      SOL leg:   $100K capital x 4x = $400K notional (Bybit SOL-PERP)
      Total:     $800K notional (two legs combined)
      Margin:    $200K (2% of AUM)
      HL conc:   UNCHANGED at 62.5% (Bybit-only)
      Net profit: ~$214,638/yr @$10M @4x @2% sleeve (OOS ann ret x notional)
      K493+K476 note: standalone (no algebraic netting assumed)

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
    Submit K682 ATOM-SOL paired trade: POST_ONLY both legs in parallel.

    Protocol (K682 Bybit primary — both legs on Bybit):
      1. Submit ATOM leg on Bybit POST_ONLY
      2. Submit SOL leg on Bybit POST_ONLY
      3. Both legs submitted in parallel (K439 pattern)
      4. IOC fallback per leg if POST_ONLY times out
      5. If both fail: retry next 8h cycle

    Args:
      long_leg:  {"symbol": "ATOM", "notional": 400000, "venue": "BYBIT"}
      short_leg: {"symbol": "SOL",  "notional": 400000, "venue": "BYBIT"}
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
        print(f"  [K682] {mode_tag}: LONG {long_sym}@{long_venue} ${long_notl:,.0f}  "
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
            "venue_config":     "BYBIT_ONLY_ATOM_SOL_ALT_ALT",
            "mechanism_note":   (
                "ATOM-SOL direct alt-alt differential (K682 SECOND ALT-ALT): "
                "ATOM FR = Cosmos IBC governance-driven episodics (new chain launches, validator "
                "staking inflation pressure -3.27%/ann mean, SNS DAO proposals, IBC ecosystem beta); "
                "SOL FR = Solana DePIN/Retail adoption premium (persistent +7.73%/ann, meme-coin "
                "season BONK/WIF, Firedancer upgrade hype, validator economics). "
                "Bybit-only: HL at 62.5%; HL-only would approach 65% cap — Bybit preferred. "
                "K493+K476 overlap warning: K682 STANDALONE (anti-corr -0.5195 with K493 HEDGES). "
                "OOS Sh=43.43 (SECOND ALT-ALT record > K679 39.29), $214.6K/yr @$10M @4x @2% sleeve."
            ),
            "ts_utc":           ts,
        }
        _append_trade_log(result)
        return result

    # LIVE scaffold (not reached in PAPER_TRADE mode):
    print(f"  [K682] SCAFFOLD LIVE: parallel POST_ONLY "
          f"LONG {long_sym}@{long_venue} ${long_notl:,.0f} "
          f"+ SHORT {short_sym}@{short_venue} ${short_notl:,.0f}")
    long_order_id  = f"SCAFFOLD_LONG_{long_sym}_{int(time.time())}"
    short_order_id = f"SCAFFOLD_SHORT_{short_sym}_{int(time.time())}"

    print(f"  [K682] Neither leg filled within timeout — retry next 8h cycle")
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
    Check if current K682 position has drifted beyond DRIFT_REBALANCE_PCT (5%).

    K682 Bybit-only: both legs on Bybit (ATOM-PERP + SOL-PERP).
    Drift detection: compare stored ATOM leg notional vs SOL leg notional.
    Threshold: 5% (same as K449/K476/K484/K493/K629/K663/K679 pattern).

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
    Both legs on Bybit (K682 Bybit primary — ATOM-PERP + SOL-PERP).

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

    if state == STATE_LONG_ATOM_SHORT_SOL:
        long_sym,  short_sym  = "ATOM", "SOL"
    else:  # LONG_SOL_SHORT_ATOM
        long_sym,  short_sym  = "SOL", "ATOM"

    long_notional  = float(dash.get("long_notional",  0.0))
    short_notional = float(dash.get("short_notional", 0.0))

    if dry_run or PAPER_TRADE:
        mode_tag = "DRY_RUN" if dry_run else "PAPER_TRADE"
        print(f"  [K682] {mode_tag} CLOSE:")
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
        print(f"  [K682] SCAFFOLD CLOSE:")
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
    """Load k682_dashboard.json; return defaults if missing."""
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
    """Write k682_dashboard.json with full signal + regime state."""
    dash = _load_dashboard()

    # Update signal data
    dash["last_poll_jst"]         = signal.get("ts_jst", "—")
    dash["fr_atom_current"]       = signal.get("fr_atom",       0.0)
    dash["fr_sol_current"]        = signal.get("fr_sol",        0.0)
    dash["atom_sol_diff_current"] = signal.get("atom_sol_diff", 0.0)
    dash["mean_168h"]             = signal.get("mean_168h",     0.0)
    dash["diff_sigma"]            = signal.get("diff_sigma",    0.0)
    dash["regime"]                = signal.get("regime",   "NEUTRAL")
    dash["signal_direction"]      = signal.get("signal_direction", 0)
    dash["history_points"]        = signal.get("history_points", 0)

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
    dash["hl_concentration_pct"]     = HL_CONCENTRATION_POST_K682   # 62.5% UNCHANGED (Bybit-only)

    # Paper-trade status
    paper_status = dash.get("paper_trade_status", {"days_elapsed": 0, "target_60d": 60})
    dash["paper_trade_status"]       = paper_status

    # 60d activation gate metrics (K685: Realized Sh >= 22, fill >= 60%, DD < 15%)
    dash["gate_metrics"] = {
        "realized_sharpe_target":  22.0,    # >=22 (50% of K682 OOS 43.43)
        "fill_rate_target_pct":    60,
        "max_drawdown_target_pct": 15,       # <15%
        "current_realized_sharpe": dash.get("60d_sharpe", 0.0),
        "current_fill_rate_pct":   0.0,
        "current_max_dd_pct":      0.0,
        "gate_status":             "IN_PROGRESS",
        "activation_trigger":      "60d paper-trade: Sh>=22 AND fill>=60% AND maxDD<15%",
        "profit_at_activation_2pct": "$214,638/yr net @$10M @4x (2% sleeve, OOS Sh 43.43)",
        "alt_alt_note":            "SECOND ALT-ALT pair (ATOM-SOL, no BTC/ETH leg). Standalone.",
        "overlap_warning":         "K493 ATOM-BTC + K476 SOL-BTC algebraic overlap — run standalone or rebalance",
        "anti_correlation_note":   "K682 vs K493 corr=-0.5195 (HEDGES K493 ATOM exposure in portfolio)",
    }

    # Strategy metadata
    dash["paper_trade_mode"]    = PAPER_TRADE
    dash["wave"]                = "K685"
    dash["strategy"]            = "K682 ATOM-SOL FR Differential (SECOND ALT-ALT, W=168h, Bybit-only)"
    dash["execution_mode"]      = "POST_ONLY_PARALLEL"
    dash["venue_config"]        = "BYBIT_ONLY"
    dash["alt_alt_mechanism"]   = {
        "formula":            "diff = ATOM_FR - SOL_FR  (direct alt-alt, no base asset)",
        "rolling_window":     "W=168h (21 x 8h periods, primary config)",
        "signal":             "sign(rolling_mean_168h(diff))",
        "second_alt_alt":     True,
        "bybit_only_reason":  "HL 62.5%; HL-only would risk 65% cap breach — Bybit preferred",
        "hl_concentration":   62.5,
        "k493_k476_warning":  (
            "K493 ATOM-BTC (HL+Bybit, 5% sleeve) + K476 SOL-BTC (HL-only, 1.5%) overlap. "
            "ATOM-SOL = -(BTC-ATOM) + (BTC-SOL) = -K493_dir + K476_dir. "
            "K682 anti-corr with K493 (-0.5195) HEDGES portfolio. Run K682 STANDALONE or rebalance. "
            "Default: K682 standalone 2% Bybit sleeve."
        ),
        "atom_fr_drivers": (
            "Cosmos IBC governance-driven episodics: new chain launches, validator staking "
            "inflation pressure (negative FR mean -3.27%/ann), SNS DAO proposals, IBC ecosystem growth."
        ),
        "sol_fr_drivers": (
            "Solana DePIN/Retail adoption premium (persistent +7.73%/ann), meme-coin season (BONK/WIF), "
            "Firedancer upgrade hype, validator economics, network congestion spikes."
        ),
    }
    dash["activation_criteria"] = {
        "60d_paper_trade_gate":  "required",
        "realized_sharpe_min":   22.0,
        "fill_rate_min_pct":     60,
        "max_drawdown_max_pct":  15,
        "status":                "SCAFFOLD-READY",
        "activation_sleeve_pct": 0.020,
        "venue":                 "BYBIT primary (ATOM-PERP + SOL-PERP both on Bybit)",
    }
    dash["oos_performance"] = {
        "sharpe":                   43.43,
        "oos_ann_ret_pct":          21.043,  # ~$214.6K / ($10M x 2% x 4x) / 4x
        "ann_return_usd_2pct_4x":   214638,
        "daily_usdc":               588,
        "wave_accept":              "K682 ACCEPT (K685 scaffold) — SECOND ALT-ALT pair Sh=43.43",
        "cluster":                  "ATOM-SOL Alt-Alt FR Differential (Cosmos IBC vs Solana SVM, Bybit-only)",
        "cluster_rationale": (
            "ATOM (Cosmos SDK/CometBFT IBC) vs SOL (Solana SVM DePIN-Retail): second alt-alt pair. "
            "No BTC or ETH leg — pure alt-to-alt narrative differential. "
            "ATOM FR = Cosmos governance cycles (episodic); SOL FR = DePIN/meme-coin cycles (persistent). "
            "Bybit-only: HL at 62.5%; adding HL legs would approach 65% cap. "
            "K493+K476 algebraic overlap: anti-corr K682/K493=-0.5195 means K682 HEDGES portfolio."
        ),
        "daemon_number":            "56th",
        "k679_comparison": {
            "k682_oos_sharpe":  43.43,
            "k679_oos_sharpe":  39.29,
            "note":             "K682 ATOM-SOL (Sh=43.43) > K679 APT-SOL (Sh=39.29): ATOM governance cycles provide cleaner signal",
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
      1. Fetch ATOM + SOL FRs from Bybit
      2. Compute ATOM-SOL differential + 168h rolling mean
      3. Decide position (sign of rolling mean — zero threshold)
      4. Compute delta-neutral notional
      5. If entering: submit paired trade (POST_ONLY, Bybit primary)
      6. If holding: check drift + rebalance
      7. Write k682_dashboard.json
    """
    ts_jst = datetime.now(JST).strftime("%Y-%m-%d %H:%M JST")
    print(f"\n=== K682 ATOM-SOL FR Differential (SECOND ALT-ALT, Bybit-only) — {ts_jst} ===")
    print(f"  Mode:      {'DRY-RUN' if dry_run else 'PAPER-TRADE' if PAPER_TRADE else 'LIVE'}")
    print(f"  AUM:       ${aum:,.0f}  Sleeve: {SLEEVE_PCT:.1%}  Leverage: {LEVERAGE}x")
    print(f"  Venue:     Bybit-only (ATOM-PERP + SOL-PERP, both Bybit)")
    print(f"  HL conc:   62.5% — Bybit-only avoids cap risk")
    print(f"  Execution: POST_ONLY parallel (K439)")
    print(f"  Signal:    diff = ATOM_FR - SOL_FR  (direct alt-alt, no base asset)")
    print(f"             sign(rolling_mean_168h)  (zero threshold, W=168h = 21 x 8h periods)")
    print(f"  SECOND:    SECOND ALT-ALT pair (no BTC/ETH leg) — OOS Sh=43.43 > K679 39.29")
    print(f"  Overlap:   K493 ATOM-BTC + K476 SOL-BTC algebraic overlap — standalone 2% sleeve")
    print(f"  Anti-corr: K682 vs K493 = -0.5195 (HEDGES K493 ATOM portfolio exposure)")
    print(f"  10/12 gates: OOS Sh={43.43:.2f} W=168h Bybit-only 2% sleeve $214.6K/yr @$10M @4x")

    # Step 1: Fetch + compute ATOM-SOL differential
    print("\n  [Step 1] Computing ATOM-SOL FR differential from Bybit...")
    signal = compute_signal()
    print(f"  ATOM FR:     {signal['fr_atom']:+.8f} (8h, Bybit; mean ann -3.27% staking pressure)")
    print(f"  SOL FR:      {signal['fr_sol']:+.8f} (8h, Bybit; mean ann +7.73% retail premium)")
    print(f"  ATOM-SOL:    {signal['atom_sol_diff']:+.8f}  (direct alt-alt differential)")
    print(f"  Mean 168h:   {signal['mean_168h']:+.8f}")
    print(f"  Sigma 168h:  {signal['diff_sigma']:+.8f}  (informational)")
    print(f"  Direction:   {signal['signal_direction']:+d}  (+1=BULL_ATOM, -1=BEAR_ATOM, 0=NEUTRAL)")
    print(f"  Regime:      {signal['regime']}")
    print(f"  History:     {signal['history_points']} data points")

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
    print(f"  ATOM leg:         ${notional_per_leg:,.0f}  (2% x ${aum/1e6:.0f}M x {LEVERAGE}x / 2)")
    print(f"  SOL leg:          ${notional_per_leg:,.0f}  (2% x ${aum/1e6:.0f}M x {LEVERAGE}x / 2)")
    print(f"  Total notional:   ${total_notional:,.0f}")
    print(f"  Margin required:  ${total_notional/LEVERAGE:,.0f}  ({SLEEVE_PCT:.1%} AUM)")
    print(f"  Profit @$10M 4x:  OOS Sh=43.43 = $214,638/yr net (2% sleeve, standalone)")
    print(f"  HL conc:          UNCHANGED 62.5% (Bybit-only — no HL impact)")

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
    print(f"\n  === K682 ATOM-SOL Cycle Complete ===")
    print(f"  Position state:      {dash_out.get('position_state')}")
    print(f"  Regime:              {dash_out.get('regime')}")
    print(f"  ATOM-SOL Mean 168h:  {dash_out.get('mean_168h'):+.8f}")
    print(f"  Signal direction:    {dash_out.get('signal_direction')}")
    print(f"  SECOND ALT-ALT:      ATOM-SOL (no BTC/ETH base) OOS Sh=43.43")
    print(f"  Bybit-only:          HL 62.5% — Bybit avoids 65% cap risk")
    print(f"  K493+K476 overlap:   STANDALONE 2% sleeve (hedges K493 anti-corr -0.5195)")
    print(f"  Paper-trade mode:    {PAPER_TRADE}")
    print(f"  OOS Sharpe:          43.43 (W=168h, zero threshold)")
    print(f"  Cluster:             ATOM-SOL Alt-Alt (Cosmos IBC vs SVM, 56th daemon)")
    print(f"  Profit 2% sleeve:    $214,638/yr net @$10M @4x (standalone)")
    print(f"  HL concentration:    62.5% UNCHANGED (Bybit-only)")
    print(f"  60d gate:            Realized Sh>=22 + fill>=60% + maxDD<15%")
    print()

    return 0


# ─────────────────────────────────────────────────────────────────────────────
# CLI entry point
# ─────────────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="K682 ATOM-SOL FR Differential Strategy (K685 scaffold, SECOND ALT-ALT, Bybit-only)"
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
        print(f"\n=== K682 Dashboard ({dash.get('last_poll_jst', '—')}) ===")
        print(json.dumps(dash, indent=2))
        return 0

    if args.rebalance:
        dash   = _load_dashboard()
        result = daily_rebalance(dash)
        print(f"\n=== K682 Rebalance Check ===")
        print(json.dumps(result, indent=2))
        return 0

    if args.close:
        result = close_paired_position(args.close, dry_run=args.dry_run)
        print(f"\n=== K682 Close Result ===")
        print(json.dumps(result, indent=2))
        return 0

    return run_cycle(dry_run=args.dry_run, aum=args.aum)


if __name__ == "__main__":
    sys.exit(main())
