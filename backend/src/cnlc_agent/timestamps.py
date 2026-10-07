"""统一生成 UTC 业务时间。"""

from datetime import datetime, timezone


def utc_now() -> str:
    """以带时区的 ISO 字符串记录业务时间。"""
    return datetime.now(timezone.utc).isoformat()


now = utc_now
