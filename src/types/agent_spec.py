from dataclasses import dataclass, field


@dataclass
class AgentSpec:
    agent_id: str
    role: str
    goal: str
    tools: list[str] = field(default_factory=list)
    constraints: str = ""
    output_format: str = "text"
    memory_scope: str = "task"
