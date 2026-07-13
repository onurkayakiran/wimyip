from fastapi import APIRouter, HTTPException, Query
from fastapi.concurrency import run_in_threadpool

from app.db.mongo import get_db

router = APIRouter()


def _clean(doc: dict) -> dict:
    doc = dict(doc)
    doc.pop("_id", None)
    return doc


@router.get("/domains")
async def list_domains(
    q: str | None = None,
    source: str | None = None,
    limit: int = Query(50, le=500),
    offset: int = 0,
):
    db = get_db()
    query: dict = {}
    if q:
        query["domain"] = {"$regex": q, "$options": "i"}
    if source:
        query["sources"] = source

    cursor = db.domains.find(query).sort("last_seen", -1).skip(offset).limit(limit)
    items = [_clean(doc) async for doc in cursor]
    total = await db.domains.count_documents(query)
    return {"total": total, "items": items}


@router.get("/domains/{domain}")
async def get_domain(domain: str):
    db = get_db()
    doc = await db.domains.find_one({"domain": domain})
    if not doc:
        raise HTTPException(status_code=404, detail="Domain bulunamadı")

    ptr_cursor = db.ptr_records.find({"ptr_hostname": domain}).sort("first_seen", 1)
    ptr_hits = [_clean(d) async for d in ptr_cursor]

    return {**_clean(doc), "ptr_records": ptr_hits}


@router.get("/domains/{domain}/history")
async def get_domain_dns_history(domain: str):
    db = get_db()

    ip_cursor = db.domain_ip_history.find({"domain": domain}).sort("first_seen", 1)
    ip_history = [_clean(d) async for d in ip_cursor]

    ns_cursor = db.domain_ns_history.find({"domain": domain}).sort("first_seen", 1)
    ns_history = [_clean(d) async for d in ns_cursor]

    return {"domain": domain, "ip_history": ip_history, "ns_history": ns_history}


@router.post("/domains/{domain}/refresh-dns")
async def refresh_domain_dns(domain: str):
    from app.ingestion.dns_history_sync import sync_domain_dns

    return await run_in_threadpool(sync_domain_dns, domain)
