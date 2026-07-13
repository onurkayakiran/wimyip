import ipaddress
import logging
from datetime import datetime, timezone

from app.db.sync_client import get_sync_db
from app.ingestion.ripestat_client import fetch_announced_prefixes, fetch_prefix_overview

logger = logging.getLogger(__name__)


def _parse_ts(raw: str) -> datetime:
    dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _cidr_bounds(cidr: str) -> tuple[int, int] | None:
    try:
        net = ipaddress.ip_network(cidr, strict=False)
    except ValueError:
        return None
    if net.version != 4:
        return None
    return int(net.network_address), int(net.broadcast_address)


def sync_asn_announcements(asn: int) -> dict:
    """RIPEstat'tan bir ASN'in gecmiste+su an duyurdugu prefixleri ceker ve
    prefix_asn_history koleksiyonuna isler. Ayni (prefix, asn) ciftinde
    zaman araligi genisletilir (first_seen kucultulur, last_seen buyutulur);
    boylece BGP duyuru gecmisi zaman icinde birikir.
    """
    db = get_sync_db()
    payload = fetch_announced_prefixes(asn)
    if payload is None:
        return {"asn": asn, "prefixes": 0, "error": "fetch_failed"}

    data = payload.get("data") or {}
    query_endtime = (
        _parse_ts(data["query_endtime"])
        if data.get("query_endtime")
        else datetime.now(timezone.utc)
    )

    written = 0
    for entry in data.get("prefixes", []) or []:
        prefix = entry.get("prefix")
        timelines = entry.get("timelines") or []
        if not prefix or not timelines:
            continue

        bounds = _cidr_bounds(prefix)
        if bounds is None:
            continue
        start_ip, end_ip = bounds

        first_start = min(_parse_ts(t["starttime"]) for t in timelines)
        last_end = max(_parse_ts(t["endtime"]) for t in timelines)
        active = (query_endtime - last_end).total_seconds() < 86400

        db.prefix_asn_history.update_one(
            {"prefix": prefix, "asn": asn},
            {
                "$set": {
                    "start_ip": start_ip,
                    "end_ip": end_ip,
                    "last_seen": last_end,
                    "active": active,
                },
                "$min": {"first_seen": first_start},
            },
            upsert=True,
        )
        written += 1

    return {"asn": asn, "prefixes": written}


def sync_ip_bgp(resource: str) -> dict:
    """Bir IP/prefix icin RIPEstat'tan CANLI olarak "su an bunu hangi ASN(lar)
    duyuruyor" bilgisini ceker, bulunan her ASN icin tam gecmis+guncel
    duyuru taramasini (sync_asn_announcements) tetikler. IP sayfasindaki
    "BGP'yi Simdi Topla" butonu bunu kullanir - boylece o IP icin henuz hic
    BGP verisi toplanmamis olsa bile (hangi ASN sorulacagi bilinmedigi icin
    normalde beklenmesi gerekirdi) anlik olarak veri cekilebilir.
    """
    payload = fetch_prefix_overview(resource)
    if payload is None:
        return {"resource": resource, "asns": [], "error": "fetch_failed"}

    data = payload.get("data") or {}
    asns = sorted({a["asn"] for a in (data.get("asns") or []) if "asn" in a})

    results = [sync_asn_announcements(asn) for asn in asns]
    return {"resource": resource, "asns": asns, "results": results}
