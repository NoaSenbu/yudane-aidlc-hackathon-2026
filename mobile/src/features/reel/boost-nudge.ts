/**
 * 深夜ブースト枠の注意誘導アニメ判定（US-02-01 AC-2）。
 *
 * ブーストカード表示中、最初の 3 秒間スクロール/ジェスチャーが無い場合に
 * 誘導アニメを発火する。純粋関数で判定し、UI 側は reanimated で実行する。
 */

/** 誘導アニメ発火までの無操作時間（ms、US-02-01 AC-2）。 */
export const BOOST_NUDGE_IDLE_MS = 3_000;

/** 誘導判定の入力。 */
export interface BoostNudgeInput {
  /** 現在表示中カードがブースト枠か。 */
  isHighPriceBoost: boolean;
  /** カード表示開始からの経過時間（ms）。 */
  idleMs: number;
  /** 表示中にスクロール/ジェスチャーが発生したか。 */
  interacted: boolean;
}

/**
 * 誘導アニメを発火すべきか判定する（純粋関数）。
 *
 * ブースト枠 かつ 3 秒以上無操作 かつ 未インタラクション のときのみ true。
 *
 * @param input - 判定入力。
 * @returns 発火すべきなら true。
 */
export function shouldNudge(input: BoostNudgeInput): boolean {
  return input.isHighPriceBoost && !input.interacted && input.idleMs >= BOOST_NUDGE_IDLE_MS;
}
