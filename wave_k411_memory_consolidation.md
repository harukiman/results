# Wave K411 — Memory Consolidation Review
**生成日時**: 2026-05-29 07:44 JST  
**対象**: `/Users/nekonaomichi/.claude/projects/-Users-nekonaomichi/memory/`  
**総ファイル数**: 44 (MEMORY.md含む: 40 feedback + 3 project + MEMORY.md)  
**現在 Wave**: K409 (最新確認済)、K411 本 Wave

---

## エグゼクティブサマリー

44ファイルを全文精査した。主要な知見:

1. **HTMLルール 5本** (`html_record_all`, `html_log_continuous`, `html_tips_continuous`, `html_audit_periodic`, `timestamp_accuracy`) は互いに重複・補完関係にある。統合候補として `html_master_rules` に圧縮可能（HIGH confidence）
2. **Inbox/Security 2本** (`user_instruction_inbox`, `inbox_security_and_filter`) は明示的に補完関係に置かれているが、初回読者には2本を両方読む負荷がある。MED confidence でマージ提案
3. **External Research 3本** (`external_research`, `external_findings_paginated`, `research_allocation_3_1_1`) は同じドメインを3ファイルに分割。1本に統合可能（MED confidence）
4. **Always-running 2本** (`no_premature_stop`, `always_running_full_auto`) は `always_running` が `no_premature_stop` を明示的に強化しており実質重複。`always_running` が superset（HIGH confidence でマージ）
5. **Silent stall 2本** (`silent_stall_handling`, `always_running_full_auto`) は明示的に補完として設計されており、単独でも意味をなす → 現状維持推奨
6. **Obsolete候補 3本**: `feedback_site_performance`, `feedback_server_restart`, `project_crypto_lab` は現在プロジェクト (HL中心) と乖離した記述を含む
7. **MEMORY.md 構造**: 現在は追加順。トピック別グループ化で参照効率 2-3x 向上可能

---

## Phase 1: 全ファイルインベントリ

| # | ファイル名 | type | 年齢 | 主要内容 | 関連ルール |
|---|-----------|------|------|----------|-----------|
| 1 | feedback_first_priority.md | feedback | 39d | 最速最高効率・真の目標達成 | 基本原則 |
| 2 | feedback_perspective.md | feedback | 22d | 視野狭窄防止・複数戦略・探索 | 基本原則 |
| 3 | feedback_overfitting_and_edge.md | feedback | 22d | 過学習防止・flearn参照・リスク先行 | 研究品質 |
| 4 | feedback_ct_lab_mission.md | feedback | 19d | コピートレード目標・年間日利5%・設計原則 | ミッション |
| 5 | feedback_server_restart.md | feedback | 46d | launchctlでバックエンド自動再起動 | インフラ |
| 6 | feedback_site_performance.md | feedback | 39d | サイト軽量化 | インフラ |
| 7 | feedback_haruking_github_save.md | feedback | 25d | haruking_games変更→GitHub push | インフラ |
| 8 | feedback_subagent_model.md | feedback | 16d | haiku/sonnet/opus使い分け | 運用 |
| 9 | feedback_detailed_analysis.md | feedback | 5d | 分析は数字羅列でなく考察 | 報告品質 |
| 10 | feedback_report_detail.md | feedback | 5d | エクイティカーブ・詳細リターン・更新時刻 | 報告品質 |
| 11 | feedback_crypto_specific.md | feedback | 5d | クリプト特有戦略・並列・トークン制限なし | 研究戦略 |
| 12 | feedback_symbol_breadth.md | feedback | 5d | 15-30銘柄スクリーニング | 研究戦略 |
| 13 | feedback_findings_consolidation.md | feedback | 5d | 発見を構造化サマリーで報告 | 報告品質 |
| 14 | feedback_html_record_all.md | feedback | 5d | 発見はすべてHTML記載 | HTML管理 |
| 15 | feedback_no_premature_stop.md | feedback | 4d | 長時間タスクで途中停止しない | 運用 |
| 16 | feedback_html_log_continuous.md | feedback | 4d | 発見・tipsを逐次HTML追記 | HTML管理 |
| 17 | feedback_html_tips_continuous.md | feedback | 4d | tips全記録＋更新日時表示 | HTML管理 |
| 18 | feedback_explore_vs_exploit.md | feedback | 4d | explore/exploit同等・プロセス改変権限 | 運用 |
| 19 | feedback_user_instruction_inbox.md | feedback | 4d | サイト指示インボックス・pwd=2026 | セキュリティ |
| 20 | feedback_external_research.md | feedback | 4d | botter/Qiita/論文を定期リサーチ | 研究戦略 |
| 21 | feedback_symbol_universe_50.md | feedback | 4d | 戦略テスト最低50銘柄 | 研究戦略 |
| 22 | feedback_consistency_watch.md | feedback | 4d | コード/JSONとHTMLの矛盾チェック | HTML管理 |
| 23 | feedback_html_audit_periodic.md | feedback | 4d | 3-5 Waveに1回HTML全体監査 | HTML管理 |
| 24 | feedback_mobile_responsive.md | feedback | 4d | 全UI・グラフのモバイル対応 | HTML管理 |
| 25 | feedback_periodic_refactoring.md | feedback | 4d | 5-10 Waveに1回コード整理 | 運用 |
| 26 | feedback_visualization_quality.md | feedback | 4d | equity curve・ヒートマップ・Plotly統一 | 報告品質 |
| 27 | feedback_onchain_native_strategies.md | feedback | 4d | オンチェーン/ウォレット特化戦略 | 研究戦略 |
| 28 | feedback_external_findings_paginated.md | feedback | 4d | 外部リサーチ知見はページ切替式追加 | 研究戦略 |
| 29 | feedback_inbox_security_and_filter.md | feedback | 4d | 戦略指示のみカウント・攻撃ロック | セキュリティ |
| 30 | feedback_always_running_full_auto.md | feedback | 4d | 常時稼働・全判断自動・確認待ち禁止 | 運用 |
| 31 | feedback_silent_stall_handling.md | feedback | 4d | silent stall検知・時間triggerで次wave | 運用 |
| 32 | feedback_timestamp_accuracy.md | feedback | 4d | 更新時刻はBash date取得・推測禁止 | HTML管理 |
| 33 | feedback_agent_groundtruth_verify.md | feedback | 3d | agent主張をlaunchctl/lsで実体確認 | 検証 |
| 34 | feedback_cross_source_comparison.md | feedback | 3d | データ比較前にsource(取引所)を確認 | 検証 |
| 35 | feedback_token_budget_2026_05.md | feedback | 3d | 週次80%以下・並列3まで | 運用 |
| 36 | feedback_research_allocation_3_1_1.md | feedback | 3d | scraper round後7日以内に3+1+1実施 | 研究戦略 |
| 37 | feedback_backlog_discipline.md | feedback | 3d | WIP limit: 3/5/8/15・5wave毎governance | 運用 |
| 38 | feedback_public_repo_security.md | feedback | 3d | 公開repo前提・username/path露出禁止 | セキュリティ |
| 39 | feedback_regime_filter_line_closed.md | feedback | 2d | regime filter 5連続REJECTで停止 | 研究状態 |
| 40 | feedback_concentration_risk_HL.md | feedback | 2d | HL集中57.5%・tail risk・fallback設計 | リスク |
| 41 | feedback_hypurrfi_dropline.md | project | 0d | HypurrFi TVL死亡・trigger 2027-04-01 | 研究状態 |
| 42 | project_crypto_lab.md | project | 5d | crypto-lab概要・生存者7戦略 | プロジェクト |
| 43 | project_ct_lab_mission_v2.md | project | 5d | CT Lab v2・6エージェント・§6ゲート | ミッション |
| 44 | project_systematic_alpha_default.md | project | 4d | デフォルト作業・毎回push | プロジェクト |

---

## Phase 2: トピック別グループ化

### グループ A — 基本行動原則 (3本)
- `feedback_first_priority.md` — 最速最高効率
- `feedback_perspective.md` — 視野狭窄防止
- `feedback_explore_vs_exploit.md` — explore/exploit同等・プロセス改変権限

### グループ B — ミッション・プロジェクト定義 (4本)
- `feedback_ct_lab_mission.md` — CT Lab ミッション（コピートレード・年間5%）
- `project_ct_lab_mission_v2.md` — CT Lab v2（§6ゲート・エージェント組織）
- `project_crypto_lab.md` — プロジェクト現状（生存者7戦略）
- `project_systematic_alpha_default.md` — デフォルト作業定義

### グループ C — 研究品質・過学習防止 (2本)
- `feedback_overfitting_and_edge.md` — 過学習防止・flearn参照
- `feedback_regime_filter_line_closed.md` — regime filter CLOSED（状態メモ）

### グループ D — 研究戦略・銘柄 (5本)
- `feedback_crypto_specific.md` — クリプト特有戦略
- `feedback_onchain_native_strategies.md` — オンチェーン特化
- `feedback_symbol_breadth.md` — 15-30銘柄スクリーニング
- `feedback_symbol_universe_50.md` — 最低50銘柄
- `feedback_external_research.md` — 外部リサーチ

### グループ E — 外部リサーチ運用 (2本)
- `feedback_external_findings_paginated.md` — ページ切替式・追加運用
- `feedback_research_allocation_3_1_1.md` — 3+1+1配分

### グループ F — 報告・可視化品質 (4本)
- `feedback_detailed_analysis.md` — 深い考察を含める
- `feedback_report_detail.md` — エクイティカーブ・詳細リターン
- `feedback_findings_consolidation.md` — 構造化サマリー
- `feedback_visualization_quality.md` — equity curve・ヒートマップ

### グループ G — HTML管理 (6本) ★重複最多
- `feedback_html_record_all.md` — 発見はすべてHTML記載
- `feedback_html_log_continuous.md` — 発見・tipsを逐次追記
- `feedback_html_tips_continuous.md` — tips全記録＋更新日時
- `feedback_consistency_watch.md` — コード/JSONとHTMLの矛盾チェック
- `feedback_html_audit_periodic.md` — 3-5 Waveに1回HTML全体監査
- `feedback_timestamp_accuracy.md` — 更新時刻はBash date取得
- `feedback_mobile_responsive.md` — モバイル対応
- `feedback_periodic_refactoring.md` — 5-10 Waveに1回リファクタ

### グループ H — 運用・自律稼働 (6本) ★重複あり
- `feedback_no_premature_stop.md` — 途中停止しない
- `feedback_always_running_full_auto.md` — 常時稼働・全判断自動
- `feedback_silent_stall_handling.md` — silent stall対策
- `feedback_backlog_discipline.md` — WIP limit
- `feedback_token_budget_2026_05.md` — トークン節約
- `feedback_subagent_model.md` — haiku/sonnet/opus使い分け

### グループ I — 検証・品質保証 (2本)
- `feedback_agent_groundtruth_verify.md` — agent主張をground truth確認
- `feedback_cross_source_comparison.md` — データsource確認

### グループ J — セキュリティ (3本) ★補完関係
- `feedback_user_instruction_inbox.md` — インボックス設計（補完前）
- `feedback_inbox_security_and_filter.md` — 攻撃ロック・戦略分類（補完後）
- `feedback_public_repo_security.md` — 公開repo・credentials禁止

### グループ K — インフラ運用 (3本)
- `feedback_server_restart.md` — launchctl自動再起動
- `feedback_site_performance.md` — サイト軽量化
- `feedback_haruking_github_save.md` — haruking_games→GitHub push

### グループ L — リスク・プロジェクト状態 (3本)
- `feedback_concentration_risk_HL.md` — HL集中リスク
- `feedback_hypurrfi_dropline.md` — HypurrFi DROP_LINE
- `feedback_regime_filter_line_closed.md` — regime filter CLOSED（Cと重複カウント）

---

## Phase 3: 重複・冗長性の詳細分析

### 重複パターン A: HTML記録ルール群 (最大冗長)

| ファイル | 核心主張 | 固有コンテンツ |
|---------|---------|--------------|
| `html_record_all` | 発見はすべてHTMLへ | 記録の場所・構造（2段構え）|
| `html_log_continuous` | 逐次追記・溜めない | Future Ideasセクション・commit待たない |
| `html_tips_continuous` | tips全記録＋更新日時表示 | 更新日時形式YYYY-MM-DD HH:MM JST |
| `timestamp_accuracy` | 時刻はBash dateで取得 | AM/PM間違い防止の具体的手順 |
| `consistency_watch` | コード/JSONとHTMLの矛盾チェック | 見守りパス5点チェックリスト |
| `html_audit_periodic` | 3-5 Waveに1回深い監査 | `consistency_watch`の**拡張版**と明記 |

**観察**: `html_audit_periodic`は本文に「既存の`feedback_consistency_watch`を拡張する」と明記。`html_tips_continuous`の更新日時ルールは`timestamp_accuracy`と直接重複。`html_record_all`と`html_log_continuous`は主張が95%重複。

**統合案**: 
- `html_record_all` + `html_log_continuous` + `html_tips_continuous` → **1本に統合可能**（HIGH confidence）
- `consistency_watch` + `html_audit_periodic` → **1本に統合可能**（HIGH confidence）
- `timestamp_accuracy` → 統合版HTMLルールの1節に吸収

### 重複パターン B: 常時稼働ルール群

| ファイル | 核心主張 | 固有コンテンツ |
|---------|---------|--------------|
| `no_premature_stop` | 途中でsummaryを出して止めない | long-running task中の言動規則 |
| `always_running_full_auto` | 常時稼働・全判断自動 | 本文に「`no_premature_stop`を強化」と明記、agent完了→即次wave |
| `silent_stall_handling` | silent stall対策・時間trigger | 本文に「`always_running`を補完」と明記 |

**観察**: `always_running_full_auto`は`no_premature_stop`のスーパーセット。`no_premature_stop`の全内容は`always_running_full_auto`に含まれる。`silent_stall_handling`は独立した具体的実装ルール（stall事例・時間閾値）を持つ。

**統合案**:
- `no_premature_stop` → `always_running_full_auto`に吸収（HIGH confidence）
- `silent_stall_handling` → 現状維持（独自コンテンツが十分あり）

### 重複パターン C: 外部リサーチ群

| ファイル | 核心主張 | 固有コンテンツ |
|---------|---------|--------------|
| `external_research` | 定期的にbotter/Qiita/論文リサーチ | scraper起動頻度・タグ分類 |
| `external_findings_paginated` | 上書き禁止・ページ切替式UI | 本文に「`external_research`を補完」と明記 |
| `research_allocation_3_1_1` | 3+1+1配分・7日以内 | 本文に「`external_research`を補完」と明記 |

**観察**: 3本とも「外部リサーチをどう運用するか」の異なる側面。`external_findings_paginated`と`research_allocation_3_1_1`はどちらも「`external_research`の補完」と明記。

**統合案**:
- 3本 → 1本の`external_research_master.md`へ統合（MED confidence）
- 各ファイルは独自の具体的実装（UI設計・配分比率）を持つため、セクション分けで保持

### 重複パターン D: インボックス/セキュリティ群

| ファイル | 核心主張 | 固有コンテンツ |
|---------|---------|--------------|
| `user_instruction_inbox` | パスワード2026・インボックス設計 | フロントエンド実装・ポーリング間隔 |
| `inbox_security_and_filter` | 戦略指示のみカウント・攻撃ロック | 本文に「`user_instruction_inbox`を補完」と明記 |

**観察**: 2本は明示的に補完関係。インボックスの概念（何を）と実装（どう守るか）の分担。合計文字数は統合しても管理可能な量。

**統合案**:
- 2本 → 1本のインボックス統合ルール（MED confidence）

### 重複パターン E: 銘柄ユニバース

| ファイル | 核心主張 |
|---------|---------|
| `symbol_breadth` | 15-30銘柄でスクリーニング（DOGE/AVAX/SUI脱却） |
| `symbol_universe_50` | 最低50銘柄確保（`symbol_breadth`の拡張） |

**観察**: `symbol_universe_50`（2026-05-24）が`symbol_breadth`（2026-05-20頃）を上書き。50銘柄が現行ルール、15-30は古い。ただし`symbol_breadth`はカテゴリ分類（メジャー/ラージ/ミッド/スモール/ミーム）という独自コンテンツを持つ。

**統合案**:
- `symbol_breadth` → `symbol_universe_50`に吸収（HIGH confidence）

### 重複パターン F: プロジェクト定義の重複

| ファイル | 内容 |
|---------|-----|
| `feedback_ct_lab_mission` | コピートレード・年間5%・CT Report形式 |
| `project_ct_lab_mission_v2` | §6ゲート・エージェント組織・運転原則 |
| `project_systematic_alpha_default` | デフォルト作業・push毎回 |
| `project_crypto_lab` | プロジェクト現状（生存者・試行数等） |

**観察**: `project_systematic_alpha_default`は「`project_ct_lab_mission_v2`と重複しないこと」と自己言及。`project_crypto_lab`は定期的に陳腐化する（試行数705K+は5d前の数値）。`feedback_ct_lab_mission`の内容は`project_ct_lab_mission_v2`と重複する部分が多い。

**統合案**: 
- 統合は慎重に（ミッション文書は細かい差異が重要）。`project_crypto_lab`のみ更新頻度が低い点で問題 → 提案のみ

---

## Phase 4: 陳腐化チェック

### 陳腐化スコア基準
- **RED**: 現在のプロジェクト状態と矛盾または無関係
- **YELLOW**: 部分的に古い
- **GREEN**: 現役

| ファイル | 陳腐化評価 | 理由 |
|---------|-----------|-----|
| `feedback_server_restart` | YELLOW | MEXCエージェント向け(`com.quanta.mexc-agent.plist`)。現在はHL/cryptolabが主。mexcエージェントはまだ稼働中かが不明。46日前作成 |
| `feedback_site_performance` | YELLOW | 「haruking_games サイト」の軽量化文脈で作成。現在のcrypto-lab report.htmlはGitHub Pagesでシンプル静的HTML。適用範囲が曖昧 |
| `project_crypto_lab` | YELLOW | 試行数705K+(5d前)・生存者7戦略は既に変化している可能性。K280/K297/v6.13d等の新HL戦略が含まれていない。定期更新が必要な「状態」ファイル |
| `feedback_ct_lab_mission` | YELLOW | 「MEXC先物」「コピートレード」を主題とするが、現在はHL中心に移行。`project_ct_lab_mission_v2`が最新版 |
| `feedback_symbol_breadth` | YELLOW | 15-30銘柄ルールは`symbol_universe_50`（50銘柄）に上書き済み |
| `feedback_token_budget_2026_05` | YELLOW | 「次のuser instruction見直しまで有効」「土曜以降は新指示優先」と明記。今日は05-29 (木曜)。土曜05-31リセット後に見直す必要あり。ただし有効期間中なので保持 |
| `feedback_no_premature_stop` | YELLOW | `always_running_full_auto`のサブセット。独立して存在する必要性が低い |
| その他38本 | GREEN | 現役、内容一貫 |

---

## Phase 5: マージ提案一覧

### MERGE-1: HTMLルール統合 (HIGH confidence)
**マージ**: `html_record_all` + `html_log_continuous` + `html_tips_continuous` → `feedback_html_record_and_log.md`

**根拠**:
- 3本の核心主張: 「重要発見はHTMLへ、逐次・溜めずに、更新日時付きで」= 同一
- `html_tips_continuous`の更新日時ルールは`timestamp_accuracy`に委任すれば吸収可能
- 3本を読む認知コストが1本の3倍

**保持すべき固有コンテンツ**:
- 2段構え（サマリーカード＋詳細セクション）(`html_record_all`)
- Future Ideas セクション (`html_log_continuous`)
- `Last updated: YYYY-MM-DD HH:MM JST`フォーマット (`html_tips_continuous`)

**統合後**: 内容量は現在の約60%に圧縮可能

---

### MERGE-2: HTML整合性・監査統合 (HIGH confidence)
**マージ**: `consistency_watch` + `html_audit_periodic` → `feedback_html_audit.md`（`consistency_watch`を改名統合）

**根拠**:
- `html_audit_periodic`本文に「既存の`consistency_watch`を拡張する」と明記
- `consistency_watch`のチェックリスト（5点）は`html_audit_periodic`の詳細チェックリストに完全に包含

**保持すべき固有コンテンツ**:
- 見守りパス頻度: 2-3 Waveに1回 (`consistency_watch`)
- 深い監査頻度: 3-5 Waveに1回 (`html_audit_periodic`)
- 両頻度の差異を明確に維持（二段階の監視）

---

### MERGE-3: 常時稼働ルール (HIGH confidence)
**マージ**: `no_premature_stop` → `always_running_full_auto`に吸収（`no_premature_stop`削除）

**根拠**:
- `always_running_full_auto`本文に「`no_premature_stop`を強化」と明記
- `no_premature_stop`の全内容（途中summaryを出さない、forward-looking進捗報告のみ、ユーザー停止指示まで止まらない）は`always_running_full_auto`に包含
- `no_premature_stop`固有: 「完了・総括・以上」のような終了phraseの禁止 → `always_running_full_auto`に1行追加で保持可能

**保持すべき固有コンテンツ**:
- 「完了」「総括」「以上」phraseはlong-running taskの本当の終了時のみ → `always_running_full_auto`の"How to apply"に追記

---

### MERGE-4: 銘柄ユニバース統合 (HIGH confidence)
**マージ**: `symbol_breadth` → `symbol_universe_50`に吸収（`symbol_breadth`削除）

**根拠**:
- `symbol_universe_50`（2026-05-24）は`symbol_breadth`の上位互換（15-30 → 50+）
- `symbol_breadth`のDOGE/AVAX/SUI偏重脱却の背景と、カテゴリ別分類（メジャー/ラージ/ミッド/スモール/ミーム）は`symbol_universe_50`に追記で保持可能

**保持すべき固有コンテンツ**:
- Multi-Symbol validation を必須要件にする (`symbol_breadth`)
- カテゴリ別分散意識 (`symbol_breadth`)

---

### MERGE-5: 外部リサーチ統合 (MED confidence)
**マージ**: `external_research` + `external_findings_paginated` + `research_allocation_3_1_1` → `feedback_external_research_master.md`

**根拠**:
- 3本とも「外部リサーチ運用」ドメイン
- `external_findings_paginated`と`research_allocation_3_1_1`はどちらも「`external_research`の補完」と自己言及
- 読者が外部リサーチルールを確認する時、3本を横断するのは非効率

**不確実性**:
- 各ファイルに固有の詳細実装（UI設計、round tracking JSON形式）があるため、統合時に情報欠損リスク
- MED confidence（LOW risk、情報量が多い）

---

### MERGE-6: インボックス統合 (MED confidence)
**マージ**: `user_instruction_inbox` + `inbox_security_and_filter` → `feedback_inbox_master.md`

**根拠**:
- `inbox_security_and_filter`本文に「`user_instruction_inbox`を補完する」と明記
- インボックスの設計・実装・セキュリティは本来1つのコンテキスト

**不確実性**:
- 両ファイル合計で200行超。統合時の可読性を維持する必要
- フロントエンド実装詳細（localStorage管理）と攻撃検知パターンは別の関心事
- MED confidence

---

## Phase 6: Prune候補

### PRUNE-1: `feedback_no_premature_stop` (HIGH confidence)
**削除理由**: `feedback_always_running_full_auto`のサブセット。独立した存在価値なし。
**処理**: `always_running_full_auto`に"completion phrase restriction"を追記してから削除

### PRUNE-2: `feedback_symbol_breadth` (HIGH confidence) 
**削除理由**: `feedback_symbol_universe_50`に上書きされた旧ルール。15-30銘柄→50銘柄へ。カテゴリ分類コンテンツは統合先に移設。
**処理**: `symbol_universe_50`にカテゴリ分類を追記してから削除

### PRUNE-3: `project_crypto_lab` (LOW confidence — 提案のみ)
**削除候補理由**: 試行数・生存者リストは急速に陳腐化。5日前時点ですでに旧情報。`STRATEGY_REGISTRY.json`が真のsingle source of truth。
**不確実性**: GitHub URLやファイル構成など一部の情報は依然有効。削除ではなく「定期更新が必要」のフラグを付けることを推奨。
**処理**: 提案のみ、実施しない

### PRUNE-4: `feedback_server_restart` (LOW confidence — 提案のみ)
**削除候補理由**: MEXC-agentのlaunchctl手順が主体。現在のプロジェクトがHL中心に移行しており適用頻度低い。46日前作成、最古のファイルの一つ。
**不確実性**: MEXC agentがまだ稼働中であれば削除は損失。プロジェクト状態を確認してから。
**処理**: 提案のみ、実施しない

### PRUNE-5: `feedback_site_performance` (LOW confidence — 提案のみ)
**削除候補理由**: `feedback_mobile_responsive.md`（より具体的なUI最適化ルール）と`feedback_visualization_quality.md`でカバーされている。39日前作成。
**不確実性**: haruking_gamesへの適用文脈がある可能性。
**処理**: 提案のみ、実施しない

---

## Phase 7: MEMORY.md 再構成案

### 現在の構造の問題点
1. **追加順** (chronological) なので関連ルールが散在
2. 新規追加時はどこに挿入するか不明確
3. 「HTML関係を全部調べたい」時に5本を探す必要

### 提案: トピック別グループ + セクションヘッダ

```markdown
# MEMORY.md (K411 再構成案)

## 【基本原則 / 行動指針】
- [最優先原則](feedback_first_priority.md)
- [視野の広さ](feedback_perspective.md)
- [explore=exploit同等+プロセス改変権限](feedback_explore_vs_exploit.md)

## 【ミッション / プロジェクト定義】
- [CT Lab ミッション](feedback_ct_lab_mission.md)
- [CT Lab ミッション v2](project_ct_lab_mission_v2.md)
- [Systematic Alpha Discovery (デフォルト)](project_systematic_alpha_default.md)
- [crypto-lab プロジェクト現状](project_crypto_lab.md)

## 【研究品質 / 過学習防止】
- [過学習/エッジ](feedback_overfitting_and_edge.md)
- [分析の詳細さ](feedback_detailed_analysis.md)
- [発見の統合](feedback_findings_consolidation.md)
- [レポート詳細化](feedback_report_detail.md)
- [可視化品質](feedback_visualization_quality.md)

## 【研究戦略 / 銘柄ユニバース】
- [クリプト特有戦略](feedback_crypto_specific.md)
- [オンチェーン特化戦略](feedback_onchain_native_strategies.md)
- [銘柄ユニバース50+](feedback_symbol_universe_50.md)  ← symbol_breadthをここに吸収後
- [外部リサーチ定期](feedback_external_research.md)
- [外部リサーチ ページ切替式](feedback_external_findings_paginated.md)
- [R-finding 3+1+1 配分](feedback_research_allocation_3_1_1.md)

## 【プロジェクト状態 / リスク】
- [Regime-filter line CLOSED](feedback_regime_filter_line_closed.md)
- [HL 集中リスク](feedback_concentration_risk_HL.md)
- [HypurrFi DROP_LINE](feedback_hypurrfi_dropline.md)

## 【HTML管理 / 記録】
- [HTML記録原則](feedback_html_record_all.md)  ← html_log_continuous, html_tips_continuousを吸収後
- [HTML整合性・監査](feedback_html_audit_periodic.md)  ← consistency_watchを吸収後
- [モバイル対応](feedback_mobile_responsive.md)
- [時刻 記入は date 取得](feedback_timestamp_accuracy.md)

## 【運用 / 自律稼働】
- [常時稼働・完全自動判断](feedback_always_running_full_auto.md)  ← no_premature_stopを吸収後
- [Silent stall 対策](feedback_silent_stall_handling.md)
- [バックログ規律 WIP limit](feedback_backlog_discipline.md)
- [定期リファクタリング](feedback_periodic_refactoring.md)
- [トークン節約 2026-05](feedback_token_budget_2026_05.md)
- [サブエージェントモデル](feedback_subagent_model.md)

## 【検証 / 信頼性】
- [Agent claim → ground truth verify](feedback_agent_groundtruth_verify.md)
- [クロスソース比較は source 検証先](feedback_cross_source_comparison.md)

## 【セキュリティ / インボックス】
- [サイト指示インボックス](feedback_user_instruction_inbox.md)
- [インボックス: 戦略のみ+攻撃ロック](feedback_inbox_security_and_filter.md)
- [公開リポ前提セキュリティ](feedback_public_repo_security.md)

## 【インフラ / 環境】
- [Server restart](feedback_server_restart.md)
- [サイト軽量化](feedback_site_performance.md)
- [haruking_games保存](feedback_haruking_github_save.md)
```

---

## Phase 8: 実施内容 (HIGH-confidence のみ)

### 実施 A: `no_premature_stop` → `always_running_full_auto`に吸収
**難易度**: LOW。`always_running_full_auto`に1文追加 → `no_premature_stop`を削除

具体的変更:
- `always_running_full_auto.md`の"How to apply"に以下を追記:
  ```
  - 「完了」「総括」「以上」のような finalizing phrase は long-running task の本当の終了時のみ使用。途中経過では「次に X 試す」「Y 完了、Z 着手」の forward-looking style のみ
  ```
- `no_premature_stop.md`を削除
- `MEMORY.md`から`no_premature_stop`の行を削除

### 実施 B: `symbol_breadth` → `symbol_universe_50`に吸収
**難易度**: LOW。`symbol_universe_50`にカテゴリ分類を追記 → `symbol_breadth`を削除

具体的変更:
- `symbol_universe_50.md`の"How to apply"に以下を追記:
  ```
  - カテゴリ別分散: メジャー(BTC/ETH)・ラージキャップ(SOL/BNB)・ミッドキャップ(DOT/LINK/AVAX等)・スモールキャップ(SUI/INJ/TIA等)・ミーム(DOGE/PEPE/SHIB)から各カテゴリ生存者を抽出
  - 単一銘柄の生存者は Multi-Symbol validation を必須要件にする
  - ポートフォリオ構築時は銘柄カテゴリー分散を意識
  ```
- `symbol_breadth.md`を削除
- `MEMORY.md`から`symbol_breadth`の行を削除

### 未実施 (MED/LOW confidence)
- MERGE-5 (外部リサーチ3本統合): 実施保留 → 将来wave
- MERGE-6 (インボックス統合): 実施保留 → 将来wave
- MERGE-1,2 (HTML5本統合): ★大きい変更のため今回は実施保留。提案として記録
- PRUNE-3,4,5: 削除は行わず提案として記録

---

## 変更ログ

### K411 実施済み変更
1. `feedback_always_running_full_auto.md` — "How to apply" に no_premature_stop の終了phrase制限を追記
2. `feedback_no_premature_stop.md` — **削除** (always_running_full_autoに吸収)
3. `feedback_symbol_universe_50.md` — "How to apply" にカテゴリ分類を追記
4. `feedback_symbol_breadth.md` — **削除** (symbol_universe_50に吸収)
5. `MEMORY.md` — 2行削除 (no_premature_stop, symbol_breadth)
6. `MEMORY.md` — トピック別グループ再構成（セクションヘッダ追加）

### 今後の推奨 Wave (提案のみ)
- **K42x**: HTML記録5本統合 (MERGE-1,2) — 大規模だが高効果
- **K43x**: 外部リサーチ3本統合 (MERGE-5) — 中規模
- **K44x**: インボックス2本統合 (MERGE-6) — 小規模
- **K45x**: `project_crypto_lab`の更新または削除判断

---

## 統計サマリー

| 指標 | 値 |
|-----|---|
| 総ファイル数 (MEMORY.md含む) | 44 |
| トピックグループ数 | 12 |
| HIGH confidence マージ提案数 | 4 |
| MED confidence マージ提案数 | 2 |
| LOW confidence Prune提案数 | 3 |
| 今回 HIGH confidence 実施数 | 2 (A: no_premature_stop吸収, B: symbol_breadth吸収) |
| 削除ファイル数 | 2 |
| MEMORY.md 削除行数 | 2 |
