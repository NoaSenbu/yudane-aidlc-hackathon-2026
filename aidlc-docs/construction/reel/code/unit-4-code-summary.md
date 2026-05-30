# Unit-4 Reel — Code Generation 総括

> Unit-4 Reel（🎬 エージェント型リール UC-02）のコード生成（Step 1〜10）の全体サマリ。
> 確定方針: FD（Q1=X/Q2〜Q10=A, CL-1〜3=A）/ NFR-Req（Q1〜Q10=A）/ NFR-Design（Q1〜Q10=A + 矛盾解消 3）/ Infra（Q1〜Q7=A）+ 横断矛盾解消（EXP 同期 / Associates タグ SSM / B-10 共有モジュール）

## 生成物の全体像（ワークスペース直下）

### shared/schema/（API 契約、非破壊拡張）
- `paths/reel.yaml` — getReel（200=ReelPage）/ recordAmazonTransition（201=ExpAward / 409 / 429）
- `components/schemas/reel.yaml` — ProductMeta / OwnershipLabel / ReelCard / ReelPage / AmazonTransitionRequest / ExpAward
- `examples/reel.yaml` — Prism Mock / 契約テスト用
- `openapi.yaml`（更新）— reel スキーマ登録

### backend/src/reel/（Python 3.13、クラシック TDD）
- `models.py` — Pydantic v2 DTO（frozen / extra=forbid）
- `catalog.py` + `dummy_catalog.json` — ProductCatalogPort / DummyCatalogAdapter / CachedCatalog
- `ranking.py` — CandidateSourcePort / PurchaseHistoryHeuristicSource / rank（決定論）/ apply_boost（深夜）
- `bedrock_client.py` — TextGenerator Protocol + BedrockTextGenerator（薄ラッパ、DI）
- `labels.py` — generate_pitch / generate_label / is_safe（モデレーション + フォールバック + 24h 重複防止）
- `special_link.py` — generate_special_link（純関数、短縮禁止、環境ガード）
- `cursor.py` — ReelCursor + encode/decode（不透明・round-trip）
- `feed.py` — build_reel（候補→リランク→ブースト→カード化→カーソル、ラベル同期確定）
- `transition.py` — record_transition（先行 Safeguard ゲート fail-closed + 冪等記録 + EXP +1 同期）
- `handlers/feed.py` / `handlers/transition.py` — Lambda ハンドラ（require_owner / 409 / 検証）

### backend/tests/reel/（example + PBT）
- `strategies.py`（PBT-07 ドメインジェネレータ）/ `test_ranking.py`（PBT-03）/ `test_boost.py` / `test_special_link.py`（PBT-02）/ `test_transition.py`（PBT-04）/ `test_labels.py` / `test_cursor.py`（PBT-02/05）/ `test_handler_feed.py` / `test_handler_transition.py`
- `backend/conftest.py`（更新）— shared python パス追加

### mobile/src/features/reel/（React Native + TS、Outside-In TDD）
- `types.ts` / `gestures.ts` / `boost-nudge.ts` / `client-transition-id.ts` / `reel-api.ts` / `use-reel-feed.ts` / `use-amazon-redirect.ts` / `reel-screen.tsx` / `index.ts`
- テスト: `gestures.test.ts` + `gestures.pbt.test.ts` / `boost-nudge.test.ts` + `boost-nudge.pbt.test.ts` / `reel-api.test.ts` / `client-transition-id.test.ts`（example/PBT 分割）
- `mobile/src/test/msw-handlers.ts`（更新）— reel ルート追加

### infra/（AWS CDK v2、Snapshot TDD）
- `lib/reel-stack.ts` — DynamoDB 2 / feed・transition Lambda（VPC 外 SnapStart）/ API パス / usage plan 429 / SSM / Alarm
- `test/reel-stack.test.ts` — CDK assertions + cdk-nag
- `bin/app.ts`（更新）— reel-stack 登録

### docs
- `aidlc-docs/construction/reel/code/{backend,mobile,infra,unit-4-code}-summary.md`

## ストーリーカバレッジ（US-02）
- US-02-01 深夜ブースト: ranking.apply_boost / boost-nudge / reel-stack ✅
- US-02-02 ダブルタップ遷移 + EXP: transition / special_link / use-amazon-redirect / overlay ✅
- US-02-03 左スワイプ論破: gestures（reel-refuse / 論破不要 / クールダウン）✅
- US-02-04 右スワイプ監視: gestures（register-cart-watch、Unit-5 連携）✅
- US-02-05 所有感ラベル: labels（LLM + フォールバック + 24h 重複防止）✅

## Extension コンプライアンス（実装段階）
- SECURITY-05（入力検証）/ -08（require_owner sub 照合）/ -09（external-api 詳細秘匿）/ -11（usage plan 429 / fail-closed Safeguard）/ NG-6・NG-3（モデレーション）/ NG-8（短縮禁止）/ Secrets vs SSM 分離
- PBT-02（Special Link round-trip / cursor round-trip）/ PBT-03（ranking 決定論・score=Σ・NG 除外）/ PBT-04（transition 冪等）/ PBT-07（ドメインジェネレータ）/ PBT-08（seed 固定）/ PBT-10（example 併存）

## 検証メモ
- **Backend ロジック + PBT 40 件 pass を実行確認**（`.venv`、coverage 無効化）。handler 2 件は `aws_xray_sdk` 未導入のローカル制約で collection 不可（Unit-1 と同制約、Build and Test で実行）
- Mobile vitest / infra cdk synth・snapshot は **Build and Test 段**で実行（node_modules 未セットアップ、package-lock 未コミットのため install 保留・ユーザー合意済み）
- 全生成ファイル diagnostics 0

## スコープ外（後続）
- 実行・カバレッジ計測・型生成・cdk synth/deploy・依存インストール（CVE チェック込み）→ Build and Test
- OpenSearch ベクトル検索（B-204）/ Creators API 本番接続 → 決勝
- **Unit-1 への依頼**: API Gateway の `api-id` / `api-root-resource-id` の SSM 公開（reel/debate/cart のパス相乗り前提）+ OpenSearch コレクション追加（infra-summary.md 参照）
- 契約 PR（reel.yaml）の分離 merge（Member A Approve）
