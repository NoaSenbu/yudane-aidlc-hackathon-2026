---
inclusion: always
---

# プロジェクト規則（AGENTS.md、コア）

> 本ファイルはすべての対話・成果物で **常に** 適用される。
>
> 常時ロードされる関連 steering: [product.md](./product.md) / [structure.md](./structure.md) / [tech.md](./tech.md) / [hackathon-evaluation-criteria.md](./hackathon-evaluation-criteria.md) / [aws-aidlc-rules/core-workflow.md](./aws-aidlc-rules/core-workflow.md)
>
> コンテキスト発火の fileMatch steering:
>
> - [tech-typescript.md](./tech-typescript.md)（`*.ts*` で発火）
> - [tech-python.md](./tech-python.md)（`*.py` で発火）
> - [tech-cdk.md](./tech-cdk.md)（`infra/**` で発火）
> - [api-contracts.md](./api-contracts.md)（`shared/schema/**` で発火）
> - [hackathon-stage-checklists.md](./hackathon-stage-checklists.md)（`aidlc-docs/**` で発火）
>
> AI が自発的に readFile で参照する manual steering: [git-ops.md](./git-ops.md) / [dev-commands.md](./dev-commands.md)（発動条件は §10 を参照）
>
> ルールが重複する場合、`hackathon-evaluation-criteria.md` > `aws-aidlc-rules/core-workflow.md` > 本ファイル の優先順序とする。

---

## 1. 言語

- 回答・ドキュメント・コミットメッセージ・コード内コメントは原則日本語で記述する
- 技術用語は必要に応じて英語併記を許容する（例: 「ユニットテスト (unit test)」）
- ファイル名・ディレクトリ名・コード内の識別子（変数・関数・クラス等）は英語で記述する
- JSDoc / Python docstring も日本語で記述する

---

## 2. 作業規約

- 勝手な判断で実装・ファイル変更を行わず、計画と内容を提示してユーザーの承認を得てから実行する
- 確認事項を質問する際は、推奨案・背景・目的・選択肢の比較を添えて提示する
- 成果物を提示する前に、自身でレビュー（整合性・要件充足・誤記）を済ませる
- 不明点や前提が曖昧な場合は、推測で進めず必ずユーザーに確認する
- ハッカソンの 4 審査基準（ビジネス意図の明確さ／Unit 分解の適切さ／創造性とテーマ適合性／ドキュメント品質）を意思決定の指針とする

---

## 3. 実装計画

- コード生成前に、変更対象ファイル・影響範囲・手順を明示した実装計画を提示する
- 大規模な変更は小さなステップに分割し、各ステップごとに検証可能な状態を保つ
- 破壊的変更（削除・大幅リファクタ・スキーマ変更等）は事前承認を必須とする

---

## 4. デバッグ・問題解決

- 修正着手前に原因分析を行い、目安として「なぜなぜ分析」を 5 回程度繰り返して根本原因を特定する
- 対症療法的な修正で終わらせず、再発防止の観点を含めて説明する
- 同じアプローチで 2 回以上失敗した場合は、小さな微修正を重ねず方針そのものを見直し、ユーザーへ報告・相談する

---

## 5. 開発環境

- ライブラリ・フレームワークのグローバルインストールは禁止
- 仮想環境・コンテナ（venv、poetry、npm、Docker 等）でプロジェクト単位に依存関係を管理する
- ロックファイル（`package-lock.json`、`poetry.lock` 等）は必ずコミットする
- 長時間実行コマンド（`npm run dev`、`webpack --watch`、テストの watch モード等）はバックグラウンド実行、またはユーザー側での手動実行を前提とし、対話プロセスをブロックしない
- 具体的コマンドは [dev-commands.md](./dev-commands.md) を参照（manual steering、§10 の条件で AI が自発的に readFile する）

---

## 6. ファイル・ドキュメント

- ファイル操作はワークスペース内に限定し、外部パスへの書き込み・削除は行わない
- アプリケーションコードはワークスペース直下、AI-DLC 公式成果物は `aidlc-docs/` 配下、チーム運用ドキュメント（Backlog 等）は `doc/` 配下に配置し、3 者を混在させない（詳細は [structure.md](./structure.md) §1）
- 「後回し」「見送り」「将来検討」「留保された設計オプション」と判断した項目は、判断と同じ作業ターンで [doc/backlog.md](../../doc/backlog.md) に必須 4 項目（項目名 / 出典 / 後付けトリガー / 優先度）で追記する（詳細は [structure.md](./structure.md) §6.1）
- 図・ダイアグラムは Markdown 内の Mermaid 記法を第一選択とし、補助として ASCII 図も可とする
- Markdown はリンク切れ・文法エラー・レンダリング崩れがない状態で提出する

---

## 7. Git 運用（ダイジェスト）

- `main` / `master` へ直接プッシュしない。作業ブランチ → PR で統合
- `develop` への直接 push は小規模変更に限り許容。Unit を跨ぐ大規模変更 / 破壊的変更 / `shared/schema/` 更新は必ず `feature/...` ブランチ + PR を経由する
- コミットメッセージは日本語で簡潔に、対象ステージ・変更内容が伝わる粒度で
- `.gitignore` 対象の機密情報・ビルド成果物を誤コミットしない
- 破壊的操作（`git push --force`、`git reset --hard`、`main` への直接 commit / push 等）は **事前承認必須**

詳細なブランチ戦略・PR 規則・マージ順序・衝突解決・API 契約変更手順は [git-ops.md](./git-ops.md) を参照（manual steering、§10 の条件で AI が自発的に readFile する）。

---

## 8. セキュリティ

- API キー・パスワード・トークン等の認証情報をコード・ドキュメント・コミット履歴に直接記載しない
- 認証情報は環境変数または AWS Secrets Manager / SSM Parameter Store で管理する
- `.env` ファイル等の秘匿ファイルは `.gitignore` に登録する
- `console.log` / `print` での機密情報出力禁止。全ログは構造化ロガー経由
- ユーザー入力は全て検証（Pydantic / Zod）。無検証の `JSON.parse(request.body)` 禁止
- SECURITY Extension（`.kiro/aws-aidlc-rule-details/extensions/security/baseline/`）SECURITY-01〜15 を全面適用

---

## 9. 品質ゲート（原則）

PR マージ前に以下を全て green にする:

- Lint（ESLint / ruff / cdk-nag）エラー 0
- 型チェック（`tsc --noEmit` / `mypy --strict`）エラー 0
- Unit / Property-Based / Integration Test 全件 pass
- Coverage 目標達成（Line 80%+ / Branch 70%+）
- SAST Critical / High 0
- `shared/schema/` 変更時は型生成ファイルが最新（CI 差分なし）+ Schemathesis pass

詳細なツール採用・テストレイヤー構成は [tech.md](./tech.md) §品質ゲート、および言語別 fileMatch steering（[tech-typescript.md](./tech-typescript.md) / [tech-python.md](./tech-python.md) / [tech-cdk.md](./tech-cdk.md)）を参照。
Unit ごとの Definition of Done・MVP/決勝 Readiness チェックリストは Construction Phase 着手時に per-Unit で作成する。

---

## 10. AI が自発的に参照する manual steering

以下の manual steering は context 節約のため常時注入されない。AI は以下の「発動条件」に該当する文脈を検出したら、ユーザーが `#file.md` を指定していなくても **自発的に readFile ツールで該当ファイルを読み込み、その内容に従って応答する**。発動条件に該当するのに読み込まなかった場合は規約違反とみなす。

| ファイル | 発動条件（これらのキーワード / 文脈を検出したら読む） | 補足 |
|---|---|---|
| [git-ops.md](./git-ops.md) | `git` / `commit` / `push` / `pull request` / `PR` / `merge` / `rebase` / `ブランチ` / `branch` / `コンフリクト` / `.gitignore` / `CHANGELOG` / 破壊的 git 操作 / API 契約変更 PR の準備 | git / PR 運用の詳細規約・マージ順序・衝突解決・API 契約 PR の二段階手順など |
| [dev-commands.md](./dev-commands.md) | `npm` / `poetry` / `pytest` / `vitest` / `cdk` / `ビルド` / `build` / `テスト実行` / `デプロイ` / `deploy` / `環境構築` / `ローカル起動` / `ruff` / `mypy` / `schemathesis` / 破壊的 CLI 操作（`rm -rf`、`cdk destroy` 等） | ビルド / テスト / デプロイ / 破壊的コマンドの一覧と実行方針 |

**運用ルール**:

1. 該当コンテキストを検出したら、実装・コマンド提示・助言の前に対象 steering を readFile する
2. 既に同一セッション内で読み込んで内容を記憶している場合は再読込不要（ただし 10 ターン以上経過していれば再確認を推奨）
3. 発動条件が曖昧な場合は、保守的に読み込んでから判断する

---

## 11. チーム同期プロトコル

4 名 Member A〜D が並行で 8 Units を進めるため、進捗・ブロッカー・契約変更を毎日 / 毎週同期する。

### 11.1 タスク管理ツール（I-5 = A 確定）

- **採用**: GitHub Projects（kanban）
- **理由**: 同 Repo で完結 / Issue と PR の自動連携 / 28 ストーリーをそのまま Issue 化できる / 4 名の追加コストゼロ
- **Issue 化の粒度**: 28 ストーリー（[stories.md](../../aidlc-docs/inception/user-stories/stories.md)）を 1 Issue = 1 Story として Member A が Day 1 に一括登録
- **ラベル**: `unit-1` 〜 `unit-8` / `priority-high` / `priority-medium` / `priority-low` / `extension-security` / `extension-pbt` / `blocker`
- **Status**: `Todo` / `In Progress` / `Review` / `Done`
- **採用しないもの**: Slack のみのステータス共有（Issue 化なし）/ Notion / Linear / Trello（[parallel-dev-prerequisites.md I-5](../../aidlc-docs/construction/plans/parallel-dev-prerequisites.md) の選択肢 B/C）

### 11.2 同期タイミング

| 種別 | タイミング | 形式 | 議題 |
|---|---|---|---|
| 日次同期（朝会） | 毎日 10:00（JST） | Slack スタンプ + GitHub Projects 更新 | 昨日の進捗 / 今日のタスク / ブロッカー |
| 週次同期（振り返り） | 金曜 17:00 | 30 分ミーティング | 完了 Story / 未完 Story / マージ順序の調整 / 翌週の優先度 |
| 緊急同期 | 随時 | Slack `#yudane-emergency` チャンネル | API 契約破壊的変更 / 本番障害 / セキュリティインシデント |

### 11.3 コミュニケーションチャネル

| チャネル | 用途 |
|---|---|
| Slack `#yudane-general` | 雑談 / お知らせ |
| Slack `#yudane-dev` | 技術相談 / コードレビュー依頼 |
| Slack `#yudane-emergency` | 緊急対応専用、1 時間以内応答 |
| GitHub Issue | タスク管理 / 議論ログ |
| GitHub PR | コードレビュー / マージ承認 |

### 11.4 マイルストーン判定（書類審査 / MVP / 決勝）

各マイルストーンの Readiness は週次同期で判定する。

| マイルストーン | 期限 | 判定基準 |
|---|---|---|
| 書類審査 | 2026-05-10 | Inception 完了（達成済み） |
| 予選 MVP | 2026-05-30 | E2E 3 シナリオ（E2E-01〜03）pass / 主要 Story 15 / 28 完了 |
| 決勝 | 2026-06-26 | AWS prd デプロイ済 / 全 Story 28 完了 / cdk-nag green |

### 11.5 ブロッカー対応

- ブロッカー検出時は **Issue に `blocker` ラベル + Slack `#yudane-emergency` 即時投稿**
- 24 時間以内に解消しない場合は週次同期で議題化、Member A が代替案を提示
- 同じアプローチで 2 回以上失敗した場合は方針見直し（[§4 デバッグ・問題解決](#4-デバッグ問題解決) に従う）
