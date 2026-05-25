# External Findings Round 9 — TOP 3 Summary
**Generated**: 2026-05-25 JST  
**Context**: K246a v6.9 FINAL (OOS 12.69 / WF min 8.93). Architecture settled. Future lift = NEW orthogonal alpha.  
**R1-R9 cumulative**: 202 entries (R9 adds 20)

---

## TOP 3 for K254+ Implementation

---

### #1 — R9-01: AdaptiveTrend (arxiv:2602.11708)
**URL**: https://arxiv.org/abs/2602.11708  
**Source**: arXiv q-fin.PM, February 2026

**What it is**  
A framework combining 6-hour trend-following with monthly adaptive portfolio construction across 150+ crypto pairs. Three innovations: (1) dynamic trailing stop calibrated to intraday ATR regimes, (2) rolling monthly Sharpe-ratio-based asset selection with market-cap filtering, (3) asymmetric 70/30 long/short allocation justified by crypto's empirical positive drift. OOS 36-month backtest (2022-2024): Sharpe 2.41, MaxDD -12.7%, Calmar 3.18. Significantly outperforms TSMOM and equal-weight benchmarks.

**Why orthogonal to K246a**  
K246a (K198+K208+K226) uses FR/TVL/OHLCV time-series features at daily granularity. AdaptiveTrend is 6-hour trend signal × monthly cross-sectional selection — different time dimension, different signal type, different portfolio construction logic. All three are orthogonal to K246a's FR-prediction basis.

**K254 implementation plan**  
1. Compute 6H ATR-normalized trend score for all universe symbols.  
2. Monthly re-rank by rolling Sharpe ratio; keep top 30 symbols.  
3. Apply 70/30 long/short asymmetric allocation.  
4. Validate standalone (target Sharpe >1.5) → combine with K246a → WF test.  
5. Fix lookback for ATR and Sharpe period outside WF to prevent overfitting.  
6. WF window must be ≥1 month to avoid interference with monthly selection.

**WF stability note (K228/K233 lesson)**  
Monthly selection period must not be optimized inside WF. ATR window and Sharpe lookback are fixed at design time. Adding this strategy to K246a ensemble should be done as a separate WF test, not simultaneous with other changes.

---

### #2 — R9-08: Weekend Geopolitical Shock Session Effect (SSRN:6600698)
**URL**: https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6600698  
**Source**: SSRN, Boon Chuan Lim, April 18, 2026

**What it is**  
Empirical study using second-level BTC/ETH/SOL/XRP data across three geopolitical events: 2023 Hamas attack, April 2024 Iran-Israel exchange, and the 2026 Iran War. Key finding: for weekend-onset shocks (futures markets closed 30-43 hours), the single US Saturday-evening session accounts for 67%–126% of the cumulative price response. Asian and European sessions contribute minimally. The 2026 Iran War event showed BTC +530 bps cumulative, of which the first US session captured the majority. Prior 30-60 minute event study windows underestimate response by up to 5x or invert the sign.

**Why orthogonal to K246a**  
K246a has no session-time variable and no geopolitical event filter. The asymmetry in which trading session absorbs geopolitical shock is a completely new dimension. K246a's FR-based signals are most vulnerable to weekend gap events; this filter directly addresses K246a's biggest failure mode.

**K254 implementation plan**  
1. Subscribe to geopolitical headline feed (Reuters/AP API or GDELT project, free tier).  
2. Detect weekend-onset events: headline score >0.7 AND BTC 15-min return >1.5σ between Fri-Sun.  
3. Do NOT trade directional until US Saturday-evening session (22:00–02:00 EST) opens and confirms direction.  
4. Post-session direction becomes a 48-hour momentum filter; align K254 positions accordingly.  
5. Rule is generalizable (not event-specific), so overfitting risk is low.

**WF stability note**  
Only 3 reference events exist — insufficient for statistical optimization. Rule must be kept rule-based and generalizable. Do not fit session timing thresholds to historical events.

---

### #3 — R9-16: Dollar-Neutral Crypto Momentum (SSRN:6300843)
**URL**: https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6300843  
**Source**: SSRN, Kaston Chen & Jaslyn Chen, February 24, 2026

**What it is**  
Cross-sectional momentum strategy on Binance's ~50 most active crypto pairs. Daily cross-sectional regression of forward returns on past returns. Strategy: long top quartile + short bottom quartile ranked by momentum signal. Dollar-neutral construction removes market beta. Historical simulation: superior Sharpe ratio and drawdown profile vs. BTC buy-and-hold.

**Why orthogonal to K246a**  
K246a uses time-series FR/TVL signals to predict individual asset returns. Dollar-neutral cross-sectional momentum uses relative ranking across assets — a completely different signal dimension. The strategy is market-beta-neutral, so correlation with K246a (which has positive market beta through FR-long bias) should be low. Low correlation = meaningful Sharpe improvement when combined.

**K254 implementation plan**  
1. Universe: 50+ symbols (aligned with `feedback_symbol_universe_50.md` requirement).  
2. Daily: compute 1-day, 5-day, 20-day returns for all symbols; create composite momentum score.  
3. Rank all symbols; long top 20%, short bottom 20% with equal notional weighting.  
4. Rebalance daily at UTC 00:00.  
5. Validate correlation with K246a returns (<0.3 target) → combine → WF test.  
6. Lookback windows (1/5/20 day) fixed OUTSIDE WF — do not optimize inside WF.

**WF stability note (K228/K233 lesson)**  
The lookback period for momentum must be fixed before WF. In-WF lookback selection is a canonical overfitting trap in momentum strategies. Hold-out OOS period must span at least two full market regime cycles (bull+bear).

---

## Remaining 17 Findings Summary

| ID | Title | Actionable | Priority |
|---|---|---|---|
| R9-02 | Arkham Ultra API: エンティティ機関フロー（99%精度） | Y | High |
| R9-03 | Kalshi KXRECSSNBER/KXCPI チャネル別精度確定（R8-01深掘り） | Y | High |
| R9-04 | Hyperliquid 長尾FR裁定 年利20-60% APR | Y | High |
| R9-05 | CEX-DEX裁定の正体: ジャンプ拡散モデル（arxiv:2604.15973） | Y | High |
| R9-06 | 1秒サブスロット+535%増 ePBS事前準備（arxiv:2601.00738） | Y | Medium |
| R9-07 | ePBS SoK: Glamsterdam MEVフロー再編（arxiv:2506.18189） | N | Monitor |
| R9-09 | GEX Heatmap: ストライク×時間密度でTP/SL精密化（R8-04深掘り） | Y | High |
| R9-10 | Pump.funトークンローンチ→SOL注意ショック→ETH下落（R8-02精緻化） | Y | Medium |
| R9-11 | Deribit IV Term Structure: Backwardation 85H TTL・BTC-ETH乖離 | Y | High |
| R9-12 | Hidden Factor: TVL/MktCap比+Altcoin Season Index（arxiv:2601.07664） | Y | Medium |
| R9-13 | Polymarket 5分二値オプション: AI増強裁定 | Y | Medium |
| R9-14 | Pump.fun 36%収益シェア: SOLボラ先行指標 | Y | Medium |
| R9-15 | BTC機関フローサイクル: ハービング代替パラダイム（Amberdata） | Y | High |
| R9-17 | Nansen Smart Money: ドーマントウォレット活性化7-14日先行 | Y | High |
| R9-18 | Hash Ribbon AND ETFフロー: 4年サイクル崩壊後再校正（R8-08深掘り） | Y | Medium |
| R9-19 | EigenLayer LRT Stress: KelpDAO伝播経路実証（R8-20との組み合わせ） | Y | Medium |
| R9-20 | Amberdata Deribit テイカーフロー: Net Call/Put Buy Ratio機関確信度 | Y | High |

---

## Zero-Overlap Verification with R1-R8

The following mechanisms in R9 are confirmed absent from R1-R8:
- AdaptiveTrend 6H + monthly selection framework (R9-01): NEW
- Arkham Intel API v2 with UTXO institutional tracking (R9-02): NEW (R1-8 had no Arkham)
- CEX-DEX jump-diffusion model (R9-05): extension of R8-10 but distinct mechanism insight
- 1-second subslot ePBS impact quantification (R9-06): NEW
- ePBS SoK Glamsterdam roadmap (R9-07): NEW
- Weekend geopolitical session asymmetry (R9-08): NEW
- GEX Heatmap spatial distribution (R9-09): R8-04 had sign only, R9-09 adds spatial density
- Deribit IV term structure contango/backwardation signals (R9-11): NEW
- Crypto hidden factor model TVL/MktCap ratio (R9-12): NEW (R8 used TVL absolute)
- Polymarket 5-minute binary options (R9-13): R8-12 had general Polymarket, R9-13 is ultra-short-term specific
- Pump.fun revenue as SOL network health indicator (R9-14): NEW
- Institutional flow cycle replacing halving cycle (R9-15): extension of R8-17 but paradigm insight is new
- Dollar-neutral cross-sectional momentum (R9-16): NEW
- Nansen Smart Money dormant wallet activation (R9-17): NEW (R1-8 had no Nansen)
- Hash Ribbon AND-condition redesign post-halving cycle collapse (R9-18): R8-08 was standalone Hash Ribbon
- EigenLayer LRT systemic risk propagation path (R9-19): NEW (R8-20 was stETH only)
- Amberdata taker-flow Net Call/Put Buy Ratio (R9-20): NEW (R8-04 was GEX, different metric)
