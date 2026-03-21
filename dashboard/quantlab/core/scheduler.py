from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass(order=True)
class ScheduledTask:
    timestamp: str
    name: str
    callback: Callable[..., Any] = field(compare=False)
    payload: dict[str, Any] = field(default_factory=dict, compare=False)


class Scheduler:
    def __init__(self) -> None:
        self._tasks: list[ScheduledTask] = []

    def add(self, task: ScheduledTask) -> None:
        self._tasks.append(task)
        self._tasks.sort(key=lambda item: (item.timestamp, item.name))

    def run_due(self, timestamp: str) -> list[Any]:
        completed: list[Any] = []
        pending: list[ScheduledTask] = []
        for task in self._tasks:
            if task.timestamp <= timestamp:
                completed.append(task.callback(**task.payload))
            else:
                pending.append(task)
        self._tasks = pending
        return completed
