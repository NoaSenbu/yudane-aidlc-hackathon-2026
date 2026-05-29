# Unit-1 Platform — NFR Requirements Clarification

> NFR Requirements の Q3 について、これまでの確定設計との矛盾が検出されたため確認する。
> 確定済み: Q1=A / Q2=A / Q4=A / Q5=A / Q6=B / Q7=A
> 作成: 2026-05-29

---

## 矛盾 1: カスタムメトリクス土台（元 Q3=C）

**あなたの回答**: Q3=C「メトリクスは CloudWatch 標準メトリクスのみ使い、カスタムメトリクス土台は最小限」

**検出された矛盾**:

| # | 矛盾先 | 内容 |
|---|---|---|
| 1 | 要件書 §6.1 北極星指標 | 「論破→Amazon 遷移率 35%+」「通知開封率 45%+」「深夜帯利用比率 30%+」等はアプリ固有のビジネスイベントで、CloudWatch 標準メトリクス（Lambda 実行回数 / エラー率等）からは算出不能 |
| 2 | services.md「北極星指標の集計経路」 | B-12 `metric()` と B-14 が **EMF 形式でカスタムメトリクス出力** → B-08 が週次集計 → Unit-8 ダメ化レポート表示、と確定済み。土台を最小化すると Unit-8 と週次集計が動かない |
| 3 | Unit-1 Functional Design（承認済み） | domain-entities.md で `MetricDatum`（EMF カスタムメトリクス）を定義、business-logic-model.md ALG-LOG で `metric()` を設計済み |

**推測される意図**: 「Unit-1 が他 Unit のメトリクスまで先回りで全部定義しすぎないようにしたい（各 Unit が自分のメトリクスを定義すべき）」という懸念ではないか。これは妥当で、推奨案 A よりむしろ B に近い。

### Clarification Question 1
Unit-1 のカスタムメトリクス土台の扱いをどうしますか？

A) **元の A（フル）**: Unit-1 が必須メトリクスカタログ雛形（api_latency / api_error_rate / cold_start_ms / safeguard_decision / cache_hit_rate）まで提供 + オーバーヘッド上限規定
B) **B（土台のみ、推奨）**: Unit-1 は「EMF 出力ライブラリ（B-12 metric / B-14）+ オーバーヘッド上限 + メトリクス命名規約」だけ提供し、**具体的なメトリクス名カタログは各 Unit が S-04 に追記**。北極星指標の集計経路（services.md）は維持される。Unit-1 の責務を絞りつつ矛盾を解消
C) **元の C を維持**: カスタムメトリクス土台を持たず CloudWatch 標準メトリクスのみ（→ この場合、北極星指標の計測方法・Unit-8 ダメ化レポートの集計方法を別途再設計する必要があり、要件書 §6.1 / services.md の改訂を伴う。影響大）
X) Other（[Answer]: の後に記述）

[Answer]: 

---

## 補足: 各選択肢の影響

- **B（推奨）**: あなたの「Unit-1 が定義しすぎない」意図を満たしつつ、北極星指標・Unit-8・Functional Design との整合を保つ。Unit-1 の作業は EMF 出力土台 + 命名規約 + オーバーヘッド上限に限定され軽くなる
- **C**: 要件書 §6.1（北極星指標）と services.md（集計経路）の改訂が必要になり、ハッカソン評価の核（テーマのダメ化可視化 = Unit-8 ダメ化レポート）に影響する。選ぶ場合は影響範囲の再設計を別途実施
