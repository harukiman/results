#!/usr/bin/env python3
"""
k376_regime_trigger_monitor.py — K376 Bull Regime Trigger Monitor (K497)
=========================================================================
31st daemon.  Daily check of BTC 20d SMA slope.  Writes JSON status and
appends to alerts.log when regime transitions.  NO live switch (user gate).

Trigger logic:
  slope = (SMA_today - SMA_20d_ago) / 20
  BEAR         : slope ≤ -500 AND days_bear ≥ 1
  TRANSITION   : -500 < slope < +500  (alert: approaching bull)
  BULL_CONFIRMED : slope ≥ 0 for ≥ 7 consecutive calendar days

Outputs:
  data/k376_regime_status.json   — current state
  data/alerts.log                — append on BULL_CONFIRMED / TRANSITION edge
  data/k376_activation_alert.md  — generated when BULL_CONFIRMED (5-step playbook)

K339 Security: REPO_ROOT = Path(__file__).resolve().parent.parent
No /Users/ literals.

Usage:
  python3 scripts/k376_regime_trigger_monitor.py
  python3 scripts/k376_regime_trigger_monitor.py --dry-run   # no file writes
  python3 scripts/k376_regime_trigger_monitor.py --backtest  # 2-year regime history
"""
from __future__ import annotations

import argparse
import datetime
import json
import logging
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ── K339 REPO_ROOT (no /Users/ literals) ─────────────────────────────────────
REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR  = REPO_ROOT / "data"
LOGS_DIR  = REPO_ROOT / "logs"
DATA_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)

# ── Constants ─────────────────────────────────────────────────────────────────
DAEMON_LABEL        = "com.cryptolab.k376-regime-monitor"
VERSION             = "k497_v1"
BTC_SMA_PERIOD      = 20          # days
BULL_CONSEC_DAYS    = 7           # slope > 0 for this many days = BULL_CONFIRMED
SLOPE_BEAR_THRESH   = -500.0      # slope ≤ this = BEAR
SLOPE_BULL_THRESH   = 0.0         # slope ≥ this = trending bull
SLOPE_TRANSITION_LO = -500.0      # -500 < slope < +500 = TRANSITION zone
SLOPE_TRANSITION_HI = 500.0

# Annual profit when K376 is activated (K488 quantification at $10M)
K376_ANNUAL_PROFIT_3PCT  = 247_000   # $247K/yr @ $10M, 3% sleeve
K376_ANNUAL_PROFIT_5PCT  = 412_000   # $412K/yr @ $10M, 5% sleeve
K376_ANNUAL_PROFIT_100M  = 2_470_000 # $2.47M/yr @ $100M, 3% sleeve
DAILY_PROFIT_3PCT        = K376_ANNUAL_PROFIT_3PCT / 365.0  # $/day when active

STATUS_FILE      = DATA_DIR / "k376_regime_status.json"
ALERTS_LOG       = DATA_DIR / "alerts.log"
ACTIVATION_ALERT = DATA_DIR / "k376_activation_alert.md"
STATE_HISTORY    = DATA_DIR / "k376_regime_history.jsonl"

JST = datetime.timezone(datetime.timedelta(hours=9))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    handlers=[
        logging.StreamHandler(sys.stderr),
        logging.FileHandler(LOGS_DIR / "k376_regime_monitor.log", encoding="utf-8"),
    ],
)
log = logging.getLogger("k376_regime_monitor")


# ─────────────────────────────────────────────────────────────────────────────
# Data fetch: HL candleSnapshot → BTC daily close
# ─────────────────────────────────────────────────────────────────────────────

def _fetch_hl_btc_daily(n_days: int = 45) -> List[Dict[str, Any]]:
    """Fetch BTC 1d candles from HyperLiquid info API (free, no auth)."""
    try:
        import urllib.request
        end_ms   = int(time.time() * 1000)
        start_ms = end_ms - n_days * 86_400_000
        payload  = json.dumps({
            "type": "candleSnapshot",
            "req": {
                "coin": "BTC",
                "interval": "1d",
                "startTime": start_ms,
                "endTime": end_ms,
            }
        }).encode()
        req = urllib.request.Request(
            "https://api.hyperliquid.xyz/info",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
        # data is list of [t, o, h, l, c, v, n]  or dict with "t","c" fields
        candles = []
        for row in data:
            if isinstance(row, (list, tuple)) and len(row) >= 5:
                candles.append({"t": int(row[0]), "c": float(row[4])})
            elif isinstance(row, dict):
                candles.append({"t": int(row.get("t", 0)), "c": float(row.get("c", 0))})
        candles.sort(key=lambda x: x["t"])
        return candles
    except Exception as e:
        log.warning("HL candle fetch failed: %s", e)
        return []


def _fetch_bybit_btc_daily(n_days: int = 45) -> List[Dict[str, Any]]:
    """Fallback: Bybit BTC/USDT 1d kline."""
    try:
        import urllib.request
        end_ms   = int(time.time() * 1000)
        start_ms = end_ms - n_days * 86_400_000
        url = (
            f"https://api.bybit.com/v5/market/kline"
            f"?category=spot&symbol=BTCUSDT&interval=D"
            f"&start={start_ms}&end={end_ms}&limit={n_days}"
        )
        with urllib.request.urlopen(url, timeout=15) as resp:
            data = json.loads(resp.read())
        rows = data.get("result", {}).get("list", [])
        # each row: [startTime, open, high, low, close, volume, turnover]
        candles = []
        for row in rows:
            candles.append({"t": int(row[0]), "c": float(row[4])})
        candles.sort(key=lambda x: x["t"])
        return candles
    except Exception as e:
        log.warning("Bybit candle fetch failed: %s", e)
        return []


def fetch_btc_daily_closes(n_days: int = 45) -> List[float]:
    """Return list of BTC daily closes (oldest first), length ≈ n_days."""
    candles = _fetch_hl_btc_daily(n_days)
    if len(candles) < BTC_SMA_PERIOD + 2:
        log.info("HL insufficient (%d candles), trying Bybit …", len(candles))
        candles = _fetch_bybit_btc_daily(n_days)
    if not candles:
        log.error("All BTC candle sources failed")
        return []
    closes = [c["c"] for c in candles if c["c"] > 0]
    log.info("Fetched %d BTC daily closes (last=%.1f)", len(closes), closes[-1] if closes else 0)
    return closes


# ─────────────────────────────────────────────────────────────────────────────
# SMA slope computation
# ─────────────────────────────────────────────────────────────────────────────

def compute_sma(prices: List[float], period: int) -> Optional[float]:
    if len(prices) < period:
        return None
    return sum(prices[-period:]) / period


def compute_slope(closes: List[float]) -> Optional[float]:
    """
    slope = (SMA_today - SMA_20d_ago) / 20
    Requires len(closes) >= 40 (20 for today's SMA + 20 days earlier SMA).
    """
    needed = BTC_SMA_PERIOD * 2
    if len(closes) < needed:
        return None
    sma_today    = compute_sma(closes, BTC_SMA_PERIOD)
    sma_20d_ago  = compute_sma(closes[:-BTC_SMA_PERIOD], BTC_SMA_PERIOD)
    if sma_today is None or sma_20d_ago is None:
        return None
    return (sma_today - sma_20d_ago) / BTC_SMA_PERIOD


# ─────────────────────────────────────────────────────────────────────────────
# Regime classification
# ─────────────────────────────────────────────────────────────────────────────

def classify_regime(slope: float, days_slope_positive: int) -> str:
    if slope >= SLOPE_BULL_THRESH and days_slope_positive >= BULL_CONSEC_DAYS:
        return "BULL_CONFIRMED"
    if SLOPE_TRANSITION_LO < slope < SLOPE_TRANSITION_HI:
        return "TRANSITION"
    if slope <= SLOPE_BEAR_THRESH:
        return "BEAR"
    # slope in [-500, 0) — trending toward bull but not confirmed
    return "BEAR_WEAKENING"


# ─────────────────────────────────────────────────────────────────────────────
# State persistence
# ─────────────────────────────────────────────────────────────────────────────

def load_previous_state() -> Dict[str, Any]:
    if STATUS_FILE.is_file():
        try:
            return json.loads(STATUS_FILE.read_text())
        except Exception:
            pass
    return {
        "regime": "BEAR",
        "days_slope_positive": 0,
        "days_in_regime": 0,
        "trigger_date_jst": None,
        "last_regime": None,
    }


def save_state(state: Dict[str, Any], dry_run: bool = False) -> None:
    if dry_run:
        log.info("[DRY-RUN] would write %s", STATUS_FILE.name)
        return
    STATUS_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False))
    log.info("State saved → %s", STATUS_FILE)


# ─────────────────────────────────────────────────────────────────────────────
# Alerts
# ─────────────────────────────────────────────────────────────────────────────

def append_alert(msg: str, dry_run: bool = False) -> None:
    ts = datetime.datetime.now(JST).strftime("%Y-%m-%d %H:%M JST")
    line = f"[{ts}] {msg}\n"
    log.warning("ALERT: %s", msg)
    if dry_run:
        log.info("[DRY-RUN] would append to alerts.log: %s", msg)
        return
    with ALERTS_LOG.open("a", encoding="utf-8") as f:
        f.write(line)


def generate_activation_alert(state: Dict[str, Any], dry_run: bool = False) -> None:
    """Write k376_activation_alert.md with 5-step activation checklist."""
    now_jst    = datetime.datetime.now(JST).strftime("%Y-%m-%d %H:%M JST")
    slope      = state.get("slope", 0.0)
    days_bull  = state.get("days_slope_positive", 0)
    btc_price  = state.get("btc_price", 0.0)
    sma_today  = state.get("sma_today", 0.0)

    content = f"""# K376 Bull Regime CONFIRMED — Activation Alert

**Generated:** {now_jst}
**Wave:** K497 auto-trigger monitor (31st daemon)

---

## Current Regime Status

| Metric | Value |
|--------|-------|
| Regime | BULL_CONFIRMED |
| BTC 20d SMA slope | +{slope:.1f} $/day |
| Consecutive days slope > 0 | {days_bull} days (threshold: {BULL_CONSEC_DAYS}) |
| BTC price | ${btc_price:,.0f} |
| BTC 20d SMA | ${sma_today:,.0f} |

---

## Profit Impact (K488 Quantification)

| AUM | Sleeve | Annual Lift (when active) |
|-----|--------|--------------------------|
| $10M | 3% | **+$247,000/yr** |
| $10M | 5% | **+$412,000/yr** |
| $100M | 3% | **+$2,470,000/yr** |

**Daily opportunity cost of delay:** ${DAILY_PROFIT_3PCT:,.0f}/day (3% sleeve @$10M)

> K497 automation lag ≤ 1 day. Manual monitoring lag risk: N days × ${DAILY_PROFIT_3PCT:,.0f}/day lost.

---

## 5-Step Activation Checklist

- [ ] **Step 1: Verify regime independently**
  ```bash
  python3 scripts/k376_regime_trigger_monitor.py
  # Confirm: regime = BULL_CONFIRMED, days_slope_positive >= 7
  python3 scripts/k376_momentum_run.py --verbose
  # Confirm: current_regime == "bull"
  ```

- [ ] **Step 2: Check emergency flags and HL concentration**
  ```bash
  ls EMERGENCY_EXIT_TRIGGERED.flag 2>/dev/null && echo "FLAG PRESENT — DO NOT ACTIVATE"
  # HL exposure must be < 65% after K376 addition (check leverage_config.json)
  python3 -c "import json; d=json.load(open('data/leverage_config.json')); print('HL%:', d.get('hl_concentration_pct','?'))"
  ```

- [ ] **Step 3: Load K376 daemon**
  ```bash
  cp com.cryptolab.k376-momentum.plist ~/Library/LaunchAgents/
  launchctl load ~/Library/LaunchAgents/com.cryptolab.k376-momentum.plist
  launchctl list | grep k376-momentum
  ```

- [ ] **Step 4: Confirm first signal fires within 24h (paper trade)**
  ```bash
  tail -f logs/k376_momentum.log
  # Expect: "signal detected" entries within next 5min cycle
  python3 -c "import json; d=json.load(open('data/k376_momentum_dashboard.json')); print('Regime:', d.get('current_regime')); print('Signals 24h:', d.get('recent_signals_24h'))"
  ```

- [ ] **Step 5: Update HTML and monitor G8/G9 gates**
  - Update `report.html` K376 badge: SCAFFOLD-READY → ACTIVE
  - Monitor `fill_rate_60d` (G8 gate: ≥ 65% after 60d paper)
  - After 30d live Sharpe ≥ 1.0: expand sleeve to 5% (v6.20 path)

---

## Position Sizing (K483 1/4 Kelly guidance)

| Phase | Sleeve | Note |
|-------|--------|------|
| Immediate | **3% AUM** (v6.14) | K488 conditional accept |
| 30d live (Sh ≥ 1.0) | 5% AUM (v6.20) | HL concentration check |
| Full Kelly | 35% | BLOCKED: HL cap 65% |

**HL concentration guard:** K376 uses HL executions. Confirm HL% + K376_3% ≤ 65%.
Current HL baseline per K488: ~56%. After adding K376 3%: 59% → OK.

---

## References

| Source | Details |
|--------|---------|
| K488 | Graduation pre-validation ($247K/yr, CONDITIONAL ACCEPT) |
| §38b | K302a runbook activation procedure |
| K497 | This trigger automation (31st daemon) |
| K378 | Original CONDITIONAL_ACCEPT decision |

*Auto-generated by scripts/k376_regime_trigger_monitor.py (K497)*
"""
    if dry_run:
        log.info("[DRY-RUN] would write %s", ACTIVATION_ALERT.name)
        return
    ACTIVATION_ALERT.write_text(content, encoding="utf-8")
    log.warning("ACTIVATION ALERT written → %s", ACTIVATION_ALERT)


# ─────────────────────────────────────────────────────────────────────────────
# Historical backtest (Phase 6)
# ─────────────────────────────────────────────────────────────────────────────

def run_backtest() -> Dict[str, Any]:
    """
    Fetch ~2 years of BTC 1d closes and compute regime transitions.
    Returns summary dict with bull/bear/transition duration distributions.
    """
    log.info("Running 2-year regime backtest …")
    closes = fetch_btc_daily_closes(n_days=730)
    if len(closes) < 60:
        return {"error": "insufficient data", "n_closes": len(closes)}

    # Compute daily slopes for all available windows
    results: List[Dict[str, Any]] = []
    for i in range(BTC_SMA_PERIOD * 2, len(closes) + 1):
        window = closes[:i]
        slope  = compute_slope(window)
        if slope is None:
            continue
        results.append({"day_idx": i, "slope": slope, "close": window[-1]})

    # Count consecutive positive slope days
    bull_runs: List[int] = []
    bear_runs: List[int] = []
    current_sign   = None
    current_length = 0
    for r in results:
        sign = "bull" if r["slope"] >= 0 else "bear"
        if sign == current_sign:
            current_length += 1
        else:
            if current_sign is not None:
                (bull_runs if current_sign == "bull" else bear_runs).append(current_length)
            current_sign   = sign
            current_length = 1
    if current_sign is not None:
        (bull_runs if current_sign == "bull" else bear_runs).append(current_length)

    n_bull = len(bull_runs)
    n_bear = len(bear_runs)
    avg_bull = sum(bull_runs) / n_bull if n_bull else 0
    avg_bear = sum(bear_runs) / n_bear if n_bear else 0
    total_days = sum(bull_runs) + sum(bear_runs)
    bull_fraction = sum(bull_runs) / total_days if total_days else 0

    # Trigger frequency: how often slope positive for ≥ BULL_CONSEC_DAYS
    trigger_count = sum(1 for r in bull_runs if r >= BULL_CONSEC_DAYS)
    n_years = total_days / 365.0
    triggers_per_year = trigger_count / n_years if n_years > 0 else 0

    # Profit quantification with regime-weighted activation
    expected_annual_k376 = K376_ANNUAL_PROFIT_3PCT * bull_fraction
    # Lag savings: manual lag ~7d avg vs automation lag ≤1d
    lag_days_saved = 6  # 7d manual - 1d auto
    lag_savings_per_trigger = DAILY_PROFIT_3PCT * lag_days_saved
    annual_lag_savings = lag_savings_per_trigger * triggers_per_year

    summary = {
        "n_closes_analyzed": len(closes),
        "n_years_approx": round(n_years, 2),
        "bull_runs_count": n_bull,
        "bear_runs_count": n_bear,
        "avg_bull_duration_days": round(avg_bull, 1),
        "avg_bear_duration_days": round(avg_bear, 1),
        "bull_fraction_pct": round(bull_fraction * 100, 1),
        "bear_fraction_pct": round((1 - bull_fraction) * 100, 1),
        "bull_confirmed_triggers_per_year": round(triggers_per_year, 2),
        "k376_expected_annual_profit_regime_weighted_usd": int(expected_annual_k376),
        "k376_max_annual_profit_all_bull_usd": K376_ANNUAL_PROFIT_3PCT,
        "lag_savings_per_trigger_usd": int(lag_savings_per_trigger),
        "annual_lag_savings_usd": int(annual_lag_savings),
        "automation_vs_manual_note": (
            f"Automation lag ≤1d; manual lag est. ~7d. "
            f"At {triggers_per_year:.1f} triggers/yr: "
            f"~${annual_lag_savings:,.0f}/yr saved by K497 automation."
        ),
    }
    log.info("Backtest complete: %s", json.dumps(summary, indent=2))
    return summary


# ─────────────────────────────────────────────────────────────────────────────
# Main monitoring logic
# ─────────────────────────────────────────────────────────────────────────────

def run_monitor(dry_run: bool = False) -> Dict[str, Any]:
    now_jst     = datetime.datetime.now(JST)
    now_jst_str = now_jst.strftime("%Y-%m-%d %H:%M JST")

    closes = fetch_btc_daily_closes(n_days=50)
    if len(closes) < BTC_SMA_PERIOD * 2:
        error_state = {
            "regime": "UNKNOWN",
            "error": f"insufficient data: {len(closes)} closes",
            "last_checked_jst": now_jst_str,
            "version": VERSION,
        }
        save_state(error_state, dry_run=dry_run)
        return error_state

    slope     = compute_slope(closes)
    sma_today = compute_sma(closes, BTC_SMA_PERIOD)
    btc_price = closes[-1]

    prev      = load_previous_state()
    prev_regime = prev.get("regime", "BEAR")
    days_pos  = prev.get("days_slope_positive", 0)
    days_in   = prev.get("days_in_regime", 0)

    # Update consecutive positive slope counter
    if slope is not None and slope >= 0:
        days_pos += 1
    else:
        days_pos = 0

    regime = classify_regime(slope or 0.0, days_pos)

    if regime != prev_regime:
        days_in = 1
    else:
        days_in += 1

    # Build output state
    days_until_trigger: Optional[int] = None
    if regime in ("TRANSITION", "BEAR_WEAKENING") and slope is not None and slope >= 0:
        remaining = max(0, BULL_CONSEC_DAYS - days_pos)
        days_until_trigger = remaining

    state: Dict[str, Any] = {
        "regime": regime,
        "slope": round(slope, 2) if slope is not None else None,
        "sma_today": round(sma_today, 2) if sma_today is not None else None,
        "btc_price": round(btc_price, 2),
        "days_slope_positive": days_pos,
        "days_in_regime": days_in,
        "days_until_bull_confirmed": days_until_trigger,
        "last_regime": prev_regime,
        "trigger_date_jst": prev.get("trigger_date_jst"),
        "last_checked_jst": now_jst_str,
        "version": VERSION,
        "daemon_label": DAEMON_LABEL,
        "profit_unlocked_when_bull": {
            "10M_3pct_per_yr_usd": K376_ANNUAL_PROFIT_3PCT,
            "10M_5pct_per_yr_usd": K376_ANNUAL_PROFIT_5PCT,
            "100M_3pct_per_yr_usd": K376_ANNUAL_PROFIT_100M,
            "daily_value_usd": round(DAILY_PROFIT_3PCT, 0),
        },
    }

    # Regime transition alerts
    if regime == "BULL_CONFIRMED" and prev_regime != "BULL_CONFIRMED":
        state["trigger_date_jst"] = now_jst_str
        append_alert(
            f"K376 BULL_CONFIRMED! slope={slope:.1f} $/day, "
            f"days_positive={days_pos}. "
            f"Activate K376 now for +${K376_ANNUAL_PROFIT_3PCT:,}/yr. "
            f"See data/k376_activation_alert.md",
            dry_run=dry_run,
        )
        generate_activation_alert({**state, "slope": slope or 0.0, "btc_price": btc_price, "sma_today": sma_today or 0.0}, dry_run=dry_run)

    elif regime == "TRANSITION" and prev_regime in ("BEAR", "BEAR_WEAKENING"):
        append_alert(
            f"K376 regime TRANSITION (slope={slope:.1f}, approaching bull). "
            f"Days until BULL_CONFIRMED: ~{days_until_trigger} days.",
            dry_run=dry_run,
        )
    elif regime == "BEAR_WEAKENING" and prev_regime == "BEAR":
        append_alert(
            f"K376 BEAR_WEAKENING detected (slope={slope:.1f}, days_pos={days_pos}). "
            f"Monitoring for BULL_CONFIRMED in ~{BULL_CONSEC_DAYS - days_pos} more days.",
            dry_run=dry_run,
        )

    save_state(state, dry_run=dry_run)

    # Append to history JSONL (non-critical)
    if not dry_run:
        try:
            with STATE_HISTORY.open("a", encoding="utf-8") as f:
                f.write(json.dumps({"date": now_jst.strftime("%Y-%m-%d"), **state}) + "\n")
        except Exception:
            pass

    log.info(
        "Regime: %s | slope: %s | days_pos: %d | btc: $%.0f | sma: $%.0f",
        regime,
        f"{slope:.1f}" if slope is not None else "n/a",
        days_pos,
        btc_price,
        sma_today or 0,
    )
    return state


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(description="K376 Bull Regime Trigger Monitor (K497)")
    parser.add_argument("--dry-run", action="store_true", help="No file writes")
    parser.add_argument("--backtest", action="store_true", help="Run 2-year backtest and exit")
    parser.add_argument("--verbose", action="store_true", help="Extra debug output")
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    if args.backtest:
        result = run_backtest()
        print(json.dumps(result, indent=2))
        return 0

    state = run_monitor(dry_run=args.dry_run)
    if args.verbose or args.dry_run:
        print(json.dumps(state, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
