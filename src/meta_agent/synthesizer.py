from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from src.config import GEMINI_API_KEY, GEMINI_MODEL, LLM_TIMEOUT
from src.event_bus.bus import event_bus
from src.shared_state.redis_store import store
from src.task_logger import get_logger
from src.utils import extract_llm_text


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
        log = get_logger(task_id)

        if not subtask_outputs:
            log.log("SYNTHESIZER", "No subtask outputs to synthesize — returning empty")
            result = ""
            await store.set_result(task_id, result)
            event_bus.emit(task_id, "complete", {"result": result})
            return result

        log.log(
            "SYNTHESIZER",
            f"Synthesizing {len(subtask_outputs)} output(s): {list(subtask_outputs.keys())}",
        )

        inputs_detail = "\n".join(
            f"  [{k}] ({len(str(v))} chars): {str(v)[:200]}..." for k, v in subtask_outputs.items()
        )
        log.log_multiline("SYNTHESIZER", "Inputs to synthesis:", inputs_detail)

        try:
            log.log("SYNTHESIZER", "Calling Gemini for LLM synthesis")
            result = await self._llm_synthesize(subtask_outputs)
            log.log("SYNTHESIZER", f"LLM synthesis produced {len(result)} chars")
        except Exception as e:
            log.log("SYNTHESIZER", "LLM synthesis failed, using fallback", str(e))
            result = self._fallback_synthesize(subtask_outputs)

        await store.set_result(task_id, result)
        event_bus.emit(task_id, "complete", {"result": result})
        return result

    async def _llm_synthesize(self, subtask_outputs: dict[str, Any]) -> str:
        prompt = (
            "Synthesize the following agent outputs into a coherent final response.\n"
            "Merge findings, remove redundancy, and present a well-structured summary.\n\n"
            + "\n\n".join(self._format_parts(subtask_outputs))
        )

        messages = [
            SystemMessage(
                content=(
                    "You are a synthesis agent that merges multiple research outputs "
                    "into a clear final report."
                )
            ),
            HumanMessage(content=prompt),
        ]

        response = await self._get_llm().ainvoke(messages)
        return extract_llm_text(response.content)

    def _format_parts(self, subtask_outputs: dict[str, Any]) -> list[str]:
        return [f"## {agent_id}\n{output}" for agent_id, output in subtask_outputs.items()]

    def _fallback_synthesize(self, subtask_outputs: dict[str, Any]) -> str:
        return "\n\n".join(self._format_parts(subtask_outputs))
