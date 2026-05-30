# Unit-4 Reel — NFR Requirements

> Unit-4 Reel（🎬 エージェント型リール UC-02）の非機能要件。Unit-4 固有の品質目標 + Unit-1 から継承する横断 NFR 基盤への適合。
> 参照: [Functional Design](../functional-design/) / [NFR Requirements Plan](../../plans/unit-4-reel-nfr-requirements-plan.md) / [要件書 §6](../../../inception/requirements/requirements.md) / [Unit-1 NFR Requirements](../../unit-1-platform/nfr-requirements/) / [tech.md](../../../../.kiro/steering/tech.md)
> 確定方針: Q1=A / Q2=A / Q3=A / Q4=A / Q5=A / Q6=A / Q7=A / Q8=A / Q9=A / Q10=A

---

## 0. サマリ

| 観点 | Unit-4 の要件 | 確定根拠 |
|---|---|---|
| 性能 | フィード p95 800ms（MVP）/ 500ms（決勝）・遷移記録 p95 400ms・リール 60fps | Q1 / Q2 / 要件書 §6.2 |
| スケール | 〜10K DAU・深夜帯スパイク・DynamoDB On-Demand・Redis キャッシュ TTL 6h | Q3 / §6.3 |
| 可用性 | 依存別 graceful degradation・Safeguard 取得失敗は fail-closed | Q4 |
| カバレッジ | 推薦/遷移/リンクの純ロジック 90%/85%、カタログ 85%、UI は全体目標 | Q5 |
| テスタビリティ | ALG ごとに PBT 性質割当（round-trip / invariant / idempotency）+ example 併存 | Q6 / §6.5 |
| セキュリティ | 認可・遷移ゲート・外部 API 秘匿・モデレーション・Secrets Manager | Q8 / §6.4 |
| 観測 | 北極星補助 + Reel 固有メトリクスを S-04 カタログへ（`reel.<verb>`） | Q7 / §6.1 |
| A11y | ジェスチャーにボタン代替 + コントラスト AA + SR ラベル | Q10 / §6.6 |
| マイルストーン | MVP 必須 / 決勝最適化の段階達成 | Q9 |

---

## 1. 性能要件（NFR-PERF、Q1 / Q2）

| ID | 要件 | 目標値 | 計測 | マイルストーン |
|---|---|---|---|---|
| NFR-PERF-01 | フィード取得 `GET /v1/reel` サーバー処理 | p95 800ms（MVP）/ 500ms（決勝） | サーバーメトリクス（EMF） | MVP（800ms）/ 決勝（500ms） |
| NFR-PERF-02 | フィード初回ページ UI 描画 | 1s 以内 | クライアント計測 | MVP |
| NFR-PERF-03 | リール描画 / スクロール | 60fps 維持（§6.2） | フレーム計測 / 目視 | MVP |
| NFR-PERF-04 | Amazon 遷移記録 `POST /v1/amazon-transitions` | p95 400ms | サーバーメトリクス | MVP |
| NFR-PERF-05 | リランク・深夜ブースト挿入（ALG-RANK/BOOST） | インメモリ純関数、サーバー処理内で誤差（< 数 ms） | 単体ベンチ | MVP |
| NFR-PERF-06 | カタログ取得（ALG-CATALOG） | キャッシュヒット時 < 50ms / ミス時は外部 API レイテンシ依存 | キャッシュヒット率メトリクス | MVP |
| NFR-PERF-07 | EXP 即時反映（US-02-02 AC-4） | 遷移レスポンスに ExpAward を同梱（B-13 が EXP +1 を同期付与・即時トースト可）。嗜好ベクトル学習（B-08 日次バッチ）は非同期 | 遷移レスポンス検証 | MVP |

> 論破初回トークン 300ms（§6.2）は Unit-3 の要件。Reel は左スワイプで論破へ遷移するのみ（Unit-3 が担当）。

---

## 2. スケーラビリティ要件（NFR-SCALE、Q3）

| ID | 要件 | 方針 | マイルストーン |
|---|---|---|---|
| NFR-SCALE-01 | 想定負荷 | 〜10K DAU、ピーク数十 req/s（深夜帯 22〜2 時に集中、US-02-01） | MVP |
| NFR-SCALE-02 | Lambda 同時実行 | AWS 既定の範囲内（B-03/B-13 は VPC 外想定で ENI 制約回避、詳細は Infra Design） | MVP |
| NFR-SCALE-03 | DynamoDB キャパシティ | On-Demand（PAY_PER_REQUEST）。`AmazonTransitions` / `SafeguardStates` / `ReelImpressions` | MVP |
| NFR-SCALE-04 | Creators API レート制限吸収 | ElastiCache Redis キャッシュ TTL 6h（B-11、**決勝の Creators ライブ時のみ**。MVP はダミーカタログをプロセス内保持し Redis 不使用） | 決勝 |
| NFR-SCALE-05 | 本格オートスケール設計 | 将来プロダクト化時に再評価（backlog、ハッカソン範囲外） | — |

---

## 3. 可用性・フォールバック要件（NFR-AVAIL、Q4）

依存別の **graceful degradation**。Unit-1 は共通フォールバック土台を持たない（Unit-1 Q6=B）ため、Reel が自身の縮退を実装する。

| ID | 依存 | 失敗時の挙動 | 根拠 |
|---|---|---|---|
| NFR-AVAIL-01 | カタログ外部 API / Creators 失敗 | ダミー or キャッシュ済みカタログにフォールバック（ALG-CATALOG） | Q4 / Q7=A |
| NFR-AVAIL-02 | カレンダー ctx（Unit-6）不在 | 通常推薦にフォールバック（カレンダー加点なし） | Q4 / Q10=A（FD） |
| NFR-AVAIL-03 | LLM ラベル/コピー生成失敗 | 決定論テンプレートにフォールバック（フィードが崩れない） | Q4 / Q4=A（FD） |
| NFR-AVAIL-04 | ストレス推定不可 | `low` 扱い → 深夜ブースト抑止（**安全側**、過剰な高単価提示を避ける） | Q4 |
| NFR-AVAIL-05 | Safeguard 状態取得失敗 | **fail-closed**（遷移をブロック、`safeguard.*` 409 相当）。SECURITY-09 整合 | Q4 / Q8=A |
| NFR-AVAIL-06 | エラー伝播 | 外部 API 失敗は DomainError（external-api.*）に変換、詳細を body に出さない | Q8 / Unit-1 ERR 体系 |

> **設計判断（Q4=A の核心）**: 「ユーザー体験の縮退」は許容するが「セーフガードの縮退」は許容しない。カタログ/ラベル/カレンダーは degrade してでもフィードを出すが、Safeguard だけは fail-closed で遷移を止める（NG-4 / FR-FUNNEL-05）。

---

## 4. カバレッジ要件（NFR-COV、Q5）

| ID | 対象 | Line | Branch | 根拠 |
|---|---|---|---|---|
| NFR-COV-01 | B-03 推薦・リランク（ALG-RANK/BOOST/PITCH/LABEL の純ロジック部） | 90%+ | 85%+ | 推薦順位・ブースト判定の誤りは体験とダメ化設計に直結 |
| NFR-COV-02 | B-13 遷移記録（ALG-TRANSITION） | 90%+ | 85%+ | 冪等性・EXP・Safeguard 連携の誤りは二重計上/上限破りに直結 |
| NFR-COV-03 | B-10 Special Link（ALG-LINK） | 90%+ | 85%+ | NG-8 / 環境ガードの誤りは規約違反・本番事故に直結 |
| NFR-COV-04 | B-11 カタログ（ALG-CATALOG、アダプタ/キャッシュ） | 85%+ | — | ポート/アダプタ切替・キャッシュ・ダミー注入 |
| NFR-COV-05 | M-03 ReelScreen（UI / ジェスチャー） | tech.md 全体目標（80%/70%） | — | UI 寄り、E2E（IT-04/IT-05）で補完 |

> LLM 呼び出しの外部 I/O 部分・モデレーション結果はモック化してロジックを計測。LLM 応答そのものは coverage 対象外宣言可（TDD 例外と整合）。

---

## 5. テスタビリティ要件（NFR-PBT、Q6 / PBT-01〜10）

| ID | 対象ロジック | PBT 性質 | フレームワーク |
|---|---|---|---|
| NFR-PBT-01 | ALG-LINK（Special Link 生成） | round-trip（PBT-02）: `extractAsin(generate(input).url).asin === input.asin`、純関数（同一入力→同一 URL）、短縮しない | fast-check + Hypothesis |
| NFR-PBT-02 | ALG-RANK（リランク） | invariant（PBT-03）: 決定論（同一入力→同一順位）/ `score == Σcomponents` / NG カテゴリ除外 / 既出抑制 | fast-check + Hypothesis |
| NFR-PBT-03 | ALG-TRANSITION（遷移記録） | idempotency（PBT-04）: 同一 `clientTransitionId` で EXP 加算 ≤ 1・月間カウント二重計上なし / 上限超過で記録されない（invariant） | fast-check + Hypothesis |
| NFR-PBT-04 | ALG-BOOST（深夜ブースト） | 発火条件の真理値表（メタモルフィック）: 時刻×ストレス×フラグの全組合せで発火/抑止が仕様一致、価格は 1.5〜3 倍範囲内 | fast-check + Hypothesis |
| NFR-PBT-05 | ReelCursor encode/decode | round-trip（PBT-02）: encode → decode で `seenCardKeys`/`rankPosition`/`boostConsumed` 一致 | fast-check + Hypothesis |
| NFR-PBT-06 | ドメインジェネレータ（PBT-07） | 購入履歴 / 価格 / StressLevel / TimeBucket / SafeguardFlags の現実的ジェネレータを提供（他テストで再利用） | fast-check + Hypothesis |
| 共通 | 全 PBT | shrinking + seed ログ必須（PBT-08）、主要ロジックは example-based 併存（PBT-10） | — |

---

## 6. セキュリティ要件（NFR-SEC、Q8 / SECURITY-01〜15）

Unit-1 基盤を継承し、Unit-4 固有の重点を上乗せ。

### 6.1 Unit-4 が上乗せ実装する重点

| ルール | Unit-4 の責務 | マイルストーン |
|---|---|---|
| SECURITY-08（認可 / IDOR） | 遷移記録・フィード取得で `userId == JWT.sub` を検証。ストレス値・user 識別はクライアント値を信用せずサーバー算出（REEL-TR-06 / REEL-STRESS-04） | MVP |
| SECURITY-11（セキュアデザイン） | 遷移前 Safeguard ゲート必須、取得失敗は fail-closed（NFR-AVAIL-05）。S-03 を直接利用 | MVP |
| SECURITY-05（入力検証） | `GET /reel` の cursor/limit、`POST /amazon-transitions` の body を契約スキーマで検証 | MVP |
| SECURITY-11（レート制限） | `POST /v1/amazon-transitions` に 429 レスポンス + `X-RateLimit-*` ヘッダを定義（Unit-1 API-09 / api-contracts.md §9.3）。reel.yaml へ非破壊で追記 | MVP |
| SECURITY-09（エラー詳細秘匿） | Creators/外部 API 失敗を `external-api.*` に変換、内部詳細を body に出さない | MVP |
| NG-6 / NG-8（コンテンツ・規約） | ラベル/コピーの出力モデレーション（脅迫・罪悪感強要除去）、Special Link 短縮禁止 | MVP |
| シークレット管理 | Creators API / Associates 認証情報は Secrets Manager / SSM（ハードコード禁止、§6.4） | MVP |

### 6.2 Unit-1 から継承（Unit-4 で再実装しない）

| ルール | 継承元 |
|---|---|
| SECURITY-01（暗号化）/ -02（NW ログ）/ -03（アプリログ + PII マスク）/ -06（IAM 最小権限）/ -10（SBOM）/ -15（例外処理） | Unit-1 基盤 |
| SECURITY-12（認証 / MFA） | Unit-2 の責務（Reel では N/A） |
| SECURITY-04（HTTP ヘッダ） | モバイルのため N/A |
| SECURITY-07（VPC / Endpoint） | Infrastructure Design で確定（次ステージ） |

---

## 7. 観測要件（NFR-OBS、Q7）

Unit-1 の EMF 土台 + 命名規約に乗せ、Reel 固有メトリクスを S-04 TelemetryContracts に追記する。

| ID | メトリクス / イベント | 用途 |
|---|---|---|
| NFR-OBS-01 | `reel.viewed` | カード閲覧数（分母） |
| NFR-OBS-02 | `reel.swiped`（left/right） | 論破遷移率 / カート監視登録率 |
| NFR-OBS-03 | `reel.double_tap` / `reel.amazon_tap` | **北極星補助: リール経由 Amazon 遷移率**（§6.1） |
| NFR-OBS-04 | `reel.boost_shown` | 深夜ブースト表示数（M-2 効果測定） |
| NFR-OBS-05 | `reel.label_fallback` | LLM ラベル生成のフォールバック率（品質監視） |
| NFR-OBS-06 | フィード生成レイテンシ（サーバー EMF） | NFR-PERF-01 の回帰監視 |
| NFR-OBS-07 | カタログキャッシュヒット率（サーバー EMF） | NFR-PERF-06 / レート制限健全性 |
| NFR-OBS-08 | 遷移 409（Safeguard block）率（サーバー EMF） | セーフガード発動頻度・非ターゲット保護の可視化 |

**規約**: イベント名は `reel.<verb>`（api-contracts.md §12.2）。PII を properties / 次元に含めない（Unit-1 TEL-02 / 次元カーディナリティ制約）。`userId` は匿名化ハッシュ。

---

## 8. アクセシビリティ要件（NFR-A11Y、Q10）

| ID | 要件 | マイルストーン |
|---|---|---|
| NFR-A11Y-01 | ジェスチャー操作（左/右スワイプ・ダブルタップ）に**ボタン等の代替操作**を用意（スワイプ不能ユーザー向け） | MVP |
| NFR-A11Y-02 | カラーコントラスト WCAG 2.2 AA 相当（Unit-1 テーマトークン継承） | MVP |
| NFR-A11Y-03 | カード画像・所有感ラベル・タグにスクリーンリーダー用テキスト | 決勝（MVP は主要要素） |
| NFR-A11Y-04 | 動的フォントスケーリング（Unit-1 土台継承） | 決勝 |

> WCAG 全面準拠は宣言しない（実機検証・専門レビュー未実施、§6.6）。

---

## 9. マイルストーン別達成目標（Q9 段階達成）

### MVP（2026-05-30）で必須
- 推薦（購入履歴ベース + 決定論リランク、ALG-RANK/BOOST）
- 3 ジェスチャー + 確認オーバーレイ（ALG-GESTURE、FR-REEL-05）
- 遷移記録（冪等 + EXP + Safeguard 同期ゲート、ALG-TRANSITION）
- Special Link（dev 仮リンク、ALG-LINK）
- ダミーカタログ（ALG-CATALOG、DummyCatalogAdapter）
- 主要 PBT（NFR-PBT-01/02/03 = ALG-LINK/RANK/TRANSITION）
- 北極星テレメトリ（NFR-OBS-03）
- 性能: リール 60fps / フィード p95 800ms / 遷移 p95 400ms
- 可用性: graceful degradation（NFR-AVAIL-01〜05）
- セキュリティ: SECURITY-05/08/09/11 + NG-6/NG-8 モデレーション + POST 429 レート制限
- A11y: コントラスト AA + ジェスチャーのボタン代替

### 決勝（2026-06-26）までに最適化
- ベクトル検索（Titan + OpenSearch、[B-204](../../../../doc/backlog.md)）
- Creators API 本番接続（Approved Mobile Application 承認後、ALG-CATALOG の CreatorsApiAdapter）
- フィード p95 500ms
- 全 PBT（NFR-PBT-04/05/06）・全メトリクス（NFR-OBS-04〜08）
- A11y: SR フル対応・動的フォント（NFR-A11Y-03/04）

---

## 10. Extension コンプライアンスサマリ（NFR Requirements 段階）

| Extension | 状態 | 備考 |
|---|---|---|
| SECURITY-05/08/09/11 | ✅ Compliant | §6.1 で Unit-4 固有の重点を定義 |
| SECURITY-01/02/03/06/10/15 | ✅ 継承 | Unit-1 基盤を継承（§6.2） |
| SECURITY-04 | N/A | モバイルのため該当なし |
| SECURITY-07 | ⏭ 次ステージ | Infrastructure Design で VPC 構成 |
| SECURITY-12 | ⏭ Unit-2 | MFA は Unit-2 の責務 |
| NG-6 / NG-8 | ✅ Compliant | §6.1 でモデレーション・短縮禁止を NFR 化 |
| PBT-02/03/04/07/08/10 | ✅ Compliant | §5 で ALG ごとに性質割当、ジェネレータ・shrinking・example 併存を規定 |
| PBT-01/05/09 | ✅ Compliant | PBT-01 性質整理（FD）/ PBT-05 Oracle（推薦新旧比較は決勝、B-204 連動）/ PBT-09 fast-check + Hypothesis |
