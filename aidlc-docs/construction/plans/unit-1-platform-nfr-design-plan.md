# Unit-1 Platform — NFR Design Plan

> Construction Phase / Per-Unit Loop / Unit-1 Platform の NFR 設計（パターン + 論理コンポーネント）計画。
> 参照: [NFR Requirements](../unit-1-platform/nfr-requirements/) / [Functional Design](../unit-1-platform/functional-design/) / [services.md](../../inception/application-design/services.md)
> 作成: 2026-05-29 / ステージ: 🟢 CONSTRUCTION / NFR Design
> 確定済み: Q1=A / Q2=A / Q3=B / Q4=A / Q5=A / Q6=B / Q7=A（NFR Requirements）

---

## 0. このステージの狙い

NFR Requirements で確定した「数値・方針」を、**設計パターン + 論理コンポーネント** に落とし込む。Unit-1 は横断基盤のため、ここで決めるパターンは他 7 Unit に継承される。

| NFR | 落とし込む設計パターン候補 |
|---|---|
| タイムアウト 2 系統（Q2） | ApiClient の Request Policy パターン（REST / SSE のポリシー分離） |
| リトライ（Q5/FD） | 指数バックオフ + jitter、冪等メソッド限定 |
| PII default-deny（Q4=refinedA） | Allowlist Sanitizer パターン + Decorator（B-12 が Powertools をラップ） |
| 観測 EMF 土台（Q3=B） | Facade（B-12 metric）+ 命名規約、カタログは各 Unit |
| 可用性（Q6=B） | ヘルスチェック + 構造化ログのみ（サーキットブレーカは持たない） |
| 認可土台（Q4） | API Gateway Authorizer + Lambda 冒頭の sub 照合（IDOR 対策） |

---

## 1. 設計判断のための質問

`[Answer]:` タグで回答してください。Unit-1 は方針が概ね固まっているため、設計パターンの選定に絞った 4 問です。

### Question 1
ApiClient（M-12）の **リクエストポリシーの実装パターン**をどうしますか？（タイムアウト2系統・リトライ・401リフレッシュ・相関ID付与・エラー変換を内包）

A) **単一の `apiFetch` + Request Policy オブジェクト**（呼び出し時に `{ kind: 'rest' | 'stream', timeout?, retry? }` を渡し、内部で interceptor チェーン（auth → correlation → timeout → retry → errorMap）を適用）— 横断既定値 + 各 Unit の上書きが両立、推奨
B) `restFetch` / `streamFetch` の2関数に分離（明示的だが共通処理が重複しやすい）
C) クラスベースの ApiClient インスタンス（DI でテスト容易、RN では軽量さに欠ける）
X) Other（[Answer]: の後に記述）

[Answer]: A

### Question 2
B-12 AuditLogger の **PII マスキング実装パターン**をどうしますか？（Q4=refinedA: default-deny / Lambda Powertools ラッパー）

A) **Allowlist Sanitizer + Powertools Decorator**（ログ出力直前に context を再帰走査し、S-04 allowlist 外を full-mask する純関数 sanitizer を噛ませる。Powertools Logger を薄くラップし全 Lambda 共通で適用）— fail-safe を構造的に強制、推奨
B) Powertools の標準ログマスク機能（指定キーのみ）を使う（denylist 寄りになり Q4 の fail-safe 方針と不整合）
C) ログ呼び出し側が sanitize 済みの値を渡す規約のみ（ライブラリは素通し、漏れリスク）
X) Other（[Answer]: の後に記述）

[Answer]: A

### Question 3
テレメトリ送信（M-13 → B-14）の **配送設計パターン**をどうしますか？（Q6=B: フォールバック土台は持たない / Q3=B: EMF 土台のみ）

A) **クライアント側 バッファ + 退避キュー（At-least-once）**（メモリキュー → flush 失敗時 AsyncStorage 退避 → 再送。B-14 は EMF put が idempotent なので重複は集計誤差で吸収。サーバー側に専用キュー（SQS 等）は MVP では設けず API 同期受信）— シンプルで §6.3 の規模に十分、推奨
B) クライアント → SQS → B-14（非同期バッファ、信頼性高いが MVP にはオーバースペック）
C) 即時送信のみ（バッファなし、Q6=B の精神に最も近いが取りこぼし発生）
X) Other（[Answer]: の後に記述）

[Answer]: A

### Question 4
横断的な **認可（SECURITY-08）の設計パターン**をどう土台化しますか？（Unit-1 が土台、業務判定は各 Unit）

A) **API Gateway Lambda Authorizer（JWT 検証）+ Lambda 冒頭の共通デコレータ（sub ↔ path userId 照合）**（認証は Authorizer で一元化、IDOR 対策の sub 照合は共通デコレータ/ミドルウェアで全 Lambda に強制適用、リソースオーナー業務判定は各 Unit が実装）— 推奨
B) 各 Lambda が個別に JWT 検証 + 照合（重複多く漏れリスク）
C) API Gateway Authorizer のみ（Lambda 側の sub 照合を省略、IDOR リスク）
X) Other（[Answer]: の後に記述）

[Answer]: A

---

## 2. 実行ステップ（チェックボックス）

### Part 1: 計画 + 質問
- [x] NFR Requirements 成果物の分析
- [x] NFR Design Plan の作成（本ファイル）
- [x] ユーザーが Q1〜Q4 に回答（全問 A）
- [x] 回答の分析・曖昧さ検出（矛盾なし）

### Part 2: NFR 設計成果物の生成（承認後）
- [x] `aidlc-docs/construction/unit-1-platform/nfr-design/nfr-design-patterns.md`
  - レジリエンス / 性能 / セキュリティ / 観測の設計パターンを Unit-1 向けに確定
- [x] `aidlc-docs/construction/unit-1-platform/nfr-design/logical-components.md`
  - ApiClient interceptor チェーン / AuditLogger sanitizer / Telemetry パイプライン / Authorizer + 認可デコレータ / ヘルスチェック の論理コンポーネント構成
- [x] 自己レビュー（NFR Requirements との整合・診断エラー）— 診断エラー 0
- [ ] 完了メッセージ提示 + 承認ゲート

---

## 3. Extension 適合の予定

| Extension | 本ステージでの扱い |
|---|---|
| SECURITY-08（認可 / IDOR） | Q4 で Authorizer + 共通デコレータの認可パターンを確定 |
| SECURITY-03/09（ログ / エラー秘匿） | Q2 で Allowlist Sanitizer パターンを確定、500 系の詳細秘匿を設計に反映 |
| SECURITY-11（セキュアデザイン / rate limit） | nfr-design-patterns に API Gateway rate limit + 専用モジュール分離を記載 |
| SECURITY-15（fail-closed） | リトライ・認可・マスキングの各パターンで fail-closed 既定を明記 |
| PBT-03/04（invariant / idempotency） | Telemetry の At-least-once（Q3=A）と EMF idempotent 集計の整合を logical-components に記載 |
