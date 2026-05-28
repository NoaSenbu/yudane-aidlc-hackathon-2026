# 並列開発前提の決定事項（Construction Phase 着手前）

> 4 名の Member A〜D が Unit-1 Platform → Unit-2 Auth → コア 3 並行 → サポート 3 並行で開発を進めるにあたり、**並列着手前にチームで合意すべき項目**を `[Answer]:` タグ形式で投げる。
>
> 参照: [unit-of-work.md](../../inception/application-design/unit-of-work.md) / [unit-of-work-dependency.md](../../inception/application-design/unit-of-work-dependency.md) / [steering/AGENTS.md](../../../.kiro/steering/AGENTS.md) / [steering/tech.md](../../../.kiro/steering/tech.md) / [steering/api-contracts.md](../../../.kiro/steering/api-contracts.md)

***

## 0. 本ドキュメントの位置づけ

* AI-DLC の **Construction Phase 着手前ステージ**（Per-Unit Loop の前提固め）

* ハッカソン書類審査 / 予選評価軸の「AI-DLC プロセスの実践と工夫」の証跡として残す

* 回答確定後、内容を steering 該当ファイル（AGENTS.md / tech.md / dev-commands.md / 等）に反映してから Unit-1 Functional Design に着手する

* 既存 steering で **既に決定済みの事項は本ドキュメントに含めない**（重複排除）

### 決定済み事項（参考、本ドキュメントの議論対象外）

| 領域                | 出典                                                         | 決定事項                                                                            |
| ----------------- | ---------------------------------------------------------- | ------------------------------------------------------------------------------- |
| 言語・主要フレームワーク      | tech.md §2                                                 | RN 0.76+ / TS 5.x / Python 3.13 / CDK v2 / Node 22 LTS                          |
| 状態管理              | tech.md §2 / tech-typescript.md §9                         | TanStack Query + Zustand                                                        |
| 認証                | tech.md §2                                                 | Cognito + Amplify Auth モジュールのみ + TOTP MFA                                       |
| データ層              | tech.md §2                                                 | DynamoDB + S3 + ElastiCache + OpenSearch                                        |
| API 契約 SSOT       | api-contracts.md §1                                        | `shared/schema/openapi.yaml`（OpenAPI 3.1）                                       |
| Lint / 型 / フォーマッタ | tech-typescript.md / tech-python.md / tech-cdk.md          | ESLint strict + Prettier、ruff + mypy --strict、cdk-nag                           |
| 命名規則              | tech-typescript.md §4 / tech-python.md §5 / tech-cdk.md §4 | ファイル kebab-case、識別子 PascalCase/camelCase/snake\_case、Stack `<unit>-<env>-stack` |
| Git / PR / マージ順序  | git-ops.md / AGENTS.md §7                                  | feature/develop/main、squash/merge commit、Unit-1→2→コア→サポート                       |
| ディレクトリ構造          | structure.md §2 / unit-of-work.md                          | mobile / backend / infra / shared モノレポ                                          |
| テスト               | tech-typescript.md §10 / tech-python.md §10                | Vitest + fast-check / pytest + Hypothesis、Line 80%+ / Branch 70%+               |
| セキュリティ            | AGENTS.md §8 / tech.md §3                                  | SECURITY-01〜15 全面、PBT-01〜10 全面                                                  |

***

## 1. Critical 5 項目（並列着手前に必須確定）

### C-1. UI デザインシステムとスタイリング基盤

**背景**: Mobile features を 4 名が並列で実装するため、色・フォント・スペーシング・コンポーネントのトークン基盤が必要。モックアップ HTML は CSS で Indigo×cold rose×cyan のパレットと slow motion を表現済み。

**選択肢**:

* **A. NativeWind v4 + Tailwind 設計トークン** — RN 公式 React Native 系で最もメジャー、トークンを `tailwind.config.js` で集中管理、モックアップの HEX 値（#4F4DDC / #E8B4D0 / #4DE1FF など）をそのまま import 可能。チーム学習コスト低

* **B. Tamagui** — テーマトークン + コンパイル時最適化 + メディアクエリ対応で高機能。学習コスト中

* **C. React Native Paper（Material Design）** — Material 準拠コンポーネントが揃う。YUDANE のダーク基調 + ご褒美感とは方向性が違うため要再着色

* **D. 自作 + StyleSheet.create + theme.ts** — 完全自由、依存なし、Member A が `mobile/src/features/platform/theme/` に design tokens / typography / colors を実装。モックアップとの 1:1 移植が最速

* **E. その他**（自由記述）

**推奨**: **D 自作 + theme.ts**（モックアップ既存 CSS の HEX を移植するだけで済む / 依存ゼロ / 学習コスト 0 / Member A の Platform Unit で 1 ファイル整備すれば全 features が import するだけ）。次点 A（チームが Tailwind 慣れていれば）。

\[Answer]:A

***

### C-2. Bedrock の利用方針（Model 用途 + Region 戦略）

**背景**: 要件書 v0.8 / tech.md は Haiku 4.5（ストリーミング論破）/ Sonnet 4.6（プロンプト合成）/ Titan Embeddings V2 と明記。Inception 中に Sonnet 4.6 の用途は「リアルタイム高品質」「日次バッチでプロンプトテンプレ最適化」「使わない」の 3 案が混在しており、Construction 着手前に確定が必要。`ap-northeast-1` の Provider 状況:

* **Haiku 4.5**: Tokyo apne1 ネイティブ提供（confirmed via web search 2026-05）

* **Sonnet 4.6**: 2026-02-17 Bedrock リリース、Global Cross-Region Inference (CRIS) 経由でアクセス可能（`global.anthropic.claude-sonnet-4-6-v1:0`）

* **Sonnet 4.5**: Tokyo apne1 native 提供あり（CRIS 不要）

* **Titan Embeddings V2**: Tokyo ネイティブ提供

* **Opus 4.6**: 評価用に限定（要件書 §2 より、本実装では使わない）

**選択肢**:

* **A. Haiku 4.5 + Sonnet 4.6 併用**（要件書 v0.8 ママ） — Haiku 4.5 = apne1 native ストリーミング論破、Sonnet 4.6 = Global CRIS で日次バッチプロンプト最適化、Embeddings V2 = apne1 native

* **B. Haiku 4.5 全面採用、Sonnet 4.6 は精度問題が顕在化した時点で後付け導入**（コスト優先） — MVP / 予選 / 決勝の初版は Haiku 4.5 単独で運用。PBT-08 の論破合意率 / 認知負荷指標が要件未達なら Sonnet 4.6 をエスカレーションパスとして後付け追加

* **C. Sonnet 4.5 を Tokyo native で使う**（Sonnet 4.6 は使わず） — CRIS 不要、データ越境なし。ただし要件書 v0.8 の記述更新が必要

* **D. その他**（自由記述）

**推奨**: **B**。理由 — (1) 予選 5/30 まで 3 日で実装範囲を最小化したい、(2) 4 名チームで Sonnet 4.6 のエスカレーション UI / 課金モニタリングまで作る余裕は少ない、(3) Haiku 4.5 単独でも論破プロンプト品質は要件書 §6.3 の合意率目標を満たすベンチマーク報告あり、(4)「精度問題が顕在化したら導入」というドキュメント化された撤退・拡張ロジックは AI-DLC プロセスの工夫の証跡になる。

\[Answer]:B — Haiku 4.5 を全面採用、Sonnet 4.6 は精度問題が顕在化した時点でエスカレーション機能として後付け導入。

**確定（B の帰結）**:

* 要件書 §7 / tech.md §2 / product.md / unit-of-work.md Unit-3 / mockup-validation/3-tap-timeline.md の Sonnet 4.6 関連記述を「**留保された設計オプション = 後付けエスカレーション**」と明記（一律削除はせず、判断ロジックを残す）

* `infra/lib/platform-stack.ts` で Haiku 4.5 + Embeddings V2 の SSM Parameter のみ先行定義。Sonnet 4.6 の SSM Parameter は **未作成のまま留保**（コードコメントで導入トリガーを記述）

* 後付け導入トリガー（少なくとも 1 つで Sonnet 4.6 検討開始）:

  * PBT-08 論破合意率 < 70% が連続 1 週間

  * MVP デモ視聴者の体感評価で「論破が浅い」フィードバックが過半

  * Haiku 4.5 のストリーミングが要件書 §6.3 のレイテンシ要件（初回トークン 3 秒以内）に届かない場合（この場合は Nova Lite 等の軽量モデル fallback も検討）

* Tokyo Region の Bedrock モデルアクセス申請（Haiku 4.5 + Titan Embeddings V2）を **Member A が Unit-1 着手 Day 1 に実施**（承認に 24-48h 必要）

* Inference Profile ID は SSM Parameter Store 経由で取得（`/yudane/dev/bedrock/haiku-model-id`, `/yudane/dev/bedrock/embeddings-model-id`、tech-cdk.md §4 準拠）。コード直書き禁止

* Sonnet 4.6 後付けエスカレーションの判断ロジック・概算工数・後付けトリガーは [doc/backlog.md B-002](../../../doc/backlog.md#b-002-bedrock-sonnet-46-の後付けエスカレーション機能) に集約

***

### C-3. OpenAPI 3.1 第 1 版の作成主体とタイミング

**背景**: api-contracts.md §1 で SSOT は `shared/schema/openapi.yaml` と確定。Q6=A（Unit 着手前に第 1 版凍結）。Unit-2/3/4/5 が並列で実装着手するには、**先に契約のスケルトンが存在する必要**がある。誰が・いつ・どの範囲を書くかが未確定。

**選択肢**:

* **A. Member A 一括ドラフト → 各 Unit オーナーがレビュー** — Unit-1 Platform の Functional Design / Code Generation で Member A が `paths/auth.yaml`, `paths/debate.yaml`, `paths/reel.yaml`, `paths/cart.yaml`, `paths/calendar.yaml`, `paths/safeguard.yaml`, `paths/report.yaml` を全部スケルトン作成（200 OK / Problem Details / 主要エンドポイントのみ）。各 Unit オーナーが PR で詳細化

* **B. 各 Unit オーナーが paths/\*.yaml をドラフト → Member A 統合** — 各オーナーが自分の Unit の paths を `feature/unit-N/openapi-skeleton` ブランチで作成 → Member A が統合 PR で凍結

* **C. ハイブリッド: components/schemas/ は Member A、paths/\*.yaml は各 Unit オーナー** — 共通モデル（User, ProblemDetails, TimeRange 等）を Member A 先行、paths はオーナー

* **D. その他**（自由記述）

**推奨**: **C ハイブリッド**。理由 — (1) `components/schemas/` を先に決めると paths は型を import するだけになる、(2) Member A の負荷分散、(3) Unit オーナーが自分のドメインを最も理解している、(4) api-contracts.md §10 のファイル分割と整合。

**確定すべき詳細**:

* スケルトン凍結期限: **Day 4（Unit-2 Auth & Profile 着手前）**

* 第 1 版に含めるエンドポイント: 28 ストーリーから派生する MVP エンドポイントのみ（dame report 集計など決勝向けは v0.2）

* 凍結後の変更プロセス: api-contracts.md §6 + git-ops.md §7（API 契約 PR 先行 → 実装 PR 追従）

\[Answer]:A

***

### C-4. AWS アカウント構成と環境戦略

**背景**: tech-cdk.md §4 で Stack 命名は `<unit>-<env>-stack`（例: `platform-dev-stack`, `debate-prd-stack`）。env が登場するが、ハッカソン 4 名でどの AWS アカウントをどう使うかは未確定。

**選択肢**:

* **A. 単一 AWS アカウント / env=dev のみ（予選） + env=prd（決勝）** — 全員が同じアカウントの dev で開発、衝突は CDK Stack 名 prefix（例: `platform-dev-yusuke-stack`）で回避。決勝前に prd 環境を追加

* **B. 個人別 sandbox（4 アカウント） + 共有 dev + prd（計 6 アカウント）** — AWS Control Tower 相当の構成、衝突なしだがアカウント管理コスト高

* **C. 単一アカウント / env=dev + env=prd、個人別は CDK Context で suffix** — Member A の個人 Stack は `platform-dev-a-stack`、共有結合 dev は `platform-dev-stack`、決勝 prd は `platform-prd-stack`

* **D. その他**（自由記述）

**推奨**: **C**。理由 — (1) ハッカソン期間中（〜6/26）にアカウント分離する事務コストは過大、(2) 個人別 suffix で開発時の衝突は回避、(3) CDK の `cdk.context.json` に `developer` キーを設けて Stack 名末尾に注入する設計が CDK で一般的、(4) 統合テスト用の共有 dev は Member A が管理。

**確定すべき詳細**:

* AWS アカウント所有者: **Member A** が Builder ID で取得・管理（ハッカソン参加要件）

* 個人 sandbox サフィックス命名: `<unit>-dev-<initial>-stack`（例: `debate-dev-b-stack`）

* 結合 dev 環境のデプロイ権限: Member A 経由で承認（`cdk deploy` は事前承認必須を維持）

* リージョン: `ap-northeast-1` 固定（要件書 §7）

\[Answer]:C

***

### C-5. React Native 実機検証戦略（Expo or Bare）

**背景**: tech.md は RN 0.76+ New Architecture（Fabric + TurboModules）前提。Unit-5 Cart Intercept の Share Extension（iOS Swift）/ Share Target（Android Kotlin）はネイティブモジュールが必須で、Bare workflow が必要になる可能性が高い。

**選択肢**:

* **A. Expo Dev Client（Bare 化対応） + EAS Build** — Expo の便利さ + ネイティブモジュール対応、CI/CD は EAS、ただし EAS は無料枠制限あり

* **B. Bare React Native + EAS Build** — フル制御、Member A〜D が `npx react-native init` で初期化、EAS Build で iOS/Android ビルド

* **C. Bare React Native + ローカル Xcode/Android Studio ビルドのみ** — 最大の自由度、依存なし、各メンバーがローカルで実機ビルド。CI でのビルド確認は省略（コード品質ゲートのみ CI）

* **D. その他**（自由記述）

**推奨**: **A Expo Dev Client**。理由 — (1) Share Extension のネイティブコードは Expo Config Plugin で対応可、(2) Expo の Hot Reload は開発速度を 2-3 倍にする、(3) Member D（Native 担当）以外は Expo の便利さを享受できる、(4) 予選デモは Expo Go で配布も可能（Member A〜D が個別実機セットアップ不要）。次点 C（時間が押した場合の最低限）。

**確定すべき詳細**:

* 実機要件: 各 Member が iOS or Android の最新版実機を 1 台以上保有

* Expo SDK: 52+ （RN 0.76+ 対応）

* ビルド戦略: 開発中は Expo Dev Client、予選デモは Expo Go or Dev Client、決勝は EAS Build または App Store Connect TestFlight

* ネイティブモジュール: Unit-5 の Share Extension は Expo Config Plugin として実装

\[Answer]:A

***

## 2. Important 5 項目（コア Unit 着手前までに）

### I-1. テレメトリ（B-14 / M-13）の最小スキーマ

**背景**: 全 Unit が `B-14 TelemetryIngestionService` に書き込む。S-04 TelemetryContracts の event schema を Unit-1 Platform で先に確定させる必要がある。確定しないと Unit-3/4/5 の telemetry 呼び出しがバラバラになる。

**推奨スキーマ**:

```typescript
type TelemetryEvent = {
  eventId: string;          // ULID
  userId: string;           // anonymized hash for non-auth events
  sessionId: string;        // 起動セッション
  timestamp: string;        // ISO 8601 UTC
  eventType: string;        // e.g. "debate.started", "reel.amazon_tap", "cart.intercept_received"
  unit: 'platform' | 'auth' | 'debate' | 'reel' | 'cart' | 'calendar' | 'safeguard' | 'report';
  properties: Record<string, unknown>;  // event-specific payload
  context: {
    appVersion: string;
    osVersion: string;
    locale: string;
  };
};
```

**確定すべき詳細**:

* Event Type 命名規約: `<unit>.<verb>`（例: `debate.started`, `cart.attack_30m_fired`）

* PII の扱い: `properties` には PII を含めない、ストレージは S3 + Glue + Athena

* 投入経路: Mobile → API Gateway POST `/v1/telemetry` → B-14 Lambda → Kinesis Data Firehose → S3

* リテンション: dev = 7 日、prd = 90 日

**選択肢**:

* **A. 推奨スキーマで確定** — 上記の TypeScript 型を `shared/schema/telemetry/event.ts` に commit、Unit-1 で実装

* **B. 修正して確定** — 修正点を追記

* **C. 最小化（context を削減等）** — どの項目を削るか追記

\[Answer]:**A**

***

### I-2. ログ・監視のスタック

**背景**: tech.md §6 で Lint / 型 / フォーマッタは確定だが、構造化ログのスキーマ・トレースの ON/OFF・ダッシュボードが未確定。

**推奨**:

* **構造化ログ**: AWS Lambda Powertools（Python は `aws-lambda-powertools`、Node.js は `@aws-lambda-powertools/logger`）

* **トレース**: AWS X-Ray を全 Lambda で有効化（cdk-nag 推奨）

* **メトリクス**: CloudWatch Metrics + EMF（Embedded Metric Format）でカスタムメトリクス（例: `DebateAgreementRate`）を発行

* **ダッシュボード**: CloudWatch Dashboard を Member A が `infra/lib/observability-stack.ts` で IaC 化（北極星指標の集計を可視化、AGENTS.md §10 マイルストーン判定で利用）

**選択肢**:

* **A. 推奨どおり全採用**

* **B. X-Ray は決勝以降に後付け、ハッカソン期間は Lambda Powertools のみ**

* **C. 全部見送り、CloudWatch Logs raw のみ**

* **D. その他**

\[Answer]:Cで一旦見送りにします。

**確定（C の帰結）**:

* 暫定運用は CloudWatch Logs raw のみ（Lambda 標準出力）。構造化ログ・X-Ray・EMF・Dashboard は導入しない

* 後付け導入の判断ロジックを [doc/backlog.md B-001](../../../doc/backlog.md#b-001-ログ監視スタック観測性基盤) に集約（後付けトリガー / 暫定運用 / 概算工数）

* 予選 5/30 までは現状維持、決勝 6/26 に向けた AWS デプロイで再評価する

***

### I-3. Mock Server (Prism) の起動規約

**背景**: api-contracts.md §7 で Prism モックサーバーが採用済み。各 Unit が Mock 上で開発を進める手順は記載されているが、`examples` の更新責任が未確定。

**推奨運用**:

* **examples 配置**: `shared/schema/examples/<resource>.yaml` に集約。各 Unit オーナーが自分の Unit の examples を更新する責任を持つ

* **起動コマンド**: `npm run mock:api` を `package.json` の root に定義、内部で `prism mock shared/schema/openapi.yaml --port 4010`

* **CI 確認**: PR 単位で `npm run mock:api` がエラーなく起動することを smoke check

* **Mobile 接続**: `mobile/.env.development` に `API_BASE_URL=http://localhost:4010`、本番は `https://api.yudane.app/v1`（仮）

**選択肢**:

* **A. 推奨どおり**

* **B. examples は Member A が一括管理**（Unit オーナーは Member A に PR で依頼）

* **C. Prism 不採用、Lambda local invoke で代替**（依存削減）

* **D. その他**

\[Answer]:A

***

### I-4. CI/CD パイプラインの実体

**背景**: tech.md §2 で「GitHub Actions」「SBOM (Snyk / Dependabot)」と確定。具体的なジョブ構成は未確定。

**推奨パイプライン**（`.github/workflows/`）:

```
ci.yml:
  on: [pull_request, push to develop]
  jobs:
    - lint-mobile: ESLint + TypeScript
    - lint-backend: ruff + mypy --strict
    - lint-infra: ESLint + cdk-nag (cdk synth)
    - test-mobile: vitest + fast-check
    - test-backend: pytest + Hypothesis
    - test-contract: schemathesis (Backend のみ)
    - sbom: Snyk + Dependabot

deploy-dev.yml:
  on: push to develop
  jobs:
    - cdk-deploy-platform-dev (manual approval)
    - cdk-deploy-auth-dev (manual approval)
    - ...

deploy-prd.yml:
  on: workflow_dispatch
  jobs:
    - cdk-deploy-*-prd (manual approval、Member A のみ実行可)
```

**選択肢**:

* **A. 推奨どおり**

* **B. PR CI は最低限（lint + test）、deploy は手動 cdk deploy** — 時間優先、CI 構築コストを削減

* **C. CI なし、ローカルでの確認のみ** — 最速、ただし品質ゲート不在

* **D. その他**

\[Answer]:A

***

### I-5. Issue / タスク管理ツール

**背景**: 4 名の進捗を毎日同期する場所が未確定。stories.md の 28 ストーリーを誰が今やっているかを共有する必要がある。

**推奨**:

* **GitHub Projects (kanban)** — 同 Repo で完結、ストーリー ID（US-XX-YY）を Issue 化、`unit-N` ラベルで分類、Status は `Todo / In Progress / Review / Done`

* **Daily Standup**: AGENTS.md §11 のチーム同期プロトコルに従う（同期タイミングは別途決定）

* **Coverage**: 28 ストーリー全件を Issue 化、Member A が Day 1 に一括登録

**選択肢**:

* **A. 推奨どおり GitHub Projects + 28 Issue 一括作成**

* **B. Slack のチャンネルでステータス共有のみ**（Issue 化なし、軽量）

* **C. 別ツール**（Notion / Linear / Trello 等）

* **D. その他**

\[Answer]:A

***

## 3. Nice to have / 議論再開項目

### N-1. デザインモックの Claude Design 化（**確定**）

**背景**: 当初は「`mockup/` HTML をそのまま仕様書として運用」でスキップ判定していたが、ユーザー指示によりスキップ判断を撤回し、**Claude Design を SSOT とする運用**で確定する。Figma は採用しない。

**Claude Design とは**: Anthropic Labs が 2026-04-17 にリリースした AI 駆動のデザイン / プロトタイピングツール。自然言語の対話で **HTML / CSS / JavaScript を直接生成** する。Figma のようなベクター・キャンバス上の編集可能ファイルではなく、対話で動くプロトタイプ HTML を作る。Claude Pro / Max / Team / Enterprise プランで research preview 提供中。

**確定方針（A' = Claude Design 単独 SSOT、Figma 不使用）**:

* SSOT は `mockup/index.html`（Claude Design からの出力 HTML）に統一

* Figma は採用しない（Anthropic が Claude を主軸にしている YUDANE スタックと相性が良く、Bedrock Claude Haiku 4.5 + Claude Design で Anthropic ファミリーに揃う）

* 新規画面の生成・既存画面の改良はすべて Claude Design 上で対話的に実施 → エクスポート HTML を `mockup/` に直接更新

* React Native への移植は Claude Design の生成 HTML / CSS（Tailwind ベースで出力されるケースが多い）を NativeWind v4（C-1 = A 採用）のトークンに機械的に変換

**Claude Design 採用のメリット**:

* Anthropic 主軸スタックとの整合性（Bedrock Claude Haiku 4.5 + Claude Design）

* 対話で UI を生成 → そのまま HTML として `mockup/` に統合可能、現存資産を破壊しない

* Figma を持ち込んだ場合の二重管理コストを回避

* AI-DLC プロセスの工夫として「設計フェーズも AI で加速」を審査員にアピール可能

**Claude Design 採用のリスク / 制約**:

* research preview のため API / 出力形式が変わる可能性（commit 履歴で出力スナップショットを残し、再現性を担保）

* 動的挙動（リールスワイプ / 論破タイムライン進行 / トースト等）の表現は HTML + JS で実装可能だが Claude Design の対話的調整が main の使い方になる

* Claude Pro 以上のサブスクリプションが必要（Member A が代表アカウントを保持）

* Figma Variables のようなトークン集中管理は不在 → トークンは `tailwind.config.js`（NativeWind v4）側で集中管理し、Claude Design 出力で参照される色 / スペーシングを後追いで揃える

**確定すべき詳細**:

* SSOT: `mockup/index.html`（Claude Design 出力をそのまま反映）

* デザイントークン管理: NativeWind v4 の `tailwind.config.js` を一次的な真実とし、Claude Design の出力で発生したトークン揺れは Member A が PR で吸収

* 担当: Member A（Claude Design アカウントを保有、新規画面 / 改良は Member A 経由でリクエスト）

* 着手タイミング: 必要に応じて随時（Unit-1 Platform 着手後に theme トークン整備と並行）

* バージョン管理: Claude Design 上のセッション URL / プロンプトを `mockup/README.md` に追記してトレーサビリティを確保

* 採用しないもの: Figma、Storybook（B-102 で見送り済み）、Sketch、Adobe XD

\[Answer]:**A'（Claude Design 単独 SSOT、Figma 不使用）で確定**

***

### N-x. 旧 Nice to have（決定不要、参考）

> N-2 / N-3 / N-5 はスキップ判定済み。後付け導入トリガーと暫定運用は [doc/backlog.md](../../../doc/backlog.md) に集約。

| #   | 項目                  | 推奨方針                                                                | Backlog リンク                                                     |
| --- | ------------------- | ------------------------------------------------------------------- | --------------------------------------------------------------- |
| N-2 | 多言語化（i18n）          | **スキップ**。日本語のみ                                                      | [B-101](../../../doc/backlog.md#b-101-多言語化i18n対応)               |
| N-3 | Storybook 導入        | **スキップ**。UI コンポーネントは features に直接配置                                 | [B-102](../../../doc/backlog.md#b-102-storybook-によるコンポーネントカタログ) |
| N-4 | 通知文言の事前 Copy Review | **mockup-validation/dark-copy-inventory.md §8 に従う**（AI プロンプト型ライブラリ） | （backlog 不要、運用ルール確定済み）                                          |
| N-5 | ダークモード対応            | **不要**。モックアップが既にダーク基調                                               | [B-103](../../../doc/backlog.md#b-103-ダークモード切替ライトモード追加)         |

***

## 4. 回答後のアクション

1. 全 [Answer]: タグが埋まったら、AI が **回答内容を解析**
2. 矛盾・曖昧さがあれば追加質問（Step 5 in functional-design.md と同様）
3. 確定した内容を以下のファイルに反映:

   * **C-1 UI デザインシステム** → `tech-typescript.md` §3 と新規 `mobile/src/features/platform/theme/` の方針メモ

   * **C-2 Bedrock の利用方針（Model 用途 + Region 戦略）** → `requirements.md` §7 / `tech.md` §2 / `product.md` / `unit-of-work.md` Unit-3 / `mockup-validation/3-tap-timeline.md` の Sonnet 4.6 関連記述を「留保された設計オプション」と明記、`tech-cdk.md` §4 SSM Parameter 命名（Haiku 4.5 + Embeddings V2 のみ先行）、後付けエスカレーションは [doc/backlog.md B-002](../../../doc/backlog.md#b-002-bedrock-sonnet-46-の後付けエスカレーション機能) に集約

   * **C-3 OpenAPI 凍結タイミング** → `api-contracts.md` §1（既存）の補足、Unit-1 Platform 担当範囲明記

   * **C-4 AWS アカウント構成** → `tech-cdk.md` §4 の Stack 命名規約に suffix 追加 + `dev-commands.md` §5

   * **C-5 RN 実機検証戦略** → `tech.md` §2 + `dev-commands.md` §3 + `tech-typescript.md` §3

   * **I-1 Telemetry スキーマ** → `shared/schema/telemetry/event.ts`（実装は Unit-1 Code Generation で）

   * **I-2 ログ・監視（C で見送り）** → 暫定運用は CloudWatch Logs raw のみ、後付け導入トリガーは [doc/backlog.md B-001](../../../doc/backlog.md#b-001-ログ監視スタック観測性基盤) に集約

   * **I-3 Prism 運用** → `api-contracts.md` §7（既存）の補足

   * **I-4 CI/CD** → `.github/workflows/` 計画 + `dev-commands.md` 反映

   * **I-5 タスク管理** → `AGENTS.md` §11 同期プロトコルへの追記

   * **N-1 Claude Design 化（A' 確定）** → `tech.md` §2 の技術スタック表に「デザインツール = Claude Design（mockup/ への HTML 出力を SSOT 化、Figma 不採用）」行を追加 + §4 採用しないものに「Figma / Sketch / Adobe XD」を追加 + `mockup/README.md` にバージョン管理ルール（Claude Design セッション URL / プロンプト記録）を追記

   * **N-2 / N-3 / N-5（旧 Nice to have、スキップ確定）** → [doc/backlog.md](../../../doc/backlog.md) §2 にエントリ済み、追加対応不要
4. ステアリング反映完了 → audit.md / aidlc-state.md 更新
5. **Unit-1 Functional Design Part 1 Planning に着手**

***

## 5. ハッカソン書類審査・予選評価軸へのインパクト

| 評価軸                | 本ドキュメントの貢献                                                   |
| ------------------ | ------------------------------------------------------------ |
| ビジネス意図の明確さ         | （直接貢献なし）                                                     |
| Unit 分解の適切さ        | **強化**: 並列実行の前提を明示することで Unit 分解の運用面が補強される                    |
| 創造性とテーマ適合性         | （直接貢献なし）                                                     |
| ドキュメント品質           | **強化**: 決定事項を documented decision として残し、AI-DLC プロセスの工夫の証跡になる |
| AI-DLC プロセス（予選評価軸） | **強化**: Construction Phase 着手前の決定事項整理は AI-DLC のベストプラクティス     |
