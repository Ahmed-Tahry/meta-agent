import pytest
from unittest.mock import AsyncMock, patch, MagicMock, PropertyMock

from langchain_core.messages import HumanMessage

from src.agents.base import Agent
from src.tools import Tool


@pytest.fixture
def sample_tools():
    async def search(q: str) -> str:
        return f"searched {q}"
    return [
        Tool(name="web_search", fn=search, description="search web"),
    ]


def _make_mock_llm():
    mock_msg = MagicMock()
    mock_msg.content = ""
    mock_msg.tool_calls = []
    mock_llm = MagicMock()
    mock_llm.ainvoke = AsyncMock(return_value=mock_msg)
    mock_llm.bind_tools = MagicMock(return_value=mock_llm)
    return mock_llm


@pytest.fixture
def agent():
    a = Agent(
        agent_id="test_01",
        system_prompt="You are a test agent.",
        tools=[],
    )
    a._llm = _make_mock_llm()
    return a


class TestAgent:
    @pytest.mark.asyncio
    async def test_run_returns_string(self, agent):
        expected = "LLM response text"
        agent._llm.ainvoke.return_value.content = expected

        result = await agent.run("task_01", "find info", {})
        assert isinstance(result, str)
        assert result == expected

    @pytest.mark.asyncio
    async def test_run_adds_message(self, agent):
        await agent.run("task_01", "find info", {})
        assert len(agent.messages) == 2
        assert isinstance(agent.messages[0], HumanMessage)
        assert "find info" in agent.messages[0].content

    @pytest.mark.asyncio
    async def test_run_shared_state_empty(self, agent):
        result = await agent.run("task_01", "test", {})
        assert result is not None

    def test_agent_has_system_prompt(self, agent):
        assert agent.system_prompt == "You are a test agent."

    def test_agent_no_tools_by_default(self, agent):
        assert agent.tools == []

    def test_agent_llm_lazy_init(self):
        a = Agent(agent_id="test", system_prompt="prompt", tools=[])
        assert a._llm is None
        llm = a._get_llm()
        assert llm is not None
        assert a._llm is llm


class TestAgentSubclasses:
    def test_agent_is_used_for_any_role(self):
        from src.factory.agent_factory import AgentFactory
        from src.types.agent_spec import AgentSpec

        factory = AgentFactory()
        for role in ["researcher", "coder", "writer", "data_analyzer", "reviewer"]:
            spec = AgentSpec(agent_id=f"{role}_01", role=role, goal="test")
            agent = factory._resolve_agent_cls(role)
            assert agent is Agent
