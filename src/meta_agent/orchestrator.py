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
from src.config import MAX_RETRIES, RETRY_DELAY


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

    async def _build_shared_state(self, task_id: str, subtask: Subtask) -> dict[str, Any]:
        shared_state: dict[str, Any] = {}
        for dep_id in subtask.depends_on:
            dep_summary = await store.get_subtask_summary(task_id, dep_id)
            if dep_summary:
                shared_state[dep_id] = dep_summary
        return shared_state

    async def _run_subtask_with_retry(
        self,
        task_id: str,
        subtask: Subtask,
        evaluator: Evaluator,
        factory: AgentFactory,
    ) -> tuple[str, bool, str | None]:
        last_error: str | None = None

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                event_bus.emit(task_id, "node", {
                    "node": "spawner",
                    "status": "running",
                    "agent": subtask.subtask_id,
                    "attempt": attempt,
                })

                agent = await factory.create_dynamic(subtask.agent_spec)

                event_bus.emit(task_id, "node", {
                    "node": "spawner",
                    "status": "done",
                    "agent": subtask.subtask_id,
                    "attempt": attempt,
                })

                await store.set_subtask_status(task_id, subtask.subtask_id, "running")
                shared_state = await self._build_shared_state(task_id, subtask)
                output = await agent.run(task_id, subtask.agent_spec.goal, shared_state)

                is_valid = await evaluator.evaluate(task_id, subtask.subtask_id, output)
                if is_valid:
                    await store.set_subtask_status(task_id, subtask.subtask_id, "done")
                    summary = {"output": output}
                    await store.set_subtask_summary(task_id, subtask.subtask_id, summary)
                    return subtask.subtask_id, True, output

                last_error = "Output failed evaluation"

            except Exception as e:
                last_error = str(e)
                event_bus.emit(task_id, "error", {
                    "subtask_id": subtask.subtask_id,
                    "message": last_error,
                    "attempt": attempt,
                })

            if attempt < MAX_RETRIES:
                await store.set_subtask_status(task_id, subtask.subtask_id, "retrying")
                event_bus.emit(task_id, "subtask", {
                    "agent_id": subtask.subtask_id,
                    "status": "retrying",
                    "attempt": attempt + 1,
                })
                await asyncio.sleep(RETRY_DELAY)

        await store.set_subtask_status(task_id, subtask.subtask_id, "failed")
        event_bus.emit(task_id, "error", {
            "subtask_id": subtask.subtask_id,
            "message": last_error or "Subtask failed after retries",
        })
        return subtask.subtask_id, False, None

    async def _run(self, goal: str, task_id: str) -> None:
        try:
            await store.set_task_status(task_id, "running")
            await store.set_goal(task_id, goal)
            event_bus.emit(task_id, "status", {"status": "running"})

            planner = self._get_planner()
            subtasks = await planner.decompose(goal, task_id)

            event_bus.emit(task_id, "node", {"node": "executor", "status": "running"})

            evaluator = self._get_evaluator()
            factory = self._get_factory()
            subtask_outputs: dict[str, Any] = {}
            pending: dict[str, Subtask] = {s.subtask_id: s for s in subtasks}
            completed: set[str] = set()
            failed: set[str] = set()

            while pending:
                dependency_failed = [
                    s for s in pending.values()
                    if any(dep in failed for dep in s.depends_on)
                ]
                for s in dependency_failed:
                    await store.set_subtask_status(task_id, s.subtask_id, "failed")
                    event_bus.emit(task_id, "error", {
                        "subtask_id": s.subtask_id,
                        "message": "Dependency failed",
                    })
                    failed.add(s.subtask_id)
                    pending.pop(s.subtask_id, None)

                ready = [
                    s for s in pending.values()
                    if all(dep in completed for dep in s.depends_on)
                ]
                if not ready:
                    break

                results = await asyncio.gather(*[
                    self._run_subtask_with_retry(task_id, s, evaluator, factory)
                    for s in ready
                ])

                for subtask_id, ok, output in results:
                    pending.pop(subtask_id, None)
                    if ok and output is not None:
                        completed.add(subtask_id)
                        subtask_outputs[subtask_id] = output
                    else:
                        failed.add(subtask_id)

            if pending:
                await store.set_task_status(task_id, "failed")
                event_bus.emit(task_id, "error", {
                    "message": "Could not resolve subtask dependencies (possible cycle)",
                })
                return

            event_bus.emit(task_id, "node", {"node": "executor", "status": "done"})
            event_bus.emit(task_id, "node", {"node": "evaluator", "status": "done"})

            if not subtask_outputs:
                await store.set_task_status(task_id, "failed")
                event_bus.emit(task_id, "error", {
                    "message": "No valid subtask outputs produced",
                })
                return

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
