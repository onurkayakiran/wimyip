from datetime import datetime, timezone

from app.db.sync_client import get_sync_db
from app.ingestion.dns_client import resolve_records

_A_TYPES = (("A", 4), ("AAAA", 6))


def _record_ips(name: str) -> list[tuple[str, int]]:
    ips = []
    for rdtype, version in _A_TYPES:
        for ip in resolve_records(name, rdtype):
            ips.append((ip, version))
    return ips


def sync_domain_dns(domain: str) -> dict:
    """Bir domain'in A/AAAA/NS kayitlarini yeniden cozer. Her gozlemlenen
    deger (ip veya nameserver) kendi first_seen/last_seen'iyle ayri bir
    satir olarak tutulur - boylece gecmis asla ezilmez, sadece hangi
    degerlerin hala 'guncel' oldugu last_seen'e bakilarak anlasilir.
    Ayrica her NS hostname'inin KENDI A/AAAA kaydi da nameserver_ip_history'ye
    islenir (nameserver'lar da zamanla IP degistirebilir).
    """
    db = get_sync_db()
    now = datetime.now(timezone.utc)

    # domains koleksiyonu "bilinen domain kayit defteri"dir; bu fonksiyon
    # CT-log/PTR disinda (orn. manuel /refresh-dns) de cagirilabildigi icin
    # domain'in burada da var oldugundan emin oluyoruz - aksi halde zengin
    # DNS gecmisi olsa bile /api/domains/{domain} 404 doner.
    db.domains.update_one(
        {"domain": domain},
        {
            "$set": {"last_seen": now},
            "$setOnInsert": {"domain": domain, "first_seen": now},
        },
        upsert=True,
    )

    ip_count = 0
    for ip, version in _record_ips(domain):
        db.domain_ip_history.update_one(
            {"domain": domain, "ip": ip},
            {
                "$set": {"last_seen": now, "ip_version": version},
                "$setOnInsert": {"domain": domain, "ip": ip, "first_seen": now},
            },
            upsert=True,
        )
        ip_count += 1

    ns_count = 0
    for ns in resolve_records(domain, "NS"):
        db.domain_ns_history.update_one(
            {"domain": domain, "nameserver": ns},
            {
                "$set": {"last_seen": now},
                "$setOnInsert": {"domain": domain, "nameserver": ns, "first_seen": now},
            },
            upsert=True,
        )
        ns_count += 1

        for ns_ip, version in _record_ips(ns):
            db.nameserver_ip_history.update_one(
                {"nameserver": ns, "ip": ns_ip},
                {
                    "$set": {"last_seen": now, "ip_version": version},
                    "$setOnInsert": {"nameserver": ns, "ip": ns_ip, "first_seen": now},
                },
                upsert=True,
            )

    return {"domain": domain, "ips": ip_count, "nameservers": ns_count}
