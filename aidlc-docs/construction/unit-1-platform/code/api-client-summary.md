# Unit-1 Platform — Code Summary: M-12 ApiClient（Step 12-13）

## 生成ファイル

| ファイル | 役割 |
|---|---|
| `mobile/src/features/platform/api-client/types.ts` | RequestPolicy / TimeoutPolicy / 既定値・リトライ定数 |
| `mobile/src/features/platform/api-client/retry-policy.ts` | shouldRetry / backoffDelayMs（純関数、PBT 対象） |
| `mobile/src/features/platform/api-client/domain-error.ts` | DomainError + ProblemDetails マッピング（ALG-MAP） |
| `mobile/src/features/platform/api-client/api-client.ts` | ApiClient 本体（interceptor チェーン、LC-01） |
| `mobile/src/features/platform/api-client/index.ts` | export 制御 |
| `*.test.ts`（retry-policy / api-client） | PBT + モック fetch テスト |

## ルール準拠
- REQ-01〜05（相関 ID 付与・不変、JWT、sub 検証は Backend）
- RETRY-01〜06（GET のみ / 429・503・断 / 指数バックオフ / 401 single-shot refresh / 再リフレッシュなし）
- PAT-PERF-01（REST/SSE 2 系統タイムアウト）/ ALG-MAP（Problem→DomainError）
- NFR-COV-04（目標 85%）/ PBT（リトライ上限 invariant、非冪等は必ず false）

## 次ステップ
Step 14-15: M-13 Telemetry + PBT
