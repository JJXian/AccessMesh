"""扫描并撤销过期权限的独立后台任务。"""

import argparse
import asyncio

import structlog
from sqlalchemy import text

from accessmesh.db.session import AsyncSessionLocal

logger = structlog.get_logger()


async def scan_once() -> None:
    """执行一次扫描；权限实例表将在执行阶段接入，目前仅验证数据库连通性。"""
    async with AsyncSessionLocal() as session:
        await session.execute(text("SELECT 1"))
    logger.info("expiry_scan_completed", expired_count=0)


async def run(interval: int) -> None:
    """按指定秒数持续执行扫描。"""

    while True:
        await scan_once()
        await asyncio.sleep(interval)


def main() -> None:
    """解析命令行参数并启动单次或循环扫描。"""

    parser = argparse.ArgumentParser(description="Scan and revoke expired permissions")
    parser.add_argument("--interval", type=int, default=60)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    asyncio.run(scan_once() if args.once else run(args.interval))


if __name__ == "__main__":
    main()
