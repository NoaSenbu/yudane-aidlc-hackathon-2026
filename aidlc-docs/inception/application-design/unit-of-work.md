# Unit of Work

> YUDANE を **並行開発可能な 8 つの Unit** に分解した定義書。各 Unit は独立デプロイ可能な単位として設計する。  
> 参照: [要件書 v0.6](../requirements/requirements.md) / [Application Design](./application-design.md) / [Stories](../user-stories/stories.md) / [UoW Plan](../plans/unit-of-work-plan.md)

## 確定した分割方針（Q1-Q7 回答反映）

| # | 項目 | 確定値 |
|---|---|---|
| Q1 | 分割戦略 | **C**: ハイブリッド（Platform 先行 + コア UC 縦割り） |
| Q2 | チーム 4 名の分担 | **B**: コア UC 担当 + ローテーション |
| Q3 | 実装順序 | **A**: Platform First |
| Q4 | リポジトリ構造 | **A**: モノレポ |
| Q5 | デプロイ単位 | **A**: Unit ごとに独立デプロイ可能（CDK スタック分割） |
| Q6 | API 契約凍結タイミング | **A**: Unit 着手前に OpenAPI 3.1 第 1 版凍結（Shared/schema） |
| Q7 | ストーリー配分粒度 | **A**: 各 Unit に 3〜5 ストーリー |

## コード組織戦略（Greenfield モノレポ）

```
yudane-aidlc-hackathon-2026/
├── mobile/                  # React Native + TypeScript（1 アプリ、Unit ごとに features/ サブディレクトリ）
│   └── src/features/
│       ├── platform/        # Unit-1 の mobile 部分（AppShell, ApiClient, Telemetry）
│       ├── auth/            # Unit-2 の mobile 部分（AuthModule, オンボ、Home）
│       ├── debate/          # Unit-3
│       ├── reel/            # Unit-4
│       ├── cart/            # Unit-5
│       ├── calendar/        # Unit-6
│       ├── safeguard/       # Unit-7
│       └── report/          # Unit-8
├── backend/                 # Python Lambda 群、Unit 単位でフォルダ分割
│   └── src/
│       ├── auth/            # Unit-2 (B-01, B-08)
│       ├── debate/          # Unit-3 (B-02)
│       ├── reel/            # Unit-4 (B-03, B-10, B-11, B-13)
│       ├── cart/            # Unit-5 (B-04, B-05, B-06)
│       ├── calendar/        # Unit-6 (B-07)
│       ├── safeguard/       # Unit-7 (B-09)
│       ├── report/          # Unit-8 (週次集計ジョブ)
│       ├── telemetry/       # Unit-1 (B-14)
│       └── common/          # Unit-1 (B-12 AuditLogger など)
├── infra/                   # AWS CDK (TypeScript)、Unit 単位で Stack 分割
│   └── lib/
│       ├── platform-stack.ts      # Unit-1（VPC, API Gateway, Cognito UserPool, DynamoDB 共通, ElastiCache, OpenSearch）
│       ├── auth-stack.ts          # Unit-2 固有
│       ├── debate-stack.ts        # Unit-3（Bedrock IAM など）
│       ├── reel-stack.ts          # Unit-4
│       ├── cart-stack.ts          # Unit-5（EventBridge Scheduler, End User Messaging）
│       ├── calendar-stack.ts      # Unit-6
│       ├── safeguard-stack.ts     # Unit-7
│       └── report-stack.ts        # Unit-8
├── shared/                  # Unit-1 が owner、他 Unit は利用のみ
│   ├── schema/              # OpenAPI 3.1 + 自動生成 TS/Python 型
│   ├── asin-extractor/      # S-01
│   ├── safeguard-policy/    # S-03（Mobile と Backend で共有）
│   └── telemetry-contracts/ # S-04
└── aidlc-docs/              # ドキュメント
```

---

## Unit 定義（全 8 Units）

### Unit-1 Platform（🏗️ 横断基盤）

| 項目 | 内容 |
|---|---|
| 目的 | 他全 Unit の開発・デプロイを可能にする基盤の提供 |
| 範囲（Mobile） | M-01 AppShell / M-12 ApiClient / M-13 Telemetry |
| 範囲（Backend） | B-12 AuditLogger（ライブラリ）/ B-14 TelemetryIngestionService |
| 範囲（Shared） | S-01 AsinExtractor / S-02 SchemaRegistry / S-03 SafeguardPolicy / S-04 TelemetryContracts |
| 範囲（Infra） | CDK プロジェクト / VPC / API Gateway / Cognito User Pool / DynamoDB 共通設定 / ElastiCache Redis / OpenSearch Serverless / IAM 基本 / SBOM 生成 |
| 主な責務 | OpenAPI 3.1 第 1 版定義 + 凍結 / 型生成 / モノレポ構造整備 / CI セットアップ |
| 対応 UC | なし（全 UC の前提基盤） |
| ストーリー | なし（基盤 Unit） |
| デプロイ CDK | `platform-stack.ts` |
| 担当 | Member A（PM/UX or インフラ専任） |
| 工数目安 | 2〜3 日 |
| 成功条件 | OpenAPI 凍結 + 型生成 + Auth 以外の全 Backend Lambda がデプロイ可能な状態 |

### Unit-2 Auth & Profile（👤 オンボーディング + ホーム + 日次バッチ）

| 項目 | 内容 |
|---|---|
| 目的 | ユーザー登録・認証・プロファイル初期化・ホーム画面の提供 |
| 範囲（Mobile） | M-02 HomeScreen / M-11 AuthModule |
| 範囲（Backend） | B-01 AuthEdgeLambda / B-08 PreferenceVectorUpdater |
| 主な責務 | Cognito MFA 認証フロー / オンボ（予算感・NG カテゴリ・負債フラグ）/ ホーム画面 / 日次嗜好ベクトル更新 / 週次指標集計（Unit-8 へ供給） |
| 対応 UC | UC-05（判定ロジック: 称号 / Lv 付与）/ UC-06（サブダッシュボード表示）/ UC-07（嗜好ベクトル更新部分）/ UC-08 初期化 |
| ストーリー | **US-AUTH-01, US-AUTH-02, US-AUTH-03（3 本）** + 暗黙的に全 US の前提 |
| デプロイ CDK | `auth-stack.ts` |
| 担当 | Member A（Unit-1 完了後） |
| 工数目安 | 3〜4 日 |
| 依存 | Unit-1 Platform |

### Unit-3 Debate（💬 論破チャット UC-01）

| 項目 | 内容 |
|---|---|
| 目的 | 論破セッションの完全ループ（起動 → Bedrock ストリーミング → 決着） |
| 範囲（Mobile） | M-04 DebateScreen |
| 範囲（Backend） | B-02 DebateLlmService |
| 外部サービス | Amazon Bedrock (**Claude Haiku 4.5 / Sonnet 4.6**) / Titan Embeddings V2 |
| 主な責務 | 論破 UI（チャット + タイピング演出 + 90 秒タイマー）/ 事実 + 心理の 2 軸反論プロンプト合成 / ストリーミング配信 / 論破成功ログ / 個別最適化学習 |
| 対応 UC | UC-01 |
| ストーリー | US-01-01〜05（5 本） |
| デプロイ CDK | `debate-stack.ts` |
| 担当 | Member B（コア専任） |
| 工数目安 | 5〜7 日 |
| 依存 | Unit-1 / Unit-2 |

### Unit-4 Reel（🎬 エージェント型リール UC-02）

| 項目 | 内容 |
|---|---|
| 目的 | 縦型リール UI + AI 推薦エンジン + Amazon 遷移導線 |
| 範囲（Mobile） | M-03 ReelScreen |
| 範囲（Backend） | B-03 ReelRecommendationService / B-10 AssociatesLinkGenerator / B-11 CreatorsApiClient / B-13 AmazonTransitionRecorder |
| 外部サービス | OpenSearch Serverless / Amazon Creators API / Amazon Associates |
| 主な責務 | 縦型スワイプ UI / 嗜好 × 時刻 × カレンダー × 疲労度の推薦 / Special Link 生成 / Amazon アプリ Deep Link / 「確保しておきました」所有感ラベル / EXP 加算 |
| 対応 UC | UC-02 + UC-05（散財 EXP 加算、Amazon タップ時点で EXP を B-13 から B-08 へ送る） |
| ストーリー | US-02-01〜05（5 本） |
| デプロイ CDK | `reel-stack.ts` |
| 担当 | Member C（コア専任） |
| 工数目安 | 5〜7 日 |
| 依存 | Unit-1 / Unit-2 |

### Unit-5 Cart Intercept（🛒 カート介入 UC-03）

| 項目 | 内容 |
|---|---|
| 目的 | Share Extension → 監視登録 → 3 段追撃 → 論破への導線 |
| 範囲（Mobile） | M-05 CartInterceptScreen / M-08 ShareExtensionNativeModule / M-09 PushNotificationHandler |
| 範囲（Backend） | B-04 CartIntakeHandler / B-05 CartAttackScheduler / B-06 NotificationDispatcher |
| 外部サービス | EventBridge Scheduler / AWS End User Messaging Push / Amazon Creators API（キャッシュ経由で参照） |
| 主な責務 | iOS Share Extension（Swift）/ Android Share Target（Kotlin）/ ASIN 抽出 / 監視リスト登録 / 30m/6h/24h 追撃ジョブスケジュール / APNs/FCM Push 配信 / 通知タップから論破遷移 |
| 対応 UC | UC-03 |
| ストーリー | US-03-01〜05（5 本） |
| デプロイ CDK | `cart-stack.ts` |
| 担当 | Member D（コア専任、ネイティブ作業あり） |
| 工数目安 | 6〜8 日（ネイティブ作業含む） |
| 依存 | Unit-1 / Unit-2 |

### Unit-6 Calendar（📅 カレンダー連動推薦 UC-04）

| 項目 | 内容 |
|---|---|
| 目的 | 予定駆動の商品提案 + 論破材料供給 |
| 範囲（Mobile） | M-10 CalendarNativeModule |
| 範囲（Backend） | B-07 CalendarPredictionService |
| 外部サービス | iOS EventKit / Google Calendar API / Bedrock（商品カテゴリ推定） |
| 主な責務 | 端末ローカル分類（プライバシー配慮 FR-CAL-05）/ カテゴリ → 商品カテゴリ推定 / Unit-3/4 に context 供給 |
| 対応 UC | UC-04 |
| ストーリー | US-01-03（カレンダー論破材料、副担当）+ **US-CAL-01, US-CAL-02, US-CAL-03（主担当 3 本）** + US-02-01/05 の予定由来推薦（Unit-4 から参照） |
| デプロイ CDK | `calendar-stack.ts` |
| 担当 | Member B（Unit-3 Debate 完了後、後半フェーズ） |
| 工数目安 | 3 日（圧縮） |
| 依存 | Unit-1 / Unit-2 / Unit-3 API 契約凍結済み |
| 成功条件 | Unit-3 論破プロンプト + Unit-4 リール推薦に予定カテゴリ ctx を供給でき、US-01-03 の受入条件が満たされる |

### Unit-7 Safeguard（🛡️ セーフガード UC-08）

| 項目 | 内容 |
|---|---|
| 目的 | 月間上限 / 冷却モード / 負債検知 / NG カテゴリ / データ削除の網羅的実装 |
| 範囲（Mobile） | M-07 SafeguardScreen |
| 範囲（Backend） | B-09 SafeguardRulesEngine |
| 範囲（Shared） | S-03 SafeguardPolicy（Unit-1 で定義、本 Unit がコンシューマ） |
| 主な責務 | 全 Amazon 遷移前の authorizer（B-09）/ 月間上限スライダー UI / 冷却モード トグル / NG カテゴリチェックリスト / データエクスポート / アカウント削除 |
| 対応 UC | UC-08 |
| ストーリー | **US-SAFE-01, US-SAFE-02, US-SAFE-03, US-SAFE-04（主担当 4 本）** + US-01-05（副担当、クールダウン部分）/ US-03-05（副担当、月間上限到達部分） |
| デプロイ CDK | `safeguard-stack.ts` |
| 担当 | Member C（Unit-4 Reel 完了後、後半フェーズ） |
| 工数目安 | 3〜4 日（主担当ストーリー 4 本に対応） |
| 依存 | Unit-1 / Unit-2。Unit-3/4/5 の API に middleware として組み込まれる |
| 成功条件 | API Gateway Authorizer / Lambda middleware として Unit-3/4/5 の前段に挿入済み、SafeguardPolicy (S-03) の判定が Mobile と Backend で一致、US-SAFE-01〜04 + US-01-05 / US-03-05 のセーフガード動作確認 |

### Unit-8 Dame Report（📊 ダメ化レポート UC-06/07 表示）

| 項目 | 内容 |
|---|---|
| 目的 | 週次「委ね度」レポート / 称号 / Before-After 可視化 / タグ雲編集 |
| 範囲（Mobile） | M-06 DameReportScreen |
| 範囲（Backend） | 週次集計ジョブ（Unit-2 の B-08 PreferenceVectorUpdater を拡張）/ WeeklyReports テーブル |
| 主な責務 | 週次指標集計（論破→Amazon 遷移率、カート介入成約率、深夜帯利用比率等）/ ダメ化ポートフォリオ編集 UI / レポート通知（SVC-07 と連携） |
| 対応 UC | UC-05（Lv / 称号 / Streak の表示層）+ UC-06 逆家計簿 + UC-07 ダメ化ポートフォリオ |
| ストーリー | **US-REP-01, US-REP-02, US-REP-03（主担当 3 本）** + US-02-05（副担当、確保ラベル効果の可視化）/ US-01-04（副担当、個別最適化の成果可視化） |
| デプロイ CDK | `report-stack.ts` |
| 担当 | Member D（Unit-5 Cart 完了後、後半フェーズ） |
| 工数目安 | 3 日（主担当ストーリー 3 本に対応） |
| 依存 | Unit-1 / Unit-2 / Unit-3・4・5（活動データ源泉） |
| 成功条件 | 週次集計ジョブが稼働し、北極星指標（論破→Amazon 遷移率、カート介入成約率等）が `WeeklyReports` テーブルに出力される。M-06 DameReportScreen で 4 指標の Before/After と嗜好タグ雲が表示される |

---

## チーム 4 名の役割マトリクス（Q2=B 実装案、工数現実性修正版）

**各コア担当がコア Unit 完了後に 1 つのサポート Unit を主担当で引き受ける** 方針に修正。Member A は全期間 Platform 運用 + OpenAPI 凍結守護 + CI メンテ + 横断レビューに専念し、過負荷を回避する。

| メンバー | 前半（Day 1-16） | 後半（Day 17-21） | 工数 |
|---|---|---|---|
| **Member A**（PM/UX + インフラ） | Unit-1 Platform → Unit-2 Auth & Profile | 全期間の Platform 運用 / OpenAPI 守護 / CI メンテ / 横断レビュー / 統合テスト支援 | 2-3d + 3-4d + 継続 |
| **Member B**（Backend + AI） | Unit-3 Debate（専任） | Unit-6 Calendar（主担当）| 5-7d + 3d |
| **Member C**（Mobile + Backend） | Unit-4 Reel（専任） | Unit-7 Safeguard（主担当）| 5-7d + 3d |
| **Member D**（Mobile + ネイティブ） | Unit-5 Cart Intercept（専任） | Unit-8 Dame Report（主担当）| 6-8d + 3d |

これにより各メンバーの総工数は **8〜11 営業日**、3 週間（15 営業日）に十分収まる。サポート Unit は元の 3-4 日見積もりを **3 日に圧縮**（Platform の基盤が整っているため少人数で完走可能）。

## 工数サマリ

| Unit | 工数（日） |
|---|---|
| Unit-1 Platform | 2〜3 |
| Unit-2 Auth & Profile | 3〜4 |
| Unit-3 Debate | 5〜7 |
| Unit-4 Reel | 5〜7 |
| Unit-5 Cart Intercept | 6〜8 |
| Unit-6 Calendar | 3〜4 |
| Unit-7 Safeguard | 3〜4 |
| Unit-8 Dame Report | 3〜4 |

**並行総工数**: 書類審査後の予選デモ（5/30）まで約 3 週間（15 営業日 + 週末）、並行開発で間に合う目算。

---

## ストーリー数サマリ（Q7=A 3〜5 ストーリー/Unit、v1.1 更新）

- Unit-1 Platform: 0（基盤 Unit、全 Unit の副担当）
- Unit-2 Auth & Profile: **3**（US-AUTH-01/02/03）
- Unit-3 Debate: **5**（US-01-01〜05）
- Unit-4 Reel: **5**（US-02-01〜05）
- Unit-5 Cart Intercept: **5**（US-03-01〜05）
- Unit-6 Calendar: **3**（US-CAL-01/02/03）
- Unit-7 Safeguard: **4**（US-SAFE-01/02/03/04）
- Unit-8 Dame Report: **3**（US-REP-01/02/03）
- **合計: 28 ストーリー**（コア 15 + サポート 13）

→ **Unit-1 Platform を除き、全 Unit が 3〜5 本ずつの主担当ストーリーを持つ**。これにより縦割り Unit（各 Unit にデモで見せられる価値）を実現する。

> **v1.0 → v1.1 での変更**: v1.0 はコア 3 Units に 15 本集中、サポート 5 Units は主担当 0 本だった。v1.1 では Q7=A「各 Unit に 3〜5 ストーリー」原案に沿い、サポート 4 Units（Unit-2/6/7/8）にも主担当ストーリーを 3〜4 本ずつ配置。結果として総ストーリー数は 15 → **28** に増加、全 Unit がデモで見せられる独立機能を抱える設計になった。Unit-1 Platform のみ基盤 Unit として主担当ストーリーなし（全 Unit の副担当位置づけ）。

---

## 成功条件（ユニット分解全体）

- [ ] 全 28 ストーリーが少なくとも 1 つの Unit に主担当として割り当てられている（カバレッジ 100%、詳細は [story-map](./unit-of-work-story-map.md)）
- [ ] 各 Unit が独立した CDK スタックでデプロイできる
- [ ] OpenAPI 3.1 第 1 版が Unit-1 で凍結されている
- [ ] Unit 間の依存は DAG（非循環）
- [ ] 4 名 × 3 週間で並行開発可能な工数見積もり
