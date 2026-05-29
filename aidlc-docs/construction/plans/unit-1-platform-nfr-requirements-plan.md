# Unit-1 Platform — NFR Requirements Plan

> Construction Phase / Per-Unit Loop / Unit-1 Platform の非機能要件評価 + 技術選定の計画。
> 参照: [Functional Design](../unit-1-platform/functional-design/) / [要件書 §6 / §7](../../inception/requirements/requirements.md) / [tech.md](../../../.kiro/steering/tech.md) / [api-contracts.md](../../../.kiro/steering/api-contracts.md)
> 作成: 2026-05-29 / ステージ: 🟢 CONSTRUCTION / NFR Requirements
> 確定済み（Functional Design）: Q1=refinedA / Q2=A / Q3=A / Q4=refinedA / Q5=A / Q6=A / Q7=A

---

## 0. Unit-1 における NFR の位置づけ

Unit-1 Platform は横断基盤。よって本ステージの NFR は「Unit-1 自身の品質目標」だけでなく、**他 7 Unit が継承する横断 NFR 基盤（プラットフォーム規定値）** を定義する性格を持つ。

| 観点 | Unit-1 が定義する横断基盤 | 要件書の根拠 |
|---|---|---|
| 性能 | ApiClient のタイムアウト / リトライ既定値、コールドスタート 2s、テレメトリ overhead 上限 | §6.2 |
| スケーラビリティ | サーバーレス前提（Lambda/APIGW/DynamoDB）、同時 50→500、Redis ウォームキャッシュ | §6.3 |
| セキュリティ | SECURITY-01〜15 のうち Unit-1 が「基盤として実装」する項目（暗号化 / ログ / 認可土台 / SBOM / fail-closed 等） | §6.4 |
| テスタビリティ | PBT-02/03/04/06/07/08/09/10 を Unit-1 の対象ロジック（ASIN / Safeguard / Telemetry / Masking）に適用 | §6.5 |
| 可用性 | SLO 99.5%、ログ保持 90 日、フォールバック土台 | §6.7 |
| A11y | WCAG 2.2 AA 相当の土台（テーマトークン / SR 規約） | §6.6 |

> インフラの具体構成（VPC / IAM ポリシー / スタック分割）は次の **NFR Design** と **Infrastructure Design** で確定。本ステージは「要件値の確定」と「技術選定の確認」に集中する。

---

## 1. 技術選定の確認（要件書 §7 準拠、Unit-1 の確定事項）

以下は要件書 §7 / tech.md で既に確定済み。Unit-1 で実体化する分を再掲（質問ではなく確認）:

| 項目 | 確定値 |
|---|---|
| Mobile | React Native 0.76+ (New Arch) + TypeScript 5.x + AWS SDK v3 + TanStack Query + Zustand |
| 認証 | Cognito + Amplify Auth モジュールのみ + TOTP MFA |
| API/データ | API Gateway (REST) + Lambda (Python 3.13) + 生 DynamoDB + S3 + ElastiCache Redis + OpenSearch Serverless |
| IaC | AWS CDK (TypeScript v2) + Node.js 22 LTS |
| 観測 | CloudWatch Logs/Metrics/Alarms + X-Ray + Lambda Powertools |
| PBT FW | fast-check (TS) + Hypothesis (Python) |
| 契約 | OpenAPI 3.1 + openapi-typescript / datamodel-code-generator + Prism + Schemathesis |

→ これらは前提として確定。本計画の質問は「Unit-1 固有の NFR 数値・方針の確定」に絞る。

---

## 2. 設計判断のための質問

`[Answer]:` タグで回答してください。各質問に推奨案・背景・選択肢を添えています。

### Question 1
Unit-1（横断基盤）の **カバレッジ目標**をどう設定しますか？（tech.md の全体目標は Line 80%+ / Branch 70%+）

A) **基盤 Unit として全体目標より高く設定**（S-01 AsinExtractor / S-03 SafeguardPolicy / B-12 マスキングは多 Unit が依存する純ロジックのため Line 95%+ / Branch 90%+、ApiClient / Telemetry は Line 85%+。他 Unit のバグ波及を防ぐ）— 推奨
B) tech.md の全体目標（Line 80%+ / Branch 70%+）を Unit-1 にもそのまま適用
C) 純ロジック（Shared 層）のみ高め（90%+）、Mobile/Backend インフラ系は全体目標どおり
X) Other（[Answer]: の後に記述）

[Answer]: A

### Question 2
ApiClient（M-12）の **HTTP タイムアウト既定値**をどうしますか？（§6.2: 論破初回トークン 300ms、Share→メタ表示 2s、コールドスタート 2s）

A) **用途別に2系統**（通常 REST = 接続 3s / 全体 10s、SSE ストリーミング = 接続 3s / アイドル 30s・全体無制限。これを横断既定値とし各 Unit が必要時に上書き）— 推奨
B) 全リクエスト一律（接続 5s / 全体 15s）でシンプルに
C) タイムアウトは設けず、OS / プラットフォーム既定に委ねる
X) Other（[Answer]: の後に記述）

[Answer]: A

### Question 3
Unit-1 が定義する **テレメトリ／メトリクスの計測オーバーヘッド上限**と必須カスタムメトリクスをどうしますか？（§6.1 の北極星指標の集計基盤）

A) **オーバーヘッド上限 + 必須メトリクスを規定**（テレメトリ track は 1 呼び出し 1ms 未満・UI スレッドをブロックしない、flush は背景。Unit-1 が必須メトリクスのカタログ雛形を提供: api_latency / api_error_rate / cold_start_ms / safeguard_decision / cache_hit_rate）— 推奨
B) オーバーヘッド上限のみ規定し、メトリクスカタログは各 Unit が自由定義
C) メトリクスは CloudWatch 標準メトリクスのみ使い、カスタムメトリクス土台は最小限
X) Other（[Answer]: の後に記述）

[Answer]: C

### Question 4
Unit-1 が**基盤として実装責任を負う SECURITY ルール**の範囲をどうしますか？（SECURITY-01〜15、他 Unit は Unit-1 の土台を継承）

A) **基盤側で一元実装し全 Unit へ継承**（SECURITY-01 暗号化既定 / 02 ネットワークログ / 03 構造化ログ+PII マスク / 05 入力検証土台 / 06 IAM 最小権限の雛形 / 09 fail-closed・エラー秘匿 / 10 SBOM / 14 アラート土台 / 15 グローバルエラーハンドラ）。各 Unit 固有（08 リソースオーナー確認の業務判定 / 12 MFA フロー = Unit-2）は該当 Unit が実装 — 推奨
B) Unit-1 は最小限（ログ・SBOM・暗号化）のみ基盤化し、他は各 Unit 任せ
C) SECURITY 全 15 を Unit-1 で網羅実装してから他 Unit に渡す
X) Other（[Answer]: の後に記述）

[Answer]: A

### Question 5
Unit-1 対象ロジックへの **PBT 適用範囲**をどうしますか？（§6.5 PBT-01〜10 全面適用、fast-check / Hypothesis）

A) **対象ロジックごとに性質を割当**（S-01 ASIN = round-trip PBT-02 + 冪等正規化、S-03 Safeguard = invariant PBT-03（remaining>=0・実効上限<=上限）+ idempotency PBT-04、Telemetry = round-trip PBT-02、Masking = invariant「未分類キーは必ずマスク」、いずれも example-based PBT-10 併存、shrinking ログ PBT-08 必須）— 推奨
B) Shared 層（S-01/S-03）のみ PBT 適用、Mobile/Backend は example-based のみ
C) PBT は全ロジックに最低 1 性質を機械的に付与（性質の質より網羅優先）
X) Other（[Answer]: の後に記述）

[Answer]: A

### Question 6
Unit-1（基盤）の**可用性・フォールバックの土台**をどこまで持たせますか？（§6.7 SLO 99.5% / フォールバック / Creators API 障害時縮退）

A) **横断フォールバック土台を Unit-1 が提供**（ApiClient のサーキットブレーカ風の degrade フラグ + 各 Unit が「静的フォールバック」を差し込めるフック、Redis キャッシュアクセスの共通ラッパー、ヘルスチェックエンドポイント）。個別フォールバック中身（静的推薦カタログ等）は各 Unit — 推奨
B) Unit-1 はヘルスチェックとログのみ。フォールバックは完全に各 Unit 任せ
C) MVP（5/30）まではフォールバック土台を持たず、決勝（6/26）前に追加
X) Other（[Answer]: の後に記述）

[Answer]: B

### Question 7
Unit-1 の NFR 達成を **どのマイルストーンで満たす**ことを目標にしますか？（MVP 5/30 / 決勝 6/26）

A) **段階達成**（MVP 5/30 = 機能動作 + 構造化ログ + 基本認可 + 主要 PBT + カバレッジ目標、コールドスタート/SLO/フル SBOM/全アラートは決勝 6/26 までに最適化）— 現実的、推奨
B) 全 NFR を MVP 5/30 までに満たす（前倒し、リスク高）
C) MVP では NFR を最小限に留め、決勝でまとめて達成
X) Other（[Answer]: の後に記述）

[Answer]: A

---

## 3. 実行ステップ（チェックボックス）

### Part 1: 計画 + 質問
- [x] Functional Design 成果物の分析（domain-entities / business-logic / business-rules / frontend-components）
- [x] 要件書 §6 / §7 の NFR・技術スタック確認
- [x] NFR Requirements Plan の作成（本ファイル）
- [x] ユーザーが Q1〜Q7 に回答（Q1/Q2/Q4/Q5/Q6/Q7=確定、Q3 は矛盾検出 → clarification）
- [x] 回答の分析・曖昧さ検出 → Q3=C の矛盾を検出し clarification 作成 → Q3=B で確定

### Part 2: NFR 成果物の生成（承認後）
- [x] `aidlc-docs/construction/unit-1-platform/nfr-requirements/nfr-requirements.md`
  - 性能 / カバレッジ / セキュリティ / テスタビリティ / 可用性 / 観測 / A11y の Unit-1 向け定量要件 + マイルストーン別達成目標
- [x] `aidlc-docs/construction/unit-1-platform/nfr-requirements/tech-stack-decisions.md`
  - 要件書 §7 を Unit-1 で実体化する技術選定 + 横断ライブラリ（Powertools / fast-check / Hypothesis / openapi-typescript 等）の確定
- [x] 自己レビュー（要件書 §6 との整合・診断エラー）— tech-stack は diagnostics 0、nfr-requirements は Kiro Spec Format の誤検出のみ（AI-DLC 成果物のため対象外）
- [ ] 完了メッセージ提示 + 承認ゲート

---

## 4. Extension 適合の予定（NFR Requirements 段階での該当性）

| Extension | 本ステージでの扱い |
|---|---|
| SECURITY-01〜15 | Q4 で Unit-1 の基盤実装責任範囲を確定。nfr-requirements.md に各ルールの Unit-1 適用方針を表で明記 |
| PBT-01〜10 | Q5 で Unit-1 対象ロジックへの性質割当を確定。nfr-requirements.md に PBT マトリクスを記載 |
| 数値目標（性能 / カバレッジ / SLO） | Q1/Q2/Q3/Q6/Q7 で確定し定量要件として記録 |
