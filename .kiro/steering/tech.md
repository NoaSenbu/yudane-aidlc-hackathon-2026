---
inclusion: always
---

# 技術スタックと開発コマンド

## 1. 現在のリポジトリ状態

書類審査（Inception フェーズ）完了時点。**アプリケーションコードはまだ存在しない**。
確定している成果物:

- `aidlc-docs/` 配下の設計ドキュメント（日本語、Markdown + Mermaid）
- `mockup/` 配下の静的 HTML モックアップ（ビジュアル検証用）

Construction フェーズ（Unit ごとの実装）は書類審査後に着手する。

---

## 2. 技術スタック（要件書 v0.7 / Application Design 準拠）

| レイヤ | 採用技術 | 備考 |
|---|---|---|
| モバイル | React Native 0.76+ (New Architecture) + TypeScript 5.x + AWS SDK v3 | Fabric + TurboModules 前提 |
| 状態管理 | TanStack Query（サーバー状態）+ Zustand（クライアント状態） | |
| 認証 | Amazon Cognito + Amplify JavaScript v6 の **Auth モジュールのみ** + TOTP MFA | `amazon-cognito-identity-js` は非推奨のため不採用。Data/Functions/CLI も不採用 |
| API | API Gateway (REST) + AWS Lambda (Python 3.13) | |
| データ | 生 DynamoDB + S3 + ElastiCache Redis + OpenSearch Serverless | Amplify Data (AppSync) は不採用 |
| AI | Amazon Bedrock（Claude Haiku 4.5 ストリーミング論破 / Sonnet 4.6 プロンプト合成）+ Titan Embeddings V2 | Opus 4.7 は評価用に限定 |
| EC 連携 | Amazon Creators API + Amazon Associates Program（Special Link） | PA-API 5.0 は 2026-04-30 deprecation / 2026-05-15 shutdown。Approved Mobile Application 申請が決勝前必須 |
| プッシュ | AWS End User Messaging Push + EventBridge Scheduler | Pinpoint EoL 2026-10-30 への対応。30m/6h/24h 追撃 |
| IaC | AWS CDK (TypeScript, v2 系最新) + Node.js 22 LTS | Amplify CLI は不採用、Cognito User Pool も CDK で直接管理 |
| CI/CD | GitHub Actions + SBOM（Snyk / Dependabot） | SECURITY-10 準拠 |
| リージョン | `ap-northeast-1` | |

---

## 3. Extension（全面強制）

- **Security Baseline**: SECURITY-01〜15 すべて適用（要件書 §6.4 参照）
- **Property-Based Testing**: fast-check（TypeScript / React Native）+ Hypothesis（Python 3.13 Lambda）で PBT-01〜10 を全面適用（要件書 §6.5 参照）

詳細は `.kiro/aws-aidlc-rule-details/extensions/` 配下を参照。

---

## 4. 採用しないもの（明示的除外）

- AWS Amplify Gen 2 の Data / Functions / CLI（Auth モジュールのみ採用）
- `amazon-cognito-identity-js`（npm 公式で非推奨）
- Plaid / Moneytree / Money Forward ME 等の金融アグリゲーション（オンボーディングアンケートで代替）
- Stripe / Square 等の決済サンドボックス（決済は Amazon 側で完結）
- Flutter / Dart（v0.3 以降 React Native に変更）
- Step Functions（時間差制御は EventBridge Scheduler 単独）

---

## 5. 開発環境ルール

- グローバルインストール禁止、`venv` / `poetry` / `npm` / Docker でプロジェクト単位に依存を管理
- ロックファイル（`package-lock.json`、`poetry.lock`、`cdk.json` 等）は必ずコミット
- 長時間実行コマンド（`npm run dev`、`webpack --watch`、テスト watch モード）はユーザー手動実行 or バックグラウンド実行。対話プロセスをブロックしない
- 認証情報はコード・ドキュメント・コミット履歴に直接記載しない（AWS Secrets Manager / SSM Parameter Store 経由）

詳細な依存ライブラリ管理規則は [AGENTS.md](./AGENTS.md) §開発環境 を参照。

---

## 6. Lint・型・フォーマッタ

具体的なツール設定値（`.eslintrc.cjs` / `pyproject.toml` / `cdk.json`）は各プロジェクトルートに配置し、本節では **採用方針** と **必須項目** を定義する。

### 6.1 TypeScript / React Native

| 項目 | 採用 | 備考 |
|---|---|---|
| ESLint ベース設定 | `@typescript-eslint/recommended`（strict）| `tseslint.configs.strict` を利用 |
| React Native 追加ルール | `eslint-plugin-react` + `eslint-plugin-react-native` | Hooks ルール `eslint-plugin-react-hooks` 必須 |
| Import 並び替え | `eslint-plugin-import` + `eslint-plugin-simple-import-sort` | 自動整列を CI で強制 |
| Prettier | 2 spaces / single quote / trailing comma = `all` / semi = true / printWidth = 100 | ESLint と `eslint-config-prettier` で競合回避 |
| Unused import / unused var | **エラー扱い**（警告ではない） | `no-unused-vars` は ESLint で error |

**型安全性**:
- `tsconfig.json` の `"strict": true` 必須
- 追加で有効化: `noUncheckedIndexedAccess` / `exactOptionalPropertyTypes` / `noImplicitOverride` / `noFallthroughCasesInSwitch`
- `any` / `@ts-ignore` / `@ts-nocheck` は原則禁止。やむを得ず使う場合は PR description で理由を明記
- 型アサーション（`as`）よりも型ガード関数を優先

**React Native 固有**:
- コンポーネントは **関数コンポーネント + Hooks** のみ。クラスコンポーネント禁止
- Side effect は `useEffect` / `useLayoutEffect` 以外での実行禁止
- Style は `StyleSheet.create` または `NativeWind`。インラインスタイルは単純な一時用途のみ

**JSDoc**（公開 API には必須、日本語で記述）:

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

### 6.2 Python 3.13 Lambda

| 項目 | 採用 | 備考 |
|---|---|---|
| ruff | `ruff check` + `ruff format` | target: `py313`。rules は `E`, `F`, `W`, `I`, `B`, `UP`, `S`, `ASYNC`, `RUF` |
| mypy | `--strict` | `disallow_untyped_defs = true` を全 Unit で強制 |
| import 並び替え | ruff `I` rule | isort 互換 |
| docstring style | Google style | mypy + ruff の `D` rule で整合 |

**型安全性**:
- 関数の引数・戻り値に **完全型付け** を必須
- `typing.Any` は最小限に限定。`TypedDict` / `pydantic.BaseModel` / `dataclasses` を優先
- Pydantic v2 を採用（Lambda のリクエスト/レスポンス検証）
- Optional は `X | None`（PEP 604）を使用、`Optional[X]` は避ける

**非同期処理**:
- Bedrock ストリーミング等の I/O 多重は `asyncio` または `boto3` の `botocore` + `aiohttp` を利用
- Lambda ハンドラ本体は同期関数のままとし、内部で `asyncio.run()` で async 処理をラップ

**エラーハンドリング**:
- 例外は具体的な型で catch（`except Exception as e:` の包括 catch は禁止）
- 包括 catch が必要な境界（ハンドラ最外周）は `logger.exception()` で構造化ログ出力 + 定型エラーレスポンス
- 例外クラスは `backend/src/common/exceptions/` で集約定義

**docstring**（Google style、日本語で記述）:

```python
def start_debate(user_id: str, product_asin: str, context: DebateContext) -> AsyncIterator[str]:
    """論破セッションを開始する。

    Bedrock Claude Haiku 4.5 にストリーミングで接続し、ユーザーの嗜好ベクトルと
    コンテキスト信号（カレンダー予定・時刻・直近購入履歴）をプロンプトに組み立てる。

    Args:
        user_id: 論破対象のユーザー ID
        product_asin: 対象商品の ASIN
        context: プロンプト組立用のコンテキスト

    Yields:
        Bedrock からのストリーミングチャンク（文字列）

    Raises:
        DebateCooldownError: クールダウン中（FR-DEBATE-05）
    """
```

### 6.3 AWS CDK (TypeScript, v2)

| 項目 | 採用 | 備考 |
|---|---|---|
| cdk-nag | `AwsSolutionsChecks` rule pack | 予選前は `aws-solutions-iam4` / `aws-solutions-l1` 等の本番相当ルールまで全適用 |
| ESLint | TypeScript 側と同じ設定を継承 | |
| Suppression | `NagSuppressions.addResourceSuppressions()` + 理由コメント必須 | 無言サプレッション禁止 |

**推奨パターン**:
- Stack 間の依存は **CloudFormation Export/Import を避け**、CDK プロパティ参照または SSM Parameter Store 経由で連携
- L1 Construct（`Cfn*`）直接使用は最後の手段。L2 / L3 Construct を優先
- `removalPolicy` は dev = `DESTROY`、prd = `RETAIN` を明示

CDK 固有の命名規則は [structure.md](./structure.md) §命名規則 を参照。

---

## 7. API 契約ガバナンス

### 7.1 Single Source of Truth（SSOT）

- **REST API 契約の正本**: `shared/schema/openapi.yaml`（OpenAPI 3.1）
- **非同期イベント契約**: `shared/schema/events/*.json`（AsyncAPI または JSON Schema、将来拡張）
- **ドメイン型（UI / Backend 共有）**: `shared/schema/domain/*.ts`（TypeScript 型定義）

**変更の基本順序**:

```
1. shared/schema/ を更新（契約変更）
   └─ PR を切り、Member A のレビューを受ける
2. 型生成ファイルを同じ PR 内で再生成・commit
3. Mobile / Backend の実装を該当 Story の PR で追従
```

契約変更を実装 PR の中に混ぜ込むことは **禁止**。契約 PR を先に merge してから実装 PR を出す。PR 詳細手順は [AGENTS.md](./AGENTS.md) §Git 運用 §API 契約変更時の追加手順 を参照。

### 7.2 クライアント・サーバー型生成

**TypeScript（Mobile）**:
- ツール: `openapi-typescript`
- 出力先: `shared/schema/types/api.ts`（生成ファイル、commit 必須）
- 実行: `npm run schema:gen:ts`
- 生成物は **手動編集禁止**。ファイル先頭に `/* Generated by openapi-typescript. Do not edit. */` を自動挿入

**Python（Backend）**:
- ツール: `datamodel-code-generator`（Pydantic v2 output）
- 出力先: `backend/src/common/models/api.py`（生成ファイル、commit 必須）
- 実行: `poetry run python scripts/gen_models.py`
- 生成物は **手動編集禁止**。冒頭に `# Generated by datamodel-codegen. Do not edit.`

**CI 検証**: `shared/schema/openapi.yaml` の変更検知で再生成を実行し、コミット済みファイルと差分があれば fail（「生成ファイルが古い」の検知）。

### 7.3 エンドポイント設計規則

**パス・バージョニング**:
- 全エンドポイントは `/v1/...` の prefix 固定
- 破壊的変更（削除・必須フィールド追加・型変更）は `/v2/...` を新設して共存
- v1 / v2 間の deprecation 期間は最低 30 日

**リソース命名**:
| 規則 | 例 |
|---|---|
| リソースは複数形（英語）| `/v1/users`, `/v1/cart-watch-items`, `/v1/debate-sessions` |
| パスは kebab-case | `/v1/cart-watch-items`（`/v1/cartWatchItems` は禁止）|
| リソース ID はパスパラメータ | `/v1/users/{userId}/cart-watch-items/{asin}` |
| Action URL は例外的に許容 | `POST /v1/debate-sessions/{sessionId}/agree` |

**ステータスコード**:
| コード | 用途 |
|---|---|
| 200 / 201 / 204 | 成功（GET/PATCH / POST / DELETE）|
| 400 | リクエスト検証エラー |
| 401 / 403 | 未認証 / 認可エラー（IDOR 含む、SECURITY-08）|
| 404 | リソースなし |
| 409 | 競合（冷却モード中の遷移リクエスト等）|
| 422 | セマンティックエラー |
| 429 | レート制限 |
| 500 | サーバーエラー（詳細を body に含めない、SECURITY-09）|

**レスポンス形式**:
- 正常系はリソース JSON を直接返す
- エラー系は **RFC 7807 Problem Details**:
  ```json
  {
    "type": "https://api.yudane.app/errors/debate-cooldown",
    "title": "論破クールダウン中です",
    "status": 409,
    "detail": "3 回連続の拒否によりクールダウン中（FR-DEBATE-05）。解除まで 02:14:33",
    "instance": "/v1/debate-sessions/abc123"
  }
  ```

### 7.4 認証・認可

- 全エンドポイントは Cognito JWT Bearer Token を要求（ログイン系を除く）
- トークン検証は API Gateway Authorizer で実施、Lambda 側でも `userId` を再検証（SECURITY-08）
- パスパラメータの `{userId}` と JWT claim の `sub` が一致することを Lambda 冒頭で検証

### 7.5 破壊的変更 / 非破壊的変更

**破壊的変更**（v2 path 新設 or 非推奨化が必要）:
- 既存フィールドの削除
- 必須フィールドの追加
- フィールドの型変更
- エンドポイントの削除
- レスポンスステータスコードの意味変更

**非破壊的変更**（v1 内で可能）:
- 省略可能フィールドの追加
- 新規エンドポイント・新規ステータスコードの追加

**非推奨化プロセス**:
1. `openapi.yaml` で `deprecated: true` を付与、代替を description に明記
2. レスポンスヘッダに `Deprecation: true` と `Sunset: <date>` を付加
3. 30 日後に削除（別 PR）

### 7.6 Mock Server（並行開発）

- **Prism**（Stoplight）を採用
- 起動: `npm run mock:api` → `http://localhost:4010` で OpenAPI に準拠したモックサーバー
- `examples` セクションを OpenAPI に書き込めば、それがモックレスポンスになる
- Mobile 側は環境変数 `API_BASE_URL` を `http://localhost:4010` に指定することで Backend 実装完了を待たずに UI 実装可能
- Unit Test / Integration Test 時は **MSW（Mock Service Worker）** で API をモック（`mobile/src/test/msw-handlers.ts` に集約）

### 7.7 契約テスト

- **Backend**: Schemathesis による fuzz test
  ```
  poetry run schemathesis run shared/schema/openapi.yaml --base-url=http://localhost:8000
  ```
  CI で全エンドポイントに対して契約違反レスポンス 0 を必須
- **Mobile**: MSW ハンドラは OpenAPI の examples に対して型で検証。`npm run test:contract` で確認

### 7.8 プライバシー制約の契約レベル表現

**FR-CAL-05 の強制**（カレンダー予定本文を送信しない）:

`shared/schema/openapi.yaml` の `CalendarEvent` スキーマには以下のみを許可:

```yaml
CalendarEvent:
  type: object
  required: [category, timeRange]
  properties:
    category:
      type: string
      enum: [presentation, date, camping, other]
    timeRange:
      $ref: '#/components/schemas/TimeRange'
    # NOTE: title / body / attendees は意図的にスキーマに含めない（NG-7 データ悪用防止）
```

`title` / `body` / `attendees` フィールドの追加は **禁止**。追加 PR は CI の `check-pii-fields.sh` スクリプトで自動 reject。

**機密情報フィールド**:
- `password`, `token`, `secret`, `apiKey`, `creditCard*` 等の名前を持つフィールドは **レスポンスに含めない**
- 例外的に request body に受け取る場合は `example` を伏字にする

**Rate Limit**:
- 全 POST エンドポイントに `429` レスポンスを定義（SECURITY-11）
- ヘッダで `X-RateLimit-Limit` / `X-RateLimit-Remaining` / `X-RateLimit-Reset` を返却

### 7.9 OpenAPI ファイル構造（物理分割）

```
shared/schema/
├── openapi.yaml                  # エントリポイント、refs を集約
├── paths/
│   ├── auth.yaml, debate.yaml, reel.yaml, cart.yaml,
│   ├── calendar.yaml, safeguard.yaml, report.yaml
├── components/
│   ├── schemas/*.yaml            # ドメインモデル
│   ├── parameters/*.yaml
│   └── responses/*.yaml          # 共通レスポンス（ProblemDetails 等）
└── examples/
    └── *.yaml
```

`$ref` で相互参照。CI で `openapi-merge-cli` または `redocly bundle` でマージ版も生成（配布用）。

---

## 8. テストレイヤーとカバレッジ

### 8.1 テストレイヤー構成

| レイヤ | 対象 | ツール | 配置 |
|---|---|---|---|
| **Unit Test** | 関数・クラス単位 | Mobile: `vitest`、Backend: `pytest`、Infra: `jest`（CDK snapshot） | 各プロジェクト `**/*.test.ts` / `tests/test_*.py` |
| **Property-Based Test** | 不変条件・ラウンドトリップ | Mobile: `fast-check`、Backend: `hypothesis` | Unit Test と同居、ファイル名で区別 |
| **Integration Test** | Unit 内のコンポーネント間 | `vitest` + MSW、`pytest` + moto | `mobile/tests/integration/`、`backend/tests/integration/` |
| **Contract Test** | API 契約準拠 | `schemathesis`（Backend）、契約型検証（Mobile）| `backend/tests/contract/` |
| **E2E Test** | 複数 Unit を跨ぐシナリオ | `playwright`（Web 経由）または手動シナリオ | `e2e/` |
| **Smoke Test** | デプロイ直後の疎通確認 | `curl` スクリプト + `jest` | `scripts/smoke/` |

### 8.2 カバレッジ目標

| レイヤ | ライン | ブランチ | 備考 |
|---|---|---|---|
| Unit Test | **80% 以上** | **70% 以上** | 生成ファイル（型定義）は除外 |
| PBT 適用率 | PBT Extension の各カテゴリに対し 1 つ以上のプロパティを実装 | — | PBT-01〜10 ごとに対象テスト存在を CI で検証 |
| Integration Test | 主要シーケンス 100% カバー | — | §8.3 参照 |
| E2E Test | MVP 5/30 時点で 3 シナリオ以上 | — | AGENTS.md §10.1 参照 |

カバレッジは CI で自動計測。目標未達の PR はマージ不可。

### 8.3 Integration Test で最低限カバーすべきシーケンス

| # | シーケンス | 跨ぐ Unit |
|---|---|---|
| IT-01 | Amazon Share Extension 受領 → ASIN 抽出 → Creators API モック → 監視リスト登録 | Unit-5 (Cart Intercept) |
| IT-02 | 30m 遅延通知 → プッシュ配信 → 論破起動 | Unit-5 → Unit-3 (Debate) |
| IT-03 | 論破成功 → Special Link 生成 → Amazon アプリ起動（Deep Link モック）| Unit-3 → Unit-1 (Platform) |
| IT-04 | カレンダー予定 → カテゴリ推定 → リール先頭挿入 | Unit-6 (Calendar) → Unit-4 (Reel) |
| IT-05 | 月間上限到達 → Safeguard 発動 → 論破・リール停止 | Unit-7 (Safeguard) → Unit-3 / Unit-4 |
| IT-06 | 週次集計バッチ → DameReport 生成 → プッシュ通知 | Unit-8 (Dame Report) |
| IT-07 | サインアップ → MFA 設定 → 予算感アンケート → プロファイル永続化 | Unit-2 (Auth & Profile) |

### 8.4 開発プロセス・プロダクトメトリクス

**開発プロセスメトリクス**:

| 指標 | 目標値 | 計測方法 |
|---|---|---|
| PR レビュー応答時間 | 平均 4 時間以内 | GitHub Insights |
| PR merge までの時間 | 24 時間以内 | GitHub Insights |
| CI 成功率 | 95% 以上 | GitHub Actions |
| Coverage（Line） | Unit 80% 以上 / プロジェクト平均 85% 以上 | `codecov` または GitHub Insights |
| 脆弱性対応時間（Critical） | 24 時間以内 | Dependabot ログ |

**プロダクトメトリクス**（MVP 以降、要件書 §6.1 と連動、CloudWatch Dashboard で可視化）:

- 論破セッション → Amazon 遷移率（目標 35%+）
- カート介入通知の開封率（目標 45%+）
- Share 受領 → 論破開始までの平均時間（目標 60 秒以下）
- Bedrock 初回トークン到達時間（目標 1.5 秒以内）

PR マージ条件・Unit DoD・MVP Readiness の詳細は [AGENTS.md](./AGENTS.md) §9〜§10 を参照。

---

## 9. 現時点で使えるコマンド

モックアップ（静的 HTML、ビルド不要）:

```bash
open mockup/index.html          # macOS
python3 -m http.server -d mockup 8080   # 静的サーバ → http://localhost:8080
```

---

## 10. Construction フェーズで想定するコマンド

実装着手後に各 Unit の Code Generation で確定させる。

```bash
# モバイル（mobile/）
npm install
npm run lint
npm run test            # fast-check PBT を含む
npm run ios / android   # ローカル起動はユーザー手動
npm run mock:api        # Prism による OpenAPI モックサーバー
npm run test:contract   # MSW ハンドラの契約型検証

# バックエンド（backend/、Poetry 前提）
poetry install
poetry run pytest       # Hypothesis PBT を含む
poetry run ruff check .
poetry run mypy --strict
poetry run schemathesis run shared/schema/openapi.yaml --base-url=http://localhost:8000

# インフラ（infra/、CDK v2）
npm install
npx cdk synth
npx cdk diff
npx cdk deploy <stack-name>   # デプロイはユーザー承認必須

# 共有スキーマ（shared/schema/）
npm run schema:gen:ts   # TypeScript 型生成
poetry run python scripts/gen_models.py   # Python Pydantic モデル生成
```

---

## 11. 品質チェック

- Markdown を編集したら Mermaid の文法とリンク切れを確認
- コード編集後は `getDiagnostics` ツールで型・Lint エラーを確認
- 破壊的コマンド（`cdk destroy`、`git push --force`、`rm -rf` 等）は必ずユーザーの明示承認を得る
- PR マージ条件・Unit DoD は [AGENTS.md](./AGENTS.md) §品質ゲート を参照
