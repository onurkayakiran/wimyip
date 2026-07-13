import requests

# Her RIR'in bilinen RDAP taban URL'i. prefixes/asns koleksiyonlarindaki
# "rir" alani zaten hangi RIR'a ait oldugunu bildirdigi icin IANA bootstrap
# dosyasina ihtiyac yok, dogrudan ilgili RIR'in RDAP servisine sorulur.
RDAP_BASE_URLS = {
    "arin": "https://rdap.arin.net/registry/",
    "ripencc": "https://rdap.db.ripe.net/",
    "apnic": "https://rdap.apnic.net/",
    "lacnic": "https://rdap.lacnic.net/rdap/",
    "afrinic": "https://rdap.afrinic.net/rdap/",
}

_HEADERS = {"Accept": "application/rdap+json"}


def fetch_asn_rdap(rir: str, asn: int) -> dict | None:
    base = RDAP_BASE_URLS.get(rir)
    if not base:
        return None
    resp = requests.get(f"{base}autnum/{asn}", headers=_HEADERS, timeout=30)
    if resp.status_code != 200:
        return None
    return resp.json()


def fetch_prefix_rdap(rir: str, cidr: str) -> dict | None:
    base = RDAP_BASE_URLS.get(rir)
    if not base:
        return None
    resp = requests.get(f"{base}ip/{cidr}", headers=_HEADERS, timeout=30)
    if resp.status_code != 200:
        return None
    return resp.json()


def _find_fn(vcard_array) -> str | None:
    if not vcard_array or len(vcard_array) < 2:
        return None
    for item in vcard_array[1]:
        if item and item[0] == "fn":
            return item[3]
    return None


def extract_org(rdap_json: dict) -> dict:
    """RDAP yanitindan organizasyon adi/handle bilgisini cikarir.
    RIR'lar arasinda entity yapisi farkli olabildigi icin oncelik sirasi:
    registrant rolundeki entity -> ilk entity -> ust seviye name/handle.
    """
    top_name = rdap_json.get("name")
    top_handle = rdap_json.get("handle")

    org_name = None
    org_handle = None
    for entity in rdap_json.get("entities") or []:
        roles = entity.get("roles") or []
        fn = _find_fn(entity.get("vcardArray"))
        if fn and (org_name is None or "registrant" in roles):
            org_name = fn
            org_handle = entity.get("handle")
        if "registrant" in roles:
            break

    return {
        "org_name": org_name or top_name,
        "org_handle": org_handle or top_handle,
        "network_name": top_name,
        "handle": top_handle,
    }
