import yaml

from src.agents.base import Agent
from src.factory.prompt_builder import PromptBuilder
from src.tools import tool_registry
from src.tools.composer import ToolComposer
from src.tools.generator import ToolGenerator
from src.types.agent_spec import AgentSpec


def load_agent_configs(path: str = "config/agents.yaml") -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


class AgentFactory:
    def __init__(self, config_path: str = "config/agents.yaml") -> None:
        self.configs = load_agent_configs(config_path)
        self.prompt_builder = PromptBuilder()
        self.tool_composer = ToolComposer(tool_registry)
        self.tool_generator = ToolGenerator()

    def _resolve_agent_cls(self, role: str) -> type[Agent]:
        return Agent

    def _resolve_tools(self, tool_names: list[str]) -> list:
        resolved = []
        unregistered: list[str] = []
        for name in tool_names:
            tool = tool_registry.get(name)
            if tool:
                resolved.append(tool)
                continue

            if "|" in name:
                parts = [p.strip() for p in name.split("|") if p.strip()]
                if len(parts) >= 2:
                    composed_name = "|".join(parts)
                    composed = tool_registry.get(composed_name)
                    if not composed:
                        composed = self.tool_composer.compose(
                            parts,
                            name=composed_name,
                            description=f"Pipeline: {' -> '.join(parts)}",
                        )
                        tool_registry.register(composed)
                    resolved.append(composed)
                    continue

            unregistered.append(name)

        return resolved, unregistered

    async def _generate_missing(
        self, names: list[str], goal: str, tool_defs: dict[str, str] | None = None
    ) -> list:
        generated = []
        for name in names:
            tool_goal = (tool_defs or {}).get(name, goal)
            tool = await self.tool_generator.generate(name, tool_goal)
            tool_registry.register(tool)
            generated.append(tool)
        return generated

    def create(self, spec: AgentSpec) -> Agent:
        agent_cls = self._resolve_agent_cls(spec.role)
        config = self.configs.get(spec.role, {})
        system_prompt = config.get("system_prompt", spec.goal)
        tools, _ = self._resolve_tools(spec.tools)

        return agent_cls(
            agent_id=spec.agent_id,
            system_prompt=system_prompt,
            tools=tools,
        )

    async def create_dynamic(self, spec: AgentSpec) -> Agent:
        if spec.tool_definitions:
            for name in spec.tool_definitions:
                if name not in spec.tools:
                    spec.tools.append(name)
        agent_cls = self._resolve_agent_cls(spec.role)
        config = self.configs.get(spec.role, {})
        base_prompt = config.get("system_prompt", "")
        system_prompt = await self.prompt_builder.build(spec, base_prompt)
        tools, unregistered = self._resolve_tools(spec.tools)

        if unregistered:
            generated = await self._generate_missing(unregistered, spec.goal, spec.tool_definitions)
            tools.extend(generated)

        return agent_cls(
            agent_id=spec.agent_id,
            system_prompt=system_prompt,
            tools=tools,
        )
