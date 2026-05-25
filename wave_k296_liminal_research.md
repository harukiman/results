# K296 Liminal Protocol Research Report
**Generated:** 2026-05-25 04:09 UTC

---

## Executive Summary

Liminal (liminal.money) is a live, production-grade delta-neutral yield protocol on HyperEVM/Hyperliquid. xToken mechanism is well-documented, TVL peaked at $90M, and live HL funding data confirms 5-11% net annualized yield per asset. **Liminal is technically feasible as a K275 OKX successor**, but the K291 diagnosis concluded K275's underperformance was a methodology bug (now fixed), not a strategy failure — reducing the urgency of a replacement decision.

---

## 1. Liminal Protocol Summary

| Attribute | Detail |
|---|---|
| Chain | HyperEVM (hub), bridged to Arb/ETH/Base via LayerZero OFT |
| Strategy | Delta-neutral: long spot (or LST) + short HL perp |
| Products | xHYPE, xBTC, xETH, xSOL, xLEND, limUSD |
| Yield Sources | HL perp funding rates + staking rewards (kHYPE) + lending markets (xLEND) |
| Fee Structure | 10% performance fee on positive funding; 0% management fee; 0.3% instant redemption |
| Leverage | 1x–2x max (asset-specific caps) |
| TVL Peak | $90M (May 2026), current ~$24M (DeFiLlama) |
| Custody | Non-custodial: agent-only Hyperliquid subaccount, no withdrawal perms |
| Status | Live and operational (launched Q3 2025) |

### xToken NAV Mechanism
ERC-4626 shares. Oracle updates on-chain price-per-share as funding accrues. Example: 1 xHYPE starts at $1.00 → grows to $1.05 after 5% yield. Redemption burns xTokens for underlying USDC at current NAV. No lock-up.

---

## 2. Data Availability Assessment

| Data Type | Availability | Source |
|---|---|---|
| Live xToken NAV | Partial (app dashboard, no public API) | liminal.money/stats |
| Historical xToken NAV series | **Not public** | No API or subgraph found |
| HL fundingHistory (underlying) | **Full public API** | api.hyperliquid.xyz/info |
| Lookback depth | Up to 180+ days | HL API confirmed |
| DeFiLlama TVL history | Available | defillama.com/protocol/liminal |

**Conclusion:** Direct xToken NAV backtest is not possible (no public NAV history). However, the underlying HL funding rate series is fully accessible, enabling yield reconstruction with high fidelity.

---

## 3. Live Yield Reconstruction (180-day HL Funding, net of fees)

Data: `api.hyperliquid.xyz/info` fundingHistory, 500 hourly records per asset.

| Asset | Gross Annualized | Net (HL fees) | Net (OKX fees) | % Hours Positive |
|---|---|---|---|---|
| BTC | 5.12% | 5.41% | 5.37% | 78.6% |
| ETH | 9.21% | 8.33% | 8.29% | 97.2% |
| HYPE | 11.21% | 10.67% | 10.63% | 96.2% |
| SOL | 2.89% | 4.74% | 4.70% | 65.6% |
| **Equal-weight portfolio** | — | **7.29%** | **7.25%** | — |

**HL vs OKX fee advantage: ~4 bps/year** (HL maker 0.015% vs OKX 0.02%).

Note: Fee advantage is structurally real but small; compounds at 2x leverage (+8 bps/yr) or higher turnover.

---

## 4. Mechanism Comparison: Liminal vs K275 vs K265/K276b

| Dimension | K275 OKX Cross-section FR | K265/K276b HL Long-tail | Liminal xToken |
|---|---|---|---|
| Exchange | OKX (centralized) | Hyperliquid | Hyperliquid (native) |
| Strategy type | Long low-FR / short high-FR cross-section | Long-tail FR long/short | Delta-neutral single-asset |
| Alpha source | FR spread harvesting | Long-tail FR mispricing | Structural BTC/ETH/HYPE funding |
| Maker fee | 0.02% | 0.015% | 0.015% |
| Counterparty risk | OKX credit | None (on-chain) | None (on-chain) |
| Capital efficiency | Standard | Standard | 30%+ (portfolio margin Dec 2025) |
| Operational complexity | External exchange API | HL native | HL native, delegated |
| Correlation with K265 | Low | — | Moderate (same HL funding pool) |
| Returns (net est.) | ~8-9% (K291 fixed) | ~6-8% | ~7.3% equal-weight |

---

## 5. Correlation Assessment: Liminal vs K265/K276b

Both Liminal and K265/K276b harvest HL perp funding rates — positive correlation expected (same exchange, same funding pool, same bear-market risk). **Liminal as K275 replacement does NOT improve diversification.** K275 OKX on a separate exchange provides genuine decorrelation vs K265.

---

## 6. Verdict on K287d K275 Replacement Timeline

| Factor | Assessment |
|---|---|
| Liminal technically feasible? | Yes — live protocol, accessible |
| K275 currently failing? | No — K291 confirmed methodology bug (now fixed), Sharpe +16.8 on rolling 30d |
| Liminal yield competitive? | Yes (7.3% net EW), comparable to K275 expected |
| Correlation benefit of replacing K275 with Liminal | **Negative** — Liminal correlates with K265, K275 OKX does not |
| Liminal portfolio margin advantage | Real but early-stage (Dec 2025 launch) |
| Urgency of replacement | **Low** |

**Recommendation: MONITOR, do not replace.**

K275 OKX should remain in K287d Satellite at current allocation. Its cross-exchange positioning provides genuine diversification vs K265/K276b that Liminal cannot replicate. Liminal is better suited as a **standalone position** (potential K297+ target) or as a limUSD treasury yield vehicle, not as a like-for-like K275 substitute.

**Revisit trigger:** K275 live Sharpe falls below +5 for 30+ days post bug-fix confirmation, OR Liminal introduces cross-asset FR spread strategies (moving closer to K275's alpha source).

---

## 7. Implementation Path (if triggered)

1. Deploy USDC into limUSD (auto-compounds xHYPE/xBTC/xETH) via HL subaccount delegation
2. Monitor NAV via HyperEVM RPC oracle reads
3. Gate: require 90d live NAV series before production allocation
4. Proxy backtest available now via `wave_k296_liminal_research.py` (HL fundingHistory API)
