---
inclusion: fileMatch
fileMatchPattern: '*.py'
---

# Python 3.13 Lambda 規則

> `.py` ファイルを編集しているときに自動で適用される steering。
> 横断的なプロダクト規則は [AGENTS.md](./AGENTS.md)、プロジェクト構造は [structure.md](./structure.md)、API 契約は [api-contracts.md](./api-contracts.md) を参照。

---

## 1. Lint・フォーマッタ

| 項目 | 採用 | 備考 |
|---|---|---|
| ruff | `ruff check` + `ruff format` | target: `py313`。rules は `E`, `F`, `W`, `I`, `B`, `UP`, `S`, `ASYNC`, `RUF` |
| mypy | `--strict` | `disallow_untyped_defs = true` を全 Unit で強制 |
| import 並び替え | ruff `I` rule | isort 互換 |
| docstring style | Google style | mypy + ruff の `D` rule で整合 |

具体的な設定値は `pyproject.toml` に配置する。

## 2. 型安全性

- 関数の引数・戻り値に **完全型付け** を必須
- `typing.Any` は最小限に限定。`TypedDict` / `pydantic.BaseModel` / `dataclasses` を優先
- Pydantic v2 を採用（Lambda のリクエスト / レスポンス検証）
- Optional は `X | None`（PEP 604）を使用、`Optional[X]` は避ける

## 3. 非同期処理

- Bedrock ストリーミング等の I/O 多重は `asyncio` または `boto3` の `botocore` + `aiohttp` を利用
- Lambda ハンドラ本体は同期関数のままとし、内部で `asyncio.run()` で async 処理をラップ

## 4. エラーハンドリング

- 例外は具体的な型で catch（`except Exception as e:` の包括 catch は禁止）
- 包括 catch が必要な境界（ハンドラ最外周）は `logger.exception()` で構造化ログ出力 + 定型エラーレスポンス
- 例外クラスは `backend/src/common/exceptions/` で集約定義

## 5. 命名規則

### 5.1 ファイル・ディレクトリ

| 対象 | 規則 | 例 |
|---|---|---|
| Python ファイル | snake_case | `debate_session.py`、`user_profile.py` |
| ディレクトリ | kebab-case（プロジェクト全体の一貫性を優先） | `debate-session/`、`user-profile/` |

### 5.2 識別子

| 対象 | 規則 | 例 |
|---|---|---|
| クラス | PascalCase | `class DebateSession:` |
| 関数 / 変数 | snake_case | `def start_debate():`、`max_tokens = 512` |
| 定数 | UPPER_SNAKE_CASE | `MAX_DEBATE_TURNS = 3` |

### 5.3 ドメイン ID（共通）

- Lambda コンポーネント: `B-XX`（Backend）/ `S-XX`（Shared）
- FR / NFR: `FR-<領域>-<番号>`（例: `FR-DEBATE-01`）

## 6. Import 順序

ruff `I` rule で自動整列。グループは以下の順（PEP 8 準拠）:

1. Standard library（`asyncio`, `json` 等）
2. Third-party（`boto3`, `pydantic`, `aiohttp` 等）
3. Local（`backend.src.common.*` 等）

Circular import は CI で pylint 検知。

## 7. ファイルサイズ・責務

- 1 ファイル 400 行以内
- 1 ファイル 1 関心事。`utils.py` への雑多集約は禁止。関心事ごとにディレクトリを分け `__init__.py` でエクスポート制御
- 未使用 import / 変数 / 関数は ruff で **エラー扱い**

## 8. コメント方針

- コメントは「なぜ」を書く。「何を」はコード自体で明らかに
- TODO にはチケット番号や期限を必須: `# TODO(#123): 2026-06 までに B-03 と整合`

## 9. docstring（Google style、日本語）

```python
def start_debate(user_id: str, product_asin: str, context: DebateContext) -> AsyncIterator[str]:
    """論破セッションを開始する。

    Bedrock Claude Haiku 4.5 にストリーミングで接続し、ユーザーの嗜好ベクトルと
    コンテキスト信号（カレンダー予定・時刻・直近購入履歴）をプロンプトに組み立てる。

    Args:
        user_id: 論破対象のユーザー ID
        product_asin: 対象商品の ASIN
        context: プロンプト組立用のコンテキスト

    Yields:
        Bedrock からのストリーミングチャンク（文字列）

    Raises:
        DebateCooldownError: クールダウン中（FR-DEBATE-05）
    """
```

## 10. テスト（Python 側）

| レイヤ | ツール | 配置 |
|---|---|---|
| Unit Test | `pytest` | `tests/test_*.py` |
| Property-Based Test | `hypothesis` | Unit Test と同居、`@given` で識別 |
| Integration Test | `pytest` + moto | `backend/tests/integration/` |
| Contract Test | `schemathesis` | `backend/tests/contract/` |

**カバレッジ目標**:

- Unit Test: Line **80%+** / Branch **70%+**（生成ファイル除外）
- PBT: PBT-01〜10 各カテゴリに対し 1 つ以上のプロパティ実装
- Contract Test: Schemathesis で全エンドポイントの契約違反レスポンス 0

### 10.1 TDD サイクル（クラシック / Detroit、Backend Lambda 必須）

[AGENTS.md §12](./AGENTS.md#12-tdd-開発スタイル全-unit-必須) の TDD 開発スタイルを Python 側で具体化:

| Phase | やること | ツール |
|---|---|---|
| **Red** | 失敗する `pytest` example test を 1 ケース書く | `pytest` `assert` |
| **Green** | テストが通る最小コードを書く（仮実装可、戻り値直書きでも OK） | 実装ファイル |
| **Refactor** | 重複排除・命名整理・抽象化、テストは触らない | エディタ |
| **PBT 補強** | `hypothesis` の `@given(...)` を同テストファイルに追加 | `hypothesis` |

#### クラシック TDD の流れ（Backend Lambda 例）

```
Test 1 (Red): 純粋関数 1 つ → 戻り値の最小ケース
Test 2 (Red): エラーケース → ValidationError 期待
Test 3 (Red): エッジケース → 境界値 / null / 空配列
   ↓ 各 Red を 1 つずつ Green に倒す
   ↓ Mock 最小限、内部から組み立てる
最後に Hypothesis で @given(strategy) を property 化
```

#### TDD 例外（テストファースト緩和、AGENTS.md §12.3）

- Pydantic v2 の `BaseModel` 純粋宣言（フィールドのみ、`@field_validator` なし）
- 単純な定数定義 / 設定（`SAFEGUARD_LIMITS` 等）
- Lambda Powertools の boilerplate import 部分
- 自動生成された型ファイル（`backend/src/common/models/api.py`）

例外時は PR description に「TDD 例外: ◯◯」と明記。

#### PBT との統合（PBT-01〜10 と TDD の関係）

| PBT カテゴリ | TDD サイクル中の位置 |
|---|---|
| PBT-01 Round-trip | Refactor 後の補強で `@given` を追加 |
| PBT-02 Invariant | Green が通った直後に property を追加 |
| PBT-06 Stateful | RuleBasedStateMachine を Refactor 後に追加 |
| PBT-08 Shrinking | 失敗時に `--hypothesis-seed` でリプレイ可能に

## 11. セキュリティ（SECURITY Extension 抜粋）

- ユーザー入力は **Pydantic v2 で検証必須**。無検証の `json.loads(request_body)` 禁止
- `print` / `logger.info(plain)` での機密情報出力禁止。`logger.info(..., extra={...})` の構造化ログ経由
- 認証情報はコード直書き禁止（環境変数 / Secrets Manager / SSM Parameter Store）
- IDOR 対策: パスパラメータの `{userId}` と JWT claim の `sub` が一致することを Lambda 冒頭で検証（SECURITY-08）
- 詳細は [AGENTS.md](./AGENTS.md) §セキュリティ を参照

## 12. 採用しないもの（Python 側）

- 決済サンドボックス（Stripe / Square 等、決済は Amazon 側で完結）
- Step Functions（時間差制御は EventBridge Scheduler 単独）
