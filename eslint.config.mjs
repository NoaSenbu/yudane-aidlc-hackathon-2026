// @ts-check
import eslint from '@eslint/js';
import tseslint from 'typescript-eslint';
import importPlugin from 'eslint-plugin-import';
import simpleImportSort from 'eslint-plugin-simple-import-sort';
import prettier from 'eslint-config-prettier';

/**
 * モノレポ共通 ESLint 設定（Flat Config）。
 * 各ワークスペースはこの設定を継承し、必要に応じて拡張する。
 * 規約は .kiro/steering/tech-typescript.md §1 を参照。
 */
export default tseslint.config(
  eslint.configs.recommended,
  ...tseslint.configs.strict,
  {
    plugins: {
      import: importPlugin,
      'simple-import-sort': simpleImportSort,
    },
    rules: {
      'simple-import-sort/imports': 'error',
      'simple-import-sort/exports': 'error',
      'no-unused-vars': 'off',
      '@typescript-eslint/no-unused-vars': 'error',
      '@typescript-eslint/no-explicit-any': 'error',
    },
  },
  {
    // 生成ファイルは Lint 対象外（手動編集禁止のため）
    ignores: [
      '**/node_modules/**',
      '**/dist/**',
      '**/cdk.out/**',
      'shared/schema/types/**',
    ],
  },
  prettier,
);
