from fastapi import FastAPI

from src.api.routes import router
from src.shared_state.redis_store import store

app = FastAPI(title="Meta-Agent")
app.include_router(router)


@app.on_event("startup")
async def startup() -> None:
    await store.connect()


@app.on_event("shutdown")
async def shutdown() -> None:
    await store.close()
