import ipaddress
from collections.abc import Iterable
from datetime import datetime


def _parse_date(raw: str) -> str | None:
    if not raw or raw == "00000000":
        return None
    try:
        return datetime.strptime(raw, "%Y%m%d").date().isoformat()
    except ValueError:
        return None


def parse_delegated_stats(
    rir: str, lines: Iterable[str]
) -> tuple[list[dict], list[dict]]:
    """RIR delegated-extended formatindaki satirlari IPv4 prefix ve ASN
    kayitlarina cevirir. IPv6 ve ozet(summary)/header satirlari MVP
    kapsaminda atlanir (Faz 7'de IPv6 eklenecek).
    """
    prefixes: list[dict] = []
    asns: list[dict] = []

    for raw_line in lines:
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        parts = line.split("|")
        if len(parts) < 7:
            continue

        _registry, cc, rec_type, start, value, date, status = parts[:7]
        opaque_id = parts[7] if len(parts) > 7 else None

        if status not in ("allocated", "assigned"):
            continue

        alloc_date = _parse_date(date)

        if rec_type == "ipv4":
            try:
                count = int(value)
                start_addr = ipaddress.IPv4Address(start)
                end_addr = ipaddress.IPv4Address(int(start_addr) + count - 1)
                networks = ipaddress.summarize_address_range(start_addr, end_addr)
            except (ValueError, ipaddress.AddressValueError):
                continue

            for net in networks:
                prefixes.append(
                    {
                        "cidr": str(net),
                        "version": 4,
                        "start_ip": int(net.network_address),
                        "end_ip": int(net.broadcast_address),
                        "rir": rir,
                        "country": cc or None,
                        "status": status,
                        "alloc_date": alloc_date,
                        "opaque_id": opaque_id,
                    }
                )

        elif rec_type == "asn":
            try:
                asn_start = int(start)
                count = int(value)
            except ValueError:
                continue

            for asn in range(asn_start, asn_start + count):
                asns.append(
                    {
                        "asn": asn,
                        "rir": rir,
                        "country": cc or None,
                        "status": status,
                        "alloc_date": alloc_date,
                        "opaque_id": opaque_id,
                    }
                )

    return prefixes, asns
