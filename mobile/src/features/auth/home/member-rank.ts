/**
 * 会員ランク導出（R5）— 委ね Lv から会員ランクを導出する全域純関数。
 */

export type MemberRank = 'BLANC' | 'ARGENT' | 'NOIR' | 'ONYX' | 'ÉBÈNE';

/** 最下位→最上位の順序配列（単調性・全射の根拠）。 */
export const MEMBER_RANK_ORDER: readonly MemberRank[] = [
  'BLANC',
  'ARGENT',
  'NOIR',
  'ONYX',
  'ÉBÈNE',
];

/** ランクのしきい値（降順 = 最上位優先走査用）。 */
export const MEMBER_RANK_THRESHOLDS: { rank: MemberRank; minLevel: number }[] = [
  { rank: 'ÉBÈNE', minLevel: 50 },
  { rank: 'ONYX', minLevel: 30 },
  { rank: 'NOIR', minLevel: 15 },
  { rank: 'ARGENT', minLevel: 5 },
  { rank: 'BLANC', minLevel: 0 },
];

/** 会員ランクの日本語 / 英語表示名。 */
export const MEMBER_RANK_DISPLAY: Record<MemberRank, { ja: string; en: string }> = {
  BLANC:  { ja: '純白',   en: 'BLANC'  },
  ARGENT: { ja: '白銀',   en: 'ARGENT' },
  NOIR:   { ja: '漆黒',   en: 'NOIR'   },
  ONYX:   { ja: '縞瑪瑙', en: 'ONYX'   },
  ÉBÈNE:  { ja: '黒檀',   en: 'ÉBÈNE'  },
};

/**
 * 委ね Lv → 会員ランクを導出する全域関数（R5.2 決定的・R5.3 全射・R5.4 単調非減少）。
 * @param yudaneLevel - 非負整数（負数や非整数は 0 にクランプ）
 */
export function deriveMemberRank(yudaneLevel: number): MemberRank {
  const level = Math.max(0, Math.floor(yudaneLevel));
  for (const { rank, minLevel } of MEMBER_RANK_THRESHOLDS) {
    if (level >= minLevel) return rank;
  }
  return 'BLANC';
}

/** ランクの段階インデックス（0=BLANC 〜 4=ÉBÈNE）。 */
export function rankStageIndex(rank: MemberRank): number {
  return MEMBER_RANK_ORDER.indexOf(rank);
}

/** 次のランクと、昇格に必要な残り Lv を返す。最上位なら null。 */
export function nextRankInfo(
  yudaneLevel: number,
): { nextRank: MemberRank; remaining: number } | null {
  const current = deriveMemberRank(yudaneLevel);
  const currentIdx = rankStageIndex(current);
  if (currentIdx >= MEMBER_RANK_ORDER.length - 1) return null;
  const nextRank = MEMBER_RANK_ORDER[currentIdx + 1];
  const nextThreshold = MEMBER_RANK_THRESHOLDS.find((t) => t.rank === nextRank)!;
  return { nextRank, remaining: nextThreshold.minLevel - Math.max(0, Math.floor(yudaneLevel)) };
}
