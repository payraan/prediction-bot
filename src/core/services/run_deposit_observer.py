import asyncio
import os

from src.core.services.deposit_observer import run_deposit_observer

def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default

async def main():
    interval = _env_int("DEPOSIT_OBSERVER_INTERVAL_SECONDS", 15)
    await run_deposit_observer(interval_seconds=interval)

if __name__ == "__main__":
    asyncio.run(main())
