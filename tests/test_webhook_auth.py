import json

import httpx
import pytest

from app.config import Settings
from app.main import create_app


@pytest.fixture
def app_with_webhook_secret():
    return create_app(settings=Settings(vapi_webhook_secret="test-secret"))


class StubEMRClient:
    async def list_patients(self, **_filters):
        return [
            {
                "id": "pat_123",
                "first_name": "Maria",
                "last_name": "Santos",
                "date_of_birth": "1985-03-15",
                "phone": "+15551234001",
            }
        ]


class CountingRegistrationEMRClient:
    def __init__(self) -> None:
        self.create_count = 0

    async def list_patients(self, **_filters):
        return []

    async def create_patient(self, patient):
        self.create_count += 1
        return {"id": "pat_new", **patient}


@pytest.mark.asyncio
async def test_webhook_rejects_missing_bearer_credential(app_with_webhook_secret) -> None:
    transport = httpx.ASGITransport(app=app_with_webhook_secret)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/vapi/webhook", json={"message": {"type": "status-update"}})

    assert response.status_code == 401
    assert response.json() == {"detail": "Unauthorized"}


@pytest.mark.asyncio
async def test_webhook_returns_vapi_result_for_unknown_tool(app_with_webhook_secret) -> None:
    transport = httpx.ASGITransport(app=app_with_webhook_secret)
    payload = {
        "message": {
            "type": "tool-calls",
            "toolCallList": [{"id": "tool_unknown", "name": "not_a_tool", "arguments": {}}],
        }
    }

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/vapi/webhook",
            headers={"Authorization": "Bearer test-secret"},
            json=payload,
        )

    assert response.status_code == 200
    assert response.json() == {
        "results": [
            {
                "name": "not_a_tool",
                "toolCallId": "tool_unknown",
                "result": json.dumps({"status": "unsupported_tool", "tool": "not_a_tool"}),
            }
        ]
    }


@pytest.mark.asyncio
async def test_webhook_dispatches_find_patient_with_injected_emr_client() -> None:
    app = create_app(
        settings=Settings(vapi_webhook_secret="test-secret"),
        emr_client=StubEMRClient(),
    )
    transport = httpx.ASGITransport(app=app)
    payload = {
        "message": {
            "type": "tool-calls",
            "toolCallList": [
                {
                    "id": "tool_find",
                    "name": "find_patient",
                    "arguments": {"phone": "+15551234001", "date_of_birth": "1985-03-15"},
                }
            ],
        }
    }

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/vapi/webhook",
            headers={"Authorization": "Bearer test-secret"},
            json=payload,
        )

    assert response.status_code == 200
    assert json.loads(response.json()["results"][0]["result"])["status"] == "verified"


@pytest.mark.asyncio
async def test_webhook_returns_safe_result_for_malformed_tool_arguments(
    app_with_webhook_secret,
) -> None:
    transport = httpx.ASGITransport(app=app_with_webhook_secret, raise_app_exceptions=False)
    payload = {
        "message": {
            "type": "tool-calls",
            "toolCallList": [
                {
                    "id": "tool_bad_args",
                    "function": {"name": "find_patient", "arguments": "{not-json"},
                }
            ],
        }
    }

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/vapi/webhook",
            headers={"Authorization": "Bearer test-secret"},
            json=payload,
        )

    assert response.status_code == 200
    assert response.json()["results"][0]["toolCallId"] == "tool_bad_args"
    assert json.loads(response.json()["results"][0]["result"])["status"] == "invalid_arguments"


@pytest.mark.asyncio
async def test_webhook_deduplicates_retried_registration_tool_call() -> None:
    emr_client = CountingRegistrationEMRClient()
    app = create_app(settings=Settings(vapi_webhook_secret="test-secret"), emr_client=emr_client)
    transport = httpx.ASGITransport(app=app)
    payload = {
        "message": {
            "type": "tool-calls",
            "toolCallList": [
                {
                    "id": "tool_register_once",
                    "name": "register_patient",
                    "arguments": {
                        "first_name": "Ava",
                        "last_name": "Jones",
                        "date_of_birth": "1990-01-02",
                        "phone": "+15551234567",
                    },
                }
            ],
        }
    }

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        first = await client.post(
            "/vapi/webhook", headers={"Authorization": "Bearer test-secret"}, json=payload
        )
        second = await client.post(
            "/vapi/webhook", headers={"Authorization": "Bearer test-secret"}, json=payload
        )

    assert first.json() == second.json()
    assert emr_client.create_count == 1


@pytest.mark.asyncio
async def test_webhook_reprocesses_mutation_after_idempotency_cache_expiry() -> None:
    emr_client = CountingRegistrationEMRClient()
    app = create_app(settings=Settings(vapi_webhook_secret="test-secret"), emr_client=emr_client)
    app.state.idempotency_cache["tool_register_expired"] = {
        "expires_at": 0,
        "result": {
            "name": "register_patient",
            "toolCallId": "tool_register_expired",
            "result": "{}",
        },
    }
    transport = httpx.ASGITransport(app=app)
    payload = {
        "message": {
            "type": "tool-calls",
            "toolCallList": [
                {
                    "id": "tool_register_expired",
                    "name": "register_patient",
                    "arguments": {
                        "first_name": "Ava",
                        "last_name": "Jones",
                        "date_of_birth": "1990-01-02",
                        "phone": "+15551234567",
                    },
                }
            ],
        }
    }

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/vapi/webhook", headers={"Authorization": "Bearer test-secret"}, json=payload
        )

    assert json.loads(response.json()["results"][0]["result"])["status"] == "created"
    assert emr_client.create_count == 1


@pytest.mark.asyncio
async def test_webhook_ignores_authenticated_end_of_call_report() -> None:
    app = create_app(settings=Settings(vapi_webhook_secret="test-secret"))
    transport = httpx.ASGITransport(app=app)
    payload = {
        "message": {
            "type": "end-of-call-report",
            "call": {"id": "call_123"},
            "transcript": "This must not be persisted by the backend.",
        }
    }

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/vapi/webhook",
            headers={"Authorization": "Bearer test-secret"},
            json=payload,
        )

    assert response.status_code == 200
    assert response.json() == {"status": "ignored"}


@pytest.mark.asyncio
async def test_webhook_rejects_invalid_bearer_credential(app_with_webhook_secret) -> None:
    transport = httpx.ASGITransport(app=app_with_webhook_secret)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/vapi/webhook",
            headers={"Authorization": "Bearer wrong-secret"},
            json={"message": {"type": "status-update"}},
        )

    assert response.status_code == 401
    assert response.json() == {"detail": "Unauthorized"}
