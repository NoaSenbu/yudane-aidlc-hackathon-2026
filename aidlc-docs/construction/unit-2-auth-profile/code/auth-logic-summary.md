# Unit-2 — Code Summary: ドメインモデル + ロジック（Step 2-4）

## 生成ファイル
| ファイル | 役割 |
|---|---|
| `backend/src/auth/models/entities.py` | UserEntity / SafeguardStateEntity / AchievementEntity |
| `backend/src/auth/repositories/protocols.py` | リポジトリ Protocol（疎結合） |
| `backend/src/auth/repositories/dynamodb.py` | boto3 DynamoDB 実装（4 テーブル、PK=userId） |
| `backend/src/auth/onboarding.py` | 段階保存（冪等 max step、ALG-ONBOARD） |
| `backend/src/auth/level.py` | Lv/称号判定（ALG-LEVEL、純関数） |
| `backend/src/auth/debt_safeguard.py` | 負債 72h クーリングオフ（ALG-DEBT、Unit-1 S-03 連携） |
| `backend/tests/auth/test_onboarding.py` | 段階保存 idempotency PBT |
| `backend/tests/auth/test_level.py` | Lv 単調増加 PBT |
| `backend/tests/auth/test_debt_safeguard.py` | 72h クーリングオフ |

## ルール準拠
- ONB-01〜06 / LV-01〜04 / DEBT-01〜05
- PBT-04（オンボ段階保存の冪等性）/ LV 単調増加 invariant
- 判定ロジックは純関数 + Protocol でリポジトリ疎結合（テスト容易）
- US-AUTH-03 の判定本体は Unit-1 SafeguardPolicy を再利用（debt_safeguard は状態管理のみ）

## 次ステップ
Step 5: B-01 AuthEdgeLambda
