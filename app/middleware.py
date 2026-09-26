"""ASGI middleware for Prometheus HTTP metrics collection."""

import time

from prometheus_client import Counter, Gauge, Histogram
from starlette.types import ASGIApp, Message, Receive, Scope, Send

HTTP_REQUESTS_TOTAL = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status_code"],
)

HTTP_REQUEST_DURATION = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

HTTP_REQUESTS_IN_PROGRESS = Gauge(
    "http_requests_in_progress",
    "Number of HTTP requests currently in progress",
    ["method"],
)

_EXCLUDED_PATHS = frozenset({"/metrics", "/metrics/", "/healthz"})
_UNMATCHED_ENDPOINT = "unmatched"


def _endpoint(scope: Scope) -> str:
    """Resolve the low-cardinality endpoint label for a request scope.

    Uses the matched route template (e.g. /api/v1/orders/{order_id}) instead
    of the raw URL path so path parameters never explode metric cardinality.
    Requests that matched no route are aggregated under "unmatched".

    Args:
        scope: The ASGI HTTP scope, after routing has been performed.

    Returns:
        The route template path, or "unmatched" when no route matched.
    """
    route = scope.get("route")
    route_path = getattr(route, "path", None)
    if isinstance(route_path, str) and route_path:
        return route_path
    return _UNMATCHED_ENDPOINT


def _record(method: str, scope: Scope, status: str, start: float) -> None:
    """Record duration, in-flight gauge and request counter for a request.

    Args:
        method: The HTTP method.
        scope: The ASGI scope (routing already performed).
        status: The response status code as a string.
        start: perf_counter timestamp taken at request start.
    """
    endpoint = _endpoint(scope)
    elapsed = time.perf_counter() - start
    HTTP_REQUEST_DURATION.labels(method=method, endpoint=endpoint).observe(elapsed)
    HTTP_REQUESTS_IN_PROGRESS.labels(method=method).dec()
    HTTP_REQUESTS_TOTAL.labels(method=method, endpoint=endpoint, status_code=status).inc()


class PrometheusMiddleware:
    """Pure ASGI middleware that records Prometheus metrics for every request."""

    def __init__(self, app: ASGIApp) -> None:
        """Wrap the downstream ASGI application.

        Args:
            app: The next ASGI application in the chain.
        """
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Process a request and record metrics.

        Args:
            scope: The ASGI scope.
            receive: The ASGI receive callable.
            send: The ASGI send callable.
        """
        if scope["type"] != "http" or scope.get("path") in _EXCLUDED_PATHS:
            await self.app(scope, receive, send)
            return

        method = scope.get("method", "GET")
        status_code = "500"
        start = time.perf_counter()

        async def send_wrapper(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = str(message["status"])
            await send(message)

        HTTP_REQUESTS_IN_PROGRESS.labels(method=method).inc()
        try:
            await self.app(scope, receive, send_wrapper)
        except BaseException:
            _record(method, scope, "500", start)
            raise
        _record(method, scope, status_code, start)
