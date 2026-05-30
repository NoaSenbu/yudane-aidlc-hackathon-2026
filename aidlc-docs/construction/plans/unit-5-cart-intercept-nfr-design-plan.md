# Unit-5 Cart Intercept — NFR Design Part 1 Planning

> Construction Phase の Per-Unit Loop NFR Design ステージ。NFR Requirements（Q1〜Q10 確定 + 6 段階再検証で 46 件修正済み）で確定した数値目標をどう設計パターンと論理コンポーネントに落とし込むかを判断する。
>
> 参照: [Unit-5 nfr-requirements.md](../unit-5-cart-intercept/nfr-requirements/nfr-requirements.md) / [tech-stack-decisions.md](../unit-5-cart-intercept/nfr-requirements/tech-stack-decisions.md) / [Unit-5 functional-design.md](../unit-5-cart-intercept/functional-design/functional-design.md) / [data-model.md](../unit-5-cart-intercept/functional-design/data-model.md)

---

## 0. ステージ判定

| 項目 | 判定 |
|---|---|
| NFR Design 実行判定 | **EXECUTE（軽量）** — Functional Design + NFR Requirements で大半のパターン（SnapStart / Idempotency / Telemetry 命名分離 / ステータスマシン / Property 6 件数上限）が確定済み。本ステージでは **未確定のパターン選択** のみを判断する |
| 深さレベル | **Standard** — リジリエンス / スケーラビリティ / 性能 / セキュリティ / 論理コンポーネントの 5 軸で残課題を整理 |
| Part 1 の目的 | 設計判断ポイントを `[Answer]:` タグで投げ、確定内容を Part 2 で具体的なパターン定義に展開 |
| Part 2 の目的 | 確定後に nfr-design-patterns.md / logical-components.md を Markdown 化 |

---

## 1. 既に確定済みのパターン（再確認）

NFR Design で **新規判断不要** のパターンを以下に整理:

| カテゴリ | パターン | 確定 source |
|---|---|---|
| Resilience | EventBridge Retry（MaximumRetryAttempts=2 + MaximumEventAgeInSeconds=600）| Functional Design §2.2 B-05 |
| Resilience | Lambda DLQ（NotificationDispatcherDlq、SQS 14 日保持）| Functional Design §3.1 |
| Resilience | Idempotency middleware（atomic lock with ConditionExpression、5 分 TTL）| Unit-1 §3.2 |
| Resilience | NotificationLogs stepKey ConditionExpression（同 step 重複ガード）| NFR §4.1 |
| Scalability | Lambda Reserved Concurrency 500（本番化時）| NFR §2.2 |
| Scalability | DDB On-Demand 自動スケール | NFR §2 |
| Scalability | EventBridge One-time Schedule（ActionAfterCompletion=DELETE 自動削除）| Functional Design Q4 = A |
| Performance | SnapStart 適用 3 Lambda（cart_intake / cart_dismiss / notification_dispatcher）| NFR Q4 = B' |
| Performance | ARM64 アーキテクチャ（コスト 20% + 性能向上）| Unit-1 §3.2 |
| Performance | ElastiCache 6h 商品メタキャッシュ（B-11 経由）| Unit-1 §3.1 |
| Security | KMS CMEK 暗号化全 DDB / SQS DLQ | Functional Design §3.1 |
| Security | Cognito Authorizer + Lambda Authorizer（ハイブリッド）| Unit-1 Q2 = C |
| Security | Property 6 件数上限 100 active（DoS 防御）| Functional Design §6.1 |
| Security | WAF Rate-based Rule（10 req/sec/userId 想定）| Functional Design §6.1 |
| Observability | CloudWatch EMF 即時計測 | NFR §1.2 |
| Observability | CloudWatch Alarms 4 系統 + SNS → Slack | Functional Design §3.3 |

**本ステージで判断する残課題**: §2 設計判断ポイントの Q1〜Q6 のみ。

---

## 2. 設計判断ポイント（Part 1 の質問）

各設問は推奨案 + 根拠付きの選択肢で構成。`[Answer]:` タグに回答してください。

> **再検証メモ（2026-05-28T20:00:00Z 更新）**
>
> 当初推奨で 3 件の問題を再検証で発見し、以下のとおり修正:
>
> | Q | 旧推奨 | 修正後 | 修正理由 |
> |---|---|---|---|
> | Q1 | C（ハイブリッド、Creators API のみ CB）| **B（CB 不採用）**| B-11 owner（Unit-4）への依頼が §8.1 合意プロセスに未登録、Unit-4 owner が「不要」と判断したら破綻するリスク。boto3 adaptive + Lambda Reserved で十分 |
> | Q2 | A（シンプル）| **A'（staleTime 階層化）**| 一覧モード staleTime=60s / 詳細モード staleTime=0 に分離、通知タップ時に古い status を見るリスクを排除 |
> | Q4 | A（部分失敗許容）| **A'（部分失敗許容 + B-05 リトライバッチ仕様確定）**| 当初は「B-05 のリトライバッチで補完」と書きつつバッチ仕様未定義だった問題を解消、本 Q で 15 分間隔実行 / 3 回失敗で orphaned 遷移 / 並列度 10 を確定 |
>
> Q3 / Q5 / Q6 は問題なしで変更なし。

---

### Q1. Circuit Breaker パターンの採用範囲

**背景**: B-04 が依存する Creators API（B-11 経由）と B-06 が依存する End User Messaging Push は外部依存。レート制限超過 / 障害時の **連鎖障害（cascading failure）** を防ぐため Circuit Breaker パターンを検討する。

**選択肢**:

* **A. 全外部依存に Circuit Breaker 適用**
  - B-11 Creators API / End User Messaging Push の両方に CB 実装
  - ライブラリ: `pybreaker`（Python）/ `circuit-breaker-js`（TypeScript）
  - CB 状態管理は ElastiCache Redis（短時間 TTL）

* **B. CB 不採用、boto3 デフォルトリトライ + Lambda 同時実行制限で代替**
  - 簡易、追加ライブラリゼロ（NFR §6.1 整合）
  - boto3 retries `mode='adaptive'` で AWS 内部の指数バックオフ
  - 連鎖障害は Lambda Reserved Concurrency 500 で局所化

* **C. ハイブリッド: Creators API のみ CB 適用、End User Messaging Push は B**
  - Creators API は外部商用 API でレート制限が厳しい → CB 必須
  - End User Messaging Push は AWS 内部 → boto3 リトライで十分

**推奨**: **B（CB 不採用、boto3 adaptive で十分）**。理由 — (1) 当初推奨の C は「**B-11 CreatorsApiClient は Unit-4 Reel owner（Member C）の責務**」のため、本 Unit が CB 追加を依頼する形になるが §8.1 合意プロセスに登録されておらず合意期限管理が必要、Unit-4 owner が「不要」と判断したら破綻するリスク、(2) **本 Unit が CB を必要とする実用的シナリオが薄い**: B-04 cart_intake が B-11 を呼ぶのは intake 時の 1 回のみで、Lambda 同時実行 100 + Creators API レート制限を boto3 adaptive mode が吸収する、(3) Lambda Reserved Concurrency 500（本番化）で連鎖障害は局所化、(4) End User Messaging Push は AWS 内部で boto3 リトライ + adaptive mode で十分、(5) 追加ライブラリゼロ方針（NFR §6.1 / SECURITY-10 SBOM 整合）、(6) 決勝後の本番化判断時に必要なら CB 採用を [backlog] 登録（Unit-4 owner と協議）。

[Answer]: B

---

### Q2. キャッシュ戦略のレイヤリング

**背景**: M-05 の `useQuery(['cart-watch-items'])` で TanStack Query キャッシュ（staleTime=60s）。ElastiCache Redis（B-11 商品メタ TTL 6h）。**Browser/Mobile 側のキャッシュ**と **Backend キャッシュ** をどう連携させるか。

**選択肢**:

* **A. シンプル（Mobile staleTime=60s + Backend Redis 6h、独立運用）**
  - Mobile / Backend のキャッシュは互いに非協調
  - 商品メタが Redis 内で更新されても Mobile は 60s 古いまま見続ける
  - 実装最小、ハッカソン規模で十分

* **B. ETag + If-None-Match で 304 応答**
  - Backend が ETag を返却、Mobile が次回リクエストで `If-None-Match` 送信
  - Backend が 304 Not Modified を返せば Mobile は古いキャッシュを継続使用
  - ネットワーク帯域削減 + Backend Lambda 実行短縮（≈ 50ms 削減）

* **C. WebSocket / SSE で Backend → Mobile push invalidation**
  - 商品メタ更新時に Mobile に強制 invalidation 通知
  - 過剰実装、ハッカソン規模では不要

**推奨**: **A'（シンプル + staleTime 階層化）**。理由 — (1) 当初推奨の A は「60s 古いデータの不整合は UX 問題化しない」だったが、再検証で **status 遷移（watching → notified-30m）を通知タップ時に古い値で見るリスク** を発見、(2) **修正方針: 一覧モードは staleTime=60s、詳細モード（通知タップ後）は staleTime=0**（常に refetch）に階層化:

```typescript
// 一覧モード（M-05 起動時、Home hero）
useQuery({ queryKey: ['cart-watch-items'], staleTime: 60_000 })

// 詳細モード（通知タップ → CartInterceptScreen detail mode）
useCartWatchItem(asin, { staleTime: 0 })  // 通知タップ時は最新状態が必要
```

(3) 商品メタは Backend Redis 6h で問題ないため Mobile 側はその範囲で freshness 確保、(4) ETag は Lambda 負担増のため不採用、WebSocket は要件書 §6.2 で論破ストリーミング専用、(5) 決勝後に必要なら ETag への移行可能（API 後方互換）。

[Answer]: A'

---

### Q3. Bulkhead（隔壁）パターンの粒度

**背景**: 1 ユーザーの大量 intake / 異常リクエストが他ユーザーに影響しないよう、Lambda 同時実行を分離する Bulkhead パターン。

**選択肢**:

* **A. Lambda 関数ごとに Reserved Concurrency 設定（既定）**
  - cart_intake = 100 / dispatcher = 200 / list = 100 / dismiss = 50 / push_token = 20
  - シンプル、Functional Design §3.1 と整合
  - 1 関数の枯渇が他関数に影響しない（隔壁性確保）

* **B. ユーザー単位の Lambda 分離（Multi-Tenant Isolation）**
  - userId ハッシュで Lambda Function を 4 分割
  - 完全隔壁性、但し実装複雑化、CDK スタックコード 4 倍

* **C. 同 Lambda 内のスレッド/プロセス分離**
  - Python は GIL のため意味薄い
  - 不採用

**推奨**: **A（既定の関数別 Reserved Concurrency）**。理由 — (1) ハッカソン規模で同 Lambda 内のリクエスト混雑は発生しない、(2) Reserved Concurrency 数値は Functional Design §3.1 の各 Lambda 設定と整合、(3) Multi-Tenant Isolation は決勝後の Enterprise 化判断時の backlog、(4) 関数別 Reserved Concurrency が **NFR §1.5 Mobile SLO の前提**（500 同時実行で 60fps を維持できる Backend 容量）。

[Answer]: A

---

### Q4. Saga パターン採用判断（intake → schedule_attacks の分散トランザクション）

**背景**: B-04 cart_intake は **DDB PutItem + EventBridge CreateSchedule × 3** の 4 操作を行う。途中失敗時のロールバック戦略を確定する。

**選択肢**:

* **A. 部分失敗許容（既定、Compensation なし）**
  - DDB PutItem 成功 + Scheduler 1 失敗 でも CartWatchItem は status=watching で残す
  - status=watching の attackSchedule が空のアイテムを **B-05 batch リトライ** で補完
  - シンプル、Functional Design §2.1 の「部分失敗許容」と整合

* **B. Saga パターン（Compensation Transaction）**
  - 全成功なら commit、1 失敗なら DDB DeleteItem + Scheduler DeleteSchedule × 完了分で全 rollback
  - 実装複雑化、AWS Step Functions 依存（しかし Step Functions は不採用、tech.md §4）
  - ハッカソン規模で過剰

* **C. Saga パターン（Lambda 内手動 Compensation）**
  - Step Functions 使わず Lambda 内で try/except + 補償ロジック
  - B より軽量だが、Compensation 自身が失敗したら状態破綻

**推奨**: **A'（部分失敗許容 + B-05 リトライバッチ仕様確定）**。理由 — (1) Functional Design で「部分失敗許容」は確定済みだが **B-05 リトライバッチ仕様が未定義**だった問題を本 Q で解消、(2) Saga パターンは「強整合性」が必要なドメイン（金融決済等）向けで本 Unit の カート監視は **eventually consistent で OK**（追撃通知が 1 ステップ欠けても UX に致命的影響なし）、(3) Step Functions 不採用方針（tech.md §4）と整合、(4) ハッカソン規模で実装工数を最小化。

**B-05 リトライバッチ仕様（本 Q で確定、Code Generation で Member D が実装）**:

```python
# backend/src/cart/scheduler.py に追加
# 実行: EventBridge Schedule（rate(15 minutes)）で定期起動
# Lambda: cart-attack-scheduler-retry（VPC 外、Memory 512MB、Timeout 60s）

def retry_failed_schedules_handler(event, context):
    """部分失敗で attackSchedule が空の watching アイテムを補完"""
    repo = CartWatchItemsRepo()
    # GSI1 (status × createdAt) で watching の最近 24h 以内のアイテムを 100 件取得
    items = repo.list_active_without_schedule(limit=100, max_age_hours=24)

    success_count = 0
    failure_count = 0
    for item in items:
        try:
            schedule = schedule_attacks(item.userId, item.itemId, item.asin, item.createdAt)
            repo.update_attack_schedule(item.userId, item.asin, schedule)
            success_count += 1
        except Exception as e:
            log("error", "Retry failed", {"itemId": item.itemId, "error": str(e)})
            failure_count += 1

    metric("cart.scheduler.retry_succeeded", success_count, "Count")
    metric("cart.scheduler.retry_failed", failure_count, "Count")
```

**運用方針**:

- **実行頻度**: 15 分間隔（EventBridge `rate(15 minutes)`）
- **対象抽出**: GSI1（status=watching）で `attackSchedule` 属性が空 or 不完全（3 件未満）かつ `createdAt < 24h 前` のアイテム
- **並列度**: 1 batch × 最大 100 件、Lambda Reserved Concurrency 10
- **3 回失敗で諦め**: `retry_count >= 3` なら CartWatchItem を `status=watching_orphaned` に遷移（手動復旧対象、CloudWatch Alarm 発火）
- **既存スケジュールの上書き防止**: schedule_attacks() 内で既存 schedule_name を `GetSchedule` で確認、存在すればスキップ

**Code Generation での実装範囲**:

- B-05 内に `retry_failed_schedules_handler` 追加
- CDK Stack に `cartAttackSchedulerRetryFunction` Lambda 追加 + EventBridge Schedule 定期実行設定
- §3.3 CloudWatch Alarms に Alarm 5（`cart.scheduler.retry_failed > 5/15min`）追加

(5) リトライバッチで補完できない場合は手動復旧（オンコール手順 §5.3.3 に追加）。

[Answer]: A'

---

### Q5. Database Replication パターン（読み書き分離）

**背景**: DDB は単一テーブル設計だが、本番化時に **GSI のための Read Replica** や **DAX キャッシュ層** を採用するか。

**選択肢**:

* **A. 不採用（DDB On-Demand 単独）**
  - 既定、Functional Design 整合
  - GSI1（status × createdAt）は同 DDB テーブル内で索引

* **B. DAX（DynamoDB Accelerator）で Mobile read レイテンシ短縮**
  - GET /v1/cart-watch-items の p95 < 500ms をさらに < 100ms に短縮可能
  - 月額 ~$200（最小 t3.small インスタンス × 3 ノード）

* **C. Global Tables で Multi-Region read replica**
  - Multi-Region 不採用方針と矛盾、不採用

**推奨**: **A（不採用）**。理由 — (1) NFR §1.1.2 の cart_list p95 < 500ms は DDB On-Demand 単独で達成可能（実測 < 100ms 想定）、(2) DAX は月額 $200 で本番化時の DAU 5K でも費用対効果が薄い（コスト試算 §6.4.2 で本番化合計 $20-25/月 に対し $200 は過剰）、(3) Multi-Region は不採用方針整合、(4) 決勝後の本番化判断時に必要なら DAX 採用を [backlog] 登録。

[Answer]: A

---

### Q6. Telemetry / Audit Log の論理コンポーネント分離

**背景**: NFR §1.2 で Telemetry は EMF 即時計測（Backend）と AsyncStorage 永続キュー（Mobile）の 2 経路。Audit Log（B-12 AuditLogger 構造化ログ）と Telemetry は別レイヤーで実装すべきか同レイヤーか。

**選択肢**:

* **A. 完全分離（Audit = CloudWatch Logs / Telemetry = EMF + Firehose）**
  - 関心の分離（Audit は SECURITY 監査用、Telemetry は KPI 分析用）
  - Unit-1 §1.3 Telemetry 仕様 + B-12 AuditLogger 仕様と整合
  - 実装複雑化はないため自然な選択

* **B. 統合（B-12 AuditLogger に Telemetry も委譲）**
  - 単一 API、実装シンプル
  - Audit Log と Telemetry の保持期間 / 形式が異なるため運用が混乱

* **C. 統合 + フィルタリング（B-12 内で構造化ログ + Telemetry を別 stream に分岐）**
  - 統合 API でメンテ容易、ストリーム分離で保管も最適化
  - Unit-1 §2.1 B-12 AuditLogger に metric / trace 関数が既存

**推奨**: **A（完全分離）**。理由 — (1) NFR §1.2 で Telemetry EMF 経路を確定、Audit Log は CloudWatch Logs に B-12 が出力で確定済み、(2) 統合すると Telemetry の高頻度 publish が CloudWatch Logs を flood しコスト増、(3) NFR §6.4.2 でコスト試算済み（DDB / Lambda コストのみ、Logs / Firehose は無料枠内）、(4) Unit-1 §1.3 / §2.1 の既存仕様と整合、本 Unit で再判断不要。

[Answer]: A

---

## 3. 回答後のアクション（Part 2 Generation で実施）

全 Q1〜Q6 の `[Answer]:` が埋まったら、以下を順次実行する:

1. **回答内容の解析** — 矛盾・曖昧さがあれば追加質問

2. **Part 2 Generation: NFR Design ドキュメント生成**
   - `aidlc-docs/construction/unit-5-cart-intercept/nfr-design/nfr-design-patterns.md` — Resilience / Scalability / Performance / Security / Observability の 5 カテゴリにパターンマッピング、§1 既確定パターン + Q1〜Q6 確定パターンを統合
   - `aidlc-docs/construction/unit-5-cart-intercept/nfr-design/logical-components.md` — 5 Lambda + 2 DDB Table + EventBridge Scheduler + SQS DLQ + ElastiCache の論理コンポーネント図 + 相互作用パターン

3. **Part 2 完了後の承認ゲート → Infrastructure Design ステージへ移行**

---

## 4. ハッカソン書類審査・予選評価軸へのインパクト

| 評価軸 | 本ドキュメントの貢献 |
|---|---|
| ビジネス意図の明確さ | （直接貢献なし、技術文書のため）|
| Unit 分解の適切さ | **強化**: Unit-5 の NFR パターンが論理コンポーネント単位で確定、Unit 横断のパターン継承（Unit-1 SnapStart 等）が見える化 |
| 創造性とテーマ適合性 | （直接貢献なし）|
| ドキュメント品質 | **強化**: NFR 設計判断が `[Answer]:` タグで documented decision として残る |
| AI-DLC プロセス（予選評価軸） | **強化**: Per-Unit Loop の NFR Design を正規手順で実施、後続 Unit のテンプレートになる |
