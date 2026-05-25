# External Findings Round 11
**Date**: 2026-05-25 (JST)
**Strategic Focus**: HL HIP-3 RWA拡張、HIP-4予測市場、Portfolio Margin、ML/RL allocator、microstructure research
**Cumulative**: R1-R10: 222件 → R11追加: 20件 → **累計242件**

---

## Executive Summary

Round 11では7つの戦略軸から20件の新規findingを収集。最重要発見は以下3点:

### Top 3 Actionable for K311+

**#1 [R11-01/02/04] XAG(銀)・WTI原油のHL HIP-3流動性確立 → K297ユニバース拡張Ready**
- Silver OI $100M超、WTI OI $200M超(2026年4月時点)
- Ripple Primeが機関向けに金/銀/原油perpを統合済み
- K297の衛星ユニバースをPAXG/SPXのみから拡張する十分な流動性基盤が整った

**#2 [R11-09/10] CEX→DEX情報フロー一方向 → K302a用CEXシグナル先行指標化**
- 26取引所・812シンボルの実証: CEXがDEXに61%高い統合度、逆因果ゼロ
- FR有意スプレッドの84%がCEX-DEXペア発生
- Binance/Bybitの8時間FR差異をHLの1時間FR予測への先行シグナルとして設計可能

**#3 [R11-13] 3状態HMM + Bayesian非同次推移確率 → K280 regimeフィルタ追加**
- bull/bear/neutral 3状態モデルがBTC 4h足で2状態を有意に上回る
- K280のentryフィルタとして組み込み → bearish neutralでの誤エントリー削減

---

## Full Findings (20件)

### カテゴリ: HL RWA拡張 (4件)

#### R11-01: HyperLiquid HIP-3 RWA OI $1.74B ATH — WTI/Silver/SPX主導
- **URL**: https://cryptonews.com/news/hyperliquid-hip-3-open-interest-hits-record-tokenized-commodities/
- **日付**: 2026年4月
- **要約**: HIP-3 RWA OIが$1.74B ATHを更新。WTI原油($200M)、Silver($100M)、S&P 500($420M)が牽引。Trade.xyz が91.3%シェア。XAG/WTIがK297拡張の実現可能性を直接証明するデータ。
- **K302a直交性**: K297はPAXG/SPXのみ。XAGの$100M+ OIは拡張候補として実行可能な閾値を超えた。

#### R11-02: S&P Dow Jones×Trade[XYZ]正式ライセンス: SPX perp 24/7合法化
- **URL**: https://www.prnewswire.com/news-releases/sp-dow-jones-indices-licenses-sp-500-to-tradexyz-for-perpetual-contracts-on-hyperliquid-302717487.html
- **日付**: 2026年3月18日
- **要約**: S&P DJIがTrade[XYZ]にSPX指数の公式ライセンスを供与。K297 SPX衛星が規制ライセンス基盤の上で稼働中。日次ボリューム$22B、上位30市場中23市場がTradFi資産。
- **K302a直交性**: K297前提が制度的に強化されたことを確認。流動性増加でFR edgeが変化する可能性の監視が必要。

#### R11-04: Ripple Prime×HyperLiquid: 機関向け金・銀・原油perp統合(RLUSD担保)
- **URL**: https://coinpedia.org/news/ripple-prime-expands-hyperliquid-integration-now-trade-gold-silver-and-oil-on-chain/
- **日付**: 2026年3月30日
- **要約**: Ripple PrimeがHIP-3をGold/Silver/WTI perpsに拡張。CME週末閉鎖時の中東紛争ヘッジ需要が直接導入契機。機関がRLUSD担保で単一フレームワークからクロスマージン管理。
- **K302a直交性**: 機関プライムブローカー経由のRWA perp流入。XAG/WTI追加時の機関流動性ソースとして重要。

#### R11-05: Tokenized Gold週末価格発見100%: PAXG/XAUtがCME閉鎖中の唯一公開市場
- **URL**: https://cointelegraph.com/news/tokenized-gold-weekend-price-discovery-cme-closed
- **日付**: 2026年3月
- **要約**: CME停止中(金曜17時ET〜日曜18時ET)にPAXG/XAUtが金価格形成を独占。$4.4B時価総額(1年177%増)。機関マクロデスクが週末gap riskシグナルとして監視。
- **K302a直交性**: K297 PAXGのweekend edgeの理論的根拠を確立。FR/spread戦略の週末効果の追加検証が必要。

---

### カテゴリ: HLエコシステム (4件)

#### R11-03: HyperLiquid Portfolio Margin + BLP Pre-Alpha: BTC担保・USDH借入
- **URL**: https://thedefiant.io/news/defi/hyperliquid-launches-portfolio-margin-and-blp-pre-alpha
- **日付**: 2026年3月
- **要約**: Portfolio Marginでspot+全perp統合margining。$5M+ボリューム要件。BTC担保でUSDH/USDC最大$1M借入。RWA perp(SPX/PAXG/XAG)を同一口座で保有し証拠金効率最大化。
- **K302a直交性**: K302aは固定配分。Portfolio Marginで複数戦略間の相殺が可能になりK297証拠金効率が向上。

#### R11-06: HyperLiquid HIP-4: 予測市場、ゼロ手数料、初日3×Polymarket+Kalshi
- **URL**: https://www.dlnews.com/articles/markets/hyperliquid-launches-prediction-markets-for-bitcoin/
- **日付**: 2026年5月2日
- **要約**: ゼロ手数料のイベント予測市場をperp同一口座から取引可能。初日出来高がPolymarket+Kalshi合算の3倍。Arthur Hayes: HYPEが予測市場での競争兵器。マクロイベントヘッジの新次元。
- **K302a直交性**: perp戦略に加え、イベント駆動バイナリーpositionを統合した複合戦略が可能。K311+で検討。

#### R11-07: HypurrFi×Euler Finance: HyperEVM上の分離リスク貸借市場、BLP担保化
- **URL**: https://www.blocmates.com/news-posts/hypurrfi-brings-euler-finance-to-hyperliquid-s-growing-ecosystem
- **日付**: 2026年Q1
- **要約**: Eulerの貸借スタックをHyperEVM上にデプロイ。各資産独立リスクパラメータ。BLPポジション担保化。$2.3B deposit実績。perp利益のHyperEVM側lending活用が可能。
- **K302a直交性**: K302aはHyperCore完結型。HypurrFiはperp→lending複合資本循環の新経路を開く。

#### R11-08: HyperLiquid USDH: Coinbase/Circle支援、GENIUS Act対応ステーブルコイン
- **URL**: https://www.coingecko.com/learn/what-is-usdh-hyperliquid-native-stablecoin
- **日付**: 2026年5月
- **要約**: 短期米国債担保でGENIUS Act対応。Coinbase が USDH連動資産取得権確保。供給上限500M/借入上限100M。K302aのリスク点検: 将来的にUSDC→USDH移行でsettlement通貨が変わる可能性。
- **K302a直交性**: 現在USDC清算前提の戦略設計。USDH移行フェーズでの影響を監視すべき。

#### R11-20: HyperLiquid 2026 H2ロードマップ: ネイティブOptions Q3、HYPE-margin perp
- **URL**: https://www.hypewatch.io/blog/hyperliquid-complete-guide-2026
- **日付**: 2026年5月
- **要約**: (1)ネイティブOptions Q3 2026 (2)HYPE担保perp (3)新spot bridge (4)バリデーター50+ノード (5)HyperEVM precompile追加。オプション市場はevent-driven hedging戦略の基盤。
- **K302a直交性**: Q3のoptionローンチはK311+設計前提を変える。delta-hedged vol play等の新次元が開く。

---

### カテゴリ: Microstructure Research (2件)

#### R11-09: Temporal Dynamics: perp先物市場マイクロストラクチャー、CEX→DEX一方向情報フロー
- **URL**: https://www.mdpi.com/2227-7072/14/5/103
- **日付**: 2026年5月(2025年11月〜2026年1月データ)
- **要約**: 26取引所・812シンボルの実証。CEX統合度がDEXより61%高い。情報フローCEX→DEX一方向。離散的構造変化なく緩やかドリフト。K302aのHL戦略がCEXシグナルをラグして受け取ることを実証。
- **K302a直交性**: Binance/OKX等CEXのFR/OIシグナルをHL戦略の先行指標として組み込む設計根拠。

#### R11-10: Two-Tiered FR Market: CEXタイト・DEXフラグメント、スプレッドの84%がCEX-DEXペア
- **URL**: https://www.mdpi.com/2227-7390/14/2/346
- **日付**: 2026年1月
- **要約**: FRマーケットが2層構造。有意スプレッド(>=20bps)の84%がCEX-DEXペア。CEX 8h/DEX 1h settlementの差異が主要アービトラージ源泉。
- **K302a直交性**: CEX-DEX FRスプレッドをlongする戦略は既存K298 predictedFundingとは独立した新軸。

---

### カテゴリ: Funding Rate Research (1件)

#### R11-11: Funding-Aware Optimal Market Making for Perpetual DEXs (arxiv 2605.06405)
- **URL**: https://arxiv.org/abs/2605.06405
- **日付**: 2026年5月7日
- **要約**: Funding rateが確率的状態変数のときのperp DEX最適流動性供給。HJBスキームでbid/askオフセット最適化。HL ETH/BTC/SOLでキャリブレーション。古典AS比でparafomance改善+inventory RMS低下。
- **K302a直交性**: K302aはtaker戦略。HL makerとしてのFR-aware quotingはHLP/BLPに適用。K311以降でmaker satellite追加の理論基盤。

---

### カテゴリ: Regime Detection (1件)

#### R11-13: HMM 3状態: Bitcoin 2024-2026 Bayesian非同次推移確率 (Preprints 202603.0831)
- **URL**: https://www.preprints.org/manuscript/202603.0831
- **日付**: 2026年3月11日
- **要約**: BTC 4h足2024-2026のHMM分析。3状態(bull/bear/neutral)モデルが2状態を有意に上回る。非同次推移確率+Bayesian推定で動的市場挙動を捕捉。
- **K302a直交性**: K302aはregimeフィルタ未搭載。3状態HMMをK280 entryフィルタに使うことで誤エントリー削減。

---

### カテゴリ: ML Research (5件)

#### R11-14: Wavelet-Transformer: F&Gの多重時間スケール分解→暗号通貨価格予測 (MDPI Algorithms 2026)
- **URL**: https://www.mdpi.com/1999-4893/19/2/101
- **日付**: 2026年1月
- **要約**: Daubechies-4ウェーブレット4レベルでF&Gを5周波数帯に分解。高ボラティリティレジームで最大パフォーマンスマージン。210万パラメータのwavelet強化transformer。
- **K302a直交性**: K302aはsentimentフィルタ未搭載。Wavelet-TransformerによるF&G多重分解でshort/mediumタームsentimentシフトを早期検知。

#### R11-15: Meta-RL-Crypto: Transformer+RL Actor-Judge-MetaJudge閉ループ (arxiv 2509.09751)
- **URL**: https://arxiv.org/abs/2509.09751
- **日付**: 2025年9月
- **要約**: Llama-7Bベース自己改善RL。Actor/Judge/MetaJudge 3役割閉ループ。on-chain+news+sentimentを統合処理。追加人間監督なし。K198 Ridge era後の次世代ML allocator候補。
- **K302a直交性**: K280はRidge回帰ベース。Meta-RL-Cryptoはself-improving型で非定常市場適応力でRidgeの根本的限界を超える。

#### R11-16: Transformer Actor-Critic + VAEトレンド表現: Expert選択型動的perp portfolio (ScienceDirect 2026)
- **URL**: https://www.sciencedirect.com/science/article/abs/pii/S1568494625010087
- **日付**: 2026年
- **要約**: Transformer VAEで非絡み合いトレンド表現。Actor-criticがexpert strategyプールから動的選択。Markowitz benchmarkをreturn/sharpe両面で上回る。
- **K302a直交性**: K302aはK280 80%+K297 20%固定配分。動的配分比によりK297 RWA衛星への比率をregime適応的に変更できる。

#### R11-19: Deep RL Free-Energy: Riemannian幾何学的取引コスト+Carnot効率限界 (MDPI Risks 2026)
- **URL**: https://www.mdpi.com/2227-9091/14/5/103
- **日付**: 2026年5月
- **要約**: PPOエージェントをFisher情報多様体上のgeodesic slippage(幾何学的取引コスト)で訓練。Wasserstein-2レジーム遷移コスト。5資産中4で flat-fee baselineより統計的優位なSharpe達成。ポートフォリオ効率のCarnot限界を理論・実証両面で導出。
- **K302a直交性**: 取引コストを幾何学的に再定義する根本的に異なるアプローチ。K311でより精緻なコストモデリングに活用可能。

---

### カテゴリ: Onchain Research (2件)

#### R11-17: On-Chain Flow Forecasting: USDTネット流入がBTC/ETH 1時間リターンを正に予測 (arxiv 2411.06327)
- **URL**: https://arxiv.org/abs/2411.06327
- **日付**: 2025年9月
- **要約**: BTC/ETH/USDTの1-6時間頻度on-chain flow(2017-2023)。USDT取引所ネット流入がBTC/ETHリターンを複数区間で正に予測。ETHネット流入はETHリターンを負に予測。USDT流入=流動性供給→ボラティリティ低下。
- **K302a直交性**: K302aはcandle+FR/OIベース。USDTon-chain flowは外部独立シグナルで既存K280 entryフィルタへの直交性あり。

#### R11-18: Intraday Functional PCA: 24/7暗号通貨リターン関数予測、KL動的ファクターモデル (arxiv 2505.20508)
- **URL**: https://arxiv.org/abs/2505.20508
- **日付**: 2026年5月
- **要約**: Journal of Forecasting掲載。BTC時系列にFPCA適用。KL動的ファクターモデルでfunctional↔discrete-timeを橋渡し。1時間・15分サンプリングで未完関数の予測アルゴリズムを開発。条件付き異分散性考慮でinterval予測改善。
- **K302a直交性**: OHLCVベースの既存手法と異なる関数的アプローチ。24/7連続市場に最適化された予測手法として将来の signal engineに組み込み候補。

---

## K297 RWA拡張候補サマリー (Special Focus)

| 資産 | HL OI | 日次ボリューム | 機関統合 | 拡張Ready |
|------|--------|---------------|----------|-----------|
| XAG (銀) | $100M+ | $300M+ | Ripple Prime経由 | **Yes** |
| WTI原油 | $200M+ | $600M+ | Ripple Prime経由 | **Yes** |
| S&P 500 | $420M | $10B+ | S&P DJIライセンス | **既存** |
| PAXG (金) | 既存 | 既存 | 週末独占価格形成 | **既存** |
| NASDAQ, Tesla | 流動性確認中 | - | HIP-3 permissionless | 要検証 |

**推奨**: K311でXAGをK297ユニバースに追加(Silver OI $100M超、Ripple Prime機関フロー確認済み)

---

## 重複確認 (R1-R10 vs R11)

- arxiv 2506.08573: R10にHTMLバージョンURL含む → R11-12を削除、代わりにR11-19(MDPI Risks DRL)を含める
- CoinDesk portfolio marginURL: R10に `cryptopolitan.com/hyperliquids-newest-portfolio-margin` 含む → R11-03はThe Defiant URLで差別化
- CoinDesk $1.2B記事: R10に含む → R11-01はcryptonews.com($1.74B ATH)で差別化
- CoinGecko HIP3/HIP4記事: R10に含む → R11-06はDL News URLで差別化
- 全20件のURLがR1-R10と異なることを確認済み
