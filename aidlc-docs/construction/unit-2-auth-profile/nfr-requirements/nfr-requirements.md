# Unit-2 Auth & Profile — NFR Requirements

> Unit-2 の非機能要件。Unit-1 の横断 NFR 基盤を継承し、Unit-2 固有分を定義する。
> 参照: [Unit-2 Functional Design](../functional-design/) / [Unit-1 NFR Requirements](../../unit-1-platform/nfr-requirements/) / [要件書 §6](../../../inception/requirements/requirements.md)
> 確定方針: Q1=C / Q2=C / Q3=部分（MFA ロジック MVP / Alarm 作り込み決勝）/ Q4=A / Q5=B / US-AUTH-03=MVP 残置

---

## 0. Unit-1 から継承する横断 NFR

| 観点 | 継承内容 |
|---|---|
| ApiClient タイムアウト | REST 接続 3s / 全体 10s |
| カバレッジ | Mobile/Backend 基盤 85%、純ロジック 95% |
| SECURITY 基盤 | 01/02/03/05/06/08/09/15（Unit-1 実装を継承） |
| PBT | shrinking/seed/example 併存 |
| 観測 | EMF 土台 + 命名規約（メトリクス名は Unit-2 が追記） |
| 可用性 | フォールバックは各 Unit、ヘルスチェックは Unit-1 |
| マイルストーン | 段階達成（MVP 5/30 / 決勝 6/26） |

---

## 1. 性能要件（NFR2-PERF、Q1=C）

| ID | 要件 | マイルストーン |
|---|---|---|
| NFR2-PERF-01 | 認証・オンボの性能目標値（保存 API / サインイン / MFA 検証等）は**決勝で計測して設定** | 決勝 |
| NFR2-PERF-02 | MVP では Unit-1 汎用タイムアウト（REST 全体 10s）を適用、機能動作を優先 | MVP |
| NFR2-PERF-03 | オンボ 90 秒は UX 目標として保持（FD ONB-01、計測は決勝） | UX 目標 |

> Q1=C: Unit-2 固有の定量性能目標は決勝前に実測ベースで設定。MVP は機能完成を優先。

---

## 2. 計測・メトリクス（NFR2-OBS、Q2=C / Q5=B）

| ID | 要件 | マイルストーン |
|---|---|---|
| NFR2-OBS-01 | MVP の Unit-2 メトリクスは **`auth.signin.success_rate` のみ**（Q5=B、最小化） | MVP |
| NFR2-OBS-02 | オンボ完了率 / 画面別離脱 / 平均完了時間の計測は**決勝で追加**（Q2=C） | 決勝 |
| NFR2-OBS-03 | メトリクスは Unit-1 EMF 土台 + 命名規約 `<unit>.<domain>.<metric>` に準拠 | MVP |

> Q2=C / Q5=B 整合: MVP はサインイン成功率のみ。ダメ化ファネル計測（完了率等）は決勝。

---

## 3. セキュリティ・認証（NFR2-SEC、Q3 / SECURITY-12/14）

| ID | 要件 | マイルストーン | 根拠 |
|---|---|---|---|
| NFR2-SEC-01 | TOTP MFA 必須（platform-stack User Pool で REQUIRED） | MVP | SECURITY-12 / US-AUTH-02 AC-1/2 |
| NFR2-SEC-02 | 認証失敗 5 回で 15 分ロックアウト（**ロジックは MVP**） | MVP | US-AUTH-02 AC-4 |
| NFR2-SEC-03 | MFA リセットは 72h 冷却（**ロジックは MVP**） | MVP | US-AUTH-02 AC-3 |
| NFR2-SEC-04 | 認証失敗の CloudWatch Alarm **作り込み**・異常検知・監査ログ 90 日保持 | 決勝 | SECURITY-14 |
| NFR2-SEC-05 | 全 `/v1/users/{userId}*` に Unit-1 require_owner（IDOR、SECURITY-08） | MVP | FD SEC-01 |

> Q3 部分採用: MFA 必須・ロックアウト・リセット冷却の**機能ロジックは MVP**（FD の AC を満たす）。CloudWatch Alarm の作り込み・異常検知・監査ログ 90 日保持のみ決勝。

---

## 4. 負債セーフガード（NFR2-SAFE、US-AUTH-03 = MVP 残置）

| ID | 要件 | マイルストーン | 根拠 |
|---|---|---|---|
| NFR2-SAFE-01 | 負債フラグ保存 + Unit-1 `SafeguardPolicy.decideAllow`（DEBT 比率 0.35）連携 | **MVP** | US-AUTH-03 AC-1/2 / NG-4 |
| NFR2-SAFE-02 | 負債フラグ ON 中の遷移 24h 非活性 + Safeguard 画面誘導 | **MVP** | US-AUTH-03 AC-3 |
| NFR2-SAFE-03 | 負債解除は 72h クーリングオフ + 解除理由ログ | **MVP** | US-AUTH-03 AC-4 |

> **倫理判断（Clarification 3=A）**: US-AUTH-03 は NG-4（金融実害）への配慮の実装本体。Unit-1 SafeguardPolicy 再利用で追加コストほぼゼロのため MVP に残置。これを外すと予選デモが倫理アンチパターン（借金保有者に無制限散財）に抵触する。

---

## 5. PII 保護（NFR2-PII、Q4=A）

| ID | 要件 |
|---|---|
| NFR2-PII-01 | Unit-1 sanitizer（default-deny）を継承。email は既存 PII としてマスク |
| NFR2-PII-02 | 予算額 / 負債フラグ / ブランド嗜好は allowlist に**追加しない** = 自動マスク（ログ出力しない） |
| NFR2-PII-03 | DynamoDB（Users/SafeguardStates 等）は Unit-1 共通 KMS 暗号化 |

---

## 6. カバレッジ（NFR2-COV、Unit-1 継承）

| 対象 | Line | Branch |
|---|---|---|
| B-01 AuthEdgeLambda（初期化・claim） | 85%+ | — |
| B-08 PreferenceVectorUpdater | 85%+ | — |
| M-11 AuthModule | 85%+ | — |
| M-02 HomeScreen | 80%+ | 70%+ |
| オンボ段階保存・Lv 判定（純ロジック） | 95%+ | 90%+ |

---

## 7. マイルストーン別サマリ

### MVP（5/30）で必須
- MFA 必須 + 15 分ロックアウト + 72h リセット冷却（ロジック）
- **US-AUTH-03 負債セーフガード（上限半減・冷却・72h クーリングオフ）**
- require_owner 認可 / PII fail-safe マスク
- `auth.signin.success_rate` メトリクス
- オンボ段階保存（90 秒 UX 目標 + 途中再開）

### 決勝（6/26）で追加
- Unit-2 性能目標の実測設定
- オンボ完了率 / 離脱率 / 平均時間の計測
- 認証失敗 CloudWatch Alarm 作り込み + 異常検知 + 監査ログ 90 日

---

## 8. Extension コンプライアンスサマリ

| Extension | 状態 | 備考 |
|---|---|---|
| SECURITY-08 | ✅ MVP | require_owner |
| SECURITY-12 | ✅ MVP | MFA 必須 + ロックアウト + リセット冷却 |
| SECURITY-14 | ⏭ 決勝 | Alarm 作り込み（基本ログは MVP） |
| NG-4（金融実害） | ✅ MVP | US-AUTH-03 残置 |
| NG-8（Associates 開示） | ✅ MVP | オンボ完了時の開示確認 |
| PBT-04 | ✅ MVP | オンボ段階保存・初期化の冪等性 |
