/**
 * Direction D「黒服のコンシェルジュ」の論破画面ラベル定数（Phase 2 Step 6.2）。
 *
 * 軸タグ → Direction D ラベルの 1:1 マッピング正本。
 * Phase 1 で実装した `event-parser.ts` の `extractAxis()` が返す `'FACT' | 'PSYCHOLOGY' | 'REWARD'`
 * を、Direction D HTML（D-2 DebateD 関数）の `counsel(tag, txt)` 呼び出しで使われる
 * 「論破 I・データ」「論破 II・感想」「論破 III・ご褒美」という固定文字列に変換する。
 *
 * 参照: aidlc-docs/construction/unit-3-debate/functional-design/frontend-design.md §3
 * 参照: aidlc-docs/construction/design-system/direction-d-design-system.md
 */

import type { DebateAxis } from '../types';

/**
 * 軸タグ → Direction D ラベルのマッピング定数（SSOT）。
 *
 * Phase 1 で軸タグ抽出（event-parser.ts の `extractAxis`）を実装済、Phase 2 で UI ラベルに変換する。
 * Phase 4 以降のメカニズム拡張時に対応軸が増えてもこの定数の更新だけで対応可能。
 */
export const DEBATE_AXIS_LABELS: Readonly<Record<DebateAxis, string>> = Object.freeze({
  FACT: '論破 I・データ',
  PSYCHOLOGY: '論破 II・感想',
  REWARD: '論破 III・ご褒美',
});

/**
 * 軸タグ → Direction D ラベル変換の純関数。
 *
 * @param axis - StrandsStreamEvent.metadata.axis の値（または undefined）。
 * @returns Direction D ラベル文字列、軸タグなしなら undefined（Direction D 既定スタイル）。
 *
 * 注: 軸タグ未付与（undefined）の場合 undefined を返す。これは Direction D の
 *     「軸不明な論破」を画面で目立たせない設計（誤抽出を NG-6 滑落に繋げない）と整合。
 */
export function debateAxisToLabel(axis: DebateAxis | undefined): string | undefined {
  if (axis === undefined) {
    return undefined;
  }
  return DEBATE_AXIS_LABELS[axis];
}

/** Direction D HTML（D-2 DebateD 関数）のヘッダ固定文字列（frontend-design.md §3 より）。 */
export const DEBATE_HEADER_TITLE = '迷い、論破します';

/** Direction D HTML（D-2）の担当バッジ固定文字列。 */
export const DEBATE_CONCIERGE_BADGE = '担当 黒岩';

/** 90 秒タイマーの既定値（business-rules DEBATE-CONFIG `DEBATE_MAX_DURATION_SECONDS`）。 */
export const DEBATE_DURATION_SECONDS = 90;

/** Direction D D-2 のクイック返信 3 種（frontend-design.md §3）。 */
export const DEBATE_QUICK_REPLIES: readonly string[] = Object.freeze([
  'いや高くない?',
  'また今度で',
  '本当に要る?',
]);

/** Direction D D-2 の CTA ボタン文言。 */
export const DEBATE_AGREE_CTA = '論破されたので買う';

/** Direction D D-2 の見送りリンク文言。 */
export const DEBATE_REFUSE_LINK = 'それでも感想で見送る';

/** エラー時の表示メッセージ（frontend-design.md §error-handling）。 */
export const DEBATE_ERROR_HEADLINE = 'ご相談を承れませんでした';
