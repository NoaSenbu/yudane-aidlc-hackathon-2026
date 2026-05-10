---
inclusion: always
---

# 技術スタックと開発コマンド

## 現在のリポジトリ状態

書類審査（Inception フェーズ）完了時点。**アプリケーションコードはまだ存在しない**。
確定している成果物:

- `aidlc-docs/` 配下の設計ドキュメント（日本語、Markdown + Mermaid）
- `mockup/` 配下の静的 HTML モックアップ（ビジュアル検証用）

Construction フェーズ（Unit ごとの実装）は書類審査後に着手する。

## 技術スタック（要件書 v0.6 / Application Design 準拠）

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

## Extension（全面強制）

- **Security Baseline**: SECURITY-01〜15 すべて適用（要件書 §6.4 参照）
- **Property-Based Testing**: fast-check（TypeScript / React Native）+ Hypothesis（Python 3.13 Lambda）で PBT-01〜10 を全面適用（要件書 §6.5 参照）

## 採用しないもの（明示的除外）

- AWS Amplify Gen 2 の Data / Functions / CLI（Auth モジュールのみ採用）
- `amazon-cognito-identity-js`（npm 公式で非推奨）
- Plaid / Moneytree / Money Forward ME 等の金融アグリゲーション（オンボーディングアンケートで代替）
- Stripe / Square 等の決済サンドボックス（決済は Amazon 側で完結）
- Flutter / Dart（v0.3 以降 React Native に変更）
- Step Functions（時間差制御は EventBridge Scheduler 単独）

## 開発環境ルール（AGENTS.md より）

- グローバルインストール禁止、`venv` / `poetry` / `npm` / Docker でプロジェクト単位に依存を管理
- ロックファイル（`package-lock.json`、`poetry.lock`、`cdk.json` 等）は必ずコミット
- 長時間実行コマンド（`npm run dev`、`webpack --watch`、テスト watch モード）はユーザー手動実行 or バックグラウンド実行。対話プロセスをブロックしない
- 認証情報はコード・ドキュメント・コミット履歴に直接記載しない（AWS Secrets Manager / SSM Parameter Store 経由）

## 現時点で使えるコマンド

モックアップ（静的 HTML、ビルド不要）:

```bash
open mockup/index.html          # macOS
python3 -m http.server -d mockup 8080   # 静的サーバ → http://localhost:8080
```

## Construction フェーズで想定するコマンド（未着手）

実装着手後に各 Unit の Code Generation で確定させる。現時点では参考情報。

```bash
# モバイル（mobile/）
npm install
npm run lint
npm run test            # fast-check PBT を含む
npm run ios / android   # ローカル起動はユーザー手動

# バックエンド（backend/、Poetry 前提）
poetry install
poetry run pytest       # Hypothesis PBT を含む
poetry run ruff check .

# インフラ（infra/、CDK v2）
npm install
npx cdk synth
npx cdk diff
npx cdk deploy <stack-name>   # デプロイはユーザー承認必須
```

## 品質チェック

- Markdown を編集したら Mermaid の文法とリンク切れを確認
- コード編集後は `getDiagnostics` ツールで型・Lint エラーを確認
- 破壊的コマンド（`cdk destroy`、`git push --force`、`rm -rf` 等）は必ずユーザーの明示承認を得る
