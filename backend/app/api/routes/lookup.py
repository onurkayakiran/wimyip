import ipaddress

from fastapi import APIRouter, HTTPException
from fastapi.concurrency import run_in_threadpool

from app.db.mongo import get_db

router = APIRouter()


def _clean(doc: dict) -> dict:
    doc = dict(doc)
    doc.pop("_id", None)
    return doc


@router.get("/lookup/ip/{ip}")
async def lookup_ip(ip: str):
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        raise HTTPException(status_code=400, detail="Geçersiz IP adresi")

    if addr.version != 4:
        raise HTTPException(status_code=400, detail="Şu an sadece IPv4 destekleniyor")

    ip_int = int(addr)
    db = get_db()
    cursor = db.prefixes.find(
        {"version": 4, "start_ip": {"$lte": ip_int}, "end_ip": {"$gte": ip_int}}
    )
    matches = [_clean(doc) async for doc in cursor]
    if not matches:
        raise HTTPException(status_code=404, detail="Eşleşen prefix bulunamadı")

    # en spesifik (en dar) prefiksi öne al
    matches.sort(key=lambda d: d["end_ip"] - d["start_ip"])

    bgp_cursor = db.prefix_asn_history.find(
        {"start_ip": {"$lte": ip_int}, "end_ip": {"$gte": ip_int}}
    ).sort("last_seen", -1)
    bgp_matches = [_clean(doc) async for doc in bgp_cursor]

    ptr_cursor = db.ptr_records.find({"ip": ip}).sort("first_seen", 1)
    ptr_matches = [_clean(doc) async for doc in ptr_cursor]

    # bu IP bir nameserver'in kendi adresiyse, hangi domainlere hizmet
    # verdigini de goster
    ns_hostnames = [
        d["nameserver"] async for d in db.nameserver_ip_history.find({"ip": ip}, {"nameserver": 1})
    ]
    nameserver_domains = []
    if ns_hostnames:
        served_cursor = db.domain_ns_history.find({"nameserver": {"$in": ns_hostnames}})
        nameserver_domains = [_clean(d) async for d in served_cursor]

    return {
        "ip": ip,
        "prefix": matches[0],
        "all_matches": matches,
        "bgp": bgp_matches,
        "ptr": ptr_matches,
        "nameserver_domains": nameserver_domains,
    }


@router.post("/lookup/ip/{ip}/refresh-bgp")
async def refresh_ip_bgp(ip: str):
    try:
        ipaddress.ip_address(ip)
    except ValueError:
        raise HTTPException(status_code=400, detail="Geçersiz IP adresi")

    from app.ingestion.bgp_sync import sync_ip_bgp

    return await run_in_threadpool(sync_ip_bgp, ip)
