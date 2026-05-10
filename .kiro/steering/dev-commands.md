---
inclusion: manual
---

# 開発コマンド集

> このファイルは manual inclusion です。context を無駄に消費しないため常時注入はしませんが、always steering の [AGENTS.md](./AGENTS.md) §10 に記載された条件に AI が該当したら自発的に readFile で参照してください（ビルド / テスト / デプロイ / 環境構築コマンドを相談または実行する前）。

---

## 1. 現時点で使えるコマンド（Inception フェーズ完了時点）

モックアップ（静的 HTML、ビルド不要）:

```bash
open mockup/index.html                  # macOS
python3 -m http.server -d mockup 8080   # 静的サーバ → http://localhost:8080
```

## 2. Construction フェーズで想定するコマンド

実装着手後に各 Unit の Code Generation で確定させる。

### 2.1 モバイル（`mobile/`）

```bash
npm install
npm run lint
npm run test            # fast-check PBT を含む
npm run ios / android   # ローカル起動はユーザー手動
npm run mock:api        # Prism による OpenAPI モックサーバー
npm run test:contract   # MSW ハンドラの契約型検証
```

### 2.2 バックエンド（`backend/`、Poetry 前提）

```bash
poetry install
poetry run pytest       # Hypothesis PBT を含む
poetry run ruff check .
poetry run mypy --strict
poetry run schemathesis run shared/schema/openapi.yaml --base-url=http://localhost:8000
```

### 2.3 インフラ（`infra/`、CDK v2）

```bash
npm install
npx cdk synth
npx cdk diff
npx cdk deploy <stack-name>   # デプロイはユーザー承認必須
```

### 2.4 共有スキーマ（`shared/schema/`）

```bash
npm run schema:gen:ts                       # TypeScript 型生成（openapi-typescript）
poetry run python scripts/gen_models.py     # Python Pydantic モデル生成
```

## 3. 長時間実行コマンド（対話プロセスをブロックしないこと）

以下は AI エージェントによる直接実行を避け、ユーザー手動 or バックグラウンドで起動する:

- `npm run dev` / `npm run ios` / `npm run android`
- `webpack --watch` / `vite` 等のビルド watch
- `vitest --watch` / `pytest-watch` 等のテスト watch
- `npm run mock:api`（Prism モックサーバー、常駐）

AI からテストを単発実行したい場合は `--run` フラグ（vitest）や `--maxfail=1`（pytest）を付ける。

## 4. 破壊的コマンド（事前承認必須）

- `cdk destroy`（本番相当環境の破棄）
- `rm -rf` の広範なパス
- `git push --force` / `git reset --hard`（公開ブランチ）
- DB スキーマの `DROP TABLE` / `DROP INDEX`
- S3 バケット `aws s3 rb --force`

詳細は [git-ops.md](./git-ops.md) §破壊的操作 および [tech-cdk.md](./tech-cdk.md) §破壊的操作 を参照。

## 5. デプロイ手順（予選 / 決勝向け、将来更新）

Construction フェーズで各 Unit の Infrastructure Design / Build and Test が確定次第、本節を追記する。

現時点の方針メモ:

- dev 環境: `ap-northeast-1` 単一リージョン、`removalPolicy = DESTROY`
- prd 環境: `ap-northeast-1` 単一リージョン、`removalPolicy = RETAIN`、Cognito MFA 強制
- デプロイ順: `platform-stack` → `auth-stack` → コア 3 並行 → サポート 3 並行（Unit 依存 DAG に従う）
