from typing import Any

from src.event_bus.bus import event_bus
from src.tools import Tool


class Agent:
    def __init__(
        self,
        agent_id: str,
        system_prompt: str,
        tools: list[Tool],
    ) -> None:
        self.agent_id = agent_id
        self.system_prompt = system_prompt
        self.tools = tools
        self.messages: list[dict[str, Any]] = []

    async def run(self, task_id: str, goal: str, shared_state: dict[str, Any]) -> str:
        event_bus.emit(task_id, "subtask", {"agent_id": self.agent_id, "status": "running"})

        tool_descriptions = "\n".join(f"- {t.name}: {t.description}" for t in self.tools)
        prompt = f"{self.system_prompt}\n\nGoal: {goal}\n\nTools available:\n{tool_descriptions}"
        self.messages.append({"role": "user", "content": prompt})

        result = self._execute(task_id, goal)

        event_bus.emit(task_id, "subtask", {
            "agent_id": self.agent_id,
            "status": "done",
            "summary": {"output": result},
        })
        return result

    def _execute(self, task_id: str, goal: str) -> str:
        return f"[{self.agent_id}] Processed: {goal}"
