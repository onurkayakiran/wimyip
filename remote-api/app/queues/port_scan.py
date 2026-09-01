import ipaddress
import uuid
from datetime import datetime, timedelta, timezone

from app.config import settings

# port_scan is-tabanli bir kuyruk (surekli tarama degil) - cok daha uzun bir
# lease'e ihtiyaci var, cunku tam bir subnet SYN taramasi saatler surebilir.
# routes/claim.py bunu settings.claim_lease_seconds yerine kullanir (bkz.
# getattr(handler, "LEASE_SECONDS", ...)).
LEASE_SECONDS = settings.port_scan_lease_seconds


def _expand_target(target: str) -> list[str]:
    network = ipaddress.ip_network(target, strict=False)
    return [str(ip) for ip in network.hosts()]


async def claim(db, max_items: int, token_id) -> tuple[str | None, list[dict], dict | None]:
    """`max_items` yoksayilir: bir job'un TUM host'lari tek batch'te verilir
    (chunking, IP'ler arasi gecikme/pacing'i parcalar ve sonuclarin tek bir
    tutarli job'a baglanmasini zorlastirirdi). Bekleyen (pending) VEYA
    lease'i dolmus terk edilmis (claimed ama worker cokmus) bir job'u tek
    atomik find_one_and_update ile claim eder - paylasilan bir cursor
    uzerinde yaris olmadigi icin ptr_sweep/dns_history'deki CAS-retry
    donguye gerek yok.
    """
    now = datetime.now(timezone.utc)
    job = await db.port_scan_jobs.find_one_and_update(
        {
            "$or": [
                {"status": "pending"},
                {"status": {"$in": ["claimed", "running"]}, "lease_expires_at": {"$lt": now}},
            ]
        },
        {
            "$set": {
                "status": "claimed",
                "claimed_at": now,
                "claimed_by_token_id": token_id,
                "lease_expires_at": now + timedelta(seconds=LEASE_SECONDS),
            }
        },
        sort=[("created_at", 1)],
    )
    if not job:
        return None, [], None

    try:
        ips = _expand_target(job["target"])
    except ValueError:
        await db.port_scan_jobs.update_one(
            {"_id": job["_id"]}, {"$set": {"status": "failed", "error": "gecersiz target"}}
        )
        return None, [], None

    batch_id = uuid.uuid4().hex
    items = [{"ip": ip} for ip in ips]
    await db.remote_batches.insert_one(
        {
            "_id": batch_id,
            "queue": "port_scan",
            "token_id": token_id,
            "job_id": job["_id"],
            "host_count": len(items),
            "items": items,
            "status": "claimed",
            "claimed_at": now,
            "lease_expires_at": now + timedelta(seconds=LEASE_SECONDS),
        }
    )
    meta = dict(job.get("meta") or {})
    meta["job_id"] = str(job["_id"])
    return batch_id, items, meta


async def apply(db, batch_id: str, token: dict, results: list[dict]) -> dict:
    """Artimli calisir: worker her IP'yi bitirdiginde `results` genelde TEK
    elemanli bir liste olarak gonderir (bkz. remote-worker/worker.py'deki
    INCREMENTAL_QUEUES), bu yuzden burasi batch'in tamamlanmasini beklemeden
    her cagrida ilerlemeyi (scanned_count/current_ip) gunceller.
    """
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

    job_id = batch["job_id"]
    valid_ips = {item["ip"] for item in batch["items"]}
    written = found = 0
    last_ip = None
    for r in results:
        ip = r.get("ip")
        if ip not in valid_ips:
            continue  # batch'te verilmemis bir IP - sessizce yoksayilir
        written += 1
        last_ip = ip
        open_ports = r.get("open_ports") or []
        if open_ports:
            found += 1
        await db.port_scan_results.update_one(
            {"job_id": job_id, "ip": ip},
            {
                "$set": {
                    "job_id": job_id,
                    "ip": ip,
                    "ip_int": int(ipaddress.IPv4Address(ip)),
                    "open_ports": open_ports,
                    "services": r.get("services") or [],
                    "total_scanned": r.get("total_scanned"),
                    "scanned_at": now,
                }
            },
            upsert=True,
        )

    # Ayri bir $inc sayaci yerine bilerek yeniden-sayim: worker bir sonucu
    # ag hatasi yuzunden tekrar gonderirse (job_id,ip) upsert zaten
    # idempotent, sayac boylece asla yanlislikla sismez.
    scanned_count = await db.port_scan_results.count_documents({"job_id": job_id})
    job = await db.port_scan_jobs.find_one({"_id": job_id}, {"host_count": 1, "status": 1})
    job_update: dict = {"scanned_count": scanned_count, "last_progress_at": now}
    if last_ip:
        job_update["current_ip"] = last_ip

    if job and scanned_count >= job["host_count"]:
        found_total = await db.port_scan_results.count_documents(
            {"job_id": job_id, "open_ports": {"$ne": []}}
        )
        job_update["status"] = "completed"
        job_update["completed_at"] = now
        job_update["result_summary"] = {
            "scanned_hosts": scanned_count,
            "hosts_with_open_ports": found_total,
        }
        await db.remote_batches.update_one(
            {"_id": batch_id},
            {"$set": {"status": "completed", "completed_at": now, "result_summary": {"written": written, "found": found}}},
        )
    elif job and job["status"] == "claimed":
        job_update["status"] = "running"

    await db.port_scan_jobs.update_one({"_id": job_id}, {"$set": job_update})
    return {"written": written, "found": found}
