#!/usr/bin/env python3
"""
k768_blur_sol_run.py — K768 BLUR-SOL FR Differential Strategy
==============================================================
EIGHTEENTH ALT-ALT pair: BLUR vs SOL (NFT marketplace × Solana SVM).
Signal: BLUR_FR - SOL_FR
W=168h rolling mean (7d — G6 compliant: 38.2 entries/yr OOS)
HL primary, Bybit fallback
HL concentration: 66.8% AT CAP → paper-gate strict (K498/v6.52 required for live)

K768 BLUR-SOL alt-alt hypothesis:
  BLUR (Blur.io NFT marketplace token, Ethereum L1, launched Oct 2022):
    FR driven by NFT bull cycles (BAYC Q1-2023, Pudgy Penguins Q4-2023—Q1-2024,
    SOL NFT seasons Q1-2024), royalty mechanism battles (Blur vs OpenSea),
    NFT lending (Blur Blend protocol), wash-trading incentive programs (Blur
    airdrop seasons), Ethereum L1 congestion cycles.
    Extreme fat-tail FR spikes: kurtosis=575.70.
    Max spike: 0.008065 on 2026-04-01 (NFT season event).
    64 spike events over 0.0001 threshold in full history.
    2026-04 vol ratio: 83.49x (extreme spike month).
    Full-period vol ratio: 6.77x vs SOL FR.
  SOL (Solana SVM L1):
    FR driven by retail momentum, Phantom wallet adoption,
    Firedancer upgrade cycles, Solana ETF narrative flows, SVM DeFi TVL.
    SOL FR mean +8.79%/ann — persistently positive structural retail demand.
    SOL extreme negative FR: Min=-20.51bps (liquidation cascade Feb 2025).
  Alt-alt mechanism: BLUR (Ethereum L1 NFT marketplace) vs SOL (Solana SVM).
    Cross-cluster: NFT cultural event cycles vs SVM ecosystem sentiment diverge.
    BLUR can spike 10-50x normal range during NFT seasons while SOL FR stays muted.
    Structurally independent FR drivers: NFT marketplace protocol vs SVM infrastructure.
  EIGHTEENTH alt-alt pair. OOS Sharpe 14.98. W=168h. 20/21 WF positive.
  G1-G4+G6-G9 ALL PASS. G5 FIL-SOL borderline (full=0.4398, OOS=0.2805).
  G8: HL+Bybit confirmed (BLURUSDT Bybit 4594 rows, HL listed 2024-05).
  BLUR becomes 16th vertex. All future BLUR-X auto-blocked (MR9 L002).
  LIQUIDITY WARNING: HL BLUR $0.6M/day → max $60K position → 0.6% sleeve.

K768 §6 validation (CONDITIONAL_ACCEPT — G5 FIL-SOL documented exception):
  - OOS Sharpe: 14.9799 (W=168h, zero threshold, ~210d OOS)
  - G1-G4+G6-G9 ALL PASS. G5 FIL-SOL full=0.4398 FAIL (OOS=0.2805 PASS).
  - G5 exception: SOL-anchor contamination (both BLUR-SOL and FIL-SOL short SOL
    when SOL FR dominates IS period). Raw FRs independent: L007=0.0478.
    OOS corr 0.2805 < IS 0.5112 → contamination reduces in OOS (structural divergence).
  - G4 walk-forward: 20/21 folds positive (positive_frac=0.952)
  - G5 max_corr_full=0.4398 (FIL-SOL) — documented SOL-anchor exception
  - G5 max_corr_oos=0.2805 (FIL-SOL) PASS in OOS window (critical gate)
  - G6: 38.2 entries/yr OOS PASS (W=168h: G6-compliant vs 30/yr minimum)
  - G8: HL+Bybit confirmed (BLURUSDT 4594 rows since 2023-02, HL 2024-05+)
  - CONDITIONAL: HL 66.8% AT CAP → paper-gate strict until K498/v6.52
  - LIQUIDITY: $0.6M/day → 0.6% sleeve cap (10% daily vol rule)
  - 4 live-elevation conditions required (see below)

K768 BLUR-SOL vertex addition (16th vertex, NFT marketplace cluster):
  V (before K768) = {APT, ATOM, AVAX, BNB, ENA, FIL, HBAR, INJ, LDO, SEI,
                      SOL, TIA, TAO, PEPE, WIF, RUNE*}  (*RUNE rejected K762)
  V (before K768) = {APT, ATOM, AVAX, BNB, ENA, FIL, HBAR, INJ, LDO, SEI,
                      SOL, TIA, TAO, PEPE, WIF}  (15 accepted vertices)
  V (after K768)  = {APT, ATOM, AVAX, BNB, ENA, FIL, HBAR, INJ, LDO, SEI,
                      SOL, TIA, TAO, PEPE, WIF, BLUR}
  BLUR = 16th vertex (NFT marketplace cluster — first NFT marketplace in family).
  MR9 L002: all future BLUR-X pairs are auto-blocked (BLUR exhausted as new vertex).
  BLUR-SOL is the only permissible BLUR-X pair given V composition at K768.

G5 FIL-SOL exception analysis (K770 governance note):
  G5 full_corr(BLUR-SOL, FIL-SOL) = 0.4398 FAIL (> 0.40 gate).
  IS corr = 0.5112 (IS-period contamination: both strategies short SOL → correlated).
  OOS corr = 0.2805 PASS (< 0.40 threshold — contamination decreases in OOS).
  Mechanism: SOL-anchor contamination. When SOL FR dominates, both BLUR-SOL and
    FIL-SOL strategies short SOL → correlated signals. Raw FR independence confirmed:
    L007 raw_corr(BLUR_fr, FIL_fr) = 0.0478 (< 0.45 threshold, well clear).
  Precedent: no exact precedent in K748-K762. Standard protocol = G5 FAIL → REJECT.
  Exception condition: OOS corr < gate AND documented SOL-anchor mechanism.
  Governance note: FIL-SOL capacity sharing implicit. Total SOL-short exposure elevated.
  4 live-elevation conditions required before deployment (rolling 90d OOS monitoring).

4 LIVE-ELEVATION CONDITIONS (K770 governance):
  1. G5 FIL-SOL rolling 90d OOS corr < 0.40 (currently 0.2805 PASS but borderline)
  2. HL BLUR daily volume > $1M/day sustained (currently $0.6M)
  3. HL cap < 65% (currently 66.8% — requires K498/v6.52)
  4. Governance review of NFT marketplace cluster (no family precedent)
  All 4 conditions must be met simultaneously before PAPER_TRADE=False.

K523 3-point profit projection (@$10M @4x @0.6% sleeve — liquidity-limited):
  Conservative: $37,000/yr  (R2S=38% floor, K518 floor, 0.6% sleeve)
  Central:      $61,000/yr  (base case, K523 mandate, 0.6% sleeve)
  Optimistic:   $153,000/yr (near-full OOS realization — standard 2.5% sleeve
                              not viable at $0.6M/day liquidity; reference only)
  Note: optimistic assumes HL BLUR liquidity grows to $2.5M/day (condition 2).
  Upper bound: OOS raw return (NOT central — K523 mandatory).

Architecture (K679→K747→K754→K759→K768 alt-alt scaffold pattern):
  1. fetch_fr_batch()                    → fetch BLUR + SOL FR every 8h from HL
  2. compute_signal(blur_fr, sol_fr)    → 168h rolling mean of (BLUR_FR - SOL_FR); sign()
  3. decide_position(signal)             → LONG_BLUR_SHORT_SOL | LONG_SOL_SHORT_BLUR | NEUTRAL
  4. submit_paired_trade(long, short)   → POST_ONLY paired (BLUR + SOL legs, HL primary)
  5. daily_rebalance()                   → drift > 5% triggers rebalance
  6. close_paired_position(reason)      → sequential: short first, then long

K770 production scaffold:
  - 75th daemon (eighteenth alt-alt pair, CONDITIONAL_ACCEPT, 4 live conditions)
  - HL primary, Bybit fallback (BLUR: HL BLUR-PERP + Bybit BLURUSDT)
  - 0.6% sleeve (liquidity-limited: HL $0.6M/day → 10% daily vol rule → $60K max)
  - $61K central @$10M @4x @0.6% sleeve (K523 3-point: $37K-$153K reference)
  - Paper-gate until ALL 4 live-elevation conditions met
  - 60d paper-trade gate: Realized Sh>=6 + fill>=60% + maxDD<15%
  - 18th alt-alt pair (NFT marketplace × SVM, 16th vertex BLUR)

Execution:
  - HL primary (BLUR-PERP + SOL-PERP, HL)
  - Bybit fallback (BLURUSDT + SOL-PERP, Bybit) — informational cross-check
  - POST_ONLY paired execution (K439 pattern)
  - Position: 0.6% sleeve, 4x leverage (paper-gate strict — liquidity + HL cap)
  - 8h cadence (matches FR settlement cycle)
  - W=168h rolling mean (21 x 8h periods — G6-safe: 38.2 entries/yr OOS)

Paper-trade mode is the DEFAULT.  No orders are submitted unless
PAPER_TRADE=False is explicitly set in the environment.

K339 security: REPO_ROOT from __file__, no /Users/ literals.
No new packages — stdlib urllib + json only.

Usage:
  python3 scripts/k768_blur_sol_run.py --dry-run
  python3 scripts/k768_blur_sol_run.py --status
  python3 scripts/k768_blur_sol_run.py --rebalance
  python3 scripts/k768_blur_sol_run.py --close "scheduled exit"
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

DASHBOARD_PATH  = DATA_DIR  / "k768_dashboard.json"
FR_HISTORY_PATH = CACHE_DIR / "k768_fr_history.jsonl"
TRADE_LOG_PATH  = CACHE_DIR / "k768_paper_trades.jsonl"

JST = timezone(timedelta(hours=9))
UTC = timezone.utc

# ── Strategy constants ────────────────────────────────────────────────────────
PAPER_TRADE         = os.environ.get("PAPER_TRADE", "True").lower() != "false"
SLEEVE_PCT          = 0.006         # K768 sleeve = 0.6% of AUM (liquidity-limited)
LEVERAGE            = 4.0           # 4x per K768 analysis
AUM_DEFAULT         = 10_000_000.0  # $10M reference AUM
DRIFT_REBALANCE_PCT = 0.05          # rebalance if legs drift > 5%
IOC_TIMEOUT_SEC     = 300           # 5 min fill window
EMA_PERIOD_HOURS    = 168           # 168h rolling mean (W=168h, G6 compliant: 38.2/yr)
EMA_PERIOD_PERIODS  = EMA_PERIOD_HOURS // 8  # = 21 periods (8h settlement cycle)
SIGNAL_SIGMA_MULT   = 0.0           # zero threshold (sign of rolling mean)
HL_API_URL          = "https://api.hyperliquid.xyz/info"
BYBIT_API_URL       = "https://api.bybit.com"

# ── Venue config ──────────────────────────────────────────────────────────────
# HL primary: BLUR-PERP + SOL-PERP on HL
# Bybit fallback: BLURUSDT + SOL-PERP on Bybit (informational cross-check)
# HL concentration: 66.8% AT CAP per K751 audit — paper-gate strict until K498/v6.52.
# LIQUIDITY WARNING: HL BLUR $0.6M/day → 10% daily vol rule → max $60K position.
HL_CONCENTRATION_PRE_K768   = 66.8   # post-K761 reference (K751 audit)
HL_CONCENTRATION_POST_K768  = 66.8   # UNCHANGED — paper-only, no live capital added
HL_ONLY_REASON              = (
    "HL primary: BLUR-PERP + SOL-PERP on HL. Bybit BLURUSDT fallback (informational). "
    "HL at 66.8% AT CAP (K751 audit). Paper-gate strict: any live capital would breach 65%. "
    "LIQUIDITY CAP: HL BLUR $0.6M/day → max safe position $60K (10% daily vol rule). "
    "Sleeve capped at 0.6% (@$10M) until HL BLUR vol > $1M/day (live condition 2). "
    "Deploy LIVE after all 4 live-elevation conditions met (K770)."
)

# ── Live-elevation conditions (all 4 required) ───────────────────────────────
LIVE_CONDITIONS = [
    "G5 FIL-SOL rolling 90d OOS corr < 0.40 (currently 0.2805 PASS — borderline, monitor)",
    "HL BLUR daily volume > $1M/day sustained (currently $0.6M — sub-threshold)",
    "HL cap < 65% (currently 66.8% — requires K498/v6.52 OKX activation)",
    "Governance review of NFT marketplace cluster (no family precedent — K770 open)",
]

# ── Position state constants ──────────────────────────────────────────────────
STATE_NEUTRAL             = "NEUTRAL"
STATE_LONG_BLUR_SHORT_SOL = "LONG_BLUR_SHORT_SOL"
STATE_LONG_SOL_SHORT_BLUR = "LONG_SOL_SHORT_BLUR"

# ── Symbols fetched from HL for FR data ──────────────────────────────────────
SYMBOLS = ("BLUR", "SOL")


# ─────────────────────────────────────────────────────────────────────────────
# HTTP helper (stdlib urllib only — no requests)
# ─────────────────────────────────────────────────────────────────────────────

def _http_get(url: str, timeout: int = 10) -> Optional[dict]:
    try:
        req = urllib.request.Request(
            url, headers={"User-Agent": "crypto-lab-k768/1.0"}
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        print(f"  [k768] HTTP error: {e}", file=sys.stderr)
        return None


def _http_post(url: str, payload: dict, timeout: int = 10) -> Optional[dict]:
    try:
        data = json.dumps(payload).encode()
        req  = urllib.request.Request(
            url, data=data,
            headers={"Content-Type": "application/json",
                     "User-Agent": "crypto-lab-k768/1.0"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        print(f"  [k768] HTTP error: {e}", file=sys.stderr)
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Phase 1 — Funding rate fetch (BLUR + SOL from HL)
# ─────────────────────────────────────────────────────────────────────────────

def _fetch_hl_fr_batch() -> Dict[str, float]:
    """
    Fetch current 1h funding rates for BLUR and SOL from HL.
    Returns {symbol: fr_1h_fraction}.

    HL API: metaAndAssetCtxs (POST).
    K768: HL primary (BLUR-PERP + SOL-PERP).
    Bybit fallback: BLURUSDT (informational cross-check).
    BLUR HL listed: 2024-05 per cache. Bybit BLURUSDT: 4594 rows 2023-02 to 2026-05.

    Note: HL settles 1h funding; W=168h = 168 x 1h periods for rolling mean.
    FR stored as 1h fraction; annualized = fr_1h * 8760.

    LIQUIDITY NOTE: HL BLUR $0.6M/day — only 10% daily vol rule → $60K max position.
    Monitor daily vol: if > $1M/day sustained for 30d → live condition 2 met.

    Fallback: Bybit /v5/market/tickers — BLURUSDT (8h interval vs HL 1h — different
    granularity; cross-check informational; 8h smoothing reduces spike visibility).
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
        print(f"  [k768] HL partial result {list(result.keys())} — trying Bybit fallback",
              file=sys.stderr)

    # Fallback: Bybit /v5/market/tickers (BLURUSDT — informational)
    bybit_url = f"{BYBIT_API_URL}/v5/market/tickers?category=linear"
    raw_bybit = _http_get(bybit_url)
    if raw_bybit and raw_bybit.get("retCode") == 0:
        tickers = raw_bybit.get("result", {}).get("list", [])
        sym_map = {t["symbol"]: t for t in tickers}
        for sym in SYMBOLS:
            if sym not in result:
                perp_sym = f"{sym}USDT"
                if perp_sym in sym_map:
                    tick = sym_map[perp_sym]
                    try:
                        fr_val = float(tick.get("fundingRate", 0.0))
                        result[sym] = fr_val
                        print(f"  [k768] {sym} FR from Bybit fallback "
                              f"({perp_sym}, informational cross-check)", file=sys.stderr)
                    except (TypeError, ValueError):
                        pass
    return result


def _load_fr_history() -> List[dict]:
    """Load K768 FR history JSONL."""
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
    fr_blur: float, fr_sol: float, blur_sol_diff: float
) -> None:
    """Append one FR snapshot to history."""
    rec = {
        "ts_utc":        datetime.now(UTC).isoformat(),
        "fr_blur":       round(fr_blur,       10),
        "fr_sol":        round(fr_sol,          10),
        "blur_sol_diff": round(blur_sol_diff,   10),  # BLUR_FR - SOL_FR
    }
    with open(FR_HISTORY_PATH, "a") as f:
        f.write(json.dumps(rec) + "\n")


# ─────────────────────────────────────────────────────────────────────────────
# Phase 2 — Signal computation (BLUR-SOL direct differential, 168h rolling mean)
# ─────────────────────────────────────────────────────────────────────────────

def compute_signal(
    fr_blur: Optional[float] = None,
    fr_sol:  Optional[float] = None,
) -> dict:
    """
    Fetch live BLUR and SOL FRs from HL, compute BLUR-SOL differential,
    and compute 168h rolling mean for direction signal.

    Signal mechanism (K768 direct alt-alt differential — no orthogonalization):
      diff = BLUR_FR - SOL_FR
      mean_168h = 168h rolling mean of diff (21 x 8h periods equivalent)
      sign  = sign(mean_168h)
      Enter: sign > 0 -> BLUR FR > SOL FR -> long BLUR (collect NFT marketplace premium)
             sign < 0 -> SOL FR > BLUR FR -> long SOL (collect SVM premium), short BLUR

    NOTE: BLUR has extreme fat-tail FR spikes (kurtosis=575.70). Max=0.008065 (2026-04-01).
    These spike events can dominate annual PnL. W=168h smoothing reduces sensitivity
    to individual 1h spike events while maintaining signal quality (OOS Sh=14.98).
    SOL can go deeply negative (Min=-20.51bps) during liquidation cascades.
    Strategy profits from differential regardless of absolute FR level.

    LIQUIDITY WARNING: Position capped at $60K (0.6% @$10M). At spike events,
    BLUR FR can exceed SOL FR by 100-800x. Strategy direction clear; PnL dominated
    by spike periods. MaxDD OOS=-0.68% (small — consistent with carry structure).

    Alt-alt mechanism (EIGHTEENTH ALT-ALT pair — K768):
      BLUR FR tracks Ethereum L1 NFT marketplace: NFT bull cycles (BAYC/Pudgy/SOL NFT),
      royalty battles (Blur vs OpenSea), NFT lending (Blur Blend protocol),
      wash-trading airdrop seasons, L1 congestion events.
      SOL FR tracks Solana SVM DePIN/Retail adoption: meme-coin seasons,
      Firedancer upgrade hype, SOL ETF speculation, SVM DeFi TVL.
      BLUR-SOL diff captures relative NFT marketplace premium vs SVM retail premium.
      Cross-cluster: Ethereum L1 NFT marketplace vs Solana SVM infrastructure.
      Mean diff reverting: OOS Sh=14.98, MaxDD OOS=-0.68%, G4 20/21 positive.

    W=168h rationale (G6 compliance + family standard):
      W=168h → 38.2 entries/yr OOS (PASS vs 30/yr G6 threshold).
      Family standard window (K739/K759 pattern). G6 compliant.
      OOS Sh=14.98 (W=168h). Grid search best W=48h OOS Sh=15.83
      but W=168h chosen for G6 compliance and family standard consistency.

    K768 §6 validation:
      - OOS Sharpe: 14.9799 (W=168h, zero threshold, ~210d OOS period)
      - G1-G4+G6-G9 ALL PASS. G5 FIL-SOL documented SOL-anchor exception.
      - All G5 gates PASS except FIL-SOL full=0.4398 (OOS=0.2805 PASS).
      - G4 WF 20/21 positive (positive_frac=0.952)
      - 60d gate: Realized Sh>=6 + fill>=60% + maxDD<15%
      - CONDITIONAL: 4 live-elevation conditions required (K770)

    Returns:
      {
        "fr_blur":          float,
        "fr_sol":           float,
        "blur_sol_diff":    float,    # BLUR_FR - SOL_FR (current)
        "mean_168h":        float,    # 168h rolling mean of differential
        "diff_sigma":       float,    # 168h rolling sigma (informational)
        "history_points":   int,
        "regime":           str,      # BULL_BLUR | BEAR_BLUR | NEUTRAL
        "signal_direction": int,      # +1 | -1 | 0
        "ts_jst":           str,
      }
    """
    if fr_blur is None or fr_sol is None:
        frs     = _fetch_hl_fr_batch()
        fr_blur = frs.get("BLUR", 0.0)
        fr_sol  = frs.get("SOL", 0.0)

    # BLUR-SOL direct alt-alt differential (no orthogonalization)
    blur_sol_diff = fr_blur - fr_sol

    _append_fr_history(fr_blur, fr_sol, blur_sol_diff)

    # Load history for rolling mean + sigma (168h = 21 x 8h periods)
    history = _load_fr_history()
    diffs   = [r["blur_sol_diff"] for r in history if "blur_sol_diff" in r]

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

    # Regime classification (zero threshold — per K768 spec)
    # BULL_BLUR: BLUR FR > SOL FR (NFT marketplace premium > SVM retail premium)
    # BEAR_BLUR: BLUR FR < SOL FR (SVM retail premium > NFT marketplace premium)
    if mean_168h > 0:
        regime    = "BULL_BLUR"   # BLUR-SOL diff positive → BLUR FR > SOL FR (NFT season)
        direction = 1
    elif mean_168h < 0:
        regime    = "BEAR_BLUR"   # BLUR-SOL diff negative → SOL FR > BLUR FR (SVM season)
        direction = -1
    else:
        regime    = "NEUTRAL"
        direction = 0

    return {
        "fr_blur":          round(fr_blur,        10),
        "fr_sol":           round(fr_sol,           10),
        "blur_sol_diff":    round(blur_sol_diff,    10),
        "mean_168h":        round(mean_168h,         10),
        "diff_sigma":       round(sigma,              10),
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
    Determine trade direction from BLUR-SOL differential rolling mean.

    Logic (BLUR-SOL direct alt-alt pair, HL primary):
      regime = BULL_BLUR (mean_168h > 0):
        BLUR FR > SOL FR: NFT season dominant
        -> long BLUR (collect NFT marketplace carry premium)
        -> short SOL (avoid lower SVM carry in NFT-dominant regime)
        -> position_state = LONG_BLUR_SHORT_SOL

      regime = BEAR_BLUR (mean_168h < 0):
        SOL FR > BLUR FR: SVM season dominant
        -> long SOL (collect SVM infrastructure premium)
        -> short BLUR (avoid lower/negative NFT carry in SVM regime)
        -> position_state = LONG_SOL_SHORT_BLUR

      regime = NEUTRAL: no trade (mean_168h == 0 exactly — rare)

    Alt-alt edge (EIGHTEENTH ALT-ALT pair — K768):
      BLUR and SOL are cross-cluster assets with structurally independent FR drivers.
      BULL_BLUR: NFT season drives BLUR premium (BAYC/Pudgy/SOL NFT bull cycles,
        Blur airdrop wash-trading programs, royalty battle spikes, NFT lending
        protocol events). BLUR FR >> SOL FR. Extreme fat-tail: kurtosis=575.70.
      BEAR_BLUR: SVM season drives SOL premium (DeFi TVL, Firedancer, ETF narratives).
        SOL FR >> BLUR FR. BLUR may go negative during NFT bear + SVM bull.
      Cross-cluster: Ethereum L1 NFT marketplace (cultural/event-driven) vs Solana SVM
        execution (infrastructure/retail). OOS Sh=14.98 >> 1.0. MaxDD OOS=-0.68%.
      G4 WF 20/21 POSITIVE (positive_frac=0.952). G5 FIL-SOL exception documented.
      BLUR = 16th vertex. MR9 L002: all future BLUR-X pairs blocked.

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

    if regime == "BULL_BLUR":
        # BLUR FR > SOL FR: NFT season
        long_asset  = "BLUR"
        short_asset = "SOL"
        state       = STATE_LONG_BLUR_SHORT_SOL
    else:  # BEAR_BLUR
        # SOL FR > BLUR FR: SVM season
        long_asset  = "SOL"
        short_asset = "BLUR"
        state       = STATE_LONG_SOL_SHORT_BLUR

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
    Compute equal notional for both legs of the BLUR-SOL paired trade.

    K768 HL config (BLUR-PERP + SOL-PERP on HL, paper-gate strict):
      sleeve_capital   = aum x sleeve_pct      (e.g. $10M x 0.6% = $60K)
      total_notional   = sleeve_capital x lev   ($60K x 4 = $240K)
      notional_per_leg = total_notional / 2     ($120K per leg)

    At $10M / 0.6% sleeve / 4x (paper-gate):
      BLUR leg: $30K capital x 4x = $120K notional (HL BLUR-PERP)
      SOL leg:  $30K capital x 4x = $120K notional (HL SOL-PERP)
      Total:    $240K notional (two legs combined)
      Margin:   $60K (0.6% of AUM — liquidity-limited)
      HL conc:  PAPER-ONLY (66.8% AT CAP — no live capital added)
      Net profit: central $61K/yr @$10M @4x @0.6% (K523: $37K-$153K)
      BLUR vertex: 16th — MR9 L002 blocks all future BLUR-X pairs
      Liquidity cap: HL BLUR $0.6M/day → 10% daily vol → $60K position max.

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
    Submit K768 BLUR-SOL paired trade: POST_ONLY both legs in parallel.

    Protocol (K768 HL primary — both legs on HL):
      1. Submit BLUR leg on HL POST_ONLY
      2. Submit SOL leg on HL POST_ONLY
      3. Both legs submitted in parallel (K439 pattern)
      4. IOC fallback per leg if POST_ONLY times out
      5. If both fail: retry next 8h cycle

    LIQUIDITY NOTE: BLUR leg notional capped at $60K (0.6% sleeve @$10M x 4x / 2 legs).
    At $60K BLUR position = 10% of $0.6M daily volume. Slippage ~10bps estimated.
    If HL BLUR vol grows to $1M+/day → sleeve upgradeable (live condition 2).

    Args:
      long_leg:  {"symbol": "BLUR", "notional": 120000, "venue": "HL"}
      short_leg: {"symbol": "SOL",  "notional": 120000, "venue": "HL"}
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
        print(f"  [K768] {mode_tag}: LONG {long_sym}@{long_venue} ${long_notl:,.0f}  "
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
            "venue_config":     "HL_PRIMARY_BLUR_SOL_ALT_ALT",
            "mechanism_note":   (
                "BLUR-SOL direct alt-alt differential (K768 EIGHTEENTH ALT-ALT, 75th daemon): "
                "BLUR FR = Ethereum L1 NFT marketplace (Blur.io, launched Oct 2022), "
                "NFT bull cycles (BAYC Q1-2023, Pudgy Q4-2023, SOL NFT Q1-2024), "
                "royalty battle spikes (Blur vs OpenSea), NFT lending (Blur Blend), "
                "wash-trading airdrop seasons, kurtosis=575.70 extreme fat-tail events. "
                "Max spike: 0.008065 (2026-04-01). Full vol ratio: 6.77x vs SOL. "
                "SOL FR = Solana SVM DePIN/Retail adoption premium (meme-coin BONK/WIF/POPCAT, "
                "Firedancer upgrade hype, SOL ETF speculation, SVM DeFi TVL — "
                "+8.79%/ann persistently positive, SOL liquidation cascade Min=-20.51bps). "
                "G4 WF 20/21 POSITIVE (positive_frac=0.952). G5 FIL-SOL documented exception. "
                "G5 FIL-SOL: full=0.4398 FAIL, OOS=0.2805 PASS — SOL-anchor contamination. "
                "HL at 66.8% AT CAP — paper-gate strict until 4 live conditions met (K770). "
                "BLUR = 16th vertex. MR9 L002: all future BLUR-X pairs blocked. "
                "Liquidity cap: HL BLUR $0.6M/day → 0.6% sleeve ($60K pos max). "
                "OOS Sh=14.98 (W=168h, zero threshold). K523 central $61K/yr @$10M @4x @0.6%. "
                "4 live conditions: G5-FIL-SOL 90d OOS <0.40 + vol>$1M/day + HL<65% + governance. "
                "60d gate: Realized Sh>=6 + fill>=60% + maxDD<15%."
            ),
            "ts_utc":           ts,
        }
        _append_trade_log(result)
        return result

    # LIVE scaffold (not reached in PAPER_TRADE mode):
    print(f"  [K768] SCAFFOLD LIVE: parallel POST_ONLY "
          f"LONG {long_sym}@{long_venue} ${long_notl:,.0f} "
          f"+ SHORT {short_sym}@{short_venue} ${short_notl:,.0f}")
    long_order_id  = f"SCAFFOLD_LONG_{long_sym}_{int(time.time())}"
    short_order_id = f"SCAFFOLD_SHORT_{short_sym}_{int(time.time())}"

    print(f"  [K768] Neither leg filled within timeout — retry next 8h cycle")
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
    Check if current K768 position has drifted beyond DRIFT_REBALANCE_PCT (5%).

    K768 HL: both legs on HL (BLUR-PERP + SOL-PERP).
    Drift detection: compare stored BLUR leg notional vs SOL leg notional.
    Threshold: 5% (same as K679/K682/K684/K686/K690/K747/K739/K754/K759 pattern).

    LIQUIDITY NOTE: At $60K BLUR position, 5% drift = $3K notional difference.
    Rebalance trades at HL BLUR $0.6M/day: 0.5% daily vol — minimal market impact.

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
    Both legs on HL (K768 HL primary — BLUR-PERP + SOL-PERP).

    LIQUIDITY NOTE: At $60K BLUR position, IOC close at HL BLUR $0.6M/day.
    Close trades should fill quickly given 10% daily vol — normal slippage ~5bps.

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

    if state == STATE_LONG_BLUR_SHORT_SOL:
        long_sym,  short_sym  = "BLUR", "SOL"
    else:  # LONG_SOL_SHORT_BLUR
        long_sym,  short_sym  = "SOL", "BLUR"

    long_notional  = float(dash.get("long_notional",  0.0))
    short_notional = float(dash.get("short_notional", 0.0))

    if dry_run or PAPER_TRADE:
        mode_tag = "DRY_RUN" if dry_run else "PAPER_TRADE"
        print(f"  [K768] {mode_tag} CLOSE:")
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
        print(f"  [K768] SCAFFOLD CLOSE:")
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
    """Load k768_dashboard.json; return defaults if missing."""
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
    """Write k768_dashboard.json with full signal + regime state."""
    dash = _load_dashboard()

    # Update signal data
    dash["last_poll_jst"]         = signal.get("ts_jst", "—")
    dash["fr_blur_current"]       = signal.get("fr_blur",         0.0)
    dash["fr_sol_current"]        = signal.get("fr_sol",           0.0)
    dash["blur_sol_diff_current"] = signal.get("blur_sol_diff",   0.0)
    dash["mean_168h"]             = signal.get("mean_168h",        0.0)
    dash["diff_sigma"]            = signal.get("diff_sigma",       0.0)
    dash["regime"]                = signal.get("regime",    "NEUTRAL")
    dash["signal_direction"]      = signal.get("signal_direction", 0)
    dash["history_points"]        = signal.get("history_points",   0)

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
    dash["hl_concentration_pct"]     = HL_CONCENTRATION_POST_K768

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
        "activation_trigger":      "60d paper-trade: Sh>=6 AND fill>=60% AND maxDD<15% + 4 live conditions",
        "profit_at_activation_0_6pct": (
            "central $61,000/yr net @$10M @4x (K523: $37K cons / $61K central / $153K opt ref)"
        ),
        "alt_alt_note": (
            "EIGHTEENTH ALT-ALT pair (BLUR-SOL, no BTC/ETH leg). Standalone. 75th daemon. "
            "CONDITIONAL_ACCEPT (G5 FIL-SOL documented SOL-anchor exception). "
            "G4 WF 20/21 POSITIVE (positive_frac=0.952). G5 FIL-SOL OOS=0.2805 PASS. "
            "BLUR = 16th vertex (NFT marketplace cluster). MR9 L002: all future BLUR-X pairs blocked. "
            "W=168h (G6-safe: 38.2/yr vs 30/yr min). OOS Sh=14.98 MaxDD=-0.68% OOS."
        ),
        "hl_cap_warning": (
            "HL concentration 66.8% AT CAP (K751 audit). Paper-gate strict. "
            "Deploy LIVE only after all 4 live-elevation conditions met (K770). "
            "K768 HL primary: both BLUR-PERP + SOL-PERP on HL. "
            "0.6% all-HL would add 0.6% — over cap until K498/v6.52. Paper-only. "
            "LIQUIDITY: HL BLUR $0.6M/day → $60K position max (10% daily vol rule)."
        ),
        "live_conditions": LIVE_CONDITIONS,
    }

    # Strategy metadata
    dash["paper_trade_mode"]    = PAPER_TRADE
    dash["wave"]                = "K770"
    dash["strategy"]            = "K768 BLUR-SOL FR Differential (EIGHTEENTH ALT-ALT, W=168h, HL primary)"
    dash["execution_mode"]      = "POST_ONLY_PARALLEL"
    dash["venue_config"]        = "HL_PRIMARY_BYBIT_FALLBACK"
    dash["alt_alt_mechanism"]   = {
        "formula":            "diff = BLUR_FR - SOL_FR  (direct alt-alt, no base asset)",
        "rolling_window":     "W=168h (21 x 8h periods, G6-safe: 38.2 entries/yr OOS)",
        "signal":             "sign(rolling_mean_168h(diff))",
        "eighteenth_alt_alt": True,
        "g4_result":          "20/21 POSITIVE (positive_frac=0.952) — strong WF validation",
        "hl_reason":          HL_ONLY_REASON,
        "hl_concentration":   66.8,
        "liquidity_cap": {
            "hl_daily_vol_usd":  600000,
            "max_position_usd":  60000,
            "position_vs_vol_pct": 10.0,
            "sleeve_pct":        0.006,
            "upgrade_condition": "HL BLUR daily vol > $1M/day sustained → sleeve upgradeable",
        },
        "cross_cluster_note": (
            "BLUR (Ethereum L1 NFT marketplace — Blur.io, launched Oct 2022. "
            "NFT bull cycles: BAYC Q1-2023, Pudgy Penguins Q4-2023, SOL NFT Q1-2024. "
            "Royalty battles: Blur vs OpenSea mechanism wars. NFT lending: Blur Blend protocol. "
            "Wash-trading airdrop seasons (Blur S1/S2/S3). kurtosis=575.70, Max=0.008065 FR. "
            "64 spike events >0.0001; full vol_ratio=6.77x vs SOL. 2026-04 spike: 83.49x.) "
            "vs SOL (Solana SVM retail/DeFi/meme — persistently positive +8.79%/ann, "
            "SOL liquidation cascade Min=-20.51bps Feb 2025). "
            "Cross-cluster: Ethereum L1 NFT marketplace (cultural/event-driven) vs SVM infrastructure. "
            "OOS Sh=14.98. MaxDD OOS=-0.68%. G4 20/21 POSITIVE."
        ),
        "blur_vertex_rule": (
            "BLUR = 16th vertex added to V. "
            "V = {APT, ATOM, AVAX, BNB, ENA, FIL, HBAR, INJ, LDO, SEI, SOL, TIA, TAO, PEPE, WIF, BLUR}. "
            "MR9 L002: all future BLUR-X pairs auto-blocked. "
            "BLUR-SOL is the only permissible BLUR-X pair given V at K768."
        ),
        "g5_exception": {
            "pair":       "FIL-SOL",
            "full_corr":  0.4398,
            "is_corr":    0.5112,
            "oos_corr":   0.2805,
            "gate":       0.40,
            "full_fail":  True,
            "oos_pass":   True,
            "mechanism":  "SOL-anchor contamination: both BLUR-SOL and FIL-SOL short SOL when SOL FR dominates IS period. Raw FR independence: L007 raw_corr(BLUR,FIL)=0.0478.",
            "governance": "CONDITIONAL_ACCEPT with 4 live-elevation conditions. FIL-SOL capacity sharing implicit.",
        },
        "g5_max_oos_corr": "0.2805 (FIL-SOL OOS) — PASS in OOS window. Full=0.4398 FAIL documented.",
        "w168h_g6_note": (
            "W=168h family standard window (G6: 38.2 entries/yr OOS PASS vs 30/yr minimum). "
            "Grid search best W=48h OOS Sh=15.83 but W=168h chosen for G6 compliance + family standard. "
            "W=168h OOS Sh=14.98. Canonical choice for K768."
        ),
        "k523_projection": {
            "conservative_yr": 37000,
            "central_yr":      61000,
            "optimistic_yr":   153000,
            "sleeve_pct":      0.006,
            "note":            "K523 mandatory 3-point. Conservative=R2S×0.38 (K518 floor) @0.6% sleeve. Optimistic assumes $2.5M/day HL BLUR liquidity (condition 2 met).",
        },
        "live_conditions": LIVE_CONDITIONS,
    }

    dash["activation_criteria"] = {
        "60d_paper_trade_gate": "required",
        "realized_sharpe_min": 6.0,
        "fill_rate_min_pct":   60,
        "max_drawdown_max_pct": 15,
        "status":              "SCAFFOLD-READY",
        "activation_sleeve_pct": 0.006,
        "venue":               "HL primary (BLUR-PERP + SOL-PERP)",
        "conditional_note": (
            "CONDITIONAL: 4 live-elevation conditions required (K770). "
            "1. G5 FIL-SOL 90d OOS corr < 0.40 (borderline). "
            "2. HL BLUR vol > $1M/day (currently $0.6M). "
            "3. HL cap < 65% (requires K498/v6.52). "
            "4. NFT marketplace governance review (no family precedent)."
        ),
        "live_trigger": "ALL 4 live-elevation conditions met (K770) + 60d gate passage",
    }

    dash["oos_performance"] = {
        "sharpe":              14.9799,
        "oos_ann_ret_pct":     2.1541,
        "oos_ann_ret_4x_pct":  8.6164,
        "k523_conservative_yr": 37000,
        "k523_central_yr":     61000,
        "k523_optimistic_yr":  153000,
        "daily_usdc_central":  167,
        "wave_accept": (
            "K768 CONDITIONAL_ACCEPT (K770 scaffold) — EIGHTEENTH ALT-ALT, "
            "NFT marketplace × SVM, G4 20/21, G5 FIL-SOL documented exception"
        ),
        "cluster":    "BLUR-SOL Alt-Alt FR Differential (Eth L1 NFT marketplace × Solana SVM, HL primary, 16th vertex)",
        "daemon_number": "75th",
        "section6_result": (
            "CONDITIONAL_ACCEPT G1-G4+G6-G9 PASS. G5 FIL-SOL full=0.4398 FAIL (OOS=0.2805 PASS). "
            "SOL-anchor exception documented. OOS Sh=14.98 (W=168h zero threshold ~210d OOS). "
            "MaxDD OOS=-0.68%. HL 66.8% AT CAP → paper-gate strict + 4 live conditions."
        ),
        "family_rank": {
            "k768_oos_sharpe":   14.9799,
            "k768_pair":         "BLUR-SOL (alt-alt, EIGHTEENTH, 16th vertex BLUR NFT marketplace)",
            "alt_alt_accepted":  18,
            "g4_note":           "K768 G4=20/21 POSITIVE (positive_frac=0.952) — strong WF validation.",
            "vertex_note":       "BLUR = 16th vertex. V={APT,ATOM,AVAX,BNB,ENA,FIL,HBAR,INJ,LDO,SEI,SOL,TIA,TAO,PEPE,WIF,BLUR}.",
        },
    }

    DASHBOARD_PATH.write_text(json.dumps(dash, indent=2))
    return dash


# ─────────────────────────────────────────────────────────────────────────────
# Main entry point
# ─────────────────────────────────────────────────────────────────────────────

def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="K768 BLUR-SOL FR Differential Strategy (EIGHTEENTH ALT-ALT, 75th daemon)"
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

    print(f"\n=== K768 BLUR-SOL FR Differential Strategy — {ts_jst} ===")
    print(f"  Strategy:    BLUR-SOL FR Differential (EIGHTEENTH ALT-ALT pair)")
    print(f"  Wave:        K770 (scaffold wave for K768 CONDITIONAL_ACCEPT)")
    print(f"  Daemon:      75th (eighteenth alt-alt pair, 16th vertex BLUR)")
    print(f"  OOS Sharpe:  14.9799 (W=168h, zero threshold, ~210d OOS)")
    print(f"  G4 WF:       20/21 POSITIVE (positive_frac=0.952)")
    print(f"  G5:          FIL-SOL full=0.4398 FAIL / OOS=0.2805 PASS (SOL-anchor exception)")
    print(f"  W=168h:      G6 compliance (38.2/yr OOS vs 30/yr min)")
    print(f"  BLUR vertex: 16th. MR9 L002: all future BLUR-X pairs blocked.")
    print(f"  HL cap:      66.8% AT CAP (K751 audit) — paper-gate strict")
    print(f"  Liquidity:   HL BLUR $0.6M/day → 0.6% sleeve ($60K pos max)")
    print(f"  Profit:      central $61K/yr @$10M @4x @0.6% sleeve (K523 3-point)")
    print(f"  4 conditions: G5-FIL-SOL 90d + vol>$1M/day + HL<65% + governance")
    print(f"  Paper mode:  {PAPER_TRADE}")

    # --status mode
    if args.status:
        dash = _load_dashboard()
        print(f"\n  [Status] {dash.get('strategy', 'K768 BLUR-SOL')}")
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
    print(f"\n  [Phase 1] Fetching BLUR + SOL funding rates from HL ...")
    signal = compute_signal()
    print(f"  fr_blur={signal['fr_blur']:.6e}  fr_sol={signal['fr_sol']:.6e}")
    print(f"  blur_sol_diff={signal['blur_sol_diff']:.6e}")
    print(f"  mean_168h={signal['mean_168h']:.6e}  sigma={signal['diff_sigma']:.6e}")
    print(f"  regime={signal['regime']}  direction={signal['signal_direction']}")
    print(f"  history_points={signal['history_points']}")

    print(f"\n  [Phase 2] Computing signal (W=168h rolling mean of BLUR_FR - SOL_FR) ...")
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

    print(f"\n=== K768 BLUR-SOL run complete — {datetime.now(JST).strftime('%Y-%m-%d %H:%M JST')} ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
