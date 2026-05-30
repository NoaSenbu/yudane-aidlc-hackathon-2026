# Unit-2 Auth & Profile — Infrastructure Design

> `auth-stack`（Unit-2）の AWS インフラ設計。platform-stack の SSM 出力を参照する。
> 参照: [Unit-2 NFR Design](../nfr-design/) / [shared-infrastructure.md](../../shared-infrastructure.md) / [Unit-1 Infrastructure Design](../../unit-1-platform/infrastructure-design/) / [tech-cdk.md](../../../../.kiro/steering/tech-cdk.md)
> 確定方針: Infra Q1=A / Q2=A / Q3=A / Q4=A
> リージョン: `ap-northeast-1`

---

## 0. サマリ

| カテゴリ | リソース | 確定根拠 |
|---|---|---|
| データ | DynamoDB 4 テーブル（Users / PreferenceVectors / SafeguardStates / Achievements） | Q1=A |
| 認証 | platform User Pool に B-01 トリガー追加 | Q2=A |
| バッチ | EventBridge cron 2 本（日次/週次）→ B-08 | Q3=A |
| Lambda | B-01 / B-08 + auth API Lambda 群 | NFR Design LC2 |
| 環境 | dev + prd（DynamoDB prd=RETAIN） | Q4=A |

---

## 1. platform-stack からの参照（SSM、shared-infrastructure §1）

| 参照値 | SSM パラメータ |
|---|---|
| VPC ID | `/yudane/<env>/platform/vpc-id` |
| Private Subnet IDs | `/yudane/<env>/platform/private-subnet-ids` |
| Lambda SG ID | `/yudane/<env>/platform/lambda-sg-id` |
| User Pool ID | `/yudane/<env>/platform/userpool-id` |
| KMS Key ARN | `/yudane/<env>/platform/kms-key-arn` |
| Alerts SNS Topic | `/yudane/<env>/platform/alerts-topic-arn` |

---

## 2. DynamoDB（Q1=A、4 テーブル分離）

| テーブル | PK | 主な属性 | 共通設定 |
|---|---|---|---|
| `yudane-auth-<env>-users` | userId | email(x-pii) / profileCompleted / onboardingStep / UserProfile 埋め込み | PAY_PER_REQUEST / PITR / SSE-KMS（platform key） |
| `yudane-auth-<env>-preference-vectors` | userId | vector / labels / updatedAt | 同上 |
| `yudane-auth-<env>-safeguard-states` | userId | monthlyLimitYen / currentBudgetUsedYen / flags / debtReleaseRequestedAt | 同上 |
| `yudane-auth-<env>-achievements` | userId | exp / level / titles / streak | 同上 |

- removalPolicy: dev=DESTROY / prd=RETAIN（Q4=A、データ保全）
- WeeklyReports は Unit-8 `report-stack` 所有（本 stack には含めない）
- GSI: MVP では不要（全アクセスが userId 主キー）。将来必要なら `gsi-<attr>` 命名（shared-infrastructure §2）

---

## 3. Cognito トリガー（Q2=A）

```
platform-stack: User Pool 本体（yudane-auth-<env>-userpool、MFA REQUIRED）
auth-stack:
  - B-01 AuthEdgeLambda を SSM の userpool-id 参照でアタッチ
    - Post Confirmation → ALG-INIT（User/PreferenceVector/SafeguardState/Achievement 初期化）
    - Pre Token Generation → ALG-CLAIM（yudane_level/title/monthly_limit 付与）
  - クロススタックは CfnUserPool への trigger 追加（SSM 参照 + addTrigger）
```

- B-01 の IAM: 上記 4 テーブルへの PutItem/GetItem のみ（最小権限、SECURITY-06）

---

## 4. EventBridge cron（Q3=A、PAT2-BATCH-01）

| Rule | スケジュール | ターゲット |
|---|---|---|
| `yudane-auth-<env>-daily` | cron 日次 04:00 JST | B-08 handler: update_preference（+ 負債 72h 遅延評価） |
| `yudane-auth-<env>-weekly` | cron 日曜 22:00 JST | B-08 handler: generate_weekly_report |

- B-08 の IAM: PreferenceVectors/SafeguardStates 読み書き + CloudWatch Metrics 読み取り + WeeklyReports 書き込み（report-stack のテーブルへクロスアカウントなしの同一アカウント書き込み）

---

## 5. Lambda（VPC / 観測）

| Lambda | 配置 | ロール |
|---|---|---|
| B-01 AuthEdgeLambda | platform VPC（private）+ SG | 個別ロール（4 テーブル put/get） |
| B-08 PreferenceVectorUpdater | platform VPC + SG | 個別ロール（バッチ集計） |
| auth API Lambda（profile / user CRUD） | platform VPC + SG | require_owner、対象テーブル最小権限 |

- 全 Lambda: Python 3.13 / Powertools / B-12 AuditLogger Layer（Unit-1）/ X-Ray active
- メモリ・タイムアウトは Code Generation で確定

---

## 6. 観測（NFR2-SEC-04）

- MVP: B-12 構造化ログ + サインイン成功率メトリクス（`auth.signin.success_rate`）
- 決勝: 認証失敗 Alarm（platform SNS トピックへ）+ 異常検知 + 監査ログ 90 日

---

## 7. 論理 → 物理マッピング

| LC | 論理 | 物理 |
|---|---|---|
| LC2-01 AuthModule | （クライアント、Cognito User Pool 利用） | — |
| LC2-03 AuthEdgeLambda | B-01 Lambda + Cognito トリガー | auth-stack |
| LC2-04 PreferenceVectorUpdater | B-08 Lambda + EventBridge cron 2 本 | auth-stack |
| LC2-06 DebtSafeguardCoordinator | SafeguardStates テーブル + B-08 日次遅延評価 | auth-stack |
| Users/PreferenceVectors/SafeguardStates/Achievements | DynamoDB 4 テーブル | auth-stack |

---

## 8. Extension コンプライアンスサマリ
| Extension | 状態 | 反映 |
|---|---|---|
| SECURITY-01 | ✅ | DynamoDB SSE-KMS（platform key） |
| SECURITY-06 | ✅ | Lambda 個別ロール最小権限 |
| SECURITY-07 | ✅ | platform VPC + SG |
| SECURITY-14 | ⏭ 決勝 | 認証失敗 Alarm |
| NG-4 | ✅ MVP | SafeguardStates + 負債遅延評価 |
| cdk-nag | ✅ | AwsSolutionsChecks（auth-stack にも適用） |
