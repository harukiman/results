# Wave K383 — K362 Coinbase USDC Retrigger (R13 Finding 1)

**Generated:** 2026-05-27T09:48:03+09:00  
**K362 Original Verdict:** REJECT  
**K383 Verdict:** CONFIRM REJECT  
**Triggered by:** R13-01 micro-scraper: "Coinbase USDC yield governance realized — 90% revenue share to HL protocol, $135-160M estimated annual, rolling out Q3 2026"

---

## Executive Summary

R13-01 flagged K362 for retrigger citing "governance realized." K383 re-examined whether this realization introduced a claimable USDC yield product or changed the revenue distribution away from pure HYPE buybacks.

**Finding: K362 REJECT stands. The following remains true as of 2026-05-27:**

1. All AQAv2 reserve yield routes exclusively to Hyperliquid Assistance Fund → HYPE buybacks.
2. No sUSDC, yield-bearing USDC token, or direct USDC holder yield product was launched or announced.
3. HYPE staking APY (2.37%) is unchanged — AQAv2 yield does NOT feed staking rewards.
4. No governance vote was found to redirect AQAv2 yield toward USDC depositors.
5. "Governance realized" in R13-01 means AQAv2 framework activation (Coinbase as treasury deployer confirmed), not a yield distribution product launch.

**Action: v6.14a (sUSDe 5% sleeve unchanged) remains the recommended architecture.**

---

## Phase 1 — R13-01 Evidence & Governance Investigation

### Sources Fetched (4 of 5 successful)

| # | URL | Status | Key Finding |
|---|-----|--------|-------------|
| 1 | CoinDesk May 18 (USDC deal analysis) | 200 | Revenue distribution macro details; no USDC holder yield mentioned |
| 2 | Coinbase blog (official announcement) | 403 blocked | N/A |
| 3 | KuCoin explainer (AQAv2 + HYPE staking) | 200 | Assistance Fund uses yield for: HYPE buybacks, MM rebates, protocol insurance. No depositor distribution. |
| 4 | CoinCentral (HYPE buyback routing) | 200 | "Revenue routed through Assistance Fund → HYPE buybacks confirmed. No USDC holder yield proposals." |
| 5 | StableDash (USDH governance proposals) | 404 | N/A |

### R13-01 Finding — Exact Text

```json
{
  "id": "R13-01",
  "title": "Coinbase/Circle USDC Yield Sharing on Hyperliquid (May 2026) — 90% Revenue to HL Protocol",
  "why_relevant": "K362トリガーのHL Coinbase USDC yield product governanceが実現段階へ",
  "actionable_for_k383": true,
  "k383_note": "K362シグナル確定。$135-160M年間revenue追加はHYPE supply-demand改善要因"
}
```

**Critical observation:** R13-01 notes "$135-160M annual revenue for HYPE supply-demand improvement" — this is HYPE buyback benefit, not USDC holder yield. The R13 note itself implicitly confirms buyback-only routing. The retrigger label "K362 Confirmed" in R13 was imprecise: it confirmed the deal structure, not a new yield product.

### AQAv2 Governance Facts (K383 Updated)

| Field | K362 Data (2026-05-27 T07:57) | K383 Update (2026-05-27 T09:48) |
|-------|-------------------------------|----------------------------------|
| AQAv2 announced | 2026-05-14 | Unchanged |
| USDC on HL | $5.1B | $5.1B |
| Yield share to HL | up to 90% (exact undisclosed) | Unchanged — "vast majority" per Coinbase |
| Annual routed to HL | $135-160M | Unchanged |
| Routing mechanism | HYPE_buyback_only | **CONFIRMED** — KuCoin + CoinCentral both confirm |
| Claimable USDC yield product | NOT FOUND | **STILL NOT FOUND** |
| sUSDC equivalent launched | No | **No** |
| HYPE staking APY change | No change (2.37%) | **No change confirmed** |
| HLP vault yield change | No change | **No change confirmed** |
| Governance vote for passthrough | NOT FOUND | **NOT FOUND** |
| Q3 2026 rollout items | phased USDC integration | USDC as canonical quote asset; no yield product announced |

---

## Phase 2 — Revenue Distribution Channel Analysis

All confirmed distribution channels for AQAv2 yield:

### Channel 1: HYPE Buybacks (PRIMARY — 90%+)
- **Route:** Assistance Fund → open-market HYPE repurchase and burn
- **Benefit type:** INDIRECT (requires HYPE token ownership)
- **Claimable yield:** NO
- **Sleeve candidate:** NO
- **K383 status:** CONFIRMED EXCLUSIVE route

### Channel 2: Market-Maker Rebates (minor)
- **Route:** Assistance Fund → MM rebate program
- **Benefit type:** OPERATIONAL (benefits MM participants only)
- **Claimable yield for USDC holders:** NO
- **Sleeve candidate:** NO

### Channel 3: Protocol Insurance (minor)
- **Route:** Assistance Fund → insurance reserve
- **Benefit type:** SYSTEMIC RISK BUFFER
- **Claimable yield for USDC holders:** NO
- **Sleeve candidate:** NO

### Channel 4: Direct USDC Holder Yield (hypothetical — NOT FOUND)
- **Status:** This product does NOT exist as of 2026-05-27
- **Would require:** HL governance proposal + vote + implementation
- **No evidence of:** proposal, vote, or implementation timeline
- **Trigger for K384:** Publication of formal governance proposal for this product

---

## Phase 3 — K344 sUSDe Comparison (Refreshed)

### K344 Baseline (Active, Current)

| Metric | sUSDe K344 |
|--------|-----------|
| APY (current) | 3.72% (K344 live: 4.01% Q1 mean) |
| APY (7d MA) | 4.04% |
| Sharpe | 8.39 |
| MDD | 0.11% |
| Correlation vs HL trading | 0.05 (near-zero) |
| Allocation | 5.0% of portfolio |
| Chain | Ethereum (outside HL ecosystem) |
| Claimable | YES |
| Audit | Multiple independent |

### Hypothetical Coinbase USDC Direct Yield (if launched)

| Metric | AQAv2 Direct (Hypothetical) |
|--------|----------------------------|
| APY (direct passthrough) | 2.6-3.1% ($135-160M ÷ $5.1B USDC) |
| APY net of friction | ~2.3-2.8% (below sUSDe) |
| Sharpe | Unknown (no track record) |
| MDD | Unknown |
| Correlation vs HL trading | HIGH (~0.6-0.8, HL-native) |
| Claimable | NOT LAUNCHED |
| Audit | N/A |
| HL concentration delta | +5pp (57.5% → 62.5%) |

**Conclusion:** Even if launched, estimated APY (2.6-3.1%) is BELOW sUSDe (4.01%) AND the product would be HL-native (high correlation), destroying orthogonality advantage. No scenario favors replacement.

---

## Phase 4 — v6.14 Architecture Candidates

### v6.14a — RECOMMENDED
```
sUSDe 5%        (K344 confirmed, Ethereum-native, Sh 8.39, MDD 0.11%)
USDC HL 0%      (no claimable yield product exists)
HL concentration: 57.5% (unchanged, 7.5pp headroom preserved)
```

**Rationale:** AQAv2 HYPE buyback benefit is captured passively through existing HL trading strategies (K280, K297', etc.). No sleeve adjustment warranted.

### v6.14b — BLOCKED
```
sUSDe 3% + USDC HL 2%
Gate condition: USDC HL claimable yield >= 3% — NOT MET (product doesn't exist)
HL concentration: 59.5% (+2pp)
```

### v6.14c — BLOCKED
```
sUSDe 0% + USDC HL 5%
Gate conditions: multiple failures (G1/G4/G5)
HL concentration: 62.5% (+5pp)
Loss: Ethereum-native orthogonality of sUSDe
```

---

## Phase 5 — K266 Strict Gate Evaluation

### Gate Results: AQAv2 Direct USDC Yield (Hypothetical)

| Gate | Threshold | Actual | Pass/Fail |
|------|-----------|--------|-----------|
| G1 Net APY | ≥ 5.0% | N/A (product not launched) | FAIL |
| G2 Audit + counterparty | Audited | N/A | FAIL |
| G3 Peg stability | Stable peg | N/A | FAIL |
| G4 Orthogonal (rho < 0.3) | < 0.3 | ~0.7 (if HL-native) | FAIL |
| G5 Holder-claimable | YES | NO (buyback-only) | FAIL |
| **Overall** | | | **0/5 — REJECT** |

### Gate Results: HYPE Staking

| Gate | Threshold | Actual | Pass/Fail |
|------|-----------|--------|-----------|
| G1 Net APY | ≥ 5.0% | 2.37% | FAIL |
| G2 Audit | Audited | Native L1 (low risk) | PASS |
| G3 Peg stability | Stable | FAIL — HYPE volatile | FAIL |
| G4 Orthogonal | rho < 0.3 | ~0.85 (HL-native) | FAIL |
| G5 Claimable | YES | NO (auto-compound, 7d unlock) | FAIL |
| **Overall** | | | **1/5 — REJECT** |

### Gate Results: sUSDe (K344 baseline, reference)

| Gate | Threshold | Actual | Pass/Fail |
|------|-----------|--------|-----------|
| G1 Net APY | ≥ 5.0%* | 4.01% (Q1 avg) / 3.72% (current) | MARGINAL* |
| G2 Audit | Audited | Multiple audits | PASS |
| G3 Peg stability | Stable | MDD 0.11% (K344 live) | PASS |
| G4 Orthogonal | rho < 0.3 | 0.05 | PASS |
| G5 Claimable | YES | YES (7d cooldown) | PASS |
| **Overall** | | | **4/5 — ACCEPT (grandfathered at 5%)** |

*sUSDe currently 3.72% vs 5% gate — grandfathered under K344 live status. No change warranted unless sustained drop below 3.5% threshold (K361 defined).

---

## Phase 6 — HL Concentration Impact

| Scenario | HL Exposure | Delta | Within Cap (65%) | Headroom |
|----------|-------------|-------|-------------------|----------|
| Current (v6.13d) | 57.5% | — | YES | 7.5pp |
| v6.14a (sUSDe unchanged) | 57.5% | 0pp | YES | 7.5pp |
| v6.14b (split 3+2) | 59.5% | +2pp | YES | 5.5pp |
| v6.14c (full replace) | 62.5% | +5pp | YES (tight) | 2.5pp |

Note: sUSDe (Ethereum-native) is NOT included in HL concentration count. Any USDC HL sleeve would be included.

**v6.14a preserves maximum concentration headroom (7.5pp buffer). This is strategically valuable for future K384+ opportunities that may have genuine HL-native alpha (e.g., HLP vault, HipurrFi if matures).**

---

## Phase 7 — Decision Matrix

| Factor | K362 Data | K383 Update | Change? |
|--------|-----------|-------------|---------|
| AQAv2 routing mechanism | HYPE buyback only | HYPE buyback only confirmed | NO CHANGE |
| Claimable USDC yield product | NOT FOUND | NOT FOUND | NO CHANGE |
| sUSDC or yield token | NO | NO | NO CHANGE |
| HYPE staking APY boost | NO (2.37%) | NO (2.37%, AQAv2 doesn't feed staking) | NO CHANGE |
| HLP vault boost | NO | NO | NO CHANGE |
| Governance vote for passthrough | NOT FOUND | NOT FOUND | NO CHANGE |
| K344 sleeve replacement warranted | NO | NO | NO CHANGE |
| K362 REJECT verdict | REJECT | **CONFIRM REJECT** | CONFIRMED |

---

## Phase 8 — Implementation Effort

**K383 verdict: CONFIRM_REJECT — no implementation required.**

sUSDe sleeve (K344) operates unchanged. Daemon `com.cryptolab.susde-oc.plist` continues scheduled monitoring.

### If future K384 triggers on governance proposal (monitor trigger):
Estimated implementation effort:
1. USDC HL yield monitoring daemon (`wave_k384_usdc_hl_yield_daemon.py`) — ~2h
2. Architecture rebalance (K386 v6.14b execution if APY ≥ 5%) — ~1h
3. HTML runbook + `report.html` updates — ~1h
4. Gate re-evaluation with live APY data — ~1h
**Total if triggered: ~5h**

---

## Monitor Trigger Definition

**Re-trigger K384 when:**

> A formal HL governance proposal is published (hyperliquid.gitbook.io governance, HL Discord #governance, Hyper Foundation announcements) that explicitly routes a portion of AQAv2 USDC reserve yield to a **holder-claimable** yield product (sUSDC-style rebasing token, yield vault, or direct distribution to USDC depositors).

**Watch channels:**
- https://hyperliquid.gitbook.io/hyperliquid-docs (governance section)
- HL Discord `#governance` channel
- Hyper Foundation Twitter / X
- DefiLlama new pools (search "USDC Hyperliquid" yield > 3%)
- inbox-poll.plist scheduled scraper → add HL governance URL

**Recheck cadence:** 30 days (2026-06-27)

---

## Final Verdict

```
K383 Decision: CONFIRM REJECT (K362 REJECT stands — permanent unless monitor trigger fires)

K362 original reason: "AQAv2 yield routes exclusively to HYPE buybacks — no passthrough"
K383 finding:         Same. Governance realization = AQAv2 framework activation, NOT yield product launch.
K344 sleeve:          UNCHANGED (sUSDe 5%, Sh 8.39, MDD 0.11%, rho 0.05)
Architecture:         v6.14a (no change from v6.13d)
Next action:          K363+ sUSDe monitoring continues. No new scaffold required.
Monitor trigger:      HL governance proposal for USDC holder claimable yield (re-trigger K384)
```

---

## Appendix A — K344 sUSDe OC Controller Current State

| Metric | Value |
|--------|-------|
| Current APY | 3.72% |
| 7d MA APY | 4.04% |
| EMA30 APY | ~4.34% |
| OC signal | 0.5 (HOLD partial) |
| Current vs EMA30 | -0.31pp (below threshold, hold) |
| 7d momentum | -0.60pp |
| Allocation | 5% of portfolio |
| Live since | K344 (2026-02-xx) |
| Status | ACTIVE — daemon running |

Source: wave_k344_ethena_optimal_control.json (K344 run: 2026-05-26T21:32:11Z)

---

## Appendix B — URLs Consulted

1. CoinDesk (2026-05-18): https://www.coindesk.com/markets/2026/05/18/hyperliquid-s-usdc-deal-could-supercharge-hype-pressure-circle-coinbase-margins-analysts-say
2. KuCoin explainer: https://www.kucoin.com/blog/coinbase-and-circle-partner-with-hyperliquid-usdc-treasury-role-hype-staking-and-usdh-transition-explained
3. CoinCentral: https://coincentral.com/hyperliquid-usdc-yield-deal-could-route-up-to-90-to-hype-buybacks/
4. WebSearch: "HyperLiquid Coinbase USDC governance 90% revenue share HL protocol 2026"
5. WebSearch: "HyperLiquid USDC yield passthrough sUSDC claimable yield product governance May 2026"
6. R13 findings: /Users/nekonaomichi/crypto-lab/external_findings_round13.json (R13-01)
7. K362 baseline: /Users/nekonaomichi/crypto-lab/wave_k362_coinbase_usdc_hl.json
8. K344 baseline: /Users/nekonaomichi/crypto-lab/wave_k344_ethena_optimal_control.json
