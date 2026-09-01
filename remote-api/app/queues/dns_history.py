import hashlib
import ipaddress
import uuid
from datetime import datetime, timedelta, timezone

from pymongo.errors import DuplicateKeyError

from app.config import settings

JOB_NAME = "dns_history_remote"

# Kotu niyetli/hatali bir sonucun tek bir domain icin veritabanini
# sisirmesini onlemek icin makul ust sinirlar (backend/app/ingestion/
# dns_history_sync.py::sync_domain_dns'te boyle bir sinir yok, cunku o
# gercek DNS yanitini dogrudan isliyor - burada ise sonuc disaridan/
# guvenilmeyen bir worker'dan geliyor).
_MAX_IPS = 50
_MAX_NAMESERVERS = 20
_MAX_MX = 20
_MAX_TXT = 20


# backend/app/ingestion/dns_history_batch.py::enrich_dns_history_batch'teki
# fetch_page ile ayni keyset-cursor mantigi (domain adina gore artan sirada
# sayfalama) - orada degisirse burada da senkron tutulmali.
async def claim(db, max_items: int, token_id) -> tuple[str | None, list[dict], dict | None]:
    while True:
        job = await db.ingestion_jobs.find_one({"job": JOB_NAME}) or {}
        start_cursor = job.get("cursor")
        query = {"domain": {"$gt": start_cursor}} if start_cursor else {}
        docs = await db.domains.find(query, {"domain": 1}).sort("domain", 1).limit(max_items).to_list(max_items)

        wrapped = False
        if not docs:
            wrapped = True
            docs = await db.domains.find({}, {"domain": 1}).sort("domain", 1).limit(max_items).to_list(max_items)
        if not docs:
            return None, [], None

        new_cursor = docs[-1]["domain"]
        now = datetime.now(timezone.utc)
        try:
            await db.ingestion_jobs.update_one(
                {"job": JOB_NAME, "cursor": start_cursor},
                {"$set": {"cursor": new_cursor, "updated_at": now, "wrapped_around": wrapped}},
                upsert=True,
            )
        except DuplicateKeyError:
            continue
        break

    domains = [d["domain"] for d in docs]
    batch_id = uuid.uuid4().hex
    await db.remote_batches.insert_one(
        {
            "_id": batch_id,
            "queue": "dns_history",
            "token_id": token_id,
            "items": [{"domain": d} for d in domains],
            "status": "claimed",
            "claimed_at": now,
            "lease_expires_at": now + timedelta(seconds=settings.claim_lease_seconds),
        }
    )
    return batch_id, [{"domain": d} for d in domains], None


async def apply(db, batch_id: str, token: dict, results: list[dict]) -> dict:
    batch = await db.remote_batches.find_one({"_id": batch_id})
    if not batch:
        raise ValueError("batch bulunamadi")
    if batch["status"] != "claimed":
        raise ValueError("batch zaten tamamlanmis")
    if batch["token_id"] != token["_id"]:
        raise ValueError("bu batch baska bir token'a ait")
    now = datetime.now(timezone.utc)
    lease_expires_at = batch["lease_expires_at"]
    if lease_expires_at.tzinfo is None:
        lease_expires_at = lease_expires_at.replace(tzinfo=timezone.utc)
    if lease_expires_at < now:
        raise ValueError("batch suresi dolmus")

    valid_domains = {item["domain"] for item in batch["items"]}
    label = token.get("label", "unknown")
    written = 0
    for r in results:
        domain = r.get("domain")
        if domain not in valid_domains:
            continue  # batch'te verilmemis bir domain - sessizce yoksayilir
        written += 1
        await _apply_domain_result(db, domain, r, label)

    await db.remote_batches.update_one(
        {"_id": batch_id},
        {"$set": {"status": "completed", "completed_at": now, "result_summary": {"written": written}}},
    )
    return {"written": written, "found": written}


# Yazma mantigi backend/app/ingestion/dns_history_sync.py::sync_domain_dns'den
# kopyalandi - orada degisirse burada da senkron tutulmali. Fark: buradaki
# veri disaridan/guvenilmeyen bir worker'dan geldigi icin liste uzunluklari
# yukaridaki _MAX_* sabitleriyle kirpiliyor ve gecersiz kayitlar atlaniyor.
async def _apply_domain_result(db, domain: str, result: dict, label: str) -> None:
    now = datetime.now(timezone.utc)

    await db.domains.update_one(
        {"domain": domain},
        {
            "$set": {"last_seen": now},
            "$setOnInsert": {"domain": domain, "first_seen": now},
            "$addToSet": {"sources": f"remote:{label}"},
        },
        upsert=True,
    )

    for entry in (result.get("ips") or [])[:_MAX_IPS]:
        await _apply_ip(db, domain, entry, now)

    for ns_entry in (result.get("nameservers") or [])[:_MAX_NAMESERVERS]:
        ns = ns_entry.get("host")
        if not ns or not isinstance(ns, str):
            continue
        await db.domain_ns_history.update_one(
            {"domain": domain, "nameserver": ns},
            {"$set": {"last_seen": now}, "$setOnInsert": {"domain": domain, "nameserver": ns, "first_seen": now}},
            upsert=True,
        )
        for ns_ip_entry in (ns_entry.get("ips") or [])[:_MAX_IPS]:
            await _apply_nameserver_ip(db, ns, ns_ip_entry, now)

    for mx_entry in (result.get("mx") or [])[:_MAX_MX]:
        exchange = mx_entry.get("exchange")
        if not exchange or not isinstance(exchange, str):
            continue
        priority = mx_entry.get("priority")
        await db.domain_mx_history.update_one(
            {"domain": domain, "exchange": exchange},
            {
                "$set": {"last_seen": now, "priority": priority},
                "$setOnInsert": {"domain": domain, "exchange": exchange, "first_seen": now},
            },
            upsert=True,
        )

    for value in (result.get("txt") or [])[:_MAX_TXT]:
        if not isinstance(value, str):
            continue
        value_hash = hashlib.sha256(value.encode()).hexdigest()
        await db.domain_txt_history.update_one(
            {"domain": domain, "value_hash": value_hash},
            {
                "$set": {"last_seen": now, "value": value},
                "$setOnInsert": {"domain": domain, "value_hash": value_hash, "first_seen": now},
            },
            upsert=True,
        )


async def _apply_ip(db, domain: str, entry: dict, now: datetime) -> None:
    ip = entry.get("ip")
    version = entry.get("version")
    if not ip or version not in (4, 6):
        return
    set_fields = {"last_seen": now, "ip_version": version}
    if version == 4:
        try:
            set_fields["ip_int"] = int(ipaddress.IPv4Address(ip))
        except ValueError:
            return
    await db.domain_ip_history.update_one(
        {"domain": domain, "ip": ip},
        {"$set": set_fields, "$setOnInsert": {"domain": domain, "ip": ip, "first_seen": now}},
        upsert=True,
    )


async def _apply_nameserver_ip(db, nameserver: str, entry: dict, now: datetime) -> None:
    ip = entry.get("ip")
    version = entry.get("version")
    if not ip or version not in (4, 6):
        return
    await db.nameserver_ip_history.update_one(
        {"nameserver": nameserver, "ip": ip},
        {
            "$set": {"last_seen": now, "ip_version": version},
            "$setOnInsert": {"nameserver": nameserver, "ip": ip, "first_seen": now},
        },
        upsert=True,
    )
