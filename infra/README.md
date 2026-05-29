# infra

YUDANE インフラ（AWS CDK v2 / TypeScript / Node.js 22 LTS）。リージョン: `ap-northeast-1`。

## Unit-1 Platform が提供するもの

- `lib/platform-stack.ts` — VPC / API Gateway / Cognito User Pool / DynamoDB 共通 / S3 / ElastiCache Redis / KMS / IAM / 観測 / B-12 Layer / B-14 / Health
- `bin/app.ts` — CDK アプリエントリ（env=dev|prd を context で切替）

各 Unit は `lib/<unit>-stack.ts` を追加し、platform-stack の出力を SSM Parameter Store 経由で参照する（shared-infrastructure.md）。

## コマンド

```bash
npm install
npx cdk synth
npx cdk diff
npx cdk deploy <stack-name>   # デプロイはユーザー承認必須
```
