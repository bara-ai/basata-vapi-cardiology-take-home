import httpx
import pytest

from app.clients.emr import EMRClient
from app.config import Settings
from app.main import app, create_app


@pytest.mark.asyncio
async def test_health_returns_ok() -> None:
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_lifespan_creates_emr_client_when_not_injected() -> None:
    application = create_app(settings=Settings(emr_base_url="https://emr.test"))

    async with application.router.lifespan_context(application):
        assert isinstance(application.state.emr_client, EMRClient)
