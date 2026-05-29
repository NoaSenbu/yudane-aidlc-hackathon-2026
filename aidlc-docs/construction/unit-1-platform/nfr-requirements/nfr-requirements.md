# Unit-1 Platform — NFR Requirements

> Unit-1 Platform（横断基盤）の非機能要件。Unit-1 自身の品質目標 + 他 7 Unit が継承する横断 NFR 基盤の規定値。
> 参照: [Functional Design](../functional-design/) / [要件書 §6](../../../inception/requirements/requirements.md) / [tech.md](../../../../.kiro/steering/tech.md)
> 確定方針: Q1=A / Q2=A / Q3=B / Q4=A / Q5=A / Q6=B / Q7=A

---

## 0. サマリ

| 観点 | Unit-1 の要件 | 確定根拠 |
|---|---|---|
| 性能 | ApiClient タイムアウト 2 系統 / コールドスタート 2s / テレメトリ overhead < 1ms | Q2 / 要件書 §6.2 |
| カバレッジ | Shared 純ロジック Line 95%+ / Branch 90%+、Mobile/Backend 基盤 Line 85%+ | Q1 |
| セキュリティ | SECURITY 基盤項目を Unit-1 が一元実装し全 Unit に継承 | Q4 / §6.4 |
| テスタビリティ | 対象ロジックごとに PBT 性質を割当 + example-based 併存 | Q5 / §6.5 |
| 可用性 | Unit-1 はヘルスチェック + 構造化ログのみ。フォールバック中身は各 Unit | Q6 / §6.7 |
| 観測 | EMF 出力土台 + メトリクス命名規約 + overhead 上限のみ（カタログは各 Unit） | Q3 / §6.1 |
| A11y | WCAG 2.2 AA 相当の土台（テーマトークン / SR 規約） | §6.6 |
| マイルストーン | 段階達成（MVP 5/30 で必須、決勝 6/26 で最適化） | Q7 |

---

## 1. 性能要件（NFR-PERF）

| ID | 要件 | 目標値 | 計測 | マイルストーン |
|---|---|---|---|---|
| NFR-PERF-01 | ApiClient 通常 REST タイムアウト | 接続 3s / 全体 10s | クライアントログ | MVP |
| NFR-PERF-02 | ApiClient SSE タイムアウト | 接続 3s / アイドル 30s / 全体無制限 | クライアントログ | MVP |
| NFR-PERF-03 | アプリ起動コールドスタート | 2s 以下 | 起動イベント計測 | 決勝（MVP は計測のみ） |
| NFR-PERF-04 | Telemetry.track のオーバーヘッド | 1 呼び出し 1ms 未満・UI スレッド非ブロック | ベンチマーク | MVP |
| NFR-PERF-05 | Telemetry flush | 背景実行（メインスレッド非ブロック）/ バッチ送信 | コードレビュー + 計測 | MVP |
| NFR-PERF-06 | ApiClient リトライによる追加遅延 | GET のみ最大 2 回、base 300ms 指数バックオフ + jitter | 単体テスト | MVP |

**注**: 論破初回トークン 300ms（§6.2）は Unit-3 の要件。Unit-1 は SSE 土台（ALG-STREAM）で初回トークン計測点を提供するのみ。

---

## 2. カバレッジ要件（NFR-COV、Q1=A）

| ID | 対象 | Line | Branch | 根拠 |
|---|---|---|---|---|
| NFR-COV-01 | S-01 AsinExtractor | 95%+ | 90%+ | 多 Unit が依存する純ロジック、バグ波及防止 |
| NFR-COV-02 | S-03 SafeguardPolicy | 95%+ | 90%+ | 全 Amazon 遷移の gate、誤判定の影響大 |
| NFR-COV-03 | B-12 AuditLogger（マスキング） | 95%+ | 90%+ | PII 漏洩リスクの最後の砦 |
| NFR-COV-04 | M-12 ApiClient | 85%+ | — | 横断インフラ、リトライ・エラー分岐を網羅 |
| NFR-COV-05 | M-13 Telemetry / B-14 | 85%+ | — | バッファリング・退避ロジック |
| NFR-COV-06 | M-01 AppShell | tech.md 全体目標（80%/70%） | — | UI 寄り、E2E で補完 |

---

## 3. セキュリティ要件（NFR-SEC、Q4=A / SECURITY-01〜15）

Unit-1 が **基盤として一元実装し全 Unit へ継承する** ルールと、各 Unit が実装するルールを区別する。

| ルール | Unit-1 の責務 | 実装担当 | マイルストーン |
|---|---|---|---|
| SECURITY-01 暗号化 | DynamoDB/S3 の KMS 暗号化既定、TLS 1.2+ 強制を CDK 基盤で設定 | Unit-1 | MVP |
| SECURITY-02 ネットワークログ | API Gateway 実行/アクセスログを CloudWatch 集約する基盤設定 | Unit-1 | MVP |
| SECURITY-03 アプリログ | B-12 AuditLogger（構造化 JSON + 相関 ID + PII マスク default-deny） | Unit-1 | MVP |
| SECURITY-05 入力検証 | API Gateway + Lambda 入口の JSON Schema 検証土台、S-01 ASIN フォーマット検証 | Unit-1 | MVP |
| SECURITY-06 IAM 最小権限 | Lambda 個別ロールの雛形、ワイルドカード禁止規約 | Unit-1 | MVP |
| SECURITY-08 認可 | JWT 検証土台（ApiClient ヘッダ付与 / userId と sub の照合規約）。**リソースオーナー業務判定は各 Unit** | Unit-1（土台）+ 各 Unit | MVP |
| SECURITY-09 ハードニング | fail-closed 既定、エラー詳細秘匿（ERR-05）、S3 パブリック遮断 | Unit-1 | MVP |
| SECURITY-10 SBOM | Snyk / Dependabot を CI 組込み、ロックファイルコミット | Unit-1 | MVP（基本）/ 決勝（フル） |
| SECURITY-11 セキュアデザイン | Safeguard / 認可ロジックの専用モジュール分離（S-03）、API rate limit 土台 | Unit-1 | MVP |
| SECURITY-13 整合性 | 相関 ID 伝搬、Amazon 遷移履歴の監査ログ土台 | Unit-1（土台） | MVP |
| SECURITY-14 アラート | 認証失敗 / 権限エラーの CloudWatch Alarm 雛形、ログ保持 90 日 | Unit-1 | MVP（基本）/ 決勝（全アラート） |
| SECURITY-15 例外処理 | グローバルエラーハンドラ、全外部呼び出し try/catch、fail-closed | Unit-1 | MVP |
| SECURITY-04 HTTP ヘッダ | （管理画面/Web 向け。Unit-1 のモバイルでは N/A、将来 Web 版で適用） | N/A | — |
| SECURITY-07 ネットワーク | VPC 内 Lambda / VPC Endpoint は Infrastructure Design で構成 | Unit-1（次ステージ） | 決勝 |
| SECURITY-12 認証 | Cognito MFA フロー / セッション属性は **Unit-2 が実装**（Unit-1 は User Pool 基盤のみ） | Unit-2 | — |

---

## 4. テスタビリティ要件（NFR-PBT、Q5=A / PBT-01〜10）

| ID | 対象ロジック | PBT 性質 | フレームワーク |
|---|---|---|---|
| NFR-PBT-01 | S-01 AsinExtractor | round-trip（PBT-02）: 任意有効 ASIN を含む URL → 抽出 → 一致。冪等正規化 | fast-check（TS）+ Hypothesis（Py）|
| NFR-PBT-02 | S-03 SafeguardPolicy | invariant（PBT-03）: `remaining>=0`・`実効上限<=月間上限`・決定論。idempotency（PBT-04） | fast-check + Hypothesis |
| NFR-PBT-03 | M-13/B-14 Telemetry | round-trip（PBT-02）: TelemetryEnvelope serialize ⇔ deserialize 一致 | fast-check + Hypothesis |
| NFR-PBT-04 | B-12 マスキング | invariant: 「未分類キーは必ずマスクされる（fail-safe）」をジェネレータで検証 | fast-check + Hypothesis |
| NFR-PBT-05 | S-01/S-03 クロス言語一致 | TS 実装と Python 実装が同一入力 → 同一出力（golden test） | 両 FW + golden fixtures |
| 共通 | 全 PBT | shrinking + seed ログ必須（PBT-08）、主要ロジックは example-based 併存（PBT-10） | — |
| 共通 | ドメインジェネレータ（PBT-07） | ASIN / 金額 / フラグ組合せの現実的ジェネレータを Unit-1 が提供（他 Unit が再利用） | — |

---

## 5. 可用性・運用要件（NFR-AVAIL、Q6=B）

| ID | 要件 | Unit-1 の責務 | マイルストーン |
|---|---|---|---|
| NFR-AVAIL-01 | ヘルスチェックエンドポイント | `GET /v1/health`（依存サービス状態を返す簡易版）を提供 | MVP |
| NFR-AVAIL-02 | 構造化ログ + 90 日保持 | B-12 + CloudWatch Logs 保持設定 | MVP |
| NFR-AVAIL-03 | SLO 99.5% | 基盤（APIGW/Lambda/DynamoDB）の可用性確保。SLO 計測は決勝までに | 決勝 |
| NFR-AVAIL-04 | フォールバック | **Unit-1 は土台を持たない（Q6=B）**。各 Unit が自身の縮退（静的推薦カタログ等）を実装。Unit-1 はログ + ヘルスチェックのみ提供 | 各 Unit |

> **Q6=B の帰結**: ApiClient はエラーを DomainError として各 Unit に正しく伝播することに責任を持つが、サーキットブレーカや degrade フックは Unit-1 では提供しない。各 Unit が必要に応じて TanStack Query のエラーハンドリングで縮退する。

---

## 6. 観測要件（NFR-OBS、Q3=B）

| ID | 要件 | Unit-1 の責務 |
|---|---|---|
| NFR-OBS-01 | EMF 出力土台 | B-12 `metric()` / B-14 が EMF 形式で CloudWatch Metrics にカスタムメトリクスを出力する**ライブラリ**を提供 |
| NFR-OBS-02 | メトリクス命名規約 | `<unit>.<domain>.<metric>` 形式の命名規約 + 次元カーディナリティ制約（userId/asin を次元に入れない）を規定 |
| NFR-OBS-03 | オーバーヘッド上限 | track < 1ms、flush は背景（NFR-PERF-04/05 と同一） |
| NFR-OBS-04 | メトリクス名カタログ | **各 Unit が S-04 TelemetryContracts に追記**（Unit-1 は雛形と登録の仕組みのみ提供）。北極星指標の集計経路（services.md）は維持 |
| NFR-OBS-05 | X-Ray トレース | B-12 `trace()` で相関 ID 付き X-Ray セグメント土台を提供 |

> **Q3=B の帰結**: Unit-1 は「メトリクスをどう出すか（EMF + 命名規約 + overhead）」の土台に責務を限定。「何を計測するか（具体メトリクス名）」は各 Unit が定義。これにより Unit-1 が他 Unit のメトリクスを先回り定義しすぎず、かつ北極星指標の集計基盤は壊れない。

---

## 7. アクセシビリティ要件（NFR-A11Y）

| ID | 要件 | Unit-1 の責務 | マイルストーン |
|---|---|---|---|
| NFR-A11Y-01 | カラーコントラスト WCAG 2.2 AA 相当 | テーマトークン（Indigo / cold rose / cyan）を AA 目標で定義 | MVP |
| NFR-A11Y-02 | スクリーンリーダー（VoiceOver/TalkBack） | ナビゲーション殻の role / label 規約を提供 | 決勝 |
| NFR-A11Y-03 | 動的フォント | ルートのテキストスケーリング土台 | 決勝 |

> WCAG 全面準拠は宣言しない（§6.6、実機検証・専門レビュー未実施）。

---

## 8. マイルストーン別達成目標（Q7=A 段階達成）

### MVP（2026-05-30）で必須
- NFR-PERF-01/02/04/05/06（タイムアウト・テレメトリ overhead・リトライ）
- NFR-COV-01〜06（カバレッジ目標）
- SECURITY 基盤項目（01/02/03/05/06/08 土台/09/11/13 土台/15）
- NFR-PBT-01〜05（主要 PBT）
- NFR-OBS-01〜05（EMF 土台・命名規約）
- NFR-AVAIL-01/02（ヘルスチェック・ログ）
- NFR-A11Y-01（コントラスト）

### 決勝（2026-06-26）までに最適化
- NFR-PERF-03（コールドスタート 2s チューニング）
- SECURITY-07（VPC/Endpoint）/ SECURITY-10 フル SBOM / SECURITY-14 全アラート
- NFR-AVAIL-03（SLO 99.5% 計測）
- NFR-A11Y-02/03（SR / 動的フォント）

---

## 9. Extension コンプライアンスサマリ（NFR Requirements 段階）

| Extension | 状態 | 備考 |
|---|---|---|
| SECURITY-01/02/03/05/06/08/09/10/11/13/14/15 | ✅ Compliant | §3 で Unit-1 の基盤実装責務を定義 |
| SECURITY-04 | N/A | モバイルのため該当なし（将来 Web 版で適用） |
| SECURITY-07 | ⏭ 次ステージ | Infrastructure Design で VPC/Endpoint 構成 |
| SECURITY-12 | ⏭ Unit-2 | MFA フローは Unit-2 の責務 |
| PBT-01〜10 | ✅ Compliant | §4 で対象ロジックごとに性質割当、shrinking/seed/example-based 併存を規定 |
