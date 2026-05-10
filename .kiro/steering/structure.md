---
inclusion: always
---

# プロジェクト構成（コア）

> このファイルは常にコンテキストに含まれます。言語別の命名規則・コード編集ルールは、対象ファイルを編集した時に自動発火する fileMatch steering を参照してください。
>
> - TypeScript / React Native: [tech-typescript.md](./tech-typescript.md)（`*.ts*` で発火）
> - Python: [tech-python.md](./tech-python.md)（`*.py` で発火）
> - CDK 固有命名: [tech-cdk.md](./tech-cdk.md)（`infra/**` で発火）

---

## 1. ディレクトリ配置原則

- **アプリケーションコード**: ワークスペース直下（`mobile/`、`backend/`、`infra/`、`shared/`）
- **ドキュメント**: `aidlc-docs/` 配下のみ
- **両者を混在させない**（AGENTS.md §ファイル・ドキュメント 規約）

---

## 2. 現在の構成

```
yudane-aidlc-hackathon-2026/
├── README.md
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
│       │   ├── personas.md                          # 2 名 + 非ターゲット 3 名
│       │   └── persona-journey.md                   # 1 年退化年表
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
├── mockup/                            # 静的 HTML モックアップ
│   ├── README.md
│   ├── index.html                     # 6 画面
│   ├── styles.css
│   ├── app.js
│   └── assets/{brand, products}/*.svg
│
└── .kiro/                             # Kiro 用設定・ステアリング
    ├── steering/                      # 常時適用ルール + fileMatch + manual
    └── aws-aidlc-rule-details/        # AI-DLC ワークフロー詳細
```

---

## 3. 今後追加される構成（Construction フェーズ着手後）

Unit of Work に従い、モノレポで以下を展開する。

```
├── mobile/                   # React Native + TypeScript
│   └── src/features/{platform,auth,debate,reel,cart,calendar,safeguard,report}/
├── backend/                  # Python 3.13 Lambda 群
│   └── src/{auth,debate,reel,cart,calendar,safeguard,report,telemetry,common}/
├── infra/                    # AWS CDK (TypeScript)
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

依存順序: **Unit-1 → Unit-2 → コア 3（Unit-3/4/5 並行）→ サポート 3（Unit-6/7/8 並行）**。
詳細は `aidlc-docs/inception/application-design/unit-of-work-dependency.md` を参照。

---

## 5. 言語共通の基本原則

- **ファイル / ディレクトリ / コード識別子**: 英語
- **ドキュメント本文・コミットメッセージ・コード内コメント**: 日本語（技術用語の英語併記は可）

言語固有の命名規則（kebab-case / snake_case / PascalCase）・ファイルサイズ・import 順序・コメント方針は、対象ファイル編集時に発火する fileMatch steering に集約しています。

---

## 6. ドキュメント編集ルール

- Markdown 文法エラー・リンク切れがない状態で保つ
- 図は Mermaid を第一選択、ASCII 図は補助
- `aidlc-docs/audit.md` は **追記のみ**（上書き禁止）
- `aidlc-docs/aidlc-state.md` は各ステージの EXECUTE / SKIP / 承認履歴を必ず更新
- 書類審査の 4 評価軸（ビジネス意図 / Unit 分解 / 創造性 / ドキュメント品質）を常に意識

---

## 7. Git 運用（ダイジェスト）

- `main` / `master` へ直接プッシュしない。作業ブランチ → PR で統合
- コミットメッセージは日本語で簡潔に、対象ステージ・変更内容が伝わる粒度で
- `.gitignore` 対象の機密情報・ビルド成果物を誤コミットしない

詳細なブランチ戦略・PR 規則・マージ順序・破壊的操作の取扱は [git-ops.md](./git-ops.md) を参照（manual steering、[AGENTS.md](./AGENTS.md) §10 の条件で AI が自発的に readFile する）。
