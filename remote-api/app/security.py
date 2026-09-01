import hashlib

from fastapi import Header, HTTPException

from app.db import get_db


def hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


async def require_worker_token(authorization: str = Header(default="")) -> dict:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Gecersiz token")
    raw = authorization.removeprefix("Bearer ").strip()
    doc = await get_db().remote_worker_tokens.find_one({"token_hash": hash_token(raw)})
    if not doc or doc.get("revoked_at"):
        raise HTTPException(status_code=401, detail="Gecersiz veya iptal edilmis token")
    return doc
