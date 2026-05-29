# K498 Smart Router Profitability Quantification

**Wave:** K498  |  **Date:** 2026-05-30  |  **Generated:** 2026-05-30 03:35 JST

## Executive Summary

K434 smart router + K458 depth-aware allocator provide measurable and scalable profit lift across AUM tiers.

| AUM | Strategy A (HL-only) | Strategy E (7-venue) | Lift E vs A |
|-----|---------------------|---------------------|-------------|
| $10M | $0 | $22K | **+$22K** |
| $30M | $0 | $121K | **+$121K** |
| $100M | $0 | $1.03M | **+$1.03M** |
| $200M | $0 | $3.86M | **+$3.86M** |

> Strategy A baseline = 0 by definition; all values above represent absolute profit USDC/yr from routing optimization.

## Per-Strategy / Per-AUM Lift Table (USDC/yr)

| AUM | A (HL only) | B (HL+Bybit) | C (3-venue) | D (depth) | E (7-venue) |
|-----|-------------|--------------|-------------|-----------|-------------|
| $10M | $0 | $0 | $22K | $22K | $22K |
| $30M | $0 | $0 | $121K | $121K | $121K |
| $100M | $0 | $0 | $1.03M | $1.03M | $1.03M |
| $200M | $0 | $0 | $3.86M | $3.86M | $3.86M |

## Venue Models

| Venue | Maker Rebate (bps) | Taker Fee (bps) | Slip Coeff | Max OI% | Status | Effort (h) | Risk |
|-------|-------------------|-----------------|------------|---------|--------|-----------|------|
| HL | 0.3 | 4.5 | 10.0 | 5% | LIVE | 0 | LOW |
| Bybit | 1.0 | 3.2 | 8.0 | 5% | LIVE | 0 | LOW |
| OKX | 0.5 | 4.0 | 9.0 | 5% | SCAFFOLD-READY | 8 | LOW |
| Aevo | 0.0 | 5.0 | 15.0 | 5% | SCAFFOLD-READY | 40 | MEDIUM |
| dYdX_v4 | 0.0 | 5.0 | 12.0 | 5% | SCAFFOLD-READY | 60 | MEDIUM |
| Lighter | 0.0 | 5.0 | 18.0 | 3% | SCAFFOLD-READY | 80 | HIGH |
| Vertex | 0.0 | 5.0 | 18.0 | 3% | SCAFFOLD-READY | 80 | HIGH |

## Phase Activation ROI

| Phase | Label | Effort (h) | Risk | Ref AUM | Incremental Lift | ROI ($/h) |
|-------|-------|-----------|------|---------|-----------------|-----------|
| 1A | K456 OKX LIVE switch + BBO routing activation → St... | 8 | LOW | $30M | $121K | $15,100/h |
| 1B | K460 Aevo + dYdX LIVE → Strategy D (K458 allocator... | 100 | MEDIUM | $30M | $-1 | $-0/h |
| 2 | K465 Lighter + Vertex LIVE → Strategy E full 7-ven... | 160 | HIGH | $100M | $0 | $0/h |

## Detailed Results at $10M AUM

| Strategy | Order Size | Effective Cost (bps) | Lift (bps) | Annual Lift (USDC) | Rebate Lift | Slip Lift |
|----------|-----------|---------------------|------------|-------------------|-------------|-----------|
| A: HL-only (current v6.13d LIVE)... | $173K | 0.66 | 0.0000 | **$0** | $0 | $0 |
| B: HL primary + Bybit overflow (K... | $173K | 0.66 | 0.0000 | **$0** | $0 | $0 |
| C: 3-venue BBO: best-bid-offer se... | $173K | -0.51 | 1.1738 | **$22K** | $13K | $9K |
| D: Depth-aware allocator: HL + By... | $173K | -0.51 | 1.1739 | **$22K** | $13K | $9K |
| E: Full 7-venue optimal (K434 K45... | $173K | -0.51 | 1.1739 | **$22K** | $13K | $9K |

## Detailed Results at $100M AUM

| Strategy | Order Size | Effective Cost (bps) | Lift (bps) | Annual Lift (USDC) | Rebate Lift | Slip Lift |
|----------|-----------|---------------------|------------|-------------------|-------------|-----------|
| A: HL-only (current v6.13d LIVE)... | $1.73M | 9.33 | 0.0000 | **$0** | $0 | $0 |
| B: HL primary + Bybit overflow (K... | $1.73M | 9.33 | 0.0000 | **$0** | $0 | $0 |
| C: 3-venue BBO: best-bid-offer se... | $1.73M | 3.89 | 5.4384 | **$1.03M** | $133K | $899K |
| D: Depth-aware allocator: HL + By... | $1.73M | 3.89 | 5.4384 | **$1.03M** | $133K | $899K |
| E: Full 7-venue optimal (K434 K45... | $1.73M | 3.89 | 5.4384 | **$1.03M** | $133K | $899K |

## Activation Roadmap

### Phase 1A: K456 OKX LIVE switch + BBO routing activation → Strategy C

- **Timeline:** 1 month
- **Venues Added:** OKX
- **Strategy Upgrade:** B → C
- **Effort:** 8h
- **Risk:** LOW

Current K434 default routes to HL first (Strategy B = overflow only). This gives $0 lift because HL depth cap ($9M avg) is never hit at current AUM. True lift comes from activating BBO selection: route to BEST-SCORED venue per order rather than always defaulting to HL. Bybit VIP5 maker rebate 1.0 bps >> HL GOLD 0.3 bps = 0.7 bps rebate advantage. OKX VIP1 adds 3rd venue option and 0.5 bps rebate. Two concurrent changes: (1) enable OKX in config, (2) switch K434 routing from 'HL_OVERFLOW' to 'BBO_SELECT' mode. 8h effort total (config + paper-trade validation).

**Steps:**
1. Set OKX enabled=true in smart_router_config.json trading section
1. Switch smart_router.py routing mode from HL_OVERFLOW to BBO_SELECT (select_best_venue already implements this — ensure it is called per order, not just for overflow)
1. Validate OKX API key permissions (read + trade)
1. Run 48h paper-trade comparing Strategy C vs B cost_bps via decision log
1. Flip live switch; monitor smart_router_decisions.jsonl for routing events

### Phase 1B: K460 Aevo + dYdX LIVE → Strategy D (K458 allocator) — capacity scaling

- **Timeline:** 3 months
- **Venues Added:** Aevo, dYdX_v4
- **Strategy Upgrade:** C → D
- **Effort:** 100h
- **Risk:** MEDIUM

At current AUM ($10-30M), Strategy C and D have identical lift because Bybit alone ($14.2M cap) absorbs all order flow. Phase 1B value is CAPACITY INSURANCE: raises AUM ceiling before Bybit depth becomes binding. At $100M AUM+ with Aevo+dYdX, total OI capacity grows by ~$280M (BTC headroom alone), preventing forced HL concentration. Secondary value: 1h funding cycle on Aevo/dYdX creates FR arbitrage opportunities not available on 8h venues. Aevo: api.aevo.xyz trading keys needed + 1h funding cycle normalization. dYdX v4: Cosmos SDK signing required (significant engineering). Activate after Phase 1A 30d track record.

**Steps:**
1. Aevo: configure trading keys + activate post_only_order_manager
1. dYdX v4: implement Cosmos SDK signing module
1. K458 allocator: integrate with K280 live_fetch.py order flow
1. 30d parallel paper-trade vs Strategy C
1. Deploy both venues simultaneously (atomic config switch)

### Phase 2: K465 Lighter + Vertex LIVE → Strategy E full 7-venue — $200M+ scale

- **Timeline:** 6 months
- **Venues Added:** Lighter, Vertex
- **Strategy Upgrade:** D → E
- **Effort:** 160h
- **Risk:** HIGH

Lighter (zkEVM) and Vertex (AMM hybrid) add ~$80M OI headroom (BTC: $80M combined). Both require new signing modules (zkEVM proof / Vertex Gateway). Conservative tier (3% OI cap vs 5% established). At $200M AUM where per-order size reaches $3.5M, all 7 venues together provide necessary distribution to maintain slippage < 10 bps. Without Phase 2, $200M AUM would require concentrating >20% of BTC OI at Bybit alone = high slippage regime. Activate after Phase 1B 60d track record. Reconciliation across 7 venues requires unified P&L reporting.

**Steps:**
1. Lighter: deploy zkEVM signing module (mainnet.zklighter.elliot.ai)
1. Vertex: implement Gateway POST /execute signing
1. Expand reconciliation loop to 7 venues
1. 60d paper-trade Phase E vs D
1. Full Phase E activation with kill-switch back to Strategy D

## Risk Registry

### R1: Venue API instability (Aevo / Lighter newer)

- **Probability:** MEDIUM
- **Impact:** MEDIUM
- **Mitigation:** K434 fallback_order list: if venue API returns error, router absorbs on next-best venue within 1s budget. Conservative min_depth_usd gates prevent routing to venues with insufficient depth. Monitor uptime via venue_uptime_pct thresholds; auto-disable venue if uptime < 95% over 7d window.

### R2: Cross-venue coordination latency (7-venue)

- **Probability:** HIGH
- **Impact:** LOW
- **Mitigation:** K434 1s fill budget. HL+Bybit+OKX legs complete in <150ms combined (worst case 50ms+coord). Aevo/dYdX add ~80-120ms each. 7-venue sequential risk: 30+40+50+80+120+150+150 = 620ms — within 1s budget. For large orders: parallelize venue submissions with asyncio (planned K499+).

### R3: Funding rate mismatch across venues

- **Probability:** MEDIUM
- **Impact:** HIGH
- **Mitigation:** Aevo/dYdX use 1h funding cycles (vs HL/Bybit/OKX 8h). K460 config: funding_normalization_factor=8 applied before comparison. Risk: if 1h rate spikes during settlement window, multi-venue position has inconsistent FR exposure. Mitigation: never split same symbol across 8h-cycle and 1h-cycle venues simultaneously. Route per-symbol to single venue.

### R4: Reconciliation complexity (7 venues)

- **Probability:** HIGH
- **Impact:** MEDIUM
- **Mitigation:** smart_router_decisions.jsonl logs all routing decisions. Each venue allocation tracked separately in multi_account_orchestrator.py. K485 multi-account playbook covers HL+Bybit already. dYdX/Lighter/Vertex require additional reconciliation module. Risk accepted for Phase 2; Phase 1 (HL+Bybit+OKX) is manageable.

### R5: HL concentration risk residual (K357/MEMORY.md)

- **Probability:** LOW
- **Impact:** HIGH
- **Mitigation:** v6.13d HL 57.5% of AUM; hard cap 65%. Smart router actively reduces HL concentration by routing overflow to Bybit/OKX. At $30M+ AUM, router becomes mandatory to stay within cap. concentration_caps in config enforced per K434 filter_by_concentration_caps(). Monitor HL% in dashboard daily.

### R6: Depth model calibration error

- **Probability:** MEDIUM
- **Impact:** MEDIUM
- **Mitigation:** K458 FALLBACK_OI_USD are conservative estimates from public data (2026-05). Live OI fetchers for HL/Bybit/OKX are implemented (K458 Phase 1). Aevo/dYdX/Lighter/Vertex use fallback until live API confirmed. Slippage model linear (conservative). Actual slippage may be lower for post-only orders in passive FR capture (not aggressive market orders). Re-calibrate every 30d using decision log actual vs estimated.

## Decision / Recommendation

**Primary:** Phase 1A: Activate K456 OKX + switch to BBO routing mode immediately (8h effort, LOW risk, $121K/yr lift at $30M, $1.03M/yr at $100M, ROI $15,100/hr)

**Secondary:** Phase 1B: Aevo+dYdX activation for AUM capacity insurance ($200M+ ceiling); activate after Phase 1A 30d track record

**Context:** K434 current B (HL-overflow mode) gives ZERO lift. The routing logic must be switched from 'HL_DEFAULT' to 'BBO_SELECT' to capture the Bybit 1.0 bps rebate advantage. This is a config + routing mode change (not new venue integration). The K434 score_venue() function already implements BBO selection — it just needs to be called per order as the primary routing decision, not just for overflow handling.

---

*Generated by wave_k498_smart_router_profit.py (K339 pattern)*
*Elapsed: 0.0s*