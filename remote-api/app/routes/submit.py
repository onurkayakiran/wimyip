from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from app.config import settings
from app.db import get_db
from app.models import SubmitRequest, SubmitResponse
from app.ratelimit import enforce_rate_limit
from app.registry import QUEUES
from app.security import require_worker_token

router = APIRouter()


@router.post("/v1/submit", response_model=SubmitResponse)
async def submit_results(body: SubmitRequest, token: dict = Depends(require_worker_token)):
    if body.queue not in token.get("queues", []):
        raise HTTPException(status_code=403, detail="Bu token bu kuyruga izinli degil")
    handler = QUEUES.get(body.queue)
    if handler is None:
        raise HTTPException(status_code=400, detail="Bilinmeyen kuyruk")

    enforce_rate_limit(f"submit:{token['_id']}", settings.rate_limit_submit_per_minute)

    db = get_db()
    try:
        result = await handler.apply(db, body.batch_id, token, body.results)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))

    now = datetime.now(timezone.utc)
    await db.remote_worker_status.update_one(
        {"token_id": token["_id"], "queue": body.queue},
        {
            "$set": {
                "label": token.get("label"),
                "last_seen_at": now,
                "last_submit_at": now,
                "last_batch_found": result["found"],
                "updated_at": now,
            },
            "$inc": {"total_submitted": len(body.results)},
        },
        upsert=True,
    )
    return SubmitResponse(accepted=True, written=result["written"], found=result["found"])
