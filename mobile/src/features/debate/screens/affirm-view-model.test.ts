/**
 * AffirmViewModel のテスト（Phase 2 Step 7.1 Red）。
 *
 * Direction D D-3 AffirmScreen の純ロジック層を検証。固定文字列の整合性 + 受付メタの
 * 形式（serviceRecordId / acceptedAt ISO）を確認。M-2 解放感の物理層が成立することを保証。
 *
 * 参照: aidlc-docs/construction/unit-3-debate/functional-design/frontend-design.md §3 D-3
 */

import { describe, expect, it } from 'vitest';

import {
  buildAffirmViewModel,
  randomServiceRecordId,
} from './affirm-view-model';

describe('buildAffirmViewModel', () => {
  it('headlineText が「はい、論破完了。」固定文字列', () => {
    const vm = buildAffirmViewModel({
      asin: 'B01ABC1234',
      sessionId: 'sess-1',
    });
    expect(vm.headlineText).toBe('はい、論破完了。');
  });

  it('bodyText が Direction D D-3 の固定文字列', () => {
    const vm = buildAffirmViewModel({
      asin: 'B01ABC1234',
      sessionId: 'sess-1',
    });
    expect(vm.bodyText).toBe(
      '正しい判断だと思いますよ。\n面倒な手配は、こっちでやっときます。',
    );
  });

  it('dismissText が「そんな感じなんで、おやすみなさい。」', () => {
    const vm = buildAffirmViewModel({
      asin: 'B01ABC1234',
      sessionId: 'sess-1',
    });
    expect(vm.dismissText).toBe('そんな感じなんで、おやすみなさい。');
  });

  it('acceptedPillText が "ACCEPTED · #503-XXXXXXX" 形式', () => {
    const vm = buildAffirmViewModel({
      asin: 'B01ABC1234',
      sessionId: 'sess-1',
      serviceRecordIdGenerator: () => '#503-2890471',
    });
    expect(vm.acceptedPillText).toBe('ACCEPTED · #503-2890471');
    expect(vm.serviceRecordId).toBe('#503-2890471');
  });

  it('serviceRecordId は #503-XXXXXXX（7 桁数字）形式', () => {
    const vm = buildAffirmViewModel({
      asin: 'B01ABC1234',
      sessionId: 'sess-1',
    });
    expect(vm.serviceRecordId).toMatch(/^#503-\d{7}$/);
  });

  it('acceptedAt が ISO 8601 形式', () => {
    const fixedNow = new Date('2026-06-01T12:00:00.000Z');
    const vm = buildAffirmViewModel({
      asin: 'B01ABC1234',
      sessionId: 'sess-1',
      now: () => fixedNow,
    });
    expect(vm.acceptedAt).toBe('2026-06-01T12:00:00.000Z');
  });

  it('asin / sessionId が ViewModel に保持される', () => {
    const vm = buildAffirmViewModel({
      asin: 'B01ABC1234',
      sessionId: 'sess-abcde',
    });
    expect(vm.asin).toBe('B01ABC1234');
    expect(vm.sessionId).toBe('sess-abcde');
  });

  it('PII を ViewModel に含まない（actor_id / email 等を入れる手段がない）', () => {
    const vm = buildAffirmViewModel({
      asin: 'B01ABC1234',
      sessionId: 'sess-1',
    });
    // ViewModel に actor_id 等のフィールドが存在しないことを確認
    expect(Object.keys(vm)).toEqual([
      'acceptedPillText',
      'serviceRecordId',
      'acceptedAt',
      'headlineText',
      'bodyText',
      'dismissText',
      'asin',
      'sessionId',
    ]);
  });

  it('serviceRecordIdGenerator を注入してテスト容易性を確保', () => {
    const fixedId = '#503-9999999';
    const vm = buildAffirmViewModel({
      asin: 'B01ABC1234',
      sessionId: 'sess-1',
      serviceRecordIdGenerator: () => fixedId,
    });
    expect(vm.serviceRecordId).toBe(fixedId);
  });
});

describe('randomServiceRecordId', () => {
  it('#503- + 7 桁数字の形式', () => {
    for (let i = 0; i < 50; i++) {
      const id = randomServiceRecordId();
      expect(id).toMatch(/^#503-\d{7}$/);
    }
  });

  it('複数回呼ぶと異なる ID が返る（高確率）', () => {
    const ids = new Set<string>();
    for (let i = 0; i < 20; i++) {
      ids.add(randomServiceRecordId());
    }
    // 20 回中ユニーク数 >= 15（10^7 空間で衝突は極稀）
    expect(ids.size).toBeGreaterThanOrEqual(15);
  });
});
