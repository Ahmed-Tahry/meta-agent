from collections.abc import Callable, Coroutine
from typing import Any


class Tool:
    def __init__(
        self,
        name: str,
        fn: Callable[..., Coroutine[Any, Any, str]],
        description: str = "",
    ) -> None:
        self.name = name
        self.fn = fn
        self.description = description

    async def run(self, **kwargs: Any) -> str:
        return await self.fn(**kwargs)


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def list_tools(self) -> list[str]:
        return list(self._tools.keys())

    def get_multiple(self, names: list[str]) -> list[Tool]:
        result = []
        for name in names:
            tool = self.get(name)
            if tool:
                result.append(tool)
        return result


tool_registry = ToolRegistry()


from src.tools.prebuilt.web_search import tool_web_search
from src.tools.prebuilt.file_reader import tool_file_reader
from src.tools.prebuilt.code_executor import tool_code_executor

tool_registry.register(tool_web_search)
tool_registry.register(tool_file_reader)
tool_registry.register(tool_code_executor)
