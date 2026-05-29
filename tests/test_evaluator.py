import pytest
from unittest.mock import AsyncMock, patch

from src.meta_agent.evaluator import Evaluator


class TestEvaluator:
    @pytest.fixture
    def evaluator(self):
        return Evaluator()

    @pytest.mark.asyncio
    async def test_valid_string_output(self, evaluator):
        with patch("src.meta_agent.evaluator.event_bus") as mock_bus:
            result = await evaluator.evaluate("task_01", "sub_01", "some result")
            assert result is True
            mock_bus.emit.assert_not_called()

    @pytest.mark.asyncio
    async def test_valid_dict_output(self, evaluator):
        result = await evaluator.evaluate("task_01", "sub_01", {"key": "value"})
        assert result is True

    @pytest.mark.asyncio
    async def test_valid_number_output(self, evaluator):
        result = await evaluator.evaluate("task_01", "sub_01", 42)
        assert result is True

    @pytest.mark.asyncio
    async def test_none_output_fails(self, evaluator):
        with patch("src.meta_agent.evaluator.event_bus") as mock_bus:
            result = await evaluator.evaluate("task_01", "sub_01", None)
            assert result is False
            mock_bus.emit.assert_called_once_with(
                "task_01", "error",
                {"subtask_id": "sub_01", "message": "Output is empty"},
            )

    @pytest.mark.asyncio
    async def test_empty_string_fails(self, evaluator):
        with patch("src.meta_agent.evaluator.event_bus") as mock_bus:
            result = await evaluator.evaluate("task_01", "sub_01", "")
            assert result is False

    @pytest.mark.asyncio
    async def test_whitespace_string_fails(self, evaluator):
        result = await evaluator.evaluate("task_01", "sub_01", "   ")
        assert result is False

    @pytest.mark.asyncio
    async def test_list_output_valid(self, evaluator):
        result = await evaluator.evaluate("task_01", "sub_01", ["a", "b"])
        assert result is True
