import logging
import time
from datetime import datetime, timezone

from app.db.sync_client import get_sync_db

logger = logging.getLogger(__name__)


def run_resumable_batch(job_name, fetch_page, process_one, cursor_value, rate_limit_seconds):
    """Keyset (cursor tabanli) sayfalama ile hiz-sinirli, devam edilebilir bir
    toplu is turu calistirir. Her calisma bir onceki calismanin kaldigi
    yerden devam eder; koleksiyonun sonuna gelince basa doner (surekli,
    kademeli yeniden tarama). RDAP, RIPEstat ve PeeringDB zenginlestirme
    gorevleri tarafindan ortak kullanilir.

    fetch_page(db, cursor) -> list[doc]   (cursor=None -> ilk sayfa/basa donus)
    process_one(doc) -> None              (dis servise sorup DB'ye yazar)
    cursor_value(doc) -> yeni cursor degeri

    Tum calisma tek bir try/except ile sarilidir: fetch_page veya baglanti
    seviyesinde toptan bir hata olursa (orn. dis servis tamamen erisilemez),
    bu durum sessizce yutulup bir sonraki beat tick'ine birakilmaz - ilgili
    ingestion_jobs kaydina status="error" + last_error yazilir ve hata
    Celery'nin de gorebilmesi icin tekrar firlatilir.
    """
    db = get_sync_db()
    try:
        job = db.ingestion_jobs.find_one({"job": job_name}) or {}
        cursor = job.get("cursor")

        docs = fetch_page(db, cursor)
        wrapped = False
        if not docs:
            wrapped = True
            docs = fetch_page(db, None)

        processed = 0
        failed = 0
        for doc in docs:
            try:
                process_one(doc)
                processed += 1
            except Exception:
                logger.exception("%s: is basarisiz (%s)", job_name, doc)
                failed += 1
            time.sleep(rate_limit_seconds)

        new_cursor = cursor_value(docs[-1]) if docs else None
        db.ingestion_jobs.update_one(
            {"job": job_name},
            {
                "$set": {
                    "status": "ok",
                    "cursor": new_cursor,
                    "updated_at": datetime.now(timezone.utc),
                    "last_batch_processed": processed,
                    "last_batch_failed": failed,
                    "wrapped_around": wrapped,
                },
                "$unset": {"last_error": ""},
            },
            upsert=True,
        )
        return {
            "processed": processed,
            "failed": failed,
            "next_cursor": new_cursor,
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
