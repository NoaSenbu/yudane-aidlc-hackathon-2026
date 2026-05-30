# Unit-5 Cart Intercept — Functional Design Part 1 Planning

> Construction Phase の Per-Unit Loop。Unit-5 Cart Intercept は UC-03（カート介入）の完全ループを担当する。Share Extension → ASIN 抽出 → 監視登録 → 3 段追撃通知 → 論破遷移の一連のフローを設計する。
>
> 参照: [unit-of-work.md Unit-5](../../../inception/application-design/unit-of-work.md#unit-5-cart-intercept-カート介入-uc-03) / [components.md](../../../inception/application-design/components.md) / [component-methods.md](../../../inception/application-design/component-methods.md) / [stories.md US-03-01〜05](../../../inception/user-stories/stories.md#uc-03-カート介入) / [Unit-1 functional-design.md](../../unit-1-platform/functional-design/functional-design.md) / [Unit-1 data-model.md](../../unit-1-platform/functional-design/data-model.md)

***

## 0. ステージ判定

| 項目                     | 判定                                                                                                                                                                |
| ---------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Functional Design 実行判定 | **EXECUTE** — Unit-5 はネイティブモジュール（iOS Share Extension / Android Share Target）+ EventBridge Scheduler + Push 通知の 3 技術を横断し、ビジネスロジック（ASIN 抽出 / 追撃スケジュール / 通知コピー生成）が複雑 |
| 深さレベル                  | **Standard** — Share Extension のネイティブ実装詳細は Code Generation で確定するが、RN ↔ ネイティブのインターフェース / EventBridge Scheduler のジョブ設計 / Push 通知ペイロード設計は本ステージで固める                   |
| Part 1 の目的             | 設計判断ポイントを `[Answer]:` タグで投げ、確定内容を Part 2 で具体的な仕様書に展開                                                                                                              |
| Part 2 の目的             | 確定後に各コンポーネントの IO / 状態 / エラー / イベント仕様を Markdown 化                                                                                                                  |

***

## 1. Unit-5 のスコープ再確認

### 1.1 Mobile 層（`mobile/src/features/cart/`）

| ID   | コンポーネント                      | 主な責務                                                                            |
| ---- | ---------------------------- | ------------------------------------------------------------------------------- |
| M-05 | `CartInterceptScreen`        | Share 到着アニメ / 商品取込カード / 3 段追撃タイムライン可視化 / 論破遷移ボタン                                |
| M-08 | `ShareExtensionNativeModule` | iOS Share Extension（Swift）/ Android Share Target（Kotlin）。共有 URL の受け取りとアプリへの引き渡し |
| M-09 | `PushNotificationHandler`    | APNs / FCM トークン登録 / 受信 / タップ時の Deep Link ルーティング                                 |

### 1.2 Backend 層（`backend/src/cart/`）

| ID   | コンポーネント                  | 主な責務                                                            |
| ---- | ------------------------ | --------------------------------------------------------------- |
| B-04 | `CartIntakeHandler`      | Share 経由の URL 受取、ASIN 抽出（S-01）、Creators API 呼出（B-11 経由）、カート監視登録 |
| B-05 | `CartAttackScheduler`    | 登録商品に対する 30m / 6h / 24h 追撃ジョブ作成（EventBridge Scheduler）          |
| B-06 | `NotificationDispatcher` | AWS End User Messaging Push で APNs/FCM に通知配信、追撃コピー生成            |

### 1.3 Infra 層（`infra/lib/cart-stack.ts`）

| 項目                      | 内容                                                                   |
| ----------------------- | -------------------------------------------------------------------- |
| DynamoDB                | `CartWatchItems` テーブル（Unit-1 data-model.md §4.3 で概要定義済み、本 Unit で詳細化） |
| EventBridge Scheduler   | 追撃ジョブ 3 本 / ジョブ（30m / 6h / 24h）                                      |
| End User Messaging Push | APNs / FCM チャネル設定                                                    |
| Lambda                  | B-04 / B-05 / B-06（すべて VPC 外、Unit-1 §3.1 確定）                         |
| NotificationLogs テーブル   | 配信ログ（Unit-1 data-model.md §4.5 で概要定義済み）                              |

### 1.4 外部サービス依存

| サービス                        | 用途                                             | 制約                                   |
| --------------------------- | ---------------------------------------------- | ------------------------------------ |
| Amazon Creators API         | 商品メタ取得（B-11 CreatorsApiClient 経由、Unit-4 owner） | レート制限 1 req/sec、ElastiCache 6h キャッシュ |
| EventBridge Scheduler       | 追撃ジョブスケジュール                                    | 1 アカウント 100 万スケジュール上限                |
| AWS End User Messaging Push | APNs / FCM 配信                                  | Pinpoint EoL 2026-10-30 の後継          |

### 1.5 対応ストーリー

| ID       | タイトル                                    | 核心                                        |
| -------- | --------------------------------------- | ----------------------------------------- |
| US-03-01 | Amazon Shopping から共有 → ASIN 取込で監視リスト登録  | Share Extension + ASIN 抽出 + 2 秒以内登録       |
| US-03-02 | 30 分 / 6 時間 / 24 時間の 3 段追撃通知            | EventBridge Scheduler + Push 配信 + トーン使い分け |
| US-03-03 | クリップボードに Amazon URL → 自動サジェスト           | フォアグラウンド復帰時のクリップボード検知                     |
| US-03-04 | Special Link で Amazon アプリを Deep Link 起動 | Associates Special Link 生成 + Deep Link    |
| US-03-05 | 月間上限到達時にカート介入を停止（セーフガード）                | Safeguard 連携（Unit-7 の Lambda Authorizer）  |

***

## 2. 設計判断ポイント（Part 1 の質問）

各設問は推奨案 + 根拠付きの選択肢で構成。`[Answer]:` タグに回答してください。

***

### Q1. Share Extension のネイティブ ↔ RN 通信方式

**背景**: iOS Share Extension は別プロセスで動作し、メインアプリの RN ランタイムにアクセスできない。Android Share Target はメインアプリ内の Activity で受け取れるが、iOS との統一インターフェースが必要。

**選択肢**:

* **A. Expo Config Plugin + App Group（iOS）/ Intent Filter（Android）** — Expo の Config Plugin で Share Extension を自動生成。iOS は App Group 経由で UserDefaults に URL を書き込み、メインアプリ起動時に読み取る。Android は Intent Filter で直接 Activity に渡す。RN 側は `expo-sharing` / カスタム Native Module で統一 API を提供

* **B. react-native-share-menu（コミュニティライブラリ）** — iOS / Android の Share Extension を統一的に扱うライブラリ。ただし Expo Dev Client + EAS Build との互換性確認が必要、メンテナンス状況要確認

* **C. 完全カスタム Native Module（Swift + Kotlin）** — 最大の柔軟性。iOS は App Group + NSUserDefaults + URL Scheme で起動、Android は Intent Filter。RN 側は TurboModule で JSI 経由通信。実装工数 +2d

* **D. その他**

**推奨**: **A**。理由 — (1) Expo Dev Client + EAS Build（C-5 確定）との親和性が最も高い、(2) Config Plugin で `ios/` `android/` のネイティブコードを自動生成でき、Member D のネイティブ作業を最小化、(3) App Group は iOS Share Extension の標準パターンで Apple 審査に通りやすい、(4) 予選デモ（5/30）までの 6-8 日工数に収まる、(5) 将来的に C に移行可能（Config Plugin の ejection）。

\[Answer]: A

***

### Q2. ASIN 抽出の実行場所（Mobile vs Backend）

**背景**: Share Extension で受け取った URL から ASIN を抽出する処理を、Mobile 側（即時フィードバック）で行うか、Backend 側（バリデーション集約）で行うか。S-01 AsinExtractor は TypeScript / Python 両実装が存在する。

**選択肢**:

* **A. Mobile 側で即時抽出 + Backend 側で再検証** — Mobile で S-01（TS 版）を使い即座に ASIN を表示、Backend（B-04）でも S-01（Python 版）で再検証。UX は最速（Share → 即座に商品名表示）、ただし二重実装の整合性管理が必要

* **B. Backend 側のみで抽出** — Mobile は URL をそのまま `POST /v1/cart-watch-items` に送信、B-04 が ASIN 抽出 + Creators API 呼出 + 登録を一括実行。Mobile は結果を待つ（最大 2 秒）。シンプルだが UX にラグ

* **C. Mobile 側のみで抽出、Backend は ASIN を受け取る** — Mobile で S-01 を使い ASIN を抽出、Backend には ASIN のみ送信。Backend 側のバリデーションが弱くなる（不正 ASIN 注入リスク）

**推奨**: **A**。理由 — (1) US-03-01 AC-3「2 秒以内に登録完了トースト」を満たすには Mobile 側で即座に ASIN を表示し、Backend は非同期で商品メタ取得 + 登録を行うのが最適、(2) S-01 は Shared 層で TS / Python 両方が同一正規表現なので整合性は CI で担保（Schemathesis + PBT-07）、(3) Mobile 側で不正 URL を即座にエラー表示できる（US-03-01 AC-5）、(4) Backend 側の再検証で SECURITY-05（入力バリデーション）を満たす。

\[Answer]: A

***

### Q3. 追撃通知のコピー生成方式

**背景**: US-03-02 AC-2 で「ステップに応じて軽い論破 / 記憶想起 / 最終通告のトーンが使い分けられる」と定義。通知コピーを LLM で動的生成するか、テンプレートベースにするか。

**選択肢**:

* **A. テンプレートベース（商品名 + 時間帯 + ステップで分岐）** — 30m / 6h / 24h の各ステップに 5〜10 パターンのテンプレートを用意し、商品名・価格・ユーザー名を埋め込む。LLM コスト ゼロ、レイテンシ最小、NG-6（脅迫禁止）の事前検証が容易

* **B. LLM 動的生成（Bedrock Claude Haiku 4.5）** — 商品メタ + ユーザー嗜好 + ステップ情報を Haiku に渡し、パーソナライズされた通知コピーを生成。M-1/M-2 の個別最適化が最大化、ただし Bedrock コスト + レイテンシ + NG-6 モデレーション必須

* **C. ハイブリッド: 30m はテンプレート、6h/24h は LLM** — 30m は即時性重視でテンプレート、6h/24h は時間的余裕があるため LLM で個別最適化。コスト / 品質のバランス

* **D. その他**

**推奨**: **A（MVP）→ B（決勝）**。理由 — (1) 予選 5/30 までの工数制約で LLM 通知コピー生成 + モデレーションパイプラインは +2d、(2) テンプレートでも「友達系トーン」（§2.2）を 10 パターン用意すれば十分なバリエーション、(3) NG-6 遵守の事前検証がテンプレートなら静的に完了、(4) 決勝（6/26）で B に移行すれば M-2 の個別最適化を強化できる、(5) backlog に「B-06 LLM 通知コピー生成」を登録。

\[Answer]: A

***

### Q4. EventBridge Scheduler のジョブ管理方式

**背景**: 1 商品登録につき 3 ジョブ（30m / 6h / 24h）を作成する。ジョブのライフサイクル管理（作成 / キャンセル / 完了後削除）の方式を決定する。

**選択肢**:

* **A. One-time Schedule（使い捨て）** — 各ジョブを `at()` 式の one-time schedule で作成。発火後は自動削除（`ActionAfterCompletion: DELETE`）。キャンセルは `DeleteSchedule` API で明示削除

* **B. Rate-based Schedule + DynamoDB フラグ** — 1 分間隔の共通 Schedule が DynamoDB をスキャンし、発火時刻に達したアイテムを処理。ジョブ個別作成不要、ただしスキャン負荷 + 遅延（最大 1 分）

* **C. SQS Delay Queue（30m / 6h / 24h の 3 キュー）** — SQS の DelaySeconds（最大 15 分）では 6h/24h に対応不可。Step Functions の Wait State で代替可能だが、Step Functions は不採用（tech.md §4）

* **D. その他**

**推奨**: **A**。理由 — (1) EventBridge Scheduler の one-time schedule は正確な時刻発火（秒精度）で US-03-02 の要件に最適、(2) `ActionAfterCompletion: DELETE` で発火後の自動クリーンアップ、(3) キャンセル（US-03-02 AC-4「いらない」選択時）は `DeleteSchedule` 3 回で完了、(4) 1 アカウント 100 万スケジュール上限はハッカソン規模で問題なし、(5) DynamoDB `CartWatchItems.attackSchedule` に Schedule 名を保持してキャンセル時に参照。

\[Answer]: A

***

### Q5. Push 通知トークン管理の方式

**背景**: M-09 PushNotificationHandler が APNs / FCM トークンを取得し、Backend に登録する。トークンの保存場所と更新戦略を決定する。

**選択肢**:

* **A. DynamoDB Users テーブルに** **`pushToken`** **/** **`pushPlatform`** **属性を追加** — シンプル、ユーザーと 1:1 対応。ただし複数デバイス対応が将来必要になった場合にスキーマ変更

* **B. 専用** **`DeviceTokens`** **テーブルを新設（PK=USER#{userId}, SK=DEVICE#{deviceId}）** — 複数デバイス対応、トークンローテーション履歴保持。ただしハッカソン規模では過剰

* **C. AWS End User Messaging Push のエンドポイント管理に委ねる** — End User Messaging Push が内部でトークン → エンドポイント ID のマッピングを管理。YUDANE 側は `endpointId` のみ保持

* **D. その他**

**推奨**: **C**。理由 — (1) AWS End User Messaging Push は内部でトークン管理・ローテーション・無効トークン検知を行う、(2) YUDANE 側は `Users` テーブルに `pushEndpointId` を 1 属性追加するだけ、(3) 複数デバイス対応も End User Messaging 側で管理可能、(4) トークン更新時は Mobile が `POST /v1/push-tokens` で Backend に通知 → Backend が End User Messaging の `UpdateEndpoint` を呼ぶだけ、(5) Pinpoint EoL 後の End User Messaging Push は同等の Endpoint 管理機能を提供。

\[Answer]: C

***

### Q6. クリップボード検知（US-03-03）の実装範囲

**背景**: US-03-03 はフォアグラウンド復帰時にクリップボードを読み取り、Amazon URL があればサジェストする機能。iOS 16+ では paste 許可ダイアログが必須で UX に影響する。

**選択肢**:

* **A. MVP で実装（iOS paste 許可ダイアログ込み）** — フォアグラウンド復帰時に `Clipboard.getString()` → Amazon URL 判定 → サジェスト表示。iOS は paste 許可ダイアログが毎回出る（UIPasteControl で軽減可能だが Expo 対応要確認）

* **B. MVP では見送り、決勝で実装** — Share Extension（US-03-01）が主導線として十分機能する。クリップボード検知は「あると便利」だが必須ではない。予選デモでは Share Extension のみで UC-03 を完結させる

* **C. iOS は UIPasteControl（ボタン型）、Android は従来の Clipboard API** — iOS の paste 許可ダイアログを回避するため UIPasteControl を採用。ただし Expo / RN での対応状況が不明確

**推奨**: **B**。理由 — (1) US-03-01（Share Extension）が UC-03 の核心動作であり、予選デモで十分なインパクト、(2) iOS paste 許可ダイアログの UX 問題は予選段階で解決する優先度ではない、(3) 工数 -1d で他の US-03-01/02/04/05 に集中できる、(4) 決勝（6/26）で UIPasteControl 対応を含めて実装すれば「進化した UC-03」としてアピール可能、(5) backlog に登録。

\[Answer]: B

***

### Q7. 追撃通知タップ後の遷移先

**背景**: US-03-02 AC-3 で「通知タップ → 論破モードに遷移」と定義。通知タップ時の Deep Link 設計と、論破モード（Unit-3）への遷移方式を決定する。

**選択肢**:

* **A. Deep Link で CartInterceptScreen → ユーザーが「論破する」ボタンをタップ → DebateScreen** — 通知タップで CartInterceptScreen に遷移し、商品情報 + 追撃タイムラインを表示。ユーザーが能動的に「論破する」を選択して DebateScreen へ。2 ステップだが文脈を提供

* **B. Deep Link で直接 DebateScreen に遷移（商品 ASIN をパラメータで渡す）** — 通知タップ → 即座に論破モード起動。1 ステップで最速だが、ユーザーが「何の商品だっけ？」となるリスク

* **C. ハイブリッド: 30m は CartInterceptScreen 経由、6h/24h は直接 DebateScreen** — 30m は「さっき見たやつ」なので文脈不要で直接論破、6h/24h は時間が経っているので CartInterceptScreen で文脈を提供してから論破

* **D. その他**

**推奨**: **A**。理由 — (1) CartInterceptScreen で商品情報 + 追撃タイムライン（「30m 前に通知 → 今 6h 通知」）を見せることで M-2 の「追い詰められている感」を演出、(2) 「論破する」ボタンのタップが UC-01 への明示的な遷移トリガーとなり、ユーザーの主体性を（表面上）維持、(3) Unit-3 Debate との API 契約が `POST /v1/debate-sessions { trigger: "cart-attack", productId }` で明確、(4) 直接 DebateScreen に飛ばすと「何の商品？」問題 + Safeguard 判定の UI フィードバックが困難。

\[Answer]: A

***

### Q8. CartWatchItems テーブルの詳細設計

**背景**: Unit-1 data-model.md §4.3 で概要が定義済み（PK=USER#{userId}, SK=CART#{asin}）。追撃ステータス管理 / TTL / GSI の詳細を確定する。

**選択肢**:

* **A. ステータスマシン方式（status 属性で遷移管理）** — `watching` → `notified-30m` → `notified-6h` → `notified-24h` → `purchased` / `dismissed`。各通知発火時に B-06 が status を更新。TTL は `dismissed` / `purchased` 後 7 日で自動削除

* **B. イベントソーシング方式（CartWatchEvents テーブルを別途新設）** — CartWatchItems は最新状態のみ保持、CartWatchEvents に全イベント（registered / notified-30m / notified-6h / notified-24h / purchased / dismissed）を追記。監査ログ + 分析に強い、ただし実装工数 +1d

* **C. その他**

**推奨**: **A**。理由 — (1) ハッカソン規模ではステータスマシンで十分、(2) 監査ログは B-12 AuditLogger + NotificationLogs テーブルで代替可能、(3) イベントソーシングは決勝後のプロダクト化判断時に検討（backlog）、(4) TTL 7 日で不要データを自動クリーンアップ、(5) GSI は `GSI1 (status → createdAt)` で「watching 中の全アイテム」を効率的にクエリ（B-05 のバッチ処理用）。

\[Answer]: A

***

## 3. 回答後のアクション（Part 2 Generation で実施）

全 Q1〜Q8 の `[Answer]:` が埋まったら、以下を順次実行する。

1. **回答内容の解析**

   * 矛盾・曖昧さがあれば追加質問

2. **Part 2 Generation: Functional Design ドキュメント生成**

   * `aidlc-docs/construction/unit-5-cart-intercept/functional-design/functional-design.md` — Mobile / Backend / Infra 各層の IO / 状態 / エラー仕様

   * `aidlc-docs/construction/unit-5-cart-intercept/functional-design/data-model.md` — CartWatchItems / NotificationLogs テーブル詳細設計

   * `aidlc-docs/construction/unit-5-cart-intercept/functional-design/sequence-diagrams.md` — Share Extension → 登録 / 追撃通知 / 通知タップ → 論破遷移 の Mermaid sequence diagram

3. **Part 2 完了後の承認ゲート → NFR Requirements ステージへ移行**

***

## 4. ハッカソン書類審査・予選評価軸へのインパクト

| 評価軸                | 本ドキュメントの貢献                                                                                   |
| ------------------ | -------------------------------------------------------------------------------------------- |
| ビジネス意図の明確さ         | **強化**: UC-03 の「迷いの置き場所を外部化する」メカニズムが技術仕様レベルで具体化                                              |
| Unit 分解の適切さ        | **強化**: Unit-5 が Unit-1（基盤）/ Unit-3（論破遷移先）/ Unit-4（リール右スワイプ連携）/ Unit-7（Safeguard）との依存を明示的に設計 |
| 創造性とテーマ適合性         | **強化**: 3 段追撃（30m/6h/24h）の「しつこさ」が M-2（購買快楽のストレス解消剤化）を加速する設計意図を明文化                            |
| ドキュメント品質           | **強化**: Q1〜Q8 の設計判断が documented decision として残る                                               |
| AI-DLC プロセス（予選評価軸） | **強化**: Per-Unit Loop の Functional Design を Unit-1 と同じ正規手順で実施                                |
