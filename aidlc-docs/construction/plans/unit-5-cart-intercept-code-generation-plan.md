# Unit-5 Cart Intercept — Code Generation Plan

> **このプランは Code Generation の Single Source of Truth**。Part 2 ではこのステップ順に従ってコードを生成し、各ステップ完了時に [x] を付ける。
>
> 参照:
> - [Unit-5 Functional Design](../unit-5-cart-intercept/functional-design/)（functional-design.md / data-model.md / sequence-diagrams.md）
> - [Unit-5 NFR Design](../unit-5-cart-intercept/nfr-design/)（nfr-design-patterns.md / logical-components.md）
> - [Unit-5 Infrastructure Design](../unit-5-cart-intercept/infrastructure-design/)（infrastructure-design.md / deployment-architecture.md）
> - [Unit-1 Code Generation Plan](./unit-1-platform-code-generation-plan.md)（テンプレートとして参照、shared/* / common/* の追記方針整合）
> - [shared-infrastructure.md](../shared-infrastructure.md) / steering（[tech-typescript.md](../../../.kiro/steering/tech-typescript.md) / [tech-python.md](../../../.kiro/steering/tech-python.md) / [tech-cdk.md](../../../.kiro/steering/tech-cdk.md) / [api-contracts.md](../../../.kiro/steering/api-contracts.md) / [AGENTS.md §12 TDD](../../../.kiro/steering/AGENTS.md#12-tdd-開発スタイル全-unit-必須)）
>
> 作成: 2026-05-29 / ステージ: 🟢 CONSTRUCTION / Code Generation Part 1（計画）

---

## 0. Unit-5 のコンテキスト

| 項目 | 内容 |
|---|---|
| 目的 | UC-03 カート介入（Share 受信 → 監視リスト → 30m/6h/24h 追撃通知 → 論破セッション誘導 → Amazon 遷移）の機能実現 |
| 担当 | Member D |
| 主担当ストーリー | **5 ストーリー**: US-03-01（Share 受信 → 監視登録）/ US-03-02（30m/6h/24h 追撃通知）/ US-03-03（クリップボード検知 — backlog B-502 で MVP 見送り）/ US-03-04（Amazon 遷移）/ US-03-05（Safeguard 月間上限・冷却モード反映） |
| 副担当ストーリー | なし |
| 依存 Unit | **Unit-1**（基盤、ApiClient / AuditLogger / SafeguardPolicy / AsinExtractor / IdempotencyKeys / Telemetry）/ **Unit-2**（Cognito JWT / Users.pushEndpointId）/ **Unit-3**（POST /v1/debate-sessions）/ **Unit-4**（B-11 CreatorsApiClient / B-13 AmazonTransitionRecorder / B-10 AssociatesLinkGenerator）/ **Unit-7**（SafeguardStates / Lambda Authorizer） |
| 提供インターフェース | OpenAPI cart paths（`shared/schema/paths/cart.yaml` 既存） / cart-stack（CDK） / Cart 関連 telemetry 識別子（既追加） |
| プロジェクト種別 | Greenfield モノレポ既存（mobile/backend/infra/shared 構造を継承） |
| ワークスペースルート | リポジトリ直下（aidlc-docs/ には絶対に置かない） |

### Unit-5 が生成するコンポーネント

| ID | コンポーネント | 配置 | 種別 |
|---|---|---|---|
| **M-05** | CartInterceptScreen + use-* hooks | `mobile/src/features/cart/` | UI + Hooks |
| **M-08** | ShareExtensionNativeModule（Expo Config Plugin + iOS Swift + Android Kotlin） | `mobile/plugins/share-extension/` + `mobile/src/features/cart/share-extension-module.ts` | Native + Bridge |
| **M-09** | PushNotificationHandler | `mobile/src/features/cart/push-notification-handler.ts` | TS module |
| **B-04** | CartIntakeHandler / CartDismissHandler / CartListHandler / PushTokenHandler | `backend/src/cart/handlers/` | Lambda × 4 |
| **B-05** | CartAttackScheduler（library） + cart_attack_scheduler_retry（Lambda） | `backend/src/cart/scheduler.py` + `backend/src/cart/handlers/cart_attack_scheduler_retry.py` | Library + Lambda |
| **B-06** | NotificationDispatcher + notification_templates | `backend/src/cart/handlers/notification_dispatcher.py` + `backend/src/cart/notification_templates.py` | Lambda |
| **S-03 拡張** | `evaluate_notification`（decide_allow ラッパー、本 Unit が owner） | `shared/safeguard-policy/{src,python}/` 既存ファイルへ追記 | Library |
| **Repo** | CartWatchItemsRepo / NotificationLogsRepo | `backend/src/cart/repository.py` | Repository |
| **Infra** | cart-stack（CDK） | `infra/lib/cart-stack.ts` | CDK Stack |

> **MVP スコープ方針（Plan v3 確定値継承）**:
>
> - 本 Code Generation は「コードと単体/PBT テストの生成」までを行う。テスト実行とデプロイは Build and Test ステージ
> - クリップボード検知（US-03-03）は [backlog B-502](../../../doc/backlog.md) で MVP 見送り、Code Generation 対象外
> - LLM 通知コピー（FR-CART-03 拡張）は [backlog B-501](../../../doc/backlog.md) で決勝向け、本 Code Generation はテンプレートベースのみ
> - APNs Production cert は [backlog B-504](../../../doc/backlog.md) で決勝 2 週間前まで、dev は Sandbox cert で進行
> - Amazon Approved Mobile Application 申請待ちは [backlog B-503](../../../doc/backlog.md) でダミーカタログ fallback 維持
>
> **Member A への合意プロセス（Stage 2 ブロッカー、§8.1 / §8.2）**:
>
> - PlatformStack 7 項目追実装（kmsKey public 化 / IdempotencyKeysTable / IdempotencyBucket / DebateRateLimitsTable / alertTopic public 化 / developerInitial props / with_idempotency middleware）が PR `#platform-additions-001` で 5/29 18:00 までに merge される前提
> - 期限超過時は §8.2 代替案 B（CartStack 内一時実装）に切替

## 0.5 v1 → v2 → v3 改訂ログ（2026-05-29 再レビュー反映）

### v1 → v2（6 件）

Plan v1 を批判的再検証し、main 由来の `mobile/package.json` / `infra/package.json` / `backend/pyproject.toml` の実コード状態と突き合わせて 6 件の Issue を検出。v2 で全件反映。

| Issue | 重大度 | 検出内容 | v2 修正方針 |
|---|---|---|---|
| **R1** | 重大 | `mobile/package.json` に `react`, `react-native`, `expo`, `expo-notifications`, `react-navigation`, `uuid`, `@types/uuid`, `@testing-library/react-native` がすべて未追加 | **Mobile UI 結線を本 Plan 対象外に格下げ**（Unit-1 M-01 AppShell スタンス継承）。`uuid ^11.0.0` + `@types/uuid ^10.0.0` のみ最小追加、CartInterceptScreen.tsx は実機統合時に延期、純粋関数 / Hook ロジック / Adapter インターフェース型のみ生成 |
| **R2** | 誤検出 | CDK の `aws-pinpoint` / `aws-scheduler` / `aws-sns` 等の追加依存要否 | **追加不要**（aws-cdk-lib ^2.170.0 monorepo に全て含まれる）。Step 23 に「import パス正確性確認」のチェックを追加 |
| **R3** | 重大 | Step 20 で `@testing-library/react-native` を使う前提だが現状未整備 | R1 と統合、UI コンポーネントテスト不要（純粋関数テストのみ）|
| **R4** | 中 | Step 23 の Lambda Code asset bundling が Docker 起動を要求し CI 時間増 | bundling 簡素化方針確定: `lambda.Code.fromAsset('../backend/src/cart')` 直接参照、Layer 不使用 |
| **R5** | 軽微 | SchedulerInvokeRole の Confused Deputy 防御が SourceAccount のみ（SourceArn 抜け）| Trust Policy に SourceAccount + SourceArn 両方を含める（functional-design.md §3.1 整合）|
| **R6** | 軽微 | `responses` dev dep 追加の version 指定なし | `responses ^0.25.0` で明示 |

### v2 → v3（5 件、観点: ストーリー充足性 + 並列開発リスク + コード生成順序）

| Issue | 重大度 | 検出内容 | v3 修正方針 |
|---|---|---|---|
| **R7** | 重大 | v2 で Mobile UI 結線をスコープ外にしたが、US-03-01〜05 の AC（取込アニメ / navigate / Toast / Amazon ボタン）は UI 必須で、予選 5/30 デモが Backend 擬似デモになるリスク | Step 19 の `cart-intercept-screen-state.ts` を強化、UI 不要部分の状態管理ロジック（タイムライン進捗計算 / 楽観的更新 rollback / 警告アイコン判定）を完全純粋関数化。`unit-5-code-summary.md` に Mobile UI 結線スケジュール（Day 4-5）を明示し、Member D が Code Generation 完了後即座に UI 結線開始できる準備状態にする |
| **R8** | 中 | Step 9 が Unit-1 IdempotencyKeys 未整備時に import エラーで停止リスク | Step 9 に「Option C: with_idempotency 呼出をコメントアウト + TODO コメント、§8.1 PR `#platform-additions-001` merge 後に有効化」を明記 |
| R9 | 中 | Step 23 → Step 24 の順序が Snapshot TDD の Red-First と不整合 | Step 24 に「Snapshot TDD 4 段階（hasResourceProperties → Stack 実装追加 → Refactor → toMatchSnapshot）を 1 コミットに収める方針」をコメント追加。Unit-1 §18-19 と同一スタンス維持 |
| **R10** | 軽微 | uuid library の TS / Python 整合性 | Step 2 に「Python 側は標準 uuid モジュール使用、追加依存不要」明記 |
| **R11** | 軽微 | `mobile/src/test/msw-handlers.ts` 追加が OpenAPI examples と二重管理になる | Step 25 に「`shared/schema/examples/cart.yaml` 生成」を追加（api-contracts.md §7.1 / Prism Mock Server 連携）|

**v3 確定方針**: 選択肢 A（純粋ロジックのみ、Unit-1 整合）+ Mobile UI 結線スケジュール明示 + Unit-1 IdempotencyKeys フォールバック対応。

---

### Step 1: Backend ディレクトリ雛形 + 既存パターン継承
- [x] `backend/src/cart/__init__.py` / `backend/src/cart/handlers/__init__.py` 作成
- [x] `backend/tests/cart/__init__.py` / `backend/tests/cart/conftest.py`（moto + DynamoDB Local fixture、Unit-1 `backend/conftest.py` パターンを継承）
- [x] **2026-05-29 v2 修正（Issue R6 対応）**: `backend/pyproject.toml` の dev dep に `responses ^0.25.0` を追加（既存 `moto ^5.0.0` / `hypothesis ^6.122.0` / `pytest-cov ^6.0.0` / `schemathesis ^3.39.0` は維持）
- ドキュメント: `aidlc-docs/construction/unit-5-cart-intercept/code/structure-setup.md`

### Step 2: Mobile ディレクトリ雛形 + 最小依存追加（v2 改訂）
- [x] `mobile/src/features/cart/index.ts`（feature export 集約、Unit-1 既存 `mobile/src/features/platform/` パターン継承）
- [x] **2026-05-29 v2 修正（Issue R1 対応）**: `mobile/package.json` に最小限の dev dep のみ追加: **`uuid ^11.0.0` + `@types/uuid ^10.0.0`**（v7 / v5 ID 生成用）
- [x] **2026-05-29 v3 修正（Issue R10 対応）**: Backend Python 側は **標準 `uuid` モジュールのみ使用**（既存 backend/pyproject.toml の依存に追加なし）。Backend は Idempotency-Key ヘッダ値を検証だけする bypass 方式のため、`uuid` library を新規追加する必要なし
- [x] **Mobile UI 結線方針（v2 確定）**: Unit-1 M-01 AppShell の「純粋ロジックとして実装、UI 結線は実機統合時」スタンスを継承。本 Code Generation では **Mobile features は TypeScript の純粋関数 + Hook ロジックのみ生成**し、`CartInterceptScreen.tsx` の RN UI コンポーネント結線は実機統合時（Build and Test ステージ）に延期。expo-notifications / react-navigation / @testing-library/react-native の依存追加は本 Plan の対象外
- [x] **Expo Config Plugin スケルトンも本 Plan では対象外**（Mobile UI 結線時に Member D が実機 + iOS / Android Native 開発環境で着手）
- ストーリー: US-03-01 AC-1（Share Extension の入口 = ロジック層のみ）/ functional-design.md §1.2 Q1=A
- ドキュメント: `code/mobile-cart-structure.md`

### Step 3: Shared / S-03 SafeguardPolicy への `evaluate_notification` 追加（Unit-5 owner）
- [x] TS: `shared/safeguard-policy/src/decide-allow.ts` に `evaluateNotification(ctx: NotificationContext): SafeguardDecision` 追加（既存 `decideAllow` ラッパー）
- [x] TS: `shared/safeguard-policy/src/index.ts` に export 追加
- [x] Python: `shared/safeguard-policy/python/safeguard_policy.py` に `evaluate_notification(...)` 追加（同等仕様）
- [x] Python: `shared/safeguard-policy/python/__init__.py`（あれば）の export 追加
- ルール: SG-01〜10 維持 + cooldown_until 追加チェック + warn → block 格上げ（NG-6 配慮、SG-07 例外）
- 規約: api-contracts.md Shared 層変更ルール（Unit-7 owner Member C のレビュー必須、PR `#safeguard-001` で対応）

### Step 4: S-03 evaluate_notification 単体 + PBT テスト
- [x] TS: `shared/safeguard-policy/src/evaluate-notification.test.ts`（example: cooldown_until 未来 / cooldown_on / quiet_week / warn → block 格上げ各ケース + fast-check invariant: warn が必ず block にマッピングされる + cooldown_until 時刻判定の境界）
- [x] Python: `shared/safeguard-policy/python/test_evaluate_notification.py`（hypothesis 同等）
- [x] golden fixtures（TS / Python クロス言語一致、SG-10 維持）
- NFR: NFR-PBT-02（[functional-design.md §0.2 Property 5](../unit-5-cart-intercept/functional-design/functional-design.md#property-5-safeguard-連携での通知抑制) 担保）

### Step 5: Backend / B-04 CartWatchItemsRepo / NotificationLogsRepo（Repository 層）
- [x] `backend/src/cart/repository.py`（CartWatchItemsRepo: get / create / reactivate / transition_status / transition_to_dismissed / transition_to_purchased / count_active / update_attack_schedule、NotificationLogsRepo: create）
- [x] data-model.md §1.2 全属性 + §1.3 ステータスマシン ConditionExpression 厳密実装
- [x] data-model.md §1.4 GSI1 Sparse Index 化（dismissed/purchased で REMOVE GSI1PK）
- ルール: data-model.md §1〜§5 / `retry_count` 属性 / `watching_orphaned` 遷移ルール / TDD クラシック（Red → Green → Refactor → PBT）

### Step 6: B-04 Repository 単体 + PBT テスト
- [x] `backend/tests/cart/test_repository.py`（DynamoDB Local + moto、ステータスマシン全遷移パス + Stateful PBT-05: 任意の遷移シーケンスで ConditionExpression 不正遷移を全 reject + count_active < 100 invariant）
- NFR: NFR-PBT-05 / Property 1 / Property 6
- ドキュメント: `code/cart-repository-summary.md`

### Step 7: Backend / B-05 CartAttackScheduler（Library）
- [x] `backend/src/cart/scheduler.py`（schedule_attacks(user_id, item_id, asin, base_time): AttackSchedule + cancel_attacks(schedule: AttackSchedule)）
- [x] EventBridge Scheduler の One-time Schedule 形式（at(YYYY-MM-DDTHH:MM:SS)）+ Schedule 名 prefix `cart-attack-{user_hash}-{asin}-{base_ms}-{step}`（infrastructure-design.md §1.2、64 文字以内）
- [x] 部分失敗許容（NFR Design Q4=A'、3 件中 1 件成功でも CartWatchItem は維持）
- ルール: functional-design.md §2.2 / Property 2 時系列単調性

### Step 8: B-05 単体 + PBT テスト
- [x] `backend/tests/cart/test_scheduler.py`（moto Scheduler モック、3 件並列作成成功 / 1 件失敗時の挙動 + PBT-02 Invariant: 任意 createdAt で 30m/6h/24h ジョブが時系列整合 + PBT-03 Inverse: schedule_attacks → cancel_attacks で 0 件）
- NFR: NFR-PBT-02 / NFR-PBT-03

### Step 9: Backend / B-04 CartIntakeHandler（Lambda 1）
- [x] `backend/src/cart/handlers/cart_intake.py`（functional-design.md §2.1 全実装: with_idempotency middleware → ASIN 再検証（AsinResult 判別ユニオン）→ 既存登録チェック / dismissed→watching 再活性化 → Creators API → DDB PutItem → schedule_attacks 同期呼出 → metric / log）
- [x] **2026-05-29 v3 修正（Issue R8 対応）**: Unit-1 IdempotencyKeys 未整備時のフォールバック方針確定。`from common.idempotency import with_idempotency` の import 行と `@with_idempotency` デコレータ適用を **TODO コメント形式で記述**（コメントアウト + `# TODO(unit-1-platform-additions-001): Member A の PR #platform-additions-001 merge 後に有効化` を併記）。本 Lambda の実装ロジックは完全に書き、Idempotency-Key ヘッダの抽出も `event["headers"].get("Idempotency-Key")` で取得しておくが、middleware なしでは duplicate detection は効かない状態で生成。同 Plan 完了後、Member A 整備完了次第コメント解除して有効化
- [x] Pydantic v2 リクエスト/レスポンスモデル（`CartIntakeRequest` / `CartIntakeResponse`、shared/schema/paths/cart.yaml 整合）
- [x] AuditLogger クラスベース呼び出し（`audit = AuditLogger(service="cart-intake")`）
- ルール: functional-design.md §2.1 / Q2=A 二段検証 / SECURITY-05 / Property 1 二重防御 / Property 6 件数上限

### Step 10: B-04 CartIntakeHandler 単体 + PBT テスト
- [x] `backend/tests/cart/test_cart_intake.py`（example: 正常 ASIN / Mobile Backend ASIN 不一致 / 既存 watching / 既存 dismissed 再活性化 / Creators API 404 / 100 件超過 429 + PBT-04 Idempotency: 同 Idempotency-Key で N 回 POST → 副作用 1 回 + PBT-08-local: ロジック単体 latency < 100ms）
- NFR: NFR-PBT-04 / NFR-PBT-08-local

### Step 11: Backend / B-04 CartDismissHandler / CartListHandler / PushTokenHandler（Lambda 3）
- [x] `backend/src/cart/handlers/cart_dismiss.py`（functional-design.md §2.1.1 / 残追撃 cancel_attacks → transition_to_dismissed）
- [x] `backend/src/cart/handlers/cart_list.py`（GET 一覧 + cursor pagination + status filter / GET 単一 = SK CART#{asin} 直接 GetItem）
- [x] `backend/src/cart/handlers/push_token.py`（functional-design.md §1.3 / End User Messaging UpdateEndpoint + Users.pushEndpointId 更新）
- [x] 各 Lambda に AuditLogger インスタンス初期化

### Step 12: B-04 残 3 Handler 単体テスト
- [x] `backend/tests/cart/test_cart_dismiss.py`（dismissed/purchased 冪等返却 + PBT-03 Inverse 補完）
- [x] `backend/tests/cart/test_cart_list.py`（cursor pagination invariant + status filter）
- [x] `backend/tests/cart/test_push_token.py`（同 token 再 POST で UpdateEndpoint 1 回のみ呼ばれる）
- ドキュメント: `code/cart-handlers-summary.md`

### Step 13: Backend / B-06 NotificationDispatcher + 30 通知テンプレート
- [x] `backend/src/cart/notification_templates.py`（30 パターン静的辞書: 30m × 10 + 6h × 10 + 24h × 10、商品名 / 価格 / ユーザー名 placeholder）
- [x] `backend/src/cart/handlers/notification_dispatcher.py`（functional-design.md §2.3 全実装: GetItem(asin) → status check → SafeguardStates 取得 → evaluate_notification → block ならログのみ → allow なら template 選択 → SendMessages → NotificationLogs PutItem → transition_status notified-{step}）
- [x] AuditLogger インスタンス初期化
- ルール: functional-design.md §2.3 / Q3=A テンプレートベース / Property 5 通知抑制

### Step 14: B-06 単体 + PBT テスト
- [x] `backend/tests/cart/test_notification_dispatcher.py`（example: status=watching → 30m 通知成功 / status=dismissed → スキップ / safeguard block → suppressed_by_safeguard log / EUM 失敗 → failed log + PBT-06 Metamorphic: 同 step + 同 productMeta + 同 user_name で N 回呼んでも 10 パターン内 + PBT-09 Output Moderation: 任意テンプレート × 商品メタで NG-6 キーワード辞書非含有）
- NFR: NFR-PBT-06 / NFR-PBT-09 / Property 4 / Property 5

### Step 15: Backend / B-05 cart_attack_scheduler_retry Lambda（NEW、NFR Q4=A'）
- [x] `backend/src/cart/handlers/cart_attack_scheduler_retry.py`（GSI1 Query で attackSchedule 不完全 watching アイテム抽出 → schedule_attacks 再実行 / 成功 retry_count=0 / 失敗 retry_count++ / 3 回失敗で transition_status(watching → watching_orphaned) + Alarm 5 累積）
- [x] AuditLogger インスタンス初期化
- ルール: nfr-design-patterns.md §1.2 リトライバッチ / sequence-diagrams.md §7

### Step 16: B-05 retry Lambda 単体テスト
- [x] `backend/tests/cart/test_cart_attack_scheduler_retry.py`（moto: 3 連続失敗で `watching_orphaned` 遷移検証 + 成功時 retry_count=0 リセット + 100 件超過時の逐次処理）

### Step 17: Mobile / M-08 ShareExtensionNativeModule（v2 改訂、純粋ロジック層のみ）
- [x] **2026-05-29 v2 修正（Issue R1 対応）**: 本 Code Generation では Native Module の **TypeScript Bridge ロジックのみ**を生成。iOS Swift / Android Kotlin / Expo Config Plugin の Native コードは実機統合時（Build and Test ステージ後）に Member D が iOS / Android 開発環境で着手
- [x] `mobile/src/features/cart/share-extension-module.ts`（NativeEventEmitter wrapper の TS インターフェース定義 + onUrlShared / consumePendingUrl の純粋ロジック関数、実体 Native 側は `NativeModules.ShareExtensionModule` を後で結線）
- [x] `mobile/src/features/cart/use-share-intake.ts`（M-08 イベント購読 + AsinResult 判別ユニオン処理 + Toast 通知の純粋ロジック）
- ルール: functional-design.md §1.2 / Q1=A / iOS App Group / Android Intent（コメントで Native 側仕様明記）

### Step 18: M-08 単体テスト
- [x] `mobile/src/features/cart/share-extension-module.test.ts`（vitest + NativeEventEmitter モック、起動時 consume + URL イベント受信 + ASIN 抽出失敗時の Toast、純粋ロジック層のテストのみ）
- [x] `mobile/src/features/cart/use-share-intake.test.ts`（vitest、AsinResult 判別ユニオンの分岐網羅 + PBT-07 Domain Generator: 任意 URL での extract_asin 出力検証）
- ドキュメント: `code/share-extension-module-summary.md`

### Step 19: Mobile / M-05 use-* hooks（v2 改訂、TypeScript 純粋ロジックのみ）
- [x] **2026-05-29 v2 修正（Issue R1 / R3 対応）**: `CartInterceptScreen.tsx` の React Native UI 結線は本 Code Generation 対象外（Unit-1 M-01 AppShell スタンス継承）
- [x] **2026-05-29 v3 修正（Issue R7 対応）**: Member D が Day 4-5 に UI 結線するときに**ロジック側を一切書き直さなくて済む状態**にするため、UI 不要部分の状態管理を完全純粋関数化:
  - タイムライン進捗計算（`computeTimelineProgress(item: CartWatchItemDto, now: Date): { step: '30m'|'6h'|'24h'|'completed', remainingSec: number, isCurrentStep: boolean }`）
  - 楽観的更新 rollback ロジック（`applyOptimisticDismiss / rollbackOptimisticDismiss`）
  - 警告アイコン表示判定（`shouldShowOrphanedWarning(status: string): boolean`）
  - Associates 開示文言定数（`ASSOCIATES_DISCLOSURE_TEXT: string`）
  - Reduce Motion 判定純粋関数（`getAnimationConfig(reduceMotion: boolean): { duration: number, easing: string }`）
- [x] `mobile/src/features/cart/use-cart-watch-item.ts`（useQuery、staleTime=0 詳細）
- [x] `mobile/src/features/cart/use-cart-watch-items.ts`（useQuery、staleTime=60000 一覧）
- [x] `mobile/src/features/cart/use-cart-intake.ts`（useMutation + uuidv7 idempotencyKey）
- [x] `mobile/src/features/cart/use-cart-dismiss.ts`（useMutation + 楽観的更新）
- [x] **CartInterceptScreen.tsx は実機統合時に書く**ため本 Plan ではスキップ。代わりに `mobile/src/features/cart/cart-intercept-screen-state.ts`（画面状態の純粋ロジック完全版: 上記 5 関数 + mode 判定 / watching_orphaned 検知 + 型定義の集約）を生成
- ルール: functional-design.md §1.1 / NFR Design Q2=A' staleTime 階層化 / Issue LLLL watching_orphaned 可視化（純粋ロジックでの判定のみ）

### Step 20: M-05 hooks 単体 + PBT テスト
- [x] `use-cart-*.test.ts`（vitest + MSW、各 hook の queryFn / mutationFn 動作）
- [x] `cart-intercept-screen-state.test.ts`（mode 判定 / watching_orphaned 警告判定 / Reduce Motion 純粋関数のテスト）
- ドキュメント: `code/cart-screen-state-summary.md`

### Step 21: Mobile / M-09 PushNotificationHandler（v2 改訂、TypeScript ロジックのみ）
- [x] **2026-05-29 v2 修正（Issue R1 対応）**: 本 Code Generation では `expo-notifications` 依存追加は対象外。代わりに **`PushNotificationsAdapter` インターフェース型を定義** + 純粋ロジック関数のみ生成（実体は実機統合時に Member D が `expo-notifications` を `mobile/package.json` に追加して結線）
- [x] `mobile/src/features/cart/push-notification-handler.ts`（PushPayload validate + cart-attack-* 判定 + navigate 遷移先決定の純粋関数、Property 3 productId 不正時 fallback ロジック）
- [x] `mobile/src/features/cart/push-notification-types.ts`（PushPayload / PushPermissionState / PushTokenRotation 等の型定義のみ）
- ルール: functional-design.md §1.3 / Q5=C / Q7=A / Property 3 productId 不正時 fallback

### Step 22: M-09 単体 + PBT テスト
- [x] `push-notification-handler.test.ts`（PushPayload validate / Deep Link payload PBT-01 Round-trip: decode(encode(payload)) === payload / cart-attack-* 判定の境界）
- NFR: NFR-PBT-01 / Property 3
- ドキュメント: `code/push-notification-summary.md`

### Step 23: Infra / cart-stack（CDK、v2 改訂で bundling 簡素化方針確定）
- [x] **2026-05-29 v2 修正（Issue R4 対応）**: Lambda Code asset path は **`lambda.Code.fromAsset('../backend/src/cart')` 直接参照 + Layer 不使用 + poetry export なしの単純 zip bundle**（Unit-1 platform-stack の Lambda 配置パターンと整合、Docker bundling 起動を回避）。本格的な poetry path dependencies 同梱は **Build and Test ステージで CI を整備する際に判断**
- [x] **2026-05-29 v2 修正（Issue R2 対応）**: import パス正確性確認: `aws-cdk-lib/aws-pinpoint` / `aws-cdk-lib/aws-scheduler` / `aws-cdk-lib/aws-sns` / `aws-cdk-lib/aws-sns-subscriptions` / `aws-cdk-lib/aws-secretsmanager` / `aws-cdk-lib/aws-cloudwatch-actions` がすべて aws-cdk-lib ^2.170.0 で利用可能
- [x] **2026-05-29 v2 修正（Issue R5 対応）**: SchedulerInvokeRole の Trust Policy に **`StringEquals: aws:SourceAccount` + `ArnLike: aws:SourceArn = arn:aws:scheduler:...:schedule/default/cart-*`** の **両方** を含める（functional-design.md §3.1 / Confused Deputy 防御強化）
- [x] `infra/lib/cart-stack.ts`（infrastructure-design.md §0/§1/§2/§3/§4/§5/§6/§7/§8 全実装）
  - DDB CartWatchItems / NotificationLogs（KMS / TTL / GSI1 / PITR=prd / RemovalPolicy=prd:RETAIN / DeletionProtection=prd）
  - 6 Lambda（cart_intake / cart_dismiss / cart_list / push_token / notification_dispatcher / cart_attack_scheduler_retry）+ SnapStart 3 関数 + Reserved Concurrency
  - EventBridge Scheduler default Group + cart_attack_scheduler_retry の rate(15min) Schedule + SchedulerInvokeRole（Confused Deputy 対策、SourceAccount + SourceArn）
  - End User Messaging Application × 環境別 + APNs Sandbox/Production / FCM Channel + SSM Parameter
  - cartAlertTopic（KMS）+ Slack Bridge Lambda + Secrets Manager Slack Webhook 参照
  - CloudWatch Alarms 5 系統
  - 必須 4 タグ（Environment / Unit / Owner / CostCenter）
  - cdk-nag suppressions 4 件（infrastructure-design.md §7）
- [x] `infra/bin/app.ts` に `CartStack` インスタンス追加（dev / prd の 2 環境 + 個人 sandbox は context で分岐）。Stack 名 = `cart-{env}-stack` または `cart-dev-{init}-stack`
- ルール: infrastructure-design.md / shared-infrastructure.md §3 全規約

### Step 24: cart-stack スナップショットテスト
- [x] **2026-05-29 v3 修正（Issue R9 対応）**: Snapshot TDD 4 段階（[tech-cdk.md §6.1](../../../.kiro/steering/tech-cdk.md#61-snapshot-tdd-cdk-必須)）の運用方針を以下に明確化:
  - **Phase 1 (Red)**: Step 23 と並走で `template.hasResourceProperties` を最小 1 リソースで先に書く（Stack 未実装時は当然失敗）
  - **Phase 2 (Green)**: Step 23 の Stack 実装で assertion 通過
  - **Phase 3 (Refactor)**: KMS / TTL / IAM / Tag 細目を整理、テストは触らない
  - **Phase 4 (Snapshot 固定)**: cdk-nag pass を確認の上で `toMatchSnapshot()` で全体 fixture 化
  - 1 PR / 1 commit 内に Phase 1〜4 を含めるか分割するかは PR 段階で判断（Unit-1 §18-19 と同一スタンス、Snapshot Test の Red-First 原則は守りつつ実装は連続的に進める）
- [x] `infra/test/cart-stack.test.ts`（vitest CDK assertions + cdk-nag アサート、Snapshot TDD）
  - DDB CartWatchItems / NotificationLogs の `hasResourceProperties` 検証（PartitionKey / SortKey / GSI1 / KMS encryption）
  - 6 Lambda の `hasResourceProperties` 検証 + SnapStart 3 関数の SnapStartConfig 検証
  - EventBridge Schedule リソース存在検証（rate(15 minutes) Schedule + SchedulerInvokeRole の Confused Deputy 条件）
  - cdk-nag pass（4 件 suppression のみ許可）
  - Tag が必須 4 タグすべて付与されていることを検証
- ルール: tech-cdk.md §6.1 Snapshot TDD / functional-design.md §0.1 TDD 適用方針
- ドキュメント: `code/cart-stack-summary.md`

### Step 25: ドキュメント + CI 雛形拡張 + 仕上げ
- [x] `aidlc-docs/construction/unit-5-cart-intercept/code/unit-5-code-summary.md`（全コンポーネント総括 + 生成ファイル一覧 + ストーリー実装状況 + Mobile UI 結線スコープ外の旨を明記）
- [x] **2026-05-29 v3 修正（Issue R7 対応）**: `unit-5-code-summary.md` に **「Mobile UI 結線スケジュール」** セクションを新設（Day 4-5 = 5/31 〜 6/2）。Member D が Code Generation 完了後すぐに UI 結線着手するためのチェックリスト + 必要な追加依存リスト（react / react-native / expo / expo-notifications / @react-navigation/native / @testing-library/react-native）+ 純粋ロジック層（cart-intercept-screen-state.ts 等）への依存方法を明記
- [x] `.github/workflows/ci.yml` への Unit-5 テストジョブ追加（既存 jobs に cart テスト追加、coverage 閾値継承）
- [x] `.github/workflows/deploy-dev.yml` に `cdk-deploy-cart-dev` ジョブ追加（infrastructure-design.md / deployment-architecture.md §3.2、`needs: cdk-deploy-safeguard-dev`）
- [x] `scripts/check-ng-keywords.sh`（NG-6 静的検証、Property 4、CI integration）
- [x] `mobile/src/test/msw-handlers.ts` に Cart 関連 examples ハンドラ追加
- [x] **2026-05-29 v3 修正（Issue R11 対応）**: `shared/schema/examples/cart.yaml` を生成（api-contracts.md §7.1 / Prism Mock Server で `npm run mock:api` から参照される）。CartWatchItemDto / CartIntakeResponse / PushTokenResponse の各 examples を、shared/schema/paths/cart.yaml の `examples` セクションと整合させる
- [x] aidlc-state.md / 本プランのチェックボックス最終更新
- 規約: api-contracts.md §7 Mock Server / Property 4 NG-6

---

## 2. ストーリートレーサビリティ

| Story | 担当 Step | 受入条件カバー |
|---|---|---|
| **US-03-01** Share 受信 → 監視登録 | Step 2, 17, 19 (M-08, M-05), Step 9, 10 (B-04 intake) | AC-1〜5（Share Extension / 即時抽出 / 2 秒以内取込 / 重複排除 / 不正 URL Toast）|
| **US-03-02** 30m/6h/24h 追撃通知 | Step 7, 8, 13, 14, 15, 16 (B-05, B-06, retry batch), Step 21, 22 (M-09) | AC-1〜5（時系列正確性 / タップ → 論破 / 「いらない」キャンセル / Safeguard 抑制 / 無視時 24h で停止）|
| **US-03-03** クリップボード検知 | **対象外**（[backlog B-502](../../../doc/backlog.md) で MVP 見送り） | — |
| **US-03-04** Amazon 遷移 | Step 19 (M-05 「Amazon で買う」ボタン + 遷移確認オーバーレイ + Associates 開示) | AC-1〜5（Special Link 起動 / 開示文言常時表示 / EXP 加算 / ダメ化レポート遷移 / 短縮 URL 不採用）|
| **US-03-05** Safeguard 連動 | Step 3, 4 (S-03 evaluate_notification), Step 13 (B-06 通知抑制) | AC-1〜4（月間上限到達時 block / 冷却モード時 block / 静かな週 block / Cart 側 409 表示）|

## 3. 依存・インターフェース

### 上流依存（本 Code Generation の前提）

| 依存先 | 依存内容 | 状態 |
|---|---|---|
| **Unit-1 PlatformStack** | kmsKey public 化 / IdempotencyKeysTable / IdempotencyBucket / DebateRateLimitsTable / alertTopic public 化 / developerInitial props / with_idempotency middleware | **未実装、Member A 依頼中**（PR `#platform-additions-001`、5/29 18:00 期限）|
| Unit-1 ApiClient + apiFetch ヘルパー | mobile features から `import { apiFetch } from '@yudane/api-client'` で利用 | ✅ 整備済（B3 修正で api-fetch.ts 新規追加） |
| Unit-1 AuditLogger | `from backend.src.common.logging import AuditLogger` でクラスインスタンス化 | ✅ 整備済 |
| Unit-1 AsinExtractor | `extract_asin(url)` が AsinResult 判別ユニオンを返す | ✅ 整備済 |
| Unit-1 SafeguardPolicy | `decide_allow` ベース / Step 3 で `evaluate_notification` を本 Unit が追加 | ✅ ベース整備済、本 Unit が拡張 |
| Unit-1 telemetry-contracts | Cart 関連 Events 11 件 + Metrics 9 件 + Fields 8 件 | ✅ 整備済（B4 修正で追加済） |
| Unit-2 Cognito JWT | API Gateway Authorizer で sub 取得 | Pending（Unit-2 Functional Design 後） |
| Unit-2 Users.pushEndpointId | push_token Lambda が更新 | Pending（PR `#auth-002` 依頼中） |
| Unit-3 POST /v1/debate-sessions | 通知タップ → 論破モード遷移 | Pending（Unit-3 progress 中） |
| Unit-4 B-11 CreatorsApiClient | cart_intake が import | Pending（ダミーカタログ fallback で進行可能、§8 A-10）|
| Unit-4 B-13 AmazonTransitionRecorder | M-05 から POST | Pending |
| Unit-7 SafeguardStates / Lambda Authorizer | B-06 が GetItem / Authorizer から context 受信 | Pending（PR `#safeguard-001` 依頼中） |

### 下流提供（本 Unit が他 Unit に提供）

- OpenAPI cart paths（既整備、shared/schema/paths/cart.yaml）
- shared/safeguard-policy への `evaluate_notification` 関数（Unit-7 Member C レビュー必須）
- Cart 関連 telemetry 識別子（既追加）
- cart-stack の SSM Parameter（CartWatchItemsTableArn / NotificationLogsTableArn / EumApplicationId / AlertTopicArn）

### Mock 駆動の並行開発戦略

[functional-design.md §7](../unit-5-cart-intercept/functional-design/functional-design.md#7-並行開発の-mock-提供方針stage-12) の Mock 戦略を継承。pending 依存先は以下で代替:

- Unit-2 Users → `backend/tests/cart/fixtures/users.py` の Mock User
- Unit-3 / Unit-4 / Unit-7 API → Prism Mock Server（5/29 OpenAPI 第 1 版凍結後）
- Unit-4 B-11 → `backend/src/cart/_dummy_catalog.py`（B-503 backlog で削除候補）

## 4. TDD 開発スタイル（[AGENTS.md §12](../../../.kiro/steering/AGENTS.md#12-tdd-開発スタイル全-unit-必須) 準拠）

各 Step は **Red → Green → Refactor → PBT 補強** の 4 フェーズサイクルで実施:

| 領域 | 主スタイル | 適用 Step |
|---|---|---|
| Mobile features (`mobile/src/features/cart/`) | **Outside-In TDD** | Step 17, 19, 21（テスト先 → 実装後追い） |
| Backend Lambda (`backend/src/cart/`) | **クラシック TDD（Detroit）** | Step 5, 7, 9, 11, 13, 15（最小単位 example test → 実装最小コード → Refactor → PBT 補強） |
| Shared library (`shared/safeguard-policy/`) | **クラシック TDD** | Step 3 |
| CDK Infra (`infra/lib/cart-stack.ts`) | **Snapshot TDD** | Step 23 |

### TDD 例外（[AGENTS.md §12.3](../../../.kiro/steering/AGENTS.md#123-tdd-例外テストファースト強制を緩和論点-5)）

以下は Green を先に書くことを許容（PR description で「TDD 例外: ◯◯」明記）:

- Step 13 通知テンプレート 30 件の静的辞書定義（純粋宣言）
- Step 17 Expo Config Plugin の iOS Swift / Android Kotlin template（mockup の機械的移植部分、`mockup/index.html` L193-L268）
- Step 23 cdk.context.json / bin/app.ts の宣言的設定

## 5. 完了基準

- [x] Step 1〜25 すべて [x]
- [x] コードと単体/PBT テストが生成済み（実行は Build and Test ステージ）
- [x] cart-stack が cdk synth 可能な状態（デプロイは承認後）
- [x] 6 Lambda + 30 通知テンプレート + ステータスマシン Repository 完成
- [x] 生成ドキュメントが `aidlc-docs/construction/unit-5-cart-intercept/code/` に揃う
- [x] OpenAPI cart paths と実装の整合（Schemathesis 通過想定、実行は Build and Test）

## 6. スコープ外（後続）

- テスト実行・カバレッジ計測・cdk deploy → **Build and Test ステージ**
- クリップボード検知（US-03-03） → [backlog B-502](../../../doc/backlog.md) 決勝向け
- LLM 通知コピー（FR-CART-03 拡張） → [backlog B-501](../../../doc/backlog.md) 決勝向け
- ダミーカタログ削除 → [backlog B-503](../../../doc/backlog.md) Approved Mobile Application 申請後
- APNs Production cert 取得 → [backlog B-504](../../../doc/backlog.md) 決勝 2 週間前
- 実機 Push 配信検証 / E2E-03 シナリオ実行 → Build and Test / 予選 rehearsal
- アクセシビリティ実機検証（VoiceOver / TalkBack） → Day 5（[NFR Requirements §7.3](../unit-5-cart-intercept/nfr-requirements/nfr-requirements.md)）

## 7. ハッカソン書類審査・予選評価軸へのインパクト

| 評価軸 | 本 Plan の貢献 |
|---|---|
| Unit 分解の適切さ | **強化**: 25 Step 構成で Mobile / Backend / Shared / Infra の責務を明示、Story Traceability マトリクスで 5 ストーリー × Step 対応を可視化 |
| 創造性とテーマ適合性 | **強化**: 30 通知テンプレート + Property 4 NG-6 静的検証 + ステータスマシン + watching_orphaned 警告アイコンで 3 段追撃の物語性を実装 |
| ドキュメント品質 | **強化**: TDD 適用方針（Outside-In / クラシック / Snapshot のハイブリッド）+ Mock 駆動並行開発戦略 + 依存・インターフェース表で Code Generation の根拠を明示 |
| AI-DLC プロセス（予選評価軸） | **強化**: Per-Unit Loop の Code Generation を Unit-1 と同一テンプレートで実施、後続 Unit（Unit-2/3/4/6/7/8）の参考形 |
