import logging
import random
import time

from app.index_defs import INDEX_DEFS

logger = logging.getLogger(__name__)

_MAX_ATTEMPTS = 5


def _normalize_keys(keys):
    if isinstance(keys, str):
        return [(keys, 1)]
    return list(keys)


def _index_exists(index_information: dict, keys) -> bool:
    wanted = _normalize_keys(keys)
    return any(list(info["key"]) == wanted for info in index_information.values())


async def _create_index_safe(db, collection_name, keys, kwargs):
    collection = db[collection_name]
    for attempt in range(1, _MAX_ATTEMPTS + 1):
        try:
            await collection.create_index(keys, **kwargs)
            return
        except Exception:
            try:
                info = await collection.index_information()
                if _index_exists(info, keys):
                    return
            except Exception:
                pass
            if attempt == _MAX_ATTEMPTS:
                logger.exception(
                    "Index olusturulamadi (%s deneme sonrasi): %s %s %s",
                    attempt,
                    collection_name,
                    keys,
                    kwargs,
                )
                return
            time.sleep(random.uniform(0.2, 1.0) * attempt)


async def ensure_indexes(db) -> None:
    for collection_name, keys, kwargs in INDEX_DEFS:
        await _create_index_safe(db, collection_name, keys, kwargs)
