import requests

RIPESTAT_BASE = "https://stat.ripe.net/data"


def fetch_announced_prefixes(asn: int) -> dict | None:
    """Bir ASN'in gecmiste ve su an duyurdugu tum prefixleri, her biri icin
    zaman araliklariyla (timelines) birlikte dondurur. Key/auth gerekmez.
    """
    resp = requests.get(
        f"{RIPESTAT_BASE}/announced-prefixes/data.json",
        params={"resource": f"AS{asn}"},
        timeout=30,
    )
    if resp.status_code != 200:
        return None
    return resp.json()


def fetch_prefix_overview(prefix: str) -> dict | None:
    """Bir prefix icin su anda onu duyuran ASN(lar)i dondurur (canli sorgu)."""
    resp = requests.get(
        f"{RIPESTAT_BASE}/prefix-overview/data.json",
        params={"resource": prefix},
        timeout=30,
    )
    if resp.status_code != 200:
        return None
    return resp.json()


def fetch_asn_neighbours(asn: int) -> dict | None:
    """RIS route collector'larinin BGP tablolarinda gozlemledigi, bir ASN'e
    komsu ASN'leri dondurur (gercek peering'in herkese acik, kimlik dogrulama
    gerektirmeyen yaklasik karsiligi). Her komsu 'left' (bu ASN'e giden yolda
    onceki hop - upstream/peer) veya 'right' (sonraki hop - musteri/peer)
    olarak isaretlenir. Key/auth gerekmez.
    """
    resp = requests.get(
        f"{RIPESTAT_BASE}/asn-neighbours/data.json",
        params={"resource": f"AS{asn}"},
        timeout=30,
    )
    if resp.status_code != 200:
        return None
    return resp.json()
