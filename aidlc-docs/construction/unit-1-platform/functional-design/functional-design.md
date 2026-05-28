# Unit-1 Platform — Functional Design

> Construction Phase の Per-Unit Loop 第 1 ターン Part 2 Generation 成果物。Q1〜Q10 の確定を仕様レベルに展開する。
>
> 参照: [functional-design-plan.md](./functional-design-plan.md)（Q1〜Q10 確定済み）/ [data-model.md](./data-model.md) / [sequence-diagrams.md](./sequence-diagrams.md) / [openapi-skeleton-plan.md](./openapi-skeleton-plan.md)

---

## 0. 確定事項サマリ

| Q | 論点 | 確定 |
|---|---|---|
| Q1 | Cognito MFA 強制範囲 | A: dev = 任意 / prd = 強制 |
| Q2 | API Gateway Authorizer 方式 | C: ハイブリッド（Cognito Authorizer 基本 + Safeguard 介入時 Lambda Authorizer）|
| Q3 | Telemetry 投入の同期 / 非同期 | B + 安全装置 3 点（Idempotency Key + Lambda DLQ + backlog B-201）|
| Q4 | Shared 層パッケージング | A: npm workspaces |
| Q5 | VPC 構成 | B: 必要な Lambda のみ VPC + B-02 DDB 化 + SnapStart |
| Q6 | DynamoDB テーブル設計 | B: Multi Table Design |
| Q7 | M-12 ApiClient リトライ戦略 | B: GET/DELETE 自動リトライ + POST/PATCH 冪等キー必須 |
| Q8 | M-13 Telemetry オフライン挙動 | A: AsyncStorage 永続キュー、起動時 + 5 分 flush |
| Q9 | OpenAPI 第 1 版エンドポイント | B: 全 7 UC を含める |
| Q10 | CI セットアップのスコープ | A: CI + deploy-dev のみ Unit-1 完成 |

---

## Overview

本ドキュメントは Unit-1 Platform の **機能設計仕様書**。Q1〜Q10 の確定（functional-design-plan.md）を IO / 状態 / エラー仕様レベルに展開し、各コンポーネント実装の根拠を提示する。

Unit-1 Platform は YUDANE 全 8 Units の基盤として、Mobile アプリのシェル / 認証 / API クライアント / Telemetry / Backend の共通ライブラリ / Shared 層 / Infrastructure を提供する。本 Unit のインターフェースが他全 Unit の実装の前提となる。

## Architecture

YUDANE は Mobile（React Native + Expo）/ Backend（API Gateway + Lambda）/ Infra（CDK）/ Shared（npm workspaces）の 4 層モノレポで構成される。Unit-1 Platform はこの 4 層すべてに横断的に基盤コンポーネントを配置する。

層別の Unit-1 担当コンポーネント:

- **Mobile**: M-01 AppShell / M-12 ApiClient / M-13 Telemetry（§1）
- **Backend**: B-12 AuditLogger / B-14 TelemetryIngestionService / B-01 AuthEdgeLambda（§2）
- **Infrastructure**: VPC / API Gateway / Cognito User Pool / DynamoDB 共通 / ElastiCache Redis / OpenSearch Serverless / IAM 基本（§3）
- **API Gateway Authorizer**: ハイブリッド配置（Cognito Authorizer 基本 + Lambda Authorizer for Safeguard、§4）
- **モノレポ**: npm workspaces による 4 層管理（§5）
- **Shared**: S-01 AsinExtractor / S-02 SchemaRegistry / S-03 SafeguardPolicy / S-04 TelemetryContracts（§6）
- **CI/CD**: GitHub Actions の ci.yml + deploy-dev.yml（§7）

VPC 配置の方針は Q5 確定で「必要な Lambda のみ VPC、B-02 は DDB 化により VPC 外 + SnapStart」とした（§3.1）。

シーケンス図は別ファイル [sequence-diagrams.md](./sequence-diagrams.md) に集約。

## Components and Interfaces

詳細は §1〜§6 で各コンポーネントの IO 仕様 / 状態 / エラー仕様 を定義する。本 Unit で確定する主要インターフェース:

- M-12 ApiClient の `apiFetch` / `apiStream`（§1.2、Q7 = B 反映の冪等キー対応）
- M-13 Telemetry の `track` / `flush`（§1.3、Q3 + Q8 反映の安全装置 3 点 + AsyncStorage 永続キュー）
- B-12 AuditLogger の `log` / `metric` / `trace`（§2.1）
- B-14 TelemetryIngestionService の `lambda_handler`（§2.2、Q3 確定の Idempotency Key + DLQ）
- API Gateway Authorizer 配置マトリクス（§4.1、Q2 = C ハイブリッド反映）

## Data Models

DynamoDB Multi Table Design（Q6 = B 確定）の詳細は別ファイル [data-model.md](./data-model.md) に集約。本 Unit で新設する 2 テーブル:

- `DebateRateLimits`（Q5 確定で B-02 の Redis 代替）
- `IdempotencyKeys`（Q7 確定で M-12 ApiClient の冪等キー検知）

その他 11 テーブル（Users / PreferenceVectors / CartWatchItems / DebateSessions / 他）は各 Unit owner が Functional Design で詳細化する。

## Error Handling

各層でのエラー処理方針:

- **Mobile (M-12)**: Problem Details → ApiError マッピング、UI 上の扱いを §1.2 で定義
- **Mobile (M-13)**: 永続キュー保留 + Idempotency Key 再送（§1.3、Q3 安全装置 1 + Q8 反映）
- **Backend (B-14)**: Lambda DLQ で自動退避、ElastiCache 1h TTL で重複検知（§2.2、Q3 安全装置 2）
- **API Gateway**: RFC 7807 Problem Details で統一（[api-contracts.md §4.4](../../../../.kiro/steering/api-contracts.md)）

## Testing Strategy

Unit-1 で必要なテスト:

- **Unit Test**: Vitest（Mobile）+ pytest（Backend）、Line 80%+ / Branch 70%+
- **Property-Based Test**: fast-check（M-12 リトライ動作）+ Hypothesis（B-14 重複検知）
- **Contract Test**: Schemathesis（OpenAPI 第 1 版凍結後、[openapi-skeleton-plan.md](./openapi-skeleton-plan.md)）
- **Integration Test**: IT-07（サインアップ → MFA → プロファイル永続化、[api-contracts.md §11](../../../../.kiro/steering/api-contracts.md) 参照、Unit-2 と共通）

詳細なテストレイヤーとカバレッジは [tech.md §6 品質ゲート](../../../../.kiro/steering/tech.md) を参照。

## Correctness Properties

本 Unit が満たすべき不変条件:

### Property 1: 冪等性

**Validates: Requirements 6.4** SECURITY-08（IDOR / 重複処理防止）

同 Idempotency-Key で複数回 POST してもサーバー側状態は 1 回分のみ変化（Q7 反映）。`IdempotencyKeys` テーブルの `requestHash` 検証で重複検知し、初回の `responseStatus` / `responseBody` をキャッシュ返却する。

### Property 2: Telemetry 欠損率 0.1% 以下

**Validates: Requirements 6.1**（北極星指標の可視化）/ **Requirements 6.5** PBT-08（テレメトリ整合性）

Lambda DLQ + AsyncStorage 永続キュー + Idempotency 重複検知の 3 段で担保（Q3 反映）。超過時は backlog B-201 で C 移行（SQS 介在型）に切り替える。

### Property 3: VPC 不要 Lambda の VPC 配置禁止

**Validates: Requirements 6.3**（論破ストリーミング初回トークン 3 秒以内のレイテンシ要件）

ENI 新規作成リスク + コールドスタート増を回避（§3.1）。VPC 配置可否は §3.1 の配置マトリクスに従い、Functional Design 段階で決定する。

### Property 4: PII の Telemetry 流入禁止

**Validates: Requirements 6.4** SECURITY-01（PII 暗号化）/ **Requirements 9** NG-7（データ悪用防止）

`properties` への PII 投入を CI の `check-pii-fields.sh` で自動 reject（[api-contracts.md §12.3](../../../../.kiro/steering/api-contracts.md)）。`userId` は Cognito `sub` の SHA-256 ハッシュ化で匿名化済み値のみ送信する。

---

## 1. Mobile 層

### 1.1 M-01 AppShell

#### 責務

- アプリのルートレイアウト、タブナビゲーション（6 画面）
- グローバル状態（TanStack Query / Zustand / Auth context / Telemetry）の Provider 配置
- Deep Link / Universal Link のハンドリング窓口（Amazon 遷移後の復帰、通知タップ、Share Extension 受信）
- Splash 中の Cognito セッション復元
- ネットワークステータス監視（オフライン → AsyncStorage キューでの telemetry 保持）

#### IO 仕様

```typescript
// mobile/src/features/platform/AppShell.tsx
export function AppShell(): JSX.Element {
  // Providers:
  //   QueryClientProvider (TanStack Query, defaultOptions: retry=2, staleTime=60s)
  //   AuthProvider (Cognito JWT 復元 + refresh hook)
  //   TelemetryProvider (M-13 のセッション ID 発行 + flush タイマー)
  //   SafeguardPolicyProvider (S-03 の判定キャッシュ)
  //   NavigationContainer (React Navigation v7)
  // 子ツリー:
  //   <BottomTabs>
  //     <HomeTab>     M-02 HomeScreen          (Unit-2 が実装)
  //     <ReelTab>     M-03 ReelScreen          (Unit-4)
  //     <DebateTab>   M-04 DebateScreen        (Unit-3)
  //     <CartTab>     M-05 CartInterceptScreen (Unit-5)
  //     <ReportTab>   M-06 DameReportScreen    (Unit-8)
  //     <SafeguardTab> M-07 SafeguardScreen    (Unit-7)
  //   </BottomTabs>
}
```

#### 状態 / 遷移

- 起動時: Splash → Cognito セッション復元（トークン有効）→ Home / 失敗 → Login
- バックグラウンド復帰: 30 分以上経過していれば JWT refresh
- Deep Link: `yudane://debate/{sessionId}` / `yudane://cart-attack/{itemId}` を Tab 経由でルーティング
- ネットワーク状態: NetInfo で監視、オフライン → Telemetry を AsyncStorage に堆積、復帰 → flush 起動

#### エラー仕様

| 状態 | 挙動 |
|---|---|
| Cognito refresh 失敗 | Login 画面に強制遷移、Telemetry に `auth.refresh_failed` 記録 |
| Deep Link 不正 | Home に fallback、Telemetry に `deeplink.invalid` 記録 |
| ネットワークオフライン | UI を保持、Telemetry のみ AsyncStorage キューへ |

---

### 1.2 M-12 ApiClient（Q7 = B 反映）

#### 責務

- REST API 呼び出しのラッパー、認証ヘッダ付与、相関 ID 付与
- エラーマッピング（Problem Details → ApiError）
- **GET / DELETE のみ自動リトライ**（最大 3 回、指数バックオフ）
- **POST / PATCH は `Idempotency-Key` ヘッダを呼び出し側が付与した場合のみリトライ可**

#### IO 仕様

```typescript
// mobile/src/features/platform/api-client.ts
type ApiInit = RequestInit & {
  idempotencyKey?: string;   // POST/PATCH のリトライを許可する場合に付与（UUID v7 推奨）
};

export async function apiFetch<T>(path: string, init?: ApiInit): Promise<T>;
export async function apiStream<T>(path: string, init?: ApiInit): AsyncIterable<T>;
// 注: 非ストリーミング = apiFetch、ストリーミング (SSE) = apiStream の 2 種類を型レベルで分離
//     呼び出し側が用途別に適切な API を選択する。stream フラグは責務曖昧化のため不採用。

// 内部仕様:
//   ベース URL: process.env.API_BASE_URL（mobile/.env.development = http://localhost:4010）
//   認証: Authorization: Bearer <Cognito ID Token>（AuthModule から取得）
//   相関 ID: X-Correlation-Id: <ULID>（リクエストごとに新規発行）
//   Idempotency: Idempotency-Key: <UUID v7>（呼び出し側指定時のみ）
//
//   リトライ条件:
//     - GET / DELETE: 自動 3 回、500ms / 1000ms / 2000ms バックオフ
//     - POST / PATCH: idempotencyKey 指定時のみリトライ（Backend が 5 分間の重複検知）
//     - 408 / 429 / 5xx で発動、4xx は即時 throw
```

#### エラーマッピング（Problem Details → ApiError）

| HTTP | ApiError サブクラス | UI 上の扱い |
|---|---|---|
| 400 | ValidationError | フォームエラー表示 |
| 401 | UnauthorizedError | Login 画面へ強制遷移 |
| 403 | ForbiddenError | Toast「権限がないよ」 |
| 404 | NotFoundError | 一覧に戻す |
| 409 | ConflictError | Safeguard クールダウンの場合は専用 UI |
| 429 | RateLimitError | バックオフ後に再試行 |
| 5xx | ServerError | エラー画面 + Telemetry |

---

### 1.3 M-13 Telemetry（Q3 + Q8 反映）

#### 責務

- クライアントイベント計測 → 5 件バッファ → `POST /v1/telemetry`
- オフライン時は AsyncStorage 永続キューに保留
- 起動時 + 5 分タイマーで flush
- Idempotency Key（batch_id = UUID v7）を付与してリトライ安全化

#### IO 仕様

```typescript
// mobile/src/features/platform/telemetry.ts
type TelemetryEvent = {
  eventId: string;        // ULID
  userId: string;         // 匿名化ハッシュ
  sessionId: string;      // 起動セッション
  timestamp: string;      // ISO 8601 UTC
  eventType: string;      // <unit>.<verb>（例: "debate.started"）
  unit: 'platform' | 'auth' | 'debate' | 'reel' | 'cart' | 'calendar' | 'safeguard' | 'report';
  properties: Record<string, unknown>;
  context: { appVersion: string; osVersion: string; locale: string };
};

export function track(eventName: string, props?: Record<string, unknown>): void;
//   バッファに push、5 件溜まれば flush() 呼び出し

export async function flush(): Promise<void>;
//   バッファ → AsyncStorage の永続キューに移動（耐障害性）
//   batchId = UUID v7、Idempotency-Key ヘッダで送信
//   POST /v1/telemetry { events: [...], batch_id }
//   成功時: 永続キューから削除
//   失敗時（408/429/5xx）: 永続キューに残してリトライ（次回 flush で再送）
//   失敗時（4xx）: エラーログ出力、永続キューから破棄（リクエスト不正のため）

// flush タイミング:
//   1. バッファが 5 件溜まった
//   2. 起動時の AppShell mount 時（前回オフライン時の残骸を消化）
//   3. 5 分タイマー（背景でも動作、AppState=active のみ）
//   4. 重要イベント（"auth.signin_completed", "cart.intercept_received" 等）は即座 flush
```

#### 永続キュー仕様

- ストレージ: `@react-native-async-storage/async-storage`
- キー: `telemetry-queue-v1`
- 値: `TelemetryEvent[]`（最大 1000 件、超過時は古い順に破棄）
- シリアライズ: JSON、起動時に deserialize
- バッチサイズ: flush 1 回あたり最大 100 件 / 1MB（API Gateway 制約）

---

### 1.4 認証（Cognito Amplify Auth）

#### 責務

- Cognito User Pool への signUp / signIn / confirmMfa / refresh / signOut
- TOTP MFA セットアップ（Recovery Code は **Cognito 標準仕様にないため、B-01 AuthEdgeLambda で別途実装**。詳細は [sequence-diagrams.md §1.1](./sequence-diagrams.md) と [openapi-skeleton-plan.md §2.1](./openapi-skeleton-plan.md) `/v1/auth/recovery-code` を参照）
- JWT カスタム claim（委ね Lv / 称号 / 月間上限）の取得 → Zustand に保持

#### Q1 反映（dev = 任意 / prd = 強制）

```typescript
// mobile/src/features/platform/auth-config.ts
export const authConfig = {
  Auth: {
    Cognito: {
      userPoolId: process.env.COGNITO_USER_POOL_ID,
      userPoolClientId: process.env.COGNITO_CLIENT_ID,
      mfa: {
        status: process.env.APP_ENV === 'prd' ? 'required' : 'optional',
        totpEnabled: true,
        smsEnabled: false,  // SMS は採用しない（要件書 §7）
      },
    },
  },
};
```

---

## 2. Backend 層

### 2.1 B-12 AuditLogger（共通ライブラリ）

#### 責務

- 構造化 JSON ログ、PII マスキング、相関 ID 伝搬、CloudWatch Logs / X-Ray 統合
- EMF（Embedded Metric Format）でカスタムメトリクス出力

#### IO 仕様

```python
# backend/src/common/audit_logger.py
def log(level: Literal["info", "warn", "error"], message: str, context: dict) -> None: ...
# 構造化 JSON: { timestamp, level, message, correlationId, userId(masked), unit, ...context }
# PII マスキング: email, phone, address は SHA-256 ハッシュ化

def metric(name: str, value: float, unit: str, dimensions: dict) -> None: ...
# EMF 形式で CloudWatch Metrics に直接出力

def trace(segment_name: str) -> ContextManager: ...
# X-Ray セグメント作成（with 文で使用）
# 注: I-2 = C 確定（X-Ray 等は backlog B-001 で見送り中）
#     現状では関数を提供するが内部は no-op、将来 X-Ray 有効化で実装差し替え
```

#### Q5 反映 — VPC 配置の有無

- B-12 はライブラリのため Lambda 単位の VPC 配置に依存
- 各 Lambda の VPC 配置方針は §3 Infrastructure 配置マトリクス を参照

---

### 2.2 B-14 TelemetryIngestionService（Q3 + Q5 反映）

#### 責務

- `POST /v1/telemetry` の受信
- Idempotency Key で重複検知（ElastiCache 1h TTL）
- Kinesis Data Firehose に PutRecordBatch 投入
- **EMF メトリクスは B-12 AuditLogger.metric() に分離**（m9 修正、2026-05-27）。B-14 自身は Firehose 投入のみで責務を限定し、CloudWatch Metrics 出力は B-12 経由とする

#### IO 仕様

```python
# backend/src/telemetry/handler.py
def lambda_handler(event: APIGatewayProxyEvent, context: LambdaContext) -> APIGatewayProxyResponse:
    body = parse_body(event, schema=TelemetryRequest)  # Pydantic 検証
    batch_id = event.headers.get("Idempotency-Key")  # UUID v7

    # 重複検知（Q3 安全装置 1）
    if redis.set(f"telemetry-batch:{batch_id}", "1", ex=3600, nx=True) is None:
        return Response(200, {"status": "duplicate", "batch_id": batch_id})

    # Firehose 同期投入
    firehose.put_record_batch(
        DeliveryStreamName="yudane-telemetry-stream",
        Records=[{"Data": json.dumps(e).encode()} for e in body.events],
    )
    return Response(200, {"status": "accepted", "count": len(body.events)})
# 失敗時は Lambda DLQ（SQS）に自動退避（Q3 安全装置 2）
```

#### VPC 配置

- B-14 は Redis 重複検知のため **VPC 内配置**
- Firehose は Interface VPC Endpoint（PrivateLink）経由で投入

#### DLQ 設定（Q3 安全装置 2）

```typescript
// infra/lib/platform-stack.ts
const telemetryDlq = new sqs.Queue(this, 'TelemetryDlq', {
  retentionPeriod: Duration.days(14),
});
new lambda.Function(this, 'TelemetryIngestion', {
  // ...
  deadLetterQueue: telemetryDlq,
  deadLetterQueueEnabled: true,
});
```

---

### 2.3 認証 Cognito User Pool（Q1 反映）

#### Pool 設定

| 項目 | dev | prd |
|---|---|---|
| MFA Configuration | OPTIONAL | ON |
| TOTP MFA | 有効 | 有効 |
| SMS MFA | 無効 | 無効（採用しない） |
| Password Policy | 8 文字以上、英数字 | 12 文字以上、英大小数字記号 |
| Self Sign-up | 有効 | 有効 |
| Account Recovery | Email | Email |
| User Pool Domain | `yudane-dev.auth.ap-northeast-1.amazoncognito.com` | `yudane-prd.auth.ap-northeast-1.amazoncognito.com` |

#### B-01 AuthEdgeLambda（Cognito Trigger）

```python
def on_post_confirmation(event: CognitoPostConfirmationEvent) -> None:
    # User / PreferenceVector / SafeguardState を初期化
    # 詳細は Unit-2 Auth & Profile で実装、本 Unit ではトリガー登録のみ

def on_pre_token_generation(event: CognitoPreTokenGenerationEvent) -> dict:
    # 委ね Lv / 称号 / 月間上限を JWT カスタム claim に付与
    # 詳細は Unit-2 で実装
```

---

## 3. Infrastructure 配置マトリクス（Q5 反映）

### 3.1 Lambda VPC 配置一覧

| Lambda | VPC 配置 | 理由 |
|---|---|---|
| B-01 AuthEdgeLambda | **VPC 外** | Cognito Trigger、ネットワーク不要 |
| B-02 DebateLlmService | **VPC 外** | DDB 化により Redis 不要、SnapStart 適用 |
| B-03 ReelRecommendationService | VPC 内 | OpenSearch Serverless へのアクセス（VPC エンドポイント経由が望ましい） |
| B-04 CartIntakeHandler | **VPC 外** | DDB / Creators API 経由のみ |
| B-05 CartAttackScheduler | **VPC 外** | EventBridge Scheduler + DDB のみ |
| B-06 NotificationDispatcher | **VPC 外** | End User Messaging Push API のみ |
| B-07 CalendarPredictionService | **VPC 外** | Bedrock + DDB のみ |
| B-08 PreferenceVectorUpdater | **VPC 外** | DDB バッチ集計のみ |
| B-09 SafeguardRulesEngine | **VPC 外** | Q5 セルフレビュー後修正：Lambda Authorizer 内で SafeguardPolicy（S-03、Shared 層判定関数）を直接実行 + DynamoDB `SafeguardStates` / `DebateRateLimits` を直接参照、Redis 依存を排除 |
| B-10 AssociatesLinkGenerator | **VPC 外** | URL 生成のみ |
| B-11 CreatorsApiClient | VPC 内 | Redis 6h キャッシュ |
| B-13 AmazonTransitionRecorder | **VPC 外** | DDB のみ |
| B-14 TelemetryIngestionService | VPC 内 | Redis Idempotency 検知 + Firehose VPC Endpoint |

VPC 内 Lambda（3 つ）は Hyperplane ENI 共有、コールドスタート増分は 100-200ms。

**Q5 セルフレビュー後の修正（2026-05-27）**: 当初設計では B-09 SafeguardRulesEngine を VPC 内に配置していたが、論破ストリーミングの Lambda Authorizer が B-09 を呼び出すため、Q5 で B-02 を VPC 外に出した利益（コールドスタート最小化）が部分的に相殺される矛盾を検出。修正後は B-09 も VPC 外配置とし、Safeguard 判定は以下の二択で実装する:

1. **Lambda Authorizer 内に S-03 SafeguardPolicy（Shared 層、判定関数）を直接 import** して実行（Redis 介在ゼロ）
2. **DynamoDB `SafeguardStates` / `DebateRateLimits` テーブルを Lambda Authorizer から直接参照**（Redis 介在ゼロ）

これにより VPC 内 Lambda は B-03 / B-11 / B-14 の 3 つに限定され、論破ストリーミング系全体（API Gateway → Lambda Authorizer → B-02）が VPC 外で完結する。

### 3.2 B-02 DebateLlmService の SnapStart 設定

```typescript
// infra/lib/debate-stack.ts（Unit-3 で実装、本 Unit では設定方針のみ）
const debateLambda = new lambda.Function(this, 'DebateLambda', {
  runtime: lambda.Runtime.PYTHON_3_13,
  architecture: lambda.Architecture.ARM_64,  // 20% コスト削減
  memorySize: 1024,
  timeout: Duration.seconds(120),
  snapStart: lambda.SnapStartConf.ON_PUBLISHED_VERSIONS,
  // ...
});

// バージョン公開 + Alias 必須（SnapStart 制約）
const liveAlias = new lambda.Alias(this, 'DebateLive', {
  aliasName: 'live',
  version: debateLambda.currentVersion,
});

// API Gateway 統合は Alias を指す
api.addMethod('POST', new apigw.LambdaIntegration(liveAlias), { ... });
```

---

## 4. API Gateway Authorizer（Q2 = C ハイブリッド反映）

### 4.1 Authorizer 配置

| エンドポイント | Authorizer | 理由 |
|---|---|---|
| `POST /v1/auth/*` | なし（公開） | サインアップ / サインイン |
| `GET/PATCH /v1/users/{userId}` | Cognito Authorizer | JWT 検証のみ |
| `GET /v1/users/{userId}/preference` | Cognito Authorizer | JWT 検証のみ |
| `POST /v1/telemetry` | Cognito Authorizer | JWT 検証のみ（高頻度、軽量に） |
| `POST /v1/debate-sessions` | **Lambda Authorizer**（Safeguard 統合） | クールダウン判定 + JWT 検証 |
| `POST /v1/debate-sessions/{id}/agree` | **Lambda Authorizer** | Safeguard 月間上限 + JWT 検証 |
| `POST /v1/cart-watch-items` | Cognito Authorizer | 登録は Safeguard 不要 |
| `POST /v1/amazon-transitions` | **Lambda Authorizer** | 月間上限 + クールダウン |
| `GET /v1/reel` | Cognito Authorizer | 表示は Safeguard 不要 |
| `GET /v1/reports/*` | Cognito Authorizer | 集計データの表示 |

### 4.2 Lambda Authorizer 仕様

```python
# backend/src/safeguard/authorizer.py（Unit-7 Safeguard で実装、本 Unit では枠組みのみ）
from yudane_safeguard_policy import evaluate_monthly_limit, evaluate_cooldown  # Shared 層 S-03

def lambda_handler(event: APIGatewayAuthorizerEvent, context: LambdaContext) -> AuthorizerResponse:
    # 1. JWT 検証（Cognito JWKS 経由）
    claims = verify_jwt(event["authorizationToken"])
    user_id = claims["sub"]

    # 2. Safeguard 判定（Q5 セルフレビュー後修正：S-03 SafeguardPolicy を直接実行、B-09 RPC 不使用）
    action = infer_action(event["methodArn"])  # debate-start / amazon-transition

    # DynamoDB から状態取得（Redis 介在ゼロ）
    safeguard_state = safeguard_states_table.get_item(
        Key={"PK": f"USER#{user_id}", "SK": f"SAFEGUARD#{current_month()}"}
    ).get("Item", default_state())

    if action == "amazon-transition":
        decision = evaluate_monthly_limit(
            user_id, safeguard_state["spent"], safeguard_state["limit"]
        )
    elif action == "debate-start":
        rate_limit = debate_rate_limits_table.get_item(
            Key={"PK": f"USER#{user_id}", "SK": f"DEBATE_RATE#{current_hour()}"}
        ).get("Item", {"consecutiveRefuses": 0})
        decision = evaluate_cooldown(
            rate_limit["consecutiveRefuses"], safeguard_state.get("lastRefuseAt")
        )

    # 3. allow / deny / warn を IAM ポリシーに変換
    if decision == "allow":
        return generate_policy("Allow", event["methodArn"], context={"safeguard": "ok"})
    elif decision == "block":
        raise UnauthorizedException("Safeguard: monthly limit reached")
    elif decision == "warn":
        return generate_policy("Allow", event["methodArn"], context={"safeguard": "warn"})

# キャッシュ: Authorizer Result Cache TTL = 300 秒（5 分）
# レスポンス時間目標: P95 < 50ms（VPC 外配置 + DynamoDB 直接参照で達成、B-09 RPC 不要）
```

#### Q5 セルフレビュー後修正の意図

- 当初設計（B-09 RPC 呼び出し）→ Lambda Authorizer から B-09 への内部 Lambda invocation でコールドスタート + ENI 経由の往復が発生
- 修正後（S-03 直接実行 + DDB 直接参照）→ Lambda Authorizer 単体で完結、論破ストリーミング系全体が VPC 外で完結
- B-09 Lambda 自体は Unit-7 Safeguard で **管理 UI / バッチ処理 / 監査ログ** 専用に責務縮小（Lambda Authorizer の重複実装にならないよう、S-03 / DDB アクセスは S-03 ライブラリに集約）

---

## 5. モノレポ構造（Q4 = npm workspaces）

### 5.1 root package.json

```json
{
  "name": "yudane",
  "private": true,
  "workspaces": [
    "mobile",
    "infra",
    "shared/*"
  ],
  "scripts": {
    "lint": "npm run lint --workspaces",
    "test": "npm run test --workspaces --if-present",
    "schema:gen:ts": "openapi-typescript shared/schema/openapi.yaml -o shared/schema/types/api.ts",
    "mock:api": "prism mock shared/schema/openapi.yaml --port 4010"
  }
}
```

### 5.2 ディレクトリ構造

```
yudane/
├── package.json              # workspaces 定義
├── package-lock.json         # 単一 lockfile
├── tsconfig.base.json        # 共通 TS 設定
├── mobile/                   # workspace
│   ├── package.json          # name: @yudane/mobile
│   └── src/features/platform/
├── infra/                    # workspace
│   ├── package.json          # name: @yudane/infra
│   └── lib/platform-stack.ts
├── backend/                  # Poetry プロジェクト（npm workspace 外）
│   ├── pyproject.toml
│   └── src/{auth,telemetry,common}/
└── shared/
    ├── schema/               # workspace, name: @yudane/schema
    │   ├── package.json
    │   ├── openapi.yaml
    │   └── types/api.ts
    ├── asin-extractor/       # workspace, name: @yudane/asin-extractor
    │   ├── package.json
    │   └── src/index.ts
    ├── safeguard-policy/     # workspace, name: @yudane/safeguard-policy
    │   ├── package.json
    │   └── src/index.ts
    └── telemetry-contracts/  # workspace, name: @yudane/telemetry-contracts
        ├── package.json
        └── src/index.ts
```

### 5.3 Python 側の Shared 参照

```toml
# backend/pyproject.toml
[tool.poetry.dependencies]
python = "^3.13"
yudane-asin-extractor = { path = "../shared/asin-extractor", develop = true }
yudane-safeguard-policy = { path = "../shared/safeguard-policy", develop = true }
yudane-telemetry-contracts = { path = "../shared/telemetry-contracts", develop = true }
```

---

## 6. Shared 層

### 6.1 S-01 AsinExtractor

```typescript
// shared/asin-extractor/src/index.ts
const ASIN_PATTERN = /\/(?:dp|gp\/product|exec\/obidos\/asin)\/([A-Z0-9]{10})/i;

export function extractAsin(url: string): string | null {
  const m = url.match(ASIN_PATTERN);
  return m ? m[1].toUpperCase() : null;
}
```

```python
# shared/asin-extractor/python/asin_extractor/__init__.py
import re
ASIN_PATTERN = re.compile(r'/(?:dp|gp/product|exec/obidos/asin)/([A-Z0-9]{10})', re.IGNORECASE)

def extract_asin(url: str) -> str | None:
    m = ASIN_PATTERN.search(url)
    return m.group(1).upper() if m else None
```

### 6.2 S-02 SchemaRegistry

`shared/schema/openapi.yaml` を SSOT として、TypeScript / Python 型を自動生成。詳細は [openapi-skeleton-plan.md](./openapi-skeleton-plan.md) を参照。

### 6.3 S-03 SafeguardPolicy

```typescript
// shared/safeguard-policy/src/index.ts
export const SAFEGUARD_LIMITS = {
  monthlySpending: { default: 50000, min: 10000, max: 200000 },     // 円
  cooldownAfterRefuse: 3,                                            // 連続拒否で発動
  cooldownDurationMinutes: 180,                                      // 3 時間
  quietWeekDays: 7,                                                  // 静かな週
  debtThresholdRatio: 0.3,                                           // 月収の 30%
} as const;

export function evaluateMonthlyLimit(
  userId: string,
  currentSpending: number,
  limit: number,
): "allow" | "warn" | "block";

export function evaluateCooldown(
  recentRefuseCount: number,
  lastRefuseAt: Date,
): "allow" | "block";
```

Python 側も同等の判定関数を提供（`shared/safeguard-policy/python/`）。

### 6.4 S-04 TelemetryContracts

[api-contracts.md §12](../../../../.kiro/steering/api-contracts.md#12-クライアントテレメトリスキーマ-i-1--a-確定) に確定済みの Telemetry イベント型を `shared/telemetry-contracts/src/index.ts` に定義。Event Type 命名規約 `<unit>.<verb>` を enum で固定。

---

## 7. CI/CD（Q10 = A 反映）

### 7.1 Unit-1 で完成するワークフロー

| ファイル | トリガー | ジョブ |
|---|---|---|
| `.github/workflows/ci.yml` | pull_request, push to develop | lint-mobile / lint-backend / lint-infra / test-mobile / test-backend / test-contract / sbom |
| `.github/workflows/deploy-dev.yml` | push to develop | cdk-deploy-platform-dev（manual approval） |

### 7.2 Unit-1 で対象外（決勝前 6/15 以降に追加）

- `.github/workflows/deploy-prd.yml`
- 各 Unit Stack の deploy ジョブ追加（Unit-2 以降の Functional Design で順次追加）

詳細は [dev-commands.md §5](../../../../.kiro/steering/dev-commands.md) を参照。

---

## 8. ハッカソン書類審査・予選評価軸へのインパクト

| 評価軸 | 本ドキュメントの貢献 |
|---|---|
| ビジネス意図の明確さ | （直接貢献なし、基盤 Unit のため） |
| Unit 分解の適切さ | **強化**: Unit-1 が他全 Unit のインターフェースを技術仕様レベルで定義、依存関係が具体化 |
| 創造性とテーマ適合性 | （直接貢献なし） |
| ドキュメント品質 | **強化**: Q1〜Q10 の確定が IO / 状態 / エラー / VPC 配置 / DDB スキーマ / Authorizer 配置の各レイヤに展開された |
| AI-DLC プロセス（予選評価軸） | **強化**: Per-Unit Loop の Functional Design Part 2 を正規手順で実施、後続 Unit のテンプレートになる |
