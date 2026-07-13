import ipaddress
from datetime import datetime, timezone

from app.db.sync_client import get_sync_db
from app.ingestion.dns_client import ptr_lookup


def sync_ptr(ip_int: int) -> str | None:
    """Tek bir IP icin PTR sorgusu yapar; sonucu ptr_records'a (ip+hostname
    ciftine gore gecmisli, first_seen/last_seen ile) ve kesfedilen hostname'i
    domains koleksiyonuna isler.
    """
    db = get_sync_db()
    ip = str(ipaddress.IPv4Address(ip_int))
    hostname = ptr_lookup(ip)
    if hostname is None:
        return None

    now = datetime.now(timezone.utc)

    db.ptr_records.update_one(
        {"ip": ip, "ptr_hostname": hostname},
        {
            "$set": {"last_seen": now},
            "$setOnInsert": {"ip": ip, "ptr_hostname": hostname, "first_seen": now},
        },
        upsert=True,
    )

    db.domains.update_one(
        {"domain": hostname},
        {
            "$set": {"last_seen": now},
            "$setOnInsert": {"domain": hostname, "first_seen": now},
            "$addToSet": {"sources": "ptr"},
        },
        upsert=True,
    )

    return hostname
