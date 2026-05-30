/**
 * use-share-intake 単体テスト（純粋ロジック層、AsinResult 判別ユニオン分岐）。
 *
 * Validates: PBT-07 Domain Generator: 任意 URL での extract_asin 出力検証。
 */

import { describe, expect, it, vi } from 'vitest';

import { handleShareEvent } from './use-share-intake';

describe('handleShareEvent', () => {
  it('正常 Amazon URL で onAsinExtracted 呼出', async () => {
    const toast = { show: vi.fn() };
    const onAsinExtracted = vi.fn();
    await handleShareEvent(
      { url: 'https://www.amazon.co.jp/dp/B0CXXXXXXX', receivedAt: '2026-05-29T10:00:00Z' },
      { toast, onAsinExtracted },
    );
    expect(onAsinExtracted).toHaveBeenCalledWith({
      url: 'https://www.amazon.co.jp/dp/B0CXXXXXXX',
      asin: 'B0CXXXXXXX',
    });
    expect(toast.show).not.toHaveBeenCalled();
  });

  it('Amazon URL でない場合は Toast + onAsinExtracted 不呼出', async () => {
    const toast = { show: vi.fn() };
    const onAsinExtracted = vi.fn();
    await handleShareEvent(
      { url: 'https://example.com/product/123', receivedAt: '2026-05-29T10:00:00Z' },
      { toast, onAsinExtracted },
    );
    expect(toast.show).toHaveBeenCalledWith('商品として認識できなかったよ');
    expect(onAsinExtracted).not.toHaveBeenCalled();
  });

  it('ASIN 抽出失敗 URL（短縮 URL etc）で Toast', async () => {
    const toast = { show: vi.fn() };
    const onAsinExtracted = vi.fn();
    await handleShareEvent(
      { url: 'https://amzn.to/abcd', receivedAt: '2026-05-29T10:00:00Z' },
      { toast, onAsinExtracted },
    );
    expect(toast.show).toHaveBeenCalled();
    expect(onAsinExtracted).not.toHaveBeenCalled();
  });
});
