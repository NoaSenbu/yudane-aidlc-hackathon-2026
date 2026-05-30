# Unit-3 Debate — Mobile Event Parser 実装サマリ（Phase 1 Step 7）

> Phase 1 Step 7（Mobile Event Parser、Outside-In TDD + PBT-02）の実装結果。
>
> 参照: [Phase 1 Plan §1 Step 7](../../../plans/unit-3-debate-code-generation-phase1-plan.md) / [domain-entities §3](../functional-design/domain-entities.md) / [direction-d-design-system.md](../../design-system/direction-d-design-system.md)
>
> 完了日: 2026-05-30 / 担当: Member B（AI 代行実装）/ TDD スタイル: Outside-In TDD + PBT-02

---

## 1. 生成ファイル

| ファイル | 役割 |
|---|---|
| `mobile/src/features/debate/event-parser.ts`（130 行）| LC-D-10 NDJSON パーサー + 軸タグ抽出 |
| `mobile/src/features/debate/event-parser.test.ts`（150 行）| 14 unit tests |
| `mobile/src/features/debate/event-parser.property.test.ts`（100 行）| 2 PBT-02 ラウンドトリップ |

---

## 2. API 仕様

### 2.1 `parseEventStream(stream)` 関数

```typescript
async function* parseEventStream(
  stream: AsyncIterable<Uint8Array>,
): AsyncIterableIterator<StrandsStreamEvent>
```

NDJSON（改行区切り JSON）を前提とし、chunk の境界が JSON 構造途中に来てもバッファリングで復元する。

### 2.2 `extractAxis(text)` 関数

```typescript
function extractAxis(text: string): DebateAxis | undefined
```

正規表現 `\[(FACT|PSYCHOLOGY|REWARD)\]` で **最初の軸タグマーカー** を抽出。複数マーカーがあっても最初の 1 個のみ返す。**大文字のみ受理**（ガードレール仕様、`[fact]` 小文字は無視）。

### 2.3 Direction D ラベルへの 1:1 マッピング

| 軸タグ | Direction D ラベル | M-1/M-2 メカニズム |
|---|---|---|
| `[FACT]` | 論破 I・データ | M-1（事実軸、時給換算 / 在庫希少性 / カレンダー整合）|
| `[PSYCHOLOGY]` | 論破 II・感想 | M-1（心理軸、preferred_axis ベース個別最適化）|
| `[REWARD]` | 論破 III・ご褒美 | M-2（ストレス × ご褒美軸、stress_level=mid/high で発火）|

Phase 2 の `DebateScreen` 実装時は `metadata.axis` を見るだけで Direction D ラベルへ振り分け可能。

---

## 3. テスト 16 ケース

### 3.1 Unit Test 14 ケース

| グループ | テスト数 | 主な検証 |
|---|---|---|
| `parseEventStream` | 7 | token / turn_complete / session_complete / error / 不正 JSON / 複数 chunk / バッファリング |
| `extractAxis` | 6 | FACT / PSYCHOLOGY / REWARD / マーカーなし / 複数マーカー（最初のみ）/ 大小文字区別 |
| 統合 | 1 | token の delta_text に `[FACT]` → `metadata.axis: 'FACT'` |

### 3.2 PBT-02 Round-trip 2 プロパティ

| Property | 戦略 | 不変条件 |
|---|---|---|
| `parseEventStream PBT-02 Round-trip` | 任意 4 種 EventType + safe string + 50 examples | JSON 化 → parse で type / delta_text / metadata.reason 復元 |
| 軸タグ確実抽出 | DebateAxis × safe string + 30 examples | `[AXIS] content` 形式で必ず `metadata.axis === axis` |

**実行結果**: 14 unit + 2 PBT = **16/16 green / 12ms**。

---

## 4. 設計上の判断

### 4.1 NDJSON ベースの実装（`event-source-parser` 不使用）

**理由**:
- AgentCore Runtime のレスポンスは **`Content-Type: application/x-ndjson`**（infrastructure-design §1.1 Cognito Authorizer 構成と整合）
- `event-source-parser` は SSE 形式（`data: {...}\n\n`）専用で NDJSON とは互換性なし
- 自前の `TextDecoder.decode(chunk, {stream:true})` + 改行スキャンでバッファリングを実装、依存ゼロで動作

### 4.2 軸タグの大小文字区別

**ガードレール仕様**: プロンプト合成（PROMPT-08）で **大文字 `[FACT]` のみ** を出力させる。Bedrock Haiku 4.5 が誤って `[fact]` 小文字や `[Fact]` 混合大小文字を出力しても、event-parser は無視 → `metadata.axis` が undefined → Direction D ラベル無し（既定スタイル）で表示される。これは **「軸不明な論破」を画面で目立たせない** 設計（誤抽出を NG-6 滑落に繋げない）。

### 4.3 fail-safe な error event

不正な JSON は throw せずに `error event with reason='parser.invalid_json'` で yield → セッション継続不可（Mobile UI で「通信エラー」表示）。これは MCP（Model Context Protocol）的な挙動で、Mobile 側のエラーハンドリングを統一できる。

### 4.4 Phase 2 拡張時の互換性

Phase 2 で追加される EventType（`moderation_blocked` / `graceful_shutdown_initiated` / `summary` / `debate.cooldown_triggered` / `debate.refused` / `debate.agreed` / `debate.affirmation_shown`）は、`VALID_EVENT_TYPES` セットに追加するだけで対応可能。既存の 4 種は変更不要。

---

## 5. ハッカソン評価軸へのインパクト

- **Unit 分解の適切さ**: 130 行の純パーサー + 軸抽出ヘルパーで疎結合、Phase 2 の DebateScreen から `metadata.axis` だけで Direction D ラベル切替
- **創造性とテーマ適合性**: 軸タグ → Direction D ラベルの 1:1 マッピングが M-1 + M-2 併走 UI を物理層で実現、論理軸/感情軸/ご褒美軸の **3 段攻撃を視覚的に成立**
- **ドキュメント品質**: 14 unit + 2 PBT で **エンコード/デコード対称性 + 軸抽出の確実性** を 80 examples で証明
- **AI-DLC プロセス**: PBT-02（NFR-PBT-DEBATE-02）を fast-check で実装、Phase 2 以降の event 型拡張にも対応可能な構造を Phase 1 で確立
