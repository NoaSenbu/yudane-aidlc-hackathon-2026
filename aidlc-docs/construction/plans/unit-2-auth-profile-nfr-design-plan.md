# Unit-2 Auth & Profile — NFR Design Plan

> Construction Phase / Per-Unit Loop / Unit-2 の NFR 設計（パターン + 論理コンポーネント）。
> 参照: [Unit-2 NFR Requirements](../unit-2-auth-profile/nfr-requirements/) / [Unit-2 Functional Design](../unit-2-auth-profile/functional-design/) / [Unit-1 NFR Design](../unit-1-platform/nfr-design/)
> 作成: 2026-05-29 / ステージ: 🟢 CONSTRUCTION / NFR Design

---

## 0. Unit-1 から継承するパターン（再質問しない）

| Unit-1 パターン | Unit-2 での適用 |
|---|---|
| PAT-RESIL-01/02（Retry / Token Refresh） | ApiClient 経由で自動継承 |
| PAT-SEC-01（Authorizer + require_owner） | 全 users/{userId} エンドポイントに適用 |
| PAT-SEC-02（Allowlist Sanitizer） | B-01/B-08 のログに適用、Unit-2 PII を allowlist 外に |
| PAT-SEC-03（Fail-closed Error Handler） | B-01/B-08 ハンドラに適用 |
| PAT-OBS-01/02（Metric Facade / Correlation） | auth メトリクスを EMF で |
| LC-01〜08 | ApiClient / AuditLogger / SafeguardPolicy / Authorization を再利用 |

→ Unit-2 固有のパターン（オンボ段階保存 / MFA チャレンジ / 負債ステートマシン / バッチ）のみ質問する。

---

## 1. 設計判断のための質問

`[Answer]:` タグで回答してください。

### Question 1
オンボ段階保存（ALG-ONBOARD）の **状態管理パターン**をどうしますか？（途中再開 / 冪等、Q1=A FD）

A) **サーバー権威 + クライアントドラフトの二層**（サーバーの `User.onboardingStep` を正とし、クライアントは Zustand persist でドラフト保持。各画面 onNext で PATCH（冪等 upsert）→ step 前進。再開はサーバー step から）— FD と整合、推奨
B) クライアント完結（全画面入力後に一括 POST、サーバーは step 管理しない）
C) サーバーセッション（バックエンドにオンボセッションを持つ）
X) Other（[Answer]: の後に記述）

[Answer]: 

### Question 2
負債フラグ解除（72h クーリングオフ、ALG-DEBT）の **ステートマシン実装パターン**をどうしますか？

A) **タイムスタンプ + 遅延評価**（`debtReleaseRequestedAt` を保存し、SafeguardPolicy 評価時 or 日次バッチで `now - requestedAt >= 72h` を判定して解除。専用スケジューラを持たない）— Step Functions 不採用方針と整合、推奨
B) EventBridge Scheduler で 72h 後に解除ジョブを発火
C) クライアント側でカウントダウン管理
X) Other（[Answer]: の後に記述）

[Answer]: 

### Question 3
B-08 の **日次/週次バッチの起動パターン**をどうしますか？（Q5=A FD: 日次=嗜好ベクトル / 週次=指標集計を別ハンドラ）

A) **EventBridge cron 2 本 + 単一 Lambda の別エントリ**（日次 cron → update_preference ハンドラ、週次 cron（日曜22時）→ generate_weekly_report ハンドラ。同一デプロイ単位で 2 エントリ）— Q5=A と整合、推奨
B) Lambda 2 本に分離（日次用と週次用で別関数）
C) 単一 cron + 関数内で曜日判定
X) Other（[Answer]: の後に記述）

[Answer]: 

### Question 4
MFA チャレンジ（ALG-MFA）の **認証フロー実装パターン**をどうしますか？（Amplify Auth v6、Q4=A FD）

A) **Amplify Auth のチャレンジ駆動ステートマシン**（signIn → MFA challenge 検出 → confirmMfa の状態遷移を AuthModule 内の有限状態機械で管理。失敗カウント・ロックは Cognito 側 + クライアント表示）— 推奨
B) 各画面が個別に Amplify API を呼ぶ（状態機械なし）
C) カスタム認証フロー（Cognito Custom Auth Lambda Trigger）
X) Other（[Answer]: の後に記述）

[Answer]: 

---

## 2. 実行ステップ（チェックボックス）

### Part 1: 計画 + 質問
- [x] Unit-2 NFR Requirements / Unit-1 NFR Design の分析
- [x] NFR Design Plan の作成（本ファイル）
- [x] ユーザーが Q1〜Q4 に回答（全問 A）
- [x] 回答の分析・曖昧さ検出（矛盾なし）

### Part 2: NFR 設計成果物の生成（承認後）
- [x] `aidlc-docs/construction/unit-2-auth-profile/nfr-design/nfr-design-patterns.md`（オンボ状態管理 / 負債ステートマシン / バッチ / MFA フロー + Unit-1 継承）
- [x] `logical-components.md`（AuthModule / OnboardingController / B-01 / B-08 / HomeSnapshot の論理構成）
- [x] 自己レビュー（診断エラー 0、Unit-1 パターン継承の整合）+ 完了メッセージ + 承認ゲート

---

## 3. Extension 適合の予定
| Extension | 扱い |
|---|---|
| SECURITY-12 | Q4 で MFA チャレンジステートマシンを確定 |
| SECURITY-08/09 | Unit-1 PAT-SEC-01/03 継承 |
| NG-4 | 負債ステートマシン（Q2）で 72h クーリングオフを設計 |
| PBT-04 | オンボ段階保存（Q1）の冪等性パターン |
