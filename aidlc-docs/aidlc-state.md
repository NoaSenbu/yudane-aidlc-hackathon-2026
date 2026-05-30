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
- **Current Stage**: 🎉 Unit-1 + Unit-2 完了（Member A 前半フェーズ完了）→ Unit-3 Debate UI SSOT を Direction D「黒服のコンシェルジュ」に切替完了（2026-05-30）+ Unit-4 Reel Code Generation Part 2 完了（reel 実装・テスト・CDK 生成、Backend 40 件 pass、2026-05-30）+ Unit-5 Cart Intercept Code Generation Part 2 完了 + 1 巡目セルフレビュー Z1〜Z6 + 2 巡目セルフレビュー W1〜W7 + Build and Test 検証完了（2026-05-30、Unit-5 スコープ内 177 件すべて pass + 検証時修正 4 件 + Unit-1 由来問題 2 件 backlog 登録 = B-506 / B-507）。`feature/unit-4-reel` を develop にマージ（2026-05-30）。Unit-3 は Code Generation Phase 1 Part 2（実装着手）前 / Unit-4・Unit-5 は承認ゲート通過、次 Unit / 次ステージ移行待ち
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
- [ ] Per-Unit Loop（進行中: Unit-2 Auth & Profile）
- [x] Backlog 運用ルールの整備（`doc/backlog.md` 新設 + structure.md §1/§6.1 + AGENTS.md §6 更新、2026-05-27）
- [x] 並列開発前提の決定事項（parallel-dev-prerequisites.md、Critical 5 + Important 5 + N-1 確定、2026-05-27）
  - C-1=A NativeWind v4 / C-2=B Haiku 4.5 単独・Sonnet 4.6 backlog / C-3=A Member A 一括ドラフト / C-4=C 単一アカウント suffix / C-5=A Expo Dev Client + EAS Build
  - I-1=A 推奨スキーマ / I-2=C 見送り（backlog） / I-3=A 推奨運用 / I-4=A 推奨パイプライン / I-5=A GitHub Projects
  - N-1=A' Claude Design 単独 SSOT、Figma 不採用
- [x] 並列開発前提決定のステアリング一括反映（2026-05-27）
  - tech.md / tech-typescript.md / tech-cdk.md / api-contracts.md / dev-commands.md / AGENTS.md / mockup/README.md
- [x] TDD 開発スタイルをステアリングに反映（2026-05-28、Outside-In / クラシック / Snapshot のハイブリッド方式）
- [x] **main → develop マージ完了**（2026-05-29、Unit-1 Platform 実装 140 ファイルを develop に取り込み、ステアリング拡張は develop 版を維持）
- [x] **UI SSOT を Direction D「黒服のコンシェルジュ」に切替**（2026-05-30、`aidlc-docs/construction/unit-3-debate/YUDANE Concierge (Direction D) (offline).html` を Construction 以降の正本に。旧 `mockup/index.html` v0.4 は Inception 期参考資料として残置。tech.md §1/§2/§4 / mockup/README.md / 新規 design-system/direction-d-design-system.md / 新規 unit-3-debate/functional-design/frontend-design.md / Phase 1 Plan §0 + Step 7.3 / doc/backlog.md B-301 を一括更新、diagnostics エラーゼロ）
- [ ] Per-Unit Loop（進行中）
  - **Unit-1 Platform** ✅ 完了（2026-05-29）
    - [x] Functional Design（承認済み）
    - [x] NFR Requirements（承認済み）
    - [x] NFR Design（承認済み）
    - [x] Infrastructure Design（承認済み）
    - [x] Code Generation（承認済み、Step 1〜20 完了）
  - **Unit-2 Auth & Profile**（Member A）✅ 完了（2026-05-29）
    - [x] Functional Design（承認済み）
    - [x] NFR Requirements（承認済み）
    - [x] NFR Design（承認済み）
    - [x] Infrastructure Design（承認済み）
    - [x] Code Generation（承認済み、Step 1〜15 完了）
  - **Unit-3 Debate**（進行中）
    - [x] Functional Design Part 1 Planning v1（2026-05-28、Q1〜Q15 提示、develop 系前提）
    - [x] Functional Design Part 1 Planning v2（2026-05-29、main 整合、自前 Lambda + DDB + Lambda Streaming 案）
    - [x] Functional Design Part 1 Planning v3（2026-05-29、**AgentCore Runtime + Memory + Identity 全面採用版**、Q1〜Q17）
    - [x] Functional Design Part 1 Planning v3.2（2026-05-29、**通常運用版全採用 = オプション C**、Q1〜Q17 確定。L1 機能面の穴 3 件（Q11/Q13/Q12）を MVP の段階で塞ぐ。custom Strategy / PBT 全面 / SSM 切替 / 3 RuntimeEndpoint を追加）
    - [x] Functional Design Part 1 Planning v3.3（2026-05-29、**セルフレビュー修正版**、Critical 6 件 + Major 6 件を一括修正。設計判断自体に変更なし、ドキュメント整合性のみ向上）
    - [x] task-breakdown.md（2026-05-29、Phase 1〜6 実装計画 + P0/P1/P2 優先度マトリクス + 5/30 暫定構成 + リスク 7 件 + 依存 DAG）+ v1.1 修正（v3.3 整合）
    - [x] Functional Design Part 2 Generation（2026-05-29、6 ファイル）
      - business-logic-model.md（ALG-DEBATE-START / ALG-COOLDOWN-* / ALG-STRESS / ALG-PROMPT / ALG-MEMORY-* / ALG-AFFIRMATION / ALG-GRACEFUL-SHUTDOWN / ALG-MOD / ALG-S3-EXPORT の 11 アルゴリズム）
      - business-rules.md（DEBATE / COOLDOWN / PROMPT / STRESS / MEMORY / MOD / AUTHZ / STREAM / ENDPOINT / SSM / PBT の 11 区分 + 設定値カタログ）
      - domain-entities.md（Mermaid クラス図 + Pydantic v2 / TypeScript 型定義 + 13 DTO + Memory / DDB データモデル）
      - strands-agent-design.md（ファイル構造 + main.py 実装方針 + Strands Agent 設定 + タイマー実装 + Q15 起動方法 + Property 1〜5）
      - prompt-composition.md（M-1 + M-2 併走テンプレート 4 ブロック + compose.py 実装 + PBT 重点 property + プロンプト改善ロードマップ）
      - sequence-diagrams.md（Mermaid シーケンス 8 種: 翻意 / クールダウン / graceful shutdown / 多層モデレーション / Memory 学習 / Year 1 退化レポート / クールダウン解除 / env 切替）
    - [x] **多巡セルフレビュー完了（2026-05-29、7 巡で Critical 9 件 + Major 8 件を修正、全 8 ファイル diagnostics エラーゼロ）**
    - [x] **NFR Requirements ステージ完了（2026-05-29、2 ファイル）**
      - nfr-requirements.md（性能 / コスト / カバレッジ / セキュリティ / 倫理担保 / PBT / 可用性 / 観測 / A11y の 9 区分、Extension コンプライアンスサマリ）
      - tech-stack-decisions.md（AgentCore + Strands + Bedrock の Unit-3 固有スタック実体化、Direct Code Deploy / Memory Strategy / RuntimeEndpoint / SSM 7 個）
    - [x] **NFR Design ステージ完了（2026-05-29、2 ファイル + 多巡セルフレビュー）**
      - logical-components.md（LC-D-01〜12 の 12 論理コンポーネント定義 + Mermaid 依存図 + NFR Requirements 対応サマリ）
      - nfr-design-patterns.md（PAT-D-PERF / COST / ETHICS / RESIL / OBS / SEC の 6 区分 21 パターン + FMEA + マイルストーン別優先度）
      - **多巡セルフレビュー**（2 巡で Critical 4 + Major 6 + 1 件を修正、kill-switch ヘルパー経由統一 / Mobile 側 actor_id 取得経路明示 / DDBError try/except 整合 / A11Y 帰属修正 / 定数名カタログ参照 / FMEA Sonnet 切替 N/A 化 / PAT-D-COST-04 を P0 へ昇格 / NFR ID 表記統一 / NC2-2 削除）
    - [x] **Infrastructure Design ステージ完了（2026-05-30、2 ファイル + 多巡セルフレビュー）**
      - infrastructure-design.md（AgentCore Runtime + Memory + Bedrock Guardrails + Cooldowns DDB + S3 Memory Export + IAM 個別 + SSM 8 個 + CloudWatch Alarms 5 種 + 論理 → 物理マッピング表）
      - deployment-architecture.md（dev/staging/prd の 3 環境戦略 + SSM 経由連携 + CI/CD フロー + cdk-nag Suppression 方針 + 物理アーキテクチャ図 Mermaid + カナリアリリース手順 + ロールバック手順 + GO/NO-GO チェックリスト + コスト見積もり）
      - **多巡セルフレビュー（6 巡）**（Critical 8 + Major 13 + Minor 1 = **計 22 件を 6 巡で修正**）
        - 1 巡目: Critical 4 + Major 5（タイマー責任主体 / Unit-7 削除権限 / E2E ID 整合 / Memory P0/P1 段階 / Alarms 出典 / 環境別 RuntimeEndpoint Phase / Bedrock コスト式 / Mermaid シンタックス）
        - 2 巡目: Critical 1 + Major 1（SSM 昇格メカニズム / Unit-7/8 並列デプロイ）
        - 3 巡目: Major 1 + Minor 1（Memory custom P1 明示 / lifecycleConfiguration コメント）
        - 4 巡目（**重要**）: Critical 3 + Major 2（**Mobile-SSM 直接読み と Cognito Identity Pool 不採用の矛盾を発見、EAS Build 時 EXPO_PUBLIC_* 環境変数注入方式に統一** / カナリアトラフィック振り分け OTA 段階配信明示 / Memory IAM actor_id 単位分離不可能性明示）
        - 5 巡目: Major 1（Phase 5 開始日 6/13 vs 6/14 vs 6/15 混在解消、6/13 に統一）+ Minor 1（許容）
        - 6 巡目: Major 2（staging 検証期間 6/13 起点 / 決勝 Readiness 6/15 前倒し目標 6/14 整合）
        - **計 22 件のクロスステージ矛盾を全て解消**（Functional Design / NFR Requirements / NFR Design / Infrastructure Design の 4 ステージ + shared-infrastructure / Unit-1 連携の整合性チェック完了）
    - [x] **Code Generation Phase 1 Plan 完了（2026-05-30、1 ファイル + 多巡セルフレビュー）**
      - `aidlc-docs/construction/plans/unit-3-debate-code-generation-phase1-plan.md`（Phase 1 期間 5/31〜6/2、Member B 担当、Step 1〜8 詳細化、TDD サイクル、ファイル一覧、依存関係、リスク表、ハッカソン評価軸インパクト）
      - **Step 構成**: Step 1 Infra Snapshot TDD / Step 2 SSM Loader / Step 3 Domain Models / Step 4 Cooldown DDB Adapter / Step 5 main.py 最小実装 / Step 6 Mobile AgentCore Client / Step 7 Mobile Event Parser / Step 8 疎通確認
      - **多巡セルフレビュー（3 巡）**（Critical 2 + Major 4 + 1 + 0 件 = 計 7 件を 3 巡で修正、`parse_jwt_actor_id` の責務を Step 4 → Step 5 へ移動 / `bedrock_kwargs={}` 仕様確認注記 / RuntimeEndpoint live test 追加 / `agentcore invoke --dev` モード明示 / vitest `vi.stubEnv` モック方法明示 / SSM model-id 動的反映の再起動待ち追記 / **Step 3/4 順序逆転を解消（Domain Models を Step 3 へ繰り上げ、Cooldown を Step 4 へ）** / **CDK で `kms.Key.fromKeyArn()` での復元を明示** / Cognito MFA 未設定リスクの緩和策表現改善）
    - [ ] Code Generation Phase 1 Part 2 実装着手（pending、Step 1〜8 を Part 2 で順次実行）
  - **Unit-4 Reel**（進行中）
    - [x] Functional Design Part 1 Planning（2026-05-30、`feature/unit-4-reel` ブランチ作成 + Q1〜Q10 提示 + CL-1/2/3 clarification、全回答受領）
    - [x] Functional Design Part 2 Generation（2026-05-30、`construction/reel/functional-design/` に domain-entities / business-logic-model / business-rules / frontend-components の 4 種生成、承認済み 2026-05-30）
    - [x] NFR Requirements Part 1 Planning（2026-05-30、Q1〜Q10 提示、全 A 回答受領）
    - [x] NFR Requirements Part 2 Generation（2026-05-30、`construction/reel/nfr-requirements/` に nfr-requirements / tech-stack-decisions 生成、承認済み 2026-05-30。再レビューで 5 件修正済み）
    - [x] NFR Design Part 1 Planning（2026-05-30、Q1〜Q10 提示、全 A 回答受領）
    - [x] NFR Design Part 2 Generation（2026-05-30、`construction/reel/nfr-design/` に nfr-design-patterns / logical-components 生成、矛盾 3 件解消 + 過剰設計・矛盾 2 件再修正、承認済み 2026-05-30）
    - [x] Infrastructure Design Part 1 Planning（2026-05-30、Q1〜Q7 提示、全 A 回答受領）
    - [x] Infrastructure Design Part 2 Generation（2026-05-30、`construction/reel/infrastructure-design/` に infrastructure-design / deployment-architecture 生成、Unit-1 基盤を SSM 参照で再利用、承認済み 2026-05-30。横断矛盾 3 件修正済み）
    - [x] Code Generation Part 1 Planning（2026-05-30、`unit-4-reel-code-generation-plan.md` 10 ステップ提示、レビュー修正 3 件後承認）
    - [x] Code Generation Part 2 Generation（2026-05-30、shared/schema + backend/src/reel + mobile/src/features/reel + infra/lib/reel-stack 生成。Backend ロジック+PBT 40 件 pass 実行確認。承認済み 2026-05-30、`feature/unit-4-reel` を develop にマージ）
      - **cross-unit 依頼**: platform-stack の `api-id`/`api-root-resource-id` SSM 公開（Member A）、OpenSearch コレクション追加（決勝）
  - **Unit-5 Cart Intercept**（進行中、Functional Design / NFR Requirements / NFR Design / Infrastructure Design 完了、Code Generation Part 2 完了、Build and Test 検証完了、2026-05-30）
  - **Unit-6 Calendar / Unit-7 Safeguard / Unit-8 Dame Report**（サポート 3 並行、pending）
- [ ] Functional Design (EXECUTE, per-unit)
  - [x] Unit-1 Platform Functional Design Part 1 Planning（2026-05-27、Q1〜Q10 確定）
  - [x] Unit-1 Platform Functional Design Part 2 Generation（2026-05-27、main 由来 + 4 ファイル新規 + 4 ファイル既存更新）
  - [ ] Unit-2 Auth & Profile（pending）
  - [ ] Unit-3 Debate（Part 1 Planning 進行中、2026-05-28、Q1〜Q15 提示済、main マージで前提見直し必要）
  - [ ] Unit-4 Reel（コア並行、pending）
  - [x] Unit-5 Cart Intercept Functional Design Part 1 Planning（2026-05-28、Q1〜Q8 全て推奨どおり確定）
  - [x] Unit-5 Cart Intercept Functional Design Part 2 Generation（2026-05-28、4 ファイル新規 + backlog 2 件追記）
  - [ ] Unit-6 Calendar / Unit-7 Safeguard / Unit-8 Dame Report（サポート 3 並行、pending）
- [ ] NFR Requirements (EXECUTE, per-unit)
  - [x] Unit-5 Cart Intercept NFR Requirements Part 1 Planning（2026-05-28、Q1〜Q10 確定、2 段階再検証で 10 件修正）
  - [x] Unit-5 Cart Intercept NFR Requirements Part 2 Generation（2026-05-28、nfr-requirements.md + tech-stack-decisions.md）
- [ ] NFR Design (EXECUTE, per-unit)
  - [x] Unit-5 Cart Intercept NFR Design Part 1 Planning（2026-05-28、Q1〜Q6 確定、再検証で 3 件修正）
  - [x] Unit-5 Cart Intercept NFR Design Part 2 Generation（2026-05-28、nfr-design-patterns.md + logical-components.md）+ 1 巡目セルフレビュー 5 件修正（Issue BBBB/CCCC/DDDD/EEEE/FFFF）+ 2 巡目セルフレビュー 6 件修正（Issue GGGG/HHHH/IIII/JJJJ/KKKK/LLLL、watching_orphaned 全文書整合 + retry_count 属性追加 + retry batch シーケンス図 §7 追加 + コスト試算更新 + Mock 戦略追記 + M-05 可視化方針）
- [ ] Infrastructure Design (EXECUTE, per-unit)
  - [x] Unit-5 Cart Intercept Infrastructure Design Part 1 Planning（2026-05-29、Q1〜Q10 確定 v3、再検証 2 巡目で v1 → v2 → v3 と 8 件修正・補強）
  - [x] Unit-5 Cart Intercept Infrastructure Design Part 2 Generation（2026-05-29、infrastructure-design.md + deployment-architecture.md、1 巡目セルフレビュー 2 件修正、B-504 backlog 登録、diagnostics エラーゼロ）
- [ ] Code Generation (EXECUTE, per-unit)
  - [x] Unit-1 Platform Code Generation Part 1 + Part 2（2026-05-29、main 由来 20 Step 完了）
  - [x] Unit-5 Cart Intercept Code Generation Part 1 Planning（2026-05-29、25 Step、v1 → v2 → v3 で 11 件修正）
  - [x] Unit-5 Cart Intercept Code Generation Part 2 Generation（2026-05-29、25 Step すべて完了、純粋ロジック層 + Backend Lambda + CDK Stack 生成、NG-6 静的検証 CI スクリプト pass、全ファイル diagnostics エラーゼロ）+ 1 巡目セルフレビュー Z1〜Z6 修正（2026-05-29、重大 3 + 中 2 + 軽微 1 = 計 6 件即修正）+ 2 巡目セルフレビュー W1〜W7 完了（2026-05-30、即修正 4 系統 = W1 / W2-1 / W3（4 Lambda）/ W4 + B-505 backlog 登録 + TODO 残置 = W7 / W2-2 + 問題なし確認 = W5 / W6）
- [ ] Build and Test (EXECUTE)
  - [x] Unit-5 Cart Intercept Build and Test 検証（2026-05-30、Unit-5 スコープ内 177 件 pass / 検証時修正 4 件 / B-506 cdk-nag + B-507 TS compile を Unit-1 由来として backlog 登録）

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
