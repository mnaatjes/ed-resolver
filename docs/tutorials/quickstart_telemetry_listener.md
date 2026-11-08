---
title: "Quickstart: Building a Live Telemetry Listener"
tags: ["tutorial", "quickstart", "sse", "copilot"]
created_at: "2026-11-08"
last_updated_at: "2026-11-08"
---

# Quickstart: Building a Live Telemetry Listener

In this tutorial, you will build an event-driven status monitor using `ed-resolver`. The monitor connects to game telemetry, tracks hyperspace transitions, and reports docking events as they happen in real time.

---

## What You Will Build

A Python script that:

1. Connects to Elite Dangerous ambient telemetry.
2. Runs a background loop that monitors ship status.
3. Automatically prints notifications whenever your ship jumps to a new star system or docks at a station.

---

## Step 1: Set Up the Environment

Create a project directory and virtual environment:

```bash
mkdir ed-copilot
cd ed-copilot
uv venv
source .venv/bin/activate
uv add git+https://github.com/mnaatjes/ed-resolver.git
```

---

## Step 2: Write the Monitor Script

Create a file named `listener.py`:

```python
"""Live telemetry status listener using ed-resolver."""

import asyncio
from ed_resolver.adapters.driven.telemetry_ingress import EdTelemetryNetworkAdapter
from ed_resolver.bootstrap import create_resolver


async def monitor_status() -> None:
    # 1. Connect to local telemetry server (or use in-memory resolver without arguments)
    ingress = EdTelemetryNetworkAdapter(base_url="http://localhost:8080")
    facade = create_resolver(ingress_adapter=ingress)

    # 2. Start telemetry ingestion
    print("Initializing ed-resolver...")
    await facade.start()
    print("Telemetry stream active. Listening for events... (Press Ctrl+C to stop)")

    last_system = None
    last_docked_state = None

    try:
        while True:
            # Poll current ambient state
            loc = facade.location.current()
            station = facade.station.current()

            # Detect system transitions
            if loc.star_system and loc.star_system != last_system:
                print(f"[SYSTEM JUMP] Entered system: {loc.star_system} ({loc.security or 'Unknown'})")
                last_system = loc.star_system

            # Detect docking state changes
            if loc.docked != last_docked_state:
                if loc.docked:
                    print(f"[DOCKED] Docked at {station.station_name} ({station.station_type or 'Outpost'})")
                elif last_docked_state is not None:
                    print("[UNDOCKED] Ship has cleared station airlock.")
                last_docked_state = loc.docked

            # Throttle poll rate
            await asyncio.sleep(0.5)

    except asyncio.CancelledError:
        pass
    finally:
        print("\nStopping resolver worker...")
        await facade.stop()
        print("Resolver shut down cleanly.")


if __name__ == "__main__":
    try:
        asyncio.run(monitor_status())
    except KeyboardInterrupt:
        print("\nExiting listener.")
```

---

## Step 3: Run the Script

Run the monitor:

```bash
python listener.py
```

Sample output:

```text
Initializing ed-resolver...
Telemetry stream active. Listening for events... (Press Ctrl+C to stop)
[SYSTEM JUMP] Entered system: Shinrarta Dezhra (High Security)
[DOCKED] Docked at Jameson Memorial (Coriolis)
[UNDOCKED] Ship has cleared station airlock.
```

---

## Next Steps

- Explore the complete list of available sub-facades in the [API Reference Guide](../reference/facade_api.md).
- Check [How to Query Ambient Telemetry](../how-to/query_ambient_telemetry.md) for custom unit test recipes.
