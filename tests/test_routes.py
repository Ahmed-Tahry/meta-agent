import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from httpx import AsyncClient, ASGITransport

from src.main import app


@pytest.fixture
def client():
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


class TestRoutes:
    @pytest.mark.asyncio
    async def test_run_returns_202(self, client):
        with patch("src.api.routes.orchestrator") as mock_orch:
            mock_orch.start = MagicMock()

            response = await client.post("/run", json={"goal": "test goal"})
            assert response.status_code == 202
            data = response.json()
            assert "task_id" in data
            assert len(data["task_id"]) == 8

    @pytest.mark.asyncio
    async def test_run_starts_orchestrator(self, client):
        with patch("src.api.routes.orchestrator") as mock_orch:
            mock_orch.start = MagicMock()

            response = await client.post("/run", json={"goal": "research competitors"})
            mock_orch.start.assert_called_once()
            args = mock_orch.start.call_args
            assert args[1]["goal"] == "research competitors"

    @pytest.mark.asyncio
    async def test_run_invalid_body(self, client):
        response = await client.post("/run", json={})
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_get_task_found(self, client):
        with (
            patch("src.api.routes.store") as mock_store,
        ):
            mock_store.get_task_status = AsyncMock(return_value="done")
            mock_store.get_result = AsyncMock(return_value={"report": "final"})
            mock_store.get_goal = AsyncMock(return_value="test goal")

            response = await client.get("/tasks/task_01")
            assert response.status_code == 200
            data = response.json()
            assert data["task_id"] == "task_01"
            assert data["status"] == "done"
            assert data["goal"] == "test goal"
            assert data["result"] == {"report": "final"}

    @pytest.mark.asyncio
    async def test_get_task_not_found(self, client):
        with patch("src.api.routes.store") as mock_store:
            mock_store.get_task_status = AsyncMock(return_value=None)

            response = await client.get("/tasks/nonexistent")
            assert response.status_code == 404
            assert response.json()["detail"] == "Task not found"

    @pytest.mark.asyncio
    async def test_get_task_pending(self, client):
        with patch("src.api.routes.store") as mock_store:
            mock_store.get_task_status = AsyncMock(return_value="running")
            mock_store.get_result = AsyncMock(return_value=None)
            mock_store.get_goal = AsyncMock(return_value="test")

            response = await client.get("/tasks/task_01")
            assert response.status_code == 200
            assert response.json()["status"] == "running"
            assert response.json()["result"] is None

    @pytest.mark.asyncio
    async def test_stream_task_found(self, client):
        with (
            patch("src.api.routes.store") as mock_store,
            patch("src.api.routes.event_bus") as mock_bus,
        ):
            mock_store.get_task_status = AsyncMock(return_value="running")
            mock_queue = AsyncMock()
            mock_queue.get = AsyncMock(side_effect=[
                {"event": "status", "data": {"status": "running"}},
                {"event": "node", "data": {"node": "planner"}},
                {"event": "complete", "data": {"result": "done"}},
            ])
            mock_bus.subscribe = MagicMock(return_value=mock_queue)

            async with client.stream("GET", "/tasks/task_01/stream") as response:
                assert response.status_code == 200
                assert response.headers["content-type"] == "text/event-stream"

                content = b""
                async for chunk in response.aiter_bytes():
                    content += chunk

                text = content.decode()
                assert "event: status" in text
                assert "event: node" in text
                assert "event: complete" in text

    @pytest.mark.asyncio
    async def test_stream_task_not_found(self, client):
        with patch("src.api.routes.store") as mock_store:
            mock_store.get_task_status = AsyncMock(return_value=None)

            response = await client.get("/tasks/nonexistent/stream")
            assert response.status_code == 404
