# Unit-1 Platform — Code Summary: M-01 AppShell + 状態管理土台（Step 16-17）

## 生成ファイル

| ファイル | 役割 |
|---|---|
| `mobile/src/features/platform/app-shell/navigation.ts` | deeplink 解決（push/url）+ decideNavigation（純粋ロジック） |
| `mobile/src/features/platform/app-shell/auth-gate.ts` | Auth ゲート状態遷移 reducer（pending deeplink 保留） |
| `mobile/src/features/platform/app-shell/index.ts` | export 制御 |
| `mobile/src/app/theme/tokens.ts` | テーマトークン（WCAG AA 目標、NFR-A11Y-01） |
| `mobile/src/app/store/toast-slice.ts` | GlobalToast slice（Zustand 土台） |
| `mobile/src/app/providers/query-client.ts` | QueryClient（retry=false で ApiClient に一元化） |
| `*.test.ts`（navigation / auth-gate / toast-slice） | 状態遷移・deeplink ルーティングの単体テスト |

## ルール準拠
- frontend-components.md §2（ナビ状態遷移 / deeplink ルーティング / pending 保留）/ §5（状態管理土台）/ §7（A11y）
- React Native UI（React Navigation 結線）は実機統合時。Unit-1 はテスト可能な純粋ロジックを土台として提供
- retry=false で TanStack Query と ApiClient の二重リトライ防止（NFR-AVAIL Q6=B 整合）
- NFR-COV-06（80%/70%）

## 注記
React Navigation / RN コンポーネント本体（`data-testid` 付与含む）は RN ランタイム依存のため、骨格の純粋ロジック + 状態管理土台を本ステップで確定。画面 UI は各 Unit が feature 配下に追加。

## 次ステップ
Step 18-19: infra platform-stack + snapshot
