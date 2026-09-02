from fastapi import APIRouter
from fastapi.responses import Response

from app.core.seo_render import SITE_ORIGIN
from app.db.mongo import get_db

# ASN sayisi (domains'in 16M+'inin aksine) makul olcekte, ve /asn/{asn}
# sayfalari zaten bot'lara tam render ediliyor (bkz. seo.py) - bu yuzden
# ASN'ler icin canli, veritabanindan uretilen bir sitemap ekleniyor.
# Sitemap protokolu dosya basina 50.000 URL siniri koyuyor; ASN sayisi
# bunu asarsa otomatik olarak bir sitemap-index + parcalara bolunuyor.

router = APIRouter()

SHARD_SIZE = 50_000
_XML_HEADER = '<?xml version="1.0" encoding="UTF-8"?>\n'


def _urlset(locs: list[str]) -> str:
    urls = "".join(f"<url><loc>{loc}</loc></url>" for loc in locs)
    return f'{_XML_HEADER}<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>'


def _sitemapindex(locs: list[str]) -> str:
    entries = "".join(f"<sitemap><loc>{loc}</loc></sitemap>" for loc in locs)
    return f'{_XML_HEADER}<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{entries}</sitemapindex>'


@router.get("/sitemap-asns.xml")
async def sitemap_asns():
    db = get_db()
    total = await db.asns.count_documents({})

    if total <= SHARD_SIZE:
        cursor = db.asns.find({}, {"asn": 1}).sort("asn", 1)
        locs = [f"{SITE_ORIGIN}/asn/{doc['asn']}" async for doc in cursor]
        return Response(_urlset(locs), media_type="application/xml")

    shard_count = -(-total // SHARD_SIZE)  # ceil division
    locs = [f"{SITE_ORIGIN}/sitemap-asns-{n}.xml" for n in range(1, shard_count + 1)]
    return Response(_sitemapindex(locs), media_type="application/xml")


@router.get("/sitemap-asns-{n}.xml")
async def sitemap_asns_shard(n: int):
    db = get_db()
    cursor = (
        db.asns.find({}, {"asn": 1})
        .sort("asn", 1)
        .skip((n - 1) * SHARD_SIZE)
        .limit(SHARD_SIZE)
    )
    locs = [f"{SITE_ORIGIN}/asn/{doc['asn']}" async for doc in cursor]
    return Response(_urlset(locs), media_type="application/xml")
