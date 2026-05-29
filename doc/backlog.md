# Backlog（後回し・見送り・将来検討の集約）

> AI-DLC ワークフロー外のチーム運用ドキュメント。`aidlc-docs/` は AI-DLC 公式成果物専用、本ファイルを含む `doc/` 配下はチーム運用情報専用。
>
> 並列開発前提の決定（[parallel-dev-prerequisites.md](../aidlc-docs/construction/plans/parallel-dev-prerequisites.md)）/ Per-Unit 設計 / Inception 時に「後回し」「見送り」「将来検討」と判断した項目を集約する。
>
> **記載ルール（必須 4 項目）**: 各エントリは以下を必ず含む:
>
> 1. **項目名**: 何を議論したか
> 2. **出典**: どの議論・ドキュメント・ステージで判断したか（相対リンク）
> 3. **後付け導入トリガー**: どんな条件・指標が満たされたら再評価するか
> 4. **優先度**: 高 / 中 / 低（再評価の緊急度）
>
> 詳細ルールは [.kiro/steering/structure.md](../.kiro/steering/structure.md) §6 Backlog 運用ルール を参照。

---

## 1. Construction Phase 並列開発前提（2026-05-27 確定）

### B-001. ログ・監視スタック（観測性基盤）

| 項目 | 内容 |
|---|---|
| **項目名** | AWS Lambda Powertools / X-Ray / EMF / CloudWatch Dashboard の全面導入 |
| **出典** | [parallel-dev-prerequisites.md §I-2](../aidlc-docs/construction/plans/parallel-dev-prerequisites.md) 回答 = C（一旦見送り） |
| **当初推奨案** | Powertools 構造化ログ + X-Ray 全 Lambda トレース + EMF カスタムメトリクス + Dashboard IaC 化 |
| **見送り理由** | 予選 5/30 まで実装範囲を最小化、構築コストを Unit-1〜5 のコア機能に集中させるため |
| **暫定運用** | CloudWatch Logs raw のみ（Lambda 標準出力）。構造化なし、トレースなし、カスタムメトリクスなし |
| **後付け導入トリガー** | 以下のいずれか 1 つで導入検討開始<br>1. 予選デモで Lambda 障害が発生し、原因特定が raw ログで困難だった場合<br>2. 北極星指標（論破 → Amazon 遷移率）の可視化が決勝までに必要となった場合<br>3. 決勝 6/26 に向けて AWS デプロイ時の SLA / SLO 提示が必要となった場合 |
| **優先度** | **中**（予選では不要、決勝の AWS 上動作デモで価値が出る可能性あり） |
| **概算工数** | Powertools 導入 = 0.5d / X-Ray 有効化 = 0.5d / EMF + Dashboard = 1d、合計 2d（Member A） |

---

### B-002. Bedrock Sonnet 4.6 の後付けエスカレーション機能

| 項目 | 内容 |
|---|---|
| **項目名** | Bedrock Claude Sonnet 4.6（Global CRIS 経由）を高品質モデルとして導入 |
| **出典** | [parallel-dev-prerequisites.md §C-2](../aidlc-docs/construction/plans/parallel-dev-prerequisites.md) 回答 = B（Haiku 4.5 全面採用 + 留保） |
| **当初推奨案** | Haiku 4.5（apne1 native）= ストリーミング論破 + Sonnet 4.6（Global CRIS）= 日次バッチでプロンプト最適化 |
| **見送り理由** | 4 名 / 3 日（予選まで）の制約下で、エスカレーション UI / 課金モニタリング / Cross-Region Inference の運用までは作り込めない。Haiku 4.5 単独で要件書 §6.3 の合意率目標を満たせるベンチマーク見込みあり |
| **暫定運用** | 全論破 / 推薦 / プロンプト合成を Haiku 4.5 で実装。SSM Parameter Store には Haiku 4.5 + Embeddings V2 のみ先行登録、Sonnet 4.6 用 Parameter は未作成 |
| **後付け導入トリガー** | 以下のいずれか 1 つで Sonnet 4.6 検討開始<br>1. PBT-08 論破合意率 < 70% が連続 1 週間継続<br>2. MVP デモ視聴者の体感評価で「論破が浅い」フィードバックが過半<br>3. Haiku 4.5 のストリーミングが要件書 §6.3 のレイテンシ要件（初回トークン 3 秒以内）に届かない場合（この場合は Nova Lite 等の軽量モデル fallback も検討） |
| **優先度** | **中**（Haiku 4.5 で要件未達が顕在化した時点で即時検討） |
| **概算工数** | Sonnet 4.6 SSM Parameter 追加 + DebateLlmService の model_id 切替実装 + Cross-Region Inference 設定 = 1.5d（Member A or Member B） |

---

## 2. Per-Unit 内の見送り / 後付け検討（2026-05-27 確定）

### B-201. Telemetry 投入経路の C 案（SQS 介在型）への移行

| 項目 | 内容 |
|---|---|
| **項目名** | B-14 TelemetryIngestionService の Firehose 投入を SQS Consumer Lambda 経由に変更（C 案） |
| **出典** | [Unit-1 Platform Functional Design Plan §Q3](../aidlc-docs/construction/unit-1-platform/functional-design/functional-design-plan.md) 回答 = B + 安全装置 3 点 |
| **当初推奨案（B）** | Mobile 5 件バッファ + B-14 Lambda 内で Firehose 同期呼び出し |
| **見送り理由** | ハッカソン規模（10〜10K DAU）で性能限界は 100K DAU 以降にしか出ない。C 案は実装工数 +1d / 運用複雑度増のため、安全装置 3 点（Idempotency Key + Lambda DLQ + 移行トリガー記録）でリスクを緩和して B で開始 |
| **暫定運用** | B-14 Lambda が Firehose を同期呼び出し。失敗時は Lambda DLQ に自動退避、Idempotency Key で重複防止 |
| **後付け導入トリガー** | 以下のいずれか 1 つで C 移行検討開始<br>1. 平均 events/sec > **100**（〜50K DAU 相当）が連続 1 週間継続<br>2. Telemetry 欠損率 > **0.1%** が観測された<br>3. Firehose 一時障害が 1 回でも顕在化した<br>4. 決勝後にプロダクト化判断が下された |
| **優先度** | **中**（性能 / 欠損問題が顕在化した時点で即時検討） |
| **概算工数** | B-14 Lambda の Firehose → SQS 切替（5-10 行）+ SQS Consumer Lambda 新設（30-50 行）+ DLQ 設定 + CDK スタック追加 = **0.5〜1d**（Member A）。Mobile 側変更ゼロ、API 契約変更ゼロ、ダウンタイムほぼゼロ |

---

### B-202. B-02 DebateLlmService の Provisioned Concurrency 追加

| 項目 | 内容 |
|---|---|
| **項目名** | B-02 DebateLlmService に Provisioned Concurrency 1 並列を追加して論破ストリーミングのコールドスタートを完全にゼロ化 |
| **出典** | [Unit-1 Platform Functional Design Plan §Q5](../aidlc-docs/construction/unit-1-platform/functional-design/functional-design-plan.md) 回答 = B + B-02 DDB 化 + SnapStart |
| **当初推奨案（採用済み）** | A 採用（B-02 DDB 化）+ SnapStart 有効化（追加料金ゼロ、cold start 〜300-400ms に短縮） |
| **見送り理由** | 月額 $11-15 のコスト発生 / SnapStart 単独でも要件「初回トークン 3 秒以内」を 13% 程度の余裕で達成 / SnapStart + DDB 化 + VPC 外で ENI 新規作成リスクも回避済み |
| **暫定運用** | SnapStart 単独（追加料金ゼロ）で B-02 を運用。ENI 新規作成リスクは VPC 外配置で完全回避 |
| **後付け導入トリガー** | 以下のいずれかで Provisioned Concurrency 追加検討<br>1. 決勝デモ（2026-06-26）の前 1 週間（6/15 以降）の総合判断で「並列 2 以上の同時アクセスでデモ事故が起きうる」と判断された場合<br>2. PBT-08 / E2E テストで cold start が 500ms を超えるケースが連続観測された場合<br>3. MVP デモ視聴者の体感評価で「論破の最初の応答が遅い」フィードバックが過半 |
| **優先度** | **低**（SnapStart で要件達成済み、決勝向けの保険） |
| **概算工数** | CDK 5 行追加 = **5 分**（Member A）。`addAutoScaling` で `minCapacity: 1, maxCapacity: 10` 設定、cost monitor を CloudWatch Dashboard に追加（要 I-2 の B-001 backlog の解消が前提）|
| **想定追加コスト** | 月額 $11-15（apne1 / Python 3.13 / 1024MB / 1 並列）|

---

## 3. Nice to have（決定不要、将来検討）

> [parallel-dev-prerequisites.md §3](../aidlc-docs/construction/plans/parallel-dev-prerequisites.md) で「決定不要、参考」と判断した項目のうち、再評価の余地があるものを記録。
> N-1（Figma 化）はスキップ判断を撤回し、議論再開のため本 backlog からは除外（同 §3 で active 議論中）。

### B-101. 多言語化（i18n）対応

| 項目 | 内容 |
|---|---|
| **項目名** | アプリ全体を日本語以外の言語に対応させる |
| **出典** | [parallel-dev-prerequisites.md §3 N-2](../aidlc-docs/construction/plans/parallel-dev-prerequisites.md) |
| **見送り理由** | YUDANE のターゲットペルソナ（悠介・里奈）は日本のリモートワーカー。ハッカソン提出範囲は日本語のみで十分 |
| **暫定運用** | 全 UI コピー・通知・論破プロンプトは日本語ハードコード。`react-native-localize` 等の i18n 基盤は導入しない |
| **後付け導入トリガー** | 以下のいずれかで検討<br>1. ハッカソン後にプロダクト化を検討する場合<br>2. 海外向け展開を意思決定した場合<br>3. 審査員から多言語対応の質問が出た場合（プレゼン Q&A の事前準備として） |
| **優先度** | **低**（ハッカソン期間中は不要） |
| **概算工数** | i18n 基盤導入 + 日本語以外 1 言語 = 3d（チーム全体） |

---

### B-102. Storybook によるコンポーネントカタログ

| 項目 | 内容 |
|---|---|
| **項目名** | Storybook（または Storybook for React Native）で UI コンポーネントを単体プレビュー可能にする |
| **出典** | [parallel-dev-prerequisites.md §3 N-3](../aidlc-docs/construction/plans/parallel-dev-prerequisites.md) |
| **見送り理由** | UI コンポーネントは `mobile/src/features/<unit>/` 配下に直接配置する方針。Storybook の構築・運用コストは 4 名 / 1 ヶ月では割に合わない |
| **暫定運用** | コンポーネントのプレビューは Expo Dev Client 上の screen で確認、Figma（B-103 の検討結果に依存）と並列でビジュアル管理 |
| **後付け導入トリガー** | 以下のいずれかで検討<br>1. UI コンポーネントが 30 個以上に肥大化した場合<br>2. デザイナーがチームに加入した場合<br>3. ハッカソン後の継続開発で複数アプリ間でデザインシステム共有が必要となった場合 |
| **優先度** | **低**（決勝までは不要） |
| **概算工数** | Storybook 導入 + 主要コンポーネント 10 個カタログ化 = 2d（Member A） |

---

### B-103. ダークモード切替（ライトモード追加）

| 項目 | 内容 |
|---|---|
| **項目名** | ライトモード対応の追加（OS 設定連動の自動切替を含む） |
| **出典** | [parallel-dev-prerequisites.md §3 N-5](../aidlc-docs/construction/plans/parallel-dev-prerequisites.md) |
| **見送り理由** | YUDANE のモックアップが既にダーク基調（Indigo×cold rose×cyan）で、深夜帯利用と背徳感の演出に直結。ライトモードはコンセプトと相反する |
| **暫定運用** | ダークモード固定。`tailwind.config.js` のトークンも単一テーマで管理 |
| **後付け導入トリガー** | 以下のいずれかで検討<br>1. ハッカソン後にプロダクト化する場合（A11y / WCAG 観点で必要になる可能性）<br>2. ユーザーテストでダーク基調が拒否された場合 |
| **優先度** | **低**（ハッカソン期間中は採用しない設計判断そのもの） |
| **概算工数** | ライトモードトークン整備 + 全画面確認 = 3d（Member A） |

---

## 4. ドキュメント編集ルール

- 新たに「後回し」「見送り」「将来検討」と判断した項目は、判断と同じ作業ターンで本ファイルに追記する
- エントリ ID は領域ごとに分離（B-001 系 = Construction 並列開発前提 / B-101 系 = Nice to have / B-201 系 = Per-Unit 内の見送り）
- 後付け導入が決定された項目は、本ファイルから削除せず「**ステータス: 採用済み（YYYY-MM-DD）**」を末尾に追記して履歴を残す
- 採用判断ロジックの変更を `aidlc-docs/audit.md` に必ず追記する

---

## 5. 関連リンク

- [.kiro/steering/structure.md](../.kiro/steering/structure.md) §6 Backlog 運用ルール
- [aidlc-docs/construction/plans/parallel-dev-prerequisites.md](../aidlc-docs/construction/plans/parallel-dev-prerequisites.md) — 並列開発前提の決定
- [aidlc-docs/aidlc-state.md](../aidlc-docs/aidlc-state.md) — AI-DLC 各ステージの進捗
- [aidlc-docs/audit.md](../aidlc-docs/audit.md) — 対話履歴と判断証跡
