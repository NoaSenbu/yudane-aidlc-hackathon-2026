# Unit-2 Auth & Profile — Frontend Components

> Unit-2 の Mobile コンポーネント（M-02 HomeScreen / M-11 AuthModule）の機能設計。
> Unit-1 の AppShell / ApiClient / 状態管理土台 / テーマトークンに乗る。
> 参照: [domain-entities.md](./domain-entities.md) / [business-logic-model.md](./business-logic-model.md) / [Unit-1 frontend-components](../../unit-1-platform/functional-design/frontend-components.md)
> 確定方針: Q1=A / Q4=A / Q6=A

---

## 1. コンポーネント階層（Unit-1 土台への追加）

```
<AppShell>（Unit-1）
├── <AuthGate>（Unit-1）
│   ├── 未認証 → <AuthFlow>（Unit-2 M-11）
│   │   ├── <SignUpScreen>
│   │   ├── <SignInScreen>
│   │   ├── <MfaSetupScreen>     # QR + 6 桁（US-AUTH-02）
│   │   └── <MfaChallengeScreen>
│   └── 認証済み + 未オンボ → <OnboardingFlow>（Unit-2、5 画面）
│       ├── <BudgetScreen>       # 画面1 月間使える額
│       ├── <SavingsScreen>      # 画面2 月間貯金額
│       ├── <BrandsScreen>       # 画面3 好きなブランド 5+
│       ├── <NgCategoriesScreen> # 画面4 NG カテゴリ
│       └── <DebtFlagScreen>     # 画面5 負債フラグ（US-AUTH-03）
└── <TabNavigator>（Unit-1）
    └── <HomeScreen>（Unit-2 M-02）  # タブの 1 つ
```

---

## 2. M-11 AuthModule（US-AUTH-02、Q4=A）

### 2.1 公開関数（component-methods.md + AuthTokenProvider 実装）

```ts
function signUp(email, password): Promise<void>;
function confirmSignUp(email, code): Promise<void>;
function signIn(email, password): Promise<TokenSet>;
function confirmMfa(session, totp): Promise<TokenSet>;
function setupMfa(): Promise<{ qrUri: string; secret: string }>;
function refresh(): Promise<TokenSet>;
function signOut(): Promise<void>;
function getCurrentUser(): Promise<UserDto | null>;
// Unit-1 AuthTokenProvider 実装（ApiClient へ注入）
const authTokenProvider: AuthTokenProvider = { getAccessToken, refresh, onAuthExpired };
```

### 2.2 オンボ前後の遷移
- サインアップ → MFA セットアップ（QR）→ 認証済み → `profileCompleted` 判定 → 未完了なら OnboardingFlow
- `data-testid`: `signin-submit-button` / `mfa-code-input` / `mfa-verify-button` 等（自動テスト用）

---

## 3. OnboardingFlow（US-AUTH-01、Q1=A 段階保存）

### 3.1 5 画面の Props / State

```ts
type OnboardingState = {
  step: number;                  // User.onboardingStep と同期
  draft: Partial<UserProfile>;   // 画面ごとの入力ドラフト（Zustand slice）
};
```

### 3.2 各画面の責務

| 画面 | 入力 | 保存タイミング | data-testid |
|---|---|---|---|
| BudgetScreen | 月間使える額（スライダー） | onNext で PATCH | `onboarding-budget-slider` |
| SavingsScreen | 月間貯金額 | onNext | `onboarding-savings-input` |
| BrandsScreen | 好きなブランド（チップ選択、5+） | onNext | `onboarding-brand-chip` |
| NgCategoriesScreen | NG カテゴリ（チェックリスト） | onNext | `onboarding-ngcat-checkbox` |
| DebtFlagScreen | 負債有無 + Associates 開示確認 | complete | `onboarding-debt-toggle` / `onboarding-complete-button` |

### 3.3 90 秒 / 途中再開
- 各画面 18 秒以内を目安、進捗バー表示（AC-1）
- 起動時 `onboardingStep` から再開（AC-3）。Zustand persist でドラフトも端末保持
- 完了時 Associates 開示文言の確認を必須化（NG-8、AC-4）

---

## 4. M-02 HomeScreen（UC-06、Q6=A）

### 4.1 useHomeSnapshot

```ts
function useHomeSnapshot(): UseQueryResult<HomeSnapshotDto>;
// HomeSnapshotDto: candidateCount / cartWatchCount / calendarCards / yudaneLevel / remainingBudgetYen
```

### 4.2 構成要素（概況のみ、Q6=A）

| 要素 | データ源 | 備考 |
|---|---|---|
| エージェント稼働 hero | candidateCount（Unit-4） | 「今日の候補 N 件」 |
| カート監視リスト | cartWatchCount（Unit-5） | 件数 + 直近数件 |
| カレンダー連動カード | calendarCards（Unit-6） | 「予定から先回り」 |
| 委ね Lv | yudaneLevel（Achievement） | JWT claim でも即時表示 |
| 今月の使える額残り | remainingBudgetYen（SafeguardPolicy） | Unit-1 decideAllow の remaining |

- 詳細な Before-After 指標・ダメ化ポートフォリオは Unit-8 DameReportScreen へ遷移（Q6=A）
- `data-testid`: `home-hero` / `home-cart-watch-list` / `home-calendar-card` / `home-level-badge`

---

## 5. A11y / トーン（Unit-1 継承）
- テーマトークン（Indigo / cold rose / cyan、WCAG AA、Unit-1 NFR-A11Y-01）を使用
- コピーは友達系タメ口（product.md トーン）。オンボは「真面目なアプリ」演出（US-AUTH-01 Day 1 シグナル）
- トーストは Unit-1 GlobalToast slice を使用
