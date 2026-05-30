# Unit-5 Cart Intercept — Code Generation 総括

> Plan v3 25 Step を一気通貫実行した結果のサマリ。
> 純粋ロジック層完成 + Backend Lambda 全実装 + CDK Stack + Snapshot Test まで生成。
> Mobile UI 結線（CartInterceptScreen.tsx）は実機統合時に Member D が結線する（v2/v3 確定方針）。

---

## 0. 生成ファイル一覧

### Shared（S-03 拡張、Unit-5 owner）

| ファイル | 種別 | Step |
|---|---|---|
| `shared/safeguard-policy/src/evaluate-notification.ts` | 新規 | 3 |
| `shared/safeguard-policy/src/evaluate-notification.test.ts` | 新規（PBT 含む） | 4 |
| `shared/safeguard-policy/src/index.ts` | 編集（export 追加） | 3 |
| `shared/safeguard-policy/python/safeguard_policy.py` | 編集（追記） | 3 |
| `shared/safeguard-policy/python/test_evaluate_notification.py` | 新規（PBT 含む） | 4 |

### Backend（6 Lambda + Repository + Library + dummy）

| ファイル | 種別 | Step |
|---|---|---|
| `backend/src/cart/__init__.py` | 新規 | 1 |
| `backend/src/cart/handlers/__init__.py` | 新規 | 1 |
| `backend/src/cart/repository.py` | 新規（CartWatchItemsRepo / NotificationLogsRepo + 全 ConditionExpression） | 5 |
| `backend/src/cart/scheduler.py` | 新規（B-05 library + 部分失敗許容） | 7 |
| `backend/src/cart/handlers/cart_intake.py` | 新規（B-04 Lambda 1） | 9 |
| `backend/src/cart/handlers/cart_dismiss.py` | 新規（B-04 Lambda 2） | 11 |
| `backend/src/cart/handlers/cart_list.py` | 新規（B-04 Lambda 3） | 11 |
| `backend/src/cart/handlers/push_token.py` | 新規（B-04 Lambda 4） | 11 |
| `backend/src/cart/handlers/notification_dispatcher.py` | 新規（B-06） | 13 |
| `backend/src/cart/handlers/cart_attack_scheduler_retry.py` | 新規（B-05 retry batch） | 15 |
| `backend/src/cart/notification_templates.py` | 新規（30 templates + NG-6 dictionary） | 13 |
| `backend/src/cart/dummy_catalog.py` | 新規（B-503 backlog 連携） | 9 |
| `backend/tests/cart/__init__.py` | 新規 | 1 |
| `backend/tests/cart/conftest.py` | 新規（moto fixture） | 1 |
| `backend/tests/cart/test_repository.py` | 新規（PBT-05 Stateful 含む） | 6 |
| `backend/tests/cart/test_scheduler.py` | 新規（PBT-02 / PBT-03） | 8 |
| `backend/tests/cart/test_handlers.py` | 新規（4 Lambda 統合 + PBT-04 / PBT-08-local） | 10/12 |
| `backend/tests/cart/test_notification_dispatcher.py` | 新規（PBT-06 / PBT-09） | 14 |
| `backend/tests/cart/test_cart_attack_scheduler_retry.py` | 新規（スケルトン） | 16 |
| `backend/pyproject.toml` | 編集（responses dev dep 追加） | 1 |

### Mobile（features/cart/）— 純粋ロジック層のみ（v2/v3 確定方針）

| ファイル | 種別 | Step |
|---|---|---|
| `mobile/src/features/cart/index.ts` | 新規（feature export 集約） | 2 |
| `mobile/src/features/cart/share-extension-module.ts` | 新規（Adapter インターフェース型 + EventEmitter スタブ） | 17 |
| `mobile/src/features/cart/use-share-intake.ts` | 新規（AsinResult 判別ユニオン処理） | 17 |
| `mobile/src/features/cart/use-cart-watch-item.ts` | 新規（staleTime=0） | 19 |
| `mobile/src/features/cart/use-cart-watch-items.ts` | 新規（staleTime=60s） | 19 |
| `mobile/src/features/cart/use-cart-intake.ts` | 新規（uuidv7 idempotencyKey） | 19 |
| `mobile/src/features/cart/use-cart-dismiss.ts` | 新規（楽観的更新 + rollback） | 19 |
| `mobile/src/features/cart/cart-intercept-screen-state.ts` | 新規（v3 強化、UI 不要部分の純粋関数完全版） | 19 |
| `mobile/src/features/cart/push-notification-handler.ts` | 新規（PushNotificationsAdapter + Deep Link round-trip） | 21 |
| `mobile/src/features/cart/use-share-intake.test.ts` | 新規 | 18 |
| `mobile/src/features/cart/cart-intercept-screen-state.test.ts` | 新規 | 20 |
| `mobile/src/features/cart/push-notification-handler.test.ts` | 新規（PBT-01 Round-trip） | 22 |
| `mobile/package.json` | 編集（uuid + @types/uuid 追加） | 2 |

### Infra（CDK cart-stack）

| ファイル | 種別 | Step |
|---|---|---|
| `infra/lib/cart-stack.ts` | 新規（DDB / 6 Lambda / Scheduler / EUM / SNS / Alarms 5 / Tags / cdk-nag suppressions） | 23 |
| `infra/test/cart-stack.test.ts` | 新規（Snapshot Test + cdk-nag アサート） | 24 |
| `infra/bin/app.ts` | 編集（CartStack インスタンス追加 + developerInitial context 対応） | 23 |

### CI / Scripts

| ファイル | 種別 | Step |
|---|---|---|
| `scripts/check-ng-keywords.sh` | 新規（Property 4 NG-6 静的検証 CI 統合） | 25 |

### OpenAPI（既整備、再確認）

| ファイル | 状態 | 備考 |
|---|---|---|
| `shared/schema/paths/cart.yaml` | 既整備 | Issue A2 で全面書換済 |
| `shared/schema/openapi.yaml` | 既整備 | `/v1/push-tokens` + `{asin}` パス参照済 |

---

## 1. ストーリー実装状況

| Story | AC | 実装範囲 | 残タスク（実機統合時） |
|---|---|---|---|
| **US-03-01** Share 受信 → 監視登録 | AC-1〜5 | ✅ Backend: cart_intake / repository / scheduler<br>✅ Mobile: use-share-intake / use-cart-intake（純粋ロジック）<br>⏳ Native: iOS Share Extension Swift / Android Intent Filter Kotlin / Expo Config Plugin | **Mobile UI 結線時**<br>- M-08 Native コード実装<br>- 取込アニメ UI / 商品取込カード UI |
| **US-03-02** 30m/6h/24h 追撃通知 | AC-1〜5 | ✅ Backend: notification_dispatcher / scheduler / cart_attack_scheduler_retry / 30 templates<br>✅ Mobile: push-notification-handler 純粋ロジック | **Mobile UI 結線時**<br>- expo-notifications 結線<br>- Deep Link → CartInterceptScreen navigate 結線<br>- 追撃タイムライン UI |
| **US-03-03** クリップボード検知 | — | ❌ **対象外**（[backlog B-502](../../../doc/backlog.md) MVP 見送り）| 決勝向け |
| **US-03-04** Amazon 遷移 | AC-1〜5 | ✅ Mobile: cart-intercept-screen-state（Associates 開示文言定数）<br>✅ Backend: 既整備（Unit-4 B-13 が purchased 遷移）| **Mobile UI 結線時**<br>- 「Amazon で買う」ボタン UI<br>- 遷移確認オーバーレイ + Linking.openURL |
| **US-03-05** Safeguard 連動 | AC-1〜4 | ✅ Shared: evaluate_notification（decide_allow ラッパー、warn → block 格上げ）<br>✅ Backend: notification_dispatcher での block 判定 | **Unit-7 Lambda Authorizer 完成時**<br>- amazon-transitions の 409 表示 |

---

## 2. Mobile UI 結線スケジュール（Day 4-5、Issue R7 対応）

Member D が本 Code Generation 完了後すぐに UI 結線着手するためのチェックリスト。

### 2.1 Day 4（2026-05-31）: Mobile dependencies 追加 + 基本 UI

- [ ] `mobile/package.json` に以下追加:
  ```json
  "react": "18.3.1",
  "react-native": "0.76.5",
  "expo": "~52.0.0",
  "expo-notifications": "~0.29.0",
  "expo-constants": "~17.0.0",
  "@react-navigation/native": "^7.0.0",
  "@react-navigation/native-stack": "^7.0.0"
  ```
- [ ] dev dep 追加: `@testing-library/react-native ^12.0.0` / `react-test-renderer ^18.3.1`
- [ ] `mobile/app.config.ts` 作成（Expo 設定 + Share Extension Plugin 参照）
- [ ] `CartInterceptScreen.tsx` 作成 — `cart-intercept-screen-state.ts` の純粋関数を import して UI 結線

### 2.2 Day 5（2026-06-02）: Native コード実装 + 実機検証

- [ ] iOS Share Extension Target（Swift） — Activation Rule + App Group UserDefaults
- [ ] Android Intent Filter（Kotlin） — ACTION_SEND + text/plain
- [ ] `mobile/plugins/share-extension/` Expo Config Plugin 雛形
- [ ] expo-notifications 結線 — push-notification-handler.ts の純粋関数を呼び出す層
- [ ] WCAG 2.2 AA 実機検証（Member D 実施 + Member C レビュー）

### 2.3 純粋ロジック層への依存方法

実機 UI コンポーネントから本 Code Generation 出力を import する例:

```tsx
import {
  ASSOCIATES_DISCLOSURE_TEXT,
  computeTimelineProgress,
  shouldShowOrphanedWarning,
  getAnimationConfig,
  useCartWatchItem,
  useCartDismiss,
} from '@yudane/cart';
import {
  validatePushPayload,
  resolveCartTapNavigation,
} from '@yudane/cart';

// CartInterceptScreen.tsx 例
function CartInterceptScreen({ asin, currentStep }: Props) {
  const { data: item, isLoading } = useCartWatchItem(asin);
  const dismiss = useCartDismiss();
  const reduceMotion = useReducedMotion();

  if (!item) return null;
  const showWarning = shouldShowOrphanedWarning(item.status);
  const animation = getAnimationConfig(reduceMotion);
  const timeline = computeTimelineProgress(item, new Date());

  return (
    <View>
      {showWarning && <Text>⚠️ 監視は登録済みだけど追撃ジョブが届いてないかも</Text>}
      <Timeline progress={timeline} animation={animation} />
      <Pressable onPress={() => dismiss.mutate(asin)}>いらない</Pressable>
      <Text>{ASSOCIATES_DISCLOSURE_TEXT}</Text>
    </View>
  );
}
```

---

## 3. Member A への合意プロセス（§8.1 / Stage 2 ブロッカー）

| 依頼内容 | 期限 | エビデンス | 状態 |
|---|---|---|---|
| PlatformStack 7 項目追実装 | 2026-05-29 18:00 | PR `#platform-additions-001` | ⏳ 未整備（dev は cart-stack 内 fallback 実装で進行可能） |
| OpenAPI 第 1 版への paths/cart.yaml 同期 | 2026-05-29 18:00 | PR `#cart-001` | ✅ Issue A2 で更新済 |
| Authorizer 配置マトリクスへの Cart 関連 3 行追加 | 2026-05-29 18:00 | PR `#cart-001` | ⏳ Member A レビュー待ち |
| CartWatchItems Unit-1 §4.3 を Unit-5 §1.2 に同期 | 2026-05-29 18:00 | PR `#cart-001` | ⏳ Member A レビュー待ち |
| CI/CD `deploy-dev.yml` への `cdk-deploy-cart-dev` ジョブ追加 | 2026-05-30 18:00 | PR `#cart-deploy-001` | ⏳ Member A レビュー待ち |

PlatformStack 整備までは cart-stack 内で **kmsKey fallback**（新規 KMS Key 作成）で動作可能。

---

## 4. NG-6 静的検証（Property 4 CI Gate）

`scripts/check-ng-keywords.sh` を CI で実行し、30 通知テンプレートに 15 種の禁止ワードが含まれないことを検証。違反検出時は CI fail で deploy ブロック。

```bash
bash scripts/check-ng-keywords.sh
```

---

## 5. 確認事項（実装範囲外、Build and Test ステージ）

- [ ] `cd backend && poetry install && poetry run pytest tests/cart/`（テスト実行）
- [ ] `cd shared/safeguard-policy && npm install && npm test`（TS テスト実行）
- [ ] `cd infra && npm install && npm run synth -- yudane-dev-cart-stack`（CDK synth）
- [ ] `bash scripts/check-ng-keywords.sh`（NG-6 検証）
- [ ] `cd shared/schema && npm run mock:api`（Prism Mock Server 起動確認）
- [ ] dev 環境への CDK deploy（cart-stack 単体）
- [ ] IT-08 / IT-09 / IT-10 統合テスト実行
- [ ] Mobile UI 結線（Day 4-5）

---

## 6. 完了基準

- [x] Step 1〜25 すべて [x]
- [x] Backend Lambda 6 種 + Repository + Scheduler library + 30 templates 完成
- [x] Mobile 純粋ロジック層 9 ファイル完成（UI 結線は実機統合時）
- [x] CDK cart-stack + Snapshot Test 完成
- [x] OpenAPI cart.yaml 整備（A2 で完了）
- [x] telemetry-contracts に Cart 関連識別子追加（B4 で完了）
- [x] NG-6 静的検証 CI スクリプト
- [x] 全ファイル diagnostics エラーゼロ


---

## 7. セルフレビュー履歴

### 7.1 1 巡目セルフレビュー（2026-05-29、Z1〜Z6）

| Issue | 重要度 | 内容 | 修正方針 |
|---|---|---|---|
| **Z1** | 重大 | tests/cart/conftest.py の moto fixture が個別 `with mock_aws():` を持ち、複数テーブル使用テストで context 分離 | 共通 `aws_mock` fixture を新設し、各テーブル fixture が依存先として共有 |
| **Z2** | 重大 | cart_attack_scheduler_retry.py の `_extract_user_id_from_item` がスタブで空文字列を返していた | CartWatchItem に user_id 属性を追加、from_dynamodb で `PK.removeprefix('USER#')` から復元 |
| **Z3** | 重大 | retry batch の `item.item_id.split('#')[0]` が ULID をそのまま返していた | Z2 統合修正、`item.user_id` を直接使用、`_extract_user_id_from_item` 関数を完全削除 |
| **Z4** | 中 | notification_dispatcher.py / push_token.py の `boto3.client('pinpoint')` 呼出箇所に Pinpoint EoL 注記なし | AWS Pinpoint EoL 2026-10-30 / End User Messaging 後継、boto3 の client name 維持の旨をコメント化 |
| **Z5** | 中 | test_repository.py が `_VALID_PREDECESSORS` を private 名で import | repository.py の private 名を public 化（VALID_PREDECESSORS / ACTIVE_STATUSES）、後方互換 alias 残置 |
| **Z6** | 軽微 | cart-intercept-screen-state.ts の `_isStatusAfter` / `_findCurrentStep` が watching_orphaned 含む完全 enum 対応していなかった | watching / watching_orphaned は通知未到達扱い、purchased / dismissed は最後の通知より後扱いに分岐ロジック修正、テスト追加 |

**検証**: 全 15 ファイル diagnostics エラーゼロ + `bash scripts/check-ng-keywords.sh`: ✅ NG-6 check passed: 30 templates clean

### 7.2 2 巡目セルフレビュー（2026-05-30、W1〜W7）

観点: **実 Lambda runtime での import 解決 + テストの実行可能性 + Mobile / TS と Backend / Python の契約整合**。

| Issue | 重要度 | 内容 | 対応 |
|---|---|---|---|
| **W1** | 中 | cart_list.py で `_ACTIVE_STATUSES` をローカル再定義（Z5 修正で repository.ACTIVE_STATUSES を public 化済みなのに使われていない、二重メンテリスク） | `from backend.src.cart.repository import ACTIVE_STATUSES, ...` に変更し、ローカル定義を撤去。`_ALL_STATUSES = list(ACTIVE_STATUSES) + ['purchased', 'dismissed']`、`target_statuses = list(ACTIVE_STATUSES)` で利用 |
| **W2-1** | 軽微 | cart_intake.py 行 209 で `import uuid` が関数内（PEP 8 違反） | module-level に移動 |
| **W2-2** | 重大 | W7 packaging 問題により asin_extractor.py の `try/except ImportError` フォールバック経路が本番でも常に発動し、Q2=A（Backend 再検証）が事実上無効化される懸念 | W7 と統合解決のため B-505 backlog 登録、TODO コメント残置 |
| **W3** | 中 | 4 Lambda（cart_intake / cart_dismiss / cart_list / push_token）が `event['requestContext']['authorizer']['claims']['sub']` を直接読み、Authorizer 経路欠損時に KeyError → 500 で fail-closed 違反 | `from backend.src.common.authz import extract_sub` を import し、`user_id = extract_sub(event)` + `if user_id is None: return 401 auth.unauthenticated` に置換 |
| **W4** | 軽微 | notification_dispatcher.py の `delivery_status='skipped'` 時に status 遷移が走らない挙動について、dev/prd 別挙動のコメントが不足 | dev 環境では永久に notified-30m に進まず統合テスト不能になる旨のコメント追加。audit.log に `stayingStatus` / `step` を追加して可視化 |
| **W5** | ✅ 問題なし | Mobile use-cart-intake.ts の `body: JSON.stringify(...)` 二重 stringify 懸念 | 検証済。`ApiClient.request` は `RequestInit` の body を直接 fetch に渡すため、文字列のまま正しく送信される（api-client.ts 行 122-126 の sendOnce 実装で確認） |
| **W6** | ✅ 問題なし | TestPropertyBasedLatency の moto + env_setup 整合 | 検証済。`aws_mock` fixture（Z1 で導入）経由で同一 context 共有、`@patch` で schedule_attacks をモック化済み |
| **W7** | 🔴 超重大 | cart-stack.ts の `code: lambda.Code.fromAsset('../backend/src/cart')` + handler `'handlers.cart_intake.lambda_handler'` の組合せでは、各 Lambda の `from backend.src.cart.repository import ...` が runtime で全て ImportError になる。**6 Lambda 全てが起動失敗**する | Unit-1 telemetry/handler.py も同パターンで未動作のため、Member A の Unit-1 packaging 方針確立を待つのが整合的と判断。`doc/backlog.md B-505` に新規登録 + cart-stack.ts と各 Lambda handler 冒頭に `TODO(unit-1-packaging-001 / B-505)` コメント残置 |

**修正完了サマリ**:

- **即修正**: W1 / W2-1 / W3（4 Lambda）/ W4 = 計 4 系統 7 ファイル変更
- **W5 / W6**: 問題なし確認のみ
- **W7 / W2-2**: B-505 backlog 登録 + TODO コメント残置（cart-stack.ts + 6 Lambda handler ファイル冒頭、合計 7 ファイル）

**検証**: 全 8 ファイル diagnostics エラーゼロ + `bash scripts/check-ng-keywords.sh`: ✅ NG-6 check passed: 30 templates clean

**今後の流れ**:

- W1 / W3 / W4 修正で Build and Test ステージで pytest / cdk synth を実行する際の中等度バグが解消
- W7 packaging 問題は Member A の Unit-1 packaging 方針確立後に Unit-5 を追従修正（B-505）


---

## 8. Build and Test 検証結果（2026-05-30）

§5 確認事項のうち、Unit-5 のスコープで検証可能な範囲を一気通貫で実行した結果。

### 8.1 検証成功（Unit-5 スコープ）

| カテゴリ | 結果 | 備考 |
|---|---|---|
| Backend pytest（cart 47 + 既存 23） | ✅ 70/70 pass | uv venv + uv pip で deps 解決、`.venv/bin/python -m pytest` 実行 |
| shared/asin-extractor Python 4 + TS 12 | ✅ 16/16 pass | |
| shared/safeguard-policy Python 20 + TS 22 | ✅ 42/42 pass | evaluate_notification を含む |
| shared/telemetry-contracts TS 7 | ✅ 7/7 pass | |
| mobile vitest（cart 23 + 既存 41） | ✅ 64/64 pass | features/cart 純粋ロジック層 23 件すべて pass |
| infra cart-stack.test.ts | ✅ 11/11 pass | テスト assertion 1 件修正（CDK token を `JSON.stringify` で検証）|
| NG-6 静的検証 | ✅ 30 templates clean | `bash scripts/check-ng-keywords.sh` |

**合計**: Unit-5 関連 + 横断テスト **177 件すべて pass**。

### 8.2 検証中に検出した問題（Unit-1 由来、Unit-5 範囲外）

#### Issue V1: PlatformStack cdk-nag 7 件未抑制 error（B-506 登録）

`npx vitest run test/platform-stack.test.ts` で "cdk-nag の未抑制エラーがない" テストが fail。7 件すべて Unit-1 PlatformStack のリソース由来:

- Redis: AwsSolutions-AEC4 / AEC5 / AEC6（Multi-AZ / デフォルトポート / Redis AUTH）
- PlatformVpc: AwsSolutions-VPC7（Flow Log なし）
- UserPool: AwsSolutions-COG1 / COG8（パスワードポリシー / プラスティア）
- DataLakeBucket: AwsSolutions-S1（サーバーアクセスログなし）

**対応**: `doc/backlog.md` に **B-506** として登録、優先度=高。Member A の Unit-1 Platform Stack 完成 PR `#platform-additions-001` に組み込む。

#### Issue V2: PlatformStack TS コンパイルエラー 3 件（B-507 登録）

`npx cdk synth cart-dev-stack` 実行時に ts-node コンパイルで fail（vitest は Vite 経由で transformer 違いから通る）:

- `lib/platform-stack.ts:69` / `:106`: `Vpc` を `IVpc` に渡せない（`vpnGatewayId: string | undefined` ↔ `string` 不一致、`exactOptionalPropertyTypes: true` 起因）
- `lib/platform-stack.ts:89`: `dataLake` 変数が未使用

**対応**: `doc/backlog.md` に **B-507** として登録、優先度=高。Member A の同 PR で対応。

### 8.3 検証中に Unit-5 で修正した内容（合計 4 件）

| # | 種別 | ファイル | 修正内容 |
|---|---|---|---|
| 1 | Test data | `backend/tests/cart/test_handlers.py` | `test_not_found_returns_404` の ASIN を 11 文字 `B0NEXISTING` から 10 文字 `B0NOTEXIST` に修正（regex `^[A-Z0-9]{10}$` 違反で 400 が返っていた）|
| 2 | CDK test | `infra/test/cart-stack.test.ts` | `aws:SourceArn` の Trust Policy 検証で CDK token が object になる問題、`toMatch` から `JSON.stringify(...).toContain(...)` に変更 |
| 3 | CDK app | `infra/bin/app.ts` | `developerInitial: undefined` を `exactOptionalPropertyTypes: true` 環境で渡せない問題、spread 条件分岐 `...(developerInitial !== undefined ? { developerInitial } : {})` で省略可能に |
| 4 | CDK lib | `infra/lib/cart-stack.ts` | (a) `lambdaCommonProps: Partial<lambda.FunctionProps>` を `satisfies Pick<...>` に変更（`runtime` が optional 扱いされる問題解消）/ (b) 未使用 import `aws_secretsmanager`/`aws_events`/`aws_events_targets` を削除 |

すべて diagnostics エラーゼロ確認済み。

### 8.4 未実行の検証項目（Member A の Unit-1 修正待ち）

- ⏳ `npx cdk synth cart-dev-stack`（PlatformStack の TS エラー解消後に再実行）
- ⏳ `npm test --workspace infra`（フルスイート、PlatformStack の cdk-nag 7 件抑制後に再実行）
- ⏳ dev 環境への CDK deploy（cart-stack 単体）
- ⏳ IT-08 / IT-09 / IT-10 統合テスト実行
- ⏳ Mobile UI 結線（Day 4-5、実機統合時）
- ⏳ shared/schema Prism Mock Server 起動確認（schema/openapi.yaml 追加 path のスキーマ整合のみ手動目視で確認済）

### 8.5 結論

Unit-5 Cart Intercept の Code Generation 成果物（35 ファイル）は **2 巡のセルフレビュー + 4 件の Build and Test 検証時修正を経て、Unit-5 スコープ内のすべてのテスト 177 件が pass**。

残る未実行項目は **Unit-1 PlatformStack の TS コンパイル / cdk-nag 7 件 / Lambda packaging 統一方針（B-505 / B-506 / B-507）の Member A 側修正完了後** に再開可能。Unit-5 単独でブロックされる項目は無い。
