# 4-way mix 実運用デプロイガイド

このドキュメントは、本研究で「使用可能」認定された **4-way mix** 戦略を実MEXC先物アカウントでライブ運用するための実践的手順です。

---

## 警告

- **過去のバックテストは将来の結果を保証しない**。crypto 市場は非定常、レジーム変化リスクあり。
- 本ガイドは **教育・研究目的**。実運用は自己責任。
- **「日利10%」は実在しない**。本戦略の現実上限は MC median +462%/年 @ 10x レバ (破産確率 0.6%)。
- 最初は **必ず paper trading** (現在 daemon 稼働中) で 30日以上検証してから少額ライブ運用に進む。

---

## Phase 1: 環境準備 (Day 0, 30分)

### 必要なもの
- MacOS or Linux マシン (Windows 未検証)
- MEXC futures アカウント (API key 必要)
- Bybit アカウント (Funding rate データ取得用、無料 read-only OK)
- Python 3.11+ (本リポジトリの `.venv311/` を流用可)

### Step 1.1: リポジトリ clone
```bash
git clone https://github.com/harukiman/results.git crypto-lab
cd crypto-lab
```

### Step 1.2: Python 環境
```bash
python3.11 -m venv .venv311
.venv311/bin/pip install -U pip
.venv311/bin/pip install ccxt pandas numpy scipy statsmodels matplotlib plotly httpx pyarrow tqdm
```

### Step 1.3: MEXC API key 設定
```bash
# ~/.zshrc または .bashrc に追加
export MEXC_API_KEY="your_key_here"
export MEXC_API_SECRET="your_secret_here"
```
**重要**: API key には **futures trading 権限のみ**、出金権限は OFF。

### Step 1.4: cache directory 作成
```bash
mkdir -p cache logs
```

---

## Phase 2: Paper Trading (Day 1-30, 30 日間)

### Step 2.1: paper trade daemon インストール
```bash
cp com.cryptolab.paper-trade-4way.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.cryptolab.paper-trade-4way.plist
launchctl list | grep com.cryptolab
```

daemon は4時間ごと (UTC 0/4/8/12/16/20 の 15分後) 自動実行。

### Step 2.2: 初回手動テスト
```bash
.venv311/bin/python paper_trade_4way_mix.py
```
出力: `paper_trades_4way.json` に状態保存。

### Step 2.3: 30日後の評価
```bash
# 30日後に集計
.venv311/bin/python -c "
import json
d = json.load(open('paper_trades_4way.json'))
print('Initial:', d['initial_capital_usd'])
print('Current:', d['equity_usd'])
print('Closed trades:', len(d['closed_trades']))
print('Sharpe:', ...)  # 計算ロジック追加
"
```

**判定**:
- ✅ Backtest Sharpe (+3.61) と 30日 paper Sharpe の差が ±0.5 以内 → Phase 3 進行可
- ❌ 差が大 → 戦略再評価必要、ライブ運用見送り

---

## Phase 3: Small Live Trade (Day 31-90, 小額)

### Step 3.1: ライブ API クライアント追加
`live_trade_4way_mix.py` を新規作成 (paper_trade_4way_mix.py を base に):
```python
import ccxt
exchange = ccxt.mexc({
    'apiKey': os.environ['MEXC_API_KEY'],
    'secret': os.environ['MEXC_API_SECRET'],
    'options': {'defaultType': 'swap'},  # USD-M perpetual
})
# 既存の paper シミュレーション部分を 実 order placement に置換
```

### Step 3.2: 初期資金
- **$1,000** (絶対損失上限 = 5% = $50/月想定)
- **レバ 1x** で開始 (Phase 4 で段階拡張)
- 全 strategy axis フル有効化

### Step 3.3: 異常検知
- 1日 -3% を超えるDDが発生したら **即停止 + 調査**
- 90日 paper のworst day (-1.87% p5) を超える → 構造異常

### Step 3.4: 60日後の評価
- 実 Sharpe vs paper Sharpe の差
- 実コスト (slippage) vs backtest 想定 (-0.07%/side) の検証
- レバ拡張可否決定

---

## Phase 4: Scale-up (Day 91-180)

### Step 4.1: レバ段階拡張
- 90日 ライブ実績 OK → レバ 2x
- さらに 30日 OK → 3x
- 6ヶ月通算 OK → 5x (保守的上限)
- **10x は非推奨** (Kelly Quarter で破産 0.6% だが、実取引でのスリッページ拡大で破産確率上昇可能性)

### Step 4.2: 資金スケール
- $1,000 → $10,000 (月毎 30-50% step)
- $10,000 → $100,000 (慎重に、流動性検証必要)
- $100,000+ は MEXC スポット流動性に注意

### Step 4.3: 監視
- 毎日エクイティチェック
- 月次 Sharpe 集計
- レジーム変化 (Wave K8 の rolling 90日 100% positive 維持) 監視

---

## Phase 5: 長期運用 (Day 181+)

### Step 5.1: 定期再評価 (四半期)
- 全戦略軸の最新 Sharpe を計算
- パラメータ drift があれば調整 (再 backtest)
- 新規 strategy 候補の検討 (本研究で 23% 成功率)

### Step 5.2: リスク管理
- 月次 DD 上限: -5%
- 月次 Sharpe 下限: +1.0 (3ヶ月連続下回ったら停止検討)
- 取引所多様化: MEXC 70%, Bybit 30% (流動性分散)

### Step 5.3: 知見の共有
- 毎月の運用結果を `RESEARCH_LOG.md` に追記
- 新たなレジーム発見、戦略改善を継続記録

---

## トラブルシューティング

### Q: paper_trade daemon が動作しない
```bash
launchctl list | grep paper-trade  # status 確認
cat logs/paper_trade_4way.err  # エラー確認
```

### Q: BTC vol_z データが古い
```bash
# キャッシュ古いとシグナル不正確
rm cache/BTCUSDT_4h_*.parquet
.venv311/bin/python paper_trade_4way_mix.py  # 再取得
```

### Q: シグナル数が少ない
- 現在のレジームでは ATR/FOPD 発火条件が稀。本研究実測でも 78% の日は flat。
- 数週間 zero signal も normal range。

### Q: 大暴落で損失
- Wave K8 stress test 結果: 過去730日内 BTC -25% でも 4-way mix は +1.85% 維持
- もし大暴落で 4-way mix が-3% 超なら **構造的異常** = 即停止、研究フェーズに戻る

---

## 重要な数値リファレンス

| 項目 | 値 | 出典 |
|------|-----|------|
| 730日 Sharpe | +3.61 | Wave K13 audit |
| Bootstrap median | +3.54 | Wave K7 |
| 95% CI lower | +2.73 | Wave K7 |
| Max DD (730d) | -1.8% | Wave K13 |
| Calmar | 36.65 | Wave K13 |
| 90日 windows 100% positive | 100% | Wave K15 |
| MC ruin 5x lev | 0% | Wave K1 |
| MC ruin 10x lev | 0.05% | Wave K1 |
| Hansen SPA p | 0.0 | Wave K2 |
| White RC p | 0.001 | Wave K2 |

---

## サポート

本研究の詳細: `RESEARCH_LOG.md`, `RESEARCH_SUMMARY.md`, https://harukiman.github.io/results/report.html
全戦略レジストリ: `STRATEGY_REGISTRY.json`
質問: GitHub Issues

---

*Last updated: 2026-05-24 06:25 JST*
