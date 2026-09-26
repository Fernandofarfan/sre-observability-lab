"""Alertmanager webhook receiver: ingests alerts, logs them and exposes metrics."""

import structlog
from fastapi import APIRouter, FastAPI, HTTPException, Request
from prometheus_client import Counter, make_asgi_app

logger = structlog.get_logger()

ALERTS_RECEIVED = Counter(
    "alerts_received_total",
    "Alerts received from Alertmanager",
    ["receiver", "severity", "status", "alertname"],
)

app = FastAPI(title="alertmanager-webhook-receiver", version="1.0.0")

router = APIRouter()


def _dict_or_empty(value: object) -> dict[str, object]:
    """Return the value if it is a dict, otherwise an empty dict.

    Args:
        value: Any value parsed from the webhook payload.

    Returns:
        The value as a dict, or an empty dict when it is not one.
    """
    if isinstance(value, dict):
        return dict(value)
    return {}


@router.get("/healthz")
async def healthz() -> dict[str, str]:
    """Liveness probe for the webhook receiver.

    Returns:
        JSON indicating the service is alive.
    """
    return {"status": "alive"}


async def _ingest(receiver: str, request: Request) -> dict[str, int]:
    """Parse an Alertmanager webhook payload, record metrics and log alerts.

    Args:
        receiver: The Alertmanager receiver that delivered the payload.
        request: The incoming webhook request.

    Returns:
        Count of alerts processed.

    Raises:
        400: If the body is not valid JSON.
        502: If the payload is not an Alertmanager webhook object.
    """
    try:
        payload = await request.json()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Body is not valid JSON") from exc
    if not isinstance(payload, dict) or "alerts" not in payload:
        raise HTTPException(status_code=502, detail="Not an Alertmanager webhook payload")

    alerts = payload.get("alerts", [])
    processed = 0
    for alert in alerts:
        if not isinstance(alert, dict):
            continue
        labels = _dict_or_empty(alert.get("labels"))
        annotations = _dict_or_empty(alert.get("annotations"))
        alertname = str(labels.get("alertname", "unknown"))
        severity = str(labels.get("severity", "unknown"))
        status = str(alert.get("status", "unknown"))
        ALERTS_RECEIVED.labels(
            receiver=receiver,
            severity=severity,
            status=status,
            alertname=alertname,
        ).inc()
        logger.info(
            "alert_received",
            receiver=receiver,
            alertname=alertname,
            severity=severity,
            status=status,
            summary=str(annotations.get("summary", "")),
        )
        processed += 1
    return {"received": processed}


@router.post("/")
async def receive_default(request: Request) -> dict[str, int]:
    """Receive alerts routed to the default receiver.

    Args:
        request: The incoming webhook request.

    Returns:
        Count of alerts processed.
    """
    return await _ingest("default", request)


@router.post("/pager")
async def receive_pager(request: Request) -> dict[str, int]:
    """Receive alerts routed to the pager receiver (severity=critical).

    Args:
        request: The incoming webhook request.

    Returns:
        Count of alerts processed.
    """
    return await _ingest("pager", request)


@router.post("/ticket")
async def receive_ticket(request: Request) -> dict[str, int]:
    """Receive alerts routed to the ticket receiver (severity=warning).

    Args:
        request: The incoming webhook request.

    Returns:
        Count of alerts processed.
    """
    return await _ingest("ticket", request)


app.include_router(router)
app.mount("/metrics", make_asgi_app())
