import re
from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, field_validator

from app.core.config import settings
from app.core.security import get_current_user_id
from app.db.mongo import get_db
from app.ingestion.monitor_checks import CHECK_TYPES, UnsafeTargetError, resolve_public_ip

router = APIRouter()

# Sema+yol icermeyen duz bir hostname/IP bekleniyor (http/https ayri check
# tipleri oldugu icin kullanicinin scheme yazmasina gerek yok/izin verilmiyor).
_TARGET_RE = re.compile(r"^[a-zA-Z0-9]([a-zA-Z0-9.-]{0,253}[a-zA-Z0-9])?$")


def _clean(doc: dict) -> dict:
    doc = dict(doc)
    doc["id"] = str(doc.pop("_id"))
    doc["user_id"] = str(doc["user_id"])
    return doc


class MonitorRequest(BaseModel):
    target: str
    checks: dict[str, bool]
    interval_seconds: int = settings.default_monitor_interval_seconds

    @field_validator("target")
    @classmethod
    def _validate_target(cls, v: str) -> str:
        v = v.strip().lower()
        if v.startswith("http://") or v.startswith("https://"):
            raise ValueError("Sadece hostname/IP girin, http:// veya https:// eklemeyin")
        if not _TARGET_RE.match(v):
            raise ValueError("Gecersiz hostname/IP")
        return v

    @field_validator("checks")
    @classmethod
    def _validate_checks(cls, v: dict[str, bool]) -> dict[str, bool]:
        unknown = set(v) - set(CHECK_TYPES)
        if unknown:
            raise ValueError(f"Bilinmeyen check tipi: {', '.join(unknown)}")
        cleaned = {t: bool(v.get(t, False)) for t in CHECK_TYPES}
        if not any(cleaned.values()):
            raise ValueError("En az bir check tipi (http/https/ping) etkin olmali")
        return cleaned

    @field_validator("interval_seconds")
    @classmethod
    def _validate_interval(cls, v: int) -> int:
        if v < settings.min_monitor_interval_seconds:
            raise ValueError(f"Kontrol sikligi en az {settings.min_monitor_interval_seconds} saniye olmali")
        return v


@router.post("/monitors")
async def create_monitor(body: MonitorRequest, user_id: str = Depends(get_current_user_id)):
    db = get_db()

    existing_count = await db.monitors.count_documents({"user_id": ObjectId(user_id)})
    if existing_count >= settings.max_monitors_per_user:
        raise HTTPException(
            status_code=400,
            detail=f"Kullanici basina en fazla {settings.max_monitors_per_user} monitor eklenebilir",
        )

    try:
        await run_in_threadpool(resolve_public_ip, body.target)
    except UnsafeTargetError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    now = datetime.now(timezone.utc)
    doc = {
        "user_id": ObjectId(user_id),
        "target": body.target,
        "checks": body.checks,
        "interval_seconds": body.interval_seconds,
        "current_status": {t: "unknown" for t in CHECK_TYPES if body.checks.get(t)},
        "last_checked_at": None,
        "next_check_at": now,
        "created_at": now,
    }
    try:
        result = await db.monitors.insert_one(doc)
    except Exception:
        raise HTTPException(status_code=409, detail="Bu hedef zaten ekli")
    return _clean({**doc, "_id": result.inserted_id})


@router.get("/monitors")
async def list_monitors(user_id: str = Depends(get_current_user_id)):
    docs = await get_db().monitors.find({"user_id": ObjectId(user_id)}).sort("created_at", -1).to_list(200)
    return {"monitors": [_clean(d) for d in docs]}


async def _get_own_monitor(monitor_id: str, user_id: str) -> dict:
    try:
        oid = ObjectId(monitor_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Gecersiz monitor id")
    monitor = await get_db().monitors.find_one({"_id": oid, "user_id": ObjectId(user_id)})
    if not monitor:
        raise HTTPException(status_code=404, detail="Monitor bulunamadi")
    return monitor


@router.get("/monitors/{monitor_id}")
async def get_monitor(monitor_id: str, user_id: str = Depends(get_current_user_id)):
    monitor = await _get_own_monitor(monitor_id, user_id)
    results = (
        await get_db()
        .monitor_results.find({"monitor_id": monitor["_id"]})
        .sort("checked_at", -1)
        .to_list(100)
    )
    for r in results:
        r["id"] = str(r.pop("_id"))
        r["monitor_id"] = str(r["monitor_id"])
        r["user_id"] = str(r["user_id"])
    return {"monitor": _clean(monitor), "results": results}


@router.patch("/monitors/{monitor_id}")
async def update_monitor(monitor_id: str, body: MonitorRequest, user_id: str = Depends(get_current_user_id)):
    monitor = await _get_own_monitor(monitor_id, user_id)
    try:
        await run_in_threadpool(resolve_public_ip, body.target)
    except UnsafeTargetError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    current_status = monitor.get("current_status", {})
    new_status = {t: current_status.get(t, "unknown") for t in CHECK_TYPES if body.checks.get(t)}
    await get_db().monitors.update_one(
        {"_id": monitor["_id"]},
        {
            "$set": {
                "target": body.target,
                "checks": body.checks,
                "interval_seconds": body.interval_seconds,
                "current_status": new_status,
            }
        },
    )
    return {"updated": monitor_id}


@router.delete("/monitors/{monitor_id}")
async def delete_monitor(monitor_id: str, user_id: str = Depends(get_current_user_id)):
    monitor = await _get_own_monitor(monitor_id, user_id)
    await get_db().monitor_results.delete_many({"monitor_id": monitor["_id"]})
    await get_db().monitors.delete_one({"_id": monitor["_id"]})
    return {"deleted": monitor_id}
