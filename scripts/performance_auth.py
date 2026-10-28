"""Measure registration and login latency under concurrent requests.

Run against a disposable test environment:
    python scripts/performance_auth.py --base-url http://127.0.0.1:8000
"""

import argparse
import asyncio
import math
import time
from uuid import uuid4

import httpx

PASSWORD = "Perf-Test-Password-123"


def percentile95(samples: list[float]) -> float:
    ordered = sorted(samples)
    return ordered[max(0, math.ceil(0.95 * len(ordered)) - 1)]


async def measure_request(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    *,
    json: dict[str, object] | None = None,
    data: dict[str, str] | None = None,
) -> tuple[float, int, str | None]:
    started = time.perf_counter()
    try:
        response = await client.request(method, url, json=json, data=data)
        return time.perf_counter() - started, response.status_code, None
    except httpx.HTTPError as exc:
        return time.perf_counter() - started, 0, str(exc)


async def run_scenario(
    client: httpx.AsyncClient,
    base_url: str,
    users: int,
    run_number: int,
) -> bool:
    run_id = uuid4().hex[:10]
    accounts = [
        {"email": f"perf-{run_id}-{index}@example.test", "password": PASSWORD}
        for index in range(users)
    ]

    registrations = await asyncio.gather(
        *[
            measure_request(
                client,
                "POST",
                f"{base_url}/register/user/",
                json={
                    "first_name": "Perf",
                    "first_surname": "Tester",
                    "contact_info": {"email": account["email"]},
                    "password": account["password"],
                },
            )
            for account in accounts
        ]
    )
    registration_times = [sample[0] for sample in registrations]
    registration_failures = [sample for sample in registrations if sample[1] != 201]

    login_accounts = [
        account
        for account, sample in zip(accounts, registrations, strict=True)
        if sample[1] == 201
    ]
    logins = await asyncio.gather(
        *[
            measure_request(
                client,
                "POST",
                f"{base_url}/users/v1/auth/token",
                data={"username": account["email"], "password": account["password"]},
            )
            for account in login_accounts
        ]
    )
    login_times = [sample[0] for sample in logins]
    login_failures = [sample for sample in logins if sample[1] != 200]

    registration_p95 = percentile95(registration_times)
    login_p95 = percentile95(login_times) if login_times else float("inf")
    print(
        f"Run {run_number}: register p95={registration_p95:.3f}s "
        f"({len(registration_failures)}/{users} failures); "
        f"login p95={login_p95:.3f}s "
        f"({len(login_failures)}/{len(login_accounts)} failures)"
    )
    if registration_failures:
        sample = registration_failures[0]
        print(f"  First registration failure: status={sample[1]} error={sample[2]}")
    if login_failures:
        sample = login_failures[0]
        print(f"  First login failure: status={sample[1]} error={sample[2]}")

    registration_passed = len(registration_failures) == 0 and registration_p95 <= 3.0
    login_passed = len(login_failures) == 0 and login_p95 <= 3.0
    return registration_passed and login_passed


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--users", type=int, default=60)
    parser.add_argument("--runs", type=int, default=3)
    args = parser.parse_args()

    if args.users < 1 or args.runs < 1:
        parser.error("--users and --runs must be positive integers")

    limits = httpx.Limits(
        max_connections=args.users,
        max_keepalive_connections=args.users,
    )
    async with httpx.AsyncClient(timeout=30.0, limits=limits) as client:
        results = [
            await run_scenario(client, args.base_url.rstrip("/"), args.users, run)
            for run in range(1, args.runs + 1)
        ]

    print(f"Overall result: {'PASS' if all(results) else 'FAIL'}")
    print(
        f"Acceptance criteria: {args.users} concurrent users, "
        f"p95 <= 3.0s, {args.runs} runs."
    )
    return 0 if all(results) else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
