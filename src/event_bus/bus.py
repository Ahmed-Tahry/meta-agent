import asyncio
from typing import Any


class EventBus:
    def __init__(self) -> None:
        self._queues: dict[str, asyncio.Queue] = {}

    def emit(self, task_id: str, event: str, data: dict[str, Any]) -> None:
        queue = self._queues.get(task_id)
        if queue:
            queue.put_nowait({"event": event, "data": data})

    def subscribe(self, task_id: str) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue()
        self._queues[task_id] = queue
        return queue

    def unsubscribe(self, task_id: str) -> None:
        self._queues.pop(task_id, None)


event_bus = EventBus()
