import os
import pytest

from src.agents.base import Agent
from src.factory.agent_factory import AgentFactory
from src.tools import tool_registry

REAL_API_KEY_SET = (
    os.environ.get("GEMINI_API_KEY")
    and os.environ.get("GEMINI_API_KEY") != "test-key"
)

pytestmark = pytest.mark.skipif(
    not REAL_API_KEY_SET,
    reason="Set GEMINI_API_KEY to a real key to run integration tests",
)


@pytest.fixture
def configs():
    from src.factory.agent_factory import load_agent_configs
    return load_agent_configs()


@pytest.fixture
def agent_factory():
    return AgentFactory()


class TestAgentIntegration:
    @pytest.mark.asyncio
    async def test_agent_returns_output(self, agent_factory, configs):
        prompt = configs.get("researcher", {}).get("system_prompt", "You are a researcher.")
        tools = tool_registry.get_multiple(["web_search"])
        agent = Agent(
            agent_id="researcher_01",
            system_prompt=prompt,
            tools=tools,
        )

        result = await agent.run(
            task_id="int_test_res",
            goal="Research the benefits of renewable energy sources like solar "
                 "and wind power. Provide a concise summary of at least 3 key benefits.",
            shared_state={},
        )

        assert isinstance(result, str)
        assert len(result) > 50
        assert any(word in result.lower() for word in ["energy", "solar", "renewable", "wind", "power"])

    @pytest.mark.asyncio
    async def test_agent_appends_to_message_history(self, agent_factory, configs):
        prompt = configs.get("researcher", {}).get("system_prompt", "You are a researcher.")
        tools = tool_registry.get_multiple(["web_search"])
        agent = Agent(
            agent_id="researcher_02",
            system_prompt=prompt,
            tools=tools,
        )

        await agent.run(
            task_id="int_test_res_hist",
            goal="What are the main causes of climate change?",
            shared_state={},
        )

        assert len(agent.messages) == 2
        assert "climate change" in agent.messages[0].content.lower()

    @pytest.mark.asyncio
    async def test_coder_returns_code_output(self, agent_factory, configs):
        prompt = configs.get("coder", {}).get("system_prompt", "You are a coder.")
        tools = tool_registry.get_multiple(["code_executor"])
        agent = Agent(
            agent_id="coder_01",
            system_prompt=prompt,
            tools=tools,
        )

        result = await agent.run(
            task_id="int_test_code",
            goal="Write a Python function called `calculate_average` that takes "
                 "a list of numbers and returns the average. Include a docstring.",
            shared_state={},
        )

        assert isinstance(result, str)
        assert len(result) > 20
        assert "def " in result or "calculate_average" in result or "average" in result.lower()

    @pytest.mark.asyncio
    async def test_agent_handles_empty_tools(self):
        agent = Agent(
            agent_id="coder_no_tools",
            system_prompt="You are a helpful coding assistant.",
            tools=[],
        )

        result = await agent.run(
            task_id="int_test_code_no_tools",
            goal="What is the time complexity of binary search? Answer in one sentence.",
            shared_state={},
        )

        assert isinstance(result, str)
        assert len(result) > 10

    @pytest.mark.asyncio
    async def test_writer_returns_written_output(self, configs):
        prompt = configs.get("writer", {}).get("system_prompt", "You are a writer.")
        tools = tool_registry.get_multiple(["web_search"])
        agent = Agent(
            agent_id="writer_01",
            system_prompt=prompt,
            tools=tools,
        )

        result = await agent.run(
            task_id="int_test_write",
            goal="Write a short paragraph (3-5 sentences) explaining why "
                 "regular exercise is important for physical and mental health.",
            shared_state={},
        )

        assert isinstance(result, str)
        assert len(result) > 50
        assert any(word in result.lower() for word in ["exercise", "health", "mental", "physical"])

    @pytest.mark.asyncio
    async def test_agent_with_shared_state(self, configs):
        prompt = configs.get("writer", {}).get("system_prompt", "You are a writer.")
        tools = tool_registry.get_multiple(["web_search"])
        agent = Agent(
            agent_id="writer_02",
            system_prompt=prompt,
            tools=tools,
        )

        shared = {
            "researcher_01": {"output": "Wind and solar are the cheapest energy sources."}
        }

        result = await agent.run(
            task_id="int_test_write_shared",
            goal="Summarize the key findings about renewable energy.",
            shared_state=shared,
        )

        assert isinstance(result, str)
        assert len(result) > 20
