import json
import re
from typing import Any

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage

from src.config import GEMINI_API_KEY, GEMINI_MODEL, LLM_TIMEOUT
from src.types.agent_spec import AgentSpec
from src.types.task import Subtask
from src.event_bus.bus import event_bus
from src.shared_state.redis_store import store
from src.task_logger import get_logger


class Planner:
    def __init__(self) -> None:
        self._llm: ChatGoogleGenerativeAI | None = None

    def _get_llm(self) -> ChatGoogleGenerativeAI:
        if self._llm is None:
            self._llm = ChatGoogleGenerativeAI(
                model=GEMINI_MODEL,
                google_api_key=GEMINI_API_KEY,
                timeout=LLM_TIMEOUT,
            )
        return self._llm

    async def decompose(self, goal: str, task_id: str) -> list[Subtask]:
        log = get_logger(task_id)
        event_bus.emit(task_id, "node", {"node": "planner", "status": "running"})

        log.log("PLANNER", "Calling Gemini to decompose goal", f"model={GEMINI_MODEL}")

        prompt = f"""Decompose the following goal into a list of subtasks.
Each subtask must be assigned to one of these agent roles: researcher, coder, writer.
Pre-built tools available: web_search, file_reader, code_executor.
If a subtask requires a capability none of the pre-built tools provide, define a new custom tool 
with a unique name and a clear description of what it should do in tool_definitions.

CRITICAL: Your entire response must be ONLY a valid JSON array. No markdown formatting, no code fences, no explanations, no preamble, no postscript. Start with '[' and end with ']'.

Each item in the array has:
- agent_id: unique identifier like "researcher_01", "coder_01", "writer_01"
- role: one of "researcher", "coder", "writer"
- goal: what this subtask should accomplish
- tools: list of tool names (pre-built + custom tool names you define)
- tool_definitions: object mapping custom tool names to their goals (e.g. {{"my_tool": "what my_tool does"}})
- depends_on: list of agent_ids this subtask depends on (empty list if none)
- output_format: "text" or "json"

Goal: {goal}"""

        log.log_multiline("PLANNER", "Prompt sent to Gemini:", prompt)
        await store.append_trace(task_id, {"type": "planner_prompt", "prompt": prompt})

        messages = [
            SystemMessage(content="You are a task planner. Decompose goals into subtasks."),
            HumanMessage(content=prompt),
        ]

        llm = self._get_llm()
        response = await llm.ainvoke(messages)
        raw = response.content if isinstance(response.content, str) else str(response.content)

        log.log_multiline("PLANNER", "Raw response from Gemini:", raw)
        await store.append_trace(task_id, {"type": "planner_response", "response": raw})

        subtasks_data = self._parse_response(raw)
        if not subtasks_data:
            log.log("PLANNER", "Failed to parse Gemini response as JSON",
                f"response preview: {raw[:300]}")
            event_bus.emit(task_id, "error", {
                "node": "planner",
                "message": "Failed to parse planner JSON output",
                "raw": raw,
            })
        else:
            log.log("PLANNER", f"Parsed {len(subtasks_data)} subtask(s) from JSON")

        subtasks = []
        for i, item in enumerate(subtasks_data):
            spec = AgentSpec(
                agent_id=item.get("agent_id", f"agent_{i:02d}"),
                role=item.get("role", "researcher"),
                goal=item.get("goal", ""),
                tools=item.get("tools", []),
                tool_definitions=item.get("tool_definitions", {}),
                constraints=item.get("constraints", ""),
                output_format=item.get("output_format", "text"),
            )
            subtask = Subtask(
                subtask_id=spec.agent_id,
                agent_spec=spec,
                depends_on=item.get("depends_on", []),
            )
            subtasks.append(subtask)

        plan_detail = "\n".join(
            f"  [{s.subtask_id}] role={s.agent_spec.role}  goal={s.agent_spec.goal}  "
            f"tools={s.agent_spec.tools}  output_format={s.agent_spec.output_format}"
            for s in subtasks
        ) if subtasks else "  (no subtasks)"
        log.log_multiline("PLANNER", f"Final plan ({len(subtasks)} subtasks):", plan_detail)

        await store.append_trace(task_id, {
            "type": "plan",
            "subtasks": [{"agent_id": s.agent_spec.agent_id, "goal": s.agent_spec.goal, "depends_on": s.depends_on} for s in subtasks],
        })

        event_bus.emit(task_id, "node", {
            "node": "planner",
            "status": "done",
            "output": [s.agent_spec.agent_id for s in subtasks],
        })
        return subtasks

    def _parse_response(self, content: str) -> list[dict[str, Any]]:
        raw = content.strip()

        for attempt in self._extract_candidates(raw):
            try:
                parsed = json.loads(attempt)
                if isinstance(parsed, list):
                    return parsed
            except json.JSONDecodeError:
                continue

        return []

    def _extract_candidates(self, content: str) -> list[str]:
        candidates = []

        # 1) code fence block
        m = re.search(r'```(?:json)?\s*(.*?)```', content, re.DOTALL)
        if m:
            candidates.append(m.group(1).strip())

        # 2) bracket-balanced [ … ] extraction
        start = content.find('[')
        if start != -1:
            depth = 0
            for i, ch in enumerate(content[start:], start):
                if ch == '[':
                    depth += 1
                elif ch == ']':
                    depth -= 1
                    if depth == 0:
                        candidates.append(content[start:i + 1])
                        break

        # 3) whole string as fallback
        candidates.append(content)

        # 4) unwrap {"key": [...]} if Gemini returns an object
        for attempt in candidates[:]:
            try:
                obj = json.loads(attempt)
                if isinstance(obj, dict):
                    lists = [v for v in obj.values() if isinstance(v, list)]
                    if len(lists) == 1:
                        candidates.append(json.dumps(lists[0]))
            except (json.JSONDecodeError, Exception):
                pass

        return candidates