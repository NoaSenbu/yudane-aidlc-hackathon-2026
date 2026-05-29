# Requirements Document

## Introduction

本ドキュメントは Unit-5 Cart Intercept の **非機能要件（Non-Functional Requirements）** を確定する。Construction Phase の Per-Unit Loop NFR Requirements Part 2 Generation 成果物として、Q1〜Q10 確定（2 段階再検証で 10 件修正済み）を性能・可用性・セキュリティ等の数値目標 + 検証方法 + エスカレーション手順に展開する。

参照: [nfr-requirements-plan.md](../../plans/unit-5-cart-intercept-nfr-requirements-plan.md)（Q1〜Q10 確定済み）/ [functional-design.md](../functional-design/functional-design.md) / [data-model.md](../functional-design/data-model.md) / [要件書 §6 非機能要件](../../../inception/requirements/requirements.md)

## Glossary

| 用語 | 定義 |
|---|---|
| **SLO** (Service Level Objective) | サービスレベル目標。月間稼働率 99.5% 等の数値目標 |
| **SLI** (Service Level Indicator) | SLO 達成度を計測する指標（実測値）|
| **RPO** (Recovery Point Objective) | データ消失許容範囲（例: 5 分前までのデータは復旧可能）|
| **RTO** (Recovery Time Objective) | 復旧時間目標（例: 障害発生から 30 分以内に復旧）|
| **エラー予算** (Error Budget) | SLO の未達成許容量（月間 0.5% = 約 3.6h/月）|
| **active 監視** | CartWatchItems の `status ∈ {watching, notified-30m, notified-6h, notified-24h}` |
| **history** | CartWatchItems の `status ∈ {dismissed, purchased}`（7 日 TTL で自動削除）|
| **Critical / Important / Best-effort ティア** | RTO / RPO の優先度区分（[§3.2](#32-rto--rpo-ティア) 参照）|

## Requirements

本ドキュメントの **Requirements** は §1〜§7 の 7 軸構成で展開する:

- §1 **Performance**（Q1 確定）— レイテンシ予算、SLI 計測、性能リスク緩和
- §2 **Scalability**（Q2 確定）— MVP / 本番化規模、スケーリング判断トリガー
- §3 **Availability**（Q3 確定）— SLO 99.5% 統一、エラー予算配分、Multi-AZ / Multi-Region
- §4 **Security**（Q4 / Q5 確定 + SECURITY-01〜15）— 配信冪等性、Telemetry 命名分離
- §5 **Reliability & Operations**（Q7 / Q8 確定）— CloudWatch Alarms、エスカレーション
- §6 **Maintainability**（Q10 確定）— 採用ライブラリ、SBOM 整合性
- §7 **Usability**（Q6 確定）— アクセシビリティ、Push 通知本文の可読性

加えて §8 NFR 検証スケジュール（Q9 確定）で実機検証マイルストーンを提示する。

---

## 0. 確定事項サマリ

| Q | 論点 | 確定 |
|---|---|---|
| Q1 | 性能 SLO | B（要件書 §6.2 整合）|
| Q2 | 容量計画 | C（MVP A=数百 DAU / 本番 B=DAU 5K Roadmap）|
| Q3 | 可用性 SLO | C（全層 99.5% + RTO ティア + エラー予算配分）|
| Q4 | Cold Start 緩和 | B'（cart_intake / cart_dismiss / notification_dispatcher に SnapStart）|
| Q5 | Push 配信保証 | B'（At-least-once + 同 step 重複ガード + Telemetry 命名分離）|
| Q6 | アクセシビリティ | C（WCAG 2.2 AA 相当 + Day 5 実機検証）|
| Q7 | 監視・可観測性 | A（Alarms 4 系統のみ、X-Ray は Unit-1 backlog 整合）|
| Q8 | エスカレーション | B（L1 Slack → L2 emergency → L3 週次同期）|
| Q9 | NFR 検証スケジュール | B'+C（Day 2-4 段階検証 + CI 自動 PBT-08）|
| Q10 | 追加ライブラリ | D（`responses` dev dep のみ）|

---

## 1. Performance（Q1 確定）

要件書 §6.2 整合。Unit-5 の各コンポーネントのレイテンシ予算を以下に確定する。

### 1.1 SLO レイテンシ予算

#### 1.1.1 end-to-end SLO とコンポーネント単位の予算配分（Issue RR 対応）

要件書 §6.2「Share Extension 受領 → 商品メタ表示 2 秒以下」を **end-to-end SLO** とし、構成要素にレイテンシ予算を配分する:

| 区間 | コンポーネント | 予算（p95） | 累積（p95）|
|---|---|---|---|
| ① Share Extension 起動 + URL キャプチャ | M-08 iOS / Android Native | 200 ms | 200 ms |
| ② メインアプリ起動 / consumePendingUrl | M-01 + M-08 RN bridge | 300 ms | 500 ms |
| ③ S-01 ASIN 抽出（Mobile） | S-01 TS 版 | 10 ms | 510 ms |
| ④ HTTPS POST `/v1/cart-watch-items` | API Gateway | 100 ms | 610 ms |
| ⑤ Cognito JWT 検証 | API Gateway Authorizer | 50 ms | 660 ms |
| ⑥ B-04 Lambda 実行（**詳細は §1.1.1.1**） | B-04 Lambda | **900 ms** | 1,560 ms |
| ⑦ HTTPS レスポンス + UI 反映 | M-05 / TanStack Query | 200 ms | 1,760 ms |
| **end-to-end 合計（p95）** | — | — | **< 2,000 ms** ✅ |

##### 1.1.1.1 B-04 Lambda 内部の予算配分（Issue AAA 対応）

⑥ B-04 Lambda の 900ms 予算を内部処理単位に細分化:

| 区間 | 操作 | 予算（p95） | 累積 |
|---|---|---|---|
| ⑥-1 | Idempotency middleware（DDB PutItem ConditionExpression）| 50 ms | 50 ms |
| ⑥-2 | S-01 ASIN 再検証（Backend、Pydantic + 正規表現）| 10 ms | 60 ms |
| ⑥-3 | DDB GetItem（既存登録チェック、CartWatchItems）| 20 ms | 80 ms |
| ⑥-4 | Creators API 呼出（B-11 経由、ElastiCache キャッシュ前提でヒット時 50ms / ミス時 500ms）| **500 ms** | 580 ms |
| ⑥-5 | DDB PutItem（CartWatchItems 新規登録）| 20 ms | 600 ms |
| ⑥-6 | B-05 schedule_attacks（EventBridge CreateSchedule × 3 並列、各 60ms）| 200 ms | 800 ms |
| ⑥-7 | DDB UpdateItem（attackSchedule 属性更新）+ Telemetry EMF publish + その他 | 100 ms | **900 ms** ✅ |

> **重要な前提**: ⑥-4 Creators API 500ms は **キャッシュミス時の最大値**。キャッシュヒット時は 50ms に短縮されるため、p95 では 500ms より低くなる可能性が高い。ただし [Issue TT で確定したとおりキャッシュヒット率は実測なし、Day 3 IT-08 でベースライン計測する](#14-性能リスクと緩和策)。低ヒット率（< 50%）が観測されたら ⑥-4 予算を再調整する。

#### 1.1.2 個別 SLO 一覧

| メトリクス | コンポーネント | p95 SLO | p99 SLO | 要件書出典 |
|---|---|---|---|---|
| **Share Extension 受領 → 商品メタ表示**（end-to-end）| §1.1.1 全体 | **2 秒** | **3 秒** | §6.2「Share Extension 受領 → 商品メタ表示 2 秒以下」 |
| **B-04 cart_intake Lambda 実行時間** | B-04 Lambda（⑥ のみ）| **900 ms** | 1.5 秒 | end-to-end 2 秒の予算配分（§1.1.1）|
| **B-04 cart_dismiss Lambda 実行時間** | B-04 Lambda | 500 ms | 1 秒 | （独自、UX 観点で intake より緩く設定）|
| **B-04 cart_list Lambda 実行時間** | B-04 Lambda | 200 ms | 500 ms | （独自、M-05 起動時の体感、DDB Query のみ）|
| **カート介入通知配信遅延の精度**（30m / 6h / 24h スケジュール時刻 ± 精度）| EventBridge → B-06 → APNs/FCM | **± 30 秒** | ± 60 秒 | §6.2「カート介入通知配信遅延 30 秒以下」を **「予定時刻からのズレ 30s 以内」** と解釈（Issue SS 対応）|
| **B-06 notification_dispatcher Lambda 実行時間** | B-06 Lambda | 5 秒 | 10 秒 | （独自、配信精度 30s 内に収まれば OK）|
| **Push 端末到達 → 表示** | APNs / FCM | 3 秒 | 5 秒 | （OS 標準動作、独自、best-effort）|
| **アプリ起動 Cold Start**（Share 受信時のメインアプリ起動含む）| M-01 AppShell | **2 秒** | 3 秒 | §6.2「アプリ起動コールドスタート 2 秒以下」 |

#### 1.1.3 配信遅延 30s の解釈（Issue SS 対応）

要件書 §6.2「カート介入通知配信遅延（登録 → 初回プッシュ）30 秒以下」は **以下のいずれの解釈も成立しない**:

- ❌ **登録から 30 秒以内に最初のプッシュ発火** → 30m 待つ仕様と矛盾
- ❌ **end-to-end の Lambda 実行時間 30 秒以下** → 自明すぎて要件にする意味なし

正しい解釈は:

- ✅ **30m / 6h / 24h スケジュールの予定時刻（`createdAt + offset`）からのズレが 30 秒以内**

実測方法: NotificationLogs.sentAt − (CartWatchItems.createdAt + step_offset_seconds) の絶対値 < 30s

#### 1.1.4 配信遅延 ± 30s の予算配分（Issue FFF 対応、3 巡目追加）

配信遅延の許容誤差 ± 30s を構成要素に予算配分:

| 区間 | 説明 | 予算（p95、誤差） | 累積 |
|---|---|---|---|
| ⑴ EventBridge Scheduler 発火タイミング誤差 | AWS 公式 SLA = ± 1 秒精度、安全マージン +1s | ± **2s** | 2s |
| ⑵ B-06 Lambda Cold Start（SnapStart 適用済み）| Q4 = B' SnapStart で Cold Start 短縮 | + 1s | 3s |
| ⑶ B-06 Lambda 実行時間（DDB Get / Safeguard 判定 / End User Messaging 呼出）| **§1.1.2 の B-06 SLO p95 = 5s と整合** | + 5s | 8s |
| ⑷ End User Messaging Push API 受付 | AWS 内部 | + 2s | 10s |
| ⑸ APNs / FCM サーバー処理 | OS ベンダー | + 5s | 15s |
| ⑹ 端末到達 + iOS/Android OS の通知表示 | OS 標準動作 | + 3s | 18s |
| **合計（p95）** | — | — | **< 30s** ✅ |
| 余裕 | — | — | **12s** |

> **6 巡目修正（Issue WWW 対応）**: 旧版「⑴ Scheduler 発火誤差 ± 5s」は AWS 公式 SLA（One-time Schedule ± 1s 精度保証）に対し過剰保守的だったため ± 2s に修正、余裕が 9s → 12s に拡大。これにより APNs/FCM や端末側の遅延に対するマージンが増えた。

> **重要な制約**: 上記 ⑸ APNs / FCM の 5s と ⑹ 端末到達 3s は **OS ベンダーの動作で YUDANE 側で制御不可能**。これらが伸びると ± 30s を突破する。観測された場合は best-effort として SLO 違反を許容（外部依存 SLA 超過は構造的に保証不能、§3.1 と整合）。

### 1.2 SLI 計測方法（Issue VV 対応で EMF 即時計測に修正）

各 SLO に対する SLI（Service Level Indicator）の計測経路。**リアルタイムアラート可能性を担保するため、CloudWatch Embedded Metric Format（EMF）で即時計測を基本とする**:

| SLO | SLI 計測 | データソース | リアルタイム性 |
|---|---|---|---|
| Share → 商品メタ表示（end-to-end p95）| M-13 Telemetry `cart.intake_succeeded.latencyMs` を **EMF で CloudWatch Metrics に直接 publish** | CloudWatch Metrics | **1 分以内** |
| cart_intake Lambda p95 | Lambda Duration メトリクス | CloudWatch Lambda Insights | **1 分以内** |
| 配信遅延の精度（± 30s）| B-06 内で `delivery_drift_ms = abs(now - scheduled_time)` を EMF publish | CloudWatch Metrics | **1 分以内** |
| Cold Start | Lambda InitDuration メトリクス | CloudWatch Lambda Insights | **1 分以内** |

> **旧仕様からの変更点**: 旧版は「Telemetry → Firehose → S3 → 集計バッチ」で計測する経路を提示していたが、これだと **数時間遅延**してアラート発火するため、決勝デモ当日の障害検知に間に合わない。EMF で CloudWatch Metrics に直接 publish することで **1 分粒度のリアルタイム計測** + **Alarm 発火 5 分以内**を達成する。

S3 + バッチ集計は **長期保管 + 履歴分析用途**として併存（Telemetry は両経路で送信、EMF が即時アラート用、Firehose → S3 が長期分析用）。

### 1.3 SLO 違反時の挙動

[Q8 = B エスカレーション](#5-エスカレーション手順q8-確定) に従う。配信遅延 30 秒超が連続 3 回観測された場合は L1（Slack `#yudane-dev`）通知。

### 1.4 性能リスクと緩和策

| リスク | 緩和策 |
|---|---|
| Lambda Cold Start で intake が 2 秒超 | Q4 = B' により cart_intake / dismiss / notification_dispatcher に SnapStart 適用（[Tech Stack §3](./tech-stack-decisions.md)）|
| Creators API レート制限で intake が遅延 | ElastiCache 6h キャッシュ（B-11）でヒット率を上げる。**ヒット率は当初 95% を想定していたが実測なし、Day 3 IT-08 でベースライン計測する**（ハッカソンユーザー数では同一 ASIN シェア低く、ヒット率 30-60% 程度になる可能性あり）。低ヒット率時の緩和策: ① ダミーカタログ fallback（[backlog B-503](../../../../doc/backlog.md)、Approved 承認前期間のみ）② Creators API リトライ無し + 5xx 時は 503 応答で UI エラー表示 |
| EventBridge Scheduler の発火遅延 | 要件書 §6.2 の 30 秒目標に対し AWS SLA は秒単位精度、実装上のリスク低 |
| APNs / FCM の OS 側遅延 | OS 標準動作のため YUDANE 側で制御不可、SLO 値（端末到達 < 3s）は best-effort として明示 |

### 1.5 Mobile 側パフォーマンス SLO（4 巡目追加、Issue KKK 対応）

要件書 §6.2「リール描画 60fps 維持」を継承し、Cart 関連画面の Mobile 側パフォーマンス SLO を確定する:

| メトリクス | コンポーネント | SLO | 計測方法 |
|---|---|---|---|
| **CartInterceptScreen 表示 FPS（list mode）**| M-05 FlatList | **60 fps 維持**（最低 50fps）| React Native Performance Monitor + Reanimated v3 worklet 使用 |
| **CartInterceptScreen 表示 FPS（detail mode、追撃タイムライン）**| M-05 timeline UI | 60 fps 維持 | 同上 |
| **M-05 表示メモリ使用量**| RAM | < 50 MB | Xcode Instruments / Android Studio Profiler |
| **Share Extension メモリ使用量**| iOS Extension | < **120 MB**（OS 上限 120 MB の制約遵守）| Xcode Instruments |
| **Push 通知受信時のバッテリー消費**| M-09 background handler | **100 通知あたり < 1% バッテリー**（OS Background Push の標準処理範囲）| iOS Energy Log / Android Battery Historian で 100 通知連続受信時の差分計測 |
| **アプリ初回起動 → CartInterceptScreen 表示**| M-01 + M-05 | < 3 秒 | E2E テストでスプラッシュ → 画面遷移計測 |

### 1.6 性能 SLO の観測タイミング

| 観点 | 観測タイミング | 担当 |
|---|---|---|
| Backend SLO（§1.1）| 即時（CloudWatch EMF 1 分粒度）| §5.1 CloudWatch Alarms |
| Mobile SLO（§1.5）| **デモ前 rehearsal + Day 5 アクセシビリティ実機検証時に同時計測**（§7.3 と統合）| Member D + Member C |

---

## 2. Scalability（Q2 確定）

要件書 §6.3 整合。MVP は A 規模 / 本番化判断時に B 規模に拡張する Roadmap。

### 2.1 MVP 規模（同時 50 ユーザー、〜数百 DAU）

| リソース | 想定値 | 上限 |
|---|---|---|
| CartWatchItems アイテム数 | 数千件規模（数百 DAU × 平均 5 active + 平均 5 history、history は 7 日 TTL 自動削除）| Property 6 = 100 active / ユーザー |
| EventBridge Schedule 数 | 数百件（active × 3 ステップ）| 100 万 / アカウント（AWS 上限）|
| Push 配信 / 日 | 数百件 | 10 M Endpoint / アカウント（End User Messaging）|
| Lambda 同時実行 | 100（Reserved 不要）| 1000（アカウント default）|
| DDB On-Demand WCU/RCU | スパイク時 100 ユニット未満 | On-Demand のため自動スケール |

### 2.2 本番化規模（同時 500 ユーザー、DAU 5K）

| リソース | 想定値 | 緩和策 |
|---|---|---|
| CartWatchItems アイテム数 | **50,000 件**（5K DAU × 平均 5 active + 平均 5 history）| 標準動作で吸収 |
| EventBridge Schedule 数 | **75,000 件**（5K × 5 active × 3 ステップ、ピーク値）| 100 万上限の 7.5%、十分余裕 |
| Push 配信 / 日 | **75,000 件** | End User Messaging Endpoint 10M 上限の 0.75% |
| Lambda 同時実行 | 500 程度 | Reserved Concurrency 500 設定検討 |
| DDB On-Demand WCU/RCU | スパイク時 1000 ユニット程度 | On-Demand のため自動スケール |

### 2.3 スケーリング判断トリガー（A → B 遷移）

以下のいずれかが連続 1 週間観測されたら本番化判断:

- DAU > 500
- 同時ユーザー > 100
- CartWatchItems 累計 > 10,000 件
- Lambda 同時実行 > 50

---

## 3. Availability（Q3 確定）

### 3.1 SLO 99.5%（全層統一）

要件書 §6.7「SLO 99.5%」を全コンポーネントに統一適用。**外部依存（Creators API / APNs / FCM）の SLA を超える可用性は構造的に保証不可能**のため、99.9% は採用しない。

| コンポーネント | 月間 SLO | 月間ダウンタイム上限 |
|---|---|---|
| B-04 cart_intake | 99.5% | 約 3.6h/月 |
| B-04 cart_dismiss | 99.5% | 約 3.6h/月 |
| B-04 cart_list | 99.5% | 約 3.6h/月 |
| B-04 push_token | 99.5% | 約 3.6h/月 |
| B-06 notification_dispatcher | 99.5% | 約 3.6h/月 |

### 3.2 RTO / RPO ティア

可用性は同じでも、復旧優先度はティア分け。

| ティア | コンポーネント | RPO | RTO |
|---|---|---|---|
| **Critical** | B-04 cart_intake / B-06 notification_dispatcher / B-04 cart_dismiss | 5 min（DDB PITR 最小粒度）| 30 min |
| **Important** | B-04 cart_list / B-04 push_token | 1 hour | 1 hour |
| **Best-effort** | M-13 Telemetry 配信（Unit-1 backlog B-201 と整合）| 24 hour | 4 hour |

### 3.3 エラー予算配分（月間 0.5% = 約 3.6h）

| ティア | エラー予算配分 | 配分量 |
|---|---|---|
| Critical | 60% | 約 2.16 hour/月 |
| Important | 30% | 約 1.08 hour/月 |
| Best-effort | 10% | 約 0.36 hour/月 |

#### 3.3.1 エラー予算枯渇時の運用ルール（Issue BBB 対応）

**ハッカソン期間中（〜2026-06-26 決勝）**:

| 状態 | 対応 |
|---|---|
| ティア別予算 50% 消費 | Slack `#yudane-dev` に warn 通知（情報共有のみ）|
| ティア別予算 80% 消費 | Slack `#yudane-emergency` に alert、新機能実装の一時停止（Code Generation で本 Unit 関連 PR を hold）|
| ティア別予算 100% 消費（枯渇） | **新規 PR マージ凍結**（cdk deploy / lambda update を全停止）、復旧優先で全リソース投入。Member A が他 Unit の Critical 機能の冗長化を検討 |
| 月またぎでリセット | 翌月 1 日 0:00 (JST) に予算リセット、運用ログを `aidlc-docs/construction/unit-5-cart-intercept/nfr-requirements/error-budget-{YYYY-MM}.md` に記録 |

**本番化判断後**:

- SRE 標準どおり「エラー予算枯渇 → 新機能リリース凍結 → 信頼性投資優先」のルールを正式適用
- Multi-Region 採用判断（[Unit-1 backlog](../../unit-1-platform/functional-design/data-model.md)）と連動して再評価

> **ハッカソン期間の特例**: 月間 0.5% = 3.6h は MVP 5/30 と決勝 6/26 の 1 日で容易に枯渇しうる。デモ前後 24 時間は **特別運用期間**として、エラー予算管理は「観測のみ + Slack 共有」に留め、新機能凍結は適用しない（チーム判断による）。

### 3.4 Multi-AZ / Multi-Region

- **Multi-AZ**: DDB On-Demand + Lambda + EventBridge Scheduler は **すべて Multi-AZ 標準動作**で追加設定不要（dev / prd 共通）
- **Multi-Region**: 不採用、決勝後の本番化判断時の backlog（[Unit-1 §6.4 KMS Multi-Region 議論](../../unit-1-platform/functional-design/data-model.md) と整合）

### 3.5 障害シナリオと挙動

| 障害 | 挙動 | RTO 達成可否 |
|---|---|---|
| 単一 AZ 障害 | DDB / Lambda が他 AZ で継続稼働 | ✅ 30 min 以内に自動復旧 |
| **ElastiCache Redis 障害**（B-11 が依存）| キャッシュバイパスで Creators API 直撃 → レート制限超過時は 503 連鎖。Lambda 内で Redis タイムアウト 100ms に設定し、即時 fallback。NFR §1.1.1.1 ⑥-4 の予算 500ms を超過しないよう Redis 不在前提で動作可能 | ⚠️ **部分機能停止**（intake のみ）、AWS 側 ElastiCache 復旧待ち、N/A（外部 AWS サービス、自前復旧不可）|
| Creators API 障害 | ElastiCache キャッシュから返却、未キャッシュ ASIN は 503 応答（または `USE_DUMMY_CATALOG=true` でダミー fallback、§5.3.3 オンコール手順参照）| ⚠️ **部分機能停止**（intake のみ）、N/A（外部依存、復旧不可）|
| APNs / FCM 障害 | NotificationLogs に failed 記録、復旧後手動再送なし（EventBridge 失効）| ⚠️ **部分機能停止**（追撃通知のみ）、**N/A（OS ベンダー外部依存、自前復旧不可）**|
| DDB リージョン障害 | **Multi-Region 不採用のため復旧待ち**。本番化時の Multi-Region 採用判断は [Unit-1 backlog（KMS Multi-Region 議論）](../../unit-1-platform/functional-design/data-model.md) と整合的に再評価（採用判断ロジックは Unit-1 に集約、本 Unit はそれに従う）| ❌ RTO 超過（ハッカソン期間中は許容、本番化判断時に再評価）|

> **3 巡目修正（Issue GGG / III 対応）**: 旧版は「⚠️」「✅」「❌」のみで RTO 達成可否を曖昧に表現していたが、外部依存（APNs / FCM / Creators API / Redis）は **YUDANE 側で復旧不可能**（N/A 評価）であることを明示。**Redis 障害シナリオ**を新規追加（旧版は Creators API 障害でカバーしていたが、Redis 自体の障害は別事象）。

---

## 4. Security（Q4 = B' Cold Start / Q5 = B' 配信保証 / 全 SECURITY-01〜15）

[Functional Design §6 SECURITY 適用マトリクス](../functional-design/functional-design.md#6-security-適用マトリクスsecurity-0115-の網羅性確認) で確定済みのため、本ドキュメントでは差分のみ。

### 4.1 配信冪等性の強化（Q5 = B' 反映）

NotificationLogs テーブルに `stepKey` 属性（`{itemId}#{step}` 形式）を追加し、PutItem に `ConditionExpression: attribute_not_exists(stepKey)` を強制。**同一 step での重複配信を物理的に排除**する。

```python
# B-06 NotificationDispatcher 内
def dispatch_notification(item_id, step, payload):
    step_key = f"{item_id}#{step}"
    try:
        notification_logs_table.put_item(
            Item={
                "PK": f"USER#{user_id}",
                "SK": f"NOTIFY#{ulid.new()}",
                "stepKey": step_key,    # NEW（Q5 = B'）
                "itemId": item_id,
                "step": step,
                "status": "sent",
                # ...
            },
            ConditionExpression="attribute_not_exists(stepKey)",  # Q5 = B'
        )
    except ConditionalCheckFailedException:
        # 重複配信検知 → suppressed_as_duplicate として記録（Q5 = B' Telemetry 命名分離）
        log_duplicate_attempt(item_id, step)
        metric("notification.dispatched", 1, "Count",
               dimensions={"step": step, "status": "suppressed_as_duplicate"})
        return
```

### 4.2 Telemetry 命名分離（Q5 = B' / Issue PP 反映）

[Functional Design §5.2 Backend EMF メトリクス](../functional-design/functional-design.md#52-backend-emf-メトリクスb-04--b-05--b-06) を以下のとおり更新:

```diff
- notification.dispatched dimensions: status ∈ { sent, failed, suppressed_by_safeguard }
+ notification.dispatched dimensions: status ∈ {
+   sent,                      // 純粋な配信成功
+   failed,                    // 純粋な通信失敗（APNs/FCM エラー、Lambda エラー）
+   suppressed_by_safeguard,   // SafeguardPolicy = block で抑制
+   suppressed_as_duplicate    // NEW（Q5 = B'）: 同 step 重複起因で抑制
+ }
```

### 4.3 §3.3 CloudWatch Alarm 2 の指標修正

[Functional Design §3.3 Alarm 2「配信失敗率 5% 超」](../functional-design/functional-design.md#33-cloudwatch-alarms5-巡目追加issue-z) を以下のとおり修正:

```typescript
// 旧: failed / (sent + failed) > 5%
// 新: failed / (sent + failed) > 5%（suppressed_as_duplicate / suppressed_by_safeguard は分母分子から除外）
const failureRate = new cloudwatch.MathExpression({
  expression: '(failed / (sent + failed)) * 100',
  // suppressed_* は分母分子から除外することで、Q5 = B' の重複排除動作で誤 alert を起こさない
  usingMetrics: {
    failed: /* dimensionsMap: { status: 'failed' } */,
    sent: /* dimensionsMap: { status: 'sent' } */,
  },
});
```

### 4.4 脅威モデル（4 巡目追加、Issue LLL 対応）

SECURITY-01〜15 の網羅マトリクス（[Functional Design §6](../functional-design/functional-design.md#6-security-適用マトリクスsecurity-0115-の網羅性確認)）に対し、Unit-5 固有の **STRIDE / OWASP Mobile Top 10 / OWASP API Top 10** ベースの脅威分析を追加:

#### 4.4.1 STRIDE 分析

| 脅威カテゴリ | Unit-5 固有の脅威 | 緩和策 |
|---|---|---|
| **S**poofing | 偽の Push トークンを `POST /v1/push-tokens` に送信して他ユーザーになりすまし | Cognito JWT で `sub` を強制取得、payload の `userId` を信用しない |
| **T**ampering | NotificationLogs / CartWatchItems の改竄 | DDB IAM ポリシーで Lambda 実行ロール限定 + KMS CMEK 暗号化 |
| **R**epudiation | Amazon 遷移ログの否認 | NotificationLogs の `tappedAt` + AmazonTransitions（Unit-4 owner）の二重記録、相関 ID で監査 |
| **I**nformation Disclosure | Push 通知 payload に PII 含有、ログ漏洩 | M-13 Telemetry の userId は SHA-256 ハッシュ化（Unit-1 §1.3 整合）、Push payload は productId（公開 ASIN）のみ |
| **D**enial of Service | Cart 監視リスト 100 件超の登録試行で EventBridge Scheduler 枯渇攻撃 | Property 6（active 100 件上限） + WAF Rate-based Rule 10 req/sec/userId（[Functional Design §6.1](../functional-design/functional-design.md#61-security-15dosレート制限対策4-巡目強化)）|
| **E**levation of Privilege | Lambda Authorizer のバイパス | Cognito Authorizer 基本 + Lambda Authorizer for Safeguard（Unit-1 Q2 = C ハイブリッド整合）|

#### 4.4.2 OWASP Mobile Top 10（2024）対応

| OWASP M-* | Unit-5 該当箇所 | 緩和策 |
|---|---|---|
| M1: Improper Credential Usage | Cognito JWT を AsyncStorage 保存 | Expo SecureStore に変更（Unit-1 整合）、Push トークンは平文 OK |
| M2: Inadequate Supply Chain Security | npm / pip 依存の脆弱性 | SECURITY-10 SBOM（Snyk / Dependabot）/ §6.3 SBOM 整合性 |
| M4: Insufficient Input/Output Validation | Share Extension からの不正 URL 注入 | S-01 AsinExtractor で Mobile / Backend 二重検証（Q2 = A 確定）|
| M5: Insecure Communication | HTTPS でない通信 | TLS 1.2+ 強制（要件書 §6.4 SECURITY-02）|
| M9: Insecure Data Storage | App Group UserDefaults の URL 平文保存 | App Group は同一署名アプリ間のみ共有、iOS Keychain ほど高機密ではないが Amazon URL 自体は機密ではない（公開可能情報）。ただし容量上限を考慮 FIFO で 100 件以下に制限 |

#### 4.4.3 OWASP API Top 10（2023）対応

| OWASP API* | Unit-5 該当箇所 | 緩和策 |
|---|---|---|
| API1: Broken Object Level Authorization | 他ユーザーの cart-watch-item を取得・削除 | DDB Query は `PK = USER#{cognito.sub}` 強制、IDOR 対策（要件書 §6.4 SECURITY-08）|
| API2: Broken Authentication | JWT 検証バイパス | Cognito Authorizer + Lambda Authorizer の二重検証 |
| API3: Broken Object Property Level Authorization | productMeta に過剰な情報含有 | productMeta は B-11 Creators API の公開フィールドのみ含む（PII なし）|
| API4: Unrestricted Resource Consumption | DoS 攻撃 | Property 6（100 件上限）+ WAF Rate-based Rule + Lambda 同時実行制限 |
| API8: Security Misconfiguration | Stack 設定漏れ | cdk-nag 全 Stack 自動検証（[Functional Design §3.2](../functional-design/functional-design.md#32-cdk-nag-対応)）|

#### 4.4.4 外部依存からの脅威

| 依存先 | 脅威 | 緩和策 |
|---|---|---|
| Amazon Creators API | 偽商品メタ注入（Amazon 側がコンプロマイズ）| 信頼境界外として扱う、productMeta はキャッシュ後も RFC 8785 ハッシュ検証なし（ハッカソン規模で過剰） |
| APNs / FCM | Push トークン漏洩 / リプレイ攻撃 | **複数層の緩和策**: ① **Notification ID 重複検知**（M-09 が 24h AsyncStorage キャッシュで notificationId の重複を検知、[Functional Design §1.3](../functional-design/functional-design.md#13-m-09-pushnotificationhandlerq5--c--q7--a-反映) 整合）/ ② End User Messaging Push Endpoint 経由でトークンを抽象化、トークンローテーション時に旧 Endpoint 自動無効化（AWS 側標準動作）/ ③ APNs 側は `apns-id` ヘッダーで OS 側が重複配信を de-dup（Apple 標準動作） |
| EventBridge Scheduler | Schedule Input への注入 | Input は IAM 経由のみアクセス、改竄不可（[Functional Design §3.3 Confused Deputy 対策](../functional-design/functional-design.md#31-stack-構成)）|
| Amazon Associates Tag | アフィリエイトタグ奪取 | B-10 AssociatesLinkGenerator（Unit-4 owner）が SSM Parameter Store でタグ管理、SECURITY-12 整合 |

---

## 5. Reliability & Operations（Q7 監視 / Q8 エスカレーション）

### 5.1 監視（Q7 = A、NFR Design Q4 = A' で 1 系統追加）

[Functional Design §3.3 CloudWatch Alarms](../functional-design/functional-design.md#33-cloudwatch-alarms5-巡目追加issue-z) で確定済みの **5 系統**:

1. NotificationDispatcher DLQ メッセージ到達
2. notification.dispatched 失敗率 5% 超（4.3 で修正適用）
3. cart.scheduler.create_failed が 5 分間で 5 件超
4. Lambda Error 率（**6 Lambda × 各々**、cart_attack_scheduler_retry 含む）
5. **cart.scheduler.retry_failed が 15 分間で 5 件超**（NFR Design Q4 = A' 追加、watching_orphaned 遷移検知）

> **Q7 = A の解釈について**: Q7 = A「Alarms 4 系統のみ採用」は当初確定だったが、NFR Design Q4 = A' で B-05 リトライバッチ仕様を確定した際に Alarm 5 を追加した。Q7 の本意は「**X-Ray / CloudWatch Dashboard は採用しない**」点にあり、Alarms 数の上限を意味するものではない。本 Unit owner が必要に応じて Alarm を追加することは Q7 と矛盾しない。

X-Ray / CloudWatch Dashboard は採用しない（[Unit-1 backlog B-001](../../../doc/backlog.md) と整合）。

### 5.2 エスカレーション手順（Q8 = B）

| Level | トリガー | 通知先 | 期待応答時間 | 担当 |
|---|---|---|---|---|
| **L1** | SLO 違反 1 回検知 | Slack `#yudane-dev` | 5 分以内に確認 | Member D（1 次調査）|
| **L2** | L1 が 1 時間継続 | Slack `#yudane-emergency` + 全員召集 | 15 分以内に応答 | Member A 支援開始 |
| **L3** | L2 が 4 時間継続 | 週次同期で議題化 | 翌週金曜 17:00 | チーム全員で根本原因分析 |

[AGENTS.md §11.5 ブロッカー対応](../../../../.kiro/steering/AGENTS.md) と整合。

### 5.3 オンコール手順（具体化、Issue UU 対応）

ハッカソン期間中は専属オンコール体制なし。Member D が Functional Design §3.3 で定義された「1 次調査」責任を負う。決勝デモ当日（5/30 / 6/26）のみ Member A も同時待機。

#### 5.3.1 標準対応フロー（5 分以内に判断）

```
1. Slack `#yudane-dev` の Alarm 通知を確認
2. CloudWatch Alarm の詳細から Lambda 名 / メトリクス値を特定
3. CloudWatch Logs Insights で該当 Lambda のエラーログをクエリ（§5.3.2 のクエリ集を使用）
4. NotificationLogs / CartWatchItems の該当レコードを確認
5. 復旧判断（§5.3.3 の判断基準を使用）
6. 1 時間で解消しない場合は #yudane-emergency へエスカレーション
```

#### 5.3.2 CloudWatch Logs Insights クエリ集（即時利用可能）

**クエリ 1: B-04 / B-06 のエラーログ抽出（直近 30 分）**:

```
fields @timestamp, @message, @logStream
| filter @message like /(ERROR|Exception|Traceback)/
| sort @timestamp desc
| limit 50
```

**クエリ 2: 配信遅延が大きい Notification 抽出**:

```
fields @timestamp, itemId, step, @message
| filter @message like /delivery_drift_ms/
| parse @message /delivery_drift_ms=(?<drift>\d+)/
| filter drift > 30000
| sort drift desc
| limit 20
```

**クエリ 3: 特定 userId の最近のアクティビティ**:

```
fields @timestamp, @message
| filter @message like /USER#<userId>/
| sort @timestamp desc
| limit 100
```

#### 5.3.3 復旧判断基準

| シナリオ | 即時対応 | ロールバック判断基準 |
|---|---|---|
| Lambda Error 率 5% 超 | 直近デプロイの commit を確認、関連 PR を Slack に共有 | **直近 1h 以内にデプロイあり** → ロールバック（CDK アーティファクト前バージョンに戻す） |
| 配信遅延 30s 超が頻発 | EventBridge Scheduler のジョブ一覧を確認、target Lambda の throttle 状態を確認 | Lambda 同時実行不足 → Reserved Concurrency 一時引き上げ（CDK 変更不要、AWS Console 操作）|
| DLQ メッセージ到達 | DLQ メッセージの payload から userId / itemId / step を抽出、原因 Lambda のエラーログを §5.3.2 クエリ 3 で抽出 | DLQ 滞留 > 10 件 → Lambda 緊急停止（API Gateway 一時 503 化） |
| Creators API レート制限 | キャッシュヒット率を CloudWatch Metrics で確認 | キャッシュヒット率 < 50% かつ 5xx 連続 → ダミーカタログ強制 ON（環境変数 `USE_DUMMY_CATALOG=true` 即時設定）|

#### 5.3.4 緊急時連絡先

- **Slack Channels**:
  - `#yudane-dev`: 通常通知
  - `#yudane-emergency`: L2 以降のエスカレーション
- **Member D 連絡**: Slack DM（5 分以内応答期待）
- **Member A 連絡**: Slack DM（L2 以降、15 分以内応答期待）

---

## 6. Maintainability（Q10 追加ライブラリ）

### 6.1 採用ライブラリ（最小化方針）

| ライブラリ | 用途 | 環境 | 採用理由 |
|---|---|---|---|
| `boto3` | DDB / Lambda / Scheduler / End User Messaging クライアント | prod | AWS 標準、別途追加なし |
| `pydantic` | リクエスト / レスポンスバリデーション | prod | Unit-1 整合、SECURITY-05 |
| `expo-notifications` | iOS / Android Push トークン取得 | prod | Q1 = A Expo Config Plugin と整合 |
| `uuid` (Python / npm) | UUID v4 / v7 / v5 生成 | prod | Idempotency-Key / notificationId |
| `python-ulid` | ULID 生成（Python 側）| prod | Unit-1 整合（itemId / NotificationLogs SK の `NOTIFY#{ulid}` 形式）|
| `hypothesis` | Property-Based Testing（Backend）| **dev only** | tech.md §3 / PBT-01〜10 全項目（[Functional Design § PBT カバレッジマトリクス](../functional-design/functional-design.md#pbt-カバレッジマトリクス全項目網羅5-巡目追加) 整合）|
| `fast-check` | Property-Based Testing（Mobile / TypeScript）| **dev only** | tech.md §3 / M-08 ASIN 抽出 PBT-07 等 |
| `moto` | AWS API モック（Backend pytest）| **dev only** | PBT-08-local / PBT-04 で boto3 の DDB / Scheduler / End User Messaging をモック |
| `responses` | pytest 用 HTTP Mock | **dev only** | PBT-04 / PBT-08 テスト用（Q10 = D 確定）|

### 6.2 不採用ライブラリと理由

| 候補 | 不採用理由 |
|---|---|
| AWS Lambda Powertools for Python | [Unit-1 backlog B-001](../../../doc/backlog.md) で「予選まで観測性スタック全面導入見送り」と確定済み、本 Unit が先行すると整合性が崩れる |
| `apscheduler` | EventBridge Scheduler で完結、不要 |
| `tenacity` | B-04 / B-06 内で **boto3 デフォルトリトライ**（client config の `retries={'max_attempts': 3, 'mode': 'adaptive'}`）で代替可能。**B-11 Creators API 呼出は B-11 内で個別リトライ実装**（Unit-4 owner の責務）、本 Unit には影響しない。EventBridge Scheduler → Lambda の経路は AWS が retry を持つ |

### 6.3 SBOM 整合性

SECURITY-10 SBOM 観点で **追加 prod 依存ゼロ** を達成（既存の boto3 / pydantic / expo-notifications / uuid / python-ulid のみ、すべて Unit-1 で導入済み）。`responses` のみ dev dep として `requirements-dev.txt` に追加。

> **NFR Design 2 巡目追加（Issue IIII）**: NFR Design Q4 = A' で追加した B-05 `cart_attack_scheduler_retry` Lambda（[NFR Design Q4](../nfr-design/nfr-design-patterns.md) / [sequence-diagrams.md §7](../functional-design/sequence-diagrams.md#7-b-05-リトライバッチnfr-design-q4--a-追加)）も、上記の **既存ライブラリ（boto3 + pydantic）のみで実装可能**。EventBridge Scheduler の `CreateSchedule` API 呼出は B-04 / B-05 と同じ boto3 client を再利用、CartWatchItems の GSI1 Query / `transition_status` も既存リポジトリ実装の延長で対応する。**prod 依存追加はゼロ、SBOM 整合性に影響なし**。

### 6.4 月額コスト試算（4 巡目追加、Issue JJJ 対応）

ap-northeast-1 リージョンの 2026-05 時点の標準料金で試算（リザーブドキャパシティ / Savings Plans 不適用）。

> **6 巡目追加（Issue YYY 対応）**: 各単価の出典は以下:
>
> - **Lambda**: ARM64 = $0.00001633 per GB-second + $0.20 per million invocations（[AWS Lambda Pricing](https://aws.amazon.com/lambda/pricing/)）
> - **DynamoDB On-Demand**: WCU = $1.25 per million writes / RCU = $0.25 per million strongly consistent reads（[DynamoDB Pricing](https://aws.amazon.com/dynamodb/pricing/on-demand/)）
> - **EventBridge Scheduler**: 1400 万 invocation/月 まで無料、超過分 $1.00 per million（[EventBridge Pricing](https://aws.amazon.com/eventbridge/pricing/)）
> - **End User Messaging Push**: 100 万通知/月 まで無料、超過分 $1.00 per million APNs / $0.50 per million FCM（[End User Messaging Pricing](https://aws.amazon.com/end-user-messaging/pricing/)）
> - **検算ツール**: [AWS Pricing Calculator](https://calculator.aws/) で同等構成を再計算可能

#### 6.4.1 MVP 規模（同時 50 ユーザー、〜数百 DAU）

| リソース | 試算根拠 | 月額（USD）|
|---|---|---|
| Lambda 5 種（cart_intake / cart_dismiss / cart_list / push_token / notification_dispatcher）| ARM64 / 512MB / 平均 200ms / 5 万 invocation/月 | **$1.0** |
| **B-05 cart_attack_scheduler_retry** | ARM64 / 512MB / 平均 500ms / **2,880 invocation/月**（rate(15min) × 24h × 30 日）| **約 $0.05** |
| DDB CartWatchItems（On-Demand）| 数千件 + WCU/RCU 数千 ユニット/月 | **$1.5** |
| DDB NotificationLogs（On-Demand）| 数百件 + WCU/RCU 数百 ユニット/月 | **$0.5** |
| EventBridge Scheduler | 数百件 / 月（One-time）| **$0.0**（無料枠 1400 万件/月内）|
| End User Messaging Push | 数百件 / 月 | **$0.0**（無料枠 100 万通知/月内）|
| SQS DLQ（NotificationDispatcherDlq）| メッセージほぼゼロ | **$0.0** |
| KMS（CMEK 共通）| Unit-1 共有のため Unit-5 単独コストゼロ | **$0.0** |
| **合計（MVP）** | — | **約 $3.0/月** |

#### 6.4.2 本番化規模（同時 500 ユーザー、DAU 5K）

**前提**: 5K DAU × 平均 5 active × 3 step（30m / 6h / 24h）× 30 日 = **約 225 万通知/月**

| リソース | 試算根拠 | 月額（USD）|
|---|---|---|
| **Lambda 5 種合計** | ARM64 / 平均 200ms / **約 450 万 invocation/月**（intake 75 万 + dismiss 15 万 + list 150 万 + push_token 0.3 万 + notification_dispatcher 225 万）| **約 $5** |
| ↳ 内訳 cart_intake | 5K DAU × 5 件登録/日 × 30 日 = 75 万 invocation | $1 |
| ↳ 内訳 cart_dismiss | 5K DAU × 1 件解除/日 × 30 日 = 15 万 invocation | $0.2 |
| ↳ 内訳 cart_list | 5K DAU × 10 回表示/日 × 30 日 = 150 万 invocation | $2 |
| ↳ 内訳 push_token | 5K DAU × 0.002 回更新/日 × 30 日 = 0.3 万 invocation | $0 |
| ↳ 内訳 notification_dispatcher | 上記 225 万通知（EventBridge 発火）| $1.8 |
| **B-05 cart_attack_scheduler_retry** | ARM64 / 512MB / 平均 500ms / **2,880 invocation/月**（rate(15min) × 24h × 30 日、本番化でも頻度同じ）| **約 $0.05** |
| DDB CartWatchItems（On-Demand）| 書込 75 万件/月（intake）+ 75 万件/月（status 遷移 × 通知）+ 15 万件/月（dismiss）= **約 165 万 WCU/月**、読込 1500 万 RCU/月 | **約 $5** |
| DDB NotificationLogs（On-Demand）| 書込 **約 225 万件/月**（通知 1 件あたり 1 PutItem）+ TTL 90 日保持で蓄積 約 675 万件、読込 監査用クエリ少 | **約 $8** |
| EventBridge Scheduler | 75K active × 月内発火（active が month-late まで残る前提でピーク 75K active × 3 step = 225K Schedule 同時保持、月間作成 約 225 万件）| **$0.0**（無料枠 1400 万件/月内）|
| End User Messaging Push | **約 225 万通知/月** | **約 $2.5**（無料枠 100 万通知超過分 125 万件 × $0.000002 = $2.50）|
| SQS DLQ | メッセージほぼゼロ | **$0.0** |
| Lambda Reserved Concurrency 500（オプション）| Provisioned Concurrency ではなく Reserved のみ | **$0.0**（追加料金なし）|
| **合計（本番化）** | — | **約 $20-25/月** |

> **5 巡目修正（Issue PPP / QQQ 対応）**: 旧版は「Lambda 750 万 invocation = $30」「NotificationLogs 月 300 万件 = $80」と過大計算していたが、検算で **Lambda 約 450 万 invocation = $5、NotificationLogs 約 225 万 PutItem = $8** に修正。本番化合計も $160 → **約 $20-25** に大幅削減（クラウドクレジット範囲内で余裕、本番化判断時のコスト懸念ほぼなし）。

#### 6.4.3 SnapStart 適用 3 Lambda の追加コスト（Q4 = B'）

Python SnapStart は **追加料金ゼロ**（[Unit-1 §3.2](../../unit-1-platform/functional-design/functional-design.md#32-b-02-debatellmservice-の-snapstart-設定) と整合）。本 Unit でも追加コストなし。

> **5 巡目補足（Issue TTT 対応）**: SnapStart は published version の Snapshot を AWS が自動キャッシュするが、ユーザーへの追加課金なし（Java SnapStart と異なり Python は無料で利用可能、2024-11 GA）。本 Unit のコスト試算 §6.4.2 でも考慮不要。

#### 6.4.4 backlog 化されているコスト要素

| 項目 | 月額 | backlog 参照 |
|---|---|---|
| Provisioned Concurrency（cart_intake 1 並列）| $11-15 / Lambda | [B-202](../../../../doc/backlog.md) 決勝直前再評価 |
| LLM 通知コピー生成（Bedrock Haiku 4.5）| 月 1 万通知で約 $1 / 75 万通知で約 $75 | [B-501](../../../../doc/backlog.md) 決勝向け |
| X-Ray Active Tracing（5 Lambda）| 月 100 万トレースで約 $5 | [B-001](../../../../doc/backlog.md) 観測性スタック |

#### 6.4.5 コスト最適化判断

- MVP $3/月 + 本番化 **約 $20-25/月**（5 巡目修正後）ともに **ハッカソン期間内のクラウドクレジット範囲内**で大幅余裕
- 主なコストドライバは **DDB NotificationLogs（90 日 TTL 保持の蓄積）= $8/月** で、TTL を 30 日に短縮すれば $8 → 約 $3 に削減可能
- ただし北極星指標の長期分析（カート介入成約率の月次推移等）には 90 日が必要なため、現状維持を推奨
- Lambda コストは ARM64 + SnapStart 適用で十分最適化済み

#### 6.4.6 クラウドクレジット枯渇時の対応（6 巡目追加、Issue ZZZ 対応）

ハッカソン期間中はクラウドクレジット使用を前提とし、枯渇リスクは低いが、運用ドキュメントとして以下を定義:

| 状態 | 対応 |
|---|---|
| クレジット残高 50% 消費 | Slack `#yudane-dev` に warn 通知（Member A が monthly cost monitoring で確認）|
| クレジット残高 80% 消費 | Slack `#yudane-emergency` に alert、最適化アクションリスト発動: ① DDB NotificationLogs TTL を 30 日に短縮（$8 → $3） / ② Lambda Memory 512MB → 256MB（$5 → $3） / ③ ダミーカタログ強制 ON で Creators API 通信ゼロ化（B-503 backlog 一時前倒し） |
| クレジット枯渇 | **dev 環境停止**（CDK destroy）、prd 環境のみ最低限維持。Member A が AWS サポートに増額申請、決勝デモまでに復旧 |
| 移行手順（プロダクト化判断後）| Savings Plans 1 年契約で Lambda コスト 17% 削減 + DDB Reserved Capacity 10K WCU/RCU で 30% 削減を検討 |

---

## 7. Usability（Q6 アクセシビリティ）

### 7.1 WCAG 2.2 AA 相当の準拠目標

要件書 §6.6 整合。本 Unit のアクセシビリティ要件:

| 要素 | 目標値 | 検証方法 |
|---|---|---|
| 色コントラスト（テキスト / 背景）| 4.5:1 以上（NativeWind v4 トークン管理）| CI で `tailwindcss-aria` プラグイン実行 |
| 動的フォントサイズ | 100%〜150% で破綻しない | E2E テストで端末設定変更 |
| VoiceOver / TalkBack | 主要要素（「論破する」「いらない」「Amazon で買う」）に accessibility label 必須 | 実機テスト（Member D Day 5 = 6/2）|
| Reduce Motion | OS 設定 ON 時に到着アニメ停止 | `useReducedMotion` hook |

### 7.2 Push 通知本文の可読性

30 通知テンプレート（[Functional Design §2.3](../functional-design/functional-design.md#23-b-06-notificationdispatcherq3--a-反映テンプレートベース)）に対し:

- 本文長 50 文字以内（Notification preview の OS 標準）
- 顔文字 / 絵文字は最大 1 個（VoiceOver の読み上げ干渉回避）
- ASIN や数値 ID を含めない（読み上げで意味不明になる）

### 7.3 アクセシビリティ実機検証スケジュール

[NFR Plan Q6](../../plans/unit-5-cart-intercept-nfr-requirements-plan.md) Day 5（6/2）に **Member D（実施）+ Member C（レビュー）の協業タスク** として 0.5d で実施（4 巡目修正、Issue OOO 対応）:

1. **Member D（実施役）**: Member D が iOS / Android 端末を用意し、以下を 1 巡:
   - iOS VoiceOver で M-05 全画面を navigate
   - Android TalkBack で同上
   - iOS / Android で動的フォント 150% 設定
   - **§1.5 Mobile 側パフォーマンス SLO（FPS / メモリ / バッテリー）も同時計測**（4 巡目で追加、Issue KKK 整合）
   - 結果を `aidlc-docs/construction/unit-5-cart-intercept/nfr-requirements/a11y-validation-{date}.md` に記録

2. **Member C（レビュー役）**: Member C は Mobile + Backend が専門で VoiceOver 経験豊富、結果ドキュメントをレビューし以下を確認:
   - 主要要素（「論破する」「いらない」「Amazon で買う」）に accessibility label あり
   - 動的フォント 150% で UI 破綻なし
   - FPS / メモリ閾値が §1.5 SLO 内
   - 不備があれば Member D に修正依頼（Day 5 中に再実施）

> **協業の意図**: アクセシビリティ実機検証は Mobile 経験が物を言うため、Member D 単独では検証品質に懸念がある。Member C が Mobile 専門のため検証結果のレビューに加わることで、決勝デモ Q&A での「アクセシビリティ実機検証の網羅性は？」即答精度が向上する。

---

## 8. NFR 検証スケジュール（Q9 = B'+C 反映）

### 8.1 段階的検証（B'）

| 期日 | 検証範囲 | 担当 |
|---|---|---|
| **Day 2（5/29）** | B-04 単体性能（intake p95 < 2s 実測、PBT-08-deployed + curl × 100）| Member D |
| **Day 3 朝（5/30 9:00）** | 統合性能 + IT-08（Share→監視登録、即時実測可能）| Member D |
| **Day 3 朝（5/30 9:00）** | IT-08 / IT-09 は **Unit-7 SafeguardStates Mock fixture** で実行（Unit-7 合意期限 5/30 18:00 と Day 3 朝の時間差対応）| Member D |
| **Day 3 朝 → 昼（5/30 9:30 → 12:00）** | **IT-09 配信レイテンシ実測（30m 通知発火を観測）**: Day 3 朝 9:30 に test 用 ASIN 登録 → 10:00 に 30m 通知発火を実測（NotificationLogs.sentAt − createdAt − 1800s の絶対値 < 30s 確認）| Member D |
| **Day 3 昼 → 夕方（5/30 12:00 → 17:00）** | 統合動作確認（30m 通知タップ → 論破モード起動 → Amazon 遷移）| Member D |
| **Day 4 朝（5/31）** | 予選デモ最終 rehearsal + Q&A 想定 NFR 数値即答練習 | Member D + Member A |
| **Day 4 朝（5/31）** | Unit-7 SafeguardStates 実装完了確認後、IT-10（Safeguard 抑制）を実 SafeguardStates で再実行 | Member D + Member C |
| **Day 5（6/2）** | E2E-03 / E2E-03b / アクセシビリティ実機検証（Q6 = C）| Member D |
| **Day 5-6（6/2-6/3）** | **6h / 24h 通知の実測**（Day 3 朝登録分が 6/3 朝に 24h 通知到達 → 配信精度実測）| Member D |
| **6/15 以降** | DAU 5K 負荷試験（本番化判断 Backlog）| 未定（本番化チーム）|

> **3 巡目修正（Issue HHH 対応）**: 旧版「Day 3 = IT-09 実測」は 30m 通知発火に最低 30 分の wall clock 経過が必要なため、**朝 9:30 登録 → 10:00 発火観測**の時系列を明示。6h / 24h 通知の実測は Day 5-6 まで継続し、決勝までに全ステップの精度を検証する。

### 8.2 CI 自動検証（C）

**3 巡目修正（Issue DDD 対応）**: PBT-08 を 2 系統に分離して GitHub Actions と実機計測の役割を明確化:

#### 8.2.1 PBT-08-local（CI 上の pytest、ロジック単体）

```yaml
# .github/workflows/ci.yml に追加
- name: Run PBT-08-local (logic-only latency)
  run: pytest backend/tests/ -k "pbt_latency_local" --hypothesis-profile=ci
  # 閾値違反（p95 > 100ms、AWS Mock 応答 < 10ms 前提でロジック単体 100ms 以内）で merge block
  # 注意: GitHub Actions runner で計測するため Lambda 実機環境ではない。AWS API は moto でモック化
```

#### 8.2.2 PBT-08-deployed（dev 環境デプロイ後の実機計測）

```yaml
# .github/workflows/deploy-dev.yml に追加（Stage 3 deploy 後）
- name: Run PBT-08-deployed (Lambda real-env latency)
  run: pytest backend/tests/integration/ -k "pbt_latency_deployed" --hypothesis-profile=ci
  # 閾値違反（p95 > 2s、要件書 §6.2 整合）で deploy ロールバック
  # 実装: API Gateway endpoint に対する HTTP リクエスト × 100 で p95 計測
```

> **役割分離の理由**: GitHub Actions runner 上の pytest では Lambda コールドスタート / AWS API レイテンシ / Creators API 応答時間が再現できない。**ロジック単体の latency**（PBT-08-local）と **実機 latency**（PBT-08-deployed）を区別することで、各々で意味のある閾値を持たせる。

### 8.3 NFR Q&A 即答チェックリスト（予選 Day 4 朝 rehearsal 用）

| Q | 即答内容 |
|---|---|
| 「intake p95 何 ms？」 | 「< 2 秒、要件書 §6.2 整合。**内訳は §1.1.1 の 7 区間予算配分**（Native 200ms + RN bridge 300ms + ASIN 抽出 10ms + HTTPS 100ms + JWT 50ms + B-04 Lambda 900ms + UI 200ms = 1,760ms < 2,000ms）」|
| 「30 秒以内達成？」 | 「Day 3 IT-09 で実測。**§1.1.4 で配信遅延 ± 30s の予算配分**（Scheduler 2s + Cold Start 1s + Lambda 5s + EUM 2s + APNs/FCM 5s + 端末 3s = 18s + 余裕 12s）」|
| 「SLO 99.5% は外部依存制約と整合？」 | 「**全層 99.5% に統一**、Critical は RTO 30min + エラー予算 60% で攻める。**外部依存（Creators API / APNs / FCM）の SLA を超える可用性は構造的に保証不能**」|
| 「DAU 5K で破綻しない？」 | 「EventBridge 約 225 万件/月（**無料枠 1400 万件/月の 16% 内**、無料枠で完結）、Lambda 450 万 invocation で約 $5、Reserved Concurrency 500 で対応可能」|
| 「障害時のフォールバックは？」 | 「Creators API 障害 → ElastiCache キャッシュ + ダミーカタログ強制 ON / APNs 障害 → NotificationLogs failed 記録（外部依存復旧不可）/ DDB 障害 → Multi-Region は Unit-1 backlog で再評価」|
| **「月額コストは？」**（5 巡目追加、Issue RRR 対応）| 「**MVP $3/月、本番化 DAU 5K で約 $20-25/月**。クラウドクレジット範囲内で大幅余裕。コストドライバは DDB NotificationLogs（90 日 TTL）= $8/月、北極星指標分析のため TTL 短縮はせず現状維持」|
| **「Mobile 側パフォーマンス目標は？」**（5 巡目追加）| 「CartInterceptScreen FPS 60fps 維持、RAM < 50MB、Share Extension < 120MB（OS 上限遵守）、Push 通知 100 件あたり < 1% バッテリー、アプリ起動 < 3 秒」|
| **「セキュリティ脅威モデルは？」**（5 巡目追加）| 「STRIDE 6 カテゴリ + OWASP Mobile Top 10 5 項目 + OWASP API Top 10 5 項目 + 外部依存 4 件で網羅。代表的緩和策: IDOR は PK=USER#{cognito.sub} 強制、DoS は Property 6 100 件上限 + WAF Rate-based Rule、Push トークン漏洩は End User Messaging Endpoint 経由抽象化 + Notification ID 24h キャッシュで重複検知」|
| **「対応 OS は？」**（5 巡目追加）| 「**iOS 15.0 以降（推奨 17+）/ Android API 29 以降（推奨 33+）**。Expo SDK 52 最小要件と整合、iOS 16+ paste 許可は backlog B-502 で MVP 見送り」|
| **「アクセシビリティ対応は？」**（5 巡目追加）| 「WCAG 2.2 AA 相当。色コントラスト 4.5:1 以上、VoiceOver / TalkBack 主要要素ラベル必須、動的フォント 100-150% 対応。Day 5（6/2）に Member D 実施 + Member C レビューの協業で実機検証」|

> **5 巡目修正（Issue RRR 対応）**: 4 巡目で追加した §6.4 コスト試算 / §1.5 Mobile SLO / §4.4 脅威モデル / §1.1 OS バージョン / §7 アクセシビリティを Q&A チェックリストに反映、予選プレゼン Q&A 想定の 5 項目を追加。Day 4 朝 rehearsal でこれらを即答できるよう Member D が暗記する。

---

## 9. NFR 文書のメンテ責任（6 巡目追加、Issue XXX 対応）

NFR ドキュメントは時間とともに陳腐化するため、レビューサイクルと責任を以下に定義:

### 9.1 レビューサイクル

| ドキュメント要素 | レビュー頻度 | 主担当 | レビューイベント |
|---|---|---|---|
| §1 Performance SLO | マイルストーン契機 | Member D | 予選 5/30 直前 / 決勝 6/26 直前 / 本番化判断時 |
| §2 Scalability 容量計画 | マイルストーン契機 | Member A（Platform 担当）| 同上 |
| §3 Availability SLO + エラー予算配分 | 月次 | Member A | 月初に前月実績レビュー、エラー予算枯渇率を `aidlc-docs/.../error-budget-{YYYY-MM}.md` に記録 |
| §4 Security 脅威モデル | 四半期 | Member A + 全員レビュー | プロダクト化判断後の SOC 2 / ISO 27001 認証準備時に必須 |
| §5 Reliability & Operations | マイルストーン契機 | Member D（実施）+ Member A（レビュー）| デモ前 rehearsal で実走、フローを更新 |
| §6 Maintainability + コスト試算 | 月次 | Member A | 月初に AWS Cost Explorer の前月実績と試算を比較、乖離 30% 超なら §6.4 を更新 |
| §7 Usability アクセシビリティ | マイルストーン契機 | Member C | Day 5 / 決勝前の実機検証で結果記録 |
| §8 NFR 検証スケジュール | 完了時更新 | Member D | 各検証完了時にチェックボックスマーク + 実測値記録 |

### 9.2 更新トリガー

以下のイベントで該当セクションを **同日中** に更新:

- **要件書の変更** → §1 SLO / §2 Scalability を再確認、変更があれば版バンプ
- **AWS 料金体系の変更**（年 1 回程度の頻度）→ §6.4 単価出典確認 + 試算再計算
- **新規 Lambda / DDB テーブル追加** → §1.1 SLO 追加 + §3.1 SLO 追加 + §6.4 試算再計算
- **障害発生** → §3.5 障害シナリオに実例追記 + §5.3 オンコール手順アップデート
- **本番化判断** → §3.4 Multi-Region / §6.4.6 Savings Plans / §9.1 レビュー頻度を「月次 → 週次」に強化

### 9.3 NFR 文書の version 管理

- 本ドキュメントは Git でバージョン管理、ファイル冒頭に **`Last Updated: YYYY-MM-DD by {Member}`** を記載
- 重要変更（数値変更 / SLO 追加削除 / セクション増減）は **PR description に「NFR Change」ラベル** を付与し、Member A + 該当 Owner の二重レビュー必須

---

## 10. ハッカソン書類審査・予選評価軸へのインパクト

| 評価軸 | 本ドキュメントの貢献 |
|---|---|
| ビジネス意図の明確さ | （直接貢献なし、技術文書のため）|
| Unit 分解の適切さ | **強化**: Unit-5 NFR 数値目標が Lambda 単位で確定、Unit 横断 SLO（99.5% 全層統一）を整合 |
| 創造性とテーマ適合性 | （直接貢献なし）|
| ドキュメント品質 | **強化**: 性能・可用性・セキュリティ・運用の 7 軸 NFR が要件書数値と整合、外部依存 SLA 制約も documented decision として残る |
| AI-DLC プロセス（予選評価軸） | **強化**: 2 段階再検証（10 件修正）の透明な議論プロセス、推奨案の批判的見直しが審査員にアピール可能 |
