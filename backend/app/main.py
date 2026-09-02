from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import (
    admin,
    asns,
    auth,
    domains,
    health,
    lookup,
    monitors,
    nameservers,
    prefixes,
    scans,
    search,
    seo,
    stats,
)
from app.db.mongo import ensure_indexes


@asynccontextmanager
async def lifespan(app: FastAPI):
    await ensure_indexes()
    yield


app = FastAPI(title="IP / ASN / Domain Arşivi", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api")
app.include_router(prefixes.router, prefix="/api")
app.include_router(asns.router, prefix="/api")
app.include_router(lookup.router, prefix="/api")
app.include_router(stats.router, prefix="/api")
app.include_router(domains.router, prefix="/api")
app.include_router(nameservers.router, prefix="/api")
app.include_router(search.router, prefix="/api")
app.include_router(admin.router, prefix="/api")
app.include_router(auth.router, prefix="/api")
app.include_router(monitors.router, prefix="/api")
app.include_router(scans.router, prefix="/api")
app.include_router(seo.router, prefix="/api")
