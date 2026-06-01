from typing import Any

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage

from src.config import GEMINI_API_KEY, GEMINI_MODEL, LLM_TIMEOUT
from src.event_bus.bus import event_bus
from src.shared_state.redis_store import store


class Synthesizer:
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

    async def synthesize(self, task_id: str, subtask_outputs: dict[str, Any]) -> str:
        if not subtask_outputs:
            result = ""
            await store.set_result(task_id, result)
            event_bus.emit(task_id, "complete", {"result": result})
            return result

        try:
            result = await self._llm_synthesize(subtask_outputs)
        except Exception:
            result = self._fallback_synthesize(subtask_outputs)

        await store.set_result(task_id, result)
        event_bus.emit(task_id, "complete", {"result": result})
        return result

    async def _llm_synthesize(self, subtask_outputs: dict[str, Any]) -> str:
        parts = []
        for agent_id, output in subtask_outputs.items():
            parts.append(f"## {agent_id}\n{output}")

        prompt = (
            "Synthesize the following agent outputs into a coherent final response.\n"
            "Merge findings, remove redundancy, and present a well-structured summary.\n\n"
            + "\n\n".join(parts)
        )

        messages = [
            SystemMessage(content="You are a synthesis agent that merges multiple research outputs into a clear final report."),
            HumanMessage(content=prompt),
        ]

        response = await self._get_llm().ainvoke(messages)
        return response.content if isinstance(response.content, str) else str(response.content)

    def _fallback_synthesize(self, subtask_outputs: dict[str, Any]) -> str:
        parts = []
        for agent_id, output in subtask_outputs.items():
            parts.append(f"## {agent_id}\n{output}")

        return "\n\n".join(parts)
