from datetime import datetime, timezone

from app.db.sync_client import get_sync_db
from app.ingestion.peeringdb_client import fetch_net_by_asn, fetch_org


def sync_asn_peeringdb(asn: int) -> dict | None:
    """PeeringDB'deki en guncel network/org profilini asn_peeringdb_info'ya
    yazar. PeeringDB agin kendi beyan ettigi (self-reported) bir profil
    oldugu icin resmi tescil kaydi (RDAP) gibi tarihsel diff tutulmaz,
    sadece en son bilinen durum cache'lenir.
    """
    db = get_sync_db()
    net = fetch_net_by_asn(asn)
    now = datetime.now(timezone.utc)

    if net is None:
        db.asn_peeringdb_info.update_one(
            {"asn": asn}, {"$set": {"asn": asn, "found": False, "updated_at": now}}, upsert=True
        )
        return None

    org_id = net.get("org_id")
    org = (fetch_org(org_id) if org_id else None) or {}
    doc = {
        "asn": asn,
        "found": True,
        "peeringdb_net_id": net.get("id"),
        "name": net.get("name"),
        "aka": net.get("aka"),
        "website": net.get("website"),
        "info_type": net.get("info_type"),
        "notes": net.get("notes"),
        "org_id": net.get("org_id"),
        "org_name": org.get("name"),
        "city": org.get("city"),
        "country": org.get("country"),
        "updated_at": now,
    }
    db.asn_peeringdb_info.update_one({"asn": asn}, {"$set": doc}, upsert=True)
    return doc
