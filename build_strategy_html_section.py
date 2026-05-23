"""Wave J19 — Build HTML section with detailed strategy cards.

Reads strategy_cards_data.json, generates an HTML block with:
  - Per-strategy header card (Sharpe/Return/DD/Calmar/etc)
  - Plotly equity curve
  - Plotly drawdown chart
  - Plotly rolling 90d Sharpe
  - Monthly returns table

Output: writes the HTML block to a file that we paste into report.html.
"""
import json
from pathlib import Path

DATA = json.loads(Path("/Users/nekonaomichi/crypto-lab/strategy_cards_data.json").read_text())


def gen_card(strat_key, color="--accent-green"):
    s = DATA["stats"][strat_key]
    eq_curve = DATA["equity_curves"][strat_key]
    dd_curve = DATA["drawdowns"][strat_key]

    # Build monthly table
    monthly = s["monthly_returns"]
    monthly_html = "<table class='data-table' style='width:100%;font-size:0.78rem;margin-top:8px;'>\n<thead><tr>"
    monthly_html += "<th>月</th><th>リターン</th>" * 4 + "</tr></thead><tbody>"
    # Layout in 4-column rows
    for i in range(0, len(monthly), 4):
        row = monthly[i:i+4]
        cells = ""
        for m, r in row:
            color = "var(--accent-green)" if r > 0 else "var(--accent-red)"
            cells += f"<td>{m}</td><td style='color:{color};'>{r:+.2f}%</td>"
        # pad to 4
        for _ in range(4 - len(row)):
            cells += "<td></td><td></td>"
        monthly_html += f"<tr>{cells}</tr>"
    monthly_html += "</tbody></table>"

    # Equity curve data
    eq_dates = [p["date"] for p in eq_curve]
    eq_vals = [p["value"] for p in eq_curve]

    chart_id = f"sc-{strat_key}"
    eq_chart_id = f"{chart_id}-eq"
    dd_chart_id = f"{chart_id}-dd"
    rs_chart_id = f"{chart_id}-rs"

    rolling_sh = s["rolling_sharpe_90d"]

    js = f"""
<script>
Plotly.newPlot('{eq_chart_id}', [{{
  x: {json.dumps(eq_dates)},
  y: {json.dumps([round(v, 4) for v in eq_vals])},
  mode: 'lines', line: {{color: '#3fb950', width: 2.5}}, name: 'Equity'
}}], {{
  paper_bgcolor: '#0d1117', plot_bgcolor: '#161b22', font: {{color: '#e6edf3', size: 11}},
  xaxis: {{title: 'Date', gridcolor: '#30363d'}},
  yaxis: {{title: 'Equity (1 = starting)', gridcolor: '#30363d', tickformat: '.2f'}},
  margin: {{t: 20, l: 60, r: 30, b: 50}}, height: 280
}}, {{responsive: true, displayModeBar: false}});

Plotly.newPlot('{dd_chart_id}', [{{
  x: {json.dumps(eq_dates)},
  y: {json.dumps([round(d * 100, 3) for d in dd_curve])},
  mode: 'lines', line: {{color: '#f85149', width: 1.5}}, fill: 'tozeroy',
  fillcolor: 'rgba(248,81,73,0.15)', name: 'DD'
}}], {{
  paper_bgcolor: '#0d1117', plot_bgcolor: '#161b22', font: {{color: '#e6edf3', size: 11}},
  xaxis: {{title: 'Date', gridcolor: '#30363d'}},
  yaxis: {{title: 'Drawdown (%)', gridcolor: '#30363d', tickformat: '.1f'}},
  margin: {{t: 20, l: 60, r: 30, b: 50}}, height: 220
}}, {{responsive: true, displayModeBar: false}});

Plotly.newPlot('{rs_chart_id}', [{{
  x: {json.dumps(eq_dates[:len(rolling_sh)])},
  y: {json.dumps([(v if v is not None else None) for v in rolling_sh])},
  mode: 'lines', line: {{color: '#58a6ff', width: 2}}, name: 'Rolling 90d Sharpe',
  connectgaps: false
}}], {{
  paper_bgcolor: '#0d1117', plot_bgcolor: '#161b22', font: {{color: '#e6edf3', size: 11}},
  xaxis: {{title: 'Date', gridcolor: '#30363d'}},
  yaxis: {{title: '90d Sharpe (annualized)', gridcolor: '#30363d', tickformat: '.1f', zeroline: true, zerolinecolor: '#888'}},
  margin: {{t: 20, l: 60, r: 30, b: 50}}, height: 220,
  shapes: [{{type: 'line', xref: 'paper', x0: 0, x1: 1, y0: 2, y1: 2, line: {{color: 'rgba(63,185,80,0.3)', dash: 'dash'}}}}]
}}, {{responsive: true, displayModeBar: false}});
</script>
"""

    # Header metrics
    metrics = f"""
<table class='data-table' style='width:100%;font-size:0.85rem;'>
  <thead><tr><th>メトリクス</th><th>値</th><th>メトリクス</th><th>値</th></tr></thead>
  <tbody>
    <tr><td>累計リターン (730d)</td><td><strong>{s['total_return_pct']:+.1f}%</strong></td>
        <td>Sharpe (年率)</td><td><strong>{s['sharpe']:+.2f}</strong></td></tr>
    <tr><td>最大DD</td><td><strong>{s['max_dd_pct']:+.1f}%</strong></td>
        <td>Calmar</td><td><strong>{s['calmar']:.2f}</strong></td></tr>
    <tr><td>日次プラス率</td><td>{s['win_rate_pct']:.1f}%</td>
        <td>観測日数</td><td>{s['n_days']}</td></tr>
    <tr><td>Rolling 90d Sh (平均)</td><td>{s['rolling_sh_mean']:+.2f}</td>
        <td>Rolling 90d Sh (Range)</td><td>[{s['rolling_sh_min']:+.2f}, {s['rolling_sh_max']:+.2f}]</td></tr>
  </tbody>
</table>
"""

    return f"""
<div class='card' style='border-left:4px solid var({color});'>
  <h3 style='color:var({color});'>📊 {s['name']}</h3>
  {metrics}

  <h4 style='margin-top:14px;'>エクイティ推移 (初期=1.0)</h4>
  <div id='{eq_chart_id}' style='width:100%;'></div>

  <h4 style='margin-top:10px;'>ドローダウン</h4>
  <div id='{dd_chart_id}' style='width:100%;'></div>

  <h4 style='margin-top:10px;'>ローリング90日 Sharpe (年率換算)</h4>
  <div id='{rs_chart_id}' style='width:100%;'></div>
  <p style='font-size:0.82rem;color:var(--text-secondary);margin-top:4px;'>
    破線は Sh=+2.0 の目安。安定して +2 以上を維持できれば真のエッジの強い証拠。
  </p>

  <h4 style='margin-top:12px;'>月次リターン</h4>
  {monthly_html}

  {js}
</div>
"""


def build_section():
    html = """
  <!-- ==================== STRATEGY DETAILS (Wave J19) ==================== -->
  <section class="section" id="strategy-details">
    <div class="section-header">
      <div><span class="section-num">02</span><span class="jp-title">主要戦略の詳細解析</span></div>
      <div class="en-subtitle">Strategy Deep Dive (Wave J19, 2026-05-24)</div>
    </div>

    <div class="card info">
      <p style="font-size:0.9rem;">
        以下、現在の最良ポートフォリオ <strong>50/50合成</strong> と、その構成要素 <strong>ATR×8+vol_z</strong> および <strong>FOPD×6</strong> の各カード。
        各エクイティカーブ・DD・ローリング90日Sharpe・月次リターン を表示。
        日次プラス率が低い (10-22%) のは <strong>多くの日でシグナル発火がない (=リターン0)</strong> ためで、戦略の「ヒット率」とは異なる (発火時のヒット率は別)。
      </p>
    </div>
"""
    # Combined first (most important)
    html += gen_card("combined", "--accent-green")
    html += gen_card("atr", "--accent-cyan")
    html += gen_card("fopd", "--accent-orange")
    html += """
  </section>
  <hr class="divider">
"""
    return html


if __name__ == "__main__":
    section_html = build_section()
    Path("/Users/nekonaomichi/crypto-lab/_strategy_section.html").write_text(section_html)
    print(f"Wrote _strategy_section.html ({len(section_html)} chars)")
