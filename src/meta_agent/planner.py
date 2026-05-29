import json
from typing import Any

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage

from src.config import GEMINI_API_KEY, GEMINI_MODEL
from src.types.agent_spec import AgentSpec
from src.types.task import Subtask
from src.event_bus.bus import event_bus


class Planner:
    def __init__(self) -> None:
        self._llm: ChatGoogleGenerativeAI | None = None

    def _get_llm(self) -> ChatGoogleGenerativeAI:
        if self._llm is None:
            self._llm = ChatGoogleGenerativeAI(
                model=GEMINI_MODEL,
                google_api_key=GEMINI_API_KEY,
            )
        return self._llm

    async def decompose(self, goal: str, task_id: str) -> list[Subtask]:
        event_bus.emit(task_id, "node", {"node": "planner", "status": "running"})

        prompt = f"""Decompose the following goal into a list of subtasks.
Each subtask must be assigned to one of these agent roles: researcher, coder, writer.
Return a JSON list where each item has:
- agent_id: unique identifier like "researcher_01", "coder_01", "writer_01"
- role: one of "researcher", "coder", "writer"
- goal: what this subtask should accomplish
- tools: list of tool names (available: web_search, file_reader, code_executor)
- depends_on: list of agent_ids this subtask depends on (empty list if none)
- output_format: "text" or "json"

Goal: {goal}"""

        messages = [
            SystemMessage(content="You are a task planner. Decompose goals into subtasks."),
            HumanMessage(content=prompt),
        ]

        llm = self._get_llm()
        response = await llm.ainvoke(messages)
        subtasks_data = self._parse_response(response.content)
        subtasks = []
        for i, item in enumerate(subtasks_data):
            spec = AgentSpec(
                agent_id=item.get("agent_id", f"agent_{i:02d}"),
                role=item.get("role", "researcher"),
                goal=item.get("goal", ""),
                tools=item.get("tools", []),
                constraints=item.get("constraints", ""),
                output_format=item.get("output_format", "text"),
            )
            subtask = Subtask(
                subtask_id=spec.agent_id,
                agent_spec=spec,
                depends_on=item.get("depends_on", []),
            )
            subtasks.append(subtask)

        event_bus.emit(task_id, "node", {
            "node": "planner",
            "status": "done",
            "output": [s.agent_spec.agent_id for s in subtasks],
        })
        return subtasks

    def _parse_response(self, content: str) -> list[dict[str, Any]]:
        content = content.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[-1]
            content = content.rsplit("```", 1)[0]
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            return []
