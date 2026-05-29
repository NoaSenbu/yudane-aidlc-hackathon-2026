# Unit-1 Platform — Code Summary: S-03 SafeguardPolicy（Step 5-6）

## 生成ファイル

| ファイル | 役割 |
|---|---|
| `shared/safeguard-policy/package.json` / `tsconfig.json` | TS パッケージ |
| `shared/safeguard-policy/src/constants.ts` | 定数（ratio / cooldown / attack steps / warn 0.8） |
| `shared/safeguard-policy/src/decide-allow.ts` | ALG-SG 段階判定（純関数） |
| `shared/safeguard-policy/src/index.ts` | export 制御 |
| `shared/safeguard-policy/src/decide-allow.test.ts` | example + fast-check invariant/idempotency |
| `shared/safeguard-policy/python/safeguard_policy.py` | Python 同等実装 |
| `shared/safeguard-policy/python/test_safeguard_policy.py` | pytest + hypothesis |

## ルール準拠
- SG-01〜10（段階評価 / cooldown・quietWeek 最優先 / debt 半減 / 上限 block / 80% warn / remaining>=0 / 純関数 / Mobile-Backend 一致）
- NFR-PBT-02（invariant PBT-03: remaining>=0・実効上限<=上限 / idempotency PBT-04）、example 併存（PBT-10）、seed 固定（PBT-08）
- NFR-COV-02（目標 Line 95%+ / Branch 90%+）
- warn は遷移を止めず通知のみ（NG-6 罪悪感強要の回避）

## 次ステップ
Step 7: S-04 TelemetryContracts
