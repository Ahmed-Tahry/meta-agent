from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

from src.event_bus.bus import event_bus
from src.shared_state.redis_store import store
from src.meta_agent.orchestrator import orchestrator
import uuid


router = APIRouter()


class RunRequest(BaseModel):
    goal: str


@router.post("/run")
async def run(req: RunRequest) -> JSONResponse:
    task_id = str(uuid.uuid4())[:8]
    orchestrator.start(req.goal, task_id)
    return JSONResponse(
        content={"task_id": task_id},
        status_code=202,
    )


@router.get("/tasks/{task_id}")
async def get_task(task_id: str) -> dict[str, Any]:
    status = await store.get_task_status(task_id)
    if status is None:
        raise HTTPException(status_code=404, detail="Task not found")
    result = await store.get_result(task_id)
    goal = await store.get_goal(task_id)
    return {
        "task_id": task_id,
        "goal": goal,
        "status": status,
        "result": result,
    }


@router.get("/tasks/{task_id}/stream")
async def stream_task(task_id: str) -> StreamingResponse:
    status = await store.get_task_status(task_id)
    if status is None:
        raise HTTPException(status_code=404, detail="Task not found")

    queue = event_bus.subscribe(task_id)

    async def event_generator():
        try:
            while True:
                msg = await queue.get()
                yield f"event: {msg['event']}\ndata: {msg['data']}\n\n"
                if msg["event"] == "complete" or msg["event"] == "error":
                    break
        finally:
            event_bus.unsubscribe(task_id)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
    )
