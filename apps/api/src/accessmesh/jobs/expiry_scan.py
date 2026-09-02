"""扫描并撤销过期权限的独立后台任务。"""

import argparse
import asyncio

import structlog

from accessmesh.db.session import AsyncSessionLocal
from accessmesh.execution.revocation import ExpiryScanResult, revoke_expired_permissions

logger = structlog.get_logger()


async def scan_once(batch_size: int = 100) -> ExpiryScanResult:
    """在一个数据库事务中扫描并回收一批过期权限。"""

    async with AsyncSessionLocal() as session:
        try:
            result = await revoke_expired_permissions(
                session,
                batch_size=batch_size,
            )
            await session.commit()
        except Exception:
            await session.rollback()
            logger.exception("expiry_scan_failed")
            raise

    logger.info(
        "expiry_scan_completed",
        scanned_count=result.scanned_count,
        revoked_count=result.revoked_count,
        failed_count=result.failed_count,
    )
    return result


async def run(interval: int, batch_size: int = 100) -> None:
    """按指定秒数持续执行扫描。"""

    while True:
        try:
            await scan_once(batch_size)
        except Exception:  # noqa: BLE001
            # 单轮异常不能终止常驻进程，下一轮仍需继续尝试回收。
            pass
        await asyncio.sleep(interval)


def main() -> None:
    """解析命令行参数并启动单次或循环扫描。"""

    parser = argparse.ArgumentParser(description="Scan and revoke expired permissions")
    parser.add_argument("--interval", type=int, default=60)
    parser.add_argument("--batch-size", type=int, default=100)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    asyncio.run(scan_once(args.batch_size) if args.once else run(args.interval, args.batch_size))


if __name__ == "__main__":
    main()
