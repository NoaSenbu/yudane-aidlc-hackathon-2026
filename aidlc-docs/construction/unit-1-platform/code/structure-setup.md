# Unit-1 Platform — Code Summary: Structure Setup（Step 1）

> モノレポ構造セットアップの生成サマリ。実コードはワークスペース直下。

## 生成ファイル（ワークスペース直下）

| ファイル | 役割 |
|---|---|
| `package.json` | モノレポルート（npm workspaces: shared/* + mobile + infra）、共通 scripts |
| `tsconfig.base.json` | TS strict + noUncheckedIndexedAccess / exactOptionalPropertyTypes 等（tech-typescript §2） |
| `eslint.config.mjs` | Flat Config、typescript-eslint strict + simple-import-sort + prettier 連携 |
| `.prettierrc` | 2 spaces / single quote / trailing comma all / printWidth 100 |
| `.editorconfig` | 文字コード・改行・インデント（py は 4） |
| `.gitignore`（更新） | Flutter 残骸を削除、TS/CDK/coverage を追記、生成型はコミット対象と明記 |
| `backend/pyproject.toml` | Poetry、ruff（py313, E/F/W/I/B/UP/S/ASYNC/RUF/D）+ mypy strict + pytest cov |
| `mobile/README.md` / `backend/README.md` / `infra/README.md` / `shared/README.md` | 各ディレクトリのスタブ |

## 規約準拠
- structure.md §今後追加される構成 のモノレポ配置に準拠（mobile / backend / infra / shared）
- 生成ファイル（`shared/schema/types/**`, `backend/src/common/models/api.py`）は Lint / 型チェック / カバレッジから除外
- アプリコードはワークスペース直下、ドキュメントは aidlc-docs/ のみ（混在なし）

## 次ステップ
Step 2: OpenAPI 骨格凍結 + 型生成（S-02 SchemaRegistry）
