import json
from typing import Any

import redis.asyncio as aioredis

from src.config import REDIS_URL


class RedisStore:
    def __init__(self) -> None:
        self._redis: aioredis.Redis | None = None

    async def connect(self) -> None:
        self._redis = await aioredis.from_url(REDIS_URL, decode_responses=True)

    async def close(self) -> None:
        if self._redis:
            await self._redis.close()

    def _task_key(self, task_id: str) -> str:
        return f"task:{task_id}"

    def _subtask_key(self, task_id: str, subtask_id: str) -> str:
        return f"task:{task_id}:subtask:{subtask_id}"

    async def set_task_status(self, task_id: str, status: str) -> None:
        assert self._redis
        await self._redis.hset(self._task_key(task_id), "status", status)

    async def get_task_status(self, task_id: str) -> str | None:
        assert self._redis
        return await self._redis.hget(self._task_key(task_id), "status")

    async def set_subtask_status(self, task_id: str, subtask_id: str, status: str) -> None:
        assert self._redis
        key = self._subtask_key(task_id, subtask_id)
        await self._redis.hset(key, "status", status)

    async def get_subtask_status(self, task_id: str, subtask_id: str) -> str | None:
        assert self._redis
        key = self._subtask_key(task_id, subtask_id)
        return await self._redis.hget(key, "status")

    async def set_subtask_summary(self, task_id: str, subtask_id: str, summary: dict[str, Any]) -> None:
        assert self._redis
        key = self._subtask_key(task_id, subtask_id)
        await self._redis.hset(key, "summary", json.dumps(summary))

    async def get_subtask_summary(self, task_id: str, subtask_id: str) -> dict[str, Any] | None:
        assert self._redis
        key = self._subtask_key(task_id, subtask_id)
        raw = await self._redis.hget(key, "summary")
        return json.loads(raw) if raw else None

    async def set_result(self, task_id: str, result: Any) -> None:
        assert self._redis
        key = self._task_key(task_id)
        await self._redis.hset(key, "result", json.dumps(result))

    async def get_result(self, task_id: str) -> Any:
        assert self._redis
        key = self._task_key(task_id)
        raw = await self._redis.hget(key, "result")
        return json.loads(raw) if raw else None

    async def set_goal(self, task_id: str, goal: str) -> None:
        assert self._redis
        key = self._task_key(task_id)
        await self._redis.hset(key, "goal", goal)

    async def get_goal(self, task_id: str) -> str | None:
        assert self._redis
        key = self._task_key(task_id)
        return await self._redis.hget(key, "goal")


store = RedisStore()
