# Unit-5 Cart Intercept — Tech Stack Decisions

> Construction Phase の Per-Unit Loop NFR Requirements Part 2 Generation 成果物。Unit-5 の Tech Stack 確定（既存スタック整合 + 本 Unit 固有の追加判断）と各ライブラリの採用根拠。
>
> 参照: [nfr-requirements.md](./nfr-requirements.md) / [Functional Design](../functional-design/functional-design.md) / [tech.md（コア技術スタック）](../../../../.kiro/steering/tech.md) / [Unit-1 Functional Design](../../unit-1-platform/functional-design/functional-design.md)

---

## 0. 確定方針

**新規スタック判断は不要**。既に以下で確定済みのスタックを継承し、Unit-5 固有の追加ライブラリのみ Q10 = D で確定。

| ソース | 確定範囲 |
|---|---|
| `tech.md` | 全層の主要スタック（RN / Python / CDK / Bedrock / DDB / EventBridge Scheduler / End User Messaging Push）|
| Unit-1 Functional Design | VPC 配置 / SnapStart / Cognito Authorizer / IdempotencyKeys |
| Unit-5 Functional Design | Q1〜Q8 確定（Expo Config Plugin / Multi Table / 通知テンプレート方式 等）|
| Unit-5 NFR Requirements Q10 | 追加ライブラリ最小化（`responses` dev dep のみ）|

---

## 1. Mobile スタック（既存整合）

| 層 | 採用 | 出典 |
|---|---|---|
| RN ランタイム | React Native 0.76+ (New Architecture: Fabric + TurboModules) | tech.md §2 |
| 言語 | TypeScript 5.x (`strict` + `noUncheckedIndexedAccess`) | tech.md §2 / tech-typescript.md |
| 開発・配布 | **Expo Dev Client + EAS Build**（Expo SDK 52+） | tech.md §2（C-5 確定）|
| ナビゲーション | React Navigation v7 | Unit-1 §1.1 AppShell |
| サーバー状態 | TanStack Query（retry=2、staleTime=60s）| Unit-1 §1.1 |
| クライアント状態 | Zustand（persist ミドルウェア + AsyncStorage）| Unit-1 §1.1 |
| 認証 | Amazon Cognito + Amplify JavaScript v6 Auth モジュールのみ | tech.md §2 |
| Push 通知 | **`expo-notifications`** + ネイティブ拡張（APNs / FCM）| Q5 = C 確定（M-09）|
| Share Extension | **Expo Config Plugin + App Group**（iOS）/ **Intent Filter**（Android）| Q1 = A 確定（M-08）|
| デザイントークン | NativeWind v4（`tailwind.config.js`）| tech.md §2（C-1 確定）|
| 永続化 | `@react-native-async-storage/async-storage` | Unit-1 §1.1 |
| UUID 生成 | `uuid` (npm、v7 / v5 利用) | Unit-1 Q7 整合（Idempotency-Key）|

### 1.1 ターゲット OS バージョン（4 巡目追加、Issue MMM 対応）

| プラットフォーム | 最小サポートバージョン | 推奨ターゲット | 理由 |
|---|---|---|---|
| iOS | **15.0**（iPhone 6s 以降）| iOS 17+ | Share Extension App Group / Background Push の安定動作下限。Expo SDK 52 の最小要件と整合 |
| Android | **API 29（Android 10）**| API 33+ | FCM HTTP v1 API + Foreground Service / Background Restriction の安定動作下限。Expo SDK 52 の最小要件と整合 |

**OS バージョン依存の挙動差異**:

- **iOS 16+**: Clipboard 読取で paste 許可ダイアログ必須（[backlog B-502](../../../../doc/backlog.md) で MVP 見送り）
- **iOS 17+**: UIPasteControl による paste 許可スキップ（決勝向け実装候補、B-502 と整合）
- **Android API 33+**: POST_NOTIFICATIONS 権限が必須（Q5 = C で既に対応、`expo-notifications` が処理）

`app.json` の `expo` セクションに以下設定:

```json
{
  "expo": {
    "ios": { "deploymentTarget": "15.0" },
    "android": { "minSdkVersion": 29 }
  }
}
```

---

## 2. Backend スタック（既存整合）

| 層 | 採用 | 出典 |
|---|---|---|
| ランタイム | Python 3.13 on AWS Lambda | tech.md §2 |
| アーキテクチャ | ARM64（コスト 20% 削減）| Unit-1 §3.2 |
| 入力検証 | Pydantic v2 | tech.md §2 / tech-python.md / SECURITY-05 |
| AWS SDK | `boto3`（DDB / Scheduler / End User Messaging Push）| 標準 |
| ログ・メトリクス | B-12 AuditLogger（log / metric / trace の 3 関数）| Unit-1 §2.1 |
| Idempotency middleware | `with_idempotency`（Unit-1 §3.2 IdempotencyKeys テーブル + S3 連携）| Unit-1 確定 |
| Cold Start 緩和 | **SnapStart**（Python、追加料金ゼロ）| Q4 = B' 確定（cart_intake / dismiss / notification_dispatcher の 3 Lambda 適用）|
| ULID 生成 | `python-ulid` | Unit-1 整合（itemId / notificationId） |

---

## 3. SnapStart 適用範囲（Q4 = B' 確定）

[Unit-1 §3.2 で確定した SnapStart 設定パターン](../../unit-1-platform/functional-design/functional-design.md#32-b-02-debatellmservice-の-snapstart-設定) を本 Unit の以下 3 Lambda に適用。性能 SLO の根拠は [nfr-requirements.md §1.1.1.1 B-04 内部予算配分](./nfr-requirements.md#1111-b-04-lambda-内部の予算配分issue-aaa-対応) を参照:

| Lambda | SnapStart | 理由 |
|---|---|---|
| **B-04 cart_intake** | ✅ ON_PUBLISHED_VERSIONS | US-03-01 AC-3「2 秒以内」を確実に満たすため |
| **B-04 cart_dismiss** | ✅ ON_PUBLISHED_VERSIONS | 「いらない」タップ後のロールバック時に Cold Start 露出すると UX 劣化 |
| B-04 cart_list | ❌ なし | 低頻度（M-05 起動時のみ）+ バッファ可能 |
| B-04 push_token | ❌ なし | 低頻度（起動毎 + ローテーション時のみ）|
| **B-06 notification_dispatcher** | ✅ ON_PUBLISHED_VERSIONS | EventBridge 発火時の遅延がユーザー体験に直結 |

CDK 設定は [Unit-1 §3.2 SnapStart 設定パターン](../../unit-1-platform/functional-design/functional-design.md#32-b-02-debatellmservice-の-snapstart-設定) と同様に `lambda.SnapStartConf.ON_PUBLISHED_VERSIONS` + `Alias` 必須。

---

## 4. Infrastructure スタック（既存整合）

| 層 | 採用 | 出典 |
|---|---|---|
| IaC | AWS CDK (TypeScript) v2 系最新 + Node.js 22 LTS | tech.md §2 |
| データストア | Multi Table Design（DDB On-Demand + KMS CMEK + PITR）| Unit-1 Q6 確定 |
| キャッシュ | ElastiCache Redis（B-11 Creators API キャッシュのみ、本 Unit 直接利用なし）| Unit-1 §3.1 |
| 検索 | OpenSearch Serverless（Unit-4 Reel 専用、本 Unit 利用なし）| Unit-1 §3.1 |
| Authorizer | API Gateway Cognito Authorizer 基本 + Lambda Authorizer（Safeguard 統合）| Unit-1 Q2 = C 確定 |
| Scheduler | EventBridge Scheduler（One-time Schedule + ActionAfterCompletion=DELETE）| Q4 = A 確定（B-05）|
| Push 通知 | AWS End User Messaging Push（Pinpoint EoL 2026-10-30 後継）| tech.md §2 |
| 暗号化 | KMS CMEK（Unit-1 Platform Stack で共有）| Unit-1 §3.1 SECURITY-01 |
| 環境分離 | dev / prd（C-4 = 単一アカウント suffix `developerInitial`）| Unit-1 整合 |

---

## 5. 追加ライブラリ判断（Q10 = D 確定）

### 5.1 採用（dev only）

| ライブラリ | 環境 | 用途 |
|---|---|---|
| `responses` | **dev only** | pytest 用 HTTP Mock。PBT-04（Idempotency）/ PBT-08-local（Latency、[nfr-requirements.md §8.2.1](./nfr-requirements.md#821-pbt-08-localci-上の-pytestロジック単体)）テスト用 |
| `hypothesis` | **dev only** | Backend PBT。[nfr-requirements.md §6.1 採用ライブラリ表](./nfr-requirements.md#61-採用ライブラリ最小化方針) で詳細記載 |
| `fast-check` | **dev only** | Mobile PBT。同上 |
| `moto` | **dev only** | AWS API モック（boto3 の DDB / Scheduler / End User Messaging）。[nfr-requirements.md §6.1](./nfr-requirements.md#61-採用ライブラリ最小化方針) と整合 |

### 5.2 不採用と理由

| 候補 | 不採用理由 |
|---|---|
| AWS Lambda Powertools for Python | [Unit-1 backlog B-001](../../../../doc/backlog.md) で「予選まで観測性スタック全面導入見送り」と確定済み、本 Unit が先行すると整合性が崩れる |
| `apscheduler` | EventBridge Scheduler で完結、不要 |
| `tenacity` | Lambda 同時実行 + EventBridge Retry で代替可能、追加依存を最小化 |

### 5.3 SBOM 整合性（SECURITY-10）

**本 Unit で追加される prod 依存はゼロ**。`responses` のみ dev dep として `requirements-dev.txt` に追加。`package-lock.json` / `poetry.lock` で全依存をピン留め。

---

## 6. CI/CD 統合（既存整合）

| 項目 | 採用 | 出典 |
|---|---|---|
| パイプライン | GitHub Actions | tech.md §2 |
| SBOM | Snyk / Dependabot | tech.md §2 |
| 性能 PBT 自動実行 | **GitHub Actions で PBT-08 を毎 PR 実行**（閾値違反で merge block）| Q9 = C 確定 |
| デプロイ | I-4 確定の CI/CD パイプライン（Unit-1 整合）| dev-commands.md §5 |

---

## 7. Unit 間スタック整合性確認

本 Unit が他 Unit のスタックと矛盾しないことを確認:

| 他 Unit | 整合性 |
|---|---|
| Unit-1 Platform | ✅ IdempotencyKeys / S-01 / S-03 / KMS / Cognito Authorizer / SnapStart 設定パターンを継承 |
| Unit-2 Auth & Profile | ✅ Cognito JWT / Users テーブルへの `pushEndpointId` 追加合意済み（[§8.1](../functional-design/functional-design.md#81-本-unit-が他-unit-owner-にレビュー依頼する事項)）|
| Unit-3 Debate | ✅ `POST /v1/debate-sessions { trigger: "cart-attack", productId: asin }` 契約整合（[§6 シーケンス図](../functional-design/sequence-diagrams.md#3-通知タップ--論破モード遷移us-03-02-ac-3--q7--a)）|
| Unit-4 Reel | ✅ B-11 CreatorsApiClient（Redis キャッシュ）/ B-10 AssociatesLinkGenerator / B-13 AmazonTransitionRecorder を consume |
| Unit-7 Safeguard | ✅ S-03 SafeguardPolicy に `evaluate_notification` 追加合意済み（Member C レビュー）/ Lambda Authorizer 経由統合 |

---

## 8. ハッカソン書類審査・予選評価軸へのインパクト

| 評価軸 | 本ドキュメントの貢献 |
|---|---|
| ビジネス意図の明確さ | （直接貢献なし）|
| Unit 分解の適切さ | **強化**: Unit-5 が新規スタック判断ゼロで既存スタックと完全整合、SBOM 観点で prod 依存追加ゼロ |
| 創造性とテーマ適合性 | （直接貢献なし）|
| ドキュメント品質 | **強化**: SnapStart 適用範囲 / 追加ライブラリ判断 / Unit 間整合確認が一貫展開 |
| AI-DLC プロセス（予選評価軸） | **強化**: tech.md / Unit-1 / 他 Unit の確定事項を継承し矛盾なく統合する判断プロセス |
