from datetime import datetime, UTC
from .config import settings

def get_china_time():
    return datetime.now(UTC) + settings.CHINA_TIMEZONE_OFFSET 