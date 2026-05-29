# mobile

YUDANE モバイルアプリ（React Native 0.76+ / TypeScript 5.x / AWS SDK v3 / TanStack Query / Zustand）。

## Unit-1 Platform が提供するもの

- `src/features/platform/api-client/` — M-12 ApiClient（interceptor チェーン）
- `src/features/platform/telemetry/` — M-13 Telemetry（バッファ + 退避）
- `src/features/platform/app-shell/` — M-01 AppShell（ナビ殻 / Auth ゲート / deeplink）
- `src/app/providers/` — TanStack Query / Zustand / Telemetry / GlobalToast の状態管理土台

各 Unit は `src/features/<unit>/` に自身の画面・hooks を追加する。

## コマンド

```bash
npm install
npm run lint
npm run test          # vitest（fast-check PBT を含む）
npm run mock:api      # Prism による OpenAPI モックサーバー（ユーザー手動）
```
