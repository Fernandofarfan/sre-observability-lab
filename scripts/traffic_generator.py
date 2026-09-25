"""Traffic generator script - produces realistic synthetic HTTP traffic."""

import argparse
import asyncio
import random
import time
import uuid

import httpx


def _random_items() -> list[dict[str, str | int | float]]:
    """Generate a random list of order items."""
    count = random.randint(1, 5)
    items = []
    for _ in range(count):
        items.append(
            {
                "product_id": f"prod-{random.randint(1000, 9999)}",
                "quantity": random.randint(1, 3),
                "price": round(random.uniform(5.0, 200.0), 2),
            }
        )
    return items


async def send_create_order(client: httpx.AsyncClient, base_url: str) -> httpx.Response:
    """Send a POST request to create an order."""
    payload = {
        "customer_id": f"cust-{random.randint(1, 1000)}",
        "items": _random_items(),
    }
    return await client.post(f"{base_url}/api/v1/orders", json=payload)


async def send_list_orders(client: httpx.AsyncClient, base_url: str) -> httpx.Response:
    """Send a GET request to list orders."""
    return await client.get(f"{base_url}/api/v1/orders")


async def run_traffic(
    base_url: str,
    duration: int,
    rps: int,
) -> None:
    """Generate traffic against the API.

    Args:
        base_url: The base URL of the API.
        duration: Total duration in seconds.
        rps: Target requests per second.
    """
    total_requests = 0
    total_errors = 0
    latencies: list[float] = []
    start_time = time.time()
    stats_interval = 10.0
    next_stats = stats_interval

    async with httpx.AsyncClient(timeout=30.0) as client:
        while time.time() - start_time < duration:
            elapsed = time.time() - start_time
            is_peak = (int(elapsed) % 60) < 10 and int(elapsed) > 0
            current_rps = rps * 4 if is_peak else rps

            batch_size = max(1, current_rps // 5)
            delay = batch_size / current_rps if current_rps > 0 else 1.0

            tasks = []
            for _ in range(batch_size):
                if random.random() < 0.7:
                    tasks.append(send_create_order(client, base_url))
                else:
                    tasks.append(send_list_orders(client, base_url))

            results = await asyncio.gather(*tasks, return_exceptions=True)

            for result in results:
                total_requests += 1
                if isinstance(result, Exception):
                    total_errors += 1
                else:
                    latencies.append(result.elapsed.total_seconds())
                    if result.status_code >= 500:
                        total_errors += 1

            if time.time() >= next_stats:
                avg_latency = sum(latencies[-100:]) / max(len(latencies[-100:]), 1)
                error_rate = (total_errors / total_requests * 100) if total_requests > 0 else 0
                mode = "PEAK" if is_peak else "NORMAL"
                print(
                    f"[{mode}] Requests: {total_requests} | "
                    f"Errors: {total_errors} ({error_rate:.1f}%) | "
                    f"Avg Latency: {avg_latency * 1000:.1f}ms"
                )
                next_stats += stats_interval

            await asyncio.sleep(delay)

    final_avg = sum(latencies) / max(len(latencies), 1)
    final_error_rate = (total_errors / total_requests * 100) if total_requests > 0 else 0
    print(f"\n--- Traffic Generation Complete ---")
    print(f"Total Requests: {total_requests}")
    print(f"Total Errors: {total_errors} ({final_error_rate:.1f}%)")
    print(f"Average Latency: {final_avg * 1000:.1f}ms")


def main() -> None:
    """Parse arguments and start traffic generation."""
    parser = argparse.ArgumentParser(description="Generate synthetic traffic for SRE lab")
    parser.add_argument(
        "--target",
        default="http://localhost:8000",
        help="API base URL (default: http://localhost:8000)",
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=300,
        help="Duration in seconds (default: 300)",
    )
    parser.add_argument(
        "--rps",
        type=int,
        default=10,
        help="Target requests per second (default: 10)",
    )
    args = parser.parse_args()
    asyncio.run(run_traffic(args.target, args.duration, args.rps))


if __name__ == "__main__":
    main()
