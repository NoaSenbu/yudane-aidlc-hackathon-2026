---
inclusion: always
---

# プロジェクト規則（AGENTS.md）

> 本ファイルはすべての対話・成果物で **常に** 適用される。
>
> 関連ステアリング: [product.md](./product.md) / [structure.md](./structure.md) / [tech.md](./tech.md) / [hackathon-evaluation-criteria.md](./hackathon-evaluation-criteria.md) / [aws-aidlc-rules/core-workflow.md](./aws-aidlc-rules/core-workflow.md)
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
- ハッカソンの 4 審査基準（ビジネス意図の明確さ／Unit分解の適切さ／創造性とテーマ適合性／ドキュメント品質）を意思決定の指針とする

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

---

## 6. ファイル・ドキュメント

- ファイル操作はワークスペース内に限定し、外部パスへの書き込み・削除は行わない
- アプリケーションコードはワークスペース直下、ドキュメントは `aidlc-docs/` 配下に配置し、両者を混在させない
- 図・ダイアグラムは Markdown 内の Mermaid 記法を第一選択とし、補助として ASCII 図も可とする
- Markdown はリンク切れ・文法エラー・レンダリング崩れがない状態で提出する

---

## 7. Git 運用

### 7.1 ブランチ

| ブランチ | 用途 | 直接 push |
|---|---|---|
| `main` | 本番相当 | **禁止** |
| `develop` | 統合 | **禁止**（PR 経由） |
| `feature/unit-<n>/<topic>` / `fix/<unit>/<topic>` / `chore/<topic>` | 作業 | — |

命名は `unit-of-work.md` の番号と英語 kebab-case。1 ブランチ = 1 PR = 1 関心事。

### 7.2 マージ戦略

| 方向 | 戦略 |
|---|---|
| `feature/...` → `develop` | squash merge |
| `develop` → `main` | merge commit |

マージ順序は [unit-of-work-dependency.md](../../aidlc-docs/inception/application-design/unit-of-work-dependency.md) の DAG に従う（Unit-1 → Unit-2 → コア 3 並行 → サポート 3 並行）。

### 7.3 PR 規則

- タイトル: 日本語、70 文字以内、変更内容が分かる粒度
- 本文: 変更内容 / 背景 / 動作確認 / 関連 Story ID を記載
- 必須レビュアー: 同 Unit オーナー以外 1 名以上。コア 3 Unit（Unit-3/4/5）と `shared/schema/` 変更は Member A の Approve 必須
- PR の粒度: 差分 500 行以内目安（自動生成ファイルは除外）

### 7.4 コミットメッセージ

- 1 行目: 日本語 50 文字以内、prefix なし
- 本文: 空行を挟んで「なぜ」を記述

### 7.5 破壊的操作

以下は **事前承認必須**:

- `git push --force` / `git push --force-with-lease`
- `git reset --hard` による公開ブランチの書き換え
- リモートブランチの強制削除（`git branch -D`）
- `main` / `develop` への直接 commit
- 1 PR で 20 ファイル以上の削除

コミット前に差分を確認し、機密情報・無関係な変更が含まれていないことを確かめる。

### 7.6 衝突解決

- API 契約（`shared/schema/`）/ DB スキーマ / `shared/` ライブラリの変更: **Member A 決裁**
- Unit 内の UI / ビジネスロジック: 各 Unit オーナー決裁
- 規約例外: 全員合意（PR コメントで記録）
- 合意不能時は **予選 5/30 を最優先** の観点で判断

`develop` とのコンフリクトは PR 作成者が解消。マージ後 CI が赤くなった場合、作成者が 1 時間以内に revert または fix PR を作成。

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

詳細なツール採用・テストレイヤー構成は [tech.md](./tech.md) §Lint / §API 契約 / §テストレイヤー を参照。
Unit ごとの Definition of Done・MVP/決勝 Readiness チェックリストは Construction Phase 着手時に per-Unit で作成する。
