from datetime import datetime, timezone, timedelta
from .config import settings


def get_china_time():
    # 创建一个中国时区的对象 (UTC+8)
    china_tz = timezone(settings.CHINA_TIMEZONE_OFFSET)  # 中国时区为 UTC+8
    # 获取当前的 UTC 时间，并转换为中国时区时间
    china_time = datetime.now(china_tz)
    return china_time
