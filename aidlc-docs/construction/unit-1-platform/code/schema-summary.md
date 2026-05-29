# Unit-1 Platform — Code Summary: Schema / OpenAPI 骨格凍結（Step 2）

> S-02 SchemaRegistry。OpenAPI 3.1 第1版骨格を凍結し型生成（Q1=refinedA）。

## 生成ファイル

| ファイル | 役割 |
|---|---|
| `shared/schema/openapi.yaml` | エントリ。全 UC のパス + 共通コンポーネントを $ref 集約 |
| `shared/schema/components/parameters/common.yaml` | CorrelationId / Cursor / Limit |
| `shared/schema/components/responses/problem-details.yaml` | ProblemDetails / Unauthorized / Forbidden / RateLimited |
| `shared/schema/components/schemas/common.yaml` | ProblemDetails / HealthStatus / Telemetry* / User / CalendarEvent |
| `shared/schema/paths/health.yaml` / `telemetry.yaml` | Unit-1 の具体エンドポイント |
| `shared/schema/paths/{auth,debate,reel,cart,calendar,safeguard,report}.yaml` | 他 Unit のパス骨格（URL + メソッド + 共通レスポンス） |
| `shared/schema/package.json` | 型生成 / bundle / mock / lint スクリプト |
| `shared/schema/types/api.ts` | 生成 TS 型（ヘッダ: Do not edit） |
| `backend/scripts/gen_models.py` | Pydantic モデル生成スクリプト |
| `backend/src/common/models/api.py` | 生成 Pydantic モデル（ヘッダ: Do not edit） |

## 凍結方針（Q1=refinedA）
- 第1版で凍結: 全 UC パス骨格（URL + メソッド）+ 共通コンポーネント + 主要リソース必須フィールド最小セット
- 実装者が後から追記: 担当パスの省略可能フィールド（非破壊、v1 内）
- 破壊的変更は `/v2` + 30 日 deprecation

## セキュリティ・プライバシー
- 全 POST に 429（RateLimited）+ `X-RateLimit-*`（SECURITY-11 / API-09）
- `User.email` に `x-pii: true`（ログ/テレメトリで必ずマスク、PII-03）
- `CalendarEvent` は category / timeRange のみ。title/body/attendees を意図的に除外（FR-CAL-05 / NG-7）。CI の check-pii-fields.sh で追加 PR を reject

## 注記（ネットワーク制約）
型生成（openapi-typescript / datamodel-code-generator）は依存インストールが必要なため、本コミットでは骨格に対応する代表型のスナップショットを配置。CI で実生成し差分検証する（api-contracts.md §3.3）。

## 次ステップ
Step 3-4: S-01 AsinExtractor 実装 + PBT
