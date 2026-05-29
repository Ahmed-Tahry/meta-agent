from typing import Any

from src.event_bus.bus import event_bus


class Evaluator:
    async def evaluate(self, task_id: str, subtask_id: str, output: Any) -> bool:
        if output is None or (isinstance(output, str) and not output.strip()):
            event_bus.emit(task_id, "error", {
                "subtask_id": subtask_id,
                "message": "Output is empty",
            })
            return False
        return True
