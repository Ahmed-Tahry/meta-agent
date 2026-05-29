import pytest
from src.types.agent_spec import AgentSpec
from src.types.task import Subtask, Task


class TestAgentSpec:
    def test_minimal_spec(self):
        spec = AgentSpec(agent_id="test_01", role="researcher", goal="find info")
        assert spec.agent_id == "test_01"
        assert spec.role == "researcher"
        assert spec.goal == "find info"
        assert spec.tools == []
        assert spec.constraints == ""
        assert spec.output_format == "text"
        assert spec.memory_scope == "task"

    def test_full_spec(self):
        spec = AgentSpec(
            agent_id="coder_01",
            role="coder",
            goal="write script",
            tools=["code_executor", "file_reader"],
            constraints="Python only",
            output_format="code",
            memory_scope="task",
        )
        assert spec.agent_id == "coder_01"
        assert spec.tools == ["code_executor", "file_reader"]
        assert spec.constraints == "Python only"
        assert spec.output_format == "code"


class TestSubtask:
    def test_minimal_subtask(self):
        spec = AgentSpec(agent_id="test_01", role="researcher", goal="find")
        sub = Subtask(subtask_id="test_01", agent_spec=spec)
        assert sub.subtask_id == "test_01"
        assert sub.agent_spec == spec
        assert sub.depends_on == []
        assert sub.status == "pending"
        assert sub.output is None

    def test_subtask_with_deps(self):
        spec = AgentSpec(agent_id="writer_01", role="writer", goal="write")
        sub = Subtask(
            subtask_id="writer_01",
            agent_spec=spec,
            depends_on=["researcher_01", "coder_01"],
        )
        assert sub.depends_on == ["researcher_01", "coder_01"]

    def test_subtask_status_transitions(self):
        spec = AgentSpec(agent_id="test_01", role="researcher", goal="find")
        sub = Subtask(subtask_id="test_01", agent_spec=spec)
        assert sub.status == "pending"
        sub.status = "running"
        assert sub.status == "running"
        sub.status = "done"
        assert sub.status == "done"


class TestTask:
    def test_minimal_task(self):
        task = Task(task_id="task_01", goal="do something")
        assert task.task_id == "task_01"
        assert task.goal == "do something"
        assert task.subtasks == []
        assert task.status == "pending"
        assert task.result is None

    def test_task_with_subtasks(self):
        spec1 = AgentSpec(agent_id="res_01", role="researcher", goal="research")
        spec2 = AgentSpec(agent_id="wri_01", role="writer", goal="write")
        subs = [
            Subtask(subtask_id="res_01", agent_spec=spec1),
            Subtask(subtask_id="wri_01", agent_spec=spec2, depends_on=["res_01"]),
        ]
        task = Task(task_id="task_01", goal="do something", subtasks=subs)
        assert len(task.subtasks) == 2
        assert task.subtasks[1].depends_on == ["res_01"]

    def test_task_status_transitions(self):
        task = Task(task_id="task_01", goal="test")
        assert task.status == "pending"
        task.status = "running"
        assert task.status == "running"
        task.status = "done"
        assert task.status == "done"
