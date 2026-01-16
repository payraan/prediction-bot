"""
Round Runner Entrypoint
اجرای مستقل Round Runner (برای Railway / cron / local)
"""

import asyncio
import os

from src.core.services.round_runner import run_round_loop


def _get_assets() -> list[str]:
    raw = os.getenv("ROUND_RUNNER_ASSETS", "BTCUSDT")
    assets = [a.strip() for a in raw.split(",") if a.strip()]
    return assets or ["BTCUSDT"]


def _get_interval() -> int:
    try:
        return int(os.getenv("ROUND_RUNNER_INTERVAL_SECONDS", "5"))
    except Exception:
        return 5


async def main():
    assets = _get_assets()
    interval = _get_interval()
    await run_round_loop(assets=assets, interval_seconds=interval)


if __name__ == "__main__":
    asyncio.run(main())
