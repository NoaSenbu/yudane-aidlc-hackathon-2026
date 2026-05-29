import { describe, expect, it, vi } from 'vitest';

import { ApiClient } from './api-client';
import { DomainError } from './domain-error';
import type { AuthTokenProvider } from './types';

/** テスト用の AuthTokenProvider モック。 */
function makeAuth(overrides: Partial<AuthTokenProvider> = {}): AuthTokenProvider {
  return {
    getAccessToken: vi.fn().mockResolvedValue('token-1'),
    refresh: vi.fn().mockResolvedValue(false),
    onAuthExpired: vi.fn(),
    ...overrides,
  };
}

/** Response を生成するヘルパ。 */
function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

const baseUrl = 'https://api.test';

describe('ApiClient.request', () => {
  it('2xx の JSON を返し、相関 ID と認証ヘッダを付与する', async () => {
    const fetchImpl = vi.fn().mockResolvedValue(jsonResponse(200, { ok: true }));
    const client = new ApiClient({ baseUrl, auth: makeAuth(), fetchImpl });

    const result = await client.request<{ ok: boolean }>('/v1/health');

    expect(result).toEqual({ ok: true });
    const [, init] = fetchImpl.mock.calls[0];
    const headers = init.headers as Headers;
    expect(headers.get('X-Correlation-Id')).toBeTruthy();
    expect(headers.get('Authorization')).toBe('Bearer token-1');
  });

  it('401 で refresh 成功なら同一相関 ID で再送する', async () => {
    const fetchImpl = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse(401, { type: 'x', title: 'a', status: 401 }))
      .mockResolvedValueOnce(jsonResponse(200, { ok: true }));
    const auth = makeAuth({ refresh: vi.fn().mockResolvedValue(true) });
    const client = new ApiClient({ baseUrl, auth, fetchImpl });

    const result = await client.request<{ ok: boolean }>('/v1/health');

    expect(result).toEqual({ ok: true });
    expect(auth.refresh).toHaveBeenCalledTimes(1);
    const cid1 = (fetchImpl.mock.calls[0][1].headers as Headers).get('X-Correlation-Id');
    const cid2 = (fetchImpl.mock.calls[1][1].headers as Headers).get('X-Correlation-Id');
    expect(cid1).toBe(cid2);
  });

  it('401 で refresh 失敗なら onAuthExpired を呼び DomainError を投げる', async () => {
    const fetchImpl = vi
      .fn()
      .mockResolvedValue(jsonResponse(401, { type: 'x', title: 'a', status: 401 }));
    const auth = makeAuth({ refresh: vi.fn().mockResolvedValue(false) });
    const client = new ApiClient({ baseUrl, auth, fetchImpl });

    await expect(client.request('/v1/health')).rejects.toBeInstanceOf(DomainError);
    expect(auth.onAuthExpired).toHaveBeenCalledTimes(1);
  });

  it('ProblemDetails を DomainError にマッピングする', async () => {
    const problem = {
      type: 'https://api.yudane.app/errors/safeguard.cooldown',
      title: '論破クールダウン中です',
      status: 409,
    };
    const fetchImpl = vi.fn().mockResolvedValue(jsonResponse(409, problem));
    const client = new ApiClient({ baseUrl, auth: makeAuth(), fetchImpl });

    await expect(client.request('/v1/debate-sessions', { method: 'POST' })).rejects.toMatchObject({
      code: 'safeguard.cooldown',
      category: 'safeguard',
      status: 409,
    });
  });

  it('POST は 503 でもリトライしない（非冪等）', async () => {
    const fetchImpl = vi
      .fn()
      .mockResolvedValue(jsonResponse(503, { type: 'x', title: 'a', status: 503 }));
    const client = new ApiClient({ baseUrl, auth: makeAuth(), fetchImpl });

    await expect(client.request('/v1/telemetry', { method: 'POST' })).rejects.toBeInstanceOf(
      DomainError,
    );
    expect(fetchImpl).toHaveBeenCalledTimes(1);
  });
});
