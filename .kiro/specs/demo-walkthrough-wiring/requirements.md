# Requirements Document

## Introduction

本スペック「デモ通し導線（demo-walkthrough-wiring）」は、YUDANE モバイルアプリの予選 MVP デモ（2026-05-30）で「通しで見せられる導線」を最優先で成立させるための機能要件を定義する。

現状、`mobile/src/screens/` 配下の 4 画面（ホーム / お見立て / お取り置き / 会員証）はすべて固定モックを表示し、「Amazon で買う」系アクションは `Alert` を出すだけで実際の遷移は発生していない。一方、`mobile/src/features/` 配下には接続用ロジック（TanStack Query フック・`reel-api`・`api-client`）が既に実装済みだが、画面とは未接続のまま分断している。

本スペックは、この分断を解消し、(1) 各画面を `features/` 配下の既存フック（OpenAPI 契約準拠）に接続し、(2) Amazon Associates Special Link への実遷移を配線し、(3) 遷移を `POST /v1/amazon-transitions` で記録して EXP（委ね Lv）を加算する。バックエンド未デプロイ環境でもデモが成立するよう、MSW モック層でのフォールバックを前提とする。

### ダメ化メカニズムとの対応

- **M-1（判断力の弱体化）**: お見立て・お取り置き画面に AI が選んだ商品を提示し続ける導線を実データで成立させる
- **M-2（購買快楽のストレス解消剤化）**: Amazon 実遷移 → EXP 加算 → 委ね Lv / 会員ランク前進という即時報酬ループを配線する
- **M-3（判断の完全移譲）**: 上記 M-1・M-2 を 4 画面の通し導線として連結し、悠介の退化年表（[persona-journey.md](../../../aidlc-docs/inception/user-stories/persona-journey.md)）が描く「反射的に開いて買う」体験をデモで再現する

### スコープ（このスペックで実装するもの）

1. ホーム / お見立て / お取り置き / 会員証の 4 画面を、`features/` 配下の既存フック（TanStack Query 経由）+ OpenAPI 契約に接続する
2. Amazon Associates Special Link URL の構築と、各画面の「Amazon で買う」系アクションからの実遷移（`Linking.openURL`）への置換
3. Amazon 遷移記録（`POST /v1/amazon-transitions`）による EXP 加算と委ね Lv / 会員ランクへの反映
4. お取り置き画面のフィルタタブの実フィルタリングへの接続
5. バックエンド未デプロイ時の MSW モック層フォールバック
6. ローディング / エラー / 空状態のハンドリング
7. 予選 MVP 判定基準のデモシナリオ E2E-01〜03 を通しで再現できる導線の確立

### スコープ外（本スペックでは扱わない / 別スペック）

- 論破チャット（ご相談画面 / Unit-3 Debate）の実 AI 化（Bedrock ストリーミング論破）。本スペックではご相談画面の既存ハードコード応答辞書を据え置く
- リール（お見立て画面）の縦スワイプジェスチャーの新規実装
- カレンダー連動 / ダメ化ポートフォリオ / セーフガード / オンボーディングの新規画面実装
- ネイティブ Share Extension 連携の新規実装
- バックエンド Lambda（debate / calendar / safeguard / report）の新規実装
- OpenAPI 契約そのものの破壊的変更（既存契約への接続が原則。不足が判明した場合は依存として明示し、契約 PR を先行させる）

## Glossary

- **デモ通し導線 (Demo_Walkthrough)**: 予選 MVP デモにおいて、ホーム → お見立て → お取り置き → 会員証 の 4 画面を遷移しながら、実データ表示と Amazon 実遷移を含む一連の操作を中断なく提示できる操作フロー
- **接続層 (Connection_Layer)**: `mobile/src/features/` 配下に既存する TanStack Query フック群および API 呼び出しロジック（`useHomeSnapshot` / `useReelFeed` / `useAmazonRedirect` / `useCartWatchItems` / `useCartDismiss` / `reel-api` 等）
- **ホーム画面 (HomeScreen)**: `mobile/src/screens/home/HomeScreen.tsx`。ウェルカム・ランク・統計・「今日の論破」を表示する画面
- **お見立て画面 (MitateScreen)**: `mobile/src/screens/mitate/MitateScreen.tsx`。AI が提示する商品（リール）を表示する画面
- **お取り置き画面 (OtorikokiScreen)**: `mobile/src/screens/otorikoki/OtorikokiScreen.tsx`。カート介入の監視リストを表示する画面
- **会員証画面 (KaiinshoScreen)**: `mobile/src/screens/kaiinsho/KaiinshoScreen.tsx`。会員ランクの進行と特典を表示する画面
- **APIクライアント (Api_Client)**: Unit-1 の M-12 `ApiClient`。`apiFetch` ヘルパー経由で REST 呼び出しを行う
- **ホーム概況 (HomeSnapshot)**: `GET /v1/home` のレスポンス。`candidateCount` / `cartWatchCount` / `yudaneLevel` / `remainingBudgetYen` を持つ
- **リールページ (ReelPage)**: `GET /v1/reel` のレスポンス。`cards` / `nextCursor` / `generatedAt` を持つ
- **監視アイテム (CartWatchItem)**: `GET /v1/cart-watch-items` の各要素（`CartWatchItemDto`）。`asin` / `status` / `productMeta` 等を持つ
- **EXP加算結果 (ExpAward)**: `POST /v1/amazon-transitions` のレスポンス。`awarded` / `totalExp` / `duplicate` を持つ
- **委ねLv (Yudane_Level)**: `HomeSnapshot.yudaneLevel`。会員ランク導出の根拠となる非負整数
- **会員ランク (Member_Rank)**: BLANC / ARGENT / NOIR / ONYX / ÉBÈNE のいずれか。委ね Lv から導出される
- **Amazon遷移サービス (Amazon_Transition_Service)**: Special Link URL を構築し、`POST /v1/amazon-transitions` で遷移を記録した上で外部の Amazon を開く一連の処理（`useAmazonRedirect` + Special Link ビルダー + `Linking.openURL`）
- **Special Linkビルダー (Special_Link_Builder)**: ASIN と Amazon Associates トラッキングタグから Amazon Associates Special Link URL を構築する純関数
- **トラッキングタグ (Associates_Tracking_Tag)**: Amazon Associates の紹介コミッションを識別するタグ文字列。環境変数または設定経由で注入される
- **MSWモック層 (MSW_Mock_Layer)**: `mobile/src/test/msw-handlers.ts` の Mock Service Worker ハンドラ群。OpenAPI の examples に準拠したモックレスポンスを返す
- **Associates開示 (Associates_Disclosure)**: `ASSOCIATES_DISCLOSURE_TEXT` 定数が示す、Amazon Associates 紹介料に関する開示文言（NG-8 / FR-PROFILE-04 整合）
- **デモシナリオ (Demo_Scenario)**: 予選 MVP 判定基準が定める E2E-01〜03 の 3 シナリオ

## Requirements

### Requirement 1: ホーム画面のバックエンド接続

**User Story:** 予選デモの操作者として、ホーム画面の概況（候補件数・監視件数・委ね Lv・残額）を実データで表示したい。それにより、固定モックではなく「YUDANE が悠介の状況を把握している」感を審査員に提示できる（M-1）。

#### Acceptance Criteria

1. WHEN ホーム画面が初めて表示（マウント）される、THE HomeScreen SHALL 接続層の `useHomeSnapshot` を通じて `GET /v1/home` へのホーム概況取得を 1 回開始する
2. WHEN ホーム概況の取得が成功する、THE HomeScreen SHALL `candidateCount`（候補件数）・`cartWatchCount`（監視件数）・`yudaneLevel`（委ね Lv）・`remainingBudgetYen`（残額）の 4 値を、それぞれ対応する 4 つの表示要素に反映し、値が 0 の場合も当該数値（0）を表示する
3. WHILE ホーム概況の取得が進行中であり、かつ表示可能なキャッシュ済みホーム概況が存在しない、THE HomeScreen SHALL ローディング状態を、成功時の概況表示およびエラー表示のいずれとも区別可能な形で提示する
4. IF ホーム概況の取得がネットワークエラー・10 秒のタイムアウト超過・レスポンス構造の検証失敗のいずれかにより失敗する、THEN THE HomeScreen SHALL 取得に失敗した旨を示すエラーメッセージを提示し、かつ概況の各表示要素を空ではなくエラー状態として提示する
5. WHEN 操作者がエラー表示上の再取得操作を行う、THE HomeScreen SHALL 接続層の `useHomeSnapshot` を通じて `GET /v1/home` のホーム概況取得を再度開始する
6. WHEN 操作者がウェルカムカードの「お見立てを見る」を操作する、THE HomeScreen SHALL お見立て画面へ遷移する
7. WHEN 操作者が「今日の論破」の優先アイテムを操作する、THE HomeScreen SHALL お取り置き画面へ遷移する

### Requirement 2: お見立て（リール）画面のバックエンド接続

**User Story:** 予選デモの操作者として、お見立て画面に表示する商品カードを実データで取得したい。それにより、AI が「これあなた好きでしょう」と差し出す導線を実データで成立させられる（M-2）。

#### Acceptance Criteria

1. WHEN お見立て画面が表示される、THE MitateScreen SHALL 接続層の `useReelFeed` を通じて `GET /v1/reel` からリールページを取得する
2. WHEN リールページの取得が成功する、THE MitateScreen SHALL リールページ内の現在表示中カードを先頭カードに設定する
3. WHILE 現在表示中カードが存在する、THE MitateScreen SHALL 現在表示中カードの商品名・価格・論破ピッチ・所有感ラベルを対応する表示要素に反映する
4. WHILE 現在表示中カードより後続のカードがリールページ内に 1 件以上存在する、THE MitateScreen SHALL 当該後続カードを「UP NEXT」一覧に反映する
5. IF 現在表示中カードより後続のカードがリールページ内に存在しない、THEN THE MitateScreen SHALL 「UP NEXT」一覧を空として提示する
6. WHILE リールページの取得が進行中である、THE MitateScreen SHALL ローディングを示す表示状態を提示する
7. IF リールページの取得が失敗する、THEN THE MitateScreen SHALL エラー表示と再取得操作を提示する
8. IF 取得したリールページがカードを 1 件も含まない、THEN THE MitateScreen SHALL 空状態の表示を提示する
9. WHEN 操作者が「論破されて買う」を操作する、THE MitateScreen SHALL 現在表示中カードの ASIN を引数に Amazon 遷移サービスを起動する
10. WHEN 操作者が「感想で見送る」を操作し、かつ現在表示中カードより後続のカードが存在する、THE MitateScreen SHALL 現在表示中カードを直後の後続カードへ進め、進めた後のカードの商品名・価格・論破ピッチ・所有感ラベルを表示要素に反映する
11. IF 操作者が「感想で見送る」を操作し、かつ現在表示中カードより後続のカードが存在しない、THEN THE MitateScreen SHALL 空状態の表示を提示する

### Requirement 3: お取り置き（カート介入）画面のバックエンド接続

**User Story:** 予選デモの操作者として、お取り置き画面の監視リストを実データで表示し、不要なアイテムを解除したい。それにより、「迷いを外部化させる装置」としての監視リストを実データで提示できる（M-1）。

#### Acceptance Criteria

1. WHEN お取り置き画面が表示される、THE OtorikokiScreen SHALL 接続層の `useCartWatchItems` を通じて `GET /v1/cart-watch-items` から監視アイテム一覧を取得する
2. WHEN 監視アイテム一覧の取得が成功する、THE OtorikokiScreen SHALL 各監視アイテムについて、商品名（`productMeta.title`）・価格（`productMeta.priceYen`、円建て整数）・ステータス（`status` の値 watching / notified-30m / notified-6h / notified-24h / purchased / dismissed / watching_orphaned のいずれか）を当該アイテムの表示要素に反映する
3. WHEN 監視アイテム一覧の取得が成功する、THE OtorikokiScreen SHALL 表示対象の監視アイテムの件数（0 以上の整数）と価格合計（表示対象の各監視アイテムの `productMeta.priceYen` を合算した円建て整数）を、一覧の集計表示要素に反映する
4. WHILE 監視アイテム一覧の取得が進行中である、THE OtorikokiScreen SHALL ローディングを示す表示状態を提示する
5. IF 監視アイテム一覧の取得が失敗する、THEN THE OtorikokiScreen SHALL エラー表示と、`GET /v1/cart-watch-items` を再実行する再取得操作を提示する
6. IF 取得した監視アイテム一覧が 0 件である、THEN THE OtorikokiScreen SHALL 空状態の表示を提示する
7. WHEN 操作者が監視アイテムの「論破して買う」を操作する、THE OtorikokiScreen SHALL 当該アイテムの ASIN を引数に Amazon 遷移サービスを起動する
8. WHEN 操作者が監視アイテムの解除を操作する、THE OtorikokiScreen SHALL 当該アイテムの ASIN を経路パラメータとして、接続層の `useCartDismiss` を通じて `DELETE /v1/cart-watch-items/{asin}` を呼び出す
9. WHEN 監視解除の呼び出しが成功する（HTTP 204 を含む冪等な成功応答が返る）、THE OtorikokiScreen SHALL 当該アイテムを一覧表示から除去し、表示対象の件数と価格合計を再計算する
10. IF 監視解除の呼び出しが失敗する（成功応答以外が返る、または通信に失敗する）、THEN THE OtorikokiScreen SHALL 当該アイテムを一覧表示に保持したまま、利用者向けのエラー表示と再試行手段を提示する

### Requirement 4: お取り置きフィルタタブの実フィルタリング

**User Story:** 予選デモの操作者として、お取り置き画面のフィルタタブで監視リストを絞り込みたい。それにより、表示だけのタブではなく機能するフィルタを審査員に提示できる。

#### Acceptance Criteria

1. THE OtorikokiScreen SHALL フィルタタブの各タブ値（「すべて」「おすすめ」「まもなく」「休眠」）を、監視アイテムのステータスに対する判定条件へ一意に対応付ける
2. WHEN 操作者があるフィルタタブを選択する、THE OtorikokiScreen SHALL 選択タブの判定条件に合致する監視アイテムのみを一覧に表示する
3. WHEN 操作者が「すべて」タブを選択する、THE OtorikokiScreen SHALL 取得済みの全監視アイテムを一覧に表示する
4. WHEN フィルタタブの選択が変化する、THE OtorikokiScreen SHALL 当該タブの判定条件に従って表示件数と合計金額を再計算する
5. THE OtorikokiScreen SHALL 各監視アイテムを、選択中タブの判定条件に対して合致または非合致のいずれか一方に分類する

### Requirement 5: 会員証画面のバックエンド接続

**User Story:** 予選デモの操作者として、会員証画面の会員ランクと進行を実データの委ね Lv から表示したい。それにより、ゲーミフィケーションによる即時報酬（M-2）を実データで提示できる。

#### Acceptance Criteria

1. WHEN 会員証画面が表示される、THE KaiinshoScreen SHALL 接続層（`useHomeSnapshot`）を通じて `GET /v1/home` のホーム概況から委ね Lv（`yudaneLevel`、非負整数）を取得して保持する
2. THE KaiinshoScreen SHALL すべての非負整数の委ね Lv に対して、会員ランク集合 {BLANC, ARGENT, NOIR, ONYX, ÉBÈNE} のうちちょうど 1 つを割り当てる決定的な対応付け（同一の委ね Lv からは常に同一の会員ランクを返す）を用いて会員ランクを導出する
3. THE KaiinshoScreen SHALL 会員ランク集合 {BLANC, ARGENT, NOIR, ONYX, ÉBÈNE} の各ランクについて、当該ランクを導出する非負整数の委ね Lv が少なくとも 1 つ存在する対応付け（全射）を用いて会員ランクを導出する
4. THE KaiinshoScreen SHALL BLANC → ARGENT → NOIR → ONYX → ÉBÈNE を最下位から最上位への昇順段階とし、委ね Lv の増加に対して導出される会員ランクの段階が単調非減少となる（より大きい委ね Lv がより低い段階の会員ランクを導出しない）対応付けを用いる
5. WHEN 会員ランクが導出される、THE KaiinshoScreen SHALL 導出された現在の会員ランクに対応するランク段階をちょうど 1 つ強調表示し、それ以外のランク段階を強調しない
6. WHILE 委ね Lv の取得が進行中である、THE KaiinshoScreen SHALL ローディングを示す表示状態を提示する
7. IF 委ね Lv の取得が失敗する、THEN THE KaiinshoScreen SHALL エラー表示と再取得操作を提示する

### Requirement 6: Amazon Associates Special Link への実遷移

**User Story:** 予選デモの操作者として、「Amazon で買う」操作で実際に Amazon の商品ページへ遷移したい。それにより、決済を Amazon 側で完結させる YUDANE の収益導線を審査員に提示できる。

#### Acceptance Criteria

1. WHEN Special Link ビルダーに半角英数字 10 文字の ASIN と 1 文字以上の非空トラッキングタグが渡される、THE Special_Link_Builder SHALL 当該 ASIN と当該トラッキングタグの両方を含み、Amazon の当該 ASIN の商品ページを指す Amazon Associates Special Link URL を構築する
2. THE Special_Link_Builder SHALL すべての半角英数字 10 文字の ASIN について、構築した Special Link URL から再抽出した ASIN が入力 ASIN と大文字小文字を含めて完全一致することを保証する（round-trip property、プロパティベーステスト候補）
3. IF Special Link ビルダーに半角英数字 10 文字に合致しない値（長さ不一致・英数字以外の文字を含む・空文字列・未定義のいずれか）が渡される、THEN THE Special_Link_Builder SHALL URL を構築せず、呼び出し元に入力検証失敗を示すエラーを通知する
4. WHEN Amazon 遷移サービスが起動される、THE Amazon_Transition_Service SHALL Amazon 遷移記録（`POST /v1/amazon-transitions`）を 5 秒以内のタイムアウトで実行し、その成功・失敗・タイムアウトのいずれかの結果が確定した後に、構築した Special Link URL を `Linking.openURL` で開く
5. IF Amazon 遷移記録がネットワークエラー・非成功応答・タイムアウトのいずれかにより失敗する、THEN THE Amazon_Transition_Service SHALL EXP が記録されなかったことを示す利用者向けエラー表示を提示し、かつ構築済み Special Link URL の `Linking.openURL` による遷移自体は継続する
6. THE Amazon_Transition_Service SHALL トラッキングタグを環境変数または設定経由で取得する
7. IF トラッキングタグを環境変数または設定から取得できない（未設定または空文字列）、THEN THE Amazon_Transition_Service SHALL Special Link URL を構築せず、設定不備を示すエラー表示を提示し、Amazon 遷移を実行しない

### Requirement 7: Amazon 遷移記録による EXP 加算

**User Story:** 予選デモの操作者として、Amazon 遷移を記録して委ね Lv を加算したい。それにより、購買 → 即時報酬 → ランク前進という M-2 の報酬ループを実データで提示できる。

#### Acceptance Criteria

1. WHEN Amazon 遷移サービスが Amazon 遷移記録を実行する、THE Amazon_Transition_Service SHALL カード ID・ASIN・遷移コンテキスト・クライアント遷移 ID を含むリクエストを `POST /v1/amazon-transitions` に送信する
2. WHEN Amazon 遷移記録が成功し EXP 加算結果を受信する、THE Amazon_Transition_Service SHALL 受信した `totalExp` の値を、次回のホーム概況取得が完了するまでの間、委ね Lv 表示が参照する委ね Lv の値として保持する
3. THE Amazon_Transition_Service SHALL 同一カードに対するすべての Amazon 遷移記録の試行に対して、当該カードの識別情報から決定的に導出される単一のクライアント遷移 ID を用いる
4. WHEN 同一カードに対する Amazon 遷移記録が 2 回以上実行される、THE Amazon_Transition_Service SHALL 委ね Lv 表示が参照する委ね Lv の値を、加算がちょうど 1 回だけ反映された場合と同一の値に保つ
5. IF Amazon 遷移記録のレスポンスが `duplicate` を真として返す、THEN THE Amazon_Transition_Service SHALL `awarded` を加算として再適用せず、かつ受信した `totalExp` の値を委ね Lv 表示が参照する委ね Lv の値として保持する
6. IF Amazon 遷移記録が失敗する、THEN THE Amazon_Transition_Service SHALL 委ね Lv 表示が参照する委ね Lv の値を当該記録の試行前の値から変更しない

### Requirement 8: MSW モック層フォールバック（バックエンド未デプロイ対応）

**User Story:** 予選デモの操作者として、バックエンドが未デプロイの環境でも 4 画面を実データ相当で表示したい。それにより、デプロイ状況に依存せずデモを成立させられる。

#### Acceptance Criteria

1. WHERE MSW モック層が有効化されている、THE MSW_Mock_Layer SHALL `GET /v1/home` / `GET /v1/reel` / `POST /v1/amazon-transitions` / `GET /v1/cart-watch-items` の各要求に OpenAPI の examples に準拠したレスポンスを返す
2. WHERE MSW モック層が有効化されている、THE Connection_Layer SHALL バックエンド実装の有無に関わらず各画面へデータを供給する
3. THE MSW_Mock_Layer SHALL 認証情報・個人を特定する情報（PII）を含まないモックレスポンスを返す
4. WHEN お取り置き画面の解除操作が MSW モック層に対して実行される、THE MSW_Mock_Layer SHALL `DELETE /v1/cart-watch-items/{asin}` に成功レスポンスを返す

### Requirement 9: ローディング・エラー・空状態の一貫したハンドリング

**User Story:** 予選デモの操作者として、通信中や失敗時にも画面が破綻しないようにしたい。それにより、デモ中の予期せぬ通信状況でも導線を継続できる。

#### Acceptance Criteria

1. WHILE いずれかの画面でデータ取得が進行中である、THE Connection_Layer SHALL 当該画面にローディング状態を提供する
2. IF いずれかの画面でデータ取得が失敗する、THEN THE Connection_Layer SHALL 同一画面で並行する他のデータ取得の進行状況に関わらず、当該失敗に対する利用者向けのエラーメッセージと再取得手段を直ちに当該画面へ提供する
3. WHEN データ取得が成功してキャッシュが有効な間に同一画面が再表示される、THE Connection_Layer SHALL キャッシュ済みデータを表示に用いる
4. IF データ取得が再試行される、THEN THE Connection_Layer SHALL 再試行の結果に応じて表示状態を成功・失敗のいずれかへ更新する

### Requirement 10: デモ通し導線（E2E-01〜03 の再現）

**User Story:** 予選デモの発表者として、ホームから始まる一連の操作で E2E-01〜03 の各シナリオに対応する導線を中断なく提示したい。それにより、予選 MVP 判定基準を満たすデモを実施できる。

#### Acceptance Criteria

1. THE Demo_Walkthrough SHALL ホーム画面・お見立て画面・お取り置き画面・会員証画面の 4 画面を、底部タブまたは画面内遷移によって相互に到達可能にする
2. WHEN 発表者がお見立て画面で「論破されて買う」を操作する、THE Demo_Walkthrough SHALL Amazon 実遷移と EXP 加算を実行し、E2E-01 が要する「翻意 → Amazon 遷移」に対応する導線を提示する
3. WHEN 発表者がお取り置き画面の監視アイテムで「論破して買う」を操作する、THE Demo_Walkthrough SHALL Amazon 実遷移と EXP 加算を実行し、E2E-03 が要する「監視 → Amazon 遷移」に対応する導線を提示する
4. WHEN Amazon 遷移による EXP 加算が反映された後に会員証画面が表示される、THE Demo_Walkthrough SHALL 加算後の委ね Lv に基づく会員ランクを提示する
5. THE Demo_Walkthrough SHALL ご相談画面（論破チャット）の既存応答辞書を据え置いたまま、本スペックのスコープ内 4 画面の導線を成立させる

### Requirement 11: Associates 開示と倫理ライン（NG-8）

**User Story:** プロダクト責任者として、Amazon 遷移を伴う画面で紹介料に関する開示を提示したい。それにより、Amazon Associates Operating Agreement と NG-8（データ悪用・規約違反の除外）を遵守できる。

#### Acceptance Criteria

1. WHERE Amazon 遷移を伴う操作を提示する画面である、THE Connection_Layer SHALL Associates 開示（`ASSOCIATES_DISCLOSURE_TEXT`）を当該画面で利用者に表示する
2. THE Associates_Disclosure SHALL 「Amazon Associates」および「紹介料」の文言を含む
3. WHERE Amazon 遷移を伴う操作を提示する画面である、THE Connection_Layer SHALL Associates 開示が正しい文言を含むことと利用者に表示されることの両方を満たす

### Requirement 12: セキュリティと設定管理

**User Story:** 開発者として、接続先や認証に関わる設定をコードに直書きせず、入力を検証したい。それにより、SECURITY Baseline と project 規約を遵守できる。

#### Acceptance Criteria

1. THE Connection_Layer SHALL API のベース URL を環境変数または設定経由で取得する
2. THE Connection_Layer SHALL 認証情報・トラッキングタグをソースコードに直接記載しない
3. WHEN API レスポンスを画面表示に用いる、THE Connection_Layer SHALL レスポンスの構造を検証した上で表示に渡す
4. IF API レスポンスが期待する構造に合致しない、THEN THE Connection_Layer SHALL 当該画面にエラー状態を提供する
5. WHEN Amazon 遷移記録または監視解除を要求する、THE Api_Client SHALL Cognito JWT による認証ヘッダを付与する

## 既知の依存・前提（要確認事項）

> 以下は本要件の前提となる外部依存である。設計フェーズで解消方針を確定する。

1. **`GET /v1/home` のパス未登録**: `HomeSnapshot` スキーマは `shared/schema/components/schemas/auth.yaml` に定義済みだが、`shared/schema/openapi.yaml` の `paths` 節に `/v1/home` が登録されていない。`useHomeSnapshot` と MSW ハンドラは既に当該パスを参照しているため、OpenAPI 契約への `/v1/home` パス追記（非破壊的変更）が前段で必要になる可能性がある（api-contracts.md §6 に従い契約 PR 先行）。
2. **トラッキングタグの供給元**: Amazon Associates トラッキングタグの値そのものは本リポジトリに格納せず、環境変数 / SSM Parameter Store 経由で注入する前提（tech.md §5 / AGENTS.md §8）。
3. **Special Link URL の最終仕様**: Amazon Approved Mobile Application 申請（[backlog B-503](../../../doc/backlog.md)）の承認状況により、Special Link の最終形式が変わる可能性がある。本スペックは「ASIN + トラッキングタグを含む遷移可能 URL」を最小要件とする。
