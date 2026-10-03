"""Run: python3 tests/test_values.py (helpers.py has no Home Assistant imports)."""

import importlib.util
from datetime import datetime, timedelta, timezone
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "helpers",
    Path(__file__).parent.parent / "custom_components/pulse_monitor/helpers.py",
)
h = importlib.util.module_from_spec(spec)
spec.loader.exec_module(h)

# Shapes of /api/resources, /api/state/summary, /api/alerts/active; names/ids are fictional.
AGENT = {
    "id": "agent-0000000000000001",
    "name": "vps-example",
    "canonicalIdentity": {"displayName": "VPS"},
    "status": "online",
    "uptime": 4189128,
    "health": {"verdict": "ok", "reasons": []},
    "metrics": {
        "cpu": {"percent": 23.2},
        "memory": {"used": 6228848640, "total": 8324337664, "percent": 74.8},
        "disk": {"used": 127059587072, "percent": -1},
        "netIn": {"value": 640889.2},
        "diskRead": {"value": 1650503.8},
    },
    "agent": {
        "loadAverage": [0.45, 0.64, 0.63],
        "netInRate": 640000.0,
        "packageUpdates": {"supported": True, "pendingCount": 3},
    },
}
ROUTER = {
    "id": "agent-0000000000000002",
    "name": "router-example",
    "status": "online",
    "metrics": {"netOut": {"value": 193764.4}},
    "agent": {"packageUpdates": {"supported": False, "pendingCount": 0}},
}
CONTAINER = {
    "id": "app-container-0000000000000001",
    "name": "apprise",
    "status": "online",
    "parentId": AGENT["id"],
    "docker": {"containerState": "running"},
    "metrics": {"cpu": {"percent": 0.05}, "memory": {"percent": 11.0}},
}
SUMMARY = {
    "activeAlerts": 1,
    "verdicts": {"ok": 268, "attention": 0, "critical": 0, "stale": 0, "off": 0, "unknown": 17},
}
ALERT = {
    "level": "critical",
    "message": "CPU usage is critical at 95%",
    "resourceName": "vps-example",
    "acknowledged": True,
}

assert h.display_name(AGENT) == "VPS" and h.display_name(ROUTER) == "router-example"
assert h.cpu(AGENT) == 23.2 and h.mem_pct(AGENT) == 74.8
assert h.mem_used(AGENT) == 6228848640 and h.disk_used(AGENT) == 127059587072
assert h.disk_pct(AGENT) is None  # -1 sentinel
AGENT["agent"]["cpuCount"] = 4
assert h.load_pct(AGENT) == 11.2  # 0.45 / 4 cores
assert h.load_pct(ROUTER) is None
assert h.load_pct({"agent": {"cpuCount": 0, "loadAverage": [1]}}) is None
assert h.load_attrs(AGENT) == {"load_1m": 0.45, "load_5m": 0.64, "load_15m": 0.63, "cpu_count": 4}
assert h.load_attrs(ROUTER)["load_5m"] is None
assert h.net_in(AGENT) == 640000.0  # agent field wins over metrics
assert h.net_out(ROUTER) == 193764.4  # falls back to metrics
assert h.disk_read(AGENT) == 1650503.8 and h.disk_read(ROUTER) is None
assert h.package_updates(AGENT) == 3 and h.package_updates(ROUTER) is None
assert h.verdict(AGENT) == "ok" and h.verdict(ROUTER) == "unknown"
assert h.verdict({"health": {"verdict": "bogus"}}) == "unknown"
assert h.is_online(AGENT) and not h.is_online({"status": "offline"})
assert h.container_running(CONTAINER)
assert not h.container_running({"docker": {"containerState": "exited"}, "status": "online"})
assert h.container_running({"status": "online"})
assert h.cpu(CONTAINER) == 0.05
assert h.container_key(CONTAINER) == "apprise"  # name, not the volatile id
assert h.container_key({**CONTAINER, "id": "app-container-new"}) == "apprise"
assert h.container_key({"id": "x"}) == "x"
LABELED = {
    "id": "app-container-1",
    "name": "quickwit-otel-collector-abc123",
    "status": "online",
    "docker": {
        "containerState": "running",
        "health": "healthy",
        "image": "otel/collector:1.0",
        "oomKilled": False,
        "startedAt": "2026-09-28T23:34:50.535979761Z",
        "labels": {
            "coolify.serviceName": "quickwit-otel-collector",
            "coolify.projectName": "core",
            "coolify.resourceName": "quickwit",
        },
        "updateStatus": {"updateAvailable": True, "lastChecked": "x"},
    },
    "metrics": {"memory": {"used": 100}, "netIn": {"value": 5.0}},
}
assert h.container_key(LABELED) == "quickwit-otel-collector"  # label beats name
assert h.container_attrs(LABELED) == {
    "image": "otel/collector:1.0", "project": "core", "resource": "quickwit",
}
assert h.container_health(LABELED) == "healthy" and h.container_health(CONTAINER) == "none"
assert h.update_available(LABELED) is True and h.update_available(CONTAINER) is None
errored = {"docker": {"updateStatus": {"updateAvailable": True, "error": "boom"}}}
assert h.update_available(errored) is None
assert h.oom_killed(LABELED) is False and h.oom_killed(CONTAINER) is False
assert h.started(LABELED) == datetime(2026, 9, 28, 23, 34, 50, 535979, tzinfo=timezone.utc)
assert h.started(CONTAINER) is None
assert h.mem_used(LABELED) == 100 and h.net_in(LABELED) == 5.0
fleet = {"containers": {"a": LABELED, "b": {**CONTAINER, "docker": {"containerState": "exited", "health": "unhealthy"}}}}
assert h.containers_running(fleet) == 1 and h.containers_unhealthy(fleet) == 1
assert h.container_updates(fleet) == 1
assert h.container_update_attrs(fleet) == {"containers": ["a"]}

now = datetime(2026, 10, 3, tzinfo=timezone.utc)
boot = h.boot_time(AGENT, now)
assert boot == now - timedelta(seconds=4189128) and h.boot_time(ROUTER, now) is None
assert h.stable(boot, boot + timedelta(seconds=30)) == boot  # jitter held
assert h.stable(boot, boot + timedelta(hours=1)) == boot + timedelta(hours=1)  # reboot
assert h.stable(None, boot) == boot

data = {"summary": SUMMARY, "alerts": [ALERT]}
assert h.alert_count(data) == 1 and h.alert_count({"alerts": []}) == 0
assert h.alert_attrs(data)["alerts"][0] == {
    "level": "critical", "message": ALERT["message"], "resource": ALERT["resourceName"],
}
assert h.alert_attrs(data)["unacknowledged"] == 0 and h.unacked_count(data) == 0
unacked = {"summary": SUMMARY, "alerts": [{**ALERT, "acknowledged": False}]}
assert h.unacked_count(unacked) == 1 and h.problem(unacked)
assert [h.verdict_count(data, v) for v in h.VERDICTS] == [268, 0, 0, 0, 0, 17]
assert not h.problem(data) and not h.problem({"summary": SUMMARY, "alerts": []})
assert h.problem({"summary": {"verdicts": {"critical": 2}}, "alerts": []})

live = {"agents": {"agent-1": {}}, "containers": {"apprise": {}}}


def stale(ids):
    return h.is_stale(ids, live, "entry", "pulse_monitor")


assert not stale({("pulse_monitor", "agent-1")}) and not stale({("pulse_monitor", "apprise")})
assert not stale({("pulse_monitor", "entry")})
assert stale({("pulse_monitor", "app-container-old")}) and stale({("other", "apprise")})

print("ok")
