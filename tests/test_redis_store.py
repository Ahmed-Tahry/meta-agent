import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from src.shared_state.redis_store import RedisStore


@pytest.fixture
def mock_redis():
    mock = AsyncMock()
    mock.hset = AsyncMock()
    mock.hget = AsyncMock(return_value=None)
    mock.close = AsyncMock()
    return mock


@pytest.fixture
def store(mock_redis):
    s = RedisStore()
    s._redis = mock_redis
    return s


class TestRedisStore:
    @pytest.mark.asyncio
    async def test_connect(self, mock_redis):
        with patch("src.shared_state.redis_store.aioredis.from_url", new_callable=AsyncMock) as from_url:
            from_url.return_value = mock_redis
            s = RedisStore()
            await s.connect()
            assert s._redis is not None

    @pytest.mark.asyncio
    async def test_set_and_get_task_status(self, store, mock_redis):
        await store.set_task_status("task_01", "running")
        mock_redis.hset.assert_called_with("task:task_01", "status", "running")

        mock_redis.hget.return_value = "done"
        status = await store.get_task_status("task_01")
        assert status == "done"

    @pytest.mark.asyncio
    async def test_set_and_get_subtask_status(self, store, mock_redis):
        await store.set_subtask_status("task_01", "sub_01", "running")
        mock_redis.hset.assert_called_with("task:task_01:subtask:sub_01", "status", "running")

        mock_redis.hget.return_value = "done"
        status = await store.get_subtask_status("task_01", "sub_01")
        assert status == "done"

    @pytest.mark.asyncio
    async def test_set_and_get_subtask_summary(self, store, mock_redis):
        summary = {"output": "some result", "key": "value"}
        await store.set_subtask_summary("task_01", "sub_01", summary)

        import json
        mock_redis.hget.return_value = json.dumps(summary)
        result = await store.get_subtask_summary("task_01", "sub_01")
        assert result == summary

    @pytest.mark.asyncio
    async def test_get_subtask_summary_none(self, store, mock_redis):
        mock_redis.hget.return_value = None
        result = await store.get_subtask_summary("task_01", "sub_01")
        assert result is None

    @pytest.mark.asyncio
    async def test_set_and_get_result(self, store, mock_redis):
        result_data = {"report": "final output"}
        await store.set_result("task_01", result_data)

        import json
        mock_redis.hget.return_value = json.dumps(result_data)
        result = await store.get_result("task_01")
        assert result == result_data

    @pytest.mark.asyncio
    async def test_set_and_get_goal(self, store, mock_redis):
        await store.set_goal("task_01", "research topic")
        mock_redis.hget.return_value = "research topic"
        goal = await store.get_goal("task_01")
        assert goal == "research topic"

    @pytest.mark.asyncio
    async def test_get_goal_null(self, store, mock_redis):
        mock_redis.hget.return_value = None
        goal = await store.get_goal("task_01")
        assert goal is None

    @pytest.mark.asyncio
    async def test_close(self, store, mock_redis):
        await store.close()
        mock_redis.close.assert_called_once()
