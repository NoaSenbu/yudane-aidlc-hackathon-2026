# Unit-2 Auth & Profile — Functional Design Plan

> Construction Phase / Per-Unit Loop / Unit-2 Auth & Profile の機能設計計画。
> 参照: [unit-of-work.md](../../inception/application-design/unit-of-work.md) / [stories.md US-AUTH-01/02/03](../../inception/user-stories/stories.md) / [component-methods.md](../../inception/application-design/component-methods.md) / [Unit-1 成果物](../unit-1-platform/) / [shared-infrastructure.md](../shared-infrastructure.md)
> 作成: 2026-05-29 / ステージ: 🟢 CONSTRUCTION / Functional Design
> 担当: Member A（Unit-1 完了後）

---

## 0. Unit-2 の位置づけ

ユーザー登録・認証・プロファイル初期化・ホーム画面・日次/週次集計を提供する。Unit-1 の基盤（OpenAPI 骨格 / ApiClient / AuditLogger / SafeguardPolicy / Cognito User Pool / DynamoDB 共通設定）の上に乗る最初の機能 Unit。

| 層 | コンポーネント | 機能設計で扱う対象 |
|---|---|---|
| Mobile | M-02 HomeScreen | エージェント稼働 hero / カート監視リスト / カレンダー連動カード / サブダッシュボード |
| Mobile | M-11 AuthModule | Cognito 認証（サインアップ / ログイン / MFA / トークン管理、Amplify Auth v6） |
| Backend | B-01 AuthEdgeLambda | Cognito トリガー（Post Confirmation 初期化 / Pre Token Generation claim 付与） |
| Backend | B-08 PreferenceVectorUpdater | 日次嗜好ベクトル更新 + 週次指標集計（Unit-8 へ供給） |

### 対応 UC / ストーリー
- UC-05（称号 / Lv 付与の判定ロジック）/ UC-06（サブダッシュボード表示）/ UC-07（嗜好ベクトル更新）/ UC-08 初期化
- **US-AUTH-01**（オンボーディング予算感アンケート 90 秒）/ **US-AUTH-02**（MFA）/ **US-AUTH-03**（負債自己申告 → 初期セーフガード）

### Unit-1 からの継承（再設計しない）
- DomainError 体系 / ProblemDetails（Unit-1 exceptions）
- ApiClient（M-12）/ AuditLogger（B-12）/ require_owner（IDOR）
- SafeguardPolicy（S-03）— US-AUTH-03 の負債フラグ → 実効上限 35% は S-03 の `decideAllow`（debt 半減）を利用
- Cognito User Pool（MFA REQUIRED は platform-stack で設定済み）
- OpenAPI の auth パス骨格（`/v1/users/{userId}/profile` / `/v1/users/{userId}`）に省略可能フィールドを非破壊で追記

---

## 1. 設計判断のための質問

`[Answer]:` タグで回答してください。

### Question 1
オンボーディング 5 項目（月間使える額 / 月間貯金額 / 好きなブランド 5+ / NG カテゴリ / 負債フラグ）の **ドメインモデルと保存単位**をどうしますか？（US-AUTH-01 AC-2、90 秒完了 / 途中再開）

A) **単一 `UserProfile` 集約 + 段階保存**（5 画面それぞれで部分保存し `onboardingStep` を記録 → 途中離脱から再開（AC-3 IDEMPOTENCY）。完了時に `profileCompleted=true`）— US-AUTH-01 AC-1/3 に最適、推奨
B) 全項目を最終画面で一括保存（途中保存しない、再開は最初から）
C) 項目ごとに別エンティティ（budget / brands / ngCategories を別テーブル）に分割保存
X) Other（[Answer]: の後に記述）

[Answer]: A

### Question 2
B-01 AuthEdgeLambda の **Post Confirmation 初期化で作るエンティティ群**をどうしますか？（新規ユーザーの初期状態）

A) **User / PreferenceVector(empty) / SafeguardState を一括初期化**（Cognito sub を id に、SafeguardState は負債フラグ未確定なのでオンボ完了時に上限確定。冪等化のため既存チェック）— SVC-05 オーケストレーションに整合、推奨
B) User のみ初期化し、PreferenceVector / SafeguardState はオンボ完了 API で作る
C) 初期化は最小（User レコードのみ）、他は遅延作成（初回アクセス時）
X) Other（[Answer]: の後に記述）

[Answer]: A

### Question 3
US-AUTH-03 の **負債フラグと初期セーフガードの連動**をどう設計しますか？（AC-2: 上限 35% / AC-3: 24h 非活性 / AC-4: 解除は 72h クーリングオフ）

A) **負債フラグ → SafeguardState に反映 → S-03 SafeguardPolicy が自動的に DEBT 比率（0.35）適用**（Unit-1 の decideAllow をそのまま利用、Unit-2 は has_debt の保存と解除フローのみ実装。解除は 72h クーリングオフのステートマシン）— Unit-1 ロジック再利用、推奨
B) Unit-2 が独自に負債者向け上限計算ロジックを実装（S-03 を使わない）
C) 負債フラグの保存のみ行い、上限適用は Unit-7 Safeguard に委譲
X) Other（[Answer]: の後に記述）

[Answer]: A

### Question 4
M-11 AuthModule の **MFA フローと認証状態管理**をどうしますか？（US-AUTH-02、Amplify Auth v6 / Cognito、SECURITY-12）

A) **Amplify Auth v6 をラップした AuthModule + Unit-1 AuthTokenProvider 実装**（signUp/confirmSignUp/signIn/confirmMfa/refresh/signOut/getCurrentUser を実装し、Unit-1 ApiClient の `AuthTokenProvider` インターフェースを満たす。MFA リセットは 72h 冷却、5 回失敗で 15 分ロックは Cognito + CloudWatch Alarm）— Unit-1 ApiClient と直結、推奨
B) Amplify を使わず Cognito SDK を直接叩く（tech.md で非推奨）
C) AuthModule は薄いラッパーのみ、トークン管理は各画面が個別実装
X) Other（[Answer]: の後に記述）

[Answer]: A

### Question 5
B-08 PreferenceVectorUpdater の **日次バッチと週次集計の責務分担**をどうしますか？（UC-07 嗜好ベクトル更新 + 北極星指標の週次集計を Unit-8 へ供給）

A) **日次 = 嗜好ベクトル更新、週次 = 指標集計を同一 Lambda の別ハンドラに分離**（日次 cron で PreferenceVector 更新、週次 cron で WeeklyReports 生成。集計は CloudWatch Metrics + DynamoDB から、services.md 北極星指標経路）— 責務明確、推奨
B) 日次バッチに週次集計も含める（曜日判定で週次処理を実行）
C) 週次集計は Unit-8 Dame Report が自前で実装（Unit-2 は嗜好ベクトル更新のみ）
X) Other（[Answer]: の後に記述）

[Answer]: A

### Question 6
M-02 HomeScreen の **サブダッシュボード（逆家計簿）の構成要素**をどこまで Unit-2 で持ちますか？（UC-06 逆家計簿サブ、本格表示は Unit-8）

A) **Home は概況スナップショットのみ**（候補件数 / カート監視リスト件数 / カレンダー連動カード / 委ね Lv / 今月の使える額残り。詳細な Before-After やポートフォリオは Unit-8 DameReportScreen へ遷移）— 責務分離、推奨
B) Home に逆家計簿の詳細（Before-After 指標含む）も実装
C) Home は最小（hero + ナビ）のみ、サブダッシュボードは全て Unit-8
X) Other（[Answer]: の後に記述）

[Answer]: A

---

## 2. 実行ステップ（チェックボックス）

### Part 1: 計画 + 質問
- [x] Unit-2 のコンテキスト分析（unit-of-work / stories US-AUTH / component-methods / Unit-1 成果物）
- [x] Functional Design Plan の作成（本ファイル）
- [x] ユーザーが Q1〜Q6 に回答（全問 A）
- [x] 回答の分析・曖昧さ検出（矛盾なし）

### Part 2: 機能設計成果物の生成（承認後）
- [x] `aidlc-docs/construction/unit-2-auth-profile/functional-design/domain-entities.md`（UserProfile / PreferenceVector / SafeguardState / Achievement 等）
- [x] `business-logic-model.md`（オンボ段階保存 / 嗜好ベクトル更新 / 負債セーフガード連動 / Lv・称号判定 / 週次集計）
- [x] `business-rules.md`（オンボ項目・90秒・再開 / 負債35%・72hクーリングオフ / MFA・ロックアウト / Lv 計算）
- [x] `frontend-components.md`（M-02 HomeScreen / M-11 AuthModule のオンボ 5 画面・MFA 画面）
- [x] 自己レビュー（診断エラー 0、Unit-1 ロジック再利用の整合確認）+ 完了メッセージ + 承認ゲート

---

## 3. Extension 適合の予定

| Extension | 本ステージでの扱い |
|---|---|
| SECURITY-12（認証 / MFA） | M-11 の MFA フロー、72h リセット、5 回失敗ロックを business-rules に明記 |
| SECURITY-08（認可） | Unit-1 require_owner を全 users/{userId} エンドポイントに適用 |
| SECURITY-14（アラート） | 認証失敗 Alarm（Unit-1 SNS トピック利用） |
| PBT-04（idempotency） | オンボ段階保存の冪等性 / Post Confirmation 初期化の冪等性 |
| §9 NG-4 / NG-8 | 負債セーフガード（US-AUTH-03）/ Associates 開示（US-AUTH-01 AC-4） |
