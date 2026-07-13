import logging
from datetime import datetime, timezone

from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.x509.oid import NameOID

from app.db.sync_client import get_sync_db

logger = logging.getLogger(__name__)


def _extract_domains(der: bytes) -> set[str]:
    names: set[str] = set()
    try:
        cert = x509.load_der_x509_certificate(der, default_backend())
        try:
            san = cert.extensions.get_extension_for_class(x509.SubjectAlternativeName)
            names.update(san.value.get_values_for_type(x509.DNSName))
        except x509.ExtensionNotFound:
            pass

        for attr in cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME):
            if isinstance(attr.value, str):
                names.add(attr.value)
    except Exception:
        # Eski/standart-disi sertifikalar (orn. bozuk ASN.1 alanlari,
        # katı Rust tabanli ayristiriciyi kirabilen eski CA'lar) burada
        # herhangi bir asamada patlayabilir. Tek bir bozuk sertifika
        # yuzunden butun batch'in (digerlerindeki gecerli domainler dahil)
        # dusmemesi icin sessizce atlanir.
        return set()

    cleaned = set()
    for name in names:
        name = name.strip().lower().lstrip("*.")
        if name and " " not in name and "." in name:
            cleaned.add(name)
    return cleaned


def sync_certificates(certs: list[tuple[int, bytes]]) -> int:
    """Ham sertifika baytlarindan (SAN + CN) domain adlarini cikarip
    domains koleksiyonuna isler. Ayni domain PTR taramasindan da
    gorulmusse 'sources' alanina ikinci kaynak olarak eklenir.
    """
    db = get_sync_db()
    now = datetime.now(timezone.utc)
    written = 0

    for _cert_id, der in certs:
        for domain in _extract_domains(der):
            db.domains.update_one(
                {"domain": domain},
                {
                    "$set": {"last_seen": now},
                    "$setOnInsert": {"domain": domain, "first_seen": now},
                    "$addToSet": {"sources": "ct_log"},
                },
                upsert=True,
            )
            written += 1

    return written
