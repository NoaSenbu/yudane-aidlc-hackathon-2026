# Unit-2 Auth & Profile — Code Generation 総括

> Unit-2 のコード生成（Step 1〜15）の全体サマリ。
> 確定方針: FD（Q1〜Q6=A）/ NFR-Req（Q1=C/Q2=C/Q3=部分/Q4=A/Q5=B、US-AUTH-03=MVP）/ NFR-Design（Q1〜Q4=A）/ Infra（Q1〜Q4=A）

## 生成物の全体像

### shared/
- `schema/components/schemas/auth.yaml` + paths/auth.yaml 詳細化（非破壊）+ 生成型に Unit-2 型追記

### backend/src/auth/
- `models/`（UserEntity / SafeguardStateEntity / AchievementEntity）
- `repositories/`（Protocol + DynamoDB 実装、4 テーブル）
- `onboarding.py` / `level.py` / `debt_safeguard.py`（ドメインロジック、純関数）
- `post_confirmation.py` / `pre_token_generation.py`（B-01）
- `handlers/`（profile / safeguard_debt / responses、require_owner + 検証）
- `preference_updater.py` / `weekly_report.py`（B-08 日次/週次）
- `tests/auth/`（onboarding/level/debt/post_confirmation/profile_handler/batch + fakes）

### mobile/src/features/auth/
- `auth-module/`（auth-machine 状態機械 / amplify-auth ラッパー / auth-token-provider + テスト）
- `onboarding/`（onboarding-store + nextStep 冪等 + テスト）
- `home/`（use-home-snapshot）

### infra/
- `lib/auth-stack.ts`（DynamoDB 4 / B-08 + cron 2 / SSM 参照）+ bin/app.ts 追加 + auth-stack.test.ts

### shared / docs
- `mobile/src/test/msw-handlers.ts` に auth エンドポイント追加
- `code/` 配下に 8 サマリ

## ストーリー実装状況（MVP）
- **US-AUTH-01**（オンボ 90 秒 + 段階保存 + Associates 開示）✅ コード + PBT
- **US-AUTH-02**（MFA 状態機械 + ロック/リセット冷却ロジック）✅ コード + テスト（Alarm 作り込みは決勝）
- **US-AUTH-03**（負債セーフガード、Unit-1 S-03 連携 + 72h クーリングオフ）✅ コード + テスト（MVP 残置、NG-4）

## Extension コンプライアンス（実装段階）
- SECURITY-05（Pydantic/JSON 検証）/ SECURITY-08（require_owner）/ SECURITY-12（MFA 状態機械）/ SECURITY-01/06（auth-stack）
- PBT-04（オンボ段階保存・初期化の冪等性）/ Lv 単調増加 invariant / 負債 72h クーリングオフ

## Unit-1 再利用（二重実装なし）
- DomainError / AuditLogger / require_owner / SafeguardPolicy（debt）/ ApiClient / AuthTokenProvider / models

## スコープ外（後続）
- テスト実行・カバレッジ・cdk deploy → Build and Test
- B-01 トリガーアタッチ + API Gateway 統合の結線 → 実装統合
- Alarm 作り込み / オンボ完了率計測 / 性能実測 → 決勝
- 嗜好ベクトルの OpenSearch 検索本格化 → Unit-4

## 検証メモ
- 全コードファイル diagnostics 0
- ネットワーク制約により依存インストール・テスト実行・型生成・cdk synth は未実行（Build and Test で実施）
