import logging
import os
import time

import dns.exception
import dns.resolver
import dns.reversename
import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("remote-worker")

CENTRAL_API_URL = os.environ["CENTRAL_API_URL"].rstrip("/")
REMOTE_API_TOKEN = os.environ["REMOTE_API_TOKEN"]
QUEUE = os.environ.get("QUEUE", "ptr_sweep")
BATCH_SIZE = int(os.environ.get("BATCH_SIZE", "200"))
RATE_LIMIT_SECONDS = float(os.environ.get("RATE_LIMIT_SECONDS", "0.1"))
POLL_INTERVAL_SECONDS = float(os.environ.get("POLL_INTERVAL_SECONDS", "5"))
DNS_RESOLVER = os.environ.get("DNS_RESOLVER", "").strip()

_SOFT_ERRORS = (
    dns.resolver.NXDOMAIN,
    dns.resolver.NoAnswer,
    dns.resolver.NoNameservers,
    dns.exception.Timeout,
)

session = requests.Session()
session.headers["Authorization"] = f"Bearer {REMOTE_API_TOKEN}"


def get_resolver() -> dns.resolver.Resolver:
    # Bos ise sistem/ISP resolver'i (configure=True) kullanilir - farkli
    # kaynak IP'lerden dagitik sorgu yapmak zaten bu tasarimin amaci.
    resolver = dns.resolver.Resolver(configure=not DNS_RESOLVER)
    if DNS_RESOLVER:
        resolver.nameservers = [DNS_RESOLVER]
    resolver.timeout = 5
    resolver.lifetime = 5
    return resolver


def ptr_lookup(ip: str) -> str | None:
    try:
        rev_name = dns.reversename.from_address(ip)
        answer = get_resolver().resolve(rev_name, "PTR")
        return str(answer[0]).rstrip(".")
    except _SOFT_ERRORS:
        return None


def resolve_records(name: str, rdtype: str) -> list[str]:
    try:
        answer = get_resolver().resolve(name, rdtype)
        return sorted({str(r).rstrip(".") for r in answer})
    except _SOFT_ERRORS:
        return []


def resolve_mx_records(name: str) -> list[tuple[int, str]]:
    try:
        answer = get_resolver().resolve(name, "MX")
        return sorted({(r.preference, str(r.exchange).rstrip(".")) for r in answer})
    except _SOFT_ERRORS:
        return []


def resolve_txt_records(name: str) -> list[str]:
    try:
        answer = get_resolver().resolve(name, "TXT")
        return sorted({b"".join(r.strings).decode("utf-8", "replace") for r in answer})
    except _SOFT_ERRORS:
        return []


def _record_ips(name: str) -> list[dict]:
    ips = []
    for rdtype, version in (("A", 4), ("AAAA", 6)):
        for ip in resolve_records(name, rdtype):
            ips.append({"ip": ip, "version": version})
    return ips


def process_ptr_item(item: dict, meta: dict) -> dict:
    ip = item["ip"]
    return {"ip": ip, "ptr_hostname": ptr_lookup(ip)}


def process_dns_history_item(item: dict, meta: dict) -> dict:
    domain = item["domain"]
    nameservers = [{"host": ns, "ips": _record_ips(ns)} for ns in resolve_records(domain, "NS")]
    return {
        "domain": domain,
        "ips": _record_ips(domain),
        "nameservers": nameservers,
        "mx": [{"priority": p, "exchange": e} for p, e in resolve_mx_records(domain)],
        "txt": resolve_txt_records(domain),
    }


def describe_ptr_result(result: dict) -> str:
    return f"{result['ip']} -> {result.get('ptr_hostname') or '(bulunamadi)'}"


def _truncate(value: str, limit: int = 80) -> str:
    return value if len(value) <= limit else value[:limit] + "..."


def describe_dns_history_result(result: dict) -> str:
    ips = ", ".join(e["ip"] for e in result.get("ips") or []) or "-"
    ns = ", ".join(e["host"] for e in result.get("nameservers") or []) or "-"
    mx = ", ".join(e["exchange"] for e in result.get("mx") or []) or "-"
    txt = "; ".join(_truncate(v) for v in result.get("txt") or []) or "-"
    return f"{result['domain']} | A/AAAA: {ips} | NS: {ns} | MX: {mx} | TXT: {txt}"


def describe_port_scan_result(result: dict) -> str:
    ports = result.get("open_ports") or []
    if not ports:
        return f"{result['ip']} -> acik port yok ({result.get('total_scanned', 0)} port tarandi)"
    svc_bits = []
    for svc in result.get("services") or []:
        names = ", ".join(svc.get("services") or []) or "?"
        svc_bits.append(f"{svc['port']}/{names}")
    return f"{result['ip']} -> {len(ports)} acik port ({', '.join(map(str, ports))}) | " + "; ".join(svc_bits)


# Yeni bir kuyruk desteklemek icin: item -> sonuc dict'i ureten bir islev ve
# sonucu tek satirlik ozetleyen bir describe islevi yazip buraya ekleyin
# (karsiligi remote-api/app/queues/<isim>.py'da olmali). port_scan icin
# gercek processor port_scanner.py'de tanimli (yalnizca worker-portscan
# image'inda mevcut - bkz. Dockerfile.portscan), bu yuzden burada lazy
# import ediliyor ki diger 3 image'in scapy'ye ihtiyaci olmasin.
PROCESSORS = {
    "ptr_sweep": process_ptr_item,
    "dns_history": process_dns_history_item,
    # dns_history_apex: hangi domain'lerin verildigi sunucu tarafinda (sadece
    # ana/apex domainler) filtreleniyor, worker'in yaptigi is birebir ayni.
    "dns_history_apex": process_dns_history_item,
}
DESCRIBERS = {
    "ptr_sweep": describe_ptr_result,
    "dns_history": describe_dns_history_result,
    "dns_history_apex": describe_dns_history_result,
    "port_scan": describe_port_scan_result,
}

if QUEUE == "port_scan":
    from port_scanner import process_port_scan_item

    PROCESSORS["port_scan"] = process_port_scan_item

# IP/item basina anlik submit yapan kuyruklar - digerleri batch sonunda tek
# submit yapmaya devam ediyor (davranislari degismedi).
INCREMENTAL_QUEUES = {"port_scan"}


def claim_batch() -> dict:
    resp = session.get(
        f"{CENTRAL_API_URL}/v1/claim",
        params={"queue": QUEUE, "max_items": BATCH_SIZE},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def submit_results(batch_id: str, results: list[dict]) -> None:
    resp = session.post(
        f"{CENTRAL_API_URL}/v1/submit",
        json={"batch_id": batch_id, "queue": QUEUE, "results": results},
        timeout=30,
    )
    resp.raise_for_status()


def run_once(processor, describer) -> int:
    batch = claim_batch()
    items = batch.get("items") or []
    if not items:
        return 0

    meta = batch.get("meta") or {}
    delay = float(meta.get("delay_seconds", RATE_LIMIT_SECONDS))

    if QUEUE in INCREMENTAL_QUEUES:
        # Her IP bitince sonucu HEMEN gonder - batch'in tamami bitmesini
        # beklemez. Boylece admin panel ilerlemeyi canli gorebiliyor ve
        # worker cokerse zaten gonderilmis sonuclar kaybolmuyor.
        for item in items:
            result = processor(item, meta)
            logger.info(describer(result))
            submit_results(batch["batch_id"], [result])
            time.sleep(delay)
        logger.info("batch tamamlandi: %s islendi", len(items))
        return len(items)

    results = []
    for item in items:
        result = processor(item, meta)
        results.append(result)
        logger.info(describer(result))
        time.sleep(delay)

    submit_results(batch["batch_id"], results)
    logger.info("batch tamamlandi: %s islendi", len(results))
    return len(results)


def main() -> None:
    processor = PROCESSORS.get(QUEUE)
    describer = DESCRIBERS.get(QUEUE)
    if processor is None or describer is None:
        logger.error("desteklenmeyen kuyruk: %s (destekli: %s)", QUEUE, ", ".join(PROCESSORS))
        return

    logger.info("baslatildi (queue=%s, central=%s)", QUEUE, CENTRAL_API_URL)
    while True:
        try:
            processed = run_once(processor, describer)
        except requests.RequestException:
            logger.exception("central API'ye ulasilamadi, tekrar denenecek")
            processed = 0
        if processed == 0:
            time.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
