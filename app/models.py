from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base
from .utils import get_china_time

class Client(Base):
    __tablename__ = "clients"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(String(50), unique=True, nullable=False, index=True)
    ip_address = Column(String(50))
    last_heartbeat = Column(DateTime, default=get_china_time)
    status = Column(Integer, default=1)  # 1: online, 0: offline
    task_status = Column(Integer, default=0)  # 0: idle, 1: busy
    created_at = Column(DateTime, default=get_china_time)

class MainTask(Base):
    """总任务表"""
    __tablename__ = "main_tasks"

    id = Column(Integer, primary_key=True, index=True)
    room_id = Column(String(50), nullable=False, index=True)  # 直播间ID
    total_watch_time = Column(Integer, nullable=False)  # 总观看时间(分钟)
    status = Column(Integer, default=0)  # 0: pending, 1: running, 2: completed, 3: failed
    client_count = Column(Integer, nullable=False)  # 需要的客户端数量
    created_at = Column(DateTime, default=get_china_time)
    updated_at = Column(DateTime, default=get_china_time, onupdate=get_china_time)

    # 关联的客户端任务
    client_tasks = relationship("ClientTask", back_populates="main_task")

class ClientTask(Base):
    """客户端任务表"""
    __tablename__ = "client_tasks"

    id = Column(Integer, primary_key=True, index=True)
    main_task_id = Column(Integer, ForeignKey("main_tasks.id"), nullable=False)  # 关联的主任务ID
    client_id = Column(String(50), ForeignKey("clients.client_id"), nullable=False)  # 关联的客户端ID
    total_watch_time = Column(Integer, nullable=False)  # 该客户端需要观看的时间(分钟)
    watched_time = Column(Integer, default=0)  # 已观看时间(分钟)
    status = Column(Integer, default=0)  # 0: pending, 1: running, 2: completed, 3: failed
    last_report_time = Column(DateTime, nullable=True)  # 最后一次进度报告时间
    error_screenshot = Column(String(500), nullable=True)  # 错误截图路径
    created_at = Column(DateTime, default=get_china_time)
    updated_at = Column(DateTime, default=get_china_time, onupdate=get_china_time)

    # 关联关系
    main_task = relationship("MainTask", back_populates="client_tasks") 