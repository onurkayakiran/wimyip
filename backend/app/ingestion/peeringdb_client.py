import requests

PEERINGDB_BASE = "https://www.peeringdb.com/api"


def fetch_net_by_asn(asn: int) -> dict | None:
    """PeeringDB'de bir ASN'e ait network kaydini dondurur. Auth gerekmez,
    herkese acik salt-okunur API.
    """
    resp = requests.get(
        f"{PEERINGDB_BASE}/net",
        params={"asn": asn},
        headers={"Accept": "application/json"},
        timeout=30,
    )
    if resp.status_code != 200:
        return None
    data = (resp.json() or {}).get("data") or []
    return data[0] if data else None


def fetch_org(org_id: int) -> dict | None:
    """PeeringDB net kaydindaki org_id referansi uzerinden organizasyon
    detayini (adres, sehir, ulke) ayri bir cagriyla getirir; /net endpoint'i
    org'u govdeye gommuyor.
    """
    resp = requests.get(
        f"{PEERINGDB_BASE}/org/{org_id}",
        headers={"Accept": "application/json"},
        timeout=30,
    )
    if resp.status_code != 200:
        return None
    data = (resp.json() or {}).get("data") or []
    return data[0] if data else None
