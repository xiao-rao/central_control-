from fastapi import FastAPI, APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import List, Optional
from . import models, schemas, database
from .config import settings
from .database import engine
from .utils import get_china_time  # 导入工具函数
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import and_

# 创建数据库表
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Client Control Center")

# 添加 CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有来源，生产环境应限制为特定域名
    allow_credentials=True,
    allow_methods=["*"],  # 允许所有 HTTP 方法
    allow_headers=["*"],  # 允许所有 HTTP 头
)

router = APIRouter(prefix="/api")

def get_client_ip(request):
    return request.client.host

@router.post("/heartbeat", response_model=dict)
async def heartbeat(
    heartbeat_req: schemas.HeartbeatRequest,
    request: Request,
    db: Session = Depends(database.get_db)
):
    try:
        client = db.query(models.Client).filter(
            models.Client.client_id == heartbeat_req.client_id
        ).first()

        if client:
            client.last_heartbeat = get_china_time()
            client.ip_address = get_client_ip(request)
            client.status = 1  # online
        else:
            client = models.Client(
                client_id=heartbeat_req.client_id,
                ip_address=get_client_ip(request),
                last_heartbeat=get_china_time(),
                status=1  # online
            )
            db.add(client)

        db.commit()
        return {
            "code": 0,
            "data": {"status": "success"}
        }
    except Exception as e:
        return {
            "code": 1,
            "msg": f"心跳更新失败: {str(e)}"
        }

@router.get("/clients", response_model=dict)
async def get_clients(
    page: Optional[int] = 1,
    page_size: Optional[int] = 10,
    db: Session = Depends(database.get_db)
):
    try:
        # 更新超时客户端状态
        timeout = get_china_time() - timedelta(seconds=settings.HEARTBEAT_TIMEOUT)
        db.query(models.Client).filter(
            models.Client.last_heartbeat < timeout,
            models.Client.status == 1  # online
        ).update({"status": 0})  # offline
        db.commit()

        # 计算总数
        total = db.query(models.Client).count()
        
        # 分页查询
        clients = db.query(models.Client)\
            .order_by(models.Client.last_heartbeat.desc())\
            .offset((page - 1) * page_size)\
            .limit(page_size)\
            .all()
            
        # 转换为 Pydantic 模型
        client_list = [schemas.ClientResponse.model_validate(client.__dict__) for client in clients]
        
        return {
            "code": 0,
            "data": {
                "items": client_list,
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": (total + page_size - 1) // page_size
            }
        }
    except Exception as e:
        return {
            "code": 1,
            "msg": f"获取客户端列表失败: {str(e)}"
        }

@router.get("/client/{client_id}", response_model=schemas.ClientResponse)
async def get_client(client_id: str, db: Session = Depends(database.get_db)):
    client = db.query(models.Client).filter(
        models.Client.client_id == client_id
    ).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return client

@router.delete("/clients/offline", response_model=dict)
async def remove_offline_clients(db: Session = Depends(database.get_db)):
    try:
        deleted_count = db.query(models.Client).filter(
            models.Client.status == 0
        ).delete()
        
        db.commit()
        return {
            "code": 0,
            "data": {
                "deleted_count": deleted_count
            }
        }
    except Exception as e:
        db.rollback()
        return {
            "code": 1,
            "msg": f"清理离线客户端失败: {str(e)}"
        }

@router.get("/menu", response_model=dict)
async def get_client_menu():
    """
    获取客户端菜单信息
    """
    menu = {
        "code": 0,
        "data": {
            "list": [
                {
                    "path": "/client",
                    "name": "client",
                    "component": "LAYOUT",
                    "redirect": "/client",
                    "meta": {
                        "title": {
                            "zh_CN": "客户端管理",
                            "en_US": "Client Management"
                        },
                        "icon": "user"
                    },
                    "children": [
                        {
                            "path": "list",
                            "name": "ClientList",
                            "component": "/client/index",
                            "meta": {
                                "title": {
                                    "zh_CN": "客户端列表",
                                    "en_US": "Client List"
                                }
                            }
                        },
                        {
                            "path": "monitor",
                            "name": "ClientMonitor",
                            "component": "/client/monitor/index",
                            "meta": {
                                "title": {
                                    "zh_CN": "客户端监控",
                                    "en_US": "Client Monitor"
                                }
                            }
                        }
                    ]
                }
            ]
        }
    }
    return menu

# 创建任务
@router.post("/tasks", response_model=dict)
async def create_task(
    task: schemas.MainTaskCreate,
    db: Session = Depends(database.get_db)
):
    try:
        # 获取可用的客户端
        available_clients = db.query(models.Client).filter(
            and_(
                models.Client.status == 1,  # online
                models.Client.task_status == 0  # idle
            )
        ).all()

        if len(available_clients) < task.client_count:
            return {
                "code": 1,
                "msg": f"可用客户端数量不足，需要{task.client_count}个，当前只有{len(available_clients)}个"
            }

        # 创建主任务
        main_task = models.MainTask(
            room_id=task.room_id,
            total_watch_time=task.total_watch_time,
            client_count=task.client_count,
            status=0  # pending
        )
        db.add(main_task)
        db.flush()  # 获取主任务ID

        # 计算每个客户端需要观看的时间
        watch_time_per_client = task.total_watch_time // task.client_count

        # 创建客户端任务
        client_tasks = []
        for i in range(task.client_count):
            client = available_clients[i]
            client.task_status = 1  # busy
            
            client_task = models.ClientTask(
                main_task_id=main_task.id,
                client_id=client.client_id,
                total_watch_time=watch_time_per_client,
                status=0  # pending
            )
            client_tasks.append(client_task)

        db.add_all(client_tasks)
        db.commit()

        return {
            "code": 0,
            "data": {
                "task_id": main_task.id,
                "client_count": len(client_tasks),
                "watch_time_per_client": watch_time_per_client
            }
        }
    except Exception as e:
        db.rollback()
        return {
            "code": 1,
            "msg": f"创建任务失败: {str(e)}"
        }

# 客户端获取任务
@router.get("/tasks/client/{client_id}", response_model=dict)
async def get_client_task(
    client_id: str,
    db: Session = Depends(database.get_db)
):
    try:
        # 获取该客户端的未完成任务
        client_task = db.query(models.ClientTask).filter(
            and_(
                models.ClientTask.client_id == client_id,
                models.ClientTask.status.in_([0, 1])  # pending or running
            )
        ).first()

        if not client_task:
            return {
                "code": 0,
                "data": None
            }

        # 如果任务状态是pending，更新为running
        if client_task.status == 0:  # pending
            client_task.status = 1  # running
            # 更新主任务状态
            main_task = client_task.main_task
            if main_task.status == 0:
                main_task.status = 1  # running
            db.commit()

        # 转换为响应格式
        response_data = {
            "id": client_task.id,  # 客户端任务ID
            "room_id": client_task.main_task.room_id,
            "total_watch_time": client_task.total_watch_time,
            "watched_time": client_task.watched_time,
            "status": client_task.status,
            "cookie": {
    "buvid3": "D10C2FEE-DD94-A0F7-A5FC-4D0B8A18656B94888infoc",
    "b_nut": "1739786794",
    "b_lsid": "51C5857E_195135FB8FC",
    "_uuid": "85A9F531-A3FF-A818-4A2A-23B3A651256D95267infoc",
    "buvid_fp": "fa3608a4af6e28fe316f94d83cdd9a9e",
    "enable_web_push": "DISABLE",
    "enable_feed_channel": "DISABLE",
    "home_feed_column": "5",
    "buvid4": "00565A61-9FEC-6A48-3F54-954D4EF2FE5795717-025021710-zDGizg3RjfGNhGRZ8B2dhQ%3D%3D",
    "bili_ticket": "eyJhbGciOiJIUzI1NiIsImtpZCI6InMwMyIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3NDAwNDU5OTUsImlhdCI6MTczOTc4NjczNSwicGx0IjotMX0.5P-twhXrhDITsoaNRlHMEsdSMUXu81Ib-JxWZF5sIic",
    "bili_ticket_expires": "1740045935",
    "SESSDATA": "bf69e471%2C1755338816%2C7d91a%2A22CjBKiQwdjDORRLxRUNL-sYuVi2T9BcAAIUQMrGgVnBGYr93xXBXbwIo2kMqRvdgORKkSVmtOTzR2RVFxRW5oUDFyR0RDU29ZQlVySkh1RlJ3TGMtYmhSY0pCbWlBZFFuRGRrbXNGZmZ5OU5iaEc2dmI2VnBtYXVXYVU3ejV3MGIyRU45bGIyOTVnIIEC",
    "bili_jct": "3ecb647a7fd5332f261ee41d13e7cf22",
    "DedeUserID": "1687506845",
    "DedeUserID__ckMd5": "d421e3dbc9dc1524",
    "sid": "661ml0fl",
    "browser_resolution": "1686-294",
    "CURRENT_FNVAL": "2000",
    "header_theme_version": "CLOSE"
}  # 从配置中获取cookie
        }

        return {
            "code": 0,
            "data": response_data
        }
    except Exception as e:
        return {
            "code": 1,
            "msg": f"获取任务失败: {str(e)}"
        }

# 更新任务进度
@router.post("/tasks/progress", response_model=dict)
async def update_task_progress(
    progress: schemas.TaskProgress,
    db: Session = Depends(database.get_db)
):
    try:
        # 更新客户端任务进度
        client_task = db.query(models.ClientTask).filter(
            models.ClientTask.id == progress.task_id
        ).first()

        if not client_task:
            return {
                "code": 1,
                "msg": "任务不存在"
            }

        client_task.watched_time = progress.watched_time
        client_task.last_report_time = get_china_time()

        # 如果该客户端任务完成
        if progress.watched_time >= client_task.total_watch_time:
            client_task.status = 2  # completed
            # 更新客户端状态为idle
            client = db.query(models.Client).filter(
                models.Client.client_id == client_task.client_id
            ).first()
            if client:
                client.task_status = 0  # idle

            # 检查主任务是否完成
            main_task = client_task.main_task
            all_completed = all(ct.status == 2 for ct in main_task.client_tasks)
            if all_completed:
                main_task.status = 2  # completed

        db.commit()

        return {
            "code": 0,
            "data": {"status": "success"}
        }
    except Exception as e:
        db.rollback()
        return {
            "code": 1,
            "msg": f"更新任务进度失败: {str(e)}"
        }

# 获取任务列表（包含客户端任务详情）
@router.get("/tasks", response_model=dict)
async def get_tasks(
    page: Optional[int] = 1,
    page_size: Optional[int] = 10,
    status: Optional[int] = None,
    db: Session = Depends(database.get_db)
):
    try:
        # 构建查询
        query = db.query(models.MainTask)
        
        if status is not None:
            query = query.filter(models.MainTask.status == status)
            
        # 计算总数
        total = query.count()
        
        # 分页查询
        tasks = query.order_by(models.MainTask.created_at.desc())\
            .offset((page - 1) * page_size)\
            .limit(page_size)\
            .all()
            
        # 转换为响应格式
        task_list = []
        for task in tasks:
            task_data = {
                "id": task.id,
                "room_id": task.room_id,
                "total_watch_time": task.total_watch_time,
                "status": task.status,
                "client_count": task.client_count,
                "created_at": task.created_at,
                "updated_at": task.updated_at,
                "client_tasks": []
            }
            
            # 添加客户端任务详情
            total_watched = 0
            for ct in task.client_tasks:
                client_task = {
                    "id": ct.id,
                    "client_id": ct.client_id,
                    "total_watch_time": ct.total_watch_time,
                    "watched_time": ct.watched_time,
                    "status": ct.status,
                    "last_report_time": ct.last_report_time,
                    "progress": (ct.watched_time / ct.total_watch_time * 100) if ct.total_watch_time > 0 else 0
                }
                task_data["client_tasks"].append(client_task)
                total_watched += ct.watched_time
            
            # 计算总进度
            task_data["watched_time"] = total_watched
            task_data["progress"] = (total_watched / task.total_watch_time * 100) if task.total_watch_time > 0 else 0
            
            task_list.append(task_data)
        
        return {
            "code": 0,
            "data": {
                "items": task_list,
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": (total + page_size - 1) // page_size
            }
        }
    except Exception as e:
        return {
            "code": 1,
            "msg": f"获取任务列表失败: {str(e)}"
        }

@router.post("/tasks/error", response_model=dict)
async def update_task_error(
    error: schemas.TaskError,
    db: Session = Depends(database.get_db)
):
    try:
        client_task = db.query(models.ClientTask).filter(
            models.ClientTask.id == error.task_id
        ).first()

        if not client_task:
            return {
                "code": 1,
                "msg": "任务不存在"
            }

        # 更新任务状态为失败
        client_task.status = 3  # failed
        client_task.error_screenshot = error.screenshot_path
        
        # 释放客户端
        client = db.query(models.Client).filter(
            models.Client.client_id == client_task.client_id
        ).first()
        if client:
            client.task_status = 0  # idle

        db.commit()

        return {
            "code": 0,
            "data": {"status": "success"}
        }
    except Exception as e:
        db.rollback()
        return {
            "code": 1,
            "msg": f"更新任务状态失败: {str(e)}"
        }

app.include_router(router) 