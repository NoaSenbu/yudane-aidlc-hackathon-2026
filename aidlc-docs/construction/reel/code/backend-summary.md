# Unit-4 Reel — Code Summary: Backend（Step 2〜5）

> `backend/src/reel/` のビジネスロジック + API レイヤの生成サマリ。TDD（クラシック）で生成。
> 確定方針: FD（Q1=X/Q2〜Q10=A, CL-1〜3=A）/ NFR-Req（Q1〜Q10=A）/ NFR-Design（Q1〜Q10=A + 矛盾解消 3）/ Infra（Q1〜Q7=A）

## 生成物（`backend/src/reel/`）

| ファイル | 役割 | 対応 ALG / Story |
|---|---|---|
| `models.py` | Pydantic v2 DTO（frozen/extra=forbid） | domain-entities 全般 |
| `catalog.py` | `ProductCatalogPort` + `DummyCatalogAdapter`（プロセス内）+ `CachedCatalog`（cache-aside） | ALG-CATALOG / REEL-CAT |
| `dummy_catalog.json` | MVP 固定カタログ（5 商品、外部に出ない） | FR-REEL-04 / §8 A-10 |
| `ranking.py` | `CandidateSourcePort` + `PurchaseHistoryHeuristicSource` + `rank`（決定論リランク）+ `apply_boost`（深夜ブースト） | ALG-RANK/BOOST / US-02-01/05 |
| `bedrock_client.py` | `TextGenerator` Protocol + `BedrockTextGenerator`（薄ラッパ、DI 注入） | R-PAT-LLM-01 |
| `labels.py` | `generate_pitch` / `generate_label` / `is_safe`（モデレーション + テンプレフォールバック + 24h 重複防止） | ALG-PITCH/LABEL / US-02-05 |
| `special_link.py` | `generate_special_link`（純関数、短縮禁止、環境ガード） | ALG-LINK / US-02-02 |
| `cursor.py` | `ReelCursor` + encode/decode（不透明・round-trip） | REEL-PAGE / Q9 |
| `feed.py` | `build_reel`（候補→リランク→ブースト→カード化→カーソル、ラベル同期確定） | RLC-01 / US-02 全般 |
| `transition.py` | `record_transition`（先行 Safeguard ゲート fail-closed + 冪等記録 + EXP +1 同期） | ALG-TRANSITION / US-02-02 |
| `handlers/feed.py` | `GET /v1/reel`（require_owner / cursor・limit 検証） | REEL-API-03 |
| `handlers/transition.py` | `POST /v1/amazon-transitions`（require_owner / 409 / DI） | REEL-API-04/07 |

## テスト（`backend/tests/reel/`）

| ファイル | 観点 | PBT |
|---|---|---|
| `strategies.py` | ドメインジェネレータ（購入履歴/価格/StressLevel/TimeBucket/Flags/ProductMeta） | PBT-07 |
| `test_ranking.py` | カテゴリ一致/NG 除外/既出抑制/遷移後 cooldown/深夜加点 | PBT-03（score=Σ・決定論・NG 除外）|
| `test_boost.py` | 発火条件の真理値表/高単価先頭挿入 | 価格範囲不変条件 |
| `test_special_link.py` | dev仮/prd未承認ブロック/短縮禁止/純関数 | PBT-02（ASIN round-trip）|
| `test_transition.py` | allow/warn/block(409)/fail-closed/冪等 | PBT-04（冪等性・月間カウント=ユニーク数）|
| `test_labels.py` | モデレーション/フォールバック非空/24h 重複 | — |
| `test_cursor.py` | None/不正フォールバック/単調増加 | PBT-02/05（encode-decode round-trip）|
| `test_handler_feed.py` | 200/401/400/必須フィールド | — |
| `test_handler_transition.py` | 201/401/409/冪等 | — |

## 検証メモ
- **ロジック + PBT テスト 40 件 pass**（`.venv` で coverage 無効化して実行確認）
- `handlers/*` の 2 テストは本ローカル `.venv` に `aws_xray_sdk`（Powertools tracer extra）未導入のため collection 不可。**Unit-1 と同じ環境制約**で、Build and Test（フル依存）で実行する。コード・diagnostics は確認済み
- S-03 は `shared/safeguard-policy/python` の `decide_allow` 正本を参照（再実装せず、SG-10）。`backend/conftest.py` に shared python パスを追加
- EXP は B-13 が同期付与（Achievements、Unit-2 スキーマ）、非同期は嗜好ベクトル学習（B-08）のみ
- 実行・カバレッジ計測・型生成・schemathesis は Build and Test へ
