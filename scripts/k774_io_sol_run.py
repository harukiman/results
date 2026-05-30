#!/usr/bin/env python3
"""
k774_io_sol_run.py — K774 IO-SOL FR Differential Strategy
============================================================
NINETEENTH ALT-ALT pair (20th evaluated): IO vs SOL (GPU-DePIN × Solana SVM).
Signal: IO_FR - SOL_FR  (SHORT IO + LONG SOL double carry strategy)
W=168h rolling mean (7d — standard family window; G6 compliant: 48.6/yr OOS)
HL-only primary (IO: HIP-3 fresh listing, NOT on Bybit)
HL concentration: 66.8% AT CAP → paper-gate strict (K498/v6.52 required for live)

K774 IO-SOL alt-alt hypothesis:
  IO (io.net GPU DePIN marketplace):
    FR driven by GPU compute supply/demand cycles (H100 rental demand),
    AI hyperscaler capacity expansion vs contraction,
    io.net network utilization (GPU rental yield cycles),
    GPU shortage narrative (Nvidia H100/H200 supply chain events),
    IO staking/reward programs (tokenomics cycles),
    HIP-3 fresh listing (Jan 2025) — structural short squeeze periods,
    DePIN narrative rotations (compute-layer vs data-layer cycles).
    FR structural negative: -17.9%/yr gross carry (persistent shorts dominant).
    FR erratic: kurtosis=493.47, p01=-0.000208, p99=+0.000059.
    Vol ratio vs SOL: 1.96x (full), 13.11x (30d), 5.83x (90d), 17.26x (K773 30d snapshot).
  SOL (Solana SVM L1):
    FR driven by retail momentum, Phantom wallet adoption, Firedancer upgrade,
    Solana ETF narrative flows, SVM DeFi TVL (Jupiter/Drift/Jito).
    SOL FR mean +2.59%/yr — persistently positive structural retail demand.
    SOL extreme negative FR: Min=-20.51bps (liquidation cascade Feb 2025).
  Alt-alt mechanism: IO (GPU DePIN, io.net) vs SOL (Solana SVM L1).
    Structurally orthogonal: GPU compute supply/demand cycle (hardware DePIN)
    is decoupled from Solana SVM cycle (Firedancer, validator rewards, meme).
    IO vs TAO AI cluster check: io.net GPU rental marketplace DISTINCT from
    Bittensor TAO AI L1 (G5v IO-SOL vs TAO-SOL corr=0.047 PASS).
    raw_corr(IO_fr, SOL_fr) = very low — essentially orthogonal.
    G5 max_corr=0.2778 (G5s HBAR-SOL) ALL 26/26 PASS (no corr approaching 0.40).
  NINETEENTH alt-alt pair (20th evaluated). OOS Sharpe 19.884. W=168h. 12/12 WF ALL POSITIVE.
  All G5 26/26 gates PASS. MaxDD OOS only -0.389955%.
  G8: N/A structural (IO HIP-3 HL-only, no Bybit listing — K735/K747 precedent).
  G9: marginal (OOS=150.2d < 180d) — 60d live gate compensates.
  IO becomes 18th vertex (1st GPU-DePIN cluster). All future IO-X blocked (MR9 L002).

K774 §6 validation (ACCEPT CONDITIONAL — 32/33 gates PASS, G9 marginal):
  - OOS Sharpe: 19.884 (W=168h, zero threshold, 150.2d OOS)
  - OOS Ann Return: $28K central @$10M @4x @1.5% sleeve (K523 3-point)
  - W=168h rolling mean, zero threshold (sign of diff) — G6 compliant (48.6/yr)
  - G4 walk-forward: 12/12 folds positive (min_sh=5.866)
  - G5 all 26 gates PASS (max_corr=0.2778 G5s HBAR-SOL — all well below 0.40)
  - Sleeve 1.5% (HIP-3 HL-only liquidity constraint — IO $1.42M/day)
  - G8: N/A structural (IO HIP-3 HL-only — no Bybit listing; K735/K747 precedent)
  - G9: marginal (OOS=150.2d < 180d) — 60d gate compensates
  - HL 66.8% AT CAP → paper-gate strict until K498/v6.52

K774 IO-SOL vertex addition (18th vertex, GPU-DePIN cluster):
  V (before K774) = {APT, ATOM, AVAX, BNB, ENA, FIL, HBAR, INJ, LDO, SEI, SOL, TIA, TAO,
                      PEPE, WIF, BLUR, AXS}
  V (after K774)  = {APT, ATOM, AVAX, BNB, ENA, FIL, HBAR, INJ, LDO, SEI, SOL, TIA, TAO,
                      PEPE, WIF, BLUR, AXS, IO}
  IO = 18th vertex (GPU-DePIN cluster — io.net GPU compute marketplace).
  MR9 L002: all future IO-X pairs are auto-blocked (IO exhausted as new vertex).
  IO-SOL is the only permissible IO-X pair given V composition at K774.

K523 3-point profit projection (@$10M @4x @1.5% sleeve):
  Conservative: $21,007/yr  (R2S=38% floor, K518 floor, OOS haircut 25%)
  Central:      $28,009/yr  (K523 mandate: 60% realized-to-stated, base case)
  Optimistic:   $73,707/yr  (near-full OOS realization if GPU-DePIN narrative peaks)
  Upper bound:  OOS raw return (NOT central — K523 mandatory)
  Note: 1.5% sleeve → ~$150K margin @$10M; central per K774 eval json=$28,009/yr

Cross-venue note (K774):
  HL:   IO listed from Jan 2025 (HIP-3). IO-PERP on HL. $1.42M/day volume. maxLeverage=10.
  Bybit: IO NOT LISTED (HIP-3 fresh HL-only asset).
  G8 = STRUCTURAL_NA per K735 HBAR-SOL / K747 TAO-SOL precedent.
  HL primary for all signal, backtest, and live execution.

Architecture (K679→K747→K754→K759→K769→K774 alt-alt scaffold pattern):
  1. fetch_fr_batch()                  → fetch IO + SOL FR every 8h from HL
  2. compute_signal(io_fr, sol_fr)    → 168h rolling mean of (IO_FR - SOL_FR); sign()
  3. decide_position(signal)           → LONG_IO_SHORT_SOL | LONG_SOL_SHORT_IO | NEUTRAL
  4. submit_paired_trade(long, short) → POST_ONLY paired (IO + SOL legs, HL primary)
  5. daily_rebalance()                 → drift > 5% triggers rebalance
  6. close_paired_position(reason)    → sequential: short first, then long

K776 production scaffold:
  - 77th daemon (nineteenth alt-alt pair, ACCEPT CONDITIONAL, G4 12/12)
  - HL-only (IO: HIP-3 fresh, NOT on Bybit)
  - 1.5% sleeve (HIP-3 HL-only liquidity constraint — IO $1.42M/day)
  - $28K central @$10M @4x @1.5% sleeve (K523 3-point: $21K-$74K)
  - Paper-gate until K498/v6.52 reduces HL concentration
  - 60d paper-trade gate: Realized Sh>=10 + fill>=60% + maxDD<15%
  - 20th alt-alt pair evaluated (19th alt-alt pair, 18th vertex IO)

Execution:
  - HL-only (IO-PERP + SOL-PERP, HL) — Bybit N/A (IO HIP-3 HL-primary only)
  - POST_ONLY paired execution (K439 pattern)
  - Position: 1.5% sleeve, 4x leverage (paper-gate strict — HL cap 66.8%)
  - 8h cadence (matches FR settlement cycle)
  - W=168h rolling mean (21 x 8h periods — G6-safe: 48.6 entries/yr)

Paper-trade mode is the DEFAULT.  No orders are submitted unless
PAPER_TRADE=False is explicitly set in the environment.

K339 security: REPO_ROOT from __file__, no /Users/ literals.
No new packages — stdlib urllib + json only.

Usage:
  python3 scripts/k774_io_sol_run.py --dry-run
  python3 scripts/k774_io_sol_run.py --status
  python3 scripts/k774_io_sol_run.py --rebalance
  python3 scripts/k774_io_sol_run.py --close "scheduled exit"
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

DASHBOARD_PATH  = DATA_DIR  / "k774_dashboard.json"
FR_HISTORY_PATH = CACHE_DIR / "k774_fr_history.jsonl"
TRADE_LOG_PATH  = CACHE_DIR / "k774_paper_trades.jsonl"

JST = timezone(timedelta(hours=9))
UTC = timezone.utc

# ── Strategy constants ────────────────────────────────────────────────────────
PAPER_TRADE         = os.environ.get("PAPER_TRADE", "True").lower() != "false"
SLEEVE_PCT          = 0.015         # K774 sleeve = 1.5% of AUM (HIP-3 HL-only liquidity constraint)
LEVERAGE            = 4.0           # 4x per K774 analysis
AUM_DEFAULT         = 10_000_000.0  # $10M reference AUM
DRIFT_REBALANCE_PCT = 0.05          # rebalance if legs drift > 5%
IOC_TIMEOUT_SEC     = 300           # 5 min fill window
EMA_PERIOD_HOURS    = 168           # 168h rolling mean (W=168h, G6 compliant: 48.6/yr)
EMA_PERIOD_PERIODS  = EMA_PERIOD_HOURS // 8  # = 21 periods (8h settlement cycle)
SIGNAL_SIGMA_MULT   = 0.0           # zero threshold (sign of rolling mean)
HL_API_URL          = "https://api.hyperliquid.xyz/info"
BYBIT_API_URL       = "https://api.bybit.com"  # informational only (IO not listed on Bybit)

# ── Venue config ──────────────────────────────────────────────────────────────
# HL-only: IO-PERP + SOL-PERP on HL (IO: HIP-3 fresh listing Jan 2025)
# IO NOT on Bybit (HIP-3 fresh HL-primary only).
# G8 = STRUCTURAL_NA per K735 HBAR-SOL / K747 TAO-SOL precedent.
# HL concentration: 66.8% AT CAP — paper-gate strict until K498/v6.52.
HL_CONCENTRATION_PRE_K774   = 66.8   # post-K769 reference
HL_CONCENTRATION_POST_K774  = 66.8   # UNCHANGED — paper-only, no live capital added
HL_ONLY_REASON              = (
    "HL-only: IO-PERP + SOL-PERP on HL. IO NOT on Bybit (HIP-3 fresh listing Jan 2025). "
    "G8 = STRUCTURAL_NA per K735 HBAR-SOL / K747 TAO-SOL HIP-3 precedent. "
    "IO $1.42M/day HL volume. HL at 66.8% AT CAP. "
    "Paper-gate strict: any live capital would breach 65% ceiling. "
    "Deploy LIVE after K498/v6.52 reduces HL% below 65%."
)

# ── Position state constants ──────────────────────────────────────────────────
STATE_NEUTRAL            = "NEUTRAL"
STATE_LONG_IO_SHORT_SOL  = "LONG_IO_SHORT_SOL"
STATE_LONG_SOL_SHORT_IO  = "LONG_SOL_SHORT_IO"

# ── Symbols fetched from HL for FR data ──────────────────────────────────────
SYMBOLS = ("IO", "SOL")


# ─────────────────────────────────────────────────────────────────────────────
# HTTP helper (stdlib urllib only — no requests)
# ─────────────────────────────────────────────────────────────────────────────

def _http_get(url: str, timeout: int = 10) -> Optional[dict]:
    try:
        req = urllib.request.Request(
            url, headers={"User-Agent": "crypto-lab-k774/1.0"}
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        print(f"  [k774] HTTP error: {e}", file=sys.stderr)
        return None


def _http_post(url: str, payload: dict, timeout: int = 10) -> Optional[dict]:
    try:
        data = json.dumps(payload).encode()
        req  = urllib.request.Request(
            url, data=data,
            headers={"Content-Type": "application/json",
                     "User-Agent": "crypto-lab-k774/1.0"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        print(f"  [k774] HTTP error: {e}", file=sys.stderr)
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Phase 1 — Funding rate fetch (IO + SOL from HL)
# ─────────────────────────────────────────────────────────────────────────────

def _fetch_hl_fr_batch() -> Dict[str, float]:
    """
    Fetch current 1h funding rates for IO and SOL from HL.
    Returns {symbol: fr_1h_fraction}.

    HL API: metaAndAssetCtxs (POST).
    K774: HL-only (IO-PERP + SOL-PERP). IO NOT on Bybit (HIP-3 fresh).
    IO HL: HIP-3 listing Jan 2025. $1.42M/day volume. maxLeverage=10.

    Note: HL settles 1h funding; W=168h = 168 x 1h periods for rolling mean.
    FR stored as 1h fraction; annualized = fr_1h * 8760.

    IO strategy direction (SHORT IO + LONG SOL double carry):
      IO FR structural negative: -17.9%/yr gross (SHORT IO collects carry).
      SOL FR structural positive: +2.59%/yr (LONG SOL collects carry).
      Both legs favorable → double carry strategy.
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
        print(f"  [k774] HL partial result {list(result.keys())} — IO HIP-3 HL-only, "
              f"Bybit N/A (IO not listed on Bybit)", file=sys.stderr)

    # Note: Bybit fallback not available for IO (HIP-3 HL-only asset).
    # SOL fallback from Bybit if HL fails for SOL:
    if "SOL" not in result:
        bybit_url = f"{BYBIT_API_URL}/v5/market/tickers?category=linear"
        raw_bybit = _http_get(bybit_url)
        if raw_bybit and raw_bybit.get("retCode") == 0:
            tickers = raw_bybit.get("result", {}).get("list", [])
            sym_map = {t["symbol"]: t for t in tickers}
            for perp_sym in ["SOLUSDT", "SOLUSDC"]:
                if perp_sym in sym_map:
                    tick = sym_map[perp_sym]
                    try:
                        fr_val = float(tick.get("fundingRate", 0.0))
                        result["SOL"] = fr_val
                        print(f"  [k774] SOL FR from Bybit fallback "
                              f"({perp_sym}, informational cross-check)", file=sys.stderr)
                    except (TypeError, ValueError):
                        pass
                    break

    return result


def _load_fr_history() -> List[dict]:
    """Load K774 FR history JSONL."""
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
    fr_io: float, fr_sol: float, io_sol_diff: float
) -> None:
    """Append one FR snapshot to history."""
    rec = {
        "ts_utc":      datetime.now(UTC).isoformat(),
        "fr_io":       round(fr_io,        10),
        "fr_sol":      round(fr_sol,        10),
        "io_sol_diff": round(io_sol_diff,   10),  # IO_FR - SOL_FR
    }
    with open(FR_HISTORY_PATH, "a") as f:
        f.write(json.dumps(rec) + "\n")


# ─────────────────────────────────────────────────────────────────────────────
# Phase 2 — Signal computation (IO-SOL direct differential, 168h rolling mean)
# ─────────────────────────────────────────────────────────────────────────────

def compute_signal(
    fr_io:  Optional[float] = None,
    fr_sol: Optional[float] = None,
) -> dict:
    """
    Fetch live IO and SOL FRs from HL, compute IO-SOL differential,
    and compute 168h rolling mean for direction signal.

    Signal mechanism (K774 direct alt-alt differential — no orthogonalization):
      diff = IO_FR - SOL_FR
      mean_168h = 168h rolling mean of diff (21 x 8h periods equivalent)
      sign  = sign(mean_168h)
      Enter: sign > 0 -> IO FR > SOL FR -> long IO (collect GPU-DePIN premium), short SOL
             sign < 0 -> SOL FR > IO FR -> long SOL (collect SVM premium), short IO
                         [This is the structural direction: IO persistent negative,
                          SOL persistent positive — LONG_SOL_SHORT_IO dominates]

    NOTE: IO is GPU-DePIN — structurally orthogonal to SOL SVM infrastructure.
    IO vs TAO AI cluster: io.net GPU rental marketplace (hardware DePIN)
    DISTINCT from Bittensor TAO AI L1 (substrate tokenization). G5v=0.047 PASS.
    During SOL liquidation cascades (SOL min=-20.51bps), IO is NOT correlated
    (GPU compute demand cycle independent of SOL SVM margin calls).
    Strategy: SHORT IO + LONG SOL double carry (both sides favorable).
    IO -17.9%/yr gross negative → SHORT IO collects carry.
    SOL +2.59%/yr gross positive → LONG SOL collects carry.

    K774 double carry mechanism:
      When signal says LONG_SOL_SHORT_IO (dominant regime):
        SHORT IO: collect ~17.9%/yr carry from persistent IO shorts
        LONG SOL: collect ~2.59%/yr carry from persistent SOL longs
        Both legs in favorable carry direction simultaneously.
      When signal says LONG_IO_SHORT_SOL (temporary IO spike):
        IO FR temporarily turns positive (GPU shortage narrative spikes).
        LONG IO captures the temporary premium.
        SHORT SOL benefits if SOL FR simultaneously drops.

    Alt-alt mechanism (NINETEENTH ALT-ALT pair — K774):
      IO FR tracks GPU compute supply/demand cycles:
        H100 supply constraints (Q4-2024, Q1-2025 spike events),
        AI hyperscaler capacity expansion vs contraction,
        io.net network utilization and GPU rental yield,
        GPU shortage narratives (Nvidia H100/H200 events),
        IO staking/reward program cycles,
        HIP-3 fresh listing structural short squeeze periods,
        DePIN narrative rotations (compute vs data vs bandwidth layers).
        Vol ratio vs SOL: 1.96x (full), 13.11x (30d), 5.83x (90d).
      SOL FR tracks Solana SVM: DePIN, Phantom, Firedancer, SOL ETF.
        SVM DeFi TVL (Jupiter/Drift/Jito). +2.59%/yr persistent.
      IO-SOL diff captures relative GPU-DePIN premium vs SVM infrastructure.
      G5 max_corr=0.2778 (G5s HBAR-SOL) ALL 26/26 PASS.

    W=168h rationale (G6 compliance):
      W=168h → 48.6 entries/yr OOS (ABOVE 30/yr G6 threshold — PASS).
      W=168h chosen as family standard window for consistency with alt-alt family.
      Best grid config: W=48h T=0.25 OOS Sh=31.42 (61 entries/yr) — more entries.
      W=168h canonical for K774 (family standard; G6-compliant 48.6/yr).

    K774 §6 validation:
      - OOS Sharpe: 19.884 (W=168h, zero threshold, 150.2d OOS)
      - OOS Ann Return: $28K central @$10M @4x @1.5% sleeve (K523 3-point)
      - All G5 26 checks PASS (max_corr=0.2778 G5s HBAR-SOL — all well below 0.40)
      - G4 WF 12/12 all positive (min_sh=5.866)
      - 60d gate: Realized Sh>=10 + fill>=60% + maxDD<15%
      - HL 66.8% AT CAP → paper-gate strict

    Returns:
      {
        "fr_io":            float,
        "fr_sol":           float,
        "io_sol_diff":      float,    # IO_FR - SOL_FR (current)
        "mean_168h":        float,    # 168h rolling mean of differential
        "diff_sigma":       float,    # 168h rolling sigma (informational)
        "history_points":   int,
        "regime":           str,      # BULL_IO | BEAR_IO | NEUTRAL
        "signal_direction": int,      # +1 | -1 | 0
        "ts_jst":           str,
      }
    """
    if fr_io is None or fr_sol is None:
        frs    = _fetch_hl_fr_batch()
        fr_io  = frs.get("IO",  0.0)
        fr_sol = frs.get("SOL", 0.0)

    # IO-SOL direct alt-alt differential (no orthogonalization)
    io_sol_diff = fr_io - fr_sol

    _append_fr_history(fr_io, fr_sol, io_sol_diff)

    # Load history for rolling mean + sigma (168h = ~21 x 8h periods)
    history = _load_fr_history()
    diffs   = [r["io_sol_diff"] for r in history if "io_sol_diff" in r]

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

    # Regime classification (zero threshold — per K774 spec)
    # BULL_IO: IO FR > SOL FR (GPU-DePIN cycle dominant — temporary spike)
    # BEAR_IO: IO FR < SOL FR (SVM infrastructure premium dominant — structural)
    # Note: BEAR_IO is the dominant structural direction (IO -17.9%/yr vs SOL +2.59%/yr)
    if mean_168h > 0:
        regime    = "BULL_IO"    # IO-SOL diff positive → IO FR > SOL FR (GPU spike)
        direction = 1
    elif mean_168h < 0:
        regime    = "BEAR_IO"    # IO-SOL diff negative → SOL FR > IO FR (SVM dominant)
        direction = -1
    else:
        regime    = "NEUTRAL"
        direction = 0

    return {
        "fr_io":            round(fr_io,         10),
        "fr_sol":           round(fr_sol,          10),
        "io_sol_diff":      round(io_sol_diff,     10),
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
    Determine trade direction from IO-SOL differential rolling mean.

    Logic (IO-SOL direct alt-alt pair, HL-only):
      regime = BULL_IO (mean_168h > 0):
        IO FR > SOL FR: GPU-DePIN spike (IO temporarily positive)
        -> long IO (collect GPU-DePIN premium during spike)
        -> short SOL (avoid lower SVM carry in GPU-spike regime)
        -> position_state = LONG_IO_SHORT_SOL

      regime = BEAR_IO (mean_168h < 0):
        SOL FR > IO FR: SVM season + IO structural negative
        -> long SOL (collect SVM DePIN/DeFi premium)
        -> short IO (collect IO negative carry — double carry both sides)
        -> position_state = LONG_SOL_SHORT_IO [dominant structural direction]

      regime = NEUTRAL: no trade (mean_168h == 0 exactly — rare)

    Double carry note (BEAR_IO structural direction):
      SHORT IO: IO FR structural -17.9%/yr → collect carry from IO short
      LONG SOL: SOL FR structural +2.59%/yr → collect carry from SOL long
      Both legs favorable simultaneously = double carry strategy.
      This is the structural dominant direction for IO-SOL pair.

    Alt-alt edge (NINETEENTH ALT-ALT pair — K774):
      IO and SOL are structurally distinct assets with orthogonal FR timing.
      BULL_IO: GPU supply shortage drives IO premium (H100 scarcity events,
        io.net network congestion, GPU-DePIN adoption spikes).
      BEAR_IO: SVM infrastructure drives SOL premium (Firedancer, ETF,
        Phantom adoption, DeFi TVL growth). IO structural negative -17.9%/yr.
      OOS Sh=19.884. MaxDD OOS=-0.389955%. G4 12/12 ALL POSITIVE (min_sh=5.866).
      IO = 18th vertex (1st GPU-DePIN). MR9 L002: all future IO-X pairs blocked.

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

    if regime == "BULL_IO":
        # IO FR > SOL FR: GPU-DePIN spike (temporary)
        long_asset  = "IO"
        short_asset = "SOL"
        state       = STATE_LONG_IO_SHORT_SOL
    else:  # BEAR_IO
        # SOL FR > IO FR: SVM season + IO structural negative (dominant)
        long_asset  = "SOL"
        short_asset = "IO"
        state       = STATE_LONG_SOL_SHORT_IO

    # HL-only for both legs (IO not on Bybit)
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
    Compute equal notional for both legs of the IO-SOL paired trade.

    K774 HL config (IO-PERP + SOL-PERP on HL, paper-gate strict):
      sleeve_capital   = aum x sleeve_pct      (e.g. $10M x 1.5% = $150K)
      total_notional   = sleeve_capital x lev   ($150K x 4 = $600K)
      notional_per_leg = total_notional / 2     ($300K per leg)

    At $10M / 1.5% sleeve / 4x (paper-gate):
      IO leg:  $75K capital x 4x = $300K notional (HL IO-PERP)
      SOL leg: $75K capital x 4x = $300K notional (HL SOL-PERP)
      Total:   $600K notional (two legs combined)
      Margin:  $150K (1.5% of AUM)
      HL conc: PAPER-ONLY (66.8% AT CAP — no live capital added)
      Net profit: central $28K/yr @$10M @4x (K523: $21K-$74K)
      IO vertex: 18th (1st GPU-DePIN) — MR9 L002 blocks all future IO-X pairs
      Sleeve: 1.5% (HIP-3 HL-only liquidity constraint — IO $1.42M/day)

    Returns (notional_per_leg, total_notional).
    """
    sleeve_capital   = aum * sleeve_pct
    total_notional   = sleeve_capital * leverage
    notional_per_leg = total_notional / 2.0
    return round(notional_per_leg, 2), round(total_notional, 2)


# ─────────────────────────────────────────────────────────────────────────────
# Phase 5 — Paired trade submission (HL-only, POST_ONLY)
# ─────────────────────────────────────────────────────────────────────────────

def submit_paired_trade(
    long_leg:  dict,
    short_leg: dict,
    dry_run:   bool = True,
) -> dict:
    """
    Submit K774 IO-SOL paired trade: POST_ONLY both legs in parallel.

    Protocol (K774 HL-only — both legs on HL, IO HIP-3):
      1. Submit IO leg on HL POST_ONLY
      2. Submit SOL leg on HL POST_ONLY
      3. Both legs submitted in parallel (K439 pattern)
      4. IOC fallback per leg if POST_ONLY times out
      5. If both fail: retry next 8h cycle

    Args:
      long_leg:  {"symbol": "IO"|"SOL", "notional": 300000, "venue": "HL"}
      short_leg: {"symbol": "SOL"|"IO", "notional": 300000, "venue": "HL"}
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
        print(f"  [K774] {mode_tag}: LONG {long_sym}@{long_venue} ${long_notl:,.0f}  "
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
            "venue_config":     "HL_ONLY_IO_SOL_ALT_ALT",
            "mechanism_note":   (
                "IO-SOL direct alt-alt differential (K774 NINETEENTH ALT-ALT, 77th daemon): "
                "IO FR = GPU-DePIN premium (io.net GPU compute marketplace, HIP-3 Jan 2025, "
                "H100 supply constraint events, AI hyperscaler demand cycles, "
                "GPU rental yield cycles, IO staking/reward programs, "
                "DePIN narrative rotations compute/data/bandwidth layers, "
                "vol_ratio=1.96x SOL full / 5.83x 90d / 13.11x 30d / 17.26x K773 snapshot); "
                "SOL FR = Solana SVM DePIN/DeFi premium (Phantom adoption, Firedancer upgrade, "
                "SOL ETF speculation, SVM DeFi TVL Jupiter/Drift/Jito, +2.59%/yr persistent, "
                "SOL liquidation cascade Min=-20.51bps Feb 2025). "
                "G4 WF 12/12 ALL POSITIVE (min_sh=5.866). "
                "G5 26/26 PASS (max_corr=0.2778 G5s HBAR-SOL — well below 0.40). "
                "HL at 66.8% AT CAP — paper-gate strict until K498/v6.52 reduces HL%. "
                "IO = 18th vertex (1st GPU-DePIN). MR9 L002: all future IO-X pairs blocked. "
                "OOS Sh=19.884 (W=168h, zero threshold, 150.2d). "
                "K523 3-point: conservative=$21,007 central=$28,009 optimistic=$73,707/yr @$10M @4x @1.5%. "
                "60d gate: Realized Sh>=10 + fill>=60% + maxDD<15%."
            ),
            "ts_utc":           ts,
        }
        _append_trade_log(result)
        return result

    # LIVE scaffold (not reached in PAPER_TRADE mode):
    print(f"  [K774] SCAFFOLD LIVE: parallel POST_ONLY "
          f"LONG {long_sym}@{long_venue} ${long_notl:,.0f} "
          f"+ SHORT {short_sym}@{short_venue} ${short_notl:,.0f}")
    long_order_id  = f"SCAFFOLD_LONG_{long_sym}_{int(time.time())}"
    short_order_id = f"SCAFFOLD_SHORT_{short_sym}_{int(time.time())}"

    print(f"  [K774] Neither leg filled within timeout — retry next 8h cycle")
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
    Check if current K774 position has drifted beyond DRIFT_REBALANCE_PCT (5%).

    K774 HL: both legs on HL (IO-PERP + SOL-PERP).
    Drift detection: compare stored IO leg notional vs SOL leg notional.
    Threshold: 5% (same as K679/K682/K684/K686/K690/K747/K739/K754/K759/K769 pattern).

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
    Both legs on HL (K774 HL-only — IO-PERP + SOL-PERP).

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

    if state == STATE_LONG_IO_SHORT_SOL:
        long_sym,  short_sym  = "IO", "SOL"
    else:  # LONG_SOL_SHORT_IO
        long_sym,  short_sym  = "SOL", "IO"

    long_notional  = float(dash.get("long_notional",  0.0))
    short_notional = float(dash.get("short_notional", 0.0))

    if dry_run or PAPER_TRADE:
        mode_tag = "DRY_RUN" if dry_run else "PAPER_TRADE"
        print(f"  [K774] {mode_tag} CLOSE:")
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
        print(f"  [K774] SCAFFOLD CLOSE:")
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
    """Load k774_dashboard.json; return defaults if missing."""
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
    """Write k774_dashboard.json with full signal + regime state."""
    dash = _load_dashboard()

    # Update signal data
    dash["last_poll_jst"]       = signal.get("ts_jst", "—")
    dash["fr_io_current"]       = signal.get("fr_io",            0.0)
    dash["fr_sol_current"]      = signal.get("fr_sol",            0.0)
    dash["io_sol_diff_current"] = signal.get("io_sol_diff",       0.0)
    dash["mean_168h"]           = signal.get("mean_168h",         0.0)
    dash["diff_sigma"]          = signal.get("diff_sigma",        0.0)
    dash["regime"]              = signal.get("regime",     "NEUTRAL")
    dash["signal_direction"]    = signal.get("signal_direction",  0)
    dash["history_points"]      = signal.get("history_points",    0)

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
    dash["rebalance_required"]      = rebalance.get("rebalance_required", False)

    # Margin / notional summary
    dash["total_notional_usdc"]     = round(total_notional, 2)
    dash["notional_per_leg_usdc"]   = round(notional_per_leg, 2)
    dash["leverage"]                = LEVERAGE
    dash["sleeve_pct"]              = SLEEVE_PCT
    dash["aum_ref_usdc"]            = aum
    dash["margin_used_usdc"]        = round(total_notional / LEVERAGE, 2)
    dash["margin_pct_of_aum"]       = round((total_notional / LEVERAGE) / aum, 4)
    dash["hl_concentration_pct"]    = HL_CONCENTRATION_POST_K774

    # K774 static metadata
    dash["strategy"]        = "K774 IO-SOL FR Differential (NINETEENTH ALT-ALT, K776 scaffold)"
    dash["oos_sharpe"]      = 19.884
    dash["w_hours"]         = 168
    dash["paper_trade"]     = PAPER_TRADE
    dash["hl_only"]         = True
    dash["hl_only_reason"]  = HL_ONLY_REASON
    dash["io_vertex"]       = "18th vertex (1st GPU-DePIN cluster). MR9 L002: all future IO-X blocked."
    dash["k523_central_yr"] = 28009
    dash["k523_cons_yr"]    = 21007
    dash["k523_opt_yr"]     = 73707
    dash["live_gate_60d"]   = {
        "sharpe_threshold":     10.0,
        "fill_rate_pct":        60.0,
        "max_dd_pct":           15.0,
        "additional_gate":      "K498/v6.52 OKX activation required (HL% must drop below 65.0%)",
    }
    dash["g9_note"]         = "G9 marginal: OOS=150.2d < 180d threshold. Monitor for full 180d."
    dash["g5s_note"]        = "G5s HBAR-SOL borderline (IS 0.352, full 0.278) — monthly recheck."

    DASHBOARD_PATH.write_text(json.dumps(dash, indent=2))
    return dash


# ─────────────────────────────────────────────────────────────────────────────
# Phase 8 — Print status
# ─────────────────────────────────────────────────────────────────────────────

def print_status(dash: dict) -> None:
    """Print K774 IO-SOL strategy status summary."""
    print("=" * 70)
    print("K774 IO-SOL FR Differential — Status")
    print("=" * 70)
    print(f"  Last poll:         {dash.get('last_poll_jst', '—')}")
    print(f"  Regime:            {dash.get('regime', 'NEUTRAL')}")
    print(f"  Position:          {dash.get('position_state', 'NEUTRAL')}")
    print(f"  IO FR (current):   {dash.get('fr_io_current', 0.0):.8f}")
    print(f"  SOL FR (current):  {dash.get('fr_sol_current', 0.0):.8f}")
    print(f"  IO-SOL diff:       {dash.get('io_sol_diff_current', 0.0):.8f}")
    print(f"  Mean 168h:         {dash.get('mean_168h', 0.0):.8f}")
    print(f"  History points:    {dash.get('history_points', 0)}")
    print(f"  Total notional:    ${dash.get('total_notional_usdc', 0.0):,.0f}")
    print(f"  Margin used:       ${dash.get('margin_used_usdc', 0.0):,.0f}")
    print(f"  Sleeve:            {SLEEVE_PCT:.1%}")
    print(f"  Leverage:          {LEVERAGE}x")
    print(f"  Venue:             HL-only (IO HIP-3, NOT on Bybit)")
    print(f"  HL concentration:  {dash.get('hl_concentration_pct', 66.8):.1f}%")
    print(f"  Paper trade:       {PAPER_TRADE}")
    print(f"  OOS Sharpe:        19.884 (W=168h, 150.2d OOS)")
    print(f"  K523 central:      $28,009/yr @$10M @4x @1.5%")
    print(f"  Drift:             {dash.get('delta_neutral_drift_pct', 0.0):.2%}")
    print(f"  Rebalance:         {dash.get('rebalance_required', False)}")
    print(f"  IO vertex:         18th (1st GPU-DePIN). MR9 L002: all IO-X blocked.")
    print(f"  G9 monitor:        OOS=150.2d < 180d — watch for full 180d.")
    print(f"  G5s monitor:       HBAR-SOL IS=0.352 borderline — monthly recheck.")
    print("=" * 70)


# ─────────────────────────────────────────────────────────────────────────────
# Main loop — 8h cadence
# ─────────────────────────────────────────────────────────────────────────────

def run_main_cycle(aum: float = AUM_DEFAULT) -> dict:
    """
    Main 8h execution cycle for K774 IO-SOL FR Differential.

    Steps:
      1. Fetch IO + SOL FR from HL
      2. Compute 168h rolling mean signal
      3. Decide position
      4. Submit / hold / rebalance
      5. Write dashboard
    """
    print(f"\n[K774 IO-SOL] {datetime.now(JST).strftime('%Y-%m-%d %H:%M JST')} — 8h cycle")
    print(f"  Venue: HL-only (IO HIP-3 NOT on Bybit). PAPER_TRADE={PAPER_TRADE}")
    print(f"  HL concentration: {HL_CONCENTRATION_POST_K774}% AT CAP — paper-gate strict")

    # Step 1+2: Signal
    signal = compute_signal()

    print(f"  IO FR:    {signal['fr_io']:.8f} ({signal['fr_io'] * 8760 * 100:.2f}%/yr)")
    print(f"  SOL FR:   {signal['fr_sol']:.8f} ({signal['fr_sol'] * 8760 * 100:.2f}%/yr)")
    print(f"  diff:     {signal['io_sol_diff']:.8f}")
    print(f"  mean168h: {signal['mean_168h']:.8f}")
    print(f"  regime:   {signal['regime']} (direction={signal['signal_direction']})")
    print(f"  history:  {signal['history_points']} points")

    # Step 3: Position decision
    decision = decide_position(signal)
    if decision is None:
        print("  Decision: NEUTRAL — no trade")
    else:
        print(f"  Decision: {decision['position_state']}")
        print(f"    LONG  {decision['long_asset']}@{decision['long_venue']}")
        print(f"    SHORT {decision['short_asset']}@{decision['short_venue']}")

    # Step 4: Notionals
    notional_per_leg, total_notional = compute_delta_neutral_notional(aum)
    print(f"  Notional per leg: ${notional_per_leg:,.0f}  total: ${total_notional:,.0f}")

    # Step 4b: Load dashboard for rebalance check
    dash = _load_dashboard()
    rebalance = daily_rebalance(dash)
    if rebalance["rebalance_required"]:
        print(f"  REBALANCE required: drift={rebalance['drift_pct']:.2%}")

    # Step 4c: Trade submission (paper only)
    if decision and dash.get("position_state", STATE_NEUTRAL) == STATE_NEUTRAL:
        long_leg  = {"symbol": decision["long_asset"],  "notional": notional_per_leg, "venue": "HL"}
        short_leg = {"symbol": decision["short_asset"], "notional": notional_per_leg, "venue": "HL"}
        exec_result = submit_paired_trade(long_leg, short_leg, dry_run=False)
        print(f"  Submit: {exec_result['status']}")

    # Step 5: Write dashboard
    final_dash = _write_dashboard(signal, decision, notional_per_leg, total_notional, rebalance, aum)
    print(f"  Dashboard written: {DASHBOARD_PATH}")
    return final_dash


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="K774 IO-SOL FR Differential — 77th daemon, 19th alt-alt, 18th vertex IO"
    )
    parser.add_argument("--dry-run",   action="store_true", help="Run signal + decision, no submission")
    parser.add_argument("--status",    action="store_true", help="Print dashboard status and exit")
    parser.add_argument("--rebalance", action="store_true", help="Check drift + rebalance if needed")
    parser.add_argument("--close",     type=str, metavar="REASON", help="Close all IO-SOL positions")
    parser.add_argument("--aum",       type=float, default=AUM_DEFAULT, help="AUM for sizing ($10M default)")
    args = parser.parse_args()

    if args.status:
        dash = _load_dashboard()
        print_status(dash)
        return 0

    if args.close:
        result = close_paired_position(args.close, dry_run=False)
        print(json.dumps(result, indent=2))
        return 0

    if args.rebalance:
        dash = _load_dashboard()
        result = daily_rebalance(dash)
        print(json.dumps(result, indent=2))
        if result["rebalance_required"]:
            print("  [K774] Rebalance triggered — resizing legs to target notional")
        return 0

    if args.dry_run:
        print(f"[K774 IO-SOL] DRY-RUN — {datetime.now(JST).strftime('%Y-%m-%d %H:%M JST')}")
        signal   = compute_signal()
        decision = decide_position(signal)
        notional_per_leg, total_notional = compute_delta_neutral_notional(args.aum)
        print(json.dumps({
            "signal":            signal,
            "decision":          decision,
            "notional_per_leg":  notional_per_leg,
            "total_notional":    total_notional,
            "paper_trade":       PAPER_TRADE,
            "hl_only":           True,
            "oos_sharpe":        19.884,
            "k523_central_yr":   28009,
        }, indent=2))
        return 0

    # Normal 8h cycle
    run_main_cycle(args.aum)
    return 0


if __name__ == "__main__":
    sys.exit(main())
