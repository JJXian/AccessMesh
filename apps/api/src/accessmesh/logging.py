"""结构化日志配置。"""

import logging

import structlog


def configure_logging() -> None:
    """将标准日志和 structlog 统一输出为带时间戳的 JSON。"""

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.JSONRenderer(),
        ]
    )
