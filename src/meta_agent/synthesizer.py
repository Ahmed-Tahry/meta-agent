from typing import Any

from src.event_bus.bus import event_bus
from src.shared_state.redis_store import store


class Synthesizer:
    async def synthesize(self, task_id: str, subtask_outputs: dict[str, Any]) -> str:
        parts = []
        for agent_id, output in subtask_outputs.items():
            parts.append(f"## {agent_id}\n{output}")

        result = "\n\n".join(parts)
        await store.set_result(task_id, result)

        event_bus.emit(task_id, "complete", {"result": result})
        return result
