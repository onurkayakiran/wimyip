import uuid
from datetime import datetime, timedelta, timezone

import tldextract
from pymongo.errors import DuplicateKeyError

from app.config import settings
from app.queues.dns_history import apply  # noqa: F401 - yazma mantigi ayni, tekrar yazilmiyor

JOB_NAME = "dns_history_apex_remote"

# Ag istegi atmaz - sadece paketle gelen sabit Public Suffix List kullanilir
# (backend/app/ingestion/domain_apex_batch.py'deki ile ayni gerekce).
_extract = tldextract.TLDExtract(suffix_list_urls=())

_PAGE_SIZE = 500
# Bir claim() cagrisinda en fazla max_items * bu kat kadar ham domain taranir -
# subdomain'in cok yogun oldugu bolgelerde (orn. wildcard sertifikadan gelen
# binlerce alt-domain) claim() suresiz uzamasin diye bir ust sinir.
_SCAN_MULTIPLIER = 50


# backend/app/ingestion/domain_apex_batch.py::_is_apex_domain'den kopyalandi -
# orada degisirse burada da senkron tutulmali.
def _is_apex_domain(domain: str) -> bool:
    ext = _extract(domain)
    if not ext.domain or not ext.suffix:
        return False
    return domain == f"{ext.domain}.{ext.suffix}"


async def claim(db, max_items: int, token_id) -> tuple[str | None, list[dict], dict | None]:
    while True:
        job = await db.ingestion_jobs.find_one({"job": JOB_NAME}) or {}
        start_cursor = job.get("cursor")
        cursor = start_cursor
        apex_domains: list[str] = []
        scanned = 0
        scan_limit = max_items * _SCAN_MULTIPLIER
        wrapped = False

        while len(apex_domains) < max_items and scanned < scan_limit:
            query = {"domain": {"$gt": cursor}} if cursor else {}
            page = await db.domains.find(query, {"domain": 1}).sort("domain", 1).limit(_PAGE_SIZE).to_list(_PAGE_SIZE)
            if not page:
                if wrapped:
                    break  # tam bir tur attik, koleksiyonda baska apex domain yok
                wrapped = True
                cursor = None
                continue
            for doc in page:
                cursor = doc["domain"]
                scanned += 1
                if _is_apex_domain(doc["domain"]):
                    apex_domains.append(doc["domain"])
                if len(apex_domains) >= max_items:
                    break

        if scanned == 0:
            return None, [], None  # koleksiyon tamamen bos, kaydedecek ilerleme yok

        # Cursor'u HER durumda ilerletiyoruz - scan_limit'e takilip hic apex
        # domain bulunamasa bile (yogun subdomain bolgesi, orn. wildcard
        # sertifikadan gelen binlerce alt-domain). Aksi halde bir sonraki
        # claim() ayni bolgeyi bastan tarar ve o blok asla asilamaz.
        now = datetime.now(timezone.utc)
        try:
            await db.ingestion_jobs.update_one(
                {"job": JOB_NAME, "cursor": start_cursor},
                {"$set": {"cursor": cursor, "updated_at": now, "wrapped_around": wrapped}},
                upsert=True,
            )
        except DuplicateKeyError:
            continue
        break

    if not apex_domains:
        return None, [], None

    batch_id = uuid.uuid4().hex
    await db.remote_batches.insert_one(
        {
            "_id": batch_id,
            "queue": "dns_history_apex",
            "token_id": token_id,
            "items": [{"domain": d} for d in apex_domains],
            "status": "claimed",
            "claimed_at": now,
            "lease_expires_at": now + timedelta(seconds=settings.claim_lease_seconds),
        }
    )
    return batch_id, [{"domain": d} for d in apex_domains], None
