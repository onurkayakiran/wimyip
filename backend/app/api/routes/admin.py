import hashlib
import ipaddress
import secrets
from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, Header, HTTPException, Query
from pydantic import BaseModel

from app.core.config import settings
from app.core.serialization import clean_doc as _clean
from app.db.mongo import get_db

router = APIRouter()


def _require_admin_password(x_admin_password: str = Header(default="")) -> None:
    if not settings.admin_password or x_admin_password != settings.admin_password:
        raise HTTPException(status_code=401, detail="Gecersiz parola")


@router.post("/admin/login")
async def admin_login(x_admin_password: str = Header(default="")):
    _require_admin_password(x_admin_password)
    return {"ok": True}


class CreateRemoteWorkerTokenRequest(BaseModel):
    label: str
    queues: list[str]


@router.post("/admin/remote-workers/tokens")
async def create_remote_worker_token(
    body: CreateRemoteWorkerTokenRequest, x_admin_password: str = Header(default="")
):
    _require_admin_password(x_admin_password)
    raw = secrets.token_urlsafe(32)
    doc = {
        "label": body.label,
        "queues": body.queues,
        "token_hash": hashlib.sha256(raw.encode()).hexdigest(),
        "created_at": datetime.now(timezone.utc),
        "revoked_at": None,
    }
    result = await get_db().remote_worker_tokens.insert_one(doc)
    # NOT: 'token' alani SADECE bu response'ta doner - hash disinda hicbir
    # yerde saklanmiyor, bir daha hic gosterilemez.
    return {"id": str(result.inserted_id), "token": raw, "label": body.label, "queues": body.queues}


@router.get("/admin/remote-workers/tokens")
async def list_remote_worker_tokens(x_admin_password: str = Header(default="")):
    _require_admin_password(x_admin_password)
    docs = await get_db().remote_worker_tokens.find({}, {"token_hash": 0}).to_list(500)
    return {"tokens": [_clean(d) for d in docs]}


@router.post("/admin/remote-workers/tokens/{token_id}/revoke")
async def revoke_remote_worker_token(token_id: str, x_admin_password: str = Header(default="")):
    _require_admin_password(x_admin_password)
    try:
        oid = ObjectId(token_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Gecersiz token id")
    result = await get_db().remote_worker_tokens.update_one(
        {"_id": oid}, {"$set": {"revoked_at": datetime.now(timezone.utc)}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Token bulunamadi")
    return {"revoked": token_id}


@router.get("/admin/remote-workers/status")
async def remote_worker_status(x_admin_password: str = Header(default="")):
    _require_admin_password(x_admin_password)
    docs = await get_db().remote_worker_status.find({}).to_list(500)
    return {"workers": [_clean(d) for d in docs]}


class CreatePortScanJobRequest(BaseModel):
    target: str
    port_mode: str = "custom"
    custom_ports: list[int] = []
    delay_seconds: float | None = None
    timeout: float = 1.0
    enable_service_detect: bool = True
    syn_scan: bool = True


@router.post("/admin/port-scans")
async def create_port_scan_job(body: CreatePortScanJobRequest, x_admin_password: str = Header(default="")):
    _require_admin_password(x_admin_password)
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
        "target": str(network),
        "status": "pending",
        "created_at": datetime.now(timezone.utc),
        "created_by": "admin",
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
    result = await get_db().port_scan_jobs.insert_one(doc)
    return _clean({**doc, "_id": result.inserted_id})


@router.get("/admin/port-scans")
async def list_port_scan_jobs(
    limit: int = Query(50, le=200), offset: int = 0, x_admin_password: str = Header(default="")
):
    _require_admin_password(x_admin_password)
    db = get_db()
    cursor = db.port_scan_jobs.find({}).sort("created_at", -1).skip(offset).limit(limit)
    items = [_clean(d) async for d in cursor]
    total = await db.port_scan_jobs.count_documents({})
    return {"total": total, "items": items}


@router.get("/admin/port-scans/{job_id}")
async def get_port_scan_job(job_id: str, x_admin_password: str = Header(default="")):
    _require_admin_password(x_admin_password)
    try:
        oid = ObjectId(job_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Gecersiz job id")
    job = await get_db().port_scan_jobs.find_one({"_id": oid})
    if not job:
        raise HTTPException(status_code=404, detail="Job bulunamadi")
    results = await get_db().port_scan_results.find({"job_id": oid}).sort("ip_int", 1).to_list(2000)
    return {"job": _clean(job), "results": [_clean(r) for r in results]}


@router.post("/admin/port-scans/{job_id}/reset")
async def reset_port_scan_job(job_id: str, x_admin_password: str = Header(default="")):
    _require_admin_password(x_admin_password)
    # Worker cokup lease suresi dolmadan takili kalmis (status="claimed"
    # veya "running") bir job'u elle "pending"e geri almak icin - normalde
    # bu otomatik lease-expiry ile kendiliginden olur (bkz.
    # remote-api/app/queues/port_scan.py), bu sadece admin'in erken
    # mudahale etmek istedigi durum icin bir supap.
    try:
        oid = ObjectId(job_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Gecersiz job id")
    result = await get_db().port_scan_jobs.update_one(
        {"_id": oid, "status": {"$in": ["claimed", "running"]}},
        {
            "$set": {"status": "pending"},
            "$unset": {"claimed_at": "", "claimed_by_token_id": "", "lease_expires_at": ""},
        },
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Job bulunamadi veya zaten claimed/running durumunda degil")
    return {"reset": job_id}
