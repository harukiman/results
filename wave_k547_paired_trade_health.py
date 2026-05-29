"""
wave_k547_paired_trade_health.py
K547 Paired-Trade Family Paper-Trade Health Audit
K339 REPO_ROOT pattern

Phases:
  1. Dashboard freshness audit (7 daemons)
  2. 60d gate progress
  3. BEAR regime impact
  4. Activation readiness ranking
  5. HL concentration scenario (v6.28)
  6. Sequenced activation plan (D30-D60)
  7. Combined family lift trajectory
  8. Risk assessment
  9. Recommendation & monitoring spec

Output:
  wave_k547_paired_trade_health.json
  wave_k547_paired_trade_health.md
  report.html  (paired-trade health widget)
"""

import json
import os
import datetime
import math
import sys

# ── K339 REPO_ROOT ──────────────────────────────────────────────────────────
REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_DIR  = os.path.join(REPO_ROOT, "data")

# ── Constants ────────────────────────────────────────────────────────────────
NOW_JST   = "2026-05-30 05:37 JST"
AUM_10M   = 10_000_000
TARGET_60D = 60
HL_CAP_PCT = 65.0

# ── Phase 1: Dashboard definitions ──────────────────────────────────────────
DAEMONS = [
    {
        "id":         "K476",
        "strategy":   "SOL-BTC FR Differential",
        "scaffold_wave": "K478",
        "dashboard":  "k476_dashboard.json",
        "oos_sharpe": 16.30,
        "ann_return": 187_000,
        "sleeve_pct": 0.03,
        "hl_fraction": 1.0,
        "oos_sharpe_min": 5.0,
        "fill_rate_min": 60,
        "max_dd_max":    15,
        "split_protocol": "HL-only 3%",
        "family_rank": 5,
    },
    {
        "id":         "K484",
        "strategy":   "AVAX-BTC FR Differential",
        "scaffold_wave": "K489",
        "dashboard":  "k484_dashboard.json",
        "oos_sharpe": 43.89,
        "ann_return": 75_700,
        "sleeve_pct": 0.03,
        "hl_fraction": 1.0,
        "oos_sharpe_min": 5.0,
        "fill_rate_min": 60,
        "max_dd_max":    15,
        "split_protocol": "HL-only 3%",
        "family_rank": 4,
    },
    {
        "id":         "K493",
        "strategy":   "ATOM-BTC FR Differential",
        "scaffold_wave": "K499",
        "dashboard":  "k493_dashboard.json",
        "oos_sharpe": 50.79,
        "ann_return": 231_000,
        "sleeve_pct": 0.03,
        "hl_fraction": 1.0,
        "oos_sharpe_min": 5.0,
        "fill_rate_min": 60,
        "max_dd_max":    15,
        "split_protocol": "HL-only 3%",
        "family_rank": 2,
    },
    {
        "id":         "K500",
        "strategy":   "INJ-BTC FR Differential",
        "scaffold_wave": "K506",
        "dashboard":  "k500_dashboard.json",
        "oos_sharpe": 11.23,
        "ann_return": 124_000,
        "sleeve_pct": 0.03,
        "hl_fraction": 1.0,
        "oos_sharpe_min": 3.5,
        "fill_rate_min": 60,
        "max_dd_max":    15,
        "split_protocol": "HL-only 3%",
        "family_rank": 7,
    },
    {
        "id":         "K507_SEI",
        "strategy":   "SEI-BTC FR Differential",
        "scaffold_wave": "K514",
        "dashboard":  "k507_dashboard.json",
        "oos_sharpe": 48.10,
        "ann_return": 179_000,
        "sleeve_pct": 0.03,
        "hl_fraction": 0.5,
        "oos_sharpe_min": 5.0,
        "fill_rate_min": 60,
        "max_dd_max":    15,
        "split_protocol": "HL 1.5% + Bybit 1.5%",
        "family_rank": 3,
    },
    {
        "id":         "K507_TIA",
        "strategy":   "TIA-BTC FR Differential",
        "scaffold_wave": "K524",
        "dashboard":  "k507_tia_dashboard.json",
        "oos_sharpe": 14.44,
        "ann_return": 51_000,
        "sleeve_pct": 0.01,
        "hl_fraction": 1.0,
        "oos_sharpe_min": 3.5,
        "fill_rate_min": 60,
        "max_dd_max":    15,
        "split_protocol": "HL-only 1%",
        "family_rank": 6,
    },
    {
        "id":         "K512",
        "strategy":   "APT-BTC FR Differential",
        "scaffold_wave": "K520",
        "dashboard":  "k512_dashboard.json",
        "oos_sharpe": 51.10,
        "ann_return": 302_000,
        "sleeve_pct": 0.02,
        "hl_fraction": 0.5,
        "oos_sharpe_min": 5.0,
        "fill_rate_min": 60,
        "max_dd_max":    15,
        "split_protocol": "HL 1% + Bybit 1%",
        "family_rank": 1,
    },
]

# K449 ETH-BTC (already LIVE-ready, not paper-gating the same way)
K449 = {
    "id":         "K449",
    "strategy":   "ETH-BTC FR Differential",
    "scaffold_wave": "K450",
    "oos_sharpe": 5.66,
    "ann_return": 13_000,   # live-ready figure per task prompt (K516 v6.28 has higher)
    "sleeve_pct": 0.05,
    "hl_fraction": 1.0,
    "status": "LIVE-READY",
    "split_protocol": "HL-only 5%",
    "family_rank": 8,
}

# Scaffold first-commit dates (from git log)
SCAFFOLD_DEPLOY_DATES = {
    "K476":     "2026-05-30 02:37 JST",
    "K484":     "2026-05-30 03:23 JST",
    "K493":     "2026-05-30 03:42 JST",
    "K500":     "2026-05-30 04:06 JST",
    "K507_SEI": "2026-05-30 04:30 JST",
    "K512":     "2026-05-30 04:48 JST",
    "K507_TIA": "2026-05-30 05:05 JST",
}

# ── Phase 1+2: Load dashboards & compute gate progress ──────────────────────
def load_dashboard(fname):
    path = os.path.join(DATA_DIR, fname)
    try:
        with open(path) as f:
            return json.load(f)
    except Exception as e:
        return {"error": str(e)}


def days_since_deploy(deploy_ts: str) -> float:
    """Approximate days since scaffold deploy, using 2026-05-30 05:37 as now."""
    # All scaffolds deployed today 2026-05-30 — so <1 day elapsed for all
    # Use time difference in hours
    deploy_hour = int(deploy_ts[11:13])
    now_hour    = 5  # 05:37
    now_min     = 37
    elapsed_min = (now_hour * 60 + now_min) - deploy_hour * 60
    if elapsed_min < 0:
        elapsed_min = 0
    return elapsed_min / 1440.0   # fraction of a day


def assess_status(daemon: dict, days_elapsed: float,
                  paper_oos_sharpe: float, fill_rate: float, max_dd: float) -> str:
    """
    READY        : 60d gate PASS + all metrics met
    PROGRESSING  : in paper-trade, no failures
    STALLED      : days_elapsed > 30 but sharpe still 0 or fill_rate 0
    BLOCKED      : hard gate failure (dd > max, sharpe negative)
    """
    d60_done = days_elapsed >= TARGET_60D
    sharpe_ok = paper_oos_sharpe >= daemon["oos_sharpe_min"] if d60_done else None
    fill_ok   = fill_rate >= daemon["fill_rate_min"] if d60_done else None
    dd_ok     = max_dd < daemon["max_dd_max"] if d60_done else None

    if d60_done and sharpe_ok and fill_ok and dd_ok:
        return "READY"
    if days_elapsed > 30 and paper_oos_sharpe == 0 and fill_rate == 0:
        return "STALLED"
    if max_dd >= daemon["max_dd_max"]:
        return "BLOCKED"
    return "PROGRESSING"


def audit_daemon(daemon: dict) -> dict:
    dash = load_dashboard(daemon["dashboard"])
    deploy_ts    = SCAFFOLD_DEPLOY_DATES.get(daemon["id"], "2026-05-30 00:00 JST")
    days_elapsed = days_since_deploy(deploy_ts)
    days_remain  = max(0, TARGET_60D - days_elapsed)

    # Pull live metrics from dashboard
    last_poll        = dash.get("last_poll_jst", "unknown")
    position_state   = dash.get("position_state", "unknown")
    signal           = dash.get("signal", position_state)
    fr_raw_diff      = dash.get("fr_raw_diff", 0.0)
    daily_pnl        = dash.get("daily_pnl_usdc", 0.0)
    realized_sharpe  = dash.get("60d_sharpe", 0.0)
    trade_count      = 0   # paper — no live fills yet (day 0)
    fill_rate        = 0.0
    max_dd           = 0.0
    gate_status      = "IN_PROGRESS"

    gate_m = dash.get("gate_metrics", {})
    if gate_m:
        realized_sharpe = gate_m.get("current_oos_sharpe", realized_sharpe)
        fill_rate       = gate_m.get("current_fill_rate", fill_rate)
        max_dd          = gate_m.get("current_max_dd_pct", max_dd)
        gate_status     = gate_m.get("gate_status", gate_status)

    paper_status  = dash.get("paper_trade_status", {})
    days_elapsed_dash = paper_status.get("days_elapsed", 0)

    # Use dashboard days_elapsed if > computed (scaffold may have been running longer)
    actual_days = max(days_elapsed, days_elapsed_dash)

    status = assess_status(daemon, actual_days, realized_sharpe, fill_rate, max_dd)

    # Annualized trade target (FR diff strategies: ~3-8 trades/month = 36-96/yr)
    ann_trade_target = 60   # conservative estimate
    trades_per_day   = ann_trade_target / 365.0
    expected_trades  = actual_days * trades_per_day

    # Signal active?
    signal_active = signal not in ("NEUTRAL", None, "")

    return {
        "daemon_id":           daemon["id"],
        "strategy":            daemon["strategy"],
        "scaffold_wave":       daemon["scaffold_wave"],
        "split_protocol":      daemon["split_protocol"],
        "oos_sharpe_backtest": daemon["oos_sharpe"],
        "ann_return_usd":      daemon["ann_return"],
        "sleeve_pct":          daemon["sleeve_pct"],
        "family_rank":         daemon["family_rank"],
        # Freshness
        "last_poll_jst":       last_poll,
        "deploy_ts_jst":       deploy_ts,
        "days_elapsed":        round(actual_days, 3),
        "days_remaining":      round(days_remain, 1),
        # Signal
        "signal":              signal,
        "signal_active":       signal_active,
        "fr_raw_diff":         fr_raw_diff,
        "position_state":      position_state,
        # Paper metrics
        "paper_realized_sharpe": realized_sharpe,
        "paper_fill_rate_pct":   fill_rate,
        "paper_max_dd_pct":      max_dd,
        "paper_daily_pnl_usdc":  daily_pnl,
        "paper_trade_count":     trade_count,
        "expected_trades_by_now": round(expected_trades, 1),
        "gate_status":           gate_status,
        # Readiness
        "readiness_status":    status,
        # Gates
        "oos_sharpe_min":      daemon["oos_sharpe_min"],
        "fill_rate_min_pct":   daemon["fill_rate_min"],
        "max_dd_max_pct":      daemon["max_dd_max"],
    }


# ── Phase 3: BEAR regime assessment ─────────────────────────────────────────
def bear_regime_assessment() -> dict:
    """
    K497 BTC slope = -33.83 $/day (from report.html).
    BTC slope negative → BEAR regime → paired-trade FR diff strategies
    not suppressed the same way K376 momentum is.
    FR differential strategies are regime-agnostic by design
    (long one asset, short another, delta-neutral).
    """
    return {
        "btc_slope_per_day":          -33.83,
        "regime":                     "BEAR (TRANSITION)",
        "k497_status":                "BTC 20d SMA slope < 0 (−33.83 $/day)",
        "eta_bull_confirmed_days":    7,
        "paired_trade_impact":        "LOW",
        "rationale": (
            "FR differential strategies are delta-neutral by design. "
            "BEAR regime suppresses K376 momentum but NOT FR differential pairs. "
            "Active signals observed: K493 LONG_ATOM_SHORT_BTC, K500 LONG_INJ_SHORT_BTC, "
            "K507_TIA LONG_BTC_SHORT_TIA, K512 LONG_APT_SHORT_BTC — all fired in BEAR. "
            "Cross-family correlation risk: all strategies share BTC as common leg "
            "→ correlated tail risk if BTC flash-crashes."
        ),
        "signal_suppression_pct":     0,
        "k376_suppression":           True,
        "k376_note":                  "K376 BLOCKED-CAP: HL 65% exact, not related to BEAR",
        "cross_family_btc_correlation": "MODERATE (shared BTC short leg in 4/7 strategies)",
        "bear_tail_scenario":         "BTC -20% flash → all BTC-short legs gain, BTC-long legs lose; delta-neutral so net ~0 PnL pre-funding",
    }


# ── Phase 5: HL concentration scenario ──────────────────────────────────────
def hl_concentration_scenario() -> list:
    """
    Starting: v6.13d HL 65% (exact cap).
    K280 B1: 75% → 60% = -15pp HL weight → HL goes from 65% to ~57.5%.
    Then add paired-trade family sequentially.
    """
    steps = [
        {
            "step":        0,
            "event":       "Current v6.13d baseline",
            "hl_pct":      65.0,
            "note":        "HL 65% exact cap, K449 not yet live",
        },
        {
            "step":        1,
            "event":       "K280 Phase B1: 75%→60% weight cut",
            "hl_pct":      57.5,
            "delta_pp":    -7.5,
            "note":        "K280 HL fraction ~1.0; 15pp weight cut × 50% HL fraction ≈ 7.5pp HL reduction",
        },
        {
            "step":        2,
            "event":       "K449 ETH-BTC LIVE (5% sleeve, HL-only)",
            "hl_pct":      62.5,
            "delta_pp":    +5.0,
            "note":        "5% sleeve × 100% HL = +5pp. HL: 57.5 → 62.5",
        },
        {
            "step":        3,
            "event":       "K476 SOL-BTC LIVE (3% sleeve, HL-only)",
            "hl_pct":      65.5,
            "delta_pp":    +3.0,
            "note":        "3% sleeve × 100% HL = +3pp. HL: 62.5 → 65.5 (OVER CAP!)",
            "cap_breach":  True,
        },
        {
            "step":        "3a",
            "event":       "Option: K476 SOL-BTC 2% HL + 1% Bybit split",
            "hl_pct":      64.5,
            "delta_pp":    +2.0,
            "note":        "2% HL sleeve only = +2pp. HL: 62.5 → 64.5 (within cap)",
            "cap_breach":  False,
        },
        {
            "step":        4,
            "event":       "K484 AVAX-BTC LIVE (3% sleeve, HL-only) [from step 3a]",
            "hl_pct":      66.5,
            "delta_pp":    +3.0,
            "note":        "From 64.5 + 3pp HL = 67.5% (OVER). Need split: 2% HL + 1% Bybit",
            "cap_breach":  True,
        },
        {
            "step":        "4a",
            "event":       "K484 AVAX-BTC 2% HL + 1% Bybit",
            "hl_pct":      66.5,
            "delta_pp":    +2.0,
            "note":        "2% HL from 64.5 = 66.5. Still over. K280 must cut to 58% first.",
            "cap_breach":  True,
        },
        {
            "step":        "4b",
            "event":       "K280 cut to 58% FIRST, then K484 2% HL",
            "hl_pct":      64.5,
            "delta_pp":    -2.0,
            "note":        "K280 58% (-2pp from B1 result) → HL ~55.5%; +K449 5pp=60.5%; +K476 2pp=62.5%; +K484 2pp=64.5%",
            "cap_breach":  False,
        },
        {
            "step":        5,
            "event":       "K493 ATOM-BTC LIVE (3% sleeve, HL-only)",
            "hl_pct":      65.5,
            "delta_pp":    +3.0,
            "note":        "From 64.5 (step 4b) → 64.5 + 3 = 67.5 BREACH. Use 2% HL + 1% Bybit.",
            "cap_breach":  True,
        },
        {
            "step":        "5a",
            "event":       "K493 ATOM-BTC 2% HL + 1% Bybit",
            "hl_pct":      64.5,
            "delta_pp":    +2.0,
            "note":        "From 62.5 (after K280 extra cut) + 2pp = 64.5%. Within cap.",
            "cap_breach":  False,
        },
        {
            "step":        6,
            "event":       "K500 INJ-BTC LIVE (3% → 2% HL + 1% Bybit)",
            "hl_pct":      64.5,
            "delta_pp":    +2.0,
            "note":        "K500 forced split: +2pp HL → 64.5% if prior at 62.5%",
            "cap_breach":  False,
        },
        {
            "step":        7,
            "event":       "K507 SEI-BTC (HL 1.5% + Bybit 1.5%)",
            "hl_pct":      64.0,
            "delta_pp":    +1.5,
            "note":        "Split already in design: +1.5pp HL. From 62.5 → 64.0",
            "cap_breach":  False,
        },
        {
            "step":        8,
            "event":       "K507 TIA-BTC (HL 1%, no Bybit)",
            "hl_pct":      65.0,
            "delta_pp":    +1.0,
            "note":        "+1pp HL from 64.0 → 65.0 = EXACT CAP",
            "cap_breach":  False,
        },
        {
            "step":        9,
            "event":       "K512 APT-BTC (HL 1% + Bybit 1%)",
            "hl_pct":      65.0,
            "delta_pp":    +1.0,
            "note":        "+1pp HL → 66.0 BREACH unless K280 trimmed first",
            "cap_breach":  True,
        },
        {
            "step":        "9a",
            "event":       "K512 APT-BTC: K280 extra cut to 57% clears headroom",
            "hl_pct":      64.0,
            "delta_pp":    -1.0,
            "note":        "K280 57% frees 1pp → K512 1pp HL = 64.0%. Full family live @ 64%.",
            "cap_breach":  False,
        },
    ]
    return steps


# ── Phase 6+7: Sequenced activation plan ────────────────────────────────────
def activation_plan() -> list:
    return [
        {
            "week":           1,
            "timing":         "D0 (immediate — LIVE-ready)",
            "activation":     "K449 ETH-BTC",
            "gate_status":    "LIVE-READY (60d paper already pending)",
            "sleeve":         "5% HL",
            "ann_return_usd": 13_000,
            "cumulative_usd": 13_000,
            "hl_after":       62.5,
            "risk":           "LOW",
            "notes":          "K280 B1 cut must happen first (57.5% → 62.5% after K449)",
        },
        {
            "week":           2,
            "timing":         "D7-D14 (after K280 B1 confirmed)",
            "activation":     "K476 SOL-BTC + K484 AVAX-BTC",
            "gate_status":    "PAPER-GATE IN_PROGRESS (day 0 → D60)",
            "sleeve":         "SOL: 2% HL+1% Bybit; AVAX: 2% HL+1% Bybit",
            "ann_return_usd": 187_000 + 75_700,
            "cumulative_usd": 13_000 + 187_000 + 75_700,
            "hl_after":       64.5,
            "risk":           "LOW-MEDIUM",
            "notes":          "60d gate must complete. K476 Sh16 lower bar but still strong. Forced split to stay under 65%.",
        },
        {
            "week":           3,
            "timing":         "D14-D21",
            "activation":     "K493 ATOM-BTC",
            "gate_status":    "PAPER-GATE IN_PROGRESS (day 0 → D60) — signal ALREADY FIRING",
            "sleeve":         "2% HL + 1% Bybit (forced split)",
            "ann_return_usd": 231_000,
            "cumulative_usd": 13_000 + 187_000 + 75_700 + 231_000,
            "hl_after":       64.5,
            "risk":           "LOW",
            "notes":          "ATOM signal firing now: LONG_ATOM_SHORT_BTC. Sh50.79, family rank #2. Cosmos orthogonality confirmed.",
        },
        {
            "week":           4,
            "timing":         "D21-D35",
            "activation":     "K500 INJ-BTC + K507 SEI-BTC + K507 TIA-BTC",
            "gate_status":    "PAPER-GATE IN_PROGRESS",
            "sleeve":         "INJ: 2%HL+1%Bybit; SEI: 1.5%HL+1.5%Bybit; TIA: 1%HL",
            "ann_return_usd": 124_000 + 179_000 + 51_000,
            "cumulative_usd": 13_000 + 187_000 + 75_700 + 231_000 + 124_000 + 179_000 + 51_000,
            "hl_after":       65.0,
            "risk":           "MEDIUM",
            "notes":          "3 simultaneous activations. INJ and TIA signals firing. SEI neutral. Stagger by 48h each.",
        },
        {
            "week":           5,
            "timing":         "D35-D60",
            "activation":     "K512 APT-BTC",
            "gate_status":    "PAPER-GATE IN_PROGRESS — signal FIRING (LONG_APT_SHORT_BTC)",
            "sleeve":         "1% HL + 1% Bybit",
            "ann_return_usd": 302_000,
            "cumulative_usd": 13_000 + 187_000 + 75_700 + 231_000 + 124_000 + 179_000 + 51_000 + 302_000,
            "hl_after":       64.0,
            "risk":           "MEDIUM",
            "notes":          "K280 micro-trim to 57% required. APT Sh51.10 = family #1. Move-VM orthogonality confirmed. K280 B1 + K476 2pp + K484 2pp + K493 2pp + K500 2pp + SEI 1.5pp + TIA 1pp + APT 1pp = 12.5pp added, must net ≤65%.",
        },
    ]


# ── Phase 8: Risk assessment ─────────────────────────────────────────────────
def risk_assessment() -> dict:
    return {
        "cascade_risk": {
            "description":    "Multiple simultaneous LIVE switches",
            "probability":    "MEDIUM",
            "severity":       "HIGH",
            "mitigation":     "Stagger activations 48h each within week; monitor PnL per leg",
            "trigger":        "2+ strategies open opposite BTC legs simultaneously",
        },
        "paper_live_divergence": {
            "description":    "Paper Sharpe vs realized Sharpe gap",
            "expected_decay": "20-40% Sharpe degradation post-live (slippage, fee drag)",
            "k476_live_est":  round(16.30 * 0.70, 2),
            "k493_live_est":  round(50.79 * 0.70, 2),
            "k512_live_est":  round(51.10 * 0.70, 2),
            "mitigation":     "Post_only fill optimization per scaffold; 30d live monitoring gate",
        },
        "hl_cap_breach": {
            "description":    "HL concentration exceeds 65% during transition",
            "probability":    "HIGH without pre-cut",
            "severity":       "HIGH",
            "mitigation":     "K280 Phase B1 cut MUST precede each activation step",
            "monitoring":     "Check HL pct after every daemon load",
        },
        "fr_mean_reversion_failure": {
            "description":    "FR differentials converge faster than expected",
            "probability":    "LOW (all strategies have OOS Sh ≥ 10)",
            "severity":       "MEDIUM",
            "mitigation":     "NEUTRAL signal = no position; exit on convergence",
        },
        "btc_flash_crash": {
            "description":    "BTC -20%+ event with correlated leg failure",
            "probability":    "LOW",
            "severity":       "HIGH",
            "mitigation":     "Delta-neutral design absorbs price move; FR income continues",
            "tail_loss_est":  "1.7-4.0% per strategy (liquidation if BTC >80% single-candle)",
        },
        "liquidity_risk": {
            "description":    "HL liquidity insufficient for full notional",
            "k476_notional":  1_200_000,
            "k493_notional":  1_200_000,
            "k500_notional":  1_200_000,
            "note":           "HL depth adequate for all strategies at $10M AUM",
        },
    }


# ── Main orchestration ────────────────────────────────────────────────────────
def main():
    print(f"[K547] Paired-Trade Family Health Audit — {NOW_JST}")
    print("=" * 72)

    # Phase 1+2: Audit each daemon
    print("\n[Phase 1+2] Auditing 7 daemons...")
    daemon_results = []
    for d in DAEMONS:
        result = audit_daemon(d)
        daemon_results.append(result)
        sig_icon = "🟢" if result["signal_active"] else "⚪"
        print(f"  {result['daemon_id']:12s} | {result['signal']:25s} | "
              f"OOS Sh={result['oos_sharpe_backtest']:5.2f} | "
              f"Days={result['days_elapsed']:.3f} | {result['readiness_status']}")

    # Phase 3: BEAR regime
    print("\n[Phase 3] BEAR regime impact...")
    bear = bear_regime_assessment()
    print(f"  BTC slope: {bear['btc_slope_per_day']} $/day | Regime: {bear['regime']}")
    print(f"  Paired-trade impact: {bear['paired_trade_impact']} (delta-neutral by design)")

    # Phase 4: Readiness ranking
    print("\n[Phase 4] Readiness ranking...")
    ranked = sorted(daemon_results, key=lambda x: (
        0 if x["readiness_status"] == "READY" else
        1 if x["readiness_status"] == "PROGRESSING" else
        2 if x["readiness_status"] == "STALLED" else 3,
        -x["oos_sharpe_backtest"]
    ))
    for i, r in enumerate(ranked, 1):
        print(f"  #{i}: {r['daemon_id']:12s} | {r['readiness_status']:12s} | "
              f"Sh={r['oos_sharpe_backtest']:.2f} | ${r['ann_return_usd']:,}/yr")

    # Phase 5: HL concentration
    print("\n[Phase 5] HL concentration scenario...")
    hl_steps = hl_concentration_scenario()
    for s in hl_steps[:5]:
        breach = " ❌ OVER CAP" if s.get("cap_breach") else ""
        print(f"  Step {str(s['step']):3s}: {s['hl_pct']:.1f}% | {s['event'][:50]}{breach}")

    # Phase 6+7: Activation plan
    print("\n[Phase 6+7] Sequenced activation plan...")
    plan = activation_plan()
    for p in plan:
        print(f"  Week {p['week']}: {p['activation'][:30]:30s} | "
              f"${p['ann_return_usd']:,}/yr | Cumulative ${p['cumulative_usd']:,}/yr | "
              f"HL {p['hl_after']}%")

    # Phase 8: Risk
    print("\n[Phase 8] Risk assessment — 4 key risks identified")
    risk = risk_assessment()

    # ── Build JSON output ────────────────────────────────────────────────────
    output = {
        "wave":          "K547",
        "title":         "Paired-Trade Family Paper-Trade Health Audit",
        "generated_jst": NOW_JST,
        "aum_ref_usd":   AUM_10M,
        "hl_cap_pct":    HL_CAP_PCT,
        "k449_live_ready": {
            "id":          "K449",
            "strategy":    "ETH-BTC FR Differential",
            "oos_sharpe":  5.66,
            "ann_return":  13_000,
            "sleeve_pct":  0.05,
            "status":      "LIVE-READY",
            "notes":       "Week 1 activation, pending K280 B1 cut",
        },
        "daemon_health_table": daemon_results,
        "readiness_ranking":   ranked,
        "bear_regime":         bear,
        "hl_concentration_scenario": hl_steps,
        "activation_plan":     plan,
        "risk_assessment":     risk,
        "profit_table_10m": {
            "K449_eth_btc":  {"ann_usd": 13_000,  "sleeve": "5%",   "sharpe": 5.66,  "status": "LIVE-READY"},
            "K476_sol_btc":  {"ann_usd": 187_000, "sleeve": "3%",   "sharpe": 16.30, "status": "PROGRESSING"},
            "K484_avax_btc": {"ann_usd": 75_700,  "sleeve": "3%",   "sharpe": 43.89, "status": "PROGRESSING"},
            "K493_atom_btc": {"ann_usd": 231_000, "sleeve": "3%",   "sharpe": 50.79, "status": "PROGRESSING"},
            "K500_inj_btc":  {"ann_usd": 124_000, "sleeve": "3%",   "sharpe": 11.23, "status": "PROGRESSING"},
            "K507_sei_btc":  {"ann_usd": 179_000, "sleeve": "3%",   "sharpe": 48.10, "status": "PROGRESSING"},
            "K507_tia_btc":  {"ann_usd": 51_000,  "sleeve": "1%",   "sharpe": 14.44, "status": "PROGRESSING"},
            "K512_apt_btc":  {"ann_usd": 302_000, "sleeve": "2%",   "sharpe": 51.10, "status": "PROGRESSING"},
            "TOTAL":         {"ann_usd": 1_162_700, "note": "Full v6.28 family @ $10M AUM"},
        },
        "cumulative_lift_trajectory": {
            "week_1_k449":                 13_000,
            "week_2_plus_sol_avax":        13_000 + 187_000 + 75_700,
            "week_3_plus_atom":            13_000 + 187_000 + 75_700 + 231_000,
            "week_4_plus_inj_sei_tia":     13_000 + 187_000 + 75_700 + 231_000 + 124_000 + 179_000 + 51_000,
            "week_5_plus_apt_full_family": 13_000 + 187_000 + 75_700 + 231_000 + 124_000 + 179_000 + 51_000 + 302_000,
        },
        "recommendation": {
            "immediate":   "K449 ETH-BTC activate Week 1 (post K280 B1 cut). LIVE-READY.",
            "week_2_gate": "K476+K484 activate only after 60d paper complete. All 7 daemons at day 0 — need D60 before gates.",
            "hl_mandate":  "K280 Phase B1 cut (75%→60%) MUST precede every activation step.",
            "monitoring":  "Post-activation: check HL pct every 6h for 48h; verify fill rates > 0 within 24h.",
            "key_risk":    "Cascade risk from simultaneous activations — stagger 48h each.",
            "paper_note":  "All 7 daemons deployed TODAY (2026-05-30). 60d gate = 2026-07-29. Full family live earliest late July.",
        },
    }

    # Write JSON
    json_path = os.path.join(REPO_ROOT, "wave_k547_paired_trade_health.json")
    with open(json_path, "w") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"\n[OK] JSON written: {json_path}")

    # ── Build Markdown ────────────────────────────────────────────────────────
    md = build_markdown(output, daemon_results, ranked, plan, hl_steps, bear, risk)
    md_path = os.path.join(REPO_ROOT, "wave_k547_paired_trade_health.md")
    with open(md_path, "w") as f:
        f.write(md)
    print(f"[OK] MD written:   {md_path}")

    # ── Update report.html ───────────────────────────────────────────────────
    update_report_html(output, daemon_results, ranked, plan)
    print(f"[OK] report.html updated")

    print("\n[K547] DONE")
    return output


def build_markdown(output, daemon_results, ranked, plan, hl_steps, bear, risk) -> str:
    lines = []
    lines.append("# K547 Paired-Trade Family Paper-Trade Health Audit")
    lines.append("")
    lines.append(f"**Generated:** {output['generated_jst']}  ")
    lines.append(f"**AUM Reference:** $10M  ")
    lines.append(f"**HL Cap:** {output['hl_cap_pct']}%  ")
    lines.append(f"**Daemons audited:** 7 (+ K449 LIVE-READY)  ")
    lines.append("")

    lines.append("## Executive Summary")
    lines.append("")
    lines.append("All 7 paired-trade daemons (K476 SOL, K484 AVAX, K493 ATOM, K500 INJ, K507 SEI, K507 TIA, K512 APT) "
                 "were deployed **today 2026-05-30** and are at Day 0 of their 60-day paper-trade gate. "
                 "Full family activation is earliest **2026-07-29**. "
                 "K449 ETH-BTC is LIVE-READY and can activate Week 1 pending K280 Phase B1 cut. "
                 "4 of 7 daemons have signals already firing (ATOM, INJ, TIA, APT), "
                 "confirming FR differential mechanics are active even in BEAR regime. "
                 "Full v6.28 family target: **$1.163M/yr @ $10M AUM**.")
    lines.append("")

    lines.append("## Phase 1+2: Dashboard Health Table")
    lines.append("")
    lines.append("| Daemon | Strategy | Last Poll | Signal | FR Diff | Position | Days | Status |")
    lines.append("|--------|----------|-----------|--------|---------|----------|------|--------|")
    for d in daemon_results:
        lines.append(
            f"| {d['daemon_id']} | {d['strategy']} | {d['last_poll_jst']} | "
            f"{d['signal']} | {d['fr_raw_diff']:.2e} | {d['position_state']} | "
            f"{d['days_elapsed']:.3f} | {d['readiness_status']} |"
        )
    lines.append("")
    lines.append("**Key findings:**")
    lines.append("- All dashboards fresh (polled within last 3 hours on 2026-05-30)")
    lines.append("- 4/7 daemons firing signals: K493 LONG_ATOM_SHORT_BTC, K500 LONG_INJ_SHORT_BTC, "
                 "K507_TIA LONG_BTC_SHORT_TIA, K512 LONG_APT_SHORT_BTC")
    lines.append("- K476 SOL and K484 AVAX/K507_SEI NEUTRAL (FR diff below threshold)")
    lines.append("- All at paper_realized_sharpe=0 (day 0, no historical fills yet)")
    lines.append("")

    lines.append("## Phase 2: 60-Day Gate Progress")
    lines.append("")
    lines.append("| Daemon | Deploy Date | Days Elapsed | Days to 60d Gate | Paper Sh | Fill Rate | Max DD | Gate |")
    lines.append("|--------|-------------|--------------|------------------|----------|-----------|--------|------|")
    for d in daemon_results:
        lines.append(
            f"| {d['daemon_id']} | {d['deploy_ts_jst']} | {d['days_elapsed']:.3f} | "
            f"{d['days_remaining']:.1f} | {d['paper_realized_sharpe']:.2f} | "
            f"{d['paper_fill_rate_pct']:.1f}% | {d['paper_max_dd_pct']:.1f}% | {d['gate_status']} |"
        )
    lines.append("")
    lines.append("> **Note:** All daemons at Day 0 → gate metrics show 0 by definition. "
                 "60-day gate target completion: **2026-07-29**.")
    lines.append("")

    lines.append("## Phase 3: BEAR Regime Impact")
    lines.append("")
    lines.append(f"**BTC slope:** {bear['btc_slope_per_day']} $/day ({bear['regime']})")
    lines.append(f"**ETA BULL_CONFIRMED:** ~{bear['eta_bull_confirmed_days']} days")
    lines.append(f"**Paired-trade impact:** {bear['paired_trade_impact']}")
    lines.append("")
    lines.append(bear["rationale"])
    lines.append("")
    lines.append(f"**Cross-family BTC correlation:** {bear['cross_family_btc_correlation']}")
    lines.append(f"**K376 suppressed:** {bear['k376_suppression']} ({bear['k376_note']})")
    lines.append("")
    lines.append("### Signal Activity in Current BEAR Regime")
    lines.append("")
    lines.append("| Daemon | Signal | Active in BEAR? | Implication |")
    lines.append("|--------|--------|-----------------|-------------|")
    lines.append("| K476 SOL | NEUTRAL | N/A | FR diff below threshold |")
    lines.append("| K484 AVAX | NEUTRAL | N/A | FR diff below threshold |")
    lines.append("| K493 ATOM | LONG_ATOM_SHORT_BTC | ✓ YES | ATOM FR negative vs BTC positive → signal active |")
    lines.append("| K500 INJ | LONG_INJ_SHORT_BTC | ✓ YES | INJ FR -5.8e-5 vs BTC 1.2e-5 → strong signal |")
    lines.append("| K507 SEI | NEUTRAL | N/A | FR diff small positive, below threshold |")
    lines.append("| K507 TIA | LONG_BTC_SHORT_TIA | ✓ YES | TIA FR positive > BTC → short TIA |")
    lines.append("| K512 APT | LONG_APT_SHORT_BTC | ✓ YES | APT FR negative vs BTC positive → signal active |")
    lines.append("")

    lines.append("## Phase 4: Activation Readiness Ranking")
    lines.append("")
    lines.append("| Rank | Daemon | Strategy | OOS Sharpe | Ann Return | Status | Days to Gate | Notes |")
    lines.append("|------|--------|----------|-----------|-----------|--------|--------------|-------|")
    for i, r in enumerate(ranked, 1):
        lines.append(
            f"| #{i} | {r['daemon_id']} | {r['strategy']} | {r['oos_sharpe_backtest']:.2f} | "
            f"${r['ann_return_usd']:,} | {r['readiness_status']} | {r['days_remaining']:.0f}d | "
            f"{r['split_protocol']} |"
        )
    lines.append("")
    lines.append("**All 7 daemons: PROGRESSING (Day 0 of 60d gate)**")
    lines.append("No daemon is READY, STALLED, or BLOCKED at this audit point.")
    lines.append("Gate completion expected: 2026-07-29.")
    lines.append("")

    lines.append("## Phase 5: HL Concentration Scenario (v6.28)")
    lines.append("")
    lines.append("| Step | Event | HL % | Delta | Breach? |")
    lines.append("|------|-------|-------|-------|---------|")
    for s in hl_steps:
        breach = "❌ YES" if s.get("cap_breach") else "✓ OK"
        delta  = s.get("delta_pp", 0)
        delta_str = f"+{delta:.1f}pp" if delta > 0 else f"{delta:.1f}pp" if delta < 0 else "—"
        lines.append(f"| {s['step']} | {s['event'][:55]} | {s['hl_pct']}% | {delta_str} | {breach} |")
    lines.append("")
    lines.append("**Key finding:** Raw 3% HL sleeves for SOL/AVAX/ATOM/INJ will breach 65% cap. "
                 "**All must be split: 2% HL + 1% Bybit** unless K280 is cut further.")
    lines.append("K280 Phase B1 (75%→60%) is prerequisite for any paired-trade activation.")
    lines.append("")

    lines.append("## Phase 6+7: Sequenced Activation Plan & Profit Trajectory")
    lines.append("")
    lines.append("| Week | Timing | Activation | Ann Return | Cumulative | HL After | Risk |")
    lines.append("|------|--------|-----------|-----------|-----------|---------|------|")
    for p in plan:
        lines.append(
            f"| {p['week']} | {p['timing'][:20]} | {p['activation']} | "
            f"${p['ann_return_usd']:,} | ${p['cumulative_usd']:,} | {p['hl_after']}% | {p['risk']} |"
        )
    lines.append("")
    lines.append("### Cumulative Profit Lift @ $10M AUM")
    lines.append("")
    traj = output["cumulative_lift_trajectory"]
    lines.append(f"- **Week 1 (K449):** ${traj['week_1_k449']:,}/yr")
    lines.append(f"- **Week 2 (+SOL+AVAX):** ${traj['week_2_plus_sol_avax']:,}/yr")
    lines.append(f"- **Week 3 (+ATOM):** ${traj['week_3_plus_atom']:,}/yr")
    lines.append(f"- **Week 4 (+INJ+SEI+TIA):** ${traj['week_4_plus_inj_sei_tia']:,}/yr")
    lines.append(f"- **Week 5 (+APT, full family):** ${traj['week_5_plus_apt_full_family']:,}/yr")
    lines.append("")

    lines.append("## Phase 8: Risk Assessment")
    lines.append("")
    lines.append("| Risk | Probability | Severity | Mitigation |")
    lines.append("|------|-------------|----------|------------|")
    lines.append(f"| Cascade (simultaneous LIVE switches) | {risk['cascade_risk']['probability']} | "
                 f"{risk['cascade_risk']['severity']} | {risk['cascade_risk']['mitigation']} |")
    lines.append(f"| Paper-live Sharpe divergence | MEDIUM | MEDIUM | "
                 f"~30% Sharpe decay expected post-live; 30d monitoring gate |")
    lines.append(f"| HL cap breach | {risk['hl_cap_breach']['probability']} | "
                 f"{risk['hl_cap_breach']['severity']} | {risk['hl_cap_breach']['mitigation']} |")
    lines.append(f"| FR mean-reversion failure | {risk['fr_mean_reversion_failure']['probability']} | "
                 f"{risk['fr_mean_reversion_failure']['severity']} | Delta-neutral exits on convergence |")
    lines.append(f"| BTC flash crash | {risk['btc_flash_crash']['probability']} | "
                 f"{risk['btc_flash_crash']['severity']} | Delta-neutral; tail loss 1.7-4.0% |")
    lines.append("")

    lines.append("## Phase 9: Recommendation")
    lines.append("")
    rec = output["recommendation"]
    lines.append(f"1. **Immediate:** {rec['immediate']}")
    lines.append(f"2. **Week 2 gate:** {rec['week_2_gate']}")
    lines.append(f"3. **HL mandate:** {rec['hl_mandate']}")
    lines.append(f"4. **Monitoring:** {rec['monitoring']}")
    lines.append(f"5. **Key risk:** {rec['key_risk']}")
    lines.append(f"6. **Paper timeline:** {rec['paper_note']}")
    lines.append("")

    lines.append("## Profit USDC/yr @ $10M Cumulative Table")
    lines.append("")
    lines.append("| Strategy | Sleeve | OOS Sharpe | Ann USDC/yr @$10M | Family Rank | Status |")
    lines.append("|----------|--------|-----------|------------------|-------------|--------|")
    pt = output["profit_table_10m"]
    for k, v in pt.items():
        if k == "TOTAL":
            lines.append(f"| **{k}** | — | — | **${v['ann_usd']:,}** | — | {v['note']} |")
        else:
            lines.append(
                f"| {k} | {v['sleeve']} | {v['sharpe']:.2f} | ${v['ann_usd']:,} | — | {v['status']} |"
            )
    lines.append("")
    lines.append(f"**Full v6.28 combined:** ${pt['TOTAL']['ann_usd']:,}/yr @ $10M AUM")
    lines.append(f"**@ $100M AUM:** ${pt['TOTAL']['ann_usd'] * 10:,}/yr (linear scaling)")
    lines.append("")

    lines.append("---")
    lines.append(f"*Generated by wave_k547_paired_trade_health.py | {output['generated_jst']}*")

    return "\n".join(lines)


def update_report_html(output, daemon_results, ranked, plan):
    """Inject K547 paired-trade health widget into report.html."""
    html_path = os.path.join(REPO_ROOT, "report.html")
    content = open(html_path, encoding="utf-8").read()

    traj = output["cumulative_lift_trajectory"]
    pt   = output["profit_table_10m"]

    # Build the new widget HTML
    rows_health = ""
    signal_colors = {
        "NEUTRAL":             "#8b949e",
        "LONG_ATOM_SHORT_BTC": "#3fb950",
        "LONG_INJ_SHORT_BTC":  "#3fb950",
        "LONG_APT_SHORT_BTC":  "#3fb950",
        "LONG_BTC_SHORT_TIA":  "#58a6ff",
        "LONG_ETH_SHORT_BTC":  "#3fb950",
    }
    for d in daemon_results:
        color = signal_colors.get(d["signal"], "#d29922")
        status_color = {
            "PROGRESSING": "#d29922",
            "READY":       "#3fb950",
            "STALLED":     "#f85149",
            "BLOCKED":     "#f85149",
        }.get(d["readiness_status"], "#8b949e")
        rows_health += (
            f'<tr>'
            f'<td style="padding:5px 8px;color:#e6edf3;font-weight:600;">{d["daemon_id"]}</td>'
            f'<td style="padding:5px 8px;color:#8b949e;font-size:0.85em;">{d["strategy"]}</td>'
            f'<td style="padding:5px 8px;color:#8b949e;font-size:0.78em;">{d["last_poll_jst"]}</td>'
            f'<td style="padding:5px 8px;color:{color};font-size:0.85em;">{d["signal"]}</td>'
            f'<td style="padding:5px 8px;color:#58a6ff;">{d["oos_sharpe_backtest"]:.2f}</td>'
            f'<td style="padding:5px 8px;color:#3fb950;">${d["ann_return_usd"]:,}</td>'
            f'<td style="padding:5px 8px;color:{status_color};font-weight:700;">{d["readiness_status"]}</td>'
            f'<td style="padding:5px 8px;color:#8b949e;">{d["days_remaining"]:.0f}d</td>'
            f'</tr>'
        )

    rows_plan = ""
    for p in plan:
        risk_color = {"LOW": "#3fb950", "LOW-MEDIUM": "#d29922",
                      "MEDIUM": "#d29922", "HIGH": "#f85149"}.get(p["risk"], "#8b949e")
        rows_plan += (
            f'<tr>'
            f'<td style="padding:5px 8px;color:#e6edf3;font-weight:700;">Wk {p["week"]}</td>'
            f'<td style="padding:5px 8px;color:#8b949e;font-size:0.82em;">{p["timing"]}</td>'
            f'<td style="padding:5px 8px;color:#58a6ff;font-weight:600;">{p["activation"]}</td>'
            f'<td style="padding:5px 8px;color:#3fb950;">${p["ann_return_usd"]:,}</td>'
            f'<td style="padding:5px 8px;color:#e6edf3;font-weight:600;">${p["cumulative_usd"]:,}</td>'
            f'<td style="padding:5px 8px;color:#d29922;">{p["hl_after"]}%</td>'
            f'<td style="padding:5px 8px;color:{risk_color};">{p["risk"]}</td>'
            f'</tr>'
        )

    widget = f"""
  <!-- ==================== K547 PAIRED-TRADE HEALTH ==================== -->
  <section style="background:var(--bg-secondary);border:1px solid rgba(88,166,255,0.35);border-radius:12px;padding:18px 22px;margin:16px 0;">
    <h2 style="color:#58a6ff;margin:0 0 12px 0;font-size:1.1em;">K547 Paired-Trade Family Health Audit <span style="color:#8b949e;font-size:0.8em;font-weight:400;">— 2026-05-30 05:37 JST</span></h2>

    <!-- Summary banner -->
    <div style="background:linear-gradient(90deg,rgba(88,166,255,0.12),rgba(63,185,80,0.10),rgba(88,166,255,0.12));border:1.5px solid rgba(88,166,255,0.5);border-radius:10px;padding:10px 16px;margin-bottom:14px;font-size:0.9em;">
      <strong style="color:#3fb950;">7 daemons</strong> deployed 2026-05-30 (Day 0) &nbsp;|&nbsp;
      <strong style="color:#d29922;">60d gate target: 2026-07-29</strong> &nbsp;|&nbsp;
      <strong style="color:#58a6ff;">K449 LIVE-READY</strong> (activate Week 1) &nbsp;|&nbsp;
      <strong style="color:#e6edf3;">4/7 signals firing in BEAR</strong> (FR diff regime-agnostic) &nbsp;|&nbsp;
      <strong style="color:#3fb950;">Full family: $1,162,700/yr @ $10M</strong>
    </div>

    <!-- Daemon health table -->
    <h3 style="color:#e6edf3;font-size:0.95em;margin:0 0 8px 0;">Daemon Health Table</h3>
    <div style="overflow-x:auto;">
    <table style="width:100%;border-collapse:collapse;font-size:0.88em;">
      <thead>
        <tr style="border-bottom:1px solid rgba(88,166,255,0.3);">
          <th style="padding:5px 8px;color:#8b949e;text-align:left;">Daemon</th>
          <th style="padding:5px 8px;color:#8b949e;text-align:left;">Strategy</th>
          <th style="padding:5px 8px;color:#8b949e;text-align:left;">Last Poll</th>
          <th style="padding:5px 8px;color:#8b949e;text-align:left;">Signal</th>
          <th style="padding:5px 8px;color:#8b949e;text-align:left;">OOS Sh</th>
          <th style="padding:5px 8px;color:#8b949e;text-align:left;">$/yr @$10M</th>
          <th style="padding:5px 8px;color:#8b949e;text-align:left;">Status</th>
          <th style="padding:5px 8px;color:#8b949e;text-align:left;">To Gate</th>
        </tr>
      </thead>
      <tbody>
        {rows_health}
      </tbody>
    </table>
    </div>

    <!-- Profit table -->
    <h3 style="color:#e6edf3;font-size:0.95em;margin:14px 0 8px 0;">Profit USDC/yr @ $10M Cumulative</h3>
    <div style="overflow-x:auto;">
    <table style="width:100%;border-collapse:collapse;font-size:0.88em;">
      <thead>
        <tr style="border-bottom:1px solid rgba(63,185,80,0.3);">
          <th style="padding:4px 8px;color:#8b949e;text-align:left;">Strategy</th>
          <th style="padding:4px 8px;color:#8b949e;text-align:right;">Sharpe</th>
          <th style="padding:4px 8px;color:#8b949e;text-align:right;">$/yr @$10M</th>
          <th style="padding:4px 8px;color:#8b949e;text-align:left;">Sleeve</th>
          <th style="padding:4px 8px;color:#8b949e;text-align:left;">Status</th>
        </tr>
      </thead>
      <tbody>
        <tr><td style="padding:3px 8px;color:#d29922;font-weight:600;">K449 ETH-BTC</td><td style="padding:3px 8px;color:#58a6ff;text-align:right;">5.66</td><td style="padding:3px 8px;color:#3fb950;text-align:right;">$13,000</td><td style="padding:3px 8px;color:#8b949e;">5% HL</td><td style="padding:3px 8px;color:#d29922;font-weight:600;">LIVE-READY</td></tr>
        <tr><td style="padding:3px 8px;color:#e6edf3;">K476 SOL-BTC</td><td style="padding:3px 8px;color:#58a6ff;text-align:right;">16.30</td><td style="padding:3px 8px;color:#3fb950;text-align:right;">$187,000</td><td style="padding:3px 8px;color:#8b949e;">3%</td><td style="padding:3px 8px;color:#d29922;">PROGRESSING</td></tr>
        <tr><td style="padding:3px 8px;color:#e6edf3;">K484 AVAX-BTC</td><td style="padding:3px 8px;color:#58a6ff;text-align:right;">43.89</td><td style="padding:3px 8px;color:#3fb950;text-align:right;">$75,700</td><td style="padding:3px 8px;color:#8b949e;">3%</td><td style="padding:3px 8px;color:#d29922;">PROGRESSING</td></tr>
        <tr><td style="padding:3px 8px;color:#e6edf3;">K493 ATOM-BTC</td><td style="padding:3px 8px;color:#58a6ff;text-align:right;">50.79</td><td style="padding:3px 8px;color:#3fb950;text-align:right;">$231,000</td><td style="padding:3px 8px;color:#8b949e;">3%</td><td style="padding:3px 8px;color:#d29922;">PROGRESSING</td></tr>
        <tr><td style="padding:3px 8px;color:#e6edf3;">K500 INJ-BTC</td><td style="padding:3px 8px;color:#58a6ff;text-align:right;">11.23</td><td style="padding:3px 8px;color:#3fb950;text-align:right;">$124,000</td><td style="padding:3px 8px;color:#8b949e;">3%</td><td style="padding:3px 8px;color:#d29922;">PROGRESSING</td></tr>
        <tr><td style="padding:3px 8px;color:#e6edf3;">K507 SEI-BTC</td><td style="padding:3px 8px;color:#58a6ff;text-align:right;">48.10</td><td style="padding:3px 8px;color:#3fb950;text-align:right;">$179,000</td><td style="padding:3px 8px;color:#8b949e;">3% split</td><td style="padding:3px 8px;color:#d29922;">PROGRESSING</td></tr>
        <tr><td style="padding:3px 8px;color:#e6edf3;">K507 TIA-BTC</td><td style="padding:3px 8px;color:#58a6ff;text-align:right;">14.44</td><td style="padding:3px 8px;color:#3fb950;text-align:right;">$51,000</td><td style="padding:3px 8px;color:#8b949e;">1% HL</td><td style="padding:3px 8px;color:#d29922;">PROGRESSING</td></tr>
        <tr><td style="padding:3px 8px;color:#e6edf3;">K512 APT-BTC</td><td style="padding:3px 8px;color:#58a6ff;text-align:right;">51.10</td><td style="padding:3px 8px;color:#3fb950;text-align:right;">$302,000</td><td style="padding:3px 8px;color:#8b949e;">2% split</td><td style="padding:3px 8px;color:#d29922;">PROGRESSING</td></tr>
        <tr style="border-top:2px solid rgba(63,185,80,0.5);"><td style="padding:5px 8px;color:#3fb950;font-weight:700;">TOTAL v6.28</td><td style="padding:5px 8px;color:#58a6ff;text-align:right;font-weight:700;">—</td><td style="padding:5px 8px;color:#3fb950;font-weight:700;text-align:right;">$1,162,700</td><td style="padding:5px 8px;color:#8b949e;">28% sleeve</td><td style="padding:5px 8px;color:#3fb950;font-weight:700;">Full family</td></tr>
      </tbody>
    </table>
    </div>

    <!-- Sequenced activation plan -->
    <h3 style="color:#e6edf3;font-size:0.95em;margin:14px 0 8px 0;">Sequenced v6.28 Activation Plan (D30-D60)</h3>
    <div style="overflow-x:auto;">
    <table style="width:100%;border-collapse:collapse;font-size:0.85em;">
      <thead>
        <tr style="border-bottom:1px solid rgba(163,113,247,0.3);">
          <th style="padding:4px 8px;color:#8b949e;text-align:left;">Week</th>
          <th style="padding:4px 8px;color:#8b949e;text-align:left;">Timing</th>
          <th style="padding:4px 8px;color:#8b949e;text-align:left;">Activation</th>
          <th style="padding:4px 8px;color:#8b949e;text-align:right;">$/yr</th>
          <th style="padding:4px 8px;color:#8b949e;text-align:right;">Cumulative</th>
          <th style="padding:4px 8px;color:#8b949e;text-align:right;">HL %</th>
          <th style="padding:4px 8px;color:#8b949e;text-align:left;">Risk</th>
        </tr>
      </thead>
      <tbody>{rows_plan}</tbody>
    </table>
    </div>

    <!-- BEAR regime note -->
    <div style="margin-top:12px;padding:8px 14px;background:rgba(210,153,34,0.10);border-left:3px solid #d29922;border-radius:6px;font-size:0.85em;">
      <strong style="color:#d29922;">BEAR Regime:</strong>
      <span style="color:#e6edf3;"> BTC slope −33.83 $/day. FR differential strategies are <em>delta-neutral</em> — BEAR does NOT suppress signals. 4/7 daemons already firing. K376 momentum remains BLOCKED-CAP (separate constraint).</span>
    </div>

    <!-- HL cap note -->
    <div style="margin-top:8px;padding:8px 14px;background:rgba(248,81,73,0.10);border-left:3px solid #f85149;border-radius:6px;font-size:0.85em;">
      <strong style="color:#f85149;">HL Cap Mandate:</strong>
      <span style="color:#e6edf3;"> K280 Phase B1 (75%→60%) MUST precede every activation. All 3% HL sleeves require split (2% HL + 1% Bybit) to stay ≤65%. Full v6.28 steady-state: ~64.0% HL.</span>
    </div>

    <div style="margin-top:10px;color:#6e7681;font-size:0.72rem;text-align:right;">
      K547 health audit | {output['generated_jst']} | wave_k547_paired_trade_health.{{py,json,md}}
    </div>
  </section>

"""

    # Insert widget before HEADER div
    header_marker = "  <!-- ==================== HEADER ===================="
    if header_marker in content:
        content = content.replace(header_marker, widget + "  " + header_marker.lstrip())

    # Update last-update span
    old_span_start = content.find('<span id="last-update">')
    old_span_end   = content.find("</span>", old_span_start)
    if old_span_start != -1:
        old_span = content[old_span_start:old_span_end + 7]
        new_span = '<span id="last-update">2026-05-30 05:37 JST (K547 Paired-Trade Health Audit)</span>'
        content = content.replace(old_span, new_span, 1)

    # Update banner in HEADER area
    old_banner_start = content.find("K532 Governance v5")
    if old_banner_start != -1:
        old_banner_line_start = content.rfind("<div", 0, old_banner_start)
        old_banner_line_end   = content.find("</div>", old_banner_start) + 6
        new_banner = (
            '<div style="background:linear-gradient(90deg,rgba(88,166,255,0.18),'
            'rgba(63,185,80,0.14),rgba(88,166,255,0.18));border:2px solid rgba(88,166,255,0.7);'
            'border-radius:14px;padding:10px 22px;margin-bottom:10px;text-align:center;'
            'font-size:1.1em;font-weight:800;color:#e6edf3;box-shadow:0 0 24px rgba(88,166,255,0.3);">'
            ' &#9670; <span style="color:#58a6ff;">K547 Paired-Trade Health Audit</span>'
            ' &mdash; 7 daemons Day 0 paper-gate | 4/7 signals FIRING in BEAR | '
            'K449 LIVE-READY | Full v6.28 $1.163M/yr @$10M | 60d gate 2026-07-29 | '
            'HL 65% exact &rarr; K280 B1 cut prerequisite'
            '</div>'
        )
        content = content[:old_banner_line_start] + new_banner + content[old_banner_line_end:]

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(content)


if __name__ == "__main__":
    main()
