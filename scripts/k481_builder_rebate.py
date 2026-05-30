"""
k481_builder_rebate.py — K481 HL Builder Rebate Module (K755 scaffold)
=======================================================================
Production-ready module for injecting HL builder code into all order actions.
Used by post_only_order_manager.py, k280_live_fetch.py, k449_eth_btc_run.py,
and any future HL-facing order submission code.

Key design principles:
  - Zero-risk additive: if HL_BUILDER_CODE env var is unset, all functions are no-ops
  - Paper-mode safe: builder field NOT injected during dry_run (does not affect paper P&L)
  - Venue-specific: only injects for HL (Bybit/OKX orders are never touched)
  - Public-key only: HL_BUILDER_CODE is a wallet address, not a private key
  - f=0 always: zero additional fee charged to the trader

Builder code mechanism (HL docs, verified 2026-05-27):
  order_action["builder"] = {"b": "<BUILDER_WALLET_ADDRESS>", "f": 0}
  f = fee in tenths of basis points (0 = no extra cost to user)
  Builder earns from HL referral pool on every order carrying this field.

K523 3-point annual projection @ $10M AUM:
  Conservative (10% referral rate): ~$99K/yr  ($272/day)
  Central      (25% referral rate): ~$248K/yr  ($679/day)
  Optimistic   (50% referral rate): ~$496K/yr  ($1,358/day)

Model: HL fraction 57.5%, daily turnover 1.5x, POST_ONLY fill rate 70%, taker 4.5bps.
Memory cites $94K-$472K/yr — K481 refined: conservative $99K, optimistic $496K.

Activation:
  1. approveBuilderFee on-chain (main wallet, not agent/API key)
  2. export HL_BUILDER_CODE='0x<YOUR_MAIN_WALLET_ADDRESS>'
  3. Restart daemons (launchctl unload/load)
  Reversibility: unset HL_BUILDER_CODE → silently skips (no-op, no breakage)

K339 security: REPO_ROOT from __file__, no /Users/ literals.
LIVE auto-change: PROHIBITED (paper-mode default).

Usage:
  from scripts.k481_builder_rebate import inject_builder_field, get_builder_stats
  inject_builder_field(order_action, venue="HL", dry_run=False)
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, Optional

# ── K339 canonical paths ──────────────────────────────────────────────────────
REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR  = REPO_ROOT / "data"
CACHE_DIR = REPO_ROOT / "cache"
DATA_DIR.mkdir(exist_ok=True)

JST = timezone(timedelta(hours=9))

# ── Config ────────────────────────────────────────────────────────────────────
BUILDER_CODES_JSON = DATA_DIR / "builder_codes.json"

# HL builder fee in tenths of basis points (0 = zero extra cost to trader)
HL_BUILDER_FEE_TENTHS_BP = 0

# ── K523 profit model constants ───────────────────────────────────────────────
HL_TAKER_RATE_BPS   = 4.5    # Standard HL taker rate
HL_FRACTION         = 0.575  # v6.22 architecture: 57.5% of AUM on HL
DAILY_TURNOVER_X    = 1.5    # 1.5x AUM traded per day on HL
POST_ONLY_FILL_RATE = 0.70   # 70% maker fill rate (K439 target)
TRADING_DAYS        = 365

REBATE_SCENARIOS = {
    "conservative": 0.10,   # 10% of taker notional (floor estimate)
    "central":      0.25,   # 25% of taker notional (K481 mid estimate)
    "optimistic":   0.50,   # 50% of taker notional (K370 upper bound)
}


# ─────────────────────────────────────────────────────────────────────────────
# Core injection function
# ─────────────────────────────────────────────────────────────────────────────

def inject_builder_field(
    order_action: Dict,
    venue: str,
    dry_run: bool = False,
    strategy: Optional[str] = None,
) -> bool:
    """
    Inject the HL builder code field into an order action dict in-place.

    This is the single canonical injection point for all HL orders.
    Call this function just before submitting any live HL order action.

    Args:
        order_action: dict being built for HL clearinghouse API call.
                      Modified in-place if injection occurs.
        venue:        exchange venue string. Only "HL" receives injection.
        dry_run:      if True, skip injection (paper-mode safe).
        strategy:     optional strategy name for logging (e.g., "K280", "K449").

    Returns:
        True if builder field was injected, False otherwise (no-op cases).

    No-op conditions (returns False, order_action unchanged):
        - venue != "HL"
        - dry_run == True
        - HL_BUILDER_CODE env var not set or empty
        - HL_BUILDER_CODE value is not a valid 0x address (length guard)

    Example:
        order_action = {
            "type": "order",
            "orders": [...],
            "grouping": "na",
        }
        injected = inject_builder_field(order_action, venue="HL", dry_run=False)
        # If injected: order_action["builder"] = {"b": "0x...", "f": 0}
    """
    if venue != "HL":
        return False
    if dry_run:
        return False

    builder_code = _get_builder_code_for_venue("HL")
    if not builder_code:
        return False

    order_action["builder"] = {"b": builder_code, "f": HL_BUILDER_FEE_TENTHS_BP}

    strat_tag = f"[{strategy}] " if strategy else ""
    print(f"  [K481] {strat_tag}Builder code injected for HL order "
          f"(f={HL_BUILDER_FEE_TENTHS_BP}, code=...{builder_code[-6:]})")
    return True


def _get_builder_code_for_venue(venue: str) -> str:
    """
    Get the builder code for a given venue from env var or config file.

    Priority:
      1. HL_BUILDER_CODE env var (primary, recommended)
      2. data/builder_codes.json → venue-specific override

    Returns empty string if not set (triggers no-op in inject_builder_field).
    """
    if venue != "HL":
        return ""

    # 1. Environment variable (primary)
    code = os.environ.get("HL_BUILDER_CODE", "").strip()
    if code:
        # Basic sanity check: Ethereum address format (0x + 40 hex chars)
        if _is_valid_eth_address(code):
            return code
        else:
            print(f"  [K481] WARNING: HL_BUILDER_CODE format invalid "
                  f"(expected 0x + 40 hex chars). Got: {code[:12]}... — skipping injection.")
            return ""

    # 2. Config file fallback
    if BUILDER_CODES_JSON.exists():
        try:
            with open(BUILDER_CODES_JSON) as f:
                cfg = json.load(f)
            override = cfg.get("venue_overrides", {}).get(venue, {}).get("builder_code", "")
            if override and _is_valid_eth_address(override):
                return override
        except Exception as e:
            print(f"  [K481] WARNING: Could not read builder_codes.json: {e}")

    return ""


def _is_valid_eth_address(addr: str) -> bool:
    """Basic Ethereum address format check: 0x + 40 hex characters."""
    if not addr.startswith("0x"):
        return False
    hex_part = addr[2:]
    if len(hex_part) != 40:
        return False
    try:
        int(hex_part, 16)
        return True
    except ValueError:
        return False


# ─────────────────────────────────────────────────────────────────────────────
# Builder code status and stats
# ─────────────────────────────────────────────────────────────────────────────

def is_builder_active(venue: str = "HL") -> bool:
    """Return True if builder code is configured and ready for the given venue."""
    return bool(_get_builder_code_for_venue(venue))


def get_builder_status() -> Dict:
    """
    Return builder code activation status for all supported venues.
    Used by monitoring scripts and dashboard generators.

    Returns:
        {
            "hl_active": bool,
            "hl_code_masked": str | None,   # last 6 chars only (security)
            "source": "env" | "config" | "none",
            "fee_tenths_bp": int,
            "zero_risk_assertion": str,
            "checked_utc": str,
        }
    """
    code = os.environ.get("HL_BUILDER_CODE", "").strip()
    source = "none"
    masked = None

    if code and _is_valid_eth_address(code):
        source = "env"
        masked = f"...{code[-6:]}"
    elif BUILDER_CODES_JSON.exists():
        try:
            with open(BUILDER_CODES_JSON) as f:
                cfg = json.load(f)
            override = cfg.get("venue_overrides", {}).get("HL", {}).get("builder_code", "")
            if override and _is_valid_eth_address(override):
                source = "config"
                masked = f"...{override[-6:]}"
        except Exception:
            pass

    return {
        "hl_active":           source != "none",
        "hl_code_masked":      masked,
        "source":              source,
        "fee_tenths_bp":       HL_BUILDER_FEE_TENTHS_BP,
        "zero_risk_assertion": (
            "ZERO: f=0 no extra cost, ZERO HL concentration delta, "
            "ZERO signal change, ZERO counterparty risk"
        ),
        "checked_utc":         datetime.now(timezone.utc).isoformat(),
    }


# ─────────────────────────────────────────────────────────────────────────────
# K523 3-point profit projection
# ─────────────────────────────────────────────────────────────────────────────

def compute_annual_rebate(
    aum_usd: float,
    scenario: str = "central",
    hl_fraction: float = HL_FRACTION,
    daily_turnover_x: float = DAILY_TURNOVER_X,
    post_only_fill_rate: float = POST_ONLY_FILL_RATE,
    taker_rate_bps: float = HL_TAKER_RATE_BPS,
) -> float:
    """
    Compute annual builder rebate estimate in USDC.

    Model:
        HL_daily_vol = AUM × hl_fraction × daily_turnover_x
        maker_vol    = HL_daily_vol × post_only_fill_rate
        daily_rebate = maker_vol × (taker_rate_bps / 10000) × rebate_fraction
        annual       = daily_rebate × TRADING_DAYS

    Args:
        aum_usd:            total AUM in USD
        scenario:           "conservative" | "central" | "optimistic"
        hl_fraction:        fraction of AUM on HL (default 57.5%)
        daily_turnover_x:   daily HL turnover vs HL AUM (default 1.5x)
        post_only_fill_rate: maker fill rate (default 70%)
        taker_rate_bps:     HL taker fee in bps (default 4.5)

    Returns:
        Annual USDC rebate estimate
    """
    rebate_frac = REBATE_SCENARIOS.get(scenario, REBATE_SCENARIOS["central"])
    hl_daily_vol = aum_usd * hl_fraction * daily_turnover_x
    maker_vol    = hl_daily_vol * post_only_fill_rate
    daily_rebate = maker_vol * (taker_rate_bps / 10_000.0) * rebate_frac
    return daily_rebate * TRADING_DAYS


def k523_projection(aum_usd: float = 10_000_000.0) -> Dict:
    """
    K523 mandatory 3-point projection for K481 builder rebate.

    Per memory K523: all profit projections require conservative/mid/optimistic.
    Single-point estimates are PROHIBITED.

    Args:
        aum_usd: AUM in USD (default $10M)

    Returns:
        {
            "aum_usd": float,
            "conservative_usdc_yr": float,
            "central_usdc_yr": float,
            "optimistic_usdc_yr": float,
            "conservative_daily": float,
            "central_daily": float,
            "optimistic_daily": float,
            "memory_range_note": str,
            "k523_compliant": True,
        }
    """
    con = compute_annual_rebate(aum_usd, "conservative")
    ctr = compute_annual_rebate(aum_usd, "central")
    opt = compute_annual_rebate(aum_usd, "optimistic")

    return {
        "aum_usd":               aum_usd,
        "conservative_usdc_yr":  round(con, 0),
        "central_usdc_yr":       round(ctr, 0),
        "optimistic_usdc_yr":    round(opt, 0),
        "conservative_daily":    round(con / TRADING_DAYS, 1),
        "central_daily":         round(ctr / TRADING_DAYS, 1),
        "optimistic_daily":      round(opt / TRADING_DAYS, 1),
        "memory_range_note":     (
            f"Memory cites $94K-$472K/yr @$10M (K370). "
            f"K481 refined: conservative ${con/1e3:.0f}K, "
            f"central ${ctr/1e3:.0f}K, "
            f"optimistic ${opt/1e3:.0f}K. "
            f"K523: central is realistic estimate, optimistic is upper bound."
        ),
        "k523_compliant":        True,
    }


# ─────────────────────────────────────────────────────────────────────────────
# HL API: referral state check
# ─────────────────────────────────────────────────────────────────────────────

def check_referral_state(wallet_address: str) -> Dict:
    """
    Query HL API for referral/builder state for a wallet address.
    Used for weekly approval verification and daily rebate monitoring.

    HL API endpoint: POST https://api.hyperliquid.xyz/info
    Payload: {"type": "referralState", "user": "<wallet_address>"}

    Args:
        wallet_address: wallet address to check (public, not private key)

    Returns:
        API response dict, or {"error": str} if request fails.

    Note: This function makes a live HTTP request. Do NOT call during
    backtest or paper-trade loops. Use for monitoring scripts only.
    """
    try:
        import urllib.request
        payload = json.dumps({"type": "referralState", "user": wallet_address}).encode()
        req = urllib.request.Request(
            "https://api.hyperliquid.xyz/info",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        return {"error": str(e), "wallet": wallet_address}


def check_builder_fees(wallet_address: str) -> Dict:
    """
    Query HL API for active builder fee approvals for a wallet.

    HL API payload: {"type": "builderFees", "user": "<wallet_address>"}

    Args:
        wallet_address: wallet address to check

    Returns:
        API response dict, or {"error": str} if request fails.
    """
    try:
        import urllib.request
        payload = json.dumps({"type": "builderFees", "user": wallet_address}).encode()
        req = urllib.request.Request(
            "https://api.hyperliquid.xyz/info",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        return {"error": str(e), "wallet": wallet_address}


# ─────────────────────────────────────────────────────────────────────────────
# Dashboard / monitoring output
# ─────────────────────────────────────────────────────────────────────────────

def get_builder_stats(aum_usd: float = 10_000_000.0) -> Dict:
    """
    Return complete builder rebate stats for dashboard integration.

    Args:
        aum_usd: current AUM in USD

    Returns:
        Full status dict including activation status, K523 projection,
        risk assertion, and monitoring thresholds.
    """
    status  = get_builder_status()
    proj    = k523_projection(aum_usd)

    return {
        "module":              "k481_builder_rebate",
        "wave":                "K755",
        "generated_utc":       datetime.now(timezone.utc).isoformat(),
        "generated_jst":       datetime.now(JST).strftime("%Y-%m-%d %H:%M JST"),

        "activation_status":   status,
        "k523_projection":     proj,

        "model_params": {
            "hl_fraction":          HL_FRACTION,
            "daily_turnover_x":     DAILY_TURNOVER_X,
            "post_only_fill_rate":  POST_ONLY_FILL_RATE,
            "hl_taker_rate_bps":    HL_TAKER_RATE_BPS,
            "builder_fee_tbp":      HL_BUILDER_FEE_TENTHS_BP,
        },

        "monitoring_thresholds": {
            "alert_pct_of_expected":  0.50,
            "alert_consecutive_days": 3,
            "expected_daily_con":     proj["conservative_daily"],
            "expected_daily_ctr":     proj["central_daily"],
            "expected_daily_opt":     proj["optimistic_daily"],
            "alert_floor_daily":      round(proj["conservative_daily"] * 0.50, 1),
        },

        "zero_risk_assertion": {
            "hl_concentration_delta": 0.0,
            "signal_change":          "NONE",
            "counterparty_risk":      "NONE (HL referral pool, internal accounting)",
            "execution_risk":         "NONE (f=0, no extra cost to trader)",
            "worst_case":             "Program ends → return to current cost baseline, zero degradation",
            "k266_gate":              "ACCEPT-FREE (cost optimization, not alpha signal)",
        },

        "activation_checklist": [
            "[ ] Step 1: approveBuilderFee on-chain (HL main wallet, f=0)",
            "[ ] Step 2: export HL_BUILDER_CODE='0x<YOUR_MAIN_WALLET_ADDRESS>' in ~/.zshrc",
            "[ ] Step 3: Add HL_BUILDER_CODE to launchd plist EnvironmentVariables for each daemon",
            "[ ] Step 4: python3 scripts/post_only_order_manager.py --dry-run (verify no errors)",
            "[ ] Step 5: Paper-trade 24h, confirm builder field in HL order payloads",
            "[ ] Step 6: Check HL referral dashboard — rebate > $0 after 24h",
            "[ ] Step 7: Restart live daemons via launchctl unload/load",
            "[ ] Ongoing: Daily rebate vs expected, weekly approval check",
        ],

        "security": {
            "builder_code_in_output": False,
            "note": (
                "HL_BUILDER_CODE is a public Ethereum wallet address, not a private key. "
                "Still excluded from git commits and report.html per security hygiene. "
                "Use env var — never hardcode in source."
            ),
        },
    }


# ─────────────────────────────────────────────────────────────────────────────
# CLI for testing and status
# ─────────────────────────────────────────────────────────────────────────────

def _cli_main():
    import argparse
    parser = argparse.ArgumentParser(
        description="K481 HL Builder Rebate Module — status and projection tool"
    )
    parser.add_argument("--status",    action="store_true", help="Show activation status")
    parser.add_argument("--project",   action="store_true", help="Show K523 3-point projection")
    parser.add_argument("--aum",       type=float, default=10_000_000.0, help="AUM in USD (default 10M)")
    parser.add_argument("--smoke",     action="store_true", help="Smoke test inject_builder_field()")
    parser.add_argument("--check-api", metavar="WALLET",  help="Check HL referral state for WALLET")
    args = parser.parse_args()

    if args.status or (not any([args.status, args.project, args.smoke, args.check_api])):
        status = get_builder_status()
        print(f"\n=== K481 Builder Rebate Status ===")
        print(f"  HL active:      {status['hl_active']}")
        print(f"  Source:         {status['source']}")
        print(f"  Code (masked):  {status['hl_code_masked']}")
        print(f"  Fee (tenths bp): {status['fee_tenths_bp']} (0 = ZERO extra cost)")
        print(f"  Checked UTC:    {status['checked_utc']}")

    if args.project:
        proj = k523_projection(args.aum)
        aum_m = args.aum / 1_000_000
        print(f"\n=== K523 3-Point Projection @ ${aum_m:.0f}M AUM ===")
        print(f"  Conservative (10%): ${proj['conservative_usdc_yr']:>10,.0f}/yr  "
              f"(${proj['conservative_daily']:>8.1f}/day)")
        print(f"  Central      (25%): ${proj['central_usdc_yr']:>10,.0f}/yr  "
              f"(${proj['central_daily']:>8.1f}/day)  ← realistic estimate")
        print(f"  Optimistic   (50%): ${proj['optimistic_usdc_yr']:>10,.0f}/yr  "
              f"(${proj['optimistic_daily']:>8.1f}/day)  ← upper bound")
        print(f"\n  {proj['memory_range_note']}")

    if args.smoke:
        print(f"\n=== Smoke Test: inject_builder_field() ===")
        # Test 1: dry_run → no injection
        order_action = {"type": "order", "orders": []}
        result = inject_builder_field(order_action, venue="HL", dry_run=True)
        assert "builder" not in order_action, "FAIL: builder injected in dry-run mode"
        print(f"  Test 1 (dry_run=True, HL): no-op → PASS (builder field absent as expected)")

        # Test 2: non-HL venue → no injection
        order_action2 = {"type": "order", "orders": []}
        result2 = inject_builder_field(order_action2, venue="Bybit", dry_run=False)
        assert "builder" not in order_action2, "FAIL: builder injected for Bybit venue"
        print(f"  Test 2 (venue=Bybit): no-op → PASS (Bybit unaffected)")

        # Test 3: HL venue, live mode, env var set or unset
        order_action3 = {"type": "order", "orders": []}
        result3 = inject_builder_field(order_action3, venue="HL", dry_run=False, strategy="SMOKE_TEST")
        if result3:
            assert "builder" in order_action3, "FAIL: injected=True but field missing"
            builder = order_action3["builder"]
            assert builder["f"] == 0, "FAIL: builder fee is not 0"
            assert isinstance(builder["b"], str) and builder["b"].startswith("0x"), "FAIL: builder address invalid"
            print(f"  Test 3 (HL live): INJECTED → PASS (code=...{builder['b'][-6:]}, f={builder['f']})")
        else:
            print(f"  Test 3 (HL live): SKIPPED (HL_BUILDER_CODE not set — expected in activation)")
            print(f"    Set HL_BUILDER_CODE env var to test live injection.")

        print(f"\n  Smoke test complete.")

    if args.check_api:
        wallet = args.check_api
        print(f"\n=== HL API Check: {wallet[:12]}... ===")
        print("  Referral state:")
        ref = check_referral_state(wallet)
        print(f"    {json.dumps(ref, indent=4)}")
        print("  Builder fees:")
        fees = check_builder_fees(wallet)
        print(f"    {json.dumps(fees, indent=4)}")


if __name__ == "__main__":
    _cli_main()
