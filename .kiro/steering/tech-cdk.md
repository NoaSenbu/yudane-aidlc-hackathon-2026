---
inclusion: fileMatch
fileMatchPattern: 'infra/**'
---

# AWS CDK (TypeScript, v2) 規則

> `infra/**` 配下のファイルを編集しているときに自動で適用される steering。
> TypeScript 共通規則は [tech-typescript.md](./tech-typescript.md)、横断規則は [AGENTS.md](./AGENTS.md) を参照。

---

## 1. 採用技術

- **AWS CDK v2 系最新**（TypeScript）
- **Node.js 22 LTS**
- **cdk-nag**（`AwsSolutionsChecks` rule pack）
- リージョン: `ap-northeast-1`

## 2. Lint・品質

| 項目 | 採用 | 備考 |
|---|---|---|
| cdk-nag | `AwsSolutionsChecks` rule pack | 予選前は `aws-solutions-iam4` / `aws-solutions-l1` 等の本番相当ルールまで全適用 |
| ESLint | TypeScript 側と同じ設定を継承 | [tech-typescript.md](./tech-typescript.md) §1 参照 |
| Suppression | `NagSuppressions.addResourceSuppressions()` + 理由コメント必須 | 無言サプレッション禁止 |

## 3. 推奨パターン

- Stack 間の依存は **CloudFormation Export/Import を避け**、CDK プロパティ参照または SSM Parameter Store 経由で連携
- L1 Construct（`Cfn*`）直接使用は最後の手段。L2 / L3 Construct を優先
- `removalPolicy` は dev = `DESTROY`、prd = `RETAIN` を明示

## 4. CDK 固有命名

| 対象 | 規則 | 例 |
|---|---|---|
| Stack | `<unit>-<env>-stack` | `debate-dev-stack`、`platform-prd-stack` |
| Construct | PascalCase | `DebateLambdaConstruct` |
| Logical ID | 意味ある PascalCase | `DebateStreamingLambda` |
| Resource Name（Cognito User Pool 等） | `yudane-<unit>-<env>-<resource>` | `yudane-auth-dev-userpool` |
| SSM Parameter | `/yudane/<env>/<unit>/<key>` | `/yudane/dev/debate/bedrock-model-id` |

## 5. Unit 対応

| Unit | Stack 名 |
|---|---|
| Unit-1 Platform | `platform-stack` |
| Unit-2 Auth & Profile | `auth-stack` |
| Unit-3 Debate | `debate-stack` |
| Unit-4 Reel | `reel-stack` |
| Unit-5 Cart Intercept | `cart-stack` |
| Unit-6 Calendar | `calendar-stack` |
| Unit-7 Safeguard | `safeguard-stack` |
| Unit-8 Dame Report | `report-stack` |

依存順序の詳細は [structure.md](./structure.md) §Unit 構成 を参照。

## 6. テスト（CDK 側）

| レイヤ | ツール | 配置 |
|---|---|---|
| Snapshot Test | `jest`（CDK snapshot） | `infra/test/**/*.test.ts` |
| cdk-nag 検証 | CI で `cdk synth` 時に自動検査 | — |

Snapshot の破壊的変更は PR description で必ず差分を説明。

## 7. セキュリティ（SECURITY Extension 抜粋）

- IAM ポリシーは最小権限の原則。`*` resource / action の付与は理由コメント必須
- S3 バケットは SSE-KMS 暗号化を標準（cdk-nag で検査）
- Cognito User Pool は CDK で直接管理（Amplify CLI は不採用）
- 認証情報を `cdk.context.json` / `cdk.json` に直書き禁止。Secrets Manager / SSM Parameter Store から参照

## 8. 採用しないもの

- AWS Amplify CLI（CDK で直接管理）
- Step Functions（時間差制御は EventBridge Scheduler 単独）

## 9. よく使うコマンド

```bash
npm install
npx cdk synth
npx cdk diff
npx cdk deploy <stack-name>   # デプロイはユーザー承認必須
```

詳細は [dev-commands.md](./dev-commands.md)（manual steering、[AGENTS.md](./AGENTS.md) §10 の条件で AI が自発的に readFile する）を参照。

## 10. 破壊的操作（事前承認必須）

- `cdk destroy`（本番相当環境）
- IAM ロール / ポリシーの削除
- DynamoDB テーブル / S3 バケット（データを含む）の削除
- KMS キーの削除（grace period 設定後でも要承認）
