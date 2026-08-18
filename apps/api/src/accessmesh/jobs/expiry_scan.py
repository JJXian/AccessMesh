import argparse
import asyncio

import structlog
from sqlalchemy import text

from accessmesh.db.session import AsyncSessionLocal

logger = structlog.get_logger()


async def scan_once() -> None:
    """Scaffold scanner; permission_instances are added in the execution phase."""
    async with AsyncSessionLocal() as session:
        await session.execute(text("SELECT 1"))
    logger.info("expiry_scan_completed", expired_count=0)


async def run(interval: int) -> None:
    while True:
        await scan_once()
        await asyncio.sleep(interval)


def main() -> None:
    parser = argparse.ArgumentParser(description="Scan and revoke expired permissions")
    parser.add_argument("--interval", type=int, default=60)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    asyncio.run(scan_once() if args.once else run(args.interval))


if __name__ == "__main__":
    main()
