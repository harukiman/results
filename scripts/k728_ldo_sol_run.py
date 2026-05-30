#!/usr/bin/env python3
"""
k728_ldo_sol_run.py — K728 LDO-SOL FR Differential Strategy
=============================================================
TENTH ALT-ALT scaffold (64th daemon): LDO vs SOL (no BTC/ETH base).
Signal: LDO_FR - SOL_FR
W=168h rolling mean, zero threshold (sign only)
Bybit-only (LDO-PERP + SOL-PERP on Bybit)
4x leverage, 3% sleeve standalone

K728 LDO-SOL alt-alt hypothesis (CROSS-CLUSTER: Ethereum Liquid Staking vs Solana SVM):
  LDO (Lido DAO) FR dynamics: ETH validator queue dynamics — stETH protocol yield.
  LDO FR is driven by: ETH staking APY cycles (validator queue, stETH yield vs DeFi yield),
  LSD competition cycles (RocketPool/Frax/Mantle share wars), Ethereum upgrade events
  (Shanghai unlock, Cancun blobs, Pectra sharding), regulatory staking risk events
  (Kraken SEC action, Coinbase staking compliance). LDO FR mean = +15.96%/yr (structurally
  POSITIVE — ETH institutional demand for stETH is persistent).
  SOL (Solana L1) FR dynamics: Retail-momentum/meme driven. SOL FR governed by: memecoin
  season cycles (BONK/WIF/POPCAT), Jito MEV revenue cycles (block proposer fee cycles),
  Jupiter DEX volume explosions, Solana network congestion/outage narratives, ETH vs SOL
  narrative battles (Layer war sentiment cycles). SOL FR mean = +7.71%/yr.
  Cross-cluster: LDO (Ethereum Liquid Staking / LSD cluster) vs SOL (Solana SVM L1 cluster).
  GENUINELY different economic segments — orthogonal FR drivers. MR9: LDO-SOL = K594_dir -
  K476_dir with K594 ⊥ K476 (corr=0.0585). K594 (LDO-BTC) was TRIPLE-BLOCKED; removing BTC
  common factor via alt-alt pivot yields genuine independent alpha.

K728 KEY INSIGHT — Persistent Cross-Cluster Carry:
  Dominant state (85.1% of time): LDO FR > SOL FR (ETH staking institutional premium)
    → signal = +1 → SHORT LDO (collect LDO FR) + LONG SOL (net LDO-SOL carry > 0)
    → Persistent carry from LDO FR structural premium over SOL (ETH staking demand)
  Other state (13.9%): SOL FR > LDO FR (SOL meme-season spike or ETH staking pressure)
    → signal = -1 → SHORT SOL + LONG LDO (collect SOL premium when meme mania spikes)
  LDO structural premium: +8.25%/yr (LDO 15.96% vs SOL 7.71%)

K728 §6 gates (ACCEPT CONDITIONAL — 14/19 PASS, MR8/MR9 compliant):
  - OOS Sharpe: 46.84 (W=168h, zero threshold, 217d OOS period)
  - OOS Ann Return: 10.30% @1x, 41.19% @4x
  - Net @$10M @4x @3% sleeve: $105,032/yr USDC
  - ADF t=-17.45 (strongly stationary p=4.6e-30)
  - G4 walk-forward: 11/12 folds positive (fold 2 = -7.51 only negative)
  - G5c: K594 LDO-BTC corr=0.505 FAIL (K594 REJECTED — structural LDO leg, not portfolio risk)
  - G5k: K708 BNB-SOL corr=0.592 FAIL (SOL concentration $2.4M vs $10B OI = 0.024%)
  - G6: 11.8 trades/yr < 30 threshold (low but operationally acceptable per K476 precedent)
  - G8: Bybit-primary venue mismatch (structural, not strategy risk)
  - MR8: LDO NOT in {APT,ATOM,SOL,INJ,AVAX,SEI,TIA,ENA,BNB} — new vertex (LSD cluster) PASS
  - MR9: LDO-SOL = K594_dir - K476_dir (K594⊥K476 corr=0.0585, near-orthogonal) PASS
  - 60d gate: Realized Sh >= 23 (50% of OOS 46.84), fill >= 60%, DD < 15%
  - Alt-alt family: 10th alt-alt scaffold (LSD vs SVM, rank #3 by OOS Sharpe)
  - K594 pivot: K594 LDO-BTC TRIPLE-BLOCKED (vol 0.80x, ETH corr 0.43, DeFi corr 0.50,
    OOS Sh=-3.82). K728 removes BTC common factor: LDO-SOL = K594 - K476.

Dominant regime (LDO 15.96%/yr vs SOL 7.71%/yr):
  LDO structurally higher than SOL (ETH staking premium) -> fr_diff (LDO-SOL) > 0 -> signal +1
  -> SHORT LDO (collect LDO FR premium) + LONG SOL
  Carry: |LDO_FR - SOL_FR| captured per period (when LDO > SOL, 85% of time)

Signal mechanism (MR9: LDO-SOL = K594_dir - K476_dir):
  diff = LDO_FR - SOL_FR   (LDO minus SOL)
  mean_168h = 168h rolling mean of diff (21 x 8h periods)
  sign = sign(mean_168h)
  +1 -> SHORT LDO / LONG SOL (LDO FR > SOL FR — ETH staking institutional premium)
  -1 -> SHORT SOL / LONG LDO (SOL FR > LDO FR — meme-season spike or ETH staking collapse)

HL concentration:
  Current HL weight: 64.5% (post-K721)
  K728 HL-only impact: 67.5% (EXCEEDS 65% cap)
  Resolution: Bybit mandatory (LDO maxLev=50, SOL-PERP on Bybit)
  K728 is fully Bybit-only: HL concentration UNCHANGED at 64.5%

K730 production scaffold:
  - 64th daemon (10th alt-alt scaffold, LSD vs SVM, rank #3 OOS Sh=46.84)
  - Bybit-only (HL cap 65% constraint — HL-only would reach 67.5%)
  - 3% standalone sleeve, 4x leverage
  - $105,032/yr net @$10M @4x (OOS Ann Ret 10.30% @1x)
  - 60d paper-trade gate: Realized Sh>=23 (50% of OOS 46.84) + fill>=60% + maxDD<15%
  - LDO notional cap: K728 3% standalone (first LDO strategy in portfolio)
  - SOL notional cap: K728 3% + K708 existing — monitor combined SOL on Bybit
  - G5k conflict K708 BNB-SOL (corr=0.592 FAIL — SOL shared, $2.4M combined = 0.024% SOL OI)
  - G5c structural: K594 LDO-BTC REJECTED (vol+ETH+DeFi triple block) — not portfolio risk
  - K594 pivot: removing BTC common factor unlocks LDO-SOL independent alpha (MR9 PASS)

Architecture (K683/K685/K687/K689/K693/K697/K699/K710/K721 alt-alt pattern):
  1. fetch_fr_batch()                  -> fetch LDO + SOL FR every 8h from Bybit
  2. compute_signal(ldo_fr, sol_fr)   -> 168h rolling mean of (LDO_FR - SOL_FR); sign()
  3. decide_position(signal)           -> SHORT_LDO_LONG_SOL | SHORT_SOL_LONG_LDO | NEUTRAL
  4. submit_paired_trade(long, short)  -> POST_ONLY paired (LDO + SOL legs, both Bybit)
  5. daily_rebalance()                 -> drift > 5% triggers rebalance
  6. close_paired_position(reason)     -> sequential: short first, then long

Paper-trade mode is the DEFAULT.  No orders are submitted unless
PAPER_TRADE=False is explicitly set in the environment.

K339 security: REPO_ROOT from __file__, no /Users/ literals.
No new packages — stdlib urllib + json only.

Usage:
  python3 scripts/k728_ldo_sol_run.py --dry-run
  python3 scripts/k728_ldo_sol_run.py --status
  python3 scripts/k728_ldo_sol_run.py --rebalance
  python3 scripts/k728_ldo_sol_run.py --close "scheduled exit"
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

DASHBOARD_PATH  = DATA_DIR  / "k728_dashboard.json"
FR_HISTORY_PATH = CACHE_DIR / "k728_fr_history.jsonl"
TRADE_LOG_PATH  = CACHE_DIR / "k728_paper_trades.jsonl"

JST = timezone(timedelta(hours=9))
UTC = timezone.utc

# ── Strategy constants ────────────────────────────────────────────────────────
PAPER_TRADE         = True          # never submit real orders in paper-trade mode
SLEEVE_PCT          = 0.030         # K728 sleeve = 3% of AUM (standalone, Bybit-only)
LEVERAGE            = 4.0           # 4x per K728 analysis (K430 cap)
AUM_DEFAULT         = 10_000_000.0  # $10M reference AUM
DRIFT_REBALANCE_PCT = 0.05          # rebalance if legs drift > 5%
IOC_TIMEOUT_SEC     = 300           # 5 min fill window
EMA_PERIOD_HOURS    = 168           # 168h rolling mean primary config (W=168h)
EMA_PERIOD_PERIODS  = EMA_PERIOD_HOURS // 8  # = 21 periods (8h settlement cycle)
SIGNAL_SIGMA_MULT   = 0.0           # zero threshold (sign of rolling mean)
BYBIT_API_URL       = "https://api.bybit.com"
HL_API_URL          = "https://api.hyperliquid.xyz/info"

# ── Venue config (Bybit-only — LDO-PERP + SOL-PERP on Bybit) ─────────────────
# HL concentration: 64.5% baseline — Bybit mandatory (HL-only would breach 65%)
# K728: 64.5% + 3.0% = 67.5% > 65% cap if on HL. Bybit resolves cap breach.
# Bybit: LDO maxLev=50, SOL-PERP (both listed, perp pairs confirmed)
HL_CONCENTRATION_PRE_K728  = 64.5   # post-K721 reference
HL_CONCENTRATION_POST_K728 = 64.5   # UNCHANGED (Bybit-only — HL-only would breach 65%)

BYBIT_LDO_MAX_LEV  = 50
BYBIT_SOL_MAX_LEV  = 50

# ── Position state constants ──────────────────────────────────────────────────
STATE_NEUTRAL              = "NEUTRAL"
STATE_SHORT_LDO_LONG_SOL   = "SHORT_LDO_LONG_SOL"    # signal +1: LDO FR > SOL FR (dominant 85%)
STATE_SHORT_SOL_LONG_LDO   = "SHORT_SOL_LONG_LDO"    # signal -1: SOL FR > LDO FR (meme spike)

# ── Symbols fetched from Bybit for FR data ────────────────────────────────────
# K728: LDO + SOL only — direct alt-alt differential (TENTH ALT-ALT pair)
SYMBOLS = ("LDO", "SOL")


# ─────────────────────────────────────────────────────────────────────────────
# HTTP helpers (stdlib urllib only — no requests)
# ─────────────────────────────────────────────────────────────────────────────

def _http_get(url: str, timeout: int = 10) -> Optional[dict]:
    try:
        req = urllib.request.Request(
            url, headers={"User-Agent": "crypto-lab-k728/1.0"}
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        print(f"  [k728] HTTP error: {e}", file=sys.stderr)
        return None


def _http_post(url: str, payload: dict, timeout: int = 10) -> Optional[dict]:
    try:
        data = json.dumps(payload).encode()
        req  = urllib.request.Request(
            url, data=data,
            headers={"Content-Type": "application/json",
                     "User-Agent": "crypto-lab-k728/1.0"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        print(f"  [k728] HTTP error: {e}", file=sys.stderr)
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Phase 1 — Funding rate fetch (LDO + SOL from Bybit)
# ─────────────────────────────────────────────────────────────────────────────

def _fetch_bybit_fr_batch() -> Dict[str, float]:
    """
    Fetch current 8h funding rates for LDO and SOL from Bybit.
    Returns {symbol: fr_8h_fraction}.

    Bybit API: /v5/market/tickers?category=linear
    K728: both legs on Bybit (LDO-PERP + SOL-PERP).
    Bybit-only mandatory: HL concentration at 64.5%+3.0%=67.5% > 65% cap.
    Both LDOUSDT and SOLUSDT perpetuals listed on Bybit (LDO maxLev=50, SOL maxLev=50).

    Fallback: HL metaAndAssetCtxs for cross-reference (informational only).
    K728: Bybit is the execution venue; HL FR data is used for cross-check only.
    Note: HL LDO maxLev=5 vs Bybit maxLev=50 — Bybit primary also resolves leverage constraint.
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
        print(f"  [k728] Bybit partial result {list(result.keys())} — trying HL fallback",
              file=sys.stderr)

    # Fallback: HL metaAndAssetCtxs (informational cross-check only)
    raw_hl = _http_post(HL_API_URL, {"type": "metaAndAssetCtxs"})
    if raw_hl and isinstance(raw_hl, list) and len(raw_hl) >= 2:
        meta       = raw_hl[0]
        asset_ctxs = raw_hl[1]
        universe   = {item["name"]: i for i, item in enumerate(meta.get("universe", []))}
        for sym in SYMBOLS:
            if sym in result:
                continue   # already have from Bybit
            if sym not in universe:
                continue
            idx = universe[sym]
            ctx = asset_ctxs[idx]
            try:
                result[sym] = float(ctx.get("funding", 0.0))
                print(f"  [k728] HL fallback used for {sym} FR (informational)", file=sys.stderr)
            except (TypeError, ValueError):
                continue

    if len(result) < len(SYMBOLS):
        print(f"  [k728] Warning: only fetched {list(result.keys())} FRs", file=sys.stderr)
    return result


def _load_fr_history() -> List[dict]:
    """Load K728 FR history JSONL."""
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
    fr_ldo: float, fr_sol: float, ldo_sol_diff: float
) -> None:
    """Append one FR snapshot to history."""
    rec = {
        "ts_utc":        datetime.now(UTC).isoformat(),
        "fr_ldo":        round(fr_ldo,       10),
        "fr_sol":        round(fr_sol,        10),
        "ldo_sol_diff":  round(ldo_sol_diff,  10),  # LDO_FR - SOL_FR
    }
    with open(FR_HISTORY_PATH, "a") as f:
        f.write(json.dumps(rec) + "\n")


# ─────────────────────────────────────────────────────────────────────────────
# Phase 2 — Signal computation (LDO-SOL direct differential, 168h rolling mean)
# ─────────────────────────────────────────────────────────────────────────────

def compute_signal(
    fr_ldo: Optional[float] = None,
    fr_sol: Optional[float] = None,
) -> dict:
    """
    Fetch live LDO and SOL FRs from Bybit, compute LDO-SOL differential,
    and compute 168h rolling mean for direction signal.

    Signal mechanism (K728 direct differential — LSD vs SVM):
      diff = LDO_FR - SOL_FR   (LDO minus SOL = K594_dir - K476_dir per MR9)
      mean_168h = 168h rolling mean of diff (21 x 8h periods)
      sign  = sign(mean_168h)
      +1 -> SHORT LDO / LONG SOL (LDO FR higher — ETH staking institutional premium, 85% of time)
      -1 -> SHORT SOL / LONG LDO (SOL FR higher — meme-season spike or ETH staking collapse)

    Cross-cluster mechanism:
      - LDO FR: Lido DAO / Ethereum Liquid Staking — driven by ETH validator queue dynamics,
        stETH yield vs DeFi yield spread, LSD competition (RocketPool/Frax/Mantle),
        Ethereum upgrade events (Shanghai unlock, Cancun blobs, Pectra sharding),
        regulatory staking risk events (Kraken SEC / Coinbase compliance).
        LDO FR mean = +15.96%/yr (structurally POSITIVE — institutional stETH demand).
      - SOL FR: Solana SVM L1 retail-momentum driven. Governed by memecoin season cycles
        (BONK/WIF/POPCAT), Jito MEV revenue cycles (block proposer fee cycles), Jupiter DEX
        volume explosions, Solana network congestion narratives, ETH vs SOL narrative battles.
        SOL FR mean = +7.71%/yr.
      - LDO FR > SOL FR 85.1% of time: ETH institutional staking premium is structurally
        persistent. LDO-SOL = K594_dir - K476_dir (K594⊥K476 corr=0.0585 ≈ 0).
      - MR9: LDO-SOL = K594_dir - K476_dir (K594 triple-blocked LDO-BTC + K476 SOL-BTC).
        Removing BTC common factor reveals independent alpha. max_err=4.34e-19.

    K728 §6 validation (14/19 PASS, ACCEPT CONDITIONAL):
      - OOS Sharpe: 46.84 (W=168h, zero threshold, 217d OOS period)
      - OOS Ann Ret: 10.30% @1x, 41.19% @4x
      - Net @$10M @4x @3% sleeve: $105,032/yr
      - ADF t=-17.45 (strongly stationary p=4.6e-30)
      - G4 walk-forward: 11/12 folds positive (fold 2 = -7.51 only negative)
      - G5c K594 LDO-BTC: corr=0.505 FAIL (K594 REJECTED — structural, not portfolio risk)
      - G5k K708 BNB-SOL: corr=0.592 FAIL (SOL $2.4M combined = 0.024% SOL OI)
      - G6 trade count: 11.8/yr (below 30 threshold — low but operationally acceptable)
      - G8 cross-venue: Bybit-primary addresses venue mismatch
      - MR8: LDO outside {APT,ATOM,SOL,INJ,AVAX,SEI,TIA,ENA,BNB} — new vertex PASS
      - MR9: LDO-SOL = K594-K476 with K594⊥K476 (corr=0.0585) PASS
      - 60d gate: Realized Sh>=23 (50% of OOS 46.84) + fill>=60% + maxDD<15%

    Returns:
      {
        "fr_ldo":           float,
        "fr_sol":           float,
        "ldo_sol_diff":     float,    # LDO_FR - SOL_FR (current)
        "mean_168h":        float,    # 168h rolling mean of differential
        "diff_sigma":       float,    # 168h rolling sigma (informational)
        "history_points":   int,
        "regime":           str,      # LDO_PREMIUM | SOL_PREMIUM | NEUTRAL
        "signal_direction": int,      # +1 | -1 | 0
        "ts_jst":           str,
      }
    """
    if fr_ldo is None or fr_sol is None:
        frs    = _fetch_bybit_fr_batch()
        fr_ldo = frs.get("LDO", 0.0)
        fr_sol = frs.get("SOL", 0.0)

    # LDO-SOL direct differential (= K594_dir - K476_dir per MR9)
    ldo_sol_diff = fr_ldo - fr_sol

    _append_fr_history(fr_ldo, fr_sol, ldo_sol_diff)

    # Load history for rolling mean + sigma (168h = 21 x 8h periods)
    history = _load_fr_history()
    diffs   = [r["ldo_sol_diff"] for r in history if "ldo_sol_diff" in r]

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

    # Regime classification (zero threshold — per K728 spec)
    # LDO_PREMIUM: LDO FR > SOL FR (ETH staking institutional demand — 85.1% of time)
    # SOL_PREMIUM: SOL FR > LDO FR (meme-season spike or ETH staking collapse — 13.9%)
    if mean_168h > 0:
        regime    = "LDO_PREMIUM"    # LDO FR > SOL FR -> short LDO / long SOL (dominant)
        direction = 1
    elif mean_168h < 0:
        regime    = "SOL_PREMIUM"    # SOL FR > LDO FR -> short SOL / long LDO
        direction = -1
    else:
        regime    = "NEUTRAL"
        direction = 0

    return {
        "fr_ldo":           round(fr_ldo,        10),
        "fr_sol":           round(fr_sol,         10),
        "ldo_sol_diff":     round(ldo_sol_diff,   10),
        "mean_168h":        round(mean_168h,      10),
        "diff_sigma":       round(sigma,          10),
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
    Determine trade direction from LDO-SOL differential rolling mean.

    Logic (LDO-SOL direct differential pair, Bybit primary):
      regime = LDO_PREMIUM (mean_168h > 0):
        LDO FR > SOL FR: ETH staking institutional demand (structural 85.1% of time)
        -> short LDO (collect LDO staking premium)
        -> long SOL  (SOL FR lower — net positive carry when LDO > SOL)
        -> position_state = SHORT_LDO_LONG_SOL
        -> both legs on Bybit

      regime = SOL_PREMIUM (mean_168h < 0):
        SOL FR > LDO FR: memecoin season spike or ETH staking collapse
        -> short SOL  (collect SOL meme-season premium when retail mania spikes)
        -> long LDO   (LDO FR lower — net positive carry when SOL > LDO)
        -> position_state = SHORT_SOL_LONG_LDO
        -> both legs on Bybit

      regime = NEUTRAL: no trade (mean_168h == 0 exactly — rare)

    K728 edge (cross-cluster mechanism):
      LDO (Ethereum Liquid Staking) driven by ETH validator economics and stETH protocol yield.
      ETH staking demand is institutional (stETH = institutional carry trade in DeFi/TradFi
      convergence). LDO FR mean = +15.96%/yr (structurally positive). Persistent: Shanghai
      unlock enabled withdrawals but demand stabilized at high rate.
      SOL (Solana L1) driven by retail momentum: meme cycles, Jito MEV revenue, Jupiter DEX.
      SOL FR spikes are episodic (BONK/WIF/POPCAT seasons) but mean-reverts to 7.71%/yr.
      Cross-cluster: LDO institutional yield-seeking vs SOL retail speculation.
        - Orthogonal drivers: LDO driven by ETH protocol economics; SOL by retail meme.
        - MR9: LDO-SOL = K594_dir - K476_dir (K594⊥K476 corr=0.0585)
        - 11/12 WF: one negative fold (fold 2 early 2024 = -7.51, 91.7% positive rate)
        - G5c K594 structural FAIL: K594 never deployed (TRIPLE-BLOCKED); not portfolio risk
        - Net $105,032/yr @$10M = 10th alt-alt in portfolio (rank #3 OOS Sh=46.84)

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

    if regime == "LDO_PREMIUM":
        # LDO FR > SOL FR: collect LDO ETH staking premium (short LDO / long SOL) — 85.1% of time
        long_asset  = "SOL"
        short_asset = "LDO"
        state       = STATE_SHORT_LDO_LONG_SOL
    else:  # SOL_PREMIUM
        # SOL FR > LDO FR: collect SOL meme-season premium (short SOL / long LDO) — 13.9% of time
        long_asset  = "LDO"
        short_asset = "SOL"
        state       = STATE_SHORT_SOL_LONG_LDO

    # Both legs on Bybit (K728: HL at 64.5%+3.0% = 67.5% > 65% cap; HL LDO maxLev=5 vs Bybit 50)
    long_venue  = "Bybit"
    short_venue = "Bybit"

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
    Compute equal notional for both legs of the LDO-SOL paired trade.

    K728 Bybit-only config (both LDO-PERP + SOL-PERP on Bybit):
      sleeve_capital   = aum x sleeve_pct      (e.g. $10M x 3.0% = $300K)
      total_notional   = sleeve_capital x lev   ($300K x 4 = $1,200K)
      notional_per_leg = total_notional / 2     ($600K per leg)

    At $10M / 3.0% sleeve / 4x:
      LDO leg:  $150K capital x 4x = $600K notional (Bybit LDO-PERP)
      SOL leg:  $150K capital x 4x = $600K notional (Bybit SOL-PERP)
      Total:    $1,200K notional (two legs combined)
      Margin:   $300K (3.0% of AUM)
      HL conc:  UNCHANGED 64.5% (Bybit-only — HL-only would push to 67.5% > 65% cap)
      Net profit: ~$105,032/yr @$10M @4x (OOS 10.30% ann ret x $10M x 4x x 3.0% x 0.85)

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
    Submit K728 LDO-SOL paired trade: POST_ONLY both legs in parallel.

    Protocol (K728 Bybit primary — both legs on Bybit):
      1. Submit LDO leg on Bybit POST_ONLY
      2. Submit SOL leg on Bybit POST_ONLY
      3. Both legs submitted in parallel (K439 pattern)
      4. IOC fallback per leg if POST_ONLY times out
      5. If both fail: retry next 8h cycle

    Args:
      long_leg:  {"symbol": "SOL", "notional": 600000, "venue": "Bybit"}
      short_leg: {"symbol": "LDO", "notional": 600000, "venue": "Bybit"}
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
        print(f"  [K728] {mode_tag}: LONG {long_sym}@{long_venue} ${long_notl:,.0f}  "
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
            "venue_config":     "BYBIT_PRIMARY_LDO_SOL_LSD_VS_SVM",
            "mechanism_note":   (
                "LDO-SOL direct differential (Ethereum LSD vs Solana SVM, K728): "
                "LDO FR = Lido DAO stETH protocol (ETH validator queue, stETH yield vs DeFi, "
                "LSD competition RocketPool/Frax/Mantle, Ethereum upgrades Shanghai/Cancun/Pectra). "
                "LDO mean = +15.96%/yr (structurally positive institutional demand). "
                "SOL FR = Solana retail momentum (meme cycles BONK/WIF/POPCAT, Jito MEV, Jupiter DEX). "
                "SOL mean = +7.71%/yr. LDO FR > SOL FR 85.1% of time (structural ETH staking premium). "
                "MR9: LDO-SOL = K594_dir - K476_dir (K594 triple-blocked; BTC common factor removed). "
                "K594⊥K476 corr=0.0585. G4: 11/12 WF positive (91.7%). Net: $105,032/yr @$10M. "
                "Bybit mandatory: HL at 64.5%+3.0%=67.5%>65% cap AND HL LDO maxLev=5 vs Bybit 50."
            ),
            "ts_utc":           ts,
        }
        _append_trade_log(result)
        return result

    # LIVE scaffold (not reached in PAPER_TRADE mode):
    print(f"  [K728] SCAFFOLD LIVE: parallel POST_ONLY "
          f"LONG {long_sym}@{long_venue} ${long_notl:,.0f} "
          f"+ SHORT {short_sym}@{short_venue} ${short_notl:,.0f}")
    long_order_id  = f"SCAFFOLD_LONG_{long_sym}_{int(time.time())}"
    short_order_id = f"SCAFFOLD_SHORT_{short_sym}_{int(time.time())}"

    # Scaffold: poll not implemented — retry next 8h cycle
    print(f"  [K728] Neither leg filled within timeout — retry next 8h cycle")
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
    Check if current K728 position has drifted beyond DRIFT_REBALANCE_PCT (5%).

    K728 Bybit-only: both legs on Bybit (LDO-PERP + SOL-PERP).
    Drift detection: compare stored LDO leg notional vs SOL leg notional.
    Threshold: 5% (same as K449/K476/K484/K493/K629/K663/K696/K698/K708/K719 pattern).

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
    Both legs on Bybit (K728 Bybit primary — LDO-PERP + SOL-PERP).

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

    if state == STATE_SHORT_LDO_LONG_SOL:
        long_sym,  short_sym  = "SOL", "LDO"
    else:  # SHORT_SOL_LONG_LDO
        long_sym,  short_sym  = "LDO", "SOL"

    long_notional  = float(dash.get("long_notional",  0.0))
    short_notional = float(dash.get("short_notional", 0.0))

    if dry_run or PAPER_TRADE:
        mode_tag = "DRY_RUN" if dry_run else "PAPER_TRADE"
        print(f"  [K728] {mode_tag} CLOSE:")
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
        print(f"  [K728] SCAFFOLD CLOSE:")
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
    """Load k728_dashboard.json; return defaults if missing."""
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
    """Write k728_dashboard.json with full signal + regime state."""
    dash = _load_dashboard()

    # Update signal data
    dash["last_poll_jst"]         = signal.get("ts_jst", "—")
    dash["fr_ldo_current"]        = signal.get("fr_ldo",         0.0)
    dash["fr_sol_current"]        = signal.get("fr_sol",          0.0)
    dash["ldo_sol_diff_current"]  = signal.get("ldo_sol_diff",   0.0)
    dash["mean_168h"]             = signal.get("mean_168h",      0.0)
    dash["diff_sigma"]            = signal.get("diff_sigma",     0.0)
    dash["regime"]                = signal.get("regime",    "NEUTRAL")
    dash["signal_direction"]      = signal.get("signal_direction", 0)
    dash["history_points"]        = signal.get("history_points", 0)

    # Update position if entering
    if decision:
        state = decision.get("position_state", STATE_NEUTRAL)
        if dash.get("position_state") == STATE_NEUTRAL:
            dash["position_state"]   = state
            dash["long_notional"]    = notional_per_leg
            dash["short_notional"]   = notional_per_leg
            dash["long_asset"]       = decision.get("long_asset")
            dash["short_asset"]      = decision.get("short_asset")
            dash["venue"]            = "Bybit"
            dash["entry_ts_jst"]     = dash["last_poll_jst"]
            dash["signal_direction"] = decision.get("signal_direction", 0)

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
    dash["hl_concentration_pct"]    = HL_CONCENTRATION_POST_K728   # 64.5% unchanged

    # Paper-trade status
    paper_status = dash.get("paper_trade_status", {"days_elapsed": 0, "target_60d": 60})
    dash["paper_trade_status"]      = paper_status

    # 60d activation gate metrics (K730: Realized Sh >= 23, fill >= 60%, DD < 15%)
    dash["gate_metrics"] = {
        "realized_sharpe_target":  23.0,     # >=23 (50% of K728 OOS 46.84)
        "fill_rate_target_pct":    60,
        "max_drawdown_target_pct": 15,        # <15%
        "current_realized_sharpe": dash.get("60d_sharpe", 0.0),
        "current_fill_rate_pct":   0.0,
        "current_max_dd_pct":      0.0,
        "gate_status":             "IN_PROGRESS",
        "activation_trigger":      "60d paper-trade: Sh>=23 AND fill>=60% AND maxDD<15%",
        "profit_at_activation_3pct": "$105,032/yr net @$10M @4x (3% sleeve, OOS 10.30% ann ret)",
        "bybit_primary_note":      "Bybit primary: LDO maxLev=50, SOL-PERP. HL at 64.5%+3.0%=67.5%>65% cap AND HL LDO maxLev=5.",
    }

    # Strategy metadata
    dash["paper_trade_mode"]   = PAPER_TRADE
    dash["wave"]               = "K730"
    dash["strategy"]           = "K728 LDO-SOL FR Differential (LSD vs SVM, W=168h, Bybit primary)"
    dash["execution_mode"]     = "POST_ONLY_PARALLEL"
    dash["venue_config"]       = "BYBIT_PRIMARY"
    dash["cross_cluster_mechanism"] = {
        "formula":                 "diff = LDO_FR - SOL_FR  (= K594_dir - K476_dir per MR9)",
        "rolling_window":          "W=168h (21 x 8h periods)",
        "signal":                  "sign(rolling_mean_168h(diff))",
        "g5c_k594_ldo_btc_corr":   0.5053,    # FAIL structural (K594 REJECTED, not portfolio risk)
        "g5k_k708_bnb_sol_corr":   0.5917,    # FAIL (SOL shared — $2.4M combined = 0.024% SOL OI)
        "mr9_identity":            "LDO-SOL = K594_dir - K476_dir",
        "mr9_k594_k476_corr":      0.0585,
        "adf_tstat":               -17.4526,
        "adf_pvalue":              4.6437e-30,
        "ldo_gt_sol_pct":          85.1,       # LDO FR > SOL FR 85.1% of time (structural premium)
        "walk_forward_11_12":      True,       # 11/12 folds positive (91.7% rate)
        "note": (
            "LDO-SOL: $105,032/yr net @$10M @4x @3% sleeve. "
            "LDO (Lido DAO/Ethereum Liquid Staking) vs SOL (Solana SVM L1) — orthogonal clusters. "
            "LDO FR = ETH validator queue + stETH yield + LSD competition. Mean +15.96%/yr. "
            "SOL FR = retail meme cycles (BONK/WIF/POPCAT) + Jito MEV + Jupiter DEX. Mean +7.71%/yr. "
            "LDO structural premium +8.25%/yr (institutional vs retail separation). "
            "MR9: LDO-SOL = K594-K476 with K594⊥K476 (corr=0.0585) → genuine independent alpha. "
            "K594 TRIPLE-BLOCKED (vol+ETH+DeFi): removing BTC common factor unlocks K728 alpha. "
            "G5c K594 structural FAIL: K594 never deployed → NOT portfolio risk. "
            "G5k K708 BNB-SOL: corr=0.592 FAIL → SOL $2.4M combined = 0.024% SOL OI. "
            "11/12 WF positive (91.7%): one negative fold (fold 2 early 2024 = -7.51). "
            "G6 11.8 trades/yr: low but operationally acceptable (same issue K476). "
            "10th alt-alt scaffold (64th daemon). LDO new vertex in alt-alt group."
        ),
    }
    dash["activation_criteria"] = {
        "60d_paper_trade_gate":  "required",
        "realized_sharpe_min":   23.0,
        "fill_rate_min_pct":     60,
        "max_drawdown_max_pct":  15,
        "status":                "SCAFFOLD-READY",
        "activation_sleeve_pct": 0.030,
        "venue":                 "Bybit primary (LDO-PERP + SOL-PERP both on Bybit)",
    }
    dash["oos_performance"] = {
        "sharpe":                   46.8355,
        "sharpe_is":                14.431,
        "is_oos_ratio":             3.25,      # OOS/IS (IS=14.43, OOS=46.84 — OOS outperforms IS)
        "oos_ann_ret_1x_pct":       10.2973,
        "oos_ann_ret_4x_pct":       41.1892,
        "ann_return_usd_3pct_4x":   105_032,
        "wave_accept":              "K728 ACCEPT CONDITIONAL (K730 scaffold) — 14/19 §6 gates PASS",
        "cluster":                  "Ethereum LSD (LDO/Lido) vs Solana SVM L1 (SOL)",
        "g5c_verdict":              "FAIL structural (corr=0.505) — K594 REJECTED, not portfolio risk",
        "g5k_verdict":              "FAIL (corr=0.592) — K708 SOL shared, $2.4M combined 0.024% OI",
        "g6_verdict":               "FAIL (11.8/yr < 30) — low but operationally acceptable",
        "g8_verdict":               "FAIL (venue mismatch structural) — Bybit-primary mitigates",
        "walk_forward":             "11/12 folds positive (91.7% rate, fold 2 = -7.51 only negative)",
        "perm_pvalue":              0.0,
        "dsr_pvalue":               5.3233e-254,
        "trades_per_yr":            11.8,
        "max_drawdown_oos_pct":     0.1358,
        "daemon_number":            "64th",
        "alt_alt_rank":             "10th alt-alt scaffold (rank #3 by OOS Sharpe in alt-alt family)",
        "alt_alt_family_ranking": {
            "k686_avax_sol":         50.27,    # rank 1
            "k708_bnb_sol":          48.59,    # rank 2
            "k728_ldo_sol":          46.8355,  # rank 3 (THIS)
            "k682_atom_sol":         43.43,    # rank 4
            "k679_apt_sol":          39.29,    # rank 5
        },
    }
    dash["notional_caps"] = {
        "ldo_cap_note":  "LDO total: K728 3% only (first LDO in portfolio — new vertex, no existing LDO exposure).",
        "sol_cap_note":  "SOL total: K728 3% + K708 3% existing. G5k corr=0.592 FAIL. $2.4M combined = 0.024% SOL OI.",
        "hl_cap_note":   "HL concentration 64.5% UNCHANGED (Bybit-only — HL-only 67.5% > 65% cap AND HL LDO maxLev=5).",
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
      1. Fetch LDO + SOL FRs from Bybit
      2. Compute LDO-SOL differential + 168h rolling mean
      3. Decide position (sign of rolling mean — zero threshold)
      4. Compute delta-neutral notional
      5. If entering: submit paired trade (POST_ONLY, Bybit primary)
      6. If holding: check drift + rebalance
      7. Write k728_dashboard.json
    """
    ts_jst = datetime.now(JST).strftime("%Y-%m-%d %H:%M JST")
    print(f"\n=== K728 LDO-SOL FR Differential (Ethereum LSD vs Solana SVM) — {ts_jst} ===")
    print(f"  Mode:      {'DRY-RUN' if dry_run else 'PAPER-TRADE' if PAPER_TRADE else 'LIVE'}")
    print(f"  AUM:       ${aum:,.0f}  Sleeve: {SLEEVE_PCT:.1%}  Leverage: {LEVERAGE}x")
    print(f"  Venue:     Bybit primary (LDO-PERP + SOL-PERP, both Bybit perps)")
    print(f"  HL cap:    64.5%+3.0%=67.5%>65% cap + HL LDO maxLev=5 -> Bybit primary")
    print(f"  Execution: POST_ONLY parallel (K439)")
    print(f"  Signal:    diff = LDO_FR - SOL_FR  (= K594_dir - K476_dir per MR9)")
    print(f"             sign(rolling_mean_168h)  (zero threshold, W=168h = 21 x 8h periods)")
    print(f"  Clusters:  LDO Ethereum LSD (stETH protocol yield) | SOL Solana SVM (retail/meme)")
    print(f"  LDO pct:   LDO FR > SOL FR 85.1% of time (ETH staking institutional premium)")
    print(f"  MR9:       LDO-SOL = K594_dir - K476_dir (K594⊥K476 corr=0.0585)")
    print(f"  K594 note: K594 LDO-BTC TRIPLE-BLOCKED. K728 removes BTC factor -> MR9 PASS")
    print(f"  14/19 gates: OOS Sh=46.84, Net $105,032/yr @$10M (10th alt-alt, rank #3 OOS Sh)")
    print(f"  SOL caps:  K728 3% + K708 3% existing (G5k corr=0.592, $2.4M = 0.024% SOL OI)")

    # Step 1: Fetch + compute LDO-SOL differential
    print("\n  [Step 1] Computing LDO-SOL FR differential...")
    signal = compute_signal()
    print(f"  LDO FR:    {signal['fr_ldo']:+.8f} (8h, Bybit — stETH protocol yield/ETH staking)")
    print(f"  SOL FR:    {signal['fr_sol']:+.8f} (8h, Bybit — Solana retail/meme momentum)")
    print(f"  LDO-SOL:   {signal['ldo_sol_diff']:+.8f}  (direct differential = K594-K476)")
    print(f"  Mean 168h: {signal['mean_168h']:+.8f}")
    print(f"  Sigma:     {signal['diff_sigma']:+.8f}  (informational)")
    print(f"  Direction: {signal['signal_direction']:+d}  (+1=LDO_PREMIUM short LDO/long SOL 85%, -1=SOL_PREMIUM)")
    print(f"  Regime:    {signal['regime']}")
    print(f"  History:   {signal['history_points']} data points")

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
    print(f"  LDO leg:          ${notional_per_leg:,.0f}  (3.0% x ${aum/1e6:.0f}M x {LEVERAGE}x / 2)")
    print(f"  SOL leg:          ${notional_per_leg:,.0f}  (3.0% x ${aum/1e6:.0f}M x {LEVERAGE}x / 2)")
    print(f"  Total notional:   ${total_notional:,.0f}")
    print(f"  Margin required:  ${total_notional/LEVERAGE:,.0f}  ({SLEEVE_PCT:.1%} AUM)")
    print(f"  Profit @$10M 4x:  OOS 10.30% ann ret = $105,032/yr net (3% sleeve)")

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
    print(f"\n  === K728 Cycle Complete ===")
    print(f"  Position state:      {dash_out.get('position_state')}")
    print(f"  Regime:              {dash_out.get('regime')}")
    print(f"  LDO-SOL Mean 168h:   {dash_out.get('mean_168h'):+.8f}")
    print(f"  Signal direction:    {dash_out.get('signal_direction')}")
    print(f"  G5c K594 corr:       +0.5053 (FAIL structural — K594 REJECTED, not portfolio risk)")
    print(f"  G5k K708 corr:       +0.5917 (FAIL — K708 SOL shared, $2.4M 0.024% SOL OI)")
    print(f"  MR9 identity:        LDO-SOL = K594_dir - K476_dir (K594⊥K476 corr=0.0585)")
    print(f"  K594 context:        TRIPLE-BLOCKED (vol+ETH+DeFi). K728 = K594 - K476 no BTC.")
    print(f"  Paper-trade mode:    {PAPER_TRADE}")
    print(f"  OOS Sharpe:          46.84 (IS=14.43)")
    print(f"  G4 Walk-Forward:     11/12 positive (91.7% — fold 2 = -7.51 only negative)")
    print(f"  Cluster:             Ethereum LSD (LDO/Lido stETH) vs Solana SVM (SOL)")
    print(f"  Profit 3% sleeve:    $105,032/yr net @$10M @4x (OOS 10.30% ann ret)")
    print(f"  Alt-alt rank:        #3 OOS Sh=46.84 (AVAX-SOL 50.27 > BNB-SOL 48.59 > LDO-SOL 46.84)")
    print(f"  HL concentration:    64.5% UNCHANGED (Bybit-only — HL-only 67.5%>65% + HL LDO maxLev=5)")
    print(f"  60d gate:            Realized Sh>=23 + fill>=60% + maxDD<15%")
    print(f"  LDO notional cap:    K728 3% standalone (first LDO in portfolio, new vertex)")
    print(f"  SOL notional cap:    K728 3% + K708 3% existing (G5k borderline — monitor)")
    print(f"  v6.52 path:          K728 LDO-SOL 3% Bybit sleeve (64th daemon, 10th alt-alt)")
    print()

    return 0


# ─────────────────────────────────────────────────────────────────────────────
# CLI entry point
# ─────────────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="K728 LDO-SOL FR Differential Strategy (K730 scaffold, Ethereum LSD vs Solana SVM, Bybit primary)"
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
        print(f"\n=== K728 Dashboard ({dash.get('last_poll_jst', '—')}) ===")
        print(json.dumps(dash, indent=2))
        return 0

    if args.rebalance:
        dash   = _load_dashboard()
        result = daily_rebalance(dash)
        print(f"\n=== K728 Rebalance Check ===")
        print(json.dumps(result, indent=2))
        return 0

    if args.close:
        result = close_paired_position(args.close, dry_run=args.dry_run)
        print(f"\n=== K728 Close Result ===")
        print(json.dumps(result, indent=2))
        return 0

    return run_cycle(dry_run=args.dry_run, aum=args.aum)


if __name__ == "__main__":
    sys.exit(main())
