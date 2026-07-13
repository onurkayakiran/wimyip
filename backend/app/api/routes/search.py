from fastapi import APIRouter, Query

from app.db.mongo import get_db

router = APIRouter()


def _clean(doc: dict) -> dict:
    doc = dict(doc)
    doc.pop("_id", None)
    return doc


@router.get("/search")
async def search(q: str = Query(..., min_length=2), limit: int = Query(20, le=100)):
    """Organizasyon adi veya domain adina gore serbest metin arama (IP/CIDR/ASN
    icin frontend zaten dogrudan ilgili detay sayfasina yonlendiriyor).
    """
    db = get_db()
    regex = {"$regex": q, "$options": "i"}

    asn_matches: dict[int, str | None] = {}
    async for doc in db.asn_org_history.find({"org_name": regex}).limit(limit):
        asn_matches[doc["asn"]] = doc.get("org_name")
    async for doc in db.asn_peeringdb_info.find(
        {"$or": [{"org_name": regex}, {"name": regex}]}
    ).limit(limit):
        asn_matches.setdefault(doc["asn"], doc.get("org_name") or doc.get("name"))

    domain_matches = [_clean(d) async for d in db.domains.find({"domain": regex}).limit(limit)]

    return {
        "query": q,
        "asns": [{"asn": asn, "org_name": name} for asn, name in list(asn_matches.items())[:limit]],
        "domains": domain_matches,
    }
