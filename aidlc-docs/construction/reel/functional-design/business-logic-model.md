# Unit-4 Reel — Business Logic Model

> Unit-4 Reel の業務ロジックを**技術非依存**で記述。アルゴリズム・処理フロー・状態遷移を扱う（インフラ実装は NFR Design / Infrastructure Design で確定）。
> 参照: [domain-entities.md](./domain-entities.md) / [business-rules.md](./business-rules.md) / [Functional Design Plan](../../plans/unit-4-reel-functional-design-plan.md) / [Clarification](../../plans/unit-4-reel-functional-design-clarification.md) / [Unit-1 business-logic-model.md](../../unit-1-platform/functional-design/business-logic-model.md)
> 確定方針: Q1=X（MVP は購入履歴ベース関連商品）/ Q2〜Q10=A / CL-1=A / CL-2=A / CL-3=A

---

## ALG-RANK: リール推薦（候補生成 → 決定論的リランク、CL-1/CL-2=A）

Reel 推薦の中核。**候補生成（購入履歴ベース関連商品）→ 決定論的リランク（ブースト加算）** の 2 段（CL-1 + CL-2 = A）。LLM は順位には使わず、コピー/ラベル生成のみ（Q1/Q4）。

### 入力 / 出力
- 入力: `RecommendationContext`（domain-entities §2.3）、`RankingWeights`、`ReelCursor | null`
- 出力: `ReelPage`（domain-entities §1.3）

### 処理フロー

```
buildReel(ctx, weights, cursor):
  # ── ステップ1: 候補生成（MVP = 購入履歴ベース関連商品、CL-1=A）──
  if ctx.purchaseHistory is non-empty:
      query = CatalogQuery(
        byCategory = distinct(ctx.purchaseHistory.category),
        byBrand    = distinct(ctx.purchaseHistory.brand),
        seedAsins  = recent(ctx.purchaseHistory).asin,   # 共購買の起点
        excludeNgCategories = ctx.safeguardFlags.ngCategories,
        maxResults = CANDIDATE_POOL_SIZE)               # 例 50
      candidates = catalogPort.searchItems(query)        # ALG-CATALOG 経由（キャッシュ + ダミー/本番）
      origin_default = 'purchase-related' | 'co-purchase'
  else:
      # ── cold start（CL-3=A）──
      seedQuery = CatalogQuery(
        byCategory = ctx.onboardingPreferences.categories,
        byBrand    = ctx.onboardingPreferences.brands,
        excludeNgCategories = ctx.safeguardFlags.ngCategories,
        maxResults = CANDIDATE_POOL_SIZE)
      candidates = catalogPort.searchItems(seedQuery)
      if candidates is empty:
          candidates = catalogPort.searchItems(curatedPopularQuery)  # キュレーション固定リストで補完
      origin_default = 'onboarding-seed' | 'curated-popular'

  # ── ステップ2: 既出抑制（Q9=A）+ 遷移後カテゴリクールダウン（FR-AUTH-03）──
  candidates = filter(candidates, c => c.asin not in cursor.seenCardKeys)
  candidates = filter(candidates, c =>
      not inPostTransitionCooldown(c.category, ctx.recentTransitions, POST_TRANSITION_CATEGORY_COOLDOWN_SECONDS))
      # 直近 10 分以内に遷移した同一カテゴリを除外（REEL-RANK-10 / FR-AUTH-03）

  # ── ステップ3: 決定論的リランク（CL-2=A、純関数）──
  scored = []
  for c in candidates:
      base = relatedness(c, ctx.purchaseHistory)         # 0..1（カテゴリ/ブランド一致 + 共購買度）
      components = {
        relatedness:  weights.relatedness  * base,
        timeBoost:    weights.timeBoost    * (ctx.timeBucket.isLateNight ? 1 : 0),
        stressBoost:  weights.stressBoost  * stressFactor(ctx.stressLevel),   # low=0 / mid=0.5 / high=1
        calendarMatch:weights.calendarMatch* (matchesCalendar(c, ctx.calendarCategory) ? 1 : 0),
        recencyDecay: -weights.recencyDecay * recencyPenalty(c, cursor),      # 直近表示の減衰（負）
      }
      score = sum(components.values)
      scored.append(ScoredCandidate(product=c, baseRelatedness=base, score, origin, components))
  scored = stableSort(scored, key=score desc, tiebreak=asin asc)   # 決定論（同点は asin 昇順）

  # ── ステップ4: 深夜高単価ブースト挿入（ALG-BOOST、Q2=A）──
  if shouldBoost(ctx) and not cursor.boostConsumed:
      boosts = ALG-BOOST(ctx, scored)                    # 高単価カードを最大 K 件
      page_cards = interleaveBoostAtHead(boosts, scored) # ブーストを先頭に配置
      cursor.boostConsumed = true
  else:
      page_cards = scored

  # ── ステップ5: ページ化 + ラベル/コピー生成 ──
  top = take(page_cards, LIMIT)                          # 既定 10
  cards = []
  for s in top:
      label = ALG-LABEL(s.product, ctx)                  # 所有感ラベル（Q4=A）
      pitch = ALG-PITCH(s, ctx)                          # 推薦コメント（FR-REEL-03）
      cards.append(ReelCard(cardId=newId(), product=s.product, pitch, ownershipLabel=label,
                            tags=deriveTags(s, ctx), origin=s.origin,
                            isHighPriceBoost=(s.origin=='late-night-boost'), rankScore=s.score))
  nextCursor = advanceCursor(cursor, top)                # seenCardKeys 追加、rankPosition 前進
  return ReelPage(cards, nextCursor, generatedAt=now())
```

### 設計判断（Q1=X / CL-1/CL-2=A の根拠）
- **MVP は購入履歴ベースの関連商品**（CL-1=A）: Titan Embeddings + OpenSearch ベクトル検索は MVP では使わず、カテゴリ/ブランド一致 + 共購買ヒューリスティックで候補化。OpenSearch 依存を予選から外して軽量化・テスト容易化。ベクトル検索導入は決勝向けに backlog 化（[B-204](../../../../doc/backlog.md)）
- **リランクは MVP から適用**（CL-2=A）: 深夜/ストレス/カレンダーのブーストを順位に反映（US-02-01 の「深夜に高単価が先頭」を順位として実現）。リランクは純関数で決定論的、PBT 可能
- **cold start**（CL-3=A）: オンボ嗜好をシードにし、不足はキュレーション固定リストで補完。初回からフィードが成立

### 不変条件（PBT-03 候補）
- 同一 `(ctx, weights, 候補集合)` に対し順位は決定論的（同点は asin 昇順 tiebreak で安定）
- NG カテゴリ該当商品は候補に入らない（ステップ1 で除外）
- 既出商品（`cursor.seenCardKeys`）は再提示されない（ステップ2）
- 直近 10 分以内に遷移した同一カテゴリの商品は候補に入らない（ステップ2、FR-AUTH-03）
- `score == sum(components)`（内訳の和が一致、検算可能）

---

## ALG-BOOST: 深夜高単価ブースト（FR-REEL-03 / US-02-01、Q2=A）

### 発火条件（複合トリガー）

```
shouldBoost(ctx):
  return ctx.timeBucket.isLateNight              # 22:00〜02:00
     and ctx.stressLevel in {'mid','high'}        # ストレス mid 以上
     and not ctx.safeguardFlags.quietWeek         # 静観ウィークは抑止（US-02-01 AC-4 / NG-6）
     and not ctx.safeguardFlags.cooldownOn        # 冷却モードは抑止
```

### ブースト挿入

```
ALG-BOOST(ctx, scored):
  highPriceMin = ctx.averagePriceYen * BOOST_PRICE_MIN_RATIO   # 1.5x
  highPriceMax = ctx.averagePriceYen * BOOST_PRICE_MAX_RATIO   # 3.0x
  pool = filter(scored, s => highPriceMin <= s.product.priceYen <= highPriceMax)
  boosts = take(stableSort(pool, key=score desc), BOOST_MAX_CARDS)  # 最大 K=3
  for b in boosts:
      b.origin = 'late-night-boost'
      b.tags += '頑張ったあなたへ'
  return boosts
```

### 設計判断（Q2=A の根拠）
- **時間帯 + ストレスの複合**で発火 → M-2（深夜帯の脳内報酬系形成）を最速で狙う設計意図に整合
- **quietWeek / cooldownOn で抑止** → NG-6（脅迫・罪悪感強要回避）とセーフガード最優先（FR-FUNNEL-05）に整合
- ブースト枠は `cursor.boostConsumed` で**同一セッション 1 回のみ**（Q9=A、フィードの先頭に集中）

### 不変条件
- ブースト枠の価格は平均の 1.5〜3 倍の範囲内（範囲外は採用しない）
- `shouldBoost` が false なら高単価カードの強制先頭挿入は起きない（通常リランクのまま）

---

## ALG-PITCH / ALG-LABEL: 推薦コメント・所有感ラベル生成（FR-REEL-03 / US-02-05、Q4=A）

LLM 生成 + テンプレートフォールバック + 24h 重複防止（Q4=A）。**順位には影響しない**（表示テキストのみ）。

### ALG-PITCH: 推薦コメント

```
ALG-PITCH(scored, ctx):
  if ctx.stressLevel in {'mid','high'} and ctx.timeBucket.isLateNight:
      style = 'fatigue-boost'    # 「今日の会議 6 本、よく戦った。ご褒美は当然じゃね？」型（M-2 連動）
  elif ctx.calendarCategory present and matchesCalendar(scored.product, ctx.calendarCategory):
      style = 'calendar-agent'   # 「月曜のプレゼンのためのエージェント提案」型
  else:
      style = 'ownership-default'
  text = LLM.generatePitch(scored.product, ctx, style)
  text = moderate(text)          # NG-6（脅迫・罪悪感強要）除去、NG-3 身体/家族等の言及除去
  if LLM failed or moderation rejected:
      text = templatePitch(style, scored.product)   # 決定論フォールバック
  return text
```

### ALG-LABEL: 所有感ラベル（US-02-05）

```
ALG-LABEL(product, ctx):
  input = LabelGenerationInput(
    product,
    purchaseAffinity = deriveAffinity(product, ctx.purchaseHistory),  # 根拠 1 文の材料（AC-2）
    calendarBusyness = (ctx.calendarCategory present ? 'high' : 'low'),
    recentLabelHashes = load24hLabelHashes(ctx.userId))               # 重複防止（AC-3）
  if input.calendarBusyness == 'high':
      style = 'battle'           # 「今週もよく戦ってるね。これ、自分へのご褒美」（AC-4）
  else:
      style = 'reserved'         # 「確保しておきました」「○○ さんのために見つけといた」（AC-1）
  result = LLM.generateLabel(input, style)            # text + rationale（固有根拠 1 文、AC-2）
  result.text = moderate(result.text)                 # NG-6 除去
  if LLM failed or moderation rejected or hash(result.text) in input.recentLabelHashes:
      result = templateLabel(style, product)          # フォールバック（AC-3 重複時は別バリエーション）
      result.source = 'template-fallback'
  store24hLabelHash(ctx.userId, hash(result.text))
  return result
```

### 不変条件
- ラベル `text` は直近 24h で同一文言を連続表示しない（AC-3、ハッシュ照合）
- LLM 障害時もフォールバックで必ず非空のラベル/コメントを返す（フィードが崩れない、Q4=A）
- 出力は NG-6 / NG-3 をモデレーションで除去後に確定

---

## ALG-CATALOG: 商品カタログ取得（B-11、Q7=A / CL-1=A）

ポート/アダプタ + キャッシュデコレータ + 環境フラグ切替（Q7=A）。

### 処理フロー

```
catalogPort = withCache(selectAdapter(env))   # 環境フラグでアダプタ選択

selectAdapter(env):
  if env in {'doc-review','preview'} or not CREATORS_API_APPROVED:
      return DummyCatalogAdapter()    # 代表 1〜2 社の固定カタログ（§8 A-10 / FR-REEL-04）
  else:
      return CreatorsApiAdapter()     # Amazon Creators API

withCache(adapter).getItemByAsin(asin):
  1. キャッシュ参照（キー=asin、TTL=CREATORS_CACHE_TTL_SECONDS=6h）
  2. hit → 返す
  3. miss → adapter.getItemByAsin(asin) → キャッシュに put → 返す
  4. adapter が外部 API 失敗 → DomainError('external-api.creators-unavailable') を返す（SECURITY-09、詳細は body に出さない）

withCache(adapter).searchItems(query):
  - 同様にキャッシュ（キー=query のハッシュ）→ miss は adapter 呼出
```

### 設計判断（Q7=A の根拠）
- **ポート/アダプタ**で本番↔ダミーを差し替え → Approved Mobile Application 承認前後の移行が非破壊、テストでダミー注入が容易
- **キャッシュは共通デコレータ層** → 両アダプタで TTL 6h を一貫適用（B-11 責務）
- Creators API のレート制限・物理キャッシュ（ElastiCache Redis）は Infrastructure Design で確定

### 不変条件
- ダミーアダプタは外部ネットワークに出ない（書類審査・予選で安定動作）
- キャッシュ TTL 内の同一クエリは同一結果（決定論、テスト容易）

---

## ALG-TRANSITION: Amazon 遷移記録 + EXP + Safeguard（B-13、Q6=A）

冪等キー付き記録 + EXP +1 + Safeguard ゲート（Q6=A）。

### 処理フロー

```
recordTransition(req: AmazonTransitionRequest):
  1. 認可: req.userId == JWT.sub を検証（SECURITY-08）。不一致 → DomainError('auth.idor', 403)
  2. Safeguard ゲート（FR-FUNNEL-05）:
       decision = SafeguardPolicy.decideAllow(loadSafeguardInput(req.userId))   # Unit-1 ALG-SG
       if decision.decision == 'block':
           return DomainError(decision.reasonCode, 409)   # 記録せず（reel.yaml と整合）
       # warn は遷移を止めない（200 + warning ヘッダ）
  3. 冪等チェック（Q6=A）:
       existing = findByClientTransitionId(req.userId, req.clientTransitionId)
       if existing:
           return ExpAward(awarded=0, totalExp=current, duplicate=true)  # 二重計上しない
  4. 原子的書き込み（条件付き）:
       - AmazonTransitionRecord を put（条件: clientTransitionId 未登録）
       - SafeguardStates.transitionCountMonth += 1（同一条件付き書き込み / トランザクション）
       - EXP += 1（B-13 が Achievements〔Unit-2 スキーマ〕へ冪等 UpdateItem、同期）
  5. 遷移ログは B-08 PreferenceVectorUpdater（日次バッチ）が集計し嗜好ベクトル学習に反映（EXP 加算ではない、UC-05/FR-FUNNEL-04 連動）
  6. Telemetry: track('reel.amazon_tap', { context: req.context })   # PII 含めない
  7. return ExpAward(awarded=1, totalExp=new, duplicate=false)
```

### 設計判断（Q6=A の根拠）
- **冪等キー** `(userId, clientTransitionId)` で「戻る → 再タップ」の二重 EXP・二重カウントを防止（PBT-04）
- **Safeguard 先行ゲート** → 上限到達なら記録もカウントもせず 409。FR-FUNNEL-05「セーフガード最優先」に整合
- **EXP は B-13 が同期付与**（component-methods.md `record_transition() -> ExpAwardDto`）。嗜好ベクトル学習のみ B-08 日次バッチが非同期で実施（UC-05 連動）

### 不変条件（PBT-04 候補）
- 同一 `clientTransitionId` の N 回リクエストで EXP 加算は高々 1（`duplicate=true` で吸収）
- 月間遷移カウントは Safeguard 上限を超えて記録されない（ゲートで block）
- 記録とカウントとEXP加算は原子的（部分適用が起きない）

---

## ALG-LINK: Special Link 生成（B-10、Q8=A）

タグ付き正規 URL を純関数生成 + 環境ガード + 短縮禁止（Q8=A / NG-8）。

### 処理フロー

```
generateSpecialLink(input: SpecialLinkInput):
  1. baseUrl = "https://www.amazon.co.jp/dp/" + input.asin     # 正規 URL（短縮しない、NG-8）
  2. tag = ASSOCIATES_TAG + "-" + subTag(input.userId)         # commission 計測用ユーザーサブタグ
  3. url = baseUrl + "?tag=" + tag                             # クエリにタグ付与
  4. 環境ガード（§8 A-10 / US-03-04 AC-4）:
       if input.env == 'prd' and not CREATORS_API_APPROVED:
           return SpecialLink(url, tag, blocked=true)          # 本番未承認は遷移ブロック
       if input.env == 'dev':
           url = devPlaceholderLink(input.asin)                # dev は仮リンク
  5. return SpecialLink(url, tag, blocked=false)
```

### 不変条件（PBT-02 候補 round-trip）
- `extractAsin(generateSpecialLink(input).url).asin == input.asin`（Unit-1 S-01 で逆抽出して一致、Q8=A）
- 純関数: 同一 `input` → 同一 `url`
- 短縮 URL を使わない（遷移先が Amazon であることを不明瞭にしない、NG-8 / Associates Operating Agreement）

---

## ALG-GESTURE: ジェスチャーディスパッチ（M-03、Q5=A、詳細は frontend-components.md）

```
onGesture(gesture, card, settings):
  switch resolvePriority(gesture):   # double-tap > 水平スワイプ > vertical-scroll
    case 'double-tap':
        return show-transition-overlay(card)   # 必ずオーバーレイ（FR-REEL-05、削除不可）
    case 'swipe-left' (>=60px):
        if leftSwipeCount(card) > 3:  return cooldown-blocked   # US-02-03 AC-4 / FR-DEBATE-05
        if settings.debateDisabled:   return skip-toast(card)   # US-02-03 AC-3
        return navigate-debate(card)  # 0.5s トースト後（FR-DEBATE-01 trigger=reel-refuse）
    case 'swipe-right' (>=60px):
        return register-cart-watch(card)   # Unit-5 B-04（楽観 UI + トースト）
    default:
        return next-card
```

確認オーバーレイ確定後の遷移は ALG-TRANSITION（記録）+ ALG-LINK（Deep Link）へ接続する。

---

## アルゴリズム一覧と検証方針サマリ

| ID | ロジック | 主担当コンポーネント | PBT 性質候補 |
|---|---|---|---|
| ALG-RANK | 候補生成 → 決定論的リランク | B-03 | 決定論（同一入力→同一順位）/ NG 除外不変条件 / score=Σcomponents |
| ALG-BOOST | 深夜高単価ブースト | B-03 | 発火条件の真理値表 / 価格範囲不変条件 / quietWeek 抑止 |
| ALG-PITCH / ALG-LABEL | 推薦コメント・所有感ラベル | B-03 | 24h 重複なし / フォールバック非空 / モデレーション後出力 |
| ALG-CATALOG | カタログ取得 + キャッシュ + ダミー | B-11 | キャッシュ一貫性 / ダミーの決定性 |
| ALG-TRANSITION | 遷移記録 + EXP + Safeguard | B-13 | 冪等性（PBT-04）/ 上限超過なし / 原子性 |
| ALG-LINK | Special Link 生成 | B-10 | round-trip（PBT-02）/ 純関数 / 短縮禁止 |
| ALG-GESTURE | ジェスチャーディスパッチ | M-03 | 優先順位の決定性 / double-tap は必ずオーバーレイ |

> PBT / Security の具体的なテスト戦略・カバレッジ目標・性能目標は NFR Requirements / NFR Design ステージで Unit-4 向けに確定する。
