# モックアップ検証フェーズ — 計画と位置付け

> **作成日**: 2026-05-10
> **ステータス**: Inception 仕上げラウンドで正式化
> **位置付け**: AI-DLC 公式にない **Inception の補助ステージ**（公式ワークフローは上書きしない）

---

## 1. なぜこのフェーズを追加したか

### 1.1 現状の問題

AI-DLC 公式 Inception は **Requirements → User Stories → Application Design → Units Generation** の 4 段で完結する。要件の文字化には強いが、UX と視覚トーンの妥当性検証がフェーズとして存在しない。

YUDANE のコア体験（論破・カート介入・リール）は **「2〜3 タップで Amazon 遷移」** の UX 成立が要件書の設計前提になっている。この前提が実体として成立するかを文書だけで証明するのは困難。

### 1.2 採用した解決策

`mockup/` 配下に存在する **静的 HTML モックアップ 6 画面** を、単なるビジュアル補助ではなく **「仮説検証の証跡」** として昇格させる。Inception の 5 番目の成果物群として aidlc-docs 配下に文書化する。

### 1.3 既存ワークフローとの関係

| 項目 | 方針 |
|---|---|
| AI-DLC 公式ステージの上書き | **行わない**（Workspace Detection〜Units Generation は既承認済） |
| Construction フェーズへの影響 | **なし**（本フェーズの成果物は Construction で参照されるのみ、前提を変更しない） |
| Extension（Security / PBT）との関係 | モックアップは静的 HTML のため Extension 対象外。実装時に全面適用 |
| 位置付け | Inception の補助成果物として、モックアップに埋め込まれた設計判断を文書化する |

---

## 2. 本フェーズの成果物

本ディレクトリ `aidlc-docs/inception/mockup-validation/` 配下に 6 ファイルを配置する。

| # | ファイル | 検証する仮説 |
|---|---|---|
| 1 | `mockup-plan.md`（本書）| なぜモックアップを検証フェーズに昇格させたか |
| 2 | [`screen-hypothesis-map.md`](./screen-hypothesis-map.md) | 6 画面それぞれが検証する UX 仮説と判定 |
| 3 | [`dark-copy-inventory.md`](./dark-copy-inventory.md) | 論破コピーに埋め込まれた心理学的メカニズムと倫理境界との距離 |
| 4 | [`color-rationale.md`](./color-rationale.md) | Indigo / Cold Rose / Cyan を採用した設計判断 |
| 5 | [`3-tap-timeline.md`](./3-tap-timeline.md) | 「通知受信 → Amazon 遷移」を 3 タップ 3 分以内で達成できるか |
| 6 | [`mockup-to-uc-traceability.md`](./mockup-to-uc-traceability.md) | 6 画面が UC-01〜08 / FR / Story に 1:1 対応していることのトレース表 |

---

## 3. モックアップ自体の構成（参照）

`mockup/` 配下の静的 HTML は以下で構成される。

```
mockup/
├── index.html           # 6 画面構成のスマホ型 HTML
├── styles.css           # Indigo × Cold Rose × Cyan デザインシステム
├── app.js               # タブ遷移・リール・論破チャット・Amazon 遷移オーバーレイ
├── README.md            # モックアップ自体の使い方
└── assets/
    ├── brand/logo.svg
    └── products/*.svg（earbuds / book / desk-lamp / whisky）
```

ビルド不要、ブラウザで `mockup/index.html` を開くだけで全 6 画面を操作できる。

---

## 4. 検証対象の 6 画面

| # | 画面 | 対応 UC | モックアップ収録機能 |
|---|---|---|---|
| 1 | ホーム | UC-03 主 + UC-04 先回り + UC-06 弾薬 | Hero / カート監視リスト / 予定から先回りカード / サブダッシュボード |
| 2 | カート介入 | UC-03 | Share Sheet 擬似到着 / 商品取込カード / 追撃スケジュール 30m/6h/24h |
| 3 | リール | UC-02 | 縦型スワイプ 3 商品 / 🛍 Amazon で買うボタン |
| 4 | 論破チャット | UC-01 | タイピング演出 / 事実・心理ラベル / 90 秒タイマー |
| 5 | ダメ化レポート | UC-05/06/07 | 委ね Lv. / Before-After 指標 / 行動変容ナラティブ |
| 6 | セーフガード | UC-08 | 月間上限 / 冷却モード / NG カテゴリ |

---

## 5. 位置付けのまとめ

本フェーズの 6 ファイルは、いずれも **モックアップに埋め込まれた設計判断を文書として外在化する** ことを目的とする。

- [`3-tap-timeline.md`](./3-tap-timeline.md) で「悠介の金曜深夜」体験シーンの実時間検証を行い、Year 1 退化年表の起点が成立することを示す
- [`mockup-to-uc-traceability.md`](./mockup-to-uc-traceability.md) で画面 × UC × FR × Story × Unit の対応関係を示し、要件とモックアップの整合性を立証する
- [`dark-copy-inventory.md`](./dark-copy-inventory.md) で論破コピーの心理学メカニズムを分解し、[`color-rationale.md`](./color-rationale.md) で配色の設計意図を記述する
- [`screen-hypothesis-map.md`](./screen-hypothesis-map.md) で各画面が検証する仮説と現時点判定を残し、実装時の参照点とする

---

## 6. 本フェーズの完了条件

- [ ] 本計画書（`mockup-plan.md`）が作成されている
- [ ] `screen-hypothesis-map.md` で 6 画面すべてに仮説・判定が付与されている
- [ ] `dark-copy-inventory.md` でモックアップに実在する 39 件の論破コピーが心理学分類されている
- [ ] `color-rationale.md` で 3 色の採用根拠と不採用色の対比が記述されている
- [ ] `3-tap-timeline.md` で「悠介の金曜深夜」シーン（23:47〜00:20）が実時間検証されている
- [ ] `mockup-to-uc-traceability.md` で 6 画面 × 8 UC × FR × Story のマトリクスが完成している
- [ ] 全ファイルに Markdown 文法エラー・リンク切れがない

---

## 7. 参照ドキュメント

- [要件書 v0.8](../requirements/requirements.md)
- [ペルソナ](../user-stories/personas.md)
- [退化年表](../user-stories/persona-journey.md)
- [Unit of Work](../application-design/unit-of-work.md)
- [NG シナリオ集](../requirements/ng-scenarios.md)
- [市場ポジショニング](../requirements/market-positioning.md)
