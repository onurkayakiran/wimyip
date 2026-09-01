import ipaddress
import uuid
from datetime import datetime, timedelta, timezone

from pymongo.errors import DuplicateKeyError

from app.config import settings

JOB_NAME = "ptr_sweep_remote"


# backend/app/ingestion/ptr_batch.py::_next_target_ip'den kopyalandi - orada
# degisirse burada da senkron tutulmali.
async def _next_target_ip(db, after_ip: int) -> int | None:
    candidate = after_ip + 1

    inside = await db.prefixes.find_one(
        {"version": 4, "start_ip": {"$lte": candidate}, "end_ip": {"$gte": candidate}},
        {"_id": 1},
    )
    if inside:
        return candidate

    nxt = await db.prefixes.find_one(
        {"version": 4, "start_ip": {"$gt": candidate}},
        sort=[("start_ip", 1)],
        projection={"start_ip": 1},
    )
    return nxt["start_ip"] if nxt else None


async def claim(db, max_items: int, token_id) -> tuple[str | None, list[dict], dict | None]:
    """Bir sonraki N tahsisli IPv4 adresini claim eder. `ingestion_jobs`
    cursor'u, "job" alanindaki tekil index sayesinde compare-and-swap ile
    ilerletilir: filtre cursor'u eslesmezse upsert bir INSERT denemesine
    donusur, bu da tekil index'e carpip DuplicateKeyError firlatir - bu,
    baska bir istegin cursor'u once ilerlettiginin (CAS kaybedildiginin)
    guvenli bir sinyalidir, tekrar denenir.
    """
    while True:
        job = await db.ingestion_jobs.find_one({"job": JOB_NAME}) or {}
        start_cursor = job.get("cursor", -1)
        current = start_cursor
        ips: list[int] = []
        wrapped = False
        for _ in range(max_items):
            nxt = await _next_target_ip(db, current)
            if nxt is None:
                wrapped, current = True, -1
                nxt = await _next_target_ip(db, current)
                if nxt is None:
                    break
            ips.append(nxt)
            current = nxt
        if not ips:
            return None, [], None

        now = datetime.now(timezone.utc)
        try:
            await db.ingestion_jobs.update_one(
                {"job": JOB_NAME, "cursor": start_cursor},
                {"$set": {"cursor": current, "updated_at": now, "wrapped_around": wrapped}},
                upsert=True,
            )
        except DuplicateKeyError:
            continue
        break

    batch_id = uuid.uuid4().hex
    items = [{"ip_int": i, "ip": str(ipaddress.IPv4Address(i))} for i in ips]
    await db.remote_batches.insert_one(
        {
            "_id": batch_id,
            "queue": "ptr_sweep",
            "token_id": token_id,
            "items": items,
            "status": "claimed",
            "claimed_at": now,
            "lease_expires_at": now + timedelta(seconds=settings.claim_lease_seconds),
        }
    )
    return batch_id, [{"ip": it["ip"]} for it in items], None


async def apply(db, batch_id: str, token: dict, results: list[dict]) -> dict:
    batch = await db.remote_batches.find_one({"_id": batch_id})
    if not batch:
        raise ValueError("batch bulunamadi")
    if batch["status"] != "claimed":
        raise ValueError("batch zaten tamamlanmis")
    if batch["token_id"] != token["_id"]:
        raise ValueError("bu batch baska bir token'a ait")
    now = datetime.now(timezone.utc)
    # Motor/PyMongo BSON datetime'lari naive (tzinfo=None, UTC varsayilarak)
    # geri donduruyor - aware `now` ile dogrudan karsilastirmak TypeError
    # firlatir (ayni sorun stats.py'de de yasanmisti, ayni sekilde duzeltildi).
    lease_expires_at = batch["lease_expires_at"]
    if lease_expires_at.tzinfo is None:
        lease_expires_at = lease_expires_at.replace(tzinfo=timezone.utc)
    if lease_expires_at < now:
        raise ValueError("batch suresi dolmus")

    valid_ips = {item["ip"] for item in batch["items"]}
    label = token.get("label", "unknown")
    found = written = 0
    for r in results:
        ip = r.get("ip")
        if ip not in valid_ips:
            continue  # batch'te verilmemis bir IP - sessizce yoksayilir
        written += 1
        hostname = r.get("ptr_hostname")
        if hostname:
            await _apply_ptr_result(db, ip, hostname, label)
            found += 1

    await db.remote_batches.update_one(
        {"_id": batch_id},
        {
            "$set": {
                "status": "completed",
                "completed_at": now,
                "result_summary": {"written": written, "found": found},
            }
        },
    )
    return {"written": written, "found": found}


# Yazma mantigi backend/app/ingestion/ptr_sync.py::sync_ptr'den kopyalandi -
# orada degisirse burada da senkron tutulmali.
async def _apply_ptr_result(db, ip: str, hostname: str, label: str) -> None:
    now = datetime.now(timezone.utc)
    await db.ptr_records.update_one(
        {"ip": ip, "ptr_hostname": hostname},
        {
            "$set": {"last_seen": now},
            "$setOnInsert": {"ip": ip, "ptr_hostname": hostname, "first_seen": now},
        },
        upsert=True,
    )
    await db.domains.update_one(
        {"domain": hostname},
        {
            "$set": {"last_seen": now},
            "$setOnInsert": {"domain": hostname, "first_seen": now},
            "$addToSet": {"sources": {"$each": ["ptr", f"remote:{label}"]}},
        },
        upsert=True,
    )
