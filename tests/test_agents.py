import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from src.agents.base import Agent
from src.agents.researcher import ResearcherAgent
from src.agents.coder import CoderAgent
from src.agents.writer import WriterAgent
from src.tools.registry import Tool


@pytest.fixture
def sample_tools():
    async def search(q: str) -> str:
        return f"searched {q}"
    return [
        Tool(name="web_search", fn=search, description="search web"),
    ]


@pytest.fixture
def agent(sample_tools):
    return Agent(
        agent_id="test_01",
        system_prompt="You are a test agent.",
        tools=sample_tools,
    )


class TestAgent:
    @pytest.mark.asyncio
    async def test_run_returns_string(self, agent):
        result = await agent.run("task_01", "find info", {})
        assert isinstance(result, str)
        assert "[test_01]" in result

    @pytest.mark.asyncio
    async def test_run_adds_message(self, agent):
        await agent.run("task_01", "find info", {})
        assert len(agent.messages) == 1
        assert agent.messages[0]["role"] == "user"
        assert "find info" in agent.messages[0]["content"]

    @pytest.mark.asyncio
    async def test_run_shared_state_empty(self, agent):
        result = await agent.run("task_01", "test", {})
        assert result is not None

    def test_agent_has_system_prompt(self, agent):
        assert agent.system_prompt == "You are a test agent."

    def test_agent_has_tools(self, agent, sample_tools):
        assert len(agent.tools) == 1
        assert agent.tools[0].name == "web_search"


class TestResearcherAgent:
    def test_is_agent_subclass(self):
        assert issubclass(ResearcherAgent, Agent)


class TestCoderAgent:
    def test_is_agent_subclass(self):
        assert issubclass(CoderAgent, Agent)


class TestWriterAgent:
    def test_is_agent_subclass(self):
        assert issubclass(WriterAgent, Agent)
