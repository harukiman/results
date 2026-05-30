#!/usr/bin/env python3
"""
k759_wif_sol_run.py — K759 WIF-SOL FR Differential Strategy
============================================================
SEVENTEENTH ALT-ALT pair: WIF vs SOL (Solana meme leader × Solana SVM).
Signal: WIF_FR - SOL_FR
W=168h rolling mean (7d — standard family window; G6 compliant: 31.2/yr OOS)
HL primary, Bybit fallback
HL concentration: 66.8% AT CAP → paper-gate strict (K498/v6.52 required for live)

K759 WIF-SOL alt-alt hypothesis:
  WIF (dogwifhat — Solana-native SPL meme coin, launched Jan 2024):
    FR driven by Solana meme season timing (BONK/WIF/POPCAT rotation cycles),
    WIF CEX listings (Coinbase Apr 2024, Binance), meme coin retail FOMO cycles,
    SVM on-chain DEX liquidity (Raydium/Jupiter WIF pairs), social media virality.
    SOL-native meme: amplifies SOL FR by ~1.3x during Solana bull peaks.
    FR spikes: P99=1.416bps, Max=3.164bps/hr during Solana meme peaks.
    Q2 2024 WIF peak: WIF +0.34bps vs SOL +0.22bps mean differential (+0.13bps).
    Q4 2024: WIF +0.43bps vs SOL +0.34bps (+0.09bps differential maintained).
    OOS carries differential despite SOL-native co-movement (OOS FR corr 0.054).
  SOL (Solana SVM L1):
    FR driven by retail momentum, Phantom wallet adoption, Firedancer upgrade,
    Solana ETF narrative flows, SVM DeFi TVL (Jupiter/Drift/Jito).
    SOL FR mean +8.82%/ann — persistently positive structural retail demand.
    SOL extreme negative FR: Min=-20.51bps (liquidation cascade Feb 2025).
  Alt-alt mechanism: WIF (Solana meme cluster, SOL-native SPL) vs SOL (Solana SVM L1).
    Both SOL-ecosystem — WIF amplifies SOL meme FR without full SOL infra correlation.
    L011 rule: raw_corr(WIF_fr, SOL_fr) = 0.487 PASS (< 0.50 SOL-ecosystem threshold).
    G5w: WIF-SOL vs PEPE-SOL corr=0.382 PASS (< 0.40, 0.018 margin — reduced sleeve).
    Structurally distinct FR regimes: meme rotation timing vs SVM infrastructure cycles.
  SEVENTEENTH alt-alt pair. OOS Sharpe 24.45. W=168h. 12/12 WF ALL POSITIVE.
  All G5 gates PASS. MaxDD OOS only -0.216%.
  G8 CONDITIONAL: HL+Bybit+OKX confirmed (Bybit=WIF standard denomination).
  WIF becomes 15th vertex. All future WIF-X blocked (MR9 L002).

K759 §6 validation (CONDITIONAL_ACCEPT — G1-G9 ALL PASS):
  - OOS Sharpe: 24.4547 (W=168h, zero threshold, ~210d OOS)
  - OOS Ann Return: $54K central @$10M @4x @2.0% sleeve (K523 3-point)
  - W=168h rolling mean, zero threshold (sign of diff) — G6 compliant (31.2/yr)
  - G4 walk-forward: 12/12 folds positive (min_sh=9.895)
  - G5 all gates PASS (max_corr=0.3819 G5w PEPE-SOL — below 0.40 threshold)
  - G5w PEPE-SOL=0.382 proximity: 0.018 margin → reduced sleeve 2.0% (vs 2.5% standard)
  - L011 SOL-direct corr=0.487 PASS (< 0.50 SOL-ecosystem threshold, borderline)
  - G8: HL+Bybit+OKX confirmed (WIF: HL WIFUSDC, Bybit WIFUSDT, OKX WIF-PERP)
  - CONDITIONAL: HL 66.8% AT CAP → paper-gate strict until K498/v6.52
  - L011 borderline (0.487) — monthly recheck rule

K759 WIF-SOL vertex addition (15th vertex, SOL meme cluster):
  V (before K759) = {APT, ATOM, AVAX, BNB, ENA, FIL, HBAR, INJ, LDO, SEI, SOL, TIA, TAO, PEPE}
  V (after K759)  = {APT, ATOM, AVAX, BNB, ENA, FIL, HBAR, INJ, LDO, SEI, SOL, TIA, TAO, PEPE, WIF}
  WIF = 15th vertex (Solana meme cluster, SOL-native SPL token).
  MR9 L002: all future WIF-X pairs are auto-blocked (WIF exhausted as new vertex).
  WIF-SOL is the only permissible WIF-X pair given V composition at K759.

G5w PEPE-SOL proximity note (K761):
  G5w full_corr(WIF-SOL signal, PEPE-SOL signal) = 0.382 (0.018 margin below 0.40).
  WIF-SOL and PEPE-SOL share the SOL leg — both are meme-vs-SOL signals.
  ETH meme (PEPE, cross-chain) vs SOL meme (WIF, on-chain native) have distinct triggers.
  Reduced sleeve 2.0% (vs standard 2.5%) to manage G5w cross-sleeve concentration.
  Cross-sleeve monitor: WIF-SOL + PEPE-SOL combined sleeve = 4.0% (2.0% + 2.0%).

L011 borderline note (K761):
  raw_corr(WIF_fr, SOL_fr) = 0.487 PASS (< 0.50 threshold, OOS=0.054 confirms independence).
  WIF is the highest SOL-beta alt-alt candidate. Monthly recheck required.
  If OOS live corr drifts toward 0.50, sleeve reduces to 1.5% or pair closes.

K523 3-point profit projection (@$10M @4x @2.0% sleeve):
  Conservative: $20,655/yr  (R2S=38% floor, K518 floor, OOS haircut 25%)
  Central:      $54,245/yr  (K523 mandate: 60% realized-to-stated, base case)
  Optimistic:   $76,847/yr  (near-full OOS realization if SOL meme cycle peaks)
  Upper bound:  OOS raw return (NOT central — K523 mandatory)
  Note: 2.0% sleeve → ~$200K margin @$10M; central per K759 eval json=$54,245/yr

Architecture (K679→K747→K754→K759 alt-alt scaffold pattern):
  1. fetch_fr_batch()                  → fetch WIF + SOL FR every 8h from HL
  2. compute_signal(wif_fr, sol_fr)   → 168h rolling mean of (WIF_FR - SOL_FR); sign()
  3. decide_position(signal)           → LONG_WIF_SHORT_SOL | LONG_SOL_SHORT_WIF | NEUTRAL
  4. submit_paired_trade(long, short) → POST_ONLY paired (WIF + SOL legs, HL primary)
  5. daily_rebalance()                 → drift > 5% triggers rebalance
  6. close_paired_position(reason)    → sequential: short first, then long

K761 production scaffold:
  - 72nd daemon (seventeenth alt-alt pair, CONDITIONAL_ACCEPT, G4 12/12)
  - HL primary, Bybit fallback (WIF: HL WIFUSDC-PERP + Bybit WIFUSDT + OKX confirmed)
  - 2.0% sleeve (reduced — G5w PEPE-SOL proximity 0.382, 0.018 margin)
  - $54K central @$10M @4x @2.0% sleeve (K523 3-point: $20.7K-$76.8K)
  - Paper-gate until K498/v6.52 reduces HL concentration
  - 60d paper-trade gate: Realized Sh>=6 + fill>=60% + maxDD<15%
  - 17th alt-alt pair (SOL meme cluster × SVM, 15th vertex WIF)

Execution:
  - HL primary (WIF-PERP + SOL-PERP, HL)
  - Bybit fallback (WIFUSDT-PERP + SOL-PERP, Bybit) — informational
  - POST_ONLY paired execution (K439 pattern)
  - Position: 2.0% sleeve, 4x leverage (paper-gate strict — HL cap 66.8%)
  - 8h cadence (matches FR settlement cycle)
  - W=168h rolling mean (21 x 8h periods — G6-safe: 31.2 entries/yr)

Paper-trade mode is the DEFAULT.  No orders are submitted unless
PAPER_TRADE=False is explicitly set in the environment.

K339 security: REPO_ROOT from __file__, no /Users/ literals.
No new packages — stdlib urllib + json only.

Usage:
  python3 scripts/k759_wif_sol_run.py --dry-run
  python3 scripts/k759_wif_sol_run.py --status
  python3 scripts/k759_wif_sol_run.py --rebalance
  python3 scripts/k759_wif_sol_run.py --close "scheduled exit"
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

DASHBOARD_PATH  = DATA_DIR  / "k759_dashboard.json"
FR_HISTORY_PATH = CACHE_DIR / "k759_fr_history.jsonl"
TRADE_LOG_PATH  = CACHE_DIR / "k759_paper_trades.jsonl"

JST = timezone(timedelta(hours=9))
UTC = timezone.utc

# ── Strategy constants ────────────────────────────────────────────────────────
PAPER_TRADE         = os.environ.get("PAPER_TRADE", "True").lower() != "false"
SLEEVE_PCT          = 0.020         # K759 sleeve = 2.0% of AUM (reduced — G5w proximity)
LEVERAGE            = 4.0           # 4x per K759 analysis
AUM_DEFAULT         = 10_000_000.0  # $10M reference AUM
DRIFT_REBALANCE_PCT = 0.05          # rebalance if legs drift > 5%
IOC_TIMEOUT_SEC     = 300           # 5 min fill window
EMA_PERIOD_HOURS    = 168           # 168h rolling mean (W=168h, G6 compliant: 31.2/yr)
EMA_PERIOD_PERIODS  = EMA_PERIOD_HOURS // 8  # = 21 periods (8h settlement cycle)
SIGNAL_SIGMA_MULT   = 0.0           # zero threshold (sign of rolling mean)
HL_API_URL          = "https://api.hyperliquid.xyz/info"
BYBIT_API_URL       = "https://api.bybit.com"

# ── Venue config ──────────────────────────────────────────────────────────────
# HL primary: WIF-PERP + SOL-PERP on HL
# Bybit fallback: WIFUSDT-PERP + SOL-PERP on Bybit (informational)
# HL concentration: 66.8% AT CAP per K751 audit — paper-gate strict until K498/v6.52.
HL_CONCENTRATION_PRE_K759   = 66.8   # post-K756 reference (K751 audit)
HL_CONCENTRATION_POST_K759  = 66.8   # UNCHANGED — paper-only, no live capital added
HL_ONLY_REASON              = (
    "HL primary: WIF-PERP + SOL-PERP on HL. Bybit WIFUSDT fallback (informational). "
    "OKX WIF confirmed (cross-venue CONFIRMED, 3-venue presence). HL at 66.8% AT CAP (K751 audit). "
    "Paper-gate strict: any live capital would breach 65% ceiling. "
    "Deploy LIVE after K498/v6.52 reduces HL% below 65%."
)

# ── Position state constants ──────────────────────────────────────────────────
STATE_NEUTRAL            = "NEUTRAL"
STATE_LONG_WIF_SHORT_SOL = "LONG_WIF_SHORT_SOL"
STATE_LONG_SOL_SHORT_WIF = "LONG_SOL_SHORT_WIF"

# ── Symbols fetched from HL for FR data ──────────────────────────────────────
SYMBOLS = ("WIF", "SOL")


# ─────────────────────────────────────────────────────────────────────────────
# HTTP helper (stdlib urllib only — no requests)
# ─────────────────────────────────────────────────────────────────────────────

def _http_get(url: str, timeout: int = 10) -> Optional[dict]:
    try:
        req = urllib.request.Request(
            url, headers={"User-Agent": "crypto-lab-k759/1.0"}
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        print(f"  [k759] HTTP error: {e}", file=sys.stderr)
        return None


def _http_post(url: str, payload: dict, timeout: int = 10) -> Optional[dict]:
    try:
        data = json.dumps(payload).encode()
        req  = urllib.request.Request(
            url, data=data,
            headers={"Content-Type": "application/json",
                     "User-Agent": "crypto-lab-k759/1.0"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        print(f"  [k759] HTTP error: {e}", file=sys.stderr)
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Phase 1 — Funding rate fetch (WIF + SOL from HL)
# ─────────────────────────────────────────────────────────────────────────────

def _fetch_hl_fr_batch() -> Dict[str, float]:
    """
    Fetch current 1h funding rates for WIF and SOL from HL.
    Returns {symbol: fr_1h_fraction}.

    HL API: metaAndAssetCtxs (POST).
    K759: HL primary (WIF-PERP + SOL-PERP).
    Bybit fallback: WIFUSDT denomination (informational only).
    WIF HL confirmed: 17519 rows 2024-05-24 to 2026-05-24.

    Note: HL settles 1h funding; W=168h = 168 x 1h periods for rolling mean.
    FR stored as 1h fraction; annualized = fr_1h * 8760.

    Fallback: Bybit /v5/market/tickers — WIFUSDT denomination (informational
    cross-check; 8h interval vs HL 1h settlement — signal cross-check only).
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
        print(f"  [k759] HL partial result {list(result.keys())} — trying Bybit fallback",
              file=sys.stderr)

    # Fallback: Bybit /v5/market/tickers (WIFUSDT denomination — informational)
    bybit_url = f"{BYBIT_API_URL}/v5/market/tickers?category=linear"
    raw_bybit = _http_get(bybit_url)
    if raw_bybit and raw_bybit.get("retCode") == 0:
        tickers = raw_bybit.get("result", {}).get("list", [])
        sym_map = {t["symbol"]: t for t in tickers}
        for sym in SYMBOLS:
            if sym not in result:
                for perp_sym in [f"{sym}USDT", f"{sym}USDC"]:
                    if perp_sym in sym_map:
                        tick = sym_map[perp_sym]
                        try:
                            fr_val = float(tick.get("fundingRate", 0.0))
                            result[sym] = fr_val
                            print(f"  [k759] {sym} FR from Bybit fallback "
                                  f"({perp_sym}, informational cross-check)", file=sys.stderr)
                        except (TypeError, ValueError):
                            pass
                        break
    return result


def _load_fr_history() -> List[dict]:
    """Load K759 FR history JSONL."""
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
    fr_wif: float, fr_sol: float, wif_sol_diff: float
) -> None:
    """Append one FR snapshot to history."""
    rec = {
        "ts_utc":       datetime.now(UTC).isoformat(),
        "fr_wif":       round(fr_wif,       10),
        "fr_sol":       round(fr_sol,         10),
        "wif_sol_diff": round(wif_sol_diff,   10),  # WIF_FR - SOL_FR
    }
    with open(FR_HISTORY_PATH, "a") as f:
        f.write(json.dumps(rec) + "\n")


# ─────────────────────────────────────────────────────────────────────────────
# Phase 2 — Signal computation (WIF-SOL direct differential, 168h rolling mean)
# ─────────────────────────────────────────────────────────────────────────────

def compute_signal(
    fr_wif: Optional[float] = None,
    fr_sol: Optional[float] = None,
) -> dict:
    """
    Fetch live WIF and SOL FRs from HL, compute WIF-SOL differential,
    and compute 168h rolling mean for direction signal.

    Signal mechanism (K759 direct alt-alt differential — no orthogonalization):
      diff = WIF_FR - SOL_FR
      mean_168h = 168h rolling mean of diff (21 x 8h periods equivalent)
      sign  = sign(mean_168h)
      Enter: sign > 0 -> WIF FR > SOL FR -> long WIF (collect SOL meme premium), short SOL
             sign < 0 -> SOL FR > WIF FR -> long SOL (collect SVM premium), short WIF

    NOTE: WIF is SOL-native — both tokens share Solana on-chain leverage dynamics.
    During SOL liquidation cascades (SOL min=-20.51bps), WIF also faces negative FR
    (WIF min=-18.98bps). Strategy captures the differential, not absolute level.
    OOS FR corr=0.054 (near-zero OOS despite full-period corr=0.487): strong signal.
    G5w PEPE-SOL proximity=0.382 (0.018 margin) → 2.0% sleeve (reduced from 2.5%).

    Alt-alt mechanism (SEVENTEENTH ALT-ALT pair — K759):
      WIF FR tracks Solana meme rotation cycles: BONK/WIF/POPCAT timing,
      WIF CEX listing catalysts (Coinbase Apr 2024), meme coin FOMO cycles,
      SVM DEX liquidity (Raydium/Jupiter WIF pairs), social media virality.
      WIF amplifies SOL FR by ~1.3x during Solana bull peaks (vol_ratio=1.347x).
      SOL FR tracks Solana SVM infrastructure: DePIN, Phantom adoption, Firedancer,
      SOL ETF speculation, SVM DeFi TVL (Jupiter/Drift/Jito). +8.82%/ann persistent.
      WIF-SOL diff captures relative SOL meme premium vs SVM infrastructure premium.
      OOS corr=0.054 despite full-period corr=0.487: regime-switch cleans signal in OOS.
      Mean diff reverting: OOS Sh=24.45, MaxDD OOS=-0.216%, G4 12/12 positive.

    W=168h rationale (G6 compliance):
      W=168h → 31.2 entries/yr OOS (ABOVE 30/yr G6 threshold — PASS).
      W=84h  → 59.0 entries/yr OOS (PASS, OOS Sh=26.51 — marginally higher Sharpe).
      W=168h chosen as family standard window for consistency with alt-alt family.
      W=48h best OOS Sh=28.07 but 85/yr entries may overfit to meme spike timing.
      W=168h canonical for K759 (family standard; G6-compliant 31.2/yr).

    K759 §6 validation:
      - OOS Sharpe: 24.4547 (W=168h, zero threshold, ~210d OOS period)
      - OOS Ann Return: $54K central @$10M @4x @2.0% sleeve (K523 3-point)
      - All G5 checks PASS (max_corr=0.3819 G5w PEPE-SOL — below 0.40)
      - G4 WF 12/12 all positive (min_sh=9.895)
      - 60d gate: Realized Sh>=6 + fill>=60% + maxDD<15%
      - CONDITIONAL: HL 66.8% AT CAP → paper-gate strict

    Returns:
      {
        "fr_wif":           float,
        "fr_sol":           float,
        "wif_sol_diff":     float,    # WIF_FR - SOL_FR (current)
        "mean_168h":        float,    # 168h rolling mean of differential
        "diff_sigma":       float,    # 168h rolling sigma (informational)
        "history_points":   int,
        "regime":           str,      # BULL_WIF | BEAR_WIF | NEUTRAL
        "signal_direction": int,      # +1 | -1 | 0
        "ts_jst":           str,
      }
    """
    if fr_wif is None or fr_sol is None:
        frs    = _fetch_hl_fr_batch()
        fr_wif = frs.get("WIF", 0.0)
        fr_sol = frs.get("SOL", 0.0)

    # WIF-SOL direct alt-alt differential (no orthogonalization)
    wif_sol_diff = fr_wif - fr_sol

    _append_fr_history(fr_wif, fr_sol, wif_sol_diff)

    # Load history for rolling mean + sigma (168h = ~21 x 8h periods)
    history = _load_fr_history()
    diffs   = [r["wif_sol_diff"] for r in history if "wif_sol_diff" in r]

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

    # Regime classification (zero threshold — per K759 spec)
    # BULL_WIF: WIF FR > SOL FR (Solana meme rotation dominant)
    # BEAR_WIF: WIF FR < SOL FR (SVM infrastructure premium dominant)
    if mean_168h > 0:
        regime    = "BULL_WIF"   # WIF-SOL diff positive → WIF FR > SOL FR (meme season)
        direction = 1
    elif mean_168h < 0:
        regime    = "BEAR_WIF"   # WIF-SOL diff negative → SOL FR > WIF FR (SVM season)
        direction = -1
    else:
        regime    = "NEUTRAL"
        direction = 0

    return {
        "fr_wif":           round(fr_wif,        10),
        "fr_sol":           round(fr_sol,          10),
        "wif_sol_diff":     round(wif_sol_diff,    10),
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
    Determine trade direction from WIF-SOL differential rolling mean.

    Logic (WIF-SOL direct alt-alt pair, HL primary):
      regime = BULL_WIF (mean_168h > 0):
        WIF FR > SOL FR: Solana meme season dominant
        -> long WIF (collect SOL meme rotation premium)
        -> short SOL (avoid lower SVM infra carry in meme-dominant regime)
        -> position_state = LONG_WIF_SHORT_SOL

      regime = BEAR_WIF (mean_168h < 0):
        SOL FR > WIF FR: SVM infrastructure season dominant
        -> long SOL (collect SVM DePIN/DeFi premium)
        -> short WIF (avoid lower/negative meme carry in SVM regime)
        -> position_state = LONG_SOL_SHORT_WIF

      regime = NEUTRAL: no trade (mean_168h == 0 exactly — rare)

    Alt-alt edge (SEVENTEENTH ALT-ALT pair — K759):
      WIF and SOL are same-ecosystem assets but with structurally distinct FR timing.
      BULL_WIF: Solana meme rotation drives WIF premium (WIF CEX listings, BONK/WIF/POPCAT
        rotation, social media virality, meme FOMO cycles). WIF FR >> SOL FR.
      BEAR_WIF: SVM infrastructure drives SOL premium (DeFi TVL, Firedancer, ETF narratives,
        Phantom adoption). SOL FR >> WIF FR. Note: SOL liquidation cascade (SOL -20.51bps,
        WIF -18.98bps) — both negative, but SOL more extreme; strategy favors LONG WIF in this.
      Cross-regime: SOL meme rotation (WIF) vs Solana SVM execution (SOL infrastructure).
      OOS Sh=24.45 >> 1.0. MaxDD OOS=-0.216% very contained. G4 12/12 ALL POSITIVE.
      WIF = 15th vertex. MR9 L002: all future WIF-X pairs blocked.
      G5w PEPE-SOL=0.382 → reduced sleeve 2.0% (0.018 margin below 0.40 threshold).

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

    if regime == "BULL_WIF":
        # WIF FR > SOL FR: Solana meme season
        long_asset  = "WIF"
        short_asset = "SOL"
        state       = STATE_LONG_WIF_SHORT_SOL
    else:  # BEAR_WIF
        # SOL FR > WIF FR: SVM season
        long_asset  = "SOL"
        short_asset = "WIF"
        state       = STATE_LONG_SOL_SHORT_WIF

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
    Compute equal notional for both legs of the WIF-SOL paired trade.

    K759 HL config (WIF-PERP + SOL-PERP on HL, paper-gate strict):
      sleeve_capital   = aum x sleeve_pct      (e.g. $10M x 2.0% = $200K)
      total_notional   = sleeve_capital x lev   ($200K x 4 = $800K)
      notional_per_leg = total_notional / 2     ($400K per leg)

    At $10M / 2.0% sleeve / 4x (paper-gate):
      WIF leg: $100K capital x 4x = $400K notional (HL WIF-PERP)
      SOL leg: $100K capital x 4x = $400K notional (HL SOL-PERP)
      Total:   $800K notional (two legs combined)
      Margin:  $200K (2.0% of AUM)
      HL conc: PAPER-ONLY (66.8% AT CAP — no live capital added)
      Net profit: central $54K/yr @$10M @4x (K523: $20.7K-$76.8K)
      WIF vertex: 15th — MR9 L002 blocks all future WIF-X pairs
      G5w reduction: 2.0% (vs 2.5% standard) due to PEPE-SOL proximity=0.382

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
    Submit K759 WIF-SOL paired trade: POST_ONLY both legs in parallel.

    Protocol (K759 HL primary — both legs on HL):
      1. Submit WIF leg on HL POST_ONLY
      2. Submit SOL leg on HL POST_ONLY
      3. Both legs submitted in parallel (K439 pattern)
      4. IOC fallback per leg if POST_ONLY times out
      5. If both fail: retry next 8h cycle

    Args:
      long_leg:  {"symbol": "WIF", "notional": 400000, "venue": "HL"}
      short_leg: {"symbol": "SOL", "notional": 400000, "venue": "HL"}
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
        print(f"  [K759] {mode_tag}: LONG {long_sym}@{long_venue} ${long_notl:,.0f}  "
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
            "venue_config":     "HL_PRIMARY_WIF_SOL_ALT_ALT",
            "mechanism_note":   (
                "WIF-SOL direct alt-alt differential (K759 SEVENTEENTH ALT-ALT, 72nd daemon): "
                "WIF FR = Solana meme rotation premium (dogwifhat SOL-native SPL, launched Jan 2024, "
                "CEX listings Coinbase Apr 2024/Binance, BONK/WIF/POPCAT rotation cycles, meme FOMO, "
                "SVM DEX liquidity Raydium/Jupiter, vol_ratio=1.347x SOL, P99=1.416bps Max=3.164bps "
                "Q2 2024 peak: WIF +0.34bps vs SOL +0.22bps mean diff +0.13bps); "
                "SOL FR = Solana SVM DePIN/DeFi premium (Phantom adoption, Firedancer upgrade, "
                "SOL ETF speculation, SVM DeFi TVL Jupiter/Drift/Jito, +8.82%/ann persistent, "
                "SOL liquidation cascade Min=-20.51bps Feb 2025). "
                "G4 WF 12/12 ALL POSITIVE (min_sh=9.895). G5 all PASS (max_corr=0.3819 G5w PEPE-SOL). "
                "G5w PEPE-SOL=0.382 proximity (0.018 margin) → 2.0% sleeve (reduced). "
                "L011 raw_corr(WIF,SOL)=0.487 PASS (< 0.50 SOL-ecosystem threshold, borderline). "
                "HL at 66.8% AT CAP — paper-gate strict until K498/v6.52 reduces HL%. "
                "WIF = 15th vertex. MR9 L002: all future WIF-X pairs blocked. "
                "OOS Sh=24.45 (W=168h, zero threshold). K523 central $54K/yr @$10M @4x @2.0%. "
                "60d gate: Realized Sh>=6 + fill>=60% + maxDD<15%."
            ),
            "ts_utc":           ts,
        }
        _append_trade_log(result)
        return result

    # LIVE scaffold (not reached in PAPER_TRADE mode):
    print(f"  [K759] SCAFFOLD LIVE: parallel POST_ONLY "
          f"LONG {long_sym}@{long_venue} ${long_notl:,.0f} "
          f"+ SHORT {short_sym}@{short_venue} ${short_notl:,.0f}")
    long_order_id  = f"SCAFFOLD_LONG_{long_sym}_{int(time.time())}"
    short_order_id = f"SCAFFOLD_SHORT_{short_sym}_{int(time.time())}"

    print(f"  [K759] Neither leg filled within timeout — retry next 8h cycle")
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
    Check if current K759 position has drifted beyond DRIFT_REBALANCE_PCT (5%).

    K759 HL: both legs on HL (WIF-PERP + SOL-PERP).
    Drift detection: compare stored WIF leg notional vs SOL leg notional.
    Threshold: 5% (same as K679/K682/K684/K686/K690/K747/K739/K754 pattern).

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
    Both legs on HL (K759 HL primary — WIF-PERP + SOL-PERP).

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

    if state == STATE_LONG_WIF_SHORT_SOL:
        long_sym,  short_sym  = "WIF", "SOL"
    else:  # LONG_SOL_SHORT_WIF
        long_sym,  short_sym  = "SOL", "WIF"

    long_notional  = float(dash.get("long_notional",  0.0))
    short_notional = float(dash.get("short_notional", 0.0))

    if dry_run or PAPER_TRADE:
        mode_tag = "DRY_RUN" if dry_run else "PAPER_TRADE"
        print(f"  [K759] {mode_tag} CLOSE:")
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
        print(f"  [K759] SCAFFOLD CLOSE:")
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
    """Load k759_dashboard.json; return defaults if missing."""
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
    """Write k759_dashboard.json with full signal + regime state."""
    dash = _load_dashboard()

    # Update signal data
    dash["last_poll_jst"]        = signal.get("ts_jst", "—")
    dash["fr_wif_current"]       = signal.get("fr_wif",          0.0)
    dash["fr_sol_current"]       = signal.get("fr_sol",           0.0)
    dash["wif_sol_diff_current"] = signal.get("wif_sol_diff",    0.0)
    dash["mean_168h"]            = signal.get("mean_168h",        0.0)
    dash["diff_sigma"]           = signal.get("diff_sigma",       0.0)
    dash["regime"]               = signal.get("regime",    "NEUTRAL")
    dash["signal_direction"]     = signal.get("signal_direction", 0)
    dash["history_points"]       = signal.get("history_points",   0)

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
    dash["hl_concentration_pct"]     = HL_CONCENTRATION_POST_K759

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
        "activation_trigger":      "60d paper-trade: Sh>=6 AND fill>=60% AND maxDD<15%",
        "profit_at_activation_2_0pct": (
            "central $54,245/yr net @$10M @4x (K523: $20.7K cons / $54.2K central / $76.8K opt)"
        ),
        "alt_alt_note": (
            "SEVENTEENTH ALT-ALT pair (WIF-SOL, no BTC/ETH leg). Standalone. 72nd daemon. "
            "CONDITIONAL_ACCEPT (HL 66.8% AT CAP — paper-gate strict until K498/v6.52). "
            "G4 WF 12/12 ALL POSITIVE (min_sh=9.895). G5 all PASS (max_corr=0.3819 G5w PEPE-SOL). "
            "G5w proximity=0.382 (0.018 margin) → reduced sleeve 2.0% (vs 2.5% standard). "
            "WIF = 15th vertex (SOL meme cluster). MR9 L002: all future WIF-X pairs blocked. "
            "W=168h (G6-safe: 31.2/yr vs 30/yr min). OOS Sh=24.45 MaxDD=-0.216% (very contained)."
        ),
        "hl_cap_warning": (
            "HL concentration 66.8% AT CAP (K751 audit). Paper-gate strict. "
            "Deploy LIVE only after K498/v6.52 reduces HL% below 65%. "
            "K759 HL primary: both WIF-PERP + SOL-PERP on HL. "
            "2.0% all-HL would add 2.0% → over cap. Paper-only until HL% resolved. "
            "L011 borderline: raw_corr(WIF,SOL)=0.487 — monthly recheck required."
        ),
        "g5w_cross_sleeve_note": (
            "G5w PEPE-SOL=0.382 (0.018 margin below 0.40). "
            "WIF-SOL (2.0%) + PEPE-SOL (2.0%) combined = 4.0% meme-vs-SOL cluster. "
            "Monitor cross-sleeve concentration: if G5w OOS drifts toward 0.40, "
            "consider reducing WIF-SOL sleeve to 1.5%."
        ),
    }

    # Strategy metadata
    dash["paper_trade_mode"]    = PAPER_TRADE
    dash["wave"]                = "K761"
    dash["strategy"]            = "K759 WIF-SOL FR Differential (SEVENTEENTH ALT-ALT, W=168h, HL primary)"
    dash["execution_mode"]      = "POST_ONLY_PARALLEL"
    dash["venue_config"]        = "HL_PRIMARY_BYBIT_FALLBACK"
    dash["alt_alt_mechanism"]   = {
        "formula":            "diff = WIF_FR - SOL_FR  (direct alt-alt, no base asset)",
        "rolling_window":     "W=168h (21 x 8h periods, G6-safe: 31.2 entries/yr OOS)",
        "signal":             "sign(rolling_mean_168h(diff))",
        "seventeenth_alt_alt": True,
        "g4_result":          "12/12 ALL POSITIVE (min_sh=9.895) — strong WF validation",
        "hl_reason":          HL_ONLY_REASON,
        "hl_concentration":   66.8,
        "cross_cluster_note": (
            "WIF (dogwifhat SOL-native SPL meme coin, launched Jan 2024, "
            "CEX listings Coinbase Apr 2024/Binance, BONK/WIF/POPCAT rotation cycles, "
            "meme FOMO, SVM DEX liquidity Raydium/Jupiter, vol_ratio=1.347x SOL, "
            "P99=1.416bps Max=3.164bps/hr peak, Q2 2024: WIF+0.34 vs SOL+0.22bps +0.13bps diff) "
            "vs SOL (Solana SVM retail/DeFi — Phantom adoption, Firedancer, SOL ETF, "
            "SVM DeFi TVL Jupiter/Drift/Jito — persistently positive +8.82%/ann, "
            "SOL liquidation cascade Min=-20.51bps Feb 2025). "
            "OOS FR corr=0.054 (near-zero in OOS despite full-period=0.487). "
            "OOS Sh=24.45. MaxDD OOS=-0.216% (very contained). G5 all PASS."
        ),
        "wif_vertex_rule": (
            "WIF = 15th vertex added to V. "
            "V = {APT, ATOM, AVAX, BNB, ENA, FIL, HBAR, INJ, LDO, SEI, SOL, TIA, TAO, PEPE, WIF}. "
            "MR9 L002: all future WIF-X pairs auto-blocked. "
            "WIF-SOL is the only permissible WIF-X pair given V at K759."
        ),
        "g5_max_corr": "0.3819 (G5w PEPE-SOL) — 0.018 margin below 0.40 threshold. All PASS.",
        "g5w_reduced_sleeve": (
            "G5w PEPE-SOL=0.382 (0.018 margin) triggers reduced sleeve: 2.0% (vs 2.5% standard). "
            "WIF-SOL and PEPE-SOL share SOL leg — both meme-vs-SOL signals. "
            "Combined: WIF-SOL 2.0% + PEPE-SOL 2.0% = 4.0% meme-vs-SOL cluster sleeve. "
            "If G5w OOS approaches 0.40 in live monitoring, reduce WIF-SOL sleeve to 1.5%."
        ),
        "w168h_g6_note": (
            "W=168h family standard window (21 x 8h periods). G6: 31.2 entries/yr OOS (PASS >30/yr). "
            "W=84h: 59/yr OOS Sh=26.51 (marginally higher but departs from family standard). "
            "W=48h: 85/yr OOS Sh=28.07 (best config but may overfit meme spike timing). "
            "W=168h chosen for family consistency and G6 compliance. OOS Sh=24.45."
        ),
        "l011_sol_ecosystem": (
            "L011 (new rule K759): SOL-ecosystem tokens must have raw_corr(candidate_fr, SOL_fr) < 0.50. "
            "WIF at 0.487 full-period, OOS=0.054 (near-zero — regime-switch cleans signal). "
            "Borderline PASS. Monthly recheck: if OOS live corr drifts toward 0.50, reduce sleeve. "
            "SOL-native meme: WIF min=-18.98bps mirrors SOL min=-20.51bps cascade pattern."
        ),
        "wif_fr_drivers": (
            "dogwifhat (SOL-native SPL meme coin, launched Jan 2024, top-3 Solana meme by MC). "
            "FR driven by Solana meme season timing (BONK/WIF/POPCAT rotation cycles). "
            "WIF CEX listings (Coinbase Apr 2024, Binance), meme coin retail FOMO. "
            "SVM on-chain DEX liquidity (Raydium/Jupiter WIF pairs). Social media virality. "
            "Amplifies SOL FR by ~1.3x during bull peaks (vol_ratio=1.347x). "
            "P99=1.416bps, Max=3.164bps/hr. Q2 2024 peak: WIF +0.34bps vs SOL +0.22bps."
        ),
        "sol_fr_drivers": (
            "Solana SVM DePIN/Retail adoption premium. "
            "Meme-coin seasons (BONK/WIF/POPCAT). Firedancer upgrade hype. "
            "SOL ETF speculation. SVM DeFi TVL (Jupiter/Drift/Jito). "
            "+8.82%/ann persistently positive. Extreme negative: -20.51bps (Feb 2025 cascade)."
        ),
        "g8_note": (
            "G8 PASS: HL+Bybit+OKX confirmed (3-venue presence). "
            "HL: WIF-PERP (WIFUSDC primary). Bybit: WIFUSDT-PERP. OKX: WIF-PERP confirmed. "
            "Cross-venue presence CONFIRMED on all 3 major venues."
        ),
        "k523_projection": {
            "conservative_yr": 20655,
            "central_yr":      54245,
            "optimistic_yr":   76847,
            "sleeve_pct":      0.020,
            "note":            "K523 mandatory 3-point. Conservative=R2S×0.38 (K518 floor). Central=$54.2K @$10M @4x @2.0%.",
        },
    }

    dash["activation_criteria"] = {
        "60d_paper_trade_gate": "required",
        "realized_sharpe_min": 6.0,
        "fill_rate_min_pct":   60,
        "max_drawdown_max_pct": 15,
        "status":              "SCAFFOLD-READY",
        "activation_sleeve_pct": 0.020,
        "venue":               "HL primary (WIF-PERP + SOL-PERP)",
        "conditional_note": (
            "CONDITIONAL: HL 66.8% AT CAP (K751 audit). "
            "Deploy LIVE only after K498/v6.52 reduces HL% below 65%. "
            "L011 borderline: raw_corr(WIF,SOL)=0.487 — monthly recheck. "
            "G5w proximity: monitor PEPE-SOL cross-sleeve concentration."
        ),
        "live_trigger": "K498/v6.52 OKX activation (HL% drops from 66.8%) + 60d gate passage",
    }

    dash["oos_performance"] = {
        "sharpe":              24.4547,
        "oos_ann_ret_pct":     12.0544,
        "oos_ann_ret_4x_pct":  48.22,
        "k523_conservative_yr": 20655,
        "k523_central_yr":     54245,
        "k523_optimistic_yr":  76847,
        "daily_usdc_central":  149,
        "wave_accept": (
            "K759 CONDITIONAL_ACCEPT (K761 scaffold) — SEVENTEENTH ALT-ALT, "
            "SOL meme cluster × SVM, G4 12/12, G5 all PASS"
        ),
        "cluster":    "WIF-SOL Alt-Alt FR Differential (Solana meme × SVM, HL primary, 15th vertex)",
        "daemon_number": "72nd",
        "section6_result": (
            "CONDITIONAL_ACCEPT G5 all PASS. G1-G9 PASS. "
            "OOS Sh=24.45 (W=168h zero threshold ~210d OOS). MaxDD=-0.216%. "
            "HL 66.8% AT CAP → paper-gate strict. G5w PEPE-SOL=0.382 → 2.0% sleeve."
        ),
        "family_rank": {
            "k759_oos_sharpe":   24.4547,
            "k759_pair":         "WIF-SOL (alt-alt, SEVENTEENTH, 15th vertex WIF SOL meme cluster)",
            "alt_alt_accepted":  17,
            "g4_note":           "K759 G4=12/12 ALL POSITIVE (min_sh=9.895).",
            "vertex_note":       "WIF = 15th vertex. V={APT,ATOM,AVAX,BNB,ENA,FIL,HBAR,INJ,LDO,SEI,SOL,TIA,TAO,PEPE,WIF}.",
        },
    }

    DASHBOARD_PATH.write_text(json.dumps(dash, indent=2))
    return dash


# ─────────────────────────────────────────────────────────────────────────────
# Main entry point
# ─────────────────────────────────────────────────────────────────────────────

def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="K759 WIF-SOL FR Differential Strategy (SEVENTEENTH ALT-ALT, 72nd daemon)"
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

    print(f"\n=== K759 WIF-SOL FR Differential Strategy — {ts_jst} ===")
    print(f"  Strategy:    WIF-SOL FR Differential (SEVENTEENTH ALT-ALT pair)")
    print(f"  Wave:        K761 (scaffold wave for K759 CONDITIONAL_ACCEPT)")
    print(f"  Daemon:      72nd (seventeenth alt-alt pair, 15th vertex WIF)")
    print(f"  OOS Sharpe:  24.4547 (W=168h, zero threshold, ~210d OOS)")
    print(f"  G4 WF:       12/12 ALL POSITIVE (min_sh=9.895)")
    print(f"  G5:          all PASS (max_corr=0.3819 G5w PEPE-SOL — 0.018 margin)")
    print(f"  G5w note:    PEPE-SOL proximity=0.382 → reduced sleeve 2.0% (vs 2.5%)")
    print(f"  W=168h:      G6 compliance (31.2/yr OOS vs 30/yr min)")
    print(f"  WIF vertex:  15th. MR9 L002: all future WIF-X pairs blocked.")
    print(f"  L011:        raw_corr(WIF,SOL)=0.487 PASS (borderline, monthly recheck)")
    print(f"  HL cap:      66.8% AT CAP (K751 audit) — paper-gate strict")
    print(f"  Profit:      central $54K/yr @$10M @4x @2.0% sleeve (K523 3-point)")
    print(f"  Paper mode:  {PAPER_TRADE}")

    # --status mode
    if args.status:
        dash = _load_dashboard()
        print(f"\n  [Status] {dash.get('strategy', 'K759 WIF-SOL')}")
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
    print(f"\n  [Phase 1] Fetching WIF + SOL funding rates from HL ...")
    signal = compute_signal()
    print(f"  fr_wif={signal['fr_wif']:.6e}  fr_sol={signal['fr_sol']:.6e}")
    print(f"  wif_sol_diff={signal['wif_sol_diff']:.6e}")
    print(f"  mean_168h={signal['mean_168h']:.6e}  sigma={signal['diff_sigma']:.6e}")
    print(f"  regime={signal['regime']}  direction={signal['signal_direction']}")
    print(f"  history_points={signal['history_points']}")

    print(f"\n  [Phase 2] Computing signal (W=168h rolling mean of WIF_FR - SOL_FR) ...")
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

    print(f"\n=== K759 WIF-SOL run complete — {datetime.now(JST).strftime('%Y-%m-%d %H:%M JST')} ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
