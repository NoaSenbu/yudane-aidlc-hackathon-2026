# Unit-2 — Code Summary: M-11 AuthModule / Onboarding / Home（Step 9-12）

## 生成ファイル
| ファイル | 役割 |
|---|---|
| `mobile/src/features/auth/auth-module/auth-machine.ts` | MFA チャレンジ駆動状態機械（純ロジック、PAT2-MFA-01） |
| `mobile/src/features/auth/auth-module/amplify-auth.ts` | Amplify Auth v6 ラッパー interface |
| `mobile/src/features/auth/auth-module/auth-token-provider.ts` | Unit-1 AuthTokenProvider 実装 |
| `mobile/src/features/auth/auth-module/auth-machine.test.ts` | 状態遷移 + token provider テスト |
| `mobile/src/features/auth/onboarding/onboarding-store.ts` | Zustand slice + nextStep 冪等ロジック |
| `mobile/src/features/auth/onboarding/onboarding-store.test.ts` | 段階保存冪等 PBT |
| `mobile/src/features/auth/home/use-home-snapshot.ts` | Home 概況 hook（Q6=A） |

## ルール準拠
- MFA-01〜07（状態機械、AuthTokenProvider 結線）/ PAT2-MFA-01 / PAT2-ONB-01
- ONB-03（段階保存 step は後退しない、PBT で検証）
- ALG-HOME（概況のみ、詳細は Unit-8）
- Amplify 依存を amplify-auth.ts に隔離し、状態機械・store は純ロジックでテスト
- NFR2-COV（85%）

## 次ステップ
Step 13-14: auth-stack + snapshot
