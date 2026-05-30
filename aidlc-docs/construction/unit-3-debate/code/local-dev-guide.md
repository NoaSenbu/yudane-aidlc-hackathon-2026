# Unit-3 Debate — ローカル開発ガイド（L2 MVP 動作確認）

> ローカル PC で Backend を `agentcore dev --port 8080` 起動 + 実 Bedrock Haiku 4.5 + in-memory DDB/Memory で動作させ、Mobile 純ロジックから疎通確認する手順書。
>
> 参照: [Phase 2 Plan §1 Step 4 / Step 9](../../plans/unit-3-debate-code-generation-phase2-plan.md) / [tech-stack-decisions.md §3](../nfr-requirements/tech-stack-decisions.md)
>
> 作成: 2026-05-30 / 担当: Member B / 動作確認レベル: **L2 ローカル LLM 駆動 MVP**

---

## 0. このドキュメントの目的

Phase 2 完了時点で、**Mobile アプリの実機ビルドなしに** ローカル PC で論破ロジックの動作確認ができる手順を提供する。L1 / L2 / L3 の段階的 MVP 動作確認のうち、**L2** が本ドキュメントの対象。

| レベル | 内容 | 本ガイドの対象 |
|---|---|---|
| L1 UI 単体動作 | Direction D の DebateScreen 純ロジックのみ（vitest）| 単体テスト経由 |
| **L2 ローカル LLM 駆動** | **`agentcore dev` + 実 Bedrock + in-memory DDB/Memory** | **★本ガイド** |
| L3 完全 MVP | dev 環境統合（実 DDB / Memory / Cognito MFA）| Phase 1 Step 8 + Phase 5 |

---

## 1. 前提条件

### 1.1 AWS 側の前提

- [ ] **AWS Builder ID** で `ap-northeast-1` アカウントへのアクセス可能
- [ ] **Bedrock Claude Haiku 4.5 のモデルアクセス申請**が承認済み（AWS コンソール → Bedrock → Model access）
- [ ] ローカル PC に `~/.aws/credentials` で apne1 アクセス情報が設定済み（`aws configure`）

### 1.2 開発環境

- macOS（または Linux）
- Python 3.13.2（pyenv `hackson` virtualenv 推奨）
- bash / zsh

### 1.3 必要な依存ライブラリ（Phase 1 + Phase 2 累計）

```bash
# pyenv hackson virtualenv で install 済（Phase 1 で完了）
pip list | grep -E "boto3|pytest|pydantic|hypothesis|moto|aws-lambda-powertools"
```

Phase 2 開始時に追加で:

```bash
pip install bedrock-agentcore strands-agents
```

---

## 2. ローカル起動手順

### 2.1 環境変数設定

`.env.local` ファイルを `backend/` 直下に作成:

```bash
# ~/dev/.../backend/.env.local
DEBATE_LOCAL_MODE=true
ENV_NAME=dev
AWS_REGION=ap-northeast-1
LOCAL_USER_ID=local-user
COOLDOWNS_TABLE_NAME=yudane-debate-dev-cooldowns
```

ターミナルでロード:

```bash
cd backend
set -a && source .env.local && set +a
```

### 2.2 SSM `/yudane/dev/debate/model-id` 設定

ローカルモードでは SSM 経由ではなく環境変数で直接モデル ID を渡す方が簡単。`get_model_id` を override する形で `MODEL_ID` 環境変数を読む拡張は Phase 4 以降で検討（B-308 backlog）。

Phase 2 では `aws ssm put-parameter` で dev 環境に登録（Phase 1 Step 8 デプロイ時に CDK で自動作成済の想定）:

```bash
aws ssm put-parameter \
  --name /yudane/dev/debate/model-id \
  --value "anthropic.claude-haiku-4-5" \
  --type String \
  --overwrite \
  --region ap-northeast-1
```

### 2.3 Backend 起動

```bash
cd backend

# `agentcore dev` で uvicorn が BedrockAgentCoreApp を hot reload 起動
agentcore dev src/debate/main:app --port 8080
```

**期待出力**:
```
INFO: Started server process [...]
INFO: Application startup complete.
INFO: Uvicorn running on http://0.0.0.0:8080
```

### 2.4 別ターミナルから疎通確認

```bash
curl -X POST http://localhost:8080/invocations \
  -H "Content-Type: application/json" \
  -d '{
    "action": "start_session",
    "user_input": "でも欲しい",
    "asin": "B01ABC1234",
    "trigger": "reel_skip"
  }'
```

**期待出力**（Strands Agent native event の NDJSON ストリーミング）:
```json
{"data": "[FACT] 時給換算で 11 時間分の労働量じゃないですか?"}
{"data": "[PSYCHOLOGY] 結局買って結果的に使ってるじゃないですか"}
...
{"event": {"type": "session_complete"}}
```

---

## 3. クールダウン動作確認

### 3.1 連続拒否で 3 回目に cooldown 発火（COOLDOWN-02）

```bash
# 拒否を 3 回連続で送信
for i in 1 2 3; do
  echo "Refuse $i:"
  curl -X POST http://localhost:8080/invocations \
    -H "Content-Type: application/json" \
    -d '{
      "action": "refuse",
      "user_input": "やっぱりいらない",
      "asin": "B01ABC1234",
      "trigger": "reel_skip"
    }'
  echo ""
done
```

**期待結果**:
- 1 回目: `{"type": "debate.refused", "metadata": {"consecutive_refuses": 1, "cooldown_triggered": false}}`
- 2 回目: `{"type": "debate.refused", "metadata": {"consecutive_refuses": 2, "cooldown_triggered": false}}`
- 3 回目: `{"type": "debate.refused", "metadata": {"consecutive_refuses": 3, "cooldown_triggered": true, "cooldown_until": "..."}}`

### 3.2 クールダウン中の論破セッション開始 → cooldown_triggered

```bash
curl -X POST http://localhost:8080/invocations \
  -H "Content-Type: application/json" \
  -d '{
    "action": "start_session",
    "user_input": "またですか?",
    "asin": "B01XYZ9876",
    "trigger": "reel_skip"
  }'
```

**期待結果**: `{"type": "debate.cooldown_triggered", "metadata": {"cooldown_until": "..."}}`

---

## 4. ストレスレベル別の M-2 reward 軸動作確認

### 4.1 stress_level=high で reward 軸が必ず含まれる（PBT-03 不変条件）

深夜帯 + cart_intercepts 多 + late_night_signin で score >= 4 → high:

```bash
curl -X POST http://localhost:8080/invocations \
  -H "Content-Type: application/json" \
  -d '{
    "action": "start_session",
    "user_input": "疲れてる",
    "asin": "B01ABC1234",
    "trigger": "reel_skip",
    "client_signals": {
      "recent_cart_intercepts": 5,
      "recent_debate_refuses": 1,
      "last_signin_at_late_night": true,
      "current_hour_jst": 23
    }
  }'
```

**期待結果**: ストリーム内に `[REWARD]` セクションマーカーが含まれる（M-2 ストレス × ご褒美軸）。

### 4.2 stress_level=low で reward 軸が含まれない

```bash
curl -X POST http://localhost:8080/invocations \
  -H "Content-Type: application/json" \
  -d '{
    "action": "start_session",
    "user_input": "迷う",
    "asin": "B01ABC1234",
    "trigger": "product_dwell",
    "client_signals": {
      "recent_cart_intercepts": 0,
      "recent_debate_refuses": 0,
      "last_signin_at_late_night": false,
      "current_hour_jst": 14
    }
  }'
```

**期待結果**: `[FACT]` / `[PSYCHOLOGY]` のみ含まれ、`[REWARD]` は含まれない（PROMPT-02 不変条件）。

---

## 5. kill-switch 緊急停止の確認（PAT-D-COST-04）

dev 環境の SSM kill-switch を `enabled` に切替:

```bash
aws ssm put-parameter \
  --name /yudane/dev/debate/kill-switch \
  --value "enabled" \
  --type String \
  --overwrite \
  --region ap-northeast-1
```

その後、論破セッション開始リクエストを送ると:

```json
{"type": "error", "metadata": {"reason": "kill_switch.enabled"}}
```

が即座に返る（Bedrock を呼ばない、コスト保護）。動作確認後は `disabled` に戻す:

```bash
aws ssm put-parameter \
  --name /yudane/dev/debate/kill-switch \
  --value "disabled" \
  --type String \
  --overwrite \
  --region ap-northeast-1
```

---

## 6. Mobile 純ロジックとの統合確認（E2E-01 vitest）

ローカル Backend を直接叩く統合テストはまだ無いが、Mobile 純ロジックの E2E は msw モックで完結している:

```bash
cd mobile
npx vitest run src/test/e2e/debate-e2e-01.test.ts
```

**期待結果**: 2 テストとも green（`E2E-01: Cart Intercept → 論破 → 翻意 → Amazon 遷移` + クールダウンシナリオ）。

---

## 7. トラブルシューティング

### 7.1 `pip install bedrock-agentcore strands-agents` で依存解決エラー

`--no-deps` で個別 install を試す:
```bash
pip install --no-deps bedrock-agentcore strands-agents
pip install <欠落パッケージ>
```

### 7.2 `ImportError: No module named 'strands'`

`strands-agents` がインストールされていない可能性。`pip list | grep strands` で確認、未インストールなら再 install。

### 7.3 `botocore.exceptions.NoCredentialsError`

`aws configure` で apne1 認証情報を設定。または環境変数で:
```bash
export AWS_PROFILE=default
```

### 7.4 `AccessDeniedException: User is not authorized to perform: bedrock:InvokeModelWithResponseStream`

Bedrock コンソールで Claude Haiku 4.5 のモデルアクセス申請が承認されていない。AWS コンソール → Bedrock → Model access から申請。

### 7.5 `agentcore dev` が起動しない

直接 uvicorn を呼ぶ代替手段:
```bash
python -m uvicorn src.debate.main:app --port 8080 --reload
```

---

## 8. コスト管理

| 項目 | 概算 |
|---|---|
| 1 セッション（論破 30 ターン）| Bedrock Haiku 4.5 で約 $0.005 |
| 1 日の動作確認（10 セッション）| 約 $0.05 |
| 1 ヶ月（毎日 10 セッション）| 約 $1.5 |

**$10/日の上限を Cost Anomaly Detection（Unit-1 既存）で監視**。動作確認は最小限に留め、PBT / unit テストでの検証を優先する。

---

## 9. Phase 3 以降の展開

Phase 2 では「Backend 単体ローカル疎通 + Mobile 純ロジックの E2E」までを範囲とする。**Mobile 実機ビルド + Cognito MFA + 実 Memory** は以下のフェーズで段階的に追加:

| Phase | 追加内容 |
|---|---|
| Phase 1 Step 8（保留中、ユーザー承認待ち）| dev 環境への CDK デプロイ（debate-stack）|
| Phase 3 | Strands graceful shutdown 80s / Memory streamDeliveryResources / Bedrock Guardrails 多層 |
| Phase 4 | custom Memory Strategy `m1_m2_axis_extractor` / PBT 全面適用 |
| Phase 5 | RuntimeEndpoint canary / EAS Build dev 実機ビルド |
| Phase 6 | 性能テスト / 決勝前カナリアリリース |

実機 Mobile アプリのビルドは決勝直前カナリアリリース時に着手する（B-309 backlog 候補）。
