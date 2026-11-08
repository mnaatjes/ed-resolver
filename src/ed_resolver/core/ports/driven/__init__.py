"""Driven (outbound / secondary) port contracts."""

from .state_store import DomainStateReaderPort, DomainStateWriterPort

__all__ = [
    "DomainStateReaderPort",
    "DomainStateWriterPort",
]
