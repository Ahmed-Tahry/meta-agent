import asyncio
from typing import Any

from src.types.task import Subtask
from src.types.agent_spec import AgentSpec
from src.meta_agent.planner import Planner
from src.meta_agent.evaluator import Evaluator
from src.meta_agent.synthesizer import Synthesizer
from src.factory.agent_factory import AgentFactory
from src.event_bus.bus import event_bus
from src.shared_state.redis_store import store


class Orchestrator:
    def __init__(self) -> None:
        self._planner: Planner | None = None
        self._evaluator: Evaluator | None = None
        self._synthesizer: Synthesizer | None = None
        self._factory: AgentFactory | None = None
        self._tasks: dict[str, asyncio.Task] = {}

    def _get_planner(self) -> Planner:
        if self._planner is None:
            self._planner = Planner()
        return self._planner

    def _get_evaluator(self) -> Evaluator:
        if self._evaluator is None:
            self._evaluator = Evaluator()
        return self._evaluator

    def _get_synthesizer(self) -> Synthesizer:
        if self._synthesizer is None:
            self._synthesizer = Synthesizer()
        return self._synthesizer

    def _get_factory(self) -> AgentFactory:
        if self._factory is None:
            self._factory = AgentFactory()
        return self._factory

    def start(self, goal: str, task_id: str) -> None:
        self._tasks[task_id] = asyncio.create_task(self._run(goal, task_id))

    async def _run(self, goal: str, task_id: str) -> None:
        try:
            await store.set_task_status(task_id, "running")
            await store.set_goal(task_id, goal)
            event_bus.emit(task_id, "status", {"status": "running"})

            planner = self._get_planner()
            subtasks = await planner.decompose(goal, task_id)

            event_bus.emit(task_id, "node", {
                "node": "spawner",
                "status": "running",
                "agents": [s.agent_spec.agent_id for s in subtasks],
            })

            factory = self._get_factory()
            agents = {}
            for subtask in subtasks:
                agent = factory.create(subtask.agent_spec)
                agents[subtask.subtask_id] = agent

            event_bus.emit(task_id, "node", {
                "node": "spawner",
                "status": "done",
                "agents": list(agents.keys()),
            })

            event_bus.emit(task_id, "node", {"node": "executor", "status": "running"})

            evaluator = self._get_evaluator()
            subtask_outputs: dict[str, Any] = {}
            for subtask in subtasks:
                await store.set_subtask_status(task_id, subtask.subtask_id, "running")

                shared_state = {}
                for dep_id in subtask.depends_on:
                    dep_summary = await store.get_subtask_summary(task_id, dep_id)
                    if dep_summary:
                        shared_state[dep_id] = dep_summary

                agent = agents[subtask.subtask_id]
                output = await agent.run(task_id, subtask.agent_spec.goal, shared_state)

                is_valid = await evaluator.evaluate(task_id, subtask.subtask_id, output)
                if is_valid:
                    await store.set_subtask_status(task_id, subtask.subtask_id, "done")
                    summary = {"output": output}
                    await store.set_subtask_summary(task_id, subtask.subtask_id, summary)
                    subtask_outputs[subtask.subtask_id] = output
                else:
                    await store.set_subtask_status(task_id, subtask.subtask_id, "failed")

            event_bus.emit(task_id, "node", {"node": "executor", "status": "done"})
            event_bus.emit(task_id, "node", {"node": "evaluator", "status": "done"})

            synthesizer = self._get_synthesizer()
            await synthesizer.synthesize(task_id, subtask_outputs)
            await store.set_task_status(task_id, "done")
            event_bus.emit(task_id, "status", {"status": "done"})

        except Exception as e:
            await store.set_task_status(task_id, "failed")
            event_bus.emit(task_id, "error", {"message": str(e)})
            raise
        finally:
            event_bus.unsubscribe(task_id)
            self._tasks.pop(task_id, None)


orchestrator = Orchestrator()
