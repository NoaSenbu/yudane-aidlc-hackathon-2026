# Unit-1 Platform — OpenAPI 第 1 版スケルトン作成計画（Q9 = B 反映）

> Q9 = B 確定（全 7 UC を第 1 版に含める）に基づき、Member A が Day 4 までに作成する OpenAPI 3.1 スケルトンの詳細計画。
>
> 参照: [api-contracts.md §1.1](../../../../.kiro/steering/api-contracts.md#11-第-1-版作成主体c-3--a-確定) / [stories.md](../../../inception/user-stories/stories.md) / [components.md](../../../inception/application-design/components.md)

---

## 1. 目的とスコープ

### 1.1 凍結期限

**Day 3 終業時（5/29 木曜日 18:00 JST）**

ハッカソン期間（5/27 着手）で計算すると、本来の Day 4 = 5/30 は **予選デモ当日**で凍結作業に充てられない。そのため凍結を **1 日前倒しして Day 3 = 5/29 終業時** をターゲットとする。Day 4 = 5/30 朝は予選デモ準備に専念し、軽微な修正のみ対応する。

**スケジュールサマリ**:

| 日 | 主な作業 |
|---|---|
| Day 1（5/27 火） | エントリポイント + 共通スキーマ + auth + telemetry |
| Day 2（5/28 水） | debate + reel + 主要ドメインスキーマ + Prism 起動確認 |
| Day 3（5/29 木）| cart + calendar + safeguard + report + examples + 型生成 + **凍結 PR merge（終業時）** |
| Day 4（5/30 金、予選デモ当日） | 予選デモ準備、軽微な修正のみ |

### 1.2 スコープ（Q9 = B）

第 1 版に含める **8 paths ファイル**:

1. `paths/auth.yaml` — UC-05/06/07/08 の前提
2. `paths/debate.yaml` — UC-01
3. `paths/reel.yaml` — UC-02
4. `paths/cart.yaml` — UC-03
5. `paths/calendar.yaml` — UC-04（Q9 = B で前倒し含める）
6. `paths/safeguard.yaml` — UC-08
7. `paths/report.yaml` — UC-06/07（Q9 = B で前倒し含める）
8. `paths/telemetry.yaml` — 横断

---

## 2. エンドポイント網羅一覧

### 2.1 Auth（`paths/auth.yaml`、Unit-2 owner）

| Method | Path | 概要 | Story |
|---|---|---|---|
| POST | /v1/auth/sign-up | サインアップ | US-AUTH-01 |
| POST | /v1/auth/confirm-sign-up | サインアップ確認（コード） | US-AUTH-01 |
| POST | /v1/auth/sign-in | サインイン | US-AUTH-02 |
| POST | /v1/auth/confirm-mfa | TOTP MFA 確認 | US-AUTH-02 |
| POST | /v1/auth/refresh-token | トークン更新 | 横断 |
| POST | /v1/auth/sign-out | サインアウト | 横断 |
| GET | /v1/auth/recovery-code | Recovery Code 取得（1 回限り、Cognito 標準外、B-01 で実装） | US-AUTH-02 |

### 2.2 User Profile（`paths/auth.yaml` に統合、Unit-2 owner）

> **配置ルール（M6 確定、2026-05-27）**: User Profile 5 エンドポイントは `paths/auth.yaml` に統合する（Auth 7 + User 5 = 12 エンドポイント）。理由は (1) 認証と密接に関連し、Cognito User Pool 配下のリソースと自然に対応、(2) Unit-2 Auth & Profile owner が一括で管理しやすい、(3) paths ファイル数を 8 に維持して §1.2 と整合。`users.yaml` 分離は不採用。

| Method | Path | 概要 | Story |
|---|---|---|---|
| POST | /v1/users/{userId}/profile | オンボーディングアンケート保存 | US-AUTH-03 |
| GET | /v1/users/{userId} | プロファイル取得 | 横断 |
| PATCH | /v1/users/{userId} | プロファイル更新 | US-SAFE-04 |
| DELETE | /v1/users/{userId} | アカウント削除 | US-SAFE-04（FR-AUTH-06）|
| GET | /v1/users/{userId}/preference | 嗜好ベクトル取得（B-02 が内部呼び出し） | 横断 |

### 2.3 Debate（`paths/debate.yaml`、Unit-3 owner）

| Method | Path | 概要 | Story |
|---|---|---|---|
| POST | /v1/debate-sessions | 論破セッション開始（SSE ストリーミング） | US-01-01 |
| POST | /v1/debate-sessions/{sessionId}/agree | 論破成功（Amazon 遷移へ） | US-01-01 |
| POST | /v1/debate-sessions/{sessionId}/refuse | 論破拒否（次のターン） | US-01-02 |
| GET | /v1/debate-sessions/{sessionId} | セッション状態取得 | US-01-04 |
| GET | /v1/debate-sessions | セッション一覧（最近の論破履歴） | US-01-05 |

### 2.4 Reel（`paths/reel.yaml`、Unit-4 owner）

| Method | Path | 概要 | Story |
|---|---|---|---|
| GET | /v1/reel | リール商品取得（ページング） | US-02-01 |
| POST | /v1/reel/impressions | スワイプ / 視聴ログ記録 | US-02-03 / US-02-04（左右スワイプログ） |
| POST | /v1/amazon-transitions | 「🛍 Amazon で買う」記録 | US-02-02（ダブルタップ Amazon 遷移）/ US-03-04（Special Link Deep Link） |

### 2.5 Cart Intercept（`paths/cart.yaml`、Unit-5 owner）

| Method | Path | 概要 | Story |
|---|---|---|---|
| POST | /v1/cart-watch-items | Share Extension 受信 → 監視登録 | US-03-01 |
| GET | /v1/cart-watch-items | 監視リスト一覧（ホーム画面の表示用） | 横断（M-02 HomeScreen から、US-03-01 派生） |
| DELETE | /v1/cart-watch-items/{asin} | 監視解除（自発削除） | 横断（US-02-04 右スワイプ撤回 / 自発操作） |
| POST | /v1/cart-watch-items/{asin}/dismiss | 通知から「やめる」（追撃キャンセル） | US-03-02（30m/6h/24h 追撃通知のキャンセル） |

### 2.6 Calendar（`paths/calendar.yaml`、Unit-6 owner、Q9 = B で前倒し）

| Method | Path | 概要 | Story |
|---|---|---|---|
| POST | /v1/calendar-categories | 端末ローカル分類済みカテゴリ送信（FR-CAL-05） | US-CAL-01 |
| GET | /v1/calendar/upcoming-recommendations | 予定駆動の商品推薦 | US-CAL-02 |
| DELETE | /v1/calendar-categories | カレンダーデータ全削除 | US-CAL-03 |

### 2.7 Safeguard（`paths/safeguard.yaml`、Unit-7 owner）

| Method | Path | 概要 | Story |
|---|---|---|---|
| GET | /v1/safeguard/status | 月間上限 / 冷却 / 静かな週の状態 | US-SAFE-01 |
| PATCH | /v1/safeguard/monthly-limit | 月間上限の更新 | US-SAFE-01 |
| POST | /v1/safeguard/cooldown | 冷却モードを ON | US-SAFE-02 |
| POST | /v1/safeguard/quiet-week | 静かな週を ON | US-SAFE-03 |
| GET | /v1/safeguard/data-export | データエクスポート（JSON） | US-SAFE-04 |

### 2.8 Dame Report（`paths/report.yaml`、Unit-8 owner、Q9 = B で前倒し）

| Method | Path | 概要 | Story |
|---|---|---|---|
| GET | /v1/reports/weekly | 週次レポート取得 | US-REP-01 |
| GET | /v1/reports/portfolio | ダメ化ポートフォリオ取得 | US-REP-02 |
| PATCH | /v1/reports/portfolio | タグ雲編集 | US-REP-03 |

### 2.9 Telemetry（`paths/telemetry.yaml`、横断）

| Method | Path | 概要 | Story |
|---|---|---|---|
| POST | /v1/telemetry | バッチイベント受信（Idempotency-Key 必須） | 全 Unit |

### エンドポイント総数

- Auth + User: 12（Auth 7 + User 5、Recovery Code 追加）
- Debate: 5
- Reel: 3
- Cart: 4
- Calendar: 3
- Safeguard: 5
- Report: 3
- Telemetry: 1

**合計: 36 エンドポイント**

---

## 3. components/schemas/ の整備（Member A 担当）

第 1 版で必須となる共通スキーマ:

### 3.1 共通

| Schema | 説明 |
|---|---|
| `ProblemDetails` | RFC 7807 エラーレスポンス |
| `TimeRange` | `{ from, to }` の ISO 8601 期間 |
| `Pagination` | `{ cursor, limit, total }` |

### 3.2 ドメインモデル

| Schema | Owner | 説明 |
|---|---|---|
| `User` | Unit-2 | 基本プロファイル |
| `UserProfile` | Unit-2 | 拡張プロファイル（オンボ アンケート結果） |
| `PreferenceVector` | Unit-2 | 嗜好ベクトル |
| `DebateSession` | Unit-3 | 論破セッション |
| `DebateMessage` | Unit-3 | 論破ターン |
| `DebateToken` | Unit-3 | SSE トークン |
| `ReelItem` | Unit-4 | リール商品カード |
| `ReelPage` | Unit-4 | ページング込みリール |
| `ProductMeta` | Unit-4 / Unit-5 | 商品メタデータ |
| `SpecialLink` | Unit-4 | Amazon Special Link |
| `CartWatchItem` | Unit-5 | カート監視アイテム |
| `CalendarEvent` | Unit-6 | カレンダーカテゴリ（FR-CAL-05 準拠） |
| `ProductCategoryPrediction` | Unit-6 | 予定 → 商品カテゴリ予測 |
| `SafeguardState` | Unit-7 | Safeguard 状態 |
| `MonthlyLimit` | Unit-7 | 月間上限 |
| `WeeklyReport` | Unit-8 | 週次レポート |
| `DamePortfolio` | Unit-8 | ダメ化ポートフォリオ |
| `Achievement` | Unit-8 | 称号 / Lv |
| `TelemetryEvent` | Unit-1 | テレメトリイベント（[api-contracts.md §12](../../../../.kiro/steering/api-contracts.md)）|
| `IdempotencyKey` | Unit-1 | 冪等キー（リクエストヘッダ） |

合計 **約 25 schemas**。

### 3.3 共通レスポンス（`components/responses/`）

| Response | 用途 |
|---|---|
| `BadRequest` | 400 |
| `Unauthorized` | 401 |
| `Forbidden` | 403（Safeguard ブロック等） |
| `NotFound` | 404 |
| `Conflict` | 409（クールダウン / 冪等キー不一致） |
| `TooManyRequests` | 429 |
| `InternalServerError` | 500 |

---

## 4. Member A の Day 1〜Day 3 タスク分解（Q9 = B の前倒し作業含む、凍結 = Day 3 終業時）

### Day 1（5/27 火）

- [ ] `shared/schema/openapi.yaml` のエントリポイント作成
- [ ] `components/schemas/` の共通スキーマ（ProblemDetails / TimeRange / Pagination）
- [ ] `components/responses/` の共通エラーレスポンス
- [ ] `paths/auth.yaml` スケルトン（**12 エンドポイント** = Auth 7 + User Profile 5、M6 確定で統合）
- [ ] `paths/telemetry.yaml` スケルトン（1 エンドポイント）

工数目安: 4h

### Day 2（5/28 水）

- [ ] `paths/debate.yaml` スケルトン（5 エンドポイント）
- [ ] `paths/reel.yaml` スケルトン（3 エンドポイント）
- [ ] ドメインスキーマ作成（User / UserProfile / DebateSession / ReelItem 等 8 個）
- [ ] Prism モックサーバーの起動確認（`npm run mock:api`）

工数目安: 4h

### Day 3（5/29 木、凍結日）

#### 午前

- [ ] `paths/cart.yaml` スケルトン（4 エンドポイント）
- [ ] **`paths/calendar.yaml` スケルトン（3 エンドポイント、Q9 = B 前倒し）**
- [ ] `paths/safeguard.yaml` スケルトン（5 エンドポイント）
- [ ] **`paths/report.yaml` スケルトン（3 エンドポイント、Q9 = B 前倒し）**
- [ ] ドメインスキーマ追加（CartWatchItem / CalendarEvent / SafeguardState / WeeklyReport 等 12 個）

#### 午後（凍結作業）

- [ ] 全エンドポイントの最低限の `examples` 追加（Prism がモックレスポンスを返せるように）
- [ ] `npm run schema:gen:ts` で TypeScript 型生成 → commit
- [ ] `poetry run python scripts/gen_models.py` で Python 型生成 → commit
- [ ] OpenAPI 第 1 版 PR を `develop` に merge → **凍結宣言**
- [ ] Slack `#yudane-dev` で Member B/C/D に凍結通知

工数目安: 6-8h（Q9 = B 前倒しで +2h、午前 4h + 午後 2-4h）

### Day 4（5/30 金、予選デモ当日）

- 予選デモ準備に専念
- 凍結後の軽微な修正があれば対応（破壊的変更禁止、追加 PR で対応）
- Member B/C/D は Day 4 から凍結済み API 契約に基づいて実装着手可能

### 累積工数

- C 採用時（Calendar / Report 後付け）: 12-14h
- **B 採用時（Q9 = B、Calendar / Report 含む）: 14-16h**

→ Member A の Day 1-3 で完走可能な範囲（Day 3 終業時に間に合う）。Day 4 は予選デモに集中。

---

## 5. 凍結後の変更プロセス

[git-ops.md](../../../../.kiro/steering/git-ops.md) §API 契約変更時の追加手順 に従う:

1. 契約変更 PR を `feature/openapi-<change>` で先行 merge
2. 型生成ファイル（`shared/schema/types/api.ts` + `backend/src/common/models/api.py`）を同 PR で再生成 + commit
3. 実装 PR を `feature/<unit>/...` で追従

破壊的変更（既存フィールド削除 / 必須フィールド追加 / 型変更）は **`/v2/...` を新設して共存**（[api-contracts.md §6](../../../../.kiro/steering/api-contracts.md)）。

---

## 6. Q9 = B 採用の影響まとめ

| 観点 | 影響 |
|---|---|
| **Member A の負荷** | C 採用比 +2h（Calendar 3 エンドポイント + Report 3 エンドポイント + 関連スキーマ 4 個） |
| **Day 4 凍結の余裕** | C 採用時 4h 余裕 → B 採用時 2h 余裕（タイトだが完走可能） |
| **Unit-6 / Unit-8 着手時の契約変更コスト** | C 採用比でゼロ（既に凍結済み） |
| **後半フェーズの開発速度** | 上昇（API 契約 PR の頻度低減） |
| **書類審査評価軸** | 既に書類審査（5/10）終了のため評価軸への直接影響なし |
| **予選評価軸（5/30）** | 「全 API 契約が凍結済み」を MVP デモ前にアピール可能 |
| **決勝評価軸（6/26）** | API 契約の安定性が完成度として加点要素 |

---

## 7. ハッカソン書類審査・予選評価軸へのインパクト

| 評価軸 | 本ドキュメントの貢献 |
|---|---|
| Unit 分解の適切さ | **強化**: 36 エンドポイントを Unit owner 別にマッピング、責任分界が明確 |
| ドキュメント品質 | **強化**: Day 1-4 のタスク分解で凍結期限の現実性が定量化された |
| AI-DLC プロセス（予選評価軸） | **強化**: Q9 = B 採用の影響を documented decision として残し、後半フェーズの開発速度向上の根拠を明示 |
