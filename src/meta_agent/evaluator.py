from typing import Any

from src.event_bus.bus import event_bus
from src.task_logger import get_logger


class Evaluator:
    async def evaluate(self, task_id: str, subtask_id: str, output: Any) -> bool:
        log = get_logger(task_id)

        if output is None or (isinstance(output, str) and not output.strip()):
            log.log("EVALUATOR", f"Subtask {subtask_id} FAILED — output is None or empty")
            event_bus.emit(task_id, "error", {
                "subtask_id": subtask_id,
                "message": "Output is empty",
            })
            return False

        log.log("EVALUATOR", f"Subtask {subtask_id} PASSED evaluation",
            f"output length: {len(str(output))} chars")
        return True
