# Unit-2 — Code Summary: B-01 / auth API Lambda（Step 5-7）

## 生成ファイル
| ファイル | 役割 |
|---|---|
| `backend/src/auth/post_confirmation.py` | B-01 Post Confirmation（冪等初期化、ALG-INIT） |
| `backend/src/auth/pre_token_generation.py` | B-01 Pre Token Generation（claim 付与、ALG-CLAIM） |
| `backend/src/auth/handlers/responses.py` | 共通レスポンス（DomainError→ProblemDetails） |
| `backend/src/auth/handlers/profile.py` | POST/PATCH profile（段階保存 + require_owner、US-AUTH-01） |
| `backend/src/auth/handlers/safeguard_debt.py` | 負債申告/解除リクエスト（US-AUTH-03） |
| `backend/tests/auth/fakes.py` | インメモリリポジトリ（テスト用） |
| `backend/tests/auth/test_post_confirmation.py` | 冪等初期化 + claim |
| `backend/tests/auth/test_profile_handler.py` | 段階保存完了 + 負債連携 + 認可エラー |

## ルール準拠
- INIT-01〜04 / ONB-02/06 / DEBT-01/04 / SEC-01〜03
- SECURITY-05（Pydantic/JSON 検証）/ SECURITY-08（require_owner）/ ERR-05（ProblemDetails）
- ドメインロジックを純関数（apply_profile_update / apply_debt_action / initialize_user / build_claims）に分離し、インメモリ fake でテスト
- DynamoDB 実装は遅延 import でハンドラに注入（テスト時は boto3 不要）

## 次ステップ
Step 8: B-08 バッチ（日次/週次）
