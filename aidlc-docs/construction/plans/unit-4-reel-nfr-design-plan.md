# Unit-4 Reel — NFR Design Plan

> Construction Phase / Per-Unit Loop / Unit-4 Reel の非機能設計（NFR Design）計画。NFR Requirements を設計パターン + 論理コンポーネントに落とし込む。
> 参照: [NFR Requirements](../reel/nfr-requirements/) / [Functional Design](../reel/functional-design/) / [Unit-1 NFR Design](../unit-1-platform/nfr-design/) / [tech.md](../../../.kiro/steering/tech.md)
> 作成: 2026-05-30 / ステージ: 🟢 CONSTRUCTION / NFR Design / 担当: Member C

---

## 0. 位置づけ（Unit-4 の NFR Design スコープ）

NFR Requirements で確定した品質目標（フィード p95 800ms / 遷移 p95 400ms / graceful degradation / fail-closed / PBT 割当 / 観測 / A11y）を、**設計パターン**（resilience / scalability / performance / security）と **論理コンポーネント**（cache / adapter / gate / queue 等）に落とし込む。

Unit-1 が確立した横断パターン（PAT-RESIL-01 リトライ / PAT-PERF-01 Request Policy / PAT-SEC-01 Authorizer+sub 照合 / PAT-SEC-04 Rate Limit / PAT-OBS-01 Metric Facade 等）は **継承** し、Unit-4 は固有パターン（推薦・カタログ・遷移・ラベル生成・ブースト）を上乗せする。物理インフラ（OpenSearch / ElastiCache ノード / Lambda メモリ / VPC / IAM）は次の **Infrastructure Design** で確定する。

---

## 1. 設計判断のための質問

以下の質問に `[Answer]:` タグで回答してください（推奨は **A**）。回答完了後「done」等でお知らせください。曖昧な回答が残る場合は follow-up clarification を作成します。

### Question 1（Resilience: カタログ取得の縮退）
ALG-CATALOG の **外部 API 障害時の縮退パターン**をどう設計しますか？（NFR-AVAIL-01、Q7=A のポート/アダプタ + キャッシュ前提）

A) **Cache-aside + Stale-on-error + アダプタ別タイムアウト**: ① 通常はキャッシュ参照→ミスでアダプタ呼出→put（cache-aside）② Creators API 失敗時は **期限切れキャッシュがあれば stale を返す（stale-while-error）**、無ければダミーカタログにフォールバック ③ アダプタ呼出に短いタイムアウト（例 2s）を設け、フィード全体のレイテンシ予算（p95 800ms）を守る — 推奨（フィードが落ちない）
B) Cache-aside のみ（失敗時は即フォールバックせず DomainError をフィードに伝播）。実装は単純だがデモでフィードが空になりうる
X) Other（[Answer]: の後に記述）

[Answer]: A

### Question 2（Resilience: ラベル/コピー LLM 生成）
ALG-PITCH/LABEL の **Bedrock LLM 呼び出しのレジリエンス**をどう設計しますか？（NFR-AVAIL-03、Q4=A のテンプレートフォールバック前提）

A) **タイムアウト + フォールバック + 任意の事前生成**: ① LLM 呼出にタイムアウト（例 1.5s）② タイムアウト/失敗/モデレーション拒否で決定論テンプレートにフォールバック ③ フィード生成のレイテンシ予算を守るため、ラベル生成は**カードごと並列**実行 ④（決勝向け任意）人気商品のラベルを事前生成キャッシュ — 推奨
B) LLM を同期直列呼び出し（カードごとに順次）。実装単純だが 10 枚で遅延が累積し p95 を超える
X) Other（[Answer]: の後に記述）

[Answer]: A

### Question 3（Performance: フィード生成のレイテンシ予算配分）
フィード生成（ALG-RANK 全体）の **レイテンシ予算の配分と最適化**をどうしますか？（NFR-PERF-01 = p95 800ms）

A) **段階別予算 + ラベル生成の非ブロッキング化**: 候補取得（カタログ）≤ 300ms / リランク（インメモリ純関数）≤ 50ms / ラベル・コピー生成 ≤ 350ms（並列）+ 余裕。ラベル生成が予算を超える場合は**先にカードを返してラベルは後追い（プレースホルダ → 差し替え）も許容**。リランク・ブーストは純関数のため最適化不要 — 推奨
B) 全部同期で組み立ててから返す（シンプルだが LLM ラベルが律速、p95 リスク）
X) Other（[Answer]: の後に記述）

[Answer]: A

### Question 4（Performance/Scalability: キャッシュ階層）
カタログ・推薦の **キャッシュ階層**をどう設計しますか？（NFR-PERF-06 / NFR-SCALE-04、Redis TTL 6h 前提）

A) **2 層キャッシュ（商品メタ = Redis 共有 / 候補リスト = 短 TTL）**: ① 商品メタ（ASIN→ProductMeta）は ElastiCache Redis に TTL 6h（B-11、全 Unit 共有）② ユーザー別の推薦候補リストは短 TTL（例 60〜120s）でフィード連打のスパイクを吸収（任意、決勝で調整）③ ダミーカタログはインメモリ/同梱 JSON — 推奨
B) 商品メタ Redis キャッシュ（6h）のみ。候補リストはキャッシュしない（毎回再計算、MVP は十分）
X) Other（[Answer]: の後に記述）

[Answer]: A

### Question 5（Security/Resilience: 遷移の冪等性 + Safeguard ゲート実装パターン）
ALG-TRANSITION の **冪等書き込み + Safeguard ゲートの実装パターン**をどう確定しますか？（NFR-PERF-04 = p95 400ms、Q2/Q6=A）

A) **条件付き書き込み + トランザクション + 先行ゲート**: ① Safeguard 判定は遷移 Lambda 冒頭で S-03 を同期評価（block なら 409、取得失敗は fail-closed）② 記録は DynamoDB `TransactWriteItems` で「遷移記録の put（条件: clientTransitionId 未登録）+ 月間カウント increment + EXP increment」を原子的に ③ 冪等キー重複は条件式違反で検知し `duplicate=true` を返す ④ EXP の B-08 供給は非同期（イベント or 後続バッチ）— 推奨
B) アプリ層で read→check→write（条件付き書き込みを使わない）。競合で二重計上リスク
X) Other（[Answer]: の後に記述）

[Answer]: A

### Question 6（Scalability: 深夜帯スパイク + Lambda コールドスタート）
深夜帯（22〜2 時）のアクセス集中（US-02-01）への **スケール・コールドスタート対策**をどうしますか？（NFR-SCALE-01）

A) **On-Demand + SnapStart（B-03/B-13）+ Provisioned は backlog**: ① DynamoDB On-Demand でスパイク吸収 ② フィード/遷移 Lambda は VPC 外配置 + SnapStart でコールドスタート短縮（Unit-1 B-02 と同方針）③ Provisioned Concurrency は決勝判断（コスト発生のため backlog）④ Redis キャッシュで Creators API レート制限を吸収 — 推奨
B) 特別な対策なし（AWS 既定のオートスケールに委ねる）。深夜スパイクでコールドスタート多発の体感劣化リスク
X) Other（[Answer]: の後に記述）

[Answer]: A

### Question 7（Logical Components: OpenSearch を見据えた推薦の論理分離）
MVP（購入履歴ヒューリスティック）と決勝（ベクトル検索 B-204）の **推薦の論理コンポーネント分離**をどうしますか？

A) **`RecommendationStrategy` ポートで候補生成を抽象化**: 候補生成段を `CandidateSourcePort`（入力: ctx → 出力: 候補）として抽象化し、MVP は `PurchaseHistoryHeuristicSource`、決勝は `VectorSearchSource`（Titan + OpenSearch）を差し替え。リランク（ALG-RANK ステップ3 以降）は候補ソース非依存で共通 — 推奨（B-204 導入が非破壊、ALG-CATALOG のポート/アダプタと一貫）
B) MVP のヒューリスティックを直書きし、決勝でリファクタ（B-204 導入時に書き換えコスト）
X) Other（[Answer]: の後に記述）

[Answer]: A

### Question 8（Security: モデレーション + Special Link のパターン）
NG-6/NG-8 の **モデレーションと Special Link 安全策のパターン**をどう設計しますか？（NFR-SEC、Q8=A）

A) **出力モデレーションパイプライン + リンク生成の純関数ガード**: ① LLM 出力（pitch/label）は生成後に `moderate()`（禁止表現の正規表現/分類 + 必要なら Bedrock Guardrails）を必ず通し、拒否ならテンプレートへ ② Special Link は純関数 + 環境ガード（dev 仮 / prd 未承認ブロック）+ 短縮禁止の不変条件を単体で検証 ③ Creators/Associates 認証情報は Secrets Manager 参照（実行時取得、ハードコード禁止）— 推奨
B) モデレーションは LLM プロンプト内の指示のみに任せる（出力後チェックなし）。NG-6 すり抜けリスク
X) Other（[Answer]: の後に記述）

[Answer]: A

### Question 9（Observability: Reel メトリクスの実装パターン）
NFR-OBS の **Reel メトリクス/テレメトリの実装パターン**をどうしますか？（Unit-1 PAT-OBS-01 Metric Facade 継承）

A) **クライアント = M-13 track / サーバー = B-12 metric Facade の二経路 + S-04 カタログ追記**: ① クライアントイベント（reel.viewed/swiped/double_tap/amazon_tap/boost_shown/label_fallback）は M-13 経由 ② サーバーメトリクス（フィードレイテンシ/キャッシュヒット率/遷移 409 率）は B-12 `metric()`（EMF）③ `reel.*` 命名・PII 非含・低カーディナリティ次元を S-04 TelemetryContracts に追記 — 推奨
B) クライアント計測のみ（サーバーメトリクスは決勝で追加）。レイテンシ/キャッシュの可視化が遅れる
X) Other（[Answer]: の後に記述）

[Answer]: A

### Question 10（Performance: モバイル 60fps の実現パターン）
M-03 ReelScreen の **60fps スクロール + ジェスチャーの実現パターン**をどうしますか？（NFR-PERF-03）

A) **仮想化リスト + UI スレッドジェスチャー + 画像最適化**: ① 縦型ページングは仮想化リスト（FlashList 優先、FlatList フォールバック）でオフスクリーン破棄 ② ジェスチャーは react-native-gesture-handler + reanimated で **UI スレッド実行**（JS ブリッジ往復を避ける）③ 画像はサムネ解像度 + プリフェッチ（次カード先読み）④ 誘導アニメ（boostNudge）も reanimated worklet — 推奨
B) RN 標準 FlatList + JS スレッドジェスチャー（実装容易だが 60fps が安定しにくい）
X) Other（[Answer]: の後に記述）

[Answer]: A

---

## 2. 実行ステップ（チェックボックス）

### Part 1: 計画 + 質問（現在地）
- [x] NFR Requirements 成果物の分析（nfr-requirements / tech-stack-decisions 読込）
- [x] NFR Design Plan の作成（本ファイル）
- [x] ユーザーが Q1〜Q10 に回答（全 A 確定）
- [x] 回答の分析・矛盾検出 → 3 件の矛盾を検出し推奨方針で解消（clarification ファイルは作らず本計画に記録）
- [x] ユーザーが矛盾解消方針に同意（「はい」、2026-05-30）

#### 矛盾解消の確定方針（ユーザー同意済み）
1. **VPC 配置の矛盾（Q6 vs Q1/Q4 + services.md）**: 解消案 **(a)** — Redis アクセスを担う **B-11 CreatorsApiClient は VPC 内**に配置し、**B-03/B-13 は VPC 外**（SnapStart）から B-11 を Lambda invoke で呼ぶ。VPC 外で論破/フィード/遷移のストリーミング系を完結させつつ Redis 共有キャッシュの利点を維持（Unit-1 B-02 の VPC 外方針と一貫）
2. **レイテンシ予算とタイムアウトの不整合（Q3 vs Q1/Q2）**: **ソフト期限（予算）とハードタイムアウトを分離**。カタログはキャッシュヒット（Redis 数十 ms）が 300ms 予算の前提、ミス時の外部呼び出しハードタイムアウト 2s は stale 返却/ダミーで予算を死守。ラベルはソフト期限 350ms で打ち切りテンプレートフォールバック（LLM ハードタイムアウト 1.5s は後追いパス採用時のみ）
3. **「ラベル後追い差し替え」が FD と未整合（Q3）**: **MVP は同期生成に統一**（350ms ソフト期限内にテンプレートフォールバックで必ず非空ラベルを返す）。後追い差し替えは FD ドメインモデル（ownershipLabel/pitch は必須・同期）との整合のため採用せず、決勝最適化として backlog 化（[B-205](../../../doc/backlog.md)）

### Part 2: NFR 設計成果物の生成（承認後）
- [x] `aidlc-docs/construction/reel/nfr-design/nfr-design-patterns.md`
  - resilience / scalability / performance / security / observability パターン（Unit-1 継承 + Unit-4 固有）+ パターン依存図
- [x] `aidlc-docs/construction/reel/nfr-design/logical-components.md`
  - 推薦パイプライン / カタログアダプタ + キャッシュ / 遷移ゲート / ラベル生成 / ReelScreen の論理コンポーネントと配置
- [x] 自己レビュー（整合性・要件充足・診断エラー）— diagnostics 0、矛盾 3 件を解消（VPC 境界分離 / レイテンシ soft-hard 分離 / ラベル同期統一 + B-205 backlog）
- [x] 完了メッセージ提示 + 承認ゲート（次ステージ = Infrastructure Design）— 2026-05-30 承認（過剰設計・矛盾 2 件修正後）

---

## 3. Extension 適合の予定（NFR Design 段階での該当性）

| Extension | 本ステージでの扱い |
|---|---|
| SECURITY-08/09/11 | PAT-SEC（Authorizer+sub 照合継承 / fail-closed / レート制限）を Unit-4 の遷移・フィードに適用 |
| NG-6 / NG-8 | 出力モデレーションパイプライン + Special Link 純関数ガードをパターン化（Q8） |
| PBT-02/03/04 | パターンの不変条件（round-trip / 決定論 / 冪等）を logical-components に紐付け |
| SECURITY-07（VPC）/ IAM / Lambda 構成 | Infrastructure Design で物理化（本ステージでは N/A、論理境界のみ） |
