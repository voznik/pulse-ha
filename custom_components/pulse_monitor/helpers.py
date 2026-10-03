"""Pure extraction helpers (no Home Assistant imports) for Pulse payloads."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

VERDICTS = ("ok", "attention", "critical", "stale", "off", "unknown")


def get(d: Any, *path: Any) -> Any:
    for key in path:
        try:
            d = d[key]
        except (KeyError, IndexError, TypeError):
            return None
    return d


def _pct(v: Any) -> float | None:
    # Pulse uses -1 as "unknown" for percentages.
    return v if isinstance(v, int | float) and v >= 0 else None


CONTAINER_HEALTH = ("healthy", "unhealthy", "starting", "none")


def container_key(r: dict) -> str:
    # Pulse resource ids change when a container is recreated; the Coolify service
    # label (else the container name) is stable and readable.
    return get(r, "docker", "labels", "coolify.serviceName") or r.get("name") or r["id"]


def container_image(r: dict) -> str | None:
    return get(r, "docker", "image")


def container_attrs(r: dict) -> dict:
    return {
        "image": container_image(r),
        "project": get(r, "docker", "labels", "coolify.projectName"),
        "resource": get(r, "docker", "labels", "coolify.resourceName"),
    }


def container_health(r: dict) -> str:
    v = get(r, "docker", "health")
    return v if v in CONTAINER_HEALTH else "none"


def update_available(r: dict) -> bool | None:
    st = get(r, "docker", "updateStatus")
    if not st or st.get("error"):
        return None
    return st.get("updateAvailable")


def oom_killed(r: dict) -> bool:
    return bool(get(r, "docker", "oomKilled"))


def started(r: dict) -> datetime | None:
    v = get(r, "docker", "startedAt")
    try:
        return datetime.fromisoformat(v) if v else None
    except ValueError:
        return None


def containers_running(data: dict) -> int:
    return sum(container_running(c) for c in data["containers"].values())


def containers_unhealthy(data: dict) -> int:
    return sum(
        container_health(c) == "unhealthy" or not container_running(c)
        for c in data["containers"].values()
    )


def container_updates(data: dict) -> int:
    return sum(update_available(c) is True for c in data["containers"].values())


def container_update_attrs(data: dict) -> dict:
    return {
        "containers": [
            k for k, c in data["containers"].items() if update_available(c) is True
        ]
    }


def is_stale(identifiers: set, data: dict, fleet_id: str, domain: str) -> bool:
    """True if none of the device's identifiers match a live agent, container or the fleet."""
    live = {fleet_id, *data["agents"], *data["containers"]}
    return not any(d == domain and i in live for d, i in identifiers)


def display_name(r: dict) -> str:
    return get(r, "canonicalIdentity", "displayName") or r.get("name") or r["id"]


def cpu(r: dict) -> float | None:
    return _pct(get(r, "metrics", "cpu", "percent"))


def mem_pct(r: dict) -> float | None:
    return _pct(get(r, "metrics", "memory", "percent"))


def mem_used(r: dict) -> int | None:
    return get(r, "metrics", "memory", "used")


def disk_pct(r: dict) -> float | None:
    return _pct(get(r, "metrics", "disk", "percent"))


def disk_used(r: dict) -> int | None:
    return get(r, "metrics", "disk", "used")


def load_pct(r: dict) -> float | None:
    cores = get(r, "agent", "cpuCount")
    l1 = get(r, "agent", "loadAverage", 0)
    if not cores or l1 is None:
        return None
    return round(l1 / cores * 100, 1)


def load_attrs(r: dict) -> dict:
    la = get(r, "agent", "loadAverage") or []
    return {
        "load_1m": get(la, 0),
        "load_5m": get(la, 1),
        "load_15m": get(la, 2),
        "cpu_count": get(r, "agent", "cpuCount"),
    }


def _rate(r: dict, agent_key: str, metric_key: str) -> float | None:
    v = get(r, "agent", agent_key)
    return v if v is not None else get(r, "metrics", metric_key, "value")


def net_in(r: dict) -> float | None:
    return _rate(r, "netInRate", "netIn")


def net_out(r: dict) -> float | None:
    return _rate(r, "netOutRate", "netOut")


def disk_read(r: dict) -> float | None:
    return _rate(r, "diskReadRate", "diskRead")


def disk_write(r: dict) -> float | None:
    return _rate(r, "diskWriteRate", "diskWrite")


def package_updates(r: dict) -> int | None:
    if get(r, "agent", "packageUpdates", "supported") is False:
        return None
    return get(r, "agent", "packageUpdates", "pendingCount")


def verdict(r: dict) -> str:
    v = get(r, "health", "verdict")
    return v if v in VERDICTS else "unknown"


def is_online(r: dict) -> bool:
    return r.get("status") == "online"


def container_running(r: dict) -> bool:
    state = get(r, "docker", "containerState")
    return state == "running" if state else r.get("status") in ("online", "running")


def boot_time(r: dict, now: datetime) -> datetime | None:
    up = r.get("uptime")
    return now - timedelta(seconds=up) if isinstance(up, int | float) else None


def stable(prev: datetime | None, new: datetime | None, tol: int = 60):
    """Keep the previous boot time unless it moved by more than tol seconds."""
    if prev is not None and new is not None and abs((new - prev).total_seconds()) < tol:
        return prev
    return new


def alert_count(data: dict) -> int:
    return len(data.get("alerts") or [])


def unacked_count(data: dict) -> int:
    return sum(1 for a in data.get("alerts") or [] if not a.get("acknowledged"))


def alert_attrs(data: dict) -> dict:
    return {
        "unacknowledged": unacked_count(data),
        "alerts": [
            {
                "level": a.get("level"),
                "message": a.get("message"),
                "resource": a.get("resourceName"),
            }
            for a in data.get("alerts") or []
        ]
    }


def verdict_count(data: dict, name: str) -> int | None:
    return get(data, "summary", "verdicts", name)


def problem(data: dict) -> bool:
    return unacked_count(data) > 0 or (verdict_count(data, "critical") or 0) > 0
