#!/usr/bin/env python3
"""K387 SEC/CFTC RSS monitor daemon - lightweight regulatory alert polling.

Single-shot 30min cron (launchd StartInterval=1800).
- Fetch SEC + CFTC official RSS feeds
- Track seen alerts via JSONL + seen.txt cache
- Match keywords: HyperLiquid, HIP-3, perpetual, tokenized, manipulation, DeFi DEX, Clarity Act, etc.
- Output alerts to ntfy.sh + HTML dashboard (no auto-trigger)
- Error handling: catch all, write to .err, exit 0

K387 requirements:
- REPO_ROOT via K339 pattern
- Stdlib only (xml.etree.ElementTree)
- Cache files: regulatory_alerts_seen.txt, regulatory_alerts.jsonl
- Dashboard: data/regulatory_dashboard.json
- Manual review trigger only (no BEAR_1/K386 auto-flag)
"""
from __future__ import annotations

import json
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional
from xml.etree import ElementTree as ET

REPO_ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = REPO_ROOT / "cache"
DATA_DIR = REPO_ROOT / "data"
LOGS_DIR = REPO_ROOT / "logs"

SEEN_FILE = CACHE_DIR / "regulatory_alerts_seen.txt"
ALERTS_JSONL = CACHE_DIR / "regulatory_alerts.jsonl"
DASHBOARD_JSON = DATA_DIR / "regulatory_dashboard.json"
LOG_FILE = LOGS_DIR / "regulatory_rss_monitor.log"
ERR_FILE = LOGS_DIR / "regulatory_rss_monitor.err"

JST = timezone(timedelta(hours=9))

# RSS feeds
FEEDS = {
    "SEC": "https://www.sec.gov/news/pressreleases.rss",
    "CFTC": "https://www.cftc.gov/PressRoom/PressReleases.xml",
}

# Keywords (case-insensitive)
KEYWORDS = [
    "hyperliquid",
    "hip-3",
    "perpetual",
    "tokenized",
    "manipulation",
    "defi dex",
    "clarity act",
    "digital asset market clarity act",
    "h.r.3633",
    "senate floor",
    "crypto market structure",
    "defi exemption",
    "cftc market authority",
    "variational trading api",   # K443: trigger for K297'' Variational activation (Q3-Q4 2026)
    "variational finance",       # K443: Variational protocol news
]


def log_err(msg: str) -> None:
    """Write to stderr log file."""
    try:
        ERR_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(ERR_FILE, "a") as f:
            ts = datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S JST")
            f.write(f"[{ts}] {msg}\n")
    except Exception as e:
        print(f"Failed to write error log: {e}", file=sys.stderr)


def load_seen() -> set:
    """Load previously seen alert GUIDs."""
    if not SEEN_FILE.exists():
        return set()
    try:
        return set(SEEN_FILE.read_text().strip().split("\n"))
    except Exception as e:
        log_err(f"Failed to load seen cache: {e}")
        return set()


def save_seen(guids: set) -> None:
    """Save seen GUIDs to cache."""
    try:
        SEEN_FILE.parent.mkdir(parents=True, exist_ok=True)
        SEEN_FILE.write_text("\n".join(sorted(guids)))
    except Exception as e:
        log_err(f"Failed to save seen cache: {e}")


def fetch_feed(url: str, source: str) -> list:
    """Fetch and parse RSS/XML feed. Returns list of {title, link, pubDate, guid}."""
    items = []
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            content = response.read()
        root = ET.fromstring(content)

        # Handle both RSS and Atom-style feeds
        for item in root.findall(".//item") + root.findall(".//entry"):
            title_elem = item.find("title")
            link_elem = item.find("link")
            pubdate_elem = item.find("pubDate")
            guid_elem = item.find("guid")

            # Atom feeds use href attribute on link
            link = None
            if link_elem is not None:
                if link_elem.text:
                    link = link_elem.text
                elif link_elem.get("href"):
                    link = link_elem.get("href")

            # Atom uses published, RSS uses pubDate
            pubdate = None
            if pubdate_elem is not None and pubdate_elem.text:
                pubdate = pubdate_elem.text
            else:
                pub_elem = item.find("published")
                if pub_elem is not None and pub_elem.text:
                    pubdate = pub_elem.text

            # Generate deterministic GUID if missing
            guid = None
            if guid_elem is not None and guid_elem.text:
                guid = guid_elem.text
            elif link:
                guid = link
            elif title_elem is not None and title_elem.text:
                guid = f"{source}:{title_elem.text}:{pubdate or 'unknown'}"

            if title_elem is not None and guid:
                items.append(
                    {
                        "source": source,
                        "title": title_elem.text or "(no title)",
                        "link": link or "",
                        "pubDate": pubdate or "",
                        "guid": guid,
                    }
                )
    except urllib.error.URLError as e:
        log_err(f"Failed to fetch {source} feed: {e}")
    except ET.ParseError as e:
        log_err(f"Failed to parse {source} feed XML: {e}")
    except Exception as e:
        log_err(f"Unexpected error fetching {source}: {e}")

    return items


def matches_keyword(text: str) -> Optional[str]:
    """Check if text matches any keyword. Return matched keyword or None."""
    text_lower = text.lower()
    for kw in KEYWORDS:
        if kw in text_lower:
            return kw
    return None


def process_feeds() -> list:
    """Fetch all feeds and return new alerts matching keywords."""
    seen = load_seen()
    new_alerts = []

    for source, url in FEEDS.items():
        items = fetch_feed(url, source)
        for item in items:
            guid = item["guid"]
            if guid in seen:
                continue

            # Check title + description for keywords
            matched_kw = matches_keyword(item["title"])
            if not matched_kw:
                # Check link/description if available
                matched_kw = matches_keyword(item.get("link", ""))

            if matched_kw:
                alert = {
                    "timestamp_jst": datetime.now(JST).isoformat(),
                    "source": source,
                    "title": item["title"],
                    "link": item["link"],
                    "pubDate": item["pubDate"],
                    "guid": guid,
                    "keyword_matched": matched_kw,
                }
                new_alerts.append(alert)
                seen.add(guid)

            # Always mark as seen (even non-matching items)
            seen.add(guid)

    save_seen(seen)
    return new_alerts


def write_alerts_jsonl(alerts: list) -> None:
    """Append new alerts to JSONL file."""
    if not alerts:
        return
    try:
        ALERTS_JSONL.parent.mkdir(parents=True, exist_ok=True)
        with open(ALERTS_JSONL, "a") as f:
            for alert in alerts:
                f.write(json.dumps(alert) + "\n")
    except Exception as e:
        log_err(f"Failed to write JSONL: {e}")


def load_recent_alerts(limit: int = 10) -> list:
    """Load recent alerts from JSONL (last N lines)."""
    if not ALERTS_JSONL.exists():
        return []
    try:
        lines = ALERTS_JSONL.read_text().strip().split("\n")
        alerts = []
        for line in lines[-limit:]:
            if line.strip():
                try:
                    alerts.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
        return alerts
    except Exception as e:
        log_err(f"Failed to load recent alerts: {e}")
        return []


def count_alerts_24h() -> tuple:
    """Count alerts from last 24h by source (SEC, CFTC)."""
    if not ALERTS_JSONL.exists():
        return 0, 0

    now = datetime.now(JST)
    cutoff = now - timedelta(hours=24)
    sec_count = 0
    cftc_count = 0

    try:
        for line in ALERTS_JSONL.read_text().strip().split("\n"):
            if not line.strip():
                continue
            try:
                alert = json.loads(line)
                ts = datetime.fromisoformat(alert["timestamp_jst"])
                if ts > cutoff:
                    if alert["source"] == "SEC":
                        sec_count += 1
                    elif alert["source"] == "CFTC":
                        cftc_count += 1
            except (json.JSONDecodeError, ValueError):
                pass
    except Exception as e:
        log_err(f"Failed to count alerts: {e}")

    return sec_count, cftc_count


def update_dashboard(alerts: list) -> None:
    """Update regulatory_dashboard.json with latest poll summary."""
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)

        sec_24h, cftc_24h = count_alerts_24h()
        recent = load_recent_alerts(10)

        dashboard = {
            "last_poll_jst": datetime.now(JST).isoformat(),
            "sec_alerts_24h": sec_24h,
            "cftc_alerts_24h": cftc_24h,
            "new_alerts_this_poll": len(alerts),
            "recent_alerts": recent,
            "next_action": "monitor",  # Always "monitor" unless user flags BEAR_1
        }

        DASHBOARD_JSON.write_text(json.dumps(dashboard, indent=2, ensure_ascii=False))
    except Exception as e:
        log_err(f"Failed to update dashboard: {e}")


def post_ntfy(alerts: list) -> None:
    """Optional: POST alert summary to ntfy.sh (disabled by default)."""
    if not alerts:
        return

    # Disabled for now per K387 spec (manual review only)
    # Placeholder for future integration
    pass


def main() -> int:
    """Single-shot RSS poll."""
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        LOGS_DIR.mkdir(parents=True, exist_ok=True)

        # Fetch and process
        alerts = process_feeds()

        # Write JSONL
        write_alerts_jsonl(alerts)

        # Update dashboard
        update_dashboard(alerts)

        # Optional: ntfy.sh (disabled)
        # post_ntfy(alerts)

        return 0

    except Exception as e:
        log_err(f"Unexpected error in main: {e}")
        return 0  # Exit 0 per spec (catch all)


if __name__ == "__main__":
    sys.exit(main())
