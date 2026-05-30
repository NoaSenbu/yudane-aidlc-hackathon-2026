# ネットワーク制限環境でのフォールバック手順

`check_package.py` が OSV.dev に到達できず終了コード `1` を返した場合、
ローカルにインストール済みの CLI ツールで脆弱性チェックを行う。

## 判定しきい値（共通）

| 深刻度 | 挙動 |
|---|---|
| Critical / High | ブロック（インストール中止） |
| Medium | 警告してユーザーに確認 |
| Low | 記録のみ |

## npm / yarn / pnpm

```bash
# npm 標準（レジストリの advisory DB を参照。要ネットワークだが OSV とは別経路）
npm audit --audit-level=high --json

# 完全オフラインなら osv-scanner のローカル DB を使う
# （事前に `osv-scanner --download-offline-databases` で DB を取得済みの場合）
osv-scanner --lockfile=package-lock.json --offline
```

## poetry / pip

```bash
# pip-audit（ローカルにキャッシュされた advisory を使用可能）
poetry run pip-audit

# osv-scanner で poetry.lock を検査
osv-scanner --lockfile=poetry.lock
```

## osv-scanner（両エコシステム横断・推奨）

`osv-scanner` はプロジェクト全体のロックファイルを一括検査できる:

```bash
# プロジェクトルートで全ロックファイルを再帰検査
osv-scanner scan --recursive .

# オフライン DB を事前ダウンロードしておけば完全オフライン動作
osv-scanner --download-offline-databases scan --offline --recursive .
```

## ツールが一切ない場合

1. パッケージ名・バージョンをユーザーに提示し、手元の環境で
   [osv.dev](https://osv.dev/) または [github.com/advisories](https://github.com/advisories) を
   手動照会してもらう。
2. 照会できるまでインストールを保留する（チェックを飛ばして入れない）。
