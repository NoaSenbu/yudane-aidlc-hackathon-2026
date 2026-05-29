/**
 * S-04 TelemetryContracts — テレメトリ/ログの契約。
 *
 * Q4=refinedA（default-deny）+ Q3=B（Unit-1 は命名規約 + 雛形のみ、具体名は各 Unit が追記）。
 * 設計: business-rules.md PII-01〜09 / TEL-01〜09 / NFR-OBS。
 */

/** フィールドの出力可否分類（default-deny の基盤）。 */
export type FieldClassification = 'allowed' | 'pii' | 'unclassified';

/** マスク戦略。 */
export type MaskStrategy = 'passthrough' | 'full-mask' | 'partial-email' | 'hash';

/**
 * ログ・テレメトリに**そのまま出力してよい**フィールド名の allowlist。
 * ここに無いキーは default-deny で full-mask される（PII-01/02）。
 * 各 Unit は自分が出力したいフィールドをこの集合に PR で追記する。
 */
export const ALLOWED_FIELDS: ReadonlySet<string> = new Set<string>([
  'correlationId',
  'sessionId',
  'userId', // 注: userId はログ相関に必要だが、メトリクス次元には使わない（TEL-07）
  'screen',
  'eventName',
  'durationMs',
  'statusCode',
  'source',
  'category',
  'decision',
  'reasonCode',
]);

/**
 * 明示的に PII として扱うフィールド名（OpenAPI x-pii と併用、PII-03）。
 * allowlist に入っていてもマスクが優先される。
 */
export const PII_FIELDS: ReadonlySet<string> = new Set<string>([
  'email',
  'password',
  'token',
  'secret',
  'apiKey',
  'address',
  'phone',
  'creditCard',
]);

/**
 * 許可されたメトリクス名カタログ（Q3=B: Unit-1 は雛形のみ、各 Unit が追記）。
 * 命名規約: `<unit>.<domain>.<metric>`（NFR-OBS-02）。
 */
export const METRIC_CATALOG: ReadonlySet<string> = new Set<string>([
  'platform.api.latency',
  'platform.api.error_rate',
  'platform.telemetry.accepted',
  'platform.telemetry.dropped',
  'platform.health.status',
]);

/** メトリクス命名規約の検証（NFR-OBS-02）。 */
const METRIC_NAME_PATTERN = /^[a-z][a-z0-9-]*\.[a-z][a-z0-9-]*\.[a-z][a-z0-9_]*$/;

/**
 * フィールド名を分類する（default-deny）。
 *
 * @param key - フィールド名
 * @returns 分類（pii が allowed より優先、未登録は unclassified）
 */
export function classifyField(key: string): FieldClassification {
  if (PII_FIELDS.has(key)) {
    return 'pii';
  }
  if (ALLOWED_FIELDS.has(key)) {
    return 'allowed';
  }
  return 'unclassified';
}

/** メトリクス名が命名規約に従うかを検証する。 */
export function isValidMetricName(name: string): boolean {
  return METRIC_NAME_PATTERN.test(name);
}

/** イベント名が S-04 カタログに登録済みかを判定する（TEL-01）。 */
export const EVENT_CATALOG: ReadonlySet<string> = new Set<string>([
  'screen_view',
  'app_foreground',
  'app_background',
  'deeplink_open',
]);

export function isKnownEvent(name: string): boolean {
  return EVENT_CATALOG.has(name);
}

/** S-04 スキーマバージョン。 */
export const TELEMETRY_SCHEMA_VERSION = '1.0.0';
