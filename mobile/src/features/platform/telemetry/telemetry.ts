/**
 * M-13 Telemetry — クライアント計測のバッファリングと送信（ALG-TEL / PAT-PERF-02 / RESIL-03）。
 *
 * track はメモリ enqueue のみ（< 1ms、NFR-PERF-04）。flush は件数/時間/background で発火。
 * 失敗時は退避キュー（PersistentStore）に保存し次回再送（At-least-once、Q3=A/Q6=B）。
 */

import {
  DEFAULT_BATCH_MAX_EVENTS,
  DEFAULT_OVERFLOW_MAX_EVENTS,
  OVERFLOW_STORE_KEY,
  type TelemetryConfig,
  type TelemetryEnvelope,
  type TelemetryEvent,
  type TelemetryValue,
} from './types';

export class Telemetry {
  private readonly config: TelemetryConfig;
  private readonly batchMax: number;
  private readonly overflowMax: number;
  private readonly schemaVersion: string;
  private readonly now: () => Date;
  private queue: TelemetryEvent[] = [];

  constructor(config: TelemetryConfig) {
    this.config = config;
    this.batchMax = config.batchMaxEvents ?? DEFAULT_BATCH_MAX_EVENTS;
    this.overflowMax = config.overflowMaxEvents ?? DEFAULT_OVERFLOW_MAX_EVENTS;
    this.schemaVersion = config.schemaVersion ?? '1.0.0';
    this.now = config.now ?? (() => new Date());
  }

  /**
   * イベントを計測する。未知イベント名は no-op、許可外 props はドロップ（TEL-01/02）。
   *
   * @param name - イベント名（S-04 カタログ登録済み）
   * @param props - 付帯情報（許可キーのみ送信）
   */
  track(name: string, props?: Record<string, TelemetryValue>): void {
    if (this.config.isKnownEvent && !this.config.isKnownEvent(name)) {
      return; // 不正イベントは作らない
    }
    const safeProps = this.filterProps(props);
    this.queue.push({
      name,
      occurredAt: this.now().toISOString(),
      ...(safeProps ? { props: safeProps } : {}),
    });
    if (this.queue.length >= this.batchMax) {
      void this.flush();
    }
  }

  /**
   * キュー + 退避分をまとめて送信する。失敗時は退避キューへ保存（TEL-04/05）。
   */
  async flush(): Promise<void> {
    const pending = await this.loadOverflow();
    const events = [...pending, ...this.queue];
    if (events.length === 0) {
      return;
    }
    this.queue = [];

    const envelope: TelemetryEnvelope = {
      events,
      clientSentAt: this.now().toISOString(),
      schemaVersion: this.schemaVersion,
    };

    try {
      await this.config.transport.send(envelope);
      await this.config.store.removeItem(OVERFLOW_STORE_KEY);
    } catch {
      await this.saveOverflow(events);
    }
  }

  /** 許可キーのみ残す（TEL-02、PII 混入防止）。 */
  private filterProps(
    props?: Record<string, TelemetryValue>,
  ): Record<string, TelemetryValue> | undefined {
    if (!props) {
      return undefined;
    }
    const allow = this.config.isAllowedProp;
    if (!allow) {
      return props;
    }
    const filtered: Record<string, TelemetryValue> = {};
    for (const [key, value] of Object.entries(props)) {
      if (allow(key)) {
        filtered[key] = value;
      }
    }
    return Object.keys(filtered).length > 0 ? filtered : undefined;
  }

  /** 退避キューを読み込む。 */
  private async loadOverflow(): Promise<TelemetryEvent[]> {
    const raw = await this.config.store.getItem(OVERFLOW_STORE_KEY);
    if (!raw) {
      return [];
    }
    try {
      const parsed = JSON.parse(raw) as TelemetryEvent[];
      return Array.isArray(parsed) ? parsed : [];
    } catch {
      return [];
    }
  }

  /** 退避キューへ保存（上限超過は古い順に破棄、TEL-05）。 */
  private async saveOverflow(events: TelemetryEvent[]): Promise<void> {
    const trimmed = events.slice(-this.overflowMax);
    await this.config.store.setItem(OVERFLOW_STORE_KEY, JSON.stringify(trimmed));
  }
}
