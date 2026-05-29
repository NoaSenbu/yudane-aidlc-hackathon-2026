# Unit-2 — Code Summary: auth-stack（Step 13-14）

## 生成ファイル
| ファイル | 役割 |
|---|---|
| `infra/lib/auth-stack.ts` | DynamoDB 4 テーブル / B-08 Lambda 2 本 / EventBridge cron 2 本 / SSM 参照 / cdk-nag |
| `infra/bin/app.ts` | auth-stack を追加 |
| `infra/test/auth-stack.test.ts` | DynamoDB 4 / cron 2 / Python3.13 / prd RETAIN / 週次 SUN |

## ルール準拠
- tech-cdk §3（SSM 参照、Export/Import 不使用）/ §4（命名 auth-<env>-stack）
- Q1=A（4 テーブル PK=userId、PAY_PER_REQUEST/PITR/SSE-KMS）/ Q3=A（cron 2 本）/ Q4=A（prd RETAIN）
- SECURITY-01（KMS）/ SECURITY-06（grantReadWriteData で最小権限）
- cdk-nag AwsSolutionsChecks 適用 + 理由つき Suppression

## 注記
- B-01 Cognito トリガーのアタッチ + auth API Lambda（profile/user/debt）の API Gateway 統合は、platform User Pool 参照 + API ルート結線として実装統合で追加（コードは Step 5-6 で生成済み）
- `cdk deploy` は Build and Test（ユーザー承認必須）

## 次ステップ
Step 15: 総括
