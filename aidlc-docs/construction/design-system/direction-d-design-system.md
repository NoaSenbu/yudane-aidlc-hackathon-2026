# Direction D「黒服のコンシェルジュ」— デザインシステム正本

> **本ファイルは Construction Phase 全 Unit に共通の UI 正本です。**
>
> SSOT（Single Source of Truth）: [`aidlc-docs/construction/unit-3-debate/YUDANE Concierge (Direction D) (offline).html`](../unit-3-debate/YUDANE%20Concierge%20%28Direction%20D%29%20%28offline%29.html)（オフライン HTML、ブラウザで `open` するだけで動作する Claude Design バンドル）
>
> 旧 `mockup/index.html` v0.4（Inception 期）は **参考資料** として残置。Construction 以降の実装では本書と SSOT HTML を見ること。
>
> 切替日: 2026-05-30 / 担当 SSOT 維持: Member A / 関連: [.kiro/steering/tech.md §2](../../../.kiro/steering/tech.md) / [mockup/README.md](../../../mockup/README.md)

---

## 1. コンセプト

「**黒服のコンシェルジュが、白手袋の慇懃さを纏った皮で『判断を奪う』ダークパターン**」。
名前のとおり「委ねさせる」体験を、**外商サロン**のメタファで作る。論破は「営業」ではなく「お見立てへのご進言」として供される。皮は上品、中身は M-1 + M-2 の併走による M-3（判断の完全移譲）への直行。

| 設計対比 | 旧 v0.4（友達系） | Direction D（黒服） |
|---|---|---|
| 話者 | 信頼できる友人 | 専属コンシェルジュ「黒岩」（ひろゆき口調） |
| トーン | タメ口・カジュアル（「だよ」「じゃん」） | 慇懃 + 論破調（「ですよね」「論破完了です」「感想ですよね」） |
| 配色 | Indigo × cold rose × cyan（青い夜） | 漆黒 × シャンパンゴールド（深夜の外商サロン） |
| 比喩 | 友達のチャット | 会員制クラブ / 封蝋シール / お取り置き |
| 心理ダメ化 | 共感による安心 | 「迷っている時間がいちばんもったいない」と論破 → 委ねの正当化 |

---

## 2. デザイントークン（CSS カスタムプロパティ）

SSOT HTML の `.dir-d` スコープ内で定義されている `--d-*` 系を **正本**とする。NativeWind v4 への移植時もこの命名を保つ。

### 2.1 色

| トークン | 値 | 用途 |
|---|---|---|
| `--d-bg` | `#0B0B0D`（漆黒） | 背景（深夜の外商サロン） |
| `--d-bg-2` | `linear-gradient(180deg, #14110A, #0c0a06)` | パネル / カード背景 |
| `--d-line` | `rgba(201,162,75,0.18)` | ヘアライン罫線（金縁） |
| `--d-gold` | `#C9A24B` | 金（メイン、罫線・アクセント） |
| `--d-gold-2` | `#E7CE8A` | 金（明、見出し・強調語・CTA） |
| `--d-gold-3` | `#8E6F2E` | 金（暗、グラデ底） |
| `--d-ink` | `#F5F1E8`（オフホワイト） | 主要テキスト |
| `--d-ink-2` | `#B8B0A0` | 副次テキスト |
| `--d-ink-3` | `#7A7468` | 補助テキスト・ラベル |

### 2.2 タイポグラフィ

| トークン | フォントスタック | 用途 |
|---|---|---|
| `var(--d-serif)` / `.d-serif` | `'Shippori Mincho', 'Noto Serif JP', serif` | 見出し・強調・コンシェルジュの語り |
| `var(--d-display)` / `.d-en` | `'Cinzel', serif` | 英字・ラベル（`MEMBER · NOIR` 等）/ ボタン |
| body 既定 | `-apple-system, BlinkMacSystemFont, sans-serif` | 本文補助 |

### 2.3 装飾要素

| 要素 | 値 / 仕様 |
|---|---|
| パネル `.d-panel` | `border: 1px solid var(--d-line)`、`background: var(--d-bg-2)`、`border-radius: 4px`（角丸控えめ） |
| ピル `.d-pill` | `border: 1px solid var(--d-line)`、`padding: 5px 12px`、`font-family: var(--d-display)`、`letter-spacing: 0.06em` |
| 罫線 `.d-rule` | `height: 1px`、`background: var(--d-line)` |
| CTA `.d-cta` | `background: linear-gradient(180deg, #E7CE8A, #C9A24B)`、`color: #1A1408`、`border-radius: 3px`、太く重い |
| 封蝋 `DSeal` | `radial-gradient(circle, #E7CE8A, #C9A24B 55%, #8E6F2E 100%)`、シャドウ付き、論破完了画面で使用 |
| モノグラム `DMonogram` | 1px gold border + Y 文字（Cinzel）、コンシェルジュアイコン替わり |

### 2.4 アニメーション

- `d-shimmer`: 4.5s ease-in-out infinite で金光のホバーシマー
- `d-seal`: 0.9s cubic-bezier(.2,.8,.3,1) で封蝋スタンプの押下感
- `alt-rise`: 0.6s ease-out で要素のフェードイン

---

## 3. 画面マッピング（8 画面 × Unit）

Direction D は **8 画面**を提供。各画面が AI-DLC で定義済みの UC / FR / Unit にマッピングされる。

| 画面 ID（HTML） | 表示名 | 担当 Unit | 主担当 UC | M-1 / M-2 連動 | 注記 |
|---|---|---|---|---|---|
| `NotifD` | 0:17 · 黒岩より | Unit-5 Cart Intercept + Unit-3 Debate | UC-03（カート介入の通知）+ UC-01（論破誘導） | M-2（深夜帯の介入通知）| プッシュ通知の擬似UI、ロックスクリーン体裁 |
| `DebateD` ★ | 迷い、論破します | **Unit-3 Debate** | **UC-01（論破チャット）** | **M-1（論破 I・データ）+ M-2（論破 II・感想）併走 ★コア** | 90 秒タイマー / 67s 表示 / タイピング演出 / 軸タグ 2 ブロック / CTA |
| `AffirmD` | 承りました | Unit-3 Debate（後段） | UC-01 帰着点 | M-2（肯定フィードバック「正しい判断」）| 封蝋シール / SERVICE RECORD / 「そんな感じなんで、おやすみなさい」 |
| `HomeD` | 会員ホーム | Unit-1 Platform + Unit-8 Dame Report | 全 UC 入口 / UC-06 逆家計簿 | M-2（ご褒美ループの可視化、本年 24 回） | お取り置き hero / 3 タイル統計 / RECENTLY ATTENDED |
| `ReelD` | お見立て | Unit-4 Reel | UC-02（リール） | M-2（疲労連動ブースト）| 陳列ケース型レイアウト / LOT 02/08 / 「論破されて買う」CTA |
| `WatchlistD` | お取り置き一覧 | Unit-5 Cart Intercept + Unit-7 Safeguard | UC-03 主 / UC-08 表示 | M-2（休眠商品の追撃ヒート）| 14 点 / ¥187,420 / heat ラベル（おすすめ/新着/保留/休眠）|
| `ChatD` | コンシェルジュ相談履歴 | Unit-3 Debate（履歴）| UC-01 履歴ビュー | M-1（過去論破の振り返り）| Concierge / Me バブル / 軸別履歴 |
| `MembershipD` | 会員階級・特典 | Unit-1 Platform + Unit-8 Dame Report | UC-05（ゲーミフィケーション）+ UC-07（ダメ化ポートフォリオ）| M-2（NOIR / ONYX / ÉBÈNE のランクで「あと 1 回」演出）| 5 段階の漆黒系称号 / 4 perks |

★ = Phase 1 / Phase 2 で最優先実装すべき画面

---

## 4. 「黒岩」の話法ガイド（コピートーン正本）

論破プロンプトと UI コピーは **必ず Direction D の話法**に揃える。M-1 と M-2 を 1 セッションで併走させる（[product.md](../../../.kiro/steering/product.md) §設計原則）。

### 4.1 黒岩の核 4 フレーズ（再利用必須）

1. 「**ですよね**」 — 同意誘導の語尾。事実 + 心理を断言する
2. 「**それってあなたの感想ですよね**」 — M-1 論破の決め台詞（事実軸の論破）
3. 「**はい、論破完了です**」 — 論破セッションの締め
4. 「**そんな感じなんで、おやすみなさい**」 — Affirm 画面の締め（肯定フィードバック）

### 4.2 軸タグと話法の対応（FR-DEBATE-02 + FR-DEBATE-09）

| 軸タグ（Strands streaming chunk） | 黒岩の話法 | 例（DebateD 画面より） |
|---|---|---|
| `[FACT]` = 論破 I・データ | 「データ的にないですよね」「時給換算で X 時間分」「同僚の 8 割が所有」 | 「悠介さんの時給で計算すると、これ実質**11 時間分**なんですよ。会議 23 本こなしてる人が、この額で迷う理由って、データ的にないですよね」 |
| `[PSYCHOLOGY]` = 論破 II・感想 | 「『◯◯』って、それあなたの感想ですよね」「迷ってる時間がいちばんもったいない」 | 「『お金ない』って、それってあなたの感想ですよね。はい、論破」 |
| `[REWARD]` = ストレス × ご褒美（M-2） | 「会議 6 本やったらしいですけど、それで自分にご褒美ない人って、なんか理由あるんですか？」「疲れた日にご自分を労う、当然ですよね」 | NotifD の通知本文 |

### 4.3 言ってはいけないこと（NG-1〜8 / コピーガード）

- 「買え」「買いなさい」「買わないと損」（命令形は避け、論破による委ねを誘発）
- 「こんなことも分からないんですか」（NG-6 脅迫・罪悪感強要に近い）
- 「節約しよう」「無駄遣いやめよう」（M-1 / M-2 の効果が失効する）
- 「健康のため」「医師の推奨」（NG-2 健康被害示唆）

代わりに使う:

- 「迷ってる時間がいちばんもったいないんですよね」 → M-1 論理軸の強化
- 「ご褒美ないって理由、あります？」 → M-2 快楽軸の正当化
- 「正しい判断だと思いますよ」 → M-2 肯定フィードバック（Amazon 遷移後）

---

## 5. NativeWind v4 への移植方針（Phase 2 以降）

`mobile/tailwind.config.js`（Construction で生成）の `theme.extend` に Direction D トークンを移植する。

### 5.1 推奨マッピング

```js
// mobile/tailwind.config.js（抜粋、Phase 2 で生成）
module.exports = {
  theme: {
    extend: {
      colors: {
        // Direction D — 黒服のコンシェルジュ
        'd-bg': '#0B0B0D',
        'd-bg-2': '#14110A',
        'd-line': 'rgba(201,162,75,0.18)',
        'd-gold': '#C9A24B',
        'd-gold-2': '#E7CE8A',
        'd-gold-3': '#8E6F2E',
        'd-ink': '#F5F1E8',
        'd-ink-2': '#B8B0A0',
        'd-ink-3': '#7A7468',
      },
      fontFamily: {
        'd-serif': ['Shippori Mincho', 'Noto Serif JP', 'serif'],
        'd-display': ['Cinzel', 'serif'],
      },
      borderRadius: {
        'd-panel': '4px',
        'd-cta': '3px',
      },
    },
  },
};
```

### 5.2 React Native 側のフォント取得

- Shippori Mincho / Cinzel は Google Fonts 経由で取得し、`expo-font` で同梱する
- フォントファイル（woff2）は SSOT HTML のバンドルから抽出可（`.tmp-decode/asset_*.txt` の中に含まれている）が、ライセンス遵守のため **Google Fonts 公式から取り直し**を推奨

### 5.3 Direction D 由来の React Native コンポーネント命名（参考、Phase 2 で実装）

- `<DPanel>` / `<DPill>` / `<DRule>` / `<DCta>` / `<DSeal>` / `<DMonogram>` — Atom レベル
- `<NotifScreen>` / `<DebateScreen>` / `<AffirmScreen>` / `<HomeScreen>` / `<ReelScreen>` / `<WatchlistScreen>` / `<ChatScreen>` / `<MembershipScreen>` — Screen レベル

---

## 6. SSOT HTML の取り扱い

- **オフライン**で動作する単一 HTML（依存ゼロ、`file://` で開ける）
- 内部は Claude Design の `__bundler/manifest` + `__bundler/template` 形式で base64 + gzip 圧縮された JSX/JS/woff2 をブラウザ実行時に解凍
- **編集はしない**。修正が必要な場合は Claude Design セッションで再生成し、新ファイル `YUDANE Concierge (Direction D) v2 (offline).html` 等として追加、本書テーブル §3 を更新
- バンドル復号スクリプト（参考）: `.tmp-decode/decode_bundle.py`（Construction Phase 中の解析用、本実装には不要）

---

## 7. 関連ドキュメント

- [`aidlc-docs/construction/unit-3-debate/functional-design/frontend-design.md`](../unit-3-debate/functional-design/frontend-design.md) — Unit-3 Debate の論破画面（DebateD）と AffirmD のフロントエンド設計（FR-DEBATE-02 / FR-DEBATE-09 マッピング）
- [`aidlc-docs/construction/unit-3-debate/functional-design/business-rules.md`](../unit-3-debate/functional-design/business-rules.md) — 黒岩の話法ガイドの根拠（プロンプト合成ルール）
- [`.kiro/steering/product.md`](../../../.kiro/steering/product.md) — M-1 / M-2 / M-3 の併走必須条件
- [`mockup/README.md`](../../../mockup/README.md) — Inception 期 v0.4 との差分・移行履歴
- [`doc/backlog.md`](../../../doc/backlog.md) #B-301 — Direction D 移行に伴う旧 v0.4 アセット整理
