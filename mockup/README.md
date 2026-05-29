# YUDANE — Mockup v0.4

「買わない理由を論破する AI エージェント・コマース」のビジュアル仮説検証用モックアップ。

> ⚠️ これは UI 仮説を伝えるためのモックアップで、実アプリではありません。React Native + AWS SDK v3 本実装の前段として、画面フロー・コピー・視覚トーンの合意形成に使います。

## 起動方法

ビルド不要。ブラウザで直接開けます。

```
open mockup/index.html     # macOS
xdg-open mockup/index.html # Linux
start mockup/index.html    # Windows
```

あるいは静的サーバ経由:

```
python3 -m http.server -d mockup 8080
# http://localhost:8080
```

## ディレクトリ構成

```
mockup/
├── README.md              # このファイル
├── index.html             # 6 画面構成のスマホ型モックアップ
├── styles.css             # デザインシステム（Indigo × cold rose × cyan）
├── app.js                 # タブ遷移・リール・論破チャット・Amazon 遷移オーバーレイ
└── assets/
    ├── brand/
    │   └── logo.svg       # YUDANE ロゴマーク
    └── products/
        ├── earbuds.svg    # Sony WF-1000XM5（リール / カート介入）
        ├── book.svg       # 『欲望の資本主義』（カート監視）
        ├── desk-lamp.svg  # FLOS Tokio（リール）
        └── whisky.svg     # 山崎 18 年（リール）
```

## 画面構成（v0.4）

| # | 画面 | UC | 主な要素 |
|---|---|---|---|
| 1 | ホーム | UC-03 主 + UC-04 先回り + UC-06 弾薬 | AI エージェント稼働 hero / カート監視リスト / **予定から先回りカード（新設）** / サブダッシュボード |
| 2 | カート介入 | UC-03 | Share Sheet 擬似到着 / 商品取込カード / 追撃スケジュール 3 段 |
| 3 | リール | UC-02 | 縦型スワイプ 3 商品 / **「🛍 Amazon で買う」ボタン** |
| 4 | 論破チャット | UC-01 | タイピング演出 / 事実ベース・心理ベースのラベル / 90 秒タイマー / **友達系コピー** |
| 5 | ダメ化レポート | §2.5 アーク可視化 | 委ね Lv. / Before-After 4 指標 / 行動変容ナラティブ / サイン入り引用 |
| 6 | セーフガード | UC-08 | 月間上限 / 冷却モード / 静かな週 / NG カテゴリ / データ削除 |

## インタラクション

- 左下タブで画面切替（6 タブ）
- ホームのカート監視リストをタップ → カート介入画面へ
- ホームの「📅 予定から先回り」カードをタップ → リールへ
- ホームの CTA「リール見に行く」→ リールへ
- リール「買わない」→ 自動で論破モーダルへ
- リール商品をダブルタップ or 「🛍 Amazon で買う」タップ → Amazon 遷移確認オーバーレイ
- オーバーレイ「🛍 Amazon で買う」→ トースト `Amazon に送ったよ — 委ね度 +1` → 1.2 秒後にダメ化レポートへ自動遷移
- 論破チャットで「納得した」→ ダメ化レポートへ、「まだ抵抗する」→ 反論追加
- セーフガードの上限スライダー・トグルが動く

## v0.4 での主な変更

- **決済はアプリ内で完結しない方針に変更**:
  - Face ID 風決済オーバーレイを廃止、「🛍 Amazon で買う」の Amazon 遷移確認オーバーレイに置換
  - リールの決済ボタンを「💳 即決済」から「🛍 Amazon で買う」に変更
  - 決済は Amazon 側で完結する前提（YUDANE は Associates Special Link でユーザーを Amazon にバトンタッチする）
- **カレンダー連動カード新設**（UC-04 / FR-CAL）: ホームに「📅 予定から先回り」カードを追加。プレゼン・記念日ディナー等の予定から事前提案する UX を可視化
- **コピートーンを友達系に統一**: 敬語（〜です / 〜ます）をタメ口（〜だよ / 〜じゃん）に書換え。「信頼できる友人が論破してくる」構図
- **ダメ化レポートの指標更新**: 「Face ID 反射速度」→ 「Amazon 遷移の決断速度」（アプリ内 Face ID 決済を廃止した整合）
- **ピッチパネル更新**: モバイル必然性の 5 項目のうち「👤 Face ID 決済」→ 「👤 ワンタップ Amazon」

## 意図的に未実装

- 実 Amazon Creators API 連携（書類審査・予選はモックデータで要件充足）
- 本物の Share Extension（iOS/Android ネイティブ側実装が必要）
- Amazon Associates の本物の Special Link（Approved Mobile Application 承認後に組込、§8 A-10）
- Face ID / Touch ID の実機能（そもそも決済はアプリ内にないので不要）
- HealthKit / TOTP MFA / APNs

これらは React Native + AWS SDK v3 本実装で対応します（Amplify は不採用）。

## 要件書との対応

- プロダクト定義: `aidlc-docs/inception/requirements/requirements.md` (v0.3)
- 主な対応: UC-01〜04 のコア UC、FR-DEBATE / FR-REEL / FR-CART / FR-CAL / FR-FUNNEL、Degradation Arc、Before/After、収益モデル（Amazon Associates）
- 倫理ライン §9 NG-8 — オーバーレイの注記に「YUDANE は紹介だけ（Associates）」を明示
- モックアップは要件書の §5 を逸脱しないことを原則とする


## デザインツール: Claude Design（SSOT）

本モックアップは **Claude Design**（Anthropic Labs、2026-04-17 リリース）を SSOT デザインツールとして採用する。Figma / Sketch / Adobe XD は採用しない。詳細決定の経緯は [parallel-dev-prerequisites.md §N-1](../aidlc-docs/construction/plans/parallel-dev-prerequisites.md) と [.kiro/steering/tech.md §2 デザインツール行](../.kiro/steering/tech.md) を参照。

### 運用ルール

- **SSOT**: 本ディレクトリ配下（`mockup/index.html` ほか）に Claude Design からエクスポートした HTML / CSS / JS を反映する
- **デザイントークン**: 色 / フォント / スペーシング等のトークンは NativeWind v4 の `mobile/tailwind.config.js`（Construction Phase で生成）を一次の真実とする。Claude Design 出力で発生したトークン揺れは Member A が PR で吸収する
- **モックアップ HEX → Tailwind トークン**: `mockup/styles.css` の HEX 値（Indigo `#4F4DDC` / cold rose `#E8B4D0` / cyan `#4DE1FF` 他）を `tailwind.config.js` の `theme.extend.colors` にミラーリング（Member A が Unit-1 Platform で実施）
- **担当**: Member A が Claude Design アカウント（Pro 以上）を保有。新規画面 / 改良依頼は Member A 経由でリクエスト
- **採用しない**: Figma / Sketch / Adobe XD（二重管理を避ける）

### バージョン管理: Claude Design セッション履歴

Claude Design で生成 / 改良した画面は、再現性確保のため以下を記録する:

| 画面 | Claude Design セッション URL | 主要プロンプト要約 | 反映コミット |
|---|---|---|---|
| ホーム v0.4 | （セッション URL） | （プロンプト要約） | （commit hash） |
| カート介入 v0.4 | （セッション URL） | （プロンプト要約） | （commit hash） |
| リール v0.4 | （セッション URL） | （プロンプト要約） | （commit hash） |
| 論破チャット v0.4 | （セッション URL） | （プロンプト要約） | （commit hash） |
| ダメ化レポート v0.4 | （セッション URL） | （プロンプト要約） | （commit hash） |
| セーフガード v0.4 | （セッション URL） | （プロンプト要約） | （commit hash） |

> 各セッション URL は Claude Pro ユーザーのみアクセス可能。チーム外への共有は Anthropic 利用規約に従う。
> v0.4 までは Claude Design 不採用時代の手書き HTML のため、セッション URL は空欄でよい。**v0.5 以降の更新で Claude Design を使った場合に必須記録**。

### 既存資産の扱い（v0.4 → v0.5 移行時）

- v0.4 までの `mockup/` 配下の HTML / CSS / JS は Claude Design 不採用時代の手書きアセット
- v0.5 以降は Claude Design 経由で新規生成 / 改良するが、現存の v0.4 資産を破壊せず incremental に更新する
- Claude Design の出力が NativeWind v4 のトークンと整合しない場合は Member A が PR で吸収

