import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI,Request
from core.config import settings
from api.v1.routes import router as api_v1_router
from queen.worker import transaction_worker
import logging
from queen.task_queue import tx_task_queue

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 🌱 启动线程，仅执行一次
    threading.Thread(target=transaction_worker, args=(tx_task_queue,), daemon=True).start()
    logging.info("✅ 后台交易处理线程已启动")
    yield  # ⏳ 这里之后 app 正式启动
    logging.info("🛑 应用关闭，可做清理")
    # 此处可加清理逻辑，如 tx_task_queue.join(


app = FastAPI(title=settings.PROJECT_NAME, debug=settings.DEBUG, lifespan=lifespan)

app.include_router(api_v1_router, prefix=settings.API_V1_STR)


@app.get("/")
async def root(request:Request,):
    host = f"{request.client.host:}:{request.client.port}"
    logging.info(f"🌍 收到来自{host}的启动探活请求")
    return {"message": "Hash Fun,Have Fun!","HOST":host}
# uvicorn main:app --reload