from __future__ import annotations

import heapq
from itertools import count

from quantlab.core.event_types import Event


class EventQueue:
    def __init__(self) -> None:
        self._heap: list[tuple[str, int, Event]] = []
        self._seq = count()

    def put(self, event: Event) -> Event:
        heapq.heappush(self._heap, (event.timestamp, next(self._seq), event))
        return event

    def get(self) -> Event:
        _, _, event = heapq.heappop(self._heap)
        return event

    def clear(self) -> None:
        self._heap.clear()

    def __bool__(self) -> bool:
        return bool(self._heap)
