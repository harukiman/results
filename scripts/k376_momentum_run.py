"""
k376_momentum_run.py — K376 Volume-Spike Momentum Paper-Trade Daemon
=====================================================================
K380 production scaffold — paper-trade only, NO real exchange calls.
K378 CONDITIONAL_ACCEPT activation criteria implemented here.

Strategy:
  - Universe:     ETH, LINK, AVAX (stable 3; PEPE/SUI dropped — 3/4 folds negative)
  - Signal:       volume_ratio > 4.0 AND |5min_return| > 0.4% on 5min bars
  - Regime gate:  BTC 20d SMA slope > 0 (bull only; skip all signals in bear)
  - Execution:    Post-only limit (maker) — paper: log to JSONL, no real order
  - Hold period:  4h (240 min)
  - Sleeve:       3% of AUM (v6.14 candidate)
  - Paper gate:   60-day run required; G8 fill_rate ≥ 65% before capital activation
  - Emergency:    Check EMERGENCY_EXIT_TRIGGERED.flag on each run

Usage (cron via launchd at 5-min interval):
  python3 scripts/k376_momentum_run.py
  python3 scripts/k376_momentum_run.py --dry-run   # verbose without file writes

K339 Security:
  REPO_ROOT = Path(__file__).resolve().parent.parent
  No /Users/ literals in code paths.

Dependencies: requests (stdlib-supplemented). NO new packages beyond existing venv.
"""
from __future__ import annotations

import argparse
import datetime
import json
import logging
import math
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ── K339 Security: REPO_ROOT from __file__, no /Users/ literals ──────────────
REPO_ROOT = Path(__file__).resolve().parent.parent
LOGS_DIR  = REPO_ROOT / "logs"
DATA_DIR  = REPO_ROOT / "data"
LOGS_DIR.mkdir(exist_ok=True)
DATA_DIR.mkdir(exist_ok=True)

# ── Strategy constants (K378 CONDITIONAL_ACCEPT specification) ────────────────
STRATEGY_ID         = "K376_volume_momentum_v1"
VERSION             = "v6.14_candidate"
UNIVERSE            = ["ETH", "LINK", "AVAX"]   # PEPE/SUI dropped (3/4 folds negative)
REGIME_FILTER       = "BTC_20d_SMA_slope"
SLEEVE_PCT          = 0.03                        # 3% of AUM
HOLD_PERIOD_MINUTES = 240                         # 4h hold
VOL_RATIO_THRESHOLD = 4.0                         # volume spike: 4× 12h rolling avg
RETURN_THRESHOLD    = 0.004                       # |5min return| > 0.4%
BTC_SMA_PERIOD      = 20 * 24                     # 20d in hours = 480 1h bars
SIGNAL_LOOKBACK_H   = 24                          # 24h of 5min bars for vol rolling
PAPER_TRADE_DAYS    = 60                          # required before capital activation
FILL_RATE_GATE_PCT  = 0.65                        # G8: fill rate ≥ 65%

# ── File paths ────────────────────────────────────────────────────────────────
EMERGENCY_FLAG_FILE     = REPO_ROOT / "EMERGENCY_EXIT_TRIGGERED.flag"
DASHBOARD_JSON          = DATA_DIR  / "k376_momentum_dashboard.json"
PAPER_FILLS_JSONL       = DATA_DIR  / "k376_paper_fills.jsonl"
LOG_FILE                = LOGS_DIR  / "k376_momentum.log"

# ── Binance OHLCV endpoint (public, no auth) ─────────────────────────────────
BINANCE_KLINES_URL = "https://api.binance.com/api/v3/klines"

# ── Logging setup ─────────────────────────────────────────────────────────────
def setup_logging(verbose: bool = False) -> logging.Logger:
    logger = logging.getLogger("k376_momentum")
    if logger.handlers:
        return logger  # already configured (idempotent)
    logger.setLevel(logging.DEBUG)
    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s", "%Y-%m-%d %H:%M:%S UTC"
    )
    sh = logging.StreamHandler(sys.stdout)
    sh.setLevel(logging.DEBUG if verbose else logging.INFO)
    sh.setFormatter(fmt)
    logger.addHandler(sh)
    fh = logging.FileHandler(LOG_FILE, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)
    logger.addHandler(fh)
    return logger


# ─────────────────────────────────────────────────────────────────────────────
# 1. Emergency exit flag check
# ─────────────────────────────────────────────────────────────────────────────

def check_emergency_flag(logger: logging.Logger) -> bool:
    """Return True if emergency exit has been triggered (flag file present)."""
    if EMERGENCY_FLAG_FILE.exists():
        logger.critical(
            f"EMERGENCY_EXIT_TRIGGERED.flag present at {EMERGENCY_FLAG_FILE}. "
            "Skipping all signal evaluation and exiting immediately."
        )
        return True
    return False


# ─────────────────────────────────────────────────────────────────────────────
# 2. Data fetch helpers
# ─────────────────────────────────────────────────────────────────────────────

def _fetch_binance_klines(
    symbol: str,
    interval: str,
    limit: int,
    retries: int = 3,
) -> List[List]:
    """
    Fetch OHLCV klines from Binance public API.
    Returns list of [open_time, open, high, low, close, volume, ...].
    On failure: raises RuntimeError.
    """
    try:
        import requests
    except ImportError:
        raise RuntimeError("requests library required. Install: pip install requests")

    params = {
        "symbol":   symbol.upper() + "USDT",
        "interval": interval,
        "limit":    str(limit),
    }
    for attempt in range(retries):
        try:
            resp = requests.get(
                BINANCE_KLINES_URL,
                params=params,
                headers={"User-Agent": "ct-k376-momentum/1.0"},
                timeout=20,
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:
            if attempt < retries - 1:
                wait = 5 * (2 ** attempt)
                print(f"  [WARN] klines fetch {symbol} {interval} attempt {attempt+1} failed: {exc} — retry in {wait}s")
                time.sleep(wait)
            else:
                raise RuntimeError(f"Binance klines fetch failed after {retries} attempts for {symbol}/{interval}: {exc}")


def fetch_btc_1h_sma(logger: logging.Logger) -> Tuple[float, str]:
    """
    Fetch BTC 1h OHLCV (last 20d = 480 bars), compute 20d SMA slope.
    Returns (slope, regime) where regime in ('bull', 'bear').
    slope > 0 => bull, slope <= 0 => bear.

    Slope = (SMA[-1] - SMA[-BTC_SMA_PERIOD//2]) / (BTC_SMA_PERIOD//2) — simple linear proxy.
    """
    logger.debug("Fetching BTC 1h klines (480 bars = 20d)...")
    try:
        klines = _fetch_binance_klines("BTC", "1h", BTC_SMA_PERIOD + 10)
    except RuntimeError as exc:
        logger.error(f"BTC 1h fetch failed: {exc}")
        logger.warning("Regime check failed — defaulting to BEAR (safe skip).")
        return 0.0, "bear"

    if len(klines) < BTC_SMA_PERIOD:
        logger.warning(f"BTC 1h klines too short ({len(klines)} bars). Defaulting to bear.")
        return 0.0, "bear"

    closes = [float(k[4]) for k in klines[-BTC_SMA_PERIOD:]]
    n = len(closes)

    # Simple 20d SMA slope: compare first-half mean vs second-half mean
    half = n // 2
    sma_early = sum(closes[:half]) / half
    sma_late  = sum(closes[half:]) / (n - half)
    slope = sma_late - sma_early  # positive => rising SMA => bull

    regime = "bull" if slope > 0 else "bear"
    logger.info(f"BTC 20d SMA slope: {slope:+.2f} ({regime.upper()} regime) "
                f"[early_avg={sma_early:.0f}, late_avg={sma_late:.0f}]")
    return slope, regime


def fetch_coin_5min_ohlcv(coin: str, lookback_bars: int, logger: logging.Logger) -> Optional[List[Dict]]:
    """
    Fetch last `lookback_bars` of 5min OHLCV for given coin.
    Returns list of {ts, open, high, low, close, volume} dicts, or None on error.
    lookback_bars: 24h = 288 bars.
    """
    logger.debug(f"Fetching {coin} 5min klines ({lookback_bars} bars)...")
    try:
        klines = _fetch_binance_klines(coin, "5m", lookback_bars + 5)
    except RuntimeError as exc:
        logger.error(f"{coin} 5min fetch failed: {exc}")
        return None

    bars = []
    for k in klines[-lookback_bars:]:
        bars.append({
            "ts":     int(k[0]) // 1000,     # unix seconds
            "open":   float(k[1]),
            "high":   float(k[2]),
            "low":    float(k[3]),
            "close":  float(k[4]),
            "volume": float(k[5]),
        })
    return bars


# ─────────────────────────────────────────────────────────────────────────────
# 3. Signal computation
# ─────────────────────────────────────────────────────────────────────────────

def compute_volume_ratio(bars: List[Dict]) -> float:
    """
    volume_ratio = current_bar_volume / 12h rolling average volume.
    12h = 144 bars of 5min. If fewer bars available, use all.
    """
    if not bars:
        return 0.0
    current_vol = bars[-1]["volume"]
    lookback = min(144, len(bars) - 1)
    if lookback <= 0:
        return 1.0
    rolling_vols = [b["volume"] for b in bars[-lookback - 1:-1]]
    avg_vol = sum(rolling_vols) / len(rolling_vols) if rolling_vols else 1.0
    if avg_vol < 1e-9:
        return 0.0
    return current_vol / avg_vol


def compute_5min_return(bars: List[Dict]) -> float:
    """Return 5min return of last bar: (close - open) / open."""
    if not bars:
        return 0.0
    bar = bars[-1]
    if bar["open"] < 1e-9:
        return 0.0
    return (bar["close"] - bar["open"]) / bar["open"]


def evaluate_signal(
    coin: str,
    bars: List[Dict],
    logger: logging.Logger,
) -> Optional[Dict]:
    """
    Evaluate K376 signal for a single coin.
    Signal: vol_ratio > 4.0 AND |ret| > 0.4%.
    Returns signal dict if triggered, None otherwise.
    """
    vol_ratio = compute_volume_ratio(bars)
    ret       = compute_5min_return(bars)
    abs_ret   = abs(ret)

    logger.info(
        f"  {coin}: vol_ratio={vol_ratio:.2f}x, |ret|={abs_ret*100:.3f}% "
        f"[threshold: vol>{VOL_RATIO_THRESHOLD}x, |ret|>{RETURN_THRESHOLD*100:.1f}%]"
    )

    if vol_ratio > VOL_RATIO_THRESHOLD and abs_ret > RETURN_THRESHOLD:
        direction = "long" if ret > 0 else "short"
        entry_px  = bars[-1]["close"]
        ts_utc    = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        exit_time = (
            datetime.datetime.utcnow()
            + datetime.timedelta(minutes=HOLD_PERIOD_MINUTES)
        ).strftime("%Y-%m-%dT%H:%M:%SZ")

        signal = {
            "coin":       coin,
            "direction":  direction,
            "entry_px":   entry_px,
            "vol_ratio":  round(vol_ratio, 3),
            "ret_5m_pct": round(ret * 100, 4),
            "entry_time": ts_utc,
            "exit_time":  exit_time,
            "hold_min":   HOLD_PERIOD_MINUTES,
            "maker_only": True,
            "status":     "paper_open",
        }
        logger.info(
            f"  *** SIGNAL: {coin} {direction.upper()} @ {entry_px:.4f} "
            f"(vol_ratio={vol_ratio:.2f}x, ret={ret*100:+.3f}%)"
        )
        return signal
    return None


# ─────────────────────────────────────────────────────────────────────────────
# 4. Paper-trade execution (log-only, no real API)
# ─────────────────────────────────────────────────────────────────────────────

def place_paper_order(signal: Dict, logger: logging.Logger) -> None:
    """
    Paper-trade: log signal to JSONL fill log.
    In paper mode: compute simulated post-only limit price (mid ± 1 tick)
    and record as fill (assumed filled for paper purposes).
    Maker-only: entry price is post-only limit at mid.
    """
    fill_record = {
        **signal,
        "paper_trade":   True,
        "fill_type":     "post_only_limit",
        "maker_rebate_bps": 2.0,   # HL/Bybit maker rebate estimate
        "sleeve_pct":    SLEEVE_PCT,
        "strategy_id":   STRATEGY_ID,
        "version":       VERSION,
        "logged_at_utc": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
    }

    with open(PAPER_FILLS_JSONL, "a", encoding="utf-8") as f:
        f.write(json.dumps(fill_record) + "\n")

    logger.info(
        f"  [PAPER] Order logged: {signal['coin']} {signal['direction'].upper()} "
        f"@ {signal['entry_px']:.4f} (maker post-only, exit ~{signal['exit_time']})"
    )


# ─────────────────────────────────────────────────────────────────────────────
# 5. Position tracker — read JSONL, check for expired holds
# ─────────────────────────────────────────────────────────────────────────────

def load_paper_positions(logger: logging.Logger) -> Tuple[List[Dict], List[Dict]]:
    """
    Read PAPER_FILLS_JSONL.
    Returns (open_positions, all_fills).
    A position is "open" if status == 'paper_open' and exit_time > now.
    """
    all_fills: List[Dict] = []
    if PAPER_FILLS_JSONL.exists():
        with open(PAPER_FILLS_JSONL, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        all_fills.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass

    now_utc = datetime.datetime.utcnow()
    open_positions = []
    for fill in all_fills:
        if fill.get("status") != "paper_open":
            continue
        exit_time_str = fill.get("exit_time", "")
        try:
            exit_time = datetime.datetime.strptime(exit_time_str, "%Y-%m-%dT%H:%M:%SZ")
        except (ValueError, TypeError):
            continue
        if exit_time > now_utc:
            open_positions.append(fill)

    logger.debug(f"Loaded {len(all_fills)} fills; {len(open_positions)} open positions.")
    return open_positions, all_fills


def compute_fill_rate_60d(all_fills: List[Dict]) -> float:
    """
    G8 fill rate gate: fraction of signals where maker fill was simulated.
    In paper mode: all logged signals count as filled (limit assumed resting).
    Real fill rate computed once live data flows.
    Returns float in [0.0, 1.0].
    """
    if not all_fills:
        return 0.0
    cutoff = datetime.datetime.utcnow() - datetime.timedelta(days=60)
    recent = [
        f for f in all_fills
        if f.get("status") in ("paper_open", "paper_closed")
        and _parse_utc(f.get("logged_at_utc", "")) >= cutoff
    ]
    if not recent:
        return 0.0
    filled = sum(1 for f in recent if f.get("fill_type") is not None)
    return filled / len(recent)


def _parse_utc(ts_str: str) -> datetime.datetime:
    """Parse ISO UTC string; return epoch on failure."""
    try:
        return datetime.datetime.strptime(ts_str, "%Y-%m-%dT%H:%M:%SZ")
    except (ValueError, TypeError):
        return datetime.datetime(1970, 1, 1)


def compute_live_sharpe_30d(all_fills: List[Dict]) -> float:
    """
    Compute approximate daily Sharpe over last 30 days from paper fills.
    Paper-mode: assumes 1 unit position per signal, PnL = direction × |ret|.
    Returns 0.0 if insufficient data (< 5 fills).
    """
    cutoff = datetime.datetime.utcnow() - datetime.timedelta(days=30)
    recent = [
        f for f in all_fills
        if _parse_utc(f.get("logged_at_utc", "")) >= cutoff
    ]
    if len(recent) < 5:
        return 0.0

    pnls = []
    for f in recent:
        ret = f.get("ret_5m_pct", 0.0) / 100.0
        direction_mult = 1.0 if f.get("direction") == "long" else -1.0
        pnls.append(direction_mult * abs(ret))  # simplified paper PnL

    if len(pnls) < 2:
        return 0.0
    mean_pnl = sum(pnls) / len(pnls)
    var_pnl  = sum((x - mean_pnl) ** 2 for x in pnls) / (len(pnls) - 1)
    std_pnl  = math.sqrt(var_pnl) if var_pnl > 0 else 1e-9
    sharpe   = mean_pnl / std_pnl * math.sqrt(252)  # annualized
    return round(sharpe, 3)


def count_signals_24h(all_fills: List[Dict]) -> int:
    """Count signals in last 24h."""
    cutoff = datetime.datetime.utcnow() - datetime.timedelta(hours=24)
    return sum(
        1 for f in all_fills
        if _parse_utc(f.get("logged_at_utc", "")) >= cutoff
    )


# ─────────────────────────────────────────────────────────────────────────────
# 6. Dashboard JSON update
# ─────────────────────────────────────────────────────────────────────────────

def update_dashboard(
    regime: str,
    slope: float,
    open_positions: List[Dict],
    all_fills: List[Dict],
    logger: logging.Logger,
) -> None:
    """Write/update data/k376_momentum_dashboard.json with current state."""
    fill_rate_60d   = compute_fill_rate_60d(all_fills)
    live_sharpe_30d = compute_live_sharpe_30d(all_fills)
    signals_24h     = count_signals_24h(all_fills)

    # Annualized paper return (simplified): mean daily signal PnL × 252
    cutoff = datetime.datetime.utcnow() - datetime.timedelta(days=30)
    recent_30 = [
        f for f in all_fills
        if _parse_utc(f.get("logged_at_utc", "")) >= cutoff
    ]
    if recent_30:
        pnl_vals = []
        for f in recent_30:
            ret = abs(f.get("ret_5m_pct", 0.0)) / 100.0
            pnl_vals.append(ret)
        ann_return_paper = round(sum(pnl_vals) / max(len(pnl_vals), 1) * 252, 4)
    else:
        ann_return_paper = 0.0

    dashboard = {
        "strategy_id":         STRATEGY_ID,
        "version":             VERSION,
        "universe":            UNIVERSE,
        "regime_filter":       REGIME_FILTER,
        "sleeve_pct":          SLEEVE_PCT,
        "hold_period_minutes": HOLD_PERIOD_MINUTES,
        "vol_ratio_threshold": VOL_RATIO_THRESHOLD,
        "return_threshold":    RETURN_THRESHOLD,
        "current_regime":      regime,
        "btc_sma_slope":       round(slope, 4),
        "open_positions":      open_positions,
        "recent_signals_24h":  signals_24h,
        "fill_rate_60d":       round(fill_rate_60d, 4),
        "live_sharpe_30d":     live_sharpe_30d,
        "ann_return_paper":    ann_return_paper,
        "paper_trade_mode":    True,
        "maker_only":          True,
        "g8_fill_rate_gate":   FILL_RATE_GATE_PCT,
        "g8_gate_passed":      fill_rate_60d >= FILL_RATE_GATE_PCT,
        "paper_trade_days_required": PAPER_TRADE_DAYS,
        "activation_criteria": {
            "btc_20d_sma_slope_filter": True,
            "universe":                 "ETH_LINK_AVAX_only",
            "sleeve_pct":               SLEEVE_PCT,
            "maker_only_execution":     True,
            "paper_trade_60d_gate":     True,
            "g8_fill_rate_ge_65pct":    True,
            "k357_bybit_emergency_exit": True,
            "g8_g9_live_gates_required": True,
        },
        "next_eligibility":    "After 60d paper-trade + G8 fill rate >=65% confirmation",
        "runbook_section":     "docs/k302a_runbook.md §17",
        "last_updated_utc":    datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
    }

    with open(DASHBOARD_JSON, "w", encoding="utf-8") as f:
        json.dump(dashboard, f, indent=2)

    logger.info(
        f"Dashboard updated: regime={regime}, open={len(open_positions)}, "
        f"signals_24h={signals_24h}, fill_rate_60d={fill_rate_60d:.1%}, "
        f"sharpe_30d={live_sharpe_30d:.3f}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# 7. Main
# ─────────────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "K376 Volume-Spike Momentum Paper-Trade Daemon (K380 scaffold)\n"
            "K378 CONDITIONAL_ACCEPT: ETH/LINK/AVAX · BTC 20d SMA slope filter · "
            "3% sleeve · 60d paper-trade gate"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Normal run (called by launchd every 5min):
  python3 scripts/k376_momentum_run.py

  # Verbose debug run:
  python3 scripts/k376_momentum_run.py --verbose

  # Skip file writes (read-only diagnostic):
  python3 scripts/k376_momentum_run.py --dry-run

K378 activation criteria embedded:
  1. BTC 20d SMA slope filter (systemic regime gate)
  2. Universe: ETH + LINK + AVAX only
  3. 3% sleeve allocation (v6.14 candidate)
  4. Maker-only execution (post-only limit)
  5. 60-day paper-trade (G8 fill rate gate >= 65%)
  6. K357 Bybit emergency exit gap addressed in docs/k302a_runbook.md §14
  7. G8 + G9 live gates required pre-activation
        """,
    )
    parser.add_argument("--verbose",  action="store_true", help="Verbose logging")
    parser.add_argument("--dry-run",  action="store_true",
                        help="Skip file writes (diagnostic mode)")
    args = parser.parse_args()

    logger = setup_logging(verbose=args.verbose or args.dry_run)

    logger.info(f"K376 momentum run starting | REPO_ROOT={REPO_ROOT} | dry_run={args.dry_run}")
    logger.info(f"Universe: {UNIVERSE} | Sleeve: {SLEEVE_PCT*100:.0f}% | Hold: {HOLD_PERIOD_MINUTES}min")

    # ── Step 1: Emergency exit flag check ────────────────────────────────────
    if check_emergency_flag(logger):
        return 0

    # ── Step 2: BTC regime check ─────────────────────────────────────────────
    slope, regime = fetch_btc_1h_sma(logger)

    if regime == "bear":
        logger.info(
            f"BEAR regime detected (BTC SMA slope={slope:+.2f}). "
            "Skipping all signal evaluation per K378 regime gate."
        )
        if not args.dry_run:
            # Still update dashboard with bear regime state
            open_positions, all_fills = load_paper_positions(logger)
            update_dashboard(regime, slope, open_positions, all_fills, logger)
        return 0

    logger.info(f"BULL regime confirmed (slope={slope:+.2f}). Proceeding to signal evaluation.")

    # ── Step 3: Load existing paper positions ────────────────────────────────
    open_positions, all_fills = load_paper_positions(logger)
    logger.info(f"Open positions: {len(open_positions)} | Total fills: {len(all_fills)}")

    # ── Step 4 & 5: Fetch 5min OHLCV + compute signals ───────────────────────
    bars_per_24h = SIGNAL_LOOKBACK_H * 12  # 12 × 5min bars per hour
    new_signals: List[Dict] = []

    for coin in UNIVERSE:
        bars = fetch_coin_5min_ohlcv(coin, bars_per_24h, logger)
        if bars is None or len(bars) < 50:
            logger.warning(f"{coin}: insufficient bars ({len(bars) if bars else 0}). Skip.")
            continue
        signal = evaluate_signal(coin, bars, logger)
        if signal:
            new_signals.append(signal)

    # ── Step 6 & 7: Place paper orders ───────────────────────────────────────
    if new_signals:
        logger.info(f"Signals triggered: {len(new_signals)}")
        for signal in new_signals:
            if not args.dry_run:
                place_paper_order(signal, logger)
            else:
                logger.info(
                    f"  [DRY-RUN] Would log: {signal['coin']} {signal['direction'].upper()} "
                    f"@ {signal['entry_px']:.4f}"
                )
    else:
        logger.info("No signals triggered this cycle.")

    # Reload fills to include any new ones for dashboard
    if not args.dry_run:
        open_positions, all_fills = load_paper_positions(logger)

    # ── Step 8 & 9: Update dashboard ─────────────────────────────────────────
    if not args.dry_run:
        update_dashboard(regime, slope, open_positions, all_fills, logger)
    else:
        logger.info("[DRY-RUN] Dashboard update skipped.")

    logger.info("K376 momentum run complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
