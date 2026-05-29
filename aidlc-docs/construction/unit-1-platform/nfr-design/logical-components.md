# Unit-1 Platform — Logical Components

> NFR 設計パターンを実現する **論理コンポーネント** の構成。技術非依存の論理構造（物理インフラは Infrastructure Design で確定）。
> 参照: [nfr-design-patterns.md](./nfr-design-patterns.md) / [Functional Design](../functional-design/) / [components.md](../../../inception/application-design/components.md)
> 確定方針: NFR-Design Q1=A / Q2=A / Q3=A / Q4=A

---

## 0. 論理コンポーネント一覧

| ID | 論理コンポーネント | 物理マッピング先（予定） | 実現パターン |
|---|---|---|---|
| LC-01 | ApiClient Interceptor Chain | M-12（mobile/src/features/platform） | PAT-PERF-01 / RESIL-01/02 / OBS-02 |
| LC-02 | Telemetry Pipeline | M-13 + B-14 | PAT-RESIL-03 / PERF-02 / OBS-01 |
| LC-03 | Audit Logging Facade | B-12（backend/src/common） | PAT-SEC-02 / OBS-01/02 |
| LC-04 | Authorization Layer | API GW Authorizer + require_owner デコレータ | PAT-SEC-01 / SEC-03 |
| LC-05 | Health & Degrade Surface | platform API（GET /v1/health） | PAT-RESIL-04 |
| LC-06 | Shared Contract & Codegen | S-02 SchemaRegistry | API-01〜10 |
| LC-07 | Safeguard Policy Module | S-03（shared/safeguard-policy） | PAT-SEC（gate）/ ALG-SG |
| LC-08 | ASIN Utility | S-01（shared/asin-extractor） | ALG-ASIN |

---

## 1. LC-01 ApiClient Interceptor Chain（M-12）

### 構成
```
apiFetch(path, init: RequestInit & { kind?: 'rest'|'stream', timeout?, retry? })
  └─ Interceptor Chain（順序固定）:
       1. AuthInterceptor      … Authorization: Bearer <token>
       2. CorrelationInterceptor … X-Correlation-Id 付与（生成 or 継承）
       3. TimeoutInterceptor   … RequestPolicy で REST/SSE 別タイムアウト
       4. RetryInterceptor     … GET のみ 指数バックオフ（PAT-RESIL-01）
       5. RefreshInterceptor   … 401 → single-shot refresh（PAT-RESIL-02）
       6. ErrorMapInterceptor  … ProblemDetails → DomainError（ALG-MAP）
```

### 依存
- AuthModule（M-11、Unit-2 提供）からトークン取得 / refresh
- AppShell（M-01）の `onAuthExpired` を呼ぶ
- 出力: `Promise<T>`（REST）/ `AsyncIterable<T>`（SSE）

### 設定可能パラメータ（business-rules §8）
- REST timeout（接続 3s / 全体 10s）、SSE timeout（接続 3s / アイドル 30s）
- リトライ base 300ms / 最大 2 回

---

## 2. LC-02 Telemetry Pipeline（M-13 + B-14）

### 構成
```
[M-13 クライアント]
  track() → InMemoryQueue
     └─ flush trigger（20件 / 30s / background）
          → POST /v1/telemetry（LC-01 経由）
          → 失敗時 → AsyncStorageOverflowQueue（上限 500、古い順破棄）
[B-14 サーバー]
  ingest_events()
     ├─ sub↔user_id 照合（LC-04）
     ├─ name を S-04 カタログ照合（未知は drop + warn）
     ├─ EMF put（LC-03 metric Facade 経由）
     └─ S3 Data Lake 非同期書き込み（Parquet）
```

### 信頼性（PAT-RESIL-03、Q3=A）
- At-least-once。重複は EMF idempotent 集計で吸収
- MVP ではサーバー専用キュー（SQS）なし。API 同期受信

---

## 3. LC-03 Audit Logging Facade（B-12）

### 構成
```
B-12 AuditLogger（Lambda Powertools ラッパー）
  ├─ log(level, message, context)
  │     └─ sanitize(record)  ← Allowlist Sanitizer（PAT-SEC-02）
  │            classify(key): allowed / pii / unclassified
  │            mask: passthrough / partial-email / full-mask（unclassified も full-mask）
  ├─ metric(name, value, unit, dimensions)  ← Metric Facade（EMF, PAT-OBS-01）
  └─ trace(segment_name)  ← X-Ray セグメント（correlation 付与）
```

### 入力分類の出所
- allowlist / pii リスト: S-04 TelemetryContracts
- OpenAPI `x-pii: true` 宣言フィールド
- CI: check-pii-fields.sh（拡張）が未分類を検出して fail

---

## 4. LC-04 Authorization Layer（API GW + デコレータ）

### 構成
```
[API Gateway]
  └─ Lambda Authorizer（JWT 検証、認証一元化）
       └─ 各業務 Lambda
            └─ @require_owner デコレータ（共通）
                 ├─ JWT sub と path {userId} 照合（IDOR 対策、PAT-SEC-01）
                 ├─ 不一致 → 403 auth.idor（fail-closed）
                 └─ 通過 → 各 Unit の業務オーナー判定へ
```

### 責務分界
- Unit-1: Authorizer 設定 + `require_owner` デコレータ（共通土台）
- 各 Unit: リソース固有の業務オーナー判定（例: セッション参照権限）

---

## 5. LC-05 Health & Degrade Surface（Q6=B）

### 構成
```
GET /v1/health
  └─ shallow check: DynamoDB ping / Redis ping / 自身の起動状態
       → 200（healthy）/ 503（degraded）
```
- **Q6=B**: サーキットブレーカ・自動フォールバックは持たない
- 各 Unit は自身の縮退（静的推薦カタログ等）を TanStack Query エラーハンドリングで実装

---

## 6. LC-06 Shared Contract & Codegen（S-02）

### 構成
```
shared/schema/
  openapi.yaml（エントリ）→ paths/ + components/ + examples/（物理分割、api-contracts §10）
  ├─ codegen:ts  → openapi-typescript → types/api.ts（手動編集禁止）
  ├─ codegen:py  → datamodel-code-generator → backend/src/common/models/api.py
  ├─ mock        → Prism（localhost:4010、並行開発）
  └─ contract    → Schemathesis（Backend）/ MSW（Mobile）
```
- 第1版凍結範囲（Q1=refinedA）: 全 UC パス骨格 + 共通コンポーネント + 必須フィールド最小セット
- 実装者は省略可能フィールドを非破壊で追記

---

## 7. LC-07 Safeguard Policy Module（S-03）

### 構成
```
shared/safeguard-policy/
  ├─ constants（DEFAULT/DEBT ratio, cooldown, attack steps, WARN 0.8）
  └─ decideAllow(input) → SafeguardDecision（純関数、ALG-SG）
       Mobile（M-07 等）と Backend（B-09）が同一実装を import
```
- gate パターンで全 Amazon 遷移前に評価（FR-FUNNEL-05）
- PBT: invariant（remaining>=0、実効上限<=上限）+ idempotency

---

## 8. LC-08 ASIN Utility（S-01）

### 構成
```
shared/asin-extractor/
  ├─ extractAsin(url) → AsinResult（ALG-ASIN）
  └─ isValidAsin(asin) → boolean
  TS / Python 両実装、golden fixtures でクロス言語一致検証
```

---

## 9. 論理コンポーネント配置（モノレポ）

```
mobile/src/features/platform/    … LC-01（ApiClient）/ LC-02 クライアント側（Telemetry）/ M-01 AppShell
backend/src/common/              … LC-03（AuditLogger）/ LC-04 デコレータ / 共通モデル
backend/src/telemetry/           … LC-02 サーバー側（B-14）
shared/schema/                   … LC-06（SchemaRegistry）
shared/safeguard-policy/         … LC-07（SafeguardPolicy）
shared/asin-extractor/           … LC-08（AsinExtractor）
shared/telemetry-contracts/      … S-04（allowlist / メトリクスカタログ雛形）
infra/lib/platform-stack.ts      … LC-04 Authorizer / LC-05 Health（物理は Infra Design）
```

---

## 10. 未確定（Infrastructure Design で物理化）

| 論理コンポーネント | 物理化で決めること |
|---|---|
| LC-04 Authorizer | Lambda Authorizer の具体構成 / キャッシュ TTL |
| LC-05 Health | ヘルスチェックの実体（Lambda / Route） |
| LC-02 S3 Data Lake | バケット / Parquet パーティション設計 |
| 全般 | VPC / IAM ポリシー / Lambda メモリ・タイムアウト・同時実行 |
