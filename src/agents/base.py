import asyncio
import json
from typing import Any

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage

from src.config import GEMINI_API_KEY, GEMINI_MODEL, MAX_TOOL_CALLS, LLM_TIMEOUT, TOOL_CALL_DELAY
from src.event_bus.bus import event_bus
from src.shared_state.redis_store import store
from src.task_logger import get_logger, current_task_id
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
        self._llm: ChatGoogleGenerativeAI | None = None
        self.messages: list = []
        self._tool_map: dict[str, Tool] = {t.name: t for t in tools}

    def _get_llm(self) -> ChatGoogleGenerativeAI:
        if self._llm is None:
            self._llm = ChatGoogleGenerativeAI(
                model=GEMINI_MODEL,
                google_api_key=GEMINI_API_KEY,
                timeout=LLM_TIMEOUT,
            )
        return self._llm

    def _build_context(self, shared_state: dict[str, Any]) -> str:
        if not shared_state:
            return ""
        parts = []
        for agent_id, data in shared_state.items():
            output = data.get("output", "")
            summary = output[:500] if isinstance(output, str) else json.dumps(output)[:500]
            parts.append(f"From {agent_id}: {summary}")
        return "\n\nPrevious findings:\n" + "\n".join(parts)

    async def _append_trace(self, task_id: str, entry: dict) -> None:
        entry["agent_id"] = self.agent_id
        await store.append_trace(task_id, entry)

    async def run(self, task_id: str, goal: str, shared_state: dict[str, Any]) -> str:
        log = get_logger(task_id)
        event_bus.emit(task_id, "subtask", {"agent_id": self.agent_id, "status": "running"})
        await self._append_trace(task_id, {"type": "agent_start", "goal": goal, "shared_state": bool(shared_state)})

        log.log("AGENT", f"Agent {self.agent_id} running",
            f"goal={goal}  tools={[t.name for t in self.tools]}  "
            f"shared_state_keys={list(shared_state.keys())}")

        current_task_id.set(task_id)
        tool_descriptions = "\n".join(f"- {t.name}: {t.description}" for t in self.tools)
        context = self._build_context(shared_state)
        result = await self._execute(task_id, goal, tool_descriptions, context)

        log.log_multiline("AGENT", f"Agent {self.agent_id} final output ({len(result)} chars):", result)
        event_bus.emit(task_id, "subtask", {
            "agent_id": self.agent_id,
            "status": "done",
            "summary": {"output": result},
        })
        await self._append_trace(task_id, {"type": "agent_done", "output_preview": result[:200]})
        return result

    async def _execute(self, task_id: str, goal: str, tool_descriptions: str, context: str) -> str:
        log = get_logger(task_id)
        system = SystemMessage(content=self.system_prompt)
        user_content = f"Goal: {goal}\n\nTools available:\n{tool_descriptions}{context}"
        user = HumanMessage(content=user_content)
        messages = [system] + self.messages + [user]

        log.log("AGENT", f"{self.agent_id} — sending initial prompt to LLM")
        await self._append_trace(task_id, {"type": "agent_llm_call", "prompt": user_content})

        if self.tools:
            lc_tools = [t.to_langchain_tool() for t in self.tools]
            llm = self._get_llm().bind_tools(lc_tools)
        else:
            llm = self._get_llm()

        response = await llm.ainvoke(messages)
        tool_call_count = 0
        tool_results: list[str] = []

        while response.tool_calls and tool_call_count < MAX_TOOL_CALLS:
            messages.append(response)

            for tc in response.tool_calls:
                tool = self._tool_map.get(tc["name"])
                if not tool:
                    log.log("AGENT", f"{self.agent_id} — unknown tool requested: {tc['name']}")
                    await self._append_trace(task_id, {
                        "type": "unknown_tool_call", "tool": tc["name"], "args": tc["args"],
                    })
                    event_bus.emit(task_id, "error", {
                        "subtask_id": self.agent_id,
                        "message": f"Unknown tool: {tc['name']}",
                    })
                    continue

                log.log("AGENT", f"{self.agent_id} — tool call: {tc['name']}",
                    f"args={json.dumps(tc['args'])[:300]}")
                await self._append_trace(task_id, {
                    "type": "tool_call", "tool": tc["name"], "args": tc["args"],
                })
                event_bus.emit(task_id, "tool_call", {
                    "agent_id": self.agent_id, "tool": tc["name"], "args": tc["args"],
                })

                result = await tool.run(**tc["args"])
                tool_results.append(result)

                log.log("AGENT", f"{self.agent_id} — tool result: {tc['name']}",
                    f"result ({len(result)} chars): {result[:300]}")
                await self._append_trace(task_id, {
                    "type": "tool_result", "tool": tc["name"], "result": result,
                })
                event_bus.emit(task_id, "tool_result", {
                    "agent_id": self.agent_id, "tool": tc["name"], "result": result,
                })

                messages.append(ToolMessage(content=result, tool_call_id=tc["id"]))

            await asyncio.sleep(TOOL_CALL_DELAY)
            response = await llm.ainvoke(messages)
            tool_call_count += 1

        if response.tool_calls and tool_call_count >= MAX_TOOL_CALLS:
            log.log("AGENT",
                f"{self.agent_id} — reached max tool-call rounds ({MAX_TOOL_CALLS})")
            await self._append_trace(task_id, {
                "type": "tool_call_limit_reached",
                "max_tool_calls": MAX_TOOL_CALLS,
            })
            event_bus.emit(task_id, "error", {
                "subtask_id": self.agent_id,
                "message": f"Reached max tool-call rounds ({MAX_TOOL_CALLS})",
            })

        self.messages.append(user)
        self.messages.append(response)

        if isinstance(response.content, str):
            final_content = response.content
        elif isinstance(response.content, list):
            final_content = "\n".join(
                block.get("text", "") if isinstance(block, dict)
                else block.text if hasattr(block, "text")
                else str(block)
                for block in response.content
            ).strip()
        else:
            final_content = str(response.content)
        if final_content.strip():
            log.log("AGENT", f"{self.agent_id} — got LLM final response ({len(final_content)} chars)")
            return final_content

        log.log("AGENT", f"{self.agent_id} — LLM returned empty content, using tool results fallback")
        if tool_results:
            preview = "\n".join(f"- {x}" for x in tool_results[-3:])
            return (
                f"Could not get additional model narrative after tool usage for goal: {goal}.\n"
                "Recent tool outputs:\n"
                f"{preview}"
            )

        return f"No model response generated for goal: {goal}."
