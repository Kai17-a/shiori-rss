import logging
import sqlite3
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from api.routers.news_sites import router as news_sites_router
from api.routers.rss_feeds import router as rss_feeds_router
from api.routers.settings import router as settings_router
from api.database import initialize_database

logging.basicConfig(
    level=logging.ERROR,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    initialize_database()
    yield


logger = logging.getLogger(__name__)


app = FastAPI(title="Shiori Feed API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    return JSONResponse(
        status_code=422, content={"detail": jsonable_encoder(exc.errors())}
    )


@app.exception_handler(sqlite3.Error)
async def sqlite_exception_handler(request, exc):
    logger.error(f"Database error: {exc}", exc_info=True)
    return JSONResponse(status_code=500, content={"detail": "Database error occurred"})


@app.get("/health", status_code=200)
def health_check():
    return {"status": "ok"}


app.include_router(news_sites_router)
app.include_router(rss_feeds_router)
app.include_router(settings_router)


def dev() -> None:
    import subprocess

    subprocess.run(["fastapi", "dev", "main.py"], check=True)


def serve() -> None:
    import subprocess

    subprocess.run(
        ["fastapi", "run", "main.py", "--host", "0.0.0.0", "--port", "8000"],
        check=True,
    )
