"""CLI driving entrypoint for ed-resolver standalone daemon and status probe."""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import signal
import sys
import threading
import urllib.error
import urllib.request
from typing import Any

from .. import __version__
from ..adapters.driven.ingress import EdTelemetryNetworkAdapter, MemoryQueueAdapter
from ..bootstrap import create_resolver
from .broadcaster import EventBroadcaster
from .server import TelemetryDaemonServer

logger = logging.getLogger("ed_resolver.daemon")


def _probe_daemon(host: str = "127.0.0.1", port: int = 8989) -> dict[str, Any] | None:
    """Probe running daemon health endpoint to retrieve status."""
    url = f"http://{host}:{port}/api/v1/health"
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=1.0) as resp:
            if resp.status == 200:
                data: dict[str, Any] = json.loads(resp.read().decode("utf-8"))
                return data
    except (urllib.error.URLError, TimeoutError, OSError):
        return None
    return None


def _query_endpoint(endpoint: str, host: str = "127.0.0.1", port: int = 8989) -> Any:
    """Query a REST endpoint on the running daemon."""
    url = f"http://{host}:{port}/api/v1/{endpoint.lstrip('/')}"
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=2.0) as resp:
        return json.loads(resp.read().decode("utf-8"))


async def _run_server_async(
    host: str,
    port: int,
    telemetry_url: str | None,
    stop_event: asyncio.Event,
) -> None:
    """Asynchronous runner managing facade lifecycle and HTTP server thread."""
    ingress_adapter = (
        EdTelemetryNetworkAdapter(base_url=telemetry_url) if telemetry_url else MemoryQueueAdapter()
    )

    facade = create_resolver(ingress_port=ingress_adapter)
    broadcaster = EventBroadcaster()

    server = TelemetryDaemonServer(
        server_address=(host, port),
        facade=facade,
        broadcaster=broadcaster,
        version=__version__,
    )

    server_thread = threading.Thread(
        target=server.serve_forever,
        daemon=True,
        name="ed-resolver-http",
    )

    logger.info("Starting ed-resolver engine and ingress worker...")
    await facade.start()

    server_thread.start()
    logger.info("ed-resolver daemon active and listening on http://%s:%d", host, port)

    await stop_event.wait()

    logger.info("Shutdown signal received. Stopping HTTP server...")
    server.is_stopping = True
    server.shutdown()
    server.server_close()

    logger.info("Stopping telemetry facade worker...")
    await facade.stop(timeout=5.0)
    logger.info("ed-resolver daemon stopped cleanly.")


def serve_command(args: argparse.Namespace) -> int:
    """Execute 'serve' CLI subcommand."""
    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    stop_event = asyncio.Event()

    def _signal_handler() -> None:
        logger.info("Interrupted by user signal.")
        loop.call_soon_threadsafe(stop_event.set)

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _signal_handler)
        except NotImplementedError:
            # On environments where add_signal_handler is not implemented (e.g. Windows)
            signal.signal(sig, lambda _s, _f: loop.call_soon_threadsafe(stop_event.set))

    try:
        loop.run_until_complete(
            _run_server_async(
                host=args.host,
                port=args.port,
                telemetry_url=args.telemetry_url,
                stop_event=stop_event,
            )
        )
        return 0
    finally:
        loop.close()


def status_command(args: argparse.Namespace) -> int:
    """Execute 'status' CLI subcommand."""
    health = _probe_daemon(host=args.host, port=args.port)
    if not health:
        print(f"Daemon offline or unreachable at http://{args.host}:{args.port}")
        return 1

    print(f"Daemon Status: {health.get('status', 'unknown').upper()}")
    print(f"Version:       {health.get('version', 'unknown')}")
    print(f"Uptime:        {health.get('uptime_seconds', 0)}s")

    try:
        location = _query_endpoint("state/location", host=args.host, port=args.port)
        vessel = _query_endpoint("state/vessel", host=args.host, port=args.port)
        predicates = _query_endpoint("predicates", host=args.host, port=args.port)

        print("\n--- Current Ambient State ---")
        print(f"Star System:   {location.get('system_name', 'Unknown')}")
        print(f"Body:          {location.get('body_name', 'None')}")
        print(f"Ship:          {vessel.get('ship_name') or vessel.get('ship_type') or 'Unknown'}")
        print(f"Docked:        {predicates.get('is_docked', False)}")
        print(f"Supercruise:   {predicates.get('in_supercruise', False)}")
        print(f"On Foot:       {predicates.get('is_on_foot', False)}")
    except Exception as e:
        print(f"\nCould not fetch full state: {e}")

    return 0


def build_parser() -> argparse.ArgumentParser:
    """Build CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="ed-resolver",
        description="Elite Dangerous Telemetry Resolver Daemon and Client",
    )
    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=f"ed-resolver {__version__}",
    )

    subparsers = parser.add_subparsers(dest="command", help="Operational commands")

    # Serve command
    serve_parser = subparsers.add_parser("serve", help="Launch standalone telemetry daemon")
    serve_parser.add_argument(
        "--host", default="127.0.0.1", help="Interface to bind (default: 127.0.0.1)"
    )
    serve_parser.add_argument(
        "-p", "--port", type=int, default=8989, help="Port to listen on (default: 8989)"
    )
    serve_parser.add_argument(
        "--telemetry-url",
        default="http://127.0.0.1:8080",
        help="Upstream ed-telemetry HTTP/SSE endpoint (default: http://127.0.0.1:8080)",
    )
    serve_parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging verbosity (default: INFO)",
    )

    # Status command
    status_parser = subparsers.add_parser("status", help="Inspect status of running daemon")
    status_parser.add_argument(
        "--host", default="127.0.0.1", help="Target daemon interface (default: 127.0.0.1)"
    )
    status_parser.add_argument(
        "-p", "--port", type=int, default=8989, help="Target daemon port (default: 8989)"
    )

    return parser


def main(args: list[str] | None = None) -> int:
    """Main CLI entrypoint."""
    parser = build_parser()
    parsed_args = parser.parse_args(args)

    if parsed_args.command == "serve":
        return serve_command(parsed_args)
    if parsed_args.command == "status":
        return status_command(parsed_args)

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
