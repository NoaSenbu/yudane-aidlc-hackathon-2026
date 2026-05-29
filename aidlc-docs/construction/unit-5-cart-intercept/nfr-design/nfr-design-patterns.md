# Unit-5 Cart Intercept — NFR Design Patterns

> Construction Phase の Per-Unit Loop NFR Design Part 2 Generation 成果物。Q1〜Q6 確定（再検証で 3 件修正済み）+ Functional Design / NFR Requirements で確定済みの 16 パターンを統合し、Resilience / Scalability / Performance / Security / Observability の 5 カテゴリに整理する。
>
> 参照: [nfr-design-plan.md](../../plans/unit-5-cart-intercept-nfr-design-plan.md)（Q1〜Q6 確定済み）/ [logical-components.md](./logical-components.md) / [nfr-requirements.md](../nfr-requirements/nfr-requirements.md) / [functional-design.md](../functional-design/functional-design.md)

---

## 0. 確定事項サマリ

| Q | 論点 | 確定 |
|---|---|---|
| Q1 | Circuit Breaker 採用範囲 | **B**（CB 不採用、boto3 adaptive + Lambda Reserved で十分）|
| Q2 | キャッシュ戦略レイヤリング | **A'**（staleTime 階層化: 一覧 60s / 詳細 0s）|
| Q3 | Bulkhead パターン粒度 | **A**（関数別 Reserved Concurrency）|
| Q4 | Saga パターン採用判断 | **A'**（部分失敗許容 + B-05 リトライバッチ仕様確定）|
| Q5 | Database Replication（DAX 等）| **A**（不採用、DDB On-Demand 単独）|
| Q6 | Telemetry / Audit Log 分離 | **A**（完全分離: Audit = Logs / Telemetry = EMF + Firehose）|

---

## 1. Resilience パターン

### 1.1 EventBridge Retry + Lambda DLQ（既確定）

**出典**: [Functional Design §2.2 B-05](../functional-design/functional-design.md#22-b-05-cartattackschedulerq4--a-反映) / [§3.1 Stack 構成](../functional-design/functional-design.md#31-stack-構成)

**動作**:

- EventBridge Scheduler の `RetryPolicy: MaximumRetryAttempts=2 + MaximumEventAgeInSeconds=600`
- 失敗継続なら Lambda DLQ（`NotificationDispatcherDlq`）へ自動退避
- DLQ メッセージは 14 日保持、CloudWatch Alarm 1 で 1 件到達時に Slack 通知

### 1.2 Idempotency Middleware（既確定）

**出典**: [Unit-1 §3.2 IdempotencyKeys](../../unit-1-platform/functional-design/data-model.md#32-idempotencykeysq7-確定で新設)

**動作**:

- POST 系 API（`/v1/cart-watch-items` / `/v1/push-tokens`）に必須 `Idempotency-Key` ヘッダ
- DDB IdempotencyKeys テーブルで atomic lock + 5 分 TTL + S3 レスポンスボディキャッシュ
- 同 key 再送 → キャッシュ済みレスポンス即返却

### 1.3 NotificationLogs stepKey ConditionExpression（既確定）

**出典**: [NFR Requirements §4.1](../nfr-requirements/nfr-requirements.md#41-配信冪等性の強化q5--b-反映)

**動作**:

- `NotificationLogs.stepKey = {itemId}#{step}` に `ConditionExpression: attribute_not_exists(stepKey)`
- 同 step 重複試行は ConditionalCheckFailedException → `suppressed_as_duplicate` Telemetry 記録

### 1.4 Circuit Breaker は不採用（Q1 = B 確定）

**判断根拠**: [Q1](../../plans/unit-5-cart-intercept-nfr-design-plan.md) 再検証で B-11 owner（Unit-4）への依頼問題を発見、boto3 adaptive リトライ + Lambda Reserved Concurrency で代替

```python
# backend/src/cart/_creators_api_client.py（Unit-4 owner 既存実装を consume）
import boto3
from botocore.config import Config

# B-04 / B-06 から呼び出される際の boto3 設定
client_config = Config(
    retries={
        "max_attempts": 3,
        "mode": "adaptive",  # AWS 内部の指数バックオフ + ジッター
    },
    connect_timeout=2,
    read_timeout=5,
)
```

### 1.5 B-05 リトライバッチ（Q4 = A' 確定）

**判断根拠**: [Q4](../../plans/unit-5-cart-intercept-nfr-design-plan.md) で「部分失敗許容」前提として B-05 リトライバッチ仕様を確定

| 項目 | 値 |
|---|---|
| 実行頻度 | EventBridge Schedule `rate(15 minutes)` |
| Lambda | `cartAttackSchedulerRetryFunction`（VPC 外、Memory 512MB、Timeout 60s）|
| 対象抽出 | GSI1（status=watching）で `attackSchedule` 属性が空 or 不完全（3 件未満）かつ `createdAt < 24h 前` |
| 並列度 | 1 batch × 最大 100 件、Reserved Concurrency 10 |
| 3 回失敗時 | CartWatchItem を `status=watching_orphaned` に遷移、CloudWatch Alarm 5 発火 |
| Telemetry | `cart.scheduler.retry_succeeded` / `cart.scheduler.retry_failed`（EMF）|

**実装**: [logical-components.md §B-05 RetryFunction](./logical-components.md) 参照

### 1.6 部分失敗許容（Q4 = A' 確定、Saga 不採用）

**判断根拠**: カート監視は eventually consistent で OK（追撃通知 1 ステップ欠けても UX 致命的影響なし）。Step Functions 不採用方針（tech.md §4）整合。

```python
# backend/src/cart/handlers/cart_intake.py
# 部分失敗許容: DDB PutItem 成功 + Scheduler 1 失敗 でも CartWatchItem は status=watching で残す
# 注: audit = AuditLogger(service="cart-intake") は呼び出し元 lambda_handler 冒頭で初期化済み
try:
    attack_schedule = schedule_attacks(user_id, item.itemId, extracted_asin, now)
    repo.update_attack_schedule(user_id, extracted_asin, attack_schedule)
except Exception as e:
    audit.log("error", "Failed to schedule attacks", {"itemId": item.itemId, "error": str(e)})
    # CartWatchItem は維持、B-05 リトライバッチ（§1.5）で補完
```

---

## 2. Scalability パターン

### 2.1 Bulkhead: 関数別 Reserved Concurrency（Q3 = A 確定）

**動作**: 各 Lambda 関数に Reserved Concurrency を設定して同時実行数を分離、1 関数の枯渇が他関数に影響しない隔壁性を確保。

| Lambda | Reserved Concurrency | 出典 |
|---|---|---|
| cart_intake | 100（MVP）/ 500（本番化）| Functional Design §3.1 + NFR §2.2 |
| cart_dismiss | 50 | Functional Design §3.1 |
| cart_list | 100 | Functional Design §3.1 |
| push_token | 20 | Functional Design §3.1 |
| notification_dispatcher | 200（MVP）/ 500（本番化）| Functional Design §3.1 |
| cart_attack_scheduler_retry | 10（5 巡目追加、Q4 = A' リトライバッチ）| §1.5 |

### 2.2 EventBridge One-time Schedule（既確定）

**出典**: Functional Design Q4 = A

**動作**: 1 回限り発火 → `ActionAfterCompletion=DELETE` で自動削除。100 万 Schedule/アカウント上限の 7.5%（本番化想定）で十分余裕。

### 2.3 DDB On-Demand 自動スケール（既確定、Q5 = A 整合）

**判断根拠**: cart_list p95 < 500ms は DDB On-Demand 単独で達成可能（実測 < 100ms 想定）、DAX $200/月は本 Unit 全体 $20-25/月に対し過剰。

### 2.4 Property 6 件数上限（既確定）

**動作**: 1 ユーザー × active 状態（4 status）= 100 件上限。B-04 intake 前に `count_active(user_id)` で件数取得、超過時 429 返却。EventBridge Scheduler 100 万上限の `1/10000` で十分余裕。

---

## 3. Performance パターン

### 3.1 SnapStart 適用 3 Lambda（Q4 = B' 確定、NFR Requirements）

**出典**: [NFR Q4](../../plans/unit-5-cart-intercept-nfr-requirements-plan.md) / [tech-stack-decisions.md §3](../nfr-requirements/tech-stack-decisions.md#3-snapstart-適用範囲q4--b-確定)

**動作**:

| Lambda | SnapStart | 理由 |
|---|---|---|
| cart_intake | ✅ ON_PUBLISHED_VERSIONS | end-to-end 2 秒 SLO 達成のため Cold Start 排除 |
| cart_dismiss | ✅ ON_PUBLISHED_VERSIONS | 「いらない」タップ後ロールバック時の UX 担保 |
| notification_dispatcher | ✅ ON_PUBLISHED_VERSIONS | 配信遅延 ± 30s 達成のため |
| cart_list | ❌ なし | 低頻度・バッファ可能 |
| push_token | ❌ なし | 低頻度（起動毎 + ローテーション）|
| cart_attack_scheduler_retry | ❌ なし | バックグラウンド処理、UX 影響なし |

### 3.2 ARM64 アーキテクチャ（既確定）

**出典**: [Unit-1 §3.2](../../unit-1-platform/functional-design/functional-design.md)

**動作**: 全 Lambda を `lambda.Architecture.ARM_64` で実行、x86_64 比 20% コスト削減 + 性能向上。

### 3.3 ElastiCache 6h 商品メタキャッシュ（既確定、Unit-4 owner）

**動作**: B-11 CreatorsApiClient が Creators API 応答を Redis 6h TTL でキャッシュ。本 Unit は consumer のみ、ヒット率は Day 3 IT-08 で実測（[NFR §1.4](../nfr-requirements/nfr-requirements.md#14-性能リスクと緩和策)）。

### 3.4 staleTime 階層化（Q2 = A' 確定）

**動作**: TanStack Query の staleTime を一覧モード / 詳細モードで分離。

```typescript
// 一覧モード（M-05 起動時、Home hero）
useQuery({
  queryKey: ['cart-watch-items'],
  queryFn: () => apiFetch<CartWatchItemDto[]>('/v1/cart-watch-items?status=active'),
  staleTime: 60_000,  // 60 秒間は cache 利用、再 fetch 不要
});

// 詳細モード（通知タップ → CartInterceptScreen detail mode）
export function useCartWatchItem(asin: string) {
  return useQuery({
    queryKey: ['cart-watch-item', asin],
    queryFn: () => apiFetch<CartWatchItemDto>(`/v1/cart-watch-items/${asin}`),
    staleTime: 0,  // 通知タップ時は常に refetch（status 遷移の即時反映が必要）
  });
}
```

**意図**: 通知タップ時に古い status（watching → notified-30m 遷移前）を見るリスクを排除。一覧モードは UX 上 60s の遅延を許容して fetch コスト削減。

### 3.5 EMF 即時計測（既確定、NFR §1.2）

**動作**: Telemetry を CloudWatch EMF で 1 分粒度 publish、Alarm 5 分以内発火。S3 + Firehose は長期保管用として併存。

---

## 4. Security パターン

### 4.1 KMS CMEK 全 DDB / SQS DLQ 暗号化（既確定）

**出典**: Functional Design §3.1 / SECURITY-01

**動作**: Unit-1 共通 KMS キー（`platformStack.kmsKey`）を CartWatchItems / NotificationLogs / SQS DLQ で共有暗号化。

### 4.2 Cognito + Lambda Authorizer ハイブリッド（既確定、Unit-1 Q2 = C）

**出典**: [Unit-1 §4.1 Authorizer 配置](../../unit-1-platform/functional-design/functional-design.md#41-authorizer-配置)

**動作**:

| エンドポイント | Authorizer |
|---|---|
| GET /v1/cart-watch-items | Cognito Authorizer（軽量、Safeguard 不要）|
| POST /v1/cart-watch-items | Cognito Authorizer（intake は Safeguard 不要）|
| DELETE /v1/cart-watch-items/{asin} | Cognito Authorizer |
| GET /v1/cart-watch-items/{asin} | Cognito Authorizer |
| POST /v1/push-tokens | Cognito Authorizer |
| **POST /v1/amazon-transitions**（本 Unit から呼出）| **Lambda Authorizer**（Safeguard 統合、月間上限）|
| **POST /v1/debate-sessions**（本 Unit から呼出）| **Lambda Authorizer**（Safeguard 統合、クールダウン）|

### 4.3 Property 6 + WAF Rate-based Rule（既確定）

**動作**:

- Property 6: active 100 件上限（B-04 で `count_active()` チェック、超過時 429）
- WAF Rate-based Rule: 10 req/sec/userId（POST /v1/cart-watch-items に適用）
- 60 req/sec/userId（GET /v1/cart-watch-items に適用）
- 1 req/min/userId（POST /v1/push-tokens に適用、低頻度のため）

### 4.4 配信冪等性（NotificationLogs stepKey、既確定）

**動作**: §1.3 と同じ。Q5 = B' で確定済みの ConditionExpression による物理的重複排除。

### 4.5 IDOR 防御（PK = USER#{cognito.sub} 強制）

**動作**: 全 DDB Query / GetItem / PutItem で PK を `USER#{event["requestContext"]["authorizer"]["claims"]["sub"]}` から取得、ユーザー自身のリソースのみアクセス可能。SECURITY-08 整合。

### 4.6 SCHEDULER_ROLE Confused Deputy 対策（既確定、Issue L 対応）

**動作**: Trust Policy に `aws:SourceAccount` + `aws:SourceArn` 条件を追加、wildcard を `arn:aws:scheduler:*:*:schedule/default/cart-*` に限定。

---

## 5. Observability パターン

### 5.1 Audit / Telemetry 完全分離（Q6 = A 確定）

**動作**:

| 用途 | 経路 | 保管 |
|---|---|---|
| **Audit Log** | B-12 AuditLogger 構造化 JSON → CloudWatch Logs | 90 日保持（SECURITY-14）|
| **Telemetry（即時アラート）** | EMF → CloudWatch Metrics | 15 ヶ月（CloudWatch 標準）|
| **Telemetry（長期分析）** | M-13 → POST /v1/telemetry → B-14 → Firehose → S3 Parquet | 永久（コスト試算 §6.4 では数値考慮済み）|

**理由**: 統合すると Telemetry の高頻度 publish が CloudWatch Logs を flood しコスト増。関心の分離（Audit = SECURITY 監査用、Telemetry = KPI 分析用）が明確化。

### 5.2 CloudWatch Alarms 5 系統（既確定 4 系統 + Q4 = A' で 1 系統追加）

**出典**: [Functional Design §3.3](../functional-design/functional-design.md#33-cloudwatch-alarms5-巡目追加issue-z) + 本 Unit Q4 = A'

| # | 名前 | トリガー | 通知先 |
|---|---|---|---|
| 1 | NotificationDispatcherDlqAlarm | DLQ メッセージ 1 件到達 | Slack #yudane-emergency |
| 2 | NotificationFailureRateAlarm | `failed / (sent + failed)` > 5% | Slack #yudane-dev |
| 3 | SchedulerCreateFailureAlarm | `cart.scheduler.create_failed` > 5/5min | Slack #yudane-dev |
| 4 | LambdaErrorAlarm × 5 | 各 Lambda Error > 5 件/5min | Slack #yudane-dev |
| **5** | **SchedulerRetryFailureAlarm** | **`cart.scheduler.retry_failed` > 5/15min**（Q4 = A' リトライバッチ用）| Slack #yudane-emergency |

### 5.3 X-Ray Active Tracing は不採用（Q7 = A 整合、Unit-1 backlog B-001）

**動作**: 採用しない、CloudWatch Logs Insights クエリで代替（[NFR §5.3.2](../nfr-requirements/nfr-requirements.md#532-cloudwatch-logs-insights-クエリ集即時利用可能)）。

---

## 6. パターン適用マトリクス（NFR 軸 × コンポーネント）

| パターン | M-05 | M-08 | M-09 | B-04 | B-05 | B-06 | retry_batch（B-05'）| DDB | EB Sched | EUM Push |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| EventBridge Retry | | | | | ✅ | ✅ | | | ✅ | |
| Lambda DLQ | | | | | | ✅ | | | | |
| Idempotency Middleware | | | | ✅ | | | | ✅ | | |
| stepKey ConditionExpression | | | | | | ✅ | | ✅ | | |
| boto3 adaptive retries | | | | ✅ | | ✅ | ✅ | | | ✅ |
| B-05 retry batch | | | | | ✅ | | ✅ | ✅ | ✅ | |
| 関数別 Reserved Concurrency | | | | ✅ | ✅ | ✅ | ✅ | | | |
| One-time Schedule | | | | | ✅ | | | | ✅ | |
| Property 6 件数上限 | | | | ✅ | | | | ✅ | | |
| SnapStart | | | | ✅ | | ✅ | | | | |
| ARM64 | | | | ✅ | ✅ | ✅ | ✅ | | | |
| ElastiCache 6h cache | | | | ✅(consumer) | | | | | | |
| staleTime 階層化 | ✅ | | | | | | | | | |
| EMF 即時計測 | | | | ✅ | ✅ | ✅ | ✅ | | | |
| KMS CMEK 暗号化 | | | | | | | | ✅ | | |
| Cognito + Lambda Authorizer | | | | ✅ | | | | | | |
| Property 6 + WAF | | | | ✅ | | | | | | |
| IDOR 防御（PK=USER#sub） | | | | ✅ | ✅ | ✅ | ✅ | ✅ | | |
| Audit / Telemetry 分離 | ✅ | | ✅ | ✅ | ✅ | ✅ | ✅ | | | |
| CloudWatch Alarms 5 系統 | | | | ✅ | ✅ | ✅ | ✅ | | | |

---

## 7. ハッカソン書類審査・予選評価軸へのインパクト

> **2026-05-29 追記（Issue C1 対応）**: 本 NFR Design パターン適用は [AGENTS.md §12.4 AI Code Generation での TDD（CDK は Snapshot TDD）](../../../../.kiro/steering/AGENTS.md#124-ai-code-generation-での-tddc-確定) / [tech-cdk.md §6.1 Snapshot TDD](../../../../.kiro/steering/tech-cdk.md#61-snapshot-tdd-cdk-必須) と整合。19 パターンすべてを Red → Green → Refactor → Snapshot 固定 のサイクルで CDK Stack に組み込む。

| 評価軸 | 本ドキュメントの貢献 |
|---|---|
| ビジネス意図の明確さ | （直接貢献なし、技術文書のため）|
| Unit 分解の適切さ | **強化**: Unit-5 のパターンが Lambda / DDB / EB Schedule / EUM Push の論理コンポーネント単位で分類、Unit 横断パターン継承（SnapStart / Idempotency Middleware 等）が見える化 |
| 創造性とテーマ適合性 | （直接貢献なし）|
| ドキュメント品質 | **強化**: 5 カテゴリ（Resilience / Scalability / Performance / Security / Observability）× 19 パターンを整合的にマッピング、再検証で 3 件修正済み（Q1 / Q2 / Q4） |
| AI-DLC プロセス（予選評価軸） | **強化**: Functional Design + NFR Requirements + NFR Design の段階的精緻化が透明、批判的再検証プロセスが審査員にアピール可能 |
