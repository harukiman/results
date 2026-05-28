#!/usr/bin/env python3
"""K415 USDY Sleeve Paper-Trade Scaffold — v6.15a/b activation pathway.

Single-shot execution. Daily cron via launchd (StartCalendarInterval: 06:00 JST).
Paper-trades a virtual USDY position (sleeve_pct × AUM) earning daily accrual from
the Ondo USDY APY. Reads price/yield from Ondo public API or DefiLlama fallback.

IMPORTANT — This is a PAPER-TRADE SCAFFOLD ONLY:
  - No on-chain transactions are performed
  - No real USDY is purchased
  - User must register on Ondo Finance and confirm non-US residency before activation
  - See docs/k302a_runbook.md §21 for full activation playbook

K415 context:
  K400 CONDITIONAL_ACCEPT: USDY 5-10% sleeve, requires non-US residency verification.
  v6.15a: K280 75% + K297' 15% + sUSDe 5% + USDY 5%  → HL exposure 52.5%
  v6.15b: K280 75% + K297' 10% + sUSDe 5% + USDY 10% → HL exposure 47.5% (< 50% first time)
  Default recommendation: v6.15b (concentration risk > yield cost)

EMERGENCY flag check:
  If EMERGENCY_EXIT_TRIGGERED.flag exists → exit 0 immediately.
  USDY is NOT part of HL emergency exit (T-bill yield = safe during crisis).
  Do NOT redeem USDY in emergencies — hold through crisis, see §21.6.

Security (K339):
  REPO_ROOT = Path(__file__).resolve().parent.parent — no /Users/ literals

Universe: USDY virtual position only.

Dashboard: data/k415_usdy_dashboard.json
Logs: logs/k415_usdy_sleeve.log / logs/k415_usdy_sleeve.err
"""
from __future__ import annotations

import json
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional, Any

# ── K339 Security: REPO_ROOT from __file__, no /Users/ literals ──────────────
REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR  = REPO_ROOT / "data"
LOGS_DIR  = REPO_ROOT / "logs"
CACHE_DIR = REPO_ROOT / "cache"

DASHBOARD_JSON   = DATA_DIR  / "k415_usdy_dashboard.json"
LOG_FILE         = LOGS_DIR  / "k415_usdy_sleeve.log"
ERR_FILE         = LOGS_DIR  / "k415_usdy_sleeve.err"
EMERGENCY_FLAG   = REPO_ROOT / "EMERGENCY_EXIT_TRIGGERED.flag"

JST = timezone(timedelta(hours=9))

# ── USDY constants (Ondo Finance) ─────────────────────────────────────────────
USDY_EXPECTED_APY_PCT      = 4.5       # ~4.5% APY (T-bill backed, Ondo 2026-05)
USDY_LOCK_DAYS             = 40        # Initial lock period (40 calendar days)
USDY_REDEMPTION_DAYS       = 1         # Business days after lock expires
USDY_MINIMUM_USD           = 500.0     # Minimum investment (Ethereum network)
USDY_ONDO_URL              = "https://ondo.finance/"    # For documentation reference

# DefiLlama pool ID for USDY (Ondo USDY Ethereum)
# If this pool ID changes, update here. Falls back to USDY_EXPECTED_APY_PCT.
DEFILAMA_USDY_POOL_ID      = "d4b19b66-e4a0-4dc4-a0db-6b2ee0c7e3af"
DEFILAMA_YIELDS_URL        = f"https://yields.llama.fi/chart/{DEFILAMA_USDY_POOL_ID}"

# Ondo public price API (USDY price, best-effort)
ONDO_USDY_PRICE_URL        = "https://api.ondo.finance/v1/usdy/price"

# ── Default portfolio params (operator-configurable via dashboard JSON) ────────
DEFAULT_AUM_USD             = 10_000.0   # Assumed AUM for paper-trade PnL calc
DEFAULT_SLEEVE_PCT_A        = 0.05       # v6.15a: 5% USDY sleeve
DEFAULT_SLEEVE_PCT_B        = 0.10       # v6.15b: 10% USDY sleeve

# Default: v6.15b (concentration risk > yield cost per K415 recommendation)
DEFAULT_SLEEVE_PCT          = DEFAULT_SLEEVE_PCT_B
DEFAULT_VARIANT             = "v6.15b"


# ── Logging ───────────────────────────────────────────────────────────────────

def _ts() -> str:
    return datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S JST")


def log_msg(msg: str) -> None:
    try:
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        with open(LOG_FILE, "a") as f:
            f.write(f"[{_ts()}] {msg}\n")
    except Exception as e:
        print(f"[log_msg fail] {e}", file=sys.stderr)


def log_err(msg: str) -> None:
    try:
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        with open(ERR_FILE, "a") as f:
            f.write(f"[{_ts()}] {msg}\n")
    except Exception as e:
        print(f"[log_err fail] {e}", file=sys.stderr)


# ── USDY price / APY fetch ────────────────────────────────────────────────────

def fetch_usdy_apy_defilama() -> Optional[float]:
    """Try to get USDY current APY from DefiLlama yields API.

    Returns APY as float (e.g. 4.5 = 4.5%) or None on error.
    Uses the most recent data point from the chart endpoint.
    """
    try:
        with urllib.request.urlopen(DEFILAMA_YIELDS_URL, timeout=15) as resp:
            if resp.status != 200:
                log_err(f"fetch_usdy_apy_defilama: HTTP {resp.status}")
                return None
            raw = json.loads(resp.read().decode("utf-8"))
            data = raw.get("data") if isinstance(raw, dict) else raw
            if not data or not isinstance(data, list):
                log_err("fetch_usdy_apy_defilama: empty or malformed response")
                return None
            # Most recent point is last in list
            last = data[-1]
            apy = last.get("apy") if isinstance(last, dict) else None
            if apy is not None:
                apy_float = float(apy)
                log_msg(f"fetch_usdy_apy_defilama: APY={apy_float:.4f}% (DefiLlama)")
                return apy_float
    except urllib.error.URLError as e:
        log_err(f"fetch_usdy_apy_defilama: URLError {e}")
    except Exception as e:
        log_err(f"fetch_usdy_apy_defilama: {type(e).__name__} {e}")
    return None


def fetch_usdy_price_ondo() -> Optional[float]:
    """Try to fetch USDY price from Ondo public API.

    Returns price as float (e.g. 1.0472) or None on error.
    USDY is not a stablecoin — it accretes daily in USD terms.
    """
    try:
        req = urllib.request.Request(
            ONDO_USDY_PRICE_URL,
            headers={"User-Agent": "ct-k415-scaffold/1.0"},
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            if resp.status != 200:
                log_err(f"fetch_usdy_price_ondo: HTTP {resp.status}")
                return None
            raw = json.loads(resp.read().decode("utf-8"))
            # Ondo API format may vary; try common keys
            price = (
                raw.get("price")
                or raw.get("nav")
                or raw.get("usdy_price")
                or raw.get("data", {}).get("price")
                if isinstance(raw, dict) else None
            )
            if price is not None:
                price_float = float(price)
                log_msg(f"fetch_usdy_price_ondo: price=${price_float:.6f} (Ondo API)")
                return price_float
    except urllib.error.URLError as e:
        log_err(f"fetch_usdy_price_ondo: URLError {e} (Ondo API may require auth — using fallback)")
    except Exception as e:
        log_err(f"fetch_usdy_price_ondo: {type(e).__name__} {e}")
    return None


def get_usdy_apy() -> tuple[float, str]:
    """Resolve USDY APY with fallback chain.

    Priority:
      1. DefiLlama yields API (USDY pool)
      2. Hard-coded expected APY constant (USDY_EXPECTED_APY_PCT)

    Returns: (apy_pct: float, source: str)
    """
    apy = fetch_usdy_apy_defilama()
    if apy is not None and 0.1 < apy < 20.0:  # Sanity check
        return apy, "DefiLlama"

    log_msg(f"Using fallback USDY APY: {USDY_EXPECTED_APY_PCT}%")
    return USDY_EXPECTED_APY_PCT, "fallback_constant"


def get_usdy_price() -> tuple[float, str]:
    """Resolve USDY price with fallback chain.

    Priority:
      1. Ondo public API
      2. Compute from expected APY (nav = 1 + cumulative_accretion)

    Returns: (price: float, source: str)
    """
    price = fetch_usdy_price_ondo()
    if price is not None and 0.9 < price < 2.0:  # Sanity check
        return price, "Ondo API"

    # Fallback: approximate current nav from expected APY
    # USDY launched 2023-08-08; approximate accretion since then
    launch_date = datetime(2023, 8, 8, tzinfo=timezone.utc)
    days_since_launch = (datetime.now(timezone.utc) - launch_date).days
    approx_nav = 1.0 * (1 + USDY_EXPECTED_APY_PCT / 100.0) ** (days_since_launch / 365.0)
    log_msg(f"Using computed USDY NAV: ${approx_nav:.6f} (APY={USDY_EXPECTED_APY_PCT}%, day {days_since_launch})")
    return approx_nav, "computed_from_apy"


# ── PnL computation ───────────────────────────────────────────────────────────

def compute_daily_pnl(
    aum_usd: float,
    sleeve_pct: float,
    apy_pct: float,
) -> dict:
    """Compute daily PnL for virtual USDY sleeve.

    Args:
        aum_usd:    Total portfolio AUM in USD
        sleeve_pct: USDY allocation fraction (e.g. 0.10 for 10%)
        apy_pct:    Annual percentage yield (e.g. 4.5 for 4.5%)

    Returns dict with daily/monthly/annual PnL projections.
    """
    sleeve_usd = aum_usd * sleeve_pct
    daily_rate = apy_pct / 100.0 / 365.0
    daily_pnl_usd = sleeve_usd * daily_rate
    monthly_pnl_usd = sleeve_usd * (apy_pct / 100.0 / 12.0)
    annual_pnl_usd  = sleeve_usd * (apy_pct / 100.0)
    annual_pnl_pct_of_aum = (annual_pnl_usd / aum_usd) * 100.0  # pp contribution to portfolio

    return {
        "sleeve_usd":           round(sleeve_usd, 2),
        "sleeve_pct":           round(sleeve_pct * 100.0, 2),
        "daily_pnl_usd":        round(daily_pnl_usd, 4),
        "monthly_pnl_usd":      round(monthly_pnl_usd, 2),
        "annual_pnl_usd":       round(annual_pnl_usd, 2),
        "annual_pnl_pct_of_aum": round(annual_pnl_pct_of_aum, 4),
        "daily_rate_pct":       round(daily_rate * 100.0, 6),
    }


def compute_lock_status(
    purchase_date_iso: Optional[str],
) -> dict:
    """Determine lock status based on purchase date.

    Args:
        purchase_date_iso: ISO date string of USDY purchase ("YYYY-MM-DD"), or None.

    Returns dict with lock status, days remaining, unlock date.
    """
    if purchase_date_iso is None:
        return {
            "purchase_date": None,
            "lock_status":   "NOT_PURCHASED",
            "days_remaining": USDY_LOCK_DAYS,
            "unlock_date":   None,
            "is_liquid":     False,
            "note": "USDY not yet purchased. User action required: register at ondo.finance",
        }

    try:
        purchase_dt = datetime.fromisoformat(purchase_date_iso).replace(tzinfo=timezone.utc)
    except ValueError:
        return {
            "purchase_date": purchase_date_iso,
            "lock_status":   "PARSE_ERROR",
            "days_remaining": USDY_LOCK_DAYS,
            "unlock_date":   None,
            "is_liquid":     False,
            "note": f"Cannot parse purchase_date: {purchase_date_iso}",
        }

    now = datetime.now(timezone.utc)
    days_held = (now - purchase_dt).days
    unlock_dt = purchase_dt + timedelta(days=USDY_LOCK_DAYS)
    days_remaining = max(0, (unlock_dt - now).days)

    if days_held < USDY_LOCK_DAYS:
        return {
            "purchase_date":  purchase_date_iso,
            "lock_status":    "LOCKED",
            "days_held":      days_held,
            "days_remaining": days_remaining,
            "unlock_date":    unlock_dt.strftime("%Y-%m-%d"),
            "is_liquid":      False,
            "note": (
                f"USDY still in {USDY_LOCK_DAYS}-day initial lock. "
                f"Unlocks {unlock_dt.strftime('%Y-%m-%d')} ({days_remaining}d remaining). "
                "Earning ~{:.2f}% APY. DO NOT treat as emergency reserve until unlock.".format(
                    USDY_EXPECTED_APY_PCT
                )
            ),
        }
    else:
        return {
            "purchase_date":  purchase_date_iso,
            "lock_status":    "LIQUID",
            "days_held":      days_held,
            "days_remaining": 0,
            "unlock_date":    unlock_dt.strftime("%Y-%m-%d"),
            "is_liquid":      True,
            "note": (
                f"USDY fully liquid as of {unlock_dt.strftime('%Y-%m-%d')}. "
                f"Redemption: {USDY_REDEMPTION_DAYS} business day. "
                "v6.15 fully operational."
            ),
        }


# ── Dashboard writer ──────────────────────────────────────────────────────────

def write_dashboard(payload: dict) -> None:
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        with open(DASHBOARD_JSON, "w") as f:
            json.dump(payload, f, indent=2)
        log_msg(f"Dashboard written: {DASHBOARD_JSON}")
    except Exception as e:
        log_err(f"write_dashboard: {e}")


# ── Main ─────────────────────────────────────────────────────────────────────

def main() -> int:
    """Single-shot K415 USDY sleeve paper-trade run."""
    try:
        # ── EMERGENCY flag check ──────────────────────────────────────────────
        if EMERGENCY_FLAG.exists():
            log_msg(
                f"EMERGENCY_EXIT_TRIGGERED.flag detected — exiting. "
                "USDY is safe (T-bill yield); no redemption required. "
                "Hold USDY through crisis. See §21.6."
            )
            return 0

        log_msg("K415 USDY sleeve paper-trade scaffold started")

        # ── Load existing dashboard (for purchase_date, aum, variant) ─────────
        existing: dict = {}
        if DASHBOARD_JSON.exists():
            try:
                with open(DASHBOARD_JSON, "r") as f:
                    existing = json.load(f)
            except Exception as e:
                log_err(f"Failed to read existing dashboard: {e}")

        aum_usd       = float(existing.get("aum_usd", DEFAULT_AUM_USD))
        sleeve_pct    = float(existing.get("sleeve_pct_decimal", DEFAULT_SLEEVE_PCT))
        variant       = str(existing.get("variant", DEFAULT_VARIANT))
        purchase_date = existing.get("usdy_purchase_date")  # None until user buys

        # ── Fetch USDY APY and price ──────────────────────────────────────────
        apy_pct, apy_source = get_usdy_apy()
        price, price_source = get_usdy_price()

        # ── Compute PnL ───────────────────────────────────────────────────────
        pnl = compute_daily_pnl(aum_usd, sleeve_pct, apy_pct)

        # Also compute both variants for comparison
        pnl_a = compute_daily_pnl(aum_usd, DEFAULT_SLEEVE_PCT_A, apy_pct)
        pnl_b = compute_daily_pnl(aum_usd, DEFAULT_SLEEVE_PCT_B, apy_pct)

        # ── Lock status ───────────────────────────────────────────────────────
        lock_status = compute_lock_status(purchase_date)

        # ── Portfolio composition for active variant ──────────────────────────
        k297_pct = 0.15 if variant == "v6.15a" else 0.10
        composition = {
            "K280_core_pct":   75.0,
            "K297_satellite_pct": k297_pct * 100.0,
            "sUSDe_sleeve_pct":  5.0,
            "USDY_sleeve_pct":   sleeve_pct * 100.0,
            "HL_exposure_pct":   (75.0 * 0.50 + k297_pct * 100.0),  # K280 HL leg ~50% + K297' HL-only
            "total_pct":         100.0,
        }

        # ── Yield cost vs concentration benefit ──────────────────────────────
        # Yield cost = annual yield lost vs keeping capital in HL strategies
        # Conservative: assume HL strategies earn ~10% ann; USDY earns ~4.5% ann
        hl_assumed_ann_return = 10.0  # % (v6.13d target ~10-15%)
        yield_cost_pp = sleeve_pct * (hl_assumed_ann_return - apy_pct)  # pp opportunity cost
        hl_reduction_pp = composition["HL_exposure_pct"] - 57.5  # vs v6.13d baseline 57.5%

        # ── Build dashboard ───────────────────────────────────────────────────
        now_jst = datetime.now(JST)
        dashboard = {
            "last_run_jst":        now_jst.strftime("%Y-%m-%d %H:%M:%S JST"),
            "last_run_utc":        datetime.now(timezone.utc).isoformat(),
            "wave":                "K415",
            "scaffold_status":     "PAPER-TRADE",
            "variant":             variant,
            "aum_usd":             aum_usd,
            "sleeve_pct_decimal":  sleeve_pct,
            "usdy_purchase_date":  purchase_date,

            # APY and price
            "usdy_apy_pct":        round(apy_pct, 4),
            "usdy_apy_source":     apy_source,
            "usdy_price_usd":      round(price, 6),
            "usdy_price_source":   price_source,

            # Daily PnL for active variant
            "pnl": pnl,

            # Comparison table
            "variant_comparison": {
                "v6.15a": {
                    "sleeve_pct":         5.0,
                    "k297_pct":           15.0,
                    "hl_exposure_pct":    52.5,
                    "annual_pnl_usd":     pnl_a["annual_pnl_usd"],
                    "yield_cost_pp_ann":  round(DEFAULT_SLEEVE_PCT_A * (hl_assumed_ann_return - apy_pct), 3),
                    "daily_pnl_usd":      pnl_a["daily_pnl_usd"],
                },
                "v6.15b": {
                    "sleeve_pct":         10.0,
                    "k297_pct":           10.0,
                    "hl_exposure_pct":    47.5,
                    "annual_pnl_usd":     pnl_b["annual_pnl_usd"],
                    "yield_cost_pp_ann":  round(DEFAULT_SLEEVE_PCT_B * (hl_assumed_ann_return - apy_pct), 3),
                    "daily_pnl_usd":      pnl_b["daily_pnl_usd"],
                },
            },

            # Lock status
            "lock_status":         lock_status,

            # Portfolio composition
            "composition":         composition,

            # Opportunity cost analysis
            "opportunity_cost": {
                "hl_assumed_ann_return_pct":  hl_assumed_ann_return,
                "usdy_apy_pct":               round(apy_pct, 4),
                "yield_cost_pp_ann":           round(yield_cost_pp, 4),
                "hl_exposure_reduction_pp":    round(hl_reduction_pp, 1),
                "note": (
                    f"K415 default: v6.15b. Yield cost ~{yield_cost_pp:.2f}pp/yr vs "
                    f"HL exposure reduction {-hl_reduction_pp:.1f}pp. "
                    "Concentration risk > yield cost per K355/K415."
                ),
            },

            # Activation status
            "activation_status": {
                "user_confirmed_non_us":  existing.get("user_confirmed_non_us", False),
                "ondo_kyc_complete":      existing.get("ondo_kyc_complete", False),
                "usdy_purchase_date":     purchase_date,
                "v613d_parallel_active":  True,  # v6.13d continues during lock phase
                "ready_to_activate":      (
                    existing.get("user_confirmed_non_us", False)
                    and existing.get("ondo_kyc_complete", False)
                    and purchase_date is not None
                ),
                "next_action": (
                    "Confirm non-US residency → register at ondo.finance → complete KYC → purchase USDY"
                    if not existing.get("user_confirmed_non_us", False)
                    else "Complete Ondo KYC and purchase USDY"
                    if not existing.get("ondo_kyc_complete", False)
                    else "Waiting for 40-day lock to expire: " + (lock_status.get("unlock_date") or "—")
                    if lock_status.get("lock_status") == "LOCKED"
                    else "v6.15 fully operational — USDY liquid"
                ),
            },

            # Reference
            "reference": {
                "ondo_onboarding_url":   USDY_ONDO_URL,
                "defilama_pool_id":      DEFILAMA_USDY_POOL_ID,
                "runbook_section":       "docs/k302a_runbook.md §21",
                "k400_decision":         "CONDITIONAL_ACCEPT (non-US residency required)",
                "k415_default_variant":  "v6.15b (concentration risk > yield cost)",
                "emergency_note":        "USDY is NOT part of HL emergency exit. Hold through crisis.",
            },
        }

        write_dashboard(dashboard)

        # ── Log summary ───────────────────────────────────────────────────────
        log_msg(
            f"USDY APY={apy_pct:.2f}% ({apy_source}) | price=${price:.4f} ({price_source}) | "
            f"variant={variant} sleeve={sleeve_pct*100:.0f}% | "
            f"daily_pnl=${pnl['daily_pnl_usd']:.4f} | "
            f"annual_pnl=${pnl['annual_pnl_usd']:.2f} | "
            f"lock_status={lock_status['lock_status']} | "
            f"hl_exposure={composition['HL_exposure_pct']:.1f}%"
        )
        log_msg("K415 USDY sleeve paper-trade scaffold completed successfully")
        return 0

    except Exception as e:
        log_err(f"Unhandled exception: {type(e).__name__} {e}")
        return 0  # Exit cleanly even on exception


if __name__ == "__main__":
    sys.exit(main())
