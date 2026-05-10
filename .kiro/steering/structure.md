---
inclusion: always
---

# プロジェクト構成

## 1. ディレクトリ配置原則

- **アプリケーションコード**: ワークスペース直下（`mobile/`、`backend/`、`infra/`、`shared/`）
- **ドキュメント**: `aidlc-docs/` 配下のみ
- **両者を混在させない**（AGENTS.md §ファイル・ドキュメント 規約）

---

## 2. 現在の構成

```
yudane-aidlc-hackathon-2026/
├── README.md                          # プロダクト概要・ダメ化アーク・システム構成図
├── LICENSE
├── .gitignore
│
├── aidlc-docs/                        # 📄 ドキュメント専用
│   ├── aidlc-state.md                 # 全ステージの EXECUTE/SKIP 進捗追跡
│   ├── audit.md                       # AI-DLC 対話履歴（ISO 8601 タイムスタンプ）
│   └── inception/                     # 🔵 Inception フェーズ（完了）
│       ├── requirements/
│       │   ├── requirements.md                      # 要件書 v0.7
│       │   ├── requirement-verification-questions.md
│       │   ├── ng-scenarios.md                      # NG-1〜8 発動シナリオ
│       │   └── market-positioning.md                # 3 軸市場比較
│       ├── user-stories/
│       │   ├── stories.md                           # 28 本
│       │   ├── personas.md                          # 2 名（悠介・里奈）+ 非ターゲット 3 名
│       │   └── persona-journey.md                   # 悠介の 1 年退化年表
│       ├── application-design/
│       │   ├── application-design.md                # 統合ビュー
│       │   ├── components.md                        # 31 コンポーネント
│       │   ├── component-methods.md
│       │   ├── component-dependency.md              # Mermaid 依存図
│       │   ├── services.md                          # 7 サービス
│       │   ├── unit-of-work.md                      # 8 Units
│       │   ├── unit-of-work-dependency.md
│       │   └── unit-of-work-story-map.md            # ストーリーカバレッジ 100%
│       ├── mockup-validation/                       # AI-DLC 公式外の補助ステージ
│       │   ├── mockup-plan.md
│       │   ├── screen-hypothesis-map.md
│       │   ├── dark-copy-inventory.md
│       │   ├── color-rationale.md
│       │   ├── 3-tap-timeline.md
│       │   └── mockup-to-uc-traceability.md
│       └── plans/
│           ├── execution-plan.md
│           ├── application-design-plan.md
│           ├── unit-of-work-plan.md
│           ├── story-generation-plan.md
│           ├── user-stories-assessment.md
│           └── paper-review-enhancement-plan.md
│
├── mockup/                            # 静的 HTML モックアップ（ビジュアル検証用）
│   ├── README.md
│   ├── index.html                     # 6 画面
│   ├── styles.css
│   ├── app.js
│   └── assets/{brand, products}/*.svg
│
└── .kiro/                             # Kiro 用設定・ステアリング
    ├── steering/                      # 常時適用ルール
    └── aws-aidlc-rule-details/        # AI-DLC ワークフロー詳細
```

---

## 3. 今後追加される構成（Construction フェーズ着手後）

Unit of Work に従い、モノレポで以下を展開する。

```
├── mobile/                   # React Native + TypeScript（Unit ごとに features/ サブディレクトリ）
│   └── src/features/{platform,auth,debate,reel,cart,calendar,safeguard,report}/
├── backend/                  # Python 3.13 Lambda 群、Unit 単位でフォルダ分割
│   └── src/{auth,debate,reel,cart,calendar,safeguard,report,telemetry,common}/
├── infra/                    # AWS CDK (TypeScript)、Unit 単位で Stack 分割
│   └── lib/{platform,auth,debate,reel,cart,calendar,safeguard,report}-stack.ts
└── shared/                   # 横断コンポーネント
    ├── schema/               # OpenAPI 3.1 + 自動生成型
    ├── asin-extractor/       # S-01
    ├── safeguard-policy/     # S-03（Mobile / Backend で共有）
    └── telemetry-contracts/  # S-04
```

---

## 4. Unit 構成（8 Units、並行開発可能）

| # | Unit | 対応 UC | 担当 | Stack |
|---|---|---|---|---|
| 1 | Platform | 横断基盤 | Member A | `platform-stack` |
| 2 | Auth & Profile | UC-05/06/07/08 初期化 | Member A | `auth-stack` |
| 3 | Debate | UC-01 | Member B | `debate-stack` |
| 4 | Reel | UC-02 | Member C | `reel-stack` |
| 5 | Cart Intercept | UC-03 | Member D | `cart-stack` |
| 6 | Calendar | UC-04 | Member B（後半） | `calendar-stack` |
| 7 | Safeguard | UC-08 | Member C（後半） | `safeguard-stack` |
| 8 | Dame Report | UC-06/07 表示 | Member D（後半） | `report-stack` |

依存の順序: **Unit-1 → Unit-2 → コア 3（Unit-3/4/5 並行）→ サポート 3（Unit-6/7/8 並行）**。詳細は `aidlc-docs/inception/application-design/unit-of-work-dependency.md` を参照。

---

## 5. 命名規則

### 5.1 基本原則

- **ファイル / ディレクトリ / コード識別子**: 英語
- **ドキュメント本文・コミットメッセージ・コード内コメント**: 日本語（技術用語の英語併記は可）

### 5.2 ファイル・ディレクトリ

| 対象 | 規則 | 例 |
|---|---|---|
| TypeScript ファイル | kebab-case | `debate-session.ts`、`user-profile.tsx` |
| Python ファイル | snake_case | `debate_session.py`、`user_profile.py` |
| ディレクトリ | kebab-case | `debate-session/`、`user-profile/` |

### 5.3 識別子（コード内）

| 対象 | 規則 | 例 |
|---|---|---|
| TypeScript クラス / 型 | PascalCase | `class DebateSession`、`type UserProfile` |
| TypeScript 関数 / 変数 | camelCase | `function startDebate()`、`const maxTokens = 512` |
| TypeScript 定数（モジュール即値）| UPPER_SNAKE_CASE | `const MAX_DEBATE_TURNS = 3` |
| TypeScript enum | PascalCase、メンバーは UPPER_SNAKE | `enum DebateOutcome { AGREED, REJECTED }` |
| Python クラス | PascalCase | `class DebateSession:` |
| Python 関数 / 変数 | snake_case | `def start_debate():`、`max_tokens = 512` |
| Python 定数 | UPPER_SNAKE_CASE | `MAX_DEBATE_TURNS = 3` |

### 5.4 CDK（TypeScript, v2）固有命名

| 対象 | 規則 | 例 |
|---|---|---|
| Stack | `<unit>-<env>-stack` | `debate-dev-stack`、`platform-prd-stack` |
| Construct | PascalCase | `DebateLambdaConstruct` |
| Logical ID | 意味ある PascalCase | `DebateStreamingLambda` |
| Resource Name（Cognito User Pool 等）| `yudane-<unit>-<env>-<resource>` | `yudane-auth-dev-userpool` |
| SSM Parameter | `/yudane/<env>/<unit>/<key>` | `/yudane/dev/debate/bedrock-model-id` |

### 5.5 ドメイン ID

- **Lambda コンポーネント ID**: `B-XX`（Backend）/ `M-XX`（Mobile）/ `S-XX`（Shared）
- **FR / NFR ID**: `FR-<領域>-<番号>`（例: `FR-DEBATE-01`、`FR-CART-03`）
- **ストーリー ID**: `US-<領域>-<番号>`（例: `US-01-01`、`US-AUTH-02`）
- **UC / NG / A（前提）ID**: 要件書準拠（`UC-01`、`NG-8`、`A-10`）

---

## 6. コード編集ルール

### 6.1 ファイル 1 つあたりの目安

- TypeScript: 300 行以内（例外: UI Component で Story ごとに分かれるもの）
- Python: 400 行以内
- 超える場合は責務分割を検討（`debate/session.py` と `debate/prompt.py` 等）

### 6.2 1 ファイル 1 関心事

- 1 ファイルに複数の関心事（例: `utils.ts` に雑多な関数）は禁止
- 関心事ごとにディレクトリを分け、`index.ts` / `__init__.py` でエクスポート制御

### 6.3 Import 順序（TypeScript）

グループは上から順に配置、グループ間は空行 1 行:

1. External packages（`react`, `react-native`, `@tanstack/react-query` 等）
2. Internal alias（`@/features/debate/...`, `@/shared/...`）
3. Relative（`./components`, `../hooks`）
4. Side-effect only import（`import './styles.css'`）

`eslint-plugin-simple-import-sort` で自動化。Python は ruff の `I` rule で同等の整列を強制。

### 6.4 Circular import の禁止

- CI で検知（madge / pylint）。発生時は責務分割または `shared/` 配下への抽出で解消

### 6.5 未使用コード

- 未使用 import / 変数 / 関数 は ESLint / ruff で **エラー扱い**（警告ではない）
- 「念のため」のコメントアウトされたコード（`// const x = 1;`）は commit に含めない。歴史的経緯は Git 履歴と PR description で残す

### 6.6 コメント方針

- コメントは「なぜ」を書く。「何を」するかはコード自体で明らかにすること
- 公開 API（export 関数・class）には JSDoc / docstring を必須（日本語）
- TODO にはチケット番号や期限を必須で付与: `// TODO(#123): 2026-06 までに B-03 と整合`
- 避けるべき: コードを逐語的に訳しただけのコメント（`i++ // i を 1 増やす`）

詳細な JSDoc / docstring のテンプレートは [tech.md](./tech.md) §Lint・型・フォーマッタ を参照。

---

## 7. ドキュメント編集ルール

- Markdown 文法エラー・リンク切れがない状態で保つ
- 図は Mermaid を第一選択、ASCII 図は補助
- `aidlc-docs/audit.md` は **追記のみ**（上書き禁止）
- `aidlc-docs/aidlc-state.md` は各ステージの EXECUTE / SKIP / 承認履歴を必ず更新
- 書類審査の 4 評価軸（ビジネス意図 / Unit 分解 / 創造性 / ドキュメント品質）を常に意識

---

## 8. Git 運用（ダイジェスト）

- `main` / `master` へ直接プッシュしない。作業ブランチ → PR で統合
- コミットメッセージは日本語で簡潔に、対象ステージ・変更内容が伝わる粒度で
- `.gitignore` 対象の機密情報・ビルド成果物を誤コミットしない

詳細なブランチ戦略・PR 規則・マージ順序・破壊的操作の取扱は [AGENTS.md](./AGENTS.md) §Git 運用 を参照。
