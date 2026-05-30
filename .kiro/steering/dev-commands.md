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
npx expo start          # Expo Dev Client 起動（Hot Reload、ローカル）
npx expo run:ios        # iOS Dev Client ビルド + 実機 / シミュレータ起動（ユーザー手動）
npx expo run:android    # Android Dev Client ビルド + 実機 / エミュレータ起動（ユーザー手動）
eas build --profile development --platform ios       # EAS Build で iOS Dev Client クラウドビルド
eas build --profile development --platform android   # EAS Build で Android Dev Client クラウドビルド
eas build --profile preview --platform all           # 予選デモ用 ad-hoc ビルド
eas build --profile production --platform all        # 決勝向け本番ビルド（Member A のみ実行可）
eas build --local --platform ios                     # ローカルビルド（EAS 月 30 ビルド超過時のフォールバック）
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

単一 AWS アカウント運用、env = `dev` / `prd`、個人 sandbox は CDK Context の `developer` キーで suffix を注入する（[tech-cdk.md §4.1](./tech-cdk.md) 参照）。

```bash
npm install
npx cdk synth
npx cdk diff
npx cdk deploy <unit>-dev-<initial>-stack -c developer=<initial>     # 個人 sandbox（例: -c developer=b で debate-dev-b-stack）
npx cdk deploy <unit>-dev-stack                                       # 共有結合 dev（Member A 経由で承認）
npx cdk deploy <unit>-prd-stack                                       # 決勝向け prd（Member A のみ実行可、事前承認必須）
```

### 2.4 共有スキーマ（`shared/schema/`）

```bash
npm run schema:gen:ts                       # TypeScript 型生成（openapi-typescript）
poetry run python scripts/gen_models.py     # Python Pydantic モデル生成
```

## 3. 長時間実行コマンド（対話プロセスをブロックしないこと）

以下は AI エージェントによる直接実行を避け、ユーザー手動 or バックグラウンドで起動する:

- `npx expo start` / `npx expo run:ios` / `npx expo run:android`
- `eas build --profile development --platform ios|android`（クラウドビルド、待機が長い）
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

## 5. デプロイ手順 / CI・CD パイプライン（I-4 = A 確定）

### 5.1 環境構成（C-4 確定）

- **AWS アカウント**: 単一アカウント運用（Member A が Builder ID で管理）
- **環境**: dev（共有結合）+ prd（決勝向け）の 2 環境、リージョン `ap-northeast-1` 固定
- **個人 sandbox**: `<unit>-dev-<initial>-stack` で隔離（CDK Context `developer` キー）
- **dev 環境**: `removalPolicy = DESTROY`、Cognito MFA 強制なし
- **prd 環境**: `removalPolicy = RETAIN`、Cognito MFA 強制、cdk-nag 全適用
- **デプロイ順**: `platform-stack` → `auth-stack` → コア 3 並行 → サポート 3 並行（Unit 依存 DAG に従う）
- 詳細は [tech-cdk.md §4.1 環境構成](./tech-cdk.md) を参照

### 5.2 GitHub Actions ジョブ構成

`.github/workflows/` に以下を配置する。

```yaml
# .github/workflows/ci.yml
on: [pull_request, push to develop]
jobs:
  lint-mobile:    ESLint + TypeScript（mobile/）
  lint-backend:   ruff + mypy --strict（backend/）
  lint-infra:    ESLint + cdk-nag（infra/、cdk synth で実施）
  test-mobile:    vitest --run + fast-check
  test-backend:   pytest --maxfail=1 + Hypothesis
  test-contract:  schemathesis（Backend のみ、shared/schema/openapi.yaml に対して fuzz）
  sbom:           Snyk + Dependabot（SECURITY-10）
```

```yaml
# .github/workflows/deploy-dev.yml
on: push to develop
jobs:
  cdk-deploy-platform-dev: manual approval（Member A）
  cdk-deploy-auth-dev:     manual approval（Member A）
  cdk-deploy-debate-dev:   manual approval（Member A or B）
  # ... 各 Unit 同様
```

```yaml
# .github/workflows/deploy-prd.yml
on: workflow_dispatch（手動トリガーのみ）
jobs:
  cdk-deploy-*-prd: manual approval（Member A のみ実行可）
```

### 5.3 CI 必須通過条件

PR マージ前に以下を全て green にする（[AGENTS.md §9](./AGENTS.md) と同じ）:

- 上記 7 ジョブすべて pass
- Coverage 目標達成（Line 80%+ / Branch 70%+）
- SAST Critical / High = 0
- `shared/schema/` 変更時は型生成ファイルが最新（CI 差分なし）+ Schemathesis pass

### 5.4 採用しないもの

- ローカルでの手動 `cdk deploy` のみで運用（CI 経由なし）（[parallel-dev-prerequisites.md I-4](../../aidlc-docs/construction/plans/parallel-dev-prerequisites.md) の選択肢 C）
- 単一 AWS アカウントでの個人 sandbox 分離なし（[parallel-dev-prerequisites.md C-4](../../aidlc-docs/construction/plans/parallel-dev-prerequisites.md) の選択肢 A）
