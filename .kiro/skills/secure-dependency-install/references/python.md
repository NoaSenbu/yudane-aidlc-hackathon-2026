# poetry / pip の事前 CVE チェック詳細

Python 3.13 Lambda（`backend/`）と共有ライブラリ（`shared/`）の依存追加で適用する。

## 1. インストール前チェックの基本フロー

```bash
# 1) 追加したいパッケージとバージョンを確定（PyPI JSON API で最新版確認）
#    poetry add は範囲を自動解決するため、解決後のバージョンを照会する

# 2) OSV.dev で脆弱性を照会（同梱スクリプト）
python3 .kiro/skills/secure-dependency-install/scripts/check_package.py \
  --ecosystem PyPI --package <pkg> --version <ver>
```

エコシステム名は **`PyPI`**（大文字小文字を厳守。OSV.dev の規定値）。

終了コードで分岐する:

- `0` → そのままインストール可
- `2`（Medium）→ ユーザーに続行可否を確認
- `3`（High/Critical）→ **インストールせず**、修正版を提案
- `1`（エラー）→ `offline.md` の CLI 手順にフォールバック

## 2. poetry での導入

```bash
# バージョンを明示して安全版を固定する
poetry add "requests>=2.32.4"

# 追加後、解決された実バージョンを poetry.lock から確認して再チェック
poetry show requests
```

`poetry add` は範囲を解決して `poetry.lock` に実バージョンを固定する。
ロック後の実バージョンに対して再度スクリプトを実行し、安全を確認する。

## 3. インストール後の全依存スキャン

`pip-audit` で環境全体（推移的依存含む）を検査する:

```bash
# poetry 環境で pip-audit を実行
poetry run pip-audit

# requirements.txt ベースの場合
pip-audit -r requirements.txt

# poetry.lock を直接検査
poetry run pip-audit --desc
```

`pip-audit` が High/Critical を報告した依存は、`poetry add "<pkg>>=<安全版>"` で引き上げる。
直接引き上げられない推移的依存は、親パッケージのアップグレード or 制約追加で対応する。

## 4. プロジェクト固有の注意

- グローバルインストール禁止（tech.md §5）。`venv` / `poetry` でプロジェクト単位に管理。
- `poetry.lock` は必ずコミットする。
- Lambda ランタイムは Python 3.13。3.13 非対応の脆弱性修正版を選ばないよう、対応バージョンを確認する。
- 既存 CI の Dependabot / Snyk と競合しない（事前防御 + 事後防御の二重化）。
