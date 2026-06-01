import inspect
from typing import Any

from src.tools import Tool, ToolRegistry


class ToolComposer:
    def __init__(self, registry: ToolRegistry) -> None:
        self.registry = registry
        self._cache: dict[tuple[str, ...], Tool] = {}

    def compose(
        self,
        tool_names: list[str],
        name: str | None = None,
        description: str | None = None,
    ) -> Tool:
        if len(tool_names) < 2:
            raise ValueError("Tool composition requires at least two tools")

        key = tuple(tool_names)
        if key in self._cache:
            return self._cache[key]

        tools = []
        for t_name in tool_names:
            t = self.registry.get(t_name)
            if not t:
                raise ValueError(f"Unknown tool in composition: {t_name}")
            tools.append(t)

        composed_name = name or "|".join(tool_names)
        composed_description = description or f"Pipeline: {' -> '.join(tool_names)}"

        async def pipeline(input_text: str) -> str:
            current = input_text
            for tool in tools:
                kwargs = self._kwargs_for(tool, current)
                current = await tool.run(**kwargs)
            return current

        composed = Tool(
            name=composed_name,
            fn=pipeline,
            description=composed_description,
        )
        self._cache[key] = composed
        return composed

    def _kwargs_for(self, tool: Tool, value: str) -> dict[str, Any]:
        sig = inspect.signature(tool.fn)
        params = list(sig.parameters.values())
        if not params:
            return {}
        first_param = params[0].name
        return {first_param: value}
