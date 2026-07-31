from fastapi import APIRouter, HTTPException, Query
from fastapi.concurrency import run_in_threadpool

from app.db.mongo import get_db

router = APIRouter()


def _clean(doc: dict) -> dict:
    doc = dict(doc)
    doc.pop("_id", None)
    return doc


@router.get("/asns")
async def list_asns(
    rir: str | None = None,
    country: str | None = None,
    limit: int = Query(50, le=500),
    offset: int = 0,
):
    db = get_db()
    query: dict = {}
    if rir:
        query["rir"] = rir
    if country:
        query["country"] = country

    cursor = db.asns.find(query).skip(offset).limit(limit)
    items = [_clean(doc) async for doc in cursor]
    total = await db.asns.count_documents(query)
    return {"total": total, "items": items}


@router.get("/asns/{asn}")
async def get_asn(asn: int):
    db = get_db()
    doc = await db.asns.find_one({"asn": asn})
    if not doc:
        raise HTTPException(status_code=404, detail="ASN bulunamadı")
    return _clean(doc)


@router.get("/asns/{asn}/history")
async def get_asn_history(asn: int):
    db = get_db()
    cursor = db.asn_org_history.find({"asn": asn}).sort("first_seen", 1)
    history = [_clean(doc) async for doc in cursor]
    latest_snapshot = await db.whois_snapshots.find_one(
        {"object_type": "asn", "object_key": str(asn)}, sort=[("fetched_at", -1)]
    )
    return {
        "asn": asn,
        "history": history,
        "latest_snapshot_at": latest_snapshot["fetched_at"] if latest_snapshot else None,
    }


@router.post("/asns/{asn}/refresh")
async def refresh_asn_whois(asn: int):
    db = get_db()
    doc = await db.asns.find_one({"asn": asn})
    if not doc:
        raise HTTPException(status_code=404, detail="ASN bulunamadı")

    from app.ingestion.rdap_sync import sync_asn_rdap

    info = await run_in_threadpool(sync_asn_rdap, asn, doc["rir"])
    if info is None:
        raise HTTPException(status_code=502, detail="RDAP sorgusu başarısız oldu")
    return info


@router.get("/asns/{asn}/prefixes")
async def get_asn_prefixes(asn: int, limit: int = Query(100, le=1000), offset: int = 0):
    db = get_db()
    query = {"asn": asn}
    cursor = db.prefix_asn_history.find(query).sort("last_seen", -1).skip(offset).limit(limit)
    items = [_clean(doc) async for doc in cursor]
    total = await db.prefix_asn_history.count_documents(query)
    return {"asn": asn, "total": total, "items": items}


@router.post("/asns/{asn}/refresh-bgp")
async def refresh_asn_bgp(asn: int):
    db = get_db()
    doc = await db.asns.find_one({"asn": asn})
    if not doc:
        raise HTTPException(status_code=404, detail="ASN bulunamadı")

    from app.ingestion.bgp_sync import sync_asn_announcements, sync_asn_peering

    announcements = await run_in_threadpool(sync_asn_announcements, asn)
    peering = await run_in_threadpool(sync_asn_peering, asn)
    return {**announcements, "peering": peering}


@router.get("/asns/{asn}/peers")
async def get_asn_peers(asn: int, limit: int = Query(200, le=1000), offset: int = 0):
    db = get_db()
    query = {"asn": asn}
    cursor = db.asn_peering_history.find(query).sort("power", -1).skip(offset).limit(limit)
    items = [_clean(doc) async for doc in cursor]
    total = await db.asn_peering_history.count_documents(query)
    return {"asn": asn, "total": total, "items": items}


@router.get("/asns/{asn}/peeringdb")
async def get_asn_peeringdb(asn: int):
    db = get_db()
    doc = await db.asn_peeringdb_info.find_one({"asn": asn})
    if not doc:
        raise HTTPException(status_code=404, detail="PeeringDB bilgisi henüz toplanmadı")
    return _clean(doc)


@router.post("/asns/{asn}/refresh-peeringdb")
async def refresh_asn_peeringdb(asn: int):
    db = get_db()
    doc = await db.asns.find_one({"asn": asn})
    if not doc:
        raise HTTPException(status_code=404, detail="ASN bulunamadı")

    from app.ingestion.peeringdb_sync import sync_asn_peeringdb

    result = await run_in_threadpool(sync_asn_peeringdb, asn)
    if result is None:
        return {"asn": asn, "found": False}
    return result
