import logging
import time
from datetime import datetime, timezone

from app.core.config import settings
from app.db.sync_client import get_sync_db
from app.ingestion.ptr_sync import sync_ptr

logger = logging.getLogger(__name__)

JOB_NAME = "ptr_sweep"


def _next_target_ip(db, after_ip: int) -> int | None:
    """Verilen IP'den sonraki, ALLOCATED bir RIR prefix'inin icine dusen bir
    sonraki hedef IP'yi bulur. Boylece sadece gercekten tahsis edilmis
    bloklar taranir, bos/rezerve edilmemis adres uzayinda vakit kaybedilmez.
    """
    candidate = after_ip + 1
    inside = db.prefixes.find_one(
        {"version": 4, "start_ip": {"$lte": candidate}, "end_ip": {"$gte": candidate}},
        {"_id": 1},
    )
    if inside:
        return candidate

    nxt = db.prefixes.find_one(
        {"version": 4, "start_ip": {"$gt": candidate}},
        sort=[("start_ip", 1)],
        projection={"start_ip": 1},
    )
    return nxt["start_ip"] if nxt else None


def run_ptr_sweep_batch() -> dict:
    db = get_sync_db()
    try:
        job = db.ingestion_jobs.find_one({"job": JOB_NAME}) or {}
        current = job.get("cursor", -1)

        processed = 0
        found = 0
        failed = 0
        wrapped = False

        for _ in range(settings.ptr_batch_size):
            nxt = _next_target_ip(db, current)
            if nxt is None:
                wrapped = True
                current = -1
                nxt = _next_target_ip(db, current)
                if nxt is None:
                    break  # DB'de hic allocated IPv4 prefix yok

            try:
                hostname = sync_ptr(nxt)
                processed += 1
                if hostname:
                    found += 1
            except Exception:
                logger.exception("%s: IP basarisiz (%s)", JOB_NAME, nxt)
                failed += 1
            current = nxt
            time.sleep(settings.ptr_rate_limit_seconds)

        db.ingestion_jobs.update_one(
            {"job": JOB_NAME},
            {
                "$set": {
                    "status": "ok",
                    "cursor": current,
                    "updated_at": datetime.now(timezone.utc),
                    "last_batch_processed": processed,
                    "last_batch_found": found,
                    "last_batch_failed": failed,
                    "wrapped_around": wrapped,
                },
                "$unset": {"last_error": ""},
            },
            upsert=True,
        )
        return {
            "processed": processed,
            "found": found,
            "failed": failed,
            "next_cursor": current,
            "wrapped_around": wrapped,
        }
    except Exception as exc:
        logger.exception("%s: batch tamamen basarisiz oldu", JOB_NAME)
        db.ingestion_jobs.update_one(
            {"job": JOB_NAME},
            {
                "$set": {
                    "status": "error",
                    "updated_at": datetime.now(timezone.utc),
                    "last_error": str(exc),
                }
            },
            upsert=True,
        )
        raise


if __name__ == "__main__":
    import json

    logging.basicConfig(level=logging.INFO)
    print(json.dumps(run_ptr_sweep_batch(), default=str, indent=2))
