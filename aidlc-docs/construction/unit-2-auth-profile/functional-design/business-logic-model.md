# Unit-2 Auth & Profile — Business Logic Model

> Unit-2 の業務ロジックを技術非依存で記述。Unit-1 の共通ロジック（SafeguardPolicy 等）は再利用する。
> 参照: [domain-entities.md](./domain-entities.md) / [business-rules.md](./business-rules.md) / [Unit-1 business-logic-model](../../unit-1-platform/functional-design/business-logic-model.md)
> 確定方針: Q1=A / Q2=A / Q3=A / Q4=A / Q5=A / Q6=A

---

## ALG-ONBOARD: オンボーディング段階保存（US-AUTH-01、Q1=A）

```
画面遷移（5 画面、各 < 18 秒で合計 90 秒、AC-1）:
  画面1 月間使える額 → 画面2 月間貯金額 → 画面3 好きなブランド(5+)
  → 画面4 NG カテゴリ → 画面5 負債フラグ

各画面 onNext():
  1. 当該項目を UserProfile に部分保存（PATCH /v1/users/{userId}/profile）
  2. User.onboardingStep を当該画面番号に更新
  3. 次画面へ

resume()（次回起動、AC-3 / PBT-04）:
  - User.onboardingStep を読み、その画面から再開（冪等: 同じ画面を再保存しても結果不変）

complete()（画面5 完了時、AC-2/AC-4）:
  1. 5 項目すべて非 null を検証
  2. monthlyLimitYen = monthlyDisposableYen * DEFAULT_MONTHLY_LIMIT_RATIO(0.7) を SafeguardState に確定
  3. hasDebt=true なら SafeguardState.flags.hasDebt=true + cooldownOn=true（ALG-DEBT へ）
  4. associatesDisclosureAcknowledged=true を要求（NG-8 開示、AC-4）
  5. User.profileCompleted=true
```

**不変条件**: 段階保存は冪等（同一画面の再保存で `onboardingStep` が後退しない）。

---

## ALG-INIT: Post Confirmation 初期化（US-AUTH、Q2=A）

B-01 AuthEdgeLambda の Cognito Post Confirmation トリガー。

```
on_post_confirmation(event):
  user_id = event.claims.sub
  # 冪等化: 既存チェック（再試行で二重作成しない、PBT-04）
  if not exists(User[user_id]):
      put User { id: user_id, email, createdAt: now, profileCompleted: false, onboardingStep: 0 }
      put PreferenceVector { userId, vector: [], labels: [], updatedAt: now }
      put SafeguardState {
        userId, monthlyLimitYen: 0,  # オンボ完了時に確定
        currentBudgetUsedYen: 0, transitionCountMonth: 0,
        flags: { cooldownOn: false, quietWeek: false, hasDebt: false },
        debtReleaseRequestedAt: null, monthAnchor: currentMonth()
      }
      put Achievement { userId, exp: 0, level: 1, titles: [], streak: 0 }
```

## ALG-CLAIM: Pre Token Generation（B-01）

```
on_pre_token_generation(event):
  # JWT カスタム claim に委ね Lv・称号・月間上限を付与（UI 即時表示用）
  achievement = get Achievement[sub]
  safeguard = get SafeguardState[sub]
  add_claims:
    yudane_level = achievement.level
    yudane_title = achievement.titles[-1] or "new"
    yudane_monthly_limit = safeguard.monthlyLimitYen
```

---

## ALG-DEBT: 負債フラグと初期セーフガード（US-AUTH-03、Q3=A）

```
申告時（オンボ画面5 で「負債あり」、AC-1/2/3）:
  SafeguardState.flags.hasDebt = true
  SafeguardState.flags.cooldownOn = true   # 初回から冷却 ON（AC-1）
  # 上限適用は Unit-1 SafeguardPolicy.decideAllow が自動で 0.35 比率に半減（AC-2）
  # → Unit-2 は has_debt 保存のみ、判定は再実装しない

遷移可否（リール・論破起動時、AC-3）:
  decision = SafeguardPolicy.decideAllow(toSafeguardInput(state))  # Unit-1 を利用
  if decision.decision == 'block':
      遷移ボタンを 24h 非活性 + Safeguard 画面へ誘導

解除（手動、AC-4、72h クーリングオフ）:
  requestDebtRelease():
    state.debtReleaseRequestedAt = now
    記録: 解除理由ログ（AuditLogger）
  # 72h 経過後にバッチ or 次回アクセスで:
  if now - debtReleaseRequestedAt >= 72h:
      state.flags.hasDebt = false
      state.flags.cooldownOn = false
```

**不変条件**: 負債解除は必ず 72h 経過後（即時解除は不可）。`debtReleaseRequestedAt` から 72h 未満での解除リクエストは no-op。

---

## ALG-MFA: MFA フローと認証（US-AUTH-02、Q4=A）

M-11 AuthModule（Amplify Auth v6 ラッパー）。Unit-1 `AuthTokenProvider` を実装する。

```
signUp(email, password) → confirmSignUp(email, code)
signIn(email, password):
  → MFA REQUIRED なら challenge 返却 → confirmMfa(session, totp) → TokenSet
setupMfa():
  → Authenticator 用 QR（TOTP secret）表示 → 6 桁コードで有効化（AC-1）
refresh(): TokenSet 更新（ApiClient の 401 single-shot refresh から呼ばれる）
getCurrentUser(): UserDto | null

# AuthTokenProvider 実装（Unit-1 ApiClient と直結）
getAccessToken() = 現在の TokenSet.accessToken
refresh() = 上記 refresh の成否を boolean で返す
onAuthExpired() = AppShell.onAuthExpired（Unit-1）へ委譲

MFA リセット（AC-3）: メール確認 + 72h 冷却後にリセット可能
ロックアウト（AC-4）: 5 回失敗で 15 分ロック（Cognito + CloudWatch Alarm、SECURITY-14）
```

---

## ALG-LEVEL: Lv / 称号判定（UC-05）

```
レベル算出: level = floor(sqrt(exp / 100)) + 1  （単調増加、business-rules LV-*）
称号付与:
  - level 到達ベース（Lv5 → 「本日の湯水使い」等）
  - streak ベース（7 日連続 → 「静かな信徒」）
  - 累積行動ベース（論破成約 100 回 → 「伝道師」）
EXP 加算は Unit-4/B-13 の Amazon 遷移時に発生（Unit-2 は判定・保存）
```

---

## ALG-PREF: 嗜好ベクトル日次更新（UC-07、B-08 日次、Q5=A）

```
update_preference(user_id) [日次 cron]:
  signals = 集計:
    - Amazon 遷移履歴（カテゴリ分布）
    - スキップ履歴
    - 論破成功パターン
    - カレンダーパターン（Unit-6 由来）
  new_vector = embed + 重み付き更新
  put PreferenceVector { vector: new_vector, labels: deriveLabels(...), updatedAt: now }
```

## ALG-WEEKLY: 週次指標集計（UC-06/07、B-08 週次、Q5=A）

```
generate_weekly_report(user_id) [週次 cron、日曜 22 時]:
  metrics = CloudWatch Metrics + DynamoDB から集計:
    - debateToAmazonRate（北極星指標、§6.1）
    - cartInterceptConversionRate
    - lateNightUsageRatio
    - monthlySpendYen
  put WeeklyReport { weekAnchor, metrics, generatedAt }
  → SVC-07 が report-weekly 通知を配信、Unit-8 が GET /v1/report で表示
```

**Q5=A の責務分離**: 日次ハンドラ（嗜好ベクトル）と週次ハンドラ（指標集計）を同一 Lambda の別エントリに分離。曜日判定の混在を避ける。

---

## ALG-HOME: HomeScreen スナップショット（UC-06、Q6=A）

```
useHomeSnapshot() → HomeSnapshotDto:
  - 候補件数（Unit-4 リール）
  - カート監視リスト件数（Unit-5）
  - カレンダー連動カード（Unit-6）
  - 委ね Lv（Achievement）
  - 今月の使える額残り（SafeguardState.remaining、SafeguardPolicy 経由）
# 詳細な Before-After / ポートフォリオは Unit-8 DameReportScreen へ遷移（Q6=A）
```

---

## アルゴリズム一覧

| ID | ロジック | 主担当 | 検証方針 |
|---|---|---|---|
| ALG-ONBOARD | オンボ段階保存 | M-02 / API | idempotency PBT-04 |
| ALG-INIT | Post Confirmation 初期化 | B-01 | idempotency（二重作成なし）|
| ALG-DEBT | 負債セーフガード連動 | B-01 / S-03 再利用 | 72h クーリングオフ不変条件 |
| ALG-MFA | MFA / 認証 | M-11 | 例外系（lockout / reset）|
| ALG-LEVEL | Lv / 称号判定 | B-08 | 単調増加 invariant |
| ALG-PREF | 嗜好ベクトル日次 | B-08 | — |
| ALG-WEEKLY | 週次集計 | B-08 | — |
| ALG-HOME | Home スナップショット | M-02 | — |
