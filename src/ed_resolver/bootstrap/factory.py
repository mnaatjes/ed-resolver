"""Composition root factory initializing and wiring ed-resolver subsystems."""

from __future__ import annotations

from ed_resolver.adapters.driven.ingress.memory import MemoryQueueAdapter
from ed_resolver.adapters.driven.runtime.deserializer import TelemetryPayloadDeserializer
from ed_resolver.adapters.driven.runtime.quarantine import QuarantineDeadLetterQueue
from ed_resolver.adapters.driven.runtime.worker import TelemetryIngressWorker
from ed_resolver.adapters.driven.state_store import InMemoryDomainStateStore
from ed_resolver.adapters.driving.facade import AmbientTelemetryFacade
from ed_resolver.core.domain.classification.classifier import IngressClassifier
from ed_resolver.core.ports.ingress import TelemetryIngressPort
from ed_resolver.core.use_cases import ProcessTelemetryReductionUseCase


def create_resolver(
    ingress_port: TelemetryIngressPort | None = None,
    state_store: InMemoryDomainStateStore | None = None,
    quarantine_capacity: int = 100,
) -> AmbientTelemetryFacade:
    """Creates a fully configured AmbientTelemetryFacade wired to an ingress worker."""
    store = state_store or InMemoryDomainStateStore()
    port = ingress_port or MemoryQueueAdapter()

    use_case = ProcessTelemetryReductionUseCase(reader=store, writer=store)
    classifier = IngressClassifier()
    deserializer = TelemetryPayloadDeserializer()
    quarantine = QuarantineDeadLetterQueue(max_capacity=quarantine_capacity)

    worker = TelemetryIngressWorker(
        ingress_port=port,
        classifier=classifier,
        reducer_pipeline=use_case,
        deserializer=deserializer,
        quarantine_queue=quarantine,
    )

    return AmbientTelemetryFacade(reader=store, worker=worker)
