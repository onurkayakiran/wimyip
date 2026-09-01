from datetime import datetime, timedelta, timezone

import bcrypt
from fastapi import Header, HTTPException
from jose import JWTError, jwt

from app.core.config import settings

_ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def create_access_token(user_id: str) -> str:
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {"sub": user_id, "exp": expires_at}
    return jwt.encode(payload, settings.jwt_secret, algorithm=_ALGORITHM)


def decode_access_token(token: str) -> str:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[_ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=401, detail="Gecersiz veya suresi dolmus oturum")
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Gecersiz oturum")
    return user_id


def get_current_user_id(authorization: str = Header(default="")) -> str:
    # Cookie/session yerine bilhassa Authorization: Bearer <token> - mevcut
    # X-Admin-Password header konvansiyonuyla ayni ruhta, ve backend'in
    # CORS'u (allow_origins=["*"], allow_credentials yok) cookie tabanli bir
    # semayla uyumsuz olurdu.
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Oturum acilmamis")
    token = authorization[len("Bearer ") :]
    return decode_access_token(token)
