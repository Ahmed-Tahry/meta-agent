import yaml

from src.agents.base import Agent
from src.agents.researcher import ResearcherAgent
from src.agents.coder import CoderAgent
from src.agents.writer import WriterAgent
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

    def create(self, spec: AgentSpec) -> Agent:
        agent_type = spec.agent_id.split("_")[0]
        agent_cls = AGENT_TYPE_MAP.get(agent_type)
        if not agent_cls:
            agent_cls = Agent

        config = self.configs.get(agent_type, {})
        system_prompt = config.get("system_prompt", spec.goal)
        tools = tool_registry.get_multiple(spec.tools)

        return agent_cls(
            agent_id=spec.agent_id,
            system_prompt=system_prompt,
            tools=tools,
        )
