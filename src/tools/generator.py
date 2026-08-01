from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from src.config import GEMINI_API_KEY, GEMINI_MODEL, LLM_TIMEOUT, SANDBOX_TIMEOUT, TOOL_GEN_RETRIES
from src.tools import Tool
from src.tools.sandbox import Sandbox, SandboxError, SandboxExecutionError, SandboxTimeout

GENERATION_PROMPT = """\
Write a Python async function named {tool_name} that accomplishes:
{goal}

Requirements:
- async def {tool_name}(input_text: str) -> str:
- Standard library only (no pip packages)
- Include a docstring
- Be self-contained
{error_feedback}
Only output the function code, no explanation."""


TEST_HARNESS = """\
import asyncio

{code}

async def main():
    result = await {tool_name}("test input")
    print(result)

asyncio.run(main())
"""


class ToolGenerator:
    def __init__(
        self,
        sandbox: Sandbox | None = None,
        llm: ChatGoogleGenerativeAI | None = None,
    ) -> None:
        self._sandbox = sandbox or Sandbox()
        self._llm = llm

    def _get_llm(self) -> ChatGoogleGenerativeAI:
        if self._llm is None:
            self._llm = ChatGoogleGenerativeAI(
                model=GEMINI_MODEL,
                google_api_key=GEMINI_API_KEY,
                timeout=LLM_TIMEOUT,
            )
        return self._llm

    async def generate(self, tool_name: str, goal: str) -> Tool:
        if not self._sandbox._built:
            try:
                await self._sandbox.build()
            except SandboxError:
                pass

        last_error = ""
        for attempt in range(1, TOOL_GEN_RETRIES + 1):
            code = await self._llm_generate(tool_name, goal, last_error)
            result = await self._test_in_sandbox(tool_name, code)
            if result is True:
                return Tool(
                    name=tool_name,
                    fn=self._make_fn(code, tool_name),
                    description=goal,
                )
            last_error = result

        return self._fallback_tool(tool_name, goal, last_error)

    async def _llm_generate(
        self,
        tool_name: str,
        goal: str,
        error_feedback: str = "",
    ) -> str:
        feedback = ""
        if error_feedback:
            feedback = (
                f"\nPrevious attempt failed with:\n{error_feedback}\nFix the issue and try again."
            )

        prompt = GENERATION_PROMPT.format(
            tool_name=tool_name,
            goal=goal,
            error_feedback=feedback,
        )

        messages = [
            SystemMessage(content="You generate Python async functions for tool execution."),
            HumanMessage(content=prompt),
        ]

        response = await self._get_llm().ainvoke(messages)
        if isinstance(response.content, str):
            content = response.content
        elif isinstance(response.content, list):
            content = "\n".join(
                block.get("text", "")
                if isinstance(block, dict)
                else block.text
                if hasattr(block, "text")
                else str(block)
                for block in response.content
            ).strip()
        else:
            content = str(response.content)
        return self._extract_code(content)

    async def _test_in_sandbox(self, tool_name: str, code: str) -> bool | str:
        script = TEST_HARNESS.format(code=code, tool_name=tool_name)
        try:
            await self._sandbox.run(script, timeout=SANDBOX_TIMEOUT)
            return True
        except SandboxTimeout as e:
            return str(e)
        except SandboxExecutionError as e:
            return e.stderr or e.stdout
        except SandboxError as e:
            return str(e)

    def _extract_code(self, content: str) -> str:
        content = content.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[-1]
            content = content.rsplit("```", 1)[0]
        return content.strip()

    def _make_fn(self, code: str, tool_name: str) -> Any:
        sandbox = self._sandbox
        timeout = SANDBOX_TIMEOUT

        async def fn(input_text: str) -> str:
            from src.task_logger import get_current_logger

            log = get_current_logger()

            harness = f"""\
import asyncio

{code}

async def main():
    result = await {tool_name}({repr(input_text)})
    print(result)

asyncio.run(main())
"""
            if log:
                log.log(
                    "SANDBOX",
                    f"Generated tool '{tool_name}' executing in sandbox",
                    f"input ({len(input_text)} chars): {input_text[:200]}",
                )
            try:
                result = await sandbox.run(harness, timeout=timeout)
                if log:
                    log.log("SANDBOX", f"Generated tool '{tool_name}' output ({len(result)} chars)")
                return result.strip() or "(no output)"
            except SandboxTimeout:
                if log:
                    log.log("SANDBOX", f"Generated tool '{tool_name}' timed out ({timeout}s)")
                return f"Tool execution timed out after {timeout}s."
            except SandboxExecutionError as e:
                err = e.stderr or e.stdout or "Execution failed"
                if log:
                    log.log("SANDBOX", f"Generated tool '{tool_name}' execution error", err)
                return err
            except SandboxError as e:
                if log:
                    log.log("SANDBOX", f"Generated tool '{tool_name}' sandbox error", str(e))
                return f"Sandbox error: {e}"
            except FileNotFoundError:
                if log:
                    log.log("SANDBOX", "Docker not available for generated tool")
                return "Docker is not available. Install Docker and start the daemon."

        return fn

    def _fallback_tool(self, tool_name: str, goal: str, last_error: str) -> Tool:
        async def error_fn(input_text: str) -> str:
            return (
                f"Failed to generate tool '{tool_name}' for goal: {goal}\n"
                f"After {TOOL_GEN_RETRIES} attempt(s), last error:\n{last_error}"
            )

        return Tool(name=tool_name, fn=error_fn, description=goal)
