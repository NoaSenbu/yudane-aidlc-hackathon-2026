# Unit-4 Reel — Tech Stack Decisions

> Unit-4 Reel で実体化する技術選定の確定と根拠。要件書 §7 / tech.md / Unit-1 Tech Stack Decisions を Unit-4 の責務に落とし込む。
> 参照: [nfr-requirements.md](./nfr-requirements.md) / [要件書 §7](../../../inception/requirements/requirements.md) / [Unit-1 tech-stack-decisions.md](../../unit-1-platform/nfr-requirements/tech-stack-decisions.md) / [tech.md](../../../../.kiro/steering/tech.md)
> 確定方針: Q1=A / Q2=A / Q3=A / Q4=A / Q5=A / Q6=A / Q7=A / Q8=A / Q9=A / Q10=A

---

## 0. 前提

技術スタックの大枠は要件書 §7 / tech.md / Unit-1 で確定済み。本書は **Unit-4 が実際に導入・設定する具体ライブラリと、Unit-4 固有の技術判断**（MVP の OpenSearch 見送り / Bedrock ラベル生成 / カタログアダプタ / DynamoDB テーブル前提）を確定する。新規スタックの導入はない。

---

## 1. Mobile（M-03 ReelScreen）

| レイヤ | ライブラリ | バージョン方針 | 用途 |
|---|---|---|---|
| フレームワーク | React Native (New Architecture) | 0.76+（Unit-1 継承） | 縦型スワイプ UI（Fabric） |
| 言語 | TypeScript | 5.x strict | M-03 実装 |
| ジェスチャー | react-native-gesture-handler | 最新安定 | 左/右スワイプ・ダブルタップ判定（ALG-GESTURE、Q5=A） |
| アニメーション | react-native-reanimated | 最新安定 | 60fps スクロール / カード遷移（NFR-PERF-03） |
| リスト | FlashList（@shopify/flash-list）or RN FlatList（pagingEnabled） | 最新安定 | 縦型ページング無限スクロール（FR-REEL-01）。選定は Code Generation で性能比較 |
| サーバー状態 | TanStack Query（useInfiniteQuery） | v5（Unit-1 継承、retry=false） | カーソルページング（Q9=A FD / REEL-PAGE） |
| クライアント状態 | Zustand（persist） | 最新安定（Unit-1 継承） | オーバーレイ / 論破不要設定 / 左スワイプ回数 |
| スタイル | NativeWind v4 | 最新安定（tech.md） | テーマトークン（A11y コントラスト継承） |
| PBT | fast-check | 最新安定 | NFR-PBT（カーソル round-trip 等） |

### Unit-4 が確立する Mobile 規約
- ジェスチャー閾値（60px / 350ms / クールダウン 3 回）は設定値カタログ（business-rules §12）で定数管理
- ダブルタップは必ず確認オーバーレイを経る（FR-REEL-05、直接遷移禁止）
- スワイプ操作にボタン代替を併設（NFR-A11Y-01）

---

## 2. Backend（B-03 / B-10 / B-11 / B-13）

| レイヤ | ライブラリ | バージョン方針 | 用途 |
|---|---|---|---|
| ランタイム | Python 3.13（Unit-1 継承） | — | Lambda |
| 観測 | AWS Lambda Powertools (Python) | 最新安定（Unit-1 継承） | Logger / Tracer / Metrics(EMF)。`reel.<verb>` メトリクス（NFR-OBS） |
| バリデーション | Pydantic v2（Unit-1 継承） | — | 入力検証（SECURITY-05）、DTO |
| 型生成 | datamodel-code-generator（Unit-1 継承） | — | reel.yaml → Pydantic |
| AI（ラベル/コピー生成） | Amazon Bedrock **Claude Haiku 4.5**（apne1） | — | ALG-PITCH / ALG-LABEL（所有感ラベル・疲労連動コピー）。Sonnet 4.6 は backlog B-002 |
| AWS SDK | boto3（Unit-1 継承） | 最新安定 | DynamoDB / ElastiCache / Bedrock / Secrets Manager |
| PBT | Hypothesis | 最新安定 | NFR-PBT（ALG-LINK/RANK/TRANSITION/BOOST） |

### Unit-4 が確立する Backend 規約
- カタログアクセスは `ProductCatalogPort` 経由に限定（Q7=A FD / REEL-CAT-01）、直接 SDK 呼出禁止
- Bedrock 呼び出し失敗・モデレーション拒否時はテンプレートフォールバック（NFR-AVAIL-03）
- Safeguard 判定は S-03 SafeguardPolicy を直接 import（Unit-1 / Lambda Authorizer と同一ロジック）、取得失敗は fail-closed（NFR-AVAIL-05）

---

## 3. データストア（Unit-4 が利用するテーブル・キャッシュ）

| ストア | 用途 | キャパシティ | 確定ステージ |
|---|---|---|---|
| DynamoDB `AmazonTransitions` | 遷移記録（冪等キー `(userId, clientTransitionId)`、月間カウント） | On-Demand（Q3=A） | テーブル設計は Infrastructure Design |
| DynamoDB `SafeguardStates`（Unit-1/7 共有） | 月間遷移カウント・冷却/負債フラグ（遷移ゲートで参照・更新） | On-Demand | Infrastructure Design |
| DynamoDB `ReelImpressions` | 閲覧ログ / 既出抑制・A/B（services.md SVC-02） | On-Demand | Infrastructure Design |
| DynamoDB `PreferenceVectors`（Unit-2 owner） | 嗜好ベクトル（Reel は推薦で read、更新は B-08 日次バッチ） | On-Demand | Unit-2 / Infra |
| DynamoDB `Achievements`（Unit-2 スキーマ） | EXP / Lv（B-13 が遷移時に EXP +1 を冪等 UpdateItem） | On-Demand | Unit-2 / Infra |
| ElastiCache Redis | Creators API カタログキャッシュ TTL 6h（B-11） | Infra Design で確定 | Infrastructure Design |
| S3 | 画像 / ダミーカタログ JSON | — | Infrastructure Design |

> テーブルのキー設計・GSI・TTL・暗号化（KMS）は **Infrastructure Design** で確定。本書は「どのストアを使うか」の前提のみ。

---

## 4. Unit-4 固有の技術判断

| 判断 | 内容 | 根拠 |
|---|---|---|
| **MVP は OpenSearch 不採用** | 推薦候補生成は購入履歴ベース（カテゴリ/ブランド一致 + 共購買）。Titan Embeddings + OpenSearch Serverless は決勝で導入 | CL-1=A / [B-204](../../../../doc/backlog.md) |
| **ラベル/コピー生成は Haiku 4.5** | ALG-PITCH/LABEL の動的生成に Bedrock Claude Haiku 4.5（低コスト・高速）。Sonnet 4.6 はエスカレーション backlog | Q4=A（FD） / 要件書 §7 / B-002 |
| **カタログはポート/アダプタ** | `ProductCatalogPort` + `DummyCatalogAdapter`（MVP）/ `CreatorsApiAdapter`（決勝、Approved Mobile App 承認後）+ 共通キャッシュデコレータ | Q7=A（FD） / FR-REEL-04 / §8 A-10 |
| **遷移記録は条件付き書き込み** | DynamoDB 条件式で冪等性（`attribute_not_exists(clientTransitionId)`）+ 月間カウントを原子的更新 | Q2=A / PBT-04 |
| **リスト実装は Code Generation で性能比較** | FlashList vs FlatList を 60fps 目標で評価して確定 | NFR-PERF-03 |

---

## 5. CI/CD・セキュリティツール（Unit-1 継承）

| 項目 | ツール | 備考 |
|---|---|---|
| CI | GitHub Actions | Unit-1 継承 |
| TS Lint / Format | ESLint (strict) + Prettier | Unit-1 継承 |
| Python Lint / 型 | ruff + mypy --strict | Unit-1 継承 |
| 契約テスト | Schemathesis（reel.yaml）/ MSW（Mobile） | api-contracts.md §8 |
| Mock Server | Prism（localhost:4010） | Unit-6/5 未完成時の ctx/登録スタブ |
| シークレット管理 | Secrets Manager / SSM | Creators API / Associates 認証情報（Q8=A、ハードコード禁止） |
| PBT | fast-check（TS）+ Hypothesis（Py） | Q6=A |

---

## 6. 未決定事項（後続ステージで確定）

| 項目 | 確定ステージ |
|---|---|
| DynamoDB テーブルのキー設計・GSI・TTL・暗号化 | Infrastructure Design |
| Lambda メモリ / タイムアウト / 同時実行 / VPC 配置（B-03/B-10/B-11/B-13） | NFR Design / Infrastructure Design |
| ElastiCache Redis ノードタイプ / クラスタ構成 | Infrastructure Design |
| OpenSearch Serverless コレクション設定（決勝） | Infrastructure Design（B-204 採用時） |
| Bedrock モデル ID / プロンプトテンプレート / レート制限 | NFR Design / Code Generation |
| FlashList vs FlatList の最終選定 | Code Generation（60fps ベンチ） |

---

## 7. 技術選定の確定事項サマリ

- **新規技術の導入なし**: 要件書 §7 / tech.md / Unit-1 の確定スタックを Unit-4 で実体化
- **MVP は OpenSearch 見送り**、購入履歴ベース推薦で軽量化（決勝でベクトル検索、B-204）
- **カタログはポート/アダプタ**で本番↔ダミーを差し替え（Approved Mobile App 承認前後の移行が非破壊）
- **ラベル/コピーは Haiku 4.5 + テンプレートフォールバック**（LLM 障害でフィードが崩れない）
- **遷移は条件付き書き込みで冪等**（二重 EXP・上限破り防止）
- **Safeguard は S-03 直接 import で判定一致**、取得失敗は fail-closed
