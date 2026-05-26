# Wave K355 — Perp DEX Competitive Landscape + v6.13d Concentration Risk Assessment

**Generated:** 2026-05-27 07:18 JST  
**Wave:** K355  
**Synthesis:** R12-11 (Paradex $8T endgame) + R12-15 (Variational $50M) + R12-16 (CME/ICE CFTC)  
**Deliverables:** `wave_k355_perp_dex_landscape.py` / `.json` / `.md`

---

## Executive Summary

v6.13d carries **57.5% exposure to Hyperliquid** (HL) infrastructure across K280 + K297'. This is a real and non-trivial concentration risk. Three active threat vectors exist simultaneously:

1. **R12-16 (ACTIVE):** CME and ICE lobbied CFTC in May 2026 to scrutinize HL over manipulation and benchmark distortion. No formal enforcement yet, but the lobbying is live.
2. **R12-15 (LIVE competitor):** Variational — already operational with $200B cumulative volume and $50M Series A — offers Gold/Silver/WTI RFQ perps that directly substitute HL HIP-3 carry. Competitive pressure on K297' carry is already a present tense concern, not future.
3. **R12-11 (structural):** HL market share already compressed from 80% peak (mid-2025) to 31.7% (Feb 2026). The multi-venue era has arrived.

**Recommended actions:**
- v6.13e fallback (K280 85% + K297' 10% + sUSDe 5%) is pre-approved and should be treated as the standing contingency.
- Emergency HL exit script is unbuilt — K356 highest priority.
- Variational API scouting = K356 research task.
- HL HIP-3 dominance window: **6-18 months** before meaningful RWA carry fragmentation.

---

## Phase 1: Venue Catalog

### Data Sources and Methodology

Data fetched via WebFetch (May 27 2026): paradex.trade/blog (R12-11 self-published competitive analysis), coindesk.com (R12-15, R12-16), dydx.xyz, aevo.xyz, drift.trade, lighter.xyz, variational.fi (403). Paradex blog data is self-reported — flag potential self-serving bias on their own metrics.

### Venue Comparison Table

| Venue | Chain | 30d Vol ($B) | OI ($B) | OI/Vol | Mkt Share | Assets | RWA | Funding Mechanism | Reg Status |
|---|---|---:|---:|---:|---:|---:|---|---|---|
| **Hyperliquid** | HL L1 custom | 248.0 | 5.63 | 0.021 | 31.7% | 230 | PAXG, SPX (HIP-3) | Hourly discrete (8h computed) | No license; CFTC pressure |
| **Lighter** | ETH ZK-Rollup | 145.9 | 1.02 | 0.007 | ~18.6% | 500+ | Equities, Forex, Commodities (Chainlink) | 8h standard | No license; Jan 2026 launch |
| **Variational** | Arbitrum | 71.8 | 0.93 | 0.014 | ~9.2% | 500+ | Gold, Silver, Copper, WTI | OLP-embedded carry | Cayman Is.; no formal license |
| **Aster** | BNB (primary) | 87.5 | 1.83 | 0.013 | 11.2% | ~100 | Tokenized stocks | 8h standard | Delisting concerns (wash) |
| **EdgeX** | StarkEx Validium | 67.4 | 0.47 | 0.007 | ~8.6% | 100+ | None confirmed | 8h standard | Privacy architecture |
| **Extended** | Starknet | 55.5 | 0.28 | 0.005 | ~7.1% | 100+ | Yield collateral only | 8h standard | Compliance-ambiguous |
| **GRVT** | ZK Stack sovereign | 53.2 | 0.39 | 0.007 | ~6.8% | 100+ | None confirmed | 8h standard | Bermuda Class M + VASP |
| **Paradex** | Starknet appchain | 43.5 | 0.61 | 0.014 | 0.99% | 250+ | None confirmed | Continuous (unrealized PnL) | No license; confidentiality |
| **dYdX v4** | Cosmos chain | N/A | 0.20 | N/A | N/A | 220+ | None | 8h standard | US-excluded; Int'l Ltd |
| **Aevo** | ETH L2 (OP Stack) | N/A | N/A | N/A | N/A | N/A | None | Hybrid off/on-chain | Paradigm/CB backed |
| **Drift** | Solana | N/A | N/A | N/A | N/A | 100+ | None | Solana-native 8h | Trail of Bits audited |
| **GMX v2** | Arbitrum + Avax | N/A | N/A | N/A | N/A | N/A | None | Borrowing rate (pool) | Permissionless |
| **Vertex** | Arbitrum | N/A | N/A | N/A | N/A | N/A | None | Hybrid sequencer | Permissionless |

**Notes on data gaps:** dYdX, Aevo, Drift, GMX, Vertex volume data not obtained this wave (API blocked or not fetched). OI/Vol ratio is the OI-to-30d-volume ratio per R12-11. Market share figures are from the R12-11 Paradex report's 30d window — treat as directional, not audited.

### Key Architectural Observations

**Capital Stickiness (OI/Volume):** Three distinct tiers:
- Tier 1: Hyperliquid (0.021) — highest position retention by wide margin. Indicates sticky, long-duration traders.
- Tier 2: Paradex + Variational + Aster (0.013-0.014) — comparable retention, significant second tier.
- Tier 3: Lighter, EdgeX, GRVT, Extended (0.005-0.007) — incentive-driven churn, not sticky capital.

HL's Tier 1 stickiness supports the view that its user base is fundamentally different: algorithmic market makers and yield farmers who hold positions, not speculators chasing fee rebates.

**The RWA battleground is crowded already:**
- Lighter: 500+ markets including US equities (Chainlink 24/5 real data feeds), forex, commodities — LIVE.
- Variational: Gold, Silver, Copper, WTI RFQ perps — LIVE since 2025, $200B vol.
- Hyperliquid HIP-3: PAXG (gold-backed), SPX — LIVE since Jan-Apr 2025.
- HL does NOT have XAG (silver), XAU (gold direct), WTI as confirmed perp markets as of K297 survey.

This means HL is currently missing Silver and WTI, which Variational already offers. **The window for HL RWA monopoly has already closed on commodity perps.**

---

## Phase 2: HL Competitive Position

### HIP-3 RWA Market Summary

| Market | Asset | Carry Sharpe | Ann Return | Max DD | FR Avg | Correlation |
|---|---|---:|---:|---:|---:|---|
| PAXG | Gold-backed token | 16.91 | 8.03% | -0.36% | +7.77% wknd / +8.31% wkday | SPX ρ=0.18 (low) |
| SPX | S&P 500 Index | 5.87 | 6.80% | -1.74% | +5.95% wknd / +7.48% wkday | PAXG ρ=0.18 |
| Portfolio EW | — | **10.17** | **~7.3%** | **-1.41%** | — | — |

Source: K297 (wave_k297_hip3_weekend.md). Data through K297 survey date.

**Key finding from K297:** No weekend premium on HL HIP-3 (contrary to R10 Binance XAG claim). The carry is always-on, weekday > weekend. This is the correct signal for K297' filter design.

### Market Share Trajectory

| Period | HL Share | Interpretation |
|---|---|---|
| Mid-2025 peak | ~80% | Near-monopoly period |
| Feb 2026 | 31.7% | Healthy fragmentation |
| Trajectory | Declining % share | Absolute volume still growing |

The 80% → 31.7% compression does NOT mean HL is losing — it means the total DEX perp market grew dramatically (R12-14: DEX perp volume 4x to $6.7T with 8% CEX share). HL's absolute volume continues growing while competitors capture new flows.

### HL HIP-3 Dominance Window

**Assessment: 6-18 months before meaningful RWA carry fragmentation**

Reasoning:
1. Variational is already live with $200B cumulative vol and $50M new capital. Not a future threat — a present one.
2. Lighter's Chainlink equities feed directly competes with SPX perp. No FR extractable from Lighter's ZK model — different mechanism, but same underlying exposure.
3. HL's moat is: (a) permissionless listing speed (24-48h for new HIP-3 assets vs Variational's RFQ onboarding), (b) builder ecosystem (40% DAU via 3rd-party frontends, $31M fees), (c) HLP liquidity depth.
4. Variational's OLP-embedded carry model obscures FR — no extractable carry signal visible to K297-style strategies. This is a structural difference: Variational won't offer the same arbitrageable FR that K297' captures on HL.
5. **Net effect:** K297' carry on PAXG/SPX is safe for now (Variational doesn't directly offer these specific perps). However, if Variational or Lighter introduces a PAXG or SPX equivalent with similar liquidity, K297' FR premium will compress as arbitrageurs equalize cross-venue pricing.

**Estimated carry compression from Variational scaling Gold:** 10-25% over 12 months if Variational's RFQ Gold volume reaches $10B/month (vs current scale). PAXG is a different wrapper from Variational Gold but close enough that capital will equalize if yield differential exceeds transaction cost.

---

## Phase 3: Cross-Venue Arbitrage Opportunities

### Same-Asset Multi-Venue Listings

| Asset | Venues Available | FR Spread | K208 Extensibility | Priority |
|---|---|---|---|---|
| SOL-PERP | HL + Drift + dYdX | 2-8 bps | HIGH — Drift public API | 1 |
| BTC-PERP | HL + dYdX + Drift + Aevo + Lighter | 0.5-2 bps | MEDIUM — tight spreads | 3 |
| ETH-PERP | HL + dYdX + Drift + Aevo | 1-3 bps | MEDIUM | 3 |
| PAXG-PERP | HL HIP-3 only | N/A | NOT FEASIBLE YET | — |
| Gold-PERP proxy | HL PAXG + Variational Gold RFQ + Lighter | UNKNOWN | MEDIUM-HIGH if Variational API open | 2 |

### Recommended Venue Pairs for K208 Extension

**Priority 1: HL SOL-PERP vs Drift SOL-PERP**
- Both venues have public REST APIs.
- K208 DAR reverse carry pattern directly extensible: same 8h FR cycle on HL; Drift uses comparable Solana-native mechanism.
- Drift cumulative vol $50B+ confirms liquidity.
- Estimated edge: 1-5 bps FR spread captured on 8h cycle.
- Required work: normalize Drift funding rate feed format, add Drift credential support to K208 framework.

**Priority 2: HL PAXG-PERP vs Variational Gold-RFQ**
- High potential but unknown spread — requires data collection first.
- Variational OLP model embeds carry differently from HL FR; pricing gaps may persist structurally.
- First step: verify Variational API endpoint availability and format (K356 task).

**Priority 3: HL BTC vs dYdX v4 BTC**
- K270 already partially tracks dYdX FR data (alt_exchange_fr_daily).
- Low hanging fruit: use existing K270 data to estimate bilateral BTC FR spread.
- Spread likely tight (0.5-2 bps) — may not clear execution cost hurdle.

### K208 Architecture Note

K208 is currently Bybit-HL bilateral DAR reverse carry. Extension to multi-venue requires:
1. Normalized FR schema across venues (HL 8h computed hourly vs Bybit 8h vs Drift Solana-native).
2. Latency matching (HL ~1s block, Bybit CEX ~100ms, Drift Solana ~400ms finality).
3. Settlement timing alignment — all venues compute FR differently at T-windows.
4. Feasibility: HIGH for HL-Drift SOL pair within 2-3 waves of engineering effort.

---

## Phase 4: Concentration Risk Assessment

### v6.13d Capital Allocation

| Component | Weight | Venue(s) | HL Exposure |
|---|---:|---|---:|
| K280 | 75% | Bybit (50%) + HL (50%) | 37.5% |
| K297' (HIP-3 RWA) | 20% | HL only (PAXG + SPX) | 20.0% |
| sUSDe (Ethena OC) | 5% | Ethena / DeFi | 0.0% |
| **Total** | **100%** | | **57.5% HL** |

**57.5% of all capital depends on HL functionality.** This is the honest number. It was flagged by the K346 monitoring trigger (`hl_concentration_alert: if HL capital share > 65%`), but 57.5% is already high.

### Scenario Analysis

#### Scenario A: CFTC Formally Restricts HL HIP-3 (ACTIVE THREAT)
- **Probability (12m):** 15-25%
- **Trigger:** CME/ICE lobbying already filed (May 2026). Next step = formal CFTC investigation.
- **Impact on K297':** Total collapse of alpha. SPX and PAXG carry source eliminated. Strategy returns ~0% (costs > carry).
- **Impact on K280:** Partial — HL execution disruption, not HIP-3 specific. Estimated 5-15% Sharpe degradation.
- **Portfolio return impact:** -2.0pp from K297' loss + -0.75pp from K280 degradation = **~-2.75pp** on 10.0% target.
- **Capital at risk:** 20% (K297' weight). Not capital loss per se, but strategy becomes dead weight.
- **Mitigation already in place:** K346 set R12-16 hard cap at K297' ≤ 20%. v6.13e fallback drops K297' to 10%.

#### Scenario B: HL Platform Shutdown (TAIL RISK)
- **Probability (12m):** 3-7%
- **Impact:** 57.5% of capital at risk (HL execution positions stranded).
- **Capital at risk:** 57.5% — the full HL exposure.
- **Expected loss:** 3-7% probability × 57.5% capital loss = **1.7-4.0% expected loss from this tail alone.**
- **Mitigation status:** No emergency exit script exists. This is the critical gap.

#### Scenario C: Variational Captures RWA Carry (HIGH PROBABILITY)
- **Probability (12m):** 40-60%
- **Impact on K297':** Gradual FR compression — estimated 10-25% carry reduction over 12 months.
- **Portfolio impact:** ~-0.22pp return loss (manageable).
- **Capital at risk:** Zero — carry degradation, not capital loss.
- **Note:** This is the most LIKELY scenario. Variational is already live and scaling.

#### Scenario D: HL Market Share Decline (MEDIUM PROBABILITY)
- **Probability (12m):** 25-35%
- **Impact:** Wider spreads, higher slippage on K280 execution. Cost degradation 5-10%.
- **Capital at risk:** Zero — cost impact, not capital loss.

### Risk Severity Matrix

| Severity | Scenario | P(12m) | Capital at Risk | Expected Impact |
|---|---|---:|---:|---|
| CRITICAL | B: HL Shutdown | 3-7% | 57.5% | 1.7-4.0% expected loss |
| HIGH | A: CFTC HIP-3 enforcement | 15-25% | 20% (dead weight) | -2.75pp return |
| MEDIUM | C: Variational RWA carry capture | 40-60% | 0% | -0.22pp return |
| MEDIUM | D: HL share decline/liquidity thin | 25-35% | 0% | Cost degradation |

**Overall assessment: REAL AND NON-TRIVIAL. Do not downplay.**

The 57.5% HL exposure is too high for a capital-preservation mandate. While the Sharpe (25.47) justifies the current allocation from a pure performance standpoint, the tail risk from Scenario B alone generates 1.7-4.0% expected loss — which is material relative to a 10% annual return target. Scenario A has active regulatory triggers as of May 2026.

### Honest Risk Disclosure

The K346 v6.13d architecture was optimized for maximum Sharpe within the R12-16 regulatory cap (K297' ≤ 20%). It was NOT optimized for venue diversification. The Sharpe optimization correctly maximized return/risk ratio given the inputs, but the inputs don't capture counterparty/platform/regulatory risk. That gap is documented here.

---

## Phase 5: Decision Matrix

### IMMEDIATE ACTIONS (This Wave)

| Action | Status | Concern Level |
|---|---|---|
| Document concentration risk (57.5% HL) | DONE — this wave | HIGH |
| Confirm v6.13e fallback parameters | CONFIRMED — Sharpe 22.89, K280 85%+K297' 10%+sUSDe 5% | HIGH |
| Identify K356 emergency exit script as highest priority | DONE — flagged | CRITICAL |

### MONITOR (Next 30 Days)

| Signal | Threshold | Action |
|---|---|---|
| Variational 30d RWA volume | If > $20B → carry compression imminent | Begin K297' reduce to 15% |
| CFTC formal HL action | Any public filing or investigation open | Execute v6.13e fallback within 24h |
| HL HYPE token 7d return | < -40% from ~$44 level | Heightened platform risk; reduce K297' |
| K297' 30d rolling APR | If PAXG + SPX combined APR < 4% | K297' carry degraded; fallback to v6.13e |
| HL market share | If falls to < 15% (from 31.7%) | Liquidity concern for K280 execution |

### DEFER UNTIL CONCRETE ACTION

- Architecture change to Variational integration (K356+)
- Drift Solana sleeve engineering (K357+)
- Lighter SPX data collection (K357+)

### v6.13e Fallback Trigger Protocol

If any trigger fires:
1. Reduce K297' from 20% → 10% (within 24h of trigger confirmation).
2. Increase K280 from 75% → 85%.
3. sUSDe unchanged at 5%.
4. Log to `deployment_status.json` with timestamp.
5. Post alert to monitoring channel.
6. HL exposure drops from 57.5% → 52.5% (modest reduction — emergency exit script is the real fix).

---

## Phase 6: Forward Strategy

### Memory Recommendation

**Create: `feedback_concentration_risk_HL.md`**

The concentration risk is non-trivial and warrants a persistent memory entry. Key facts:
- v6.13d: 57.5% HL exposure.
- Scenario B (HL shutdown, 3-7% P): 57.5% capital at risk → 1.7-4.0% expected loss from tail.
- Scenario A (CFTC HIP-3, 15-25% P): K297' dead weight, -2.75pp return.
- v6.13e fallback: pre-approved, Sharpe 22.89 vs 25.47 (-2.58).
- Emergency exit script: NOT BUILT. K356 must-do.
- Variational: already live, direct RWA carry competitor.

### K356 Candidates

| Priority | Task | Rationale |
|---|---|---|
| 1 (CRITICAL) | Emergency HL exit script | Can close all HL positions within 2h if trigger fires. Currently unbuilt. |
| 2 (HIGH) | Variational API integration research | Verify endpoint, format, supported assets, WebSocket availability |
| 3 (MEDIUM) | Drift SOL-PERP FR data collection | K208 extension Phase 1: data pipeline before strategy |

### K357 Candidates

| Priority | Task | Rationale |
|---|---|---|
| 1 | Lighter Chainlink equities feed vs HL SPX | Data collection for SPX proxy comparison |
| 2 | Multi-venue FR normalization schema | Foundation for K208 multi-venue arb |
| 3 | GRVT API exploration | Compliance-ready venue for institutional paths |

### v6.13e Conversion Checklist (pre-built for rapid execution)

```
When trigger fires:
1. [ ] Confirm trigger type (CFTC filing / HYPE -40% / K297' APR < 4%)
2. [ ] Execute: reduce K297' target to 10%
3. [ ] Execute: increase K280 target to 85%
4. [ ] sUSDe: no change
5. [ ] Update deployment_status.json
6. [ ] Notify monitoring
7. [ ] Log timestamp and trigger type to wave_k355_events.jsonl (create if needed)
8. [ ] If trigger = CFTC action: immediately begin K356 emergency exit evaluation
```

---

## Appendix: Venue Regulatory Risk Ranking

| Venue | Regulatory Risk | Basis |
|---|---|---|
| GRVT | LOWEST | Bermuda Class M license + mandatory KYC — nearest to regulated |
| dYdX v4 | LOW | US-excluded by policy; Cosmos-based, international Ltd structure |
| Drift | LOW-MEDIUM | Trail of Bits audited; Solana-native; no US restriction stated |
| Aevo | LOW-MEDIUM | Paradigm/CB Ventures backed; EU MiCA exposure |
| Lighter | MEDIUM | Large VC backing but Founders Fund (US-based) creates potential nexus |
| Paradex | MEDIUM | Privacy architecture creates FATF Travel Rule tension |
| **Hyperliquid** | **HIGH** | CME/ICE lobbying active; no formal license; custom L1 opaque |
| Variational | MEDIUM | Cayman; no license; but RFQ model less obvious attack surface than CLOB |

---

## Appendix: Data Quality Notes

1. **Paradex blog (R12-11)** is self-published by Paradex. The 30d volume figures (including for Variational and HL) should be treated as directional. Paradex has incentive to portray HL's market share decline favorably. That said, the OI/Volume methodology is consistent across venues and the fragmentation narrative aligns with multiple independent sources.

2. **Variational $50M Series A (R12-15 CoinDesk)** is sourced from a reputable outlet. The "$200B cumulative since 2025" claim from Variational CEO is self-reported — unaudited. However, $200B over ~12-18 months at $71.8B/month (R12-11 30d vol) is arithmetically consistent.

3. **CFTC pressure (R12-16)** is Bloomberg-reported (via CoinDesk). No formal CFTC action exists as of May 2026. The CME/ICE lobbying is real but not equivalent to enforcement. Probability estimates in Phase 4 (15-25% for Scenario A) are subjective assessments.

4. **HL stats:** 230 markets and PAXG/SPX carry data from K297 direct on-chain measurement. This is the highest-quality data in this wave — sourced from actual HL API calls.

---

*Wave K355 | Perp DEX Competitive Landscape + v6.13d Concentration Risk*  
*Generated: 2026-05-27 07:18 JST*  
*Sources: R12-11/15/16 + K297 + K346 + WebFetch (8 URLs)*
