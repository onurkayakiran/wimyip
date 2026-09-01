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
    """Anasayfada 'IP adresiniz' alani icin - gercek istemci IP'sini dondurur
    (DB'ye dokunmaz). Production'da birden fazla proxy hop'u olabiliyor
    (Cloudflare -> sunucudaki nginx -> bu container) - oncelik sirasi:
    1) CF-Connecting-IP (Cloudflare'in verdigi en guvenilir dogrudan sinyal)
    2) X-Forwarded-For'un ILK (en soldaki) degeri - her hop kendi IP'sini
       SONA ekler, ilk deger her zaman orijinal istemcidir
    3) X-Real-IP (geriye donuk uyumluluk)
    4) dogrudan baglantinin IP'si (proxy'siz erisimde)
    """
    cf_ip = request.headers.get("cf-connecting-ip")
    if cf_ip:
        return {"ip": cf_ip.strip()}

    xff = request.headers.get("x-forwarded-for")
    if xff:
        return {"ip": xff.split(",")[0].strip()}

    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return {"ip": real_ip.strip()}

    return {"ip": request.client.host if request.client else None}
