# Wave K329 — HTML Audit #6
## report.html Integrity Check (K300-K326 era)
**Auditor**: K329 Subagent  
**Date**: 2026-05-25 14:46 JST  
**File**: `/Users/nekonaomichi/crypto-lab/report.html`  
**File stats**: 8919 lines, 952,608 bytes (~930 KB)  
**Public URL**: https://harukiman.github.io/results/report.html  
**Prior audits**: #1-5 (last ~K293-K300)

---

## Executive Summary

The report is in generally good shape following K310's ground-truth correction of daemon badges. Seven findings require attention in K330+: two HIGH (footer still claims v6.11; K287d "← 現在" arrow points to superseded production), three MED (header meta timestamp lag, --border-color undefined CSS variable, K320/K323 in-flight never resolved), and two LOW (mobile TOC missing 6 sections, bare Plotly.newPlot calls risk silent fails). No duplicate K-number contradictions found. All critical numbers (Sh 32.59, 98.7%, 16.30, 18.46, 10.17) are internally consistent.

---

## Focus Area 1: Banner & Header Integrity

### Finding 1.1 — LOW: Header meta timestamp lags banner by 9 hours
**Severity**: LOW  
**Line**: 772  
**Evidence**:
```html
v4.1 (Sh +4.08) | Updated: 2026-05-25 05:30 JST | Project: crypto-lab
```
The top banner (line 762) correctly reads `2026-05-25 14:37 JST`, but the `<div class="meta">` inside `<header class="report-header">` still says `05:30 JST`. This creates a secondary timestamp that is 9 hours behind the authoritative banner timestamp.

**Recommended fix**: Update line 772 to match `2026-05-25 14:37 JST`, or remove the duplicate timestamp from the header meta div.  
**Effort**: 5 min

---

### Finding 1.2 — PASS: Banner timestamp current
**Line**: 762  
`2026-05-25 14:37 JST` — matches the task description's expected value. PASS.

---

### Finding 1.3 — PASS: Production architecture claim
**Lines**: 764-765  
`K302a 2-EXCHANGE (K280 80% + K297 RWA [PAXG 60% / SPX 40%] 20%) combined 55d Sh +32.59 / 98.7% K287d retention / 2 exchanges` — correctly reflects K303 decision (K302a v6.12). PASS.

---

### Finding 1.4 — PASS: v6.12 FINAL mentions consistent
All references to `v6.12 FINAL` in the banner (line 764), Live Monitoring header (line 781), and TOC links (lines 1258, 1301) are consistent. PASS.

---

### Finding 1.5 — PASS: 試行数 counter
**Line**: 763  
`738,388+` — credible given evolution from 710,079 cited in an earlier section (line ~3483). No contradiction. PASS.

---

## Focus Area 2: Tips Log Integrity

### Finding 2.1 — PASS: K306-K322 chronicle entry is `open` by default
**Line**: 8114  
```html
<details open>
  <summary><strong>★★★ 2026-05-25 14:35 JST — K306-K322 chronicle: deployment scaffolding, ground-truth audit, data-quality probes, HMM follow-up</strong></summary>
```
Correctly `open`. PASS.

---

### Finding 2.2 — PASS: K288-K305 entry is closed (collapsed) by default
**Line**: 8056  
```html
<details>
  <summary><strong>★★★★★★ 2026-05-25 13:55 JST — v6.12 K302a FINAL PRODUCTION 確定 (K288-K305 journey)</strong></summary>
```
No `open` attribute — collapsed. PASS.

---

### Finding 2.3 — PASS: Older entries collapsed
All `<details>` tags from line 8145 onward (K254-K287 journey, signal amplitude principles, older K-series) lack the `open` attribute. PASS.

---

### Finding 2.4 — PASS: No duplicate K-number references
Grep across K306-K322 shows each K-number appears exactly once as a primary event. No contradictory claims found.

---

### Finding 2.5 — PASS: K317 retraction properly contextualized
**Lines**: 8132, 8134  
K317 is explicitly labeled `(bug confirmed but mis-attributed)` with a clear note that the claim `"K208 production bug, K280 Sh overstated 10-20%"` was an `誤主張` (false claim). K319 entry confirms `K317 retracted, K302a v6.12 deployment 安全`. K319 language is clear and unambiguous. PASS.

---

### Finding 2.6 — MED: K320 and K323 listed as "in-flight" with no resolution
**Severity**: MED  
**Line**: 8142  
```html
<li><strong>【インフライト】</strong> K320 (HMM on K297 satellite, K315 follow-up), K323 (FR-regime filter for K280, K315 alt) は並列 sonnet agent 実行中。</li>
```
These waves are listed as currently executing. Now at K329, these should have completed. If results exist, they should be logged. If they were abandoned, the entry should be updated to reflect the outcome. This creates reader confusion — were these executed and what happened?

**Recommended fix**: Add outcome bullet: e.g., `K320 RESULT: [outcome]` and `K323 RESULT: [outcome]` within the K306-K322 chronicle's in-flight item, or create a new K323-K328 chronicle entry.  
**Effort**: 30 min (requires checking actual K320/K323 output files)

---

## Focus Area 3: Live Monitoring Section

### Finding 3.1 — PASS: SCAFFOLD-READY badges correct
**Lines**: 840, 847, 854  
All three active daemon rows (K280 main, K302a satellite, K304 HL mon) show `SCAFFOLD-READY` badges. The K310 correction comment at line 832 is in place. PASS.

---

### Finding 3.2 — PASS: K310 activation notice card present
**Lines**: 878-894  
K310 Plist Scaffold Status card present, with full explanation of the ground-truth finding and load commands. PASS.

---

### Finding 3.3 — PASS: K200 HLP correctly marked "NO SCRIPT"
**Lines**: 861-864  
```html
<td><span class="lm-badge lm-badge-deprecated" title="No HLP monitor script found in scripts/. Daemon not scaffolded in K310.">NO SCRIPT</span></td>
```
PASS.

---

### Finding 3.4 — PASS: K287d satellite marked DEPRECATED
**Lines**: 867-869  
K287d satellite row shows `DEPRECATED` badge. PASS.

---

### Finding 3.5 — MED: CSS variable `--border-color` undefined in `:root`
**Severity**: MED  
**Lines**: 787, 799  
```css
.lm-card { background:var(--bg-secondary); border:1px solid var(--border-color); ... }
.lm-table th { ... border-bottom:1px solid var(--border-color); ... }
```
The `:root` block (lines 26-50) defines `--border: #30363d` but NOT `--border-color`. The scoped Live Monitoring `<style>` block at line 787 references `var(--border-color)` which will fall back to the browser default (typically transparent or black) rather than the intended `#30363d` dark gray. This means `.lm-card` borders and table header separators in the Live Monitoring section may render incorrectly in some browsers.

**Recommended fix**: Add `--border-color: #30363d;` to the `:root` block at line 31, OR change lines 787 and 799 to use `var(--border)` which is the correctly defined variable.  
**Effort**: 5 min

---

### Finding 3.6 — PASS: Plotly equity chart placeholder present
**Lines**: 967-1225+  
`<div id="lm-equity-chart">` exists and is populated by the `loadDashboards()` async function with traces for K280 and K302a. responsive:true flag set at line 1225. PASS.

---

## Focus Area 4: Mobile Responsiveness

### Finding 4.1 — LOW: 375px (iPhone SE) breakpoint absent
**Severity**: LOW  
Media query breakpoints present: `1001px`, `1000px`, `768px`, `600px`, `480px`. No specific `375px` breakpoint for iPhone SE exists. The `480px` breakpoint covers this device (375px < 480px), so the rules do apply, but there is no fine-tuned optimization for the smallest viewport.

**Evidence**: Lines 489-493 (480px breakpoint), 733-748 (480px ext). Lines 558-620 (768px comprehensive block).  
**Impact**: Minor — 480px rules cascade to 375px, so no hard breakage. Single-column layout and font scaling apply.  
**Recommended fix**: Add a `@media (max-width: 375px)` block if further font-size or padding reduction is needed.  
**Effort**: 30 min

---

### Finding 4.2 — LOW: 414px (iPhone Plus) breakpoint absent
Same rationale as 4.1 — 414px falls inside the 480px breakpoint zone. No regression, but no targeted optimization.  
**Effort**: 30 min (combined with 4.1)

---

### Finding 4.3 — PASS: 768px (iPad) breakpoint present
**Lines**: 480-488, 558-620  
Two `@media (max-width: 768px)` blocks. The comprehensive block at 558-620 handles typography, chart widths, table scrolling, code blocks. PASS.

---

### Finding 4.4 — PASS: Tables horizontally scrollable
**Lines**: 606-610 (global), 232, 528  
```css
.card table, .card .data-table, table.data-table {
  display: block !important;
  overflow-x: auto !important;
  white-space: nowrap;
}
```
Plus many inline `<div style="overflow-x:auto;">` wrappers (lines 819, 7251, 7294, 7396, etc.). PASS.

---

### Finding 4.5 — PASS: Font sizes readable at small viewports
480px breakpoint sets h1=1.2rem, h2=1.0rem, h3=0.95rem (lines 733-736). Table font-size 0.68rem at 480px. PASS.

---

### Finding 4.6 — PASS: Plotly responsive flag
26 of 28 `Plotly.newPlot` calls include `{responsive: true}`. The two at lines 1224 and bare calls in the sc-* section are addressed below in Focus Area 6. For the live monitoring chart (line 1224-1225), `responsive: true` is present. PASS.

---

## Focus Area 5: Dead Sections / Outdated Content

### Finding 5.1 — HIGH: Footer still claims "Production v6.11 K287d SATELLITE"
**Severity**: HIGH  
**Line**: 8911  
```html
<p>Systematic Alpha Discovery in MEXC Perpetual Futures | crypto-lab | Research Baseline v4.1 / Production v6.11 K287d SATELLITE</p>
```
The footer explicitly states the production version is `v6.11 K287d SATELLITE`, which was superseded by `v6.12 K302a` at K303. The footer timestamp (line 8912) also reads `更新: 2026-05-25 13:35 JST | K297完了` — correct date but wrong production label and outdated event reference.

**Recommended fix**: Update line 8911 to:  
`Research Baseline v4.1 / Production v6.12 K302a (K280 80% + K297 RWA 20%)`  
Update line 8912 to: `更新: 2026-05-25 14:37 JST | K302a v6.12 FINAL PRODUCTION確定 (K303) | 手法: flearn.pdf §5 + §6厳密ゲート`  
**Effort**: 5 min

---

### Finding 5.2 — HIGH: K287d "← 現在" arrow in tips log points to superseded production
**Severity**: HIGH  
**Line**: 8196  
```html
<li>→ <strong style="color:var(--accent-cyan);">K287d SATELLITE combined v6.11 (<strong>33.00</strong>, ZERO MaxDD) ← 現在</strong></li>
```
This appears inside the "K254-K287 journey" chronicle (closed by default, but still reads `← 現在`). The ensemble evolution chain ends at K287d v6.11 with a "← 現在" (← current) pointer. This is incorrect — the current production is K302a v6.12.

Additionally, line 8200 in the same section says:  
`【推奨デプロイ構成】 K280 (80%) = PRODUCTION CORE / K287d Satellite [K270 dYdX 50% + K275 OKX 50%] (20%) = SATELLITE`  
This deploy recommendation refers to the now-superseded v6.11 architecture.

**Recommended fix**:
- Line 8196: Change `← 現在` to `← v6.11 (K303にてv6.12 K302aへ更新済み)`
- Line 8200: Append `(歴史的記録: K303にてK302a v6.12へ更新。現行: K280 80% + K297 RWA 20%)`  
**Effort**: 5 min

---

### Finding 5.3 — MED: Survivor-card note cites "現在のプロダクション v6.11 K287d SATELLITE"
**Severity**: MED  
**Line**: 3480  
```html
<p><strong>⚠️ 注記:</strong> 下記の「8生存者」はK176世代（初期スクリーニング）の分析。現在のプロダクション（<strong>v6.11 K287d SATELLITE: K280 (80%) + K287d Sat [K270 dYdX + K275 OKX] (20%)</strong>）は多層構造に進化しており...</p>
```
This note in the "survivor card" section correctly warns the reader that the section is historical, but its inline description of "現在のプロダクション" (current production) is still v6.11, not v6.12.

**Recommended fix**: Update the parenthetical to `v6.12 K302a: K280 (80%) + K297 RWA [PAXG 60% / SPX 40%] (20%)`.  
**Effort**: 5 min

---

### Finding 5.4 — LOW: Mobile TOC missing 6 sections present in desktop TOC
**Severity**: LOW  
**Lines**: 1255-1275 (mobile TOC), 1297-1330 (desktop TOC)  
The mobile TOC (shown on viewports ≤1000px) has 22 entries. The desktop TOC has 27 entries. Missing from mobile TOC:
1. `#daily-tf-advantage` (日足の優位性)
2. `#scan-4h` (4H スキャン)
3. `#asymmetric-edge` (非対称エッジ)
4. `#portfolio-analysis` (ポートフォリオ分析)
5. `#equity-simulator` (資産推移シミュレータ)
6. `#is-oos-reversal` (IS/OOS 反転事例)

All 6 section IDs exist as real `<section>` elements (confirmed at lines 5982, 6023, 6106, 6183, 6725, 6520). Mobile users cannot navigate to these sections via TOC.

**Recommended fix**: Add the 6 missing `<li>` entries to the mobile TOC `<ol>` block (lines 1256-1274).  
**Effort**: 5 min

---

### Finding 5.5 — LOW: No TODO/FIXME/WIP comments found
Grep for `TODO`, `FIXME`, `WIP` returned no results. PASS.

---

### Finding 5.6 — PASS: No inappropriate ACTIVE/DEPLOY-READY badges for retracted items
ACTIVE and DEPLOY-READY strings appear only in the K310 historical comment (line 832-837, noting that prior waves incorrectly used these labels) and in the tips log as historical record. No current badge in the Live Monitoring table uses these values. PASS.

---

## Focus Area 6: Performance

### Finding 6.1 — INFO: File has grown to 8919 lines (952 KB)
**Severity**: INFO (expected growth)  
Previous audit noted 8500+ lines; task description expected 8862; actual is 8919. Growth of ~57 lines since task description was written. The file is 930 KB, approaching 1 MB threshold. Primary drivers are inline JSON equity arrays (lines ~1597-1600: 4 large arrays, each 700+ data points), chart labeler case data (line 7183: ~15 KB inline JSON), and accumulated tips log content.

No immediate action required, but extraction of the large equity arrays (lines 1597-1600) to an external JSON file would reduce page size by ~150-200 KB.

**Estimated inline JSON impact**: Lines 1597-1600 contain 4 arrays totaling approximately 150 KB. The sc-combined-eq chart at line 1771+ adds another ~80 KB.  
**Effort**: 2h (requires js fetch refactor)

---

### Finding 6.2 — MED: 12 bare `Plotly.newPlot` calls not wrapped in `__renderWhenReady`
**Severity**: MED  
**Lines**: 1771, 1782, 1794, 1846, 1857, 1869, 1921, 1932, 1944, 6929, 6940, 6949  
The `__renderWhenReady` wrapper (defined at line 12) was introduced to solve silent chart failures when Plotly hasn't loaded or container divs have no width. However, 12 `Plotly.newPlot` calls bypass this wrapper. The sc-* charts (lines 1771-1944) and equity simulator (lines 6929-6949) are called bare.

Note: Line 1224 (Live Monitoring equity chart) is inside `loadDashboards()` which is called after the DOM is ready, and lines 1596, 1678 wrap their sections. But sc-combined-*, sc-atr-*, sc-fopd-* (9 charts) and sim-* (3 charts) are bare inline scripts.

**Risk**: On slow connections or older mobile browsers, these charts may silently fail if the DOM isn't ready when the script runs. Since Plotly is loaded in `<head>` (line 8), the Plotly availability issue is mitigated, but DOM readiness for the container divs is not guaranteed for inline scripts that execute during parsing.

**Recommended fix**: Wrap each bare `Plotly.newPlot` call in `window.__renderWhenReady(function() { ... }, 'chart-id')`.  
**Effort**: 30 min

---

### Finding 6.3 — LOW: Duplicate media query blocks
**Lines**: 480-488 (first `@media (max-width:768px)`) and 558-620 (second comprehensive `@media (max-width:768px)`) — two separate blocks for the same breakpoint. While browsers handle this correctly (last definition wins), it increases file size and maintenance complexity.

Similarly, `@media (max-width:480px)` appears at both lines 489-493 and 733-748.

**Recommended fix**: Consolidate during the next refactoring wave (separate issue from this audit).  
**Effort**: 30 min (during planned periodic refactoring)

---

### Finding 6.4 — PASS: No dead JS functions detected
The 21 JS functions defined are all called elsewhere in the page (setEl, setHtml, fmtTs, alertClass, alertIcon, renderAlerts, renderFlagList, loadDashboards, renderEquityChart, onScroll, quantile, mean, median, getReturnsSource, simulateOne, maxDD, sha256, checkLock, showForm, show, attempt). No unreachable functions identified.

---

## Focus Area 7: Internal Consistency

### Finding 7.1 — PASS: Sharpe numbers internally consistent
Cross-checked key numbers across sections:

| Metric | Expected | Found at | Status |
|--------|----------|----------|--------|
| K280 OOS Sh | 18.46 | Lines 902, 8148, 8158, 8195 | PASS |
| K287d combined 55d Sh | 33.00 | Lines 8108, 8148, 8166 | PASS |
| K302a combined 55d Sh | 32.59 | Lines 764, 937, 8079, 8084, 8109 | PASS |
| K302a Sh/exchange | 16.30 | Lines 764, 8079, 8084 | PASS |
| K297 EW Sh | 10.17 | Lines 8071, 8883, 8892 | PASS |
| K297 PAXG Sh | 16.91 | Lines 8071, 8892 | PASS |
| K297 SPX Sh | 5.87 | Lines 8071, 8891 | PASS |
| K302a retention | 98.7% | Lines 764, 1379, 8079 | PASS |
| K301 combined Sh | 35.26 | Lines 8077, 8084 | PASS |

Note: K280 Sh `17.11` at line 8138 is the baseline before HMM filtering in the K315 experiment. This is a distinct measurement from OOS Sh `18.46`. The 17.11 value appears to be a 55d realized Sh window (not the full OOS) used in the K315 HMM test. No explicit clarification is provided in the text, which could confuse readers. This is a documentation gap but not an error.

---

### Finding 7.2 — PASS: K317 retraction consistent across all mentions
K317 is mentioned in two places:
1. Line 8132 (K306-K322 chronicle): explicitly `誤主張` (false claim), corrected by K318+K319
2. Line 8134: `K317 retracted` explicitly stated

No other K317 mentions exist. No contradictions. PASS.

---

### Finding 7.3 — PASS: K-number sequence coherent
K306-K322 in the chronicle covers all listed waves. K320 and K323 are noted as in-flight (finding 2.6, MED). K324-K328 are not present — this is expected as K329 is the current wave and the chronicle hasn't been updated yet.

---

### Finding 7.4 — PASS: K302a vs K302 distinction maintained
The chronicle clearly distinguishes K302 (initial test) from K302a (final adopted version). Line 8079 labels K302, line 8084 labels K302a as adopted. Banner and monitoring consistently use K302a. PASS.

---

## Summary Table

| # | Area | Finding | Severity | Line(s) | Effort |
|---|------|---------|----------|---------|--------|
| 5.1 | Dead sections | Footer claims v6.11 production | HIGH | 8911-8912 | 5 min |
| 5.2 | Dead sections | K287d "← 現在" arrow obsolete | HIGH | 8196, 8200 | 5 min |
| 6.2 | Performance | 12 bare Plotly.newPlot calls | MED | 1771-1944, 6929-6949 | 30 min |
| 3.5 | Live Monitoring | --border-color CSS var undefined | MED | 787, 799 | 5 min |
| 2.6 | Tips log | K320/K323 still shown as in-flight | MED | 8142 | 30 min |
| 5.3 | Dead sections | Survivor-card note cites v6.11 | MED | 3480 | 5 min |
| 1.1 | Banner | Header meta timestamp 9h behind | LOW | 772 | 5 min |
| 4.1 | Mobile | No 375px/414px breakpoint | LOW | — | 30 min |
| 5.4 | Dead sections | Mobile TOC missing 6 sections | LOW | 1255-1275 | 5 min |
| 6.3 | Performance | Duplicate @media query blocks | LOW | 480/558, 489/733 | 30 min |
| 6.1 | Performance | File approaching 1 MB | INFO | 1597-1600 | 2h |

**HIGH**: 2 | **MED**: 4 | **LOW**: 4 | **INFO**: 1 | **PASS**: 24

---

## Recommended K330 Fix Order

1. (5 min each) Footer v6.11→v6.12 (line 8911-8912) + K287d arrow (8196, 8200) + survivor note (3480) + CSS var (787/799) + header meta timestamp (772) — batch all 5-min fixes
2. (5 min) Mobile TOC add 6 missing sections
3. (30 min) Add resolution notes for K320/K323 in-flight items
4. (30 min) Wrap bare Plotly calls in __renderWhenReady
5. (30 min) Consolidate duplicate @media blocks (can defer to next refactor wave)
6. (2h) Extract large equity JSON arrays to external files (defer to dedicated perf wave)
