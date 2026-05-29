#!/usr/bin/env python3
"""
scripts/multi_account_orchestrator.py
======================================
K485 Multi-Account Orchestrator — Design Draft (NOT production-ready)
Wave: K485 | Generated: 2026-05-30 02:54 JST

PURPOSE:
  Spawn, monitor, and aggregate positions/P&L across multiple wallet accounts
  (HL W1, HL W2, Bybit sub, dYdX, Aevo) in a single orchestration process.

USAGE:
  python3 scripts/multi_account_orchestrator.py [--dry-run] [--positions] [--wallets=W1,W2,all]

DESIGN:
  - Reads multi_account_config.json for wallet registry
  - For each wallet: load env vars from separate .env file (no hardcoded secrets)
  - Spawn per-wallet sub-processes for live daemons
  - Aggregate positions from all wallets → single dashboard update
  - Emergency exit: --exit-all flag closes all positions on all venues

SECURITY:
  - NEVER reads private keys from git-tracked files
  - Env vars loaded per-wallet from separate .env.{wallet_label} files
  - Private keys must be in macOS Keychain or 1Password CLI
  - Bybit sub: trade-only API keys (no withdrawal scope)

STATUS: DESIGN DRAFT — not production-ready. Review before live use.
"""

import argparse
import json
import os
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# ─── REPO_ROOT (K339 pattern) ────────────────────────────────────────────────
REPO_ROOT = Path(__file__).parent.parent.resolve()
CONFIG_PATH = REPO_ROOT / "multi_account_config.json"

# ─── Data Classes ─────────────────────────────────────────────────────────────

@dataclass
class WalletConfig:
    """Configuration for a single wallet/account."""
    id: str                              # e.g. "W1_HL_primary"
    label: str                           # human label
    exchange: str                        # "HL" | "Bybit" | "OKX" | "Aevo" | "dYdX"
    env_file: str                        # e.g. ".env.hl_w1" (NOT git-tracked)
    strategies: list[str]                # strategy IDs assigned to this wallet
    aum_target_usd: float                # capital allocation target
    active: bool = True                  # whether this wallet is live
    paper_mode: bool = False             # paper-trade mode
    note: str = ""

@dataclass
class WalletPosition:
    """Aggregated position data for a single wallet."""
    wallet_id: str
    exchange: str
    timestamp_utc: str
    total_equity_usd: float
    unrealized_pnl_usd: float
    daily_pnl_usd: float
    positions: list[dict] = field(default_factory=list)
    error: Optional[str] = None

@dataclass
class AggregatedState:
    """Cross-wallet aggregated state."""
    timestamp_utc: str
    total_aum_usd: float
    total_unrealized_pnl_usd: float
    total_daily_pnl_usd: float
    hl_combined_usd: float               # W1+W2 HL exposure
    hl_concentration_pct: float          # hl_combined / total_aum
    hl_concentration_ok: bool            # must be ≤ 65%
    wallets: list[WalletPosition] = field(default_factory=list)

# ─── Config Loader ─────────────────────────────────────────────────────────────

DEFAULT_CONFIG = {
    "accounts": [
        {
            "id": "W1_HL_primary",
            "label": "HL Primary (v6.13d operator)",
            "exchange": "HL",
            "env_file": ".env.hl_w1",
            "strategies": ["K280", "K297p", "sUSDe"],
            "aum_target_usd": 10_000_000,
            "active": True,
            "paper_mode": False,
            "note": "Main HL wallet. K280+K297p+sUSDe. HL_PRIVATE_KEY in env."
        },
        {
            "id": "W2_HL_strategy_iso",
            "label": "HL W2 (K449+K476 strategy isolation)",
            "exchange": "HL",
            "env_file": ".env.hl_w2",
            "strategies": ["K449", "K476"],
            "aum_target_usd": 2_000_000,
            "active": False,
            "paper_mode": True,
            "note": "Same HL OB. Strategy isolation only. HL_PRIVATE_KEY_W2 in env."
        },
        {
            "id": "W3_Bybit_sub1",
            "label": "Bybit Sub #1 (K297p overflow + K208 Bybit leg)",
            "exchange": "Bybit",
            "env_file": ".env.bybit_sub1",
            "strategies": ["K208_Bybit", "K297p_overflow"],
            "aum_target_usd": 7_500_000,
            "active": False,
            "paper_mode": True,
            "note": "Bybit sub-account. Trade-only API. BYBIT_SUB1_API_KEY in env."
        },
        {
            "id": "W4_dYdX_cosmos",
            "label": "dYdX v4 Cosmos wallet (K208 5th venue)",
            "exchange": "dYdX",
            "env_file": ".env.dydx",
            "strategies": ["K208_dYdX"],
            "aum_target_usd": 2_500_000,
            "active": False,
            "paper_mode": True,
            "note": "Cosmos chain wallet. DYDX_MNEMONIC in env. K460 scaffolded."
        },
        {
            "id": "W5_Aevo_evm",
            "label": "Aevo EVM wallet (K208 4th venue, 1h funding cycle)",
            "exchange": "Aevo",
            "env_file": ".env.aevo",
            "strategies": ["K208_Aevo"],
            "aum_target_usd": 2_500_000,
            "active": False,
            "paper_mode": True,
            "note": "EVM wallet on OP Stack. AEVO_PRIVATE_KEY in env. K460 scaffolded."
        }
    ],
    "hl_concentration_limit_pct": 65.0,
    "emergency_exit_script": "scripts/emergency_hl_exit.py",
    "monitoring_interval_seconds": 300,
}


def load_config() -> dict:
    """Load multi_account_config.json or return default."""
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH) as f:
            return json.load(f)
    # Write default config on first run
    with open(CONFIG_PATH, "w") as f:
        json.dump(DEFAULT_CONFIG, f, indent=2)
    print(f"[orchestrator] Default config written to {CONFIG_PATH}")
    print("[orchestrator] Edit multi_account_config.json to activate wallets.")
    return DEFAULT_CONFIG


def load_wallet_env(env_file: str) -> dict:
    """
    Load environment variables from .env.{label} file.
    Returns dict of key-value pairs. File must NOT be git-tracked.
    """
    env_path = REPO_ROOT / env_file
    if not env_path.exists():
        return {}
    env_vars = {}
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            env_vars[key.strip()] = val.strip().strip('"').strip("'")
    return env_vars

# ─── Position Fetchers (stubs — implement per-exchange) ──────────────────────

def fetch_hl_positions(wallet_id: str, env_vars: dict, dry_run: bool = False) -> WalletPosition:
    """Fetch positions from HL for given wallet."""
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    if dry_run:
        return WalletPosition(
            wallet_id=wallet_id,
            exchange="HL",
            timestamp_utc=ts,
            total_equity_usd=10_000_000.0,
            unrealized_pnl_usd=15_234.0,
            daily_pnl_usd=4_512.0,
            positions=[{"symbol": "BTC-PERP", "size": 1.5, "side": "long"}],
        )
    # TODO: integrate with HL SDK
    # from hyperliquid.info import Info
    # info = Info(env_vars.get("HL_BASE_URL", "https://api.hyperliquid.xyz"))
    # state = info.user_state(env_vars["HL_WALLET_ADDRESS"])
    # return WalletPosition(...)
    return WalletPosition(
        wallet_id=wallet_id, exchange="HL", timestamp_utc=ts,
        total_equity_usd=0.0, unrealized_pnl_usd=0.0, daily_pnl_usd=0.0,
        error="HL position fetch not yet implemented — integrate with HL SDK"
    )


def fetch_bybit_positions(wallet_id: str, env_vars: dict, dry_run: bool = False) -> WalletPosition:
    """Fetch positions from Bybit sub-account."""
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    if dry_run:
        return WalletPosition(
            wallet_id=wallet_id, exchange="Bybit", timestamp_utc=ts,
            total_equity_usd=7_500_000.0, unrealized_pnl_usd=8_100.0,
            daily_pnl_usd=2_300.0, positions=[],
        )
    # TODO: integrate with Bybit SDK
    # from pybit.unified_trading import HTTP
    # session = HTTP(api_key=env_vars["BYBIT_SUB1_API_KEY"],
    #               api_secret=env_vars["BYBIT_SUB1_SECRET"])
    # result = session.get_wallet_balance(accountType="UNIFIED")
    return WalletPosition(
        wallet_id=wallet_id, exchange="Bybit", timestamp_utc=ts,
        total_equity_usd=0.0, unrealized_pnl_usd=0.0, daily_pnl_usd=0.0,
        error="Bybit position fetch not yet implemented — integrate pybit SDK"
    )


def fetch_positions(wallet: dict, dry_run: bool = False) -> WalletPosition:
    """Dispatch position fetch to correct exchange handler."""
    env_vars = load_wallet_env(wallet["env_file"])
    exchange = wallet["exchange"]

    fetchers = {
        "HL":    fetch_hl_positions,
        "Bybit": fetch_bybit_positions,
        # "OKX": fetch_okx_positions,   # K456 integration
        # "Aevo": fetch_aevo_positions,  # K460 integration
        # "dYdX": fetch_dydx_positions,  # K460 integration
    }

    if exchange not in fetchers:
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        return WalletPosition(
            wallet_id=wallet["id"], exchange=exchange, timestamp_utc=ts,
            total_equity_usd=0.0, unrealized_pnl_usd=0.0, daily_pnl_usd=0.0,
            error=f"{exchange} fetcher not yet implemented"
        )

    return fetchers[exchange](wallet["id"], env_vars, dry_run=dry_run)

# ─── Aggregation ──────────────────────────────────────────────────────────────

def aggregate_positions(wallet_positions: list[WalletPosition],
                        config: dict) -> AggregatedState:
    """Aggregate positions across all wallets."""
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    total_aum = sum(w.total_equity_usd for w in wallet_positions if w.error is None)
    total_upnl = sum(w.unrealized_pnl_usd for w in wallet_positions if w.error is None)
    total_dpnl = sum(w.daily_pnl_usd for w in wallet_positions if w.error is None)

    hl_combined = sum(
        w.total_equity_usd for w in wallet_positions
        if w.exchange == "HL" and w.error is None
    )
    hl_pct = (hl_combined / total_aum * 100) if total_aum > 0 else 0.0
    hl_limit = config.get("hl_concentration_limit_pct", 65.0)

    return AggregatedState(
        timestamp_utc=ts,
        total_aum_usd=total_aum,
        total_unrealized_pnl_usd=total_upnl,
        total_daily_pnl_usd=total_dpnl,
        hl_combined_usd=hl_combined,
        hl_concentration_pct=round(hl_pct, 1),
        hl_concentration_ok=hl_pct <= hl_limit,
        wallets=wallet_positions,
    )

# ─── Emergency Exit ───────────────────────────────────────────────────────────

def emergency_exit_all(config: dict, dry_run: bool = True):
    """
    Emergency exit: close all positions on all venues.
    DESIGN: calls exchange-specific emergency exit scripts per wallet.
    CRITICAL: Always test with --dry-run first.
    """
    exit_script = REPO_ROOT / config.get("emergency_exit_script", "scripts/emergency_hl_exit.py")

    print("[EMERGENCY EXIT] Initiating emergency exit across all wallets...")
    if dry_run:
        print("[EMERGENCY EXIT] DRY RUN — no actual orders sent.")

    for wallet in config["accounts"]:
        if not wallet.get("active", False):
            continue
        wallet_id = wallet["id"]
        exchange = wallet["exchange"]
        env_vars = load_wallet_env(wallet["env_file"])

        print(f"[EMERGENCY EXIT] {wallet_id} ({exchange}) ...", end=" ")
        if dry_run:
            print("DRY RUN OK")
            continue

        # HL emergency exit
        if exchange == "HL" and exit_script.exists():
            private_key = env_vars.get("HL_PRIVATE_KEY", "")
            if not private_key:
                print(f"ERROR: no HL_PRIVATE_KEY in {wallet['env_file']}")
                continue
            env = {**os.environ, "HL_PRIVATE_KEY": private_key}
            result = subprocess.run(
                [sys.executable, str(exit_script), f"--wallet={wallet_id}"],
                env=env, capture_output=True, text=True, timeout=30
            )
            if result.returncode == 0:
                print("OK")
            else:
                print(f"ERROR: {result.stderr[:100]}")
        else:
            print(f"WARN: No emergency exit handler for {exchange}. Implement manually.")

# ─── Report Summary ───────────────────────────────────────────────────────────

def print_summary(state: AggregatedState):
    """Print aggregated state to stdout."""
    print(f"\n{'='*60}")
    print(f"K485 Multi-Account State — {state.timestamp_utc}")
    print(f"{'='*60}")
    print(f"Total AUM:          ${state.total_aum_usd:>12,.0f}")
    print(f"Unrealized P&L:     ${state.total_unrealized_pnl_usd:>12,.0f}")
    print(f"Daily P&L:          ${state.total_daily_pnl_usd:>12,.0f}")
    print(f"HL Combined:        ${state.hl_combined_usd:>12,.0f}")
    hl_ok = "OK" if state.hl_concentration_ok else "ALERT OVER 65%"
    print(f"HL Concentration:   {state.hl_concentration_pct:>11.1f}%  [{hl_ok}]")
    print()

    print(f"{'Wallet':<25} {'Exchange':>8} {'AUM':>12} {'Day P&L':>10} {'Status':>12}")
    print("-" * 72)
    for w in state.wallets:
        status = "ERROR" if w.error else "OK"
        aum_str = f"${w.total_equity_usd:>10,.0f}" if not w.error else "N/A"
        pnl_str = f"${w.daily_pnl_usd:>8,.0f}" if not w.error else "N/A"
        print(f"{w.wallet_id:<25} {w.exchange:>8} {aum_str:>12} {pnl_str:>10} {status:>12}")
        if w.error:
            print(f"  └ {w.error}")

# ─── CLI ──────────────────────────────────────────────────────────────────────

def parse_args():
    p = argparse.ArgumentParser(description="K485 Multi-Account Orchestrator")
    p.add_argument("--dry-run", action="store_true",
                   help="Simulate without fetching real data or sending orders")
    p.add_argument("--positions", action="store_true",
                   help="Fetch and display current positions across all wallets")
    p.add_argument("--wallets", default="all",
                   help="Comma-separated wallet IDs to include, or 'all'")
    p.add_argument("--exit-all", action="store_true",
                   help="EMERGENCY: close all positions on all venues")
    p.add_argument("--config-check", action="store_true",
                   help="Validate config and env files, then exit")
    return p.parse_args()


def main():
    args = parse_args()
    config = load_config()

    print(f"[orchestrator] K485 Multi-Account Orchestrator")
    print(f"[orchestrator] Config: {CONFIG_PATH}")
    print(f"[orchestrator] Dry run: {args.dry_run}")

    # Filter wallets
    all_wallets = config["accounts"]
    if args.wallets != "all":
        wanted = {w.strip() for w in args.wallets.split(",")}
        all_wallets = [w for w in all_wallets if w["id"] in wanted]

    # Config check
    if args.config_check:
        for wallet in all_wallets:
            env_file = REPO_ROOT / wallet["env_file"]
            exists = env_file.exists()
            active = wallet.get("active", False)
            print(f"  {wallet['id']:<25} env_file={'OK' if exists else 'MISSING':<8} active={active}")
        return

    # Emergency exit
    if args.exit_all:
        print("[orchestrator] EMERGENCY EXIT MODE")
        if not args.dry_run:
            confirm = input("Type 'CONFIRM' to proceed with emergency exit: ")
            if confirm != "CONFIRM":
                print("[orchestrator] Emergency exit cancelled.")
                return
        emergency_exit_all(config, dry_run=args.dry_run)
        return

    # Positions fetch + aggregate
    if args.positions or args.dry_run:
        active_wallets = [w for w in all_wallets if w.get("active", False) or args.dry_run]
        positions = [fetch_positions(w, dry_run=args.dry_run) for w in active_wallets]
        state = aggregate_positions(positions, config)
        print_summary(state)

        # HL concentration alert
        if not state.hl_concentration_ok:
            print(f"\n!!! ALERT: HL concentration {state.hl_concentration_pct:.1f}% > 65% limit !!!")
            print("  Action: reduce HL exposure or increase non-HL AUM.")

        return

    print("[orchestrator] No action specified. Use --positions, --dry-run, or --exit-all.")
    print("[orchestrator] See --help for options.")


if __name__ == "__main__":
    main()
