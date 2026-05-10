# Unit of Work — Story Map

> 28 ストーリー × 8 Units のカバレッジマッピング（v1.1）。  
> 参照: [Unit of Work](./unit-of-work.md) / [Dependency](./unit-of-work-dependency.md) / [Stories](../user-stories/stories.md)

## 目的

- 全 28 ストーリー（コア 15 + サポート 13）が **少なくとも 1 つの Unit に主担当** として割り当てられていることを保証
- ストーリー内で言及される他 Unit の機能連動を **副担当** として明示
- 書類審査評価軸「Unit 分解の適切さ（カバレッジ漏れなし）」を満たす

## 主担当 / 副担当マッピング

### コア UC（15 ストーリー）

| ストーリー ID | タイトル | 主担当 Unit | 副担当 Units |
|---|---|---|---|
| **US-01-01** | カート停滞を 1 分論破で翻意させる | **Unit-3 Debate** | Unit-5 Cart（trigger）/ Unit-7 Safeguard（セーフガードチェック）/ Unit-4 Reel（B-10/B-13 遷移連動） |
| **US-01-02** | リール「買わない」を事実ベース反論で翻意させる | **Unit-3 Debate** | Unit-4 Reel（trigger）/ Unit-2 Profile（嗜好ベクトル） |
| **US-01-03** | カレンダー予定を論破材料として差し込む | **Unit-3 Debate** | Unit-6 Calendar（ctx 供給）/ Unit-4 Reel（予定タグ表示） |
| **US-01-04** | 「まだ抵抗」の連打で論破が個別最適化される | **Unit-3 Debate** | Unit-2 Profile（B-08 PreferenceVectorUpdater）/ Unit-8 Dame Report（成約率可視化） |
| **US-01-05** | 3 回連続拒否でクールダウン（セーフガード） | **Unit-3 Debate** | Unit-7 Safeguard（B-09 ルール）/ Unit-2 Profile（負債フラグ） |
| **US-02-01** | 深夜 22 時にコンテキスト連動で高単価リール | **Unit-4 Reel** | Unit-6 Calendar（多忙度 ctx）/ Unit-2 Profile（嗜好ベクトル） |
| **US-02-02** | ダブルタップで Amazon へワンタップ遷移 | **Unit-4 Reel** | Unit-1 Platform（Special Link）/ Unit-7 Safeguard（遷移前チェック） |
| **US-02-03** | 左スワイプで論破モードへ自動遷移 | **Unit-4 Reel** | Unit-3 Debate（遷移先） |
| **US-02-04** | 右スワイプで「後で見る」→ カート監視登録 | **Unit-4 Reel** | Unit-5 Cart（登録先 B-04） |
| **US-02-05** | 「確保しておきました」ラベルで所有感を醸成 | **Unit-4 Reel** | Unit-2 Profile（嗜好ベクトル）/ Unit-6 Calendar（予定タグ連動） |
| **US-03-01** | Amazon Shopping から共有 → ASIN 取込で監視リスト登録 | **Unit-5 Cart** | Unit-1 Platform（S-01 AsinExtractor）/ Unit-4 Reel（B-11 Creators API 共有） |
| **US-03-02** | 30 分 / 6 時間 / 24 時間の 3 段追撃通知 | **Unit-5 Cart** | Unit-1 Platform（End User Messaging Push 基盤） |
| **US-03-03** | クリップボードに Amazon URL → 自動サジェスト | **Unit-5 Cart** | Unit-1 Platform（S-01 AsinExtractor） |
| **US-03-04** | Special Link で Amazon アプリを Deep Link 起動 | **Unit-5 Cart** | Unit-4 Reel（B-10 AssociatesLinkGenerator / B-13 AmazonTransitionRecorder）/ Unit-7 Safeguard |
| **US-03-05** | 月間上限到達時にカート介入を停止（セーフガード） | **Unit-5 Cart** | Unit-7 Safeguard（B-09 ルール）/ Unit-2 Profile（月間上限設定） |

### サポート UC（13 ストーリー、v1.1 追加）

| ストーリー ID | タイトル | 主担当 Unit | 副担当 Units |
|---|---|---|---|
| **US-AUTH-01** | オンボーディングで予算感アンケートを 90 秒で完了する | **Unit-2 Auth & Profile** | Unit-1 Platform（Amplify Auth 基盤）/ Unit-7 Safeguard（予算感 → SafeguardPolicy 連動） |
| **US-AUTH-02** | MFA を設定する | **Unit-2 Auth & Profile** | Unit-1 Platform（Cognito + CloudWatch Alarm） |
| **US-AUTH-03** | 負債自己申告で初期セーフガードが適用される | **Unit-2 Auth & Profile** | Unit-7 Safeguard（B-09 ルール適用） |
| **US-CAL-01** | カレンダー連携をオプトインする | **Unit-6 Calendar** | Unit-1 Platform（プライバシーポリシー表示）/ Unit-2 Profile（同意ログ保存） |
| **US-CAL-02** | プレゼン予定から商品カテゴリを先回り提案する | **Unit-6 Calendar** | Unit-4 Reel（ctx 消費）/ Unit-5 Cart（プッシュ通知） |
| **US-CAL-03** | デート予定の情報を論破材料として AI プロンプトに埋め込む | **Unit-6 Calendar** | Unit-3 Debate（プロンプト合成）/ Unit-4 Reel（ctx 消費） |
| **US-SAFE-01** | 月間 Amazon 遷移上限をスライダーで調整する | **Unit-7 Safeguard** | Unit-2 Profile（`Users.safeguard.monthly_limit_pct` 保存） |
| **US-SAFE-02** | 冷却モードを手動 ON/OFF する | **Unit-7 Safeguard** | Unit-3 Debate / Unit-4 Reel / Unit-5 Cart（全遷移 middleware） |
| **US-SAFE-03** | NG カテゴリを追加・編集する | **Unit-7 Safeguard** | Unit-4 Reel（推薦フィルタ）/ Unit-5 Cart（登録フィルタ） |
| **US-SAFE-04** | アカウント削除と全データエクスポートを実行する | **Unit-7 Safeguard** | Unit-1 Platform（S3 Presigned URL / ログ削除）/ Unit-2 Profile（データ源） |
| **US-REP-01** | 週次「委ね度」レポートを受信する | **Unit-8 Dame Report** | Unit-2 Profile（B-08 PreferenceVectorUpdater 拡張）/ Unit-1 Platform（EventBridge Scheduler + End User Messaging Push） |
| **US-REP-02** | ダメ化ポートフォリオのタグを編集する | **Unit-8 Dame Report** | Unit-2 Profile（嗜好ベクトル再計算）/ Unit-4 Reel（フィードバックループ） |
| **US-REP-03** | Before/After 4 指標で 90 日の変化を閲覧する | **Unit-8 Dame Report** | Unit-2 Profile（オンボアンケート値）/ Unit-1 Platform（インフォグラフィック生成） |

## Unit 別のストーリー配分

| Unit | 主担当ストーリー数 | ストーリー ID |
|---|:---:|---|
| Unit-1 Platform | 0 | （基盤、全ストーリーの前提。副担当として多数に関与） |
| **Unit-2 Auth & Profile** | **3** | US-AUTH-01, US-AUTH-02, US-AUTH-03 |
| **Unit-3 Debate** | **5** | US-01-01, US-01-02, US-01-03, US-01-04, US-01-05 |
| **Unit-4 Reel** | **5** | US-02-01, US-02-02, US-02-03, US-02-04, US-02-05 |
| **Unit-5 Cart Intercept** | **5** | US-03-01, US-03-02, US-03-03, US-03-04, US-03-05 |
| **Unit-6 Calendar** | **3** | US-CAL-01, US-CAL-02, US-CAL-03 |
| **Unit-7 Safeguard** | **4** | US-SAFE-01, US-SAFE-02, US-SAFE-03, US-SAFE-04 |
| **Unit-8 Dame Report** | **3** | US-REP-01, US-REP-02, US-REP-03 |
| **合計（主担当）** | **28** | **カバレッジ 100%** |

**Q7=A「各 Unit に 3〜5 ストーリー」適合状況**: コア 3 Units（Unit-3/4/5）が各 5 ストーリー、サポート 4 Units（Unit-2/6/7/8）が各 3〜4 ストーリー。Unit-1 Platform のみ基盤 Unit としてストーリー未割当（全 Unit の副担当位置づけ）。全 Units がサポーティング役割を持ちつつ、**デモで見せられる独立機能** を必ず 3〜5 本抱える設計。

## ストーリーカバレッジ検証

```
コア UC（15 ストーリー）:
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

サポート UC（13 ストーリー、v1.1 追加）:
[US-AUTH-01] ✅ Unit-2 Auth & Profile（主）
[US-AUTH-02] ✅ Unit-2 Auth & Profile（主）
[US-AUTH-03] ✅ Unit-2 Auth & Profile（主）
[US-CAL-01]  ✅ Unit-6 Calendar（主）
[US-CAL-02]  ✅ Unit-6 Calendar（主）
[US-CAL-03]  ✅ Unit-6 Calendar（主）
[US-SAFE-01] ✅ Unit-7 Safeguard（主）
[US-SAFE-02] ✅ Unit-7 Safeguard（主）
[US-SAFE-03] ✅ Unit-7 Safeguard（主）
[US-SAFE-04] ✅ Unit-7 Safeguard（主）
[US-REP-01]  ✅ Unit-8 Dame Report（主）
[US-REP-02]  ✅ Unit-8 Dame Report（主）
[US-REP-03]  ✅ Unit-8 Dame Report（主）
```

**カバレッジ: 28/28 = 100%** ✅

## Unit 完成とストーリー Done の関係

各 Unit の完成判定は、主担当ストーリーの受入条件（GIVEN/WHEN/THEN + ダメ化シグナル）がすべて満たされることで定義する。

### Unit-3 Debate の完成条件（例）

- [ ] US-01-01 のすべての AC-1〜4 がパス（カート停滞通知 → 300ms 初回トークン → Amazon 遷移）
- [ ] US-01-02 のすべての AC-1〜4 がパス（事実→心理の 2 軸切替）
- [ ] US-01-03 のすべての AC-1〜4 がパス（カレンダー予定ベース論破）
- [ ] US-01-04 のすべての AC-1〜4 がパス（個別最適化 + 90 秒タイマー）
- [ ] US-01-05 のすべての AC-1〜4 がパス（クールダウン + 非ターゲット保護）

### Unit-7 Safeguard の完成条件（例、v1.1 追加）

- [ ] US-SAFE-01 のすべての AC-1〜4 がパス（月間上限スライダー + 逆方向クーリングオフ）
- [ ] US-SAFE-02 のすべての AC-1〜4 がパス（冷却モード ON/OFF + 早期解除摩擦）
- [ ] US-SAFE-03 のすべての AC-1〜4 がパス（NG カテゴリ編集 + 警告）
- [ ] US-SAFE-04 のすべての AC-1〜5 がパス（データエクスポート + 物理削除 + grace period）

同様に Unit-2/4/5/6/8 も主担当ストーリーで判定。

## 副担当の責任範囲

副担当 Unit は「主担当 Unit が呼び出すインターフェースや提供する機能」を責任持って提供する:

- **Unit-3 が Unit-5 から呼び出される**（US-01-01）→ Unit-3 の API が Unit-5 のトリガーに応答できる
- **Unit-6 が Unit-3/4 に ctx 供給**（US-01-03, US-CAL-02, US-CAL-03）→ Unit-6 の API が Unit-3/4 の呼び出しに応答できる
- **Unit-7 が Unit-3/4/5 に middleware 挿入**（US-01-05, US-SAFE-02, US-SAFE-03, US-03-04）→ Unit-7 の Authorizer が API Gateway に登録済み
- **Unit-2 が Unit-7/8 にプロファイルデータ供給**（US-SAFE-01, US-REP-01 他）→ Unit-2 の `Users` テーブル API が公開済み

副担当側の Unit が未完成でも、主担当は **スタブ** を使って先行実装可能（Q6=A OpenAPI 凍結の恩恵）。

## 非ターゲットペルソナの扱い

- **田中 一郎（FIRE 志向）**: US-01-05 で Unit-3 のクールダウン発動 → Unit-7 が早期撤退ポリシー適用
- **山田 健二（借金保有者）**: US-AUTH-03 で Unit-2 オンボ時の負債フラグ → Unit-7 が初期から冷却モード ON、US-03-05 で月間上限到達ブロック

両者とも **Unit-2 Auth & Profile + Unit-7 Safeguard の重要な検証ケース**。両 Unit の PBT で明示的に扱う。

## Extension 適合のストーリーマッピング

ストーリー受入条件内の Extension 要件（SECURITY / PBT）は、主担当 Unit の Functional Design（per-unit）で具体化する。

| Extension ルール | 主な該当ストーリー | 担当 Unit |
|---|---|---|
| SECURITY-05（入力検証）| US-03-01（ASIN 抽出）/ US-01-01（カート停滞判定）/ US-AUTH-01（オンボ入力検証）| Unit-5 / Unit-3 / Unit-2 |
| SECURITY-08（認可）| US-02-02, US-03-04（Amazon 遷移前）| Unit-4 / Unit-5 / Unit-7 |
| SECURITY-11（セキュアデザイン）| US-SAFE-01/02/03（SafeguardPolicy 分離）/ US-SAFE-04（物理削除）| Unit-7 |
| SECURITY-12（認証）| US-AUTH-02（MFA）| Unit-2 |
| SECURITY-14（アラート・監査ログ）| US-AUTH-02（認証失敗 lockout）/ US-SAFE-04（削除監査）| Unit-2 / Unit-7 |
| PBT-02（round-trip）| US-03-01（ASIN 抽出/復元）| Unit-1（Shared S-01） |
| PBT-03（invariant）| US-03-05（月間上限超過で block）/ US-SAFE-01（上限スライダー範囲）| Unit-7 |
| PBT-04（idempotency）| US-AUTH-01（オンボ再開）/ US-REP-01（週次ジョブ）| Unit-2 / Unit-8 |
| PBT-06（stateful）| US-03-02（30m→6h→24h→購入/破棄）/ US-SAFE-02（冷却 ON/OFF/早期解除）| Unit-5 / Unit-7 |
| PBT-07（ドメインジェネレータ）| US-CAL-02/03（予定カテゴリ分類入力）| Unit-6 |

---

## Summary

- ✅ 全 28 ストーリー（コア 15 + サポート 13）を 7 つの Unit に **3〜5 本ずつ** 配分、Unit-1 Platform 以外は全 Unit が主担当ストーリーを持つ
- ✅ 各ストーリーに副担当 Unit を明示、Unit 間の連動責任が明確
- ✅ 非ターゲットペルソナの扱いを Unit-2 Auth & Profile + Unit-7 Safeguard に集約
- ✅ ストーリー受入条件の Extension 適合を Unit に紐付け、Functional Design に引き継ぐ
