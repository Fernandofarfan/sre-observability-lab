"""Tests for the application-level unhandled exception handler."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.main import unhandled_exception_handler


def test_unhandled_exception_returns_500() -> None:
    """Verify an unexpected exception is converted into a generic 500 JSON response."""
    test_app = FastAPI()
    test_app.add_exception_handler(Exception, unhandled_exception_handler)

    @test_app.get("/boom")
    async def boom() -> None:
        raise RuntimeError("unexpected failure")

    client = TestClient(test_app, raise_server_exceptions=False)
    response = client.get("/boom")
    assert response.status_code == 500
    assert response.json() == {"detail": "Internal Server Error"}
