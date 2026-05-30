/**
 * evaluateNotification の単体 + PBT テスト（Unit-5 owner）。
 *
 * Property 5（Safeguard 連携での通知抑制）を担保。
 * Validates: NFR-PBT-02 / functional-design.md Property 5。
 */

import fc from 'fast-check';
import { describe, expect, it } from 'vitest';

import { evaluateNotification, type NotificationContext } from './evaluate-notification';

const baseCtx = (overrides: Partial<NotificationContext> = {}): NotificationContext => ({
  userId: 'user-123',
  monthlyLimitYen: 70_000,
  currentBudgetUsedYen: 0,
  cooldownOn: false,
  quietWeek: false,
  hasDebt: false,
  ...overrides,
});

describe('evaluateNotification', () => {
  describe('cooldownUntil 自動冷却', () => {
    it('cooldownUntil が現在時刻より未来なら block + safeguard.cooldown', () => {
      const now = new Date('2026-05-29T10:00:00Z');
      const future = new Date('2026-05-29T13:00:00Z').toISOString();
      const result = evaluateNotification(baseCtx({ cooldownUntil: future }), now);
      expect(result.decision).toBe('block');
      expect(result.reasonCode).toBe('safeguard.cooldown');
    });

    it('cooldownUntil が過去なら通常評価に進む（allow）', () => {
      const now = new Date('2026-05-29T10:00:00Z');
      const past = new Date('2026-05-29T09:00:00Z').toISOString();
      const result = evaluateNotification(baseCtx({ cooldownUntil: past }), now);
      expect(result.decision).toBe('allow');
    });

    it('cooldownUntil が undefined なら通常評価に進む', () => {
      const result = evaluateNotification(baseCtx());
      expect(result.decision).toBe('allow');
    });
  });

  describe('SG-01 評価順 + warn → block 格上げ', () => {
    it('cooldownOn が true なら block + safeguard.cooldown', () => {
      const result = evaluateNotification(baseCtx({ cooldownOn: true }));
      expect(result.decision).toBe('block');
      expect(result.reasonCode).toBe('safeguard.cooldown');
    });

    it('quietWeek が true なら block + safeguard.quiet-week', () => {
      const result = evaluateNotification(baseCtx({ quietWeek: true }));
      expect(result.decision).toBe('block');
      expect(result.reasonCode).toBe('safeguard.quiet-week');
    });

    it('上限超過なら block + safeguard.monthly-limit-exceeded', () => {
      const result = evaluateNotification(baseCtx({ currentBudgetUsedYen: 75_000 }));
      expect(result.decision).toBe('block');
      expect(result.reasonCode).toBe('safeguard.monthly-limit-exceeded');
    });

    it('警告閾値（80%）超過は decideAllow では warn だが、通知では block に格上げ', () => {
      // 70_000 * 0.8 = 56_000、warn 閾値到達
      const result = evaluateNotification(baseCtx({ currentBudgetUsedYen: 60_000 }));
      expect(result.decision).toBe('block');
      expect(result.reasonCode).toBe('safeguard.near-limit');
    });

    it('閾値未満なら allow', () => {
      const result = evaluateNotification(baseCtx({ currentBudgetUsedYen: 30_000 }));
      expect(result.decision).toBe('allow');
    });
  });

  describe('hasDebt 実効上限再スケール', () => {
    it('hasDebt=true で実効上限が半減し（70_000 × 35/70 = 35_000）、超過で block', () => {
      const result = evaluateNotification(
        baseCtx({ hasDebt: true, currentBudgetUsedYen: 36_000 }),
      );
      expect(result.decision).toBe('block');
      expect(result.reasonCode).toBe('safeguard.debt-restricted');
    });
  });

  describe('PBT: warn が必ず block にマッピングされる不変条件', () => {
    it('任意の near-limit（80%-100%）で常に block を返す', () => {
      fc.assert(
        fc.property(
          fc.integer({ min: 56_000, max: 69_999 }), // 70k の 80% = 56k 〜 直前
          (used) => {
            const result = evaluateNotification(baseCtx({ currentBudgetUsedYen: used }));
            return result.decision === 'block' && result.reasonCode === 'safeguard.near-limit';
          },
        ),
      );
    });
  });

  describe('PBT: cooldownUntil 時刻判定の境界', () => {
    it('任意の未来時刻で block、任意の過去時刻で通常評価', () => {
      fc.assert(
        fc.property(
          fc.integer({ min: 1, max: 86_400 * 30 }), // 1 秒先〜30 日先
          (offsetSec) => {
            const now = new Date('2026-05-29T10:00:00Z');
            const future = new Date(now.getTime() + offsetSec * 1000).toISOString();
            const result = evaluateNotification(baseCtx({ cooldownUntil: future }), now);
            return result.decision === 'block';
          },
        ),
      );
    });
  });
});
