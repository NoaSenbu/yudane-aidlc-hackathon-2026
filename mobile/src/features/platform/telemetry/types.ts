/** M-13 Telemetry の型定義（ALG-TEL クライアント側 / TEL-01〜05）。 */

/** テレメトリ値（PII 混入防止のためプリミティブのみ、TEL-03）。 */
export type TelemetryValue = string | number | boolean;

/** 計測イベント。 */
export interface TelemetryEvent {
  name: string;
  occurredAt: string;
  props?: Record<string, TelemetryValue>;
}

/** バッチ送信の封筒。 */
export interface TelemetryEnvelope {
  events: TelemetryEvent[];
  clientSentAt: string;
  schemaVersion: string;
}

/** 永続化ストレージの抽象（AsyncStorage を注入。テスト容易化）。 */
export interface PersistentStore {
  getItem(key: string): Promise<string | null>;
  setItem(key: string, value: string): Promise<void>;
  removeItem(key: string): Promise<void>;
}

/** 送信トランスポート（ApiClient を注入）。 */
export interface TelemetryTransport {
  send(envelope: TelemetryEnvelope): Promise<void>;
}

/** Telemetry 設定。 */
export interface TelemetryConfig {
  transport: TelemetryTransport;
  store: PersistentStore;
  /** flush 件数閾値（既定 20、TEL-04）。 */
  batchMaxEvents?: number;
  /** 退避キュー上限（既定 500、TEL-05）。 */
  overflowMaxEvents?: number;
  /** スキーマバージョン。 */
  schemaVersion?: string;
  /** 既知イベント名の判定（S-04、TEL-01）。 */
  isKnownEvent?: (name: string) => boolean;
  /** 許可キー判定（S-04、TEL-02）。許可外 props はドロップ。 */
  isAllowedProp?: (key: string) => boolean;
  /** 時刻供給（テスト注入）。 */
  now?: () => Date;
}

export const DEFAULT_BATCH_MAX_EVENTS = 20;
export const DEFAULT_OVERFLOW_MAX_EVENTS = 500;
export const OVERFLOW_STORE_KEY = 'yudane.telemetry.overflow';
