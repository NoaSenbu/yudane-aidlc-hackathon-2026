# Unit-4 Reel — Logical Components

> NFR 設計パターンを実現する **論理コンポーネント** の構成。技術非依存の論理構造（物理インフラは Infrastructure Design で確定）。
> 参照: [nfr-design-patterns.md](./nfr-design-patterns.md) / [Functional Design](../functional-design/) / [NFR Requirements](../nfr-requirements/) / [components.md](../../../inception/application-design/components.md) / [Unit-1 logical-components.md](../../unit-1-platform/nfr-design/logical-components.md)
> 確定方針: NFR-Design Q1〜Q10=A ＋ 矛盾解消 3 件（VPC=a / レイテンシ分離 / ラベル同期統一）

---

## 0. 論理コンポーネント一覧

| ID | 論理コンポーネント | 物理マッピング先（予定） | VPC 境界 | 実現パターン |
|---|---|---|---|---|
| RLC-01 | Reel Feed Orchestrator | B-03（backend/src/reel） | VPC 外 | R-PAT-RANK-01 / PERF-01 |
| RLC-02 | Candidate Source（pluggable） | B-03 内 `CandidateSourcePort` | VPC 外（MVP）/ VPC 内（決勝 OpenSearch） | R-PAT-RANK-01 |
| RLC-03 | Deterministic Reranker | B-03 内（純関数） | VPC 外 | R-PAT-RANK-01 |
| RLC-04 | Late-night Booster | B-03 内（純関数） | VPC 外 | ALG-BOOST |
| RLC-05 | Label/Pitch Generator | B-03 内（Bedrock 呼出 + フォールバック + モデレーション） | VPC 外 | R-PAT-LLM-01 / MOD-01 |
| RLC-06 | Product Catalog Gateway | B-11 CreatorsApiClient | MVP=プロセス内（ダミー）/ 決勝=**VPC 内** | R-PAT-CAT-01/02 / PERF-02 |
| RLC-07 | Amazon Transition Recorder | B-13 | VPC 外 | R-PAT-TXN-01 / SAFE-01 |
| RLC-08 | Special Link Generator | B-10（純関数・**共有モジュール**、feed/transition Lambda が import） | VPC 外 | R-PAT-LINK-01 |
| RLC-09 | Reel Screen | M-03（mobile/src/features/reel） | client | R-PAT-UI-01 |
| RLC-10 | Reel Metrics（dual-path） | M-13 + B-12 metric | client / 両 VPC | R-PAT-OBS-01 |

継承する Unit-1 論理コンポーネント: LC-01 ApiClient / LC-03 Audit Logging / LC-04 Authorization Layer / LC-07 Safeguard Policy Module（S-03）/ LC-08 ASIN Utility（S-01）。

---

## 1. RLC-01 Reel Feed Orchestrator（B-03、VPC 外）

### 構成
```
buildReel(ctx, weights, cursor)   ← GET /v1/reel
  ├─ [予算 ≤300ms] RLC-02 CandidateSource.fetch(ctx)        ← MVP=プロセス内ダミー / 決勝=RLC-06 invoke
  ├─ フィルタ: NG カテゴリ除外 / 既出抑制 / 遷移後カテゴリ cooldown（FR-AUTH-03）
  ├─ [予算 ≤50ms]  RLC-03 Reranker.rank(candidates, ctx)    ← 純関数（決定論）
  ├─ [純関数]       RLC-04 Booster.insert(scored, ctx)       ← 深夜ブースト（同一セッション1回）
  └─ [予算 ≤350ms] RLC-05 LabelGenerator.generate(top, ctx) ← カードごと並列・同期確定
  → ReelPage（cards + nextCursor）
```
- **レイテンシ予算配分**（R-PAT-PERF-01）: 候補 300ms / リランク 50ms / ラベル 350ms（並列）
- ラベルは **同期確定**（矛盾解消3）。ソフト期限超過はテンプレートフォールバックで埋める（後追いなし）

---

## 2. RLC-02 Candidate Source（pluggable、R-PAT-RANK-01）

### 構成（B-204 非破壊導入のための抽象化）
```
interface CandidateSourcePort {
  fetch(ctx: RecommendationContext): Promise<Candidate[]>;
}
  ├─ PurchaseHistoryHeuristicSource   … MVP: カテゴリ/ブランド一致 + 共購買（**プロセス内 DummyCatalogAdapter** を直接利用、VPC/Redis/invoke なし）
  │     └─ cold start: オンボ嗜好シード → 不足はキュレーション固定リスト（CL-3）
  └─ VectorSearchSource               … 決勝: Titan Embeddings + OpenSearch（B-204、VPC 内）
```
- リランク（RLC-03）以降は **候補ソース非依存**で共通 → B-204 導入時に Reranker/Booster/Label を書き換えない
- **MVP**: Source も Catalog も B-03 プロセス内で完結（最小構成）。**決勝**: カタログは RLC-06（VPC 内 B-11）invoke、VectorSearchSource は VPC 内側に置く

---

## 3. RLC-03 Deterministic Reranker / RLC-04 Late-night Booster（B-03、純関数）

### 構成
```
RLC-03 rank(candidates, ctx, weights):
  score = Σ(relatedness, timeBoost, stressBoost, calendarMatch, -recencyDecay)
  stableSort(desc, tiebreak=asin asc)        ← 決定論（PBT-03）

RLC-04 insert(scored, ctx):
  if shouldBoost(ctx) and not cursor.boostConsumed:   ← 深夜22-2時 ∧ stress≥mid ∧ ¬quietWeek ∧ ¬cooldown
     高単価枠（平均1.5〜3倍）を最大3件先頭挿入、boostConsumed=true
```
- 副作用なし・外部 I/O なし → レイテンシ予算 50ms 内、PBT で決定論検証

---

## 4. RLC-05 Label/Pitch Generator（B-03、VPC 外、R-PAT-LLM-01 / MOD-01）

### 構成
```
generate(card, ctx):  ← カードごと並列
  ├─ [hard timeout 1.5s] Bedrock Haiku 4.5 で pitch/label 生成
  ├─ moderate()  … NG-6（脅迫/罪悪感）/ NG-3（身体/家族等）除去 [+ Guardrails 任意]
  ├─ 24h 重複チェック（recentLabelHashes）
  └─ 失敗/拒否/重複/ソフト期限350ms超過 → templateFallback（必ず非空、source='template-fallback'）
```
- **MVP は同期確定**。後追い差し替えは不採用（FD: ownershipLabel/pitch 必須）。決勝最適化は [B-205](../../../../doc/backlog.md)

---

## 5. RLC-06 Product Catalog Gateway（B-11、MVP=プロセス内 / 決勝=**VPC 内**、R-PAT-CAT-01/02 / PERF-02）

### MVP 構成（予選 5/30、最小）
```
[B-03 プロセス内] DummyCatalogAdapter（インメモリ / 同梱 JSON）
  └─ searchItems / getItemByAsin … 外部に出ない、Redis なし、VPC なし、別 Lambda invoke なし
```

### 決勝構成（Creators API ライブ、R-PAT-VPC-01: VPC 境界分離）
```
[VPC 外 B-03] ──Lambda invoke──> [VPC 内 B-11 CreatorsApiClient]
                                    ├─ withCache(adapter)  … L1: Redis（ASIN→ProductMeta, TTL 6h）
                                    │     ├─ hit → 返す
                                    │     ├─ miss → adapter 呼出（hard timeout 2s）→ put
                                    │     └─ adapter 失敗 → stale 返却（あれば）/ なければ DummyCatalog
                                    ├─ adapter: CreatorsApiAdapter（本番）
                                    └─ L2: ユーザー別候補リスト 短 TTL 60〜120s（任意）
                                  └─ Redis / Creators API（VPC Endpoint or NAT）
```
- **MVP は B-03 プロセス内でダミー完結**（過剰な VPC/Redis/invoke を持ち込まない）
- **決勝のみ** B-11 を VPC 内に隔離し、cache-aside + stale-on-error でフィードを落とさない（R-PAT-CAT-01）
- `ProductCatalogPort` 抽象（FD Q7）により MVP↔決勝の差し替えは非破壊

---

## 6. RLC-07 Amazon Transition Recorder（B-13、VPC 外、R-PAT-TXN-01 / SAFE-01）

### 構成
```
recordTransition(req):  ← POST /v1/amazon-transitions
  1. @require_owner（JWT sub == userId、LC-04 継承）
  2. [先行 Gate] S-03 decideAllow(loadSafeguardInput)   ← 同期、取得失敗=fail-closed
       block → 409（記録せず） / warn → 続行（200+warningヘッダ）
  3. TransactWriteItems（原子的、**Reel 所有の 2 項目**）:
       - AmazonTransitions.put（条件: clientTransitionId 未登録）
       - SafeguardStates.transitionCountMonth += 1
     条件違反（重複）→ ExpAward(duplicate=true, awarded=0)
  4. 非重複時に EXP +1 を同期付与（Achievements を冪等 UpdateItem）→ ExpAwardDto を返す（US-02-02 AC-4）
  5. metric: 遷移409率 / track('reel.amazon_tap')
```
- DynamoDB / Safeguard 状態は VPC 外から到達可（VPC 不要、MVP/決勝とも）
- **EXP は B-13 が同期付与**（component-methods.md `record_transition() -> ExpAwardDto` / services.md「B-13 → EXP 加算 → Lv↑」準拠）。Achievements は Unit-2 スキーマだが B-13 が冪等に書く
- **非同期は嗜好ベクトル学習のみ**: B-08 PreferenceVectorUpdater（日次バッチ）が AmazonTransitions を集計（EXP 加算ではない）
- **クロス Unit**: SafeguardStates（Unit-7）月間カウント更新と Achievements（Unit-2）EXP 付与は B-13 の責務として component-methods.md で定義済み。テーブル所有境界・書き込み権限は Infrastructure Design / Unit-2・7 調整で確定

---

## 7. RLC-08 Special Link Generator（B-10、VPC 外、**純関数共有モジュール**、R-PAT-LINK-01）

### 構成
```
generateSpecialLink(input):  ← 純関数（専用 Lambda にしない。feed/transition Lambda が import）
  baseUrl = "https://www.amazon.co.jp/dp/" + asin   ← 短縮しない（NG-8）
  tag = ASSOCIATES_TAG + "-" + subTag(userId)        ← Associates タグは SSM（非機密、URL に公開される値）
  環境ガード: dev=仮リンク / prd 未承認=blocked（creators-approved フラグ）
  不変条件: extractAsin(url).asin == input.asin（PBT-02、S-01/LC-08 で検証）
```
- 外部呼び出しのない純 URL 生成のため、独立 Lambda（invoke ホップ・コスト）を避け、呼び出し元 Lambda に同梱（過剰設計回避）

---

## 8. RLC-09 Reel Screen（M-03、client、R-PAT-UI-01）

### 構成
```
<ReelScreen>
  ├─ 仮想化リスト（FlashList 優先 / FlatList fallback、オフスクリーン破棄）
  ├─ GestureLayer（gesture-handler + reanimated、UI スレッド実行）
  │     優先順位: double-tap > 水平スワイプ > vertical-scroll
  ├─ AmazonTransitionOverlay（ダブルタップ必須、FR-REEL-05）
  ├─ boostNudge（3秒無操作で誘導アニメ、reanimated worklet、US-02-01 AC-2）
  └─ 画像: サムネ解像度 + 次カードプリフェッチ
  状態: TanStack useInfiniteQuery（カーソル）/ Zustand（overlay/設定/swipe回数/boostNudge）
```

---

## 9. RLC-10 Reel Metrics（dual-path、R-PAT-OBS-01）

### 構成
```
client（M-13 track）: reel.viewed / swiped / double_tap / amazon_tap / boost_shown / label_fallback
server（B-12 metric, EMF）: feed_latency / catalog_cache_hit_rate / transition_409_rate
→ S-04 TelemetryContracts に reel.* を追記（PII 非含・低カーディナリティ次元）
```

---

## 10. 論理コンポーネント配置（モノレポ）+ VPC 境界

```
mobile/src/features/reel/        … RLC-09 ReelScreen / RLC-10 client metrics
backend/src/reel/                … RLC-01 Orchestrator / RLC-02〜05（VPC 外）/ RLC-07 Transition / RLC-08 Link / RLC-06 ダミー（MVP プロセス内）
backend/src/reel/ (catalog)      … RLC-06 CreatorsApiClient（**決勝のみ** VPC 内・別 Lambda）
shared/safeguard-policy/         … S-03（LC-07 継承、遷移ゲート）
shared/asin-extractor/           … S-01（LC-08 継承、Special Link 逆抽出検証）
infra/lib/reel-stack.ts          … VPC 境界 / Lambda 構成 / DDB / Redis 接続（物理は Infra Design）
```

### VPC 境界サマリ（R-PAT-VPC-01）

| 配置 | コンポーネント | 理由 |
|---|---|---|
| **VPC 外**（SnapStart） | RLC-01/02/03/04/05/07/08（B-03/B-13/B-10）。**MVP は RLC-06 ダミーもプロセス内で VPC 外** | 低レイテンシ・ストリーミング系、ENI コールドスタート回避 |
| **VPC 内（決勝のみ）** | RLC-06（B-11 Creators ライブ）+ 決勝の VectorSearchSource | ElastiCache Redis / OpenSearch への到達が必須 |
| client | RLC-09（M-03） | モバイル |

> **MVP は VPC を使わない**（カタログがプロセス内ダミーのため）。VPC 分割は決勝の Creators API 本番接続で初めて導入する。

---

## 11. 未確定（Infrastructure Design で物理化）

| 論理コンポーネント | 物理化で決めること |
|---|---|
| RLC-06 ↔ Redis（決勝のみ） | ElastiCache ノードタイプ / クラスタ / VPC Subnet / Security Group（MVP は不要） |
| RLC-01/07（VPC 外 Lambda） | メモリ / タイムアウト / SnapStart Alias / 同時実行 |
| RLC-06（VPC 内 Lambda、決勝のみ） | VPC 構成 / VPC Endpoint（Creators API・Secrets Manager・DynamoDB） |
| RLC-07 テーブル | AmazonTransitions / ReelImpressions のキー設計 / GSI / TTL / KMS。SafeguardStates・EXP の所有境界（Unit-7/2 と調整） |
| RLC-02 決勝 | OpenSearch Serverless コレクション（B-204 採用時） |
| RLC-05 | Bedrock モデル ID / Guardrails / レート制限 |
| RLC-09 | FlashList vs FlatList 最終選定（60fps ベンチ） |
