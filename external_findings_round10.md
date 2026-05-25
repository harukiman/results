# External Findings Round 10 — Systematic Alpha Discovery
**生成日時**: 2026-05-25 JST
**累計**: R1-R9: 202件 | R10: 20件 | 総計: 222件
**R10 戦略フォーカス**: Multi-exchange arb refinement | dYdX deepening | OKX FR sustainability | LRT/restaking 2026 | Solana perp | HL ecosystem | 2026 H1 academic

---

## Executive Summary

R10の最重要発見は3点:

1. **K275 -3.55 Sh の根本原因が特定された**: 2026年3月のBTC FR sign反転(positive→negative carry) [R10-010] と、2025年12月のBoros OKX統合による三会場アービトラージ資本流入 [R10-002] がOKX FR プレミアムを構造的に消去した。K275の即時対策: 30日平均FR < -0.001% でのレジームゲート追加。

2. **HL HIP-3 RWA perp $2.6B OI達成**: 全HL取引量の47.1%がRWA perp [R10-008]。equity cash-and-carry arbitrage(HL equity perp short + brokerage stock long)という新戦略カテゴリが誕生。weekend gap riskが唯一の制約。

3. **Drift崩壊→Jupiter Perp台頭**: 2026年4月Drift $285M exploit [R10-007] でSolana perp DEXの重心移動が完了。K293+ SolanaシグナルはJupiterを参照基準に変更必須。

---

## Top 3 Actionable for K293+

### #1 K275 Regime Gate (最優先実装)
- **What**: 30日平均FR < -0.001% 時にK275を無効化するレジームフィルター追加
- **Evidence**: R10-010 (BTC FR most negative since 2023, March 2026) + R10-002 (Boros OKX integration Dec 2025)
- **Expected lift**: K275 Sharpe -3.55 → likely positive in positive-carry regime only

### #2 HyperEVM Liminal xToken Vault Prototype (K275後継)
- **What**: HL上でFRをdelta-neutralに収集するLiminal xTokenをK293でプロトタイプ
- **Evidence**: R10-020 (HyperEVM Liminal) + R10-017 (portfolio margin 30% efficiency)
- **Why better**: HL maker 0.015% vs OKX 0.02% + 30% capital efficiency + no counterparty credit risk

### #3 HL HIP-3 Equity Cash-and-Carry (新戦略カテゴリ)
- **What**: TSLA/AAPL/S&P perp short on HL + brokerage stock long during positive funding periods
- **Evidence**: R10-008 (HIP-3 $2.6B OI, 47% HL volume) + R10-012 (predictedFundings API timing)
- **Entry signal**: HL predictedFundings > 0.15%/h for equity perps; exit before weekend close

---

## All 20 Findings

| ID | タイトル | カテゴリ | Actionability | K275関連 |
|---|---|---|---|---|
| R10-001 | HL Tokenomics: $65M/mo Revenue, 99% Buyback | hl-ecosystem | MEDIUM | OKX capital flow competition |
| R10-002 | Boros OKX Integration: 3-Venue FR Arb | okx-specific | HIGH | ROOT CAUSE candidate |
| R10-003 | BitMEX Q1 2026 TradFi Deriv Report: XAG Weekend FR 3x | multi-exchange-arb | HIGH | OKX absent from TradFi growth |
| R10-004 | Price Discovery Lead-Lag: SOL DEX +40min | dex-cex-information-flow | MEDIUM | OKX SOL lag signal |
| R10-005 | HLP Vault: Sharpe 5.2, CAGR 22%, DD -6.6% | hl-ecosystem | HIGH | Passive HL benchmark vs K275 |
| R10-006 | Kelp DAO $292M rsETH Exploit | lrt-restaking | MEDIUM | Restaking FR arb windows |
| R10-007 | Drift $285M Exploit → Jupiter Wins | solana-perp | HIGH | Drift→Jupiter reference change |
| R10-008 | HL HIP-3 RWA $2.6B OI, 47% HL Volume | hl-ecosystem | HIGH | OKX volume erosion backdrop |
| R10-009 | HL HIP-4 Zero-Fee Prediction Markets | hl-ecosystem | LOW-MEDIUM | OKX moat erosion |
| R10-010 | BTC FR Most Negative Since 2023 (March 2026) | okx-specific | HIGH | PRIMARY ROOT CAUSE |
| R10-011 | CoinGecko 2026 CEX-DEX Report | multi-exchange-arb | HIGH | OKX volume share loss |
| R10-012 | Chainstack HL Spot-Perp Arb: predictedFundings | hl-ecosystem | HIGH | HL early warning signal |
| R10-013 | MEV in dYdX v4: CLOB MEV-Resistant | dydx-specific | MEDIUM | dYdX signal robustness |
| R10-014 | ICE-OKX $25B: NYSE Tokenized Equities on OKX | okx-specific | HIGH | K275 sunset timeline |
| R10-015 | OKX April 2026 VIP/ELP Fee Cuts | okx-specific | MEDIUM | Market maker outflow signal |
| R10-016 | Binance-OKX BTC FR Mean Reversion Params | okx-specific | HIGH | K275 risk management params |
| R10-017 | HL Portfolio Margin: 30% Capital Efficiency | hl-ecosystem | HIGH | HL vs OKX capital efficiency |
| R10-018 | dYdX 2026 Fee-Free Programs + Affiliate Booster | dydx-specific | MEDIUM | OKX arb flow diversion |
| R10-019 | Path-Dependent BSDE FR Framework (arXiv 2506) | academic-research | LOW-MEDIUM | OKX FR model evolution |
| R10-020 | HyperEVM Liminal + Hyperbeat: K275 Successor | hl-ecosystem | HIGH | K275 SUCCESSOR ARCH |

---

## Detailed Findings

### R10-001: HL Tokenomics: $65M Monthly Holder Revenue, 99% Fees → HYPE Buyback, 13% Burn Proposal
**URL**: https://tokenomics.com/articles/hyperliquid-tokenomics-how-hype-captures-65m-monthly-in-holder-revenue
**Summary**: Precise 2026 HL revenue decomposition: Perps $62.6M/month (90.9%), Spot $1.9M, L1 Gas $549K, HLP $651K. Total >$65M monthly (Jan 2026). Assistance Fund uses 99% of fees to buy HYPE from open market — $1.7M weekly buybacks, +26% WoW during high-volume periods. Cumulative: $1.16B in buybacks since launch ($3.6M/day). Jan 2026 proposal: burn 13% of circulating supply ($920M worth). Compounding mechanism: volume → fees → buybacks → HYPE price support → attracts more volume.
**Why Orthogonal**: Revenue decomposition by product line with weekly buyback velocity data — not in R1-R9. HYPE price becomes indirect proxy for HL volume, enabling HYPE momentum as leading indicator for HL FR activity.
**K275**: HL's $65M/month revenue vs OKX's declining share quantifies asymmetric growth. HYPE buyback compounding attracts capital away from OKX, structurally reducing OKX FR sustainability.

### R10-002: Boros OKX Integration — Three-Venue Fixed-Rate FR Arbitrage
**URL**: https://blockchainreporter.net/boros-integrates-okx-for-wider-funding-rate-trading-and-arbitrage-opportunities
**Summary**: Boros (Pendle FR tokenization on Arbitrum) integrated OKX December 2025 via Yield Units (YUs). Four-leg delta-neutral: short HL YU + short HL perp + long Binance YU + long Binance perp. Historical Boros yields: BTC 5.98-11.4% Fixed APR (peaks 23.5%); ETH 9.94% avg. Three-venue triangular: up to 30% delta-neutral fixed yield.
**Why Orthogonal**: Three-venue triangular arb via DeFi fixed-income wrapper — first time OKX is a third leg in a structured fixed-yield arb product.
**K275**: Boros OKX integration Dec 2025 pulled institutional arb capital into OKX-Binance spread, collapsing the carry K275 harvests. DIRECT root cause candidate.

### R10-003: BitMEX Q1 2026 TradFi Derivatives Report: XAG Weekend FR 3x Weekday Premium
**URL**: https://www.bitmex.com/blog/2026q1-derivatives-report
**Summary**: TradFi perps: 0.03% → 1.72% of total derivatives volume in Q1 2026; weekly volume $30.7B. KEY ANOMALY: XAG (silver) on Binance weekend FR = +56.69% APR vs weekday +18.18% APR — a 3x weekend premium. Commodities: +65,463% volume growth; crude oil $0 → $6.9B weekly (Iran tensions drove it). BitMEX TradFi perps: deeply negative FR (SPY -163.43% APR, COIN -105.23% APR). Binance: +74,537% volume surge, 62.7% TradFi perp market share. HL grew +953.4% to 29.7% share. OKX entirely absent from TradFi perp growth data.
**Why Orthogonal**: First quantified 3x weekend vs weekday FR premium on RWA perps — opening a new timing-based FR strategy layer for HL HIP-3 commodity perps not in R1-R9. Q1 2026 snapshot of TradFi perp market share distribution.
**K275**: OKX absent from TradFi perp growth (Binance + HL = 92.4% of market). OKX not competing in highest-growth segment — validates structural market share erosion underlying K275 underperformance.

### R10-004: Price Discovery Lead-Lag DEX vs CEX: SOL DEX Leads Binance by 40 Minutes
**URL**: https://zenodo.org/records/17084252
**Summary**: BTC: CEX leads 5 min. SOL: DEX leads Binance by 40 minutes (strongest DEX dominance). ETH: mixed. Price correlations 0.98-0.99, MAPE 0.06-0.08% — efficient transmission but systematic timing offsets. DEX spot share doubled 6.9% → 13.6%.
**Why Orthogonal**: Asset-class-dependent lead-lag reveals SOL as DEX-leads-CEX pair — opens distinct signal source for Solana perps on Jupiter/Drift vs Binance.
**K275**: OKX SOL perp FR adjustments lag Solana DEX by 40 min — K275 OKX signal may be buying already-priced information.

### R10-005: HLP Vault Risk-Return: Sharpe 5.2, CAGR 22%, Max DD -6.6%
**URL**: https://medium.com/@RyskyGeronimo/a-risk-return-analysis-of-hyperliquids-hlp-vault-7c164cd00a0d
**Summary**: Lifetime CAGR 42% → 22% (trailing 12M); vol fell 17.89% → 4.5%, Sharpe 2.89 → 5.2. Max drawdown -6.6% vs BTC -23%. Negative BTC correlation -9.6%. 80/20 HLP+BTC blend: 175% cumulative, 16% vol, Sharpe 3.6. Monthly avg 1.75%. 4-day lockup is crisis exit risk.
**Why Orthogonal**: Quantified Sharpe decomposition as standalone asset class — not in R1-R9. Sets passive HL market-making baseline (Sharpe 5.2) that active K287d satellites must beat.
**K275**: As OKX carry decays, HLP passive exposure (Sh 5.2) is the direct alternative benchmark for K275 capital reallocation decision.

### R10-006: Kelp DAO $292M rsETH Bridge Exploit — Largest 2026 DeFi Hack
**URL**: https://defiprime.com/kelpdao-rseth-exploit
**Summary**: April 18 2026: Lazarus Group RPC poisoning attack minted 116,500 unbacked rsETH ($292M), drained $236M WETH from Aave. $5.4B restaking withdrawals in 48 hours. Aave/SparkLend/Fluid froze rsETH markets. KernelDAO at $20M cap vs $2B TVL (100x trust-discount gap). Recovery underway via refill and security rebuild.
**Why Orthogonal**: 2026 systemic shock to LRT/restaking — entirely new event. Creates post-exploit alpha playbook for mean-reversion on surviving protocols.
**K275**: Restaking sector fear may create brief FR arb windows for weETH/EIGEN perps on OKX — satellite-adjacent opportunity.

### R10-007: Drift Protocol $285M Solana DEX Exploit — DPRK Durable Nonce Attack
**URL**: https://unchainedcrypto.com/how-solanas-largest-perp-dex-was-exploited-for-285-million/
**Summary**: April 1 2026: DPRK socially engineered Drift for months, used durable nonces to drain $285M in 12 minutes. Drift TVL $550M → $250M, DRIFT token -42%. Tether $127.5M rescue; Drift pivoting to USDT settlement. Jupiter explicitly firewalled, gaining trust. 8.6% Solana DeFi TVL gap created.
**Why Orthogonal**: New 2026 event reshaping Solana perp DEX landscape. Creates clear structural winner (Jupiter) for K293+ Solana strategy references.
**K275**: Drift must be removed from any cross-venue signal set. Jupiter Perp replaces Drift as Solana DEX FR leader.

### R10-008: HL HIP-3 RWA Perps: $2.6B Open Interest, 47% of HL Volume Tokenized
**URL**: https://www.coindesk.com/markets/2026/03/10/hyperliquid-s-permissionless-market-smashes-usd1-2-billion-in-open-positions-as-oil-and-equity-futures-boom
**Summary**: HIP-3 (Oct 2025): anyone stakes 500K HYPE → deploys perps. trade.xyz: TSLA/AAPL/NVDA/AMZN + S&P500 (licensed Mar 18 2026) + CL/gold/silver. May 2026: $2.6B RWA OI ATH; 47.1% of all HL trading is RWA perps. Top: XYZ100 $213M OI; CL $169.8M OI, $1.62B daily volume.
**Why Orthogonal**: RWA/equity perp FR dynamics on HL not covered in R1-R9. Opens equity cash-and-carry arb: stock long (brokerage) + HL equity perp short. Weekend gap risk is the novel structural hazard.
**K275**: RWA perp growth shows HL cannibalizing OKX/Binance in novel asset classes — institutional HL adoption continues to compress OKX FR premium.

### R10-009: HL HIP-4 Outcome Markets: Zero-Fee Binaries vs Polymarket
**URL**: https://www.coingecko.com/learn/hyperliquid-hip3-hip4-tokenized-stocks-and-prediction-markets
**Summary**: HIP-4 launched May 2 2026 via Outcomexyz: fully collateralized binary contracts (USDH, no liquidation risk), settling daily 06:00 UTC. First: BTC daily binary, 6.05M contracts in 24h. Zero fee to open; fees only on close/settle. Outcome positions share margin with perps/spot in unified HL account; activity counts toward fee tier.
**Why Orthogonal**: Fee-tier compounding incentive — binary market volume unlocks lower perp maker tiers, reducing K287d satellite execution costs up to 30%.
**K275**: HIP-4 draws volume from OKX options/prediction products, further eroding OKX's competitive FR premium moat.

### R10-010: BTC FR Most Negative Since 2023 — OKX/Binance 30-Day Avg Below Zero Since March 2026
**URL**: https://www.coindesk.com/markets/2026/04/16/bitcoin-funding-rates-hit-most-negative-since-2023-history-suggests-bottom-is-in
**Summary**: April 2026: BTC aggregate FR -0.005% 7-day avg (most extreme since 2023). Binance BTC/USDT 30-day avg below zero since March 1 2026; OKX + Bybit identical. BTC: $126K ATH (Oct 2025) → $65.6K-72.5K. OI -21.7% Jan-Feb. Historical: extreme negative FR preceded bottoms in Mar 2020, mid-2021, Nov 2022, Aug 2024.
**Why Orthogonal**: R1-R9 analyzed positive-carry environments. Q1-Q2 2026 sustained negative FR regime is the first comprehensive regime-shift documentation for 2026.
**K275**: PRIMARY ROOT CAUSE. K275 designed for positive carry (longs pay shorts). March 2026 flip = K275 collecting from wrong side. Add regime filter: disable K275 when 30-day avg FR < -0.001%.

### R10-011: CoinGecko 2026 CEX-DEX Report: Perp DEX Volume 8x, HL Only DEX in Top 10
**URL**: https://www.coingecko.com/research/publications/cex-dex-trading-activity-report-2026
**Summary**: CEX perps: $7.24T/month. Perp DEX: 8x growth $82B → $739B. DEX perp share: 2.0% → 10.2%. HL ONLY DEX in top 10 with $1.59T cumulative volume. DEX spot share doubled 6.9% → 13.6%. Binance: $3.54T spot + $13.61T perp. OKX declining relative share.
**Why Orthogonal**: Authoritative 2026 full-year market structure report with first quantification of OKX's declining relative volume share.
**K275**: OKX volume share loss to HL is the structural backdrop for K275 degradation — as volume migrates, OKX FR becomes noisier.

### R10-012: Chainstack HL Spot-Perp Arb: predictedFundings API + 0.11%/h Break-Even
**URL**: https://docs.chainstack.com/docs/hyperliquid-funding-rate-arbitrage
**Summary**: Break-even: FR > 0.11%/h (maker), practical minimum 0.15%/h. Fee cycle: spot 0.08% + perp 0.03% = 0.11%. Critical: 'predictedFundings' endpoint provides forward-looking FR before settlement. Entry: 5-10 min pre-funding. Asset set: intersect spot and perp markets. Liquidity gate: l2Book spread >0.15% = reject.
**Why Orthogonal**: Technical implementation layer with underdocumented predictedFundings API — provides advance notice of FR changes before market prices reflect them.
**K275**: HL predictedFundings = early warning for K275 OKX cross-venue: divergence from OKX current FR opens a 5-10 min window before the hour.

### R10-013: MEV in dYdX v4 Cosmos Appchain: CLOB Architecture is MEV-Resistant
**URL**: https://chorus.one/articles/exploring-mev-implications-and-cross-domain-dynamics-on-dydx-v4
**Summary**: Chorus One: cross-chain value extraction currently lacks compelling incentives on dYdX v4. CLOB architecture creates market-maker-validator partnership incentive (unlike AMMs) but not active MEV extraction. dYdX v4 FR is structurally MEV-resistant. dYdX v5 (Jan 2025): isolated markets + isolated margin + spot markets + prediction markets + permissionless perps.
**Why Orthogonal**: First detailed dYdX-specific MEV analysis. Finding that MEV is NOT the culprit changes diagnostic search for K270 underperformance.
**K275**: dYdX MEV resistance makes it more reliable FR signal source vs OKX where institutional flow manipulation lacks blockchain transparency.

### R10-014: ICE (NYSE Parent) Invests in OKX at $25B — NYSE Tokenized Equities on OKX Late 2026
**URL**: https://fortune.com/2026/03/05/okx-ice-intercontinental-exchange-investment-tokenized-securities-25-billio/
**Summary**: March 2026: ICE invested in OKX at $25B, taking board seat. OKX enables tokenized NYSE stocks in late 2026; ICE supplies crypto price feeds to OKX; OKX relocating 2,000/5,000 employees to US. OKX re-entered US market April 2025. Ranks 3rd CME liquidity behind Binance + Coinbase. VIP 1 threshold lowered from $10M to $5M April 2026.
**Why Orthogonal**: Structural regulatory transformation of OKX — ICE partnership signals TradFi pivot with imminent equity perp integration, reshaping OKX flow composition fundamentally.
**K275**: K275 must sunset or evolve before late 2026 NYSE tokenized equity launch on OKX. TradFi arb capital will drive CEX-CEX FR to near-parity faster than K275 assumptions allow.

### R10-015: OKX April 2026 VIP/ELP Fee Cuts: VIP 1-3 Thresholds Lowered, ELP Maker Fee Halved
**URL**: https://www.okx.com/en-us/help/advance-notice-adjustment-to-vip-tier-and-future-fees
**Summary**: April 8 2026: VIP 1 threshold $10M → $5M 30-day futures volume (~$167K/day), automatic tier upgrades. May 20 2026: ELP maker fee for VIP 7-9 cut to 50% of standard maker fee across all products. Designed to retain high-volume market makers facing Binance/HL pressure.
**Why Orthogonal**: OKX-specific incentive structure change — VIP tier lowering + halved ELP maker fees signals OKX actively fighting market maker outflows. Direct K275 FR sustainability signal.
**K275**: ELP maker fee halving signals OKX bleeding high-frequency market makers → wider FR volatility → noisier K275 signal. Structural headwind despite fee cuts.

### R10-016: Binance-OKX BTC FR Mean Reversion: 2% Historical Spread, 22-Day 21% Return
**URL**: https://rho.trading/blog/mean-reversion-strategy-in-crypto-rate-trading
**Summary**: Binance vs OKX BTC FR spread: historical mean ~2%, peak deviation >5%. Example: -3% spread at deviation peak, 100x leverage $50K notional / $1K collateral, 22-day convergence = 21% return. Liquidation buffers: Binance long safe until 2.0% APR; OKX short safe until 26% APR. Spread historically reverts even through negative territory dips.
**Why Orthogonal**: First quantitative mean-reversion parameter study for OKX-Binance BTC FR pair with documented liquidation safety levels — not in R1-R9 despite K275 direct relevance.
**K275**: DIRECT INPUT: 2% mean spread, 5% peak deviation, 22-day convergence horizon. Alert at 3.5% spread; forced exit at 6%. Monitor SIGN of spread in current negative FR regime.

### R10-017: HL Portfolio Margin: 30%+ Capital Efficiency, Unified Spot+Perp, Auto-Borrow
**URL**: https://www.cryptopolitan.com/hyperliquids-newest-portfolio-margin-upgrade/
**Summary**: Pre-alpha live Dec 23 2025. Net portfolio risk calculation → 30%+ capital efficiency improvement. Single USDC/USDH balance collateralizes all cross-margin perps + spot. Auto-earn on idle borrowable assets. Borrow up to 1M USDC/USDH against spot HYPE or BTC. Access: >$5M weighted trading volume. Liminal + Hyperbeat use this for delta-neutral strategies.
**Why Orthogonal**: Portfolio margin enables new class of HL-native multi-leg strategies — spot long + perp short + leveraged borrowing from one account. 30%+ capital efficiency vs K287d two-account model.
**K275**: HL portfolio margin makes HL-based carry 30% more capital efficient than OKX equivalents — further tilting competitive balance against K275 OKX-native approach.

### R10-018: dYdX 2026 Programs: BTC/SOL Perps Fee-Free + 50% Rebates + $200K Affiliate
**URL**: https://www.dydx.xyz/blog/first-affiliate-booster-program-of-2026-announced
**Summary**: Dec 2025 Season 9: all traders 50% fee rebates automatically; BTC and SOL perp markets completely fee-free (0% maker + taker). Jan-Mar 2026 Affiliate Booster: $200K USDC pool, $1M-$100M milestone structure. BTC/BONK fee-free markets count 0.5x toward milestones. $1M liquidation rebate pilot Dec 2025. Surge Seasons 10/11 continuing.
**Why Orthogonal**: dYdX's systematic fee elimination on BTC/SOL changes fundamental cost structure for K270 cross-venue arb — temporarily making dYdX lowest-cost venue globally.
**K275**: dYdX fee elimination periods divert institutional arb flow from OKX to dYdX — contributing to OKX FR carry premium erosion underlying K275 underperformance.

### R10-019: Path-Dependent BSDE Framework for Perpetual Futures FR (arXiv 2506.08573v1)
**URL**: https://arxiv.org/html/2506.08573v1
**Summary**: June 2026 paper using infinite-horizon path-dependent BSDEs to prove appropriately designed FR can maintain perp price alignment. Proposes alternative 'path-dependent' FR formulas beyond standard linear premium index. Key theoretical implication: path-dependent FR accounts for price trajectory (not just instantaneous premium), meaning reversals after sustained trends generate predictable correction signals.
**Why Orthogonal**: HTML v1 adds mathematical developments beyond abstract-level R9 citation. New: path-dependent FR design reduces price-tracking error, with trend-reversal correction signals as novel derivative alpha source.
**K275**: If OKX moves toward path-dependent FR design (possible given ICE TradFi partnership), K275's stationary linear premium assumption breaks. Model OKX FR as path-dependent in K293.

### R10-020: HyperEVM Liminal + Hyperbeat: Delta-Neutral FR Vaults as K275 Successor Architecture
**URL**: https://www.datawallet.com/crypto/top-hyperevm-projects
**Summary**: HyperEVM (Feb 2025 mainnet): Solidity contracts with direct read/write access to HL L1 orderbook. Enables delta-neutral strategies, on-chain market makers, automated basis trades, structured products without external keepers. Liminal: converts HL FR into market-neutral xTokens. Hyperbeat: beHYPE liquid staking + HYPE/USDC/UBTC/XAUt vaults + HIP-3 liquidity + delta-neutral tokens. Precompiles: instant collateral checks, synchronized liquidations, no oracle delays.
**Why Orthogonal**: HyperEVM smart contract composition with CLOB is entirely new strategy category. Liminal xToken model wrapping FR carry into liquid tokens is a new primitive for K293+ architecture not in R1-R9.
**K275**: Liminal is the structural replacement for K275 at execution layer: delta-neutral FR capture, lower cost (0.015% HL maker vs OKX 0.02%), +30% capital efficiency (portfolio margin), better composability. K275 sunset roadmap should point to Liminal-equivalent on-chain structure.

---

## URL Deduplication Verification
All 20 URLs verified against R6-R9 database (72 URLs). Zero overlaps confirmed.

*Systematic Alpha Discovery Program — Round 10 complete*
