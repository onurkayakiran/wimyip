import re
from datetime import datetime, timedelta, timezone

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, field_validator

from app.core.config import settings
from app.core.plans import get_user_plan, max_monitors_for_plan
from app.core.security import get_current_user_id
from app.core.serialization import clean_doc
from app.db.mongo import get_db
from app.ingestion.monitor_checks import CHECK_TYPES, UnsafeTargetError, resolve_public_ip

router = APIRouter()

# Sema+yol icermeyen duz bir hostname/IP bekleniyor (http/https ayri check
# tipleri oldugu icin kullanicinin scheme yazmasina gerek yok/izin verilmiyor).
_TARGET_RE = re.compile(r"^[a-zA-Z0-9]([a-zA-Z0-9.-]{0,253}[a-zA-Z0-9])?$")

# Liste sayfasindaki bar-geçmişi kaç ham sonuç gösterir, ve uptime yuzdesi
# hangi pencerede hesaplanir (24s, UptimeRobot dahil cogu aracin varsayilani).
_HISTORY_BAR_COUNT = 20
_UPTIME_WINDOW_HOURS = 24


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

    plan = await get_user_plan(user_id)
    limit = max_monitors_for_plan(plan)
    existing_count = await db.monitors.count_documents({"user_id": ObjectId(user_id)})
    if existing_count >= limit:
        detail = f"Kullanici basina en fazla {limit} monitor eklenebilir"
        if plan != "premium":
            detail += " (premium'a geçerek limiti artırabilirsiniz)"
        raise HTTPException(status_code=400, detail=detail)

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
        # status_since: durum "unknown"dan ilk kez cikinca run_due_checks()
        # gercek degerle degistirir - simdilik yaratilma anini tutuyoruz ki
        # "ne zamandir boyle" hesaplamasi hic bos kalmasin.
        "status_since": {t: now for t in CHECK_TYPES if body.checks.get(t)},
        "last_checked_at": None,
        "next_check_at": now,
        "created_at": now,
    }
    try:
        result = await db.monitors.insert_one(doc)
    except Exception:
        raise HTTPException(status_code=409, detail="Bu hedef zaten ekli")
    return clean_doc({**doc, "_id": result.inserted_id})


async def _monitor_check_detail(db, monitor: dict) -> list[dict]:
    """Liste sayfasi icin: monitorun her ETKIN check tipi icin durum,
    "ne zamandir boyle", son 24s uptime yuzdesi ve son N sonucun bar
    gecmisini hesaplar. Kucuk olcekli bir uygulama (kullanici basina en
    fazla max_monitors_per_user monitor) oldugu icin agregasyon pipeline'ina
    gerek yok - dogrudan sorgular yeterince hizli.
    """
    checks = monitor.get("checks", {})
    current_status = monitor.get("current_status", {})
    status_since = monitor.get("status_since", {})
    window_start = datetime.now(timezone.utc) - timedelta(hours=_UPTIME_WINDOW_HOURS)

    detail = []
    for check_type in CHECK_TYPES:
        if not checks.get(check_type):
            continue

        total = await db.monitor_results.count_documents(
            {"monitor_id": monitor["_id"], "check_type": check_type, "checked_at": {"$gte": window_start}}
        )
        ok = await db.monitor_results.count_documents(
            {
                "monitor_id": monitor["_id"],
                "check_type": check_type,
                "checked_at": {"$gte": window_start},
                "ok": True,
            }
        )
        uptime_pct = round((ok / total) * 100, 3) if total > 0 else None

        recent_cursor = (
            db.monitor_results.find({"monitor_id": monitor["_id"], "check_type": check_type})
            .sort("checked_at", -1)
            .limit(_HISTORY_BAR_COUNT)
        )
        recent = [r["ok"] async for r in recent_cursor]
        recent.reverse()  # eskiden yeniye - bar gecmisi soldan saga ilerlesin

        since = status_since.get(check_type)
        detail.append(
            {
                "type": check_type,
                "status": current_status.get(check_type, "unknown"),
                "status_since": since.replace(tzinfo=timezone.utc) if since and since.tzinfo is None else since,
                "uptime_pct": uptime_pct,
                "recent_results": recent,
            }
        )
    return detail


@router.get("/monitors")
async def list_monitors(user_id: str = Depends(get_current_user_id)):
    db = get_db()
    docs = await db.monitors.find({"user_id": ObjectId(user_id)}).sort("created_at", -1).to_list(200)
    monitors = []
    for d in docs:
        cleaned = clean_doc(d)
        cleaned["checks_detail"] = await _monitor_check_detail(db, d)
        monitors.append(cleaned)
    return {"monitors": monitors}


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
    return {"monitor": clean_doc(monitor), "results": [clean_doc(r) for r in results]}


@router.patch("/monitors/{monitor_id}")
async def update_monitor(monitor_id: str, body: MonitorRequest, user_id: str = Depends(get_current_user_id)):
    monitor = await _get_own_monitor(monitor_id, user_id)
    try:
        await run_in_threadpool(resolve_public_ip, body.target)
    except UnsafeTargetError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    now = datetime.now(timezone.utc)
    current_status = monitor.get("current_status", {})
    status_since = monitor.get("status_since", {})
    new_status = {t: current_status.get(t, "unknown") for t in CHECK_TYPES if body.checks.get(t)}
    # Yeni etkinlestirilen bir check tipi icin status_since yoksa simdi
    # baslatiliyor; zaten var olanlar (durum degismedigi surece) korunuyor.
    new_status_since = {t: status_since.get(t, now) for t in CHECK_TYPES if body.checks.get(t)}
    await get_db().monitors.update_one(
        {"_id": monitor["_id"]},
        {
            "$set": {
                "target": body.target,
                "checks": body.checks,
                "interval_seconds": body.interval_seconds,
                "current_status": new_status,
                "status_since": new_status_since,
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
