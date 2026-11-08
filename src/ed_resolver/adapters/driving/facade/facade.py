"""AmbientTelemetryFacade root driving adapter."""

from __future__ import annotations

from typing import Any

from ....core.ports.driven.state_store import DomainStateReaderPort
from ...driven.runtime.worker import TelemetryIngressWorker
from .sub_facades import (
    CargoSubFacade,
    CarrierSubFacade,
    CommanderSubFacade,
    ExplorationSubFacade,
    FlightSubFacade,
    LocationSubFacade,
    PowerplaySubFacade,
    StationSubFacade,
    VesselSubFacade,
)


class AmbientTelemetryFacade:
    """Root driving adapter exposing 9 domain sub-facades and ubiquitous macro predicates."""

    def __init__(
        self,
        reader: DomainStateReaderPort,
        worker: TelemetryIngressWorker | None = None,
    ) -> None:
        self._reader = reader
        self._worker = worker

        self.location = LocationSubFacade(reader)
        self.vessel = VesselSubFacade(reader)
        self.flight = FlightSubFacade(reader)
        self.cargo = CargoSubFacade(reader)
        self.commander = CommanderSubFacade(reader)
        self.station = StationSubFacade(reader)
        self.carrier = CarrierSubFacade(reader)
        self.exploration = ExplorationSubFacade(reader)
        self.powerplay = PowerplaySubFacade(reader)

    # --- Runtime Lifecycle Management ---

    async def start(self) -> None:
        """Starts supervised telemetry ingress ingestion worker."""
        if self._worker is not None:
            await self._worker.start()

    async def stop(self, timeout: float = 5.0) -> None:
        """Signals shutdown to ingress worker and awaits loop termination."""
        if self._worker is not None:
            await self._worker.stop(timeout=timeout)

    async def __aenter__(self) -> AmbientTelemetryFacade:
        """Async context manager entry starting the worker."""
        await self.start()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        """Async context manager exit cleanly terminating the worker."""
        await self.stop()

    # --- Root Convenience Predicates ---

    def is_docked(self) -> bool:
        """Predicate: Is commander docked at a starport, outpost, or carrier."""
        return self.location.is_docked()

    def is_on_foot(self) -> bool:
        """Predicate: Is commander disembarked on foot."""
        return self.vessel.is_on_foot()

    def in_supercruise(self) -> bool:
        """Predicate: Is commander in supercruise flight."""
        return self.location.in_supercruise()

    def is_in_srv(self) -> bool:
        """Predicate: Is commander operating an SRV."""
        return self.vessel.is_in_srv()

    def is_wanted(self) -> bool:
        """Predicate: Does commander hold active bounty or wanted status."""
        return self.commander.is_wanted()
