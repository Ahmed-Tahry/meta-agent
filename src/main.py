from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse


# Load .env before any other imports that need env vars
_env_path = Path(__file__).resolve().parents[1] / ".env"
if _env_path.exists():
    for _line in _env_path.read_text().splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _v = _line.split("=", 1)
            import os
            os.environ.setdefault(_k, _v)


from src.api.routes import router
from src.shared_state.redis_store import store

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
