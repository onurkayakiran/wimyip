from fastapi import APIRouter, Request

from app.db.mongo import get_db

router = APIRouter()


@router.get("/health")
async def health():
    db = get_db()
    await db.command("ping")
    return {"status": "ok"}


@router.get("/whoami")
async def whoami(request: Request):
    """Anasayfada 'IP adresiniz' alani icin - nginx'in ilettigi gercek
    istemci IP'sini dondurur (DB'ye dokunmaz).
    """
    ip = (
        request.headers.get("x-real-ip")
        or (request.headers.get("x-forwarded-for") or "").split(",")[0].strip()
        or (request.client.host if request.client else None)
    )
    return {"ip": ip}
