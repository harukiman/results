#!/usr/bin/env python3
"""
Wave K501 — Profit Lift Activation Dashboard
K339 pattern: data → compute → JSON → console report

Aggregates all profit-lift waves (K370/K430/K437/K481/K482/K483/K484/K485/K488/K492/K493/K498)
into a single ROI/hr-ranked queue for user activation.

Usage:
    python3 wave_k501_profit_lift_queue.py [--aum 10000000] [--out wave_k501_profit_lift_queue.json]
"""

import argparse
import json
import math
import os
import sys
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# K339 REPO_ROOT pattern
# ---------------------------------------------------------------------------
REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
RUN_TIME_UTC = datetime.now(timezone.utc)
RUN_TIME_JST = RUN_TIME_UTC.strftime("%Y-%m-%d %H:%M JST")

# ---------------------------------------------------------------------------
# § 1 — Profit Lift Inventory
#        Each entry is one discrete user-activatable action.
#        Fields:
#          id        – unique action id
#          wave      – source wave
#          title     – short human title
#          profit_10M – annual USDC lift @ $10M AUM (MID / best-estimate)
#          profit_30M – annual USDC lift @ $30M AUM
#          profit_100M– annual USDC lift @ $100M AUM
#          setup_hours – estimated human effort in hours
#          risk       – ZERO / LOW / MEDIUM / HIGH
#          status     – PENDING / IN-PROGRESS / ACTIVATED / REALIZED
#          deps       – list of action ids that must be completed first
#          gate       – paper-trade or monitoring gate before live activation
#          source_md  – relative path to source .md file
#          notes      – key caveats
# ---------------------------------------------------------------------------

ACTIONS = [
    # -----------------------------------------------------------------------
    # K481 — Builder Rebate (HL, 6-LOC patch)
    # Conservative $99K / Mid $248K / Optimistic $496K @ $10M
    # We use MID for primary projection
    # -----------------------------------------------------------------------
    {
        "id": "K481-A",
        "wave": "K481",
        "title": "HL Builder Rebate — approveBuilderFee (on-chain, main wallet)",
        "category": "fee_optimization",
        "profit_10M": 247_915,
        "profit_30M": 743_745,
        "profit_100M": 2_479_148,
        "profit_10M_conservative": 99_166,
        "profit_10M_optimistic": 495_830,
        "setup_hours": 0.5,   # 20 min web UI registration
        "risk": "ZERO",
        "status": "PENDING",
        "deps": [],
        "gate": "None (registration is instant on-chain, no paper-trade gate)",
        "source_md": "wave_k481_builder_rebate_activation.md",
        "notes": (
            "Referral-pool mechanism — true rate TBD after activation. "
            "Conservative $99K / Mid $248K / Optimistic $496K @ $10M. "
            "6-LOC code patch required after registration (K481-B)."
        ),
    },
    {
        "id": "K481-B",
        "wave": "K481",
        "title": "HL Builder Rebate — 6-LOC patch to post_only_order_manager.py",
        "category": "fee_optimization",
        "profit_10M": 0,   # profit captured by K481-A; this just activates it in code
        "profit_30M": 0,
        "profit_100M": 0,
        "profit_10M_conservative": 0,
        "profit_10M_optimistic": 0,
        "setup_hours": 0.25,
        "risk": "ZERO",
        "status": "PENDING",
        "deps": ["K481-A"],
        "gate": "24h paper-trade: verify builder field appears in order payload",
        "source_md": "wave_k481_builder_rebate_activation.md",
        "notes": (
            "Env-var gated (HL_BUILDER_CODE). Silently skips if unset. "
            "Additive patch, no existing logic removed."
        ),
    },
    # -----------------------------------------------------------------------
    # K482 — Compounding Optimization (Variant F: 4% buffer + weekly rebalance)
    # Lift breakdown: K482-1 (buffer 8%→4%): +$154K-$525K; K482-2 (weekly); K482-3 (vol-scaler)
    # Combined Variant F lift vs current B: +$886K/yr @ $10M
    # -----------------------------------------------------------------------
    {
        "id": "K482-3",
        "wave": "K482",
        "title": "K482-3: Log-utility vol-conditional scaler (new module, 80 LOC)",
        "category": "compounding",
        "profit_10M": 368_961,    # Variant D lift vs B, vol-scaler component
        "profit_30M": 1_106_883,
        "profit_100M": 3_689_611,
        "profit_10M_conservative": 200_000,
        "profit_10M_optimistic": 524_697,
        "setup_hours": 8.0,   # 80 LOC new module + 30d paper gate
        "risk": "LOW",
        "status": "PENDING",
        "deps": [],
        "gate": "Back-test on K280 equity curve; require Sharpe lift > 0.5 before deploy",
        "source_md": "wave_k482_compounding_optimize.md",
        "notes": (
            "Implement first (independent of K482-1/2). "
            "New file: scripts/vol_conditional_scaler.py. "
            "Floor=0.70, cap=1.15 vol scaling."
        ),
    },
    {
        "id": "K482-2",
        "wave": "K482",
        "title": "K482-2: Weekly rebalance toggle (15 LOC)",
        "category": "compounding",
        "profit_10M": 154_420,    # Variant C lift vs B
        "profit_30M": 463_260,
        "profit_100M": 1_544_199,
        "profit_10M_conservative": 80_000,
        "profit_10M_optimistic": 200_000,
        "setup_hours": 2.0,
        "risk": "LOW",
        "status": "PENDING",
        "deps": ["K482-3"],
        "gate": "30d paper-trade: verify drift stays < 5pp from target",
        "source_md": "wave_k482_compounding_optimize.md",
        "notes": (
            "Add REBALANCE_FREQ_DAYS config (1 → 7). "
            "Lower friction: 0.3bps daily → 0.8bps weekly."
        ),
    },
    {
        "id": "K482-1",
        "wave": "K482",
        "title": "K482-1: Cash buffer 8% → 4% (2 LOC)",
        "category": "compounding",
        "profit_10M": 362_300,    # Variant F additional lift over C+D
        "profit_30M": 1_086_900,
        "profit_100M": 3_623_000,
        "profit_10M_conservative": 200_000,
        "profit_10M_optimistic": 524_697,
        "setup_hours": 0.5,
        "risk": "MEDIUM",
        "status": "PENDING",
        "deps": ["K482-3", "K482-2"],
        "gate": "30d paper-trade with 4% buffer before live; K482-3 DD-conditional guard active",
        "source_md": "wave_k482_compounding_optimize.md",
        "notes": (
            "File: scripts/portfolio_aum_manager.py line ~77. "
            "REQUIRES K482-3 DD-conditional guard FIRST. "
            "Halves margin buffer — must paper-trade 30d before live."
        ),
    },
    # -----------------------------------------------------------------------
    # K483 — Kelly Re-optimization (v6.22a weight update)
    # Lift vs K479 heuristic: +$150K/yr @ $10M
    # -----------------------------------------------------------------------
    {
        "id": "K483",
        "wave": "K483",
        "title": "K483: v6.22a Kelly weight update (K280=50%, K376=35%, K476=5%, sUSDe=10%)",
        "category": "portfolio_allocation",
        "profit_10M": 150_300,
        "profit_30M": 450_900,
        "profit_100M": 1_503_000,
        "profit_10M_conservative": 100_000,
        "profit_10M_optimistic": 200_000,
        "setup_hours": 1.0,   # config file update
        "risk": "LOW",
        "status": "PENDING",
        "deps": [],
        "gate": "K476 paper-trade 60d gate still active; config change is safe",
        "source_md": "wave_k483_kelly_reoptimize.md",
        "notes": (
            "1/4 Kelly MV (lambda=4). K280 floor 50% active. "
            "HL 65% cap binding. K376 rises to 35% from 5%. "
            "Sharpe: 1.997 vs 1.797 baseline."
        ),
    },
    # -----------------------------------------------------------------------
    # K484 — AVAX-BTC paired trade
    # Profit: ~$75K/yr @ $10M (4x leverage, delta-neutral)
    # Gated by 60d paper-trade (K489 scaffold ready)
    # -----------------------------------------------------------------------
    {
        "id": "K484",
        "wave": "K484",
        "title": "K484: AVAX-BTC FR differential paired trade (K489 scaffold → LIVE after 60d paper)",
        "category": "new_strategy",
        "profit_10M": 75_000,
        "profit_30M": 225_000,
        "profit_100M": 750_000,
        "profit_10M_conservative": 50_000,
        "profit_10M_optimistic": 120_000,
        "setup_hours": 4.0,   # scaffold already ready; paper-trade monitoring
        "risk": "LOW",
        "status": "PENDING",
        "deps": [],
        "gate": "60d paper-trade gate (K489). G4 fold 7 Sharpe=-2.49 resolved in OOS. G6 23.8/yr < 30 threshold.",
        "source_md": "wave_k484_avax_btc_eval.md",
        "notes": (
            "OOS Sharpe 43.9. 7/10 gates pass (G4/G6/G8 soft-fail). "
            "K489 scaffold loaded. 60d paper-trade before live activation. "
            "Projected +$75K/yr @ $10M (conservative; OOS ann ret 7.9%)."
        ),
    },
    # -----------------------------------------------------------------------
    # K485 — Multi-account Phase 1A (Bybit sub-account, 30 min + 7d gate)
    # Lift: +$2.2M/yr @ $25M AUM (Phase 1A). Re-stated @ $10M as HL isolation
    # -----------------------------------------------------------------------
    {
        "id": "K485-1A",
        "wave": "K485",
        "title": "K485 Phase 1A: Bybit sub-account + HL W2 strategy isolation ($25M AUM unlock)",
        "category": "multi_account",
        "profit_10M": 204_370,    # K485 phase1B isolation lift @ $10M
        "profit_30M": 1_099_000,  # interpolated toward $25M phase1A
        "profit_100M": 5_000_000, # phase3 approximation
        "profit_10M_conservative": 100_000,
        "profit_10M_optimistic": 500_000,
        "setup_hours": 0.5,   # 30-min Bybit sub-account creation
        "risk": "LOW",
        "status": "PENDING",
        "deps": [],
        "gate": "7d paper monitoring post-setup. Bybit sub-account: KYC required.",
        "source_md": "wave_k485_multi_account_scaling.md",
        "notes": (
            "Phase 1A: HL W2 strategy isolation + Bybit sub-account. "
            "Full benefit realized at $25M AUM (+$2.2M/yr). "
            "At current $10M: isolation benefit ~$204K/yr. "
            "Bybit: sub-account system permitted (not dup personal)."
        ),
    },
    # -----------------------------------------------------------------------
    # K488 — K376 graduation (CONDITIONAL on BULL_CONFIRMED)
    # Lift @ 5% sleeve: +$411K/yr; @ 35% Kelly: +$2.88M (blocked by HL cap)
    # Gated by K497 trigger: BTC 20d SMA slope > 0
    # -----------------------------------------------------------------------
    {
        "id": "K488",
        "wave": "K488",
        "title": "K488: K376 graduation to LIVE 5% sleeve (K497 trigger: BTC SMA>0)",
        "category": "strategy_graduation",
        "profit_10M": 247_047,    # K376 at 5% sleeve lift over v6.13d
        "profit_30M": 741_141,
        "profit_100M": 4_117_450,
        "profit_10M_conservative": 150_000,
        "profit_10M_optimistic": 411_745,
        "setup_hours": 1.0,
        "risk": "MEDIUM",
        "status": "PENDING",
        "deps": [],
        "gate": "K497: BTC 20d SMA slope > 0 (BULL_CONFIRMED). Then 30d live @ 3% sleeve before 5%.",
        "source_md": "wave_k488_k376_graduation_prep.md",
        "notes": (
            "6/8 gates PASS (2 PENDING due to bear regime suppression). "
            "Initial sleeve 3% → 5% after 30d positive live Sharpe. "
            "K376 K376-momentum daemon must be running."
        ),
    },
    # -----------------------------------------------------------------------
    # K492 — K208 Signal Refinement (3 sub-actions)
    # Combined Variant E: +$223K/yr @ $10M
    # -----------------------------------------------------------------------
    {
        "id": "K492-2",
        "wave": "K492",
        "title": "K492-2: FR persistence filter (45 LOC in k280_live_fetch.py)",
        "category": "signal_quality",
        "profit_10M": 45_175,
        "profit_30M": 135_525,
        "profit_100M": 451_748,
        "profit_10M_conservative": 30_000,
        "profit_10M_optimistic": 70_000,
        "setup_hours": 2.0,
        "risk": "LOW",
        "status": "PENDING",
        "deps": [],
        "gate": "14d paper-trade toggle confirmation before live",
        "source_md": "wave_k492_k208_signal_refinement.md",
        "notes": (
            "Soft monotonic gate: 2-of-3 periods positive + gradient >= 0. "
            "Toggle: PERSISTENCE_ENABLED=false (default off). "
            "Implement first (minimal effort, high standalone impact)."
        ),
    },
    {
        "id": "K492-1",
        "wave": "K492",
        "title": "K492-1: FR microstructure filter (120 LOC, new module k208_microstructure.py)",
        "category": "signal_quality",
        "profit_10M": 75_282,
        "profit_30M": 225_846,
        "profit_100M": 752_823,
        "profit_10M_conservative": 45_000,
        "profit_10M_optimistic": 100_000,
        "setup_hours": 4.0,
        "risk": "LOW",
        "status": "PENDING",
        "deps": ["K492-2"],
        "gate": "14d paper-trade after K492-2 confirmed live",
        "source_md": "wave_k492_k208_signal_refinement.md",
        "notes": (
            "FR gradient + trade imbalance (HL recentTrades public API) + "
            "spread compression. New: scripts/k208_microstructure.py."
        ),
    },
    {
        "id": "K492-3",
        "wave": "K492",
        "title": "K492-3: Cross-venue convergence filter (50 LOC, requires OKX daemon K456)",
        "category": "signal_quality",
        "profit_10M": 126_731,
        "profit_30M": 380_193,
        "profit_100M": 1_267_309,
        "profit_10M_conservative": 80_000,
        "profit_10M_optimistic": 180_000,
        "setup_hours": 3.0,
        "risk": "LOW",
        "status": "PENDING",
        "deps": ["K492-2", "K492-1", "K498-1A"],
        "gate": "K456 OKX daemon must be LIVE. 14d paper-trade.",
        "source_md": "wave_k492_k208_signal_refinement.md",
        "notes": (
            "Enter only if HL+Bybit+OKX FR signs all agree. "
            "Highest single-component lift: +$127K/yr @ $10M. "
            "Depends on K498-1A (OKX activation)."
        ),
    },
    # -----------------------------------------------------------------------
    # K493 — ATOM-BTC paired trade
    # Profit: +$231K/yr @ $10M (OOS ann ret 24.1%, 4x leverage)
    # Gated by 60d paper-trade (K499 scaffold)
    # -----------------------------------------------------------------------
    {
        "id": "K493",
        "wave": "K493",
        "title": "K493: ATOM-BTC FR differential paired trade (K499 scaffold → LIVE after 60d paper)",
        "category": "new_strategy",
        "profit_10M": 231_000,    # OOS ann ret 24.1% × 4x × 1% sleeve (conservative sizing)
        "profit_30M": 693_000,
        "profit_100M": 2_310_000,
        "profit_10M_conservative": 150_000,
        "profit_10M_optimistic": 350_000,
        "setup_hours": 4.0,
        "risk": "LOW",
        "status": "PENDING",
        "deps": [],
        "gate": "60d paper-trade (K499). 11/12 gates PASS (only G6 soft-fail: 18.2/yr < 30).",
        "source_md": "wave_k493_atom_btc_eval.md",
        "notes": (
            "OOS Sharpe 50.8 (best in FR family). All 12 walk-forward folds positive. "
            "G5a corr vs K449 = 0.176 (Cosmos orthogonal). "
            "Lower trade freq than threshold but high per-trade quality."
        ),
    },
    # -----------------------------------------------------------------------
    # K498 — Smart Router Phase 1A (BBO + OKX, 8h effort)
    # Lift: +$121K/yr @ $30M; +$1.03M/yr @ $100M; $15K ROI/hr
    # -----------------------------------------------------------------------
    {
        "id": "K498-1A",
        "wave": "K498",
        "title": "K498 Phase 1A: K456 OKX LIVE + BBO routing mode switch (8h, $15K/hr ROI)",
        "category": "execution_optimization",
        "profit_10M": 22_279,
        "profit_30M": 120_799,
        "profit_100M": 1_032_206,
        "profit_10M_conservative": 15_000,
        "profit_10M_optimistic": 40_000,
        "setup_hours": 8.0,
        "risk": "LOW",
        "status": "PENDING",
        "deps": [],
        "gate": "48h paper-trade comparing Strategy C vs B cost_bps via decision log",
        "source_md": "wave_k498_smart_router_profit.md",
        "notes": (
            "Switch K434 routing from HL_OVERFLOW → BBO_SELECT. "
            "Bybit VIP5 1.0bps >> HL GOLD 0.3bps (0.7bps delta). "
            "Two concurrent changes: OKX enabled=true + routing mode switch. "
            "ROI: $15,100/hr (highest in portfolio at $30M AUM)."
        ),
    },
    # -----------------------------------------------------------------------
    # K370 (legacy) — Builder Rebate conservative estimate
    # Note: K481 supersedes K370 with more refined model.
    # K370 included for legacy reference; K481 is the activation wave.
    # -----------------------------------------------------------------------
    {
        "id": "K370",
        "wave": "K370",
        "title": "K370 (legacy): Builder Rebate baseline — $82.8K/yr ZERO RISK reference",
        "category": "fee_optimization",
        "profit_10M": 82_800,    # K368 conservative (corrected by K481)
        "profit_30M": 248_400,
        "profit_100M": 828_000,
        "profit_10M_conservative": 82_800,
        "profit_10M_optimistic": 472_219,
        "setup_hours": 0.5,
        "risk": "ZERO",
        "status": "SUPERSEDED_BY_K481",
        "deps": [],
        "gate": "See K481 for current activation playbook",
        "source_md": "wave_k370_builder_rebate.md",
        "notes": (
            "K368 original: $82.8K/yr at 50% direct rebate assumption. "
            "K481 corrected: referral-pool mechanism, MID=$248K/yr. "
            "This entry is for audit trail only; activate via K481."
        ),
    },
    # -----------------------------------------------------------------------
    # K430 — 3x Leverage (already deployed per K430 note)
    # Expected lift: +$2.2M/yr @ $10M (K426 finding)
    # -----------------------------------------------------------------------
    {
        "id": "K430",
        "wave": "K430",
        "title": "K430: 3x Leverage deployment (circuit breaker, 15th daemon)",
        "category": "leverage",
        "profit_10M": 2_200_000,
        "profit_30M": 6_600_000,
        "profit_100M": 22_000_000,
        "profit_10M_conservative": 1_500_000,
        "profit_10M_optimistic": 3_000_000,
        "setup_hours": 0.0,   # marked SCAFFOLD-READY / already deployed per task spec
        "risk": "MEDIUM",
        "status": "ACTIVATED",  # per K501 task spec: "already deployed K430 patch"
        "deps": [],
        "gate": "Circuit breaker daemon (leverage-circuit-breaker.plist) must be running",
        "source_md": "wave_k430_leverage_3x.md",
        "notes": (
            "3x leverage on $10M @ v6.13d architecture. "
            "Circuit breaker: auto-reduce to 1x if drawdown > threshold. "
            "PAPER_TRADE phase → confirmed ACTIVATED per K501 mandate."
        ),
    },
    # -----------------------------------------------------------------------
    # K437 — HYPE Bronze Stake (100 HYPE ≈ $5,900, 143.9% ROI)
    # -----------------------------------------------------------------------
    {
        "id": "K437",
        "wave": "K437",
        "title": "K437: HYPE Bronze stake (100 HYPE ≈ $5,900, 143.9% ROI, $8.6K/yr benefit)",
        "category": "fee_optimization",
        "profit_10M": 8_623,
        "profit_30M": 25_869,
        "profit_100M": 86_230,
        "profit_10M_conservative": 8_623,
        "profit_10M_optimistic": 12_000,
        "setup_hours": 0.5,
        "risk": "LOW",
        "status": "PENDING",
        "deps": [],
        "gate": "None (stake immediately; payback < 9 months)",
        "source_md": "wave_k437_hype_stake.md",
        "notes": (
            "Buy 100 HYPE at ~$59 = $5,900 total cost. "
            "Annual benefit: $8,490 fee saving + $133 staking yield = $8,623. "
            "ROI 143.9%. Do NOT buy Gold tier at $10M AUM (ROI only 2.9%)."
        ),
    },
]

# ---------------------------------------------------------------------------
# § 2 — ROI/hr Calculation
# ---------------------------------------------------------------------------

def compute_roi_per_hr(action: dict, aum_key: str = "profit_10M") -> float:
    """profit_per_year / setup_hours (1-year operating, realize assumption)."""
    profit = action.get(aum_key, 0)
    hours = action.get("setup_hours", 1)
    if hours <= 0:
        return float("inf") if profit > 0 else 0.0
    return profit / hours


def rank_actions(actions: list, aum_key: str = "profit_10M") -> list:
    """Sort actions by ROI/hr descending, skipping ACTIVATED/SUPERSEDED."""
    active = [a for a in actions if a["status"] not in ("ACTIVATED", "SUPERSEDED_BY_K481")]
    return sorted(active, key=lambda a: compute_roi_per_hr(a, aum_key), reverse=True)


# ---------------------------------------------------------------------------
# § 3 — Dependency Graph
# ---------------------------------------------------------------------------

def build_dep_graph(actions: list) -> dict:
    """Return {action_id: [list of ids that must be done first]}."""
    return {a["id"]: a.get("deps", []) for a in actions}


def topological_order(graph: dict) -> list:
    """Kahn's BFS topological sort (stable order)."""
    from collections import deque
    in_deg = {n: 0 for n in graph}
    rev = {n: [] for n in graph}
    for node, deps in graph.items():
        for d in deps:
            if d in in_deg:
                in_deg[node] += 1
                rev[d].append(node)
    queue = deque(sorted(n for n, d in in_deg.items() if d == 0))
    order = []
    while queue:
        n = queue.popleft()
        order.append(n)
        for m in sorted(rev.get(n, [])):
            in_deg[m] -= 1
            if in_deg[m] == 0:
                queue.append(m)
    return order


# ---------------------------------------------------------------------------
# § 4 — 5-Year Projection
# ---------------------------------------------------------------------------

def project_5y(
    initial_aum: float,
    base_cagr: float,        # v6.13d LIVE CAGR
    lift_annual: float,      # total annual lift from activated actions
    years: int = 5,
) -> dict:
    """Compound $initial_aum at (base_cagr + effective lift rate) for N years."""
    effective_cagr = base_cagr + (lift_annual / initial_aum)
    terminal = initial_aum * ((1 + effective_cagr) ** years)
    return {
        "initial_aum": initial_aum,
        "base_cagr_pct": round(base_cagr * 100, 4),
        "lift_annual_usd": round(lift_annual),
        "effective_cagr_pct": round(effective_cagr * 100, 4),
        "terminal_5y_usd": round(terminal),
        "profit_5y_usd": round(terminal - initial_aum),
        "years": years,
    }


# ---------------------------------------------------------------------------
# § 5 — Total Profit Aggregation
# ---------------------------------------------------------------------------

def aggregate_profit(actions: list) -> dict:
    """Sum profit across active (non-superseded, non-activated) actions."""
    active = [a for a in actions if a["status"] not in ("SUPERSEDED_BY_K481",)]
    # Include ACTIVATED (K430) in the sum — they are already realized
    total_10M = sum(a["profit_10M"] for a in active)
    total_30M = sum(a["profit_30M"] for a in active)
    total_100M = sum(a["profit_100M"] for a in active)
    # Pending-only (not yet activated)
    pending = [a for a in active if a["status"] not in ("ACTIVATED", "REALIZED")]
    pending_10M = sum(a["profit_10M"] for a in pending)
    pending_30M = sum(a["profit_30M"] for a in pending)
    pending_100M = sum(a["profit_100M"] for a in pending)
    return {
        "total_actions": len(active),
        "pending_actions": len(pending),
        "total_annual_10M": total_10M,
        "total_annual_30M": total_30M,
        "total_annual_100M": total_100M,
        "pending_annual_10M": pending_10M,
        "pending_annual_30M": pending_30M,
        "pending_annual_100M": pending_100M,
    }


# ---------------------------------------------------------------------------
# § 6 — Risk Re-assessment
# ---------------------------------------------------------------------------

RISK_NOTES = {
    "K481-A": "ZERO. approveBuilderFee is on-chain approval, no code change. Worst case: program ends → return to baseline.",
    "K481-B": "ZERO. Additive 6-LOC patch, env-var gated. Falls back silently if HL_BUILDER_CODE unset.",
    "K482-3": "LOW. New module. vol-scaling floor=0.70 limits downside. Back-test required.",
    "K482-2": "LOW. Weekly rebalance reduces friction. Drift risk < 5pp in testing.",
    "K482-1": "MEDIUM. Halves margin buffer (8%→4%). REQUIRES K482-3 DD-conditional guard active first.",
    "K483":   "LOW. Config weight update. HL cap 65% binding; K280 floor 50% active. No new code.",
    "K484":   "LOW. Scaffold ready. Delta-neutral (both legs HL). Max DD <0.36% full-period.",
    "K485-1A": "LOW. Bybit sub-account (sub, not dup personal). Strategy isolation only.",
    "K488":   "MEDIUM. K376 momentum in bear regime. Gated by BULL_CONFIRMED trigger.",
    "K492-2": "LOW. Toggle flag (default off). Emergency fallback: set flag=False.",
    "K492-1": "LOW. New module with public API calls. recentTrades timeout → graceful skip.",
    "K492-3": "LOW. Cross-venue convergence. OKX timing mismatch is primary risk (1h vs 8h settlement).",
    "K493":   "LOW. Delta-neutral. OOS Sharpe 50.8, all 12 WF folds positive.",
    "K498-1A": "LOW. Config + routing mode switch. 48h paper-trade validation before live.",
    "K370":   "ZERO (legacy). Superseded by K481.",
    "K430":   "MEDIUM. 3x leverage increases drawdown exposure. Circuit breaker required.",
    "K437":   "LOW. 100 HYPE stake ($5,900). HYPE price risk (asset exposure, not strategy risk).",
}

CASCADE_RISKS = [
    "K482-1 depends on K482-3: activating buffer reduction without DD-conditional guard → margin call risk",
    "K492-3 depends on K498-1A (OKX LIVE): cross-venue filter without OKX data → graceful skip (LOW risk)",
    "K488 gated by BULL_CONFIRMED: activating K376 in bear regime → reduced win rate (50d historical)",
    "K484/K493 gated by 60d paper: skipping gate → operating under G4/G6 soft-fail conditions",
    "K430 requires circuit-breaker daemon: 3x without circuit breaker → uncontrolled drawdown",
]


# ---------------------------------------------------------------------------
# § 7 — Main Assembly
# ---------------------------------------------------------------------------

def build_output(args) -> dict:
    aum_key = "profit_10M"
    if args.aum >= 80_000_000:
        aum_key = "profit_100M"
    elif args.aum >= 20_000_000:
        aum_key = "profit_30M"

    ranked = rank_actions(ACTIONS, aum_key)

    # Compute ROI/hr for each action
    for a in ACTIONS:
        a["roi_per_hr_10M"] = round(compute_roi_per_hr(a, "profit_10M"), 1)
        a["roi_per_hr_30M"] = round(compute_roi_per_hr(a, "profit_30M"), 1)
        a["roi_per_hr_100M"] = round(compute_roi_per_hr(a, "profit_100M"), 1)
        a["implementation_risk_note"] = RISK_NOTES.get(a["id"], "")

    dep_graph = build_dep_graph(ACTIONS)
    topo = topological_order(dep_graph)

    agg = aggregate_profit(ACTIONS)

    # v6.13d baseline (K431 confirmed): ~20.84% annual return on $10M AUM
    V613D_CAGR = 0.2084
    # With all pending activated
    lift_pending_10M = agg["pending_annual_10M"]
    lift_all_10M = agg["total_annual_10M"]

    proj_baseline = project_5y(10_000_000, V613D_CAGR, 0)
    proj_pending = project_5y(10_000_000, V613D_CAGR, lift_pending_10M)
    proj_all = project_5y(10_000_000, V613D_CAGR, lift_all_10M)

    proj_100m_baseline = project_5y(100_000_000, V613D_CAGR, 0)
    proj_100m_all = project_5y(100_000_000, V613D_CAGR, agg["total_annual_100M"])

    # Build queue (top 10)
    queue = []
    rank_num = 0
    for a in ranked[:10]:
        rank_num += 1
        queue.append({
            "rank": rank_num,
            "id": a["id"],
            "wave": a["wave"],
            "title": a["title"],
            "category": a["category"],
            "setup_hours": a["setup_hours"],
            "risk": a["risk"],
            "profit_10M": a["profit_10M"],
            "profit_30M": a["profit_30M"],
            "profit_100M": a["profit_100M"],
            "roi_per_hr_10M": a["roi_per_hr_10M"],
            "roi_per_hr_30M": a["roi_per_hr_30M"],
            "status": a["status"],
            "deps": a.get("deps", []),
            "gate": a["gate"],
            "source_md": a["source_md"],
            "notes": a["notes"],
            "implementation_risk_note": a.get("implementation_risk_note", ""),
        })

    # Immediate top 5 (no deps, status PENDING, LOW or ZERO risk)
    immediate_5 = [
        q for q in queue
        if q["deps"] == [] and q["status"] == "PENDING" and q["risk"] in ("ZERO", "LOW")
    ][:5]

    return {
        "wave": "K501",
        "title": "Profit Lift Activation Dashboard — ROI/hr Ranked Queue",
        "generated_utc": RUN_TIME_UTC.isoformat(),
        "generated_jst": RUN_TIME_JST,
        "aum_basis": f"${args.aum:,.0f}",
        "v613d_cagr_pct": round(V613D_CAGR * 100, 2),
        "aggregated_profit": agg,
        "projection_v613d_baseline_10M": proj_baseline,
        "projection_all_pending_activated_10M": proj_pending,
        "projection_all_including_activated_10M": proj_all,
        "projection_all_activated_100M": proj_100m_all,
        "activation_queue_top10": queue,
        "immediate_top5_no_deps": immediate_5,
        "dependency_graph": dep_graph,
        "topological_order": topo,
        "cascade_risks": CASCADE_RISKS,
        "all_actions": ACTIONS,
        "status_legend": {
            "PENDING": "Not started; user action required",
            "IN-PROGRESS": "Partially implemented or in paper-trade phase",
            "ACTIVATED": "Code deployed / live in production",
            "REALIZED": "Confirmed profit appearing in PnL",
            "SUPERSEDED_BY_K481": "Older entry; use K481 for activation",
        },
        "notes": [
            "ROI/hr = profit_per_year / setup_hours (1-year operating, realize assumption)",
            "Profit figures are annualized estimates. Conservative/optimistic variants in all_actions.",
            "K430 marked ACTIVATED per K501 task spec ('already deployed K430 patch').",
            "K370 marked SUPERSEDED_BY_K481 — activate builder rebate via K481 playbook.",
            "K482 sub-actions must be implemented in order: K482-3 → K482-2 → K482-1.",
            "K492 sub-actions must be implemented in order: K492-2 → K492-1 → K492-3.",
        ],
    }


def print_console_report(data: dict) -> None:
    print("=" * 72)
    print(f"  K501 PROFIT LIFT ACTIVATION QUEUE")
    print(f"  Generated: {data['generated_jst']}")
    print("=" * 72)

    agg = data["aggregated_profit"]
    print(f"\n{'AGGREGATED PROFIT POTENTIAL':}")
    print(f"  Pending actions:          {agg['pending_actions']}")
    print(f"  Pending lift @ $10M/yr:   ${agg['pending_annual_10M']:>12,.0f}")
    print(f"  Pending lift @ $30M/yr:   ${agg['pending_annual_30M']:>12,.0f}")
    print(f"  Pending lift @ $100M/yr:  ${agg['pending_annual_100M']:>12,.0f}")

    pb = data["projection_v613d_baseline_10M"]
    pp = data["projection_all_pending_activated_10M"]
    print(f"\n{'5-YEAR PROJECTION @ $10M (v6.13d LIVE)':}")
    print(f"  Baseline (no new actions): ${pb['terminal_5y_usd']:>12,.0f}  (CAGR {pb['base_cagr_pct']}%)")
    print(f"  All pending activated:     ${pp['terminal_5y_usd']:>12,.0f}  (CAGR {pp['effective_cagr_pct']}%)")
    print(f"  Delta 5y:                  ${pp['profit_5y_usd']-pb['profit_5y_usd']:>12,.0f}")

    print(f"\n{'TOP 10 ACTIONS BY ROI/HR (@ $10M AUM)':}")
    print(f"  {'#':<3} {'ID':<12} {'ROI/hr':>10} {'$10M/yr':>12} {'Hours':>7} {'Risk':<8} {'Title'}")
    print(f"  {'-'*3} {'-'*12} {'-'*10} {'-'*12} {'-'*7} {'-'*8} {'-'*30}")
    for q in data["activation_queue_top10"]:
        roi = q["roi_per_hr_10M"]
        roi_str = f"${roi:>8,.0f}" if roi != float("inf") else "    INSTANT"
        print(
            f"  {q['rank']:<3} {q['id']:<12} {roi_str} "
            f"  ${q['profit_10M']:>10,.0f}  {q['setup_hours']:>5.1f}h  {q['risk']:<8} "
            f"{q['title'][:45]}"
        )

    print(f"\n{'IMMEDIATE TOP 5 (no deps, LOW/ZERO risk, PENDING)':}")
    for i, q in enumerate(data["immediate_top5_no_deps"], 1):
        print(f"  {i}. [{q['id']}] {q['title'][:60]}")
        print(f"     +${q['profit_10M']:,.0f}/yr @ $10M | Setup: {q['setup_hours']}h | Risk: {q['risk']}")

    print(f"\n{'CASCADE DEPENDENCY RISKS':}")
    for r in data["cascade_risks"]:
        print(f"  ! {r}")

    print("\n" + "=" * 72)


# ---------------------------------------------------------------------------
# § 8 — Entry Point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="K501 Profit Lift Activation Queue")
    parser.add_argument("--aum", type=float, default=10_000_000, help="AUM basis in USDC")
    parser.add_argument(
        "--out",
        default=os.path.join(REPO_ROOT, "wave_k501_profit_lift_queue.json"),
        help="Output JSON path",
    )
    parser.add_argument("--no-json", action="store_true", help="Skip JSON output")
    args = parser.parse_args()

    data = build_output(args)
    print_console_report(data)

    if not args.no_json:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)
        print(f"\nJSON written: {args.out}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
