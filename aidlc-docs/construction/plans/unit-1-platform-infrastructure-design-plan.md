# Unit-1 Platform — Infrastructure Design Plan

> Construction Phase / Per-Unit Loop / Unit-1 Platform の AWS インフラ設計計画。
> 参照: [NFR Design](../unit-1-platform/nfr-design/) / [NFR Requirements](../unit-1-platform/nfr-requirements/) / [Functional Design](../unit-1-platform/functional-design/) / [tech-cdk.md](../../../.kiro/steering/tech-cdk.md) / [unit-of-work.md](../../inception/application-design/unit-of-work.md)
> 作成: 2026-05-29 / ステージ: 🟢 CONSTRUCTION / Infrastructure Design
> 確定済み: NFR-Req Q1-Q7 / NFR-Design Q1-Q4

---

## 0. Unit-1 のインフラ範囲（unit-of-work.md より）

`platform-stack`（共通基盤）が範囲。他 Unit のスタックはこの基盤の上に乗る。

| カテゴリ | リソース | 論理コンポーネント（LC） |
|---|---|---|
| ネットワーク | VPC / Subnet / VPC Endpoint / Security Group | SECURITY-07 |
| API | API Gateway (REST) + Lambda Authorizer | LC-04 |
| 認証基盤 | Cognito User Pool（基盤のみ。MFA フロー実装は Unit-2） | — |
| データ（共通） | DynamoDB 共通設定 / S3（Data Lake / カタログ）/ ElastiCache Redis / OpenSearch Serverless | LC-02/06 |
| 観測 | CloudWatch Logs/Metrics/Alarms + X-Ray | LC-03 |
| セキュリティ | KMS / IAM 基本ロール / Secrets Manager / SSM Parameter Store | SECURITY-01/06 |
| 共通 Lambda | B-12 AuditLogger（layer/lib）/ B-14 TelemetryIngestion / health | LC-02/03/05 |
| CI 基盤 | SBOM 生成 / cdk-nag | SECURITY-10 |

---

## 1. 設計判断のための質問

`[Answer]:` タグで回答してください。各質問に推奨案・背景・選択肢を添えています。

### Question 1（ネットワーク）
VPC 構成をどうしますか？（SECURITY-07: VPC 内 Lambda + VPC Endpoint。§6.3: 同時 50→500）

A) **2 AZ / public + private(with egress) + isolated の 3 層 + 主要 VPC Endpoint（DynamoDB/S3 Gateway、Secrets/CloudWatch/Bedrock Interface）+ NAT 1 基（dev）**（本番相当の最小構成、コスト抑制）— 推奨
B) VPC なし（Lambda を非 VPC で動かし、DynamoDB/S3 はパブリックエンドポイント + IAM）。コスト最小だが SECURITY-07 と不整合
C) 3 AZ フル冗長 + NAT 各 AZ（高可用だが MVP にはオーバースペック・高コスト）
X) Other（[Answer]: の後に記述）

[Answer]: A

### Question 2（API Gateway / 認証）
API Gateway と Authorizer の構成をどうしますか？（LC-04: Authorizer + sub 照合デコレータ）

A) **REST API（単一 API GW）+ Lambda Authorizer（JWT 検証、結果キャッシュ TTL 5 分）+ usage plan で rate limit**（全 Unit が共有する単一 API、パスを Unit 別に分割）— 推奨
B) Unit ごとに API Gateway を分割（独立性は高いが Cognito Authorizer や CORS 設定が重複、コスト増）
C) HTTP API（API Gateway v2、低コスト・低レイテンシだが REST 専用機能が一部未対応）
X) Other（[Answer]: の後に記述）

[Answer]: A

### Question 3（データストア共通設定）
DynamoDB の共通設計方針をどうしますか？（生 DynamoDB、各 Unit が固有テーブルを持つ）

A) **テーブル分離 + 共通設定を Unit-1 が規定**（テーブルは各 Unit 所有。Unit-1 は共通設定 = オンデマンド課金 / PITR 有効 / SSE-KMS / TTL 属性規約 / 命名 `yudane-<unit>-<env>-<entity>` / GSI 命名規約を定義）— 推奨
B) シングルテーブルデザイン（全 Unit が 1 テーブルを共有、PK/SK 設計を Unit-1 が一括管理）— 並行開発の独立性が下がる
C) 各 Unit が完全自由にテーブル設計（共通設定なし）— 一貫性が崩れる
X) Other（[Answer]: の後に記述）

[Answer]: A

### Question 4（メッセージング / 非同期）
非同期・スケジューリング基盤をどう扱いますか？（services.md: Step Functions 不採用、カート追撃は EventBridge Scheduler 単独。Q3=A: テレメトリにサーバー専用キューは設けない）

A) **Unit-1 は基盤を持たず規約のみ**（EventBridge Scheduler は Unit-5 Cart が自身のスタックで使う。Unit-1 は EventBridge デフォルトバス + Scheduler 用 IAM ロール雛形 / 命名規約のみ提供。テレメトリは API 同期受信 = Q3=A）— 推奨
B) Unit-1 が共通 SQS / SNS / EventBridge カスタムバスを先行整備（将来の非同期拡張に備える、現状オーバースペック）
C) 各 Unit が完全自由（規約なし）
X) Other（[Answer]: の後に記述）

[Answer]: A

### Question 5（観測 / アラート）
監視・アラートの基盤をどこまで Unit-1 で整えますか？（SECURITY-02/14、ログ保持 90 日、Q7=A 段階達成）

A) **MVP は基盤 + 主要アラート、決勝でフル**（MVP: CloudWatch Logs 90 日保持 / X-Ray / 認証失敗・5xx の主要 Alarm + SNS 通知トピック。決勝: 北極星指標ダッシュボード / 全 Alarm / 異常検知）— Q7=A と整合、推奨
B) MVP からフルセット（全 Alarm + ダッシュボード）を整える（前倒し、工数増）
C) MVP はログのみ、Alarm は決勝で追加
X) Other（[Answer]: の後に記述）

[Answer]: ___a

### Question 6（環境戦略）
デプロイ環境をどう構成しますか？（書類審査・予選はモックデータ可、決勝は AWS 本番デプロイ）

A) **dev + prd の 2 環境**（dev = removalPolicy DESTROY / NAT 1 基 / コスト最小、prd = RETAIN / 決勝前に構築。env は CDK context で切替）— 推奨
B) dev のみ（決勝直前に prd を追加）
C) dev + stg + prd の 3 環境（手厚いが 4 名 × 短期間には過剰）
X) Other（[Answer]: の後に記述）

[Answer]: A

### Question 7（ElastiCache / OpenSearch の構築タイミング）
ElastiCache Redis（Creators API キャッシュ・レート制限）と OpenSearch Serverless（ベクトル検索）を Unit-1 でいつ構築しますか？（主利用は Unit-4 Reel / Unit-5 Cart）

A) **段階構築**（ElastiCache Redis は MVP で最小ノード構築（カート/リールが依存）。OpenSearch Serverless は Unit-4 着手時に Unit-1 の platform-stack へ追加し、MVP では小規模コレクション）— 推奨
B) Unit-1 着手時に両方フル構築（早いが利用前のコスト発生）
C) 両方とも利用 Unit（Unit-4/5）のスタックに委譲（platform-stack には含めない）
X) Other（[Answer]: の後に記述）

[Answer]: C

---

## 2. 実行ステップ（チェックボックス）

### Part 1: 計画 + 質問
- [x] Functional / NFR Design 成果物の分析
- [x] tech-cdk.md / unit-of-work.md のインフラ範囲確認
- [x] Infrastructure Design Plan の作成（本ファイル）
- [x] ユーザーが Q1〜Q7 に回答（Q1-Q6=A、Q7=C は矛盾検出）
- [x] 回答の分析・曖昧さ検出 → Q7=C の矛盾を検出し clarification 作成 → Q7=A で確定

### Part 2: インフラ設計成果物の生成（承認後）
- [x] `aidlc-docs/construction/unit-1-platform/infrastructure-design/infrastructure-design.md`
  - platform-stack の AWS サービスマッピング（VPC / API GW / Cognito / DynamoDB 共通 / S3 / Redis / OpenSearch / KMS / IAM / 観測）
- [x] `aidlc-docs/construction/unit-1-platform/infrastructure-design/deployment-architecture.md`
  - 環境戦略 / スタック依存（SSM 連携）/ デプロイ順序 / cdk-nag 方針 / デプロイ図
- [x] `aidlc-docs/construction/shared-infrastructure.md`
  - 他 Unit が継承する共通インフラ規約（命名 / 暗号化 / IAM / SSM パラメータ / VPC 参照方法）
- [x] 自己レビュー（NFR Design / tech-cdk との整合・診断エラー）— deployment/shared は diagnostics 0、infrastructure-design は Kiro Spec Format の誤検出のみ（AI-DLC 成果物のため対象外）
- [ ] 完了メッセージ提示 + 承認ゲート

---

## 3. Extension 適合の予定

| Extension | 本ステージでの扱い |
|---|---|
| SECURITY-01 暗号化 | DynamoDB/S3 SSE-KMS、TLS 強制を infrastructure-design に明記 |
| SECURITY-06 IAM 最小権限 | Lambda 個別ロール雛形、`*` 禁止、cdk-nag aws-solutions-iam4/5 |
| SECURITY-07 ネットワーク | Q1 で VPC + VPC Endpoint 構成を確定 |
| SECURITY-02/14 観測・アラート | Q5 で監視基盤・Alarm 構成を確定 |
| SECURITY-10 SBOM | deployment-architecture に CI 組込みを記載 |
| cdk-nag | AwsSolutionsChecks 全適用、Suppression は理由コメント必須 |
