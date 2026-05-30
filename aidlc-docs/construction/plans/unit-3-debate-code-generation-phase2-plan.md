# Unit-3 Debate — Code Generation Phase 2 Plan

> **このプランは Unit-3 Phase 2 Code Generation の Single Source of Truth**。Code Generation Part 2 ではこのステップ順に従ってコードを生成し、各ステップ完了時に [x] を付ける。
>
> 参照: [task-breakdown.md Phase 2](../unit-3-debate/functional-design/task-breakdown.md#phase-263--66-p0-機能完成--予選-mvp-デモ) / [Functional Design](../unit-3-debate/functional-design/) / [NFR Design](../unit-3-debate/nfr-design/) / [Infrastructure Design](../unit-3-debate/infrastructure-design/) / [Phase 1 Plan](./unit-3-debate-code-generation-phase1-plan.md) / steering（tech-typescript / tech-python / tech-cdk）
>
> 作成: 2026-05-30 / ステージ: 🟢 CONSTRUCTION / Code Generation Phase 2 Plan
>
> 期間: **2026-06-03〜2026-06-06（4 日）** / 担当: **Member B**
>
> **本計画の目的**: Phase 1 の基盤疎通（empty stub）に **論破ロジックの本格実装** を載せて、ユーザーが「ローカル PC で動作する MVP」を体験できる状態（**L2 ローカル LLM 駆動 MVP**）を構築する。

---

## 0. Phase 2 のコンテキスト

| 項目 | 内容 |
|---|---|
| 目的 | M-1 + M-2 併走プロンプト + Memory STM + Cooldown DDB + Mobile DebateScreen を本格実装し、E2E-01 シナリオ（Cart Intercept → 論破 → 翻意 → Amazon 遷移）を **dev 環境** で pass させる。**ローカル PC では `agentcore dev` + 実 Bedrock Haiku 4.5 + moto/dummy DDB/Memory** で MVP 動作確認できる状態（L2）まで到達する |
| 担当 | Member B（AI 代行実装） |
| 依存 | Phase 1 完了（Step 1〜7）/ Unit-1 platform-stack（SSM 5 個 / Cognito User Pool）/ Unit-2 Auth & Profile（Cognito MFA）|
| 完了条件 | E2E-01 が dev 環境で pass、PBT-03（M-2 reward 必須含有）/ PBT-07（stress_level 集合性）が green、Mobile UI（Direction D）で論破実機動作確認、ローカルモードで `agentcore dev` 駆動 |
| プロジェクト種別 | Phase 1 の上に積み上げ |
| **MVP 動作確認レベル** | **段階的に到達可能**:<br>• **L1 UI 単体動作**（Step 6 完了時点、Direction D の DebateScreen のみで dummy token streaming、フロント単体動作）<br>• **L2 ローカル LLM 駆動 MVP**（Phase 2 全 Step 完了時点、`agentcore dev --port 8080` + 実 Bedrock + in-memory DDB/Memory）<br>• L3（dev 環境統合）は Phase 1 Step 8 + Phase 2 完了後に到達可能 |
| **UI SSOT** | **Direction D「黒服のコンシェルジュ」**。Phase 2 では DebateScreen（D-2）+ AffirmScreen（D-3）を本格実装。軸タグ → ラベル 1:1 マッピングは Phase 1 で構築済（[frontend-design.md](../unit-3-debate/functional-design/frontend-design.md)）|
| **ローカル起動方式** | **`agentcore dev --port 8080`**（公式ローカル開発サーバー、Q15=A 確定方針、uvicorn ベース hot reload）。FastAPI 別建ては不要 |

### Phase 2 で生成するコンポーネント

| LC ID | 論理コンポーネント | 配置 | TDD スタイル | 状態 |
|---|---|---|---|---|
| LC-D-04 | Prompt Composition Engine（6 モジュール） | `backend/src/debate/prompts/` | クラシック TDD | **新規（Phase 2）** |
| LC-D-05 | Stress Estimator | `backend/src/debate/stress.py` | クラシック TDD | **新規（Phase 2）** |
| LC-D-03 | Memory Hook Manager（P0: STM + 組み込み 2 Strategy） | `backend/src/debate/memory_hooks.py` | クラシック TDD | **新規（Phase 2）** |
| LC-D-06 | Cooldown DDB Adapter（main.py 結線）| `backend/src/debate/main.py` 拡張 | クラシック TDD | Phase 1 → Phase 2 結線 |
| LC-D-08 | Affirmation Generator（簡易版） | `backend/src/debate/prompts/affirmation.py` | クラシック TDD | **新規（Phase 2）** |
| LC-D-01 | Debate Entrypoint Router（拡張） | `backend/src/debate/main.py` | クラシック TDD | Phase 1 → Phase 2 拡張 |
| LC-D-02 | Strands Agent Streaming Pipeline（実装） | `backend/src/debate/main.py` 内 Agent 初期化 | クラシック TDD | Phase 1 stub → Phase 2 実装 |
| LC-D-09 | Mobile AgentCore Client | （Phase 1 完成、変更なし）| Outside-In TDD | Phase 1 完成済 |
| LC-D-10 | Mobile Event Parser（拡張）| `mobile/src/features/debate/event-parser.ts` | Outside-In TDD | Phase 1 → Phase 2 Step 5 で EventType 拡張（`debate.cooldown_triggered` 受信ケースを追加、`moderation_blocked` / `graceful_shutdown_initiated` は Phase 3）|
| LC-D-12 | SSM Configuration Loader | （Phase 1 完成、変更なし）| クラシック TDD | Phase 1 完成済 |
| Mobile | M-04 DebateScreen（Direction D）| `mobile/src/features/debate/screens/debate-screen.tsx` | Outside-In TDD | **新規（Phase 2）** |
| Mobile | M-04 AffirmScreen（Direction D）| `mobile/src/features/debate/screens/affirm-screen.tsx` | Outside-In TDD | **新規（Phase 2）** |
| Mobile | DebateSession Store（Zustand）| `mobile/src/features/debate/store/debate-store.ts` | クラシック TDD | **新規（Phase 2）** |
| Mobile | Telemetry 10 イベント拡張 | `mobile/src/features/debate/telemetry.ts` | クラシック TDD | **新規（Phase 2）** |
| Local | ローカル開発モード分岐（Protocol-based DI） | `backend/src/debate/local_mode.py` | クラシック TDD | **新規（Phase 2、L2 MVP のため）** |

### Phase 2 では実装しないもの（Phase 3 以降）

| 領域 | 理由 |
|---|---|
| Strands graceful shutdown 80s | Phase 3 T3.1（L1 機能面の穴塞ぎ） |
| Memory streamDeliveryResources + S3 export | Phase 3 T3.2 |
| Bedrock Guardrails streaming + 正規表現多層 | Phase 3 T3.3 |
| custom Memory Strategy `m1_m2_axis_extractor` | Phase 4 T4.2 |
| RuntimeEndpoint canary | Phase 5 T5.1 |
| `action='request_affirmation'` 用の Affirmation 別ターン Bedrock 呼び出し | Phase 2 T2.5 で簡易実装、Phase 4 で本格化 |

---

## 1. コード生成ステップ（Code Generation Part 2 で順次実行）

> **TDD 規約**: AGENTS.md §12.4 に従い、各 Step は Red → Green → Refactor → PBT 補強 の順序で生成する。Phase 1 と同じく、Backend = クラシック TDD / Mobile = Outside-In TDD。
>
> **依存順序**: Step 1（Stress）→ Step 2（Prompt 6 モジュール）→ Step 3（main.py 拡張）→ Step 4（ローカルモード）→ Step 5（Mobile Store）→ Step 6（Mobile DebateScreen）→ Step 7（Mobile AffirmScreen）→ Step 8（Telemetry）→ Step 9（E2E-01 + ローカル疎通）

### Step 1: Backend / Stress Estimator（T2.2、PBT-07）

**目的**: Memory + ヒューリスティックでストレスレベルを `low | mid | high` の 3 種に判定する純粋関数を実装。プロンプト合成（Step 2）が `stress_level` を入力として受け取るため、Step 1 で先行実装。

- [ ] **Step 1.1（Red）**: `backend/tests/debate/test_stress.py`
  - test: `client_signals=空 + memory=空 → stress_level='low'`
  - test: `current_hour_jst=23（深夜帯）→ +2 加算 → stress_level='mid'` 
  - test: `current_hour_jst=12（昼）+ recent_cart_intercepts=3 + recent_debate_refuses=1 → +2 加算 → mid`
  - test: `深夜帯 + late_night_signin=True + cart_intercepts=3 → score=4 → high`
  - test: `Memory に 'stress_high' signal 含む → +1 加算`
  - test: `Memory retrieve が None でも例外を上げず stress_level='low' を返す`（fail-safe）

- [ ] **Step 1.2（Green）**: `backend/src/debate/stress.py`
  - `estimate_stress_level(actor_id, now, client_signals, memory_signals=None) -> StressLevelResult`
  - スコア配点（business-rules STRESS-03）:
    - 深夜帯（23-04 時）= +2
    - 残業帯（18-23 時）= +1
    - Memory 'high' signals = +1〜+2
    - cart_intercepts >= 3 = +1
    - recent_refuses >= 1 = +1
    - late_night_signin = +1
  - スコアレベル変換: score >= 4 → high / score >= 2 → mid / それ以外 → low

- [ ] **Step 1.3（Refactor）**: `StressLevelResult`（`level` / `score` / `signals_used`）を `domain/results.py` に追加、Telemetry に level のみ送信（PII 配慮）

- [ ] **Step 1.4（PBT 補強）**: `backend/tests/debate/property/test_stress_property.py`
  - PBT-07 集合性: `任意の入力で必ず 'low' | 'mid' | 'high' のいずれかを返す`（Hypothesis）
  - PBT-07 範囲: `score >= 0` を保証

**完了条件**: `pytest tests/debate/test_stress.py + property/test_stress_property.py` 全 green、Coverage Line 95%+ Branch 90%+。

**ドキュメント**: `aidlc-docs/construction/unit-3-debate/code/stress-estimator-summary.md`

---

### Step 2: Backend / Prompt Composition Engine 6 モジュール（T2.1、PBT-03）

**目的**: M-1 + M-2 併走プロンプトを 6 ファイルに分離して構造化。stress_level=mid/high で必ず m2_reward_axis が含まれる **PBT-03 不変条件** を保証。

- [ ] **Step 2.1（Red）**: `backend/tests/debate/prompts/test_compose.py`
  - test: `compose_debate_prompt(stress_level='low') の axes に 'reward' が含まれない`
  - test: `compose_debate_prompt(stress_level='mid') の axes に 'reward' が含まれる`
  - test: `compose_debate_prompt(stress_level='high') の axes に 'reward' が含まれる`
  - test: `axes に必ず 'fact' と 'psychology' が含まれる`
  - test: `len(text) <= 8000`（PROMPT_MAX_LENGTH_CHARS）
  - test: `text に [FACT] / [PSYCHOLOGY] セクションマーカーが含まれる`
  - test: `stress=high の text に [REWARD] マーカーが含まれる`
  - test: `compose_debate_prompt は純関数（同一入力 → 同一出力）`
  - test: `MemoryContext が空でも preferred_axis='fact' で動作する`（fail-safe）

- [ ] **Step 2.2（Green）**: `backend/src/debate/prompts/__init__.py` + 6 ファイル
  - `prompts/base.py`: BASE_TEMPLATE（NG-1〜8 ガードレール指示文 + トーン指示）
  - `prompts/m1_fact_axis.py`: M1_FACT_AXIS_TEMPLATE（時給換算 / 在庫希少性 / カレンダー整合）
  - `prompts/m1_psychology_axis.py`: M1_PSYCHOLOGY_AXIS_TEMPLATE（preferred_axis ベース個別最適化）
  - `prompts/m2_reward_axis.py`: M2_REWARD_AXIS_TEMPLATE（stress_level=mid/high 用、論理優位ディベート系）
  - `prompts/affirmation.py`: AFFIRMATION_TEMPLATE（翻意後の肯定 FB、Phase 2 では簡易版）
  - `prompts/compose.py`: `compose_debate_prompt(user_input, asin, stress_level, memory_context) -> ComposedPrompt`

- [ ] **Step 2.3（Refactor）**: `ComposedPrompt`（domain/results.py に追加）+ `MemoryContext` 型定義（domain/memory_context.py に追加、Phase 2 では空 dict で動作可能）

- [ ] **Step 2.4（PBT 補強）**: `backend/tests/debate/property/test_compose_property.py`
  - PBT-03 不変条件: `任意の stress_level='mid' or 'high' で必ず 'reward' in composed.axes`（Hypothesis）
  - PBT-08: `text 長さが必ず 8000 以下`
  - PBT-08: `任意のユーザー入力 + ASIN で text に [FACT] / [PSYCHOLOGY] マーカーが含まれる`

**完了条件**: `pytest tests/debate/prompts/` 全 green、Coverage Line 90%+ Branch 85%+、PBT-03 / PBT-08 が green。

**ドキュメント**: `aidlc-docs/construction/unit-3-debate/code/prompts-summary.md`

---

### Step 3: Backend / Strands Agent 統合（Bedrock + Memory + Cooldown 結線、T2.3 / T2.4 拡張、P2C-2 修正）

**目的**: Phase 1 の `_run_streaming_agent` dummy stub を **Strands Agent 経由の実 Bedrock 呼び出し**（`agent.stream_async()`、Q3=A 確定方針）+ Memory Hook + Cooldown 結線に置換。boto3 で Bedrock を直接呼ばず、Strands SDK の役割を尊重する。

- [ ] **Step 3.1（Red）**: `backend/tests/debate/test_main_integration.py`
  - test: `compose_debate_prompt() の出力が Strands Agent の prompt として渡される`（Strands Agent をモック）
  - test: `agent.stream_async() の chunk が token event として yield される`
  - test: `Memory `create_event` が セッション開始時 + 各 turn で呼ばれる`（MemoryHook をモック）
  - test: `Strands Agent の bedrock_kwargs に SSM `model-id` が反映される`
  - test: `kill_switch enabled で agent.stream_async が呼ばれない`（PAT-D-COST-04）
  - test: `論破セッション後、increment_refuse_count が action='refuse' で呼ばれる`

- [ ] **Step 3.2（Green）**: `backend/src/debate/main.py` 拡張 + `backend/src/debate/memory_hooks.py` 新規
  - **Strands Agent を実 import**（`from strands import Agent` + `from bedrock_agentcore.runtime import BedrockAgentCoreApp`）
  - `agent = Agent(model=MODEL_ID, hooks=[DebateMemoryHook(memory_id=DEBATE_MEMORY_ID)], callback_handler=None)` に拡張
  - `_run_streaming_agent` を Strands 経由実装に置換:
    - `stress_level = estimate_stress_level(actor_id, now, client_signals)`
    - `memory_context = await build_memory_context_via_hook(actor_id)`（MemoryHook 経由、ローカルモードでは empty MemoryContext）
    - `composed = compose_debate_prompt(user_input, asin, stress_level, memory_context)`
    - **`async for event in agent.stream_async(composed.text):`** → chunk を順に yield + EventType=token に変換
    - turn_complete + session_complete を yield
  - `memory_hooks.py`: `DebateMemoryHook(BaseHook)` で `on_session_start` / `on_turn_complete` を実装、Memory `create_event` / `retrieve_memories` を Strands Agent から自動呼び出し
  - `action='refuse'` payload を受けて `increment_refuse_count` を呼び出し（Phase 1 で先行宣言済の API を結線）

- [ ] **Step 3.3（Refactor）**: Strands Agent の `bedrock_kwargs` 設定（Phase 3 で `guardrailIdentifier` を追加するための拡張ポイント）

- [ ] **Step 3.4（PBT 補強）**: `backend/tests/debate/property/test_main_property.py`
  - PBT-04 idempotency: `同一 client_session_id で 2 回起動しても DDB Cooldowns の状態が変わらない`

**完了条件**: `pytest tests/debate/test_main_integration.py` 全 green、Coverage Line 85%+ Branch 80%+。

**ドキュメント**: `aidlc-docs/construction/unit-3-debate/code/main-integration-summary.md`

---

### Step 4: Backend / ローカル開発モード（Protocol-based DI、L2 MVP のため、P2C-1 + P2M-4 修正）

**目的**: ローカル PC で `agentcore dev --port 8080` 起動時に DDB Cooldowns / AgentCore Memory を **in-memory dict（Protocol-based DI）** で代替する切替フラグを追加。**実 Bedrock は呼び出す**（L2 構成）。`moto` は使わず軽量な Protocol DI で実装。

- [ ] **Step 4.1（Red）**: `backend/tests/debate/test_local_mode.py`
  - test: `DEBATE_LOCAL_MODE=true で check_cooldown が in-memory dict から読む`
  - test: `DEBATE_LOCAL_MODE=true で increment_refuse_count が in-memory dict に書く`
  - test: `DEBATE_LOCAL_MODE=true で Memory retrieve が空 MemoryContext を返す`
  - test: `DEBATE_LOCAL_MODE=false（既定）で本番 DDB / Memory が呼ばれる`
  - test: `JWT 検証も `DEBATE_LOCAL_MODE=true` で dummy actor_id 'local-user' を返す`
  - test: `Protocol 互換性: LocalCooldownStore と本番の cooldown.check_cooldown が同じシグネチャ`

- [ ] **Step 4.2（Green）**: `backend/src/debate/local_mode.py` + `backend/src/debate/protocols.py`
  - `protocols.py`: `CooldownStoreProtocol` / `MemoryStoreProtocol` を `typing.Protocol` で定義
  - `local_mode.py`:
    - `is_local_mode() -> bool`（環境変数 `DEBATE_LOCAL_MODE` チェック）
    - `LocalCooldownStore`（in-memory dict、Protocol を満たす）
    - `LocalMemoryStore`（empty MemoryContext + 任意の preferred_axis='fact' を返す、Protocol を満たす）
    - `local_parse_jwt_actor_id()`（`'local-user'` を返す）
    - `get_cooldown_store() -> CooldownStoreProtocol`（local / 本番を切替）
    - `get_memory_store() -> MemoryStoreProtocol`（同上）
  - `cooldown.py` / `main.py` から `store = get_cooldown_store()` で切替（`if is_local_mode():` 分岐は最小化）

- [ ] **Step 4.3（Refactor）**: 環境変数 `DEBATE_LOCAL_MODE=true|false` を `.env.local` ファイルでサポート、ローカル起動スクリプト `backend/scripts/run_local.sh` を新規作成
  - **スクリプト内容**: `agentcore dev --port 8080 backend.src.debate.main:app` を呼び出す（FastAPI 別建てなし、Q15=A 公式サーバー）
  - 環境変数の export: `DEBATE_LOCAL_MODE=true`、`ENV_NAME=dev`、`AWS_REGION=ap-northeast-1`

- [ ] **Step 4.4**: ドキュメント `aidlc-docs/construction/unit-3-debate/code/local-dev-guide.md`
  - 前提: AWS Bedrock Haiku 4.5 のモデルアクセス申請承認 + `~/.aws/credentials` 設定
  - 起動手順: `cd backend && bash scripts/run_local.sh`（**`agentcore dev` で uvicorn 起動 + 実 Bedrock + in-memory DDB/Memory**）
  - Mobile 側: `EXPO_PUBLIC_DEBATE_RUNTIME_URL=http://localhost:8080` で接続
  - 注意点: 完全オフラインは不可（Bedrock は AWS）、料金 1 セッション $0.005 程度

**完了条件**: `pytest tests/debate/test_local_mode.py` 全 green、`bash scripts/run_local.sh` でローカル `agentcore dev` 起動成功。

**ドキュメント**: `aidlc-docs/construction/unit-3-debate/code/local-mode-summary.md` + `local-dev-guide.md`

---

### Step 5: Mobile / DebateSession Store（Zustand）+ event-parser 拡張

**目的**: Phase 1 で実装した `agentcore-client.ts` + `event-parser.ts` を統合する状態管理層を Zustand で実装。Phase 2 で必要な拡張 EventType（`debate.cooldown_triggered`）を `event-parser.ts` に追加（`moderation_blocked` / `graceful_shutdown_initiated` は Phase 3）。論破画面（Step 6）が依存する。

- [ ] **Step 5.1（Red）**: `mobile/src/features/debate/store/debate-store.test.ts`
  - test: `startSession(asin, trigger) で論破セッション開始、tokensByAxis が空 dict`
  - test: `agentcore-client が yield する Uint8Array を event-parser で StrandsStreamEvent に変換し、token event 受信で tokensByAxis[axis] に append`
  - test: `session_complete event 受信で sessionComplete=true`
  - test: `error event 受信で error フィールドにセット`
  - test: `90 秒経過で countdownExpired=true（タイマー）`
  - test: `cancel() で AbortController が abort、tokensByAxis は保持`
  - test: `debate.cooldown_triggered event 受信で cooldownActive=true + cooldownUntil をセット`

- [ ] **Step 5.2（Green）**: 
  - `mobile/src/features/debate/store/debate-store.ts`: `useDebateStore = create<DebateState>(...)` Zustand store
    - state: `asin / trigger / tokensByAxis / sessionComplete / error / countdownStartedAt / countdownExpired / cooldownActive / cooldownUntil`
    - actions: `startSession / appendToken / completeSession / setError / cancel / reset / handleCooldown`
  - `mobile/src/features/debate/event-parser.ts` 拡張: `EventType` に `'debate.cooldown_triggered'` を追加（Phase 2 範囲）

- [ ] **Step 5.3（Refactor）**: タイマー制御を `useDebateTimer(startedAt, durationSec=90)` フックに分離（DebateScreen から再利用）

**完了条件**: `vitest run src/features/debate/store/debate-store.test.ts + event-parser.test.ts` 全 green、Coverage Line 85%+ Branch 80%+。

**ドキュメント**: `aidlc-docs/construction/unit-3-debate/code/debate-store-summary.md`

---

### Step 6: Mobile / DebateScreen（Direction D 適用、★コア）

**目的**: Direction D「黒服のコンシェルジュ」の論破画面 D-2 を React Native + NativeWind v4 で本格実装。タイピング演出 + 90 秒タイマー + 軸別ラベル（論破 I・データ / 論破 II・感想 / 論破 III・ご褒美）。

- [ ] **Step 6.1（Red）**: `mobile/src/features/debate/screens/debate-screen.test.tsx`
  - test: `初期表示でヘッダ「迷い、論破します」+ 担当 黒岩 · 90s タイマー`
  - test: `token event の delta_text に [FACT] が含まれる → 論破 I・データ ブロックに表示`
  - test: `token event の [PSYCHOLOGY] → 論破 II・感想 ブロックに表示`
  - test: `[REWARD] token → 論破 III・ご褒美 ブロックに表示`
  - test: `90 秒経過でタイマー 0s + summary が表示される`
  - test: `error event で「ご相談を承れませんでした」+ 「もう一度」ボタン表示`
  - test: `「論破されたので買う」ボタン押下で onAmazonTransition コールバック発火`
  - test: `「それでも感想で見送る」ボタン押下で onRefuse コールバック発火`

- [ ] **Step 6.2（Green）**: 
  - `mobile/src/features/debate/screens/debate-screen.tsx`（Direction D HTML の `DebateD` 関数を React Native に移植）
  - `mobile/src/features/debate/components/debate-header.tsx`（タイマーバッジ）
  - `mobile/src/features/debate/components/item-card.tsx`（商品カード）
  - `mobile/src/features/debate/components/counsel-block.tsx`（軸別セクション、frontend-design.md §3 NativeWind 例準拠）
  - `mobile/src/features/debate/components/quick-replies.tsx`（[いや高くない？] 等）
  - `mobile/src/features/debate/components/debate-cta.tsx`（CTA ボタン + 見送りリンク）

- [ ] **Step 6.3（Refactor）**: NativeWind v4 設定（`tailwind.config.js`）に Direction D デザイントークン（`d-bg` / `d-gold` / `d-gold-2` / `d-ink` 等）を追加

- [ ] **Step 6.4（PBT 補強）**: `mobile/src/features/debate/screens/debate-screen.property.test.tsx`
  - PBT P-FRONT-01: `任意の token event で軸タグ → 論破 I/II/III ラベルへの 1:1 マッピングが破綻しない`（fast-check）

**完了条件**: `vitest run src/features/debate/screens/debate-screen.test.tsx` 全 green、Coverage Line 85%+ Branch 80%+、Direction D HTML との見た目整合（手動レビュー）。

**ドキュメント**: `aidlc-docs/construction/unit-3-debate/code/debate-screen-summary.md`

---

### Step 7: Mobile / Affirm 純ロジック（封蝋シール演出は実機ビルド時に追加）

**目的**: 翻意後の AffirmScreen の純ロジック層を実装。M-2（購買快楽の解放感）の物理層成立を「肯定 FB の取得 + 表示メタデータ」のレベルで完成。React Native コンポーネント（`<DSeal>` 封蝋シール）は実機ビルド時に追加。

- [ ] **Step 7.1（Red）**: `mobile/src/features/debate/screens/affirm-view-model.test.ts`
  - test: `buildAffirmViewModel(asin, sessionId, fallbackText) で affirmation メタが返る`
  - test: `acceptedAt フィールドが ISO 8601 で生成される`
  - test: `serviceRecordId が #503-XXXXXXX 形式で発行される`
  - test: `headlineText が「はい、論破完了。」固定文字列`
  - test: `bodyText が 「正しい判断だと思いますよ。面倒な手配は、こっちでやっときます。」`
  - test: `dismissText が「そんな感じなんで、おやすみなさい。」`
  - test: `affirmation メタは PII を含まない`（NFR-SEC-DEBATE-04）

- [ ] **Step 7.2（Green）**: `mobile/src/features/debate/screens/affirm-view-model.ts`
  - `buildAffirmViewModel({asin, sessionId, fallbackText, now}) -> AffirmViewModel` 純関数
  - 固定コピー（Direction D D-3 SSOT より）

- [ ] **Step 7.3（Refactor）**: `serviceRecordId` 生成ロジックを `crypto.randomUUID()` ベースに（決勝で実際の注文番号 prefix と置換しやすく）

**完了条件**: `vitest run src/features/debate/screens/affirm-view-model.test.ts` 全 green、Direction D HTML（D-3）の固定文字列と整合。

**注**: React Native コンポーネント（`<AffirmScreen>` / `<DSeal>` 封蝋シール `react-native-reanimated`）は Phase 2 範囲外、実機ビルド時に着手。

**ドキュメント**: `aidlc-docs/construction/unit-3-debate/code/affirm-screen-summary.md`

---

### Step 8: Mobile + Backend / Telemetry 10 イベント（T2.6、P2m-1 修正）

**目的**: M-13 Telemetry に Unit-3 専用 10 イベントを追加。Phase 2 では **送信パイプ整備が主目的**、`moderation_blocked` / `graceful_shutdown_initiated` の **イベント発火元は Phase 3** で完成（Phase 2 では送信スキーマと API を整備）。

- [ ] **Step 8.1（Red）**: `mobile/src/features/debate/telemetry.test.ts`
  - test: `debate.session_started イベントが発火される`
  - test: `debate.token_streamed が token event 受信ごとに発火される`
  - test: `debate.refused が「それでも感想で見送る」押下で発火`
  - test: `debate.agreed が「論破されたので買う」押下で発火`
  - test: `debate.session_complete{reason='agreed'|'refused'|'graceful_timeout'} が発火`
  - test: `debate.cooldown_triggered イベントが発火`
  - test: `debate.affirmation_shown イベントが発火`
  - test: `debate.moderation_blocked / debate.graceful_shutdown_initiated は **送信スキーマと API のみ整備**（発火元は Phase 3）`
  - test: `debate.stress_estimated{level} イベントが Backend から送信される`

- [ ] **Step 8.2（Green）**:
  - `mobile/src/features/debate/telemetry.ts`（M-13 TelemetryClient 経由で 10 イベント送信、Phase 3 で発火元結線）
  - `backend/src/debate/main.py` 拡張（`debate.stress_estimated` 等の Backend 発火イベント追加）

- [ ] **Step 8.3（Refactor）**: イベント名定数を `shared/telemetry-contracts/` に集約

**完了条件**: `vitest run src/features/debate/telemetry.test.ts + pytest tests/debate/test_telemetry.py` 全 green。Phase 2 で発火配線するのは 8 イベント（`session_started` / `token_streamed` / `refused` / `agreed` / `session_complete` / `cooldown_triggered` / `affirmation_shown` / `stress_estimated`）、`moderation_blocked` / `graceful_shutdown_initiated` の **2 イベントは送信スキーマのみで完了**（Phase 3 で発火元 = Bedrock Guardrails / Strands graceful shutdown 80s から呼び出し）。

**ドキュメント**: `aidlc-docs/construction/unit-3-debate/code/telemetry-summary.md`

---

### Step 9: E2E-01 シナリオ + ローカル疎通確認

**目的**: Cart Intercept → 論破セッション開始 → 翻意 → Amazon 遷移の E2E-01 シナリオを実装し、**ローカル PC で MVP 動作確認**（L2）を完了する。

- [ ] **Step 9.1（Red、E2E）**: `mobile/src/test/e2e/debate-e2e-01.test.tsx`
  - test: `カート介入通知タップ → 論破セッション開始 → token streaming 受信`
  - test: `90 秒以内に「論破されたので買う」押下 → AffirmScreen 遷移 → Amazon 遷移コールバック発火`
  - test: `初回 token 受信が 3 秒以内（FR-DEBATE-03、Mock Bedrock では即時）`

- [ ] **Step 9.2（Green）**: 
  - `mobile/src/test/e2e/setup-mock-server.ts`（msw で Backend Mock）
  - 既存の Mobile features を組み合わせて E2E-01 シナリオを実装

- [ ] **Step 9.3（ローカル疎通確認、★MVP 動作確認）**:
  - **Backend ローカル起動**: `cd backend && DEBATE_LOCAL_MODE=true bash scripts/run_local.sh` で FastAPI :8080 起動
  - **Mobile ローカル起動**: `cd mobile && EXPO_PUBLIC_DEBATE_RUNTIME_URL=http://localhost:8080 npm run dev`
  - **AWS 認証**: `~/.aws/credentials` で apne1 アクセス可能、Bedrock Haiku 4.5 モデルアクセス承認済
  - **動作確認シナリオ**:
    1. Mobile アプリで論破セッションを開始
    2. ユーザー入力「でも欲しい」を送信
    3. 実 Bedrock Haiku 4.5 から streaming で論破文が返る（M-1 + M-2 併走）
    4. 軸タグ抽出で「論破 I・データ / 論破 II・感想」が表示される
    5. 「論破されたので買う」押下 → AffirmScreen 遷移 → 封蝋シール表示
  - **期待結果**: ローカル PC のみで論破ロジックが動作（DDB / Memory はローカル代替、Bedrock のみ実呼び出し）

- [ ] **Step 9.4**: Phase 2 完了サマリ作成
  - `aidlc-docs/construction/unit-3-debate/code/phase2-summary.md`
  - 生成ファイル一覧、TDD サイクル実績、Coverage 値、E2E-01 結果、ローカル MVP 動作スクリーンショット

- [ ] **Step 9.5**: aidlc-state.md / 本プランのチェックボックス最終更新

**完了条件**: 全 Step が [x] 状態、E2E-01 が dev / ローカル両方で pass、PBT-03 + PBT-07 + PBT-08 green、ローカル MVP 動作確認成功、aidlc-state.md / Phase 2 完了マーク。

---

## 2. Phase 2 完了後の主要ファイル一覧

```
backend/
├── src/debate/
│   ├── main.py                         # 拡張（Strands Agent 統合 + Memory Hook + Cooldown 結線）
│   ├── stress.py                       # 新規（Step 1）
│   ├── memory_hooks.py                 # 新規（Step 3）
│   ├── local_mode.py                   # 新規（Step 4、L2 MVP のため）
│   ├── protocols.py                    # 新規（Step 4、CooldownStoreProtocol / MemoryStoreProtocol）
│   ├── prompts/                        # 新規ディレクトリ（Step 2）
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── m1_fact_axis.py
│   │   ├── m1_psychology_axis.py
│   │   ├── m2_reward_axis.py
│   │   ├── affirmation.py
│   │   └── compose.py
│   └── domain/
│       ├── memory_context.py           # 新規（MemoryContext / OutcomeRecord 等）
│       └── results.py                  # 拡張（StressLevelResult / ComposedPrompt 追加）
├── tests/debate/
│   ├── test_stress.py                  # 新規
│   ├── test_main_integration.py        # 新規
│   ├── test_local_mode.py              # 新規
│   ├── prompts/
│   │   ├── __init__.py
│   │   └── test_compose.py             # 新規
│   └── property/
│       ├── test_stress_property.py     # 新規（PBT-07）
│       ├── test_compose_property.py    # 新規（PBT-03 / PBT-08）
│       └── test_main_property.py       # 新規（PBT-04 idempotency）
└── scripts/
    └── run_local.sh                    # 新規（agentcore dev 起動スクリプト、L2 のため）

mobile/src/features/debate/
├── screens/
│   ├── debate-screen.tsx               # 新規（Step 6、Direction D 本格実装）
│   ├── debate-screen.test.tsx
│   ├── debate-screen.property.test.tsx
│   ├── affirm-screen.tsx               # 新規（Step 7）
│   └── affirm-screen.test.tsx
├── components/
│   ├── debate-header.tsx
│   ├── item-card.tsx
│   ├── counsel-block.tsx
│   ├── quick-replies.tsx
│   ├── debate-cta.tsx
│   └── d-seal.tsx                      # 封蝋シール（Step 7）
├── store/
│   ├── debate-store.ts                 # 新規（Zustand）
│   └── debate-store.test.ts
├── hooks/
│   └── use-debate-timer.ts             # 新規（Step 5.3 Refactor）
└── telemetry.ts                        # 新規（Step 8）

mobile/src/test/e2e/
├── setup-mock-server.ts                # 新規（msw Backend Mock）
└── debate-e2e-01.test.tsx              # 新規（E2E-01 シナリオ）

mobile/
└── tailwind.config.js                  # Direction D デザイントークン追加（Step 6.3）

aidlc-docs/construction/unit-3-debate/code/
├── stress-estimator-summary.md         # 新規
├── prompts-summary.md                  # 新規
├── main-integration-summary.md         # 新規
├── local-mode-summary.md               # 新規
├── local-dev-guide.md                  # 新規（★MVP 動作確認のため）
├── debate-store-summary.md             # 新規
├── debate-screen-summary.md            # 新規
├── affirm-screen-summary.md            # 新規
├── telemetry-summary.md                # 新規
└── phase2-summary.md                   # 新規（Phase 2 全体サマリ）
```

---

## 3. ストーリートレーサビリティ

Phase 2 で完成する主担当ストーリー（[stories.md](../../inception/user-stories/stories.md) 準拠、`US-01-XX` 表記）:

| ストーリー | Step | 完了条件 |
|---|---|---|
| **US-01-01**（カート停滞を 1 分論破で翻意）| Step 3 + Step 6 | Mobile から論破セッション起動 → Bedrock streaming → UI 表示 → 翻意 → AffirmScreen |
| **US-01-02**（リール「買わない」を事実ベース反論で翻意）| Step 2 + Step 6 | M-1 fact_axis ベースで論破、軸タグ → 「論破 I・データ」ラベル切替 |
| **US-01-04**（連打で論破が個別最適化）| Step 2 + Step 3（Memory Hook）| MemoryContext.preferred_axis を起点に m1_psychology_axis を組み立て |
| **US-01-05**（3 回連続拒否でクールダウン）| Step 3（main.py 結線）| `action='refuse'` payload → increment_refuse_count → 3 回目で cooldown event |
| **US-01-03**（カレンダー予定を論破材料に）| Step 2 | Phase 2 では空 calendar_context で動作、Unit-6 完成後に本格実装 |
| **US-09**（M-2 ストレス × ご褒美軸）| Step 1 + Step 2 | stress_level=mid/high で reward 軸を必ず含む（PBT-03） |
| 肯定 FB | Step 7 | AffirmScreen で「正しい判断」+ 封蝋シール（FR-DEBATE-08） |

---

## 4. 依存・インターフェース

### 上流依存
- **Phase 1 完了（Step 1〜7）**: 全Phase 1 ロジックを利用
- **Unit-1 platform-stack**: SSM 5 個（kms-key-arn / userpool-id 等）/ Cognito User Pool / KMS Key
- **Unit-2 Auth & Profile**: Cognito User Pool MFA フロー（実機デモのみ）

### 下流提供（Phase 3 以降の Step が利用）
- 完成した論破ロジック → Phase 3 で graceful shutdown 80s + Guardrails 多層を上載せ
- DebateScreen / AffirmScreen → Phase 3 以降の Mobile 拡張で再利用
- Memory Hook（P0 STM のみ）→ Phase 4 で custom Strategy `m1_m2_axis_extractor` を追加

---

## 5. 完了基準（Phase 2 全体）

- [ ] Step 1〜9 すべて [x]
- [ ] Backend Coverage: Line 90%+ / Branch 85%+（重点 6 ファイル: stress / prompts/* / main / local_mode）
- [ ] Mobile Coverage: Line 85%+ / Branch 80%+（screens / store / components）
- [ ] PBT-03 / PBT-07 / PBT-08 が green、shrinking + seed ログ確認
- [ ] dev 環境で E2E-01 が pass（Phase 1 Step 8 完了が前提条件）
- [ ] **★ローカル PC で MVP 動作確認成功（L2: agentcore dev + 実 Bedrock + moto/dummy）**
- [ ] 生成ドキュメント 10 件が `aidlc-docs/construction/unit-3-debate/code/` に揃う
- [ ] aidlc-state.md Phase 2 完了マーク

---

## 6. スコープ外（Phase 3 以降）

| Phase | 内容 |
|---|---|
| Phase 3（6/7〜6/9）| Strands graceful shutdown 80s / Memory streamDeliveryResources + S3 export / Bedrock Guardrails 多層モデレーション完成 |
| Phase 4（6/10〜6/13）| custom Memory Strategy `m1_m2_axis_extractor` / PBT 全面適用（NFR-PBT-DEBATE-01〜10） |
| Phase 5（6/13）| RuntimeEndpoint canary 追加（dev / staging / prd） |
| Phase 6（6/16〜6/26）| 統合テスト + cdk-nag green 確認 + 性能テスト + 決勝前カナリアリリース + リハーサル |

---

## 7. リスクと緩和策

| リスク | 影響 | 緩和策 |
|---|---|---|
| **Bedrock Haiku 4.5 のモデルアクセス申請が承認されていない** | **高（Step 3 / Step 9 ブロッカー）**| Phase 2 開始前 = Phase 1 Step 8 着手時に dev アカウントで Bedrock コンソールから申請、承認まで 1〜2 営業日。**Phase 1 完了サマリ §6.1 でもチェック項目化済**。代替: Step 3〜8 の実装は申請承認待ちでも進行可（テストで Strands Agent をモック）、Step 9 の MVP 動作確認のみ承認後に延期 |
| Strands SDK / bedrock-agentcore SDK の Python 3.13 互換性が不安定 | 高（Step 3 / Step 4） | Phase 2 開始時に `pip install bedrock-agentcore strands-agents` でインストール検証、不安定なら `pip install --no-deps` で個別解決。Phase 1 で `requirements.txt` に列挙済 |
| `agentcore dev` が macOS で起動しない | 中（Step 4 / Step 9）| `agentcore dev --port 8080` で uvicorn が起動するか Phase 2 序盤で検証、不可なら uvicorn を直接呼ぶ `python -m uvicorn backend.src.debate.main:app --port 8080 --reload` で代替 |
| Direction D の NativeWind v4 移植コスト | 中（Step 6）| `tailwind.config.js` にデザイントークンを集中管理、`<CounselBlock>` 等の小さなコンポーネントから段階的に作る |
| `react-native-reanimated` の封蝋シールアニメーション動作不良 | 低（Step 7）| 動作不良時は CSS Transition で代替、reduced-motion 対応で機能優先 |
| Bedrock 呼び出しコスト超過 | 低（Step 9）| ローカル MVP 動作確認時は 1 セッション $0.005 程度、$10/日上限を Cost Anomaly Detection で監視 |
| ローカル動作確認が macOS / Linux でしか動かない | 低（Step 4 / Step 9）| `run_local.sh` は bash 前提、Windows 向けは PowerShell 版を Phase 5 で追加（決勝チームの環境次第） |
| プロンプト 6 モジュールの分割粒度が細かすぎる | 低（Step 2）| Phase 2 では 6 モジュールで完成させ、Phase 4 の改善は B-306 backlog 化済 |
| Strands Agent の `bedrock_kwargs` で SSM `model-id` を渡す方法が不明 | 中（Step 3） | Phase 2 序盤で Strands SDK の docs を確認、`Agent(model=MODEL_ID)` の `model` 引数で SSM 取得値を渡す方式が標準。`bedrock_kwargs` は Phase 3 の Guardrails 関連付け時に使う |

---

## 8. ハッカソン評価軸へのインパクト

| 評価軸 | 本 Phase 2 Plan による貢献 |
|---|---|
| ビジネス意図の明確さ | M-1 + M-2 併走プロンプトを 6 モジュール構造化、PBT-03 で「stress=mid/high → reward 軸必須」を property 化、ダメ化 3 段メカニズムが物理層に降りる |
| Unit 分解の適切さ | Step 1〜9 を TDD サイクル（Red → Green → Refactor → PBT 補強）で構造化、Member B 単独完遂可能 |
| 創造性とテーマ適合性 | Direction D「黒服のコンシェルジュ」を本格実装、論破 I/II/III ラベル切替で M-1 + M-2 併走 UI が成立、封蝋シールで M-2 の解放感を視覚化 |
| ドキュメント品質 | Phase 2 完了時に code summary 10 件、TDD サイクルログ、E2E-01 結果、ローカル MVP スクリーンショット全て traceable |
| AI-DLC プロセス（予選評価軸） | Code Generation の TDD 順序を Plan に明記（Backend 5 Step → Mobile 4 Step）、AI が Plan に従って実装する証跡 |
| 決勝デモ完成度 | Phase 2 完了後に Phase 3〜6 の前提が整い、6/26 決勝デモまでの 20 日間を計画的に進行可能 |

---

## 9. ローカル MVP 動作確認の前提（重要）

**L2: ローカル LLM 駆動 MVP** に到達するには以下の前提が満たされる必要がある:

| 項目 | 内容 | 達成方法 |
|---|---|---|
| AWS Builder ID | apne1 アカウントへのアクセス | ハッカソン参加要件、達成済 |
| **Bedrock Haiku 4.5 モデルアクセス** | apne1 リージョンで Claude Haiku 4.5 にアクセス | **AWS コンソールから申請、承認まで 1〜2 営業日**（Phase 2 開始前に必須） |
| ローカル AWS 認証情報 | `~/.aws/credentials` で apne1 アクセス | `aws configure` で設定 |
| Python 3.13 + 依存 | hackson virtualenv に Phase 1 + Phase 2 依存をインストール | Phase 1 で完了、Phase 2 で `bedrock-agentcore` `strands-agents` 追加 install |
| Node.js 22 + npm | Mobile 起動 | Phase 1 で完了 |
| ネット接続 | Bedrock API 呼び出し | 必須（**完全オフラインは不可**） |

**完全オフラインで動かしたい場合**（要件書 §7 から逸脱）:
- Anthropic API 直接 / OpenAI API に差し替え可能だが、Phase 2 計画書では非推奨
- backlog 化候補（B-308 として追加可能）

