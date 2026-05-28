# Wave K418: R10/R11 Untouched +1 Backlog Cleanup

**Date:** 2026-05-25 (JST)  
**Phase:** R14 Round 3+1+1 (Top-3 done: K396/K403/K412 + K400 MED + K418 R10/R11)

---

## Phase 1: Untouched Inventory Scan

Reviewed all R10 (20 items) and R11 (20 items) external findings.

**Classification:**
- **Already scheduled:** K339 (R11-16), K340 (R11-17), K337 (R11-07 MONITOR)
- **Deferred with gates:** K341-K342 (7 items, explicit triggers documented)
- **Backlog surviving:** 12 items (K342_range / K343_range / K345_range targets)
- **Untouched high-value:** 8+ items identified below

---

## Phase 2: Top Untouched Candidates

| Rank | ID | Title | Actionability | Current Status | Redundancy |
|------|----|----|---|---|---|
| 1 | **R10-010** | BTC negative FR April 2026 = K275 root cause | **HIGH** | UNTOUCHED | None — novel regime shift |
| 2 | R10-014 | ICE OKX $25B: K275 sunset roadmap | **HIGH** | UNTOUCHED | Overlaps with K303 OKX monitoring |
| 3 | R11-04 | Ripple Prime + HL RWA commodities | **HIGH** | UNTOUCHED | Complements K297 universe expansion |
| 4 | R10-013 | dYdX v4 MEV Cosmos: K270 robustness | **MED** | UNTOUCHED | K270 validation only |
| 5 | R11-13 | HMM 3-state Bayesian regime | **MED** | DEFERRED (gate: misspec evidence) | Regime filter alternative to K315-K341 |
| 6 | R10-009 | HIP-4 zero-fee binaries: fee tier acceleration | **MED-LOW** | UNTOUCHED | Novel but secondary |
| 7 | R10-015 | OKX VIP tier cuts + ELP halving | **MED** | UNTOUCHED | Market maker exit signal |
| 8 | R11-01/02 | HIP-3 $1.74B RWA + S&P DJI license | **MED** | UNTOUCHED | K297 universe validation |

---

## Phase 3: Item Selected: R10-010

**ID:** R10-010  
**Title:** BTC Funding Rates Turn Most Negative Since 2023 — Crowded Shorts Signal Tactical Bottom

### Why Deferred Originally
- Discovered April 2026, late in R10 cycle
- Required regime gate design for K275 (which was in-flight via K303)
- K275 already showing -3.55 Sh live; negative carry was the hypothesis not yet quantified

### What's Changed Since
1. **K275 live data**: -3.55 Sh confirmed as structural (not transient)
2. **Production state**: v6.13d deployed; K303 OKX monitoring live; K275 NOT sunset yet
3. **Evidence accumulation**: R10-010 quantifies the regime shift; RHO Trading mean-reversion study (R10-016) provides 22-day convergence horizon and liquidation safety parameters

### Updated Relevance Assessment

**Relevance: HIGH**

**Rationale:**
- R10-010 identifies the ROOT CAUSE of K275 underperformance: March 2026 flip from positive to negative carry regime
- Current 30-day BTC funding rate avg <-0.001% is the most negative since 2023
- K275 was architected for positive-carry; negative carry inverts the logic entirely (shorts collect, not longs pay)
- This is NOT a temporary arb compression—it's a regime shift requiring architectural decision

### Concrete Recommendation

**Decision: DEFER with explicit trigger + conditional ACT window**

**Trigger:**
- IF 30-day BTC funding rate avg returns to >+0.001% for 3 consecutive days → **ACT NOW** (K419 wave)
- IF K275 live Sharpe recovers to >20 before next governance wave → **MONITOR** (regime may be self-correcting)
- IF BTC/Binance-OKX spread remains below 1% mean for 14 days → **ACT NOW** (cross-venue arb may dominate carry)

**If triggered to ACT:** K419 proposal

Scope: Add regime gate to K275 production config:
- Gate: Disable K275 long-short when 30-day FR avg < -0.001%
- Fallback: Switch to short-long (reverse carry, collect negative FR) when regime flips
- Validation: 14-day paper-trade window on opposite position

**Why NOT ACT now (wait for gate):**
1. K275 already live with -3.55 Sh; immediate redesign risk during negative regime
2. Short reversal may trap on regime re-flip (high whipsaw risk)
3. Better to observe trigger: if carry normalizes, gate never activates; if persists, gate saves capital

---

## Phase 4: Internal Tracking Update

**Updates to task_pipeline.json:**

```json
{
  "deferred": [
    {
      "id": "R10-010",
      "topic": "BTC negative FR regime gate for K275",
      "trigger": "30-day BTC FR avg > +0.001% for 3d OR K275 Sharpe > 20",
      "drop": "2026-08-15",
      "wave_if_triggered": "K419",
      "new": true
    }
  ]
}
```

**Rationale for deferral order:**
- K400 (Ondo) completes this wave
- K418 (this wave) adds R10-010 gate to deferred list
- K419 (proposed next) is conditional on R10-010 trigger firing

---

## Summary

**Item picked:** R10-010 (BTC negative FR April 2026)  
**Decision:** DEFER with HIGH-priority trigger  
**Rationale:** Root cause validated; regime shift requires gate design; better to wait for normalization signal than redesign live production  
**Next action:** Monitor BTC 30-day FR avg; K419 launch if trigger fires  
**Effort if acted:** ~1 sonnet wave (config + 14d paper-trade + gate logic)

---

*End K418 backlog cleanup*
