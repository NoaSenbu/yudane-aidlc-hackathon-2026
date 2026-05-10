# Unit of Work Plan (AI-DLC Inception / Units Generation)

## 参照ドキュメント

* 要件書: [`requirements.md`](../requirements/requirements.md) [v0.5](../requirements/requirements.md)

* ユーザーストーリー: [`stories.md`](../user-stories/stories.md)（15 本 × 3 コア UC）

* ペルソナ: [`personas.md`](../user-stories/personas.md)

* Application Design: [`application-design.md`](../application-design/application-design.md)（31 コンポーネント + 7 サービス）

* 実行計画: [`execution-plan.md`](./execution-plan.md)（Workflow Planning 承認済み）

## 分割の目的

書類審査評価軸「**Unit 分解の適切さ**」に直接貢献する成果物を作る。Units of Work は以下を満たすこと:

* **並行開発可能**（4 名チームが分担できる粒度）

* **単一責任**（UI だけ / API 層だけのような混在は避け、UC と整合した縦割り）

* **依存関係が明示**（実装順序を根拠付きで決められる）

* **ストーリーカバレッジ 100%**（全 15 ストーリーが少なくとも 1 つの Unit に属する）

## 暫定の Unit 候補（ユーザーへの選択肢提示用）

Application Design の 31 コンポーネントを以下 3 つの戦略で分割できる:

### 戦略 A: サービス軸（SVC アライン）

| Unit                  | 範囲                                                |
| --------------------- | ------------------------------------------------- |
| Unit-1 Debate         | M-04 + B-02（UC-01）                                |
| Unit-2 Reel           | M-03 + B-03 + B-10 + B-11 + B-13（UC-02）           |
| Unit-3 Cart Intercept | M-05 + M-08 + B-04 + B-05 + B-06（UC-03）           |
| Unit-4 Calendar       | M-10 + B-07（UC-04）                                |
| Unit-5 Profile        | M-02 + M-06 + B-01 + B-08 + B-14（UC-05/06/07）     |
| Unit-6 Safeguard      | M-07 + B-09 + S-03（UC-08）                         |
| Unit-7 Platform       | M-01 + M-11 + M-12 + M-13 + B-12 + Shared 層 + IaC |

合計 **7 Units**。7 サービスとほぼ 1 対 1 で理解しやすい。ただし「機能価値」が分割単位にならないため、ユーザーストーリーは複数 Unit にまたがる。

### 戦略 B: フィーチャースライス

| Unit                   | 範囲                           |
| ---------------------- | ---------------------------- |
| Unit-1 Onboarding      | Auth + 初回予算設定 + NG カテゴリ      |
| Unit-2 Share Intake    | Share 受信 → ASIN → 監視リスト登録    |
| Unit-3 Cart Attack     | 追撃 Scheduler + Push + 論破への導線 |
| Unit-4 Debate Core     | 論破 LLM + チャット UI             |
| Unit-5 Reel Experience | リール UI + 推薦エンジン              |
| Unit-6 Calendar Boost  | カレンダー連動推薦                    |
| Unit-7 Dame Report     | ダメ化レポート + ゲーミフィケーション         |
| Unit-8 Safeguard Net   | 月間上限 / 冷却 / 負債検知             |
| Unit-9 Platform        | 共通基盤（Auth 以外）、IaC            |

合計 **9 Units**。各 Unit が **デモで見せられる UC 単位の価値** を持つ。ハッカソン審査軸「Unit 分解の適切さ（縦割り Unit 推奨）」に強い。

### 戦略 C: ハイブリッド（コア UC 縦割り + 共通基盤横割り）

| Unit                  | 範囲                                                     | 対応 UC / 担当 |
| --------------------- | ------------------------------------------------------ | ---------- |
| Unit-1 Platform       | IaC / API Gateway / Cognito / CDK スタック / Shared 層 / CI | 全体基盤       |
| Unit-2 Auth & Profile | M-11 + B-01 + M-02 + B-08 + B-14 + オンボーディング            | UC-05/07   |
| Unit-3 Debate         | M-04 + B-02 + B-12                                     | UC-01      |
| Unit-4 Reel           | M-03 + B-03 + B-10 + B-11 + B-13                       | UC-02      |
| Unit-5 Cart Intercept | M-05 + M-08 + B-04 + B-05 + B-06                       | UC-03      |
| Unit-6 Calendar       | M-10 + B-07                                            | UC-04      |
| Unit-7 Safeguard      | M-07 + B-09 + S-03                                     | UC-08      |
| Unit-8 Dame Report    | M-06 + 週次集計 + 称号                                       | UC-07 表示層  |

合計 **8 Units**。Platform を最初に作って他 Unit を並行させる戦略。ハッカソン向きで、審査軸に対しても縦割り + Unit 間依存明示ができる。

***

## 設計の判断ポイント（ユーザー回答必須）

### Q1. Unit 分割戦略

* **A**: サービス軸（SVC アライン、7 Units）

* **B**: フィーチャースライス（9 Units、各 Unit がデモ可能な UC 単位）

* **C（推奨）**: **ハイブリッド**（8 Units、Platform を先行 + コア UC 縦割り）

* **D**: 別案（指示ください）

\[Answer]:C

### Q2. チーム 4 名の分担方針

* **A**: Unit 固定割当（1 人 2 Unit 担当、スプリント期間中は固定）

* **B（推奨）**: **コア UC 担当 + ローテーション**（Unit-3/4/5 はコア、各 1 名が専任 + 残り 1 名が Platform + Safeguard + Dame Report 横断）

* **C**: 全員がすべての Unit に関わる（小規模チームに向く）

* **D**: PM 1 名 + Dev 3 名の明確分離

\[Answer]:B

### Q3. 実装順序の優先ルール

* **A（推奨）**: **Platform First**（Unit-1 Platform → Unit-2 Auth → 並行でコア UC 3 つ → サポーティング）。依存解消優先、ブロッキング回避

* **B**: User Value First（動くデモを最短で作る、最優先 Unit のみ端から端まで完成）

* **C**: Greedy Parallel（全 Unit を並行着手、依存が出たら調整）

\[Answer]:A

### Q4. リポジトリ構造

* **A（推奨）**: **モノレポ**（`mobile/` `backend/` `infra/` `shared/` を単一 Git リポで管理）

* **B**: マルチリポ（Unit ごとに別リポ、依存は git submodule または npm/pip パッケージ）

* **C**: 混成（フロント/バックエンド/IaC で 3 リポ）

モノレポは開発スピード優先、審査時の説明も容易。

\[Answer]:A

### Q5. デプロイ単位

* **A（推奨）**: **Unit ごとに独立デプロイ可能**（CDK スタック分割、各 Unit が関連リソースを 1 スタックに）

* **B**: まとめてデプロイ（単一 CDK スタック、リスク低く簡単）

* **C**: コア Unit（Debate/Reel/Cart）のみ独立、他は一括

\[Answer]:A

### Q6. API 契約の凍結タイミング

* **A（推奨）**: **Unit 着手前に第 1 版凍結**（OpenAPI 3.1、Shared/schema に置く）

* **B**: 並行実装中に合意しながら進化

* **C**: 一旦モック、Unit 完成後に統合

\[Answer]:A（詳細説明を受けて確定）

### Q7. ストーリー配分の粒度

* **A（推奨）**: 各 Unit に **3〜5 ストーリー** を割り当て、スプリント単位で消化可能にする

* **B**: 1 Unit あたり 1〜2 ストーリー（小さく早い）

* **C**: 1 Unit あたり 5 以上（大きく少ない）

\[Answer]:A

***

## 計画フェーズ チェックリスト

* [x] Step 1: 要件書 v0.5 / ストーリー / Application Design / ペルソナ読み込み

* [x] Step 2-4: 本プラン作成（分割戦略 / Unit 候補 / 判断ポイント）

* [ ] Step 5-6: ユーザーが Q1〜Q7 の \[Answer]: タグに回答

* [ ] Step 7-8: 回答の曖昧性解析（必要なら追加質問）

* [ ] Step 9-11: 計画の最終承認

## 生成フェーズ チェックリスト

* [x] `aidlc-docs/inception/application-design/unit-of-work.md` を生成（Unit 定義 / 範囲 / コンポーネント / 責務 / コード構成戦略）
* [x] `aidlc-docs/inception/application-design/unit-of-work-dependency.md` を生成（依存マトリクス / ブロッキング関係 / 実装順序の Mermaid 図）
* [x] `aidlc-docs/inception/application-design/unit-of-work-story-map.md` を生成（15 ストーリーを Unit に割り当て、カバレッジ 100%）
* [x] ストーリーカバレッジ検証（漏れなし）
* [x] 診断エラー・リンク整合チェック
* [x] 生成物の承認を得る
* [x] `aidlc-state.md` 更新（Units Generation 完了マーク）
