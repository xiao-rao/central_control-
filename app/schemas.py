from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List

class HeartbeatRequest(BaseModel):
    client_id: str

class ClientBase(BaseModel):
    client_id: str
    ip_address: Optional[str] = None
    status: int
    task_status: int
    last_heartbeat: datetime
    created_at: datetime

class ClientResponse(ClientBase):
    id: int

    class Config:
        from_attributes = True

class TaskCreate(BaseModel):
    room_id: str
    total_watch_time: int  # 总观看时间(分钟)
    client_count: int      # 需要的客户端数量

class TaskResponse(BaseModel):
    id: int
    room_id: str
    client_id: str
    total_watch_time: int
    watched_time: int
    status: int
    progress: float
    last_report_time: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class MainTaskCreate(BaseModel):
    room_id: str
    total_watch_time: int  # 总观看时间(分钟)
    client_count: int      # 需要的客户端数量

class ClientTaskResponse(BaseModel):
    id: int
    main_task_id: int
    client_id: str
    total_watch_time: int
    watched_time: int
    status: int
    last_report_time: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class MainTaskResponse(BaseModel):
    id: int
    room_id: str
    total_watch_time: int
    status: int
    client_count: int
    created_at: datetime
    updated_at: datetime
    watched_time: int = 0  # 计算得到的总观看时间
    progress: float = 0    # 计算得到的总进度
    client_tasks: List[ClientTaskResponse]

    class Config:
        from_attributes = True

class TaskProgress(BaseModel):
    task_id: int          # 客户端任务ID
    watched_time: int     # 已观看时间(分钟)

class TaskError(BaseModel):
    task_id: int
    error_message: str
    screenshot_path: str 