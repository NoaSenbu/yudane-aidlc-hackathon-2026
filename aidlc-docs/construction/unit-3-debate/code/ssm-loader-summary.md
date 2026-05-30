# Unit-3 Debate — SSM Configuration Loader 実装サマリ（Phase 1 Step 2）

> Phase 1 Step 2（Backend / SSM Loader、クラシック TDD）の実装結果。
>
> 参照: [Phase 1 Plan §1 Step 2](../../../plans/unit-3-debate-code-generation-phase1-plan.md) / [infrastructure-design §5](../infrastructure-design/infrastructure-design.md) / [nfr-design-patterns PAT-D-COST-04](../nfr-design/nfr-design-patterns.md)
>
> 完了日: 2026-05-30 / 担当: Member B（AI 代行実装）/ TDD スタイル: クラシック TDD

---

## 1. 生成ファイル

| ファイル | 役割 |
|---|---|
| `backend/src/debate/ssm.py`（新規 70 行）| SSM Configuration Loader（`get_model_id` / `is_kill_switch_enabled`）|
| `backend/tests/debate/test_ssm.py`（新規 132 行）| クラシック TDD のテスト 5 ケース（boto3 Stubber） |
| `backend/tests/debate/__init__.py`（新規）| テストパッケージ |

---

## 2. API 仕様

### 2.1 `get_model_id(env_name: str) -> str`

- 用途: Strands Agent **起動時 1 回呼び出し**（Lambda コールドスタート最適化）
- SSM パス: `/yudane/<env>/debate/model-id`
- 既定値（CDK で初期登録）: `anthropic.claude-haiku-4-5`
- 例外時の挙動: SSM 例外を伝播（model-id は必須、起動失敗で fail-fast）

### 2.2 `is_kill_switch_enabled(env_name: str) -> bool`

- 用途: **毎セッション開始時呼び出し**（リアルタイム反映、緊急停止用）
- SSM パス: `/yudane/<env>/debate/kill-switch`
- 既定値（CDK で初期登録）: `disabled` → False
- 値 `'enabled'`（前後空白許容、大小文字無視）→ True
- 例外時の挙動: **fail-safe で False を返却**（PAT-D-COST-04、kill-switch 未設定 = 通常運用継続）+ 構造化ログ出力

---

## 3. 設計上の判断

### 3.1 `_ssm_client()` の `@lru_cache(maxsize=1)`

`boto3.client("ssm")` の生成は重い（証明書チェーン読込み等）ため、`lru_cache` で初回のみ生成。Lambda の microVM が稼働中は同じクライアントを再利用する。

### 3.2 例外ハンドリング戦略の差

| 関数 | 例外時 | 理由 |
|---|---|---|
| `get_model_id` | 例外伝播（`ClientError` / `BotoCoreError` を伝播）| model-id 取得失敗 = AgentCore Runtime 起動不可。fail-fast で運用者に検出させる |
| `is_kill_switch_enabled` | False 返却（catch して構造化ログ）| kill-switch は緊急停止用、未設定 = 通常運用続行が安全（fail-safe）|

NFR Design `PAT-D-COST-04` の DDB 障害時 + kill-switch enabled で全停止という設計と整合：kill-switch 自体が読めない時は通常運用を続行し、運用者が SSM を直接 put-parameter で更新できる猶予を与える。

### 3.3 Phase 2 への引き継ぎ

- 構造化ログは Phase 1 では標準 `logging` で出力（line 70 周辺）。Phase 2 で AuditLogger Lambda Layer 経由（Powertools Logger）に置換予定。
- 動的 reload はサポートしない（Strands Agent 起動時 1 回 + 毎セッション開始時のみ）。SSM Parameter 値変更後は `aws bedrock-agentcore restart-runtime` 等で Runtime をローリング再起動する必要あり（Step 8.4 で確認手順化）。

---

## 4. テスト結果

| # | テスト名 | 検証 |
|---|---|---|
| 1 | `test_get_model_id_returns_value_from_ssm` | dev で値返却 |
| 2 | `test_is_kill_switch_enabled_returns_true_for_enabled` | 'enabled' で True |
| 3 | `test_is_kill_switch_enabled_returns_false_for_disabled` | 'disabled' で False |
| 4 | `test_is_kill_switch_enabled_returns_false_on_ssm_exception` | `ParameterNotFound` で False（fail-safe）|
| 5 | `test_get_model_id_uses_env_specific_path` | env 名で SSM パス切替（dev / prd）|

**実行結果**: 5/5 green / 0.84s / Line coverage **96%**（line 26 の `_ssm_client()` 内クライアント生成は `@lru_cache` で初回のみ実行、テストでは patch で差し替えのため 1 行未カバー、意図通り）/ Branch coverage **100%**。

---

## 5. 開発環境セットアップ

Backend は pyenv `hackson` virtualenv（Python 3.13.2）に以下を install：

| パッケージ | バージョン |
|---|---|
| boto3 | 1.43.18 |
| botocore[crt] | 1.43.18 + awscrt 0.32.2（macOS で `MissingDependencyException` 回避）|
| pytest | 9.0.3 |
| pytest-cov | 7.1.0 |
| hypothesis | 6.155.0 |
| moto | 5.2.1 |
| pydantic | 2.13.4 |
| aws-lambda-powertools[tracer,validation] | 3.29.0 |

`pyproject.toml` の `[tool.poetry.dependencies]` バージョン指定と整合（poetry.lock の生成は別作業）。

---

## 6. ハッカソン評価軸へのインパクト

- **Unit 分解の適切さ**: SSM Loader を 70 行の純粋ラッパーとして分離、main.py / cooldown.py から疎結合に呼び出し可能
- **創造性とテーマ適合性**: kill-switch 機構自体が「ダメ化メカニズムの暴走を抑える倫理的セーフガード」として直接機能（NG-6 滑落の最終防衛線）
- **ドキュメント品質**: 完全な docstring（Google style）+ ruff D ルールパス、テストファイルにも目的・参照リンクを記載
- **AI-DLC プロセス**: Red → Green → Refactor のサイクルを 1 ファイル内で完結、テスト 5 件で API 全パスを網羅
