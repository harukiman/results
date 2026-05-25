#!/usr/bin/env bash
# k302a_migration.sh — K302a Satellite Migration: K287d → K302a
# ==============================================================
# Migrates from K289 (K287d satellite: K270 dYdX + K275 OKX)
# to K305 (K302a satellite: K297 PAXG/SPX on HyperLiquid).
#
# K303 Deployment Plan (Day 0):
#   1. Stop K287 satellite daemon
#   2. Backup K287d cache files to cache/k287d_backup/
#   3. Load K302a satellite daemon
#   4. Reconciliation diff (K287d vs K302a positions/dashboards)
#
# K289 Deprecation:
#   - com.cryptolab.k287-satellite.plist: DISABLED (not deleted) — 60d rollback
#   - K287d cache files: PRESERVED in cache/k287d_backup/
#   - K287d scripts: PRESERVED in scripts/ (not removed)
#
# Usage:
#   bash scripts/k302a_migration.sh [--dry-run]
#
# Dry-run mode shows what WOULD happen without making changes.
#
# Date: 2026-05-25 | Wave: K305

set -euo pipefail

BASE="/Users/nekonaomichi/crypto-lab"
PYTHON="$BASE/.venv311/bin/python3"
LOG="$BASE/logs/k302a_migration.log"
BACKUP="$BASE/cache/k287d_backup"

DRY_RUN=false
if [[ "${1:-}" == "--dry-run" ]]; then
    DRY_RUN=true
    echo "[DRY RUN] No changes will be made."
fi

log() {
    local msg="[$(date -u '+%Y-%m-%d %H:%M:%S UTC')] $*"
    echo "$msg"
    if [ "$DRY_RUN" = false ]; then
        echo "$msg" >> "$LOG"
    fi
}

run_cmd() {
    if [ "$DRY_RUN" = true ]; then
        echo "[DRY RUN] Would run: $*"
    else
        "$@"
    fi
}

echo ""
echo "======================================================================"
echo "  K302a Migration: K289 (K287d) → K305 (K302a v6.12)"
echo "  $(date -u '+%Y-%m-%d %H:%M:%S UTC')"
echo "======================================================================"
echo ""

log "=== K302a Migration Start ==="

# ─────────────────────────────────────────────────────────────────────────────
# STEP 1: Stop K287 satellite daemon
# ─────────────────────────────────────────────────────────────────────────────
log "STEP 1: Stopping K287 satellite daemon..."

K287_PLIST="$HOME/Library/LaunchAgents/com.cryptolab.k287-satellite.plist"
K287_LABEL="com.cryptolab.k287-satellite"

if launchctl list | grep -q "$K287_LABEL" 2>/dev/null; then
    log "  K287 daemon is loaded. Unloading..."
    run_cmd launchctl unload "$K287_PLIST" 2>/dev/null || true
    log "  K287 daemon unloaded."
else
    log "  K287 daemon not currently loaded (already stopped or never installed)."
fi

# Disable K289 plist (rename, not delete) — retain for 60d rollback
K287_PLIST_SRC="$BASE/com.cryptolab.k287-satellite.plist"
K287_PLIST_DISABLED="$BASE/com.cryptolab.k287-satellite.plist.disabled_k305"
if [ -f "$K287_PLIST_SRC" ] && [ ! -f "$K287_PLIST_DISABLED" ]; then
    log "  Disabling K287 plist (renaming to .disabled_k305 for 60d rollback)..."
    run_cmd cp "$K287_PLIST_SRC" "$K287_PLIST_DISABLED"
    log "  K287 plist preserved as: $K287_PLIST_DISABLED"
elif [ -f "$K287_PLIST_DISABLED" ]; then
    log "  K287 plist already disabled (.disabled_k305 exists)."
else
    log "  WARNING: K287 plist not found at $K287_PLIST_SRC"
fi

echo ""

# ─────────────────────────────────────────────────────────────────────────────
# STEP 2: Backup K287d cache files
# ─────────────────────────────────────────────────────────────────────────────
log "STEP 2: Backing up K287d cache files to $BACKUP/..."

if [ "$DRY_RUN" = false ]; then
    mkdir -p "$BACKUP"
fi

K287_CACHE_FILES=(
    "$BASE/cache/k270_dydx_daily.parquet"
    "$BASE/cache/okx_fr_daily.parquet"
)

for f in "${K287_CACHE_FILES[@]}"; do
    if [ -f "$f" ]; then
        fname=$(basename "$f")
        log "  Backing up $fname..."
        run_cmd cp "$f" "$BACKUP/$fname"
    else
        log "  Not found (skip): $f"
    fi
done

# Backup k270_dydx/ per-symbol directory
DYDX_DIR="$BASE/cache/k270_dydx"
if [ -d "$DYDX_DIR" ]; then
    DYDX_BACKUP="$BACKUP/k270_dydx"
    log "  Backing up k270_dydx/ directory..."
    run_cmd cp -r "$DYDX_DIR" "$DYDX_BACKUP" 2>/dev/null || \
        log "  WARNING: Could not backup k270_dydx/ (may already exist)"
else
    log "  k270_dydx/ not found (skip)"
fi

# Backup K287 dashboard
K287_DASH="$BASE/data/k287_satellite_dashboard.json"
if [ -f "$K287_DASH" ]; then
    log "  Backing up k287_satellite_dashboard.json..."
    run_cmd cp "$K287_DASH" "$BACKUP/k287_satellite_dashboard_backup.json"
fi

# Backup K287 trade log
K287_LOG="$BASE/data/k287_satellite_paper_trades.jsonl"
if [ -f "$K287_LOG" ]; then
    log "  Backing up k287_satellite_paper_trades.jsonl..."
    run_cmd cp "$K287_LOG" "$BACKUP/k287_satellite_paper_trades_backup.jsonl"
fi

log "  Backup complete: $BACKUP/"
echo ""

# ─────────────────────────────────────────────────────────────────────────────
# STEP 3: Load K302a satellite daemon
# ─────────────────────────────────────────────────────────────────────────────
log "STEP 3: Loading K302a satellite daemon..."

K302A_PLIST_SRC="$BASE/com.cryptolab.k302a-satellite.plist"
K302A_PLIST_DST="$HOME/Library/LaunchAgents/com.cryptolab.k302a-satellite.plist"
K302A_LABEL="com.cryptolab.k302a-satellite"

if [ ! -f "$K302A_PLIST_SRC" ]; then
    log "  ERROR: K302a plist not found at $K302A_PLIST_SRC"
    log "  Run Wave K305 implementation first."
    exit 1
fi

run_cmd cp "$K302A_PLIST_SRC" "$K302A_PLIST_DST"
log "  Copied K302a plist to ~/Library/LaunchAgents/"

if launchctl list | grep -q "$K302A_LABEL" 2>/dev/null; then
    log "  K302a daemon already loaded. Reloading..."
    run_cmd launchctl unload "$K302A_PLIST_DST" 2>/dev/null || true
fi

run_cmd launchctl load "$K302A_PLIST_DST"
log "  K302a daemon loaded: $K302A_LABEL"

echo ""

# ─────────────────────────────────────────────────────────────────────────────
# STEP 4: Reconciliation diff
# ─────────────────────────────────────────────────────────────────────────────
log "STEP 4: Reconciliation diff (K287d vs K302a)..."
echo ""

# Run K302a fetch and execute to seed dashboard
log "  Running K302a initial fetch..."
if [ "$DRY_RUN" = false ]; then
    "$PYTHON" "$BASE/scripts/k302a_satellite_fetch.py" --force >> "$LOG" 2>&1
    log "  K302a fetch complete."

    log "  Running K302a initial execution..."
    "$PYTHON" "$BASE/scripts/k302a_satellite_run.py" >> "$LOG" 2>&1
    log "  K302a execution complete."
fi

echo ""
echo "======================================================================"
echo "  RECONCILIATION SUMMARY"
echo "======================================================================"
echo ""

if [ "$DRY_RUN" = false ]; then
    python3 - <<'EOF'
import json, os
from pathlib import Path

BASE = Path("/Users/nekonaomichi/crypto-lab")

print("--- K287d (DEPRECATED) Dashboard ---")
k287_path = BASE / "data" / "k287_satellite_dashboard.json"
if k287_path.exists():
    with open(k287_path) as f:
        k287 = json.load(f)
    rm = k287.get("rolling_metrics") or {}
    sw = k287.get("satellite_weights") or {}
    print(f"  Architecture:    {k287.get('architecture', 'K287d')}")
    print(f"  Sat weights:     K270={sw.get('K270', 0):.1%}  K275={sw.get('K275', 0):.1%}")
    print(f"  Sat Sh (30d):    {rm.get('sh_30d', 'N/A')}")
    print(f"  Sat Sh (all):    {rm.get('sh_all', 'N/A')}")
    print(f"  Sat MaxDD(all):  {rm.get('mdd_all', 'N/A')}")
    print(f"  Sat equity:      {k287.get('sat_equity', 'N/A')}")
    print(f"  Last update:     {k287.get('last_update', 'N/A')}")
    print(f"  Alert flags:     {k287.get('active_alert_flags', {})}")
else:
    print("  K287d dashboard not found.")

print("")
print("--- K302a (ACTIVE) Dashboard ---")
k302a_path = BASE / "data" / "k302a_satellite_dashboard.json"
if k302a_path.exists():
    with open(k302a_path) as f:
        k302a = json.load(f)
    rm = k302a.get("rolling_metrics") or {}
    sw = k302a.get("satellite_weights") or {}
    print(f"  Architecture:    {k302a.get('architecture', 'K302a')}")
    print(f"  Sat weights:     PAXG={sw.get('PAXG', 0):.1%}  SPX={sw.get('SPX', 0):.1%}")
    print(f"  Sat Sh (30d):    {rm.get('sh_30d', 'N/A')}")
    print(f"  Sat Sh (all):    {rm.get('sh_all', 'N/A')}")
    print(f"  Sat MaxDD(all):  {rm.get('mdd_all', 'N/A')}")
    print(f"  Sat equity:      {k302a.get('sat_equity', 'N/A')}")
    print(f"  Last update:     {k302a.get('last_update', 'N/A')}")
    print(f"  Alert flags:     {k302a.get('active_alert_flags', {})}")
else:
    print("  K302a dashboard not found.")

print("")
print("--- K280 Main Dashboard ---")
k280_path = BASE / "data" / "k280_live_dashboard.json"
if k280_path.exists():
    with open(k280_path) as f:
        k280 = json.load(f)
    rm = k280.get("rolling_metrics") or {}
    print(f"  Main Sh (30d):   {rm.get('sh_30d', 'N/A')}")
    print(f"  Main Sh (all):   {rm.get('sh_all', 'N/A')}")
    print(f"  Last update:     {k280.get('last_update', 'N/A')}")
else:
    print("  K280 dashboard not found.")

print("")
print("--- Daemon Status ---")
import subprocess
r = subprocess.run(["launchctl", "list"], capture_output=True, text=True)
for line in r.stdout.split("\n"):
    if "k280" in line or "k302a" in line or "k287" in line:
        print(f"  {line}")
EOF
fi

echo ""
log "=== K302a Migration Complete ==="
echo ""
echo "======================================================================"
echo "  NEXT STEPS (K303 Deployment Plan)"
echo "======================================================================"
echo ""
echo "  Day 1-14:  Shadow paper-trade K302a alongside K287d daily PnL delta"
echo "             Verify k302a_satellite_dashboard.json updates daily at 09:30 JST"
echo "  Day 15-30: K302a live at 20% target capital on HyperLiquid"
echo "             Monitor 14d rolling Sh ≥ 25.0 target"
echo "  Day 31+:   Full capital if 30d Sh ≥ 25.0"
echo "             K287d plist retained as 60d rollback (k287-satellite.plist.disabled_k305)"
echo ""
echo "  Monitoring:"
echo "    tail -f $BASE/logs/k302a_satellite.log"
echo "    tail -f $BASE/logs/k302a_satellite_err.log"
echo ""
echo "  Rollback to K287d (if needed):"
echo "    launchctl unload ~/Library/LaunchAgents/com.cryptolab.k302a-satellite.plist"
echo "    cp $BASE/com.cryptolab.k287-satellite.plist.disabled_k305 \\"
echo "       ~/Library/LaunchAgents/com.cryptolab.k287-satellite.plist"
echo "    launchctl load ~/Library/LaunchAgents/com.cryptolab.k287-satellite.plist"
echo ""
