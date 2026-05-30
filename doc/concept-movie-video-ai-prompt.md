# YUDANE コンセプトムービー 動画生成プロンプト集（30秒 / 全編AI生成 / 案A）

> 前提は実アプリ画面を使わない**全編AI生成**、ナレーターは**ひろゆき氏本人ではない「論破系の口調に寄せた架空キャラ（声のみ）」**（[骨子 §3.0](presentation-prelim-skeleton.md) 案A）。
> 構成は [骨子 §3.2](presentation-prelim-skeleton.md) の流れを、短尺クリップ単位に合わせ **6秒×5ショット = 30秒** に再設計した。

---

## 0. 先に読む：作成上の制約と回避策

1. **縦9:16を直接出せず横16:9が標準の場合が多い。**
   → 16:9 で生成し、**編集で中央を 9:16 にクロップ**して縦ショートに仕上げる。各プロンプトは被写体（手元のスマホ・画面）を**画面中央**に置く構図なので、左右を切っても成立する。縦が不要なら 16:9 のまま使ってもよい。
2. **1クリップは数秒単位／1プロンプトに文字数上限がある場合が多い。** 本書は **5ショット（各約6秒）= 30秒**、各プロンプトは短め（目安512文字以内）に収めた。長尺を1プロンプトでまとめられるツールならつなげてもよい。
3. **否定語（no / not / without 等）は避ける。** 否定が効かず逆効果になることがある（「バナナの無い果物かご」→バナナが出る）。「文字を出さない」「ロゴなし」等は本文に書かず、**除外語は §2.5 のネガティブ指定にまとめる**。
4. **カメラ移動はプロンプトの末尾に置く**と効きやすい。本書は各ショット末尾にカメラ指示を置いた。
5. **命令形でなく描写（キャプション）形式**で書く。「〜してください」ではなく「すでに存在する映像を説明する」文体。
6. **英語の方が安定する場合が多い。** 本文は英語、登場人物は `Japanese man` で固定。日本語プロンプトが必要なら用意できるが品質は落ちることがある。
7. **実在人物・実ブランドは出さない。** 人物は架空の日本人男性。Amazon 等のロゴ・名称は描かない（ネガティブ指定でも抑制）。本番投入前に NTT DOCOMO 社内法務の確認を取る。

---

## 1. 共通スタイル語彙（各ショットに織り込み済み）

文字数を抑えるため独立の「STYLEブロック」は付けず、各プロンプトに最小限で埋め込んでいる。トーンの核は次の語彙：

`photorealistic, calm room with soft low light, light from a smartphone screen, deep indigo and blue tones, soft rose-pink and light cyan glow, shallow depth of field, gentle film grain, calm mood, a young Japanese man in his late twenties (fictional, original character), centered composition`

---

## 2. ショット別プロンプト（5本 / 各6秒 / 各512字以内 / 英語）

> ⚠️ **動画生成AIに貼るのは、この §2 の英語ブロック「だけ」**。次のものは絶対に貼らない（安全フィルタで弾かれる原因）:
> - §3 のナレーション原稿（「時給換算11分…」等の説得文＝操作的とみなされる）
> - §3.0 / §6 の権利説明（**実在人物名「ひろゆき」**、「人をダメにする／浪費に追い込む／ドーパミン依存」等の語を含む）
> - このマークダウン全体やテーマ説明文
> 下記プロンプトは、人物を夜の室内に密着で描く表現（性的表現と誤判定されやすい）を避けた**中立な視覚描写のみ**の版に修正済み。

> 使い方: 各ブロックをそのまま1ショットの prompt 欄（手動/storyboardモード）に貼る。5ショットを順に並べて30秒の動画にする。

**ショット1（0–6秒）— 迷う指**
```
A young Japanese man's hand holds a smartphone in a calm room with soft low evening light, his face partly lit by the screen. The screen shows a simple online shopping cart of abstract glowing shapes. His thumb hovers as he thinks it over, with a calm thoughtful look. Deep indigo and blue tones, soft rose-pink and light cyan glow, photorealistic, shallow depth of field, gentle film grain, calm mood, centered composition. Slow gentle push-in.
```

**ショット2（6–12秒）— 40分の逡巡（早回し）**
```
A young Japanese man in a calm room with soft low light taps through a simple shopping app, adding an item to a cart, going back, and scrolling again, looking thoughtful and undecided. The soft screen light gently shifts on his face while a wall clock in the background advances quickly. Deep indigo and blue tones, soft rose-pink and cyan glow, photorealistic, shallow depth of field, film grain, calm mood, centered composition. Gentle time-lapse cutting.
```

**ショット3（12–18秒）— 30分後の通知**
```
A calm quiet room with soft low light. A young Japanese man's smartphone screen dims, then a single message notification appears and glows softly, spreading gentle rose and cyan light across the room as he turns toward it with mild curiosity. Deep indigo and blue tones, photorealistic, shallow depth of field, gentle film grain, calm mood, centered composition. Slow gentle push toward the glowing phone.
```

**ショット4（18–24秒）— 論破の畳みかけ**
```
An over-the-shoulder view of a young Japanese man's smartphone. Simple glowing message bubbles of abstract shapes appear and rise on the screen one by one, each a little brighter. His expression gently shifts from unsure to convinced, a soft thoughtful look, as soft cyan light grows on his face. Deep indigo and blue tones, rose-pink and cyan glow, photorealistic, shallow depth of field, film grain, calm focused mood, centered composition. Slow steady push-in.
```

**ショット5（24–30秒）— タップ → 弛緩 → 暗転ロゴ余韻**
```
A close-up of a young Japanese man's hand gently tapping a softly glowing button on a smartphone; the screen brightens with a soft warm bloom of light, and he looks calm and at ease. The scene then transitions slowly to a deep indigo background with a single soft rose-and-cyan point of light in the center. Photorealistic, shallow depth of field, gentle film grain, calm mood, centered composition. Close-up start, then a slow fade to a calm dark frame.
```
→ **編集でこの末尾にロゴ「YUDANE」とテロップ「委ねるほど、ダメになる。」を後乗せ。**

### 2.5 negativeText パラメータ（5ショット共通）

否定語は使わず、除外したい要素を**名詞で列挙**する（ツールの「ネガティブプロンプト」欄に設定）。

```
on-screen text, captions, subtitles, watermark, logo, brand logo, readable interface text, extra fingers, distorted hands, blurry, low quality
```

### 2.6 それでもブロックされる場合：人物を出さない超セーフ版

人物（顔・手）の描写自体が弾かれる、または人物生成が制限されている場合は、**人物を出さず「スマホ・光・抽象画面・モノ」だけ**で構成すると通りやすい。ナレーションと編集のテロップで物語を補う前提。

**ショット1（代替）**
```
A smartphone resting on a table in a calm room with soft low light. The screen shows a simple online shopping cart made of abstract glowing shapes. The cursor or highlight hovers and pauses, suggesting hesitation. Deep indigo and blue tones, soft rose-pink and light cyan glow, photorealistic, shallow depth of field, gentle film grain, calm mood, centered composition. Slow gentle push-in on the screen.
```

**ショット3（代替）**
```
A calm dim room with a smartphone on a table. The screen lights up with a single soft message notification, spreading a gentle rose and cyan glow across the surrounding surface. Quiet and still. Deep indigo and blue tones, photorealistic, shallow depth of field, gentle film grain, calm mood, centered composition. Slow gentle push toward the glowing screen.
```

**ショット5（代替）**
```
A smartphone screen showing a soft glowing confirmation bloom of light, then the view transitions slowly to a deep indigo background with a single soft rose-and-cyan point of light in the center. Calm and quiet. Photorealistic, shallow depth of field, gentle film grain, calm mood, centered composition. Slow fade to a calm dark frame.
```

> ショット2・4も同様に「手元・顔」を外し「スマホ画面と光の変化」に置き換えれば作れる。必要なら全5本の人物なし版を出す。

---

## 3. ナレーション原稿（別TTS or 肉声で。映像に後乗せ）

映像生成側で音声は付けない前提。論破系の口調に寄せた**架空ナレーター**（ひろゆき氏本人の名前・自己同定は入れない）の原稿を、VOICEVOX 等の商用利用可音声かメンバー肉声で当て、編集で合わせる。総約130字。

| 対応ショット | 秒 | ナレーション |
|---|---|---|
| 1 | 0:00–0:05 | あの、それ……まだ買うか迷ってるんすか？ |
| 2 | 0:05–0:11 | 40分迷うくらいなら、AIに任せた方が早くないですか？ |
| 3 | 0:11–0:17 | ほら、30分後。ちゃんと迎えに来ますよ。 |
| 4 | 0:17–0:24 | 時給換算11分っすよ。会議23本こなした人が、それくらい自分に使えないって、逆に変じゃないですか？ |
| 5 | 0:24–0:30 | はい、買えた。気分も、ちょっと治った。……それ、"自分で決めるの"、やめた瞬間ですけどね。 |

---

## 4. 仕上げ（編集）設定

- 生成が 16:9 の場合、**編集で中央を 9:16 にクロップ**して縦ショート化（被写体は中央寄せ済み）。縦が不要なら 16:9 のまま。
- 連結: ショット1→5 をカット繋ぎ。ショット3の暗転とショット5の暗転でリズムを作る。
- テロップ（後乗せ・1カット1ワード）: 「まだ迷ってるの？」→「30分後、追撃」→「事実×感情、同時に」→「2タップで確定」→ ロゴ＋「委ねるほど、ダメになる。」
- ナレーション（§3）と BGM（軽快＋皮肉っぽいロイヤリティフリー）を重ねる。ショット5末で BGM を抜いて余韻。
- 文字・ロゴ・ブランドは全て編集で管理（生成映像には入れない）。
- 同じプロンプトでも乱数シードを変えると結果が変わるので、複数回生成して良いテイクを選ぶ。

---

## 5. 補足

- ひろゆき氏本人の声・名前・肖像は使わない（[骨子 §3.0](presentation-prelim-skeleton.md) の案A）。ナレーターは声のみの架空キャラ、映像の人物も架空の日本人男性で実在人物に似せない。
- 日本語プロンプトが必要な場合は別途用意可能だが、崩れやすいため英語版を推奨する。
