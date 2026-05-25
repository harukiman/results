# External Findings Round 12 — Wave K334

**最終更新:** 2026-05-25 20:11 JST
**累計:** R1-R11: 242件 + R12: 20件 = **262件**
**重複:** 0件 (全108件の既存URLと照合済)

---

## エグゼクティブサマリー

R12は5-7日ぶりの研究ラウンド。10のフォーカスエリアに対し20件の新規発見を取得。最大の発見は以下4点:

1. **BOCPD Switch-Off実装** (R12-10) — K315-K327で失敗中のBOCPD問題に対し、Python実装付きのdual-trigger設計が利用可能
2. **RWA Perps予測オラクル** (R12-12) — 日曜22:00 UTCシグナル窓でSilver 84.6%/Gold 69.2%の方向精度を実証
3. **Ethena最適制御論文** (R12-05) — delta-neutral carryの最適accumulation speedを解析的に解いた初の論文(May 2026)
4. **CME/ICE規制圧力** (R12-16) — HIP-3 RWA戦略のtail riskとして即時リスク管理対応が必要

---

## ★ Top 3 Actionable for K336+

### 1位: R12-10 — QuantBeckman BOCPD Switch-Off (Python付)
- **URL:** https://www.quantbeckman.com/p/with-code-switch-off-bayesian-online
- **K336適用:** K323/K327の代替としてBOCPD dual-triggerをv6.12サブ戦略に実装
- **即効性:** Python実装公開済み、kill_threshold=0.5のBayesian decision ruleを即移植可能
- **なぜ最優先:** shock(突発崩壊)とerosion(漸進的alpha decay)を別々に検知。funding rate carryのalpha decayはerosion型が多く、既存の閾値ベース手法では検知遅延が大きい

### 2位: R12-12 — Crypto.com Research RWA Perps Predictive Edge (Apr 2026)
- **URL:** https://crypto.com/eea/research/rwa-perps-find-predictive-edge-apr-2026
- **K336適用:** K297 weekend戦略に日曜22:00 UTC執行窓を追加。Silver/Goldシグナルを直接利用
- **即効性:** Silver 84.6%/Gold 69.2%の方向精度データ + 5種測定フレームワーク + liquidation bufferが揃っている
- **なぜ2位:** K297の既存コードに窓タイミングとfake-outフィルター(Tech株)を追加するだけで改善可能

### 3位: R12-05 — arXiv 2605.11263 Ethena最適制御 (May 2026)
- **URL:** https://arxiv.org/abs/2605.11263
- **K336適用:** K206/K207 Ethena TVLシグナルのdynamic sizeにoptimal policy理論を反映
- **即効性:** sUSDe APY 9.4%(7日MA)の現在地は再エントリータイミング。Infinite-horizon optimal policyがFR正の時に積み上げ・inventory大で速度低下するルールを提供
- **なぜ3位:** K336での新サブ戦略追加より既存K206/K207の改良として低リスクで高インパクト

---

## 全20件リスト

### Group A: HL HIP-3 RWA (4件)

| ID | タイトル | URL | 主要メトリクス |
|---|---|---|---|
| R12-01 | FalconX: HIP-3 Transformational Potential | https://www.falconx.io/newsroom/the-transformational-potential-of-hyperliquids-hip-3 | MAG7 $0.9B/日、0DTE $9.0B潜在ボリューム |
| R12-12 ★ | Crypto.com RWA Perps Predictive Edge | https://crypto.com/eea/research/rwa-perps-find-predictive-edge-apr-2026 | Silver 84.6%、日曜22:00 UTC窓 |
| R12-13 | Monarq: Price Discovery While the World Sleeps | https://medium.com/@Monarq_Mgmt/price-discovery-while-the-world-sleeps-c489a0a08dd1 | 2/28 Iran攻撃時HL単独でprice discovery |
| R12-16 ★ | CME/ICE規制圧力 (CoinDesk May 2026) | https://www.coindesk.com/markets/2026/05/15/cme-ice-push-u-s-regulators-to-scrutinize-hyperliquid-over-manipulation-risks-bloomberg | WTI volume $339M→$7.3B(3週間) |

### Group B: HL Portfolio Margin / Ecosystem (2件)

| ID | タイトル | URL | 主要メトリクス |
|---|---|---|---|
| R12-19 | kkdemian: HL Investment-Grade Report 2026 | https://www.kkdemian.com/blog/hyperliquid_report_2026 | HLP $845.6M累積収益、Portfolio Margin $5M閾値 |
| R12-20 | Crypto.com Research Roundup May 2026 | https://crypto.com/en/research/research-roundup-may-2026 | RWA $30.8B(431%成長)、BTC機関保有1.2M BTC |

### Group C: 2026 H1 Academic Research — RL Allocators (3件)

| ID | タイトル | URL | 主要発見 |
|---|---|---|---|
| R12-02 ★ | arXiv 2602.17098: DRL vs MVO (Feb 2026) | https://arxiv.org/abs/2602.17098 | DRL全指標でMVO超過 |
| R12-03 | arXiv 2603.22880: Recursive Utility RL (Mar 2026) | https://arxiv.org/abs/2603.22880 | リスク感応的目的関数でSharpe/MaxDD改善 |
| R12-09 | arXiv 2511.20678: SAC and DDPG (Nov 2025) | https://arxiv.org/abs/2511.20678 | SAC > DDPG > equal-weight > MVO |

### Group D: Funding Rate / BOCPD (2件)

| ID | タイトル | URL | 主要発見 |
|---|---|---|---|
| R12-10 ★ | QuantBeckman Switch-Off BOCPD | https://www.quantbeckman.com/p/with-code-switch-off-bayesian-online | dual-trigger(shock+erosion)、Python実装付き |
| R12-18 | arXiv 2505.24831: Stable Clustering Portfolio | https://arxiv.org/abs/2505.24831 | Louvain+ARIMA、14日ホライズンで安定パフォーマンス |

### Group E: DEX Perp Microstructure 2026 (4件)

| ID | タイトル | URL | 主要発見 |
|---|---|---|---|
| R12-11 | A1 Research: Perp DEX Wars $8T Endgame | https://paradex.trade/blog/perp-dex-wars-the-8-trillion-institutional-endgame | 8 DEX比較、OI-Volume比、funding mechanics |
| R12-14 | Monarq: From Subsidies to Market Structure | https://medium.com/@Monarq_Mgmt/perp-dexs-in-2025-the-shift-from-subsidies-to-market-structure-68a1138f4c10 | DEX perp $6.7T(4x)、シェア8% |
| R12-15 | Variational $50M raise (CoinDesk May 2026) | https://www.coindesk.com/business/2026/05/21/peer-to-peer-trading-startup-variational-raises-usd50-million-for-real-world-perps-in-funding-round-led-by-dragonfly | RFQ型、Gold/Silver/Copper/WTI 100+市場 |
| R12-04 | arXiv 2602.10798: CEX/DEX Priority Fees | https://arxiv.org/abs/2602.10798 | priority feeで遅延操作、significant outperformance |

### Group F: Flash Crash Protection / ADL (2件)

| ID | タイトル | URL | 主要発見 |
|---|---|---|---|
| R12-06 ★ | arXiv 2602.15182: ADL as Online Learning | https://arxiv.org/abs/2602.15182 | 本番regret50%→最適2.6%、$51.7M過剰削減可能 |
| R12-07 | arXiv 2512.01112: ADL Impossibilities | https://arxiv.org/abs/2512.01112 | trilemma証明、Binance > HL過剰ADL |

### Group G: Stablecoin Yield Arb (3件)

| ID | タイトル | URL | 主要メトリクス |
|---|---|---|---|
| R12-05 ★ | arXiv 2605.11263: Ethena最適制御 | https://arxiv.org/abs/2605.11263 | infinite-horizon closed-form解 |
| R12-08 | arXiv 2601.10812: Optimal Liquidation Perp | https://arxiv.org/abs/2601.10812 | closed-form解、funding rate考慮 |
| R12-17 | Ethena USDe Q1 2026 Report | https://stablecoininsider.org/ethena-usde-q1-2026-report/ | 供給$5.92B、APY 3.72%→9.4%回復 |

---

## v6.12 K302aへの直交性/相乗性

| カテゴリ | 直交性 | 相乗性 |
|---|---|---|
| BOCPD Switch-Off (R12-10) | 独立した戦略モニタリング層 | v6.12全サブ戦略のde-allocationに適用 |
| RWA Perps Oracle (R12-12) | K297以外の戦略には独立 | K297/K302のweekend収益を直接強化 |
| Ethena最適制御 (R12-05) | K206/K207固有 | Ethena TVLシグナルのsizingロジックに統合 |
| ADL Online Learning (R12-06) | K200固有 | ADLイベントの予測・回避で全体のtail riskを削減 |
| DRL vs MVO (R12-02) | 既存ウェイト最適化と独立 | K198/K201のMLアロケーターの次世代化 |
| CME/ICE規制リスク (R12-16) | 新しいtail riskカテゴリ | HIP-3関連全戦略のposition capに影響 |

---

*Generated by Wave K334 tip-scraper Round 12 | 2026-05-25 20:11 JST*
