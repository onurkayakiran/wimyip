import logging

from app.core.config import settings
from app.ingestion.batch_runner import run_resumable_batch
from app.ingestion.rdap_sync import sync_asn_rdap, sync_prefix_rdap

logger = logging.getLogger(__name__)


def enrich_asns_batch() -> dict:
    def fetch_page(db, cursor):
        query = {"asn": {"$gt": cursor}} if cursor is not None else {}
        return list(
            db.asns.find(query, {"asn": 1, "rir": 1})
            .sort("asn", 1)
            .limit(settings.rdap_batch_size)
        )

    def process_one(doc):
        sync_asn_rdap(doc["asn"], doc["rir"])

    return run_resumable_batch(
        "rdap_sync:asns",
        fetch_page,
        process_one,
        lambda doc: doc["asn"],
        settings.rdap_rate_limit_seconds,
    )


def enrich_prefixes_batch() -> dict:
    def fetch_page(db, cursor):
        query = {"start_ip": {"$gt": cursor}} if cursor is not None else {}
        return list(
            db.prefixes.find(query, {"cidr": 1, "rir": 1, "start_ip": 1})
            .sort("start_ip", 1)
            .limit(settings.rdap_batch_size)
        )

    def process_one(doc):
        sync_prefix_rdap(doc["cidr"], doc["rir"])

    return run_resumable_batch(
        "rdap_sync:prefixes",
        fetch_page,
        process_one,
        lambda doc: doc["start_ip"],
        settings.rdap_rate_limit_seconds,
    )


if __name__ == "__main__":
    import json
    import sys

    logging.basicConfig(level=logging.INFO)
    target = sys.argv[1] if len(sys.argv) > 1 else "asns"
    result = enrich_asns_batch() if target == "asns" else enrich_prefixes_batch()
    print(json.dumps(result, default=str, indent=2))
