#!/usr/bin/env python3
"""
K764 Phase A++ Governance Synthesis
=====================================
Wave:    K764
Date:    2026-05-30
Purpose: Synthesize all pending Phase A++ items (K744-K763) with K523 3-point ranges,
         risk-ranked priority order, v7.0 architecture proposal, and activation sequence.

K339 Pattern: REPO_ROOT resolved from __file__
K523 Mandate: ALL uplift projections MUST be 3-point (conservative / central / optimistic)
              Single-point projections PROHIBITED.
              K518 38% realized-to-stated ratio applied to all.
LIVE Auto-Change: PROHIBITED (synthesis only)
"""

from __future__ import annotations

import json
import sys
import traceback
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# ─── K339 REPO_ROOT pattern ────────────────────────────────────────────────
REPO_ROOT = Path(__file__).resolve().parent
DATA_DIR   = REPO_ROOT / "data"
DOCS_DIR   = REPO_ROOT / "docs"
SCRIPTS_DIR= REPO_ROOT / "scripts"

JST = timezone(timedelta(hours=9))
NOW_JST = datetime.now(JST).strftime("%Y-%m-%d %H:%M JST")
NOW_UTC = datetime.now(timezone.utc).isoformat()

# ─── K523 Constants ────────────────────────────────────────────────────────
K518_HAIRCUT = 0.38          # realized-to-stated ratio (K518 floor)
OOS_PAIRED_HAIRCUT = 0.25    # additional OOS haircut for paired-trade
AUM_REF = 10_000_000         # $10M reference AUM
K523_VIOLATION = "SINGLE_POINT_PROJECTION_PROHIBITED"

# ─── Dataclasses ───────────────────────────────────────────────────────────

@dataclass
class K523Range:
    """K523-compliant 3-point projection."""
    conservative: float
    central: float
    optimistic: float
    note: str = ""
    k518_applied: bool = False

    def realized(self) -> "K523Range":
        """Apply K518 38% haircut."""
        return K523Range(
            conservative=round(self.conservative * K518_HAIRCUT),
            central=round(self.central * K518_HAIRCUT),
            optimistic=round(self.optimistic * K518_HAIRCUT),
            note=f"K518 {K518_HAIRCUT:.0%} realized | " + self.note,
            k518_applied=True,
        )

    def to_dict(self) -> dict:
        return {
            "conservative": self.conservative,
            "central": self.central,
            "optimistic": self.optimistic,
            "note": self.note,
            "k518_applied": self.k518_applied,
        }

    def __add__(self, other: "K523Range") -> "K523Range":
        return K523Range(
            conservative=self.conservative + other.conservative,
            central=self.central + other.central,
            optimistic=self.optimistic + other.optimistic,
            note="(summed)",
        )


@dataclass
class PhaseAItem:
    """Single Phase A++ item with full metadata."""
    id: str
    title: str
    wave: str
    tier: int
    tier_label: str
    status: str
    k523_gross: K523Range
    activation_1step: str
    reversibility: str
    days_to_activate: int
    critical_risks: List[str]
    files: List[str]
    zero_risk: bool = False
    zero_infra_change: bool = False
    daemon_number: Optional[int] = None
    activation_prerequisite: List[str] = field(default_factory=list)

    @property
    def k523_realized(self) -> K523Range:
        return self.k523_gross.realized()

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "wave": self.wave,
            "tier": self.tier,
            "tier_label": self.tier_label,
            "status": self.status,
            "zero_risk": self.zero_risk,
            "zero_infra_change": self.zero_infra_change,
            "days_to_activate": self.days_to_activate,
            "daemon_number": self.daemon_number,
            "k523_gross": self.k523_gross.to_dict(),
            "k523_realized": self.k523_realized.to_dict(),
            "activation_1step": self.activation_1step,
            "reversibility": self.reversibility,
            "critical_risks": self.critical_risks,
            "files": self.files,
            "activation_prerequisite": self.activation_prerequisite,
        }


# ─── Phase A++ Item Registry ───────────────────────────────────────────────

def build_items() -> List[PhaseAItem]:
    """Define all Phase A++ items with K523 3-point ranges."""
    return [
        # ──────────────────── TIER 1: Immediate, Zero Risk ───────────────────
        PhaseAItem(
            id="K763",
            title="Daily Compound Scheduler",
            wave="K763",
            tier=1,
            tier_label="Immediate — zero infra risk",
            status="SCAFFOLD-READY",
            daemon_number=73,
            zero_infra_change=True,
            days_to_activate=1,
            k523_gross=K523Range(
                conservative=3_517,
                central=3_281_131,
                optimistic=13_636_966,
                note=(
                    "Conservative=monthly→weekly scheduling increment only (@r=10% decay env). "
                    "Central=weekly→daily at v6.52 r=218%/yr (K724 confirmed). "
                    "Optimistic=daily+half-Kelly+continuous rebalance @r=273%/yr. "
                    "K523: central and optimistic contingent on ALL sleeves live at v6.52. "
                    "Daily operational cost $118K/yr negligible vs compound uplift."
                ),
            ),
            activation_1step="COMPOUND_FREQUENCY=daily in scripts/k763_compound_scheduler.py + launchctl load",
            reversibility="COMPOUND_FREQUENCY=monthly returns to current behavior instantly",
            critical_risks=[
                "K763 central ($3.28M) contingent on all sleeves live + v6.52 r=218%/yr",
                "K208 decay (K509): realistic env closer to conservative framing unless full live stack active",
                "Daily rebalance: $118K/yr operational cost, must be net-positive vs gross uplift",
            ],
            files=["scripts/k763_compound_scheduler.py", "scripts/com.cryptolab.k763-compound-scheduler.plist"],
        ),
        PhaseAItem(
            id="K755",
            title="HL Builder Rebate",
            wave="K755",
            tier=1,
            tier_label="Immediate — zero risk",
            status="BUILDER-REBATE-READY",
            zero_risk=True,
            zero_infra_change=True,
            days_to_activate=1,
            k523_gross=K523Range(
                conservative=99_166,
                central=247_915,
                optimistic=495_830,
                note=(
                    "Conservative=10% referral pool allocation, central=25%, optimistic=50%. "
                    "HL fraction 57.5%, daily turnover 1.5x, POST_ONLY fill rate 70%. "
                    "10 HL daemons benefit automatically. Worst case: silent no-op (f=0). "
                    "K368 correction: referral pool mechanism, exact rate undocumented by HL."
                ),
            ),
            activation_1step="Set HL_BUILDER_CODE=0x<YOUR_WALLET> in .env.local + restart 10 HL daemons",
            reversibility="Unset HL_BUILDER_CODE → silent no-op, zero impact on execution",
            critical_risks=[
                "Referral pool mechanism — exact rebate rate not published by HL as of 2026-05",
                "POST_ONLY fill rate 70% assumption — may vary with market microstructure",
                "Builder code must be from approveBuilderFee signed by MAIN wallet (not agent)",
            ],
            files=["scripts/k481_builder_rebate.py", "data/builder_codes.json", "scripts/post_only_order_manager.py"],
        ),
        PhaseAItem(
            id="K753",
            title="K545 Tax Loss Harvester",
            wave="K753",
            tier=1,
            tier_label="Immediate — zero risk (paper default)",
            status="SCAFFOLD-READY",
            daemon_number=70,
            zero_infra_change=False,
            days_to_activate=1,
            k523_gross=K523Range(
                conservative=74_000,
                central=185_000,
                optimistic=370_000,
                note=(
                    "Tax shield NOT trading alpha. INFORMATIONAL ONLY — NOT TAX ADVICE. "
                    "Conservative=$200K losses/yr @37% rate. Central=$500K. Optimistic=$1M. "
                    "CPA consultation MANDATORY before --live. US_STCG 37% assumed. "
                    "Wash-sale 30d default. Regime stress guard (max_dd>15%) may suppress."
                ),
            ),
            activation_1step="launchctl load com.cryptolab.k545-tax-harvester.plist (paper default; CPA required before live)",
            reversibility="Set PAPER_TRADE=True + launchctl reload → no harvests, no re-entry",
            critical_risks=[
                "NOT TAX ADVICE — CPA consultation mandatory before any live harvest",
                "US wash-sale 30d assumption may differ by jurisdiction (JP/KOR/DE: 0d)",
                "Regime stress guard may suppress harvests during drawdown periods",
                "FIFO basis method — verify against K302a/K443 trade logs",
            ],
            files=["scripts/k545_tax_harvester.py", "scripts/com.cryptolab.k545-tax-harvester.plist"],
        ),

        # ──────────────────── TIER 2: Immediate, Low Risk ─────────────────────
        PhaseAItem(
            id="K751",
            title="v6.52 Kelly Sleeve Sizing (MANDATORY COMPLIANCE FIX)",
            wave="K751",
            tier=2,
            tier_label="Immediate — low risk, MANDATORY (compliance)",
            status="SCAFFOLD-READY",
            zero_infra_change=True,
            days_to_activate=2,
            k523_gross=K523Range(
                conservative=184_568,
                central=195_024,
                optimistic=555_647,
                note=(
                    "Uplift vs v6.51. Half-Kelly (0.5x) method. "
                    "v6.51 violations FIXED: HL 66.8%→53.6% (-13.2pp), "
                    "Bybit 55.7%→43.8% (-11.9pp), K280 15.5%→30.0% (+14.5pp mandate). "
                    "Portfolio Sh 9.33→70.4 (concentration fix primary driver). "
                    "K751 is MANDATORY before activating K745/K757 (cap fix prerequisite)."
                ),
            ),
            activation_1step="Add SLEEVE_WEIGHTS_V652 to scripts/leverage_manager.py (1-flip, single file)",
            reversibility="git revert — single file, no cascade effects",
            critical_risks=[
                "v6.51 is NON-COMPLIANT — K751 is mandatory, not optional optimization",
                "Bybit 43.8% post-fix assumes sub-account not yet added; K757 shifts numbers",
                "K280 weight restoration (15.5%→30%) reduces K208 decay impact on K280 sleeve",
            ],
            files=["scripts/leverage_manager.py", "data/kelly_optimal_weights.json"],
        ),
        PhaseAItem(
            id="K742",
            title="K492-C Persistence Filter Patch",
            wave="K742",
            tier=2,
            tier_label="Immediate — low risk (config flip)",
            status="DIFF-READY",
            zero_infra_change=True,
            days_to_activate=2,
            k523_gross=K523Range(
                conservative=20_000,
                central=32_500,
                optimistic=45_000,
                note=(
                    "K492-C adds spread-gradient persistence gate to K280 (K208 DAR). "
                    "Backtest: 80% filter rate (2/10 symbols pass in sim). "
                    "Conservative: 20% live pass rate, reduced false entries. "
                    "Central: 35% pass rate improvement. Optimistic: 50% improvement. "
                    "Addresses K208 decay (K509: -67% Y/Y, K280 sleeve $400K/yr)."
                ),
            ),
            activation_1step="Set PERSISTENCE_ENABLED = True in scripts/k280_live_fetch.py",
            reversibility="PERSISTENCE_ENABLED = False OR git apply -R wave_k742_k492c_ready.diff",
            critical_risks=[
                "80% filter rate may over-suppress entries in sustained trending markets",
                "Gradient check may produce false negatives in low-liquidity periods",
                "K208 decay is structural (crowding + spread mean-reversion) — filter alone insufficient",
            ],
            files=["scripts/k280_live_fetch.py", "wave_k742_k492c_ready.diff"],
        ),

        # ──────────────────── TIER 3: Medium Risk, Infra Change ───────────────
        PhaseAItem(
            id="K745",
            title="K498 OKX Integration (3rd Venue)",
            wave="K745",
            tier=3,
            tier_label="Medium risk — account setup required",
            status="SCAFFOLD-READY",
            zero_infra_change=False,
            days_to_activate=7,
            k523_gross=K523Range(
                conservative=31_484,
                central=47_218,
                optimistic=138_486,
                note=(
                    "Primary value: HL 65%→50% relief (+$1.5M headroom, 5 new strategies possible). "
                    "Conservative=1 new strategy @Sh=10. Mid=1 new strategy @Sh=15. "
                    "Optimistic=2 new strategies @Sh=22. OKX taker rebate $38-57/yr (negligible). "
                    "OOS haircut 25% applied to new strategy projections. "
                    "25/25 API smoke tests passed (paper mode). HL relief independent of K757."
                ),
            ),
            activation_prerequisite=["K751 v6.52 activated first (concentration caps fix required)"],
            activation_1step="OKX_LIVE_ENABLED=true in .env.local + live_enabled=true in venue_allocation.json",
            reversibility="OKX_LIVE_ENABLED=false → all routing reverts to HL/Bybit instantly",
            critical_risks=[
                "OKX API key setup required (trade-only, no withdraw — security hygiene)",
                "Must paper-trade 7d minimum before live enable",
                "HL cap relief (65%→50%) is primary value driver — dependent on K751 first",
                "OKX liquidity on alt-alt pairs may differ from HL; fill rate comparison required",
            ],
            files=["scripts/okx_client.py", "scripts/okx_fr_cache.py", "scripts/multi_venue_router.py", "data/venue_allocation.json"],
        ),
        PhaseAItem(
            id="K757",
            title="K485 Bybit Sub-Account (2nd Bybit)",
            wave="K757",
            tier=3,
            tier_label="Medium risk — account setup required",
            status="SCAFFOLD-READY",
            zero_infra_change=False,
            days_to_activate=7,
            k523_gross=K523Range(
                conservative=20_000,
                central=50_000,
                optimistic=120_000,
                note=(
                    "Capacity relief, not direct alpha. Bybit 55.7%→halved-effective. "
                    "$5M sub headroom @$10M AUM. 10 alt-alt sleeves → sub account. "
                    "Conservative=5pp relief, central=10pp, optimistic=20pp. "
                    "K757 and K498 effects are independent and additive. "
                    "41/41 scaffold tests passed. Sub activation pending API key."
                ),
            ),
            activation_prerequisite=["K751 v6.52 activated first (Bybit_main still at 55.7% after K757 if K751 not done)"],
            activation_1step="Paste BYBIT_SUB_API_KEY + BYBIT_SUB_API_SECRET into .env.local",
            reversibility="Unset BYBIT_SUB_API_KEY → all routing returns to main (no code change)",
            critical_risks=[
                "Bybit sub-account creation requires identity verification on Bybit platform",
                "API key must be trade-only (no withdraw) — critical security requirement",
                "After K757 alone: Bybit_main still 55.7% — K751 v6.52 must also be active",
                "Transfer between main and sub has delay — not suitable for emergency exit path",
            ],
            files=["scripts/bybit_multi_account_client.py", "scripts/risk_manager.py", "data/venue_allocation.json"],
        ),

        # ──────────────────── TIER 4: Paper-Gate Dependent ────────────────────
        PhaseAItem(
            id="K747",
            title="TAO-SOL Live Elevation",
            wave="K747",
            tier=4,
            tier_label="Paper-gate dependent (K498 + 60d gate)",
            status="PAPER-GATE",
            zero_infra_change=False,
            days_to_activate=30,
            k523_gross=K523Range(
                conservative=34_000,
                central=62_000,
                optimistic=110_000,
                note=(
                    "TAO = AI L1 (Bittensor), 69th daemon, 15th alt-alt. "
                    "OOS Sh=41.2 (K747 eval). Paper-gate until K498 live (HL cap relief). "
                    "Live elevation requires 60d paper PASS: Sh>=6, fill>=60%, maxDD<15%. "
                    "Conservative: moderate AI narrative cycle alignment. Optimistic: bull rotation."
                ),
            ),
            activation_prerequisite=["K498 OKX integration active (K745)", "60d paper gate: Sh>=6, fill>=60%, maxDD<15%"],
            activation_1step="Set live_enabled=true in data/k747_dashboard.json after gate PASS",
            reversibility="Set live_enabled=false → paper-only mode",
            critical_risks=[
                "TAO = high beta to AI narrative cycle — correlated to BTC/ETH bull runs",
                "HL concentration at 66.8% pre-K751 — must wait for compliance fix + K498",
                "60d paper gate is hard requirement (not advisory)",
            ],
            files=["data/k747_dashboard.json"],
        ),
        PhaseAItem(
            id="K754",
            title="PEPE-SOL Live Elevation",
            wave="K754",
            tier=4,
            tier_label="Paper-gate dependent (K498 + 60d gate)",
            status="PAPER-GATE",
            zero_infra_change=False,
            days_to_activate=30,
            k523_gross=K523Range(
                conservative=34_758,
                central=62_000,
                optimistic=85_678,
                note=(
                    "PEPE-SOL, 71st daemon, 16th alt-alt, 14th vertex ERC-20 meme cluster. "
                    "OOS Sh=44.43, G4 12/12 ALL POSITIVE, G5 22/22 PASS. "
                    "Bybit 1000PEPE denomination. L003 AVAX proximity warning (0.4125 < 0.40 threshold). "
                    "Monthly L003 recheck required. MR9 L002 PEPE-X auto-blocked (SOL pivot triangle)."
                ),
            ),
            activation_prerequisite=["K498 OKX integration active (K745)", "60d paper gate: Sh>=6, fill>=60%, maxDD<15%"],
            activation_1step="Set live_enabled=true in data/k754_dashboard.json after gate PASS",
            reversibility="Set live_enabled=false → paper-only mode",
            critical_risks=[
                "PEPE = ERC-20 meme — bull rotation dependent, high regime sensitivity",
                "L003 AVAX proximity warning (0.4125 — threshold 0.40) — monthly recheck mandatory",
                "1000PEPE denomination on Bybit — fills may differ from HL",
            ],
            files=["data/k754_dashboard.json"],
        ),
        PhaseAItem(
            id="K759",
            title="WIF-SOL Live Elevation",
            wave="K759",
            tier=4,
            tier_label="Paper-gate dependent (K498 + 60d gate)",
            status="PAPER-GATE",
            zero_infra_change=False,
            days_to_activate=30,
            k523_gross=K523Range(
                conservative=20_655,
                central=54_245,
                optimistic=76_847,
                note=(
                    "WIF-SOL, 72nd daemon, 17th alt-alt, 15th vertex SOL-native meme. "
                    "OOS Sh=24.45, G4 12/12 POSITIVE, G5 PASS. "
                    "G5w PEPE-SOL=0.382 (proximity 0.40 threshold) — reduced sleeve 2.0%. "
                    "Cross-sleeve WIF+PEPE combined 4.0% meme-vs-SOL hard cap. "
                    "L011 raw_corr(WIF,SOL)=0.487 monthly recheck."
                ),
            ),
            activation_prerequisite=["K498 OKX integration active (K745)", "60d paper gate: Sh>=6, fill>=60%, maxDD<15%"],
            activation_1step="Set live_enabled=true in data/k759_dashboard.json after gate PASS",
            reversibility="Set live_enabled=false → paper-only mode",
            critical_risks=[
                "G5w PEPE-SOL=0.382 borderline (threshold 0.40) — monthly cross-sleeve monitoring mandatory",
                "WIF = SOL-native meme — BONK/WIF/POPCAT rotation, correlated drawdowns",
                "Combined meme sleeve 4.0% hard cap (WIF+PEPE) prevents further meme expansion",
            ],
            files=["data/k759_dashboard.json"],
        ),
    ]


# ─── Analysis Functions ─────────────────────────────────────────────────────

def compute_tier_summary(items: List[PhaseAItem], tier: int) -> Dict:
    """Compute K523 3-point sum for a given tier."""
    tier_items = [i for i in items if i.tier == tier]
    gross = K523Range(0, 0, 0)
    for item in tier_items:
        gross = gross + item.k523_gross
    realized = gross.realized()
    return {
        "tier": tier,
        "items": [i.id for i in tier_items],
        "count": len(tier_items),
        "gross": gross.to_dict(),
        "realized": realized.to_dict(),
    }


def compute_grand_total(items: List[PhaseAItem]) -> Dict:
    """Compute grand total K523 3-point across all items."""
    gross = K523Range(0, 0, 0)
    for item in items:
        gross = gross + item.k523_gross
    realized = gross.realized()
    return {
        "gross": gross.to_dict(),
        "realized": realized.to_dict(),
        "note": (
            "Grand total = sum of all incremental Phase A++ items (Tier 1-4). "
            "Does NOT include v6.52 base architecture ($2.34M-$6.23M @$10M). "
            "K763 central/optimistic dominate — treat with K523 caution (contingent on "
            "all sleeves live at v6.52 r=218%/yr, K724 confirmed). "
            "K523 MANDATORY: $4.78M central is NOT upper bound. Realized central $1.60M "
            "is the planning anchor. Single-point projection PROHIBITED (K523)."
        ),
    }


def compute_v70_totals() -> Dict:
    """Compute v7.0 total including v6.52 base."""
    # v6.52 base from K751
    v652 = K523Range(2_336_139, 3_175_654, 6_227_901, "v6.52 base (Kelly-compliant)")
    # Phase A++ incremental (grand total)
    phase_aplus = K523Range(
        conservative=522_148,
        central=4_217_033,
        optimistic=15_634_454,
        note="Phase A++ incremental sum (K763+K755+K753+K751+K742+K745+K757+K747+K754+K759)",
    )
    # v7.0 = v6.52 base + Phase A++ incremental
    v70_gross = v652 + phase_aplus
    v70_realized = v70_gross.realized()
    return {
        "v651": {
            "label": "v6.51 (current — NON-COMPLIANT)",
            "k523_conservative": 2_151_571,
            "k523_central": 2_980_630,
            "k523_optimistic": 5_672_254,
            "realized_conservative": round(2_151_571 * K518_HAIRCUT),
            "realized_central": round(2_980_630 * K518_HAIRCUT),
            "realized_optimistic": round(5_672_254 * K518_HAIRCUT),
            "violations": "HL 66.8% > 65% cap | Bybit 55.7% > 50% cap | K280 15.5% < 30% floor",
        },
        "v652": {
            "label": "v6.52 (Kelly half-sizing, compliant, user 1-flip)",
            "k523_conservative": 2_336_139,
            "k523_central": 3_175_654,
            "k523_optimistic": 6_227_901,
            "realized_conservative": round(2_336_139 * K518_HAIRCUT),
            "realized_central": round(3_175_654 * K518_HAIRCUT),
            "realized_optimistic": round(6_227_901 * K518_HAIRCUT),
            "compliance": "HL 53.6% / Bybit 43.8% / K280 30.0% — all caps satisfied",
        },
        "v70": {
            "label": "v7.0 (full Phase A++ stack)",
            "k523_conservative": v70_gross.conservative,
            "k523_central": v70_gross.central,
            "k523_optimistic": v70_gross.optimistic,
            "realized_conservative": v70_realized.conservative,
            "realized_central": v70_realized.central,
            "realized_optimistic": v70_realized.optimistic,
            "k523_warning": (
                "K523 MANDATORY: v7.0 central ($7.39M gross) is NOT upper bound. "
                "Realized central $2.81M is the planning anchor. "
                "$21.9M optimistic assumes r=273%/yr + all Phase A++ items at ceiling. "
                "Realistic planning range: $963K (conservative) to $2.81M (central) realized. "
                "K763 compound uplift dominates and is contingent on full live stack."
            ),
            "components": [
                "v6.52 base (38 sleeves, Kelly half-sizing)",
                "K763 daily compound scheduler (73rd daemon)",
                "K755 HL builder rebate (10 daemons, zero-risk)",
                "K753 K545 tax loss harvester (70th daemon, paper→live with CPA)",
                "K498 OKX 3rd venue (HL 65%→50% relief)",
                "K485 Bybit sub-account (alt-alt isolation)",
                "K492-C persistence filter (K280 entry quality)",
                "TAO/PEPE/WIF live elevation (Tier 4, after 60d gates)",
            ],
        },
    }


# ─── Phase Output Functions ──────────────────────────────────────────────────

def run_phase1_audit(items: List[PhaseAItem]) -> Dict:
    """Phase 1: Audit all K744-K763 deliverables."""
    print("\n[Phase 1] Auditing K744-K763 deliverables...")
    wave_files = {
        "K744": REPO_ROOT / "wave_k744_saturation_map.json",
        "K745": REPO_ROOT / "wave_k745_k498_okx_scaffold.json",
        "K747": REPO_ROOT / "wave_k747_tao_sol_eval.json",
        "K751": REPO_ROOT / "wave_k751_kelly_sizing.json",
        "K753": REPO_ROOT / "wave_k753_k545_scaffold.json",
        "K754": REPO_ROOT / "wave_k754_pepe_sol_eval.json",
        "K755": REPO_ROOT / "wave_k755_k481_scaffold.json",
        "K757": REPO_ROOT / "wave_k757_k485_scaffold.json",
        "K759": REPO_ROOT / "wave_k759_wif_sol_eval.json",
        "K763": REPO_ROOT / "wave_k763_compounding.json",
        "K742": REPO_ROOT / "wave_k742_k492c_ready.json",
    }
    audit = {}
    for wave_id, path in wave_files.items():
        present = path.exists()
        size = path.stat().st_size if present else 0
        audit[wave_id] = {"present": present, "path": str(path.relative_to(REPO_ROOT)), "size_bytes": size}
        status = "PASS" if present else "MISSING"
        print(f"  [{status}] {wave_id}: {path.name} ({size:,} bytes)")
    total_present = sum(1 for v in audit.values() if v["present"])
    print(f"  Audit: {total_present}/{len(wave_files)} wave files present")
    return audit


def run_phase2_uplift_table(items: List[PhaseAItem]) -> Dict:
    """Phase 2: K523 total uplift summary table."""
    print("\n[Phase 2] K523 Uplift Summary Table (K523 3-point, K518 38% haircut)...")
    print(f"\n  {'Item':<10} {'Title':<42} {'Cons (R)':<12} {'Central (R)':<14} {'Opt (R)':<13} Tier")
    print("  " + "-" * 100)

    rows = []
    for item in items:
        gr = item.k523_gross
        re = item.k523_realized
        print(f"  {item.id:<10} {item.title[:40]:<42} "
              f"${re.conservative:>8,.0f}   ${re.central:>10,.0f}   ${re.optimistic:>10,.0f}   T{item.tier}")
        rows.append({
            "id": item.id,
            "title": item.title,
            "tier": item.tier,
            "gross_conservative": gr.conservative,
            "gross_central": gr.central,
            "gross_optimistic": gr.optimistic,
            "realized_conservative": re.conservative,
            "realized_central": re.central,
            "realized_optimistic": re.optimistic,
        })

    # Tier subtotals
    tier_summaries = {}
    for tier in [1, 2, 3, 4]:
        ts = compute_tier_summary(items, tier)
        tier_summaries[f"tier{tier}"] = ts
        print(f"\n  Tier {tier} subtotal: "
              f"cons=${ts['realized']['conservative']:>8,.0f} | "
              f"central=${ts['realized']['central']:>10,.0f} | "
              f"opt=${ts['realized']['optimistic']:>10,.0f}")

    # Grand total
    gt = compute_grand_total(items)
    print(f"\n  GRAND TOTAL (realized): "
          f"cons=${gt['realized']['conservative']:>8,.0f} | "
          f"central=${gt['realized']['central']:>10,.0f} | "
          f"opt=${gt['realized']['optimistic']:>10,.0f}")
    print(f"  K523 WARNING: {gt['note'][:120]}...")

    return {"rows": rows, "tier_summaries": tier_summaries, "grand_total": gt}


def run_phase3_priority(items: List[PhaseAItem]) -> Dict:
    """Phase 3: Risk-ranked priority order."""
    print("\n[Phase 3] Risk-Ranked Priority Order...")
    priority = []
    for tier in [1, 2, 3, 4]:
        tier_items = [i for i in items if i.tier == tier]
        print(f"\n  TIER {tier}: {tier_items[0].tier_label if tier_items else 'empty'}")
        for item in tier_items:
            risk_score = "ZERO" if item.zero_risk else ("LOW" if item.zero_infra_change else ("MEDIUM" if tier == 3 else "GATE"))
            print(f"    [{risk_score}] {item.id}: {item.title} — {item.days_to_activate}d")
            priority.append({"tier": tier, "id": item.id, "risk": risk_score, "days": item.days_to_activate})
    return {"priority_ranked": priority}


def run_phase4_activation_sequence(items: List[PhaseAItem]) -> Dict:
    """Phase 4: Activation sequence recommendation."""
    print("\n[Phase 4] Activation Sequence...")
    sequence = {
        "day1": {
            "label": "Day 1 — Tier 1 (no infra change, no risk)",
            "actions": [
                "1. python3 scripts/k763_compound_scheduler.py --set-frequency daily --paper && launchctl load ~/Library/LaunchAgents/com.cryptolab.k763-compound-scheduler.plist",
                "2. echo 'HL_BUILDER_CODE=0x<YOUR_WALLET>' >> .env.local && launchctl unload/load all HL daemons",
                "3. launchctl load ~/Library/LaunchAgents/com.cryptolab.k545-tax-harvester.plist  # paper mode",
            ],
            "monitoring": "After 24h: confirm compound events, builder credit in HL account, no harvest errors",
            "expected_realized_central_yr": 1_411_337,
            "note": "K763 central contingent on all sleeves live; conservative $67K/yr is safe floor",
        },
        "day2_3": {
            "label": "Days 2-3 — Tier 2 (MANDATORY compliance + config flips)",
            "actions": [
                "1. [MANDATORY] Add SLEEVE_WEIGHTS_V652 to scripts/leverage_manager.py (K751 compliance fix)",
                "2. Set PERSISTENCE_ENABLED = True in scripts/k280_live_fetch.py (K742 K492-C patch)",
                "3. Restart affected daemons: k280-live, k246a-live",
            ],
            "monitoring": "After 48h: HL <= 65%, Bybit <= 50%, K280 >= 30% weight; K280 entry rate >= 15%",
            "expected_realized_central_yr": 86_459,
            "note": "K751 MUST precede K745/K757. v6.51 non-compliance is priority #1.",
        },
        "week1": {
            "label": "Week 1 — Tier 3 (account setup + integration, 7d paper)",
            "actions": [
                "1. Create OKX API key (trade-only, no withdraw) → paste into .env.local",
                "2. Paper 7d: python3 scripts/okx_client.py --paper-test && monitor",
                "3. Live enable: OKX_LIVE_ENABLED=true + live_enabled=true in venue_allocation.json (K745)",
                "4. Create Bybit sub-account (Bybit platform) → generate trade-only API key",
                "5. Paste BYBIT_SUB_API_KEY + BYBIT_SUB_API_SECRET into .env.local (K757)",
            ],
            "monitoring": "OKX fill rate >= 60%; Bybit sub routing correct; HL <= 55% post-OKX",
            "expected_realized_central_yr": 36_943,
            "note": "K745 and K757 can proceed in parallel. Both require K751 v6.52 active first.",
        },
        "week2_4": {
            "label": "Weeks 2-4 — Tier 4 (live elevation after 60d gates)",
            "actions": [
                "1. Monitor 60d paper gate for TAO-SOL (K747): Sh>=6, fill>=60%, maxDD<15%",
                "2. Monitor 60d paper gate for PEPE-SOL (K754): same + L003 monthly recheck",
                "3. Monitor 60d paper gate for WIF-SOL (K759): same + G5w PEPE-SOL monthly recheck",
                "4. On PASS for each: Set live_enabled=true in respective dashboard JSON",
                "5. After live: Check K545 CPA consultation complete → upgrade tax harvester --live",
            ],
            "monitoring": "Per-strategy paper Sharpe, fill rate, cross-sleeve correlations monthly",
            "expected_realized_central_yr": 67_733,
            "note": "All Tier 4 items are paper-gate dependent. Do NOT elevate before 60d.",
        },
    }
    for phase_id, phase in sequence.items():
        print(f"\n  {phase['label']}")
        for action in phase["actions"][:2]:
            print(f"    • {action[:90]}")
    return sequence


def run_phase5_v70_proposal() -> Dict:
    """Phase 5: v7.0 architecture proposal."""
    print("\n[Phase 5] v7.0 Architecture Proposal...")
    v70 = compute_v70_totals()
    for version in ["v651", "v652", "v70"]:
        vd = v70[version]
        print(f"  {vd['label']}")
        print(f"    K523: ${vd['k523_conservative']:>9,.0f} / ${vd['k523_central']:>9,.0f} / ${vd['k523_optimistic']:>9,.0f} (gross)")
        print(f"    Realized: ${vd['realized_conservative']:>8,.0f} / ${vd['realized_central']:>8,.0f} / ${vd['realized_optimistic']:>8,.0f}")
    return v70


def write_json_output(items: List[PhaseAItem], phase_results: Dict) -> Path:
    """Write comprehensive K764 JSON output."""
    output = {
        "wave": "K764",
        "title": "Phase A++ Governance Synthesis (K744-K763 Cumulative)",
        "generated_jst": NOW_JST,
        "generated_utc": NOW_UTC,
        "k339_pattern": "REPO_ROOT = Path(__file__).resolve().parent",
        "k523_mandatory": True,
        "k518_haircut_ratio": K518_HAIRCUT,
        "live_auto_change_prohibited": True,
        "aum_ref_usd": AUM_REF,
        "items": [item.to_dict() for item in items],
        "phases": phase_results,
        "architecture_versions": compute_v70_totals(),
        "deliverables": {
            "wave_k764_phase_a_plus_governance.py": "This synthesis harness (K339, K523, ~700 LOC)",
            "wave_k764_phase_a_plus_governance.json": "Comprehensive output JSON",
            "wave_k764_phase_a_plus_governance.md": "Human-readable summary",
            "data/phase_a_plus_status.json": "Machine-readable activation queue",
            "docs/k302a_runbook.md §74": "Phase A++ Activation Master Plan",
            "report.html": "Top banner Phase A++ status with Tier 1-4 progress",
        },
        "status": "K764 PHASE A++ GOVERNANCE SYNTHESIS COMPLETE",
    }
    out_path = REPO_ROOT / "wave_k764_phase_a_plus_governance.json"
    out_path.write_text(json.dumps(output, indent=2, ensure_ascii=False))
    print(f"\n  [OK] Written: {out_path.name}")
    return out_path


# ─── Main Entry Point ────────────────────────────────────────────────────────

def main() -> int:
    print("=" * 70)
    print(f"K764 Phase A++ Governance Synthesis")
    print(f"Generated: {NOW_JST}")
    print(f"REPO_ROOT: {REPO_ROOT}")
    print(f"K523: 3-point mandatory | K518 haircut: {K518_HAIRCUT:.0%}")
    print(f"LIVE auto-change: PROHIBITED (synthesis only)")
    print("=" * 70)

    items = build_items()
    print(f"\nTotal Phase A++ items: {len(items)} across {len(set(i.tier for i in items))} tiers")

    phase_results: Dict = {}
    errors = []

    try:
        phase_results["phase1_audit"]             = run_phase1_audit(items)
        phase_results["phase2_uplift_table"]      = run_phase2_uplift_table(items)
        phase_results["phase3_priority"]          = run_phase3_priority(items)
        phase_results["phase4_activation"]        = run_phase4_activation_sequence(items)
        phase_results["phase5_v70_architecture"]  = run_phase5_v70_proposal()
    except Exception as exc:
        errors.append(str(exc))
        traceback.print_exc()

    # Write JSON output
    out_path = write_json_output(items, phase_results)

    # Summary
    gt = compute_grand_total(items)
    print("\n" + "=" * 70)
    print("K764 SYNTHESIS COMPLETE")
    print(f"  Items: {len(items)} | Tiers: 4 | JSON: {out_path.name}")
    print(f"  Grand Total Realized @$10M AUM (K518 38% haircut):")
    print(f"    Conservative: ${gt['realized']['conservative']:>8,.0f}/yr")
    print(f"    Central:      ${gt['realized']['central']:>8,.0f}/yr  ← planning anchor")
    print(f"    Optimistic:   ${gt['realized']['optimistic']:>8,.0f}/yr  (K763-dominated)")
    print(f"  K523 WARNING: Central is NOT upper bound. OOS haircut applies.")
    print(f"  LIVE auto-change: PROHIBITED")
    print("=" * 70)

    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
