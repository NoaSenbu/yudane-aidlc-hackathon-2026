"""ローカル開発用の ASGI app wrapper（Phase A1 Step A1.4）。

`debate_handler(payload, context)` は AgentCore Runtime SDK 用のシグネチャ。
ローカル開発（`uvicorn` 直接または `agentcore dev`）では FastAPI でラップして
HTTP POST /invocations を受け付ける。

参照:
- aidlc-docs/construction/plans/unit-3-debate-mobile-expo-mvp-plan.md §2.4
- aidlc-docs/construction/unit-3-debate/code/local-dev-guide.md
"""

from __future__ import annotations

import json
import logging
from types import SimpleNamespace
from typing import Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from backend.src.debate.local_mode import (
    is_local_mode,
    local_parse_jwt_actor_id,
)
from backend.src.debate.main import debate_handler

_LOGGER = logging.getLogger(__name__)

app = FastAPI(title="YUDANE Debate Local Dev Server")

# Mobile（Expo Go on iOS Simulator / Android Emulator）からの CORS を許容。
# ローカル開発専用のため `*` でよい（本番デプロイでは別経路、API Gateway 統合）。
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["POST", "GET", "OPTIONS"],
    allow_headers=["*"],
)


@app.get("/health")
async def health() -> dict[str, str]:
    """ヘルスチェック。Mobile 起動時の疎通確認に使用。"""
    return {"status": "ok", "service": "yudane-debate-local"}


@app.post("/invocations")
async def invocations(request: Request) -> StreamingResponse:
    """Mobile / curl からの POST /invocations を受け、debate_handler の async generator を NDJSON で返す。

    AgentCore Runtime context.user.sub に相当する actor_id は、ローカルモードでは
    LOCAL_USER_ID 環境変数（既定 `local-user`）から取得する（JWT 認証バイパス）。
    """
    payload = await request.json()
    actor_id = local_parse_jwt_actor_id() if is_local_mode() else "anonymous"
    context = SimpleNamespace(user=SimpleNamespace(sub=actor_id))

    _LOGGER.info(
        "invocation_received",
        extra={"actor_id": actor_id, "action": payload.get("action")},
    )

    async def stream_body():
        try:
            async for event in debate_handler(payload, context):
                line = json.dumps(event, ensure_ascii=False, default=str) + "\n"
                yield line.encode("utf-8")
        except Exception as exc:  # noqa: BLE001
            _LOGGER.exception("invocation_failed")
            error_event = {
                "type": "error",
                "metadata": {"reason": "internal_error", "detail": str(exc)},
            }
            yield (json.dumps(error_event, ensure_ascii=False) + "\n").encode("utf-8")

    return StreamingResponse(stream_body(), media_type="application/x-ndjson")


__all__ = ["app"]
