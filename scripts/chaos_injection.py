"""Chaos injection script - triggers predefined fault scenarios against the API."""

import argparse
import asyncio
import time
from datetime import datetime, timezone

import httpx


def _log(message: str) -> None:
    """Print a timestamped log message."""
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    print(f"[{ts}] {message}")


async def latency_spike(client: httpx.AsyncClient, base_url: str) -> None:
    """Inject 500-2000ms latency for 60 seconds.

    Args:
        client: The HTTP client.
        base_url: The API base URL.
    """
    _log("SCENARIO: latency-spike — Enabling 500-2000ms latency for 60s")
    await client.post(f"{base_url}/chaos/latency", json={"enabled": True, "min_ms": 500, "max_ms": 2000})
    _log("Latency injection active")
    await asyncio.sleep(60)
    await client.post(f"{base_url}/chaos/reset")
    _log("Latency injection stopped — chaos reset")


async def error_storm(client: httpx.AsyncClient, base_url: str) -> None:
    """Inject 30% error rate for 30 seconds.

    Args:
        client: The HTTP client.
        base_url: The API base URL.
    """
    _log("SCENARIO: error-storm — Enabling 30% error rate for 30s")
    await client.post(f"{base_url}/chaos/errors", json={"enabled": True, "rate": 0.3})
    _log("Error injection active")
    await asyncio.sleep(30)
    await client.post(f"{base_url}/chaos/reset")
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
        )
        await asyncio.sleep(10)

    await client.post(f"{base_url}/chaos/reset")
    _log("Gradual degradation complete — chaos reset")


async def full_chaos(client: httpx.AsyncClient, base_url: str) -> None:
    """Combine 300-800ms latency + 15% error rate for 45 seconds.

    Args:
        client: The HTTP client.
        base_url: The API base URL.
    """
    _log("SCENARIO: full-chaos — Enabling latency (300-800ms) + errors (15%) for 45s")
    await client.post(
        f"{base_url}/chaos/latency",
        json={"enabled": True, "min_ms": 300, "max_ms": 800},
    )
    await client.post(
        f"{base_url}/chaos/errors",
        json={"enabled": True, "rate": 0.15},
    )
    _log("Full chaos active")
    await asyncio.sleep(45)
    await client.post(f"{base_url}/chaos/reset")
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
