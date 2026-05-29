import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from src.meta_agent.planner import Planner
from src.types.agent_spec import AgentSpec


SAMPLE_RESPONSE = """
[
  {
    "agent_id": "researcher_01",
    "role": "researcher",
    "goal": "Search for competitor data",
    "tools": ["web_search"],
    "depends_on": [],
    "output_format": "json"
  },
  {
    "agent_id": "writer_01",
    "role": "writer",
    "goal": "Write a summary report",
    "tools": ["file_reader"],
    "depends_on": ["researcher_01"],
    "output_format": "markdown"
  }
]
"""

MALFORMED_RESPONSE = "I'll decompose this task into subtasks."


class TestPlanner:
    @pytest.fixture
    def planner(self):
        p = Planner()
        p.llm = AsyncMock()
        return p

    @pytest.mark.asyncio
    async def test_decompose_returns_subtasks(self, planner):
        mock_msg = MagicMock()
        mock_msg.content = SAMPLE_RESPONSE
        planner.llm.ainvoke = AsyncMock(return_value=mock_msg)

        subtasks = await planner.decompose("Research competitors", "task_01")

        assert len(subtasks) == 2
        assert subtasks[0].subtask_id == "researcher_01"
        assert subtasks[0].agent_spec.role == "researcher"
        assert subtasks[0].agent_spec.goal == "Search for competitor data"
        assert subtasks[0].agent_spec.tools == ["web_search"]
        assert subtasks[0].depends_on == []

        assert subtasks[1].subtask_id == "writer_01"
        assert subtasks[1].agent_spec.role == "writer"
        assert subtasks[1].depends_on == ["researcher_01"]

    @pytest.mark.asyncio
    async def test_decompose_calls_llm_with_goal(self, planner):
        mock_msg = MagicMock()
        mock_msg.content = SAMPLE_RESPONSE
        planner.llm.ainvoke = AsyncMock(return_value=mock_msg)

        await planner.decompose("test goal", "task_01")
        planner.llm.ainvoke.assert_called_once()
        call_args = planner.llm.ainvoke.call_args[0][0]
        messages_str = str(call_args)
        assert "test goal" in messages_str

    @pytest.mark.asyncio
    async def test_decompose_malformed_response(self, planner):
        mock_msg = MagicMock()
        mock_msg.content = MALFORMED_RESPONSE
        planner.llm.ainvoke = AsyncMock(return_value=mock_msg)

        subtasks = await planner.decompose("test", "task_01")
        assert subtasks == []

    @pytest.mark.asyncio
    async def test_parse_response_json_block(self, planner):
        content = "```json\n" + SAMPLE_RESPONSE + "\n```"
        result = planner._parse_response(content)
        assert len(result) == 2
        assert result[0]["agent_id"] == "researcher_01"

    @pytest.mark.asyncio
    async def test_parse_response_plain_json(self, planner):
        result = planner._parse_response(SAMPLE_RESPONSE)
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_parse_response_invalid(self, planner):
        result = planner._parse_response("not json at all")
        assert result == []

    @pytest.mark.asyncio
    async def test_emits_events(self, planner):
        mock_msg = MagicMock()
        mock_msg.content = SAMPLE_RESPONSE
        planner.llm.ainvoke = AsyncMock(return_value=mock_msg)

        with patch("src.meta_agent.planner.event_bus") as mock_bus:
            await planner.decompose("test", "task_01")
            assert mock_bus.emit.call_count == 2
            mock_bus.emit.assert_any_call("task_01", "node", {"node": "planner", "status": "running"})
