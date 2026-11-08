"""Daemon HTTP/SSE driving adapter using Python standard library ThreadingHTTPServer."""

from __future__ import annotations

import json
import logging
import queue
import time
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from types import MappingProxyType
from typing import Any
from urllib.parse import urlparse

from ..adapters.driving.facade import AmbientTelemetryFacade
from .broadcaster import EventBroadcaster

logger = logging.getLogger(__name__)


def _to_serializable(obj: Any) -> Any:
    """Recursively converts objects, dataclasses, mappingproxies, and sets to serializable forms."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, set | frozenset):
        return list(obj)
    if isinstance(obj, MappingProxyType | dict):
        return {str(k): _to_serializable(v) for k, v in obj.items()}
    if hasattr(obj, "__dataclass_fields__"):
        return {
            field_name: _to_serializable(getattr(obj, field_name))
            for field_name in obj.__dataclass_fields__
        }
    if isinstance(obj, list | tuple):
        return [_to_serializable(item) for item in obj]
    return obj


def _json_serial(obj: Any) -> Any:
    """Fallback JSON serializer."""
    return _to_serializable(obj)


class TelemetryDaemonRequestHandler(BaseHTTPRequestHandler):
    """Request handler implementing REST query endpoints and persistent SSE streaming."""

    server: TelemetryDaemonServer  # Type hint for associated server

    def log_message(self, format: str, *args: Any) -> None:
        """Route access logs through standard logger instead of stderr."""
        logger.debug("%s - %s", self.address_string(), format % args)

    def _send_cors_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")

    def do_OPTIONS(self) -> None:
        """Handle CORS pre-flight requests."""
        self.send_response(204)
        self._send_cors_headers()
        self.end_headers()

    def do_GET(self) -> None:
        """Route GET requests to health, state, or SSE endpoints."""
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")

        if path == "/api/v1/health":
            self._handle_health()
        elif path == "/api/v1/predicates":
            self._handle_predicates()
        elif path == "/api/v1/state":
            self._handle_all_state()
        elif path.startswith("/api/v1/state/"):
            domain = path[len("/api/v1/state/") :]
            self._handle_domain_state(domain)
        elif path == "/api/v1/stream":
            self._handle_stream()
        else:
            self._send_json(
                {"error": "Endpoint not found", "path": parsed.path},
                status=404,
            )

    def _send_json(self, data: Any, status: int = 200) -> None:
        """Encode and send JSON HTTP response."""
        payload = json.dumps(data, default=_json_serial).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self._send_cors_headers()
        self.end_headers()
        self.wfile.write(payload)

    def _handle_health(self) -> None:
        """GET /api/v1/health"""
        uptime = time.time() - self.server.start_time
        self._send_json(
            {
                "status": "ok",
                "version": self.server.version,
                "timestamp": datetime.now(UTC).isoformat(),
                "uptime_seconds": round(uptime, 2),
            }
        )

    def _handle_predicates(self) -> None:
        """GET /api/v1/predicates"""
        facade = self.server.facade
        self._send_json(
            {
                "is_docked": facade.is_docked(),
                "in_supercruise": facade.in_supercruise(),
                "on_surface": facade.location.on_surface(),
                "is_on_foot": facade.is_on_foot(),
                "is_in_srv": facade.is_in_srv(),
                "is_wanted": facade.is_wanted(),
            }
        )

    def _handle_domain_state(self, domain: str) -> None:
        """GET /api/v1/state/<domain>"""
        facade = self.server.facade
        sub_facade = getattr(facade, domain, None)
        if sub_facade is None or not hasattr(sub_facade, "state"):
            self._send_json(
                {
                    "error": f"Unknown domain state '{domain}'",
                    "valid_domains": self.server.valid_domains,
                },
                status=404,
            )
            return

        state = sub_facade.state()
        self._send_json(state)

    def _handle_all_state(self) -> None:
        """GET /api/v1/state"""
        facade = self.server.facade
        all_state = {
            domain: getattr(facade, domain).state() for domain in self.server.valid_domains
        }
        self._send_json(all_state)

    def _handle_stream(self) -> None:
        """GET /api/v1/stream (SSE)"""
        broadcaster = self.server.broadcaster
        q = broadcaster.subscribe()

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self._send_cors_headers()
        self.end_headers()

        # Initial keep-alive ping
        try:
            self.wfile.write(b": keep-alive\n\n")
            self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError, OSError):
            broadcaster.unsubscribe(q)
            return

        # Set socket timeout so blocking write detects disconnects
        try:
            self.connection.settimeout(0.5)
        except OSError:
            pass

        try:
            while not self.server.is_stopping:
                try:
                    payload = q.get(timeout=0.1)
                    data_str = json.dumps(payload, default=_json_serial)
                    msg = f"event: state_update\ndata: {data_str}\n\n".encode()
                    self.wfile.write(msg)
                    self.wfile.flush()
                except queue.Empty:
                    # Write ping to detect dead client connections quickly
                    self.wfile.write(b": keep-alive\n\n")
                    self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError, OSError, TimeoutError):
            pass
        finally:
            broadcaster.unsubscribe(q)


class TelemetryDaemonServer(ThreadingHTTPServer):
    """Threading HTTP server subclass holding facade and broadcaster references."""

    daemon_threads = True

    def __init__(
        self,
        server_address: tuple[str, int],
        facade: AmbientTelemetryFacade,
        broadcaster: EventBroadcaster,
        version: str = "0.1.0",
    ) -> None:
        super().__init__(server_address, TelemetryDaemonRequestHandler)
        self.facade = facade
        self.broadcaster = broadcaster
        self.version = version
        self.start_time = time.time()
        self.is_stopping = False
        self.valid_domains = [
            "location",
            "vessel",
            "flight",
            "cargo",
            "commander",
            "station",
            "carrier",
            "exploration",
            "powerplay",
        ]
