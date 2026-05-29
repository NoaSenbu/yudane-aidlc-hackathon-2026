# Unit-2 Auth & Profile — Code Generation Plan

> **Code Generation の Single Source of Truth**。Part 2 でこのステップ順に従ってコード生成し、各ステップ完了時に [x]。
> 参照: [Unit-2 Functional Design](../unit-2-auth-profile/functional-design/) / [NFR Design](../unit-2-auth-profile/nfr-design/) / [Infrastructure Design](../unit-2-auth-profile/infrastructure-design/) / [Unit-1 成果物](../unit-1-platform/) / steering（tech-typescript / tech-python / tech-cdk / api-contracts）
> 作成: 2026-05-29 / ステージ: 🟢 CONSTRUCTION / Code Generation Part 1

---

## 0. Unit-2 のコンテキスト

| 項目 | 内容 |
|---|---|
| 目的 | ユーザー登録・認証・プロファイル初期化・ホーム・日次/週次バッチ |
| 担当 | Member A |
| ストーリー | US-AUTH-01（オンボ）/ US-AUTH-02（MFA）/ US-AUTH-03（負債セーフガード） |
| 依存 | Unit-1 Platform（exceptions / logging / authz / SafeguardPolicy / ApiClient / models / platform-stack） |
| プロジェクト種別 | Greenfield モノレポ（mobile/backend/infra に Unit-2 分を追加） |

### Unit-1 からの再利用（再実装しない）
- `backend/src/common/`（DomainError / AuditLogger / sanitizer / require_owner / models）
- `mobile/src/features/platform/`（ApiClient / AuthTokenProvider 型 / Telemetry / app-shell / providers）
- `shared/safeguard-policy`（S-03 decideAllow、US-AUTH-03 の DEBT 比率）
- platform-stack の SSM 出力（auth-stack が参照）

### MVP スコープ（NFR2 確定）
- MFA 必須 + 15 分ロック + 72h リセット冷却（ロジック）/ US-AUTH-03 負債セーフガード = MVP
- Alarm 作り込み・オンボ完了率計測・性能目標実測 = 決勝

---

## 1. コード生成ステップ（Part 2 で順次実行）

### Step 1: OpenAPI auth パス詳細化 + 型再生成
- [x] `shared/schema/paths/auth.yaml` に省略可能フィールドを非破壊追記（UserProfile / SafeguardSettings / Achievement の詳細スキーマ）
- [x] `shared/schema/components/schemas/` に auth ドメインスキーマ追加（UserProfile / SafeguardState / Achievement）
- [x] 生成型スナップショット更新（types/api.ts / api.py に Unit-2 型）
- 規約: api-contracts §2/§6（非破壊）/ ドキュメント: `code/schema-auth-summary.md`

### Step 2: Backend ドメインモデル + リポジトリ
- [x] `backend/src/auth/models/`（UserProfile / SafeguardState / Achievement の Pydantic ドメインモデル）
- [x] `backend/src/auth/repositories/`（DynamoDB アクセス、4 テーブル、boto3 + Protocol）
- ルール: ONB / INIT / Unit-1 共通設定

### Step 3: Backend ドメインロジック（純ロジック）
- [x] `backend/src/auth/onboarding.py`（段階保存・冪等 max step、ALG-ONBOARD）
- [x] `backend/src/auth/level.py`（Lv/称号判定、ALG-LEVEL、純関数）
- [x] `backend/src/auth/debt_safeguard.py`（負債 72h クーリングオフ、Unit-1 S-03 連携、ALG-DEBT/PAT2-DEBT-01）
- ルール: ONB-01〜06 / LV-01〜04 / DEBT-01〜05

### Step 4: Backend ドメインロジック PBT + 単体テスト
- [x] `backend/tests/auth/test_onboarding.py`（段階保存 idempotency PBT-04）
- [x] `backend/tests/auth/test_level.py`（Lv 単調増加 invariant）
- [x] `backend/tests/auth/test_debt_safeguard.py`（72h クーリングオフ / S-03 連携）
- NFR: NFR2-COV（純ロジック 95%）/ ドキュメント: `code/auth-logic-summary.md`

### Step 5: B-01 AuthEdgeLambda
- [x] `backend/src/auth/post_confirmation.py`（User/SafeguardState/Achievement 冪等初期化、ALG-INIT）
- [x] `backend/src/auth/pre_token_generation.py`（yudane_level/title/monthly_limit claim、ALG-CLAIM）
- ルール: INIT-01〜04

### Step 6: auth API Lambda（profile / user CRUD）
- [x] `backend/src/auth/handlers/profile.py`（POST/PATCH /v1/users/{userId}/profile、require_owner、Pydantic 検証）
- [x] `backend/src/auth/handlers/safeguard_debt.py`（負債フラグ申告/解除リクエスト）+ `responses.py`（共通レスポンス）
- ルール: SEC-01〜03 / SECURITY-05/08

### Step 7: B-01 / API Lambda 単体テスト
- [x] `backend/tests/auth/test_post_confirmation.py`（冪等初期化 + claim）
- [x] `backend/tests/auth/test_profile_handler.py`（段階保存 + 負債連携 + not-found、fake repo）
- ドキュメント: `code/auth-backend-summary.md`

### Step 8: B-08 バッチ（日次/週次）
- [x] `backend/src/auth/preference_updater.py`（日次: 嗜好ラベル更新 + 負債遅延評価、ALG-PREF）
- [x] `backend/src/auth/weekly_report.py`（週次: 指標集計 → WeeklyReports、ALG-WEEKLY）
- [x] `backend/tests/auth/test_batch.py`（日次/週次の集計）
- ルール: RPT-01/02 / PAT2-BATCH-01 / ドキュメント: `code/auth-batch-summary.md`

### Step 9: Mobile / M-11 AuthModule（MFA 状態機械）
- [x] `mobile/src/features/auth/auth-module/auth-machine.ts`（チャレンジ駆動状態機械、純ロジック、PAT2-MFA-01）
- [x] `auth-module/amplify-auth.ts`（Amplify Auth v6 ラッパー interface）
- [x] `auth-module/auth-token-provider.ts`（Unit-1 AuthTokenProvider 実装）
- ルール: MFA-01〜07

### Step 10: M-11 単体テスト
- [x] `auth-machine.test.ts`（状態遷移: idle→signingIn→mfaChallenge→authenticated、失敗/リセット + token provider）
- NFR: NFR2-COV（85%）/ ドキュメント: `code/auth-module-summary.md`

### Step 11: Mobile / OnboardingController + HomeScreen
- [x] `mobile/src/features/auth/onboarding/`（onboarding-store Zustand slice + nextStep 冪等ロジック、PAT2-ONB-01）
- [x] `mobile/src/features/auth/home/`（use-home-snapshot hook、ALG-HOME 概況のみ Q6=A）
- ルール: ONB-02/03 / RPT-03/04

### Step 12: Onboarding / Home 単体テスト
- [x] `onboarding-store.test.ts`（段階保存 max 演算の冪等性 PBT）
- [x] Home hook は ApiClient 結線（実機統合時にレンダリングテスト追加）
- ドキュメント: `code/auth-module-summary.md`

### Step 13: Infra / auth-stack
- [x] `infra/lib/auth-stack.ts`（DynamoDB 4 テーブル / B-08 EventBridge cron 2 本 / SSM 参照 / cdk-nag）
- [x] `infra/bin/app.ts` に auth-stack 追加
- ルール: tech-cdk / shared-infrastructure / SECURITY-01/06/07
- 注記: B-01 トリガーアタッチ + auth API Gateway 統合は実装統合で結線（コードは Step 5-6 で生成済み）

### Step 14: auth-stack スナップショットテスト
- [x] `infra/test/auth-stack.test.ts`（DynamoDB 4 / cron 2 / Python3.13 / prd RETAIN / cdk-nag アサート）
- ドキュメント: `code/auth-stack-summary.md`

### Step 15: 仕上げ + 総括
- [x] MSW ハンドラに auth エンドポイント追加（profile / home、contract テスト）
- [x] Unit-2 コード総括: `code/unit-2-code-summary.md`
- [x] aidlc-state.md / 本プランのチェックボックス最終更新

---

## 2. ストーリートレーサビリティ
- US-AUTH-01 → Step 1/2/3/5/6/11（オンボ段階保存 + プロファイル + Associates 開示）
- US-AUTH-02 → Step 9/10（MFA 状態機械）+ platform User Pool（MFA REQUIRED）
- US-AUTH-03 → Step 3/4/6/8/13（負債セーフガード、Unit-1 S-03 + SafeguardStates + 72h 遅延評価）

## 3. 完了基準
- [x] Step 1〜15 すべて [x]
- [x] US-AUTH-01/02/03 のコード + テスト生成済み（実行は Build and Test）
- [x] auth-stack が cdk synth 可能
- [x] Unit-1 共通ライブラリを再利用（二重実装なし）

## 4. スコープ外（後続）
- テスト実行・カバレッジ・cdk deploy → Build and Test
- Alarm 作り込み / オンボ完了率計測 / 性能実測 → 決勝
- OpenSearch 連携の嗜好ベクトル検索本格化 → Unit-4
