import re
import time
from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, field_validator
from pymongo.errors import DuplicateKeyError

from app.core.security import create_access_token, get_current_user_id, hash_password, verify_password
from app.core.serialization import clean_doc
from app.db.mongo import get_db

router = APIRouter()

_USERNAME_RE = re.compile(r"^[a-zA-Z0-9_.-]{3,32}$")
# pydantic'in EmailStr'i ekstra bir 'email-validator' paketi gerektiriyor -
# bagimliligi artirmamak icin basit ama yeterli bir regex kullaniyoruz.
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# Basit, kalici olmayan (in-memory) brute-force korumasi: IP basina 15
# dakikada 10 basarisiz denemeden fazlasi reddedilir. Kalici bir depolama
# gerektirmeyen kucuk bir ek - process yeniden basladiginda sifirlanir,
# kisisel/kucuk olcekli bir proje icin yeterli.
_RATE_LIMIT_WINDOW_SECONDS = 15 * 60
_RATE_LIMIT_MAX_ATTEMPTS = 10
_attempts: dict[str, list[float]] = {}


def _check_rate_limit(ip: str) -> None:
    now = time.time()
    window_start = now - _RATE_LIMIT_WINDOW_SECONDS
    recent = [t for t in _attempts.get(ip, []) if t > window_start]
    if len(recent) >= _RATE_LIMIT_MAX_ATTEMPTS:
        raise HTTPException(status_code=429, detail="Cok fazla deneme, biraz sonra tekrar deneyin")
    recent.append(now)
    _attempts[ip] = recent


def _validate_password_str(v: str) -> str:
    if len(v) < 8:
        raise ValueError("Parola en az 8 karakter olmali")
    # bcrypt 72 BAYT'tan uzun parolalarda hata veriyor.
    if len(v.encode("utf-8")) > 72:
        raise ValueError("Parola en fazla 72 karakter olmali")
    return v


class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str

    @field_validator("username")
    @classmethod
    def _validate_username(cls, v: str) -> str:
        if not _USERNAME_RE.match(v):
            raise ValueError("Kullanici adi 3-32 karakter olmali, sadece harf/rakam/._- icerebilir")
        return v

    @field_validator("email")
    @classmethod
    def _validate_email(cls, v: str) -> str:
        if not _EMAIL_RE.match(v):
            raise ValueError("Gecersiz e-posta adresi")
        return v

    @field_validator("password")
    @classmethod
    def _validate_password(cls, v: str) -> str:
        return _validate_password_str(v)


class LoginRequest(BaseModel):
    username: str
    password: str


class UpdateProfileRequest(BaseModel):
    email: str
    first_name: str = ""
    last_name: str = ""

    @field_validator("email")
    @classmethod
    def _validate_email(cls, v: str) -> str:
        if not _EMAIL_RE.match(v):
            raise ValueError("Gecersiz e-posta adresi")
        return v


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def _validate_new_password(cls, v: str) -> str:
        return _validate_password_str(v)


def _clean_user(doc: dict) -> dict:
    # Sifre hash'i asla API yanitlarina sizmamali.
    doc = dict(doc)
    doc.pop("password_hash", None)
    return clean_doc(doc)


@router.post("/auth/register")
async def register(body: RegisterRequest, request: Request):
    _check_rate_limit(request.client.host if request.client else "unknown")
    doc = {
        "username": body.username,
        "email": body.email,
        "password_hash": hash_password(body.password),
        "first_name": "",
        "last_name": "",
        # Herkes once free olarak kayit olur - premium'a gecis SADECE admin
        # tarafindan yapilir (bkz. /admin/users/{id}/plan). Odeme entegrasyonu
        # yok, bilerek - plan degisimi elle yonetiliyor.
        "plan": "free",
        "created_at": datetime.now(timezone.utc),
    }
    try:
        result = await get_db().users.insert_one(doc)
    except DuplicateKeyError:
        raise HTTPException(status_code=409, detail="Bu kullanici adi veya e-posta zaten kayitli")

    token = create_access_token(str(result.inserted_id))
    return {"access_token": token, "token_type": "bearer"}


@router.post("/auth/login")
async def login(body: LoginRequest, request: Request):
    _check_rate_limit(request.client.host if request.client else "unknown")
    user = await get_db().users.find_one(
        {"$or": [{"username": body.username}, {"email": body.username}]}
    )
    if not user or not verify_password(body.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Kullanici adi veya parola hatali")

    token = create_access_token(str(user["_id"]))
    return {"access_token": token, "token_type": "bearer"}


@router.get("/auth/me")
async def get_me(user_id: str = Depends(get_current_user_id)):
    user = await get_db().users.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=404, detail="Kullanici bulunamadi")
    return _clean_user(user)


@router.patch("/auth/me")
async def update_me(body: UpdateProfileRequest, user_id: str = Depends(get_current_user_id)):
    oid = ObjectId(user_id)
    try:
        await get_db().users.update_one(
            {"_id": oid},
            {"$set": {"email": body.email, "first_name": body.first_name, "last_name": body.last_name}},
        )
    except DuplicateKeyError:
        raise HTTPException(status_code=409, detail="Bu e-posta zaten kullaniliyor")
    user = await get_db().users.find_one({"_id": oid})
    return _clean_user(user)


@router.post("/auth/change-password")
async def change_password(body: ChangePasswordRequest, user_id: str = Depends(get_current_user_id)):
    oid = ObjectId(user_id)
    user = await get_db().users.find_one({"_id": oid})
    if not user or not verify_password(body.current_password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Mevcut parola hatali")
    await get_db().users.update_one({"_id": oid}, {"$set": {"password_hash": hash_password(body.new_password)}})
    return {"ok": True}
