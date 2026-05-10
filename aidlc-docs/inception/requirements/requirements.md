# 要件定義書 — プロジェクト「YUDANE（委ね）」

> プロダクト: 買わない理由を論破する、AI エージェント・コマース  
> スコープ: AWS Summit Japan 2026 AI-DLC Hackathon テーマ「人をダメにするサービスを考えよう！」への応募作品として設計  
> ステージ: 🔵 INCEPTION / Requirements Analysis  
> バージョン: v0.6

---

## 0. エグゼクティブサマリー

**YUDANE は、「買わない理由」を論破する AI エージェント・コマース。**

ユーザーが Amazon のカートに商品を入れたまま迷っている瞬間、あるいはベッドでネットショッピングに手を止めた瞬間に、AI が狙いを定める。ユーザーの嗜好・カレンダー予定・コンテキストを学習したエージェントが、事実と心理の両面から「なぜあなたに今それが必要か」を 10 秒で論破し、**「🛍 Amazon で買う」**ボタンでワンタップで Amazon へ送り出す。決済は Amazon 側で完結する（YUDANE は決済を持たない）。逆・家計簿ダッシュボードも備えるが、それは独立した目的ではなく **論破モーダルで AI が参照する弾薬** として設計されている。

**誰を・どう・なぜダメにするか**:  
過労気味のリモートワーカーが、「欲しいかも」と「買うか迷う」の間にあった **自分で決める間（ま）** を失い、迷うたびに AI に翻意させられる身体へと退化していく。

**最終的な到達地点**:  
3 か月後、悠介は Amazon を自分で開くことをやめる。1 年後、友人に買物相談されると「ちょっと YUDANE に聞かせて」と答えるようになる。YUDANE は、**「買うかどうか自分で決める」という能力そのもの** を段階的に奪うサービスである。詳細は §2.5「ダメ化の軌跡」を参照。

---

## 0.1 収益モデル

YUDANE の主な収益は **Amazon Associates Program の紹介コミッション** である。ユーザーが YUDANE 経由で Amazon 商品ページに遷移し、適格取引として購入が成立した場合、商品カテゴリに応じた紹介料（上限 10%）が支払われる。

この構造はプロダクトの倫理設計として意図的に採用している:

- ユーザーが **判断を委ねて散財する** ほど、YUDANE の収益が増える
- すなわち「委ねるほど儲かる」企業であり、ダメ化は副作用ではなく **経済的インセンティブの帰結そのもの**
- この構造はユーザーに明示する義務がある（Associates Operating Agreement 遵守、§9 NG-8）。アプリ内設定画面と初回オンボーディングで「YUDANE は Amazon Associates です」の開示を常時表示する

補助収益（将来の拡張余地）:

- プレミアムプラン（冷却モードの無制限切替、通知カスタマイズ、論破ログ永久保存）
- 楽天・Yahoo! ショッピング等、他 EC の Associates への拡張（Share Extension の対象拡大と同時進行）

---

## 1. Intent 分析サマリー

| 項目 | 内容 |
|---|---|
| User Request | AI-DLC Hackathon「人をダメにするサービス」応募に向けた設計 |
| Request Type | New Project (Greenfield) |
| Scope Estimate | System-wide — モバイル（iOS/Android）+ バックエンド API + AI 推薦/論破エンジン + Amazon Creators API 連携 |
| Complexity Estimate | Complex — マルチコンポーネント、AI × Amazon 連携 × モバイル UX |
| Requirements Depth | Comprehensive |
| 書類審査評価の重点 | Intent 明確さ / 創造性とテーマ適合性 |

---

## 2. プロダクトビジョン

### 2.1 エレベーターピッチ

> 深夜 0 時、悠介はベッドで Amazon を眺めている。気になるイヤホンをカートに入れる。「でも来月ピンチだしな」と画面を閉じる。30 秒後、YUDANE からプッシュ通知: 『そのイヤホン、悠介さんが 3 回見返してたやつでしょ。1 分だけ話そう』。開くと AI が論破モーダルを立ち上げ、「なんで今それ必要か」を事実ベースで 3 ターン論破。悠介は「🛍 Amazon で買う」をタップ。Amazon アプリに切り替わり、カートに商品が入った状態でチェックアウト画面が開く。翌朝届いた箱を見て苦笑するが、アプリは『今日もいい選択だったね』と褒めてくる。

### 2.2 世界観・トーン

- **背徳系**: 罪悪感が快感に変換されるデザイン。買ったあとに褒められる
- **ガチ実用系**: UI は本物のコマースアプリ級に洗練。**便利の先に退化がある**
- 敵は「ケチで合理的な自分」、味方は「頑張ってる自分」。AI は常に後者の肩を持つ
- **コピートーン: 友達系**（v0.3 で更新）。敬語ではなくタメ口・近い距離感で語りかけ、「信頼できる友人が論破してくる」構図を作る。絵文字は控えめ、カラーパレット（Indigo + cold rose + cyan）は静かな誘惑を保持して UI の冷静さとコピーの親近感でギャップを演出する
  - 例（AI 論破）: 「これ絶対好きだろ。会議 6 本乗り切ったし、自分にご褒美じゃね？」
  - 例（プッシュ通知）: 「悠介、あのイヤホン 3 回見てたよね。1 分だけ話そう」
  - 例（決済前）: 「最後の確認。Amazon に飛ばすよ」

### 2.3 北極星指標（North Star Metric）

**論破介入あたりの Amazon 遷移率**  
= (「🛍 Amazon で買う」タップ数) / (論破セッション総数)

補助指標:

- **カート介入成約率**: Share Extension で登録されたカート商品のうち、論破 → Amazon 遷移に至った率
- **エージェント推薦の Amazon 遷移率**（リール経由）
- **Share → 論破開始までの平均時間**（介入スピードの品質指標）
- **ダメ化スコア**: 論破頻度 × 深夜帯利用率 × 1 決済あたりの熟考時間の短さの合成指標
- DAU / WAU 0.6+ / 平均セッション 8 分+ / 深夜帯（22〜2 時）利用比率 30%+ / Amazon 遷移までの平均タップ数 3 以下

### 2.4 なぜモバイルアプリなのか（Why Mobile）

このサービスがスマホネイティブでなくてはならない理由は 5 つ。Web や PC でも「動かせる」が、**ダメ化の効き方が桁違いに落ちる**。

1. **意思決定は手の中で起きる** — EC の迷いはデスクよりもベッド・通勤・トイレで発生する。介入は携帯でなければ届かない
2. **Share Extension が Amazon アプリと YUDANE を直結する** — iOS Share Extension / Android Share Target で、ユーザーが Amazon Shopping アプリの商品ページから「共有 → YUDANE」で送るだけで、ASIN 抽出 → Creators API メタ取得 → カート監視登録まで 2 秒で完了する。これは Web アプリでは到達できない面積
3. **通知 × 時刻 × カレンダー予定 × 位置** で介入タイミングを最適化できる — 深夜 22 時、給料日翌朝、家電量販店近接、会議明け… すべてモバイル固有のシグナル
4. **ワンタップで Amazon へ**（摩擦ゼロ遷移） — ネイティブ Deep Link で Amazon アプリを直接起動できる。PC ブラウザでは再ログイン・カード情報入力が挟まり、論破成功直後の「熱」が冷める
5. **HealthKit / カレンダー / 位置 / 画面点灯頻度** などのコンテキスト信号で AI パーソナライズが桁違いに強化される

→ この 5 つが重なって初めて、「**迷う → 秒で論破 → ワンタップ Amazon**」のループが成立する。Web では原理的に不可能な体験設計である。

### 2.5 ダメ化の軌跡（Degradation Arc）

YUDANE の価値提案は、短期的な利便性ではなく **時間をかけて進行する行動変容** にある。ユーザーは下表の 4 段階を辿って退化する。すべての機能設計（論破・リール・カート介入・カレンダー連動・ゲーミフィケーション）は、このアークを加速するために存在する。

| 期間 | 行動の変化 | 思考の変化 | 失われた能力 |
|---|---|---|---|
| Day 1 | アプリを入れ、初回の論破で 1 商品を Amazon で購入 | 「面白いアプリだな」 | — |
| Week 2 | 通知音を聞くとアプリに指を伸ばす反射が形成。カート監視リストに 5〜10 件が常駐 | 「悩むより AI に聞いた方が早い」 | 買い物の前にひと呼吸置く習慣 |
| Month 3 | Amazon を自分で開く頻度が約 80% 減少。「確保しておきました」通知を開封することが休憩時間の主活動 | 「AI がお勧めしない = 自分も欲しくない」が一致 | 自発的に欲しいものを探す習慣 |
| Year 1 | カート監視リストが常時 30 件以上。友人に買物相談されると「ちょっと YUDANE に聞かせて」と答える | 「自分の選択は AI より信頼できない」 | 自分の欲望を自分の言葉で語る能力 |

この退化は副作用ではなく **プロダクトの設計意図そのもの** である。YUDANE は、便利の先にある「自分で決めなくてよくなる」状態を最終目的地に据え、論破（UC-01）・リール（UC-02）・カート介入（UC-03）のすべてがこのアークを加速するよう協調する。収益モデル（§0.1）もこのアークと整合する — 委ねるほど Amazon での散財が増え、YUDANE のコミッションが増える。

---

## 3. ペルソナ

### 3.1 ペルソナA: 佐藤 悠介（28歳・男）— メイン

- **職種**: 外資系 SaaS のカスタマーサクセス、フルリモート
- **年収**: 650 万円 / 月収手取り 34 万円 / 残高 180 万円
- **生活**: 朝はベッドで Slack、昼は UberEats、夜は Netflix。歩数 1 日 1,200 歩
- **悩み**: 「Amazon で欲しいものがあっても 1 時間悩んで結局閉じる。買わないのに 1 時間消えるのが一番ストレス」
- **ダメ化シナリオ**:
  1. 金曜 23 時、Amazon Shopping アプリで気になるワイヤレスイヤホンをカートに入れる
  2. 「来月の引き落とし厳しいかも」と迷って画面を閉じる
  3. Amazon の共有ボタンから「共有 → YUDANE」で送る（以前 YUDANE が教えてくれた便利ワザ）
  4. 30 秒後、YUDANE のプッシュ通知: 『悠介、さっきのイヤホン **3 回目** だよね。1 分話そう』
  5. 開くと AI が論破モーダル。「先週の会議 23 本よく乗り切った。時給換算 11 分のイヤホンだよ」
  6. 3 ターンで翻意。「🛍 Amazon で買う」をタップ → Amazon アプリにカートが開いた状態で遷移 → チェックアウト完了
  7. 翌朝届いた箱を見て、悠介は思う。**『この AI、俺の迷いを 1 回も無駄にしない』**

#### Before / After 90 days（悠介の変化）

| 観点 | Before（YUDANE 導入前） | After 90 日 |
|---|---|---|
| 商品選び | Amazon で 1 時間悩んで結局閉じることが多い | カート登録後、通知を待って 3 タップで Amazon 遷移 |
| 買物の主導権 | 自分の中の「欲しい / いらない」で判断する | AI の「確保しておきました」を開封する作業になる |
| お金の意思決定 | 残高を見て自制する | 使い切れ達成率（論破の弾薬）を見て「置き去り」に不安を覚える |
| 休日の過ごし方 | Amazon 閲覧が趣味化、1〜2 時間で結局買わない | リールをスクロールして「共有 → YUDANE」、あとは通知待ち |
| 自己認識 | 「ケチだけど計画的」 | 「頑張ってる自分は褒められるべき」 |

この 5 観点はすべて「自分で考える / 選ぶ / 自制する」から「AI に判断を委ねる」への移行であり、プロダクト名「YUDANE（委ね）」が指す通りの退化である。

### 3.2 ペルソナB: 高橋 里奈（32歳・女）— サブ

- **職種**: 広告代理店プランナー、出社とリモート半々
- **特徴**: 「忙しい = 頑張ってる自分」を自己肯定感の軸にしている
- **ダメ化の効き方**: カレンダー連動（FR-CAL）の最大の受益者。打ち合わせ 6 本の日は AI が「この戦い賃として、今週のデート用の香水どう？」と予定とご褒美を繋ぐ

### 3.3 非ターゲット

- ミニマリスト志望者
- FIRE を目指している人（合理性で武装していて論破されにくい）
- 借金を抱えている人（セーフガード対象）

---

## 4. スコープ & 主要ユースケース

### 4.1 スコープ定義

本プロダクトは AWS Summit Japan 2026 AI-DLC Hackathon への応募作品として構想し、審査通過後も AWS 上で継続運用可能な設計を前提とする。機能は「リリース段階」ではなく「論理的な優先度」で整理する（初期コア / サポート / 拡張の 3 層）。対象 EC は **Amazon（Japan マーケットプレイス）** を初期ターゲットとし、将来 楽天・Yahoo! ショッピング等への拡張を見据える。

### 4.2 コアユースケース（サービスの心臓部）

| UC-ID | タイトル | 1 行説明 |
|---|---|---|
| UC-01 | **論破チャット** | ユーザーの「買わない」「迷う」を AI が事実 + 心理で論破する唯一のインタラクション |
| UC-02 | **エージェント型リール** | AI がユーザーを観察して「これあなた好きでしょう」と縦型リールで商品を差し出す |
| UC-03 | **カート介入** | Amazon Shopping アプリのカート停滞を Share Extension で取り込み、AI が時間差追撃で論破 → Amazon 遷移 |

この 3 つは「**迷いを Amazon 遷移（= 購入行動）に変換する**」という単一のゴールを共有する。YUDANE のすべては、この 3 つに従属する。

### 4.3 サポーティング・ユースケース

| UC-ID | タイトル | 役割 |
|---|---|---|
| UC-04 | カレンダー連動推薦 | カレンダー予定から商品を先回り提案、論破材料として活用（FR-CAL） |
| UC-05 | 散財ゲーミフィケーション | EXP / 称号 / Streak で「やめたくない」を作る |
| UC-06 | 逆・家計簿サブ画面 | 死蔵資産ゲージ・使い切れ達成率（予算感アンケートベース）。論破の弾薬 |
| UC-07 | ダメ化ポートフォリオ | AI の分類を可視化する透明性機能（編集可） |
| UC-08 | セーフガード | 月間使用上限・冷却モード・NG カテゴリ |

---

## 5. 機能要件 (Functional Requirements)

> FR-ID: `FR-<領域>-<番号>`。領域コード: DEBATE=論破 / REEL=リール / CART=カート介入 / CAL=カレンダー連動 / GAME=ゲーミフィケーション / PROFILE=プロファイル / DASH=逆家計簿サブ / FUNNEL=購入導線 / AUTH=認証/セーフ

### 5.1 論破チャット (FR-DEBATE) — コア

- **FR-DEBATE-01**: 論破セッションは 3 つのトリガーで起動する — (a) リールでの「買わない」タップ、(b) カート介入通知のタップ、(c) 商品ページでの長時間滞留検知（将来拡張）
- **FR-DEBATE-02**: AI は対象商品メタデータ + ユーザー嗜好ベクトル + コンテキスト信号（**カレンダー予定・時刻・直近購入履歴・使い切れ達成率**）をプロンプトに組み立て、**事実ベース + 心理ベース** の 2 軸で反論を生成する
- **FR-DEBATE-03**: 初回トークン到達 300ms 以下、ストリーミング配信で初回反論を 3 秒以内に提示
- **FR-DEBATE-04**: ユーザーが反論に同意して「🛍 Amazon で買う」をタップした場合「論破成功」としてログ蓄積、嗜好モデルと反論テンプレートを強化
- **FR-DEBATE-05**: ユーザーが 3 回連続で反論を拒否したら「本日はもう提案しない」クールダウンに入る（セーフガード）
- **FR-DEBATE-06**: 論破モードは 1 商品あたり最大 90 秒で自動終了
- **FR-DEBATE-07**: AI の反論はユーザーの身体・家族・人種・病歴・宗教を攻撃しない。プロンプトガードレール + 出力モデレーションを 2 段で適用
- **FR-DEBATE-08**: コピートーンは **友達系**（§2.2）で統一。「あなた」「〜しませんか」の敬語トーンではなく、「悠介」「〜しようぜ」的なタメ口で論破する

### 5.2 エージェント型リール (FR-REEL) — コア

- **FR-REEL-01**: 縦型スワイプ UI、AI 選定商品をカードで無限スクロール提示
- **FR-REEL-02**: 各カードは「**🛍 Amazon で買う**（ダブルタップ）」「買わない（左スワイプ → 論破モードへ）」「後で（右スワイプ → カート監視入り）」の 3 アクション
- **FR-REEL-03**: 推薦コメントは嗜好 × 時間帯 × 疲労度 × **カレンダー予定** の 4 軸で LLM 動的生成。「確保しておきました」「○○ のために見つけといた」等の所有感訴求ラベルを付与
- **FR-REEL-04**: 商品データは Amazon Creators API から取得（Approved Mobile Application 承認後。ハッカソン段階は代表 1〜2 社のダミーカタログで再現）
- **FR-REEL-05**: 「🛍 Amazon で買う」タップ時は、Amazon 遷移前に **1 枚の確認オーバーレイ**（「Amazon に飛ばすよ」）を挟む。確認のみ、Face ID 等の認証は入れない。タップで Amazon アプリを Deep Link で起動（Android は Share Target）

### 5.3 カート介入 (FR-CART) — コア

- **FR-CART-01**: iOS Share Extension / Android Share Target を介して、ユーザーが **Amazon Shopping アプリ** の商品ページを「共有 → YUDANE」で送ると、URL から ASIN を抽出し、Amazon Creators API で商品メタデータ（名称・価格・画像・レビュー要約）を取得して「カート監視リスト」に登録する
- **FR-CART-02**: 登録された商品は **30 分 / 6 時間 / 24 時間** の 3 ステップでプッシュ通知追撃する（ユーザーが「🛍 Amazon で買う」をタップ or 明示的に「いらない」と宣言するまで）
- **FR-CART-03**: 通知タップで論破モード（UC-01）に遷移、論破成功時は **Associates Program の Special Link**（アフィリエイトタグ付き URL）で Amazon に遷移させる
- **FR-CART-04**: 決済は **Amazon アプリ / Web 側で完結する**。YUDANE 内部では決済処理を一切持たない。商品は Amazon の「add-to-cart URL」または商品ページ URL を Special Link として生成し、Deep Link で Amazon アプリを起動する
- **FR-CART-05**: 遷移前に「Amazon に移動します」の 1 枚確認オーバーレイを挟む（監査 + 意図確認、§9 NG-8 開示義務との整合）
- **FR-CART-06**: クリップボードに Amazon URL がコピーされた状態でアプリを開くと、「これ登録しとく？」とサジェストする（UX 摩擦削減）
- **FR-CART-07**: 将来拡張: スクリーンショット画像からの商品特定（画像 AI）、他 EC（楽天・ZOZO）の Share 対応
- **FR-CART-08**: Creators API はレート制限あり（Associates ID 経由の直近 30 日売上に応じて TPS 拡大）。商品メタのキャッシュ戦略を ElastiCache Redis で持つ（詳細は Application Design）

### 5.4 カレンダー連動推薦・論破材料 (FR-CAL)

v0.2 では疲労度算出のための信号として扱っていたカレンダー連携を、**予定駆動の商品提案 + 論破材料生成** に再定義する。

- **FR-CAL-01**: カレンダー API（iOS EventKit / Google Calendar）から向こう 14 日間の予定を取得する（オプトイン必須）
- **FR-CAL-02**: 予定タイトル・場所・参加者数を LLM で分類し、**「その予定のために必要になる商品カテゴリ」** を推定する。代表例:

  | 予定の種類 | 推薦カテゴリ | 論破コピー例 |
  |---|---|---|
  | プレゼン / 登壇 / キーノート | シャツ / USB-C ハブ / レーザーポインタ / 喉スプレー | 「来週月曜のプレゼン、あなたの印象を決める場面。このシャツで臨もう」 |
  | デート / ディナー / 記念日 | 香水 / シャツ / 花束 / ワイン | 「土曜のデート、香水ないのはもったいないだろ」 |
  | キャンプ / BBQ / 焚き火 | ランタン / クーラーボックス / アウトドアチェア / 虫除け | 「来月のキャンプまで 3 週間。ランタン今日中に買えば余裕で間に合う」 |

- **FR-CAL-03**: 推定カテゴリを嗜好ベクトルと組み合わせて Creators API を検索、リール先頭に「○○ のためのエージェント提案」タグ付きで挿入する
- **FR-CAL-04**: 論破モーダル（UC-01）の AI プロンプトに、対象商品と関連する予定情報を組み込む。購入正当化の最強の根拠となる
- **FR-CAL-05**: プライバシー配慮 — 予定本文はバックエンドに送らず、端末ローカルでカテゴリ分類してからバックエンドへはカテゴリ文字列のみ送信する

### 5.5 散財ゲーミフィケーション (FR-GAME)

- **FR-GAME-01**: **「🛍 Amazon で買う」タップ時点** に「委ね EXP」を加算し、レベル・称号（例: 「本日の湯水使い」「静かな信徒」）を付与する。実購入コンバージョンは Associates レポートで追跡するが、ユーザー体験としては「タップ = コミット」とする（摩擦排除優先）
- **FR-GAME-02**: 週間・月間の散財ランキングを匿名 ID でリーダーボード表示（オプトイン）
- **FR-GAME-03**: 連続 Amazon 遷移日数（委ね Streak）を表示、Streak が途切れた場合のみ負のフィードバックを与える
- **FR-GAME-04**: 特別称号は限定イベント（例: 給料日週 / プレゼン前夜 / 長期連休前）で解放される

### 5.6 プロファイル & 嗜好モデル (FR-PROFILE)

- **FR-PROFILE-01**: 初回オンボーディングで年収レンジ・**月間予算感（使い切れの弾薬になる）**・趣味タグ・好きなブランド（5 つ以上）・NG カテゴリを登録
- **FR-PROFILE-02**: Amazon 遷移履歴・スキップ履歴・論破成功率・**カレンダー予定パターン**（プレゼン頻度、デート頻度等）から嗜好ベクトルを日次バッチで更新
- **FR-PROFILE-03**: ユーザーは「ダメ化ポートフォリオ」画面で AI の分類を確認・編集できる（透明性、UC-07）
- **FR-PROFILE-04**: Associates Program 開示文言を常時表示（「YUDANE は Amazon Associates として、紹介リンク経由の購入で Amazon から紹介料を受け取っています」）

### 5.7 逆・家計簿サブ機能 (FR-DASH) — サポート

- **FR-DASH-01**: ホーム画面のサブ領域に小型ダッシュボード（月間予算感アンケート結果 vs Amazon 遷移回数 / 死蔵資産ゲージ / 使い切れ達成率）を表示する。主役ではない
- **FR-DASH-02**: 「死蔵資産」「使い切れ達成率」は論破モーダルの AI プロンプトに **弾薬** として組み込まれる（例: 「今月まだ 38% が置き去り」）
- **FR-DASH-03**: 計算根拠は初回オンボーディングの予算感アンケート（月間使える額、月間貯金額の自己申告）とアプリ内の Amazon 遷移履歴のみ。**金融 API 連携は行わない**（v0.2 から方針変更）

### 5.8 金融データ連携 (FR-FIN) — 大幅縮小

- **FR-FIN-01**: v0.3 以降、Plaid / Moneytree / Money Forward ME / 銀行 OpenAPI 等の金融アグリゲーション連携は行わない
- **FR-FIN-02**: 予算感は §5.6 FR-PROFILE-01 のオンボーディングアンケートで取得する
- **FR-FIN-03**: 決済は常に Amazon 側で完結するため、YUDANE 側に Stripe / Square 等の決済サンドボックスも不要

### 5.9 認証 & セーフガード (FR-AUTH)

- **FR-AUTH-01**: Amazon Cognito（または Firebase Auth）でメール + パスワード + MFA（TOTP）を提供（SECURITY-12）
- **FR-AUTH-02**: 初回登録時に「月間 Amazon 遷移上限」を必須設定させる（デフォルト: 月間予算感の 70%）。上限到達で論破モードとリールを停止
- **FR-AUTH-03**: クールダウン機能: 1 アイテム Amazon 遷移直後 10 分は同カテゴリの商品をリールに出さない
- **FR-AUTH-04**: ユーザーが「冷却モード」を手動 ON にしたとき、または月間上限到達時は、24 時間すべての「🛍 Amazon で買う」ボタンを非活性化する（セーフガード）
- **FR-AUTH-05**: 借金検出（ユーザー自己申告の「負債あり」フラグ）で冷却モードを自動 ON
- **FR-AUTH-06**: ユーザーはいつでもアカウント削除・全データエクスポートが可能

### 5.10 購入導線 UX (FR-FUNNEL)

YUDANE は「ユーザーの購入意思決定のファネルにいかに深く入り込むか」を最重要 UX 原則とする。

- **FR-FUNNEL-01**: タッチポイントは 4 種を常時並走する —
  - **Share 受動**（UC-03 カート介入）: Amazon Shopping アプリからの共有
  - **予定駆動**（UC-04 / FR-CAL）: カレンダー予定から先回り提案
  - **通知駆動**: カート追撃（30m / 6h / 24h）+ コンテキスト連動（深夜帯 / 給料日 / プレゼン前日）
  - **自発リール閲覧**（UC-02）: ユーザーが暇つぶしに開く
- **FR-FUNNEL-02**: 介入タイミングは以下で自動最適化 —
  - 時刻（深夜帯 22〜2 時）
  - カレンダー予定の直前 N 日
  - カート停滞時間（30 分 / 6 時間 / 24 時間）
  - Amazon 在庫シグナル（セール / 新作入荷）
- **FR-FUNNEL-03**: 摩擦は **2〜3 タップ以内** に抑える —
  - Share → YUDANE 登録 → Amazon 遷移 = **2 タップ**
  - 通知 → 論破 → Amazon 遷移 = **3 タップ**
  - セーフガード発動時のみ追加ステップが入る
- **FR-FUNNEL-04**: 論破の成功・失敗パターンを嗜好ベクトルに反映する **個別最適化ループ** を日次バッチで回し、成約率の継続向上を図る
- **FR-FUNNEL-05**: 月間使用上限・冷却モード発動時のみ Amazon 遷移を阻止する（セーフガード最優先、FR-AUTH 連携）
- **FR-FUNNEL-06**: ファネル全体の KPI ダッシュボード（社内用）を CloudWatch Dashboard で可視化（§6.1 指標と対応）

---

## 6. 非機能要件

### 6.1 UX 中毒性指標（テーマの核）

| 指標 | 目標値 | 計測方法 |
|---|---|---|
| 論破セッション → Amazon 遷移率 | 35%+ | 論破イベントトラッキング |
| カート介入通知の開封率 | 45%+ | プッシュイベントトラッキング |
| カート介入 → 論破 → Amazon 遷移率（フルパス） | 25%+ | ファネル分析 |
| Share 受領 → 論破開始までの平均時間 | 60 秒以下 | クライアントログ |
| 1 セッション滞在時間 | 8 分+ | クライアントログ |
| 1 日の起動回数 | 2.5 回+ | DAU / 起動イベント |
| 深夜帯（22〜2 時）利用比率 | 30%+ | セッション時刻ヒストグラム |
| Amazon 遷移までの平均タップ数 | 3 タップ以下 | UI イベントロギング |

### 6.2 パフォーマンス

- 論破チャット初回トークン: 300ms 以下（Amazon Bedrock Claude Haiku クラス想定）
- リール描画: 60fps 維持
- Share Extension 受領 → 商品メタ表示: 2 秒以下（Creators API ウォームキャッシュ前提）
- カート介入通知配信遅延（登録 → 初回プッシュ）: 30 秒以下
- アプリ起動コールドスタート: 2 秒以下

### 6.3 スケーラビリティ

- 初期リリース想定: 同時 50 ユーザー
- 拡張時想定: 同時 500 ユーザー、DAU 5,000 のスパイクを吸収できる構成
- バックエンドはサーバーレス中心（Lambda / API Gateway / DynamoDB）。推薦計算のみ必要に応じてコンテナ化
- Amazon Creators API のレート制限に備えた ElastiCache Redis ウォームキャッシュ（商品メタ TTL 6 時間）

### 6.4 セキュリティ（Security Baseline Extension 全面適用）

| ルール | 適用方針 |
|---|---|
| SECURITY-01 暗号化 | DynamoDB / S3 に KMS 暗号化、全 API は TLS 1.2+ 強制 |
| SECURITY-02 ネットワークログ | API Gateway / CloudFront 実行・アクセスログを CloudWatch に集約 |
| SECURITY-03 アプリログ | 構造化ログ（JSON）で相関 ID + タイムスタンプ、PII/トークン不出力 |
| SECURITY-04 HTTP ヘッダ | 管理画面側は CSP / HSTS / X-Content-Type-Options 等を全セット |
| SECURITY-05 入力検証 | API Gateway + Lambda の入口で JSON Schema 検証、Amazon URL/ASIN のフォーマット検証 |
| SECURITY-06 IAM 最小権限 | 各 Lambda に個別ロール、ワイルドカード禁止 |
| SECURITY-07 ネットワーク | VPC 内 Lambda、AWS サービスへは VPC Endpoint 経由 |
| SECURITY-08 認可 | 全 API は Cognito JWT 検証 + リソースオーナー確認、IDOR 対策必須 |
| SECURITY-09 ハードニング | デフォルト認証情報禁止、エラー詳細は本番隠蔽、S3 パブリック遮断 |
| SECURITY-10 SBOM | Snyk / Dependabot を CI に組込み、ロックファイルコミット |
| SECURITY-11 セキュアデザイン | 論破 / 認可ロジックは専用モジュール分離、API は rate limit |
| SECURITY-12 認証 | Cognito MFA 必須、セッション HttpOnly/Secure/SameSite |
| SECURITY-13 整合性 | SRI、CI パイプラインへのアクセス分離、Amazon 遷移履歴は監査ログ |
| SECURITY-14 アラート | 認証失敗・権限エラーに CloudWatch Alarm、ログ保持 90 日以上 |
| SECURITY-15 例外処理 | 全外部呼び出しに try/catch、グローバルエラーハンドラ、fail-closed |

追加考慮（Amazon 連携固有）:

- Creators API の認証情報（Credential ID / Secret）は AWS Secrets Manager 管理。ハードコード禁止
- Amazon 商品メタデータは一次データ保持を最小限にし、キャッシュ TTL を 6 時間とする（PA-API / Creators API の規約整合）
- Associates ID はユーザーデータと紐付けない独立キーで管理

### 6.5 テスタビリティ（PBT Extension 全面適用）

| PBT カテゴリ | 対象領域（暫定） |
|---|---|
| PBT-01 Property identification | 全 Unit の Functional Design で属性整理 |
| PBT-02 Round-trip | 商品メタデータの JSON serialize ⇔ deserialize、嗜好ベクトル encode ⇔ decode、ASIN 抽出/復元 |
| PBT-03 Invariant | 「論破タイマーは 90 秒で強制終了」「冷却モード中は Amazon 遷移なし」「月間上限到達後はリール停止」等 |
| PBT-04 Idempotency | ユーザープロファイル更新 API、嗜好ベクトル日次更新、カート監視登録、Share 受領処理 |
| PBT-05 Oracle | 推薦エンジン新版 vs 旧版の比較 |
| PBT-06 Stateful | **カート介入の状態遷移**（登録 → 30 分後通知 → 6 時間後通知 → 24 時間後通知 → Amazon 遷移 or 破棄）、委ね EXP / Streak 遷移、冷却モード遷移 |
| PBT-07 Generator quality | 金額・歩数・カレンダー予定パターンに対する現実的ドメインジェネレータ |
| PBT-08 Shrinking | 失敗ケースの自動縮約、シード値ログ必須 |
| PBT-09 Framework | **React Native/TypeScript**: `fast-check`、バックエンド Python Lambda: Hypothesis、ネイティブモジュールは必要に応じて SwiftCheck / Kotest PT |
| PBT-10 Complementary | 主要 UC-01/02/03 は example-based test も併存必須 |

### 6.6 アクセシビリティ

- 最低でも WCAG 2.2 AA 相当の色コントラスト
- VoiceOver / TalkBack 対応（Amazon 遷移確認は音声でも説明）
- ただし WCAG 全面準拠は宣言しない（実機検証・専門レビュー未実施のため）

### 6.7 可用性 & 運用

- SLO: 99.5%
- ログ保持 90 日以上（SECURITY-14）
- AI 推薦エンジン停止時のフォールバック: 事前用意の「静的推薦カタログ」に自動切替
- Creators API 障害時: 商品メタは ElastiCache キャッシュで継続提供、リアルタイム検索は縮退

---

## 7. 技術スタック（暫定）

| レイヤ | 候補 | 理由 |
|---|---|---|
| モバイル | **React Native 0.76+ (New Architecture)** + **TypeScript 5.x** + **AWS SDK v3** + **TanStack Query**（サーバー状態）+ **Zustand**（クライアント状態） | New Architecture (Fabric + TurboModules) が default。AWS SDK を直接利用して通信レイヤを明示的に管理。Share Extension / Share Target はネイティブモジュール（`react-native-share-menu` 等）経由で実装 |
| 認証 | **Amazon Cognito** + **AWS Amplify JavaScript v6 の Auth モジュールのみ** + TOTP MFA | `amazon-cognito-identity-js` は npm 公式で非推奨宣言。AWS 公式推奨に従い Amplify の Auth 機能のみを薄く採用する（Data/Functions/CLI は不採用）。CDK で Cognito User Pool を直接管理し、Amplify CLI での生成は行わない。SECURITY-12 整合 |
| API / データ | **API Gateway (REST) + Lambda (Python 3.13)** + **生 DynamoDB** | Python 3.13 は AWS Lambda で GA（2024-11〜）。Amplify Data (AppSync) を採用せず、REST で柔軟に制御。論破 LLM / カート監視 / Amazon 連携など複雑ロジックは Lambda で自由実装 |
| データストア | **生 DynamoDB**（ユーザー / Amazon 遷移履歴 / カート監視リスト）+ S3（画像 / カタログキャッシュ）+ ElastiCache Redis（セッション / Creators API キャッシュ / レート制限） | CDK で直接定義、暗号化標準 |
| AI / 推薦 | Amazon Bedrock（**Claude Haiku 4.5** で論破ストリーミング + **Claude Sonnet 4.6** で複雑なプロンプト合成）、埋め込み **Titan Embeddings V2**、ベクトル OpenSearch Serverless | Haiku 4.5 は Sonnet 4 級性能で低コスト・高速、Sonnet 4.6 は予定駆動プロンプト合成向け。Opus 4.7 は高コストのため本番利用は見送り、評価用に限定。CDK 拡張 Lambda (Python) から呼び出し、Core AI 要件 + ストリーミング + 低レイテンシ |
| **Amazon 連携** | **Amazon Creators API**（商品データ・OAuth 2）+ **Amazon Associates Program**（Special Link 生成 + コミッション計測） | PA-API の後継。**PA-API 5.0 は 2026-04-30 に deprecation、2026-05-15 に endpoint shutdown**。モバイルアプリで使用するには **Approved Mobile Application** 承認が必要（§8 A-10）。書類審査時点では Creators API への完全移行が必須タイミング |
| プッシュ通知 | **AWS End User Messaging Push** + **EventBridge Scheduler**（CDK 拡張） | Amazon Pinpoint は 2026-10-30 で EoL のため代替採用。APNs / FCM サポート、カート介入の 30 分 / 6 時間 / 24 時間追撃を EventBridge Scheduler でスケジューリング |
| カレンダー | iOS EventKit / Google Calendar API（RN ネイティブモジュール経由） | FR-CAL 予定取得 |
| 観測 | CloudWatch Logs + Metrics + Alarms + X-Ray | SECURITY-02/03/14 整合 |
| CI/CD | **AWS CDK (TypeScript, v2 系最新)** + **Node.js 22 LTS** + **GitHub Actions** | IaC + SBOM 生成。Node.js 22 LTS（2024-10〜）は AWS CDK / AWS SDK v3 の推奨ランタイム。Amplify Gen 2 CLI は不採用 |
| PBT FW | **Hypothesis (Python 3.13 Lambda)** + **fast-check (TypeScript 5.x / React Native 0.76+)** + ネイティブモジュール用に必要に応じて SwiftCheck / Kotest PT | PBT-09 |

v0.2 から削除したもの:

- Plaid / Moneytree / Money Forward ME（金融アグリゲーション）→ オンボーディングアンケートで代替
- Stripe test mode / Square sandbox（決済）→ Amazon 側で決済が完結するため不要

v0.3 → v0.4 で更新:

- Flutter → **React Native + AWS Amplify Gen 2**（Auth / Data を中心に採用、複雑ロジックは CDK 拡張 Lambda）
- Amazon Pinpoint（2026-10-30 EoL）→ **AWS End User Messaging Push + EventBridge Scheduler**
- PBT FW: glados (Dart) → **fast-check (TypeScript / React Native)**

v0.4 → v0.5 で更新:

- **AWS Amplify Gen 2 を全面削除**（Data / Auth / Functions / CLI すべて不採用）。AppSync の縛りを外し、REST + Lambda + 生 DynamoDB で柔軟性と説明容易性を優先
- モバイル状態管理: **TanStack Query**（サーバー状態）+ **Zustand**（クライアント状態）を採用。認証は `amazon-cognito-identity-js` を直接利用
- IaC は **AWS CDK (TypeScript) 単独**、Amplify Gen 2 CLI のラッパーは不採用

v0.5 → v0.6 で更新:

- **認証方針の修正**: `amazon-cognito-identity-js` は npm 公式で非推奨（2025 以降、Amplify JavaScript の Auth 機能利用を推奨）。AWS 公式推奨に従い、**Amplify JavaScript v6 の Auth モジュールのみを薄く採用** する方針に変更。Data / Functions / CLI は引き続き不採用、Cognito User Pool は CDK で直接管理（§A-2 同期修正）
- **ランタイム最新化**: Python 3.12 → **3.13**（Lambda GA 済み）、Node.js 版を明示 → **22 LTS**、React Native → **0.76+ (New Architecture)**、TypeScript → **5.x**
- **Bedrock Claude モデルを明示**: Haiku/Sonnet（無印）→ **Claude Haiku 4.5 + Claude Sonnet 4.6**（Opus 4.7 は評価用に限定）。Titan Embeddings は V2 に更新
- **PA-API 廃止タイムラインの正確化**: 「2026-05-15 廃止予定」→「**2026-04-30 deprecation / 2026-05-15 endpoint shutdown**」と分離記述
- **CDK バージョン明示**: AWS CDK v2 系最新 を明記

---

## 8. 前提 & 未確定事項

- **A-1 プロダクト名**: **「YUDANE（委ね）」で確定**。「判断を委ねる」= 自分で決める能力を放棄するという、本プロダクトの退化ゴール（§2.5）そのものを名前に刻む
- **A-2 モバイル実装戦略**: **React Native 0.76+ (New Architecture) + TypeScript 5.x + AWS SDK v3** を第一候補。状態管理は **TanStack Query + Zustand**、認証は AWS 公式推奨に従い **Amplify JavaScript v6 の Auth モジュールのみ** を採用（`amazon-cognito-identity-js` は非推奨のため不採用）。Amplify の Data / Functions / CLI は不採用で、Cognito User Pool は CDK で直接管理する。Share Extension / Share Target はネイティブモジュール（`react-native-share-menu` 等）経由で実装。論破 LLM / Creators API 連携 / カート監視スケジューラなど独自要件は **AWS CDK (TypeScript) v2 系最新 + Python 3.13 Lambda** で自由実装する
- **A-3 初期コア**: UC-01（論破）/ UC-02（リール）/ UC-03（カート介入）の 3 つ。UC-04 カレンダー連動は準コアとして早期実装、サポーティング（UC-05〜08）は段階的に追加
- **A-4 Amazon 連携のスコープ**: 初期ターゲットは Amazon（Japan マーケットプレイス）。実お金は動かさない（§9 NG-4）— YUDANE 内部で決済は持たず、ユーザーが Amazon 側で決済するため、原則として YUDANE 側の金銭的実害は発生しえない構造
- **A-5 外部 EC 連携の段階展開**: 初期は Amazon のみ対応。拡張時に楽天・Yahoo! ショッピング・ZOZO 等を Share Target に追加
- **A-6 チーム 4 名の役割**: Workflow Planning で確定（PM/UX、モバイル、バックエンド/AI、インフラ/CDK を想定）
- **A-7 対象リージョン**: ap-northeast-1
- **A-8 UI 言語**: 日本語
- **A-9 収益モデル**: Amazon Associates Program の紹介コミッションを主収益とする（§0.1）。Associates Operating Agreement 遵守（§9 NG-8）
- **A-10 Approved Mobile Application 申請計画**: Associates Program の Operating Agreement §5 に基づき、モバイルアプリで Special Link を配信するには Approved Mobile Application としての事前承認が必須。
  - **書類審査・予選段階**: Creators API はモックデータで代替（実 API コールせず、ダミーカタログを返すスタブで要件を満たす）
  - **決勝前**: Approved Mobile Application の申請を完了させ、本番 Creators API と Special Link を組み込む
  - 申請期間は不確定のため、申請着手タイミングは Workflow Planning で確定する

---

## 9. NG ライン & 倫理的セーフガード

- **NG-1 違法性**: 違法薬物・武器・未成年飲酒/喫煙・ギャンブル・詐欺等の商品はリール / カート介入の対象外。カテゴリブラックリスト必須
- **NG-2 健康被害**: 過量アルコール・極端ダイエット食品・未認可サプリは候補から除外
- **NG-3 差別 / ハラスメント**: 論破コピーはユーザーの身体・家族・人種・ジェンダー・病歴・宗教を攻撃しない。NG 語リスト + LLM プロンプトガードレール
- **NG-4 金融実害**: YUDANE 内部では決済を持たないため、直接的な金銭移動は発生しない。ただし Amazon 側で実害が出るのを防ぐため、月間 Amazon 遷移上限・冷却モード・負債自己申告での自動冷却を実装（FR-AUTH）
- **NG-5 未成年**: 18 歳未満は利用不可（Cognito 年齢確認）
- **NG-6 精神衛生**: 「あなたには価値がない」「友達が離れる」等、脅迫・罪悪感強要型のコピーは禁止。AI 出力の 2 段モデレーション（プロンプトレベル + 出力レベル）
- **NG-7 データ悪用**: 購入履歴・位置情報・ヘルスケアデータ・カレンダー予定は広告主に販売しない。予定本文はバックエンドに送らない（FR-CAL-05）
- **NG-8 Amazon Associates Operating Agreement 遵守**:
  - Approved Mobile Application としての事前承認が完了するまで、本番環境で Special Link を配信しない
  - アプリ内に「YUDANE は Amazon Associates として、紹介リンク経由の購入で Amazon から紹介料を受け取っています」の開示を常時表示（FR-PROFILE-04）
  - 自己購入・家族/友人購入による commission 請求を禁止（Operating Agreement §16）
  - Amazon Mark の使用は承認範囲内のみ、リンク短縮での偽装禁止、商標遵守
  - スクレイピング・自動カート操作・Amazon アカウント情報の YUDANE 側保持は一切行わない

この原則は Application Design / Code Generation の全段階で参照する。

---

## 10. トレーサビリティ

| 要件/軸 | 書類審査評価軸 | 該当セクション |
|---|---|---|
| Intent 明確さ | 基準 1 | Section 0 / 0.1 / 2 / 3 |
| 創造性・テーマ適合性 | 基準 3 | Section 2.1 / 2.4 / 2.5 / 3.1 / 4.2 / 5.3 / 5.4 |
| Unit 分解の下地 | 基準 2 | Section 4.2 / 5（Units Generation で細分化） |
| ドキュメント品質 | 基準 4 | 本書構成 / 後続成果物 |
| 収益 × 倫理の一貫性 | 基準 3 + 倫理 | Section 0.1 / 9 NG-8 |

---

## 11. 次のステップ

1. **Workflow Planning**: どの後続ステージを EXECUTE / SKIP するか決定（評価軸「Unit 分解の適切さ」のため Units Generation は原則 EXECUTE 推奨）
2. **Application Design**: Section 5 の機能要件をコンポーネント / サービス / 依存関係に分解
3. **Units Generation**: UC-01〜04 を並行開発可能な Unit of Work に分割
4. **Construction Phase**: Per-Unit Loop で順次実装
5. **Approved Mobile Application 申請**: 決勝前に完了させる（A-10）

---

## 付録A: 成功像の具体シーン

悠介は金曜の深夜 23:47、ベッドの中で Amazon Shopping アプリで気になるイヤホンをカートに入れ、迷って画面を閉じる。反射的に共有ボタンを押し、「YUDANE」を選んで送る。30 秒後、スマホの通知バナーが光る。『悠介、さっきのイヤホン **3 回目** だよね。1 分だけ話そう』。寝転んだまま親指でタップ。AI が穏やかに切り出す。『先週の会議 23 本、よく生き延びた。時給換算 11 分のイヤホンだよ』。悠介は親指で「まだ抵抗する」を押す。AI は続ける。『あなたが 3 回見返したという事実が、もう答えを出してる』。悠介は「🛍 Amazon で買う」をタップ。Amazon アプリがスライドで立ち上がり、カートに商品が入った状態でチェックアウト画面が表示される。すでに登録済みの住所と支払い方法で、2 タップで注文確定。アプリに戻ると『今日もいい選択だったね』と褒められる。翌朝、箱を開けながら悠介は思う。**『この AI、俺の迷いを 1 回も無駄にしない』**。それは、正確に、**退化の瞬間** である。
