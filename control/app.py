import re
import socket

import docker
from docker.errors import NotFound
from fastapi import Depends, FastAPI, Header, HTTPException, Query

from config import settings

app = FastAPI(title="ASN Control Service")

client = docker.from_env()

_ERROR_PATTERN = re.compile(r"error|traceback|critical|exception", re.IGNORECASE)


def _project_label() -> str:
    # Kendi container'imizin compose projesini kendimiz kesfediyoruz - boylece
    # proje adini (dizin adina bagli, degisebilir) ayrica .env'de tekrar
    # tanimlamaya gerek kalmiyor.
    own = client.containers.get(socket.gethostname())
    return own.labels["com.docker.compose.project"]


def require_token(x_control_token: str = Header(default="")) -> None:
    if not settings.control_service_token or x_control_token != settings.control_service_token:
        raise HTTPException(status_code=401, detail="Gecersiz token")


def _service_containers(service: str | None = None):
    project = _project_label()
    filters = {"label": [f"com.docker.compose.project={project}"]}
    if service:
        filters["label"].append(f"com.docker.compose.service={service}")
    return client.containers.list(all=True, filters=filters)


def _container_summary(container) -> dict:
    attrs = container.attrs
    state = attrs.get("State", {})
    health = state.get("Health", {}).get("Status")
    return {
        "service": container.labels.get("com.docker.compose.service", container.name),
        "container_name": container.name,
        "status": container.status,
        "health": health,
        "started_at": state.get("StartedAt"),
        "restart_count": attrs.get("RestartCount", 0),
        "image": container.image.tags[0] if container.image.tags else container.image.short_id,
    }


@app.get("/services")
def list_services(_: None = Depends(require_token)):
    containers = _service_containers()
    return {"services": [_container_summary(c) for c in containers]}


@app.get("/services/{service}/logs")
def service_logs(service: str, tail: int = Query(default=200, le=2000), _: None = Depends(require_token)):
    containers = _service_containers(service)
    if not containers:
        raise HTTPException(status_code=404, detail=f"Servis bulunamadi: {service}")

    container = containers[0]
    raw = container.logs(tail=tail, timestamps=True).decode("utf-8", "replace")
    lines = raw.splitlines()
    error_count = sum(1 for line in lines if _ERROR_PATTERN.search(line))

    return {
        "service": service,
        "container_name": container.name,
        "lines": lines,
        "error_count": error_count,
    }


@app.post("/services/{service}/restart")
def restart_service(service: str, _: None = Depends(require_token)):
    containers = _service_containers(service)
    if not containers:
        raise HTTPException(status_code=404, detail=f"Servis bulunamadi: {service}")

    for container in containers:
        try:
            container.restart(timeout=10)
        except NotFound:
            raise HTTPException(status_code=404, detail=f"Servis bulunamadi: {service}")

    return {"restarted": service, "containers": [c.name for c in containers]}
