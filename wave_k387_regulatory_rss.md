# Wave K387: SEC/CFTC RSS Regulatory Monitor Daemon Scaffold

**Date:** 2026-05-27  
**Status:** COMPLETE  
**Scope:** K385 regulatory-conservative strategy, K386 BEAR_1 fallback trigger support  

---

## Task Summary

Scaffold a lightweight daemon for monitoring SEC and CFTC official RSS feeds, searching for keywords related to HyperLiquid, HIP-3, perpetuals, and market manipulation concerns. This feeds manual operator review for potential K386 BEAR_1 fallback activation.

**Key constraint:** K387 does NOT automatically trigger any flag. All decisions are manual.

---

## Deliverables

### 1. Script: `scripts/regulatory_rss_monitor.py`
- **Lines:** ~280 LOC (single-file, stdlib only)
- **Execution:** Single-shot, 30min via launchd
- **Feeds:** SEC (news.pressreleases.rss) + CFTC (PressReleases.xml)
- **Keywords:** `hyperliquid`, `hip-3`, `perpetual`, `tokenized`, `manipulation`, `defi dex` (case-insensitive)
- **Outputs:**
  - `cache/regulatory_alerts_seen.txt` — Track seen GUIDs (avoid duplicates)
  - `cache/regulatory_alerts.jsonl` — Timestamped alert log (one per line)
  - `data/regulatory_dashboard.json` — Live dashboard JSON (24h counts, recent alerts)
  - `logs/regulatory_rss_monitor.log/.err` — plist-controlled logging
- **Error handling:** Catch all exceptions, write to .err, exit 0

### 2. Plist: `com.cryptolab.regulatory-rss.plist`
- **Label:** `com.cryptolab.regulatory-rss`
- **StartInterval:** 1800 (30min polling)
- **RunAtLoad:** false (per K310 security rule)
- **Logging:** Absolute paths to logs/ directory
- **Status:** Gitignored, in repo root, ready for manual activation

### 3. Registry Update: `scripts/verify_deployment_status.py`
- Added DaemonSpec for K387:
  - Label: `com.cryptolab.regulatory-rss`
  - Expected status: `SCAFFOLD-READY`
  - Purpose: SEC/CFTC RSS monitoring (30min polling, manual review)

### 4. HTML Dashboard Update: `report.html`
- Added K387 row to Daemon Status table
- Added "Regulatory Alerts Monitor" card with:
  - 24h alert counts (SEC, CFTC)
  - New alerts this poll
  - Recent 5 alerts with keyword matches
  - Live fetch timestamp (JST)
- Responsive grid layout, mobile-friendly

### 5. Runbook Update: `docs/k302a_runbook.md`
- Added **§19 K387 Regulatory Alerts — Manual Review & BEAR_1 Trigger** (1,200+ lines)
- Covers:
  - Daemon overview & activation
  - Feed structure & keywords
  - Manual review workflow
  - BEAR_1 fallback activation (manual flag creation)
  - Dashboard access patterns
  - No auto-trigger policy (compliance)
  - Deactivation procedure

---

## Verification

### Phase 5: Test Dry-Run ✅
```bash
$ python3 scripts/regulatory_rss_monitor.py
# No output (expected), exit 0

$ ls -lh cache/regulatory_alerts* data/regulatory_dashboard.json
-rw-r--r--  924B  5月 27 10:09 cache/regulatory_alerts_seen.txt
-rw-r--r--  184B  5月 27 10:09 data/regulatory_dashboard.json

$ cat data/regulatory_dashboard.json
{
  "last_poll_jst": "2026-05-27T10:09:57.748539+09:00",
  "sec_alerts_24h": 0,
  "cftc_alerts_24h": 0,
  "new_alerts_this_poll": 0,
  "recent_alerts": [],
  "next_action": "monitor"
}
```

### Phase 5: Deployment Status ✅
```bash
$ python3 scripts/verify_deployment_status.py 2>&1 | tail -5
  com.cryptolab.regulatory-rss             SCAFFOLD-READY       (html claims: SCAFFOLD-READY) pid=None plist=N
--- summary: {'active': 0, 'loaded': 0, 'pending_activation': 3, 'scaffold_ready': 7, 'unknown': 1, 'mismatches_with_html': 0} ---
--- json saved: /Users/nekonaomichi/crypto-lab/deployment_status.json ---

# 0 mismatches ✅
```

---

## Implementation Notes

### K339 Security Pattern
- REPO_ROOT: `Path(__file__).resolve().parent.parent`
- All paths absolute, no hardcoded `/Users/nekonaomichi`
- Plist paths also absolute for launchd safety

### Stdlib Only
- `xml.etree.ElementTree` for RSS/XML parsing
- `urllib.request/urllib.error` for HTTP
- `json`, `datetime`, `pathlib` (standard library)
- No external dependencies

### Error Handling
- All RSS fetch errors logged to `.err`, no crash
- Parse errors caught, continue to next feed
- Exit always 0 per task spec

### Feed Format Support
- Both RSS (`<item>`) and Atom (`<entry>`) handled
- `<link>` with text or `href` attribute supported
- `pubDate` and `published` elements recognized

### Cache Strategy
- Seen GUIDs stored as newline-separated text (fast, simple)
- JSONL alerts append-only, preserving history
- Dashboard JSON overwrites (small, ~200 bytes)

---

## Next Steps (Future Waves)

1. **K388:** Test K387 with live SEC/CFTC feed polling for 7 days
2. **K389:** Add ntfy.sh integration for push alerts
3. **K390:** Build operator UI for manual BEAR_1 trigger acknowledgment
4. **K391:** Historical alert analytics (patterns, false positives)
5. **K392:** Integration with other regulatory data sources (Reuters, Bloomberg)

---

## Constraints & Compliance

- **No auto-trigger:** K387 does not create any flag file or modify daemon state
- **Manual review mandatory:** Operator must read SEC/CFTC document before BEAR_1 activation
- **BEAR_1 activation:** User creates `BEAR_1_FALLBACK_ACTIVE.flag` manually (§19.5 runbook)
- **Regulatory-conservative:** Per K385 design, maintains human-in-loop for all critical decisions
- **Status:** SCAFFOLD-READY, awaiting manual plist activation

---

*K387 Regulatory RSS Monitor Daemon Scaffold — Complete*
