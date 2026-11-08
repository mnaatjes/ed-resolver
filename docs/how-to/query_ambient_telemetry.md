---
title: "How to Query Ambient Telemetry"
tags: ["how-to", "facade", "telemetry", "recipes"]
created_at: "2026-11-08"
last_updated_at: "2026-11-08"
---

# How to Query Ambient Telemetry

This guide provides practical recipes for using `AmbientTelemetryFacade` to inspect game state, check convenience predicates, stream events over SSE network streams, and write isolated unit tests.

---

## 1. Quick In-Memory State Inspection

Use this recipe to start the background worker in-memory, ingest an event, and read current state.

```python
import asyncio
from ed_models.events import LocationEvent
from ed_resolver.bootstrap import create_resolver


async def main() -> None:
    # 1. Initialize resolver with an in-memory queue
    facade = create_resolver()

    # 2. Start the background reduction worker
    await facade.start()

    try:
        # 3. Simulate an incoming game event
        event = LocationEvent(
            StarSystem="Sol",
            SystemAddress=10477373803,
            Docked=False,
            Body="Earth",
        )
        await facade.ingress.put(event)

        # Allow worker task loop to process the reduction
        await asyncio.sleep(0.05)

        # 4. Read ambient state via sub-facades
        loc = facade.location.current()
        print(f"Current Star System: {loc.star_system}")
        print(f"Current Body: {loc.body}")
        print(f"Is Docked: {facade.location.is_docked()}")

    finally:
        # 5. Always stop the worker before exiting
        await facade.stop()


if __name__ == "__main__":
    asyncio.run(main())
```

---

## 2. Using High-Level Macro Predicates

The root `AmbientTelemetryFacade` provides direct boolean helpers for common situational checks.

```python
from ed_resolver.bootstrap import create_resolver

facade = create_resolver()

# Macro helpers across domains:
if facade.is_in_hyperspace:
    print("Vessel is currently jumping between star systems.")

if facade.is_docked:
    print(f"Docked at station: {facade.station.current().station_name}")

if facade.is_in_danger:
    print("Commander is currently in danger or under attack!")

if facade.is_on_foot:
    print("Commander has disembarked from the ship/SRV.")
```

---

## 3. Connecting to Live SSE Network Streams

To connect to a live telemetry server (such as an `ed-telemetry` HTTP service streaming Server-Sent Events):

```python
import asyncio
from ed_resolver.adapters.driven.telemetry_ingress import EdTelemetryNetworkAdapter
from ed_resolver.bootstrap import create_resolver


async def main() -> None:
    # 1. Point the ingress adapter to the telemetry service URL
    ingress_adapter = EdTelemetryNetworkAdapter(base_url="http://localhost:8080")

    # 2. Inject adapter into composition root
    facade = create_resolver(ingress_adapter=ingress_adapter)

    # 3. Start worker and network stream
    await facade.start()
    print("Connected to live telemetry stream. Listening for game events...")

    try:
        while True:
            await asyncio.sleep(2.0)
            loc = facade.location.current()
            vessel = facade.vessel.current()
            print(f"Status update -> System: {loc.star_system} | Ship: {vessel.ship_name}")
    except KeyboardInterrupt:
        pass
    finally:
        await facade.stop()


if __name__ == "__main__":
    asyncio.run(main())
```

---

## 4. Writing Unit Tests with Test Fixtures

Use `create_resolver()` in your test suites with `pytest-asyncio` for zero-network, fast testing.

```python
import pytest
from ed_models.events import DockedEvent
from ed_resolver.bootstrap import create_resolver


@pytest.mark.asyncio
async def test_docking_state_updates():
    facade = create_resolver()
    await facade.start()

    try:
        # Ingest a docking event
        dock_event = DockedEvent(
            StarSystem="Shinrarta Dezhra",
            StationName="Jameson Memorial",
            StationType="Coriolis",
        )
        await facade.ingress.put(dock_event)

        # Wait briefly for reducer
        import asyncio
        await asyncio.sleep(0.01)

        # Assert state matches expectations
        assert facade.location.is_docked() is True
        assert facade.station.current().station_name == "Jameson Memorial"
        assert facade.is_docked is True

    finally:
        await facade.stop()
```
