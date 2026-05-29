# AI-DLC State Tracking

## Project Information
- **Project Name**: yudane-aidlc-hackathon-2026
- **Product Name**: YUDANE（委ね）
- **Hackathon**: AWS Summit Japan 2026 AI-DLC Hackathon
- **Theme**: 「人をダメにするサービスを考えよう！」
- **Submission Deadline**: 2026-05-10
- **Project Type**: Greenfield
- **Start Date**: 2026-05-07T00:00:00Z
- **Current Phase**: 🟢 CONSTRUCTION PHASE
- **Current Stage**: Unit-4 Reel Code Generation Part 2 完了（reel 実装・テスト・CDK 生成、Backend 40 件 pass、承認待ち、2026-05-30）
- **User Language**: Japanese

## Workspace State
- **Existing Code**: Yes（main 側で Unit-1 Platform 完全実装が取り込まれた）
- **Programming Languages**: TypeScript（mobile / infra）+ Python 3.13（backend）
- **Build System**: npm workspaces + Poetry + AWS CDK
- **Project Structure**: mobile/ + backend/ + infra/ + shared/ + aidlc-docs/ + doc/ + mockup/
- **Reverse Engineering Needed**: No
- **Workspace Root**: (workspace root)

## Code Location Rules
- **Application Code**: Workspace root（mobile/ / backend/ / infra/ / shared/）
- **AI-DLC 公式成果物（ドキュメント）**: aidlc-docs/ 配下
- **チーム運用ドキュメント**: doc/ 配下
- **Structure patterns**: structure.md §1 参照

## Stage Progress
### 🔵 INCEPTION PHASE
- [x] Workspace Detection
- [ ] Reverse Engineering (N/A - greenfield)
- [x] Requirements Analysis（v0.8、2026-05-10 ダメ化 3 段メカニズム M-1/M-2/M-3 を明示化）
- [x] User Stories（美咲ペルソナ追加、2026-05-10）
- [x] Workflow Planning
- [x] Application Design
- [x] Units Generation
- [x] 🆕 Mockup Validation（補助ステージ / AI-DLC 公式外 / 6 ファイル完成、2026-05-10）

### 🟢 CONSTRUCTION PHASE
- [x] 並行開発規約の整備（既存ステアリング 3 ファイルに統合、2026-05-10）
  - AGENTS.md: Git 運用 / 品質ゲート / MVP・決勝 Readiness / 同期プロトコル
  - structure.md: 識別子命名規則 / コード編集ルール
  - tech.md: Lint・型・フォーマッタ / API 契約ガバナンス / テストレイヤー
- [x] Backlog 運用ルールの整備（`doc/backlog.md` 新設 + structure.md §1/§6.1 + AGENTS.md §6 更新、2026-05-27）
- [x] 並列開発前提の決定事項（parallel-dev-prerequisites.md、Critical 5 + Important 5 + N-1 確定、2026-05-27）
  - C-1=A NativeWind v4 / C-2=B Haiku 4.5 単独・Sonnet 4.6 backlog / C-3=A Member A 一括ドラフト / C-4=C 単一アカウント suffix / C-5=A Expo Dev Client + EAS Build
  - I-1=A 推奨スキーマ / I-2=C 見送り（backlog） / I-3=A 推奨運用 / I-4=A 推奨パイプライン / I-5=A GitHub Projects
  - N-1=A' Claude Design 単独 SSOT、Figma 不採用
- [x] 並列開発前提決定のステアリング一括反映（2026-05-27）
  - tech.md / tech-typescript.md / tech-cdk.md / api-contracts.md / dev-commands.md / AGENTS.md / mockup/README.md
- [x] TDD 開発スタイルをステアリングに反映（2026-05-28、Outside-In / クラシック / Snapshot のハイブリッド方式）
- [x] **main → develop マージ完了**（2026-05-29、Unit-1 Platform 実装 140 ファイルを develop に取り込み、ステアリング拡張は develop 版を維持）
- [ ] Per-Unit Loop（進行中）
  - **Unit-1 Platform**（完了 ✅）
    - [x] Functional Design（承認済み、2026-05-29）
    - [x] NFR Requirements（承認済み、2026-05-29）
    - [x] NFR Design（承認済み、2026-05-29）
    - [x] Infrastructure Design（承認済み、2026-05-29）
    - [x] Code Generation Part 2 完了（2026-05-29）
    - **正本ドキュメント**: `aidlc-docs/construction/unit-1-platform/{functional-design, nfr-requirements, nfr-design, infrastructure-design, code}/`（main 由来）
    - **正本実装**: `mobile/` / `backend/` / `infra/` / `shared/`（main 由来、TDD で生成済み）
    - **参考ドキュメント**: develop 系の `functional-design-plan.md` / `functional-design.md` / `data-model.md` / `openapi-skeleton-plan.md` / `sequence-diagrams.md`（Q1〜Q10 検討プロセスの記録として残置、main 正本との差分は audit に記載）
  - **Unit-2 Auth & Profile**（pending）
  - **Unit-3 Debate**（進行中）
    - [x] Functional Design Part 1 Planning（2026-05-28、Q1〜Q15 提示、main マージで一部前提見直し必要）
    - [ ] Functional Design Part 2 Generation（pending、main 側 Unit-1 確定を踏まえて Q1〜Q15 再検討）
  - **Unit-4 Reel**（進行中）
    - [x] Functional Design Part 1 Planning（2026-05-30、`feature/unit-4-reel` ブランチ作成 + Q1〜Q10 提示 + CL-1/2/3 clarification、全回答受領）
    - [x] Functional Design Part 2 Generation（2026-05-30、`construction/reel/functional-design/` に domain-entities / business-logic-model / business-rules / frontend-components の 4 種生成、承認済み 2026-05-30）
    - [x] NFR Requirements Part 1 Planning（2026-05-30、Q1〜Q10 提示、全 A 回答受領）
    - [x] NFR Requirements Part 2 Generation（2026-05-30、`construction/reel/nfr-requirements/` に nfr-requirements / tech-stack-decisions 生成、承認済み 2026-05-30。再レビューで 5 件修正済み）
    - [x] NFR Design Part 1 Planning（2026-05-30、Q1〜Q10 提示、全 A 回答受領）
    - [x] NFR Design Part 2 Generation（2026-05-30、`construction/reel/nfr-design/` に nfr-design-patterns / logical-components 生成、矛盾 3 件解消 + 過剰設計・矛盾 2 件再修正、承認済み 2026-05-30）
    - [x] Infrastructure Design Part 1 Planning（2026-05-30、Q1〜Q7 提示、全 A 回答受領）
    - [x] Infrastructure Design Part 2 Generation（2026-05-30、`construction/reel/infrastructure-design/` に infrastructure-design / deployment-architecture 生成、Unit-1 基盤を SSM 参照で再利用、承認待ち）
    - [x] Infrastructure Design Part 2 Generation（2026-05-30、`construction/reel/infrastructure-design/` に infrastructure-design / deployment-architecture 生成、Unit-1 基盤を SSM 参照で再利用、承認済み 2026-05-30。横断矛盾 3 件修正済み）
    - [ ] Code Generation Part 1 Planning（2026-05-30、`unit-4-reel-code-generation-plan.md` 10 ステップ提示、承認待ち）
    - [ ] Code Generation Part 2 Generation（pending）
    - [x] Code Generation Part 1 Planning（2026-05-30、`unit-4-reel-code-generation-plan.md` 10 ステップ提示、レビュー修正 3 件後承認）
    - [x] Code Generation Part 2 Generation（2026-05-30、shared/schema + backend/src/reel + mobile/src/features/reel + infra/lib/reel-stack 生成。Backend ロジック+PBT 40 件 pass 実行確認。承認待ち）
      - **cross-unit 依頼**: platform-stack の `api-id`/`api-root-resource-id` SSM 公開（Member A）、OpenSearch コレクション追加（決勝）
  - **Unit-5 Cart Intercept**（コア 3 並行、pending）
  - **Unit-6 Calendar / Unit-7 Safeguard / Unit-8 Dame Report**（サポート 3 並行、pending）
- [ ] Functional Design (EXECUTE, per-unit)
- [ ] NFR Requirements (EXECUTE, per-unit)
- [ ] NFR Design (EXECUTE, per-unit)
- [ ] Infrastructure Design (EXECUTE, per-unit)
- [ ] Code Generation (EXECUTE, per-unit)
- [ ] Build and Test (EXECUTE)

### 🟡 OPERATIONS PHASE
- [ ] Operations (placeholder)

## Extension Configuration
| Extension | Enabled | Mode | Decided At |
|---|---|---|---|
| Security Baseline | Yes | Full enforcement (all SECURITY-01〜15) | Requirements Analysis (2026-05-07) |
| Property-Based Testing | Yes | Full enforcement (all PBT-01〜10) | Requirements Analysis (2026-05-07) |
| TDD 開発スタイル | Yes | Outside-In / クラシック / Snapshot ハイブリッド | 2026-05-28 |

## 並列開発開始までのロードマップ（Member 別）

> **目的**: Member A〜D が「いつから何ができるか」を 1 枚で把握する。設計書 push と Code Generation の節目で並列開発の解錠範囲が広がる。
>
> **2026-05-29 時点のステータス**: main 側で Unit-1 Platform Code Generation Part 2 が完了し、develop に取り込み完了。Stage 2 / Stage 3 の前提が整った。

### 4 段階の解錠ステージ

| Stage | 達成条件 | 並列開発の解錠範囲 | 目標日 | 状態 |
|---|---|---|---|---|
| **Stage 0** | Inception 完了 | Member A のみ Per-Unit Loop 着手可 | 2026-05-10 | ✅ 完了 |
| **Stage 1** | Unit-1 Functional Design 完了 + 設計書 push | Member B/C/D が **設計書を読んで Mock 駆動で Unit ごとの実装を開始** | 2026-05-27 | ✅ 完了 |
| **Stage 2** | Unit-1 Code Generation 完了（OpenAPI 第 1 版凍結 + scaffold + CI） | Member B/C/D が **`shared/schema/` 経由の型生成 + Prism Mock + npm workspaces** で実装 | 2026-05-29 | ✅ **完了**（main マージで取り込み） |
| **Stage 3** | Unit-1 Platform Stack を dev 環境にデプロイ | 個人 sandbox 環境で実 AWS リソースにアクセス可能 | 2026-05-29 夕方〜5/30 朝 | ⏳ Member A 実施中 |
| **Stage 4** | Unit-2 Auth & Profile 完成 | 実 Cognito JWT で API を叩ける、E2E-01〜03 開始可 | 2026-05-30〜6/2 | ⏳ 未着手 |

### Member 別の開始可能タスク（Stage 2 = 現在）

> **🧪 TDD ルール**: すべて Red → Green → Refactor → PBT 補強の 4 フェーズ（[AGENTS.md §12](../.kiro/steering/AGENTS.md#12-tdd-開発スタイル全-unit-必須)）。Mobile = Outside-In / Backend = クラシック / CDK = Snapshot TDD。

#### Member A（Unit-1 Platform 完了 → Unit-2 Auth & Profile）

**完了済み**:
- [x] Bedrock モデルアクセス申請（Haiku 4.5 + Titan Embeddings V2）
- [x] OpenAPI 第 1 版（`shared/schema/openapi.yaml`）+ モノレポ scaffold + CI
- [x] Unit-1 Platform Stack の CDK 実装

**進行中**:
- [ ] Unit-1 Platform Stack を dev 環境にデプロイ（Stage 3）
- [ ] Unit-2 Auth & Profile に着手

#### Member B（Unit-3 Debate）

**Stage 2 で着手可能**:
- [ ] `mobile/src/features/debate/` 配下の M-04 DebateScreen UI（タイピング演出 / 90 秒タイマー / 事実-心理 2 軸ラベル）
- [ ] `shared/schema/paths/debate.yaml` の詳細化（5 エンドポイント）+ `examples` 整備
- [ ] B-02 DebateLlmService の枠組み実装（Mock Bedrock SSE 応答）
- [ ] 論破プロンプト合成ロジック（M-1 + M-2 併走、stress_level 推定）
- [ ] PBT-08 Hypothesis プロパティテスト雛形（Outside-In TDD で先行）

#### Member C（Unit-4 Reel）

**Stage 2 で着手可能**:
- [ ] `mobile/src/features/reel/` 配下の M-03 ReelScreen 縦型スワイプ UI
- [ ] スワイプジェスチャー（左 = 論破 / 右 = カート監視 / ダブルタップ = Amazon 遷移）
- [ ] B-03 ReelRecommendationService の枠組み（OpenSearch を呼ばず固定リスト返却）
- [ ] B-10 AssociatesLinkGenerator の Special Link URL 生成ロジック
- [ ] B-13 AmazonTransitionRecorder の DDB 書き込みロジック

#### Member D（Unit-5 Cart Intercept）

**Stage 2 で着手可能**:
- [ ] Expo Config Plugin で iOS Share Extension scaffold
- [ ] `shared/asin-extractor/`（main 側で既に実装済み、`shared/asin-extractor/src/extract-asin.ts`）を活用
- [ ] M-05 CartInterceptScreen UI を mockup/ から移植
- [ ] B-04 CartIntakeHandler 枠組み（Mock Creators API 商品メタ）
- [ ] B-05 CartAttackScheduler の EventBridge Scheduler 連携ロジック
