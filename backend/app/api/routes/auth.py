import re
import time
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, field_validator
from pymongo.errors import DuplicateKeyError

from app.core.security import create_access_token, hash_password, verify_password
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
        if len(v) < 8:
            raise ValueError("Parola en az 8 karakter olmali")
        # bcrypt 72 BAYT'tan uzun parolalarda hata veriyor.
        if len(v.encode("utf-8")) > 72:
            raise ValueError("Parola en fazla 72 karakter olmali")
        return v


class LoginRequest(BaseModel):
    username: str
    password: str


@router.post("/auth/register")
async def register(body: RegisterRequest, request: Request):
    _check_rate_limit(request.client.host if request.client else "unknown")
    doc = {
        "username": body.username,
        "email": body.email,
        "password_hash": hash_password(body.password),
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
    user = await get_db().users.find_one({"username": body.username})
    if not user or not verify_password(body.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Kullanici adi veya parola hatali")

    token = create_access_token(str(user["_id"]))
    return {"access_token": token, "token_type": "bearer"}
