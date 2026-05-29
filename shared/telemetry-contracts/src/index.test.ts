import { describe, expect, it } from 'vitest';

import { classifyField, isKnownEvent, isValidMetricName } from './index';

describe('classifyField（default-deny）', () => {
  it('allowlist のキーは allowed', () => {
    expect(classifyField('correlationId')).toBe('allowed');
  });

  it('PII キーは pii（allowlist より優先）', () => {
    expect(classifyField('email')).toBe('pii');
  });

  it('未登録キーは unclassified（fail-safe）', () => {
    expect(classifyField('deviceFingerprint')).toBe('unclassified');
    expect(classifyField('lineUserId')).toBe('unclassified');
  });
});

describe('isValidMetricName', () => {
  it('命名規約 <unit>.<domain>.<metric> を満たす', () => {
    expect(isValidMetricName('platform.api.latency')).toBe(true);
  });

  it('規約外は false', () => {
    expect(isValidMetricName('latency')).toBe(false);
    expect(isValidMetricName('Platform.Api.Latency')).toBe(false);
  });
});

describe('isKnownEvent', () => {
  it('カタログ登録済みは true', () => {
    expect(isKnownEvent('screen_view')).toBe(true);
  });

  it('未登録は false', () => {
    expect(isKnownEvent('unknown_event')).toBe(false);
  });
});
