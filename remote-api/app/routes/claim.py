from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query

from app.config import settings
from app.db import get_db
from app.models import ClaimResponse
from app.ratelimit import enforce_rate_limit
from app.registry import QUEUES
from app.security import require_worker_token

router = APIRouter()


@router.get("/v1/claim", response_model=ClaimResponse)
async def claim_batch(
    queue: str = Query(...),
    max_items: int = Query(default=200, gt=0),
    token: dict = Depends(require_worker_token),
):
    if queue not in token.get("queues", []):
        raise HTTPException(status_code=403, detail="Bu token bu kuyruga izinli degil")
    handler = QUEUES.get(queue)
    if handler is None:
        raise HTTPException(status_code=400, detail="Bilinmeyen kuyruk")

    enforce_rate_limit(f"claim:{token['_id']}", settings.rate_limit_claim_per_minute)

    db = get_db()
    max_items = min(max_items, settings.max_batch_size)
    batch_id, items, meta = await handler.claim(db, max_items, token["_id"])

    now = datetime.now(timezone.utc)
    await db.remote_worker_status.update_one(
        {"token_id": token["_id"], "queue": queue},
        {
            "$set": {
                "label": token.get("label"),
                "last_seen_at": now,
                "last_claim_at": now,
                "last_batch_size": len(items),
                "updated_at": now,
            },
            "$inc": {"total_claimed": len(items)},
        },
        upsert=True,
    )

    # Kuyruk modulu kendi LEASE_SECONDS'ini tanimlamissa (orn. port_scan, cok
    # daha uzun bir lease'e ihtiyac duyuyor) onu kullan; tanimlamamissa genel
    # ayara don.
    lease_seconds = getattr(handler, "LEASE_SECONDS", settings.claim_lease_seconds)
    return ClaimResponse(
        batch_id=batch_id,
        queue=queue,
        items=items,
        lease_seconds=lease_seconds,
        meta=meta,
    )
