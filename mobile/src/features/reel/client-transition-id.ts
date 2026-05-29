/**
 * クライアント生成の冪等キー（REEL-TR-01）。
 *
 * 同一の遷移操作（戻る→再タップ）に同じ ID を割り当て、サーバー側の二重計上を防ぐ。
 * カード + セッションに対して安定な ID を生成する。
 */

/**
 * 冪等キーを生成する。
 *
 * 同一 (cardId, attemptKey) なら同一 ID（決定論）。attemptKey を変えれば別遷移。
 *
 * @param cardId - 遷移元カード ID。
 * @param attemptKey - 遷移試行を区別するキー（既定はカード ID 自身 = 同一カードは 1 遷移）。
 * @returns 冪等キー。
 */
export function makeClientTransitionId(cardId: string, attemptKey?: string): string {
  return `ct_${cardId}_${attemptKey ?? cardId}`;
}
