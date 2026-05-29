# Unit-4 Reel — Code Generation Plan（Part 1: Planning）

> Construction Phase / Per-Unit Loop / Unit-4 Reel のコード生成計画。**本計画が Code Generation の Single Source of Truth**。TDD（Red → Green → Refactor → PBT 補強、[AGENTS.md §12](../../../.kiro/steering/AGENTS.md)）で実装。
> 参照: [Functional Design](../reel/functional-design/) / [NFR Design](../reel/nfr-design/) / [Infrastructure Design](../reel/infrastructure-design/) / [stories.md US-02](../../inception/user-stories/stories.md) / [Unit-1 code](../unit-1-platform/code/) / [tech-typescript.md](../../../.kiro/steering/tech-typescript.md) / [tech-python.md](../../../.kiro/steering/tech-python.md) / [tech-cdk.md](../../../.kiro/steering/tech-cdk.md) / [api-contracts.md](../../../.kiro/steering/api-contracts.md)
> 作成: 2026-05-30 / 担当: Member C / プロジェクト: Greenfield モノレポ

---

## 0. ユニットコンテキスト

### 実装するストーリー（US-02、5 本）
| Story | 概要 | 主担当コンポーネント |
|---|---|---|
| US-02-01 | 深夜ブースト（高単価先頭挿入 + 誘導アニメ） | B-03 ALG-BOOST / M-03 boostNudge |
| US-02-02 | ダブルタップ → 確認オーバーレイ → Amazon 遷移 + EXP +1 | M-03 / B-13 / B-10 |
| US-02-03 | 左スワイプ → 論破モード遷移（論破不要/クールダウン分岐） | M-03 ALG-GESTURE |
| US-02-04 | 右スワイプ → カート監視登録 | M-03 / Unit-5 連携 |
| US-02-05 | 「確保しておきました」所有感ラベル | B-03 ALG-PITCH/LABEL |

### 依存・インターフェース
- **依存（継承）**: Unit-1（M-12 ApiClient / S-01 AsinExtractor / S-03 SafeguardPolicy / AuditLogger Layer / DomainError / OpenAPI 骨格）/ Unit-2（Achievements・PreferenceVectors スキーマ、未完成中はスタブ）/ Unit-5（cart-watch-items、Prism Mock）/ Unit-6（calendar ctx、任意・スタブ）
- **契約**: `shared/schema/paths/reel.yaml` を非破壊拡張（getReel レスポンス / amazonTransitions body / 429）。**契約 PR 先行**（api-contracts §2、コア 3 Unit は Member A Approve）
- **所有エンティティ**: DynamoDB `amazon-transitions` / `impressions`（reel-stack）。SafeguardStates（Unit-7 read+条件付き increment）/ Achievements（Unit-2 スキーマ、EXP 冪等 UpdateItem）

### コード配置（Greenfield モノレポ、structure.md 準拠）
- Mobile: `mobile/src/features/reel/`
- Backend: `backend/src/reel/`
- Shared: 既存 `shared/asin-extractor` / `shared/safeguard-policy` を import（新規 shared は作らない）
- Infra: `infra/lib/reel-stack.ts` / `infra/test/reel-stack.test.ts`
- 契約: `shared/schema/paths/reel.yaml`（+ examples）

### TDD ルール（全ステップ共通）
- Backend = クラシック TDD（Red→Green→Refactor→PBT）/ Mobile = Outside-In（MSW 駆動）/ CDK = Snapshot TDD
- AI 生成順序（AGENTS.md §12.4）: テストファイル（Red）→ 実装（Green）→ PBT property → Refactor。各ファイル間で diagnostics 0 を確認
- ネットワーク制約により**依存インストール・テスト実行・型生成・cdk synth は Build and Test ステージで実施**（本ステージはコードとテストの生成まで、Unit-1 と同方針）

---

## 1. コード生成ステップ（番号順、各 [ ]）

> **✅ Part 2 実行完了（2026-05-30）**: 全 10 ステップ生成済み。実装上の差分メモ:
> - ジェスチャー純ロジックは `use-reel-gestures.ts` ではなく `gestures.ts`（純関数 `resolveGesture`）+ `boost-nudge.ts` として分離実装（フックより薄く・テスト容易）
> - フックは `use-reel-feed.ts` / `use-amazon-redirect.ts` として実装、冪等キーは `client-transition-id.ts`、API は `reel-api.ts` に分離
> - テストはユーザー要望で example（`*.test.ts`）と PBT（`*.pbt.test.ts`）を別ファイル化
> - Backend ロジック + PBT **40 件 pass 実行確認**。handler 2 件 / mobile vitest / infra synth は Build and Test で実行
> - 検出した cross-unit 依存（platform の `api-id`/`api-root-resource-id` SSM 未公開）は `infra-summary.md` に Member A 依頼として記録

### Step 1: API 契約の非破壊拡張（`shared/schema`）— ✅ 完了
- [ ] `shared/schema/paths/reel.yaml`: `getReel` の 200 レスポンス schema（ReelPage: cards[] + nextCursor）、`recordAmazonTransition` の requestBody（AmazonTransitionRequest）+ 201（ExpAward）+ 429（`X-RateLimit-*`）を定義
- [ ] `shared/schema/components/schemas/` に reel スキーマ（ReelCard / ReelPage / OwnershipLabel / AmazonTransitionRequest / ExpAward 等、`x-pii` 不要）を追加
- [ ] `shared/schema/examples/reel.yaml` を整備（Prism Mock 用、Member C 責務）
- [ ] **注**: 契約 PR は実装と分離し先行 merge（api-contracts §2）。型生成（openapi-typescript / datamodel-code-generator）は Build and Test で実行
- 関連: REEL-API-01〜07 / US-02 全般

### Step 2: Backend ビジネスロジック生成（`backend/src/reel/`、クラシック TDD）
2 段で実装（テスト先 → 実装 → PBT）:
- [ ] **事前掃除**: 別ブランチ由来の stale `backend/src/reel/__pycache__/`（`associates_link`/`creators_client`/`opensearch_client`/`service`/`transition_service` 等、本計画と異なる命名）を削除してから着手（import 混乱防止）
- [ ] `models.py` — Pydantic v2 DTO（RecommendationContext / ReelCard / ScoredCandidate / OwnershipLabel / AmazonTransitionRequest / ExpAward / SpecialLink / CatalogQuery / PurchaseHistoryItem）（型宣言は TDD 例外 §12.3）
- [ ] `catalog.py` — `ProductCatalogPort` + `DummyCatalogAdapter`（プロセス内・同梱 JSON）+ cache デコレータ枠（決勝の CreatorsApiAdapter は stub）。ALG-CATALOG
- [ ] `ranking.py` — ALG-RANK（候補生成→決定論リランク、純関数）+ ALG-BOOST（深夜ブースト）。`CandidateSourcePort` + `PurchaseHistoryHeuristicSource`
- [ ] `bedrock_client.py` — Bedrock Runtime（Haiku 4.5）の**薄いラッパ**（boto3 `bedrock-runtime`、モデル ID は SSM）。テストは**クライアント注入でモック**（実 SDK 呼び出しはせず、依存性注入でフェイク差し替え）
- [ ] `labels.py` — ALG-PITCH/LABEL（`bedrock_client` 注入 + テンプレートフォールバック + モデレーション `moderate()` + 24h 重複防止）
- [ ] `special_link.py` — ALG-LINK（純関数、Associates タグ=SSM、短縮禁止、環境ガード、S-01 で逆抽出検証）
- [ ] `transition.py` — ALG-TRANSITION（先行 Safeguard ゲート / fail-closed、冪等 TransactWriteItems〔遷移+月間カウント〕、EXP +1 同期 Achievements UpdateItem）
  - **S-03 整合**: 既存 `shared/safeguard-policy/python/safeguard_policy.py` の `decide_allow(SafeguardInput(transition_count_month, monthly_limit_yen, current_budget_used_yen, SafeguardFlags(cooldown_on, quiet_week, has_debt)))` の正本シグネチャに合わせて `SafeguardInput` を構築（独自再実装しない、SG-10 クロス言語一致）
- 関連: US-02-01/02/05 / REEL-RANK/BOOST/LABEL/CAT/TR/LINK

### Step 3: Backend ビジネスロジック・ユニットテスト + PBT
- [ ] `tests/reel/test_ranking.py` — example + PBT-03（決定論・score=Σcomponents・NG 除外・既出抑制・遷移後カテゴリ cooldown）
- [ ] `tests/reel/test_boost.py` — 発火条件の真理値表（時刻×ストレス×フラグ）+ 価格範囲不変条件
- [ ] `tests/reel/test_special_link.py` — PBT-02 round-trip（生成 URL → S-01 extractAsin → 一致）+ 短縮禁止 + 環境ガード
- [ ] `tests/reel/test_transition.py` — PBT-04 冪等性（同一 clientTransitionId で EXP/カウント二重計上なし）+ 上限超過なし + fail-closed
- [ ] `tests/reel/test_labels.py` — フォールバック非空 + 24h 重複なし + モデレーション後出力（NG-6/NG-3）。`bedrock_client` はモック注入
- [ ] `tests/reel/strategies.py` — PBT-07 ドメインジェネレータ（購入履歴/価格/StressLevel/TimeBucket/SafeguardFlags）
- フレームワーク: Hypothesis（seed 固定 PBT-08 / example 併存 PBT-10）

### Step 4: Backend API レイヤ（Lambda ハンドラ）
- [ ] `handlers/feed.py` — `GET /v1/reel`（@require_owner、cursor/limit 検証、ALG-RANK 呼出、B-10 同梱、Bedrock ラベル、決勝 B-11 invoke 分岐）
- [ ] `handlers/transition.py` — `POST /v1/amazon-transitions`（@require_owner、ALG-TRANSITION、409/429、ExpAward 返却）
- [ ] `tests/reel/test_handler_feed.py` / `test_handler_transition.py` — example（200/401/403/409 + 冪等）
- 関連: REEL-API-03/04/07 / SECURITY-05/08/09/11

### Step 5: Backend ビジネスロジック・API サマリ（ドキュメント）
- [ ] `aidlc-docs/construction/reel/code/backend-summary.md`（生成物・テスト・カバレッジ方針）

### Step 6: Mobile フロントエンド生成（`mobile/src/features/reel/`、Outside-In TDD）
- [ ] `use-reel-feed.ts` — `GET /v1/reel` カーソルページング（TanStack useInfiniteQuery、MSW 駆動）
- [ ] `use-amazon-redirect.ts` — 確認オーバーレイ → `POST /v1/amazon-transitions`（clientTransitionId 生成）→ Special Link Deep Link
- [ ] `use-reel-gestures.ts` — ALG-GESTURE（左/右 60px・ダブルタップ 350ms・優先順位・論破不要/クールダウン・boostNudge 3 秒）純粋ロジック
- [ ] `reel-screen.tsx` — M-03（仮想化リスト + GestureLayer + AmazonTransitionOverlay + OwnershipLabelBadge）。`data-testid` 付与（automation friendly）
- [ ] テーマ/トースト/EXP 楽観表示は Unit-1 土台（GlobalToast / Zustand）を利用
- 関連: US-02-01〜05 / REEL-GES / FR-REEL-05
- **依存追加**: `@shopify/flash-list` / `react-native-gesture-handler` / `react-native-reanimated` を declare（インストールは Build and Test、追加時に CVE チェック = secure-dependency-install）

### Step 7: Mobile フロントエンド・ユニットテスト
- [ ] `__tests__/use-reel-feed.test.ts` / `use-amazon-redirect.test.ts` / `use-reel-gestures.test.ts`（MSW + renderHook）
- [ ] ジェスチャー閾値・優先順位・確認オーバーレイ必須・論破不要分岐・boostNudge の example テスト
- [ ] `mobile/src/test/msw-handlers.ts` に reel ハンドラ追記（reel.yaml examples 整合）

### Step 8: Mobile フロントエンド・サマリ（ドキュメント）
- [ ] `aidlc-docs/construction/reel/code/mobile-summary.md`

### Step 9: Infra（`infra/lib/reel-stack.ts`、Snapshot TDD）
- [ ] `infra/lib/reel-stack.ts` — DynamoDB（amazon-transitions + gsi-month / impressions、On-Demand/PITR/SSE-KMS/TTL）、Lambda（feed/transition = VPC 外 SnapStart + AuditLogger Layer、catalog = 決勝 feature フラグで VPC 内）、API パス追加（SSM 参照）、usage plan 429、SSM 出力、CloudWatch Alarm → SNS
  - **API GW 結線**: platform-stack が SSM で expose する `api-id` / `api-root-resource-id` を `RestApi.fromRestApiAttributes()` で import し、`addResource('reel')` / `addResource('amazon-transitions')` でルート追加（platform の単一 API に相乗り、shared-infra §3.6）
  - **共有資源参照**: VPC / KMS / Lambda SG / SNS / AuditLogger Layer ARN を `StringParameter.valueForStringParameter()` で参照（Export/Import 不使用）
- [ ] `infra/test/reel-stack.test.ts` — CDK assertions（テーブル/Lambda/Alarm）+ cdk-nag（AwsSolutionsChecks）スナップショット
- [ ] `infra/bin/app.ts` に reel-stack を env 切替で登録
- 関連: Infra Q1〜Q7 / SECURITY-01/06/07/11/14

### Step 10: Infra サマリ + Unit-4 総括（ドキュメント）
- [ ] `aidlc-docs/construction/reel/code/infra-summary.md`
- [ ] `aidlc-docs/construction/reel/code/unit-4-code-summary.md`（全体サマリ + Extension コンプライアンス + スコープ外）

---

## 2. ストーリートレーサビリティ

| Story | カバーするステップ |
|---|---|
| US-02-01 | Step 2（ranking/boost）/ Step 3（boost test）/ Step 6（boostNudge）|
| US-02-02 | Step 2（transition/special_link）/ Step 3/4 / Step 6（use-amazon-redirect, overlay）|
| US-02-03 | Step 6（use-reel-gestures）/ Step 7 |
| US-02-04 | Step 6（右スワイプ → cart-watch-items、Unit-5 Mock）/ Step 7 |
| US-02-05 | Step 2（labels）/ Step 3（labels test）/ Step 6（OwnershipLabelBadge）|

---

## 3. スコープ外（後続ステージ / Unit）

- テスト実行・カバレッジ計測・型生成・cdk synth/deploy → **Build and Test ステージ**
- 依存パッケージの実インストール（CVE チェック込み）→ Build and Test 着手時
- OpenSearch ベクトル検索（VectorSearchSource）/ Creators API 本番接続 → 決勝（B-204）
- Achievements / PreferenceVectors / SafeguardStates テーブル本体 → Unit-2 / Unit-7（reel は参照・スタブ）
- 契約 PR の merge（Member A Approve）→ 実装 PR と分離。**Part 2 では reel.yaml と実装を同じターンで生成するが、PR 化の際は契約 PR を分離して先に出す**（api-contracts §2、生成レイヤと PR 運用レイヤは別）

---

## 4. 完了基準（Part 2 終了条件）
- 全 Step [x]、US-02-01〜05 実装済み
- 各 ALG にテスト + 該当 PBT（PBT-02/03/04/07）を併設、diagnostics 0
- reel-stack の CDK + snapshot test 生成
- code サマリ（backend/mobile/infra/unit-4 総括）作成
- 実行・デプロイは Build and Test へ引き継ぎ
