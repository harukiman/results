#!/usr/bin/env python3
"""
multi_venue_router.py — K745 Multi-Venue Router with OKX Registration
=======================================================================
Extends smart_router.py with:
  1. OKX venue registration (K498 scaffold integration)
  2. Sleeve-to-venue mapping (per strategy: HL% / OKX% / Bybit%)
  3. Venue allocation config driven by data/venue_allocation.json
  4. POST_ONLY enforcement on all venues (maker rebate capture)
  5. HL concentration tracking with 65%→50% relief target

Architecture:
  VenueRegistry      — register / deregister venues
  SleeveVenueMap     — per-strategy sleeve allocation {strategy: {venue: pct}}
  MultiVenueRouter   — extends SmartRouter scoring with venue allocation
  route_with_cap()   — primary routing function (cap-aware, OKX-registered)
  get_concentration() — real-time HL/OKX/Bybit concentration pcts

K339 security: REPO_ROOT from __file__, no /Users/ literals.
K745 context: OKX registration unblocks $4.5M Phase A queue (HL 65% cap exact).

Usage:
  from scripts.multi_venue_router import MultiVenueRouter, route_with_cap
  router = MultiVenueRouter()
  decision = router.route("INJ", "short", 100_000)
  print(decision["venue"])  # "OKX" | "Bybit" | "HL"

  # Check concentration status:
  conc = router.get_concentration()
  print(f"HL: {conc['HL_pct']:.1%}  OKX: {conc['OKX_pct']:.1%}")

Venue config loaded from data/venue_allocation.json.
Fallback to inline defaults if config file missing.
"""
from __future__ import annotations

import json
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# ── K339 canonical paths ──────────────────────────────────────────────────────
REPO_ROOT   = Path(__file__).resolve().parent.parent
DATA_DIR    = REPO_ROOT / "data"
LOGS_DIR    = REPO_ROOT / "logs"
SCRIPTS_DIR = REPO_ROOT / "scripts"

DATA_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)

JST = timezone(timedelta(hours=9))

# ── Config paths ──────────────────────────────────────────────────────────────
VENUE_ALLOC_PATH  = DATA_DIR / "venue_allocation.json"
ROUTER_CONFIG     = DATA_DIR / "smart_router_config.json"
ROUTER_DASHBOARD  = DATA_DIR / "multi_venue_router_dashboard.json"
DECISION_LOG      = DATA_DIR / "multi_venue_router_decisions.jsonl"


# ─────────────────────────────────────────────────────────────────────────────
# Venue Registry
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class VenueConfig:
    """Per-venue configuration for multi-venue router."""
    name:                str
    enabled:             bool    = True
    live_enabled:        bool    = False    # True only if API keys + LIVE gate set
    maker_rebate_bps:    float   = 0.0
    taker_fee_bps:       float   = 5.0
    min_depth_usd:       float   = 100_000.0
    max_pct_of_total:    float   = 0.50     # concentration cap (fraction of total AUM)
    max_position_pct_of_depth: float = 0.10
    post_only_default:   bool    = True
    api_base:            str     = ""
    user_tier:           str     = "default"
    status:              str     = "SCAFFOLD-READY"  # "LIVE" | "SCAFFOLD-READY" | "DISABLED"

    def to_dict(self) -> dict:
        return {
            "name": self.name, "enabled": self.enabled,
            "live_enabled": self.live_enabled,
            "maker_rebate_bps": self.maker_rebate_bps,
            "taker_fee_bps": self.taker_fee_bps,
            "max_pct_of_total": self.max_pct_of_total,
            "post_only_default": self.post_only_default,
            "status": self.status, "user_tier": self.user_tier,
        }


# K745 default venue registry (matches smart_router_config.json + wave_k498_smart_router_profit.py)
DEFAULT_VENUE_REGISTRY: Dict[str, VenueConfig] = {
    "HL": VenueConfig(
        name="HL", enabled=True, live_enabled=True,
        maker_rebate_bps=0.30, taker_fee_bps=4.50,
        min_depth_usd=100_000, max_pct_of_total=0.65,  # hard cap: EXACT 65.0% (K524)
        post_only_default=True, user_tier="GOLD",
        api_base="https://api.hyperliquid.xyz", status="LIVE",
    ),
    "Bybit": VenueConfig(
        name="Bybit", enabled=True, live_enabled=True,
        maker_rebate_bps=1.00, taker_fee_bps=3.20,
        min_depth_usd=100_000, max_pct_of_total=0.50,  # K485 cap
        post_only_default=True, user_tier="VIP5",
        api_base="https://api.bybit.com", status="LIVE",
    ),
    "OKX": VenueConfig(
        name="OKX", enabled=True, live_enabled=False,  # LIVE gate: OKX_LIVE_ENABLED=true
        maker_rebate_bps=0.50, taker_fee_bps=4.00,     # VIP1 conservative (post-VIP4: 2.0 bps)
        min_depth_usd=100_000, max_pct_of_total=0.40,  # K745 initial cap: 40%
        post_only_default=True, user_tier="VIP1",
        api_base="https://www.okx.com", status="SCAFFOLD-READY",
    ),
}


class VenueRegistry:
    """Manages set of registered trading venues."""

    def __init__(self, venues: Optional[Dict[str, VenueConfig]] = None):
        self._venues: Dict[str, VenueConfig] = dict(venues or DEFAULT_VENUE_REGISTRY)

    def register(self, venue: VenueConfig) -> None:
        """Register or update a venue configuration."""
        self._venues[venue.name] = venue
        _log(f"Registered venue: {venue.name} status={venue.status} enabled={venue.enabled}")

    def deregister(self, name: str) -> None:
        """Remove a venue from the registry."""
        if name in self._venues:
            del self._venues[name]
            _log(f"Deregistered venue: {name}")

    def enable(self, name: str) -> None:
        if name in self._venues:
            self._venues[name].enabled = True

    def disable(self, name: str) -> None:
        if name in self._venues:
            self._venues[name].enabled = False

    def activate_live(self, name: str) -> None:
        """Mark venue as live-enabled (after API key verification)."""
        if name in self._venues:
            self._venues[name].live_enabled = True
            self._venues[name].status = "LIVE"
            _log(f"Venue LIVE activated: {name}")

    def get(self, name: str) -> Optional[VenueConfig]:
        return self._venues.get(name)

    @property
    def enabled_venues(self) -> List[VenueConfig]:
        return [v for v in self._venues.values() if v.enabled]

    @property
    def live_venues(self) -> List[VenueConfig]:
        return [v for v in self._venues.values() if v.enabled and v.live_enabled]

    def to_dict(self) -> dict:
        return {k: v.to_dict() for k, v in self._venues.items()}

    @classmethod
    def from_config(cls) -> "VenueRegistry":
        """Load venue config from data/venue_allocation.json if present."""
        registry = cls()
        if VENUE_ALLOC_PATH.exists():
            try:
                with open(VENUE_ALLOC_PATH) as f:
                    alloc = json.load(f)
                # Update live_enabled from config (1-step activation)
                for name, cfg in alloc.get("venues", {}).items():
                    if name in registry._venues:
                        if cfg.get("live_enabled", False):
                            registry._venues[name].live_enabled = True
                            registry._venues[name].status = "LIVE"
                        if "max_pct_of_total" in cfg:
                            registry._venues[name].max_pct_of_total = cfg["max_pct_of_total"]
            except Exception as exc:
                _log(f"Config load error: {exc}", level="warning")
        return registry


# ─────────────────────────────────────────────────────────────────────────────
# Sleeve-to-venue mapping
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class SleeveVenueAllocation:
    """Per-strategy sleeve allocation across venues."""
    strategy_id: str
    allocations: Dict[str, float]   # {venue_name: fraction_of_sleeve}  sums to 1.0

    def dominant_venue(self) -> str:
        """Return venue with highest allocation."""
        return max(self.allocations, key=self.allocations.get)  # type: ignore

    def venue_size(self, total_size_usd: float, venue: str) -> float:
        """Return USD size for a given venue based on sleeve allocation."""
        return total_size_usd * self.allocations.get(venue, 0.0)


def load_sleeve_allocations() -> Dict[str, SleeveVenueAllocation]:
    """
    Load per-strategy sleeve allocations from data/venue_allocation.json.
    Returns dict {strategy_id: SleeveVenueAllocation}.

    K500 INJ-BTC example: HL 30% / OKX 70% post-K498 activation.
    """
    allocations: Dict[str, SleeveVenueAllocation] = {}

    if not VENUE_ALLOC_PATH.exists():
        return _default_sleeve_allocations()

    try:
        with open(VENUE_ALLOC_PATH) as f:
            config = json.load(f)
        for strat_id, strat_cfg in config.get("sleeves", {}).items():
            if not isinstance(strat_cfg, dict):
                continue   # skip _comment or non-dict entries
            alloc_dict = strat_cfg.get("venue_allocation", {})
            if not isinstance(alloc_dict, dict):
                continue
            # Normalize to sum to 1.0
            total = sum(alloc_dict.values())
            if total > 0:
                alloc_dict = {k: v / total for k, v in alloc_dict.items()}
            allocations[strat_id] = SleeveVenueAllocation(
                strategy_id=strat_id,
                allocations=alloc_dict,
            )
    except Exception as exc:
        _log(f"Sleeve allocation load error: {exc}", level="warning")
        return _default_sleeve_allocations()

    return allocations


def _default_sleeve_allocations() -> Dict[str, SleeveVenueAllocation]:
    """Default sleeve allocations (before K498 OKX activation)."""
    return {
        # Current live sleeves (Bybit-primary where HL cap exceeded)
        "K280": SleeveVenueAllocation("K280", {"HL": 1.0}),
        "K297p": SleeveVenueAllocation("K297p", {"HL": 1.0}),
        "K500_INJ_BTC": SleeveVenueAllocation("K500_INJ_BTC", {"Bybit": 1.0}),
        "K507_TIA_BTC": SleeveVenueAllocation("K507_TIA_BTC", {"Bybit": 1.0}),
        "K512_APT_BTC": SleeveVenueAllocation("K512_APT_BTC", {"Bybit": 1.0}),
        "K679_APT_SOL": SleeveVenueAllocation("K679_APT_SOL", {"Bybit": 1.0}),
        "K682_ATOM_SOL": SleeveVenueAllocation("K682_ATOM_SOL", {"Bybit": 1.0}),
        # After K498 OKX activation: INJ-BTC shifts HL 30% / OKX 70%
        # (Set in venue_allocation.json when user activates OKX)
    }


# ─────────────────────────────────────────────────────────────────────────────
# Concentration tracker
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ConcentrationSnapshot:
    """Current venue concentration state."""
    total_aum_usd:    float
    venue_notional:   Dict[str, float]   # {venue: notional_usd}
    venue_pct:        Dict[str, float]   # {venue: pct_of_total_aum}
    caps:             Dict[str, float]   # {venue: cap_pct}
    violations:       List[str]          # venues exceeding cap
    timestamp_utc:    str

    @property
    def hl_pct(self) -> float:
        return self.venue_pct.get("HL", 0.0)

    @property
    def okx_pct(self) -> float:
        return self.venue_pct.get("OKX", 0.0)

    @property
    def bybit_pct(self) -> float:
        return self.venue_pct.get("Bybit", 0.0)

    @property
    def hl_headroom(self) -> float:
        """Remaining HL headroom before cap (fractional)."""
        return self.caps.get("HL", 0.65) - self.hl_pct

    def to_dict(self) -> dict:
        return {
            "total_aum_usd": self.total_aum_usd,
            "venue_notional": self.venue_notional,
            "venue_pct":      {k: round(v, 4) for k, v in self.venue_pct.items()},
            "caps":           self.caps,
            "violations":     self.violations,
            "hl_headroom_pct": round(self.hl_headroom, 4),
            "timestamp_utc":  self.timestamp_utc,
        }


# ─────────────────────────────────────────────────────────────────────────────
# Multi-Venue Router
# ─────────────────────────────────────────────────────────────────────────────

class MultiVenueRouter:
    """
    K745 multi-venue router: extends smart_router.py with OKX registration,
    sleeve-to-venue mapping, and HL concentration cap management.

    Routing priority (K745):
      1. Check concentration caps (HL 65%, OKX 40%, Bybit 50%)
      2. If OKX live: score HL/Bybit/OKX → select best net_per_8h
      3. If OKX not live: route per sleeve_allocation (HL or Bybit)
      4. POST_ONLY enforced on all venues

    Activation path:
      OKX_LIVE_ENABLED=true in .env.local → OKX routes go live
      → HL concentration drops from 65% toward 50% over ~1-2 months
      → Unlocks $4.5M Phase A queue (new alt-alt sleeves)
    """

    def __init__(
        self,
        registry:         Optional[VenueRegistry] = None,
        current_notional: Optional[Dict[str, float]] = None,
        total_aum:        float = 10_000_000.0,
    ):
        self.registry         = registry or VenueRegistry.from_config()
        self.current_notional = current_notional or {"HL": 0.0, "Bybit": 0.0, "OKX": 0.0}
        self.total_aum        = total_aum
        self.sleeve_allocs    = load_sleeve_allocations()
        self._decision_buf:   List[dict] = []

    def get_concentration(self) -> ConcentrationSnapshot:
        """Compute current venue concentration snapshot."""
        total = self.total_aum
        venue_pct = {}
        for venue, notional in self.current_notional.items():
            venue_pct[venue] = notional / total if total > 0 else 0.0

        caps: Dict[str, float] = {}
        violations: List[str] = []
        for v in self.registry.enabled_venues:
            cap = v.max_pct_of_total
            caps[v.name] = cap
            pct = venue_pct.get(v.name, 0.0)
            if pct >= cap:
                violations.append(v.name)

        return ConcentrationSnapshot(
            total_aum_usd=total,
            venue_notional=dict(self.current_notional),
            venue_pct=venue_pct,
            caps=caps,
            violations=violations,
            timestamp_utc=datetime.now(timezone.utc).isoformat(),
        )

    def _is_venue_at_cap(self, venue_name: str, additional_usd: float = 0.0) -> bool:
        """Check if adding additional_usd to venue would breach its cap."""
        vcfg = self.registry.get(venue_name)
        if not vcfg:
            return True   # unknown venue → block
        current = self.current_notional.get(venue_name, 0.0)
        projected_pct = (current + additional_usd) / self.total_aum if self.total_aum > 0 else 1.0
        return projected_pct >= vcfg.max_pct_of_total

    def score_venue_net(
        self,
        venue_name:       str,
        fr:               float,      # funding rate (fractional per 8h)
        side:             str,        # "short" | "long"
        position_usd:     float,
        depth_usd:        float,
    ) -> float:
        """
        Compute net score for routing to venue.
        score = fr_capture + maker_rebate_bps/10000 - slippage_estimate

        Positive = profitable. Higher = preferred.
        Matches smart_router.py scoring logic for compatibility.
        """
        vcfg = self.registry.get(venue_name)
        if not vcfg or not vcfg.enabled:
            return -999.0

        # FR capture: short receives positive FR if FR > 0
        fr_capture = fr if side == "short" else -fr

        # Maker rebate (always positive — we receive it)
        maker_rebate = vcfg.maker_rebate_bps / 10_000

        # Slippage estimate (linear impact)
        slippage = 0.0
        if depth_usd > 0:
            ratio = position_usd / depth_usd
            slippage_bps = ratio * 100 * 0.5   # 0.5 bps per 1% depth (conservative)
            slippage = slippage_bps / 10_000

        return fr_capture + maker_rebate - slippage

    def route(
        self,
        symbol:        str,
        side:          str,
        position_usd:  float,
        strategy_id:   Optional[str] = None,
        venue_state:   Optional[Dict[str, Dict[str, dict]]] = None,
    ) -> dict:
        """
        Route a trade to the best venue.

        Args:
          symbol:       Base symbol (e.g. "BTC", "INJ", "SOL")
          side:         "short" | "long"
          position_usd: Position size in USD
          strategy_id:  If provided, use sleeve allocation from venue_allocation.json
          venue_state:  {venue: {symbol: {fr, depth_usd, mark_px}}} — from smart_router or live fetch

        Returns dict:
          venue:         Selected venue name
          score:         Best venue score
          scores:        {venue: score} for all venues
          post_only:     True (always enforced)
          capped_venues: List of venues at concentration cap
          mode:          "live" | "paper"
          reason:        Human-readable routing reason
          timestamp_utc: ISO timestamp
        """
        ts = datetime.now(timezone.utc).isoformat()
        capped_venues = []
        scores: Dict[str, float] = {}
        mode = "paper"

        # Get scores for all enabled venues
        for vcfg in self.registry.enabled_venues:
            vname = vcfg.name

            # Check concentration cap
            if self._is_venue_at_cap(vname, position_usd):
                scores[vname] = -666.0
                capped_venues.append(vname)
                continue

            # Get venue state (FR + depth)
            fr        = 0.0
            depth_usd = 2_000_000.0   # fallback depth
            if venue_state and vname in venue_state:
                sym_state = venue_state[vname].get(symbol, {})
                fr        = sym_state.get("fr", 0.0)
                depth_usd = sym_state.get("depth_usd", 2_000_000.0)

            scores[vname] = self.score_venue_net(vname, fr, side, position_usd, depth_usd)

            if vcfg.live_enabled:
                mode = "live"

        # Strategy sleeve override: if strategy_id maps to a fixed venue allocation, use that
        if strategy_id and strategy_id in self.sleeve_allocs:
            sleeve = self.sleeve_allocs[strategy_id]
            dominant = sleeve.dominant_venue()
            if dominant in scores and scores[dominant] > -100.0:
                selected_venue = dominant
                reason = f"sleeve_allocation: {strategy_id} → {dominant} ({sleeve.allocations[dominant]:.0%})"
                _log(f"route {symbol} {side}: sleeve override → {selected_venue} ({reason})")
                return self._make_decision(
                    venue=selected_venue, symbol=symbol, side=side,
                    position_usd=position_usd, scores=scores,
                    capped_venues=capped_venues, mode=mode, reason=reason,
                    post_only=self.registry.get(selected_venue).post_only_default,
                    ts=ts,
                )

        # Best score selection (BBO mode — K498 Phase 1A)
        usable = {v: s for v, s in scores.items() if s > -100.0}
        if not usable:
            # All capped — return HL as fallback (log warning)
            _log(f"ALL_VENUES_CAPPED: {symbol} {side} ${position_usd:,.0f}", level="warning")
            return self._make_decision(
                venue="HL", symbol=symbol, side=side, position_usd=position_usd,
                scores=scores, capped_venues=capped_venues, mode="paper",
                reason="ALL_VENUES_CAPPED — fallback HL, manual review required",
                post_only=True, ts=ts,
            )

        best_venue = max(usable, key=usable.get)  # type: ignore
        reason = (
            f"BBO_SELECT: best net_per_8h={usable[best_venue]:.8f} at {best_venue} | "
            f"scores={{{', '.join(f'{v}:{s:.6f}' for v, s in sorted(scores.items()))}}}"
        )

        vcfg_best = self.registry.get(best_venue)
        post_only = vcfg_best.post_only_default if vcfg_best else True

        return self._make_decision(
            venue=best_venue, symbol=symbol, side=side,
            position_usd=position_usd, scores=scores,
            capped_venues=capped_venues, mode=mode, reason=reason,
            post_only=post_only, ts=ts,
        )

    def route_paired(
        self,
        symbol_long:  str,
        symbol_short: str,
        position_usd: float,
        strategy_id:  Optional[str] = None,
        prefer_same_venue: bool = True,
    ) -> Tuple[dict, dict]:
        """
        Route a paired trade (long leg + short leg).
        If prefer_same_venue=True, tries to route both legs to same venue.
        Returns (long_decision, short_decision).
        """
        long_dec  = self.route(symbol_long,  "long",  position_usd, strategy_id)
        short_dec = self.route(symbol_short, "short", position_usd, strategy_id)

        if prefer_same_venue and long_dec["venue"] != short_dec["venue"]:
            # Try to align: if both venues are valid, prefer the one that's live
            long_v  = long_dec["venue"]
            short_v = short_dec["venue"]
            # Check if long venue can handle short (same OI constraints)
            long_conc_ok  = not self._is_venue_at_cap(long_v,  position_usd)
            short_conc_ok = not self._is_venue_at_cap(short_v, position_usd)
            # Prefer the live venue
            if long_conc_ok and self.registry.get(long_v) and self.registry.get(long_v).live_enabled:
                # Force short to same venue as long
                short_dec = dict(short_dec)
                short_dec["venue"]  = long_v
                short_dec["reason"] = f"paired_trade_alignment: aligned to long venue {long_v}"
            elif short_conc_ok and self.registry.get(short_v) and self.registry.get(short_v).live_enabled:
                long_dec = dict(long_dec)
                long_dec["venue"]  = short_v
                long_dec["reason"] = f"paired_trade_alignment: aligned to short venue {short_v}"

        return long_dec, short_dec

    def _make_decision(
        self,
        venue: str, symbol: str, side: str,
        position_usd: float, scores: Dict[str, float],
        capped_venues: List[str], mode: str, reason: str,
        post_only: bool, ts: str,
    ) -> dict:
        decision = {
            "venue":         venue,
            "symbol":        symbol,
            "side":          side,
            "position_usd":  position_usd,
            "score":         scores.get(venue, -9999.0),
            "scores":        {k: round(v, 8) for k, v in scores.items()},
            "capped_venues": capped_venues,
            "post_only":     post_only,
            "mode":          mode,
            "reason":        reason,
            "timestamp_utc": ts,
        }
        self._log_decision(decision)
        return decision

    def _log_decision(self, decision: dict) -> None:
        """Append routing decision to multi_venue_router_decisions.jsonl."""
        entry = {
            "ts_jst":       datetime.now(JST).strftime("%Y-%m-%d %H:%M JST"),
            "venue":        decision["venue"],
            "symbol":       decision["symbol"],
            "side":         decision["side"],
            "position_usd": decision["position_usd"],
            "score":        decision["score"],
            "mode":         decision["mode"],
            "capped":       decision["capped_venues"],
            "reason":       decision["reason"],
        }
        try:
            with open(DECISION_LOG, "a") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception as exc:
            _log(f"Decision log error: {exc}", level="warning")
        self._decision_buf.append(decision)
        if len(self._decision_buf) > 200:
            self._decision_buf = self._decision_buf[-100:]

    def write_dashboard(self, venue_state: Optional[Dict] = None) -> Path:
        """Write multi_venue_router_dashboard.json."""
        conc = self.get_concentration()
        now_jst = datetime.now(JST)
        live_venues = [v.name for v in self.registry.live_venues]
        scaffold_venues = [v.name for v in self.registry.enabled_venues if not v.live_enabled]

        payload = {
            "_wave":         "K745",
            "_source":       "multi_venue_router.py",
            "last_update_jst": now_jst.strftime("%Y-%m-%d %H:%M JST"),
            "total_aum_usd": self.total_aum,
            "concentration": conc.to_dict(),
            "live_venues":   live_venues,
            "scaffold_venues": scaffold_venues,
            "venue_registry": self.registry.to_dict(),
            "recent_decisions_count": len(self._decision_buf),
            "okx_activation_status": {
                "live": self.registry.get("OKX") and self.registry.get("OKX").live_enabled,  # type: ignore
                "1_step": "set OKX_LIVE_ENABLED=true in .env.local",
                "hl_target_after_okx": "50% (from 65%)",
                "unlocks_usd": 4_500_000,
                "note": "K745 K498 OKX scaffold — paste API key + flip env var",
            },
        }

        tmp = ROUTER_DASHBOARD.with_suffix(".tmp")
        with open(tmp, "w") as f:
            json.dump(payload, f, indent=2)
        tmp.replace(ROUTER_DASHBOARD)
        return ROUTER_DASHBOARD


# ── Public convenience function ────────────────────────────────────────────────

def route_with_cap(
    symbol:       str,
    side:         str,
    position_usd: float,
    strategy_id:  Optional[str] = None,
    total_aum:    float = 10_000_000.0,
    hl_notional:  float = 6_500_000.0,   # 65% of $10M = HL at exact cap
    bybit_notional: float = 2_000_000.0,
    okx_notional:   float = 0.0,
    venue_state:    Optional[Dict] = None,
) -> dict:
    """
    Convenience wrapper: route a single trade with current concentration state.

    Args:
      symbol, side, position_usd: trade parameters
      strategy_id: if set, uses sleeve allocation from venue_allocation.json
      total_aum, hl_notional, bybit_notional, okx_notional: current allocation state
      venue_state: {venue: {symbol: {fr, depth_usd}}} — from smart_router or cache

    Returns routing decision dict.
    """
    router = MultiVenueRouter(
        current_notional={"HL": hl_notional, "Bybit": bybit_notional, "OKX": okx_notional},
        total_aum=total_aum,
    )
    return router.route(symbol, side, position_usd, strategy_id, venue_state)


def _log(msg: str, level: str = "info") -> None:
    ts = datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S JST")
    prefix = {"info": "[INFO]", "warning": "[WARN]", "error": "[ERR]"}.get(level, "[INFO]")
    print(f"  {ts} {prefix} [multi_venue_router] {msg}", file=sys.stderr)


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> int:
    import argparse
    p = argparse.ArgumentParser(
        description="K745 Multi-Venue Router — OKX registration + HL cap relief",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Route a trade (paper mode, no keys needed):
  python3 scripts/multi_venue_router.py --symbol BTC --side short --size 100000

  # Paired trade routing:
  python3 scripts/multi_venue_router.py --paired INJ SOL --size 100000

  # Check concentration state:
  python3 scripts/multi_venue_router.py --concentration

  # Show venue registry:
  python3 scripts/multi_venue_router.py --registry

  # Write dashboard:
  python3 scripts/multi_venue_router.py --dashboard

K745: OKX_LIVE_ENABLED=true in .env.local activates OKX live routing.
HL cap: 65.0% hard limit. OKX initial: 40%. Bybit: 50%.
        """,
    )
    p.add_argument("--symbol",        help="Base symbol to route (e.g. BTC, INJ)")
    p.add_argument("--side",          choices=["short", "long"], default="short")
    p.add_argument("--size",          type=float, default=100_000.0)
    p.add_argument("--strategy-id",   default=None)
    p.add_argument("--paired",        nargs=2, metavar=("LONG", "SHORT"),
                   help="Route paired trade: LONG SHORT")
    p.add_argument("--concentration", action="store_true")
    p.add_argument("--registry",      action="store_true")
    p.add_argument("--dashboard",     action="store_true")
    p.add_argument("--total-aum",     type=float, default=10_000_000.0)
    p.add_argument("--hl-notional",   type=float, default=6_500_000.0)
    p.add_argument("--bybit-notional", type=float, default=2_000_000.0)
    p.add_argument("--okx-notional",  type=float, default=0.0)
    p.add_argument("--json",          action="store_true")
    args = p.parse_args()

    router = MultiVenueRouter(
        current_notional={
            "HL": args.hl_notional,
            "Bybit": args.bybit_notional,
            "OKX": args.okx_notional,
        },
        total_aum=args.total_aum,
    )

    if args.concentration:
        conc = router.get_concentration()
        if args.json:
            print(json.dumps(conc.to_dict(), indent=2))
        else:
            print(f"\n=== Venue Concentration (K745) ===")
            for venue, pct in conc.venue_pct.items():
                cap = conc.caps.get(venue, 1.0)
                status = "CAP HIT" if venue in conc.violations else "OK"
                print(f"  {venue:<8}  {pct:.1%} / {cap:.0%}  [{status}]")
            print(f"\n  HL headroom: {conc.hl_headroom:.1%}")
            print(f"  Violations:  {conc.violations or 'none'}")
        return 0

    if args.registry:
        reg = router.registry.to_dict()
        if args.json:
            print(json.dumps(reg, indent=2))
        else:
            print(f"\n=== Venue Registry (K745) ===")
            for name, vcfg in reg.items():
                print(f"  {name:<8}  live={str(vcfg['live_enabled']):<5}  "
                      f"rebate={vcfg['maker_rebate_bps']:.1f}bps  "
                      f"cap={vcfg['max_pct_of_total']:.0%}  status={vcfg['status']}")
        return 0

    if args.dashboard:
        path = router.write_dashboard()
        print(f"  Dashboard: {path}")
        return 0

    if args.paired:
        sym_long, sym_short = args.paired
        long_dec, short_dec = router.route_paired(sym_long, sym_short, args.size, args.strategy_id)
        if args.json:
            print(json.dumps({"long": long_dec, "short": short_dec}, indent=2))
        else:
            print(f"  LONG  {sym_long:<6} → {long_dec['venue']}  score={long_dec['score']:.6f}  mode={long_dec['mode']}")
            print(f"  SHORT {sym_short:<6} → {short_dec['venue']}  score={short_dec['score']:.6f}  mode={short_dec['mode']}")
        return 0

    if args.symbol:
        decision = router.route(args.symbol, args.side, args.size, args.strategy_id)
        if args.json:
            print(json.dumps(decision, indent=2))
        else:
            print(f"\n=== Route Decision ===")
            print(f"  Symbol:   {decision['symbol']}")
            print(f"  Venue:    {decision['venue']}")
            print(f"  Score:    {decision['score']:.8f}")
            print(f"  Mode:     {decision['mode']}")
            print(f"  PostOnly: {decision['post_only']}")
            print(f"  Capped:   {decision['capped_venues'] or 'none'}")
            print(f"  Reason:   {decision['reason'][:80]}")
        return 0

    # Default: show status
    conc = router.get_concentration()
    print(f"\n=== K745 Multi-Venue Router ===")
    print(f"  Total AUM: ${args.total_aum:,.0f}")
    for venue, pct in conc.venue_pct.items():
        print(f"  {venue:<8}  ${conc.venue_notional.get(venue, 0):>12,.0f}  ({pct:.1%})")
    print(f"\n  OKX live: {router.registry.get('OKX') and router.registry.get('OKX').live_enabled}")  # type: ignore
    print(f"  Use --help for options")
    return 0


if __name__ == "__main__":
    sys.exit(main())
