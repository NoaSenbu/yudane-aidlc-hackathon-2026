/**
 * フロント側 DomainError 型と ProblemDetails → DomainError 変換（ALG-MAP / ERR-01〜08）。
 */

import type { ProblemDetails } from '@yudane/schema';

/** エラーカテゴリ（第1階層、ERR-02）。 */
export type ErrorCategory =
  | 'validation'
  | 'auth'
  | 'not-found'
  | 'conflict'
  | 'safeguard'
  | 'external-api'
  | 'rate-limit'
  | 'internal';

/** フロント側ドメインエラー。 */
export class DomainError extends Error {
  readonly category: ErrorCategory;
  readonly code: string;
  readonly status: number;
  readonly retryable: boolean;
  readonly userMessage: string | undefined;

  constructor(params: {
    category: ErrorCategory;
    code: string;
    message: string;
    status: number;
    retryable?: boolean;
    userMessage?: string;
  }) {
    super(params.message);
    this.name = 'DomainError';
    this.category = params.category;
    this.code = params.code;
    this.status = params.status;
    this.retryable = params.retryable ?? false;
    this.userMessage = params.userMessage;
  }
}

const ERROR_TYPE_BASE = 'https://api.yudane.app/errors/';
const RETRYABLE_STATUS = new Set([429, 503]);

/** HTTP ステータスからカテゴリの既定を導く。 */
function categoryFromStatus(status: number): ErrorCategory {
  if (status === 400 || status === 422) return 'validation';
  if (status === 401) return 'auth';
  if (status === 403) return 'auth';
  if (status === 404) return 'not-found';
  if (status === 409) return 'conflict';
  if (status === 429) return 'rate-limit';
  if (status >= 500) return 'internal';
  return 'internal';
}

/**
 * ProblemDetails を DomainError に変換する（ALG-MAP）。
 *
 * @param problem - サーバーが返した ProblemDetails（パース済み）。null 可
 * @param status - HTTP ステータス
 * @param isIdempotent - 冪等メソッド（GET）か。retryable 判定に使用
 * @returns DomainError
 */
export function mapProblemToDomainError(
  problem: ProblemDetails | null,
  status: number,
  isIdempotent: boolean,
): DomainError {
  const code = problem?.type?.startsWith(ERROR_TYPE_BASE)
    ? problem.type.slice(ERROR_TYPE_BASE.length)
    : `${categoryFromStatus(status)}.unknown`;
  const category = (code.split('.')[0] ?? categoryFromStatus(status)) as ErrorCategory;
  const retryable = RETRYABLE_STATUS.has(status) && isIdempotent;

  return new DomainError({
    category,
    code,
    message: problem?.detail ?? `HTTP ${status}`,
    status,
    retryable,
    userMessage: problem?.title,
  });
}
