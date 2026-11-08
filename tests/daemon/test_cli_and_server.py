"""Comprehensive integration tests for the ed-resolver thin CLI and daemon HTTP/SSE server."""

from __future__ import annotations

import asyncio
import json
import threading
import time
import urllib.request
from typing import Any

import pytest

from ed_resolver import __version__
from ed_resolver.adapters.driven.ingress import MemoryQueueAdapter
from ed_resolver.bootstrap import create_resolver
from ed_resolver.daemon.broadcaster import EventBroadcaster
from ed_resolver.daemon.cli import build_parser, main
from ed_resolver.daemon.server import TelemetryDaemonServer


@pytest.fixture
def test_port() -> int:
    """Provide dynamic local port for test isolation."""
    import socket

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


@pytest.fixture
def running_daemon(test_port: int):
    """Fixture initializing in-memory facade and background TelemetryDaemonServer."""
    queue_adapter = MemoryQueueAdapter()
    facade = create_resolver(ingress_port=queue_adapter)
    broadcaster = EventBroadcaster()

    server = TelemetryDaemonServer(
        server_address=("127.0.0.1", test_port),
        facade=facade,
        broadcaster=broadcaster,
        version=__version__,
    )

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    yield {
        "port": test_port,
        "server": server,
        "facade": facade,
        "broadcaster": broadcaster,
        "ingress": queue_adapter,
    }

    server.is_stopping = True
    server.shutdown()
    server.server_close()


def _get(port: int, path: str) -> tuple[int, dict[str, Any]]:
    """Helper to perform HTTP GET request against test daemon."""
    url = f"http://127.0.0.1:{port}{path}"
    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=2.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return resp.status, data
    except urllib.error.HTTPError as e:
        data = json.loads(e.read().decode("utf-8"))
        return e.code, data


def test_cli_parser():
    """Verify CLI parser options and default values."""
    parser = build_parser()
    args = parser.parse_args(["serve", "--port", "9090", "--log-level", "DEBUG"])
    assert args.command == "serve"
    assert args.port == 9090
    assert args.log_level == "DEBUG"

    status_args = parser.parse_args(["status", "--port", "9090"])
    assert status_args.command == "status"
    assert status_args.port == 9090


def test_health_endpoint(running_daemon: dict[str, Any]):
    """Verify GET /api/v1/health returns ok status and version."""
    port = running_daemon["port"]
    status, data = _get(port, "/api/v1/health")

    assert status == 200
    assert data["status"] == "ok"
    assert data["version"] == __version__
    assert "uptime_seconds" in data
    assert "timestamp" in data


def test_predicates_endpoint(running_daemon: dict[str, Any]):
    """Verify GET /api/v1/predicates returns macro predicate map."""
    port = running_daemon["port"]
    status, data = _get(port, "/api/v1/predicates")

    assert status == 200
    assert data["is_docked"] is False
    assert data["in_supercruise"] is False
    assert data["is_on_foot"] is False


def test_domain_state_endpoints(running_daemon: dict[str, Any]):
    """Verify GET /api/v1/state/<domain> endpoints return state models."""
    port = running_daemon["port"]

    # Verify initial empty location
    status, data = _get(port, "/api/v1/state/location")
    assert status == 200
    assert data["system_name"] is None

    # Test all 9 domains
    for domain in [
        "location",
        "vessel",
        "flight",
        "cargo",
        "commander",
        "station",
        "carrier",
        "exploration",
        "powerplay",
    ]:
        status, data = _get(port, f"/api/v1/state/{domain}")
        assert status == 200, f"Domain {domain} failed"
        assert isinstance(data, dict)

    # Test consolidated state
    status, all_data = _get(port, "/api/v1/state")
    assert status == 200
    assert len(all_data) == 9
    assert "vessel" in all_data
    assert "cargo" in all_data


def test_unknown_endpoint_404(running_daemon: dict[str, Any]):
    """Verify invalid paths return 404 with structured JSON."""
    port = running_daemon["port"]
    status, data = _get(port, "/api/v1/unknown")
    assert status == 404
    assert "error" in data

    status, domain_err = _get(port, "/api/v1/state/not_a_domain")
    assert status == 404
    assert "Unknown domain state" in domain_err["error"]


@pytest.mark.asyncio
async def test_state_mutation_via_ingress(running_daemon: dict[str, Any]):
    """Verify that ingesting an event mutates state reflected across REST endpoints."""
    port = running_daemon["port"]
    facade = running_daemon["facade"]
    ingress = running_daemon["ingress"]

    await facade.start()

    try:
        # Push a location event using RawTelemetryEnvelope
        from datetime import datetime

        from ed_resolver.core.ports.envelope import RawTelemetryEnvelope

        payload = (
            '{"timestamp": "2026-11-08T02:00:00Z", "event": "Location", '
            '"StarSystem": "Achenar", "SystemAddress": 987654321, '
            '"Docked": true, "StationName": "Dawes Hub", "StationType": "Coriolis"}'
        )
        await ingress.put(RawTelemetryEnvelope(raw_payload=payload, received_at=datetime.now()))

        # Allow worker processing
        await asyncio.sleep(0.1)

        # Check location state endpoint
        status, loc_data = _get(port, "/api/v1/state/location")
        assert status == 200
        assert loc_data["system_name"] == "Achenar"
        assert loc_data["docked"] is True

        # Check predicates endpoint
        status, pred_data = _get(port, "/api/v1/predicates")
        assert status == 200
        assert pred_data["is_docked"] is True

    finally:
        await facade.stop()


def test_sse_stream_subscription(running_daemon: dict[str, Any]):
    """Verify GET /api/v1/stream delivers SSE initial keepalive comment."""
    port = running_daemon["port"]
    broadcaster: EventBroadcaster = running_daemon["broadcaster"]

    url = f"http://127.0.0.1:{port}/api/v1/stream"
    req = urllib.request.Request(url, method="GET")
    resp = urllib.request.urlopen(req, timeout=2.0)

    try:
        assert resp.status == 200
        assert resp.headers.get("Content-Type") == "text/event-stream"
        assert broadcaster.subscriber_count == 1

        # Read initial line
        line = resp.readline().decode("utf-8")
        assert ": keep-alive" in line

    finally:
        resp.close()
        # Broadcast multiple times with small delays to ensure socket write triggers disconnect
        for _ in range(5):
            broadcaster.broadcast({"type": "ping"})
            time.sleep(0.05)
            if broadcaster.subscriber_count == 0:
                break
        assert broadcaster.subscriber_count == 0


def test_cli_status_command(running_daemon: dict[str, Any], capsys: pytest.CaptureFixture[str]):
    """Verify 'status' CLI command connects and formats output."""
    port = running_daemon["port"]
    code = main(["status", "--port", str(port)])
    assert code == 0

    captured = capsys.readouterr().out
    assert "Daemon Status: OK" in captured
    assert "Version:" in captured
    assert "Star System:" in captured
