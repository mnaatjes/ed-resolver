"""In-memory test doubles for DomainStateReaderPort and DomainStateWriterPort."""

from __future__ import annotations

from ed_resolver.adapters.driven.state_store import InMemoryDomainStateStore


class FakeDomainStateReaderAdapter(InMemoryDomainStateStore):
    """Test double satisfying FakeDomainStateReaderAdapter double parity."""


class FakeDomainStateWriterAdapter(InMemoryDomainStateStore):
    """Test double satisfying FakeDomainStateWriterAdapter double parity."""
