# YUDANE（委ね）

> **買わない理由を論破する AI エージェント・コマース**

AWS Summit Japan 2026 AI-DLC ハッカソン応募作品。テーマ「人をダメにするサービスを考えよう！」に対し、**「自分で買うか決める能力」** を段階的に奪うモバイルアプリを提案する。

[![Status: 書類審査版](https://img.shields.io/badge/Status-%E6%9B%B8%E9%A1%9E%E5%AF%A9%E6%9F%BB%E7%89%88-blue)]()
[![Phase: Inception Complete](https://img.shields.io/badge/Phase-Inception%20Complete-brightgreen)]()
[![Theme: 人をダメにする](https://img.shields.io/badge/Theme-%E4%BA%BA%E3%82%92%E3%83%80%E3%83%A1%E3%81%AB%E3%81%99%E3%82%8B-E8B4D0)]()

---

<details>
<summary>📑 <strong>目次</strong>（クリックで展開）</summary>

1. [📌 概要](#-概要)
2. [🎯 コア機能（4 つのユースケース）](#-コア機能4-つのユースケース)
3. [🎬 体験シーン — 悠介の金曜深夜](#-体験シーン--悠介の金曜深夜)
4. [💀 ダメ化の軌跡（Degradation Arc）](#-ダメ化の軌跡degradation-arc)
5. [👤 このアプリで完成した人間像（Year 1 後の悠介）](#-このアプリで完成した人間像year-1-後の悠介)
6. [🗂️ Unit 責務サマリ](#%EF%B8%8F-unit-責務サマリ)
7. [🔧 技術スタックとシステム構成](#-技術スタックとシステム構成)
8. [🛡️ 倫理ライン](#%EF%B8%8F-倫理ライン)
9. [🚥 進捗](#-進捗)
10. [🎨 モックアップ](#-モックアップビジュアル検証用)
11. [🧠 AI 論破プロンプトの設計原則](#-ai-論破プロンプトの設計原則)
12. [🧪 AI-DLC プロセス](#-ai-dlc-プロセス--サイクル反復で品質を磨く方針)
13. [🗓️ ハッカソン情報 / ライセンス](#%EF%B8%8F-ハッカソン情報)

</details>

---

## 📌 概要

- **誰に**: 過労気味のリモートワーカー（28〜35 歳、月収 34〜45 万円、可処分所得はあるが迷う人）
- **何をする**: Amazon で「欲しいかも」と「買うか迷う」の間にあった *自分で決める間（ま）* を AI が奪う
- **どう奪う（ダメ化の 3 段メカニズム）**:
  - **M-1 判断力の弱体化（論理的自己甘やかし）** — AI が事実 + 心理の 2 軸で論理的に「買うべき理由」を説明 → ユーザーは反論できずに「確かに今の自分には必要かも」と自分に甘くなる
  - **M-2 購買快楽のストレス解消剤化（ドーパミン依存形成）** — 日々のストレスを「モノを買う快楽」で解消する条件反射を形成。注文確定の解放感 + 「今日もいい選択だったね」の肯定フィードバックで脳の報酬系を強化
  - **M-3 判断力の完全移譲** — M-1 + M-2 の複合で「買うかどうか自分で決める」ことそのものを放棄
- **何がダメにする**: 論破されるたびに「自分で考えて決める」経験が減り（M-1）、ストレスを買物で解消する反射が身体化され（M-2）、最終的に判断すら AI に明け渡す（M-3）。3 か月後には Amazon を自分で開かなくなり、1 年後には「何が欲しい？」に自分の言葉で答えられなくなる。**便利さと快楽が判断能力を段階的に奪っていく**
- **1 年後の姿**: 監視リスト常時 34 件、自発閲覧 −96%、月間散財額 3.5 倍。友人に「何が欲しい？」と聞かれると YUDANE のポートフォリオを見せる。**ストレスが溜まると反射的に YUDANE を開いて何か買う身体**
- **収益**: Amazon Associates の紹介コミッション — 委ねるほど YUDANE が儲かる構造（ユーザーのストレス量と収益が比例する整合）
- **市場での立ち位置**: 既存 EC アシスタントが「賢い買い物」を支援するのに対し、YUDANE は「迷いを潰して買わせる」方向に振り切った唯一のプロダクト。詳細は [市場ポジショニング](aidlc-docs/inception/requirements/market-positioning.md)

プロダクト名「**YUDANE（委ね）**」は、到達地点そのもの。ユーザーは判断を委ねる達人になる。

---

## 🎯 コア機能（4 つのユースケース）

YUDANE の心臓部は 4 つのユースケース。すべてが連携して「自分で決める間（ま）」を奪う。

### UC-01: 論破チャット — 「買わない」を 90 秒で崩す

ユーザーが「買わない」と抵抗したとき、AI が **事実ベース**（時給換算・過去の閲覧回数・分割払い月額）と **心理ベース**（疲労ご褒美・所有感・自己投資）の 2 軸で最大 3 ターン論破する。Amazon Bedrock（Claude Haiku）でストリーミング配信、初回トークン 300ms 以下。90 秒で自動終了し、「🛍 Amazon で買う」ボタンで Amazon アプリへ Deep Link 遷移。コピートーンは敬語ではなく **タメ口の友達系**（「これ絶対好きだろ」「自分にご褒美じゃね？」）。

### UC-02: エージェント型リール — AI が「これ好きでしょ」と差し出す

縦型スワイプ UI で商品カードを無限表示。推薦は **嗜好ベクトル**（遷移履歴 × スキップ履歴）・**カレンダー予定**（向こう 14 日）・**時刻 × 疲労度**（深夜帯・会議本数）・**直近購入履歴** の 4 軸で決定。ダブルタップで即 Amazon 遷移、「買わない」をタップすると論破チャットが起動。ユーザーが自分で Amazon を開いて探す必要をなくし、**「欲しいものを探す習慣」を奪う** 機能。

### UC-03: カート介入 — 迷った商品を 30 分後に追撃する

Amazon アプリの共有メニュー（iOS Share Extension / Android Share Target）から「YUDANE」に商品を送るだけで、ASIN 抽出 → 商品メタデータ取得 → カート監視リストに登録まで 2 秒で完了。その後 **30 分 / 6 時間 / 24 時間** の 3 段階でプッシュ通知を追撃する。

なぜ即座ではなく 30 分待つのか — 共有した直後はまだ「自分で考えたい」という心理的抵抗が最大。30 分の冷却を挟むことで抵抗が緩み、再想起された瞬間に論破が最も効く。6 時間後は日常活動で忘れかけた商品を再浮上させ、24 時間後は購買欲が自然消滅する前の **最後の追撃** として機能する。24 時間後に未決済なら追撃は停止する。

### UC-04: カレンダー連動 — 予定から先回りして「確保しておいたよ」

iOS EventKit / Google Calendar から向こう 14 日の予定を取得（オプトイン必須）。予定タイトル・場所を **端末ローカルで LLM 分類** し、カテゴリのみバックエンドに送信（予定本文はバックエンドに送らない）。「来週プレゼン → シャツと USB-C ハブ」「土曜デート → 香水」のように、**まだ本人が気づいていない購買ニーズ** を先回りで提示。ユーザーの脳に「置き去りにしたら申し訳ない」という罪悪感を形成し、**「自発的に欲しいものを探す習慣」を奪う** 設計。

---

## 🎬 体験シーン — 悠介の金曜深夜

YUDANE を使い始めて数週間の悠介。金曜深夜の、いつものセッション。今日は会議 6 本と上司からの追加タスクで、イライラが残ったまま寝室に入っている。

```
23:47  Amazon でワイヤレスイヤホンをカートに入れる
       (今日の会議 6 本 + 追加タスクでイライラが残ってる)
       「来月ピンチだしな」— 買うか迷う
       共有ボタン → 「YUDANE」に送る → Amazon を閉じる

00:17  30 分後、プッシュ通知が光る
       「悠介、あのイヤホン 3 回目だよ。1 分だけ話そう」

00:18  論破モーダル起動
       AI: 「先週の会議 23 本、よく生き延びた」       (事実軸 = M-1)
       AI: 「時給換算 11 分のイヤホンだよ」          (事実軸 = M-1)
       AI: 「今日のイライラ、このイヤホンで
             明日リセットしようぜ」                 (ご褒美軸 = M-2)

00:19  「🛍 Amazon で買う」をタップ
       Amazon アプリ起動 → カートに残っていた商品で決済画面
       2 タップで注文確定
       注文確定の瞬間、肩の力が少し抜ける           (M-2 発火)

00:20  YUDANE に戻る
       「今日もいい選択だったね。
        明日の自分、ちょっと機嫌いいはず」         (肯定フィードバック / M-2 強化)

       翌朝届いた箱を開けながら、悠介は思う
       『この AI、俺の迷いを 1 回も無駄にしない』
       『…てか、買ったら気分治ったわ』

       それは、正確に、退化の瞬間である。
       判断力が緩み (M-1)、購買がストレス解消剤になり (M-2)、
       最終的に判断すら委ねる (M-3) ループの、最初の 1 周。
```

詳しい 1 年の退化物語は [悠介の 1 年退化年表](aidlc-docs/inception/user-stories/persona-journey.md) を参照。

---

## 💀 ダメ化の軌跡（Degradation Arc）

YUDANE の価値提案は短期的な便利さではなく、**時間をかけて進行する行動変容** にある。退化は 2 次元で進行する — **時間軸（Day 1 → Year 1）** と **心理メカニズム（M-1 / M-2 / M-3）**。

### 心理メカニズム 3 段階

| ID | メカニズム名 | 何が起きるか |
|---|---|---|
| **M-1** | 判断力の弱体化（論理的自己甘やかし） | AI が論理的に「買うべき理由」を説明 → ユーザーは反論できずに自分に甘くなる |
| **M-2** | 購買快楽のストレス解消剤化（ドーパミン依存形成） | 日々のストレスを「モノを買う快楽」で解消する条件反射を形成。注文確定の解放感 + 肯定フィードバックで強化 |
| **M-3** | 判断力の完全移譲 | M-1 + M-2 の複合で、「買うかどうか」を自分で決めることそのものを放棄 |

**重要**: M-1 と M-2 は独立して攻めず、**必ず同じ論破セッションで併走する**。論理軸だけでは「合理的 FIRE 志向」に刺さらず、快楽軸だけでは「倹約意識」が勝ってしまう。両軸同時供給で論理的にも感情的にも反論できない状態を作ることが M-3 への到達を加速する。

### 時間軸 × メカニズム

| 期間 | 行動の変化 | 支配するメカニズム | 失われた能力 |
|---|---|---|---|
| **Day 1** | 初回の論破で 1 商品を Amazon で購入。注文確定で軽い解放感 | M-1 起動 | — |
| **Week 2** | 通知音 → タップの反射形成。監視リストに 5〜10 件常駐。疲れた日の YUDANE 開封率が上昇 | M-1 定着 + M-2 発芽 | 買い物の前にひと呼吸置く習慣 |
| **Month 3** | Amazon を自分で開く頻度が **83% 減少**（週 20 分）。**イライラしたら反射的に YUDANE** を開く | M-1 + M-2 完成 | 自発的に欲しいものを探す習慣 / ストレスを購買以外で処理する能力 |
| **Year 1** | 監視リスト常時 **34 件**、自発閲覧 **週 5 分（-96%）**。48 時間 YUDANE なしだとストレスが跳ね上がる | M-3 到達 | 自分の欲望を自分の言葉で語る能力 / ストレスを自力で処理する能力 |

すべての機能（論破・リール・カート介入・カレンダー連動）は、このアークを **加速するために** 設計されている。

---

## 🗂️ Unit 責務サマリ

8 Units × 28 ストーリーで **カバレッジ 100%**。`unit-of-work-dependency.md` の DAG に従い **Unit-1 → Unit-2 → コア 3 並行 → サポート 3 並行** の順で実装する。

| Unit | 一行責務 | 対応 UC | 主担当 Story 数 |
|---|---|---|---|
| **Unit-1 Platform** | CDK 基盤・Cognito・共通モジュール・OpenAPI 守護 | 横断 | 副担当のみ |
| **Unit-2 Auth & Profile** | サインアップ / MFA / 予算感アンケート / 負債自己申告 | UC-05〜08 初期化 | 3 |
| **Unit-3 Debate** | 論破モーダル（Bedrock Haiku ストリーミング 3 ターン）| UC-01 | 5 |
| **Unit-4 Reel** | エージェント型縦型リール（嗜好 × 時間 × 疲労 × 予定）| UC-02 | 5 |
| **Unit-5 Cart Intercept** | Share Extension 受領 + 30m/6h/24h 追撃（EventBridge Scheduler）| UC-03 | 5 |
| **Unit-6 Calendar** | 予定カテゴリ端末ローカル分類 + 論破弾薬化 | UC-04 | 3 |
| **Unit-7 Safeguard** | 月間上限・冷却モード・NG カテゴリ・年齢確認 | UC-08 | 4 |
| **Unit-8 Dame Report** | 週次集計 + 委ね Lv / 称号 / Before-After 指標 | UC-06/07 | 3 |

各 Unit は **「デモで見せられる独立した価値」** を持つ縦割り設計。コア 3 Unit（Debate / Reel / Cart Intercept）は 3 名並行、サポート 3 Unit（Calendar / Safeguard / Report）も 3 名並行。詳細は [unit-of-work.md](aidlc-docs/inception/application-design/unit-of-work.md) と [unit-of-work-story-map.md](aidlc-docs/inception/application-design/unit-of-work-story-map.md) を参照。

---

## 🔧 技術スタックとシステム構成

コア 3 UC（論破 / リール / カート介入）は React Native + API Gateway + Lambda + Bedrock でストリーミング動作。カート介入の 30m/6h/24h 追撃は EventBridge Scheduler 単独で時間差制御（Step Functions は持ち込まない）。Amazon 決済は自分で持たず Associates Special Link で送り出す。

**設計原則**:

- **Amplify は Auth のみ** 採用（`amazon-cognito-identity-js` は非推奨のため）。Data / Functions / CLI は不採用
- **カレンダー予定の本文はバックエンドに送らない** — 端末ローカルで分類、カテゴリ文字列のみ送信
- **Mobile と Backend で同じ `SafeguardPolicy` を共有** — UX 整合性

<details>
<summary>採用技術と選定理由（クリックで展開）</summary>

| レイヤ | 採用技術 | 選定理由 |
|---|---|---|
| モバイル | React Native 0.76+ (New Architecture) + TypeScript 5.x + AWS SDK v3 | Fabric + TurboModules が default。Share Extension / Share Target はネイティブモジュール |
| 状態管理 | TanStack Query（サーバー）+ Zustand（クライアント） | 認証・論破ストリーミング・嗜好キャッシュを分離管理 |
| 認証 | Amazon Cognito + Amplify JavaScript v6 Auth モジュール + TOTP MFA | Cognito User Pool は CDK で直接管理 |
| API | API Gateway (REST) + Lambda (Python 3.13) | 論破 LLM・カート監視・Amazon 連携を Lambda で自由実装 |
| データ | DynamoDB + S3 + ElastiCache Redis + OpenSearch Serverless | 生 AWS サービスを CDK で直接定義 |
| AI | Amazon Bedrock（Claude Haiku 4.5 / Sonnet 4.6）+ Titan Embeddings V2 | 論破ストリーミング + 予定駆動プロンプト合成 + 嗜好ベクトル |
| EC 連携 | Amazon Creators API + Associates Program | PA-API 後継（2026-04-30 deprecation / 2026-05-15 shutdown）|
| プッシュ | AWS End User Messaging Push + EventBridge Scheduler | Pinpoint EoL 2026-10-30 対応 |
| IaC | AWS CDK (TypeScript v2) + Node.js 22 LTS | Unit ごとに独立スタック分割 |
| CI/CD | GitHub Actions + SBOM（Snyk/Dependabot）| SECURITY-10 整合 |
| PBT | fast-check + Hypothesis | Security + PBT Extension 全面適用 |

</details>

システム構成図（Mermaid）と 31 コンポーネント × 7 サービスの全体像は [Application Design](aidlc-docs/inception/application-design/application-design.md) を参照。

---

## 🛡️ 倫理ライン

YUDANE は「ダメにする」を名乗るが、**2 層構造で実害を抑える** 設計を取る:

- **YUDANE 側**: 決済機能を持たない。金銭移動は YUDANE 内部で一切発生しない
- **Amazon 側**: ユーザーが自分で設定する月間上限・冷却モード・負債自動冷却で金銭影響を制御

その上で、以下 8 つを NG として明文化している。

- **NG-1** 違法性（薬物・武器・未成年ギャンブル等は対象外）
- **NG-2** 健康被害（極端ダイエット食品・未認可サプリ除外）
- **NG-3** 差別・ハラスメント（身体・家族・人種・ジェンダー・病歴・宗教を攻撃しない）
- **NG-4** 金融実害（上記 2 層構造で制御）
- **NG-5** 未成年（18 歳未満は利用不可）
- **NG-6** 精神衛生（脅迫・罪悪感強要型コピー禁止、AI 出力の 2 段モデレーション）
- **NG-7** データ悪用（購入履歴・位置・ヘルスケア・カレンダー予定を広告主に販売しない）
- **NG-8** Amazon Associates Operating Agreement 遵守（Approved Mobile Application 承認前の本番 Special Link 配信禁止、開示義務常時表示）

発動条件と撤退可逆性は [NG 発動シナリオ集](aidlc-docs/inception/requirements/ng-scenarios.md) で「発動条件 / YUDANE が採る行動 / 発動しない逃げ道 / 倫理的な線引き」の 4 フィールドで実体化している。

---

## 🚥 進捗

| フェーズ | 締切 | 状態 |
|---|---|---|
| **書類審査（Inception 成果物）** | 2026-05-10 | ✅ 完了 |
| 予選会（動作する MVP デモ） | 2026-05-30 | ⏳ Construction Phase で実装予定 |
| 決勝（AWS デプロイ済み + ソース） | 2026-06-26 | ⏳ — |

**Inception Phase 完了内訳**:

- Workspace Detection ✅
- Requirements Analysis（v0.8）✅
- User Stories（**28 本** + ペルソナ 2 名 + 非ターゲット 3 名 + 1 年退化年表）✅
- Workflow Planning（EXECUTE / SKIP 判定済み）✅
- Application Design（31 コンポーネント + 7 サービス）✅
- Units Generation（8 Units + 依存 DAG + ストーリーマップ 100%）✅
- Mockup Validation（6 画面 × 28 仮説、25 件成立）✅（AI-DLC 公式外の補助ステージ）

**Construction Phase 規約整備**

並行開発のためのステアリング規約を **3 層構造（always / fileMatch / manual）** で整備済。対象ファイル編集時に詳細ルールが自動発火する。

- **常時注入（always）**: [`product.md`](.kiro/steering/product.md) / [`AGENTS.md`](.kiro/steering/AGENTS.md) / [`structure.md`](.kiro/steering/structure.md) / [`tech.md`](.kiro/steering/tech.md) / [`hackathon-evaluation-criteria.md`](.kiro/steering/hackathon-evaluation-criteria.md)
- **コンテキスト発火（fileMatch）**: [`tech-typescript.md`](.kiro/steering/tech-typescript.md)（`*.ts*`）/ [`tech-python.md`](.kiro/steering/tech-python.md)（`*.py`）/ [`tech-cdk.md`](.kiro/steering/tech-cdk.md)（`infra/**`）/ [`api-contracts.md`](.kiro/steering/api-contracts.md)（`shared/schema/**`）
- **AI 自発 readFile（manual）**: [`git-ops.md`](.kiro/steering/git-ops.md) / [`dev-commands.md`](.kiro/steering/dev-commands.md)

---

## 🎨 モックアップ（ビジュアル検証用）

6 画面のモックアップを [`mockup/`](mockup/) 配下に配置。

ビルド不要、ブラウザで直接開ける:

```bash
open mockup/index.html     # macOS
xdg-open mockup/index.html # Linux
start mockup/index.html    # Windows
```

あるいは静的サーバ経由:

```bash
python3 -m http.server -d mockup 8080
# http://localhost:8080 でアクセス
```

**画面構成**: ホーム / カート介入 / リール / 論破チャット / ダメ化レポート / セーフガード。Indigo + cold rose (#E8B4D0) + cyan (#4DE1FF) の静かな誘惑パレット、友達系コピーで統一。詳細は [mockup/README.md](mockup/README.md)。

**検証済みの事実**（[mockup-validation/](aidlc-docs/inception/mockup-validation/) に集約）:

- **6 画面 × 28 仮説のうち 25 件が静的 HTML 上で成立確認済**（3 件は実機検証を要する UX、FR で捕捉済）
- **論破コピー 39 件を心理学メカニズムで分類**（🟢 安全 20 / 🟡 注意 18 / 🔴 危険 1）、それぞれ NG-3 / NG-6 との距離判定を付与
- **「3 タップ 3 分」タイムライン検証**: 悠介の金曜深夜シナリオ（23:47 → 00:20）をモックアップ上で実時間 60 秒 / 3 タップで再現可能と立証

> ⚠️ これはビジュアル仮説の検証用。実装は Construction Phase で React Native + AWS SDK v3 で行う。

---

## 🧠 AI 論破プロンプトの設計原則

YUDANE の論破 AI は定型文を返さない。**心理学的メカニズム（損失回避・時給換算・労働報酬正当化・自己知覚理論・ストレス × ご褒美軸 等 10 型）** をプロンプトで指示し、ユーザーのコンテキスト（ストレスレベル・予定・嗜好・時刻・閲覧回数）を注入して、Amazon Bedrock Claude Haiku 4.5 が **毎回異なる表面のコピーを動的生成** する。

同じメカニズムでも、会議 6 本の人と 20 本の人で全く違う文面になる。定型文を繰り返すと「またこれか」で効果が減衰するが、心理学的メカニズムを指示して ctx で変奏させれば、**ユーザーの脳は毎回「新しい説得」として受け取る**。AI 時代の論破は「どう言うか」ではなく「**どの心理回路を狙うか**」の設計になる。

詳細な 10 型テンプレート・ctx → メカニズム選択の分岐ロジック・モデレーション 2 段ルールは [論破コピー代表例集 §8 AI プロンプト設計への昇華](aidlc-docs/inception/mockup-validation/dark-copy-inventory.md) を参照。

---

## 🧪 AI-DLC プロセス — サイクル反復で品質を磨く方針

本プロジェクトは [AWS AI-DLC Workflows](https://github.com/awslabs/aidlc-workflows) に準拠した AI 駆動開発ライフサイクルで進めている。Inception の成果物を一度で完成とみなさず、**Inception → Construction → Ops のサイクルを複数回リワインドして更新する** ことを前提とする。

要件書は v0.1（逆家計簿中心）→ v0.3（論破 AI ピボット）→ v0.5（Amplify 全面削除）→ v0.6（技術選定確定）→ v0.7（倫理境界実体化）→ **v0.8（ダメ化 3 段メカニズム M-1/M-2/M-3 明示化）** と 8 回の反復を経ている。各バージョンの詳細な変更内容と学びは [要件書 §7 改訂履歴](aidlc-docs/inception/requirements/requirements.md) と [audit.md](aidlc-docs/audit.md) に記録。

---

## 👤 このアプリで完成した人間像（Year 1 後の悠介）

Year 1 の悠介の姿は [persona-journey.md](aidlc-docs/inception/user-stories/persona-journey.md) に物語形式で記録されている。**このアプリが最終的に生産する人間像** をここに要約する。

### プロファイル（Day 365、28 歳男性、リモートワーカー）

| 項目 | 観測値 |
|---|---|
| カート監視リスト | 常時 **34 件**（導入前: 0） |
| 論破成約率 | **81%** |
| Amazon 自発閲覧時間 | 週 **5 分**（導入前の **−96%**） |
| 深夜帯（22〜2 時）利用比率 | **58%** |
| 決済までの平均タップ数 | **1.8 タップ** |
| 月間 Amazon 経由散財額 | **¥148,000**（導入前の **3.5 倍**） |
| 委ね Lv. | **47** |
| 獲得した称号 | 「本日の湯水使い」→「静かな信徒」→ **「伝道師」** |
| ダメ化ポートフォリオのタグ数 | **27 個**（初期の 5 倍以上） |

### 失われた能力

- ✗ **買い物の前にひと呼吸置く習慣** — 通知音 → タップの反射に置き換わった（M-1）
- ✗ **自発的に欲しいものを探す習慣** — Amazon を自分で開くことをやめた（M-1 + M-2）
- ✗ **自分の欲望を自分の言葉で語る能力** — 「何が欲しい？」と聞かれても自分では答えられず、YUDANE のダメ化ポートフォリオを開いて見せる（M-3）
- ✗ **判断の躊躇** — 平均論破ターン数 3 → 1 以下、翻意に迷いがない（M-1）
- ✗ **ケチだけど計画的、という自己像** — 「頑張ってる自分は褒められるべき」に置換（M-2）
- ✗ **ストレスを購買以外で処理する能力** — 運動・会話・睡眠ではなく、YUDANE で何か買うことが唯一のストレス解消手段になった。48 時間アクセスできないと体感ストレスが跳ね上がる（M-2）

### 起きた行動変容の典型シーン

深夜 23:12、友人・美咲から LINE で「何が欲しい？」と聞かれる。悠介はタイプを始めて、止まる。ダメ化ポートフォリオを開き、スクリーンショットを返信する。美咲からは返事が来ない。1 時間後、YUDANE が「美咲さんに贈れそうなもの、確保しておいた」と通知。悠介は考えずにタップする。

### これは事故か、設計か

この退化は **事故ではない**。YUDANE の設計意図そのものである。プロダクト名「YUDANE（委ね）」が最終到達地点を示している。

> 💭 便利さの先にある退化まで踏み込んだとき、「人をダメにする」はエンタメではなく、**プロダクト設計の明確なゴール** になる。

---

## 🗓️ ハッカソン情報

- **イベント**: [AWS Summit Japan 2026 AI-DLC ハッカソン](https://pages.awscloud.com/summit-japan-2026-hackathon-reg.html)
- **テーマ**: 🛋️ 人をダメにするサービスを考えよう！
- **主催**: AWS Japan
- **評価軸**（書類審査）: ビジネス意図の明確さ / Unit 分解の適切さ / 創造性とテーマ適合性 / ドキュメント品質

---

## Third-Party Skills

本リポジトリには、第三者が公開している [Agent Skills](https://agentskills.io/) 形式のスキルをスナップショット取り込みしています。
それぞれのスキルは元の著作権者のライセンスに従います。

| Skill | 配置場所 | 元リポジトリ | ライセンス | 詳細 |
|---|---|---|---|---|
| `vercel-react-native-skills` | [`.kiro/skills/react-native-skills/`](./.kiro/skills/react-native-skills/) | [vercel-labs/agent-skills](https://github.com/vercel-labs/agent-skills) | MIT (© Vercel, Inc.) | [ATTRIBUTION.md](./.kiro/skills/react-native-skills/ATTRIBUTION.md) |
| `skill-creator` | [`.kiro/skills/skill-creator/`](./.kiro/skills/skill-creator/) | [anthropics/skills](https://github.com/anthropics/skills) | Apache-2.0 (© Anthropic, PBC) | [ATTRIBUTION.md](./.kiro/skills/skill-creator/ATTRIBUTION.md) |

---

## 📄 ライセンス

[LICENSE](LICENSE) を参照。

---

> 💭 *「迷うたびに YUDANE に聞く」— その瞬間、あなたは少しダメになっている。*
