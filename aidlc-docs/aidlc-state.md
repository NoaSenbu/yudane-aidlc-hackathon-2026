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
- **Current Stage**: Unit-1 Platform Functional Design Part 2 Generation 完了。承認ゲート → NFR Requirements ステージ移行待ち（2026-05-27）
- **User Language**: Japanese

## Workspace State
- **Existing Code**: No
- **Programming Languages**: None detected
- **Build System**: None detected
- **Project Structure**: Empty (only README.md and LICENSE)
- **Reverse Engineering Needed**: No
- **Workspace Root**: (workspace root)

## Code Location Rules
- **Application Code**: Workspace root (NEVER in aidlc-docs/)
- **Documentation**: aidlc-docs/ only
- **Structure patterns**: See code-generation.md Critical Rules

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
  - tech.md §2: モバイル行に Expo Dev Client + EAS Build 追記、デザインツール行に Claude Design 追記
  - tech-typescript.md §3: §3.1 NativeWind v4 / §3.2 Expo Dev Client + EAS Build 新設
  - tech-cdk.md §4: §4.1 環境構成（C-4 単一アカウント suffix）新設、Stack 命名表に個人 sandbox 行追加
  - api-contracts.md §1: §1.1 第 1 版作成主体（C-3 Member A 一括ドラフト）新設、§7 §7.1 examples 更新責任、§12 クライアントテレメトリスキーマ新設
  - dev-commands.md §2.1: Expo / EAS Build コマンド追加、§2.3: 個人 sandbox suffix 注入、§3: Expo を長時間コマンドに、§5 デプロイ手順を CI/CD パイプライン（I-4）に書き換え
  - AGENTS.md §11: チーム同期プロトコル新設（GitHub Projects / 同期タイミング / コミュニケーション / マイルストーン / ブロッカー対応）
  - mockup/README.md: NativeWind v4 トークンミラーリングの責任を追記
- [ ] Per-Unit Loop (pending - 上記決定事項確定後に Unit-1 Platform から着手)
- [ ] Functional Design (EXECUTE, per-unit)
  - [x] Unit-1 Platform Functional Design Part 1 Planning（2026-05-27、Q1〜Q10 確定）
  - [x] Unit-1 Platform Functional Design Part 2 Generation（2026-05-27、4 ファイル新規 + 4 ファイル既存更新）
  - [ ] Unit-2 Auth & Profile（pending）
  - [ ] Unit-3 Debate / Unit-4 Reel / Unit-5 Cart Intercept（コア 3 並行、pending）
  - [ ] Unit-6 Calendar / Unit-7 Safeguard / Unit-8 Dame Report（サポート 3 並行、pending）
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
| Property-Based Testing | Yes | Full enforcement (all PBT-01〜10) | Requirements Analysis (2026-05-27) |

## 並列開発開始までのロードマップ（Member 別）

> **目的**: Member A〜D が「いつから何ができるか」を 1 枚で把握する。設計書 push と Code Generation の節目で並列開発の解錠範囲が広がる。

### 4 段階の解錠ステージ

| Stage | 達成条件 | 並列開発の解錠範囲 | 目標日 | 状態 |
|---|---|---|---|---|
| **Stage 0** | Inception 完了 | Member A のみ Per-Unit Loop 着手可 | 2026-05-10 | ✅ 完了 |
| **Stage 1** | Unit-1 Functional Design 完了 + 設計書 push | Member B/C/D が **設計書を読んで Mock 駆動で Unit ごとの実装を開始**できる（80-90% の作業） | 2026-05-27 | ✅ **本 push で達成** |
| **Stage 2** | Unit-1 Code Generation 完了（OpenAPI 第 1 版凍結 + scaffold + CI） | Member B/C/D が **`shared/schema/` 経由の型生成 + Prism Mock + npm workspaces** で実装。型安全な並列開発 | 2026-05-29（Day 3 終業時） | ⏳ 未着手 |
| **Stage 3** | Unit-1 Platform Stack を dev 環境にデプロイ | 個人 sandbox 環境で実 AWS リソース（VPC / API Gateway / DDB / KMS）にアクセス可能 | 2026-05-29 夕方〜5/30 朝 | ⏳ 未着手 |
| **Stage 4** | Unit-2 Auth & Profile 完成 | 実 Cognito JWT で API を叩ける、E2E-01〜03 開始可 | 2026-05-30〜6/2 | ⏳ 未着手 |

### Member 別の開始可能タスク（Stage 1 = いま push 後、Mock を別途利用）

> **🧪 TDD ルール（[AGENTS.md §12](../.kiro/steering/AGENTS.md#12-tdd-開発スタイル全-unit-必須) 反映）**: 以下のタスクはすべて **Red → Green → Refactor → PBT 補強** の 4 フェーズで進める。Mobile = Outside-In / Backend = クラシック / CDK = Snapshot TDD。例外は §12.3 のリスト参照（Mockup HTML 移植 / 純粋型定義 / 設定ファイル等）。AI Code Generation はテストファイルを必ず先に生成（§12.4）。

#### Member A（Unit-1 Platform → Unit-2 Auth & Profile）

**いま並行で進める**:
- [ ] Bedrock モデルアクセス申請（Haiku 4.5 + Titan Embeddings V2）— Day 1 朝必須、24-48h 承認
- [ ] NFR Requirements / NFR Design / Infrastructure Design ステージを順次実施
- [ ] Code Generation で OpenAPI 第 1 版 + モノレポ scaffold + CI を生成（Day 3 終業時凍結）
- [ ] Unit-1 Platform Stack を CDK で実装 → dev 環境にデプロイ
- [ ] Unit-2 Auth & Profile に着手

#### Member B（Unit-3 Debate）

**Stage 1 で着手可能（Mock 駆動）**:
- [ ] React Native プロジェクト初期化（Expo Dev Client + NativeWind v4）
- [ ] `mobile/src/features/debate/` 配下の M-04 DebateScreen UI（タイピング演出 / 90 秒タイマー / 事実-心理 2 軸ラベル）
- [ ] Pydantic / TypeScript 型を data-model.md §3.1 / §4.4 から手書きで作成
- [ ] B-02 DebateLlmService の枠組み実装（Mock Bedrock SSE 応答）
- [ ] 論破プロンプト合成ロジック（M-1 + M-2 併走、stress_level 推定）
- [ ] PBT-08 Hypothesis プロパティテスト雛形

**Stage 2 で解錠**: shared/schema/ 経由の型生成、Prism Mock サーバー
**Stage 4 で解錠**: 実 Bedrock 呼び出し、実 Cognito JWT

#### Member C（Unit-4 Reel）

**Stage 1 で着手可能（Mock 駆動）**:
- [ ] `mobile/src/features/reel/` 配下の M-03 ReelScreen 縦型スワイプ UI
- [ ] スワイプジェスチャー（左 = 論破 / 右 = カート監視 / ダブルタップ = Amazon 遷移）
- [ ] B-03 ReelRecommendationService の枠組み（OpenSearch を呼ばず固定リスト返却）
- [ ] B-10 AssociatesLinkGenerator の Special Link URL 生成ロジック
- [ ] B-13 AmazonTransitionRecorder の DDB 書き込みロジック

**Stage 2 で解錠**: shared/schema/ 経由の型生成
**Stage 4 で解錠**: 実 OpenSearch Serverless、実 Creators API（A-10 承認後）

#### Member D（Unit-5 Cart Intercept）

**Stage 1 で着手可能（Mock 駆動）**:
- [ ] Expo Config Plugin で iOS Share Extension scaffold
- [ ] `shared/asin-extractor/` の S-01（functional-design.md §6.1 のサンプルコード）TS / Python 両言語実装
- [ ] M-05 CartInterceptScreen UI を mockup/ から移植
- [ ] B-04 CartIntakeHandler 枠組み（Mock Creators API 商品メタ）
- [ ] B-05 CartAttackScheduler の EventBridge Scheduler 連携ロジック

**Stage 2 で解錠**: shared/schema/ 経由の型生成
**Stage 4 で解錠**: 実 EventBridge Scheduler、実 APNs/FCM 証明書

### Stage 1 push の共有ガイド（Member B/C/D 向け）

push 直後に Member B/C/D が読むべきドキュメント（重要度順）:

1. **何を作るか**: [aidlc-docs/inception/application-design/components.md](./inception/application-design/components.md) / [unit-of-work.md](./inception/application-design/unit-of-work.md)
2. **設計判断（Q1〜Q10）**: [construction/unit-1-platform/functional-design/functional-design-plan.md](./construction/unit-1-platform/functional-design/functional-design-plan.md)
3. **各層の IO/状態/エラー**: [construction/unit-1-platform/functional-design/functional-design.md](./construction/unit-1-platform/functional-design/functional-design.md)
4. **DynamoDB 13 テーブル**: [construction/unit-1-platform/functional-design/data-model.md](./construction/unit-1-platform/functional-design/data-model.md)
5. **5 系統 Mermaid シーケンス**: [construction/unit-1-platform/functional-design/sequence-diagrams.md](./construction/unit-1-platform/functional-design/sequence-diagrams.md)
6. **36 エンドポイント**: [construction/unit-1-platform/functional-design/openapi-skeleton-plan.md](./construction/unit-1-platform/functional-design/openapi-skeleton-plan.md)
7. **後回し事項**: [doc/backlog.md](../doc/backlog.md)

### Mock 利用方針（Stage 1 〜 Stage 2）

- **Stage 1（いま）**: 別途開発中の Mock を利用して各 Unit の実装を開始
- **Stage 2（5/29）**: Unit-1 Code Generation で `shared/schema/openapi.yaml` 凍結 + Prism Mock サーバー（`npm run mock:api`）が動く状態に。各 Member は接続先を Prism に切替
- **Stage 4（5/30〜6/2）**: 個人 sandbox の実 AWS API に接続切替（環境変数 `API_BASE_URL`）


