# Unit-1 Platform — Functional Design Part 1 Planning

> Construction Phase の Per-Unit Loop 第 1 ターン。Unit-1 Platform は 8 Units すべての基盤となるため、本 Functional Design で固める設計判断は他全 Unit のスタートラインを定義する。
>
> 参照: [unit-of-work.md Unit-1](../../../inception/application-design/unit-of-work.md#unit-1-platform-横断基盤) / [components.md](../../../inception/application-design/components.md) / [component-methods.md](../../../inception/application-design/component-methods.md) / [parallel-dev-prerequisites.md](../../plans/parallel-dev-prerequisites.md) / [steering/AGENTS.md](../../../../.kiro/steering/AGENTS.md) / [steering/api-contracts.md](../../../../.kiro/steering/api-contracts.md) / [steering/tech-cdk.md](../../../../.kiro/steering/tech-cdk.md)

***

## 0. ステージ判定

| 項目                     | 判定                                                                                                     |
| ---------------------- | ------------------------------------------------------------------------------------------------------ |
| Functional Design 実行判定 | **EXECUTE（軽量）** — Unit-1 は基盤 Unit でビジネスロジックは薄いが、認証 / Telemetry / Shared 層のインターフェース設計は他 Unit の前提となるため必須 |
| 深さレベル                  | **Standard** — 過剰な詳細は不要だが、API Authorizer 方式 / Telemetry 投入経路 / Shared パッケージング戦略は他 Unit の実装に直結          |
| Part 1 の目的             | 設計判断ポイントを `[Answer]:` タグで投げ、確定内容を Part 2 で具体的な仕様書に展開                                                   |
| Part 2 の目的             | 確定後に各コンポーネントの IO / 状態 / エラー / イベント仕様を Markdown 化、`shared/schema/` のスケルトン作成計画を提示                        |

***

## 1. Unit-1 のスコープ再確認

### 1.1 Mobile 層（`mobile/src/features/platform/`）

| ID   | コンポーネント     | 主な責務                                        |
| ---- | ----------- | ------------------------------------------- |
| M-01 | `AppShell`  | アプリのルートレイアウト、タブナビゲーション、グローバル状態の Provider 配置 |
| M-12 | `ApiClient` | REST API ラッパー、認証ヘッダ付与、相関 ID 付与、エラーハンドリング    |
| M-13 | `Telemetry` | クライアントイベント計測、`/v1/telemetry` への送信           |

### 1.2 Backend 層

| ID   | コンポーネント                     | 主な責務                                       |
| ---- | --------------------------- | ------------------------------------------ |
| B-12 | `AuditLogger`（ライブラリ）        | 構造化ログ、相関 ID 伝搬、PII マスキング                   |
| B-14 | `TelemetryIngestionService` | `/v1/telemetry` 受信 → Kinesis Firehose → S3 |

### 1.3 Shared 層（`shared/`）

| ID   | コンポーネント              | 主な責務                                                                                                                     |
| ---- | -------------------- | ------------------------------------------------------------------------------------------------------------------------ |
| S-01 | `AsinExtractor`      | URL から ASIN を正規表現抽出（Mobile / Backend で共有）                                                                                |
| S-02 | `SchemaRegistry`     | OpenAPI 3.1 + 自動生成の TypeScript / Python 型                                                                                |
| S-03 | `SafeguardPolicy`    | 月間上限・冷却モード・負債検知のルール定数 + 判定関数                                                                                             |
| S-04 | `TelemetryContracts` | Telemetry イベント型定義（[api-contracts.md §12](../../../../.kiro/steering/api-contracts.md#12-クライアントテレメトリスキーマ-i-1--a-確定) 確定済み） |

### 1.4 Infra 層（`infra/lib/platform-stack.ts`）

| 項目          | 内容                                                                       |
| ----------- | ------------------------------------------------------------------------ |
| ネットワーク      | VPC（subnet 構成は Q5 で決定）、Security Group、NAT Gateway                        |
| API Gateway | REST API、Cognito Authorizer、`/v1/...` ベースパス                              |
| 認証基盤        | Cognito User Pool、TOTP MFA 設定、PostConfirmation Lambda                    |
| データ層共通      | DynamoDB GSI 設計の方針、ElastiCache Redis（Cluster mode）、OpenSearch Serverless |
| セキュリティ      | KMS キー、Secrets Manager、SSM Parameter Store の階層                           |
| 監視          | CloudWatch Logs（I-2 で raw のみ確定）、IAM ロール基本セット                             |

***

## 2. 設計判断ポイント（Part 1 の質問）

各設問は推奨案 + 根拠付きの選択肢で構成。`[Answer]:` タグに回答してください。

***

### Q1. Cognito User Pool の MFA 強制範囲

**背景**: 要件書 §6.4 SECURITY-04 で TOTP MFA を要求。dev 環境と prd 環境で MFA 強制度を変えるかが未確定。

**選択肢**:

* **A. dev = 任意、prd = 強制** — 開発中は MFA 設定を後回しできる。テストアカウント作成が速い。決勝向け prd では強制

* **B. dev = 強制、prd = 強制** — 全環境で MFA 強制。本番環境と同一の動作確認が dev で可能、テストカバレッジが高い

* **C. dev = 任意、prd = 任意** — MFA は完全任意。要件書 SECURITY-04 違反のリスクあり、不採用候補

**推奨**: **A**。理由 — (1) 4 名チームで dev のテストアカウントを毎回 TOTP 設定するのは時間効率が悪い、(2) prd では確実に MFA 強制すれば SECURITY-04 を満たす、(3) MFA 関連 UI / フロー（Recovery Code 含む）は dev でも任意設定で動作確認可能、(4) 予選デモは dev 相当の環境で実施するため任意設定の方がスムーズ。

\[Answer]:A

***

### Q2. API Gateway Authorizer 方式

**背景**: 全エンドポイントで Cognito JWT 検証が必要。API Gateway の Authorizer 種別を選定する。

**選択肢**:

* **A. Cognito Authorizer 単独** — API Gateway 標準の Cognito Authorizer。設定が最も簡単、JWT 検証は API Gateway が代行、Lambda は `event.requestContext.authorizer.claims` から `sub` を取得するだけ

* **B. Lambda Authorizer 単独** — Lambda で JWT 検証 + Safeguard 判定 + リクエスト改竄チェック等を一箇所に集約。柔軟性最大、ただし全リクエストで Lambda コールドスタートのリスク

* **C. ハイブリッド: Cognito Authorizer（基本）+ Lambda Authorizer（Safeguard 適用エンドポイントのみ）** — 通常 API は Cognito Authorizer で軽量、Unit-7 Safeguard が介入する Amazon 遷移系（FR-CART / FR-REEL の Special Link 生成）のみ Lambda Authorizer

* **D. その他**

**推奨**: **C ハイブリッド**。理由 — (1) Cognito Authorizer は無料 + 高速で大半の API に最適、(2) Safeguard はカート介入 / リール → Amazon 遷移の前段で必須なので Lambda Authorizer に集約するのが自然（Unit-7 と整合）、(3) 過半のエンドポイントで Lambda コールドスタートを避けられる、(4) Lambda Authorizer のキャッシュを 5 分有効化すればコールドスタート影響は最小化。

\[Answer]:C

***

### Q3. Telemetry 投入の同期 / 非同期

**背景**: M-13 Telemetry が `/v1/telemetry` にイベントを送信し、B-14 が Kinesis Firehose 経由で S3 に保存する。Mobile からの送信タイミングと、B-14 内の処理を同期/非同期どうするか。

**選択肢**:

* **A. Mobile 単発送信 + B-14 同期書き込み（Firehose PutRecord）** — シンプル、ただしイベント数が多いとコスト・性能ともに不利

* **B. Mobile 5 件バッファ + B-14 PutRecordBatch（同期、Firehose 内部バッファで実質非同期）** — 5 件溜まるか 10 秒経過で送信、B-14 は Lambda 内で Firehose を同期呼び出し → Firehose の内部バッファ（60s/5MiB）で S3 投入

* **C. Mobile 単発送信 + B-14 受信即 SQS 投入 → SQS Consumer Lambda が Firehose 投入** — 完全分離、Firehose 障害時の再送可能（SQS 14 日保持 + DLQ）、ただし SQS 追加コスト + 実装工数 +1d

* **D. その他**

**推奨**: **B + 安全装置 3 点**。理由 — (1) ハッカソン規模（10〜10K DAU）で性能限界は 100K DAU 以降にしか出ない（Firehose 5K records/sec / Lambda 1K concurrent）、(2) C は実装工数 +1d / 運用複雑度増、(3) B → C の移行は 0.5〜1d で可能（Mobile 変更ゼロ、Lambda 内部のみ）、(4) 安全装置 3 点で B の最大の弱点（Firehose 一時障害時の欠損）を緩和、(5) 性能限界 / 欠損率が顕在化したら C に切替（backlog で trigger 管理）。

**安全装置 3 点（B 採用の必須条件）**:

1. **Idempotency Key 対応**: Mobile が 5 件 batch ごとに UUID v7 ベースの `batch_id` を `Idempotency-Key` ヘッダで送付。B-14 は ElastiCache（1 時間 TTL）で重複検知 → POST のリトライ安全化。Q7=B の例外として Telemetry POST は冪等キー込みでリトライ可
2. **Lambda DLQ**: B-14 Lambda の DLQ を SQS で設定（CDK 5 行）、Lambda 失敗時に自動退避 → 復旧後に手動 / バッチで Firehose リプレイ
3. **B → C 移行トリガー**: [doc/backlog.md](../../../../doc/backlog.md) に B-201 として登録、以下のいずれか 1 つで C 移行検討:

   * 平均 events/sec > **100**（〜50K DAU 相当）が連続 1 週間

   * Telemetry 欠損率 > **0.1%** が観測された

   * Firehose 障害 1 回でも顕在化した

   * 決勝後にプロダクト化判断が下された

\[Answer]:**B + 安全装置 3 点（Idempotency Key + Lambda DLQ + backlog B-201 で C 移行トリガー記録）**

***

### Q4. Shared 層パッケージング戦略

**背景**: `shared/schema/` / `shared/asin-extractor/` / `shared/safeguard-policy/` / `shared/telemetry-contracts/` を Mobile / Backend / Infra が参照する。モノレポでどう管理するか。

**選択肢**:

* **A. npm workspaces** — 公式、Node 16+ で標準。`package.json` に `"workspaces": ["mobile", "infra", "shared/*"]` を書くだけ。Python 側は `pyproject.toml` の `path = "../shared/asin-extractor"` 等で参照

* **B. pnpm workspaces** — 高速、ディスク効率良好。ただし pnpm 自体の追加学習コスト、Expo / EAS との相性確認が必要

* **C. yarn workspaces (v1)** — 安定、ただし Yarn 自体が現在は v3+ Berry 系がメイン。v1 は legacy

* **D. ローカル symlink + 個別 package** — workspaces を使わず、`mobile/node_modules/@yudane/asin-extractor` のような symlink で参照

* **E. その他**

**推奨**: **A npm workspaces**。理由 — (1) Expo SDK 52 + EAS Build が npm workspaces に対応している（pnpm は要追加設定）、(2) チーム全員が npm に慣れている前提、(3) lockfile が `package-lock.json` 1 つで完結、(4) Python 側は Poetry の `[tool.poetry.dependencies]` で `path = "../shared/..."` の dev dep として参照、(5) CDK も Node プロジェクトなので同じ workspaces に乗る。

\[Answer]:A

***

### Q5. VPC 構成（Lambda VPC 配置の有無）

**背景**: Lambda を VPC 内に配置すると ENI 起動でコールドスタートが遅くなる（Hyperplane ENI で改善されたが完全ゼロではない）。一方、ElastiCache Redis / OpenSearch Serverless へのアクセスには VPC が（条件付きで）必要。

**ElastiCache Redis / OpenSearch Serverless の存在理由**:

* **ElastiCache Redis**:

  1. Amazon Creators API 商品メタキャッシュ（TTL 6h）— Creators API のレート制限（1 req/sec 想定）回避が主目的、ヒット率 95% で API コール 1/20 に削減
  2. 論破 / リール / カートのレート制限（FR-DEBATE-05 クールダウン等）— 原子的 INCR で 5ms 完結
  3. 論破ストリーミング中のコンテキストキャッシュ（嗜好ベクトル / 直近テレメトリ）— DynamoDB 直接参照より 200ms 短縮

* **OpenSearch Serverless**:

  * リール推薦（UC-02 / B-03 ReelRecommendationService）の k-NN ベクトル検索専用

  * 1024 次元の HNSW インデックスで 50ms 未満の類似度検索、DynamoDB / RDS では 10 万件規模で破綻

**VPC 要件**:

* **ElastiCache**: VPC 必須（パブリックアクセス不可、AWS 仕様）

* **OpenSearch Serverless**: パブリックエンドポイント + IAM 認証も可（ハッカソン期間はパブリック採用、VPC 化は backlog）

**選択肢**:

* **A. 全 Lambda を VPC 配置**（subnet = private with NAT） — シンプル、ElastiCache / OpenSearch にアクセス可能。コールドスタート 100-300ms 増、不要 Lambda にも VPC オーバーヘッド

* **B. 必要な Lambda のみ VPC 配置、それ以外（Cognito Trigger / Telemetry / Auth 等）はパブリック** — コールドスタート最小化、Lambda が 2 種類になり管理コスト微増

* **C. ElastiCache を Layer 経由でアクセス**（過剰技巧） — 不採用候補

* **D. ElastiCache 自体を別技術に変更**（要件書 §7 の構成変更に該当、要承認） — 不採用候補

**検討プロセス（Decision Record）**:

#### 段階 1: B 案を起点に深掘り — B-02 DebateLlmService の問題

B 案で B-02 を考えると、Bedrock 呼び出し + Redis 呼び出しの両方が必要なため VPC 配置となり、論破ストリーミングのコールドスタートが要件「初回トークン 3 秒以内」（要件書 §6.3）に影響する懸念が浮上。

#### 段階 2: B-02 が Redis を欲しがる用途を分解

B-02 が Redis を呼ぶのは以下 2 用途のみ（商品メタキャッシュは B-11 が独立 Lambda として持つため B-02 不要）:

1. 論破レート制限（FR-DEBATE-05、原子的カウンタ）
2. 論破ストリーミングのコンテキストキャッシュ

#### 段階 3: B-02 を VPC から抜く 4 案の比較

| 案                                               | アプローチ                                                        | 工数   | 効果 | 影響範囲                                               |
| ----------------------------------------------- | ------------------------------------------------------------ | ---- | -- | -------------------------------------------------- |
| **A. B-02 だけ DynamoDB 化**                       | Redis 2 用途を DynamoDB の `UpdateItem` `ADD` 操作 + `GetItem` で代替 | 30 分 | ◎  | services.md / component-methods.md（小）              |
| B. Lambda 分割（context Lambda + streaming Lambda） | B-02 を VPC 内 / VPC 外の 2 Lambda に分離                           | 1d   | ◎  | API 契約 + Mobile + 設計（中）                            |
| C. Provisioned Concurrency                      | VPC 内維持、コールドスタート緩和                                           | 5 行  | △  | なし、ただし月 \$11-15                                    |
| D. 全 Redis 廃止                                   | 要件書改訂で全コンポーネントを DynamoDB 化                                   | 0.5d | ◎  | requirements.md / Application Design（大、書類審査整合性リスク） |

→ **A 採用**（最小工数 + 影響最小 + 他コンポーネント無影響）

#### 段階 4: コールドスタートの定量比較（出典: AWS 公式 / 業界ベンチマーク 2025）

| 構成                           | warm  | cold（ENI 既存） | cold（ENI 新規 = 初回 1 回）        |
| ---------------------------- | ----- | ------------ | ---------------------------- |
| **A 採用（B-02 = VPC 外、DDB 化）** | 205ms | 400-700ms    | 400-700ms（ENI 不要）            |
| VPC 内維持                      | 201ms | 500-900ms    | **3-10 秒**（一度きりだがデモで起きると致命的） |

→ 定常時の差は誤差レベル（数 ms）だが、ENI 新規作成リスクの完全回避と将来の SnapStart 適用余地で A が勝る

#### 段階 5: コールドスタート完全緩和の選択 — Provisioned Concurrency vs SnapStart

| 方式                                       | 月額（apne1 / Python 3.13 / 1024MB） | コールドスタート短縮                        | YUDANE 要件達成 |
| ---------------------------------------- | -------------------------------- | --------------------------------- | ----------- |
| 何もしない                                    | \$0                              | なし、500-900ms                      | ✅（要件 30%）   |
| **SnapStart（Python）**                    | **\$0（追加料金なし）**                  | snapshot restore で 〜300-400ms に短縮 | ✅（要件 13%）   |
| Provisioned Concurrency 1 並列             | \$11-15                          | warm 維持で 0ms                      | ✅（要件 7%）    |
| SnapStart + Provisioned Concurrency 1 並列 | \$11-15                          | 0-300ms                           | ✅（最強）       |

Python SnapStart は 2024-11 GA、2025-06 で apne1（東京）含む 23 リージョン拡大、**Java と異なり追加料金なし**（[公式案内](https://aws.amazon.com/about-aws/whats-new/2024/11/aws-lambda-snapstart-python-net-functions/)、Content was rephrased for compliance with licensing restrictions）。

→ **SnapStart 単独採用**（コスト ゼロ + 要件達成余裕 + 決勝デモ前に Provisioned Concurrency を保険追加できる柔軟性を保つ）

**確定方針（A + B-02 DDB 化 + SnapStart）**:

> ⚠️ **セルフレビュー後修正（2026-05-27）**: 当初の確定方針では B-09 SafeguardRulesEngine を VPC 内に配置していたが、論破ストリーミングの Lambda Authorizer が B-09 を呼び出すため、Q5 で B-02 を VPC 外に出した利益（コールドスタート最小化）が部分的に相殺される矛盾を検出。**B-09 も VPC 外に変更**し、Lambda Authorizer 内に S-03 SafeguardPolicy を直接 import + DDB 直接参照で完結する設計に修正。VPC 内 Lambda は B-03 / B-11 / B-14 の **3 つに限定**。詳細は [functional-design.md §3.1 / §4.2](./functional-design.md#3-infrastructure-配置マトリクスq5-反映) を参照。

* **VPC 配置 Lambda**（セルフレビュー後 = 3 つ）: B-11 CreatorsApiClient（Redis 6h キャッシュ）/ B-03 ReelRecommendationService（OpenSearch アクセス、ただし VPC は任意で初期はパブリック + IAM 認証）/ B-14 TelemetryIngestionService（Redis Idempotency 検知）

* **VPC 外 Lambda**: B-01 AuthEdgeLambda / B-02 DebateLlmService（DDB 化により Redis 不要、SnapStart 有効）/ **B-09 SafeguardRulesEngine（セルフレビュー後修正、S-03 直接 import + DDB 直接参照、Lambda Authorizer に統合）** / B-13 AmazonTransitionRecorder / B-10 AssociatesLinkGenerator

* **OpenSearch Serverless**: パブリックエンドポイント + IAM 認証（VPC 化は backlog 化）

* **B-02 SnapStart 設定**: CDK で `snapStart: lambda.SnapStartConf.ON_PUBLISHED_VERSIONS` + `currentVersion` 公開 + `Alias` 設定必須

* **B-02 の DDB スキーマ追加**:

  * `DebateRateLimits` テーブル: `PK = USER#{userId}`, `SK = DEBATE_RATE#{hour}`, `attempts: number`, TTL 1h

  * `DebateContexts` テーブル（既存 Users / PreferenceVectors を流用、TTL 5min キャッシュは Lambda メモリ内で代替も検討）

* **Provisioned Concurrency**: 不採用（決勝デモ前の保険として backlog 登録、6/15 以降に再評価）

**ドキュメント影響**:

* `services.md` SVC-01 論破サービス: コンテキスト供給を「Redis → DynamoDB（B-02 のみ）」に修正

* `component-methods.md` B-02: `estimate_stress_level()` / `start_debate()` の Redis 参照を DynamoDB に置換、SnapStart Hook（`@register_after_restore`）の例追加

* `components.md` B-02 説明: 補足追記（B-02 単独では Redis 非依存、SnapStart 適用）

* `tech-cdk.md` §3 推奨パターン: SnapStart 適用ルール追加（要対応、Part 2 で実施）

* `doc/backlog.md`: B-202 として「Provisioned Concurrency の決勝デモ前再評価」を記録

**SnapStart 適用時の注意**:

* B-02 でランダム値 / 一意性のある初期化があれば SnapStart Hook で再生成（`@register_after_restore`）

* `$LATEST` バージョンでは無効、必ず公開バージョン + Alias で運用

* VPC 内 / 外どちらでも適用可能、本案では VPC 外 + SnapStart の組み合わせで効果最大化

\[Answer]:**B（必要な Lambda のみ VPC）+ B-02 だけ DynamoDB 化（VPC 不要に変更）+ B-02 に SnapStart 有効化、Provisioned Concurrency は不採用（決勝前再評価を backlog B-202 で記録）**

***

### Q6. DynamoDB テーブル設計の方針

**背景**: 要件書 §7 で「生 DynamoDB」と確定、Amplify Data は不採用。Single Table Design vs Multi Table Design は未決定。

**選択肢**:

* **A. Single Table Design（DynamoDB ベストプラクティス）** — 1 テーブルで全ドメインを管理、PK / SK / GSI で表現。クエリ性能高、ただし設計とドキュメンテーションコストが高い

* **B. Multi Table Design（ドメインごとに 1 テーブル）** — `Users` / `CartWatchItems` / `DebateSessions` / `WeeklyReports` 等で分離。設計が直感的、Unit ごとに owner が明確、ただしテーブル間 JOIN は Application 側で実装

* **C. ハイブリッド: コアエンティティ（User + UserActivity）は Single Table、独立性が高いもの（CartWatchItems / WeeklyReports）は別テーブル**

**推奨**: **B Multi Table Design**。理由 — (1) Unit ごとに owner が明確（Unit-2 = Users / Unit-5 = CartWatchItems / Unit-8 = WeeklyReports）、(2) Single Table の設計には DynamoDB 上級者の継続的な監修が必要だがハッカソン期間では負担、(3) コスト最適化は Multi Table でも GSI 設計で十分対応可能、(4) Schemathesis / 契約テストの観点でもテーブル単位の責任が明確、(5) Single Table の優位性は数千万件規模で出るが、ハッカソン規模では差が出ない。

\[Answer]:B

***

### Q7. M-12 ApiClient のリトライ / バックオフ戦略

**背景**: ネットワーク不安定時の挙動を統一する。

**選択肢**:

* **A. 全エンドポイントに統一リトライ（最大 3 回、指数バックオフ 500ms / 1000ms / 2000ms）** — シンプル、ただし冪等性のない POST に副作用を起こすリスク

* **B. GET / DELETE のみリトライ、POST / PATCH は冪等キー（`Idempotency-Key`** **ヘッダ）必須でリトライ可** — 安全、ただし全 POST に冪等キー実装が必要

* **C. リトライなし、エラーは即 UI に通知** — 最もシンプル、ただし UX 悪化の可能性

* **D. その他**

**推奨**: **B**。理由 — (1) GET / DELETE は冪等なのでリトライ安全、(2) POST のリトライは Telemetry 重複や論破セッション重複生成のリスク、(3) 冪等キーは Backend 側で 5 分間 DynamoDB 保持で重複検知、(4) `/v1/cart-watch-items POST`（重複登録防止）/ `/v1/debate-sessions POST`（セッション 1 件保証）等で特に必要。

\[Answer]:B

***

### Q8. M-13 Telemetry のオフライン挙動

**背景**: Q3 で B = 「Mobile 5 件バッファ + B-14 非同期」を推奨。オフライン時の永続化方針が未確定。

**選択肢**:

* **A. AsyncStorage に永続キュー、起動時 / オンライン復帰時に flush** — 標準的、起動時のみ flush なら実装シンプル

* **B. SQLite ローカル DB に永続キュー、定期的 flush（30 秒間隔）** — より堅牢、ただし SQLite 依存追加

* **C. 永続化なし、オフライン中は破棄** — 軽量、ただしテレメトリ欠損

* **D. その他**

**推奨**: **A**。理由 — (1) Expo `@react-native-async-storage/async-storage` で実装簡単、(2) 永続キューサイズ上限 1000 件で十分（オフラインが長時間続く想定外）、(3) SQLite は Reel の嗜好キャッシュ等で必要になれば後付け、(4) 起動時 flush + 5 分タイマー flush の 2 段で実用上十分。

\[Answer]: A

***

### Q9. OpenAPI 第 1 版に含めるエンドポイント

**背景**: [api-contracts.md §1.1](../../../../.kiro/steering/api-contracts.md) で「28 ストーリーから派生する MVP エンドポイントのみ」と確定済みだが、具体的なエンドポイント網羅範囲を Q9 で確定。

**選択肢**:

* **A. コア 3 UC（UC-01 論破 / UC-02 リール / UC-03 カート介入）+ Auth + Telemetry のみ** — 予選 5/30 までに必要な最小構成、Unit-2/3/4/5 が並行着手可能

* **B. A + Calendar（UC-04）+ Safeguard（UC-08） を含む 7 UC 全部** — 決勝も視野、ただし 28 エンドポイントを Day 4 までに整備するのは Member A の負担増

* **C. A + Safeguard のみ追加（Calendar は Unit-6 着手時に追加）** — Safeguard は middleware として全エンドポイントに影響するため第 1 版必須、Calendar は後付け

* **D. その他**

**推奨**: **C**。理由 — (1) Safeguard authorizer は Unit-3/4/5 の API に middleware として組み込まれるため第 1 版から含める必要、(2) Calendar API は Unit-6（Member B 後半）で追加すれば良い、(3) Day 3 凍結に間に合う現実的な範囲（予選デモ当日 Day 4 = 5/30 の負荷回避のため前倒し、詳細は [openapi-skeleton-plan.md §1.1](./openapi-skeleton-plan.md)）、(4) 第 1 版凍結後の Calendar / Report エンドポイント追加は契約 PR で対応。

\[Answer]:B

***

### Q10. CI セットアップのスコープ（Unit-1 で何処までやるか）

**背景**: I-4 で確定した CI/CD パイプラインのうち、Unit-1 Platform でどこまでセットアップするか。

**選択肢**:

* **A. CI（lint + test + sbom）+ deploy-dev のみ Unit-1 で完成** — 予選までに必要な範囲、deploy-prd は決勝前準備で追加

* **B. A + deploy-prd も Unit-1 で完成** — 完全自動化、ただし prd 環境は実際にデプロイするのが決勝前なので未検証期間が長い

* **C. CI（lint + test）のみ、deploy はローカル** **`cdk deploy`** **で運用** — 最速、ただし I-4 確定（A: 推奨どおり）と矛盾

* **D. その他**

**推奨**: **A**。理由 — (1) I-4 確定方針と整合、(2) Unit-1 は基盤 Unit なので CI セットアップに集中する責任、(3) deploy-prd は決勝前 1 週間（6/15〜）で Member A が追加、(4) Unit-1 完了時点で develop ブランチへの push が dev 環境にデプロイされる状態になる。

\[Answer]:A

***

## 3. 回答後のアクション（Part 2 Generation で実施）

全 Q1〜Q10 の `[Answer]:` が埋まったら、以下を順次実行する。

1. **回答内容の解析**

   * 矛盾・曖昧さがあれば追加質問（Step 5 in functional-design.md と同様）

2. **Part 2 Generation: Functional Design ドキュメント生成**

   * `aidlc-docs/construction/unit-1-platform/functional-design/functional-design.md` — Mobile / Backend / Shared / Infra 各層の IO / 状態 / エラー仕様を明文化

   * `aidlc-docs/construction/unit-1-platform/functional-design/data-model.md` — Multi Table Design の主要テーブル設計、PK / SK / GSI 定義

   * `aidlc-docs/construction/unit-1-platform/functional-design/sequence-diagrams.md` — 認証 / Telemetry / Safeguard middleware の Mermaid sequence diagram

3. **`shared/schema/openapi.yaml`** **第 1 版スケルトン作成計画**

   * Member A の Day 1 タスクとして `paths/auth.yaml` / `paths/debate.yaml` / `paths/reel.yaml` / `paths/cart.yaml` / `paths/safeguard.yaml` / `paths/telemetry.yaml` の 6 ファイルスケルトン

   * `components/schemas/User.yaml` / `ProblemDetails.yaml` / `TelemetryEvent.yaml` の共通モデル

4. **Part 2 完了後の承認ゲート → NFR Requirements ステージへ移行**

***

## 4. ハッカソン書類審査・予選評価軸へのインパクト

| 評価軸                | 本ドキュメントの貢献                                                                |
| ------------------ | ------------------------------------------------------------------------- |
| ビジネス意図の明確さ         | （直接貢献なし、基盤 Unit のため）                                                      |
| Unit 分解の適切さ        | **強化**: Unit-1 が他全 Unit のインターフェースを定義することを明示、依存関係が技術仕様レベルで具体化              |
| 創造性とテーマ適合性         | （直接貢献なし）                                                                  |
| ドキュメント品質           | **強化**: Functional Design 設計判断が `[Answer]:` タグで documented decision として残る |
| AI-DLC プロセス（予選評価軸） | **強化**: Per-Unit Loop の最初のステージを正規手順で実施、後続 Unit のテンプレートになる                 |
