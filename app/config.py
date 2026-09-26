"""Centralized configuration using pydantic-settings."""

import time

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    SERVICE_NAME: str = "sre-observability-lab"
    SERVICE_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    OTEL_EXPORTER_OTLP_ENDPOINT: str = "http://otel-collector:4317"
    OTEL_TRACES_EXPORTER: str = "otlp"
    LOG_LEVEL: str = "INFO"
    CHAOS_ENABLED: bool = True
    CHAOS_TOKEN: str = ""

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()

APP_START_TIME: float = time.time()
