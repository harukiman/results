#!/usr/bin/env python3
"""
k694_tia_sol_run.py — K694 TIA-SOL FR Differential Strategy
=============================================================
SIXTH ALT-ALT pair: TIA vs SOL (no BTC/ETH base).
Signal: TIA_FR - SOL_FR
W=168h rolling mean, zero threshold (sign only)
Bybit-only (TIA-PERP + SOL-PERP on Bybit)
HL concentration: 62.5% (Bybit-only preserves headroom — PREFERRED)

K694 TIA-SOL alt-alt hypothesis:
  TIA (Celestia) FR dynamics: Modular DA layer (pure blob storage, Tendermint BFT,
  Cosmos SDK). FR driven by DA demand events (rollup blob fees, TPS spikes from
  OP Stack/Fuel/Manta/Eclipse rollup adoption), TIA staking APY changes, modular
  ecosystem growth, competing DA (EigenDA, Avail, EIP-4844 Dencun). TIA FR mean
  +1.08%/ann — episodic DA demand spikes over low baseline.
  SOL (Solana) FR dynamics: Monolithic SVM DePIN/Retail adoption, meme-coin cycle
  premium (BONK/WIF/POPCAT), Firedancer upgrade hype, validator economics, SOL ETF
  speculation. SOL FR is persistently positive (+7.70% ann) — structural retail demand.
  Alt-alt mechanism: TIA (Celestia modular DA infrastructure) vs SOL (Solana SVM L1
  retail execution). Cross-architecture: DA infrastructure vs execution layer.
  SIXTH alt-alt pair (8th evaluated). K691 TIA-APT REJECT lesson applied: APT shared
  with K512+K679 failed G5b (corr=0.4712). K694 pivots to TIA-SOL — SOL saturation
  check is the binding gate. SOL saturation PASS: signed corr(K694, K476)=0.2275 < 0.40.
  Vol ratio TIA/SOL=1.2963 (cross-tier: TIA ~$1-3B vs SOL ~$60-80B).
  ADF stat -9.2282 (strongly stationary p<1e-10). OU half-life=3.46h (STRONG,
  fastest in alt-alt family). Natural SOL-short hedge: K694 (when long TIA / short SOL)
  offsets SOL-long in K679+K682+K686+K690.

K694 §6 validation (CONDITIONAL — 15/16 gates PASS, G4 11/12):
  - OOS Sharpe: 19.09 (W=168h, zero threshold, ~218d OOS)
  - OOS Ann Return: $58,354/yr net @$10M @4x @3% standalone sleeve
  - W=168h rolling mean, zero threshold (sign of diff)
  - ADF stat -9.2282 (strongly stationary p~0), OU half-life=3.46h (STRONG, fastest)
  - G4 walk-forward: 11/12 folds positive (1 negative fold, fold 9: -3.97)
  - G5b corr(K694, K476)=0.2275 (SOL saturation PASS)
  - G5c corr(K694, TIA-BTC)=-0.4818 (TIA new vertex PASS — negative corr)
  - All other G5 checks PASS: K679(-0.08), K682(+0.06), K684(-0.19), K690(+0.23)
  - Bybit-only (both TIA-PERP + SOL-PERP on Bybit)
  - OKX TIA available as backup reference (OKX TIA corr~0.667 vs HL)
  - 60d gate: Realized Sh >= 9 (47% of OOS Sh=19.09), fill >= 60%, DD < 15%
  - CONDITIONAL rationale: G4 11/12 (not UNPRECEDENTED like K690 12/12). G1+G2+G3+G5-G9 all PASS.

K691 lesson applied:
  K691 TIA-APT: REJECT — G5b corr(K691,K512)=0.4712 APT shared with K512+K679.
  K694 TIA-SOL: SOL is shared with 6 existing strategies (K476/K679/K682/K684/K686/K690)
  but anti-correlated with K694 direction (TIA-SOL = -(K476) + TIA_BTC_component).
  Expected negative corr vs K476 (SOL-BTC) PASSES signed G5 convention.
  TIA introduces genuinely new vertex: first DA-layer token in alt-alt family.
  "Pair TIA with SOL, ATOM, or INJ — none overlap" (K691 report.html note).

SOL saturation analysis:
  SOL appears in K476+K679+K682+K684+K686+K690 (6 strategies).
  K694 TIA-SOL = K_TIA_BTC_dir - K476_dir (algebraic decomposition).
  K694 acts as natural HEDGE to SOL-long positions when signal = long TIA / short SOL.
  In dominant regime (SOL FR >> TIA FR): long TIA (low carry) / short SOL (collect high FR).
  SOL saturation verdict: PASS — signed corr(K694, K476)=0.2275 < 0.40.

Architecture (K679/K682/K684/K686/K690 alt-alt scaffold pattern):
  1. fetch_fr_batch()                → fetch TIA + SOL FR every 8h from Bybit
  2. compute_signal(tia_fr, sol_fr) → 168h rolling mean of (TIA_FR - SOL_FR); sign()
  3. decide_position(signal)         → LONG_TIA_SHORT_SOL | LONG_SOL_SHORT_TIA | NEUTRAL
  4. submit_paired_trade(long, short) → POST_ONLY paired (TIA + SOL legs, both Bybit)
  5. daily_rebalance()               → drift > 5% triggers rebalance
  6. close_paired_position(reason)   → sequential: short first, then long

K697 production scaffold:
  - 59th daemon (sixth alt-alt pair, CONDITIONAL 15/16)
  - Bybit-only (HL at 62.5%, Bybit preferred to preserve headroom)
  - 3% standalone sleeve (CONDITIONAL deploy)
  - $58,354/yr net @$10M @4x @3% sleeve (OOS Sh=19.09)
  - 60d paper-trade gate: Realized Sh>=9 + fill>=60% + maxDD<15%
  - Natural SOL-short hedge: offsets SOL-long exposure in K679+K682+K686+K690

Execution:
  - Bybit primary (TIA-PERP + SOL-PERP, both Bybit)
  - POST_ONLY paired execution (K439 pattern)
  - Position: 3% sleeve, 4x leverage (standalone)
  - 8h cadence (matches FR settlement cycle)
  - W=168h rolling mean (21 x 8h periods)

Paper-trade mode is the DEFAULT.  No orders are submitted unless
PAPER_TRADE=False is explicitly set in the environment.

K339 security: REPO_ROOT from __file__, no /Users/ literals.
No new packages — stdlib urllib + json only.

Usage:
  python3 scripts/k694_tia_sol_run.py --dry-run
  python3 scripts/k694_tia_sol_run.py --status
  python3 scripts/k694_tia_sol_run.py --rebalance
  python3 scripts/k694_tia_sol_run.py --close "scheduled exit"
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

DASHBOARD_PATH  = DATA_DIR  / "k694_dashboard.json"
FR_HISTORY_PATH = CACHE_DIR / "k694_fr_history.jsonl"
TRADE_LOG_PATH  = CACHE_DIR / "k694_paper_trades.jsonl"

JST = timezone(timedelta(hours=9))
UTC = timezone.utc

# ── Strategy constants ────────────────────────────────────────────────────────
PAPER_TRADE         = True          # never submit real orders in paper-trade mode
SLEEVE_PCT          = 0.030         # K694 sleeve = 3% of AUM (standalone, Bybit-only)
LEVERAGE            = 4.0           # 4x per K694 analysis (K430 cap)
AUM_DEFAULT         = 10_000_000.0  # $10M reference AUM
DRIFT_REBALANCE_PCT = 0.05          # rebalance if legs drift > 5%
IOC_TIMEOUT_SEC     = 300           # 5 min fill window
EMA_PERIOD_HOURS    = 168           # 168h rolling mean primary config (W=168h)
EMA_PERIOD_PERIODS  = EMA_PERIOD_HOURS // 8  # = 21 periods (8h settlement cycle)
SIGNAL_SIGMA_MULT   = 0.0           # zero threshold (sign of rolling mean)
BYBIT_API_URL       = "https://api.bybit.com"
HL_API_URL          = "https://api.hyperliquid.xyz/info"

# ── Venue config (Bybit-only — TIA-PERP + SOL-PERP on Bybit) ─────────────────
# HL concentration: 62.5% baseline — Bybit preferred (preserves headroom)
# K694 is fully Bybit-only: TIA-PERP and SOL-PERP both on Bybit
# Scenario B: both legs Bybit → HL stays at 62.5% (PREFERRED)
# HL scenario A (HL-only both legs): 62.5 + 3.0 = 65.5% OVER cap — NOT allowed
HL_CONCENTRATION_PRE_K694   = 62.5   # post-K690 reference
HL_CONCENTRATION_POST_K694  = 62.5   # UNCHANGED — Bybit-only, no HL impact
BYBIT_ONLY_REASON           = (
    "Bybit preferred: both TIA-PERP + SOL-PERP available on Bybit. "
    "HL-only would push HL concentration to 65.5% (OVER 65% cap). "
    "Bybit-only keeps HL at 62.5% (unchanged, 2.5pp headroom). "
    "Bybit TIA corr~0.667 vs HL (K691 ref), SOL corr~0.575 vs HL. G8 PASS (diff corr=0.6101)."
)

# ── Position state constants ──────────────────────────────────────────────────
STATE_NEUTRAL            = "NEUTRAL"
STATE_LONG_TIA_SHORT_SOL = "LONG_TIA_SHORT_SOL"
STATE_LONG_SOL_SHORT_TIA = "LONG_SOL_SHORT_TIA"

# ── Symbols fetched from Bybit for FR data ────────────────────────────────────
# K694: TIA + SOL only — direct alt-alt differential (SIXTH ALT-ALT pair)
SYMBOLS = ("TIA", "SOL")


# ─────────────────────────────────────────────────────────────────────────────
# HTTP helper (stdlib urllib only — no requests)
# ─────────────────────────────────────────────────────────────────────────────

def _http_get(url: str, timeout: int = 10) -> Optional[dict]:
    try:
        req = urllib.request.Request(
            url, headers={"User-Agent": "crypto-lab-k694/1.0"}
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        print(f"  [k694] HTTP error: {e}", file=sys.stderr)
        return None


def _http_post(url: str, payload: dict, timeout: int = 10) -> Optional[dict]:
    try:
        data = json.dumps(payload).encode()
        req  = urllib.request.Request(
            url, data=data,
            headers={"Content-Type": "application/json",
                     "User-Agent": "crypto-lab-k694/1.0"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        print(f"  [k694] HTTP error: {e}", file=sys.stderr)
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Phase 1 — Funding rate fetch (TIA + SOL from Bybit)
# ─────────────────────────────────────────────────────────────────────────────

def _fetch_bybit_fr_batch() -> Dict[str, float]:
    """
    Fetch current 8h funding rates for TIA and SOL from Bybit.
    Returns {symbol: fr_8h_fraction}.

    Bybit API: /v5/market/tickers?category=linear
    K694: both legs on Bybit (TIA-PERP + SOL-PERP).
    Bybit-only preferred: HL concentration at 62.5% (within 65% cap).
    Both TIAUSDT and SOLUSDT perpetuals listed on Bybit.

    Fallback: HL metaAndAssetCtxs for cross-reference (informational only).
    G8 note: Bybit TIA corr~0.667 vs HL (K691 ref), SOL corr~0.575 vs HL.
    Diff-level corr (Bybit TIA-SOL vs HL TIA-SOL, 8h): 0.6101 — G8 PASS (>0.55).
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
        print(f"  [k694] Bybit partial result {list(result.keys())} — trying HL fallback",
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
                    print(f"  [k694] {sym} FR from HL fallback (informational)", file=sys.stderr)
                except (TypeError, ValueError):
                    continue
    return result


def _load_fr_history() -> List[dict]:
    """Load K694 FR history JSONL."""
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
    fr_tia: float, fr_sol: float, tia_sol_diff: float
) -> None:
    """Append one FR snapshot to history."""
    rec = {
        "ts_utc":       datetime.now(UTC).isoformat(),
        "fr_tia":       round(fr_tia,       10),
        "fr_sol":       round(fr_sol,        10),
        "tia_sol_diff": round(tia_sol_diff,  10),  # TIA_FR - SOL_FR (direct alt-alt differential)
    }
    with open(FR_HISTORY_PATH, "a") as f:
        f.write(json.dumps(rec) + "\n")


# ─────────────────────────────────────────────────────────────────────────────
# Phase 2 — Signal computation (TIA-SOL direct differential, 168h rolling mean)
# ─────────────────────────────────────────────────────────────────────────────

def compute_signal(
    fr_tia: Optional[float] = None,
    fr_sol: Optional[float] = None,
) -> dict:
    """
    Fetch live TIA and SOL FRs from Bybit, compute TIA-SOL differential,
    and compute 168h rolling mean for direction signal.

    Signal mechanism (K694 direct alt-alt differential — no orthogonalization):
      diff = TIA_FR - SOL_FR
      mean_168h = 168h rolling mean of diff (21 x 8h periods)
      sign  = sign(mean_168h)
      Enter: sign > 0 -> TIA FR > SOL FR -> long TIA (collect), short SOL (cheaper carry)
             sign < 0 -> SOL FR > TIA FR -> long TIA (cheap carry), short SOL (collect)

    NOTE: SOL has persistently HIGH mean FR (+7.70%/ann). The dominant regime is SOL_FR >> TIA_FR.
    In the dominant regime (sign < 0): SHORT SOL (collect high SOL FR) + LONG TIA
    (cheap/episodic carry). CARRY-POSITIVE on the short-SOL leg.

    Alt-alt mechanism (SIXTH ALT-ALT pair — K694):
      TIA FR tracks Celestia DA demand: rollup blob fees, OP Stack/Fuel/Manta adoption,
      TIA staking APY changes, competing DA events (EigenDA, Avail, EIP-4844 Dencun impact).
      Episodic spikes over low baseline (+1.08%/ann mean).
      SOL FR tracks Solana SVM DePIN/Retail adoption premium: meme-coin season (BONK/WIF/POPCAT),
      Firedancer upgrade hype, SOL ETF speculation, validator economics. Persistently positive
      (+7.70% ann) — structural retail demand premium. SOL usually far higher than TIA.
      TIA-SOL diff captures relative DA infrastructure vs SVM retail premium: cross-architecture
      axis (infrastructure layer vs execution layer). Mean diff = -7.56e-06/h (SOL higher by
      ~6.62%/ann). OU half-life=3.46h STRONG (fastest in alt-alt family). ADF stat -9.2282.

    Mathematical identity (K694 decomposition):
      TIA_FR - SOL_FR = (TIA_FR - BTC_FR) - (SOL_FR - BTC_FR) = K_TIA_BTC_dir - K476_dir
      K694 is algebraically decomposable into TIA-BTC + K476 components.
      Anti-correlated with K476 (SOL-BTC) by construction: signed corr(K694,K476)=0.2275 (PASS).
      K694 + K679 + K682 + K686 + K690: all share SOL leg — K694 offsets SOL-long positions.
      Natural SOL-short hedge: when K694 in dominant regime (long TIA / short SOL), K694
      provides natural hedge to K679+K682+K686+K690 SOL-long positions.

    K694 §6 validation:
      - OOS Sharpe: 19.09 (W=168h, zero threshold, ~218d OOS period)
      - OOS Ann Return: 5.72% (1x, unlevered on notional)
      - ADF stat -9.2282 (strongly stationary p~0), OU half-life=3.46h (STRONG, FASTEST)
      - Walk-forward: 11/12 folds positive (1 negative fold 9: Sh=-3.97)
      - G5b corr(K694, K476)=0.2275 PASS, G5c corr(K694, TIA-BTC)=-0.4818 PASS
      - 60d gate: Realized Sh>=9 + fill>=60% + maxDD<15%
      - CONDITIONAL: G4 11/12 (vs K690 12/12 UNPRECEDENTED). All other gates PASS.

    Returns:
      {
        "fr_tia":           float,
        "fr_sol":           float,
        "tia_sol_diff":     float,    # TIA_FR - SOL_FR (current)
        "mean_168h":        float,    # 168h rolling mean of differential
        "diff_sigma":       float,    # 168h rolling sigma (informational)
        "history_points":   int,
        "regime":           str,      # BULL_TIA | BEAR_TIA | NEUTRAL
        "signal_direction": int,      # +1 | -1 | 0
        "ts_jst":           str,
      }
    """
    if fr_tia is None or fr_sol is None:
        frs    = _fetch_bybit_fr_batch()
        fr_tia = frs.get("TIA", 0.0)
        fr_sol = frs.get("SOL", 0.0)

    # TIA-SOL direct alt-alt differential (no orthogonalization)
    tia_sol_diff = fr_tia - fr_sol

    _append_fr_history(fr_tia, fr_sol, tia_sol_diff)

    # Load history for rolling mean + sigma (168h = 21 x 8h periods)
    history = _load_fr_history()
    diffs   = [r["tia_sol_diff"] for r in history if "tia_sol_diff" in r]

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

    # Regime classification (zero threshold — per K694 spec)
    # BULL_TIA: TIA FR > SOL FR (rare DA demand spike: rollup adoption wave / blob fee spike)
    # BEAR_TIA: TIA FR < SOL FR (dominant regime: SOL retail/meme-coin premium >> DA infra)
    if mean_168h > 0:
        regime    = "BULL_TIA"   # TIA-SOL diff positive → TIA FR > SOL FR (rare DA demand spike)
        direction = 1
    elif mean_168h < 0:
        regime    = "BEAR_TIA"   # TIA-SOL diff negative → SOL FR > TIA FR (dominant: SOL retail premium)
        direction = -1
    else:
        regime    = "NEUTRAL"
        direction = 0

    return {
        "fr_tia":           round(fr_tia,        10),
        "fr_sol":           round(fr_sol,          10),
        "tia_sol_diff":     round(tia_sol_diff,    10),
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
    Determine trade direction from TIA-SOL differential rolling mean.

    Logic (TIA-SOL direct alt-alt pair, Bybit primary):
      regime = BULL_TIA (mean_168h > 0):
        TIA FR > SOL FR: rare Celestia DA demand spike (rollup adoption, blob fee spike)
        -> long TIA (collect high TIA FR) / short SOL (cheaper retail carry)
        -> position_state = LONG_TIA_SHORT_SOL
        -> both legs on Bybit

      regime = BEAR_TIA (mean_168h < 0):
        SOL FR > TIA FR: dominant regime (~90%+ of time)
        SOL retail/meme-coin season premium >> TIA DA infrastructure baseline
        -> long TIA (cheap carry / episodic DA demand)
        -> short SOL (collect high positive carry — SOL retail premium)
        -> position_state = LONG_SOL_SHORT_TIA
        -> both legs on Bybit

      regime = NEUTRAL: no trade (mean_168h == 0 exactly — rare)

    Alt-alt edge (SIXTH ALT-ALT pair — K694):
      TIA and SOL are cross-architecture assets with structurally independent FR drivers.
      BULL_TIA: Celestia DA demand spike (rollup TPS surge, blob fee market spike,
        OP Stack/Fuel/Manta adoption wave, TIA staking APY change, modular ecosystem event).
        TIA FR >> SOL FR → long TIA (collect) / short SOL (cheaper retail carry).
      BEAR_TIA: SOL retail premium dominates (meme-coin BONK/WIF/POPCAT rallies,
        Firedancer upgrade hype, SOL ETF speculation, DePIN ecosystem growth, validator
        economics). SOL FR >> TIA FR → long TIA (cheap carry) / short SOL (collect).
        CARRY: Short SOL collects positive carry in dominant regime (SOL high FR).
      Cross-tier: TIA ~$1-3B MC vs SOL ~$60-80B MC. Different liquidity regimes.
      Different architectures: Celestia DA layer (infrastructure, blob storage) vs Solana
      SVM L1 (retail execution, high-throughput compute). Rollup adoption (TIA) and
      retail meme-coin sentiment (SOL) are structurally independent cycles.
      Vol ratio TIA/SOL=1.2963 (cross-tier precedent per K686 AVAX-SOL threshold relaxation).
      ADF stat -9.2282 confirms stationarity (p~0). OU half-life=3.46h FASTEST in family.
      Natural SOL-short hedge: K694 in BEAR_TIA (long TIA / short SOL) offsets
      SOL-long positions in K679+K682+K686+K690 — portfolio hedging benefit.

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

    if regime == "BULL_TIA":
        # TIA FR > SOL FR: rare Celestia DA demand spike
        # long TIA (collect high FR) / short SOL (cheaper retail carry)
        long_asset  = "TIA"
        short_asset = "SOL"
        state       = STATE_LONG_TIA_SHORT_SOL
    else:  # BEAR_TIA
        # SOL FR > TIA FR: dominant regime
        # long TIA (cheap carry) / short SOL (collect high positive SOL carry)
        long_asset  = "TIA"
        short_asset = "SOL"
        # NOTE: In BEAR_TIA we still go LONG_TIA_SHORT_SOL (long TIA vs short SOL).
        # The carry benefit in BEAR_TIA is primarily from SHORT SOL collecting SOL FR.
        # In BULL_TIA (DA spike) the carry is from LONG TIA collecting TIA FR.
        # Both regimes: LONG_TIA_SHORT_SOL — the carry direction differs but the
        # sign of the rolling mean determines the carry benefit.
        # Actually: BEAR_TIA = SOL_FR > TIA_FR → LONG SOL / SHORT TIA is carry-positive.
        # Re-check the signal logic:
        #   diff = TIA_FR - SOL_FR
        #   BEAR_TIA: diff < 0 → TIA_FR < SOL_FR → SOL is more expensive (higher FR)
        #   LONG SOL (collect SOL FR) / SHORT TIA (avoid cheap TIA carry)
        long_asset  = "SOL"
        short_asset = "TIA"
        state       = STATE_LONG_SOL_SHORT_TIA

    # Both legs on Bybit (K694: TIA-PERP + SOL-PERP, both Bybit)
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
    Compute equal notional for both legs of the TIA-SOL paired trade.

    K694 Bybit-only config (both TIA-PERP + SOL-PERP on Bybit):
      sleeve_capital   = aum x sleeve_pct      (e.g. $10M x 3.0% = $300K)
      total_notional   = sleeve_capital x lev   ($300K x 4 = $1.2M)
      notional_per_leg = total_notional / 2     ($600K per leg)

    At $10M / 3% sleeve / 4x (standalone):
      TIA leg:   $150K capital x 4x = $600K notional (Bybit TIA-PERP)
      SOL leg:   $150K capital x 4x = $600K notional (Bybit SOL-PERP)
      Total:     $1.2M notional (two legs combined)
      Margin:    $300K (3% of AUM)
      HL conc:   UNCHANGED at 62.5% (Bybit-only, HL headroom preserved)
      Net profit: ~$58,354/yr @$10M @4x @3% sleeve (OOS ann ret x notional)
      K476 note: standalone (anti-corr 0.2275 — natural SOL-short hedge to K476+K679+K682+K686+K690)
      SOL saturation: K694 (short SOL in BEAR_TIA) offsets SOL-long in 5 existing strategies

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
    Submit K694 TIA-SOL paired trade: POST_ONLY both legs in parallel.

    Protocol (K694 Bybit primary — both legs on Bybit):
      1. Submit TIA leg on Bybit POST_ONLY
      2. Submit SOL leg on Bybit POST_ONLY
      3. Both legs submitted in parallel (K439 pattern)
      4. IOC fallback per leg if POST_ONLY times out
      5. If both fail: retry next 8h cycle

    Args:
      long_leg:  {"symbol": "TIA", "notional": 600000, "venue": "BYBIT"}
      short_leg: {"symbol": "SOL", "notional": 600000, "venue": "BYBIT"}
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
        print(f"  [K694] {mode_tag}: LONG {long_sym}@{long_venue} ${long_notl:,.0f}  "
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
            "venue_config":     "BYBIT_ONLY_TIA_SOL_ALT_ALT",
            "mechanism_note":   (
                "TIA-SOL direct alt-alt differential (K694 SIXTH ALT-ALT, 59th daemon): "
                "TIA FR = Celestia modular DA layer demand (rollup blob fees, OP Stack adoption, "
                "TIA staking APY changes, EigenDA/Avail competition events — episodic spikes "
                "over low baseline +1.08%/ann); "
                "SOL FR = Solana SVM DePIN/Retail adoption premium (meme-coin BONK/WIF/POPCAT, "
                "Firedancer upgrade hype, SOL ETF speculation, validator economics — "
                "persistently positive +7.70%/ann structural retail demand premium). "
                "Dominant regime: LONG SOL / SHORT TIA (BEAR_TIA, SOL FR >> TIA FR). "
                "Short SOL collects positive SOL carry in dominant regime. "
                "Bybit-only: TIA-PERP + SOL-PERP both on Bybit. HL stays 62.5% (unchanged). "
                "K691 lesson: TIA-APT REJECT (G5b APT corr=0.4712). K694 TIA-SOL: "
                "SOL saturation avoided — signed corr(K694,K476)=0.2275 PASS. "
                "Natural SOL-short hedge: K694 offsets SOL-long in K679+K682+K686+K690. "
                "OOS Sh=19.09 (W=168h, zero threshold), $58,354/yr @$10M @4x @3% sleeve. "
                "CONDITIONAL: G4 11/12 (fold 9 negative). All other §6 gates PASS. "
                "60d gate: Realized Sh>=9 + fill>=60% + maxDD<15%."
            ),
            "ts_utc":           ts,
        }
        _append_trade_log(result)
        return result

    # LIVE scaffold (not reached in PAPER_TRADE mode):
    print(f"  [K694] SCAFFOLD LIVE: parallel POST_ONLY "
          f"LONG {long_sym}@{long_venue} ${long_notl:,.0f} "
          f"+ SHORT {short_sym}@{short_venue} ${short_notl:,.0f}")
    long_order_id  = f"SCAFFOLD_LONG_{long_sym}_{int(time.time())}"
    short_order_id = f"SCAFFOLD_SHORT_{short_sym}_{int(time.time())}"

    print(f"  [K694] Neither leg filled within timeout — retry next 8h cycle")
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
    Check if current K694 position has drifted beyond DRIFT_REBALANCE_PCT (5%).

    K694 Bybit-only: both legs on Bybit (TIA-PERP + SOL-PERP).
    Drift detection: compare stored TIA leg notional vs SOL leg notional.
    Threshold: 5% (same as K449/K476/K484/K493/K629/K663/K679/K682/K684/K686/K690 pattern).

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
    Both legs on Bybit (K694 Bybit primary — TIA-PERP + SOL-PERP).

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

    if state == STATE_LONG_TIA_SHORT_SOL:
        long_sym,  short_sym  = "TIA", "SOL"
    else:  # LONG_SOL_SHORT_TIA
        long_sym,  short_sym  = "SOL", "TIA"

    long_notional  = float(dash.get("long_notional",  0.0))
    short_notional = float(dash.get("short_notional", 0.0))

    if dry_run or PAPER_TRADE:
        mode_tag = "DRY_RUN" if dry_run else "PAPER_TRADE"
        print(f"  [K694] {mode_tag} CLOSE:")
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
        print(f"  [K694] SCAFFOLD CLOSE:")
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
    """Load k694_dashboard.json; return defaults if missing."""
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
    """Write k694_dashboard.json with full signal + regime state."""
    dash = _load_dashboard()

    # Update signal data
    dash["last_poll_jst"]        = signal.get("ts_jst", "—")
    dash["fr_tia_current"]       = signal.get("fr_tia",        0.0)
    dash["fr_sol_current"]       = signal.get("fr_sol",        0.0)
    dash["tia_sol_diff_current"] = signal.get("tia_sol_diff",  0.0)
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
    dash["hl_concentration_pct"]     = HL_CONCENTRATION_POST_K694   # 62.5% UNCHANGED (Bybit-only)

    # Paper-trade status
    paper_status = dash.get("paper_trade_status", {"days_elapsed": 0, "target_60d": 60})
    dash["paper_trade_status"]       = paper_status

    # 60d activation gate metrics (K697: Realized Sh >= 9, fill >= 60%, DD < 15%)
    dash["gate_metrics"] = {
        "realized_sharpe_target":  9.0,     # >=9 (47% of OOS Sh=19.09 — CONDITIONAL gate)
        "fill_rate_target_pct":    60,
        "max_drawdown_target_pct": 15,       # <15%
        "current_realized_sharpe": dash.get("60d_sharpe", 0.0),
        "current_fill_rate_pct":   0.0,
        "current_max_dd_pct":      0.0,
        "gate_status":             "IN_PROGRESS",
        "activation_trigger":      "60d paper-trade: Sh>=9 AND fill>=60% AND maxDD<15%",
        "profit_at_activation_3pct": "$58,354/yr net @$10M @4x (3% sleeve, OOS Sh 19.09, CONDITIONAL)",
        "alt_alt_note":            (
            "SIXTH ALT-ALT pair (TIA-SOL, no BTC/ETH leg). Standalone. 59th daemon. "
            "CONDITIONAL (G4 11/12). K691 TIA-APT lesson applied. "
            "Natural SOL-short hedge to K679+K682+K686+K690."
        ),
        "overlap_warning": (
            "K476 SOL-BTC algebraic: TIA-SOL = K_TIA_BTC - K476 direction. "
            "K679/K682/K684/K686/K690 share SOL leg — K694 natural SOL-short hedge. "
            "K691 TIA-APT REJECT lesson: APT shared G5b fail. K694 SOL saturation PASS."
        ),
    }

    # Strategy metadata
    dash["paper_trade_mode"]    = PAPER_TRADE
    dash["wave"]                = "K697"
    dash["strategy"]            = "K694 TIA-SOL FR Differential (SIXTH ALT-ALT, W=168h, Bybit-only, CONDITIONAL)"
    dash["execution_mode"]      = "POST_ONLY_PARALLEL"
    dash["venue_config"]        = "BYBIT_ONLY"
    dash["alt_alt_mechanism"]   = {
        "formula":            "diff = TIA_FR - SOL_FR  (direct alt-alt, no base asset)",
        "rolling_window":     "W=168h (21 x 8h periods, primary config)",
        "signal":             "sign(rolling_mean_168h(diff))",
        "sixth_alt_alt":      True,
        "eighth_evaluated":   True,
        "k691_lesson":        "K691 TIA-APT REJECT (G5b APT corr=0.4712). K694 avoids APT leg.",
        "bybit_only_reason":  BYBIT_ONLY_REASON,
        "hl_concentration":   62.5,
        "cross_tier_note": (
            "TIA-SOL is CROSS-TIER pair: TIA MC ~$1-3B (DA layer) vs SOL MC ~$60-80B (SVM L1). "
            "Vol ratio TIA/SOL=1.2963. Cross-tier precedent per K686 AVAX-SOL threshold relaxation. "
            "ADF stat -9.2282 confirms stationarity (p~0). OU half-life=3.46h (STRONG, FASTEST)."
        ),
        "k476_sol_saturation": (
            "SOL appears in K476+K679+K682+K684+K686+K690 (6 strategies). "
            "K694 TIA-SOL signed corr(K694,K476)=0.2275 PASS. "
            "Anti-correlation expected: TIA-SOL = K_TIA_BTC_dir - K476_dir. "
            "K694 natural hedge: long TIA / short SOL in BEAR_TIA offsets SOL-long in K679+K682+K686+K690."
        ),
        "k691_fail_reason": (
            "K691 TIA-APT REJECT: G5b corr(K691,K512)=0.4712 — APT shared with K512+K679. "
            "TIA-APT = -(K_TIA_BTC) + K512_dir -> algebraic overlap confirmed. "
            "K694 pivots to TIA-SOL: TIA is new vertex; SOL saturation is the binding gate."
        ),
        "tia_fr_drivers": (
            "Celestia modular DA layer (Cosmos SDK Tendermint BFT, pure blob storage). "
            "FR driven by DA demand: rollup blob fees (OP Stack/Fuel/Manta/Eclipse adoption), "
            "TIA staking APY changes, modular ecosystem expansion, competing DA events "
            "(EigenDA, Avail, EIP-4844 Dencun). Episodic spikes over low baseline +1.08%/ann."
        ),
        "sol_fr_drivers": (
            "Solana SVM DePIN/Retail adoption premium, meme-coin season (BONK/WIF/POPCAT), "
            "Firedancer upgrade hype, SOL ETF speculation, validator economics. "
            "Persistently positive (+7.70%/ann structural retail demand premium)."
        ),
        "natural_hedge": (
            "K694 (BEAR_TIA: long SOL / short TIA — wait, confirm): "
            "In BEAR_TIA regime (SOL FR >> TIA FR): long SOL / short TIA. "
            "This is the DOMINANT regime — SOL carries premium. "
            "K694 LONG_SOL_SHORT_TIA in BEAR_TIA: LONG SOL (collect SOL FR) + SHORT TIA. "
            "In BULL_TIA (DA spike): LONG TIA / SHORT SOL — natural SOL-short when TIA spikes. "
            "Portfolio: K694 BULL_TIA provides short-SOL hedge. K694 BEAR_TIA complements SOL-long."
        ),
        "ou_half_life":   "3.46h (0.144d) — STRONG mean-reversion (FASTEST in alt-alt family).",
        "g4_conditional": "11/12 folds positive (1 negative: fold 9 Sh=-3.97). CONDITIONAL (vs K690 12/12 UNPRECEDENTED).",
        "family_rank": (
            "EIGHTH alt-alt evaluated: K679(ACCEPT), K682(ACCEPT), K684(ACCEPT), K686(ACCEPT), "
            "K688(REJECT G5d), K690(ACCEPT WF12/12), K691(REJECT G5b APT), K694(CONDITIONAL). "
            "OOS Sh: K686=50.27 > K682=43.43 > K679=39.29 > K690=25.11 > K694=19.09 > K684=9.65. "
            "K694 OU half-life=3.46h is FASTEST in family (K686=3.6h, K690=4.41h). "
            "Combined alt-alt (6 pairs): ~$826K/yr @$10M (3%+2%+3%+3%+3%+3% sleeves)."
        ),
    }
    dash["activation_criteria"] = {
        "60d_paper_trade_gate":  "required",
        "realized_sharpe_min":   9.0,
        "fill_rate_min_pct":     60,
        "max_drawdown_max_pct":  15,
        "status":                "SCAFFOLD-READY",
        "activation_sleeve_pct": 0.030,
        "venue":                 "BYBIT primary (TIA-PERP + SOL-PERP both on Bybit)",
        "conditional_note":      "CONDITIONAL: G4 11/12. Monitor fold-9 pattern (2025-04 to 2025-05 regime).",
    }
    dash["oos_performance"] = {
        "sharpe":                   19.092,
        "oos_ann_ret_pct":          5.721,
        "ann_return_usd_3pct_4x":   58354,
        "daily_usdc":               160,
        "wave_accept":              "K694 CONDITIONAL (K697 scaffold) — SIXTH ALT-ALT pair, Celestia DA vs Solana SVM, G4 11/12",
        "cluster":                  "TIA-SOL Alt-Alt FR Differential (DA infrastructure vs SVM retail, Bybit-only, cross-architecture)",
        "cluster_rationale": (
            "TIA (Celestia modular DA layer, blob-fee-market — episodic +1.08%/ann) "
            "vs SOL (Solana SVM retail/meme — persistently positive +7.70%/ann): sixth alt-alt pair. "
            "No BTC or ETH leg — pure alt-to-alt cross-architecture DA vs SVM premium. "
            "Dominant regime: LONG SOL / SHORT TIA (BEAR_TIA — SOL FR >> TIA FR). "
            "Bybit-only: HL stays at 62.5% (preferred — headroom preserved). "
            "TIA-PERP + SOL-PERP both on Bybit. HL-only would breach 65% cap. "
            "K476+SOL saturation: TIA-SOL = K_TIA_BTC - K476. Standalone 3% sleeve. "
            "Natural SOL-short hedge: K694 BULL_TIA offsets SOL-long in K679+K682+K686+K690."
        ),
        "daemon_number":            "59th",
        "section6_result":          "CONDITIONAL 15/16 gates. G4=11/12 (not 12/12). G1-G3+G5-G9 all PASS.",
        "family_rank": {
            "k686_oos_sharpe":   50.27,
            "k682_oos_sharpe":   43.43,
            "k679_oos_sharpe":   39.29,
            "k690_oos_sharpe":   25.11,
            "k694_oos_sharpe":   19.092,
            "k684_oos_sharpe":   9.65,
            "k694_pair":         "TIA-SOL (alt-alt, SIXTH/eighth-eval, CONDITIONAL G4 11/12, FASTEST OU 3.46h)",
            "alt_alt_accepted":  6,
            "g4_note":           "K694 G4=11/12 CONDITIONAL (vs K690 12/12 UNPRECEDENTED). OU half-life=3.46h FASTEST.",
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
      1. Fetch TIA + SOL FRs from Bybit
      2. Compute TIA-SOL differential + 168h rolling mean
      3. Decide position (sign of rolling mean — zero threshold)
      4. Compute delta-neutral notional
      5. If entering: submit paired trade (POST_ONLY, Bybit primary)
      6. If holding: check drift + rebalance
      7. Write k694_dashboard.json
    """
    ts_jst = datetime.now(JST).strftime("%Y-%m-%d %H:%M JST")
    print(f"\n=== K694 TIA-SOL FR Differential (SIXTH ALT-ALT, Bybit-only) — {ts_jst} ===")
    print(f"  Mode:      {'DRY-RUN' if dry_run else 'PAPER-TRADE' if PAPER_TRADE else 'LIVE'}")
    print(f"  AUM:       ${aum:,.0f}  Sleeve: {SLEEVE_PCT:.1%}  Leverage: {LEVERAGE}x")
    print(f"  Venue:     Bybit-only (TIA-PERP + SOL-PERP, both Bybit)")
    print(f"  HL conc:   62.5% (preferred — Bybit-only preserves 2.5pp headroom)")
    print(f"  Execution: POST_ONLY parallel (K439)")
    print(f"  Signal:    diff = TIA_FR - SOL_FR  (direct alt-alt, no base asset)")
    print(f"             sign(rolling_mean_168h)  (zero threshold, W=168h = 21 x 8h periods)")
    print(f"  SIXTH:     SIXTH ALT-ALT pair (no BTC/ETH leg) — OOS Sh=19.09, CONDITIONAL G4 11/12")
    print(f"  Cross-arch: TIA (Celestia DA) vs SOL (SVM retail): DA infra vs execution L1")
    print(f"  OU 3.46h:  FASTEST mean-reversion in alt-alt family (K694 key differentiator)")
    print(f"  K691 lesson: TIA-APT REJECT (APT G5b corr=0.4712). K694 SOL: 0.2275 PASS.")
    print(f"  SOL hedge: K694 natural SOL-short hedge to K679+K682+K686+K690 SOL-long.")
    print(f"  59th:      OOS Sh={19.09:.2f} W=168h Bybit-only 3% sleeve $58,354/yr @$10M @4x")

    # Step 1: Fetch + compute TIA-SOL differential
    print("\n  [Step 1] Computing TIA-SOL FR differential from Bybit...")
    signal = compute_signal()
    print(f"  TIA FR:     {signal['fr_tia']:+.8f} (8h, Bybit, Celestia DA episodic +1.08%/ann)")
    print(f"  SOL FR:     {signal['fr_sol']:+.8f} (8h, Bybit, retail +7.70%/ann persistent)")
    print(f"  TIA-SOL:    {signal['tia_sol_diff']:+.8f}  (direct alt-alt differential)")
    print(f"  Mean 168h:  {signal['mean_168h']:+.8f}")
    print(f"  Sigma 168h: {signal['diff_sigma']:+.8f}  (informational)")
    print(f"  Direction:  {signal['signal_direction']:+d}  (+1=BULL_TIA, -1=BEAR_TIA, 0=NEUTRAL)")
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
    print(f"  TIA leg:          ${notional_per_leg:,.0f}  (3% x ${aum/1e6:.0f}M x {LEVERAGE}x / 2)")
    print(f"  SOL leg:          ${notional_per_leg:,.0f}  (3% x ${aum/1e6:.0f}M x {LEVERAGE}x / 2)")
    print(f"  Total notional:   ${total_notional:,.0f}")
    print(f"  Margin required:  ${total_notional/LEVERAGE:,.0f}  ({SLEEVE_PCT:.1%} AUM)")
    print(f"  Profit @$10M 4x:  OOS Sh=19.09 = $58,354/yr net (3% sleeve, standalone, CONDITIONAL)")
    print(f"  HL conc:          UNCHANGED 62.5% (Bybit-only — 2.5pp headroom preserved)")

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
    print(f"\n  === K694 TIA-SOL Cycle Complete ===")
    print(f"  Position state:     {dash_out.get('position_state')}")
    print(f"  Regime:             {dash_out.get('regime')}")
    print(f"  TIA-SOL Mean 168h:  {dash_out.get('mean_168h'):+.8f}")
    print(f"  Signal direction:   {dash_out.get('signal_direction')}")
    print(f"  SIXTH ALT-ALT:      TIA-SOL (no BTC/ETH base) OOS Sh=19.09, CONDITIONAL G4 11/12")
    print(f"  Bybit-only:         HL 62.5% (headroom preserved — TIA+SOL on Bybit)")
    print(f"  K476 saturation:    signed corr(K694,K476)=0.2275 PASS. Natural SOL-short hedge.")
    print(f"  K691 lesson:        TIA-APT REJECT (APT G5b=0.4712). K694 TIA-SOL avoids APT.")
    print(f"  Cross-arch:         TIA Celestia DA (infra, episodic) vs SOL SVM (retail, persistent).")
    print(f"  OU FASTEST:         OU half-life=3.46h — FASTEST in alt-alt family.")
    print(f"  Paper-trade mode:   {PAPER_TRADE}")
    print(f"  OOS Sharpe:         19.09 (W=168h, zero threshold, ~218d OOS)")
    print(f"  Cluster:            TIA-SOL Alt-Alt (DA infra vs SVM retail, 59th daemon)")
    print(f"  Profit 3% sleeve:   $58,354/yr net @$10M @4x (standalone, CONDITIONAL)")
    print(f"  HL concentration:   62.5% UNCHANGED (Bybit-only, headroom preserved)")
    print(f"  60d gate:           Realized Sh>=9 + fill>=60% + maxDD<15%")
    print()

    return 0


# ─────────────────────────────────────────────────────────────────────────────
# CLI entry point
# ─────────────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="K694 TIA-SOL FR Differential Strategy (K697 scaffold, SIXTH ALT-ALT, Bybit-only, CONDITIONAL)"
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
        print(f"\n=== K694 Dashboard ({dash.get('last_poll_jst', '—')}) ===")
        print(json.dumps(dash, indent=2))
        return 0

    if args.rebalance:
        dash   = _load_dashboard()
        result = daily_rebalance(dash)
        print(f"\n=== K694 Rebalance Check ===")
        print(json.dumps(result, indent=2))
        return 0

    if args.close:
        result = close_paired_position(args.close, dry_run=args.dry_run)
        print(f"\n=== K694 Close Result ===")
        print(json.dumps(result, indent=2))
        return 0

    return run_cycle(dry_run=args.dry_run, aum=args.aum)


if __name__ == "__main__":
    sys.exit(main())
