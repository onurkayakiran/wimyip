from fastapi import APIRouter

from app.db.mongo import get_db

router = APIRouter()


def _clean(doc: dict) -> dict:
    doc = dict(doc)
    doc.pop("_id", None)
    return doc


@router.get("/nameservers/{nameserver}/history")
async def get_nameserver_history(nameserver: str):
    db = get_db()
    cursor = db.nameserver_ip_history.find({"nameserver": nameserver}).sort("first_seen", 1)
    history = [_clean(doc) async for doc in cursor]
    return {"nameserver": nameserver, "ip_history": history}


@router.get("/nameservers/{nameserver}/domains")
async def get_domains_by_nameserver(nameserver: str):
    db = get_db()
    cursor = db.domain_ns_history.find({"nameserver": nameserver}).sort("last_seen", -1)
    items = [_clean(doc) async for doc in cursor]
    return {"nameserver": nameserver, "total": len(items), "items": items}
