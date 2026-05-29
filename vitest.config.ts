import { defineConfig } from 'vitest/config';

/**
 * ルート vitest 設定。各ワークスペースの *.test.ts を対象に globals を有効化。
 * カバレッジ目標は tech-typescript.md §10 / NFR-COV を参照。
 */
export default defineConfig({
  test: {
    globals: true,
    environment: 'node',
    include: ['**/*.test.ts', '**/*.test.tsx'],
    exclude: ['**/node_modules/**', '**/dist/**', '**/cdk.out/**'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'lcov'],
      exclude: ['**/node_modules/**', 'shared/schema/types/**', '**/*.test.ts'],
    },
  },
  resolve: {
    alias: {
      '@yudane/schema': new URL('./shared/schema/types/api.ts', import.meta.url).pathname,
      '@yudane/safeguard-policy': new URL(
        './shared/safeguard-policy/src/index.ts',
        import.meta.url,
      ).pathname,
      '@yudane/telemetry-contracts': new URL(
        './shared/telemetry-contracts/src/index.ts',
        import.meta.url,
      ).pathname,
    },
  },
});
