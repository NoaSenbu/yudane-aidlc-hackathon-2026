# Unit-5 Cart Intercept — NFR Requirements Part 1 Planning

> Construction Phase の Per-Unit Loop NFR Requirements ステージ。Functional Design（Q1〜Q8 + 7 巡セルフレビュー 39 件修正済み）で確定した IO / 状態 / エラー仕様を、品質特性（Performance / Scalability / Availability / Security / Reliability / Maintainability）の数値目標と技術選択に展開する。
>
> 参照: [Unit-5 functional-design.md](../unit-5-cart-intercept/functional-design/functional-design.md) / [data-model.md](../unit-5-cart-intercept/functional-design/data-model.md) / [sequence-diagrams.md](../unit-5-cart-intercept/functional-design/sequence-diagrams.md) / [要件書 §6 非機能要件](../../inception/requirements/requirements.md) / \[Unit-1 NFR Requirements（先行参考）] ※ 未着手

***

## 0. ステージ判定

| 項目                    | 判定                                                                                                                                                      |
| --------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------- |
| NFR Requirements 実行判定 | **EXECUTE（標準）** — Unit-5 は Push 通知 / EventBridge Scheduler / 外部 API（Creators API）/ Native Module と多様な技術を扱うため、性能・可用性・セキュリティの NFR 数値目標を Unit 単位で確定する必要がある |
| 深さレベル                 | **Standard** — 要件書 §6 の数値目標を Unit-5 のコンポーネント単位（B-04 / B-05 / B-06 / M-08 / M-09）にブレイクダウン。新規スタック判断は不要（既に tech.md / Unit-1 で確定済み）                         |
| Part 1 の目的            | 設計判断ポイントを `[Answer]:` タグで投げ、確定内容を Part 2 で nfr-requirements.md / tech-stack-decisions.md に展開                                                            |
| Part 2 の目的            | 確定後に Unit-5 の NFR 数値目標（SLO / SLI / レイテンシ予算 / 容量計画 / 障害時挙動）と Tech Stack 決定根拠を Markdown 化                                                                 |

***

## 1. Unit-5 NFR スコープの俯瞰

要件書 §6 の各章を Unit-5 にマッピングし、本ステージで深掘りする項目を整理:

| 要件書 § | 章タイトル        | Unit-5 適用範囲                                                                                                                                            | Part 2 で確定するもの                  |
| ----- | ------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------- |
| §6.1  | UX 中毒性指標     | 通知開封率 / カート介入成約率 / Amazon 遷移までのタップ数                                                                                                                    | Telemetry 計測ポイント・KPI 目標値        |
| §6.2  | パフォーマンス      | B-04 intake 2s / B-06 配信レイテンシ / 通知到達速度 / Cold Start                                                                                                    | SLO レイテンシ予算（per Lambda）         |
| §6.3  | スケーラビリティ     | 50 同時ユーザー → 10K DAU の成長想定 / EventBridge Scheduler 1 アカウント上限                                                                                            | スケール上限値・水平拡張ポイント                |
| §6.4  | セキュリティ       | SECURITY-01〜15（既に [§6 SECURITY 適用マトリクス](../unit-5-cart-intercept/functional-design/functional-design.md#6-security-適用マトリクスsecurity-0115-の網羅性確認) で網羅済み） | NFR レベルでの抜け漏れ確認のみ               |
| §6.5  | テスタビリティ（PBT） | PBT-01〜10（既に [§Testing Strategy.PBT カバレッジマトリクス](../unit-5-cart-intercept/functional-design/functional-design.md#pbt-カバレッジマトリクス全項目網羅5-巡目追加) で網羅済み）      | NFR レベルでの抜け漏れ確認のみ               |
| §6.6  | アクセシビリティ     | M-05 CartInterceptScreen / Push 通知の本文                                                                                                                  | カラーコントラスト・スクリーンリーダー対応の確認        |
| §6.7  | 可用性 & 運用     | Lambda DLQ / CloudWatch Alarms（既に [§3.3](../unit-5-cart-intercept/functional-design/functional-design.md#33-cloudwatch-alarms5-巡目追加issue-z) で定義済み）     | SLO 99.5% / RPO / RTO / オンコール手順 |

***

## 2. 設計判断ポイント（Part 1 の質問）

各設問は推奨案 + 根拠付きの選択肢で構成。`[Answer]:` タグに回答してください。

> **再検証メモ（2026-05-28T15:30:00Z 更新、2 次再検証で 5 件追加修正）**
>
> 当初推奨で要件書 §6.2 / §6.3 と乖離した数値を 1 次修正、別観点（外部依存 SLA / Property 6 整合 / アラーム整合 / マイルストーン整合）で 2 次修正。修正履歴:
>
> | Q | 旧推奨 | 1 次修正 | 2 次修正（最終） | 修正理由 |
> |---|---|---|---|---|
> | Q1 | B（独自数値）| **B**（要件書整合）| （変更なし）| 配信遅延 5s → 30s（要件書）/ Cold Start 2s 追加 |
> | Q2 | C（10K DAU）| C（5K DAU）| **C**（5K DAU + 内訳実態整合）| Property 6 100 件上限 + history 7 日 TTL に整合（10 履歴 → 5 active + 5 history） |
> | Q3 | C（B + Multi-AZ）| （変更なし）| **C**（全層 99.5% + エラー予算）| Critical 99.9% は外部依存（Creators API / APNs / FCM）SLA で構造的に達成不可、99.5% に統一しエラー予算配分で攻める |
> | Q4 | B（intake / dispatcher）| **B'**（+ cart_dismiss）| （変更なし）| SnapStart 追加料金ゼロかつ UX 寄与あり |
> | Q5 | B（重複許容）| B'（同 step 重複ガード）| **B'**（+ Telemetry 命名分離）| §3.3 アラーム 5% 超で重複起因の誤 alert 防止のため、`failed` と `suppressed_as_duplicate` を分離計上 |
> | Q9 | B+C（Day 3 単体）| B'+C（Day 2 単体）| **B'+C**（+ 配信レイテンシ実測 + Mock 利用明示）| Q1 で確定した B-06 配信遅延 p95 < 30s の実機検証が抜けていた / Unit-7 合意期限 5/30 18:00 と Day 3 朝の時間差に対応 |
>
> Q6 / Q7 / Q8 / Q10 は要件書整合済みで変更なし。

***

### Q1. 性能 SLO の数値目標（Unit-5 固有）

**背景**: 要件書 §6.2 で以下が確定済み:
- 論破初回トークン: 300ms 以下（Unit-3 の責務）
- **Share Extension 受領 → 商品メタ表示: 2 秒以下**（Creators API ウォームキャッシュ前提）← Unit-5 直接該当
- **カート介入通知配信遅延（登録 → 初回プッシュ）: 30 秒以下** ← Unit-5 直接該当
- アプリ起動コールドスタート: 2 秒以下

Unit-5 のコンポーネントごとのレイテンシ予算をこれに整合させて確定する。

**選択肢**:

* **A. 攻めの目標（要件書を超える厳しさ）**

  * B-04 intake p95 < 1 秒 / p99 < 1.5 秒

  * B-06 配信遅延 p95 < 5 秒（要件書 30 秒の 1/6）

  * GET /v1/cart-watch-items p95 < 200ms

  * Push 受信 → 表示 < 1 秒（OS 依存）

* **B. 要件書整合（推奨）**

  * **B-04 intake p95 < 2 秒 / p99 < 3 秒**（要件書 §6.2「Share Extension 受領 → 商品メタ表示 2 秒」と同値）

  * **B-06 配信遅延 p95 < 30 秒 / p99 < 60 秒**（登録 → 初回プッシュ、要件書 §6.2 と同値）

  * **GET /v1/cart-watch-items p95 < 500ms**（M-05 起動時の体感重視）

  * **アプリ起動 Cold Start < 2 秒**（要件書 §6.2 と同値、M-08 Share 受信時のメインアプリ起動含む）

  * **Push 受信 → 端末表示 < 3 秒**（APNs/FCM 標準動作）

* **C. 段階目標（MVP → 決勝）**

  * MVP（5/30）= B、決勝（6/26）= 必要に応じ A の一部適用

* **D. その他**

**推奨**: **B**（要件書整合）。理由 — (1) 要件書 §6.2 の数値（**Share Extension 受領 → 商品メタ表示 2 秒**、**カート介入通知配信遅延 30 秒**、**Cold Start 2 秒**）に厳密に合わせる、(2) 当初推奨で「配信レイテンシ p95 < 5 秒」と独自数値を作っていたが、要件書 30 秒との乖離はトレードオフ説明なしには採用できない、(3) p99 = p95 × 1.5 〜 2 倍の幅で long tail を許容、(4) 攻めたい場合は決勝直前に Provisioned Concurrency（[backlog B-202](../../../doc/backlog.md)）で A 達成を保険として残す。

\[Answer]: B

***

### Q2. スケーラビリティ容量計画（Unit-5 固有）

**背景**: 要件書 §6.3 で以下が確定済み:
- 初期リリース想定: **同時 50 ユーザー**
- 拡張時想定: **同時 500 ユーザー、DAU 5,000** のスパイクを吸収できる構成
- バックエンドはサーバーレス中心（Lambda / API Gateway / DynamoDB）

Unit-5 の Cart 監視リスト規模・EventBridge Scheduler 数・Push 配信数の上限を要件書整合で確定する。

**選択肢**:

* **A. MVP 規模で固定（同時 50 ユーザー、〜数百 DAU 想定）**

  * CartWatchItems 想定 数千件規模（数百 DAU × 平均 5 active + 平均 5 history、history は dismissed/purchased 後 7 日 TTL で自動削除）

  * EventBridge Schedule 想定 数百件（active × 3 ステップ）

  * Push 配信 / 日 想定 数百件

  * DDB On-Demand / Lambda 同時実行 100 で十分

* **B. 拡張時想定（同時 500 ユーザー、DAU 5K）**

  * CartWatchItems 想定 50,000 件（5K DAU × 平均 5 active + 平均 5 history、Property 6 上限 100 active と整合）

  * EventBridge Schedule 想定 75,000 件（5K × 5 active × 3 ステップ、ピーク値）

  * Push 配信 / 日 想定 75,000 件

  * DDB On-Demand 継続、Lambda 予約 500 / Reserved Concurrency 検討、End User Messaging Push の Endpoint 上限確認（10M / アカウント）

* **C. ハッカソン期間は A、決勝後の本番化は B（推奨）**

  * MVP 5/30 〜 決勝 6/26 = A（要件書 §6.3 初期 50 同時に整合）

  * 本番化判断時 = B（要件書 §6.3 拡張時 500 同時 / DAU 5K に整合）

  * 上限値は NFR 文書に明示してチェックリスト化

**推奨**: **C**（要件書整合）。理由 — (1) 要件書 §6.3 の数値（**同時 50 → 500 ユーザー、DAU 5K**）に厳密に合わせる、(2) 当初推奨で「1 年後 10K DAU 想定」と書いていたが、要件書上限の 2 倍を勝手に拡張していたため修正、(3) ハッカソン期間中の DAU は数百を超えない見込み、(4) スケーリング限界（EventBridge Scheduler 100 万 / アカウント、Lambda 1000 reserved、End User Messaging Endpoint 10M/アカウント）を NFR 文書に明示することで A → B 遷移時のチェックリスト化、(5) **見積もり内訳を Property 6（active 100 件上限）+ history 7 日 TTL の実態に整合**（再検証で「平均 5 active × 10 履歴」の出典不明な数値を「平均 5 active + 平均 5 history」に修正）、(6) Multi-AZ / Multi-Region は Q3 で別途確定。

\[Answer]: C

***

### Q3. 可用性 SLO と RPO / RTO（Unit-5 固有）

**背景**: 要件書 §6.7 で「SLO 99.5%」が定義済み。Unit-5 のコンポーネントごとの可用性目標、データ消失許容範囲（RPO）、復旧時間（RTO）を確定する。

> **重要な前提（再検証で気づき）**: B-04 は **Amazon Creators API**（外部サービス、SLA 不明）に、B-06 は **APNs / FCM**（OS ベンダー、SLA 99.9% も保証なし）に依存する。**外部依存の SLA を超える可用性は構造的に保証不可能**。よって Critical 層も 99.9% は誤りで、99.5% を上限に設計する。

**選択肢**:

* **A. 全コンポーネント一律 99.5% / RPO 1h / RTO 1h**

  * シンプル、ハッカソン規模で十分

* **B. ティア分け（旧推奨、外部依存 SLA で破綻）**

  * Critical（B-04 intake / B-06 配信）= 99.9% / RPO 5min / RTO 30min ← **不可能**

  * Important（GET 一覧 / Push Token）= 99.5% / RPO 1h / RTO 1h

  * Best-effort（Telemetry 配信）= 99% / RPO 24h / RTO 4h

* **C. 全層 99.5% + Critical はエラー予算で攻める**（推奨）

  * **全コンポーネント 99.5%**（外部依存 SLA に整合、要件書 §6.7 準拠）

  * RPO / RTO のティア分けは維持:
    * Critical（B-04 intake / B-06 配信 / cart_dismiss）= RPO 5min（DDB PITR 最小粒度）/ RTO 30min
    * Important（GET 一覧 / Push Token）= RPO 1h / RTO 1h
    * Best-effort（Telemetry 配信）= RPO 24h / RTO 4h（[Unit-1 backlog B-201](../../../doc/backlog.md) と整合）

  * **エラー予算（月間 0.5% = 約 3.6h/月）の配分**: Critical 層に 60%（2.16h）、Important 層に 30%（1.08h）、Best-effort 層に 10%（0.36h）

  * 単一 AZ 障害許容（dev のみ）+ 全 AZ 障害許容（prd 標準動作）/ Multi-Region DR は Backlog

**推奨**: **C**（全層 99.5% + エラー予算戦略）。理由 — (1) 当初推奨の B「Critical 99.9%」は **B-04 が依存する Creators API、B-06 が依存する APNs/FCM の SLA を超えるため構造的に達成不可能**（再検証で気づき、修正）、(2) 要件書 §6.7「SLO 99.5%」を全コンポーネントに統一適用、(3) Critical 層を 99.9% で攻めたい場合は **RTO の短さ（30min）+ エラー予算配分（60%）** で表現する方が現実的、(4) DDB On-Demand + Lambda + EventBridge Scheduler は **すべて Multi-AZ 標準動作**で追加設定不要、(5) Multi-Region DR は決勝後の本番化判断時の backlog（[Unit-1 §6.4 KMS Multi-Region 議論](../unit-1-platform/functional-design/data-model.md) と整合）、(6) RPO 5min は DDB PITR の最小粒度で達成可能。

\[Answer]: C

***

### Q4. Lambda Cold Start 緩和方針（Unit-5 固有）

**背景**: Unit-1 §3.1 で B-02 DebateLlmService に SnapStart 適用済み。Unit-5 の 5 Lambda（cart\_intake / cart\_dismiss / cart\_list / push\_token / notification\_dispatcher）にも SnapStart や Provisioned Concurrency を適用するか判断する。

**選択肢**:

* **A. 全 Lambda に SnapStart 適用**（Python SnapStart 追加料金ゼロ）

  * Cold Start を全コンポーネントで最小化

  * CDK 設定 +5 行 × 5 Lambda = +25 行

  * 効果: Cold Start 500-900ms → 〜300ms

* **B. Critical のみ SnapStart 適用**（cart\_intake / notification\_dispatcher）

  * 効果が大きい intake / 配信のみ最適化

  * cart\_dismiss / cart\_list / push\_token は warm 維持で実用上問題なし

* **B'. UX 直結の 3 Lambda に SnapStart 適用**（cart\_intake / cart\_dismiss / notification\_dispatcher）（推奨）

  * cart\_dismiss も追加：「いらない」タップ時の楽観的更新でロールバックが起きると UX 劣化、追加料金ゼロなら適用すべき

  * cart\_list / push\_token は warm 維持で実用上問題なし（Cold Start 起きても影響軽微）

* **C. SnapStart 不適用（hackathon 期間は default）**

  * シンプル、Cold Start は ARM\_64 + 512MB で十分速い（〜500ms）

  * 決勝後の本番化判断時に再評価

* **D. SnapStart + Provisioned Concurrency 1 並列（cart\_intake のみ、決勝直前）**

  * 万全を期す、ただし月額 \$11-15 / Lambda

**推奨**: **B'**（B + cart\_dismiss を追加）。理由 — (1) cart\_intake は US-03-01 AC-3「2 秒以内」を確実に満たすため SnapStart で Cold Start リスクを排除、(2) notification\_dispatcher は EventBridge 発火時の遅延がユーザー体験に直結、(3) **cart\_dismiss も「いらない」タップ後のロールバック時に Cold Start が露出すると UX 劣化、SnapStart 追加料金ゼロなのに除外する理由が薄い**（再検証で気づき、Issue 修正）、(4) cart\_list / push\_token は低頻度 / バッファ可能で Cold Start 許容、(5) 決勝直前で問題があれば Provisioned Concurrency を保険として追加（[backlog B-202](../../../doc/backlog.md) 参照）。

\[Answer]: B'

***

### Q5. Push 通知の配信保証レベル

**背景**: AWS End User Messaging Push は内部リトライを持つが、配信失敗時の挙動を確定する。

**選択肢**:

* **A. At-most-once（再送なし）**

  * Push 送信失敗 → NotificationLogs に failed 記録のみ、再送しない

  * シンプル、ただし 30m / 6h / 24h の追撃が 1 つでも欠ける可能性

* **B. At-least-once（EventBridge Retry + Lambda DLQ）**

  * EventBridge Scheduler が Lambda 呼出失敗時に 2 回まで retry（[functional-design.md §2.2](../unit-5-cart-intercept/functional-design/functional-design.md)）

  * Lambda 内の SendMessages 失敗は failed 記録のみ（OS 配信は best-effort）

  * 重複配信のリスクあり（Lambda が成功直後に retry 発火する稀ケース）

* **B'. At-least-once + ステップ重複ガード**（推奨）

  * B + NotificationLogs PutItem に `ConditionExpression: attribute_not_exists(stepKey)` を追加（stepKey = `{itemId}#{step}`）

  * **同一 step での重複配信を物理的に排除**（重複は失敗扱いで NotificationLogs に warn 記録）

  * 異 step（30m / 6h / 24h）の並列到達は許容（端末オフライン時の OS 制約、§1.3 端末オフライン対応で UI 再構築する設計と整合）

  * 実装コスト最小（DDB write 1 操作の ConditionExpression 追加のみ）

* **C. Exactly-once（DDB Conditional Update で完全重複防止）**

  * NotificationLogs を主キー化して厳密 exactly-once

  * 実装コスト + DDB WCU 増、Lambda 失敗時の詳細リカバリ手順も必要

**推奨**: **B'**（B + ステップ重複ガード）。理由 — (1) 当初推奨の B は「同一 step の重複配信を許容」だが、US-03-02 AC-1 の 30m 通知が 2 回連続で届くと UX 違和感、(2) **ConditionExpression 1 行追加だけで同一 step 重複を物理的に排除**できるため、実装コスト最小、(3) 異 step（30m / 6h / 24h）の並列到達は端末オフライン由来で OS 制約のため許容（§1.3 でアプリ起動時の UI 再構築で吸収する設計と整合）、(4) NotificationLogs に重複試行が warn 記録されるため監査ログ残る、(5) Exactly-once（C）は過剰、Lambda 内 DLQ のリカバリ手順を運用ドキュメント化する負担を避ける。

> **重要な実装制約（再検証で気づき、Issue PP 対応）**: B-06 NotificationDispatcher の Telemetry を以下のように **重複起因 failed と通信失敗 failed で分離**する必要がある（[Functional Design §3.3 CloudWatch Alarm 2「配信失敗率 5% 超」](../unit-5-cart-intercept/functional-design/functional-design.md#33-cloudwatch-alarms5-巡目追加issue-z) で重複起因の failed が誤 alert を起こすため）:
>
> - `notification.dispatched` dimensions: `status` ∈ `{ sent, failed, suppressed_by_safeguard, suppressed_as_duplicate }`
> - 旧仕様: `failed` のみ → 重複と通信失敗が混在
> - 新仕様: 重複起因は **`suppressed_as_duplicate`** として分離計上 → アラーム指標は `failed`（純粋な通信失敗）のみで集計
>
> § Telemetry 命名規約（[Functional Design §5.2 Backend EMF メトリクス](../unit-5-cart-intercept/functional-design/functional-design.md#52-backend-emf-メトリクスb-04--b-05--b-06)）の更新を Part 2 Generation で実施する。

\[Answer]: B'

***

### Q6. アクセシビリティ準拠レベル

**背景**: 要件書 §6.6 で「最低 WCAG 2.2 AA 相当の色コントラスト」「VoiceOver / TalkBack 対応」「全面準拠は宣言しない」と定義。Unit-5 の M-05 / Push 通知本文の対応範囲を確定する。

**選択肢**:

* **A. WCAG 2.2 AA 相当（要件書最小ライン）**

  * 色コントラスト 4.5:1 以上（NativeWind トークン管理）

  * VoiceOver / TalkBack: 主要要素に accessibility label

  * キーボードナビゲーションは対象外（Mobile のため）

* **B. WCAG 2.2 AAA（攻めの目標）**

  * 色コントラスト 7:1 以上、ダークモード強化

  * 全要素に accessibility label + ヒント

  * 動的フォントサイズ 200% 対応

* **C. A 採用 + 決勝デモ前にアクセシビリティ実機検証**

  * VoiceOver / TalkBack の実機テストを E2E-03 に追加

  * 検証結果を README に記録（プレゼン Q\&A 対策）

**推奨**: **C**（A + 実機検証）。理由 — (1) 要件書 §6.6 に整合、(2) 過剰な AAA 準拠は工数増 + 「ダメ化」コンセプトとの両立が難しい（高コントラストは UI 美感を損なう懸念）、(3) 決勝審査でアクセシビリティ質問が出た場合の備え、(4) 実機検証は Member D が Day 5（6/2）に 0.5d で実施可能、(5) NativeWind v4 のトークン管理で色コントラスト計算は自動化可能。

\[Answer]: C

***

### Q7. 監視・可観測性のレベル

**背景**: Functional Design [§3.3 CloudWatch Alarms](../unit-5-cart-intercept/functional-design/functional-design.md#33-cloudwatch-alarms5-巡目追加issue-z) で 4 系統のアラームを定義済み。NFR レベルでオンコール手順 / X-Ray トレーシング / ダッシュボード化の有無を確定する。

**選択肢**:

* **A. Alarms のみ（既定義 4 系統で十分、X-Ray 不採用）**

  * [Unit-1 backlog B-001](../../../doc/backlog.md) と整合（観測性スタック全面導入は見送り）

  * Slack 通知 + 手動調査

* **B. Alarms + X-Ray 部分採用（Critical Lambda のみ）**

  * cart\_intake / notification\_dispatcher に Active Tracing 有効化

  * 障害時の root cause 特定を高速化

  * Unit-1 backlog B-001 に部分的に踏み込む

* **C. Alarms + X-Ray + CloudWatch Dashboard 完全採用**

  * 北極星指標を Dashboard 化

  * 決勝デモで「観測性も整備済み」アピール

  * Unit-1 backlog B-001 を本 Unit で先行解決

**推奨**: **A**。理由 — (1) [Unit-1 backlog B-001](../../../doc/backlog.md) で「予選まで観測性スタック全面導入見送り」と確定済み、本 Unit が先行すると整合性が崩れる、(2) Alarms 4 系統で MVP デモ時の障害検知は十分、(3) X-Ray / Dashboard は決勝直前（6/15 以降）に Member A が一括導入する想定、(4) ハッカソン審査基準「ドキュメント品質」では既に Alarms 定義の質で評価獲得可能。

\[Answer]: A

***

### Q8. NFR 違反時の SLA エスカレーション方針

**背景**: SLO 違反（例: B-04 p95 > 2s が 1 時間継続）時の対応プロセスを確定する。

**選択肢**:

* **A. ハッカソン期間中は SLA なし（best-effort）**

  * SLO 違反は Slack 通知のみ、即時エスカレーションなし

  * 決勝デモ直前のみ手動監視強化

* **B. 段階的エスカレーション**

  * L1: Slack `#yudane-dev` 通知（5 分以内に Member D が確認）

  * L2: 1 時間継続なら `#yudane-emergency` + 全員召集

  * L3: 4 時間継続なら週次同期で根本原因分析

* **C. 全レベルで即時エスカレーション**

**推奨**: **B**。理由 — (1) [AGENTS.md §11.5 ブロッカー対応](../../../.kiro/steering/AGENTS.md) と整合（24h 以内に解消しない場合は週次同期で議題化）、(2) 段階的エスカレーションでチームの注意リソースを最適配分、(3) Member D が L1 を担当することで Functional Design §3.3 で定義した「Member D 1 次調査」責任と整合、(4) Member A は L2 以降の支援役。

\[Answer]: B

***

### Q9. NFR 検証スケジュール

**背景**: NFR 数値目標（性能・可用性・セキュリティ）を実機 / dev 環境で検証するタイミングを確定する。

**選択肢**:

* **A. 予選デモ前夜（5/29 夜）に集中検証**

  * シンプル、ただし問題発覚時の修正時間が短い

* **B. 段階的検証**

  * Day 3（5/30）= 単体性能（B-04 p95 < 2s）

  * Day 4-5（5/31-6/2）= 統合性能 + Push 配信レイテンシ

  * 6/15 以降 = 負荷試験（DAU 5K シミュレーション、Q2 整合）

* **B'. 前倒し段階的検証**（推奨）

  * **Day 2（5/29）= B-04 単体性能（dev 環境デプロイ後）**
    - intake p95 < 2s 実測（PBT-08 + curl で 100 回実行）

  * **Day 3（5/30）= 統合性能 + IT-08 / IT-09**
    - **IT-09 で B-06 配信レイテンシ p95 < 30s を実測**（EventBridge 発火 → APNs/FCM 端末到達のタイマー計測、Issue OO 対応）
    - IT-08 / IT-09 は **Unit-7 SafeguardStates の Mock fixture で実行**（Unit-7 owner との合意期限が 5/30 18:00 のため、Day 3 朝時点では実装未確定の前提、Issue QQ 対応）
    - Cold Start 検証: SnapStart 適用済み 3 Lambda（Q4 = B'）の cold/warm 比較

  * **Day 4 朝（5/31）= 予選デモ最終 rehearsal（Q&A 想定 NFR 数値の即答練習）**
    - Unit-7 SafeguardStates の実装が 5/30 18:00 までに完成していれば、IT-10（Safeguard 抑制）を実 SafeguardStates で再実行
    - 「intake p95 何 ms？」「配信遅延 30 秒以内達成？」「SLO 99.5% は外部依存制約と整合？」即答練習

  * 5/31 以降 = E2E-03 / E2E-03b / アクセシビリティ実機検証（Q6 整合）

  * 6/15 以降 = DAU 5K 負荷試験（本番化判断 Backlog）

* **C. CI で自動検証**

  * GitHub Actions で性能 PBT（PBT-08 latency）を毎 PR 実行

  * 閾値違反で merge block

**推奨**: **B' + C**（前倒し段階的検証 + CI 自動 PBT）。理由 — (1) 当初推奨では「Day 3 = 単体性能」と Functional Design §7.3 のマイルストーンより 1 日遅かったため修正、(2) **Day 2 で単体性能を検証することで Day 3 の統合検証で問題があれば 1 日の修正余裕を確保**、(3) **Day 3 で B-06 配信レイテンシ p95 < 30s を実測**（Issue OO 対応、Q1 で確定した数値の達成評価には実機計測必須）、(4) **Day 3 の IT-08 / IT-09 は Unit-7 SafeguardStates の Mock fixture で実行**（Issue QQ 対応、Unit-7 合意期限 5/30 18:00 と Day 3 朝の時間差に対応）、(5) Day 4 朝の rehearsal で予選プレゼン Q&A の「p95 何 ms？」「30 秒以内達成？」「SLO 99.5% は外部依存制約と整合？」即答練習を必須化、(6) PBT-08 を CI に組み込むことで Code Generation 後の自動検証、(7) DAU 数値を Q2 確定の 5K に整合、(8) Member D の作業負荷を Day 単位で分散できる、(9) [tech.md §6 品質ゲート](../../../.kiro/steering/tech.md) と整合。

\[Answer]: B' + C

***

### Q10. Tech Stack 追加判断（Unit-5 固有の追加ライブラリ）

**背景**: Functional Design で `expo-notifications` / `boto3 scheduler` / `boto3 pinpoint-sms-voice-v2` を使用する方針を提示。NFR 視点で他に Unit-5 固有の追加ライブラリが必要か確認。

**候補**:

* **A. AWS Lambda Powertools for Python**（B-04 / B-05 / B-06 で構造化ログ / メトリクス / トレース）

  * [Unit-1 backlog B-001](../../../doc/backlog.md) で見送り済 → 本 Unit でも未採用

* **B.** **`apscheduler`（Lambda 内のローカルスケジューラ補助）**

  * 不要（EventBridge Scheduler で完結）

* **C.** **`tenacity`（Python リトライライブラリ）**

  * B-04 が Creators API を呼ぶ際のリトライ実装に活用可能

  * Lambda 標準 retry とは別レイヤー

* **D.** **`responses`（pytest 用 HTTP モック）**

  * PBT-04（Idempotency）/ PBT-08（Latency）テスト用、dev dependency

* **E. 追加ライブラリなし**

**推奨**: **D（dev dep のみ）**。理由 — (1) 本番ロジックは boto3 と Pydantic で完結、追加依存を最小化（SECURITY-10 SBOM 観点で減らす方が good）、(2) `responses` はテスト品質向上に直結、(3) `tenacity` は Lambda 内 retry のために導入する価値があるが、Lambda 同時実行 + EventBridge Retry で代替可能なため見送り、(4) Powertools は Unit-1 整合のため不採用。

\[Answer]: D

***

## 3. 回答後のアクション（Part 2 Generation で実施）

全 Q1〜Q10 の `[Answer]:` が埋まったら、以下を順次実行する。

1. **回答内容の解析**

   * 矛盾・曖昧さがあれば追加質問

2. **Part 2 Generation: NFR Requirements ドキュメント生成**

   * `aidlc-docs/construction/unit-5-cart-intercept/nfr-requirements/nfr-requirements.md` — Performance / Scalability / Availability / Security / Reliability / Maintainability / Usability の 7 軸の数値目標 + 検証方法 + SLO 違反時のエスカレーション

   * `aidlc-docs/construction/unit-5-cart-intercept/nfr-requirements/tech-stack-decisions.md` — Tech Stack の最終確定（Q10 反映）+ 各ライブラリの採用根拠

3. **Part 2 完了後の承認ゲート → NFR Design ステージへ移行**

***

## 4. ハッカソン書類審査・予選評価軸へのインパクト

| 評価軸                | 本ドキュメントの貢献                                                                        |
| ------------------ | --------------------------------------------------------------------------------- |
| ビジネス意図の明確さ         | （直接貢献なし、技術文書のため）                                                                  |
| Unit 分解の適切さ        | **強化**: Unit-5 固有の NFR 数値目標がコンポーネント単位で確定、Unit 横断の SLO 整合が見える化                     |
| 創造性とテーマ適合性         | （直接貢献なし）                                                                          |
| ドキュメント品質           | **強化**: NFR 設計判断が `[Answer]:` タグで documented decision として残る                       |
| AI-DLC プロセス（予選評価軸） | **強化**: Per-Unit Loop の NFR Requirements を正規手順で実施、Unit-1 完了後の他 Unit 着手時のテンプレートになる |
