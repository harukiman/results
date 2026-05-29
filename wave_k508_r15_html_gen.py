#!/usr/bin/env python3
"""
Wave K508 R15 — HTML Generation for External Findings
Generates pagination-style HTML matching R12-R14 pattern
"""

import json
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path("/Users/nekonaomichi/crypto-lab")

def generate_html(findings: list, assignments: dict) -> str:
    """Generate HTML for R15 findings"""

    # Count findings by actionable status
    actionable_count = sum(1 for f in findings if f.get("actionable"))
    high_count = sum(1 for f in findings if f.get("actionable") and f.get("actionable_score", 0) >= 4)

    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S JST")

    html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>External Findings Round 15 — Wave K508</title>
<style>
  :root {{
    --bg: #0d0d0f;
    --surface: #161618;
    --surface2: #1e1e22;
    --border: #2a2a30;
    --accent: #7c6ff7;
    --accent2: #4ecdc4;
    --accent3: #f7b731;
    --text: #e8e8f0;
    --muted: #8888a0;
    --green: #4caf50;
    --red: #ef5350;
    --tag-bg: #252530;
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    background: var(--bg);
    color: var(--text);
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    font-size: 14px;
    line-height: 1.6;
  }}
  .header {{
    background: linear-gradient(135deg, #1a1040 0%, #0d1a30 100%);
    border-bottom: 2px solid var(--accent);
    padding: 24px 20px 20px;
  }}
  .header h1 {{
    font-size: clamp(18px, 4vw, 26px);
    color: var(--accent);
    letter-spacing: 0.5px;
    margin-bottom: 6px;
  }}
  .header .meta {{
    color: var(--muted);
    font-size: 12px;
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
    align-items: center;
  }}
  .badge {{
    background: var(--tag-bg);
    border: 1px solid var(--border);
    border-radius: 4px;
    padding: 2px 8px;
    font-size: 11px;
    font-weight: 600;
    color: var(--accent2);
  }}
  .update-time {{
    color: var(--accent3);
    font-weight: 700;
    font-size: 13px;
  }}

  .summary-bar {{
    background: var(--surface);
    border-bottom: 1px solid var(--border);
    padding: 12px 20px;
    display: flex;
    flex-wrap: wrap;
    gap: 16px;
    align-items: center;
  }}
  .stat {{
    display: flex;
    flex-direction: column;
    align-items: center;
    min-width: 80px;
  }}
  .stat-value {{
    font-size: 22px;
    font-weight: 700;
    color: var(--accent);
  }}
  .stat-label {{ font-size: 10px; color: var(--muted); text-transform: uppercase; letter-spacing: 0.5px; }}

  .top3-section {{
    background: linear-gradient(135deg, #1a1228 0%, #121a24 100%);
    border: 1px solid var(--accent);
    border-radius: 8px;
    margin: 16px 20px;
    padding: 16px;
  }}
  .top3-section h2 {{
    color: var(--accent3);
    font-size: 14px;
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-bottom: 12px;
  }}
  .top3-item {{
    background: var(--tag-bg);
    border-left: 3px solid var(--accent3);
    border-radius: 4px;
    padding: 10px 12px;
    margin-bottom: 8px;
  }}
  .top3-item .top3-id {{ color: var(--accent3); font-weight: 700; font-size: 12px; }}
  .top3-item .top3-title {{ color: var(--text); font-weight: 600; margin: 2px 0; }}
  .top3-item .top3-note {{ color: var(--muted); font-size: 12px; margin-top: 4px; }}

  .cards {{
    padding: 16px 20px;
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
    gap: 14px;
  }}
  @media (max-width: 600px) {{
    .cards {{ grid-template-columns: 1fr; padding: 10px; }}
  }}

  .card {{
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 14px;
    transition: border-color 0.2s;
  }}
  .card:hover {{ border-color: var(--accent); }}
  .card.actionable {{ border-left: 3px solid var(--accent3); }}

  .card-header {{
    display: flex;
    align-items: flex-start;
    gap: 8px;
    margin-bottom: 8px;
  }}
  .card-id {{
    background: var(--accent);
    color: #fff;
    font-size: 10px;
    font-weight: 700;
    padding: 2px 6px;
    border-radius: 3px;
    flex-shrink: 0;
    margin-top: 2px;
  }}
  .card-id.actionable {{ background: var(--accent3); color: #000; }}
  .card-title {{
    font-size: 13px;
    font-weight: 600;
    color: var(--text);
    line-height: 1.4;
  }}
  .card-title a {{
    color: inherit;
    text-decoration: none;
  }}
  .card-title a:hover {{ color: var(--accent2); }}

  .card-tags {{
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
    margin-bottom: 8px;
  }}
  .tag {{
    font-size: 10px;
    padding: 2px 6px;
    border-radius: 3px;
    background: var(--tag-bg);
    color: var(--muted);
    border: 1px solid var(--border);
  }}
  .tag.verified {{ background: rgba(76, 175, 80, 0.15); color: var(--green); border-color: var(--green); }}
  .tag.partial {{ background: rgba(247, 183, 49, 0.15); color: var(--accent3); border-color: var(--accent3); }}

  .card-summary {{
    font-size: 12px;
    color: var(--muted);
    margin-bottom: 8px;
    line-height: 1.5;
  }}

  .card-footer {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 11px;
    color: var(--muted);
  }}

  .profit-badge {{
    background: rgba(76, 175, 80, 0.2);
    color: var(--green);
    padding: 2px 6px;
    border-radius: 3px;
    font-weight: 600;
  }}

  .footer {{
    padding: 20px;
    text-align: center;
    color: var(--muted);
    font-size: 12px;
    border-top: 1px solid var(--border);
  }}
</style>
</head>
<body>

<div class="header">
  <h1>External Findings Round 15</h1>
  <div class="meta">
    <span class="badge">Wave K508</span>
    <span class="badge">May 2026</span>
    <span class="update-time">{ts}</span>
  </div>
</div>

<div class="summary-bar">
  <div class="stat">
    <div class="stat-value">{len(findings)}</div>
    <div class="stat-label">Total Findings</div>
  </div>
  <div class="stat">
    <div class="stat-value">{high_count}</div>
    <div class="stat-label">HIGH Score</div>
  </div>
  <div class="stat">
    <div class="stat-value">{actionable_count}</div>
    <div class="stat-label">Actionable</div>
  </div>
</div>

<div class="top3-section">
  <h2>Top 3 HIGH Actionable</h2>
"""

    for idx, item in enumerate(assignments.get("top_3_high", [])[:3], 1):
        profit_str = f"${item.get('profit_mid', 0):,.0f}/yr" if item.get('profit_mid') else "~"
        html += f"""  <div class="top3-item">
    <div class="top3-id">#{idx} {item['id']}</div>
    <div class="top3-title">{item['title']}</div>
    <div class="top3-note">Score: {item['score']} | Profit: {profit_str}</div>
  </div>
"""

    html += """</div>

<div class="cards">
"""

    for finding in sorted(findings, key=lambda x: (not x.get("actionable"), -x.get("actionable_score", 0))):
        actionable_class = "actionable" if finding.get("actionable") else ""
        id_class = "actionable" if finding.get("actionable") else ""

        # Verification strength tag
        verify_strength = finding.get("verification_strength", "UNVERIFIED")
        if "STRICT" in verify_strength:
            verify_tag = '<span class="tag verified">✓ VERIFIED</span>'
        elif "PARTIAL" in verify_strength:
            verify_tag = '<span class="tag partial">◐ PARTIAL</span>'
        else:
            verify_tag = '<span class="tag">? UNVERIFIED</span>'

        # Profit estimate
        profit_mid = finding.get("profit_impact_usdc_yr", {}).get("mid", 0)
        profit_display = f"${profit_mid:,.0f}/yr" if profit_mid > 0 else ("Indirect" if profit_mid == 0 else "Risk")

        # Summary (first 100 chars)
        summary = finding.get("summary_ja", "")[:100] + "..."

        html += f"""  <div class="card {actionable_class}">
    <div class="card-header">
      <div class="card-id {id_class}">{finding['id']}</div>
      <div style="flex: 1;">
        <div class="card-title"><a href="{finding.get('url', '#')}" target="_blank">{finding['title']}</a></div>
      </div>
    </div>
    <div class="card-tags">
      {verify_tag}
      <span class="tag">{finding.get('source_quality', 'UNKNOWN')}</span>
      <span class="tag">{finding.get('date', '?')}</span>
    </div>
    <div class="card-summary">{summary}</div>
    <div class="card-footer">
      <span>Focus: {finding.get('focus_area', '?')}</span>
      <span class="profit-badge">{profit_display}</span>
    </div>
  </div>
"""

    html += """</div>

<div class="footer">
  Generated by Wave K508 R15 Scraper | Crypto-Lab External Research Pipeline
</div>

</body>
</html>
"""

    return html


def main():
    # Load findings from JSON
    json_path = REPO_ROOT / "external_findings_round15.json"
    with open(json_path) as f:
        findings = json.load(f)

    # Determine top 3
    high_actionable = [f for f in findings if f.get("actionable") and f.get("actionable_score", 0) >= 4]
    high_actionable_sorted = sorted(high_actionable, key=lambda x: (x.get("actionable_score", 0), x.get("profit_impact_usdc_yr", {}).get("high", 0)), reverse=True)

    assignments = {
        "top_3_high": [{"id": f["id"], "title": f["title"], "score": f.get("actionable_score"), "profit_mid": f.get("profit_impact_usdc_yr", {}).get("mid")} for f in high_actionable_sorted[:3]],
    }

    # Generate HTML
    html = generate_html(findings, assignments)

    # Save HTML
    html_path = REPO_ROOT / "external_findings_round15.html"
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"HTML generated: {html_path}")
    return findings, assignments


if __name__ == "__main__":
    findings, assignments = main()
