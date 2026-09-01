import ipaddress
import socket
import time
from datetime import datetime, timedelta, timezone

import requests

from app.core.config import settings
from app.core.mailer import send_email
from app.db.sync_client import get_sync_db

CHECK_TYPES = ("http", "https", "ping")


class UnsafeTargetError(Exception):
    """Hedef, private/reserved bir IP'ye cozumleniyor (SSRF koruma)."""


def resolve_public_ip(hostname: str) -> str:
    """Hostname'i coz, IP private/reserved (RFC1918, loopback, link-local -
    169.254.169.254 cloud metadata dahil - vs. *.cluster.local) ise reddet.

    Kullanicilar KEYFI bir hedef girebildigi icin bu kontrol olmadan bu
    ozellik, cluster'in kendi internal agini/metadata servisini probe'lamak
    icin bir SSRF pivotuna donusebilirdi. Sadece monitor OLUSTURULURKEN
    degil, HER kontrolde tekrar cagrilir (DNS rebinding'e karsi - hedefin
    IP'si zaman icinde degisebilir).
    """
    try:
        ip_str = socket.gethostbyname(hostname)
    except socket.gaierror as exc:
        raise UnsafeTargetError(f"Hostname cozulemedi: {exc}")

    ip = ipaddress.ip_address(ip_str)
    if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
        raise UnsafeTargetError(f"Hedef private/reserved bir IP'ye cozumleniyor: {ip_str}")
    return ip_str


# Bazi siteler (orn. Wikipedia/Wikimedia) generic "python-requests/x.y"
# User-Agent'ini bot sanip 403 ile engelliyor - bu, hedefin GERCEKTEN down
# olmadigi halde monitoring'in yanlislikla "down" raporlamasina yol acardi.
# Kendimizi taniyan, tarayici benzeri bir User-Agent gonderiyoruz.
_HTTP_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; wimyip-monitor/1.0)"}


def _run_http_check(target: str, scheme: str) -> dict:
    url = f"{scheme}://{target}"
    started = time.monotonic()
    try:
        resolve_public_ip(target)
        resp = requests.get(
            url, timeout=settings.monitor_http_timeout_seconds, allow_redirects=True, headers=_HTTP_HEADERS
        )
        elapsed_ms = (time.monotonic() - started) * 1000
        return {
            "ok": resp.status_code < 400,
            "response_time_ms": round(elapsed_ms, 1),
            "status_code": resp.status_code,
            "error": None,
        }
    except UnsafeTargetError as exc:
        return {"ok": False, "response_time_ms": None, "status_code": None, "error": str(exc)}
    except requests.RequestException as exc:
        elapsed_ms = (time.monotonic() - started) * 1000
        return {"ok": False, "response_time_ms": round(elapsed_ms, 1), "status_code": None, "error": str(exc)}


def _run_ping_check(target: str) -> dict:
    try:
        resolve_public_ip(target)
    except UnsafeTargetError as exc:
        return {"ok": False, "response_time_ms": None, "status_code": None, "error": str(exc)}

    # icmplib SADECE izole monitor-worker image'inda kurulu (CAP_NET_RAW
    # gerektirir) - lazy import, diger celery surecleri bu modulu hic
    # yuklemeye calismaz (onlar "monitor-checks" kuyrugunu tuketmiyor).
    from icmplib import ping as icmp_ping

    try:
        result = icmp_ping(target, count=3, timeout=settings.monitor_ping_timeout_seconds, privileged=True)
        return {
            "ok": result.is_alive,
            "response_time_ms": round(result.avg_rtt, 1) if result.is_alive else None,
            "status_code": None,
            "error": None if result.is_alive else "Yanit yok (paket kaybi %100)",
        }
    except Exception as exc:
        return {"ok": False, "response_time_ms": None, "status_code": None, "error": str(exc)}


def _run_check(target: str, check_type: str) -> dict:
    if check_type == "http":
        return _run_http_check(target, "http")
    if check_type == "https":
        return _run_http_check(target, "https")
    if check_type == "ping":
        return _run_ping_check(target)
    raise ValueError(f"Bilinmeyen check tipi: {check_type}")


def _send_status_email(db, monitor: dict, check_type: str, new_status: str) -> None:
    user = db.users.find_one({"_id": monitor["user_id"]})
    if not user:
        return
    subject = f"[wimyip] {monitor['target']} ({check_type}) durumu: {new_status.upper()}"
    body = (
        f"{monitor['target']} hedefinin {check_type} kontrolu {new_status.upper()} durumuna gecti.\n\n"
        f"Bu bildirimi /monitors sayfanizdaki ayarlardan yonetebilirsiniz."
    )
    send_email(user["email"], subject, body)


def run_due_checks() -> dict:
    db = get_sync_db()
    now = datetime.now(timezone.utc)
    due = list(
        db.monitors.find({"next_check_at": {"$lte": now}}).limit(settings.monitor_check_batch_size)
    )

    processed = 0
    for monitor in due:
        checks = monitor.get("checks", {})
        current_status = monitor.get("current_status", {})
        status_since = monitor.get("status_since", {})
        new_status = dict(current_status)
        new_status_since = dict(status_since)

        for check_type in CHECK_TYPES:
            if not checks.get(check_type):
                continue
            result = _run_check(monitor["target"], check_type)
            db.monitor_results.insert_one(
                {
                    "monitor_id": monitor["_id"],
                    "user_id": monitor["user_id"],
                    "check_type": check_type,
                    "ok": result["ok"],
                    "response_time_ms": result["response_time_ms"],
                    "status_code": result["status_code"],
                    "error": result["error"],
                    "checked_at": now,
                }
            )
            next_state = "up" if result["ok"] else "down"
            previous_state = current_status.get(check_type, "unknown")
            new_status[check_type] = next_state
            # status_since SADECE durum fiilen degistiginde (veya hic
            # bilinmiyorken ilk kez belirlendiginde) ilerletilir - "ne
            # zamandir boyle" suresinin dogru hesaplanabilmesi icin her
            # kontrolde degil, sadece gecislerde guncelleniyor.
            if previous_state != next_state:
                new_status_since[check_type] = now
            if previous_state != "unknown" and previous_state != next_state:
                _send_status_email(db, monitor, check_type, next_state)

        interval = monitor.get("interval_seconds", settings.default_monitor_interval_seconds)
        db.monitors.update_one(
            {"_id": monitor["_id"]},
            {
                "$set": {
                    "current_status": new_status,
                    "status_since": new_status_since,
                    "last_checked_at": now,
                    "next_check_at": now + timedelta(seconds=interval),
                }
            },
        )
        processed += 1

    return {"processed": processed}
