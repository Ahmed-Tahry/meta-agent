from dataclasses import dataclass, field
from typing import Any
from src.types.agent_spec import AgentSpec


@dataclass
class Subtask:
    subtask_id: str
    agent_spec: AgentSpec
    depends_on: list[str] = field(default_factory=list)
    status: str = "pending"
    output: Any = None


@dataclass
class Task:
    task_id: str
    goal: str
    subtasks: list[Subtask] = field(default_factory=list)
    status: str = "pending"
    result: Any = None
