import logging

from app.core.config import settings
from app.ingestion.batch_runner import run_resumable_batch
from app.ingestion.dns_history_sync import sync_domain_dns

logger = logging.getLogger(__name__)


def enrich_dns_history_batch() -> dict:
    def fetch_page(db, cursor):
        query = {"domain": {"$gt": cursor}} if cursor is not None else {}
        return list(
            db.domains.find(query, {"domain": 1})
            .sort("domain", 1)
            .limit(settings.dns_history_batch_size)
        )

    def process_one(doc):
        sync_domain_dns(doc["domain"])

    return run_resumable_batch(
        "dns_history_sync:domains",
        fetch_page,
        process_one,
        lambda doc: doc["domain"],
        settings.dns_history_rate_limit_seconds,
    )


if __name__ == "__main__":
    import json

    logging.basicConfig(level=logging.INFO)
    print(json.dumps(enrich_dns_history_batch(), default=str, indent=2))
