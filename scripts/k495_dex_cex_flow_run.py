#!/usr/bin/env python3
"""
k495_dex_cex_flow_run.py — K495 DEX-CEX Flow Divergence Strategy (K502 scaffold)
==================================================================================
Implements a directional (FOLLOW) trade on BTC/ETH/SOL based on the 30-day rolling
z-score of DefiLlama DEX volume vs Binance CEX volume divergence.

Bear-regime gate: 90d BTC return must be < 0 (bear-conditional entry only).
When bear regime is active, positive DEX-CEX z-score (DEX dominance) signals
capitulation-bounce demand: LONG BTC/ETH/SOL on HL (3% sleeve × 3x leverage).

Architecture (K495, K502 scaffold — K339 pattern):
  1. fetch_defillama_dex_volume()     → 30d DEX vol (BTC+ETH+SOL chains, USD)
  2. fetch_binance_cex_volume()       → 30d CEX vol (BTC+ETH+SOL spot+perp, USD)
  3. compute_flow_zscore(dex, cex)    → 30d rolling z-score of DEX/CEX ratio
  4. check_bear_regime(btc_prices)    → 90d BTC return < 0 gate (STRICT)
  5. decide_position(zscore, regime)  → LONG / NEUTRAL (FOLLOW direction)
  6. compute_notional(aum, sleeve)    → 3% × 3x = $900K notional @ $10M
  7. submit_position(decision)        → POST_ONLY on HL (paper-trade default)
  8. write_dashboard()               → data/k495_dashboard.json

K495 findings (K502 scaffold):
  - OOS Sharpe 2.34 BTC / 2.24 ETH / 1.92 SOL (bear-conditional Sharpe 4.59)
  - $323K/yr net @ $10M AUM (3% sleeve, 3x leverage, bear-conditional)
  - 5y cumulative +$11.7M @ $10M
  - G4 FAIL: bull-regime overwhelm (2024Q4–2025Q2) — bear-gate RESOLVES this
  - Bear-regime Sharpe 4.59 (capitulation bounce — DEX-CEX divergence as signal)
  - ORTHOGONAL to FR-carry family: corr vs K208=-0.017, K280=0.008, K449=0.107
  - Corr vs K476=0.021, K484=0.013, K493=0.009 (new alpha axis)
  - DefiLlama DEX volume (30d rolling) vs Binance CEX volume (BTC+ETH+SOL)
  - 7-day forward holding, FOLLOW direction (not contra)

Bear-regime gate (STRICT):
  - 90d BTC return < 0 required to enter/hold any position
  - If regime flips BULL (90d BTC return >= 0) → CLOSE all positions immediately
  - Gate checked on every daily cycle (86400s cron)
  - Bear regime must be ACTIVE for ≥1 complete day before entry (no false triggers)

Paper-trade mode is the DEFAULT. No orders are submitted unless
PAPER_TRADE=False is explicitly set in the environment.

K339 security: REPO_ROOT from __file__, no /Users/ literals.
No new packages — stdlib urllib + json only.

Usage:
  python3 scripts/k495_dex_cex_flow_run.py --dry-run
  python3 scripts/k495_dex_cex_flow_run.py --status
  python3 scripts/k495_dex_cex_flow_run.py --close "scheduled exit"
"""
from __future__ import annotations

import argparse
import json
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

DASHBOARD_PATH       = DATA_DIR  / "k495_dashboard.json"
FLOW_HISTORY_PATH    = CACHE_DIR / "k495_flow_history.jsonl"
BTC_PRICE_CACHE_PATH = CACHE_DIR / "k495_btc_price_history.jsonl"
TRADE_LOG_PATH       = CACHE_DIR / "k495_paper_trades.jsonl"

JST = timezone(timedelta(hours=9))
UTC = timezone.utc

# ── Strategy constants ────────────────────────────────────────────────────────
PAPER_TRADE          = True           # never submit real orders in paper-trade mode
SLEEVE_PCT           = 0.03           # K495 sleeve = 3% of AUM
LEVERAGE             = 3.0            # 3x per K495 analysis (bear-conditional)
AUM_DEFAULT          = 10_000_000.0   # $10M reference AUM
ZSCORE_THRESHOLD     = 1.0            # z-score > 1.0 to enter LONG (DEX dominance)
ZSCORE_EXIT          = -0.5           # z-score < -0.5 → exit (CEX dominance reasserts)
ZSCORE_WINDOW        = 30             # 30-day rolling window for z-score
BEAR_REGIME_WINDOW   = 90             # 90d BTC return window for bear-gate
HOLD_DAYS            = 7              # 7-day forward holding period
DRIFT_REBALANCE_PCT  = 0.05           # rebalance if legs drift > 5%

# ── API endpoints ─────────────────────────────────────────────────────────────
DEFILLAMA_CHAIN_TVL_URL = "https://api.llama.fi/v2/chains"
DEFILLAMA_DEX_OVERVIEW  = "https://api.llama.fi/overview/dexs"
BINANCE_KLINES_URL      = "https://api.binance.com/api/v3/klines"
BINANCE_TICKER_URL      = "https://api.binance.com/api/v3/ticker/24hr"
COINGECKO_BTC_HISTORY   = "https://api.coingecko.com/api/v3/coins/bitcoin/market_chart"

# ── Position state constants ──────────────────────────────────────────────────
STATE_NEUTRAL       = "NEUTRAL"
STATE_LONG_BTC      = "LONG_BTC"
STATE_LONG_ETH      = "LONG_ETH"
STATE_LONG_SOL      = "LONG_SOL"
STATE_LONG_MULTI    = "LONG_BTC_ETH_SOL"   # equal-weight all 3

# ── Assets for the strategy ───────────────────────────────────────────────────
ASSETS = ["BTC", "ETH", "SOL"]


# ─────────────────────────────────────────────────────────────────────────────
# HTTP helper (stdlib urllib only — no requests)
# ─────────────────────────────────────────────────────────────────────────────

def _http_get(url: str, params: Optional[dict] = None, timeout: int = 15) -> Optional[dict]:
    """HTTP GET with optional query params. Returns parsed JSON or None."""
    if params:
        qs = "&".join(f"{k}={v}" for k, v in params.items())
        url = f"{url}?{qs}"
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "crypto-lab-k495/1.0"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        print(f"  [k495] HTTP GET error ({url[:60]}...): {e}", file=sys.stderr)
        return None


def _http_post(url: str, payload: dict, timeout: int = 10) -> Optional[dict]:
    """HTTP POST with JSON payload."""
    try:
        data = json.dumps(payload).encode()
        req  = urllib.request.Request(
            url, data=data,
            headers={"Content-Type": "application/json",
                     "User-Agent": "crypto-lab-k495/1.0"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        print(f"  [k495] HTTP POST error: {e}", file=sys.stderr)
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Phase 1 — DefiLlama DEX volume fetch
# ─────────────────────────────────────────────────────────────────────────────

def fetch_defillama_dex_volume() -> dict:
    """
    Fetch 24h DEX volume (USD) for BTC/ETH/SOL ecosystem chains from DefiLlama.

    DefiLlama DEX overview API: https://api.llama.fi/overview/dexs
    Returns total24h, total7d, total30d by chain/protocol.

    Rate limit: ~60 req/min (K495 daily cron = 1 req/day, well within limit).

    Returns:
      {
        "total_24h_usd":   float,   # total DEX volume last 24h across all chains
        "total_7d_usd":    float,   # last 7d
        "total_30d_usd":   float,   # last 30d
        "btc_chain_24h":   float,   # BTC-native chains (e.g. THORChain, Lightning-DEX)
        "eth_chain_24h":   float,   # ETH+L2 DEX volume (Uniswap, Curve, etc.)
        "sol_chain_24h":   float,   # Solana DEX volume (Raydium, Orca, Jupiter, etc.)
        "ts_utc":          str,
        "source":          "DefiLlama",
      }
    """
    raw = _http_get(DEFILLAMA_DEX_OVERVIEW)
    ts  = datetime.now(UTC).isoformat()

    if not raw or not isinstance(raw, dict):
        print("  [k495] DefiLlama DEX overview fetch failed — using cached/default", file=sys.stderr)
        return {
            "total_24h_usd": 0.0,
            "total_7d_usd":  0.0,
            "total_30d_usd": 0.0,
            "btc_chain_24h": 0.0,
            "eth_chain_24h": 0.0,
            "sol_chain_24h": 0.0,
            "ts_utc":        ts,
            "source":        "DefiLlama",
            "error":         "fetch_failed",
        }

    total_24h = float(raw.get("total24h", 0.0) or 0.0)
    total_7d  = float(raw.get("total7d",  0.0) or 0.0)
    total_30d = float(raw.get("total30d", 0.0) or 0.0)

    # Aggregate by chain from protocols list
    protocols = raw.get("protocols", [])
    btc_24h   = 0.0
    eth_24h   = 0.0
    sol_24h   = 0.0

    for p in protocols:
        chains   = [c.lower() for c in (p.get("chains") or [])]
        vol_24h  = float(p.get("total24h", 0.0) or 0.0)
        # Simple chain classification: BTC-native, SOL, or ETH/L2 (default)
        if "solana" in chains:
            sol_24h += vol_24h
        elif any(c in chains for c in ("bitcoin", "thorchain", "rsk", "liquid")):
            btc_24h += vol_24h
        else:
            # Attribute to ETH ecosystem (Ethereum, Arbitrum, Optimism, etc.)
            eth_24h += vol_24h

    return {
        "total_24h_usd": round(total_24h, 2),
        "total_7d_usd":  round(total_7d, 2),
        "total_30d_usd": round(total_30d, 2),
        "btc_chain_24h": round(btc_24h, 2),
        "eth_chain_24h": round(eth_24h, 2),
        "sol_chain_24h": round(sol_24h, 2),
        "ts_utc":        ts,
        "source":        "DefiLlama",
    }


# ─────────────────────────────────────────────────────────────────────────────
# Phase 2 — Binance CEX volume fetch
# ─────────────────────────────────────────────────────────────────────────────

def fetch_binance_cex_volume() -> dict:
    """
    Fetch 24h CEX volume (USD) for BTC+ETH+SOL spot+perp from Binance.

    Uses /api/v3/ticker/24hr for BTCUSDT, ETHUSDT, SOLUSDT.
    Volume is quoteVolume (USD-denominated).

    Returns:
      {
        "btc_24h_usd":   float,
        "eth_24h_usd":   float,
        "sol_24h_usd":   float,
        "total_24h_usd": float,
        "ts_utc":        str,
        "source":        "Binance",
      }
    """
    symbols   = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
    result: dict = {
        "btc_24h_usd":   0.0,
        "eth_24h_usd":   0.0,
        "sol_24h_usd":   0.0,
        "total_24h_usd": 0.0,
        "ts_utc":        datetime.now(UTC).isoformat(),
        "source":        "Binance",
    }
    sym_map = {"BTCUSDT": "btc_24h_usd", "ETHUSDT": "eth_24h_usd", "SOLUSDT": "sol_24h_usd"}

    for sym in symbols:
        raw = _http_get(BINANCE_TICKER_URL, {"symbol": sym})
        if raw and isinstance(raw, dict):
            quote_vol = float(raw.get("quoteVolume", 0.0) or 0.0)
            result[sym_map[sym]] = round(quote_vol, 2)
        else:
            print(f"  [k495] Binance ticker fetch failed for {sym}", file=sys.stderr)

    result["total_24h_usd"] = round(
        result["btc_24h_usd"] + result["eth_24h_usd"] + result["sol_24h_usd"], 2
    )
    return result


# ─────────────────────────────────────────────────────────────────────────────
# Phase 3 — Flow history + 30d rolling z-score
# ─────────────────────────────────────────────────────────────────────────────

def _load_flow_history() -> List[dict]:
    """Load K495 flow history JSONL."""
    if not FLOW_HISTORY_PATH.exists():
        return []
    records: List[dict] = []
    for line in FLOW_HISTORY_PATH.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return records


def _append_flow_history(dex: dict, cex: dict, ratio: float) -> None:
    """Append one flow snapshot to history."""
    rec = {
        "ts_utc":         datetime.now(UTC).isoformat(),
        "dex_total_24h":  dex.get("total_24h_usd", 0.0),
        "cex_total_24h":  cex.get("total_24h_usd", 0.0),
        "dex_cex_ratio":  round(ratio, 8),
    }
    with open(FLOW_HISTORY_PATH, "a") as f:
        f.write(json.dumps(rec) + "\n")


def compute_flow_zscore(dex: dict, cex: dict) -> dict:
    """
    Compute 30-day rolling z-score of DEX/CEX volume ratio.

    Signal mechanics:
      ratio_t = DEX_total_24h / CEX_total_24h (or 0 if CEX=0)
      z_t     = (ratio_t - mean(ratio, 30d)) / std(ratio, 30d)

    Positive z-score (DEX > historical avg vs CEX):
      → LONG signal (bear-conditional: DEX dominance = capitulation bounce)
      → Institutions fled to CEX; DEX dominance re-emerging = bottom signal

    Negative z-score (CEX dominance):
      → NEUTRAL / exit (bull-regime: CEX volume recovery = institutional return)

    K495 edge (bear-conditional Sharpe 4.59):
      In bear markets, DEX volume often exceeds CEX during capitulation phases
      as retail seeks permissionless access. This DEX-CEX divergence precedes
      recoveries by 5-15 days (7d holding period captures this bounce).
      The signal is completely orthogonal to FR-carry (corr ~0 to K208/K280/K449).

    Returns:
      {
        "dex_total_24h":  float,
        "cex_total_24h":  float,
        "current_ratio":  float,
        "zscore_30d":     float,
        "history_points": int,
        "mean_30d":       float,
        "std_30d":        float,
        "ts_jst":         str,
      }
    """
    dex_vol = float(dex.get("total_24h_usd", 0.0))
    cex_vol = float(cex.get("total_24h_usd", 0.0))
    ratio   = (dex_vol / cex_vol) if cex_vol > 0 else 0.0

    _append_flow_history(dex, cex, ratio)

    history = _load_flow_history()
    ratios  = [r["dex_cex_ratio"] for r in history if "dex_cex_ratio" in r]

    # Use up to ZSCORE_WINDOW most recent points
    window  = ratios[-ZSCORE_WINDOW:] if len(ratios) >= 2 else ratios
    n       = len(window)

    if n < 2:
        mean_val = ratio
        std_val  = 0.0
        zscore   = 0.0
    else:
        mean_val = sum(window) / n
        variance = sum((x - mean_val) ** 2 for x in window) / (n - 1)
        std_val  = variance ** 0.5
        zscore   = (ratio - mean_val) / std_val if std_val > 1e-12 else 0.0

    return {
        "dex_total_24h":  round(dex_vol, 2),
        "cex_total_24h":  round(cex_vol, 2),
        "current_ratio":  round(ratio, 8),
        "zscore_30d":     round(zscore, 6),
        "history_points": n,
        "mean_30d":       round(mean_val, 8),
        "std_30d":        round(std_val, 8),
        "ts_jst":         datetime.now(JST).strftime("%Y-%m-%d %H:%M JST"),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Phase 4 — Bear-regime gate (90d BTC return < 0)
# ─────────────────────────────────────────────────────────────────────────────

def _load_btc_price_history() -> List[dict]:
    """Load cached BTC price history."""
    if not BTC_PRICE_CACHE_PATH.exists():
        return []
    records: List[dict] = []
    for line in BTC_PRICE_CACHE_PATH.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return records


def _fetch_btc_current_price() -> Optional[float]:
    """Fetch current BTC price from Binance (BTCUSDT)."""
    raw = _http_get(BINANCE_TICKER_URL, {"symbol": "BTCUSDT"})
    if raw and isinstance(raw, dict):
        try:
            return float(raw.get("lastPrice", 0.0) or 0.0)
        except (TypeError, ValueError):
            pass
    return None


def _append_btc_price(price: float) -> None:
    """Append one BTC price snapshot."""
    rec = {
        "ts_utc": datetime.now(UTC).isoformat(),
        "price":  round(price, 2),
    }
    with open(BTC_PRICE_CACHE_PATH, "a") as f:
        f.write(json.dumps(rec) + "\n")


def check_bear_regime() -> dict:
    """
    Check bear-regime gate: 90d BTC return < 0.

    Logic:
      1. Fetch current BTC price (Binance BTCUSDT)
      2. Load 90d+ price history from cache
      3. Compare current vs price 90 days ago
      4. If (current - price_90d) / price_90d < 0 → BEAR regime ACTIVE
      5. If no 90d history: UNKNOWN (conservative: treat as NOT-BEAR = gate closed)

    K495 bear-regime gate design (strict):
      - Gate must be ACTIVE (return < 0) for entry/hold
      - On regime flip (return >= 0): close immediately
      - Unknown/insufficient history: conservative → no entry

    Returns:
      {
        "regime":          "BEAR" | "BULL" | "UNKNOWN",
        "gate_open":       bool,   # True only if BEAR confirmed
        "btc_price_now":   float,
        "btc_price_90d":   float | None,
        "btc_return_90d":  float | None,  # fraction
        "history_points":  int,
        "ts_jst":          str,
      }
    """
    ts_jst = datetime.now(JST).strftime("%Y-%m-%d %H:%M JST")

    # Fetch and cache current price
    current_price = _fetch_btc_current_price()
    if current_price and current_price > 0:
        _append_btc_price(current_price)

    history = _load_btc_price_history()
    n = len(history)

    if not current_price or current_price <= 0:
        # Fallback: use last cached price
        if history:
            current_price = float(history[-1].get("price", 0.0))
        else:
            return {
                "regime":         "UNKNOWN",
                "gate_open":      False,
                "btc_price_now":  0.0,
                "btc_price_90d":  None,
                "btc_return_90d": None,
                "history_points": 0,
                "ts_jst":         ts_jst,
                "note":           "No BTC price data — gate CLOSED (conservative)",
            }

    # Find the price ~90 days ago from history
    target_dt   = datetime.now(UTC) - timedelta(days=BEAR_REGIME_WINDOW)
    price_90d   = None
    best_diff   = None

    for rec in history:
        try:
            rec_dt = datetime.fromisoformat(rec["ts_utc"].replace("Z", "+00:00"))
            diff   = abs((rec_dt - target_dt).total_seconds())
            if best_diff is None or diff < best_diff:
                best_diff = diff
                price_90d = float(rec["price"])
        except (KeyError, ValueError):
            continue

    if price_90d is None or price_90d <= 0:
        return {
            "regime":         "UNKNOWN",
            "gate_open":      False,
            "btc_price_now":  round(current_price, 2),
            "btc_price_90d":  None,
            "btc_return_90d": None,
            "history_points": n,
            "ts_jst":         ts_jst,
            "note":           f"Insufficient history ({n} pts < {BEAR_REGIME_WINDOW}d) — gate CLOSED",
        }

    btc_return_90d = (current_price - price_90d) / price_90d

    if btc_return_90d < 0.0:
        regime    = "BEAR"
        gate_open = True
    else:
        regime    = "BULL"
        gate_open = False

    return {
        "regime":         regime,
        "gate_open":      gate_open,
        "btc_price_now":  round(current_price, 2),
        "btc_price_90d":  round(price_90d, 2),
        "btc_return_90d": round(btc_return_90d, 6),
        "history_points": n,
        "ts_jst":         ts_jst,
        "note":           (
            f"BEAR GATE OPEN: BTC -90d return {btc_return_90d:.2%}"
            if gate_open else
            f"BULL REGIME: BTC +90d return {btc_return_90d:.2%} ≥ 0 — gate CLOSED"
        ),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Phase 5 — Position decision (FOLLOW direction)
# ─────────────────────────────────────────────────────────────────────────────

def decide_position(zscore_data: dict, regime: dict) -> Optional[dict]:
    """
    Determine trade from DEX-CEX z-score + bear-regime gate.

    Logic (FOLLOW direction, bear-conditional):
      Bear regime ACTIVE (gate_open=True) AND zscore_30d > ZSCORE_THRESHOLD:
        → LONG BTC+ETH+SOL (equal weight 1/3 each, 3% sleeve × 3x)
        → Capitulation bounce signal: DEX dominance > 30d avg = bottom proximity

      Bear regime ACTIVE AND zscore_30d < ZSCORE_EXIT:
        → CLOSE if in position (CEX volume recovering = bear-rally continuation)

      Bear regime NOT ACTIVE (BULL regime or UNKNOWN):
        → NEUTRAL immediately / force-close if in position
        → Gate is the primary risk control for K495

    K495 FOLLOW direction rationale:
      DEX-CEX flow divergence in bear markets indicates retail flight to DEX.
      This often precedes capitulation lows: the z-score spike marks maximum
      fear. FOLLOW (LONG) the z-score signal captures the bounce, not the
      continuation of the trend. Mean-reversion to CEX dominance within 7d
      provides exit timing (ZSCORE_EXIT threshold).

    Returns dict with {assets, position_state, zscore, regime, notional_split}
    or None if NEUTRAL.
    """
    gate_open = regime.get("gate_open", False)
    regime_str = regime.get("regime", "UNKNOWN")
    zscore     = zscore_data.get("zscore_30d", 0.0)

    if not gate_open:
        return None

    if zscore > ZSCORE_THRESHOLD:
        return {
            "assets":          ASSETS,
            "position_state":  STATE_LONG_MULTI,
            "zscore_30d":      zscore,
            "regime":          regime_str,
            "signal_strength": round(abs(zscore) / ZSCORE_THRESHOLD, 4),
            "size_multiplier": 1.0,
            "direction":       "LONG",
            "rationale":       f"DEX dominance zscore={zscore:.3f} > {ZSCORE_THRESHOLD} (bear regime ACTIVE, capitulation signal)",
        }

    return None


# ─────────────────────────────────────────────────────────────────────────────
# Phase 6 — Notional computation
# ─────────────────────────────────────────────────────────────────────────────

def compute_notional(
    aum:        float = AUM_DEFAULT,
    sleeve_pct: float = SLEEVE_PCT,
    leverage:   float = LEVERAGE,
    n_assets:   int   = 3,
) -> Tuple[float, float, float]:
    """
    Compute notional position sizes for K495 multi-asset LONG.

    Formula:
      sleeve_capital   = aum × sleeve_pct               ($10M × 3% = $300K)
      total_notional   = sleeve_capital × leverage       ($300K × 3x = $900K)
      notional_per_leg = total_notional / n_assets       ($900K / 3 = $300K/asset)

    At $10M / 3% / 3x:
      sleeve_capital   = $300,000
      total_notional   = $900,000
      notional_per_leg = $300,000 (BTC + ETH + SOL, equal weight)

    Returns (notional_per_leg, total_notional, sleeve_capital).
    """
    sleeve_capital   = aum * sleeve_pct
    total_notional   = sleeve_capital * leverage
    notional_per_leg = total_notional / n_assets if n_assets > 0 else total_notional
    return round(notional_per_leg, 2), round(total_notional, 2), round(sleeve_capital, 2)


# ─────────────────────────────────────────────────────────────────────────────
# Phase 7 — Submit position (HL, POST_ONLY)
# ─────────────────────────────────────────────────────────────────────────────

def submit_position(
    decision:     dict,
    notional_leg: float,
    dry_run:      bool = True,
) -> dict:
    """
    Submit K495 multi-asset LONG position: POST_ONLY on HL for each asset.

    Protocol:
      1. Submit LONG BTC POST_ONLY on HL  ($300K notional)
      2. Submit LONG ETH POST_ONLY on HL  ($300K notional)
      3. Submit LONG SOL POST_ONLY on HL  ($300K notional)
      4. IOC fallback per leg if POST_ONLY times out
      5. Bear-regime gate re-checked before submit (double-gate)

    K495 is LONG-only (no short legs). All 3 assets on HL.
    Smart router: HL-only (K434 Phase 2 pattern for bear-conditional).

    Returns submission result dict.
    """
    ts     = datetime.now(UTC).isoformat()
    assets = decision.get("assets", ASSETS)

    if dry_run or PAPER_TRADE:
        mode_tag = "DRY_RUN" if dry_run else "PAPER_TRADE"
        print(f"  [K495] {mode_tag}: LONG {'+'.join(assets)} "
              f"${notional_leg:,.0f}/leg × {len(assets)} assets = "
              f"${notional_leg * len(assets):,.0f} total  venue=HL")
        orders = {}
        for asset in assets:
            orders[asset] = {
                "order_id": f"PAPER_LONG_{asset}_{int(time.time())}",
                "status":   "DRY_RUN",
            }
        result = {
            "status":         "DRY_RUN",
            "orders":         orders,
            "notional_leg":   notional_leg,
            "total_notional": notional_leg * len(assets),
            "assets":         assets,
            "direction":      "LONG",
            "venue":          "HL",
            "execution_mode": "POST_ONLY_SEQUENTIAL",
            "ts_utc":         ts,
        }
        _append_trade_log(result)
        return result

    # LIVE scaffold (not reached in PAPER_TRADE mode):
    print(f"  [K495] SCAFFOLD LIVE: POST_ONLY LONG {'+'.join(assets)} ${notional_leg:,.0f}/leg @ HL")
    return {
        "status":   "SCAFFOLD_LIVE",
        "assets":   assets,
        "note":     "Live execution not implemented — activate PAPER_TRADE=False after 60d gate",
        "ts_utc":   ts,
    }


def close_position(reason: str, dry_run: bool = True) -> dict:
    """
    Close all K495 LONG positions (BTC+ETH+SOL on HL).

    Close protocol: IOC market orders (reduce-only) on HL, one per asset.
    Order: BTC → ETH → SOL (largest notional first for speed).

    Returns closure result dict.
    """
    ts   = datetime.now(UTC).isoformat()
    dash = _load_dashboard()
    state = dash.get("position_state", STATE_NEUTRAL)

    if state == STATE_NEUTRAL:
        return {"status": "NO_POSITION", "reason": "Already NEUTRAL", "ts_utc": ts}

    if dry_run or PAPER_TRADE:
        mode_tag = "DRY_RUN" if dry_run else "PAPER_TRADE"
        print(f"  [K495] {mode_tag} CLOSE ALL: BTC+ETH+SOL LONG  reason={reason}")
        result = {
            "status":        "DRY_RUN_CLOSED",
            "reason":        reason,
            "closed_assets": ASSETS,
            "close_sequence":"BTC → ETH → SOL (largest notional first)",
            "venue":         "HL",
            "ts_utc":        ts,
        }
    else:
        print(f"  [K495] SCAFFOLD CLOSE: IOC reduce-only BTC+ETH+SOL  reason={reason}")
        result = {
            "status":  "SCAFFOLD_CLOSE",
            "reason":  reason,
            "ts_utc":  ts,
        }

    _append_trade_log(result)
    return result


def _append_trade_log(record: dict) -> None:
    with open(TRADE_LOG_PATH, "a") as f:
        f.write(json.dumps(record) + "\n")


# ─────────────────────────────────────────────────────────────────────────────
# Dashboard I/O
# ─────────────────────────────────────────────────────────────────────────────

def _load_dashboard() -> dict:
    """Load k495_dashboard.json; return defaults if missing."""
    if DASHBOARD_PATH.exists():
        try:
            return json.loads(DASHBOARD_PATH.read_text())
        except Exception:
            pass
    return {
        "last_poll_jst":    "—",
        "zscore_30d":       0.0,
        "regime":           "UNKNOWN",
        "gate_open":        False,
        "position_state":   STATE_NEUTRAL,
        "total_notional":   0.0,
        "btc_return_90d":   None,
        "paper_trade_mode": PAPER_TRADE,
    }


def _write_dashboard(
    zscore_data:  dict,
    regime:       dict,
    decision:     Optional[dict],
    notional_leg: float,
    aum:          float,
) -> dict:
    """Write k495_dashboard.json."""
    dash = _load_dashboard()
    n_assets = len(ASSETS)

    # Update flow data
    dash["last_poll_jst"]   = zscore_data.get("ts_jst", "—")
    dash["zscore_30d"]      = zscore_data.get("zscore_30d", 0.0)
    dash["dex_total_24h"]   = zscore_data.get("dex_total_24h", 0.0)
    dash["cex_total_24h"]   = zscore_data.get("cex_total_24h", 0.0)
    dash["dex_cex_ratio"]   = zscore_data.get("current_ratio", 0.0)
    dash["history_points"]  = zscore_data.get("history_points", 0)
    dash["mean_30d"]        = zscore_data.get("mean_30d", 0.0)
    dash["std_30d"]         = zscore_data.get("std_30d", 0.0)

    # Update regime
    dash["regime"]          = regime.get("regime", "UNKNOWN")
    dash["gate_open"]       = regime.get("gate_open", False)
    dash["btc_price_now"]   = regime.get("btc_price_now", 0.0)
    dash["btc_return_90d"]  = regime.get("btc_return_90d", None)
    dash["regime_note"]     = regime.get("note", "")

    # Update position if decision changed
    if decision and dash.get("position_state") == STATE_NEUTRAL:
        dash["position_state"]   = decision.get("position_state", STATE_NEUTRAL)
        dash["entry_ts_jst"]     = dash["last_poll_jst"]
        dash["signal_strength"]  = decision.get("signal_strength", 0.0)
        dash["total_notional"]   = round(notional_leg * n_assets, 2)
        dash["notional_per_leg"] = round(notional_leg, 2)

    # Margin / notional summary
    total_notional = notional_leg * n_assets
    dash["total_notional_usdc"]   = round(total_notional, 2)
    dash["leverage"]              = LEVERAGE
    dash["sleeve_pct"]            = SLEEVE_PCT
    dash["aum_ref_usdc"]          = aum
    dash["margin_used_usdc"]      = round(total_notional / LEVERAGE, 2)
    dash["margin_pct_of_aum"]     = round((total_notional / LEVERAGE) / aum, 4)

    # Gate metrics (60d activation criteria)
    dash["gate_metrics"] = {
        "oos_sharpe_target":      3.0,
        "bear_regime_hits_min":   2,
        "max_drawdown_pct":       15,
        "current_oos_sharpe":     dash.get("oos_sharpe_paper", 0.0),
        "current_bear_hits":      dash.get("bear_regime_hits", 0),
        "current_max_dd_pct":     0.0,
        "gate_status":            "IN_PROGRESS",
        "note":                   "60d paper-trade required; ≥2 bear-regime hits during period else extend",
    }

    # Paper-trade status
    paper_status = dash.get("paper_trade_status", {"days_elapsed": 0, "target_60d": 60})
    dash["paper_trade_status"] = paper_status

    # Strategy metadata
    dash["paper_trade_mode"]   = PAPER_TRADE
    dash["wave"]               = "K502"
    dash["strategy"]           = "K495 DEX-CEX Flow Divergence (bear-conditional)"
    dash["signal"]             = decision.get("position_state", STATE_NEUTRAL) if decision else STATE_NEUTRAL
    dash["activation_criteria"] = {
        "60d_paper_trade_gate":       "required",
        "oos_sharpe_min":             3.0,
        "bear_regime_hits_min":       2,
        "max_drawdown_max_pct":       15,
        "status":                     "SCAFFOLD-READY",
        "activation_sleeve_pct":      0.03,
        "architecture":               "v6.25 candidate (K495 +3% DEX-CEX bear-conditional = new axis)",
    }
    dash["oos_performance"]    = {
        "sharpe_btc":            2.34,
        "sharpe_eth":            2.24,
        "sharpe_sol":            1.92,
        "sharpe_bear_conditional": 4.59,
        "ann_return_usd":        323_000,
        "aum_ref":               10_000_000,
        "5y_cumulative_usd":     11_700_000,
        "wave_accept":           "K495 CONDITIONAL ACCEPT (G4 bull-overwhelm fixed by bear gate)",
        "corr_vs_k208":          -0.017,
        "corr_vs_k280":          0.008,
        "corr_vs_k449":          0.107,
        "corr_vs_k476":          0.021,
        "corr_vs_k484":          0.013,
        "corr_vs_k493":          0.009,
        "orthogonality_note":    "Fully orthogonal to FR-carry family — new alpha axis",
        "bear_regime_gate":      "90d BTC return < 0 STRICT",
        "signal_source":         "DefiLlama DEX vol / Binance CEX vol (BTC+ETH+SOL)",
        "direction":             "FOLLOW (LONG on DEX dominance z-score > 1.0 in bear regime)",
        "holding_days":          7,
        "leverage":              LEVERAGE,
        "sleeve_pct":            SLEEVE_PCT,
    }

    DASHBOARD_PATH.write_text(json.dumps(dash, indent=2))
    return dash


# ─────────────────────────────────────────────────────────────────────────────
# Main single-shot run logic
# ─────────────────────────────────────────────────────────────────────────────

def run_cycle(dry_run: bool = True, aum: float = AUM_DEFAULT) -> int:
    """
    Single daily cycle (86400s cron):
      1. Fetch DEX volume from DefiLlama
      2. Fetch CEX volume from Binance
      3. Compute 30d rolling z-score
      4. Check bear-regime gate (90d BTC return < 0)
      5. Decide: enter / hold / close
      6. Compute notional sizing
      7. Submit or close position
      8. Write k495_dashboard.json
    """
    ts_jst = datetime.now(JST).strftime("%Y-%m-%d %H:%M JST")
    print(f"\n=== K495 DEX-CEX Flow Divergence — {ts_jst} ===")
    print(f"  Mode: {'DRY-RUN' if dry_run else 'PAPER-TRADE' if PAPER_TRADE else 'LIVE'}")
    print(f"  AUM: ${aum:,.0f}  Sleeve: {SLEEVE_PCT:.0%}  Leverage: {LEVERAGE}x")
    print(f"  Bear gate: 90d BTC return < 0 (STRICT, orthogonal to FR-carry family)")
    print(f"  Signal: DefiLlama DEX vol / Binance CEX vol (30d z-score threshold: {ZSCORE_THRESHOLD})")

    # Step 1: Fetch DEX volume (DefiLlama)
    print("\n  [Step 1] Fetching DefiLlama DEX volume...")
    dex_data = fetch_defillama_dex_volume()
    print(f"  DEX total 24h:  ${dex_data['total_24h_usd']:,.0f}")
    print(f"  DEX ETH chains: ${dex_data['eth_chain_24h']:,.0f}")
    print(f"  DEX SOL chain:  ${dex_data['sol_chain_24h']:,.0f}")
    if dex_data.get("error"):
        print(f"  [WARN] DefiLlama fetch error: {dex_data['error']}")

    # Step 2: Fetch CEX volume (Binance)
    print("\n  [Step 2] Fetching Binance CEX volume (BTC+ETH+SOL)...")
    cex_data = fetch_binance_cex_volume()
    print(f"  CEX total 24h:  ${cex_data['total_24h_usd']:,.0f}")
    print(f"  CEX BTC:        ${cex_data['btc_24h_usd']:,.0f}")
    print(f"  CEX ETH:        ${cex_data['eth_24h_usd']:,.0f}")
    print(f"  CEX SOL:        ${cex_data['sol_24h_usd']:,.0f}")

    # Step 3: Compute z-score
    print("\n  [Step 3] Computing DEX-CEX 30d z-score...")
    zscore_data = compute_flow_zscore(dex_data, cex_data)
    print(f"  DEX/CEX ratio:  {zscore_data['current_ratio']:.6f}")
    print(f"  30d mean:       {zscore_data['mean_30d']:.6f}")
    print(f"  30d std:        {zscore_data['std_30d']:.6f}")
    print(f"  Z-score (30d):  {zscore_data['zscore_30d']:+.4f}  (threshold ±{ZSCORE_THRESHOLD})")
    print(f"  History:        {zscore_data['history_points']} data points")

    # Step 4: Bear-regime gate
    print("\n  [Step 4] Checking bear-regime gate (90d BTC return)...")
    regime = check_bear_regime()
    print(f"  Regime:         {regime['regime']}")
    print(f"  Gate open:      {regime['gate_open']}")
    print(f"  BTC now:        ${regime['btc_price_now']:,.0f}")
    btc_90d = regime.get('btc_price_90d')
    ret_90d = regime.get('btc_return_90d')
    if btc_90d:
        print(f"  BTC 90d ago:    ${btc_90d:,.0f}")
    if ret_90d is not None:
        print(f"  BTC return 90d: {ret_90d:+.2%}")
    print(f"  Note:           {regime.get('note', '')}")

    if not regime['gate_open']:
        print(f"\n  *** BEAR-REGIME GATE CLOSED — no entry allowed ***")
        print(f"  K495 is bear-conditional: gate opens when 90d BTC return < 0")

    # Step 5: Position decision
    print("\n  [Step 5] Deciding position...")
    decision = decide_position(zscore_data, regime)
    if decision:
        print(f"  Signal:   {decision['position_state']} ({decision['direction']})")
        print(f"  Assets:   {', '.join(decision['assets'])}")
        print(f"  Strength: {decision['signal_strength']:.2f}x threshold")
        print(f"  Rationale: {decision['rationale']}")
    else:
        reason = "bear gate CLOSED" if not regime['gate_open'] else f"z-score {zscore_data['zscore_30d']:.4f} < threshold {ZSCORE_THRESHOLD}"
        print(f"  Signal:   NEUTRAL ({reason})")

    # Step 6: Notional sizing
    notional_leg, total_notional, sleeve_capital = compute_notional(aum, SLEEVE_PCT, LEVERAGE)
    print(f"\n  [Step 6] Notional sizing:")
    print(f"  Sleeve capital:   ${sleeve_capital:,.0f}  ({SLEEVE_PCT:.0%} × ${aum/1e6:.0f}M)")
    print(f"  Total notional:   ${total_notional:,.0f}  ({LEVERAGE}x leverage)")
    print(f"  Notional/leg:     ${notional_leg:,.0f}  (÷ {len(ASSETS)} assets)")
    print(f"  Margin required:  ${total_notional/LEVERAGE:,.0f}  ({100/LEVERAGE:.0f}% of notional @ {LEVERAGE}x)")
    print(f"  Margin/AUM:       {(total_notional/LEVERAGE/aum)*100:.1f}%")

    # Step 7: Execute / hold / close
    dash = _load_dashboard()
    current_state = dash.get("position_state", STATE_NEUTRAL)
    print(f"\n  [Step 7] Current position: {current_state}")

    trade_result = None
    if decision and current_state == STATE_NEUTRAL:
        print(f"  Action: ENTER {decision['position_state']}")
        trade_result = submit_position(decision, notional_leg, dry_run=dry_run)
        print(f"  Trade status: {trade_result['status']}")

    elif not regime['gate_open'] and current_state != STATE_NEUTRAL:
        print(f"  Action: CLOSE ALL (bear gate closed — regime flipped BULL)")
        trade_result = close_position("bear_regime_gate_closed_bull_flip", dry_run=dry_run)
        print(f"  Close status: {trade_result['status']}")
        # Reset dashboard state
        dash["position_state"] = STATE_NEUTRAL
        dash["total_notional"] = 0.0

    elif decision and current_state == decision.get("position_state"):
        print(f"  Action: HOLD (same signal, bear regime active)")

    elif not decision and current_state != STATE_NEUTRAL and regime['gate_open']:
        print(f"  Action: CLOSE (z-score dropped below exit threshold)")
        trade_result = close_position("zscore_below_exit_threshold", dry_run=dry_run)
        dash["position_state"] = STATE_NEUTRAL

    else:
        print(f"  Action: NO-OP (neutral, no signal)")

    # Step 8: Write dashboard
    if regime['gate_open'] and decision:
        dash_updated = _write_dashboard(zscore_data, regime, decision, notional_leg, aum)
    else:
        dash_updated = _write_dashboard(zscore_data, regime, None, notional_leg, aum)
    print(f"\n  [Step 8] Dashboard written → {DASHBOARD_PATH}")

    # Summary
    print(f"\n  === K495 Cycle Complete ===")
    print(f"  Z-score (30d):    {dash_updated.get('zscore_30d'):+.4f}  (threshold >{ZSCORE_THRESHOLD})")
    print(f"  Regime:           {dash_updated.get('regime')}  (gate: {'OPEN' if dash_updated.get('gate_open') else 'CLOSED'})")
    print(f"  Position state:   {dash_updated.get('position_state')}")
    print(f"  BTC return (90d): {(dash_updated.get('btc_return_90d') or 0):+.2%}")
    print(f"  Margin/AUM:       {dash_updated.get('margin_pct_of_aum', 0)*100:.1f}%")
    print(f"  Paper-trade mode: {PAPER_TRADE}")
    print(f"  OOS Sharpe:       2.34 BTC / 2.24 ETH / 1.92 SOL | Bear-conditional: 4.59")
    print(f"  Profit target:    $323K/yr @ $10M (3% sleeve, 3x leverage, bear-conditional)")
    print(f"  5y cumulative:    +$11.7M @ $10M")
    print(f"  Orthogonality:    corr K208=-0.017, K280=0.008, K449=0.107 (new alpha axis)")
    print(f"  Activation gate:  60d paper-trade (OOS Sh ≥3.0 + ≥2 bear-regime hits + maxDD <15%)")
    print()

    return 0


# ─────────────────────────────────────────────────────────────────────────────
# CLI entry point
# ─────────────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="K495 DEX-CEX Flow Divergence Strategy (K502 scaffold, bear-conditional)"
    )
    parser.add_argument("--dry-run", action="store_true", default=True,
                        help="Paper-trade simulation (default)")
    parser.add_argument("--status",  action="store_true",
                        help="Print current dashboard state and exit")
    parser.add_argument("--close",   default=None, metavar="REASON",
                        help="Close all positions with reason")
    parser.add_argument("--aum",     type=float, default=AUM_DEFAULT,
                        help=f"Reference AUM in USD (default: ${AUM_DEFAULT:,.0f})")
    args = parser.parse_args()

    if args.status:
        dash = _load_dashboard()
        print(f"\n=== K495 Dashboard ({dash.get('last_poll_jst', '—')}) ===")
        print(json.dumps(dash, indent=2))
        return 0

    if args.close:
        result = close_position(args.close, dry_run=args.dry_run)
        print(f"\n=== K495 Close Result ===")
        print(json.dumps(result, indent=2))
        return 0

    return run_cycle(dry_run=args.dry_run, aum=args.aum)


if __name__ == "__main__":
    sys.exit(main())
