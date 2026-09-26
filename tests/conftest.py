"""Test configuration and shared fixtures."""

import httpx
import pytest

from app.config import settings
from app.main import app
from app.telemetry import setup_telemetry

settings.OTEL_TRACES_EXPORTER = "none"
setup_telemetry(app)


@pytest.fixture
async def client() -> httpx.AsyncClient:
    """Create an async HTTP client for testing the FastAPI app.

    Returns:
        An httpx.AsyncClient wired to the app via ASGITransport.
    """
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac
