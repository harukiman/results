"""Wave K90 — v4 daemon health monitor.

Run periodically to check:
- Paper trade daemon status (launchctl)
- Recent snapshots
- Equity trajectory
- Signal generation activity (per axis)
- Alert when equity DD exceeds threshold or daemon silent
"""
import json
import subprocess
from datetime import datetime, timezone, timedelta
from pathlib import Path
import sys

STATE_PATH = Path("/Users/nekonaomichi/crypto-lab/paper_trades_4way.json")
DAEMON_NAME = "com.cryptolab.paper-trade-4way"
SILENT_THRESHOLD_HOURS = 8  # alert if no snapshot in 8h
DD_THRESHOLD_PCT = -5.0  # alert if equity DD > 5% from peak

def check_daemon():
    try:
        result = subprocess.run(
            ['launchctl', 'list'], capture_output=True, text=True, timeout=10
        )
        lines = result.stdout.split('\n')
        for line in lines:
            if DAEMON_NAME in line:
                parts = line.split('\t')
                pid = parts[0].strip()
                status = parts[1].strip()
                return {'found': True, 'pid': pid, 'last_exit': status}
        return {'found': False}
    except Exception as e:
        return {'error': str(e)}

def check_state():
    if not STATE_PATH.exists():
        return {'error': 'state file missing'}
    try:
        d = json.load(open(STATE_PATH))
    except Exception as e:
        return {'error': f'cannot parse state: {e}'}

    snapshots = d.get('snapshots', [])
    if not snapshots:
        return {'state': d, 'no_snapshots': True}

    # Parse last snapshot time
    last = snapshots[-1]
    last_time_str = last.get('snapshot_time', '')
    try:
        last_dt = datetime.strptime(last_time_str, "%Y-%m-%d %H:%M JST")
        last_dt = last_dt.replace(tzinfo=timezone(timedelta(hours=9)))
        now = datetime.now(timezone(timedelta(hours=9)))
        hours_since = (now - last_dt).total_seconds() / 3600
    except Exception:
        hours_since = 999

    # Equity stats
    equities = [s.get('equity_usd', 0) for s in snapshots]
    initial = d.get('initial_capital_usd', 10000)
    current = d.get('equity_usd', initial)
    peak = max(equities) if equities else initial
    dd_pct = (current / peak - 1) * 100 if peak > 0 else 0.0
    total_pct = (current / initial - 1) * 100

    # Signal activity (last 10 snapshots)
    recent = snapshots[-10:]
    axes_total = {}
    for s in recent:
        for axis, n in (s.get('axes_signals') or {}).items():
            axes_total[axis] = axes_total.get(axis, 0) + n

    return {
        'strategy': d.get('strategy', 'N/A'),
        'leverage': d.get('leverage', 0),
        'initial_usd': initial,
        'current_usd': current,
        'total_return_pct': total_pct,
        'dd_from_peak_pct': dd_pct,
        'peak_usd': peak,
        'snapshots_count': len(snapshots),
        'closed_trades': len(d.get('closed_trades', [])),
        'open_positions': len(d.get('open_positions', [])),
        'last_snapshot_time': last_time_str,
        'hours_since_last_snap': hours_since,
        'recent_signal_activity': axes_total,
    }


def alert(msg, level='WARN'):
    """Output formatted alert."""
    print(f"[{level}] {datetime.now().isoformat()}: {msg}")


def main():
    print(f"=== v4 daemon health check {datetime.now().isoformat()} ===\n")

    # Daemon check
    daemon = check_daemon()
    print("Daemon (launchctl):")
    if daemon.get('error'):
        alert(f"launchctl error: {daemon['error']}", 'ERROR')
    elif daemon.get('found'):
        print(f"  ✓ {DAEMON_NAME} registered (last exit {daemon['last_exit']})")
    else:
        alert(f"{DAEMON_NAME} NOT registered in launchctl", 'ERROR')

    # State check
    state = check_state()
    print("\nPaper trade state:")
    if state.get('error'):
        alert(state['error'], 'ERROR')
        return

    print(f"  Strategy: {state['strategy']}")
    print(f"  Lev: {state['leverage']}x")
    print(f"  Equity: ${state['current_usd']:.2f} (init ${state['initial_usd']:.0f})")
    print(f"  Total: {state['total_return_pct']:+.2f}%")
    print(f"  Peak: ${state['peak_usd']:.2f}, DD: {state['dd_from_peak_pct']:+.2f}%")
    print(f"  Snapshots: {state['snapshots_count']},  Closed: {state['closed_trades']},  Open: {state['open_positions']}")
    print(f"  Last snap: {state['last_snapshot_time']} ({state['hours_since_last_snap']:.1f}h ago)")
    print(f"  Recent activity (last 10 snaps): {state['recent_signal_activity']}")

    # Alerts
    if state['hours_since_last_snap'] > SILENT_THRESHOLD_HOURS:
        alert(f"Daemon silent {state['hours_since_last_snap']:.1f}h (> {SILENT_THRESHOLD_HOURS}h)", 'ERROR')

    if state['dd_from_peak_pct'] < DD_THRESHOLD_PCT:
        alert(f"Equity DD {state['dd_from_peak_pct']:.1f}% < threshold {DD_THRESHOLD_PCT}%", 'ERROR')

    total_recent_sigs = sum(state['recent_signal_activity'].values()) if state['recent_signal_activity'] else 0
    if state['snapshots_count'] > 30 and total_recent_sigs == 0:
        alert("No signals in last 10 snapshots — strategy may be in flat regime", 'INFO')

    print(f"\n=== End check ===")


if __name__ == '__main__':
    main()
