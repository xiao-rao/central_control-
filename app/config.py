from pydantic_settings import BaseSettings
from datetime import timedelta

class Settings(BaseSettings):
    # MySQL配置
    DATABASE_URL: str = "mysql+pymysql://root:123456@localhost:3306/dbname"
    # 心跳超时时间（秒）
    HEARTBEAT_TIMEOUT: int = 60
    # 中国时区偏移
    CHINA_TIMEZONE_OFFSET: timedelta = timedelta(hours=8)

    class Config:
        env_file = ".env"

BILIBILI_COOKIE = {
    "buvid3": "83F4D322-E481-B6B4-A8D7-1BA47CCA17E758899infoc",
    # ... 其他 cookie 值
}

settings = Settings() 