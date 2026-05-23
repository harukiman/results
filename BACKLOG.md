# BACKLOG.md — 未探索アイデア・戦略候補

> 継続的に新規系統を開拓するためのアイデア蓄積。優先度は暫定。

## 高優先度 (Phase A スキャン対象)

### 平均回帰系
- [ ] ボリンジャーバンド回帰 (動的閾値, ATRベース帯域)
- [ ] Z-scoreベース平均回帰 (ローリング平均/標準偏差)
- [ ] OU (Ornstein-Uhlenbeck) プロセスフィッティング
- [ ] ペアトレード (共和分ペアの探索)
- [ ] バスケット裁定 (セクター/テーマ間)

### モメンタム・トレンド系
- [ ] ブレイクアウト (ATRベース, ドンチャンチャネル)
- [ ] 時系列モメンタム (リターンの自己相関活用)
- [ ] クロスセクショナルモメンタム (銘柄間の相対強度)
- [ ] トレンドフォロー + フィルター (ADX, 移動平均クロス)
- [ ] ボラティリティブレイクアウト (Keltnerチャネル)

### マイクロストラクチャ系
- [ ] オーダーフロー不均衡 (買い/売りボリューム比)
- [ ] 板インバランス (ビッド/アスク深度比)
- [ ] CVD (Cumulative Volume Delta) ダイバージェンス
- [ ] VWAP回帰
- [ ] 大口検出 (異常出来高)

### ファンディング・ベーシス裁定
- [ ] ファンディングレート方向トレード
- [ ] ファンディング時刻前後のアノマリー (8h周期)
- [ ] 現物-先物ベーシス変動
- [ ] 極端ファンディング時の逆張り

### ボラティリティ系
- [ ] ボラティリティ圧縮→拡大 (ATR/BBwidth)
- [ ] レンジブレイク (低ボラ期間後のブレイクアウト)
- [ ] GARCH予測ベースのポジショニング
- [ ] IV-RV乖離 (オプション市場参照可能なら)

### 時間帯・季節性
- [ ] ファンディング決済前後 (UTC 0:00/8:00/16:00)
- [ ] 曜日効果
- [ ] アジア/欧州/米国セッション切替
- [ ] 月初/月末効果

### 清算カスケード
- [ ] 大規模清算後のリバーサル
- [ ] 清算ヒートマップベースのエントリー
- [ ] OI急変時のトレード

### 特徴量+ML (flearn手法適用)
- [ ] CUSUMイベント + トリプルバリア + メタラベリング
- [ ] FFD特徴量 + RandomForest/LightGBM
- [ ] 複合特徴量 (テクニカル + オーダーフロー + ファンディング)
- [ ] PurgedKFold + Sequential Bootstrap

## 中優先度 (Phase B 以降)
- [ ] クロス取引所裁定 (MEXC vs Binance/Bybit)
- [ ] 相関ブレイク (BTC-ALT相関崩壊時)
- [ ] センチメント指標連動
- [ ] オンチェーンデータ連動 (ウォレット移動, DEX flows)

## 低優先度 / 要調査
- [ ] 強化学習ベースの最適執行
- [ ] NLPベースのニューストレード
- [ ] フラクタル/カオス理論ベース

---
*更新: 2026-05-22 初版*

---

## 2026-05-23 22:50 JST: Researcher subagent 10案 + Tip-scraper 15記事追加

### Researcher 10案 (新規仮説)

| # | 名称 | カテゴリ | データ | 難易度 | 想定独立性 | 検証優先度 |
|---|------|----------|--------|--------|-----------|-----------|
| R1 | FOPD (Funding-OI-Price Triple Decoupling) | クラウディング | OHLCV+FR+OI | 中 | 高 | TOP2 |
| R2 | LCSF (Liquidation Cluster Stop-Hunt Fade) | カスケード | OHLCV+OI | 中 | 中 | - |
| R3 | FRSC (Funding Regime-Switching Carry) | メタオーバーレイ | OHLCV+FR | 低 | 既存拡張 | - |
| R4 | LISRM (L1 Intra-Sector Rotation Momentum) | クロスセクション | OHLCV | 中 | 高 | TOP3 |
| R5 | S3I (Stablecoin Supply Surge Inflow) | オンチェーン外生 | OHLCV+API | 中 | 極高 | - |
| R6 | HLWI (HL Wick Imbalance OB proxy) | 形状非対称 | OHLCV | 低 | 中 | - |
| R7 | BTC.D Inflection Alt-Rotation | マクロ回転 | OHLCV+market | 低 | メタ層 | - |
| R8 | WEIR (Whale Exchange Inflow Reversal) | オンチェーン | API+OHLCV | 高 | 極高 | - |
| R9 | FToD (Funding Time-of-Day Tail Reversal) | 行動経済学 | OHLCV+FR | 低 | 高 | **TOP1** |
| R10 | IFTS (Implied Funding Term Structure) | 期間構造 | basis x2 | 高 | 極高 | - |

**Researcher TOP3 (検証推奨順)**: R9 FToD (1H で実装可能) → R1 FOPD (3項一致条件) → R4 LISRM (クロスセクション市場中立)

### Tip-scraper 15記事 (botter/Qiita/note/GitHub等)

| # | 名称 | ソース | 既存重複度 | 品質タグ | 採用判定 |
|---|------|--------|----------|---------|---------|
| T1 | ReconResilience_Live (運用層回復力) | Qiita ponfreelance | 低 (運用層) | [partial-edge][crypto-native] | 保留 |
| T2 | **LiqCascadeFade_v1** | Curupira blog | 中 | [strong-evidence][crypto-native][risky] | **検証推奨 TOP1** |
| T3 | OBImbalanceQuoteSkew (L2 真imbalance) | hftbacktest | 中 | [strong-evidence][crypto-native] | 条件付推奨 (tick data前提) |
| T4 | **MetaLabel_BTC_TripleBarrier** | richmanBTC/Zenn | 低 | [strong-evidence][partial-edge] | **検証推奨 TOP4** |
| T5 | **FundingNeutral_HL_vs_Spot** | Hummingbot | 低 (carry系) | [strong-evidence][crypto-native] | **検証推奨 TOP2** |
| T6 | **FundingSpread_CrossCEX** | FinanceFeeds/BingX | 低 | [strong-evidence][crypto-native][risky] | **検証推奨 TOP5** |
| T7 | CVD_PriceDivergence | Bookmap | 中 | [partial-edge][crypto-native] | 条件付 (taker buy/sell前提) |
| T8 | CointegPair_BTC_ETH_v2 | IJSRA 2026 | 高 (既棄却) | [partial-edge] | 保留 (レジーム別なら) |
| T9 | WhaleExchInflow_Short | Nansen | 低 | [partial-edge][crypto-native][unverifiable] | 保留 (有償依存) |
| T10 | **TripleSignal_OI_Funding_Liq** | Gate Wiki | 中 (既部分棄却) | [strong-evidence][crypto-native] | **検証推奨 TOP3** |
| T11 | PreMarket_TWAP_Convergence | Bybit/MEXC | 低 | [partial-edge][risky][crypto-native] | 保留 |
| T12 | SocialVelocity_Meme_v2 | Coinmonks | 高 (MemeMom重複) | [hype][partial-edge] | 保留 |
| T13 | InventorySkewMM | Hummingbot | 低 (純MM) | [strong-evidence][partial-edge][crypto-native] | 保留 (インフラ要件) |
| T14 | OI_PriceDivergence (1h/4h単独) | Bikotrading | 中 (既棄却) | [partial-edge][crypto-native] | 検証推奨 (ablation) |
| T15 | StablecoinDepeg_Arb | StablecoinInsider | 低 | [strong-evidence][crypto-native][risky] | 検証推奨 |

**Tip-scraper TOP5 (検証推奨順)**: T2 LiqCascadeFade → T5 FundingNeutral_HL → T10 TripleSignal_OI_Funding_Liq → T4 MetaLabel_BTC → T6 FundingSpread_CrossCEX

### 統合・優先候補 (重複統合後の検証順位)

| 統合優先度 | 候補 (Researcher/Tip-scraper) | 主要根拠 | 想定検証時間 |
|-----------|-------------------------------|---------|------------|
| **1** | R9 FToD = T (一部T10と重複) | 行動経済学的トリガー、1H実装、既存と独立 | 1H |
| **2** | R1 FOPD ≈ T10 TripleSignal_OI_Funding_Liq | 3項一致でクラウディング指標、既部分失敗を克服 | 半日 |
| **3** | T2 LiqCascadeFade_v1 ≈ R2 LCSF | 既存WF-OOS実証、stop-hunt限定でedge残存 | 半日 |
| **4** | R4 LISRM | クロスセクション市場中立、BTCベータ除去 | 半日 |
| **5** | T5 FundingNeutral_HL_vs_Spot | Carry系、既存directionalと相関≈0 | 1日 |
| **6** | T4 MetaLabel_BTC_TripleBarrier | 既存生存者の精度向上モジュール | 1日 |
| **7** | R5 S3I (Stablecoin Supply) | 外生キャッシュフロー先行指標 | 1日 |
| **8** | R8 WEIR (Whale Inflow) | オンチェーン非対称情報 | 1日+データ整備 |
