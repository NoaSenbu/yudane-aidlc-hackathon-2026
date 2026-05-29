# Unit-5 Cart Intercept — Functional Design

> Construction Phase の Per-Unit Loop Part 2 Generation 成果物。Q1〜Q8 の確定（[functional-design-plan.md](./functional-design-plan.md)）を仕様レベルに展開する。
>
> 参照: [functional-design-plan.md](./functional-design-plan.md) / [data-model.md](./data-model.md) / [sequence-diagrams.md](./sequence-diagrams.md) / [Unit-1 functional-design.md](../../unit-1-platform/functional-design/functional-design.md) / [stories.md US-03-01〜05](../../../inception/user-stories/stories.md#uc-03-カート介入)

---

## 0. 確定事項サマリ

| Q | 論点 | 確定 |
|---|---|---|
| Q1 | Share Extension のネイティブ ↔ RN 通信方式 | A: Expo Config Plugin + App Group（iOS）/ Intent Filter（Android） |
| Q2 | ASIN 抽出の実行場所 | A: Mobile 即時抽出 + Backend 再検証 |
| Q3 | 追撃通知のコピー生成方式 | A: テンプレートベース（MVP）→ B: LLM 動的生成（決勝、[backlog B-501](../../../../doc/backlog.md)） |
| Q4 | EventBridge Scheduler のジョブ管理方式 | A: One-time Schedule（`ActionAfterCompletion: DELETE`） |
| Q5 | Push 通知トークン管理の方式 | C: AWS End User Messaging Push の Endpoint 管理に委ねる |
| Q6 | クリップボード検知（US-03-03）の実装範囲 | B: MVP 見送り、決勝で実装（[backlog B-502](../../../../doc/backlog.md)） |
| Q7 | 追撃通知タップ後の遷移先 | A: CartInterceptScreen 経由 → 「論破する」ボタン → DebateScreen |
| Q8 | CartWatchItems テーブルの詳細設計 | A: ステータスマシン方式 |

---

## Overview

本ドキュメントは Unit-5 Cart Intercept の **機能設計仕様書**。Q1〜Q8 の確定を IO / 状態 / エラー仕様レベルに展開し、各コンポーネント実装の根拠を提示する。

Unit-5 Cart Intercept は YUDANE のコア UC-03（カート介入）を担い、ユーザーが Amazon Shopping アプリで「迷った商品」を YUDANE に共有してから、3 段追撃（30m / 6h / 24h）で論破セッションへ誘導するフロー全体を提供する。M-2（購買快楽のストレス解消剤化）の主戦場の一つであり、「迷いの置き場所をユーザー自身から YUDANE に外部化する」体験を成立させる。

## Architecture

層別の Unit-5 担当コンポーネント:

- **Mobile**: M-05 CartInterceptScreen / M-08 ShareExtensionNativeModule / M-09 PushNotificationHandler（§1）
- **Backend**: B-04 CartIntakeHandler / B-05 CartAttackScheduler / B-06 NotificationDispatcher（§2）
- **Infrastructure**: cart-stack.ts（EventBridge Scheduler / End User Messaging Push / DynamoDB CartWatchItems / NotificationLogs、§3）
- **Data Model**: CartWatchItems / NotificationLogs（[data-model.md](./data-model.md) で詳細化）

依存関係:

- Unit-1 Platform: ApiClient / Telemetry / SafeguardPolicy / AsinExtractor（S-01）
- Unit-2 Auth & Profile: User の Cognito JWT / pushEndpointId
- Unit-3 Debate: 通知タップ → 論破モード起動の API 契約（`POST /v1/debate-sessions { trigger: "cart-attack" }`）
- Unit-4 Reel: B-11 CreatorsApiClient（商品メタ取得）/ B-10 AssociatesLinkGenerator（Special Link）
- Unit-7 Safeguard: API Gateway Lambda Authorizer 経由で月間上限 / 冷却モード判定（US-03-05）

シーケンス図は別ファイル [sequence-diagrams.md](./sequence-diagrams.md) に集約。

## Components and Interfaces

詳細は §1〜§3 で各コンポーネントの IO 仕様 / 状態 / エラー仕様 を定義する。本 Unit で確定する主要インターフェース:

- M-08 ShareExtensionNativeModule の `onUrlShared` / `consumePendingUrl`（§1.2、Q1 = A 反映）
- M-05 CartInterceptScreen の `useCartWatchItem(asin)` / `useCartIntake` / `useCartDismiss(asin)`（§1.1、Q2 = A 反映、6 巡目で Associates 開示責務追加）
- M-09 PushNotificationHandler の `registerForPushNotifications` / `onNotificationTap`（§1.3、Q5 = C / Q7 = A 反映）
- B-04 CartIntakeHandler の `lambda_handler` + `dismiss_lambda_handler` + `list_lambda_handler` + `push_token.register_lambda_handler`（§2 冒頭の Lambda 一覧 + §2.1 / §2.1.1、Q2 = A 反映、SECURITY-05 入力バリデーション）
- B-05 CartAttackScheduler の `schedule_attacks(user_id, item_id, asin, base_time)` / `cancel_attacks`（§2.2、Q4 = A 反映、6 巡目で衝突回避命名）
- B-06 NotificationDispatcher の `lambda_handler` / `generate_copy`（§2.3、Q3 = A 反映、テンプレートベース）

## Data Models

CartWatchItems（PK=USER#{userId}, SK=CART#{asin}、Q8 = A ステータスマシン方式）と NotificationLogs（配信ログ）の詳細は [data-model.md](./data-model.md) を参照。

## Error Handling

各層でのエラー処理方針:

- **Mobile (M-08)**: 不正 URL（Amazon URL でない / ASIN 抽出失敗）→ Toast「商品として認識できなかったよ」+ 監視リスト未登録（US-03-01 AC-5）
- **Mobile (M-05)**: Backend 登録失敗 → 楽観的更新ロールバック + 再試行ダイアログ
- **Mobile (M-09)**: 通知タップで Deep Link 不正 → CartInterceptScreen 一覧 fallback
- **Backend (B-04)**: Creators API レート制限 → ElastiCache キャッシュ fallback、未承認 ASIN は Approved Mobile Application 申請前のためダミーカタログから返却（§8 A-10）
- **Backend (B-05)**: EventBridge Scheduler 作成失敗 → Lambda 再試行 + 1 件失敗でも他 2 件は登録（部分失敗許容）
- **Backend (B-06)**: APNs / FCM 配信失敗 → NotificationLogs に `delivery_status: failed` 記録、End User Messaging の自動リトライに委譲
- **API Gateway**: RFC 7807 Problem Details で統一（[api-contracts.md §4.4](../../../../.kiro/steering/api-contracts.md)）

## Testing Strategy

Unit-5 で必要なテスト:

- **Unit Test**: Vitest（Mobile）+ pytest（Backend）、Line 80%+ / Branch 70%+
- **Property-Based Test**: 要件書 §6.5 PBT-01〜10 を全面適用。本 Unit のカバー対象は [§Testing Strategy.PBT カバレッジマトリクス](#pbt-カバレッジマトリクス全項目網羅5-巡目追加) を参照
- **Contract Test**: Schemathesis で `POST /v1/cart-watch-items` / `GET /v1/cart-watch-items/{asin}` / `DELETE /v1/cart-watch-items/{asin}` / `POST /v1/push-tokens` の OpenAPI 整合性
- **Integration Test**: 本 Unit owner として以下 3 件を採番（Unit-1 IT-01〜07 の続番）:

| ID | シナリオ | 範囲 | 期待結果 |
|---|---|---|---|
| **IT-08** | Share 受信 → 監視登録 → EventBridge ジョブ作成 | M-08 + B-04 + B-05 + DDB + Scheduler | CartWatchItem が status=watching で登録、3 ジョブが at 時刻精度で作成、`attackSchedule` 属性に schedule 名保存 |
| **IT-09** | 30m 通知 → タップ → 論破セッション起動 | EventBridge → B-06 → APNs/FCM → M-09 → M-05 → API → Unit-3 | 通知配信ログ status=sent、CartWatchItem status=notified-30m、DebateSession 1 件作成、初回 token 受信 |
| **IT-10** | Safeguard 月間上限到達時の通知抑制 + Amazon 遷移阻止 | 既存 SafeguardStates {spent >= limit} で B-06 通知 + B-13 遷移を呼ぶ | 通知配信されず NotificationLogs に suppressed_by_safeguard 記録、Amazon 遷移は 403 → Cart 側で 409 表示 |

- **E2E Test**: 本 Unit owner として以下を採番:

| ID | シナリオ | 範囲 | 予選 MVP Readiness |
|---|---|---|---|
| **E2E-03** | Share Extension → 30m 通知 → 論破 → Amazon 遷移 | iOS/Android 端末 + 全 Stack | ✅ 必須 |
| **E2E-03b** | Share Extension → 「いらない」で解除 | iOS/Android 端末 + Cart Stack のみ | 推奨 |

詳細なテストレイヤーとカバレッジは [tech.md §6 品質ゲート](../../../../.kiro/steering/tech.md) を参照。

#### PBT カバレッジマトリクス（全項目網羅、5 巡目追加）

要件書 §6.5 PBT-01〜10 の全項目を本 Unit でどう満たすか:

| ID | カテゴリ | 本 Unit の適用先 | プロパティ |
|---|---|---|---|
| **PBT-01** | Round-trip | M-09 PushPayload serialize/deserialize | `decode(encode(payload)) === payload`（Deep Link URL の round-trip） |
| **PBT-02** | Invariant | B-05 schedule_attacks / S-03 evaluate_notification | 任意 `createdAt` で 3 ジョブが時系列整合 / 任意 4 軸組合せで `block`/`allow` の単調性 |
| **PBT-03** | Inverse | B-04 intake → B-04 dismiss | 登録後 dismiss で active 件数が ±0、attackSchedule の Schedule が全削除される |
| **PBT-04** | Idempotency | B-04 with_idempotency middleware | 同 Idempotency-Key で N 回 POST → 副作用 1 回 + レスポンス同一 |
| **PBT-05** | Stateful | CartWatchItems ステータスマシン | 任意の遷移シーケンス（watching → notified-30m → ...）で ConditionExpression が不正遷移を全 reject |
| **PBT-06** | Metamorphic | B-06 generate_copy | 同 step + 同 productMeta + 同 user_name で N 回呼んでも 10 パターンのいずれかにマッチ（決定論的でないがレンジ内） |
| **PBT-07** | Domain Generator | S-01 AsinExtractor | 任意 URL（Amazon URL strategy / 非 Amazon URL strategy）で `extract_asin` の出力が `ASIN | None` のみ |
| **PBT-08** | Latency / Performance | B-04 lambda_handler | **2 系統に分離**: ① **PBT-08-local**（CI 上の pytest、ロジック単体 < 100ms 想定、AWS Mock）/ ② **PBT-08-deployed**（dev 環境デプロイ後の実機計測、p95 < 2s 想定、要件書 §6.2 整合、Day 2 IT-08 で実施） |
| **PBT-09** | Output Moderation | B-06 notification_templates | 任意テンプレート × 商品メタ × ユーザー名で NG-6 キーワード辞書非含有 |
| **PBT-10** | Example-Based 併存 | 全コンポーネント | PBT で見つかった反例を `tests/regressions/` に固定 example として保存、回帰防止 |

各 PBT は Unit Test と同 PR で同期実装（[AGENTS.md §12.1 Red→Green→Refactor→PBT 補強](../../../../.kiro/steering/AGENTS.md#121-基本サイクルred--green--refactor--pbt-補強)）。

### TDD 開発スタイル（全コンポーネント必須、AGENTS.md §12 反映）

本 Unit のすべてのコンポーネント実装は **Red → Green → Refactor → PBT 補強** の 4 フェーズサイクルで進める。

| コンポーネント | 主スタイル | TDD サイクルの具体例 |
|---|---|---|
| M-05 CartInterceptScreen | Outside-In TDD | Red: useCartWatchItem(asin) 表示テスト → Green: TanStack Query fetch → Refactor: 追撃タイムライン UI → PBT: 任意 status での UI レンダリング不変条件 |
| M-08 ShareExtensionNativeModule | Outside-In TDD | Red: onUrlShared で ASIN を含むイベント発火 → Green: NativeEventEmitter ラッパ → Refactor: App Group consume + 重複排除 → PBT: 任意 URL での ASIN 抽出（PBT-07） |
| M-09 PushNotificationHandler | Outside-In TDD | Red: registerForPushNotifications で endpointId 取得 → Green: End User Messaging SDK 呼出 → Refactor: トークンローテーション → PBT: Deep Link payload の round-trip（PBT-01） |
| B-04 CartIntakeHandler | クラシック TDD | Red: 正常 ASIN で CartWatchItem 作成 → Green: DDB PutItem → Refactor: Creators API 呼出 + 商品メタコピー → PBT: 同 idempotency-key で副作用 1 回（PBT-04） |
| B-05 CartAttackScheduler | クラシック TDD | Red: 1 アイテムで 3 ジョブ作成 → Green: CreateSchedule 3 回呼出 → Refactor: ジョブ ID を attackSchedule に保存 → PBT: 任意 createdAt で時系列整合（PBT-02） |
| B-06 NotificationDispatcher | クラシック TDD | Red: 30m ステップで 30m テンプレートが選ばれる → Green: 辞書ルックアップ → Refactor: 商品名 / 価格埋め込み + NG-6 静的検証 → PBT: 任意テンプレート × 商品メタで NG キーワード出現ゼロ（PBT-09） |
| Cart Stack (CDK) | Snapshot TDD | Red: `template.hasResourceProperties` で CartWatchItems / NotificationLogs / Scheduler IAM 期待 → Green: Stack に追加 → Refactor: KMS / TTL → Snapshot 固定 |

#### TDD 例外（本 Unit）

- `mockup/index.html` の CartInterceptScreen 部分から RN への機械的移植
  - **対象範囲**: `mockup/index.html` の `<section class="screen screen--cart" data-screen="cart">`（実測 **L193〜L268**、cart screen の終端は次画面 reel section L269 の直前）
  - **移植対象 DOM 要素**:
    - 商品取込カード（`.watch` クラス）→ React Native の Pressable + 商品メタ表示コンポーネント
    - 追撃タイムライン（`.card--timeline`）→ FlatList ベースのタイムライン UI
    - チップ（`.chip--hot` / `.chip--ghost`）→ NativeWind 化したバッジコンポーネント
  - **移植しない要素**: ピッチパネル（`.pitch`）/ ダミーデータ（実 API に切替）/ data-goto 属性（React Navigation に置換）
- Pydantic / TypeScript の DTO 純粋宣言（CartWatchItemDto / AttackStepDto）
- 30 通知テンプレート文字列の静的辞書定義（`backend/src/cart/notification_templates.py`）

例外採用時は PR description に「TDD 例外: ◯◯（mockup/index.html L193-L268）」のように **mockup の対応行範囲も併記** する（Code Generation 時の追跡性確保）。

## Correctness Properties

本 Unit が満たすべき不変条件:

### Property 1: 重複登録の冪等性

**Validates: Requirements 6.4** SECURITY-05（入力検証 + ASIN フォーマット） + [Unit-1 §3.2 IdempotencyKeys](../../unit-1-platform/functional-design/data-model.md#32-idempotencykeysq7-確定で新設) の atomic lock パターン

**二重防御で担保**:

1. **Idempotency-Key 層**: 同 `Idempotency-Key` で `POST /v1/cart-watch-items` を複数回送ると、Unit-1 IdempotencyKeys テーブルの atomic lock で 2 回目以降は初回レスポンスをキャッシュ返却（5 分窓）
2. **DDB SK 一意性層**: SK = `CART#{asin}` で同一 user × asin は物理的に 1 レコードのみ。仮に Idempotency-Key 窓外（5 分超）の重複でも `B-04` の既存登録チェック（status=watching なら `isNewlyCreated=false` で既存返却）が発動

これにより、ネットワーク再送、ユーザー操作の連打、Mobile アプリ再起動を跨いだ重複でも整合性を維持する。

### Property 2: 追撃ジョブの時系列整合性

**Validates: Requirements 5.3** FR-CART-02（3 段追撃の正確性）

CartWatchItem 登録時刻 `createdAt` に対し、30m / 6h / 24h ジョブは厳密に `createdAt + {1800, 21600, 86400}` 秒で発火し、順序が逆転しない。EventBridge Scheduler の秒精度仕様で担保。

### Property 3: 通知タップ → 論破遷移の整合性

**Validates: Requirements 5.3** FR-CART-03（通知タップから論破セッション起動）

通知 payload の `productId`（値は ASIN）が CartWatchItems に存在することを Mobile 側で検証し、存在しない場合は CartInterceptScreen 一覧に fallback。Unit-7 Safeguard の判定で block されたセッションは DebateScreen に遷移しない。

> **命名規則の階層化（3 巡目セルフレビュー後確定）**:
>
> Unit-3 Debate（[component-methods.md `start_debate`](../../../inception/application-design/component-methods.md)）との API 契約整合のため、以下の階層で命名を分離:
>
> | レイヤ | 命名 | 値 |
> |---|---|---|
> | Mobile navigation params | `asin` | ASIN |
> | DynamoDB SK | `CART#{asin}` | ASIN |
> | API パスパラメータ | `{asin}` | ASIN |
> | **API request/response body** | **`productId`** | ASIN |
> | **Push notification data** | **`productId`** | ASIN |
>
> Unit 内部（Mobile / DDB / API パス）は `asin` を主軸に、Unit 横断 API（POST body / Push payload）は `productId` で Unit-3 と整合させる。

### Property 4: NG-6 脅迫禁止コピーの遵守

**Validates: Requirements 9** NG-6（脅迫・罪悪感強要禁止）

30 通知テンプレートに対し、CI で「ストレス悪化」「罪悪感」「失敗」等の NG キーワード辞書による静的検証を実施（PBT-09 LLM 出力モデレーション補完）。Q3 = A（テンプレート方式）採用により、CI 段階で全パターン検証可能。

### Property 5: Safeguard 連携での通知抑制

**Validates: Requirements 5.9** FR-AUTH-04（冷却モード）/ Stories US-03-05

冷却モード ON / 月間上限到達時、B-06 NotificationDispatcher は配信前に SafeguardPolicy（S-03、Shared 層）を呼び出し、`block` 判定なら配信せず NotificationLogs に `suppressed_by: safeguard` を記録する。

---

## 1. Mobile 層（`mobile/src/features/cart/`）

### 1.1 M-05 CartInterceptScreen

#### 責務

- Share 受信時の到着アニメーション + 商品取込カード表示
- カート監視リスト一覧表示（Home 画面の hero と同期）
- 3 段追撃タイムライン可視化（30m / 6h / 24h、現在のステップをハイライト）
- 「論破する」ボタンで Unit-3 DebateScreen 起動
- 「いらない」ボタンで監視解除（残り追撃ジョブをキャンセル）
- US-03-05 のセーフガード状態の表示（冷却モード / 月間上限到達）
- US-03-04 AC-3 / FR-PROFILE-04 / NG-8 整合：「Amazon で買う」ボタンの近傍に **Associates 開示文言**（「YUDANE は Amazon Associates として、紹介リンク経由の購入で Amazon から紹介料を受け取っています」）を常時表示。タップ時の遷移確認オーバーレイにも同文言を含める（6 巡目追加）
- **NFR Design 2 巡目追加（Issue LLLL）**: `status === "watching_orphaned"` のアイテムは一覧で **⚠️ 警告アイコン + 「監視は登録済みだけど追撃ジョブが届いてないかも」** のサブテキストを表示。タップ時はその場で「いらない」（dismiss）ボタンを目立つ位置に表示し、ユーザーが手動削除可能。論破ボタンと Amazon 遷移ボタンは通常通り表示（追撃ジョブがなくても論破経路は有効、Property 6 / SECURITY-15 整合）。Member D 実装時は「警告アイコン」の Reduce Motion 対応（`useReducedMotion` で点滅停止）を確認
- **2026-05-29 追記（Issue C3）**: M-13 Telemetry の自動計測 4 イベント（`screen_view` / `app_foreground` / `app_background` / `deeplink_open`）が本画面で発火する。手動計測は `cart.intake_received` / `cart.dismiss` / `cart.amazon_transition` / `cart.notification_tap`（[shared/telemetry-contracts](../../../../shared/telemetry-contracts/) Issue B4 で追加済）。

> **注: パスパラメータの設計（2 巡目セルフレビュー後修正）**
>
> CartWatchItems テーブルの SK が `CART#{asin}` であるため、API パスパラメータも **`{asin}`** に統一する（`{itemId}` ではない）。`itemId`（ULID）は NotificationLogs からの FK 参照や監査ログ目的で属性として保持するが、API URL では asin を使用することで、DDB の `GetItem(PK=USER#u, SK=CART#asin)` で 1 RCU の効率的アクセスを可能にする。

#### IO 仕様

```typescript
// mobile/src/features/cart/use-cart-watch-item.ts
import { useQuery } from '@tanstack/react-query';
// 2026-05-29 修正（Issue B3）: apiFetch は ApiClient.request の薄いラッパーとして
// mobile/src/features/platform/api-client/api-fetch.ts に追加（Unit-5 owner で main に PR 提出）
import { apiFetch } from '@yudane/api-client';

export function useCartWatchItem(asin: string) {
  return useQuery({
    queryKey: ['cart-watch-item', asin],
    queryFn: () => apiFetch<CartWatchItemDto>(`/v1/cart-watch-items/${asin}`),
    staleTime: 30_000,
  });
}

// mobile/src/features/cart/use-cart-intake.ts
import { useMutation } from '@tanstack/react-query';
import { v7 as uuidv7 } from 'uuid';

export function useCartIntake() {
  return useMutation({
    mutationFn: async (input: { url: string; asin: string }) => {
      // Q2 = A 反映：Mobile 側で抽出済み ASIN を Backend に送信、Backend が再検証
      return apiFetch<CartWatchItemDto>('/v1/cart-watch-items', {
        method: 'POST',
        idempotencyKey: uuidv7(),  // Q7 = B（Unit-1）：POST は冪等キー必須
        body: JSON.stringify({ url: input.url, asin: input.asin }),
      });
    },
  });
}

// mobile/src/features/cart/use-cart-dismiss.ts
export function useCartDismiss() {
  return useMutation({
    mutationFn: (asin: string) => apiFetch<void>(`/v1/cart-watch-items/${asin}`, {
      method: 'DELETE',
      // DELETE は Unit-1 Q7=B により冪等のため Idempotency-Key 不要
    }),
  });
}

// mobile/src/features/cart/CartInterceptScreen.tsx
export function CartInterceptScreen(): JSX.Element {
  // ルートからの prop: { mode: 'list' | 'detail', asin?: string, currentStep?: '30m'|'6h'|'24h' }
  // 状態:
  //   - 一覧モード: useQuery(['cart-watch-items']) で全 watching アイテム取得
  //   - 詳細モード: useCartWatchItem(asin) で単一アイテム + 追撃タイムライン
  //   - intake モード: 取込中 → 完了アニメ
  // アクション:
  //   - 「論破する」: navigation.navigate('Debate', { trigger: 'cart-attack', productId: asin })  // Unit-3 契約に従い productId キー
  //   - 「いらない」: useCartDismiss().mutate(asin) → 楽観的更新
  //   - 「Amazon で買う」: B-10 経由 Special Link → Linking.openURL (deep link)
}
```

#### 状態 / 遷移

```
[idle] ──Share 受信──> [intake-pending]
                           │
                           ├──成功──> [intake-success] ──1.5s──> [list]
                           └──失敗──> [intake-error] ──Toast──> [list]

[list] ──notification 受信──> [detail (highlighted)]
[list] ──cardTap──> [detail]
[detail] ──「論破する」──> Unit-3 DebateScreen
[detail] ──「いらない」──> [list (item removed)]
[detail] ──Safeguard block──> [list (with safeguard banner)]
```

#### エラー仕様

| 状態 | 挙動 |
|---|---|
| Backend 登録失敗（5xx） | 楽観的更新ロールバック + Toast「もう一度試して」+ 自動リトライ（GET/DELETE のみ、Q7=B） |
| Safeguard block（409） | Toast「今日は静かな日にしたじゃん」+ SafeguardScreen への誘導ボタン表示 |
| 商品メタ取得失敗（B-04 から 4xx 戻り） | 「商品として認識できなかったよ」Toast + intake モード終了 |
| ネットワークオフライン | 取込操作はキューイング不可（リアルタイム性が必要）、Toast で再試行を促す |

---

### 1.2 M-08 ShareExtensionNativeModule（Q1 = A 反映）

#### 責務

- iOS Share Extension（Swift、別プロセス）で Amazon URL を受信
- App Group `group.app.yudane` の UserDefaults に URL を書き込み + URL Scheme `yudane://share` でメインアプリ起動
- Android Share Target（Intent Filter）でメインアプリ Activity が直接受信
- メインアプリ側で起動時 / フォアグラウンド復帰時に保留中 URL を消費し、JS にイベント発行

#### Expo Config Plugin 仕様

```typescript
// app.json（YUDANE のルート）抜粋
{
  "expo": {
    "plugins": [
      ["./plugins/yudane-share-extension", {
        "appGroupIdentifier": "group.app.yudane",
        "schemeHost": "share",
        "activationRules": {
          "ios": {
            "type": "URL",
            "patterns": ["amazon\\.co\\.jp", "amazon\\.com", "amzn\\.asia"]
          },
          "android": {
            "intentFilters": [
              { "action": "android.intent.action.SEND", "mimeType": "text/plain" }
            ]
          }
        }
      }]
    ]
  }
}
```

注: 本 Plugin は Member A が Day 2-3 に整備（[parallel-dev-prerequisites.md C-3 = A 一括ドラフト方針](../../plans/parallel-dev-prerequisites.md) に整合）。OSS の `expo-share-extension` メンテナンス状況によっては自前 Plugin に切替（半日工数）。

#### IO 仕様（RN ↔ Native）

```typescript
// mobile/src/features/cart/share-extension-module.ts
import { NativeModules, NativeEventEmitter } from 'react-native';

interface YudaneShareModuleSpec {
  /** App Group / Intent Filter に保留されている URL を 1 件取り出す（再呼出可、なければ null） */
  consumePendingUrl(): Promise<{ url: string; receivedAt: string } | null>;
  /** Share Extension からの新規 URL 受信を購読開始（NativeEventEmitter 経由） */
  startListening(): void;
  /** 購読停止 */
  stopListening(): void;
}

const { YudaneShareModule } = NativeModules as { YudaneShareModule: YudaneShareModuleSpec };

export const shareEventEmitter = new NativeEventEmitter(NativeModules.YudaneShareModule);
// Event: 'onUrlShared' { url: string, receivedAt: string }

export async function consumePendingUrl() {
  return YudaneShareModule.consumePendingUrl();
}
```

```typescript
// mobile/src/features/cart/use-share-intake.ts
import { useEffect } from 'react';
import { AppState } from 'react-native';
import { extractAsin } from '@yudane/asin-extractor';  // S-01
import { useCartIntake } from './use-cart-intake';
import { shareEventEmitter, consumePendingUrl } from './share-extension-module';

export function useShareIntake() {
  const { mutate } = useCartIntake();

  useEffect(() => {
    const handleUrl = async (payload: { url: string }) => {
      // 2026-05-29 修正（Issue B1）: 実装は判別ユニオン AsinResult を返すため
      // result.ok で分岐（business-rules.md ASIN-06 / shared/asin-extractor 整合）
      const result = extractAsin(payload.url);
      if (!result.ok) {
        // US-03-01 AC-5: Amazon URL 形式以外は登録しない
        // result.reason: 'no-match' | 'invalid-checksum-format' | 'unsupported-host'
        Toast.show('商品として認識できなかったよ');
        return;
      }
      // Mobile 側で即時 ASIN 表示（Q2 = A 反映、UX レイテンシ最小化）
      mutate({ url: payload.url, asin: result.asin });
    };

    const sub = shareEventEmitter.addListener('onUrlShared', handleUrl);

    // 起動時 / フォアグラウンド復帰時に保留中 URL を消費
    const consume = async () => {
      let pending = await consumePendingUrl();
      while (pending) {
        await handleUrl(pending);
        pending = await consumePendingUrl();
      }
    };
    consume();
    const appStateSub = AppState.addEventListener('change', (state) => {
      if (state === 'active') consume();
    });

    return () => {
      sub.remove();
      appStateSub.remove();
    };
  }, [mutate]);
}
```

#### iOS Native 仕様（Swift、Share Extension Target）

```swift
// ios/YudaneShareExtension/ShareViewController.swift（Plugin が雛形生成）
import UIKit
import Social
import MobileCoreServices

class ShareViewController: SLComposeServiceViewController {
  private let appGroupId = "group.app.yudane"
  private let pendingKey = "pendingShareUrls"

  override func didSelectPost() {
    guard let item = extensionContext?.inputItems.first as? NSExtensionItem,
          let provider = item.attachments?.first else {
      completeRequest()
      return
    }

    provider.loadItem(forTypeIdentifier: kUTTypeURL as String, options: nil) { [weak self] data, _ in
      guard let self = self,
            let url = data as? URL else { self?.completeRequest(); return }

      // App Group の UserDefaults に保留 URL を追記（FIFO キュー）
      let defaults = UserDefaults(suiteName: self.appGroupId)
      var pending = defaults?.array(forKey: self.pendingKey) as? [[String: String]] ?? []
      pending.append([
        "url": url.absoluteString,
        "receivedAt": ISO8601DateFormatter().string(from: Date())
      ])
      defaults?.set(pending, forKey: self.pendingKey)

      // メインアプリを URL Scheme で起動（Share Extension UI を即閉じる）
      self.openMainApp()
      self.completeRequest()
    }
  }

  private func openMainApp() {
    let url = URL(string: "yudane://share")!
    var responder: UIResponder? = self
    while let r = responder {
      if let app = r as? UIApplication {
        app.perform(#selector(UIApplication.open(_:options:completionHandler:)),
                    with: url, with: [:])
        break
      }
      responder = r.next
    }
  }

  private func completeRequest() {
    extensionContext?.completeRequest(returningItems: nil)
  }
}
```

```swift
// ios/YudaneShareModule/YudaneShareModule.swift（メインアプリ Native Module）
import Foundation
import React

@objc(YudaneShareModule)
class YudaneShareModule: RCTEventEmitter {
  private let appGroupId = "group.app.yudane"
  private let pendingKey = "pendingShareUrls"

  override func supportedEvents() -> [String]! { ["onUrlShared"] }

  @objc func consumePendingUrl(_ resolve: @escaping RCTPromiseResolveBlock,
                                rejecter reject: @escaping RCTPromiseRejectBlock) {
    let defaults = UserDefaults(suiteName: appGroupId)
    var pending = defaults?.array(forKey: pendingKey) as? [[String: String]] ?? []
    guard !pending.isEmpty else { resolve(nil); return }
    let head = pending.removeFirst()
    defaults?.set(pending, forKey: pendingKey)
    resolve(head)
  }

  // URL Scheme `yudane://share` 受信時に AppDelegate から呼ばれる
  @objc func notifyUrlShared(_ payload: [String: String]) {
    sendEvent(withName: "onUrlShared", body: payload)
  }
}
```

#### Android Native 仕様（Kotlin、Intent Filter）

```kotlin
// android/app/src/main/AndroidManifest.xml に Plugin が追記
<activity android:name=".MainActivity" ... >
  <intent-filter>
    <action android:name="android.intent.action.SEND" />
    <category android:name="android.intent.category.DEFAULT" />
    <data android:mimeType="text/plain" />
  </intent-filter>
</activity>

// android/app/src/main/java/app/yudane/YudaneShareModule.kt
class YudaneShareModule(reactContext: ReactApplicationContext) :
  ReactContextBaseJavaModule(reactContext) {

  override fun getName() = "YudaneShareModule"

  // MainActivity.onNewIntent() から呼ばれる
  fun handleIntent(intent: Intent) {
    if (intent.action == Intent.ACTION_SEND && intent.type == "text/plain") {
      val text = intent.getStringExtra(Intent.EXTRA_TEXT) ?: return
      // Amazon URL のみ通す（Q1 activationRules 相当）
      if (!Regex("amazon\\.(co\\.jp|com)|amzn\\.asia").containsMatchIn(text)) return
      val payload = Arguments.createMap().apply {
        putString("url", text)
        putString("receivedAt", Instant.now().toString())
      }
      reactApplicationContext
        .getJSModule(DeviceEventManagerModule.RCTDeviceEventEmitter::class.java)
        .emit("onUrlShared", payload)
    }
  }

  @ReactMethod
  fun consumePendingUrl(promise: Promise) {
    // Android はキュー化不要（onNewIntent で即イベント発火、メインアプリ常駐前提）
    promise.resolve(null)
  }
}
```

#### エラー仕様

| 状態 | 挙動 |
|---|---|
| Share Extension のメモリ上限超過（120MB） | OS が Extension を kill、UserDefaults への書き込みは未完了 → メインアプリ起動時に何も起きない（許容、ユーザーは再 Share） |
| App Group 未設定 | `UserDefaults(suiteName:)` が nil → ログ出力 + `consumePendingUrl()` が常に null 返却（CI で App Group 設定を E2E 検証） |
| Amazon URL でない（Activation Rule で弾かれない場合の二重防御） | `extractAsin()` が `{ ok: false, reason: ... }` を返す → Toast 表示のみ、登録なし（ASIN-06 整合）|

---

### 1.3 M-09 PushNotificationHandler（Q5 = C / Q7 = A 反映）

#### 責務

- APNs / FCM トークン取得（`expo-notifications` + ネイティブ拡張）
- Backend に `POST /v1/push-tokens` で送信 → Backend が AWS End User Messaging Push の Endpoint を作成 / 更新
- 通知受信 → Deep Link payload に基づき CartInterceptScreen（detail mode）へ遷移
- フォアグラウンド受信時のローカル表示（in-app banner）

> **AppShell との Deep Link ハンドリング連携（7 巡目追加、Issue JJ）**:
>
> Cold Start（アプリ未起動状態で通知タップ）/ Warm Start（バックグラウンドで起動済み）の両方をサポートする。
>
> | 起動状態 | フロー |
> |---|---|
> | **Cold Start** | OS が `yudane://cart-attack/{asin}?step=...` を Intent / URL として渡す → Unit-1 [M-01 AppShell.onDeepLink](../../unit-1-platform/functional-design/functional-design.md#11-m-01-appshell) が受領 → Cognito セッション復元完了を待ち（Splash 中）→ AppShell から M-09 onNotificationTap に payload を delegate → CartInterceptScreen に navigate |
> | **Warm Start** | OS が `expo-notifications` のリスナーを直接起動 → M-09 onNotificationTap が即座に navigate（Cognito セッションは既に復元済み） |
> | **Foreground 受信** | M-09 が `expo-notifications` の `addNotificationReceivedListener` で受信 → 上部 in-app banner を表示（M-05 が表示中なら一覧 refetch） |
>
> AppShell からの delegate 経路: `M-01.onDeepLink(url) → parseUrl(url) → M-09.onNotificationTap(payload)`。Unit-1 owner との合意事項は [§8.1 Unit 間契約レビュープロセス](#81-本-unit-が他-unit-owner-にレビュー依頼する事項) に追加（Member A 担当）。

#### IO 仕様

```typescript
// mobile/src/features/cart/push-notification-handler.ts
import * as Notifications from 'expo-notifications';
import { v5 as uuidv5 } from 'uuid';
import { apiFetch } from '@yudane/api-client';

// Idempotency-Key を UUID 形式に統一する namespace（YUDANE 固定）
// Unit-1 IdempotencyKeys テーブルは format: uuid を要求するため、
// APNs/FCM トークン文字列を UUID v5 で決定論的に変換する
const PUSH_TOKEN_NAMESPACE = '6ba7b810-9dad-11d1-80b4-00c04fd430c8';

export async function registerForPushNotifications(): Promise<{ endpointId: string }> {
  const { status } = await Notifications.requestPermissionsAsync();
  if (status !== 'granted') throw new Error('push-permission-denied');

  const token = await Notifications.getDevicePushTokenAsync();
  // Q5 = C 反映：Backend が End User Messaging の Endpoint を管理
  // Issue C 対応: トークン文字列を UUID v5 化して Idempotency-Key 規約に整合
  const idempotencyKey = uuidv5(token.data, PUSH_TOKEN_NAMESPACE);
  const response = await apiFetch<{ endpointId: string }>('/v1/push-tokens', {
    method: 'POST',
    idempotencyKey,
    body: JSON.stringify({ token: token.data, platform: token.type }),
  });
  return response;
}

// 通知 payload（Push 配信のキー名は Unit-3 契約に整合させ productId に統一）
type PushPayload = {
  type: 'cart-attack-30m' | 'cart-attack-6h' | 'cart-attack-24h' | 'calendar' | 'admin';
  productId?: string;         // cart-attack-* で必須（値は ASIN、Unit-3 契約整合）
  step?: '30m' | '6h' | '24h';
};

// notification tap handler（AppShell / M-01 から呼ばれる）
export function onNotificationTap(payload: PushPayload, navigation: NavigationProp<RootStack>) {
  // Q7 = A 反映：cart-attack-* は CartInterceptScreen 経由で論破に進む
  if (payload.type.startsWith('cart-attack')) {
    if (!payload.productId) {
      // Property 3 不変条件違反 → CartInterceptScreen 一覧に fallback
      navigation.navigate('CartIntercept', { mode: 'list' });
      return;
    }
    navigation.navigate('CartIntercept', {
      mode: 'detail',
      asin: payload.productId,        // Unit 内部キー名 asin に変換
      currentStep: payload.step,
    });
  }
}
```

#### 状態 / 遷移

```
[unregistered] ──requestPermissions──> [permission-pending]
                                            │
                                            ├──granted──> [registering]
                                            │              │
                                            │              ├──成功──> [registered]
                                            │              └──失敗──> [error] ──5min retry──> [registering]
                                            └──denied───> [denied (Telemetry: push.permission_denied)]

[registered] ──token rotation──> [registering] ──Endpoint update──> [registered]
[registered] ──notification 受信──> [tap handler 起動] ──> CartInterceptScreen
```

#### エラー仕様

| 状態 | 挙動 |
|---|---|
| Permission denied | SafeguardScreen に「通知を OFF にしている間はカート介入が機能しないよ」案内、Telemetry 記録 |
| Token 取得失敗 | 5 分後にリトライ（最大 3 回）、失敗継続なら諦め（Telemetry 記録） |
| Backend 登録失敗（5xx） | 起動毎にリトライ、AsyncStorage に未送信トークンを保留 |
| Notification tap で `productId` 不正 | CartInterceptScreen 一覧 fallback + Telemetry 記録 |
| 端末オフライン中の通知（5 巡目追加、Issue BB） | APNs / FCM が **最終 1 件のみキャッシュ**する仕様（OS 制約）。30m / 6h が未受信のまま 24h 通知が来ると順序逆転する。アプリ起動時に M-05 が `GET /v1/cart-watch-items?status=active` で最新状態をフェッチして UI を再構築するため、表示の整合性は保たれる（追撃タイムラインは status を信頼） |
| 通知の重複受信（OS のリトライによる） | M-09 が `notificationId`（payload に含む UUID v4）で重複検知、24 時間 AsyncStorage キャッシュ。Telemetry の `push.notification_received` も同 ID で de-dup |

---

## 2. Backend 層（`backend/src/cart/`）

> **Lambda 一覧（6 巡目で整理 + NFR Design Q4 = A' で 1 種追加）**:
>
> | Lambda | Handler | 主な責務 | API |
> |---|---|---|---|
> | B-04 CartIntakeHandler | `handlers.cart_intake.lambda_handler` | URL 受信 → ASIN 検証 → 商品メタ取得 → DDB 登録 → 追撃ジョブ作成 | `POST /v1/cart-watch-items` |
> | B-04 cart_dismiss | `handlers.cart_dismiss.dismiss_lambda_handler` | 監視解除 + 残追撃ジョブ取消 | `DELETE /v1/cart-watch-items/{asin}` |
> | B-04 cart_list | `handlers.cart_list.list_lambda_handler` | 一覧取得（status filter + cursor）/ 単一取得（path param） | `GET /v1/cart-watch-items` / `GET /v1/cart-watch-items/{asin}` |
> | B-04 push_token_register | `handlers.push_token.register_lambda_handler` | End User Messaging Endpoint 作成・更新 | `POST /v1/push-tokens` |
> | B-05 CartAttackScheduler | （ライブラリ、B-04 内同期呼出） | 3 ジョブ作成 / 取消 | — |
> | **B-05 cart_attack_scheduler_retry**（NFR Design Q4 = A' 追加）| `handlers.cart_attack_scheduler_retry.lambda_handler` | **部分失敗で attackSchedule が空の watching アイテムを 15 分間隔で補完、3 回失敗で orphaned 遷移** | EventBridge Schedule 起動のみ |
> | B-06 NotificationDispatcher | `handlers.notification_dispatcher.lambda_handler` | EventBridge 発火 → 配信判定 → Push 配信 | EventBridge 起動のみ |

### 2.1 B-04 CartIntakeHandler（Q2 = A 反映）

#### 責務

- `POST /v1/cart-watch-items` の受信
- ASIN 再検証（S-01 AsinExtractor、SECURITY-05）
- 既存登録チェック（重複時は既存アイテム返却）
- Creators API（B-11 経由）で商品メタ取得、ElastiCache 6h キャッシュ
- DynamoDB CartWatchItems への登録（status=watching）
- B-05 CartAttackScheduler を非同期呼出（ジョブ作成）
- レスポンス返却（2 秒以内、US-03-01 AC-3）

#### IO 仕様

```python
# backend/src/cart/handlers/cart_intake.py
from datetime import datetime, timezone
from yudane_asin_extractor import extract_asin  # S-01（実装は AsinResult 判別ユニオン、ASIN-06）
# 2026-05-29 修正（Issue B2）: main 由来の AuditLogger はクラスベース実装
from backend.src.common.logging import AuditLogger
from common.idempotency import with_idempotency  # Unit-1 §3.2 / Issue A1 で Member A 依頼中
from common.creators_api import get_item_by_asin  # B-11 経由
from .scheduler import schedule_attacks  # B-05 を Lambda 内で同期呼出
from .repository import CartWatchItemsRepo

# 注: intake 自体には Safeguard 判定を入れない（登録は常に許容、配信時に B-06 で判定）
# Safeguard middleware（API Gateway Lambda Authorizer、Unit-7）が前段で監視するのは
# debate-start / amazon-transition のみ（Unit-1 §4.1 配置マトリクス）

class CartIntakeRequest(BaseModel):
    url: HttpUrl
    asin: str = Field(min_length=10, max_length=10, pattern=r'^[A-Z0-9]{10}$')

class CartIntakeResponse(BaseModel):
    item: CartWatchItemDto
    isNewlyCreated: bool

@with_idempotency
def lambda_handler(event, context) -> APIGatewayProxyResponse:
    audit = AuditLogger(service="cart-intake")
    user_id = event["requestContext"]["authorizer"]["claims"]["sub"]
    body = CartIntakeRequest.model_validate_json(event["body"])

    # Q2 = A 反映：Backend 側で再検証（Mobile の抽出を信用しない、SECURITY-05）
    # 2026-05-29 修正（Issue B1）: shared/asin-extractor 実装は AsinResult 判別ユニオンを返す
    # Python 実装（shared/asin-extractor/python/asin_extractor.py）も TS 同等（ASIN-07 クロス言語一致）
    asin_result = extract_asin(str(body.url))
    if not asin_result.ok or asin_result.asin != body.asin:
        audit.log("warn", "ASIN mismatch between mobile and backend", {
            "userId": user_id,
            "mobileAsin": body.asin,
            "backendOk": asin_result.ok,
            "backendAsin": asin_result.asin if asin_result.ok else None,
            "reason": asin_result.reason if not asin_result.ok else None,
        })
        return Response(400, ProblemDetails(
            type="https://api.yudane.app/errors/asin-mismatch",
            title="ASIN 不一致",
            status=400,
        ))
    extracted_asin = asin_result.asin  # 以降は string として扱う

    repo = CartWatchItemsRepo()

    # 既存登録チェック（同一 user × asin は 1 件、status=dismissed なら再活性化）
    existing = repo.get(user_id, extracted_asin)
    if existing and existing.status == "watching":
        audit.log("info", "Duplicate intake, returning existing", {
            "userId": user_id, "asin": extracted_asin
        })
        return Response(200, CartIntakeResponse(item=existing.to_dto(), isNewlyCreated=False))

    # 5 巡目: dismissed / purchased からの再活性化（Issue X 対応）
    # 「やっぱり気になる」「もう一度買いたい」ケースに対応
    if existing and existing.status in ("dismissed", "purchased"):
        audit.log("info", "Reactivating from terminal status", {
            "userId": user_id, "asin": extracted_asin, "previousStatus": existing.status
        })
        # 既存レコードを watching に戻す（既存 itemId を維持、createdAt は更新）
        # GSI1 を再付与、TTL は watching 用 30 日に再設定
        now = datetime.now(timezone.utc)
        item = repo.reactivate(user_id, extracted_asin, now)
        # 新たに 3 ジョブをスケジュール（前回の attackSchedule は dismissed 時に既に削除済）
        try:
            attack_schedule = schedule_attacks(user_id, item.itemId, extracted_asin, now)
            repo.update_attack_schedule(user_id, extracted_asin, attack_schedule)
        except Exception as e:
            audit.log("error", "Failed to schedule attacks for reactivation", {
                "itemId": item.itemId, "error": str(e)
            })
        audit.metric("cart.intake.reactivated", 1, "Count", {"previousStatus": existing.status})
        return Response(200, CartIntakeResponse(item=item.to_dto(), isNewlyCreated=False))

    # Creators API で商品メタ取得（B-11 経由、ElastiCache 6h キャッシュ、§8 A-10 でダミー fallback）
    product_meta = get_item_by_asin(extracted_asin)
    if product_meta is None:
        return Response(404, ProblemDetails(
            type="https://api.yudane.app/errors/product-not-found",
            title="商品が見つからなかった",
            status=404,
        ))

    # CartWatchItem 登録（Q8 = A ステータスマシン: watching で開始）
    now = datetime.now(timezone.utc)
    item = repo.create(
        user_id=user_id,
        asin=extracted_asin,
        product_meta=product_meta,
        status="watching",
        created_at=now,
    )

    # B-05 を Lambda 内で同期呼出（追撃ジョブ 3 件作成、部分失敗許容）
    try:
        attack_schedule = schedule_attacks(user_id, item.itemId, extracted_asin, now)
        repo.update_attack_schedule(user_id, extracted_asin, attack_schedule)
    except Exception as e:
        # 部分失敗でも CartWatchItem 登録は維持、後で B-05 のリトライバッチで補完
        audit.log("error", "Failed to schedule attacks", {"itemId": item.itemId, "error": str(e)})

    audit.metric("cart.intake.created", 1, "Count", {"userId": user_id})
    return Response(201, CartIntakeResponse(item=item.to_dto(), isNewlyCreated=True))
```

#### エラー仕様

| 入力 | レスポンス | 挙動 |
|---|---|---|
| ASIN 形式不正 | 400 ValidationError | Pydantic で即 reject |
| Mobile ASIN ≠ Backend 抽出 ASIN | 400 asin-mismatch | Telemetry に warn 記録（不正クライアント検知） |
| Creators API 404 | 404 product-not-found | ダミーカタログ fallback（§8 A-10 期間中） |
| Creators API 5xx / レート制限 | ElastiCache キャッシュから返却、なければ 503 | キャッシュヒット率 95% 想定 |
| 重複登録（status=watching） | 200 + isNewlyCreated=false | 既存アイテムをそのまま返却 |
| Idempotency-Key 重複 | キャッシュ済みレスポンス | Unit-1 §3.2 IdempotencyKeys 参照 |

#### Lambda 設定

- VPC: **VPC 外**（Unit-1 §3.1、DDB / Creators API 経由のみ）
- Memory: 512MB（Pydantic + DDB / API 呼出で十分）
- Timeout: 5s（US-03-01 AC-3「2 秒以内」+ バッファ）
- 同時実行: 100（予選想定）

---

### 2.1.1 B-04 dismiss handler（DELETE /v1/cart-watch-items/{asin}）

> **2 巡目セルフレビュー後追加（Issue B 対応）+ 3 巡目セルフレビュー後修正（Issue K 対応）**: B-04 と論理的に同じドメインだが、責務とパッケージング上は **独立した Lambda** として CDK に登録する（POST と DELETE で IAM 権限要件 / VPC 設定 / 同時実行が分離可能）。同 `backend/src/cart/handlers/` 配下に配置するが、CDK の `lambda.Function` は別インスタンスとなる。

#### 責務

- `DELETE /v1/cart-watch-items/{asin}` の受信
- 残追撃ジョブ 3 件を `cancel_attacks()` で取消（[functional-design.md §2.2](#22-b-05-cartattackschedulerq4--a-反映)）
- CartWatchItems を `dismissed` ステータスに遷移 + TTL 7 日設定 + GSI1 から外す（Sparse 化）
- 既に `dismissed` / `purchased` の場合は 204 で冪等返却

#### IO 仕様

```python
# backend/src/cart/handlers/cart_dismiss.py
from datetime import datetime, timezone
# 2026-05-29 修正（Issue B2）: main 由来の AuditLogger はクラスベース実装
from backend.src.common.logging import AuditLogger
from .scheduler import cancel_attacks
from .repository import CartWatchItemsRepo

def dismiss_lambda_handler(event, context) -> APIGatewayProxyResponse:
    audit = AuditLogger(service="cart-dismiss")
    user_id = event["requestContext"]["authorizer"]["claims"]["sub"]
    asin = event["pathParameters"]["asin"]

    # ASIN 形式バリデーション（SECURITY-05）
    if not re.match(r'^[A-Z0-9]{10}$', asin):
        return Response(400, ProblemDetails(
            type="https://api.yudane.app/errors/invalid-asin-format",
            title="ASIN 形式不正",
            status=400,
        ))

    repo = CartWatchItemsRepo()
    item = repo.get(user_id, asin)

    if item is None:
        return Response(404, ProblemDetails(
            type="https://api.yudane.app/errors/cart-watch-item-not-found",
            title="監視リストに該当アイテムなし",
            status=404,
        ))

    # 冪等性: 既に dismissed / purchased なら 204
    if item.status in ("dismissed", "purchased"):
        return Response(204, body=None)

    # 残追撃ジョブをキャンセル（部分失敗許容、ResourceNotFoundException は無視）
    if item.attack_schedule:
        cancel_attacks(item.attack_schedule)

    # ステータス遷移 + TTL 7 日設定 + GSI1 から外す
    repo.transition_to_dismissed(user_id, asin)

    audit.log("info", "Cart watch item dismissed", {"userId": user_id, "asin": asin})
    audit.metric("cart.dismissed", 1, "Count", {"previousStatus": item.status})
    return Response(204, body=None)
```

#### エラー仕様

| 入力 | レスポンス | 挙動 |
|---|---|---|
| ASIN 形式不正 | 400 invalid-asin-format | Pydantic / 正規表現で即 reject |
| アイテムなし | 404 cart-watch-item-not-found | UI 側で一覧再取得 |
| 既に dismissed / purchased | 204 No Content | 冪等返却（Property 1 と整合） |
| `cancel_attacks` 部分失敗 | 204 + warn ログ | EventBridge 側で発火しても `dismissed` 判定で B-06 が抑制 |

#### Lambda 設定

- 独立 Lambda `cartDismissFunction` として CDK 登録（[§3.1](#31-stack-構成) 参照）
- VPC: **VPC 外**（Unit-1 §3.1）
- Memory: 256MB（DDB + Scheduler 取消のみで軽量）
- Timeout: 5s（3 ジョブ並列削除 + DDB 更新で十分）
- 同時実行: 50（dismiss は intake より低頻度）

---

### 2.2 B-05 CartAttackScheduler（Q4 = A 反映）

#### 責務

- CartWatchItem 登録時刻 `createdAt` を起点に、30m / 6h / 24h の 3 ジョブを EventBridge Scheduler に登録
- 各ジョブは B-06 NotificationDispatcher Lambda を target として one-time invoke
- 「いらない」選択時に 3 ジョブを `DeleteSchedule` で取消
- 失敗ジョブは Lambda DLQ 経由で管理者通知（最終手段）

#### IO 仕様

```python
# backend/src/cart/scheduler.py
import boto3
from datetime import datetime, timedelta, timezone
from typing import Literal

ATTACK_STEPS: dict[Literal["30m", "6h", "24h"], int] = {
    "30m": 1800,
    "6h": 21600,
    "24h": 86400,
}

scheduler = boto3.client("scheduler")
NOTIFICATION_DISPATCHER_ARN = os.environ["NOTIFICATION_DISPATCHER_ARN"]
SCHEDULER_ROLE_ARN = os.environ["SCHEDULER_ROLE_ARN"]

class AttackSchedule(TypedDict):
    """CartWatchItems.attackSchedule に保存する構造"""
    schedule_30m: str  # EventBridge Scheduler の name
    schedule_6h: str
    schedule_24h: str

def schedule_attacks(user_id: str, item_id: str, asin: str, base_time: datetime) -> AttackSchedule:
    """3 段追撃ジョブを作成（Q4 = A: One-time Schedule + ActionAfterCompletion=DELETE）

    2 巡目セルフレビュー後修正（Issue A）: B-06 が CartWatchItems への直接アクセス
    （SK=CART#asin）を可能にするため、Scheduler Input に asin を追加。
    itemId は監査・FK 用の二次的識別子として併送。

    5 巡目セルフレビュー後修正（Issue Y）: Schedule 名衝突を回避するため
    user_id 全体の SHA-256 先頭 12 文字 + asin 10 文字 + timestamp ms 13 文字 + step を組成。
    最大長 = `cart-` (5) + 12 + 1 + 10 + 1 + 13 + 1 + 3 = 46 文字 <= 64 文字制限内。
    再活性化ケース（同 user × 同 asin × 異なる createdAt）でも timestamp で一意性確保。

    7 巡目セルフレビュー後修正（Issue HH）: dev 環境で developerInitial が指定されていれば
    `cart-{init}-...` として個人 sandbox を分離（Lambda 環境変数 `DEV_INITIAL` から取得）。
    """
    schedule_names: dict[str, str] = {}
    user_hash = hashlib.sha256(user_id.encode()).hexdigest()[:12]
    base_ms = int(base_time.timestamp() * 1000)
    dev_initial = os.environ.get("DEV_INITIAL", "")  # 7 巡目: 個人 sandbox suffix
    name_prefix = f"cart-{dev_initial}-" if dev_initial else "cart-"

    for step, offset_seconds in ATTACK_STEPS.items():
        fire_at = base_time + timedelta(seconds=offset_seconds)
        # 衝突回避: user_hash + asin + base_ms + step の組合せで一意化
        schedule_name = f"{name_prefix}{user_hash}-{asin}-{base_ms}-{step}"

        scheduler.create_schedule(
            Name=schedule_name,
            ScheduleExpression=f"at({fire_at.strftime('%Y-%m-%dT%H:%M:%S')})",
            ScheduleExpressionTimezone="UTC",
            FlexibleTimeWindow={"Mode": "OFF"},
            ActionAfterCompletion="DELETE",
            State="ENABLED",
            Target={
                "Arn": NOTIFICATION_DISPATCHER_ARN,
                "RoleArn": SCHEDULER_ROLE_ARN,
                "Input": json.dumps({
                    "userId": user_id,
                    "itemId": item_id,   # 監査・FK 用
                    "asin": asin,        # B-06 が CartWatchItems を直接 GetItem するための主軸
                    "step": step,
                }),
                "RetryPolicy": {
                    "MaximumRetryAttempts": 2,
                    "MaximumEventAgeInSeconds": 600,
                },
            },
        )
        schedule_names[f"schedule_{step}"] = schedule_name

    return AttackSchedule(**schedule_names)

def cancel_attacks(schedule: AttackSchedule) -> None:
    """残り追撃ジョブを取消（US-03-02 AC-4「いらない」選択時）"""
    for step in ("30m", "6h", "24h"):
        name = schedule.get(f"schedule_{step}")
        if not name:
            continue
        try:
            scheduler.delete_schedule(Name=name)
        except scheduler.exceptions.ResourceNotFoundException:
            # 既に発火済 / 削除済みは許容
            pass
```

#### エラー仕様

| 状態 | 挙動 |
|---|---|
| `CreateSchedule` 失敗（5xx） | Lambda 内 try/except で部分失敗許容、CartWatchItem 登録は維持 |
| `DeleteSchedule` で `ResourceNotFoundException` | 既に発火 / 削除済として無視 |
| 100 万スケジュール上限超過 | 予選規模では未到達、決勝後にプロダクト化判断時に再評価（backlog） |
| ジョブ発火時刻に B-06 Lambda が落ちている | EventBridge Scheduler の `RetryPolicy: MaximumRetryAttempts=2` で 2 回再試行、最大 600 秒以内 |

#### IAM Role

`SCHEDULER_ROLE_ARN` は EventBridge Scheduler が NotificationDispatcher を invoke できる権限のみ。CDK で最小権限定義（`PrincipalWithConditions: scheduler.amazonaws.com`）。

---

### 2.3 B-06 NotificationDispatcher（Q3 = A 反映、テンプレートベース）

#### 責務

- EventBridge Scheduler 発火時に invoke される
- CartWatchItems から最新状態取得（status=watching であることを確認）
- SafeguardPolicy（S-03）で配信可否判定（冷却モード / 月間上限）
- ステップ別テンプレートから通知コピー生成（Q3 = A、30 パターン）
- AWS End User Messaging Push API で APNs / FCM 配信
- CartWatchItems の status を `notified-30m` 等に更新（Q8 = A ステータスマシン）
- NotificationLogs に配信ログ記録

#### IO 仕様

```python
# backend/src/cart/handlers/notification_dispatcher.py
import boto3
import random
from datetime import datetime, timezone
from yudane_safeguard_policy import evaluate_notification  # S-03（本 Unit で追加、§2.4 参照）
# 2026-05-29 修正（Issue B2）: main 由来の AuditLogger はクラスベース実装
from backend.src.common.logging import AuditLogger
from common.user_repo import get_user  # Unit-2 提供
from .repository import CartWatchItemsRepo, NotificationLogsRepo
from .notification_templates import TEMPLATES  # 30 パターン静的辞書

end_user_messaging = boto3.client("pinpoint-sms-voice-v2")  # End User Messaging
APPLICATION_ID = os.environ["EUM_APPLICATION_ID"]

def lambda_handler(event, context):
    """EventBridge Scheduler から invoke される

    2 巡目セルフレビュー後修正（Issue A/D/F）:
    - asin を Scheduler Input から受け取り、CART#asin SK で直接 GetItem
    - evaluate_notification に cooldown_until を渡す
    - displayName が空の場合は「あなた」をフォールバック

    2026-05-29 修正（Issue B2）: AuditLogger をクラスベース呼び出しに統一
    """
    audit = AuditLogger(service="cart-notification-dispatcher")
    user_id = event["userId"]
    item_id = event["itemId"]
    asin = event["asin"]                        # Issue A 対応
    step = event["step"]  # "30m" | "6h" | "24h"

    repo = CartWatchItemsRepo()
    logs = NotificationLogsRepo()

    # CartWatchItem の最新状態取得（PK=USER#u, SK=CART#asin の効率的な GetItem）
    item = repo.get(user_id, asin)
    if item is None:
        audit.log("warn", "Cart watch item not found, skipping notification", {
            "userId": user_id, "asin": asin, "itemId": item_id
        })
        return

    # status が dismissed / purchased なら配信しない（Property 5 と整合）
    if item.status in ("dismissed", "purchased"):
        audit.log("info", "Skipping notification for resolved item", {
            "asin": asin, "status": item.status
        })
        return

    # SafeguardPolicy 判定（Property 5、Unit-7 連携、Issue D 対応で cooldown_until を渡す）
    # 2026-05-29 修正（Issue A4）: evaluate_notification は decide_allow ラッパー、戻り値は SafeguardDecision
    user = get_user(user_id)
    decision = evaluate_notification(
        user_id=user_id,
        monthly_limit_yen=user.safeguard.monthly_limit_yen,
        current_budget_used_yen=user.safeguard.current_budget_used_yen,
        cooldown_on=user.safeguard.cooldown_on,
        quiet_week=user.safeguard.quiet_week,
        has_debt=user.safeguard.has_debt,
        cooldown_until=user.safeguard.cooldown_until,  # Issue D: 自動冷却の解除時刻
    )
    if decision.decision == "block":
        logs.create(
            user_id=user_id,
            item_id=item.itemId,
            channel=f"cart-attack-{step}",
            status="suppressed_by_safeguard",
            reason_code=decision.reason_code,  # 例: safeguard.cooldown / safeguard.monthly-limit-exceeded
            sent_at=datetime.now(timezone.utc),
        )
        audit.metric("notification.suppressed_by_safeguard", 1, "Count", {"step": step, "reason": decision.reason_code})
        return

    # Q3 = A 反映：テンプレート選択 + 商品メタ埋め込み（Issue F: displayName フォールバック）
    user_name = user.display_name or "あなた"
    copy = generate_copy(step, item.product_meta, user_name)

    # End User Messaging Push 配信
    try:
        response = end_user_messaging.send_messages(
            ApplicationId=APPLICATION_ID,
            MessageRequest={
                "Addresses": {user.push_endpoint_id: {"ChannelType": user.push_platform}},
                "MessageConfiguration": build_message_config(copy, asin, step),
            },
        )
        delivery_status = "sent"
        delivery_receipt = response.get("MessageResponse", {}).get("Result", {})
    except Exception as e:
        audit.log("error", "Push delivery failed", {"asin": asin, "error": str(e)})
        delivery_status = "failed"
        delivery_receipt = {"error": str(e)}

    # NotificationLogs に記録
    logs.create(
        user_id=user_id,
        item_id=item.itemId,
        channel=f"cart-attack-{step}",
        copy=copy,
        status=delivery_status,
        delivery_receipt=delivery_receipt,
        sent_at=datetime.now(timezone.utc),
    )

    # CartWatchItem の status 更新（Q8 = A ステータスマシン）
    if delivery_status == "sent":
        repo.transition_status(user_id, asin, f"notified-{step}")

    audit.metric("notification.dispatched", 1, "Count", {"step": step, "status": delivery_status})


def generate_copy(step: str, product_meta: ProductMeta, user_name: str) -> dict:
    """Q3 = A 反映：30 パターンから 1 つランダム選択 + 商品名 / 価格を埋め込み"""
    templates = TEMPLATES[step]  # 10 パターン
    template = random.choice(templates)
    return {
        "title": template["title"].format(product=product_meta.title[:20], user=user_name),
        "body": template["body"].format(
            product=product_meta.title[:30],
            price=f"¥{product_meta.price_yen:,}",
            user=user_name,
        ),
    }


def build_message_config(copy: dict, asin: str, step: str) -> dict:
    """Issue A 対応: Deep Link は asin ベース（CartInterceptScreen の useCartWatchItem(asin) と整合）

    Push payload の Data は Unit-3 契約に整合させ productId キーで送信（値は ASIN）
    """
    deep_link = f"yudane://cart-attack/{asin}?step={step}"
    return {
        "APNSMessage": {
            "Title": copy["title"],
            "Body": copy["body"],
            "Action": "OPEN_APP",
            "Url": deep_link,
            "Sound": "default",
            "Data": {"productId": asin, "step": step, "type": f"cart-attack-{step}"},
        },
        "GCMMessage": {
            "Title": copy["title"],
            "Body": copy["body"],
            "Action": "OPEN_APP",
            "Url": deep_link,
            "Data": {"productId": asin, "step": step, "type": f"cart-attack-{step}"},
        },
    }
```

#### 通知テンプレート（30 パターン、`backend/src/cart/notification_templates.py`）

```python
# Q3 = A 反映：30m / 6h / 24h × 10 パターン = 30 通り
# トーン使い分け（US-03-02 AC-2）：
#   30m = 「軽い論破」（友達系のリマインド）
#   6h  = 「記憶想起」（「そういえば…」）
#   24h = 「最終通告」（「今夜決める？」）
# NG-6（脅迫禁止）静的検証用 NG キーワード：「ストレス悪化」「失敗」「罪悪感」「後悔」等

TEMPLATES = {
    "30m": [
        {"title": "{product}、まだ気になってる？", "body": "30 分前に見てたやつ、忘れる前に話そ"},
        {"title": "さっきのやつ、再考タイム", "body": "{product} ¥{price}、迷ってるなら 1 分話そう"},
        {"title": "ねぇ、{product} のことだけど", "body": "今ならサクッと決められそう。話す？"},
        {"title": "{product} に戻る？", "body": "30 分経ったよ、もう一回見てみる？"},
        {"title": "あの商品、覚えてる？", "body": "{product}、まだあるよ。確保しといた"},
        {"title": "1 分だけ、論破させて", "body": "{product}、買わない理由ある？"},
        {"title": "さっきの続きしよう", "body": "{product} ¥{price}、納得いくまで話そう"},
        {"title": "{user} へのお知らせ", "body": "{product} を確保中。いま決める？"},
        {"title": "あれ、まだ迷ってる？", "body": "{product}、サクッと終わらせよ"},
        {"title": "{product} 、置いとくね", "body": "30 分経過。まだ気になるなら話そう"},
    ],
    "6h": [
        {"title": "{product}、まだ気になってる？", "body": "そういえば朝見てたやつ。今ならどう？"},
        {"title": "今日のお買い物候補", "body": "{product} ¥{price}、まだ確保中だよ"},
        {"title": "ふと思い出した", "body": "{product}、6 時間前のあれ、決めた？"},
        {"title": "{user} のリスト確認", "body": "{product}、もう一度見てみる？"},
        {"title": "そろそろ決断タイム？", "body": "{product}、迷うなら話そ"},
        {"title": "今日の {user} のために", "body": "{product} ¥{price}、用意できてるよ"},
        {"title": "{product}、再登場", "body": "朝の続き、今ならどう感じる？"},
        {"title": "まだあるよ、{product}", "body": "確保しておいた。納得いくまで考えて"},
        {"title": "今日中に決める？", "body": "{product} ¥{price}、お預け状態だよ"},
        {"title": "ふと、{product} のこと", "body": "6 時間経った。話す気あったら呼んで"},
    ],
    "24h": [
        {"title": "{product}、今夜決める？", "body": "1 日経ったよ。最後のチャンス、話そう"},
        {"title": "{user} のために最終提案", "body": "{product} ¥{price}、今夜が決め時かも"},
        {"title": "明日には忘れる前に", "body": "{product}、まだ確保してるよ。話そっか"},
        {"title": "そろそろ手放す？", "body": "{product} ¥{price}、24h 経過。ラストコール"},
        {"title": "{product}、最終確認", "body": "決断するなら今夜。1 分だけちょうだい"},
        {"title": "1 日寝かせた {product}", "body": "もう一度だけ、考え直してみる？"},
        {"title": "今夜の {user} へ", "body": "{product}、24 時間悩んだあれ、決めよう"},
        {"title": "{product}、ラストコール", "body": "今夜中に決めれば、論破する用意あるよ"},
        {"title": "1 日経ったね", "body": "{product} ¥{price}、まだ気になるなら話そ"},
        {"title": "最後の {product}", "body": "24h 経過。今夜決めるなら呼んで"},
    ],
}
```

#### NG-6 静的検証

CI で `npm run check-ng-keywords` を実行し、テンプレート全 30 パターンに対し以下の禁止ワード辞書をチェック:

```python
NG_KEYWORDS = [
    "ストレス悪化", "失敗", "罪悪感", "後悔", "怒られる", "嫌われる",
    "孤独", "病気", "不健康", "貧乏", "破産", "借金",
    # NG-3, NG-6, NG-7 由来
]
```

該当ワード検出時は CI fail。Q3 = A の利点として、**全パターンを CI で静的に検証可能**（LLM 動的生成では事後モデレーションが必須）。

---

### 2.4 S-03 SafeguardPolicy への拡張（本 Unit で追加）

Unit-1 [S-03 SafeguardPolicy](../../unit-1-platform/functional-design/functional-design.md#63-s-03-safeguardpolicy) と main 由来の正本実装（[shared/safeguard-policy/](../../../../shared/safeguard-policy/)）は **`decide_allow` / `decideAllow`** を提供する（business-rules.md SG-01〜10、Q2=A 段階評価）。本 Unit では B-06 NotificationDispatcher が Property 5（通知抑制）を担保するため、`decide_allow` を拡張する形で **`evaluate_notification` ラッパー関数**を追加する。

> **2026-05-29 改訂（Issue A4 対応）**: 当初の `evaluate_notification` 独自実装は既存 `decide_allow` と評価順 / 引数名 / 戻り値の 3 点で乖離していた:
>
> - 評価順乖離: 当初 `quiet_week → cooldown_on → cooldown_until → monthly_limit` vs SG-01 規約 `cooldown → quietWeek → 上限超過 → warn 80% → allow`
> - 引数名乖離: 当初 `monthly_used` / `monthly_limit` vs 実装 `current_budget_used_yen` / `monthly_limit_yen`、`has_debt` 引数欠落
> - 戻り値乖離: 当初 `Literal["allow", "block"]` vs 実装 `SafeguardDecision { decision, reason_code, effective_limit_yen, remaining_yen }`、warn 欠落で SG-06 違反
>
> 修正後は **`decide_allow` ラッパー方式**で、業務ロジックは既存実装に委譲し本関数は通知特有の条件（`cooldown_until` 自動冷却 / warn → block 格上げ）のみ担当する。

#### TypeScript 版（`shared/safeguard-policy/src/decide-allow.ts` 拡張）

既存 `decideAllow` の入力型 `SafeguardInput` は維持しつつ、通知判定用の薄いラッパーを追加する:

```typescript
import { decideAllow, type SafeguardInput, type SafeguardDecision } from './decide-allow';

/** 通知判定の追加コンテキスト（cooldown_until 自動冷却を SG-01 に追加）。 */
export interface NotificationContext {
  userId: string;
  monthlyLimitYen: number;
  currentBudgetUsedYen: number;
  cooldownOn: boolean;
  cooldownUntil?: string;          // ISO 8601、自動冷却の解除時刻（未来なら block）
  quietWeek: boolean;
  hasDebt: boolean;
}

/**
 * 通知配信可否判定（B-06 NotificationDispatcher が呼び出す）。
 *
 * `decideAllow` を内包し、以下 2 点を追加:
 * 1. `cooldownUntil` が現在時刻より未来 → block（自動冷却、SG-02 直前で評価）
 * 2. `decideAllow` の `warn` 判定は通知では `block` に格上げ（プッシュ通知は介入性が高く、
 *    NG-6 罪悪感強要を避けるため near-limit 時も通知抑制、SG-07 の例外）
 *
 * 戻り値は既存 `SafeguardDecision` を維持（reason_code / effective_limit_yen / remaining_yen
 * を NotificationLogs に記録するため）。
 */
export function evaluateNotification(ctx: NotificationContext): SafeguardDecision {
  // 自動冷却（SG-02 cooldownOn の手動フラグに加えて時刻ベース）
  if (ctx.cooldownUntil && new Date(ctx.cooldownUntil) > new Date()) {
    return {
      decision: 'block',
      reasonCode: 'safeguard.cooldown',
      effectiveLimitYen: ctx.monthlyLimitYen,
      remainingYen: Math.max(0, ctx.monthlyLimitYen - ctx.currentBudgetUsedYen),
    };
  }

  const input: SafeguardInput = {
    transitionCountMonth: 0,  // 通知判定では未使用
    monthlyLimitYen: ctx.monthlyLimitYen,
    currentBudgetUsedYen: ctx.currentBudgetUsedYen,
    flags: {
      cooldownOn: ctx.cooldownOn,
      quietWeek: ctx.quietWeek,
      hasDebt: ctx.hasDebt,
    },
  };
  const decision = decideAllow(input);

  // warn は通知では block に格上げ（SG-07 例外）
  if (decision.decision === 'warn') {
    return { ...decision, decision: 'block' };
  }
  return decision;
}
```

#### Python 版（`shared/safeguard-policy/python/safeguard_policy.py` 拡張）

```python
from datetime import datetime, timezone
from typing import Optional
from safeguard_policy import (
    decide_allow,
    SafeguardInput,
    SafeguardFlags,
    SafeguardDecision,
)

def evaluate_notification(
    user_id: str,
    monthly_limit_yen: int,
    current_budget_used_yen: int,
    cooldown_on: bool,
    quiet_week: bool,
    has_debt: bool,
    cooldown_until: Optional[str] = None,
) -> SafeguardDecision:
    """通知配信可否判定（B-06 NotificationDispatcher が呼び出す）。

    decide_allow ラッパー。SG-01 評価順を継承しつつ、以下 2 点を追加:
    1. cooldown_until が現在時刻より未来 → block（自動冷却、SG-02 直前で評価）
    2. decide_allow の warn 判定は通知では block に格上げ（SG-07 例外、NG-6 配慮）

    Returns:
        SafeguardDecision: 既存型を維持（reason_code 等を NotificationLogs に記録）
    """
    # 自動冷却（SG-02 cooldown_on の手動フラグに加えて時刻ベース）
    if cooldown_until and datetime.fromisoformat(cooldown_until) > datetime.now(timezone.utc):
        return SafeguardDecision(
            decision="block",
            reason_code="safeguard.cooldown",
            effective_limit_yen=monthly_limit_yen,
            remaining_yen=max(0, monthly_limit_yen - current_budget_used_yen),
        )

    input_data = SafeguardInput(
        transition_count_month=0,  # 通知判定では未使用
        monthly_limit_yen=monthly_limit_yen,
        current_budget_used_yen=current_budget_used_yen,
        flags=SafeguardFlags(
            cooldown_on=cooldown_on,
            quiet_week=quiet_week,
            has_debt=has_debt,
        ),
    )
    decision = decide_allow(input_data)

    # warn は通知では block に格上げ（SG-07 例外）
    if decision.decision == "warn":
        return SafeguardDecision(
            decision="block",
            reason_code=decision.reason_code,
            effective_limit_yen=decision.effective_limit_yen,
            remaining_yen=decision.remaining_yen,
        )
    return decision
```

#### S-03 への追加責任分界

- 本関数の **TypeScript 版** は、将来 Mobile 側でも同一判定を走らせる（例: SafeguardScreen で「冷却モード ON 時は通知が来ない」表示）場合に使用
- 現時点では Backend のみで使用するが、Shared 層に置くことで Mobile/Backend の判定一貫性を保証（要件書 §6.4 SECURITY-11、Mobile と Backend で同一ロジック）
- PR は本 Unit が owner として `shared/safeguard-policy/` に追加するが、Unit-7 Safeguard owner（Member C）にコードレビュー必須（[api-contracts.md](../../../../.kiro/steering/api-contracts.md) Shared 層変更ルールに整合）
- 既存 `decide_allow` の評価順（SG-01）/ 戻り値型（SafeguardDecision）/ 定数（DEFAULT_MONTHLY_LIMIT_RATIO 等）を**一切変更しない**ため、Unit-1 / Unit-7 への波及影響なし
- PBT-02 / PBT-07: Hypothesis / fast-check で `evaluate_notification` の任意入力での block 整合性検証（特に warn → block 格上げ / cooldown_until 時刻判定の境界条件）

---

## 3. Infrastructure（`infra/lib/cart-stack.ts`）

### 3.1 Stack 構成

```typescript
// infra/lib/cart-stack.ts（Snapshot TDD で先に test を書く）
interface CartStackProps extends StackProps {
  envName: 'dev' | 'prd';
  developerInitial?: string;        // 個人 sandbox suffix（C-4 確定、Unit-1 data-model §2.1 整合）
  platformStack: PlatformStack;    // KMS / IdempotencyKeys を参照
  authStack: AuthStack;             // Users テーブルを参照
  safeguardStack: SafeguardStack;   // 3 巡目: SafeguardStates テーブルを参照（B-06 配信判定用）
}

// 7 巡目追加（Issue HH）: 個人 sandbox suffix を組み込んだリソース名生成ヘルパー
function resourceName(props: CartStackProps, baseName: string): string {
  // dev 環境かつ developerInitial 指定時のみ suffix 付与（prd 環境では常に未付与）
  if (props.envName === 'dev' && props.developerInitial) {
    return `yudane-${props.envName}-${props.developerInitial}-${baseName}`;
  }
  return `yudane-${props.envName}-${baseName}`;
}

export class CartStack extends Stack {
  public readonly cartWatchItemsTable: dynamodb.Table;
  public readonly notificationLogsTable: dynamodb.Table;
  public readonly cartIntakeFunction: lambda.Function;
  public readonly cartDismissFunction: lambda.Function;          // 3 巡目: Issue K
  public readonly cartListFunction: lambda.Function;             // 6 巡目: Issue FF
  public readonly pushTokenFunction: lambda.Function;            // 6 巡目: Issue FF
  public readonly cartAttackSchedulerRetryFunction: lambda.Function;  // NFR Design Q4 = A' 追加
  public readonly notificationDispatcherFunction: lambda.Function;
  public readonly schedulerInvokeRole: iam.Role;

  constructor(scope: Construct, id: string, props: CartStackProps) {
    super(scope, id, props);

    // CartWatchItems テーブル（Q8 = A ステータスマシン、詳細は data-model.md §1）
    this.cartWatchItemsTable = new dynamodb.Table(this, 'CartWatchItemsTable', {
      tableName: resourceName(props, 'cart-watch-items'),
      partitionKey: { name: 'PK', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'SK', type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      encryption: dynamodb.TableEncryption.CUSTOMER_MANAGED,
      encryptionKey: props.platformStack.kmsKey,
      timeToLiveAttribute: 'ttl',
      pointInTimeRecoverySpecification: {
        pointInTimeRecoveryEnabled: props.envName === 'prd',
      },
      removalPolicy: props.envName === 'prd' ? RemovalPolicy.RETAIN : RemovalPolicy.DESTROY,
      deletionProtection: props.envName === 'prd',
    });
    this.cartWatchItemsTable.addGlobalSecondaryIndex({
      indexName: 'GSI1-status-createdAt',
      partitionKey: { name: 'GSI1PK', type: dynamodb.AttributeType.STRING },  // STATUS#{status}
      sortKey: { name: 'GSI1SK', type: dynamodb.AttributeType.STRING },        // {createdAt}
      projectionType: dynamodb.ProjectionType.ALL,
    });

    // NotificationLogs テーブル
    this.notificationLogsTable = new dynamodb.Table(this, 'NotificationLogsTable', {
      tableName: resourceName(props, 'notification-logs'),
      partitionKey: { name: 'PK', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'SK', type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      encryption: dynamodb.TableEncryption.CUSTOMER_MANAGED,
      encryptionKey: props.platformStack.kmsKey,
      timeToLiveAttribute: 'ttl',
      removalPolicy: props.envName === 'prd' ? RemovalPolicy.RETAIN : RemovalPolicy.DESTROY,
    });
    // GSI1: cartWatchItemId × sentAt（特定アイテムの通知履歴クエリ用）
    this.notificationLogsTable.addGlobalSecondaryIndex({
      indexName: 'GSI1-cartWatchItemId',
      partitionKey: { name: 'cartWatchItemId', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'sentAt', type: dynamodb.AttributeType.STRING },
      projectionType: dynamodb.ProjectionType.ALL,
    });

    // EventBridge Scheduler Invoke Role（NotificationDispatcher を呼ぶ最小権限）
    // 3 巡目セルフレビュー後修正（Issue L）: Confused Deputy 対策で SourceAccount / SourceArn 条件追加
    this.schedulerInvokeRole = new iam.Role(this, 'SchedulerInvokeRole', {
      assumedBy: new iam.ServicePrincipal('scheduler.amazonaws.com', {
        conditions: {
          StringEquals: { 'aws:SourceAccount': this.account },
          ArnLike: {
            'aws:SourceArn': `arn:aws:scheduler:${this.region}:${this.account}:schedule/default/cart-*`,
          },
        },
      }),
    });

    // B-04 CartIntakeHandler（VPC 外、Unit-1 §3.1）
    this.cartIntakeFunction = new lambda.Function(this, 'CartIntakeFunction', {
      functionName: resourceName(props, 'cart-intake'),
      runtime: lambda.Runtime.PYTHON_3_13,
      architecture: lambda.Architecture.ARM_64,
      handler: 'handlers.cart_intake.lambda_handler',
      code: lambda.Code.fromAsset('../backend/src/cart'),
      memorySize: 512,
      timeout: Duration.seconds(5),
      environment: {
        CART_WATCH_ITEMS_TABLE: this.cartWatchItemsTable.tableName,
        NOTIFICATION_DISPATCHER_ARN: '',  // 下で循環参照解消
        SCHEDULER_ROLE_ARN: this.schedulerInvokeRole.roleArn,
        IDEMPOTENCY_KEYS_TABLE: props.platformStack.idempotencyKeysTable.tableName,
        IDEMPOTENCY_BUCKET: props.platformStack.idempotencyBucket.bucketName,
        DEV_INITIAL: props.developerInitial ?? '',  // 7 巡目: Issue HH（Schedule 名衝突回避）
      },
    });

    // B-04 dismiss handler（3 巡目: Issue K で別 Lambda として明示）
    this.cartDismissFunction = new lambda.Function(this, 'CartDismissFunction', {
      functionName: resourceName(props, 'cart-dismiss'),
      runtime: lambda.Runtime.PYTHON_3_13,
      architecture: lambda.Architecture.ARM_64,
      handler: 'handlers.cart_dismiss.dismiss_lambda_handler',
      code: lambda.Code.fromAsset('../backend/src/cart'),
      memorySize: 256,
      timeout: Duration.seconds(5),
      reservedConcurrentExecutions: 50,
      environment: {
        CART_WATCH_ITEMS_TABLE: this.cartWatchItemsTable.tableName,
      },
    });

    // B-04 cart_list handler（6 巡目: Issue FF で別 Lambda として明示）
    this.cartListFunction = new lambda.Function(this, 'CartListFunction', {
      functionName: resourceName(props, 'cart-list'),
      runtime: lambda.Runtime.PYTHON_3_13,
      architecture: lambda.Architecture.ARM_64,
      handler: 'handlers.cart_list.list_lambda_handler',
      code: lambda.Code.fromAsset('../backend/src/cart'),
      memorySize: 256,
      timeout: Duration.seconds(3),
      reservedConcurrentExecutions: 100,  // 一覧取得は intake より高頻度（M-05 起動毎）
      environment: {
        CART_WATCH_ITEMS_TABLE: this.cartWatchItemsTable.tableName,
      },
    });

    // B-04 push_token handler（6 巡目: Issue FF で別 Lambda として明示）
    this.pushTokenFunction = new lambda.Function(this, 'PushTokenFunction', {
      functionName: resourceName(props, 'push-token'),
      runtime: lambda.Runtime.PYTHON_3_13,
      architecture: lambda.Architecture.ARM_64,
      handler: 'handlers.push_token.register_lambda_handler',
      code: lambda.Code.fromAsset('../backend/src/cart'),
      memorySize: 256,
      timeout: Duration.seconds(5),
      reservedConcurrentExecutions: 20,  // トークン更新は低頻度（起動毎 + ローテーション時のみ）
      environment: {
        USERS_TABLE: props.authStack.usersTable.tableName,
        IDEMPOTENCY_KEYS_TABLE: props.platformStack.idempotencyKeysTable.tableName,
        IDEMPOTENCY_BUCKET: props.platformStack.idempotencyBucket.bucketName,
        EUM_APPLICATION_ID: '',  // SSM Parameter から注入
      },
    });

    // B-05 cart_attack_scheduler_retry handler（NFR Design Q4 = A' 追加）
    this.cartAttackSchedulerRetryFunction = new lambda.Function(this, 'CartAttackSchedulerRetryFunction', {
      functionName: resourceName(props, 'cart-attack-scheduler-retry'),
      runtime: lambda.Runtime.PYTHON_3_13,
      architecture: lambda.Architecture.ARM_64,
      handler: 'handlers.cart_attack_scheduler_retry.lambda_handler',
      code: lambda.Code.fromAsset('../backend/src/cart'),
      memorySize: 512,
      timeout: Duration.seconds(60),
      reservedConcurrentExecutions: 10,  // バックグラウンド処理、低並列度
      environment: {
        CART_WATCH_ITEMS_TABLE: this.cartWatchItemsTable.tableName,
        NOTIFICATION_DISPATCHER_ARN: '',   // 下で循環参照解消
        SCHEDULER_ROLE_ARN: this.schedulerInvokeRole.roleArn,
        DEV_INITIAL: props.developerInitial ?? '',
      },
    });

    // EventBridge Schedule: cart_attack_scheduler_retry を 15 分間隔で起動
    new scheduler.CfnSchedule(this, 'CartAttackSchedulerRetrySchedule', {
      name: resourceName(props, 'cart-attack-scheduler-retry-schedule'),
      scheduleExpression: 'rate(15 minutes)',
      flexibleTimeWindow: { mode: 'OFF' },
      target: {
        arn: this.cartAttackSchedulerRetryFunction.functionArn,
        roleArn: this.schedulerInvokeRole.roleArn,
      },
      state: 'ENABLED',
    });

    // B-05 CartAttackScheduler（B-04 内で同期呼出されるため独立 Lambda は不要、ライブラリ化）
    // → 本 Stack では IAM 権限のみ追加（cart-intake-function に scheduler:CreateSchedule 付与）

    // B-06 NotificationDispatcher（VPC 外）
    this.notificationDispatcherFunction = new lambda.Function(this, 'NotificationDispatcherFunction', {
      functionName: resourceName(props, 'notification-dispatcher'),
      runtime: lambda.Runtime.PYTHON_3_13,
      architecture: lambda.Architecture.ARM_64,
      handler: 'handlers.notification_dispatcher.lambda_handler',
      code: lambda.Code.fromAsset('../backend/src/cart'),
      memorySize: 512,
      timeout: Duration.seconds(10),
      deadLetterQueueEnabled: true,
      deadLetterQueue: new sqs.Queue(this, 'NotificationDispatcherDlq', {
        retentionPeriod: Duration.days(14),
        encryptionMasterKey: props.platformStack.kmsKey,
      }),
      environment: {
        CART_WATCH_ITEMS_TABLE: this.cartWatchItemsTable.tableName,
        NOTIFICATION_LOGS_TABLE: this.notificationLogsTable.tableName,
        EUM_APPLICATION_ID: '',  // SSM Parameter から注入（下記）
      },
    });

    // 循環参照解消：NotificationDispatcher ARN を CartIntakeFunction に環境変数注入
    this.cartIntakeFunction.addEnvironment(
      'NOTIFICATION_DISPATCHER_ARN',
      this.notificationDispatcherFunction.functionArn,
    );

    // IAM 権限
    this.cartWatchItemsTable.grantReadWriteData(this.cartIntakeFunction);
    this.cartWatchItemsTable.grantReadWriteData(this.cartDismissFunction);          // 3 巡目: Issue K
    this.cartWatchItemsTable.grantReadData(this.cartListFunction);                  // 6 巡目: Issue FF（読み取り専用）
    this.cartWatchItemsTable.grantReadWriteData(this.cartAttackSchedulerRetryFunction);  // NFR Design Q4 = A'（status 遷移含む）
    this.cartWatchItemsTable.grantReadWriteData(this.notificationDispatcherFunction);
    props.authStack.usersTable.grantReadWriteData(this.pushTokenFunction);          // 6 巡目: pushEndpointId 更新
    this.notificationLogsTable.grantWriteData(this.notificationDispatcherFunction);
    props.authStack.usersTable.grantReadData(this.notificationDispatcherFunction);
    props.safeguardStack.safeguardStatesTable.grantReadData(this.notificationDispatcherFunction);  // 3 巡目: SafeguardStates 読取明示
    this.cartIntakeFunction.addToRolePolicy(new iam.PolicyStatement({
      actions: ['scheduler:CreateSchedule', 'scheduler:GetSchedule'],
      resources: [`arn:aws:scheduler:${this.region}:${this.account}:schedule/default/cart-*`],  // 3 巡目: Wildcard 範囲を限定（個人 sandbox の cart-{init}-* も同パターンに含まれる）
    }));
    this.cartDismissFunction.addToRolePolicy(new iam.PolicyStatement({
      actions: ['scheduler:DeleteSchedule', 'scheduler:GetSchedule'],
      resources: [`arn:aws:scheduler:${this.region}:${this.account}:schedule/default/cart-*`],
    }));
    this.cartAttackSchedulerRetryFunction.addToRolePolicy(new iam.PolicyStatement({
      actions: ['scheduler:CreateSchedule', 'scheduler:GetSchedule'],  // NFR Design Q4 = A' リトライ補完
      resources: [`arn:aws:scheduler:${this.region}:${this.account}:schedule/default/cart-*`],
    }));
    this.cartIntakeFunction.addToRolePolicy(new iam.PolicyStatement({
      actions: ['iam:PassRole'],
      resources: [this.schedulerInvokeRole.roleArn],
    }));
    this.cartAttackSchedulerRetryFunction.addToRolePolicy(new iam.PolicyStatement({
      actions: ['iam:PassRole'],
      resources: [this.schedulerInvokeRole.roleArn],
    }));
    this.schedulerInvokeRole.addToPolicy(new iam.PolicyStatement({
      actions: ['lambda:InvokeFunction'],
      resources: [
        this.notificationDispatcherFunction.functionArn,
        this.cartAttackSchedulerRetryFunction.functionArn,        // NFR Design Q4 = A' rate(15min) Schedule 用
      ],
    }));

    // End User Messaging Push 権限
    this.notificationDispatcherFunction.addToRolePolicy(new iam.PolicyStatement({
      actions: ['mobiletargeting:SendMessages'],
      resources: ['*'],
    }));
    this.pushTokenFunction.addToRolePolicy(new iam.PolicyStatement({
      actions: ['mobiletargeting:UpdateEndpoint', 'mobiletargeting:GetEndpoint'],
      resources: ['*'],   // Endpoint ID は実行時動的決定
    }));

    // SSM Parameter（他 Stack から参照）
    // 7 巡目: 個人 sandbox 環境では `/yudane/dev/{init}/cart/...` のパスに変更
    const ssmPathPrefix = props.envName === 'dev' && props.developerInitial
      ? `/yudane/${props.envName}/${props.developerInitial}/cart`
      : `/yudane/${props.envName}/cart`;
    new ssm.StringParameter(this, 'CartWatchItemsTableArn', {
      parameterName: `${ssmPathPrefix}/cart-watch-items-table-arn`,
      stringValue: this.cartWatchItemsTable.tableArn,
    });
    new ssm.StringParameter(this, 'NotificationLogsTableArn', {
      parameterName: `${ssmPathPrefix}/notification-logs-table-arn`,
      stringValue: this.notificationLogsTable.tableArn,
    });
  }
}
```

### 3.2 cdk-nag 対応

- `AwsSolutions-IAM5: Wildcard permissions` for `mobiletargeting:SendMessages` → Suppression 理由「End User Messaging Push の Endpoint ID は実行時に動的決定、IAM Resource を事前特定不可」
- `AwsSolutions-SQS3: DLQ encryption` → Platform Stack の KMS キーで暗号化済み
- 3 巡目: Scheduler 関連の wildcard は `arn:aws:scheduler:*:*:schedule/default/cart-*` で範囲限定済み（cdk-nag pass 期待）

### 3.3 CloudWatch Alarms（5 巡目追加、Issue Z）

決勝デモ時の障害検知のため、本 Unit owner として以下のアラームを CDK 定義する:

```typescript
// infra/lib/cart-stack.ts に追加
import * as cloudwatch from 'aws-cdk-lib/aws-cloudwatch';
import * as cw_actions from 'aws-cdk-lib/aws-cloudwatch-actions';
import * as sns from 'aws-cdk-lib/aws-sns';

// SNS トピック（Slack #yudane-emergency に連携、Member A が運用）
const alertTopic = sns.Topic.fromTopicArn(this, 'YudaneAlerts',
  ssm.StringParameter.valueForStringParameter(this,
    `/yudane/${props.envName}/platform/alerts-topic-arn`));

// Alarm 1: B-06 NotificationDispatcher の DLQ にメッセージが到達
new cloudwatch.Alarm(this, 'NotificationDispatcherDlqAlarm', {
  metric: notificationDispatcherDlq.metricApproximateNumberOfMessagesVisible(),
  threshold: 1,
  evaluationPeriods: 1,
  treatMissingData: cloudwatch.TreatMissingData.NOT_BREACHING,
  alarmDescription: 'B-06 NotificationDispatcher の Lambda DLQ にメッセージ到達。配信失敗を調査せよ',
}).addAlarmAction(new cw_actions.SnsAction(alertTopic));

// Alarm 2: notification.dispatched の status=failed 比率が 5% 超
new cloudwatch.Alarm(this, 'NotificationFailureRateAlarm', {
  metric: new cloudwatch.MathExpression({
    expression: '(failed / (sent + failed)) * 100',
    usingMetrics: {
      failed: new cloudwatch.Metric({
        namespace: 'Yudane/Cart', metricName: 'notification.dispatched',
        dimensionsMap: { status: 'failed' }, statistic: 'Sum', period: Duration.minutes(5),
      }),
      sent: new cloudwatch.Metric({
        namespace: 'Yudane/Cart', metricName: 'notification.dispatched',
        dimensionsMap: { status: 'sent' }, statistic: 'Sum', period: Duration.minutes(5),
      }),
    },
  }),
  threshold: 5,  // 5% 超
  evaluationPeriods: 2,
  treatMissingData: cloudwatch.TreatMissingData.NOT_BREACHING,
}).addAlarmAction(new cw_actions.SnsAction(alertTopic));

// Alarm 3: cart.scheduler.create_failed が 5 分間で 5 件超
new cloudwatch.Alarm(this, 'SchedulerCreateFailureAlarm', {
  metric: new cloudwatch.Metric({
    namespace: 'Yudane/Cart', metricName: 'cart.scheduler.create_failed',
    statistic: 'Sum', period: Duration.minutes(5),
  }),
  threshold: 5,
  evaluationPeriods: 1,
}).addAlarmAction(new cw_actions.SnsAction(alertTopic));

// Alarm 4: B-04 / cart-dismiss / cart-list / push-token / B-06 各 Lambda の Error 率
[
  this.cartIntakeFunction, this.cartDismissFunction,
  this.cartListFunction, this.pushTokenFunction,                  // 6 巡目: 追加
  this.notificationDispatcherFunction,
  this.cartAttackSchedulerRetryFunction,                          // NFR Design Q4 = A' 追加
].forEach(fn => {
  new cloudwatch.Alarm(this, `${fn.node.id}ErrorAlarm`, {
    metric: fn.metricErrors({ period: Duration.minutes(5) }),
    threshold: 5,
    evaluationPeriods: 2,
  }).addAlarmAction(new cw_actions.SnsAction(alertTopic));
});

// Alarm 5: cart.scheduler.retry_failed が 15 分間で 5 件超（NFR Design Q4 = A' 追加）
new cloudwatch.Alarm(this, 'SchedulerRetryFailureAlarm', {
  metric: new cloudwatch.Metric({
    namespace: 'Yudane/Cart', metricName: 'cart.scheduler.retry_failed',
    statistic: 'Sum', period: Duration.minutes(15),
  }),
  threshold: 5,
  evaluationPeriods: 1,
  alarmDescription: 'B-05 リトライバッチで 3 回失敗が頻発、watching_orphaned 遷移が増えている。手動復旧対象アイテムの確認を要する',
}).addAlarmAction(new cw_actions.SnsAction(alertTopic));
```

> **運用責任**: 上記アラームは Member A（Platform / 横断レビュー担当）が SNS → Slack 連携を運用、Member D（Unit-5 owner）は alarm 発火時の 1 次調査を担当（[AGENTS.md §11.3](../../../../.kiro/steering/AGENTS.md#113-コミュニケーションチャネル)）。

### 3.4 ダミーカタログ仕様（5 巡目追加、Issue AA / §8 A-10 関連）

Amazon Approved Mobile Application 申請承認前（〜2026-06-15 想定）は、B-11 CreatorsApiClient の代わりにダミーカタログから商品メタを返却する。

**配置**: `backend/src/cart/_dummy_catalog.py`

**データ構造**:

```python
# backend/src/cart/_dummy_catalog.py
from typing import Optional

# mockup/assets/products/ の SVG 4 種に対応する 4 商品 + デモ用追加 6 商品 = 10 件
DUMMY_CATALOG: dict[str, dict] = {
    "B0DGHYDZSB": {  # Sony WF-1000XM5（mockup ホーム画面で使用）
        "asin": "B0DGHYDZSB",
        "title": "Sony WF-1000XM5 ワイヤレスノイズキャンセリングイヤホン",
        "priceYen": 41800,
        "imageUrl": "https://yudane-dummy-catalog.s3.ap-northeast-1.amazonaws.com/earbuds.svg",
        "reviewSummary": "★4.5 / 業界最高クラスのノイキャン",
        "brand": "Sony", "category": "audio",
    },
    "B09JZJSF1L": {  # ウィスキー
        "asin": "B09JZJSF1L",
        "title": "響 21年 ジャパニーズハーモニー",
        "priceYen": 198000,
        "imageUrl": "https://yudane-dummy-catalog.s3.ap-northeast-1.amazonaws.com/whisky.svg",
        "reviewSummary": "★4.7 / 限定流通の至高",
        "brand": "Suntory", "category": "luxury",
    },
    "B08L5T8R7K": {  # デスクライト
        "asin": "B08L5T8R7K",
        "title": "BenQ ScreenBar Halo モニターライト",
        "priceYen": 19900,
        "imageUrl": "https://yudane-dummy-catalog.s3.ap-northeast-1.amazonaws.com/desk-lamp.svg",
        "reviewSummary": "★4.6 / 在宅ワークの目疲れ軽減",
        "brand": "BenQ", "category": "home-office",
    },
    "B07X9JRKR2": {  # 書籍
        "asin": "B07X9JRKR2",
        "title": "FACTFULNESS 10の思い込みを乗り越え、データを基に世界を正しく見る習慣",
        "priceYen": 1980,
        "imageUrl": "https://yudane-dummy-catalog.s3.ap-northeast-1.amazonaws.com/book.svg",
        "reviewSummary": "★4.4 / ビル・ゲイツ推薦",
        "brand": "Hans Rosling", "category": "book",
    },
    # ... デモ用追加 6 商品（家電 / コーヒー / アウトドア / 衣服 / コスメ / 食品）
}

def get_dummy_item_by_asin(asin: str) -> Optional[dict]:
    """B-11 CreatorsApiClient の代替（§8 A-10 期間中のみ使用）"""
    return DUMMY_CATALOG.get(asin)
```

**運用ルール**:
- B-11 CreatorsApiClient は `os.environ.get("USE_DUMMY_CATALOG") == "true"` でダミーモードに切替（CDK の `dev` 環境では常時 true、`prd` でも 6/15 までは true）
- ダミーモード時に存在しない asin が来た場合、`get_dummy_item_by_asin` は None を返し、B-04 が 404 product-not-found を返却
- 予選デモのシナリオは上記 4 商品（mockup と同じ）を Share する想定で固定
- imageUrl の S3 バケット `yudane-dummy-catalog` は Member A が事前に作成（mockup/assets/products/*.svg を配置）

**6/15 以降のスイッチオフ**:
- Approved 承認後、`USE_DUMMY_CATALOG=false` に切替、Creators API 本接続を有効化
- ダミーカタログは backlog エントリ B-503 として削除候補登録（決勝後）

---

## 4. API 契約（`shared/schema/openapi.yaml` 追加分）

```yaml
# shared/schema/paths/cart.yaml（Unit-1 OpenAPI 第 1 版に追加）
paths:
  /v1/cart-watch-items:
    get:
      summary: カート監視リスト一覧取得（M-05 一覧モード / Home hero）
      operationId: listCartWatchItems
      tags: [cart]
      security:
        - cognitoAuth: []
      parameters:
        - in: query
          name: status
          required: false
          schema:
            type: string
            enum: [watching, notified-30m, notified-6h, notified-24h, purchased, dismissed, watching_orphaned, active]
            default: active   # active = watching + notified-* + watching_orphaned の合成（M-05 一覧で表示するアクティブ群、NFR Design Q4 = A' 反映）
        - in: query
          name: limit
          required: false
          schema: { type: integer, minimum: 1, maximum: 100, default: 50 }
        - in: query
          name: cursor
          required: false
          schema: { type: string }   # base64 エンコードされた DDB LastEvaluatedKey
      responses:
        '200':
          content:
            application/json:
              schema:
                type: object
                required: [items]
                properties:
                  items:
                    type: array
                    items: { $ref: '#/components/schemas/CartWatchItemDto' }
                  nextCursor:
                    type: string
                    nullable: true

    post:
      summary: カート監視リスト登録（US-03-01）
      operationId: createCartWatchItem
      tags: [cart]
      security:
        - cognitoAuth: []
      parameters:
        - in: header
          name: Idempotency-Key
          required: true
          schema:
            type: string
            format: uuid
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required: [url, asin]
              properties:
                url: { type: string, format: uri }
                asin: { type: string, pattern: '^[A-Z0-9]{10}$' }
      responses:
        '201':
          description: 新規登録
          content:
            application/json:
              schema: { $ref: '#/components/schemas/CartIntakeResponse' }
        '200':
          description: 既存登録（重複）
        '400': { $ref: '#/components/responses/ProblemDetails' }
        '409': { $ref: '#/components/responses/ProblemDetails' }  # Safeguard block

  /v1/cart-watch-items/{asin}:
    get:
      summary: カート監視アイテム詳細（US-03-02 通知タップ後）
      operationId: getCartWatchItem
      tags: [cart]
      security:
        - cognitoAuth: []
      parameters:
        - in: path
          name: asin
          required: true
          schema: { type: string, pattern: '^[A-Z0-9]{10}$' }
      responses:
        '200':
          content:
            application/json:
              schema: { $ref: '#/components/schemas/CartWatchItemDto' }
        '404': { $ref: '#/components/responses/ProblemDetails' }
    delete:
      summary: 「いらない」で監視解除（US-03-02 AC-4）
      operationId: dismissCartWatchItem
      tags: [cart]
      security:
        - cognitoAuth: []
      parameters:
        - in: path
          name: asin
          required: true
          schema: { type: string, pattern: '^[A-Z0-9]{10}$' }
      responses:
        '204': { description: 解除成功 }
        '400': { $ref: '#/components/responses/ProblemDetails' }
        '404': { $ref: '#/components/responses/ProblemDetails' }

  /v1/push-tokens:
    post:
      summary: Push 通知トークン登録（Q5 = C 反映、End User Messaging Endpoint 作成）
      operationId: registerPushToken
      tags: [cart]
      security:
        - cognitoAuth: []
      parameters:
        - in: header
          name: Idempotency-Key
          required: true
          schema:
            type: string
            format: uuid    # M-09 で uuidv5(token, namespace) で生成、Unit-1 規約整合
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required: [token, platform]
              properties:
                token: { type: string, minLength: 32 }
                platform:
                  type: string
                  enum: [APNS, GCM]
      responses:
        '201':
          content:
            application/json:
              schema:
                type: object
                properties:
                  endpointId: { type: string }
        '400': { $ref: '#/components/responses/ProblemDetails' }

components:
  schemas:
    CartWatchItemDto:
      type: object
      required: [itemId, asin, productMeta, status, createdAt]
      properties:
        itemId: { type: string }
        asin: { type: string }
        productMeta: { $ref: '#/components/schemas/ProductMetaDto' }
        status:
          type: string
          enum: [watching, notified-30m, notified-6h, notified-24h, purchased, dismissed, watching_orphaned]
        attackSchedule:
          type: object
          properties:
            schedule_30m: { type: string }
            schedule_6h: { type: string }
            schedule_24h: { type: string }
        createdAt: { type: string, format: date-time }

    CartIntakeResponse:
      type: object
      properties:
        item: { $ref: '#/components/schemas/CartWatchItemDto' }
        isNewlyCreated: { type: boolean }
```

---

## 5. Telemetry イベント定義（S-04 TelemetryContracts への追加）

> **4 巡目セルフレビュー後追加（Issue Q 対応）**: 本 Unit が発火する Telemetry イベントを Unit-1 [S-04 TelemetryContracts](../../unit-1-platform/functional-design/functional-design.md#64-s-04-telemetrycontracts) のスキーマに正式登録する。Unit-1 [api-contracts.md §12 クライアントテレメトリスキーマ](../../../../.kiro/steering/api-contracts.md) の命名規約 `<unit>.<verb>` に準拠。

### 5.1 Mobile 発火イベント（M-05 / M-08 / M-09）

| Event Type | 発火タイミング | properties |
|---|---|---|
| `cart.share_received` | M-08 が onUrlShared を受信 | `{ urlValid: boolean, asin: string \| null, source: 'ios-extension' \| 'android-intent' }` |
| `cart.intake_succeeded` | M-05 useCartIntake mutation 成功 | `{ asin: string, isNewlyCreated: boolean, latencyMs: number }` |
| `cart.intake_failed` | M-05 useCartIntake mutation 失敗 | `{ asin: string, errorType: 'asin-mismatch' \| 'product-not-found' \| 'network' \| 'safeguard', httpStatus: number }` |
| `cart.dismiss_tapped` | M-05 「いらない」タップ | `{ asin: string, previousStatus: string, secondsSinceCreated: number }` |
| `cart.debate_tapped` | M-05 「論破する」タップ | `{ asin: string, currentStep: '30m' \| '6h' \| '24h' \| null }` |
| `cart.amazon_tapped` | M-05 「Amazon で買う」タップ | `{ asin: string, fromContext: 'cart-attack' \| 'list-view' }` |
| `push.permission_requested` | M-09 requestPermissionsAsync 開始 | `{}` |
| `push.permission_denied` | M-09 permission denied | `{ reasonInferred: string \| null }` |
| `push.token_registered` | M-09 endpointId 取得成功 | `{ platform: 'APNS' \| 'GCM', isRotation: boolean }` |
| `push.notification_received` | M-09 通知受信（フォアグラウンド/バックグラウンド） | `{ type: string, productId: string \| null, step: string \| null, foreground: boolean }` |
| `push.notification_tapped` | M-09 onNotificationTap 起動 | `{ type: string, productId: string \| null, step: string \| null, validPayload: boolean }` |

### 5.2 Backend EMF メトリクス（B-04 / B-05 / B-06）

| Metric Name | Unit | Dimensions | 用途 |
|---|---|---|---|
| `cart.intake.created` | Count | `userId` | 新規登録数（北極星指標 1: カート介入成約率の分母） |
| `cart.intake.duplicate` | Count | `userId` | 既存登録の重複検知数 |
| `cart.intake.asin_mismatch` | Count | — | 不正クライアント検知（SECURITY-05 違反） |
| `cart.dismissed` | Count | `previousStatus` | 「いらない」タップ数（離脱率分析） |
| `cart.scheduler.create_failed` | Count | `step` | EventBridge Scheduler 作成失敗（部分失敗の検知） |
| `notification.dispatched` | Count | `step`, `status` | 通知配信数（北極星指標: 配信成功率） |
| `notification.suppressed_by_safeguard` | Count | `step` | Safeguard により抑制された通知数（Property 5 動作確認） |
| `notification.delivery_latency` | Milliseconds | `step` | 配信レイテンシ（B-06 invoke から SendMessages 完了まで） |

### 5.3 PII マスキング方針（SECURITY-01 / NG-7）

- `userId` は SHA-256 ハッシュ済みの匿名化値を使用（Unit-1 §1.3 Telemetry IO 仕様と整合）
- `asin` は公開 Amazon 商品 ID のため平文 OK
- `errorType` 等の文字列定数は ENUM のみ、自由記述不可
- `urlValid: boolean` のみ送信、URL 全文は送らない

### 5.4 CI 静的検証（PII 流入防止）

`shared/telemetry-contracts/` への本 Unit 追加分について、Unit-1 [Property 4: PII の Telemetry 流入禁止](../../unit-1-platform/functional-design/functional-design.md#property-4-pii-の-telemetry-流入禁止) で定義された `check-pii-fields.sh` の対象に含める。CI で email / phone / address / 商品 URL 全文の流入を自動検知。

---

## 6. SECURITY 適用マトリクス（SECURITY-01〜15 の網羅性確認）

> **4 巡目セルフレビュー後追加（Issue S 対応）**: 要件書 §6.4 SECURITY-01〜15 を本 Unit がどう満たすか、項目別に明示。

| ID | 項目 | 本 Unit の対応 |
|---|---|---|
| SECURITY-01 | PII 暗号化 | DDB CartWatchItems / NotificationLogs を KMS CMEK 暗号化（[§3.1](#31-stack-構成)）、productMeta は公開情報のためハッシュ化対象外 |
| SECURITY-02 | TLS 1.2+ | API Gateway Edge / End User Messaging Push がデフォルトで TLS 1.2+ 強制 |
| SECURITY-03 | ログ構造化 | B-12 AuditLogger 経由で全ログを JSON 構造化、相関 ID 伝搬（Unit-1 §2.1） |
| SECURITY-04 | HTTP ヘッダ | API Gateway Cognito Authorizer + CORS 設定（Mobile 専用のため CSP / HSTS は将来 Web 版で適用） |
| SECURITY-05 | 入力検証 | Pydantic で `asin: ^[A-Z0-9]{10}$` 検証、Backend 側で S-01 再検証（[§2.1](#21-b-04-cartintakehandlerq2--a-反映)） |
| SECURITY-06 | IAM 最小権限 | 各 Lambda に個別ロール、`scheduler:*` は `arn:.../schedule/default/cart-*` に限定（[§3.1](#31-stack-構成)）、3 巡目 Issue L で Confused Deputy 対策済み |
| SECURITY-07 | ネットワーク | 本 Unit Lambda は VPC 外（Unit-1 §3.1 確定、コールドスタート最小化）、外部 API は HTTPS のみ |
| SECURITY-08 | 認可 | API Gateway Cognito JWT 検証 + Lambda 内で `event["requestContext"]["authorizer"]["claims"]["sub"]` から userId 取得、IDOR 対策で全 DDB 操作に PK = `USER#{sub}` 強制 |
| SECURITY-09 | ハードニング | `removalPolicy = RETAIN` (prd) + `deletionProtection: true` (prd)、エラー詳細は ProblemDetails で本番では type/title のみ |
| SECURITY-10 | SBOM | Unit-1 で全 Stack 共通、本 Unit の `boto3` / `expo-notifications` 等の依存を `package-lock.json` / `poetry.lock` で固定 |
| SECURITY-11 | Mobile/Backend 整合 | S-01 AsinExtractor / S-03 SafeguardPolicy（本 Unit で `evaluate_notification` 追加）が両言語で同一ロジック |
| SECURITY-12 | 認証 / トークン | Cognito JWT を全 API で要求、APNs/FCM トークンは End User Messaging Push 内で管理（Q5 = C） |
| SECURITY-13 | SRI / 署名 | EventBridge Scheduler の Input は IAM 経由で Lambda 内のみアクセス、改竄不可 |
| SECURITY-14 | アカウント乗っ取り耐性 | Unit-2 Auth で Cognito Lockout / MFA 強制、本 Unit は consumer |
| **SECURITY-15** | **DoS / レート制限**（4 巡目で強化） | **下記 §6.1 で詳細** |

### 6.1 SECURITY-15（DoS/レート制限）対策（4 巡目強化）

#### Cart 監視リスト件数の上限

- 1 ユーザー × **active 状態**（`status ∈ {watching, notified-30m, notified-6h, notified-24h, watching_orphaned}`）のアイテムは最大 **100 件**（Property 6 として定義）
- B-04 CartIntakeHandler は intake 前に `count_active(user_id)`（[data-model.md §1.3 便宜関数](./data-model.md#13-ステータスマシンq8--a)）で active 群件数を取得、超過時は **429 too-many-cart-watch-items** 返却
- 100 件は EventBridge Scheduler 1 アカウント上限（100 万）の `1/10000` で十分余裕

```python
# backend/src/cart/handlers/cart_intake.py に追加
MAX_ACTIVE_WATCH_ITEMS = 100

def lambda_handler(event, context):
    # ... 既存の検証 ...

    # 4 巡目: SECURITY-15 件数上限チェック
    active_count = repo.count_active(user_id)  # status in (watching, notified-*) を集計
    if active_count >= MAX_ACTIVE_WATCH_ITEMS:
        return Response(429, ProblemDetails(
            type="https://api.yudane.app/errors/too-many-cart-watch-items",
            title="監視リスト上限到達",
            status=429,
            detail=f"アクティブな監視アイテムが {MAX_ACTIVE_WATCH_ITEMS} 件に達しました。「いらない」で整理してください。",
        ))
    # ...
```

#### API Gateway レート制限

- `POST /v1/cart-watch-items`: **10 req/sec / userId**（API Gateway Usage Plan + API Key per user は使わず、WAF Rate-based Rule で IP × Cognito sub 単位）
- `GET /v1/cart-watch-items`: 60 req/sec / userId
- `POST /v1/push-tokens`: 1 req/min / userId（トークン更新は頻度低）

→ 詳細な WAF ルール定義は Unit-1 NFR Design ステージで集約定義（本 Unit は要件のみ提示）。

### Property 6: 監視リスト件数の上限による DoS 防御（4 巡目追加）

**Validates: Requirements 6.4** SECURITY-15（DoS / レート制限）

1 ユーザーの active 監視アイテム（`status in (watching, notified-30m, notified-6h, notified-24h, watching_orphaned)`）は最大 100 件。超過時は B-04 が 429 を返却し、EventBridge Scheduler の不必要な作成を防ぐ。

---

## 7. 並行開発の Mock 提供方針（Stage 1〜2）

> **4 巡目セルフレビュー後追加（Issue T 対応）**: Unit-5 が依存する Unit-3 / Unit-4 / Unit-7 が並行開発中の期間（Stage 1: 2026-05-28〜29 / Stage 2: 5/29 以降）の Mock 戦略。

### 7.1 Member D（Unit-5 owner）が用意すべき Mock

| 依存先 | Mock 内容 | 配置 |
|---|---|---|
| Unit-1 IdempotencyKeys middleware | DynamoDB Local + `with_idempotency` のローカル動作確認 | `backend/tests/conftest.py` の fixture |
| Unit-1 S-03 SafeguardPolicy | `evaluate_notification` の本実装をそのまま import（本 Unit が owner として追加） | 不要（実装済み） |
| Unit-1 S-01 AsinExtractor | 本実装をそのまま import | 不要 |
| Unit-1 IdempotencyKeys テーブル | LocalStack DynamoDB Local | `docker-compose.local.yml` |
| Unit-2 Users テーブル / `pushEndpointId` | Mock User fixture（[unit-2/functional-design.md] 完成前） | `backend/tests/fixtures/users.py` |
| Unit-3 `POST /v1/debate-sessions` | Prism Mock（`shared/schema/openapi.yaml` 第 1 版 5/29 凍結後） | `npm run mock:api` |
| Unit-4 B-11 CreatorsApiClient | ダミーカタログ（§8 A-10 Approved 申請前なので予選まで継続） | `backend/src/cart/_dummy_catalog.py` |
| Unit-4 B-13 AmazonTransitionRecorder | API Mock（`POST /v1/amazon-transitions` を Prism で返却） | 同上 |
| Unit-7 SafeguardStates テーブル | Mock fixture（`spent`, `limit`, `cooldownOn` 等を定数返却） | `backend/tests/fixtures/safeguard.py` |
| Unit-7 Lambda Authorizer | API Gateway 開発時はスキップ（`NONE` authorizer）、IT-09 / IT-10 で実装済 Lambda Authorizer に切替 | CDK の `dev` 環境設定で分岐 |
| **B-05 cart_attack_scheduler_retry**（NFR Design 2 巡目追加、Issue KKKK） | **moto** で `EventBridge Scheduler.create_schedule` の連続失敗を simulate（3 回連続 `RaisesException` で `watching_orphaned` 遷移を検証）+ DynamoDB Local の GSI1 で `attackSchedule` 不完全アイテム抽出 + CloudWatch Alarm 5（`cart.scheduler.retry_failed` カウント）の疎通テスト。実装ファイルは `backend/src/cart/handlers/cart_attack_scheduler_retry.py`、テストは `backend/tests/cart/test_cart_attack_scheduler_retry.py`（Member D が他 Unit に依頼するものではなく、Member D 自身が retry batch のロジックテスト用に整備する Mock）| `backend/tests/cart/conftest.py` の moto + DynamoDB Local fixture |

### 7.2 Member D が他 Unit owner に提供する Mock / API スタブ

本 Unit が他 Unit の依存となるケース（Unit-8 Dame Report が `NotificationLogs` を読む等）に備え、**Stage 2 までに以下を提供**:

- OpenAPI `paths/cart.yaml` 第 1 版（本ドキュメント §4 で記述、Member A の一括ドラフト C-3 で Stage 2 までに統合）
- `CartWatchItemDto` / `NotificationLogDto` の TypeScript / Python 型生成（`shared/schema/types/`）
- DynamoDB Local の seed データ（5 アイテム × 3 status のサンプル）

### 7.3 移行スケジュール

| Stage | 期日 | 状態 / Member D マイルストーン |
|---|---|---|
| **Stage 1** | 2026-05-28（本日） | 設計書 push 完了、Member D が Native Module / B-04 / B-05 / B-06 を Mock 駆動で着手可能。**Day 1（5/28）作業範囲**: Expo Config Plugin 雛形 + iOS Share Extension Swift 雛形 + S-01 AsinExtractor 動作確認 |
| **Stage 2** | 2026-05-29 終業 | OpenAPI 第 1 版凍結 + `shared/schema/types/` 型生成完了 + Prism Mock サーバー稼働。**Day 2（5/29）作業範囲**: B-04 CartIntakeHandler 雛形 + テンプレート 30 件記述 + Snapshot TDD で CartStack スケルトン |
| **Stage 3** | 2026-05-29 夕方〜5/30 朝 | dev 環境 CartStack デプロイ、E2E-03b（dismiss 経路）から動作確認開始。**Day 3（5/30）作業範囲**: 個人 sandbox `yudane-cart-dev-d-*` への CDK deploy（Member D の initial = `d`）+ E2E-03b smoke test |
| **Stage 4** | 2026-05-30〜6/2 | Unit-2 Auth & Profile 完成、E2E-03（フル経路）動作確認。**Day 4-5（5/31〜6/2）作業範囲**: B-06 NotificationDispatcher 配信統合 + APNs/FCM 実機テスト + 予選デモシナリオ rehearsal |
| **予選当日** | 2026-05-30（土）| MVP デモ提出。E2E-03（Share → 30m 通知 → 論破 → Amazon）が動作する状態 |
| **Approved 申請** | 〜2026-06-15 | Amazon Approved Mobile Application 承認待ち（[backlog B-503](../../../../doc/backlog.md)）|
| **決勝** | 2026-06-26（金）| AWS 上にデプロイ済みデモ。LLM 通知コピー（[backlog B-501](../../../../doc/backlog.md)）+ クリップボード検知（[backlog B-502](../../../../doc/backlog.md)）の追加実装も視野 |

---

## 8. Unit 間契約レビュープロセス（Member 間合意）

> **4 巡目セルフレビュー後追加（Issue V 対応）**: data-model.md §3 で「想定」段階の Unit 間契約を、Member 間の正式合意プロセスに乗せる。
>
> **develop プル後の見直し（2026-05-29、Issue A1 対応）**: main 由来の Unit-1 完成版（`infra/lib/platform-stack.ts` / `backend/src/common/`）と Unit-5 設計の乖離を検出し、**PlatformStack 追実装 7 項目 を新規依頼として §8.1 に格上げ**。Unit-1 は既存実装あれど Unit-5 が前提とする `IdempotencyKeysTable` / `IdempotencyBucket` / `kmsKey` public 化等が**未着手**のため、Member A への正式合意プロセスとして扱う。

### 8.1 本 Unit が他 Unit owner にレビュー依頼する事項

| 依頼先 Member | 依頼対象 | レビュー期限 | 合意エビデンス |
|---|---|---|---|
| **Member A**（Unit-1 PlatformStack 追実装、2026-05-29 追加）| **PlatformStack 7 項目の追実装**: ① `kmsKey: kms.IKey` を `public readonly` 化（現状 `const key` ローカル変数のため Cross-Stack 参照不可）/ ② `IdempotencyKeysTable: dynamodb.ITable` 新規（Unit-1 data-model.md §3.2 で予告済、未実装）/ ③ `IdempotencyBucket: s3.IBucket` 新規（同上、Idempotency response 大容量 S3 退避用）/ ④ `DebateRateLimitsTable: dynamodb.ITable` 新規（Unit-3 owner 用だが Unit-1 で作成、Unit-1 data-model.md §3.1 で予告済、未実装）/ ⑤ `alertsTopic` を `alertTopic` に rename + `public readonly` 化（[infrastructure-design.md §5.3 将来統合手順](../infrastructure-design/infrastructure-design.md#5-sns-topic--slack-webhookq6a-反映) で本 Unit が `subscription` 追加するため）/ ⑥ `PlatformStackProps` に `developerInitial?: string` 追加（個人 sandbox 命名分離用、tech-cdk.md §4.1 整合）/ ⑦ `backend/src/common/idempotency/with_idempotency.py` 新規実装（Unit-1 data-model.md §3.2 atomic lock パターンの実コード化）| **2026-05-29 18:00 JST**（Stage 2 デッドライン）| GitHub PR `#platform-additions-001` のマージ |
| **Member A**（Unit-1 既存合意） | OpenAPI 第 1 版への `paths/cart.yaml` 追加 + IdempotencyKeys 利用 + S-04 TelemetryContracts への本 Unit イベント追加 + **M-01 AppShell.onDeepLink の M-09 への delegate 仕様**（7 巡目: Issue JJ）+ **CartWatchItems の Unit-1 §4.3 を Unit-5 §1.2 に同期**（Issue B5: ttl 30 日/7 日、`watching_orphaned` enum 追加）+ **Unit-1 §4.1 Authorizer 配置マトリクスに Cart 関連 3 行追加**（Issue C2: cart-watch-items POST/DELETE / push-tokens POST / amazon-transitions の Lambda Authorizer / Cognito Authorizer 振り分け）| 2026-05-29 18:00 JST | GitHub PR `#cart-001` のマージ |
| **Member A**（Unit-2） | Users テーブルへの `pushEndpointId` / `pushPlatform` / `pushTokenUpdatedAt` 追加 | 2026-05-29 18:00 JST | GitHub PR #auth-002 のマージ（[data-model.md §3.1](./data-model.md#31-users-テーブルunit-2-owner-への追加属性)） |
| **Member B**（Unit-3） | `POST /v1/debate-sessions` の request body に `productId: string` / `trigger: "cart-attack"` 受入 | 2026-05-29 18:00 JST | Unit-3 functional-design への記述 |
| **Member C**（Unit-7） | SafeguardStates テーブル属性 6 件（cooldown_on / cooldown_until / quiet_week / monthly_limit_yen / current_budget_used_yen / has_debt）の正式定義 + S-03 `evaluate_notification` 関数（`decide_allow` ラッパー方式、2026-05-29 修正版）の Unit-7 owner レビュー | 2026-05-30 18:00 JST | GitHub PR `#safeguard-001` のマージ |
| **Member C**（Unit-7） | Lambda Authorizer から `POST /v1/amazon-transitions` の Safeguard 判定実装 | 2026-05-30 18:00 JST | Unit-7 functional-design への記述 |
| **Member C**（Unit-4） | `POST /v1/amazon-transitions` の request body に `cartWatchItemId` 含む受入 + B-13 が CartWatchItem を `purchased` に遷移する責務 | 2026-05-29 18:00 JST | Unit-4 functional-design への記述 |

### 8.2 ブロッカー判定

合意期限内に PR がマージされない場合は [AGENTS.md §11.5 ブロッカー対応](../../../../.kiro/steering/AGENTS.md) に従い、Slack `#yudane-emergency` で即時エスカレーション。週次同期（金曜 17:00）で代替案を協議。

特に **PlatformStack 追実装 7 項目（§8.1 1 行目）** は Unit-5 の Code Generation ステージのクリティカルパスとなる。期限超過時の代替案:

- **代替案 A**: Member D が Unit-5 owner として Unit-1 PlatformStack に直接 PR を出す（コア 3 Unit ルール違反だが、実装ブロックよりは低リスク）
- **代替案 B**: Unit-5 内で `kmsKey` / `idempotencyKeysTable` 等を一時的に CartStack に直接作成し、Unit-1 PlatformStack 整備後に SSM Parameter 経由で参照に切替（後付け移行）
- **代替案 C**: dev 環境のみ KMS / Idempotency を Unit-5 内で完結させ、prd 環境では Unit-1 整備を待つ（環境別差異が増えるため最終手段）

---

## 9. ハッカソン書類審査・予選評価軸へのインパクト

| 評価軸 | 本ドキュメントの貢献 |
|---|---|
| ビジネス意図の明確さ | **強化**: UC-03（迷いの外部化 + 3 段追撃）の M-2（購買快楽のストレス解消剤化）連動が技術仕様レベルで具体化、通知トーン使い分け（30m / 6h / 24h × 10 パターン）でストーリー的根拠が見える化 |
| Unit 分解の適切さ | **強化**: Unit-5 が Unit-1（基盤）/ Unit-3（論破遷移）/ Unit-7（Safeguard 連携）との依存を API 契約レベルで明示、横断テスト IT-08〜10 / E2E-03 を定義 |
| 創造性とテーマ適合性 | **強化**: Share Extension → 30m → 6h → 24h の追撃タイムライン UI が「迷いを外部化させる装置」として可視化、Property 4 で NG-6 遵守を CI 強制 |
| ドキュメント品質 | **強化**: Q1〜Q8 確定が IO / 状態 / エラー / Native コード / IAM / OpenAPI まで一貫展開、TDD 適用方針も明文化 |
| AI-DLC プロセス（予選評価軸） | **強化**: Per-Unit Loop の Functional Design を Unit-1 と同一テンプレートで実施、後続 Unit（Unit-3/4 等）の参考形 |
