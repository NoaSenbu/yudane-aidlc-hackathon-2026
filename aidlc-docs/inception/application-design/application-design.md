# Application Design — 統合ビュー

> YUDANE のアプリケーション設計統合ドキュメント。4 つの詳細成果物を束ねる入口。  
> 参照: [要件書 v0.5](../requirements/requirements.md) / [ストーリー](../user-stories/stories.md) / [ペルソナ](../user-stories/personas.md) / [実行計画](../plans/execution-plan.md)

## 構成ドキュメント

| ファイル | 内容 |
|---|---|
| [`components.md`](./components.md) | Mobile / Backend / Shared 3 層のコンポーネント定義（計 31 個）と責務 |
| [`component-methods.md`](./component-methods.md) | 各コンポーネントのメソッドシグネチャ、入出力型（TypeScript / Python） |
| [`services.md`](./services.md) | 7 つのサービス（Debate / Reel / Cart / Calendar / Profile / Safeguard / Notification）のオーケストレーション |
| [`component-dependency.md`](./component-dependency.md) | 依存関係 Mermaid 図、主要データフロー 4 本（カート介入 / リール / カレンダー / 認証）、通信パターン、ストア配置 |

---

## 設計サマリ

### 技術スタック（要件書 v0.5 準拠）

| レイヤ | 選定 |
|---|---|
| Mobile | React Native + TypeScript + AWS SDK v3 + TanStack Query + Zustand |
| Auth | Amazon Cognito（`amazon-cognito-identity-js` 直接利用、Amplify 不採用） |
| API | API Gateway (REST) + Lambda (Python 3.12) |
| Data | 生 DynamoDB + S3 + ElastiCache Redis + OpenSearch Serverless |
| AI | Bedrock（Claude Haiku/Sonnet）+ Titan Embeddings |
| Push | AWS End User Messaging Push + EventBridge Scheduler |
| Amazon | Creators API（商品データ）+ Associates Program（Special Link） |
| IaC | AWS CDK (TypeScript) 単独 |
| CI | GitHub Actions + SBOM |
| PBT | fast-check (TS/RN) + Hypothesis (Python) |

### ディレクトリ構造（暫定案、Units Generation で確定予定）

```
AIDLC-Hackathon-2026-teamname/
├── mobile/                     # React Native + TypeScript
│   ├── src/
│   │   ├── features/           # Feature-based: home/reel/debate/cart/report/safeguard
│   │   ├── shared/             # hooks, ApiClient, AuthModule, Telemetry
│   │   ├── native/             # ShareExtension / Calendar / Push bridges
│   │   └── stores/             # Zustand stores
│   ├── ios/                    # Xcode project + Share Extension target
│   ├── android/                # Gradle project + Share Target
│   └── package.json
│
├── backend/                    # Python Lambda 群
│   ├── src/
│   │   ├── auth/               # B-01 AuthEdgeLambda (Cognito トリガー)
│   │   ├── debate/             # B-02 DebateLlmService
│   │   ├── reel/               # B-03 ReelRecommendationService
│   │   ├── cart/               # B-04 CartIntakeHandler, B-05 CartAttackScheduler
│   │   ├── notification/       # B-06 NotificationDispatcher
│   │   ├── calendar/           # B-07 CalendarPredictionService
│   │   ├── preference/         # B-08 PreferenceVectorUpdater
│   │   ├── safeguard/          # B-09 SafeguardRulesEngine
│   │   ├── associates/         # B-10 AssociatesLinkGenerator
│   │   ├── creators/           # B-11 CreatorsApiClient
│   │   ├── transition/         # B-13 AmazonTransitionRecorder
│   │   ├── telemetry/          # B-14 TelemetryIngestionService
│   │   └── common/             # B-12 AuditLogger など
│   ├── tests/                  # Hypothesis PBT + example-based
│   ├── pyproject.toml
│   └── poetry.lock
│
├── infra/                      # AWS CDK (TypeScript)
│   ├── bin/                    # CDK app entry
│   ├── lib/                    # Stacks: Cognito, ApiGateway, DynamoDB, Lambda, ElastiCache, OpenSearch, EventBridge, EndUserMessaging
│   ├── package.json
│   └── cdk.json
│
├── shared/                     # 横断コンポーネント
│   ├── schema/                 # OpenAPI 3.1 + 生成型
│   ├── asin-extractor/         # S-01
│   ├── safeguard-policy/       # S-03
│   └── telemetry-contracts/    # S-04
│
├── aidlc-docs/                 # 📄 ドキュメントのみ
└── mockup/                     # UI 仮説検証用（Flutter ではなく静的 HTML）
```

### コンポーネント数

- **Mobile**: 13（画面 6 + ネイティブ 3 + 認証/API/計測 3 + シェル 1）
- **Backend**: 14（API Lambda 12 + ロガー 1 + Cognito トリガー 1）
- **Shared**: 4
- **合計**: **31**

### サービス数

- **Orchestration Services**: 7（UC ごとに対応、横断 Notification を 1 つ）

### UC ↔ サービス対応

| UC | サービス |
|---|---|
| UC-01 論破チャット | SVC-01 Debate |
| UC-02 エージェント型リール | SVC-02 Reel |
| UC-03 カート介入 | SVC-03 Cart Intercept |
| UC-04 カレンダー連動 | SVC-04 Calendar-driven Recommendation |
| UC-05 散財ゲーミフィケーション | SVC-05 User Profile & Preference |
| UC-06 逆家計簿サブ | SVC-05（計算ロジックは SafeguardPolicy / PreferenceVectorUpdater に内包） |
| UC-07 ダメ化ポートフォリオ | SVC-05 |
| UC-08 セーフガード | SVC-06 Safeguard |
| 横断 | SVC-07 Notification |

---

## 設計原則の再掲

1. **Feature-based + 軽レイヤード** — 機能ごとにフォルダを切り、UI/hooks/API を同居
2. **Amplify 不採用** — 技術スタック純化、説明容易性優先
3. **EventBridge Scheduler 単独で時間差制御** — Step Functions は採用しない
4. **Mobile と Backend で同じ SafeguardPolicy を使う** — UX 整合
5. **LLM 呼出は Python Lambda に集約** — PBT と相性、ストリーミング制御容易
6. **予定本文はバックエンドに送らない** — プライバシー、§9 NG-7
7. **Amazon 決済に誘導するが保持しない** — §0.1 収益モデル、§9 NG-8

---

## Extension 適合の概要

### SECURITY-01〜15

要件書 §6.4 に全 15 ルールのマッピングあり。Application Design レベルでは:

- コンポーネント境界が SECURITY-11（セキュアデザイン、責務分離）を体現
- B-09 SafeguardRulesEngine は SECURITY-08（認可）の中核
- B-12 AuditLogger は SECURITY-02/03/14（ログ・監査）の基盤

### PBT-01〜10

要件書 §6.5 に対象領域マッピングあり。Application Design レベルでは:

- S-01 AsinExtractor は PBT-02（round-trip）/ PBT-07（ドメインジェネレータ）
- B-05 CartAttackScheduler は PBT-06（stateful: 30m→6h→24h→購入/破棄）
- S-03 SafeguardPolicy は PBT-03（invariant: 上限超過で block）
- B-08 PreferenceVectorUpdater は PBT-04（idempotent）

詳細は Construction フェーズの **Functional Design（per-unit）** で各 Unit ごとに定義する。

---

## 未解決事項（次ステージ Units Generation への申し送り）

1. **Unit 分割の粒度最終確定** — 本設計では Lambda 単位で 12 個 + Mobile 画面 6 個に分けているが、Units Generation で並行開発可能な Unit of Work に再束ね直す
2. **mobile/backend/infra/shared の物理パッケージ分割** — モノレポ or マルチリポの判断
3. **API スキーマの凍結** — OpenAPI 3.1 の第 1 版を Unit 実装前に確定
4. **キャッシュ戦略の詳細** — ElastiCache のキー設計、整合性モデル、TTL
5. **観測メトリクスのカタログ** — CloudWatch カスタムメトリクス名、次元、単位
6. **Amazon Approved Mobile Application 申請の進捗管理** — Hackathon 決勝までの timeline

---

## 次ステージへの接続

- **Units Generation**: 本 Application Design を入力として、Unit of Work の分割・依存関係・ストーリーマップ・実装順序を確定する
- **Functional Design (per-unit)**: Unit ごとに詳細ビジネスルール、データモデル、エラーハンドリングを設計
- **NFR Requirements / Design (per-unit)**: Unit ごとに SECURITY / PBT / Performance / Scalability を具体化
- **Infrastructure Design (per-unit)**: CDK スタック分割、リソース構成、IAM 最小権限
