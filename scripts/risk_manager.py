#!/usr/bin/env python3
"""
risk_manager.py — K757 Risk Manager (Bybit dual-account + OKX-extended)
=========================================================================
Tracks and enforces venue concentration limits across HL, Bybit (main+sub), and OKX.
K757 update: recognizes 2 Bybit accounts (main + sub) in concentration calculation.
K745 update: recognizes OKX positions in concentration calculation.

Concentration caps (K757):
  HL:         65.0% max (K524 exact cap — HARD LIMIT, no exceptions)
  Bybit_main: 50.0% max (K485 per-account cap)
  Bybit_sub:  50.0% max (K757 sub-account — same per-account limit)
  Bybit total: main + sub (effective headroom doubled vs single account)
  OKX:        40.0% max (K745 initial, expand to 50% after 30d track record)

Relief mechanisms:
  K757: Bybit sub → 5.7pp over-cap relieved; total Bybit capacity ~doubled
  K498: OKX → HL 65% → ~50% over 1-2 months as new sleeves route to OKX
  Combined: unlocks ~$1.5M HL headroom + $500K Bybit headroom at $10M AUM

Architecture:
  RiskSnapshot      — point-in-time concentration snapshot (includes Bybit_main + Bybit_sub)
  RiskManager       — concentration tracking + cap enforcement
  check_trade()     — pre-trade risk check (returns ALLOW/BLOCK + reason)
  update_position() — update position after confirmed fill
  write_risk_report() — write data/risk_manager_report.json

K339: REPO_ROOT from __file__, no /Users/ literals.
LIVE modification: NONE — analytical + pre-trade check only.

Integration with smart_router.py + bybit_multi_account_client.py:
  from scripts.risk_manager import RiskManager
  rm = RiskManager.from_cache()
  check = rm.check_trade("Bybit_sub", 500_000)   # check sub-account cap
  check2 = rm.check_trade("OKX", 500_000)
  if check["allow"]:
      # route to Bybit sub-account via bybit_multi_account_client

Usage:
  python3 scripts/risk_manager.py --report
  python3 scripts/risk_manager.py --check-trade Bybit_sub 500000
  python3 scripts/risk_manager.py --check-trade OKX 500000 --symbol INJ
  python3 scripts/risk_manager.py --bybit-capacity       # K757 dual-account view
  python3 scripts/risk_manager.py --update-position Bybit_sub 500000 --symbol TIA
"""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# ── K339 canonical paths ──────────────────────────────────────────────────────
REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR  = REPO_ROOT / "data"
LOGS_DIR  = REPO_ROOT / "logs"
CACHE_DIR = REPO_ROOT / "cache"

DATA_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)
CACHE_DIR.mkdir(exist_ok=True)

JST = timezone(timedelta(hours=9))

# ── Concentration caps (K757) ─────────────────────────────────────────────────
CONCENTRATION_CAPS: Dict[str, float] = {
    "HL":         0.650,   # K524 exact cap — HARD LIMIT
    "Bybit":      0.500,   # K485 legacy single-account view (for backward compat)
    "Bybit_main": 0.500,   # K757: main account per-account cap
    "Bybit_sub":  0.500,   # K757: sub-account per-account cap (same limit)
    "OKX":        0.400,   # K745 initial; expand after 30d track record
    "Aevo":       0.100,   # scaffold-only
    "dYdX":       0.100,   # scaffold-only
    "Lighter":    0.050,
    "Vertex":     0.050,
}

# K757: Bybit aliases — Bybit_main + Bybit_sub map to same Bybit exchange
BYBIT_ACCOUNTS = ("Bybit_main", "Bybit_sub")

# Relief targets
HL_TARGET_AFTER_OKX     = 0.50   # from 0.65 → target after OKX migration
OKX_TARGET_EXPANDED     = 0.50   # OKX expansion target after 30d track record
BYBIT_SUB_HEADROOM_PP   = 0.50   # K757: sub adds up to 50pp more Bybit headroom

# Emergency thresholds (trigger emergency exit check)
EMERGENCY_THRESHOLDS: Dict[str, float] = {
    "HL":         0.70,   # 70% → trigger emergency_hl_exit.py review
    "Bybit":      0.55,   # legacy
    "Bybit_main": 0.55,   # K757: per-account emergency
    "Bybit_sub":  0.55,   # K757: per-account emergency
    "OKX":        0.45,
}

# Tail loss estimates (K524 per MEMORY.md)
TAIL_LOSS_ESTIMATES: Dict[str, float] = {
    "HL":    0.040,   # 4.0% expected tail loss (platform risk)
    "Bybit": 0.020,
    "OKX":   0.025,   # slightly higher (newer venue for us)
    "Aevo":  0.050,
    "dYdX":  0.040,
}

# ── State paths ───────────────────────────────────────────────────────────────
POSITION_CACHE  = DATA_DIR / "risk_positions.json"
RISK_REPORT     = DATA_DIR / "risk_manager_report.json"
RISK_HISTORY    = DATA_DIR / "risk_manager_history.jsonl"


# ─────────────────────────────────────────────────────────────────────────────
# Data structures
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class PositionRecord:
    """A single position record: one strategy × one venue × one symbol."""
    strategy_id:   str
    venue:         str
    symbol:        str
    notional_usd:  float        # absolute notional (not signed — use side for direction)
    side:          str          # "long" | "short"
    entry_price:   float        = 0.0
    updated_utc:   str          = ""

    def to_dict(self) -> dict:
        return {
            "strategy_id": self.strategy_id,
            "venue":       self.venue,
            "symbol":      self.symbol,
            "notional_usd": self.notional_usd,
            "side":        self.side,
            "entry_price": self.entry_price,
            "updated_utc": self.updated_utc,
        }


@dataclass
class RiskSnapshot:
    """Point-in-time risk snapshot: all positions + concentration metrics."""
    total_aum_usd:      float
    venue_notional:     Dict[str, float]    # {venue: total_notional_usd}
    venue_pct:          Dict[str, float]    # {venue: pct_of_aum}
    caps:               Dict[str, float]    # {venue: cap_pct}
    violations:         List[str]           # venues above cap
    near_cap_warnings:  List[str]           # venues within 5pp of cap
    tail_risk_usd:      float               # tail loss estimate @ current concentration
    hl_headroom_usd:    float               # USD remaining before HL cap
    okx_headroom_usd:   float              # USD remaining before OKX cap
    timestamp_utc:      str

    @property
    def hl_pct(self) -> float:
        return self.venue_pct.get("HL", 0.0)

    @property
    def okx_pct(self) -> float:
        return self.venue_pct.get("OKX", 0.0)

    @property
    def bybit_pct(self) -> float:
        return self.venue_pct.get("Bybit", 0.0)

    def to_dict(self) -> dict:
        return {
            "total_aum_usd": self.total_aum_usd,
            "venue_notional": self.venue_notional,
            "venue_pct":     {k: round(v, 4) for k, v in self.venue_pct.items()},
            "caps":          self.caps,
            "violations":    self.violations,
            "near_cap_warnings": self.near_cap_warnings,
            "tail_risk_usd": round(self.tail_risk_usd, 0),
            "hl_headroom_usd": round(self.hl_headroom_usd, 0),
            "okx_headroom_usd": round(self.okx_headroom_usd, 0),
            "hl_pct":        round(self.hl_pct, 4),
            "okx_pct":       round(self.okx_pct, 4),
            "bybit_pct":     round(self.bybit_pct, 4),
            "timestamp_utc": self.timestamp_utc,
        }


@dataclass
class TradeCheckResult:
    """Result of a pre-trade concentration check."""
    allow:         bool
    venue:         str
    symbol:        str
    notional_usd:  float
    current_pct:   float         # current concentration before trade
    projected_pct: float         # projected concentration after trade
    cap_pct:       float
    headroom_usd:  float
    reason:        str
    block_reason:  str = ""      # non-empty if allow=False
    warnings:      List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "allow":         self.allow,
            "venue":         self.venue,
            "symbol":        self.symbol,
            "notional_usd":  self.notional_usd,
            "current_pct":   round(self.current_pct, 4),
            "projected_pct": round(self.projected_pct, 4),
            "cap_pct":       self.cap_pct,
            "headroom_usd":  round(self.headroom_usd, 0),
            "reason":        self.reason,
            "block_reason":  self.block_reason,
            "warnings":      self.warnings,
        }


# ─────────────────────────────────────────────────────────────────────────────
# Risk Manager
# ─────────────────────────────────────────────────────────────────────────────

class RiskManager:
    """
    K745 multi-venue risk manager.
    Tracks HL + Bybit + OKX positions and enforces concentration caps.

    Key methods:
      check_trade(venue, notional_usd)  → pre-trade ALLOW/BLOCK
      update_position(...)              → record confirmed fill
      get_snapshot()                    → current concentration state
      write_risk_report()               → write data/risk_manager_report.json

    Cap enforcement (K745):
      HL:    65.0% — K524 exact cap (HARD LIMIT, no exceptions)
      Bybit: 50.0% — K485
      OKX:   40.0% — K745 initial (expand to 50% after 30d track record)
    """

    def __init__(
        self,
        total_aum:    float = 10_000_000.0,
        positions:    Optional[List[PositionRecord]] = None,
        caps:         Optional[Dict[str, float]] = None,
    ):
        self.total_aum = total_aum
        self._positions: List[PositionRecord] = positions or []
        self._caps = caps or CONCENTRATION_CAPS

    # ── Position management ───────────────────────────────────────────────────

    def update_position(
        self,
        venue:        str,
        symbol:       str,
        notional_usd: float,
        side:         str,
        strategy_id:  str = "unknown",
        entry_price:  float = 0.0,
    ) -> None:
        """
        Add or update a position record.
        Existing positions matching (venue, symbol, strategy_id) are replaced.
        Set notional_usd=0 to remove a position.
        """
        ts = datetime.now(timezone.utc).isoformat()

        # Remove existing record for this (strategy, venue, symbol) triple
        self._positions = [
            p for p in self._positions
            if not (p.venue == venue and p.symbol == symbol and p.strategy_id == strategy_id)
        ]

        if notional_usd > 0:
            self._positions.append(PositionRecord(
                strategy_id=strategy_id,
                venue=venue,
                symbol=symbol,
                notional_usd=notional_usd,
                side=side,
                entry_price=entry_price,
                updated_utc=ts,
            ))

        self._save_positions()

        # Log to history
        entry = {
            "ts_jst":       datetime.now(JST).strftime("%Y-%m-%d %H:%M JST"),
            "action":       "update_position",
            "venue":        venue, "symbol": symbol,
            "notional_usd": notional_usd, "side": side,
            "strategy_id":  strategy_id,
            "hl_pct_after": round(self._venue_pct("HL"), 4),
            "okx_pct_after": round(self._venue_pct("OKX"), 4),
        }
        try:
            with open(RISK_HISTORY, "a") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception:
            pass

    def _venue_notional(self, venue: str) -> float:
        return sum(p.notional_usd for p in self._positions if p.venue == venue)

    def _total_notional(self) -> float:
        return sum(p.notional_usd for p in self._positions)

    def _venue_pct(self, venue: str) -> float:
        if self.total_aum <= 0:
            return 0.0
        return self._venue_notional(venue) / self.total_aum

    # ── Pre-trade check ───────────────────────────────────────────────────────

    def check_trade(
        self,
        venue:        str,
        notional_usd: float,
        symbol:       str = "",
        strategy_id:  str = "unknown",
    ) -> TradeCheckResult:
        """
        Pre-trade concentration check.
        Returns TradeCheckResult with allow=True/False.

        Checks:
          1. Venue cap: projected_pct > cap → BLOCK
          2. Emergency threshold: projected_pct > emergency → WARN (still allow with warning)
          3. OKX live gate: OKX must be live-enabled (venue_allocation.json)

        Called by multi_venue_router.py before submitting any order.
        """
        cap = self._caps.get(venue, 1.0)
        current_notional = self._venue_notional(venue)
        current_pct      = self._venue_pct(venue)
        projected_notional = current_notional + notional_usd
        projected_pct    = projected_notional / self.total_aum if self.total_aum > 0 else 1.0
        headroom_usd     = max(0.0, (cap - current_pct) * self.total_aum)

        warnings: List[str] = []
        block_reason = ""

        # Hard cap check
        if projected_pct > cap:
            block_reason = (
                f"{venue} cap exceeded: projected {projected_pct:.1%} > cap {cap:.0%} "
                f"(adding ${notional_usd:,.0f} to current ${current_notional:,.0f})"
            )
            return TradeCheckResult(
                allow=False, venue=venue, symbol=symbol,
                notional_usd=notional_usd,
                current_pct=current_pct, projected_pct=projected_pct,
                cap_pct=cap, headroom_usd=headroom_usd,
                reason="CAP_EXCEEDED",
                block_reason=block_reason, warnings=warnings,
            )

        # Near-cap warning (within 5pp of cap)
        if projected_pct > cap - 0.05:
            warnings.append(
                f"{venue} near cap: projected {projected_pct:.1%} within 5pp of {cap:.0%}"
            )

        # Emergency threshold warning
        emerg = EMERGENCY_THRESHOLDS.get(venue, 1.0)
        if projected_pct > emerg:
            warnings.append(
                f"EMERGENCY threshold: {venue} {projected_pct:.1%} > {emerg:.0%} "
                f"— review emergency exit triggers"
            )

        # OKX-specific: check if live-enabled
        if venue == "OKX":
            alloc_config = self._load_venue_alloc()
            okx_live = alloc_config.get("venues", {}).get("OKX", {}).get("live_enabled", False)
            if not okx_live:
                warnings.append(
                    "OKX not live-enabled — set OKX_LIVE_ENABLED=true in .env.local + "
                    "update data/venue_allocation.json venues.OKX.live_enabled=true"
                )

        reason = (
            f"ALLOW: {venue} {current_pct:.1%} → {projected_pct:.1%} / cap {cap:.0%} "
            f"(headroom ${headroom_usd:,.0f})"
        )

        return TradeCheckResult(
            allow=True, venue=venue, symbol=symbol,
            notional_usd=notional_usd,
            current_pct=current_pct, projected_pct=projected_pct,
            cap_pct=cap, headroom_usd=headroom_usd,
            reason=reason, block_reason="", warnings=warnings,
        )

    def _load_venue_alloc(self) -> dict:
        if not (DATA_DIR / "venue_allocation.json").exists():
            return {}
        try:
            with open(DATA_DIR / "venue_allocation.json") as f:
                return json.load(f)
        except Exception:
            return {}

    # ── Snapshot ──────────────────────────────────────────────────────────────

    def get_snapshot(self) -> RiskSnapshot:
        """Compute current concentration snapshot across all venues."""
        ts = datetime.now(timezone.utc).isoformat()
        all_venues = set(self._caps.keys()) | {p.venue for p in self._positions}

        venue_notional = {}
        venue_pct      = {}
        violations     = []
        near_cap       = []

        for venue in sorted(all_venues):
            notional = self._venue_notional(venue)
            pct      = notional / self.total_aum if self.total_aum > 0 else 0.0
            venue_notional[venue] = round(notional, 0)
            venue_pct[venue]      = pct
            cap = self._caps.get(venue, 1.0)
            if pct >= cap:
                violations.append(venue)
            elif pct >= cap - 0.05:
                near_cap.append(venue)

        # Tail risk: expected loss = sum(venue_notional × tail_loss_pct)
        tail_risk_usd = sum(
            venue_notional.get(v, 0) * TAIL_LOSS_ESTIMATES.get(v, 0.02)
            for v in venue_notional
        )

        hl_cap    = self._caps.get("HL", 0.65)
        okx_cap   = self._caps.get("OKX", 0.40)
        hl_head   = max(0.0, (hl_cap  - venue_pct.get("HL",  0.0)) * self.total_aum)
        okx_head  = max(0.0, (okx_cap - venue_pct.get("OKX", 0.0)) * self.total_aum)

        return RiskSnapshot(
            total_aum_usd=self.total_aum,
            venue_notional=venue_notional,
            venue_pct=venue_pct,
            caps=dict(self._caps),
            violations=violations,
            near_cap_warnings=near_cap,
            tail_risk_usd=tail_risk_usd,
            hl_headroom_usd=hl_head,
            okx_headroom_usd=okx_head,
            timestamp_utc=ts,
        )

    # ── OKX-specific helpers ──────────────────────────────────────────────────

    def okx_positions(self) -> List[PositionRecord]:
        """Return all OKX positions."""
        return [p for p in self._positions if p.venue == "OKX"]

    def hl_positions(self) -> List[PositionRecord]:
        """Return all HL positions."""
        return [p for p in self._positions if p.venue == "HL"]

    def bybit_positions(self, account: Optional[str] = None) -> List[PositionRecord]:
        """
        Return Bybit positions.
        account=None: all Bybit (Bybit + Bybit_main + Bybit_sub)
        account="main": Bybit_main + legacy Bybit positions
        account="sub": Bybit_sub positions
        """
        if account is None:
            return [p for p in self._positions if p.venue in ("Bybit", "Bybit_main", "Bybit_sub")]
        if account == "main":
            return [p for p in self._positions if p.venue in ("Bybit", "Bybit_main")]
        if account == "sub":
            return [p for p in self._positions if p.venue == "Bybit_sub"]
        return []

    def bybit_dual_account_capacity(self) -> dict:
        """
        K757: Compute dual-account Bybit capacity view.
        Returns per-account and combined headroom.
        """
        aum = self.total_aum
        main_notional = self._venue_notional("Bybit") + self._venue_notional("Bybit_main")
        sub_notional  = self._venue_notional("Bybit_sub")
        main_pct = main_notional / aum if aum > 0 else 0.0
        sub_pct  = sub_notional  / aum if aum > 0 else 0.0
        total_pct = main_pct + sub_pct

        cap = CONCENTRATION_CAPS.get("Bybit_main", 0.50)
        main_head = max(0.0, (cap - main_pct) * aum)
        sub_head  = max(0.0, (cap - sub_pct)  * aum)
        total_head = main_head + sub_head

        return {
            "wave":           "K757",
            "main_pct":       round(main_pct, 4),
            "sub_pct":        round(sub_pct, 4),
            "total_bybit_pct": round(total_pct, 4),
            "main_headroom_usd": round(main_head, 0),
            "sub_headroom_usd":  round(sub_head, 0),
            "total_headroom_usd": round(total_head, 0),
            "per_account_cap": cap,
            "main_violations": main_pct >= cap,
            "sub_violations":  sub_pct  >= cap,
            "k523_3point": {
                "conservative_usd_yr": 20_000,
                "mid_usd_yr":          50_000,
                "optimistic_usd_yr":  120_000,
                "basis": "Bybit sub relief: +5pp cons / +10pp mid / +20pp opt vs current 55.7% over-cap",
            },
            "note": (
                f"K757: Bybit dual-account. Before: 55.7% over 50% cap. "
                f"After: main={main_pct:.1%} + sub={sub_pct:.1%} each vs 50% cap. "
                f"Total headroom: ${total_head:,.0f} (was ${max(0,(cap-main_pct)*aum):,.0f})."
            ),
        }

    def hl_cap_relief_projection(
        self,
        new_okx_notional_usd: float,
    ) -> dict:
        """
        Project HL concentration relief if {new_okx_notional_usd} migrates from HL to OKX.

        K745: after K498 OKX live activation, new paired-trade sleeves (e.g. K500 INJ-BTC 70% OKX)
        reduce HL concentration over ~1-2 months.

        Returns: {hl_before_pct, hl_after_pct, relief_pp, okx_after_pct, unlocked_usd}
        """
        hl_before = self._venue_pct("HL")
        okx_before = self._venue_pct("OKX")

        # If migrating X from HL→OKX:
        # HL after = (HL_notional - X) / AUM, OKX after = (OKX_notional + X) / AUM
        hl_notional_before  = self._venue_notional("HL")
        okx_notional_before = self._venue_notional("OKX")

        migrate_usd = min(new_okx_notional_usd, hl_notional_before)
        hl_after    = (hl_notional_before - migrate_usd) / self.total_aum if self.total_aum > 0 else 0.0
        okx_after   = (okx_notional_before + migrate_usd) / self.total_aum if self.total_aum > 0 else 0.0
        relief_pp   = hl_before - hl_after

        hl_cap       = self._caps.get("HL", 0.65)
        unlocked_usd = relief_pp * self.total_aum   # USD newly available for HL deployment

        return {
            "hl_before_pct":  round(hl_before, 4),
            "hl_after_pct":   round(hl_after, 4),
            "relief_pp":      round(relief_pp, 4),
            "okx_after_pct":  round(okx_after, 4),
            "okx_cap_pct":    self._caps.get("OKX", 0.40),
            "okx_cap_ok":     okx_after <= self._caps.get("OKX", 0.40),
            "migrate_usd":    round(migrate_usd, 0),
            "unlocked_usd":   round(unlocked_usd, 0),
            "new_alt_alt_capacity_usd": round(unlocked_usd, 0),
            "note": (
                f"HL: {hl_before:.1%}→{hl_after:.1%} ({relief_pp*100:.1f}pp relief). "
                f"OKX: {okx_before:.1%}→{okx_after:.1%}. "
                f"Unlocks ${unlocked_usd:,.0f} new HL headroom for alt-alt pairs."
            ),
        }

    # ── Persistence ──────────────────────────────────────────────────────────

    def _save_positions(self) -> None:
        payload = {
            "_wave":         "K745",
            "total_aum_usd": self.total_aum,
            "positions":     [p.to_dict() for p in self._positions],
            "saved_utc":     datetime.now(timezone.utc).isoformat(),
        }
        tmp = POSITION_CACHE.with_suffix(".tmp")
        with open(tmp, "w") as f:
            json.dump(payload, f, indent=2)
        tmp.replace(POSITION_CACHE)

    @classmethod
    def from_cache(cls, total_aum: float = 10_000_000.0) -> "RiskManager":
        """Load positions from data/risk_positions.json if present."""
        positions = []
        if POSITION_CACHE.exists():
            try:
                with open(POSITION_CACHE) as f:
                    data = json.load(f)
                for p in data.get("positions", []):
                    positions.append(PositionRecord(**{
                        k: v for k, v in p.items()
                        if k in PositionRecord.__dataclass_fields__  # type: ignore
                    }))
                total_aum = data.get("total_aum_usd", total_aum)
            except Exception as exc:
                print(f"  [RiskManager] Cache load error: {exc}", file=sys.stderr)
        return cls(total_aum=total_aum, positions=positions)

    def write_risk_report(self) -> Path:
        """Write current risk state to data/risk_manager_report.json."""
        snap = self.get_snapshot()
        now_jst = datetime.now(JST)

        # OKX integration projection
        okx_proj = self.hl_cap_relief_projection(new_okx_notional_usd=1_500_000.0)  # $1.5M migration example

        # K757 Bybit dual-account capacity
        bybit_dual = self.bybit_dual_account_capacity()

        payload = {
            "_wave":         "K757",
            "_source":       "risk_manager.py",
            "generated_jst": now_jst.strftime("%Y-%m-%d %H:%M JST"),
            "total_aum_usd": self.total_aum,
            "snapshot":      snap.to_dict(),
            "positions":     [p.to_dict() for p in self._positions],
            "caps":          self._caps,
            "emergency_thresholds": EMERGENCY_THRESHOLDS,
            "tail_loss_estimates":  TAIL_LOSS_ESTIMATES,
            "okx_integration_projection": okx_proj,
            "bybit_dual_account_capacity": bybit_dual,
            "hl_target_after_okx": HL_TARGET_AFTER_OKX,
            "okx_target_expanded": OKX_TARGET_EXPANDED,
            "summary": {
                "hl_pct":         round(snap.hl_pct,    4),
                "okx_pct":        round(snap.okx_pct,   4),
                "bybit_pct":      round(snap.bybit_pct, 4),
                "bybit_main_pct": round(bybit_dual["main_pct"], 4),
                "bybit_sub_pct":  round(bybit_dual["sub_pct"],  4),
                "bybit_total_headroom_usd": round(bybit_dual["total_headroom_usd"], 0),
                "hl_cap_relief_pp_from_okx": round(okx_proj["relief_pp"], 4),
                "violations": snap.violations,
                "tail_risk_usd": round(snap.tail_risk_usd, 0),
            },
        }

        tmp = RISK_REPORT.with_suffix(".tmp")
        with open(tmp, "w") as f:
            json.dump(payload, f, indent=2)
        tmp.replace(RISK_REPORT)
        print(f"  [RiskManager] Report: {RISK_REPORT.name}", file=sys.stderr)
        return RISK_REPORT


# ── K745 hardcoded scenario: HL at 65% cap + OKX unlocked ────────────────────

def _k745_scenario_report() -> dict:
    """
    K745 scenario: HL exactly at 65% cap, OKX at 0%.
    Shows how K498 OKX activation relieves concentration.
    @$10M AUM.
    """
    aum = 10_000_000.0
    rm  = RiskManager(
        total_aum=aum,
        positions=[
            PositionRecord("K280", "HL", "BTC",  3_750_000.0, "short"),
            PositionRecord("K280", "HL", "ETH",  1_000_000.0, "short"),
            PositionRecord("K280", "HL", "SOL",    750_000.0, "short"),
            PositionRecord("K297p","HL", "PAXG",   500_000.0, "long"),
            PositionRecord("K507_TIA_BTC","Bybit","TIA", 500_000.0, "short"),
            PositionRecord("K500_INJ_BTC","Bybit","INJ", 500_000.0, "short"),
            PositionRecord("K512_APT_BTC","Bybit","APT", 500_000.0, "short"),
            PositionRecord("K679_APT_SOL","Bybit","APT", 300_000.0, "short"),
            PositionRecord("K682_ATOM_SOL","Bybit","ATOM",300_000.0,"short"),
        ]
    )
    snap = rm.get_snapshot()
    proj = rm.hl_cap_relief_projection(1_500_000.0)

    # Simulate check_trade for new OKX sleeve (K500 INJ-BTC 70% OKX)
    check_okx = rm.check_trade("OKX", 350_000.0, "INJ", "K500_INJ_BTC_OKX")

    return {
        "scenario": "K745 HL@65%-cap OKX-unlock",
        "aum_usd": aum,
        "snapshot": snap.to_dict(),
        "hl_cap_relief_projection": proj,
        "new_okx_trade_check": check_okx.to_dict(),
    }


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> int:
    import argparse
    p = argparse.ArgumentParser(
        description="K745 Risk Manager — multi-venue concentration tracking (OKX extended)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 scripts/risk_manager.py --report           # write risk report
  python3 scripts/risk_manager.py --snapshot         # show current snapshot
  python3 scripts/risk_manager.py --check-trade OKX 500000
  python3 scripts/risk_manager.py --check-trade HL 100000 --symbol BTC
  python3 scripts/risk_manager.py --scenario        # K745 HL@65% + OKX unlock scenario
  python3 scripts/risk_manager.py --relief 1500000  # project HL relief from OKX migration
        """,
    )
    p.add_argument("--report",          action="store_true", help="Write risk report to data/")
    p.add_argument("--snapshot",        action="store_true", help="Show current concentration")
    p.add_argument("--check-trade",     nargs=2, metavar=("VENUE", "NOTIONAL"),
                   help="Pre-trade concentration check (use Bybit_main or Bybit_sub for K757)")
    p.add_argument("--symbol",          default="", help="Symbol for trade check")
    p.add_argument("--scenario",        action="store_true", help="K745 HL@65% + OKX scenario")
    p.add_argument("--relief",          type=float, metavar="NOTIONAL",
                   help="Project HL relief from routing NOTIONAL to OKX")
    p.add_argument("--bybit-capacity",  action="store_true",
                   help="K757: Show dual-account Bybit capacity (main + sub)")
    p.add_argument("--total-aum",       type=float, default=10_000_000.0)
    p.add_argument("--json",            action="store_true")
    args = p.parse_args()

    if args.scenario:
        result = _k745_scenario_report()
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            snap = result["snapshot"]
            print(f"\n=== K745 Risk Scenario: HL@65% + OKX Unlock ===")
            print(f"  AUM: ${args.total_aum:,.0f}")
            for venue, pct in snap["venue_pct"].items():
                notional = snap["venue_notional"].get(venue, 0)
                cap = snap["caps"].get(venue, 1.0)
                status = "CAP" if venue in snap["violations"] else "OK"
                print(f"  {venue:<8}  {pct:.1%} / {cap:.0%}  ${notional:>12,.0f}  [{status}]")
            proj = result["hl_cap_relief_projection"]
            print(f"\n  HL cap relief (routing ${proj['migrate_usd']:,.0f} to OKX):")
            print(f"    HL:  {proj['hl_before_pct']:.1%} → {proj['hl_after_pct']:.1%} ({proj['relief_pp']*100:.1f}pp)")
            print(f"    OKX: {proj['okx_after_pct']:.1%} (cap {proj['okx_cap_pct']:.0%}: {'OK' if proj['okx_cap_ok'] else 'EXCEED'})")
            print(f"    Unlocked: ${proj['unlocked_usd']:,.0f}")
        return 0

    rm = RiskManager.from_cache(total_aum=args.total_aum)

    if args.report:
        path = rm.write_risk_report()
        print(f"  Report: {path}")
        return 0

    if args.snapshot:
        snap = rm.get_snapshot()
        if args.json:
            print(json.dumps(snap.to_dict(), indent=2))
        else:
            print(f"\n=== Risk Snapshot ===")
            for venue, pct in sorted(snap.venue_pct.items()):
                cap = snap.caps.get(venue, 1.0)
                notional = snap.venue_notional.get(venue, 0)
                status = "CAP" if venue in snap.violations else ("WARN" if venue in snap.near_cap_warnings else "OK")
                print(f"  {venue:<8}  {pct:.1%} / {cap:.0%}  ${notional:>12,.0f}  [{status}]")
            print(f"\n  HL headroom:  ${snap.hl_headroom_usd:,.0f}")
            print(f"  OKX headroom: ${snap.okx_headroom_usd:,.0f}")
            print(f"  Tail risk:    ${snap.tail_risk_usd:,.0f}")
        return 0

    if args.check_trade:
        venue    = args.check_trade[0]
        notional = float(args.check_trade[1])
        result   = rm.check_trade(venue, notional, symbol=args.symbol)
        if args.json:
            print(json.dumps(result.to_dict(), indent=2))
        else:
            status = "ALLOW" if result.allow else "BLOCK"
            print(f"\n=== Trade Check: {venue} ${notional:,.0f} ===")
            print(f"  Result:  {status}")
            print(f"  Current: {result.current_pct:.1%}  Projected: {result.projected_pct:.1%}  Cap: {result.cap_pct:.0%}")
            print(f"  Headroom: ${result.headroom_usd:,.0f}")
            if not result.allow:
                print(f"  BLOCK:   {result.block_reason}")
            for w in result.warnings:
                print(f"  WARN:    {w}")
        return 0 if result.allow else 1

    if args.relief:
        proj = rm.hl_cap_relief_projection(args.relief)
        if args.json:
            print(json.dumps(proj, indent=2))
        else:
            print(f"\n=== HL Cap Relief Projection ===")
            print(f"  Migrate ${proj['migrate_usd']:,.0f} from HL → OKX")
            print(f"  HL: {proj['hl_before_pct']:.1%} → {proj['hl_after_pct']:.1%} ({proj['relief_pp']*100:.1f}pp)")
            print(f"  OKX: {proj['okx_after_pct']:.1%} / cap {proj['okx_cap_pct']:.0%}")
            print(f"  Unlocked: ${proj['unlocked_usd']:,.0f}")
            print(f"  {proj['note']}")
        return 0

    if args.bybit_capacity:
        cap = rm.bybit_dual_account_capacity()
        if args.json:
            print(json.dumps(cap, indent=2))
        else:
            print(f"\n=== K757 Bybit Dual-Account Capacity ===")
            print(f"  Main:  {cap['main_pct']:.1%} / {cap['per_account_cap']:.0%} cap  "
                  f"headroom=${cap['main_headroom_usd']:,.0f}")
            print(f"  Sub:   {cap['sub_pct']:.1%} / {cap['per_account_cap']:.0%} cap  "
                  f"headroom=${cap['sub_headroom_usd']:,.0f}")
            print(f"  Total headroom: ${cap['total_headroom_usd']:,.0f}")
            print(f"  {cap['note']}")
            k523 = cap['k523_3point']
            print(f"\n  K523 3-point (capacity relief, not direct alpha):")
            print(f"    Conservative: ${k523['conservative_usd_yr']:,.0f}/yr")
            print(f"    Central:      ${k523['mid_usd_yr']:,.0f}/yr")
            print(f"    Optimistic:   ${k523['optimistic_usd_yr']:,.0f}/yr")
            if cap["main_violations"]:
                print(f"  CAP VIOLATION: main account at {cap['main_pct']:.1%} ≥ {cap['per_account_cap']:.0%}")
            if cap["sub_violations"]:
                print(f"  CAP VIOLATION: sub account at {cap['sub_pct']:.1%} ≥ {cap['per_account_cap']:.0%}")
        return 0

    # Default: show snapshot
    snap = rm.get_snapshot()
    bybit_dual = rm.bybit_dual_account_capacity()
    print(f"\n=== K757 Risk Manager ===")
    print(f"  HL: {snap.hl_pct:.1%}  OKX: {snap.okx_pct:.1%}  "
          f"Bybit_main: {bybit_dual['main_pct']:.1%}  Bybit_sub: {bybit_dual['sub_pct']:.1%}")
    print(f"  Bybit total headroom: ${bybit_dual['total_headroom_usd']:,.0f}")
    print(f"  Violations: {snap.violations or 'none'}")
    print(f"  Use --help for options (--bybit-capacity for K757 dual-account view)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
