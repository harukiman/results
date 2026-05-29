#!/usr/bin/env python3
"""
k457_basket_run.py — K457 BTC+ETH+SOL Multi-Asset Basket FR Carry
==================================================================
Implements a 3-asset simultaneous K208-style funding-rate carry basket.
Each asset is independently traded on HL vs Bybit:
  - long lower-FR venue, short higher-FR venue
  - Inv-vol weighting across assets (30d realized vol normalization)
  - DAR(2,1) signal gate per asset

Total: up to 6 legs simultaneously (3 longs + 3 shorts: BTC/ETH/SOL × 2 venues).

Architecture (K459 scaffold):
  1. fetch_per_asset_fr()        → HL + Bybit FR per asset
  2. compute_inv_vol_weights()   → 30d realized vol normalization
  3. apply_dar_filter()          → DAR(2,1) signal gate per asset
  4. decide_basket_position()    → per-asset long/short direction
  5. submit_basket_trade()       → 6-leg POST_ONLY execution + IOC fallback
  6. close_basket_position()     → 6-leg unwind (shorts first)

K457 findings (CONDITIONAL ACCEPT — K459 scaffold):
  - OOS Sharpe 19.58 (highest standalone; K457 = best FR basket wave)
  - 3-asset basket outperforms 2-asset by diversification + inv-vol weighting
  - 60d paper-trade gate required before v6.20 sleeve activation
  - Sleeve: 5% of AUM at v6.20 (if 60d OOS Sharpe ≥15 + fill_rate ≥65%)

Paper-trade mode is the DEFAULT.  No orders submitted unless PAPER_TRADE=False.

K339 security: REPO_ROOT from __file__, no /Users/ literals.
No new packages — stdlib urllib + json only.

Usage:
  python3 scripts/k457_basket_run.py --dry-run
  python3 scripts/k457_basket_run.py --status
  python3 scripts/k457_basket_run.py --rebalance
  python3 scripts/k457_basket_run.py --close "reason"
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

DASHBOARD_PATH   = DATA_DIR / "k457_basket_dashboard.json"
FR_HISTORY_PATH  = CACHE_DIR / "k457_basket_fr_history.jsonl"
TRADE_LOG_PATH   = CACHE_DIR / "k457_basket_paper_trades.jsonl"
VOL_CACHE_PATH   = CACHE_DIR / "k457_basket_vol_cache.jsonl"

JST = timezone(timedelta(hours=9))
UTC = timezone.utc

# ── Strategy constants ────────────────────────────────────────────────────────
PAPER_TRADE           = True              # never submit real orders in paper-trade mode
BASKET_SYMBOLS        = ["BTC", "ETH", "SOL"]
SLEEVE_PCT            = 0.05             # v6.20 activation target: 5% of AUM
LEVERAGE              = 4.0             # K457 leverage cap = 4x (matches K449)
AUM_DEFAULT           = 10_000_000.0    # $10M reference AUM
SIGNAL_THRESHOLD      = 0.00001         # FR spread must exceed this to enter
DAR_P                 = 2               # DAR(2,1) AR order p
DAR_Q                 = 1               # DAR(2,1) MA-like history window q
VOL_LOOKBACK_DAYS     = 30              # 30d realized vol for inv-vol weights
IOC_TIMEOUT_SEC       = 300             # 5-min POST_ONLY fill window
HL_API_URL            = "https://api.hyperliquid.xyz/info"
BYBIT_API_URL         = "https://api.bybit.com/v5/market/tickers"
HL_CAP_PCT            = 0.65            # K355: HL concentration cap ≤65%

# ── Position state constants ──────────────────────────────────────────────────
STATE_LONG_HL_SHORT_BYBIT   = "LONG_HL_SHORT_BYBIT"
STATE_LONG_BYBIT_SHORT_HL   = "LONG_BYBIT_SHORT_HL"
STATE_NEUTRAL               = "NEUTRAL"

# Bybit symbol map (API symbol format for perpetuals)
BYBIT_SYMBOL_MAP: Dict[str, str] = {
    "BTC": "BTCUSDT",
    "ETH": "ETHUSDT",
    "SOL": "SOLUSDT",
}


# ─────────────────────────────────────────────────────────────────────────────
# HTTP helper (stdlib urllib only — no requests)
# ─────────────────────────────────────────────────────────────────────────────

def _http_post(url: str, payload: dict, timeout: int = 10) -> Optional[dict]:
    try:
        data = json.dumps(payload).encode()
        req  = urllib.request.Request(
            url, data=data,
            headers={"Content-Type": "application/json",
                     "User-Agent": "crypto-lab-k457/1.0"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        print(f"  [k457] HTTP POST error: {e}", file=sys.stderr)
        return None


def _http_get(url: str, timeout: int = 10) -> Optional[dict]:
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "crypto-lab-k457/1.0"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        print(f"  [k457] HTTP GET error: {e}", file=sys.stderr)
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Phase 1 — Per-asset FR fetch (HL + Bybit)
# ─────────────────────────────────────────────────────────────────────────────

def _fetch_hl_fr_all() -> Dict[str, float]:
    """
    Fetch 8h funding rates for all basket symbols from HyperLiquid.
    Returns {symbol: fr_8h_fraction}.
    """
    raw = _http_post(HL_API_URL, {"type": "metaAndAssetCtxs"})
    if not raw or not isinstance(raw, list) or len(raw) < 2:
        print("  [k457] HL metaAndAssetCtxs fetch failed", file=sys.stderr)
        return {}
    meta       = raw[0]
    asset_ctxs = raw[1]
    universe   = {item["name"]: i for i, item in enumerate(meta.get("universe", []))}
    result: Dict[str, float] = {}
    for sym in BASKET_SYMBOLS:
        if sym not in universe:
            continue
        idx = universe[sym]
        ctx = asset_ctxs[idx]
        try:
            result[sym] = float(ctx.get("funding", 0.0))
        except (TypeError, ValueError):
            result[sym] = 0.0
    return result


def _fetch_bybit_fr_all() -> Dict[str, float]:
    """
    Fetch 8h funding rates for all basket symbols from Bybit.
    Returns {symbol: fr_8h_fraction}.

    Bybit v5 linear tickers endpoint returns fundingRate as a string.
    """
    result: Dict[str, float] = {}
    for sym in BASKET_SYMBOLS:
        bybit_sym = BYBIT_SYMBOL_MAP.get(sym, f"{sym}USDT")
        url = f"{BYBIT_API_URL}?category=linear&symbol={bybit_sym}"
        raw = _http_get(url, timeout=10)
        if not raw:
            continue
        try:
            items = raw.get("result", {}).get("list", [])
            if not items:
                continue
            fr_str = items[0].get("fundingRate", "0") or "0"
            result[sym] = float(fr_str)
        except (TypeError, ValueError, IndexError) as e:
            print(f"  [k457] Bybit FR parse error {sym}: {e}", file=sys.stderr)
            result[sym] = 0.0
    return result


def fetch_per_asset_fr(symbols: List[str] = None) -> Dict[str, Dict[str, float]]:
    """
    Fetch per-asset FR from HL and Bybit for the basket.

    Returns:
      {
        "BTC": {"hl": 0.00012, "bybit": 0.00010, "spread": 0.00002},
        "ETH": {"hl": ..., "bybit": ..., "spread": ...},
        "SOL": {"hl": ..., "bybit": ..., "spread": ...},
      }

    spread = HL FR − Bybit FR (positive → HL more expensive → long Bybit, short HL)
    """
    if symbols is None:
        symbols = BASKET_SYMBOLS

    hl_frs    = _fetch_hl_fr_all()
    bybit_frs = _fetch_bybit_fr_all()

    result: Dict[str, Dict[str, float]] = {}
    for sym in symbols:
        hl_fr    = hl_frs.get(sym, 0.0)
        bybit_fr = bybit_frs.get(sym, 0.0)
        spread   = hl_fr - bybit_fr  # positive → HL more expensive
        result[sym] = {
            "hl":     round(hl_fr, 10),
            "bybit":  round(bybit_fr, 10),
            "spread": round(spread, 10),
        }

    ts = datetime.now(UTC).isoformat()
    # Append to history
    rec = {"ts_utc": ts, "fr": result}
    with open(FR_HISTORY_PATH, "a") as f:
        f.write(json.dumps(rec) + "\n")

    return result


# ─────────────────────────────────────────────────────────────────────────────
# Phase 2 — Inv-vol weights (30d realized vol normalization)
# ─────────────────────────────────────────────────────────────────────────────

def _load_fr_history(lookback_days: int = VOL_LOOKBACK_DAYS) -> List[dict]:
    """Load FR history JSONL, filtered to lookback window."""
    if not FR_HISTORY_PATH.exists():
        return []
    cutoff_utc = datetime.now(UTC) - timedelta(days=lookback_days)
    records: List[dict] = []
    for line in FR_HISTORY_PATH.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
            # Filter to lookback window
            ts_str = rec.get("ts_utc", "")
            if ts_str:
                try:
                    ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                    if ts < cutoff_utc:
                        continue
                except ValueError:
                    pass
            records.append(rec)
        except json.JSONDecodeError:
            continue
    return records


def compute_inv_vol_weights(symbols: List[str] = None) -> Dict[str, float]:
    """
    Compute inverse-volatility weights across basket assets.

    Method:
      1. Load 30d FR spread history per asset
      2. Compute realized std of spread per asset (proxy for vol)
      3. inv_vol_weight_i = (1/vol_i) / sum(1/vol_j for all j)
      4. If insufficient history (< 3 points): use equal weights

    Returns:
      {"BTC": 0.369, "ETH": 0.357, "SOL": 0.274}  (sum = 1.0)

    Rationale: Lower-vol assets receive larger weight, reducing basket variance.
    This is consistent with K208 DAR(2,1) inv-vol sizing philosophy.
    """
    if symbols is None:
        symbols = BASKET_SYMBOLS

    history = _load_fr_history(VOL_LOOKBACK_DAYS)

    # Build per-asset spread series
    spreads: Dict[str, List[float]] = {sym: [] for sym in symbols}
    for rec in history:
        fr_data = rec.get("fr", {})
        for sym in symbols:
            sp = fr_data.get(sym, {}).get("spread", None)
            if sp is not None:
                spreads[sym].append(sp)

    # Compute realized std per asset
    vols: Dict[str, float] = {}
    for sym in symbols:
        series = spreads[sym]
        if len(series) < 3:
            # Fallback: use representative crypto vol as proxy
            fallback_vol = {"BTC": 0.00015, "ETH": 0.00018, "SOL": 0.00022}.get(sym, 0.00018)
            vols[sym] = fallback_vol
        else:
            n    = len(series)
            mean = sum(series) / n
            var  = sum((x - mean) ** 2 for x in series) / (n - 1)
            vols[sym] = math.sqrt(var) if var > 1e-20 else 1e-10

    # Compute inverse-vol weights
    inv_vols    = {sym: 1.0 / max(vols[sym], 1e-10) for sym in symbols}
    total_inv   = sum(inv_vols.values())
    weights     = {sym: round(iv / total_inv, 6) for sym, iv in inv_vols.items()}

    # Normalize to sum = 1 (handle rounding)
    total_w = sum(weights.values())
    if total_w > 0 and abs(total_w - 1.0) > 1e-4:
        last_sym = symbols[-1]
        weights[last_sym] = round(1.0 - sum(weights[s] for s in symbols[:-1]), 6)

    return weights


# ─────────────────────────────────────────────────────────────────────────────
# Phase 3 — DAR(2,1) signal gate per asset
# ─────────────────────────────────────────────────────────────────────────────

def apply_dar_filter(fr_series: List[float], p: int = DAR_P, q: int = DAR_Q) -> bool:
    """
    Apply DAR(p,q) signal gate to FR spread series.

    DAR(2,1) logic:
      - Requires >= p+q points (3 minimum for DAR(2,1))
      - AR(2) component: check if current spread is consistent with AR(2) momentum
      - Signal gate: True if the most recent spread confirms persistent direction
        (i.e., consecutive spread values have same sign and non-trivial magnitude)
      - Returns False (no trade) if series is too noisy (sign alternates) or flat

    Implementation:
      - AR lag-1 sign persistence check: sign(fr_series[-1]) == sign(fr_series[-2])
      - Minimum signal strength: |latest spread| > SIGNAL_THRESHOLD
      - DAR MA-dampening: use exponential smoothing of last q+1 = 2 values

    Args:
      fr_series: List of FR spread values (HL - Bybit), ordered oldest to newest.
                 Must have at least p points.
      p: AR order (default 2)
      q: moving average window (default 1)

    Returns:
      True = signal confirmed (enter/hold position)
      False = signal rejected (no trade)
    """
    if len(fr_series) < p:
        # Insufficient history — default to allow (conservative entry)
        return len(fr_series) > 0 and abs(fr_series[-1]) > SIGNAL_THRESHOLD

    latest   = fr_series[-1]
    lag1     = fr_series[-2]
    lag2     = fr_series[-3] if len(fr_series) >= 3 else lag1

    # Condition 1: signal magnitude (latest spread exceeds threshold)
    if abs(latest) <= SIGNAL_THRESHOLD:
        return False

    # Condition 2: sign persistence (DAR persistence check)
    # At least the last 2 values must have the same sign
    if (latest > 0) != (lag1 > 0):
        return False  # sign flip — reject (noisy)

    # Condition 3: MA-dampened smoothed value (q=1: average of last 2 lags)
    smoothed_lag = (lag1 + lag2) / 2.0

    # DAR confirmation: smoothed lag must also exceed threshold and same sign
    if abs(smoothed_lag) <= SIGNAL_THRESHOLD:
        return False

    if (latest > 0) != (smoothed_lag > 0):
        return False

    return True


def _get_spread_series_for_asset(symbol: str, lookback_days: int = 7) -> List[float]:
    """Load FR spread series for a single asset from history."""
    history = _load_fr_history(lookback_days)
    series  = []
    for rec in history:
        sp = rec.get("fr", {}).get(symbol, {}).get("spread", None)
        if sp is not None:
            series.append(sp)
    return series


# ─────────────────────────────────────────────────────────────────────────────
# Phase 4 — Basket position decision
# ─────────────────────────────────────────────────────────────────────────────

def decide_basket_position(
    weights: Dict[str, float],
    dar_signals: Dict[str, bool],
    fr_data: Dict[str, Dict[str, float]],
) -> Dict[str, Optional[str]]:
    """
    Decide per-asset position direction for the basket.

    For each asset:
      - If DAR signal True and |spread| > threshold:
        - spread > 0 (HL FR > Bybit FR) → LONG_BYBIT_SHORT_HL  (long cheaper, short expensive)
        - spread < 0 (Bybit FR > HL FR) → LONG_HL_SHORT_BYBIT  (long cheaper, short expensive)
      - Else: NEUTRAL (no trade for this asset)

    K434 smart router integration:
      - Per asset: use spread to determine venue direction
      - Concentration cap check (HL ≤65% of total basket notional)

    Returns:
      {
        "BTC": "LONG_BYBIT_SHORT_HL" | "LONG_HL_SHORT_BYBIT" | None,
        "ETH": ...,
        "SOL": ...,
      }
    """
    positions: Dict[str, Optional[str]] = {}

    for sym in BASKET_SYMBOLS:
        dar_ok  = dar_signals.get(sym, False)
        spread  = fr_data.get(sym, {}).get("spread", 0.0)

        if not dar_ok or abs(spread) <= SIGNAL_THRESHOLD:
            positions[sym] = None
            continue

        # Positive spread → HL more expensive (higher FR) → short HL, long Bybit
        if spread > 0:
            positions[sym] = STATE_LONG_BYBIT_SHORT_HL
        else:
            positions[sym] = STATE_LONG_HL_SHORT_BYBIT

    # K355 HL concentration cap check (≤65%)
    # Count how many legs are on HL
    total_legs   = sum(1 for s in positions.values() if s is not None) * 2  # 2 legs per asset
    hl_legs      = 0
    for sym, pos in positions.items():
        if pos == STATE_LONG_HL_SHORT_BYBIT:
            hl_legs += 1   # long leg on HL
        elif pos == STATE_LONG_BYBIT_SHORT_HL:
            hl_legs += 1   # short leg on HL

    if total_legs > 0:
        hl_concentration = hl_legs / total_legs
        if hl_concentration > HL_CAP_PCT:
            # Concentration breach: suppress lowest-weight signal asset
            active_syms = [(sym, weights.get(sym, 0)) for sym, pos in positions.items() if pos is not None]
            active_syms.sort(key=lambda x: x[1])  # sort by weight ascending
            if active_syms:
                positions[active_syms[0][0]] = None  # remove lowest-weight to reduce HL concentration
            print(f"  [k457] HL concentration cap {hl_concentration:.1%} > {HL_CAP_PCT:.0%} → suppressed 1 asset",
                  file=sys.stderr)

    return positions


# ─────────────────────────────────────────────────────────────────────────────
# Phase 5 — Basket trade submission (6-leg POST_ONLY + IOC fallback)
# ─────────────────────────────────────────────────────────────────────────────

def _compute_leg_sizes(
    positions: Dict[str, Optional[str]],
    weights: Dict[str, float],
    aum: float,
) -> Dict[str, float]:
    """
    Compute per-asset notional size.

    Formula:
      sleeve_capital   = aum × SLEEVE_PCT
      per_asset_capital = sleeve_capital × weight_i
      notional_per_leg = per_asset_capital × LEVERAGE / 2  (2 legs per asset)

    At $10M / 5% / 4x / equal weights (0.333):
      sleeve_capital   = $500,000
      per_asset_capital = $500K × 0.333 = $166,667
      notional_per_leg = $166,667 × 4 / 2 = $333,333 per leg

    Returns {symbol: notional_per_leg_usd}
    """
    sleeve_capital = aum * SLEEVE_PCT
    sizes: Dict[str, float] = {}
    for sym in BASKET_SYMBOLS:
        if positions.get(sym) is None:
            sizes[sym] = 0.0
            continue
        w = weights.get(sym, 1.0 / len(BASKET_SYMBOLS))
        per_asset = sleeve_capital * w
        sizes[sym] = round(per_asset * LEVERAGE / 2.0, 2)
    return sizes


def submit_basket_trade(
    positions: Dict[str, Optional[str]],
    weights: Dict[str, float],
    aum: float = AUM_DEFAULT,
    dry_run: bool = True,
) -> dict:
    """
    Submit up to 6-leg basket trade: POST_ONLY first, IOC fallback per leg.

    Protocol (K439-style triple-leg extended to 6 legs):
      For each active asset:
        1. Submit LONG leg POST_ONLY on lower-FR venue
        2. Submit SHORT leg POST_ONLY on higher-FR venue
        3. After 5 min: check fill status
        4. Unfilled legs → IOC fallback
      Track per-asset fill rate.

    Args:
      positions: {sym: "LONG_HL_SHORT_BYBIT" | "LONG_BYBIT_SHORT_HL" | None}
      weights:   inv-vol weights per asset
      aum:       reference AUM in USD
      dry_run:   True = paper-trade simulation

    Returns:
      {
        "status":        "DRY_RUN" | "SUBMITTED" | "PARTIAL",
        "legs":          [{"symbol": "BTC", "long_venue": "HL", ...}, ...],
        "fill_rate":     float,  # fraction of legs filled
        "total_notional_usd": float,
        "ts_utc":        str,
      }
    """
    ts      = datetime.now(UTC).isoformat()
    leg_sizes = _compute_leg_sizes(positions, weights, aum)
    legs    = []
    total_notional = 0.0

    for sym in BASKET_SYMBOLS:
        pos = positions.get(sym)
        if pos is None:
            continue

        notional = leg_sizes.get(sym, 0.0)
        if notional <= 0:
            continue

        if pos == STATE_LONG_HL_SHORT_BYBIT:
            long_venue, short_venue = "HL", "Bybit"
        else:
            long_venue, short_venue = "Bybit", "HL"

        leg_entry = {
            "symbol":       sym,
            "direction":    pos,
            "long_venue":   long_venue,
            "short_venue":  short_venue,
            "notional_per_leg_usd": notional,
            "weight":       weights.get(sym, 0.333),
        }

        if dry_run or PAPER_TRADE:
            mode_tag = "DRY_RUN" if dry_run else "PAPER_TRADE"
            long_oid  = f"PAPER_LONG_{sym}_{long_venue}_{int(time.time())}"
            short_oid = f"PAPER_SHORT_{sym}_{short_venue}_{int(time.time())}"
            leg_entry.update({
                "long_order_id":  long_oid,
                "short_order_id": short_oid,
                "long_status":    mode_tag,
                "short_status":   mode_tag,
                "fill_status":    "DRY_RUN",
            })
            print(f"  [K457] {mode_tag}: LONG {sym}@{long_venue} + SHORT {sym}@{short_venue}  "
                  f"notional=${notional:,.0f}/leg  weight={weights.get(sym,0):.3f}")
        else:
            # LIVE scaffold (POST_ONLY → 5-min wait → IOC fallback)
            print(f"  [K457] SCAFFOLD: LONG {sym}@{long_venue} POST_ONLY (notional=${notional:,.0f})")
            print(f"  [K457] SCAFFOLD: SHORT {sym}@{short_venue} POST_ONLY (notional=${notional:,.0f})")
            # [Scaffold] In live: submit POST_ONLY, poll 5min, IOC fallback if unfilled
            leg_entry.update({
                "long_order_id":  f"SCAFFOLD_LONG_{sym}_{int(time.time())}",
                "short_order_id": f"SCAFFOLD_SHORT_{sym}_{int(time.time())}",
                "long_status":    "SCAFFOLD_POST_ONLY",
                "short_status":   "SCAFFOLD_POST_ONLY",
                "fill_status":    "SCAFFOLD",
            })

        legs.append(leg_entry)
        total_notional += notional * 2  # 2 legs

    # Compute fill rate (paper-trade: assume 100% fill; live: track actual)
    filled_legs = sum(1 for leg in legs if leg.get("fill_status") in ("DRY_RUN", "PAPER_TRADE"))
    total_legs  = len(legs) * 2  # 2 legs per asset (long + short)
    fill_rate   = filled_legs / max(total_legs / 2, 1)

    result = {
        "status":             "DRY_RUN" if (dry_run or PAPER_TRADE) else "SUBMITTED",
        "legs":               legs,
        "assets_active":      [leg["symbol"] for leg in legs],
        "total_legs":         total_legs,
        "total_notional_usd": round(total_notional, 2),
        "fill_rate":          round(fill_rate, 4),
        "leverage":           LEVERAGE,
        "sleeve_pct":         SLEEVE_PCT,
        "aum_ref_usd":        aum,
        "ts_utc":             ts,
    }

    _append_trade_log(result)
    return result


def _append_trade_log(record: dict) -> None:
    with open(TRADE_LOG_PATH, "a") as f:
        f.write(json.dumps(record) + "\n")


# ─────────────────────────────────────────────────────────────────────────────
# Phase 6 — Basket close (shorts first, then longs)
# ─────────────────────────────────────────────────────────────────────────────

def close_basket_position(reason: str, dry_run: bool = True) -> dict:
    """
    6-leg basket unwind: close short legs first (avoid uncovered shorts), then longs.

    Protocol:
      1. Close all short legs (buy-to-cover) simultaneously across all assets/venues
      2. Wait 2s for settlement
      3. Close all long legs (sell) simultaneously
      4. Verify all positions near zero

    Args:
      reason:  human-readable reason for closure
      dry_run: True = paper-trade simulation

    Returns closure result dict.
    """
    ts   = datetime.now(UTC).isoformat()
    dash = _load_dashboard()
    positions = dash.get("open_positions_per_asset", {})

    if not any(v is not None for v in positions.values()):
        return {"status": "NO_POSITION", "reason": "All assets NEUTRAL", "ts_utc": ts}

    short_closes = []
    long_closes  = []

    for sym in BASKET_SYMBOLS:
        pos_data = positions.get(sym)
        if pos_data is None:
            continue
        long_venue  = pos_data.get("long_venue", "")
        short_venue = pos_data.get("short_venue", "")
        size        = pos_data.get("size", 0.0)

        short_closes.append({"symbol": sym, "venue": short_venue, "side": "buy_to_cover", "size": size})
        long_closes.append({"symbol":  sym, "venue": long_venue,  "side": "sell",         "size": size})

    if dry_run or PAPER_TRADE:
        mode_tag = "DRY_RUN" if dry_run else "PAPER_TRADE"
        print(f"  [K457] {mode_tag} CLOSE: {len(short_closes)} shorts first, "
              f"{len(long_closes)} longs second  reason={reason}")
        for sc in short_closes:
            print(f"    BUY-COVER {sc['symbol']}@{sc['venue']} size=${sc['size']:,.0f}")
        for lc in long_closes:
            print(f"    SELL {lc['symbol']}@{lc['venue']} size=${lc['size']:,.0f}")
        result = {
            "status":        "DRY_RUN_CLOSED",
            "reason":        reason,
            "short_closes":  short_closes,
            "long_closes":   long_closes,
            "ts_utc":        ts,
        }
    else:
        # LIVE scaffold: sequential close (shorts first → longs)
        print(f"  [K457] SCAFFOLD LIVE: closing {len(short_closes)} shorts...")
        for sc in short_closes:
            print(f"    SCAFFOLD IOC BUY-COVER {sc['symbol']}@{sc['venue']}")
        print(f"  [K457] SCAFFOLD LIVE: closing {len(long_closes)} longs...")
        for lc in long_closes:
            print(f"    SCAFFOLD IOC SELL {lc['symbol']}@{lc['venue']}")
        result = {
            "status":       "SCAFFOLD_CLOSE",
            "reason":       reason,
            "short_closes": short_closes,
            "long_closes":  long_closes,
            "ts_utc":       ts,
        }

    _append_trade_log(result)
    return result


# ─────────────────────────────────────────────────────────────────────────────
# Phase 7 — Weekly inv-vol weight rebalancing
# ─────────────────────────────────────────────────────────────────────────────

def rebalance_inv_vol_weights() -> Dict[str, float]:
    """
    Weekly rebalance: recompute 30d realized vol per asset, update sleeve_weights.

    This is called automatically on each 8h cycle; effective weekly impact is that
    the weights update naturally as FR history accumulates.

    Returns fresh inv-vol weights.
    """
    weights = compute_inv_vol_weights(BASKET_SYMBOLS)
    print(f"  [K457] Inv-vol weights rebalanced:")
    for sym, w in weights.items():
        print(f"    {sym}: {w:.4f} ({w*100:.1f}%)")
    return weights


# ─────────────────────────────────────────────────────────────────────────────
# Dashboard I/O
# ─────────────────────────────────────────────────────────────────────────────

def _load_dashboard() -> dict:
    """Load k457_basket_dashboard.json; return defaults if missing."""
    if DASHBOARD_PATH.exists():
        try:
            return json.loads(DASHBOARD_PATH.read_text())
        except Exception:
            pass
    # Default (initial scaffold state)
    return {
        "last_poll_jst": "—",
        "current_signals": {"BTC": None, "ETH": None, "SOL": None},
        "inv_vol_weights_30d": {"BTC": 0.369, "ETH": 0.357, "SOL": 0.274},
        "open_positions_per_asset": {"BTC": None, "ETH": None, "SOL": None},
        "daily_pnl_per_asset": {"BTC": 0.0, "ETH": 0.0, "SOL": 0.0},
        "fill_rate_60d": None,
        "paper_trade_status": {
            "days_elapsed":   0,
            "target_60d":     60,
            "OOS_sharpe_60d": None,
        },
    }


def _write_dashboard(
    fr_data:    Dict[str, Dict[str, float]],
    weights:    Dict[str, float],
    positions:  Dict[str, Optional[str]],
    leg_sizes:  Dict[str, float],
    trade_result: dict,
    aum: float,
) -> dict:
    """Write k457_basket_dashboard.json."""
    dash = _load_dashboard()

    ts_jst = datetime.now(JST).strftime("%Y-%m-%d %H:%M JST")
    dash["last_poll_jst"]       = ts_jst
    dash["inv_vol_weights_30d"] = weights

    # Current signals
    signals: Dict[str, Optional[str]] = {}
    for sym in BASKET_SYMBOLS:
        pos = positions.get(sym)
        signals[sym] = pos  # None = NEUTRAL
    dash["current_signals"] = signals

    # Open positions
    open_pos: Dict[str, Optional[dict]] = {}
    for sym in BASKET_SYMBOLS:
        pos = positions.get(sym)
        if pos is None:
            open_pos[sym] = None
        else:
            if pos == STATE_LONG_HL_SHORT_BYBIT:
                long_v, short_v = "HL", "Bybit"
            else:
                long_v, short_v = "Bybit", "HL"
            open_pos[sym] = {
                "direction":   pos,
                "long_venue":  long_v,
                "short_venue": short_v,
                "size":        leg_sizes.get(sym, 0.0),
            }
    dash["open_positions_per_asset"] = open_pos

    # Basket metadata
    total_notional = trade_result.get("total_notional_usd", 0.0)
    dash["total_notional_usd"]   = total_notional
    dash["leverage"]             = LEVERAGE
    dash["sleeve_pct"]           = SLEEVE_PCT
    dash["aum_ref_usd"]          = aum
    dash["margin_used_usd"]      = round(total_notional / LEVERAGE, 2)
    dash["margin_pct_of_aum"]    = round((total_notional / LEVERAGE) / aum, 4) if aum > 0 else 0.0
    dash["fill_rate_latest"]     = trade_result.get("fill_rate", 0.0)

    # Paper-trade status
    pt = dash.get("paper_trade_status", {})
    days_elapsed = int(pt.get("days_elapsed", 0))
    dash["paper_trade_status"] = {
        "days_elapsed":   days_elapsed,
        "target_60d":     60,
        "OOS_sharpe_60d": pt.get("OOS_sharpe_60d"),
        "activation_criteria": {
            "OOS_sharpe_min": 15.0,
            "fill_rate_min_pct": 65,
            "status": "PAPER-TRADE (day %d / 60)" % days_elapsed,
        },
    }

    # Strategy metadata
    dash["paper_trade_mode"]    = PAPER_TRADE
    dash["wave"]                = "K459"
    dash["strategy"]            = "K457 BTC+ETH+SOL Multi-Asset FR Basket Carry"
    dash["OOS_sharpe_backtest"] = 19.58
    dash["v620_sleeve_pct"]     = 5.0

    DASHBOARD_PATH.write_text(json.dumps(dash, indent=2))
    return dash


# ─────────────────────────────────────────────────────────────────────────────
# Main single-shot run logic
# ─────────────────────────────────────────────────────────────────────────────

def run_cycle(dry_run: bool = True, aum: float = AUM_DEFAULT) -> int:
    """
    Single 8h cycle:
      1. Fetch per-asset FR from HL + Bybit
      2. Compute inv-vol weights (30d)
      3. Apply DAR(2,1) filter per asset
      4. Decide basket position per asset
      5. If entering: submit basket trade (6 legs POST_ONLY + IOC)
      6. Write dashboard
    """
    ts_jst = datetime.now(JST).strftime("%Y-%m-%d %H:%M JST")
    print(f"\n=== K457 BTC+ETH+SOL Basket FR Carry — {ts_jst} ===")
    print(f"  Mode: {'DRY-RUN' if dry_run else 'PAPER-TRADE' if PAPER_TRADE else 'LIVE'}")
    print(f"  Basket: {BASKET_SYMBOLS}  |  AUM: ${aum:,.0f}  |  Sleeve: {SLEEVE_PCT:.0%}  |  Leverage: {LEVERAGE}x")

    # Step 1: Fetch per-asset FR
    print(f"\n  [Step 1] Fetching FR per asset (HL + Bybit)...")
    fr_data = fetch_per_asset_fr(BASKET_SYMBOLS)
    for sym in BASKET_SYMBOLS:
        fr = fr_data.get(sym, {})
        print(f"    {sym:4s}: HL={fr.get('hl', 0):+.8f}  Bybit={fr.get('bybit', 0):+.8f}  "
              f"Spread={fr.get('spread', 0):+.8f}")

    # Step 2: Compute inv-vol weights
    print(f"\n  [Step 2] Computing inv-vol weights (30d realized vol)...")
    weights = compute_inv_vol_weights(BASKET_SYMBOLS)
    for sym, w in weights.items():
        print(f"    {sym:4s}: weight={w:.4f} ({w*100:.1f}%)")

    # Step 3: DAR(2,1) filter per asset
    print(f"\n  [Step 3] Applying DAR(2,1) signal gate per asset...")
    dar_signals: Dict[str, bool] = {}
    for sym in BASKET_SYMBOLS:
        spread_series = _get_spread_series_for_asset(sym, lookback_days=7)
        signal = apply_dar_filter(spread_series)
        dar_signals[sym] = signal
        print(f"    {sym:4s}: spread_series_len={len(spread_series)}  DAR_signal={signal}")

    # Step 4: Decide basket position
    print(f"\n  [Step 4] Deciding basket positions...")
    positions = decide_basket_position(weights, dar_signals, fr_data)
    active_count = sum(1 for p in positions.values() if p is not None)
    for sym, pos in positions.items():
        print(f"    {sym:4s}: {pos or 'NEUTRAL'}")
    print(f"  Active assets: {active_count}/{len(BASKET_SYMBOLS)}")

    # Step 5: Compute leg sizes
    leg_sizes = _compute_leg_sizes(positions, weights, aum)
    total_notional = sum(s * 2 for s in leg_sizes.values() if s > 0)
    print(f"\n  [Step 5] Notional sizing:")
    print(f"  Sleeve capital: ${aum * SLEEVE_PCT:,.0f}  ({SLEEVE_PCT:.0%} × ${aum/1e6:.0f}M)")
    for sym in BASKET_SYMBOLS:
        sz = leg_sizes.get(sym, 0.0)
        if sz > 0:
            print(f"    {sym:4s}: ${sz:,.0f}/leg  (weight={weights.get(sym,0):.3f}, 2 legs = ${sz*2:,.0f})")
    print(f"  Total basket notional: ${total_notional:,.0f}  Margin: ${total_notional/LEVERAGE:,.0f}")

    # Step 6: Load current state + submit trade
    dash = _load_dashboard()
    current_positions = dash.get("open_positions_per_asset", {})
    any_open = any(v is not None for v in current_positions.values())

    trade_result = {"status": "NO_OP", "fill_rate": 0.0, "total_notional_usd": 0.0}

    if active_count > 0:
        if not any_open:
            print(f"\n  [Step 6] Submitting basket trade ({active_count} assets × 2 legs)...")
            trade_result = submit_basket_trade(positions, weights, aum, dry_run=dry_run)
            print(f"  Trade status: {trade_result['status']}  Fill rate: {trade_result['fill_rate']:.1%}")
        else:
            # Check for signal reversals per asset
            flip_needed = False
            for sym, new_pos in positions.items():
                old_pos = current_positions.get(sym)
                if old_pos is not None and new_pos is not None and old_pos != new_pos:
                    flip_needed = True
                    print(f"  [Step 6] Signal reversal for {sym}: {old_pos} → {new_pos}")

            if flip_needed:
                print(f"  [Step 6] Closing reversed positions...")
                close_basket_position("signal_reversal", dry_run=dry_run)
                print(f"  [Step 6] Re-entering basket...")
                trade_result = submit_basket_trade(positions, weights, aum, dry_run=dry_run)
            else:
                print(f"\n  [Step 6] HOLD (same direction, no new entry)")
    else:
        if any_open:
            print(f"\n  [Step 6] All DAR signals gone — closing basket...")
            trade_result = close_basket_position("all_signals_below_threshold", dry_run=dry_run)
        else:
            print(f"\n  [Step 6] NEUTRAL — no active signals, no positions")

    # Step 7: Write dashboard
    dash_out = _write_dashboard(fr_data, weights, positions, leg_sizes, trade_result, aum)
    print(f"\n  [Step 7] Dashboard written → {DASHBOARD_PATH}")

    # Summary
    active_sigs = [f"{s}:{p}" for s, p in positions.items() if p is not None]
    print(f"\n  === K457 Cycle Complete ===")
    print(f"  Active signals:  {active_sigs or 'NEUTRAL (all assets)'}")
    print(f"  Inv-vol weights: {weights}")
    print(f"  Margin/AUM:      {dash_out.get('margin_pct_of_aum', 0)*100:.1f}%")
    print(f"  Paper-trade:     day {dash_out.get('paper_trade_status', {}).get('days_elapsed', 0)}/60")
    print(f"  OOS Sharpe (backtest): 19.58 → 60d paper-trade target ≥15")
    print(f"  Activation:      60d paper-trade gate + fill_rate ≥65% + v6.20 sleeve 5%")
    print()

    return 0


# ─────────────────────────────────────────────────────────────────────────────
# CLI entry point
# ─────────────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="K457 BTC+ETH+SOL Multi-Asset Basket FR Carry Strategy (K459 scaffold)"
    )
    parser.add_argument("--dry-run",   action="store_true", default=True,
                        help="Paper-trade simulation (default)")
    parser.add_argument("--status",    action="store_true",
                        help="Print current dashboard state and exit")
    parser.add_argument("--rebalance", action="store_true",
                        help="Recompute inv-vol weights and show result")
    parser.add_argument("--close",     default=None, metavar="REASON",
                        help="Close all basket positions with reason")
    parser.add_argument("--aum",       type=float, default=AUM_DEFAULT,
                        help=f"Reference AUM in USD (default: ${AUM_DEFAULT:,.0f})")
    args = parser.parse_args()

    if args.status:
        dash = _load_dashboard()
        print(f"\n=== K457 Basket Dashboard ({dash.get('last_poll_jst', '—')}) ===")
        print(json.dumps(dash, indent=2))
        return 0

    if args.rebalance:
        weights = rebalance_inv_vol_weights()
        print(f"\n=== K457 Inv-Vol Weights (30d) ===")
        for sym, w in weights.items():
            print(f"  {sym}: {w:.6f} ({w*100:.2f}%)")
        return 0

    if args.close:
        result = close_basket_position(args.close, dry_run=args.dry_run)
        print(f"\n=== K457 Close Result ===")
        print(json.dumps(result, indent=2))
        return 0

    return run_cycle(dry_run=args.dry_run, aum=args.aum)


if __name__ == "__main__":
    sys.exit(main())
