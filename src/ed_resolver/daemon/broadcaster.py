"""Broadcaster hub for real-time SSE telemetry updates."""

from __future__ import annotations

import queue
import threading
from typing import Any


class EventBroadcaster:
    """Thread-safe event broadcast hub maintaining active subscriber queues."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._subscribers: set[queue.Queue[dict[str, Any]]] = set()

    def subscribe(self) -> queue.Queue[dict[str, Any]]:
        """Registers a new subscriber queue."""
        q: queue.Queue[dict[str, Any]] = queue.Queue(maxsize=100)
        with self._lock:
            self._subscribers.add(q)
        return q

    def unsubscribe(self, q: queue.Queue[dict[str, Any]]) -> None:
        """Removes a subscriber queue."""
        with self._lock:
            self._subscribers.discard(q)

    def broadcast(self, payload: dict[str, Any]) -> None:
        """Publishes an event payload to all active subscriber queues."""
        with self._lock:
            subscribers = list(self._subscribers)

        for q in subscribers:
            try:
                q.put_nowait(payload)
            except queue.Full:
                # Discard slow subscriber frame to avoid blocking
                pass

    @property
    def subscriber_count(self) -> int:
        """Returns the number of active subscribers."""
        with self._lock:
            return len(self._subscribers)
