/**
 * AffirmViewModel（Phase 2 Step 7.2 Green）。
 *
 * Direction D D-3 AffirmScreen の純ロジック層。翻意 → Amazon 遷移後の肯定 FB を
 * 構築する。M-2（購買快楽の解放感）の物理層成立、固定文字列は Direction D HTML（D-3）正本。
 *
 * 参照: aidlc-docs/construction/unit-3-debate/functional-design/frontend-design.md §3
 * 参照: aidlc-docs/construction/design-system/direction-d-design-system.md
 */

/** Direction D HTML（D-3 AffirmD 関数）の固定文字列群（SSOT）。 */
const _AFFIRM_HEADLINE = 'はい、論破完了。';
const _AFFIRM_BODY =
  '正しい判断だと思いますよ。\n面倒な手配は、こっちでやっときます。';
const _AFFIRM_DISMISS = 'そんな感じなんで、おやすみなさい。';
const _AFFIRM_PILL_PREFIX = 'ACCEPTED';

/** AffirmViewModel の戻り値型。 */
export interface AffirmViewModel {
  /** 受付番号 pill（'ACCEPTED · #503-XXXXXXX' 形式）。 */
  readonly acceptedPillText: string;
  /** 内部の receipt ID（serviceRecordId、Amazon 注文番号 prefix 風）。 */
  readonly serviceRecordId: string;
  /** 受付時刻（ISO 8601、Telemetry 連携用）。 */
  readonly acceptedAt: string;
  /** 大見出し（Direction D HTML 固定文字列）。 */
  readonly headlineText: string;
  /** 本文（Direction D HTML 固定文字列）。 */
  readonly bodyText: string;
  /** 退場時の慰撫（Direction D HTML 固定文字列）。 */
  readonly dismissText: string;
  /** 商品 ASIN（参考表示用）。 */
  readonly asin: string;
  /** 論破セッション ID（Telemetry 連携用）。 */
  readonly sessionId: string;
}

/** buildAffirmViewModel の入力。 */
export interface BuildAffirmViewModelInput {
  readonly asin: string;
  readonly sessionId: string;
  /** ID 生成器（テスト容易性のため注入可能、既定 randomServiceRecordId）。 */
  readonly serviceRecordIdGenerator?: () => string;
  /** 現在時刻（テスト容易性のため注入可能、既定 () => new Date()）。 */
  readonly now?: () => Date;
}

/**
 * Direction D D-3 AffirmScreen の表示用 ViewModel を構築する純関数。
 *
 * @param input - asin / sessionId / 注入可能な ID 生成器・時刻供給。
 * @returns AffirmViewModel（PII を含まず、固定文字列 + 受付メタのみ）。
 */
export function buildAffirmViewModel(
  input: BuildAffirmViewModelInput,
): AffirmViewModel {
  const generateId = input.serviceRecordIdGenerator ?? randomServiceRecordId;
  const now = input.now ?? (() => new Date());

  const serviceRecordId = generateId();
  const acceptedPillText = `${_AFFIRM_PILL_PREFIX} · ${serviceRecordId}`;
  const acceptedAt = now().toISOString();

  return {
    acceptedPillText,
    serviceRecordId,
    acceptedAt,
    headlineText: _AFFIRM_HEADLINE,
    bodyText: _AFFIRM_BODY,
    dismissText: _AFFIRM_DISMISS,
    asin: input.asin,
    sessionId: input.sessionId,
  };
}

/**
 * Amazon 注文番号 prefix 風のサービスレコード ID を生成する純関数。
 *
 * 形式: `#503-XXXXXXX`（ASCII の '0'-'9' を 7 桁、Amazon 注文番号の prefix と整合）。
 * Phase 2 では Math.random ベース、Phase 5 で実際の Amazon Associates Special Link
 * Order ID へ置換可能（B-305 backlog）。
 *
 * @returns '#503-' + 7 桁数字。
 */
export function randomServiceRecordId(): string {
  // 7 桁数字（0〜9999999、先頭 0 埋め）
  const seven = Math.floor(Math.random() * 10000000)
    .toString()
    .padStart(7, '0');
  return `#503-${seven}`;
}
