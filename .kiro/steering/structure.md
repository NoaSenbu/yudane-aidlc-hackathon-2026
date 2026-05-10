---
inclusion: always
---

# プロジェクト構成

## ディレクトリ配置原則

- **アプリケーションコード**: ワークスペース直下（`mobile/`、`backend/`、`infra/`、`shared/`）
- **ドキュメント**: `aidlc-docs/` 配下のみ
- **両者を混在させない**（AGENTS.md「ファイル・ドキュメント」規約）

## 現在の構成

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
│       │   ├── requirements.md                      # 要件書 v0.6
│       │   └── requirement-verification-questions.md
│       ├── user-stories/
│       │   ├── stories.md                           # 28 本
│       │   ├── personas.md                          # 2 名（悠介・里奈）
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
│       └── plans/
│           ├── execution-plan.md
│           ├── application-design-plan.md
│           ├── unit-of-work-plan.md
│           ├── story-generation-plan.md
│           └── user-stories-assessment.md
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

## 今後追加される構成（Construction フェーズ着手後）

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

## Unit 構成（8 Units、並行開発可能）

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

## 命名規則

- **ファイル / ディレクトリ / コード識別子**: 英語（kebab-case または camelCase / PascalCase）
- **ドキュメント本文・コミットメッセージ・コード内コメント**: 日本語（技術用語の英語併記は可）
- **Lambda コンポーネント ID**: `B-XX`（Backend）/ `M-XX`（Mobile）/ `S-XX`（Shared）
- **FR / NFR ID**: `FR-<領域>-<番号>`（例: `FR-DEBATE-01`、`FR-CART-03`）
- **ストーリー ID**: `US-<領域>-<番号>`（例: `US-01-01`、`US-AUTH-02`）
- **UC / NG / A（前提）ID**: 要件書準拠（`UC-01`、`NG-8`、`A-10`）

## ドキュメント編集ルール

- Markdown 文法エラー・リンク切れがない状態で保つ
- 図は Mermaid を第一選択、ASCII 図は補助
- `aidlc-docs/audit.md` は**追記のみ**（上書き禁止）
- `aidlc-docs/aidlc-state.md` は各ステージの EXECUTE / SKIP / 承認履歴を必ず更新
- 書類審査の 4 評価軸（ビジネス意図 / Unit 分解 / 創造性 / ドキュメント品質）を常に意識

## Git 運用

- `main` / `master` へ直接プッシュしない。作業ブランチ → PR で統合
- コミットメッセージは日本語で簡潔に、対象ステージ・変更内容が伝わる粒度で
- `.gitignore` 対象の機密情報・ビルド成果物を誤コミットしない
