---
inclusion: manual
---

# Git 運用詳細

> このファイルは manual inclusion です。context を無駄に消費しないため常時注入はしませんが、always steering の [AGENTS.md](./AGENTS.md) §10 に記載された条件に AI が該当したら自発的に readFile で参照してください（git / PR / merge / commit / push / 衝突解決などの相談・操作時）。
> 横断規則は [AGENTS.md](./AGENTS.md) §Git 運用（ダイジェスト）を参照。

---

## 1. ブランチ

| ブランチ | 用途 | 直接 push |
|---|---|---|
| `main` | 本番相当 | **禁止** |
| `develop` | 統合 | **許容**（小規模変更は直接 push 可、大規模 / 破壊的変更は `feature/...` + PR 推奨） |
| `feature/unit-<n>/<topic>` / `fix/<unit>/<topic>` / `chore/<topic>` | 作業 | — |

命名は `unit-of-work.md` の番号と英語 kebab-case。1 ブランチ = 1 PR = 1 関心事。

**運用方針**: ハッカソン期間中（〜決勝 6/26）は迅速な反復を優先し、個人・小規模変更の `develop` 直接 push を許容する。ただし次に該当する変更は必ず `feature/...` ブランチを切って PR 経由でマージする:

- Unit を跨ぐ大規模変更
- `shared/schema/` の更新（API 契約変更、§7 の二段階手順に従う）
- 破壊的変更（ファイル削除、スキーマ破壊、大幅リファクタ）
- コア 3 Unit（Unit-3 Debate / Unit-4 Reel / Unit-5 Cart Intercept）への変更

## 2. マージ戦略

| 方向 | 戦略 |
|---|---|
| `feature/...` → `develop` | squash merge |
| `develop` → `main` | merge commit |

マージ順序は [unit-of-work-dependency.md](../../aidlc-docs/inception/application-design/unit-of-work-dependency.md) の DAG に従う（Unit-1 → Unit-2 → コア 3 並行 → サポート 3 並行）。

## 3. PR 規則

- タイトル: 日本語、70 文字以内、変更内容が分かる粒度
- 本文: 変更内容 / 背景 / 動作確認 / 関連 Story ID を記載
- 必須レビュアー: 同 Unit オーナー以外 1 名以上。コア 3 Unit（Unit-3/4/5）と `shared/schema/` 変更は Member A の Approve 必須
- PR の粒度: 差分 500 行以内目安（自動生成ファイルは除外）

## 4. コミットメッセージ

- 1 行目: 日本語 50 文字以内、prefix なし
- 本文: 空行を挟んで「なぜ」を記述

## 5. 破壊的操作（事前承認必須）

以下は必ずユーザーの明示承認を取る:

- `git push --force` / `git push --force-with-lease`
- `git reset --hard` による公開ブランチの書き換え
- リモートブランチの強制削除（`git branch -D`）
- `main` への直接 commit / push
- 1 PR で 20 ファイル以上の削除

コミット前に差分を確認し、機密情報・無関係な変更が含まれていないことを確かめる。

## 6. 衝突解決

- API 契約（`shared/schema/`）/ DB スキーマ / `shared/` ライブラリの変更: **Member A 決裁**
- Unit 内の UI / ビジネスロジック: 各 Unit オーナー決裁
- 規約例外: 全員合意（PR コメントで記録）
- 合意不能時は **予選 5/30 を最優先** の観点で判断

`develop` とのコンフリクトは PR 作成者が解消。マージ後 CI が赤くなった場合、作成者が 1 時間以内に revert または fix PR を作成。

## 7. API 契約変更時の追加手順

`shared/schema/` を変更する PR は他の実装 PR から分離し、先に merge する。

```
Step 1: 契約 PR
  - shared/schema/openapi.yaml を更新
  - `npm run schema:gen:ts` と `poetry run python scripts/gen_models.py` を実行し生成物も commit
  - CI で Schemathesis が通ることを確認
  - Member A の Approve を取得し merge

Step 2: 実装 PR（契約 merge 後）
  - Mobile / Backend の該当 Story PR を更新
  - 最新の develop を取り込み、生成された型を import
```

契約変更と実装変更を同一 PR に含めると、レビューが困難になり CI も複雑化するため禁止。

## 8. 品質ゲート（PR マージ前に全て green）

- Lint（ESLint / ruff / cdk-nag）エラー 0
- 型チェック（`tsc --noEmit` / `mypy --strict`）エラー 0
- Unit / Property-Based / Integration Test 全件 pass
- Coverage 目標達成（Line 80%+ / Branch 70%+）
- SAST Critical / High 0
- `shared/schema/` 変更時は型生成ファイルが最新（CI 差分なし）+ Schemathesis pass

詳細なツール採用は [tech-typescript.md](./tech-typescript.md) / [tech-python.md](./tech-python.md) / [tech-cdk.md](./tech-cdk.md) を参照。

## 9. `.gitignore` 対象

- `.env`, `.env.local` 等の秘匿設定ファイル
- `node_modules/`, `__pycache__/`, `.venv/`
- ビルド成果物: `dist/`, `build/`, `.cdk.out/`, `*.pyc`
- IDE ローカル設定: `.vscode/*.local.json`（`.vscode/settings.json` の共有分は commit）
- AWS 認証情報: `~/.aws/` や `aws-credentials*` のローカル参照
