import logging
from datetime import datetime, timezone

from app.core.config import settings
from app.db.sync_client import get_sync_db
from app.ingestion.ct_client import (
    fetch_certificates,
    fetch_max_certificate_id,
    fetch_new_certificate_ids,
)
from app.ingestion.ct_sync import sync_certificates

logger = logging.getLogger(__name__)

JOB_NAME = "ct_log_sync"

# cursor guncel maksimumdan bu kadar (veya daha fazla) geride kalmissa ve
# aralarinda hic yeni kayit bulunamiyorsa, cursor'u "simdi"ye yakin bir
# noktaya atlatiyoruz. Bu, orn. eski bir yedekten geri yuklenen veya uzun
# sure calismamis bir ortamda cursor'un crt.sh'nin (replica) artik
# sorgulanamayan/budanmis eski bir ID araliginda sonsuza kadar sikisip
# kalmasini onler.
_STUCK_GAP_THRESHOLD = 1_000_000


def run_ct_sync_batch() -> dict:
    db = get_sync_db()
    try:
        job = db.ingestion_jobs.find_one({"job": JOB_NAME}) or {}
        cursor = job.get("cursor")

        if cursor is None:
            # Ilk calisma: CT gunlugunun tum tarihini (milyarlarca kayit)
            # tekrar oynatmak yerine "su an"dan itibaren canli takibe basla.
            cursor = fetch_max_certificate_id()

        ids = fetch_new_certificate_ids(cursor, settings.ct_batch_size)
        if not ids:
            jumped = False
            current_max = fetch_max_certificate_id()
            if current_max - cursor > _STUCK_GAP_THRESHOLD:
                logger.warning(
                    "%s: cursor (%s) guncel maksimumdan (%s) cok geride kaldi, "
                    "'simdi'ye atlaniyor",
                    JOB_NAME,
                    cursor,
                    current_max,
                )
                cursor = current_max
                jumped = True

            db.ingestion_jobs.update_one(
                {"job": JOB_NAME},
                {
                    "$set": {"status": "ok", "cursor": cursor, "updated_at": datetime.now(timezone.utc)},
                    "$unset": {"last_error": ""},
                },
                upsert=True,
            )
            return {"processed": 0, "domains_written": 0, "next_cursor": cursor, "jumped": jumped}

        certs = fetch_certificates(ids)
        written = sync_certificates(certs)

        new_cursor = max(ids)
        db.ingestion_jobs.update_one(
            {"job": JOB_NAME},
            {
                "$set": {
                    "status": "ok",
                    "cursor": new_cursor,
                    "updated_at": datetime.now(timezone.utc),
                    "last_batch_processed": len(ids),
                    "last_batch_domains": written,
                },
                "$unset": {"last_error": ""},
            },
            upsert=True,
        )
        return {"processed": len(ids), "domains_written": written, "next_cursor": new_cursor}
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
    print(json.dumps(run_ct_sync_batch(), default=str, indent=2))
