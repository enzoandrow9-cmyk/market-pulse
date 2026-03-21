from __future__ import annotations

from collections import defaultdict
from typing import Callable

from quantlab.core.event_queue import EventQueue
from quantlab.core.event_types import Event, EventType


Handler = Callable[[Event], None]


class EventEngine:
    def __init__(self) -> None:
        self.queue = EventQueue()
        self._handlers: dict[EventType, list[Handler]] = defaultdict(list)

    def register(self, event_type: EventType, handler: Handler) -> None:
        self._handlers[event_type].append(handler)

    def put(self, event: Event) -> Event:
        return self.queue.put(event)

    def run(self) -> None:
        while self.queue:
            event = self.queue.get()
            for handler in self._handlers.get(event.event_type, []):
                handler(event)
