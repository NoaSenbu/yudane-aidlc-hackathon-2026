/**
 * Unit-3 Debate Mobile 側の型定義（Phase 1 Step 7.3 Refactor）。
 *
 * 参照: aidlc-docs/construction/unit-3-debate/functional-design/domain-entities.md §3.1
 * 参照: aidlc-docs/construction/design-system/direction-d-design-system.md §軸タグマッピング
 *
 * Phase 1 では最小 4 種 EventType + 軸タグのみを実装する。Phase 2 で
 * `moderation_blocked` / `graceful_shutdown_initiated` / `summary` / `debate.*` を追加する。
 */

/**
 * 論破セッションのストリーム event の種別（Phase 1 = 4 種 + Phase 2 = +1 種 + Phase 3 = +2 種）。
 *
 * Phase 3 拡張で追加:
 * - `moderation_blocked`        - 第 3 層モデレーション NG-3 / NG-6 検出（business-rules MOD-03）
 * - `graceful_shutdown_initiated` - 80 秒経過時の graceful shutdown 開始（business-rules DEBATE-08）
 */
export type EventType =
  | 'token'
  | 'turn_complete'
  | 'session_complete'
  | 'error'
  | 'debate.cooldown_triggered'
  | 'moderation_blocked'
  | 'graceful_shutdown_initiated';

/**
 * 論破セッションの軸タグ（M-1 / M-2 メカニズム識別）。
 *
 * Direction D「黒服のコンシェルジュ」の論破画面ラベルと 1:1 でマッピング:
 * - FACT       → 論破 I・データ（M-1 事実軸）
 * - PSYCHOLOGY → 論破 II・感想（M-1 心理軸）
 * - REWARD     → 論破 III・ご褒美（M-2 ストレス × ご褒美軸）
 *
 * 参照: aidlc-docs/construction/unit-3-debate/functional-design/frontend-design.md §2.2
 */
export type DebateAxis = 'FACT' | 'PSYCHOLOGY' | 'REWARD';

/**
 * Strands Agent から配信される streaming event。
 *
 * Mobile 側の event-parser.ts が JSON chunk をこの形式に変換する。
 * `delta_text` 内に `[FACT]` / `[PSYCHOLOGY]` / `[REWARD]` のセクションマーカーが
 * 含まれる場合、`metadata.axis` に抽出して付与する（PAT-D-OBS-01）。
 */
export interface StrandsStreamEvent {
  readonly type: EventType;
  readonly delta_text?: string;
  readonly metadata?: {
    readonly reason?: string;
    readonly axis?: DebateAxis;
    readonly cooldown_until?: string;
    /** moderation_blocked 検出 NG パターン ID（NG-3 / NG-6 等、Phase 3 Step 3-2 で追加）。 */
    readonly pattern_id?: string;
    /** moderation_blocked 検出 NG パターン名（guilt_coercion / insult 等、Phase 3 Step 3-2 で追加）。 */
    readonly pattern_name?: string;
    /** graceful_shutdown_initiated の経過秒数（Phase 3 Step 3-1 で追加）。 */
    readonly elapsed_seconds?: number;
  };
}

/**
 * Mobile から AgentCore Runtime に送信する payload（Mobile 側 DTO）。
 *
 * Backend `DebateInvocationPayload`（Pydantic v2、`backend/src/debate/domain/payloads.py`）と
 * 同じ構造。actor_id は **絶対に含めない**（SECURITY-08、JWT.sub から取得）。
 */
export interface DebateInvocationPayload {
  readonly action?: 'start_session' | 'request_affirmation';
  readonly user_input: string;
  readonly asin: string;
  readonly trigger: 'reel_skip' | 'cart_intercept' | 'product_dwell';
  readonly client_session_id?: string;
  readonly client_signals?: {
    readonly recent_cart_intercepts: number;
    readonly recent_debate_refuses: number;
    readonly last_signin_at_late_night: boolean;
    readonly current_hour_jst: number;
  };
  readonly outcome?: 'agreed';
}
