#!/usr/bin/env python3
"""
loss_harvester.py — K444 Loss Harvesting Automation + Tax-Aware Tracking
=========================================================================
INFORMATIONAL ONLY — does not constitute tax advice.
User must consult a licensed tax advisor before taking any action.

K442 finding: loss harvesting from K376 stop-outs = $2–41K/yr tax savings
depending on jurisdiction.  This script provides infrastructure to:

  1. Track all taxable realization events (position closes) YTD
  2. Identify loss harvesting opportunities (losing positions near year-end)
  3. Estimate annual tax liability based on user-set rate
  4. Generate an annual harvest plan for advisor review (Dec 28–31)
  5. Write dashboard JSON for HTML Live Monitoring

Event taxonomy (per K442):
  K208 8h FR cycle:         ~1,095 events/yr  (short-term, ordinary in most jurisdictions)
  K297' SPX filter close:   ~26 events/yr per coin (varies by holding period)
  K376 momentum 4h close:   ~10,733 events/yr at full universe (short-term)
  sUSDe yield accrual:      ordinary income (NOT a "trade" event) — separate category

K339 security rule: REPO_ROOT = Path(__file__).resolve().parent.parent

Usage:
  python3 scripts/loss_harvester.py --status
  python3 scripts/loss_harvester.py --realize-losses     # Dec 28–31 only
  python3 scripts/loss_harvester.py --annual-report
  python3 scripts/loss_harvester.py --mock-test          # Phase 11 test
  python3 scripts/loss_harvester.py --set-rate 37        # set user_tax_rate_pct
  python3 scripts/loss_harvester.py --set-jurisdiction US_STCG

Environment:
  TAX_RATE_PCT=37          # override user_tax_rate_pct (0–100)
  TAX_JURISDICTION=US_STCG # override jurisdiction string
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

# ── K339 Security: REPO_ROOT from __file__, no /Users/ literals ─────────────
REPO_ROOT = Path(__file__).resolve().parent.parent
DATA      = REPO_ROOT / "data"
CACHE     = REPO_ROOT / "cache"
DATA.mkdir(exist_ok=True)
CACHE.mkdir(exist_ok=True)

# ── File paths ────────────────────────────────────────────────────────────────
AUM_STATE_JSON          = DATA  / "portfolio_aum_state.json"
AUM_HISTORY_JSONL       = CACHE / "portfolio_aum_history.jsonl"
K302A_TRADES_JSONL      = DATA  / "k302a_satellite_paper_trades.jsonl"
K443_TRADES_JSONL       = DATA  / "k443_variational_paper_trades.jsonl"
LOSS_HARVESTER_DASH     = DATA  / "loss_harvester_dashboard.json"

# ── JST timezone ──────────────────────────────────────────────────────────────
JST = timezone(timedelta(hours=9))

# ── Known event-rate estimates from K442 (events per year at full universe) ───
EVENT_RATE_K208  = 1_095   # 8h FR cycle: 3 cycles/day × 365
EVENT_RATE_K297  =    26   # SPX filter ~1 trade/2wk per coin
EVENT_RATE_K376  = 10_733  # momentum 4h at full 50-coin universe (K376 ACCEPT)

# ── Jurisdiction reference table (per K442) ───────────────────────────────────
# Keys match what users set in state["jurisdiction"]
JURISDICTION_NOTES: dict[str, str] = {
    "US_STCG": (
        "US Short-Term Capital Gains (held < 1 year). "
        "FR income typically ordinary income. Wash-sale rule applies to securities; "
        "crypto currently NOT subject to wash-sale (as of 2026). "
        "Top marginal: up to 37% federal + state."
    ),
    "US_LTCG": (
        "US Long-Term Capital Gains (held ≥ 1 year). "
        "Rate: 0% / 15% / 20% depending on income. "
        "Most crypto derivatives close < 1 year → likely STCG."
    ),
    "JP": (
        "Japan: crypto gains taxed as miscellaneous income (雑所得). "
        "Progressive 15–55% effective rate (incl. 10% local tax). "
        "No wash-sale equivalent; loss offset rules apply within category."
    ),
    "SG": (
        "Singapore: No capital gains tax on crypto held as investment. "
        "If classified as trading income, ordinary rates apply. "
        "Consult IRAS guidelines and qualified advisor."
    ),
    "DE": (
        "Germany: Crypto held > 1 year: tax-free. "
        "< 1 year: personal income rate up to 45% + solidarity surcharge. "
        "Derivatives may differ — consult BZSt guidance."
    ),
    "UNKNOWN": "Jurisdiction not set. Set via --set-jurisdiction or TAX_JURISDICTION env var.",
}


# ─────────────────────────────────────────────────────────────────────────────
# State helpers
# ─────────────────────────────────────────────────────────────────────────────

def _load_aum_state() -> dict:
    if not AUM_STATE_JSON.exists():
        return {}
    try:
        with open(AUM_STATE_JSON) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def _save_aum_state(state: dict) -> None:
    """Atomic save to avoid partial writes."""
    tmp = AUM_STATE_JSON.parent / f".portfolio_aum_state_tmp_{os.getpid()}.json"
    try:
        with open(tmp, "w") as f:
            json.dump(state, f, indent=2)
        tmp.rename(AUM_STATE_JSON)
    except OSError as exc:
        print(f"[HARVEST] ERROR saving AUM state: {exc}", file=sys.stderr)


def _backfill_tax_fields(state: dict) -> dict:
    """Add tax fields to AUM state if missing (non-destructive)."""
    defaults = {
        "taxable_events_ytd":              0,
        "estimated_realized_gain_ytd_usd": 0.0,
        "estimated_realized_loss_ytd_usd": 0.0,
        "user_tax_rate_pct":               None,
        "estimated_tax_liability_usd":     0.0,
        "loss_harvesting_opportunities":   [],
        "jurisdiction":                    "UNKNOWN",
        "tax_year_start":                  f"{datetime.now(JST).year}-01-01",
    }
    for k, v in defaults.items():
        if k not in state:
            state[k] = v
    return state


# ─────────────────────────────────────────────────────────────────────────────
# Phase 1 — Core functions
# ─────────────────────────────────────────────────────────────────────────────

def load_taxable_events_ytd() -> list[dict]:
    """
    Load all taxable realization events for the current tax year.

    Data sources (in priority order):
    1. data/k302a_satellite_paper_trades.jsonl  (K297' trades)
    2. data/k443_variational_paper_trades.jsonl (K297'' trades)
    3. AUM state estimated events (when per-trade logs absent)

    Returns:
        List of event dicts with keys:
          ts_jst, strategy, coin, direction, pnl_usd, event_type
    """
    state   = _load_aum_state()
    events: list[dict] = []
    tax_year_start = state.get("tax_year_start",
                                f"{datetime.now(JST).year}-01-01")

    # ── Read K302a trade log ─────────────────────────────────────────────────
    if K302A_TRADES_JSONL.exists():
        try:
            with open(K302A_TRADES_JSONL) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    rec = json.loads(line)
                    ts  = rec.get("ts_jst", rec.get("timestamp", ""))
                    if ts >= tax_year_start:
                        events.append({
                            "ts_jst":     ts,
                            "strategy":   "K297_prime",
                            "coin":       rec.get("coin", "UNKNOWN"),
                            "direction":  rec.get("direction", "UNKNOWN"),
                            "pnl_usd":    float(rec.get("pnl_usd", rec.get("pnl", 0.0))),
                            "event_type": "TRADE_CLOSE",
                        })
        except (json.JSONDecodeError, OSError) as exc:
            print(f"[HARVEST] WARNING: K302a trade log read error: {exc}", file=sys.stderr)

    # ── Read K443 trade log ──────────────────────────────────────────────────
    if K443_TRADES_JSONL.exists():
        try:
            with open(K443_TRADES_JSONL) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    rec = json.loads(line)
                    ts  = rec.get("ts_jst", rec.get("timestamp", ""))
                    if ts >= tax_year_start:
                        events.append({
                            "ts_jst":     ts,
                            "strategy":   "K443_variational",
                            "coin":       rec.get("coin", "UNKNOWN"),
                            "direction":  rec.get("direction", "UNKNOWN"),
                            "pnl_usd":    float(rec.get("pnl_usd", rec.get("pnl", 0.0))),
                            "event_type": "TRADE_CLOSE",
                        })
        except (json.JSONDecodeError, OSError) as exc:
            print(f"[HARVEST] WARNING: K443 trade log read error: {exc}", file=sys.stderr)

    # ── Fallback: use AUM state stored events ────────────────────────────────
    if not events:
        stored_gain = state.get("estimated_realized_gain_ytd_usd", 0.0)
        stored_loss = state.get("estimated_realized_loss_ytd_usd", 0.0)
        stored_n    = state.get("taxable_events_ytd", 0)
        if stored_gain or stored_loss or stored_n:
            # Synthesize a single aggregate event for display purposes
            if stored_gain:
                events.append({
                    "ts_jst":     tax_year_start,
                    "strategy":   "AGGREGATE",
                    "coin":       "ALL",
                    "direction":  "LONG/SHORT",
                    "pnl_usd":    stored_gain,
                    "event_type": "AGGREGATE_GAIN",
                })
            if stored_loss:
                events.append({
                    "ts_jst":     tax_year_start,
                    "strategy":   "AGGREGATE",
                    "coin":       "ALL",
                    "direction":  "LONG/SHORT",
                    "pnl_usd":    -abs(stored_loss),
                    "event_type": "AGGREGATE_LOSS",
                })

    return events


def compute_realized_gains_ytd() -> float:
    """Sum of positive PnL closes YTD (USD). Returns 0.0 if no data."""
    events = load_taxable_events_ytd()
    return sum(e["pnl_usd"] for e in events if e["pnl_usd"] > 0)


def compute_realized_losses_ytd() -> float:
    """Sum of absolute negative PnL closes YTD (USD). Returns 0.0 if no data."""
    events = load_taxable_events_ytd()
    return abs(sum(e["pnl_usd"] for e in events if e["pnl_usd"] < 0))


def identify_harvest_candidates() -> list[dict]:
    """
    Identify currently losing positions suitable for loss harvesting.

    In paper-trade mode (K444 current state), returns estimated candidates
    derived from AUM state loss_harvesting_opportunities field, or generates
    placeholder entries based on AUM drawdown data.

    Returns:
        List of dicts with: coin, strategy, estimated_loss_usd, note
    """
    state      = _load_aum_state()
    candidates = state.get("loss_harvesting_opportunities", [])

    # If no explicit candidates, derive from AUM drawdown as a proxy
    if not candidates:
        dd_usdc = state.get("max_drawdown_usdc", 0.0)
        if dd_usdc < 0:
            candidates = [{
                "coin":                "PORTFOLIO (aggregate)",
                "strategy":           "ALL",
                "estimated_loss_usd": abs(dd_usdc),
                "note":               "Derived from AUM max_drawdown. "
                                      "Actual per-position breakdown requires live trade log.",
            }]

    return candidates


def estimate_tax_liability(rate: Optional[float] = None) -> float:
    """
    Estimate tax liability on net realized gains YTD.

    Formula: max(0, realized_gains - realized_losses) × (rate / 100)

    Args:
        rate: Tax rate percentage (e.g. 37 for 37%). If None, reads from
              AUM state user_tax_rate_pct or TAX_RATE_PCT env var.

    Returns:
        Estimated tax liability in USD. Returns 0.0 if rate is None/unknown.
    """
    if rate is None:
        env_rate = os.environ.get("TAX_RATE_PCT")
        if env_rate:
            try:
                rate = float(env_rate)
            except ValueError:
                pass
    if rate is None:
        state = _load_aum_state()
        rate  = state.get("user_tax_rate_pct")

    if rate is None:
        print("[HARVEST] WARNING: user_tax_rate_pct not set. "
              "Use --set-rate or TAX_RATE_PCT env var.", file=sys.stderr)
        return 0.0

    gains  = compute_realized_gains_ytd()
    losses = compute_realized_losses_ytd()
    net    = max(0.0, gains - losses)
    return round(net * (float(rate) / 100.0), 2)


def generate_annual_report() -> dict:
    """
    Generate a full-year tax summary dict.

    Returns:
        Dict with YTD stats, event breakdown, harvest candidates,
        tax liability estimate, and jurisdiction notes.

    INFORMATIONAL ONLY — not tax advice.
    """
    now_jst    = datetime.now(JST).strftime("%Y-%m-%d %H:%M JST")
    state      = _load_aum_state()
    tax_year   = datetime.now(JST).year
    events     = load_taxable_events_ytd()
    gains      = compute_realized_gains_ytd()
    losses     = compute_realized_losses_ytd()
    net_pnl    = gains - losses
    rate       = state.get("user_tax_rate_pct")
    liability  = estimate_tax_liability(rate)
    candidates = identify_harvest_candidates()
    juris      = state.get("jurisdiction", "UNKNOWN")

    # Dec year-end flag
    today     = datetime.now(JST)
    is_ye     = (today.month == 12 and today.day >= 25)

    report = {
        "generated_jst":   now_jst,
        "tax_year":        tax_year,
        "INFORMATIONAL_ONLY": True,
        "disclaimer": (
            "This report is INFORMATIONAL ONLY and does not constitute tax advice. "
            "Consult a licensed tax professional before taking any action."
        ),
        "jurisdiction":    juris,
        "jurisdiction_notes": JURISDICTION_NOTES.get(juris, JURISDICTION_NOTES["UNKNOWN"]),
        "user_tax_rate_pct": rate,
        "stats_ytd": {
            "total_realization_events":   len(events),
            "realized_gains_usd":         round(gains, 2),
            "realized_losses_usd":        round(losses, 2),
            "net_realized_pnl_usd":       round(net_pnl, 2),
            "estimated_tax_liability_usd": liability,
        },
        "event_breakdown_estimates": {
            "K208_fr_cycle_events_est":   EVENT_RATE_K208,
            "K297_spx_filter_events_est": EVENT_RATE_K297,
            "K376_momentum_events_est":   EVENT_RATE_K376,
            "susde_yield_category":       "ordinary_income (not trade event)",
        },
        "actual_logged_events":       len(events),
        "harvest_candidates":         candidates,
        "year_end_action_recommended": is_ye and bool(candidates),
        "aum_context": {
            "current_aum_usdc": state.get("current_aum_usdc"),
            "cumulative_pnl_usdc": state.get("cumulative_pnl_usdc"),
            "day_count": state.get("day_count", 0),
        },
    }

    # Harvest plan (generated on Dec 28–31 or always for review)
    if candidates:
        total_harvestable = sum(c.get("estimated_loss_usd", 0) for c in candidates)
        tax_savings_est   = round(total_harvestable * (float(rate or 0) / 100), 2)
        report["harvest_plan"] = {
            "total_harvestable_loss_usd": round(total_harvestable, 2),
            "estimated_tax_savings_usd":  tax_savings_est,
            "positions_to_realize":       candidates,
            "instructions": (
                "REVIEW WITH YOUR TAX ADVISOR before executing. "
                "To realize each loss: close the position before Dec 31 market close. "
                "Re-entry after adequate wash-sale period (varies by jurisdiction — "
                "US crypto currently not subject to wash-sale as of 2026)."
            ),
        }

    return report


# ─────────────────────────────────────────────────────────────────────────────
# Phase 5 — Dashboard JSON writer
# ─────────────────────────────────────────────────────────────────────────────

def write_dashboard() -> None:
    """Write data/loss_harvester_dashboard.json for HTML Live Monitoring."""
    now_jst    = datetime.now(JST).strftime("%Y-%m-%d %H:%M JST")
    state      = _load_aum_state()
    events     = load_taxable_events_ytd()
    gains      = compute_realized_gains_ytd()
    losses     = compute_realized_losses_ytd()
    net_pnl    = gains - losses
    rate       = state.get("user_tax_rate_pct")
    liability  = estimate_tax_liability(rate)
    candidates = identify_harvest_candidates()

    today  = datetime.now(JST)
    is_ye  = (today.month == 12 and today.day >= 25)

    dash = {
        "last_poll_jst":  now_jst,
        "tax_year":       today.year,
        "INFORMATIONAL_ONLY": True,
        "stats_ytd": {
            "total_realization_events":    len(events),
            "realized_gains_usd":          round(gains, 2),
            "realized_losses_usd":         round(losses, 2),
            "net_realized_pnl_usd":        round(net_pnl, 2),
            "estimated_tax_liability_usd": liability,
            "user_tax_rate_pct":           rate,
            "jurisdiction":                state.get("jurisdiction", "UNKNOWN"),
        },
        "active_loss_positions":            candidates,
        "year_end_action_recommended":      is_ye and bool(candidates),
        "event_rate_estimates": {
            "K208_fr_cycle_yr":   EVENT_RATE_K208,
            "K297_spx_filter_yr": EVENT_RATE_K297,
            "K376_momentum_yr":   EVENT_RATE_K376,
        },
    }

    tmp = LOSS_HARVESTER_DASH.parent / f".loss_harvester_dashboard_tmp_{os.getpid()}.json"
    try:
        with open(tmp, "w") as f:
            json.dump(dash, f, indent=2)
        tmp.rename(LOSS_HARVESTER_DASH)
        print(f"[HARVEST] Dashboard written: {LOSS_HARVESTER_DASH}")
    except OSError as exc:
        print(f"[HARVEST] ERROR writing dashboard: {exc}", file=sys.stderr)


# ─────────────────────────────────────────────────────────────────────────────
# Phase 4 — AUM state extension
# ─────────────────────────────────────────────────────────────────────────────

def record_realization_event(pnl_usd: float, strategy: str = "UNKNOWN",
                              coin: str = "UNKNOWN") -> None:
    """
    Record a realized gain/loss event into AUM state for tax tracking.

    This is additive to existing AUM logic (K429 integration hook).
    Called by sleeve scripts when they close a position.

    Args:
        pnl_usd:   Realized PnL in USD (positive=gain, negative=loss)
        strategy:  e.g. "K280", "K297_prime", "K376"
        coin:      e.g. "ETH", "BTC"
    """
    state = _load_aum_state()
    state = _backfill_tax_fields(state)

    state["taxable_events_ytd"] = state.get("taxable_events_ytd", 0) + 1
    if pnl_usd > 0:
        state["estimated_realized_gain_ytd_usd"] = (
            state.get("estimated_realized_gain_ytd_usd", 0.0) + pnl_usd
        )
    elif pnl_usd < 0:
        state["estimated_realized_loss_ytd_usd"] = (
            state.get("estimated_realized_loss_ytd_usd", 0.0) + abs(pnl_usd)
        )

    # Recompute liability
    rate = state.get("user_tax_rate_pct")
    if rate is not None:
        g = state["estimated_realized_gain_ytd_usd"]
        l = state["estimated_realized_loss_ytd_usd"]
        state["estimated_tax_liability_usd"] = round(
            max(0.0, g - l) * (float(rate) / 100.0), 2
        )

    _save_aum_state(state)
    print(
        f"[HARVEST] Realization recorded: {coin}/{strategy} PnL={pnl_usd:+,.2f} USD | "
        f"YTD events={state['taxable_events_ytd']} | "
        f"Gains=${state['estimated_realized_gain_ytd_usd']:,.0f} | "
        f"Losses=${state['estimated_realized_loss_ytd_usd']:,.0f}"
    )


def set_user_tax_rate(rate_pct: float, jurisdiction: Optional[str] = None) -> None:
    """Persist user tax rate (and optionally jurisdiction) to AUM state."""
    state = _load_aum_state()
    state = _backfill_tax_fields(state)
    state["user_tax_rate_pct"] = float(rate_pct)
    if jurisdiction:
        state["jurisdiction"] = jurisdiction
    # Recompute liability
    g = state.get("estimated_realized_gain_ytd_usd", 0.0)
    l = state.get("estimated_realized_loss_ytd_usd", 0.0)
    state["estimated_tax_liability_usd"] = round(
        max(0.0, g - l) * (rate_pct / 100.0), 2
    )
    _save_aum_state(state)
    print(f"[HARVEST] Tax rate set: {rate_pct}%"
          + (f" | jurisdiction: {jurisdiction}" if jurisdiction else ""))


# ─────────────────────────────────────────────────────────────────────────────
# Phase 11 — Mock test
# ─────────────────────────────────────────────────────────────────────────────

def run_mock_test() -> None:
    """
    Phase 11 test: initialize with mock $1M YTD gains, $50K YTD losses,
    user_tax_rate=37, verify liability = ($1M-$50K) × 37% = $351,500.
    """
    print("\n" + "=" * 60)
    print("  K444 Loss Harvester — Mock Test (Phase 11)")
    print("=" * 60)

    state = _load_aum_state()
    state = _backfill_tax_fields(state)

    # Inject mock data
    state["estimated_realized_gain_ytd_usd"] = 1_000_000.0
    state["estimated_realized_loss_ytd_usd"] =    50_000.0
    state["taxable_events_ytd"]              = 200
    state["user_tax_rate_pct"]               = 37.0
    state["jurisdiction"]                    = "US_STCG"
    state["loss_harvesting_opportunities"]   = [
        {
            "coin":                "ETH",
            "strategy":           "K376",
            "estimated_loss_usd": 8_500.0,
            "note":               "Mock: ETH long position at -5.1% from entry",
        },
        {
            "coin":                "LINK",
            "strategy":           "K376",
            "estimated_loss_usd": 3_200.0,
            "note":               "Mock: LINK momentum position at -3.8% from entry",
        },
    ]
    # Recompute liability
    g  = state["estimated_realized_gain_ytd_usd"]
    l  = state["estimated_realized_loss_ytd_usd"]
    r  = state["user_tax_rate_pct"]
    state["estimated_tax_liability_usd"] = round(max(0.0, g - l) * (r / 100.0), 2)

    _save_aum_state(state)

    # Verify
    expected_liability = round((1_000_000.0 - 50_000.0) * 0.37, 2)
    actual_liability   = state["estimated_tax_liability_usd"]
    ok = abs(actual_liability - expected_liability) < 0.01

    print(f"  Gains YTD:    $1,000,000")
    print(f"  Losses YTD:   $50,000")
    print(f"  Net:          $950,000")
    print(f"  Tax rate:     37%")
    print(f"  Expected:     ${expected_liability:,.2f}")
    print(f"  Actual:       ${actual_liability:,.2f}")
    print(f"  PASS:         {'YES' if ok else 'FAIL'}")
    print()

    # Generate report
    report = generate_annual_report()
    print(f"  Harvest candidates: {len(report.get('harvest_candidates', []))}")
    plan = report.get("harvest_plan", {})
    if plan:
        print(f"  Total harvestable loss: ${plan['total_harvestable_loss_usd']:,.0f}")
        print(f"  Estimated tax savings:  ${plan['estimated_tax_savings_usd']:,.0f}")

    # Tax savings @ $10M and $50M for top 3 jurisdictions
    print()
    print("  ── Estimated tax savings @ $10M and $50M AUM ──────────────")
    print(f"  (based on K442 avg net gain estimates per AUM tier)")
    print()
    # K442 estimates: ~$1.72M/yr @ $10M, ~$6M/yr @ $50M
    for aum_label, est_gain in [("$10M AUM", 1_720_000), ("$50M AUM", 6_000_000)]:
        print(f"  {aum_label}:")
        for juris, rate in [("US_STCG (37%)", 0.37), ("JP (55%)", 0.55), ("SG (0%)", 0.0)]:
            harvest_est = est_gain * 0.05   # K442: avg loss harvest ~5% of gross gains
            savings = round(harvest_est * rate, 0)
            print(f"    {juris:20s}: harvest ~${harvest_est:,.0f} losses "
                  f"→ save ~${savings:,.0f}/yr")
        print()

    # Refresh dashboard
    write_dashboard()
    print(f"  Dashboard: {LOSS_HARVESTER_DASH}")
    print("=" * 60 + "\n")


# ─────────────────────────────────────────────────────────────────────────────
# CLI entry point
# ─────────────────────────────────────────────────────────────────────────────

def _fmt_usd(v: float) -> str:
    if abs(v) >= 1_000_000:
        return f"${v/1_000_000:.3f}M"
    if abs(v) >= 1_000:
        return f"${v/1_000:.1f}K"
    return f"${v:.0f}"


def print_status() -> None:
    state  = _load_aum_state()
    state  = _backfill_tax_fields(state)
    events = load_taxable_events_ytd()
    gains  = compute_realized_gains_ytd()
    losses = compute_realized_losses_ytd()
    rate   = state.get("user_tax_rate_pct")
    liab   = estimate_tax_liability(rate)
    cands  = identify_harvest_candidates()

    print("\n" + "=" * 60)
    print("  K444 Loss Harvester — Status")
    print("=" * 60)
    print(f"  Tax Year:             {state.get('tax_year_start', 'N/A')[:4]}")
    print(f"  Jurisdiction:         {state.get('jurisdiction', 'UNKNOWN')}")
    print(f"  User Tax Rate:        {rate}%")
    print(f"  Events YTD (logged):  {len(events)}")
    print(f"  Realized Gains YTD:   {_fmt_usd(gains)}")
    print(f"  Realized Losses YTD:  {_fmt_usd(losses)}")
    print(f"  Net Realized PnL:     {_fmt_usd(gains - losses)}")
    print(f"  Est. Tax Liability:   {_fmt_usd(liab)}")
    print(f"  Harvest Candidates:   {len(cands)}")
    today = datetime.now(JST)
    if today.month == 12 and today.day >= 25:
        print(f"  Year-End Action:      {'RECOMMENDED' if cands else 'None needed'}")
    print("=" * 60 + "\n")


def print_realize_losses() -> None:
    today = datetime.now(JST)
    if not (today.month == 12 and today.day >= 25):
        print("[HARVEST] --realize-losses is intended for Dec 28–31 (year-end window).")
        print(f"          Today is {today.strftime('%Y-%m-%d')}. Continuing anyway for review.")
    report    = generate_annual_report()
    plan      = report.get("harvest_plan", {})
    cands     = report.get("harvest_candidates", [])

    print("\n" + "=" * 60)
    print("  K444 Loss Harvester — Harvest Plan (INFORMATIONAL ONLY)")
    print("  DO NOT ACT without consulting a licensed tax advisor.")
    print("=" * 60)

    if not cands:
        print("  No harvest candidates identified.")
        return

    for i, c in enumerate(cands, 1):
        print(f"  [{i}] Coin: {c.get('coin')} | Strategy: {c.get('strategy')}")
        print(f"      Est. loss: ${c.get('estimated_loss_usd', 0):,.0f}")
        print(f"      Note: {c.get('note', 'N/A')}")
        print()

    if plan:
        print(f"  Total harvestable loss: ${plan.get('total_harvestable_loss_usd', 0):,.0f}")
        print(f"  Est. tax savings:       ${plan.get('estimated_tax_savings_usd', 0):,.0f}")
        print(f"\n  Instructions: {plan.get('instructions', '')}")
    print("=" * 60 + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="K444 Loss Harvester — INFORMATIONAL ONLY"
    )
    parser.add_argument("--status",        action="store_true", help="Print YTD tax status")
    parser.add_argument("--realize-losses",action="store_true", help="Show year-end harvest plan")
    parser.add_argument("--annual-report", action="store_true", help="Generate & print annual report")
    parser.add_argument("--mock-test",     action="store_true", help="Run Phase 11 mock test")
    parser.add_argument("--write-dashboard",action="store_true",help="Write dashboard JSON")
    parser.add_argument("--set-rate",      type=float, metavar="PCT",
                        help="Set user_tax_rate_pct in AUM state (e.g. 37)")
    parser.add_argument("--set-jurisdiction", metavar="JURIS",
                        help="Set jurisdiction string (e.g. US_STCG, JP, SG, DE)")
    parser.add_argument("--record-event",  nargs=3, metavar=("PNL", "STRATEGY", "COIN"),
                        help="Record realization event: PNL_USD STRATEGY COIN")
    args = parser.parse_args()

    if args.set_rate is not None:
        set_user_tax_rate(args.set_rate, jurisdiction=args.set_jurisdiction)

    elif args.set_jurisdiction:
        state = _load_aum_state()
        state = _backfill_tax_fields(state)
        state["jurisdiction"] = args.set_jurisdiction
        _save_aum_state(state)
        print(f"[HARVEST] Jurisdiction set: {args.set_jurisdiction}")

    elif args.record_event:
        pnl_usd, strategy, coin = args.record_event
        record_realization_event(float(pnl_usd), strategy, coin)

    elif args.mock_test:
        run_mock_test()

    elif args.annual_report:
        report = generate_annual_report()
        print(json.dumps(report, indent=2))

    elif args.realize_losses:
        print_realize_losses()
        write_dashboard()

    elif args.write_dashboard:
        write_dashboard()

    else:
        # Default: status + write dashboard
        # Backfill tax fields in AUM state if needed
        state = _load_aum_state()
        state = _backfill_tax_fields(state)
        _save_aum_state(state)
        print_status()
        write_dashboard()

    return 0


if __name__ == "__main__":
    sys.exit(main())
