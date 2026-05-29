import pytest
from unittest.mock import AsyncMock, patch, mock_open

from src.factory.agent_factory import AgentFactory, load_agent_configs


SAMPLE_YAML = """
researcher:
  system_prompt: "You are a researcher."
  tools:
    - web_search
coder:
  system_prompt: "You are a coder."
  tools:
    - code_executor
writer:
  system_prompt: "You are a writer."
  tools:
    - file_reader
"""


class TestLoadAgentConfigs:
    @patch("builtins.open", new_callable=mock_open, read_data=SAMPLE_YAML)
    def test_loads_yaml(self, mock_file):
        configs = load_agent_configs("fake_path.yaml")
        assert "researcher" in configs
        assert "coder" in configs
        assert "writer" in configs
        assert configs["researcher"]["system_prompt"] == "You are a researcher."


class TestAgentFactory:
    @pytest.fixture
    def factory(self):
        with patch("builtins.open", new_callable=mock_open, read_data=SAMPLE_YAML):
            return AgentFactory("fake_path.yaml")

    def test_create_researcher(self, factory):
        from src.types.agent_spec import AgentSpec
        spec = AgentSpec(
            agent_id="researcher_01",
            role="researcher",
            goal="find info",
            tools=["web_search"],
        )
        agent = factory.create(spec)
        assert agent.agent_id == "researcher_01"
        assert "researcher" in agent.system_prompt.lower()
        assert len(agent.tools) == 1
        assert agent.tools[0].name == "web_search"

    def test_create_coder(self, factory):
        from src.types.agent_spec import AgentSpec
        spec = AgentSpec(
            agent_id="coder_01",
            role="coder",
            goal="write code",
            tools=["code_executor"],
        )
        agent = factory.create(spec)
        assert "coder" in agent.system_prompt.lower()
        assert agent.tools[0].name == "code_executor"

    def test_create_writer(self, factory):
        from src.types.agent_spec import AgentSpec
        spec = AgentSpec(
            agent_id="writer_01",
            role="writer",
            goal="write report",
            tools=["file_reader"],
        )
        agent = factory.create(spec)
        assert "writer" in agent.system_prompt.lower()

    def test_create_with_multiple_tools(self, factory):
        from src.types.agent_spec import AgentSpec
        spec = AgentSpec(
            agent_id="coder_01",
            role="coder",
            goal="do everything",
            tools=["web_search", "code_executor", "file_reader"],
        )
        agent = factory.create(spec)
        assert len(agent.tools) == 3

    def test_create_unknown_agent_type(self, factory):
        from src.types.agent_spec import AgentSpec
        from src.agents.base import Agent
        spec = AgentSpec(
            agent_id="unknown_01",
            role="unknown",
            goal="do something",
        )
        agent = factory.create(spec)
        assert isinstance(agent, Agent)
