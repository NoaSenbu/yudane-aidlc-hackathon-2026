# Unit-1 Platform — Business Rules

> Unit-1 Platform の**ルール・定数・制約**を一覧化。実装・テストの判定基準となる。
> 参照: [domain-entities.md](./domain-entities.md) / [business-logic-model.md](./business-logic-model.md) / [API 契約ガバナンス](../../../../.kiro/steering/api-contracts.md)
> 確定方針: Q1=refinedA / Q2=A / Q3=A / Q4=refinedA / Q5=A / Q6=A / Q7=A

---

## 1. ASIN ルール（S-01、ALG-ASIN）

| ID | ルール |
|---|---|
| ASIN-01 | ASIN は 10 桁の英数字（正規化後は大文字 `[A-Z0-9]{10}`） |
| ASIN-02 | 抽出後は必ず大文字化して正規化する（正規化は冪等: `normalize(normalize(x)) == normalize(x)`） |
| ASIN-03 | 許可ホスト: `amazon.co.jp` / `amazon.com` / その他 `amazon.<tld>` / 短縮 `amzn.to` / `amzn.asia`。許可外は `unsupported-host` |
| ASIN-04 | パス優先順位: `/dp/` > `/gp/product/` > `/gp/aw/d/` > クエリ `?asin=`。最初にマッチしたものを採用 |
| ASIN-05 | 短縮 URL の実展開は呼び出し側（B-04）が担当。S-01 は短縮ホストを検知して `short-url` フラグを返すのみ |
| ASIN-06 | 抽出失敗は例外でなく `AsinResult{ok:false, reason}` で返す（reason: `no-match` / `invalid-checksum-format` / `unsupported-host`） |
| ASIN-07 | TypeScript 実装と Python 実装は同一入力に対して同一出力を返す（クロス言語一致、CI で golden test 照合） |

---

## 2. セーフガード判定ルール（S-03、ALG-SG、Q2=A）

### 2.1 定数（component-methods.md 準拠、変更は破壊的影響あり）

| 定数 | 値 | 意味 |
|---|---|---|
| `DEFAULT_MONTHLY_LIMIT_RATIO` | 0.7 | 予算感に対する標準月間上限比率 |
| `DEBT_MONTHLY_LIMIT_RATIO` | 0.35 | 負債保有者の月間上限比率 |
| `DEBATE_COOLDOWN_SECONDS` | 86_400 | 3 連続拒否後のクールダウン（24h） |
| `CART_ATTACK_STEPS_SECONDS` | [1_800, 21_600, 86_400] | カート追撃 30m / 6h / 24h |
| `WARN_THRESHOLD_RATIO` | 0.8 | 実効上限の 80% で warn |

### 2.2 判定ルール

| ID | ルール |
|---|---|
| SG-01 | 評価順序は固定: ① cooldownOn → ② quietWeek → ③ 実効上限決定（debt 切替）→ ④ 上限超過 block → ⑤ 80% 超 warn → ⑥ allow |
| SG-02 | `cooldownOn` が true なら他条件に関わらず block（reason `safeguard.cooldown`） |
| SG-03 | `quietWeek` が true なら block（reason `safeguard.quiet-week`） |
| SG-04 | `hasDebt` が true のとき実効上限を `monthlyLimitYen * (0.35/0.7)` に再スケール（= 半減） |
| SG-05 | `currentBudgetUsedYen >= effectiveLimitYen` で block（debt 時 `safeguard.debt-restricted`、通常 `safeguard.monthly-limit-exceeded`） |
| SG-06 | `currentBudgetUsedYen >= effectiveLimitYen * 0.8` かつ未超過で warn（reason `safeguard.near-limit`、遷移は止めない） |
| SG-07 | warn はユーザーの行動を阻止せず通知のみ（NG-6 罪悪感強要を避ける） |
| SG-08 | `remainingYen = max(0, effectiveLimitYen - currentBudgetUsedYen)`（負にならない） |
| SG-09 | 判定は純関数（同一入力 → 同一出力、副作用なし） |
| SG-10 | Mobile（M-07 等）と Backend（B-09）で同一の `decideAllow` を使用し判定が一致する |

---

## 3. DomainError / エラーコード体系（Q7=A、2 階層）

| ID | ルール |
|---|---|
| ERR-01 | エラーは `category`（第1階層）+ `code`（第2階層、`<category>.<slug>` 形式）で表す |
| ERR-02 | `category` は固定 8 種: validation / auth / not-found / conflict / safeguard / external-api / rate-limit / internal |
| ERR-03 | API 境界では `DomainError` を `ProblemDetails`（RFC 7807）に変換する |
| ERR-04 | `ProblemDetails.type` = `https://api.yudane.app/errors/{code}`（code を URL 化、逆引き可能） |
| ERR-05 | `internal`（500）は `detail` に内部情報・スタックトレースを含めない。固定の汎用文言のみ（SECURITY-09） |
| ERR-06 | `DomainError.cause` / `details` の内部要素は API レスポンスに出さず、ログ（B-12）にのみ残す |
| ERR-07 | `retryable` は 429 / 503 かつ冪等メソッドのときのみ true |
| ERR-08 | 全 `code` は対応する HTTP ステータスを持つ（business-logic ALG-MAP の対応表に従う） |

### コード ↔ HTTP ステータス対応

| code | HTTP |
|---|---|
| `validation.*` | 400 / 422 |
| `auth.unauthenticated` | 401 |
| `auth.forbidden` / `auth.idor` | 403 |
| `auth.token-expired` | 401 |
| `not-found.*` | 404 |
| `conflict.*` | 409 |
| `safeguard.cooldown` / `safeguard.quiet-week` / `safeguard.*-limit-exceeded` / `safeguard.debt-restricted` | 409 |
| `safeguard.near-limit` | （warn は 200 + ヘッダ通知、ブロックしない） |
| `external-api.*` | 502 / 503 |
| `rate-limit.exceeded` | 429 |
| `internal.unexpected` | 500 |

---

## 4. 相関 ID / リクエスト規則（M-12、Q5=A）

| ID | ルール |
|---|---|
| REQ-01 | 全リクエストに `X-Correlation-Id`（UUID v4）を付与。クライアント起点で生成 |
| REQ-02 | リトライ・リフレッシュ再送時も `correlationId` は不変（同一 ID を再利用） |
| REQ-03 | Backend は `X-Correlation-Id` を受け取りレスポンス・ログ・X-Ray に伝搬 |
| REQ-04 | `userId` はクライアントヘッダを信用せず、JWT claim の `sub` を正とする（SECURITY-08） |
| REQ-05 | パスパラメータの `{userId}` と JWT `sub` の不一致は `auth.idor`（403）（api-contracts.md §5） |

### リトライ規則（RETRY）

| ID | ルール |
|---|---|
| RETRY-01 | 自動リトライ対象は **GET のみ**（POST/PATCH/DELETE はリトライしない） |
| RETRY-02 | リトライ対象条件: HTTP 429 / 503 / ネットワークタイムアウト |
| RETRY-03 | バックオフ: `300ms * 2^attempt + jitter`、最大 2 回（計 3 試行） |
| RETRY-04 | 401 はリトライではなくリフレッシュ（ALG-REFRESH）で対応。リフレッシュ後の再送は 1 回のみ |
| RETRY-05 | リフレッシュ後も 401 なら再リフレッシュせず `auth.token-expired` で確定（無限ループ防止） |
| RETRY-06 | SSE ストリーミングは接続断時にリトライしない（重複配信防止） |

---

## 5. テレメトリ規則（M-13 / B-14 / S-04、Q6=A）

| ID | ルール |
|---|---|
| TEL-01 | `track` する `name` は S-04 イベントカタログに存在するもののみ。未登録は no-op |
| TEL-02 | `props` は S-04 許可キーのみ送信。未許可キーは送信前にドロップ（PII 混入防止、Q4 連動） |
| TEL-03 | `props` の値は string / number / boolean のみ（ネスト・オブジェクト禁止） |
| TEL-04 | flush トリガー: 件数 >= 20（`BATCH_MAX_EVENTS`） or 30s 経過（`FLUSH_INTERVAL_SECONDS`） or アプリ background 化 |
| TEL-05 | 送信失敗時は AsyncStorage 退避キューに保存し次回再送。上限 `OVERFLOW_MAX_EVENTS` 超過で古い順に破棄 |
| TEL-06 | B-14 は JWT sub と user_id の一致を検証してから取込（SECURITY-08） |
| TEL-07 | CloudWatch メトリクス次元（dimensions）に高カーディナリティ値（userId / correlationId / asin）を入れない |
| TEL-08 | `occurredAt`（端末時刻）と サーバー受信時刻を両方記録（遅延補正用） |
| TEL-09 | TelemetryEnvelope の serialize → deserialize は round-trip 一致（PBT-02） |

---

## 6. ログ / PII 保護ルール（B-12 / S-04、Q4=refinedA / default-deny）

| ID | ルール |
|---|---|
| PII-01 | **default-deny**: ログ・テレメトリへ出力してよいフィールドは S-04 許可リスト（`allowed`）に明示登録されたもののみ |
| PII-02 | 許可リストにもPII宣言にも無いキーは `unclassified` 扱いで **full-mask**（fail-safe） |
| PII-03 | OpenAPI で `x-pii: true` 宣言、または S-04 PII リストに載るフィールドは出力時に必ずマスク |
| PII-04 | マスク戦略: email → partial-email（`a***@example.com`）、その他 PII → full-mask（`***`）、unclassified → full-mask |
| PII-05 | マスキングは出力直前に 1 回だけ適用（二重マスク・マスク漏れ防止） |
| PII-06 | `message` 本文にも二次防御: メール / 電話番号 / カード番号らしき部分列を正規表現でマスク |
| PII-07 | CI（`check-pii-fields.sh` 拡張）でログ・テレメトリ経路の構造体に未分類フィールドを検出したら fail（分類を強制） |
| PII-08 | `password` / `token` / `secret` / `apiKey` / `creditCard*` 等の鍵名はレスポンス・ログともに出力禁止（api-contracts.md §9.2） |
| PII-09 | カレンダーは `category` / `timeRange` のみ許可。`title` / `body` / `attendees` は契約・ログ双方で禁止（FR-CAL-05 / NG-7） |

---

## 7. OpenAPI 契約ガバナンス（S-02、Q1=refinedA）

| ID | ルール |
|---|---|
| API-01 | REST 契約の SSOT は `shared/schema/openapi.yaml`（OpenAPI 3.1）。物理分割は api-contracts.md §10 に従う |
| API-02 | 第1版で Member A が凍結する範囲: 全 UC のパス骨格（URL + メソッド）+ 共通コンポーネント（ProblemDetails / 認証 / ページネーション / 共通パラメータ）+ 主要リソースの必須フィールド最小セット |
| API-03 | 実装者は担当パスに**省略可能フィールド**を後から追加してよい（非破壊的変更、v1 内） |
| API-04 | 契約変更は実装 PR と混在禁止。契約 PR を先に merge → 型再生成（同 PR）→ 実装 PR の順序（api-contracts.md §2） |
| API-05 | 破壊的変更（削除 / 必須追加 / 型変更）は禁止。必要なら `/v2` 新設 + 最低 30 日 deprecation |
| API-06 | 全パスは `/v1/...` prefix、リソースは複数形・kebab-case（`/v1/cart-watch-items`） |
| API-07 | エラーレスポンスは RFC 7807 ProblemDetails 形式（api-contracts.md §4.4） |
| API-08 | 型生成ファイル（`shared/schema/types/api.ts` / `backend/src/common/models/api.py`）は手動編集禁止・commit 必須。CI で再生成差分があれば fail |
| API-09 | 全 POST に 429 レスポンスを定義し `X-RateLimit-*` ヘッダを返す（SECURITY-11） |
| API-10 | `CalendarEvent` への `title` / `body` / `attendees` 追加 PR は `check-pii-fields.sh` で自動 reject（PII-09 と連動） |

---

## 8. 設定値カタログ（チューニング可能パラメータ）

| パラメータ | 既定値 | 所属 | 備考 |
|---|---|---|---|
| `BATCH_MAX_EVENTS` | 20 | M-13 | テレメトリ flush 件数閾値 |
| `FLUSH_INTERVAL_SECONDS` | 30 | M-13 | テレメトリ flush 時間閾値 |
| `OVERFLOW_MAX_EVENTS` | 500 | M-13 | 退避キュー上限（超過で古い順破棄） |
| リトライ base | 300ms | M-12 | 指数バックオフの基数 |
| リトライ最大回数 | 2 | M-12 | GET のみ |
| `WARN_THRESHOLD_RATIO` | 0.8 | S-03 | warn 発火閾値 |
| Creators API キャッシュ TTL | 6h | B-11（参照のみ） | Unit-1 は定数の置き場所のみ提供 |

> これらの NFR 的な閾値（タイムアウト・レート制限の具体値・性能目標）は NFR Requirements / NFR Design ステージで Unit-1 向けに最終確定する。本表は機能設計時点の既定値。
