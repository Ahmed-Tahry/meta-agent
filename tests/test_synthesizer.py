import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from src.meta_agent.synthesizer import Synthesizer


class TestSynthesizer:
    @pytest.fixture
    def synthesizer(self):
        return Synthesizer()

    @pytest.mark.asyncio
    async def test_synthesize_merges_outputs(self, synthesizer):
        with (
            patch("src.meta_agent.synthesizer.store") as mock_store,
            patch("src.meta_agent.synthesizer.event_bus") as mock_bus,
        ):
            mock_store.set_result = AsyncMock()

            outputs = {
                "researcher_01": "Found competitor data",
                "writer_01": "Report written",
            }
            result = await synthesizer.synthesize("task_01", outputs)

            assert "researcher_01" in result
            assert "writer_01" in result
            assert "Found competitor data" in result
            assert "Report written" in result

    @pytest.mark.asyncio
    async def test_synthesize_single_agent(self, synthesizer):
        with (
            patch("src.meta_agent.synthesizer.store") as mock_store,
            patch("src.meta_agent.synthesizer.event_bus") as mock_bus,
        ):
            mock_store.set_result = AsyncMock()

            result = await synthesizer.synthesize("task_01", {"coder_01": "def foo(): pass"})
            assert "coder_01" in result
            assert "def foo(): pass" in result

    @pytest.mark.asyncio
    async def test_synthesize_stores_result(self, synthesizer):
        with (
            patch("src.meta_agent.synthesizer.store") as mock_store,
            patch("src.meta_agent.synthesizer.event_bus") as mock_bus,
        ):
            mock_store.set_result = AsyncMock()

            await synthesizer.synthesize("task_01", {"a": "out"})
            mock_store.set_result.assert_called_once()

    @pytest.mark.asyncio
    async def test_synthesize_emits_complete(self, synthesizer):
        with (
            patch("src.meta_agent.synthesizer.store") as mock_store,
            patch("src.meta_agent.synthesizer.event_bus") as mock_bus,
        ):
            mock_store.set_result = AsyncMock()

            await synthesizer.synthesize("task_01", {"a": "out"})
            mock_bus.emit.assert_called_once()
            event = mock_bus.emit.call_args[0][1]
            assert event == "complete"

    @pytest.mark.asyncio
    async def test_synthesize_empty_outputs(self, synthesizer):
        with (
            patch("src.meta_agent.synthesizer.store") as mock_store,
            patch("src.meta_agent.synthesizer.event_bus") as mock_bus,
        ):
            mock_store.set_result = AsyncMock()

            result = await synthesizer.synthesize("task_01", {})
            assert result == ""
