from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.db import ensure_indexes
from app.routes import claim, health, submit


@asynccontextmanager
async def lifespan(app: FastAPI):
    await ensure_indexes()
    yield


# NOT: CORSMiddleware bilhassa YOK - bu API hicbir zaman tarayici JS'inden
# cagrilmiyor, sadece uzak worker'lardan makine-makine istekleri aliyor.
app = FastAPI(title="Uzak Worker API", lifespan=lifespan)

app.include_router(health.router)
app.include_router(claim.router)
app.include_router(submit.router)
