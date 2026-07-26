import socket

import dns.exception
import dns.resolver
import dns.reversename

from app.core.config import settings

_resolver: dns.resolver.Resolver | None = None

_SOFT_ERRORS = (
    dns.resolver.NXDOMAIN,
    dns.resolver.NoAnswer,
    dns.resolver.NoNameservers,
    dns.exception.Timeout,
)


def get_resolver() -> dns.resolver.Resolver:
    global _resolver
    if _resolver is None:
        # dnspython nameservers alaninda dogrudan IP bekler; "unbound" gibi
        # bir Docker servis adini Docker'in kendi DNS'i uzerinden (socket
        # araciligiyla) IP'ye ceviriyoruz.
        ip = socket.gethostbyname(settings.ptr_resolver_host)
        r = dns.resolver.Resolver(configure=False)
        r.nameservers = [ip]
        r.timeout = 5
        r.lifetime = 5
        _resolver = r
    return _resolver


def ptr_lookup(ip: str) -> str | None:
    """Verilen IP icin PTR (reverse DNS) sorgusu yapar."""
    try:
        rev_name = dns.reversename.from_address(ip)
        answer = get_resolver().resolve(rev_name, "PTR")
        return str(answer[0]).rstrip(".")
    except _SOFT_ERRORS:
        return None


def resolve_records(name: str, rdtype: str) -> list[str]:
    """Verilen domain/hostname icin belirtilen kayit tipini (A/AAAA/NS vb.)
    cozer; bulunamazsa/hata olursa bos liste doner (cagiran taraf bunu
    'su an kayit yok' olarak yorumlar, exception firlatmaz).
    """
    try:
        answer = get_resolver().resolve(name, rdtype)
        return sorted({str(r).rstrip(".") for r in answer})
    except _SOFT_ERRORS:
        return []


def resolve_mx_records(name: str) -> list[tuple[int, str]]:
    """MX kayitlarini (priority, exchange) ciftleri olarak doner."""
    try:
        answer = get_resolver().resolve(name, "MX")
        return sorted({(r.preference, str(r.exchange).rstrip(".")) for r in answer})
    except _SOFT_ERRORS:
        return []


def resolve_txt_records(name: str) -> list[str]:
    """TXT kayitlarini (parcalari birlestirilmis) metin listesi olarak doner."""
    try:
        answer = get_resolver().resolve(name, "TXT")
        return sorted({b"".join(r.strings).decode("utf-8", "replace") for r in answer})
    except _SOFT_ERRORS:
        return []
