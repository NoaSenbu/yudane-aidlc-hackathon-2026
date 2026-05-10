# Application Design — Component Methods

> 各コンポーネントのメインメソッドのシグネチャと高レベル目的を示す。**ビジネスルールの詳細は Construction フェーズの Functional Design（per-unit）で定義する**。  
> 参照: [Components](./components.md) / [Services](./services.md) / [Dependencies](./component-dependency.md)

## 規約

- 型は TypeScript 表現で示す。Python 実装では `pydantic` モデルに自動変換される
- エラーは `Result<T, DomainError>` 型を返すか、例外を投げる。詳細は Functional Design で確定
- すべての API Lambda は相関 ID（`X-Correlation-Id`）を受け取り、レスポンス・ログに伝搬
- ストリーミング API は SSE（Server-Sent Events）形式で返す
- 型参照: `DTO/*` は [SchemaRegistry (S-02)](./components.md#shared-%E5%B1%A4) で集中管理

---

## Mobile 層

### M-01 `AppShell`

```ts
type Screen = 'home' | 'reel' | 'debate' | 'cart' | 'report' | 'safeguard';

function navigateTo(screen: Screen, params?: Record<string, unknown>): void;
function onDeepLink(url: string): void;             // UC-03 通知タップからの復帰
function onAuthExpired(): void;                     // リフレッシュトークン失効時
```

### M-02 `HomeScreen`

```ts
function useHomeSnapshot(): UseQueryResult<HomeSnapshotDto>;
// HomeSnapshotDto: 候補件数 / カート監視リスト / カレンダー連動 / 死蔵資産 / 委ね Lv
```

### M-03 `ReelScreen`

```ts
function useReelFeed(cursor?: string): UseInfiniteQueryResult<ReelCardDto[]>;
function useAmazonRedirect(): (card: ReelCardDto) => Promise<void>;
function onSwipeLeft(card: ReelCardDto): void;       // UC-01 に遷移
function onSwipeRight(card: ReelCardDto): void;      // カート監視登録
function onDoubleTap(card: ReelCardDto): void;       // Amazon 遷移確認
```

### M-04 `DebateScreen`

```ts
function useDebateSession(targetProductId: string): {
  messages: DebateMessageDto[];
  sendUserMessage: (text: 'resist' | 'agree') => void;
  timerSeconds: number;                                // 90 秒カウントダウン
  state: 'streaming' | 'awaiting-user' | 'completed' | 'cooldown';
};
function onAgree(): void;                              // Amazon 遷移 + EXP 加算
function onResist(): void;                             // 次ターンへ
```

### M-05 `CartInterceptScreen`

```ts
function useCartWatchItem(itemId: string): UseQueryResult<CartWatchItemDto>;
function onDebateNow(item: CartWatchItemDto): void;    // UC-01 に遷移
function onDefer(item: CartWatchItemDto): void;        // 待機継続
```

### M-06 `DameReportScreen`

```ts
function useDameReport(period: 'week' | 'month'): UseQueryResult<DameReportDto>;
// DameReportDto: 委ね Lv / Before-After 4 指標 / ナラティブ / 引用
```

### M-07 `SafeguardScreen`

```ts
function useSafeguardSettings(): {
  data: SafeguardSettingsDto;
  updateMonthlyLimit: (yen: number) => Promise<void>;
  toggleCooldown: (on: boolean) => Promise<void>;
  toggleQuietWeek: (on: boolean) => Promise<void>;
  updateNgCategories: (cats: string[]) => Promise<void>;
  exportData: () => Promise<Blob>;
  deleteAccount: () => Promise<void>;
};
```

### M-08 `ShareExtensionNativeModule`

```ts
// iOS/Android ネイティブからの JS ブリッジ
function onShareReceived(payload: { url: string }): Promise<{ asin: string | null }>;
function registerAsCartWatchItem(asin: string): Promise<void>;
```

### M-09 `PushNotificationHandler`

```ts
function registerForPushNotifications(): Promise<{ token: string; platform: 'ios' | 'android' }>;
function onNotificationTap(payload: { type: 'cart-attack' | 'calendar' | 'admin'; itemId?: string }): void;
```

### M-10 `CalendarNativeModule`

```ts
// 端末ローカル分類 (FR-CAL-05 プライバシー配慮)
function fetchUpcomingEvents(days: number): Promise<EventCategoryDto[]>;
// EventCategoryDto: { startAt: string; category: 'presentation' | 'date' | 'camp' | ... ; confidence: number }
```

### M-11 `AuthModule`

```ts
function signUp(email: string, password: string): Promise<void>;
function confirmSignUp(email: string, code: string): Promise<void>;
function signIn(email: string, password: string): Promise<TokenSet>;
function confirmMfa(session: string, totp: string): Promise<TokenSet>;
function refresh(): Promise<TokenSet>;
function signOut(): Promise<void>;
function getCurrentUser(): Promise<UserDto | null>;
```

### M-12 `ApiClient`

```ts
function apiFetch<T>(
  path: string,
  init?: RequestInit & { stream?: boolean }
): Promise<T | AsyncIterable<T>>;
// 認証ヘッダ、相関 ID、リトライ、エラーマッピングを内包
```

### M-13 `Telemetry`

```ts
function track(eventName: string, props?: Record<string, unknown>): void;
function flush(): Promise<void>;                         // バッチ送信、バックオフ
```

---

## Backend 層

### B-01 `AuthEdgeLambda`

```python
# Cognito User Pool トリガー（Post Confirmation / Pre Token Generation）
def on_post_confirmation(event: CognitoPostConfirmationEvent) -> None: ...
# 新規ユーザーの User / PreferenceVector / SafeguardState を DynamoDB に初期化

def on_pre_token_generation(event: CognitoPreTokenGenerationEvent) -> dict: ...
# 委ね Lv・称号・月間上限を JWT カスタム claim に付与
```

### B-02 `DebateLlmService`

```python
def start_debate(
    user_id: str,
    product_id: str,
    trigger: Literal["reel-refuse", "cart-attack", "long-view"],
) -> DebateSessionDto: ...
# ctx を集約して Bedrock Claude Haiku 4.5 へストリーミング開始
# ctx = preference_vector + calendar_categories + time_of_day + recent_purchases
#     + spending_depletion_rate + stress_level (low/mid/high、FR-DEBATE-09)
# mid 以上では M-2 のストレス × ご褒美軸コピーを併走させる

def continue_debate(
    session_id: str,
    user_action: Literal["resist", "agree"],
) -> AsyncIterable[DebateTokenDto]: ...
# 初回トークン 300ms 以下 (要件 §6.2 / FR-DEBATE-03)
# agree 後は「今日もいい選択だったね」型の肯定フィードバックトーストを発火 (FR-DEBATE-09)

def estimate_stress_level(
    user_id: str,
    context: StressSignalsDto,
) -> Literal["low", "mid", "high"]: ...
# StressSignalsDto = 直近 7 日の会議密度 / 残業時刻分布 / 深夜帯利用回数 / カレンダー連続予定数
# FR-DEBATE-09 / M-2 のドーパミン依存回路形成のため併走させるコンテキスト信号
```

### B-03 `ReelRecommendationService`

```python
def build_reel(
    user_id: str,
    cursor: str | None = None,
    limit: int = 10,
) -> ReelPageDto: ...
# 嗜好 × 時刻 × カレンダー × 疲労度 × 使い切れ弾薬 の 5 軸で合成
```

### B-04 `CartIntakeHandler`

```python
def intake_shared_url(
    user_id: str,
    shared_url: str,
) -> CartWatchItemDto: ...
# URL → ASIN → Creators API → 登録 を 2 秒以内 (FR-CART-01)
```

### B-05 `CartAttackScheduler`

```python
def schedule_attacks(
    user_id: str,
    cart_watch_item_id: str,
) -> list[ScheduledJobDto]: ...
# EventBridge Scheduler に 30m / 6h / 24h の 3 ジョブ登録
def cancel_attacks(cart_watch_item_id: str) -> None: ...
```

### B-06 `NotificationDispatcher`

```python
def send_push(
    user_id: str,
    channel: Literal["cart-attack-30m", "cart-attack-6h", "cart-attack-24h", "calendar", "report"],
    payload: dict,
) -> DeliveryReceiptDto: ...
# AWS End User Messaging Push 経由で APNs/FCM
```

### B-07 `CalendarPredictionService`

```python
def predict_product_categories(
    events: list[EventCategoryDto],
    user_preference: PreferenceVectorDto,
) -> list[ProductCategoryPredictionDto]: ...
```

### B-08 `PreferenceVectorUpdater`

```python
def update_preference(user_id: str) -> PreferenceVectorDto: ...
# 購買履歴 + スキップ + 論破成功率 + カレンダーパターン を日次バッチで集計
```

### B-09 `SafeguardRulesEngine`

```python
def evaluate(user_id: str, action: Literal["amazon-transition", "debate-start"]) -> SafeguardDecisionDto: ...
# 月間上限 / 冷却モード / 負債 を判定。decision: allow | block | warn
```

### B-10 `AssociatesLinkGenerator`

```python
def generate_special_link(
    asin: str,
    user_id: str,           # ユーザー単位のタグ付与（commission 計測用）
) -> SpecialLinkDto: ...
```

### B-11 `CreatorsApiClient`

```python
def get_item_by_asin(asin: str) -> ProductMetaDto | None: ...
# ElastiCache Redis (TTL 6h) → 未キャッシュなら Creators API 呼出
def search_items(
    query: str,
    category: str | None = None,
    max_results: int = 20,
) -> list[ProductMetaDto]: ...
```

### B-13 `AmazonTransitionRecorder`

```python
def record_transition(
    user_id: str,
    context: Literal["reel", "debate-agree", "cart-attack"],
    product_id: str,
    session_id: str | None = None,
) -> ExpAwardDto: ...
# EXP 加算、Safeguard 上限カウント更新
```

### B-12 `AuditLogger`（Lambda 共通ライブラリ）

```python
def log(level: Literal["info", "warn", "error"], message: str, context: dict) -> None: ...
# 構造化 JSON ログ、PII マスキング、相関 ID 伝搬、CloudWatch Logs へ

def metric(name: str, value: float, unit: str, dimensions: dict) -> None: ...
# Embedded Metric Format (EMF) で CloudWatch Metrics へ直接出力

def trace(segment_name: str) -> ContextManager: ...
# X-Ray セグメント作成（with 文で使用）
```

### B-14 `TelemetryIngestionService`

```python
def ingest_events(
    user_id: str,
    events: list[TelemetryEventDto],
) -> IngestResultDto: ...
# バッチで受信したクライアントイベントを EMF 形式で CloudWatch Metrics に投入し、
# 長期保管用に S3 Data Lake（Parquet）へも並列書き込み。北極星指標の集計元

---

## Shared 層

### S-01 `AsinExtractor`

```ts
// TypeScript
export function extractAsin(url: string): string | null;
export function isValidAsin(asin: string): boolean;

// Python 実装も同等シグネチャ
```

### S-03 `SafeguardPolicy`

```ts
export const DEFAULT_MONTHLY_LIMIT_RATIO = 0.7;           // 予算感の 70%
export const DEBT_MONTHLY_LIMIT_RATIO = 0.35;             // 負債保有者
export const DEBATE_COOLDOWN_SECONDS = 86_400;            // 24h
export const CART_ATTACK_STEPS_SECONDS = [1_800, 21_600, 86_400]; // 30m/6h/24h

export function decideAllow(
  transitionCountMonth: number,
  monthlyLimitYen: number,
  currentBudgetUsedYen: number,
  flags: { cooldownOn: boolean; quietWeek: boolean; hasDebt: boolean },
): 'allow' | 'block' | 'warn';
```

---

## 型定義サマリ（主要 DTO）

```ts
type UserDto = { id: string; email: string; createdAt: string; ... };
type CartWatchItemDto = { id: string; asin: string; productMeta: ProductMetaDto; watchedAt: string; attackSteps: AttackStepDto[] };
type ProductMetaDto = { asin: string; title: string; priceYen: number; imageUrl: string; reviewSummary: string };
type ReelCardDto = { product: ProductMetaDto; pitch: string; tags: string[]; originTrigger: string };
type DebateSessionDto = { id: string; userId: string; productId: string; startedAt: string; timerSeconds: number };
type DebateMessageDto = { who: 'user' | 'ai'; text: string; axis?: 'fact' | 'psychology'; at: string };
type PreferenceVectorDto = { vector: number[]; labels: string[]; updatedAt: string };
type SafeguardSettingsDto = { monthlyLimitYen: number; cooldownOn: boolean; quietWeek: boolean; ngCategories: string[] };
type DameReportDto = { level: number; title: string; metrics: Record<string, Delta>; narrative: string[]; quote: string };
type SpecialLinkDto = { url: string; tag: string; expiresAt?: string };
```

これらは [Shared SchemaRegistry (S-02)](./components.md#shared-%E5%B1%A4) の OpenAPI で集中管理し、TypeScript / Python 両方の型を自動生成する。
