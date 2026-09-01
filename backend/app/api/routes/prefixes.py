import ipaddress

from fastapi import APIRouter, HTTPException, Query
from fastapi.concurrency import run_in_threadpool

from app.db.mongo import get_db

router = APIRouter()


def _clean(doc: dict) -> dict:
    doc = dict(doc)
    doc.pop("_id", None)
    return doc


async def _containing_prefix(db, cidr: str) -> dict | None:
    """BGP'de gorulen daha spesifik bir prefix (orn. /24), RIR'in tahsis
    ettigi daha genis blokta (orn. /16) tam string olarak eslesmeyebilir.
    Boyle durumlarda, sorgulanan araligi iceren en dar RIR blogunu bulur.
    """
    try:
        network = ipaddress.ip_network(cidr, strict=False)
    except ValueError:
        return None
    if network.version != 4:
        return None

    start_ip = int(network.network_address)
    matches = [
        d
        async for d in db.prefixes.find(
            {"version": 4, "start_ip": {"$lte": start_ip}, "end_ip": {"$gte": start_ip}}
        )
    ]
    if not matches:
        return None
    matches.sort(key=lambda d: d["end_ip"] - d["start_ip"])
    return matches[0]


@router.get("/prefixes")
async def list_prefixes(
    q: str | None = None,
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
    if q:
        q = q.strip()
        try:
            ip_obj = ipaddress.ip_address(q)
        except ValueError:
            ip_obj = None
        if ip_obj is not None:
            # Girilen deger bir IP - onu ICEREN prefix'i ara (_containing_prefix
            # ile ayni v4-only kapsam).
            query["version"] = ip_obj.version
            query["start_ip"] = {"$lte": int(ip_obj)}
            query["end_ip"] = {"$gte": int(ip_obj)}
        else:
            # domains.py'deki `q` deseniyle ayni: buyuk/kucuk harf duyarsiz alt-dize
            query["cidr"] = {"$regex": q, "$options": "i"}

    # start_ip index'li oldugu icin bedava - skip/limit'in kararli bir
    # sirasi olmasi icin (once bu endpoint'te hic sort yoktu).
    cursor = db.prefixes.find(query).sort("start_ip", 1).skip(offset).limit(limit)
    items = [_clean(doc) async for doc in cursor]
    total = await db.prefixes.count_documents(query)
    return {"total": total, "items": items}


# NOT: {cidr:path} yakalayici oldugu icin asagidaki /history ve /refresh
# rotalari, genel /prefixes/{cidr:path} rotasindan ONCE tanimlanmalidir;
# aksi halde greedy path converter onlari da yutar.


@router.get("/prefixes/{cidr:path}/history")
async def get_prefix_history(cidr: str):
    db = get_db()
    cursor = db.prefix_org_history.find({"cidr": cidr}).sort("first_seen", 1)
    history = [_clean(doc) async for doc in cursor]
    latest_snapshot = await db.whois_snapshots.find_one(
        {"object_type": "prefix", "object_key": cidr}, sort=[("fetched_at", -1)]
    )
    return {
        "cidr": cidr,
        "history": history,
        "latest_snapshot_at": latest_snapshot["fetched_at"] if latest_snapshot else None,
    }


@router.post("/prefixes/{cidr:path}/refresh")
async def refresh_prefix_whois(cidr: str):
    db = get_db()
    doc = await db.prefixes.find_one({"cidr": cidr}) or await _containing_prefix(db, cidr)
    if not doc:
        raise HTTPException(status_code=404, detail="Prefix bulunamadı")

    from app.ingestion.rdap_sync import sync_prefix_rdap

    # RDAP sorgusu, sorgulanan CIDR'in kendisiyle yapilir (daha spesifik bir
    # alt-tahsis olabilir); RIR yonlendirmesi icin sadece "rir" alani genis
    # RIR blogundan alinir.
    info = await run_in_threadpool(sync_prefix_rdap, cidr, doc["rir"])
    if info is None:
        raise HTTPException(status_code=502, detail="RDAP sorgusu başarısız oldu")
    return info


@router.get("/prefixes/{cidr:path}")
async def get_prefix(cidr: str):
    db = get_db()
    doc = await db.prefixes.find_one({"cidr": cidr})
    if doc:
        return {**_clean(doc), "queried_cidr": cidr, "exact_match": True}

    doc = await _containing_prefix(db, cidr)
    if not doc:
        raise HTTPException(status_code=404, detail="Prefix bulunamadı")
    return {**_clean(doc), "queried_cidr": cidr, "exact_match": False}
