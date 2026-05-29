# Unit-1 Platform — Code Summary: M-13 Telemetry（Step 14-15）

## 生成ファイル

| ファイル | 役割 |
|---|---|
| `mobile/src/features/platform/telemetry/types.ts` | TelemetryEvent/Envelope / PersistentStore / Transport 抽象 |
| `mobile/src/features/platform/telemetry/telemetry.ts` | track/flush + バッファ + 退避キュー（At-least-once） |
| `mobile/src/features/platform/telemetry/serialization.ts` | serialize/deserialize（PBT-02 対象） |
| `mobile/src/features/platform/telemetry/index.ts` | export 制御 |
| `mobile/src/features/platform/telemetry/telemetry.test.ts` | バッファ/退避/round-trip PBT |

## ルール準拠
- TEL-01〜05（未知イベント no-op / 許可外 props ドロップ / flush トリガー / 退避上限破棄）
- PAT-RESIL-03（At-least-once）/ PAT-PERF-02（track は enqueue のみ）/ Q6=B（フォールバック土台なし、退避のみ）
- NFR-PBT-03（Envelope round-trip PBT-02）/ NFR-COV-05（85%）
- 依存注入（PersistentStore / Transport / now）でテスト容易化、AsyncStorage/ApiClient は結線時に注入

## 次ステップ
Step 16-17: M-01 AppShell + 状態管理土台
