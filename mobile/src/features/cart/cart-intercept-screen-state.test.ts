/**
 * cart-intercept-screen-state 単体テスト（v3 Issue R7 対応の純粋関数群）。
 */

import { describe, expect, it } from 'vitest';

import {
  ASSOCIATES_DISCLOSURE_TEXT,
  applyOptimisticDismiss,
  computeTimelineProgress,
  getAnimationConfig,
  rollbackOptimisticDismiss,
  shouldShowOrphanedWarning,
} from './cart-intercept-screen-state';
import type { CartWatchItemDto } from './use-cart-watch-item';

const _item = (overrides: Partial<CartWatchItemDto> = {}): CartWatchItemDto => ({
  itemId: '01HG',
  asin: 'B0CXXXXXXX',
  status: 'watching',
  productMeta: { title: 'ワイヤレスイヤホン', priceYen: 12_800 },
  createdAt: '2026-05-29T10:00:00Z',
  updatedAt: '2026-05-29T10:00:00Z',
  ...overrides,
});

describe('shouldShowOrphanedWarning', () => {
  it('watching_orphaned で true', () => {
    expect(shouldShowOrphanedWarning('watching_orphaned')).toBe(true);
  });
  it('他の status で false', () => {
    expect(shouldShowOrphanedWarning('watching')).toBe(false);
    expect(shouldShowOrphanedWarning('notified-30m')).toBe(false);
    expect(shouldShowOrphanedWarning('dismissed')).toBe(false);
  });
});

describe('getAnimationConfig', () => {
  it('reduceMotion=true で blink off + duration 0', () => {
    const config = getAnimationConfig(true);
    expect(config.duration).toBe(0);
    expect(config.blink).toBe(false);
  });
  it('reduceMotion=false で blink on + duration > 0', () => {
    const config = getAnimationConfig(false);
    expect(config.duration).toBeGreaterThan(0);
    expect(config.blink).toBe(true);
  });
});

describe('computeTimelineProgress', () => {
  it('watching ステータスで 30m が currentStep', () => {
    const item = _item({ status: 'watching' });
    const now = new Date('2026-05-29T10:10:00Z'); // 10 分経過
    const progress = computeTimelineProgress(item, now);
    expect(progress[0].step).toBe('30m');
    expect(progress[0].isCurrentStep).toBe(true);
    expect(progress[0].remainingSec).toBe(1_200); // 30m - 10m = 20m = 1200s
  });

  it('notified-30m ステータスで 30m が past + 6h が currentStep', () => {
    const item = _item({ status: 'notified-30m' });
    const now = new Date('2026-05-29T11:00:00Z');
    const progress = computeTimelineProgress(item, now);
    expect(progress[0].isPast).toBe(true);
    expect(progress[1].step).toBe('6h');
    expect(progress[1].isCurrentStep).toBe(true);
  });

  it('watching_orphaned ステータスでは 30m を currentStep として扱う（Issue Z6 修正）', () => {
    const item = _item({ status: 'watching_orphaned' });
    const now = new Date('2026-05-29T10:10:00Z');
    const progress = computeTimelineProgress(item, now);
    expect(progress[0].step).toBe('30m');
    expect(progress[0].isCurrentStep).toBe(true);
  });

  it('purchased ステータスでは全ステップが past', () => {
    const item = _item({ status: 'purchased' });
    const now = new Date('2026-05-29T10:10:00Z');
    const progress = computeTimelineProgress(item, now);
    progress.forEach((p) => expect(p.isPast).toBe(true));
  });
});

describe('applyOptimisticDismiss / rollbackOptimisticDismiss', () => {
  it('指定 asin を一覧から除去', () => {
    const items = [
      _item({ asin: 'B0AAAAAAAA' }),
      _item({ asin: 'B0BBBBBBBB' }),
      _item({ asin: 'B0CCCCCCCC' }),
    ];
    const result = applyOptimisticDismiss(items, 'B0BBBBBBBB');
    expect(result).toHaveLength(2);
    expect(result.map((i) => i.asin)).toEqual(['B0AAAAAAAA', 'B0CCCCCCCC']);
  });

  it('rollback で元の一覧を返す', () => {
    const items = [_item({ asin: 'B0AAAAAAAA' })];
    expect(rollbackOptimisticDismiss(items)).toBe(items);
  });
});

describe('ASSOCIATES_DISCLOSURE_TEXT', () => {
  it('FR-PROFILE-04 / NG-8 整合の文言を含む', () => {
    expect(ASSOCIATES_DISCLOSURE_TEXT).toContain('Amazon Associates');
    expect(ASSOCIATES_DISCLOSURE_TEXT).toContain('紹介料');
  });
});
