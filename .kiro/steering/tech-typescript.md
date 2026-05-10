---
inclusion: fileMatch
fileMatchPattern: '*.ts*'
---

# TypeScript / React Native 規則

> `.ts` / `.tsx` ファイルを編集しているときに自動で適用される steering。
> 横断的なプロダクト規則は [AGENTS.md](./AGENTS.md)、プロジェクト構造は [structure.md](./structure.md)、API 契約は [api-contracts.md](./api-contracts.md)、CDK は [tech-cdk.md](./tech-cdk.md) を参照。

---

## 1. Lint・フォーマッタ

| 項目 | 採用 | 備考 |
|---|---|---|
| ESLint ベース設定 | `@typescript-eslint/recommended`（strict） | `tseslint.configs.strict` を利用 |
| React Native 追加ルール | `eslint-plugin-react` + `eslint-plugin-react-native` | Hooks ルール `eslint-plugin-react-hooks` 必須 |
| Import 並び替え | `eslint-plugin-import` + `eslint-plugin-simple-import-sort` | 自動整列を CI で強制 |
| Prettier | 2 spaces / single quote / trailing comma = `all` / semi = true / printWidth = 100 | ESLint と `eslint-config-prettier` で競合回避 |
| Unused import / unused var | **エラー扱い**（警告ではない） | `no-unused-vars` は ESLint で error |

具体的なツール設定値（`.eslintrc.cjs` / `tsconfig.json` / `.prettierrc`）は各プロジェクトルートに配置する。本節では **採用方針** と **必須項目** のみ定義。

## 2. 型安全性

- `tsconfig.json` の `"strict": true` 必須
- 追加で有効化: `noUncheckedIndexedAccess` / `exactOptionalPropertyTypes` / `noImplicitOverride` / `noFallthroughCasesInSwitch`
- `any` / `@ts-ignore` / `@ts-nocheck` は原則禁止。やむを得ず使う場合は PR description で理由を明記
- 型アサーション（`as`）よりも型ガード関数を優先

## 3. React Native 固有

- コンポーネントは **関数コンポーネント + Hooks** のみ。クラスコンポーネント禁止
- Side effect は `useEffect` / `useLayoutEffect` 以外での実行禁止
- Style は `StyleSheet.create` または `NativeWind`。インラインスタイルは単純な一時用途のみ

## 4. 命名規則

### 4.1 ファイル

| 対象 | 規則 | 例 |
|---|---|---|
| TypeScript ファイル | kebab-case | `debate-session.ts`、`user-profile.tsx` |
| ディレクトリ | kebab-case | `debate-session/`、`user-profile/` |

### 4.2 識別子

| 対象 | 規則 | 例 |
|---|---|---|
| クラス / 型 | PascalCase | `class DebateSession`、`type UserProfile` |
| 関数 / 変数 | camelCase | `function startDebate()`、`const maxTokens = 512` |
| 定数（モジュール即値） | UPPER_SNAKE_CASE | `const MAX_DEBATE_TURNS = 3` |
| enum | PascalCase、メンバーは UPPER_SNAKE | `enum DebateOutcome { AGREED, REJECTED }` |

### 4.3 ドメイン ID（共通）

- Lambda コンポーネント: `B-XX`（Backend）/ `M-XX`（Mobile）/ `S-XX`（Shared）
- FR / NFR: `FR-<領域>-<番号>`（例: `FR-DEBATE-01`）
- ストーリー: `US-<領域>-<番号>`（例: `US-01-01`）

## 5. Import 順序

グループは上から順に配置、グループ間は空行 1 行:

1. External packages（`react`, `react-native`, `@tanstack/react-query` 等）
2. Internal alias（`@/features/debate/...`, `@/shared/...`）
3. Relative（`./components`, `../hooks`）
4. Side-effect only import（`import './styles.css'`）

`eslint-plugin-simple-import-sort` で自動化。Circular import は CI で madge 検知。

## 6. ファイルサイズ・責務

- 1 ファイル 300 行以内（例外: UI Component で Story ごとに分かれるもの）
- 1 ファイル 1 関心事。雑多な `utils.ts` は禁止。関心事ごとにディレクトリを分け `index.ts` でエクスポート制御
- 未使用 import / 変数 / 関数は ESLint で **エラー扱い**
- コメントアウトされた残骸コードは commit に含めない（Git 履歴と PR description で残す）

## 7. コメント方針

- コメントは「なぜ」を書く。「何を」はコード自体で明らかに
- TODO にはチケット番号や期限を必須: `// TODO(#123): 2026-06 までに B-03 と整合`
- コードを逐語的に訳したコメント禁止（`i++ // i を 1 増やす`）

## 8. JSDoc（公開 API 必須、日本語）

```typescript
/**
 * 論破セッションを開始する
 *
 * Bedrock Claude Haiku 4.5 にストリーミングで接続し、ユーザーの嗜好ベクトルと
 * コンテキスト信号（カレンダー予定・時刻・直近購入履歴）をプロンプトに組み立てる。
 *
 * @param userId - 論破対象のユーザー ID
 * @param productAsin - 対象商品の ASIN
 * @param context - プロンプト組立用のコンテキスト
 * @returns ストリーミングレスポンスの AsyncIterable
 * @throws {DebateCooldownError} クールダウン中（FR-DEBATE-05）
 */
export async function* startDebate(...) { }
```

## 9. 状態管理・非同期

- サーバー状態: **TanStack Query**（キャッシュ・再検証は Query に委ねる）
- クライアント状態: **Zustand**（最小限、グローバル化しすぎない）
- Bedrock ストリーミング等は AsyncIterable / ReadableStream を優先。Promise でまとめ切らない

## 10. テスト（TypeScript 側）

| レイヤ | ツール | 配置 |
|---|---|---|
| Unit Test | `vitest` | `**/*.test.ts` / `**/*.test.tsx` |
| Property-Based Test | `fast-check` | Unit Test と同居、プロパティ関数で区別 |
| Integration Test | `vitest` + MSW | `mobile/tests/integration/` |
| Contract Test | MSW ハンドラの契約型検証 | `npm run test:contract` |
| E2E Test | `playwright`（Web 経由）または手動 | `e2e/` |

**カバレッジ目標**:

- Unit Test: Line **80%+** / Branch **70%+**（生成ファイル除外）
- PBT: PBT-01〜10 各カテゴリに対し 1 つ以上のプロパティ実装
- Integration Test: 主要シーケンス 100% カバー（詳細は [api-contracts.md](./api-contracts.md) §Integration Test の IT-01〜07）

CI で自動計測。未達 PR はマージ不可。

## 11. セキュリティ（SECURITY Extension 抜粋）

- ユーザー入力は **Zod で検証必須**。無検証の `JSON.parse(request.body)` 禁止
- `console.log` での機密情報出力禁止。構造化ロガー経由
- 認証情報はコード直書き禁止（環境変数 / Secrets Manager）
- 詳細は [AGENTS.md](./AGENTS.md) §セキュリティ を参照

## 12. 採用しないもの（TypeScript 側）

- AWS Amplify Gen 2 の Data / Functions / CLI（Auth モジュールのみ採用）
- `amazon-cognito-identity-js`（npm 公式で非推奨）
- Flutter / Dart（v0.3 以降 React Native に変更）
