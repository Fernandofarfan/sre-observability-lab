"""Chaos injection script - triggers predefined fault scenarios against the API."""

import argparse
import asyncio
import os
from datetime import UTC, datetime

import httpx


def _log(message: str) -> None:
    """Print a timestamped log message."""
    ts = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    print(f"[{ts}] {message}")


def _headers() -> dict[str, str]:
    """Return auth headers for chaos endpoints.

    Returns:
        Headers containing X-Chaos-Token when CHAOS_TOKEN is set, else empty.
    """
    token = os.environ.get("CHAOS_TOKEN", "")
    return {"X-Chaos-Token": token} if token else {}


async def latency_spike(client: httpx.AsyncClient, base_url: str) -> None:
    """Inject 500-2000ms latency for 60 seconds.

    Args:
        client: The HTTP client.
        base_url: The API base URL.
    """
    _log("SCENARIO: latency-spike — Enabling 500-2000ms latency for 60s")
    await client.post(
        f"{base_url}/chaos/latency",
        json={"enabled": True, "min_ms": 500, "max_ms": 2000},
        headers=_headers(),
    )
    _log("Latency injection active")
    await asyncio.sleep(60)
    await client.post(f"{base_url}/chaos/reset", headers=_headers())
    _log("Latency injection stopped — chaos reset")


async def error_storm(client: httpx.AsyncClient, base_url: str) -> None:
    """Inject 30% error rate for 4 minutes.

    Long enough for the 10m/1m error budget burn-rate alert to fire live.

    Args:
        client: The HTTP client.
        base_url: The API base URL.
    """
    _log("SCENARIO: error-storm — Enabling 30% error rate for 4m")
    await client.post(
        f"{base_url}/chaos/errors",
        json={"enabled": True, "rate": 0.3},
        headers=_headers(),
    )
    _log("Error injection active")
    await asyncio.sleep(240)
    await client.post(f"{base_url}/chaos/reset", headers=_headers())
    _log("Error injection stopped — chaos reset")


async def gradual_degradation(client: httpx.AsyncClient, base_url: str) -> None:
    """Gradually increase latency from 0 to 1500ms in 100ms steps every 10s.

    Args:
        client: The HTTP client.
        base_url: The API base URL.
    """
    _log("SCENARIO: gradual-degradation — Increasing latency from 0 to 1500ms")
    steps = 15
    for step in range(1, steps + 1):
        latency_ms = step * 100
        _log(f"Step {step}/{steps}: Setting latency to {latency_ms}ms")
        await client.post(
            f"{base_url}/chaos/latency",
            json={"enabled": True, "min_ms": latency_ms, "max_ms": latency_ms + 50},
            headers=_headers(),
        )
        await asyncio.sleep(10)

    await client.post(f"{base_url}/chaos/reset", headers=_headers())
    _log("Gradual degradation complete — chaos reset")


async def full_chaos(client: httpx.AsyncClient, base_url: str) -> None:
    """Combine 300-800ms latency + 20% error rate for 5 minutes.

    Long enough for the 10m/1m error budget burn-rate alert to fire live.

    Args:
        client: The HTTP client.
        base_url: The API base URL.
    """
    _log("SCENARIO: full-chaos — Enabling latency (300-800ms) + errors (20%) for 5m")
    await client.post(
        f"{base_url}/chaos/latency",
        json={"enabled": True, "min_ms": 300, "max_ms": 800},
        headers=_headers(),
    )
    await client.post(
        f"{base_url}/chaos/errors",
        json={"enabled": True, "rate": 0.2},
        headers=_headers(),
    )
    _log("Full chaos active")
    await asyncio.sleep(300)
    await client.post(f"{base_url}/chaos/reset", headers=_headers())
    _log("Full chaos stopped — chaos reset")


SCENARIOS = {
    "latency-spike": latency_spike,
    "error-storm": error_storm,
    "gradual-degradation": gradual_degradation,
    "full-chaos": full_chaos,
}


async def run_scenario(target: str, scenario: str) -> None:
    """Execute a chaos scenario.

    Args:
        target: The API base URL.
        scenario: The scenario name.
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        handler = SCENARIOS.get(scenario)
        if handler is None:
            print(f"Unknown scenario: {scenario}. Available: {', '.join(SCENARIOS)}")
            return
        _log(f"Starting scenario: {scenario} against {target}")
        await handler(client, target)
        _log(f"Scenario '{scenario}' completed")


def main() -> None:
    """Parse arguments and run the selected chaos scenario."""
    parser = argparse.ArgumentParser(description="Chaos injection for SRE observability lab")
    parser.add_argument(
        "--target",
        default="http://localhost:8000",
        help="API base URL (default: http://localhost:8000)",
    )
    parser.add_argument(
        "--scenario",
        required=True,
        choices=list(SCENARIOS.keys()),
        help="Chaos scenario to execute",
    )
    args = parser.parse_args()
    asyncio.run(run_scenario(args.target, args.scenario))


if __name__ == "__main__":
    main()
