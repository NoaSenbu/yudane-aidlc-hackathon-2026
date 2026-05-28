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

### 3.1 Lambda SnapStart 適用ルール（Unit-1 Q5 確定）

レイテンシクリティカルな Lambda（特に Bedrock ストリーミング系の B-02 DebateLlmService）には SnapStart を適用してコールドスタートを短縮する。Python 3.13 / .NET は追加料金なし、Java はキャッシュ料金あり。

```typescript
const fn = new lambda.Function(this, 'DebateLambda', {
  runtime: lambda.Runtime.PYTHON_3_13,
  architecture: lambda.Architecture.ARM_64,  // 20% コスト削減
  snapStart: lambda.SnapStartConf.ON_PUBLISHED_VERSIONS,
  // ...
});

// SnapStart は公開バージョン + Alias が必須
const liveAlias = new lambda.Alias(this, 'DebateLive', {
  aliasName: 'live',
  version: fn.currentVersion,
});

// API Gateway 統合は Alias を指す
api.root.addResource('debate-sessions').addMethod(
  'POST',
  new apigw.LambdaIntegration(liveAlias),
);
```

**SnapStart 適用時の制約**:

- `$LATEST` 版では SnapStart 効果なし、必ず公開バージョン + Alias で運用
- ハンドラ外でランダム値 / UUID 生成 / DB コネクション初期化等を行う場合は `@register_after_restore`（Python）/ `Core.beforeCheckpoint` Hook（Java）で snapshot 復元後に再生成
- VPC 内 / VPC 外いずれでも適用可能（VPC 外配置 + SnapStart の組み合わせで効果最大化）

**適用対象 Lambda（YUDANE）**:

- B-02 DebateLlmService（必須、Q5 確定）
- B-03 ReelRecommendationService（要検討、初回トークン要件次第）
- 他 Lambda は SnapStart 不要（バックグラウンドジョブ等）

## 4. CDK 固有命名

| 対象 | 規則 | 例 |
|---|---|---|
| Stack（共有結合 dev / prd） | `<unit>-<env>-stack` | `debate-dev-stack`、`platform-prd-stack` |
| Stack（個人 sandbox dev） | `<unit>-dev-<initial>-stack` | `debate-dev-b-stack`（Member B の個人 dev） |
| Construct | PascalCase | `DebateLambdaConstruct` |
| Logical ID | 意味ある PascalCase | `DebateStreamingLambda` |
| Resource Name（Cognito User Pool 等） | `yudane-<unit>-<env>-<resource>` | `yudane-auth-dev-userpool` |
| SSM Parameter | `/yudane/<env>/<unit>/<key>` | `/yudane/dev/debate/bedrock-model-id` |

### 4.1 環境構成（C-4 = C 確定: 単一アカウント + suffix）

- **AWS アカウント**: 単一アカウント運用。Member A が Builder ID で取得・管理（ハッカソン参加要件）
- **環境分離**: env = `dev`（共有結合用）+ `prd`（決勝向け）の 2 環境
- **個人 sandbox**: 個人別の作業衝突は CDK Context の `developer` キー + Stack 名 suffix で回避
  - 個人 sandbox: `<unit>-dev-<initial>-stack`（例: `platform-dev-a-stack`、`debate-dev-b-stack`）
  - 共有結合 dev: `<unit>-dev-stack`（Member A が管理、`cdk deploy` は事前承認必須）
  - 決勝 prd: `<unit>-prd-stack`（Member A のみ実行可、本番相当の cdk-nag を全適用）
- **CDK Context 注入例**: `cdk.context.json` または環境変数 `CDK_DEVELOPER=b` で suffix を渡し、Stack 名末尾に注入する
- **リージョン**: `ap-northeast-1` 固定（要件書 §7）
- **採用しないもの**: 個人別 AWS アカウント / Control Tower（[parallel-dev-prerequisites.md C-4](../../aidlc-docs/construction/plans/parallel-dev-prerequisites.md) の選択肢 B）

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
