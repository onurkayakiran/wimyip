from pydantic import BaseModel


class PrefixOut(BaseModel):
    cidr: str
    version: int
    rir: str
    country: str | None = None
    status: str | None = None
    alloc_date: str | None = None
    opaque_id: str | None = None


class AsnOut(BaseModel):
    asn: int
    rir: str
    country: str | None = None
    status: str | None = None
    alloc_date: str | None = None
    opaque_id: str | None = None


class IpLookupOut(BaseModel):
    ip: str
    prefix: PrefixOut
    all_matches: list[PrefixOut]


class StatsOut(BaseModel):
    prefixes: int
    asns: int
    domains: int
