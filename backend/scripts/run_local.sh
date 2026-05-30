#!/bin/bash
# Unit-3 Debate ローカル開発サーバー起動スクリプト（Phase 2 Step 4.3）。
#
# `agentcore dev --port 8080` で uvicorn が BedrockAgentCoreApp を hot reload 起動。
# DEBATE_LOCAL_MODE=true で Cooldowns / Memory を in-memory に切替、実 Bedrock のみ呼び出す（L2 構成）。
#
# 参照: aidlc-docs/construction/unit-3-debate/code/local-dev-guide.md
#
# 使い方:
#   cd backend
#   bash scripts/run_local.sh

set -euo pipefail

# ワークスペースルートに移動（uvicorn の `backend.src...` パス解決のため）
cd "$(dirname "$0")/../.."

# .env.local から環境変数をロード
if [ -f backend/.env.local ]; then
  set -a
  source backend/.env.local
  set +a
else
  echo "Warning: backend/.env.local not found. Using default values."
  export DEBATE_LOCAL_MODE=true
  export ENV_NAME=dev
  export AWS_REGION=ap-northeast-1
  export LOCAL_USER_ID=local-user
fi

echo "Starting local dev server (Unit-3 Debate Backend)"
echo "  CWD=$(pwd)"
echo "  DEBATE_LOCAL_MODE=$DEBATE_LOCAL_MODE"
echo "  ENV_NAME=$ENV_NAME"
echo "  AWS_REGION=$AWS_REGION"
echo "  LOCAL_USER_ID=$LOCAL_USER_ID"
echo ""

# uvicorn で local_app:app を起動。`agentcore dev` は debate_handler のシグネチャを直接
# 受けないため、FastAPI でラップした local_app をエントリポイントにする。
# --reload-dir で backend/src 配下のみ監視（hot reload）。
# ワークスペースルートから `backend.src.debate.local_app:app` のフルパスで参照（PYTHONPATH=. で解決）。
exec python -m uvicorn backend.src.debate.local_app:app \
  --host 0.0.0.0 \
  --port 8080 \
  --reload \
  --reload-dir backend/src
