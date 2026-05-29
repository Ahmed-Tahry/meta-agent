import pytest
from unittest.mock import AsyncMock, patch

from src.event_bus.bus import EventBus


@pytest.fixture
def bus():
    return EventBus()


class TestEventBus:
    def test_subscribe_returns_queue(self, bus):
        queue = bus.subscribe("task_01")
        assert queue is not None

    def test_emit_puts_event_in_queue(self, bus):
        queue = bus.subscribe("task_01")
        bus.emit("task_01", "status", {"status": "running"})
        msg = queue.get_nowait()
        assert msg["event"] == "status"
        assert msg["data"] == {"status": "running"}

    def test_emit_no_queue_no_error(self, bus):
        bus.emit("nonexistent", "status", {"status": "done"})

    def test_multiple_events(self, bus):
        queue = bus.subscribe("task_01")
        bus.emit("task_01", "node", {"node": "planner"})
        bus.emit("task_01", "node", {"node": "executor"})
        msg1 = queue.get_nowait()
        msg2 = queue.get_nowait()
        assert msg1["data"]["node"] == "planner"
        assert msg2["data"]["node"] == "executor"

    def test_unsubscribe_removes_queue(self, bus):
        bus.subscribe("task_01")
        assert "task_01" in bus._queues
        bus.unsubscribe("task_01")
        assert "task_01" not in bus._queues

    def test_emit_after_unsubscribe_no_error(self, bus):
        bus.subscribe("task_01")
        bus.unsubscribe("task_01")
        bus.emit("task_01", "status", {"status": "done"})

    def test_multiple_subscribers_independent(self, bus):
        q1 = bus.subscribe("task_01")
        q2 = bus.subscribe("task_02")
        bus.emit("task_01", "status", {"status": "running"})
        assert q1.qsize() == 1
        assert q2.qsize() == 0
