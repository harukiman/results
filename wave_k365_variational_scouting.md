# K365: Variational API Scouting + K297' Migration Feasibility
**Generated:** 2026-05-26 22:57 UTC  |  **Wave:** K365  |  **Context:** K355 Priority 2, v6.13d HL concentration risk

---

## Executive Summary

| Item | Finding |
|------|---------|
| Variational API (read) | **PUBLIC** — no auth required |
| Variational API (trading) | **NOT YET LIVE** — confirmed May 2026 |
| FR observable | **YES** — returned directly by `/metadata/stats` |
| K355 OLP-obscured claim | **INCORRECT** — FR is transparent numeric field |
| XAU (Gold) OI | $21.9M — adequate for K297-sized positions |
| XAG (Silver) OI | $4.1M — thin but passable for small allocation |
| CL (WTI) OI | $4.9M — FR negative (shorts earn) |
| COPPER OI | $1.6M — FR = 0%, no carry signal |
| Migration verdict | **DEFER** until trading API ships |
| Primary opportunity | XAU FR arb + XAG/CL expansion (K297'') |
| Estimated activation | Q3-Q4 2026 |

---

## Phase 1: API Discovery

### Endpoints

| Endpoint | Auth | Description |
|----------|------|-------------|
| `GET /metadata/stats` | None (public) | Platform stats + all listings (mark, OI, FR, spread, quotes) |
| Trading API | NOT YET LIVE | Position open/close — ETA unknown |

**Base URL:** `https://omni-client-api.prod.ap-northeast-1.variational.io`

**Rate limits:** 10 req/10s per IP | 1,000 req/min global

**Response format:** JSON; numerics returned as strings (precision preservation)

### Funding Rate Formula

```
F = P + clamp(r − P, −0.0005, 0.0005)

Where:
  P = Average Premium Index (sampled every 60s)
  r = fixed interest rate = 0.00125%/hour
  clamp limits interest-rate adjustment to ±0.05 bps per interval
  max cap: 2%/hour (extreme conditions)
```

**Settlement:** Variable 1-8h; RWA instruments use **4h intervals** (aligns Bybit/Binance schedule).

**Key correction vs K355:** K355 asserted 'OLP-embedded carry model obscures FR signal.'
Live API verification shows FR is **transparently returned** as a numeric field per listing.
OLP aggregates liquidity sources but does not obscure the funding calculation or reporting.

---

## Phase 2: Platform Stats (Live Snapshot)

- **24h Volume:** $0.94B
- **Cumulative Volume:** $227.2B (confirmed: $200B+ milestone recently crossed)
- **TVL:** $108.3M
- **Open Interest:** $996M
- **Markets Listed:** 462

---

## Phase 2: RWA Instrument Catalog

| Ticker | Name | Mark Price | 24h Volume | OI Total | Long% | Spread (base) | FR (ann%) | Carry Grade |
|--------|------|-----------|-----------|---------|-------|--------------|----------|------------|
| **XAUT** | Tether Gold | $4,492.87 | $3.57M | $26.6M | 78% | 6.41 bps | -71.1% | **GOOD** |
| **XAU** | Gold | $4,504.51 | $26.38M | $21.9M | 52% | 3.02 bps | +560.0% | **CAUTION** |
| **PAXG** | PAX Gold | $4,499.46 | $0.56M | $15.0M | 22% | 6.42 bps | +239.8% | **CAUTION** |
| **CL** | WTI Crude Oil | $93.40 | $10.09M | $4.9M | 77% | 4.42 bps | -247.0% | **CAUTION** |
| **XAG** | Silver | $77.12 | $7.04M | $4.1M | 55% | 4.73 bps | +0.0% | **MARGINAL** |
| **COPPER** | Copper | $6.43 | $1.74M | $1.6M | 63% | 5.07 bps | +0.0% | **REJECT** |

### Liquidity Depth: $100K Quotes

| Ticker | Base Spread | $100K Spread | Depth Assessment |
|--------|------------|-------------|-----------------|
| XAUT | 6.41 bps | 7.66 bps | GOOD — bid=4495.4 ask=4498.84 |
| XAU | 3.02 bps | 4.24 bps | GOOD — bid=4507.94 ask=4509.85 |
| PAXG | 6.42 bps | 15.60 bps | ACCEPTABLE — bid=4501 ask=4508.02 |
| CL | 4.42 bps | 7.21 bps | GOOD — bid=93.4208 ask=93.4881 |
| XAG | 4.73 bps | 5.96 bps | GOOD — bid=77.186 ask=77.232 |
| COPPER | 5.07 bps | 46.98 bps | WIDE — bid=6.41234 ask=6.44254 |

---

## Phase 3: K297-Style Carry Strategy Feasibility

### Funding Rate Observability: CONFIRMED

All instruments return funding rate directly from the public API endpoint.
No OLP obfuscation. FR formula matches standard perpetual funding (premium index + interest rate clamp).

### Carry Feasibility by Instrument

#### XAUT — Tether Gold (GOOD)
- **FR:** -71.1% ann (-0.0325% per 4h)
- **OI:** $26.6M | **Vol 24h:** $3.57M
- **Notes:** FR -71.1% ann — viable carry target; OI $26.6M — passes G6 liquidity gate for <$5M positions; Spread 6.4bps tight — acceptable transaction cost

#### XAU — Gold (CAUTION)
- **FR:** +560.0% ann (0.2557% per 4h)
- **OI:** $21.9M | **Vol 24h:** $26.38M
- **Notes:** Very high FR (560.0% ann) — likely unsustainable, snapshot artifact; OI $21.9M — passes G6 liquidity gate for <$5M positions; Spread 3.0bps tight — acceptable transaction cost; XAU: native gold perp — direct RWA (not wrapped token); primary HL PAXG analogue for carry arb

#### PAXG — PAX Gold (CAUTION)
- **FR:** +239.8% ann (0.1095% per 4h)
- **OI:** $15.0M | **Vol 24h:** $0.56M
- **Notes:** Very high FR (239.8% ann) — likely unsustainable, snapshot artifact; OI $15.0M — passes G6 liquidity gate for <$5M positions; Spread 6.4bps tight — acceptable transaction cost; PAXG on Variational: tokenized gold (PAX) — differs from native XAU contract; cross-venue arb complex

#### CL — WTI Crude Oil (CAUTION)
- **FR:** -247.0% ann (-0.1128% per 4h)
- **OI:** $4.9M | **Vol 24h:** $10.09M
- **Notes:** Very high FR (-247.0% ann) — likely unsustainable, snapshot artifact; OI $4.9M — passes G6 liquidity gate for <$5M positions; Spread 4.4bps tight — acceptable transaction cost; CL WTI: HL does NOT list crude oil — pure expansion instrument; negative FR = shorts earn

#### XAG — Silver (MARGINAL)
- **FR:** +0.0% ann (0.0000% per 4h)
- **OI:** $4.1M | **Vol 24h:** $7.04M
- **Notes:** Near-zero FR (< 2% ann) — minimal carry income on snapshot; OI $4.1M — passes G6 liquidity gate for <$5M positions; Spread 4.7bps tight — acceptable transaction cost; XAG Silver: HL does NOT list silver — pure expansion instrument, not migration

#### COPPER — Copper (REJECT)
- **FR:** +0.0% ann (0.0000% per 4h)
- **OI:** $1.6M | **Vol 24h:** $1.74M
- **Notes:** Near-zero FR (< 2% ann) — minimal carry income on snapshot; OI $1,610,719 < G6 min $2,000,000 — liquidity thin; Spread 5.1bps tight — acceptable transaction cost; COPPER: HL does NOT list copper — pure expansion; zero FR on snapshot = no carry signal today

### Comparison vs HL K297' Baseline

| Metric | HL K297' (K342/K343) | Variational XAU |
|--------|---------------------|-----------------|
| Ann Return (est) | 10.3% | 168.0% (30% haircut) |
| Sharpe | 12.59 | Unknown (short Variational history) |
| Max DD | 0.0% | Unknown |
| FR Interval | 1h (8h computed) | 4h |
| FR Observable | Yes | **Yes (confirmed)** |
| Trading API | Live | NOT YET LIVE |

---

## Phase 4: Cross-Venue Arbitrage (K208 Style)

### Intra-Variational: XAU vs PAXG

- **XAU mark:** $4,504.51 | **PAXG mark:** $4,499.46
- **Price spread:** +0.1122% (XAU - PAXG)
- **FR spread (ann):** +320.2% (XAU FR +560.0% - PAXG FR +239.8%)
- **Note:** XAU (native gold) vs PAXG (PAX token) on same venue: FR spread 320.2% ann. Intra-Variational arb: long cheaper FR, short pricier FR. Requires trading API + sufficient margin isolation.

### Cross-Venue: HL PAXG vs Variational XAU

- **HL PAXG FR (K342 baseline):** 8.0% ann (estimated)
- **Variational XAU FR (live snapshot):** +560.0% ann
- **Cross-venue FR spread:** +552.0% ann
- **Settlement currency:** USD (Arbitrum USDC) vs USD (HL USDC)
- **Bridge risk:** Arbitrum → HL bridge required; ~10min finality, gas cost ~$1-3
- **Feasibility:** LOW — FR is snapshot only; cross-venue arb requires persistent FR tracking pipeline (cf. K358 for Drift)

### Required Infrastructure for K366

1. Variational FR polling daemon (similar to K358 drift_fr_monitor.py)
1. HL PAXG FR baseline from live HL API (exists in data/funding_* cache)
1. Position sizing logic across two chains
1. Arbitrum USDC bridge/withdrawal module

**Estimated effort:** 2-3 waves (K366-K368) if Variational trading API ships

---

## Phase 5: K297' Migration Scenarios

**Reference:** HL exposure = 57.5% AUM; K297' = 20% allocation; target HL < 50% (−7.5pp gap)

### Scenario A Full Migration
**K297' moves 100% from HL PAXG/SPX → Variational XAU**

| Metric | Value |
|--------|-------|
| HL Exposure After | 37.5% (was 57.5%) |
| HL Concentration Reduction | 20.0pp |
| Variational Allocation | 20% |
| Est. Ann Return | 168.0% |
| Operational Complexity | HIGH |

**Risks:**
- Variational trading API NOT YET LIVE (confirmed May 2026)
- XAU FR mechanism (4h intervals) differs from HL 1h intervals
- RFQ model: no persistent order book → execution latency unknown
- Smart contract settlement on Arbitrum: gas cost + bridge delay
- SINGLE new venue dependency replaces single old dependency — zero diversification gain

**Verdict:** DEFER — trading API unavailable; venue swap does not diversify

### Scenario B Split 10 10
**K297' splits: 10% HL PAXG/SPX + 10% Variational XAU**

| Metric | Value |
|--------|-------|
| HL Exposure After | 47.5% (was 57.5%) |
| HL Concentration Reduction | 10.0pp |
| Variational Allocation | 10% |
| Est. Ann Return | 168.0% |
| Operational Complexity | VERY HIGH |

**Risks:**
- Requires two simultaneous live deployments on different chains/venues
- Variational trading API not available — cannot automate entries/exits
- Correlation of carry streams: XAU vs PAXG very high (both gold) — limited diversification benefit from carry stream itself
- Hedging complexity: two gold long positions with different FR mechanics

**Verdict:** DEFER — trading API blocker; monitor when API ships

### Scenario C Expansion K297 Prime
**K297' stays 20% HL; ADD K297'' = 10% Variational (XAG + CL focus)**

| Metric | Value |
|--------|-------|
| HL Exposure After | 57.5% (was 57.5%) |
| HL Concentration Reduction | 0.0pp |
| Variational Allocation | 10% |
| Est. Ann Return | 37.0% |
| Operational Complexity | VERY HIGH |

**Risks:**
- Does NOT reduce HL concentration (does not address K355 goal)
- Variational trading API unavailable
- XAG FR = 0% on snapshot — no carry signal today
- CL FR = -26.7% ann (shorts earn) — inverted carry, different strategy logic needed

**Verdict:** LOW VALUE NOW — XAG/CL expansion interesting but FR signals weak; revisit when XAG/CL FR normalizes and trading API ships

---

## Phase 6: K266 Strict Gates

| Gate | Pass/Fail | Notes |
|------|-----------|-------|
| **G3_orthogonality** | ✗ FAIL | HL PAXG vs Variational XAU: both track gold spot (~0.99 price correlation). Carry streams may decorrelate due to differe... |
| **G6_trade_execution** | ✗ FAIL | XAU OI $21.9M passes minimum; spread 3.02bps tight. BLOCKER: trading API unavailable → execution automation impossible →... |
| **G7_ann_return** | ✓ PASS | Snapshot XAU FR = 560.0% ann (4h interval). Single-day snapshot; Variational launched 2025, short FR history. 30% haircu... |

**Overall:** FAIL  |  **Blocking:** G3_orthogonality, G6_trade_execution  |  **Decision:** DEFER — G6 blocked by trading API unavailability; G3 fails for standalone carry

---

## Phase 7: Decision

## VERDICT: **DEFER**

**Trigger Condition:** Variational trading API becomes publicly available

**Estimated Activation:** Q3-Q4 2026 (Dragonfly $50M raise May 2026, 100+ RWA markets planned summer 2026)

### Value If Activated

- **Primary use:** XAU/PAXG cross-venue FR arb (HL PAXG long, Variational XAU short if FR inverts)
- **Secondary use:** XAG + WTI expansion (K297'' new instruments, not HL migration)
- **Estimated incremental return:** 3-8% ann (conservative; based on FR spread observable today)
- **Concentration reduction:** Scenario B split achieves 10pp HL reduction when trading API live

### Immediate Actions (No Trading API Required)

- Build Variational FR polling daemon (reuse K358 drift_fr_monitor.py pattern) — 0.5 wave
- Add XAU + PAXG FR to report.html live dashboard
- Monitor for trading API announcement from Variational

### Reject Conditions

- FR becomes non-observable (API structure changes to opaque OLP model)
- XAU/CL liquidity (OI) drops below $2M
- Regulatory action against Variational (Cayman incorporation; monitor)

---

## Key Findings vs K355 Claims

| K355 Claim | K365 Verification | Status |
|------------|-------------------|--------|
| OLP-embedded carry obscures FR signal | FR is transparent numeric in public API | **INCORRECT — corrected** |
| Variational is HIP-3 RWA competitor | Yes: XAU, XAG, CL, COPPER all live | **CONFIRMED** |
| $200B cumulative volume | Live API shows $227B cumulative | **CONFIRMED + UPDATED** |
| Gold, Silver, Copper, WTI available | XAU, XAG, CL, COPPER confirmed live | **CONFIRMED** |
| HL lacks XAG and WTI | No XAG or WTI on HL; Variational advantage | **CONFIRMED** |

---

*K339 security note: No production scripts modified. No new packages used.*
*Generated by wave_k365_variational_scouting.py | 2026-05-26 22:57 UTC*
