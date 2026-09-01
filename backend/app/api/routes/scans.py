import ipaddress
from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.core.config import settings
from app.core.plans import get_user_plan
from app.core.security import get_current_user_id
from app.core.serialization import clean_doc
from app.db.mongo import get_db

router = APIRouter()

_ACTIVE_STATUSES = ["pending", "claimed", "running"]


async def _require_premium(user_id: str) -> None:
    plan = await get_user_plan(user_id)
    if plan != "premium":
        raise HTTPException(status_code=403, detail="Bu özellik premium üyelik gerektiriyor")


class CreatePortScanJobRequest(BaseModel):
    target: str
    port_mode: str = "custom"
    custom_ports: list[int] = []
    delay_seconds: float | None = None
    timeout: float = 1.0
    enable_service_detect: bool = True
    syn_scan: bool = True


@router.post("/scans")
async def create_scan_job(body: CreatePortScanJobRequest, user_id: str = Depends(get_current_user_id)):
    await _require_premium(user_id)
    db = get_db()

    active_count = await db.port_scan_jobs.count_documents(
        {"user_id": ObjectId(user_id), "status": {"$in": _ACTIVE_STATUSES}}
    )
    if active_count >= settings.max_active_scans_per_user:
        raise HTTPException(
            status_code=400,
            detail=f"Aynı anda en fazla {settings.max_active_scans_per_user} aktif tarama olabilir",
        )

    try:
        network = ipaddress.ip_network(body.target.strip(), strict=False)
    except ValueError:
        raise HTTPException(status_code=400, detail="Gecersiz IP/CIDR")
    if network.version != 4:
        raise HTTPException(status_code=400, detail="Sadece IPv4 destekleniyor")

    # /31 ve /32 icin num_addresses zaten dogru host sayisini verir (network/
    # broadcast ayrimi yok) - .hosts() ile ayni davranis (bkz. Python stdlib).
    host_count = network.num_addresses if network.prefixlen >= 31 else network.num_addresses - 2
    if host_count > settings.portscan_max_hosts:
        raise HTTPException(
            status_code=400,
            detail=f"Hedef {host_count} host iceriyor, izin verilen ust sinir {settings.portscan_max_hosts}",
        )
    if body.port_mode == "custom" and not body.custom_ports:
        raise HTTPException(status_code=400, detail="custom port modu icin en az bir port girilmeli")

    doc = {
        "user_id": ObjectId(user_id),
        "target": str(network),
        "status": "pending",
        "created_at": datetime.now(timezone.utc),
        "host_count": host_count,
        "meta": {
            "port_mode": body.port_mode,
            "custom_ports": sorted(set(body.custom_ports)),
            "delay_seconds": body.delay_seconds
            if body.delay_seconds is not None
            else settings.portscan_default_delay_seconds,
            "timeout": body.timeout,
            "enable_service_detect": body.enable_service_detect,
            "syn_scan": body.syn_scan,
        },
    }
    result = await db.port_scan_jobs.insert_one(doc)
    return clean_doc({**doc, "_id": result.inserted_id})


@router.get("/scans")
async def list_scan_jobs(
    limit: int = Query(50, le=200), offset: int = 0, user_id: str = Depends(get_current_user_id)
):
    await _require_premium(user_id)
    db = get_db()
    query = {"user_id": ObjectId(user_id)}
    cursor = db.port_scan_jobs.find(query).sort("created_at", -1).skip(offset).limit(limit)
    items = [clean_doc(d) async for d in cursor]
    total = await db.port_scan_jobs.count_documents(query)
    return {"total": total, "items": items}


@router.get("/scans/{job_id}")
async def get_scan_job(job_id: str, user_id: str = Depends(get_current_user_id)):
    await _require_premium(user_id)
    try:
        oid = ObjectId(job_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Gecersiz job id")
    job = await get_db().port_scan_jobs.find_one({"_id": oid, "user_id": ObjectId(user_id)})
    if not job:
        raise HTTPException(status_code=404, detail="Job bulunamadi")
    results = await get_db().port_scan_results.find({"job_id": oid}).sort("ip_int", 1).to_list(2000)
    return {"job": clean_doc(job), "results": [clean_doc(r) for r in results]}


@router.post("/scans/{job_id}/reset")
async def reset_scan_job(job_id: str, user_id: str = Depends(get_current_user_id)):
    await _require_premium(user_id)
    # Worker cokup lease suresi dolmadan takili kalmis (status="claimed"
    # veya "running") bir job'u elle "pending"e geri almak icin - normalde
    # bu otomatik lease-expiry ile kendiliginden olur (bkz.
    # remote-api/app/queues/port_scan.py), bu sadece erken mudahale
    # icin bir supap.
    try:
        oid = ObjectId(job_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Gecersiz job id")
    result = await get_db().port_scan_jobs.update_one(
        {"_id": oid, "user_id": ObjectId(user_id), "status": {"$in": ["claimed", "running"]}},
        {
            "$set": {"status": "pending"},
            "$unset": {"claimed_at": "", "claimed_by_token_id": "", "lease_expires_at": ""},
        },
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Job bulunamadi veya zaten claimed/running durumunda degil")
    return {"reset": job_id}
