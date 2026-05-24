# External Findings Round 8 — Summary

**Date**: 2026-05-25  
**Total entries**: 20 (累計 R1-R8: 182)  
**Duplicates with R1-R7**: 0  
**Actionable**: 17 / Non-actionable: 3

---

## Executive Summary

R8は「K198の51特徴に存在しない完全直交なアルファ源」に焦点を当て、10つの異なる領域から20の新規発見を獲得した。最重要発見は以下3つ:

1. **Kalshi予測市場マクロシグナル** (R8-01): 規制市場の集合知がBTCボラを事前予測（OOS p=0.020）
2. **Slippage-at-Risk (SaR)** (R8-03): オーダーブック現状から清算カスケードを前向き定量化
3. **Taker-Flow GEX / Gamma Flip** (R8-04): Deribitオプション市場からディーラーヘッジレジームを特定

---

## Top 3 for K216+ 実装優先度

### #1: R8-03 — Slippage-at-Risk (SaR)
**URL**: https://arxiv.org/abs/2603.09164  
**機構**: TSaR(α)=ドル換算テールスリッページを現在オーダーブックから前向きに算出。Hyperliquid 2025/10/10清算カスケード（$2.1B/12分）で事前予測力実証済み。  
**実装**: HL APIからLOBスナップショットを定期取得→TSaR(0.95)を銘柄別計算→90パーセンタイル超えで新規エントリー停止。  
**直交理由**: K198にリアルタイムLOB流動性リスク指標なし。後向きVaRではなく前向きリスク評価は根本的に異なるアプローチ。  
**実装難度**: 中（HL LOB API + TSaR計算ロジック追加）

### #2: R8-01 — Kalshi Macro Prediction Market Signals
**URL**: https://arxiv.org/abs/2604.01431  
**機構**: KXFED（金融政策）、KXRECSSNBER（景気後退リスク: OOS MSFE=0.979）、KXCPI（インフレ）の日次確率変化がBTC/ETH/SOLボラを予測。FFレート先物・米国債・DeribitIVIXに含まれない情報を保有。  
**実装**: Kalshi API日次取得→景気後退確率急上昇（+5%/日）時にポジション縮小トリガー設定。  
**直交理由**: K198はマクロ予測市場シグナルを一切持たない。集合知ベースのボラ予測は51特徴と完全直交。  
**実装難度**: 低（Kalshi REST API + 日次バッチ処理）

### #3: R8-04 — Taker-Flow-Based GEX / Gamma Flip
**URL**: https://insights.glassnode.com/gamma-exposure/  
**機構**: CEXのtaker識別可能性を利用してディーラー在庫を実取引フローから再構築。正GEX帯=価格ピニング（ディーラーが押し目を買い戻す）、負GEX帯=モメンタム増幅。ガンマフリップ（ゼロクロス）がレジーム転換の先行指標。BTC/ETH/XRP/SOL、10分粒度。  
**実装**: Glassnode Professional API→GEX符号とフリップレベルを取得→負のGEX帯でポジションサイズ縮小、フリップ発生時にレジーム転換アラート。  
**直交理由**: K198はオプションガンマエクスポージャーを全く参照しない。Deribit日次$12Bオプション市場の影響はFR基盤信号と直交。  
**実装難度**: 中（Glassnode Pro APIサブスクリプション必要）

---

## 全20エントリー一覧

| ID | Title | Actionable | Area |
|----|-------|-----------|------|
| R8-01 | Kalshi Macro → Crypto Volatility (arxiv:2604.01431) | Y | Macro prediction markets |
| R8-02 | Cross-Chain Negative Spillovers (arxiv:2602.23762) | Y | On-chain cross-chain |
| R8-03 | Slippage-at-Risk SaR (arxiv:2603.09164) | Y ★TOP3 | Orderbook microstructure |
| R8-04 | Taker-Flow GEX / Gamma Flip (Glassnode) | Y ★TOP3 | Options market |
| R8-05 | Stablecoin Tail Spillovers (arxiv:2602.18820) | Y | Stablecoin flow |
| R8-06 | ETH Validator Queue Flip → ETH Price (ainvest) | Y | Validator/staking |
| R8-07 | 170 Perp Predictors / Log Basis (SSRN:6365329) | Y | Futures microstructure |
| R8-08 | Hash Ribbon + Miner Capitulation (CoinDesk 2026) | Y | Mining/hashrate |
| R8-09 | Jito MEV Tip Revenue as SOL Volatility Proxy | Y | On-chain MEV |
| R8-10 | CEX-DEX MEV Extraction Window (arxiv:2507.13023) | Y | Orderbook/latency |
| R8-11 | Hawkes Process Liquidation Cascade (MethodAlgo) | Y | Liquidation cascade |
| R8-12 | Polymarket Orderbook Microstructure (arxiv:2604.24366) | Y | Prediction market |
| R8-13 | P2P Stablecoin Flows 2-Day Early Warning (arxiv:2512.00893) | Y | Stablecoin flow |
| R8-14 | GoDark Institutional Dark Pool (CoinDesk) | N | OTC/dark pool |
| R8-15 | Options Max Pain + Weekly Expiry Pinning (MenthorQ) | Y | Options calendar |
| R8-16 | NFT PFP Sentiment → ETH Price (arxiv:2602.01531) | N | NFT sentiment |
| R8-17 | BTC/ETH Spot ETF Daily Flows (Glassnode) | Y | Institutional flow |
| R8-18 | HLP Vault Inverse Relationship (OAK Research) | Y | HL-specific |
| R8-19 | NVT Golden Cross BTC Top Detector (CryptoQuant) | Y | On-chain valuation |
| R8-20 | stETH Discount + ETH Staking vs FR (Lido/DeFiLlama) | Y | Liquid staking |

---

## エリア別カバレッジ

| Target Area | Entries | Key Findings |
|-------------|---------|-------------|
| Orderbook microstructure | R8-03, R8-10, R8-11 | SaR(前向きLOBリスク), CEX-DEX 1.5秒窓, Hawkes清算 |
| Options market | R8-04, R8-15 | GEX gamma flip, Max Pain週次ピニング |
| Macro prediction markets | R8-01, R8-12 | Kalshi KXRECSSNBER, Polymarket暗号イベント |
| Stablecoin/on-chain flow | R8-05, R8-13 | アルゴステーブル伝染, P2P P2B先行指標 |
| Validator/staking | R8-06, R8-20 | ETHバリデータキュー反転, stETH discount |
| Cross-chain/MEV | R8-02, R8-09, R8-10 | チェーン間負スピルオーバー, Jito MEVチップ |
| Mining/hashrate | R8-08 | ハッシュリボン+マイナー降参 |
| Liquidation cascade | R8-11 | Hawkesブランチング比リアルタイム推定 |
| Institutional flow | R8-14, R8-17, R8-18 | ETFフロー7日累計, HLP APY逆相関 |
| On-chain valuation | R8-07, R8-19 | 170指標log basis, NVT Golden Cross |

---

## 重複チェック（R1-R7との差分確認）

- R7でHLPモニタリング（R7-04）は取り上げたが、R8-18はHLP APY週次変化率の逆相関シグナルとして角度を変えた新発見
- R7でHawkesプロセスの概念は未発見（清算カスケードのブランチング比推定はR8-11が初出）
- R7でCEX-DEX価格収束（R7-11, R7-12）を扱ったが、MEV searcher抽出窓（0.5-1.5秒）の実行機会はR8-10が初出
- 全20エントリーはR1-R7の162エントリーと重複なし

---

## 次アクション提案

1. **K216-A**: R8-03 SaR → HL LOB APIからTSaR計算モジュール実装（優先度1）
2. **K216-B**: R8-01 Kalshi KXRECSSNBER → 日次バッチ取得+レジームフィルタ追加（優先度2）
3. **K216-C**: R8-04 GEX → Glassnode Pro API接続+GEX符号によるポジションサイジング補正（優先度3）
4. **K216-D**: R8-07 log basis → 全銘柄でlog basis算出→FR z-score残差特徴追加（優先度4）
5. **R9検討**: R8-16 NFT→ETH因果関係のOOS独立バックテスト（保留）
