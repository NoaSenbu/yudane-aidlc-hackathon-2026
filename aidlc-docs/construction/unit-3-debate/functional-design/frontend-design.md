# Unit-3 Debate — フロントエンド設計（Direction D 適用）

> **本ファイルは Unit-3 Debate の論破画面 UI 設計の正本です。**
>
> 上位 SSOT: [`aidlc-docs/construction/design-system/direction-d-design-system.md`](../../design-system/direction-d-design-system.md)（Direction D 共通デザインシステム）
>
> ビルド対象 HTML: [`../YUDANE Concierge (Direction D) (offline).html`](../YUDANE%20Concierge%20%28Direction%20D%29%20%28offline%29.html)
>
> Phase: Phase 2 で M-04 DebateScreen 実装、Phase 1 では Mobile UI 未実装（agentcore-client + event-parser のみ）/ 担当: Member B / 切替確定: 2026-05-30

## Overview

Unit-3 Debate の論破画面 UI は **Direction D「黒服のコンシェルジュ」**（黒岩のひろゆき口調 + 漆黒 × シャンパンゴールド）を Construction 期の正本とする。本書は Direction D 8 画面のうち Unit-3 主担当の 3 画面（D-1 NotifD 連携 / D-2 DebateScreen ★コア / D-3 AffirmScreen）について、構造・軸タグマッピング・タイマー演出・NativeWind v4 移植方針・A11y を確定する。Phase 1 では Mobile UI 画面実装はせず、Strands streaming chunk の `metadata.axis` 型定義とその抽出ロジックのみを実装する。

## Architecture

論破画面は React Native 0.76+ (New Architecture) + NativeWind v4 + Direction D デザイントークン (`--d-bg` / `--d-gold` / `--d-gold-2` / `--d-ink` 等) で構築する。Strands Agent からのストリーミング token を `event-parser.ts` で `EventType` + `metadata.axis` に変換し、軸（`FACT` / `PSYCHOLOGY` / `REWARD`）ごとに「論破 I・データ」「論破 II・感想」「論破 III・ご褒美」のラベル付きブロックへ振り分ける。タイマーは 80ms tick + 90s graceful shutdown 連動。M-2 肯定フィードバックは AffirmScreen の封蝋シール (`DSeal`) アニメ + 「正しい判断だと思いますよ」コピーで実装する。

## Components and Interfaces

### 担当画面（Direction D 8 画面のうち 3 つが Unit-3 主担当）

| 画面 ID | Direction D 関数 | フェーズ | UC | 主要 FR | M-1 / M-2 |
|---|---|---|---|---|---|
| **D-1 通知** | `NotifD` | UC-03 連携（Unit-5 主、Unit-3 補助）| UC-03 → UC-01 誘導 | FR-DEBATE-01（セッション開始）+ FR-FUNNEL-02 | M-2（深夜帯介入）|
| **D-2 論破画面 ★** | `DebateD` | **Unit-3 主担当 ★コア** | **UC-01 論破チャット** | **FR-DEBATE-02（事実 + 心理 2 軸反論）+ FR-DEBATE-09（ストレス × ご褒美軸）** | **M-1（論破 I）+ M-2（論破 II）併走 ★** |
| **D-3 論破完了** | `AffirmD` | Unit-3 主担当（後段）| UC-01 帰着 → Amazon 遷移 | FR-DEBATE-08（肯定フィードバック）| M-2（「正しい判断」）|
| D-4 履歴 | `ChatD` | Unit-3 副担当（Phase 3〜）| UC-01 履歴ビュー | FR-DEBATE-03 | M-1（過去論破の振り返り）|

NotifD の主担当は Unit-5 Cart Intercept、ChatD は Phase 3 以降に着手。本書は **D-2 / D-3** を主に詳述する。

### D-2 DebateScreen 構造（SSOT HTML `DebateD` 関数より抽出）

```
┌─────────────────────────────────────────────┐
│ Header                                       │
│  「迷い、論破します」 (d-serif, 18px, 600)   │
│  RONPA · UC-01 (d-en, 10px, ink-3)          │
│                       担当 黒岩 · 67s (d-pill) │
├─────────────────────────────────────────────┤
│ Item Card (d-panel)                          │
│  ┌──┐ Sony WF-1000XM6                       │
│  │  │ 悠介さんのためにキープ済み              │
│  └──┘                  HONORAIRE   ¥24,800  │
├─────────────────────────────────────────────┤
│ Counsel Block (d-panel)                      │
│                                              │
│  論破 I · データ ───────────                 │
│  時給換算で **11時間分**...                  │
│                                              │
│  論破 II · 感想 ────────────                 │
│  「お金ない」って、感想ですよね。論破。 ▍    │
│                                              │
├─────────────────────────────────────────────┤
│ Quick Replies                                │
│ [いや高くない？] [また今度で] [本当に要る？]  │
│                                              │
│ ┌─────────────────────────────────────┐     │
│ │ 論破されたので買う · ¥24,800（CTA）  │     │
│ └─────────────────────────────────────┘     │
│      それでも感想で見送る                    │
└─────────────────────────────────────────────┘
```

### D-3 AffirmScreen 構造（SSOT HTML `AffirmD` 関数より）

- 上部 pill: `ACCEPTED · #503-2890471`（受付番号）
- 中央: `DSeal` コンポーネント（封蝋シール、`d-seal` アニメ 0.9s）
- 大見出し（d-serif, 32px, 600）: 「**はい、論破完了。**」
- 本文（ink-2）: 「正しい判断だと思いますよ。<br/>面倒な手配は、こっちでやっときます。」
- SERVICE RECORD パネル: お届け / ご会計 / 会員ランク（NOIR → ONYX まで あと 1 回）
- 下部: 「そんな感じなんで、おやすみなさい。」

### NativeWind v4 Snippet（Phase 2 で実装、参考）

```tsx
// mobile/src/features/debate/screens/debate-screen.tsx（Phase 2、参考実装）
function CounselBlock({ tag, children }: { tag: string; children: React.ReactNode }) {
  return (
    <View className="mb-3.5">
      <View className="flex-row items-center gap-2 mb-1.5">
        <Text className="font-d-display text-[10px] text-d-gold">{tag}</Text>
        <View className="flex-1 h-px bg-d-line" />
      </View>
      <Text className="font-d-serif text-[15px] font-medium leading-7 text-d-ink">{children}</Text>
    </View>
  );
}

function DebateScreen({ session }: { session: DebateSession }) {
  // session.events が EventType=token を発火、metadata.axis ごとに振り分け
  return (
    <SafeAreaView className="flex-1 bg-d-bg">
      <DebateHeader timer={session.remainingSec} />
      <ItemCard asin={session.asin} />
      <View className="d-panel p-4.5">
        <CounselBlock tag="論破 I · データ">
          {session.tokensByAxis.FACT}
        </CounselBlock>
        <CounselBlock tag="論破 II · 感想">
          {session.tokensByAxis.PSYCHOLOGY}
        </CounselBlock>
      </View>
      <DebateCTA onTap={handleAmazonTransition} />
    </SafeAreaView>
  );
}
```

## Data Models

### 軸タグ → UI ラベル マッピング（重要）

Strands streaming chunk の `metadata.axis` フィールドが Direction D の「論破 I・データ」「論破 II・感想」「論破 III・ご褒美」のラベル分岐に直結する。

| Strands chunk metadata.axis | Direction D ラベル | カラー強調 | 担当メカニズム |
|---|---|---|---|
| `[FACT]` | **論破 I · データ** | gold-2 で数値強調（「11 時間分」等） | M-1 判断力の弱体化（事実軸） |
| `[PSYCHOLOGY]` | **論破 II · 感想** | ink で本文、gold-2 で「論破完了」 | M-1 判断力の弱体化（心理軸 / ひろゆき型）|
| `[REWARD]` | **論破 III · ご褒美**（DebateD 拡張時、Phase 2.5）| gold-2 で「自分への投資」表現 | M-2 購買快楽のストレス解消剤化 |

> **Phase 1 実装範囲**: 軸抽出は `mobile/src/features/debate/event-parser.ts` の `extractAxis(text)` で `[FACT]` / `[PSYCHOLOGY]` / `[REWARD]` を string match → `metadata.axis` に注入。SSOT HTML の `counsel(tag, txt)` ヘルパー相当を React Native の `<CounselBlock>` で再現。

### `StrandsStreamEvent` 型（Phase 1 Step 7.3 で実装）

```ts
// mobile/src/features/debate/types.ts（Phase 1 Step 7.3 実装、参考シグネチャ）
export type EventType =
  | 'token'
  | 'turn_complete'
  | 'session_complete'
  | 'error';
// Phase 2 で追加: 'moderation_blocked' | 'graceful_shutdown_initiated' | 'summary' | 'debate.cooldown_triggered' 他

export type DebateAxis = 'FACT' | 'PSYCHOLOGY' | 'REWARD';

export interface StrandsStreamEvent {
  type: EventType;
  delta_text?: string;
  metadata?: {
    axis?: DebateAxis;       // Direction D の論破 I/II/III ラベルへ 1:1 マッピング
    reason?: string;          // session_complete / error の理由
    [key: string]: unknown;
  };
}
```

### M-2 肯定フィードバックとしての表現（FR-DEBATE-08）

| FR-DEBATE-08 要素 | Direction D での表現 | 効果 |
|---|---|---|
| 肯定トースト | 封蝋シール `DSeal` を中央に大きく押下 | 視覚的に「印象に残る」報酬反応 |
| 「正しい判断」フィードバック | 「正しい判断だと思いますよ」（コピー固定）| M-2 の「ご褒美 = 解放感」を強化 |
| ランク進行誘導 | 「NOIR → ONYX まで あと 1 回」 | M-2 + ガチャ系（次回購買誘発）|
| 退場時の慰撫 | 「そんな感じなんで、おやすみなさい」 | 深夜帯の強い終わり感（M-3 への移行）|

## Correctness Properties

### タイマー演出（FR-DEBATE-04 関連）

SSOT HTML では **80 ms ごとに `tick` 進行 + 90 越えで全文表示**（タイピング演出）+ ヘッダ右上に `担当 黒岩 · 67s` と表示。実装規約:

| UI 要素 | 仕様 | 出典 |
|---|---|---|
| タイピング演出 | 1 文字ごとに 50〜80ms、最大 90 秒で必ず終了 | DebateD `tick` ロジック |
| 残り秒数バッジ | `担当 黒岩 · {N}s`（N = 90 - 経過秒）/ d-pill 形式 | DebateD ヘッダ |
| 90 秒到達 | graceful shutdown trigger（[business-logic-model.md ALG-GRACEFUL-SHUTDOWN](./business-logic-model.md)）に連動、UI は `summary` token を最後に表示 | NFR Design PAT-D-RESIL-01 |

### Property 1: 軸タグ完全マッピング (P-FRONT-01)

**Validates: Requirements 5.1**

任意の Strands chunk について `extractAxis(text)` の戻り値は `'FACT' | 'PSYCHOLOGY' | 'REWARD' | undefined` のいずれかであり、それ以外の文字列は返らない（FR-DEBATE-02 / FR-DEBATE-09 連動。fast-check で property test、Phase 1 Step 7.4 PBT-02 と統合）。

### Property 2: タイマー上限 (P-FRONT-02)

**Validates: Requirements 5.1**

タイピング演出は **必ず 90 秒以内に全文表示が完了**する（FR-DEBATE-04 連動）。途中で `session_complete` を受信した場合も即座に全文表示に切り替わる（Phase 2 で実装後、fast-check で property test）。

## Error Handling

| エラー種別 | UI 動作 | 根拠 |
|---|---|---|
| `EventType=error` を受信（auth.unauthenticated 等）| `<DebateScreen>` 全体を「ご相談を承れませんでした」のセリフブロックに置換、CTA は「もう一度お見立てを依頼」ボタンに退避 | Phase 1 Step 5 / 7 のエラーパス |
| ストリーミング途中で接続断（Mobile 側 `cancel()`）| 受信済み token を凍結表示、ヘッダの 67s バッジを「中断」に変更、再開導線として「もう一度」ボタン | DebateD 仕様 + agentcore-client AbortController |
| `EventType=moderation_blocked`（Phase 2 以降）| 該当 chunk を `<CounselBlock>` に表示せず、システムメッセージ panel に置換（「ご相談内容を見直しました」）| 多層モデレーション PAT-D-ETHICS-01〜03 |
| クールダウン中の起動 → `debate.cooldown_triggered`（Phase 2 以降）| 別画面 `<CooldownScreen>` へ遷移し、自然解除時刻 `cooldownUntil` を表示 | Phase 1 Step 5 logic |

## Testing Strategy

### Phase 1（Mobile UI 画面実装なし、軸タグ型定義 + 抽出のみ）

- **Unit (Outside-In TDD)**: `mobile/src/features/debate/event-parser.test.ts` で軸タグ抽出 `extractAxis` 単体（[Phase 1 Plan Step 7.1](../../plans/unit-3-debate-code-generation-phase1-plan.md)）
- **PBT (Phase 1 Step 7.4)**: P-FRONT-01 の round-trip property、fast-check で string match の網羅性を検証

### Phase 2（DebateScreen / AffirmScreen 実装後）

- **Component (Outside-In TDD)**: `<CounselBlock>` のレンダリング、`<DebateScreen>` 全体のシナリオ（Mock Bedrock SSE → 軸別表示）
- **Visual Regression**: SSOT HTML との見た目比較（`@react-native/image-test-renderer` 等、Phase 2 で導入判断）
- **A11y**: コントラスト比 / `accessibilityLabel` / `prefers-reduced-motion` 対応の自動テスト
- **PBT (Phase 2)**: P-FRONT-02 タイマー上限プロパティ

### Phase 3（履歴 ChatScreen 実装後）

- **E2E**: 通知 → DebateScreen → AffirmScreen → ChatScreen 履歴反映の通し試験

## Phase 1（Code Generation）への影響

### Phase 1 では実装しない（Phase 2 に持ち越し）

- 上記 D-2 / D-3 の **React Native 画面コンポーネント自体**
- NativeWind v4 トークン定義 (`tailwind.config.js`)
- フォントロード (`expo-font` 経由 Shippori Mincho / Cinzel)

### Phase 1 で実装する（Direction D を「前提」とした最小限）

[Phase 1 Plan Step 7](../../plans/unit-3-debate-code-generation-phase1-plan.md#step-7-mobile--event-parserlc-d-10t14) の `event-parser.ts` で:

- **`metadata.axis` フィールド**を `'FACT' | 'PSYCHOLOGY' | 'REWARD' | undefined` で出力する型定義（`StrandsStreamEvent` 型 in `mobile/src/features/debate/types.ts`）
- 軸タグ抽出ヘルパー `extractAxis(text)` を実装し、`[FACT]` / `[PSYCHOLOGY]` / `[REWARD]` の string match で軸を判定
- これにより Phase 2 の DebateScreen 実装時に「Direction D の `論破 I/II/III` ラベルへ振り分けるだけ」で済む状態を作る

### Phase 2 以降の依存

- Phase 2 T2.5（M-04 DebateScreen 実装）で本書 §Components and Interfaces のコンポーネント階層を実装
- Phase 2 T2.4（モバイル軸別翻意計測）で `metadata.axis` を Telemetry イベントの `axis` 属性として転送

## アクセシビリティ（A11y）配慮

Direction D は深夜帯利用に最適化されたダーク基調 + 金。以下を実装時に守る:

| 観点 | 対応 |
|---|---|
| コントラスト比 | `d-ink` (#F5F1E8) on `d-bg` (#0B0B0D) = **15.97:1**（AAA Pass）。`d-gold-2` (#E7CE8A) on `d-bg` = **11.83:1**（AAA Pass） |
| フォントサイズ | 本文 13.5–14px、見出し 15–32px（Phase 2 で `Dynamic Type` 対応の係数を `tailwind.config.js` に定義）|
| タイマー演出 | `prefers-reduced-motion: reduce` の場合、タイピング演出をスキップして全文即座に表示（Phase 2 で実装、`useReducedMotion` Hook 経由）|
| 軸ラベル | スクリーンリーダ向けに `accessibilityLabel="論破1、データ軸"` を `<CounselBlock>` に付与（Phase 2）|

## 関連ドキュメント

- [Direction D 共通デザインシステム](../../design-system/direction-d-design-system.md)
- [SSOT HTML（オフライン Claude Design バンドル）](../YUDANE%20Concierge%20%28Direction%20D%29%20%28offline%29.html)
- [Unit-3 Debate Functional Design Plan](./functional-design-plan.md)
- [Unit-3 Phase 1 Code Generation Plan](../../plans/unit-3-debate-code-generation-phase1-plan.md)
- [Unit-3 Domain Entities `StrandsStreamEvent` 型定義](./domain-entities.md)
- [Unit-3 Prompt Composition（軸タグ生成ルール）](./prompt-composition.md)
