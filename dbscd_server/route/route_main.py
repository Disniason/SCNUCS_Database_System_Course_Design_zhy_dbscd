import os
import uvicorn
from pathlib import Path
from fastapi import FastAPI
from contextlib import asynccontextmanager
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from test import tester
import route.route_user
import route.route_video
from route.route_base import router
from service.user_service import user_service
from service.video_service import video_service
from database.mysql import mysql_database

# ========== 数据库初始化生命周期 ==========
@asynccontextmanager
async def lifespan(app):
    # 启动阶段
    print("服务启动：开始初始化资源")
    await mysql_database.init_db()
    await user_service.init_redis()

    # await tester.insert_10000_user()
    # await tester.insert_100000_user_video_like()
    
    yield
    
    # 退出阶段
    await user_service.close_redis()
    await mysql_database.close()

app = FastAPI(
    title = "zhy_dbscd张淏禹数据库系统原理课程设计作品",
    lifespan = lifespan
)

app.include_router(router)

@app.get("/check-video")
def check():
    fp = video_service.VIDEO_SAVE_BASE + "/video_3_1.mp4"
    return {
        "exists": os.path.exists(fp),
        "is_file": os.path.isfile(fp),
        "can_read": os.access(fp, os.R_OK)
    }


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],        # 允许所有来源
    allow_credentials=True,     # 允许 Cookie
    allow_methods=["*"],        # 允许所有方法（GET/POST/OPTIONS 等）
    allow_headers=["*"],        # 允许所有请求头（包含 Token）
)

BASE_PATH = Path(__file__).parent
STATIC_PATH = BASE_PATH.parent / "static"

# 挂载
app.mount("/static/video", StaticFiles(directory=video_service.VIDEO_SAVE_BASE), name="video_static")
app.mount("/static", StaticFiles(directory = STATIC_PATH), name = "static")


def route_main():
    
    uvicorn.run("route.route_main:app", host="0.0.0.0", port=8000, workers = 1)
