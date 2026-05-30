# Unit-5 Cart Intercept — Deployment Architecture

> AI-DLC Construction Phase / Per-Unit Loop / Infrastructure Design ステージ。
> [Plan v3](../../plans/unit-5-cart-intercept-infrastructure-design-plan.md) Q8=A（deploy-dev.yml に cart ジョブ追加）/ Q10=A（CDK Rollback + DDB PITR）反映。
>
> 参照:
> - [infrastructure-design.md](./infrastructure-design.md)（物理マッピング詳細）
> - [Unit-1 functional-design.md §7](../../unit-1-platform/functional-design/functional-design.md)（CI/CD 基盤）
> - [.kiro/steering/git-ops.md](../../../../.kiro/steering/git-ops.md)（ブランチ戦略 / マージ順序）
> - [doc/backlog.md B-504](../../../../doc/backlog.md)（APNs Production Cert 取得）

---

## 1. デプロイ全体図（Mermaid）

```mermaid
graph TB
    subgraph Developer["Developer Workflow"]
        D[Member D Local]
        D -->|push to feature/cart-*| GH[GitHub]
        GH -->|PR review approved by Member A| Merge[Merge to develop]
    end

    subgraph CI["GitHub Actions CI"]
        Merge --> CI1[ci.yml]
        CI1 -->|lint-backend / test-backend| CI2[Quality Gates]
        CI2 -->|test-contract| CI3[Schemathesis OpenAPI 検証]
        CI3 -->|cdk synth + snapshot| CI4[CDK Snapshot Test]
    end

    subgraph DeployDev["dev 環境 自動デプロイ"]
        CI4 --> DD1[deploy-dev.yml]
        DD1 -->|manual approval| DD2[cdk-deploy-platform-dev]
        DD2 -->|完了後| DD3[cdk-deploy-auth-dev]
        DD3 -->|完了後| DD4[cdk-deploy-safeguard-dev]
        DD4 -->|完了後| DD5[<b>cdk-deploy-cart-dev<br/>(本 Unit、Q8=A)</b>]
    end

    subgraph SandboxDeploy["個人 sandbox 手動デプロイ"]
        D -.->|npm run deploy:dev:cart -- --init=d| Sandbox[cart-dev-d-stack]
        D2[Member A/B/C] -.->|sandbox の cart は Mock| MockSandbox[Cart は dev 共有を参照]
    end

    subgraph DeployPrd["prd 環境 手動デプロイ（決勝直前）"]
        DD5 -->|develop → main PR| PrdMerge[Merge to main]
        PrdMerge -->|GitHub Actions manual approval| PD1[deploy-prd.yml]
        PD1 -->|cdk-deploy-platform-prd| PD2
        PD2 -->|cdk-deploy-auth-prd| PD3
        PD3 -->|cdk-deploy-safeguard-prd| PD4
        PD4 -->|<b>cdk-deploy-cart-prd</b>| PD5[CartStack prd]
    end

    subgraph AWS["AWS ap-northeast-1"]
        DD5 --> AWS_DEV[cart-dev-stack]
        Sandbox --> AWS_SAND[cart-dev-d-stack]
        PD5 --> AWS_PRD[cart-prd-stack]
    end

    style D fill:#e1f5ff
    style DD5 fill:#fff4d6
    style PD5 fill:#ffd6d6
```

---

## 2. デプロイ順序（Stack 依存）

[Plan v3 Q1=A](../../plans/unit-5-cart-intercept-infrastructure-design-plan.md) の CDK construct 直接参照に基づく Stack 依存順:

```
1. PlatformStack       (Unit-1 owner: Member A)
   ├─ KMS Key
   ├─ IdempotencyKeys Table
   ├─ Idempotency S3 Bucket
   └─ DebateRateLimits Table

2. AuthStack            (Unit-2 owner: Member A)
   ├─ Cognito User Pool（dev/prd で MFA 設定異）
   ├─ Cognito User Pool Client
   ├─ Users Table
   └─ B-01 AuthEdgeLambda

3. SafeguardStack       (Unit-7 owner: Member C)
   └─ SafeguardStates Table

4. CartStack            (Unit-5 owner: Member D)  ← 本 Unit
   ├─ CartWatchItems Table
   ├─ NotificationLogs Table
   ├─ EUM Application + APNs/FCM Channel
   ├─ 6 Lambda（cart_intake / cart_dismiss / cart_list / push_token / notification_dispatcher / cart_attack_scheduler_retry）
   ├─ EventBridge Scheduler（default Group + cart-* prefix）
   ├─ NotificationDispatcherDlq
   ├─ CartAlertTopic + Slack Bridge Lambda
   └─ CloudWatch Alarms × 5
```

> **注**: Unit-3 Debate / Unit-4 Reel / Unit-6 Calendar / Unit-8 Report は Cart Stack に依存しないが、Unit-3 / Unit-4 は CartWatchItems の SSM Parameter を参照する（読み取り専用）。

---

## 3. CI/CD パイプライン仕様（Q8=A）

### 3.1 既存の `.github/workflows/ci.yml`（Unit-1 で確定済み、本 Unit はジョブ拡張のみ）

```yaml
# Unit-1 で確定済み、本 Unit で変更不要
name: ci
on:
  pull_request:
    branches: [develop, main]
  push:
    branches: [develop]

jobs:
  lint-backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: poetry install
      - run: poetry run ruff check
      - run: poetry run mypy --strict src/

  test-backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: poetry install
      - run: poetry run pytest --cov=src --cov-fail-under=80
      # cart の test もここで自動実行

  cdk-synth:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: cd infra && npm ci
      - run: cd infra && npm run synth -- --all  # 全 Stack を synth、cart-stack も含む
      - run: cd infra && npm run test  # snapshot test、cart-stack snapshot も含む

  test-contract:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: cd shared/schema && npm ci
      - run: cd shared/schema && npm run lint
      - run: cd shared/schema && npm run schemathesis  # cart のエンドポイントも検証
```

### 3.2 `.github/workflows/deploy-dev.yml`（Unit-1 で確定 + 本 Unit でジョブ追加）

```yaml
name: deploy-dev
on:
  push:
    branches: [develop]

jobs:
  cdk-deploy-platform-dev:
    runs-on: ubuntu-latest
    environment:
      name: dev-platform
      # manual approval は Unit-1 確定済み
    steps:
      - uses: actions/checkout@v4
      - uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::ACCOUNT:role/GitHubActionsRole
          aws-region: ap-northeast-1
      - run: cd infra && npm ci
      - run: cd infra && npm run deploy -- platform-dev-stack

  cdk-deploy-auth-dev:
    needs: cdk-deploy-platform-dev
    runs-on: ubuntu-latest
    environment: dev-auth
    steps:
      # ...同様

  cdk-deploy-safeguard-dev:
    needs: cdk-deploy-auth-dev
    runs-on: ubuntu-latest
    environment: dev-safeguard
    steps:
      # ...同様

  # 🆕 本 Unit で追加（Q8=A 反映）
  cdk-deploy-cart-dev:
    needs: cdk-deploy-safeguard-dev
    runs-on: ubuntu-latest
    environment:
      name: dev-cart
      # manual approval は不要（dev 環境の自動デプロイ）
    steps:
      - uses: actions/checkout@v4
      - uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::ACCOUNT:role/GitHubActionsRole
          aws-region: ap-northeast-1
      - run: cd infra && npm ci
      - run: cd infra && npm run deploy -- cart-dev-stack
      - name: Smoke Test
        run: |
          # CartWatchItems Table の存在確認
          aws dynamodb describe-table --table-name yudane-cart-dev-watch-items
          # EUM Application の存在確認
          aws ssm get-parameter --name /yudane/dev/cart/eum-application-id
```

### 3.3 個人 sandbox の手動デプロイ（Q9=A 反映）

```bash
# Member D の作業端末から
cd infra
npm run deploy:dev:cart -- --init=d
# 内部的に:
# cdk deploy cart-dev-d-stack --context developerInitial=d
```

各メンバーが個別 sandbox に Stack 作成可能。共有 dev は GitHub Actions 経由のみで更新（複数人 deploy 衝突回避）。

---

## 4. 環境別差異表

| 項目 | Member D Sandbox | 共有 dev | prd |
|---|---|---|---|
| **Stack 名** | `cart-dev-d-stack` | `cart-dev-stack` | `cart-prd-stack` |
| **デプロイ方法** | `npm run deploy:dev:cart -- --init=d`（手動） | `deploy-dev.yml` 自動（develop push）| `deploy-prd.yml` 手動（main merge + manual approval）|
| **DDB PITR** | 無効 | 無効 | 有効（35 日） |
| **DDB RemovalPolicy** | DESTROY | DESTROY | RETAIN |
| **DDB DeletionProtection** | off | off | on |
| **Lambda SnapStart** | 適用（cart_intake / cart_dismiss / notification_dispatcher の 3 関数） | 同左 | 同左 |
| **Reserved Concurrency** | 共有 100 + 個別 60 | 同左 | 同左 |
| **APNs cert** | Sandbox（Apple Developer 不要） | 同左 | **Production**（B-504 backlog 完了後） |
| **FCM key** | dev | 同左 | prd |
| **EUM Application** | `yudane-cart-dev-d` | `yudane-cart-dev` | `yudane-cart-prd` |
| **SNS Topic** | `yudane-cart-dev-d-alerts` | `yudane-cart-dev-alerts` | `yudane-cart-prd-alerts` |
| **Slack Webhook** | dev Slack Webhook（共通）| 同左 | prd Slack Webhook |
| **Slack 通知先 channel** | `#yudane-dev` | `#yudane-dev` | `#yudane-emergency` |
| **CloudWatch Alarms** | 5 系統すべて有効 | 同左 | 同左 |
| **コスト試算** | 約 $1.5-4/月 / 個人 | 約 $3/月 | 約 $3/月（MVP）→ 約 $20-25/月（本番化） |

---

## 5. ロールバック / 災害復旧手順（Q10=A）

### 5.1 CDK Rollback（CFN 自動）

```bash
# デプロイ失敗時、CFN は自動的に直前 version へ rollback
# 明示的にロールバックする場合:
aws cloudformation rollback-stack --stack-name cart-prd-stack
```

### 5.2 Lambda Function バージョンの巻き戻し

```bash
# SnapStart 適用 3 関数の Alias を直前 version に戻す
aws lambda update-alias \
  --function-name yudane-cart-prd-intake \
  --name live \
  --function-version <prev-version>

# 同様に cart_dismiss / notification_dispatcher も戻す
```

### 5.3 DDB データ復旧（PITR）

```bash
# CartWatchItems を任意時刻から復元（prd のみ、PITR 35 日）
aws dynamodb restore-table-to-point-in-time \
  --source-table-name yudane-cart-prd-watch-items \
  --target-table-name yudane-cart-prd-watch-items-restored-20260626 \
  --restore-date-time 2026-06-26T18:00:00+09:00

# 復元後、アプリケーションが新テーブルを参照するよう SSM Parameter を更新
aws ssm put-parameter \
  --name /yudane/prd/cart/cart-watch-items-table-arn \
  --value "arn:aws:dynamodb:ap-northeast-1:ACCOUNT:table/yudane-cart-prd-watch-items-restored-20260626" \
  --overwrite
```

### 5.4 Stack 全削除（最終手段）

```bash
# DeletionProtection を一時無効化
aws dynamodb update-table \
  --table-name yudane-cart-prd-watch-items \
  --deletion-protection-enabled false

# Stack 削除
cdk destroy cart-prd-stack

# 注: RemovalPolicy=RETAIN のため、DDB Table は CFN Stack から切り離されるが残存
# 完全削除には別途 aws dynamodb delete-table が必要
```

### 5.5 RTO / RPO 目標

| 障害種別 | RTO | RPO | 復旧手順 |
|---|---|---|---|
| Lambda コード bug（git revert で修正可能）| 30 分 | 0 | git revert + ci.yml + deploy-dev.yml 再走 |
| Lambda コード bug（緊急 hotfix）| 5 分 | 0 | Lambda Alias を直前 version に戻す（§5.2）|
| DDB データ汚染 | 1 時間 | 35 日 | PITR Restore（§5.3）|
| Stack 全壊 | 3 時間 | 35 日 | Stack 再作成 + PITR Restore + SSM Parameter 更新 |

---

## 6. ブロッカーと外部承認依存

### 6.1 Member 間合意プロセス（Plan v3 Q1=A 反映）

| 依頼先 | 依頼内容 | 期限 | エビデンス |
|---|---|---|---|
| Member A（Unit-1） | PlatformStack に `kmsKey` / `idempotencyKeysTable` / `idempotencyBucket` を export する props 経由提供 | **既合意済み**（functional-design.md §3.1）| Unit-1 functional-design.md §3.1 |
| Member A（Unit-2） | AuthStack に `usersTable` を export する props 経由提供 | **既合意済み** | Unit-2 functional-design.md（pending）|
| Member C（Unit-7） | SafeguardStack に `safeguardStatesTable` を export する props 経由提供 | **既合意済み** | Unit-7 functional-design.md（pending）|
| Member A（CI/CD） | `deploy-dev.yml` に `cdk-deploy-cart-dev` ジョブ追加 | 2026-05-30 18:00 JST | GitHub PR `#cart-deploy-001` |

> **Q6=A' により Member A への破壊的依頼ゼロ**（cartAlertTopic は CartStack 内で完結）。

> **Note**: 上記 §6.1 の Member 間合意のうち、Q8=A による `deploy-dev.yml` 拡張依頼は本 Infrastructure Design ステージで初めて発生する。functional-design.md §8.1 の既存合意リスト（Member A: OpenAPI / IdempotencyKeys / S-04 / M-01 delegate / Cognito 等）には未記載のため、本ドキュメントの §6.1 が一次出典となる。Member D が本 Plan 承認後に Slack `#yudane-dev` で Member A に依頼を出す。

### 6.2 外部承認ブロッカー

| ブロッカー | 期限 | backlog | 影響 |
|---|---|---|---|
| Apple Developer Program 登録 + APNs Production cert 取得 | **2026-06-12**（決勝 2 週間前） | [B-504](../../../../doc/backlog.md) | prd Push 配信不可、決勝デモシナリオ縮退リスク |
| Amazon Approved Mobile Application 申請 | 〜2026-06-15 | [B-503](../../../../doc/backlog.md) | Creators API 本接続不可、ダミーカタログで継続 |

両ブロッカーが期限超過した場合: Member A エスカレーション（[AGENTS.md §11.5](../../../../.kiro/steering/AGENTS.md)）→ 週次同期で代替案協議。

---

## 7. デプロイ後の動作確認チェックリスト（Smoke Test）

### 7.1 dev 環境（自動デプロイ後）

- [ ] CartWatchItems Table 存在確認: `aws dynamodb describe-table --table-name yudane-cart-dev-watch-items`
- [ ] NotificationLogs Table 存在確認: 同上
- [ ] 6 Lambda 全て deployed: `aws lambda list-functions | grep yudane-cart-dev`
- [ ] EventBridge Scheduler の retry batch が rate(15min) で稼働: `aws scheduler get-schedule --name cart-attack-scheduler-retry-schedule --group-name default`
- [ ] EUM Application 存在確認: `aws ssm get-parameter --name /yudane/dev/cart/eum-application-id`
- [ ] cartAlertTopic 存在確認 + Slack Bridge Lambda subscribe 確認
- [ ] CloudWatch Alarms 5 系統が `INSUFFICIENT_DATA` または `OK` 状態

### 7.2 prd 環境（決勝直前）

dev 環境のチェックに加えて:

- [ ] APNs Production Channel が `Enabled: true` で登録（B-504 完了後）
- [ ] DDB PITR が両 Table で有効
- [ ] DDB DeletionProtection が両 Table で有効
- [ ] CartWatchItems / NotificationLogs の RemovalPolicy=RETAIN を CFN テンプレートで確認
- [ ] Slack Webhook が `#yudane-emergency` を指す
- [ ] [E2E-03 シナリオ](../functional-design/functional-design.md)（Share → 30m → 論破 → Amazon）が pass

---

## 8. ハッカソン書類審査・予選評価軸へのインパクト

| 評価軸 | 本ドキュメントの貢献 |
|---|---|
| Unit 分解の適切さ | **強化**: デプロイ順序 4 Stack（Platform → Auth → Safeguard → Cart）が明示、CI/CD ジョブ追加が他 Unit と整合 |
| 創造性とテーマ適合性 | 維持 |
| ドキュメント品質 | **強化**: 環境別差異表 + ロールバック手順 + ブロッカーと外部承認依存 + Smoke Test チェックリストで運用 readiness を可視化 |
| AI-DLC プロセス（予選評価軸） | **強化**: Plan v3 Q8 / Q10 確定 → 物理 CI/CD パイプライン展開、運用手順まで一気通貫 |
