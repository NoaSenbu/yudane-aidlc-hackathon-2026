# Attribution — skill-creator

このディレクトリは、Anthropic が公開している [anthropics/skills](https://github.com/anthropics/skills) リポジトリから **skill-creator** スキルをスナップショットとして取り込んだものです。

## 📌 出典情報

| 項目 | 内容 |
|---|---|
| **スキル名** | `skill-creator` |
| **元リポジトリ** | [anthropics/skills](https://github.com/anthropics/skills) |
| **元パス** | [`skills/skill-creator/`](https://github.com/anthropics/skills/tree/f458cee31a7577a47ba0c9a101976fa599385174/skills/skill-creator) |
| **取得コミット SHA** | `f458cee31a7577a47ba0c9a101976fa599385174` |
| **コミット日時** | 2026-05-09T00:34:37Z |
| **取得日** | 2026-05-10 |
| **取得方法** | GitHub tarball からのスナップショットコピー |
| **ライセンス** | **Apache License 2.0**（[LICENSE.txt](./LICENSE.txt) 参照、原本同梱） |
| **著作権者** | Copyright © 2024-2026 Anthropic, PBC |

## 📝 改変履歴（Apache 2.0 Section 4(b) 準拠）

| 日付 | 変更内容 | 変更者 |
|---|---|---|
| 2026-05-10 | スナップショット取り込み（**原本からの変更なし**） | AIDLC-Hackathon-2026 チーム |

> ⚠️ **Apache 2.0 のライセンス条件として、原本から変更を加えた場合は本テーブルに必ず追記してください。**
> 変更内容には、以下を含めてください：
> - 日付
> - 何を変更したか（ファイル名・変更概要）
> - 変更者

## 📂 含まれるファイル（元リポジトリのまま）

| パス | 概要 |
|---|---|
| `SKILL.md` | スキル定義本体（33KB、YAMLフロントマター＋本文） |
| `LICENSE.txt` | Apache License 2.0 本文（原本同梱） |
| `agents/analyzer.md`, `agents/comparator.md`, `agents/grader.md` | サブエージェント定義 |
| `assets/eval_review.html` | 評価レビュー用のHTMLテンプレート |
| `eval-viewer/viewer.html`, `eval-viewer/generate_review.py` | 評価ビューア |
| `references/schemas.md` | スキーマ定義リファレンス |
| `scripts/*.py` | スキル作成・評価・改善用の Python スクリプト群（8ファイル） |

## 🎯 本プロジェクトにおける利用目的

AWS Summit Japan 2026 AI-DLC ハッカソン参加プロジェクトにおいて、**Agent Skills 形式の書式・構造・メタデータ設計のリファレンス**として利用します。

- Kiro の steering ファイルや独自スキルを整備する際の**雛形・ガイド**として参照
- Agent Skills 標準形式の学習資料
- 将来的なカスタムスキル作成時のパターン参照

> ⚠️ **本スキルの Python スクリプト群（`scripts/`）は Claude / Claude Code 向けに最適化されており、Kiro では直接実行しません。** 実行する場合は、プロジェクト規則「開発環境」に従い、仮想環境（venv / uv 等）でプロジェクトスコープ下に依存を閉じた上で実施してください。

## ⚖️ 商標利用に関する注記（Apache 2.0 Section 6 準拠）

- 本リポジトリは **Anthropic, PBC** の商標（"Anthropic", "Claude" 等）を**宣伝・推奨目的では使用しません**
- これらの名称は、本スキルの出典・著作権帰属を示す限りにおいてのみ言及しています
- 本プロジェクトは Anthropic によって後援・承認されたものではありません

## ⚠️ 免責事項（原本 README より）

原本リポジトリの免責事項を以下に引用します：

> These skills are provided for demonstration and educational purposes only. While some of these capabilities may be available in Claude, the implementations and behaviors you receive from Claude may differ from what is shown in these skills.

## 🔗 関連ドキュメント

- [Apache License 2.0 全文](./LICENSE.txt)
- [元リポジトリ](https://github.com/anthropics/skills)
- [Agent Skills 標準仕様](https://agentskills.io/)
- [本リポジトリ Third-Party Skills 一覧](../../../README.md#third-party-skills)
