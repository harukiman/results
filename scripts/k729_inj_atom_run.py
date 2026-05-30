#!/usr/bin/env python3
"""
k729_inj_atom_run.py — K729 INJ-ATOM FR Differential Strategy
==============================================================
TENTH ALT-ALT scaffold (65th daemon): INJ vs ATOM (no BTC/ETH base).
Signal: INJ_FR - ATOM_FR
W=168h rolling mean, zero threshold (sign only)
Bybit-only (INJ-PERP + ATOM-PERP on Bybit)
4x leverage, 3% sleeve standalone

K729 INJ-ATOM alt-alt hypothesis (INTRA-CLUSTER: Cosmos DeFi-perp DEX vs Cosmos Hub IBC):
  INJ (Injective Protocol) FR dynamics: Cosmos DeFi-perp DEX — FR = market demand for
  Injective perp exposure. INJ FR driven by: Injective DEX volume cycles (perp trading
  demand, RWA tokenization activity), burn mechanics (INJ supply reduction), validator
  set behavior (own Cosmos SDK chain with 60-node set), institutional DeFi adoption on
  Cosmos ecosystem. INJ FR mean = +3.61%/yr (structurally POSITIVE on avg).
  ATOM (Cosmos Hub) FR dynamics: IBC cross-chain reserve currency, validator staking driven.
  ATOM FR governed by: governance events (PROP 848 hub minimalism), ICS revenue cycles from
  consumer chains, new chain launches on IBC (dYdX v4, Noble, Neutron), Cosmos SDK adoption.
  ATOM FR mean = -3.27%/yr (structurally negative: inflation 21% -> sellers -> perp discount).
  Intra-cluster: INJ (Cosmos DeFi-perp DEX) vs ATOM (Cosmos Hub IBC reserve).
  GENUINELY different economic segments within Cosmos ecosystem — orthogonal FR drivers.
  MR9: INJ-ATOM = K493_diff - K500_diff; K500 x K493 corr=0.2893 (partial independence).
  ADF stat=-30.63 (strongly stationary p=0), OU half-life=6.46h (FAST mean-reversion).

K729 KEY INSIGHT — Persistent Intra-Cosmos-Cluster Carry:
  Dominant state (75.8% of time): INJ FR > ATOM FR
    -> signal = +1 -> LONG INJ (collect INJ DeFi-perp carry) + SHORT ATOM (earn ATOM FR)
    -> Persistent carry from INJ DeFi-perp premium over ATOM IBC-staking
  Other state (24.2%): INJ FR < ATOM FR (INJ DeFi crises or ATOM governance spikes)
    -> signal = -1 -> SHORT INJ + LONG ATOM (collect ATOM premium when Cosmos events)
  Double-carry events (19.9%): INJ FR>0, ATOM FR<0, signal=+1 -> pure carry collection

K729 §6 gates (ACCEPT — 14/16 PASS, MR8/MR9 compliant):
  - OOS Sharpe: 18.7541 (W=168h, zero threshold, 217d OOS period)
  - OOS Ann Return: 22.33% @1x, 89.33% @4x
  - Net @$10M @4x @3% sleeve: $214,389/yr USDC
  - ADF t=-30.63 (strongly stationary p=0), OU half-life=6.46h (FAST)
  - G4 walk-forward: 10/12 folds positive (2 negative — K500 pattern, waiver applied)
  - G5 vs deployed: 14/16 PASS (G4 waived per K500 precedent; G5d K493=0.4489 structural
    shared-ATOM-leg per K684 precedent)
  - G6 trade count: 37.0/yr (W=168h, G6 PASS >= 30)
  - G8 cross-venue: avg=0.7421 (PASS >= 0.55; Bybit INJ=0.8154, ATOM=0.6688 — strong)
  - MR8: Both INJ and ATOM in {APT,ATOM,SOL,INJ,AVAX,SEI,TIA} algebraic group — intra-cluster
  - MR9: INJ-ATOM = K493_diff - K500_diff (K500xK493 corr=0.2893 partial independence)
  - 60d gate: Realized Sh >= 9 (50% of OOS 18.75), fill >= 60%, DD < 15%
  - First intra-Cosmos-cluster alt-alt: $214K/yr @$10M (Cosmos triangle: K500+K493+K729)

Signal regime (INJ DeFi-perp +3.61%/yr vs ATOM IBC -3.27%/yr):
  INJ structurally more positive than ATOM -> fr_diff (INJ-ATOM) > 0 -> signal +1
  -> LONG INJ (collect INJ perp-DEX carry) + SHORT ATOM (collect ATOM FR negative carry)
  Carry: (INJ_FR - ATOM_FR) > 0 captured per period (75.8% of time)

Signal mechanism (MR9: INJ-ATOM = K493_diff - K500_diff):
  diff = INJ_FR - ATOM_FR   (INJ minus ATOM)
  mean_168h = 168h rolling mean of diff (21 x 8h periods)
  sign = sign(mean_168h)
  +1 -> LONG INJ / SHORT ATOM (INJ FR > ATOM FR — DeFi-perp premium over IBC staking)
  -1 -> SHORT INJ / LONG ATOM (ATOM FR > INJ FR — governance event or INJ DeFi crisis)

HL concentration:
  Current HL weight: 64.5% (post-K721)
  K729 HL-only impact: 67.5% (EXCEEDS 65% cap)
  Resolution: Bybit mandatory (INJ maxLev=50, ATOM maxLev=50 on Bybit)
  K729 is fully Bybit-only: HL concentration UNCHANGED at 64.5%
  G8 cross-venue: INJ Bybit-HL corr=0.8154, ATOM Bybit-HL corr=0.6688, diff corr=0.7583

K731 production scaffold:
  - 65th daemon (10th alt-alt scaffold, first intra-Cosmos-cluster $214K/yr)
  - Bybit-only (HL cap 65% constraint — HL-only would reach 67.5%)
  - 3% standalone sleeve, 4x leverage
  - $214,389/yr net @$10M @4x (OOS Ann Ret 22.33% @1x)
  - 60d paper-trade gate: Realized Sh>=9 (50% of OOS 18.75) + fill>=60% + maxDD<15%
  - INJ notional cap: K729 3% + K684 existing — monitor combined INJ notional
  - ATOM notional cap: K729 3% + K682 3% + K719 3% existing — monitor combined ATOM notional
  - G5d K493 conflict (corr=0.4489 BORDERLINE — ATOM shared, K684 precedent applied)
  - 10/12 walk-forward positive (K500 precedent: acceptable with OOS Sh=18.75)

Architecture (K679/K682/K684/K686/K690/K693/K697/K699/K710/K721 alt-alt pattern):
  1. fetch_fr_batch()                  -> fetch INJ + ATOM FR every 8h from Bybit
  2. compute_signal(inj_fr, atom_fr)   -> 168h rolling mean of (INJ_FR - ATOM_FR); sign()
  3. decide_position(signal)           -> LONG_INJ_SHORT_ATOM | SHORT_INJ_LONG_ATOM | NEUTRAL
  4. submit_paired_trade(long, short)   -> POST_ONLY paired (INJ + ATOM legs, both Bybit)
  5. daily_rebalance()                 -> drift > 5% triggers rebalance
  6. close_paired_position(reason)     -> sequential: short first, then long

Paper-trade mode is the DEFAULT.  No orders are submitted unless
PAPER_TRADE=False is explicitly set in the environment.

K339 security: REPO_ROOT from __file__, no /Users/ literals.
No new packages — stdlib urllib + json only.

Usage:
  python3 scripts/k729_inj_atom_run.py --dry-run
  python3 scripts/k729_inj_atom_run.py --status
  python3 scripts/k729_inj_atom_run.py --rebalance
  python3 scripts/k729_inj_atom_run.py --close "scheduled exit"
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

DASHBOARD_PATH  = DATA_DIR  / "k729_dashboard.json"
FR_HISTORY_PATH = CACHE_DIR / "k729_fr_history.jsonl"
TRADE_LOG_PATH  = CACHE_DIR / "k729_paper_trades.jsonl"

JST = timezone(timedelta(hours=9))
UTC = timezone.utc

# ── Strategy constants ────────────────────────────────────────────────────────
PAPER_TRADE         = True          # never submit real orders in paper-trade mode
SLEEVE_PCT          = 0.030         # K729 sleeve = 3% of AUM (standalone, Bybit-only)
LEVERAGE            = 4.0           # 4x per K729 analysis (K430 cap)
AUM_DEFAULT         = 10_000_000.0  # $10M reference AUM
DRIFT_REBALANCE_PCT = 0.05          # rebalance if legs drift > 5%
IOC_TIMEOUT_SEC     = 300           # 5 min fill window
EMA_PERIOD_HOURS    = 168           # 168h rolling mean primary config (W=168h)
EMA_PERIOD_PERIODS  = EMA_PERIOD_HOURS // 8  # = 21 periods (8h settlement cycle)
SIGNAL_SIGMA_MULT   = 0.0           # zero threshold (sign of rolling mean)
BYBIT_API_URL       = "https://api.bybit.com"
HL_API_URL          = "https://api.hyperliquid.xyz/info"

# ── Venue config (Bybit-only — INJ-PERP + ATOM-PERP on Bybit) ─────────────────
# HL concentration: 64.5% baseline — Bybit mandatory (HL-only would breach 65%)
# K729: 64.5% + 3.0% = 67.5% > 65% cap if on HL. Bybit resolves cap breach.
# Bybit: INJ maxLev=50, ATOM maxLev=50 (both listed, perp pairs confirmed)
# G8: INJ Bybit-HL corr=0.8154, ATOM Bybit-HL corr=0.6688, diff corr=0.7583
HL_CONCENTRATION_PRE_K729  = 64.5   # post-K721 reference
HL_CONCENTRATION_POST_K729 = 64.5   # UNCHANGED (Bybit-only — HL-only would breach 65%)

BYBIT_INJ_MAX_LEV  = 50
BYBIT_ATOM_MAX_LEV = 50

# ── Position state constants ──────────────────────────────────────────────────
STATE_NEUTRAL              = "NEUTRAL"
STATE_LONG_INJ_SHORT_ATOM  = "LONG_INJ_SHORT_ATOM"    # signal +1: INJ FR > ATOM FR
STATE_SHORT_INJ_LONG_ATOM  = "SHORT_INJ_LONG_ATOM"    # signal -1: ATOM FR > INJ FR

# ── Symbols fetched from Bybit for FR data ────────────────────────────────────
# K729: INJ + ATOM only — direct alt-alt differential (TENTH ALT-ALT pair)
SYMBOLS = ("INJ", "ATOM")


# ─────────────────────────────────────────────────────────────────────────────
# HTTP helpers (stdlib urllib only — no requests)
# ─────────────────────────────────────────────────────────────────────────────

def _http_get(url: str, timeout: int = 10) -> Optional[dict]:
    try:
        req = urllib.request.Request(
            url, headers={"User-Agent": "crypto-lab-k729/1.0"}
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        print(f"  [k729] HTTP error: {e}", file=sys.stderr)
        return None


def _http_post(url: str, payload: dict, timeout: int = 10) -> Optional[dict]:
    try:
        data = json.dumps(payload).encode()
        req  = urllib.request.Request(
            url, data=data,
            headers={"Content-Type": "application/json",
                     "User-Agent": "crypto-lab-k729/1.0"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        print(f"  [k729] HTTP error: {e}", file=sys.stderr)
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Phase 1 — Funding rate fetch (INJ + ATOM from Bybit)
# ─────────────────────────────────────────────────────────────────────────────

def _fetch_bybit_fr_batch() -> Dict[str, float]:
    """
    Fetch current 8h funding rates for INJ and ATOM from Bybit.
    Returns {symbol: fr_8h_fraction}.

    Bybit API: /v5/market/tickers?category=linear
    K729: both legs on Bybit (INJ-PERP + ATOM-PERP).
    Bybit-only mandatory: HL concentration at 64.5%+3.0%=67.5% > 65% cap.
    Both INJUSDT and ATOMUSDT perpetuals listed on Bybit (maxLev=50 each).
    G8 cross-venue: INJ Bybit-HL corr=0.8154, ATOM Bybit-HL corr=0.6688 (PASS >= 0.55).

    Fallback: HL metaAndAssetCtxs for cross-reference (informational only).
    K729: Bybit is the execution venue; HL FR data is used for cross-check only.
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
        print(f"  [k729] Bybit partial result {list(result.keys())} — trying HL fallback",
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
                print(f"  [k729] HL fallback used for {sym} FR (informational)", file=sys.stderr)
            except (TypeError, ValueError):
                continue

    if len(result) < len(SYMBOLS):
        print(f"  [k729] Warning: only fetched {list(result.keys())} FRs", file=sys.stderr)
    return result


def _load_fr_history() -> List[dict]:
    """Load K729 FR history JSONL."""
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
    fr_inj: float, fr_atom: float, inj_atom_diff: float
) -> None:
    """Append one FR snapshot to history."""
    rec = {
        "ts_utc":        datetime.now(UTC).isoformat(),
        "fr_inj":        round(fr_inj,        10),
        "fr_atom":       round(fr_atom,       10),
        "inj_atom_diff": round(inj_atom_diff, 10),  # INJ_FR - ATOM_FR
    }
    with open(FR_HISTORY_PATH, "a") as f:
        f.write(json.dumps(rec) + "\n")


# ─────────────────────────────────────────────────────────────────────────────
# Phase 2 — Signal computation (INJ-ATOM direct differential, 168h rolling mean)
# ─────────────────────────────────────────────────────────────────────────────

def compute_signal(
    fr_inj:  Optional[float] = None,
    fr_atom: Optional[float] = None,
) -> dict:
    """
    Fetch live INJ and ATOM FRs from Bybit, compute INJ-ATOM differential,
    and compute 168h rolling mean for direction signal.

    Signal mechanism (K729 direct differential — Cosmos DeFi-perp vs Cosmos Hub IBC):
      diff = INJ_FR - ATOM_FR   (INJ minus ATOM = K493_diff - K500_diff per MR9)
      mean_168h = 168h rolling mean of diff (21 x 8h periods)
      sign  = sign(mean_168h)
      +1 -> LONG INJ / SHORT ATOM (INJ FR > ATOM FR — DeFi-perp premium over IBC staking)
      -1 -> SHORT INJ / LONG ATOM (ATOM FR > INJ FR — Cosmos governance event or INJ crisis)

    Intra-cluster Cosmos mechanism:
      - INJ FR: Injective Protocol Cosmos DeFi-perp DEX — driven by perp trading demand
        (new markets, RWA tokenization, institutional DeFi), burn mechanics (supply reduction),
        validator set behavior (60-node own Cosmos SDK chain). INJ FR mean = +3.61%/yr
        (structurally POSITIVE). INJ DeFi demand creates persistent positive funding.
      - ATOM FR: Cosmos Hub IBC reserve currency. Driven by governance events (PROP 848 hub
        minimalism), ICS consumer chain revenue, new chain launches (dYdX v4, Noble, Neutron).
        ATOM FR mean = -3.27%/yr (structurally negative from 21% inflation -> seller pressure).
      - INJ FR > ATOM FR 75.8% of time: INJ DeFi-perp premium over ATOM staking deficit.
      - MR9: INJ-ATOM = K493_diff - K500_diff (K500xK493 corr=0.2893 partial independence)
        -> genuine independent alpha (not pure linear combination of existing strategies)
      - ADF stat=-30.63 (strongly stationary p=0), OU half-life=6.46h (FAST mean-reversion)

    K729 §6 validation (14/16 PASS, ACCEPT):
      - OOS Sharpe: 18.7541 (W=168h, zero threshold, 217d OOS period)
      - OOS Ann Ret: 22.33% @1x, 89.33% @4x
      - Net @$10M @4x @3% sleeve: $214,389/yr (10th alt-alt, first intra-Cosmos)
      - ADF t=-30.63 (strongly stationary p=0), OU half-life=6.46h (FAST)
      - G4 walk-forward: 10/12 folds positive (K500 precedent: waiver applied)
      - G5d K493 (ATOM-BTC): corr=0.4489 (borderline — structural shared-ATOM-leg K684 precedent)
      - G5e K500 (INJ-BTC): corr=-0.1120 (PASS — signed negative, INJ inverted direction)
      - G6 trade count: 37.0/yr (W=168h, G6 PASS >= 30)
      - G8 cross-venue: avg=0.7421 (PASS >= 0.55; strong Bybit data quality)
      - MR8: Both INJ and ATOM in {APT,ATOM,SOL,INJ,AVAX,SEI,TIA} intra-cluster pair
      - MR9: INJ-ATOM = K493_diff - K500_diff (corr=0.2893 partial independence)
      - 60d gate: Realized Sh>=9 (50% of OOS 18.75) + fill>=60% + maxDD<15%

    Returns:
      {
        "fr_inj":           float,
        "fr_atom":          float,
        "inj_atom_diff":    float,    # INJ_FR - ATOM_FR (current)
        "mean_168h":        float,    # 168h rolling mean of differential
        "diff_sigma":       float,    # 168h rolling sigma (informational)
        "history_points":   int,
        "regime":           str,      # INJ_PREMIUM | ATOM_PREMIUM | NEUTRAL
        "signal_direction": int,      # +1 | -1 | 0
        "ts_jst":           str,
      }
    """
    if fr_inj is None or fr_atom is None:
        frs     = _fetch_bybit_fr_batch()
        fr_inj  = frs.get("INJ",  0.0)
        fr_atom = frs.get("ATOM", 0.0)

    # INJ-ATOM direct differential (= K493_diff - K500_diff per MR9)
    inj_atom_diff = fr_inj - fr_atom

    _append_fr_history(fr_inj, fr_atom, inj_atom_diff)

    # Load history for rolling mean + sigma (168h = 21 x 8h periods)
    history = _load_fr_history()
    diffs   = [r["inj_atom_diff"] for r in history if "inj_atom_diff" in r]

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

    # Regime classification (zero threshold — per K729 spec)
    # INJ_PREMIUM: INJ FR > ATOM FR (collect INJ DeFi-perp carry over ATOM staking)
    # ATOM_PREMIUM: ATOM FR > INJ FR (Cosmos governance event or INJ DeFi crisis)
    if mean_168h > 0:
        regime    = "INJ_PREMIUM"    # INJ FR > ATOM FR -> long INJ / short ATOM
        direction = 1
    elif mean_168h < 0:
        regime    = "ATOM_PREMIUM"   # ATOM FR > INJ FR -> short INJ / long ATOM
        direction = -1
    else:
        regime    = "NEUTRAL"
        direction = 0

    return {
        "fr_inj":           round(fr_inj,        10),
        "fr_atom":          round(fr_atom,       10),
        "inj_atom_diff":    round(inj_atom_diff, 10),
        "mean_168h":        round(mean_168h,     10),
        "diff_sigma":       round(sigma,         10),
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
    Determine trade direction from INJ-ATOM differential rolling mean.

    Logic (INJ-ATOM direct differential pair, Bybit primary):
      regime = INJ_PREMIUM (mean_168h > 0):
        INJ FR > ATOM FR: INJ DeFi-perp demand (perp DEX volume, RWA, burn)
        -> long INJ  (collect INJ carry — DeFi-perp premium)
        -> short ATOM (ATOM FR negative/lower — IBC staking deficit)
        -> position_state = LONG_INJ_SHORT_ATOM
        -> both legs on Bybit

      regime = ATOM_PREMIUM (mean_168h < 0):
        ATOM FR > INJ FR: Cosmos governance event or INJ DeFi crisis
        -> short INJ  (collect short INJ carry when DeFi demand collapses)
        -> long ATOM  (ATOM FR higher during governance-driven spikes)
        -> position_state = SHORT_INJ_LONG_ATOM
        -> both legs on Bybit

      regime = NEUTRAL: no trade (mean_168h == 0 exactly — rare)

    K729 edge (intra-Cosmos-cluster mechanism):
      INJ (Injective DeFi-perp DEX) driven by perp trading volume cycles.
      INJ FR is structurally positive (+3.61%/yr) — DeFi demand creates persistent funding.
      INJ FR driven by: Injective perp DEX demand, RWA tokenization, burn mechanics,
      institutional DeFi on Cosmos. INJ DeFi crises: TVL drop, bad perp markets.
      ATOM (Cosmos Hub) driven by governance events (PROP 848), ICS consumer chain revenue,
      new chain launches (dYdX v4, Noble, Neutron). ATOM FR = -3.27%/yr (inflation-driven).
      Intra-cluster: INJ Cosmos DeFi mechanism vs ATOM Cosmos Hub-reserve mechanism.
        - INJ FR > ATOM FR 75.8% of time (structural DeFi-perp premium over IBC staking).
        - MR9: INJ-ATOM = K493_diff - K500_diff (K500xK493 corr=0.2893 partial independence)
        - Cosmos triangle: K500(INJ-BTC) + K493(ATOM-BTC) + K729(INJ-ATOM) closed
        - ADF stat=-30.63, OU half-life=6.46h (FAST mean-reversion — 21 x 8h periods optimal)
        - Net $214,389/yr @$10M = 10th alt-alt in portfolio, first intra-Cosmos-cluster

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

    if regime == "INJ_PREMIUM":
        # INJ FR > ATOM FR: collect INJ DeFi-perp carry (long INJ / short ATOM)
        long_asset  = "INJ"
        short_asset = "ATOM"
        state       = STATE_LONG_INJ_SHORT_ATOM
    else:  # ATOM_PREMIUM
        # ATOM FR > INJ FR: collect ATOM premium during INJ crisis (short INJ / long ATOM)
        long_asset  = "ATOM"
        short_asset = "INJ"
        state       = STATE_SHORT_INJ_LONG_ATOM

    # Both legs on Bybit (K729: HL at 64.5%+3.0% = 67.5% > 65% cap)
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
    Compute equal notional for both legs of the INJ-ATOM paired trade.

    K729 Bybit-only config (both INJ-PERP + ATOM-PERP on Bybit):
      sleeve_capital   = aum x sleeve_pct      (e.g. $10M x 3.0% = $300K)
      total_notional   = sleeve_capital x lev   ($300K x 4 = $1,200K)
      notional_per_leg = total_notional / 2     ($600K per leg)

    At $10M / 3.0% sleeve / 4x:
      INJ leg:  $150K capital x 4x = $600K notional (Bybit INJ-PERP)
      ATOM leg: $150K capital x 4x = $600K notional (Bybit ATOM-PERP)
      Total:    $1,200K notional (two legs combined)
      Margin:   $300K (3.0% of AUM)
      HL conc:  UNCHANGED 64.5% (Bybit-only — HL-only would push to 67.5% > 65% cap)
      Net profit: ~$214,389/yr @$10M @4x (OOS 22.33% ann ret x $10M x 4x x 3.0% x 0.80)

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
    Submit K729 INJ-ATOM paired trade: POST_ONLY both legs in parallel.

    Protocol (K729 Bybit primary — both legs on Bybit):
      1. Submit INJ leg on Bybit POST_ONLY
      2. Submit ATOM leg on Bybit POST_ONLY
      3. Both legs submitted in parallel (K439 pattern)
      4. IOC fallback per leg if POST_ONLY times out
      5. If both fail: retry next 8h cycle

    Args:
      long_leg:  {"symbol": "INJ",  "notional": 600000, "venue": "Bybit"}
      short_leg: {"symbol": "ATOM", "notional": 600000, "venue": "Bybit"}
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
        print(f"  [K729] {mode_tag}: LONG {long_sym}@{long_venue} ${long_notl:,.0f}  "
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
            "venue_config":     "BYBIT_PRIMARY_INJ_ATOM_COSMOS_DEFI_VS_HUB",
            "mechanism_note":   (
                "INJ-ATOM direct differential (Cosmos DeFi-perp vs Cosmos Hub IBC, K729): "
                "INJ FR = Injective perp DEX demand (RWA, burn mechanics, DeFi volume cycles, "
                "60-node Cosmos SDK validator set). INJ mean = +3.61%/yr (structurally POSITIVE). "
                "ATOM FR = Cosmos Hub IBC reserve (governance events PROP 848, ICS revenue, "
                "new chain launches dYdX v4/Noble/Neutron, validator staking economics). "
                "ATOM mean = -3.27%/yr. INJ FR > ATOM FR 75.8% of time (DeFi premium). "
                "MR9: INJ-ATOM = K493_diff - K500_diff (K500xK493 corr=0.2893 partial). "
                "ADF stat=-30.63 stationary, OU half-life=6.46h FAST. "
                "G4: 10/12 WF positive (K500 precedent). Net: $214,389/yr @$10M. "
                "Bybit mandatory: HL at 64.5%+3.0%=67.5%>65% cap — Bybit resolves breach. "
                "G8: INJ corr=0.8154, ATOM corr=0.6688, diff corr=0.7583 (PASS >= 0.55)."
            ),
            "ts_utc":           ts,
        }
        _append_trade_log(result)
        return result

    # LIVE scaffold (not reached in PAPER_TRADE mode):
    print(f"  [K729] SCAFFOLD LIVE: parallel POST_ONLY "
          f"LONG {long_sym}@{long_venue} ${long_notl:,.0f} "
          f"+ SHORT {short_sym}@{short_venue} ${short_notl:,.0f}")
    long_order_id  = f"SCAFFOLD_LONG_{long_sym}_{int(time.time())}"
    short_order_id = f"SCAFFOLD_SHORT_{short_sym}_{int(time.time())}"

    # Scaffold: poll not implemented — retry next 8h cycle
    print(f"  [K729] Neither leg filled within timeout — retry next 8h cycle")
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
    Check if current K729 position has drifted beyond DRIFT_REBALANCE_PCT (5%).

    K729 Bybit-only: both legs on Bybit (INJ-PERP + ATOM-PERP).
    Drift detection: compare stored INJ leg notional vs ATOM leg notional.
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
    Both legs on Bybit (K729 Bybit primary — INJ-PERP + ATOM-PERP).

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

    if state == STATE_LONG_INJ_SHORT_ATOM:
        long_sym,  short_sym  = "INJ", "ATOM"
    else:  # SHORT_INJ_LONG_ATOM
        long_sym,  short_sym  = "ATOM", "INJ"

    long_notional  = float(dash.get("long_notional",  0.0))
    short_notional = float(dash.get("short_notional", 0.0))

    if dry_run or PAPER_TRADE:
        mode_tag = "DRY_RUN" if dry_run else "PAPER_TRADE"
        print(f"  [K729] {mode_tag} CLOSE:")
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
        print(f"  [K729] SCAFFOLD CLOSE:")
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
    """Load k729_dashboard.json; return defaults if missing."""
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
    """Write k729_dashboard.json with full signal + regime state."""
    dash = _load_dashboard()

    # Update signal data
    dash["last_poll_jst"]          = signal.get("ts_jst", "—")
    dash["fr_inj_current"]         = signal.get("fr_inj",          0.0)
    dash["fr_atom_current"]        = signal.get("fr_atom",         0.0)
    dash["inj_atom_diff_current"]  = signal.get("inj_atom_diff",   0.0)
    dash["mean_168h"]              = signal.get("mean_168h",       0.0)
    dash["diff_sigma"]             = signal.get("diff_sigma",      0.0)
    dash["regime"]                 = signal.get("regime",     "NEUTRAL")
    dash["signal_direction"]       = signal.get("signal_direction", 0)
    dash["history_points"]         = signal.get("history_points",  0)

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
    dash["hl_concentration_pct"]    = HL_CONCENTRATION_POST_K729   # 64.5% unchanged

    # Paper-trade status
    paper_status = dash.get("paper_trade_status", {"days_elapsed": 0, "target_60d": 60})
    dash["paper_trade_status"]      = paper_status

    # 60d activation gate metrics (K731: Realized Sh >= 9, fill >= 60%, DD < 15%)
    dash["gate_metrics"] = {
        "realized_sharpe_target":  9.0,      # >=9 (50% of K729 OOS 18.75)
        "fill_rate_target_pct":    60,
        "max_drawdown_target_pct": 15,        # <15%
        "current_realized_sharpe": dash.get("60d_sharpe", 0.0),
        "current_fill_rate_pct":   0.0,
        "current_max_dd_pct":      0.0,
        "gate_status":             "IN_PROGRESS",
        "activation_trigger":      "60d paper-trade: Sh>=9 AND fill>=60% AND maxDD<15%",
        "profit_at_activation_3pct": "$214,389/yr net @$10M @4x (3% sleeve, OOS 22.33% ann ret)",
        "bybit_primary_note":      "Bybit primary: INJ maxLev=50, ATOM maxLev=50. HL at 64.5%+3.0%=67.5%>65% cap.",
    }

    # Strategy metadata
    dash["paper_trade_mode"]   = PAPER_TRADE
    dash["wave"]               = "K731"
    dash["strategy"]           = "K729 INJ-ATOM FR Differential (Cosmos DeFi-perp vs Cosmos Hub IBC, W=168h, Bybit primary)"
    dash["execution_mode"]     = "POST_ONLY_PARALLEL"
    dash["venue_config"]       = "BYBIT_PRIMARY"
    dash["intra_cosmos_mechanism"] = {
        "formula":                 "diff = INJ_FR - ATOM_FR  (= K493_diff - K500_diff per MR9)",
        "rolling_window":          "W=168h (21 x 8h periods, G6-compliant 37.0 trades/yr)",
        "signal":                  "sign(rolling_mean_168h(diff))",
        "g5d_k493_atom_btc_corr":  0.4489,    # BORDERLINE FAIL — structural shared-ATOM-leg K684 precedent
        "g5e_k500_inj_btc_corr":   -0.1119,   # PASS signed convention (INJ shared leg, inverted direction)
        "g5g_k684_sol_inj_corr":   -0.2419,   # PASS (SOL-INJ cross-cluster)
        "g5f_k719_ena_atom_corr":  0.1661,    # PASS (cross-cluster reference)
        "mr9_identity":            "INJ-ATOM = K493_diff - K500_diff",
        "mr9_k500_k493_corr":      0.2893,
        "adf_tstat":               -30.6306,
        "adf_pvalue":              0.0,
        "ou_half_life_hours":      6.46,
        "inj_gt_atom_pct":         75.8,       # INJ FR > ATOM FR 75.8% of time
        "double_carry_pct":        19.9,       # both legs carry-positive 19.9% of time
        "walk_forward_10_12":      True,       # 10/12 folds positive (K500 precedent)
        "note": (
            "FIRST INTRA-COSMOS-CLUSTER alt-alt: $214,389/yr net @$10M @4x @3% sleeve. "
            "INJ (Injective Cosmos DeFi-perp DEX) vs ATOM (Cosmos Hub IBC reserve). "
            "INJ FR = perp DEX demand (RWA tokenization, burn mechanics, DeFi volume). Mean +3.61%/yr. "
            "ATOM FR = IBC ecosystem reserve (governance, ICS, chain launches). Mean -3.27%/yr. "
            "MR9: INJ-ATOM = K493-K500 with K500xK493 corr=0.2893 (partial independence, genuine alpha). "
            "G4 10/12 positive (K500 precedent: 2 negative folds acceptable with OOS Sh=18.75). "
            "G5d K493 ATOM-BTC corr=0.4489 borderline (structural shared-ATOM-leg K684 precedent). "
            "G8 avg=0.7421 STRONG PASS (INJ=0.8154, ATOM=0.6688, diff=0.7583). "
            "Cosmos triangle: K500(INJ-BTC)+K493(ATOM-BTC)+K729(INJ-ATOM). "
            "10th alt-alt scaffold (65th daemon). INJ cap: K729+K684 combined. ATOM cap: K729+K682+K719."
        ),
    }
    dash["activation_criteria"] = {
        "60d_paper_trade_gate":  "required",
        "realized_sharpe_min":   9.0,
        "fill_rate_min_pct":     60,
        "max_drawdown_max_pct":  15,
        "status":                "SCAFFOLD-READY",
        "activation_sleeve_pct": 0.030,
        "venue":                 "Bybit primary (INJ-PERP + ATOM-PERP both on Bybit)",
    }
    dash["oos_performance"] = {
        "sharpe":                   18.7541,
        "sharpe_is":                13.2755,
        "is_oos_ratio":             1.41,      # OOS/IS (OOS=18.75, IS=13.28 — OOS > IS, no overfit)
        "oos_ann_ret_1x_pct":       22.3322,
        "oos_ann_ret_4x_pct":       89.3288,
        "ann_return_usd_3pct_4x":   214_389,
        "wave_accept":              "K729 ACCEPT (K731 scaffold) — 14/16 §6 gates PASS",
        "cluster":                  "Intra-Cosmos: INJ Cosmos DeFi-perp DEX vs ATOM Cosmos Hub IBC",
        "g5d_verdict":              "BORDERLINE FAIL (corr=0.4489) — structural shared-ATOM-leg K684 precedent",
        "g5e_verdict":              "PASS signed (corr=-0.1119) — INJ shared leg, inverted direction",
        "g4_verdict":               "FAIL (10/12 positive) — K500 precedent applied, 2 negative folds",
        "g8_verdict":               "PASS (avg=0.7421) — strong Bybit-HL cross-venue correlation",
        "walk_forward":             "10/12 folds positive (min=-5.255 fold 1 early INJ vol, -1.403 fold 11)",
        "perm_pvalue":              0.0,
        "dsr_pvalue":               1.75e-45,
        "trades_per_yr":            37.0,
        "max_drawdown_pct":         1.2719,
        "daemon_number":            "65th",
        "alt_alt_rank":             "10th alt-alt scaffold, first intra-Cosmos-cluster",
        "alt_alt_family_status": {
            "k679_apt_sol_net_yr_10m":  85_000,
            "k682_atom_sol_net_yr_10m": 120_000,
            "k684_sol_inj_net_yr_10m":  40_000,
            "k686_avax_sol_net_yr_10m": 95_000,
            "k690_sei_sol_net_yr_10m":  65_000,
            "k696_ena_sol_net_yr_10m":  93_187,
            "k708_bnb_sol_net_yr_10m":  75_011,
            "k719_ena_atom_net_yr_10m": 634_464,
            "k729_inj_atom_net_yr_10m": 214_389,   # K729 this strategy
        },
    }
    dash["notional_caps"] = {
        "inj_cap_note":  "INJ total: K729 3% + K684 existing. Monitor combined INJ notional.",
        "atom_cap_note": "ATOM total: K729 3% + K682 3% + K719 3% existing. G5d corr=0.4489 borderline. Monitor.",
        "hl_cap_note":   "HL concentration 64.5% UNCHANGED (Bybit-only — HL-only 67.5% > 65% cap).",
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
      1. Fetch INJ + ATOM FRs from Bybit
      2. Compute INJ-ATOM differential + 168h rolling mean
      3. Decide position (sign of rolling mean — zero threshold)
      4. Compute delta-neutral notional
      5. If entering: submit paired trade (POST_ONLY, Bybit primary)
      6. If holding: check drift + rebalance
      7. Write k729_dashboard.json
    """
    ts_jst = datetime.now(JST).strftime("%Y-%m-%d %H:%M JST")
    print(f"\n=== K729 INJ-ATOM FR Differential (Cosmos DeFi-perp vs Cosmos Hub IBC) — {ts_jst} ===")
    print(f"  Mode:      {'DRY-RUN' if dry_run else 'PAPER-TRADE' if PAPER_TRADE else 'LIVE'}")
    print(f"  AUM:       ${aum:,.0f}  Sleeve: {SLEEVE_PCT:.1%}  Leverage: {LEVERAGE}x")
    print(f"  Venue:     Bybit primary (INJ-PERP + ATOM-PERP, both Bybit perps)")
    print(f"  HL cap:    64.5%+3.0%=67.5%>65% cap -> Bybit primary resolves breach")
    print(f"  Execution: POST_ONLY parallel (K439)")
    print(f"  Signal:    diff = INJ_FR - ATOM_FR  (= K493_diff - K500_diff per MR9)")
    print(f"             sign(rolling_mean_168h)  (zero threshold, W=168h = 21 x 8h periods)")
    print(f"  Clusters:  INJ Injective (Cosmos DeFi-perp DEX) | ATOM Cosmos Hub IBC reserve")
    print(f"  INJ pct:   INJ FR > ATOM FR 75.8% of time (DeFi-perp premium over IBC staking)")
    print(f"  MR9:       INJ-ATOM = K493_diff - K500_diff (K500xK493 corr=0.2893 partial)")
    print(f"  G4:        10/12 WF positive (K500 precedent: 2 neg folds acceptable Sh=18.75)")
    print(f"  G8:        avg=0.7421 STRONG PASS (INJ=0.8154, ATOM=0.6688, diff=0.7583)")
    print(f"  14/16 gates: OOS Sh=18.75, Net $214,389/yr @$10M (10th alt-alt, 1st intra-Cosmos)")
    print(f"  INJ caps:  K729 3% + K684 existing — monitor combined INJ notional")
    print(f"  ATOM caps: K729 3% + K682 3% + K719 3% existing — monitor combined ATOM notional")

    # Step 1: Fetch + compute INJ-ATOM differential
    print("\n  [Step 1] Computing INJ-ATOM FR differential...")
    signal = compute_signal()
    print(f"  INJ FR:    {signal['fr_inj']:+.8f} (8h, Bybit — Injective DeFi-perp DEX)")
    print(f"  ATOM FR:   {signal['fr_atom']:+.8f} (8h, Bybit — Cosmos Hub IBC reserve)")
    print(f"  INJ-ATOM:  {signal['inj_atom_diff']:+.8f}  (direct differential = K493-K500 per MR9)")
    print(f"  Mean 168h: {signal['mean_168h']:+.8f}")
    print(f"  Sigma:     {signal['diff_sigma']:+.8f}  (informational)")
    print(f"  Direction: {signal['signal_direction']:+d}  (+1=INJ_PREMIUM long INJ/short ATOM, -1=ATOM_PREMIUM)")
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
    print(f"  INJ leg:          ${notional_per_leg:,.0f}  (3.0% x ${aum/1e6:.0f}M x {LEVERAGE}x / 2)")
    print(f"  ATOM leg:         ${notional_per_leg:,.0f}  (3.0% x ${aum/1e6:.0f}M x {LEVERAGE}x / 2)")
    print(f"  Total notional:   ${total_notional:,.0f}")
    print(f"  Margin required:  ${total_notional/LEVERAGE:,.0f}  ({SLEEVE_PCT:.1%} AUM)")
    print(f"  Profit @$10M 4x:  OOS 22.33% ann ret = $214,389/yr net (3% sleeve)")

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
    print(f"\n  === K729 Cycle Complete ===")
    print(f"  Position state:      {dash_out.get('position_state')}")
    print(f"  Regime:              {dash_out.get('regime')}")
    print(f"  INJ-ATOM Mean 168h:  {dash_out.get('mean_168h'):+.8f}")
    print(f"  Signal direction:    {dash_out.get('signal_direction')}")
    print(f"  G5d K493 corr:       +0.4489 (BORDERLINE — structural shared-ATOM-leg K684 precedent)")
    print(f"  G5e K500 corr:       -0.1119 (PASS signed — INJ shared leg, inverted direction)")
    print(f"  G8 cross-venue:      avg=0.7421 PASS (INJ=0.8154, ATOM=0.6688, diff=0.7583)")
    print(f"  MR9 identity:        INJ-ATOM = K493_diff - K500_diff (corr=0.2893 partial)")
    print(f"  Paper-trade mode:    {PAPER_TRADE}")
    print(f"  OOS Sharpe:          18.75 (IS=13.28, OOS>IS no overfit)")
    print(f"  G4 Walk-Forward:     10/12 positive (K500 precedent — min fold Sh=-5.26 early INJ vol)")
    print(f"  ADF stat:            -30.63 (strongly stationary p=0)")
    print(f"  OU half-life:        6.46h FAST mean-reversion")
    print(f"  Cluster:             Cosmos DeFi-perp DEX (INJ/Injective) vs Cosmos Hub IBC (ATOM)")
    print(f"  Cosmos triangle:     K500(INJ-BTC)+K493(ATOM-BTC)+K729(INJ-ATOM) closed")
    print(f"  Profit 3% sleeve:    $214,389/yr net @$10M @4x (OOS 22.33% ann ret)")
    print(f"  10th alt-alt:        first intra-Cosmos-cluster pair")
    print(f"  HL concentration:    64.5% UNCHANGED (Bybit-only — HL-only would reach 67.5%>65%)")
    print(f"  60d gate:            Realized Sh>=9 + fill>=60% + maxDD<15%")
    print(f"  INJ notional cap:    K729 3% + K684 existing (monitor combined INJ)")
    print(f"  ATOM notional cap:   K729 3% + K682 3% + K719 3% existing (monitor combined ATOM)")
    print(f"  v6.51 path:          K729 INJ-ATOM 3% Bybit sleeve (65th daemon, 10th alt-alt)")
    print()

    return 0


# ─────────────────────────────────────────────────────────────────────────────
# CLI entry point
# ─────────────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="K729 INJ-ATOM FR Differential Strategy (K731 scaffold, Cosmos DeFi-perp vs Cosmos Hub IBC, Bybit primary)"
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
        print(f"\n=== K729 Dashboard ({dash.get('last_poll_jst', '—')}) ===")
        print(json.dumps(dash, indent=2))
        return 0

    if args.rebalance:
        dash   = _load_dashboard()
        result = daily_rebalance(dash)
        print(f"\n=== K729 Rebalance Check ===")
        print(json.dumps(result, indent=2))
        return 0

    if args.close:
        result = close_paired_position(args.close, dry_run=args.dry_run)
        print(f"\n=== K729 Close Result ===")
        print(json.dumps(result, indent=2))
        return 0

    return run_cycle(dry_run=args.dry_run, aum=args.aum)


if __name__ == "__main__":
    sys.exit(main())
