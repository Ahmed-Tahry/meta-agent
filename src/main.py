from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from src.utils import load_env_file

load_env_file()


from src.api.routes import router  # noqa: E402 - after manual .env load
from src.shared_state.redis_store import store  # noqa: E402

app = FastAPI(title="Meta-Agent")
app.include_router(router)

DASHBOARD_HTML: str = ""


@app.on_event("startup")
async def startup() -> None:
    global DASHBOARD_HTML
    html_path = Path(__file__).resolve().parent / "web" / "dashboard.html"
    if html_path.exists():
        DASHBOARD_HTML = html_path.read_text()
    await store.connect()


@app.on_event("shutdown")
async def shutdown() -> None:
    await store.close()


@app.get("/", response_class=HTMLResponse)
@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard() -> str:
    return DASHBOARD_HTML
