# Unit-2 — Code Summary: OpenAPI auth 詳細化（Step 1）

## 生成・更新ファイル
| ファイル | 変更 |
|---|---|
| `shared/schema/components/schemas/auth.yaml` | 新規（UserProfile / SafeguardSettings / Achievement / HomeSnapshot） |
| `shared/schema/paths/auth.yaml` | userProfile に POST/PATCH 詳細スキーマを非破壊追記 |
| `shared/schema/openapi.yaml` | components.schemas に auth スキーマ参照追加 |
| `shared/schema/types/api.ts` | UserProfile/SafeguardSettings/Achievement/HomeSnapshot 型追記 |
| `backend/src/common/models/api.py` | 同 Pydantic モデル追記 |
| `backend/src/common/models/__init__.py` | エクスポート追加 |

## 規約準拠
- api-contracts §2/§6（非破壊的変更: 省略可能フィールド + 新規スキーマ追加。骨格 POST/PATCH は維持）
- 型生成は CI で実生成・差分検証（本コミットは代表スナップショット更新）

## 次ステップ
Step 2: Backend ドメインモデル + リポジトリ
