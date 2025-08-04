from fastapi import FastAPI
from core.config import settings
from api.v1.routes import router as api_v1_router

app = FastAPI(title=settings.PROJECT_NAME, debug=settings.DEBUG)

app.include_router(api_v1_router, prefix=settings.API_V1_STR)

@app.get("/")
async def root():
    return {"message": "Hello, FastAPI!"}
