"""Test configuration and shared fixtures."""

import httpx
import pytest

from app.main import app


@pytest.fixture
async def client() -> httpx.AsyncClient:
    """Create an async HTTP client for testing the FastAPI app.

    Returns:
        An httpx.AsyncClient wired to the app via ASGITransport.
    """
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac
