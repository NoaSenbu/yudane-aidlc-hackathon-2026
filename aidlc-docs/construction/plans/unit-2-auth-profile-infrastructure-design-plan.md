# Unit-2 Auth & Profile — Infrastructure Design Plan

> Construction Phase / Per-Unit Loop / Unit-2 の AWS インフラ設計（`auth-stack`）。
> 参照: [Unit-2 NFR Design](../unit-2-auth-profile/nfr-design/) / [Unit-2 Functional Design](../unit-2-auth-profile/functional-design/) / [shared-infrastructure.md](../shared-infrastructure.md) / [Unit-1 Infrastructure Design](../unit-1-platform/infrastructure-design/) / [tech-cdk.md](../../../.kiro/steering/tech-cdk.md)
> 作成: 2026-05-29 / ステージ: 🟢 CONSTRUCTION / Infrastructure Design

---

## 0. Unit-1 から継承する基盤（再設計しない）

auth-stack は platform-stack の SSM 出力（shared-infrastructure.md §1）を参照する:
- VPC ID / private subnet ids / lambda SG（Lambda 配置）
- Cognito User Pool ID / Client ID（B-01 トリガーアタッチ先）
- KMS Key ARN（DynamoDB 暗号化）
- alerts SNS Topic ARN（認証失敗アラート、決勝）
- 命名規約 / IAM 最小権限 / cdk-nag は shared-infrastructure §2/§3 に従う

---

## 1. Unit-2 のインフラ範囲

| カテゴリ | リソース | 論理コンポーネント |
|---|---|---|
| データ | DynamoDB 4 テーブル（Users / PreferenceVectors / SafeguardStates / Achievements） | LC2-03/04/06 |
| Cognito | User Pool トリガー（B-01 を Post Confirmation / Pre Token Generation にアタッチ） | LC2-03 |
| バッチ | EventBridge cron 2 本（日次 / 週次）→ B-08 | LC2-04 |
| Lambda | B-01 AuthEdgeLambda / B-08 PreferenceVectorUpdater + auth API Lambda 群 | LC2-03/04/05/06 |
| 観測 | 認証失敗 Alarm（決勝、platform SNS 利用） | NFR2-SEC-04 |

---

## 1. 設計判断のための質問

`[Answer]:` タグで回答してください。

### Question 1（DynamoDB テーブル設計）
Users / PreferenceVectors / SafeguardStates / Achievements の **テーブル分割と PK 設計**をどうしますか？（Q3=A FD: テーブル分離 + 共通設定）

A) **4 テーブル分離、各 PK = userId（単純キー）**（UserProfile は Users に埋め込み。全テーブル PAY_PER_REQUEST / PITR / SSE-KMS。WeeklyReports は Unit-8 の report-stack）— FD/Unit-1 共通設定に整合、推奨
B) Users に全部埋め込み（PreferenceVector/Safeguard/Achievement を Users の属性に）
C) シングルテーブル（PK=userId, SK=entityType）
X) Other（[Answer]: の後に記述）

[Answer]: 

### Question 2（Cognito トリガー）
B-01 AuthEdgeLambda を Cognito User Pool にどうアタッチしますか？（User Pool は platform-stack）

A) **auth-stack から platform の User Pool を参照し、Post Confirmation / Pre Token Generation トリガーを追加**（User Pool 本体は platform 所有、トリガー Lambda は auth-stack 所有。クロススタックは SSM の userpool-id 参照 + IAM）— 推奨
B) User Pool ごと auth-stack に移す（platform-stack から外す）
C) トリガーを使わず、初回 API アクセス時に初期化（B-01 を API Lambda 化）
X) Other（[Answer]: の後に記述）

[Answer]: 

### Question 3（EventBridge cron）
B-08 の日次/週次バッチのスケジュールをどう定義しますか？（PAT2-BATCH-01）

A) **EventBridge Rule 2 本（日次 cron 04:00 JST / 週次 cron 日曜 22:00 JST）→ 同一 Lambda の別ハンドラ**（負債 72h クーリングオフの遅延評価も日次に内包）— Q3=A FD/NFR と整合、推奨
B) 日次のみ（週次集計は日次内で曜日判定）
C) Step Functions でワークフロー化（tech-cdk §8 で不採用）
X) Other（[Answer]: の後に記述）

[Answer]: 

### Question 4（環境・デプロイ）
auth-stack の環境戦略をどうしますか？（Unit-1 Q6=A: dev + prd）

A) **Unit-1 と同じ dev + prd 2 環境**（platform-stack の env と揃える。removalPolicy dev=DESTROY / prd=RETAIN。DynamoDB は prd=RETAIN でデータ保全）— 推奨
B) auth-stack 独自の環境構成
C) dev のみ（決勝前に prd 追加）
X) Other（[Answer]: の後に記述）

[Answer]: 

---

## 2. 実行ステップ（チェックボックス）

### Part 1: 計画 + 質問
- [x] Unit-2 NFR/Functional Design / shared-infrastructure の分析
- [x] Infrastructure Design Plan の作成（本ファイル）
- [x] ユーザーが Q1〜Q4 に回答（全問 A）
- [x] 回答の分析・曖昧さ検出（矛盾なし）

### Part 2: インフラ設計成果物の生成（承認後）
- [x] `aidlc-docs/construction/unit-2-auth-profile/infrastructure-design/infrastructure-design.md`（auth-stack の DynamoDB / Cognito トリガー / EventBridge / Lambda / IAM）
- [x] `deployment-architecture.md`（platform 依存 / SSM 参照 / デプロイ順序 / cdk-nag）
- [x] 自己レビュー（NFR Design / tech-cdk との整合・診断エラー）— deployment は diagnostics 0、infrastructure-design は Kiro Spec Format 誤検出のみ
- [ ] 完了メッセージ + 承認ゲート

---

## 3. Extension 適合の予定
| Extension | 扱い |
|---|---|
| SECURITY-01 | DynamoDB SSE-KMS（platform KMS） |
| SECURITY-06 | B-01/B-08/API Lambda 個別ロール最小権限 |
| SECURITY-07 | Lambda は platform VPC + SG |
| SECURITY-14 | 認証失敗 Alarm（決勝、platform SNS） |
| NG-4 | SafeguardStates テーブル + 負債遅延評価 |
