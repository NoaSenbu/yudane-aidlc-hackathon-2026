# Unit-2 Auth & Profile — Business Rules

> Unit-2 のルール・定数・制約。Unit-1 の定数（SafeguardPolicy 等）は再掲せず参照する。
> 参照: [domain-entities.md](./domain-entities.md) / [business-logic-model.md](./business-logic-model.md) / [Unit-1 business-rules](../../unit-1-platform/functional-design/business-rules.md)
> 確定方針: Q1=A / Q2=A / Q3=A / Q4=A / Q5=A / Q6=A

---

## 1. オンボーディング（US-AUTH-01）

| ID | ルール |
|---|---|
| ONB-01 | オンボは 5 画面（使える額 / 貯金額 / 好きなブランド / NG カテゴリ / 負債フラグ）、合計 90 秒以内で完了可能（AC-1） |
| ONB-02 | 各画面で部分保存し `User.onboardingStep` を更新。途中離脱は同 step から再開（AC-3、段階保存 Q1=A） |
| ONB-03 | 段階保存は冪等（同一画面の再保存で onboardingStep が後退しない、PBT-04） |
| ONB-04 | 好きなブランドは 5 つ以上を推奨（必須は 1 つ以上）、重複不可 |
| ONB-05 | 完了条件: 5 項目すべて非 null + Associates 開示確認済み → `profileCompleted=true` |
| ONB-06 | 完了時に `monthlyLimitYen = monthlyDisposableYen * 0.7`（DEFAULT 比率、Unit-1 定数）を SafeguardState に確定 |
| ONB-07 | Associates 開示文言を設定画面の常時表示領域に格納（FR-PROFILE-04 / NG-8、AC-4） |

---

## 2. 初期化（US-AUTH、Q2=A）

| ID | ルール |
|---|---|
| INIT-01 | Post Confirmation で User / PreferenceVector(empty) / SafeguardState / Achievement を一括初期化 |
| INIT-02 | 初期化は冪等（既存チェックで二重作成しない、再試行耐性） |
| INIT-03 | SafeguardState.monthlyLimitYen はオンボ完了時に確定（初期化時は 0） |
| INIT-04 | Pre Token Generation で yudane_level / yudane_title / yudane_monthly_limit を JWT claim に付与 |

---

## 3. 負債セーフガード（US-AUTH-03、Q3=A）

| ID | ルール |
|---|---|
| DEBT-01 | 「負債あり」申告で `flags.hasDebt=true` + `flags.cooldownOn=true`（初回から冷却、AC-1） |
| DEBT-02 | 上限適用は Unit-1 `SafeguardPolicy.decideAllow` が自動で 0.35 比率に半減（AC-2、再実装しない） |
| DEBT-03 | 負債フラグ ON 中はリール・論破の遷移ボタンを 24h 非活性 + Safeguard 画面誘導（AC-3） |
| DEBT-04 | 負債解除は手動リクエスト + 確認ダイアログ + 解除理由ログ（AuditLogger） |
| DEBT-05 | 負債解除は `debtReleaseRequestedAt` から **72h クーリングオフ後** に有効化（AC-4）。72h 未満の解除は no-op |

---

## 4. MFA / 認証（US-AUTH-02、SECURITY-12/14）

| ID | ルール |
|---|---|
| MFA-01 | TOTP MFA は REQUIRED（platform-stack の User Pool で設定済み） |
| MFA-02 | サインアップ後初回ログインで MFA セットアップ（QR + 6 桁）（AC-1） |
| MFA-03 | 次回以降はパスワード + 6 桁 TOTP の 2 段認証（AC-2） |
| MFA-04 | MFA リセットはメール確認 + 72h 冷却後（アカウント乗っ取り耐性、AC-3） |
| MFA-05 | 認証失敗 5 回で 15 分ロックアウト + CloudWatch Alarm 発火（AC-4、SECURITY-14） |
| MFA-06 | AuthModule は Unit-1 `AuthTokenProvider`（getAccessToken/refresh/onAuthExpired）を実装し ApiClient と直結 |
| MFA-07 | トークンは Amplify Auth v6 が管理（`amazon-cognito-identity-js` 不採用） |

---

## 5. Lv / 称号（UC-05）

| ID | ルール |
|---|---|
| LV-01 | `level = floor(sqrt(exp / 100)) + 1`（単調増加） |
| LV-02 | EXP 加算は Unit-4/B-13 の Amazon 遷移時に発生（Unit-2 は判定・保存） |
| LV-03 | 称号は level 到達 / streak / 累積行動で付与（重複付与しない） |
| LV-04 | exp は減少しない（単調増加 invariant） |

---

## 6. 週次集計 / Home（UC-06/07、Q5=A / Q6=A）

| ID | ルール |
|---|---|
| RPT-01 | 日次ハンドラ（嗜好ベクトル）と週次ハンドラ（指標集計）を分離（Q5=A） |
| RPT-02 | 週次集計は日曜 22 時 cron で WeeklyReports に出力（北極星指標含む、§6.1） |
| RPT-03 | Home スナップショットは概況のみ（候補件数 / 監視件数 / カレンダー / Lv / 残額）。詳細は Unit-8（Q6=A） |
| RPT-04 | 今月の使える額残りは Unit-1 SafeguardPolicy の remaining を経由 |

---

## 7. セキュリティ / 認可（Unit-1 継承）

| ID | ルール |
|---|---|
| SEC-01 | 全 `/v1/users/{userId}*` エンドポイントに Unit-1 `require_owner`（sub↔userId 照合、IDOR、SECURITY-08） |
| SEC-02 | email 等 PII は AuditLogger sanitizer で default-deny マスク（Unit-1 PII-01〜09） |
| SEC-03 | 認証失敗 Alarm は platform-stack の SNS トピックへ（Unit-1 観測基盤） |
