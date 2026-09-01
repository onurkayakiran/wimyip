import hashlib
import secrets
from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, Header, HTTPException
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


class SetUserPlanRequest(BaseModel):
    plan: str


@router.get("/admin/users")
async def list_users(x_admin_password: str = Header(default="")):
    _require_admin_password(x_admin_password)
    db = get_db()
    users = await db.users.find({}, {"password_hash": 0}).sort("created_at", -1).to_list(1000)
    result = []
    for u in users:
        monitor_count = await db.monitors.count_documents({"user_id": u["_id"]})
        cleaned = _clean(u)
        cleaned["monitor_count"] = monitor_count
        result.append(cleaned)
    return {"users": result}


@router.post("/admin/users/{user_id}/plan")
async def set_user_plan(user_id: str, body: SetUserPlanRequest, x_admin_password: str = Header(default="")):
    _require_admin_password(x_admin_password)
    if body.plan not in ("free", "premium"):
        raise HTTPException(status_code=400, detail="Gecersiz plan (free|premium olmali)")
    try:
        oid = ObjectId(user_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Gecersiz kullanici id")
    result = await get_db().users.update_one({"_id": oid}, {"$set": {"plan": body.plan}})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Kullanici bulunamadi")
    return {"user_id": user_id, "plan": body.plan}
