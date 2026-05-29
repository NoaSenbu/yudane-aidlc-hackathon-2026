# Unit-2 Auth & Profile — NFR Requirements Plan

> Construction Phase / Per-Unit Loop / Unit-2 の NFR 評価 + 技術選定。
> 参照: [Unit-2 Functional Design](../unit-2-auth-profile/functional-design/) / [Unit-1 NFR Requirements](../unit-1-platform/nfr-requirements/) / [要件書 §6](../../inception/requirements/requirements.md)
> 作成: 2026-05-29 / ステージ: 🟢 CONSTRUCTION / NFR Requirements

---

## 0. Unit-1 から継承する横断 NFR（再質問しない）

Unit-1 で確定済みのため Unit-2 でもそのまま適用:

| 観点 | 継承する Unit-1 規定 |
|---|---|
| ApiClient タイムアウト | REST 接続 3s / 全体 10s（NFR-PERF-01/02） |
| カバレッジ | Mobile/Backend 基盤 85%、純ロジック 95%（NFR-COV） |
| SECURITY 基盤 | 01/02/03/05/06/08/09/15 は Unit-1 実装を継承 |
| PBT | shrinking/seed/example 併存（NFR-PBT 共通） |
| 観測 | EMF 土台 + 命名規約（Q3=B、メトリクス名は Unit-2 が追記） |
| 可用性 | フォールバックは各 Unit（Q6=B）、ヘルスチェックは Unit-1 |
| マイルストーン | 段階達成（MVP 5/30 / 決勝 6/26、Q7=A） |

→ Unit-2 固有の NFR（認証性能・オンボ完了率・MFA 可用性・PII 強化）のみ質問する。

---

## 1. 設計判断のための質問

`[Answer]:` タグで回答してください。

### Question 1
Unit-2 の **認証・オンボーディングの性能目標**をどうしますか？（US-AUTH-01 の 90 秒、§6.2 コールドスタート 2s）

A) **目標を定量化**（オンボ各画面の保存 API < 500ms / サインイン < 1.5s / MFA 検証 < 1s / オンボ全体 90 秒以内（UX 目標）/ Home スナップショット取得 < 800ms）— 推奨
B) Unit-1 の汎用目標（REST 全体 10s）のみ適用、Unit-2 固有目標は設けない
C) MVP では性能目標を設けず、決勝前に計測して設定
X) Other（[Answer]: の後に記述）

[Answer]: C

### Question 2
US-AUTH-01 の **オンボーディング完了率を NFR 指標として計測**しますか？（中毒性指標の入口、§6.1）

A) **計測する**（オンボ開始→完了率 / 各画面の離脱率 / 平均完了時間をテレメトリ（Unit-1 EMF 土台）で計測。目標: 完了率 80%+、平均 90 秒以内）— ダメ化ファネルの起点として有用、推奨
B) 完了率のみ計測（画面別離脱は計測しない）
C) MVP では計測しない（決勝で追加）
X) Other（[Answer]: の後に記述）

[Answer]: C

### Question 3
**MFA / 認証の可用性・セキュリティ要件**をどこまで Unit-2 で満たしますか？（US-AUTH-02、SECURITY-12/14）

A) **MVP で MFA 必須 + ロックアウト + リセット冷却、決勝で Alarm 完備**（MVP: TOTP MFA / 5 回失敗 15 分ロック / 72h リセット冷却。決勝: 認証失敗の CloudWatch Alarm + 異常検知 + 監査ログ 90 日）— Q7=A 段階達成と整合、推奨
B) MFA・ロックアウト・全 Alarm を MVP からフル実装
C) MVP は MFA 基本のみ、ロックアウト/リセット冷却は決勝
X) Other（[Answer]: の後に記述）

[Answer]: C

### Question 4
Unit-2 が扱う **PII（email / 予算 / 負債フラグ）の保護強化**をどうしますか？（Unit-1 の default-deny マスクを継承しつつ）

A) **Unit-1 の sanitizer を継承 + Unit-2 固有 PII を allowlist 管理**（email は既存 PII、予算額/負債フラグ/ブランド嗜好は「ログ出力しない」方針で allowlist に追加しない = 自動マスク。DynamoDB は KMS 暗号化（Unit-1 共通設定））— fail-safe 継承、推奨
B) Unit-2 で独自のマスクルールを追加実装
C) Unit-1 の sanitizer をそのまま使い、追加考慮なし
X) Other（[Answer]: の後に記述）

[Answer]: A

### Question 5
Unit-2 が追記する **メトリクス名（S-04 カタログ追加分）**をどうしますか？（Q3=B: 各 Unit が命名規約に従い追記）

A) **auth ドメインのメトリクスを定義**（`auth.signin.success_rate` / `auth.mfa.verify_latency` / `auth.onboarding.completion_rate` / `auth.onboarding.dropoff` / `profile.debt.flag_rate`。命名規約 `<unit>.<domain>.<metric>` 準拠）— 推奨
B) 最小限（サインイン成功率 + オンボ完了率のみ）
C) Unit-8 集計で代替し Unit-2 独自メトリクスは持たない
X) Other（[Answer]: の後に記述）

[Answer]: B

---

## 2. 実行ステップ（チェックボックス）

### Part 1: 計画 + 質問
- [x] Unit-2 Functional Design / Unit-1 NFR の分析
- [x] NFR Requirements Plan の作成（本ファイル）
- [x] ユーザーが Q1〜Q5 に回答（Q1=C/Q2=C/Q3=C/Q4=A/Q5=B、Q2-Q3 に矛盾・不整合検出）
- [x] 回答の分析 → clarification（1=B/2=B/3=A）で確定。US-AUTH-03 は倫理理由で MVP 残置

### Part 2: NFR 成果物の生成（承認後）
- [x] `aidlc-docs/construction/unit-2-auth-profile/nfr-requirements/nfr-requirements.md`（性能 / 計測 / MFA 可用性 / 負債セーフガード / PII / カバレッジ + Unit-1 継承の明示）
- [x] `tech-stack-decisions.md`（Amplify Auth v6 / Cognito トリガー / S-03 再利用。大半は Unit-1 継承）
- [x] 自己レビュー（FD AC との整合・診断エラー）— tech-stack diagnostics 0、nfr-requirements は Kiro Spec Format 誤検出のみ
- [ ] 完了メッセージ + 承認ゲート

---

## 3. Extension 適合の予定
| Extension | 扱い |
|---|---|
| SECURITY-12（MFA） | Q3 で MFA 可用性要件を確定 |
| SECURITY-14（アラート） | Q3 で認証失敗 Alarm を確定 |
| PII 保護 | Q4 で Unit-2 固有 PII の fail-safe 継承を確定 |
| PBT-04（idempotency） | オンボ段階保存・初期化の冪等性（Unit-2 FD で確定済み、NFR で計測方針） |
