import logging
import time
from datetime import datetime, timezone

import tldextract
from bson import ObjectId

from app.core.config import settings
from app.db.sync_client import get_sync_db
from app.ingestion.dns_history_sync import sync_domain_dns

logger = logging.getLogger(__name__)

JOB_NAME_PREFIX = "domain_apex_scan"

# suffix_list_urls=() -> SADECE paketle gelen sabit Public Suffix List
# kullanilir, calisma zamaninda hic ag istegi atilmaz (container'in disari
# HTTPS erisimi olmasa/kesintili olsa bile guvenilir calisir).
_extract = tldextract.TLDExtract(suffix_list_urls=())


def _is_apex_domain(domain: str) -> bool:
    """Public Suffix List'e gore domain'in ana (apex) domain mi yoksa
    subdomain mi oldugunu belirler - orn. "example.com.tr" icin True,
    "webmail.example.com.tr" icin False doner. "com.tr" gibi coklu-parcali
    bir suffix oldugu icin naif 'son 2 parcayi al' mantigi burada yanlis
    sonuc verirdi.
    """
    ext = _extract(domain)
    if not ext.domain or not ext.suffix:
        return False
    return domain == f"{ext.domain}.{ext.suffix}"


def _domains_in_prefix(db, start_ip: int, end_ip: int, limit: int) -> list[str]:
    cursor = db.domain_ip_history.find(
        {"ip_int": {"$gte": start_ip, "$lte": end_ip}},
        {"domain": 1},
    ).limit(limit)
    return list({doc["domain"] for doc in cursor})


def run_domain_apex_batch(
    country: str | None = None,
    job_name: str | None = None,
    batch_size: int | None = None,
    domains_per_prefix: int | None = None,
    rate_limit_seconds: float | None = None,
) -> dict:
    """`country`'ye (RIR verisindeki `prefixes.country`, orn "TR") tahsisli
    prefix'leri sirayla dolasir; her prefix'in IP araligindaki (`domain_ip_history.ip_int`
    uzerinden) bilinen domain'lerden SADECE apex (ana, subdomain olmayan)
    olanlari icin `sync_domain_dns`'i (A/AAAA/NS/MX/TXT) tetikler. Subdomain'lere
    hic dokunmaz - onlar `dns_history_sync`'in genel dongusunde kalir.
    """
    country = country or settings.target_country
    job_name = job_name or f"{JOB_NAME_PREFIX}:{country}"
    batch_size = batch_size if batch_size is not None else settings.apex_country_batch_size
    domains_per_prefix = (
        domains_per_prefix if domains_per_prefix is not None else settings.apex_country_domains_per_prefix
    )
    rate_limit_seconds = (
        rate_limit_seconds if rate_limit_seconds is not None else settings.apex_country_rate_limit_seconds
    )

    db = get_sync_db()
    try:
        job = db.ingestion_jobs.find_one({"job": job_name}) or {}
        # cursor JSON-serialize edilebilir kalsin diye (ornegin /api/status)
        # ingestion_jobs'ta string olarak saklanir, Mongo sorgusu icin tekrar
        # ObjectId'ye cevrilir.
        last_cursor = job.get("cursor")
        last_id = ObjectId(last_cursor) if last_cursor else None

        query = {"country": country, "version": 4}
        if last_id is not None:
            query["_id"] = {"$gt": last_id}
        prefixes = list(db.prefixes.find(query).sort("_id", 1).limit(batch_size))

        wrapped = False
        if not prefixes:
            wrapped = True
            prefixes = list(
                db.prefixes.find({"country": country, "version": 4}).sort("_id", 1).limit(batch_size)
            )

        prefixes_processed = 0
        apex_synced = 0
        failed = 0

        for prefix in prefixes:
            last_id = prefix["_id"]
            prefixes_processed += 1
            candidates = _domains_in_prefix(db, prefix["start_ip"], prefix["end_ip"], domains_per_prefix)
            for domain in candidates:
                if not _is_apex_domain(domain):
                    continue
                try:
                    sync_domain_dns(domain)
                    db.domains.update_one({"domain": domain}, {"$addToSet": {"sources": "tr_apex_scan"}})
                    apex_synced += 1
                except Exception:
                    logger.exception("%s: domain basarisiz (%s)", job_name, domain)
                    failed += 1
                time.sleep(rate_limit_seconds)

        db.ingestion_jobs.update_one(
            {"job": job_name},
            {
                "$set": {
                    "status": "ok",
                    "cursor": str(last_id) if last_id is not None else None,
                    "updated_at": datetime.now(timezone.utc),
                    "last_batch_processed": prefixes_processed,
                    "last_batch_found": apex_synced,
                    "last_batch_failed": failed,
                    "wrapped_around": wrapped,
                },
                "$unset": {"last_error": ""},
            },
            upsert=True,
        )
        return {
            "prefixes_processed": prefixes_processed,
            "apex_domains_synced": apex_synced,
            "failed": failed,
            "next_cursor": str(last_id) if last_id is not None else None,
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
