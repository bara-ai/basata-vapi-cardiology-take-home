import hmac
import json
import logging
import time
from contextlib import asynccontextmanager
from typing import Any

import httpx
from fastapi import FastAPI, Header, HTTPException, Request

from app.clients.emr import EMRClient
from app.config import Settings
from app.models.vapi import normalize_tool_calls
from app.services.tool_dispatch import dispatch_tool_call
from app.telemetry.logging import redact_event


logger = logging.getLogger(__name__)


def create_app(*, settings: Settings | None = None, emr_client: Any | None = None) -> FastAPI:
    app_settings = settings or Settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if app.state.emr_client is not None:
            yield
            return

        async with httpx.AsyncClient(
            base_url=app_settings.emr_base_url,
            timeout=app_settings.http_timeout_seconds,
        ) as http_client:
            app.state.emr_client = EMRClient(http_client)
            yield
            app.state.emr_client = None

    app = FastAPI(title="Basata Voice AI Webhook", lifespan=lifespan)
    app.state.emr_client = emr_client
    app.state.idempotency_cache = {}

    def require_vapi_bearer_token(authorization: str | None = Header(default=None)) -> None:
        expected = app_settings.vapi_webhook_secret
        supplied = authorization.removeprefix("Bearer ") if authorization else ""

        if not expected or not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Unauthorized")

        # Use a constant-time comparison at the public webhook boundary.
        if not hmac.compare_digest(supplied, expected):
            raise HTTPException(status_code=401, detail="Unauthorized")

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/vapi/webhook")
    async def vapi_webhook(
        request: Request,
        authorization: str | None = Header(default=None),
    ) -> dict[str, object]:
        require_vapi_bearer_token(authorization)

        payload = await request.json()
        message = payload.get("message", {})
        if message.get("type") != "tool-calls":
            return {"status": "ignored"}

        try:
            calls = normalize_tool_calls(payload)
        except json.JSONDecodeError:
            raw_tool_call = message.get("toolCallList", [])[0]
            function = raw_tool_call.get("function", {})
            result = {"status": "invalid_arguments"}
            return {
                "results": [
                    {
                        "name": raw_tool_call.get("name") or function["name"],
                        "toolCallId": raw_tool_call["id"],
                        "result": json.dumps(result),
                    }
                ]
            }

        mutation_tools = {
            "register_patient",
            "book_appointment",
            "cancel_appointment",
            "reschedule_appointment",
        }
        results = []
        for call in calls:
            started_at = time.perf_counter()
            cached_entry = app.state.idempotency_cache.get(call.tool_call_id)
            # Vapi may retry mutations; replay the original result instead of changing EMR state twice.
            if (
                app_settings.enable_idempotency_memory
                and call.name in mutation_tools
                and cached_entry is not None
                and cached_entry["expires_at"] > time.time()
            ):
                result = cached_entry["result"]
                results.append(result)
                logger.info(
                    "vapi_tool_result %s",
                    redact_event(
                        {
                            "call_id": call.call_id,
                            "tool_call_id": call.tool_call_id,
                            "tool_name": call.name,
                            "duration_ms": round((time.perf_counter() - started_at) * 1000),
                            "outcome": "idempotent_replay",
                        }
                    ),
                )
                continue

            if cached_entry is not None:
                app.state.idempotency_cache.pop(call.tool_call_id, None)

            result = await dispatch_tool_call(call, emr_client=app.state.emr_client)
            if app_settings.enable_idempotency_memory and call.name in mutation_tools:
                app.state.idempotency_cache[call.tool_call_id] = {
                    "expires_at": time.time() + app_settings.idempotency_ttl_seconds,
                    "result": result,
                }
            results.append(result)
            logger.info(
                "vapi_tool_result %s",
                redact_event(
                    {
                        "call_id": call.call_id,
                        "tool_call_id": call.tool_call_id,
                        "tool_name": call.name,
                        "duration_ms": round((time.perf_counter() - started_at) * 1000),
                        "outcome": json.loads(result["result"]).get("status"),
                    }
                ),
            )
        return {"results": results}

    return app


app = create_app()
