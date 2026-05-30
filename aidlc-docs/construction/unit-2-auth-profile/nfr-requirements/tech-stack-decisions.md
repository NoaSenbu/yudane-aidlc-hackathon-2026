# Unit-2 Auth & Profile — Tech Stack Decisions

> Unit-2 で実体化する技術選定。大半は Unit-1 / 要件書 §7 を継承し、Unit-2 固有分のみ確定。
> 参照: [nfr-requirements.md](./nfr-requirements.md) / [Unit-1 tech-stack-decisions](../../unit-1-platform/nfr-requirements/tech-stack-decisions.md) / [要件書 §7](../../../inception/requirements/requirements.md)

---

## 0. Unit-1 継承（新規選定なし）

- Mobile: React Native 0.76+ / TypeScript 5.x / TanStack Query（retry=false）/ Zustand
- Backend: Python 3.13 / Lambda Powertools / Pydantic v2 / boto3
- 観測: B-12 AuditLogger（EMF / sanitizer）
- 契約: OpenAPI 3.1（auth パスに非破壊追記）/ Prism / MSW / Schemathesis
- PBT: fast-check / Hypothesis

---

## 1. Unit-2 固有の技術選定

| 項目 | 決定 | 根拠 |
|---|---|---|
| 認証 SDK | **aws-amplify/auth v6（Auth モジュールのみ）** | US-AUTH-02 / tech.md（`amazon-cognito-identity-js` 不採用） |
| MFA | **TOTP**（Authenticator アプリ、QR + 6 桁） | SECURITY-12 / US-AUTH-02 AC-1 |
| Cognito トリガー | **B-01 AuthEdgeLambda**（Post Confirmation / Pre Token Generation） | SVC-05 / ALG-INIT・ALG-CLAIM |
| 嗜好ベクトル | Titan Embeddings V2（Unit-1 OpenSearch は Unit-4 で本格利用、Unit-2 は vector 保存のみ） | UC-07 |
| 日次/週次バッチ | EventBridge（cron）→ B-08 Lambda（日次/週次の別ハンドラ） | Q5=A FD / Step Functions 不採用 |
| Safeguard 連携 | **Unit-1 S-03 SafeguardPolicy を import**（再実装しない） | US-AUTH-03 / DEBT 比率 0.35 |

---

## 2. AuthModule と ApiClient の結線（Q4=A FD）

- M-11 AuthModule は Unit-1 `AuthTokenProvider`（getAccessToken / refresh / onAuthExpired）を実装
- ApiClient（M-12）に注入し、401 single-shot refresh が AuthModule.refresh を呼ぶ
- トークン保管は Amplify Auth v6 が管理（Secure Storage）

---

## 3. データストア（Unit-1 共通設定を適用）

| テーブル | 命名 | 備考 |
|---|---|---|
| Users | `yudane-auth-<env>-users` | UserProfile 埋め込み、KMS 暗号化、PITR |
| PreferenceVectors | `yudane-auth-<env>-preference-vectors` | B-08 日次更新 |
| SafeguardStates | `yudane-auth-<env>-safeguard-states` | Unit-1 S-03 が参照、Unit-7 が運用 |
| Achievements | `yudane-auth-<env>-achievements` | Lv / 称号 / Streak |

> テーブル設計（PK/SK/GSI）の具体は auth-stack の Infrastructure Design / Code Generation で確定。

---

## 4. デプロイ単位

- `auth-stack`（Unit-2）。platform-stack の SSM 出力（VPC / User Pool ID / KMS / SG / SNS）を参照
- B-01 は Cognito User Pool（platform-stack）のトリガーとしてアタッチ

---

## 5. 未決定（後続ステージ）

| 項目 | 確定ステージ |
|---|---|
| DynamoDB テーブルの PK/SK/GSI | auth-stack Infrastructure Design |
| B-01/B-08 の Lambda メモリ・タイムアウト | NFR Design / Code Generation |
| Unit-2 性能目標の実測値 | 決勝前（Q1=C） |
