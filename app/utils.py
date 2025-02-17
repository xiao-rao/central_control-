from datetime import datetime, timezone, timedelta
from .config import settings

def get_china_time():
    utc_now = datetime.now(timezone.utc)  # 获取当前 UTC 时间
    china_time = utc_now + timedelta(hours=settings.CHINA_TIMEZONE_OFFSET)  # 加上时区偏移
    return china_time