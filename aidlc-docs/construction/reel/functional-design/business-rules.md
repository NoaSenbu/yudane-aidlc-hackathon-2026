# Unit-4 Reel — Business Rules

> Unit-4 Reel の**ルール・定数・制約**を一覧化。実装・テストの判定基準となる。
> 参照: [domain-entities.md](./domain-entities.md) / [business-logic-model.md](./business-logic-model.md) / [Unit-1 business-rules.md](../../unit-1-platform/functional-design/business-rules.md) / [API 契約ガバナンス](../../../../.kiro/steering/api-contracts.md)
> 確定方針: Q1=X（MVP は購入履歴ベース関連商品）/ Q2〜Q10=A / CL-1=A / CL-2=A / CL-3=A

---

## 1. 推薦ルール（B-03、ALG-RANK、CL-1/CL-2=A）

| ID | ルール |
|---|---|
| REEL-RANK-01 | MVP の候補生成は **購入履歴ベースの関連商品**（直近購入のカテゴリ/ブランド一致 + 共購買ヒューリスティック）。Titan Embeddings + OpenSearch ベクトル検索は MVP で使わず決勝で導入（[B-204](../../../../doc/backlog.md)） |
| REEL-RANK-02 | リランクは **決定論的な重み付き加算スコア**（純関数）。同一 `(ctx, weights, 候補集合)` → 同一順位。同点は `asin` 昇順で安定ソート |
| REEL-RANK-03 | スコア内訳 `components`（relatedness / timeBoost / stressBoost / calendarMatch / recencyDecay）の総和が最終 `score` に一致（検算可能） |
| REEL-RANK-04 | `stressFactor`: low=0 / mid=0.5 / high=1.0（ストレス係数、Q3=A） |
| REEL-RANK-05 | `timeBoost` は `timeBucket.isLateNight`（22:00〜02:00）でのみ加点 |
| REEL-RANK-06 | `calendarMatch` は `calendarCategory` が存在し商品が一致する場合のみ加点。不在時は 0（通常推薦にフォールバック、Q10=A） |
| REEL-RANK-07 | NG カテゴリ（`safeguardFlags.ngCategories`）該当商品は **候補生成段で除外**。リランク以降に現れない（US-SAFE-03 副担当） |
| REEL-RANK-08 | 既出商品（`cursor.seenCardKeys` に含まれる `asin`）は再提示しない（Q9=A） |
| REEL-RANK-09 | cold start（`purchaseHistory` 空）はオンボ嗜好（ブランド/カテゴリ）をシードに候補化。不足はキュレーション固定リストで補完（CL-3=A） |
| REEL-RANK-10 | **遷移直後クールダウン**: 直近 Amazon 遷移から **10 分以内**は同一カテゴリの商品を候補から除外する（FR-AUTH-03）。`recentTransitions`（カテゴリ + 遷移時刻）を入力に、NG カテゴリ除外と同じ候補フィルタ層で適用 |

### 設定値カタログ（推薦、チューニング可能）

| パラメータ | 既定値 | 備考 |
|---|---|---|
| `CANDIDATE_POOL_SIZE` | 50 | 候補生成段で取得する件数 |
| `LIMIT` | 10 | 1 ページのカード数（FR-REEL-01） |
| `POST_TRANSITION_CATEGORY_COOLDOWN_SECONDS` | 600（10 分） | 遷移直後の同カテゴリ抑制（FR-AUTH-03、REEL-RANK-10） |
| `weights.relatedness` | 1.0 | 購入履歴関連度（主スコア、CL-1） |
| `weights.timeBoost` | 0.6 | 深夜時間帯ブースト |
| `weights.stressBoost` | 0.5 | ストレス係数の重み |
| `weights.calendarMatch` | 0.4 | カレンダー一致加点 |
| `weights.recencyDecay` | 0.3 | 直近表示の減衰（負方向） |

> 重みの最終値は NFR Design / 体感チューニングで調整。本表は機能設計時点の既定値。

---

## 2. 深夜ブーストルール（B-03、ALG-BOOST、Q2=A）

| ID | ルール |
|---|---|
| REEL-BOOST-01 | 発火条件は **複合トリガー**: ローカル時刻 22:00〜02:00 **かつ** ストレス `mid` 以上（Q2=A） |
| REEL-BOOST-02 | `quietWeek` または `cooldownOn` が true のときは **ブースト自体を抑止**（US-02-01 AC-4 / NG-6 / FR-FUNNEL-05） |
| REEL-BOOST-03 | ブースト枠の価格は平均価格帯の **1.5〜3.0 倍**の範囲内のみ採用（範囲外は不採用） |
| REEL-BOOST-04 | ブースト枠は最大 `BOOST_MAX_CARDS` 件、フィード先頭に配置し `origin='late-night-boost'` + 「頑張ったあなたへ」タグ付与 |
| REEL-BOOST-05 | ブーストは同一セッションで **1 回のみ**（`cursor.boostConsumed` で制御、Q9=A） |
| REEL-BOOST-06 | ブーストカードも NG カテゴリ除外・既出抑制の対象（REEL-RANK-07/08 を満たす） |

### 設定値カタログ（ブースト）

| パラメータ | 既定値 | 備考 |
|---|---|---|
| `LATE_NIGHT_START_HOUR` | 22 | 深夜帯開始（ローカル時刻） |
| `LATE_NIGHT_END_HOUR` | 2 | 深夜帯終了（翌 2 時） |
| `BOOST_PRICE_MIN_RATIO` | 1.5 | 高単価下限（平均比） |
| `BOOST_PRICE_MAX_RATIO` | 3.0 | 高単価上限（平均比） |
| `BOOST_MAX_CARDS` | 3 | 先頭挿入する最大ブースト件数 |

---

## 3. ストレスレベルルール（B-03、Q3=A）

| ID | ルール |
|---|---|
| REEL-STRESS-01 | ストレス推定は Reel と Debate（B-02）で **同一の共有純関数**を使用し判定が一致する（Q3=A、重複実装禁止） |
| REEL-STRESS-02 | 推定入力 `StressSignals` = 直近 7 日の会議密度・残業時刻分布・深夜帯利用回数・カレンダー連続予定数 |
| REEL-STRESS-03 | 出力は `low / mid / high` の 3 値のみ |
| REEL-STRESS-04 | クライアントから渡される `stress_level` は信用しない。サーバー側（共有関数）で算出する（SECURITY-08） |
| REEL-STRESS-05 | 共有関数の正本配置（shared / platform）は Member A と確定するまで backlog 管理（[B-203](../../../../doc/backlog.md)） |

---

## 4. 所有感ラベル / 推薦コメントルール（B-03、ALG-PITCH/LABEL、Q4=A）

| ID | ルール |
|---|---|
| REEL-LABEL-01 | ラベル/コメントは LLM 動的生成を第一とし、**固有の根拠を 1 文添える**（US-02-05 AC-2） |
| REEL-LABEL-02 | LLM 失敗・モデレーション拒否・重複時は決定論テンプレートにフォールバック（`source='template-fallback'`、Q4=A） |
| REEL-LABEL-03 | 同一ユーザーへの **直近 24h で同一 `text` の連続表示を禁止**（AC-3、ハッシュ照合でバリエーション担保） |
| REEL-LABEL-04 | カレンダー多忙度が高い場合「今週もよく戦ってるね。これ、自分へのご褒美」系へ切替（AC-4） |
| REEL-LABEL-05 | 深夜帯 × ストレス mid 以上の推薦コメントは疲労連動ブーストコピー（「今日の会議 6 本、よく戦った。ご褒美は当然じゃね？」型）を優先（FR-REEL-03 / M-2） |
| REEL-LABEL-06 | 出力モデレーションで NG-6（脅迫・罪悪感強要、「買わないとストレス悪化するよ」型）を除去 |
| REEL-LABEL-07 | 出力モデレーションで NG-3（身体・家族・人種・病歴・宗教への言及）を除去 |
| REEL-LABEL-08 | フォールバックでも `text` / `rationale` は必ず非空（フィードが崩れない） |

---

## 5. カタログルール（B-11、ALG-CATALOG、Q7=A）

| ID | ルール |
|---|---|
| REEL-CAT-01 | カタログアクセスは `ProductCatalogPort`（`getItemByAsin` / `searchItems`）経由に限定（直接 SDK 呼出禁止） |
| REEL-CAT-02 | Approved Mobile Application 承認前（書類審査・予選）は `DummyCatalogAdapter`（代表 1〜2 社の固定カタログ）を使用（§8 A-10 / FR-REEL-04） |
| REEL-CAT-03 | アダプタ切替は環境フラグ（環境変数/設定）で行い、関数内 if 分岐に埋め込まない |
| REEL-CAT-04 | キャッシュは両アダプタ共通のデコレータ層、TTL = `CREATORS_CACHE_TTL_SECONDS`（6h、Unit-1 設定値カタログと整合） |
| REEL-CAT-05 | 外部 API 失敗は `external-api.creators-unavailable`（DomainError）に変換。詳細を body に出さない（SECURITY-09） |
| REEL-CAT-06 | `DummyCatalogAdapter` は外部ネットワークに出ない（オフラインで決定論的に動作） |

---

## 6. 遷移・EXP・Safeguard ルール（B-13、ALG-TRANSITION、Q6=A）

| ID | ルール |
|---|---|
| REEL-TR-01 | 遷移記録は冪等。冪等キー = `(userId, clientTransitionId)`。重複時は再加算せず `duplicate=true`（PBT-04） |
| REEL-TR-02 | EXP は 1 遷移につき **+1**（US-02-02 AC-4） |
| REEL-TR-03 | 遷移は **Safeguard ゲート通過後のみ**記録（FR-FUNNEL-05）。`block` 時は記録せず該当 reasonCode で 409（reel.yaml と整合） |
| REEL-TR-04 | `warn` は遷移を止めない（200 + warning ヘッダ、NG-6 罪悪感強要回避、Unit-1 SG-07 と整合） |
| REEL-TR-05 | 月間遷移カウント（`SafeguardStates.transitionCountMonth`）の更新は記録と原子的（同一トランザクション/条件付き書き込み） |
| REEL-TR-06 | `userId` は JWT `sub` と一致を検証（SECURITY-08）。不一致は `auth.idor`（403、Unit-1 REQ-05 と整合） |
| REEL-TR-07 | 遷移時に EXP +1 を B-13 が同期付与（Achievements、Unit-2 スキーマ、`ExpAwardDto` 返却）。遷移ログは B-08 PreferenceVectorUpdater が日次バッチで集計し嗜好ベクトル学習に反映（UC-05 連動） |
| REEL-TR-08 | 遷移記録時に `reel.amazon_tap` テレメトリを送出（PII を含めない、Unit-1 TEL-02 と整合） |

---

## 7. Special Link 生成ルール（B-10、ALG-LINK、Q8=A / NG-8）

| ID | ルール |
|---|---|
| REEL-LINK-01 | Special Link は ASIN + Associates タグ（+ user 単位 commission サブタグ）から**純関数**で生成（同一入力→同一 URL） |
| REEL-LINK-02 | 生成 URL は AsinExtractor（S-01）で逆抽出して同一 ASIN に戻る（PBT-02 round-trip） |
| REEL-LINK-03 | 遷移先が Amazon であることを不明瞭にする**短縮 URL を使用しない**（NG-8 / Associates Operating Agreement / US-03-04 AC-5） |
| REEL-LINK-04 | Approved Mobile Application 承認前: `dev` = 仮リンク / `prd` = 遷移ブロック（`blocked=true`、US-03-04 AC-4 / §8 A-10） |
| REEL-LINK-05 | Associates として活動している旨の開示（設定画面/オンボ）は Unit-2 が常時表示（FR-PROFILE-04 / NG-8、Reel は遷移のみ担当） |

---

## 8. ジェスチャー・遷移ガードルール（M-03、ALG-GESTURE、Q5=A）

| ID | ルール |
|---|---|
| REEL-GES-01 | 左スワイプは水平移動 **≥60px** で確定 → 論破モード遷移（FR-DEBATE-01 trigger=`reel-refuse`） |
| REEL-GES-02 | 右スワイプは水平移動 **≥60px** で確定 → カート監視登録（Unit-5 B-04、楽観 UI + トースト） |
| REEL-GES-03 | ダブルタップは 2 タップ間隔 **≤350ms** で確定 → **必ず確認オーバーレイ**を経て Amazon 遷移（FR-REEL-05、オーバーレイ削除不可） |
| REEL-GES-04 | ジェスチャー優先順位: **double-tap > 水平スワイプ > vertical-scroll**（同時成立時、Q5=A） |
| REEL-GES-05 | 「論破不要」設定 ON のとき左スワイプは論破せずスキップトーストのみ（US-02-03 AC-3） |
| REEL-GES-06 | 同一カードへの左スワイプが **3 回超**でクールダウン適用、論破は起動しない（US-02-03 AC-4 / FR-DEBATE-05） |
| REEL-GES-07 | 確認オーバーレイで「やめとく」選択時はトースト「やめるの? もったいないじゃん」を出し同画面に留まる（US-02-02 AC-3 / §2.2 友達系トーン） |
| REEL-GES-08 | Amazon タップ後は「委ね EXP +1」「Amazon に送ったよ」トースト → 1.2 秒で自動的にダメ化レポートへ遷移（US-02-02 AC-4） |

---

## 9. ページング・既出抑制ルール（B-03、Q9=A）

| ID | ルール |
|---|---|
| REEL-PAGE-01 | ページングは **カーソルベース**。カーソルは既出カード集合 + ランキング位置 + ブースト消費フラグを不透明エンコード |
| REEL-PAGE-02 | カーソルはクライアントに **opaque**（base64url 等）で渡し、クライアントは解釈・改変しない |
| REEL-PAGE-03 | `limit` 既定 10（`LIMIT`）。同一セッションで同じ商品/ラベルの直近再表示を抑制（US-02-05 AC-3） |
| REEL-PAGE-04 | `seenCardKeys` は単調増加（ページング中に縮まない）、`boostConsumed` は false→true の一方向 |

---

## 10. カレンダー連動ルール（Unit-6 連携、Q10=A）

| ID | ルール |
|---|---|
| REEL-CAL-01 | `calendarCategory` は **任意入力**。存在すれば「○○ のためのエージェント提案」タグ + スコアブースト（REEL-RANK-06）に反映 |
| REEL-CAL-02 | 不在時は通常推薦にフォールバック（Reel 単体で完結、Unit-6 完成を待たない、Q10=A） |
| REEL-CAL-03 | Unit-6 未完成中は Unit-1 凍結 OpenAPI 契約に基づくスタブ/固定値で先行開発（Q6=A 契約凍結の恩恵） |
| REEL-CAL-04 | カレンダー本文は受け取らない。`category`（presentation/date/camping/other）のみ（FR-CAL-05 / NG-7、Unit-1 PII-09 と整合） |

---

## 11. API 契約整合（reel.yaml、Unit-1 凍結契約の非破壊拡張）

| ID | ルール |
|---|---|
| REEL-API-01 | Reel が詳細化するのは `shared/schema/paths/reel.yaml`（`getReel` / `recordAmazonTransition`）。**省略可能フィールドの追加のみ**（非破壊、Unit-1 API-03） |
| REEL-API-02 | 契約変更 PR は実装 PR と分離し先に merge（api-contracts.md §2 / git-ops.md §7、コア 3 Unit は Member A Approve 必須） |
| REEL-API-03 | `GET /v1/reel` は `cursor` / `limit` クエリ + `X-Correlation-Id`。レスポンスは ReelPage 相当（カード配列 + nextCursor） |
| REEL-API-04 | `POST /v1/amazon-transitions` は Safeguard block 時に 409 + ProblemDetails（`safeguard.monthly-limit-exceeded` 等、reel.yaml 既定と整合） |
| REEL-API-05 | 入力検証（cursor/limit/body）は契約スキーマで実施（SECURITY-05）。型生成ファイルは手動編集禁止・commit 必須（Unit-1 API-08） |
| REEL-API-06 | `examples` の更新責任は Unit-4 オーナー（Member C）が持つ（api-contracts.md §7.1） |
| REEL-API-07 | `POST /v1/amazon-transitions` は **429 レスポンス**を定義し `X-RateLimit-Limit` / `X-RateLimit-Remaining` / `X-RateLimit-Reset` ヘッダを返す（SECURITY-11 / Unit-1 API-09 / api-contracts.md §9.3）。reel.yaml への 429 追記は非破壊拡張で行う |

---

## 12. 設定値カタログ統合（Unit-4 全体）

| パラメータ | 既定値 | 所属 | 備考 |
|---|---|---|---|
| `CANDIDATE_POOL_SIZE` | 50 | B-03 | 候補生成件数 |
| `LIMIT` | 10 | B-03 | 1 ページのカード数 |
| `BOOST_MAX_CARDS` | 3 | B-03 | 深夜ブースト先頭挿入数 |
| `BOOST_PRICE_MIN_RATIO` / `MAX_RATIO` | 1.5 / 3.0 | B-03 | 高単価範囲（平均比） |
| `LATE_NIGHT_START_HOUR` / `END_HOUR` | 22 / 2 | B-03 | 深夜帯 |
| `EXP_PER_TRANSITION` | 1 | B-13 | 1 遷移の EXP |
| `LABEL_DEDUP_WINDOW_HOURS` | 24 | B-03 | ラベル重複防止ウィンドウ |
| `POST_TRANSITION_CATEGORY_COOLDOWN_SECONDS` | 600（10 分） | B-03 | 遷移直後の同カテゴリ抑制（FR-AUTH-03） |
| `CREATORS_CACHE_TTL_SECONDS` | 21_600（6h） | B-11 | カタログキャッシュ TTL（Unit-1 と整合） |
| `SWIPE_THRESHOLD_PX` | 60 | M-03 | 左右スワイプ確定閾値 |
| `DOUBLE_TAP_MS` | 350 | M-03 | ダブルタップ間隔上限 |
| `LEFT_SWIPE_COOLDOWN_COUNT` | 3 | M-03 | 同一カード左スワイプのクールダウン閾値 |
| `POST_TAP_REDIRECT_MS` | 1_200 | M-03 | Amazon タップ後のレポート自動遷移 |

> これらの性能目標・レート制限の具体値・タイムアウトは NFR Requirements / NFR Design ステージで Unit-4 向けに最終確定する。本表は機能設計時点の既定値。

---

## 13. Extension 適合（Functional Design 段階の該当性）

| Extension ルール | 本 Unit での扱い |
|---|---|
| SECURITY-05（入力検証）| REEL-API-05（cursor/limit/body の契約検証） |
| SECURITY-08（認可 / IDOR）| REEL-TR-06 / REEL-STRESS-04（JWT sub 一致、クライアント値非信用）|
| SECURITY-09（エラー詳細秘匿）| REEL-CAT-05（external-api 詳細を body に出さない）|
| SECURITY-11（セキュアデザイン）| REEL-TR-03（遷移前 Safeguard ゲート必須）/ REEL-API-07（POST 429 レート制限）|
| NG-6 / NG-8 | REEL-BOOST-02 / REEL-LABEL-06（脅迫回避）/ REEL-LINK-03（短縮禁止）|
| NG-7（PII）| REEL-CAL-04（カレンダー本文不送信）/ REEL-TR-08（テレメトリに PII 不含）|
| PBT-02（round-trip）| REEL-LINK-02（Special Link ↔ ASIN）/ カーソル encode-decode |
| PBT-03（invariant）| REEL-RANK-02/03（決定論・score=Σ）/ REEL-TR（上限超過なし）|
| PBT-04（idempotency）| REEL-TR-01（遷移記録の冪等性）|
| その他 SECURITY/PBT 実装詳細 | NFR Requirements / NFR Design で Unit-4 向けに確定（本ステージでは N/A）|
