import requests
from fastapi import APIRouter, Header, HTTPException, Query
from fastapi.concurrency import run_in_threadpool

from app.core.config import settings

router = APIRouter()


def _require_admin_password(x_admin_password: str = Header(default="")) -> None:
    if not settings.admin_password or x_admin_password != settings.admin_password:
        raise HTTPException(status_code=401, detail="Gecersiz parola")


def _control_headers() -> dict:
    return {"X-Control-Token": settings.control_service_token}


def _control_request(method: str, path: str, **kwargs):
    try:
        resp = requests.request(
            method, f"{settings.control_service_url}{path}", headers=_control_headers(), timeout=15, **kwargs
        )
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail=f"control servisine ulasilamadi: {exc}")

    if resp.status_code >= 400:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    return resp.json()


@router.post("/admin/login")
async def admin_login(x_admin_password: str = Header(default="")):
    _require_admin_password(x_admin_password)
    return {"ok": True}


@router.get("/admin/services")
async def admin_services(x_admin_password: str = Header(default="")):
    _require_admin_password(x_admin_password)
    return await run_in_threadpool(_control_request, "GET", "/services")


@router.get("/admin/services/{service}/logs")
async def admin_service_logs(service: str, tail: int = Query(default=200, le=2000), x_admin_password: str = Header(default="")):
    _require_admin_password(x_admin_password)
    return await run_in_threadpool(_control_request, "GET", f"/services/{service}/logs", params={"tail": tail})


@router.post("/admin/services/{service}/restart")
async def admin_restart_service(service: str, x_admin_password: str = Header(default="")):
    _require_admin_password(x_admin_password)
    return await run_in_threadpool(_control_request, "POST", f"/services/{service}/restart")
