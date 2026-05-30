import pytest
from unittest.mock import AsyncMock, patch, MagicMock, ANY

from src.meta_agent.orchestrator import Orchestrator


class TestOrchestrator:
    @pytest.fixture
    def orchestrator(self):
        return Orchestrator()

    @pytest.mark.asyncio
    async def test_start_creates_background_task(self, orchestrator):
        with patch("asyncio.create_task") as mock_task:
            orchestrator.start("test goal", "task_01")
            mock_task.assert_called_once()
            assert "task_01" in orchestrator._tasks

    @pytest.mark.asyncio
    async def test_run_full_flow(self, orchestrator):
        mock_subtask = MagicMock()
        mock_subtask.subtask_id = "researcher_01"
        mock_subtask.agent_spec.goal = "find info"
        mock_subtask.agent_spec.agent_id = "researcher_01"
        mock_subtask.depends_on = []

        mock_agent = AsyncMock()
        mock_agent.run = AsyncMock(return_value="research results")
        mock_agent.agent_id = "researcher_01"

        mock_planner_obj = MagicMock()
        mock_planner_obj.decompose = AsyncMock(return_value=[mock_subtask])
        mock_evaluator_obj = MagicMock()
        mock_evaluator_obj.evaluate = AsyncMock(return_value=True)
        mock_synthesizer_obj = MagicMock()
        mock_synthesizer_obj.synthesize = AsyncMock(return_value="final result")
        mock_factory_obj = MagicMock()
        mock_factory_obj.create = MagicMock(return_value=mock_agent)

        with (
            patch.object(orchestrator, "_get_planner", return_value=mock_planner_obj),
            patch.object(orchestrator, "_get_evaluator", return_value=mock_evaluator_obj),
            patch.object(orchestrator, "_get_synthesizer", return_value=mock_synthesizer_obj),
            patch.object(orchestrator, "_get_factory", return_value=mock_factory_obj),
            patch("src.meta_agent.orchestrator.store") as mock_store,
            patch("src.meta_agent.orchestrator.event_bus") as mock_bus,
        ):
            mock_store.set_task_status = AsyncMock()
            mock_store.set_goal = AsyncMock()
            mock_store.set_subtask_status = AsyncMock()
            mock_store.set_subtask_summary = AsyncMock()
            mock_store.get_subtask_summary = AsyncMock(return_value=None)
            mock_store.set_result = AsyncMock()
            mock_bus.emit = MagicMock()
            mock_bus.unsubscribe = MagicMock()

            await orchestrator._run("test goal", "task_01")

            mock_planner_obj.decompose.assert_called_once_with("test goal", "task_01")
            mock_factory_obj.create.assert_called_once_with(mock_subtask.agent_spec)
            mock_agent.run.assert_called_once_with("task_01", "find info", {})
            mock_evaluator_obj.evaluate.assert_called_once_with("task_01", "researcher_01", "research results")
            mock_synthesizer_obj.synthesize.assert_called_once_with("task_01", {"researcher_01": "research results"})

    @pytest.mark.asyncio
    async def test_run_with_dependencies(self, orchestrator):
        mock_res = MagicMock()
        mock_res.subtask_id = "researcher_01"
        mock_res.agent_spec.goal = "research"
        mock_res.agent_spec.agent_id = "researcher_01"
        mock_res.depends_on = []

        mock_writer = MagicMock()
        mock_writer.subtask_id = "writer_01"
        mock_writer.agent_spec.goal = "write"
        mock_writer.agent_spec.agent_id = "writer_01"
        mock_writer.depends_on = ["researcher_01"]

        mock_agent_res = AsyncMock()
        mock_agent_res.run = AsyncMock(return_value="research output")
        mock_agent_writer = AsyncMock()
        mock_agent_writer.run = AsyncMock(return_value="written report")

        mock_planner_obj = MagicMock()
        mock_planner_obj.decompose = AsyncMock(return_value=[mock_res, mock_writer])
        mock_evaluator_obj = MagicMock()
        mock_evaluator_obj.evaluate = AsyncMock(return_value=True)
        mock_synthesizer_obj = MagicMock()
        mock_synthesizer_obj.synthesize = AsyncMock(return_value="final")
        mock_factory_obj = MagicMock()
        mock_factory_obj.create = MagicMock(side_effect=[mock_agent_res, mock_agent_writer])

        with (
            patch.object(orchestrator, "_get_planner", return_value=mock_planner_obj),
            patch.object(orchestrator, "_get_evaluator", return_value=mock_evaluator_obj),
            patch.object(orchestrator, "_get_synthesizer", return_value=mock_synthesizer_obj),
            patch.object(orchestrator, "_get_factory", return_value=mock_factory_obj),
            patch("src.meta_agent.orchestrator.store") as mock_store,
            patch("src.meta_agent.orchestrator.event_bus") as mock_bus,
        ):
            mock_store.set_task_status = AsyncMock()
            mock_store.set_goal = AsyncMock()
            mock_store.set_subtask_status = AsyncMock()
            mock_store.set_subtask_summary = AsyncMock()
            mock_store.get_subtask_summary = AsyncMock(return_value={"output": "research output"})
            mock_store.set_result = AsyncMock()
            mock_bus.emit = MagicMock()
            mock_bus.unsubscribe = MagicMock()

            await orchestrator._run("test goal", "task_01")

            assert mock_agent_res.run.called
            assert mock_agent_writer.run.called

    @pytest.mark.asyncio
    async def test_run_handles_failure(self, orchestrator):
        mock_subtask = MagicMock()
        mock_subtask.subtask_id = "researcher_01"
        mock_subtask.agent_spec.goal = "find info"
        mock_subtask.agent_spec.agent_id = "researcher_01"
        mock_subtask.depends_on = []

        mock_agent = AsyncMock()
        mock_agent.run = AsyncMock(return_value="")

        mock_planner_obj = MagicMock()
        mock_planner_obj.decompose = AsyncMock(return_value=[mock_subtask])
        mock_evaluator_obj = MagicMock()
        mock_evaluator_obj.evaluate = AsyncMock(return_value=False)
        mock_synthesizer_obj = MagicMock()
        mock_synthesizer_obj.synthesize = AsyncMock(return_value="final")
        mock_factory_obj = MagicMock()
        mock_factory_obj.create = MagicMock(return_value=mock_agent)

        with (
            patch.object(orchestrator, "_get_planner", return_value=mock_planner_obj),
            patch.object(orchestrator, "_get_evaluator", return_value=mock_evaluator_obj),
            patch.object(orchestrator, "_get_synthesizer", return_value=mock_synthesizer_obj),
            patch.object(orchestrator, "_get_factory", return_value=mock_factory_obj),
            patch("src.meta_agent.orchestrator.store") as mock_store,
            patch("src.meta_agent.orchestrator.event_bus") as mock_bus,
        ):
            mock_store.set_task_status = AsyncMock()
            mock_store.set_goal = AsyncMock()
            mock_store.set_subtask_status = AsyncMock()
            mock_store.set_subtask_summary = AsyncMock()
            mock_store.get_subtask_summary = AsyncMock(return_value=None)
            mock_store.set_result = AsyncMock()
            mock_bus.emit = MagicMock()
            mock_bus.unsubscribe = MagicMock()

            await orchestrator._run("test goal", "task_01")

            mock_store.set_subtask_status.assert_called_with("task_01", "researcher_01", "failed")
