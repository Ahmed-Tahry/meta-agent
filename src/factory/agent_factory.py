import yaml

from src.agents.base import Agent
from src.agents.researcher import ResearcherAgent
from src.agents.coder import CoderAgent
from src.agents.writer import WriterAgent
from src.factory.prompt_builder import PromptBuilder
from src.tools.composer import ToolComposer
from src.types.agent_spec import AgentSpec
from src.tools import tool_registry

AGENT_TYPE_MAP = {
    "researcher": ResearcherAgent,
    "coder": CoderAgent,
    "writer": WriterAgent,
}


def load_agent_configs(path: str = "config/agents.yaml") -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


class AgentFactory:
    def __init__(self, config_path: str = "config/agents.yaml") -> None:
        self.configs = load_agent_configs(config_path)
        self.prompt_builder = PromptBuilder()
        self.tool_composer = ToolComposer(tool_registry)

    def _resolve_agent_cls(self, role: str) -> type[Agent]:
        return AGENT_TYPE_MAP.get(role, Agent)

    def _resolve_tools(self, tool_names: list[str]) -> list:
        resolved = []
        for name in tool_names:
            plain = tool_registry.get(name)
            if plain:
                resolved.append(plain)
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
        return resolved

    def create(self, spec: AgentSpec) -> Agent:
        agent_cls = self._resolve_agent_cls(spec.role)
        config = self.configs.get(spec.role, {})
        system_prompt = config.get("system_prompt", spec.goal)
        tools = self._resolve_tools(spec.tools)

        return agent_cls(
            agent_id=spec.agent_id,
            system_prompt=system_prompt,
            tools=tools,
        )

    async def create_dynamic(self, spec: AgentSpec) -> Agent:
        agent_cls = self._resolve_agent_cls(spec.role)
        config = self.configs.get(spec.role, {})
        base_prompt = config.get("system_prompt", "")
        system_prompt = await self.prompt_builder.build(spec, base_prompt)
        tools = self._resolve_tools(spec.tools)

        return agent_cls(
            agent_id=spec.agent_id,
            system_prompt=system_prompt,
            tools=tools,
        )
