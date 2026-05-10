# Unit of Work — Story Map

> 15 ストーリー × 8 Units のカバレッジマッピング。  
> 参照: [Unit of Work](./unit-of-work.md) / [Dependency](./unit-of-work-dependency.md) / [Stories](../user-stories/stories.md)

## 目的

- 全 15 ストーリー（UC-01 論破 5 + UC-02 リール 5 + UC-03 カート介入 5）が **少なくとも 1 つの Unit に主担当** として割り当てられていることを保証
- ストーリー内で言及される他 Unit の機能連動を **副担当** として明示
- 書類審査評価軸「Unit 分解の適切さ（カバレッジ漏れなし）」を満たす

## 主担当 / 副担当マッピング

| ストーリー ID | タイトル | 主担当 Unit | 副担当 Units |
|---|---|---|---|
| **US-01-01** | カート停滞を 1 分論破で翻意させる | **Unit-3 Debate** | Unit-5 Cart（trigger）/ Unit-7 Safeguard（セーフガードチェック）/ Unit-4 Reel（B-10/B-13 遷移連動） |
| **US-01-02** | リール「買わない」を事実ベース反論で翻意させる | **Unit-3 Debate** | Unit-4 Reel（trigger）/ Unit-2 Profile（嗜好ベクトル） |
| **US-01-03** | カレンダー予定を論破材料として差し込む | **Unit-3 Debate** | Unit-6 Calendar（ctx 供給）/ Unit-4 Reel（予定タグ表示） |
| **US-01-04** | 「まだ抵抗」の連打で論破が個別最適化される | **Unit-3 Debate** | Unit-2 Profile（B-08 PreferenceVectorUpdater）/ Unit-8 Dame Report（成約率可視化） |
| **US-01-05** | 3 回連続拒否でクールダウン（セーフガード） | **Unit-3 Debate** | Unit-7 Safeguard（B-09 ルール）/ Unit-2 Profile（負債フラグ）|
| **US-02-01** | 深夜 22 時にコンテキスト連動で高単価リール | **Unit-4 Reel** | Unit-6 Calendar（多忙度 ctx）/ Unit-2 Profile（嗜好ベクトル）|
| **US-02-02** | ダブルタップで Amazon へワンタップ遷移 | **Unit-4 Reel** | Unit-1 Platform（Special Link）/ Unit-7 Safeguard（遷移前チェック）|
| **US-02-03** | 左スワイプで論破モードへ自動遷移 | **Unit-4 Reel** | Unit-3 Debate（遷移先）|
| **US-02-04** | 右スワイプで「後で見る」→ カート監視登録 | **Unit-4 Reel** | Unit-5 Cart（登録先 B-04）|
| **US-02-05** | 「確保しておきました」ラベルで所有感を醸成 | **Unit-4 Reel** | Unit-2 Profile（嗜好ベクトル）/ Unit-6 Calendar（予定タグ連動）|
| **US-03-01** | Amazon Shopping から共有 → ASIN 取込で監視リスト登録 | **Unit-5 Cart** | Unit-1 Platform（S-01 AsinExtractor）/ Unit-4 Reel（B-11 Creators API 共有）|
| **US-03-02** | 30 分 / 6 時間 / 24 時間の 3 段追撃通知 | **Unit-5 Cart** | Unit-1 Platform（End User Messaging Push 基盤）|
| **US-03-03** | クリップボードに Amazon URL → 自動サジェスト | **Unit-5 Cart** | Unit-1 Platform（S-01 AsinExtractor）|
| **US-03-04** | Special Link で Amazon アプリを Deep Link 起動 | **Unit-5 Cart** | Unit-4 Reel（B-10 AssociatesLinkGenerator / B-13 AmazonTransitionRecorder）/ Unit-7 Safeguard |
| **US-03-05** | 月間上限到達時にカート介入を停止（セーフガード） | **Unit-5 Cart** | Unit-7 Safeguard（B-09 ルール）/ Unit-2 Profile（月間上限設定）|

## Unit 別のストーリー配分

| Unit | 主担当ストーリー数 | ストーリー ID |
|---|:---:|---|
| Unit-1 Platform | 0 | （基盤、全ストーリーの前提） |
| Unit-2 Auth & Profile | 0 | （副担当として多数のストーリーに関与） |
| **Unit-3 Debate** | **5** | US-01-01, US-01-02, US-01-03, US-01-04, US-01-05 |
| **Unit-4 Reel** | **5** | US-02-01, US-02-02, US-02-03, US-02-04, US-02-05 |
| **Unit-5 Cart Intercept** | **5** | US-03-01, US-03-02, US-03-03, US-03-04, US-03-05 |
| Unit-6 Calendar | 0 | （副担当として US-01-03, US-02-01, US-02-05 に関与） |
| Unit-7 Safeguard | 0 | （副担当として US-01-05, US-02-02, US-03-04, US-03-05 に関与） |
| Unit-8 Dame Report | 0 | （副担当として US-01-04 の成約率可視化に関与） |
| **合計（主担当）** | **15** | **カバレッジ 100%** |

**Q7=A「各 Unit に 3〜5 ストーリー」について**: コア 3 Units（Unit-3/4/5）が各 5 ストーリーを主担当、サポート Units（Unit-1/2/6/7/8）はストーリー未割当（基盤 / 副担当の位置づけ）。これは書類審査評価軸「縦割り Unit（デモで見せられる価値）」と整合。

## ストーリーカバレッジ検証

```
[US-01-01] ✅ Unit-3 Debate（主）
[US-01-02] ✅ Unit-3 Debate（主）
[US-01-03] ✅ Unit-3 Debate（主）
[US-01-04] ✅ Unit-3 Debate（主）
[US-01-05] ✅ Unit-3 Debate（主）
[US-02-01] ✅ Unit-4 Reel（主）
[US-02-02] ✅ Unit-4 Reel（主）
[US-02-03] ✅ Unit-4 Reel（主）
[US-02-04] ✅ Unit-4 Reel（主）
[US-02-05] ✅ Unit-4 Reel（主）
[US-03-01] ✅ Unit-5 Cart（主）
[US-03-02] ✅ Unit-5 Cart（主）
[US-03-03] ✅ Unit-5 Cart（主）
[US-03-04] ✅ Unit-5 Cart（主）
[US-03-05] ✅ Unit-5 Cart（主）
```

**カバレッジ: 15/15 = 100%** ✅

## Unit 完成とストーリー Done の関係

各 Unit の完成判定は、主担当ストーリーの受入条件（GIVEN/WHEN/THEN + ダメ化シグナル）がすべて満たされることで定義する。

### Unit-3 Debate の完成条件（例）

- [ ] US-01-01 のすべての AC-1〜4 がパス（カート停滞通知 → 300ms 初回トークン → Amazon 遷移）
- [ ] US-01-02 のすべての AC-1〜4 がパス（事実→心理の 2 軸切替）
- [ ] US-01-03 のすべての AC-1〜4 がパス（カレンダー予定ベース論破）
- [ ] US-01-04 のすべての AC-1〜4 がパス（個別最適化 + 90 秒タイマー）
- [ ] US-01-05 のすべての AC-1〜4 がパス（クールダウン + 非ターゲット保護）

同様に Unit-4 は US-02-01〜05、Unit-5 は US-03-01〜05 で判定。

## 副担当の責任範囲

副担当 Unit は「主担当 Unit が呼び出すインターフェースや提供する機能」を責任持って提供する:

- **Unit-3 が Unit-5 から呼び出される**（US-01-01）→ Unit-3 の API が Unit-5 のトリガーに応答できる
- **Unit-6 が Unit-3/4 に ctx 供給**（US-01-03, US-02-01, US-02-05）→ Unit-6 の API が Unit-3/4 の呼び出しに応答できる
- **Unit-7 が Unit-3/4/5 に middleware 挿入**（US-01-05, US-02-02, US-03-04, US-03-05）→ Unit-7 の Authorizer が API Gateway に登録済み

副担当側の Unit が未完成でも、主担当は **スタブ** を使って先行実装可能（Q6=A OpenAPI 凍結の恩恵）。

## 非ターゲットペルソナの扱い

- **田中 一郎（FIRE 志向）**: US-01-05 で Unit-3 のクールダウン発動 → Unit-7 が早期撤退ポリシー適用
- **山田 健二（借金保有者）**: US-03-05 で Unit-2 オンボの負債フラグ → Unit-7 が初期から冷却モード ON

両者とも **Unit-7 Safeguard の重要な検証ケース**。Unit-7 の PBT で明示的に扱う。

## Extension 適合のストーリーマッピング

ストーリー受入条件内の Extension 要件（SECURITY / PBT）は、主担当 Unit の Functional Design（per-unit）で具体化する。

| Extension ルール | 主な該当ストーリー | 担当 Unit |
|---|---|---|
| SECURITY-05（入力検証）| US-03-01（ASIN 抽出）/ US-01-01（カート停滞判定）| Unit-5 / Unit-3 |
| SECURITY-08（認可）| US-02-02, US-03-04（Amazon 遷移前）| Unit-4 / Unit-5 / Unit-7 |
| SECURITY-12（認証）| 全ストーリーの前提 | Unit-2 |
| PBT-02（round-trip）| US-03-01（ASIN 抽出/復元）| Unit-1（Shared S-01）|
| PBT-03（invariant）| US-03-05（月間上限超過で block）| Unit-7 |
| PBT-06（stateful）| US-03-02（30m→6h→24h→購入/破棄）| Unit-5 |

---

## Summary

- ✅ 全 15 ストーリーを 3 つのコア Unit に **5 本ずつ**配分、カバレッジ 100%
- ✅ 各ストーリーに副担当 Unit を明示、Unit 間の連動責任が明確
- ✅ 非ターゲットペルソナの扱いを Unit-7 Safeguard に集約
- ✅ ストーリー受入条件の Extension 適合を Unit に紐付け、Functional Design に引き継ぐ
