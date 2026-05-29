# Unit-1 Platform — Code Summary: platform-stack（Step 18-19）

## 生成ファイル

| ファイル | 役割 |
|---|---|
| `infra/package.json` / `cdk.json` / `tsconfig.json` | CDK プロジェクト設定 |
| `infra/bin/app.ts` | アプリエントリ（env context 切替 + cdk-nag 適用） |
| `infra/lib/platform-stack.ts` | VPC / Cognito / KMS / S3 / Redis / SNS / SSM 出力 |
| `infra/test/platform-stack.test.ts` | vitest スナップショット/アサート + cdk-nag |

## ルール準拠
- tech-cdk §3（Export/Import を避け SSM 出力）/ §4（命名 `<unit>-<env>-stack`）/ §7（KMS / IAM 最小権限 / Cognito CDK 管理）
- SECURITY-01（KMS）/ SECURITY-07（VPC + Endpoint）/ SECURITY-09（S3 パブリック遮断）/ SECURITY-12 土台（MFA REQUIRED）/ SECURITY-14（SNS アラート）
- Q1=A（2AZ/3層+Endpoint+NAT1）/ Q6=A（dev DESTROY / prd RETAIN）/ Q7=A（Redis は platform 配置）
- cdk-nag: AwsSolutionsChecks 適用、Suppression に理由コメント（IAM4 / COG2）

## 注記
- OpenSearch Serverless は Unit-4 着手時に追加（本 Unit では Redis まで、Q7=A）
- API Gateway + Lambda Authorizer の詳細結線、B-12 Layer / B-14 / Health の Lambda 定義は実装統合（OpenAPI 連携）で確定。本ステップで VPC / 認証基盤 / データ基盤 / 観測 / SSM 出力を確立
- `cdk deploy` は Build and Test ステージ（ユーザー承認必須）

## 次ステップ
Step 20: README / CI / MSW / 総括
