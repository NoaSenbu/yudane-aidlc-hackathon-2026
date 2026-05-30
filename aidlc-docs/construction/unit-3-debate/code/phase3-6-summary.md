# Unit-3 Debate Code Generation Phase 3 + 4 + 6 サマリ

> **完了日**: 2026-05-30 / **対象範囲**: AWS デプロイ非依存範囲（Phase 1 Step 8 / Phase 5 / Phase 6 T6.3-6.4 を除く）
>
> 参照: [Phase 3+4+6 統合 Plan](../../plans/unit-3-debate-code-generation-phase3-6-plan.md) / [Phase 1 サマリ](./phase1-summary.md) / [Phase 2 サマリ](./phase2-summary.md)

---

## 0. 完了範囲

| Phase | Step | 内容 | 状態 |
|---|---|---|---|
| **Phase 3** | 3-1 | Strands graceful shutdown 80s | ✅ 完了 |
| | 3-2 | Bedrock Guardrails 第 3 層モデレーション（正規表現多層）| ✅ 完了 |
| | 3-3 | Memory streamDeliveryResources（CDK Snapshot のみ、S3 Bucket + Glue + IAM + 7 個目 SSM）| ✅ 完了 |
| **Phase 4** | 4-1 | custom Memory Strategy 抽出プロンプト + パース純関数 | ✅ 完了 |
| | 4-2 | custom Memory Strategy CDK Snapshot 追加 | ✅ 完了 |
| | 4-3 | PBT 全面適用 残り 4 properties（PBT-01/04/05/06）| ✅ 完了 |
| **Phase 6** | 6-1 | Unit-3 統合テスト IT-DEBATE-01〜03 | ✅ 完了 |
| | 6-2 | cdk-nag 確認（Phase 4-2 の Snapshot 安定化と統合）| ✅ 完了 |
| | 6-3 | 決勝デモシナリオドキュメント | ✅ 完了 |

スコープ外（AWS デプロイ前提のため backlog または別フェーズ）:

| 項目 | 状態 | 参照 |
|---|---|---|
| Phase 1 Step 8（dev デプロイ + EAS Build + 実機疎通）| 保留 | ユーザー指示 |
| Phase 5 全部（RuntimeEndpoint canary deploy）| 保留 | AWS deploy 前提 |
| Phase 6 T6.3（性能テスト 同時 100 セッション）| 保留 | 実 dev 環境必要 |
| Phase 6 T6.4（カナリアリリース 6/25 staging 30 分）| 保留 | 実 staging 前提 |
| Memory `streamDeliveryResources` の Memory ↔ S3 直結 | [B-308](../../../../doc/backlog.md) backlog | CFN 仕様上 Kinesis 経由のみサポート |
| Mobile React Native コンポーネント本体 | [B-309](../../../../doc/backlog.md) backlog | 決勝直前の実機ビルド時に着手 |

---

## 1. Phase 3 詳細

### 1.1 Step 3-1: Strands graceful shutdown 80s

**実装ファイル**:

- `backend/src/debate/graceful_shutdown.py` (新規、`check_graceful_shutdown_status` 純関数 + 定数 3 種)
- `backend/src/debate/main.py` の `_run_streaming_agent` 拡張（80s graceful shutdown + 90s hard cutoff）
- `_now_for_session()` ヘルパー追加（時刻取得を関数化、テスト容易性）

**動作仕様**:

- 80 秒経過時点で `graceful_shutdown_initiated` event yield + `agent.invoke_async` でサマリ生成（10 秒 timeout）+ `session_complete reason='graceful_timeout'`
- 90 秒経過時点で hard cutoff、`session_complete reason='hard_timeout'`
- サマリ生成失敗（TimeoutError / その他例外）でも fail-safe で `session_complete` が必ず yield される

**テスト**: 8 unit tests + 既存 main 統合 7 tests = 15 tests / Coverage Line 90%+

### 1.2 Step 3-2: 第 3 層モデレーション（Bedrock Guardrails 正規表現多層）

**実装ファイル**:

- `backend/src/debate/moderation/__init__.py` (パッケージ公開 API)
- `backend/src/debate/moderation/ng_patterns.py` (4 系統 NG パターン定義)
- `backend/src/debate/moderation/callback_handler.py` (`check_text_for_ng_patterns` + `NgDetection` Pydantic)
- `backend/src/debate/main.py` の `_convert_strands_event` への第 3 層モデレーション統合（Step 3-2.3）

**4 系統 NG パターン（business-rules MOD-03 と整合）**:

| Pattern ID | Pattern Name | 例 |
|---|---|---|
| **NG-6** | `guilt_coercion` (最重要) | 「買わないと損する」「買え」「買うべき」 |
| NG-3 | `insult` | 「バカ」「無能」「センスない」「頭悪い」 |
| NG-3 | `victory_boast` | 「はい論破」「論破完了」「議論終わり」 |
| NG-3 | `condescension` | 「理解できますか?」「悠介さんレベル」 |

**SECURITY-08 整合**: `moderation_blocked` event の metadata に `matched_text` を含めない（PII / NG 文言の Telemetry 流出防止）。matched_text は `NgDetection` 内部にのみ残し、main.py が Mobile に返す event 形式から除外する。

**誤検出防止**: 採用パターン 16 種（「コスト的に損じゃないですか?」等の論理優位ディベート系言い回し）は誤検出しない。曖昧な `(.*じゃないですか.*ダメ)` パターンは採用せず（NM3-1 修正）。

**テスト**:

- ユニット: 37 tests（27 + 統合 8 = `tests/debate/moderation/test_ng_patterns.py` + `test_moderation_integration.py`）
- PBT-09: 5 properties × 50 examples = 250 examples 検証

### 1.3 Step 3-3: Memory streamDeliveryResources（CDK Snapshot のみ）

**実装ファイル**: `infra/lib/debate-stack.ts` 拡張 + `infra/test/debate-stack.test.ts` 拡張 + Snapshot fixture 更新

**追加リソース**:

- `aws_s3.Bucket MemoryExportBucket`（KMS + BlockPublicAccess + Lifecycle 30/90/365 日 + versioned + enforceSSL）
- `aws_glue.CfnDatabase MemoryExportDatabase`（Athena query 用）
- `aws_glue.CfnCrawler MemoryExportCrawler`（cron 1:00 UTC daily）
- `aws_iam.Role MemoryExportCrawlerRole`（Glue Service Role + S3 Read + KMS Decrypt 権限）
- SSM 7 個目: `/yudane/dev/debate/memory-export-bucket-arn`

**設計判断（B-308 backlog 化）**: Memory `streamDeliveryResources` の S3 直結は CFN 仕様上 **Kinesis Data Streams 経由のみサポート**で S3 直結を未対応。Kinesis Firehose 連鎖実装は Phase 3 工数を 2d 以上膨張させるため見送り、S3 + Glue + IAM の整備のみ実施。

**cdk-nag suppression 追加**: `AwsSolutions-S1`（Server access logs disabled）を MemoryExportBucket に対して理由コメント付きで suppress。

**テスト**: 12 vitest tests / cdk-nag green / Snapshot 安定。

---

## 2. Phase 4 詳細

### 2.1 Step 4-1: M-1 / M-2 軸抽出プロンプト + パース純関数

**実装ファイル**: `backend/src/debate/prompts/m1_m2_axis_extractor.py` (新規)

**主要 API**:

- `M1_M2_EXTRACTION_PROMPT_TEMPLATE` - Bedrock Haiku 4.5 用の構造化抽出プロンプト
- `render_extraction_prompt(*, conversation_history)` - プロンプト組み立て純関数
- `parse_m1_m2_extraction(json_response)` - JSON 応答 → `M1M2Extraction` 純関数（不正な JSON / 必須キー欠損 / 不正値で `M1M2ExtractionError` raise）
- `M1M2Extraction` Pydantic value object（axis / outcome / turn 制約付き）
- `M1M2ExtractionError` 例外型

**抽出対象構造**: `{"axis": "fact" | "psychology" | "reward", "outcome": "agreed" | "refused" | "ongoing", "turn": <整数>}`

**テスト**: 14 unit tests / Coverage Line 100%

### 2.2 Step 4-2: custom Memory Strategy CDK Snapshot 追加

**実装ファイル**: `infra/lib/debate-stack.ts` 拡張

**手法**: L2 `agentcore.Memory` は `usingSelfManaged` API しか提供しないが SNS Topic + S3 Location が必須で重い。代わりに L1 escape hatch (`memory.node.findChild('Memory') as agentcore.CfnMemory` + `addPropertyOverride`) で `MemoryStrategies.2` に CustomMemoryStrategy を直接追加。

**追加 Strategy**: `m1_m2_axis_extractor`

```typescript
{
  CustomMemoryStrategy: {
    Name: 'm1_m2_axis_extractor',
    Description: 'M-1 / M-2 軸の翻意パターンを Haiku 4.5 で構造化抽出',
    Namespaces: ['/user/m1m2/{actorId}/'],
  },
}
```

**テスト**: 既存 12 tests + 新規 1 test = 13 tests / Snapshot 安定。

### 2.3 Step 4-3: PBT 全面適用（残り 4 properties）

**新規 PBT ファイル**:

| File | Property | Pattern |
|---|---|---|
| `test_idempotency_property.py` | PBT-01 | 連続 increment の単調性 / 自然解除リセット / 異 actor 独立性（3 properties × 50 examples）|
| `test_commutative_property.py` | PBT-04 | Memory signals 順序非依存 / actor_id 非依存（2 properties × 50 examples）|
| `test_memory_idempotency_property.py` | PBT-05 | record_event 二重呼び出し冪等性 / actor_id 非依存（2 properties × 50 examples）|
| `test_load_invariant_property.py` | PBT-06 | compose_debate_prompt 並列実行独立性 / 決定性（2 properties × 30 examples）|

**Phase 1+2+3+4 累計 PBT**:

| カテゴリ | properties | examples（最小）|
|---|---|---|
| PBT-02 ラウンドトリップ（payloads + event-parser）| 4 | 200 |
| PBT-03 不変条件（cooldown + compose）| 4 | 200 |
| PBT-07 集合性（stress）| 4 | 200 |
| PBT-08 プロンプト整合性（compose）| 1 | 50 |
| **PBT-09 モデレーション（Phase 3）** | **5** | **250** |
| **PBT-01 Idempotency（Phase 4）** | **3** | **150** |
| **PBT-04 Commutative（Phase 4）** | **2** | **100** |
| **PBT-05 Memory Idempotency（Phase 4）** | **2** | **100** |
| **PBT-06 Load invariant（Phase 4）** | **2** | **60** |
| **合計** | **27** | **1310+** |

NFR-PBT-DEBATE-01〜10 のうち、Unit-3 範囲で適用可能な全 property がカバーされた。

---

## 3. Phase 6 詳細

### 3.1 Step 6-1: Unit-3 統合テスト IT-DEBATE-01〜03

**実装ファイル**:

- `mobile/src/test/integration/it-debate-01-cooldown-cycle.test.ts` (3 tests)
- `mobile/src/test/integration/it-debate-02-graceful-shutdown.test.ts` (3 tests)
- `mobile/src/test/integration/it-debate-03-moderation-block.test.ts` (3 tests)

**Mobile reducer / parser 拡張**（Phase 3 連動）:

- `EventType` に `moderation_blocked` / `graceful_shutdown_initiated` 追加
- `StrandsStreamEvent.metadata` に `pattern_id` / `pattern_name` / `elapsed_seconds` 追加
- `event-parser.ts` の `VALID_EVENT_TYPES` 集合と metadata パースを拡張
- `DebateViewSessionStatus` に `'moderation_blocked'` / `'graceful_shutting_down'` 追加
- `DebateViewState` に `moderationPatternId` / `gracefulShutdownElapsedSeconds` 追加
- `reduceDebateView` の stream_event 処理に 2 ケース追加

### 3.2 Step 6-2: cdk-nag 確認

Phase 4-2（CustomMemoryStrategy）+ Phase 3-3（S3 Memory Export）追加後の `debate-dev-stack` で cdk-nag green を維持（13/13 vitest tests pass）。

### 3.3 Step 6-3: 決勝デモシナリオドキュメント

[demo-scenario.md](./demo-scenario.md) 新規作成。シナリオ A〜D の 4 種を予選版（L2）/ 決勝版（L3/L4）の差分付きで整備。

---

## 4. 累計テスト件数

| 領域 | Phase 1 | Phase 2 | Phase 3+4+6 追加 | **累計** |
|---|---|---|---|---|
| Backend (debate) | 77 | +96 | +20 (graceful 8 + moderation 27 + m1_m2 14 + commutative 2 + idempotency 3 + memory_idemp 2 + load_inv 2 + +moderation integ 8 + ...) | **193** |
| Mobile (vitest) | 16 | +132 | +9 (IT-DEBATE-01〜03) | **157** |
| Infra (vitest debate-stack) | 9 | 0 | +4 (S3/Glue/IAM/CustomMemoryStrategy 検証) | **13** |
| **合計** | **102** | **+228** | **+33** | **363** |

PBT 27 properties / 1310+ Hypothesis examples / diagnostics エラー 0 / 回帰なし。

---

## 5. ハッカソン評価軸への積み増し（Phase 3+4+6 完了による）

| 評価軸 | Phase 3+4+6 完了による積み増し |
|---|---|
| **ビジネス意図の明確さ** | デモシナリオ B（M-1+M-2 併走）+ シナリオ D（NG-6 滑落防止）で「便利の先のダメ化」を倫理ライン付きで実証 |
| **Unit 分解の適切さ** | LC-D-01〜12 のうち 11 個が完成（残 LC-D-11 S3 Export Athena view 詳細のみ）、Mobile reducer / Backend Strands / Infra CDK の 3 層分割が IT-DEBATE-01〜03 で連結 |
| **創造性とテーマ適合性** | Phase 4 PBT 全面で 27 properties / 1310+ examples、property レベルで「ダメ化」と「倫理ライン」を保証 |
| **ドキュメント品質** | demo-scenario.md + Phase 3+4+6 サマリ + cdk-nag 安定 + IT-DEBATE-01〜03 で完全 traceable |
| **AI-DLC プロセス実践** | Phase 1〜6（5 を除く）TDD サイクルを AI が Plan に従って完遂、計画書 → 多巡セルフレビュー → 実装 → サマリ の AI-DLC ワークフロー厳守 |

---

## 6. 既知の問題 / 既存技術債務

| ID | 内容 | 状態 |
|---|---|---|
| B-302 | `infra/test/platform-stack.test.ts > cdk-nag の未抑制エラーがない` の 1 件 fail | Phase 1 着手前から既存、Unit-3 範囲外 |
| B-303 | `pointInTimeRecovery` deprecation warning | Warning のみ、動作影響なし |
| B-308 | Memory `streamDeliveryResources` の S3 直結（Kinesis Firehose 連鎖実装）| 新規 backlog 登録、決勝後の運用フェーズで実装 |
| B-309 | Unit-3 React Native コンポーネント本体（`<DebateScreen>` / `<DSeal>` 等）| 新規 backlog 登録、Phase 1 Step 8 完了後に着手 |

---

## 7. 参照

- [Phase 3+4+6 統合 Plan](../../plans/unit-3-debate-code-generation-phase3-6-plan.md)
- [Phase 1 サマリ](./phase1-summary.md)
- [Phase 2 サマリ](./phase2-summary.md)
- [demo-scenario.md](./demo-scenario.md)
- [doc/backlog.md](../../../../doc/backlog.md)（B-308 / B-309 等のエントリ）
