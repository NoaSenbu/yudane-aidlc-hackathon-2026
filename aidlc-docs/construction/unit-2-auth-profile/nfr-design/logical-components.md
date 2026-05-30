# Unit-2 Auth & Profile — Logical Components

> Unit-2 の論理コンポーネント構成。Unit-1 の LC-01〜08 を再利用しつつ Unit-2 固有を定義。
> 参照: [nfr-design-patterns.md](./nfr-design-patterns.md) / [Unit-2 Functional Design](../functional-design/) / [Unit-1 logical-components](../../unit-1-platform/nfr-design/logical-components.md)
> 確定方針: NFR-Design Q1=A / Q2=A / Q3=A / Q4=A

---

## 0. 論理コンポーネント一覧

| ID | 論理コンポーネント | 物理マッピング | 実現パターン |
|---|---|---|---|
| LC2-01 | AuthModule（MFA 状態機械） | M-11（mobile/src/features/auth） | PAT2-MFA-01 |
| LC2-02 | OnboardingController | M-02 近傍 + Zustand slice + profile API | PAT2-ONB-01 |
| LC2-03 | AuthEdgeLambda | B-01（backend/src/auth） | PAT-SEC-03 / ALG-INIT・ALG-CLAIM |
| LC2-04 | PreferenceVectorUpdater | B-08（backend/src/auth） | PAT2-BATCH-01 |
| LC2-05 | HomeSnapshotProvider | M-02 + GET /v1/home（or 集約） | ALG-HOME |
| LC2-06 | DebtSafeguardCoordinator | SafeguardState + Unit-1 S-03 | PAT2-DEBT-01 |

> Unit-1 の LC-01（ApiClient）/ LC-03（AuditLogger）/ LC-04（Authorization）/ LC-07（SafeguardPolicy）はそのまま再利用。

---

## 1. LC2-01 AuthModule（M-11、PAT2-MFA-01）

```
mobile/src/features/auth/auth-module/
  ├─ auth-machine.ts      … MFA チャレンジ駆動の有限状態機械（純ロジック、テスト対象）
  ├─ amplify-auth.ts      … Amplify Auth v6 ラッパー（signUp/signIn/confirmMfa/refresh...）
  └─ auth-token-provider.ts … Unit-1 AuthTokenProvider 実装（ApiClient へ注入）
```
- 状態機械（idle → signingIn → mfaChallenge → authenticated 等）は純ロジックで単体テスト
- Amplify 依存部分は薄いラッパーに隔離

---

## 2. LC2-02 OnboardingController（PAT2-ONB-01）

```
mobile/src/features/auth/onboarding/
  ├─ onboarding-store.ts  … Zustand slice（draft + step、persist）
  ├─ onboarding-flow.tsx  … 5 画面ナビゲーション（UI 結線は実機統合）
  └─ profile-api.ts       … PATCH /v1/users/{userId}/profile（冪等 upsert）
```
- サーバー権威 step + クライアントドラフト二層
- 段階保存の冪等性（max 演算）は純ロジックでテスト

---

## 3. LC2-03 AuthEdgeLambda（B-01、Cognito トリガー）

```
backend/src/auth/
  ├─ post_confirmation.py … User/PreferenceVector/SafeguardState/Achievement 一括初期化（冪等）
  └─ pre_token_generation.py … yudane_level/title/monthly_limit を claim 付与
```
- Unit-1 の AuditLogger / DomainError / モデルを利用
- 冪等初期化（既存チェック）

---

## 4. LC2-04 PreferenceVectorUpdater（B-08、PAT2-BATCH-01）

```
backend/src/auth/
  ├─ preference_updater.py … update_preference（日次 cron エントリ）
  └─ weekly_report.py      … generate_weekly_report（週次 cron エントリ）
```
- EventBridge cron 2 本 → 同一 Lambda の別ハンドラ
- 日次内で負債クーリングオフ遅延評価も実行（LC2-06 連携）

---

## 5. LC2-05 HomeSnapshotProvider（ALG-HOME、Q6=A）

```
mobile/src/features/auth/home/
  ├─ use-home-snapshot.ts … TanStack Query hook（候補/監視/カレンダー/Lv/残額）
  └─ home-screen.tsx      … 概況表示（詳細は Unit-8 へ遷移）
```
- remaining は Unit-1 SafeguardPolicy 経由
- 各 Unit のデータ源（候補=Unit-4, 監視=Unit-5, カレンダー=Unit-6）は API 集約で取得

---

## 6. LC2-06 DebtSafeguardCoordinator（PAT2-DEBT-01）

```
backend/src/auth/
  └─ debt_safeguard.py … 負債フラグ保存 / 解除リクエスト / 72h 遅延評価
                         判定本体は Unit-1 SafeguardPolicy.decide_allow を import
```
- Unit-2 は has_debt 状態管理 + 72h クーリングオフのみ。判定ロジックは Unit-1 再利用（NG-4 / US-AUTH-03）

---

## 7. モノレポ配置

```
mobile/src/features/auth/          … LC2-01/02/05（auth-module / onboarding / home）
backend/src/auth/                  … LC2-03/04/06（B-01 / B-08 / debt_safeguard）
infra/lib/auth-stack.ts            … Unit-2 固有スタック（次ステージで設計）
```

---

## 8. 未確定（Infrastructure Design で物理化）
| 項目 | 確定ステージ |
|---|---|
| auth-stack の DynamoDB テーブル（Users/PreferenceVectors/SafeguardStates/Achievements）PK/SK/GSI | Infrastructure Design |
| B-01 の Cognito トリガーアタッチ / B-08 の EventBridge cron 定義 | Infrastructure Design |
| Lambda メモリ・タイムアウト | Code Generation |
