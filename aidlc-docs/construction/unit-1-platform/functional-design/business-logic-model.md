# Unit-1 Platform — Business Logic Model

> Unit-1 Platform の横断ロジックを**技術非依存**で記述。アルゴリズム・処理フロー・状態遷移を扱う（インフラ実装は NFR Design / Infrastructure Design で確定）。
> 参照: [domain-entities.md](./domain-entities.md) / [business-rules.md](./business-rules.md) / [component-methods.md](../../../inception/application-design/component-methods.md)
> 確定方針: Q1=refinedA / Q2=A / Q3=A / Q4=refinedA / Q5=A / Q6=A / Q7=A

---

## ALG-ASIN: ASIN 抽出（S-01 AsinExtractor、Q3=A）

### 入力 / 出力
- 入力: `url: string`（Amazon 共有 URL、短縮 URL を含む）
- 出力: `AsinResult`（domain-entities §3.2）

### 処理フロー

```
extractAsin(url):
  1. 入力を trim し、URL としてパース不能なら → { ok:false, reason:'no-match' }
  2. ホスト検証:
       許可ホスト = amazon.co.jp / amazon.com / 各国 amazon.* / amzn.to / amzn.asia
       許可外 → { ok:false, reason:'unsupported-host' }
  3. 短縮 URL（amzn.to / amzn.asia）の場合:
       → 展開は呼び出し側（B-04）が HTTP HEAD で行い、展開後 URL を再投入する前提
       → 本関数は短縮ホストを source='short-url' として後段に渡すためのフラグのみ立てる
  4. パスパターンを優先順位順にマッチ（最初にマッチしたものを採用）:
       a. /dp/{ASIN}            → source='path-dp'
       b. /gp/product/{ASIN}    → source='path-gp-product'
       c. /gp/aw/d/{ASIN}       → source='path-gp-aw'
       d. クエリ ?asin={ASIN}    → source='query-asin'
  5. 候補 ASIN を正規化（大文字化）
  6. isValidAsin(asin) が false → { ok:false, reason:'invalid-checksum-format' }
  7. { ok:true, asin, source, normalizedFrom:url }
```

### `isValidAsin` の判定
- 10 桁の英数字（`[A-Z0-9]{10}`、大文字正規化後）
- 先頭が `B` で始まる標準 ASIN、または 10 桁数字（ISBN-10 互換）を許容
- 詳細規則は business-rules.md ASIN-01〜04

### round-trip 性質（PBT-02、テスト方針）
- 任意の有効 ASIN `a` と任意の許可ホスト `h`、任意の対応パステンプレート `t` について
  `extractAsin(buildUrl(h, t, a)).asin === a` が常に成り立つ
- 大文字小文字・末尾スラッシュ・余分なクエリパラメータの有無で結果が変わらない（正規化の冪等性）

---

## ALG-SG: セーフガード判定（S-03 SafeguardPolicy、Q2=A 段階評価）

### 入力 / 出力
- 入力: `SafeguardInput`（domain-entities §4.2）
- 出力: `SafeguardDecision`（domain-entities §4.3）

### 判定フロー（優先順位順、最初に確定した decision を返す）

```
decideAllow(input):
  flags = input.flags

  # ステップ1: フラグ系の即時 block（最優先）
  if flags.cooldownOn:
      return block(reason='safeguard.cooldown')
  if flags.quietWeek:
      return block(reason='safeguard.quiet-week')

  # ステップ2: 実効上限の決定（負債で比率切替）
  effectiveLimitYen =
      monthlyLimitYen if not flags.hasDebt
      else round(monthlyLimitYen * (DEBT_MONTHLY_LIMIT_RATIO / DEFAULT_MONTHLY_LIMIT_RATIO))
      # 注: monthlyLimitYen は既に予算の 70% 想定。負債者は 35% 相当に再スケール
  remainingYen = max(0, effectiveLimitYen - currentBudgetUsedYen)

  # ステップ3: 上限超過の block
  if currentBudgetUsedYen >= effectiveLimitYen:
      reason = 'safeguard.debt-restricted' if flags.hasDebt else 'safeguard.monthly-limit-exceeded'
      return block(reason, effectiveLimitYen, remainingYen)

  # ステップ4: 80% 超で warn
  if currentBudgetUsedYen >= effectiveLimitYen * WARN_THRESHOLD_RATIO:
      return warn(reason='safeguard.near-limit', effectiveLimitYen, remainingYen)

  # ステップ5: 許可
  return allow(reason='allowed', effectiveLimitYen, remainingYen)
```

### 設計判断（Q2=A の根拠）
- **block 最優先**は FR-FUNNEL-05「セーフガード最優先」に整合
- **warn の存在**: ユーザーに「考える負荷をかけたくない」方針（ユーザー回答 Q2）と矛盾しないよう、warn は遷移を止めず通知のみ。判断を強要しない（NG-6 罪悪感強要の回避）
- **モバイル・バックエンド一致**: S-03 は Mobile（M-07 等）と Backend（B-09）の両方で同一関数を実行し、UX とゲートの判定が一致する（unit-of-work Unit-7 成功条件）

### 不変条件
- `remainingYen >= 0`（負にならない）
- 同一入力に対して決定論的（副作用なし、純関数）
- `effectiveLimitYen <= monthlyLimitYen`（負債者は必ず上限が下がる、上がることはない）

---

## ALG-API: ApiClient のリクエストライフサイクル（M-12、Q5=A）

### 処理フロー

```
apiFetch(path, init):
  1. correlation = ensureCorrelationContext()   # 既存があれば再利用、なければ UUID v4 生成
  2. headers に付与:
       - Authorization: Bearer <accessToken>（AuthModule から取得）
       - X-Correlation-Id: correlation.correlationId
       - Content-Type / Accept
  3. stream=true の場合は SSE モードへ（ALG-STREAM 参照）
  4. リクエスト送信
  5. レスポンス分岐:
       a. 2xx → ボディをパースして返す
       b. 401（auth.token-expired 相当）→ ALG-REFRESH を1回試行 → 成功なら同一 correlationId で再送（1回のみ）
       c. 429 / 503 / ネットワーク断 → メソッドが GET（冪等）なら指数バックオフでリトライ（最大2回）
       d. その他 4xx/5xx → ProblemDetails をパースして DomainError に変換し throw
  6. リトライ上限到達 → DomainError(category='external-api' or 'rate-limit', retryable=false) を throw
```

### リトライ規則（business-rules.md RETRY-* で確定）
- 対象メソッド: **GET のみ**（POST/PATCH/DELETE は非冪等のためリトライしない）
- 対象条件: HTTP 429 / 503 / ネットワークタイムアウト
- バックオフ: `base * 2^attempt + jitter`（base=300ms、最大2回 = 計3試行）
- リトライ時も `correlationId` は不変（domain-entities §2.1 不変条件）

### ALG-REFRESH: 401 時のトークンリフレッシュ
```
on 401:
  1. AuthModule.refresh() を呼ぶ
  2. 成功 → 新 accessToken で元リクエストを1回だけ再送
  3. 失敗（リフレッシュトークンも失効）→ AppShell.onAuthExpired() を発火し、DomainError('auth.token-expired') を throw
  4. リフレッシュ後の再送でも 401 → 再リフレッシュはせず auth エラーとして確定（無限ループ防止）
```

### ALG-MAP: ProblemDetails → DomainError 変換
```
mapProblemToDomainError(problem, httpStatus):
  - code = problem.type の末尾セグメント（URL から code を逆引き）。未知なら httpStatus から既定 code
  - category = code の第1セグメント（"safeguard.cooldown" → "safeguard"）
  - retryable = (httpStatus in {429, 503}) かつ メソッドが冪等
  - userMessage = problem.title（友達系トーンで表示可能）
  - internal カテゴリ（500）は detail を捨てて固定文言にする（SECURITY-09）
```

---

## ALG-STREAM: 論破ストリーミングの土台（M-12 stream=true）

Unit-1 は SSE 配信の**クライアント土台**を提供する（論破の中身は Unit-3）。

```
apiFetch(path, { stream:true }):
  1. Accept: text/event-stream で接続
  2. AsyncIterable<T> を返す。各 SSE データチャンクを JSON パースして yield
  3. 初回トークンの計測点を記録（FR-DEBATE-03 の 300ms 監視は Unit-3 が利用）
  4. 接続断 → ストリームはリトライしない（途中状態の重複を避ける）。DomainError を yield して終了
  5. キャンセル（画面離脱）→ AbortController で接続を閉じる
```

---

## ALG-TEL: テレメトリのバッファリングと送信（M-13 / B-14、Q6=A）

### クライアント側（M-13 Telemetry）

```
track(name, props):
  1. name が S-04 許可リストに無ければ no-op（不正イベントを作らない）
  2. props から S-04 許可キー以外を除去（PII 混入防止、Q4=refinedA）
  3. TelemetryEvent をメモリキューに enqueue
  4. flush 条件を満たせば flush():
       - キュー件数 >= BATCH_MAX_EVENTS（例 20）
       - 前回 flush から FLUSH_INTERVAL_SECONDS 経過（例 30s）
       - アプリが background へ遷移

flush():
  1. キューを TelemetryEnvelope に詰める（correlation + clientSentAt + schemaVersion）
  2. POST /v1/telemetry（B-14）
  3. 成功 → キュークリア
  4. 失敗 → AsyncStorage の退避キューへ追記。次回起動/次回 flush で再送
       - 退避上限 OVERFLOW_MAX_EVENTS 超過時は古いものから破棄（容量保護）
       - 再送は指数バックオフ（ApiClient のリトライとは独立）
```

### サーバー側（B-14 TelemetryIngestionService）

```
ingest_events(user_id, events):
  1. JWT sub と user_id の一致を検証（SECURITY-08）
  2. 各 event の name を S-04 メトリクスカタログと照合。未知 name は drop + warn ログ
  3. CloudWatch に EMF（MetricDatum）として put（低カーディナリティ次元のみ）
  4. 原イベントを S3 Data Lake（Parquet）へ非同期書き込み（userId/asin は属性として保持）
  5. IngestResultDto（accepted / dropped 件数）を返す
```

### 不変条件
- クライアント時刻（occurredAt）とサーバー受信時刻を両方記録し、遅延を後段で補正可能にする
- 同一イベントの二重送信が起きても、集計は idempotent な metric put で吸収（重複は誤差範囲、厳密 dedup はしない）

---

## ALG-LOG: ログ出力と PII マスキング（B-12 AuditLogger、Q4=refinedA / default-deny）

### 処理フロー

```
log(level, message, context):
  1. correlation を解決（引数 or コンテキストローカルから）
  2. context の各キー k について classify(k):
       - S-04 許可リストに 'allowed' として存在 → そのまま
       - OpenAPI で x-pii: true、または S-04 PII リストに存在 → 'pii'
       - どちらにも無い → 'unclassified'
  3. 各値に MaskingRule を適用:
       - allowed → passthrough
       - pii かつ email 形式 → partial-email（a***@example.com）
       - pii その他 → full-mask（***）
       - unclassified → full-mask（fail-safe、Q4=refinedA の核心）
  4. LogRecord を構造化 JSON で CloudWatch Logs へ出力
  5. message 本文にも PII 検出の二次防御（正規表現でメール/電話/カード番号らしき部分列をマスク）
```

### fail-safe の要点（ユーザー指摘への回答）
- **新規 PII 列が増えても安全**: 許可リスト（allowed）に明示登録しない限り `unclassified` 扱い → 自動で full-mask される。「マスクルールを足し忘れたら漏れる」が「許可リストに足し忘れたらマスクされる」に反転
- **CI ガード**: ログ・テレメトリに渡る構造体（OpenAPI スキーマ + S-04 定義）に未分類フィールドがあれば `check-pii-fields.sh`（拡張）が CI を fail させ、開発者に分類を強制する

### metric / trace
```
metric(name, value, unit, dimensions):
  - name が S-04 メトリクスカタログにあることを検証
  - dimensions に高カーディナリティ値が無いことを検証（domain-entities §5.3 不変条件）
  - EMF で CloudWatch Metrics へ put

trace(segment_name):
  - X-Ray セグメントを開始する ContextManager を返す（with 文で使用）
  - correlation.correlationId をアノテーションに付与
```

---

## ALG-NAV: AppShell ナビゲーション（M-01、詳細は frontend-components.md）

横断的な状態遷移の概要のみ（UI 詳細は frontend-components.md）:

```
- Auth ゲート: 未認証 → Auth フロー（Unit-2）/ 認証済み → タブナビゲーション
- ディープリンク（UC-03 通知タップ）: onDeepLink(url) → 対象 Screen + params に解決して navigate
- トークン失効: onAuthExpired() → セッションクリア → Auth フローへ戻す
```

---

## OpenAPI ガバナンス・ワークフロー（S-02、Q1=refinedA）

エンティティではなくプロセスのため、ここに処理フローとして記述する。

```
第1版凍結（Member A、Unit-1 期間内）:
  1. 全 UC のパス骨格（URL + メソッド）を shared/schema/paths/*.yaml に定義
  2. 共通コンポーネント（ProblemDetails / 認証 / ページネーション / 共通パラメータ）を components/ に定義
  3. 主要リソースの必須フィールド最小セットを schemas/ に定義
  4. 型生成（openapi-typescript / datamodel-code-generator）を実行し commit
  5. Prism モックが全パスに応答する状態を確認 → 「凍結」とアナウンス

実装者による拡張（Unit-2〜8、各実装者）:
  1. 担当パスに省略可能フィールドを追加（非破壊的変更のみ）
  2. shared/schema/ の契約 PR を先に出し、Member A レビュー + 型再生成
  3. 契約 PR merge 後に実装 PR を出す（混在禁止、api-contracts.md §2）
  4. 破壊的変更が必要なら /v2 path 新設 + 30 日 deprecation（api-contracts.md §6）
```

---

## アルゴリズム一覧と検証方針サマリ

| ID | ロジック | 主担当コンポーネント | PBT 性質候補 |
|---|---|---|---|
| ALG-ASIN | ASIN 抽出・正規化 | S-01 | round-trip（PBT-02）/ 冪等正規化 |
| ALG-SG | セーフガード段階判定 | S-03 / B-09 | 不変条件（remaining>=0、決定論）/ メタモルフィック |
| ALG-API | リクエストライフサイクル | M-12 | リトライ回数上限の不変条件 |
| ALG-REFRESH | 401 リフレッシュ | M-12 | 再帰しない（最大1回）の不変条件 |
| ALG-MAP | Problem→DomainError | M-12 | 全 code が category に逆引き可能 |
| ALG-STREAM | SSE 土台 | M-12 | — |
| ALG-TEL | テレメトリ・バッファ | M-13 / B-14 | serialize/deserialize round-trip（PBT-02）|
| ALG-LOG | ログ・PII マスク | B-12 | 任意 context で未分類キーが必ずマスクされる（fail-safe 性質）|

> PBT / Security の具体的なテスト戦略・カバレッジ目標は NFR Requirements / NFR Design ステージで Unit-1 向けに確定する。
