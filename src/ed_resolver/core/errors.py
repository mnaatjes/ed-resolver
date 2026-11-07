"""Operational exception hierarchy for ed-resolver."""

from __future__ import annotations


class TelemetryWorkerError(Exception):
    """Base exception for all worker lifecycle and operational failures."""


class WorkerAlreadyRunningError(TelemetryWorkerError):
    """Raised when start() is invoked on an active worker."""


class WorkerNotRunningError(TelemetryWorkerError):
    """Raised when an operation requires an active worker, but it is stopped."""


class WorkerLifecycleTimeoutError(TelemetryWorkerError):
    """Raised when stop() times out waiting for the background task to complete."""


class IngressPortConnectionError(TelemetryWorkerError):
    """Raised when the worker cannot connect to or initialize the IngressPort stream."""
