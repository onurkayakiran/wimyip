import logging
import time
from datetime import datetime, timezone

from app.core.config import settings
from app.db.sync_client import get_sync_db
from app.ingestion.ptr_sync import sync_ptr

logger = logging.getLogger(__name__)

JOB_NAME = "ptr_sweep"


def _next_target_ip(db, after_ip: int, country: str | None = None) -> int | None:
    """Verilen IP'den sonraki, ALLOCATED bir RIR prefix'inin icine dusen bir
    sonraki hedef IP'yi bulur. Boylece sadece gercekten tahsis edilmis
    bloklar taranir, bos/rezerve edilmemis adres uzayinda vakit kaybedilmez.
    `country` verilirse (orn. "TR") sadece o ulkeye tahsisli bloklar taranir.
    """
    candidate = after_ip + 1

    inside_query = {"version": 4, "start_ip": {"$lte": candidate}, "end_ip": {"$gte": candidate}}
    if country:
        inside_query["country"] = country
    inside = db.prefixes.find_one(inside_query, {"_id": 1})
    if inside:
        return candidate

    next_query = {"version": 4, "start_ip": {"$gt": candidate}}
    if country:
        next_query["country"] = country
    nxt = db.prefixes.find_one(
        next_query,
        sort=[("start_ip", 1)],
        projection={"start_ip": 1},
    )
    return nxt["start_ip"] if nxt else None


def run_ptr_sweep_batch(
    job_name: str = JOB_NAME,
    country: str | None = None,
    batch_size: int | None = None,
    rate_limit_seconds: float | None = None,
) -> dict:
    """`job_name`/`country` verilmezse global (tum dunya) sweep gibi davranir -
    mevcut davranisla tam geriye donuk uyumlu. `country` verilirse (orn. "TR")
    sadece o ulkenin bloklarini tarar ve KENDI `job_name`'iyle ayri bir
    cursor tutar - global sweep'in cursor'una hic dokunmaz.
    """
    batch_size = batch_size if batch_size is not None else settings.ptr_batch_size
    rate_limit_seconds = (
        rate_limit_seconds if rate_limit_seconds is not None else settings.ptr_rate_limit_seconds
    )
    db = get_sync_db()
    try:
        job = db.ingestion_jobs.find_one({"job": job_name}) or {}
        current = job.get("cursor", -1)

        processed = 0
        found = 0
        failed = 0
        wrapped = False

        for _ in range(batch_size):
            nxt = _next_target_ip(db, current, country)
            if nxt is None:
                wrapped = True
                current = -1
                nxt = _next_target_ip(db, current, country)
                if nxt is None:
                    break  # DB'de hic allocated IPv4 prefix yok

            try:
                hostname = sync_ptr(nxt)
                processed += 1
                if hostname:
                    found += 1
            except Exception:
                logger.exception("%s: IP basarisiz (%s)", job_name, nxt)
                failed += 1
            current = nxt
            time.sleep(rate_limit_seconds)

        db.ingestion_jobs.update_one(
            {"job": job_name},
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
        logger.exception("%s: batch tamamen basarisiz oldu", job_name)
        db.ingestion_jobs.update_one(
            {"job": job_name},
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
