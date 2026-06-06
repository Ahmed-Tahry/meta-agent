from dataclasses import dataclass, field


@dataclass
class AgentSpec:
    agent_id: str
    role: str
    goal: str
    tools: list[str] = field(default_factory=list)
    tool_definitions: dict[str, str] = field(default_factory=dict)
    constraints: str = ""
    output_format: str = "text"
    memory_scope: str = "task"
