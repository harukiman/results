#!/usr/bin/env python3
"""
K485 Multi-Account Scaling Activation Playbook
===============================================
Wave: K485 | Generated: 2026-05-30 02:54 JST
Mandate: feedback_profit_max_priority axis #5 — Multi-account scaling capacity expansion

Key findings from K431 (corrected) + K454 + K458 + K461:
- Multi-account on SAME venue = ZERO capacity benefit + possible ToS risk (CEX)
- HL is a non-KYC DEX; multiple wallets are technically unrestricted
- Capacity expansion requires multi-VENUE (separate order books)
- Phase 1: 1→2 venues ($10M→$25M): +$2.1M/yr (100% lift)
- Phase 2: 2→3 venues ($25M→$50M): +$3.37M/yr (162% lift)
- Phase 3: v6.20 7 venues ($100M): +$46.1M/yr (K454 depth-aware required)
- Phase 4: v6.20 10 venues ($200M): +$72.4M/yr (K461 accepted conditional)
"""

import json
import math
import os
import sys
from datetime import datetime, timezone
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict

# ─── REPO_ROOT pattern (K339) ───────────────────────────────────────────────
REPO_ROOT = os.path.dirname(os.path.abspath(__file__))

# ─── Model Parameters (from K431 confirmed data) ────────────────────────────
DAILY_MU           = 0.00027422   # K346 daily mean return
DAILY_SIGMA        = 0.00020567   # daily vol
K426_NET_ANN_RET   = 0.3328       # 3x leverage net ann return (K426)
PAXG_OI_USD        = 15_000_000   # HL PAXG OI (K414 confirmed)
SPX_OI_USD         = 8_000_000    # HL SPX OI (K398 confirmed)
ETA_SQRT           = 10.0         # market impact coefficient (Almgren-Chriss)
OPEX_PER_ACCT_YR   = 12_000       # operational expense per account/yr
TRADES_PER_YEAR    = 104          # K297p round-trips/year (weekly cycle)
K297P_WEIGHT       = 0.20         # K297p sleeve weight in v6.13d
LEVERAGE           = 3.0          # 3x leverage (K426/K430)
PAXG_FRAC          = 0.60         # PAXG fraction of K297p notional
SPX_FRAC           = 0.40         # SPX fraction of K297p notional

# Venue OI reference (K431 + public data)
VENUE_OI = {
    "HL":     {"PAXG": 15_000_000, "SPX": 8_000_000,  "daily_vol_mult": 0.30},
    "Bybit":  {"PAXG": 10_000_000, "SPX": 5_000_000,  "daily_vol_mult": 0.25},
    "OKX":    {"PAXG":  8_000_000, "SPX": 4_000_000,  "daily_vol_mult": 0.22},
    "Aevo":   {"PAXG":  3_000_000, "SPX": 0,          "daily_vol_mult": 0.20},
    "dYdX":   {"PAXG":  5_000_000, "SPX": 3_000_000,  "daily_vol_mult": 0.18},
    "Lighter":{"PAXG":  2_000_000, "SPX": 0,          "daily_vol_mult": 0.15},
    "Vertex": {"PAXG":  4_000_000, "SPX": 2_000_000,  "daily_vol_mult": 0.18},
}

# ─── Slippage Model ──────────────────────────────────────────────────────────

def sqrt_impact_bps(position_usd: float, oi_usd: float, vol_mult: float = 0.30) -> float:
    """Almgren-Chriss square-root market impact in basis points."""
    if oi_usd <= 0:
        return 0.0
    daily_vol = oi_usd * vol_mult
    if daily_vol <= 0:
        return 0.0
    return ETA_SQRT * math.sqrt(position_usd / daily_vol) * 100  # convert to bps

def annual_slippage_usd(
    per_venue_aum_usd: float,
    venue: str = "HL",
) -> float:
    """Calculate annual slippage cost for K297p sleeve at given per-venue AUM."""
    k297p_notional = per_venue_aum_usd * K297P_WEIGHT * LEVERAGE
    paxg_pos = k297p_notional * PAXG_FRAC
    spx_pos  = k297p_notional * SPX_FRAC

    v = VENUE_OI.get(venue, VENUE_OI["HL"])
    vol_mult = v["daily_vol_mult"]

    paxg_impact = sqrt_impact_bps(paxg_pos, v["PAXG"], vol_mult)
    spx_impact  = sqrt_impact_bps(spx_pos, v["SPX"],  vol_mult) if v["SPX"] > 0 else 0.0

    # Annual slippage: round-trip (2x) × trades/yr × notional × bps / 10000
    paxg_slip = 2 * TRADES_PER_YEAR * paxg_pos * (paxg_impact / 10_000)
    spx_slip  = 2 * TRADES_PER_YEAR * spx_pos  * (spx_impact  / 10_000)
    return paxg_slip + spx_slip

# ─── Profit Calculations ─────────────────────────────────────────────────────

def gross_annual_profit(aum_usd: float) -> float:
    """Gross annual profit before slippage (K426 calibrated, 3x leverage)."""
    return aum_usd * K426_NET_ANN_RET

def fee_annual(aum_usd: float, n_venues: int = 1) -> float:
    """Annual taker fee cost (HL 4.5bps taker, K280 trades ~260x/yr)."""
    k297p_notional = aum_usd * K297P_WEIGHT * LEVERAGE
    # K280 fees: lower turnover, mainly taker on entry/exit
    k280_notional = aum_usd * 0.75 * LEVERAGE
    taker_bps = 4.5
    trades_k280 = 26  # biweekly
    trades_k297p = TRADES_PER_YEAR
    fee_k297p = 2 * trades_k297p * k297p_notional * (taker_bps / 10_000)
    fee_k280  = 2 * trades_k280  * k280_notional  * (taker_bps / 10_000)
    return (fee_k297p + fee_k280) * (0.9 if n_venues > 1 else 1.0)  # VIP discount multi-venue

def net_annual_profit(
    aum_usd: float,
    venues: List[str],
    n_accounts: int = 1,
) -> dict:
    """Calculate net annual profit across multi-venue setup."""
    n_venues = len(venues)
    gross = gross_annual_profit(aum_usd)
    fees  = fee_annual(aum_usd, n_venues)
    per_venue_aum = aum_usd / n_venues

    total_slip = 0.0
    venue_details = []
    for venue in venues:
        slip = annual_slippage_usd(per_venue_aum, venue=venue)
        total_slip += slip
        venue_details.append({
            "venue": venue,
            "per_venue_aum_usd": round(per_venue_aum),
            "annual_slip_usd": round(slip),
        })

    opex = OPEX_PER_ACCT_YR * n_accounts
    net  = gross - total_slip - fees - opex

    return {
        "aum_usd": aum_usd,
        "venues": venues,
        "n_venues": n_venues,
        "n_accounts": n_accounts,
        "gross_annual_usd": round(gross),
        "total_slippage_usd": round(total_slip),
        "fees_usd": round(fees),
        "opex_usd": opex,
        "net_annual_usd": round(net),
        "net_ret_pct": round(net / aum_usd * 100, 2),
        "slip_drag_pct_gross": round(total_slip / gross * 100, 1),
        "venue_details": venue_details,
    }

# ─── Phase Profit Table ───────────────────────────────────────────────────────

def build_phase_table() -> List[Dict]:
    """
    Build the multi-phase profit lift table.
    Uses K431 calibrated net figures as source of truth (K431 slippage model validated).
    K431 net numbers at key AUM points (confirmed):
      $10M single HL:    $2,084,265/yr  (20.84%)
      $25M 2-venue:      $4,282,980/yr  (17.13%)
      $50M 3-venue:      $5,446,720/yr  (10.89%)
      $100M v6.20:      $48,177,045/yr  (48.18%)  — K454 depth-aware
      $200M v6.20:      $74,449,008/yr  (37.22%)  — K454 optimal
    Strategy isolation (W1+W2 same OB): approx +$210K from cleaner execution (K431 2-venue $10M)
    """
    # K431 confirmed numbers — use as authoritative source
    CALIBRATED = [
        {
            "phase": "Baseline",
            "label": "$10M single HL (v6.13d)",
            "aum": 10_000_000,
            "venues": ["HL"],
            "n_accounts": 1,
            "net_annual_usd": 2_084_265,
            "net_ret_pct": 20.84,
            "source": "K431 confirmed"
        },
        {
            "phase": "Phase 1A",
            "label": "$25M HL+Bybit (2 venues)",
            "aum": 25_000_000,
            "venues": ["HL", "Bybit"],
            "n_accounts": 2,
            "net_annual_usd": 4_282_980,
            "net_ret_pct": 17.13,
            "source": "K431 multi-venue $25M scenario"
        },
        {
            "phase": "Phase 1B",
            "label": "$10M HL W1+W2 (strategy isolation)",
            "aum": 10_000_000,
            "venues": ["HL", "HL"],
            "n_accounts": 2,
            "net_annual_usd": 2_288_635,
            "net_ret_pct": 22.89,
            "source": "K431 multi-venue 2-account $10M (same OB, stagger benefit)",
            "note": "W2 = strategy isolation only. Same HL OB — no OI capacity gain."
        },
        {
            "phase": "Phase 2",
            "label": "$50M HL+Bybit+dYdX (3 venues)",
            "aum": 50_000_000,
            "venues": ["HL", "Bybit", "dYdX"],
            "n_accounts": 3,
            "net_annual_usd": 5_446_720,
            "net_ret_pct": 10.89,
            "source": "K431 3-venue $50M confirmed"
        },
        {
            "phase": "Phase 3 v6.20",
            "label": "$100M 7-venue depth-aware (K458)",
            "aum": 100_000_000,
            "venues": ["HL", "Bybit", "OKX", "Aevo", "dYdX", "Lighter", "Vertex"],
            "n_accounts": 5,
            "net_annual_usd": 48_177_045,
            "net_ret_pct": 48.18,
            "source": "K454 phase9 profit table (depth-aware allocator model)",
            "note": "K454/K458 depth-aware allocator required. K461 accepted conditional."
        },
        {
            "phase": "Phase 4 v6.20 optimal",
            "label": "$200M 10-venue optimal",
            "aum": 200_000_000,
            "venues": ["HL", "Bybit", "OKX", "Aevo", "dYdX", "Lighter", "Vertex",
                       "Drift", "Binance", "KuCoin"],
            "n_accounts": 5,
            "net_annual_usd": 74_449_008,
            "net_ret_pct": 37.22,
            "source": "K454 phase7 max sustainable AUM (optimal $200M ceiling)",
            "note": "K454 optimal. M6-M9 timeline. DO NOT FORCE — paper-trade gates required."
        },
    ]

    baseline_net = CALIBRATED[0]["net_annual_usd"]
    results = []
    for p in CALIBRATED:
        row = dict(p)
        row["lift_vs_baseline_usd"] = row["net_annual_usd"] - baseline_net
        row["lift_pct"] = (
            round(row["lift_vs_baseline_usd"] / baseline_net * 100, 1)
            if baseline_net != 0 else 0.0
        )
        results.append(row)
    return results

# ─── Venue Policy Summary ─────────────────────────────────────────────────────

VENUE_POLICY = {
    "HL":      {"kyc": False, "multi_wallet": "PERMITTED",  "sub_account": "Vault/sub-account supported", "tos_risk": "NONE"},
    "Bybit":   {"kyc": True,  "multi_wallet": "PROHIBITED", "sub_account": "PERMITTED (master+sub system)", "tos_risk": "HIGH if dup personal"},
    "OKX":     {"kyc": True,  "multi_wallet": "PROHIBITED", "sub_account": "PERMITTED (up to 30 subs)", "tos_risk": "HIGH if dup personal"},
    "Aevo":    {"kyc": False, "multi_wallet": "PERMITTED",  "sub_account": "N/A (wallet=account)", "tos_risk": "NONE"},
    "dYdX":    {"kyc": False, "multi_wallet": "PERMITTED",  "sub_account": "PERMITTED (sub-account index)", "tos_risk": "NONE"},
    "Lighter": {"kyc": False, "multi_wallet": "PERMITTED",  "sub_account": "N/A (wallet=account)", "tos_risk": "NONE"},
    "Vertex":  {"kyc": False, "multi_wallet": "PERMITTED",  "sub_account": "N/A (wallet=account)", "tos_risk": "NONE"},
}

# ─── Main Execution ───────────────────────────────────────────────────────────

def main():
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    print("=" * 70)
    print("K485 Multi-Account Scaling Activation Playbook")
    print(f"Generated: {ts}")
    print("=" * 70)

    # ── Phase Profit Table ──
    print("\n### PROFIT LIFT TABLE (vs $10M baseline $2.08M/yr) ###\n")
    phase_table = build_phase_table()
    baseline_net = phase_table[0]["net_annual_usd"]

    print(f"{'Phase':<22} {'AUM':>10} {'Net/yr':>12} {'Lift/yr':>12} {'Lift%':>8}")
    print("-" * 68)
    for row in phase_table:
        aum_str  = f"${row['aum']/1e6:.0f}M"
        net_str  = f"${row['net_annual_usd']/1e6:.2f}M"
        lift_str = f"${row['lift_vs_baseline_usd']/1e6:.2f}M" if row['lift_vs_baseline_usd'] != 0 else "—"
        pct_str  = f"{row['lift_pct']:.0f}%" if row['lift_vs_baseline_usd'] != 0 else "—"
        print(f"{row['phase']:<22} {aum_str:>10} {net_str:>12} {lift_str:>12} {pct_str:>8}")

    # ── Venue Policy Table ──
    print("\n### VENUE POLICY TABLE ###\n")
    print(f"{'Venue':<10} {'KYC':>5} {'Multi-wallet':>15} {'Sub-account?':>20} {'ToS Risk':>12}")
    print("-" * 68)
    for venue, pol in VENUE_POLICY.items():
        print(f"{venue:<10} {'YES' if pol['kyc'] else 'NO':>5} {pol['multi_wallet']:>15} {pol['sub_account'][:20]:>20} {pol['tos_risk']:>12}")

    # ── Activation Checklist ──
    print("\n### ACTIVATION CHECKLIST ###\n")
    checklist = [
        ("Day 1 (~5 min)",   "[ ] Create MetaMask Account 2 (W2). Set HL_PRIVATE_KEY_W2."),
        ("Day 1",            "[ ] Update K449+K476 plists: route to W2 wallet."),
        ("Day 2-3 (~30 min)","[ ] Bybit: Account & Security → Sub Accounts → Create Sub #1."),
        ("Day 2-3",          "[ ] Bybit sub: generate trade-only API key. Set BYBIT_SUB1_API_KEY."),
        ("Day 3-5 (~3 hr)",  "[ ] Build scripts/multi_account_orchestrator.py (~200 LOC)."),
        ("Day 5",            "[ ] Test orchestrator --dry-run. Verify all wallet connections."),
        ("Week 2",           "[ ] Paper-trade K297p on Bybit sub 7 days. Verify fills."),
        ("Week 2 end",       "[ ] If paper gate passes: transfer $5M to Bybit sub. Go live."),
        ("Month 2",          "[ ] K449+K457 60d paper-trade gates. Prepare dYdX/Aevo wallets."),
        ("Month 6+",         "[ ] K461 gates pass → $100M+ deployment Phase 3."),
    ]
    for timeline, step in checklist:
        print(f"  {timeline:<22} {step}")

    # ── Key Risk Summary ──
    print("\n### KEY RISKS ###\n")
    risks = [
        "CRITICAL: HL multi-wallet = ZERO capacity benefit (same OB). Use for strategy isolation only.",
        "CRITICAL: Bybit/OKX duplicate personal accounts = ToS violation. Use sub-account system.",
        "CRITICAL: Never store private keys in git or HTML report.",
        "WARN: HL combined concentration (W1+W2) still counts toward 65% cap.",
        "WARN: Multi-wallet complicates tax reporting. Extend K444 for multi-wallet.",
        "INFO: Family member accounts = separate legal entity. Commingling = compliance risk.",
    ]
    for r in risks:
        print(f"  {r}")

    # ── Save results ──
    output = {
        "wave": "K485",
        "generated_utc": ts,
        "phase_profit_table": phase_table,
        "venue_policy": VENUE_POLICY,
        "baseline_net_annual_usd": baseline_net,
        "phase1_lift_usd": phase_table[1]["lift_vs_baseline_usd"],
        "phase2_lift_usd": phase_table[3]["lift_vs_baseline_usd"],
        "phase3_lift_usd": phase_table[4]["lift_vs_baseline_usd"],
        "phase4_lift_usd": phase_table[5]["lift_vs_baseline_usd"],
        "k431_correction": (
            "HL is non-KYC DEX. Multiple wallets technically unrestricted. "
            "K431 applied incorrect CEX logic. Corrected in K485."
        ),
        "primary_recommendation": (
            "Phase 1 IMMEDIATE: HL W2 strategy isolation + Bybit sub activation. "
            f"5-day setup. +${phase_table[1]['lift_vs_baseline_usd']/1e6:.2f}M/yr lift at $25M AUM."
        ),
    }

    out_path = os.path.join(REPO_ROOT, "wave_k485_multi_account_scaling.json")
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\nResults written to: {out_path}")
    print("\nK485 COMPLETE.")


if __name__ == "__main__":
    main()
