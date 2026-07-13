from datetime import datetime, timezone

from fastapi import APIRouter

from app.db.mongo import get_db

router = APIRouter()


@router.get("/stats")
async def stats():
    db = get_db()
    return {
        "prefixes": await db.prefixes.count_documents({}),
        "asns": await db.asns.count_documents({}),
        "domains": await db.domains.count_documents({}),
    }


def _clean(doc: dict) -> dict:
    doc = dict(doc)
    doc.pop("_id", None)
    return doc


# Her gorevin celery beat zamanlamasina karsilik gelen, "bu sureden uzun
# suredir guncellenmediyse bir seyler ters gitmis olabilir" esigi (saniye).
# Zamanlamanin birkac kati tolerans birakildi (beat gecikmesi/uzun batch'ler
# normal olabilir), amac sadece TAMAMEN durmus/kilitlenmis gorevleri yakalamak.
_STALE_THRESHOLDS = [
    ("rir_sync", 60 * 60 * 30),  # gunluk (03:00 UTC) -> 30 saat
    ("rdap_sync", 60 * 20),  # 5 dk -> 20 dk
    ("bgp_sync", 60 * 20),
    ("peeringdb_sync", 60 * 20),
    ("ct_log_sync", 60 * 10),  # 2 dk -> 10 dk
    ("ptr_sweep", 60 * 10),  # 1 dk -> 10 dk
    ("dns_history_sync", 60 * 20),  # 5 dk -> 20 dk
]
_DEFAULT_STALE_THRESHOLD = 60 * 30


def _stale_threshold_for(job_name: str) -> int:
    for prefix, seconds in _STALE_THRESHOLDS:
        if job_name.startswith(prefix):
            return seconds
    return _DEFAULT_STALE_THRESHOLD


def _job_timestamp(doc: dict):
    return doc.get("updated_at") or doc.get("finished_at") or doc.get("synced_at")


@router.get("/status")
async def ingestion_status():
    db = get_db()
    now = datetime.now(timezone.utc)

    jobs = []
    async for raw in db.ingestion_jobs.find({}).sort("job", 1):
        doc = _clean(raw)
        ts = _job_timestamp(doc)
        age_seconds = None
        stale = True
        if ts:
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            age_seconds = (now - ts).total_seconds()
            stale = age_seconds > _stale_threshold_for(doc["job"])

        has_error = doc.get("status") in ("error", "failed")

        # Batch tek tek hata firlatmadan da tamamen basarisiz olabilir (orn.
        # DNS resolver'a hic ulasilamamasi - her IP kendi icinde yakalanip
        # "failed" sayilir, gorev genel olarak "ok" doner). Bu yuzden son
        # batch'in neredeyse tamami basarisizsa da unhealthy sayiyoruz.
        processed = doc.get("last_batch_processed") or 0
        failed = doc.get("last_batch_failed") or 0
        high_failure_rate = (failed > 0) and (processed + failed > 0) and (
            failed / (processed + failed) >= 0.9
        )

        doc["age_seconds"] = age_seconds
        doc["stale"] = stale
        doc["healthy"] = (not stale) and (not has_error) and (not high_failure_rate)
        jobs.append(doc)

    return {
        "checked_at": now,
        "healthy_count": sum(1 for j in jobs if j["healthy"]),
        "total_count": len(jobs),
        "jobs": jobs,
    }
