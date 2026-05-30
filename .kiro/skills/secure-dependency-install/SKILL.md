---
name: secure-dependency-install
description:
  パッケージをインストールする前に CVE / 既知脆弱性を必ずチェックするスキル。npm install / npm add /
  yarn add / pnpm add / poetry add / pip install / requirements.txt や package.json への依存追加など、
  新しい依存を導入しようとする全ての場面で必ず使う。Critical / High の脆弱性があれば中止し、修正版があれば
  提案する。「パッケージを入れて」「ライブラリを追加して」「install」「add dependency」「依存を更新」等の
  文脈で、ユーザーが明示的に脆弱性チェックを依頼していなくても発火させること。
license: MIT
metadata:
  author: yudane-team
  version: '1.0.0'
---

# Secure Dependency Install（依存パッケージ CVE ガード）

新しい依存パッケージを**インストールする前に**既知脆弱性（CVE）を照会し、リスクを評価してから導入可否を
判断するためのスキル。「入れてから `npm audit` で気づく」のではなく「入れる前に止める」ことを目的とする。

対象エコシステム: **npm**（TypeScript / React Native）と **PyPI / poetry**（Python 3.13 Lambda）。

> このスキルはプロジェクトの SECURITY-10（SBOM / Snyk / Dependabot）と品質ゲート §9（SAST Critical / High = 0）を
> インストール段階に前倒しするもの。既存の CI 上の Snyk / Dependabot と競合せず補完する。

## いつ使うか（発火条件）

以下を検出したら、実際にインストールコマンドを実行する**前に**必ずこのスキルを適用する:

- `npm install <pkg>` / `npm i <pkg>` / `npm add` / `yarn add` / `pnpm add`
- `poetry add <pkg>` / `pip install <pkg>` / `uv pip install <pkg>`
- `package.json` の `dependencies` / `devDependencies` への追記
- `pyproject.toml` の `[tool.poetry.dependencies]` や `requirements*.txt` への追記
- 依存バージョンのアップグレード（範囲指定の変更を含む）

ユーザーが「脆弱性をチェックして」と言わなくても、依存追加の意図があれば発火させる。

## 判断基準（しきい値）

| 深刻度 | CVSS v3 スコア | 挙動 |
|---|---|---|
| **Critical** | 9.0–10.0 | **ブロック**（インストール中止） |
| **High** | 7.0–8.9 | **ブロック**（インストール中止） |
| **Medium** | 4.0–6.9 | **警告**して続行可否をユーザーに確認 |
| **Low** | 0.1–3.9 | 記録のみ、続行可 |
| 該当なし | — | そのまま続行 |

品質ゲート §9 と整合させ、**Critical / High は 0 件**を必須とする。

## ワークフロー（必ずこの順序で）

1. **対象を確定する**
   - パッケージ名と、実際に解決されるバージョンを特定する。
   - バージョン未指定なら最新版を解決する（npm: `npm view <pkg> version` / PyPI: PyPI JSON API）。
   - 直接依存だけでなく、可能なら推移的依存も視野に入れる（ロックファイル生成後の再チェックで担保）。

2. **脆弱性を照会する**
   - 同梱スクリプトを使う:
     ```bash
     python3 .kiro/skills/secure-dependency-install/scripts/check_package.py \
       --ecosystem npm --package <pkg> [--version <ver>]
     ```
     ```bash
     python3 .kiro/skills/secure-dependency-install/scripts/check_package.py \
       --ecosystem PyPI --package <pkg> [--version <ver>]
     ```
   - このスクリプトは OSV.dev の公開 API（認証不要）に照会し、CVSS から深刻度を算出する。
   - ネットワークが使えない環境では `references/offline.md` の手順（`npm audit` / `pip-audit` / `osv-scanner`）に切り替える。

3. **結果を判定する**
   - スクリプトの終了コード: `0`=問題なし / `2`=Medium 警告 / `3`=High/Critical ブロック / `1`=実行エラー。
   - Critical / High → **インストールしない**。修正版があれば提案する（次項）。
   - Medium → リスクと回避策を提示し、続行するかユーザーに確認する。

4. **修正版を提案する（脆弱性が見つかった場合）**
   - スクリプト出力の "fixed versions" から、要求範囲を満たしつつ脆弱性を解消する最小バージョンを提示する。
   - 修正版がない場合は、代替パッケージの検討 or 導入見送りを提案する。
   - **承認フロー**: 修正版を選ぶ／代替案にする／見送る、をユーザーに確認してから実行する（AGENTS.md §2 準拠）。
   - 見送り判断をした場合は同ターンで `doc/backlog.md` に 4 必須項目で追記する（structure.md §6.1）。

5. **インストール後に再チェックする**
   - インストールでロックファイル（`package-lock.json` / `poetry.lock`）が更新されたら、
     推移的依存を含めて `references/offline.md` の全ツリースキャンを実行し、新規脆弱性がないことを確認する。

## タイポスクワッティングの確認

CVE とは別に、パッケージ名が著名パッケージの誤記（typosquatting）でないかを軽く確認する。
不自然な名前・極端に少ないダウンロード数・最近作られたばかりのパッケージはユーザーに注意喚起する。
詳細は `references/supply-chain.md` を参照。

## 禁止事項

- 脆弱性チェックを省略して `npm install` / `poetry add` 等を実行すること。
- Critical / High が出ているのに承認なしで続行すること。
- 認証情報（`SNYK_TOKEN` 等）をコード・ログ・コミットに直接記載すること（AGENTS.md §8）。

## 参照ファイル

- `references/npm.md` — npm / yarn / pnpm の事前チェックと修正版解決の詳細
- `references/python.md` — poetry / pip の事前チェックと修正版解決の詳細
- `references/offline.md` — ネットワーク制限環境での CLI ベースの代替手順
- `references/supply-chain.md` — typosquatting・メンテナンス状況の確認観点
- `scripts/check_package.py` — OSV.dev 照会 + CVSS 深刻度算出スクリプト（npm / PyPI 両対応）
