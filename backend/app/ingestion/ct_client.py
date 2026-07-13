import logging
import time

import psycopg2

logger = logging.getLogger(__name__)

# crt.sh herkese acik, salt-okunur Postgres veritabani. NOT: "certificate_identity"
# tablosu artik toplu (bulk) taramaya kapatilmis ("has been superseded by a Full
# Text Search index" hatasi doner) - bu yuzden domain adlarini bu tablodan degil,
# ham sertifika baytlarindan (asagida ct_sync.py) kendimiz cikariyoruz.
# "ct_log_entry" tablosu ise certificate_id'ye gore artan sirada, toplu
# taramaya hala acik ve incremental cursor icin yeterli.
CRTSH_DSN = "host=crt.sh port=5432 dbname=certwatch user=guest"

# crt.sh'nin sundugu veritabani bir streaming replication replica'si; WAL
# replay sirasinda bizim sorgumuzun ihtiyac duydugu eski satir surumleri
# temizlenirse Postgres sorguyu "canceling statement due to conflict with
# recovery" hatasiyla iptal eder. Bu bizim tarafimizdan degil, crt.sh'nin
# replica'sinin normal isleyisinden kaynaklanan GECICI bir durumdur; birkac
# saniye sonra tekrar denemek genelde yeterlidir.
_MAX_RETRIES = 3
_RETRY_DELAY_SECONDS = 3


def _connect():
    conn = psycopg2.connect(CRTSH_DSN, connect_timeout=15)
    conn.set_session(readonly=True, autocommit=True)
    return conn


def _with_retry(run):
    """run() salt-okunur bir sorgu calistirir; her deneme icin tamamen taze
    bir baglanti kullanilir (onceki baglanti hata sonrasi bozuk durumda
    olabilir). Sadece OperationalError (baglanti kopmasi, recovery conflict
    vb.) icin yeniden dener - sorgu sozdizimi hatasi gibi kalici sorunlari
    tekrar tekrar denemez.
    """
    last_exc = None
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            return run()
        except psycopg2.OperationalError as exc:
            last_exc = exc
            logger.warning(
                "crt.sh sorgusu basarisiz (deneme %s/%s): %s", attempt, _MAX_RETRIES, exc
            )
            if attempt < _MAX_RETRIES:
                time.sleep(_RETRY_DELAY_SECONDS)
    raise last_exc


def fetch_max_certificate_id() -> int:
    def run():
        conn = _connect()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT max(certificate_id) FROM ct_log_entry")
                return cur.fetchone()[0] or 0
        finally:
            conn.close()

    return _with_retry(run)


def fetch_new_certificate_ids(after_id: int, limit: int) -> list[int]:
    def run():
        conn = _connect()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT DISTINCT certificate_id FROM ct_log_entry "
                    "WHERE certificate_id > %s ORDER BY certificate_id LIMIT %s",
                    (after_id, limit),
                )
                return [row[0] for row in cur.fetchall()]
        finally:
            conn.close()

    return _with_retry(run)


def fetch_certificates(ids: list[int]) -> list[tuple[int, bytes]]:
    if not ids:
        return []

    def run():
        conn = _connect()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT id, certificate FROM certificate WHERE id = ANY(%s)", (ids,))
                return [(row[0], bytes(row[1])) for row in cur.fetchall()]
        finally:
            conn.close()

    return _with_retry(run)
