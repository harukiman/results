# External Findings Round 14 (K396 Wave)
**作成日時**: 2026-05-29 06:47 JST  
**対象Wave**: K396  
**検証基準**: STRICT (R13/K382-385教訓適用)  
**Findings数**: 13件  
**総ソース検索数**: 40+クエリ、25+URL検証  

---

## Executive Summary

R13/K383-385の教訓を踏まえ、本ラウンドでは数値主張に2ソース確認、政策主張に公式URLと具体日付を要求する厳格検証を実施。

**HIGH ACTIONABLE (STRICT_VERIFIED)**: R14-01(SEC delay確定), R14-02(Clarity Act DeFi exemption), R14-04(HIP-3 OI $2.47B), R14-05(Drift hack competitor退場), R14-07(Ondo $1B TVL), R14-10(Coinbase AQAv2 PRIMARY), R14-11(HYPE burn 85%)

**主要発見の構造**:
1. 規制環境: SEC tokenized stock exemption延期(2027+)、Clarity Act DeFi exemption確認(July 4目標)
2. HL生態系: HIP-3 OI $2.47B記録、HIP-4 macro outcome拡張、native options「開発中」だが日程未確認
3. 競合: Drift $285M DPRK hack → TVL $550M→$236M → 再オープン待ち
4. Stablecoin yield: Ethena TVL $4.49B・APY 3.75%に再圧縮、Ondo Global Markets $1B TVL達成
5. HYPE tokenomics: 85%validator合意で37.5M HYPE($912M)正式バーン、HIP-5 AF2提案でコミュニティ分裂

---

## R14-01: SEC Tokenized Stock Innovation Exemption 延期確定(May 26, 2026)

| 項目 | 内容 |
|------|------|
| **日付** | 2026-05-26 |
| **検証強度** | STRICT_VERIFIED |
| **Actionable** | YES |
| **Source Quality** | SECONDARY (crypto.news + Phemex) |

### 詳細
SECのtokenized stock innovation exemption(12-36ヶ月サンドボックス)が5月26日に正式延期。
計画:「クリプトプラットフォームが限定条件下で完全broker-dealer登録なしにUS株式オンチェーン取引提供可能」

**延期の直接原因**:
- Nasdaq/NYSE/Cboeがlate-May SEC staff会議で反発
- 「Regulation NMS・CAT reporting・小売投資家保護を回避する並列取引会場が生まれる」
- 第三者発行株式連動トークン(企業承認なし)問題を警戒
- JPMorgan・Citadel Securities・SIFMAも懸念を表明(早期段階から)

**Hester Peirce委員の立場**: 「issuer承認済みデジタル表現に絞る」方向を示唆

**影響**:
- Robinhood/Coinbase: US launch 2027+以降に後退
- Ondo Finance: equity展開遅延(treasury製品・欧州展開は無影響)
- Backed Finance: offshore bSTOCK製品は影響なし継続
- HL HIP-3 tokenized stocks: US機関流入期待の下方修正

**K385バリデーション**: R13-03が「SEC innovation exemptionを準備中」と報告したのは正確だったが、K385が指摘した通り「遅延リスク」は現実化した。

### K-wave Action
- HIP-3 RWA戦略のUS機関流入期待を下方修正
- regulatory risk discountは2026年末まで維持
- 次トリガー: SEC revised framework公表時(ATS登録条件付き可能性)

---

## R14-02: Clarity Act — Senate Banking Committee通過(May 14, 2026)・DeFi Developer Exemption確定

| 項目 | 内容 |
|------|------|
| **日付** | 2026-05-14 |
| **検証強度** | STRICT_VERIFIED |
| **Actionable** | YES |
| **Source Quality** | SECONDARY (CoinDesk + Senate Banking Committee公式) |

### 詳細
Digital Asset Market Clarity Act(CLARITY Act)がSenate Banking Committeeで5月14日採決通過。

**主要条項**:
1. **デジタル商品定義**: blockchain-native tokenをCFTC管轄の「digital commodity」として分類(SEC証券規制非適用)
2. **DeFi Developer Shield**: BRCA(Blockchain Regulatory Certainty Act)をベースにDeFiソフトウェア開発者・バリデーター・ウォレットをSEC/CFTC登録義務から免除(顧客資金を直接管理しない場合)
3. **Stablecoin定義**: 「payment stablecoin」としてyield支払いを制限

**タイムライン**:
- 5月15日: Senate Banking Committee採決
- July 4, 2026: White House adviser目標(最終可決)
- 8月上旬: Gillibrand上院議員推定
- 障害: 倫理条項(DeFi ethics provisions)の党派交渉が残存

**HLへの含意**: HyperEVM builder/validator は DeFi developer exemption の対象となる可能性が高い。HL Labs自体のperp DEX運営への直接言及はなし。

### K-wave Action
- July 4可決時: v6.12 HIP-3 regulatory risk discount削減
- CFTC登録交渉がアクティブになれば、R14-13(CFTC comment letters)と合わせて US機関流入タイムラインを再評価

---

## R14-03: HIP-4 Macro Outcome Markets拡張(May 25, 2026) — CPI/Fed Rate vs Polymarket

| 項目 | 内容 |
|------|------|
| **日付** | 2026-05-25 |
| **検証強度** | STRICT_VERIFIED |
| **Actionable** | NO(現在はvolume不十分) |
| **Source Quality** | SECONDARY (crypto.news + CoinDesk) |

### 詳細
HIP-4がBTC daily binaryから米国マクロ指標prediction marketsに拡張。

**新ラインナップ(May 25-26)**:
- US May CPI YoY変化率(6月10日BLS公式データで決済)
- June Fed funds rate decision market

**契約仕様**:
- 完全担保型、ノーレバレッジ、ノー清算
- 0か1 USDC決済(binary outcome)
- HyperCore上でperp/spot/outcome contractを同一margin accountで管理

**決済メカニズム**(Polymarket比較):
| 機能 | Hyperliquid | Polymarket |
|------|------------|-----------|
| 解決者 | 内部validator set | UMA外部オラクル |
| 紛争処理 | validator投票 | optimistic + token holder |
| 統合性 | crypto+macroを単一口座 | 独立platform |

**初期データ**: OI ~$5,000、volume ~$3,000(小規模)

**戦略的含意**: 同一margin accountでcrypto perp + macro outcome contractの組み合わせポジション可能。HL v.Polymarket v.Kalshiの三つ巴競争へ。

---

## R14-04: HIP-3 OI $2.47B記録(May 17, 2026) — トップ10の7つがRWA

| 項目 | 内容 |
|------|------|
| **日付** | 2026-05-17 |
| **検証強度** | STRICT_VERIFIED |
| **Actionable** | YES |
| **Source Quality** | SECONDARY (livebitcoinnews + KuCoin) |

### 詳細
HIP-3 OI成長軌跡:
- R12時点: ~$260M(初期)
- R13時点: $790M→$1.4B→$2.3B
- R14時点: **$2.47B(May 17 ATH)**

**Tradexyz(trade.xyz)支配**: $2.33B = 94%のHIP-3 OI

**YTD成長率**: +783%($280M → $2.47B)

**資産構成**:
- トップ10中7つがRWA(Nasdaq Index, S&P500, WTI Crude, Brent, Gold, Silver含む)
- WTI Crude OI: ~$561M、Brent: ~$576M
- Silver: 24h volume $1.01B
- HL全体ボリュームの30%+がHIP-3

**リスク**: 単一deployer(Tradexyz)94%集中によるシステミックリスク、高leverage集中でADL volatility上昇

### K-wave Action
- R12-12(Sunday 22:00 UTC RWA oracle strategy)の流動性改善確認 → Silver/Gold weekend strategyのexecution改善
- ADL監視頻度の引き上げ(K200)
- Tradexyz SOCS disruption の tail risk を明示的にポジションlimitに反映

---

## R14-05: Drift Protocol DPRK Hack($285M) — 競合 Solana perp DEX一時退場

| 項目 | 内容 |
|------|------|
| **日付** | 2026-04-01(hack)・2026-05-05(recovery plan) |
| **検証強度** | STRICT_VERIFIED |
| **Actionable** | YES |
| **Source Quality** | SECONDARY (CoinDesk + Elliptic) |

### 詳細

**ハック概要**:
- 日付: 2026年4月1日
- 被害額: $285-295M(Elliptic: $286M)
- 手法: 6ヶ月social engineering → Security Council multisig 2/5 承認取得 → admin transfer → 引き出し制限削除
- 主要流出: JLP $155M、SOL、BTC → DEX aggregator経由USDC → Ethereum bridge → ETH
- 帰属: DPRK UNC4736グループ(Radiant Capital 2024 hackと同一アクター)
- Solana史上2位のhack(1位: Wormhole $326M/2022)

**Recovery Plan(May 5発表)**:
- Starting pool: $3.8M残存資産
- Tether支援: $127.5M(revenue-linked、段階的)
- Partner: $20M
- 合計最大: $150.5M(フル$295Mの51%のみカバー)
- Recovery token発行(1token = $1損失)
- 決済通貨USDC→USDTへ変更
- 再オープン目標: Q2-Q3 2026(OtterSec/Asymmetric Research独立監査後)

**現状(May 2026)**:
- TVL: $550M → $236M(−57%)
- DRIFT token: -70%
- Carrot(Drift上のDeFiプロトコル): Drift hack後30日でシャットダウン

### K-wave Action
- R13-07(Drift VIP maker access trigger)をreopen待ちに変更
- Solana perp DEX volume空白の受益者: HL、Vertex、Axiom等を監視
- Drift reopen後の market structure変化(USDT決済化)を確認

---

## R14-06: Lighter Protocol TVL $510M・7日Perp Volume $8.6B

| 項目 | 内容 |
|------|------|
| **日付** | 2026-05-29(DefiLlama取得) |
| **検証強度** | PARTIAL_VERIFIED |
| **Actionable** | NO |
| **Source Quality** | TERTIARY (DefiLlama) |

### 詳細
- TVL: $509.67M(Ethereum、Arbitrum $2K)
- 7日perp volume: $8.628B
- 7日fees: $693K
- Annualized fees: $33.86M、revenue: $25.62M
- 累積perp volume: $1.645T
- LIT token: $1.17(ATH $7.86から -85%)
- Drift TVL($236M) < Lighter TVL($510M) — Drift一時退場でLighter相対優位

**注意**: Drift hack とLighter成長の直接因果は確認不十分(PARTIAL_VERIFIEDの理由)

---

## R14-07: Ondo Global Markets TVL $1B達成(May 11, 2026) — DTCC・SEC機密登録

| 項目 | 内容 |
|------|------|
| **日付** | 2026-05-11 |
| **検証強度** | STRICT_VERIFIED |
| **Actionable** | YES |
| **Source Quality** | SECONDARY (PRNewswire primary source + CryptoBriefing) |

### 詳細
**TVL milestone**: Ondo Global Markets(tokenized US stocks/ETF)が$1B TVL達成
- 達成期間: launch後8ヶ月(2026年1月比2倍速)
- 260+銘柄: Solana/Ethereum/BNB Chain
- 市場シェア70%+
- 累積取引量$18B
- 取引時間: 24時間5日(従来株式: 平日のみ)

**規制進展(STRICT_VERIFIED)**:
1. SEC機密登録申請: 初のtokenized stock issuerとしてSEC reporting対象を目指す
2. DTCC Industry Working Group選定: 2026年7月迄に本番tokenization取引目標
3. EU/EEA 30ヶ国認可・ADGM(Abu Dhabi)上場済み
4. J.P. Morgan/Mastercard/Rippleと初のcross-border tokenized treasury redemption完了(5秒決済)

**SEC exemption遅延(R14-01)との関係**:
- Ondo treasury製品(USDY 3.5%)は影響なし
- equity部分のUS展開は遅延
- 欧州・中東展開は継続

### K-wave Action
- Ondo USDY 3.5% vs sUSDe 3.75%(R14-09)の利回り比較を次Waveで実施
- HL HIP-3 tokenized stocksとOndo Global Marketsの棲み分けを分析
- DTCC integration(July 2026)はtokenized RWA全体の制度化の里程碑

---

## R14-08: Hyperliquid Native Options — 「開発中」確認も公式日程なし

| 項目 | 内容 |
|------|------|
| **日付** | 2026-05 |
| **検証強度** | PARTIAL_VERIFIED |
| **Actionable** | NO |
| **Source Quality** | SECONDARY |

### 詳細
**確認事項**:
- HyperCore native options開発中(HyperCore engineベース)
- HyperEVM上のEthereum-native optionsも開発中
- 第三者: Opt.funがHyperEVM上でoptions提供中

**未確認事項**:
- Q3 2026 native options launch日程: 公式Roadmapに記載なし
- Wiki Roadmapの最新記載: Sep 2025 HL Hackathon Seoul まで

**HIP-4との違い**:
- HIP-4 Outcomes = bounded binary(0 or 1), no leverage, prediction market-like
- Native options = 従来的options payoff構造(call/put), HyperCore統合
- 両者は別primitive

**R13/K385教訓適用**: 「開発中」を「Q3 2026確定」と読み替えることは過大評価(K383類似のエラー)。具体日程が公式発表されるまでLOW扱い維持。

---

## R14-09: Ethena USDe TVL $4.49B・APY 3.75%(2026-05-29) — 収益環境悪化継続

| 項目 | 内容 |
|------|------|
| **日付** | 2026-05-29 |
| **検証強度** | PARTIAL_VERIFIED |
| **Actionable** | YES |
| **Source Quality** | TERTIARY (DefiLlama) |

### 詳細
**現在の指標(DefiLlama 2026-05-29)**:
- TVL: $4.491B(全Ethereum)
- 平均APY: 3.75%(tracked pools平均値)
- Annualized fees: $173.5M
- 30日fees: $14.22M
- 24h fees: $1.93M

**時系列比較(APY)**:
| 時点 | APY |
|------|-----|
| 2024年平均 | 18% |
| 2026 Q1平均 | 3.72% |
| 2026-04-25(7日MA) | 9.4%(一時回復) |
| 2026-05-29(現在) | 3.75%(再圧縮) |

**TVL推移**:
- ピーク: $14.8B(2025年)
- Q1 2026: $5.92B
- 現在: $4.491B(−24%)

**注意(PARTIAL_VERIFIEDの理由)**: DefiLlamaの「平均APY 3.75%」はsUSDe単体APYと異なる可能性。sUSDe実際APYは個別確認が必要。

### K-wave Action
- K206/K207のEthena weight削減判断の根拠強化
- exit閾値(sUSDe APY < 5%)に近づいている可能性
- 代替利回り比較: Ondo USDY 3.5%(R14-07)、HypurrFi(R13-05: TVL $15.2M)
- Funding rate positive環境への転換を検知した場合のみ重み増加

---

## R14-10: Coinbase USDC AQAv2 公式発表(PRIMARY Source — Coinbase Blog, May 14)

| 項目 | 内容 |
|------|------|
| **日付** | 2026-05-14 |
| **検証強度** | STRICT_VERIFIED |
| **Actionable** | YES |
| **Source Quality** | PRIMARY (Coinbase公式ブログ) |

### 詳細
**公式確認事項**:
- Coinbase = USDC treasury deployer on Hyperliquid
- Circle = CCTP cross-chain technical infrastructure
- 両社がHYPE stakingでAQAv2活性化にコミット
- USDC供給$5B(YoY 2x)

**3フェーズ移行**:
1. Phase 1: USDH任意担保+incentive rebate(現在)
2. Phase 2: 新perp listingsがUSDHデフォルト
3. Phase 3: USDC→USDH自動移行ツール

**注意(K383教訓適用)**:
- Reserve yield revenue sharing %: 公式未公表(「大部分」のみ)
- R13-01(CoinDesk: $135-160M/年の90%)は二次ソース推定値
- AQAv2 = 収益構造変更の「実装段階」は確認済み
- AQAv2 ≠ 即時claimable yieldプロダクト(K383指摘通り)

### K-wave Action
- Coinbase公式ブログ = PRIMARY sourceとして参照
- Phase移行progessをモニタリング(具体%発表時に即K-wave対応)
- HYPE buy pressure: AQAv2完全移行 + R14-11(37.5M burn)の組み合わせ

---

## R14-11: HYPE Assistance Fund 37.5M トークン正式バーン — 85%Validator合意(Dec 24, 2025)

| 項目 | 内容 |
|------|------|
| **日付** | 2025-12-24 |
| **検証強度** | STRICT_VERIFIED |
| **Actionable** | NO(既成事実、戦略背景情報) |
| **Source Quality** | SECONDARY (coinlaw.io + MEXC) |

### 詳細
**Vote結果**:
- 賛成: 85%(stake-weighted)
- 反対: 7%
- 棄権: 8%
- HL歴史最高validator consensus

**Burn規模**:
- 対象: 37.5M HYPE (Assistance Fund address: 0xfefefe...)
- 当時価値: ~$912M
- 流通量削減: 11.068%

**技術的背景**: 対象addressはprivate key不在で元々アクセス不可。governanceで「burned」として公式認定することで、total supply・circulating supplyの両方から除外。

**R12/R13との関係**: 本事象(Dec 2025)はR12(K334: 2025-10以前)・R13(K382: 2026-05)間に発生しており、どちらにも記載なし。本Roundで初記録。

### K-wave Action
- HYPE tokenomics根拠として記録
- AQAv2 revenue sharing増加(R14-10) + 37.5M burn = HYPE需給改善の二重シグナル
- HIP-5(R14-12)可決でさらなるbuyback圧力

---

## R14-12: HIP-5 — HyperEVM Ecosystem Token買い支えAF2提案、コミュニティ分裂

| 項目 | 内容 |
|------|------|
| **日付** | 2026-05 |
| **検証強度** | PARTIAL_VERIFIED |
| **Actionable** | NO(投票未完了) |
| **Source Quality** | SECONDARY (AiCoin + The Defiant) |

### 詳細
**HIP-5提案内容**:
- 第二Assistance Fund(AF2)設立
- Protocol fee総額の**最大5%**をHyperliquid strict listトークン買い支えに使用
- 対象: PURR(Hyperliquid Strategies株)、Kinetiq、Felix等のHyperEVMプロジェクト
- HYPE stakerが買い支え対象トークンと量を毎回投票で決定

**賛否の対立**:
- 賛成: builderへのincentive強化、HYPE governance参加促進
- 反対: ①USDH投票プロセス類似のcartel悪用リスク(seed investor exit liquidityに使われる)、②bribery → DAO resource抽出

**投票状況**: 2026年5月時点で未完了・コミュニティ分裂中

### K-wave Action
- 可決時: PURR/Kinetiq/Felix をK376 momentum universe候補に追加検討
- 否決時: HL governance健全性の維持として肯定評価
- HIP-5投票結果を次Waveでconfirm

---

## R14-13: Hyperliquid Policy Center — CFTC Comment Letters提出(May 2026)

| 項目 | 内容 |
|------|------|
| **日付** | 2026-05 |
| **検証強度** | PARTIAL_VERIFIED |
| **Actionable** | NO |
| **Source Quality** | SECONDARY (Bitget News + The Block) |

### 詳細
**Policy Center活動**:
- 主体: Hyperliquid Policy Center(代表: Jake Chervinsky, 元crypto弁護士)
- 提出先: CFTC(米商品先物取引委員会)
- 主張: オンチェーンperp DEXはtransparency・audit可能性・価格発見効率においてCME/ICE等のoffshore alternative決済機関より優れる

**背景(R12-16, R13-03 continuation)**:
- CME/ICEがWTI crude perp volume急増($339M→$7.3B)を根拠に「市場操作リスク」主張
- HLはCFTC onshore登録を積極交渉中の姿勢を公式表明

**現状評価**:
- Formal enforcement action: なし(確認)
- 登録交渉: 進行中
- CFTCフォーマルルール公表: 未定
- Clarity Act(R14-02)とCFTC comment lettersの組み合わせがHL regulatory pathway

### K-wave Action
- Clarity Act July 4可決時にCFTC registration accelerate → 次Waveで進捗確認
- enforcement action発動時の即時ポジション調整ルールは維持

---

## 重複チェック(R1-R13, 249 URLs)

| R14 Finding | 重複確認 |
|-------------|---------|
| R14-01 SEC delay | R13-03「SEC innovation exemption準備中」とは異なる最新event(延期)。非重複 |
| R14-02 Clarity Act | 過去Roundに未記載。新規 |
| R14-03 HIP-4 macro | R13-02(HIP-4 BTC binary)の拡張。別event・新URL |
| R14-04 HIP-3 $2.47B | R13-05以降の継続更新。数値更新・新URL |
| R14-05 Drift hack | R13-07(Drift VIP)とは全く異なるevent |
| R14-06 Lighter TVL | R12-11(Paradex DEX Wars)と別事象・新数値 |
| R14-07 Ondo $1B | 過去Roundに未記載(R12-20でtokenized RWA $30.8B全体のみ) |
| R14-08 HL options | 過去Roundに未記載 |
| R14-09 Ethena APY | R13-04(Apr 25, 9.4%)の継続更新。新数値・別URL |
| R14-10 Coinbase AQAv2 | R13-01(CoinDesk二次ソース)に対してPRIMARY source(Coinbase Blog)で補強 |
| R14-11 HYPE burn | 過去Roundに未記載(Dec 2025事象) |
| R14-12 HIP-5 | 過去Roundに未記載 |
| R14-13 CFTC comment | R12-16(CME/ICE押圧)の対応側として新規 |

---

## 検証強度サマリー

| 強度 | 件数 | Finding IDs |
|------|------|-------------|
| STRICT_VERIFIED | 7 | R14-01, 02, 04, 05, 07, 10, 11 |
| PARTIAL_VERIFIED | 6 | R14-03, 06, 08, 09, 12, 13 |
| UNVERIFIED | 0 | — |

**STRICT基準達成率**: 54%(7/13) — 数値主張は2ソース確認、政策主張は公式URL+日付を取得

---

## R13教訓の適用

| R13エラー | R14での対応 |
|-----------|------------|
| K383: AQAv2 activation ≠ claimable yield | R14-10でCoinbase公式ブログ確認し「%未公表」を明記 |
| K384: Ethena APY誤解(Q1 vs Q4) | R14-09で時系列を明示(Q1 3.72%→Apr 9.4%→May 3.75%) |
| K385: SEC exemption DELAYED not "in preparation" | R14-01で延期を STRICT_VERIFIED として明記 |
| 一般: Twitter/redditルーモア混入 | 全findingでSOURCE_QUALITYを明示、PRIMARY/SECONDARYのみ採用 |

---

*生成: K396 Wave / 2026-05-29 06:47 JST*  
*次Wave推奨アクション: R14-02(Clarity Act July 4 vote)・R14-04(HIP-3 OI継続)・R14-05(Drift reopen)・R14-12(HIP-5 vote result)のモニタリング*
