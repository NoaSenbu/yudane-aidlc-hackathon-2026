# npm / yarn / pnpm の事前 CVE チェック詳細

TypeScript / React Native（`mobile/`）と CDK（`infra/`）の依存追加で適用する。

## 1. インストール前チェックの基本フロー

```bash
# 1) 追加したいパッケージとバージョンを確定
npm view <pkg> version          # 最新版を確認
npm view <pkg> versions --json  # 利用可能な全バージョン

# 2) OSV.dev で脆弱性を照会（同梱スクリプト）
python3 .kiro/skills/secure-dependency-install/scripts/check_package.py \
  --ecosystem npm --package <pkg> --version <ver>
```

終了コードで分岐する:

- `0` → そのままインストール可
- `2`（Medium）→ ユーザーに続行可否を確認
- `3`（High/Critical）→ **インストールせず**、修正版を提案
- `1`（エラー）→ `offline.md` の CLI 手順にフォールバック

## 2. 修正版の解決

スクリプト出力の「修正版」を確認し、要求を満たす最小の安全バージョンを選ぶ。

```bash
# 例: lodash@4.17.20 が High → 4.17.21 が修正版
# semver 範囲を満たすか確認してから提案する
npm view lodash@4.17.21 version
```

範囲指定（`^`, `~`）で追加する場合も、解決される実バージョンが安全であることを確認する。
`npm install` 後に `package-lock.json` に固定された実バージョンを再チェックすること。

## 3. インストール後の推移的依存チェック

直接依存だけでなく、ロックファイル生成後にツリー全体を検査する:

```bash
# npm 標準の audit（OSV とは別ソースだが補完になる）
npm audit --audit-level=high

# pnpm の場合
pnpm audit --audit-level high

# yarn (berry) の場合
yarn npm audit --severity high
```

`npm audit` が High/Critical を報告したら:

```bash
npm audit fix              # 互換性のある範囲で自動修正
npm audit fix --force      # ⚠️ 破壊的変更の可能性。事前承認必須
```

`--force` は major アップグレードを伴うため、AGENTS.md §3 に従い事前承認を得る。

## 4. プロジェクト固有の注意

- グローバルインストール禁止（tech.md §5）。必ずプロジェクトの `package.json` に追加する。
- `package-lock.json` は必ずコミットする。
- 既存 CI の Dependabot / Snyk と競合しない（これは「入れる前」、CI は「入れた後」の二重防御）。
- devDependencies であっても本チェックを省略しない（ビルドチェーン経由の供給網攻撃を防ぐ）。
