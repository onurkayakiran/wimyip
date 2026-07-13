import logging
import random
import time

from app.db.index_defs import INDEX_DEFS

logger = logging.getLogger(__name__)

_MAX_ATTEMPTS = 5


def _normalize_keys(keys):
    if isinstance(keys, str):
        return [(keys, 1)]
    return list(keys)


def _index_exists(index_information: dict, keys) -> bool:
    wanted = _normalize_keys(keys)
    return any(list(info["key"]) == wanted for info in index_information.values())


# --- senkron (pymongo) - worker/beat/ptr-worker icin ---


def _create_index_safe_sync(db, collection_name, keys, kwargs):
    collection = db[collection_name]
    for attempt in range(1, _MAX_ATTEMPTS + 1):
        try:
            collection.create_index(keys, **kwargs)
            return
        except Exception:
            # Ayni anda forklanmis birden fazla worker alt sureci (hatta
            # farkli container'lar - worker/ptr-worker) ayni index'i ayni
            # anda kurmaya calisiyor olabilir. Once index zaten olustu mu
            # diye bak; olustuysa bu zararsiz bir yaris sonucudur.
            try:
                if _index_exists(collection.index_information(), keys):
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


def ensure_indexes_sync(db) -> None:
    """pymongo (senkron) ile - Celery worker/beat/ptr-worker surecleri
    baslarken cagirir, boylece backend'in FastAPI'si henuz calismamis olsa
    bile her surec kendi yazacagi koleksiyonlarin tekil index'lerinin var
    oldugundan emin olur. Birden fazla surec/alt-surec ayni anda cagirsa
    bile guvenlidir (yarisan denemeler birbirini bekler/vazgecer).
    """
    # ptr_records eskiden "ip" uzerinde tekildi (gecmis tutmuyordu); artik
    # (ip, ptr_hostname) cifti tekil - eski index varsa once kaldirilmali.
    try:
        existing = db.ptr_records.index_information()
        if "ip_1" in existing:
            db.ptr_records.drop_index("ip_1")
    except Exception:
        pass  # zaten kaldirilmis veya baska bir surec kaldiriyor - sorun degil

    for collection_name, keys, kwargs in INDEX_DEFS:
        _create_index_safe_sync(db, collection_name, keys, kwargs)


# --- async (motor) - FastAPI (backend) icin ---


async def _create_index_safe_async(db, collection_name, keys, kwargs):
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


async def ensure_indexes_async(db) -> None:
    """motor (async) ile - FastAPI'nin lifespan baslangicinda cagirir."""
    try:
        existing = await db.ptr_records.index_information()
        if "ip_1" in existing:
            await db.ptr_records.drop_index("ip_1")
    except Exception:
        pass

    for collection_name, keys, kwargs in INDEX_DEFS:
        await _create_index_safe_async(db, collection_name, keys, kwargs)
