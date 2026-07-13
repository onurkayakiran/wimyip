import logging
from datetime import datetime, timezone

from pymongo.database import Database

from app.db.sync_client import get_sync_db
from app.ingestion.rdap_client import extract_org, fetch_asn_rdap, fetch_prefix_rdap

logger = logging.getLogger(__name__)


def _snapshot_and_diff(
    db: Database,
    object_type: str,
    object_key,
    rir: str,
    raw_rdap: dict,
    history_collection,
    history_key_field: str,
) -> dict:
    now = datetime.now(timezone.utc)
    info = extract_org(raw_rdap)

    db.whois_snapshots.insert_one(
        {
            "object_type": object_type,
            "object_key": str(object_key),
            "rir": rir,
            "raw_rdap": raw_rdap,
            "fetched_at": now,
        }
    )

    latest = history_collection.find_one(
        {history_key_field: object_key}, sort=[("last_seen", -1)]
    )

    unchanged = (
        latest is not None
        and latest.get("org_name") == info["org_name"]
        and latest.get("org_handle") == info["org_handle"]
    )

    if unchanged:
        history_collection.update_one({"_id": latest["_id"]}, {"$set": {"last_seen": now}})
    else:
        history_collection.insert_one(
            {
                history_key_field: object_key,
                "org_name": info["org_name"],
                "org_handle": info["org_handle"],
                "network_name": info["network_name"],
                "handle": info["handle"],
                "first_seen": now,
                "last_seen": now,
            }
        )

    return {**info, "object_key": object_key, "rir": rir, "fetched_at": now.isoformat()}


def sync_asn_rdap(asn: int, rir: str) -> dict | None:
    db = get_sync_db()
    raw = fetch_asn_rdap(rir, asn)
    if raw is None:
        return None
    return _snapshot_and_diff(db, "asn", asn, rir, raw, db.asn_org_history, "asn")


def sync_prefix_rdap(cidr: str, rir: str) -> dict | None:
    db = get_sync_db()
    raw = fetch_prefix_rdap(rir, cidr)
    if raw is None:
        return None
    return _snapshot_and_diff(db, "prefix", cidr, rir, raw, db.prefix_org_history, "cidr")
