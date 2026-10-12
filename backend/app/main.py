from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.observability.routes import router as observability_router
from app.config.settings import settings
from app.models.database import init_db, close_db

from app.observability.database import init_observability_db
from app.observability.middleware import observability_middleware

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_observability_db()
    await init_db()
    yield
    await close_db()


app = FastAPI(
    title="Retail Promotion Performance Classification",
    version="1.0.0",
    lifespan=lifespan,
)

app.middleware("http")(observability_middleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        x.strip() for x in settings.cors_origins.split(",")
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
app.include_router(observability_router)

@app.get("/")
def root():
    return {
        "name": app.title,
        "status": "running",
    }
